---
title: "running tracker: stage 1 — infrastructure and seed data"
date: 2026-06-13T10:00:00
draft: false
tags: ["aws", "dynamodb", "s3", "cloudfront", "acm", "route53", "python", "train", "10k"]
summary: "first post in the running tracker series: provisioning the AWS infrastructure, designing the data model, and seeding 105 days of plan data into DynamoDB."
---

### The Foundation Before the App

*This is the first post in a series documenting the build of a personal running habit tracker at train.tacedata.ca.  The [project page](/projects/running-tracker-proj/) covers the full scope — what it is, why it exists, and where it's heading.  This post covers Stage 1: getting the infrastructure in place and the data into DynamoDB.*

---

The training plan existed before the app did.  A conversation with Claude — starting with a simple prompt about training for a 10K after a 20-year break — produced a 15-week run/walk plan and the CSV schema to go with it: 105 rows, one per calendar day from June 15 to race day on September 27.

Before any infrastructure was provisioned, the right first step was to write a data dictionary.  Not because the data was complex, but because clarifying what the app would read versus what it would write shaped every decision that followed.

---

### The one thing the app needs to do

The tracker has one job: make it easy to check a box after a workout and see the streak tick up.  Session type, coaching focus, run/walk intervals — all of that is context, not the point.  The real question the app answers every day is: did you show up?

This framing drove specific choices.  The `is_active_day` flag matters more than `is_run_day`.  Rest days must not break a streak — they get skipped.  The `PATCH /days/{date}` endpoint is the critical path.  Everything else is secondary.

---

### The data model

The plan has two fundamentally different kinds of data.  Plan data — session type, coaching focus, run/walk intervals, phase — is fixed.  It was generated once, is correct by definition, and the app should never touch it at runtime.  Progress data — whether a day was completed, when, and any notes — is owned by the app and is the only thing that changes.

Labelling these [SEED] and [USER-STATE] in the data dictionary before writing any code made the DynamoDB schema obvious: one table, `date` as the partition key, two sets of columns that never interact on the write path.  The seed script loads [SEED] columns once.  The API only ever updates [USER-STATE] columns.  A `PATCH /days/{date}` that somehow tried to overwrite a session type would hit a condition check before it touched anything.

The model also denormalizes deliberately.  Week-level data — weekly focus, long run target, run/walk ratio for the week — lives in a second CSV.  Rather than doing two DynamoDB reads at query time (one for the day, one for its week), the seed script joins week fields into each day item at seed time.  In a relational database this would be wrong.  In DynamoDB, where joins do not exist and each additional read has a cost and a latency, it is the right call.  The Lambda serves a complete day card with a single `GetItem`.

---

### Infrastructure

The stack for Stage 1 is deliberately minimal: just enough to host something and store the data.

**TLS — wildcard cert, instant validation.**  The existing ACM certificate covered `tacedata.ca` and `www.tacedata.ca` only.  Rather than request a single-domain cert for `train.tacedata.ca`, a wildcard (`*.tacedata.ca`) was requested instead.  ACM public certificates are free, so a wildcard costs the same as a single-domain cert and covers any future subdomain without another request.

What happened next is worth understanding.  The new cert went from `PENDING_VALIDATION` to `ISSUED` in under a minute — before any DNS action was taken.  The reason: ACM validates certificates using a CNAME record in the hosted zone.  The validation CNAME for `*.tacedata.ca` is identical to the one already in Route 53 from the existing cert.  ACM checks for that record on request, finds it already there, and issues immediately.  Both certs now share the same validation record.  This is a useful mental model for how DNS-based cert validation actually works — the validation check is not a one-time event at creation, it happens on demand.

**S3 + CloudFront — OAC, not OAI.**  The `tacedata-train` S3 bucket is private with all public access blocked.  Traffic reaches it only through CloudFront using an Origin Access Control (OAC) — the current best practice, which replaces the older Origin Access Identity (OAI).  The difference matters: OAI is account-scoped and can be attached to multiple distributions, granting S3 access more broadly than intended.  OAC is distribution-scoped — the bucket policy whitelists exactly one CloudFront distribution ARN.  Any new S3-backed distribution should use OAC; OAI should not be used for new builds.

One Windows-specific gotcha: the AWS CLI `--distribution-config file://path` parameter fails silently on Windows, stripping backslashes and passing garbage to the API.  The fix is to read the config into a PowerShell variable and pass it inline:

```powershell
$config = Get-Content 'C:\Temp\tracker-cf-config.json' -Raw
aws cloudfront create-distribution --distribution-config $config --profile tace-aws-admin
```

Also undocumented in the CLI help: `--distribution-config` requires a `Comment` field or the request is rejected with no useful error message.

**Route 53.**  A single A alias record — `train.tacedata.ca` → CloudFront.  CloudFront's hosted zone ID for Route 53 aliases is `Z2FDTNDATAQYW2`, a global constant the same for every CloudFront distribution regardless of region.

**DynamoDB.**  Single table `training-plan`, PK: `date` (ISO 8601 string), on-demand billing.  No sort key.  No indexes.  105 items is small enough that a full scan is fine for now — the first rule of DynamoDB indexes is not to add them before you know what you are querying.

A placeholder `index.html` deployed to S3 confirmed `https://train.tacedata.ca/` resolved over HTTPS before any application code was written.

---

### Seeding the table

The seed script (`seed_dynamo.py`) reads both CSVs, maps each row to a DynamoDB item, and batch-writes all 105 items.  A few decisions worth noting:

**Boolean handling.**  DynamoDB stores booleans natively; the CSV uses the strings `TRUE` / `FALSE`.  The script casts them on import.  The [USER-STATE] boolean `completed` seeds to `False` for all 105 rows.

**Nullable columns.**  `run_interval_minutes`, `run_walk_ratio`, `completed_date`, and `notes` are empty strings in the CSV on days where they do not apply.  The script treats empty as absent — those attributes are not written to the item at all.  DynamoDB scans that filter on field presence return clean results without empty-string noise.

**Numeric types.**  The script converts CSV strings to `Decimal` rather than `int`.  DynamoDB returns numbers as `Decimal` objects; keeping the same type on the write side avoids conversion surprises when the Lambda reads them back.

**Idempotency.**  The script can be re-run safely.  A `--preserve-state` flag skips any day where `completed=True`, so plan data can be re-seeded without wiping user progress.

Validation: a `scan` returned exactly 105 items.  A spot-check on `2026-06-15` confirmed the Day 1 Strength & Mobility row was complete and correct.

---

### End state

`https://train.tacedata.ca/` loads over HTTPS.  DynamoDB has 105 rows seeded and validated.  The domain, CDN, and storage layer are in place.  Nothing is authenticated, nothing is interactive — that is Stage 2.

The reason to stop here and validate before moving on: auth layered on top of a broken data foundation is twice the debugging surface.  Stage 1's job was to make sure the ground was solid.

---

### What comes next

Before documenting the rest of the build, the completed single-user app gets a security review — auth layer, API, DynamoDB access patterns, secrets management, and the deployment pipeline.  The infrastructure stages (auth, backend API, frontend, email, CI/CD) will be documented as the series continues, but the audit comes first.

---

*Next in the series: Stage 2 — security audit — reviewing what the single-user build exposes and whether the controls hold up.*
