# Refresh this digest deliberately from Docker Official Images and verify with a clean build.
FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv/ams
COPY requirements.lock ./
RUN python -m pip install --no-cache-dir --require-hashes -r requirements.lock

COPY app ./app
COPY scripts/seed_admin.py ./scripts/seed_admin.py
COPY migrations ./migrations
COPY alembic.ini ./

EXPOSE 8000
CMD ["python", "-m", "app.server"]
