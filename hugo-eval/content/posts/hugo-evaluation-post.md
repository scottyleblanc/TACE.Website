---
title: "choosing a static site generator"
date: 2026-03-29
draft: true
tags: ["hugo", "meta"]
summary: "How I evaluated Hugo and three themes before committing to a stack — and what I was actually looking for."
---

Before writing a line of content or touching a DNS record, I needed to decide whether Hugo was actually the right tool. The old site was WordPress. Moving to a static site generator is a meaningful change in workflow — no admin panel, no plugins, no database. Everything lives in Markdown files and a git repository. That is either liberating or inconvenient depending on how you work.

I ran a short evaluation to find out which it was going to be for me.

## what I was looking for

The site has two distinct purposes: a professional portfolio and a working journal. That shaped the criteria:

- **Fast local iteration** — edit a file, see the result in a browser immediately
- **Clean output** — no bloat, fast page loads, nothing I didn't put there
- **Git-native workflow** — every change tracked, deployable from a push
- **Theme with real flexibility** — I was not going to build a theme from scratch

I evaluated three themes against these criteria: Blowfish, Congo, and PaperMod.

## the theme evaluation

**Congo** was ruled out early — build errors with Hugo 0.158 that I could not resolve cleanly. Not worth fighting a theme that doesn't work with the current Hugo version.

**Blowfish** was my initial pick. Good documentation, flexible layout options, interesting feature set. I had it running and configured. Then the rendering issues started — inconsistencies between local preview and build output, configuration complexity that grew faster than the site's actual needs. It was doing too much.

**PaperMod** is what I landed on. Minimal, fast, well-maintained. Dark/light toggle, profile home page, clean navigation. The configuration is straightforward and the output is exactly what it looks like in the source. No surprises.

## what the evaluation confirmed

Hugo is the right tool. The local workflow is exactly what I wanted — edit a Markdown file, `hugo server` picks it up immediately, browser refreshes. No build step to wait on, no CMS to navigate. A text editor and a terminal is all that is required.

The git workflow is a natural fit. Every content change is a commit. The history of the site is the history of the repository. Deployment is a push to main.

The evaluation took about a week of evenings. It was worth doing before committing to a full migration — I confirmed the workflow before investing in the infrastructure.

Scott
