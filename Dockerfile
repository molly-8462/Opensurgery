FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade -r requirements.txt

RUN groupadd --system --gid 10001 opensurgery \
    && useradd --system --uid 10001 --gid opensurgery --home-dir /app opensurgery \
    && mkdir -p /data/media \
    && chown -R opensurgery:opensurgery /app /data/media

COPY --chown=opensurgery:opensurgery app ./app
COPY --chown=opensurgery:opensurgery frontend ./frontend
COPY --chown=opensurgery:opensurgery migrations ./migrations
COPY --chown=opensurgery:opensurgery alembic.ini docker-entrypoint.sh ./

RUN chmod +x /app/docker-entrypoint.sh

USER opensurgery

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
