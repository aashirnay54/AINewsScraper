"""SMTP email delivery."""
from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"


def send_email(
    html_content: str,
    plain_content: str,
    subject: str | None = None,
) -> bool:
    """
    Send the briefing email via SMTP.

    If SMTP credentials are not set, writes to data/last.html instead.

    Args:
        html_content: HTML email body
        plain_content: Plain text email body
        subject: Optional email subject (defaults to "AI Markets Briefing")

    Returns:
        True if email was sent or saved successfully
    """
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    recipient = os.environ.get("RECIPIENT_EMAIL")
    from_email = os.environ.get("FROM_EMAIL", smtp_user)

    if not subject:
        from datetime import datetime
        today = datetime.now().strftime("%B %d, %Y")
        subject = f"AI Markets Briefing - {today}"

    # If no SMTP creds, save to file for local dev
    if not smtp_user or not smtp_pass:
        logger.info("SMTP credentials not set, writing to data/last.html")
        return _save_to_file(html_content)

    if not recipient:
        logger.error("RECIPIENT_EMAIL not set")
        return False

    if not from_email:
        from_email = smtp_user

    # Build email message with both HTML and plain text
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = recipient

    # Set plain text as primary, HTML as alternative
    msg.set_content(plain_content)
    msg.add_alternative(html_content, subtype="html")

    # Send via Gmail SMTP_SSL on port 465
    try:
        smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.environ.get("SMTP_PORT", "465"))

        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        logger.info(f"Email sent successfully to {recipient}")
        return True

    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP authentication failed: {e}")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


def _save_to_file(html_content: str) -> bool:
    """Save HTML content to data/last.html for local development."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        output_path = DATA_DIR / "last.html"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info(f"Saved email to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save email to file: {e}")
        return False
