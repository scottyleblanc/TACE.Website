---
title: "cleaning sensitive data out of git history"
date: 2026-04-04T01:00:00
draft: true
tags: ["git", "security", "aws", "git-filter-repo"]
summary: "After a security review flagged AWS identifiers committed to a public repo, we used git-filter-repo to scrub them from all 46 commits — including file content and commit messages."
---

Building in public has a cost if you are not careful about what you commit.

When we stood up the AWS infrastructure for this site — S3 bucket, CloudFront distribution, IAM role, Route 53 hosted zone, ACM certificate — we documented everything. Runbooks, config snapshots, architecture diagrams. It is good engineering practice to write things down. The problem was that we wrote the actual resource identifiers directly into those documents and committed them to a public GitHub repository.

None of it was credentials. No access keys, no secret values. But specific AWS resource identifiers — account ID, distribution ID, bucket name, hosted zone ID, certificate ARN — give a threat actor a complete infrastructure map. They eliminate the reconnaissance phase entirely. Someone targeting the account does not need to guess what resources exist or where they are.

A security review caught it.  I asked another AI to look at the site, and the repo, and it came back with findings and recommendations for remediations.  

## what was exposed

Seven categories of identifiers were present in the repository history:

- AWS account ID
- S3 bucket name
- CloudFront distribution ID and domain
- IAM role name
- ACM certificate ARN
- Route 53 hosted zone ID

These appeared across multiple files: runbooks, CloudFront config snapshots, IAM policy documents, the site README, and the Hugo config. Some files had already been scrubbed in a prior commit. The problem was the history — 46 commits, and the identifiers were visible in earlier versions of those files.

## the tool: git-filter-repo

The standard recommendation for rewriting git history is `git-filter-repo`. It is a Python tool — faster and safer than the older `git filter-branch` approach, and the one currently recommended in the git documentation.

The approach:

1. Create a replacements file — a plain text file listing each sensitive string and its replacement
2. Run `git-filter-repo --replace-text` against the repository — this rewrites every blob (file content) in every commit
3. Run a second pass with `--message-callback` to scrub commit messages, which `--replace-text` does not cover
4. Force push the rewritten history to the remote

The two-pass approach matters. We caught the file content on the first run, then verified the result and found two commit messages still containing bucket and role names. The message callback handles those separately.

## the wrinkle: Python was not installed

`git-filter-repo` requires Python. On Windows, `python` launched the Microsoft Store prompt rather than a runtime. `winget install Python.Python.3.11` resolved it in under two minutes. Then `pip install git-filter-repo` and the tool was ready.

This is a common enough situation — tool unavailability blocking a security fix — that it is worth noting. The actual rewrite took seconds. Getting the environment ready took longer.

## the result

After two passes, a full scan of `git log --all -p` returned zero matches for any of the seven identifier patterns. The force push replaced all 46 commits on the remote. The public repository history no longer contains any of the original values.

The replacements used `REDACTED_` prefixes (e.g. `REDACTED_AWS_ACCOUNT_ID`) rather than the `<PLACEHOLDER>` convention used in the scrubbed files. This makes it unambiguous in history that the value was intentionally removed, not left as a template stub.

## what we would do differently

The identifiers should never have been in the public repository to begin with. The runbooks and config files belong in a private repository or local documentation — not alongside the public Hugo source.

For any future infrastructure work: resource identifiers go in private notes or a local runbook file that is gitignored from the start. The public repo gets architecture descriptions and placeholders only.

## setting up to not repeat it

Fixing the immediate problem is one thing. Making sure the same mistake does not happen again is another.

This site is built with Claude as a collaborator. Part of the honest accounting here is that the decision to use a public repo was made without either of us asking the right question: what documentation will live here alongside the site source? The portfolio argument for going public is valid. The security check on what gets committed into it should have come first.

To close that gap, the project instructions that Claude reads at the start of every session were updated to make the constraint explicit — not just "no credentials" but a specific list of what counts as sensitive in an AWS context. The same principle was added to the shared instructions that apply across all projects. The intent is that the question gets asked before the first commit, not after a security review flags it months later.

I was already hesitant about a public repo. That instinct was right. The lesson is to push back on it when it matters, not after the fact - "AI makes mistakes".

## references

[tacedata.ca project write-up](/projects/tacedata-site-proj/)

Scott
