# CHANGELOG — tacedata-site

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

---

## [3.3.1] - 2026-11-11

### Added
- `app/econ/tests/test_boc_rate.py` — first test suite for the econ Lambda (pytest). Covers newest-first and oldest-first Valet responses, cut vs. hike direction, alert re-fire suppression, and the history correction logic.
- `scripts/fix_boc_history.py` — recomputes the `boc` attribute on every DynamoDB snapshot from the Valet date-range series. Dry run by default; `--apply` writes a backup of the original values before rewriting.

### Fixed
- `app/econ/lambda/indicators.py` — `fetch_boc_rate()` read the Valet `recent=10` response as oldest-first, but Valet returns `recent=N` newest-first (date-range queries are oldest-first). `cur` was therefore the rate from ~9 business days earlier, so the dashboard lagged every rate decision by about two weeks, and on 2026-11-11 the window edge produced a false "BoC cut to 2.25%" alert for what was a hike to 2.50% effective 2026-10-29. Now uses a date-range query with an explicit sort. Same class of bug fixed for bond yields in Stage 2.4.
- `fetch_boc_rate()` — `prev` is now the rate before the most recent change and `date` the day the current rate took effect, matching how the dashboard reads them ("Rate RISING/FALLING", "Last decision").
- BoC rate-change alert compares against the ~1-day-old DynamoDB snapshot instead of `payload.boc.prev`, so it fires once per decision rather than every time the 24-hour dedup window expires.

---

## [3.3.0] - 2026-09-14

### Added
- `app/train/scripts/seed_dynamo.py` — `--from-date` excludes earlier days from a seed run entirely, rather than relying only on a per-row state check to protect them.

### Changed
- Block 2 rotation revised (Stage 3.18), effective 2026-09-14 onward. Monday and Sunday swap roles — Monday becomes a rest day, Sunday becomes an active "Gentle Yoga" day (nets back to the usual 5 active / 2 rest per full week, with one irregular 6-active/9-day transitional week where the two changes don't land on the same date). Saturday's session type changes from a timed run/walk interval to **Parkrun (5K)**, a fixed-distance event; `run_interval_minutes`/`session_minutes_target` now hold an estimated finish time (40 → 38 min, declining as the run:walk ratio climbs 1.5:2 → 3:2) rather than a designed session length. Tuesday's interval/ratio progression steepens (30 → 36 min, 1:2 → 3:2). `dev/block-02-days.csv`/`block-02-weeks.csv` updated for 2026-09-14 onward via a throwaway generator script; days before the cutover are untouched.
- Week boundaries pivot from Saturday-start to Monday-start (Stage 3.18), effective 2026-09-14. `week_number` is the sole mechanism `app.js`, `daily_email.py`, and `coach_prompts.py` use to group "this week" — confirmed before implementing, since there is no independent display sort to change instead. The cutover lands on a Monday specifically so no historical row needs its `week_number` rewritten. One unavoidable side effect: Saturday/Sunday now display one week-number lower than before (they sit at the tail of their new week instead of the front of their old one), while Monday–Friday are unaffected.

### Security
- `app/train/scripts/seed_dynamo.py` — `--preserve-state` now also skips any day carrying `notes`, not just `completed=true`. Previously a noted-but-unchecked day (plausible for a rest day) would have been silently overwritten on re-seed, since `put_item` replaces the whole item and the seed template never carries `notes`.
- Live `training-plan-v2` state (the full 2026-09-14 → 2026-10-30 range) was queried and confirmed `completed=false` with no `notes` on all 47 affected rows before writing; a full-fidelity backup of those rows was taken immediately beforehand. Point-in-Time Recovery on the table was confirmed disabled with no on-demand backups existing — left disabled, per the athlete's own call, since writes to this table only happen during deliberate sessions, not continuously.

---

## [3.2.1] - 2026-08-31

### Added
- `app/train/scripts/check_spa_ids.py` — static consistency check between the SPA's JS and its HTML, in both directions. The SPA has no build step, bundler or test runner, so a renamed element id fails silently in the browser; this catches that class of bug without needing a JS runtime installed.
- `app/train/lambda/daily_email.py` — a `dry_run` key on the invocation event composes and returns the briefing without calling SES. The only way to exercise this Lambda was a `test_date` invoke, which sends real mail to the real recipient — as happened while validating the Block 2 cutover.

### Fixed
- `docs/CHANGELOG.md` — restructured into the per-release `## [X.Y.Z] - date` headings `VERSIONING.md` requires. Everything since v3.1.0 had been accumulating under `[Unreleased]`, so entries for Stages 3.9–3.14 are now filed under v3.1.0 and Phase Five under v3.2.0.
- `app/train/docs/STAGES.md` — recorded since Stage 3.10 that the `tracker-coach` CI deploy step had never been exercised through a real run. It was, on 2026-08-31, by the Stage 3.15–3.17 merge.

### Security
- Git tags `v0.10.0` and `v0.11.0` on the remote still pointed at pre-scrub commits, which carried the raw AWS account ID, a CloudFront distribution ID and the deploy role ARN in `config/`. The July 2026 history rewrite corrected `main` but never updated the tags, leaving them as the last publicly reachable pointers to that content on a public repo. Force-updated to the scrubbed commits after confirming no pull-request ref reaches the old ones; the raw account ID now appears in no tag and not in `main`.
- Swept the remaining live infrastructure identifiers out of tracked files into placeholders — S3 bucket names, Cognito user-pool and app-client names, the three Lambda execution-role names, and the GitHub deploy role — across seven files including a published blog post. `CLAUDE.md` classes all of these as not-for-public-repo, and the earlier scrub had only redacted account and distribution IDs.

---

## [3.2.0] - 2026-08-31

### Added
- **Training blocks** (Stage 3.15) — a user now works through several sequential training blocks rather than one fixed plan. Every plan and override row carries a `plan_id`; the `training-users` record names the current one in `active_plan_id`. Because block date ranges never overlap, `{user_id, date}` stays unique and `plan_id` is a plain attribute — an in-place attribute add, not a fourth new-table migration like Stages 3.9 and 3.12.
- `app/train/lambda/plan_merge.py` — `filter_to_plan()`, the shared block-scoping helper used by all three Lambda consumers.
- `GET /days?plan_id=<id>` — reads a past block. Completed blocks stay readable, and stay writable via `PATCH /days/{date}`, so history can still be corrected after a block ends.
- `app/train/scripts/migrate_add_plan_id.py` — Stage 3.15 migration with three independent operations: `--plan-id` backfill (idempotent; only ever tags rows missing the attribute), `--truncate-from` (retires the unlived tail of an abandoned block; dry-run by default, `--yes` to execute), and `--set-active-plan` (the cutover). The truncate aborts outright if any candidate row carries `completed` or `notes` — logged history is never deleted by this script.
- `app/train/lambda/coach_prompts.py` — block-progress facts (`block_day`, `block_total_days`, `block_active_days`, `block_active_days_completed`), the meaningful scoreboard when a block has no race to count down to.
- `dev/block-02-days.csv`, `dev/block-02-weeks.csv` (Stage 3.17) — Block 2, an 8-week consistency block (2026-09-05 → 2026-10-30, 56 days): 5 active days a week at 60 min, two run/walks (one always Saturday, never on consecutive days) and three yoga/stretching/cross-training days, with no long run and no goal race.
- `no_race_block_invents_no_goal` eval case — guards against the coach filling a null `race_date` with a plausible-sounding event instead of saying there isn't one.

### Changed
- `app/train/lambda/days_api.py`, `daily_email.py`, `tracker_coach.py` (Stage 3.15) — all three now scope plan reads to the caller's active block via `plan_merge.filter_to_plan()`. `tracker_coach.py` reads the users record once per turn for both `coach_scope` and `active_plan_id`, and splits the old `_load_merged_plan()` into `_load_plan_rows()` (all blocks, one query) and `_merge_active_block()` — so `[NOTES_LOG]` can span every block while facts and the plan window stay scoped to the current one. `daily_email.py` gained an optional `USERS_TABLE` read.
- `app/train/src/app.js`, `index.html`, `style.css` (Stage 3.16) — plan shape is derived from the block the API returns rather than hardcoded: `planShape()` computes total days, active days and start/end; the race-day countdown became a block-day counter; the progress bar computes its own denominator. 10K branding removed from the page title, headings and login copy.
- `app/train/lambda/daily_email.py` (Stage 3.16) — `_active_day_body()`/`_rest_day_body()` take the block length, so "Day N of 105" is now "Day N of {total}".
- `app/train/lambda/coach_prompts.py` (Stage 3.16) — the coach no longer opens by promising a 10K. A null `race_date`/`weeks_to_race` is stated plainly as "no race in this block" instead of being filled with an invented event, `[NOTES_LOG]` is described as spanning earlier blocks, and `[FACTS]` field names are never quoted back at the athlete.
- `app/train/scripts/seed_dynamo.py` — takes `--plan-id` (required), `--days-csv` and `--weeks-csv`, so any block can be seeded from its own CSVs.
- `app/train/docs/STAGES.md` — the daily-email schedule was recorded as `cron(0 11 * * ? *)` (11:00 UTC / 7am EDT); the live EventBridge rule fires at `cron(0 8 * * ? *)` (08:00 UTC / 4am EDT). The rule is authoritative and the doc has been corrected.

### Security
- `app/train/scripts/migrate_add_plan_id.py` (Stage 3.15) — the truncate operation refuses to delete any row carrying `completed` or `notes`, aborting with the offending dates rather than offering a `--force` override: retiring an abandoned block must never be able to destroy logged history. It is also dry-run by default, requiring an explicit `--yes` to execute, and the backfill only ever writes to rows missing `plan_id` so a re-run cannot relabel a correct row.
- `app/train/lambda/coach_prompts.py` (Stage 3.16) — the notes-injection boundary now explicitly covers notes carried over from earlier training blocks, which `[NOTES_LOG]` began spanning in this stage; those notes are cited as history but can never be presented as the current plan or used to contradict `[FACTS]`.

---

## [3.1.0] - 2026-07-05

### Added
- `app/train/docs/IDENTITY-FOUNDATION-SPEC.md`, `AI-COACH-ENDPOINT-SPEC.md`, `AI-COACH-PROMPTS-AND-EVALS-SPEC.md` — authoritative specs for the identity foundation and AI coach, superseding the prior Phase Three/Four plan in `STAGES.md`/`TODO.md`.
- `app/train/scripts/migrate_to_v2.py` — one-time migration tool (with `--verify`) copying `training-plan` into the `user_id`-partitioned `training-plan-v2`, preserving user state.
- `app/train/lambda/days_api.py` — `_ensure_profile()`: idempotent first-login provisioning of a `training-users` profile record (`coach_scope=plan_only` default); `GET`/`PATCH /settings` to read/write `coach_scope`.
- `training-plan-v2` and `training-users` DynamoDB tables (identity foundation, Stage 3.9); `conversations` table (AI coach, Stage 3.10).
- `app/train/lambda/tracker_auth.py` — server-side auth handler that runs the OAuth2 code + PKCE flow and exposes `/auth/login`, `/auth/callback`, `/auth/refresh`, and `/auth/logout`. The SPA holds the access token in memory; the refresh token is kept in an httpOnly cookie.
- `app/train/lambda/tracker_coach.py` (new Lambda `tracker-coach`) — the AI running coach: thread CRUD (`POST`/`GET /conversations`, `GET`/`PATCH`/`DELETE /conversations/{id}`), a hard medical rail (`RAIL_MODEL` classifier, fails closed, defers before the coach model is ever called), and the coach turn (`POST /conversations/{id}/messages` — merged plan view, facts computed in code, coach-model call via `COACH_MODEL`, persistence). Anthropic Python SDK packaged as a Lambda layer; API key in Secrets Manager, read server-side only.
- `app/train/lambda/plan_merge.py` — shared override-merge logic extracted from `days_api.py`/`daily_email.py`, now reused by `tracker_coach.py` too, so all three consumers show an identical physio-adjusted plan view.
- `app/train/lambda/coach_prompts.py` — the coach's prompt-assembly logic (facts, plan window, history trimming, rail classification, system prompt construction), extracted with zero AWS/env dependencies so it can be imported directly by the eval harness.
- `app/train/evals/run_coach_evals.py` + `cases.py` — eval harness for the coach: 9 rail-classifier cases (gate: 100% recall on the medical class) and 6 coach behavioral cases (grounding, fact-faithfulness under pressure, scope adherence in both modes, medical backstop, notes-injection resistance), scored deterministically and via an LLM-as-judge.
- `.github/workflows/coach-evals.yml` — runs the eval harness on PRs touching the coach prompts, plus manual dispatch; separate from the main deploy pipeline.
- `app/train/scripts/Complete-TrainingDay.ps1` — retroactive day-completion utility, scoped to a caller-supplied `user_id` against `training-plan-v2`.
- `training-plan-overrides-v2` DynamoDB table (Stage 3.12) and `app/train/scripts/migrate_overrides_to_v2.py` — partitions the physio override layer by `user_id`, same shape as the Stage 3.9 plan-table migration.
- `app/train/src/coach.js` (Stage 3.13) — the AI coach's chat UI: thread create/rename/delete/switch, chat bubbles distinguishing user/coach/rail-deferred messages, a dependency-free markdown-lite renderer, and a `coach_scope` toggle. Wired into `index.html`/`app.js`/`style.css` as a second SPA view toggled from the dashboard header.
- `app/train/lambda/coach_prompts.py` / `tracker_coach.py` (Stage 3.14) — the coach now receives a whole-plan `[NOTES_LOG]` digest (`{date, notes}` for every logged day, built from the already-loaded merged view), so it can review the athlete's full journal history on request instead of only the ~2-week plan window; reciting logged notes is treated as data retrieval and no longer trips the medical backstop. New `review_logged_notes` eval case.

### Changed
- `app/train/lambda/days_api.py`, `daily_email.py` — repartitioned by `user_id` (Cognito `sub`) instead of `date` alone: routes derive `user_id` from verified JWT claims (never body/path), `GET /days` uses `Query` instead of `Scan`, and cross-user access returns 404. `daily_email.py`'s per-user briefing logic is extracted into `_brief_user()` so a later multi-user fan-out is a loop, not a rewrite.
- `app/train/scripts/seed_dynamo.py` — `build_item()` takes a required `user_id`; default table is now `training-plan-v2`.
- `app/train/docs/STAGES.md`, `TODO.md` — rewritten around the three specs; Phase Three retitled "Identity Foundation," Phase Four "The AI Coach."
- `app/train/src/auth.js`, `app/train/src/app.js` — SPA reworked to use the server-side `/auth/*` endpoints; the browser no longer stores tokens or runs the token exchange.
- `app/train/src/config.example.js` — trimmed to the API base (Cognito values are server-side now).
- `.github/workflows/deploy.yml` — added the `tracker-auth` Lambda deploy step; trimmed the generated SPA config; bundles `plan_merge.py`/`coach_prompts.py` into the relevant Lambda zips; builds/publishes the Anthropic SDK Lambda layer and deploys `tracker-coach`; syncs the tracker SPA with `Cache-Control: no-cache` (see Fixed).
- `app/train/lambda/plan_merge.py` — override lookups changed from a table-wide `Scan` to a `Query` scoped to the caller's `user_id` (Stage 3.12); used identically by all three consumers.
- `app/train/lambda/coach_prompts.py` — rail and coach backstop prompts re-tuned after real usage showed both over-triggering on any body-part *mention* rather than an actual reported symptom (see Security).

### Fixed
- `deploy.yml` / tracker SPA — the S3 sync set no `Cache-Control` header on any file, so browsers applied heuristic caching and kept serving a stale SPA after a deploy even though the CloudFront cache had been invalidated (worked fine in Incognito, which starts with no cache). Fixed by syncing with `Cache-Control: no-cache` so browsers always revalidate with the origin.

### Security
- `app/train/lambda/days_api.py` — cross-user isolation enforced at the DynamoDB key level (`{user_id, date}`); verified against a real second Cognito identity (`GET`/`PATCH` both 404, owner's data confirmed unchanged). `user_id` is trusted only from the verified JWT, never the request body or path.
- `app/train/src/app.js` — added an `esc()` HTML-escaping helper and applied it to all values rendered into the dashboard via `innerHTML`.
- `app/train/lambda/tracker_coach.py` — every route re-verifies thread ownership from the JWT `sub`, never body/path; the medical rail fails closed on any classifier error or ambiguous response rather than passing an unclassified message to the coach model; the Anthropic API key is read from Secrets Manager server-side only and never appears in `message`/log output.
- `app/train/lambda/coach_prompts.py` — the coach's medical backstop was tightened after the eval harness caught it giving a training recommendation ("hold off on the session") alongside a correct referral to the physiotherapist; the instruction now explicitly forbids any training opinion in that path, not just a clean redirect.
- `training-plan-overrides` (Stage 3.12) — this table was global, un-partitioned reference data, so any caller's plan read could pick up another user's physio overrides regardless of whose account they belonged to. Migrated to a `user_id`-partitioned table and scoped every lookup to the caller; proven with a fixture identity that no longer sees another user's override fields.
- `app/train/lambda/coach_prompts.py` — the rail classifier and the coach's own medical backstop were both judging by *topic* (any body-part word) instead of *intent* (an actual reported symptom, pain, or injury), causing real over-triggering on messages like a bare "leg" or a positive status update. Both prompts re-tuned with explicit examples distinguishing the two; regression cases added to the eval harness.
- Security hardening tracked privately (see `TACE.Website-private`).

---

## [0.20.0] - 2026-04-06

### Added
- `lambda/indicators.py` — threshold alerting: `check_thresholds()` compares current values against 7-day and 1-day DynamoDB snapshots; `_publish_alert()` sends to SNS; `_alert_sent_recently()` / `_record_alert()` provide 24-hour deduplication via DynamoDB ALERT records
- Six alert triggers: GoC 5yr yield up >0.30% / 7 days, yield curve inversion, CPI above 3%, CPI below 2%, BoC rate change, S&P 500 down >10% / 7 days
- `SNS_TOPIC_ARN` env var — alerting disabled gracefully when not set
- Runbook steps 14–18 in `config/runbook-econ-dashboard.md` — SNS topic creation, email subscription, IAM update, env var

### Changed
- `config/lambda-execution-policy.json` — added `sns:Publish` on `econ-indicators-alerts`

---

## [0.19.0] - 2026-04-06

### Added
- `lambda/indicators.py` — DynamoDB snapshot write (`write_snapshot_to_dynamo`) on every run; once-daily history file generation (`generate_history_files`) querying 90 and 180 day windows; `_dynamo_query_all` pagination helper
- `data/history-90d.json`, `data/history-180d.json` — pre-aggregated daily history files written to S3 by Lambda; one entry per calendar day, oldest→newest
- Dashboard period selector (30D / 3M / 6M) — re-renders sparklines from history files; current values, signals, and verdict always from `indicators.json`
- Runbook steps 10–13 in `config/runbook-econ-dashboard.md` — DynamoDB table creation, TTL setup, IAM policy update, DYNAMODB_TABLE env var

### Changed
- `config/lambda-execution-policy.json` — S3 resource widened from `data/indicators.json` to `data/*`; added `dynamodb:PutItem` and `dynamodb:Query` on `econ-indicators-history`

---

## [0.18.0] - 2026-04-05

### Added
- `.github/workflows/scheduled-rebuild.yml` — daily cron workflow (08:00 UTC); triggers Hugo build, S3 sync, and CloudFront invalidation without a push. Enables future-dated posts to publish automatically. `workflow_dispatch` included for manual triggers from the GitHub Actions UI.

---

## [0.17.0] - 2026-04-05

### Added
- Lambda function `econ-indicators` (Python 3.12) — fetches all 8 indicators server-side, writes `tacedata-site/data/indicators.json` to S3 on a 30-minute EventBridge schedule
- Dashboard v0.4.0 — replaces all browser-side fetch logic with a single `fetch('/data/indicators.json')`; removes API key overlay, cooldown timer, diagnostics panel; adds error banner for feed failures
- `lambda/indicators.py` — Lambda handler with BoC, StatCan, and Twelve Data fetchers
- `config/lambda-execution-policy.json` — Lambda execution role IAM policy (S3 write + CloudWatch Logs)
- `config/lambda-trust-policy.json` — Lambda execution role trust policy
- `config/runbook-econ-dashboard.md` — setup runbook for Stage 3 AWS infrastructure
- Blog post: "economic dashboard series: stage 3 — server-side data fetching"
- Architecture diagram (Mermaid) added to Stage 3 post and project page

### Changed
- `.github/workflows/deploy.yml` — added Lambda deploy step (`update-function-code`)
- `config/iam-permissions-policy.json` — added `lambda:UpdateFunctionCode` for GitHub Actions deploy role
- Project page `econ-indicators-proj.md` — updated to Stage 3 state; architecture diagram added; build series links completed

---

## [0.16.0] - 2026-04-04

### Added
- `hugo/static/.well-known/security.txt` (RFC 9116) — vulnerability reporting contact and expiry
- `.github/dependabot.yml` — weekly Dependabot scans for GitHub Actions versions and git submodules
- `hugo.toml` `[params.assets]` — interim favicon pointing to existing logo; eliminates 404s pending proper favicon generation

### Security
- Branch protection applied to `main` — force pushes and deletions blocked
- Favicon TODO added — proper favicon files (ico, 16x16, 32x32) to be generated from tace.logo.png

---

## [0.15.0] - 2026-04-04

### Security
- Rewrote git history (46 commits) using git-filter-repo — scrubbed all AWS resource identifiers from file content and commit messages
- Replaced MIT license with All Rights Reserved (proprietary)
- Removed security clearance disclosure from contact page
- Added `*-Security-Review.md` to `.gitignore`

### Added
- CloudFront Function `tacedata-security-headers` (viewer-response) — sets CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy on all responses
- `config/security-headers.js` — CloudFront Function source
- `config/response-headers-policy.json` — response headers policy reference (not attached; WAF conflict)
- `hugo.toml` dev server headers — mirrors production headers for local CSP testing
- Blog post: "cleaning sensitive data out of git history"

---

## [0.14.0] - 2026-04-03

### Added
- CloudWatch Synthetics canary `tacedata-canary` — checks `https://tacedata.ca` every 5 minutes, alerts on 2 consecutive failures
- CloudWatch Alarm — triggers after 2 failed canary runs; SNS email notification on ALARM and OK transitions
- IAM role for canary Lambda execution (least-privilege: S3 write + CloudWatch metrics)
- `config/canary-script.js` — canary Node.js source (syn-nodejs-puppeteer-9.1 runtime)
- `config/canary-config.json`, `config/canary-permissions-policy.json`, `config/canary-trust-policy.json`
- `config/runbook-cloudwatch-monitoring.md` — full monitoring setup runbook
- Blog post: "site monitoring with aws cloudwatch"

---

## [0.13.0] - 2026-04-03

### Added
- Route 53 hosted zone `<ROUTE53_HOSTED_ZONE_ID>` — authoritative DNS for tacedata.ca
- DNS records in Route 53: MX (Fastmail), SPF, DMARC, DKIM CNAMEs, www CNAME to CloudFront
- ACM certificate issued for tacedata.ca and www.tacedata.ca (us-east-1, DNS validation)
- CloudFront distribution updated: alternate domain names tacedata.ca / www.tacedata.ca, ACM cert attached, SNI-only, TLSv1.2_2021
- Route 53 A alias record for tacedata.ca root pointing to CloudFront
- `config/route53-records.json` — initial DNS records batch file
- `config/route53-acm-validation.json` — ACM DNS validation CNAME records
- `config/route53-alias.json` — A alias record for root domain
- `config/dist-config-live.json` — CloudFront distribution config with aliases and ACM cert
- `config/runbook-stage5-dns-cutover.md` — full cutover runbook with architecture diagram
- Blog posts (draft): Stage 1–5 write-ups — hugo-evaluation, email-migration, aws-pipeline, site-content, dns-cutover

### Changed
- Nameservers at Websavers changed to Route 53 NS records — Route 53 is now authoritative
- `SITE_URL` GitHub Actions variable updated from CloudFront URL to `https://tacedata.ca`
- `docs/STAGES.md` — Stage 4 moved to correct position, marked complete; current stage updated to Stage 5

### Fixed
- `docs/STAGES.md` — Stage 4 was out of order (appeared after Stage 5); corrected

## [0.12.0] - 2026-04-03

### Added
- PaperMod theme added as git submodule; Blowfish retired
- Mermaid diagram support via render hook (`layouts/_default/_markup/render-codeblock-mermaid.html`) and unconditional JS loader in `extend_footer.html`
- Economy dashboard deployed as static HTML at `/ai/projects/econ/`
- Contact page (`content/contact.md`) published
- CloudFront Function `rewrite-index-html` (cloudfront-js-1.0) — rewrites directory-style URLs to `index.html` paths; required for Hugo static output served via S3 OAC
- `config/rewrite-index-html.js`, `config/dist-config.json`, `config/dist-config-updated.json` — function source and distribution config snapshots

### Changed
- `hugo.toml` baseURL removed from source; replaced with `vars.SITE_URL` GitHub Actions variable — site renders correctly at CloudFront URL before domain cutover; update variable at Stage 5
- Menus: removed Evolution and AI Perspective (no content); Contact retained
- `draft: true` removed from contact, Hello World post, oracle-aws-rotation project, sample project, sample post — all now deploy to production

### Fixed
- All subpath navigation returned AccessDenied (S3 OAC does not resolve directory index without rewrite); fixed with CloudFront Function
- Site CSS and JS not loading at CloudFront URL due to hardcoded tacedata.ca baseURL

---

## [0.11.0] - 2026-04-02

### Changed
- Stages renumbered: Content promoted to Stage 4; Domain Cutover moved to Stage 5
- Rationale: site needs representative content before going live on tacedata.ca

---

## [0.10.0] - 2026-04-02

### Added
- Stage 3 AWS pipeline complete
- S3 bucket `<S3_BUCKET_NAME>/tacedata-site/` configured with CloudFront OAC bucket policy
- CloudFront distribution `<CLOUDFRONT_DISTRIBUTION_ID>` — `<CLOUDFRONT_DOMAIN>`
- IAM OIDC provider for GitHub Actions (`token.actions.githubusercontent.com`)
- IAM role `<DEPLOY_ROLE_NAME>` — least-privilege, scoped to this repo and distribution
- GitHub Actions workflow: push to main → hugo build → S3 sync → CloudFront invalidation
- Round-trip validated: change live on CloudFront URL within 2 minutes of push
- Config files: `config/s3.bucket.policy.json`, `config/iam-trust-policy.json`, `config/iam-permissions-policy.json`
- `config/runbook-stage3-aws.md` — full AWS infrastructure setup commands and resource reference
- `README.md` — updated with stack, pipeline, AWS resources, and repo structure

---

## [0.9.0] - 2026-04-01

### Added
- Stage 2 email migration complete — Fastmail active for tacedata.ca
- MX, DKIM (3 CNAME records), and SPF records updated in Websavers DNS
- accounting@tacedata.ca and contact@tacedata.ca configured as aliases to scott.leblanc@tacedata.ca
- All 3 addresses validated receiving email on Fastmail
- Inbox history imported from Websavers via Fastmail built-in IMAP import

---

## [0.8.0] - 2026-04-01

### Changed
- Stages renumbered: Email Migration inserted as Stage 2; pipeline promoted to Stage 3; domain cutover promoted to Stage 4; content promoted to Stage 5
- Rationale: email must be functional on new provider before Stage 4 DNS and ACM work, which triggers validation emails
- `docs/TODO.md` — full rewrite with new stage numbers and email migration tasks as Stage 2
- `docs/STAGES.md` — full rewrite with new stage numbers; Stage 2 rationale documented
- `docs/DECISIONS.md` — AWS stack table stage column updated (Stage 3/4 instead of Stage 2/3)

---

## [0.7.0] - 2026-04-01

### Changed
- `docs/STAGES.md` — Stage 2: rewritten to reflect AWS decision, Websavers untouched, test on CloudFront URL
- `docs/STAGES.md` — Stage 3: Websavers review complete, cutover sequence documented with email DNS note, email and domain decisions recorded
- `docs/DECISIONS.md` — AWS stack table: stage column added; ACM and Route 53 correctly placed in Stage 3, not Stage 2

---

## [0.6.0] - 2026-04-01

### Changed
- `docs/DECISIONS.md` — Hosting Target: decision made — AWS direct (S3 + CloudFront + GitHub Actions + Lambda + Cognito); Netlify path closed; cost confirmed at ~$1-5 USD/month
- `docs/TODO.md` — Stage 2 replanned with concrete AWS infrastructure and pipeline tasks

---

## [0.5.0] - 2026-03-29

### Changed
- `docs/DECISIONS.md` — Email Hosting: aliases confirmed as the model, Fastmail identified as preferred provider, Zoho free tier as viable fallback, inbox migration downgraded to nice-to-have
- `docs/TODO.md` — Stage 3: domain count set at minimum 3, email migration tasks simplified
- `docs/websavers.md` — Open decisions updated to reflect clarifications

---

## [0.4.0] - 2026-03-29

### Added
- `docs/websavers.md` — findings recorded: renewal July 14 2026, 5 domains at ~$25 CAD each, 3 email addresses with inbox history, hosting bundled free

### Changed
- `docs/DECISIONS.md` — Email Hosting: constraints documented (IMAP export required, aliases vs. inboxes decision needed, domains cost comparison added)
- `docs/TODO.md` — Stage 3 fully replanned: email migration sequence, domain decisions, DNS cutover steps, hard deadline explicit

---

## [0.3.0] - 2026-03-29

### Added
- `docs/websavers.md` — account review checklist; must be completed before Stage 3 decisions
- `docs/DECISIONS.md` — Hosting Target: full architecture analysis, AWS cost breakdown, DNS delegation vs. transfer distinction, sequencing options
- `docs/DECISIONS.md` — Site Structure: confirmed URL structure and two-layer architecture (static Hugo + utilities with auth)
- `docs/DECISIONS.md` — Email Hosting: blocked on Websavers review, options documented

### Changed
- `docs/TODO.md` — Stage 2 updated: GitHub Pages eliminated, hosting decision reframed around architecture discovery
- `docs/TODO.md` — Stage 3 updated: Websavers review as prerequisite, DNS delegation and transfer treated as separate operations
- `docs/TODO.md` — Stage 4 updated: site structure confirmed, utilities section added
- `docs/STAGES.md` — Stage 2 updated: hosting analysis summarized, rationale for eliminating GitHub Pages documented
- `docs/STAGES.md` — Stage 3 updated: DNS approach clarified, email decision noted as blocked

---

## [0.2.0] - 2026-03-29

### Changed
- Stage 1 closed out — Hugo evaluation complete, Blowfish theme confirmed

### Fixed
- Removed `hugo-eval/themes/tacedata/` evaluation scaffold (not a submodule, not a theme — leftover from Congo/custom theme evaluation)

---

## [0.1.0] - 2026-03-22

### Added
- Hugo Extended v0.158 confirmed installed locally
- `hugo-eval/` workspace initialized with `hugo new site . --force`
- Blowfish theme added as git submodule (`themes/blowfish`)
- `hugo.toml` configured: baseURL, languageCode, title, theme
- `config/_default/params.toml` — color scheme, appearance, header, homepage layout, author block
- `config/_default/menus.toml` — four nav items: Projects, Blog, Evolution, AI Perspective
- `config/_default/languages.en.toml` — language and author configuration
- Logo (PNG, transparent background) at `assets/img/logo.png` and `static/logo.png`
- Sample blog post: "Rotating Oracle Credentials with AWS Secrets Manager"
- Sample project page: "OracleAwsRotation"
- `content/_index.md` — home page stub
- `docs/DECISIONS.md` — theme selection recorded with rationale
- `docs/CHANGELOG.md` — this file

### Evaluated and Rejected
- PaperMod — evaluated, liked, not selected (Blowfish preferred on structure)
- Congo — build errors on Hugo 0.158; abandoned
- Custom theme — rejected; content is the value, not the theme
