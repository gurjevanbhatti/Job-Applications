"""
Sends a single SMS-via-email digest (through a carrier's email-to-SMS
gateway, e.g. number@msg.telus.com) for this run's newly discovered matches.
One line per job: "USA: SWE Intern @ Microsoft - posted now".

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

    now = datetime.datetime.utcnow()
    lines = [format_line(r, now) for r in new_matches[:MAX_LINES]]
    if len(new_matches) > MAX_LINES:
        lines.append(f"+{len(new_matches) - MAX_LINES} more, check GitHub")
    body = "\n".join(lines)

    msg = MIMEText(body)
    msg["Subject"] = f"{len(new_matches)} new internship(s)"
    msg["From"] = gmail_address
    msg["To"] = phone_gateway

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, gmail_app_password)
        server.sendmail(gmail_address, [phone_gateway], msg.as_string())

    print(f"Sent SMS digest for {len(new_matches)} new match(es) to {phone_gateway}.")


if __name__ == "__main__":
    main()
