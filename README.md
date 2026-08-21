# OpenSurgery

OpenSurgery is a FastAPI and PostgreSQL application for community-maintained surgeon profiles,
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
it: `docker-compose.yml`, `alembic.ini`, `pytest.ini`, `requirements.txt`, and `.env.example`.

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

Open <http://127.0.0.1:8000>. API documentation is available at
<http://127.0.0.1:8000/api/docs>.

Run the test suite with:

```bash
.venv/bin/pytest
```

See [docs/backend.md](docs/backend.md) for backend details and
[docs/product.md](docs/product.md) for the product model and requirements.
