---
title: "ai development stack: stack 0 — a baseline before any layer exists"
date: 2026-11-14T00:00:00
draft: false
tags: ["ai", "powershell", "oracle", "pester", "testing", "security", "stack"]
summary: "first post in the ai development stack series: before building a single check, I set up the test bed, brought in real code that handles credentials, and wrote down where things stand."
---

### Measure First

*This is the first post in a series documenting the build of an AI development stack — a set of layers placed around AI-generated code so it can be trusted.  The [project page](/projects/ai-dev-stack-proj/) covers the question and the full layer model.  This post is Stack 0: no layers yet, just the ground they will stand on.*

---

The plan is to build nine layers of checking, one at a time, and to prove each one by planting a defect it is supposed to catch.  That only means something if I know where things stood before the first layer went in.

So Stack 0 builds nothing.  It sets up the test bed and writes down the starting numbers.

---

### The test bed

The stack is being built on [TACE.Oracle.Admin](https://github.com/scottyleblanc/TACE.Oracle.Admin), a small PowerShell module with two functions: one discovers the Oracle instances on a host, the other sets the session environment for one of them.  No passwords.  No child processes.  Nothing destructive.

Which makes it a poor test for a stack whose whole purpose is catching dangerous mistakes.

So I brought across three working examples from my Oracle backup module, chosen for what they exercise rather than for what they do:

- **One that only reads** — it reports the most recent RMAN backup for a database.
- **One that changes state** — it deletes obsolete backups, behind a confirmation prompt.
- **One on the credential path** — the helper that starts RMAN and hands it a password through standard input, never on the command line.

With the helpers they depend on and their existing unit tests, that came to eight source files and six test files.

---

### The baseline

| Measure | Before | After |
|---|--:|--:|
| Module code, lines | — | 1,883 |
| Unit test code, lines | — | 3,847 |
| Unit tests passing | 117 | 291 |
| Static analyzer findings | 4 | 74 |

Seventy of the 74 findings are in test files, most of them test passwords written as plain text.  Four are in the module code itself.

Those are the numbers every later stage gets measured against.

---

### What I did not fix

Bringing the code across showed gaps, in the code and in the documents around it.  I fixed almost none of them.

The documents were corrected, because they are supposed to describe the present.  The code was left alone, on purpose.  Every gap is something a later layer should catch by itself, and if I tidy them by hand now I throw away the evidence.

They are written down in a baseline file in the repository instead, next to the numbers.

---

### The part worth keeping

It is tempting to treat setup as the thing you get through on the way to the real work.  Copy the files, see the tests pass, move on.

But 291 passing tests say only that the code does what the tests ask.  They say nothing about whether the documents around it are still true, or whether something in it is quietly unfinished.  The tests were green the whole time.

That is the uncomfortable part of working with AI at speed.  The code arrives faster than the attention needed to read it, and green tests make it easy to stop looking.  The stack is an attempt to make the looking happen whether or not I remember to do it.

---

### What comes next

Stack 1 is intent: writing down, in plain language, what each function must do and must never do, and deciding which of my standards are real rules and which are habits.  Nothing gets enforced until that exists — a gate can only hold a line that someone has drawn.

---

*Next in the series: Stack 1 — intent.*

---

[ai development stack — project page](/projects/ai-dev-stack-proj/)
