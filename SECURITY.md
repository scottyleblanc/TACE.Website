# Security Policy

| | |
|---|---|
| **Version** | v3.4.0 |
| **Last review** | 2026-11-11 — full-repository review for this document, plus an adversarial review of the econ Lambda and dashboard |
| **Findings resolved** | 12 of 12 from the 2026-11-11 econ review (2 HIGH, 3 MEDIUM, 7 LOW; 2 tagged `[SEC]`) |
| **Open items** | 10 — see [Open items](#open-items) |
| **Automated tests** | Econ Lambda: 83 offline (CI deploy gate) + 6 opt-in live. AI coach: 37 eval cases (CI on prompt changes). Tracker SPA: static id-consistency check. Tracker Lambdas: none — see open items. |

This document describes what is **built and running**, not what is planned. It is updated at the
end of every implementation stage. Infrastructure identifiers (account IDs, bucket names, distribution
IDs, role names, API hostnames) are deliberately absent — this repository is public.

---

## Reporting a Vulnerability

Report security issues by email to **contact@tacedata.ca**. Please do not open a public GitHub issue.
The same contact is published at `https://tacedata.ca/.well-known/security.txt` (RFC 9116).

---

## Scope

| Component | What it is | Data it holds |
|---|---|---|
| **tacedata.ca** | Hugo static site — S3 behind CloudFront | Public content only |
| **Econ dashboard** | Static page + scheduled Lambda writing a public JSON feed; DynamoDB history; SNS email alerts | Public market data; one alert subscriber |
| **Training tracker** (train.tacedata.ca) | SPA + Cognito sign-in + HTTP API Lambdas + DynamoDB + daily email Lambda | Personal training plan, completion state, free-text notes, coach conversations |
| **AI coach** | Lambda calling the Anthropic API, grounded on the caller's own plan data | Conversation history (per user) |
| **CI/CD** | GitHub Actions deploying via OIDC | No stored cloud credentials |

The tracker and coach are the only components holding personal data. They are single-user today
(allowlisted owner); multi-user is designed for but deferred.

---

## Security Mechanisms

### 1. Public repository hygiene

- **Status:** Implemented Stage 1.7 (v0.15.0, 2026-04-04); extended v3.2.1 (2026-08-31).
- **Why:** The repository is public. AWS identifiers are not secrets, but they remove reconnaissance
  work for an attacker and tie configuration to a specific account.
- **How:** All config snapshots and policies in `config/` and `app/*/config/` use placeholders
  (`<AWS_ACCOUNT_ID>`, `<S3_BUCKET_NAME>`, ...). Real values live in a separate private repository.
  Git history was rewritten (46 commits, `git-filter-repo`) to remove identifiers committed before
  this rule existed; stale tags pointing at pre-scrub commits were force-updated in v3.2.1. Detailed
  security review reports are git-ignored (`*-Security-Review.md`) and kept private.
- **Contract:** No commit, tag or commit message on `main` contains an account ID, distribution ID,
  bucket name, role ARN, Cognito pool/client name, or API hostname. Every infrastructure change
  writes the real-values version privately and a placeholder version here.

### 2. CI/CD identity and deploy integrity

- **Status:** OIDC since Stage 1.3; branch protection v0.16.0; test gate v3.4.0.
- **Why:** Long-lived cloud keys in CI are the most common way a public repo leaks account access.
- **How:**
  - GitHub Actions assumes an AWS role via OIDC. The role trust policy requires audience
    `sts.amazonaws.com` **and** subject `repo:scottyleblanc/TACE.Website:ref:refs/heads/main` —
    only workflows on `main` of this repository can assume it.
  - The deploy role is least-privilege: `PutObject`/`DeleteObject` on the site prefix only,
    `ListBucket` on the one bucket, `CreateInvalidation` on the one distribution,
    `UpdateFunctionCode` on the econ Lambda only.
  - Workflows declare `permissions: id-token: write, contents: read`.
  - Branch protection on `main` blocks force pushes and deletion.
  - Dependabot raises weekly updates for GitHub Actions and the theme submodule.
  - Since v3.4.0 the econ test suite runs before any deploy step; a failing test blocks the release.
  - The coach-evals workflow is the only one holding an API secret (Anthropic). It runs on
    `pull_request` (paths-filtered) and manual dispatch, has no AWS access, and GitHub does not pass
    repository secrets to pull requests from forks.
- **Contract:** No cloud credential is stored in the repository or as a long-lived CI secret. A
  workflow on any branch other than `main`, or in a fork, cannot obtain AWS credentials.

### 3. Static site edge (tacedata.ca)

- **Status:** Implemented Stage 1.3 / 1.7.
- **Why:** Prevent direct bucket access, enforce HTTPS, and limit what injected content could do.
- **How:**
  - The S3 bucket is private. The bucket policy grants `s3:GetObject` only to the CloudFront
    service principal, conditioned on `AWS:SourceArn` matching this site's distribution (OAC).
  - TLS via ACM on CloudFront; HSTS `max-age=31536000; includeSubDomains`.
  - A CloudFront Function (`config/security-headers.js`, viewer-response) sets CSP,
    `X-Frame-Options: SAMEORIGIN`, `X-Content-Type-Options: nosniff` and
    `Referrer-Policy: strict-origin-when-cross-origin`. `config/response-headers-policy.json`
    is a reference only and is **not attached** (it conflicted with the WAF configuration).
  - A CloudFront WAF is attached; it rejects requests with no User-Agent (verified 2026-11-11).
- **Contract:** Content is reachable only through CloudFront over HTTPS, and every response carries
  the headers above. The current CSP is permissive — see open items.

### 4. Econ data pipeline

- **Status:** Implemented Stages 2.3–2.6; hardened v3.4.0.
- **Why:** The feed (`/data/indicators.json`) is public and is read by anyone; the Lambda holds two
  third-party API keys.
- **How:**
  - The Lambda's role can write only the site's `data/` prefix, `PutItem`/`Query` its one history
    table, publish to its one SNS topic, and write its own log group.
  - The feed contains only public market data. When a source fails, the public `errors` value is a
    fixed `"source unavailable"`; upstream exception text (URLs, API error bodies) goes to CloudWatch
    only (v3.4.0, R6). Tests assert that neither API key nor upstream error text can reach the payload.
  - The deploy S3 sync excludes `data/*`, so a site deploy can never overwrite or delete the feed.
  - Bulk history repairs are dry-run by default and write a backup of original values before
    changing anything (`scripts/fix_boc_history.py`).
- **Contract:** Nothing in `indicators.json` or the history files is sensitive on any code path,
  including failure paths.

### 5. Tracker identity and session handling

- **Status:** Implemented Stage 3.x (identity foundation).
- **Why:** The tracker holds personal data; tokens in browser storage are readable by any script
  that runs on the page.
- **How:**
  - Sign-in goes through the Cognito Hosted UI. A Cognito pre-token-generation trigger
    (`auth_guard.py`) rejects any account whose email is not on the allowlist **before** tokens are
    issued; self sign-up is closed.
  - A backend-for-frontend Lambda (`tracker_auth.py`) runs the OAuth2 Authorization Code flow
    with PKCE (S256) entirely server-side. The PKCE verifier and `state` travel in a short-lived
    (10 min) `HttpOnly; Secure; SameSite=Lax` cookie; `state` is compared in constant time.
  - The refresh token is held only in `__Secure-trk_rt` — `HttpOnly; Secure; SameSite=Strict;
    Path=/auth`. Browser JavaScript can never read it. The SPA keeps the short-lived access token in
    memory only and re-mints it via `POST /auth/refresh`.
  - `/auth/refresh` rejects any request whose `Origin` header is present and not the app origin
    (CSRF defence in depth on top of `SameSite=Strict`). Refresh-token rotation is honoured.
  - Auth responses are `Cache-Control: no-store`. No token, code or verifier is written to logs.
- **Contract:** No credential is ever in `localStorage`, `sessionStorage` or a JS-readable cookie.
  An account not on the allowlist never receives a token.

### 6. Tracker API authorisation and data isolation

- **Status:** Implemented v3.1.0 (Stages 3.9–3.12); verified against a second real identity.
- **Why:** Every record is personal; the design must hold when a second user is added.
- **How:**
  - Every data route (`/days`, `/settings`, `/conversations`) sits behind an API Gateway Cognito
    JWT authorizer. Only the `/auth/*` routes of mechanism 5 are unauthenticated, by design.
  - Handlers take `user_id` only from the verified token's `sub` claim — never from the body, path
    or query string. Every table is partitioned on `user_id`, so every read and write is keyed to the
    caller.
  - Access to another user's item returns **404**, not 403, so existence is not disclosed. Verified
    with a second Cognito identity for `GET`/`PATCH /days` and every conversation verb; the owner's
    data was confirmed unchanged afterwards.
  - The overrides table was migrated from global, un-partitioned data to a `user_id`-partitioned
    table queried per caller (previously any caller could see another user's physio overrides).
  - CORS allows only `https://train.tacedata.ca`. Inputs are length-capped (notes 2,000 chars,
    coach messages 4,000, titles 200).
  - The tracker site sends a strict CSP (`script-src 'self'`, `frame-ancestors 'none'`,
    `object-src 'none'`, `base-uri 'none'`, `connect-src` limited to its API and auth hosts),
    HSTS with preload, `X-Frame-Options: DENY` and a restrictive `Permissions-Policy`.
  - SPA values rendered via `innerHTML` pass through an `esc()` HTML-escaping helper.
- **Contract:** A valid token for user B can never read, modify or reveal the existence of
  user A's data.

### 7. AI coach

- **Status:** Implemented Stages 3.10–3.16 (v3.1.0–v3.2.0).
- **Why:** The coach sends personal data to a third-party model, reads user-written notes that could
  carry prompt injection, and must not give medical advice.
- **How:**
  - The Anthropic API key is stored in AWS Secrets Manager, read server-side and cached at module
    scope. It is never in an environment variable in plaintext, never in the browser, and never in a
    response or log `message`.
  - The coach is grounded only on the caller's own merged plan (same merge logic as the API), loaded
    by `user_id` from the token.
  - A separate classifier ("medical rail") runs before the coach. If it flags an injury or medical
    question, a fixed deferral is stored and the coach model is never called. The rail **fails
    closed**: a classifier error or ambiguous result is treated as medical.
  - User notes are passed inside delimited `[PLAN_DATA]` / `[NOTES_LOG]` blocks, and the system
    prompt declares them data, never instructions (the notes-injection boundary).
  - Release gates in the eval harness: 100% recall on medical cases, no fabricated facts, correct
    scope, and notes-injection must not change role or output. Runs in CI on every prompt change.
  - Output is capped by `MAX_TOKENS`; history is windowed.
- **Contract:** The coach answers only from the caller's data, defers every medical question, and
  cannot be re-tasked by text in a note.

### 8. Data-protection guards on maintenance scripts

- **Status:** v3.2.0–v3.4.0.
- **Why:** Most data loss here would come from the owner's own scripts, not an attacker.
- **How:** The seed script's `--preserve-state` skips any day with `completed` or `notes`. Block
  migration truncation refuses to delete such rows, with no `--force` override. Bulk writes are
  preceded by a backup. `Complete-TrainingDay.ps1` reads before writing and supports `-WhatIf`.
- **Contract:** No maintenance script can delete or overwrite a logged session or a note.

### 9. Client-side rendering (econ dashboard)

- **Status:** v3.4.0 (R10).
- **How:** The only user-entered content (the browser-local notes panel) is rendered with
  `textContent`. Feed values are written by the Lambda, not by users.

---

## Open items

Known gaps. Each is a real gap as of 2026-11-11; none is believed to be actively exploited.

| # | Severity | Item |
|---|---|---|
| O1 | LOW | **Main site CSP is permissive.** `script-src` allows `'unsafe-inline'` and the whole `cdn.jsdelivr.net` host (any package on it). No `frame-ancestors`, `object-src` or `base-uri` directives, no `Permissions-Policy`, and HSTS without `preload`. The tracker site already has a strict policy that can serve as the model. Needs a hash/nonce or self-hosting plan for the inline dashboard script and the Mermaid loader. |
| O2 | LOW | **Econ API keys (Twelve Data, FRED) are Lambda environment variables**, unlike the Anthropic key, which is in Secrets Manager. Both are free-tier, read-only market-data keys, but they are readable by anyone with `lambda:GetFunctionConfiguration`. |
| O3 | LOW | **No automated tests for the tracker Lambdas.** Authorisation, cross-user isolation and the cookie flow were verified by hand against real identities; nothing stops a regression from shipping. The econ suite and the coach eval gate show the pattern to follow. |
| O4 | LOW | **Published IAM policy snapshots are out of date.** `app/train/config/*-execution-policy.json` still describe the retired single-table design with `Scan` grants. The live policies (per-table `Query`, no `Scan`) are documented privately, but the public snapshots are wrong and should be refreshed with placeholders or removed. |
| O5 | LOW | **No API throttling configured on the tracker HTTP API.** It relies on API Gateway account defaults. Every coach call spends Anthropic credit; exposure is limited to allowlisted users today. |
| O6 | ADV | `auth_guard.py` puts the rejected email address in its exception message, so rejected sign-in attempts write a third party's email into CloudWatch. |
| O7 | ADV | **No WAF on the tracker distribution.** The main site has one. Cognito and the JWT authorizer carry access control there, so this is defence in depth only. |
| O8 | ADV | **The allowlist is a static environment variable.** An invited-emails store is planned before any second user (tracked as `[SEC]` in `app/train/docs/TODO.md`). |
| O9 | ADV | **Point-in-time recovery is disabled on the tracker plan table** — the owner's decision, since writes only happen during deliberate sessions. Bulk operations take a backup first instead. |
| O10 | ADV | **Lambda code signing is not configured.** Deploy integrity rests on OIDC plus branch protection. `security.txt` expires 2027-04-04 and must be renewed before then. |

---

## Audit record

Detailed reports are kept private. This is the public summary.

| Date | Version | Scope | Findings | Resolution |
|---|---|---|---|---|
| 2026-04-04 | v0.15.0–v0.16.0 | Stage 1.7 security review — repository and site | 2 HIGH, 2 MEDIUM, 2 LOW, 1 INFO | HIGH: identifiers scrubbed from current files; history rewritten (46 commits). MEDIUM: personal security-clearance disclosure removed from the contact page. LOW: MIT replaced with All Rights Reserved; security headers added via CloudFront Function. Also: branch protection on `main`, `security.txt` published, review reports git-ignored. The second MEDIUM and the INFO finding are not itemized publicly; see the private report. |
| 2026-07-05 | v3.1.0 | Tracker and coach hardening (Stages 3.9–3.14) | Cross-user isolation; un-partitioned overrides table exposing other users' data; unescaped `innerHTML` rendering; rail over-triggering | Key-level isolation verified with a second identity; overrides table re-partitioned; `esc()` helper; rail fails closed and judges intent, not topic. |
| 2026-08-31 | v3.2.0 | Block migration and coach history (Stages 3.15–3.16) | Destructive truncate path; notes-injection boundary not covering earlier blocks | Truncate refuses rows with `completed`/`notes`; injection boundary extended to `[NOTES_LOG]`. |
| 2026-08-31 | v3.2.1 | Public-repo identifier sweep | Two remote tags still pointed at pre-scrub commits; remaining bucket, Cognito and role names in seven files | Tags force-updated; identifiers replaced with placeholders. |
| 2026-09-14 | v3.3.0 | Seed script | `--preserve-state` could overwrite a noted-but-unchecked day | Now also skips days carrying `notes`; backup taken before the live write. |
| 2026-11-11 | v3.4.0 | Adversarial review — econ Lambda and dashboard | 12 (R1–R12): 2 HIGH, 3 MEDIUM, 7 LOW. `[SEC]`: R6 (upstream error text in public feed), R10 (notes `innerHTML`) | All resolved — see `docs/CHANGELOG.md` v3.4.0. |
| 2026-11-11 | v3.4.0 | Full-repository review for this document | 10 open items (5 LOW, 5 ADV) | Recorded as O1–O10 above. Also corrected this file's previous claim that the repo had "no user accounts, no database, and no server-side code". |

---

## Code signing guidance

The repository ships Python (Lambdas, scripts), JavaScript (SPA, dashboard, CloudFront Functions)
and one PowerShell script, `app/train/scripts/Complete-TrainingDay.ps1` (PowerShell 7,
`SupportsShouldProcess`), which the owner runs manually.

| Context | Runs PowerShell? | Minimum execution policy |
|---|---|---|
| Owner workstation, script from this clone | Yes | `RemoteSigned` — a locally created file runs unsigned |
| Script downloaded or copied from elsewhere (carries Mark-of-the-Web) | Yes | `RemoteSigned` requires it to be signed, or unblock it after review |
| Locked-down host (`AllSigned`) | Yes | Script must be Authenticode-signed |
| GitHub Actions | No | n/a |
| AWS Lambda | No | n/a — integrity via OIDC deploy (see O10) |

**Files to sign** if the script is distributed or run under `AllSigned`:
`app/train/scripts/Complete-TrainingDay.ps1`.

**Signing procedure:**

```powershell
$cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert | Select-Object -First 1
$params = @{
    FilePath        = 'app/train/scripts/Complete-TrainingDay.ps1'
    Certificate     = $cert
    TimestampServer = 'http://timestamp.digicert.com'
    HashAlgorithm   = 'SHA256'
}
Set-AuthenticodeSignature @params
Get-AuthenticodeSignature -FilePath $params.FilePath   # Status must be Valid
```

Re-sign after every edit — any change invalidates the signature. Lambda deployment packages are not
signed. If AWS Signer code signing is adopted (O10), the deploy step would sign the zip and the
function's code-signing config would reject unsigned code.

---

## License

All content and code in this repository is proprietary.
Copyright © 2026 TACE Data Management Inc. All rights reserved.
