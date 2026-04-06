"""
backfill_history.py — One-time DynamoDB history backfill

Fetches up to 180 days of historical data from each API source and writes
one DynamoDB item per trading day. Run once locally after Stage 2.5 setup.

Usage:
    python scripts/backfill_history.py

Requirements:
    pip install boto3 requests
    AWS profile tace-aws-admin must be configured and authenticated.

Environment variables required (set in shell before running):
    TD_API_KEY   — Twelve Data API key
    FRED_API_KEY — FRED API key

The script is non-destructive: it skips any date that already has an item
in DynamoDB (pk=SNAPSHOT, ts=<date>T12:00:00Z).
"""

import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from decimal import Decimal


# ── Config ─────────────────────────────────────────────────────────────────────

TD_API_KEY   = os.environ["TD_API_KEY"]
FRED_API_KEY = os.environ["FRED_API_KEY"]

DYNAMODB_TABLE = "econ-indicators-history"
DYNAMODB_REGION = "ca-central-1"
AWS_PROFILE = "tace-aws-admin"

BACKFILL_DAYS = 180

TD_BASE   = "https://api.twelvedata.com"
BOC_BASE  = "https://www.bankofcanada.ca/valet"
STATCAN   = "https://www150.statcan.gc.ca/t1/wds/rest"
FRED_BASE = "https://api.stlouisfed.org/fred"
YF_BASE   = "https://query1.finance.yahoo.com/v8/finance/chart"


# ── HTTP helpers ───────────────────────────────────────────────────────────────

def http_get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "tacedata-backfill/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def http_post(url, body, timeout=20):
    data = json.dumps(body).encode()
    req  = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json", "User-Agent": "tacedata-backfill/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


# ── Historical fetchers ────────────────────────────────────────────────────────

def fetch_tsx_history():
    """TSX Composite from Yahoo Finance — 1 year of daily closes."""
    print("  Fetching TSX (Yahoo Finance, 1y)...")
    url = f"{YF_BASE}/%5EGSPTSE?interval=1d&range=1y"
    d   = http_get(url)
    result     = d["chart"]["result"][0]
    timestamps = result["timestamp"]
    closes     = result["indicators"]["quote"][0]["close"]
    out = {}
    for ts, c in zip(timestamps, closes):
        if c is not None:
            date = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            out[date] = round(c, 2)
    print(f"    {len(out)} trading days")
    return out  # date -> float


def fetch_wti_history(start_date):
    """WTI crude oil from FRED — arbitrary date range."""
    print(f"  Fetching WTI (FRED, from {start_date})...")
    today = datetime.now(timezone.utc).date()
    url = (
        f"{FRED_BASE}/series/observations"
        f"?series_id=DCOILWTICO"
        f"&observation_start={start_date}"
        f"&observation_end={today}"
        f"&api_key={FRED_API_KEY}"
        f"&file_type=json&sort_order=asc"
    )
    d   = http_get(url)
    out = {}
    for o in d["observations"]:
        if o["value"] != ".":
            out[o["date"]] = round(float(o["value"]), 4)
    print(f"    {len(out)} trading days")
    return out  # date -> float


def fetch_td_history(symbol):
    """Twelve Data time_series — 200 trading days."""
    print(f"  Fetching {symbol} (Twelve Data, outputsize=200)...")
    url = (
        f"{TD_BASE}/time_series"
        f"?symbol={urllib.parse.quote(symbol)}"
        f"&interval=1day&outputsize=200&apikey={TD_API_KEY}"
    )
    d = http_get(url)
    if d.get("status") == "error":
        raise RuntimeError(f"Twelve Data error for {symbol}: {d.get('message')}")
    out = {}
    for v in d["values"]:
        out[v["datetime"]] = round(float(v["close"]), 6)
    print(f"    {len(out)} trading days")
    return out  # date -> float


def fetch_boc_rate_history(start_date):
    """BoC overnight rate — series V39079, date range.
    Returns a dict of all decision dates. Forward-fill in merge step."""
    print(f"  Fetching BoC rate (Valet, from {start_date})...")
    today = datetime.now(timezone.utc).date()
    d   = http_get(
        f"{BOC_BASE}/observations/V39079/json"
        f"?start_date={start_date}&end_date={today}"
    )
    out = {}
    for o in d["observations"]:
        if o.get("V39079", {}).get("v"):
            out[o["d"]] = round(float(o["V39079"]["v"]), 4)
    print(f"    {len(out)} decision dates")
    return out  # only dates with actual rate changes/observations


def fetch_bond_history(start_date):
    """GoC 5yr and 10yr bond yields from BoC Valet — date range."""
    print(f"  Fetching bond yields (BoC Valet, from {start_date})...")
    today = datetime.now(timezone.utc).date()
    d   = http_get(
        f"{BOC_BASE}/observations/group/bond_yields_benchmark/json"
        f"?start_date={start_date}&end_date={today}"
    )
    b5_out  = {}
    b10_out = {}
    for o in d["observations"]:
        if o.get("BD.CDN.5YR.DQ.YLD", {}).get("v") and o.get("BD.CDN.10YR.DQ.YLD", {}).get("v"):
            date = o["d"]
            b5_out[date]  = round(float(o["BD.CDN.5YR.DQ.YLD"]["v"]),  4)
            b10_out[date] = round(float(o["BD.CDN.10YR.DQ.YLD"]["v"]), 4)
    print(f"    {len(b5_out)} business days")
    return b5_out, b10_out  # date -> float


def fetch_cpi_history():
    """StatCan CPI — latestN=30 gives ~30 months; compute YoY for each."""
    print("  Fetching CPI (StatCan, latestN=30)...")
    result = http_post(
        f"{STATCAN}/getDataFromVectorsAndLatestNPeriods",
        [{"vectorId": 41690973, "latestN": 30}],
    )
    pts = sorted(
        result[0]["object"]["vectorDataPoint"],
        key=lambda o: o["refPer"],
    )
    # pts sorted oldest→newest; need at least 13 points for a YoY value
    out = {}  # "YYYY-MM" -> yoy float
    for i in range(12, len(pts)):
        cur    = float(pts[i]["value"])
        prev_y = float(pts[i - 12]["value"])
        ref    = (pts[i]["refPer"] or "")[:7]  # YYYY-MM
        out[ref] = round(((cur - prev_y) / prev_y) * 100, 4)
    print(f"    {len(out)} months with YoY values")
    return out  # "YYYY-MM" -> float


# ── Merge and write ────────────────────────────────────────────────────────────

def forward_fill(date_values, all_dates):
    """Given sparse date_values dict, forward-fill across all_dates.
    Returns dict with a value for every date >= first known observation."""
    result = {}
    last   = None
    for d in sorted(all_dates):
        if d in date_values:
            last = date_values[d]
        if last is not None:
            result[d] = last
    return result


def build_daily_items(tsx, wti, sp, cad, boc_sparse, b5, b10, cpi_monthly, cutoff_date):
    """Merge all sources into one item per calendar day.
    Uses trading days from TSX as the primary date spine.
    Skips dates before cutoff_date or with insufficient data."""
    all_dates = sorted(set(tsx.keys()) | set(b5.keys()))
    boc_ff    = forward_fill(boc_sparse, all_dates)

    items = []
    for date in all_dates:
        if date < cutoff_date:
            continue
        month = date[:7]  # YYYY-MM

        item = {}
        if date in tsx:      item["tsx"] = tsx[date]
        if date in wti:      item["oil"] = wti[date]
        if date in sp:       item["sp"]  = sp[date]
        if date in cad:      item["cad"] = cad[date]
        if date in boc_ff:   item["boc"] = boc_ff[date]
        if date in b5:       item["b5"]  = b5[date]
        if date in b10:      item["b10"] = b10[date]
        if month in cpi_monthly: item["cpi_yoy"] = cpi_monthly[month]

        # Only write items that have at least market data
        if len(item) >= 4:
            items.append((date, item))

    return items


def write_to_dynamo(items):
    """Write backfill items to DynamoDB, skipping any date already present."""
    import boto3  # noqa
    session  = boto3.Session(profile_name=AWS_PROFILE)
    dynamodb = session.resource("dynamodb", region_name=DYNAMODB_REGION)
    table    = dynamodb.Table(DYNAMODB_TABLE)

    # TTL: 1 year from today for all backfill items
    ttl_epoch = int((datetime.now(timezone.utc) + timedelta(days=365)).timestamp())

    # Fetch existing timestamps to avoid overwriting live data
    print("  Checking existing DynamoDB items...")
    from boto3.dynamodb.conditions import Key  # noqa
    existing = set()
    kwargs   = {
        "KeyConditionExpression": Key("pk").eq("SNAPSHOT"),
        "ProjectionExpression":   "ts",
    }
    while True:
        resp     = table.query(**kwargs)
        existing.update(i["ts"] for i in resp.get("Items", []))
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break
        kwargs["ExclusiveStartKey"] = last_key
    print(f"    {len(existing)} items already in table")

    written  = 0
    skipped  = 0
    with table.batch_writer() as batch:
        for date, values in items:
            ts = f"{date}T12:00:00Z"
            if ts in existing:
                skipped += 1
                continue
            record = {"pk": "SNAPSHOT", "ts": ts, "ttl": ttl_epoch}
            for k, v in values.items():
                record[k] = str(v)
            batch.put_item(Item=record)
            written += 1

    print(f"    Written: {written}  Skipped (already present): {skipped}")
    return written


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    today      = datetime.now(timezone.utc).date()
    # Fetch 200 days to ensure 180 days after alignment losses
    fetch_from = (today - timedelta(days=200)).strftime("%Y-%m-%d")
    cutoff     = (today - timedelta(days=BACKFILL_DAYS)).strftime("%Y-%m-%d")

    print(f"Backfill: fetching from {fetch_from}, writing days >= {cutoff}\n")

    print("Fetching data sources:")
    tsx         = fetch_tsx_history()
    wti         = fetch_wti_history(fetch_from)

    print("  Pausing 10s before Twelve Data calls...")
    time.sleep(10)
    sp          = fetch_td_history("SPY")
    time.sleep(5)
    cad         = fetch_td_history("CAD/USD")

    boc_sparse  = fetch_boc_rate_history(fetch_from)
    b5, b10     = fetch_bond_history(fetch_from)
    cpi_monthly = fetch_cpi_history()

    print(f"\nMerging data for days >= {cutoff}...")
    items = build_daily_items(tsx, wti, sp, cad, boc_sparse, b5, b10, cpi_monthly, cutoff)
    print(f"  {len(items)} days to write")

    print("\nWriting to DynamoDB...")
    written = write_to_dynamo(items)

    print(f"\nDone. {written} new items written to {DYNAMODB_TABLE}.")
    print("History files will be generated on the next midnight UTC Lambda run.")
    print("To generate immediately, invoke the Lambda manually between 00:00–00:59 UTC.")


if __name__ == "__main__":
    main()
