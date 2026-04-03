# CHANGELOG — tacedata-site

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

## [0.13.0] - 2026-04-03

### Added
- Route 53 hosted zone `REDACTED_R53_ZONE_ID` — authoritative DNS for tacedata.ca
- DNS records in Route 53: MX (Fastmail), SPF, DMARC, DKIM CNAMEs, www CNAME to CloudFront
- ACM certificate issued for tacedata.ca and www.tacedata.ca (us-east-1, DNS validation)
- CloudFront distribution updated: alternate domain names tacedata.ca / www.tacedata.ca, ACM cert attached, SNI-only, TLSv1.2_2021
- Route 53 A alias record for tacedata.ca root pointing to CloudFront
- `config/route53-records.json` — initial DNS records batch file
- `config/route53-acm-validation.json` — ACM DNS validation CNAME records
- `config/route53-alias.json` — A alias record for root domain
- `config/dist-config-live.json` — CloudFront distribution config with aliases and ACM cert
- `config/runbook-stage5-dns-cutover.md` — full cutover runbook with architecture diagram
- Blog posts (draft): Stage 1–5 write-ups — hugo-evaluation, email-migration, aws-pipeline, site-content, dns-cutover

### Changed
- Nameservers at Websavers changed to Route 53 NS records — Route 53 is now authoritative
- `SITE_URL` GitHub Actions variable updated from CloudFront URL to `https://tacedata.ca`
- `docs/STAGES.md` — Stage 4 moved to correct position, marked complete; current stage updated to Stage 5

### Fixed
- `docs/STAGES.md` — Stage 4 was out of order (appeared after Stage 5); corrected

## [0.12.0] - 2026-04-03

### Added
- PaperMod theme added as git submodule; Blowfish retired
- Mermaid diagram support via render hook (`layouts/_default/_markup/render-codeblock-mermaid.html`) and unconditional JS loader in `extend_footer.html`
- Economy dashboard deployed as static HTML at `/ai/projects/econ/`
- Contact page (`content/contact.md`) published
- CloudFront Function `rewrite-index-html` (cloudfront-js-1.0) — rewrites directory-style URLs to `index.html` paths; required for Hugo static output served via S3 OAC
- `config/rewrite-index-html.js`, `config/dist-config.json`, `config/dist-config-updated.json` — function source and distribution config snapshots

### Changed
- `hugo.toml` baseURL removed from source; replaced with `vars.SITE_URL` GitHub Actions variable — site renders correctly at CloudFront URL before domain cutover; update variable at Stage 5
- Menus: removed Evolution and AI Perspective (no content); Contact retained
- `draft: true` removed from contact, Hello World post, oracle-aws-rotation project, sample project, sample post — all now deploy to production

### Fixed
- All subpath navigation returned AccessDenied (S3 OAC does not resolve directory index without rewrite); fixed with CloudFront Function
- Site CSS and JS not loading at CloudFront URL due to hardcoded tacedata.ca baseURL

---

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
