"""Send OTP emails via Gmail SMTP only."""
from __future__ import annotations

import logging
import re
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from config import settings

log = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SMTP_TIMEOUT = 15


def normalize_recipient(email: str) -> str:
    return (email or "").strip().lower()


def is_valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(normalize_recipient(email)))


def _smtp_creds() -> tuple[str, str, str, str]:
    user = (settings.smtp_user or "").strip()
    password = (settings.smtp_password or "").strip().replace(" ", "")
    from_addr = (settings.smtp_from or user).strip()
    host = (settings.smtp_host or "").strip() or ("smtp.gmail.com" if user.lower().endswith("@gmail.com") else "")
    return host, user, password, from_addr


def smtp_is_configured() -> bool:
    host, user, password, from_addr = _smtp_creds()
    return bool(host and user and password and from_addr)


def email_is_configured() -> bool:
    return smtp_is_configured()


def email_provider() -> str:
    return "gmail_smtp" if smtp_is_configured() else "none"


def send_otp_email(
    to_email: str,
    otp_code: str,
    *,
    purpose: str = "verify your email for registration",
) -> tuple[bool, str | None]:
    to_email = normalize_recipient(to_email)
    if not is_valid_email(to_email):
        return False, "Invalid email address."

    host, user, password, from_addr = _smtp_creds()
    if not (host and user and password and from_addr):
        return False, "Email service is not configured. Contact support."

    minutes = settings.otp_expire_minutes
    subject = "Your verification code - AI Medical Assistant"
    plain = (
        "Hello,\n\n"
        f"Your verification code is: {otp_code}\n"
        f"Use it to {purpose}.\n\n"
        f"This code expires in {minutes} minutes.\n\n"
        "If you didn't request this, please ignore this message.\n"
    )
    html = f"""<!DOCTYPE html>
<html><body style="font-family:Segoe UI,Arial,sans-serif;line-height:1.5;color:#222;">
<p>Hello,</p>
<p>Your verification code is: <strong style="font-size:1.2em;letter-spacing:0.08em;">{otp_code}</strong></p>
<p>Use it to {purpose}.</p>
<p style="color:#555;">This code expires in {minutes} minutes.</p>
<p style="color:#555;">If you didn't request this, please ignore this message.</p>
</body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr(("AI Medical Assistant", from_addr))
    msg["To"] = to_email
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    raw = msg.as_string()

    try:
        port = settings.smtp_port or 587
        context = ssl.create_default_context()
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=_SMTP_TIMEOUT, context=context) as server:
                server.login(user, password)
                server.sendmail(from_addr, [to_email], raw)
        else:
            with smtplib.SMTP(host, port, timeout=_SMTP_TIMEOUT) as server:
                server.ehlo()
                if settings.smtp_use_tls:
                    server.starttls(context=context)
                    server.ehlo()
                server.login(user, password)
                server.sendmail(from_addr, [to_email], raw)
        return True, None
    except smtplib.SMTPAuthenticationError:
        return False, "Could not send email due to SMTP authentication failure."
    except Exception:
        log.exception("SMTP send failed")
        return False, "Could not send email. Please try again."


def send_welcome_email(to_email: str, name: str) -> tuple[bool, str | None]:
    to_email = normalize_recipient(to_email)
    if not is_valid_email(to_email):
        return False, "Invalid email address."

    host, user, password, from_addr = _smtp_creds()
    if not (host and user and password and from_addr):
        return False, "Email service is not configured. Contact support."

    subject = "Welcome to AI Medical Assistant"
    plain = (
        f"Hello {name},\n\n"
        "Welcome to AI Medical Assistant! Your account has been successfully created.\n"
    )
    html = f"""<!DOCTYPE html>
<html><body style="font-family:Segoe UI,Arial,sans-serif;line-height:1.5;color:#222;">
<p>Hello {name},</p>
<p>Welcome to <strong>AI Medical Assistant</strong>! Your account has been successfully created.</p>
</body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr(("AI Medical Assistant", from_addr))
    msg["To"] = to_email
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    raw = msg.as_string()

    try:
        port = settings.smtp_port or 587
        context = ssl.create_default_context()
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=_SMTP_TIMEOUT, context=context) as server:
                server.login(user, password)
                server.sendmail(from_addr, [to_email], raw)
        else:
            with smtplib.SMTP(host, port, timeout=_SMTP_TIMEOUT) as server:
                server.ehlo()
                if settings.smtp_use_tls:
                    server.starttls(context=context)
                    server.ehlo()
                server.login(user, password)
                server.sendmail(from_addr, [to_email], raw)
        return True, None
    except smtplib.SMTPAuthenticationError:
        return False, "Could not send email due to SMTP authentication failure."
    except Exception:
        log.exception("SMTP send failed")
        return False, "Could not send email. Please try again."

