---
title: 15-week training plan and tracker - built on aws and claude
date: 2026-06-13
draft: false
tags:
  - aws
  - dynamodb
  - lambda
  - cognito
  - claude-api
  - s3
  - cloudfront
  - 10k
  - train
summary: A personal habit tracker built around a 15-week run/walk training plan — and a vehicle to learn DynamoDB, Lambda, Cognito, and the Claude API by building something I open every day.
---

## the idea

I am training for a 10K in late September after a 20-year layoff.  But the race is not really the point.  The point is consistency: being active an hour a day, five days a week, and actually checking it off.  So I am building a habit tracker around the plan — and using it as an excuse to learn AWS and the Claude API by building something I will use every morning, rather than from another tutorial.

## the data model

The data is created from a conversation with Claude, started with a simple prompt:

| I need you to adopt the role of a running coach. I'm considering training for a 5k or 10k race that is currently scheduled for September 27. I am starting from ground zero, meaning I am not currently running, and I have not actively run for over 20 years |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |

Claude created the plan and the seed data: 105 rows, one per calendar day from the first session to race day.  The grain is deliberate.  The habit I am tracking is "did I show up today," not "did I run" — so every day, including rest days, is a checkable row, and the active-day flag is what the streak counter keys off.

The schema separates two kinds of column: plan data the app only ever reads, and progress data the app writes when I check a day off.  Keeping that line clean is what makes the build reproducible — the plan loads once as reference, and the only thing that changes at runtime is my own progress.

## the architecture

Small on purpose.  A static front end on S3 and CloudFront.  The plan seeded into a single DynamoDB table.  Progress writes go through API Gateway to a Lambda.  Auth is Cognito with Google login — no username and password, no self-registration.  A daily briefing email goes out every morning via SES and EventBridge, including rest days.  The whole first version is one table, a couple of routes, a streak counter, and a morning email — enough to be useful the day it ships.  When the AI layer arrives, the Claude API key lives in Secrets Manager, never in the browser.

## single user mvp (phase one)

"Minimum Viable Product" - The first version needs to do three things: show me the plan, let me check a day off, and lock it down so only I can get in.  It also needs to work cleanly from my phone, I don't want a dependency on a workstation.

## security audit (phase two)

Before extending the app to a second user, the single-user build gets a proper security review.  The audit covers the authentication layer, the API, DynamoDB access patterns, secrets management, and the deployment pipeline — what the app exposes, to whom, and whether the controls are doing what they should.  Findings and remediation to follow.

## going multi-user (phase three)

The interesting step up: letting a second person log in and generate their own plan from an intake form.  Claude writes the plan in the same schema the tracker already understands, which is validated before it is stored — generated output is treated as untrusted input.  Multi-tenancy comes from a composite key (user plus date) and Cognito for isolation, so each person sees only their own data.

## the ai layer (phase four)

The plan is small enough that the entire dataset fits in a single prompt, so the coach endpoint sends the whole thing to the Claude API with each question — no vector database, no retrieval machinery.  It answers grounded in my real plan and progress: "what is my long run Saturday?", "I felt wrecked after the weekend, should I repeat this week?".  Guardrails matter — it answers only from the plan, it is a running coach (not a code generator); and it defers anything injury-related to my physio rather than playing doctor.

## why build it this way

Ship phase one and live with it before adding the rest.  A streak tracker I open every day beats a feature-rich one I am still building in August.  The AI coach and the plan generator are real goals, but they are enhancements layered on a core that already works — the same discipline the running plan runs on: nail the modest, repeatable thing first.

## status

In progress.  Phase one — the tracker — first.  Notes and write-ups to follow as the AWS and AI pieces come online.

## build series

- [stage 1 — infrastructure and seed data](/posts/train-stage-1-post/)
- [stage 2 — the security audit](/posts/train-stage-2-post/)
