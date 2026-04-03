---
title: "stage 5: cutting over a website"
date: 2026-04-03T12:00:00
draft: false
tags: ["aws", "dns", "route53", "cloudfront", "acm", "powershell"]
summary: "Moving tacedata.ca from Websavers DNS to AWS Route 53 — what the cutover actually involves, and how to do it without taking the site down."
---

The new site has been running at a CloudFront URL since Stage 3. Functional, deployed, but not yet at tacedata.ca. The last piece was DNS — moving the domain off Websavers DNS and onto AWS Route 53, and attaching a proper SSL certificate.

It sounds like a small thing. It is not a small thing.  

## what actually had to happen

Before touching a nameserver, we needed to inventory everything that depended on the current DNS setup — not just the website, but email too. tacedata.ca has Fastmail MX records, DKIM CNAME records, SPF and DMARC TXT records. All of it had to be replicated in Route 53 before the nameservers changed. If we missed one, email would break the moment the delegation propagated.

The sequence:

1. Create a Route 53 hosted zone for tacedata.ca
2. Add all DNS records — MX, SPF, DMARC, DKIM CNAMEs, and the www CNAME pointing at CloudFront
3. Request an ACM certificate covering both tacedata.ca and www.tacedata.ca
4. Add the ACM DNS validation records to Route 53
5. Change the nameservers at Websavers to the 4 AWS NS records
6. Wait for the ACM certificate to reach ISSUED status
7. Attach the certificate and custom domain names to the CloudFront distribution
8. Add the A alias record for the root domain
9. Update the site's baseURL and trigger a deploy

That is not an afternoon task — it is a coordinated sequence where order matters and most steps have a dependency on the one before it.

## the registrar/DNS split

One thing worth understanding: domain registration and DNS hosting are separate concerns. We kept Websavers as the registrar — they hold the domain registration — but delegated DNS authority to Route 53 by changing the nameservers. Route 53 is now authoritative for all DNS on tacedata.ca. Websavers is just where the domain is registered.

This is the right way to do it. Transferring the registration itself is a separate process (5-7 days, ICANN window) and is not required for any of this to work.  Also, the site is Canadian, and I did not want to hit any complications regarding region.

## ACM and CloudFront

AWS Certificate Manager issues free SSL certificates, but there is a catch: CloudFront only accepts certificates provisioned in `us-east-1`, regardless of where your other AWS resources live. The certificate has to be requested in that region.  (See PS below)

Validation is DNS-based — ACM gives you two CNAME records to add to your hosted zone, then polls for them. Once it sees them resolve, the certificate issues. With Route 53 already authoritative, this took about 10-15 minutes.

## automating the wait

While the certificate was pending, we needed to check its status periodically until it reached ISSUED. The manual version is running the same AWS CLI command every few minutes and reading the output. Instead, we wrote a small PowerShell loop:

```powershell
do {
    $status = aws acm describe-certificate `
        --certificate-arn "arn:aws:acm:..." `
        --region us-east-1 `
        --profile tace-aws-admin `
        --query 'Certificate.Status' `
        --output text
    Write-Host "$(Get-Date -Format 'HH:mm:ss') — $status"
    if ($status -eq 'ISSUED') { break }
    Start-Sleep -Seconds 30
} while ($true)
```

Run it, walk away, come back when it stops. The pattern — `do { check; if done break; sleep } while ($true)` — is reusable anywhere you are waiting on an external process to reach a target state. We will use this again.

## the runbook

We wrote a full runbook for this stage with every command, all resource IDs, and a step-by-step procedure. If you are doing something similar — Hugo or otherwise — it covers the end-to-end DNS cutover for a static site on S3 + CloudFront.

[Stage 5 runbook — DNS cutover](https://github.com/scottyleblanc/TACE.Website/blob/main/config/runbook-stage5-dns-cutover.md)

More detail in the projects section — [tacedata.ca project write-up](/projects/tacedata-site-proj/)

Scott

---

**PS** — The us-east-1 requirement is not just an arbitrary AWS quirk. Readers who follow AWS news may recall recent outages where a significant portion of the internet went down because so many services rely on us-east-1 for their control plane — even when their actual workloads run elsewhere. For this site, the exposure is low: once the certificate is issued and attached, day-to-day serving does not touch us-east-1. But it is a real dependency worth understanding.
