import json
from datetime import date
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .countries import COUNTRY_NAMES
from .models import (ModerationState, Procedure, RatingDimension, Review, ReviewPhoto, ReviewRating,
                     Surgeon, SurgeonRevision, Technique, User)


def surgeon_summary(db: Session, surgeon: Surgeon) -> dict:
    review_count = db.scalar(select(func.count()).select_from(Review).where(Review.surgeon_id == surgeon.id, Review.state == ModerationState.published)) or 0
    procedures = db.execute(
        select(Procedure).join_from(Procedure, Procedure.__table__.metadata.tables["surgeon_procedures"]).where(
            Procedure.__table__.metadata.tables["surgeon_procedures"].c.surgeon_id == surgeon.id
        )
    ).scalars().all()
    return {
        "slug": surgeon.slug, "name": surgeon.display_name, "initials": "".join(x[0] for x in surgeon.display_name.split()[:2]),
        "specialty": surgeon.specialty, "city": surgeon.city, "region": surgeon.region,
        "country_code": surgeon.country_code, "country": COUNTRY_NAMES.get(surgeon.country_code, surgeon.country_code),
        "website_url": surgeon.website_url, "review_count": review_count,
        "procedures": [{"slug": p.slug, "name": p.name} for p in procedures],
        "updated_at": surgeon.updated_at.isoformat(),
    }


def surgeon_detail(db: Session, surgeon: Surgeon) -> dict:
    data = surgeon_summary(db, surgeon)
    revision = db.get(SurgeonRevision, surgeon.current_revision_id) if surgeon.current_revision_id else None
    snapshot = json.loads(revision.snapshot_json) if revision else {}
    data.update({"article_body": revision.article_body if revision else "", "profile": snapshot, "revision_number": revision.revision_number if revision else None})
    return data


def review_data(db: Session, review: Review) -> dict:
    surgeon = db.get(Surgeon, review.surgeon_id)
    reviewer = db.get(User, review.reviewer_id) if review.reviewer_id else None
    procedure = db.get(Procedure, review.procedure_id)
    technique = db.get(Technique, review.technique_id) if review.technique_id else None
    photos = db.scalars(select(ReviewPhoto).where(ReviewPhoto.review_id == review.id, ReviewPhoto.approved_at.is_not(None))).all()
    designated = [photo for photo in photos if photo.designated_long_term]
    if not review.surgery_date or any(photo.capture_date is None for photo in designated): long_term_status = "Date unavailable" if designated else "Missing 1-year update"
    elif review.surgery_date_precision == "exact" and designated: long_term_status = "1-year update included" if any((photo.capture_date - review.surgery_date).days >= 365 for photo in designated) else "Missing 1-year update"
    else: long_term_status = "1-year update included" if designated else "Missing 1-year update"
    ratings = db.execute(select(RatingDimension.slug, RatingDimension.label, ReviewRating.value).join(ReviewRating, ReviewRating.dimension_id == RatingDimension.id).where(ReviewRating.review_id == review.id)).all()
    return {
        "slug": review.slug, "title": review.title, "surgeon": {"slug": surgeon.slug, "name": surgeon.display_name},
        "reviewer": reviewer.display_name if reviewer else "Deleted member", "procedure": procedure.name,
        "technique": technique.name if technique else "Unknown or not listed", "surgery_date": review.surgery_date.isoformat() if review.surgery_date else None,
        "surgery_date_precision": review.surgery_date_precision, "location": review.location_text,
        "narrative": review.narrative, "complications_status": review.complications_status,
        "complications_detail": review.complications_detail, "revision_detail": review.revision_detail,
        "published_at": review.published_at.isoformat() if review.published_at else None,
        "updated_at": review.updated_at.isoformat(), "long_term_status": long_term_status,
        "ratings": [{"slug": row.slug, "label": row.label, "value": row.value} for row in ratings],
    }
