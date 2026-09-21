"""
Sends a single SMS-via-email digest (through a carrier's email-to-SMS
gateway, e.g. number@msg.koodomobile.com) for this run's newly discovered
matches. One line per job:
"USA: SWE Intern @ Microsoft - posted now - https://is.gd/abc123".

Plain text messages can't hide a URL behind clickable anchor text the way a
webpage or HTML email can -- there's no such thing as a "linked word" in
SMS -- so the closest equivalent is a shortened link that still taps to
open. Shortening is best-effort: if the is.gd API is unreachable or errors,
the full original URL is used instead rather than dropping the link or
failing the whole send.

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

import requests

from lib import relative_time

NEW_MATCHES_PATH = os.path.join(os.path.dirname(__file__), "..", "new_matches.json")
MAX_LINES = 8


def shorten_url(url: str) -> str:
    try:
        resp = requests.get(
            "https://is.gd/create.php",
            params={"format": "simple", "url": url},
            timeout=10,
        )
        short = resp.text.strip()
        if resp.ok and short.startswith("http"):
            return short
    except requests.RequestException:
        pass
    return url


def format_line(record: dict, now: datetime.datetime) -> str:
    country = "/".join(record.get("countries", [])) or "?"
    posted = relative_time(record.get("date_posted"), now)
    link = shorten_url(record["url"]) if record.get("url") else None
    line = f"{country}: {record['title']} @ {record['company']} - posted {posted}"
    return f"{line} - {link}" if link else line


def build_digest(matches: list, now: datetime.datetime) -> tuple:
    """Returns (subject, body) in the exact format the real digest uses --
    shared with send_test_sms.py so a preview can't drift out of sync with
    what actually gets sent."""
    lines = [format_line(r, now) for r in matches[:MAX_LINES]]
    if len(matches) > MAX_LINES:
        lines.append(f"+{len(matches) - MAX_LINES} more, check GitHub")
    return f"{len(matches)} new internship(s)", "\n".join(lines)


def send_email(gmail_address: str, gmail_app_password: str, to_address: str, subject: str, body: str) -> None:
    msg = MIMEText(body)
    msg["Subject"] = subject
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

    subject, body = build_digest(new_matches, datetime.datetime.utcnow())
    send_email(gmail_address, gmail_app_password, phone_gateway, subject, body)
    print(f"Sent SMS digest for {len(new_matches)} new match(es) to {phone_gateway}.")


if __name__ == "__main__":
    main()
