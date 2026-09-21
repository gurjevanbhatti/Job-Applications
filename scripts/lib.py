"""Shared helpers for reading/writing the internship tracker state."""
import datetime
import html
import json
import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "tracked_jobs.json")
MD_PATH = os.path.join(os.path.dirname(__file__), "..", "APPLICATIONS.md")

STATUS_ORDER = {"new": 0, "applied": 1, "expired": 2}
STATUS_LABEL = {"new": "🆕 New", "applied": "✅ Applied", "expired": "⌛ Expired"}

# Exact (case-insensitive) company_name matches from the SimplifyJobs feed.
# Kept as exact matches rather than substring matches on purpose -- a
# substring check on short names like "Intel", "Snap", or "Meta" produces
# false positives (e.g. "Intelliguard", "Snap-on", "Commercial Metals").
BIG_TECH_COMPANIES = {
    "google", "meta", "amazon", "apple", "microsoft", "netflix", "nvidia",
    "tesla", "uber", "uber freight", "airbnb", "salesforce", "oracle", "ibm",
    "adobe", "intel", "qualcomm", "bytedance", "tiktok", "snap", "pinterest",
    "spotify", "stripe", "palantir", "spacex", "openai", "anthropic",
    "databricks", "cisco", "dropbox", "atlassian", "shopify", "paypal",
    "doordash", "instacart", "roblox", "zoom", "servicenow", "dell technologies",
    "amd", "samsung", "samsung research america", "sony",
    "sony interactive entertainment", "linkedin", "twitter", "block", "ebay",
    "reddit", "vmware", "broadcom", "lyft", "twilio", "snowflake", "mongodb",
    "workday", "intuit", "hewlett packard enterprise",
}


def is_big_tech(company: str) -> bool:
    return company.strip().lower() in BIG_TECH_COMPANIES


def _parse_posted(date_posted: str):
    if not date_posted:
        return None
    try:
        return datetime.datetime.fromisoformat(date_posted.rstrip("Z"))
    except ValueError:
        return None


def is_posted_today(record: dict, now: datetime.datetime) -> bool:
    """Computed fresh at render/issue-creation time (not stored) since this
    changes as time passes, unlike a static attribute such as big_tech.
    "Today" here means within the last 24 real hours, not same calendar day,
    so it lines up with the hours/days relative_time() actually shows."""
    posted_at = _parse_posted(record.get("date_posted"))
    if posted_at is None:
        return False
    return (now - posted_at) < datetime.timedelta(days=1)


def relative_time(date_posted: str, now: datetime.datetime) -> str:
    """'3 hrs ago' / '2 days ago' style label. Falls back to '—' if unknown."""
    posted_at = _parse_posted(date_posted)
    if posted_at is None:
        return "—"
    seconds = max((now - posted_at).total_seconds(), 0)
    if seconds < 3600:
        minutes = max(1, int(seconds // 60))
        return f"{minutes} min ago"
    if seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours} hr{'s' if hours != 1 else ''} ago"
    days = int(seconds // 86400)
    return f"{days} day{'s' if days != 1 else ''} ago"


def load_tracked() -> dict:
    if not os.path.exists(DATA_PATH):
        return {}
    with open(DATA_PATH, "r") as f:
        return json.load(f)


def save_tracked(tracked: dict) -> None:
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w") as f:
        json.dump(tracked, f, indent=2, sort_keys=True)
        f.write("\n")


def _esc(text: str) -> str:
    return html.escape(str(text), quote=False)


def _sort_records(records: list, now: datetime.datetime) -> list:
    # Stable two-pass sort: newest first, then bubble up new-status, posted-
    # today, and big-tech rows within that.
    records = sorted(records, key=lambda r: r.get("date_posted") or "", reverse=True)
    records.sort(
        key=lambda r: (
            STATUS_ORDER.get(r["status"], 9),
            0 if is_posted_today(r, now) else 1,
            0 if r.get("big_tech") else 1,
        )
    )
    return records


def _country_table_html(records: list, now: datetime.datetime) -> str:
    if not records:
        return "<i>No matches yet.</i>"

    rows = ["<table>", "<tr><th>Company</th><th>Role</th><th>Posted</th><th>Status</th></tr>"]
    for r in _sort_records(records, now):
        company = _esc(r["company"])
        if r.get("big_tech"):
            company = f"⭐ <b>{company}</b>"

        role = f'<a href="{_esc(r["url"])}">{_esc(r["title"])}</a>'

        posted = relative_time(r.get("date_posted"), now)
        if is_posted_today(r, now):
            posted = f"🔥 {posted}"

        status = STATUS_LABEL.get(r["status"], r["status"])
        if r["status"] == "applied" and r.get("applied_at"):
            status += f" ({r['applied_at'][:10]})"
        if r.get("issue_number"):
            status += f' · <a href="{_esc(r["issue_url"])}">#{r["issue_number"]}</a>'

        rows.append(f"<tr><td>{company}</td><td>{role}</td><td>{posted}</td><td>{status}</td></tr>")
    rows.append("</table>")
    return "\n".join(rows)


def _section_header(title: str, records: list, now: datetime.datetime) -> str:
    new_count = sum(1 for r in records if r["status"] == "new")
    applied_count = sum(1 for r in records if r["status"] == "applied")
    expired_count = sum(1 for r in records if r["status"] == "expired")
    big_tech_count = sum(1 for r in records if r.get("big_tech"))
    today_count = sum(1 for r in records if is_posted_today(r, now))
    return (
        f"<h2>{title}</h2>"
        f"<b>{new_count} new</b> · <b>{applied_count} applied</b> · "
        f"<b>{expired_count} expired</b> · {len(records)} total · "
        f"⭐ <b>{big_tech_count} big tech</b> · 🔥 <b>{today_count} posted today</b>"
    )


def render_markdown(tracked: dict) -> None:
    now = datetime.datetime.utcnow()
    records = list(tracked.values())
    usa_records = [r for r in records if "USA" in (r.get("countries") or [])]
    canada_records = [r for r in records if "Canada" in (r.get("countries") or [])]

    lines = [
        "# Master's Internship Application Tracker",
        "",
        "Auto-generated by `scripts/fetch_internships.py`. Do not hand-edit — edit "
        "`data/tracked_jobs.json` instead, or close/reopen the linked GitHub issue "
        "to change a job's status. Postings open to both countries appear on both "
        "sides. 🔥 = posted in the last 24h, ⭐ = big tech.",
        "",
        "<table>",
        "<tr><td width=\"50%\" valign=\"top\">",
        "",
        _section_header("🇺🇸 USA", usa_records, now),
        "",
        _country_table_html(usa_records, now),
        "",
        "</td><td width=\"50%\" valign=\"top\">",
        "",
        _section_header("🇨🇦 Canada", canada_records, now),
        "",
        _country_table_html(canada_records, now),
        "",
        "</td></tr>",
        "</table>",
    ]

    with open(MD_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")
