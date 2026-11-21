# Versioning

## Commit message format

Conventional Commits: `type(scope): description`, in the imperative, lower case.

```
feat(gate): add the permissions check
fix(review): read the record path from the config
```

Commit messages are part of the kit's history and are listed in a target repository's
squashed subtree commit, so they follow DEC-002: no owner names and no rule IDs from
another repository.

## Commit types

| Type | Use |
|---|---|
| `feat` | A new check, rule, script or template |
| `fix` | A check that passes or fails the wrong thing |
| `sec` | A change to a security mechanism in `Docs/SECURITY.md`; maps to `[SEC]` items in `TODO.md` |
| `docs` | Documents only |
| `test` | Tests only |
| `chore` | Housekeeping with no effect on behaviour |

## SemVer

- **Patch**: a fix, or a document change.
- **Minor**: a new check, rule, config key or template, off by default or passing on
  every repository that passed before.
- **Major**: a change that can fail a repository that passed before: a new core check,
  a stricter rule, a renamed or removed config key, a new `SchemaVersion`.

A breaking change carries a `BREAKING CHANGE:` footer and a CHANGELOG entry saying what
a target repository must change.

## Branching

One branch per piece of work off `main`, merged with `--no-ff`. Tags `vMAJOR.MINOR.PATCH`
go on `main` after the merge. A target repository pulls a tag:
`git subtree pull --prefix=tools/gate <kit-remote> v0.1.0 --squash`.

## Version, commit and changelog

Each release has a `## [x.y.z] - date` CHANGELOG section and a tag of the same number.
`TODO.md` and `CHANGELOG.md` change in the same commit as the code they describe.
Version numbers come from tags only.
