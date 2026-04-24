
---
title: "security - stage 2 - internet cache and the wayback machine"
date: 2026-04-04T06:00:00
draft: false
tags: ["git", "security", "aws", "git-filter-repo", "wayback machine", "internet cache"]
summary: "Cleaning git history removes data from your repo — but not from search engines, the Wayback Machine, or GitHub's cache. Here is what to check."
aliases: ["/posts/cache-and-a-wayback-machine/"]
---

*This is the second post in a series documenting the security remediation of tacedata.ca. [Stage 1](/posts/sec-stage-1-post/) covered cleaning sensitive AWS identifiers from the git history.*

---

Cleaning the git history is step one. Step two is checking what already left the building.

Cleaning the git history removes the sensitive data from the repository, but it does not immediately remove it from every system that may have already seen it. Search engines, the Internet Archive, and GitHub's own internal caching operate independently of your repository state. Before considering a cleanup complete, we needed to verify that the identifiers were never indexed externally.

## search engine indexing

Run a direct string search for the specific values that were exposed. In this case, that meant the CloudFront distribution ID, the S3 bucket name, and the IAM role name — the ~~actual~~ *redacted* identifier strings, in quotes:

```
"CLOUDFRONT_DISTRIBUTION_ID" OR "S3_BUCKET_NAME" OR "AWS_ROLE_ARN"
```

We ran this search on Google, Bing, and DuckDuckGo separately — they maintain independent indexes. A result here means the identifier was cached and is still surfaceable. No result is the outcome you want, but it is not an absolute guarantee; not everything that is crawled gets surfaced in search results.

The `cache:` operator (`cache:github.com/your-repo`) was historically useful for checking Google's cached snapshot of a specific page directly, but Google has deprecated it and it is no longer reliable.

## the wayback machine

The Internet Archive crawls public GitHub repositories independently of search engines. We had to check whether a snapshot of the repository was taken before the cleanup:

```
https://web.archive.org/web/*/github.com/your-username/your-repo
```

If snapshots exist, review them to determine what state of the repository they captured. If a snapshot contains sensitive data, you can submit a removal request to the Internet Archive directly.

## github actions workflow logs

There is a fourth surface that is easy to miss: GitHub Actions workflow run logs. Every run records the full output of each step — including the commands that were executed. When the bucket name and distribution ID were hardcoded in `deploy.yml`, every workflow run logged them in plain text. The Actions tab on a public repository is visible to anyone, not just the repository owner.

Cleaning the git history does not touch the workflow logs. They are stored independently and persist until explicitly deleted. All 44 historical runs were deleted via the GitHub CLI:

```powershell
gh run list --repo your-username/your-repo --limit 100 --json databaseId --jq '.[].databaseId' | ForEach-Object {
    gh run delete $_ --repo your-username/your-repo
}
```

This is worth checking any time sensitive data has appeared in a workflow — not just in committed files.

## what no results actually means

In this case, all seven identifier strings returned nothing across search engines, the Wayback Machine, and GitHub code search. The index was clean.

A GitHub support ticket had been raised to request a cache purge, but it may not have been the deciding factor. The more likely explanation is the workflow log deletion. The logs contained 44 runs worth of CLI commands executing with the real values — far more indexed content than the source files alone. Removing them appears to have cleared the GitHub search index ahead of any manual intervention.

That is worth noting: in this case the workflow logs were probably the primary indexed surface, not the committed files. Deleting them first may be the most effective step when sensitive data has appeared in a public repository's Actions history.

The lesson is not that this will always be the case. On a repository with traffic, stars, or forks, the window between exposure and indexing can be very short. Bots actively watch public GitHub repositories for credentials and infrastructure identifiers. The right assumption after any sensitive data hits a public repository is that it was seen — and the response is to rotate or invalidate the affected resources, not just clean the history.

## references

[tacedata.ca project write-up](/projects/tacedata-site-proj/)

[security remediation — what we got wrong](/projects/security-remediation-proj/)

Scott

---

*The security remediation series ends here. The full account: [security remediation — what we got wrong](/projects/security-remediation-proj/).*