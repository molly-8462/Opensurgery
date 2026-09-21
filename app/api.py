import hashlib
import io
import json
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Response, UploadFile, status
from PIL import Image, UnidentifiedImageError
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import get_db
from .email import deliver_password_reset_by_id
from .config import settings
from .countries import COUNTRIES, country_code
from .models import (AccountToken, AuditEvent, Conversation, ConversationMember, EditProposal, EmailOutbox, Location, MediaAsset, Message,
                     ModerationState, Practice, Procedure, ProposalSource, RatingDimension, Report, Review, ReviewPhoto, ReviewRating,
                     RevisionKind, RevisionSource, Source, Surgeon,
                     SurgeonPractice, SurgeonRevision, TalkComment, TalkTopic, Technique, User, UserBlock, UserRole, surgeon_procedures)
from .schemas import (AdminAction, AdminRoleUpdate, LoginRequest, MessageCreate, MessageReply, PasswordResetConfirm, PasswordResetRequest,
                      ProposalCreate, RegisterRequest, ReportCreate, ReviewCreate, SettingsUpdate,
                      SurgeonCreate, SurgeonRemoval, TalkPost)
from .security import create_token, current_user, hash_password, verify_password
from .serializers import review_data, surgeon_detail, surgeon_summary


router = APIRouter(prefix="/api/v1")


def require_editor(user: User) -> None:
    if user.role not in {UserRole.trusted_editor, UserRole.moderator, UserRole.admin}:
        raise HTTPException(403, "Editor role required")


def require_admin(user: User) -> None:
    if user.role != UserRole.admin:
        raise HTTPException(403, "Administrator role required")


@router.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"status": "ok"}


@router.post("/auth/register", status_code=201)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    user = User(email=payload.email.lower(), display_name=payload.display_name, password_hash=hash_password(payload.password), approximate_region=payload.approximate_region)
    db.add(user)
    try: db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(409, "Email or display name already registered")
    token = create_token(user); response.set_cookie("opensurgery_session", token, httponly=True, secure=settings.cookie_secure, samesite="strict", max_age=settings.access_token_minutes * 60, path="/")
    return {"user": {"display_name": user.display_name}}


@router.post("/auth/login")
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    identity = payload.identity.lower()
    user = db.scalar(select(User).where(or_(func.lower(User.email) == identity, func.lower(User.display_name) == identity)))
    if not user or not user.is_active or user.deleted_at or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    token = create_token(user); response.set_cookie("opensurgery_session", token, httponly=True, secure=settings.cookie_secure, samesite="strict", max_age=settings.access_token_minutes * 60, path="/")
    return {"user": {"display_name": user.display_name}}


@router.post("/auth/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie("opensurgery_session", path="/", httponly=True, secure=settings.cookie_secure, samesite="strict")


@router.post("/auth/password-reset", status_code=202)
def request_password_reset(payload: PasswordResetRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(func.lower(User.email) == payload.email.lower(), User.is_active.is_(True)))
    if user:
        raw = secrets.token_urlsafe(48); digest = hashlib.sha256(raw.encode()).hexdigest()
        db.execute(delete(AccountToken).where(AccountToken.user_id == user.id, AccountToken.purpose == "password_reset", AccountToken.used_at.is_(None)))
        db.add(AccountToken(user_id=user.id, purpose="password_reset", token_hash=digest, expires_at=datetime.now(timezone.utc) + timedelta(hours=1)))
        # A URL fragment keeps the secret out of HTTP request lines, access logs, and referrers.
        reset_url = f"{settings.public_base_url.rstrip('/')}/reset-password.html#token={raw}"
        outbox = EmailOutbox(recipient_user_id=user.id, template="password_reset", payload_json=json.dumps({"reset_url": reset_url}))
        db.add(outbox); db.commit()
        background_tasks.add_task(deliver_password_reset_by_id, outbox.id)
    return {"message": "If an active account exists for that email, a reset link will arrive shortly."}


@router.post("/auth/password-reset/confirm")
def confirm_password_reset(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    digest = hashlib.sha256(payload.token.encode()).hexdigest(); current = datetime.now(timezone.utc)
    token = db.scalar(select(AccountToken).where(AccountToken.token_hash == digest, AccountToken.purpose == "password_reset", AccountToken.used_at.is_(None), AccountToken.expires_at > current).with_for_update())
    if not token: raise HTTPException(400, "Invalid or expired reset token")
    user = db.get(User, token.user_id)
    if not user or not user.is_active or user.deleted_at:
        raise HTTPException(400, "Invalid or expired reset token")
    user.password_hash = hash_password(payload.password); user.session_version += 1; token.used_at = current
    db.execute(delete(AccountToken).where(AccountToken.user_id == user.id, AccountToken.purpose == "password_reset", AccountToken.id != token.id))
    db.add(AuditEvent(actor_id=user.id, action="account.password_reset", target_type="user", target_id=user.id)); db.commit()
    return {"message": "Password updated"}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "display_name": user.display_name, "email": user.email, "role": user.role,
            "bio": user.bio, "approximate_region": user.approximate_region,
            "allow_messages": user.allow_messages, "allow_new_accounts": user.allow_new_accounts,
            "email_message_notifications": user.email_message_notifications,
            "email_watch_notifications": user.email_watch_notifications}


@router.patch("/me")
def update_me(payload: SettingsUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(user, key, value)
    db.add(AuditEvent(actor_id=user.id, action="account.settings_updated", target_type="user", target_id=user.id))
    db.commit(); return me(user)


@router.get("/me/export")
def export_me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    reviews = db.scalars(select(Review).where(Review.reviewer_id == user.id)).all()
    proposals = db.scalars(select(EditProposal).where(EditProposal.author_id == user.id)).all()
    return {"exported_at": datetime.now(timezone.utc), "account": me(user),
            "reviews": [{"slug": item.slug, "title": item.title, "state": item.state, "created_at": item.created_at} for item in reviews],
            "edit_proposals": [{"id": item.id, "summary": item.edit_summary, "state": item.state, "created_at": item.created_at} for item in proposals]}


@router.delete("/me", status_code=204)
def delete_me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    original_id = user.id; user.email = f"deleted-{user.id}@invalid.local"; user.display_name = f"Deleted-{str(user.id)[:8]}"; user.password_hash = "!deleted"; user.bio = None; user.approximate_region = None; user.allow_messages = False; user.is_active = False; user.deleted_at = datetime.now(timezone.utc)
    db.add(AuditEvent(actor_id=None, action="account.deleted", target_type="user", target_id=original_id)); db.commit()


@router.get("/admin/users/{display_name}")
def admin_user(display_name: str, admin: User = Depends(current_user), db: Session = Depends(get_db)):
    require_admin(admin)
    user = db.scalar(select(User).where(func.lower(User.display_name) == display_name.lower()))
    if not user: raise HTTPException(404, "User not found")
    return {"id": user.id, "display_name": user.display_name, "role": user.role,
            "is_active": user.is_active, "banned_at": user.banned_at, "ban_reason": user.ban_reason}


@router.patch("/admin/users/{display_name}/role")
def update_user_role(display_name: str, payload: AdminRoleUpdate, admin: User = Depends(current_user), db: Session = Depends(get_db)):
    require_admin(admin)
    user = db.scalar(select(User).where(func.lower(User.display_name) == display_name.lower()))
    if not user: raise HTTPException(404, "User not found")
    next_role = UserRole(payload.role)
    if user.id == admin.id and next_role != UserRole.admin:
        admin_count = db.scalar(select(func.count()).select_from(User).where(User.role == UserRole.admin, User.is_active.is_(True))) or 0
        if admin_count <= 1: raise HTTPException(409, "The last active administrator cannot be demoted")
    previous = user.role; user.role = next_role
    db.add(AuditEvent(actor_id=admin.id, action="user.role_changed", target_type="user", target_id=user.id,
                      private_detail=f"{previous.value} -> {next_role.value}"))
    db.commit(); return {"display_name": user.display_name, "role": user.role}


@router.post("/admin/users/{display_name}/ban")
def ban_user(display_name: str, payload: AdminAction, admin: User = Depends(current_user), db: Session = Depends(get_db)):
    require_admin(admin)
    user = db.scalar(select(User).where(func.lower(User.display_name) == display_name.lower()))
    if not user: raise HTTPException(404, "User not found")
    if user.id == admin.id: raise HTTPException(409, "Administrators cannot ban their own account")
    if not user.is_active: raise HTTPException(409, "User is already inactive")
    user.is_active = False; user.banned_at = datetime.now(timezone.utc); user.banned_by_id = admin.id; user.ban_reason = payload.reason
    db.add(AuditEvent(actor_id=admin.id, action="user.banned", target_type="user", target_id=user.id,
                      private_detail=payload.reason))
    db.commit(); return {"display_name": user.display_name, "status": "banned"}


@router.post("/admin/users/{display_name}/unban")
def unban_user(display_name: str, admin: User = Depends(current_user), db: Session = Depends(get_db)):
    require_admin(admin)
    user = db.scalar(select(User).where(func.lower(User.display_name) == display_name.lower()))
    if not user: raise HTTPException(404, "User not found")
    if user.is_active: raise HTTPException(409, "User is not banned")
    user.is_active = True; user.banned_at = None; user.banned_by_id = None; user.ban_reason = None
    db.add(AuditEvent(actor_id=admin.id, action="user.unbanned", target_type="user", target_id=user.id))
    db.commit(); return {"display_name": user.display_name, "status": "active"}


@router.get("/surgeons")
def surgeons(q: str | None = None, country: str | None = None, procedure: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Surgeon).where(Surgeon.is_published.is_(True)).order_by(Surgeon.updated_at.desc())
    if q: stmt = stmt.where(or_(Surgeon.display_name.ilike(f"%{q}%"), Surgeon.city.ilike(f"%{q}%"), Surgeon.region.ilike(f"%{q}%")))
    if country:
        selected_country = country_code(country)
        if not selected_country: return {"items": [], "total": 0}
        stmt = stmt.where(Surgeon.country_code == selected_country)
    if procedure:
        stmt = stmt.join(surgeon_procedures, surgeon_procedures.c.surgeon_id == Surgeon.id).join(Procedure, Procedure.id == surgeon_procedures.c.procedure_id).where(
            or_(Procedure.slug == procedure, Procedure.name == procedure)
        ).distinct()
    records = db.scalars(stmt).all()
    result = [surgeon_summary(db, record) for record in records]
    return {"items": result, "total": len(result)}


@router.post("/surgeons", status_code=201)
def create_surgeon(payload: SurgeonCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    slug_base = re.sub(r"[^a-z0-9]+", "-", payload.display_name.lower()).strip("-")[:105] or "surgeon"
    slug = slug_base
    suffix = 1
    while db.scalar(select(Surgeon.id).where(Surgeon.slug == slug)):
        suffix += 1
        slug = f"{slug_base}-{suffix}"
    procedures = db.scalars(select(Procedure).where(Procedure.slug.in_(set(payload.procedure_slugs)))).all()
    if len(procedures) != len(set(payload.procedure_slugs)):
        raise HTTPException(400, "One or more procedures are unknown")
    source = Source(url=str(payload.source_url), supports=payload.source_note, submitted_by_id=user.id)
    db.add(source); db.flush()
    selected_country = country_code(payload.country_code)
    if not selected_country: raise HTTPException(400, "Unknown country code")
    record = Surgeon(slug=slug, display_name=payload.display_name.strip(),
                     specialty=payload.specialty.strip(), city=payload.city.strip(),
                     region=payload.region.strip() if payload.region else None,
                     country_code=selected_country,
                     website_url=str(payload.website_url) if payload.website_url else None,
                     is_published=False, lifecycle_status="pending", submitted_by_id=user.id)
    db.add(record); db.flush()
    snapshot = {"practice": payload.practice_name, "procedure_slugs": payload.procedure_slugs}
    revision = SurgeonRevision(surgeon_id=record.id, revision_number=1, author_id=user.id,
                               article_body=payload.article_body, snapshot_json=json.dumps(snapshot),
                               edit_summary="Initial profile submission", change_type="New profile")
    db.add(revision); db.flush(); record.current_revision_id = revision.id
    db.execute(surgeon_procedures.insert(), [{"surgeon_id": record.id, "procedure_id": item.id} for item in procedures])
    db.add(RevisionSource(revision_id=revision.id, source_id=source.id))
    db.add(AuditEvent(actor_id=user.id, action="surgeon.submitted", target_type="surgeon", target_id=record.id,
                      public_detail=f"Submitted {record.display_name} for review"))
    db.commit()
    return {"id": record.id, "slug": record.slug, "status": record.lifecycle_status}


@router.get("/moderation/surgeons")
def pending_surgeons(user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_editor(user)
    rows = db.scalars(select(Surgeon).where(Surgeon.lifecycle_status == "pending").order_by(Surgeon.created_at)).all()
    items = []
    for row in rows:
        revision = db.get(SurgeonRevision, row.current_revision_id) if row.current_revision_id else None
        source_rows = db.execute(select(Source.url, Source.supports).join(
            RevisionSource, RevisionSource.source_id == Source.id
        ).where(RevisionSource.revision_id == row.current_revision_id)).all() if revision else []
        items.append({"id": row.id, "slug": row.slug, "name": row.display_name,
                      "specialty": row.specialty, "city": row.city, "region": row.region,
                      "country_code": row.country_code, "submitted_at": row.created_at,
                      "article_body": revision.article_body if revision else "",
                      "sources": [{"url": source.url, "note": source.supports} for source in source_rows],
                      "submitter": db.get(User, row.submitted_by_id).display_name if row.submitted_by_id and db.get(User, row.submitted_by_id) else "Deleted member"})
    return {"items": items}


@router.post("/moderation/surgeons/{surgeon_id}/approve")
def approve_surgeon(surgeon_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_editor(user)
    record = db.get(Surgeon, surgeon_id)
    if not record or record.lifecycle_status != "pending":
        raise HTTPException(404, "Pending surgeon submission not found")
    record.lifecycle_status = "published"; record.is_published = True
    db.add(AuditEvent(actor_id=user.id, action="surgeon.approved", target_type="surgeon", target_id=record.id,
                      public_detail=f"Published {record.display_name}"))
    db.commit(); return {"slug": record.slug, "status": record.lifecycle_status}


@router.post("/moderation/surgeons/{slug}/remove")
def remove_surgeon(slug: str, payload: SurgeonRemoval, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_admin(user)
    record = db.scalar(select(Surgeon).where(Surgeon.slug == slug))
    if not record: raise HTTPException(404, "Surgeon not found")
    record.lifecycle_status = payload.status; record.is_published = False
    record.removed_at = datetime.now(timezone.utc); record.removed_by_id = user.id; record.removal_reason = payload.reason
    db.add(AuditEvent(actor_id=user.id, action=f"surgeon.{payload.status}", target_type="surgeon", target_id=record.id,
                      public_detail=payload.reason))
    db.commit(); return {"slug": record.slug, "status": record.lifecycle_status}


@router.post("/moderation/surgeons/{slug}/restore")
def restore_surgeon(slug: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_editor(user)
    record = db.scalar(select(Surgeon).where(Surgeon.slug == slug))
    if not record or record.lifecycle_status not in {"removed", "retired"}:
        raise HTTPException(404, "Removed surgeon not found")
    record.lifecycle_status = "published"; record.is_published = True
    record.removed_at = None; record.removed_by_id = None; record.removal_reason = None
    db.add(AuditEvent(actor_id=user.id, action="surgeon.restored", target_type="surgeon", target_id=record.id,
                      public_detail=f"Restored {record.display_name}"))
    db.commit(); return {"slug": record.slug, "status": record.lifecycle_status}


@router.get("/moderation/reviews")
def pending_reviews(user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_editor(user)
    reviews = db.scalars(select(Review).where(Review.state == ModerationState.pending).order_by(Review.created_at)).all()
    items = []
    for r in reviews:
        surgeon = db.get(Surgeon, r.surgeon_id)
        reviewer = db.get(User, r.reviewer_id) if r.reviewer_id else None
        procedure = db.get(Procedure, r.procedure_id)
        photos = db.scalars(select(ReviewPhoto).where(ReviewPhoto.review_id == r.id)).all()
        items.append({
            "id": r.id,
            "slug": r.slug,
            "title": r.title,
            "narrative": r.narrative,
            "surgeon_name": surgeon.display_name if surgeon else "Unknown",
            "procedure_name": procedure.name if procedure else "Unknown",
            "reviewer_name": reviewer.display_name if reviewer else "Anonymous",
            "created_at": r.created_at,
            "photos": [{"id": p.id, "media_id": p.media_id, "approved_at": p.approved_at, "designated_long_term": p.designated_long_term} for p in photos]
        })
    return {"items": items}


@router.post("/moderation/reviews/{review_id}/approve")
def approve_review(review_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_editor(user)
    review = db.get(Review, review_id)
    if not review or review.state != ModerationState.pending:
        raise HTTPException(404, "Pending review not found")
    review.state = ModerationState.published
    review.published_at = datetime.now(timezone.utc)
    photos = db.scalars(select(ReviewPhoto).where(ReviewPhoto.review_id == review.id)).all()
    for photo in photos:
        if not photo.approved_at:
            photo.approved_at = datetime.now(timezone.utc)
    db.add(AuditEvent(actor_id=user.id, action="review.approved", target_type="review", target_id=review.id))
    db.commit()
    return {"id": review.id, "slug": review.slug, "state": review.state}


@router.post("/moderation/reviews/{review_id}/reject")
def reject_review(review_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_editor(user)
    review = db.get(Review, review_id)
    if not review or review.state != ModerationState.pending:
        raise HTTPException(404, "Pending review not found")
    review.state = ModerationState.rejected
    db.add(AuditEvent(actor_id=user.id, action="review.rejected", target_type="review", target_id=review.id))
    db.commit()
    return {"id": review.id, "state": review.state}


@router.post("/moderation/photos/{photo_id}/approve")
def approve_photo(photo_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_editor(user)
    photo = db.get(ReviewPhoto, photo_id)
    if not photo:
        raise HTTPException(404, "Photo not found")
    photo.approved_at = datetime.now(timezone.utc)
    db.add(AuditEvent(actor_id=user.id, action="photo.approved", target_type="review_photo", target_id=photo.id))
    db.commit()
    return {"id": photo.id, "approved_at": photo.approved_at}


@router.post("/moderation/photos/{photo_id}/reject")
def reject_photo(photo_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_editor(user)
    photo = db.get(ReviewPhoto, photo_id)
    if not photo:
        raise HTTPException(404, "Photo not found")
    photo.approved_at = None
    db.add(AuditEvent(actor_id=user.id, action="photo.rejected", target_type="review_photo", target_id=photo.id))
    db.commit()
    return {"id": photo.id, "approved_at": None}



@router.get("/surgeons/{slug}")
def surgeon(slug: str, db: Session = Depends(get_db)):
    record = db.scalar(select(Surgeon).where(Surgeon.slug == slug, Surgeon.is_published.is_(True)))
    if not record: raise HTTPException(404, "Surgeon not found")
    return surgeon_detail(db, record)


@router.get("/surgeons/{slug}/reviews")
def surgeon_reviews(slug: str, db: Session = Depends(get_db), limit: int = 25, offset: int = 0):
    record = db.scalar(select(Surgeon).where(Surgeon.slug == slug, Surgeon.is_published.is_(True)))
    if not record: raise HTTPException(404, "Surgeon not found")
    limit = max(1, min(limit, 100)); offset = max(0, offset)
    filters = (Review.surgeon_id == record.id, Review.state == ModerationState.published)
    total = db.scalar(select(func.count()).select_from(Review).where(*filters)) or 0
    reviews = db.scalars(select(Review).where(*filters).order_by(Review.published_at.desc()).offset(offset).limit(limit)).all()
    return {"items": [review_data(db, review) for review in reviews], "total": total,
            "limit": limit, "offset": offset, "has_more": offset + len(reviews) < total}


@router.post("/admin/reviews/{slug}/remove")
def remove_review(slug: str, payload: AdminAction, admin: User = Depends(current_user), db: Session = Depends(get_db)):
    require_admin(admin)
    record = db.scalar(select(Review).where(Review.slug == slug))
    if not record: raise HTTPException(404, "Review not found")
    if record.state == ModerationState.hidden: raise HTTPException(409, "Review is already removed")
    record.state = ModerationState.hidden
    db.add(AuditEvent(actor_id=admin.id, action="review.removed", target_type="review", target_id=record.id,
                      private_detail=payload.reason))
    db.commit(); return {"slug": record.slug, "status": "removed"}


@router.get("/reviews/{slug}")
def review(slug: str, db: Session = Depends(get_db)):
    record = db.scalar(select(Review).join(Surgeon).where(Review.slug == slug,
                       Review.state == ModerationState.published, Surgeon.is_published.is_(True)))
    if not record: raise HTTPException(404, "Review not found")
    return review_data(db, record)


@router.post("/reviews", status_code=201)
def create_review(payload: ReviewCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    surgeon = db.scalar(select(Surgeon).where(Surgeon.slug == payload.surgeon_slug, Surgeon.is_published.is_(True))); procedure = db.scalar(select(Procedure).where(Procedure.slug == payload.procedure_slug))
    technique = db.scalar(select(Technique).where(Technique.slug == payload.technique_slug)) if payload.technique_slug else None
    if not surgeon or not procedure: raise HTTPException(400, "Unknown surgeon or procedure")
    if payload.technique_slug and (not technique or technique.procedure_id != procedure.id):
        raise HTTPException(400, "Unknown technique for this procedure")
    base = re.sub(r"[^a-z0-9]+", "-", payload.title.lower()).strip("-")[:100] or "review"
    review_values = payload.model_dump(exclude={"surgeon_slug","procedure_slug","technique_slug","ratings","media_ids","designated_long_term_media_id"})
    record = Review(**review_values, slug=f"{base}-{uuid.uuid4().hex[:8]}", surgeon_id=surgeon.id, reviewer_id=user.id, procedure_id=procedure.id, technique_id=technique.id if technique else None)
    db.add(record); db.flush()
    for dimension_slug, value in payload.ratings.items():
        if value < 1 or value > 5: raise HTTPException(422, "Ratings must be from 1 to 5")
        dimension = db.scalar(select(RatingDimension).where(RatingDimension.slug == dimension_slug, RatingDimension.is_active.is_(True)))
        if not dimension: raise HTTPException(422, f"Unknown rating dimension: {dimension_slug}")
        db.add(ReviewRating(review_id=record.id, dimension_id=dimension.id, value=value))
    if payload.designated_long_term_media_id and payload.designated_long_term_media_id not in payload.media_ids:
        raise HTTPException(422, "The long-term photo must be one of the attached media items")
    for media_id in payload.media_ids:
        media = db.get(MediaAsset, media_id)
        if not media or media.owner_id != user.id or media.processing_state != "ready":
            raise HTTPException(422, "An attached image is unavailable")
        db.add(ReviewPhoto(review_id=record.id, media_id=media.id,
                           designated_long_term=media.id == payload.designated_long_term_media_id))
    db.commit(); return {"slug": record.slug, "state": record.state}


@router.get("/surgeons/{slug}/history")
def history(slug: str, db: Session = Depends(get_db)):
    surgeon = db.scalar(select(Surgeon).where(Surgeon.slug == slug, Surgeon.is_published.is_(True)));
    if not surgeon: raise HTTPException(404, "Surgeon not found")
    rows = db.scalars(select(SurgeonRevision).where(SurgeonRevision.surgeon_id == surgeon.id).order_by(SurgeonRevision.revision_number.desc())).all()
    return {"items": [{"revision_number": r.revision_number, "published_at": r.published_at, "editor": db.get(User,r.author_id).display_name if r.author_id and db.get(User,r.author_id) else "Deleted member", "summary": r.edit_summary, "change_type": r.change_type, "kind": r.kind} for r in rows]}


@router.get("/surgeons/{slug}/revisions/{number}")
def revision(slug: str, number: int, db: Session = Depends(get_db)):
    row = db.scalar(select(SurgeonRevision).join(Surgeon).where(Surgeon.slug == slug, Surgeon.is_published.is_(True), SurgeonRevision.revision_number == number))
    if not row: raise HTTPException(404, "Revision not found")
    return {"revision_number": row.revision_number, "article_body": row.article_body, "profile": json.loads(row.snapshot_json), "summary": row.edit_summary, "change_type": row.change_type, "kind": row.kind, "published_at": row.published_at}


@router.post("/surgeons/{slug}/proposals", status_code=201)
def proposal(slug: str, payload: ProposalCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    surgeon = db.scalar(select(Surgeon).where(Surgeon.slug == slug, Surgeon.is_published.is_(True)));
    if not surgeon: raise HTTPException(404, "Surgeon not found")
    profile = payload.profile.copy()
    profile["procedure_slugs"] = payload.procedure_slugs
    proposal = EditProposal(surgeon_id=surgeon.id, base_revision_id=surgeon.current_revision_id, author_id=user.id, proposed_article_body=payload.proposed_article_body, proposed_snapshot_json=json.dumps(profile), edit_summary=payload.edit_summary, state=ModerationState.pending, submitted_at=datetime.now(timezone.utc))
    db.add(proposal); db.flush()
    if payload.source_url:
        source = Source(url=str(payload.source_url), supports=payload.source_note or None, submitted_by_id=user.id)
        db.add(source); db.flush(); db.add(ProposalSource(proposal_id=proposal.id, source_id=source.id))
    db.commit(); return {"id": proposal.id, "state": proposal.state}


@router.get("/surgeons/{slug}/talk")
def talk(slug: str, db: Session = Depends(get_db)):
    surgeon = db.scalar(select(Surgeon).where(Surgeon.slug == slug, Surgeon.is_published.is_(True)));
    if not surgeon: raise HTTPException(404, "Surgeon not found")
    topics = db.scalars(select(TalkTopic).where(TalkTopic.surgeon_id == surgeon.id, TalkTopic.state == ModerationState.published).order_by(TalkTopic.created_at)).all()
    return {"items": [{"slug": t.slug, "title": t.title, "comments": [{"id": c.id, "author": db.get(User,c.author_id).display_name if c.author_id and db.get(User,c.author_id) else "Deleted member", "body": c.body, "created_at": c.created_at, "parent_comment_id": c.parent_comment_id} for c in db.scalars(select(TalkComment).where(TalkComment.topic_id == t.id, TalkComment.state == ModerationState.published).order_by(TalkComment.created_at)).all()]} for t in topics]}


@router.post("/surgeons/{slug}/talk", status_code=201)
def create_talk_topic(slug: str, payload: TalkPost, user: User = Depends(current_user), db: Session = Depends(get_db)):
    surgeon = db.scalar(select(Surgeon).where(Surgeon.slug == slug, Surgeon.is_published.is_(True)))
    if not surgeon: raise HTTPException(404, "Surgeon not found")
    topic_slug = re.sub(r"[^a-z0-9]+", "-", payload.title.lower()).strip("-")[:110] + "-" + uuid.uuid4().hex[:6]
    topic = TalkTopic(surgeon_id=surgeon.id, slug=topic_slug, title=payload.title, author_id=user.id)
    db.add(topic); db.flush(); db.add(TalkComment(topic_id=topic.id, author_id=user.id, body=payload.body)); db.commit()
    return {"slug": topic.slug}


@router.get("/procedures")
def procedures(db: Session = Depends(get_db)):
    rows = db.scalars(select(Procedure).order_by(Procedure.category, Procedure.name)).all()
    return {"items": [{"slug": p.slug, "name": p.name, "category": p.category, "description": p.description,
                        "techniques": [{"slug": t.slug, "name": t.name} for t in db.scalars(
                            select(Technique).where(Technique.procedure_id == p.id).order_by(Technique.name)
                        ).all()]} for p in rows]}


@router.get("/countries")
def countries():
    return {"items": COUNTRIES}


@router.get("/practices/{slug}")
def practice(slug: str, db: Session = Depends(get_db)):
    record = db.scalar(select(Practice).where(Practice.slug == slug))
    if not record: raise HTTPException(404, "Practice not found")
    locations = db.scalars(select(Location).where(Location.practice_id == record.id)).all()
    surgeon_rows = db.scalars(select(Surgeon).join(SurgeonPractice).where(SurgeonPractice.practice_id == record.id, Surgeon.is_published.is_(True))).all()
    return {"slug": record.slug, "name": record.name, "website_url": record.website_url,
            "locations": [{"city": x.city, "region": x.region, "country_code": x.country_code, "accessibility": x.accessibility} for x in locations],
            "surgeons": [{"slug": x.slug, "name": x.display_name} for x in surgeon_rows]}


@router.get("/proposals")
def proposals(db: Session = Depends(get_db)):
    rows = db.scalars(select(EditProposal).where(EditProposal.state == ModerationState.pending).order_by(EditProposal.submitted_at.desc())).all()
    return {"items": [{"id": p.id, "surgeon": surgeon_summary(db, db.get(Surgeon, p.surgeon_id)), "author": db.get(User,p.author_id).display_name if p.author_id and db.get(User,p.author_id) else "Deleted member", "summary": p.edit_summary, "submitted_at": p.submitted_at, "state": p.state} for p in rows]}


@router.get("/users/{display_name}")
def profile(display_name: str, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(func.lower(User.display_name) == display_name.lower(), User.is_active.is_(True)))
    if not user: raise HTTPException(404, "User not found")
    reviews_count = db.scalar(select(func.count()).select_from(Review).where(Review.reviewer_id == user.id, Review.state == ModerationState.published)) or 0
    edits_count = db.scalar(select(func.count()).select_from(SurgeonRevision).where(SurgeonRevision.author_id == user.id)) or 0
    talk_count = db.scalar(select(func.count()).select_from(TalkComment).where(TalkComment.author_id == user.id)) or 0
    return {"display_name": user.display_name, "bio": user.bio, "approximate_region": user.approximate_region, "allow_messages": user.allow_messages, "member_since": user.created_at.date(), "reviews_count": reviews_count, "edits_count": edits_count, "talk_count": talk_count}


def check_block_status(db: Session, user_a_id: uuid.UUID, user_b_id: uuid.UUID) -> None:
    blocked = db.scalar(select(UserBlock).where(or_((UserBlock.blocker_id == user_a_id) & (UserBlock.blocked_id == user_b_id), (UserBlock.blocker_id == user_b_id) & (UserBlock.blocked_id == user_a_id))))
    if blocked: raise HTTPException(403, "Messaging is blocked between these accounts")


@router.post("/messages", status_code=201)
def send_message(payload: MessageCreate, sender: User = Depends(current_user), db: Session = Depends(get_db)):
    recipient = db.scalar(select(User).where(func.lower(User.display_name) == payload.recipient.lower()))
    if not recipient or not recipient.allow_messages: raise HTTPException(403, "This member is not accepting messages")
    if recipient.id == sender.id: raise HTTPException(400, "Cannot send a message to yourself")
    check_block_status(db, sender.id, recipient.id)
    if recipient.allow_new_accounts is False:
        sender_created = sender.created_at.replace(tzinfo=timezone.utc) if sender.created_at and sender.created_at.tzinfo is None else sender.created_at
        if sender_created and (datetime.now(timezone.utc) - sender_created) < timedelta(days=7):
            raise HTTPException(403, "This member does not accept messages from new accounts")
    conv_id = db.scalar(select(ConversationMember.conversation_id).where(ConversationMember.user_id.in_([sender.id, recipient.id])).group_by(ConversationMember.conversation_id).having(func.count(ConversationMember.user_id) == 2))
    if not conv_id:
        conversation = Conversation(); db.add(conversation); db.flush(); conv_id = conversation.id
        db.add_all([ConversationMember(conversation_id=conv_id, user_id=sender.id), ConversationMember(conversation_id=conv_id, user_id=recipient.id)])
    db.add(Message(conversation_id=conv_id, sender_id=sender.id, body=payload.body))
    if recipient.email_message_notifications: db.add(EmailOutbox(recipient_user_id=recipient.id, template="new_message", payload_json=json.dumps({"conversation_id": str(conv_id)})))
    db.commit(); return {"conversation_id": conv_id}


@router.get("/conversations")
def conversations(user: User = Depends(current_user), db: Session = Depends(get_db)):
    memberships = db.scalars(select(ConversationMember).where(ConversationMember.user_id == user.id)).all()
    items = []
    for membership in memberships:
        other = db.scalar(select(User).join(ConversationMember, ConversationMember.user_id == User.id).where(ConversationMember.conversation_id == membership.conversation_id, User.id != user.id))
        last = db.scalar(select(Message).where(Message.conversation_id == membership.conversation_id, Message.deleted_at.is_(None)).order_by(Message.created_at.desc()).limit(1))
        items.append({"id": membership.conversation_id, "member": other.display_name if other else "Deleted member", "last_message": last.body if last else "", "updated_at": last.created_at if last else membership.joined_at})
    return {"items": sorted(items, key=lambda x: x["updated_at"], reverse=True)}


@router.get("/conversations/{conversation_id}/messages")
def conversation_messages(conversation_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    member = db.get(ConversationMember, {"conversation_id": conversation_id, "user_id": user.id})
    if not member: raise HTTPException(404, "Conversation not found")
    rows = db.scalars(select(Message).where(Message.conversation_id == conversation_id, Message.deleted_at.is_(None)).order_by(Message.created_at)).all()
    member.last_read_at = datetime.now(timezone.utc); db.commit()
    return {"items": [{"id": row.id, "sender": db.get(User,row.sender_id).display_name if row.sender_id and db.get(User,row.sender_id) else "Deleted member", "body": row.body, "created_at": row.created_at, "mine": row.sender_id == user.id} for row in rows]}


@router.post("/conversations/{conversation_id}/messages", status_code=201)
def reply_to_conversation(conversation_id: uuid.UUID, payload: MessageReply, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not db.get(ConversationMember, {"conversation_id": conversation_id, "user_id": user.id}): raise HTTPException(404, "Conversation not found")
    other_members = db.scalars(select(User).join(ConversationMember, ConversationMember.user_id == User.id).where(ConversationMember.conversation_id == conversation_id, User.id != user.id)).all()
    for other in other_members:
        if not other.allow_messages: raise HTTPException(403, f"{other.display_name} is not accepting messages")
        check_block_status(db, user.id, other.id)
    message = Message(conversation_id=conversation_id, sender_id=user.id, body=payload.body); db.add(message)
    for other in other_members:
        if other.email_message_notifications: db.add(EmailOutbox(recipient_user_id=other.id, template="new_message", payload_json=json.dumps({"conversation_id": str(conversation_id)})))
    db.commit()
    return {"id": message.id, "created_at": message.created_at}


@router.post("/users/{display_name}/block")
def block_user(display_name: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    target = db.scalar(select(User).where(func.lower(User.display_name) == display_name.lower(), User.is_active.is_(True)))
    if not target: raise HTTPException(404, "User not found")
    if target.id == user.id: raise HTTPException(400, "Cannot block yourself")
    existing = db.get(UserBlock, {"blocker_id": user.id, "blocked_id": target.id})
    if not existing:
        db.add(UserBlock(blocker_id=user.id, blocked_id=target.id))
        db.add(AuditEvent(actor_id=user.id, action="user.blocked", target_type="user", target_id=target.id))
        db.commit()
    return {"status": "blocked", "display_name": target.display_name}


@router.post("/users/{display_name}/unblock")
def unblock_user(display_name: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    target = db.scalar(select(User).where(func.lower(User.display_name) == display_name.lower()))
    if not target: raise HTTPException(404, "User not found")
    existing = db.get(UserBlock, {"blocker_id": user.id, "blocked_id": target.id})
    if existing:
        db.delete(existing)
        db.add(AuditEvent(actor_id=user.id, action="user.unblocked", target_type="user", target_id=target.id))
        db.commit()
    return {"status": "unblocked", "display_name": target.display_name}


@router.post("/reports", status_code=201)
def create_report(payload: ReportCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    try: target_id = uuid.UUID(payload.target_id)
    except ValueError: raise HTTPException(400, "Invalid target id")
    if payload.target_type == "surgeon" and not db.get(Surgeon, target_id): raise HTTPException(400, "Target surgeon does not exist")
    elif payload.target_type == "review" and not db.get(Review, target_id): raise HTTPException(400, "Target review does not exist")
    elif payload.target_type == "user" and not db.get(User, target_id): raise HTTPException(400, "Target user does not exist")
    elif payload.target_type == "talk_comment" and not db.get(TalkComment, target_id): raise HTTPException(400, "Target talk comment does not exist")
    report = Report(reporter_id=user.id, target_type=payload.target_type, target_id=target_id, reason=payload.reason, details=payload.details)
    db.add(report); db.add(AuditEvent(actor_id=user.id, action="report.created", target_type=payload.target_type, target_id=target_id)); db.commit()
    return {"id": report.id, "state": report.state}


@router.get("/moderation/reports")
def list_reports(user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_editor(user)
    reports = db.scalars(select(Report).order_by(Report.created_at.desc())).all()
    return {"items": [{"id": r.id, "target_type": r.target_type, "target_id": r.target_id, "reason": r.reason, "details": r.details, "state": r.state, "created_at": r.created_at} for r in reports]}


@router.post("/moderation/reports/{report_id}/resolve")
def resolve_report(report_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_editor(user)
    report = db.get(Report, report_id)
    if not report: raise HTTPException(404, "Report not found")
    report.state = "resolved"
    db.add(AuditEvent(actor_id=user.id, action="report.resolved", target_type="report", target_id=report.id))
    db.commit()
    return {"id": report.id, "state": report.state}


@router.post("/moderation/proposals/{proposal_id}/reject")
def reject_proposal(proposal_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_editor(user)
    proposal = db.get(EditProposal, proposal_id)
    if not proposal or proposal.state != ModerationState.pending: raise HTTPException(404, "Pending proposal not found")
    proposal.state = ModerationState.rejected
    proposal.decided_at = datetime.now(timezone.utc)
    proposal.decided_by_id = user.id
    db.add(AuditEvent(actor_id=user.id, action="proposal.rejected", target_type="edit_proposal", target_id=proposal.id))
    db.commit()
    return {"id": proposal.id, "state": proposal.state}


@router.post("/media", status_code=201)
async def upload_media(file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    raw = await file.read(10 * 1024 * 1024 + 1)
    if len(raw) > 10 * 1024 * 1024: raise HTTPException(413, "Image exceeds the 10 MB limit")
    try:
        image = Image.open(io.BytesIO(raw)); image.load()
    except (UnidentifiedImageError, OSError): raise HTTPException(415, "Unsupported or invalid image")
    if image.format not in {"JPEG", "PNG", "WEBP"}: raise HTTPException(415, "Only JPEG, PNG, and WebP are accepted")
    image.thumbnail((4096, 4096)); image = image.convert("RGB")
    output = io.BytesIO(); image.save(output, format="WEBP", quality=88, method=6)
    safe = output.getvalue(); digest = hashlib.sha256(safe).hexdigest(); key = f"{user.id}/{uuid.uuid4().hex}.webp"
    target = settings.media_root / key; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(safe)
    asset = MediaAsset(owner_id=user.id, storage_key=key, safe_storage_key=key, media_type="image/webp", byte_size=len(safe), width=image.width, height=image.height, sha256=digest, processing_state="ready")
    db.add(asset); db.commit(); return {"id": asset.id, "processing_state": asset.processing_state}


@router.get("/media/{media_id}")
def serve_media(media_id: uuid.UUID, db: Session = Depends(get_db)):
    asset = db.get(MediaAsset, media_id)
    if not asset: raise HTTPException(404, "Media asset not found")
    filepath = settings.media_root / (asset.safe_storage_key or asset.storage_key)
    if not filepath.exists(): raise HTTPException(404, "Media file not found")
    return FileResponse(filepath, media_type=asset.media_type)


@router.post("/moderation/proposals/{proposal_id}/approve")
def approve_proposal(proposal_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_editor(user)
    proposal = db.get(EditProposal, proposal_id)
    if not proposal or proposal.state != ModerationState.pending: raise HTTPException(404, "Pending proposal not found")
    surgeon = db.scalar(select(Surgeon).where(Surgeon.id == proposal.surgeon_id).with_for_update())
    if not surgeon: raise HTTPException(404, "Surgeon not found")
    if proposal.base_revision_id and proposal.base_revision_id != surgeon.current_revision_id:
        raise HTTPException(409, "Proposal is based on a stale revision of the surgeon profile")
    snapshot = json.loads(proposal.proposed_snapshot_json)
    country = snapshot.get("country")
    selected_country = None
    if country:
        selected_country = country_code(country)
        if not selected_country: raise HTTPException(400, "Proposal contains an unknown country")
    procedure_slugs = snapshot.get("procedure_slugs")
    selected_procedures = []
    if procedure_slugs:
        selected_procedures = db.scalars(select(Procedure).where(Procedure.slug.in_(procedure_slugs))).all()
        if len(selected_procedures) != len(set(procedure_slugs)): raise HTTPException(400, "Proposal contains an unknown procedure")
    try:
        latest = db.scalar(select(func.max(SurgeonRevision.revision_number)).where(SurgeonRevision.surgeon_id == surgeon.id)) or 0
        revision = SurgeonRevision(surgeon_id=surgeon.id, revision_number=latest + 1, parent_revision_id=surgeon.current_revision_id, author_id=proposal.author_id, article_body=proposal.proposed_article_body, snapshot_json=proposal.proposed_snapshot_json, edit_summary=proposal.edit_summary, change_type="Article text", kind=RevisionKind.reviewed)
        db.add(revision); db.flush()
        surgeon.current_revision_id = revision.id; proposal.state = ModerationState.published; proposal.decided_at = datetime.now(timezone.utc); proposal.decided_by_id = user.id
        for key in ("specialty", "city", "region", "website_url"):
            if key in snapshot: setattr(surgeon, key, snapshot[key] or None)
        if selected_country: surgeon.country_code = selected_country
        if procedure_slugs:
            db.execute(delete(surgeon_procedures).where(surgeon_procedures.c.surgeon_id == surgeon.id))
            db.execute(surgeon_procedures.insert(), [{"surgeon_id": surgeon.id, "procedure_id": item.id} for item in selected_procedures])
        for link in db.scalars(select(ProposalSource).where(ProposalSource.proposal_id == proposal.id)).all():
            db.add(RevisionSource(revision_id=revision.id, source_id=link.source_id))
        db.add(AuditEvent(actor_id=user.id, action="proposal.approved", target_type="edit_proposal", target_id=proposal.id, public_detail=proposal.edit_summary)); db.commit()
        return {"revision_number": revision.revision_number}
    except Exception:
        db.rollback()
        raise
