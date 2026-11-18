---
title: "ai development stack: stack 6 — deciding where review stops"
date: 2026-11-17T12:00:00
draft: false
tags: ["ai", "powershell", "oracle", "testing", "stack"]
summary: "seventh post in the ai development stack series: every change is now reviewed by a second AI model before it merges.  The first design reviewed again after every fix, and never settled.  Now it runs once."
---

### Independent review

*This is the seventh post in a series documenting the build of an AI development stack — a set of layers placed around AI-generated code to make it as correct, secure, and supportable as possible.  The [project page](/projects/ai-dev-stack-proj/) covers the question and the full layer model.  [Stack 5](/posts/ai-dev-stack-5-post/) gave the AI my standards before it writes code.  This post is Stack 6: independent review, the layer that has every change examined by someone (or something) other than its author.*

*In this post, "we" means me and Claude Code, the AI coding assistant I build with.*

---

Stack 5 ended on a change a check could not judge.  The secret scanner flagged a made-up password in a test, and the AI changed the password until the scanner stopped matching it.  The check could report that the scanner was quiet.  Whether that was the right change needed someone to look at it.

The checks from the earlier stages compare the code against rules a machine can test.  Some of my rules need judgement instead.  One example: text the module sends to RMAN, Oracle's backup tool, may contain only values that have been checked so they cannot change the command.  A machine can find the line.  Deciding whether the check on the value is strong enough takes a reviewer.

Stack 6 adds that reviewer to every pull request, a proposed change that GitHub shows on its own page before it is merged.

---

### The review

The reviewer is a second AI model, started fresh for each review.  It is given the change, the list of files and the commit notes (the message saved with each change), and a document that sets the order it reviews in: what the change claims to do first, then the tests, then the code.  The code comes last, so it is judged against what it is meant to do.

It is kept apart from the session that wrote the change:

- **No shared memory.**  It does not see the author's conversation, memory or instruction files.
- **Read only.**  It can read the files of the reviewed version and nothing else.  It cannot run commands or change files.
- **A fixed answer format.**  Each finding has a severity, the rule it breaks, the file and line, and a suggested fix.

| Severity | Meaning |
|---|---|
| High | A security rule broken, data changed or lost when it should not be, or a wrong result on a normal path |
| Medium | Another rule broken, or a defect on a path that is rarely taken |
| Low | A document out of step with the code, unclear code, or a gap in a test that does not hide a defect |

The review is saved as a record in the repository.  The author answers each finding with one of four words and a reason: Fixed (with the commit that fixes it), Rejected, Accepted or Deferred.

The checks GitHub runs on each pull request, from Stack 4, gained one more.  It fails a pull request whose review record is missing, does not cover the whole change, or has a finding with no answer.  It does not fail on the findings themselves.  A model's judgement does not decide what merges; the checks do, and they give the same answer every time.

---

### Proving the stage

The planted defect for this stage had to pass every check, so that only the review could catch it.

We added an option to the function that deletes obsolete backups, to limit it to one kind of storage.  The value is placed straight into the RMAN command.  Its only check is that it is not empty.  So a value such as `DISK; DELETE NOPROMPT BACKUP` passes, and RMAN would delete every backup, without asking.

It was planted the way a careless author would make it.  The help text, the function's stated promises, its test and the list of promises were all updated to agree with it.  The checks passed it: all 7 of them, including the 405 unit tests.

The review ran three times on that change:

| Run | Findings | Reported | Severity | Cost (US$) |
|:-:|:-:|:-:|:-:|:-:|
| 1 | 6 | Yes | High | 0.56 |
| 2 | 5 | Yes | High | 0.43 |
| 3 | 5 | Yes | High | 0.41 |

Each run took about a minute.  Each one named the line, a value that gets through, and a fix: allow only the valid storage types.

Two of the runs found something else.  In Stack 3 we broke the code on purpose to prove each test would notice.  The planted change had moved the line those breaks look for, so the proof no longer worked for three security promises.  That proof is too slow to run with every change, so nothing else would have reported it until its next run.

---

### Reviewing its own pull request

The first design required a new review after any change to the pull request.  The record had to name the last commit.  So any fix, even a one-line change to a document, meant a new review of the whole change, and, because this change touched the module's version, a new run of the tests against the real Oracle database, whose result must be the last commit.

The pull request that built this stage went through eight rounds of that:

| | |
|---|--:|
| Reviews | 8 |
| Findings | 23 |
| Runs against the real database | 2 |
| Cost of the reviews | US$8.23 |

Every round found something new.  I stopped it.  This was a simple change, with relatively few files.  After one or two reviews, findings should not keep coming up, and the time and money it cost was too much.

---

### Why it never settled

We sorted the 23 findings by where they came from:

| Where the finding came from | Findings |
|---|--:|
| The first review | 4 |
| The same Low finding, reported again in rounds 2 to 7 | 6 |
| Code written to fix an earlier finding | 6 |
| Real problems in the original code that the first review missed | 4 |
| A gap in the fix for the first review's Medium finding | 1 |
| A change made to the review checklist during the rounds | 2 |

Two things explain it.

**Each review finds a different part of the real problems.**  A fresh review is a new sample of the change, not a closer look at the last one.  Repeating it samples again; it does not settle.  Two of the problems the first review missed were Medium: the reviewer was not given the commit notes, and the new review check passed when git could not list what had changed.  The Stack 4 check for the database test result had the same flaw.  A check that passes when it cannot look is the same kind of failure Stack 4 set out to prevent.  Both are fixed.

**Fixing every finding writes new code to review.**  Lows included, each fix was new code for the next round to find fault with.  12 of the 19 findings after the first review were in fix code, or repeated a finding already answered.

---

### Making it simpler

Before changing the design, I asked for the proposed change to be tested against the records of the first two reviews.  It would have stopped after round 2.  It would also have missed the two real Medium problems in the original code.  So limiting the reviews limits the cost; it does not make one review find more.  That limit is stated in the review document and in the record of this stage.

Then I asked whether it could be made simpler still, without changing the result.  The rule at the root of the cost was that nothing could change after the reviewed commit.  Dropping it gave one review per pull request.  Fixes now come in later commits, and each finding's answer names the commit that fixed it.  The machinery that supported repeat reviews went with it, about 60 lines of the review script.

The checklist for the person reviewing the pull request changed the same way.  It started with thirteen items, grouped under intent, tests, the code and the findings, covering every rule a reviewer judges.  No person can confirm that many rules line by line by reading a change to 23 files.  Items such as "the checks passed" are decided by a machine, not a person.  It went to four items, briefly five when fixes moved after the review, then to two:

- **Intent.**  The change does what it says, and nothing else I can see.
- **Findings.**  I read every finding and agree with each answer.

Every other rule now has a named owner: a check, the AI reviewer, or the author.

---

### Which model

I suspected the reviewer model was part of the problem, finding something new each time because it kept looking.  So we compared two models on the planted defect (three runs each) and on the original pull request (two runs each):

| Reviewer | Planted defect reported as High | Cost per run (US$), planted defect / pull request |
|---|:-:|:-:|
| Claude Sonnet 5.5, medium effort | 3 of 3 | 0.09 to 0.12 / 0.28 to 0.30 |
| Claude Opus 5.5, medium effort | 3 of 3 | 0.32 to 0.38 / 0.63 to 0.75 |
| Claude Opus 5.5, high effort | 3 of 3 | 0.41 to 0.56 / 1.04 |

The high-effort runs were the earlier ones, with an earlier version of the review instructions, so that row is a rough guide.

Every reviewer caught the planted defect.  Opus also found real problems Sonnet did not, such as the broken proof described above.  Its extra findings were real.  The new findings in every round came from the process of reviewing until nothing was left, not from the model.  The default is Opus at medium effort: as thorough as high effort on these runs, for about 30% less.

---

### The first review under the new rules

| | |
|---|--:|
| Reviews | 1 |
| Findings | 7 (2 Medium, 5 Low) |
| Fixed, in one commit | 5 |
| Accepted, with a reason | 2 |
| Cost | US$1.13 |

No second review.  I read the answers and agreed with each, and the pull request merged.

---

### What was set aside

These are recorded in the project's task list, to come back to:

- Re-evaluating the rigor that was removed: checking that the fix commits do what their findings asked, combining two reviews, and a person reading the riskiest parts of the change.
- A review by a model from another company.  The reviewer is the same family of model as the author, and can share its blind spots.
- More planted defects for the new check.

---

### The baseline

The baseline measures, taken again at the end of this stage:

| Measure | Stack 0 | Stack 1 | Stack 2 | Stack 3 | Stack 4 | Stack 5 | Stack 6 |
|---|--:|--:|--:|--:|--:|--:|--:|
| Module code, lines | 1,883 | 2,553 | 2,588 | 2,693 | 2,693 | 2,693 | 2,693 |
| Unit test code, lines | 3,847 | 4,302 | 4,636 | 5,372 | 5,372 | 5,372 | 5,372 |
| Unit tests passing | 291 | 317 | 352 | 405 | 405 | 405 | 405 |
| Static analyzer findings | 74 | 79 | 82 | 110 | 110 | 110 | 110 |
| Change review | none | none | none | none | none | none | in place |

Stack 6 did not change what the module does.  The only change to the module code was its version number.  The review script, the new check and the review document sit outside the module.

---

### The part worth keeping

The review caught what every check passed, three times out of three.  The checks can only confirm that the parts of a change agree with each other.  The reviewer asked whether they were right.

A review is a sample, not a proof.  Run it again and it finds different things, and fixing everything it finds gives the next one more to find.  So the place to stop has to be decided before the review starts.  Here, that is one review per pull request, a person who agrees with every answer, and the checks underneath that do not change their answer.

---

### What comes next

Stack 7 is containment: what the AI is allowed to touch, run and read.  It starts with a finding recorded in Stack 5: in one mode, a command that deleted a file ran without asking, while a script that only reads files was refused.

---

| | |
|---|---|
| Previous | [Stack 5 — giving the AI the rules](/posts/ai-dev-stack-5-post/) |
| Next | [Stack 7 — what the AI can reach](/posts/ai-dev-stack-7-post/) |

---

[ai development stack — project page](/projects/ai-dev-stack-proj/)
