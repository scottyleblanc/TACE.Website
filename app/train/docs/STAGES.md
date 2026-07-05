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

## Current Focus: Phase Four — The AI Coach (Stage 3.11 next)

Stage 3.9 (identity foundation) and Stage 3.10 (coach endpoint, rail, data model)
are both live — see Completed Stages below. Loose ends carried forward, not
blocking Stage 3.11: the old `training-plan` table is retained pending a soak
period (Step 50 in the private runbook); the Stage 3.9 cutover was validated via
direct Lambda invocation rather than a live browser session; and Stage 3.10's
coach system prompt / rail classifier prompt are functional placeholders whose
final wording and eval-driven tuning is exactly what Stage 3.11 owns.

Stages 3.1–3.6 (Phase One — MVP) are complete and live. Phase Two (security audit,
Stage 3.8) is tracked in the private repo. Stage 3.7 (Public View) remains parked.

Phase mapping to the public project narrative
(`hugo/content/projects/running-tracker-proj.md`):
- Phase One (single-user MVP) = Stages 3.1–3.6 (done)
- Phase Two (security audit) = Stage 3.8 (private repo)
- Phase Three (identity foundation) = Stage 3.9
- Phase Four (the AI coach) = Stages 3.10–3.11

---

## Stage 3.1 — Infrastructure

**Goal:** train.tacedata.ca resolves over HTTPS. S3 bucket, CloudFront distribution,
wildcard ACM cert, and Route 53 record in place. DynamoDB table seeded with all 105 days.

**Definition of done:**
- `https://train.tacedata.ca/` loads (serving placeholder index.html)
- SSL cert valid — `*.tacedata.ca` wildcard (us-east-1)
- S3 bucket `tacedata-train` — private, CloudFront OAC access only
- DynamoDB table `training-plan` — 105 items seeded, PK = `date`
- Route 53 A alias record for `train.tacedata.ca` → CloudFront

**Runbook:** `TACE.Website-private/config/runbook-tracker.md` Stages 1–5, 13

---

## Stage 3.2 — Auth

**Goal:** Login with Google. Only authenticated users can access the app.

**Definition of done:**
- Cognito User Pool `tacedata-train-pool` with Google IdP
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
- EventBridge rule `tracker-daily-email` fires daily at 11:00 UTC (7am EDT)
- Email arrives at scott.leblanc@tacedata.ca

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
  `{user_id: <owner sub>, date}`; owner `sub` retrieved from `tacedata-train-pool`
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
  `tracker-coach-execution-role` (RW on `conversations`, read-only on
  `training-plan-v2` + `training-plan-overrides`), routes on the existing HTTP
  API behind the existing Cognito authorizer. Validated: full CRUD lifecycle
  for the owner; the Stage 3.9 fixture identity gets 404 on every verb with no
  write landing; delete removes the thread from the list.
- **`/settings`:** added to `days_api.py` (tracker-api) rather than the new
  Lambda — `coach_scope` lives on the `training-users` record tracker-api
  already owns via `_ensure_profile`, so the coach role never needs
  `training-users` write access. Required adding `dynamodb:UpdateItem` on
  `training-users` to `tracker-api-execution-role` (previously `GetItem`/
  `PutItem` only). Validated: default `plan_only`, update to
  `plan_plus_general`, persists, invalid value rejected with 400.
- **Anthropic setup:** API key in Secrets Manager
  (`<COACH_SECRET_NAME>`, created by the user directly so the key
  never entered the session); Anthropic Python SDK built as a Lambda layer
  (`tracker-coach-anthropic-sdk`, `pip install --platform
  manylinux2014_x86_64 --python-version 3.12` to get `jiter`'s compiled wheel
  rather than a source build); `tracker-coach-execution-role` scoped to
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
  `tracker-coach` code-update step; `tacedata-github-deploy` granted the
  matching Lambda/layer permissions; new repo variable
  `TRACKER_LAMBDA_COACH=tracker-coach`. Not yet exercised through a real CI
  run — branch not merged/pushed.
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

- IAM deploy role `tacedata-github-deploy` updated — S3 tacedata-train, CloudFront <TRACKER_DISTRIBUTION_ID>, Lambda tracker-api + tracker-email
- deploy.yml: tracker SPA sync, CloudFront invalidation, Lambda updates for both functions
- GitHub Actions variables: `TRACKER_DISTRIBUTION_ID`, `TRACKER_LAMBDA_API`, `TRACKER_LAMBDA_EMAIL`
- Validated: full run green in 19s (run <GHA_RUN_ID>)
- Note: actions/checkout and configure-aws-credentials need Node.js 24 version bumps before 2026-09-16

---

### Stage 3.5 — Email Notifications (2026-06-13)

- SES domain `tacedata.ca` verified in ca-central-1 (DKIM CNAMEs added to Route 53)
- IAM role `tracker-email-execution-role` — DynamoDB read + SES SendEmail + CloudWatch Logs
- Lambda `tracker-email` — Python 3.12, `daily_email.handler`
- Env: `DYNAMODB_TABLE=training-plan`, `SES_SENDER=noreply@tacedata.ca`, `RECIPIENT=scott.leblanc@tacedata.ca`
- EventBridge rule `tracker-daily-email` — `cron(0 11 * * ? *)` (11:00 UTC = 7am EDT)
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

- IAM role `tracker-api-execution-role` — DynamoDB (GetItem, UpdateItem, Scan) + CloudWatch Logs
- Lambda `tracker-api` — Python 3.12, `days_api.handler`, env `DYNAMODB_TABLE=training-plan`
- API Gateway HTTP API `tracker-api` — ID `<TRACKER_API_ID>`, endpoint `https://<TRACKER_API_ID>.execute-api.ca-central-1.amazonaws.com`
- Cognito JWT authorizer `<COGNITO_AUTHORIZER_ID>`, Lambda integration `<LAMBDA_INTEGRATION_ID>`
- Routes: GET /days, GET /days/{date}, PATCH /days/{date} — all JWT-protected
- Validated: GET /days returns 105 items; PATCH sets completed=true + completed_date

---

### Stage 3.2 — Auth (2026-06-13)

- Cognito User Pool `tacedata-train-pool` — `<COGNITO_USER_POOL_ID>`
- Google IdP configured — Client ID `<GOOGLE_OAUTH_CLIENT_ID>`
- App Client `tacedata-train-client` — `<COGNITO_CLIENT_ID>` (code flow, no secret, PKCE)
- Hosted UI domain — `<COGNITO_HOSTED_UI_DOMAIN>`
- Auth guard Lambda `tracker-auth-guard` — PreSignUp + PreTokenGeneration triggers
- Allowed emails: `<ALLOWED_EMAIL_1>`, `<ALLOWED_EMAIL_2>`
- Note: PreAuthentication does NOT fire for Google federated logins; PreSignUp blocks profile creation, PreTokenGeneration blocks token exchange
- Validated: non-allowed account rejected at PreSignUp; allowed account gets `?code=` redirect

---

### Stage 3.1 — Infrastructure (2026-06-13)

- ACM wildcard cert `*.tacedata.ca` — ISSUED (`arn:aws:acm:us-east-1:<AWS_ACCOUNT_ID>:certificate/<ACM_CERT_UUID>`)
- S3 bucket `tacedata-train` — private, CloudFront OAC only
- CloudFront distribution `<TRACKER_DISTRIBUTION_ID>` — `<TRACKER_CF_DOMAIN>` (deploying)
- Route 53 A alias `train.tacedata.ca` → CloudFront
- DynamoDB `training-plan` — 105 items seeded, `completed: false`
- Placeholder `index.html` deployed to S3
