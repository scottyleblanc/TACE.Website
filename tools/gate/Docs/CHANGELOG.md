# Changelog

All notable changes to this kit are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and the kit uses
[Semantic Versioning](https://semver.org/) (`Docs/VERSIONING.md`).

## [Unreleased]

### Added

- `Invoke-Gate.ps1 -Timestamp` starts every line the gate prints with the UTC time
  (`yyyy-MM-ddTHH:mm:ssZ`) and ends each `[PASS]` and `[FAIL]` line with how long that
  check took. `Templates/github/gate.yml`, `Templates/bitbucket-pipelines.yml` and the
  kit's own workflow pass it; the pre-push hook does not (DEC-021). A target picks it
  up by copying its CI template again, or adding `-Timestamp` to its own.
- The `Quick` config key lists the checks `-Quick` skips, `GK03` by default; it may
  list GK03, GK04, GK09, GK14 and GK15 (CF-003, DEC-020). The config, tool, secret
  and permission checks always run.
- `.github/workflows/gate.yml`: the kit runs every check on itself, with `-Base`, on
  each pull request into main. The kit's own hook now passes `-Quick` and skips GK03
  and GK04, and the kit's own config turns `Checks.Review` off (DEC-020).
- Custom analyzer rule AN-018 (DEC-019): code does not change the Windows registry
  through the item cmdlets on a registry path, `RegistryKey` change methods, a
  writable `OpenSubKey`, `reg add` and the other changing `reg` verbs, or `regedit`
  with arguments. An intended change carries a justified suppression.
- `gate.config.psd1` can sit in `Gate/` instead of the repository root (DEC-018).
  GK01 reads whichever copy exists and fails CF-001 when there is a copy in both
  places. Paths in the file stay relative to the root.
- The `GitleaksIgnore` config key names the gitleaks ignore file, for example
  `Gate/gitleaksignore`; left empty, gitleaks reads `.gitleaksignore` at the root, as
  before (SE-001, DEC-018). GK05 to GK07 pass it to every gitleaks call, so GK06 and
  GK07 now read the ignore file whatever folder the gate runs from.

- Custom analyzer rule AN-017 (DEC-016): a verbose message written as a string starts
  with `[Name]`, the command that writes it.
- Optional check GK15 files (FP-001, DEC-017), off by default: no file git tracks, or
  would track, holds a value that matches the message patterns. `Files.Exclude` names
  files and folders to skip; the pattern file and binary files are not scanned.
- Custom analyzer rules AN-014 to AN-016 (DEC-015). In a command that declares
  `SupportsShouldProcess`, every cmdlet call that accepts `-WhatIf` has a preview
  decision (AN-014). Every parameter of a function under a `Public` folder has a
  `[Validate*]` attribute, except switches and credential types (AN-015). Every
  `.ps1` and `.psm1` file has `#Requires -Version` (AN-016). A repository upgrading
  the kit sees each gap as a new GK03 finding; fix it, or hold it in the baseline.
- Custom analyzer rules AN-010 to AN-013 (DEC-014). Every script with a param block,
  and every function not defined inside another function or such a script, sets
  strict mode and `$ErrorActionPreference = 'Stop'` in its own body (AN-010), declares
  `[CmdletBinding()]` (AN-011), and has help that `Get-Help` can read, with a synopsis,
  description, example, notes and one entry per parameter (AN-013). Every analyzer
  suppression has a `Justification` (AN-012). A repository upgrading the kit sees each
  gap as a new GK03 finding; fix it, or hold it in the baseline.
  `Analyzer/Lib/Get-GateRuleTarget.ps1` lists the scripts and functions the three
  scoped rules check.

- `Analyzer.ExcludeRulesByPath` in `gate.config.psd1` turns analyzer rules off under
  one folder, for example `@{ 'scripts' = @('PSAvoidUsingWriteHost') }` (DEC-012). GK01
  checks each folder exists (CF-004) and lists at least one rule name (CF-003).
- `Invoke-Gate.ps1 -Quick` skips GK03 and reports it `[OFF]`. `Templates/pre-push`
  passes it, so a push no longer waits for the analyzer; CI runs without it (DEC-011).
  The kit's own hook keeps GK03, because the kit has no CI. A target repository
  refreshes its `.githooks/pre-push` from the template to pick this up.
- `LICENSE`: the MIT licence (DEC-010), and a Licence section in the README. KT-001
  skips `LICENSE`, the one file that names the copyright holder.
- Three optional checks, off by default (DEC-013):
  - GK12 evidence (EV-001), with `-Base`: when a branch changes a path under
    `Evidence.Paths`, the committed record must show a passing run of
    `Evidence.Script` on a clean tree, current for the branch.
    `Scripts/Invoke-EvidenceRun.ps1` runs the script and writes the record.
  - GK13 package (PK-001), with `-Base`: the package `Compress-PSResource` builds from
    `Package.Manifest`'s folder holds exactly the files its `FileList` names.
    `Package.Build` names a build script to run first.
  - GK14 instructions (AG-001): `AGENTS.md` matches what
    `Scripts/Export-AgentInstruction.ps1` builds from `Instructions.Sources`.
- `Scripts/Invoke-Gate.ps1`: checks GK01 to GK11, configured by `gate.config.psd1`.
- `Scripts/Install-GateTool.ps1` for Windows x64 and Linux x64.
- `Scripts/Invoke-ModelReview.ps1`, `Scripts/Update-AnalyzerBaseline.ps1`,
  `Scripts/Invoke-StaticTest.ps1`.
- Custom analyzer rules AN-002 to AN-009.
- Templates: config, pre-push hook, GitHub Actions and Bitbucket Pipelines wrappers,
  pull request template, gitleaks config, message patterns, agent permissions.
- `Docs/rules.md`, `Docs/decisions.md` (DEC-001 to DEC-009), `Docs/REVIEW.md`.
- The kit's own tests: gate behaviour, analyzer rules, unbranded files (KT-001).

### Changed

- AN-014 reads an early exit from the structure of the code (DEC-015). A declining
  `if` that ends in `continue` or `break` for an enclosing loop or `switch` now covers
  the calls after it in that loop. A `return` inside another branch, or inside a
  `ForEach-Object` block, no longer covers calls outside it, and a `return` that is not
  the last statement of the `if` body no longer counts; a target can see new findings
  for those, which were missed before.
- AN-017 accepts the class name as the label inside a class method or constructor
  (DEC-016).
- `Docs/RUNBOOK.md` holds every step for adding the gate to a repository and keeping
  it working: ADOPT-1 to ADOPT-13, the per-pull-request steps PR-1 to PR-3, updating
  the kit (UPD-1), and a table of what each analyzer rule needs. The README's
  installation steps, the review path in `Docs/REVIEW.md`, the environment setup in
  `Docs/PREREQUISITES.md` and the copy instruction in `Templates/pre-push` move there
  and leave a pointer. New in the runbook: putting a repository's gate files in
  `Gate/`, keeping static tests portable to the Linux CI runner, clearing a baseline
  one folder at a time, requiring the build on Bitbucket, and finding the kit commit a
  `subtree pull` took.
- The README, `Docs/REVIEW.md` and the GitHub template state that a required check
  needs a public repository or a paid GitHub plan; on GitHub Free a private
  repository's gate only advises, and the human confirms it passed before merging.
- README installation rewritten for a first-time reader: one numbered step per task,
  each saying what it does; the tool install and the permanent `PATH` entry for
  gitleaks; a worked `Analyzer.Paths` example and the `Checks` table; every path given
  in full, relative to the target's root folder.
- GK10 exempts the evidence record, as it does the review record (RV-001).
- DEC-003 no longer rules out test evidence, package contents or agent instructions.
- README installation adds a step for the AI agent permission files: copying
  `Templates/claude-settings.json` to `.claude/settings.json` and
  `Templates/agent-permissions.psd1` into the target, checked by GK08.

### Fixed

- `Get-Help` shows the help of every script in `Scripts/`. Each had its help block on
  the line directly below `#Requires`, which PowerShell does not read as script help,
  so `Get-Help` showed only the syntax. A blank line now separates them (AN-013).
- The functions in `Scripts/Lib/GateLib.ps1` have a description, an example and notes
  in their help (AN-013).
- GK03 tries a file again, up to three times, when PSScriptAnalyzer 1.25.0 throws
  while loading the custom rules ("more than one dynamic module in each dynamic
  assembly", or a null reference); the throw was intermittent and stopped the whole
  gate. A third throw fails GK03 with the file named, and the later checks still run.

- `Templates/bitbucket-pipelines.yml` installs `libicu74`, `libssl3t64` and
  `libgssapi-krb5-2`. On the bare `ubuntu:24.04` image PowerShell stopped at start-up
  with "Couldn't find a valid ICU package installed on the system".
- GK05 scans the working tree as `.` from the repository root, so gitleaks
  fingerprints are relative paths and a fingerprint in `.gitleaksignore` matches.
  Scanning the absolute root path gave absolute fingerprints, so no `.gitleaksignore`
  entry ever matched. A test case covers it.
- `Templates/bitbucket-pipelines.yml` runs the gate with `-Unit`, as the GitHub
  workflow does, so GK11 runs in Bitbucket CI when `Checks.Unit` is on.
- AN-002 no longer reports class methods and constructors. `[OutputType()]` cannot be
  applied to them, so every one was a finding that could only be baselined. A test
  case covers it.

### Security

- `Templates/claude-settings.json` and `Templates/agent-permissions.psd1` deny the
  agent's own registry changes: `reg` with a changing verb, `regedit`, and the
  changing PowerShell cmdlets on `HK*:` and `Registry::` paths. A target repository
  copies both templates again, or adds the rules to its own files, to pick them up.
- gitleaks and PowerShell downloads checked against pinned SHA-256 hashes.
- Agent permission files checked against their documented rules (PM-001, PM-002).
- GK13 fails a module package that would ship a file its `FileList` does not name.
