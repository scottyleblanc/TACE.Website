# DECISIONS.md — tacedata-site

Records decisions made during the build. Each entry includes the decision,
the date, the options considered, and the rationale.

---

## Theme Selection

**Decision:** Blowfish
**Date:** 2026-03-22
**Status:** Active

### Options Evaluated

| Theme | Outcome |
|-------|---------|
| PaperMod | Evaluated — clean, works well, dark/light toggle, good nav. Liked it. |
| Congo | Evaluated — incompatible with Hugo 0.158 on stable branch; build errors not resolved. Abandoned. |
| Blowfish | Selected — preferred structure and layout over PaperMod; built cleanly; logo integration working. |
| Custom theme | Considered and rejected — weeks of work with no content value for this site's purpose. |

### Rationale

- Blowfish built cleanly with no errors on Hugo Extended v0.158
- Layout and structure preferred over PaperMod after side-by-side comparison
- Logo (PNG, transparent background) integrates cleanly via `assets/img/`
- Color scheme customization is straightforward via CSS variables
- Dark/light mode built in
- Content (Markdown) is fully portable if theme is ever switched
- Theme is not the value of this site — content is; Blowfish gets out of the way

### Configuration Notes

- Theme added as git submodule: `themes/blowfish`
- Config split across `config/_default/params.toml` and `config/_default/menus.toml`
- Logo at `assets/img/logo.png`; referenced via `logo = "img/logo.png"` in `params.toml`
- Color scheme: `ocean` (to be revisited — teal accent to match logo)
- Never edit files inside `themes/blowfish/` — all overrides go in `layouts/`, `assets/`, `config/`

---

## Hosting Target

**Decision:** Pending
**Date:** —
**Status:** Open — to be decided at end of Stage 1

Options: Netlify, GitHub Pages. Decision criteria in `docs/STAGES.md`.

---

## Email Hosting

**Decision:** Pending
**Date:** —
**Status:** Open — must be decided before Websavers renewal (June/July 2026)

Options: Zoho Mail (free), Fastmail (~$5/mo), Google Workspace (~$8/mo).
