# Security

| Item | Value |
|---|---|
| Version | unreleased (first tag pending) |
| Last audit | not yet audited |
| Findings resolved | none recorded |
| Tests | 205 static tests |

## 1. Secret scanning

**Status:** implemented (GK05, GK06, GK07); the file scan GK15 is optional.
**Why:** a secret that reaches a remote has to be treated as leaked.
**How:** gitleaks 8.30.1 scans the working tree, every commit not yet on a remote (or
the commits a branch adds, with `-Base`), and every one of those commit messages
through `gitleaks stdin`. The messages are also matched against the message patterns.
With `Checks.Files` on, GK15 matches the same patterns against every file git tracks
or would track, outside `Files.Exclude`.
**Contract:** a found value is never printed in full: gitleaks runs with `--redact`,
and a pattern match shows its first six characters only.

## 2. Pinned, hash-checked tools

**Status:** implemented (`Install-GateTool.ps1`, `Templates/bitbucket-pipelines.yml`).
**Why:** a tool fetched by name at run time can change underneath the gate.
**How:** PSScriptAnalyzer and Pester are installed at exact versions from PSGallery.
gitleaks and, in the Bitbucket template, PowerShell are downloaded from their GitHub
releases and checked against a pinned SHA-256 before they are unpacked; a mismatch
deletes the download and stops.
**Contract:** GK02 fails unless the exact versions are present.

## 3. Config cannot run code

**Status:** implemented (GK01).
**Why:** a gate whose config can run commands can be made to pass by its config.
**How:** `gate.config.psd1` is read with `Import-PowerShellDataFile`, which accepts only
data. Every path is checked to be relative and inside the repository (CF-004).
**Contract:** an invalid config stops the gate with exit 1.

## 4. Agent permission files

**Status:** implemented (GK08).
**Why:** a committed agent settings file decides what an AI agent may run without
asking; a loosened rule should be a visible, deliberate change.
**How:** each documented settings file is compared with its entry in the permissions
file: every deny rule present, no allow rule or setting beyond the documented ones. A
committed settings file with no entry fails. The templates deny registry changes by
the agent (`reg add` and the like, `regedit`, and changing cmdlets on `HK*:` and
`Registry::` paths); AN-018 fails the same changes in the code.
**Contract:** loosening the rules means changing the permissions file in the same diff.

## 5. Confined reviewer session

**Status:** implemented (`Invoke-ModelReview.ps1`).
**Why:** the reviewer reads untrusted change content; it must not be able to act on it.
**How:** the review runs in a fresh git worktree holding only committed files, with
`--restricted`, `--safe-mode`, `--strict-mcp-config`, read-only tools and no session
persistence.
**Contract:** the reviewer can read the reviewed commit and nothing else, and cannot
run commands or write files.

## 6. CI least privilege

**Status:** implemented (`Templates/github/gate.yml`, and the kit's own `.github/workflows/gate.yml`, built from it).
**How:** a read-only token, the `pull_request` trigger only, no secrets, credentials not
kept in the checkout, and the one action pinned to a full commit SHA.

## 7. Package contents

**Status:** implemented (GK13, optional).
**Why:** `Compress-PSResource` and `Publish-PSResource` package every file in the module
folder and ignore `FileList`, so a scratch file, test output or local config left there
ships, and a published package version cannot be withdrawn.
**How:** GK13 builds the package in a temporary folder, reads its entries, leaves out
only the entries NuGet adds itself, and compares the rest with `FileList`. Nothing is
published and no package repository is registered; the folder is deleted afterwards.
**Contract:** a manifest with no `FileList`, a packaged file it does not name, or a
named file not packaged fails GK13.

## 8. Test evidence

**Status:** implemented (GK12, optional).
**Why:** tests that need a machine or service CI does not have can be skipped silently.
**How:** `Invoke-EvidenceRun.ps1` records the commit, whether the tree was clean and
the script's exit code; GK12 requires a passing run on a clean tree with no change
after it but the records. The record holds no host name, user name or outside path.
**Contract:** the record is the author's attestation, as the review record is: the
gate proves it is current and passing, not that the run happened as recorded.

## Open items

- The Bitbucket template uses `ubuntu:24.04` by tag, not by digest.
- The Linux path has not run yet.
- The review record is the author's attestation: the gate proves it covers the branch
  and is answered, not that the session ran as recorded. The evidence record (GK12) is
  the same.
- The message patterns catch values with a known shape only; a real name that matches
  no pattern is left to review.
- Agent deny rules match the command text the agent writes, not the program it runs:
  `pwsh -Command "..."`, a path in a variable, or a relative path after
  `Set-Location HKLM:` is not stopped. Running the agent without administrator rights
  keeps HKLM out of reach; HKCU stays writable. AN-018 reads source text the same way,
  so a registry path held in a variable is not reported.

## Audit record

| Date | Version | Findings | Resolution |
|---|---|---|---|
| — | — | No audit yet | — |

## Code signing guidance

| Context | Policy | Files to sign |
|---|---|---|
| Developer workstation | RemoteSigned | none for local clones |
| Host that requires signed scripts | AllSigned | every `.ps1` in `Scripts/`, `Scripts/Lib/` and `Analyzer/Lib/`, every `.psm1` in `Analyzer/Rules/` |

Procedure: sign with `Set-AuthenticodeSignature -Certificate <code-signing cert>
-TimestampServer <timestamp URL>`, then confirm with `Get-AuthenticodeSignature`. Sign
in the target repository after each `git subtree pull`, since an update replaces the
files.
