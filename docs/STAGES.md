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
- GitHub Actions workflow building and deploying the Hugo site
- Site accessible at a test URL (not yet tacedata.ca)
- Full round-trip validated: local edit → commit → push → live within 2 minutes

**Hosting decision criteria:**

| Option          | Pros                                         | Cons                                  |
|-----------------|----------------------------------------------|---------------------------------------|
| GitHub Pages    | Everything in one place, zero config         | Less flexible (no redirects, no forms)|
| Netlify         | Preview deploys, form handling, redirects    | One more account/service to manage    |
| AWS (S3+CF)     | Learning touchpoint, portfolio signal        | More setup, not free at low volume    |

**Recommendation:** Start with Netlify or GitHub Pages. AWS hosting is worth
revisiting once AWS certification path is underway — at that point it becomes
a portfolio item worth the setup effort.

---

## Stage 3 — Domain and Email Migration

**Goal:** tacedata.ca pointing at new host. Websavers relationship wound down cleanly.

**Hard deadline:** Websavers renewal — June/July 2026.

**Decision required before deadline:**
- Email hosting replacement if moving away from Websavers
- Whether to transfer domain registrar or keep at Websavers and just change DNS

**Email options:**

| Option           | Cost         | Notes                                      |
|------------------|--------------|--------------------------------------------|
| Zoho Mail        | Free (1 user)| Good enough for low-volume professional use|
| Google Workspace | ~$8/mo CAD   | Best integration if using Google tools     |
| Fastmail         | ~$5/mo CAD   | Privacy-focused, clean, reliable           |

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
