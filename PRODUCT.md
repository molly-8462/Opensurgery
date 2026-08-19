# SurgeonSite product foundation

## Purpose

SurgeonSite is a community-maintained directory and experience archive for transgender patients researching surgeons and procedures. It combines:

1. Factual, revision-tracked surgeon pages.
2. Structured, first-person patient reviews with optional photographs.
3. User profiles that let reviewers choose how other members may contact them.

Each surgeon page has a persistent local header with `Info` and `Reviews` tabs. The tabs are two views of the same surgeon identity: `Info` presents the community-maintained factual record, while `Reviews` presents structured first-person experiences. They are stored as separate related records and must never be blended into one editable article.

The site should help people compare information; it must not present itself as medical advice or decide which surgeon is appropriate for an individual.

## Product principles

- **Useful before decorative.** Dense, legible, link-oriented pages inspired by Wikipedia and Steam rather than marketing-site cards, gradients, oversized headings, or AI-generated imagery.
- **Community evidence over anonymous claims.** Show sources, revision history, review dates, and clearly separated firsthand experience.
- **Privacy by default.** Profiles are pseudonymous, contact is opt-in, and users control photo visibility.
- **Neutral factual records.** A surgeon page is not owned by the surgeon and is distinct from subjective reviews.
- **Human moderation is essential.** Automation may queue, label, rate-limit, or flag content, but should not silently decide whether a medical experience is truthful.
- **No generative-AI dependency.** Core writing, moderation, search, and design must work without generated prose or imagery.
- **Clearly independent identity.** The article structure may use familiar wiki conventions, but branding, colors, typography, controls, and supporting interface elements must remain recognizably OpenSurgery. The site must not imply that it is operated by, affiliated with, or endorsed by Wikipedia or the Wikimedia Foundation.

## Primary records

### Surgeon

- Name and aliases
- Practice names and locations, with effective dates
- Country and region
- Website and public contact details
- Procedures offered
- Techniques reported, with citations and effective dates
- Credentials and professional registrations, where publicly verifiable
- Languages and accessibility information
- Revision history, sources, edit notes, and moderation state
- A `Talk` section for discussing sources, disputed wording, proposed changes, and editorial decisions

Claims such as credentials, disciplinary actions, complications, or death should require a reliable source or appear only inside a clearly labeled firsthand review.

### Procedure and technique

Use controlled records rather than free-form tags. A procedure can have multiple techniques, and terminology can change across countries and communities. Preserve aliases without treating them as identical unless moderators approve the mapping.

### Review

- Reviewer and surgeon
- Procedure(s) and technique, including “unknown/not listed”
- Surgery date or privacy-preserving month/year
- Country/location at time of surgery
- Cost, currency, and what it included (optional)
- Wait time and revision history (optional)
- Ratings broken into named dimensions rather than one unexplained score
- Narrative experience
- Complications and revisions, with a “prefer not to say” option
- Photos, each with its own capture date, caption, visibility, and content warning
- One or more photos optionally designated by the reviewer as a 1-year-or-later update
- Created/updated dates and moderation state

A review is an account of one patient’s experience, not an edit to the surgeon’s factual biography.

### User profile

- Pseudonymous display name
- Optional bio and approximate region
- Procedures the user chooses to disclose
- Contact modes individually enabled by the user
- Prefer in-site messages over publishing email addresses
- Ability to disable contact, block users, hide reviews, export data, and delete the account

## Long-term follow-up status

Use a clear status label, not a judgment about whether the patient's experience itself is complete:

- `1-year update included`: at least one approved postoperative image is designated as a 1-year-or-later update and its supplied dates are consistent with that designation.
- `Missing 1-year update`: the condition above is not met.
- `Date unavailable`: the surgery date or qualifying image date is too imprecise to calculate.

Reviewers may designate an existing photo as their 1-year-or-later update when creating a review. The system must not require them to wait a year after joining or after submitting the review; many early contributors will be documenting surgeries that happened years earlier. When exact surgery and photo capture dates are available, the system should verify that the photo date is at least 365 days after the surgery date. If dates are intentionally recorded only as month/year for privacy, accept the user's designation while displaying that the timing is self-reported.

The label must explain that it verifies only the presence and user-stated timing of an image, not its authenticity or the quality of the outcome. Keep the original upload timestamp separately; it is not the capture date. Never require a user to upload a photo in order to publish a written review.

## Editing and trust model

Do not make every saved edit immediately authoritative. Use:

1. A published surgeon revision.
2. User-submitted edit proposals with an edit summary and sources.
3. A read-only preview of the proposed page and every published historical version; no side-by-side comparison interface.
4. Approval, rejection, or rollback by trusted editors/moderators.
5. A permanent audit trail that omits private moderator notes.
6. A linked `Talk` section where contributors can discuss an article without placing editorial debate inside the factual record.

New accounts should have tighter edit and upload limits. Trust can grow through account age and accepted contributions, but should not make a user immune from review.

Every published revision should record its author, timestamp, edit summary, sources, and parent revision. Anyone can open a read-only snapshot of an individual historical revision, while authorized editors can restore it by creating a new revision without destroying later history. Talk comments also need authorship, timestamps, permalinks, moderation state, and their own non-destructive history. A more formal dispute-escalation system inspired by Wikipedia can be added after the core editing and moderation workflows are stable.

The public history view should list immutable published revisions with timestamps, contributor attribution, edit summaries, change types, and permanent links. Selecting a revision opens a read-only snapshot of the full page as it appeared at that time. Authorized actions such as undo and rollback create new revisions rather than deleting or rewriting old history. Clearly distinguish the current, reviewed, and rollback states, while keeping private moderation notes out of the public log.

The surgeon editor should pair clear article-section text areas with structured profile fields. Practice and website links use URL validation; location is split into city, region, and country; procedures come from database-backed multi-select options; and portrait changes require an image upload plus a publication-rights confirmation. Every proposal requires at least one source URL, a note explaining what it supports, and an edit summary. Contributors may save a draft or preview changes before submitting the proposal for review. Clicking an article's section-level edit control should open the editor at that section.

## MVP

### Include

- Account creation, sign-in, recovery, and pseudonymous profiles
- Surgeon directory, search, and structured surgeon pages
- Revisioned edit proposals with citations
- Structured reviews and per-dimension ratings
- Secure image upload with metadata removal and content warnings
- 1-year update designation and status calculation
- Opt-in private messaging between members
- Email notification when a user receives an internal message, with account-level notification controls
- Reporting, blocking, moderation queue, rollback, and audit log
- Responsive, accessible light and dark themes
- Clearly labeled banner and sidebar advertising placements

### Defer

- Surgeon-claimed profiles or paid features
- Direct messaging attachments
- Recommendation algorithms or personalized surgeon rankings
- Native mobile apps
- Public APIs
- Automatic medical-image interpretation
- Complex reputation points or gamification

## Safety and moderation requirements

- Explicit rules for harassment, hate, threats, doxxing, impersonation, conflicts of interest, promotional reviews, and non-consensual images.
- Treat legal names, locations, contact details, medical history, surgery dates, and images as sensitive data even when local law does not classify every field as health data.
- Strip EXIF and other metadata, decode and re-encode allowed image types, use generated storage keys, scan uploads, cap dimensions/file sizes, and serve media from isolated object storage.
- Provide granular image visibility: public, signed-in members, or private draft. Use content warnings and click-to-reveal for nudity or surgical imagery.
- Preserve evidence needed for abuse handling while honoring documented retention and deletion rules.
- Rate-limit sign-up, edits, reviews, messages, reports, and uploads.
- Keep private message contents out of notification emails by default; link the recipient back to the authenticated site and provide unsubscribe/settings controls.
- Allow surgeons to report factual errors without giving them control over patient reviews.
- Create an appeals path for both reviewers and surgeons.
- Publish transparent moderation and conflict-of-interest policies before accepting public submissions.
- Do not target advertising using a person's transgender status, procedures researched, reviews, messages, photographs, medical history, or other sensitive activity. Prefer contextual sponsorships selected from the public page topic rather than behavioral profiles.
- Visually separate advertising from community content, label every placement as advertising, and prohibit ads that impersonate navigation, reviews, surgeon records, or editorial recommendations.
- Establish sponsor eligibility and conflict-of-interest rules. Payment must never affect surgeon-page content, review ordering, moderation outcomes, or removal of criticism.

## Recommended technical shape

Build one application around a relational database rather than embedding reviews in MediaWiki:

- Server-rendered web application for fast, indexable public pages
- PostgreSQL for related but separate tables covering users, surgeons, procedures, surgeon revisions, talk discussions, reviews, messages, permissions, and audit records
- Private object storage plus an image-processing pipeline for originals and safe display variants
- Background jobs for image processing, notifications, and moderation workflows
- Search initially backed by PostgreSQL; introduce a separate search service only when measurement shows it is needed
- Authorization enforced on the server, with database row-security considered as defense in depth

MediaWiki can store revisioned prose, and Semantic MediaWiki can add structured fields, but the combined privacy, review, messaging, photo, and moderation requirements would still need substantial custom application code. A purpose-built relational application gives these records one permission and moderation model.

Use one primary relational database for the MVP, not separate databases for Info and Reviews. Separate tables preserve the boundary between factual surgeon information and patient reviews while foreign keys connect both to the same surgeon. This avoids duplicated surgeon identities and makes transactions, permissions, backups, search, and deployment simpler. Media files themselves belong in object storage; the database stores their metadata and storage keys.

## Visual direction

- System or restrained humanist sans-serif typography for UI; optional serif only for long article text
- Flat surfaces, compact spacing, visible borders, conventional underlined links
- Information tables, revision tabs, small status labels, and a persistent search field
- A persistent surgeon-page header with clearly selected `Info` and `Reviews` tabs, plus access to revision history and `Talk`
- A low-fatigue blue, pink, and warm-white palette inspired by—but not color-matched to—the transgender pride flag. Use softened tints for large surfaces and reserve stronger colors for links, focus, and selected states so long research sessions remain comfortable.
- No gradients, glass effects, decorative blobs, fake testimonials, stock surgery imagery, or excessive rounded cards
- Keyboard navigation, clear focus states, semantic HTML, reduced-motion support, and WCAG AA contrast from the first prototype

The first prototype should test a surgeon page—the densest and most important screen—before building a promotional homepage.

## Frontend prototype status

The static frontend now implements a complete linked demonstration of the core product. `home.html` is the public landing page and every OpenSurgery wordmark returns there. The menu drawer provides consistent access to discovery, contribution, account, messaging, policy, and support routes. The prototype includes account creation, login and recovery, account settings, public profiles, private-message screens, directory filters, search results, procedure guides, the complete Mara Voss Info/Reviews/Talk/Edit/History workflow, historical snapshots, proposal queue, review composition and detail pages, talk archives, and public policy/support pages.

Forms and controls provide browser-side validation and honest demonstration states. Account identity is stored only in local browser storage, photo previews remain local, filters operate on the sample records, and download/copy/drawer controls work without a server. No form sends personal or medical information externally. Authentication, persistence, moderation, email delivery, uploads, and secure messaging still require the production backend described below; the frontend must not imply those services are active before they are connected.

The distinct palette, wordmark, advertising treatment, and component styling are intentional product-identity choices. They reduce the chance that users could mistake OpenSurgery for an official Wikipedia/Wikimedia project and address the trade-dress concern created by borrowing familiar wiki information architecture. Before public launch, include a plain-language non-affiliation statement in the public policies and have the final brand presentation reviewed in the operating jurisdiction.

## Advertising and sponsorship

- Reserve one responsive banner placement below the global header and one sidebar placement on wide screens.
- Keep article text, review rows, talk discussions, and private messaging free of inline advertising in the MVP.
- Every placement must use a persistent `Advertisement` label, even when sold as a sponsorship.
- Ads must not resemble site notices, edit controls, review calls to action, or medical recommendations.
- Prefer fixed-size, low-motion creative. Disallow autoplay audio, flashing content, deceptive countdowns, and disruptive overlays.
- Do not disclose page-level user activity to advertisers beyond what is strictly necessary to deliver a contextual placement, and document any ad vendor in the privacy policy.
- Surgeon and clinic advertising requires an especially visible conflict-of-interest label and must not appear on that surgeon's own profile or comparison results until a formal policy is approved.

## Decisions to resolve before public launch

- Legal entity, operating jurisdiction, age policy, and counsel review
- Whether intimate postoperative images may be public or members-only
- Exact rating dimensions and whether an aggregate score should exist
- Citation quality rules and which claims require moderator preapproval
- Whether accounts may review without publicly attaching the review to their profile
- Surgeon identity verification and right-of-reply process
- Data retention, deletion, backups, breach response, and law-enforcement request policies
- Moderator recruitment, training, escalation, and mental-health safeguards
