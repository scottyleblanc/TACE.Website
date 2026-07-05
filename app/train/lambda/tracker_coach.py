"""
tracker_coach.py -- Lambda handler for the AI coach (Stage 3.10).

Routes (API Gateway HTTP API, payload format 2.0):
  POST   /conversations                    -- create a named thread. Body: {title}
  GET    /conversations                     -- list the caller's threads (metadata only)
  GET    /conversations/{id}                -- load a thread's messages
  PATCH  /conversations/{id}                -- rename. Body: {title}
  DELETE /conversations/{id}                -- delete a thread and all its messages
  POST   /conversations/{id}/messages       -- the coach turn (rail-only for now; see below)

Every route derives user_id from the verified Cognito JWT claims (never body or
path) and scopes reads/writes to that partition; a thread that isn't the
caller's returns 404, identical to days_api.py's cross-user handling.

Response envelope (per docs/AI-COACH-ENDPOINT-SPEC.md): {ok, data, message}.
`message` is always safe to log -- never a credential, secret ARN, or the
Anthropic key.

Data model -- conversations table, PK user_id, SK sk:
  CONV#{conversation_id}       -- thread metadata (title, created_at, updated_at, message_count)
  MSG#{conversation_id}#{ts}   -- one message (role, content, created_at)

Stage 3.10 build order (per docs/AI-COACH-ENDPOINT-SPEC.md): thread CRUD, then
/settings (in days_api.py), then the medical rail proven standalone, then the
coach turn itself. This file currently implements the rail step: the message
route persists the user's message, classifies it, and either returns the canned
deferral (rail_triggered) or -- until the coach turn is built -- a 501. The
merged plan view, facts-in-code, prompt assembly, and the coach-model call are
[DEFERRED] to the next step in this stage.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import anthropic
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_CONVERSATIONS_TABLE_NAME = os.environ["CONVERSATIONS_TABLE"]
_dynamodb = boto3.resource("dynamodb")
_conversations_table = _dynamodb.Table(_CONVERSATIONS_TABLE_NAME)

_ANTHROPIC_SECRET_ARN = os.environ["ANTHROPIC_SECRET_ARN"]
_RAIL_MODEL = os.environ["RAIL_MODEL"]
_COACH_MODEL = os.environ["COACH_MODEL"]
_HISTORY_WINDOW_TURNS = int(os.environ.get("HISTORY_WINDOW_TURNS", "10"))
_MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "1024"))

_secretsmanager = boto3.client("secretsmanager")
_anthropic_client: "anthropic.Anthropic | None" = None  # cached at module scope, built lazily

_MAX_TITLE_LEN = 200
_MAX_MESSAGE_LEN = 4000

_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "https://train.tacedata.ca",
    "Access-Control-Allow-Headers": "Authorization,Content-Type",
    "Content-Type": "application/json",
}

# [DEFERRED to Stage 3.11] Final classifier prompt wording and label boundary are
# built with an eval set (docs/AI-COACH-PROMPTS-AND-EVALS-SPEC.md). This is a
# functional placeholder so the hard rail can be proven standalone now.
_RAIL_SYSTEM_PROMPT = (
    "You are a safety classifier for a running-training coach app. Decide whether "
    "the user's message is seeking clinical, injury, medical, diagnostic, or "
    "treatment guidance (pain, symptoms, an existing condition, medication, or what "
    "to do about an injury). Respond with strict JSON only: "
    '{"label": "medical"} or {"label": "ok"}. '
    "No other text, no markdown, no code fences, no backticks -- the raw JSON object only."
)

_RAIL_DEFERRAL_REPLY = (
    "That sounds like a question for your physiotherapist or another qualified "
    "clinician rather than for me -- I'm not able to give medical, injury, or "
    "treatment guidance. Please reach out to them directly."
)


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
    if _get_thread_item(user_id, conversation_id) is None:
        return _err(404, f"Conversation {conversation_id} not found")

    # Delete messages before the thread item itself: if this fails partway
    # through, the thread stays visible (just short some messages) and the
    # whole delete is safely retryable -- deleting the thread item first would
    # instead orphan any remaining messages under a conversation_id nothing
    # points to anymore.
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

    _conversations_table.delete_item(Key={"user_id": user_id, "sk": _conv_sk(conversation_id)})

    return _ok(None, "Conversation deleted")


def _get_anthropic_client() -> anthropic.Anthropic:
    global _anthropic_client
    if _anthropic_client is None:
        secret = json.loads(_secretsmanager.get_secret_value(SecretId=_ANTHROPIC_SECRET_ARN)["SecretString"])
        _anthropic_client = anthropic.Anthropic(api_key=secret["api_key"])
    return _anthropic_client


def _rail_check(message_content: str) -> bool:
    """True if the message should be deferred (medical/injury/clinical).

    Fails closed: any classifier error, or a response that doesn't parse to
    exactly {"label": "medical"|"ok"}, is treated as triggered -- the rail
    contract requires ambiguity to defer, not pass through to the coach.
    """
    try:
        client = _get_anthropic_client()
        response = client.messages.create(
            model=_RAIL_MODEL,
            max_tokens=40,
            system=_RAIL_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": message_content}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            # Strip a markdown code fence (optionally language-tagged) if the
            # model added one despite being told not to -- belt and suspenders.
            raw = raw.strip("`")
            raw = raw.removeprefix("json").strip()
        label = json.loads(raw).get("label")
        if label not in ("medical", "ok"):
            logger.warning("[tracker_coach] rail: ambiguous label %r -- deferring closed", label)
            return True
        return label == "medical"
    except Exception:
        logger.exception("[tracker_coach] rail: classifier call failed -- deferring closed")
        return True


def _bump_thread(user_id: str, conversation_id: str, message_increment: int) -> None:
    _conversations_table.update_item(
        Key={"user_id": user_id, "sk": _conv_sk(conversation_id)},
        UpdateExpression="SET updated_at = :now ADD message_count :incr",
        ExpressionAttributeValues={":now": _now(), ":incr": message_increment},
    )


def _post_message(user_id: str, conversation_id: str, raw_body: str | None) -> dict:
    thread = _get_thread_item(user_id, conversation_id)
    if thread is None:
        return _err(404, f"Conversation {conversation_id} not found")

    if not raw_body:
        return _err(400, "Request body required")
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return _err(400, "Invalid JSON")

    content = payload.get("content")
    if not isinstance(content, str) or not content.strip():
        return _err(400, "Field 'content' is required")
    if len(content) > _MAX_MESSAGE_LEN:
        return _err(400, f"Field 'content' exceeds maximum length of {_MAX_MESSAGE_LEN} characters")
    content = content.strip()

    user_ts = _now()
    _conversations_table.put_item(Item={
        "user_id": user_id,
        "sk": f"MSG#{conversation_id}#{user_ts}#user",
        "role": "user",
        "content": content,
        "created_at": user_ts,
    })

    if _rail_check(content):
        reply_ts = _now()
        _conversations_table.put_item(Item={
            "user_id": user_id,
            "sk": f"MSG#{conversation_id}#{reply_ts}#rail",
            "role": "rail",
            "content": _RAIL_DEFERRAL_REPLY,
            "created_at": reply_ts,
            "rail_triggered": True,
        })
        _bump_thread(user_id, conversation_id, message_increment=2)
        return _ok({"role": "rail", "content": _RAIL_DEFERRAL_REPLY, "rail_triggered": True})

    # [DEFERRED to the next Stage 3.10 step] Merged plan view, facts-in-code,
    # prompt assembly, and the coach-model call are not yet wired -- the rail is
    # proven standalone first, per the endpoint spec's build order. The user
    # message above is already persisted; nothing else is written on this path.
    return _err(501, "Coach turn not yet implemented -- rail-only build")


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
    if route_key == "POST /conversations/{id}/messages":
        return _post_message(user_id, conversation_id, body)
    return _err(400, f"Unhandled route: {route_key}")
