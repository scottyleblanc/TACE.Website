---
title: "economic dashboard series: stage 5 — historical storage"
date: 2026-04-06T14:00:00
draft: false
tags: ["aws", "lambda", "dynamodb", "s3", "python", "portfolio", "economics", "canada"]
summary: "fifth post in the series: adding a DynamoDB snapshot store so the dashboard can display 3-month and 6-month sparklines alongside the existing 30-day view."
---

### From a Single Snapshot to a History

*This is the fifth post in a series documenting the build-out of a Canadian economic indicators dashboard. [Stage 1](/posts/econ-stage-1-post/) covered the original problem. [Stage 2](/posts/econ-stage-2-post/) moved the dashboard into the Hugo site. [Stage 3](/posts/econ-stage-3-post/) moved all data fetching into AWS Lambda. [Stage 4](/posts/econ-stage-4-post/) replaced ETF proxies with direct data sources.*

---

Stage 4 left the pipeline in a clean state: Lambda runs every 30 minutes, pulls eight indicators from five sources, and writes a single JSON snapshot to S3. The dashboard loads that snapshot and renders everything from it.

The snapshot is exactly that — a single point in time. Every 30 minutes it gets overwritten. Nothing is retained.

Stage 5 changes that.

---

### What Changes

Each Lambda run now does two things:

1. Write the current snapshot to `data/indicators.json` as before — unchanged.
2. Write the same snapshot as a timestamped record to a DynamoDB table.

Once records accumulate, a second Lambda task aggregates them into pre-built history files — one per period — and writes those to S3. The dashboard gains a period selector: **30D** (current behaviour), **3M**, and **6M**. Selecting a longer period fetches the corresponding file and re-renders the sparklines.

No API Gateway. No new CloudFront behaviors. History files are static JSON served through the existing `data/*` path.

---

### DynamoDB Table Design

A single table: `econ-indicators-history`.

| Attribute | Type | Role |
|---|---|---|
| `pk` | String | Partition key — always `"SNAPSHOT"` |
| `ts` | String | Sort key — ISO timestamp e.g. `"2026-04-05T00:30:00Z"` |
| `ttl` | Number | Unix epoch, 1 year from write — DynamoDB deletes expired items automatically |

Single partition key keeps queries simple: `pk = "SNAPSHOT" AND ts BETWEEN start AND end`. At 48 writes per day, the table never grows beyond ~17,500 live items (365 days × 48 runs, with TTL removing anything older than a year).

Each item carries the same indicator values as `indicators.json` — roughly 2–3 KB per record.

---

### History File Schema

Lambda aggregates the DynamoDB records into daily snapshots — one entry per calendar day, taking the latest run of that day. The output written to S3:

```json
{
  "generated_at": "2026-04-05T00:30:00Z",
  "days": 90,
  "snapshots": [
    {
      "date": "2026-01-06",
      "sp": 540.2, "tsx": 24800, "oil": 72.5,
      "cad": 0.718, "b5": 2.85, "b10": 3.22,
      "boc": 4.25, "cpi_yoy": 2.1
    }
  ]
}
```

Two files: `data/history-90d.json` and `data/history-180d.json`. Oldest to newest.

---

### Regeneration Cadence

The history files only need to be regenerated once per day — the sparklines show daily granularity, not 30-minute granularity. Regenerating on every Lambda run (48 times per day) would query DynamoDB 48 times for data that changes once a day.

The Lambda detects whether it is the first run after midnight UTC and regenerates the history files only then. All other runs write only the DynamoDB record and the current `indicators.json`.

---

### Cost

This stage adds one new AWS service: DynamoDB. Everything else — Lambda, S3, CloudFront, EventBridge — is unchanged.

| Item | Monthly estimate |
|---|---|
| DynamoDB writes (48/day × 30 days) | < $0.01 |
| DynamoDB storage (44 MB peak, within 25 GB free tier) | < $0.02 |
| DynamoDB reads (once-daily history regeneration) | ~$0.12 |
| S3 PutObject (2 files/day) | < $0.01 |
| **Total addition** | **~$0.15/month** |

The free tier covers storage entirely (25 GB included always-free). Reads are the variable cost — kept to ~$0.12/month by regenerating the history files once per day rather than on every Lambda run.

Current site cost before Stage 5 is approximately $1–3/month. Stage 5 adds roughly 15 cents.

---

### AWS Infrastructure Required

Two changes to the existing setup before the code can run:

1. **DynamoDB table** — `econ-indicators-history`, on-demand capacity, PK `pk` (String), SK `ts` (String), TTL attribute `ttl`.
2. **Lambda execution role** — add `dynamodb:PutItem` and `dynamodb:Query` permissions scoped to the new table.

The rest of the infrastructure — Lambda function, EventBridge rule, S3 bucket, CloudFront distribution — is unchanged.

---

### What Comes Next

Stage 6 adds threshold alerting — Lambda detects when an indicator crosses a meaningful threshold (5yr yield up >0.3% in a week, CPI above 3%, yield curve inversion) and publishes to SNS for email notification.

---

*This dashboard is an informational tool for personal use. It is not financial advice. Mortgage decisions depend on personal circumstances that no dashboard can capture. Consult a mortgage broker or financial advisor before making rate decisions.*
