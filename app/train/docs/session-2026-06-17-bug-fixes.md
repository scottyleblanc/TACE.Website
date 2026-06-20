# Bug Fix Session — 2026-06-17

## Context

This document captures a debugging session on the 10K Training Tracker (train.tacedata.ca), a personal habit tracker built as a learning project. The app is a vanilla JS SPA backed by AWS Lambda, API Gateway, DynamoDB, and Cognito. It tracks a 15-week training plan running June 15 – September 27, 2026.

Three bugs were found and fixed. A fourth was discovered as a consequence of fixing the third. All fixes were committed and deployed via GitHub Actions the same session.

---

## Bug 1 — Mobile Double-Login (auth.js)

### Symptom

On Android and iOS, clicking "Login with Google" would complete the Google authentication flow but land back on the login screen instead of the dashboard. A second click would succeed.

### Root Cause

The PKCE OAuth2 flow works by generating a random `code_verifier` before redirecting to the authorization server, then using that verifier to exchange the authorization code for tokens when the user comes back. The verifier was stored in `sessionStorage` before the redirect.

The problem: Android and iOS browsers (particularly Safari on iOS) clear `sessionStorage` when the page navigates away to a cross-origin destination. The login flow involves at least two cross-origin hops — Cognito's hosted UI domain, then Google's login page — before landing back at `train.tacedata.ca`. By the time the `?code=` callback arrived, `sessionStorage` had been wiped, the verifier was gone, and `handleCallback()` returned early without exchanging the code for tokens. The login screen was shown again.

The second click worked because Cognito had a fresh session cookie from the first attempt, so the redirect chain was shorter and faster, and `sessionStorage` survived.

### Fix

Replaced all `sessionStorage` usage in `auth.js` with `localStorage`. The PKCE verifier, OAuth state parameter, access token, ID token, refresh token, and token expiry all moved to `localStorage`. The `logout()` function, which previously called `sessionStorage.clear()`, was updated to explicitly remove each key from `localStorage`.

As a side effect, tokens now persist across tab closes, so users stay logged in between visits without needing to re-authenticate (until the refresh token expires).

### Commits

`d2c3e88` — fix(train): fix streak break on incomplete today, fix mobile double-login

---

## Bug 2 — Streak Shows 0 When It Should Show 1+ (app.js)

### Symptom

After completing a workout on Day 1 (June 15), the streak counter showed 0 the next morning instead of 1.

### Root Cause

The `computeStreak` function filtered all active training days up to and including today, sorted them newest-first, and walked backward counting consecutive completed days — breaking on the first incomplete one.

Today's active day (June 16) appears first in the sorted list. Since the user hadn't completed today's workout yet (it was 7 am), `completed` was `false`, and the loop broke immediately, returning 0 before ever reaching the completed day from the previous day.

```javascript
// Before fix
for (const d of active) {
    if (d.completed) streak++;
    else break;  // today's incomplete day killed the streak
}
```

### Fix

Added a `continue` for today's date. If the current day in the loop matches today and is not yet completed, it skips rather than breaks — allowing the loop to keep counting backward into completed past days.

```javascript
// After fix
for (const d of active) {
    if (d.completed) streak++;
    else if (d.date === todayStr) continue;
    else break;
}
```

### Commits

`d2c3e88` — fix(train): fix streak break on incomplete today, fix mobile double-login

---

## Bug 3 — UTC Date in todayISO() (app.js)

### Symptom

Streak remained 0 after Bug 2 was fixed. The fix was logically correct, but streak was still breaking on today's date. Also would have caused the wrong session card to display in the evening.

### Root Cause

The `todayISO()` function used `new Date().toISOString()`, which returns the date in UTC regardless of the user's local timezone. In Eastern Daylight Time (UTC−4), `toISOString()` returns the next calendar day after 8:00 pm local time.

So at 9 pm EDT on June 16, `todayISO()` returned `'2026-06-17'`. The Bug 2 fix then correctly skipped June 17 (today per UTC), but June 16 — now appearing to be a *past* missed active day — triggered `else break`, returning streak = 0. The fix only worked when tested during daytime hours.

```javascript
// Before fix
function todayISO() {
    return new Date().toISOString().slice(0, 10);  // UTC date
}
```

### Fix

Replaced with local date components:

```javascript
// After fix
function todayISO() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
```

This uses the browser's local date regardless of time of day, so the "today" comparison is always accurate for the user's timezone.

### Commits

`a89c772` — fix(train): use local date in todayISO, not UTC

---

## Bug 4 — Same Streak Bug in the Daily Email Lambda (daily_email.py)

### Symptom

The daily briefing email (sent at 7 am EDT via EventBridge) was reporting streak = 0 when the correct value was 2.

### Root Cause

The `_compute_streak` function in the email Lambda had the identical logic flaw as the frontend. It walked backward through active days and broke on the first incomplete one. At 7 am, today's workout obviously hasn't been done yet, so the streak always read 0.

```python
# Before fix
for d in reversed(active_past):
    if d.get("completed"):
        streak += 1
    else:
        break  # today's incomplete day broke the streak
```

A secondary bug was also found: the rest day email computed tomorrow's session preview using `date.today()` (the actual current date) instead of `today_str` (which respects the `test_date` event override used for testing). This made manual test invocations with a `test_date` parameter show the wrong tomorrow preview.

### Fix

Added the same `continue` logic for `today_str`, and fixed the tomorrow lookup to derive from `today_str`:

```python
# After fix
for d in reversed(active_past):
    if d.get("completed"):
        streak += 1
    elif d["date"] == today_str:
        continue  # today not yet done -- don't break the streak
    else:
        break
```

```python
# Before
tomorrow_day = _day_for(days, (date.today() + timedelta(days=1)).isoformat())

# After
tomorrow_day = _day_for(days, (date.fromisoformat(today_str) + timedelta(days=1)).isoformat())
```

The fix was tested by invoking the Lambda directly with `test_date: 2026-06-17`. The email arrived with the correct streak count.

### Commits

`944779e` — fix(train): fix streak in daily email, fix tomorrow lookup on test_date

---

## What Was Not Changed

- `completed_date` in `days_api.py` uses `datetime.now(timezone.utc)` — this is UTC, but `completed_date` is audit metadata only and is not used in any display or streak logic. Left as-is.
- The email Lambda's `date.today()` for determining the current day uses UTC, but the email fires at 11:00 UTC (7 am EDT), so there is no day boundary risk at that hour.

---

## Commits Summary

| Commit | Change |
|--------|--------|
| `d2c3e88` | auth.js: sessionStorage → localStorage; app.js: continue on today in computeStreak |
| `a89c772` | app.js: todayISO uses local date, not UTC |
| `944779e` | daily_email.py: continue on today_str in _compute_streak; fix tomorrow lookup |
