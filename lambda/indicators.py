"""
indicators.py — Economic Indicators Lambda
Fetches all 8 indicators and writes indicators.json to S3.
Triggered by EventBridge on a cron schedule.

Environment variables (set in Lambda console, never in source):
  TD_API_KEY   — Twelve Data API key (SPY, CAD/USD)
  FRED_API_KEY — FRED (St. Louis Fed) API key (WTI crude oil)
  S3_BUCKET    — target bucket name
  S3_KEY       — target object key (default: data/indicators.json)

Data sources:
  BoC Valet API              — overnight rate, GoC 5yr and 10yr bond yields
  Statistics Canada WDS API  — CPI
  Yahoo Finance              — TSX Composite (^GSPTSE)
  FRED                       — WTI crude oil spot price (DCOILWTICO)
  Twelve Data                — S&P 500 (SPY), CAD/USD (free tier, 2 symbols)
"""

import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone


# ── Config ────────────────────────────────────────────────────────────────────

TD_API_KEY   = os.environ["TD_API_KEY"]
FRED_API_KEY = os.environ["FRED_API_KEY"]
S3_BUCKET    = os.environ["S3_BUCKET"]
S3_KEY       = os.environ.get("S3_KEY", "data/indicators.json")

TD_BASE   = "https://api.twelvedata.com"
BOC_BASE  = "https://www.bankofcanada.ca/valet"
STATCAN   = "https://www150.statcan.gc.ca/t1/wds/rest"
FRED_BASE = "https://api.stlouisfed.org/fred"
YF_BASE   = "https://query1.finance.yahoo.com/v8/finance/chart"

# Twelve Data free tier: 8 calls/minute.
# Stage 2.4: only SPY and CAD/USD remain (2 symbols × 2 calls = 4 calls).
# No inter-symbol pause required at this volume.
TD_PAUSE_S = 0

DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "econ-indicators-history")

# History files written to S3 once daily (midnight UTC run).
# Served via the existing CloudFront data/* behavior.
S3_HISTORY_KEYS = {
    90:  "data/history-90d.json",
    180: "data/history-180d.json",
}


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def http_get(url, timeout=15):
    """GET request, returns parsed JSON."""
    req = urllib.request.Request(url, headers={"User-Agent": "tacedata-indicators/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def http_post(url, body, timeout=15):
    """POST request with JSON body, returns parsed JSON."""
    data = json.dumps(body).encode()
    req  = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "tacedata-indicators/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


# ── Data fetchers ─────────────────────────────────────────────────────────────

def fetch_boc_rate():
    """Bank of Canada overnight rate — series V39079."""
    d   = http_get(f"{BOC_BASE}/observations/V39079/json?recent=10")
    obs = [o for o in d["observations"] if o.get("V39079", {}).get("v")]
    cur  = float(obs[-1]["V39079"]["v"])
    prev = float(obs[-2]["V39079"]["v"])
    date = obs[-1]["d"]
    return {"cur": cur, "prev": prev, "date": date}


def fetch_bonds():
    """GoC 5yr and 10yr bond yields — bond_yields_benchmark group endpoint.
    Single fetch for both series; returns nested b5/b10 objects.
    The group endpoint is maintained continuously through benchmark transitions.
    Individual series (BD.CDN.5YR.DQ.YLD etc.) can go silent for weeks.
    Data is end-of-day from BoC — no free real-time source exists for GoC yields.

    Uses a date range (90 calendar days) rather than recent=N. The recent=N
    parameter counts only valid observations — during a benchmark transition gap
    it skips the resumption data entirely and returns stale pre-gap values."""
    today      = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=90)
    d   = http_get(
        f"{BOC_BASE}/observations/group/bond_yields_benchmark/json"
        f"?start_date={start_date}&end_date={today}"
    )
    obs = [
        o for o in d["observations"]
        if o.get("BD.CDN.5YR.DQ.YLD", {}).get("v") and o.get("BD.CDN.10YR.DQ.YLD", {}).get("v")
    ]
    h5  = [float(o["BD.CDN.5YR.DQ.YLD"]["v"])  for o in obs]
    h10 = [float(o["BD.CDN.10YR.DQ.YLD"]["v"]) for o in obs]
    date = obs[-1]["d"]

    # Stale flag: more than 5 business days without an update signals a benchmark transition gap.
    stale = _is_stale(date, days=5)

    return {
        "b5":  {"cur": h5[-1],  "prev": h5[-2],  "history": h5[-30:],  "date": date, "stale": stale},
        "b10": {"cur": h10[-1], "prev": h10[-2], "history": h10[-30:], "date": date, "stale": stale},
    }


def fetch_cpi():
    """Statistics Canada all-items CPI — vector 41690973.
    Requests 25 periods to support 13-month YoY sparkline.
    Sort order is not guaranteed by the API — always sort by refPer descending."""
    result = http_post(
        f"{STATCAN}/getDataFromVectorsAndLatestNPeriods",
        [{"vectorId": 41690973, "latestN": 25}],
    )
    pts = sorted(
        result[0]["object"]["vectorDataPoint"],
        key=lambda o: o["refPer"],
        reverse=True,
    )
    # pts[0]  = most recent month
    # pts[1]  = previous month
    # pts[12] = same month 1 year ago
    cur    = float(pts[0]["value"])
    prev_m = float(pts[1]["value"])
    prev_y = float(pts[12]["value"])
    ref_date = (pts[0]["refPer"] or "")[:7]  # trim to YYYY-MM

    yoy = ((cur - prev_y) / prev_y) * 100
    mom = ((cur - prev_m) / prev_m) * 100

    # 13-month YoY sparkline: oldest→newest (indices 12 down to 0)
    yoy_history = []
    for i in range(12, -1, -1):
        val = float(pts[i]["value"])
        yr  = float(pts[i + 12]["value"])
        yoy_history.append(round(((val - yr) / yr) * 100, 4))

    return {
        "yoy":         round(yoy, 4),
        "mom":         round(mom, 4),
        "yoy_history": yoy_history,
        "ref_date":    ref_date,
    }


def fetch_tsx():
    """TSX Composite Index from Yahoo Finance (^GSPTSE).
    Returns {cur, prev, history, date} — values are index points in CAD."""
    url = f"{YF_BASE}/%5EGSPTSE?interval=1d&range=3mo"
    d   = http_get(url)
    result = d["chart"]["result"][0]
    timestamps = result["timestamp"]
    closes     = result["indicators"]["quote"][0]["close"]

    # Filter nulls (trading halts, missing data points)
    pairs = [(ts, c) for ts, c in zip(timestamps, closes) if c is not None]
    if len(pairs) < 2:
        raise RuntimeError(f"Yahoo Finance returned insufficient TSX data: {len(pairs)} points")

    history   = [c for _, c in pairs]
    last_date = datetime.fromtimestamp(pairs[-1][0], tz=timezone.utc).strftime("%Y-%m-%d")

    return {
        "cur":     history[-1],
        "prev":    history[-2],
        "history": history[-30:],
        "date":    last_date,
    }


def fetch_wti():
    """WTI crude oil spot price from FRED (DCOILWTICO).
    Returns {cur, prev, history, date} — values are USD per barrel.
    FRED uses '.' for missing observations (holidays/weekends) — filtered out."""
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=60)
    url = (
        f"{FRED_BASE}/series/observations"
        f"?series_id=DCOILWTICO"
        f"&observation_start={start.strftime('%Y-%m-%d')}"
        f"&api_key={FRED_API_KEY}"
        f"&file_type=json"
        f"&sort_order=asc"
    )
    d   = http_get(url)
    obs = [(o["date"], float(o["value"])) for o in d["observations"] if o["value"] != "."]
    if len(obs) < 2:
        raise RuntimeError(f"FRED returned insufficient WTI data: {len(obs)} observations")
    history = [v for _, v in obs]
    return {
        "cur":     history[-1],
        "prev":    history[-2],
        "history": history[-30:],
        "date":    obs[-1][0],
    }


def fetch_td_equity(symbol):
    """Fetch quote + 30-day history for a Twelve Data equity or forex symbol.
    Returns {cur, prev, history} where history is oldest→newest closing prices."""
    quote = http_get(
        f"{TD_BASE}/quote?symbol={urllib.parse.quote(symbol)}&apikey={TD_API_KEY}"
    )
    _td_check(quote, symbol)
    cur  = float(quote["close"])
    prev = float(quote["previous_close"])

    time.sleep(0.5)  # brief pause between the two calls for the same symbol

    series = http_get(
        f"{TD_BASE}/time_series?symbol={urllib.parse.quote(symbol)}"
        f"&interval=1day&outputsize=30&apikey={TD_API_KEY}"
    )
    _td_check(series, symbol)
    history = [float(v["close"]) for v in reversed(series["values"])]

    return {"cur": cur, "prev": prev, "history": history}


def _td_check(d, symbol):
    """Raise a clear error on Twelve Data API-level failures."""
    if d.get("code") in (401, 403):
        raise RuntimeError(f"Twelve Data auth failure for {symbol} — check TD_API_KEY")
    if d.get("code") == 429:
        raise RuntimeError(f"Twelve Data rate limit hit fetching {symbol}")
    if d.get("status") == "error":
        raise RuntimeError(f"Twelve Data error for {symbol}: {d.get('message')}")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_stale(date_str, days):
    """True if date_str (YYYY-MM-DD) is more than `days` days in the past."""
    dt  = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - dt).total_seconds() / 86400
    return age > days


# ── S3 write ──────────────────────────────────────────────────────────────────

def write_to_s3(payload, key=None, cache_control=None):
    """Write a JSON payload to S3. Defaults to indicators.json with 30-minute cache."""
    import boto3  # noqa: PLC0415 — available in Lambda, not needed locally
    s3 = boto3.client("s3")
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key or S3_KEY,
        Body=json.dumps(payload, separators=(",", ":")),
        ContentType="application/json",
        CacheControl=cache_control or "max-age=1800",
    )


def write_snapshot_to_dynamo(payload, ts):
    """Write a timestamped snapshot to DynamoDB for historical storage.
    Values stored as strings to avoid boto3 Decimal requirement.
    TTL set to 1 year — DynamoDB expires old items automatically."""
    import boto3  # noqa: PLC0415
    dynamodb = boto3.resource("dynamodb")
    table    = dynamodb.Table(DYNAMODB_TABLE)
    ttl      = int((datetime.now(timezone.utc) + timedelta(days=365)).timestamp())

    item = {"pk": "SNAPSHOT", "ts": ts, "ttl": ttl}
    if payload.get("boc"):
        item["boc"] = str(round(payload["boc"]["cur"], 4))
    if payload.get("bonds"):
        item["b5"]  = str(round(payload["bonds"]["b5"]["cur"],  4))
        item["b10"] = str(round(payload["bonds"]["b10"]["cur"], 4))
    if payload.get("cpi"):
        item["cpi_yoy"] = str(round(payload["cpi"]["yoy"], 4))
    if payload.get("sp"):
        item["sp"]  = str(round(payload["sp"]["cur"],  4))
    if payload.get("tsx"):
        item["tsx"] = str(round(payload["tsx"]["cur"], 2))
    if payload.get("oil"):
        item["oil"] = str(round(payload["oil"]["cur"], 4))
    if payload.get("cad"):
        item["cad"] = str(round(payload["cad"]["cur"], 6))

    table.put_item(Item=item)


def _dynamo_query_all(table, **kwargs):
    """Query DynamoDB with automatic pagination. Returns all items across pages."""
    items = []
    while True:
        resp     = table.query(**kwargs)
        items.extend(resp.get("Items", []))
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break
        kwargs["ExclusiveStartKey"] = last_key
    return items


def generate_history_files(ts_now):
    """Query DynamoDB for 90- and 180-day windows, aggregate to one entry per calendar
    day (latest run wins), and write history-90d.json / history-180d.json to S3.
    Called only on the midnight UTC run — daily granularity, negligible read cost."""
    import boto3  # noqa: PLC0415
    from boto3.dynamodb.conditions import Key  # noqa: PLC0415

    dynamodb = boto3.resource("dynamodb")
    table    = dynamodb.Table(DYNAMODB_TABLE)
    today    = datetime.now(timezone.utc).date()

    for days in [90, 180]:
        start = (today - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z")

        items = _dynamo_query_all(
            table,
            KeyConditionExpression=Key("pk").eq("SNAPSHOT") & Key("ts").gte(start),
            ProjectionExpression="ts, boc, b5, b10, cpi_yoy, sp, tsx, oil, cad",
        )

        # One entry per calendar day — take the latest timestamp for that day
        by_day = {}
        for item in items:
            date = item["ts"][:10]
            if date not in by_day or item["ts"] > by_day[date]["ts"]:
                by_day[date] = item

        snapshots = []
        for date in sorted(by_day.keys()):
            item = by_day[date]
            snap = {"date": date}
            for k in ["boc", "b5", "b10", "cpi_yoy", "sp", "tsx", "oil", "cad"]:
                if k in item:
                    snap[k] = float(item[k])
            snapshots.append(snap)

        write_to_s3(
            {"generated_at": ts_now, "days": days, "snapshots": snapshots},
            key=S3_HISTORY_KEYS[days],
            cache_control="max-age=86400",  # 24 hours — regenerated once daily
        )
        print(f"[indicators] history-{days}d: {len(snapshots)} daily snapshots written")


# ── Handler ───────────────────────────────────────────────────────────────────

def handler(event, context):
    """Lambda entry point. Fetches all indicators, writes indicators.json to S3,
    writes a timestamped snapshot to DynamoDB, and regenerates history files once daily."""
    errors  = {}
    ts_now  = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {"generated_at": ts_now}

    # No-quota / free sources — fetch first, no rate concerns
    for key, fn in [
        ("boc",   fetch_boc_rate),
        ("bonds", fetch_bonds),
        ("cpi",   fetch_cpi),
        ("tsx",   fetch_tsx),
        ("oil",   fetch_wti),
    ]:
        try:
            payload[key] = fn()
        except Exception as e:
            errors[key] = str(e)
            payload[key] = None

    # Twelve Data — SPY and CAD/USD only (4 calls, within 8/min free tier)
    for key, symbol in [("sp", "SPY"), ("cad", "CAD/USD")]:
        try:
            payload[key] = fetch_td_equity(symbol)
        except Exception as e:
            errors[key] = str(e)
            payload[key] = None
        if TD_PAUSE_S:
            time.sleep(TD_PAUSE_S)

    if errors:
        payload["errors"] = errors

    write_to_s3(payload)

    # Write snapshot to DynamoDB — non-fatal if it fails
    try:
        write_snapshot_to_dynamo(payload, ts_now)
    except Exception as e:
        print(f"[indicators] DynamoDB write failed: {e}")

    # Regenerate history files once daily — midnight UTC hour only (00:00 and 00:30 runs)
    now_utc = datetime.now(timezone.utc)
    if now_utc.hour == 0:
        try:
            generate_history_files(ts_now)
        except Exception as e:
            print(f"[indicators] history generation failed: {e}")

    print(f"[indicators] written to s3://{S3_BUCKET}/{S3_KEY} — errors: {errors or 'none'}")
    return {"statusCode": 200, "errors": errors}
