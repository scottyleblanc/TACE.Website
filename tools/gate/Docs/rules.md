# Rules

Every rule the gate enforces, with the check that enforces it. A rule is one sentence
and one example. IDs are never reused: a retired rule keeps its ID and is marked
retired.

IDs: checks are `GKnn`, in the order the gate runs them; rules are a two-letter area
and three digits; decisions are `DEC-nnn` (`Docs/decisions.md`).

## Checks

| Check | Name | Runs | Rules |
|---|---|---|---|
| GK01 | config | Always; a failure stops the gate | CF-001 to CF-005 |
| GK02 | tools | Always | — |
| GK03 | analyzer | Always, except with `-Quick` while `Quick` lists it (the default; DEC-011, DEC-020) | AN-001 to AN-018 |
| GK04 | static | Always, except with `-Quick` while `Quick` lists it | ST-001 |
| GK05 | secrets | Always | SE-001 |
| GK06 | commits | Always | SE-002 |
| GK07 | messages | Always | CM-001 |
| GK08 | permissions | Always | PM-001, PM-002 |
| GK09 | version | When `Checks.Version` is on; not with `-Quick` while `Quick` lists it | VR-001; VR-002 with `-Base` |
| GK10 | review | When `Checks.Review` is on (the default), with `-Base` | RV-001 |
| GK11 | unit | When `Checks.Unit` is on, with `-Unit` | UT-001 |
| GK12 | evidence | When `Checks.Evidence` is on, with `-Base` | EV-001 |
| GK13 | package | When `Checks.Package` is on, with `-Base` | PK-001 |
| GK14 | instructions | When `Checks.Instructions` is on; not with `-Quick` while `Quick` lists it | AG-001 |
| GK15 | files | When `Checks.Files` is on; not with `-Quick` while `Quick` lists it | FP-001 |

## Config (GK01)

- **CF-001** — The repository holds one `gate.config.psd1`, a PowerShell data file, at
  its root or in `Gate/` (DEC-018).
  Example: a missing file fails GK01 and no other check runs; so does a copy in both
  places.
- **CF-002** — The config states `SchemaVersion = 1`.
  Example: `@{ SchemaVersion = 1 }` is the smallest valid config.
- **CF-003** — The config holds only the keys in `Templates/gate.config.psd1`, each of
  the right shape.
  Example: a misspelt `Analyser` key fails rather than being ignored. `Quick` may list
  only GK03, GK04, GK09, GK14 and GK15, so `Quick = @('GK05')` fails: the config, tool,
  secret and permission checks always run (DEC-020).
- **CF-004** — Every path in the config is relative, uses `/`, stays inside the
  repository, and names a file or folder that exists.
  Example: `StaticTests = '../shared-tests'` fails.
- **CF-005** — An optional check that is turned on has the settings it needs.
  Example: `Checks.Unit = $true` with no `Unit.Script` fails.

## Analyzer (GK03)

- **AN-001** — PSScriptAnalyzer reports no finding in the analyzed folders beyond the
  counts in the repository's baseline.
  Example: a baseline that holds two `PSAvoidUsingWriteHost` findings for a file fails
  on the third. A rule that `Analyzer.ExcludeRulesByPath` lists for a folder is not
  reported for files under that folder (DEC-012).
- **AN-002** — Every function declares its output type. Class methods and constructors
  are exempt: their return type is in their signature.
  Example: `[OutputType([PSCustomObject])]` below `[CmdletBinding()]`.
- **AN-003** — Platform is detected with `$IsWindows`, `$IsLinux` or `$IsMacOS`, never
  from the `OS` environment variable.
  Example: `if ($IsLinux) { ... }`, not `if ($env:OS -eq 'Windows_NT') { ... }`.
- **AN-004** — Every parameter has an explicit type.
  Example: `[string]$Name`, never `$Name`.
- **AN-005** — A call never continues a line with a backtick.
  Example: `$params = @{ Path = $path; Encoding = 'UTF8' }` then `Set-Content @params`.
- **AN-006** — Paths are built with `Join-Path`, never by joining strings with `\` or
  `/`.
  Example: `Join-Path -Path $root -ChildPath 'bin'`, not `"$root\bin"`.
- **AN-007** — Every file write names its encoding.
  Example: `Set-Content -Path $path -Value $text -Encoding UTF8`.
- **AN-008** — The current pipeline item is written `$PSItem`, never `$_`.
  Example: `ForEach-Object { $PSItem.Name }`.
- **AN-009** — No emoji in code, scripts or output; status uses a `[LABEL]` prefix.
  Example: `Write-Output '[INFO] done'`.
- **AN-010** — Every script with a param block, and every function, sets
  `Set-StrictMode -Version Latest` and `$ErrorActionPreference = 'Stop'` as statements
  of its own body. A function defined inside another function or such a script is
  exempt (DEC-014).
  Example: both lines directly below the param block, not inside a `try`.
- **AN-011** — Every script with a param block, and every function, declares
  `[CmdletBinding()]`, with the same exemption.
  Example: `[CmdletBinding()]` above `param(...)`.
- **AN-012** — Every analyzer suppression has a non-blank `Justification`.
  Example: `[SuppressMessage('PSAvoidUsingWriteHost', '', Justification = 'Console output.')]`.
- **AN-013** — Every script with a param block, and every function, has help that
  `Get-Help` can read, with a synopsis, description, example and notes, and one
  parameter entry for each parameter and no other, with the same exemption.
  Example: help that `Get-Help` cannot read fails, such as a prose line that starts
  with `.properties`, or script help on the line directly below `#Requires`.
- **AN-014** — In a script or function that declares `SupportsShouldProcess`, every
  call to a cmdlet that accepts `-WhatIf` sits inside `if ($PSCmdlet.ShouldProcess(...))`,
  follows an early exit when `ShouldProcess` declines, or passes `-WhatIf` itself. An
  early exit is a declining `if` earlier in a block that holds the call, whose body
  ends in `return`, `throw` or `exit`, or in `continue` or `break` for an enclosing
  loop or `switch`. Without one of these, a caller's `-WhatIf` silently skips the call
  (DEC-015).
  Example: `New-Item -Path $dir -ItemType Directory -WhatIf:$false` for work that
  must happen even during a preview.
- **AN-015** — Every parameter of a function in a file under a `Public` folder has a
  `[Validate*]` attribute, except switches, `[SecureString]` and `[PSCredential]`
  (DEC-015).
  Example: `[ValidateNotNullOrEmpty()] [string]$Name`.
- **AN-016** — Every `.ps1` and `.psm1` file has a `#Requires -Version` statement;
  any version passes (DEC-015).
  Example: `#Requires -Version 7.6` on the first line.
- **AN-017** — Every verbose message written as a string starts with the name of the
  command that writes it, in square brackets: an enclosing function, the class that
  holds a method, or the script's file name outside every function (DEC-016).
  Example: `Write-Verbose "[Get-Thing] Reading $Path."` inside `Get-Thing`.
- **AN-018** — Code does not change the Windows registry: no provider cmdlet that
  changes an item or property on a registry path, no `RegistryKey` change method, no
  `OpenSubKey` for writing, and no `reg add`, `reg delete`, `reg import` or the like,
  or `regedit` with arguments. Reading is allowed. An intended change carries a
  suppression with a `Justification` (DEC-019).
  Example: `Set-ItemProperty -Path HKLM:\SOFTWARE\Thing -Name Level -Value 1` fails;
  `Get-ItemProperty` on the same path passes.

## Static tests (GK04)

- **ST-001** — Every Pester test in the repository's static test folder passes, and
  every test file runs.
  Example: a test file with a parse error fails GK04, not only a failing `It`.

## Secrets (GK05, GK06)

- **SE-001** — gitleaks finds no secret in the working tree.
  Example: a token pasted into a notes file fails GK05 before it is committed.
  A false positive listed in the ignore file by its relative-path fingerprint
  (`<file>:<rule>:<line>`) does not fail GK05. The ignore file is `.gitleaksignore` at
  the repository root, or the file `GitleaksIgnore` names (DEC-018).
- **SE-002** — gitleaks finds no secret in any commit not yet on a remote, or, with
  `-Base`, any commit the branch adds.
  Example: a token committed and then deleted in a later commit still fails GK06.

## Commit messages (GK07)

- **CM-001** — No commit message holds a secret or a value that matches the
  repository's message patterns.
  Example: a commit message that quotes a local user-profile path fails.

## Agent permissions (GK08)

- **PM-001** — Each documented agent settings file keeps every documented deny rule,
  holds no allow rule or setting beyond the documented ones.
  Example: removing `Bash(git push *)` from the deny list fails until the permissions
  file changes in the same diff. The templates' deny rules include registry changes
  (`reg add`, `regedit`, and `Set-`, `New-`, `Remove-` and other changing cmdlets on
  `HK*:` and `Registry::` paths), so an agent cannot drop them unseen.
- **PM-002** — Every committed agent settings file is documented.
  Example: committing `.claude/settings.json` with no entry in the permissions file
  fails.

## Version (GK09)

- **VR-001** — The manifest's `ModuleVersion`, the newest CHANGELOG release and each
  listed `Version :` line name the same version.
  Example: `ModuleVersion = '1.2.0'` with `## [1.1.0]` newest in the CHANGELOG fails.
- **VR-002** — With `-Base`: the version is not lower than the latest tag, and a
  version already tagged is in the branch's history with no package input changed
  since the base.
  Example: a change under `source/` while the version is still the tagged `1.2.0`
  fails until the version is bumped.

## Review (GK10)

- **RV-001** — A branch that changes any file other than the review record, the
  evidence record and the exempt files carries a record of a completed second-model review of a commit it
  adds, from its merge base or an older one, with every finding answered `Fixed:`,
  `Rejected:`, `Accepted:` or `Deferred:`.
  Example: a record left by an earlier pull request fails, because its commit is
  already in the base.

## Unit tests (GK11)

- **UT-001** — The repository's unit test script exits 0.
  Example: the script owns its tests and coverage floor; the gate reads its exit code.

## Evidence (GK12)

- **EV-001** — A branch that changes a path `Evidence.Paths` covers carries an evidence
  record showing a passing run of `Evidence.Script` on a clean tree, on a commit in the
  branch's history, with no file but the evidence and review records changed since.
  Example: a source change committed after `Invoke-EvidenceRun.ps1` ran fails until
  the run is repeated and its record committed.

## Package (GK13)

- **PK-001** — The package built from the module holds exactly the files its
  manifest's `FileList` names, and the manifest has a `FileList`.
  Example: a scratch file left in the module folder fails as "not in FileList", since
  PowerShell packages every file in the folder whatever `FileList` says.

## Agent instructions (GK14)

- **AG-001** — The agent instruction file is exactly what `Export-AgentInstruction.ps1`
  builds from the files `Instructions.Sources` lists, and each of them has a title.
  Example: a standard changed without rebuilding `AGENTS.md` fails, so agents never
  read an older rule.

## Files (GK15)

- **FP-001** — No file git tracks, and no untracked file it does not ignore, holds a
  value that matches the message patterns, outside `Files.Exclude`. The pattern file
  and binary files are not scanned (DEC-017).
  Example: a local user-profile path pasted into a notes file fails before it is
  committed, as it would in a commit message.

## The kit itself

These hold for the kit's own files and are checked by the kit's own tests.

- **KT-001** — The kit carries no owner branding, copyright line or rule IDs from
  another repository's rule set, except the copyright line in `LICENSE` (DEC-010).
  Example: `Tests/Unbranded.Tests.ps1` fails on a company name in a comment.
