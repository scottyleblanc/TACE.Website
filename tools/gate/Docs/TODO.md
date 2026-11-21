# TODO

Ordered: each item depends on the ones above it being stable. `[SEC]` items are
first-class; no release is tagged with one open.

## v0.1.0 — first release

- [x] Gate script with checks GK01 to GK11, config-driven
- [x] Custom analyzer rules AN-002 to AN-009, with tests
- [x] Analyzer baseline for repositories with existing findings
- [x] Templates: config, hook, GitHub and Bitbucket wrappers, pull request template
- [x] [SEC] Pinned, hash-checked tool installs for Windows and Linux
- [x] The kit's own tests, and the kit gated by itself
- [x] Prove on a fresh, empty repository: `git subtree add`, the minimal config, the
      gate passes; a seeded secret and a seeded analyzer finding each fail it, through
      the hook and through CI on a real pull request
- [x] Record that GitHub Free cannot require the check on a private repository (found
      by the fresh-repository proof)
- [x] Optional checks GK12 evidence, GK13 package and GK14 instructions, with tests
      (DEC-013)
- [x] Custom analyzer rules AN-010 to AN-013 (DEC-014) and AN-014 to AN-016 (DEC-015),
      with tests
- [x] Analyzer rule AN-017 (DEC-016) and the optional file scan GK15 (DEC-017), with tests
- [x] Analyzer rule AN-018 and registry deny rules in the agent templates (DEC-019), with tests
- [x] The `Quick` list of checks the hook skips, and the kit's own CI workflow (DEC-020),
      with tests
- [x] AN-014 reads early exits from the structure, including `continue` and `break`;
      AN-017 accepts the class name in a class method (DEC-015, DEC-016), with tests
- [x] Make the `gate` job a required status check on `main`: a ruleset on `main` that
      requires a pull request and a passing `gate` check, with no bypass
- [x] `Invoke-Gate.ps1 -Timestamp`: the UTC time on every line and each check's
      duration, passed by the CI templates (DEC-021), with tests
- [ ] Prove on a copy of an existing module repository hosted on Bitbucket: baseline
      the existing findings, the gate passes, run the Bitbucket template
- [ ] [SEC] Pin the Bitbucket template's image by digest
- [ ] Verify which Bitbucket plan enforces a required pipeline as a merge check, and
      record it in the template
- [ ] First run of the Linux path: `Install-GateTool.ps1` and the gate on Linux

## Later

- A cross-check against a private list of identifiers, kept outside the repository.
