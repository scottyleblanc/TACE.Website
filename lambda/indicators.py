"""
indicators.py — Economic Indicators Lambda
Fetches all 8 indicators and writes indicators.json to S3.
Triggered by EventBridge on a cron schedule.

Environment variables (set in Lambda console, never in source):
  TD_API_KEY   — Twelve Data API key
  S3_BUCKET    — target bucket name
  S3_KEY       — target object key (default: data/indicators.json)
"""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone


# ── Config ────────────────────────────────────────────────────────────────────

TD_API_KEY = os.environ["TD_API_KEY"]
S3_BUCKET  = os.environ["S3_BUCKET"]
S3_KEY     = os.environ.get("S3_KEY", "data/indicators.json")

TD_BASE    = "https://api.twelvedata.com"
BOC_BASE   = "https://www.bankofcanada.ca/valet"
STATCAN    = "https://www150.statcan.gc.ca/t1/wds/rest"

# Twelve Data free tier: 8 calls/minute. 4 symbols × 2 calls = 8 calls.
# 8-second pause between symbols keeps burst under the per-minute ceiling.
TD_PAUSE_S = 8


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
    Individual series (BD.CDN.5YR.DQ.YLD etc.) can go silent for weeks."""
    d   = http_get(f"{BOC_BASE}/observations/group/bond_yields_benchmark/json?recent=60")
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

def write_to_s3(payload):
    """Write indicators.json to S3 using boto3 (available in Lambda runtime)."""
    import boto3  # noqa: PLC0415 — available in Lambda, not needed locally
    s3 = boto3.client("s3")
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=S3_KEY,
        Body=json.dumps(payload, separators=(",", ":")),
        ContentType="application/json",
        CacheControl="max-age=1800",  # 30 minutes — matches run cadence
    )


# ── Handler ───────────────────────────────────────────────────────────────────

def handler(event, context):
    """Lambda entry point. Fetches all indicators and writes indicators.json to S3."""
    errors = {}
    payload = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}

    # Government APIs — no quota, fetch first
    try:
        payload["boc"] = fetch_boc_rate()
    except Exception as e:
        errors["boc"] = str(e)
        payload["boc"] = None

    try:
        payload["bonds"] = fetch_bonds()
    except Exception as e:
        errors["bonds"] = str(e)
        payload["bonds"] = None

    try:
        payload["cpi"] = fetch_cpi()
    except Exception as e:
        errors["cpi"] = str(e)
        payload["cpi"] = None

    # Twelve Data — sequenced with pauses to stay within 8 calls/minute
    for key, symbol in [("sp", "SPY"), ("tsx", "EWC"), ("oil", "USO"), ("cad", "CAD/USD")]:
        try:
            payload[key] = fetch_td_equity(symbol)
        except Exception as e:
            errors[key] = str(e)
            payload[key] = None
        time.sleep(TD_PAUSE_S)

    if errors:
        payload["errors"] = errors

    write_to_s3(payload)

    print(f"[indicators] written to s3://{S3_BUCKET}/{S3_KEY} — errors: {errors or 'none'}")
    return {"statusCode": 200, "errors": errors}
