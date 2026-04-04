---
title: "economic dashboard series: stage 2 — hugo integration"
date: 2026-04-04T19:00:00
draft: false
tags: ["hugo", "aws", "portfolio", "economics", "canada"]
summary: "second post in the series: giving the dashboard a proper home on tacedata.ca and the decisions that went into it."
---

# A Proper Home — Moving the Dashboard Into the Hugo Site

*This is the second post in a series documenting the build-out of a Canadian economic indicators dashboard. [Stage 1](/posts/econ-stage-1-post/) covered the original problem, what was built, and where the constraints came from.*

---

Stage 1 ended with a working dashboard and an honest account of its limitations. It was a single standalone HTML file — not connected to the site, not browsable from the navigation, not part of anything. It worked. But "works if you know the URL" is not a finished product.

Stage 2 has a narrow goal: give the dashboard a proper home on tacedata.ca. That means a URL in the site's structure, a project page with context, and a way to get there from the projects listing. Nothing more. The data fetching logic, the API calls, the signal thresholds — none of that changes in this stage. The dashboard itself is identical to v0.3.0.

---

## The first question: how should it be embedded?

There is a meaningful difference between *embedding* a tool and *linking* to one. Hugo is a static site generator. The tacedata.ca site is built around PaperMod, a clean, document-oriented theme — navigation header, text-first layout, light and dark modes.

The dashboard, by contrast, is a full-screen app. Dark background. Custom fonts. Eight data cards, canvas sparklines, an API key overlay. It was designed to fill a browser window — not to sit inside a page that also has a navigation header and a footer.

The common approach in this situation is an iframe: a box on the project page that renders the dashboard inside it. The outer page handles navigation and site chrome; the inner page runs independently. This works technically. But it creates an immediate sizing problem — the dashboard needs to be tall enough to show all eight cards without internal scrolling, which means the iframe ends up very large, which means the outer page has almost nothing else on it. It becomes the worst of both worlds: a project page that exists mostly as a frame around something that could just be its own page.

The right answer was simple: link to it. The project page carries the context — what the dashboard is, what it shows, what its current limitations are, where the series is going. A button takes the user to the dashboard at its own URL, where it fills the window as intended.

---

## Where things ended up

The dashboard lives at `/projects/econ/interest-rate/` as a static HTML file under Hugo's `static/` directory. Files placed there are passed through unchanged — no template wrapping, no PaperMod chrome, just the file served as-is. That is the right choice for a self-contained app with its own design language.

The project page lives at `/projects/econ-indicators/` as a standard Hugo content file. It follows the same structure as the other project pages on the site: problem, what it does, current limitations, data sources, links. The limitations section is honest about what Stage 1 and 2 leave in place — the API key requirement, the 32-second load time, the ETF proxies, the 90-second cooldown — because those constraints are the reason Stage 3 exists. A project page that glosses over them would be less useful, not more polished.

A button at the bottom of the limitations section links through to the dashboard.

---

## What didn't change

Everything inside the dashboard HTML is identical to v0.3.0. This is deliberate.

Stage 2's job was integration, not improvement. The signal thresholds, the data fetching logic, the API sequencing, the localStorage key management, the diagnostics panel — all untouched. Mixing structural work and content changes in the same stage creates risk: a change intended as neutral can interact with something else, and if the dashboard breaks it becomes unclear whether the integration or the content change caused it.

The principle worth keeping for any staged build: do one thing per stage, and leave it stable before starting the next.

---

## What comes next

Stage 3 moves all data fetching server-side. A Lambda function on an EventBridge schedule fetches all eight indicators, writes a JSON file to S3, and the dashboard becomes a simple display layer that reads a cached file on load rather than calling eight upstream APIs directly.

That eliminates the API key requirement, the 32-second load time, the 90-second cooldown, and the CORS restrictions that forced the ETF proxy choices. It also opens the door to better data sources — direct TSX data, direct WTI/USD pricing, and a more robust bond yield feed not subject to BoC benchmark transition gaps.

That is the next post.

---

*This dashboard is an informational tool for personal use. It is not financial advice. Mortgage decisions depend on personal circumstances that no dashboard can capture. Consult a mortgage broker or financial advisor before making rate decisions.*