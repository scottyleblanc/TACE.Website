# CHANGELOG — tacedata-site

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

## [0.11.0] - 2026-04-02

### Changed
- Stages renumbered: Content promoted to Stage 4; Domain Cutover moved to Stage 5
- Rationale: site needs representative content before going live on tacedata.ca

---

## [0.10.0] - 2026-04-02

### Added
- Stage 3 AWS pipeline complete
- S3 bucket `REDACTED_S3_BUCKET/tacedata-site/` configured with CloudFront OAC bucket policy
- CloudFront distribution `REDACTED_CF_DIST_ID` — `REDACTED_CF_DOMAIN`
- IAM OIDC provider for GitHub Actions (`token.actions.githubusercontent.com`)
- IAM role `REDACTED_DEPLOY_ROLE` — least-privilege, scoped to this repo and distribution
- GitHub Actions workflow: push to main → hugo build → S3 sync → CloudFront invalidation
- Round-trip validated: change live on CloudFront URL within 2 minutes of push
- Config files: `config/s3.bucket.policy.json`, `config/iam-trust-policy.json`, `config/iam-permissions-policy.json`
- `config/runbook-stage3-aws.md` — full AWS infrastructure setup commands and resource reference
- `README.md` — updated with stack, pipeline, AWS resources, and repo structure

---

## [0.9.0] - 2026-04-01

### Added
- Stage 2 email migration complete — Fastmail active for tacedata.ca
- MX, DKIM (3 CNAME records), and SPF records updated in Websavers DNS
- accounting@tacedata.ca and contact@tacedata.ca configured as aliases to scott.leblanc@tacedata.ca
- All 3 addresses validated receiving email on Fastmail
- Inbox history imported from Websavers via Fastmail built-in IMAP import

---

## [0.8.0] - 2026-04-01

### Changed
- Stages renumbered: Email Migration inserted as Stage 2; pipeline promoted to Stage 3; domain cutover promoted to Stage 4; content promoted to Stage 5
- Rationale: email must be functional on new provider before Stage 4 DNS and ACM work, which triggers validation emails
- `docs/TODO.md` — full rewrite with new stage numbers and email migration tasks as Stage 2
- `docs/STAGES.md` — full rewrite with new stage numbers; Stage 2 rationale documented
- `docs/DECISIONS.md` — AWS stack table stage column updated (Stage 3/4 instead of Stage 2/3)

---

## [0.7.0] - 2026-04-01

### Changed
- `docs/STAGES.md` — Stage 2: rewritten to reflect AWS decision, Websavers untouched, test on CloudFront URL
- `docs/STAGES.md` — Stage 3: Websavers review complete, cutover sequence documented with email DNS note, email and domain decisions recorded
- `docs/DECISIONS.md` — AWS stack table: stage column added; ACM and Route 53 correctly placed in Stage 3, not Stage 2

---

## [0.6.0] - 2026-04-01

### Changed
- `docs/DECISIONS.md` — Hosting Target: decision made — AWS direct (S3 + CloudFront + GitHub Actions + Lambda + Cognito); Netlify path closed; cost confirmed at ~$1-5 USD/month
- `docs/TODO.md` — Stage 2 replanned with concrete AWS infrastructure and pipeline tasks

---

## [0.5.0] - 2026-03-29

### Changed
- `docs/DECISIONS.md` — Email Hosting: aliases confirmed as the model, Fastmail identified as preferred provider, Zoho free tier as viable fallback, inbox migration downgraded to nice-to-have
- `docs/TODO.md` — Stage 3: domain count set at minimum 3, email migration tasks simplified
- `docs/websavers.md` — Open decisions updated to reflect clarifications

---

## [0.4.0] - 2026-03-29

### Added
- `docs/websavers.md` — findings recorded: renewal July 14 2026, 5 domains at ~$25 CAD each, 3 email addresses with inbox history, hosting bundled free

### Changed
- `docs/DECISIONS.md` — Email Hosting: constraints documented (IMAP export required, aliases vs. inboxes decision needed, domains cost comparison added)
- `docs/TODO.md` — Stage 3 fully replanned: email migration sequence, domain decisions, DNS cutover steps, hard deadline explicit

---

## [0.3.0] - 2026-03-29

### Added
- `docs/websavers.md` — account review checklist; must be completed before Stage 3 decisions
- `docs/DECISIONS.md` — Hosting Target: full architecture analysis, AWS cost breakdown, DNS delegation vs. transfer distinction, sequencing options
- `docs/DECISIONS.md` — Site Structure: confirmed URL structure and two-layer architecture (static Hugo + utilities with auth)
- `docs/DECISIONS.md` — Email Hosting: blocked on Websavers review, options documented

### Changed
- `docs/TODO.md` — Stage 2 updated: GitHub Pages eliminated, hosting decision reframed around architecture discovery
- `docs/TODO.md` — Stage 3 updated: Websavers review as prerequisite, DNS delegation and transfer treated as separate operations
- `docs/TODO.md` — Stage 4 updated: site structure confirmed, utilities section added
- `docs/STAGES.md` — Stage 2 updated: hosting analysis summarized, rationale for eliminating GitHub Pages documented
- `docs/STAGES.md` — Stage 3 updated: DNS approach clarified, email decision noted as blocked

---

## [0.2.0] - 2026-03-29

### Changed
- Stage 1 closed out — Hugo evaluation complete, Blowfish theme confirmed

### Fixed
- Removed `hugo-eval/themes/tacedata/` evaluation scaffold (not a submodule, not a theme — leftover from Congo/custom theme evaluation)

---

## [0.1.0] - 2026-03-22

### Added
- Hugo Extended v0.158 confirmed installed locally
- `hugo-eval/` workspace initialized with `hugo new site . --force`
- Blowfish theme added as git submodule (`themes/blowfish`)
- `hugo.toml` configured: baseURL, languageCode, title, theme
- `config/_default/params.toml` — color scheme, appearance, header, homepage layout, author block
- `config/_default/menus.toml` — four nav items: Projects, Blog, Evolution, AI Perspective
- `config/_default/languages.en.toml` — language and author configuration
- Logo (PNG, transparent background) at `assets/img/logo.png` and `static/logo.png`
- Sample blog post: "Rotating Oracle Credentials with AWS Secrets Manager"
- Sample project page: "OracleAwsRotation"
- `content/_index.md` — home page stub
- `docs/DECISIONS.md` — theme selection recorded with rationale
- `docs/CHANGELOG.md` — this file

### Evaluated and Rejected
- PaperMod — evaluated, liked, not selected (Blowfish preferred on structure)
- Congo — build errors on Hugo 0.158; abandoned
- Custom theme — rejected; content is the value, not the theme
