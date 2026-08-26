import json
import smtplib
from email.message import EmailMessage

from sqlalchemy.orm import Session

from .config import settings
from .database import SessionLocal
from .models import EmailOutbox, User


def deliver_password_reset_by_id(outbox_id) -> bool:
    """Open a worker-safe session for a FastAPI background delivery task."""
    with SessionLocal() as db:
        return deliver_password_reset(db, outbox_id)


def deliver_password_reset(db: Session, outbox_id) -> bool:
    """Attempt one SMTP delivery and retain enough state for operational retry."""
    outbox = db.get(EmailOutbox, outbox_id)
    if not outbox or outbox.state != "pending":
        return False
    user = db.get(User, outbox.recipient_user_id)
    if not user or not settings.smtp_password:
        return False

    reset_url = json.loads(outbox.payload_json)["reset_url"]
    message = EmailMessage()
    message["Subject"] = "Reset your OpenSurgery password"
    message["From"] = settings.smtp_from_address
    message["To"] = user.email
    # Resend uses this header to suppress duplicates if a pending outbox row is retried.
    message["Resend-Idempotency-Key"] = f"password-reset/{outbox.id}"
    message.set_content(
        "We received a request to reset your OpenSurgery password.\n\n"
        f"Choose a new password within one hour:\n{reset_url}\n\n"
        "If you did not request this, you can ignore this email."
    )

    outbox.attempts += 1
    try:
        smtp_class = smtplib.SMTP_SSL if settings.smtp_use_ssl else smtplib.SMTP
        with smtp_class(settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout_seconds) as smtp:
            if settings.smtp_starttls and not settings.smtp_use_ssl:
                smtp.starttls()
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException):
        db.commit()
        return False

    from datetime import datetime, timezone
    outbox.state = "sent"
    outbox.sent_at = datetime.now(timezone.utc)
    outbox.payload_json = json.dumps({"delivered": True})
    db.commit()
    return True
