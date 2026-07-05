"""
days_api.py -- Lambda handler for the tracker API.

Routes (API Gateway HTTP API, payload format 2.0):
  GET  /days           -- all 105 training days, sorted by date, with overrides merged
  GET  /days/{date}    -- single day by ISO date string (e.g. 2026-06-15)
  PATCH /days/{date}   -- update user-state fields: completed (bool), notes (str)
  GET  /settings       -- read coach_scope from the caller's users record
  PATCH /settings      -- update coach_scope (plan_only | plan_plus_general)

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
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

import plan_merge

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_TABLE_NAME = os.environ["DYNAMODB_TABLE"]
_dynamodb = boto3.resource("dynamodb")
_table = _dynamodb.Table(_TABLE_NAME)

_OVERRIDES_TABLE_NAME = os.environ.get("OVERRIDES_TABLE")
_overrides_table = _dynamodb.Table(_OVERRIDES_TABLE_NAME) if _OVERRIDES_TABLE_NAME else None

_USERS_TABLE_NAME = os.environ["USERS_TABLE"]
_users_table = _dynamodb.Table(_USERS_TABLE_NAME)

_MAX_NOTES_LEN = 2000

_COACH_SCOPES = frozenset(("plan_only", "plan_plus_general"))

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


def _claims(event: dict) -> dict:
    """The verified JWT claims map from the API Gateway Cognito authorizer."""
    try:
        return event["requestContext"]["authorizer"]["jwt"]["claims"]
    except (KeyError, TypeError):
        return {}


def _user_id(claims: dict) -> str | None:
    """The caller's Cognito `sub`, from the verified JWT authorizer claims.

    Never trust a `user_id` from the body or path -- it comes only from the token
    the API Gateway Cognito authorizer has already verified. Returns None when the
    claim is absent (treated as unauthenticated by the handler).
    """
    sub = claims.get("sub")
    return sub if sub else None


def _ensure_profile(user_id: str, claims: dict) -> None:
    """Idempotently provision the users/profile record on first login.

    A conditional put on absence of user_id -- a returning user's existing
    profile (and any coach_scope they've since changed) is left untouched.
    email/display_name are populated only if the verified token happens to
    carry them; this Cognito app client's access token does not today, so
    both are typically omitted rather than written empty.
    """
    now = datetime.now(timezone.utc).isoformat()
    item: dict = {
        "user_id": user_id,
        "coach_scope": "plan_only",
        "created_at": now,
        "updated_at": now,
    }
    email = claims.get("email")
    if email:
        item["email"] = email
    display_name = claims.get("name") or claims.get("given_name")
    if display_name:
        item["display_name"] = display_name

    try:
        _users_table.put_item(Item=item, ConditionExpression="attribute_not_exists(user_id)")
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise
        # Profile already exists -- idempotent no-op, nothing to do.


def _get_days(user_id: str) -> dict:
    items = []
    query_kwargs: dict = {"KeyConditionExpression": Key("user_id").eq(user_id)}
    while True:
        result = _table.query(**query_kwargs)
        items.extend(result.get("Items", []))
        last = result.get("LastEvaluatedKey")
        if not last:
            break
        query_kwargs["ExclusiveStartKey"] = last
    items.sort(key=lambda x: x["date"])

    if _overrides_table:
        overrides = plan_merge.query_overrides(_overrides_table, user_id)
        items = plan_merge.apply_overrides_to_items(items, overrides)

    return _ok(items)


def _get_day(user_id: str, date: str) -> dict:
    result = _table.get_item(Key={"user_id": user_id, "date": date})
    item = result.get("Item")
    if item is None:
        # Missing in the caller's partition -- a non-owned row simply isn't here.
        return _err(404, f"Day {date} not found")

    if _overrides_table:
        override_result = _overrides_table.get_item(Key={"user_id": user_id, "date": date})
        override = override_result.get("Item")
        if override and override.get("override_active"):
            item = plan_merge.merge_override(item, override)

    return _ok(item)


def _patch_day(user_id: str, date: str, raw_body: str | None) -> dict:
    if not raw_body:
        return _err(400, "Request body required")
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return _err(400, "Invalid JSON")

    set_parts: list[str] = []
    remove_parts: list[str] = []
    expr_names: dict = {"#pk": "user_id"}
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
        "Key": {"user_id": user_id, "date": date},
        "UpdateExpression": " ".join(update_expr_parts),
        # attribute_exists(user_id) is false when the item is absent from the
        # caller's partition (nonexistent date, or another user's row) -- the
        # update is rejected rather than creating a row, and we map it to 404.
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


def _get_settings(user_id: str) -> dict:
    result = _users_table.get_item(Key={"user_id": user_id})
    item = result.get("Item") or {}
    return _ok({"coach_scope": item.get("coach_scope", "plan_only")})


def _patch_settings(user_id: str, raw_body: str | None) -> dict:
    if not raw_body:
        return _err(400, "Request body required")
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return _err(400, "Invalid JSON")

    coach_scope = payload.get("coach_scope")
    if coach_scope not in _COACH_SCOPES:
        return _err(400, f"Field 'coach_scope' must be one of {sorted(_COACH_SCOPES)}")

    try:
        result = _users_table.update_item(
            Key={"user_id": user_id},
            UpdateExpression="SET coach_scope = :scope, updated_at = :now",
            ConditionExpression="attribute_exists(#pk)",
            ExpressionAttributeNames={"#pk": "user_id"},
            ExpressionAttributeValues={
                ":scope": coach_scope,
                ":now": datetime.now(timezone.utc).isoformat(),
            },
            ReturnValues="ALL_NEW",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            # _ensure_profile runs before every route, so this should be
            # unreachable in practice -- kept for the same defensive reason
            # as _patch_day's cross-user 404 mapping.
            return _err(404, "User profile not found")
        raise

    return _ok({"coach_scope": result["Attributes"]["coach_scope"]})


def handler(event: dict, context) -> dict:
    route_key = event.get("routeKey", "")
    path_params = event.get("pathParameters") or {}
    body = event.get("body")

    claims = _claims(event)
    user_id = _user_id(claims)
    if not user_id:
        return _err(401, "Unauthenticated")

    _ensure_profile(user_id, claims)

    logger.info("route=%s params=%s user=%s", route_key, path_params, user_id[:8])

    if route_key == "GET /days":
        return _get_days(user_id)
    if route_key == "GET /days/{date}":
        return _get_day(user_id, path_params.get("date", ""))
    if route_key == "PATCH /days/{date}":
        return _patch_day(user_id, path_params.get("date", ""), body)
    if route_key == "GET /settings":
        return _get_settings(user_id)
    if route_key == "PATCH /settings":
        return _patch_settings(user_id, body)
    return _err(400, f"Unhandled route: {route_key}")
