"""
daily_email.py -- EventBridge-triggered Lambda for daily training briefing emails.

Fires daily at 11:00 UTC (7am EDT) via EventBridge rule tracker-daily-email.
Sends one of two email formats depending on whether today is an active day or rest day.

Active day:  session type, detail, coaching focus, minutes, run:walk ratio, streak, link
Rest day:    recovery note, tomorrow's session preview, streak, link

If OVERRIDES_TABLE env var is set, override rows are merged into the day data
before the email is composed, so the email always reflects the adjusted plan.

Environment variables:
  DYNAMODB_TABLE  -- DynamoDB table name (training-plan)
  SES_SENDER      -- From address (noreply@tacedata.ca)
  RECIPIENT       -- To address (scott.leblanc@tacedata.ca)
  OVERRIDES_TABLE -- Optional. DynamoDB overrides table name (training-plan-overrides)
  SITE_URL        -- Optional override for the tracker link (default: https://train.tacedata.ca/)
"""

import json
import logging
import os
from datetime import date, timedelta
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_TABLE_NAME = os.environ["DYNAMODB_TABLE"]
_SENDER     = os.environ["SES_SENDER"]
_RECIPIENT  = os.environ["RECIPIENT"]
_SITE_URL   = os.environ.get("SITE_URL", "https://train.tacedata.ca/")

_OVERRIDES_TABLE_NAME = os.environ.get("OVERRIDES_TABLE")

_dynamodb        = boto3.resource("dynamodb")
_table           = _dynamodb.Table(_TABLE_NAME)
_overrides_table = _dynamodb.Table(_OVERRIDES_TABLE_NAME) if _OVERRIDES_TABLE_NAME else None
_ses             = boto3.client("sesv2", region_name="ca-central-1")

_OVERRIDE_FIELDS = (
    "session_type", "session_detail", "coaching_focus",
    "run_interval_minutes", "run_walk_ratio", "session_minutes_target",
    "alternate_exercise",
)
_CLEARABLE_FIELDS = frozenset(("run_walk_ratio", "alternate_exercise"))


def _scan_all() -> list[dict]:
    items: list[dict] = []
    kwargs: dict = {}
    while True:
        result = _table.scan(**kwargs)
        items.extend(result.get("Items", []))
        last = result.get("LastEvaluatedKey")
        if not last:
            break
        kwargs["ExclusiveStartKey"] = last
    return sorted(items, key=lambda d: d["date"])


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


def _merge_override(seed_item: dict, override_item: dict) -> dict:
    merged = dict(seed_item)
    merged["has_override"] = True
    merged["original_session_type"] = seed_item.get("session_type", "")

    for field in _OVERRIDE_FIELDS:
        if field not in override_item:
            continue
        val = override_item[field]
        if field in _CLEARABLE_FIELDS:
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


def _apply_overrides(days: list[dict], overrides: dict) -> list[dict]:
    result = []
    for day in days:
        override = overrides.get(day["date"])
        if override:
            result.append(_merge_override(day, override))
        else:
            result.append(day)
    return result


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


def _active_day_body(day: dict, streak: int) -> tuple[str, str]:
    session_type = day["session_type"]
    prov_prefix  = "[PROVISIONAL] " if day.get("provisional") else ""
    subject = f"[Training] {prov_prefix}{session_type} -- Day {_int(day['day_of_plan'])} of 105"

    lines = [
        f"Day {_int(day['day_of_plan'])} of 105  |  Week {_int(day['week_number'])}  |  {day['phase']}",
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


def _rest_day_body(day: dict, tomorrow: dict | None, streak: int) -> tuple[str, str]:
    subject = f"[Training] Rest day -- Week {_int(day['week_number'])}"

    if day.get("has_override") and day.get("session_detail"):
        rest_line = day["session_detail"]
    else:
        rest_line = "Rest day. Recovery is part of the plan."

    lines = [
        f"Day {_int(day['day_of_plan'])} of 105  |  Week {_int(day['week_number'])}  |  {day['phase']}",
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


def handler(event: dict, context) -> dict:
    today_str  = event.get("test_date") or date.today().isoformat()
    logger.info("daily_email invoked for %s", today_str)

    days = _scan_all()

    if _overrides_table:
        overrides = _scan_overrides()
        days = _apply_overrides(days, overrides)
        logger.info("Applied %d active overrides", len(overrides))

    today_day = _day_for(days, today_str)

    if today_day is None:
        logger.info("No training day for %s -- outside plan window, skipping email", today_str)
        return {"statusCode": 200, "body": "outside plan window"}

    streak = _compute_streak(days, today_str)

    if today_day["is_active_day"]:
        subject, body = _active_day_body(today_day, streak)
    else:
        tomorrow_day = _day_for(days, (date.fromisoformat(today_str) + timedelta(days=1)).isoformat())
        subject, body = _rest_day_body(today_day, tomorrow_day, streak)

    try:
        _ses.send_email(
            FromEmailAddress=_SENDER,
            Destination={"ToAddresses": [_RECIPIENT]},
            Content={
                "Simple": {
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body":    {"Text": {"Data": body,    "Charset": "UTF-8"}},
                }
            },
        )
        logger.info("Email sent to %s: %s", _RECIPIENT, subject)
    except ClientError as exc:
        logger.error("SES send failed: %s", exc.response["Error"]["Message"])
        raise

    return {"statusCode": 200, "body": json.dumps({"subject": subject})}
