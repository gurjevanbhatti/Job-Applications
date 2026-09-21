"""
Sends one fixed test text through the same Gmail-SMTP -> carrier-gateway
path as send_sms_digest.py, so you can confirm the integration works
without waiting for a real new internship posting. Triggered manually via
the "Test SMS" workflow (workflow_dispatch only, never on a schedule).
"""
import os
import smtplib
from email.mime.text import MIMEText


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

    body = "Test message from your internship bot. If you got this, SMS notifications are working."
    msg = MIMEText(body)
    msg["Subject"] = "Internship bot test"
    msg["From"] = gmail_address
    msg["To"] = phone_gateway

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, gmail_app_password)
        server.sendmail(gmail_address, [phone_gateway], msg.as_string())

    print(f"Sent test message to {phone_gateway}. Check your phone -- if nothing "
          f"arrives in a few minutes, the gateway address is likely wrong or "
          f"your carrier has disabled email-to-SMS.")


if __name__ == "__main__":
    main()
