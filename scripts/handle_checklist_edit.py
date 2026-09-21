"""
Reacts to a checkbox being toggled in the pinned "Application Checklist"
issue: checking a box marks that job applied (and closes its own issue);
unchecking reverts it to new (and reopens that issue). Context comes from
env vars set by .github/workflows/sync-checklist.yml, which diffs the issue
body before/after the edit.
"""
import datetime
import os

from lib import load_tracked, save_tracked, render_markdown, parse_checklist_state, update_checklist, gh


def main() -> None:
    before_body = os.environ.get("BEFORE_BODY")
    after_body = os.environ.get("AFTER_BODY") or ""

    if not before_body:
        print("No prior body to diff against (non-body edit); nothing to do.")
        return

    before_state = parse_checklist_state(before_body)
    after_state = parse_checklist_state(after_body)

    flips = [
        (job_id, checked)
        for job_id, checked in after_state.items()
        if job_id in before_state and before_state[job_id] != checked
    ]
    if not flips:
        print("No checkbox actually flipped (likely our own line add/remove); nothing to do.")
        return

    tracked = load_tracked()
    now = datetime.datetime.utcnow().isoformat() + "Z"

    for job_id, checked in flips:
        record = tracked.get(job_id)
        if record is None:
            continue
        if checked:
            record["status"] = "applied"
            record["applied_at"] = now
            if record.get("issue_number"):
                gh(
                    "issue", "close", str(record["issue_number"]),
                    "--comment", "Marked applied via the checklist.",
                )
        elif record["status"] == "applied":
            record["status"] = "new"
            record["applied_at"] = None
            if record.get("issue_number"):
                gh("issue", "reopen", str(record["issue_number"]))

    save_tracked(tracked)
    render_markdown(tracked)
    update_checklist(tracked)


if __name__ == "__main__":
    main()
