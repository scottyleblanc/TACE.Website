---
title: "ai development stack: stack 9 — turning missed defects into checks"
date: 2026-11-19T15:00:00
draft: false
tags: ["ai", "powershell", "oracle", "security", "stack"]
summary: "tenth post in the ai development stack series: every defect that got past the checks now ends in a new check that catches it.  A drill gave a new AI session a planted defect and nothing but the repository, and it found a wider defect of its own."
---

### Feedback loop

*This is the tenth post in a series documenting the build of an AI development stack — a set of layers placed around AI-generated code to make it as correct, secure, and supportable as possible.  The [project page](/projects/ai-dev-stack-proj/) covers the question and the full layer model.  [Stack 8](/posts/ai-dev-stack-8-post/) added checks on what goes out in a release.  This post is Stack 9: the feedback loop, the layer that learns from what the other layers missed.*

*In this post, "we" means me and Claude Code, the AI coding assistant I build with.*

---

Every layer so far has been a check of some kind: a standard, a test, a review, a rule about what the AI may run.  None of them is complete.  Sooner or later a defect gets past all of them and is found some other way: by a newer check, by a review, or by a person reading the code.

We call that an escaped defect.  Stack 9 adds one rule for them: every escaped defect ends in a new check that fails on it.  Finding the defect once is not enough.  The same defect must not be able to come back unnoticed.

The stage also has a second part, a drill.  We planted a defect and gave a new AI session nothing but the repository, to see whether the documents and tests in it are enough to find and fix it.

---

### The log

The escaped defects are recorded in one table in the repository.  Each entry says what was wrong, which check should have caught it and why it did not, and which check catches it now.

Two entries came from Stack 8.  Two functions had no version line in their help text, and the version check skipped them.  The review check accepted the previous pull request's review record.  Both were already caught by checks added in Stack 8.

I decided those two do not count for this stage.  Stack 9 had to turn a defect into a check of its own.

I also decided to keep this stage minimal: the checks do not enforce the log's rule.  Review does.

---

### A rule that could be deleted

In Stack 7, we committed two settings files that set what the AI coding tools may run and read in this repository.  One of the rules blocks `git push`, the command that sends changes to GitHub.  The independent review of Stack 7 pointed out that nothing checked these files.  Anyone, including the AI, could delete a rule, and every check would still pass.

This was the entry Stack 9 converted.  A data file now lists the rules each settings file is documented to have.  A new check fails when:

- a file is missing a rule that blocks something
- a file has a rule that allows something the list does not include

A file may add stricter rules.  Loosening one means changing the list as well, in the same change, where a reviewer sees it.

---

### A password partly shown

The module hides passwords in any text it returns or logs.  It looks for a connection string of the form `user/password@service` and replaces the password with `***SCRUBBED***`.

While choosing a defect for the drill, we read the unit test for this function.  Its test password was `S3cr3tP@ss!`, which contains an `@`.  The function stopped the password at the first `@`, so the result was:

```
backup_user/***SCRUBBED***@ss!@ORCL_SVC
```

Part of the password was still visible.  The test passed, because it only checked that the whole password was gone.

The function now treats everything up to the last `@` as the password, and the test checks the exact output.  This became the fourth entry in the log.

---

### The drill

The drill tests a different question: if the person who built this module were gone, could someone new fix it using only what is in the repository?

We made a copy of the repository with no git history, none of the notes I keep between sessions, and none of the AI's memory from earlier work.  In that copy we planted one defect.  The function that deletes old backups returned the raw text of an error to its caller, instead of the hidden version.  An error that contained a connection string would hand the password back.

We then started a new Claude Code session in the copy, with no one watching, under the same permission rules as normal work.  Its only instruction was:

> A defect has been planted in this repository.  Find it and fix it.  Report what was wrong, how you found it, what you changed, and how you know the fix is right.

It was not told where the defect was or how it would show.

| Measure | Result |
|---|---|
| Found and fixed | Yes |
| Time | 5 minutes 42 seconds |
| Steps | 14 |
| Commands refused by the permission rules | 2 |

The session ran the full set of checks first, as the repository's instructions for AI tools tell it to.  One unit test failed.  Its name starts with the ID of the requirement it proves, and that requirement is stated at the top of the function, which led straight to the defect.  The session fixed the code, not the test, and the fix matched the original code.  It named the security standards it was applying without opening a document, because the generated instruction file from Stack 5 is loaded when a session starts.

The two refused commands were outside the rules from Stack 7.  The session used its file-reading tools instead.

---

### What the drill found

At the end of its report, the session added something it had not been asked for.  Six other places in the module also used raw error text: two put it in the message they return, and four passed it on in a new error.  One of my security standards says that every error message is cleaned before it leaves a function.  Two of the six were recorded in the code as accepted exceptions, because nothing in those functions handles a password.

I decided to fix all six rather than keep the exceptions, and to add a check so the same pattern cannot come back.

All six now clean the error text.  A new check reads the module code and fails on any use of an error's text that does not go through the cleaning function first.  This is the fifth entry in the log, and the widest check the stage added.

---

### Proving the stage

We made a copy of the repository and planted the new defect:

| Planted | Expected | Result |
|---|---|---|
| The rule that blocks `git push` is removed from the AI settings | Fails on the static checks only | As expected |

The first run stopped after this case.  The settings folder is excluded from git, and the one settings file in it was added to the repository on purpose, so the test copy's git did not know the file and could not put it back.  The case now restores the file itself.

The full set of planted defects, 20 in all, passed and takes about 25 minutes.

---

### The baseline

The baseline measures, taken again at the end of this stage:

| Measure | Stack 3 | Stack 4 | Stack 5 | Stack 6 | Stack 7 | Stack 8 | Stack 9 |
|---|--:|--:|--:|--:|--:|--:|--:|
| Module code, lines | 2,693 | 2,693 | 2,693 | 2,693 | 2,693 | 2,699 | 2,711 |
| Unit test code, lines | 5,372 | 5,372 | 5,372 | 5,372 | 5,372 | 5,372 | 5,372 |
| Unit tests passing | 405 | 405 | 405 | 405 | 405 | 405 | 405 |
| Static analyzer findings | 110 | 110 | 110 | 110 | 110 | 110 | 110 |
| Change review | none | none | none | in place | in place | in place | in place |
| Agent privileges | none | none | none | none | in place | in place | in place |
| Version checks | none | none | none | none | none | in place | in place |
| Escaped-defect checks | none | none | none | none | none | none | in place |

The twelve new lines of module code are the cleaning of error text in six functions, the password fix, and the updated rule statements in two functions.

---

### The part worth keeping

The drill was meant to test the documents.  It passed that test, and it also found a defect that none of the checks, reviews or earlier stages had.

Both new defects were found by reading the code and tests closely.  The password test passed while part of the password showed.  Two functions were recorded as safe because of what they do today.  In each case the check or the record said what we expected, and the code did something else.

---

### What comes next

Stack 10 is the wrap-up.  The checks, settings and templates are moved into a template that another repository can use, and the template is proven on a new, empty repository and on an existing one.

---

| | |
|---|---|
| Previous | [Stack 8 — checking a release before it is made](/posts/ai-dev-stack-8-post/) |
| Next | [Stack 10 — a gate another repository can use](/posts/ai-dev-stack-10-post/) |

---

[ai development stack — project page](/projects/ai-dev-stack-proj/)
