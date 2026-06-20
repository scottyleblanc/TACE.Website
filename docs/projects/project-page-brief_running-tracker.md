# Build Brief — projects page for the running habit tracker

For a Claude Code session working in the **tacedata.ca** Hugo repo.
Goal: add a new entry to the `projects` section for the running habit tracker
build, matching the existing project pages in style and structure.

---

## Instructions for the build session

1. **Match the repo, do not guess.** Open an existing project page under the
   content directory (e.g. the `tacedata.ca — this site` or
   `security remediation` project) and mirror its front matter fields, file
   location, slug pattern, and layout exactly. The draft below provides the
   *content and voice*; the repo provides the *structure*. Where the two differ,
   the repo wins.

2. **File location & slug.** Place this alongside the other project pages, using
   the same convention you find there. Suggested slug: `running-tracker`
   (adjust to match the existing pattern, e.g. `running-tracker-proj` if that is
   the house style).

3. **Listing.** The projects index appears to auto-list section pages by date.
   Confirm the new page surfaces on `/projects/` after build; set the front
   matter `date` so it sorts where you want it.

4. **Style to match:**
   - Lowercase titles, "topic — angle" form.
   - Lowercase section headings in the body.
   - Concise, specific, first-person, candid. Outcome- and decision-focused.
     Honest about status (this one is in progress, not a finished retrospective).
   - No emojis. Plain text or `[LABEL]` prefixes only.

5. **Date.** The draft uses a placeholder publish date — set it to the real one.

6. Do not invent metrics or claims of completion. The project is at the
   planning/early-build stage; keep the status section truthful.

---

## Draft content (place into the Hugo page body; align front matter to the repo)

Front matter below is a starting point — replace field names/format with whatever
the existing project pages use.

```markdown
---
title: "running habit tracker — a 15-week build on aws and claude"
date: 2026-06-18
author: "Scott LeBlanc"
description: "A personal habit tracker built around a 15-week run/walk training plan. Less about running, more about building a daily habit — and a vehicle to learn DynamoDB, Lambda, Cognito, and the Claude API by building something I open every day."
draft: false
---

## the idea

I am training for a 10K in late September after a 20-year layoff. But the race is
not really the point. The point is consistency: being active an hour a day, five
days a week, and actually checking it off. So I am building a habit tracker around
the plan — and using it as an excuse to learn AWS and the Claude API by building
something I will use every morning, rather than from another tutorial.

## the data model

The plan is seed data: 105 rows, one per calendar day from the first session to
race day. The grain is deliberate. The habit I am tracking is "did I show up
today," not "did I run" — so every day, including rest days, is a checkable row,
and the active-day flag is what the streak counter keys off.

The schema separates two kinds of column: plan data the app only ever reads, and
progress data the app writes when I check a day off. Keeping that line clean is
what makes the build reproducible — the plan loads once as reference, and the only
thing that changes at runtime is my own progress.

## the architecture

Small on purpose. A static front end on S3 and CloudFront. The plan seeded into a
single DynamoDB table. Progress writes go through API Gateway to a Lambda. The
API key lives in Secrets Manager, never in the browser. The whole first version is
one table, a couple of routes, and a streak counter — enough to be useful the day
it ships.

## the ai layer

The plan is small enough that the entire dataset fits in a single prompt, so the
coach endpoint sends the whole thing to the Claude API with each question — no
vector database, no retrieval machinery. It answers grounded in my real plan and
progress: what is my long run Saturday, what is my current streak, I felt wrecked
after the weekend, should I repeat this week. Two rails matter — it answers only
from the plan, and it defers anything injury-related to my physio rather than
playing doctor.

## going multi-user (phase two)

The interesting step up: letting a second person log in and generate their own
plan from an intake form. Claude writes the plan in the same schema the tracker
already understands, which is validated before it is stored — generated output is
treated as untrusted input. Multi-tenancy comes from a composite key (user plus
date) and Cognito for isolation, so each person sees only their own data.

## why build it this way

Ship phase one and live with it before adding the rest. A streak tracker I open
every day beats a feature-rich one I am still building in August. The AI coach and
the plan generator are real goals, but they are enhancements layered on a core
that already works — the same discipline the running plan runs on: nail the
modest, repeatable thing first.

## status

In progress. Phase one — the tracker — first. Notes and write-ups to follow as the
AWS and AI pieces come online.
```

---

## Optional: short blurb for the projects index

If the index needs a manual summary/excerpt rather than pulling `description`,
use:

> A personal habit tracker built around a 15-week run/walk training plan — and a
> vehicle to learn DynamoDB, Lambda, Cognito, and the Claude API by building
> something I open every day.
