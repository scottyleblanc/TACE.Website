# TODO — Training Plan Habit Tracker (Track 3)

Active build checklist for train.tacedata.ca.
Stages defined in `docs/tracker/STAGES.md`.
Build runbook (with real resource values): `TACE.Website-private/config/runbook-tracker.md`
Data dictionary and build brief: `dev/README.md`

---

## Stage 3.7 — Public View (Later Phase)

- [ ] Design read-only progress page (no auth)
- [ ] TBD

---

## Stage 3.8 — Security Hardening

Detailed findings and remediation tracking are kept in the private repo:
`TACE.Website-private/docs/train/SECURITY-AUDIT.md`. Frontend output-escaping and CloudFront
security headers landed 2026-06-20 (see CHANGELOG).

---

# Phase Three — Going Multi-User

Stage definitions and definitions-of-done: `docs/STAGES.md` (Phase Three).
Public narrative: `hugo/content/projects/running-tracker-proj.md` ("going multi-user").

## Stage 3.9 — Multi-Tenant Data Model

- [ ] Decide composite key design: `user_id` (PK) + `date` (SK); confirm `user_id` = Cognito `sub`
- [ ] Provision new table (or GSI strategy) with the composite key
- [ ] `days_api.py`: read `user_id` from JWT claims on every route — never from body/path [SEC]
- [ ] `GET /days`: replace `Scan` with `Query` on the user partition
- [ ] `GET /days/{date}` and `PATCH /days/{date}`: key on `{user_id, date}`; cross-user access returns 404 [SEC]
- [ ] One-time migration script: move existing single-user data into the owner's partition
- [ ] `seed_dynamo.py`: write items under a `user_id`
- [ ] Validate: all 105 days load and check off for the original account post-migration
- [ ] Update execution-role IAM policy if table ARN changes

## Stage 3.10 — Onboarding and Plan Generation

- [ ] Design intake form fields (fitness/run history, race date, distance, days/week, constraints)
- [ ] Build intake form in the SPA
- [ ] Plan-generation Lambda: call Claude API with intake + coach prompt
- [ ] Schema validator: row count, required fields, types, date continuity, active-day flags [SEC]
- [ ] Reject invalid generated plans — treat model output as untrusted input [SEC]
- [ ] Write validated plan under the new user's partition (one item/day)
- [ ] Onboarding writes a `users` record (`user_id`, `email`, start/race dates) for the email Lambda to read
- [ ] First-run routing: logged-in user with no plan → intake form → populated dashboard
- [ ] Idempotency: re-submitting intake does not duplicate/corrupt an existing plan
- [ ] Validate end-to-end with a fresh test account

## Stage 3.11 — Multi-User Email and Registration

- [ ] `daily_email.py`: read the `users` record, brief each user from their own partition
- [ ] Per-user streak, session detail, tomorrow's preview
- [ ] Invite store: admin issues an invite for a specific email
- [ ] `auth_guard.py`: gate signup on the invited-email set instead of static `ALLOWED_EMAILS` [SEC]
- [ ] Confirm public self-signup remains closed [SEC]
- [ ] Validate: second account signs up, generates plan, checks off a day, gets its own email
- [ ] Confirm no cross-user data visibility at any layer (API, email) [SEC]

---

# Phase Four — The AI Layer

Stage definitions and definitions-of-done: `docs/STAGES.md` (Phase Four).
Public narrative: `hugo/content/projects/running-tracker-proj.md` ("the ai layer").

## Stage 3.12 — Secrets and Coach Endpoint

- [ ] Store Claude API key in AWS Secrets Manager [SEC]
- [ ] Coach Lambda: read caller's full plan + progress from their partition
- [ ] Package Anthropic SDK as a Lambda layer; attach to coach function; update `deploy.yml`
- [ ] Build single-prompt request to Claude API via the SDK (whole dataset in prompt; no RAG)
- [ ] Choose model (default current Claude: `claude-sonnet-4-6` latency/cost vs `claude-opus-4-8` quality)
- [ ] New route `POST /coach`, Cognito JWT-protected, CORS scoped to train.tacedata.ca [SEC]
- [ ] IAM: coach role gets `secretsmanager:GetSecretValue` on the one secret ARN + read on user partition only [SEC]
- [ ] Validate: "what is my long run Saturday?" returns an answer grounded in caller's real data

## Stage 3.13 — Coach UI and Guardrails

- [ ] Chat UI in the SPA (ask/answer; conversation scoped to signed-in user)
- [ ] Guardrail: answers only from the user's plan and progress data [SEC]
- [ ] Guardrail: stays in running-coach role; declines code generation / off-topic [SEC]
- [ ] Guardrail: defers injury/medical questions to a physio [SEC]
- [ ] Per-user rate limiting + max-tokens cap on responses [SEC]
- [ ] Adversarial validation: off-topic, injection attempt, injury question → intended refusals/deferrals [SEC]

---

## Parking Lot

- Consider custom Cognito domain `auth.tacedata.ca` (already covered by wildcard cert)
- AI coaching hook: notes + coaching_focus → Claude API → contextual feedback
- DST handling for EventBridge email rule (adjust cron at clock changes)
- Reduce `/days` first-load latency (observed ~600-900ms, likely `tracker-api` Lambda cold start) — options: provisioned concurrency or a lighter `/days` payload. Login-screen flash on refresh already fixed via the dashboard loading state (2026-06-20); this would shorten the remaining "Loading..." wait.
