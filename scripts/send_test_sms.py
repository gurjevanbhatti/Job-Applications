"""
Sends one example digest through the exact same build_digest()/send_email()
code path the real bot uses (prefixed "TEST: " so it's obvious in your
messages which ones were tests), so you can confirm delivery still works
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

    example_body = build_digest([FAKE_MATCH], now)
    test_body = f"TEST: {example_body}"
    send_email(gmail_address, gmail_app_password, phone_gateway, test_body)

    print(f"Sent test digest to {phone_gateway}:\n{test_body}\n\n"
          f"Real notifications look identical minus the 'TEST: ' prefix. If "
          f"nothing arrives in a few minutes, something's changed (secret "
          f"typo, gateway disabled, etc.) -- check this run's log for errors.")


if __name__ == "__main__":
    main()
