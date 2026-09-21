"""
Fetches the current internship listings from the SimplifyJobs community board,
filters them to postings explicitly open to Bachelor's/Master's students and
posted within the last RECENCY_DAYS days, and updates the local tracker
(data/tracked_jobs.json + APPLICATIONS.md) with any new matches.

There's no reliable public applicant-count signal for these postings (that
data lives behind LinkedIn's own UI, which this bot deliberately doesn't
scrape), so we don't filter on it.

Postings that were tracked as "new" but have disappeared from the active feed
(filled or pulled) are marked "expired" so stale issues can be auto-closed.

Writes new_matches.json (untracked) listing just this run's new matches, for
scripts/create_issues.py to turn into GitHub issues. Also sets the GitHub
Actions output `new_count`.
"""
import datetime
import json
import os
import sys

import requests

from lib import load_tracked, save_tracked, render_markdown

LISTINGS_URL = (
    "https://raw.githubusercontent.com/SimplifyJobs/"
    "Summer2026-Internships/dev/.github/scripts/listings.json"
)
NEW_MATCHES_PATH = os.path.join(os.path.dirname(__file__), "..", "new_matches.json")
TARGET_DEGREES = {"Master's", "Bachelor's"}
RECENCY_DAYS = 7


def fetch_listings() -> list:
    resp = requests.get(LISTINGS_URL, timeout=30)
    resp.raise_for_status()
    return resp.json()


def is_eligible(job: dict) -> bool:
    """Active + open to our target degrees. Used for expiry detection too,
    so a posting isn't wrongly marked "expired" just for aging past the
    recency window below — only for actually disappearing upstream."""
    return bool(job.get("active")) and bool(TARGET_DEGREES & set(job.get("degrees") or []))


def is_recent(job: dict, now: datetime.datetime) -> bool:
    """Only postings from the last RECENCY_DAYS days are worth a fresh
    application / issue — older still-active postings are left tracked-but-
    ignored rather than queued."""
    date_posted = job.get("date_posted")
    if not date_posted:
        return False
    posted_at = datetime.datetime.utcfromtimestamp(date_posted)
    return (now - posted_at) <= datetime.timedelta(days=RECENCY_DAYS)


def to_record(job: dict, now: str) -> dict:
    date_posted = job.get("date_posted")
    date_posted_iso = (
        datetime.datetime.utcfromtimestamp(date_posted).isoformat() + "Z"
        if date_posted
        else None
    )
    return {
        "id": job["id"],
        "company": job.get("company_name", "Unknown"),
        "title": job.get("title", "Unknown role"),
        "terms": job.get("terms", []),
        "locations": job.get("locations", []),
        "degrees": job.get("degrees", []),
        "url": job.get("url"),
        "date_posted": date_posted_iso,
        "status": "new",
        "found_at": now,
        "applied_at": None,
        "issue_number": None,
        "issue_url": None,
        "expired_issue_closed": False,
        "backfilled": False,
    }


def main() -> None:
    now_dt = datetime.datetime.utcnow()
    now = now_dt.isoformat() + "Z"
    listings = fetch_listings()
    eligible = [j for j in listings if is_eligible(j)]
    current_ids = {j["id"] for j in eligible}
    recent_eligible = [j for j in eligible if is_recent(j, now_dt)]

    tracked = load_tracked()
    new_matches = []

    for job in recent_eligible:
        if job["id"] not in tracked:
            record = to_record(job, now)
            tracked[job["id"]] = record
            new_matches.append(record)

    for job_id, record in tracked.items():
        if record["status"] == "new" and job_id not in current_ids:
            record["status"] = "expired"
            record["expired_at"] = now

    save_tracked(tracked)
    render_markdown(tracked)

    with open(NEW_MATCHES_PATH, "w") as f:
        json.dump(new_matches, f, indent=2)

    print(f"Fetched {len(listings)} listings, {len(eligible)} Bachelor's/Master's-eligible "
          f"active, {len(recent_eligible)} within last {RECENCY_DAYS}d, "
          f"{len(new_matches)} new.", file=sys.stderr)

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"new_count={len(new_matches)}\n")


if __name__ == "__main__":
    main()
