## What this changes

<!-- One or two sentences: what the change does and why. Name the stage or task. -->

## Human review

The decisions only a person makes. Everything else is covered by the gate; see
tools/gate/Docs/REVIEW.md.

- [ ] **Intent:** the change does what this description and its stage or task say,
      and nothing else I can see
- [ ] **Public repo:** no real resource identifier, email address or credential in
      the diff or the commit messages; real values are in the private repo only
- [ ] **Deploy:** merging deploys the site; the change is ready to go live

## Evidence

- [ ] `pwsh -NoProfile -File ./tools/gate/Scripts/Invoke-Gate.ps1 -Unit` passed locally
