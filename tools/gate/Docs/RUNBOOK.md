# Runbook

How to add the gate to a repository that already has code, and how to keep it working.  Each section is one task.  A repository with no code yet follows the same sections and skips ADOPT-7.

| Section | Task |
|---|---|
| [Conventions](#conventions) | Terms and paths used below |
| [ADOPT-1](#adopt-1--decide-where-the-gate-files-live) | Decide where the gate files live |
| [ADOPT-2](#adopt-2--add-the-kit-to-the-target) | Add the kit to the target |
| [ADOPT-3](#adopt-3--install-the-tools) | Install the tools (once per machine) |
| [ADOPT-4](#adopt-4--create-the-config-file) | Create the config file |
| [ADOPT-5](#adopt-5--turn-on-the-pre-push-hook) | Turn on the pre-push hook |
| [ADOPT-6](#adopt-6--run-the-gate-for-the-first-time) | Run the gate for the first time |
| [ADOPT-7](#adopt-7--hold-the-existing-analyzer-findings-in-a-baseline) | Hold the existing analyzer findings in a baseline |
| [ADOPT-8](#adopt-8--clear-the-baseline-one-folder-at-a-time) | Clear the baseline one folder at a time |
| [ADOPT-9](#adopt-9--add-static-tests-that-run-on-linux-too) | Add static tests that run on Linux too |
| [ADOPT-10](#adopt-10--limit-what-ai-agents-may-do) | Limit what AI agents may do |
| [ADOPT-11](#adopt-11--run-the-gate-in-ci-and-require-it) | Run the gate in CI and require it |
| [ADOPT-12](#adopt-12--add-the-pull-request-template) | Add the pull request template |
| [ADOPT-13](#adopt-13--commit-and-push) | Commit and push |
| [PR-1](#pr-1--run-the-second-model-review) | Run the second-model review |
| [PR-2](#pr-2--record-the-evidence-run) | Record the evidence run |
| [PR-3](#pr-3--rebuild-agentsmd) | Rebuild `AGENTS.md` |
| [UPD-1](#upd-1--update-the-kit) | Update the kit |
| [FIX](#fixing-analyzer-findings) | Fixing analyzer findings: what each rule needs |

## Conventions

- **Target:** the repository you add the gate to.
- **Paths:** relative to the target's root folder, written with `/`.  Run every command from that folder, in a shell that has git and `pwsh` (Git Bash on Windows for the `cp` and `mkdir` lines).
- **`<kit-remote>`:** the clone URL of the kit's repository.
- **`Gate/`:** the folder in the target that holds its own gate files (ADOPT-1).  `tools/gate/` holds the kit itself and is never edited in the target.

---

### ADOPT-1 — Decide where the gate files live

**When:** before the first commit of any gate file.
**Prerequisites:** None

1. Put the target's own gate files in `Gate/`: the config (`Gate/gate.config.psd1`, DEC-018), the analyzer baseline, the gitleaks config and ignore file, the agent permission record and the pre-push hook (`Gate/hooks/pre-push`).
2. Give the static tests (GK04) a folder of their own, for example `Tests/Static/`.  `StaticTests` names one folder, and moving test files later means updating every document and script that names them.
3. Leave `bitbucket-pipelines.yml` or `.github/workflows/gate.yml` where the host reads it; neither can move.

**Verify:** the target's root holds no gate file except the CI file.
**If this fails:** a repository that already has gate files at the root can move them later; each move is listed under the section that creates the file.

### ADOPT-2 — Add the kit to the target

**When:** once per target.
**Prerequisites:** ADOPT-1

1. Add the kit as a squashed subtree:

   ```sh
   git subtree add --prefix=tools/gate <kit-remote> main --squash
   ```

**Verify:** `tools/gate/Scripts/Invoke-Gate.ps1` exists, and `git log -1` shows one commit holding the kit.  The files are part of the target, so its CI and everyone who clones it need no access to the kit's repository.
**If this fails:** `git subtree` needs a clean working tree; commit or stash first.

### ADOPT-3 — Install the tools

**When:** once per machine that runs the gate, including a self-hosted CI runner.
**Prerequisites:** ADOPT-2; PowerShell 7.6 and git ([PREREQUISITES.md](PREREQUISITES.md))

1. In `pwsh`, install the pinned tools:

   ```powershell
   & ./tools/gate/Scripts/Install-GateTool.ps1 -Destination (Join-Path -Path $HOME -ChildPath 'gate-tools')
   ```

   This installs PSScriptAnalyzer and Pester for your user and downloads gitleaks into `-Destination` after checking its hash.  It adds gitleaks to `PATH` for that session only.
2. Add `$HOME/gate-tools` to your user `PATH` permanently: on Windows, Settings, "Edit environment variables for your account"; on Linux, a line in `~/.profile`.
3. Open a new terminal.

**Verify:** `gitleaks version` prints `8.30.1` in a new terminal, and in every other shell that runs the gate, such as an AI agent's tool shell or a CI job.
**If this fails:** a shell started before step 2, or one that does not read the user `PATH`, fails GK02 with "gitleaks is not on PATH".  Start it again, or put the folder on that shell's `PATH`.

### ADOPT-4 — Create the config file

**When:** once per target.
**Prerequisites:** ADOPT-2

1. Copy the template to the place chosen in ADOPT-1:

   ```sh
   mkdir -p Gate && cp tools/gate/Templates/gate.config.psd1 Gate/gate.config.psd1
   ```

   The gate reads `gate.config.psd1` at the root or in `Gate/`, never both (CF-001).  Paths inside it are relative to the root either way.  Every key is commented in the file.  `tools/gate/gate.config.psd1` configures the kit itself, and the gate in the target ignores it.
2. List the code folders in `Analyzer.Paths`.  Until you do, GK03 checks no code: it reports "no files to analyze" and passes.  For a module whose code is in `source/` with helper scripts in `scripts/`:

   ```powershell
   Analyzer = @{
       Paths              = @('source', 'scripts')
       Exclude            = @('*.Tests.ps1')
       ExcludeRules       = @()
       ExcludeRulesByPath = @{ 'scripts' = @('PSAvoidUsingWriteHost') }   # console output is a script's job
       Baseline           = ''
   }
   ```

   `ExcludeRulesByPath` turns a rule off under one folder and keeps it everywhere else (DEC-012).
3. Turn the optional checks on or off in `Checks`.  The core checks GK01 to GK08 always run.

   | Key | Check | What it does | Starts | Turn it on when | Also set |
   |---|---|---|---|---|---|
   | `Review` | GK10 | On a pull request, requires a second-model review record covering the branch, with every finding answered ([REVIEW.md](REVIEW.md)) | on | You use the review step; it needs Claude Code installed.  Set `$false` if you do not | — |
   | `Version` | GK09 | The module version is the same in the manifest, the newest CHANGELOG release and the listed notes files | off | The target is a module with a CHANGELOG | `Version.Manifest`, `Version.Changelog` |
   | `Unit` | GK11 | Runs the target's unit test script when the gate is run with `-Unit` | off | The target has a script that runs its tests and exits 0 only when they pass | `Unit.Script` |
   | `Evidence` | GK12 | On a pull request that changes a path in `Evidence.Paths`, requires a committed record of a passing run of `Evidence.Script`, on a clean tree, with no later change but the records | off | The target has tests CI cannot run, such as integration tests against a local database | `Evidence.Script`, `Evidence.Paths` |
   | `Package` | GK13 | On a pull request, builds the module package in a temporary folder and fails unless it holds exactly the files the manifest's `FileList` names | off | The target is a module published to a gallery | `Package.Manifest`; `Package.Build` if the module is built first |
   | `Instructions` | GK14 | Fails unless `AGENTS.md` is what `tools/gate/Scripts/Export-AgentInstruction.ps1` builds from the standards files | off | The target keeps its coding standards in Markdown files and wants AI agents to read them | `Instructions.Sources` |
   | `Files` | GK15 | Fails when a tracked file, or an untracked one git does not ignore, holds a value that matches the message patterns, the same patterns GK07 applies to commit messages | off | The repository is public, or will be, and its patterns name values that must not appear in it | `MessagePatterns` with this repository's own entries; `Files.Exclude` for fixtures |

4. For a gitleaks config of your own, copy `tools/gate/Templates/gitleaks.toml` to `Gate/gitleaks.toml` and set `Gitleaks = 'Gate/gitleaks.toml'`.  For a gitleaks ignore file in `Gate/`, set `GitleaksIgnore = 'Gate/gitleaksignore'`; left `''`, gitleaks reads `.gitleaksignore` at the root.  Fingerprints in it stay relative to the root.
5. Leave `StaticTests`, `MessagePatterns` and `Permissions` as `''` for now; ADOPT-9 and ADOPT-10 set the first and last.

**Verify:** `pwsh -NoProfile -File ./tools/gate/Scripts/Invoke-Gate.ps1 -Quick` prints `[PASS] GK01 config`, and the GK01 line lists the optional checks that are on.
**If this fails:** GK01 names the key and the rule (CF-001 to CF-005, [rules.md](rules.md)); no other check runs until it passes.

### ADOPT-5 — Turn on the pre-push hook

**When:** once to add the hook; then once in every clone that pushes.
**Prerequisites:** ADOPT-3, ADOPT-4

1. Copy the hook:

   ```sh
   mkdir -p Gate/hooks && cp tools/gate/Templates/pre-push Gate/hooks/pre-push
   ```

2. In each clone that pushes, point git at it:

   ```sh
   git config core.hooksPath Gate/hooks
   ```

   The hook runs the gate with `-Quick` before every push and refuses the push when a check fails.  `-Quick` skips the checks the `Quick` key in `gate.config.psd1` lists: GK03, the analyzer, by default.  A slow check can join it, such as GK04 when the static tests take minutes; the config, tool, secret and permission checks always run.  CI runs every check on every pull request (DEC-011, DEC-020).  Do not run the full gate locally after every change; the hook and CI already run it.
3. Do not set `core.hooksPath` in a clone that must never push, such as a deployed copy guarded by its own hook: the repository setting overrides any global guard.

**Verify:** `git config core.hooksPath` prints `Gate/hooks`, `Gate/hooks/pre-push` exists and is executable (`git ls-files -s Gate/hooks/pre-push` shows mode `100755`), and the next `git push` prints the gate's lines before it sends anything.
**If this fails:** when `core.hooksPath` names a folder with no `pre-push`, git pushes without the gate and says nothing.  After moving the hook, run step 2 again in every clone.

### ADOPT-6 — Run the gate for the first time

**When:** after ADOPT-4.
**Prerequisites:** ADOPT-3

1. Run the full gate:

   ```sh
   pwsh -NoProfile -File ./tools/gate/Scripts/Invoke-Gate.ps1
   ```

**Verify:** each check prints one line, `[PASS]`, `[FAIL]` or `[OFF]`.  On a target with no code every check passes.
**If this fails:** on a target with existing code GK03 usually fails: go to ADOPT-7.  Any other failure names its rule; see [rules.md](rules.md).

### ADOPT-7 — Hold the existing analyzer findings in a baseline

**When:** GK03 fails in ADOPT-6 on code that predates the gate.
**Prerequisites:** ADOPT-6

1. In `gate.config.psd1`, set `Analyzer.Baseline = 'Gate/analyzer-baseline.psd1'`.
2. Before recording anything, turn off each rule that is wrong for a whole folder with `ExcludeRulesByPath` (ADOPT-4 step 2), with the reason beside it.  A finding excluded this way never enters the baseline.
3. Record the findings:

   ```sh
   pwsh -NoProfile -File ./tools/gate/Scripts/Update-AnalyzerBaseline.ps1
   ```

   The baseline counts findings per file and per rule.  From then on GK03 fails only when a file has more findings for a rule than the baseline holds, so existing findings can be fixed over time and new ones cannot be added.
4. Commit the baseline file.

**Verify:** the full gate prints `[PASS] GK03 analyzer`.  Expect a large first count on an established code base, often more than a thousand findings.
**If this fails:** "PSScriptAnalyzer failed 3 times on <file>" is a tool fault, not a finding: GK03 retries a file up to three times when PSScriptAnalyzer throws while loading the custom rules.  Run the gate again.

### ADOPT-8 — Clear the baseline one folder at a time

**When:** after ADOPT-7, as ordinary work.
**Prerequisites:** ADOPT-7

1. Pick one folder and one branch.  Fix its findings, using [Fixing analyzer findings](#fixing-analyzer-findings) for each rule.  A finding that is correct as written gets a suppression with a `Justification` (AN-012) at the narrowest scope that covers it.
2. Run only the targeted tests for the code you changed while you work.
3. Regenerate the baseline once, at the end of the branch, and only when the branch removed findings (ADOPT-7 step 3).

**Verify:** the folder has no entry left in the baseline file, and the full gate passes.
**If this fails:** a rule the kit adds later arrives as new GK03 findings when the kit is updated (UPD-1); fix them, or regenerate the baseline in the update branch.

### ADOPT-9 — Add static tests that run on Linux too

**When:** the target has Pester tests that read source text instead of running it.
**Prerequisites:** ADOPT-1 step 2

1. Put them in the folder chosen in ADOPT-1 and set `StaticTests` to it, for example `'Tests/Static'`.  GK04 runs every `*.Tests.ps1` there on every push, including from the hook.
2. Write each test so it gives the same result on Windows and Linux, because hosted CI runners are Linux:
   - Build paths with `Join-Path` and `/`, never `'Source\Public'`.
   - Split a path you parse yourself on both separators (`-split '[\\/]'`).  `[System.IO.Path]::GetFileName` and `GetRelativePath` keep or return `\` on Windows and `/` on Linux.
   - Sort anything that reaches a committed file ordinally (`[System.StringComparer]::OrdinalIgnoreCase`).  Culture order on Linux treats `-` and `.` differently from Windows.
   - Match file and folder names in their exact case; Linux file systems are case-sensitive.
   - Keep `<` and `>` out of test names, or use them on purpose: Pester reads `<Name>` in a name as a template variable.
3. Make each check assert that it found something to scan, so it cannot pass on an empty set.

**Verify:** `pwsh -NoProfile -File ./tools/gate/Scripts/Invoke-StaticTest.ps1 -Path ./Tests/Static` passes on Windows and in the CI run.  Run it on Linux before pushing where WSL or a container is available; otherwise the pull request build is its first Linux run.
**If this fails:** compare the failing test's paths and sort order with step 2.

### ADOPT-10 — Limit what AI agents may do

**When:** the target is worked on with Claude Code.
**Prerequisites:** ADOPT-4

1. Copy the settings and the permission record:

   ```sh
   mkdir -p .claude Gate
   cp tools/gate/Templates/claude-settings.json .claude/settings.json
   cp tools/gate/Templates/agent-permissions.psd1 Gate/agent-permissions.psd1
   ```

2. In `gate.config.psd1`, set `Permissions = 'Gate/agent-permissions.psd1'`.

   As copied, `.claude/settings.json` lets the agent run the gate and the read-only git commands (`status`, `diff`, `log`, `show`) without asking.  It denies `git push`, `rm` and `rmdir`, reading `~/.aws`, `~/.ssh` and the Claude Code credentials file, and changing the Windows registry through `reg`, `regedit` or the PowerShell item cmdlets.  Deny rules match the command text the agent writes, so they stop the direct forms only; analyzer rule AN-018 checks the repository's code for registry changes.  The permission record lists the rules that settings file may hold.  To allow the agent more, change both files in the same pull request, so the change shows in review.

**Verify:** the gate prints `[PASS] GK08 permissions`.
**If this fails:** GK08 fails when the settings file drops a deny rule or adds an allow rule or setting the record does not list (PM-001), and when an agent settings file is committed with no entry in the record (PM-002).

### ADOPT-11 — Run the gate in CI and require it

**When:** once per target.
**Prerequisites:** ADOPT-6

1. Add the CI file:
   - **GitHub:** copy `tools/gate/Templates/github/gate.yml` to `.github/workflows/gate.yml`.
   - **Bitbucket:** copy `tools/gate/Templates/bitbucket-pipelines.yml` to `bitbucket-pipelines.yml` and turn on Pipelines for the repository.

   Both run the gate on every pull request against its target branch.
2. Make the build a required check on the target branch:
   - **GitHub:** a branch protection rule or ruleset requiring the `gate` job.  This needs a public repository or a paid plan; on GitHub Free a private repository runs the gate but cannot block the merge.
   - **Bitbucket:** Repository settings, Branch restrictions, the rule for the target branch, Merge settings: tick "Minimum number of successful builds for the last commit with no failed builds and no in progress builds" and set it to 1.  A merge check blocks the merge only when the plan enforces merge checks ("Prevent a merge with unresolved merge checks"); otherwise a failed build only warns.  Which Bitbucket plan enforces it is not yet verified ([TODO.md](TODO.md)).
3. Hosted runners are Linux.  When `Unit` is on and the unit tests need Windows, run the gate with `-Unit` on a self-hosted Windows runner, or leave `-Unit` out of the hosted job and run the unit tests elsewhere.

**Verify:** a pull request shows the gate build, and the merge checks list it beside the approval checks.
**If this fails:** a check that does not appear in the merge checks is not configured on the branch rule; step 2.

### ADOPT-12 — Add the pull request template

**When:** once per target.
**Prerequisites:** None

1. On GitHub, copy `tools/gate/Templates/pull_request_template.md` to `.github/pull_request_template.md`; GitHub fills every new pull request with its checklist.  On Bitbucket, paste its text into each pull request description.
2. When `Review` is off, drop the template's second-model review section.

**Verify:** a new pull request shows the checklist.
**If this fails:** None

### ADOPT-13 — Commit and push

**When:** after the sections that apply.
**Prerequisites:** ADOPT-2 to ADOPT-6

1. With `Instructions` on, run `pwsh -NoProfile -File ./tools/gate/Scripts/Export-AgentInstruction.ps1` first.  Claude Code reads `AGENTS.md` when `CLAUDE.md` holds the line `@AGENTS.md`.
2. Commit the files these sections created: `Gate/` (config, baseline, gitleaks files, permission record, hook), the CI file, `.github/pull_request_template.md`, `.claude/settings.json`, the static tests and `AGENTS.md`, as they apply.
3. Push.

**Verify:** the hook runs the gate on that push, and the pull request build passes.
**If this fails:** the failing check's line names its rule.

---

### PR-1 — Run the second-model review

**When:** each pull request, when `Review` is on.
**Prerequisites:** Claude Code installed

1. Finish the change, commit everything, and pass the gate locally: `pwsh -NoProfile -File ./tools/gate/Scripts/Invoke-Gate.ps1 -Unit`.
2. Run the review once:

   ```sh
   pwsh -NoProfile -File ./tools/gate/Scripts/Invoke-ModelReview.ps1
   ```

   A new Claude Code session, with no access to the author's session, memory or instruction files, reviews the commits the branch adds to the target branch, in the order [REVIEW.md](REVIEW.md) sets.  It can read the repository at the reviewed commit and nothing else; it cannot run commands or change files.  The script writes the review record named in `gate.config.psd1` (default `Review/LastReview.json`).
3. Fix the findings worth fixing, in new commits, and answer every finding in the record ([REVIEW.md](REVIEW.md), "Answering a finding").  The fixes are not reviewed again; the human review judges the Responses.  Run the gate again after the fixes.
4. Commit the record and open the pull request.  CI runs the gate with `-Base`.  The maintainer does the human review with the template's checklist.

**Verify:** GK10 passes in CI.
**If this fails:** GK10 fails when the record is missing, does not cover the branch from its merge base, or has an unanswered finding (RV-001).  One review per pull request keeps the cost bounded; a second review is the author's choice.

### PR-2 — Record the evidence run

**When:** each pull request that changes a path in `Evidence.Paths`, when `Evidence` is on.
**Prerequisites:** everything else in the branch is committed

1. Run the evidence script as the last step:

   ```sh
   pwsh -NoProfile -File ./tools/gate/Scripts/Invoke-EvidenceRun.ps1
   ```

   It runs `Evidence.Script` and writes `Evidence/LastRun.json` (the `Evidence.Record` key).
2. Commit that file as the branch's last commit.

**Verify:** GK12 passes in CI.
**If this fails:** a later change to any file other than the evidence and review records makes the record stale; run step 1 again.

### PR-3 — Rebuild AGENTS.md

**When:** a standards file listed in `Instructions.Sources` changes, when `Instructions` is on.
**Prerequisites:** None

1. Run `pwsh -NoProfile -File ./tools/gate/Scripts/Export-AgentInstruction.ps1`.
2. Commit `AGENTS.md` with the change.

**Verify:** GK14 passes.
**If this fails:** do not edit `AGENTS.md` by hand; change the source file and run step 1.

---

### UPD-1 — Update the kit

**When:** the kit has changes the target wants.
**Prerequisites:** a clean working tree

1. On a new branch, pull the kit:

   ```sh
   git subtree pull --prefix=tools/gate <kit-remote> main --squash
   ```

   This brings the kit's newer files into `tools/gate/` as one squash commit and a merge commit.  The target's own gate files are outside `tools/gate/` and are not touched.
2. Find the kit commit the pull took.  `git subtree pull` does not print it; the squash commit's message holds it:

   ```sh
   git log -1 --format=%B HEAD^2
   ```

   The subject reads `Squashed 'tools/gate/' changes from <old>..<new>`, and the `git-subtree-split:` line gives the full hash.  Record it wherever the target tracks the kit's version.
3. Read the kit's `Docs/CHANGELOG.md` for new analyzer rules and checks.  A new rule reports its findings as new GK03 failures; fix them in this branch, or regenerate the baseline here (ADOPT-7 step 3).
4. Run the full gate, commit, and open the pull request.

**Verify:** the pull request build passes with the new kit.
**If this fails:** `git subtree` refuses to run with uncommitted changes; commit or stash them.  A kit commit pulled by mistake is undone by reverting the squash and merge commits, never by editing `tools/gate/`.

---

## Fixing analyzer findings

What each kit rule needs, and the traps met clearing real code bases.  The rules themselves are in [rules.md](rules.md).

| Rule | Fix | Trap |
|---|---|---|
| AN-002 | `[OutputType()]` below `[CmdletBinding()]` | Class methods are exempt; a nested helper function is not |
| AN-004 | An explicit type on every parameter | `[object]` is a type; use it where any value is valid |
| AN-005 | Splat the parameters: `$params = @{ ... }`, then `Command @params` | A bare-word argument (`-Method Put`) becomes a command call in a hashtable; quote it (`Method = 'Put'`).  Splatting also binds parameter aliases |
| AN-006 | `Join-Path` for every file path | A regex, a URL or a connect string is not a path; suppress it with a reason |
| AN-008 | `$PSItem`, never `$_` | Also inside expandable strings: `"$($PSItem.Name)"` |
| AN-010 | `Set-StrictMode -Version Latest` and `$ErrorActionPreference = 'Stop'` as statements of the body | Inside a `try` they do not count |
| AN-012 | `Justification = '<why>'` on every suppression | — |
| AN-013 | A synopsis, description, example, notes and one entry per parameter | A prose line starting with `.` (such as `.properties`) is read as a keyword and discards the whole help block; put it in backticks.  A script's help written on the line directly below `#Requires` is not read; leave a blank line between them |
| Any | `[Diagnostics.CodeAnalysis.SuppressMessage('<Rule>', '<Target>', Justification = '<why>')]` | PSScriptAnalyzer reads a suppression only on a function's or a script's param block, not on a scriptblock's.  A target can name one parameter, for example `'CredentialId'` |

A parameter named `$home` throws in a script, or in a function defined outside a module, because `$HOME` is a read-only automatic variable.  Rename it rather than suppressing the finding that led you to it.
