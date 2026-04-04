# TODO — tacedata-site

Active build checklist. Items move to STAGES.md (complete section) when done.
Stages are defined in `docs/STAGES.md`.

---

## Stage 1 — Hugo Evaluation (Complete)

- [x] Install Hugo Extended locally (`winget install Hugo.Hugo.Extended`)
- [x] Run `hugo new site hugo-eval` to initialize site structure
- [x] Evaluate 2-3 themes — PaperMod, Congo, Blowfish; Blowfish selected
- [x] Create sample content — one post, one project page
- [x] Validate local workflow: edit Markdown → `hugo server` → view in browser
- [x] Commit hugo.toml and initial content to repo
- [x] Add `.gitignore` — exclude `hugo-eval/public/`, `hugo-eval/resources/`
- [x] Document theme decision in `docs/DECISIONS.md` with rationale
- [x] Confirm `hugo-eval/` structure matches intended production layout before graduating it

---

## Stage 2 — Email Migration (Complete)

- [x] Create Fastmail account; add tacedata.ca as custom domain (scott.leblanc@tacedata.ca)
- [x] Add Fastmail TXT record to Websavers DNS for domain verification
- [x] Configure accounting and contact as aliases forwarding to personal address
- [x] Import inbox history from Websavers via Fastmail's built-in IMAP import
- [x] Change MX records at Websavers to Fastmail mail servers
- [x] Validate all 3 addresses receive email correctly on Fastmail

---

## Stage 3 — AWS Pipeline (Complete)

- [x] Create S3 bucket for Hugo output (private, CloudFront access only) — <S3_BUCKET_NAME>/tacedata-site/
- [x] Create CloudFront distribution pointing at S3 bucket — <CLOUDFRONT_DOMAIN>
- [x] Create IAM role for GitHub Actions deployment — <DEPLOY_ROLE_NAME> (least-privilege)
- [x] Configure OIDC trust between GitHub Actions and AWS (no long-lived credentials)
- [x] Write workflow: push to main → hugo build → `aws s3 sync` → CloudFront invalidation
- [x] Store AWS role ARN as GitHub Actions secret
- [x] Validate round-trip: local edit → commit → push → live within 2 minutes
- [x] Document pipeline in README.md

---

## Stage 4 — Content (Complete — 2026-04-03)

- [x] Contact page published
- [x] Economy Dashboard deployed at `/ai/projects/econ/` (static HTML, no auth required)
- [x] Theme switched to PaperMod; Mermaid diagram rendering confirmed working
- [x] About page — TACE Data background, evolution from DBA to automation engineer
- [x] Home — profile mode with intro, buttons, social icons
- [x] Projects — tacedata.ca site write-up with architecture and deployment diagrams
- [x] Blog — "new digs" intro post published; Stage 1–5 write-up posts published

---

## Stage 5 — Domain Cutover (Complete — 2026-04-03)

- [x] Create Route 53 hosted zone for `tacedata.ca`
- [x] Replicate all existing DNS records into Route 53 — including Fastmail MX records
- [x] Request ACM certificate for tacedata.ca and www.tacedata.ca (DNS validation)
- [x] Add ACM validation CNAME records to Route 53
- [x] Change nameservers at Websavers → Route 53
- [x] Wait for ACM certificate to reach ISSUED status
- [x] Attach tacedata.ca / www.tacedata.ca and ACM cert to CloudFront distribution
- [x] Add A alias record for tacedata.ca root to Route 53
- [x] Update SITE_URL GitHub Actions variable to https://tacedata.ca
- [x] Trigger deploy; validate tacedata.ca loads with SSL
- [x] Confirm email still works on Fastmail after nameserver change

### Remaining (post-cutover)

- [ ] Confirm the 5 domain variants in Websavers dashboard — decide which to keep (minimum 3)
- [ ] Cancel Websavers WordPress hosting and email
- [ ] Optionally initiate domain transfer to Route 53 (5-7 day ICANN window)

---

## Post-Launch — Monitoring (Complete — 2026-04-03)

- [x] CloudWatch Synthetics canary — checks https://tacedata.ca every 5 minutes
- [x] CloudWatch Alarm — 2 consecutive failures triggers SNS email alert
- [x] IAM role for canary Lambda execution
- [x] Alarm tested — set-alarm-state confirmed email delivery on ALARM and OK
- [x] Blog post published: "site monitoring with aws cloudwatch"
- [x] Runbook documented: `config/runbook-cloudwatch-monitoring.md`

---

## Post-Launch — Security Remediation (Complete — 2026-04-04)

- [x] Security review conducted — 2 HIGH, 2 MEDIUM, 2 LOW, 1 INFO findings
- [x] [HIGH] Scrub AWS resource identifiers from current files
- [x] [HIGH] Rewrite git history (46 commits) — git-filter-repo, file content + commit messages
- [x] [MEDIUM] Remove security clearance disclosure from contact page
- [x] [LOW] Replace MIT license with All Rights Reserved
- [x] [LOW] Add security response headers via CloudFront Function (viewer-response)
  - CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy
  - Tested locally via hugo.toml dev server headers before production deploy
- [x] Blog post published: "cleaning sensitive data out of git history"

---

## Parking Lot — Open

- Confirm 5 domain variants in Websavers dashboard before July 14, 2026 — keep minimum 3, let remainder lapse
- Cancel Websavers WordPress hosting and email (after domain decision)
- AWS certification path — which cert, timeline, how it integrates with site content
- Analytics — simple, privacy-respecting option (Plausible, Fathom, or none)
