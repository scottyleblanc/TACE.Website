# Session Notes: UI Polish and Race-Day Countdown
**Date:** June 20, 2026
**Repo:** TACE.Website — `app/train/`
**Commit:** `47d8b88`

---

## What Was Built

This session covered cosmetic improvements to the 10K training tracker at `train.tacedata.ca` — a personal 105-day running plan tracker built on a serverless AWS stack (S3 + CloudFront, API Gateway, Lambda, DynamoDB, Cognito, SES).

The app was already fully functional: Google OAuth login, a daily training card showing session type and coaching focus, a streak counter, overall progress bar, weekly adherence grid, and daily email briefings via EventBridge + SES. Stages 3.1–3.6 were complete and live.

This session added a docs folder and made three small UI changes before committing and deploying.

---

## Changes Made

### 1. Added `app/train/docs/`

Two documentation files — `TODO.md` and `STAGES.md` — were moved from `docs/tracker/` into `app/train/docs/`, co-locating them with the rest of the tracker code. These files capture the full build checklist and completed stage records (infrastructure IDs, auth config, API Gateway details, CI/CD validation run).

### 2. Rebranded from "Training Tracker" to "10K Training Program"

The app was originally titled "Training Tracker" with a subtitle of "5K to 10K — June 15 to September 27, 2026." Since this is a 10K training program (not a couch-to-5K), the 5K reference was removed.

Changes:
- `<title>` tag: `Training Tracker` → `10K Training Program`
- Login card `<h1>`: `Training Tracker` → `10K Training Program`
- Login card subtitle: `5K to 10K — June 15 to September 27, 2026` → `June 15 – September 27, 2026`
- Dashboard header: `Training Tracker` → `10K Training Tracker`

The subtitle was also simplified — since the h1 already says "10K Training Program," repeating "10K" in the subtitle was redundant. Trimming it to just the date range keeps the login card clean.

### 3. Race-Day Countdown

A live countdown was added showing the number of days remaining until September 27, 2026 (race day).

It appears in two places:

**Login card** — a blue line below the date subtitle: *"99 days to race day"*. Visible before authentication, so it's the first thing you see when you open the app. On race day itself it reads "Race day!"

**Dashboard stats row** — a third stat box alongside the existing streak counter and overall progress bar. Shows a large number with "days to go" beneath it. On race day it shows "Today!" with no unit label.

The countdown is computed in JavaScript from the local date — no API call needed. It runs at the very start of `init()` before any auth check, so both the login screen and dashboard are populated immediately with no flicker.

```js
function computeCountdown() {
  const race = new Date('2026-09-27T00:00:00');
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.max(0, Math.floor((race - today) / 86400000));
}
```

CSS-wise, the login subtitle margin was tightened from `32px` to `6px` and the countdown element takes `28px` of bottom margin, visually grouping the date and countdown as a unit above the login button.

---

## Files Changed

| File | What changed |
|---|---|
| `src/index.html` | Page title, login h1, subtitle, dashboard header, countdown elements added |
| `src/app.js` | `computeCountdown()` and `renderCountdown()` added; called at init |
| `src/style.css` | `.login-sub` margin reduced; `.login-countdown` style added |
| `docs/STAGES.md` | Moved from `docs/tracker/STAGES.md` |
| `docs/TODO.md` | Moved from `docs/tracker/TODO.md` |

---

## Stack Context (for blog post reference)

- **Frontend:** Vanilla JavaScript + HTML/CSS, no framework. Hosted on S3 behind CloudFront.
- **Auth:** AWS Cognito with Google IdP, OAuth2 + PKCE flow. A pre-token-generation Lambda (`auth_guard.py`) enforces an email allowlist so only two accounts can log in.
- **API:** API Gateway HTTP API → Python Lambda (`days_api.py`) → DynamoDB table `training-plan` (105 items, keyed on `date`). Routes: `GET /days`, `GET /days/{date}`, `PATCH /days/{date}`.
- **Email:** EventBridge cron at 11:00 UTC triggers a Lambda (`daily_email.py`) that reads the day's training data from DynamoDB and sends a briefing via SES. Active days get session details, coaching focus, run:walk ratio, and current streak. Rest days get a recovery note and tomorrow's session preview.
- **CI/CD:** GitHub Actions deploys SPA to S3, updates both Lambdas, and invalidates CloudFront on every push to main.
- **Region:** ca-central-1 (Lambda, DynamoDB, Cognito, SES); us-east-1 (ACM cert for CloudFront).

---

## What's Next (Stage 3.7)

The only remaining stage is a read-only public progress page — no auth required, no check-off ability. Design is TBD.
