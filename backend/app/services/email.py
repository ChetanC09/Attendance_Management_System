import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_password_reset_email(recipient: str, token: str) -> None:
    if not settings.smtp_host:
        logger.warning("Password reset email is not sent because SMTP is not configured")
        return
    link = f"{settings.frontend_base_url.rstrip('/')}/auth/reset-password?token={token}"
    send_email(
        recipient,
        "Reset your AMS password",
        "A password reset was requested for your AMS account. "
        f"Use this link within 30 minutes: {link}\n\n"
        "If you did not request this, ignore this email.",
    )


def send_otp_email(recipient: str, otp: str) -> None:
    subject = "Your AMS Password Verification Code"
    body = (
        f"Hello,\n\n"
        f"Your one-time verification code to update your AMS password is:\n\n"
        f"    {otp}\n\n"
        f"This code will expire in 15 minutes.\n"
        f"If you did not request this, please disregard this email.\n\n"
        f"— Attendance Management System"
    )
    if not settings.smtp_username:
        logger.warning(
            "🔑 [DEV NOTICE] Gmail SMTP username not yet set in .env. Verification OTP for %s is: %s",
            recipient,
            otp,
        )
        return
    try:
        send_email(recipient, subject, body)
    except Exception as exc:
        logger.error("Failed to send OTP email to %s: %s", recipient, exc)
        logger.warning("🔑 [FALLBACK] OTP for %s is: %s", recipient, otp)


def send_email(recipient: str, subject: str, body: str) -> None:
    if not settings.smtp_host:
        raise RuntimeError("SMTP is not configured")
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message.set_content(body)
    context = ssl.create_default_context()
    if settings.smtp_port == 465:
        with smtplib.SMTP_SSL(
            settings.smtp_host, settings.smtp_port, context=context, timeout=15
        ) as client:
            _send(client, message)
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as client:
            client.starttls(context=context)
            _send(client, message)


def _send(client: smtplib.SMTP, message: EmailMessage) -> None:
    if settings.smtp_username:
        password = settings.smtp_password.get_secret_value() if settings.smtp_password else ""
        client.login(settings.smtp_username, password)
    client.send_message(message)
