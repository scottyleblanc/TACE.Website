# Claude Code Memory — tacedata-site

This file gives Claude Code the context needed to work effectively in this
repository without requiring re-explanation of decisions already made.

---

## Project Identity

- **Site:** tacedata.ca
- **Owner:** Scott LeBlanc (TACE Data Management Inc)
- **Purpose:** Personal portfolio and professional development journal — not a consulting brochure
- **Repo:** tacedata-site (will be public on GitHub)
- **Current stage:** Stage 1 — Hugo Evaluation

---

## What Is Being Built and Why

The existing site (WordPress on Websavers) is being replaced with a Hugo-based
static site managed entirely through Git. The motivation:

- WordPress felt like overhead — wanted Markdown + Git as the authoring workflow
- The site itself should be a portfolio artifact (public repo, CI/CD pipeline, version history)
- Authoring workflow: edit on laptop → commit → push → site updates automatically
- Websavers renewal is June/July 2026 — hard deadline for migration decision

This is not a client acquisition site. It is a working journal with proof of work,
documenting an ongoing professional evolution: Oracle DBA → PowerShell automation
engineer → cloud-capable practitioner.

---

## Stack (Decided — Do Not Revisit)

| Component    | Choice                              |
|--------------|-------------------------------------|
| Generator    | Hugo Extended                       |
| Repo hosting | GitHub (public repo)                |
| CI/CD        | GitHub Actions                      |
| Hosting      | Netlify or GitHub Pages (TBD)       |
| Domain       | tacedata.ca via Websavers (for now) |
| Email        | TBD before June/July 2026 renewal   |

---

## Content Threads

1. **Projects** — diagrams + write-ups on technical work in progress
2. **Blog** → LinkedIn — technical posts, cross-posted manually to start
3. **Evolution** — documented progression as it happens
4. **AI perspective** — honest practitioner observations on using AI in real work

---

## Current State

- Scaffold created: README.md, CLAUDE.md, docs/TODO.md, docs/STAGES.md, .gitignore
- hugo-eval/ directory structure in place, waiting for `hugo new site --force`
- Hugo not yet installed on local machine
- No theme selected yet
- No CI/CD pipeline yet
- Live site still on WordPress/Websavers — no changes made there

---

## Key Dates

| Event                          | Date            |
|--------------------------------|-----------------|
| Project scaffolded             | March 2026      |
| Websavers renewal deadline     | June/July 2026  |
| Target: Stage 1 complete       | No hard date — quality over speed |

---

## Conventions

- Docs live in `docs/` — never at repo root except README.md and CLAUDE.md
- TODO.md uses staged checklists — items move to STAGES.md complete section when done
- DECISIONS.md created when first real decision is recorded (does not exist yet)
- No generated output committed — public/ and resources/ always gitignored
- Themes added as git submodules, never copied directly

---

## What NOT to Do

- Do not propose CMS-based solutions — the move to Hugo + Git is a firm decision
- Do not commit hugo-eval/public/ or hugo-eval/resources/ — these are build output
- Do not copy theme files directly — use git submodule
- Do not create documentation files at repo root — docs/ only
- Do not hardcode any credentials, API keys, or account identifiers — repo will be public
