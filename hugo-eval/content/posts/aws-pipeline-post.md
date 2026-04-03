---
title: "deploying a static site on aws"
date: 2026-04-02
draft: true
tags: ["aws", "s3", "cloudfront", "github-actions", "oidc"]
summary: "How I set up S3, CloudFront, and a GitHub Actions deploy pipeline for tacedata.ca — no long-lived credentials, no manual deploys."
---

The site is built with Hugo. Hugo produces a folder of static files — HTML, CSS, JavaScript, images. The question is where those files live and how they get there. I chose AWS, and the setup turned out to be more interesting than I expected.

## the stack

Three AWS services do the work:

- **S3** — stores the Hugo output. Private bucket, no public access, no static website hosting enabled.
- **CloudFront** — serves the files globally. It sits in front of S3 and handles HTTPS, caching, and custom domains.
- **GitHub Actions** — builds the site on every push to main and syncs the output to S3.

S3 and CloudFront are deliberately separated. S3 is private — only CloudFront can read from it, via Origin Access Control (OAC). The bucket has no public access block exceptions, no website hosting configuration. CloudFront is the only way to reach the content.

## no long-lived credentials

The part I am most satisfied with is the deploy pipeline authentication. GitHub Actions needs AWS credentials to write to S3 and invalidate the CloudFront cache. The naive approach is to create an IAM user, generate an access key, and store it as a GitHub secret. That access key sits in GitHub indefinitely, never rotates, and becomes a liability.

The better approach is OIDC. GitHub Actions can request a short-lived token from AWS by presenting a signed identity assertion from GitHub's token endpoint. AWS verifies the assertion against a registered OIDC provider and issues temporary credentials scoped to a specific IAM role. The credentials exist only for the duration of the job.

The setup requires three things on the AWS side:

1. Register GitHub's OIDC provider (`token.actions.githubusercontent.com`) in IAM
2. Create an IAM role with a trust policy that allows only this repo's main branch to assume it
3. Attach a permissions policy scoped to exactly what the deploy job needs — S3 write to the site prefix, CloudFront invalidation on this distribution

No access keys. No rotation. Nothing stored in GitHub except the role ARN.

## the deploy workflow

Every push to main runs this sequence:

1. Checkout the repo (including the PaperMod theme submodule)
2. Build with Hugo Extended — `hugo --minify --baseURL "${{ vars.SITE_URL }}"`
3. Authenticate to AWS via OIDC
4. `aws s3 sync` the Hugo output to the S3 bucket prefix
5. `aws cloudfront create-invalidation` to clear the CDN cache

The baseURL is a GitHub Actions variable — not baked into the repo. That keeps the CloudFront URL and the eventual custom domain interchangeable without touching any config files.

## one wrinkle: directory URLs

Hugo generates `posts/index.html`, not `posts.html`. CloudFront, given a request for `/posts/`, serves `posts/index.html` correctly. But `/posts` — no trailing slash — returns a 403 because there is no object at that key in S3.

The fix is a CloudFront Function — a small JavaScript handler that runs on every incoming request before CloudFront looks up the object. If the URI ends in `/`, append `index.html`. If it has no file extension, append `/index.html`. CloudFront-js-1.0 runtime is ES5 only, so no `endsWith()` or `includes()` — `slice(-1)` and `lastIndexOf('.')` instead.

Fifteen lines of JavaScript, associated with the distribution's default behavior, and directory navigation works correctly.

## the runbook

The full command sequence — S3 bucket policy, OIDC provider setup, IAM role creation, GitHub Actions workflow — is in the project write-up.

[tacedata.ca project write-up](/projects/tacedata-site-proj/)

Scott
