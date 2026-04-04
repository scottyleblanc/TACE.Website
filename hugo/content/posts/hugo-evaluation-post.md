---
title: "stage 1: choosing a static site generator"
date: 2026-03-29
draft: false
tags: ["hugo", "meta"]
summary: "Evaluated Hugo and three themes before committing to a stack — and what we were actually looking for."
---

Before writing a line of content or touching a DNS record, we needed to decide whether Hugo was actually the right tool. The old site was WordPress. Moving to a static site generator is a meaningful change in workflow — no admin panel, no plugins, no database. Everything lives in Markdown files and a git repository. That is either liberating or inconvenient depending on how you work.

I prefer to work from the command line whenever possible, and notepad++ is a good friend.  Still learning the workings of Git, but comfortable with the basics.

## what we were looking for

The site has two distinct purposes: a professional portfolio and a working journal. That shaped the following criteria:

- **Fast local iteration** — edit a file, see the result in a browser immediately
- **Clean output** — light weight, fast page loads, nothing we didn't put there
- **Git-native workflow** — every change tracked, deployable from a push
- **Theme with real flexibility** — Building a theme from scratch not an option - unnecessary work give content more valuable.

I evaluated three themes against these criteria: Blowfish, Congo, and PaperMod.

## the theme evaluation

**Congo** was ruled out early — build errors with Hugo 0.158 that we could not resolve cleanly. Not worth fighting a theme that doesn't work with the current Hugo version.

**Blowfish** was our initial pick. Good documentation, flexible layout options, interesting feature set. We had it running and configured. Then the rendering issues started — inconsistencies between local preview and build output, configuration complexity that grew faster than the site's actual needs. It was doing too much.

**PaperMod** is what we landed on. Minimal, fast, well-maintained. Dark/light toggle, profile home page, clean navigation. The configuration is straightforward and the output is exactly what it looks like in the source. No surprises.

## what the evaluation confirmed

Hugo is the right tool. The local workflow is exactly what we wanted — edit a Markdown file, `hugo server` picks it up immediately, browser refreshes. No build step to wait on, no CMS to navigate. A text editor and a terminal is all that is required.

The git workflow is a natural fit. Every content change is a commit. The history of the site is the history of the repository. Deployment is a push to main branch.

The evaluation took a couple of evenings. It was worth doing before committing to a full migration.  It was not until I had confirmed the workflow that I made a final call.

Scott 
