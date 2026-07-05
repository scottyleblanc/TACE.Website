# TODO — Training Plan Habit Tracker (Track 3)

Active build checklist for train.tacedata.ca.
Stage definitions and definitions-of-done: `docs/STAGES.md`.
Build runbook (with real resource values): `TACE.Website-private/config/runbook-tracker.md`
Data dictionary and build brief: `dev/README.md`

**Authoritative specs (supersede any earlier plan):**
- `docs/IDENTITY-FOUNDATION-SPEC.md` — Stage 3.9
- `docs/AI-COACH-ENDPOINT-SPEC.md` — Stage 3.10
- `docs/AI-COACH-PROMPTS-AND-EVALS-SPEC.md` — Stage 3.11

Multi-user is deferred; see the Deferred section at the bottom. `[SEC]` items are
first-class — no stage is complete until its `[SEC]` items are checked off.

---

## Stage 3.7 — Public View (Parked)

- [ ] Design read-only progress page (no auth)
- [ ] TBD

---

## Stage 3.8 — Security Hardening

Findings and remediation tracked in the private repo:
`TACE.Website-private/docs/train/SECURITY-AUDIT.md`. Frontend output-escaping,
CloudFront security headers, and the BFF auth migration (`lambda/tracker_auth.py`)
landed here.

---

# Phase Three — Identity Foundation

Spec: `docs/IDENTITY-FOUNDATION-SPEC.md`. Prerequisite for the AI coach and for
future multi-user. DynamoDB key schema is immutable, so this is a new-table
migration, not a code edit.

## Stage 3.9 — Canonical `user_id`, migration, and users table

**Verify + migrate**
- [x] Confirm current state: `training-plan` keyed on `date` only, no `user_id`, `GET /days` uses `Scan` (spec [STEP 1])
- [x] Create `training-plan-v2`: PK = `user_id` (Cognito `sub`), SK = `date`, mirroring the existing item shape + `user_id`
- [x] Retrieve the owner's `user_id` (Cognito `sub`) from `tacedata-train-pool` — verified against a live access token (decoded in-browser), not just the pool record
- [x] One-time migration script: read every `date`-keyed item, rewrite under `{user_id, date}` — `migrate_to_v2.py`, 105 items
- [x] Repoint `DYNAMODB_TABLE` on **both** `tracker-api` and `tracker-email`
- [x] Update IAM policies for the new table ARN on both execution roles [SEC] — additive inline policies; existing grants (incl. overrides access) untouched

**Cutover safety**
- [x] Cutover under a write freeze (do not use the app during copy → repoint), OR re-run the copy after `DYNAMODB_TABLE` is repointed on both Lambdas to capture any late write [SEC] — no formal freeze enforced; re-ran the migration script post-flip instead, `--verify` passed again
- [x] Preserve rollback: leave the old `date`-keyed `training-plan` untouched until v2 passes Validate; do not delete it in this stage — untouched, retirement deferred pending a soak period
- [x] Reconciliation: assert row-count and user-state parity old vs new — 105 = 105, every `completed`/`completed_date`/`notes` carried across intact — `--verify` passed twice (pre- and post-flip)

**API scoping**
- [x] `days_api.py`: derive `user_id` from JWT claims (`...jwt.claims.sub`) on every route — never body/path [SEC]
- [x] `GET /days`: replace `Scan` with `Query` on the user partition
- [x] `GET`/`PATCH /days/{date}`: key on `{user_id, date}`; cross-user access returns 404 [SEC]

**Email + seed**
- [x] `daily_email.py`: replace `_scan_all()` with a `Query` on a configured owner `user_id` (env var, resolved from the single `users` record); keep single-recipient; structure for later fan-out — `OWNER_USER_ID` env var; per-user briefing extracted into `_brief_user()` so fan-out is a later loop, not a rewrite
- [x] `seed_dynamo.py`: `build_item()` writes a `user_id`; table name + key updated to the composite key
- [x] Leave `training-plan-overrides` keyed on `date` (single-user reference data); merge logic unchanged

**Users table**
- [x] Create `users` table (or PROFILE item): PK = `user_id`; `email`, `display_name`, `coach_scope` (default `plan_only`), `race_goal`, `race_date`, `created_at`/`updated_at` — `training-users`; `race_goal`/`race_date` are optional and unset until a feature writes them (by design — nothing consumes them yet)
- [x] Provision the profile idempotently on first authenticated request (conditional put on absence of `user_id`); repeated logins never overwrite it [SEC] — `_ensure_profile()` in `days_api.py`; verified: first call creates exactly one record, second call leaves `created_at` unchanged. `email`/`display_name` are populated only if present on the token's claims — this Cognito app client's access token does not carry them (confirmed by decoding a live token), so both are correctly omitted rather than written empty
- [x] Confirm no foreign keys / join table introduced — tables share `user_id` only

**Validate**
- [x] All 105 days load and check off end-to-end for the original account against `training-plan-v2` — validated via direct Lambda invocation with the real event shape (`GET /days` → 105 items; `PATCH` → write landed, reverted); not yet exercised through a live browser session
- [x] Daily email still arrives after the migration — manual invoke, correct subject read from v2 (`Day 1 of 105`); inbox delivery not independently re-confirmed this session
- [x] Create a disposable second Cognito identity (or a second `sub`) as an isolation fixture; seed it a couple of rows under its own `user_id` partition [SEC] — reused the pool's existing second (inactive) identity rather than provisioning a new one; did **not** seed rows under its partition (not needed for the isolation proof below, since it has zero rows in v2 by construction)
- [x] Verify `/days` isolation with the fixture: identity B requesting identity A's `date` gets 404 — never A's item; B cannot `PATCH` A's days [SEC] — both confirmed via direct invoke; owner's row verified unchanged after the PATCH attempt
- [x] Confirm the fixture is not picked up by the single-recipient daily email (`OWNER_USER_ID` scoping) — true by code construction (`daily_email.py` briefs only `OWNER_USER_ID`); not separately exercised since the fixture has no routed email address

---

# Phase Four — The AI Coach

Specs: `docs/AI-COACH-ENDPOINT-SPEC.md` and `docs/AI-COACH-PROMPTS-AND-EVALS-SPEC.md`.
Depends on Stage 3.9. Build order within 3.10: CRUD → settings → rail → coach turn.

## Stage 3.10 — Coach Endpoint, Rail, and Data Model

**Status: live as of 2026-07-05.** See Completed Stages in `STAGES.md` for what was built, the two live-observed bugs found during validation, and known gaps carried forward. Deployed out-of-band this session; `deploy.yml` wiring is committed but not yet exercised through a real CI run (branch not merged/pushed).

**Data model + secrets + config**
- [x] Create `conversations` table: PK = `user_id`, SK type-prefixed (`CONV#{id}`, `MSG#{id}#{ts}`)
- [x] Store Anthropic API key in Secrets Manager; read server-side, cache at module scope [SEC]
- [x] Package Anthropic SDK as a Lambda layer; attach to the coach function; update `deploy.yml`
- [x] Config via Lambda env vars: `COACH_MODEL`, `RAIL_MODEL`, `HISTORY_WINDOW_TURNS`, `MAX_TOKENS` — no hardcoded model IDs; source current IDs from the `claude-api` skill at build time [SEC] — `claude-sonnet-5` / `claude-haiku-4-5-20251001`

**Routes (in build order)**
- [x] Thread CRUD scoped to `user_id`: `POST`/`GET /conversations`, `GET`/`PATCH`/`DELETE /conversations/{id}`; every handler confirms thread `user_id` matches caller or returns 404 [SEC]
- [x] `GET`/`PATCH /settings`: read/write `coach_scope` on the users record (not a separate store) — lives in `days_api.py` (tracker-api), not the coach Lambda, so the coach role never needs `training-users` write access
- [x] Hard medical rail as a standalone step: `RAIL_MODEL` classifier before the coach; on trigger persist canned deferral (`role: rail`, `rail_triggered: true`), never call the coach; fails **closed** on error/ambiguous [SEC]
- [x] Coach turn `POST /conversations/{id}/messages`: auth → ownership → load context (rolling window + `coach_scope` + merged plan view) → rail → facts-in-code → prompt assembly → coach model call → persist + bump `updated_at`/`message_count` → return
- [x] House envelope `{ok, data, message}`; `message` always safe to log (no secrets/key) [SEC]

**Plan view (merge — coach must not read raw seed)**
- [x] Coach loads the **merged** plan view (seed `training-plan-v2` + `training-plan-overrides` + user-state), applying the same merge logic as `days_api.py`/`daily_email.py` — never the raw seed alone [SEC]
- [x] Facts-in-code (next long run, today's session, week completed/planned, weeks-to-race) computed from the merged view, so coach guidance matches the physio-adjusted plan
- [x] Extract the merge into one shared module reused by `days_api.py`, `daily_email.py`, and the coach — single source of truth for the plan view (also consolidates streak/counts computed in three places) — `lambda/plan_merge.py`

**Wiring + IAM**
- [x] New routes on the existing HTTP API, Cognito JWT-protected, CORS scoped to `https://train.tacedata.ca` [SEC]
- [x] IAM least-privilege: DynamoDB rw on `conversations` + read on `training-plan-v2` and `training-plan-overrides` (leading-key `user_id` condition where practical); `secretsmanager:GetSecretValue` on the one ARN; CloudWatch Logs only; no wildcards [SEC] — plus a read-only `training-users` grant the spec's IAM section omitted despite the pipeline needing `coach_scope` (closed as a spec gap, not skipped)

**Validate**
- [x] "what is my long run Saturday?" returns an answer grounded in the caller's real data — tested as "how many weeks until my race, and what is today's session" and "what is my session tomorrow"; both matched direct DynamoDB reads exactly
- [x] An injury/medical question is deferred by the rail before the coach model is called [SEC] — also confirmed fail-closed with a deliberately broken `RAIL_MODEL`, and confirmed the rail still triggers on a medical follow-up later in an otherwise-normal thread
- [x] For a day carrying an active override, the coach's stated session equals the override value, not the seed; streak/counts match the SPA [SEC] — strong proof: the seed's own text for that day recommends squats/lunges, the physio override says "no squats or lunges," and the coach's answer matched the override verbatim
- [x] Reusing the Stage 3.9 fixture identity: B cannot list, read, rename, delete, or `POST .../messages` on A's threads — every verb returns 404, never A's data [SEC]

## Stage 3.11 — Coach Prompts and Evaluation

**Status: live as of 2026-07-05.** See Completed Stages in `STAGES.md` for the
one real gap the harness caught (a medical-backstop reply that deferred
correctly but then also gave training advice) and how it was fixed.

- [x] Prompt assembly: `system` string + `messages` array; history as real prior turns (rolling window), not a text blob
- [x] `[FACTS]` + `[PLAN_DATA]` delimited blocks; system prompt declares `[PLAN_DATA]` (incl. `notes`) is data, never instructions [SEC]
- [x] Coach system prompt: shared base + `plan_only` delta + `plan_plus_general` delta — `lambda/coach_prompts.py`
- [x] Rail classifier prompt: binary `medical`/`ok`, strict JSON, fails closed; symptom-specificity boundary
- [x] Eval set: classifier unit evals + coach behavioural evals (grounding, scope, medical backstop, notes injection) — `app/train/evals/cases.py`
- [x] Harness (Python) imports the Lambda's real prompt-assembly code; models config-driven incl. `JUDGE_MODEL`; runnable locally and in CI — `app/train/evals/run_coach_evals.py` imports `coach_prompts.py` from `lambda/` via `sys.path`, the same flat-module import the Lambda runtime uses after `zip -j`; CI wiring in `.github/workflows/coach-evals.yml` (PR + manual dispatch, separate from `deploy.yml`)
- [x] Release gates pass: 100% recall on `medical`; no fabricated facts; correct scope in both modes; medical backstop holds; notes-injection does not alter role/output [SEC] — all pass as of the second harness run (see STAGES.md for the one fix needed between runs)
- [x] Post-launch retune: real usage showed the rail and the coach's own backstop over-triggering on any body-part mention rather than an actual symptom — re-tuned both prompts, added 7 new eval cases from the real conversation, re-validated against production

---

## Stage 3.12 — Partition `training-plan-overrides` by `user_id`

**Status: live as of 2026-07-05.** Security finding, not a planned feature — see `STAGES.md` for the goal and the private runbook (Stage 19) for full mechanics.

- [x] New table `training-plan-overrides-v2` (PK `user_id`, SK `date`); 17 rows migrated with `--verify` parity
- [x] `plan_merge.py`'s override lookup changed from a table-wide `Scan` to a `Query` scoped to the caller [SEC]
- [x] All three consumers (`days_api.py`, `daily_email.py`, `tracker_coach.py`) updated via the shared module
- [x] IAM updated on all three execution roles: `Query` on the new table, old `Scan` grants removed [SEC]
- [x] Isolation proven: a fixture identity seeded on a date with an active owner override sees no override fields merged in [SEC]
- [x] Old table retained pending soak period, matching the Stage 3.9 `training-plan` precedent

---

## Stage 3.13 — Coach Chat UI

**Status: live as of 2026-07-05.**

- [x] Second SPA view (no router, no build step) toggled from the dashboard header
- [x] Thread create/rename/delete/switch; chat bubbles (user/coach/rail-deferred); markdown-lite rendering (no library)
- [x] `coach_scope` toggle backed by the existing `/settings` route
- [x] Local mock preview built and reviewed before touching the live site
- [x] Deployed to S3 + CloudFront; found and fixed a real caching bug (no `Cache-Control` header meant browsers served stale content even after a CloudFront invalidation) — `deploy.yml` updated so future deploys don't regress
- [ ] Full end-to-end validation in a real logged-in browser session beyond the post-cache-fix functional check

---

## Stage 3.14 — Coach whole-plan notes digest

**Status: committed 2026-07-05; live pending deploy.** Post-launch enhancement from real usage: the coach only saw the ~2-week plan window (`plan_window`), so "review the comments I've logged" surfaced at most a handful of the athlete's notes.

- [x] `notes_log(days)` → `{date, notes}` for every day with a note; preloaded as a `[NOTES_LOG]` block — the whole-plan journal, not the full ~15-field rows and not a table scan
- [x] Built from the already-loaded merged view in the coach turn — no extra DynamoDB read; override-aware for free
- [x] Coach grounds on `[NOTES_LOG]`; the notes-injection boundary is extended to it; reciting logged notes is data-retrieval, so a note mentioning past pain no longer trips the medical backstop [SEC]
- [x] `review_logged_notes` eval case added; harness passes `notes_log` through
- [ ] Live eval run (100% medical recall + retrieval/notes cases) + deploy `tracker-coach` + browser validation

---

## Deferred — Multi-User and Later Phases

Schema is built to accept these without rework; out of scope now.

- [ ] Second-user onboarding + Claude plan generation (validate generated output before write) [SEC]; onboarding **updates** the existing users record, does not create it
- [ ] Invite mechanism: replace `auth_guard.py` static `ALLOWED_EMAILS` with an invited-emails store; keep self-signup closed [SEC]
- [ ] Per-user email fan-out: `daily_email.py` loops over the `users` table, briefing each user from their own partition
- [ ] Public view (Stage 3.7)
- [ ] Coach v2: response streaming; summarize-and-drop of old turns; additional scope modes/personas
- [ ] Move coach config from env vars to SSM Parameter Store (swap models without redeploy)

---

## Parking Lot

- Consider custom Cognito domain `auth.tacedata.ca` (already covered by wildcard cert)
- DST handling for EventBridge email rule (adjust cron at clock changes)
- Reduce `/days` first-load latency (~600-900ms, likely `tracker-api` cold start) — provisioned concurrency or a lighter payload
