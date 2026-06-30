"""
days_api.py -- Lambda handler for the tracker API.

Routes (API Gateway HTTP API, payload format 2.0):
  GET  /days           -- all 105 training days, sorted by date, with overrides merged
  GET  /days/{date}    -- single day by ISO date string (e.g. 2026-06-15)
  PATCH /days/{date}   -- update user-state fields: completed (bool), notes (str)

Override layer:
  If OVERRIDES_TABLE env var is set, GET routes merge active overrides on top of
  seed rows before returning. PATCH always writes to the seed table (user state).
  Merged items include has_override=true and original_session_type/original_session_detail
  so the frontend can display "Adjusted from: ...".
"""

import json
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_TABLE_NAME = os.environ["DYNAMODB_TABLE"]
_dynamodb = boto3.resource("dynamodb")
_table = _dynamodb.Table(_TABLE_NAME)

_OVERRIDES_TABLE_NAME = os.environ.get("OVERRIDES_TABLE")
_overrides_table = _dynamodb.Table(_OVERRIDES_TABLE_NAME) if _OVERRIDES_TABLE_NAME else None

_MAX_NOTES_LEN = 2000

_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "https://train.tacedata.ca",
    "Access-Control-Allow-Headers": "Authorization,Content-Type",
    "Content-Type": "application/json",
}

# Fields applied from the override item when present and non-empty.
_OVERRIDE_FIELDS = (
    "session_type", "session_detail", "coaching_focus",
    "run_interval_minutes", "run_walk_ratio", "session_minutes_target",
    "alternate_exercise",
)

# Fields always stored in the override item (even as empty string).
# An empty string here means "clear this field from the merged result"
# rather than "inherit from the seed row."
_CLEARABLE_FIELDS = frozenset(("run_walk_ratio", "alternate_exercise"))


def _json_default(obj):
    if isinstance(obj, Decimal):
        return int(obj) if obj == int(obj) else float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _ok(body: object) -> dict:
    return {
        "statusCode": 200,
        "headers": _CORS_HEADERS,
        "body": json.dumps(body, default=_json_default),
    }


def _err(status: int, message: str) -> dict:
    return {
        "statusCode": status,
        "headers": _CORS_HEADERS,
        "body": json.dumps({"error": message}),
    }


def _merge_override(seed_item: dict, override_item: dict) -> dict:
    merged = dict(seed_item)
    merged["has_override"] = True
    merged["original_session_type"] = seed_item.get("session_type", "")
    merged["original_session_detail"] = seed_item.get("session_detail", "")

    for field in _OVERRIDE_FIELDS:
        if field not in override_item:
            continue  # not in override item -- inherit from seed
        val = override_item[field]
        if field in _CLEARABLE_FIELDS:
            # Empty string = intentionally cleared; remove from merged result
            if val == "" or val is None:
                merged.pop(field, None)
            else:
                merged[field] = val
        elif val not in ("", None):
            merged[field] = val

    merged["override_reason"] = override_item.get("override_reason", "")
    merged["override_source"] = override_item.get("override_source", "")
    merged["override_note"]   = override_item.get("override_note", "")
    merged["provisional"]     = bool(override_item.get("provisional", False))

    return merged


def _scan_overrides() -> dict:
    overrides: dict = {}
    kwargs: dict = {}
    while True:
        result = _overrides_table.scan(**kwargs)
        for item in result.get("Items", []):
            if item.get("override_active"):
                overrides[item["date"]] = item
        last = result.get("LastEvaluatedKey")
        if not last:
            break
        kwargs["ExclusiveStartKey"] = last
    return overrides


def _apply_override(seed_item: dict, overrides: dict) -> dict:
    override = overrides.get(seed_item["date"])
    if override:
        return _merge_override(seed_item, override)
    return seed_item


def _get_days() -> dict:
    items = []
    scan_kwargs: dict = {}
    while True:
        result = _table.scan(**scan_kwargs)
        items.extend(result.get("Items", []))
        last = result.get("LastEvaluatedKey")
        if not last:
            break
        scan_kwargs["ExclusiveStartKey"] = last
    items.sort(key=lambda x: x["date"])

    if _overrides_table:
        overrides = _scan_overrides()
        items = [_apply_override(item, overrides) for item in items]

    return _ok(items)


def _get_day(date: str) -> dict:
    result = _table.get_item(Key={"date": date})
    item = result.get("Item")
    if item is None:
        return _err(404, f"Day {date} not found")

    if _overrides_table:
        override_result = _overrides_table.get_item(Key={"date": date})
        override = override_result.get("Item")
        if override and override.get("override_active"):
            item = _merge_override(item, override)

    return _ok(item)


def _patch_day(date: str, raw_body: str | None) -> dict:
    if not raw_body:
        return _err(400, "Request body required")
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return _err(400, "Invalid JSON")

    set_parts: list[str] = []
    remove_parts: list[str] = []
    expr_names: dict = {"#pk": "date"}
    expr_values: dict = {}

    if "completed" in payload:
        if not isinstance(payload["completed"], bool):
            return _err(400, "Field 'completed' must be a boolean")
        completed = payload["completed"]
        set_parts.append("#completed = :completed")
        expr_names["#completed"] = "completed"
        expr_values[":completed"] = completed
        if completed:
            set_parts.append("completed_date = :completed_date")
            expr_values[":completed_date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        else:
            remove_parts.append("completed_date")

    if "notes" in payload:
        notes = payload["notes"]
        if not isinstance(notes, str):
            return _err(400, "Field 'notes' must be a string")
        if len(notes) > _MAX_NOTES_LEN:
            return _err(400, f"Field 'notes' exceeds maximum length of {_MAX_NOTES_LEN} characters")
        set_parts.append("#notes = :notes")
        expr_names["#notes"] = "notes"
        expr_values[":notes"] = notes

    if not set_parts and not remove_parts:
        return _err(400, "No valid fields to update (accepted: completed, notes)")

    update_expr_parts = []
    if set_parts:
        update_expr_parts.append("SET " + ", ".join(set_parts))
    if remove_parts:
        update_expr_parts.append("REMOVE " + ", ".join(remove_parts))

    update_kwargs: dict = {
        "Key": {"date": date},
        "UpdateExpression": " ".join(update_expr_parts),
        "ConditionExpression": "attribute_exists(#pk)",
        "ExpressionAttributeNames": expr_names,
        "ReturnValues": "ALL_NEW",
    }
    if expr_values:
        update_kwargs["ExpressionAttributeValues"] = expr_values

    try:
        result = _table.update_item(**update_kwargs)
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return _err(404, f"Day {date} not found")
        raise

    return _ok(result.get("Attributes", {}))


def handler(event: dict, context) -> dict:
    route_key = event.get("routeKey", "")
    path_params = event.get("pathParameters") or {}
    body = event.get("body")
    logger.info("route=%s params=%s", route_key, path_params)

    if route_key == "GET /days":
        return _get_days()
    if route_key == "GET /days/{date}":
        return _get_day(path_params.get("date", ""))
    if route_key == "PATCH /days/{date}":
        return _patch_day(path_params.get("date", ""), body)
    return _err(400, f"Unhandled route: {route_key}")
