# VERSIONING.md — tacedata-site

Commit and release conventions for the tacedata-site Hugo project.

---

## Commit Message Format

Follows [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/):

```
type(scope): short description

Optional body — explains why, not what.
```

- Subject line: imperative mood, no trailing period, 72 characters max
- Scope is optional but recommended for non-trivial changes
- Body is optional; use it when the reason is not obvious from the subject

Examples:

```
feat(content): add OracleAwsRotation project write-up
fix(config): correct baseURL for production build
docs(decisions): record Blowfish theme selection
chore(theme): update blowfish submodule to latest stable
```

---

## Commit Types

| Type | When to use | Maps to CHANGELOG section |
|------|-------------|--------------------------|
| `feat` | New page, section, feature, or capability | `### Added` |
| `fix` | Bug fix — corrects unintended behaviour | `### Fixed` |
| `docs` | Documentation only — no config or content change | `### Changed` (or omitted) |
| `chore` | Build, config, dependency, scaffolding | omitted |
| `refactor` | Structure change with no content change | `### Changed` |

---

## SemVer Rules

Follows [Semantic Versioning 2.0.0](https://semver.org/).

| Trigger | Version bump |
|---------|-------------|
| New site section, major feature, or stage completion | Minor (0.X.0) |
| Bug fix, config correction, content update | Patch (0.0.X) |
| Breaking change to site structure or URL scheme | Major (X.0.0) |

**Current state:** pre-release (0.x.0). Major version (1.0.0) marks the
site going live at tacedata.ca on the new stack.

---

## Branching Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Stable, tagged releases only |
| `feat/<topic>` | Feature branches — one per stage or logical unit of work |

Workflow:

1. Create a feature branch from `main`:
   ```
   git checkout -b feat/<topic>
   ```

2. Commit work on the feature branch. Push as needed.

3. Merge to `main` with `--no-ff`:
   ```
   git checkout main
   git merge --no-ff feat/<topic> -m "merge(feat/<topic>): description (vX.Y.Z)"
   ```

4. Tag the merge commit on `main`:
   ```
   git tag vX.Y.Z
   git push origin main --tags
   ```

5. Delete the feature branch after merge.

---

## Version — Commit — Changelog Mapping

These three must always be in sync. `CHANGELOG.md` and `TODO.md` travel in
the same commit as the work they describe — never in a separate trailing commit.

| Artefact | Where it appears |
|----------|-----------------|
| Git tag | `vX.Y.Z` on the merge commit in `main` |
| CHANGELOG entry | `## [X.Y.Z] - YYYY-MM-DD` in `docs/CHANGELOG.md` |
| TODO completion | Checked items (`[x]`) in `docs/TODO.md` |

At the end of each stage:

1. Check off completed `TODO.md` items for the stage.
2. Write the `CHANGELOG.md` entry for the version.
3. Commit alongside the stage work in a single commit.
4. Merge to `main` with `--no-ff` and tag.
