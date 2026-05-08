---
title: "aws cost management: stage 1: what $59/month looks like on a personal site"
date: 2026-05-08T00:00:00
draft: false
tags: ["aws", "cost", "ec2", "ebs", "secrets-manager", "elastic-ip"]
summary: "A billing audit of the tacedata.ca AWS account — what was accumulating, what was surprising, and how infrastructure that was supposed to cost nothing ended up at $59/month."
---

*This is the first post in a series on AWS cost management for tacedata.ca. Related: [analytics project write-up](/projects/analytics/) — the project that prompted the audit.*

---

The analytics project ended when the CloudFront Free plan blocked all logging features. The work was not wasted — I learned something about the pricing model, documented it, and moved on. But the project had a side effect: while digging through the AWS console, I looked at the billing dashboard for the first time in a while.

The site was supposed to cost nearly nothing. S3, CloudFront on the free tier, Route 53. That part is true — the site infrastructure itself costs under a dollar a month. The rest of the account was another matter.

April spend, excluding a training subscription: **$59/month**.

That number deserved a closer look.

## reading the bill

Cost Explorer breaks down charges by service, but service-level totals only tell you so much. "EC2 — Other" at $21/month explains nothing. The useful view is grouping by usage type within each service — that shows the specific meter that is running.

Three findings stood out.

## the stopped instance trap

The VPC line item was $7.38/month. Drilling in: $7.06 of that was idle Elastic IP charges.

AWS charges $0.005/hour for a public IPv4 address. The charge applies whether the address is in use or not — and critically, it applies when an address is associated with a **stopped** instance, not just an unallocated one. The assumption was that the cost only applied to orphaned addresses with no instance at all. That is wrong. Two EIPs, each attached to a stopped EC2 instance, running 24 hours a day, 30 days a month: $7.20.

Stopped instances feel free. You are not paying for compute. The instance is just sitting there, paused. What you are paying for is everything attached to it — EBS volumes, Elastic IPs, any associated resources that bill by the hour regardless of whether the instance is running.

## deregister is not delete

EBS snapshots backing an AMI are not deleted when you deregister the AMI. The AMI entry disappears. The snapshots do not. They continue billing at $0.05/GB-month for however long they sit there.

Two snapshots — 120 GB combined — were found with no associated AMI. Their parent images had been deregistered in an earlier round of cleanup and the snapshots were never touched. They were not visible in any list of "active" things. The only way to find them was to list snapshots explicitly, cross-reference against existing AMIs, and identify the ones pointing at AMI IDs that no longer exist.

This is easy to accumulate. Create an AMI, test something, deregister the AMI, forget the snapshot. Repeat a few times. The charges are small individually — $3/month for a 60 GB snapshot — but they add up and they are invisible unless you go looking.

## secrets left on the floor

Secrets Manager charges $0.40/month per secret plus API call fees. The account had eighteen secrets. Eleven of them were named `MOCK-*` — test entries created during a POC development phase and never cleaned up. Most had a `LastAccessedDate` of `None`.

$4.40/month for test data nobody was reading. Not ruinous, but avoidable.

## the cleanup

The audit took about an hour. The cleanup took another hour.

Five EC2 instances — all stopped, none actively needed — were scheduled for termination. Before terminating, fresh AMIs were created from each so there is a recovery point if anything is ever needed again. Then the four older AMIs were deregistered and all six of their backing snapshots deleted — including the two orphaned ones.

Instances terminated. Elastic IPs released. Eleven test secrets deleted.

## the result

| | Before | After |
|---|---|---|
| EC2 instances | 5 (all stopped) | 0 |
| EBS volumes | 200 GB | 0 |
| Elastic IPs | 2 | 0 |
| Secrets | 18 | 1 |
| **Monthly cost** | **~$59** | **~$3.63** |

The $3.63 that remains is the actual site: snapshot storage for the AMI archive (~$2.00), Route 53 ($0.50), CloudWatch canary ($0.22), one real secret ($0.40), S3 storage ($0.09).

A 94% reduction from a couple of hours of work. The infrastructure that was supposed to cost nothing does, in fact, cost nothing. The charges that existed were real — accumulated from months of building, testing, and not cleaning up — and were invisible until someone looked.

The lesson is less about the specific services and more about the habit: AWS accounts accumulate charges the way drawers accumulate things. It takes an active decision to open the drawer.

Scott

---

*[AWS cost management project write-up](/projects/aws-cost/)*
