---
title: "ai development stack: stack 1 — specify what the code must do"
date: 2026-11-14T00:00:00
draft: false
tags: ["ai", "powershell", "oracle", "pester", "testing", "security", "stack"]
summary: "second post in the ai development stack series: before adding any automatic check, I specified what the code must do, and what proves it."
---

### Intent

*This is the second post in a series documenting the build of an AI development stack — a set of layers placed around AI-generated code so it can be trusted.  The [project page](/projects/ai-dev-stack-proj/) covers the question and the full layer model.  This post is Stack 1: intent, the first layer.*

---

### What

Stack 1 specifies what the code is supposed to do, in two forms.

**Coding standards.**  I already had a list of them.  Some were firm rules, some were habits, and a few were not being followed.  I kept the ones that are real rules and reduced each to one sentence with one example.  One of them: a password is never passed to another program on its command line, where other users of the same machine can see it.

**Promises (invariants) for each piece of code.**  The module is made of functions, each a small piece of code that does one job.  At the top of every function I set out what must be true before it runs, what it must never do, and what it guarantees when it finishes.  Next to each one is what proves it: a test, a check in the code itself, or a note that nothing proves it yet.

One of the promises (invariants) in the function that starts Oracle's backup tool:

```text
[SEC] S1 No password is placed in the process argument list, in any mode.
    Test: none yet.
```

It is the password standard above, stated for the one place it matters most.  The second line records that no test proves it yet, so the gap is on the page rather than assumed away.

Writing them turned up places where existing code did not do what it claimed.  Each was fixed or recorded as a known limitation.

---

### Why

**A check needs something to check against.**  The later stages add automatic checks.  One already exists: it reads every file in the repository and fails if it finds an account number or an access key.  It can do that only because the rule it enforces, that nothing identifying my systems goes into a public repository, was specified first.  Without a rule, there is nothing to compare against.

**Passing tests do not prove the code is right.**  A test checks only what its author thought of.  When an AI writes both the code and its tests, the same blind spot can appear in both.  A specification of what the code must do gives a separate reference that the code and the tests can each be checked against.

---

### How

**The promises (invariants) live inside the code.**  They sit at the top of each function, not in a separate document, so the code and its promises change together.

**Every promise (invariant) says what proves it.**  When a promise names a test, that test must fail if the promise is broken.  When nothing proves a promise yet, it says so, and the gap stays visible.

**The stage had to catch its own mistakes.**  I deliberately added a function with no promises (invariants), and another whose promises were badly formed.  The automatic check rejected both.

---

### The baseline

The measures from Stack 0, taken again at the end of this stage:

| Measure | End of Stack 0 | End of Stack 1 |
|---|--:|--:|
| Module code, lines | 1,883 | 2,553 |
| Unit test code, lines | 3,847 | 4,302 |
| Unit tests passing | 291 | 317 |
| Static analyzer findings | 74 | 79 |

Most of the new module code is the promises (invariants) themselves, which sit inside the code as comments.  The analyzer findings in the module code are unchanged at four.  The five new findings are a minor style rule, in new test files.

---

### What comes next

Stack 2 brings every automatic check under one command that gives the same answer every time it runs.

---

*Next in the series: Stack 2 — deterministic checks.*

---

[ai development stack — project page](/projects/ai-dev-stack-proj/)
