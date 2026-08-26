import enum
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Table, Text, UniqueConstraint, Uuid, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


class ModerationState(str, enum.Enum):
    draft = "draft"
    pending = "pending"
    published = "published"
    rejected = "rejected"
    hidden = "hidden"


class RevisionKind(str, enum.Enum):
    normal = "normal"
    reviewed = "reviewed"
    rollback = "rollback"


class Visibility(str, enum.Enum):
    public = "public"
    members = "members"
    private = "private"


class UserRole(str, enum.Enum):
    member = "member"
    trusted_editor = "trusted_editor"
    moderator = "moderator"
    admin = "admin"


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    session_version: Mapped[int] = mapped_column(Integer, default=0)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.member)
    bio: Mapped[str | None] = mapped_column(Text)
    approximate_region: Mapped[str | None] = mapped_column(String(160))
    allow_messages: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_new_accounts: Mapped[bool] = mapped_column(Boolean, default=False)
    email_message_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    email_watch_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    banned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    banned_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    ban_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Practice(Base):
    __tablename__ = "practices"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(240), index=True)
    website_url: Mapped[str | None] = mapped_column(String(2048))
    public_email: Mapped[str | None] = mapped_column(String(320))
    public_phone: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Location(Base):
    __tablename__ = "locations"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("practices.id", ondelete="CASCADE"), index=True)
    label: Mapped[str | None] = mapped_column(String(160))
    city: Mapped[str] = mapped_column(String(120))
    region: Mapped[str | None] = mapped_column(String(120))
    country_code: Mapped[str] = mapped_column(String(2), index=True)
    address: Mapped[str | None] = mapped_column(Text)
    accessibility: Mapped[str | None] = mapped_column(Text)
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)


class Surgeon(Base):
    __tablename__ = "surgeons"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(240), index=True)
    specialty: Mapped[str | None] = mapped_column(String(240))
    country_code: Mapped[str] = mapped_column(String(2), index=True)
    region: Mapped[str | None] = mapped_column(String(120))
    city: Mapped[str | None] = mapped_column(String(120))
    website_url: Mapped[str | None] = mapped_column(String(2048))
    public_contact: Mapped[str | None] = mapped_column(Text)
    portrait_media_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("media_assets.id", name="fk_surgeons_portrait_media", use_alter=True, ondelete="SET NULL"))
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    lifecycle_status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    submitted_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    removed_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    removal_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    current_revision_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("surgeon_revisions.id", name="fk_surgeons_current_revision", use_alter=True, ondelete="SET NULL"))
    revisions: Mapped[list["SurgeonRevision"]] = relationship(back_populates="surgeon", foreign_keys="SurgeonRevision.surgeon_id")


class SurgeonPractice(Base):
    __tablename__ = "surgeon_practices"
    surgeon_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("surgeons.id", ondelete="CASCADE"), primary_key=True)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id", ondelete="CASCADE"), primary_key=True)
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)


class Procedure(Base):
    __tablename__ = "procedures"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    name: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[str] = mapped_column(Text)
    aliases: Mapped[str | None] = mapped_column(Text)


class Technique(Base):
    __tablename__ = "techniques"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    procedure_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("procedures.id", ondelete="CASCADE"), index=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    aliases: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("procedure_id", "name"),)


surgeon_procedures = Table(
    "surgeon_procedures", Base.metadata,
    Column("surgeon_id", Uuid, ForeignKey("surgeons.id", ondelete="CASCADE"), primary_key=True),
    Column("procedure_id", Uuid, ForeignKey("procedures.id", ondelete="CASCADE"), primary_key=True),
    Column("effective_from", Date), Column("effective_to", Date), Column("citation_id", Uuid, ForeignKey("sources.id", ondelete="SET NULL")),
)


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    url: Mapped[str] = mapped_column(String(2048))
    title: Mapped[str | None] = mapped_column(String(500))
    publisher: Mapped[str | None] = mapped_column(String(240))
    archived_url: Mapped[str | None] = mapped_column(String(2048))
    accessed_on: Mapped[date | None] = mapped_column(Date)
    supports: Mapped[str | None] = mapped_column(Text)
    submitted_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class SurgeonRevision(Base):
    __tablename__ = "surgeon_revisions"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    surgeon_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("surgeons.id", ondelete="CASCADE"), index=True)
    revision_number: Mapped[int] = mapped_column(Integer)
    parent_revision_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("surgeon_revisions.id", ondelete="SET NULL"))
    author_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    article_body: Mapped[str] = mapped_column(Text)
    snapshot_json: Mapped[str] = mapped_column(Text)
    edit_summary: Mapped[str] = mapped_column(String(500))
    change_type: Mapped[str] = mapped_column(String(80), index=True)
    kind: Mapped[RevisionKind] = mapped_column(Enum(RevisionKind), default=RevisionKind.normal)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    surgeon: Mapped[Surgeon] = relationship(back_populates="revisions", foreign_keys=[surgeon_id])
    __table_args__ = (UniqueConstraint("surgeon_id", "revision_number"),)


class RevisionSource(Base):
    __tablename__ = "revision_sources"
    revision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("surgeon_revisions.id", ondelete="CASCADE"), primary_key=True)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), primary_key=True)


class EditProposal(Base):
    __tablename__ = "edit_proposals"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    surgeon_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("surgeons.id", ondelete="CASCADE"), index=True)
    base_revision_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("surgeon_revisions.id", ondelete="SET NULL"))
    author_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    proposed_article_body: Mapped[str] = mapped_column(Text)
    proposed_snapshot_json: Mapped[str] = mapped_column(Text)
    edit_summary: Mapped[str] = mapped_column(String(500))
    state: Mapped[ModerationState] = mapped_column(Enum(ModerationState), default=ModerationState.draft, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class ProposalSource(Base):
    __tablename__ = "proposal_sources"
    proposal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("edit_proposals.id", ondelete="CASCADE"), primary_key=True)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), primary_key=True)


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    surgeon_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("surgeons.id", ondelete="RESTRICT"), index=True)
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    procedure_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("procedures.id", ondelete="RESTRICT"), index=True)
    technique_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("techniques.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(160))
    surgery_date: Mapped[date | None] = mapped_column(Date)
    surgery_date_precision: Mapped[str] = mapped_column(String(12), default="month")
    location_country_code: Mapped[str | None] = mapped_column(String(2))
    location_text: Mapped[str | None] = mapped_column(String(240))
    cost_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    cost_currency: Mapped[str | None] = mapped_column(String(3))
    cost_includes: Mapped[str | None] = mapped_column(Text)
    wait_time_days: Mapped[int | None] = mapped_column(Integer)
    narrative: Mapped[str] = mapped_column(Text)
    complications_status: Mapped[str] = mapped_column(String(40), default="prefer_not_to_say")
    complications_detail: Mapped[str | None] = mapped_column(Text)
    revision_detail: Mapped[str | None] = mapped_column(Text)
    state: Mapped[ModerationState] = mapped_column(Enum(ModerationState), default=ModerationState.pending, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class RatingDimension(Base):
    __tablename__ = "rating_dimensions"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    label: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ReviewRating(Base):
    __tablename__ = "review_ratings"
    review_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"), primary_key=True)
    dimension_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rating_dimensions.id", ondelete="RESTRICT"), primary_key=True)
    value: Mapped[int] = mapped_column(Integer)


class MediaAsset(Base):
    __tablename__ = "media_assets"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    safe_storage_key: Mapped[str | None] = mapped_column(String(500), unique=True)
    media_type: Mapped[str] = mapped_column(String(100))
    byte_size: Mapped[int] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    processing_state: Mapped[str] = mapped_column(String(40), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ReviewPhoto(Base):
    __tablename__ = "review_photos"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    review_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"), index=True)
    media_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("media_assets.id", ondelete="RESTRICT"), unique=True)
    capture_date: Mapped[date | None] = mapped_column(Date)
    capture_date_precision: Mapped[str] = mapped_column(String(12), default="unknown")
    caption: Mapped[str | None] = mapped_column(String(500))
    visibility: Mapped[Visibility] = mapped_column(Enum(Visibility), default=Visibility.members)
    content_warning: Mapped[str | None] = mapped_column(String(240))
    designated_long_term: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TalkTopic(Base):
    __tablename__ = "talk_topics"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    surgeon_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("surgeons.id", ondelete="CASCADE"), index=True)
    slug: Mapped[str] = mapped_column(String(140))
    title: Mapped[str] = mapped_column(String(240))
    author_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    state: Mapped[ModerationState] = mapped_column(Enum(ModerationState), default=ModerationState.published)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (UniqueConstraint("surgeon_id", "slug"),)


class TalkComment(Base):
    __tablename__ = "talk_comments"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("talk_topics.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    parent_comment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("talk_comments.id", ondelete="SET NULL"))
    body: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    state: Mapped[ModerationState] = mapped_column(Enum(ModerationState), default=ModerationState.published)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ConversationMember(Base):
    __tablename__ = "conversation_members"
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    sender_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserBlock(Base):
    __tablename__ = "user_blocks"
    blocker_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    blocked_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AccountToken(Base):
    __tablename__ = "account_tokens"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(40), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EmailOutbox(Base):
    __tablename__ = "email_outbox"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    recipient_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    template: Mapped[str] = mapped_column(String(80), index=True)
    payload_json: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    reporter_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    target_type: Mapped[str] = mapped_column(String(50), index=True)
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    reason: Mapped[str] = mapped_column(String(120))
    details: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(40), default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    target_type: Mapped[str] = mapped_column(String(50))
    target_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    public_detail: Mapped[str | None] = mapped_column(Text)
    private_detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


Index("ix_reviews_surgeon_state_published", Review.surgeon_id, Review.state, Review.published_at)
Index("ix_revisions_surgeon_published", SurgeonRevision.surgeon_id, SurgeonRevision.published_at)
