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
    message["Subject"] = f"Reset your {settings.site_name} password"
    message["From"] = settings.smtp_from_address or f"no-reply@{settings.site_name}"
    message["To"] = user.email
    # Resend uses this header to suppress duplicates if a pending outbox row is retried.
    message["Resend-Idempotency-Key"] = f"password-reset/{outbox.id}"
    message.set_content(
        f"We received a request to reset your {settings.site_name} password.\n\n"
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


def deliver_new_message_notification(db: Session, outbox: EmailOutbox, user: User) -> bool:
    payload = json.loads(outbox.payload_json)
    conversation_id = payload.get("conversation_id")
    conv_url = f"{settings.public_base_url}/messages.html?conversation={conversation_id}" if conversation_id else f"{settings.public_base_url}/messages.html"
    
    message = EmailMessage()
    message["Subject"] = f"New private message on {settings.site_name}"
    message["From"] = settings.smtp_from_address or f"no-reply@{settings.site_name}"
    message["To"] = user.email
    message["Resend-Idempotency-Key"] = f"new-message/{outbox.id}"
    message.set_content(
        f"You have received a new private message on {settings.site_name}.\n\n"
        f"View your conversation here:\n{conv_url}\n\n"
        "To protect member privacy, message contents are not included in email notifications."
    )

    outbox.attempts += 1
    if not settings.smtp_password:
        return False

    try:
        smtp_class = smtplib.SMTP_SSL if settings.smtp_use_ssl else smtplib.SMTP
        with smtp_class(settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout_seconds) as smtp:
            if settings.smtp_starttls and not settings.smtp_use_ssl:
                smtp.starttls()
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException):
        from datetime import datetime, timedelta, timezone
        outbox.next_attempt_at = datetime.now(timezone.utc) + timedelta(minutes=5 * outbox.attempts)
        if outbox.attempts >= 5:
            outbox.state = "failed"
        db.commit()
        return False

    from datetime import datetime, timezone
    outbox.state = "sent"
    outbox.sent_at = datetime.now(timezone.utc)
    outbox.payload_json = json.dumps({"delivered": True})
    db.commit()
    return True


def process_pending_outbox() -> int:
    """Worker function to process pending outbox items."""
    from datetime import datetime, timezone
    from sqlalchemy import select
    processed = 0
    with SessionLocal() as db:
        pending_items = db.scalars(
            select(EmailOutbox)
            .where(EmailOutbox.state == "pending", EmailOutbox.next_attempt_at <= datetime.now(timezone.utc))
            .order_by(EmailOutbox.created_at)
            .limit(50)
        ).all()
        for outbox in pending_items:
            user = db.get(User, outbox.recipient_user_id)
            if not user:
                outbox.state = "failed"
                db.commit()
                continue
            if outbox.template == "password_reset":
                if deliver_password_reset(db, outbox.id):
                    processed += 1
            elif outbox.template == "new_message":
                if deliver_new_message_notification(db, outbox, user):
                    processed += 1
    return processed
