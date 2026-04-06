---
title: "economic indicators dashboard"
date: 2026-04-04
draft: false
url: /projects/econ-indicators/
tags: ["aws", "python", "hugo", "twelve-data", "boc", "statscanada", "portfolio", "economics", "canada", "mortgage"]
summary: "A Canadian mortgage rate decision aid — eight economic indicators translated into plain-English signals."
---

## Problem

When facing a mortgage renewal, the question of whether to lock in a fixed rate or stay variable is genuinely difficult. The internet has no shortage of opinion. What it lacks is a clean, signal-based view of the indicators that actually matter — stripped of media noise, translated into plain English, and specific to the Canadian context.

What I wanted was a small number of reliable signals, updated regularly, that I could check once a week and form a view from.

## What It Does

Eight economic indicators with a documented relationship to Canadian mortgage rates. Each measures the same underlying question from a different angle: how confident are businesses, consumers, and investors in the future?

**Market and price indicators** — move daily, reflect real-time confidence:

| Indicator | Source | What it signals |
|---|---|---|
| S&P 500 | SPY ETF (Twelve Data) | Broad economic confidence; sustained declines push central banks toward cuts |
| TSX Composite | ^GSPTSE (Yahoo Finance) | Canadian equity market, weighted toward financials, energy, materials |
| Crude Oil | WTI spot price (FRED) | Input cost and leading inflation indicator; spikes flow to CPI within months |
| CAD/USD | CAD/USD forex (Twelve Data) | Weak CAD raises import costs and constrains BoC rate cuts |

**Macro and rate indicators** — slower-moving, structural signals:

| Indicator | Source | What it signals |
|---|---|---|
| BoC Overnight Rate | Bank of Canada | Direct benchmark for variable-rate mortgages |
| Inflation (CPI) | Statistics Canada | BoC mandate target; above 3% constrains rate cuts |
| GoC 5-year Bond Yield | Bank of Canada | Leading indicator for 5-year fixed mortgage rates |
| GoC 10-year Bond Yield | Bank of Canada | Long-term rate expectations; spread vs 5yr signals curve shape |

Each card shows: current value, day-over-day change, 30-day sparkline, and a plain-English signal — `lock`, `wait`, `watch`, or `neutral`. An **Overall read** panel weighs all eight signals and produces a single paragraph recommendation.

## Architecture

Data fetching runs entirely server-side. An AWS Lambda function runs on a 30-minute schedule, pulls all eight indicators from their upstream sources, and writes to S3. The dashboard fetches that file on load — one request, sub-100ms, no API key required.

**Data pipeline — fetch and serve**

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'fontSize': '18px'}}}%%
flowchart LR
    EB("EventBridge\ncron 30 min"):::aws

    subgraph apis["External APIs"]
        BOC("Bank of Canada\nBoC rate · 5yr · 10yr"):::gov
        SC("Statistics Canada\nCPI"):::gov
        YF("Yahoo Finance\nTSX ^GSPTSE"):::market
        FR("FRED\nWTI crude oil"):::gov
        TD("Twelve Data\nSPY · CAD/USD"):::market
    end

    LM("Lambda\necon-indicators"):::aws
    S3("S3\ndata/indicators.json\ndata/history-*.json"):::aws
    CF("CloudFront\ndata/*"):::aws
    BR("Browser\ndashboard"):::browser

    EB -->|"trigger"| LM
    LM --> BOC & SC & YF & FR & TD
    BOC & SC & YF & FR & TD -->|"JSON"| LM
    LM -->|"PutObject"| S3
    BR -->|"GET /data/*.json"| CF
    CF -->|"OAC signed"| S3
    S3 -->|"JSON"| CF
    CF -->|"JSON"| BR

    classDef aws      fill:#FF9900,stroke:#c97a00,color:#000,rx:8,ry:8
    classDef gov      fill:#1d4ed8,stroke:#1e3a8a,color:#fff,rx:8,ry:8
    classDef market   fill:#16a34a,stroke:#14532d,color:#fff,rx:8,ry:8
    classDef browser  fill:#475569,stroke:#334155,color:#fff,rx:8,ry:8
```

**Storage and alerting**

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'fontSize': '18px'}}}%%
flowchart LR
    LM("Lambda\necon-indicators"):::aws
    DB("DynamoDB\necon-indicators-history"):::aws
    SNS("SNS\necon-indicators-alerts"):::aws
    EM("Email"):::browser

    LM -->|"PutItem snapshot\nevery run"| DB
    DB -->|"7-day lookback\nfor threshold check"| LM
    LM -->|"threshold crossing\n+ not duplicate"| SNS
    SNS -->|"email alert"| EM

    classDef aws      fill:#FF9900,stroke:#c97a00,color:#000,rx:8,ry:8
    classDef browser  fill:#475569,stroke:#334155,color:#fff,rx:8,ry:8
```

<a href="/projects/econ/interest-rate/" class="launch-btn">Launch Dashboard</a>

## Data Sources

| Source | Data | Auth |
|---|---|---|
| Bank of Canada Valet API | BoC overnight rate, GoC 5yr and 10yr bond yields | None |
| Statistics Canada WDS API | All-items CPI (vector 41690973) | None |
| Yahoo Finance | TSX Composite (^GSPTSE) — daily index, 3-month history | None |
| FRED (St. Louis Fed) | WTI crude oil spot price (DCOILWTICO) — daily, 60-day range | API key (free) |
| Twelve Data | SPY, CAD/USD — quote and 30-day history | API key (free) |

All fetching runs in Lambda — no browser API calls, no CORS constraints, no rate limit exposure to visitors.

## Build Series

This project is documented stage by stage as a blog series:

- [Post 1 — What and Why](/posts/econ-stage-1-post/) — the original problem, what was built, and where the browser-only constraints came from
- [Post 2 — Hugo Integration](/posts/econ-stage-2-post/) — moving the dashboard into the site and the iframe-vs-link decision
- [Post 3 — Server-Side Data Fetching](/posts/econ-stage-3-post/) — Lambda architecture, what disappeared from the browser, and error handling philosophy
- [Post 4 — Data Source Upgrades](/posts/econ-stage-4-post/) — replacing ETF proxies, investigating free data sources, and fixing a BoC query bug
- [Post 5 — Historical Storage](/posts/econ-stage-5-post/) — DynamoDB snapshot store, daily history file generation, and the 3M/6M period selector
- [Post 6 — Threshold Alerting](/posts/econ-stage-6-post/) — SNS email alerts on indicator crossings, deduplication logic, and the six trigger conditions

## Current Stage

Stage 5 is live. Lambda writes a timestamped snapshot to DynamoDB on every run. Once daily, it queries the last 90 and 180 days, aggregates to one entry per calendar day, and writes pre-built history files to S3. The dashboard period selector (30D / 3M / 6M) re-renders sparklines from those files.

History was backfilled at launch using a one-time script (`scripts/backfill_history.py`) that fetched 180 days of data from each upstream API — 122 daily records covering October 2025 through April 2026. The 3M and 6M views were populated immediately on launch rather than accumulating gradually.

Stage 6 is live. Lambda checks six threshold conditions after each run and sends SNS email alerts on crossings. A 24-hour deduplication window prevents repeated alerts when a value sits above a threshold for an extended period.

## Tech Used

- HTML / CSS / JavaScript (Canvas 2D for sparklines)
- Python 3.12 (Lambda)
- AWS Lambda · EventBridge · S3 · CloudFront
- Bank of Canada Valet API
- Statistics Canada WDS API
- Yahoo Finance (TSX Composite)
- FRED — St. Louis Fed (WTI crude oil)
- Twelve Data API (S&P 500, CAD/USD)
- Hugo (this site)
