---
title: "ai development stack: stack 5 — giving the AI the rules"
date: 2026-11-16T19:00:00
draft: false
tags: ["ai", "powershell", "oracle", "testing", "stack"]
summary: "sixth post in the ai development stack series: the AI is now given my standards before it writes code, built from the same source the checks enforce. On this repository, it made no measurable difference."
---

### Agent instructions

*This is the sixth post in a series documenting the build of an AI development stack — a set of layers placed around AI-generated code so it can be trusted.  The [project page](/projects/ai-dev-stack-proj/) covers the question and the full layer model.  [Stack 4](/posts/ai-dev-stack-4-post/) made the checks a condition of merging: a change that fails them cannot reach the main branch.  This post is Stack 5: agent instructions, the layer that gives the AI the rules before it writes the code.*

*In this post, "we" means me and Claude Code, the AI coding assistant I build with.*

---

My standards are in the repository, one file each for coding, security, testing, documentation and invariants (the promises each function makes).  The checks enforce them after the code is written.

The AI that writes the code does not see those files unless it goes and reads them.  Stack 5 gives it the rules before it starts.  The aim was also to measure whether that changes the result.

---

### One file, built from the standards

AI coding tools look for a file named `AGENTS.md` at the top of a repository and read it as instructions before they start work.

We did not write that file by hand.  A script builds it from the standards files and copies every rule word for word: the rule, its example, and what enforces it.  Shortening a rule can change what it means, so nothing is reworded.

A copy can fall out of step with its source.  A new check builds the file again and compares it with the one in the repository.  If they differ, the check fails.

To prove it, we added a rule to the testing standard and did not rebuild the file.  That check failed, and no other.  Without it, the AI would have been working from rules that were no longer current.

Both AI tools I use read the same file.  Cursor reads it directly.  Claude Code reads it through one line in a local settings file, because a shared instructions file higher up on my machine stops it looking for `AGENTS.md` on its own.

---

### Did it make a difference?

We gave the AI the same small task six times: three times without the file and three times with it.  The task was to add a function that reads `tnsnames.ora`, the Oracle file that lists the names used to connect to databases, and returns those names, with its tests.

Each run started from a clean copy of the repository as it stood at the end of Stack 4.  Every other instruction file and the AI's memory were turned off, so the file was the only difference.  Each finished change then went through the checks.

| | Without the file | With the file |
|---|---|---|
| Finished change passed every check | 3 of 3 | 3 of 3 |
| A check failed the first time the AI ran the checks on its own code, and the AI had to fix it | 0 of 3 | 2 of 3 |
| Standards files the AI opened | 5 of 6, every run | None |
| Median time | 7.4 minutes | 8.9 minutes |
| Median cost | US$1.86 | US$1.99 |

There was no measurable difference.  Without the file, every run read the standards before writing any code, and the existing functions already show them applied.  With the file, the AI opened none of the standards files, but it took no fewer steps.

Where the two sets differed, the runs with the file came out slightly worse.  Three runs each way cannot tell that apart from chance, so it is not a finding against the file either.

Some rules need a reviewer, because no check can test them; for example, a list result is wrapped so that a single item is still treated as a list.  I checked each finished change against those rules by hand.  Both sets met them.

---

### What the checks could not judge

In both runs where the AI had to fix its code, the failing check was the secret scanner, which looks for passwords and tokens, and the cause was the same rule: every test file must prove that no password reaches the messages a function returns.  To test that, the AI put made-up passwords in the test file, such as `'Tns_S3cret_Pw9'`.  The scanner flagged them.

Each time, the AI changed the made-up password until the scanner stopped matching it.  The replacements included `'TnsTestPass1'`.

Nothing leaked, because the values were fake.  But a check can only report that the scanner is now quiet.  Whether the change that made it quiet was the right one needs someone to look at it.  That is the next stage.

---

### What the setup found

The first pair of runs measured the wrong thing.  Under the first rules for what the AI was allowed to run, the run with the file could not call the checks, and it stopped with a check failing.  That pair measured the permission rules, not the instructions, so we set it aside, fixed the rules and started again.

Testing those rules found something else.  In the mode where the AI's file edits are accepted without asking, a command that deleted a file also ran without asking, while a script that only reads files was refused.  That is recorded for Stack 7, containment, which sets what the AI may run and read.

---

### The baseline

The baseline measures, taken again at the end of this stage:

| Measure | Stack 0 | Stack 1 | Stack 2 | Stack 3 | Stack 4 | Stack 5 |
|---|--:|--:|--:|--:|--:|--:|
| Module code, lines | 1,883 | 2,553 | 2,588 | 2,693 | 2,693 | 2,693 |
| Unit test code, lines | 3,847 | 4,302 | 4,636 | 5,372 | 5,372 | 5,372 |
| Unit tests passing | 291 | 317 | 352 | 405 | 405 | 405 |
| Static analyzer findings | 74 | 79 | 82 | 110 | 110 | 110 |

Stack 5 did not change what the module does.  The only change to the module code was its version number.  The script that builds the file and the check that compares it sit outside the module.

---

### The part worth keeping

On this repository, the checks made the result correct with or without the file, because the AI ran them and fixed what they reported.  The file saved the AI from looking up the standards; it did not prevent a defect.

That depends on the repository.  Here, the standards and code that follows them were already there to read.  In a repository whose code does not follow its own rules, the file is the only place the AI is told the rules that need a reviewer.

---

### What comes next

Stack 6 is independent review: no change is examined only by its author.  Every pull request gets a template, a checklist for the person reviewing it, and a review by a second AI model.

---

*Next in the series: [Stack 6 — deciding where review stops](/posts/ai-dev-stack-6-post/).*

---

[ai development stack — project page](/projects/ai-dev-stack-proj/)
