"""
daily_email.py -- EventBridge-triggered Lambda for daily training briefing emails.

Fires daily at 08:00 UTC (4am EDT) via EventBridge rule tracker-daily-email.
Sends one of two email formats depending on whether today is an active day or rest day.

Invocation event (both keys optional):
  test_date  -- ISO date to brief instead of today
  dry_run    -- compose and return the briefing without calling SES. Use this
                when testing: a bare test_date invoke sends real mail to the
                real recipient.

Active day:  session type, detail, coaching focus, minutes, run:walk ratio, streak, link
Rest day:    recovery note, tomorrow's session preview, streak, link

If OVERRIDES_TABLE env var is set, override rows are merged into the day data
before the email is composed, so the email always reflects the adjusted plan.

The briefing covers the user's active training block only (Stage 3.15) -- days
belonging to an earlier, completed block are never briefed, even though they
remain in the same partition.

Environment variables:
  DYNAMODB_TABLE  -- DynamoDB table name (training-plan-v2)
  SES_SENDER      -- From address (noreply@tacedata.ca)
  RECIPIENT       -- To address (<OWNER_EMAIL>)
  OWNER_USER_ID   -- Cognito sub of the single active user
  USERS_TABLE     -- Optional. Users table, read for active_plan_id (training-users)
  OVERRIDES_TABLE -- Optional. DynamoDB overrides table name (training-plan-overrides-v2)
  SITE_URL        -- Optional override for the tracker link (default: https://train.tacedata.ca/)
"""

import json
import logging
import os
from datetime import date, timedelta
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

import plan_merge

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_TABLE_NAME = os.environ["DYNAMODB_TABLE"]
_SENDER     = os.environ["SES_SENDER"]
_RECIPIENT  = os.environ["RECIPIENT"]
_OWNER_USER_ID = os.environ["OWNER_USER_ID"]  # Cognito sub of the single active user
_SITE_URL   = os.environ.get("SITE_URL", "https://train.tacedata.ca/")

_OVERRIDES_TABLE_NAME = os.environ.get("OVERRIDES_TABLE")

# Optional by design (Stage 3.15): unset means "no block configured", which
# briefs from the whole partition exactly as this Lambda did before blocks
# existed. That keeps code deploy and env-var/IAM changes independent of each
# other -- neither ordering breaks the morning email.
_USERS_TABLE_NAME = os.environ.get("USERS_TABLE")

_dynamodb        = boto3.resource("dynamodb")
_table           = _dynamodb.Table(_TABLE_NAME)
_overrides_table = _dynamodb.Table(_OVERRIDES_TABLE_NAME) if _OVERRIDES_TABLE_NAME else None
_users_table     = _dynamodb.Table(_USERS_TABLE_NAME) if _USERS_TABLE_NAME else None
_ses             = boto3.client("sesv2", region_name="ca-central-1")


def _active_plan_id(user_id: str) -> str | None:
    """The training block this user is currently working through, read from the
    users record -- the same single source of truth days_api.py uses."""
    if _users_table is None:
        return None
    result = _users_table.get_item(Key={"user_id": user_id})
    return (result.get("Item") or {}).get("active_plan_id")


def _query_user(user_id: str) -> list[dict]:
    items: list[dict] = []
    kwargs: dict = {"KeyConditionExpression": Key("user_id").eq(user_id)}
    while True:
        result = _table.query(**kwargs)
        items.extend(result.get("Items", []))
        last = result.get("LastEvaluatedKey")
        if not last:
            break
        kwargs["ExclusiveStartKey"] = last
    return sorted(items, key=lambda d: d["date"])


def _compute_streak(days: list[dict], today_str: str) -> int:
    active_past = [
        d for d in days
        if d["is_active_day"] and d["date"] <= today_str
    ]
    streak = 0
    for d in reversed(active_past):
        if d.get("completed"):
            streak += 1
        elif d["date"] == today_str:
            continue  # today not yet done -- don't break the streak
        else:
            break
    return streak


def _day_for(days: list[dict], date_str: str) -> dict | None:
    return next((d for d in days if d["date"] == date_str), None)


def _int(val) -> int:
    return int(val) if isinstance(val, Decimal) else (val or 0)


def _active_day_body(day: dict, streak: int, total_days: int) -> tuple[str, str]:
    session_type = day["session_type"]
    prov_prefix  = "[PROVISIONAL] " if day.get("provisional") else ""
    subject = f"[Training] {prov_prefix}{session_type} -- Day {_int(day['day_of_plan'])} of {total_days}"

    lines = [
        f"Day {_int(day['day_of_plan'])} of {total_days}  |  Week {_int(day['week_number'])}  |  {day['phase']}",
        "",
        f"Session: {session_type}",
        f"Detail:  {day['session_detail']}",
        f"Focus:   {day['coaching_focus']}",
    ]

    if day.get("session_minutes_target"):
        mins      = _int(day["session_minutes_target"])
        ratio     = day.get("run_walk_ratio", "")
        ratio_str = f"  |  {ratio} run:walk" if ratio else ""
        lines.append(f"Target:  {mins} min{ratio_str}")

    if day.get("alternate_exercise"):
        lines.append(f"Alternative: {day['alternate_exercise']}")

    if day.get("has_override"):
        original = day.get("original_session_type", "")
        if original and original != session_type:
            lines.append(f"Adjusted from: {original}")
        reason = day.get("override_reason", "")
        if reason:
            source = day.get("override_source", "")
            source_str = f" ({source})" if source else ""
            lines.append(f"[{prov_prefix.strip() or 'ADJUSTED'}] {reason}{source_str}")

    lines += [
        "",
        f"Current streak: {streak} active day{'s' if streak != 1 else ''}",
        "",
        f"Log your session: {_SITE_URL}",
    ]

    return subject, "\n".join(lines)


def _rest_day_body(day: dict, tomorrow: dict | None, streak: int, total_days: int) -> tuple[str, str]:
    subject = f"[Training] Rest day -- Week {_int(day['week_number'])}"

    if day.get("has_override") and day.get("session_detail"):
        rest_line = day["session_detail"]
    else:
        rest_line = "Rest day. Recovery is part of the plan."

    lines = [
        f"Day {_int(day['day_of_plan'])} of {total_days}  |  Week {_int(day['week_number'])}  |  {day['phase']}",
        "",
        rest_line,
    ]

    if day.get("has_override") and day.get("coaching_focus"):
        lines.append(day["coaching_focus"])

    if day.get("alternate_exercise"):
        lines.append(f"Alternative: {day['alternate_exercise']}")

    lines.append("")

    if tomorrow:
        lines += [
            f"Tomorrow ({tomorrow['day_of_week']}): {tomorrow['session_type']}",
            f"  {tomorrow['session_detail']}",
            "",
        ]

    lines += [
        f"Current streak: {streak} active day{'s' if streak != 1 else ''}",
        "",
        f"View your plan: {_SITE_URL}",
    ]

    return subject, "\n".join(lines)


def _send(recipient: str, subject: str, body: str) -> None:
    try:
        _ses.send_email(
            FromEmailAddress=_SENDER,
            Destination={"ToAddresses": [recipient]},
            Content={
                "Simple": {
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body":    {"Text": {"Data": body,    "Charset": "UTF-8"}},
                }
            },
        )
        logger.info("Email sent to %s: %s", recipient, subject)
    except ClientError as exc:
        logger.error("SES send failed: %s", exc.response["Error"]["Message"])
        raise


def _brief_user(user_id: str, recipient: str, today_str: str, dry_run: bool = False) -> dict | None:
    """Compose one user's briefing for today, scoped to their partition, and send
    it unless dry_run is set. Returns {subject, body, sent}, or None if today is
    outside that user's plan window.

    dry_run exists because the only way to exercise this Lambda is to invoke it
    with a test_date, and without it that puts a real briefing in a real inbox --
    which is exactly what happened while validating the Block 2 cutover.
    """
    plan_id = _active_plan_id(user_id)
    days = plan_merge.filter_to_plan(_query_user(user_id), plan_id)

    if _overrides_table:
        overrides = plan_merge.query_overrides(_overrides_table, user_id, plan_id)
        days = plan_merge.apply_overrides_to_items(days, overrides)
        logger.info("Applied %d active overrides", len(overrides))

    today_day = _day_for(days, today_str)
    if today_day is None:
        logger.info("No training day for %s (user %s) -- outside plan window, skipping",
                    today_str, user_id[:8])
        return None

    streak = _compute_streak(days, today_str)

    # Block length comes from the block itself, not a constant -- a new block of
    # a different length needs no code change here.
    total_days = len(days)

    if today_day["is_active_day"]:
        subject, body = _active_day_body(today_day, streak, total_days)
    else:
        tomorrow_day = _day_for(days, (date.fromisoformat(today_str) + timedelta(days=1)).isoformat())
        subject, body = _rest_day_body(today_day, tomorrow_day, streak, total_days)

    if dry_run:
        logger.info("[DRY RUN] composed briefing for %s, not sent: %s", today_str, subject)
        return {"subject": subject, "body": body, "sent": False}

    _send(recipient, subject, body)
    return {"subject": subject, "body": body, "sent": True}


def handler(event: dict, context) -> dict:
    today_str = event.get("test_date") or date.today().isoformat()
    dry_run = bool(event.get("dry_run"))
    logger.info("daily_email invoked for %s%s", today_str, " [DRY RUN]" if dry_run else "")

    # Single-recipient today. Multi-user fan-out (deferred) loops the users table
    # here -- resolving (user_id, email) pairs and calling _brief_user for each.
    result = _brief_user(_OWNER_USER_ID, _RECIPIENT, today_str, dry_run)

    if result is None:
        return {"statusCode": 200, "body": "outside plan window"}
    return {"statusCode": 200, "body": json.dumps(result)}
