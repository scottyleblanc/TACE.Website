---
title: "ai development stack: stack 3 — testing the tests"
date: 2026-11-16T00:00:00
draft: false
tags: ["ai", "powershell", "oracle", "pester", "testing", "security", "stack"]
summary: "fourth post in the ai development stack series: we broke each promise in the code on purpose to see whether its tests noticed, and fixed the tests that did not."
---

### Tests

*This is the fourth post in a series documenting the build of an AI development stack — a set of layers placed around AI-generated code to make it as correct, secure, and supportable as possible.  The [project page](/projects/ai-dev-stack-proj/) covers the question and the full layer model.  [Stack 2](/posts/ai-dev-stack-2-post/) brought the checks that read the code under one command.  This post is Stack 3: tests, the first layer that runs the code.*

*In this post, "we" means me and Claude Code, the AI coding assistant I build with.*

---

Stack 1 gave every function a list of promises (invariants), and next to each promise, the test that proves it.

A test proves a promise only if it would fail when the promise is broken.  A test that is not checking the right thing passes too, and from the outside the two look the same.  When an AI writes both the code and the tests, nobody may ever find out which kind they have.

Stack 3 sets out to find out.  The aim is that every promise is proven by a test that fails when the promise breaks.

---

### Counting what is proven

The first step was a list of every promise, with the test that proves it.  A script builds the list from the code, so it cannot fall out of date.

Some promises had been counted as kept because the code enforces them, for example by refusing a value of the wrong type.  For many of them, no test showed that the enforcement worked.  Once the list required a test for every promise, the number of unproven promises went up before it came down.  The code had not changed; the count had become accurate.

The promise quoted in the Stack 1 post, from the function that starts RMAN, Oracle's backup tool, now names its test:

```text
[SEC] S1 No password is placed in the process argument list, in any mode.
    Test: 'S1 no password reaches the process argument list (<Mode>)'.
```

---

### Breaking the code on purpose

The only way to know a test would fail when a promise breaks is to break the promise and run the test.

We wrote a script that does this.  It makes a temporary copy of the repository, breaks one promise in the copy, and runs the tests cited for that promise.  If one of them fails, the break was caught.  If they all pass, those tests prove nothing about that promise.  Each break is called a mutation, and the method is called mutation testing.  The repository itself is never changed.

The first run covered every security promise, and some of the breaks passed every test meant to catch them:

- **A test with nothing to leak.**  A function promises that the message it returns never contains the password.  Its test ran without a password.  We made the function put the credential in the message, and the test still passed.
- **A test that compared the wrong values.**  Several functions promise not to change the PowerShell session that calls them, such as which database it points at.  Each test compared the session before and after the call.  Earlier tests in the same file had already made the change, so before and after matched.  Run on its own, the same test failed.
- **A test that never reached the code.**  One function removes passwords from Oracle error text.  Its test supplied text the function did not treat as an error, so the line that removes passwords never ran.

Every gap was in the tests.  None was in how the module handles passwords.

We fixed each test and ran the script again until every break was caught:

| Run | Breaks | Caught | Passed every test |
|---|--:|--:|--:|
| First run, security invariants | 36 | 22 | 14 |
| After the fixes | 44 | 44 | 0 |

The second run adds breaks for other promises whose tests we fixed at the same time.

---

### What a test cannot reach

Some promises are about how the code is built, not what it does.  One says that only one function in the module may turn a protected password back into plain text.  A test runs the code, and it behaves the same whichever function does the conversion.

For those promises we wrote checks that read the code instead of running it.  They run with the other checks from Stack 2, and each one was broken in a copy to show it notices.

---

### Against a real database

Unit tests replace Oracle with a fake.  They show what the code does with the answers it expects, not with the answers Oracle gives.

There is now a second set of tests that runs against a real Oracle database on my own machine.  It takes real backups, and runs `DELETE OBSOLETE`, the RMAN command that removes backups no longer needed.

Those tests delete files, so five checks run first, and any one of them stops the run: the machine is on an approved list, a setting turns the tests on, the local settings file is complete, the database is not on a list of protected names, and the folder for test backups exists.

The first real run deleted an older backup that was there before the tests began.  That is what `DELETE OBSOLETE` does: it works on the whole database, not only on the backups the tests made.  That is why the tests run only where the checks above allow.

These tests cannot run on GitHub, which has no Oracle database.  Each run records its result in a file that is committed with the change.  The file shows the result, but it cannot prove the run happened, since anyone could edit it.  That limit stays open.

---

### Something the tests missed

We also measured how much of the code the tests run, which is called coverage, and set a floor it cannot fall below.

Writing tests for the lines no test reached turned up a real defect.  `oraset`, the command that sets up the session for a database, crashed when it found no Oracle database on the machine, instead of saying so.

The crash came from a change made earlier in this same stage.  Every test had passed.

---

### Proving the stage

The planted defect for this stage changes what the code does, not how it looks.  One line is removed from the function that reports the latest backup.  Without that line, the function picks a backup by its number instead of by when it finished.  What is left is still valid, and passes every check that reads it.

The command from Stack 2 now has an option that runs the unit tests as well.  With that option, the command failed on the unit tests alone, and only one test failed: the test cited for that promise.

---

### The baseline

The baseline measures, taken again at the end of this stage:

| Measure | Stack 0 | Stack 1 | Stack 2 | Stack 3 |
|---|--:|--:|--:|--:|
| Module code, lines | 1,883 | 2,553 | 2,588 | 2,693 |
| Unit test code, lines | 3,847 | 4,302 | 4,636 | 5,372 |
| Unit tests passing | 291 | 317 | 352 | 405 |
| Static analyzer findings | 74 | 79 | 82 | 110 |
| Change review | none | none | none | none |

- The last row counts static analyzer findings: problems reported by PSScriptAnalyzer, counted the same way at every stage.
- At Stack 0, 4 of the 74 were in the module code; Stack 2 fixed them.
- All 110 at Stack 3 are in test files.
- Of the 28 added to stack 3, most are minor style findings, and some are fake passwords.  They are there on purpose to test the code that handles real ones.

---

### The part worth keeping

A passing test says the code did what the test checked.  Whether the test checked anything is a separate question, and breaking the code is the way to answer it.

Every gap we found was in a test that had passed from the day it was added.

---

### What comes next

Stack 4 is the enforced gate: GitHub runs every check on each proposed change, and a change that fails cannot be merged.

---

| | |
|---|---|
| Previous | [Stack 2 — one command for every static check](/posts/ai-dev-stack-2-post/) |
| Next | [Stack 4 — a change that fails cannot be merged](/posts/ai-dev-stack-4-post/) |

---

[ai development stack — project page](/projects/ai-dev-stack-proj/)
