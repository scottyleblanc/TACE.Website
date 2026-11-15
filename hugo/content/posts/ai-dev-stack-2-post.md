---
title: "ai development stack: stack 2 — one command for every static check"
date: 2026-11-15T00:00:00
draft: false
tags: ["ai", "powershell", "oracle", "pester", "testing", "security", "stack"]
summary: "third post in the ai development stack series: the stack 1 rules a machine can check now run with one command, before anything is published."
---

### Deterministic checks

*This is the third post in a series documenting the build of an AI development stack — a set of layers placed around AI-generated code so it can be trusted.  The [project page](/projects/ai-dev-stack-proj/) covers the question and the full layer model.  [Stack 1](/posts/ai-dev-stack-1-post/) specified the rules the code must follow.  This post is Stack 2: deterministic checks, the first layer that enforces them.*

*In this post, "we" means me and Claude Code, the AI coding assistant I build with.*

---

Stack 1 produced a set of rules.  Until now, most of them could be checked only by me reading the code, and I do not read every line the AI writes.

Stack 2 turns the rules into checks a machine runs.  They are deterministic: run them twice on the same code and they give the same result.  The checks that read the code without running it now run from one command.

---

### Checking the code

PSScriptAnalyzer is Microsoft's analyzer for PowerShell, a tool that reads code without running it and reports problems.  It comes with built-in rules for common mistakes, such as a password parameter that accepts plain text, or a function that changes something but offers no way to preview the change first.

The built-in rules know nothing about my standards.  PSScriptAnalyzer also accepts custom rules, so we wrote custom rules for the standards it is able to check, and it now runs them alongside its own.

For example, one of my standards says every function must state what kind of result it returns.  No built-in rule checks that.  Our rule now flags any function that does not.

The first run flagged code that broke my own standards.  We fixed all of it.

---

### Checking for secrets

The repository is public.  Anything committed to it can be read by anyone, and stays in its history for good.

Stack 1 added a check for things that identify my systems, such as AWS account numbers.  Stack 2 adds gitleaks, a free scanner that recognises passwords, access keys and tokens by their format.

gitleaks scans the files, but not the note saved with each commit, the record of a change.  Those notes are just as public.  We confirmed the gap, then added a separate scan of the notes.

One gap remains.  A name with no recognisable format, such as the name of a storage location, can only be caught by someone reading the change.  Closing it affects every public repository I have, so it stays open until I decide how to handle it across all of them.

---

### One command

The following checks run from one script:

| Check | What it looks for |
|---|---|
| tools | Tools used for checks are installed, at the versions expected |
| analyzer | Code that breaks the general rules or my own |
| static | The project's own checks that read the code |
| secrets | Passwords, keys and tokens in the files |
| commits | Passwords, keys and tokens in commits not yet published |
| notes | Passwords, keys, tokens and account numbers in the notes of those commits |

The unit tests are not part of it; they run separately, before each commit.

The script runs on its own each time we publish to GitHub.  If any check fails, nothing is published.

---

### Something the tests missed

A PowerShell command that changes things can be run with `-WhatIf`, which shows what it would do, without doing it.

We ran the backup clean-up function that way on a machine with no settings file yet, and it failed.  `-WhatIf` had been passed down to the step that creates the settings file, so the file was never created.  The next step failed looking for it.

Every test passed.  None of them tried that case.

We fixed it, and added a rule that flags any step `-WhatIf` could silently skip.  Pointed at the code as it was before the fix, the rule flagged the lines that caused the failure, and nothing else.

---

### Proving the stage

To prove the command works, we made a copy of the repository and planted one mistake at a time: code that breaks one of my standards, a fake token in a file, and a fake token in a commit note.  Each had to be caught by the check meant for it, and the clean copy had to pass.

The first attempt failed because the script doing the planting broke one of my standards.  The analyzer caught it.  We fixed the script, and every case then behaved as it should.

---

### The baseline

The Stack 0 measures, taken again at the end of this stage:

| Measure | Stack 1 | Stack 2 |
|---|--:|--:|
| Module code, lines | 2,553 | 2,588 |
| Unit test code, lines | 4,302 | 4,636 |
| Unit tests passing | 317 | 352 |
| Static analyzer findings | 79 | 82 |

The findings are counted the same way as at Stack 1.  The module code went from four findings to none.  The rest are in test files: some are fake passwords, there on purpose to test the code that handles real ones, and most are minor style findings.  The new checks leave test files out.

---

### The part worth keeping

The `-WhatIf` failure got past every test because nobody wrote a test for that case.

Once a rule exists, it does not depend on anyone thinking of the case.  It is applied to every line, including code the AI has not written yet.

---

### What comes next

Stack 3 is tests: proving every invariant from Stack 1 with a test, measuring how much of the code the tests reach, and running the code against a real Oracle database.

---

*Next in the series: Stack 3 — tests.*

---

[ai development stack — project page](/projects/ai-dev-stack-proj/)
