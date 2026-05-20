---
title: "i learned this lesson, with smaller stakes"
date: 2026-05-19T00:00:00
draft: false
tags: ["security", "aws", "github", "git"]
summary: "A CISA contractor exposed credentials, config files, and access tokens in a public GitHub repository.  I had a smaller incident with a similar pattern — and a very different blast radius — in April."
---

I just finished reading the Krebs on Security report about a contractor for the U.S.
Cybersecurity and Infrastructure Security Agency — CISA.  The contractor was maintaining a
public GitHub repository and added sensitive material to it: administrative credentials to
AWS GovCloud servers, plaintext usernames and passwords for dozens of internal systems,
and access tokens for CISA's internal code repository.  The repository had been
public since November 2025.  A security researcher described it as the worst leak
they had witnessed in their career.

For context, CISA is the federal body responsible for protecting American critical
infrastructure.

The mechanism was straightforward: the contractor appears to have been using GitHub to
synchronize files between a work device and a home device — and the files included
administrative credentials to federal critical infrastructure.  The repository was public.
That isn't a workflow choice with unfortunate consequences.  That's negligent handling of
access to the systems CISA exists to protect.

I had my own public-repo incident in April.  The pattern was similar.  The response and the stakes were not.

---

My incident was smaller in every measurable way.  No credentials were exposed — not the keys
to the building, but I did leave a detailed map of its layout.  My own penetration test caught it.
Remediation involved scrubbing current files, rewriting 46 commits with git-filter-repo,
purging workflow run logs, and opening a support ticket with GitHub to clear their search
index cache (write-up [here](/projects/security-remediation-proj/)).

I'm not claiming the two incidents are the same.  The CISA contractor was handling
administrative access to federal critical infrastructure and chose to disable the scanning
that would have caught the upload.  I was handling AWS metadata for a personal project and
missed that some of it shouldn't have been committed in the first place.  Different in nearly
every way that matters.

What the two cases share is the mechanism: sensitive material in a public repository.
The blast radius — detection, response, stakes — is where they diverge.

---

The CISA case has one detail worth noting beyond the exposure itself: the contractor
explicitly disabled GitHub's default secret-detection controls — the built-in scanning
that flags credentials in public repositories.  That's not an oversight.  That's a guardrail being
removed because it was in the way.

This matters because it shifts the conversation from "how do you avoid making a mistake" to
"how do you build a process that catches mistakes regardless."  Controls exist for exactly
this reason.  They only work if they're left in place.

---

A few things I'd recommend to anyone building infrastructure in public:

**Treat public repos as permanently public.** Not just the current state — the entire commit
history.  If it was ever committed, assume it can be retrieved.

**Keep resource identifiers out of runbooks.** Architecture descriptions and placeholder
values belong in public documentation.  Real account IDs, ARNs, and bucket names belong in
private notes or a secrets manager.

**Don't disable secret scanning.** GitHub's default protections exist for a reason.  If
they're generating false positives, fix the false positives — don't turn off the detector.

**Run an external check after going public.** Tools like GitGuardian and truffleHog will
scan your history and surface what you missed.  Run them before you assume you're clean.

---

CISA's public statement noted no indication that sensitive data was compromised.  That may
be true.  It may also reflect the limits of what's currently known.

What I can say from my own experience: the remediation is uncomfortable, the audit trail is
permanent, and writing about it publicly is the right call regardless.  The mistake is already
documented in commit history and security scan logs somewhere.  Owning it directly is the
only honest response.

The work has your name on it.  So does the mistake.

---

## Further reading

- [CISA Admin Leaked AWS GovCloud Keys on Github](https://krebsonsecurity.com/2026/05/cisa-admin-leaked-aws-govcloud-keys-on-github/) — Krebs on Security (original reporting)
- ['The Worst Leak That I've Witnessed'](https://gizmodo.com/the-worst-leak-that-ive-witnessed-u-s-cybersecurity-agency-leaves-its-digital-keys-out-in-public-on-github-2000760330) — Gizmodo
- [CISA contractor apparently leaked 'highly sensitive' government AWS keys on Github](https://www.techradar.com/pro/security/cisa-contractor-apparently-leaked-highly-sensitive-government-aws-keys-on-github) — TechRadar Pro
- [Contractor Nightwing blamed for CISA secrets breach](https://www.thestack.technology/cisa-breach-nightwing-gitguardian/) — The Stack
- [CISA Credentials, Sensitive Data Exposed in GitHub Repository](https://securityboulevard.com/2026/05/cisa-credentials-sensitive-data-exposed-in-github-repository/) — Security Boulevard
