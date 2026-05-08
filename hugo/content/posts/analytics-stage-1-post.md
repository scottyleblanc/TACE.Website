---
title: "analytics: stage 1: what the cloudfront free plan doesn't tell you"
date: 2026-05-07T00:00:00
draft: false
tags: ["aws", "cloudfront", "waf", "analytics", "s3", "pricing"]
summary: "Setting up server-side traffic analytics for tacedata.ca — and hitting a hard wall in the CloudFront Free pricing plan that blocks all logging features."
---

*This is the first post in a series documenting the analytics setup for tacedata.ca — adding server-side traffic monitoring using AWS-native tooling. Site background: [tacedata.ca project write-up](/projects/tacedata-site-proj/).*

---

The site has been live for a few weeks. It works. The pipeline deploys cleanly, the pages load fast, the monitoring canary runs every five minutes. What it does not do is tell me whether anyone is visiting.

The standard answer to that question is Google Analytics — a script tag on every page, a cookie consent banner, and visitor data sent to a third party. That is not the right trade for this site. But CloudFront already has the data. Every request it serves is logged: date, time, URL, status code, referrer. The plan was to capture those logs in S3 and query them with Athena. No browser code, no cookies, no external services.

It did not go as planned.

## the s3 log bucket

The first step — creating a dedicated S3 bucket for CloudFront access logs — was mostly straightforward. One non-obvious requirement: **Object Ownership**.

S3 buckets now default to `BucketOwnerEnforced`, which disables ACLs entirely. That seems like the right choice — ACLs are a legacy access control model and bucket policies are the current recommendation. But CloudFront standard logging uses ACL-based delivery under the hood. It grants a specific log delivery account write access via ACL. With ACLs disabled, the CloudFront logging configuration cannot be applied.

The correct setting is `BucketOwnerPreferred`. ACL grants remain possible, but any objects written by external accounts are owned by the bucket owner. It is a narrower exception than re-enabling full ACL mode, and it is what CloudFront logging requires. The AWS documentation mentions this, but not prominently enough to catch before you hit the error.

## the free plan wall

Bucket configured. Next step: enable logging on the distribution.

```
InvalidArgument: Distributions with the Free pricing plan can't have
the following features: Standard logging
```

We had not encountered the phrase "Free pricing plan" before this error. The distribution has been handling real traffic, serving HTTPS, applying security headers, running WAF rules. Nothing in normal operation hints at a feature restriction.

CloudFront has a plan-based pricing model: Free ($0/month), Pro ($15/month), Business ($200/month), Premium ($1,000/month). The Free plan includes DDoS protection, managed WAF rules, CDN, edge compute, and TLS. It does not include logging. Standard logging is a Pro feature.

This is separate from the traditional CloudFront pay-per-use pricing. The distribution was created on the Free plan — likely the default at the time — and the logging restriction is invisible until you try to use it.

## the waf logging attempt

The distribution has an auto-created WAF WebACL with three managed rule groups. WAF inspects every request, and WAF can log to S3. That looked like a viable zero-cost alternative — same traffic data, different delivery path.

S3 buckets used for WAF logging have a naming requirement: the bucket name must start with `aws-waf-logs-`. We created `aws-waf-logs-tacedata` and ran `put-logging-configuration` against the WebACL.

```
WAFFeatureNotIncludedInPricingPlanException:
Enable WAF logging requires PRO plan
```

Same wall. Both CloudFront standard logging and WAF logging are gated behind Pro.

One detail worth noting: WAF had already created an `AWSLogs/` folder stub in the bucket before the API call returned the error. Deleting the bucket required emptying it first.

## what upgrading would cost

The Pro plan is $15/month. It adds logging, but it also bundles CAPTCHA challenges, AI traffic analytics, header-based threat filtering, and other features that are not relevant at this scale. It is not a logging add-on — it is a different tier.

Lambda@Edge is an alternative that stays on the Free plan. A viewer-request function could log URI, referrer, and the CloudFront viewer-country header to CloudWatch Logs on every request, then export to S3 for Athena queries. The trade is real: added latency per request, a function to maintain, a different log schema. The complexity exceeds what the problem warrants at current traffic levels.

## where it landed

We closed out the project. $15/month for analytics on a personal portfolio site at current traffic is a real cost without a clear return. The design is sound — if the distribution is ever upgraded to Pro, the implementation picks up from Step 2 with the architecture unchanged.

The Free plan is genuinely useful. It covers everything that matters for availability and security at this scale. What it does not tell you, not prominently, is that all logging — at every layer — requires an upgrade.

Scott

---

*[Analytics project write-up](/projects/analytics/)*
