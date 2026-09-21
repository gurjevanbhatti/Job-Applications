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
   - `posted-today` + 🔥 — posted within the last 24 hours, vs. anywhere in
     the 7-day window
   - `usa` / `canada` — which country the posting is in

   These sort to the top within each status group; nothing is filtered out
   because of them.

3. **You apply manually**, then mark it applied one of two ways:
   - **Close that job's individual issue.** A workflow
     (`.github/workflows/mark-applied.yml` → `scripts/mark_applied.py`)
     flips it to `applied` in the tracker and commits. Reopening flips it
     back to `new`.
   - **Check its box on the pinned "📋 Application Checklist" issue** — a
     single issue the bot keeps updated with a real, clickable GitHub
     checkbox per open match (capped at the 60 highest-priority ones —
     ⭐ big tech and 🔥 last-24h first — so the issue body stays well under
     GitHub's size limit; anything past the cap still has its own issue).
     GitHub only makes checkboxes interactive inside Issue/PR bodies, not in
     a plain repo file, which is why this lives in an issue rather than as a
     checkbox column in `APPLICATIONS.md` itself. Checking a box there
     closes that job's individual issue for you too (and unchecking reopens
     it), via `.github/workflows/sync-checklist.yml` →
     `scripts/handle_checklist_edit.py`, which diffs the issue body
     before/after the edit to see exactly which box flipped.

4. **Optional text message digest** (`scripts/send_sms_digest.py`) — one
   text per run, only when there's something new, one line per job
   (`USA: SWE Intern @ Microsoft - posted now`). See "Optional: text message
   digest" below for setup; it no-ops quietly if unconfigured.

5. `.github/workflows/find-internships.yml` runs steps 1, 2, and 4 every 15
   minutes plus on-demand via `workflow_dispatch`. GitHub's `schedule` trigger has a
   practical floor of 5 minutes and runs can lag a little under load, so
   this is "as close to always-on as Actions allows," not instant. You can
   tighten the cron in that file down to `*/5 * * * *` if you want, but a
   private repo's free Actions-minutes budget (2,000 min/month) will drain
   faster the more often it runs — 15 minutes uses roughly 500–1000 min/month
   depending on run length; 5 minutes roughly triples that.

`APPLICATIONS.md` shows **🇺🇸 USA** and **🇨🇦 Canada** side by side (an HTML
table, since GitHub-flavored markdown has no native side-by-side layout),
each with its own new/applied/expired/big-tech/posted-today counts. A
posting open to both countries appears on both sides. Rows show a relative
"Posted" time (`3 hrs ago`, `2 days ago`) rather than a raw date, computed
fresh on every run so it's always current as of the last sync.

## One-time setup

1. Merge this branch into the repo's default branch — GitHub only fires
   `schedule` triggers for workflows that live on the default branch.
2. In **Settings → Actions → General → Workflow permissions**, select
   "Read and write permissions" so the bot's `GITHUB_TOKEN` can push commits
   and open/close issues.
3. Watch this repo (you're automatically watching your own repos) so new
   internship issues also show up as GitHub's own email/push notifications
   — check **github.com → Settings → Notifications** to confirm "Email" is
   on for Issues if you want that.

### Optional: text message digest (`scripts/send_sms_digest.py`)

Sends one text per run (only when there's something new) via your carrier's
free email-to-SMS gateway, one line per job:
`USA: SWE Intern @ Microsoft - posted now`. This is **best-effort, not
guaranteed delivery** — carriers can silently drop these with no bounce or
error, and several have discontinued their gateways outright. Send yourself
one manual test email before relying on it.

1. Enable 2-Step Verification on the sending Gmail account, then generate an
   app password at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
   (pick "Mail" / name it "job-bot").
2. In this repo: **Settings → Secrets and variables → Actions → New
   repository secret**, add:
   - `GMAIL_ADDRESS` — the Gmail address sending the digest
   - `GMAIL_APP_PASSWORD` — the 16-character app password from step 1
   - `PHONE_SMS_GATEWAY` — `<10-digit-number>@<gateway-domain>`, e.g.
     `4165551234@msg.telus.com` for Koodo/Telus (Koodo's own
     `msg.koodomobile.com` has multiple recent community reports of
     delivery failures — `msg.telus.com` works since Koodo runs on the
     Telus network). Other carriers use their own domain
     (`@vtext.com` Verizon, `@txt.att.net` AT&T, `@tmomail.net` T-Mobile,
     etc.).
3. **Test it, in this order:**
   - First, confirm the gateway itself works, with zero code involved: from
     any email client, send a plain email to your `PHONE_SMS_GATEWAY`
     address. If nothing arrives on your phone within a few minutes, that
     gateway/carrier combo doesn't work for your number — try a different
     domain (e.g. `msg.telus.com` instead of `msg.koodomobile.com`) or
     switch to Twilio.
   - Once that works, confirm the bot's wiring: go to this repo's
     **Actions** tab → **Test SMS** (in the left sidebar) → **Run
     workflow**. This sends one fixed test text through the exact same
     code path as the real digest, without waiting for an actual new
     internship to appear. A run that finishes green but no text arrives
     usually means a typo in one of the three secrets — check the run's
     logs for the printed confirmation.
   - The real digest only fires from `find-internships.yml` when
     `new_matches.json` actually has something in it, so don't expect a
     text on every 15-minute run — only when a genuinely new posting shows
     up.
4. If it turns out unreliable, a paid service like Twilio is more
   dependable but costs a small fee per text and needs its own API
   credentials — ask if you want that built instead.

Without these three secrets set: the real digest (`send_sms_digest.py`)
just no-ops quietly every run, and the manual test
(`send_test_sms.py`/"Test SMS" workflow) fails loudly with a clear
"missing secret" message. Either way, nothing in the rest of the bot breaks
if you skip this section.

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
