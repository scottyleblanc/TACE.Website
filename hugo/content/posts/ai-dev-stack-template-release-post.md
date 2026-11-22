---
title: "ai development stack: after stack 10 — the template's first release"
date: 2026-11-21T20:00:00
draft: false
tags: ["ai", "powershell", "security", "stack"]
summary: "twelfth post in the ai development stack series: the template from Stack 10 is put to use on an existing repository and on this website, and what that use found is fixed.  The template now numbers its own releases, and its first release, v0.1.0, is out."
---

### After Stack 10

*This is the twelfth post in a series documenting the build of an AI development stack — a set of layers placed around AI-generated code to make it as correct, secure, and supportable as possible.  The [project page](/projects/ai-dev-stack-proj/) covers the question and the full layer model.  [Stack 10](/posts/ai-dev-stack-10-post/) made the stack reusable as a template.  This post covers what changed in the template once it was put to use, and its first release.*

*For a visual reference, see the [stack map](/projects/ai-dev-stack-map/): where each layer acts on a change, and the files behind it.*

*In this post, "we" means me and Claude Code, the AI coding assistant I build with.*

---

Stack 10 proved the template on a new, empty repository.  An empty repository has no old code, no slow tests and no history, so it could not show everything a working repository needs.

Since then the template has been added to two repositories that have them: a copy of an existing PowerShell module hosted on Bitbucket, and the repository for this website.  Each use found something to change.  This post lists the changes, and the step that gives the template version numbers.

The template is public on GitHub as [powershell-gate-kit](https://github.com/scottyleblanc/powershell-gate-kit).

---

### Proving it on an existing repository

The module copy had code standard findings from before the standards existed.  As Stack 10 planned, the baseline recorded them, counted per file and per rule, and every check then passed.  The Bitbucket CI file ran the same checks on Bitbucket's servers, which run Linux, not Windows.

---

### What changed

| Change | What it does |
|---|---|
| Nine more code standard rules | The checker now also requires, in every script and function: strict error handling, the standard behaviour of a PowerShell command, help text, a stated PowerShell version, and the function's name at the start of each progress message.  Public functions must check their input values.  A function that changes something must honour a dry run, which shows what would change without changing it.  Every exception to a rule must give a reason.  Code that changes the Windows registry, the store of system settings, is refused. |
| Fewer false reports | Two of the new rules reported some correct code as wrong.  They now read the structure of the code and accept it. |
| A text check across all files | An optional check searches every file for listed text, such as an internal server name, and fails if it finds any. |
| One folder for the gate files | A repository can keep its configuration, records, baseline and push script in one folder, `Gate/`, instead of its top folder.  The template keeps its own files there too. |
| A step-by-step guide | A runbook for adding the template to an existing repository, including running its tests on Linux. |
| Quick checks on the laptop, all checks on the pull request | The slow checks, such as the template's own tests, run only on the pull request.  The fast ones still run before every push. |
| Times in the CI log | Every line of the CI log shows the time, and each check shows how long it took. |
| A check on commit addresses | Each repository lists the email addresses its commits may carry.  A commit with any other address is refused before the push and on the pull request. |
| AI settings for the registry | The AI's settings file refuses commands that change the Windows registry. |
| Version numbers | The type of each change sets the next version, a check refuses a wrong number, and each release is tagged automatically after the merge. |

---

### The template follows its own rules

The template set rules for other repositories that its own repository did not follow.  Three changes close that gap.

**Its own checks on every pull request.**  The template's repository now runs every check on each of its own pull requests, and GitHub will not merge one that fails.  That rule has no exception, including for me as the owner.

**Its own AI settings.**  The template gives each repository a settings file that limits what the AI may do, and a check that the file has not been loosened.  The template's repository now holds the same file, under the same check.  The file refuses `git push`, the command that sends changes to GitHub.  When I asked the AI to delete branches on GitHub that had already been merged, it could not: deleting a branch there is a push.  It confirmed which branches were safe to delete and gave me the command to run.

**Its own commit address.**  Stack 10 set the template's commits to use the address GitHub provides to keep a personal address private.  That setting belonged to one copy of the repository, on one machine.  Commits made from another copy used my git default, a work email address, and some of them reached the public history.  We rewrote those commits with the private address, and every other copy of the repository has to be reset to match.  The commit address check is what stops it happening again: the template's repository allows only GitHub's private addresses.

---

### Version numbers

Until now the template had no version number.  A repository that took it in could not say which version it held, or take a later one on purpose.

Each commit message already starts with its type: `feat` for a new feature, `fix` for a correction, `docs` for documents only, and a few others.  The type now sets the next version number:

| The change | The version after 0.1.0 |
|---|---|
| A fix, such as `fix(review): read the record path from the config` | 0.1.1 |
| A new feature, such as `feat(gate): add the permissions check` | 0.2.0 |
| A change that can fail a repository that passed before | 0.2.0 for now; from version 1.0, the first number moves |
| Documents, tests or housekeeping only | no new version |

Before a pull request is opened, one script sets the version and gives it a heading in the changelog, the file that lists what each version changed.  A check refuses the pull request if the number does not match the types of its commits.  After the merge, GitHub tags the merged change with its version.  A tag is a fixed name, such as `v0.1.0`, for one point in the history, and a repository takes in a version by naming its tag.

Every merged feature or fix is a release, so a repository never has to take in changes that no version names.  The first release, v0.1.0, was tagged automatically when this work merged.

---

### Where the template stands

| | Before these changes | v0.1.0 |
|---|--:|--:|
| Checks | 14 | 15 |
| Custom code standard rules | 8 | 17 |
| Recorded decisions | 13 | 25 |
| Tests of the template itself | 100 | 217 |
| Its own checks on every pull request | no | yes |
| A failing pull request can merge | yes | no |
| Version number | none | 0.1.0, tagged automatically |

---

### The part worth keeping

The empty repository showed that the template worked.  The working repositories showed where it got in the way: gate files spread across the top folder, a slow test run before every push, and a commit address that depended on one machine's settings.  Each of those changes came from using the template, not from planning it.

The template now follows every rule it gives other repositories, and none of them has an exception for me or for the AI.

---

### What comes next

Two items remain for the next version.

**The Bitbucket image.**  Bitbucket runs the checks inside an image: a packaged copy of Linux and its tools.  The CI file picks the image by a name, `ubuntu:24.04`, that its publisher can point at a newer build at any time, so the checks could start running on different software with no change to the file.  The file should name the image by its digest instead: a fingerprint of one exact build.  Moving to a newer build would then mean editing the file, and that edit would be reviewed like any other.

**Blocking a merge on Bitbucket.**  It is not yet confirmed which Bitbucket plan can block a merge on a failing check, as GitHub does.  After that, a summary post answers the project's question layer by layer.

---

| | |
|---|---|
| Previous | [Stack 10 — a gate another repository can use](/posts/ai-dev-stack-10-post/) |
| Next | Summary — to come |

---

[ai development stack — project page](/projects/ai-dev-stack-proj/)
