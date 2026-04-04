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

| Indicator | Proxy | What it signals |
|---|---|---|
| S&P 500 | SPY ETF | Broad economic confidence; sustained declines push central banks toward cuts |
| TSX Composite | EWC ETF | Canadian equity market, weighted toward financials, energy, materials |
| Crude Oil | USO ETF | Input cost and leading inflation indicator; spikes flow to CPI within months |
| CAD/USD | CAD/USD forex | Weak CAD raises import costs and constrains BoC rate cuts |

**Macro and rate indicators** — slower-moving, structural signals:

| Indicator | Source | What it signals |
|---|---|---|
| BoC Overnight Rate | Bank of Canada | Direct benchmark for variable-rate mortgages |
| Inflation (CPI) | Statistics Canada | BoC mandate target; above 3% constrains rate cuts |
| GoC 5-year Bond Yield | Bank of Canada | Leading indicator for 5-year fixed mortgage rates |
| GoC 10-year Bond Yield | Bank of Canada | Long-term rate expectations; spread vs 5yr signals curve shape |

Each card shows: current value, day-over-day change, 30-day sparkline, and a plain-English signal — `lock`, `wait`, `watch`, or `neutral`. An **Overall read** panel weighs all eight signals and produces a single paragraph recommendation.

## Current Limitations

The dashboard at Stages 1 and 2 runs entirely in the browser. That design works, but it carries real constraints:

- **API key required.** Twelve Data market data requires a free-tier key. The user must enter it once; it is stored in the browser's localStorage. It never leaves the browser, but it is a friction point.
- **Slow load.** The free tier allows 8 calls per minute. Four symbols × 2 calls each = 8 calls, sequenced with 8-second pauses between symbols. A full refresh takes ~32 seconds.
- **90-second cooldown.** Enforced in the browser between refreshes to stay within rate limits.
- **ETF proxies.** GSPTSE (TSX) and WTI crude are not available on the Twelve Data free tier. EWC (iShares MSCI Canada ETF) and USO (United States Oil Fund) are used as proxies. Directionally reliable; not the real thing.

These are known constraints, not oversights. The next stage moves all data fetching server-side, which eliminates all four.

<a href="/projects/econ/interest-rate/" class="launch-btn">Launch Dashboard</a>

## Data Sources

Government data (BoC Overnight Rate, GoC bond yields, CPI) comes from the Bank of Canada Valet API and Statistics Canada WDS API — both public, no API key required. Market data (SPY, EWC, USO, CAD/USD) comes from Twelve Data — free tier, API key required (entered once per browser, stored locally).

A full description of data source constraints and workarounds is in the blog series below.

## Build Series

This project is being documented in stages as a blog series:

- [Post 1 — What and Why](/posts/fin-dash-stage-1-post/) — the original problem, what was built, and the architectural intent

## Current Stage

The dashboard is fully functional as a browser-side application. Upcoming stages will move data fetching server-side (AWS Lambda + EventBridge), eliminating the API key requirement and the 32-second load time.

## Tech Used

- HTML / CSS / JavaScript (Canvas 2D for sparklines)
- Bank of Canada Valet API
- Statistics Canada WDS API
- Twelve Data API
- Hugo (this site)
- AWS S3 + CloudFront (hosting)
