# STAGES — tacedata-site

Phase definitions, current state, and decision criteria.

---

## Current Stage: Stage 4 — Content

---

## Stage 1 — Hugo Evaluation (Complete — 2026-03-29)

**Goal:** Validate that Hugo + Git + CI/CD is the right workflow before committing
to a full migration away from WordPress/Websavers.

**Definition of done:** All items met.
- Hugo Extended v0.158 installed locally
- `hugo-eval/` initialized, Blowfish theme as git submodule (v2.100.0)
- PaperMod, Congo, and Blowfish evaluated; Blowfish selected (see `docs/DECISIONS.md`)
- Sample blog post and project page rendering correctly
- Local workflow confirmed: edit Markdown → `hugo server` → view result
- Theme decision documented in `docs/DECISIONS.md` with full rationale
- `.gitignore` confirmed: `hugo-eval/public/`, `hugo-eval/resources/`, `.hugo_build.lock` excluded

---

## Stage 2 — Email Migration (Complete — 2026-04-01)

**Goal:** Email for tacedata.ca fully operational on Fastmail before any DNS work begins.

**Rationale:** Route 53 and ACM setup in Stage 4 will trigger credential and validation
emails. Those must land in a known-working inbox on the new provider, not Websavers.
Email migration is independent of the pipeline — no AWS work required.

**Websavers:** DNS nameservers untouched. Only MX records and a TXT verification record
are added/changed within Websavers DNS — the website continues serving WordPress unchanged.

**Definition of done:** All items met.
- Fastmail account active; tacedata.ca verified as custom domain
- MX, DKIM (3 CNAME records), and SPF records updated in Websavers DNS
- Accounting and contact addresses configured as aliases to personal inbox
- All 3 addresses confirmed receiving email on Fastmail
- Inbox history imported via Fastmail built-in IMAP import

---

## Stage 3 — AWS Pipeline (Complete — 2026-04-02)

**Goal:** Hugo site building and deploying automatically to AWS on every push to main.
Site validates on a CloudFront test URL — no domain cutover in this stage.

**Hosting decision:** AWS direct — S3 + CloudFront + GitHub Actions. See `docs/DECISIONS.md`.

**Websavers:** untouched in this stage. tacedata.ca continues serving WordPress.

**Definition of done:**
- S3 bucket and CloudFront distribution provisioned
- IAM role created for GitHub Actions (least-privilege: S3 sync + CloudFront invalidation only)
- OIDC trust configured between GitHub Actions and AWS (no long-lived credentials)
- GitHub Actions workflow: push to main → hugo build → `aws s3 sync` → CloudFront invalidation
- Round-trip validated on `*.cloudfront.net` test URL: local edit → commit → push → live within 2 minutes
- Pipeline documented in README.md

---

## Stage 5 — Domain Cutover

**Goal:** tacedata.ca pointing at CloudFront. Websavers wound down.

**Hard deadline:** July 14, 2026.

**Prerequisite:** Stage 4 (content) must be complete before this stage begins.

**Cutover sequence:**
1. Create Route 53 hosted zone; replicate all existing DNS records (including Fastmail MX records)
2. Request ACM certificate for tacedata.ca — DNS validation via Route 53 (auto-created record)
3. Attach tacedata.ca and ACM cert to the CloudFront distribution from Stage 3
4. Change nameservers at Websavers → Route 53 (~15-20 min) — first Websavers interaction
5. Validate tacedata.ca resolves correctly and SSL is clean
6. Confirm email still works on Fastmail after nameserver change
7. Cancel Websavers WordPress hosting and email
8. Release registrar lock; initiate domain transfer to Route 53 (5-7 day ICANN window)
9. Confirm transfers complete; Websavers fully wound down

**Domains:** 5 registered at Websavers (~$25 CAD/year each). Keep minimum 3; let remainder lapse.
Exact variants to confirm in Websavers dashboard before renewal.

---

## Stage 4 — Content

**Goal:** Site has enough real content to be worth sharing. Not "complete" — just
representative of the work and the journey.

**Minimum viable content at launch:**
- Home — one clear sentence on what this site is
- About — who I am, the evolution from DBA to automation engineer, the intent
- Projects — at least one write-up (OracleAwsRotation is the natural first)
- Blog — at least one post published

**Project write-up format (proposed):**
- What problem this solves
- Architecture diagram (exported from draw.io or similar)
- Tech used
- What I learned / what I'd do differently
- Link to GitHub repo (if public)

**Blog post candidate topics:**
- Why I moved from WordPress to Hugo (meta, but useful and honest)
- How I use AI as an engineering partner — what works, what doesn't
- What credential rotation actually involves (DBA perspective, no AWS assumed)
- First impressions of AWS from an on-prem Oracle DBA

**LinkedIn publishing workflow (proposed):**
- Write post in Hugo as normal Markdown
- Publish to site via normal pipeline
- Paste adapted version into LinkedIn as article or long-form post
- Link back to tacedata.ca for full version
- No tooling required to start — manual is fine until cadence is established

---

## Completed Stages

- Stage 1 — Hugo Evaluation — complete 2026-03-29
- Stage 2 — Email Migration — complete 2026-04-01
- Stage 3 — AWS Pipeline — complete 2026-04-02

---

## Parking Lot

Items not yet assigned to a stage:

- AWS certification path and how it shapes site content
- Contact page
- Analytics (Plausible, Fathom, or none — avoid Google Analytics)
- Whether repo goes public immediately or after initial content is in place
