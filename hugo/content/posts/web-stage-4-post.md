---
title: "stage 4: building the site itself"
date: 2026-04-03T06:00:00
draft: false
tags: ["hugo", "papermod", "aws", "cloudfront"]
summary: "Getting the site into a state worth sharing — PaperMod setup, profile home page, content structure, and a few problems solved along the way."
aliases: ["/posts/site-content-post/"]
---

*This is the fourth post in a series documenting the build of tacedata.ca — moving from WordPress to a Hugo static site on AWS. [Stage 1](/posts/web-stage-1-post/) chose Hugo and PaperMod. [Stage 2](/posts/web-stage-2-post/) migrated email. [Stage 3](/posts/web-stage-3-post/) built the AWS deploy pipeline.*

---

Stage 3 left us with a working pipeline — push to main, site deploys to CloudFront. What it did not leave us with was a site worth visiting. The content was placeholder, the layout was default, and the URL was a CloudFront test domain. Stage 4 was about fixing all of that.

## switching to PaperMod

We evaluated three themes in Stage 1 and selected Blowfish. By the time we were ready to write real content, it was not working out — rendering inconsistencies, configuration complexity that exceeded what the site actually needed. We switched to PaperMod.

The migration was mostly mechanical: remove Blowfish submodule, add PaperMod submodule, rework `hugo.toml` for PaperMod's configuration model, move CSS overrides into `assets/css/extended/custom.css`. PaperMod reads `site.Copyright` as a top-level key in `hugo.toml`, not `params.copyright` — that caught us once.

## profile home page

PaperMod has a profile mode that turns the home page into an intro layout rather than a post list. Name, title, image, buttons, social icons. That is the right structure for this site — the home page should orient a visitor, not dump a list of posts at them.

The social icons render in a fixed position in PaperMod's default template — above the buttons. We wanted them below. PaperMod partial overrides live in `layouts/partials/` — create a file with the same name as the theme's partial and Hugo uses yours instead. We overrode `index_profile.html` and reordered the elements. The theme files themselves are never touched.

## fixing directory navigation

Once the pipeline was running, we noticed that navigating to `/posts/` worked, but `/posts` — no trailing slash — returned a 403. Hugo generates `posts/index.html`. S3 stores it at that key. CloudFront with OAC does not resolve directory indexes the way a web server would — it looks for the exact key, finds nothing, and returns an error.

The fix is a CloudFront Function: a small JavaScript handler that runs on every incoming request and rewrites the URI before CloudFront looks up the S3 object. If the URI ends in `/`, append `index.html`. If it has no extension, append `/index.html`. CloudFront's JS runtime is ES5 — `endsWith()` and `includes()` are not available. `slice(-1)` and `lastIndexOf('.')` do the same job.

## the content

The site shipped with:

- **Home** — profile intro with title, buttons to Projects and Blog, GitHub and LinkedIn icons
- **About** — TACE Data background, the evolution from Oracle DBA to automator to AI to cloud - and where the site is headed
- **Projects** — tacedata.ca site write-up: problem, solution, architecture diagram, content deployment workflow diagram, tech used, what we learned
- **Blog** — blog posts covering each stage of the build

The architecture and deployment diagrams on the project page are Mermaid — written in the Markdown file, rendered in the browser. No external diagramming tool, no image files to maintain.

## baseURL

One issue surfaced when the pipeline ran against the live CloudFront URL: PaperMod uses absolute URLs, and the `baseURL` in `hugo.toml` was set to `tacedata.ca` — which did not exist yet. CSS failed to load. Images broke.

The fix was to move `baseURL` out of the config file entirely and into a GitHub Actions variable (`vars.SITE_URL`), passed to Hugo at build time with `--baseURL "${{ vars.SITE_URL }}"`. The config file has no domain baked into it. When the domain cutover came, one variable update was all that was required.

Scott

---

*Next in the series: [Stage 5 — cutting over a website](/posts/web-stage-5-post/) — moving tacedata.ca from Websavers DNS to Route 53 and attaching a proper SSL certificate.*
