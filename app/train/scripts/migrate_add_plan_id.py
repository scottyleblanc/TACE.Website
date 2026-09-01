"""
migrate_add_plan_id.py -- Stage 3.15 migration: give every plan row a training
block, and retire the tail of a block that was abandoned partway through.

Background. Until now a user held exactly one training plan, so every row in
training-plan-v2 and training-plan-overrides-v2 implicitly belonged to it. A
user can now work through several sequential blocks, so each row carries a
plan_id and the users record names the active one (active_plan_id).

plan_id is a plain attribute, NOT part of the key. Block date ranges never
overlap, so {user_id, date} stays unique across every block -- which is why
this is an in-place attribute add rather than a fourth new-table migration
like Stages 3.9 and 3.12.

Three independent operations, each safe to run on its own:

  --plan-id BLOCK [--until DATE]
      Backfill: tag rows that have no plan_id yet. Only ever writes to rows
      missing the attribute, so it is idempotent and can never relabel a row
      that is already correct. --until bounds it to rows on or before a date,
      so a later block's rows cannot be swept up by a re-run.

  --truncate-from DATE
      Delete rows dated on or after DATE from both tables. This retires the
      unlived tail of an abandoned block. Dry-run by default; --yes executes.
      [SEC-adjacent] Aborts outright if any candidate row carries completed or
      notes -- logged history is never deleted by this script, and a hit here
      means a human decides, not a --force flag.

  --set-active-plan BLOCK
      Point the users record at a block. The cutover step.

Usage:
    python app/train/scripts/migrate_add_plan_id.py --owner-sub <SUB> --plan-id block-01 --until 2026-08-31 --dry-run
    python app/train/scripts/migrate_add_plan_id.py --owner-sub <SUB> --plan-id block-01 --until 2026-08-31 --verify
    python app/train/scripts/migrate_add_plan_id.py --owner-sub <SUB> --truncate-from 2026-09-01
    python app/train/scripts/migrate_add_plan_id.py --owner-sub <SUB> --truncate-from 2026-09-01 --yes
    python app/train/scripts/migrate_add_plan_id.py --owner-sub <SUB> --set-active-plan block-02
"""

import argparse
import sys

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

PLAN_TABLE = "training-plan-v2"
OVERRIDES_TABLE = "training-plan-overrides-v2"
USERS_TABLE = "training-users"


def query_partition(table, user_id: str) -> list[dict]:
    """Every row in one user's partition, date-sorted."""
    items: list[dict] = []
    kwargs: dict = {"KeyConditionExpression": Key("user_id").eq(user_id)}
    while True:
        result = table.query(**kwargs)
        items.extend(result.get("Items", []))
        last = result.get("LastEvaluatedKey")
        if not last:
            break
        kwargs["ExclusiveStartKey"] = last
    return sorted(items, key=lambda d: d["date"])


def has_logged_state(item: dict) -> bool:
    """True if the athlete has recorded anything against this day. The guard
    that stops truncation from destroying real history."""
    return bool(item.get("completed")) or bool(str(item.get("notes", "")).strip())


# --- backfill ----------------------------------------------------------------

def backfill(table, label: str, user_id: str, plan_id: str, until: str | None, dry_run: bool) -> int:
    rows = query_partition(table, user_id)
    if until:
        rows = [r for r in rows if r["date"] <= until]

    pending = [r for r in rows if not r.get("plan_id")]
    already = len(rows) - len(pending)
    print(f"[INFO]  {label}: {len(rows)} row(s) in range, {already} already tagged, {len(pending)} to tag")

    written = 0
    for row in pending:
        if dry_run:
            print(f"  [DRY RUN] {label} {row['date']}  ->  plan_id={plan_id}")
            written += 1
            continue
        try:
            table.update_item(
                Key={"user_id": user_id, "date": row["date"]},
                UpdateExpression="SET plan_id = :pid",
                # Idempotent: a row tagged by an earlier run is left untouched
                # rather than overwritten, so a re-run can never relabel.
                ConditionExpression="attribute_not_exists(plan_id)",
                ExpressionAttributeValues={":pid": plan_id},
            )
            written += 1
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                continue
            print(f"[ERROR] {label} update failed for {row['date']}: {exc}", file=sys.stderr)
            raise
    return written


def verify_backfill(table, label: str, user_id: str, plan_id: str, until: str | None) -> bool:
    rows = query_partition(table, user_id)
    if until:
        rows = [r for r in rows if r["date"] <= until]

    untagged = [r["date"] for r in rows if not r.get("plan_id")]
    wrong = [r["date"] for r in rows if r.get("plan_id") and r["plan_id"] != plan_id]

    ok = True
    if untagged:
        print(f"[FAIL]  {label}: {len(untagged)} row(s) still untagged: {untagged[:10]}", file=sys.stderr)
        ok = False
    if wrong:
        print(f"[FAIL]  {label}: {len(wrong)} row(s) tagged to another block: {wrong[:10]}", file=sys.stderr)
        ok = False
    if ok:
        print(f"[OK]    {label}: all {len(rows)} row(s) tagged plan_id={plan_id}")
    return ok


# --- truncate ----------------------------------------------------------------

def truncate(plan_table, overrides_table, user_id: str, cutoff: str, execute: bool) -> bool:
    plan_rows = [r for r in query_partition(plan_table, user_id) if r["date"] >= cutoff]
    override_rows = [r for r in query_partition(overrides_table, user_id) if r["date"] >= cutoff]

    print(f"[INFO]  Truncating from {cutoff} onward")
    print(f"[INFO]  {PLAN_TABLE}: {len(plan_rows)} candidate row(s)")
    print(f"[INFO]  {OVERRIDES_TABLE}: {len(override_rows)} candidate row(s)")

    logged = [r for r in plan_rows if has_logged_state(r)]
    if logged:
        print(
            f"\n[FAIL]  {len(logged)} candidate row(s) carry logged history and will NOT be deleted:",
            file=sys.stderr,
        )
        for row in logged:
            note = str(row.get("notes", "")).strip()
            marker = "completed" if row.get("completed") else ""
            marker = f"{marker}{' + ' if marker and note else ''}{'notes' if note else ''}"
            print(f"          {row['date']}  ({marker})", file=sys.stderr)
        print(
            "[FAIL]  Aborting. Move the cutoff past these dates, or clear them "
            "deliberately first -- this script will not delete logged history.",
            file=sys.stderr,
        )
        return False

    print("[OK]    No candidate row carries completed or notes -- safe to delete")

    if not execute:
        for row in plan_rows:
            print(f"  [DRY RUN] delete {PLAN_TABLE} {row['date']}")
        for row in override_rows:
            print(f"  [DRY RUN] delete {OVERRIDES_TABLE} {row['date']}")
        print("\n[INFO]  Dry run -- nothing deleted. Re-run with --yes to execute.")
        return True

    for table, rows, label in (
        (plan_table, plan_rows, PLAN_TABLE),
        (overrides_table, override_rows, OVERRIDES_TABLE),
    ):
        with table.batch_writer() as batch:
            for row in rows:
                batch.delete_item(Key={"user_id": user_id, "date": row["date"]})
        print(f"[OK]    {label}: deleted {len(rows)} row(s)")

    remaining_plan = [r for r in query_partition(plan_table, user_id) if r["date"] >= cutoff]
    remaining_ovr = [r for r in query_partition(overrides_table, user_id) if r["date"] >= cutoff]
    if remaining_plan or remaining_ovr:
        print(
            f"[FAIL]  {len(remaining_plan)} plan and {len(remaining_ovr)} override row(s) "
            f"still on/after {cutoff}",
            file=sys.stderr,
        )
        return False
    print(f"[OK]    Nothing remains on/after {cutoff} in either table")
    return True


# --- cutover -----------------------------------------------------------------

def set_active_plan(users_table, user_id: str, plan_id: str, dry_run: bool) -> None:
    if dry_run:
        print(f"  [DRY RUN] set active_plan_id={plan_id} on {USERS_TABLE}")
        return
    users_table.update_item(
        Key={"user_id": user_id},
        UpdateExpression="SET active_plan_id = :pid",
        ConditionExpression="attribute_exists(user_id)",
        ExpressionAttributeValues={":pid": plan_id},
    )
    print(f"[OK]    active_plan_id set to {plan_id}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage 3.15: backfill plan_id, truncate an abandoned block tail, set the active block."
    )
    parser.add_argument("--owner-sub", required=True, help="Owner's Cognito sub (the user_id partition key)")
    parser.add_argument("--plan-id", help="Backfill: tag untagged rows with this block id (e.g. block-01)")
    parser.add_argument("--until", help="Backfill: only tag rows on or before this ISO date")
    parser.add_argument("--truncate-from", help="Delete rows on/after this ISO date from both tables")
    parser.add_argument("--set-active-plan", help="Set active_plan_id on the users record")
    parser.add_argument("--profile", default="tace-aws-admin", help="AWS CLI profile name")
    parser.add_argument("--region", default="ca-central-1", help="AWS region")
    parser.add_argument("--dry-run", action="store_true", help="Print intended writes without making them")
    parser.add_argument("--verify", action="store_true", help="After backfill, assert every row in range is tagged")
    parser.add_argument("--yes", action="store_true", help="Required to actually execute --truncate-from")
    args = parser.parse_args()

    if not any((args.plan_id, args.truncate_from, args.set_active_plan)):
        parser.error("nothing to do: pass --plan-id, --truncate-from, or --set-active-plan")

    print(f"[INFO]  Connecting to DynamoDB in {args.region} (profile: {args.profile})")
    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    dynamodb = session.resource("dynamodb")
    plan_table = dynamodb.Table(PLAN_TABLE)
    overrides_table = dynamodb.Table(OVERRIDES_TABLE)
    users_table = dynamodb.Table(USERS_TABLE)

    if args.dry_run:
        print("[INFO]  Dry run -- no writes to DynamoDB\n")

    if args.plan_id:
        print(f"[INFO]  Backfill plan_id={args.plan_id}" + (f" (rows <= {args.until})" if args.until else " (all rows)"))
        tagged = backfill(plan_table, PLAN_TABLE, args.owner_sub, args.plan_id, args.until, args.dry_run)
        tagged += backfill(overrides_table, OVERRIDES_TABLE, args.owner_sub, args.plan_id, args.until, args.dry_run)
        print(f"[DONE]  {'Would tag' if args.dry_run else 'Tagged'}: {tagged} row(s)\n")

        if args.verify and not args.dry_run:
            print("[INFO]  Verifying backfill...")
            ok = verify_backfill(plan_table, PLAN_TABLE, args.owner_sub, args.plan_id, args.until)
            ok = verify_backfill(overrides_table, OVERRIDES_TABLE, args.owner_sub, args.plan_id, args.until) and ok
            if not ok:
                print("[DONE]  Verification FAILED", file=sys.stderr)
                sys.exit(1)
            print("[DONE]  Verification passed\n")

    if args.truncate_from:
        if not truncate(plan_table, overrides_table, args.owner_sub, args.truncate_from,
                        execute=args.yes and not args.dry_run):
            sys.exit(1)
        print()

    if args.set_active_plan:
        set_active_plan(users_table, args.owner_sub, args.set_active_plan, args.dry_run)


if __name__ == "__main__":
    main()
