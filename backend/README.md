# AMS Backend

FastAPI service for the Attendance Management System. The backend uses PostgreSQL, SQLAlchemy 2, and Alembic. Configuration is read from the root `.env` file using the `AMS_` prefix.

## Local startup

1. Copy `.env.example` to `.env` in the repository root and set a unique `AMS_SECRET_KEY`.
2. For the containerized stack, run `docker compose up --build`; the API container applies Alembic migrations before serving and the worker starts after the API is healthy.
3. For local development, start PostgreSQL with `docker compose up -d db`, then from `backend/` run `pip install -e '.[dev]'`, `alembic upgrade head`, and `uvicorn app.main:app --reload`.

Run `python -m pytest tests -q` for the unit and API integration suites, and `ruff check app tests migrations scripts` for lint. The API journey test uses an isolated in-memory SQLite database; production migrations target PostgreSQL with the pgvector extension.

The API exposes `/health`, `/health/ready`, and `/api/health`. OpenAPI is available at `/openapi.json`.

To bootstrap the first admin, set `AMS_BOOTSTRAP_ADMIN_EMAIL`, `AMS_BOOTSTRAP_ADMIN_ID`, `AMS_BOOTSTRAP_ADMIN_NAME`, and `AMS_BOOTSTRAP_ADMIN_PASSWORD`, then run `python -m scripts.seed_admin` from `backend/`. Local development stores documents under `AMS_STORAGE_PATH`; set `AMS_STORAGE_BACKEND=s3` with the bucket, region, endpoint (for S3-compatible services), and access credentials to use object storage. Set SMTP environment values in `.env` to enable password reset email and email notifications; set Twilio account SID, auth token, and sender number to enable SMS. Install `pip install -e '.[vision]'` to enable InsightFace camera-frame recognition; manual attendance remains available without that optional dependency.
