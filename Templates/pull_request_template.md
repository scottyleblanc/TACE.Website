## What this changes

<!-- One or two sentences: what the change does and why. Name the task or decision. -->

## Second-model review

<!-- From the review record (default Review/LastReview.json). Gate check GK10 fails if
the record is missing, does not cover the branch, or has an unanswered finding. -->

- Reviewed commit:
- Findings: <!-- count by severity, e.g. 0 High, 1 Medium, 2 Low -->

| Id | Severity | Rule | Finding | Response |
|---|---|---|---|---|
| | | | | |

## Human review

The decisions only a person makes. Everything else is covered by the gate, the
second-model review or the author; see tools/gate/Docs/REVIEW.md.

- [ ] **Intent:** the change does what this description and its task or decision say,
      and nothing else I can see
- [ ] **Findings:** I read every finding and agree with each Response

## Evidence

- [ ] `pwsh -NoProfile -File ./tools/gate/Scripts/Invoke-Gate.ps1 -Unit` passed locally
