---
title: ai development stack — making ai-generated code correct, secure, and supportable
date: 2026-11-14
draft: false
tags:
  - ai
  - powershell
  - oracle
  - pester
  - testing
  - security
  - github-actions
summary: AI lets me build things well outside my specialty.  This project asks what a senior DBA has to put around that code to make it as correct, secure, and supportable as possible — and answers it by building the practices one layer at a time, on a real PowerShell module.
---

*On this page, "we" means me and Claude Code, the AI coding assistant I build with.*

## the question

What can a senior DBA do to make sure the AI-generated code they create is as correct, secure, safe, consistent, and supportable as possible?  And are there practices a senior software engineer would use as a matter of course that I should be using too?

## why it matters

AI has changed what I can build.  I am a database administrator, and I now routinely produce working code in areas that used to belong to other specialties.  That is the upside.  The downside is that "it works" is the only thing I can easily see, and it is the least interesting claim about a piece of code.

I already have habits.  I write invariants.  I lean heavily on Pester tests.  I lint, to a degree.  I run soak tests.  I keep a written set of coding standards that the AI reads at the start of every session.  However, most of it is applied when I remember to, and code review tends to happen after the fact rather than before the merge.

## the problem — inconsistency

Human habits applied inconsistently are not a system.  AI is not deterministic — without rule based guidance, AI will produce different outputs (different code), for the same request.

## the solution — a stack

To make the checks consistent and raise code quality, I need a set of them applied in layers, before the code ships.  Each one catches what the layer before it missed, and none of them depends on the author — human or AI — being careful on the day.

| Layer | What it is |
|---|---|
| 1. intent | What the code must do and must never do, specified before any code is generated |
| 2. agent instructions | The standards the AI is given, drawn from one canonical source |
| 3. deterministic checks | Linter, formatter, and secret scanning — the same answer every time |
| 4. tests | Unit, invariant, integration, and soak |
| 5. independent review | A second AI session that did not write the code, then a human |
| 6. enforced gate | Automation that runs the checks and blocks the merge when they fail |
| 7. agent containment | What the AI is allowed to touch, run, and read |
| 8. release and supportability | Versioning, changelog, packaging, and runbooks |
| 9. feedback loop | Every defect that escapes becomes a new check |

## the test bed

The stack gets built on [TACE.Oracle.Admin](https://github.com/scottyleblanc/TACE.Oracle.Admin), a small PowerShell module for Oracle DBAs that I originally wrote to learn how to publish to the PowerShell Gallery.  It is small on purpose.  A few functions from my Oracle backup module come across as working examples, chosen for what they exercise: one that only reads, one that changes state, and one that handles credentials.

That gives the stack real DBA code to prove itself against, with real security concerns, without drowning the project in a large codebase before the first check exists.

## how it gets built

One layer at a time, each one finished before the next begins.

The order is not the order of the table.  Enforcement comes before more rules — I already have plenty of standards, and the gap is that nothing applies them consistently, every time.  Deterministic checks come before anything judged by a model.  And the checks live in scripts inside the repository, so the automation that calls them stays thin and the whole thing can move to a different platform without a rewrite.

Every layer has to earn its place.  Before a stage is called done, we plant a deliberate defect on a throwaway branch — the kind of mistake that layer exists to catch — and the layer has to catch it.  If it does not, the stage is not finished.

## what comes after

Once the stack is running against that small set of functions, the next phase is to keep adding to the module, through the stack, until it is a genuinely useful public tool for DBAs.

## status

In progress.

| Stack | Builds layer | Name | Status |
|---|---|---|---|
| 0 | — | Setup and baseline | Complete |
| 1 | 1 | Intent | Complete |
| 2 | 3 | Deterministic checks | Complete |
| 3 | 4 | Tests | Complete |
| 4 | 6 | Enforced gate | Complete |
| 5 | 2 | Agent instructions | Complete |
| 6 | 5 | Independent review | Complete |
| 7 | 7 | Containment | Next |
| 8 | 8 | Release | Not started |
| 9 | 9 | Feedback loop | Not started |
| 10 | — | Wrap-up | Not started |

## build series

- [stack 0 — a baseline before any layer exists](/posts/ai-dev-stack-0-post/)
- [stack 1 — specify what the code must do](/posts/ai-dev-stack-1-post/)
- [stack 2 — one command for every static check](/posts/ai-dev-stack-2-post/)
- [stack 3 — testing the tests](/posts/ai-dev-stack-3-post/)
- [stack 4 — a change that fails cannot be merged](/posts/ai-dev-stack-4-post/)
- [stack 5 — giving the AI the rules](/posts/ai-dev-stack-5-post/)
- [stack 6 — deciding where review stops](/posts/ai-dev-stack-6-post/)
