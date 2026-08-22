from datetime import date
from decimal import Decimal
import uuid

from pydantic import BaseModel, EmailStr, Field, HttpUrl


class RegisterRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9_-]+$")
    password: str = Field(min_length=8, max_length=128)
    approximate_region: str | None = Field(default=None, max_length=160)


class LoginRequest(BaseModel):
    identity: str = Field(min_length=3, max_length=320)
    password: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=32, max_length=300)
    password: str = Field(min_length=8, max_length=128)


class ReviewCreate(BaseModel):
    surgeon_slug: str
    procedure_slug: str
    technique_slug: str | None = None
    title: str = Field(min_length=3, max_length=160)
    surgery_date: date | None = None
    surgery_date_precision: str = "month"
    location_country_code: str | None = Field(default=None, min_length=2, max_length=2)
    location_text: str | None = Field(default=None, max_length=240)
    cost_amount: Decimal | None = Field(default=None, ge=0)
    cost_currency: str | None = Field(default=None, min_length=3, max_length=3)
    cost_includes: str | None = None
    narrative: str = Field(min_length=20, max_length=30000)
    complications_status: str = "prefer_not_to_say"
    complications_detail: str | None = None
    revision_detail: str | None = None
    ratings: dict[str, int] = Field(default_factory=dict)
    media_ids: list[uuid.UUID] = Field(default_factory=list, max_length=10)
    designated_long_term_media_id: uuid.UUID | None = None


class ProposalCreate(BaseModel):
    proposed_article_body: str = Field(min_length=20, max_length=100000)
    edit_summary: str = Field(min_length=5, max_length=500)
    change_type: str = Field(default="Article text", max_length=80)
    source_url: HttpUrl | None = None
    source_note: str | None = Field(default=None, max_length=2000)
    profile: dict = Field(default_factory=dict)
    procedure_slugs: list[str] = Field(default_factory=list)


class SurgeonCreate(BaseModel):
    display_name: str = Field(min_length=3, max_length=240)
    aliases: str | None = Field(default=None, max_length=1000)
    specialty: str = Field(min_length=3, max_length=240)
    city: str = Field(min_length=2, max_length=120)
    region: str | None = Field(default=None, max_length=120)
    country_code: str = Field(min_length=2, max_length=2, pattern=r"^[A-Za-z]{2}$")
    website_url: HttpUrl | None = None
    practice_name: str | None = Field(default=None, max_length=240)
    article_body: str = Field(min_length=20, max_length=100000)
    procedure_slugs: list[str] = Field(min_length=1, max_length=20)
    source_url: HttpUrl
    source_note: str = Field(min_length=5, max_length=2000)


class SurgeonRemoval(BaseModel):
    reason: str = Field(min_length=10, max_length=2000)
    status: str = Field(default="removed", pattern=r"^(removed|retired)$")


class AdminAction(BaseModel):
    reason: str = Field(min_length=10, max_length=2000)


class AdminRoleUpdate(BaseModel):
    role: str = Field(pattern=r"^(member|trusted_editor|moderator|admin)$")


class MessageCreate(BaseModel):
    recipient: str = Field(min_length=3, max_length=30)
    body: str = Field(min_length=1, max_length=10000)


class MessageReply(BaseModel):
    body: str = Field(min_length=1, max_length=10000)


class SettingsUpdate(BaseModel):
    bio: str | None = Field(default=None, max_length=3000)
    approximate_region: str | None = Field(default=None, max_length=160)
    allow_messages: bool | None = None
    allow_new_accounts: bool | None = None
    email_message_notifications: bool | None = None
    email_watch_notifications: bool | None = None


class TalkPost(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    body: str = Field(min_length=1, max_length=30000)


class ReportCreate(BaseModel):
    target_type: str = Field(pattern=r"^(surgeon|review|user|talk_comment)$")
    target_id: str
    reason: str = Field(min_length=3, max_length=120)
    details: str | None = Field(default=None, max_length=10000)
