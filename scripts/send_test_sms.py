"""
Sends a fake but realistic example digest -- built through the exact same
build_digest()/send_email() code the real bot uses -- so you can preview
what an actual notification looks like without waiting for a real new
posting. Triggered manually via the "Test SMS" workflow (workflow_dispatch
only, never on a schedule).
"""
import datetime
import os

from send_sms_digest import build_digest, send_email

FAKE_MATCHES = [
    {
        "title": "SWE Intern",
        "company": "Microsoft",
        "countries": ["USA"],
        "url": "https://apply.careers.microsoft.com/careers/job/1970393557002608",
        "date_posted": None,  # filled in with "now" below
    },
    {
        "title": "Data Scientist Intern",
        "company": "Shopify",
        "countries": ["Canada"],
        "url": "https://www.shopify.com/careers/data-scientist-intern",
        "date_posted": None,  # filled in with "2 hours ago" below
    },
]


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
    FAKE_MATCHES[0]["date_posted"] = now.isoformat() + "Z"
    FAKE_MATCHES[1]["date_posted"] = (now - datetime.timedelta(hours=2)).isoformat() + "Z"

    subject, body = build_digest(FAKE_MATCHES, now)
    send_email(gmail_address, gmail_app_password, phone_gateway, subject, f"[EXAMPLE] {body}")

    print(f"Sent example digest to {phone_gateway}:\n{body}\n\n"
          f"This is exactly the format/layout the real bot will send -- if "
          f"you want it to look different, tell me what to change. If "
          f"nothing arrives in a few minutes, the gateway address is likely "
          f"wrong or your carrier has disabled email-to-SMS.")


if __name__ == "__main__":
    main()
