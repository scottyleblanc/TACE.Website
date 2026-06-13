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

- [ ] Set up Google OAuth2 app in Google Cloud Console (runbook Prerequisites)
- [ ] Store Google Client ID + Secret in 1Password as "Google OAuth — train.tacedata.ca"
- [ ] Create Cognito User Pool `tacedata-train-pool` (runbook Step 14)
- [ ] Create Google IdP in Cognito (runbook Step 15)
- [ ] Create Cognito App Client `tacedata-train-client` (runbook Step 16)
- [ ] Create Cognito Hosted UI domain `tacedata-train` (runbook Step 17)
- [ ] Validate end-to-end login: browser → Cognito Hosted UI → Google → redirect back to train.tacedata.ca

---

## Stage 3.3 — Backend API

- [ ] Write `tracker/lambda/days_api.py` — GET /days, GET /days/{date}, PATCH /days/{date}
- [ ] Create IAM execution role `tracker-api-execution-role` (runbook Step 18)
- [ ] Deploy `tracker-api` Lambda (runbook Step 20)
- [ ] Set Lambda environment variables (runbook Step 21)
- [ ] Create API Gateway HTTP API `tracker-api` (runbook Step 24)
- [ ] Create Cognito JWT authorizer (runbook Step 25)
- [ ] Create Lambda integration (runbook Step 26)
- [ ] Create routes GET /days, GET /days/{date}, PATCH /days/{date} (runbook Step 27)
- [ ] Create auto-deploy stage (runbook Step 28)
- [ ] Grant API Gateway permission to invoke Lambda (runbook Step 29)
- [ ] Validate: GET /days with valid Cognito token returns 105 items
- [ ] Validate: PATCH /days/2026-06-15 sets completed=true in DynamoDB

---

## Stage 3.4 — Frontend SPA

- [ ] Write `tracker/src/auth.js` — Cognito PKCE login flow, token storage, refresh
- [ ] Write `tracker/src/app.js` — load days, render today card, streak, weekly row
- [ ] Write `tracker/src/index.html` — layout, login redirect, dashboard container
- [ ] Write `tracker/src/style.css` — clean, readable, no emojis
- [ ] Implement checkbox check-off (PATCH /days/{date} completed=true)
- [ ] Implement notes field (PATCH /days/{date} notes=text)
- [ ] Streak logic: consecutive active days completed, rest days skipped
- [ ] Weekly adherence display: completed/5 for current week
- [ ] Overall progress: completed/75 active days
- [ ] Deploy SPA to S3 and validate end-to-end in browser

---

## Stage 3.5 — Email Notifications

- [ ] Write `tracker/lambda/daily_email.py` — active day + rest day email logic
- [ ] Check SES verification status for tacedata.ca (runbook Step 30 — may already be done)
- [ ] Verify tacedata.ca in SES if needed; add DKIM CNAMEs to Route 53
- [ ] Create IAM execution role `tracker-email-execution-role` (runbook Step 19)
- [ ] Deploy `tracker-email` Lambda (runbook Step 22)
- [ ] Set Lambda environment variables (runbook Step 23)
- [ ] Create EventBridge rule `tracker-daily-email` — cron(0 11 * * ? *) (runbook Step 31)
- [ ] Grant EventBridge permission to invoke Lambda (runbook Step 32)
- [ ] Add Lambda as EventBridge target (runbook Step 33)
- [ ] Invoke Lambda manually — confirm email arrives at scott.leblanc@tacedata.ca
- [ ] Validate rest day email format
- [ ] Validate active day email format

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
