# tacedata-site

Personal portfolio and professional development site — [tacedata.ca](https://tacedata.ca).

## Purpose

This repository is the source for the tacedata.ca website. It serves as:

- A portfolio of technical projects (PowerShell automation, Oracle, AWS)
- A record of professional evolution — DBA to automation engineer to cloud-capable practitioner
- A blog for technical writing, published to LinkedIn for broader reach
- A place to share honest observations on the use of AI in real engineering work

This is not a consulting brochure. It is a working journal with proof of work.

---

## Stack

| Component       | Tool                          | Notes                                         |
|-----------------|-------------------------------|-----------------------------------------------|
| Site generator  | Hugo Extended                 | Markdown-based, single binary, fast           |
| Theme           | PaperMod                      | Git submodule at `hugo/themes/PaperMod`  |
| Source control  | Git / GitHub                  |                                               |
| CI/CD           | GitHub Actions                | Pull request → gate; merge to main → build → deploy |
| Hosting         | AWS S3 + CloudFront           | ca-central-1                                  |
| Domain          | tacedata.ca                   | Route 53 + ACM; cutover complete 2026-04-03   |
| Email           | Fastmail                      | scott.leblanc@tacedata.ca                     |

---

## Repository Structure

```
tacedata-site/
├── README.md                       ← this file
├── LICENSE                         ← All Rights Reserved
├── SECURITY.md                     ← security mechanisms, open items, audit record, reporting
├── .claude/settings.json           ← AI agent permissions (checked by gate check GK08)
├── .github/
│   ├── pull_request_template.md    ← pull request checklist
│   └── workflows/
│       ├── gate.yml                ← pull request gate (required check on main)
│       ├── deploy.yml              ← GitHub Actions deploy pipeline (on push to main)
│       └── scheduled-rebuild.yml  ← daily cron rebuild (08:00 UTC)
├── Gate/                           ← this repository's gate config, patterns, hook, unit script
├── tools/gate/                     ← powershell-gate-kit (git subtree; never edited here)
├── config/
│   ├── runbook-stage3-aws.md           ← AWS infrastructure setup (S3, CloudFront, IAM)
│   ├── runbook-stage5-dns-cutover.md   ← DNS cutover runbook
│   ├── runbook-cloudwatch-monitoring.md ← CloudWatch monitoring setup
│   ├── runbook-econ-dashboard.md       ← Econ dashboard Lambda pipeline setup (Stages 3/5/6)
│   ├── lambda-execution-policy.json    ← Lambda IAM execution policy
│   ├── lambda-trust-policy.json        ← Lambda IAM trust policy
│   ├── s3.bucket.policy.json           ← S3 bucket policy (CloudFront OAC)
│   ├── iam-trust-policy.json           ← GitHub Actions deploy role trust policy
│   ├── iam-permissions-policy.json     ← GitHub Actions deploy role permissions policy
│   └── rewrite-index-html.js           ← CloudFront Function source
├── docs/
│   ├── TODO.md                     ← active build checklist
│   ├── STAGES.md                   ← phase definitions and current state
│   ├── DECISIONS.md                ← key decisions and rationale
│   ├── CHANGELOG.md                ← version history
│   ├── VERSIONING.md               ← commit and release conventions
│   ├── templates/                  ← content templates
│   ├── projects/
│   │   └── econ-scaffold.md        ← econ dashboard project scaffold (session context)
│   └── websavers.md                ← Websavers account review findings
├── lambda/
│   └── indicators.py               ← Lambda handler — fetches 8 indicators, writes to S3 + DynamoDB
├── scripts/
│   └── backfill_history.py         ← one-time DynamoDB history backfill (180 days)
└── hugo/                           ← Hugo site source
    ├── hugo.toml                   ← Hugo site config
    ├── config/_default/            ← PaperMod theme config
    ├── content/
    │   ├── _index.md               ← home page
    │   ├── portfolio.md            ← portfolio hub (projects → stages → posts)
    │   ├── posts/                  ← blog post Markdown files
    │   ├── projects/               ← project write-up Markdown files
    │   └── about.md                ← about page
    ├── static/
    │   └── projects/econ/          ← econ dashboard static HTML
    ├── themes/PaperMod/            ← PaperMod theme (git submodule)
    ├── assets/css/extended/        ← custom CSS overrides
    └── layouts/                    ← custom layout overrides
```

---

## Local Development

### Prerequisites

- Hugo Extended v0.158+ (`winget install Hugo.Hugo.Extended`)
- Git

### Run locally

```powershell
cd hugo
hugo server -D
```

Browse to `http://localhost:1313`. The `-D` flag includes draft content.

### Build

```powershell
cd hugo
hugo --minify
```

Output is written to `hugo/public/`. This directory is not committed — it is
generated by the CI/CD pipeline on deploy.

---

## Pull Request Gate

Changes reach `main` only through a pull request whose `gate` check passes; a ruleset
on `main` blocks direct pushes for everyone, the owner included. The gate is
[powershell-gate-kit](https://github.com/scottyleblanc/powershell-gate-kit), added as a
squashed subtree at `tools/gate/` and configured in `Gate/gate.config.psd1`.

| Check | What it does here |
|---|---|
| GK05, GK06 | gitleaks over the files and every new commit |
| GK07, GK15 | No AWS, Cognito, OAuth or email identifier in a commit message or a tracked file (`Gate/message-patterns.psd1`) |
| GK08 | `.claude/settings.json` matches `Gate/agent-permissions.psd1` |
| GK11 | `Gate/Invoke-UnitTest.ps1`: the offline econ and tracker tests, a Hugo build of the site, and a check that every workflow `pip install` is hashed and runs before AWS credentials |

The PowerShell analyzer (GK03) covers `Gate/` only. The version, package and
second-model review checks are off; `Gate/gate.config.psd1` says why for each.

One-time setup per machine and clone (needs PowerShell 7.6, Python 3.12 with the test packages
from `.github/requirements/ci.txt`, and Hugo Extended):

```powershell
python -m pip install --require-hashes -r .github/requirements/ci.txt
& ./tools/gate/Scripts/Install-GateTool.ps1 -Destination (Join-Path -Path $HOME -ChildPath 'gate-tools')
git config core.hooksPath Gate/hooks
```

Run the full gate locally:

```powershell
pwsh -NoProfile -File ./tools/gate/Scripts/Invoke-Gate.ps1 -Unit
```

Update the kit: `tools/gate/Docs/RUNBOOK.md`, UPD-1.

---

## Deployment

### On push to `main` — `deploy.yml`

Merging a pull request into `main` triggers the GitHub Actions pipeline automatically.

1. Checkout repo with submodules (PaperMod theme)
2. Build Hugo Extended with `--minify --baseURL` from `vars.SITE_URL`
3. Authenticate to AWS via OIDC (no long-lived credentials)
4. Sync `hugo/public/` to `s3://<S3_BUCKET_NAME>/tacedata-site/` — `data/*` excluded (Lambda-written files)
5. Invalidate CloudFront distribution to serve updated content
6. Deploy Lambda function code (`lambda/indicators.py`)

### Daily scheduled rebuild — `scheduled-rebuild.yml`

Runs at **08:00 UTC daily** (04:00 ET) regardless of push activity. Performs steps 1–5 above (no Lambda deploy). This enables posts with a future `date:` in their frontmatter to go live automatically on their scheduled date without a manual push.

Can also be triggered manually via the **Run workflow** button in the GitHub Actions UI.

### AWS resources

Private S3 bucket + CloudFront distribution in `ca-central-1`. Resource identifiers
are stored in GitHub Actions variables — not committed to this repository.

### GitHub configuration required

| Type | Name | Purpose |
|---|---|---|
| Secret | `AWS_ROLE_ARN` | IAM role ARN for OIDC authentication |
| Variable | `SITE_URL` | Base URL for Hugo build |
| Variable | `S3_BUCKET_NAME` | S3 bucket name for site content |
| Variable | `CLOUDFRONT_DISTRIBUTION_ID` | CloudFront distribution ID for cache invalidation |
| Variable | `ECON_LAMBDA_FUNCTION_NAME` | Lambda function name for econ dashboard deploy |

See `config/runbook-stage3-aws.md` for site infrastructure setup and `config/runbook-econ-dashboard.md` for the econ dashboard Lambda pipeline.

---

## Current State

See `docs/STAGES.md` for the current phase and what is complete.

---

## Current Security State

| | |
|---|---|
| **As of** | 2026-11-11 — v3.4.0 |
| **Last review** | 2026-11-11 — full-repository review + adversarial review of the econ Lambda and dashboard |
| **Findings** | 12 of 12 econ review findings resolved (2 `[SEC]`) |
| **Open items** | 10 (5 LOW, 5 ADV) — none believed actively exploited |
| **Tests** | Econ Lambda: 83 offline (CI deploy gate) + 6 opt-in live · AI coach: 37 eval cases (CI on prompt changes) · Tracker Lambdas: none yet (open item O3) |

Headline controls: no stored cloud credentials (GitHub OIDC pinned to `main`), private S3 origin
behind CloudFront + WAF, Cognito allowlist with server-side PKCE and HttpOnly refresh cookie,
per-user data isolation keyed on the verified JWT `sub`, AI coach key in Secrets Manager with a
fail-closed medical rail. Full detail, open items and audit record: [`SECURITY.md`](SECURITY.md).

Updated at the end of every implementation stage.
