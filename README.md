# SurgeonSite backend

This is a FastAPI and PostgreSQL application for community-maintained surgeon profiles,
revision history, structured patient reviews, discussions, and private member messaging.

## Repository layout

```text
app/                  FastAPI routes, security, database models, and seed data
frontend/
  pages/              Static HTML pages served at the site root
  assets/
    css/              Stylesheets
    js/               Browser JavaScript and API integration
    data/             Public downloadable static data
migrations/           Alembic database migrations
tests/                Automated backend and integration tests
docs/                 Product documentation, notes, and reference screenshots
```

Deployment and tool configuration remains at the repository root so standard commands can discover
it: `Dockerfile`, `docker-compose.yml`, `alembic.ini`, `pytest.ini`, `requirements.txt`, and
`.env.example`.

## Compose deployment

The Compose stack runs both PostgreSQL and the FastAPI application. On application startup, the
entrypoint waits for Compose's database health dependency, applies all pending Alembic migrations,
optionally loads fictional demo data, and then starts Uvicorn.

```bash
cp .env.example .env
# Replace SECRET_KEY and POSTGRES_PASSWORD in .env before continuing.
docker compose up -d --build
docker compose ps
docker compose logs -f app
```

Open `http://SERVER_IP:8000` (or the port selected with `APP_PORT`). Set `SEED_DEMO_DATA=true` only
for an isolated demonstration environment. Keep it `false` anywhere that might receive real data.

Apply future code and migration changes with:

```bash
git pull
docker compose up -d --build
```

The recreated application container applies pending migrations before accepting requests. The
PostgreSQL and processed-media named volumes persist across ordinary container recreation.

## Local development

```bash
cp .env.example .env
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
docker compose up -d db
.venv/bin/alembic upgrade head
.venv/bin/python -m app.seed
.venv/bin/uvicorn app.main:app --reload
```

This manual workflow remains useful when developing with Python on the host. It is not required for
the containerized Compose deployment above.

Open <http://127.0.0.1:8000>. API documentation is available at
<http://127.0.0.1:8000/api/docs>.

Password-reset email is configured for [Resend's SMTP relay](https://resend.com/docs/send-with-smtp).
First verify your sending domain in Resend, then put the API key and a sender on that domain in the
private `.env` file:

```dotenv
SMTP_PASSWORD=re_your_resend_api_key
SMTP_FROM_ADDRESS=no-reply@your-domain.com
```

The checked-in defaults use `smtp.resend.com`, port `587`, username `resend`, and STARTTLS. Never
commit the real API key. Reset links expire after one hour, are single-use, and revoke existing
sessions when used. User-visible backend branding is controlled by the single `site_name` setting
in `app/config.py`; it can also be overridden with the `SITE_NAME` environment variable.

Run the test suite with:

```bash
.venv/bin/pytest
```

See [docs/backend.md](docs/backend.md) for backend details and
[docs/product.md](docs/product.md) for the product model and requirements.
