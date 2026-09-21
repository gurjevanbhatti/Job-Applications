"""Shared helpers for reading/writing the internship tracker state."""
import datetime
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


def is_posted_today(record: dict, today: datetime.date) -> bool:
    """Computed fresh at render time (not stored) since "today" changes day
    to day, unlike a static attribute such as big_tech."""
    date_posted = record.get("date_posted")
    if not date_posted:
        return False
    try:
        posted_date = datetime.datetime.fromisoformat(date_posted.rstrip("Z")).date()
    except ValueError:
        return False
    return posted_date == today


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


def _sort_records(records: list, today: datetime.date) -> list:
    # Stable two-pass sort: newest first, then bubble up new-status, posted-
    # today, and big-tech rows within that.
    records = sorted(records, key=lambda r: r.get("date_posted") or "", reverse=True)
    records.sort(
        key=lambda r: (
            STATUS_ORDER.get(r["status"], 9),
            0 if is_posted_today(r, today) else 1,
            0 if r.get("big_tech") else 1,
        )
    )
    return records


def _table_rows(records: list, today: datetime.date) -> list:
    lines = [
        "| Status | Company | Role | Term | Location | Degrees | Posted | Applied | Issue |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in records:
        issue = f"[#{r['issue_number']}]({r['issue_url']})" if r.get("issue_number") else "—"
        company = r["company"].replace("|", "/")
        if r.get("big_tech"):
            company = f"⭐ **{company}**"
        posted = (r.get("date_posted") or "")[:10] or "—"
        if is_posted_today(r, today):
            posted = f"🔥 {posted}"
        lines.append(
            "| {status} | {company} | {title} | {term} | {loc} | {deg} | {posted} | {applied} | {issue} |".format(
                status=STATUS_LABEL.get(r["status"], r["status"]),
                company=company,
                title=f"[{r['title'].replace('|', '/')}]({r['url']})",
                term=", ".join(r.get("terms", [])),
                loc=", ".join(r.get("locations", [])) or "—",
                deg=", ".join(r.get("degrees", [])),
                posted=posted,
                applied=(r.get("applied_at") or "—")[:10],
                issue=issue,
            )
        )
    return lines


def _section(title: str, records: list, today: datetime.date) -> list:
    new_count = sum(1 for r in records if r["status"] == "new")
    applied_count = sum(1 for r in records if r["status"] == "applied")
    expired_count = sum(1 for r in records if r["status"] == "expired")
    big_tech_count = sum(1 for r in records if r.get("big_tech"))
    today_count = sum(1 for r in records if is_posted_today(r, today))

    lines = [
        f"## {title}",
        "",
        f"**{new_count} new** · **{applied_count} applied** · **{expired_count} expired** "
        f"· {len(records)} total · ⭐ **{big_tech_count} big tech** · 🔥 **{today_count} posted today**",
        "",
    ]
    if records:
        lines += _table_rows(_sort_records(records, today), today)
    else:
        lines.append("_No matches yet._")
    lines.append("")
    return lines


def render_markdown(tracked: dict) -> None:
    today = datetime.datetime.utcnow().date()
    records = list(tracked.values())
    usa_records = [r for r in records if "USA" in (r.get("countries") or [])]
    canada_records = [r for r in records if "Canada" in (r.get("countries") or [])]

    lines = [
        "# Master's Internship Application Tracker",
        "",
        "Auto-generated by `scripts/fetch_internships.py`. Do not hand-edit — edit "
        "`data/tracked_jobs.json` instead, or close/reopen the linked GitHub issue "
        "to change a job's status. Postings open to both countries appear in both "
        "sections below. 🔥 = posted today, ⭐ = big tech.",
        "",
    ]
    lines += _section("🇺🇸 USA", usa_records, today)
    lines += _section("🇨🇦 Canada", canada_records, today)

    with open(MD_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")
