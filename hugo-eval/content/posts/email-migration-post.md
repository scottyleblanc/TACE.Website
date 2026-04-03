---
title: "stage 2: migrating email before touching dns"
date: 2026-04-01
draft: false
tags: ["email", "fastmail", "dns", "aws"]
summary: "Why email migration had to happen before any DNS work — moving tacedata.ca email to Fastmail without losing anything."
---

DNS changes are irreversible in the sense that once nameservers propagate, the old configuration is gone. Before we touched a single DNS record, we needed to know that email was sorted. Not planned — sorted. Working, tested, confirmed.

The concern was straightforward: if email broke mid-cutover, we could be locked out of the domain at the worst possible moment — unable to receive AWS account notifications, ACM alerts, or anything else tied to the tacedata.ca inbox. As it turned out, the cutover required no email interaction at all. But that is only knowable in hindsight — sorting email first was the right call.

## the current setup

Three addresses in use on Websavers: personal, accounting, and contact. All three had inbox history. The accounting and contact addresses were aliases forwarding to the personal inbox — that is the model we wanted to preserve.

## choosing Fastmail

The options were Zoho Mail (free), Fastmail (approx $5/month CAD), and Google Workspace (approx $8/month). Google Workspace is overbuilt for a personal domain. Zoho is viable but the free tier has constraints that would eventually become friction.

Never thought I would pay for email, but Fastmail is the right choice. Custom domain support, alias support, built-in IMAP import for inbox history. $5/month is acceptable for something used daily.

## the DNS records

Moving email means updating DNS records — specifically the records that tell the internet where to deliver mail for tacedata.ca:

- **MX records** — two records pointing at Fastmail's inbound mail servers
- **SPF TXT record** — tells receiving servers which servers are allowed to send mail for this domain
- **DKIM CNAME records** — three records (fm1, fm2, fm3) that allow Fastmail to cryptographically sign outbound mail
- **DMARC TXT record** — policy record that tells receivers what to do with mail that fails SPF or DKIM checks

At this stage, these records were added to Websavers DNS — not Route 53. Route 53 did not exist yet. The Websavers nameservers were still authoritative, so that is where the records went.

All of these records were later replicated into Route 53 in Stage 5 before the nameserver delegation changed. The sequencing matters: if you change nameservers before replicating MX records, mail delivery breaks for however long DNS propagation takes.

## inbox history

Fastmail has a built-in IMAP import tool. We pointed it at the Websavers mail server, it pulled everything across, and the inbox history landed in Fastmail intact. Nice to have, not a hard requirement — but it worked cleanly so there was no reason to leave it behind. Changing providers turned out to be easier than expected.

## what this stage confirmed

Email is working on Fastmail. All three addresses receive mail. Aliases are configured. The DNS records are in place and validated.

The site and DNS work that follows can proceed without email being a risk factor.

Scott
