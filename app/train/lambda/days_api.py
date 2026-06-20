"""
days_api.py -- Lambda handler for the tracker API.

Routes (API Gateway HTTP API, payload format 2.0):
  GET  /days           -- all 105 training days, sorted by date
  GET  /days/{date}    -- single day by ISO date string (e.g. 2026-06-15)
  PATCH /days/{date}   -- update user-state fields: completed (bool), notes (str)
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

# Maximum accepted length for the user-supplied notes field.
_MAX_NOTES_LEN = 2000

_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "https://train.tacedata.ca",
    "Access-Control-Allow-Headers": "Authorization,Content-Type",
    "Content-Type": "application/json",
}


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
    return _ok(items)


def _get_day(date: str) -> dict:
    result = _table.get_item(Key={"date": date})
    item = result.get("Item")
    if item is None:
        return _err(404, f"Day {date} not found")
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
