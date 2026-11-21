# Review

Every pull request is examined by someone other than its author before it merges: a
second-model review, then a human review using the checklist in the pull request
template. The model reviewer is told to read this file and follows the review order
below. The human review covers what only a person can establish.

The gate has already run when review starts. Review does not repeat what the gate
checks (`Docs/rules.md`). It covers what only judgement can: the repository's own
rules that no check enforces, and whether the change does what it says.

In the commands below, `tools/gate` is where the repository holds the kit.

## The review path

The author's steps are in [RUNBOOK.md](RUNBOOK.md), PR-1.

One review per pull request keeps the cost bounded: each new review is a fresh session
over the whole change, which finds a different subset of problems each time and never
settles. A second review is the author's choice, not a rule.

## What the human review covers

A person reading a pull request cannot establish rule by rule that every line holds, so
the checklist does not ask for that. Each kind of rule has an owner:

| Rule or question | Established by |
|---|---|
| The rules in `Docs/rules.md` | The gate |
| The repository's rules that no check enforces, line by line | The second-model review, in the order below |
| No real names or secrets in files or commit messages | The gate's patterns and gitleaks for known shapes, the second-model review, and the human for names they recognise as real |
| The change does what it says, and nothing else visible | The human |
| Each finding's Response is right, and a finding that should be fixed is fixed | The human |
| The fix commits after the reviewed commit do what their findings asked | The author; the gate and the human's reading of the Responses |
| The gate passed in CI | The branch protection on the target branch, which blocks the merge otherwise; where the host's plan cannot require a check (a private repository on GitHub Free), the human, before merging |

The human checklist has two items: intent, and the findings.

## Review order

Intent first, then tests, then implementation. Code is read last, so the reviewer
judges it against what it is meant to do, not against what it happens to do.

### 1. Intent

- The change matches its stated purpose: the commit messages, and the task or decision
  they cite.
- A document the change touches describes what the code now does.
- The README, changelog, task list and security notes are updated where the change
  affects them.

### 2. Tests

- A behaviour the change adds has a test that would fail without it.
- A test proves what its title says, and does not only mock the code under test.
- Tests touch the filesystem only in a test folder and need no real credential.

### 3. Implementation

- Secrets: a password is never placed in an argument list, a log line, a return value
  or an exception message.
- Text built for another interpreter (SQL, a shell, a tool script) embeds only values
  validated as typed parameters.
- A pipeline result used as an array is wrapped in `@()`; a value that can be an array
  goes to `ConvertTo-Json` with `-InputObject`.
- The repository's own rules that its standards mark for review.
- Defects no rule names: a wrong result, an unhandled path, a resource not released.

## Severity

| Severity | Meaning |
|---|---|
| High | A security rule broken, data changed or lost when it should not be, or a wrong result on a normal path |
| Medium | Another review rule broken, or a defect on an uncommon path |
| Low | A document out of step with the code, unclear code, or a gap in a test that does not hide a defect |

## Answering a finding

Each finding in the record has a `Response`. The author sets it to one of these,
followed by the reason:

| Response | When |
|---|---|
| `Fixed: <commit>` | The finding is right and a later commit on the branch fixes it |
| `Rejected: <reason>` | The finding is wrong: the code already does what it asks |
| `Accepted: <reason>` | The finding is right and is not fixed in this pull request, with the reason that is safe |
| `Deferred: <task>` | The finding is right and its task is added to the task list on the branch |

The gate fails while any `Response` is empty or does not start with one of these words.
It cannot judge the reason; the human checklist does.

Fix a High finding. Fix a Medium one, or say in its Response why it is safe not to. A Low
finding is usually answered, not fixed: each fix is new code that no model reviews.

## Limits

- The record is the author's attestation. The gate proves it covers the branch and is
  answered, not that the session ran as recorded.
- Commits after the reviewed one are not checked to be fixes, by the gate or a model.
  They are the author's; a large change after the review should be reviewed again.
- The model reviewer is a second session of the same model family as the author. It
  shares the author's blind spots more than a different model or a person would.
- A review can miss a defect, and the same change reviewed twice gives different
  findings. The gate stays the deterministic check; review adds judgement on top.
