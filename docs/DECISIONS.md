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

**Decision:** Pending — analysis complete, final call deferred
**Date:** 2026-03-29
**Status:** Open — see analysis below

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

**Decision pending:** AWS timeline is "definitely, when further down the cert path." Final hosting call deferred until Websavers account details are reviewed — see `docs/websavers.md`.

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

### Aliases vs. separate inboxes

The accounting and contact addresses are the deciding factor on cost:

- **If aliases are acceptable** (accounting and contact forward to personal inbox): Zoho Mail free tier works — 1 user, up to 30 aliases
- **If separate inboxes with independent history are needed**: Zoho free tier is insufficient; Fastmail or Google Workspace required

### Options

| Option | Cost | Inbox import | Multiple addresses | Notes |
|---|---|---|---|---|
| Zoho Mail (free) | Free | Yes (IMAP) | Aliases only on free tier | Good enough if aliases acceptable |
| Fastmail | ~$5/mo CAD | Yes (IMAP) | Aliases per account | Clean, privacy-focused |
| Google Workspace | ~$8/mo CAD | Yes (migration tool) | Aliases per user | Best tooling; higher cost |

### Domains decision (related)

5 domain variants registered at ~$25 CAD/year each (~$125 CAD/year total).
Must decide which to transfer to Route 53 and which to let lapse at renewal.
At minimum `tacedata.ca` transfers. Route 53 costs ~$14 CAD/year per .ca domain.
