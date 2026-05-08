---
title: "aws cost management — right-sizing a personal estate"
date: 2026-05-08
draft: false
url: /projects/aws-cost/
tags: ["aws", "cost", "ec2", "ebs", "secrets-manager", "cloudfront"]
summary: "A billing audit of the tacedata.ca AWS account that found $59/month in infrastructure charges on a site that was supposed to cost nearly nothing — and reduced it to $3.63/month."
---

## Problem

The analytics project surfaced a question that should have been asked earlier: what is this AWS account actually costing?

The site itself — S3, CloudFront, Route 53 — was known to be near-zero. The concern was everything else that accumulated over months of POC work, infrastructure experiments, and development activity. No one had looked at the bill as a whole.

## What Was Found

April 2026 spend (excluding a training subscription): **$59/month pre-tax** across a personal account.

The five largest line items:

| Service | Monthly cost | Driver |
|---|---|---|
| EC2 — other | $21.36 | EBS volumes ($18.64) and snapshots ($2.56) |
| EC2 — compute | $8.59 | Instance hours across POC and lab VMs |
| VPC | $7.38 | Idle Elastic IP charges |
| Secrets Manager | $7.23 | 18 secrets at $0.40/month each |
| Oracle Linux 9 support | $2.52 | Paid AMI on one EC2 instance |

Three findings were non-obvious enough to be worth documenting.

**Idle Elastic IPs:** AWS charges $0.005/hour for a public IPv4 address whether or not it is in use. Two Elastic IPs were allocated and associated with stopped instances — stopped, not terminated. The association does not prevent the idle charge. Two EIPs against stopped instances cost $7/month and are invisible unless you look at the VPC cost breakdown by usage type.

**Orphaned snapshots:** When you deregister an AMI, the EBS snapshots that back it are not deleted. They continue billing. Two snapshots — 120 GB combined — were backing AMIs that had already been deregistered in an earlier cleanup. They were silently accumulating storage charges with no associated image to restore from.

**Secret accumulation:** Eleven of the eighteen Secrets Manager entries were named `MOCK-*` — test data created during POC development and never removed. At $0.40/month per secret, they cost $4.40/month. Most had never been accessed.

## What Was Done

Cleanup in order:

1. **AMI refresh** — created fresh AMIs for all five EC2 instances (all were stopped), then deregistered the four older AMIs and deleted all six backing snapshots (including the two orphaned ones). Five clean AMIs, one snapshot each.
2. **Terminate the POC infrastructure** — three Oracle POC instances and their attached volumes. Two lab VMs followed.
3. **Release Elastic IPs** — both released after their instances were terminated.
4. **Delete test secrets** — eleven `MOCK-*` secrets deleted. One real operational secret retained.

## Result

| | Before | After |
|---|---|---|
| EC2 instances | 5 (all stopped) | 0 |
| EBS volumes | 200 GB across 5 volumes | 0 |
| Elastic IPs | 2 | 0 |
| Secrets | 18 | 1 |
| Snapshots | 280 GB declared | 200 GB declared (5 AMIs) |
| **Monthly cost (pre-tax)** | **~$59** | **~$3.63** |

The $3.63 steady state breaks down as: AMI snapshot storage (~$2.00), Route 53 hosted zone ($0.50), Secrets Manager one secret ($0.40), CloudWatch canary ($0.22), S3 site storage ($0.09), Lambda and DynamoDB trace amounts.

The only discretionary cost remaining is the snapshot storage — five AMIs covering infrastructure that no longer exists. Deleting them would bring the floor to ~$1.63/month.

## Status

Complete — 2026-05-08.

## Build Series

- [Stage 1 — What $59/month looks like on a personal site](/posts/aws-cost-stage-1-post/)
