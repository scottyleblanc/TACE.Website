---
title: "the disable button is one prompt away"
date: 2026-05-21T00:00:00
draft: true
tags: ["security", "ai", "github", "developer-tools"]
summary: "AI coding assistants optimize for completing the task in front of them.  When the friction blocking that task is a security control, helpfulness can become harm."
---

I've been reflecting on the [CISA post](/posts/sec-cisa/), and a scenario comes to mind.

A developer is trying to push a commit.  GitHub's push protection flags a secret in the
diff and blocks the push.  The developer is on a deadline, frustrated, sure the warning is
a false positive — or sure that "it's fine, it's just a test value."  They open their AI
coding assistant and ask:

> "GitHub is blocking my push because of secret scanning.  How do I get this through?"

What happens next depends on the assistant.  A well-tuned one pushes back: *are you sure
the value isn't actually a credential?  If the scan is wrong, the right fix is to mark it
as a false positive in the GitHub UI; here's how.*  A less-tuned one just answers the
question that was asked.  The answer might be `--no-verify`.  It might be the exact UI
flow to bypass push protection with "this is a false positive."  It might be the account-
level setting to disable scanning entirely.

In every case, the friction goes away.  In some of those cases, the friction was
protecting the developer — and the organization, and whoever depends on the systems behind
the credentials — from exactly the mistake they were about to make.

---

To be clear: I have no idea what tools the Nightwing contractor was using.  Krebs reported
that commit logs showed explicit commands to disable GitHub's secret detection.  That
tells us **what** happened, not **why** or **how**.  This post isn't a claim about that
specific contractor.

It's a claim about a pattern I see playing out across the industry, including in my own
day-to-day work with these tools.

---

AI coding assistants are optimized to complete the task in front of them.  That objective
is what makes them useful.  But "complete the task" and "complete the task safely" are not
the same instruction, and most assistants — out of the box, with default prompting — treat
them as the same.

When a developer hits friction, the assistant's job is to remove the friction.  Sometimes
that's exactly right: the developer is fighting a misconfigured linter, an obsolete CI
check, a deprecated tool.  Sometimes it's exactly wrong: the friction is a guardrail, and
the assistant just held the door open while the developer walked through.

The disable button used to require deliberate effort.  Find the setting.  Read the docs.
Type the command.  That effort was friction in its own right — friction that gave the
developer one more chance to ask "wait, why is this here?"  AI assistants have collapsed
that effort.  The disable button is now one prompt away from anyone willing to ask the
question.

---

A handful of patterns I see repeatedly:

- `git push --no-verify` to bypass pre-commit hooks
- Adding the file to `.gitignore` after it's already been committed (doesn't help — the
  secret is still in history — but it's a common first suggestion)
- Walking the user through GitHub's push-protection bypass UI ("select 'false positive'
  and continue")
- Recommending the account- or repo-level setting to disable secret scanning
- `git filter-branch` or `git filter-repo` to scrub the secret from history *after* it has
  been pushed — legitimate when used for remediation, but sometimes suggested as an
  alternative to rotating the credential
- Force pushing to "clean up" the visible history (which doesn't reliably remove the
  secret from GitHub's index, but the suggestion gets made anyway)

None of these are illegitimate in every context.  All of them are dangerous when offered
without first asking whether the warning was right.

---

The recommendation that follows isn't "stop using AI assistants." I use them daily.  It
also isn't "AI vendors need to do better," though that's true.

It's this: any security control that lives on the developer's workstation can be reached
by an AI assistant on that workstation.  If you depend on workstation-local controls to
prevent credential exposure, you depend on the assistant choosing not to remove them — or
on the developer choosing not to ask.

The controls that matter are the ones an AI on the workstation cannot reach:

- **Branch protection rules** that block force pushes and require status checks, enforced
  server-side.
- **Organization-level secret scanning** with bypass disabled at the org level, not the
  user level.
- **CI-side credential scanning** that runs after the push and fails the build regardless
  of what the developer's local config says.
- **Pre-receive hooks** on the Git server, where the workstation has no say.

These don't depend on the developer making the right call, or the assistant suggesting
the right path.  They fail closed.

---

This is the part I want to land: AI coding assistants are powerful precisely because they
remove friction.  Security depends on the right kind of friction being preserved.  The two
goals are in tension, and the tension is going to keep showing up — in incidents we read
about, and in commits we write ourselves.

The honest version of "what would I have done in their place" includes the possibility
that an assistant I trusted walked me to the disable button before I had time to think
about it.  That's the scenario that came to mind.

The next time the friction shows up, I want to remember the CISA repo.  And I want to ask
the question the assistant didn't.

---

## Further reading

- [I learned this lesson, with smaller stakes](/posts/sec-cisa/) — the CISA post that prompted this
- [GitHub: About push protection](https://docs.github.com/en/code-security/secret-scanning/introduction/about-push-protection) — what push protection actually does and how it's configured
- [GitHub: Enabling secret scanning for your organization](https://docs.github.com/en/code-security/secret-scanning/enabling-secret-scanning-features/enabling-secret-scanning-for-your-repository) — org-level enforcement options
