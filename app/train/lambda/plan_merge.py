"""
plan_merge.py -- shared override-merge logic for the training plan.

Single source of truth for applying the physio override layer
(training-plan-overrides-v2) on top of seed training-plan-v2 rows. Reused by
days_api.py, daily_email.py, and tracker_coach.py so all three consumers show
an identical merged view -- the coach must never read the raw seed alone, or
it will contradict the physio-adjusted plan the user sees in the app and email.

training-plan-overrides-v2 is partitioned by user_id (PK user_id, SK date),
same as training-plan-v2 -- every query here is scoped to the caller, never a
table-wide scan, so one user's physio overrides can never apply to (or leak
into) another user's plan.

Deployed by being zipped alongside each caller's own file (zip -j junks paths,
so this module lands at the same flat level and imports as a top-level module).
"""

from boto3.dynamodb.conditions import Key

# Fields applied from the override item when present and non-empty.
OVERRIDE_FIELDS = (
    "session_type", "session_detail", "coaching_focus",
    "run_interval_minutes", "run_walk_ratio", "session_minutes_target",
    "alternate_exercise",
)

# Fields always stored in the override item (even as empty string).
# An empty string here means "clear this field from the merged result"
# rather than "inherit from the seed row."
CLEARABLE_FIELDS = frozenset(("run_walk_ratio", "alternate_exercise"))


def merge_override(seed_item: dict, override_item: dict) -> dict:
    merged = dict(seed_item)
    merged["has_override"] = True
    merged["original_session_type"] = seed_item.get("session_type", "")
    merged["original_session_detail"] = seed_item.get("session_detail", "")

    for field in OVERRIDE_FIELDS:
        if field not in override_item:
            continue  # not in override item -- inherit from seed
        val = override_item[field]
        if field in CLEARABLE_FIELDS:
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


def query_overrides(overrides_table, user_id: str) -> dict:
    """Query the caller's overrides only; returns {date: override_item} for
    active overrides. Never a table-wide scan -- overrides are partitioned by
    user_id exactly like the plan table, so this can't read another user's
    physio adjustments."""
    overrides: dict = {}
    kwargs: dict = {"KeyConditionExpression": Key("user_id").eq(user_id)}
    while True:
        result = overrides_table.query(**kwargs)
        for item in result.get("Items", []):
            if item.get("override_active"):
                overrides[item["date"]] = item
        last = result.get("LastEvaluatedKey")
        if not last:
            break
        kwargs["ExclusiveStartKey"] = last
    return overrides


def apply_override_to_item(seed_item: dict, overrides: dict) -> dict:
    override = overrides.get(seed_item["date"])
    if override:
        return merge_override(seed_item, override)
    return seed_item


def apply_overrides_to_items(items: list[dict], overrides: dict) -> list[dict]:
    return [apply_override_to_item(item, overrides) for item in items]
