"""
Files a GitHub issue for each tracked job that doesn't have one yet (skipping
one-time backfilled history), and auto-closes issues for postings that just
expired. Requires `gh` (preinstalled on GitHub-hosted runners) authenticated
via GH_TOKEN.

Issue creation is capped per run (MAX_ISSUES_PER_RUN) to stay well under
GitHub's abuse-detection rate limits even if a burst of new postings shows
up in one day; any overflow just waits for the next run.
"""
import subprocess

from lib import load_tracked, save_tracked, render_markdown

LABELS = "internship-tracker,masters-eligible"
MAX_ISSUES_PER_RUN = 25


def gh(*args: str) -> str:
    result = subprocess.run(
        ["gh", *args], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def issue_body(record: dict) -> str:
    return (
        f"<!-- job_id: {record['id']} -->\n"
        f"**Company:** {record['company']}\n"
        f"**Role:** {record['title']}\n"
        f"**Term(s):** {', '.join(record.get('terms', []))}\n"
        f"**Location(s):** {', '.join(record.get('locations', [])) or 'Unspecified'}\n"
        f"**Degrees eligible:** {', '.join(record.get('degrees', []))}\n"
        f"**Apply:** {record['url']}\n\n"
        "---\n"
        "Close this issue once you've applied — it will automatically mark this "
        "internship **Applied** in `APPLICATIONS.md` and `data/tracked_jobs.json`. "
        "Reopening it flips it back to **New**."
    )


def create_issues_for_new_matches(tracked: dict) -> None:
    candidates = [
        r for r in tracked.values()
        if r["status"] == "new" and not r.get("issue_number") and not r.get("backfilled")
    ]
    candidates.sort(key=lambda r: r["found_at"])

    for record in candidates[:MAX_ISSUES_PER_RUN]:
        title = f"[Internship] {record['company']} — {record['title']}"
        url = gh(
            "issue", "create",
            "--title", title,
            "--body", issue_body(record),
            "--label", LABELS,
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
    create_issues_for_new_matches(tracked)
    close_expired_issues(tracked)
    save_tracked(tracked)
    render_markdown(tracked)


if __name__ == "__main__":
    main()
