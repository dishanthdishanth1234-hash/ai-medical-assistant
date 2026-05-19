"""Send OTP emails via Resend API (fast) or Gmail SMTP."""
from __future__ import annotations

import logging
import os
import re
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from config import settings

log = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SMTP_TIMEOUT = 12  # seconds — avoid long waits when Gmail fails


def _clean(value: str) -> str:
    return (value or "").strip().strip('"').strip("'")


def _env_bool(name: str, default: bool = True) -> bool:
    raw = _clean(os.environ.get(name, ""))
    if not raw:
        return bool(getattr(settings, name.lower(), default))
    return raw.lower() in ("1", "true", "yes", "on")


def normalize_recipient(email: str) -> str:
    return (email or "").strip().lower()


def is_valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(normalize_recipient(email)))


def _resend_api_key() -> str:
    return _clean(os.environ.get("RESEND_API_KEY", "") or getattr(settings, "resend_api_key", "") or "")


def _resend_from() -> str:
    custom = _clean(os.environ.get("RESEND_FROM", "") or getattr(settings, "resend_from", "") or "")
    return custom or "onboarding@resend.dev"


def _smtp_creds() -> tuple[str, str, str, str]:
    user = _clean(os.environ.get("SMTP_USER", "") or settings.smtp_user)
    password = _clean(os.environ.get("SMTP_PASSWORD", "") or settings.smtp_password).replace(" ", "")
    from_addr = _clean(os.environ.get("SMTP_FROM", "") or settings.smtp_from or user)
    host = _clean(os.environ.get("SMTP_HOST", "") or settings.smtp_host)
    if not host and user.lower().endswith("@gmail.com"):
        host = "smtp.gmail.com"
    return host, user, password, from_addr


def smtp_is_configured() -> bool:
    host, user, password, from_addr = _smtp_creds()
    return bool(host and user and password and from_addr)


def resend_is_configured() -> bool:
    return bool(_resend_api_key())


def email_is_configured() -> bool:
    return resend_is_configured() or smtp_is_configured()


def email_provider() -> str:
    if resend_is_configured():
        return "resend"
    if smtp_is_configured():
        return "gmail_smtp"
    return "none"


def build_otp_email(otp_code: str, *, purpose: str) -> tuple[str, str, str]:
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
    return subject, plain, html


def _send_via_resend(to_email: str, subject: str, plain: str, html: str) -> tuple[bool, str | None]:
    api_key = _resend_api_key()
    if not api_key:
        return False, None
    try:
        import resend

        resend.api_key = api_key
        resend.Emails.send(
            {
                "from": _resend_from(),
                "to": to_email,
                "subject": subject,
                "html": html,
                "text": plain,
            }
        )
        log.info("Resend email sent to %s", to_email)
        return True, None
    except Exception as exc:
        log.exception("Resend failed for %s", to_email)
        return False, f"Resend could not send email: {exc}"


def _send_via_gmail_smtp(to_email: str, subject: str, plain: str, html: str) -> tuple[bool, str | None]:
    host, user, password, from_addr = _smtp_creds()
    if not (host and user and password and from_addr):
        return False, "Gmail SMTP is not configured."

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr(("AI Medical Assistant", from_addr))
    msg["To"] = to_email
    msg["Reply-To"] = from_addr
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    raw = msg.as_string()

    port = int(_clean(os.environ.get("SMTP_PORT", "")) or settings.smtp_port or 587)
    use_tls = _env_bool("SMTP_USE_TLS", True)
    ctx = ssl.create_default_context()

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=_SMTP_TIMEOUT, context=ctx) as server:
                server.login(user, password)
                server.sendmail(from_addr, [to_email], raw)
        else:
            with smtplib.SMTP(host, port, timeout=_SMTP_TIMEOUT) as server:
                server.ehlo()
                if use_tls:
                    server.starttls(context=ctx)
                    server.ehlo()
                server.login(user, password)
                server.sendmail(from_addr, [to_email], raw)
        log.info("Gmail SMTP sent to %s", to_email)
        return True, None
    except Exception as exc:
        log.exception("Gmail SMTP failed for %s", to_email)
        return False, f"Email could not be sent: {exc}"


def _send_message(to_email: str, subject: str, plain: str, html: str | None = None) -> tuple[bool, str | None]:
    """Send to any inbox. Uses Resend only when configured (no slow Gmail fallback)."""
    to_email = normalize_recipient(to_email)
    if not is_valid_email(to_email):
        return False, "Invalid email address."
    if not email_is_configured():
        return False, "Email is not configured on the server."

    html_body = html or f"<pre>{plain}</pre>"

    if resend_is_configured():
        return _send_via_resend(to_email, subject, plain, html_body)

    return _send_via_gmail_smtp(to_email, subject, plain, html_body)


def send_otp_email(
    to_email: str,
    otp_code: str,
    *,
    purpose: str = "verify your email for registration",
) -> tuple[bool, str | None]:
    subject, plain, html = build_otp_email(otp_code, purpose=purpose)
    return _send_message(to_email, subject, plain, html)


def deliver_otp_email_background(to_email: str, otp_code: str, *, purpose: str) -> None:
    """Called from FastAPI BackgroundTasks — does not block the HTTP response."""
    try:
        ok, err = send_otp_email(to_email, otp_code, purpose=purpose)
        if not ok:
            log.error("Background OTP email failed for %s: %s", to_email, err)
    except Exception:
        log.exception("Background OTP email crashed for %s", to_email)


def send_welcome_email(to_email: str, name: str) -> None:
    """Fire-and-forget friendly; logs errors only."""
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
    try:
        _send_message(to_email, subject, plain, html)
    except Exception:
        log.exception("Welcome email failed for %s", to_email)
