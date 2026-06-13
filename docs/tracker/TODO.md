# TODO — Training Plan Habit Tracker (Track 3)

Active build checklist for train.tacedata.ca.
Stages defined in `docs/tracker/STAGES.md`.
Build runbook (with real resource values): `TACE.Website-private/config/runbook-tracker.md`
Data dictionary and build brief: `dev/README.md`

---

## Stage 3.1 — Infrastructure

- [x] Request ACM wildcard cert `*.tacedata.ca` in us-east-1 (runbook Step 1)
- [x] Add ACM DNS validation CNAME to Route 53 (runbook Step 3) — reused existing CNAME, auto-ISSUED
- [x] Wait for cert ISSUED status (runbook Step 4)
- [x] Create S3 bucket `tacedata-train` (runbook Step 5)
- [x] Block all public access on bucket (runbook Step 6)
- [x] Create CloudFront OAC (runbook Step 7) — OAC ID: <TRACKER_OAC_ID>
- [x] Create CloudFront distribution — `train.tacedata.ca`, S3 origin, error page → index.html (runbook Steps 8–9) — ID: <TRACKER_DISTRIBUTION_ID>
- [x] Apply S3 bucket policy (allow CloudFront OAC) (runbook Step 10)
- [x] Create Route 53 A alias record `train.tacedata.ca` → CloudFront (runbook Step 11)
- [x] Create DynamoDB table `training-plan` (PK: `date`) (runbook Step 12)
- [x] Deploy placeholder `index.html` to S3 — validate https://train.tacedata.ca/ loads
- [x] Run `seed_dynamo.py` — seed all 105 days (runbook Step 13)
- [x] Validate seed: count 105 items, spot-check 2026-06-15

---

## Stage 3.2 — Auth

- [x] Set up Google OAuth2 app in Google Cloud Console (runbook Prerequisites)
- [x] Store Google Client ID + Secret in 1Password as "Google OAuth — train.tacedata.ca"
- [x] Create Cognito User Pool `tacedata-train-pool` (runbook Step 14)
- [x] Create Google IdP in Cognito (runbook Step 15)
- [x] Create Cognito App Client `tacedata-train-client` (runbook Step 16)
- [x] Create Cognito Hosted UI domain `tacedata-train` (runbook Step 17)
- [x] Validate end-to-end login: browser → Cognito Hosted UI → Google → redirect back to train.tacedata.ca
- [x] Write `tracker/lambda/auth_guard.py` — PreSignUp + PreTokenGeneration trigger, rejects non-allowed Google accounts
- [x] Create IAM role `tracker-auth-guard-role` (AWSLambdaBasicExecutionRole only) (runbook Step 18)
- [x] Deploy `tracker-auth-guard` Lambda (runbook Step 18)
- [x] Grant Cognito permission to invoke auth guard (runbook Step 19)
- [x] Wire auth guard as PreSignUp + PreTokenGeneration trigger on `<COGNITO_USER_POOL_ID>` (runbook Step 20)
- [x] Validate: non-owner Google account is rejected at login (runbook Step 21)

---

## Stage 3.3 — Backend API

- [x] Write `tracker/lambda/days_api.py` — GET /days, GET /days/{date}, PATCH /days/{date}
- [x] Create IAM execution role `tracker-api-execution-role` (runbook Step 18)
- [x] Deploy `tracker-api` Lambda (runbook Step 20)
- [x] Set Lambda environment variables (runbook Step 21)
- [x] Create API Gateway HTTP API `tracker-api` (runbook Step 24)
- [x] Create Cognito JWT authorizer (runbook Step 25)
- [x] Create Lambda integration (runbook Step 26)
- [x] Create routes GET /days, GET /days/{date}, PATCH /days/{date} (runbook Step 27)
- [x] Create auto-deploy stage (runbook Step 28)
- [x] Grant API Gateway permission to invoke Lambda (runbook Step 29)
- [x] Validate: GET /days returns 105 items (2026-06-15 → 2026-09-27)
- [x] Validate: PATCH /days/2026-06-15 sets completed=true in DynamoDB

---

## Stage 3.4 — Frontend SPA

- [x] Write `tracker/src/auth.js` — Cognito PKCE login flow, token storage, refresh
- [x] Write `tracker/src/app.js` — load days, render today card, streak, weekly row
- [x] Write `tracker/src/index.html` — layout, login redirect, dashboard container
- [x] Write `tracker/src/style.css` — clean, readable, no emojis
- [x] Implement checkbox check-off (PATCH /days/{date} completed=true)
- [x] Implement notes field (PATCH /days/{date} notes=text)
- [x] Streak logic: consecutive active days completed, rest days skipped
- [x] Weekly adherence display: completed/5 for current week
- [x] Overall progress: completed/75 active days
- [x] Deploy SPA to S3 and validate end-to-end in browser

---

## Stage 3.5 — Email Notifications

- [x] Write `tracker/lambda/daily_email.py` — active day + rest day email logic
- [x] Check SES verification status for tacedata.ca (runbook Step 30 — already verified)
- [x] Verify tacedata.ca in SES if needed; add DKIM CNAMEs to Route 53
- [x] Create IAM execution role `tracker-email-execution-role` (runbook Step 19)
- [x] Deploy `tracker-email` Lambda (runbook Step 22)
- [x] Set Lambda environment variables (runbook Step 23)
- [x] Create EventBridge rule `tracker-daily-email` — cron(0 11 * * ? *) (runbook Step 31)
- [x] Grant EventBridge permission to invoke Lambda (runbook Step 32)
- [x] Add Lambda as EventBridge target (runbook Step 33)
- [x] Invoke Lambda manually — confirm email arrives at scott.leblanc@tacedata.ca
- [x] Validate rest day email format (test_date=2026-06-19, Week 1 Friday)
- [x] Validate active day email format (test_date=2026-06-15, Day 1 Strength & Mobility)

---

## Stage 3.6 — CI/CD Integration

- [ ] Update `tracker-api-execution-role` to allow Lambda deploy from GitHub Actions role
- [ ] Update GitHub Actions deploy role policy (runbook Step, Stage 12)
- [ ] Add tracker SPA sync step to `.github/workflows/deploy.yml`
- [ ] Add Lambda update steps for `tracker-api` and `tracker-email` to `deploy.yml`
- [ ] Add CloudFront invalidation for tracker distribution to `deploy.yml`
- [ ] Add GitHub Actions variables: `TRACKER_DISTRIBUTION_ID`, `TRACKER_LAMBDA_API`, `TRACKER_LAMBDA_EMAIL`
- [ ] Validate full deploy: push to main → SPA + Lambdas updated

---

## Stage 3.7 — Public View (Later Phase)

- [ ] Design read-only progress page (no auth)
- [ ] TBD

---

## Parking Lot

- Consider custom Cognito domain `auth.tacedata.ca` (already covered by wildcard cert)
- AI coaching hook: notes + coaching_focus → Claude API → contextual feedback
- DST handling for EventBridge email rule (adjust cron at clock changes)
