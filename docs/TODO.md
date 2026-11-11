# TODO — tacedata-site

Active build checklist. Items move to STAGES.md (complete section) when done.
Stages are defined in `docs/STAGES.md`.

Two tracks:
- **Track 1 (1.x)** — Website build (Hugo, AWS pipeline, DNS, content, monitoring, security)
- **Track 2 (2.x)** — Economic Indicators Dashboard (econ-scaffold stages)

---

## Stage 1.1 — Hugo Evaluation (Complete)

- [x] Install Hugo Extended locally (`winget install Hugo.Hugo.Extended`)
- [x] Run `hugo new site hugo-eval` to initialize site structure
- [x] Evaluate 2-3 themes — PaperMod, Congo, Blowfish; Blowfish selected
- [x] Create sample content — one post, one project page
- [x] Validate local workflow: edit Markdown → `hugo server` → view in browser
- [x] Commit hugo.toml and initial content to repo
- [x] Add `.gitignore` — exclude `hugo-eval/public/`, `hugo-eval/resources/`
- [x] Document theme decision in `docs/DECISIONS.md` with rationale
- [x] Confirm `hugo-eval/` structure matches intended production layout before graduating it

---

## Stage 1.2 — Email Migration (Complete)

- [x] Create Fastmail account; add tacedata.ca as custom domain (scott.leblanc@tacedata.ca)
- [x] Add Fastmail TXT record to Websavers DNS for domain verification
- [x] Configure accounting and contact as aliases forwarding to personal address
- [x] Import inbox history from Websavers via Fastmail's built-in IMAP import
- [x] Change MX records at Websavers to Fastmail mail servers
- [x] Validate all 3 addresses receive email correctly on Fastmail

---

## Stage 1.3 — AWS Pipeline (Complete)

- [x] Create S3 bucket for Hugo output (private, CloudFront access only) — <S3_BUCKET_NAME>/tacedata-site/
- [x] Create CloudFront distribution pointing at S3 bucket — <CLOUDFRONT_DOMAIN>
- [x] Create IAM role for GitHub Actions deployment — <DEPLOY_ROLE_NAME> (least-privilege)
- [x] Configure OIDC trust between GitHub Actions and AWS (no long-lived credentials)
- [x] Write workflow: push to main → hugo build → `aws s3 sync` → CloudFront invalidation
- [x] Store AWS role ARN as GitHub Actions secret
- [x] Validate round-trip: local edit → commit → push → live within 2 minutes
- [x] Document pipeline in README.md

---

## Stage 1.4 — Content (Complete — 2026-04-03)

- [x] Contact page published
- [x] Economy Dashboard deployed at `/ai/projects/econ/` (static HTML, no auth required)
- [x] Theme switched to PaperMod; Mermaid diagram rendering confirmed working
- [x] About page — TACE Data background, evolution from DBA to automation engineer
- [x] Home — profile mode with intro, buttons, social icons
- [x] Projects — tacedata.ca site write-up with architecture and deployment diagrams
- [x] Blog — "new digs" intro post published; Stage 1–5 write-up posts published

---

## Stage 1.5 — Domain Cutover (Complete — 2026-04-03)

- [x] Create Route 53 hosted zone for `tacedata.ca`
- [x] Replicate all existing DNS records into Route 53 — including Fastmail MX records
- [x] Request ACM certificate for tacedata.ca and www.tacedata.ca (DNS validation)
- [x] Add ACM validation CNAME records to Route 53
- [x] Change nameservers at Websavers → Route 53
- [x] Wait for ACM certificate to reach ISSUED status
- [x] Attach tacedata.ca / www.tacedata.ca and ACM cert to CloudFront distribution
- [x] Add A alias record for tacedata.ca root to Route 53
- [x] Update SITE_URL GitHub Actions variable to https://tacedata.ca
- [x] Trigger deploy; validate tacedata.ca loads with SSL
- [x] Confirm email still works on Fastmail after nameserver change

### Remaining (post-cutover)

- [ ] Confirm the 5 domain variants in Websavers dashboard — decide which to keep (minimum 3)
- [ ] Cancel Websavers WordPress hosting and email
- [ ] Optionally initiate domain transfer to Route 53 (5-7 day ICANN window)

---

## Stage 1.6 — Monitoring (Complete — 2026-04-03)

- [x] CloudWatch Synthetics canary — checks https://tacedata.ca every 5 minutes
- [x] CloudWatch Alarm — 2 consecutive failures triggers SNS email alert
- [x] IAM role for canary Lambda execution
- [x] Alarm tested — set-alarm-state confirmed email delivery on ALARM and OK
- [x] Blog post published: "site monitoring with aws cloudwatch"
- [x] Runbook documented: `config/runbook-cloudwatch-monitoring.md`

---

## Stage 1.7 — Security Remediation (Complete — 2026-04-04)

- [x] Security review conducted — 2 HIGH, 2 MEDIUM, 2 LOW, 1 INFO findings
- [x] [HIGH] Scrub AWS resource identifiers from current files
- [x] [HIGH] Rewrite git history (46 commits) — git-filter-repo, file content + commit messages
- [x] [MEDIUM] Remove security clearance disclosure from contact page
- [x] [LOW] Replace MIT license with All Rights Reserved
- [x] [LOW] Add security response headers via CloudFront Function (viewer-response)
  - CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy
  - Tested locally via hugo.toml dev server headers before production deploy
- [x] Blog post published: "cleaning sensitive data out of git history"

---

## Stage 2.1 — Econ Dashboard: Document Origin (Complete — 2026-04-04)

- [x] Blog post published: `econ-stage-1-post.md`

---

## Stage 2.2 — Econ Dashboard: Hugo Integration (Complete — 2026-04-04)

- [x] Dashboard deployed at `/projects/econ/interest-rate/` (v0.3.0 static HTML)
- [x] Project page at `/projects/econ-indicators/` with context and launch button
- [x] Blog post published: `econ-stage-2-post.md`
- [x] Cross-links between Stage 2.1 and Stage 2.2 posts

---

## Stage 2.3 — Econ Dashboard: Server-Side Data Fetching (Complete — 2026-04-05)

- [x] `indicators.json` schema confirmed
- [x] Lambda written: `lambda/indicators.py`
- [x] Dashboard rewritten: v0.4.0 — single JSON fetch, no API key, no cooldown, error banner
- [x] Blog post published: `econ-stage-3-post.md`
- [x] Lambda execution IAM policy: `config/lambda-execution-policy.json`
- [x] Lambda trust policy: `config/lambda-trust-policy.json`
- [x] GitHub Actions deploy step added to `deploy.yml`
- [x] Deploy role `iam-permissions-policy.json` updated: added `lambda:UpdateFunctionCode`
- [x] Setup runbook: `config/runbook-econ-dashboard.md`
- [x] Create Lambda execution IAM role in AWS
- [x] Create Lambda function (`econ-indicators`) in AWS
- [x] Set Lambda environment variables (TD_API_KEY, S3_BUCKET, S3_KEY)
- [x] Create EventBridge schedule (every 30 minutes)
- [x] Add CloudFront cache behavior for `data/*`
- [x] Add `ECON_LAMBDA_FUNCTION_NAME` GitHub Actions variable
- [x] Update deploy role inline policy (add lambda:UpdateFunctionCode)
- [x] Test Lambda manually — verify indicators.json written to S3
- [x] Validate dashboard end-to-end on live site
- [x] Tag: econ-v0.4.0

---

## Stage 2.4 — Econ Dashboard: Data Source Upgrades (Complete — 2026-04-05)

- [x] Evaluate data source options — decision: free sources only, no paid Twelve Data
- [x] Decision: TSX — `^GSPTSE` via Yahoo Finance (real index, CAD, no API key)
- [x] Decision: Crude Oil — `DCOILWTICO` via FRED (WTI spot price, free API key)
- [x] Decision: GoC bond yields — keep BoC Valet; fixed `recent=N` query bug with date range
- [x] Implement approved source changes in `lambda/indicators.py`
- [x] Update dashboard HTML — card labels, source attributions, TSX value format (pts)
- [x] Fix `deploy.yml` — add `--exclude "data/*"` to S3 sync to preserve Lambda-written JSON
- [x] Update `econ-scaffold.md` — data sources table, known constraints
- [x] Blog post: `econ-stage-4-post.md`
- [x] Tag: v2.5.0

---

## Stage 2.5 — Econ Dashboard: Historical Storage (Complete — 2026-04-06)

Goal: Lambda writes a timestamped snapshot to DynamoDB each run. Dashboard gains 3-month and 6-month sparkline options.

- [x] DynamoDB table design — `econ-indicators-history` PK/SK/TTL
- [x] Lambda write logic — `write_snapshot_to_dynamo()` on every run
- [x] Lambda history generation — `generate_history_files()` once daily at midnight UTC
- [x] IAM policy updated — S3 `data/*`, DynamoDB PutItem + Query
- [x] Dashboard UI — period selector (30D / 3M / 6M) in header
- [x] Runbook updated — Steps 10–13 for Stage 5 AWS setup
- [x] Blog post: `econ-stage-5-post.md`
- [x] AWS setup: create DynamoDB table, update Lambda execution role, add DYNAMODB_TABLE env var
- [x] Tag: v2.6.0

---

## Stage 2.6 — Econ Dashboard: Threshold Alerting (Complete — 2026-04-06)

Goal: Lambda detects threshold crossings and publishes to SNS → email.

- [x] Define trigger conditions — 6 triggers across 5yr yield, curve inversion, CPI, BoC rate, S&P 500
- [x] Lambda threshold detection — `check_thresholds()`, `_alert_sent_recently()`, `_record_alert()`, `_publish_alert()`
- [x] Alert deduplication — 24-hour suppression via DynamoDB ALERT records
- [x] IAM policy updated — added `sns:Publish` on `econ-indicators-alerts`
- [x] Runbook updated — Steps 14–18 for Stage 6 AWS setup
- [x] Blog post: `econ-stage-6-post.md`
- [x] AWS setup: create SNS topic, subscribe email, update Lambda role policy, add SNS_TOPIC_ARN env var
- [x] Tag: v2.7.0

---

## Fix — Econ Dashboard: BoC Rate Ordering (Complete — 2026-11-11)

Goal: correct the reversed BoC overnight rate (false "cut" alert, wrong dashboard rate) and its history.

- [x] Root cause — `fetch_boc_rate()` read Valet `recent=10` as oldest-first; it is newest-first
- [x] `fetch_boc_rate()` — date-range query, explicit sort, `prev`/`date` = rate before / date of last change
- [x] BoC alert compares against the ~1-day-old snapshot, not `payload.boc.prev`
- [x] Regression tests — `app/econ/tests/test_boc_rate.py`
- [x] History correction script — `scripts/fix_boc_history.py` (dry run by default, backs up before writing)
- [x] Deploy Lambda (merge to main)
- [x] Dry run, then `--apply`, `fix_boc_history.py` against DynamoDB — 658 of 10,669 snapshots corrected (2.25 -> 2.50, 2026-10-29 .. 2026-11-11); re-check shows 0 wrong
- [x] Invoke Lambda with `{"force_history": true}` to regenerate history-90d / history-180d
- [x] Verify live `indicators.json` and history files show 2.50% from 2026-10-29
- [x] Tag: v3.3.1 (and v3.3.0 retro-tagged on 6ed0826)

---

## Fix — Econ Dashboard: Adversarial Review Hardening (v3.4.0, In Progress — 2026-11-11 — all issues resolved, release pending)

Goal: resolve every finding from the 2026-11-11 adversarial review of the econ Lambda and dashboard,
and add test coverage that prevents the BoC ordering class of bug from recurring.

### Issues

- [x] **R1 (High, v3.3.1 regression)** — BoC "Rate HELD" signal unreachable. `boc.prev` is now the rate before the last change, so `cur != prev` until the next change; the dashboard shows "Rate RISING — strong case to lock in fixed" and casts a `lock` verdict vote indefinitely, including after a hold decision. Must ship before the 2026-12-09 decision.
- [x] **R2 (High)** — BoC decision schedule hardcoded for 2026 only (`BOC_DATES_2026` in the dashboard). After 2026-12-09 the "Next decision" line falls back to a placeholder, and R1's fix depends on the schedule. Move the schedule into the Lambda, add 2027 dates, emit last-decision outcome and next-decision date in the feed.
- [x] **R3 (Medium)** — Three alerts test a persistent condition, not a crossing: `b10_invert`, `b5_up_7d`, `sp_down_7d`. While the condition holds, the same alert re-sends every 24 h (dedup window). Latent — not observed in the last 90 days of logs.
- [x] **R4 (Medium, same class as v3.3.1)** — Fetchers rely on implicit API ordering: `fetch_bonds` (Valet, assumes oldest-first), `fetch_td_equity` (Twelve Data, assumes newest-first and reverses), `fetch_tsx` (Yahoo, assumes oldest-first). Sort explicitly by date.
- [x] **R5 (Medium, process)** — `deploy.yml` deploys the Lambda without running tests. Add a pytest gate before the Lambda update step.
- [x] **R6 (Low) [SEC]** — Raw upstream exception text is published in the public `indicators.json` `errors` key and rendered on the dashboard. Publish a generic per-source message; log full detail to CloudWatch only.
- [x] **R7 (Low)** — Alert dedup record is written after publish; if the DynamoDB write fails the alert re-sends every 30 min. Record before publish.
- [x] **R8 (Low)** — Bond `stale` flag uses >5 calendar days; false "Bond data delayed" warning over the Christmas/New Year market closure. Use business days.
- [x] **R9 (Low)** — Dashboard "Last decision" shows the rate's effective date (e.g. 2026-10-29), not the announcement date (2026-10-28). Show the announcement date from the schedule.
- [x] **R10 (Low) [SEC]** — Dashboard notes panel renders saved notes via `innerHTML`. Self-only (viewer's own localStorage), but use `textContent`.
- [x] **R11 (Low)** — CPI alert text uses one decimal, so a crossing above 3.0% reads "now 3.0%" (seen 2026-08-17). Use two decimals.
- [x] **R12 (Low)** — Dashboard 2026 schedule lists 2026-09-09; the actual decision was 2026-09-02 (BoC 2027 schedule release reconfirms 2026-09-02, 10-28, 12-09; `fad-press-release-2026-09-09` 404s). Correct when the schedule moves to the Lambda (R2).

### Test coverage

- [x] Order-independence — every fetcher returns identical output for oldest-first, newest-first and shuffled input
- [x] Alert behaviour — all 7 triggers (6 + new `boc_schedule_low`): fire on crossing, silent on consecutive runs while the condition persists, correct direction and wording
- [x] BoC decision outcome — hike, cut, hold, decision day before rate data posts, year boundary, schedule exhaustion
- [x] Payload contract — full `handler()` run with stubbed sources and AWS; `indicators.json` carries every field the dashboard reads
- [x] Live upstream contract tests (opt-in `-m live`) — Valet / Yahoo ordering assumptions, real BoC + bond fetch sanity (FRED and Twelve Data need API keys — covered offline only)
- [x] CI gate (R5)

### Release

- [ ] Deploy, verify live feed and dashboard
- [ ] Tag: v3.4.0

---

## Security — Open Items (from SECURITY.md, 2026-11-11)

Each maps to an entry in `SECURITY.md` → Open items. Not scheduled into a stage yet.

- [ ] **O1 [SEC]** — Tighten main-site CSP: remove `'unsafe-inline'` scripts (hash/nonce or external file for the dashboard script), pin or self-host the jsdelivr Mermaid loader, add `frame-ancestors`, `object-src`, `base-uri`, `Permissions-Policy`; consider HSTS `preload`
- [ ] **O2 [SEC]** — Move Twelve Data and FRED keys from Lambda env vars to Secrets Manager
- [ ] **O3 [SEC]** — Automated tests for tracker Lambdas: JWT-`sub` scoping, cross-user 404, cookie flags, `state` mismatch, Origin check
- [ ] **O4 [SEC]** — Refresh or remove stale `app/train/config/*-execution-policy.json` snapshots (still show retired table + `Scan`)
- [ ] **O5 [SEC]** — Configure throttling on the tracker HTTP API (coach route in particular)
- [ ] **O6** — Drop the rejected email from `auth_guard.py`'s exception message
- [ ] **O7** — Evaluate a WAF on the tracker distribution
- [ ] **O8 [SEC]** — Invited-emails store replacing the static allowlist (already tracked in `app/train/docs/TODO.md`; listed here for completeness)
- [ ] **O9** — Revisit PITR on the tracker plan table if write patterns change
- [ ] **O10** — Decide on Lambda code signing; renew `security.txt` before 2027-04-04
- [ ] Fix stale runbook note: `config/runbook-stage3-aws.md` says "WAF: disabled"; a WAF is attached to the main distribution

---

## Parking Lot — Open

- Confirm 5 domain variants in Websavers dashboard before July 14, 2026 — keep minimum 3, let remainder lapse
- Cancel Websavers WordPress hosting and email (after domain decision)
- AWS certification path — which cert, timeline, how it integrates with site content
- Analytics — simple, privacy-respecting option (Plausible, Fathom, or none)
- Favicon — generate proper favicon files from tace.logo.png using favicon.io or realfavicongenerator.net; add favicon.ico, favicon-16x16.png, favicon-32x32.png to hugo/static/; remove params.assets overrides from hugo.toml
- IAM identity audit — resolve cross-contamination between AWS identities (oar-xxxx used for tacedata operations); ensure tacedata infrastructure actions use a dedicated tacedata IAM identity with appropriate Synthetics, CloudWatch, and canary management permissions
- [x] Scheduled rebuild — `scheduled-rebuild.yml` runs daily at 08:00 UTC; future-dated posts publish automatically without a manual push
