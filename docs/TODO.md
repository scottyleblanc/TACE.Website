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

## Stage 2 — CI/CD and Hosting (Current)

### Open

- [ ] Review Websavers account details — see `docs/websavers.md` for checklist
- [ ] Make final hosting decision: Netlify-first vs AWS direct — analysis in `docs/DECISIONS.md`
- [ ] Create GitHub Actions workflow: push to main → hugo build → deploy to chosen host
- [ ] Test full pipeline end-to-end on a non-production URL before pointing domain
- [ ] Document pipeline in README.md

---

## Stage 3 — Domain and Email Migration (Pending Stage 2 complete)

**Hard deadline: July 14, 2026**

### Decisions required (can be done in parallel with Stage 2)

- [ ] Decide which of the 5 domain variants to keep vs. let lapse at renewal
    - At minimum: `tacedata.ca` must be kept and transferred
    - Each kept domain: ~$14 CAD/year at Route 53 vs. ~$25 CAD/year at Websavers
- [ ] Decide accounting and contact email: separate inboxes or aliases to personal address?
    - Answer determines whether Zoho free tier is viable — see `docs/DECISIONS.md`
- [ ] Choose email provider: Zoho Mail (free), Fastmail (~$5/mo), Google Workspace (~$8/mo)

### Email migration (must complete before cancelling Websavers)

- [ ] Export all 3 inboxes via IMAP using Thunderbird — confirm export complete before proceeding
- [ ] Set up new email provider and import inbox history
- [ ] Validate all 3 addresses receive email correctly on new provider
- [ ] Update any services or accounts using the accounting or contact addresses

### DNS and hosting cutover

- [ ] Release registrar lock on domains being transferred (Websavers dashboard)
- [ ] Create Route 53 hosted zone for `tacedata.ca`
- [ ] Delegate DNS: change nameservers at Websavers to Route 53 (~15-20 min)
- [ ] Validate SSL certificate provisioned correctly (ACM, free with CloudFront)
- [ ] Confirm site and email both resolve correctly on new infrastructure
- [ ] Cancel Websavers WordPress hosting and email (do not cancel domain registration yet)
- [ ] Initiate domain transfer to Route 53 for kept domains (5-7 day ICANN window)
- [ ] Confirm transfers complete; Websavers relationship fully wound down

---

## Stage 4 — Content (Ongoing from Stage 1)

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
