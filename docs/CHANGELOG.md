# CHANGELOG — tacedata-site

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

## [0.1.0] - 2026-03-22

### Added
- Hugo Extended v0.158 confirmed installed locally
- `hugo-eval/` workspace initialized with `hugo new site . --force`
- Blowfish theme added as git submodule (`themes/blowfish`)
- `hugo.toml` configured: baseURL, languageCode, title, theme
- `config/_default/params.toml` — color scheme, appearance, header, homepage layout, author block
- `config/_default/menus.toml` — four nav items: Projects, Blog, Evolution, AI Perspective
- `config/_default/languages.en.toml` — language and author configuration
- Logo (PNG, transparent background) at `assets/img/logo.png` and `static/logo.png`
- Sample blog post: "Rotating Oracle Credentials with AWS Secrets Manager"
- Sample project page: "OracleAwsRotation"
- `content/_index.md` — home page stub
- `docs/DECISIONS.md` — theme selection recorded with rationale
- `docs/CHANGELOG.md` — this file

### Evaluated and Rejected
- PaperMod — evaluated, liked, not selected (Blowfish preferred on structure)
- Congo — build errors on Hugo 0.158; abandoned
- Custom theme — rejected; content is the value, not the theme
