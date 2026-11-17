---
title: "ai development stack: stack 4 — a change that fails cannot be merged"
date: 2026-11-16T12:00:00
draft: false
tags: ["ai", "powershell", "oracle", "github-actions", "testing", "security", "stack"]
summary: "fifth post in the ai development stack series: GitHub now runs every check on each proposed change, and a change that fails cannot be merged, by anyone, including me."
---

### Enforced gate

*This is the fifth post in a series documenting the build of an AI development stack — a set of layers placed around AI-generated code to make it as correct, secure, and supportable as possible.  The [project page](/projects/ai-dev-stack-proj/) covers the question and the full layer model.  [Stack 3](/posts/ai-dev-stack-3-post/) added tests that fail when a promise in the code breaks.  This post is Stack 4: the enforced gate, the layer that makes the checks a condition of merging.*

*In this post, "we" means me and Claude Code, the AI coding assistant I build with.*

---

Until now, the checks ran on my own machine.  A hook, a script git runs on its own before each push, ran them, and stopped the push if one failed.

A hook depends on the machine and the person.  It runs only where it was installed, and one option on the push command (`--no-verify`) skips it.  The checks ran because I had set them up and did not skip them.

Stack 4 moves the checks to GitHub.  The aim is that a change which fails them cannot reach the main branch, whoever made it.

---

### Where the checks run

A change now reaches the main branch only through a pull request: a proposed change that GitHub shows on its own page before it is merged.

GitHub Actions, GitHub's service for running scripts, runs the checks on every pull request.  It runs the same script as the hook, with the unit tests added, so a change in what the code does is caught as well as a change in how it looks.

The file that tells GitHub what to run only installs the tools and calls that script.  It holds no logic of its own.  The checks stay in the repository, so moving to a different platform means replacing that one short file, not the checks.

---

### A check that checked nothing

Two of the checks look for passwords and tokens in commits, the saved records of each change, and in the notes that go with them.  On my machine they check the commits I have not yet published.  That is the right set: anything already published was checked when it was pushed.

On GitHub, every commit has already been published.  Run unchanged, those two checks would look at nothing and pass.

We gave the script an option that names the branch the change will be merged into.  With it, the checks look at the commits in the pull request instead.

To show the difference, we planted a token in the note of a commit that was already published.  Without the option, the checks passed.  With it, they failed.

---

### No way to merge around it

A rule on the main branch now decides what can be merged:

| Rule | What it means |
|---|---|
| Pull request required | No change goes to the main branch directly |
| Checks must pass | The pull request is blocked until the checks pass |
| Checks must come from GitHub Actions | A result with the same name, sent any other way, does not count |
| Up to date | The change must include everything already on the main branch, so the checks see what the merge will produce |
| History kept | The main branch cannot be overwritten or deleted |

Nobody can bypass the rule, including me.  I am the only person who merges changes to this repository, so a bypass for me would make the checks optional for the one person they apply to.

The rule does not require anyone to approve the change yet.  That comes with Stack 6, independent review.

---

### Giving the checks as little as possible

The checks run code from the pull request.  On a public repository, anyone can open one.  So the checks are given only what they need to read the code:

- **Read-only access.**  They can read the repository, not change it.
- **No secrets.**  No password, key or token is stored for them to use.
- **Pinned outside code.**  The one piece of outside code they use, GitHub's own tool for copying the repository, is fixed to one exact version.  The repository allows only GitHub's own tools, fixed that way.
- **Checked download.**  gitleaks, the secret scanner from Stack 2, is checked against a known fingerprint before it is unpacked.

GitHub also scans every push for secrets and refuses one that contains a known kind of token.

---

### Test results that must be current

The tests against a real Oracle database, from Stack 3, cannot run on GitHub, which has no Oracle database.  Each run records its result in a file that is committed with the change.

A new check now reads that file.  When the module code changes, the file must show a passing run of the latest code, and nothing but the file may have changed since that run.

The limit from Stack 3 stays open: the file shows the result, but it cannot prove the run happened.  It also means only someone with an Oracle database of their own can change the module code.

---

### Proving the stage

We opened a pull request carrying planted defects from the earlier stages:

- code that breaks one of my standards, from Stack 2
- a number in a commit note shaped like an AWS account number, from Stack 2
- the missing line from Stack 3 that makes the backup report pick the wrong backup
- a change to the module code with no new database test run

This is what GitHub ran:

```text
[PASS] tools : PSScriptAnalyzer 1.25.0, gitleaks 8.30.1, Pester 5.7.1, git
[FAIL] analyzer : 1 finding(s) over 40 files
[PASS] static : 160 passed, 0 failed, 0 skipped, 0 file(s) failed to run
[PASS] secrets : no leaks in the working tree
[PASS] commits : no leaks in 5 commit(s) since origin/master
[FAIL] messages : messages of 5 commit(s) since origin/master, 1 problem(s)
[FAIL] evidence : Source\ changed; integration evidence is missing or stale (rule T-14)
[FAIL] unit : 404 passed, 1 failed, 0 skipped, 0 file(s) failed to run; coverage 97.7%
[FAIL] gate: 4 of 8 checks failed: analyzer, messages, evidence, unit
```

Each defect failed the check meant for it, and GitHub blocked the merge.  The pull request that released this stage passed every check and was merged.

One planted defect stayed off GitHub: a fake token in a file.  Even a made-up token would stay readable in a public pull request.  That case runs locally, through the same script.

---

### The baseline

The baseline measures, taken again at the end of this stage:

| Measure | Stack 0 | Stack 1 | Stack 2 | Stack 3 | Stack 4 |
|---|--:|--:|--:|--:|--:|
| Module code, lines | 1,883 | 2,553 | 2,588 | 2,693 | 2,693 |
| Unit test code, lines | 3,847 | 4,302 | 4,636 | 5,372 | 5,372 |
| Unit tests passing | 291 | 317 | 352 | 405 | 405 |
| Static analyzer findings | 74 | 79 | 82 | 110 | 110 |

Stack 4 did not change what the module does.  The only changes to the module code were its version number.  The work was in the scripts around it and in GitHub's settings.

---

### The part worth keeping

Before this stage, the checks ran because I set them up and did not skip them.  Now a change that fails them cannot reach the main branch, whoever wrote it.

Moving a check to a new place can leave it passing while it checks nothing.  The only way we found out was by planting a defect and watching it get through.

---

### What comes next

Stack 5 is agent instructions: the AI is given my standards through instruction files built from the same source the checks enforce, and we measure whether that reduces the number of failed checks.

---

| | |
|---|---|
| Previous | [Stack 3 — testing the tests](/posts/ai-dev-stack-3-post/) |
| Next | [Stack 5 — giving the AI the rules](/posts/ai-dev-stack-5-post/) |

---

[ai development stack — project page](/projects/ai-dev-stack-proj/)
