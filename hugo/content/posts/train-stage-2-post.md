---
title: "training tracker: stage 2 — the security audit nobody asks for"
date: 2026-06-20T10:00:00
draft: false
tags: ["security", "appsec", "audit", "aws", "cognito", "cloudfront", "tls", "train", "10k"]
summary: "second post in the training tracker series: before adding a single new feature, the working single-user app gets a proper security review.  What an audit of a small web app actually looks at, and why shipping something is the start of the job, not the end of it."
---

### A Working App Is Not the Same Thing as a Safe One

*This is the second post in a series documenting the build of a personal running habit tracker at train.tacedata.ca.  The [project page](/projects/running-tracker-proj/) covers the full scope.  [Stage 1](/posts/train-stage-1-post/) put the infrastructure and data in place; the [previous stages](/projects/running-tracker-proj/) finished a working single-user app — login, a daily session card, a streak counter, a check-off box, and a morning briefing email.  This post is about the thing that happens before any of that gets extended: a security audit.*

---

The app worked.  I could log in from my phone, check off a workout, watch the streak tick up, and get a briefing email at 7am.  By the usual definition of "done," it was done.

That is exactly the moment worth being suspicious of.

A thing that works and a thing that is safe to leave running on the public internet are two different claims, and the gap between them is invisible from the front end.  The app behaving correctly tells you nothing about how it behaves when someone is deliberately misbehaving toward it.  So before adding a second user, before the AI coach, before anything new — the build stopped, and the whole surface got reviewed as if a stranger were poking at it.

---

### Why audit something this small

It is a personal running tracker.  One user.  The worst-case breach is that someone learns I went for a jog.  Why bother?

Two reasons.

The first is that "it's only small" is precisely the reasoning that leaves most of the internet exposed.  The size of the app has nothing to do with the size of the surface it presents.  A login page, a public web address, and a database behind an API is the same fundamental shape whether it serves one person or a million — and the categories of weakness are identical at both scales.

The second is closer to home.  My background is database security — locking down who can connect, what they can see, and proving it after the fact.  That discipline does not automatically transfer to a web front end.  The browser, the login handshake, the headers a server sends, the way a session is held open — that is a different surface with its own failure modes, and I am honest that I knew the principles far better than I knew the specifics.  Building the app was the easy half.  Learning what it was quietly exposing was the half worth writing down.

---

### What an audit of a web app actually looks at

A security review is not one check.  It is a tour through a set of distinct categories, each of which is a well-understood place where web applications tend to go wrong.  You go category by category, and for each one you ask the same two questions: *is this handled, and how do I know?*  Here is the tour, in plain terms.

**The connection itself.**  Before anything else, can the conversation between the phone and the server be read or tampered with in transit?  This is the encryption layer — making sure traffic is encrypted, modern, and can't be quietly downgraded to something weaker.

**Who is allowed in.**  The login and identity layer.  Can someone get in who shouldn't?  Can they sidestep the login handshake, or sign themselves up when sign-up is supposed to be closed?  This is the front door, and it gets the most attention.

**What they can touch once inside.**  Being logged in is not the same as being allowed to do anything.  Every action the app exposes has to independently confirm that *this* user is permitted to do *this* thing to *this* piece of data — and that nobody can reach across into someone else's records.  Getting the front door right but leaving the interior doors open is one of the most common real-world failures.

**What the app is willing to accept.**  Every field the app takes in from the outside is a place where someone can send something unexpected — the wrong kind of value, something far too large, something malformed, something crafted to confuse the app.  The category here is simply: does the app validate what it accepts, or does it trust whatever shows up?

**How the app's output is handled.**  The flip side — when the app shows information back, can content that a user supplied earlier be turned into something that runs in the browser rather than just being displayed?  This is the family of issues behind a great many web compromises, and it comes down to treating user-supplied content as data, never as instructions.

**The instructions the server gives the browser.**  Modern browsers will enforce a long list of safety rules on a site's behalf — but only if the server explicitly asks for them.  Left unset, the browser assumes the most permissive defaults.  This category is about sending that set of instructions so the browser becomes an ally in defending the page rather than a neutral party.

**How your session is held open.**  Once you log in, something has to remember that you're logged in so you aren't re-entering credentials all day.  *Where* and *how* that "remember me" token is kept is a category of its own, because a session held carelessly is a session that can be stolen.

**The ground it all stands on.**  Finally, the infrastructure underneath — the storage and the delivery network.  Is the underlying storage actually private, or can it be reached directly, bypassing all the controls in front of it?

---

### Confirm first, then harden

The point of going category by category is that an audit is not only a hunt for problems.  Most of it, done properly, is confirmation — actively proving that the controls you believe are in place really do hold when pushed.  A good number of these categories came back exactly as intended: the front door held, the interior doors held, the connection was sound, and the storage underneath was genuinely sealed off.  Confirming those is as much a part of the work as finding gaps, and it is the part people skip.

Where the review did surface gaps, they were concentrated in the categories that sit between the browser and the app — the browser-instruction layer, the way the session was held, and the strictness of what the app accepted and how it rendered things back.  Encouragingly, nothing critical or high-severity turned up; the items that did were the kind a working-but-unreviewed app almost always carries.  Every one of them has since been closed, and re-verified live.

I am deliberately not publishing the specifics of what was found or how — that detail lives in a private operations repository, not on the public web, which is itself a small example of the discipline this whole post is about.  The honest headline is enough: the app was in decent shape, the review still found real things worth fixing, and they are fixed.

---

### The part worth keeping

There is a habit, in this kind of work, of treating "it's live" as the finish line.  The site loads, the feature works, ship it, move on.

The audit is the argument against that.  Putting something on the internet is the beginning of an obligation, not the end of an effort.  The same surface that lets me check off a run from my phone is a surface someone else can probe — and that does not go away because the app is small, or personal, or "just for me."  Standing something up and securing-and-maintaining something are two different jobs, and only the first one is visible from the outside.

It is the same instinct the training plan itself runs on.  The work that counts is rarely the dramatic part.  It is showing up to do the unglamorous, repeatable thing — checking the locks on a door you already believe is shut — long after the part that gets applause is finished.

---

### What comes next

With the single-user build reviewed and hardened, the foundation is solid enough to build on.  Next is the genuinely interesting step up: letting a second person log in, fill in an intake form, and get their own plan — which means partitioning every piece of data per user so each person sees only their own, and treating anything generated for them as untrusted input until it's validated.

---

*Next in the series: Stage 3 — going multi-user — turning a personal app into one that safely holds more than one person's data.*

---

[running tracker — project page](/projects/running-tracker-proj/)
