---
title: "security remediation — what we got wrong"
date: 2026-04-04
draft: true
tags: ["security", "aws", "git", "git-filter-repo", "cloudfront"]
summary: "A post-launch security review of tacedata.ca uncovered sensitive AWS identifiers committed to a public repository. This is a full account of what was exposed, how it was found, and what it took to fix it."
---

## The Mistake

The site was built in private to start. During a later stage a decision was made to move the repository to public - which made sense for a portfolio — the repository itself is part of the proof of work. The mistake was not thinking through what documentation would live alongside the Hugo source.

Over five stages of infrastructure work, we wrote detailed runbooks: AWS CLI commands, IAM policy documents, CloudFront config snapshots, architecture diagrams. All of it committed to the same public repository as the site content. None of it was credentials. But the AWS resource identifiers — account ID, distribution ID, S3 bucket name, hosted zone ID, certificate ARN, IAM role names — were present throughout. Together, they form a complete infrastructure map. A threat actor does not need credentials to cause damage if they already know the exact shape of your environment.

A security review caught it. The honest version: both the developer and the AI collaborator (Claude) made this mistake together. The portfolio argument for going public was made without either party asking what would be committed there over time. The instinct to be cautious about a public repo was present - I did not push back hard enough.

Cleaning this mess up took longer than building the site.

## How did we catch it?

I engaged two different AI tools to perform penetration testing on the site, and on the GitHub repository.  Each came up with overlapping and unique findings.
## What Was Exposed

Seven categories of AWS identifiers across multiple files and 46 git commits:

- AWS account ID
- S3 bucket name and path prefix
- CloudFront distribution ID and domain
- IAM deploy role name and ARN
- ACM certificate ARN
- Route 53 hosted zone ID

These appeared in runbooks, IAM policy documents, CloudFront config snapshots, the site README, and the Hugo config. Some had been partially scrubbed in a prior commit. The problem was the history — scrubbing a file does not remove it from earlier commits.

## The Remediation

### Step 1 — Scrub current files

Replace all real identifiers with `<PLACEHOLDER>` values across the working tree. Commit and push. This fixes the current state but not the history.

### Step 2 — Rewrite git history

Used `git-filter-repo` — the current recommended tool for history rewriting, faster and safer than `git filter-branch`.

Two passes were required:
1. `--replace-text` with a replacements file — rewrites every blob (file content) in every commit
2. `--message-callback` — scrubs commit messages, which `--replace-text` does not cover

After both passes, `git log --all -p` returned zero matches for any of the seven identifier patterns. Force push to replace all 46 commits on the remote.

Python was not installed on the machine. `winget install Python.Python.3.11` followed by `pip install git-filter-repo` resolved it before the rewrite could begin.

### Step 3 — Harden the live site

With the immediate exposure addressed, we moved on to the broader findings:

- **HTTP security headers** — added via CloudFront Function (`viewer-response`): CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy. A custom Response Headers Policy was the natural approach, but the distribution's auto-created WAF ACL (free tier) blocks it. CloudFront Functions are the workaround.
- **License** — replaced MIT with All Rights Reserved. The MIT license was inappropriate for proprietary portfolio content.
- **Security clearance disclosure** — removed from the contact page. Not a credential, but a social engineering assist.
- **`security.txt`** — added at `/.well-known/security.txt` per RFC 9116.
- **Dependabot** — configured for weekly scans of GitHub Actions versions and git submodules.
- **Branch protection** — force pushes and deletions blocked on `main`.

### Step 4 — Private repo for operational documentation

Real infrastructure values now live in a private repository. The public repo contains descriptions and placeholders only. Any future infrastructure work follows the same pattern.

### Step 5 — Verify external exposure

Cleaning the git history removes data from the repository — not from systems that already crawled it. Three checks:

1. **Search engines** — searched Google, Bing, and DuckDuckGo for the specific identifier strings. No results.
2. **Wayback Machine** — checked `web.archive.org` for snapshots of the repository taken before the cleanup. No snapshots.
3. **GitHub code search** — searched GitHub directly for the identifier strings. Old blob objects were still indexed and returning results even after the force push. GitHub's search index does not immediately reflect history rewrites.

A support ticket was raised with GitHub requesting a search index purge and object cache clear for the repository.

## The Learning

It was a good call to complete penetration testing on publicly available content.  Unfortunately we did it when the site was live, not before.

Resource identifiers are not credentials, but they are sensitive. They eliminate the reconnaissance phase for a targeted attack. The rule going forward: public repositories get architecture descriptions and placeholders. Runbooks, policy files, and config snapshots with real values go in private documentation.

The second lesson is about instinct. The hesitation about using a public repository was present from the start and not pushed on hard enough. When a security instinct surfaces, it deserves a proper answer — not a deferred one.

AI makes mistakes.  Despite my hesitation, and initial pushback, I eventually acquiesced to the idea of making the repo public.  My mistake was not keeping security top of mind throughout; if I had prompted Claude to consider security, this issue would not have presented itself.

## References

- [cleaning sensitive data out of git history](/posts/git-history-rewrite-post/) *(draft — pending GitHub support resolution)*
- [internet cache and wayback machine](/posts/cache-and-a-wayback-machine/) *(draft — pending GitHub support resolution)*
- [tacedata.ca site build](/projects/tacedata-site-proj/)
