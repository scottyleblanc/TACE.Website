# STAGES — tacedata-site

Phase definitions, current state, and decision criteria.

---

## Current Stage: Stage 2 — CI/CD and Hosting

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

## Stage 2 — CI/CD and Hosting

**Goal:** Automated pipeline from laptop to live URL. Push to main, site updates.

**Definition of done:**
- Hosting target decided and documented in `docs/DECISIONS.md`
- GitHub Actions workflow building and deploying the Hugo site
- Site accessible at a test URL (not yet tacedata.ca)
- Full round-trip validated: local edit → commit → push → live within 2 minutes

**Hosting decision status:** Analysis complete — final call pending Websavers account review.

GitHub Pages is eliminated. The site has a utilities layer requiring authentication and
serverless backend logic, which GitHub Pages cannot support. Decision is between:

- **Netlify first** — get live quickly, migrate static content to AWS when first utility is built
- **AWS direct** — front-load setup cost once, no migration needed later

Full analysis and cost breakdown in `docs/DECISIONS.md`. Websavers review checklist in `docs/websavers.md`.

---

## Stage 3 — Domain and Email Migration

**Goal:** tacedata.ca pointing at new host. Websavers relationship wound down cleanly.

**Hard deadline:** Websavers renewal — June/July 2026.

**Websavers account review required first** — see `docs/websavers.md`. Need to confirm
exact renewal date, cost breakdown, what email addresses exist, and whether domain
registration is bundled with hosting or billed separately.

**DNS approach (decided):**
Two separate operations — do not conflate:
1. **Delegate DNS to Route 53** — change nameservers at Websavers, Route 53 becomes authoritative. ~15-20 min. This is the cutover step.
2. **Transfer domain registration** — optional, separate, takes 5-7 days (ICANN). Do after DNS delegation is confirmed working.

**Email options:**

| Option           | Cost         | Notes                                      |
|------------------|--------------|--------------------------------------------|
| Zoho Mail        | Free (1 user)| Good enough for low-volume professional use|
| Google Workspace | ~$8/mo CAD   | Best integration if using Google tools     |
| Fastmail         | ~$5/mo CAD   | Privacy-focused, clean, reliable           |

Email decision blocked on Websavers review — need to know what is in active use before choosing a replacement.

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

---

## Parking Lot

Items not yet assigned to a stage:

- AWS certification path and how it shapes site content
- Contact page
- Analytics (Plausible, Fathom, or none — avoid Google Analytics)
- Whether repo goes public immediately or after initial content is in place
