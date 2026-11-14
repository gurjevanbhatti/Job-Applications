"""
Files a GitHub issue for each tracked job that doesn't have one yet (skipping
one-time backfilled history), and auto-closes issues for postings that just
expired. Requires `gh` (preinstalled on GitHub-hosted runners) authenticated
via GH_TOKEN.

Issue creation is capped per run (MAX_ISSUES_PER_RUN) to stay well under
GitHub's abuse-detection rate limits even if a burst of new postings shows
up in one day; any overflow just waits for the next run.
"""
import datetime

from lib import (
    load_tracked,
    save_tracked,
    render_markdown,
    is_posted_today,
    update_checklist,
    gh,
    CHECKLIST_LABEL,
)

LABELS = "internship-tracker,masters-eligible"
MAX_ISSUES_PER_RUN = 25


def issue_body(record: dict) -> str:
    return (
        f"<!-- job_id: {record['id']} -->\n"
        f"**Company:** {record['company']}\n"
        f"**Role:** {record['title']}\n"
        f"**Term(s):** {', '.join(record.get('terms', []))}\n"
        f"**Location(s):** {', '.join(record.get('locations', [])) or 'Unspecified'}\n"
        f"**Country:** {', '.join(record.get('countries', [])) or 'Unspecified'}\n"
        f"**Degrees eligible:** {', '.join(record.get('degrees', []))}\n"
        f"**Apply:** {record['url']}\n\n"
        "---\n"
        "Close this issue once you've applied — it will automatically mark this "
        "internship **Applied** in `APPLICATIONS.md` and `data/tracked_jobs.json`. "
        "Reopening it flips it back to **New**. Or just check its box on the "
        "pinned **Application Checklist** issue instead of closing issues one by one."
    )


def ensure_labels() -> None:
    # `gh issue create --label` fails outright if a label doesn't already
    # exist in the repo, so create/update them idempotently up front.
    for name, color, description in [
        ("internship-tracker", "0E8A16", "Filed by the internship tracker bot"),
        ("masters-eligible", "1D76DB", "Open to Bachelor's/Master's students"),
        ("big-tech", "FBCA04", "Posting from a major tech company"),
        ("posted-today", "D93F0B", "Posted within the last 24 hours"),
        ("usa", "5319E7", "Based in the USA"),
        ("canada", "C2E0C6", "Based in Canada"),
        (CHECKLIST_LABEL, "0052CC", "The pinned one-click application checklist"),
    ]:
        gh(
            "label", "create", name,
            "--color", color,
            "--description", description,
            "--force",
        )


def create_issues_for_new_matches(tracked: dict) -> None:
    candidates = [
        r for r in tracked.values()
        if r["status"] == "new" and not r.get("issue_number") and not r.get("backfilled")
    ]
    candidates.sort(key=lambda r: r["found_at"])
    now = datetime.datetime.utcnow()

    for record in candidates[:MAX_ISSUES_PER_RUN]:
        star = "⭐ " if record.get("big_tech") else ""
        fire = "🔥 " if is_posted_today(record, now) else ""
        title = f"[Internship] {fire}{star}{record['company']} — {record['title']}"

        extra_labels = []
        if record.get("big_tech"):
            extra_labels.append("big-tech")
        if is_posted_today(record, now):
            extra_labels.append("posted-today")
        for country in record.get("countries", []):
            extra_labels.append("usa" if country == "USA" else "canada")
        labels = ",".join([LABELS] + extra_labels)

        url = gh(
            "issue", "create",
            "--title", title,
            "--body", issue_body(record),
            "--label", labels,
        )
        # gh issue create prints the created issue's URL as the last line.
        issue_url = url.splitlines()[-1].strip()
        issue_number = int(issue_url.rstrip("/").split("/")[-1])
        tracked[record["id"]]["issue_number"] = issue_number
        tracked[record["id"]]["issue_url"] = issue_url


def close_expired_issues(tracked: dict) -> None:
    for record in tracked.values():
        if (
            record["status"] == "expired"
            and record.get("issue_number")
            and not record.get("expired_issue_closed")
        ):
            gh(
                "issue", "close", str(record["issue_number"]),
                "--comment", "This posting is no longer listed as active upstream — "
                             "auto-closing as expired.",
            )
            record["expired_issue_closed"] = True


def main() -> None:
    tracked = load_tracked()
    ensure_labels()
    create_issues_for_new_matches(tracked)
    close_expired_issues(tracked)
    save_tracked(tracked)
    render_markdown(tracked)
    update_checklist(tracked)


if __name__ == "__main__":
    main()
