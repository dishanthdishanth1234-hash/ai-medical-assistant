"""Send OTP and notification emails to any address via Gmail SMTP."""
from __future__ import annotations

import logging
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from config import settings

log = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_recipient(email: str) -> str:
    return (email or "").strip().lower()


def is_valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(normalize_recipient(email)))


def smtp_is_configured() -> bool:
    user = (settings.smtp_user or "").strip()
    password = (settings.smtp_password or "").strip().replace(" ", "")
    from_addr = (settings.smtp_from or user or "").strip()
    host = _smtp_host()
    return bool(host and from_addr and user and password)


def _smtp_host() -> str:
    host = (settings.smtp_host or "").strip()
    user = (settings.smtp_user or "").strip()
    if not host and user.lower().endswith("@gmail.com"):
        return "smtp.gmail.com"
    return host


def _smtp_port() -> int:
    port = settings.smtp_port
    if not (settings.smtp_host or "").strip() and (settings.smtp_user or "").strip().lower().endswith("@gmail.com"):
        return port or 587
    return port or 587


def _send_message(to_email: str, subject: str, plain: str, html: str | None = None) -> bool:
    """Deliver email to `to_email` (any provider: Gmail, Outlook, Yahoo, etc.)."""
    to_email = normalize_recipient(to_email)
    if not is_valid_email(to_email):
        log.warning("Invalid recipient email: %s", to_email)
        return False
    if not smtp_is_configured():
        log.warning(
            "SMTP not configured — cannot email %s. Set SMTP_USER, SMTP_PASSWORD, SMTP_FROM on Render.",
            to_email,
        )
        return False

    host = _smtp_host()
    port = _smtp_port()
    user = (settings.smtp_user or "").strip()
    password = (settings.smtp_password or "").strip().replace(" ", "")
    from_addr = (settings.smtp_from or user).strip()

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = formataddr(("AI Medical Assistant", from_addr))
        msg["To"] = to_email
        msg["Reply-To"] = from_addr
        msg.attach(MIMEText(plain, "plain", "utf-8"))
        if html:
            msg.attach(MIMEText(html, "html", "utf-8"))

        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=30) as server:
                server.login(user, password)
                server.sendmail(from_addr, [to_email], msg.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=30) as server:
                server.ehlo()
                if settings.smtp_use_tls:
                    server.starttls()
                    server.ehlo()
                server.login(user, password)
                server.sendmail(from_addr, [to_email], msg.as_string())
        log.info("Email sent to %s | subject: %s", to_email, subject)
        return True
    except Exception:
        log.exception("Failed to send email to %s", to_email)
        return False


def send_otp_email(
    to_email: str,
    otp_code: str,
    *,
    purpose: str = "verify your email for registration",
) -> bool:
    """Send Telegram-style OTP to the address the user entered at sign-up."""
    minutes = settings.otp_expire_minutes
    subject = f"Your Code - {otp_code}"
    plain = (
        "Hello,\n\n"
        f"Your code is: {otp_code}. Use it to {purpose}.\n\n"
        f"This code expires in {minutes} minutes.\n\n"
        "If you didn't request this, simply ignore this message.\n\n"
        "Yours,\n"
        "The AI Medical Assistant Team"
    )
    html = f"""<!DOCTYPE html>
<html><body style="font-family:Segoe UI,Arial,sans-serif;line-height:1.5;color:#222;">
<p>Hello,</p>
<p>Your code is: <strong style="font-size:1.25em;letter-spacing:0.08em;">{otp_code}</strong>.
Use it to {purpose}.</p>
<p style="color:#555;">This code expires in {minutes} minutes.</p>
<p style="color:#555;">If you didn't request this, simply ignore this message.</p>
<p>Yours,<br>The AI Medical Assistant Team</p>
</body></html>"""
    return _send_message(to_email, subject, plain, html)


def send_welcome_email(to_email: str, name: str) -> bool:
    """Sent after successful registration."""
    display = (name or "there").strip() or "there"
    subject = "Welcome to AI Medical Assistant"
    plain = (
        f"Hello {display},\n\n"
        "Your account is ready. You can sign in anytime with the email and password you chose.\n\n"
        "Yours,\n"
        "The AI Medical Assistant Team"
    )
    html = f"""<!DOCTYPE html>
<html><body style="font-family:Segoe UI,Arial,sans-serif;line-height:1.5;color:#222;">
<p>Hello {display},</p>
<p>Your account is ready. Sign in anytime with the email and password you chose.</p>
<p>Yours,<br>The AI Medical Assistant Team</p>
</body></html>"""
    return _send_message(to_email, subject, plain, html)
