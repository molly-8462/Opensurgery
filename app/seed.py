import json
from datetime import date, datetime, timezone

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import (Conversation, ConversationMember, EditProposal, Location, Message, ModerationState, Practice,
                     Procedure, RatingDimension, Review, ReviewRating, RevisionKind, Surgeon, SurgeonPractice, SurgeonRevision, TalkComment,
                     TalkTopic, Technique, User, UserRole, surgeon_procedures)
from .security import hash_password


SURGEONS = [
    dict(slug="mara-voss", display_name="Mara Voss", specialty="Plastic and reconstructive surgeon", country_code="US", region="Oregon", city="Portland", aliases=None,
         article="Mara Voss is a fictional American plastic and reconstructive surgeon based in Portland, Oregon. Her listed practice focuses on gender-affirming chest surgery and related revisions.",
         profile={"practice":"Northbank Reconstructive Center","languages":["English","Spanish"],"accessibility":"The Portland clinic reports a step-free main entrance.","practice_summary":"Public information describes a focus on gender-affirming and reconstructive care, with virtual intake before an in-person consultation.","patient_information":"Availability, insurance participation, and consultation requirements should be confirmed with the practice."}),
    dict(slug="adrian-lee", display_name="Adrian Lee", specialty="Craniofacial surgeon", country_code="CA", region="Ontario", city="Toronto", aliases=None,
         article="Adrian Lee is a fictional craniofacial surgeon included to demonstrate a directory profile.", profile={"practice":"Example Craniofacial Centre","languages":["English"],"practice_summary":"Demonstration record."}),
    dict(slug="samira-khan", display_name="Samira Khan", specialty="Plastic surgeon", country_code="GB", region="Greater Manchester", city="Manchester", aliases=None,
         article="Samira Khan is a fictional plastic surgeon included to demonstrate a directory profile.", profile={"practice":"Example Manchester Practice","languages":["English"],"practice_summary":"Demonstration record."}),
    dict(slug="narin-chai", display_name="Narin Chai", specialty="Gender-affirming surgeon", country_code="TH", region=None, city="Bangkok", aliases=None,
         article="Narin Chai is a fictional gender-affirming surgeon included to demonstrate a directory profile.", profile={"practice":"Example Bangkok Practice","languages":["Thai","English"],"practice_summary":"Demonstration record."}),
]

PROCEDURES = [
    ("chest-masculinization","Chest masculinization","Chest","Removes and reshapes chest tissue to create a flatter chest contour."),
    ("chest-revision","Chest revision","Chest","Revisional surgery addressing an earlier chest procedure."),
    ("breast-augmentation","Breast augmentation","Chest","Uses implants, fat transfer, or both to increase breast volume and shape."),
    ("vaginoplasty","Vaginoplasty","Genital","Creates vulvar structures and, depending on the approach, a vaginal canal."),
    ("facial-feminization","Facial feminization surgery","Facial","May include forehead, jaw, chin, hairline, or nose procedures."),
    ("facial-revision","Facial revision","Facial","Revisional surgery addressing a previous facial procedure."),
    ("voice-surgery","Voice surgery","Voice","Techniques intended to alter pitch or other voice characteristics."),
]


def seed(db: Session) -> None:
    if db.scalar(select(Surgeon.id).limit(1)):
        return
    users = {}
    for name, email, role, bio, region in [
        ("JuniperNorth","juniper@example.com","trusted_editor","Researching chest surgeons and contributing sources when I can.","Northern California"),
        ("RiverNorth","river@example.com","member","I’ve shared my chest-surgery experience to help people planning travel and recovery.","Pacific Northwest"),
        ("AshAndPine","ash@example.com","member",None,None), ("CedarKeys","cedar@example.com","member",None,None), ("MapleSignal","maple@example.com","member",None,None),
    ]:
        user=User(display_name=name,email=email,password_hash=hash_password("prototype-password"),role=UserRole(role),bio=bio,approximate_region=region,allow_messages=name=="RiverNorth",created_at=datetime(2024,1,15,tzinfo=timezone.utc)); db.add(user); users[name]=user
    procedures={}
    for slug,name,category,description in PROCEDURES:
        p=Procedure(slug=slug,name=name,category=category,description=description); db.add(p); procedures[slug]=p
    db.flush()
    ratings = {}
    for slug, label in [("communication","Communication"),("expectation-setting","Expectation setting"),("aftercare","Aftercare")]:
        dimension=RatingDimension(slug=slug,label=label,is_active=True); db.add(dimension); ratings[slug]=dimension
    db.flush()
    techniques={}
    for slug,name,procedure in [("double-incision","Double incision","chest-masculinization"),("periareolar","Periareolar","chest-masculinization"),("buttonhole","Buttonhole","chest-masculinization")]:
        t=Technique(slug=slug,name=name,procedure_id=procedures[procedure].id); db.add(t); techniques[slug]=t
    db.flush()
    surgeon_map={}
    links={"mara-voss":["chest-masculinization","chest-revision"],"adrian-lee":["facial-feminization","facial-revision"],"samira-khan":["chest-masculinization","breast-augmentation"],"narin-chai":["vaginoplasty","chest-revision"]}
    for source_item in SURGEONS:
        item = source_item.copy()
        article=item.pop("article"); profile=item.pop("profile")
        surgeon=Surgeon(**item,is_published=True,lifecycle_status="published"); db.add(surgeon); db.flush(); surgeon_map[surgeon.slug]=surgeon
        db.execute(insert(surgeon_procedures), [{"surgeon_id":surgeon.id,"procedure_id":procedures[p].id} for p in links[surgeon.slug]])
        rev=SurgeonRevision(surgeon_id=surgeon.id,revision_number=124 if surgeon.slug=="mara-voss" else 1,author_id=users["JuniperNorth"].id,article_body=article,snapshot_json=json.dumps(profile),edit_summary="Seeded fictional demonstration profile.",change_type="Article text",kind=RevisionKind.reviewed,published_at=datetime(2026,5,12,9,17,tzinfo=timezone.utc)); db.add(rev); db.flush(); surgeon.current_revision_id=rev.id
    mara=surgeon_map["mara-voss"]
    practice=Practice(slug="northbank-reconstructive-center",name="Northbank Reconstructive Center"); db.add(practice); db.flush()
    db.add(SurgeonPractice(surgeon_id=mara.id,practice_id=practice.id,is_primary=True))
    db.add(Location(practice_id=practice.id,label="Portland clinic",city="Portland",region="Oregon",country_code="US",accessibility="The main entrance is reported as step-free."))
    for number,author,summary,change,kind,when in [
        (123,"RiverNorth","Specified that accessibility information applies to the Portland clinic’s main entrance.","Profile facts",RevisionKind.normal,datetime(2026,5,9,1,34,tzinfo=timezone.utc)),
        (122,"MapleSignal","Added Spanish to languages reported by the clinic and included a supporting source.","Profile facts",RevisionKind.reviewed,datetime(2026,4,22,18,51,tzinfo=timezone.utc)),
        (121,"CedarKeys","Updated the procedure citation to an archived clinic page.","Sources",RevisionKind.normal,datetime(2026,4,4,12,8,tzinfo=timezone.utc)),
        (120,"JuniperNorth","Reverted unsourced changes to practice location and website.","Moderation",RevisionKind.rollback,datetime(2026,3,30,22,16,tzinfo=timezone.utc)),
        (119,"AshAndPine","Reorganized the practice section and corrected a typographical error.","Article text",RevisionKind.normal,datetime(2026,3,18,7,42,tzinfo=timezone.utc)),
    ]:
        db.add(SurgeonRevision(surgeon_id=mara.id,revision_number=number,author_id=users[author].id,article_body=SURGEONS[0]["article"],snapshot_json=json.dumps({"practice":"Northbank Reconstructive Center"}),edit_summary=summary,change_type=change,kind=kind,published_at=when))
    review=Review(slug="river-chest-masculinization",surgeon_id=mara.id,reviewer_id=users["RiverNorth"].id,procedure_id=procedures["chest-masculinization"].id,technique_id=techniques["double-incision"].id,title="Chest masculinization with Mara Voss",surgery_date=date(2024,2,1),surgery_date_precision="month",location_country_code="US",location_text="Portland, Oregon",narrative="The office was straightforward about scheduling and recovery. I traveled from another state and stayed nearby for nine days. The written instructions were clear, and I knew who to contact when I had questions about swelling.\n\nThe first weeks were physically tiring, but my recovery was close to what the team described. I felt that expectations about scar placement and nipple healing were discussed honestly during the consultation.\n\nResponses before surgery were usually within two business days. Long-term follow-up was less structured, so I scheduled the one-year appointment myself.",complications_status="none_reported",state=ModerationState.published,published_at=datetime(2026,4,18,tzinfo=timezone.utc)); db.add(review); db.flush()
    db.add_all([ReviewRating(review_id=review.id,dimension_id=ratings["communication"].id,value=4),ReviewRating(review_id=review.id,dimension_id=ratings["expectation-setting"].id,value=5),ReviewRating(review_id=review.id,dimension_id=ratings["aftercare"].id,value=4)])
    topic=TalkTopic(surgeon_id=mara.id,slug="technique-sources",title="Technique sources",author_id=users["JuniperNorth"].id); db.add(topic); db.flush()
    db.add_all([TalkComment(topic_id=topic.id,author_id=users["JuniperNorth"].id,body="The practice page now lists buttonhole as an option, so the wording and archived source should be updated.",created_at=datetime(2026,5,12,16,42,tzinfo=timezone.utc)),TalkComment(topic_id=topic.id,author_id=users["CedarKeys"].id,body="Could we say listed in current clinic materials and avoid claiming availability?",created_at=datetime(2026,5,12,18,9,tzinfo=timezone.utc))])
    proposal=EditProposal(surgeon_id=mara.id,base_revision_id=mara.current_revision_id,author_id=users["JuniperNorth"].id,proposed_article_body=SURGEONS[0]["article"],proposed_snapshot_json=json.dumps(SURGEONS[0]["profile"]),edit_summary="Update consultation and accessibility information",state=ModerationState.pending,submitted_at=datetime(2026,5,16,tzinfo=timezone.utc)); db.add(proposal)
    conversation=Conversation(); db.add(conversation); db.flush(); db.add_all([ConversationMember(conversation_id=conversation.id,user_id=users["RiverNorth"].id),ConversationMember(conversation_id=conversation.id,user_id=users["JuniperNorth"].id),Message(conversation_id=conversation.id,sender_id=users["RiverNorth"].id,body="Happy to answer questions about finding a nearby place to stay.",created_at=datetime(2026,5,18,10,42,tzinfo=timezone.utc)),Message(conversation_id=conversation.id,sender_id=users["JuniperNorth"].id,body="Thank you. How many days did you stay before traveling home?",created_at=datetime(2026,5,18,11,5,tzinfo=timezone.utc))])
    db.commit()


def main() -> None:
    with SessionLocal() as db: seed(db)


if __name__ == "__main__": main()
