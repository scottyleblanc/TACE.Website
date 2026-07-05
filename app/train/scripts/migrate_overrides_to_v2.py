"""
migrate_overrides_to_v2.py -- One-time migration partitioning the physio
override layer by user_id.

Copies every item from the single-user, date-keyed training-plan-overrides
table into the user_id-partitioned training-plan-overrides-v2 table (PK
user_id, SK date), adding the owner's Cognito `sub` as user_id. All other
attributes are carried across unchanged.

This closes a real gap left open at Stage 3.9: training-plan-overrides was
deliberately left date-keyed at the time ("single-user reference data"), but
that means it is global, un-partitioned reference data read by every caller
regardless of user_id -- a second user would see (and be affected by) the
first user's physio overrides. Must run before any second user is onboarded.

DynamoDB key schema is immutable, so this is a new-table copy, not an
in-place change. The put is an overwrite, so the script is idempotent and
safe to re-run.

Usage:
    python app/train/scripts/migrate_overrides_to_v2.py --owner-sub <SUB> --dry-run
    python app/train/scripts/migrate_overrides_to_v2.py --owner-sub <SUB>
    python app/train/scripts/migrate_overrides_to_v2.py --owner-sub <SUB> --verify
"""

import argparse
import sys

import boto3
from botocore.exceptions import ClientError

SOURCE_TABLE = "training-plan-overrides"
DEST_TABLE = "training-plan-overrides-v2"

# Fields that must survive the migration intact. Used by --verify.
_OVERRIDE_FIELDS = (
    "override_active", "provisional", "override_reason", "override_source",
    "override_created_date", "override_note", "session_type", "session_detail",
    "coaching_focus", "run_walk_ratio", "alternate_exercise",
    "run_interval_minutes", "session_minutes_target",
)


def scan_all(table) -> list[dict]:
    items: list[dict] = []
    kwargs: dict = {}
    while True:
        result = table.scan(**kwargs)
        items.extend(result.get("Items", []))
        last = result.get("LastEvaluatedKey")
        if not last:
            break
        kwargs["ExclusiveStartKey"] = last
    return sorted(items, key=lambda d: d["date"])


def migrate(source, dest, owner_sub: str, dry_run: bool) -> int:
    items = scan_all(source)
    print(f"[INFO]  {len(items)} items read from source")

    written = 0
    for item in items:
        new_item = dict(item)
        new_item["user_id"] = owner_sub

        if dry_run:
            active = "[ACTIVE]" if item.get("override_active") else "[INACTIVE]"
            print(f"  [DRY RUN] {item['date']}  {active}  {item.get('session_type', '(inherited)')}")
            written += 1
            continue

        try:
            dest.put_item(Item=new_item)
            print(f"[OK]    {item['date']}  ->  {{user_id: {owner_sub[:8]}..., date: {item['date']}}}")
            written += 1
        except ClientError as exc:
            print(f"[ERROR] put_item failed for {item['date']}: {exc}", file=sys.stderr)
            raise

    return written


def verify(source, dest, owner_sub: str) -> bool:
    """Assert row-count and field parity between source and dest."""
    src = {d["date"]: d for d in scan_all(source)}
    dst = {d["date"]: d for d in scan_all(dest) if d.get("user_id") == owner_sub}

    ok = True

    if len(src) != len(dst):
        print(f"[FAIL]  count mismatch: source {len(src)} vs dest {len(dst)}", file=sys.stderr)
        ok = False
    else:
        print(f"[OK]    count parity: {len(src)} = {len(dst)}")

    missing = sorted(set(src) - set(dst))
    if missing:
        print(f"[FAIL]  {len(missing)} date(s) missing in dest: {missing}", file=sys.stderr)
        ok = False

    mismatches = 0
    for date_str, src_item in src.items():
        dst_item = dst.get(date_str)
        if dst_item is None:
            continue
        for field in _OVERRIDE_FIELDS:
            if src_item.get(field) != dst_item.get(field):
                print(
                    f"[FAIL]  {date_str} field '{field}': "
                    f"source {src_item.get(field)!r} != dest {dst_item.get(field)!r}",
                    file=sys.stderr,
                )
                mismatches += 1
                ok = False

    if ok:
        print(f"[OK]    field parity across all {len(src)} items")
    else:
        print(f"[FAIL]  {mismatches} field mismatch(es)", file=sys.stderr)

    return ok


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate training-plan-overrides (date-keyed) to training-plan-overrides-v2 (user_id + date)."
    )
    parser.add_argument("--owner-sub", required=True, help="Owner's Cognito sub (the user_id partition key)")
    parser.add_argument("--source", default=SOURCE_TABLE, help="Source table name")
    parser.add_argument("--dest", default=DEST_TABLE, help="Destination table name")
    parser.add_argument("--profile", default="tace-aws-admin", help="AWS CLI profile name")
    parser.add_argument("--region", default="ca-central-1", help="AWS region")
    parser.add_argument("--dry-run", action="store_true", help="Print items without writing to DynamoDB")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="After migrating, assert row-count and field parity (source vs dest)",
    )
    args = parser.parse_args()

    if not args.owner_sub.strip():
        print("[ERROR] --owner-sub must be a non-empty Cognito sub", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO]  Connecting to DynamoDB in {args.region} (profile: {args.profile})")
    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    dynamodb = session.resource("dynamodb")
    source = dynamodb.Table(args.source)
    dest = dynamodb.Table(args.dest)

    print(f"[INFO]  {args.source}  ->  {args.dest}  (user_id = {args.owner_sub})")
    if args.dry_run:
        print("[INFO]  Dry run -- no writes to DynamoDB\n")

    written = migrate(source, dest, args.owner_sub, args.dry_run)
    print(f"\n[DONE]  {'Would write' if args.dry_run else 'Wrote'}: {written} items")

    if args.verify and not args.dry_run:
        print("\n[INFO]  Verifying parity...")
        if not verify(source, dest, args.owner_sub):
            print("[DONE]  Verification FAILED -- do not proceed to cutover", file=sys.stderr)
            sys.exit(1)
        print("[DONE]  Verification passed")


if __name__ == "__main__":
    main()
