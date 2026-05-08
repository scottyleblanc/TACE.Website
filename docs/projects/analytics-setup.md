# tacedata.ca — Traffic Analytics Setup

## Purpose

This document provides context for a Claude Code session to build out web traffic monitoring for tacedata.ca. Read it fully before taking any action.

---

## Infrastructure Context

- **Site**: tacedata.ca — Hugo static site, public GitHub repo, deployed via GitHub Actions
- **Hosting**: AWS — S3 (origin) + CloudFront (CDN) + Route 53 (DNS)
- **Domain registrar**: Websavers (nameserver delegation to Route 53 — do not change this)
- **AWS account**: owner is Scott, operating as TACE Data Management Inc.

The site is fully operational. Migration from WordPress/shared hosting is complete.

---

## Objective

Enable traffic monitoring using CloudFront access logs analyzed via AWS Athena. No client-side JavaScript. No third-party analytics services. No cookies.

This is a learning exercise in AWS-native tooling, and the setup process will be documented as a blog post on tacedata.ca.

---

## Data to Collect

Collect only the fields required to answer these three questions:

| Goal | Field(s) Required |
|---|---|
| Traffic trends over time | `date`, `time` |
| Geographic distribution | `CloudFront-Viewer-Country` (non-default, requires response headers policy) |
| Page visit tracking | `cs-uri-stem`, `sc-status` |
| Traffic source (referrer) | `cs-referer` |

**Do not collect**: IP addresses, user agent strings, query strings, bytes transferred, cache status, or edge location codes. Visitor privacy is a deliberate design goal.

**Important**: CloudFront standard logging captures all fields or none — selective collection is achieved at the query layer in Athena, not at the log capture layer. The one exception is `CloudFront-Viewer-Country`, which requires explicitly enabling a CloudFront response headers policy.

---

## Architecture

```
CloudFront Distribution
    |
    ├── Access logging enabled → S3 log bucket (dedicated, separate from site bucket)
    |       └── prefix: cloudfront-logs/tacedata/
    |
    └── Response Headers Policy → adds CloudFront-Viewer-Country to log entries

Athena
    └── Database: tacedata_analytics
        └── Table: cloudfront_logs
            └── Partitioned by date for query cost efficiency
            └── Points to S3 log bucket
```

---

## Implementation Steps

Work through these in order. Verify each step before proceeding to the next.

### Step 1 — Create S3 Log Bucket

- Create a new S3 bucket dedicated to logs (separate from the site content bucket)
- Suggested name: `tacedata-cloudfront-logs` (or follow existing naming conventions in the account)
- Region: same region as the existing site S3 bucket
- Block all public access
- Enable S3 server-side encryption (SSE-S3 is sufficient)
- Do not enable static website hosting on this bucket
- Create a folder prefix: `cloudfront-logs/tacedata/`

### Step 2 — Enable CloudFront Access Logging

- In the CloudFront distribution for tacedata.ca, enable access logging
- Log destination: the S3 log bucket created in Step 1
- Log prefix: `cloudfront-logs/tacedata/`
- Confirm logging is enabled and note that log files are delivered on a best-effort basis, typically within a few minutes of traffic

### Step 3 — Enable Viewer Country Header

- In CloudFront, create or modify a Response Headers Policy for the tacedata.ca distribution
- Add `CloudFront-Viewer-Country` as a response header
- This populates the country field in log entries using ISO 3166-1 alpha-2 country codes (e.g., `CA`, `US`)
- Associate the policy with the distribution's default cache behavior

### Step 4 — Set Up Athena

- In AWS Athena, create a database: `tacedata_analytics`
- Create a table: `cloudfront_logs` pointing to the S3 log bucket prefix
- Use the standard CloudFront log table schema (tab-separated, with the standard CloudFront log header format)
- Partition the table by date to minimize query costs
- Set up an Athena query result bucket if one does not already exist in this account

### Step 5 — Validate

- Confirm log files are appearing in the S3 log bucket after live traffic hits the site
- Run a test query in Athena confirming the table returns rows
- Confirm `x_forwarded_for` is excluded from queries and `cs_country` (viewer country) is populated

### Step 6 — Build Working Queries

Create and save the following queries in Athena:

1. **Weekly traffic trend** — count of page requests grouped by week
2. **Top pages** — count of requests per `cs-uri-stem`, filtered to `.html` paths or `/` root, excluding asset extensions (`.css`, `.js`, `.png`, `.jpg`, `.woff`, etc.)
3. **Geographic distribution** — count of requests grouped by viewer country
4. **Referrer breakdown** — count of requests grouped by `cs-referer`, highlighting LinkedIn traffic specifically
5. **Combined page + referrer** — top pages with their referrer sources

---

## Constraints and Preferences

- **AWS console or CLI**: either is acceptable; document commands if using CLI so they can be included in the blog post
- **Cost awareness**: target is near-zero incremental cost; Athena charges per query scan — use partitioning and column projection to minimize this
- **No new IAM roles or users** unless strictly necessary — use existing account permissions
- **Security**: the log bucket should not be publicly accessible under any circumstances
- **Naming**: follow AWS naming conventions; use `tacedata` as the consistent identifier prefix

---

## Out of Scope

- Any changes to the Hugo site content or templates
- Any changes to the GitHub Actions deployment pipeline
- Any changes to Route 53 or DNS configuration
- Any client-side JavaScript or third-party analytics integration
- CloudWatch dashboards (possible future addition, not part of this phase)
- Real-time logs via Kinesis (out of scope for this phase)

---

## Deliverables Expected from This Session

1. S3 log bucket created and configured
2. CloudFront logging enabled and verified
3. Viewer country header policy active
4. Athena database and table created and validated
5. Five working saved queries (as listed in Step 6)
6. Brief notes on any decisions made or issues encountered — these will feed the blog post

---

## Notes for the Blog Post

Scott will write the blog post independently. Claude Code should note anything worth documenting:
- Any AWS console steps that were non-obvious
- Any Athena schema decisions or partitioning choices
- Any privacy-relevant decisions (e.g., confirming IPs are not surfaced in queries)
- Approximate setup time per phase

---

## Outcome — 2026-05-07

**The plan did not complete as designed. The CloudFront Free pricing plan blocks all logging features.**

### What was completed

**Step 1 — S3 log bucket** — Done and then reversed.

`tacedata-cloudfront-logs` was created (`ca-central-1`, public access blocked, SSE-S3, `BucketOwnerPreferred`).
`BucketOwnerPreferred` (not `BucketOwnerEnforced`) is required because CloudFront standard logging uses
ACL-based log delivery. `BucketOwnerEnforced` disables ACLs and causes CloudFront to reject the logging
configuration. This was a non-obvious requirement worth documenting.

Bucket was deleted at project close — nothing was ever written to it.

### Where it blocked

**Step 2 — CloudFront logging** — Blocked by pricing plan.

Attempting to enable standard logging via `aws cloudfront update-distribution` returned:

> `InvalidArgument: Distributions with the Free pricing plan can't have the following features: Standard logging`

The distribution was created on CloudFront's **Free pricing plan** ($0/month, 1M requests / 100GB).
This is a newer plan-based pricing model, distinct from the traditional CloudFront pay-per-use model.
The Free plan bundles DDoS protection, WAF, and CDN at no cost — but excludes logging entirely.

### Alternative investigated — WAF logging

The distribution has an auto-created WAF WebACL with three managed
rule groups. Since WAF inspects every request and can log to S3, this was explored as a zero-cost
alternative:

- `aws-waf-logs-tacedata` bucket created (S3 bucket names for WAF logging must start with `aws-waf-logs-`)
- `aws wafv2 put-logging-configuration` returned: `WAFFeatureNotIncludedInPricingPlanException: Enable WAF logging requires PRO plan`

WAF logging is also gated behind the Pro plan. **Both CloudFront standard logging and WAF logging require Pro ($15/month).**

`aws-waf-logs-tacedata` was deleted. A WAF-created `AWSLogs/` folder stub had to be emptied before
the bucket could be deleted — WAF creates folder structure before confirming the logging config succeeds.

### Other options considered

| Option | Assessment |
|---|---|
| Upgrade to Pro ($15/month) | Unblocks both logging features immediately. $180/year for personal site analytics. |
| Lambda@Edge logging to CloudWatch | Technically possible on Free plan. Significant complexity — adds latency, Lambda function to maintain, different log schema. |
| S3 server access logging on origin bucket | Only captures CloudFront cache misses (origin fetches), not all visitor traffic. Severe undercounting. |

### Decision

Close out the project. $15/month is not justified for a personal site at current traffic levels.
Analytics can be revisited if traffic grows to a point where the insight is worth the cost, or if
the Pro plan becomes worth it for other features (CAPTCHA, header-based filtering).

### What this means for the blog post

The story is more interesting than a successful how-to. The actual narrative:
- The intent and design were sound
- Step 1 revealed a non-obvious S3 config requirement (`BucketOwnerPreferred`)
- Step 2 hit a hard pricing tier wall that the Free plan documentation doesn't make prominent
- The WAF logging alternative was investigated and hit the same wall
- The Lambda@Edge path exists but trades cost for complexity
- Conclusion: the Free plan and "near-zero cost" analytics are incompatible on this platform
