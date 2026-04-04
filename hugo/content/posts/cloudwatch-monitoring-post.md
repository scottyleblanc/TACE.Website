---
title: "site monitoring with aws cloudwatch"
date: 2026-04-03T15:00:00
draft: false
tags: ["aws", "cloudwatch", "monitoring", "synthetics"]
summary: "Setting up availability monitoring for tacedata.ca using CloudWatch Synthetics — what it is, what it costs, and how we set it up."
---

The site is live. The next question is: how do we know if it goes down?

A static site on CloudFront is more resilient than a WordPress site on shared hosting, but it is not infallible. The S3 bucket could have a misconfigured policy. The CloudFront distribution could have a bad configuration change applied. DNS could drift. Any of these would take the site down silently — no error thrown, no notification sent.

The answer is availability monitoring. We want something that checks the site on a schedule and sends an alert when it stops responding.

## why CloudWatch over a third-party tool

The simple answer is that we are already in AWS. CloudWatch Synthetics is an AWS-native monitoring tool that runs a small script on a schedule, checks the response, and reports results as metrics. Those metrics feed into CloudWatch Alarms, which publish to SNS, which sends an email.

The entire chain stays inside the AWS account — the same place as the S3 bucket, CloudFront distribution, and Route 53 zone. No third-party service, no additional account to manage.

Cost at this scale is negligible — under $0.15/month.

## what we set up

Five resources:

1. **S3 bucket** — stores canary run artifacts (results, screenshots). Required by CloudWatch Synthetics. A separate bucket from the one holding the site content — mixing the two would complicate the bucket policy and make the content harder to manage.
2. **IAM role** — the canary runs as a Lambda function. It needs permission to write to S3 and publish CloudWatch metrics.
3. **CloudWatch Synthetics Canary** — a Node.js script that hits `https://tacedata.ca` every 5 minutes and checks for HTTP 200.
4. **CloudWatch Alarm** — monitors the canary's success metric. Triggers after 2 consecutive failures — avoids false positives from transient blips.
5. **SNS Topic + Email subscription** — the alarm publishes to SNS; the email subscription delivers the alert.

## what it monitors

The canary checks two things: that the site responds, and that it responds with HTTP 200. A 403, 503, or timeout all register as failures.

The 5-minute interval means we know about an outage within 10 minutes at most — two failed runs before the alarm triggers. That is acceptable for a personal site.

## the runbook

The full setup — IAM policy, canary script, alarm configuration — is in the repository.

[CloudWatch monitoring runbook](https://github.com/scottyleblanc/TACE.Website/blob/main/config/runbook-cloudwatch-monitoring.md)

[tacedata.ca project write-up](/projects/tacedata-site-proj/)

Scott
