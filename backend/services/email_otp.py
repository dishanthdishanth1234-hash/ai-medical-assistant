"""Send OTP emails via SMTP (optional). Falls back to logging when SMTP is not configured."""
import logging
import smtplib
from email.utils import formataddr
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import settings

log = logging.getLogger(__name__)


def send_otp_email(
    to_email: str,
    otp_code: str,
    *,
    subject: str = "Your verification code - AI Medical Assistant",
    intro: str = "Your AI Medical Assistant verification code is:",
    action_note: str = "If you did not request this, ignore this email.",
) -> bool:
    """Return True if an email was sent, False if skipped (dev / no SMTP)."""
    host = (settings.smtp_host or "").strip()
    user = (settings.smtp_user or "").strip()
    password = (settings.smtp_password or "").strip()
    port = settings.smtp_port
    from_addr = (settings.smtp_from or user or "").strip()
    if not host and user.lower().endswith("@gmail.com"):
        host = "smtp.gmail.com"
        port = port or 587

    body = (
        f"{intro}\n\n"
        f"{otp_code}\n\n"
        f"This code expires in {settings.otp_expire_minutes} minutes.\n"
        f"{action_note}"
    )

    if not host or not from_addr or not user or not password:
        log.warning("SMTP not configured - OTP for %s: %s (check server logs)", to_email, otp_code)
        return False

    try:
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = formataddr(("AI Medical Assistant", from_addr))
        msg["To"] = to_email
        msg.attach(MIMEText(body, "plain", "utf-8"))

        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=30) as server:
                if user and password:
                    server.login(user, password)
                server.sendmail(from_addr, [to_email], msg.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=30) as server:
                server.ehlo()
                if settings.smtp_use_tls:
                    server.starttls()
                    server.ehlo()
                if user and password:
                    server.login(user, password)
                server.sendmail(from_addr, [to_email], msg.as_string())
        log.info("OTP email sent to %s", to_email)
        return True
    except Exception:
        log.exception("Failed to send OTP email to %s - code was: %s", to_email, otp_code)
        return False
