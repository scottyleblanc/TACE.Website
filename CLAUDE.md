# Claude Instructions — tacedata-site

## Project Identity

| Field           | Value                                                        |
|-----------------|--------------------------------------------------------------|
| Repo path       | `tacedata-site\`                                             |
| Current stage   | Stage 1 — Hugo Evaluation                                    |
| Live site       | https://tacedata.ca (currently WordPress on Websavers)       |
| Hard deadline   | Websavers renewal June/July 2026 — migration must be done or decided by then |
| Domain          | tacedata.ca (registered via Websavers)                       |

---

## What This Project Is

A personal portfolio and professional development site. Not a consulting brochure —
a working journal with proof of work. The site documents an ongoing evolution:
Oracle DBA → PowerShell automation engineer → cloud-capable practitioner.

Four content threads:
- **Projects** — architecture diagrams and write-ups on technical work being built
- **Blog** — technical writing, published to site then cross-posted to LinkedIn
- **Evolution** — documented progression through stages of learning and capability
- **AI perspective** — honest observations on using AI as an engineering partner

The intended reader is a peer, future employer, or someone on a similar journey —
not a prospective client (at least not yet).

---

## Stack Decisions (Already Made)

| Component      | Decision                        | Rationale                                                    |
|----------------|---------------------------------|--------------------------------------------------------------|
| Generator      | Hugo                            | Markdown-based, no CMS overhead, fast, git-native workflow   |
| Source control | Git / GitHub                    | Public repo — the site itself is a portfolio artifact        |
| CI/CD          | GitHub Actions                  | Push to main → build → deploy; learning touchpoint for CI/CD |
| Hosting        | Netlify or GitHub Pages (TBD)   | Decided at end of Stage 1 evaluation                         |
| Current host   | Websavers (WordPress) — exiting | Renewal June/July 2026 is the migration deadline             |
| Email          | TBD — must decide before Websavers renewal | Options: Zoho Mail (free), Fastmail (~$5/mo), Google Workspace (~$8/mo) |

Do not propose WordPress, Wix, Squarespace, or any CMS-based solution.
The move to Markdown + Git is a firm decision.

---

## Session Start — Always Do This First

Before writing any code or creating any files:

1. Read `docs/TODO.md` — check what is open, in-progress, and complete
2. Read `docs/STAGES.md` — understand the current stage goal and definition of done
3. Read `docs/DECISIONS.md` if it exists — review decisions already recorded

Do not propose changes to the stack or structure without checking whether the
decision is already recorded.

---

## Current Stage Detail — Stage 1: Hugo Evaluation

**Goal:** Validate that Hugo + Git + CI/CD is the right workflow before committing
to full migration away from WordPress/Websavers.

**What needs to happen this stage:**
- Hugo Extended installed locally (`winget install Hugo.Hugo.Extended`)
- `hugo new site hugo-eval --force` run to populate the eval directory
- 2-3 themes evaluated against criteria in `docs/STAGES.md`
- Sample content rendering correctly (one post, one project page)
- Local workflow confirmed comfortable: edit Markdown → `hugo server` → view result
- Theme decision recorded in `docs/DECISIONS.md`
- `.gitignore` confirmed correct before first real commit

**hugo-eval/ structure:**
```
hugo-eval/
├── hugo.toml               ← created by hugo new site
├── content/
│   ├── posts/              ← blog posts
│   └── projects/           ← project write-ups
├── themes/                 ← themes added as git submodules
├── static/                 ← static assets
└── layouts/                ← custom layout overrides
```

`hugo-eval/public/` and `hugo-eval/resources/` are excluded by `.gitignore` —
never commit these.

---

## File Structure

```
tacedata-site/
├── CLAUDE.md               ← this file
├── README.md               ← stack, structure, local dev commands
├── .gitignore
├── docs/
│   ├── TODO.md             ← active staged checklist
│   ├── STAGES.md           ← phase definitions, criteria, decision tables
│   └── DECISIONS.md        ← created when first decision is recorded
└── hugo-eval/              ← Hugo evaluation workspace (Stage 1)
    ├── content/
    │   ├── posts/
    │   └── projects/
    ├── themes/
    ├── static/
    └── layouts/
```

---

## Constraints — Do Not Violate

- **No credentials, keys, or account IDs** committed to this repo — it will be public
- **No generated output committed** — `hugo-eval/public/` is build output, always gitignored
- **Themes via git submodule** — not copied directly into the repo
- **All docs in `docs/`** — do not create documentation files at repo root except README.md and CLAUDE.md
- **Markdown for all content** — no HTML content files in `hugo-eval/content/`

---

## Open Items

See `docs/TODO.md` for the full list. Key items as of project start:

- Hugo not yet installed locally — Stage 1 cannot proceed until this is done
- Theme not yet selected — evaluation criteria in `docs/STAGES.md`
- Hosting target (Netlify vs GitHub Pages) — decided at end of Stage 1
- Email hosting replacement — must be decided before Websavers renewal (June/July 2026)
- `docs/DECISIONS.md` does not yet exist — create it when first decision is made
