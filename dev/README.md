# 5K-to-10K Habit Tracker — Data Dictionary & Build Brief

Source data and build notes for a personal habit-tracking website.
Hand this file to a Claude Code session alongside the two CSVs.

## Purpose

This is a **habit and consistency tracker** built around a 15-week run/walk
training plan that finishes with a 10K race on **Sunday, 27 September 2026**.

The running plan is the vehicle. The real goal is showing up: being **active for
~1 hour per day, 5 days per week**. Build the streak counter first; the running
detail is secondary and should never get in the way of the core "did I show up
today" loop.

## Files

| File | Grain | Rows | Role |
|------|-------|------|------|
| `training_plan_days.csv`  | One row per calendar day | 105 | Primary data. Each row is a checkable day. |
| `training_plan_weeks.csv` | One row per week          | 15  | Reference dimension for week-level rollups. |

The two join on `week_number`. The plan runs from `2026-06-15` (day 1) to
`2026-09-27` (day 105, race day).

---

## Data classification (read this first)

Columns fall into two groups. This distinction drives the architecture.

- **[SEED]** — Plan data. Fixed, read-only, ships in the CSV. The app reads it
  and never writes it.
- **[USER-STATE]** — The user's progress. Seeded with safe defaults but
  **owned and written by the app** as the user checks days off. This is the only
  data that changes at runtime.

If you persist to a database, [SEED] columns can be loaded once as reference
data; [USER-STATE] columns are what your write path (check off a day, add a
note) updates.

---

## `training_plan_days.csv` — column reference

| Column | Type | Class | Description |
|--------|------|-------|-------------|
| `date` | DATE (ISO 8601, `YYYY-MM-DD`) | [SEED] | Primary key. Unique per row. Use for all calendar, streak, and sort logic. |
| `day_of_week` | STRING | [SEED] | Full weekday name (e.g. `Monday`). Derived from `date`; included for convenience. |
| `week_number` | INTEGER (1–15) | [SEED] | Foreign key to `training_plan_weeks.week_number`. |
| `day_of_plan` | INTEGER (1–105) | [SEED] | Sequential day counter. Handy for progress ("day 42 of 105"). |
| `phase` | STRING | [SEED] | Training phase: `Base`, `Build`, `Endurance`, `Peak`, `Taper`, `Race`. |
| `session_type` | STRING | [SEED] | What the day is: `Strength & Mobility`, `Steady Run/Walk`, `Long Run/Walk`, `Rest`, `Race - 10K`. |
| `is_active_day` | BOOLEAN (`TRUE`/`FALSE`) | [SEED] | **The core habit flag.** `TRUE` on the 5 active days/week, `FALSE` on rest days. 75 active days total. Streak logic keys off this. |
| `is_run_day` | BOOLEAN (`TRUE`/`FALSE`) | [SEED] | `TRUE` if the day involves running (steady, long, or race). A subset of active days. |
| `session_minutes_target` | INTEGER | [SEED] | Planned active minutes. ~60 on most active days (the 1-hour floor); rises above 60 on late long days (up to 85 at peak); `0` on rest days. |
| `run_interval_minutes` | INTEGER (nullable) | [SEED] | The run/walk interval portion in minutes. Blank on strength and rest days. A subset of `session_minutes_target`. |
| `run_walk_ratio` | STRING (nullable) | [SEED] | Run:walk interval ratio in minutes, e.g. `3:1` = run 3 min / walk 1 min. Blank on non-run days. |
| `session_detail` | STRING | [SEED] | Human-readable workout description, safe to show as the day's instructions. |
| `coaching_focus` | STRING | [SEED] | Short coaching cue for the day. Good for a subtitle, tooltip, or AI-prompt context. |
| `completed` | BOOLEAN (`TRUE`/`FALSE`) | **[USER-STATE]** | Seeded `FALSE`. Set `TRUE` when the user checks the day off. Binds to the checkbox. |
| `completed_date` | DATE (nullable) | **[USER-STATE]** | Seeded blank. Timestamp of when the user marked it done (may differ from `date`). |
| `notes` | STRING (nullable) | **[USER-STATE]** | Seeded blank. Free-text journal entry per day. Primary hook for AI feedback (see below). |

### Notes on the values

- Booleans are the literal strings `TRUE` / `FALSE` (upper-case) for clean,
  unambiguous parsing. Cast to native booleans on import.
- `run_interval_minutes`, `run_walk_ratio`, `completed_date`, and `notes` may be
  empty strings in the CSV — treat empty as null.
- `session_detail` and `coaching_focus` contain commas and are quoted per RFC
  4180. Use a real CSV parser, not a naive split.

---

## `training_plan_weeks.csv` — column reference

| Column | Type | Class | Description |
|--------|------|-------|-------------|
| `week_number` | INTEGER (1–15) | [SEED] | Primary key. Joins to the days table. |
| `start_date` | DATE | [SEED] | Monday that starts the week. |
| `end_date` | DATE | [SEED] | Sunday that ends the week. |
| `phase` | STRING | [SEED] | Phase label for the week. |
| `long_run_minutes` | INTEGER or `-` | [SEED] | Duration of the week's long run/walk interval work. `-` in race week 15. |
| `long_run_ratio` | STRING | [SEED] | Run:walk ratio for the week. |
| `steady_run_minutes` | INTEGER or `-` | [SEED] | Interval work duration on the two steady days. `-` in race week 15. |
| `active_days` | INTEGER | [SEED] | Active days that week (5). |
| `run_days` | INTEGER | [SEED] | Running days that week (3). |
| `weekly_focus` | STRING | [SEED] | One-line theme for the week. Good for a phase/week banner. |

---

## Weekly day template (weeks 1–14)

The same shape repeats each week. Week 15 is a custom taper into the race.

| Day | Session type |
|-----|--------------|
| Monday | Strength & Mobility |
| Tuesday | Steady Run/Walk |
| Wednesday | Strength & Mobility |
| Thursday | Steady Run/Walk |
| Friday | Rest |
| Saturday | Long Run/Walk |
| Sunday | Rest |

These weekday assignments are a sensible default, not sacred. If the user shifts
sessions to different weekdays, the app should treat `date` as the source of
truth and let `day_of_week` ride along.

---

## Habit / streak logic (the part that matters most)

Define a **"showed up" day** as a row where `is_active_day = TRUE` AND
`completed = TRUE`.

- **Current streak**: consecutive `is_active_day = TRUE` days (ignoring rest
  days) that are all `completed = TRUE`, counting back from the most recent past
  active day. Rest days do **not** break a streak — skip over them.
- **Weekly adherence**: for a given `week_number`,
  `count(completed = TRUE AND is_active_day = TRUE) / 5`.
- **Overall progress**: `count(completed = TRUE AND is_active_day = TRUE) / 75`.

Ship the current-streak counter and a weekly checklist first. Everything else is
enhancement.

---

## Suggested architecture (a "learn AWS meaningfully" starter)

Keep the first pass small and finishable.

- **Front end**: static site (S3 + CloudFront).
- **Plan data ([SEED])**: load both CSVs once into a single DynamoDB table,
  partition key `date`. Treat as read-only reference.
- **Progress ([USER-STATE])**: writes (`completed`, `completed_date`, `notes`)
  go through API Gateway to a small Lambda that updates the same item by `date`.
- **Import job**: a one-off script that parses the CSVs and seeds the table.

Do not over-normalize on the first pass. Two flat files and one table is enough
to get a working streak tracker, which is the point.

## AI hook

The `notes` field plus `coaching_focus` is the natural place for AI. A Lambda
can take a journal entry, the day's `coaching_focus`, and recent completion
history, call the Claude API, and return short contextual encouragement or
pattern flags (e.g. "third missed Tuesday in a row — want to move Strength to
Mondays?"). This turns a checkbox grid into something that coaches.

## Conventions

- No emojis anywhere in the UI or generated text. Use plain text or `[LABEL]`
  prefixes if labels are needed.
- `date` is the single source of truth for ordering and identity.
- Never overwrite [SEED] columns from the write path.
