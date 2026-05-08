---
title: "portfolio"
date: 2026-05-07
draft: false
url: /portfolio/
summary: "Projects, stages, posts, and live work — all in one place."
---

A map of the work: what was built, how it was documented, and where to find it.

---

## Traffic Analytics — CloudFront logs and Athena

*Server-side traffic analytics for tacedata.ca using AWS-native tooling — no JavaScript, no cookies, no third parties. Design proved sound; closed when the CloudFront Free pricing plan blocked all logging features.*

**[Project write-up →](/projects/analytics/)**

| Stage | What | Post | Status |
|---|---|---|---|
| 4.1 | Free plan logging wall — CloudFront and WAF logging both gated behind the Pro tier | [Post 1 — what the Free plan doesn't tell you](/posts/analytics-stage-1-post/) | Closed |

---

## Economic Indicators Dashboard

*Eight Canadian economic indicators translated into plain-English mortgage rate signals. Tracks the indicators most relevant to the fixed vs. variable rate decision.*

**[Launch Dashboard →](/projects/econ/interest-rate/)**

| Stage | What | Post | Status |
|---|---|---|---|
| 2.6 | Threshold alerting — SNS email on signal crossings | [Post 6 — threshold alerting](/posts/econ-stage-6-post/) | Complete |
| 2.5 | Historical storage — DynamoDB snapshots, extended sparklines | [Post 5 — historical storage](/posts/econ-stage-5-post/) | Complete |
| 2.4 | Data source upgrades — replace ETF proxies | [Post 4 — data source upgrades](/posts/econ-stage-4-post/) | Complete |
| 2.3 | Server-side data fetching — Lambda pipeline | [Post 3 — server-side data fetching](/posts/econ-stage-3-post/) | Complete |
| 2.2 | Hugo integration — dashboard into the site | [Post 2 — Hugo integration](/posts/econ-stage-2-post/) | Complete |
| 2.1 | Document origin — what was built and why | [Post 1 — what and why](/posts/econ-stage-1-post/) | Complete |

---

## Security Remediation — public repo cleanup

*A post-launch security review uncovered AWS resource identifiers committed to a public repository. Full account of what was exposed, how it was found, and what it took to fix it — including a `git-filter-repo` history rewrite across 46 commits.*

**[Project write-up →](/projects/security-remediation-proj/)**

| Stage | What | Post | Status |
|---|---|---|---|
| 3.2 | Internet cache and the Wayback Machine | [Post 2 — internet cache and the wayback machine](/posts/sec-stage-2-post/) | Complete |
| 3.1 | Cleaning sensitive data out of git history | [Post 1 — cleaning sensitive data out of git history](/posts/sec-stage-1-post/) | Complete |

---

## tacedata.ca — this site

*Personal portfolio and professional development site. Hugo static site hosted on AWS S3 + CloudFront, deployed via GitHub Actions. Documented as a staged build from scratch.*

**[Project write-up →](/projects/tacedata-site-proj/)**

| Stage | What | Post |
|---|---|---|
| 1.7 | Scheduled rebuild — publishing future-dated posts automatically | [Scheduled publishing](/posts/web-feat-1-post/) |
| 1.6 | Site monitoring with AWS CloudWatch | [Site monitoring with aws cloudwatch](/posts/web-stage-6-post/) |
| 1.5 | Cutting over a website | [Stage 5: cutting over a website](/posts/web-stage-5-post/) |
| 1.4 | Building the site itself | [Stage 4: building the site itself](/posts/web-stage-4-post/) |
| 1.3 | Deploying a static site on AWS | [Stage 3: deploying a static site on aws](/posts/web-stage-3-post/) |
| 1.2 | Migrating email before touching DNS | [Stage 2: migrating email before touching dns](/posts/web-stage-2-post/) |
| 1.1 | Choosing a static site generator | [Stage 1: choosing a static site generator](/posts/web-stage-1-post/) |
