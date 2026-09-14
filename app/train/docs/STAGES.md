# STAGES — Training Plan Habit Tracker (Track 3)

Phase definitions and current state for the habit tracker at train.tacedata.ca.

Plan: 15-week 5K-to-10K training plan, June 15 – September 27, 2026.
Full build brief: `dev/README.md`

---

## Source of Truth

Phases Three and Four are now defined by three specs in `docs/`, which **supersede
any earlier multi-user / AI-layer plan**:

1. `IDENTITY-FOUNDATION-SPEC.md` — canonical `user_id` and the users table. Build first.
2. `AI-COACH-ENDPOINT-SPEC.md` — coach routes, pipeline, hard medical rail, data model, IAM. Build second.
3. `AI-COACH-PROMPTS-AND-EVALS-SPEC.md` — coach system prompts, rail classifier prompt, eval harness. Build last.

Where a stage below and a spec differ on mechanics, the **spec wins** — the stage
is the checklist, the spec owns the contract. Build sessions should read the
relevant spec, not re-derive from this file.

**Multi-user is deferred.** The identity foundation is built now so that a second
user can be added later with no further migration, but second-user onboarding,
plan generation, invites, and per-user email fan-out are out of scope until we
decide to add them (see [Deferred] at the end).

---

## Current Focus: Phase Six complete, Block 2 rotation revised from 2026-09-14

Stages 3.9–3.17 (Phases Three through Five) are all live. Phase Six (Stage
3.18) revised Block 2's day-of-week rotation and moved the display week from
Saturday-start to Monday-start, both effective 2026-09-14.

The 15-week 10K plan is now **Block 1** — truncated at 2026-08-31 with its 78
lived days, 17 completed sessions and 10 journal entries intact. **Block 2** is
an 8-week consistency block (2026-09-05 → 2026-10-30). From 2026-09-14 on, its
weekly shape is: Tuesday and Saturday active (Saturday now a Parkrun 5K event
rather than a timed interval), Wednesday and Thursday active (strength/yoga,
unchanged), Sunday active (new — Gentle Yoga), Monday and Friday rest.

Loose ends carried forward: the old v1 `training-plan` and
`training-plan-overrides` tables are still retained pending a soak period
(Steps 50 and 71 in the private runbook); no cutover since Stage 3.9 has been
validated through a live browser session rather than direct Lambda invocation;
and Point-in-Time Recovery on `training-plan-v2` is confirmed disabled with no
on-demand backups, left that way deliberately (see Stage 3.18). The coach
eval-harness gates *were* re-run against the Stage 3.16 prompt rewrite, on
2026-08-31 (see the v3.2.1 follow-up below) — this line previously said
otherwise; that was stale and has been corrected.

Stages 3.1–3.6 (Phase One — MVP) are complete and live. Phase Two (security audit,
Stage 3.8) is tracked in the private repo. Stage 3.7 (Public View) remains parked.

Phase mapping to the public project narrative
(`hugo/content/projects/running-tracker-proj.md`):
- Phase One (single-user MVP) = Stages 3.1–3.6 (done)
- Phase Two (security audit) = Stage 3.8 (private repo)
- Phase Three (identity foundation) = Stage 3.9
- Phase Four (the AI coach) = Stages 3.10–3.13

---

## Stage 3.1 — Infrastructure

**Goal:** train.tacedata.ca resolves over HTTPS. S3 bucket, CloudFront distribution,
wildcard ACM cert, and Route 53 record in place. DynamoDB table seeded with all 105 days.

**Definition of done:**
- `https://train.tacedata.ca/` loads (serving placeholder index.html)
- SSL cert valid — `*.tacedata.ca` wildcard (us-east-1)
- S3 bucket `<TRACKER_S3_BUCKET>` — private, CloudFront OAC access only
- DynamoDB table `training-plan` — 105 items seeded, PK = `date`
- Route 53 A alias record for `train.tacedata.ca` → CloudFront

**Runbook:** `TACE.Website-private/config/runbook-tracker.md` Stages 1–5, 13

---

## Stage 3.2 — Auth

**Goal:** Login with Google. Only authenticated users can access the app.

**Definition of done:**
- Cognito User Pool `<COGNITO_USER_POOL_NAME>` with Google IdP
- Cognito Hosted UI at `<COGNITO_HOSTED_UI_DOMAIN>`
- App client configured — code flow, callback to `https://train.tacedata.ca/`
- Login and post-login redirect works end-to-end

**Runbook:** `TACE.Website-private/config/runbook-tracker.md` Stage 6

**Note:** The browser-side token flow described here was later hardened to a
Backend-for-Frontend (BFF) pattern in Stage 3.8 — the refresh token lives only in
an httpOnly cookie and the SPA holds a short-lived access token in memory
(`lambda/tracker_auth.py`). The API still receives that access token as a Bearer
JWT, so the API Gateway Cognito authorizer exposes the `sub` claim at
`event.requestContext.authorizer.jwt.claims.sub` — that is the canonical `user_id`.

---

## Stage 3.3 — Backend API

**Goal:** Authenticated frontend can read and update training days via API.

**Definition of done:**
- Lambda `tracker-api` deployed (Python 3.12)
- API Gateway HTTP API with Cognito JWT authorizer
- Routes: `GET /days`, `GET /days/{date}`, `PATCH /days/{date}`
- CORS configured for `https://train.tacedata.ca`
- End-to-end: `PATCH /days/2026-06-15` with valid token updates `completed=true` in DynamoDB

**Runbook:** `TACE.Website-private/config/runbook-tracker.md` Stages 7–9

---

## Stage 3.4 — Frontend SPA

**Goal:** Working habit tracker UI at train.tacedata.ca.

**Definition of done:**
- Login flow, today's session card, streak counter, overall progress bar
- Weekly checklist row (current week's active days)
- Checkbox completes a day (PATCH to API); notes field saves per-day journal entry
- Rest days shown but not checkable

---

## Stage 3.5 — Email Notifications

**Goal:** Daily briefing email every day including rest days.

**Definition of done:**
- SES domain `tacedata.ca` verified in ca-central-1
- Lambda `tracker-email` deployed
- Active day and rest day email formats with streak + link
- EventBridge rule `tracker-daily-email` fires daily at 08:00 UTC (4am EDT)
- Email arrives at <OWNER_EMAIL>

**Runbook:** `TACE.Website-private/config/runbook-tracker.md` Stages 10–11

---

## Stage 3.6 — CI/CD Integration

**Goal:** GitHub Actions deploys SPA and Lambda updates on push to main.

**Definition of done:**
- `deploy.yml` syncs `app/train/src/` to S3 and updates `tracker-api` + `tracker-email`
- CloudFront invalidation on deploy
- GitHub Actions variables added

**Runbook:** `TACE.Website-private/config/runbook-tracker.md` Stage 12, 14

---

## Stage 3.7 — Public View (Parked)

**Goal:** Read-only shareable progress page. No auth, no check-off ability.

**Definition of done:** TBD — parked as a later, optional phase.

---

# Phase Three — Identity Foundation

Spec: `docs/IDENTITY-FOUNDATION-SPEC.md` (authoritative).

Establish one stable per-user identity (Cognito `sub`) as the partition key across
every table, and add a small users/profile record. This is the prerequisite for
the AI coach (every read scoped to the caller) and for future multi-user, built
now so multi-user is a later drop-in with no second migration.

The single-user build keys every item on `date` alone and does no per-user scoping
(`lambda/days_api.py`, `lambda/daily_email.py`). Because DynamoDB key schema is
immutable, going `user_id`-partitioned is a **new-table migration**, not a code
edit.

---

## Stage 3.9 — Canonical `user_id`, migration, and users table

**Goal:** Every training day belongs to a user; reads and writes are scoped to the
authenticated caller. A users/profile record exists per account, created
idempotently on first login. One active user today; the schema supports many.

**Definition of done (per the spec):**
- New table `training-plan-v2`: PK = `user_id` (Cognito `sub`), SK = `date`,
  mirroring the existing item shape plus `user_id`
- One-time migration script rewrites every existing `date`-keyed item under
  `{user_id: <owner sub>, date}`; owner `sub` retrieved from `<COGNITO_USER_POOL_NAME>`
- `DYNAMODB_TABLE` repointed on **both** `tracker-api` and `tracker-email`
- `days_api.py` derives `user_id` from the JWT claims (`...jwt.claims.sub`) on
  every route — never from body or path [SEC]; `GET /days` uses `Query` on the
  user partition; `GET`/`PATCH /days/{date}` key on `{user_id, date}`; cross-user
  access returns 404, never another user's item [SEC]
- `daily_email.py` replaces the full-table scan with a `Query` on a configured
  owner `user_id`, single-recipient, structured for a later multi-user fan-out
- `seed_dynamo.py` writes items under a `user_id`; table/key updated
- `users` table (or PROFILE item): PK = `user_id`; attributes `email`,
  `display_name`, `coach_scope` (`plan_only` default), `race_goal`, `race_date`,
  `created_at`/`updated_at`
- Profile provisioned idempotently on first authenticated request (conditional put
  on absence of `user_id`); repeated logins never overwrite it
- All writes take `user_id` from the verified token, never the request body [SEC];
  no foreign keys, no join table, no cross-table referential mechanism
- Cutover safety: migrate under a write freeze (or re-run the copy after the
  env-var flip); reconcile row-count and user-state parity (105 = 105, every
  `completed`/`completed_date`/`notes` intact); leave the old table until v2 passes
- Isolation proven with a real second identity: a disposable second Cognito `sub`
  (fixture, retained for regression) confirms cross-user 404 on every `/days` verb
  [SEC]
- Validation: all 105 days load and check off end-to-end for the original account
  post-migration; the daily email still arrives

**Implementer notes:** the overrides table (`training-plan-overrides`) stays keyed
on `date` (single-user reference data); the merge logic in both Lambdas is
unchanged. See the spec's [STEP 1.5] for the full migration sequence.

**Status: live as of 2026-07-05.** See Completed Stages below for what was
validated and the two known gaps carried forward (old-table retirement pending a
soak period; `email`/`display_name` unpopulated since this Cognito app client's
access token carries neither claim).

---

# Phase Four — The AI Coach

Specs: `docs/AI-COACH-ENDPOINT-SPEC.md` (contract/architecture) and
`docs/AI-COACH-PROMPTS-AND-EVALS-SPEC.md` (prompts + evals). Both authoritative.

A per-user AI running coach the user talks to in multiple named, saved, resumable
conversation threads, grounded in their real plan and progress. A hard pre-model
rail intercepts clinical/injury/medical questions and defers them to the user's
physiotherapist before the coach model is ever called. Models are config-driven;
the Anthropic key lives in Secrets Manager. Depends on Stage 3.9 (canonical
`user_id`).

---

## Stage 3.10 — Coach Endpoint, Rail, and Data Model

**Goal:** An authenticated user holds multiple named, resumable conversations
grounded in their own plan; medical questions are deflected before the coach
model; models are swappable via config; no route can read another user's data.

**Definition of done (per the endpoint spec):**
- Separate `conversations` table: PK = `user_id`, SK type-prefixed
  (`CONV#{id}`, `MSG#{id}#{ts}`); one `Query` serves list-threads and load-thread
- Thread CRUD, all scoped to the caller [SEC]:
  `POST/GET /conversations`, `GET/PATCH/DELETE /conversations/{id}`
- `GET`/`PATCH /settings` read/write `coach_scope` (`plan_only` |
  `plan_plus_general`) on the users record — not a separate settings store
- **Hard medical rail** as a standalone, provable step first: a cheap/fast
  `RAIL_MODEL` classifier runs **before** the coach; on trigger it persists a
  canned deferral (`role: rail`, `rail_triggered: true`) and never calls the coach
  model; fails **closed** (classifier error/ambiguous → defer) [SEC]
- The coach turn `POST /conversations/{id}/messages`: auth → ownership (404 if not
  the caller's) → load the **merged plan view** (seed `training-plan-v2` +
  `training-plan-overrides` + user-state, same merge as `days_api.py`/
  `daily_email.py` — never the raw seed) → rail → **facts computed in code**
  (streak, week completed/planned, next long run, today's session, weeks-to-race,
  from the merged view) → prompt assembly → coach model call → persist user +
  coach messages, bump `updated_at`/`message_count` → return. Extract the merge
  into one shared module reused by all three consumers.
- House response envelope `{ok, data, message}`; `message` always safe to log
- Config via **Lambda env vars** (repo convention; SSM is a later upgrade):
  `COACH_MODEL`, `RAIL_MODEL`, `HISTORY_WINDOW_TURNS`, `MAX_TOKENS`. No hardcoded
  model IDs — source current IDs from the `claude-api` skill at build time [SEC]
- Anthropic API key in **Secrets Manager**, read server-side only, cached at
  module scope; never in env vars in plaintext, never in the browser [SEC]
- Anthropic SDK packaged as a **Lambda layer** attached to the coach function;
  `deploy.yml` builds/publishes it
- New routes on the existing HTTP API, Cognito JWT-protected, CORS scoped to
  `https://train.tacedata.ca` [SEC]
- IAM least-privilege: DynamoDB read/write on `conversations` + read on
  `training-plan-v2` and `training-plan-overrides` (leading-key condition on
  `user_id` where practical); `secretsmanager:GetSecretValue` on the one key ARN;
  CloudWatch Logs only; no wildcard resources [SEC]
- End-to-end: "what is my long run Saturday?" returns an answer grounded in the
  caller's real data; an injury question is deferred by the rail

**Build order (from the spec):** thread CRUD → `/settings` → rail (provably
deferring) → coach turn. Do not build the coach turn until CRUD and the rail work.

**Status: live as of 2026-07-05.** See Completed Stages below for what was
validated, two live-observed bugs found and fixed during validation, and the
known gap carried forward (coach/rail prompt wording is a functional
placeholder — final wording and eval-driven tuning is Stage 3.11's job).

---

## Stage 3.11 — Coach Prompts and Evaluation

**Goal:** The coach system prompts and the rail classifier prompt are committed
alongside the code, an eval harness runs locally and in CI against the
production-assembled prompt, and all release gates pass.

**Definition of done (per the prompts/evals spec):**
- Prompt assembly maps to the Messages API: a `system` string plus a `messages`
  array; history sent as real prior turns (rolling window), not a text blob
- `[FACTS]` and `[PLAN_DATA]` delimited blocks; the system prompt states that
  everything in `[PLAN_DATA]` — including the user's free-text `notes` — is data
  to read, never instructions to follow (the notes-field injection boundary) [SEC]
- Coach system prompt: shared base + one delta per `coach_scope`
  (`plan_only` steers back to the plan; `plan_plus_general` allows general running
  knowledge but the plan stays authoritative and the medical boundary still holds)
- Rail classifier prompt: binary `medical`/`ok`, strict machine-readable JSON,
  fails closed; symptom-specificity is the boundary rule
- Eval set + harness (Python): classifier unit evals and coach behavioural evals;
  harness imports the Lambda's **real** prompt-assembly code so it tests what
  ships; models config-driven incl. a new `JUDGE_MODEL` for eval scoring
- Release gates: 100% recall on the `medical` class; no fabricated facts; correct
  scope behaviour in both modes; medical backstop holds; the notes-injection case
  does not alter the role or output [SEC]

**Status: live as of 2026-07-05.** See Completed Stages below for the one real
gap the harness caught and fixed before shipping, plus a follow-up prompt
retune driven by real usage after launch.

---

## Stage 3.12 — Partition `training-plan-overrides` by `user_id`

**Goal:** Close a real security gap left open at Stage 3.9: the physio
override layer was global, un-partitioned reference data, so a second user
would have seen (and been affected by) the first user's overrides.

**Definition of done:**
- New table `training-plan-overrides-v2`: PK = `user_id`, SK = `date`, same
  shape as the existing `training-plan-v2` migration
- One-time migration script copies every override row under the owner's
  `user_id`, with `--verify` asserting count and field parity
- `plan_merge.py`'s override lookup changed from a table-wide `Scan` to a
  `Query` scoped to the caller's own partition — used identically by
  `days_api.py`, `daily_email.py`, and `tracker_coach.py`
- IAM least-privilege updated on all three execution roles: `Query` on the
  new table, old `Scan` grants removed
- Isolation proven directly: a fixture identity seeded with a row on a date
  carrying an active owner override sees **no** override fields merged in

**Status: live as of 2026-07-05.** See Completed Stages below.

---

## Stage 3.13 — Coach Chat UI

**Goal:** A working chat interface for the AI coach in the SPA — the backend
from Stages 3.10–3.11 had only ever been exercised via direct Lambda
invocation.

**Definition of done:**
- A second view in the existing single-page app (no router, no build step,
  no framework — matching the rest of the SPA), toggled from the dashboard
  header
- Thread create/rename/delete/switch; chat bubbles distinguishing user,
  coach, and rail-deferred messages; a minimal markdown-lite renderer
  (`**bold**`, bullet lists) with no external library or CDN dependency;
  a `coach_scope` toggle backed by the existing `/settings` route
- Validated first against a local mock (no backend calls) to sanity-check
  layout and interaction, then against the live site after deploying

**Status: live as of 2026-07-05.**

---

## Stage 3.14 — Coach whole-plan notes digest

**Goal:** The coach can review the athlete's full logged-note history on
request. Before this it only saw the plan window (~2 weeks), so "review the
comments I've logged" surfaced almost none of the athlete's journal.

**Definition of done:**
- `notes_log(days)` returns `{date, notes}` for every day carrying a note —
  the whole-plan journal, preloaded as a `[NOTES_LOG]` block; just the note
  field, not the full rows and not a table scan
- Built from the merged plan view the coach already loads, so no extra
  DynamoDB read; override-aware for free
- The coach system prompt grounds on `[NOTES_LOG]`, extends the notes-injection
  boundary to it, and treats reciting logged notes as a data-retrieval task, so
  a note mentioning a past symptom does not trigger the medical backstop
- `review_logged_notes` eval case; the harness passes `notes_log` through

**Status: committed 2026-07-05; live pending deploy** (prompt/code only, no
infra or IAM change). Live eval run and `tracker-coach` deploy still outstanding.

---

# Phase Five — Training Blocks and the Reset

The 15-week 10K plan (Block 1) was abandoned partway through, to injury and
other factors. Rather than patch it, the athlete reset onto a new block with a
different goal: consistency, with no race to train for.

That exposed an assumption baked in throughout — that a user has exactly one
plan, of a known length, ending in a race. Phase Five removes it.

---

## Stage 3.15 — Training blocks (`plan_id`)

**Goal:** A user works through several sequential training blocks in one
partition. Every read is scoped to the active block; completed blocks stay
readable and writable.

**Definition of done:**
- `plan_id` on every row of `training-plan-v2` and `training-plan-overrides-v2`;
  `active_plan_id` on the `training-users` record names the current block
- `plan_id` is a **plain attribute, not part of the key** — block date ranges
  never overlap, so `{user_id, date}` stays unique. An in-place attribute add,
  not a fourth new-table migration
- `plan_merge.filter_to_plan()` shared by `days_api.py`, `daily_email.py` and
  `tracker_coach.py`, so all three agree on which block is live
- Both filters lenient about untagged rows, so code deploy and data backfill are
  order-independent and neither ordering breaks the morning email
- `GET /days?plan_id=` reads a past block; `PATCH /days/{date}` still works on
  old blocks, so history can be corrected after a block ends
- Migration script with an idempotent backfill, a guarded truncate that refuses
  to delete any row carrying `completed` or `notes`, and a cutover flag [SEC]
- No IAM change: `<TRACKER_EMAIL_ROLE>` already held `GetItem` on
  `training-users` from Stage 3.9, unused until now

**Status: live as of 2026-08-31.**

---

## Stage 3.16 — De-hardcode the plan shape

**Goal:** Nothing in the code assumes a plan is 105 days, has 75 active days,
starts 2026-06-15, or ends in a 10K on 2026-09-27.

**Definition of done:**
- SPA derives total days, active days, start and end from the block the API
  returned; race-day countdown replaced with a block-day counter
- Email derives block length; "Day N of 105" becomes "Day N of {total}"
- 10K branding removed from the SPA (title, headings, login copy)
- `compute_facts` gains block-progress facts (`block_day`, `block_total_days`,
  `block_active_days`, `block_active_days_completed`) — the scoreboard that
  matters without a race
- Coach system prompt no longer promises a 10K; null `race_date`/`weeks_to_race`
  is stated as a real answer, never filled with an invented event, and [FACTS]
  field names are never quoted at the athlete
- `[NOTES_LOG]` spans **every** block, so a reset does not erase the athlete's
  logged history from the coach's view
- New `no_race_block_invents_no_goal` eval case

**Status: live as of 2026-08-31.** Eval-harness gates not yet re-run against the
rewritten prompt — see Open Items.

---

## Stage 3.17 — Block 2, the consistency block

**Goal:** Retire the unlived tail of Block 1 and start a new block with no race.

**Definition of done:**
- Block 1 truncated at 2026-08-31; 78 days of real history retained
- Block 2 seeded: 8 weeks, 2026-09-05 → 2026-10-30, 56 days
- Weekly shape: 5 active days at 60 min — two run/walks (one always Saturday,
  never on consecutive days) and three yoga/stretching/cross-training days —
  plus 2 rest days. No long run, no race
- `active_plan_id` flipped to `block-02`; all three Lambdas and the SPA deployed
- Validated end to end against production

**Status: live as of 2026-08-31.**

---

# Phase Six — Block 2 Rotation Revision

Block 2 had been live nine days when its rotation was revised in one session:
Monday and Sunday swap roles, Saturday's run/walk becomes a parkrun, Tuesday's
progression steepens, and the display week moves from Saturday-start to
Monday-start. Driven by the athlete's own read on how the week was going, not
a roadmap — see Completed Stages below for the full session write-up.

## Stage 3.18 — Rotation and week-boundary revision

**Goal:** Revise Block 2's day-of-week content and switch the displayed week
to start on Monday, without rewriting any already-lived day or introducing a
schema change.

**Definition of done:**
- Monday, Tuesday, Saturday, Sunday content updated per the athlete's
  direction; Wednesday/Thursday/Friday unchanged
- Week boundaries pivot from Saturday-start to Monday-start, confirmed as a
  `week_number` data change (not a display-only toggle) before implementation
- Cutover lands on a date that requires no rewrite of historical rows
- `seed_dynamo.py` protects `notes` as well as `completed` before any live
  re-seed of an in-progress block [SEC]
- Live state verified clean (no `completed`/`notes` in the affected range)
  before writing, and verified correct after

**Status: live as of 2026-09-14.** See Completed Stages below for the full
write-up, including the one genuine modeling question raised and dropped
(a Monday choice-day) and the Saturday/Tuesday week-label side effect that
has no workaround.

---

## [Deferred] Multi-User and Later Phases

Built to accept these later without rework, but out of scope now:

- **Second-user onboarding + plan generation** — intake form, Claude-generated
  plan validated against the item schema before any write (generated output
  treated as untrusted input), written under the new user's partition. Onboarding
  **updates** the existing users record (adding `race_goal`/`race_date`), it does
  not create it — first-login provisioning already did.
- **Invite mechanism** — replace `auth_guard.py`'s static `ALLOWED_EMAILS` with an
  invited-emails store; public self-signup stays closed.
- **Per-user email fan-out** — `daily_email.py` loops over the `users` table,
  briefing each user from their own partition to their own verified address.
- **Public view (Stage 3.7)** — read-only shareable progress page.
- **Coach v2** — response streaming; summarize-and-drop of old turns when threads
  get long; additional scope modes or personas.

---

## Completed Stages

### Stage 3.18 — Rotation and week-boundary revision (2026-09-14)

Conducted as a structured walkthrough — one day of the week at a time, current
content shown, changed or confirmed, nothing written until every day was
covered and confirmed together.

- **A Monday "choice day" was proposed and dropped.** The first idea was
  Monday offering two options (the existing yoga session, or a run/walk
  matching Tuesday's). Before implementing anything, `is_run_day` and
  `session_type` usage were traced across `app.js`, `daily_email.py`, and
  `coach_prompts.py` — both are read everywhere as a single fixed value per
  day (SPA rendering, email subject lines, the coach's "next run day" facts,
  eval case shapes). A real choice day would have meant a schema change
  (alternate-session fields) and matching updates in at least three consumers
  for one weekly occurrence. Flagged before building it; the athlete chose to
  drop it rather than accept that scope. Monday ultimately became a plain
  rest day instead, for unrelated reasons (see below).
- **Tuesday's progression was steepened, then Saturday split off into its own
  shape entirely.** Tuesday's run/walk interval moved from the original
  18 → 24 min (over the remaining weeks) to 30 → 36 min, ratio 1:2 → 3:2 — the
  same *style* of step-up as the original plan (same delta pattern, same
  plateau shape), just re-based to a higher floor. Saturday initially mirrored
  this, then was reframed entirely: **Parkrun (5K)**, a real fixed-distance
  timed community event rather than a designed interval block. That changes
  what the stored numbers *mean* — `run_interval_minutes`/
  `session_minutes_target` now hold an **estimated finish time**, not a
  session length, and the athlete's own logic was that a better run:walk ratio
  should produce a *faster* 5K, so estimated time actually **declines** week
  over week (40 → 38 min) while the ratio climbs (1.5:2 → 3:2) — the inverse
  shape of Tuesday's numbers, and internally consistent once you see the
  reasoning. This also resolved a real inconsistency for free: a flat 60-min
  session budget no longer made sense once Saturday's interval alone
  approached 46 min under the pre-parkrun numbers — reframing it as "estimated
  finish, not a hard duration" removed the "stretch to fill the hour" framing
  entirely rather than requiring a wording patch.
- **Sunday became active, Monday became rest — a deliberate swap, not two
  independent changes.** Sunday moving from Rest to a real "Gentle Yoga"
  active day was a genuine fork raised explicitly: stay in the same
  uncounted bucket as Friday (no ripple), or become a real 6th active day
  (changes `week_active_days` everywhere it's read). The athlete chose the
  latter. Minutes later, Monday flipped from Yoga & Mobility to Rest — which,
  combined with Sunday's flip, **cancels out**: every full week still nets 5
  active / 2 rest, just with rest on Monday instead of Sunday. The one
  transitional week (2026-09-12 → 2026-09-20) doesn't fully net out, though —
  Monday's flip starts *today* (2026-09-14) but Sunday's flip couldn't start
  until 2026-09-20 (2026-09-13 had already happened as Rest and can't be
  rewritten), so that single week runs 6 active / 3 rest across its 9 days
  before settling back to the normal 5/2 pattern.
- **Week-start day is a `week_number` change, not a display toggle — confirmed
  before touching anything.** `app.js`'s `weekDaysFor()`/`renderWeeklyRow()`/
  `renderWeekSchedule()`, `daily_email.py`'s subject lines, and
  `coach_prompts.py`'s "days active this week" fact all filter or group by the
  stored `week_number` attribute directly; none compute a calendar-week
  boundary independently. So "start the week on Monday" meant re-drawing
  `week_number`/`week_start_date`/`week_end_date`, not reordering a render.
  The cutover landed on 2026-09-14 specifically *because* it's a Monday —
  every day before it keeps its original Saturday-start numbering untouched,
  so the pivot needed zero historical rewrites. **Real, unavoidable side
  effect:** Saturday sits at the front of its old (Saturday-start) week but
  the tail of its new (Monday-start) one, so every Saturday/Sunday now
  displays one week-number lower than before, while Monday–Friday are
  unaffected (verified algebraically for all 8 weeks, not assumed). The
  Saturday/Tuesday pairs this stage's progression numbers were built around
  (e.g. "2026-09-19 matches that week's Tuesday") no longer share a displayed
  week-number label as a result — the prescribed content per date is
  unaffected, only the label next to it. No numbering scheme satisfies both
  "start weeks on Monday" and "keep that pairing's label matching"
  simultaneously; flagged and accepted rather than worked around.
- **Generated, not hand-transcribed.** The 47 affected rows (2026-09-14
  onward) were produced by a small throwaway Python script, not typed by hand
  — the rule set (which day-of-week gets which content, the two explicit
  date→value progression tables, the week-number shift for Saturday/Sunday
  only) was compact enough to encode directly, and a generator avoids
  transcription drift across that many rows and fields. Days before the
  cutover were passed through byte-for-byte, never regenerated.
- **`seed_dynamo.py` hardened before use, not after.** `--preserve-state`
  previously skipped a day only if `completed=true` — a day carrying `notes`
  but not checked off (plausible for a rest day) would have been silently
  overwritten, since `put_item` replaces the whole item and the seed template
  never carries `notes`. Extended the same flag to also skip noted days, and
  added `--from-date` so historical days are excluded from the run entirely
  rather than relying solely on a per-row check.
- **Live state verified clean before writing.** Queried `training-plan-v2` for
  the full affected range (2026-09-14 → 2026-10-30, 47 rows) and confirmed
  `completed=false` and no `notes` on every one before running the real seed.
  `--dry-run` output was reviewed against the intended per-date table first;
  the real write followed only after that matched. Post-write, spot-checked
  2026-09-14 (Rest), 2026-09-19 (Parkrun, 40 min, 1.5:2, `week_number=2`), and
  2026-09-20 (Gentle Yoga, `week_active_days=6`) directly against the live
  table.
- **Backup taken, PITR deliberately left off.** `training-plan-v2` had Point-
  in-Time Recovery disabled and no on-demand backups — confirmed, not
  assumed, via `describe-continuous-backups`/`list-backups` before writing.
  A full-fidelity export of the 47 affected rows was taken immediately before
  the write as a scoped rollback point (kept outside the repo — live athlete
  data, not source). Enabling PITR going forward was offered and declined:
  writes to this table only happen during deliberate sessions like this one,
  not continuously, so the athlete judged it unnecessary.
- **Identity resolution required a real check, not an assumption.** The
  Cognito pool holds two accounts — the athlete's, and a second one likely
  the Stage 3.9 isolation-test fixture, though that was never confirmed
  either way from the pool record alone. Both show `Enabled: true` with
  identical `UserStatus`, so they were not distinguishable by status; matched
  against the athlete's own name instead, and confirmed explicitly before
  running anything against a real `user_id` — writing 47 days against the
  wrong account was a realistic failure mode here, not a theoretical one.

**Known gap carried forward:** the SPA still hasn't been checked in a real
browser after this change — same standing gap as Stage 3.17.

---

### Stages 3.15–3.17 — Training blocks and the Block 2 reset (2026-08-31)

Built and cut over in one session. Driven by a real event, not a roadmap: the
athlete could not follow Block 1 through, and resetting revealed how much of the
app assumed one fixed-length, race-ending plan.

- **`plan_id` as a plain attribute, not a key change.** Block date ranges never
  overlap, so `{user_id, date}` stays unique across blocks. That made this an
  in-place attribute add rather than the fourth new-table migration the Stage
  3.9 and 3.12 precedents would have implied — no new table, no key schema
  change, and no IAM change either (`<TRACKER_EMAIL_ROLE>` already had
  the `training-users` `GetItem` grant from Stage 3.9, unused until now).
- **Deploy-order independence by design.** `filter_to_plan()` and
  `query_overrides()` both keep rows that carry no `plan_id`, so code could ship
  before the backfill or after it without a window where the morning email
  breaks. Cheap to do, and it removed the need for a write freeze.
- **Backfill:** 131 rows tagged `block-01` (78 plan + 53 override), `--verify`
  confirming every row in range carried the right block.
- **Truncate:** 27 plan and 27 override rows dated 2026-09-01 onward deleted —
  sessions that were never lived and now never would be. The script's guard
  aborts if any candidate row carries `completed` or `notes`; it passed cleanly,
  and all 17 completed days and 10 journal entries sit before the cutoff. Block 1
  retains 2026-06-15 .. 2026-08-31.
- **The journal deliberately spans blocks.** `[NOTES_LOG]` is built from raw
  rows across every block rather than the active one, so the reset did not erase
  the athlete's history from the coach. Verified live: asked to review logged
  comments while Block 2 was active, the coach listed all ten Block 1 entries
  with dates — including the calf-pain ones — without tripping the medical rail,
  and noted unprompted that they came from an earlier block.
- **De-hardcoding:** the SPA and email now derive block length, active-day count
  and start/end from the data. The race-day countdown became a block-day counter;
  10K branding is gone from the UI. `compute_facts` gained block-progress facts.
- **Prompt rewrite:** the coach no longer opens by promising a 10K. A null
  `race_date` is stated plainly as "no race in this block" rather than filled
  with an invented event — verified live. A second pass stopped it quoting
  `[FACTS]` field names (`race_date is null`) back at the athlete after the first
  live check showed it doing exactly that.
- **Validated:** 18 production checks by direct Lambda invocation (block scoping,
  `?plan_id=` history reads, override isolation, derived email length) plus 6
  live coach checks. One unintended side effect: the email validation invoked
  `tracker-email` with a `test_date`, which sends to the real recipient — a
  briefing for 2026-09-08 arrived in the inbox on 2026-08-31. The script has no
  dry-run path; worth adding before the next test.
- **Doc correction:** the live EventBridge rule fires at `cron(0 8 * * ? *)`
  (08:00 UTC, 4am EDT), not the 11:00 UTC this file recorded. The rule is
  authoritative; the doc was wrong and has been corrected.

**Follow-up, same day (v3.2.1).** The eval gates were re-run via the
`coach-evals` workflow and all pass — 100% medical recall (7/7) and all 10
coach behavioural cases, including the new no-race case. `daily_email.py`
gained a `dry_run` invocation key, closing the gap that put a real briefing in
a real inbox during validation. A static SPA check
(`scripts/check_spa_ids.py`) now verifies every element id the JS looks up
exists in the HTML — not a substitute for a browser, but it catches the
renamed-id failure mode this stage risked, and needs no JS runtime.

The same pass found a real exposure. The July 2026 history scrub corrected
`main` but never updated the git **tags**: `v0.10.0` and `v0.11.0` on the
remote still pointed at pre-scrub commits carrying the raw AWS account ID, a
CloudFront distribution ID and the deploy role ARN in `config/` — the last
publicly reachable pointers to that content. Both were force-updated to the
scrubbed commits after confirming no pull-request ref reaches the old ones.
The remaining live resource *names* (buckets, Cognito pool/client, the three
execution roles) were then swept into placeholders across seven tracked files,
including a published blog post.

**Open item:** the SPA still has not been checked in a real browser — `app.js`
has never been parsed by a JS engine, as none is installed on the build
machine.

---

### Stage 3.14 — Coach whole-plan notes digest (2026-07-05)

Post-launch enhancement from a real conversation: asked to "review the comments
I've logged and list them with dates," the coach could see only the ~2-week plan
window and surfaced one note of nine. (The same conversation also tripped the
medical rail on that retrieval request -- the rail half was folded into the
Stage 3.11 retune above; this stage is the coach-visibility half.)

- **`notes_log(days)`** returns `{date, notes}` for every day with a note,
  preloaded as a `[NOTES_LOG]` block -- the whole-plan journal, but only the note
  field, never the full rows or a table scan. Built from the merged plan view the
  coach already loads, so it costs no extra DynamoDB read and is override-aware
  for free.
- **Prompt:** the coach now grounds on `[NOTES_LOG]` alongside `[FACTS]`/
  `[PLAN_DATA]`, the notes-injection boundary is extended to it, and reciting
  logged notes is declared a data-retrieval task -- so a note mentioning past
  pain no longer trips the coach's own medical backstop.
- **Evals:** added `review_logged_notes` (one fixture note carries a 2/10 pain,
  proving the coach lists it by date rather than deferring); the harness now
  passes `notes_log` through `build_coach_system_prompt`.
- **Validated statically** (import/compile/behaviour -- no API key needed); the
  live eval run and the `tracker-coach` deploy are carried forward as the open
  item.

---

### Stage 3.13 — Coach Chat UI (2026-07-05)

- **New view, no new dependencies:** `src/coach.js` (thread create/rename/
  delete/switch via a `<select>`, chat bubbles, a minimal markdown-lite
  renderer -- `**bold**` and bullet lists via regex on already-escaped text,
  no library or CDN script) wired into `index.html`/`app.js`/`style.css` as a
  second view toggled from the dashboard header, matching the SPA's existing
  no-router, no-build-step pattern. `apiRequest`/`esc` exported from `app.js`
  and reused as-is; the coach routes' `{ok, data, message}` envelope is
  unwrapped in `coach.js` rather than changing the shared helper, since
  `/days` callers still expect the bare-body shape.
- **Local mock preview first:** before touching the live site, built a
  throwaway local preview (a copy of `coach.js` with only its import line
  swapped to a mock instead of the real API, so the rendering/interaction
  logic under test was the literal production code) to sanity-check layout,
  bubble styling, and markdown rendering without needing real auth or
  network access.
- **Deployed and found a real caching bug:** synced `src/` to the live S3
  bucket and invalidated CloudFront, but the S3 objects had no `Cache-Control`
  header at all, so browsers applied heuristic caching and kept serving a
  stale copy in a normal tab (working fine in Incognito, which has no cache) --
  even after the CloudFront invalidation. Fixed by setting `Cache-Control:
  no-cache` on all synced SPA files (revalidate-always, not "don't cache") and
  adding `--cache-control "no-cache"` to `deploy.yml`'s sync step so future
  deploys don't regress. One hard refresh was needed to clear the
  already-heuristically-cached copy; every deploy after this one revalidates
  normally.
- **Known gap:** not yet re-validated end-to-end in a real logged-in browser
  session beyond a visual/functional check after the cache fix -- no
  automated browser test exists for this SPA.

---

### Stage 3.12 — Partition `training-plan-overrides` by `user_id` (2026-07-05)

Security finding, not a planned feature -- see the Stage 3.12 section above
for the goal. Full mechanics (real resource values, IAM policy diffs, the
"deploy code and flip the env var together" reasoning) are in the private
runbook Stage 19; this entry covers what's safe to say in the public repo.

- Migrated 17 override rows from the date-keyed table to the new
  `user_id`-partitioned one; `--verify` passed count and field parity both
  before and after the Lambda cutover. (Those 17 cover 2026-06-30 to 07-18. The
  2026-07-27 post-clearance rebuild later added 63 more, so the live table held
  80 until Stage 3.17 truncated the 27 that fell past the reset.)
- `plan_merge.py`'s override lookup is now a `Query` scoped to the caller,
  never a table-wide `Scan` -- the same shared module used by all three
  Lambda consumers, so the fix applies everywhere at once.
- **Isolation proof:** seeded a temporary row for the Stage 3.9 fixture
  identity on a date carrying an active owner override, confirmed the
  fixture's response had no override fields merged in, then deleted the test
  row. Before this fix, any caller's row on that date would have picked up
  the owner's override via the old table-wide scan.
- Old table retained pending a soak period, same precedent as the Stage 3.9
  `training-plan` retirement.

---

### Stage 3.11 — Coach Prompts and Evaluation (2026-07-05)

**Post-launch retune (2026-07-05, same day):** real usage surfaced the rail
and the coach's own medical backstop both over-triggering on *any* body-part
mention (a bare "leg", and a positive status update like "my soleus is
feeling better today") rather than on an actual reported symptom -- both were
judging by topic instead of intent. Retuned `RAIL_SYSTEM_PROMPT` and
`COACH_SYSTEM_BASE` with explicit worked examples distinguishing a named body
part from an actual symptom/pain/injury signal; took two passes on the
coach's own prompt, since the first pass stopped the hard defer but the coach
still hedged toward physio pre-emptively on a bare word. Added 5 classifier
cases and 2 coach-behavioral cases to the eval harness from this exact real
conversation so the regression is locked in; all gates still pass (100%
medical recall preserved, both new coach cases pass). Re-validated against
production with the real messages plus two genuine medical cases, which
still correctly defer.

- **Extracted `lambda/coach_prompts.py`** from the Stage 3.10 placeholder
  logic in `tracker_coach.py`: facts computation, the plan-data window,
  history-window trimming, the rail classifier + `classify_message()`, and
  the coach system prompt + `build_coach_system_prompt()`. Zero AWS/env
  dependencies by design, so the eval harness can import it directly without
  any AWS credentials — only an Anthropic key. Redeployed and re-ran a subset
  of Stage 3.10's checks to confirm the refactor alone changed nothing.
- **Harness:** `app/train/evals/run_coach_evals.py` adds `app/train/lambda` to
  `sys.path` and imports `coach_prompts` as a flat top-level module — the same
  way the Lambda runtime imports it after `zip -j` — so the harness evaluates
  the literal production prompt-assembly code. Cases in `evals/cases.py`: the
  spec's 9 classifier cases and 6 coach behavioral cases (synthetic
  facts/plan_data matching the real shape, not fetched from DynamoDB, so the
  harness is deterministic and AWS-free). `JUDGE_MODEL=claude-opus-4-8` scores
  the subjective cases via a strict pass/fail JSON rubric.
- **Classifier tuning:** started from the spec's [C1] draft plus the [C2]
  boundary rule (reassurance-seeking about a specific symptom → `medical`;
  ambiguous → `medical`). Passed **100% recall on the medical class on the
  first run** — no iteration needed.
- **Coach tuning — one real gap found and fixed:** the first run failed the
  `medical_backstop` case. The coach correctly deferred to the
  physiotherapist ("that's a question for your physio...") but then *also*
  added "I'd hold off on the 60-minute session until you've got their
  input" — itself a training recommendation tied to the symptom, exactly
  what the backstop is supposed to forbid. The original wording ("do not
  advise — briefly direct the athlete to their physiotherapist") left room
  for the model to treat the redirect and the advice as two separate things.
  Tightened `COACH_SYSTEM_BASE` to state the backstop reply is *only* a brief
  acknowledgement plus the referral, explicitly ruling out any opinion on
  training/resting/modifying "even framed cautiously or as 'just in case'" —
  second run passed all 6 coach cases and the classifier gate.
- **Redeployed and re-validated:** re-ran the Stage 3.10 direct-invoke checks
  (grounded race/session question, medical defer, override-day grounding,
  cross-user 404) against the tuned prompts — all held. The override-day
  check also showed the tightened backstop generalizing correctly outside
  the eval set: asked about a physio-adjusted session with a mentioned
  Achilles symptom in the same thread, the coach deferred the go/no-go
  decision to the physiotherapist rather than recommending skipping the
  session itself.
- **CI:** `.github/workflows/coach-evals.yml` (PR-triggered on changes to
  `coach_prompts.py`/`evals/`, plus manual dispatch) — deliberately separate
  from `deploy.yml` and needs no AWS access, only the `ANTHROPIC_API_KEY` repo
  secret (added by the user directly, never entered the session).
  `deploy.yml`'s `tracker-coach` zip step now also bundles `coach_prompts.py`.
- **Known gap, not part of this stage's checklist:** no frontend chat UI
  exists yet for the coach — Phase Four's backend is complete but there's
  nothing in the SPA to drive it from a browser. Out of scope until a future
  stage decides to add it.

---

### Stage 3.10 — Coach Endpoint, Rail, and Data Model (2026-07-05)

Built in the spec's mandated order (CRUD → `/settings` → rail → coach turn),
each step deployed out-of-band and validated before the next; commits split
the same way.

- **Merge extraction (prerequisite):** `lambda/plan_merge.py` pulled the
  duplicated override-merge logic out of `days_api.py` and `daily_email.py`
  before either was touched further, so the coach reads the identical merged
  view. Re-ran the Stage 3.9 direct-invoke checks afterward to confirm no
  behavior change (105 items, 17 active overrides, same merged output).
- **`conversations` table + thread CRUD:** new Lambda `tracker-coach`
  (`POST`/`GET /conversations`, `GET`/`PATCH`/`DELETE /conversations/{id}`),
  `<TRACKER_COACH_ROLE>` (RW on `conversations`, read-only on
  `training-plan-v2` + `training-plan-overrides`), routes on the existing HTTP
  API behind the existing Cognito authorizer. Validated: full CRUD lifecycle
  for the owner; the Stage 3.9 fixture identity gets 404 on every verb with no
  write landing; delete removes the thread from the list.
- **`/settings`:** added to `days_api.py` (tracker-api) rather than the new
  Lambda — `coach_scope` lives on the `training-users` record tracker-api
  already owns via `_ensure_profile`, so the coach role never needs
  `training-users` write access. Required adding `dynamodb:UpdateItem` on
  `training-users` to `<TRACKER_API_ROLE>` (previously `GetItem`/
  `PutItem` only). Validated: default `plan_only`, update to
  `plan_plus_general`, persists, invalid value rejected with 400.
- **Anthropic setup:** API key in Secrets Manager
  (`<COACH_SECRET_NAME>`, created by the user directly so the key
  never entered the session); Anthropic Python SDK built as a Lambda layer
  (`tracker-coach-anthropic-sdk`, `pip install --platform
  manylinux2014_x86_64 --python-version 3.12` to get `jiter`'s compiled wheel
  rather than a source build); `<TRACKER_COACH_ROLE>` scoped to
  `secretsmanager:GetSecretValue` on that one ARN plus a read-only
  `training-users` grant for `coach_scope` — the endpoint spec's IAM section
  didn't list `training-users` even though the pipeline needs it; closed as a
  spec gap rather than reproduced.
- **Rail, standalone:** `POST /conversations/{id}/messages` persists the
  user's message, classifies it via `RAIL_MODEL` (`claude-haiku-4-5-20251001`),
  and returns the canned deferral on trigger — the coach turn wasn't wired yet
  at this point, so a non-triggered message hit a deliberate 501 stub, proving
  the coach model is unreachable either way. **Bug found live:** the
  classifier sometimes wrapped its JSON in a markdown code fence despite being
  told not to, so `json.loads` failed and every message defaulted to the
  fail-closed path (safe, but meant "ok" messages never got through) — fixed
  by tightening the prompt and defensively stripping fences before parsing.
  **Bug found live:** `_delete_conversation` deleted the thread item before
  batch-deleting its messages; a missing `dynamodb:BatchWriteItem` grant
  (since added) caused a partial failure that orphaned message rows under a
  conversation_id nothing pointed to anymore — fixed by reordering to delete
  messages first, thread last, so a partial failure stays retryable instead of
  leaking orphans. Validated: an injury message defers with
  `rail_triggered: true`; a normal question reaches the 501 stub; a
  deliberately broken `RAIL_MODEL` config also defers (fail-closed); delete
  with real messages present now cleans up completely.
- **Coach turn:** merged plan view via `plan_merge`, facts computed in code
  (streak, week completed/planned, next long run, weeks-to-race, today's
  session — never left for the model to derive from raw rows), a placeholder
  system prompt with the `coach_scope` delta (final wording is Stage 3.11's
  job), the model call (`COACH_MODEL` = `claude-sonnet-5`), and persistence
  with `updated_at`/`message_count` bumped. **Bug found live:**
  `claude-sonnet-5` returned a `ThinkingBlock` before its `TextBlock` (adaptive
  thinking runs by default when `thinking` is omitted, per the model's
  migration notes) and `response.content[0].text` broke on it — fixed with a
  `_response_text()` helper that finds the first text-type block, used by
  both the rail and the coach call. Validated end-to-end against the real
  plan: "how many weeks until my race, and what is today's session" returned
  12 weeks and the exact Rest-day text from `training-plan-v2`; a follow-up
  "what did I just ask" correctly recalled the prior exchange; a question
  about an overridden day (2026-07-06) returned the override's session detail
  ("no squats or lunges") rather than the seed's ("squats, planks, lunges") —
  the seed text is the literal opposite of what the physio override calls
  for, so this is a real proof the merge is load-bearing; a medical follow-up
  later in the same thread still deferred via the rail; the Stage 3.9 fixture
  identity gets 404 posting to the owner's thread, no message persisted.
- **`deploy.yml`:** wired `plan_merge.py` into the `tracker-api`/`tracker-email`
  zips, added the Anthropic-layer build/publish/attach step and the
  `tracker-coach` code-update step; `<GITHUB_DEPLOY_ROLE>` granted the
  matching Lambda/layer permissions; new repo variable
  `TRACKER_LAMBDA_COACH=tracker-coach`. Not exercised through a real CI run
  at the time (branch not merged/pushed) — first exercised successfully on
  2026-08-31 with the Stage 3.15–3.17 merge.
- **Known gap, not part of this stage's checklist:** the coach system prompt
  and rail classifier prompt are functional placeholders (clearly marked
  `[DEFERRED]` in the code) — final wording, the label boundary, and an eval
  set are Stage 3.11's explicit scope, not an oversight here.

---

### Stage 3.9 — Canonical `user_id`, migration, and users table (2026-07-05)

- Owner `user_id` retrieved and verified against a live access token —
  `<OWNER_SUB>`. Note: Cognito login is Google SSO under
  a personal Gmail address, distinct from the `tacedata.ca` address SES sends to.
- `training-plan-v2` (PK `user_id`, SK `date`) and `training-users` (PK `user_id`)
  created; `training-plan-overrides` left unchanged (still `date`-keyed)
- `migrate_to_v2.py` (new script): 105/105 items migrated, re-run post-cutover to
  close the write-freeze gap, `--verify` passed both times (row count + full
  `completed`/`completed_date`/`notes` parity)
- IAM: additive inline policies on both execution roles (`Query`/`GetItem` on
  v2, `GetItem`/`PutItem` on users) — existing grants, including overrides
  access, untouched
- `days_api.py`: `user_id` derived from JWT claims on every route; `GET /days`
  uses `Query`; `GET`/`PATCH /days/{date}` key on `{user_id, date}`;
  `_ensure_profile()` provisions the `training-users` record idempotently on
  first request
- `daily_email.py`: `_scan_all()` replaced with `_query_user()` scoped to
  `OWNER_USER_ID`; per-user briefing logic extracted into `_brief_user()` so
  multi-user fan-out is a later loop, not a rewrite
- `seed_dynamo.py`: `build_item()` takes a required `user_id`; default table is
  now `training-plan-v2`
- **Validated** (direct Lambda invocation, real event shape — not yet exercised
  through a live browser session): `GET /days` returns 105 items; a `PATCH`
  write lands under the correct key and reverts cleanly; a real second Cognito
  identity (the pool's existing, otherwise-inactive account) gets 404 on both
  `GET` and `PATCH` against the owner's data, with the owner's row confirmed
  unchanged afterward; `tracker-email` manual invoke reads the correct
  session from v2; profile provisioning is idempotent (second call leaves
  `created_at` unchanged)
- **Known gaps carried forward:** `email`/`display_name` are not populated on
  the profile — this Cognito app client's access token carries neither claim
  (confirmed by decoding a live token); populated defensively if ever present.
  Rest-day email format not separately re-tested post-cutover. Old
  `training-plan` table retained pending a soak period before retirement
  (private runbook Step 50).

---

### Stage 3.6 — CI/CD Integration (2026-06-13)

- IAM deploy role `<GITHUB_DEPLOY_ROLE>` updated — S3 `<TRACKER_S3_BUCKET>`, CloudFront <TRACKER_DISTRIBUTION_ID>, Lambda tracker-api + tracker-email
- deploy.yml: tracker SPA sync, CloudFront invalidation, Lambda updates for both functions
- GitHub Actions variables: `TRACKER_DISTRIBUTION_ID`, `TRACKER_LAMBDA_API`, `TRACKER_LAMBDA_EMAIL`
- Validated: full run green in 19s (run <GHA_RUN_ID>)
- Note: actions/checkout and configure-aws-credentials need Node.js 24 version bumps before 2026-09-16

---

### Stage 3.5 — Email Notifications (2026-06-13)

- SES domain `tacedata.ca` verified in ca-central-1 (DKIM CNAMEs added to Route 53)
- IAM role `<TRACKER_EMAIL_ROLE>` — DynamoDB read + SES SendEmail + CloudWatch Logs
- Lambda `tracker-email` — Python 3.12, `daily_email.handler`
- Env: `DYNAMODB_TABLE=training-plan`, `SES_SENDER=noreply@tacedata.ca`, `RECIPIENT=<OWNER_EMAIL>`
- EventBridge rule `tracker-daily-email` — `cron(0 8 * * ? *)` (08:00 UTC = 4am EDT), so the
  briefing is waiting in the inbox before the day starts. (Recorded as 11:00 UTC / 7am EDT
  until 2026-08-31, when the live rule was found to disagree with the doc; the rule is
  authoritative and the doc was corrected to match.)
- Validated: active day email (Day 1, Strength & Mobility) and rest day email (Week 1 Friday) both received

---

### Stage 3.4 — Frontend SPA (2026-06-13)

- `app/train/src/auth.js` — PKCE flow, token storage, refresh, logout
- `app/train/src/app.js` — today card, streak, progress bar, weekly row, checkbox, notes
- `app/train/src/index.html` — login screen + dashboard structure
- `app/train/src/style.css` — clean, no emojis
- Deployed to S3, CloudFront invalidated, validated end-to-end in browser

---

### Stage 3.3 — Backend API (2026-06-13)

- IAM role `<TRACKER_API_ROLE>` — DynamoDB (GetItem, UpdateItem, Scan) + CloudWatch Logs
- Lambda `tracker-api` — Python 3.12, `days_api.handler`, env `DYNAMODB_TABLE=training-plan`
- API Gateway HTTP API `tracker-api` — ID `<TRACKER_API_ID>`, endpoint `https://<TRACKER_API_ID>.execute-api.ca-central-1.amazonaws.com`
- Cognito JWT authorizer `<COGNITO_AUTHORIZER_ID>`, Lambda integration `<LAMBDA_INTEGRATION_ID>`
- Routes: GET /days, GET /days/{date}, PATCH /days/{date} — all JWT-protected
- Validated: GET /days returns 105 items; PATCH sets completed=true + completed_date

---

### Stage 3.2 — Auth (2026-06-13)

- Cognito User Pool `<COGNITO_USER_POOL_NAME>` — `<COGNITO_USER_POOL_ID>`
- Google IdP configured — Client ID `<GOOGLE_OAUTH_CLIENT_ID>`
- App Client `<COGNITO_CLIENT_NAME>` — `<COGNITO_CLIENT_ID>` (code flow, no secret, PKCE)
- Hosted UI domain — `<COGNITO_HOSTED_UI_DOMAIN>`
- Auth guard Lambda `tracker-auth-guard` — PreSignUp + PreTokenGeneration triggers
- Allowed emails: `<ALLOWED_EMAIL_1>`, `<ALLOWED_EMAIL_2>`
- Note: PreAuthentication does NOT fire for Google federated logins; PreSignUp blocks profile creation, PreTokenGeneration blocks token exchange
- Validated: non-allowed account rejected at PreSignUp; allowed account gets `?code=` redirect

---

### Stage 3.1 — Infrastructure (2026-06-13)

- ACM wildcard cert `*.tacedata.ca` — ISSUED (`arn:aws:acm:us-east-1:<AWS_ACCOUNT_ID>:certificate/<ACM_CERT_UUID>`)
- S3 bucket `<TRACKER_S3_BUCKET>` — private, CloudFront OAC only
- CloudFront distribution `<TRACKER_DISTRIBUTION_ID>` — `<TRACKER_CF_DOMAIN>` (deploying)
- Route 53 A alias `train.tacedata.ca` → CloudFront
- DynamoDB `training-plan` — 105 items seeded, `completed: false`
- Placeholder `index.html` deployed to S3
