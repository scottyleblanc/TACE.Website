# TODO — tacedata-site

Active build checklist. Items move to STAGES.md (complete section) when done.
Stages are defined in `docs/STAGES.md`.

---

## Stage 1 — Hugo Evaluation (Current)

### In Progress

- [ ] Install Hugo Extended locally (`winget install Hugo.Hugo.Extended`)
- [ ] Run `hugo new site hugo-eval` to initialize site structure
- [ ] Evaluate 2-3 themes — shortlist criteria in STAGES.md
- [ ] Create sample content — one post, one project page
- [ ] Validate local workflow: edit Markdown → `hugo server` → view in browser

### Open

- [ ] Commit hugo.toml and initial content to repo
- [ ] Add `.gitignore` — exclude `hugo-eval/public/`, `hugo-eval/resources/`
- [ ] Document theme decision in `docs/DECISIONS.md` with rationale
- [ ] Confirm `hugo-eval/` structure matches intended production layout before graduating it

---

## Stage 2 — CI/CD and Hosting (Pending Stage 1 complete)

### Open

- [ ] Choose hosting target: Netlify vs GitHub Pages — see STAGES.md for decision criteria
- [ ] Create GitHub Actions workflow: push to main → hugo build → deploy
- [ ] Test full pipeline end-to-end on a non-production URL before pointing domain
- [ ] Document pipeline in README.md

---

## Stage 3 — Domain and Email Migration (Pending Stage 2 complete)

### Open

- [ ] Decide on email hosting before Websavers renewal (June/July 2026)
    - Options: Zoho Mail (free tier), Google Workspace, Fastmail
- [ ] Point tacedata.ca DNS to new hosting target
- [ ] Validate SSL certificate provisioned correctly on new host
- [ ] Confirm old Websavers site is fully decommissioned before non-renewal
- [ ] Update domain registrar if moving away from Websavers

---

## Stage 4 — Content (Ongoing from Stage 1)

### Open

- [ ] Define site sections: Home, About, Projects, Blog, (AWS journey?)
- [ ] Draft "About" content — who I am, the evolution, the intent of the site
- [ ] Write up first project — OracleAwsRotation (diagram + problem/solution write-up)
- [ ] Draft first blog post — candidate topics in STAGES.md
- [ ] Decide on AI perspective thread — format, cadence, tone
- [ ] Define LinkedIn publishing workflow — how posts get from blog to LinkedIn

---

## Parking Lot — Not Yet Staged

- AWS certification path — which cert, timeline, how it integrates with site content
- Whether to make the GitHub repo public from the start or after initial content is in place
- Contact page — needed eventually, not urgent while not actively seeking clients
- Analytics — simple, privacy-respecting option (Plausible, Fathom, or none)
