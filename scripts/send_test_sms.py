"""
Sends one example digest through the exact same build_digest()/send_email()
code path the real bot uses, so you can confirm delivery still works
without waiting for an actual new posting. Triggered manually via the
"Test SMS" workflow (workflow_dispatch only, never on a schedule).
"""
import datetime
import os

from send_sms_digest import build_digest, send_email

FAKE_MATCH = {
    "title": "SWE Intern",
    "company": "Microsoft",
    "countries": ["USA"],
    "date_posted": None,  # filled in with "now" below
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
    FAKE_MATCH["date_posted"] = now.isoformat() + "Z"

    subject, body = build_digest([FAKE_MATCH], now)
    send_email(gmail_address, gmail_app_password, phone_gateway, subject, body)

    print(f"Sent example digest to {phone_gateway}:\n{body}\n\n"
          f"This is exactly what the real bot sends. If nothing arrives in "
          f"a few minutes, something's changed (secret typo, gateway "
          f"disabled, etc.) -- check this run's log for errors.")


if __name__ == "__main__":
    main()
