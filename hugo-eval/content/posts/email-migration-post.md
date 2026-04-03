---
title: "migrating email before touching dns"
date: 2026-04-01
draft: true
tags: ["email", "fastmail", "dns", "aws"]
summary: "Why email migration had to happen before any DNS work — and how I moved tacedata.ca email to Fastmail without losing anything."
---

DNS changes are irreversible in the sense that once nameservers propagate, the old configuration is gone. Before I touched a single DNS record, I needed to know that email was sorted. Not planned — sorted. Working, tested, confirmed.

The reason is straightforward: AWS Certificate Manager sends validation emails. Route 53 changes trigger notifications. If email breaks mid-cutover, I am locked out of the process at the worst possible moment.

## the current setup

Three addresses in use on Websavers: personal, accounting, and contact. All three had inbox history. The accounting and contact addresses were aliases forwarding to the personal inbox — that is the model I wanted to preserve.

## choosing Fastmail

The options were Zoho Mail (free), Fastmail (~$5/month CAD), and Google Workspace (~$8/month). Google Workspace is overbuilt for a personal domain. Zoho is viable but the free tier has constraints that would eventually become friction.

Fastmail is the right size. Custom domain support, alias support, built-in IMAP import for inbox history. $5/month is acceptable for something I will use daily.

## the DNS records

Moving email means updating DNS records — specifically the records that tell the internet where to deliver mail for tacedata.ca:

- **MX records** — two records pointing at Fastmail's inbound mail servers
- **SPF TXT record** — tells receiving servers which servers are allowed to send mail for this domain
- **DKIM CNAME records** — three records (fm1, fm2, fm3) that allow Fastmail to cryptographically sign outbound mail
- **DMARC TXT record** — policy record that tells receivers what to do with mail that fails SPF or DKIM checks

At this stage, these records were added to Websavers DNS — not Route 53. Route 53 did not exist yet. The Websavers nameservers were still authoritative, so that is where the records went.

All of these records were later replicated into Route 53 in Stage 5 before the nameserver delegation changed. The sequencing matters: if you change nameservers before replicating MX records, mail delivery breaks for however long DNS propagation takes.

## inbox history

Fastmail has a built-in IMAP import tool. I pointed it at the Websavers mail server, it pulled everything across, and the inbox history landed in Fastmail intact. Nice to have, not a hard requirement — but it worked cleanly so there was no reason to leave it behind.

## what this stage confirmed

Email is working on Fastmail. All three addresses receive mail. Aliases are configured. The DNS records are in place and validated.

The site and DNS work that follows can proceed without email being a risk factor.

Scott
