# powershell-gate-kit

## Overview

A gate for PowerShell repositories: one command that runs every check a change must
pass before it is pushed or merged. It runs PSScriptAnalyzer with the built-in rules
and 17 custom ones, the repository's static tests, gitleaks over the working tree, the
unpushed commits and their messages, a check of committed AI-agent permission files,
and, on a pull request, a check that the branch carries an answered second-model
review. Optional checks hold one version number everywhere, run the unit tests,
require a recorded run of tests CI cannot run, check that a module package ships only
the files its manifest lists, keep the AI agent instruction file in step with the
standards it is built from, and scan every file for values the message patterns
forbid.

The pre-push hook runs the same command with `-Quick`, which skips the slow checks the
config lists, such as the analyzer; the secret checks always run there. CI runs every
check on each pull request, so nothing is skipped before a merge.

A repository takes the kit as a git subtree in its `tools/gate/` folder and configures
it with one data file, `gate.config.psd1`, in its root folder or in `Gate/`.

## Prerequisites

PowerShell 7.6, git, PSScriptAnalyzer 1.25.0, Pester 5.7.1 and gitleaks 8.30.1.
`tools/gate/Scripts/Install-GateTool.ps1` installs the last three. Details in
[tools/gate/Docs/PREREQUISITES.md](Docs/PREREQUISITES.md).

## Installation

The steps to add the gate to a repository, new or existing, are in
[tools/gate/Docs/RUNBOOK.md](Docs/RUNBOOK.md): ADOPT-1 to ADOPT-13. The steps for each pull
request are PR-1 to PR-3, and updating the kit is UPD-1.

## Scripts

Paths as they are in a target.

| Script | What it does |
|---|---|
| `tools/gate/Scripts/Invoke-Gate.ps1` | Runs the checks GK01 to GK15; exits 0 when all pass |
| `tools/gate/Scripts/Install-GateTool.ps1` | Installs the pinned tool versions; gitleaks is hash-checked |
| `tools/gate/Scripts/Invoke-ModelReview.ps1` | Runs the second-model review once and writes the review record |
| `tools/gate/Scripts/Update-AnalyzerBaseline.ps1` | Records the current analyzer findings as the baseline |
| `tools/gate/Scripts/Invoke-StaticTest.ps1` | Runs the static test folder for GK04 |
| `tools/gate/Scripts/Invoke-EvidenceRun.ps1` | Runs the evidence script and writes the evidence record for GK12 |
| `tools/gate/Scripts/Export-AgentInstruction.ps1` | Builds `AGENTS.md` from the standards files for GK14 |

The checks and the rules each enforces are in
[tools/gate/Docs/rules.md](Docs/rules.md); the review steps are in
[tools/gate/Docs/RUNBOOK.md](Docs/RUNBOOK.md) PR-1, and what review covers is in
[tools/gate/Docs/REVIEW.md](Docs/REVIEW.md).

## Output Contract

The scripts are command-line tools, not module functions, so they do not return the
`Success / Data / Message` object. The gate prints one line per check and exits with a
code:

```
[PASS] GK05 secrets : no leaks in the working tree
[FAIL] GK07 messages : messages of 2 unpushed commit(s), 1 problem(s)
       commit 1a2b3c4: CM-001 no private key block: -----***
[OFF]  GK09 version : off in gate.config.psd1
[FAIL] gate: 1 of 8 checks failed: GK07 messages
```

Exit code 0 means every check that ran passed; 1 means at least one failed, or the
config is invalid. Every check runs even after one fails, except that an invalid config
stops the gate. A check that cannot run (a tool missing, git unable to list the
change) fails; it never passes by default.

## Logging and Diagnostics

The gate writes to standard output only, and writes no file in the repository; GK13
builds the package in a temporary folder and deletes it. Found values are never
printed in full: gitleaks runs with `--redact`, and a pattern match shows only its first
six characters. Each other script writes one file named in `gate.config.psd1`:
`Invoke-ModelReview.ps1` the review record (default `Review/LastReview.json`),
`Invoke-EvidenceRun.ps1` the evidence record (default `Evidence/LastRun.json`, which
holds no host name, user name or outside path), and `Export-AgentInstruction.ps1` the
agent instruction file (default `AGENTS.md`).

With `-Timestamp`, which the CI templates pass, every line the gate prints starts with
the UTC time and each `[PASS]` and `[FAIL]` line ends with that check's duration:
`2026-11-21T15:52:41Z [PASS] GK03 analyzer : 0 new finding(s) over 27 files (43.2 s)`.
The pre-push hook does not pass it (DEC-021).

## Current Security State

| Item | Value |
|---|---|
| Version | unreleased (first tag pending) |
| Last audit | not yet audited |
| Tests | 205 static tests: 48 gate behaviour cases, 98 analyzer rule cases, 59 unbranded file checks |
| Open items | See [Docs/SECURITY.md](Docs/SECURITY.md#open-items) |

## Licence

MIT; see [LICENSE](LICENSE). Anyone may use, change and redistribute the kit. It is
provided as is, without warranty, and the authors and the copyright holder accept no
liability for its use. `LICENSE` travels into `tools/gate/LICENSE` in every target and
must stay there.

## Contributing

This section is for work on the kit itself, in its own repository, where paths have no
`tools/gate/` prefix. Work is listed in [Docs/TODO.md](Docs/TODO.md), released changes
in [Docs/CHANGELOG.md](Docs/CHANGELOG.md), and commit and version rules in
[Docs/VERSIONING.md](Docs/VERSIONING.md). Decisions are in
[Docs/decisions.md](Docs/decisions.md). The kit is gated by itself, configured by its
own `gate.config.psd1`: turn on the hook with `git config core.hooksPath .githooks`.
