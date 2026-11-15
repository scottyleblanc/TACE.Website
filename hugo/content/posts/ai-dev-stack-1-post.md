---
title: "ai development stack: stack 1 — specify what the code must do"
date: 2026-11-14T00:00:00
draft: false
aliases: ["/posts/stack-stage-1-post/"]
tags: ["ai", "powershell", "oracle", "pester", "testing", "security", "stack"]
summary: "second post in the ai development stack series: before building the later checks, I specified what the code must do, and what proves it."
---

### Intent

*This is the second post in a series documenting the build of an AI development stack — a set of layers placed around AI-generated code so it can be trusted.  The [project page](/projects/ai-dev-stack-proj/) covers the question and the full layer model.  [Stack 0](/posts/ai-dev-stack-0-post/) set up the test bed and the baseline.  This post is Stack 1: intent, the first layer.*

---

Every later layer in the stack is a check of some kind.  A linter, a test, a reviewer, a gate that blocks the merge.  Each one compares the code against something.

Stack 1 specifies that something.  The goal for the stage, as it reads in the project's task list:

> Every rule the code must follow is specified — the ratified standards, and an invariant block in every function naming what enforces each entry — and every gap found while specifying them is either fixed or accepted as a stated limitation.

Two kinds of rules, then.  Rules for all the code, and rules for each function.

---

### The standards

I already had a documented list of coding standards.  The AI reads it at the start of every session.  It had grown the way these lists do: some entries were firm rules, some were habits, and a few were not being followed at all.

So I went through every entry and decided which were real rules.  The ones that survived were cut down to one sentence and one example each.

One of them: a password is never passed to another program on its command line, where other users of the same machine can see it.

---

### The invariants

```text
in·var·i·ant  (noun)
    A function, quantity, or property that remains unchanged when a
    specified transformation is applied.

    Computing or Code: a condition that must always hold true at a
    given point in a program.  Examples include a loop invariant,
    which is true before and after every iteration.

    Database: an integrity constraint plays this role —
    something like "every row in ORDERS references a valid
    CUSTOMER" has to hold after every committed transaction.
```

The module is made of functions, each a small piece of code that does one job.  At the top of every function there is now a block that sets out what must be true before it runs, what it must never do, and what it guarantees when it finishes.

Next to each entry is what proves it: a test, a check in the code itself, or a note that nothing proves it yet.

One entry, from the function that starts RMAN, Oracle's backup tool:

```text
[SEC] S1 No password is placed in the process argument list, in any mode.
    Test: none yet.
```

It is the password standard, stated for the one place it matters most.  The second line is the honest part.  No test proves it yet, and the block says so rather than leaving it assumed.

The blocks live inside the code, not in a separate document.  When the code changes, its invariants are right there to change with it.

---

### What specifying them turned up

Spelling out what each function claims to do showed that a few of them did not.  Each one was either fixed or recorded as a known limitation.  None of them was left unstated.

---

### Proving the stage

Like every stage, this one had to catch a planted defect before it could be called done.

I added a function with no invariant block, and another whose block was badly formed.  The automatic check rejected both.

---

### The baseline

The Stack 0 measures, taken again at the end of this stage:

| Measure | Stack 0 | Stack 1 |
|---|--:|--:|
| Module code, lines | 1,883 | 2,553 |
| Unit test code, lines | 3,847 | 4,302 |
| Unit tests passing | 291 | 317 |
| Static analyzer findings | 74 | 79 |

Most of the new module code is the invariant blocks themselves, which sit inside the code as comments.  The findings in the module code are unchanged at four.  The five new ones are a minor style rule, in new test files.

---

### The part worth keeping

A test checks only what its author thought of.  When an AI writes both the code and its tests, the same blind spot can turn up in both, and every test still passes.

A specification of what the code must do is independent of both.  The code can be checked against it, and so can the tests.

It also gives the later layers something to check against.  One check already exists: it reads every file in the repository and fails if it finds an account number or an access key.  It can do that only because the rule — nothing that identifies my systems goes into a public repository — was documented first.

---

### What comes next

Stack 2 is deterministic checks: bringing every automatic check under one command that gives the same answer every time it runs.

---

*Next in the series: [Stack 2 — one command for every static check](/posts/ai-dev-stack-2-post/).*

---

[ai development stack — project page](/projects/ai-dev-stack-proj/)
