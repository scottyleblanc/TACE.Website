"""
seed_overrides.py -- Create and seed the training-plan-overrides DynamoDB table.

Creates the table (PAY_PER_REQUEST) if it does not exist, waits for it to
become ACTIVE, then loads all override rows from dev/training_plan_overrides.csv.

Safe to re-run -- uses put_item (upsert), so existing rows are replaced.

Usage:
    python app/train/scripts/seed_overrides.py
    python app/train/scripts/seed_overrides.py --dry-run
    python app/train/scripts/seed_overrides.py --profile tace-aws-admin --region ca-central-1
"""

import argparse
import csv
import sys
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

TABLE_NAME = "training-plan-overrides"

_REPO_ROOT = Path(__file__).resolve().parents[3]
OVERRIDES_CSV = _REPO_ROOT / "dev" / "training_plan_overrides.csv"

# Fields always stored in the override item (even as empty string), so the
# merge function can distinguish "explicitly cleared" from "not covered".
_CLEARABLE_FIELDS = ("run_walk_ratio", "alternate_exercise")


def _parse_bool(value: str) -> bool:
    return value.strip().upper() == "TRUE"


def _nullable_int(value: str) -> int | None:
    s = value.strip()
    return int(s) if s else None


def build_item(row: dict) -> dict:
    item: dict = {
        "date":                 row["date"].strip(),
        "week_number":          int(row["week_number"]),
        "override_active":      _parse_bool(row["override_active"]),
        "provisional":          _parse_bool(row["provisional"]),
        "override_reason":      row["override_reason"].strip(),
        "override_source":      row["override_source"].strip(),
        "override_created_date": row["override_created_date"].strip(),
        "override_note":        row["override_note"].strip(),
        # Always stored so the merge layer can clear them from the seed item
        # when the override row intentionally leaves them blank.
        "run_walk_ratio":       row["run_walk_ratio"].strip(),
        "alternate_exercise":   row["alternate_exercise"].strip(),
    }

    for str_field in ("session_type", "session_detail", "coaching_focus"):
        val = row[str_field].strip()
        if val:
            item[str_field] = val

    for int_field in ("run_interval_minutes", "session_minutes_target"):
        val = _nullable_int(row[int_field])
        if val is not None:
            item[int_field] = val

    return item


def seed_table(table, items: list[dict], dry_run: bool) -> int:
    seeded = 0
    for item in items:
        date = item["date"]
        if dry_run:
            active = "[ACTIVE]" if item["override_active"] else "[INACTIVE]"
            prov   = " [PROVISIONAL]" if item.get("provisional") else ""
            print(f"  [DRY RUN] {date}  {active}{prov}  {item.get('session_type', '(inherited)')}")
            seeded += 1
            continue

        try:
            table.put_item(Item=item)
            prov = " [PROVISIONAL]" if item.get("provisional") else ""
            print(f"[OK]    {date}{prov}  {item.get('session_type', '(inherited)')}")
            seeded += 1
        except ClientError as exc:
            print(f"[ERROR] put_item failed for {date}: {exc}", file=sys.stderr)
            raise

    return seeded


def _ensure_table(client, table_name: str) -> None:
    try:
        status = client.describe_table(TableName=table_name)["Table"]["TableStatus"]
        print(f"[INFO]  Table '{table_name}' already exists (status: {status})")
        if status != "ACTIVE":
            print("[INFO]  Waiting for table to become ACTIVE...")
            _wait_active(client, table_name)
        return
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "ResourceNotFoundException":
            raise

    print(f"[INFO]  Creating table '{table_name}'...")
    client.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "date", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "date", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    print("[INFO]  Waiting for table to become ACTIVE...")
    _wait_active(client, table_name)


def _wait_active(client, table_name: str, max_attempts: int = 30) -> None:
    for _ in range(max_attempts):
        time.sleep(2)
        status = client.describe_table(TableName=table_name)["Table"]["TableStatus"]
        if status == "ACTIVE":
            print(f"[INFO]  Table '{table_name}' is ACTIVE")
            return
    raise RuntimeError(f"Table '{table_name}' did not become ACTIVE within {max_attempts * 2}s")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create and seed the training-plan-overrides DynamoDB table."
    )
    parser.add_argument("--profile", default="tace-aws-admin", help="AWS CLI profile name")
    parser.add_argument("--region", default="ca-central-1", help="AWS region")
    parser.add_argument("--table", default=TABLE_NAME, help="DynamoDB table name")
    parser.add_argument("--dry-run", action="store_true", help="Print items without writing to DynamoDB")
    args = parser.parse_args()

    if not OVERRIDES_CSV.exists():
        print(f"[ERROR] CSV not found: {OVERRIDES_CSV}", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO]  Loading overrides from {OVERRIDES_CSV.name}")
    items: list[dict] = []
    with open(OVERRIDES_CSV, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            items.append(build_item(row))

    print(f"[INFO]  {len(items)} override rows loaded from CSV")

    if args.dry_run:
        print("[INFO]  Dry run -- no writes to DynamoDB\n")
        seeded = seed_table(None, items, dry_run=True)
        print(f"\n[DONE]  Would write: {seeded}  Total: {len(items)}")
        return

    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    client  = session.client("dynamodb")
    dynamodb = session.resource("dynamodb")

    _ensure_table(client, args.table)

    table = dynamodb.Table(args.table)
    seeded = seed_table(table, items, dry_run=False)
    print(f"\n[DONE]  Seeded: {seeded}  Total: {len(items)}")


if __name__ == "__main__":
    main()
