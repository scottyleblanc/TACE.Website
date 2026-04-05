---
title: "economic dashboard series: stage 4 — data source upgrades"
date: 2026-04-05T10:00:00
draft: false
tags: ["aws", "lambda", "python", "fred", "yahoo-finance", "boc", "twelve-data", "portfolio", "economics", "canada"]
summary: "fourth post in the series: replacing ETF proxies with direct data sources, investigating free alternatives, and fixing a BoC query bug hiding three months of bond yield data."
---

### The Proxies Were Always Temporary

*This is the fourth post in a series documenting the build-out of a Canadian economic indicators dashboard. [Stage 1](/posts/econ-stage-1-post/) covered the original problem. [Stage 2](/posts/econ-stage-2-post/) moved the dashboard into the Hugo site. [Stage 3](/posts/econ-stage-3-post/) moved all data fetching into AWS Lambda.*

---

Stage 3 ended with a note: now that CORS is no longer a constraint, Stage 4 would evaluate replacing the ETF proxies that had been forced by browser limitations. Stage 3 also surfaced a bond yield staleness issue — the dashboard was showing January 7 as the latest business day, three months into April.

Stage 4 addressed both.

---

### What Was Being Proxied and Why

The original dashboard ran entirely in the browser. That created two problems with data sources:

**CORS:** Browser requests to third-party APIs require the server to send permissive CORS headers. Most financial data providers don't. The government APIs (BoC, StatCan) do — they're designed for public access. Twelve Data does. But direct market data for Canadian instruments generally doesn't.

**Twelve Data free tier:** The free tier covers US-listed instruments only. The TSX Composite (`GSPTSE`) and direct WTI crude returns 404. So the dashboard used:

- **TSX:** EWC (iShares MSCI Canada ETF, NYSE Arca) — correlation >0.95 to TSX Composite, priced in USD
- **Crude oil:** USO (United States Oil Fund ETF) — tracks WTI direction, priced in USD

Both were documented as proxies. Both worked. But they were workarounds, not the real thing.

With Lambda running server-side, CORS is irrelevant. The question became: what free sources exist for the real data?

---

### The Investigation

**TSX Composite — solved quickly.**

Yahoo Finance has `^GSPTSE` — the actual S&P/TSX Composite Index — accessible via their public chart API with no authentication required. Daily data, 3-month history, priced in CAD, 65+ data points. One fetch, no API key, and the values are in Canadian dollars rather than a USD ETF approximation.

**Crude oil — also straightforward.**

FRED (Federal Reserve Bank of St. Louis) publishes `DCOILWTICO` — the WTI crude oil spot price, sourced from the EIA, updated daily. Free API key, clean JSON response, well-documented. A single endpoint replaces the USO proxy with the actual benchmark price in USD per barrel.

**GoC bond yields — more complicated.**

The dashboard had been showing January 7, 2026 as the latest bond yield date for three months. The original assumption was a BoC benchmark bond transition — when the BoC issues a new benchmark bond, the old series can go silent. That's a known issue, already handled with a stale flag in the dashboard.

Stage 4 investigated replacing BoC Valet entirely:

- **Stooq** (`5cay.b`, `10cay.b`): has the right symbols, accessible from a browser, but blocks data center IP ranges. Access requires emailing the operator. Not viable for a Lambda function.
- **OECD Data Explorer**: has Canadian government bond yield data, but at monthly frequency. Not useful for a daily-updating dashboard.
- **FRED**: monthly data for international bond yields. Same problem.
- **Yahoo Finance**: Canadian bond yield symbols (`CA5YT=RR`, `CA10YT=RR`) use Reuters real-time feeds that aren't accessible through the public API.

After exhausting the free options, the honest conclusion: no free source of real-time GoC bond yields exists. Bond markets are over-the-counter. Real-time yield data comes from Bloomberg Terminal or Refinitiv Eikon — both institutional products at institutional prices. The BoC publishes end-of-day yields and is the authoritative source. For a mortgage rate decision tool, end-of-day is entirely adequate.

---

### The Real Bond Yield Problem

With the source decision made (keep BoC Valet), the January 7 date needed an explanation.

The Lambda was running successfully. No errors. The BoC API was returning current data — a direct check confirmed April 1 observations with the expected series keys. But `indicators.json` kept showing January 7.

The cause was in how the `fetch_bonds()` function queried the API:

```python
d = http_get(f"{BOC_BASE}/observations/group/bond_yields_benchmark/json?recent=60")
```

The `recent=N` parameter on the BoC Valet API returns the last N **valid observations** — it counts only dates where the series has data, not calendar days. During a benchmark transition, the series goes silent for some number of days. Those silent days aren't counted.

So `recent=60` was returning 60 valid observations — all from before the gap, ending at January 7. The April resumption data wasn't in the result at all, because `recent=60` had already reached its count before getting there.

The fix is to use a date range instead:

```python
today      = datetime.now(timezone.utc).date()
start_date = today - timedelta(days=90)
d = http_get(
    f"{BOC_BASE}/observations/group/bond_yields_benchmark/json"
    f"?start_date={start_date}&end_date={today}"
)
```

A 90-day calendar range returns all observations in that window — including nulls during the gap, which are filtered out by the existing logic. The result includes both the pre-gap history and the post-resumption current data. Bond date immediately corrected to April 1.

---

### One Operational Fix

During Stage 4 testing, the dashboard showed a 403 error immediately after a push. The cause: the GitHub Actions deploy step runs `aws s3 sync hugo/public/ ... --delete`. The `--delete` flag removes anything in the S3 prefix that isn't in the local Hugo output — including `data/indicators.json`, which is written by Lambda and never part of the Hugo build.

Every push was deleting the data file. The Lambda would recreate it on its next 30-minute run, but there was always a window after each deploy where the dashboard had no data.

Fix: add `--exclude "data/*"` to the sync command. One line change, permanent solution.

---

### What Changed

| Indicator | Before | After |
|---|---|---|
| TSX | EWC ETF (Twelve Data, USD) | ^GSPTSE (Yahoo Finance, CAD index points) |
| Crude Oil | USO ETF (Twelve Data, USD) | WTI spot price (FRED, USD/barrel) |
| GoC bond yields | BoC Valet `recent=60` — stale during transitions | BoC Valet 90-day date range — current |
| Twelve Data symbols | SPY, EWC, USO, CAD/USD (8 calls/run) | SPY, CAD/USD (4 calls/run) |

The signal logic, thresholds, and verdict computation are unchanged. The dashboard looks the same. The data behind it is now more accurate.

---

### What Comes Next

Stage 5 adds historical storage. Right now the Lambda writes a single current snapshot on each run. Stage 5 has Lambda write a timestamped snapshot to DynamoDB on every run, and the dashboard gains the ability to display 3-month and 6-month sparklines alongside the existing 30-day view.

---

*This dashboard is an informational tool for personal use. It is not financial advice. Mortgage decisions depend on personal circumstances that no dashboard can capture. Consult a mortgage broker or financial advisor before making rate decisions.*
