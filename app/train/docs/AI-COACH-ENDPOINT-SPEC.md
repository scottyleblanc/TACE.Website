# AI Coach — Endpoint & Architecture Spec

For a Claude Code session working in the training-tracker repo (the AWS +
Claude API app behind train.tacedata.ca).

This is a **contract and architecture** spec. It defines routes, request/response
shapes, the request pipeline, the data model, config, and the security boundary.
It deliberately does **not** contain final prompt text, the classifier's label
taxonomy, or eval rubrics — those are built in the implementation phase against
the real repo. See [DEFERRED] at the end.

Design principles carried from earlier phases: preserve the security boundary
(every read scoped to the authenticated user), let code do arithmetic and the
model do language, and treat user-authored text as untrusted input into the model.

---

## [SCOPE] What this feature is

A per-user AI running coach the user talks to in **multiple named conversation
threads**, saved and resumable. The coach answers grounded in the user's real
plan and progress. A **hard pre-model rail** intercepts clinical/injury/medical
questions and defers them to the user's physiotherapist before the coach model is
ever called.

Confirmed design decisions feeding this spec:

| Decision | Choice |
|----------|--------|
| Conversation model | Multi-turn, saved, resumable, **multiple named threads** |
| Multi-user | Live (Cognito), endpoint scoped to authenticated `user_id` |
| Coach scope | Per-user setting: `plan_only` or `plan_plus_general` |
| Facts | Computed in code, handed to the model as answers |
| Medical rail | **Hard** — model-based classifier, short-circuits before the coach |
| Conversation storage | **Separate `conversations` table** |
| Model selection | **Config-driven**, not hardcoded (see [CONFIG]) |

---

## [INSTRUCTIONS] For the build session

1. **Match the repo, do not guess.** Open an existing Lambda handler and mirror
   its structure, the Cognito authorizer / `user_id` extraction, the DynamoDB
   client setup, and the existing response-shaping helper. Where this spec and
   the repo differ on mechanics, the repo wins. This spec owns the *contract*;
   the repo owns the *conventions*.
2. Build the routes in the order under [BUILD ORDER]. Do not build the coach
   turn until thread CRUD and the rail are provably working.
3. Do not invent prompt wording or the classifier taxonomy — those are called out
   as [DEFERRED] and belong in a focused follow-up, ideally with an eval set.
4. No emojis in code or output; use `[LABEL]` prefixes, consistent with the seed
   data conventions.

---

## [RESPONSE ENVELOPE] House shape for every response

Every route returns a consistent JSON envelope. `message` is always safe to log —
never a credential, secret ARN, or the Anthropic key.

```json
{
  "ok": true,
  "data": {},
  "message": "human-readable, safe-to-log"
}
```

- `ok: false` for expected, handleable outcomes (thread not found, scope invalid).
- Return a 4xx/5xx and `ok: false` for failures; reserve thrown/500 for genuinely
  unrecoverable states (missing secret, config unreadable).

---

## [DATA MODEL] `conversations` table (new, separate)

Separate from the plan table because the access patterns are unrelated — "render
my calendar" vs "list my threads / load a thread." Single partition per user keeps
the tenant boundary identical to the plan table.

Partition key `user_id`. Sort key uses type prefixes so one query serves each
access pattern.

**Conversation (thread) item**

| Attribute | Key | Notes |
|-----------|-----|-------|
| `user_id` | PK | Owner. From the auth token, never the body. |
| `sk` | SK | `CONV#{conversation_id}` |
| `title` | | User-supplied thread name |
| `created_at` / `updated_at` | | ISO 8601 |
| `message_count` | | Maintained on each coach turn |

**Message item**

| Attribute | Key | Notes |
|-----------|-----|-------|
| `user_id` | PK | Owner |
| `sk` | SK | `MSG#{conversation_id}#{timestamp}` |
| `role` | | `user`, `coach`, or `rail` |
| `content` | | Message text |
| `created_at` | | ISO 8601 |
| `rail_triggered` | | bool, present on rail-deferred turns |

Access patterns, each a single `Query`:
- List a user's threads: `PK = user_id AND begins_with(sk, "CONV#")`
- Load a thread: `PK = user_id AND begins_with(sk, "MSG#{conversation_id}#")`

**User settings item** (may live here or on the existing settings store — match
the repo): `coach_scope` in `{plan_only, plan_plus_general}`, default `plan_only`.

---

## [ROUTES] Contract

All routes require a valid Cognito session; `user_id` is derived server-side.

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/conversations` | Create a named thread. Body: `{title}`. Returns `conversation_id`. |
| GET | `/conversations` | List the user's threads (metadata only). |
| GET | `/conversations/{id}` | Load a thread's messages (rolling window; paginate for full history). |
| PATCH | `/conversations/{id}` | Rename. Body: `{title}`. |
| DELETE | `/conversations/{id}` | Delete thread and all its messages. |
| POST | `/conversations/{id}/messages` | **The coach turn.** Body: `{content}`. |
| GET | `/settings` | Read `coach_scope`. |
| PATCH | `/settings` | Update `coach_scope`. |

Every handler must confirm the target thread's `user_id` matches the caller and
return `ok: false` / 404 otherwise. A user requesting another user's
`conversation_id` gets nothing.

---

## [PIPELINE] The coach turn — `POST /conversations/{id}/messages`

Order matters; the rail is step 4, before any coach-model call.

1. **Auth.** Derive `user_id` from the verified Cognito token.
2. **Ownership.** Load the thread; 404 if it is not this user's.
3. **Load context.** Recent messages for this thread (rolling window, size from
   config), the user's `coach_scope`, and the user's plan data (scoped to
   `user_id`). Load the **merged** plan view — seed (`training-plan-v2`) with
   active `training-plan-overrides` and user-state applied, using the same merge
   logic as `days_api.py`/`daily_email.py`. The coach must never read the raw seed
   alone, or it will contradict the physio adjustments. Reuse the shared merge
   module (extracted so all three consumers share one source of truth).
4. **[RAIL] Hard pre-check.** Send the incoming message to the classifier model
   (config: `RAIL_MODEL`). If classified clinical/injury/medical:
   - Persist the user message and a canned deferral reply (`role: rail`,
     `rail_triggered: true`).
   - Return the canned reply. **Do not call the coach model.**
   See [RAIL CONTRACT].
5. **Compute facts in code.** Streak, this week's completed vs planned, next long
   run, today's session, weeks-to-race — computed from the **merged** view (step
   3), so the facts reflect the physio-adjusted plan, not the original seed. The
   model receives answers, not raw rows.
6. **Assemble prompt.**
   - System instructions selected by `coach_scope` (`plan_only` = answer only
     from plan/progress; `plan_plus_general` = general running knowledge allowed,
     but plan facts remain authoritative and the rail still applies).
   - A delimited `[FACTS]` block (the computed values).
   - A delimited `[PLAN DATA]` block, explicitly labelled as data, not
     instructions.
   - The rolling conversation history, then the new user message.
7. **Call the coach model** (config: `COACH_MODEL`).
8. **Persist** the user message and the coach reply; bump `updated_at` and
   `message_count`.
9. **Return** the coach reply in the envelope.

---

## [RAIL CONTRACT] The hard medical rail

- A separate, cheap, fast classifier model call that runs **before** the coach.
- Binary decision for v1: is this message seeking clinical / injury / medical /
  diagnostic / treatment guidance? If yes, short-circuit.
- On trigger: return a fixed, friendly deferral pointing the user to their
  physiotherapist. The coach model never sees the message.
- The trigger is logged (`rail_triggered: true`) so behaviour is auditable.
- Fail-safe: if the classifier call errors or is ambiguous, **defer** (treat as
  triggered) rather than pass through to the coach. Safety defaults closed.
- The classifier prompt and its exact label boundary are [DEFERRED] — build with
  an eval set of representative medical and non-medical messages.

---

## [CONFIG] Model selection and knobs

No model IDs or tuning constants hardcoded. Source them from **SSM Parameter
Store** (recommended — change models without redeploying) or Lambda environment
variables (simpler; match whatever the repo already uses).

| Key | Purpose |
|-----|---------|
| `COACH_MODEL` | Coach model ID (quality-tier) |
| `RAIL_MODEL` | Classifier model ID (cheap/fast-tier) |
| `HISTORY_WINDOW_TURNS` | Rolling-window size sent per call |
| `MAX_TOKENS` | Coach response cap |

The Anthropic API key stays in Secrets Manager, read server-side only, never in
config or client.

---

## [CONTEXT STRATEGY]

The Claude API is stateless; each coach turn resends history. Send a rolling
window of recent turns (`HISTORY_WINDOW_TURNS`), not the whole thread — the
`[FACTS]` block re-grounds every call, so deep history matters less than in a
general chatbot. Summarize-and-drop older turns only if/when threads get long;
not built for v1.

---

## [IAM] Least privilege for the coach Lambda role

- DynamoDB: read/write on the `conversations` table and read on the plan table
  (`training-plan-v2`) **and** the overrides table (`training-plan-overrides`) —
  the merged plan view needs both — scoped as tightly as the repo's existing
  policies (prefer a leading-key condition on `user_id` where practical).
- Secrets Manager: `GetSecretValue` on the specific Anthropic key secret only.
- SSM: `GetParameter(s)` on the specific config path only (if using Parameter
  Store).
- CloudWatch Logs only. No wildcard resources.

This role is the real perimeter around the API key — over-permission here turns an
app-layer bug into an account-layer one. Scope it hard.

---

## [BUILD ORDER]

1. `conversations` table + thread CRUD (create/list/get/rename/delete), scoped to
   `user_id`. No model calls yet.
2. `/settings` read/update for `coach_scope`.
3. The [RAIL] classifier as a standalone step — provably deferring medical
   messages — before wiring the coach.
4. The coach turn: facts-in-code, prompt assembly, model call, persistence.
5. Only then refine prompts and build the eval set.

Definition of done for the phase: a user can hold multiple named, resumable
conversations grounded in their own plan; medical questions are deflected before
the coach model; models are swappable via config; and no route can read another
user's data.

---

## [DEFERRED] Not in this spec — build with an eval set

- Final coach system-prompt wording (both scope modes).
- The classifier prompt and its exact medical/non-medical boundary.
- The eval set itself: representative questions with rubrics (stayed grounded,
  deferred the medical one, got the streak right).
- Response streaming (v1 is non-streaming with a thinking indicator).
- Summarization of old turns (only when thread length demands it).
