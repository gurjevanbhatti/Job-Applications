"""
Sends a single SMS-via-email digest (through a carrier's email-to-SMS
gateway, e.g. number@msg.koodomobile.com) for this run's newly discovered
matches. One line per job: "USA: SWE Intern @ Microsoft - posted now". No
email Subject header is set (see build_digest()'s docstring for why).

No link is included: an A/B test confirmed the carrier silently drops texts
containing a URL (common anti-phishing filtering for SMS from a non-10DLC-
registered sender like a personal Gmail relay) while the identical message
without a link delivered fine. A dropped text is worse than one missing a
link, so this trades the link for reliable delivery -- the full details and
apply link are still on the job's GitHub issue and the pinned checklist.

Reads new_matches.json, written fresh by fetch_internships.py each run.
No-ops quietly if there's nothing new or the required secrets aren't set,
so this is safe to run even before notification setup is finished.

Email-to-SMS gateways aren't a guaranteed delivery channel -- carriers can
silently drop these with no bounce -- so this is best-effort, not a
replacement for checking GitHub directly.
"""
import datetime
import json
import os
import smtplib
from email.mime.text import MIMEText

from lib import relative_time

NEW_MATCHES_PATH = os.path.join(os.path.dirname(__file__), "..", "new_matches.json")
MAX_LINES = 8


def format_line(record: dict, now: datetime.datetime) -> str:
    country = "/".join(record.get("countries", [])) or "?"
    posted = relative_time(record.get("date_posted"), now)
    return f"{country}: {record['title']} @ {record['company']} - posted {posted}"


def build_digest(matches: list, now: datetime.datetime) -> str:
    """Returns the exact body the real digest uses -- shared with
    send_test_sms.py so a preview can't drift out of sync with what
    actually gets sent. No Subject/count header line: on this carrier the
    email Subject rendered as an extra bold line on the phone (looked like
    stray blank space above the actual content), so for >1 match the count
    is folded into the body's own first line instead."""
    lines = [format_line(r, now) for r in matches[:MAX_LINES]]
    if len(matches) > MAX_LINES:
        lines.append(f"+{len(matches) - MAX_LINES} more, check GitHub")
    body = "\n".join(lines)
    if len(matches) > 1:
        body = f"{len(matches)} new internships:\n{body}"
    return body


def send_email(gmail_address: str, gmail_app_password: str, to_address: str, body: str) -> None:
    # No Subject header on purpose -- see build_digest()'s docstring.
    msg = MIMEText(body)
    msg["From"] = gmail_address
    msg["To"] = to_address

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, gmail_app_password)
        server.sendmail(gmail_address, [to_address], msg.as_string())


def main() -> None:
    gmail_address = os.environ.get("GMAIL_ADDRESS")
    gmail_app_password = os.environ.get("GMAIL_APP_PASSWORD")
    phone_gateway = os.environ.get("PHONE_SMS_GATEWAY")
    if not (gmail_address and gmail_app_password and phone_gateway):
        print("SMS secrets not configured (GMAIL_ADDRESS/GMAIL_APP_PASSWORD/"
              "PHONE_SMS_GATEWAY); skipping notification.")
        return

    if not os.path.exists(NEW_MATCHES_PATH):
        print("No new_matches.json this run; skipping.")
        return
    with open(NEW_MATCHES_PATH) as f:
        new_matches = json.load(f)
    if not new_matches:
        print("No new matches this run; skipping notification.")
        return

    body = build_digest(new_matches, datetime.datetime.utcnow())
    send_email(gmail_address, gmail_app_password, phone_gateway, body)
    print(f"Sent SMS digest for {len(new_matches)} new match(es) to {phone_gateway}.")


if __name__ == "__main__":
    main()
