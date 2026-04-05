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

Data fetching runs entirely server-side. An AWS Lambda function runs on a 30-minute schedule, pulls all eight indicators from their upstream sources, and writes a single JSON file to S3. The dashboard fetches that file on load — one request, sub-100ms, no API key required.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'fontSize': '18px'}}}%%
flowchart TD
    EB("EventBridge\ncron — every 30 minutes"):::aws

    subgraph apis["External APIs"]
        BOC("Bank of Canada Valet API\nBoC overnight rate · GoC 5yr · 10yr bond yields"):::gov
        SC("Statistics Canada WDS API\nCPI — vector 41690973"):::gov
        YF("Yahoo Finance\nTSX Composite — ^GSPTSE"):::market
        FR("FRED — St. Louis Fed\nWTI crude oil — DCOILWTICO"):::gov
        TD("Twelve Data\nSPY · CAD/USD"):::market
    end

    LM("Lambda — econ-indicators\nPython 3.12"):::aws
    S3("S3\ndata/indicators.json"):::aws
    CF("CloudFront\ndata/* cache behavior"):::aws
    BR("Browser\ndashboard"):::browser

    EB -->|"triggers every 30 min"| LM
    LM -->|"no auth required"| BOC
    LM -->|"no auth required"| SC
    LM -->|"no auth required"| YF
    LM -->|"API key"| FR
    LM -->|"API key"| TD
    BOC & SC & YF & FR & TD -->|"JSON"| LM
    LM -->|"PutObject · max-age=1800"| S3
    BR -->|"GET /data/indicators.json"| CF
    CF -->|"GetObject · OAC signed"| S3
    S3 -->|"indicators.json"| CF
    CF -->|"indicators.json"| BR

    classDef aws      fill:#FF9900,stroke:#c97a00,color:#000,rx:8,ry:8
    classDef gov      fill:#1d4ed8,stroke:#1e3a8a,color:#fff,rx:8,ry:8
    classDef market   fill:#16a34a,stroke:#14532d,color:#fff,rx:8,ry:8
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

## Current Stage

Stage 4 is live. ETF proxies for TSX and crude oil are replaced with direct sources. GoC bond yields use a corrected BoC Valet query. Twelve Data is now used only for S&P 500 and CAD/USD.

Stage 5 will add historical storage — Lambda writes timestamped snapshots to DynamoDB, and the dashboard gains 3-month and 6-month sparkline options.

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
