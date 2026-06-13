# STAGES — Training Plan Habit Tracker (Track 3)

Phase definitions and current state for the habit tracker at train.tacedata.ca.

Plan: 15-week 5K-to-10K training plan, June 15 – September 27, 2026.
Full build brief: `dev/README.md`

---

## Current Stage: Stage 3.5 — Email Notifications (Not Started)

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
- `deploy.yml` syncs `tracker/src/` to `tacedata-train` S3 bucket
- `deploy.yml` updates `tracker-api` and `tracker-email` Lambda code
- CloudFront invalidation on deploy
- GitHub Actions variables added: `TRACKER_DISTRIBUTION_ID`, `TRACKER_LAMBDA_API`, `TRACKER_LAMBDA_EMAIL`

**Runbook:** `TACE.Website-private/config/runbook-tracker.md` Stage 12, 14

---

## Stage 3.7 — Public View (Later Phase)

**Goal:** Read-only shareable progress page. No auth, no check-off ability.

**Definition of done:** TBD

---

## Completed Stages

### Stage 3.4 — Frontend SPA (2026-06-13)

- `tracker/src/auth.js` — PKCE flow, token storage, refresh, logout
- `tracker/src/app.js` — today card, streak, progress bar, weekly row, checkbox, notes
- `tracker/src/index.html` — login screen + dashboard structure
- `tracker/src/style.css` — clean, no emojis
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
