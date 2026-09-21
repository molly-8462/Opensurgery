import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:////tmp/opensurgery-pytest.db"

from sqlalchemy import func, select
from fastapi import BackgroundTasks, Response

import json
from urllib.parse import parse_qs, urlparse
import pytest
from fastapi import HTTPException

from app.api import (admin_user, approve_proposal, approve_surgeon, ban_user, confirm_password_reset, conversation_messages, countries,
                     create_review, create_surgeon, create_talk_topic, history, login,
                     pending_surgeons, procedures, profile, proposal, remove_surgeon,
                     remove_review, reply_to_conversation, request_password_reset, restore_surgeon, send_message,
                     surgeon, surgeon_reviews, surgeons, update_me, update_user_role)
from app.database import Base, SessionLocal, engine
from app.models import AccountToken, AuditEvent, EmailOutbox, MediaAsset, ModerationState, ProposalSource, Review, ReviewPhoto, ReviewRating, Surgeon, SurgeonRevision, User, UserRole
from app.schemas import (AdminAction, AdminRoleUpdate, LoginRequest, MessageCreate, MessageReply, PasswordResetConfirm,
                         PasswordResetRequest, ProposalCreate, RegisterRequest, ReviewCreate, SettingsUpdate,
                         SurgeonCreate, SurgeonRemoval, TalkPost)
from app.seed import seed
from app.security import create_token, current_user, verify_password
from app.config import settings
from app.main import ASSETS_ROOT, PAGES_ROOT, PUBLIC_PAGES, app, surgeon_profile_page, surgeon_section_page


def setup_module():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)


def test_seeded_relations_and_public_queries():
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Surgeon)) == 4
        assert db.scalar(select(func.count()).select_from(Review)) == 1
        assert db.scalar(select(func.count()).select_from(SurgeonRevision)) == 9
        assert surgeons(db=db)["total"] == 4
        detail = surgeon("mara-voss", db)
        assert detail["profile"]["practice"] == "Northbank Reconstructive Center"
        review_result = surgeon_reviews("mara-voss", db)
        assert review_result["total"] == 1
        assert len(review_result["items"][0]["ratings"]) == 3
        assert review_result["items"][0]["long_term_status"] == "Missing 1-year update"
        assert len(history("mara-voss", db)["items"]) == 6
        assert len(procedures(db)["items"]) == 7
        assert db.scalar(select(func.count()).select_from(ReviewRating)) == 3


def test_backend_branding_comes_from_the_site_name_setting():
    assert settings.site_name == "OpenSurgery"
    assert app.title == settings.site_name


def test_surgeon_pages_hide_seed_content_until_hydrated_and_never_default_to_mara():
    script = (ASSETS_ROOT / "js" / "script.js").read_text()
    for filename in ("index.html", "reviews.html", "talk.html", "edit.html", "history.html", "revision.html"):
        page = (PAGES_ROOT / filename).read_text()
        assert 'data-surgeon-shell aria-busy="true"' in page
        assert "profile-load-status" in page
    assert '|| "mara-voss"' not in script
    assert "const selectedSurgeonSlug = () =>" in script
    assert "const finishSurgeonLoad = (error) =>" in script


def test_clean_surgeon_routes_serve_the_correct_page_shells():
    assert str(surgeon_profile_page("adrian-lee").path).endswith("index.html")
    assert str(surgeon_section_page("adrian-lee", "reviews").path).endswith("reviews.html")
    with pytest.raises(HTTPException) as missing:
        surgeon_section_page("adrian-lee", "unknown")
    assert missing.value.status_code == 404
    assert "reset-password.html" in PUBLIC_PAGES


def test_backend_owns_shared_eight_character_password_policy():
    from pydantic import ValidationError
    for schema, fields in (
        (RegisterRequest, {"email": "member@example.com", "display_name": "Member", "password": "short"}),
        (PasswordResetConfirm, {"token": "x" * 32, "password": "short"}),
    ):
        with pytest.raises(ValidationError):
            schema(**fields)


def test_pre_session_version_tokens_survive_migration_until_password_reset():
    import jwt
    from datetime import datetime, timedelta, timezone
    from fastapi.security import HTTPAuthorizationCredentials
    from app.config import settings

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "river@example.com"))
        legacy_token = jwt.encode(
            {"sub": str(user.id), "role": user.role.value, "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
            settings.secret_key,
            algorithm="HS256",
        )
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=legacy_token)
        assert current_user(type("Request", (), {"cookies": {}})(), credentials, db).id == user.id


def test_user_password_and_profile_privacy_boundary():
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.display_name == "RiverNorth"))
        assert verify_password("prototype-password", user.password_hash)
        assert create_token(user)
        response = Response()
        login(LoginRequest(identity="RiverNorth", password="prototype-password"), response, db)
        assert "HttpOnly" in response.headers["set-cookie"]
        public = profile("RiverNorth", db)
        assert public["display_name"] == "RiverNorth"
        assert "email" not in public
        assert "password_hash" not in public


def test_password_reset_uses_hashed_single_use_token_and_outbox():
    with SessionLocal() as db:
        request_password_reset(PasswordResetRequest(email="river@example.com"), BackgroundTasks(), db)
        queued = db.scalar(select(EmailOutbox).where(EmailOutbox.template == "password_reset"))
        reset_url = json.loads(queued.payload_json)["reset_url"]
        raw_token = parse_qs(urlparse(reset_url).fragment)["token"][0]
        stored_token = db.scalar(select(AccountToken).where(AccountToken.user_id == queued.recipient_user_id))
        assert raw_token not in stored_token.token_hash
        user = db.scalar(select(User).where(User.email == "river@example.com"))
        old_session = create_token(user)
        confirm_password_reset(PasswordResetConfirm(token=raw_token, password="new-prototype-password"), db)
        assert verify_password("new-prototype-password", user.password_hash)
        with pytest.raises(HTTPException) as reused:
            confirm_password_reset(PasswordResetConfirm(token=raw_token, password="another-password"), db)
        assert reused.value.status_code == 400
        from fastapi.security import HTTPAuthorizationCredentials
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=old_session)
        with pytest.raises(HTTPException) as revoked:
            current_user(type("Request", (), {"cookies": {}})(), credentials, db)
        assert revoked.value.status_code == 401


def test_password_reset_sends_smtp_message(monkeypatch):
    import app.email as email_service

    sent = []

    class FakeSmtp:
        def __init__(self, host, port, timeout):
            assert (host, port, timeout) == ("smtp.example.test", 587, 10)
        def __enter__(self): return self
        def __exit__(self, *_): return None
        def starttls(self): pass
        def login(self, username, password): assert (username, password) == ("smtp-user", "smtp-password")
        def send_message(self, message): sent.append(message)

    monkeypatch.setattr(email_service.settings, "smtp_host", "smtp.example.test")
    monkeypatch.setattr(email_service.settings, "smtp_username", "smtp-user")
    monkeypatch.setattr(email_service.settings, "smtp_password", "smtp-password")
    monkeypatch.setattr(email_service.smtplib, "SMTP", FakeSmtp)
    with SessionLocal() as db:
        tasks = BackgroundTasks()
        request_password_reset(PasswordResetRequest(email="juniper@example.com"), tasks, db)
        outbox = db.scalar(select(EmailOutbox).join(User).where(User.email == "juniper@example.com", EmailOutbox.template == "password_reset"))
        assert len(tasks.tasks) == 1
        email_service.deliver_password_reset(db, outbox.id)
        assert outbox.state == "sent"
        assert json.loads(outbox.payload_json) == {"delivered": True}
    assert sent[0]["To"] == "juniper@example.com"
    assert settings.site_name in sent[0]["Subject"]
    assert settings.site_name in sent[0].get_content()
    assert "/reset-password.html#token=" in sent[0].get_content()
    assert sent[0]["Resend-Idempotency-Key"].startswith("password-reset/")


def test_authenticated_browser_write_flows_persist_and_read_back():
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.display_name == "JuniperNorth"))
        settings_response = update_me(SettingsUpdate(bio="Updated through the browser API.", allow_messages=True), user, db)
        assert settings_response["bio"] == "Updated through the browser API."
        media = MediaAsset(owner_id=user.id, storage_key="test/review.webp", safe_storage_key="test/review.webp",
                           media_type="image/webp", byte_size=100, width=10, height=10,
                           sha256="0" * 64, processing_state="ready")
        db.add(media); db.flush()
        review_response = create_review(ReviewCreate(
            surgeon_slug="mara-voss", procedure_slug="chest-masculinization",
            technique_slug="double-incision", title="A persisted integration review",
            narrative="This narrative is long enough to pass validation and prove persistence.",
            ratings={"communication": 5}, media_ids=[media.id],
            designated_long_term_media_id=media.id), user, db)
        saved_review = db.scalar(select(Review).where(Review.slug == review_response["slug"]))
        assert saved_review is not None
        assert db.scalar(select(func.count()).select_from(ReviewRating).where(ReviewRating.review_id == saved_review.id)) == 1
        assert db.scalar(select(ReviewPhoto).where(ReviewPhoto.review_id == saved_review.id)).designated_long_term
        topic_response = create_talk_topic("mara-voss", TalkPost(title="Integration topic", body="Persist this discussion."), user, db)
        assert topic_response["slug"]
        message_response = send_message(MessageCreate(recipient="RiverNorth", body="Persist this private message."), user, db)
        conversation_id = message_response["conversation_id"]
        reply_to_conversation(conversation_id, MessageReply(body="And this reply."), user, db)
        assert len(conversation_messages(conversation_id, user, db)["items"]) >= 2


def test_proposal_approval_updates_revision_and_structured_profile():
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.display_name == "JuniperNorth"))
        proposal_response = proposal("mara-voss", ProposalCreate(
            proposed_article_body="A complete replacement article body that is long enough.",
            edit_summary="Integration-tested structured update", source_url="https://example.com/source",
            source_note="Supports the integration test update.",
            profile={"city": "Salem", "region": "Oregon", "country": "United States", "specialty": "Reconstructive surgeon"},
            procedure_slugs=["chest-revision"]), user, db)
        approval = approve_proposal(proposal_response["id"], user, db)
        assert approval["revision_number"] > 124
        detail = surgeon("mara-voss", db)
        assert detail["city"] == "Salem"
        assert detail["specialty"] == "Reconstructive surgeon"
        assert detail["article_body"].startswith("A complete replacement")
        assert [item["slug"] for item in detail["procedures"]] == ["chest-revision"]


def test_edit_proposal_can_be_submitted_without_a_source():
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.display_name == "RiverNorth"))
        result = proposal("adrian-lee", ProposalCreate(
            proposed_article_body="A complete source-free edit based on accurate community knowledge.",
            edit_summary="Update information reported by the community",
            profile={"city": "San Francisco"}, procedure_slugs=["facial-feminization"]
        ), user, db)
        assert result["state"] == ModerationState.pending
        assert db.scalar(select(func.count()).select_from(ProposalSource).where(
            ProposalSource.proposal_id == result["id"]
        )) == 0


def test_static_frontend_and_api_contracts_are_served_together():
    assert "home.html" in PUBLIC_PAGES
    assert (PAGES_ROOT / "directory.html").is_file()
    assert (ASSETS_ROOT / "css" / "styles.css").is_file()
    assert (ASSETS_ROOT / "js" / "script.js").is_file()
    assert (ASSETS_ROOT / "data" / "history-export.json").is_file()
    with SessionLocal() as db:
        chest = next(item for item in procedures(db)["items"] if item["slug"] == "chest-masculinization")
        assert {item["slug"] for item in chest["techniques"]} == {"double-incision", "periareolar", "buttonhole"}


def test_add_surgeon_uses_complete_countries_and_checkbox_procedures_without_aliases():
    page = (PAGES_ROOT / "add-surgeon.html").read_text()
    script = (ASSETS_ROOT / "js" / "script.js").read_text()
    country_items = countries()["items"]
    assert len(country_items) >= 240
    assert {"US", "CA", "GB", "TH", "DE", "ZA", "JP"} <= {item["code"] for item in country_items}
    assert 'name="aliases"' not in page
    assert 'name="country_name"' in page and 'id="country-options"' in page
    assert "data-procedure-checklist" in page
    assert 'script.js?v=20260824.1' in page
    assert 'type="checkbox" name="procedure_slugs"' in script
    assert "aliases: data.get" not in script


def test_new_surgeon_moderation_removal_and_restoration_lifecycle():
    with SessionLocal() as db:
        member = db.scalar(select(User).where(User.display_name == "RiverNorth"))
        editor = db.scalar(select(User).where(User.display_name == "JuniperNorth"))
        created = create_surgeon(SurgeonCreate(
            display_name="Taylor Example", specialty="Reconstructive surgeon", city="Seattle",
            region="Washington", country_code="US", practice_name="Example Practice",
            article_body="Taylor Example is a fictional lifecycle test record with a public source.",
            procedure_slugs=["chest-revision"], source_url="https://example.com/taylor",
            source_note="Supports the identity and listed procedure."), member, db)
        assert created["status"] == "pending"
        assert all(item["slug"] != created["slug"] for item in surgeons(db=db)["items"])
        assert any(item["id"] == created["id"] for item in pending_surgeons(editor, db)["items"])
        with pytest.raises(HTTPException) as denied:
            approve_surgeon(created["id"], member, db)
        assert denied.value.status_code == 403

        approved = approve_surgeon(created["id"], editor, db)
        assert approved["status"] == "published"
        assert surgeon(created["slug"], db)["name"] == "Taylor Example"

        removed = remove_surgeon(created["slug"], SurgeonRemoval(
            reason="Confirmed fictional vandalism test record.", status="removed"), editor, db)
        assert removed["status"] == "removed"
        assert all(item["slug"] != created["slug"] for item in surgeons(db=db)["items"])
        with pytest.raises(HTTPException) as hidden:
            surgeon(created["slug"], db)
        assert hidden.value.status_code == 404

        restored = restore_surgeon(created["slug"], editor, db)
        assert restored["status"] == "published"
        assert surgeon(created["slug"], db)["name"] == "Taylor Example"


def test_admin_user_review_and_surgeon_controls_are_server_authorized_and_audited():
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.display_name == "JuniperNorth"))
        member = db.scalar(select(User).where(User.display_name == "RiverNorth"))
        promotee = db.scalar(select(User).where(User.display_name == "AshAndPine"))
        banned = db.scalar(select(User).where(User.display_name == "CedarKeys"))
        review = db.scalar(select(Review).where(Review.state == ModerationState.published))

        assert admin.role == UserRole.admin
        with pytest.raises(HTTPException) as denied:
            update_user_role(promotee.display_name, AdminRoleUpdate(role="admin"), member, db)
        assert denied.value.status_code == 403

        assert update_user_role(promotee.display_name, AdminRoleUpdate(role="admin"), admin, db)["role"] == UserRole.admin
        assert admin_user(promotee.display_name, admin, db)["role"] == UserRole.admin

        with pytest.raises(HTTPException) as self_ban:
            ban_user(admin.display_name, AdminAction(reason="Attempted self-ban for regression coverage."), admin, db)
        assert self_ban.value.status_code == 409
        assert ban_user(banned.display_name, AdminAction(reason="Repeated abuse confirmed by moderation review."), admin, db)["status"] == "banned"
        assert not banned.is_active and banned.banned_by_id == admin.id and banned.banned_at
        with pytest.raises(HTTPException) as banned_login:
            login(LoginRequest(identity=banned.display_name, password="prototype-password"), Response(), db)
        assert banned_login.value.status_code == 401

        with pytest.raises(HTTPException) as member_delete:
            remove_review(review.slug, AdminAction(reason="Unauthorized deletion attempt for testing."), member, db)
        assert member_delete.value.status_code == 403
        assert remove_review(review.slug, AdminAction(reason="Review violates the published community policy."), admin, db)["status"] == "removed"
        assert review.state == ModerationState.hidden
        assert db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action.in_([
            "user.role_changed", "user.banned", "review.removed"
        ]))) >= 3


def test_admin_controls_are_created_only_after_server_role_confirmation():
    script = (ASSETS_ROOT / "js" / "script.js").read_text()
    for page in ("profile.html", "review.html", "index.html"):
        assert "data-admin-user-controls" not in (PAGES_ROOT / page).read_text()
    assert 'viewer.role !== "admin"' in script
    assert 'user.role !== "admin"' in script
    assert "/admin/users/" in script and "/admin/reviews/" in script


def test_http_integration_routing_and_security_headers():
    from fastapi.testclient import TestClient
    client = TestClient(app)

    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}

    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"
    assert res.headers["X-XSS-Protection"] == "1; mode=block"
    assert res.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    page_res = client.get("/")
    assert page_res.status_code == 200
    assert "OpenSurgery" in page_res.text

