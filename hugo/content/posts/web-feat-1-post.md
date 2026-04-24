---
title: "scheduled rebuild — publishing future-dated posts automatically"
date: 2026-04-06T07:30:00
draft: false
tags: ["aws", "github-actions", "hugo", "ci-cd"]
summary: "Adding a daily GitHub Actions cron workflow so future-dated Hugo posts go live on their scheduled date without a manual push."
---

Hugo respects the `date:` field in a post's frontmatter. If you set a date in the future, Hugo will not include that post in the build output until that date has passed. This is useful — write a post today, schedule it for next week.

The problem is that the build only runs when you push. If no push happens on the scheduled date, the post stays dark.

## the fix

A second GitHub Actions workflow — `scheduled-rebuild.yml` — that runs the Hugo build, S3 sync, and CloudFront invalidation on a daily cron schedule, independent of any push.

```yaml
on:
  schedule:
    - cron: '0 8 * * *'   # 08:00 UTC daily
  workflow_dispatch:
```

At 08:00 UTC each morning, the workflow runs the same build and deploy steps as the push-triggered `deploy.yml`. If a post's scheduled date has arrived since the last push, it gets picked up and published.

`workflow_dispatch` is included, which adds a **Run workflow** button in the GitHub Actions UI. Useful for forcing a rebuild without making a dummy commit.

## what it does not do

The Lambda deploy step from `deploy.yml` is not included. That step packages and deploys `lambda/indicators.py` — there is no reason to redeploy it when no code has changed. The scheduled workflow only touches the Hugo output.

## why a separate workflow

The alternative is adding a `schedule:` trigger to the existing `deploy.yml`. That would work, but it would run the Lambda deploy on every scheduled build too — unnecessary and slightly wasteful. Keeping them separate keeps each workflow's scope clear.

## cost

GitHub Actions includes 2,000 free minutes per month for public repositories and 500 for private. A daily Hugo build runs in under two minutes. 365 runs per year = under 730 minutes — well within the free tier for either visibility setting.

Scott
