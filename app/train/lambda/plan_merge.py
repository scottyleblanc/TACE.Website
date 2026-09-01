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

Stage 3.15 added plan_id: one user now holds several sequential training
blocks, and both plan rows and override rows carry the block they belong to.
Because block date ranges never overlap, plan_id is a plain attribute rather
than part of the key -- {user_id, date} is still unique across every block.

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


def query_overrides(overrides_table, user_id: str, plan_id: str | None = None) -> dict:
    """Query the caller's overrides only; returns {date: override_item} for
    active overrides. Never a table-wide scan -- overrides are partitioned by
    user_id exactly like the plan table, so this can't read another user's
    physio adjustments.

    plan_id (Stage 3.15) narrows the result to one training block, so the merge
    dict stays small as blocks accumulate. The filter is deliberately lenient:
    a row with no plan_id at all is kept rather than dropped. Two reasons --
    it makes the code safe to deploy before the backfill has run, and it can't
    cause a wrong merge either way, because plan date ranges never overlap
    (that non-overlap is exactly why plan_id is a plain attribute here and not
    part of the key)."""
    overrides: dict = {}
    kwargs: dict = {"KeyConditionExpression": Key("user_id").eq(user_id)}
    while True:
        result = overrides_table.query(**kwargs)
        for item in result.get("Items", []):
            if not item.get("override_active"):
                continue
            if plan_id and item.get("plan_id") not in (None, plan_id):
                continue
            overrides[item["date"]] = item
        last = result.get("LastEvaluatedKey")
        if not last:
            break
        kwargs["ExclusiveStartKey"] = last
    return overrides


def filter_to_plan(items: list[dict], plan_id: str | None) -> list[dict]:
    """Narrow plan rows to one training block.

    plan_id=None means "no active block configured" and returns everything --
    the pre-Stage-3.15 behaviour, so an unset active_plan_id degrades to the
    old full-partition view rather than an empty dashboard. Rows with no
    plan_id are kept for the same deploy-ordering reason as query_overrides."""
    if not plan_id:
        return items
    return [i for i in items if i.get("plan_id") in (None, plan_id)]


def apply_override_to_item(seed_item: dict, overrides: dict) -> dict:
    override = overrides.get(seed_item["date"])
    if override:
        return merge_override(seed_item, override)
    return seed_item


def apply_overrides_to_items(items: list[dict], overrides: dict) -> list[dict]:
    return [apply_override_to_item(item, overrides) for item in items]
