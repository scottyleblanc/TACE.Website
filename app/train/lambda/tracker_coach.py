"""
tracker_coach.py -- Lambda handler for the AI coach (Stage 3.10).

Routes (API Gateway HTTP API, payload format 2.0):
  POST   /conversations             -- create a named thread. Body: {title}
  GET    /conversations              -- list the caller's threads (metadata only)
  GET    /conversations/{id}         -- load a thread's messages
  PATCH  /conversations/{id}         -- rename. Body: {title}
  DELETE /conversations/{id}         -- delete a thread and all its messages

Every route derives user_id from the verified Cognito JWT claims (never body or
path) and scopes reads/writes to that partition; a thread that isn't the
caller's returns 404, identical to days_api.py's cross-user handling.

Response envelope (per docs/AI-COACH-ENDPOINT-SPEC.md): {ok, data, message}.
`message` is always safe to log -- never a credential, secret ARN, or the
Anthropic key.

Data model -- conversations table, PK user_id, SK sk:
  CONV#{conversation_id}       -- thread metadata (title, created_at, updated_at, message_count)
  MSG#{conversation_id}#{ts}   -- one message (role, content, created_at)
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_CONVERSATIONS_TABLE_NAME = os.environ["CONVERSATIONS_TABLE"]
_dynamodb = boto3.resource("dynamodb")
_conversations_table = _dynamodb.Table(_CONVERSATIONS_TABLE_NAME)

_MAX_TITLE_LEN = 200

_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "https://train.tacedata.ca",
    "Access-Control-Allow-Headers": "Authorization,Content-Type",
    "Content-Type": "application/json",
}


def _json_default(obj):
    if isinstance(obj, Decimal):
        return int(obj) if obj == int(obj) else float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _envelope(status: int, ok: bool, data: object, message: str) -> dict:
    return {
        "statusCode": status,
        "headers": _CORS_HEADERS,
        "body": json.dumps({"ok": ok, "data": data, "message": message}, default=_json_default),
    }


def _ok(data: object, message: str = "") -> dict:
    return _envelope(200, True, data, message)


def _err(status: int, message: str) -> dict:
    return _envelope(status, False, None, message)


def _claims(event: dict) -> dict:
    """The verified JWT claims map from the API Gateway Cognito authorizer."""
    try:
        return event["requestContext"]["authorizer"]["jwt"]["claims"]
    except (KeyError, TypeError):
        return {}


def _user_id(claims: dict) -> str | None:
    """The caller's Cognito `sub`, from the verified JWT authorizer claims.

    Never trust a `user_id` from the body or path -- see days_api.py for the
    same convention.
    """
    sub = claims.get("sub")
    return sub if sub else None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _conv_sk(conversation_id: str) -> str:
    return f"CONV#{conversation_id}"


def _conv_id_from_sk(sk: str) -> str:
    return sk[len("CONV#"):]


def _get_thread_item(user_id: str, conversation_id: str) -> dict | None:
    result = _conversations_table.get_item(Key={"user_id": user_id, "sk": _conv_sk(conversation_id)})
    return result.get("Item")


def _create_conversation(user_id: str, raw_body: str | None) -> dict:
    try:
        payload = json.loads(raw_body) if raw_body else {}
    except json.JSONDecodeError:
        return _err(400, "Invalid JSON")

    title = payload.get("title")
    if not isinstance(title, str) or not title.strip():
        return _err(400, "Field 'title' is required")
    if len(title) > _MAX_TITLE_LEN:
        return _err(400, f"Field 'title' exceeds maximum length of {_MAX_TITLE_LEN} characters")

    conversation_id = uuid.uuid4().hex
    now = _now()
    item = {
        "user_id": user_id,
        "sk": _conv_sk(conversation_id),
        "title": title.strip(),
        "created_at": now,
        "updated_at": now,
        "message_count": 0,
    }
    _conversations_table.put_item(Item=item)
    return _ok({"conversation_id": conversation_id}, "Conversation created")


def _list_conversations(user_id: str) -> dict:
    items = []
    query_kwargs: dict = {
        "KeyConditionExpression": Key("user_id").eq(user_id) & Key("sk").begins_with("CONV#"),
    }
    while True:
        result = _conversations_table.query(**query_kwargs)
        items.extend(result.get("Items", []))
        last = result.get("LastEvaluatedKey")
        if not last:
            break
        query_kwargs["ExclusiveStartKey"] = last

    threads = [
        {
            "conversation_id": _conv_id_from_sk(item["sk"]),
            "title": item.get("title", ""),
            "created_at": item.get("created_at", ""),
            "updated_at": item.get("updated_at", ""),
            "message_count": item.get("message_count", 0),
        }
        for item in items
    ]
    threads.sort(key=lambda t: t["updated_at"], reverse=True)
    return _ok(threads)


def _get_conversation(user_id: str, conversation_id: str) -> dict:
    thread = _get_thread_item(user_id, conversation_id)
    if thread is None:
        return _err(404, f"Conversation {conversation_id} not found")

    messages = []
    query_kwargs: dict = {
        "KeyConditionExpression": Key("user_id").eq(user_id) & Key("sk").begins_with(f"MSG#{conversation_id}#"),
    }
    while True:
        result = _conversations_table.query(**query_kwargs)
        messages.extend(result.get("Items", []))
        last = result.get("LastEvaluatedKey")
        if not last:
            break
        query_kwargs["ExclusiveStartKey"] = last

    return _ok({
        "conversation_id": conversation_id,
        "title": thread.get("title", ""),
        "created_at": thread.get("created_at", ""),
        "updated_at": thread.get("updated_at", ""),
        "messages": [
            {
                "role": m.get("role", ""),
                "content": m.get("content", ""),
                "created_at": m.get("created_at", ""),
                "rail_triggered": m.get("rail_triggered", False),
            }
            for m in messages
        ],
    })


def _patch_conversation(user_id: str, conversation_id: str, raw_body: str | None) -> dict:
    if not raw_body:
        return _err(400, "Request body required")
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return _err(400, "Invalid JSON")

    title = payload.get("title")
    if not isinstance(title, str) or not title.strip():
        return _err(400, "Field 'title' is required")
    if len(title) > _MAX_TITLE_LEN:
        return _err(400, f"Field 'title' exceeds maximum length of {_MAX_TITLE_LEN} characters")

    try:
        result = _conversations_table.update_item(
            Key={"user_id": user_id, "sk": _conv_sk(conversation_id)},
            UpdateExpression="SET title = :title, updated_at = :now",
            ConditionExpression="attribute_exists(#pk)",
            ExpressionAttributeNames={"#pk": "user_id"},
            ExpressionAttributeValues={":title": title.strip(), ":now": _now()},
            ReturnValues="ALL_NEW",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return _err(404, f"Conversation {conversation_id} not found")
        raise

    return _ok({"conversation_id": conversation_id, "title": result["Attributes"]["title"]}, "Conversation renamed")


def _delete_conversation(user_id: str, conversation_id: str) -> dict:
    try:
        _conversations_table.delete_item(
            Key={"user_id": user_id, "sk": _conv_sk(conversation_id)},
            ConditionExpression="attribute_exists(#pk)",
            ExpressionAttributeNames={"#pk": "user_id"},
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return _err(404, f"Conversation {conversation_id} not found")
        raise

    message_keys = []
    query_kwargs: dict = {
        "KeyConditionExpression": Key("user_id").eq(user_id) & Key("sk").begins_with(f"MSG#{conversation_id}#"),
        "ProjectionExpression": "sk",
    }
    while True:
        result = _conversations_table.query(**query_kwargs)
        message_keys.extend(result.get("Items", []))
        last = result.get("LastEvaluatedKey")
        if not last:
            break
        query_kwargs["ExclusiveStartKey"] = last

    with _conversations_table.batch_writer() as batch:
        for key in message_keys:
            batch.delete_item(Key={"user_id": user_id, "sk": key["sk"]})

    return _ok(None, "Conversation deleted")


def handler(event: dict, context) -> dict:
    route_key = event.get("routeKey", "")
    path_params = event.get("pathParameters") or {}
    body = event.get("body")

    claims = _claims(event)
    user_id = _user_id(claims)
    if not user_id:
        return _err(401, "Unauthenticated")

    conversation_id = path_params.get("id", "")
    logger.info("[tracker_coach] route=%s user=%s", route_key, user_id[:8])

    if route_key == "POST /conversations":
        return _create_conversation(user_id, body)
    if route_key == "GET /conversations":
        return _list_conversations(user_id)
    if route_key == "GET /conversations/{id}":
        return _get_conversation(user_id, conversation_id)
    if route_key == "PATCH /conversations/{id}":
        return _patch_conversation(user_id, conversation_id, body)
    if route_key == "DELETE /conversations/{id}":
        return _delete_conversation(user_id, conversation_id)
    return _err(400, f"Unhandled route: {route_key}")
