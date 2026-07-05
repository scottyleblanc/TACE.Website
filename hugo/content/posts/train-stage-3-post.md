---
title: "training tracker: stage 3 — building for a user who isn't here yet"
date: 2026-07-04T10:00:00
draft: false
tags: ["aws", "dynamodb", "cognito", "migration", "claude-api", "ai", "python", "train", "10k"]
summary: "third post in the training tracker series: migrating the data model from single-user to multi-tenant before the second user exists, and writing the specs for an AI coach before writing a line of its code."
---

### A Table That Only Ever Knew One Person

*This is the third post in a series documenting the build of a personal running habit tracker at train.tacedata.ca.  The [project page](/projects/running-tracker-proj/) covers the full scope.  [Stage 1](/posts/train-stage-1-post/) put the infrastructure and data in place; [Stage 2](/posts/train-stage-2-post/) was the security audit before extending the app any further.  This post covers the two things that happened next: quietly rebuilding the data model around a real identity instead of a single date, and writing out, in full, what an AI coach for this app should actually do — before either one shipped a visible feature.*

---

### The plan bent

Stage 2 ended with a promise: next comes multi-user — a second person logging in, filling out an intake form, and getting their own plan. That is still the plan. It just is not what happened next.

What happened next is that the AI coach became the more interesting problem, and it could not be built safely on the table as it existed. Every table in this app was keyed on the calendar date alone — `date` as the only identifier, because there was only ever one person using the app. A coach that answers "what's my long run Saturday?" has to know *whose* Saturday it is answering for. Bolting that onto a date-only table would mean the coach either trusts whatever it's told, or the app quietly assumes there is still only one person — neither of which is a foundation worth building anything on top of.

So the decision was to do the identity work now, and defer the rest of "letting someone new sign up" for later. The database gets rebuilt to know what a user is. The onboarding form, the invite system, a second real person actually arriving — all of that waits. It is genuinely useful groundwork either way: whenever a second person does show up, the data model will already be ready for them.

---

### Spec-first, again

Stage 2 was a security review before any new feature. This stage borrowed the same instinct for a different reason: before writing a line of the coach's code, the whole thing got written out as a design document first — what routes exist, what data flows through the pipeline, what the safety rail looks like, and exactly what the eval harness has to prove before any of it ships. Three documents, in order: the identity foundation, the coach's contract and architecture, and its prompts and test suite.

The reasoning is the same reasoning behind the audit. A feature that talks to an AI model on your behalf, using your real data, and is expected to recognize when a question needs a doctor rather than a coach — that is not something to improvise mid-build. Writing it down first meant every hard call (what counts as a medical question, what the model is and is not allowed to invent, how a second user's data stays invisible to the first) got made once, deliberately, instead of drifting in as an afterthought three files deep into an implementation.

---

### Why "add a user_id column" isn't a real option

This is worth explaining plainly, because it is a genuinely useful thing to understand about how this class of database works, and it is not obvious if you have only used a relational one.

Picture the training-plan table as a single filing cabinet drawer, with one folder per day, filed by date. That was fine when only one person used it. The moment a second person shows up, "June 15th" stops meaning one specific day — it means one specific day *for someone*. The obvious-sounding fix is to just write a name on the front of each folder.

DynamoDB will not let you do that. The way a table is organized — its *key* — is fixed the moment the table is created and cannot be changed afterward, only added to at the point of creation. There is no "add a column to the front of the filing system" operation. The only way to reorganize is to build a second drawer, with folders now labeled by person-then-date, and physically move every folder across.

That is the entire shape of this stage's real work: stand up a new table keyed on identity-then-date, copy every row across with the identity attached, and repoint the app at the new drawer without anyone noticing the switch happened.

---

### What the migration actually involved

The identity used is the one Cognito (the login system) issues internally the moment you sign in — a permanent, opaque ID that has nothing to do with your email address. That distinction turned out to matter in a small, very human way partway through: it surfaced that the address I log in with and the address the daily briefing email goes to are not the same address. Same person, two different systems, easy to conflate — a good reminder that "the account" and "the inbox" are not automatically one thing.

There was a second account already sitting in the login system, unused, left over from early setup. Rather than manufacture a fake identity to test isolation, that existing spare became the stunt double: give it a couple of rows in the new table, then confirm — for real, through the running Lambda code, not just by reasoning about it — that this second identity gets a clean "not found" for every one of the first identity's days, on both reading and writing. It did, on both. Reused rather than invented, which is a small point in favor of not deleting things you might need later.

The copy step ran in two passes: once as a dry run to preview exactly what would move, then for real, with a script that checks its own work afterward — comparing row counts and every piece of user progress (completed days, dates, notes) between the old table and the new one, refusing to call the migration done if a single field disagreed. It was also re-run once more after the app was fully switched over, on the chance that something got written to the old table in the narrow window before the switch — cheap insurance against a very specific, very avoidable kind of data loss.

The one place this stage's own process nearly tripped: the new application code and the "which table does the app actually talk to" setting were, briefly, going to be changed out of order — new code, old table, for a few seconds. New code expects a filing system organized by identity; the old table is still organized by date alone. Caught before it went out, but worth naming, because it's the exact kind of ordering mistake that a migration like this exists to be careful about.

---

### The shape of the coach that's coming

None of the coach's actual code exists yet — that is deliberately next, not this stage. But the design is settled, and it is worth describing, because the two ideas underneath it are the same two ideas that make the rest of this app trustworthy.

First: the coach never gets handed raw data and asked to figure things out. The app computes the real answer in code first — your current streak, this week's plan versus what you've actually done, your next long run — and hands the model those computed facts directly. The model's job is to talk about them, not derive them. That is the same instinct as Stage 1's decision to keep plan data and progress data on separate, clearly labeled tracks: let the deterministic part of the system be deterministic, and only ask the probabilistic part to do the part it's actually good at.

Second: before the coach model ever sees a question, a separate, fast check looks at it first and asks one question only — does this sound like it's about pain, an injury, or anything a physiotherapist should be answering instead of an app? If yes, the question gets a canned, honest redirect to a real physio, and the coach model is never even called. That check is deliberately built to fail safe — if it's ever unsure, it defers, rather than risk letting a question through it shouldn't have. A running coach that occasionally over-refers is a minor inconvenience. One that occasionally plays doctor is not a trade worth making.

---

### What comes next

The identity foundation is live. The specs for the coach — its routes, its data model, its safety rail, and the prompts and test suite that have to pass before any of it is trusted — are written. What's left is building it: the conversation storage, the routes, the rail as its own provable step before anything talks to a model, and only then the coach turn itself.

---

*Next in the series: Stage 4 — the coach itself — turning a design document into something that answers a real question, grounded in a real plan, without ever pretending to be a doctor.*

---

[running tracker — project page](/projects/running-tracker-proj/)
