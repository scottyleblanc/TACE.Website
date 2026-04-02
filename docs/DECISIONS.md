# DECISIONS.md — tacedata-site

Records decisions made during the build. Each entry includes the decision,
the date, the options considered, and the rationale.

---

## Theme Selection

**Decision:** Blowfish
**Date:** 2026-03-22
**Status:** Active

### Options Evaluated

| Theme | Outcome |
|-------|---------|
| PaperMod | Evaluated — clean, works well, dark/light toggle, good nav. Liked it. |
| Congo | Evaluated — incompatible with Hugo 0.158 on stable branch; build errors not resolved. Abandoned. |
| Blowfish | Selected — preferred structure and layout over PaperMod; built cleanly; logo integration working. |
| Custom theme | Considered and rejected — weeks of work with no content value for this site's purpose. |

### Rationale

- Blowfish built cleanly with no errors on Hugo Extended v0.158
- Layout and structure preferred over PaperMod after side-by-side comparison
- Logo (PNG, transparent background) integrates cleanly via `assets/img/`
- Color scheme customization is straightforward via CSS variables
- Dark/light mode built in
- Content (Markdown) is fully portable if theme is ever switched
- Theme is not the value of this site — content is; Blowfish gets out of the way

### Configuration Notes

- Theme added as git submodule: `themes/blowfish`
- Config split across `config/_default/params.toml` and `config/_default/menus.toml`
- Logo at `assets/img/logo.png`; referenced via `logo = "img/logo.png"` in `params.toml`
- Color scheme: `ocean` (to be revisited — teal accent to match logo)
- Never edit files inside `themes/blowfish/` — all overrides go in `layouts/`, `assets/`, `config/`

---

## Hosting Target

**Decision:** AWS direct — S3 + CloudFront + GitHub Actions + Lambda + Cognito
**Date:** 2026-04-01
**Status:** Active

### Architecture Discovery

The site has two distinct layers that change the hosting decision significantly:

**Layer 1 — Static content (Hugo output)**
- Home, About, Blog, Projects, Skills sections
- Served as static files — any host handles this identically

**Layer 2 — Utilities (web applications)**
- Pages that pull data from external sources and present summaries
- Some pages will require user authentication (username/password access control)
- Authentication cannot be done on a static host — eliminates GitHub Pages entirely
- Requires serverless functions (Lambda or equivalent) for backend logic and API key protection

### Options Analysis

| Option | Static content | Utilities with auth | AWS migration path | Verdict |
|---|---|---|---|---|
| GitHub Pages | Yes | No — incapable | Full rebuild required | Eliminated |
| Netlify | Yes | Yes (Netlify Identity + Functions) | Static migrates cleanly; Functions need rewriting | Viable bridge |
| AWS (S3 + CloudFront + Lambda + Cognito) | Yes | Yes — native | No migration needed | Right long-term answer |

### AWS Cost at Personal Site Scale

| Service | Cost |
|---|---|
| S3 + CloudFront | ~$0-2/month |
| Route 53 (hosted zone) | $0.50/month |
| Lambda + API Gateway | Free tier — effectively $0 at personal scale |
| Cognito (auth) | Free tier — 50,000 MAUs |
| **Total** | **~$1-5/month after free tier; ~$0.50/month in first 12 months** |

### DNS: Delegation vs. Transfer

These are independent operations — do not conflate them:

- **Delegate DNS to Route 53** — keep Websavers as registrar, change nameservers only. 15-20 minutes of work. This is what the AWS cutover actually requires.
- **Transfer domain registration to Route 53** — Websavers exits entirely. 30 minutes of work spread over 5-7 days (ICANN transfer window). Optional and separate from DNS delegation.

Recommended sequence: delegate DNS first, confirm everything works, then optionally transfer registration.

### Recommended Sequencing

**Option A — Netlify first, AWS later:**
Get the static site live on Netlify quickly (hits the Websavers deadline with minimal risk), then migrate to AWS when building the first utility. Migration of static content is low-risk (Hugo output is just files). Netlify Functions need a rewrite when moving to Lambda — known, acceptable cost.

**Option B — AWS from day one:**
Front-load the setup cost once. S3 + CloudFront pipeline becomes a portfolio piece immediately. No migration needed when utilities are built. Adds a few hours of setup vs. Netlify.

**Decision:** AWS direct from day one.

Rationale:
- Netlify-first creates a guaranteed migration and pipeline rebuild later — pay the cost twice
- AWS setup cost is a few hours, paid once, and the pipeline itself is a portfolio piece
- Lambda + Cognito are in place when utilities are built — no rework
- AWS account is already active (used for OracleAwsRotation); free tier has expired
- Confirmed ongoing cost: ~$0.50-5/month — acceptable

**Netlify is not on the path.** GitHub Pages was eliminated earlier (no auth capability).

### AWS stack

| Layer | Service | Purpose | Stage |
|---|---|---|---|
| Static hosting | S3 + CloudFront | Serve Hugo output | Stage 2 |
| Deploy pipeline | GitHub Actions → S3 | Push to main triggers build and deploy | Stage 2 |
| DNS | Route 53 | Authoritative DNS for tacedata.ca | Stage 3 |
| SSL | ACM | Free cert, attached to CloudFront | Stage 3 |
| Utility backend | Lambda + API Gateway | Serverless functions for data fetching | Future |
| Auth | Cognito | User pool for gated utility pages | Future |

### Cost (free tier expired, personal site scale)

| Item | Monthly cost |
|---|---|
| Route 53 hosted zone | ~$0.50 USD |
| S3 + CloudFront | ~$0.02 USD |
| Lambda + Cognito | ~$0 (permanent free tier) |
| API Gateway (utilities, low traffic) | ~$0-1 USD |
| **Total** | **~$1-5 USD/month** |

---

## Site Structure

**Decision:** Confirmed
**Date:** 2026-03-29
**Status:** Active

URL structure and section definitions:

```
tacedata.ca/
├── /                    — Home
├── /blog/               — Blog posts
├── /projects/           — Project write-ups (OracleAwsRotation first)
├── /skills/
│   ├── /skills/oracle/
│   └── /skills/powershell/
└── /utilities/
    ├── /utilities/economy-dashboard/
    └── /utilities/[tbd]/
```

Static sections (home, blog, projects, skills) are Hugo content — Markdown files, built and served as static HTML.

Utilities section is a different layer — data aggregation from external sources, some pages gated with user authentication. Maps to Lambda + API Gateway + Cognito on AWS.

---

## Email Hosting

**Decision:** Pending
**Date:** —
**Status:** Open — must be decided before July 14, 2026

### Constraints (from Websavers review)

- 3 email addresses in use: personal, accounting, contact — all hosted on Websavers
- Inbox history exists on all three and should be preserved
- **IMAP export required before cutover** — do not cancel Websavers email until confirmed complete
- Thunderbird is the standard tool for IMAP-to-local export

### Email model (confirmed)

Accounting and contact addresses are aliases forwarding to the personal inbox — that is the current Websavers setup and the preferred model going forward. No separate inboxes required.

This means **Zoho Mail free tier is viable**: 1 user, up to 30 aliases, covers all three addresses.

### Inbox history migration

Nice-to-have, not a hard requirement. Attempt IMAP export via Thunderbird if it fits into the migration window — but do not block the cutover on it.

### Options

| Option | Cost | Aliases | Inbox import | Verdict |
|---|---|---|---|---|
| Fastmail | ~$5/mo CAD | Yes | Yes (IMAP) | **Preferred** |
| Zoho Mail (free) | Free | Yes (up to 30) | Yes (IMAP, best-effort) | Viable fallback |
| Google Workspace | ~$8/mo CAD | Yes | Yes (migration tool) | Overbuilt for this use case |

### Domains decision (related)

5 defensive registrations at ~$25 CAD/year each (~$125 CAD/year total).
Will keep a minimum of 3, possibly more. Exact list TBD — confirm variants in Websavers dashboard and decide before renewal.
Route 53 costs ~$14 CAD/year per `.ca` domain — keeping 3 saves ~$33 CAD/year vs. Websavers.
