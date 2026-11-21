# Decisions

Each decision: what was decided, why, and what it rules out. IDs are never reused; a
decision that is replaced is marked superseded and names the one that replaces it.

## DEC-001 — Consumed by git subtree, squashed

A repository takes the kit with
`git subtree add --prefix=tools/gate <kit-remote> main --squash` and updates it with
`git subtree pull`.

**Why:** the people and CI runners of a target repository may not be able to reach
the kit's repository. A subtree copies the files into the target, so nothing outside
the target is needed to run the gate. `--squash` keeps the kit's history out
of the target's history.

**Rules out:** git submodules, and a package feed.

## DEC-002 — Unbranded

The kit holds no owner name or copyright line, and no rule IDs or decision numbers
from another repository. Commit messages in the kit follow the same rule, because a
squashed subtree commit lists them. The one exception is `LICENSE` (DEC-010).

**Why:** the kit is copied into repositories owned by others.

**Enforced by:** KT-001 (`Tests/Unbranded.Tests.ps1`).

## DEC-003 — What the kit holds

The kit holds the checks any PowerShell repository can use: config, tools, analyzer,
static tests, secrets, commits, messages, agent permissions and the second-model
review (on by default), plus five optional checks: version, unit tests, test evidence,
package contents and agent instructions (DEC-013). It also holds the scripts behind
them, the templates a repository copies in (config, hook, CI wrappers, pull request
template) and the review guide.

**Why:** these checks need nothing from a repository but paths. Checks that depend on
one repository's build, database or test layout stay in that repository.

**Rules out:** an invariant linter, mutation tests and seeded-defect runs. Each depends
on one repository's own conventions for documenting and testing its invariants.

## DEC-004 — One config file, data only

A repository configures the gate in one file, `gate.config.psd1` at its root. It is
read with `Import-PowerShellDataFile`, so no code in it runs. Every path comes from the
config; the kit never assumes a folder name. The core checks cannot be turned off;
only the optional checks in the `Checks` table can.

**Why:** a gate whose core checks can be switched off by one line is not a gate. Data
files cannot run commands, so a config change cannot run code during the gate.

## DEC-005 — Numbering

Checks are `GK01` onward in run order; rules are a two-letter area and three digits
(`AN-001`); decisions are `DEC-001` onward. A number is never reused.

**Why:** a finding, a commit message or a review can cite a rule without ambiguity.
The scheme differs from those of the repositories the kit came from, so an ID always
says which rule set it belongs to.

## DEC-006 — The kit is gated by itself

The kit's root holds its own `gate.config.psd1`, and its pre-push hook runs its own
`Scripts/Invoke-Gate.ps1`. Its static tests run the gate against throwaway
repositories, one case per rule.

**Why:** a gate script that is not itself held to the gate drifts first.

## DEC-007 — Analyzer baseline, counted per file and rule

A repository that adopts the gate with existing analyzer findings records them with
`Update-AnalyzerBaseline.ps1`. GK03 then fails only on findings beyond the recorded
count for each file and rule. A config that names a baseline file that does not exist
fails GK01.

**Why:** a repository with hundreds of findings cannot fix them before it adopts the
gate, and must not add more after. Counting by file and rule survives line moves; a
count by line would fail every edit.

**Rules out:** suppressing existing findings in the code, and excluding whole rules to
get to green.

## DEC-008 — Bitbucket wrapper on Linux, PowerShell from the release tarball

`Templates/bitbucket-pipelines.yml` runs on a plain Ubuntu image and installs
PowerShell from its release tarball, checked against a pinned SHA-256.

**Why:** hosted Bitbucket runners are Linux. No current, stable PowerShell 7.6 image
was found in the Microsoft container registry's legacy repository, and a pinned
tarball is checked the same way gitleaks is.

## DEC-009 — One second-model review per pull request

The review record covers the branch from its merge base. Fixes after it are answered,
not reviewed again.

**Why:** each new review is a fresh session that finds a different subset of problems
and never settles; the cost of re-reviewing every fix is unbounded.

## DEC-010 — MIT licence, held by the owner of the code it came from

The kit is released under the MIT licence in `LICENSE`, with the copyright held by
the company that owns the code the kit was derived from. `LICENSE` is the only file
that names the holder; every other file stays unbranded (DEC-002).

**Why:** the kit is public, and anyone may use, change and redistribute it. MIT allows
that, disclaims warranty and liability for the authors and the holder, and is the
licence most often accepted by company policies on open-source code. The kit was
derived from code that company owns, so the company is the party able to release it.

**Rules out:** a public-domain dedication (not clearly recognised everywhere, and
refused by some company policies), and a copyright held personally (the company would
first have had to transfer its rights).

**Enforced by:** KT-001 skips `LICENSE` and checks every other file.

## DEC-011 — The pre-push hook skips the analyzer

The pre-push hook runs the gate with `-Quick`, which skips GK03. CI runs the gate
without it, so every pull request is analyzed.

**Why:** GK03 is the slowest check by far on a repository of any size, and a push that
waits minutes for it gets made with `--no-verify`, which skips the secret checks too.
The secret checks must run before a commit leaves the machine; a new analyzer finding
is caught at the pull request with nothing lost.

The kit's own hook passes `-Quick` too, and its GitHub workflow runs every check on
each pull request (DEC-020). Before the workflow existed, the hook was where GK03
runs on the kit (DEC-006).

**Rules out:** dropping the hook, and a hook that runs only gitleaks outside the gate.

**Enforced by:** the gate test "is off with -Quick".

## DEC-012 — Analyzer rules can be turned off for one folder

`Analyzer.ExcludeRulesByPath` maps a folder to rule names; GK03 and
`Update-AnalyzerBaseline.ps1` drop those rules' findings for files under the folder and
keep them everywhere else. Each entry says why beside it, as `ExcludeRules` does.

**Why:** some rules are wrong for one kind of file only. `PSAvoidUsingWriteHost` is
right for module code and wrong for operator scripts, whose console output is their
job. `ExcludeRules` would lose the rule for the module too, a suppression in every
script repeats one decision dozens of times, and a baseline fails each new console
line.

**Rules out:** per-file globs and wildcard rule names; a folder is the unit a repository
already organizes by.

**Enforced by:** the gate tests under "GK03 analyzer with ExcludeRulesByPath".

## DEC-013 — Test evidence, package contents and agent instructions are optional checks

GK12 (evidence), GK13 (package) and GK14 (instructions) are optional checks, off by
default. Each reads only paths from `gate.config.psd1`; the part that belongs to one
repository stays in that repository's own script.

- **Evidence:** the repository's script runs the tests CI cannot run;
  `Invoke-EvidenceRun.ps1` runs it and records the result, and GK12 checks the record
  is a passing run, on a clean tree, current for the branch. The evidence and review
  records may change after the run, since neither changes code.
- **Package:** GK13 builds the package with `Compress-PSResource`, which PowerShell 7.6
  ships, in a temporary folder, and compares it with the manifest's `FileList`. A
  repository whose module is built first names its build script.
- **Instructions:** `Export-AgentInstruction.ps1` joins the listed standards files into
  `AGENTS.md`; GK14 fails when the committed file differs from what it builds.

**Why:** each check needs nothing but paths, and each closes a gap a repository cannot
see from its own tests: changes that skipped the tests CI cannot run, a file shipped
that `FileList` does not name (PowerShell packages the whole module folder), and agent
instructions that lag the standards they were built from.

**Rules out:** the gate running the evidence tests itself (they need a machine or
service CI does not have), registering a package repository to build the package (it
would change the user's PSResource settings), and publishing anything.

**Enforced by:** the gate tests under "GK12 evidence", "GK13 package" and "GK14
instructions".

## DEC-014 — Strict mode, CmdletBinding and help are checked where a command starts

AN-010, AN-011 and AN-013 check a script that has a param block and every function
not defined inside another function or such a script. A function defined inside one
is exempt.

**Why:** strict mode and the error preference are inherited by child scopes, so a
nested function already runs under the settings of the command that defines it, and
it is not a command a user calls by name or asks `Get-Help` about. Requiring the
settings, the attribute and full help on every nested helper adds noise without
closing a gap. Help that `Get-Help` cannot read counts as missing: it fails the user
as completely as no help at all.

**Rules out:** checking nested functions; checking a script that has no param block
(a module file or a dot-sourced library, whose functions are checked one by one).

**Enforced by:** the analyzer rule tests for AN-010 to AN-013.

## DEC-015 — Where AN-014, AN-015 and AN-016 apply

AN-014 checks only a script or function that declares `SupportsShouldProcess`. AN-015
treats a file as public when its path has a folder named `Public`. AN-016 requires a
`#Requires -Version` statement and accepts any version.

**Why:** the kit sets no folder layout, so a rule cannot assume one. A command that
declares `SupportsShouldProcess` has promised callers a preview, so a call it does not
decide on breaks that promise; a command that makes no such promise would raise
findings with nothing to fix. `Public` is the common folder name for exported
functions, and a repository without one is not checked. The minimum PowerShell
version is the repository's choice; the kit requires only that each file states it.

An early exit for AN-014 is read from the structure of the code, not its order: a
declining `if` covers a call only when it comes earlier in a block that holds the call,
and its body ends in `return`, `throw` or `exit`, or in `continue` or `break` for a
loop or `switch` that encloses it within the same script block. A loop that skips a
declined item with `continue` is the common form; an exit inside another branch, or
inside a `ForEach-Object` block, says nothing about code outside it.

**Rules out:** checking commands that do not declare `SupportsShouldProcess`;
configuring the public folder; requiring a particular version; counting `continue`
inside a script block such as `ForEach-Object`'s, where it does not move to the next
item.

**Enforced by:** the analyzer rule tests for AN-014 to AN-016.

## DEC-016 — A verbose message names the command that writes it

AN-017 checks a `Write-Verbose` message given as a literal string, an expandable string
or the left side of a `-f` expression. The label may be any enclosing function's name,
or the script's file name outside every function.

**Why:** a verbose stream from several commands is unreadable without the name of the
one that wrote each line. A helper defined inside a function often reports as the
function users called, so either name is accepted. For the same reason a class method
may use its class's name: callers use the class, not the method, and an operator
searches a log for the class.

**Rules out:** checking a message held in a variable or built another way, which the
rule cannot read; checking the text after the label.

**Enforced by:** the analyzer rule tests for AN-017.

## DEC-017 — The message patterns can also scan the files

GK15 matches the message patterns against every file git tracks and every untracked
file it does not ignore. It is off by default. It skips `Files.Exclude`, binary files
and the pattern file itself.

**Why:** a value that must not appear in a commit message must not appear in a
committed file either, and gitleaks finds secrets, not names that are sensitive to
one repository. Untracked files are included so a value is found before `git add`.
The pattern file holds the patterns, and its examples may match them. It is optional
because a repository that adopts it may first have values to remove.

**Rules out:** scanning history (GK06 covers secrets there); printing a matched value
in full.

**Enforced by:** the gate tests under "GK15 files".

## DEC-018 — A repository's gate files can live in Gate/

`gate.config.psd1` is read from the repository root, or from `Gate/gate.config.psd1`
when the root has none; a copy in both places fails CF-001. `GitleaksIgnore` names
the gitleaks ignore file, which otherwise stays `.gitleaksignore` at the root. Paths
in the config, and fingerprints in the ignore file, stay relative to the root.

**Why:** a repository keeps its baseline, gitleaks config and hook in one folder, and
two of its gate files could not join them: the kit read the config only at the root,
and gitleaks read the ignore file only from the folder it scans. One fixed second
place keeps every kit script, the pre-push hook and the CI templates unchanged,
because they all find the config through Import-GateConfig.

**Rules out:** a `-ConfigPath` parameter on every script (each hook and pipeline would
have to pass it, and a call that forgot would read the wrong file); searching more
folders; a copy in both places, which would leave the reader unsure which one
applies. `bitbucket-pipelines.yml` stays at the root, the only place Bitbucket reads
it.

**Enforced by:** the gate tests under "GK01 config" and "GK05 to GK07 secrets, commits
and messages".

## DEC-019 — Registry changes are blocked in the code and in the agent's commands

AN-018 fails code that changes the Windows registry, and the agent templates deny the
agent's own registry-changing commands. Reading the registry is allowed in both.

**Why:** a registry change outlives the session that made it and can alter the
machine for every user, so it should never arrive unseen, from the code or from the
agent. The two controls cover different paths: the analyzer reads what the
repository ships, and the deny rules stop what the agent runs while it works. Neither
is complete on its own: both read text, not what runs, so a path in a variable or a
command built as a string passes them. The rule is an analyzer rule, not a check that
can be turned off, so an intended change is recorded where it is made, as a
suppression with a `Justification` (AN-012).

**Rules out:** blocking registry reads; treating the deny rules as a security
boundary (running the agent without administrator rights is what keeps HKLM out of
reach).

**Enforced by:** the analyzer rule tests for AN-018, and the GK08 test that the two
agent templates pass together.

## DEC-020 — The hook's subset is configured, and the kit runs CI on itself

The `Quick` key lists the checks `-Quick` skips, `GK03` by default. It may list GK03,
GK04, GK09, GK14 and GK15. The kit's own hook passes `-Quick` with
`Quick = @('GK03', 'GK04')`, and `.github/workflows/gate.yml` runs every check, with
`-Base`, on each pull request into main.

**Why:** which check is slow depends on the repository. On the kit, the static tests
build throwaway repositories and take longer than the analyzer, so skipping only GK03
still left a long push. A list in the config lets each repository move its slow
checks to CI without changing the kit. The config, tool, secret and permission
checks stay out of the list: a secret must be found before it leaves the machine, and
the others are fast. The workflow runs on the kit's pull requests, so every check
still runs before a merge.

The kit's own config turns `Checks.Review` off. Its pull requests are reviewed by the
maintainer, not by a recorded second-model review, so with the workflow passing
`-Base`, GK10 would fail every one of them. Target repositories keep the default,
on.

**Rules out:** skipping GK01, GK02 or GK05 to GK08; GK10 to GK13 in the list, which
the hook never runs (they need `-Base` or `-Unit`); a hook with no checks at all.

**Enforced by:** the gate tests "skips every check the Quick key lists, and only with
-Quick" and "CF-003 fails a Quick entry for a check that always runs".

## DEC-021 — CI output carries the time and each check's duration

`Invoke-Gate.ps1 -Timestamp` starts every line the gate prints with the UTC time, as
`yyyy-MM-ddTHH:mm:ssZ`, and ends each `[PASS]` and `[FAIL]` line with how long that
check took, in seconds. The CI templates pass it; the pre-push hook does not.

**Why:** a CI log is read after the fact, often to find which check made a run slow
or when it stopped. Not every CI host puts a time on each line, and a time alone
still means subtracting; the duration on the line answers it directly. UTC keeps runs
from different machines comparable. Locally the run is watched as it happens, so the
hook keeps the shorter lines.

**Rules out:** timestamps on by default; changing the lines the gate reads from the
static and unit test scripts, which it matches from the start of each line; local
time.

**Enforced by:** the gate tests under "Output with -Timestamp".
