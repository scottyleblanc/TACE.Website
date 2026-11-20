---
title: "ai development stack: stack 10 — a gate another repository can use"
date: 2026-11-19T20:00:00
draft: false
tags: ["ai", "powershell", "oracle", "security", "stack"]
summary: "eleventh post in the ai development stack series: the checks, settings and templates built in the first nine stages are moved into a template another repository can take in.  On a new, empty repository, a planted secret and a planted code defect were each refused before the push and again on the pull request."
---

### Wrap-up

*This is the eleventh post in a series documenting the build of an AI development stack — a set of layers placed around AI-generated code to make it as correct, secure, and supportable as possible.  The [project page](/projects/ai-dev-stack-proj/) covers the question and the full layer model.  [Stack 9](/posts/ai-dev-stack-9-post/) turned missed defects into checks.  This post is Stack 10: the wrap-up, where the stack is made reusable.*

*In this post, "we" means me and Claude Code, the AI coding assistant I build with.*

---

The first nine stages built their layers around one PowerShell module.  Much of what they built has nothing to do with that module: the code standards the checks enforce, secret scanning, the checks on commit messages and on the AI's permission settings, the review record, and the scripts that run all of it before a push and on every pull request.

Stack 10 moves those parts into a template that any repository can take in, and proves the template on a new, empty repository.

---

### What goes in the template

The template is a repository of its own.  A target repository takes it in as a git subtree: a copy of the template's files in one folder, `tools/gate`, with a command to pull later updates.  The files live in the target repository itself, so its team and its CI service need no access to the template's repository.

| In the template | Left out |
|---|---|
| The script that runs every check, with one command | The package check, which assumes this module's build |
| The code standards checker and eight of my custom rules | Two rules that assume this module's folder layout |
| Secret scanning of the files, the commits and the commit messages | The integration tests, which need a database |
| The check on the AI's permission settings | The linter for the requirement blocks at the top of each function |
| The second-model review script and the review checklist | The scripts that plant defects to test the checks |
| A script git runs before each push, CI files for GitHub and Bitbucket, a pull request template | The generator for the AI instruction file |

Each repository sets the template up with one configuration file: which folders to check, and which optional checks to turn on.  The file holds data only.  It is read in a way that cannot run code, so it cannot be used to make the checks pass.

---

### No names in it

The template is meant for repositories that are not mine, so nothing in it names me, my company or this module.  That covers the code, the documents and the commit messages, and also the rule numbers and decision numbers this repository uses.  The template numbers its own checks, rules and decisions.

The template's own tests include one that reads every file in it and fails on my company name, this module's name, a copyright line, or one of this repository's rule or decision numbers.  The template's checks run that test before every push, so a file that names any of them cannot be pushed.  Commit messages are not checked this way; they are kept clean by review.

Even the commit author needed changing: my git settings would have put my company email address on every commit, so the template's commits use an address that GitHub provides to keep a personal address private.

---

### Existing findings

A repository that has never been checked against these standards will fail on its first run, often with hundreds of findings.  It could never adopt the checks as they stand.

We added something this module never needed: a baseline.  One command records the current findings, counted per file and per rule.  After that, the check fails only when a file has more findings for a rule than the baseline records.  Old findings can be fixed over time; new ones cannot be added.

---

### Proving it on an empty repository

We created a new repository holding only a README, added the template and copied in its configuration file, the script git runs before each push, and the CI file, without changing them.  Then we tried four cases:

| Case | Before the push | On the pull request |
|---|---|---|
| The empty repository, configuration as supplied | 8 of 8 checks passed; each said when it had nothing to check | — |
| A small function, with one review run and its finding answered | Passed | Passed, 9 of 9 checks; merged |
| A planted secret, a fake access token | Refused | Failed on the secret checks |
| A planted code defect, a short alias in place of a full command name | Refused | Failed on the code standards check |

Both planted cases also failed the review check, since neither had a review.  The fake token did not appear in the CI log: the secret scanner reports where a secret is, never the secret itself.

The review of the small function found one problem: it had no test.  I accepted that finding without a fix, because the function exists only to give the checks something to read.

---

### What the proof found

On a pull request, GitHub showed the failing check in red, and the merge button still worked.

GitHub can make a check required, so that a pull request cannot merge until it passes.  On the free plan, that setting is available only on public repositories.  The test repository was private, so GitHub refused the setting.  On a free, private repository, the checks report a failure but cannot stop the merge.

This module's repository is public, so its rules still block a failing change, as in [Stack 4](/posts/ai-dev-stack-4-post/).  The template's instructions now state the limit.

---

### Is it only for PowerShell?

About half of the template works on any repository: secret scanning, the commit message checks, the permission check, the review check, the script that runs before each push, and the CI files.  The code standards checker, the test runner and the version check are PowerShell tools.  On a repository in another language, those checks would find nothing to read.

For now the template is for PowerShell.  Letting each repository name its own tools for those checks is a later change.

---

### The baseline

The baseline measures, taken again at the end of this stage:

| Measure | Stack 5 | Stack 6 | Stack 7 | Stack 8 | Stack 9 | Stack 10 |
|---|--:|--:|--:|--:|--:|--:|
| Module code, lines | 2,693 | 2,693 | 2,693 | 2,699 | 2,711 | 2,711 |
| Unit test code, lines | 5,372 | 5,372 | 5,372 | 5,372 | 5,372 | 5,372 |
| Unit tests passing | 405 | 405 | 405 | 405 | 405 | 405 |
| Static analyzer findings | 110 | 110 | 110 | 110 | 110 | 110 |
| Change review | none | in place | in place | in place | in place | in place |
| Agent privileges | none | none | in place | in place | in place | in place |
| Version checks | none | none | none | in place | in place | in place |
| Escaped-defect checks | none | none | none | none | in place | in place |
| Reusable template | none | none | none | none | none | in place |

Stack 10 did not change what the module does.  Only its version number changed.

---

### The part worth keeping

Each part that moved into the template had assumptions built in: folder names, file names, which checks always run.  Making it work in an empty repository meant turning each assumption into a setting, or leaving the part out.

The proof also showed that a check that runs is not the same as a check that blocks.  The same check, on the same kind of pull request, stops a merge in one repository and only reports in another.  That depends on the repository's settings and the hosting plan, not on the check.

---

### What comes next

The template's repository will be made public, and the template will be proven on an existing module, one with its own build and hosted somewhere other than GitHub.  After that, a summary post answers the project's question layer by layer.

---

| | |
|---|---|
| Previous | [Stack 9 — turning missed defects into checks](/posts/ai-dev-stack-9-post/) |
| Next | Summary — to come |

---

[ai development stack — project page](/projects/ai-dev-stack-proj/)
