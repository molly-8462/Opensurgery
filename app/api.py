import hashlib
import io
import json
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from PIL import Image, UnidentifiedImageError
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import get_db
from .config import settings
from .models import (AccountToken, AuditEvent, Conversation, ConversationMember, EditProposal, EmailOutbox, Location, MediaAsset, Message,
                     ModerationState, Practice, Procedure, ProposalSource, RatingDimension, Report, Review, ReviewPhoto, ReviewRating,
                     RevisionKind, RevisionSource, Source, Surgeon,
                     SurgeonPractice, SurgeonRevision, TalkComment, TalkTopic, Technique, User, UserRole, surgeon_procedures)
from .schemas import (LoginRequest, MessageCreate, MessageReply, PasswordResetConfirm, PasswordResetRequest,
                      ProposalCreate, RegisterRequest, ReportCreate, ReviewCreate, SettingsUpdate, TalkPost)
from .security import create_token, current_user, hash_password, verify_password
from .serializers import review_data, surgeon_detail, surgeon_summary


router = APIRouter(prefix="/api/v1")


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
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    token = create_token(user); response.set_cookie("opensurgery_session", token, httponly=True, secure=settings.cookie_secure, samesite="strict", max_age=settings.access_token_minutes * 60, path="/")
    return {"user": {"display_name": user.display_name}}


@router.post("/auth/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie("opensurgery_session", path="/", httponly=True, secure=settings.cookie_secure, samesite="strict")


@router.post("/auth/password-reset", status_code=202)
def request_password_reset(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(func.lower(User.email) == payload.email.lower(), User.is_active.is_(True)))
    if user:
        raw = secrets.token_urlsafe(48); digest = hashlib.sha256(raw.encode()).hexdigest()
        db.add(AccountToken(user_id=user.id, purpose="password_reset", token_hash=digest, expires_at=datetime.now(timezone.utc) + timedelta(hours=1)))
        db.add(EmailOutbox(recipient_user_id=user.id, template="password_reset", payload_json=json.dumps({"token": raw})))
        db.commit()
    return {"message": "If the account exists, reset instructions have been queued."}


@router.post("/auth/password-reset/confirm")
def confirm_password_reset(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    digest = hashlib.sha256(payload.token.encode()).hexdigest(); current = datetime.now(timezone.utc)
    token = db.scalar(select(AccountToken).where(AccountToken.token_hash == digest, AccountToken.purpose == "password_reset", AccountToken.used_at.is_(None), AccountToken.expires_at > current))
    if not token: raise HTTPException(400, "Invalid or expired reset token")
    user = db.get(User, token.user_id); user.password_hash = hash_password(payload.password); token.used_at = current
    db.add(AuditEvent(actor_id=user.id, action="account.password_reset", target_type="user", target_id=user.id)); db.commit()
    return {"message": "Password updated"}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "display_name": user.display_name, "email": user.email, "bio": user.bio, "approximate_region": user.approximate_region,
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


@router.get("/surgeons")
def surgeons(q: str | None = None, country: str | None = None, procedure: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Surgeon).where(Surgeon.is_published.is_(True)).order_by(Surgeon.updated_at.desc())
    if q: stmt = stmt.where(or_(Surgeon.display_name.ilike(f"%{q}%"), Surgeon.city.ilike(f"%{q}%"), Surgeon.region.ilike(f"%{q}%")))
    if country: stmt = stmt.where(or_(Surgeon.country_code == country.upper(), Surgeon.country_code == {"United States":"US","Canada":"CA","United Kingdom":"GB","Thailand":"TH"}.get(country)))
    records = db.scalars(stmt).all()
    result = [surgeon_summary(db, record) for record in records]
    if procedure: result = [x for x in result if any(p["slug"] == procedure or p["name"] == procedure for p in x["procedures"])]
    return {"items": result, "total": len(result)}


@router.get("/surgeons/{slug}")
def surgeon(slug: str, db: Session = Depends(get_db)):
    record = db.scalar(select(Surgeon).where(Surgeon.slug == slug, Surgeon.is_published.is_(True)))
    if not record: raise HTTPException(404, "Surgeon not found")
    return surgeon_detail(db, record)


@router.get("/surgeons/{slug}/reviews")
def surgeon_reviews(slug: str, db: Session = Depends(get_db)):
    record = db.scalar(select(Surgeon).where(Surgeon.slug == slug))
    if not record: raise HTTPException(404, "Surgeon not found")
    reviews = db.scalars(select(Review).where(Review.surgeon_id == record.id, Review.state == ModerationState.published).order_by(Review.published_at.desc())).all()
    return {"items": [review_data(db, review) for review in reviews], "total": len(reviews)}


@router.get("/reviews/{slug}")
def review(slug: str, db: Session = Depends(get_db)):
    record = db.scalar(select(Review).where(Review.slug == slug, Review.state == ModerationState.published))
    if not record: raise HTTPException(404, "Review not found")
    return review_data(db, record)


@router.post("/reviews", status_code=201)
def create_review(payload: ReviewCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    surgeon = db.scalar(select(Surgeon).where(Surgeon.slug == payload.surgeon_slug)); procedure = db.scalar(select(Procedure).where(Procedure.slug == payload.procedure_slug))
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
    surgeon = db.scalar(select(Surgeon).where(Surgeon.slug == slug));
    if not surgeon: raise HTTPException(404, "Surgeon not found")
    rows = db.scalars(select(SurgeonRevision).where(SurgeonRevision.surgeon_id == surgeon.id).order_by(SurgeonRevision.revision_number.desc())).all()
    return {"items": [{"revision_number": r.revision_number, "published_at": r.published_at, "editor": db.get(User,r.author_id).display_name if r.author_id and db.get(User,r.author_id) else "Deleted member", "summary": r.edit_summary, "change_type": r.change_type, "kind": r.kind} for r in rows]}


@router.get("/surgeons/{slug}/revisions/{number}")
def revision(slug: str, number: int, db: Session = Depends(get_db)):
    row = db.scalar(select(SurgeonRevision).join(Surgeon).where(Surgeon.slug == slug, SurgeonRevision.revision_number == number))
    if not row: raise HTTPException(404, "Revision not found")
    return {"revision_number": row.revision_number, "article_body": row.article_body, "profile": json.loads(row.snapshot_json), "summary": row.edit_summary, "change_type": row.change_type, "kind": row.kind, "published_at": row.published_at}


@router.post("/surgeons/{slug}/proposals", status_code=201)
def proposal(slug: str, payload: ProposalCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    surgeon = db.scalar(select(Surgeon).where(Surgeon.slug == slug));
    if not surgeon: raise HTTPException(404, "Surgeon not found")
    source = Source(url=str(payload.source_url), supports=payload.source_note, submitted_by_id=user.id); db.add(source); db.flush()
    profile = payload.profile.copy()
    profile["procedure_slugs"] = payload.procedure_slugs
    proposal = EditProposal(surgeon_id=surgeon.id, base_revision_id=surgeon.current_revision_id, author_id=user.id, proposed_article_body=payload.proposed_article_body, proposed_snapshot_json=json.dumps(profile), edit_summary=payload.edit_summary, state=ModerationState.pending, submitted_at=datetime.now(timezone.utc))
    db.add(proposal); db.flush(); db.add(ProposalSource(proposal_id=proposal.id, source_id=source.id)); db.commit(); return {"id": proposal.id, "state": proposal.state}


@router.get("/surgeons/{slug}/talk")
def talk(slug: str, db: Session = Depends(get_db)):
    surgeon = db.scalar(select(Surgeon).where(Surgeon.slug == slug));
    if not surgeon: raise HTTPException(404, "Surgeon not found")
    topics = db.scalars(select(TalkTopic).where(TalkTopic.surgeon_id == surgeon.id, TalkTopic.state == ModerationState.published).order_by(TalkTopic.created_at)).all()
    return {"items": [{"slug": t.slug, "title": t.title, "comments": [{"id": c.id, "author": db.get(User,c.author_id).display_name if c.author_id and db.get(User,c.author_id) else "Deleted member", "body": c.body, "created_at": c.created_at, "parent_comment_id": c.parent_comment_id} for c in db.scalars(select(TalkComment).where(TalkComment.topic_id == t.id, TalkComment.state == ModerationState.published).order_by(TalkComment.created_at)).all()]} for t in topics]}


@router.post("/surgeons/{slug}/talk", status_code=201)
def create_talk_topic(slug: str, payload: TalkPost, user: User = Depends(current_user), db: Session = Depends(get_db)):
    surgeon = db.scalar(select(Surgeon).where(Surgeon.slug == slug))
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
    return {"display_name": user.display_name, "bio": user.bio, "approximate_region": user.approximate_region, "allow_messages": user.allow_messages, "member_since": user.created_at.date()}


@router.post("/messages", status_code=201)
def send_message(payload: MessageCreate, sender: User = Depends(current_user), db: Session = Depends(get_db)):
    recipient = db.scalar(select(User).where(func.lower(User.display_name) == payload.recipient.lower()))
    if not recipient or not recipient.allow_messages: raise HTTPException(403, "This member is not accepting messages")
    conversation = Conversation(); db.add(conversation); db.flush()
    db.add_all([ConversationMember(conversation_id=conversation.id,user_id=sender.id), ConversationMember(conversation_id=conversation.id,user_id=recipient.id), Message(conversation_id=conversation.id,sender_id=sender.id,body=payload.body)])
    if recipient.email_message_notifications: db.add(EmailOutbox(recipient_user_id=recipient.id, template="new_message", payload_json=json.dumps({"conversation_id": str(conversation.id)})))
    db.commit(); return {"conversation_id": conversation.id}


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
    message = Message(conversation_id=conversation_id, sender_id=user.id, body=payload.body); db.add(message)
    recipients = db.scalars(select(User).join(ConversationMember, ConversationMember.user_id == User.id).where(ConversationMember.conversation_id == conversation_id, User.id != user.id, User.email_message_notifications.is_(True))).all()
    for recipient in recipients: db.add(EmailOutbox(recipient_user_id=recipient.id, template="new_message", payload_json=json.dumps({"conversation_id": str(conversation_id)})))
    db.commit()
    return {"id": message.id, "created_at": message.created_at}


@router.post("/reports", status_code=201)
def create_report(payload: ReportCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    try: target_id = uuid.UUID(payload.target_id)
    except ValueError: raise HTTPException(400, "Invalid target id")
    report = Report(reporter_id=user.id, target_type=payload.target_type, target_id=target_id, reason=payload.reason, details=payload.details)
    db.add(report); db.add(AuditEvent(actor_id=user.id, action="report.created", target_type=payload.target_type, target_id=target_id)); db.commit()
    return {"id": report.id, "state": report.state}


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


@router.post("/moderation/proposals/{proposal_id}/approve")
def approve_proposal(proposal_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.role not in {UserRole.trusted_editor, UserRole.moderator, UserRole.admin}: raise HTTPException(403, "Editor role required")
    proposal = db.get(EditProposal, proposal_id)
    if not proposal or proposal.state != ModerationState.pending: raise HTTPException(404, "Pending proposal not found")
    surgeon = db.get(Surgeon, proposal.surgeon_id)
    latest = db.scalar(select(func.max(SurgeonRevision.revision_number)).where(SurgeonRevision.surgeon_id == surgeon.id)) or 0
    revision = SurgeonRevision(surgeon_id=surgeon.id, revision_number=latest + 1, parent_revision_id=surgeon.current_revision_id, author_id=proposal.author_id, article_body=proposal.proposed_article_body, snapshot_json=proposal.proposed_snapshot_json, edit_summary=proposal.edit_summary, change_type="Article text", kind=RevisionKind.reviewed)
    db.add(revision); db.flush(); surgeon.current_revision_id = revision.id; proposal.state = ModerationState.published; proposal.decided_at = datetime.now(timezone.utc); proposal.decided_by_id = user.id
    snapshot = json.loads(proposal.proposed_snapshot_json)
    for key in ("specialty", "city", "region", "website_url"):
        if key in snapshot: setattr(surgeon, key, snapshot[key] or None)
    country = snapshot.get("country")
    if country:
        surgeon.country_code = {"United States": "US", "Canada": "CA", "United Kingdom": "GB", "Thailand": "TH"}.get(country, country.upper()[:2])
    procedure_slugs = snapshot.get("procedure_slugs")
    if procedure_slugs:
        selected = db.scalars(select(Procedure).where(Procedure.slug.in_(procedure_slugs))).all()
        if len(selected) != len(set(procedure_slugs)): raise HTTPException(400, "Proposal contains an unknown procedure")
        db.execute(delete(surgeon_procedures).where(surgeon_procedures.c.surgeon_id == surgeon.id))
        db.execute(surgeon_procedures.insert(), [{"surgeon_id": surgeon.id, "procedure_id": item.id} for item in selected])
    for link in db.scalars(select(ProposalSource).where(ProposalSource.proposal_id == proposal.id)).all(): db.add(RevisionSource(revision_id=revision.id, source_id=link.source_id))
    db.add(AuditEvent(actor_id=user.id, action="proposal.approved", target_type="edit_proposal", target_id=proposal.id, public_detail=proposal.edit_summary)); db.commit()
    return {"revision_number": revision.revision_number}
