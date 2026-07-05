# Identity Foundation — Canonical `user_id` & Users Table

For a Claude Code session (Sonnet) working in the training-tracker repo (the AWS +
Claude API app behind train.tacedata.ca).

This spec establishes one stable per-user identity across every table and adds a
small users/profile record. It is written as **sequential, executable steps** with
explicit checks and stop conditions. Do the steps in order; do not skip the
verification gate in Step 1.

Companion to the AI Coach endpoint spec — the `coach_scope` setting referenced
there becomes an attribute on the users record defined here.

---

## [CONTEXT] Why this, and the one thing not to do

Multi-tenancy rests on one stable `user_id` per person, used as the partition key
everywhere. The correct value is the Cognito `sub` claim: immutable, not email
(emails change), not anything self-minted.

This is DynamoDB, not a relational database. The tables are **not** linked by
declared foreign keys, and there are no joins. They simply share the same
`user_id` value, and each is queried independently with it. Referential
integrity ("every conversation's user_id points at a real user") is enforced in
application code, not by the database.

**Do not** add foreign-key constraints, a join table, or any cross-table
referential mechanism. There is no such feature to use and the design does not
need one. If a step seems to call for a foreign key, that is the relational
reflex — stop and re-read this section.

---

## [INSTRUCTIONS] For the build session

1. **Match the repo, do not guess.** Mirror existing table definitions, the
   Cognito authorizer, the `user_id` extraction helper, and the DynamoDB client
   setup. This spec owns the contract; the repo owns the conventions.
2. Execute the steps in order. Each has a definition of done. Do not proceed past
   a step whose check fails — report instead.
3. No emojis; use `[LABEL]` prefixes, consistent with existing conventions.
4. Produce production-ready, documented code — not a sketch.

---

## [STEP 1] Verify the canonical `user_id` — hard gate, do this first

Do not assume the existing identity is correct. Confirm it.

1. Inspect how the plan table (`user_id` + `date`) populates `user_id`, and how
   the API derives it from the request.
2. Confirm `user_id` is the **Cognito `sub`** claim from the verified token —
   not email, username, or a value taken from the request body.

**If it is already the Cognito `sub`:** the canonical-ID foundation is done.
Record that finding and continue to Step 2.

**If it is anything else (email, self-minted, client-supplied):** STOP. Changing
the identity key is a data migration, not a code edit — every existing row is
keyed on the old value. Do not silently change it. Report:
- what the current `user_id` actually is,
- where it is set,
- the tables and row counts affected,
- a proposed migration approach.
Wait for a decision before proceeding.

**[DONE]** A written confirmation that `user_id` is the Cognito `sub` everywhere,
or a migration report if it is not.

**[RESOLVED — repo state as of this spec]** The `training-plan` table has **no
`user_id` at all**: it is keyed on `date` alone, `GET /days` uses `Scan`, and the
API does no per-user scoping (`lambda/days_api.py`). The email Lambda
(`lambda/daily_email.py`) also `Scan`s the whole table. This is the STOP case —
but the decision has been made: **do the migration now**, single active user,
so multi-user is a later drop-in with no second migration. Proceed to [STEP 1.5].

---

## [STEP 1.5] Migrate to a `user_id`-partitioned table — the decision is made

DynamoDB key schema is **immutable** — you cannot add a partition key to the
existing `training-plan` table, and a GSI does not solve write-partitioning
(writes still collide on `date` across users). So:

1. Create a **new table** (e.g. `training-plan-v2`): PK = `user_id` (Cognito
   `sub`), SK = `date`. Mirror the existing item shape (`build_item()` in
   `scripts/seed_dynamo.py`) plus the `user_id` attribute.
2. Retrieve the existing account's `user_id` (Cognito `sub`) from the User Pool
   `tacedata-train-pool`. Write a one-time migration script that reads every
   current item (keyed on `date`) and rewrites it under `{user_id: <sub>, date}`.
3. **Repoint `DYNAMODB_TABLE` on BOTH Lambdas** — `tracker-api` *and*
   `tracker-email`. Both read this table; the migration breaks either one left
   on the old name.
4. Update the readers/writers to key on `{user_id, date}`:
   - `days_api.py` — `Query` the user partition for `GET /days`;
     `get_item`/`update_item` on `{user_id, date}` (cross-user access simply
     misses → 404, no extra ownership check needed).
   - **`daily_email.py`** — replace the full-table `_scan_all()` with a `Query`
     on a configured owner `user_id` (env var, resolved from the single `users`
     record). Keep single-recipient behavior; structure the resolve step so a
     multi-user fan-out (loop over the `users` table) is a later drop-in.
   - `seed_dynamo.py` — `build_item()` writes a `user_id`; the table name and
     key move to the composite key.
   - The overrides table (`training-plan-overrides`) is keyed on `date` and is
     single-user reference data — leave it keyed on `date` for now; the merge in
     both Lambdas is unchanged.

**[DONE]** All 105 days load and check off end-to-end for the original account
against `training-plan-v2`; the daily email still arrives; nothing reads the old
table.

---

## [STEP 2] Define the users table

Add a `users` table (or a `PROFILE` item type on an existing table — match the
repo's preference; a dedicated small table is preferred if the repo has no strong
convention).

| Attribute | Key | Notes |
|-----------|-----|-------|
| `user_id` | PK | Cognito `sub`. No sort key needed (one profile per user). |
| `email` | | From the token claims |
| `display_name` | | User-facing name |
| `coach_scope` | | `plan_only` (default) or `plan_plus_general` |
| `race_goal` | | Optional (e.g. distance) |
| `race_date` | | Optional, ISO 8601 |
| `created_at` / `updated_at` | | ISO 8601 |

This record holds what is about the **person**, not about a plan-day or a message.

**[DONE]** Table/item exists with `user_id` as PK and the attributes above.

---

## [STEP 3] Provision the profile on first login — idempotent

A user's profile record is created the first time they are seen, and only if
absent.

1. On the first authenticated request per user (or a Cognito post-confirmation
   trigger — match the repo's auth flow), upsert a users record if none exists.
2. Set `coach_scope` to `plan_only` by default. Populate `email` / `display_name`
   from the verified token claims.
3. The operation must be **idempotent**: a returning user with an existing profile
   is left unchanged (use a conditional put on absence of `user_id`).

First-login provisioning also covers the **existing** account — no separate
backfill script is needed for the single active user; they get a record the next
time they authenticate. When multi-user onboarding/plan-generation is eventually
built, it must **update** this record (adding `race_goal`/`race_date` etc.), not
create it — the record already exists from first login. Do not let onboarding
clobber `coach_scope` or re-create the row.

**[DONE]** A new authenticated user gets exactly one profile record; repeated
logins never overwrite it.

---

## [STEP 4] Point `coach_scope` at the users record

If the AI Coach settings routes were built against a standalone settings item,
repoint them:
- `GET /settings` reads `coach_scope` from the users record.
- `PATCH /settings` writes it there, scoped to the authenticated `user_id`.

If the coach feature is not yet built, note that its settings routes must read and
write `coach_scope` here rather than creating a separate settings store.

**[DONE]** `coach_scope` is read and written on the users record, scoped to the
caller.

---

## [STEP 5] Enforce integrity in application code (no foreign keys)

1. Every write that carries a `user_id` takes it from the verified token, never
   from the request body. A client cannot assert someone else's `user_id`.
2. Trust the auth boundary as the source of truth: a valid token corresponds to a
   real user, so a separate "does this user exist" lookup is generally
   unnecessary. If a defensive check is added before a coach turn, it is an
   application-code lookup against the users table — not a database constraint.
3. Do not add cross-table foreign keys or joins (see [CONTEXT]).

**[DONE]** No route trusts a client-supplied `user_id`; no foreign-key or join
mechanism was introduced.

---

## [DEFINITION OF DONE] Whole spec

- One canonical `user_id` (Cognito `sub`) is the partition key across the plan
  table, the conversations table, and the users table.
- A users/profile record exists per authenticated user, created idempotently on
  first login, with a safe `coach_scope` default.
- Tables share the `user_id` value only — no foreign keys, no joins, no join
  table.
- No route accepts a client-supplied `user_id`.

---

## [DEFERRED] Not in this spec

- Second-user onboarding, plan generation, or admin UI (multi-user is deferred;
  the schema here is already `user_id`-partitioned so it drops in later without a
  second migration).
- Per-user email fan-out and the invite mechanism (`daily_email.py` stays
  single-recipient; `auth_guard.py`'s `ALLOWED_EMAILS` stays the signup gate).
- Additional profile attributes beyond those in Step 2, added when a feature needs
  them rather than up front.

The existing-user backfill is **no longer needed** — first-login provisioning in
Step 3 covers the single active account.
