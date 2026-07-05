"""
migrate_to_v2.py -- One-time migration for the Stage 3.9 identity foundation.

Copies every item from the single-user, date-keyed training-plan table into the
user_id-partitioned training-plan-v2 table (PK user_id, SK date), adding the
owner's Cognito `sub` as user_id. All other attributes -- including user state
(completed, completed_date, notes) -- are carried across unchanged.

DynamoDB key schema is immutable, so this is a new-table copy, not an in-place
change. The put is an overwrite, so the script is idempotent and safe to re-run
(e.g. to capture a late write after the DYNAMODB_TABLE env-var flip -- see the
[WRITE FREEZE] note in runbook-tracker.md Step 44).

The overrides table (training-plan-overrides) is migrated separately -- see
migrate_overrides_to_v2.py.

Usage:
    python app/train/scripts/migrate_to_v2.py --owner-sub <SUB> --dry-run
    python app/train/scripts/migrate_to_v2.py --owner-sub <SUB>
    python app/train/scripts/migrate_to_v2.py --owner-sub <SUB> --verify
    python app/train/scripts/migrate_to_v2.py --owner-sub <SUB> \
        --source training-plan --dest training-plan-v2 \
        --profile tace-aws-admin --region ca-central-1
"""

import argparse
import sys

import boto3
from botocore.exceptions import ClientError

SOURCE_TABLE = "training-plan"
DEST_TABLE = "training-plan-v2"

# User-state fields that must survive the migration intact. Used by --verify.
_USER_STATE_FIELDS = ("completed", "completed_date", "notes")


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
            state = " ".join(
                f"{f}={item[f]!r}" for f in _USER_STATE_FIELDS if f in item
            )
            print(f"  [DRY RUN] {item['date']}  {item.get('session_type', '')}  {state}")
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
    """Assert row-count and user-state parity between source and dest."""
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
        print(f"[FAIL]  {len(missing)} date(s) missing in dest: {missing[:5]}...", file=sys.stderr)
        ok = False

    mismatches = 0
    for date_str, src_item in src.items():
        dst_item = dst.get(date_str)
        if dst_item is None:
            continue
        for field in _USER_STATE_FIELDS:
            if src_item.get(field) != dst_item.get(field):
                print(
                    f"[FAIL]  {date_str} field '{field}': "
                    f"source {src_item.get(field)!r} != dest {dst_item.get(field)!r}",
                    file=sys.stderr,
                )
                mismatches += 1
                ok = False

    if ok:
        print(f"[OK]    user-state parity across all {len(src)} items ({', '.join(_USER_STATE_FIELDS)})")
    else:
        print(f"[FAIL]  {mismatches} user-state mismatch(es)", file=sys.stderr)

    return ok


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate training-plan (date-keyed) to training-plan-v2 (user_id + date)."
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
        help="After migrating, assert row-count and user-state parity (source vs dest)",
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
