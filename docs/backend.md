# OpenSurgery backend

The repository structure and quick-start commands are summarized in the root `README.md`. Frontend
pages are stored in `frontend/pages`, and browser assets are stored in `frontend/assets` while
remaining available through their existing public URLs.

The application is now served by FastAPI and stores relational records in PostgreSQL. Static HTML,
CSS, and JavaScript are served by the same process, while browser code reads and writes data through
the versioned `/api/v1` routes.

## Local setup

1. Copy `.env.example` to `.env` and replace `SECRET_KEY`.
2. Start PostgreSQL with `docker compose up -d db`.
3. Install Python dependencies with `python3 -m venv .venv` and
   `.venv/bin/pip install -r requirements.txt`.
4. Create the schema with `.venv/bin/alembic upgrade head`.
5. Load the fictional development records with `.venv/bin/python -m app.seed`.
6. Run the application with `.venv/bin/uvicorn app.main:app --reload`.
7. Open `http://127.0.0.1:8000`. Interactive API documentation is at `/api/docs`.

Seed accounts use the password `prototype-password` and reserved `example.com` email addresses. They are strictly
development fixtures and must not be loaded in production.

## Data boundaries

- `surgeons` is the stable identity used by directory entries, reviews, revisions, talk topics,
  practices, and proposals.
- `surgeon_revisions` is immutable published history. `surgeons.current_revision_id` identifies the
  current snapshot without overwriting older versions.
- `edit_proposals` is a moderation queue, separate from published revisions.
- `reviews` contains first-person experience and never edits the factual surgeon article.
- `procedures` and `techniques` are controlled records; join tables model offerings over time.
- `media_assets` stores only object keys, hashes, processing state, and dimensions. Actual images
  belong in isolated object storage after metadata stripping, re-encoding, and scanning.
- Conversations, blocks, reports, and audit events are separate so privacy and retention policies can
  be enforced without coupling them to public content.

Public reads never expose email addresses, password hashes, private moderator details, or message
contents. Authenticated browser sessions use signed, HTTP-only, SameSite cookies; the API also
accepts bearer tokens for non-browser clients. Writes that create reviews, proposals, and messages require authentication. Production
deployment must add reverse-proxy TLS, request rate limiting, object storage, background workers,
email delivery, secret management, backups, and a documented retention policy.
