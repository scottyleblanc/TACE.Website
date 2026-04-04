---
title: "economic dashboard series: post 1 - what and why"
date: 2026-04-04T17:00:00
draft: false
tags: ["ai", "claude", "canada", "mortgage", "economics", "html", "twelve-data", "boc", "statscanada", "portfolio"]
summary: "first post in a series documenting the build-out of a Canadian economic indicators dashboard."
---

# From a Real Question to a Working Tool — and Why That's Just the Beginning

*This is the first post in a series documenting the build-out of a Canadian economic indicators dashboard. The series covers the full arc: a genuine financial question, a working prototype built with AI, the constraints that emerged from that design, and the architectural decisions made to overcome them — using AWS, Hugo, GitHub Actions, and AI as collaborative tools throughout.*

---

With a proper foundation now in place — a Hugo site, AWS infrastructure, and a Git-based publish workflow — there's a real platform for learning in public. The plan is to build something meaningful in stages, document the decisions along the way, and share both the working results and the thinking behind them. This is the first post in that series, and it starts where most good projects do: with an honest question.

---

## The original problem

Earlier this year, facing a mortgage renewal, I had a straightforward but genuinely difficult question: should I lock in a fixed rate, or stay variable and ride out wherever the Bank of Canada takes things?  I also had basic questions about foundational economics - what is the bond yield?  Why does the relationship between 10yr and 5yr bond prices? and how inflation factor in? (etc)  Why does it feel like the Strait of Hormuz will have an impact on my personal finances?

The internet has no shortage of opinions and information on this. What it doesn't have is a clean, signal-based view of the indicators that actually matter — stripped of media noise, translated into plain English, and specific to the Canadian context. Financial news cycles thrive on drama. What I wanted was the opposite: a small number of reliable signals, updated regularly, that I could check once a week and form a view from.

So I started a conversation with Claude about it. Not "build me a dashboard" — just the underlying questions. What came out of that conversation was a framework: eight economic indicators with a documented relationship to Canadian mortgage rates, each measuring the same underlying question from a different angle — how confident are businesses, consumers, and investors in the future?

The framework breaks into two groups.

**Market and price indicators** — things that move daily and reflect real-time confidence:

- **S&P 500** (via SPY ETF): A broad vote on economic confidence. Sustained declines signal recession risk, which pushes central banks toward rate cuts.
- **TSX Composite** (via EWC ETF): The Canadian equity market, weighted heavily toward financials, energy, and materials — the three sectors most sensitive to BoC decisions.
- **Crude Oil** (via USO ETF): Both an input cost and a leading inflation indicator. Oil price spikes flow through to CPI within months.
- **CAD/USD**: A capital flow signal. A weakening Canadian dollar means foreign money is leaving — often a sign of economic stress before it shows up in official data.

**Macro and rate indicators** — the slower-moving signals that drive the actual mortgage rate environment:

- **BoC Overnight Rate**: The direct driver of variable mortgage payments. Set eight times per year on a fixed schedule.
- **Inflation (CPI)**: Statistics Canada's all-items Consumer Price Index, year-over-year. The BoC's 2% target is the reference point for everything.
- **GoC 5-Year Bond Yield**: Fixed mortgage rates are priced off this yield, plus a lender spread of roughly 1–2%. When this rises, fixed rates follow within weeks.
- **GoC 10-Year Bond Yield**: Long-term growth and inflation expectations. More importantly, the spread between the 10-year and 5-year yields is a recession indicator — an inverted curve (10yr below 5yr) has preceded every major Canadian and US recession.

That framework was useful on its own. But the obvious next question: could this be a live dashboard rather than a conversation?

---

## What got built

The answer was yes, and faster than expected. Working with Claude iteratively over several sessions, a single-file HTML dashboard came together that pulls live data for all eight indicators and translates each one into a plain-English signal.

The layout is two rows of four cards:

```
Row 1 (market/price):  [ S&P 500 ]  [ TSX Canada ]  [ Crude Oil ]  [ CAD/USD ]
Row 2 (macro/rate):    [ BoC Rate ] [ Inflation    ] [ GoC 5yr   ] [ GoC 10yr ]
```

Each card shows a current value, a day-over-day change, a 30-day sparkline, and a signal — something like *"5yr yield up +0.18% over the month — fixed rates may rise soon. Watch."* An overall panel weighs all eight signals together and produces a single paragraph read on whether the environment favours locking in a fixed rate or staying variable.

The data comes from four sources, chosen deliberately for accessibility:

- **Bank of Canada Valet API** — overnight rate and both GoC bond yields. Free, no registration required, accessible directly from the browser.
- **Statistics Canada WDS API** — all-items CPI. Free, no registration required, accessible directly from the browser.
- **Twelve Data** — S&P 500, TSX proxy, crude oil, and CAD/USD. Free tier with registration; 800 API calls per day, 8 calls per minute.

The government APIs load in parallel with no quota concerns. The Twelve Data calls are sequenced with 8-second gaps between symbols to stay within the free tier ceiling. A full refresh takes about 32 seconds and is followed by a 90-second cooldown before the next refresh is permitted.

For anyone who wants to run it: it's a single HTML file, no installation, no server. A free Twelve Data API key is the only requirement.

---

## Where it started to break

The dashboard works. It solves the original problem. But once you start using it across devices, or think about sharing it, or look closely at where the data actually comes from, the constraints become visible.

**Per-device API key entry.** The Twelve Data key is stored in each browser's localStorage. Every new browser or device requires entering it again. Sharing the dashboard with someone else means asking them to register for their own key and enter it before they can load any data. Fine for personal use; real friction at any larger scale.

**CORS restrictions forced proxy choices.** A browser can only call APIs that explicitly permit cross-origin requests. This ruled out several otherwise good data sources and required some workarounds worth being honest about:

The TSX Composite index (GSPTSE) and TSX-listed ETFs like XIU.TO return 404 on Twelve Data's free tier — it only covers US-listed instruments and forex pairs. The dashboard uses EWC (iShares MSCI Canada ETF), a US-listed ETF that holds the same large-cap Canadian companies, with a correlation above 0.95 to the TSX Composite. It's a reliable directional proxy, but it's priced in USD and it is a proxy.

WTI crude oil's historical time series is paywalled on Twelve Data's free tier. The dashboard uses USO (United States Oil Fund), which tracks WTI closely and is fully available on the free tier. Same directional signal, different instrument.

**The GoC bond yield feed has a known fragility.** The Bank of Canada Valet API is excellent for the overnight rate, but the benchmark bond yield series can stop publishing for several weeks when the BoC periodically transitions to a new benchmark bond issue. The dashboard handles this transparently — displaying the last known values with a "BoC feed delayed — last known value" warning — but it's a limitation baked into the data source, not something fixable from the browser. The feed typically recovers on its own within 4–6 weeks of a transition.

**The 90-second cooldown is friction by necessity.** It's the right behaviour to prevent burning through the rate limit, but it's a consequence of architecture — the browser is making all eight upstream API calls directly, on demand, every time someone hits refresh.

None of these are failures. They're the natural ceiling of a browser-only design, and the tool was built to fit honestly within them. The stale data warning is labelled. The proxy ETFs are documented. The cooldown is explained. But understanding the ceiling is what makes the next step interesting.

---

## What this is really about

There's a pattern worth naming directly, because it's the real subject of this series.

AI tools make it genuinely easy to get a working answer to a problem quickly. Ask a question, get a framework. Ask for a tool, get a working HTML file. The dashboard described above is a real example of that — it exists, it works, it answered the original mortgage question.

What's harder, and more valuable, is what comes next: recognizing when a working solution has hit a structural ceiling, understanding *why* the ceiling exists, and making deliberate architectural decisions to raise it. That transition doesn't happen automatically. It requires bringing domain knowledge, engineering judgment, and the willingness to ask "why does this work the way it does?" rather than accepting the first answer that functions.

There's currently a lot of enthusiasm around using AI to solve problems — and that enthusiasm is warranted. But there's a tendency to treat a working HTML file as a finished product, a checkbox beside a task on a list. The real collaborative value between human and AI emerges later, when the human brings the context to recognize that the working prototype has constraints, and the AI helps reason through and implement the architecture that overcomes them. That's what the rest of this series is about.

The ETF proxies in this dashboard aren't an embarrassing shortcut — they're the correct response to a specific API constraint, documented and reasoned through. The 90-second cooldown isn't a bug — it's the honest surface area of a rate limit made visible to the user. The bond yield fragility isn't a failure — it's a known data source limitation, labelled in the dashboard rather than silently hidden.

But all three are solvable with a different architecture. And solving them is the next stage.

---

## What comes next

The dashboard currently lives as a standalone HTML file. The next stage moves it into the Hugo site properly, then migrates data fetching to AWS — a Lambda function that runs on a schedule, fetches all eight indicators server-side, writes the results to S3, and lets the dashboard become a pure display layer.

That architecture eliminates every constraint described above. No API keys in the browser. No CORS restrictions. No rate limit sequencing. No 90-second cooldown. One fast JSON fetch on load. And because the fetching happens server-to-server, the data source choices open up — direct WTI/USD pricing, direct TSX data, and a more reliable bond yield series that isn't subject to benchmark transition gaps.

Each stage will be documented here: what was built, what decisions were made and why, where the constraints came from, and what they taught. The goal isn't a polished portfolio piece that hides the process — it's an honest record of how a real tool gets built and improved, one architectural decision at a time.

The dashboard is available now at [tacedata.ca/projects/econ/interest-rate/](/projects/econ/interest-rate/). The source is on GitHub at [TACE.Website/hugo/static/projects/econ/interest-rate/](https://github.com/scottyleblanc/TACE.Website/blob/main/hugo/static/projects/econ/interest-rate/index.html).

---

*Next in the series: Stage 2 — embedding the dashboard in the Hugo site and setting up the project page that everything else will build from.*

---

*This dashboard is an informational tool for personal use. It is not financial advice. Mortgage decisions depend on personal circumstances that no dashboard can capture — payment tolerance, term length, lender spreads, and personal risk tolerance. Consult a mortgage broker or financial advisor before making rate decisions.*
