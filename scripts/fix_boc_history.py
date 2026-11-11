"""
fix_boc_history.py — Correct the `boc` attribute on every DynamoDB snapshot

Before the v3.2.2 fix, the Lambda read BoC Valet `recent=10` results as oldest-first
when they are newest-first, so every live snapshot stored the rate from ~9 business
days earlier. This script recomputes the correct rate for every SNAPSHOT item from
the authoritative Valet date-range series and rewrites only the `boc` attribute.

The correct rate for a snapshot is the latest V39079 observation dated on or before
the snapshot's UTC calendar date (the same day bucketing generate_history_files uses).

Usage:
    python scripts/fix_boc_history.py            # dry run — report only, no writes
    python scripts/fix_boc_history.py --apply    # back up originals, then rewrite

Requirements:
    pip install boto3
    AWS profile tace-aws-admin must be configured and authenticated.

After --apply, regenerate history files by invoking the Lambda with
{"force_history": true}.
"""

import argparse
import bisect
import json
import os
import tempfile
import urllib.request
from datetime import date, datetime, timedelta, timezone


DYNAMODB_TABLE  = "econ-indicators-history"
DYNAMODB_REGION = "ca-central-1"
AWS_PROFILE     = "tace-aws-admin"
BOC_BASE        = "https://www.bankofcanada.ca/valet"
LOOKBACK_MARGIN_DAYS = 30  # extra Valet history before the earliest snapshot


# ── Pure logic (unit-tested) ──────────────────────────────────────────────────

def parse_boc_observations(valet_response):
    """Valet V39079 response -> list of (date_str, rate) sorted oldest->newest.
    Sorts explicitly: Valet ordering differs between `recent=N` and date-range queries."""
    return sorted(
        (
            (o["d"], round(float(o["V39079"]["v"]), 4))
            for o in valet_response["observations"]
            if o.get("V39079", {}).get("v")
        ),
        key=lambda t: t[0],
    )


def rate_on(day, observations):
    """Rate in effect on `day` (YYYY-MM-DD): latest observation dated <= day.
    Returns None if `day` precedes the first observation."""
    dates = [d for d, _ in observations]
    idx   = bisect.bisect_right(dates, day) - 1
    return observations[idx][1] if idx >= 0 else None


def plan_corrections(snapshots, observations):
    """Compare each snapshot's stored boc against the correct rate.
    snapshots: iterable of dicts with 'ts' and optional 'boc' (string or number).
    Returns (corrections, stats) where corrections is a list of
    {'ts', 'old', 'new'} for items whose stored value is wrong."""
    corrections = []
    stats = {"checked": 0, "correct": 0, "wrong": 0, "missing_boc": 0, "no_reference": 0}
    for item in snapshots:
        if "boc" not in item:
            stats["missing_boc"] += 1
            continue
        stats["checked"] += 1
        correct = rate_on(item["ts"][:10], observations)
        if correct is None:
            stats["no_reference"] += 1
            continue
        stored = round(float(item["boc"]), 4)
        if stored == correct:
            stats["correct"] += 1
        else:
            stats["wrong"] += 1
            corrections.append({"ts": item["ts"], "old": stored, "new": correct})
    return corrections, stats


# ── I/O ───────────────────────────────────────────────────────────────────────

def http_get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "tacedata-boc-fix/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def fetch_boc_observations(start_date):
    today = datetime.now(timezone.utc).date()
    d = http_get(f"{BOC_BASE}/observations/V39079/json?start_date={start_date}&end_date={today}")
    return parse_boc_observations(d)


def get_table():
    import boto3  # noqa: PLC0415
    session = boto3.Session(profile_name=AWS_PROFILE)
    return session.resource("dynamodb", region_name=DYNAMODB_REGION).Table(DYNAMODB_TABLE)


def load_snapshots(table):
    from boto3.dynamodb.conditions import Key  # noqa: PLC0415
    items  = []
    kwargs = {
        "KeyConditionExpression":   Key("pk").eq("SNAPSHOT"),
        "ProjectionExpression":     "ts, boc",
    }
    while True:
        resp = table.query(**kwargs)
        items.extend(resp.get("Items", []))
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break
        kwargs["ExclusiveStartKey"] = last_key
    return items


def apply_corrections(table, corrections):
    for c in corrections:
        table.update_item(
            Key={"pk": "SNAPSHOT", "ts": c["ts"]},
            UpdateExpression="SET boc = :v",
            ConditionExpression="attribute_exists(ts)",
            ExpressionAttributeValues={":v": str(c["new"])},
        )


def summarize_ranges(corrections):
    """Group corrections by (old -> new) and UTC date span for a readable report."""
    groups = {}
    for c in corrections:
        key = (c["old"], c["new"])
        day = c["ts"][:10]
        lo, hi, n = groups.get(key, (day, day, 0))
        groups[key] = (min(lo, day), max(hi, day), n + 1)
    return groups


def main():
    parser = argparse.ArgumentParser(description="Correct boc values on DynamoDB snapshots.")
    parser.add_argument("--apply", action="store_true", help="write corrections (default: dry run)")
    args = parser.parse_args()

    table = get_table()
    print("Loading snapshots...")
    snapshots = load_snapshots(table)
    if not snapshots:
        print("No snapshots found.")
        return
    earliest = min(s["ts"][:10] for s in snapshots)
    start    = date.fromisoformat(earliest) - timedelta(days=LOOKBACK_MARGIN_DAYS)
    print(f"  {len(snapshots)} snapshots, earliest {earliest}")

    print(f"Fetching BoC V39079 from {start}...")
    observations = fetch_boc_observations(start)
    print(f"  {len(observations)} observations")

    corrections, stats = plan_corrections(snapshots, observations)
    print(f"\nChecked: {stats['checked']}  Correct: {stats['correct']}  Wrong: {stats['wrong']}  "
          f"Missing boc: {stats['missing_boc']}  No reference rate: {stats['no_reference']}")
    for (old, new), (lo, hi, n) in sorted(summarize_ranges(corrections).items(), key=lambda kv: kv[1][0]):
        print(f"  {old:.2f} -> {new:.2f}  {n:5d} items  {lo} .. {hi}")

    if not args.apply:
        print("\n[DRY RUN] No changes written. Re-run with --apply to correct.")
        return
    if not corrections:
        print("\nNothing to correct.")
        return

    stamp  = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = os.path.join(tempfile.gettempdir(), f"boc-history-backup-{stamp}.json")
    with open(backup, "w", encoding="utf-8") as f:
        json.dump(corrections, f, indent=1)
    print(f"\n[BACKUP] Original values written to {backup}")

    apply_corrections(table, corrections)
    print(f"[DONE] {len(corrections)} snapshots corrected.")
    print('Next: invoke the Lambda with {"force_history": true} to regenerate history files.')


if __name__ == "__main__":
    main()
