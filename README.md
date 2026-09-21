# Job Applications — Internship Finder & Tracker

An automated bot that finds Bachelor's/Master's-eligible internships in the
**US or Canada**, posted in the last 7 days, and tracks them in this repo, so
you always have a running history of what's out there and what you've
applied to.

## What it does NOT do

It does **not** submit applications for you. Fully autonomous form-filling on
job platforms was considered and deliberately left out:

- Most platforms (LinkedIn, Handshake, Workday, individual employer ATSes)
  prohibit automated account/application activity in their terms of service,
  and can ban accounts that do it.
- Most application flows are behind CAPTCHAs/anti-bot checks anyway.
- Generic, unreviewed answers to per-employer application questions tend to
  hurt your odds rather than help.
- This holds even if personal info (resume, contact details) is supplied —
  the ToS/anti-bot/reliability problems are about the target platforms, not
  about who provides the data, and storing personal info in CI secrets/logs
  is its own exposure risk best avoided.

Instead, the bot does the (legitimately automatable) hard part — finding and
tracking — and leaves the final "review and click apply" step to you.

## How it works

1. **`scripts/fetch_internships.py`** pulls the current listings from the
   [SimplifyJobs Summer2026-Internships](https://github.com/SimplifyJobs/Summer2026-Internships)
   community board (a public, scrape-friendly JSON feed maintained for
   exactly this purpose), filters to postings that are:
   - currently active,
   - open to **Bachelor's** and/or **Master's** students,
   - based in the **US or Canada** (remote-in-US/Canada included), and
   - posted within the last **7 days**,

   and updates `data/tracked_jobs.json` (source of truth) plus
   `APPLICATIONS.md` (human-readable table) with anything new. Postings that
   later disappear from the upstream feed are marked `expired`.

   There's no reliable public "applicant count" signal for these postings —
   that data lives inside LinkedIn's own UI, which this bot deliberately
   doesn't scrape — so it isn't used as a filter.

2. **`scripts/create_issues.py`** opens one GitHub issue per new match (label
   `internship-tracker`), capped at 25 per run so a burst of new postings
   can't spam the repo or trip GitHub's rate limits — any overflow just gets
   picked up on the next run. Each issue has the company, role, term,
   location, country, eligible degrees, and a direct apply link.

   Issues (and `APPLICATIONS.md` rows) get extra labels/markers so you can
   spot what matters at a glance without narrowing the underlying matches:
   - `big-tech` + ⭐ — Google, Amazon, Meta, Microsoft, Apple, NVIDIA, Tesla,
     and similar (see `BIG_TECH_COMPANIES` in `scripts/lib.py`)
   - `posted-today` + 🔥 — posted the same day it was found, vs. anywhere in
     the 7-day window
   - `usa` / `canada` — which country the posting is in

   These sort to the top within each status group; nothing is filtered out
   because of them.

3. **You apply manually**, then **close the issue**. A second workflow
   (`.github/workflows/mark-applied.yml` → `scripts/mark_applied.py`)
   automatically flips that job's status to `applied` in the tracker and
   commits the update. Reopening an issue flips it back to `new`.

4. `.github/workflows/find-internships.yml` runs step 1–2 every 15 minutes
   plus on-demand via `workflow_dispatch`. GitHub's `schedule` trigger has a
   practical floor of 5 minutes and runs can lag a little under load, so
   this is "as close to always-on as Actions allows," not instant. You can
   tighten the cron in that file down to `*/5 * * * *` if you want, but a
   private repo's free Actions-minutes budget (2,000 min/month) will drain
   faster the more often it runs — 15 minutes uses roughly 500–1000 min/month
   depending on run length; 5 minutes roughly triples that.

`APPLICATIONS.md` is split into a **🇺🇸 USA** section and a **🇨🇦 Canada**
section, each with its own new/applied/expired/big-tech/posted-today counts.
A posting open to both countries appears in both sections.

## One-time setup

1. Merge this branch into the repo's default branch — GitHub only fires
   `schedule` triggers for workflows that live on the default branch.
2. In **Settings → Actions → General → Workflow permissions**, select
   "Read and write permissions" so the bot's `GITHUB_TOKEN` can push commits
   and open/close issues. No other secrets are required.
3. Watch this repo (you're automatically watching your own repos) so new
   internship issues show up in your GitHub notifications.

## Tracker state

`data/tracked_jobs.json` was seeded with the 564 US/Canada Bachelor's/Master's-
eligible internships posted in the 7 days before this bot was set up
(flagged `"backfilled": true`) so `APPLICATIONS.md` starts populated instead
of empty. Backfilled entries don't get issues filed retroactively — only
postings found from here on do, which keeps day one from opening hundreds of
issues at once.

## Extending it

- Add more sources by extending `fetch_internships.py` (e.g. specific
  companies' public Greenhouse/Lever/Ashby job-board APIs) — merge their
  listings into the same `is_eligible`/`is_recent` filtering before building
  records.
- Adjust `TARGET_DEGREES` or `RECENCY_DAYS` in `scripts/fetch_internships.py`
  to widen/narrow what counts as a match.
- Add/remove companies in `BIG_TECH_COMPANIES` (`scripts/lib.py`) to change
  what counts as "big tech."
