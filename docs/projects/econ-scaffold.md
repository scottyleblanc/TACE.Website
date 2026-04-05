# tacedata.ca — Economic Indicators Dashboard
## Project Scaffold for Claude Code Working Sessions

This document is the authoritative starting point for any Claude Code session on this project. Read it in full before writing any code or making any changes. It describes what exists, what is planned, the principles that govern how we build, and the context needed to make good decisions without repeated clarification.

---

## Project purpose

A Canadian economic indicators dashboard built as a portfolio piece on tacedata.ca. It tracks eight indicators with a direct relationship to Canadian mortgage rates and translates them into plain-English signals — the primary use case is deciding whether to lock in a fixed mortgage rate or stay variable.

The project is documented publicly as a staged build: a blog series on tacedata.ca tracks each architectural stage, the decisions made, and why. Code quality and decision transparency matter as much as the working result.

---

## Repository and deployment

| Item | Detail |
|---|---|
| Site | tacedata.ca |
| Static site generator | Hugo |
| Hosting | AWS S3 + CloudFront |
| Publish trigger | Git push → GitHub Actions → S3 sync |
| Current dashboard file | `hugo/static/projects/econ/interest-rate/index.html` |
| Dashboard version | v0.4.0 |
| Dashboard URL | `/projects/econ/interest-rate/` |
| Data feed | `https://tacedata.ca/data/indicators.json` (Lambda → S3 → CloudFront) |

The dashboard is integrated into the Hugo site and fetches data from a server-side Lambda pipeline.

---

## What currently exists — v0.3.0

A single self-contained HTML file (~921 lines). No external dependencies beyond Google Fonts. All logic — data fetching, signal computation, sparkline rendering, verdict aggregation — is in one `<script>` block.

### Eight indicator cards, two rows

```
Row 1 (market/price):  [ S&P 500 ]  [ TSX Canada ]  [ Crude Oil ]  [ CAD/USD ]
Row 2 (macro/rate):    [ BoC Rate ] [ Inflation    ] [ GoC 5yr   ] [ GoC 10yr ]
```

Each card: current value · day-over-day change · 30-day sparkline · plain-English signal.

An **Overall read** panel weighs all eight signals and produces a single paragraph recommendation. Signal outcomes are: `lock` · `wait` · `watch` · `neutral`.

A **Weekly observation log** persists notes to `localStorage` (max 24 entries, 6 displayed).

A **Diagnostics panel** exposes raw Twelve Data API responses for troubleshooting TSX symbol availability.

### Data sources and API details

| Indicator | Source | Endpoint / Symbol | Key required |
|---|---|---|---|
| BoC Overnight Rate | Bank of Canada Valet API | `V39079` · `recent=10` | No |
| GoC 5yr Bond Yield | Bank of Canada Valet API | `group/bond_yields_benchmark` · 90-day date range | No |
| GoC 10yr Bond Yield | Bank of Canada Valet API | same group fetch as 5yr | No |
| Inflation (CPI) | Statistics Canada WDS API | vector `41690973` · `latestN=25` | No |
| S&P 500 | Twelve Data | SPY · quote + time_series · outputsize=30 | Yes (free) |
| TSX Canada | Yahoo Finance | `^GSPTSE` · chart · interval=1d · range=3mo | No |
| Crude Oil | FRED (St. Louis Fed) | `DCOILWTICO` · series/observations · 60-day range | Yes (free) |
| CAD/USD | Twelve Data | CAD/USD · quote + time_series · outputsize=30 | Yes (free) |

**Key facts about the current API implementation:**

- All data fetching runs in Lambda — no browser-side API calls, no CORS constraints
- BoC, StatCan, Yahoo Finance, and FRED have no meaningful rate limits at our 30-minute schedule
- Twelve Data (SPY, CAD/USD only): 2 symbols × 2 calls = 4 calls per run, well within 8 calls/minute free tier
- No inter-symbol pause required at current Twelve Data volume
- `indicators.json` is written to S3 on every Lambda run; CloudFront serves it with caching disabled on the `data/*` path
- Lambda environment variables: `TD_API_KEY` (Twelve Data), `FRED_API_KEY` (FRED), `S3_BUCKET`, `S3_KEY`

**Known data source constraints:**

- **GoC bond yields — end-of-day only:** BoC publishes benchmark yields once per day (~5pm ET). No free source of real-time GoC yields exists — bond markets are OTC, real-time data requires Bloomberg/Refinitiv. End-of-day data is adequate for mortgage rate decision-making.
- **GoC bond yields — benchmark transition gap:** During BoC benchmark bond transitions, the `BD.CDN.5YR.DQ.YLD` / `BD.CDN.10YR.DQ.YLD` series go silent. The `bond_yields_benchmark` group endpoint is maintained continuously but `recent=N` counts only valid observations — it skips post-resumption data when a gap exists. Fixed in Stage 2.4: fetch uses a 90-day calendar date range instead of `recent=N`. Stale data (>5 days old) triggers a warning on the card.
- **TSX display:** `^GSPTSE` is an index (currently ~25,000–34,000 pts), not a per-share price. Displayed as integer points. Signal logic uses 30-day percentage change — unaffected by scale.
- **WTI (FRED) weekends/holidays:** FRED uses `"."` for missing observations. Lambda filters these out before computing history.
- **CPI sort order:** Statistics Canada WDS API does not guarantee observation order. Lambda sorts by `refPer` descending before indexing. 25 periods requested to support 13-month YoY sparkline.

**CPI sparkline note:** Unlike all other cards, the CPI sparkline plots the 12-month YoY inflation *rate* (not raw index level). Green = rate falling (inflation cooling). Red = rate rising. This is intentional — plotting raw index level would be permanently red and meaningless.

### Signal thresholds

| Indicator | lock | watch | wait | neutral |
|---|---|---|---|---|
| BoC Rate | cur > prev | — | cur < prev | cur == prev |
| CPI YoY | > 3.0% | 2.5–3.0% | < 2.0% | 2.0–2.5% |
| GoC 5yr (30-day diff) | > +0.30% | +0.10–0.30% | < −0.10% | −0.10 to +0.10% |
| GoC 10yr | — | inverted or +0.30% | < −0.30% | otherwise |
| S&P 500 (30-day pct) | — | −3 to −10% | < −10% | > −3% |
| TSX/EWC (30-day pct) | — | −3 to −10% | < −10% | > −3% |
| Crude/USO (30-day pct) | > +15% | +5 to +15% | < −10% | −10 to +5% |
| CAD/USD (30-day pct) | — | < −3% | — | > −3% |

Verdict logic: `locks >= 2` → lock paragraph; `waits >= 2` → wait paragraph; `watches >= 2` → mixed paragraph; otherwise neutral.

### Visual design

- Dark theme: `#0f0f0e` background, `#1a1a18` card surface
- Typography: DM Mono (monospace body) + Fraunces (serif display/values)
- CSS custom properties for all colours — defined in `:root`
- Sparklines: Canvas 2D, 40px height, 1.5px stroke, filled area with 10% opacity
- Signal colours: green `#4ade80` · red `#f87171` · amber `#fbbf24` · blue `#60a5fa` · accent `#c9b99a`

---

## Staged build plan

The project is being built and documented in stages. Each stage is a blog post on tacedata.ca. **Do not skip stages or implement future-stage work speculatively.** Each stage must leave the dashboard fully functional — no broken intermediate states.

### Stage 2.1 — Document the origin ✅ COMPLETE
Blog post written. Covers the original problem, what was built, the constraints that emerged, and the architectural intent going forward.

### Stage 2.2 — Hugo integration ✅ COMPLETE
Dashboard at `/projects/econ/interest-rate/`. Project page at `/projects/econ-indicators/`. Blog post published.

### Stage 2.3 — AWS data fetching migration ✅ COMPLETE
Lambda `econ-indicators` (Python 3.12) runs every 30 minutes via EventBridge, writes `tacedata-site/data/indicators.json` to S3. Dashboard v0.4.0 fetches that file on load — no API key, no cooldown, no CORS constraints.

**Architecture:**
```
EventBridge cron (hourly or configured schedule)
  → Lambda function (Python)
      → Bank of Canada Valet API  (BoC rate, 5yr yield, 10yr yield)
      → Statistics Canada WDS API (CPI)
      → Twelve Data               (SPY, EWC, USO, CAD/USD)
  → writes indicators.json to S3

Browser (CloudFront)
  → fetches /data/indicators.json (static file, sub-100ms)
  → renders dashboard from cached JSON
```

**What disappears from the dashboard HTML:**
- API key overlay and `localStorage` key management
- All `tdFetch`, `tdQuote`, `tdSeries` functions
- The 90-second cooldown timer
- The 8-second pauses between Twelve Data calls
- The `loadBoC`, `loadBonds`, `loadCPI` fetch functions
- The diagnostics panel (or repurposed for cache debugging)
- The `loadAll` orchestration function

**What stays:**
- All signal computation logic (`spSignal`, `tsxSignal`, `oilSignal`, etc.)
- All rendering logic (`drawSpark`, `fmtChg`, `setSig`, `buildVerdict`, etc.)
- All card HTML and CSS
- The observation log (localStorage, unaffected)

**Lambda output schema (final — as implemented):**
```json
{
  "generated_at": "2026-04-05T00:54:55Z",
  "boc":  { "cur": 2.25, "prev": 2.25, "date": "2026-03-20" },
  "bonds": {
    "b5":  { "cur": 2.93, "prev": 2.94, "history": [...30 values...], "date": "...", "stale": false },
    "b10": { "cur": 3.39, "prev": 3.40, "history": [...30 values...], "date": "...", "stale": false }
  },
  "cpi": { "yoy": 1.78, "mom": 0.55, "yoy_history": [...13 values...], "ref_date": "2026-02" },
  "sp":  { "cur": 655.83, "prev": 655.24, "history": [...30 values...] },
  "tsx": { "cur": 55.32,  "prev": 55.18,  "history": [...30 values...] },
  "oil": { "cur": 137.92, "prev": 124.09, "history": [...30 values...] },
  "cad": { "cur": 0.7171, "prev": 0.7172, "history": [...30 values...] }
}
```

### Stage 2.4 — Data source upgrades ✅ COMPLETE

**Changes made:**
- TSX: EWC proxy (Twelve Data, USD) → `^GSPTSE` via Yahoo Finance (real TSX Composite index, CAD, no API key)
- Crude Oil: USO proxy (Twelve Data, USD) → `DCOILWTICO` via FRED (WTI spot price USD/barrel, free API key)
- GoC bond yields: kept BoC Valet; fixed `recent=N` query bug — switched to 90-day calendar date range to correctly retrieve post-benchmark-transition data
- Twelve Data reduced from 4 symbols (SPY, EWC, USO, CAD/USD) to 2 (SPY, CAD/USD)
- `deploy.yml` fixed: added `--exclude "data/*"` to S3 sync to prevent Lambda-written `indicators.json` from being deleted on each deploy
- Dashboard: card labels updated, TSX value display changed from USD price to index points, source attributions updated

**Sources evaluated and rejected:**
- Stooq (`^tsx`, `5cay.b`, `10cay.b`): good symbols, accessible from browser, blocked from Lambda/AWS IPs — requires email approval from operator
- OECD Data Explorer: Canadian bond yield data available but monthly frequency only
- FRED for GoC bond yields: monthly data only — not suitable for daily sparklines
- Yahoo Finance for GoC bond yields: `CA5YT=RR` / `CA10YT=RR` are Reuters real-time feeds, not accessible via public API

**Why BoC Valet for bond yields:** No free source of real-time GoC bond yields exists. Bond markets are OTC; real-time data requires Bloomberg Terminal or Refinitiv (~$24K/year). BoC publishes end-of-day yields — authoritative, free, and adequate for mortgage rate decision-making.

### Stage 2.5 — Historical storage
**Goal:** Lambda writes a timestamped snapshot to DynamoDB each run. Dashboard gains 3-month and 6-month sparkline options.

**Scope:** DynamoDB table design, Lambda write logic, dashboard UI for period selection.

### Stage 2.6 — Threshold alerting (optional)
**Goal:** Lambda detects threshold crossings and publishes to SNS → email.

**Example triggers:** 5yr yield up >0.3% in a week; CPI crosses above 3%; yield curve inverts.

---

## Principles for all working sessions

**1. Leave the dashboard functional at all times.**
Every commit should result in a working dashboard. No partially-migrated states should be pushed.

**2. Preserve existing signal logic exactly unless explicitly asked to change it.**
Thresholds, signal text, verdict logic, and sparkline colour conventions are deliberate and documented. Do not adjust them incidentally during other changes.

**3. Document constraints honestly.**
When a workaround is in place (EWC proxy, bond yield stale warning), it stays labelled and explained — in code comments, in the README, and in the UI where relevant. Do not silently remove explanatory text.

**4. README stays in sync.**
Any change to data sources, signal logic, API endpoints, or architecture must be reflected in the README before the session ends.

**5. One stage at a time.**
Do not implement Stage 3 work during a Stage 2 session. If a future-stage improvement is obvious, note it in a comment or README section — do not build it speculatively.

**6. Confirm schema before writing Lambda or fetch code.**
The `indicators.json` schema shown above is indicative. Confirm the final schema at the start of any Stage 3 session before writing either the Lambda or the dashboard fetch logic.

**7. CSS variables, not hardcoded colours.**
All colour references must use the CSS custom properties defined in `:root`. No hex values in new CSS rules.

**8. No credentials in code.**
Twelve Data API key: Lambda environment variable only — never in source. AWS credentials: GitHub Actions secrets only.

---

## Things to know that aren't obvious from the code

- **BoC announcement dates are hardcoded.** `BOC_DATES_2026` in the JS is a fixed array from the BoC's published annual calendar. This needs updating each January. In Stage 3 this moves to the Lambda.
- **The bond yield group endpoint was a deliberate v0.3.0 fix.** Previous versions used individual series that went silent during benchmark transitions. The `bond_yields_benchmark` group endpoint is maintained continuously by the BoC. Do not revert to individual series.
- **CPI requires 25 observations, not 14.** 13 months of YoY sparkline data requires 25 raw index values (each YoY rate needs the value 12 months prior). Requesting fewer will cause an index-out-of-bounds error in the sparkline computation.
- **Statistics Canada sort order is not guaranteed.** The WDS API response must be sorted by `refPer` descending before indexing. This is already in v0.3.0 — preserve it.
- **The diagnostics panel is for TSX symbol testing.** It exists to verify that GSPTSE and XIU.TO return 404 on the free tier, and to test the EWC fallback. It can be removed or repurposed in Stage 3 once the browser is no longer calling Twelve Data directly.
- **Sparkline colour for CPI is reversed.** Green = YoY rate falling (good). Red = rising. All other sparklines: green = value up, red = value down. This is intentional and documented in the README.
- **The `ff()` formatter must be applied to all Twelve Data values.** Twelve Data returns price values as strings. `parseFloat()` before any arithmetic, `ff()` for display.

---

## Files in this project

| File | Description |
|---|---|
| `hugo/static/projects/econ/interest-rate/index.html` | Dashboard — v0.4.0 |
| `lambda/indicators.py` | Lambda handler — fetches all 8 indicators, writes indicators.json to S3 |
| `hugo/content/projects/econ-indicators-proj.md` | Project page at `/projects/econ-indicators/` |
| `hugo/content/posts/econ-stage-1-post.md` | Blog post — Stage 1 origin story |
| `hugo/content/posts/econ-stage-2-post.md` | Blog post — Stage 2 Hugo integration |
| `hugo/content/posts/econ-stage-3-post.md` | Blog post — Stage 3 server-side data fetching |
| `config/runbook-econ-dashboard.md` | AWS setup runbook (placeholders) |
| `docs/projects/econ-scaffold.md` | This file |

---

## How to start a working session

1. Read this scaffold in full.
2. Confirm which stage is being worked on.
3. If code files are needed, they will be provided as uploads — do not assume file content from memory.
4. State your plan before writing code. Get confirmation before executing changes that touch signal logic, API endpoints, or the README.
5. At session end: confirm the dashboard is functional, README is updated, and no future-stage work has been speculatively introduced.
