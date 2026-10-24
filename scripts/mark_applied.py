"""
Reacts to an issue being closed/reopened on an internship-tracker issue:
closing marks the job "applied", reopening flips an "applied" job back to "new".
Reads context from env vars set by .github/workflows/mark-applied.yml.
"""
import datetime
import os
import re

from lib import load_tracked, save_tracked, render_markdown, update_checklist

JOB_ID_RE = re.compile(r"<!--\s*job_id:\s*(\S+)\s*-->")


def main() -> None:
    action = os.environ["ISSUE_ACTION"]
    body = os.environ.get("ISSUE_BODY") or ""
    closed_at = os.environ.get("ISSUE_CLOSED_AT")

    match = JOB_ID_RE.search(body)
    if not match:
        print("No job_id marker found in issue body; nothing to do.")
        return
    job_id = match.group(1)

    tracked = load_tracked()
    record = tracked.get(job_id)
    if record is None:
        print(f"job_id {job_id} not found in tracker; nothing to do.")
        return

    if action == "closed" and record["status"] != "expired":
        record["status"] = "applied"
        record["applied_at"] = closed_at or datetime.datetime.utcnow().isoformat() + "Z"
    elif action == "reopened" and record["status"] == "applied":
        record["status"] = "new"
        record["applied_at"] = None

    save_tracked(tracked)
    render_markdown(tracked)
    update_checklist(tracked)


if __name__ == "__main__":
    main()
