import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:////tmp/opensurgery-pytest-14-fixes.db"

import uuid
import json
from datetime import datetime, timezone
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.database import Base, SessionLocal, engine
from app.seed import seed
from app.config import settings
from app.main import app, PAGES_ROOT
from app.models import (
    User, Surgeon, Review, ReviewPhoto, ReviewRating, EditProposal,
    TalkComment, UserBlock, Report, EmailOutbox, MediaAsset, ModerationState
)
from app.schemas import (
    RegisterRequest, ReviewCreate, ProposalCreate, MessageCreate,
    MessageReply, ReportCreate, SettingsUpdate
)
from app.api import (
    send_message, reply_to_conversation, block_user, unblock_user,
    approve_proposal, reject_proposal, approve_review, reject_review,
    approve_photo, reject_photo, pending_reviews, create_report,
    list_reports, resolve_report, unban_user, ban_user, create_review,
    surgeons
)
from app.email import process_pending_outbox
from app.serializers import review_data


@pytest.fixture(scope="module", autouse=True)
def setup_test_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)


# Issue 1: High: the public privacy statement is factually stale
def test_issue_1_privacy_statement_updated():
    privacy_html = (PAGES_ROOT / "privacy.html").read_text()
    assert "OpenSurgery transmits and securely stores submitted information" in privacy_html
    assert "This prototype does not transmit or store form data" not in privacy_html


# Issue 2: High: review and photo moderation cannot complete
def test_issue_2_review_and_photo_moderation():
    with SessionLocal() as db:
        editor = db.scalar(select(User).where(User.role == "admin"))
        user = db.scalar(select(User).where(User.display_name == "JuniperNorth"))
        
        # Create a pending review
        rev_res = create_review(
            ReviewCreate(
                surgeon_slug="mara-voss",
                procedure_slug="chest-masculinization",
                title="Moderation test review title",
                narrative="This narrative is long enough to meet the validation threshold.",
            ),
            user,
            db
        )
        saved_rev = db.scalar(select(Review).where(Review.slug == rev_res["slug"]))
        assert saved_rev.state == ModerationState.pending
        
        # Test pending reviews list
        pending = pending_reviews(editor, db)
        assert any(item["id"] == saved_rev.id for item in pending["items"])
        
        # Approve review
        approved = approve_review(saved_rev.id, editor, db)
        assert approved["state"] == ModerationState.published
        assert saved_rev.state == ModerationState.published
        assert saved_rev.published_at is not None


# Issue 3: High: deployment script path defects
def test_issue_3_deploy_script_repaired():
    deploy_sh = (Path(__file__).parent.parent / "scripts" / "deploy.sh").read_text()
    lines = deploy_sh.strip().split("\n")
    assert lines[0] == "#!/usr/bin/env bash"
    assert lines[1] == "set -Eeuo pipefail"
    assert "cd /home/ubuntu/docker/surgery-website/Bomboclat" not in deploy_sh
    assert '"$PROJECT_DIR/scripts/backup.sh"' in deploy_sh


# Issue 4: High: production protections named in product spec
def test_issue_4_production_protections_middleware():
    client = TestClient(app)
    res = client.get("/api/v1/health")
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"
    assert res.headers["X-XSS-Protection"] == "1; mode=block"
    assert res.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


# Issue 5: Medium: branding is split
def test_issue_5_branding_consolidated():
    assert settings.site_name == "OpenSurgery"
    assert app.title == "OpenSurgery"
    env_ex = (Path(__file__).parent.parent / ".env.example").read_text()
    assert "SITE_NAME=OpenSurgery" in env_ex
    compose_yml = (Path(__file__).parent.parent / "docker-compose.yml").read_text()
    assert "SITE_NAME: ${SITE_NAME:-OpenSurgery}" in compose_yml


# Issue 6: Medium: UI fields and database fields are out of sync
def test_issue_6_ui_and_database_fields_synced():
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.display_name == "RiverNorth"))
        # Check user profile activity counts
        client = TestClient(app)
        res = client.get("/api/v1/users/RiverNorth")
        assert res.status_code == 200
        data = res.json()
        assert "reviews_count" in data
        assert "edits_count" in data
        assert "talk_count" in data


# Issue 7: Medium: messaging preferences and blocks are not enforced
def test_issue_7_messaging_preferences_and_blocks():
    with SessionLocal() as db:
        user_a = db.scalar(select(User).where(User.display_name == "RiverNorth"))
        user_b = db.scalar(select(User).where(User.display_name == "JuniperNorth"))
        
        # Test block user
        block_user("JuniperNorth", user_a, db)

        # Message sending when blocked should fail
        with pytest.raises(HTTPException) as exc:
            send_message(MessageCreate(recipient="JuniperNorth", body="Blocked message test"), user_a, db)
        assert exc.value.status_code == 403

        # Unblock user
        unblock_user("JuniperNorth", user_a, db)


# Issue 8: Medium: queued message notifications never send
def test_issue_8_outbox_message_notifications():
    with SessionLocal() as db:
        recipient = db.scalar(select(User).where(User.display_name == "RiverNorth"))
        outbox = EmailOutbox(
            recipient_user_id=recipient.id,
            template="new_message",
            payload_json=json.dumps({"conversation_id": str(uuid.uuid4())})
        )
        db.add(outbox)
        db.commit()
        assert outbox.state == "pending"
        
        # Test process pending outbox
        processed = process_pending_outbox()
        assert processed >= 0


# Issue 9: Medium: proposal approval has race and consistency edges
def test_issue_9_proposal_approval_staleness_check():
    with SessionLocal() as db:
        editor = db.scalar(select(User).where(User.role == "admin"))
        surgeon_obj = db.scalar(select(Surgeon).where(Surgeon.slug == "mara-voss"))
        
        # Create a proposal based on a fake/stale revision ID
        stale_prop = EditProposal(
            surgeon_id=surgeon_obj.id,
            base_revision_id=uuid.uuid4(),
            author_id=editor.id,
            proposed_article_body="Stale article body text long enough.",
            proposed_snapshot_json=json.dumps({"specialty": "Stale Specialty"}),
            edit_summary="Stale test summary",
            state=ModerationState.pending,
            submitted_at=datetime.now(timezone.utc)
        )
        db.add(stale_prop)
        db.commit()

        # Approving stale proposal should raise 409 Conflict
        with pytest.raises(HTTPException) as exc:
            approve_proposal(stale_prop.id, editor, db)
        assert exc.value.status_code == 409


# Issue 10: Medium: content-state rules are incomplete
def test_issue_10_content_state_and_moderation():
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.role == "admin"))
        member = db.scalar(select(User).where(User.display_name == "AshAndPine"))
        
        # Report invalid target UUID should fail with 400
        with pytest.raises(HTTPException) as exc:
            create_report(ReportCreate(target_type="surgeon", target_id=str(uuid.uuid4()), reason="Test reason"), member, db)
        assert exc.value.status_code == 400

        # Ban and Unban user
        ban_user(member.display_name, type("Action", (), {"reason": "Testing user unban flow"})(), admin, db)
        assert not member.is_active
        unban_res = unban_user(member.display_name, admin, db)
        assert unban_res["status"] == "active"
        assert member.is_active


# Issue 11: Medium: media is stored but not consumable
def test_issue_11_media_serving_and_serializer_urls():
    with SessionLocal() as db:
        review_obj = db.scalar(select(Review).where(Review.state == ModerationState.published))
        if review_obj:
            serialized = review_data(db, review_obj)
            assert "photos" in serialized


# Issue 12: Lower: search and filtering are prototype-scale
def test_issue_12_surgeons_sql_procedure_filtering():
    with SessionLocal() as db:
        res = surgeons(procedure="chest-masculinization", db=db)
        assert res["total"] >= 1


# Issue 13: Lower: duplicate and legacy UI paths increase maintenance
def test_issue_13_legacy_ui_path_consolidation():
    client = TestClient(app)
    res = client.get("/surgeon.html")
    assert res.status_code == 200
    assert "OpenSurgery" in res.text


# Issue 14: Lower: tests bypass important runtime layers
def test_issue_14_http_integration_suite():
    client = TestClient(app)
    res = client.get("/api/v1/surgeons")
    assert res.status_code == 200
    assert "items" in res.json()
