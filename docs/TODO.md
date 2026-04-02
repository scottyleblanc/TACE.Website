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

## Stage 2 — Email Migration (Current)

- [x] Create Fastmail account; add tacedata.ca as custom domain (scott.leblanc@tacedata.ca)
- [x] Add Fastmail TXT record to Websavers DNS for domain verification
- [x] Configure accounting and contact as aliases forwarding to personal address
- [x] Import inbox history from Websavers via Fastmail's built-in IMAP import
- [x] Change MX records at Websavers to Fastmail mail servers
- [x] Validate all 3 addresses receive email correctly on Fastmail

---

## Stage 3 — AWS Pipeline (Complete)

- [x] Create S3 bucket for Hugo output (private, CloudFront access only) — REDACTED_S3_BUCKET/tacedata-site/
- [x] Create CloudFront distribution pointing at S3 bucket — REDACTED_CF_DOMAIN
- [x] Create IAM role for GitHub Actions deployment — REDACTED_DEPLOY_ROLE (least-privilege)
- [x] Configure OIDC trust between GitHub Actions and AWS (no long-lived credentials)
- [x] Write workflow: push to main → hugo build → `aws s3 sync` → CloudFront invalidation
- [x] Store AWS role ARN as GitHub Actions secret
- [x] Validate round-trip: local edit → commit → push → live within 2 minutes
- [x] Document pipeline in README.md

---

## Stage 4 — Domain Cutover (Pending Stage 3 complete)

**Hard deadline: July 14, 2026**

### Preparation (can start before Stage 3 is complete)

- [ ] Confirm the 5 domain variants in Websavers dashboard — decide which to keep (minimum 3)
    - Each kept domain: ~$14 CAD/year at Route 53 vs. ~$25 CAD/year at Websavers
    - Domains not kept: let lapse at July 14 renewal — do not renew

### Cutover

- [ ] Create Route 53 hosted zone for `tacedata.ca`
- [ ] Replicate all existing DNS records into Route 53 — including Fastmail MX records
- [ ] Request ACM certificate for tacedata.ca (DNS validation — Route 53 auto-creates the record)
- [ ] Attach tacedata.ca and ACM cert to the CloudFront distribution from Stage 3
- [ ] Change nameservers at Websavers → Route 53 (~15-20 min) — first Websavers interaction
- [ ] Validate tacedata.ca resolves correctly and SSL is clean
- [ ] Confirm email still works on Fastmail after nameserver change
- [ ] Cancel Websavers WordPress hosting and email
- [ ] Release registrar lock; initiate domain transfer to Route 53 (5-7 day ICANN window)
- [ ] Confirm transfers complete; Websavers relationship fully wound down

---

## Stage 5 — Content (Ongoing from Stage 1)

### Open

- [ ] Draft "About" content — who I am, the evolution, the intent of the site
- [ ] Write up first project — OracleAwsRotation (diagram + problem/solution write-up)
- [ ] Draft first blog post — candidate topics in STAGES.md
- [ ] Decide on AI perspective thread — format, cadence, tone
- [ ] Define LinkedIn publishing workflow — how posts get from blog to LinkedIn
- [ ] Flesh out Skills section — Oracle and PowerShell pages

### Site Structure (Confirmed — 2026-03-29)

- Home, Blog, Projects, Skills — static Hugo content
- Utilities — data aggregation pages, some with auth; see `docs/DECISIONS.md`
  - Economy Dashboard (first utility)
  - Additional utilities TBD

---

## Parking Lot — Not Yet Staged

- AWS certification path — which cert, timeline, how it integrates with site content
- Whether to make the GitHub repo public from the start or after initial content is in place
- Contact page — needed eventually, not urgent while not actively seeking clients
- Analytics — simple, privacy-respecting option (Plausible, Fathom, or none)
