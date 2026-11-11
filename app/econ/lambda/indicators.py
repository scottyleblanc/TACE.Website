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

TD_API_KEY    = os.environ["TD_API_KEY"]
FRED_API_KEY  = os.environ["FRED_API_KEY"]
S3_BUCKET     = os.environ["S3_BUCKET"]
S3_KEY        = os.environ.get("S3_KEY", "data/indicators.json")
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")

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

# History files share the same S3 prefix as indicators.json (e.g. tacedata-site/data/)
_DATA_PREFIX = S3_KEY.rsplit("/", 1)[0]
S3_HISTORY_KEYS = {
    90:  f"{_DATA_PREFIX}/history-90d.json",
    180: f"{_DATA_PREFIX}/history-180d.json",
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

BOC_RATE_LOOKBACK_DAYS = 730  # long enough to span the longest recent hold period

# Fixed announcement schedule (9:45 ET), published by the BoC each July for the next year.
# Source: bankofcanada.ca — "Bank of Canada publishes its 2027 schedule..." (2026-07).
# A latched ops alert (boc_schedule_low) fires SCHEDULE_WARN_DAYS before this runs out.
BOC_DECISION_DATES = (
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-10",
    "2026-07-15", "2026-09-02", "2026-10-28", "2026-12-09",
    "2027-01-27", "2027-03-03", "2027-04-28", "2027-06-02",
    "2027-07-21", "2027-09-08", "2027-10-27", "2027-12-08",
)


def boc_decision_summary(obs, schedule=BOC_DECISION_DATES):
    """Classify the most recent BoC decision from the rate series.
    obs: [(YYYY-MM-DD, rate)] sorted oldest->newest. A decision on day D takes effect
    the next business day, so it is resolved once an observation dated after D exists.
    Returns {"last_decision": {date, effective, outcome, before, after} | None,
             "next_decision": YYYY-MM-DD | None}
    next_decision is the first scheduled date not yet reflected in the data — it can be
    today or slightly in the past while the effective-day observation is pending."""
    last, nxt = None, None
    for day in schedule:
        after = next(((d, r) for d, r in obs if d > day), None)
        if after is None:
            nxt = day
            break
        before = next(((d, r) for d, r in reversed(obs) if d <= day), None)
        if before is None:
            continue  # decision predates the fetched window
        outcome = "hike" if after[1] > before[1] else "cut" if after[1] < before[1] else "hold"
        last = {"date": day, "effective": after[0], "outcome": outcome,
                "before": before[1], "after": after[1]}
    return {"last_decision": last, "next_decision": nxt}


def fetch_boc_rate():
    """Bank of Canada overnight rate — series V39079.
    Returns {cur, prev, date, last_decision, next_decision}:
      cur  — current rate
      prev — rate in effect before the most recent change (== cur if no change in window)
      date — first day the current rate took effect
      last_decision / next_decision — see boc_decision_summary()

    Valet returns `recent=N` results newest-first but date-range results oldest-first,
    so we use a date range and sort explicitly rather than trust either order."""
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=BOC_RATE_LOOKBACK_DAYS)
    d   = http_get(f"{BOC_BASE}/observations/V39079/json?start_date={start}&end_date={today}")
    obs = sorted(
        ((o["d"], float(o["V39079"]["v"])) for o in d["observations"] if o.get("V39079", {}).get("v")),
        key=lambda t: t[0],
    )
    cur  = obs[-1][1]
    prev = cur
    date = obs[0][0]
    # Walk back to the most recent change point
    for i in range(len(obs) - 1, 0, -1):
        if obs[i - 1][1] != cur:
            prev = obs[i - 1][1]
            date = obs[i][0]
            break
    return {"cur": cur, "prev": prev, "date": date, **boc_decision_summary(obs)}


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
    obs = sorted(
        (
            o for o in d["observations"]
            if o.get("BD.CDN.5YR.DQ.YLD", {}).get("v") and o.get("BD.CDN.10YR.DQ.YLD", {}).get("v")
        ),
        key=lambda o: o["d"],
    )
    h5  = [float(o["BD.CDN.5YR.DQ.YLD"]["v"])  for o in obs]
    h10 = [float(o["BD.CDN.10YR.DQ.YLD"]["v"]) for o in obs]
    date = obs[-1]["d"]

    # Stale flag: missed business days signal a benchmark transition gap, not a holiday.
    stale = _is_stale(date, business_days=BOND_STALE_BUSINESS_DAYS)

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

    # Filter nulls (trading halts, missing data points); sort — never trust API order
    pairs = sorted(((ts, c) for ts, c in zip(timestamps, closes) if c is not None), key=lambda p: p[0])
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
    obs = sorted(
        ((o["date"], float(o["value"])) for o in d["observations"] if o["value"] != "."),
        key=lambda t: t[0],
    )
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
    # Sort oldest->newest by datetime — Twelve Data defaults to newest-first, but never trust API order
    history = [float(v["close"]) for v in sorted(series["values"], key=lambda v: v["datetime"])]

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

BOND_STALE_BUSINESS_DAYS = 3


def _is_stale(date_str, business_days, today=None):
    """True if more than `business_days` weekdays have passed since date_str (YYYY-MM-DD)
    without a newer observation. Today is excluded — its data posts end of day — so a
    normal weekend, a long weekend, or the Christmas/New Year closure stays fresh."""
    today = today or datetime.now(timezone.utc).date()
    day   = datetime.strptime(date_str, "%Y-%m-%d").date() + timedelta(days=1)
    missed = 0
    while day < today:
        if day.weekday() < 5:
            missed += 1
        day += timedelta(days=1)
    return missed > business_days


# ── Threshold alerting ────────────────────────────────────────────────────────
#
# Two alert kinds:
#   Crossing — an event detected by comparing against the ~1-day-old snapshot
#              (BoC rate change, CPI crossing a band). Detected for ~24 h after the
#              event; the 24 h dedup record makes it send once.
#   Latched  — a condition that can persist for weeks (curve inversion, rolling
#              7-day moves, schedule running out). Sends once when the condition
#              becomes true, re-arms only after it has been observed false.
#
# Dedup/latch state lives in DynamoDB as pk=ALERT, ts=<trigger_id>. The record is
# written BEFORE publishing so a failed state write can never cause a send loop;
# if the publish fails the prior record is restored so the next run retries.

ALERT_DEDUP_HOURS = 24
SCHEDULE_WARN_DAYS = 45  # warn this many days before BOC_DECISION_DATES runs out

CROSSING_TRIGGERS = ("boc_changed", "cpi_above_3", "cpi_below_2")
LATCHED_TRIGGERS  = ("b5_up_7d", "b10_invert", "sp_down_7d", "boc_schedule_low")

DASHBOARD_URL = "https://tacedata.ca/projects/econ/interest-rate/"
_FOOTER       = f"Dashboard: {DASHBOARD_URL}\n\n---\nNot financial advice."


def _get_7day_snapshot(table, days=7):
    """Fetch the closest DynamoDB snapshot at or before N days ago. Returns item or None."""
    from boto3.dynamodb.conditions import Key  # noqa: PLC0415
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    resp   = table.query(
        KeyConditionExpression=Key("pk").eq("SNAPSHOT") & Key("ts").lte(cutoff),
        Limit=1,
        ScanIndexForward=False,
    )
    items = resp.get("Items", [])
    return items[0] if items else None


def _get_alert_record(table, trigger_id):
    """Current dedup/latch record for a trigger, or None."""
    from boto3.dynamodb.conditions import Key  # noqa: PLC0415
    resp  = table.query(
        KeyConditionExpression=Key("pk").eq("ALERT") & Key("ts").eq(trigger_id),
        Limit=1,
    )
    items = resp.get("Items", [])
    return items[0] if items else None


def _dedup_cutoff():
    return (datetime.now(timezone.utc) - timedelta(hours=ALERT_DEDUP_HOURS)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sent_recently(record):
    return bool(record) and record.get("sent_at", "") >= _dedup_cutoff()


def _is_latched(record):
    """Latched triggers store active=True/False. Records written before v3.4.0 have no
    `active` key — treat them as active only while inside the old 24 h dedup window."""
    if not record:
        return False
    if "active" in record:
        return bool(record["active"])
    return _sent_recently(record)


def _put_alert_record(table, trigger_id, ts_now, active, expire_hours=None):
    item = {"pk": "ALERT", "ts": trigger_id, "sent_at": ts_now, "active": active}
    if expire_hours:
        item["ttl"] = int((datetime.now(timezone.utc) + timedelta(hours=expire_hours)).timestamp())
    table.put_item(Item=item)


def _publish_alert(subject, message):
    """Publish to SNS. No-op if SNS_TOPIC_ARN is not configured."""
    if not SNS_TOPIC_ARN:
        print(f"[indicators] alert suppressed (SNS_TOPIC_ARN not set): {subject}")
        return
    import boto3  # noqa: PLC0415
    sns = boto3.client("sns", region_name="ca-central-1")
    sns.publish(TopicArn=SNS_TOPIC_ARN, Subject=subject, Message=message)
    print(f"[indicators] alert sent: {subject}")


def _send(table, trigger_id, subject, message, ts_now, previous, expire_hours=None):
    """Record first, then publish; restore the previous record if the publish fails."""
    _put_alert_record(table, trigger_id, ts_now, active=True, expire_hours=expire_hours)
    try:
        _publish_alert(subject, message)
    except Exception:
        if previous:
            table.put_item(Item=previous)
        else:
            _put_alert_record(table, trigger_id, "", active=False, expire_hours=1)
        raise


def _evaluate_alerts(payload, prior_1d, prior_7d, today=None):
    """Pure alert evaluation — no I/O.
    Returns (crossings, latched):
      crossings — list of (trigger_id, subject, message) for events detected this run
      latched   — list of (trigger_id, condition, subject, message); condition is
                  True/False, or None when it cannot be evaluated (missing data)."""
    today     = today or datetime.now(timezone.utc).date()
    crossings = []
    latched   = []

    # ── Crossings ──

    # BoC rate changed — compare against the stored snapshot from ~1 day ago, not
    # payload["boc"]["prev"], which holds the pre-decision rate indefinitely.
    if payload.get("boc") and prior_1d and prior_1d.get("boc"):
        cur_boc  = round(payload["boc"]["cur"], 4)
        prev_boc = round(float(prior_1d["boc"]), 4)
        if cur_boc != prev_boc:
            direction = "raised" if cur_boc > prev_boc else "cut"
            diff      = abs(cur_boc - prev_boc)
            crossings.append((
                "boc_changed",
                f"[econ-alert] BoC {direction} overnight rate to {cur_boc:.2f}%",
                f"The Bank of Canada has {direction} the overnight rate by {diff:.2f}%.\n"
                f"New rate: {cur_boc:.2f}%  |  Previous: {prev_boc:.2f}%\n\n"
                f"{'Variable rate payments will increase.' if direction == 'raised' else 'Variable rate payments will decrease.'}\n\n"
                f"{_FOOTER}",
            ))

    if payload.get("cpi") and prior_1d and prior_1d.get("cpi_yoy"):
        cur_cpi  = payload["cpi"]["yoy"]
        prev_cpi = float(prior_1d["cpi_yoy"])
        if cur_cpi > 3.0 and prev_cpi <= 3.0:
            crossings.append((
                "cpi_above_3",
                f"[econ-alert] CPI YoY crossed above 3.0% — now {cur_cpi:.2f}%",
                f"CPI YoY has crossed above 3.0% (now {cur_cpi:.2f}%, was {prev_cpi:.2f}%).\n\n"
                f"Inflation above the BoC's upper tolerance limits room for rate cuts.\n"
                f"This may be a signal to consider locking in fixed.\n\n"
                f"{_FOOTER}",
            ))
        if cur_cpi < 2.0 and prev_cpi >= 2.0:
            crossings.append((
                "cpi_below_2",
                f"[econ-alert] CPI YoY crossed below 2.0% — now {cur_cpi:.2f}%",
                f"CPI YoY has crossed below 2.0% (now {cur_cpi:.2f}%, was {prev_cpi:.2f}%).\n\n"
                f"Inflation below target opens room for BoC rate cuts.\n"
                f"This may favour staying variable.\n\n"
                f"{_FOOTER}",
            ))

    # ── Latched conditions ──

    # GoC 5yr yield up >+0.30% over 7 days
    if payload.get("bonds") and prior_7d and prior_7d.get("b5"):
        cur_b5  = payload["bonds"]["b5"]["cur"]
        prev_b5 = float(prior_7d["b5"])
        diff    = cur_b5 - prev_b5
        latched.append((
            "b5_up_7d", diff > 0.30,
            f"[econ-alert] GoC 5yr yield up +{diff:.2f}% over 7 days",
            f"GoC 5yr Bond Yield has risen +{diff:.2f}% over the past 7 days.\n"
            f"Current: {cur_b5:.2f}%  |  7 days ago: {prev_b5:.2f}%\n\n"
            f"Fixed mortgage rates typically follow within 2-4 weeks.\n"
            f"This may be a good time to review your rate decision.\n\n"
            f"{_FOOTER}",
        ))

    # Yield curve inversion (10yr < 5yr)
    if payload.get("bonds"):
        b5  = payload["bonds"]["b5"]["cur"]
        b10 = payload["bonds"]["b10"]["cur"]
        latched.append((
            "b10_invert", b10 < b5,
            "[econ-alert] Yield curve inverted — 10yr < 5yr",
            f"The yield curve has inverted: 10yr ({b10:.2f}%) is below 5yr ({b5:.2f}%).\n\n"
            f"An inverted yield curve is a recession signal. Rate cuts are likely ahead,\n"
            f"which would favour staying variable over locking in fixed.\n\n"
            f"{_FOOTER}",
        ))

    # S&P 500 down >10% over 7 days
    if payload.get("sp") and prior_7d and prior_7d.get("sp"):
        cur_sp  = payload["sp"]["cur"]
        prev_sp = float(prior_7d["sp"])
        pct     = ((cur_sp - prev_sp) / prev_sp) * 100
        latched.append((
            "sp_down_7d", pct < -10.0,
            f"[econ-alert] S&P 500 down {pct:.1f}% over 7 days",
            f"The S&P 500 has fallen {pct:.1f}% over the past 7 days.\n"
            f"Current: {cur_sp:.2f}  |  7 days ago: {prev_sp:.2f}\n\n"
            f"Sharp equity declines raise recession risk and may prompt BoC rate cuts,\n"
            f"which would favour staying variable.\n\n"
            f"{_FOOTER}",
        ))

    # BoC decision schedule running out — operational reminder to update the code
    last_scheduled = datetime.strptime(BOC_DECISION_DATES[-1], "%Y-%m-%d").date()
    days_left      = (last_scheduled - today).days
    latched.append((
        "boc_schedule_low", days_left < SCHEDULE_WARN_DAYS,
        "[econ-ops] BoC decision schedule needs updating",
        f"BOC_DECISION_DATES in indicators.py ends {last_scheduled} ({days_left} days away).\n"
        f"Add next year's dates from the Bank of Canada's published schedule\n"
        f"(released each July) so the dashboard's decision signal keeps working.",
    ))

    return crossings, latched


def check_thresholds(payload, ts_now):
    """Evaluate alerts and send/latch via SNS + DynamoDB. Non-fatal — errors are logged only."""
    if not SNS_TOPIC_ARN:
        return  # alerting not configured — skip entirely

    import boto3  # noqa: PLC0415
    table    = boto3.resource("dynamodb").Table(DYNAMODB_TABLE)
    prior_1d = _get_7day_snapshot(table, days=1)
    prior_7d = _get_7day_snapshot(table, days=7)

    crossings, latched = _evaluate_alerts(payload, prior_1d, prior_7d)

    for trigger_id, subject, message in crossings:
        try:
            record = _get_alert_record(table, trigger_id)
            if not _sent_recently(record):
                _send(table, trigger_id, subject, message, ts_now, record,
                      expire_hours=ALERT_DEDUP_HOURS + 1)
        except Exception as e:
            print(f"[indicators] alert failed for {trigger_id}: {e}")

    for trigger_id, condition, subject, message in latched:
        if condition is None:
            continue
        try:
            record = _get_alert_record(table, trigger_id)
            active = _is_latched(record)
            if condition and not active:
                _send(table, trigger_id, subject, message, ts_now, record)
            elif not condition and active:
                _put_alert_record(table, trigger_id, ts_now, active=False)
                print(f"[indicators] alert re-armed: {trigger_id}")
        except Exception as e:
            print(f"[indicators] alert failed for {trigger_id}: {e}")


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

PUBLIC_FETCH_ERROR = "source unavailable"


def _record_fetch_error(errors, key, exc):
    """[SEC] indicators.json is public. Upstream exception text (URLs, API error bodies)
    goes to CloudWatch only; the payload carries a fixed generic message."""
    print(f"[indicators] fetch failed for {key}: {type(exc).__name__}: {exc}")
    errors[key] = PUBLIC_FETCH_ERROR


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
            _record_fetch_error(errors, key, e)
            payload[key] = None

    # Twelve Data — SPY and CAD/USD only (4 calls, within 8/min free tier)
    for key, symbol in [("sp", "SPY"), ("cad", "CAD/USD")]:
        try:
            payload[key] = fetch_td_equity(symbol)
        except Exception as e:
            _record_fetch_error(errors, key, e)
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

    # Check thresholds and send alerts — non-fatal
    try:
        check_thresholds(payload, ts_now)
    except Exception as e:
        print(f"[indicators] threshold check failed: {e}")

    # Regenerate history files once daily — midnight UTC hour only (00:00 and 00:30 runs)
    # Pass {"force_history": true} in the Lambda event to trigger immediately (e.g. for testing)
    now_utc = datetime.now(timezone.utc)
    if now_utc.hour == 0 or event.get("force_history"):
        try:
            generate_history_files(ts_now)
        except Exception as e:
            print(f"[indicators] history generation failed: {e}")

    print(f"[indicators] written to s3://{S3_BUCKET}/{S3_KEY} — errors: {errors or 'none'}")
    return {"statusCode": 200, "errors": errors}
