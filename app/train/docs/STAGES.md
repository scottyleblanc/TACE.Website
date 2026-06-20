# STAGES — Training Plan Habit Tracker (Track 3)

Phase definitions and current state for the habit tracker at train.tacedata.ca.

Plan: 15-week 5K-to-10K training plan, June 15 – September 27, 2026.
Full build brief: `dev/README.md`

---

## Current Focus: Phase Three — Multi-User (Stage 3.9)

Stages 3.1–3.6 (Phase One — MVP) are complete and live. Phase Two (security audit,
Stage 3.8) is tracked in the private repo. Phase Three (multi-user) and Phase Four
(AI layer) are the next build-out, broken into Stages 3.9–3.13 below.
Stage 3.7 (Public View) remains parked as a later, optional phase.

Phase definitions map to the public project narrative at
`hugo/content/projects/running-tracker-proj.md`:
- Phase One (single-user MVP) = Stages 3.1–3.6 (done)
- Phase Two (security audit) = Stage 3.8
- Phase Three (going multi-user) = Stages 3.9–3.11
- Phase Four (the AI layer) = Stages 3.12–3.13

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
- Login flow: redirect to Cognito Hosted UI, handle callback, store tokens
- Today's session card: session type, detail, coaching focus, minutes target
- Streak counter and overall progress bar
- Weekly checklist row (current week's active days)
- Checkbox completes a day (PATCH to API)
- Notes field saves per-day journal entry (PATCH to API)
- Rest days shown but not checkable

---

## Stage 3.5 — Email Notifications

**Goal:** Daily briefing email every day including rest days.

**Definition of done:**
- SES domain `tacedata.ca` verified in ca-central-1
- Lambda `tracker-email` deployed
- Active day email: session type, detail, coaching focus, minutes, run/walk ratio, current streak, link
- Rest day email: recovery note, tomorrow's session preview, current streak, link
- EventBridge rule `tracker-daily-email` fires daily at 11:00 UTC (7am EDT)
- Email arrives at scott.leblanc@tacedata.ca

**Runbook:** `TACE.Website-private/config/runbook-tracker.md` Stages 10–11

---

## Stage 3.6 — CI/CD Integration

**Goal:** GitHub Actions deploys SPA and Lambda updates on push to main.

**Definition of done:**
- `deploy.yml` syncs `app/train/src/` to `tacedata-train` S3 bucket
- `deploy.yml` updates `tracker-api` and `tracker-email` Lambda code
- CloudFront invalidation on deploy
- GitHub Actions variables added: `TRACKER_DISTRIBUTION_ID`, `TRACKER_LAMBDA_API`, `TRACKER_LAMBDA_EMAIL`

**Runbook:** `TACE.Website-private/config/runbook-tracker.md` Stage 12, 14

---

## Stage 3.7 — Public View (Later Phase)

**Goal:** Read-only shareable progress page. No auth, no check-off ability.

**Definition of done:** TBD

---

# Phase Three — Going Multi-User

Let a second person log in and generate their own plan from an intake form. Claude
writes the plan in the same schema the tracker already understands; generated output is
validated before it is stored (treated as untrusted input). Multi-tenancy comes from a
composite key (user + date) and Cognito for isolation, so each person sees only their
own data.

The single-user build keys every DynamoDB item on `date` alone, and the API does no
per-user scoping — the JWT only gates access (see `lambda/days_api.py`). Phase Three's
core change is partitioning all data and reads by the authenticated user.

---

## Stage 3.9 — Multi-Tenant Data Model

**Goal:** Every training day belongs to a user. Reads and writes are scoped to the
authenticated caller — no user can see or modify another user's data.

**Definition of done:**
- DynamoDB table uses composite key: `user_id` (PK, partition) + `date` (SK, sort)
  - `user_id` is the Cognito `sub` claim — stable, opaque, not the email
- `days_api.py` derives `user_id` from the JWT claims
  (`event.requestContext.authorizer.jwt.claims.sub`) on every route — never from the
  request body or path
- `GET /days` uses `Query` on the user partition (not `Scan`)
- `GET /days/{date}` and `PATCH /days/{date}` key on `{user_id, date}`; cross-user access
  returns 404, never another user's item
- Existing single-user data migrated into the owner's partition (one-time migration
  script; `seed_dynamo.py` updated to write under a `user_id`)
- All 105 days still load and check off end-to-end for the original account after migration

**Implementer notes:**
- DynamoDB key schema is **immutable** — you cannot add a partition key to the existing
  `training-plan` table, and a GSI does not solve write-partitioning (writes still collide
  on `date` across users). Create a **new table** (e.g. `training-plan-v2`), migrate, then
  repoint the `DYNAMODB_TABLE` env var on both `tracker-api` and `tracker-email`. Table
  name is hardcoded as `TABLE_NAME` in `scripts/seed_dynamo.py` and read from
  `DYNAMODB_TABLE` in both Lambdas.
- The original account's `user_id` (Cognito `sub`) is needed for the migration — retrieve
  it from the Cognito User Pool `tacedata-train-pool` (see completed Stage 3.2 for the
  pool/client IDs in the private runbook). The migration script reads every existing item
  (keyed on `date`) and rewrites it with `{user_id: <sub>, date}`.
- Cross-user 404: a `get_item`/`update_item` on `{user_id, date}` for a non-owned row
  simply misses — no extra ownership check needed, since the partition key isolates it.

---

## Stage 3.10 — Onboarding and Plan Generation

**Goal:** A new user fills in an intake form and gets a personalized plan generated by
Claude, stored in the same schema the tracker reads.

**Definition of done:**
- Intake form (frontend) collects the plan inputs: current fitness/run history, race
  date, target distance, days/week available, known constraints
- Plan-generation Lambda calls the Claude API with the intake inputs and a coach prompt
  (API key from Secrets Manager — see Stage 3.12; never in the browser)
- Generated plan is **validated against the day/week schema before any write** — generated
  output is treated as untrusted input; an invalid plan is rejected, not stored. Validate:
  - one item per calendar day from start to race date (no gaps, no duplicate dates) —
    count is **derived from the intake start/race dates**, not the original fixed 105
  - every required field present with the correct type (the canonical item shape is the
    single source of truth: `build_item()` in `scripts/seed_dynamo.py`; data dictionary in
    `dev/README.md`)
  - `is_active_day` / `is_run_day` are booleans; `session_minutes_target` an int; nullable
    fields (`run_interval_minutes`, `run_walk_ratio`, etc.) omitted rather than empty
- Validated plan written under the new user's `user_id` partition (one item per day)
- Onboarding writes a `users` record (`user_id`, `email`, and plan metadata such as start
  and race dates) — this is the list the email Lambda reads in Stage 3.11
- First-run flow: a logged-in user with no plan is routed to the intake form; on success
  they land on the populated dashboard
- Idempotency: re-submitting intake does not silently duplicate or corrupt an existing plan

**Implementer notes:**
- Claude API integration: see the `claude-api` skill for current model IDs, the Anthropic
  SDK, structured-output/tool-use patterns, and token counting. Have the model return the
  plan as JSON matching the item schema; validate that JSON before any DynamoDB write.
- The originating coach prompt that produced the seed data is quoted in the public
  narrative (`hugo/content/projects/running-tracker-proj.md`) — reuse it as the basis for
  the generation system prompt.

---

## Stage 3.11 — Multi-User Email and Registration

**Goal:** Each user gets their own daily briefing, and a second account can be admitted
without code changes to a hardcoded allowlist.

**Definition of done:**
- `daily_email.py` sends a per-user briefing: it resolves each active user, reads that
  user's partition, and sends to that user's verified address
- Streak, session detail, and tomorrow's preview are computed per user
- Registration is **invite-only**: the two-email `ALLOWED_EMAILS` allowlist in
  `auth_guard.py` is replaced by an invite mechanism — an admin issues an invite for a
  specific email, and only invited emails can complete signup. Public self-signup stays
  closed.
- A second real account completes signup, generates a plan, checks off a day, and
  receives its own briefing email — with no visibility into the first user's data

**Implementer notes:**
- User enumeration (decided): onboarding (Stage 3.10) writes a lightweight `users` record
  per user; the email Lambda reads that list of `(user_id, email)` to brief — no
  full-table scan, no Cognito `ListUsers` dependency in the email path.
- Invite mechanism: an invited-emails store gates signup. `auth_guard.py` checks the
  invited set instead of a static `ALLOWED_EMAILS` env var. Keep the existing PreSignUp /
  PreTokenGeneration trigger model from Stage 3.2 (PreAuthentication does not fire for
  Google federated logins).
- Keep the single daily EventBridge rule; loop over users **inside** one invocation rather
  than one rule per user.

---

# Phase Four — The AI Layer

The plan is small enough that the entire dataset fits in a single prompt, so the coach
endpoint sends the whole thing to the Claude API with each question — no vector database,
no retrieval machinery. It answers grounded in the user's real plan and progress.
Guardrails matter: it answers only from the plan, it is a running coach (not a code
generator), and it defers anything injury-related to a physio rather than playing doctor.

---

## Stage 3.12 — Secrets and Coach Endpoint

**Goal:** An authenticated user can ask the coach a question and get an answer grounded
in their own plan and progress.

**Definition of done:**
- Claude API key stored in AWS Secrets Manager — never in the browser, never in Lambda
  env vars in plaintext, never in source
- Coach Lambda reads the caller's full plan + progress from their `user_id` partition and
  sends it in a single prompt to the Claude API (default to a current Claude model —
  e.g. `claude-sonnet-4-6` for latency/cost, `claude-opus-4-8` for quality)
- New route `POST /coach` on the existing HTTP API, Cognito JWT-protected, CORS scoped to
  `https://train.tacedata.ca`
- IAM: coach execution role granted `secretsmanager:GetSecretValue` on that one secret ARN
  plus DynamoDB read on the user's partition only
- End-to-end: a question like "what is my long run Saturday?" returns an answer that
  reflects the caller's actual plan data

**Implementer notes:**
- The existing Lambdas (`days_api.py`, `daily_email.py`) use only boto3, which is in the
  Lambda runtime. The coach Lambda uses the **Anthropic SDK** (decided), which is not —
  package it as a **Lambda layer** and attach it to the coach function; update `deploy.yml`
  to build/publish the layer (or pin a prebuilt layer version). See the `claude-api` skill
  for the SDK usage and current model IDs.
- Cache the secret value across warm invocations (module scope), not per request.

---

## Stage 3.13 — Coach UI and Guardrails

**Goal:** A usable in-app coach with enforced behavioural guardrails and cost controls.

**Definition of done:**
- Chat UI in the SPA (ask a question, see the answer; conversation scoped to the signed-in
  user)
- System prompt guardrails enforced and tested:
  - answers only from the user's plan and progress data
  - stays in the running-coach role — declines code generation and off-topic requests
  - defers injury/medical questions to a physio rather than giving medical advice
- Cost/abuse controls: per-user rate limiting and a max-tokens cap on responses
- Guardrail behaviour validated with adversarial prompts (off-topic, injection attempt,
  injury question) producing the intended refusals/deferrals

---

## Completed Stages

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
