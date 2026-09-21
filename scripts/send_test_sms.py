"""
Sends TWO separate test texts -- one without a link, one with -- so a
delivery difference between them can actually be diagnosed instead of
guessed at. Carriers are known to filter/drop texts containing URLs more
aggressively than plain text, especially from a personal (non-10DLC-
registered) sender like a Gmail SMTP relay, so this isolates whether that's
what's happening here. Triggered manually via the "Test SMS" workflow
(workflow_dispatch only, never on a schedule).
"""
import datetime
import os

from send_sms_digest import format_line, send_email

NO_LINK_MATCH = {
    "title": "SWE Intern",
    "company": "Microsoft",
    "countries": ["USA"],
    "date_posted": None,  # filled in below
}
WITH_LINK_MATCH = {
    "title": "SWE Intern",
    "company": "Microsoft",
    "countries": ["USA"],
    "url": "https://apply.careers.microsoft.com/careers/job/1970393557002608",
    "date_posted": None,  # filled in below
}


def main() -> None:
    gmail_address = os.environ.get("GMAIL_ADDRESS")
    gmail_app_password = os.environ.get("GMAIL_APP_PASSWORD")
    phone_gateway = os.environ.get("PHONE_SMS_GATEWAY")

    missing = [
        name for name, value in [
            ("GMAIL_ADDRESS", gmail_address),
            ("GMAIL_APP_PASSWORD", gmail_app_password),
            ("PHONE_SMS_GATEWAY", phone_gateway),
        ] if not value
    ]
    if missing:
        raise SystemExit(
            f"Missing secret(s): {', '.join(missing)}. Add them under "
            "Settings -> Secrets and variables -> Actions, then re-run."
        )

    now = datetime.datetime.utcnow()
    NO_LINK_MATCH["date_posted"] = now.isoformat() + "Z"
    WITH_LINK_MATCH["date_posted"] = now.isoformat() + "Z"

    body_a = f"TEST A (no link): {format_line(NO_LINK_MATCH, now)}"
    body_b = f"TEST B (with link): {format_line(WITH_LINK_MATCH, now)}"

    send_email(gmail_address, gmail_app_password, phone_gateway, "Internship bot test A", body_a)
    send_email(gmail_address, gmail_app_password, phone_gateway, "Internship bot test B", body_b)

    print(f"Sent two test messages to {phone_gateway}:\n"
          f"  A (no link): {body_a}\n"
          f"  B (with link): {body_b}\n\n"
          f"Check your phone in a few minutes. If A arrives but B doesn't, "
          f"your carrier is filtering texts containing links -- tell Claude "
          f"and the link will be dropped from the real digest. If neither "
          f"arrives, it's a gateway/carrier issue unrelated to links.")


if __name__ == "__main__":
    main()
