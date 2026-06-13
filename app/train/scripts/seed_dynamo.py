"""
seed_dynamo.py -- One-time DynamoDB seeder for the training-plan table.

Reads training_plan_days.csv and training_plan_weeks.csv from dev/ and
loads all 105 days into DynamoDB. Safe to re-run -- re-seeds unchanged
items unless --preserve-state is passed (which skips completed days).

Usage:
    python app/train/scripts/seed_dynamo.py
    python app/train/scripts/seed_dynamo.py --dry-run
    python app/train/scripts/seed_dynamo.py --preserve-state
    python app/train/scripts/seed_dynamo.py --profile tace-aws-admin --region ca-central-1
"""

import argparse
import csv
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

TABLE_NAME = "training-plan"

_REPO_ROOT = Path(__file__).resolve().parents[3]
DAYS_CSV = _REPO_ROOT / "dev" / "training_plan_days.csv"
WEEKS_CSV = _REPO_ROOT / "dev" / "training_plan_weeks.csv"


def _parse_bool(value: str) -> bool:
    return value.strip().upper() == "TRUE"


def _nullable_str(value: str) -> str | None:
    s = value.strip()
    return s if s else None


def _nullable_int(value: str) -> int | None:
    s = value.strip()
    return int(s) if s else None


def load_weeks(path: Path) -> dict[int, dict]:
    weeks: dict[int, dict] = {}
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            wn = int(row["week_number"])
            weeks[wn] = {
                "weekly_focus": row["weekly_focus"].strip(),
                "week_start_date": row["start_date"].strip(),
                "week_end_date": row["end_date"].strip(),
                "week_active_days": int(row["active_days"]),
                "week_run_days": int(row["run_days"]),
                "week_long_run_minutes": _nullable_str(row["long_run_minutes"]),
                "week_long_run_ratio": _nullable_str(row["long_run_ratio"]),
                "week_steady_run_minutes": _nullable_str(row["steady_run_minutes"]),
            }
    return weeks


def build_item(row: dict, week: dict) -> dict:
    item: dict = {
        "date": row["date"].strip(),
        "day_of_week": row["day_of_week"].strip(),
        "week_number": int(row["week_number"]),
        "day_of_plan": int(row["day_of_plan"]),
        "phase": row["phase"].strip(),
        "session_type": row["session_type"].strip(),
        "is_active_day": _parse_bool(row["is_active_day"]),
        "is_run_day": _parse_bool(row["is_run_day"]),
        "session_minutes_target": int(row["session_minutes_target"]),
        "session_detail": row["session_detail"].strip(),
        "coaching_focus": row["coaching_focus"].strip(),
        # Week-level fields joined in
        "weekly_focus": week["weekly_focus"],
        "week_start_date": week["week_start_date"],
        "week_end_date": week["week_end_date"],
        "week_active_days": week["week_active_days"],
        "week_run_days": week["week_run_days"],
        # USER-STATE defaults
        "completed": False,
    }

    # Nullable SEED columns -- omit attribute entirely when empty
    run_interval = _nullable_int(row["run_interval_minutes"])
    if run_interval is not None:
        item["run_interval_minutes"] = run_interval

    run_walk_ratio = _nullable_str(row["run_walk_ratio"])
    if run_walk_ratio is not None:
        item["run_walk_ratio"] = run_walk_ratio

    # Nullable week-level columns -- omit "-" (race week placeholder) and empty
    long_run = week["week_long_run_minutes"]
    if long_run and long_run != "-":
        item["week_long_run_minutes"] = long_run

    long_run_ratio = week["week_long_run_ratio"]
    if long_run_ratio and long_run_ratio != "-":
        item["week_long_run_ratio"] = long_run_ratio

    steady = week["week_steady_run_minutes"]
    if steady and steady != "-":
        item["week_steady_run_minutes"] = steady

    # completed_date and notes are omitted (null) on initial seed

    return item


def seed_table(
    table,
    items: list[dict],
    preserve_state: bool,
    dry_run: bool,
) -> tuple[int, int]:
    seeded = 0
    skipped = 0

    for item in items:
        date = item["date"]

        if dry_run:
            active = "[ACTIVE]" if item["is_active_day"] else "[REST]  "
            print(f"  [DRY RUN] {date}  W{item['week_number']:02d}  D{item['day_of_plan']:03d}  {active}  {item['session_type']}")
            seeded += 1
            continue

        if preserve_state:
            try:
                existing = table.get_item(Key={"date": date}).get("Item")
            except ClientError as exc:
                print(f"[ERROR] get_item failed for {date}: {exc}", file=sys.stderr)
                raise
            if existing and existing.get("completed"):
                print(f"[SKIP]  {date} -- completed, user state preserved")
                skipped += 1
                continue

        try:
            table.put_item(Item=item)
            print(f"[OK]    {date}  W{item['week_number']:02d}  D{item['day_of_plan']:03d}  {item['session_type']}")
            seeded += 1
        except ClientError as exc:
            print(f"[ERROR] put_item failed for {date}: {exc}", file=sys.stderr)
            raise

    return seeded, skipped


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed the training-plan DynamoDB table from the plan CSVs."
    )
    parser.add_argument("--profile", default="tace-aws-admin", help="AWS CLI profile name")
    parser.add_argument("--region", default="ca-central-1", help="AWS region")
    parser.add_argument("--table", default=TABLE_NAME, help="DynamoDB table name")
    parser.add_argument(
        "--preserve-state",
        action="store_true",
        help="Skip days where completed=True (preserves user progress on re-seed)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print items without writing to DynamoDB",
    )
    args = parser.parse_args()

    for path in (DAYS_CSV, WEEKS_CSV):
        if not path.exists():
            print(f"[ERROR] CSV not found: {path}", file=sys.stderr)
            sys.exit(1)

    print(f"[INFO]  Loading weeks from {WEEKS_CSV.name}")
    weeks = load_weeks(WEEKS_CSV)

    print(f"[INFO]  Loading days from {DAYS_CSV.name}")
    items: list[dict] = []
    with open(DAYS_CSV, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            wn = int(row["week_number"])
            items.append(build_item(row, weeks[wn]))

    print(f"[INFO]  {len(items)} days loaded from CSV")

    if args.dry_run:
        print("[INFO]  Dry run -- no writes to DynamoDB\n")
        seeded, skipped = seed_table(None, items, False, dry_run=True)
        print(f"\n[DONE]  Would write: {seeded}  Total: {len(items)}")
        return

    print(f"[INFO]  Connecting to DynamoDB table '{args.table}' in {args.region} (profile: {args.profile})")
    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    dynamodb = session.resource("dynamodb")
    table = dynamodb.Table(args.table)

    seeded, skipped = seed_table(table, items, args.preserve_state, dry_run=False)
    print(f"\n[DONE]  Seeded: {seeded}  Skipped: {skipped}  Total: {len(items)}")


if __name__ == "__main__":
    main()
