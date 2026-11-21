---
title: "ai development stack: stack 8 — checking a release before it is made"
date: 2026-11-19T12:00:00
draft: false
tags: ["ai", "powershell", "oracle", "security", "stack"]
summary: "ninth post in the ai development stack series: the checks now refuse a change whose version number disagrees between the files that carry it, or whose package would contain a file it should not.  The first run found two functions that had never been checked."
---

### Release

*This is the ninth post in a series documenting the build of an AI development stack — a set of layers placed around AI-generated code to make it as correct, secure, and supportable as possible.  The [project page](/projects/ai-dev-stack-proj/) covers the question and the full layer model.  [Stack 7](/posts/ai-dev-stack-7-post/) set what the AI may run and read.  This post is Stack 8: release, the layer that checks what goes out.*

*For a visual reference, see the [stack map](/projects/ai-dev-stack-map/): where each layer acts on a change, and the files behind it.*

*In this post, "we" means me and Claude Code, the AI coding assistant I build with.*

---

Each stage of the stack ends with a release.  A release is a state of the code and documentation at a point in time.  Each of these releases is given a new version number.

That version number appears in several places: the module's manifest (the file that describes it), the module file, the help text of each public function, the change log, and the git tag, a fixed label on the commit that is released.  If they disagree, nobody can say for certain which code a version refers to.

To publish the module, the code is built into a package, a single file, and uploaded to the PowerShell Gallery, the public site where PowerShell modules are shared.  A version published there cannot be replaced or deleted.  The first six versions of this module went out with folders that were never meant to ship: the test files, the documents and the git history.

Stack 8 adds two checks, so that neither mistake can reach the main branch.

---

### The version

The first check compares the version number in the manifest, the module file, each public function's help text and the newest entry in the change log.  It runs every time the checks run.

Its first run failed on the real code.  Two of the functions brought in from my backup module at Stack 0 had no version line in their help text.  The build script already had a version check, but it skipped any file without a version line, so those two had never been checked.  Both now carry one.

The tag is checked only on a pull request, a proposed change that GitHub shows on its own page before it is merged.  The work on a stage keeps the last released version until its final commit raises it, so checking the tag on every push would fail the whole stage.  On a pull request, the check fails when:

- the version is lower than the latest tag
- the version is already tagged and the module code has changed

The second case is the one that matters.  Without it, a version that is already released could end up labelling different code.

---

### The package

The manifest has a list of the files the module is made of.  The list looks as if it decides what goes into the package.

We tested whether it does.  We added one stray file to the built module's folder, next to the four files on the list, and built the package.  The stray file was in it.  The tool packages everything in the folder and ignores the list.

The second check therefore builds the package on every pull request and opens it.  It fails unless the package holds exactly the files on the list: nothing extra, and nothing missing.  The package is built on the machine running the checks and nothing is published.  The check does not depend on where the package goes.

---

### The publish script

The script that publishes to the PowerShell Gallery took its access key as plain text, and its own example showed how to convert the key to plain text first.  That breaks one of my security standards: a secret is accepted only in a protected form, and turned back into plain text only at the moment it is used.

The script now accepts only the protected form, and refuses to publish a folder holding a file that is not on the list.  Nothing is published while the stack is being built.

---

### A gap in the review check

Before this stage's own review had run, we ran every check on its pull request.  The review check from Stack 6 passed.

It had accepted the review record left by the Stack 7 pull request.  The check confirmed that the reviewed commit was in the change's history, and once a pull request is merged, its commits are in the history of every change after it.  So every pull request after the first could have merged without a review of its own.

The check now also requires the reviewed commit to be one the pull request adds.

---

### Proving the stage

We made a copy of the repository and planted one defect at a time:

| Planted | Expected | Result |
|---|---|---|
| The newest change log entry names a different version | Fails on the version check only | As expected |
| The version is already tagged, and the module code has changed | Fails on the version check only | As expected |
| The build script writes an extra file into the module's folder | Fails on the package check only | As expected |
| A pull request with no review keeps the previous pull request's record | Fails on the review check only | As expected |

The first version of the stray-file case also failed an older check.  That check runs the build script against a small test copy of a repository, and the planted line copied a file that copy does not have.  The case now writes its own file.

The full set of planted defects, 19 in all, takes about 25 minutes.  It runs when the checks themselves change, not on every change.  The package check adds about a second to each pull request.

---

### The baseline

The baseline measures, taken again at the end of this stage:

| Measure | Stack 3 | Stack 4 | Stack 5 | Stack 6 | Stack 7 | Stack 8 |
|---|--:|--:|--:|--:|--:|--:|
| Module code, lines | 2,693 | 2,693 | 2,693 | 2,693 | 2,693 | 2,699 |
| Unit test code, lines | 5,372 | 5,372 | 5,372 | 5,372 | 5,372 | 5,372 |
| Unit tests passing | 405 | 405 | 405 | 405 | 405 | 405 |
| Static analyzer findings | 110 | 110 | 110 | 110 | 110 | 110 |
| Change review | none | none | none | in place | in place | in place |
| Agent privileges | none | none | none | none | in place | in place |
| Version checks | none | none | none | none | none | in place |

Stack 8 did not change what the module does.  The six new lines of module code are the copyright, module and version lines added to two functions' help text.

---

### The part worth keeping

The build's version check had passed on every build, including for the two functions it never looked at.  The review check had passed a pull request that had no review.  A check that accepts what it should have refused reports the same result as a check that found nothing wrong.

The package tool looked as if it used the file list, and it did not.  All three were found by testing what the tool or the check actually does, not what it was expected to do.

---

### What comes next

Stack 9 is the feedback loop: every defect that gets past the stack becomes a new check, and a drill tests whether the repository's own documents and tests are enough for someone to find and fix a planted defect.

---

| | |
|---|---|
| Previous | [Stack 7 — what the AI can reach](/posts/ai-dev-stack-7-post/) |
| Next | [Stack 9 — turning missed defects into checks](/posts/ai-dev-stack-9-post/) |

---

[ai development stack — project page](/projects/ai-dev-stack-proj/)
