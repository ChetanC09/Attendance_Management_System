# AMS deployment preparation

## Recommended layout

- **Vercel** serves the existing Vite/React frontend from the repository root with `frontend/` as its Root Directory and `dist` as the output directory.
- **Render** runs the FastAPI Docker web service and notification worker.
- **Render Postgres** is the managed PostgreSQL 16 database (with pgvector), connected over Render's private network. It is preferable to a self-managed database container for a public deployment because it provides managed persistence and backup options.
- Use an S3-compatible bucket for request documents. The Render service filesystem is ephemeral; local uploads are only suitable for development.

`vercel.json` provides the SPA route fallback. `render.yaml` is a Blueprint for API, worker, and database. It does not deploy anything until connected to the Git repository and applied in Render.

## Configuration order

1. Create the Render Blueprint from `render.yaml` in the Singapore region (or change all Render regions together before first creation).
2. Set `AMS_CORS_ORIGINS` on `ams-api` to a JSON array containing the exact deployed Vercel origin, for example `["https://ams-example.vercel.app"]`. Set `AMS_FRONTEND_BASE_URL` to that same origin. Do not include a trailing slash.
3. Set the S3-compatible bucket, region, endpoint (blank for AWS), and credentials. Keep the bucket private; uploaded documents are served only after API authorization.
4. Set SMTP credentials if password reset email is required. Twilio environment values are optional unless SMS is enabled in system settings.
5. Create the Vercel project with Root Directory `frontend`, Framework Preset `Vite`, and `VITE_API_BASE_URL=https://<ams-api-service>.onrender.com`. Set this for Production and Preview environments only when the API CORS allowlist includes each origin.
6. Configure a Vercel production domain, then update Render's CORS and frontend base URL with the exact domain. Deploy the frontend and verify login, logout, and a protected request from that origin.
7. Create the first production administrator by setting `AMS_BOOTSTRAP_ADMIN_EMAIL`, `AMS_BOOTSTRAP_ADMIN_ID`, `AMS_BOOTSTRAP_ADMIN_NAME`, and a strong `AMS_BOOTSTRAP_ADMIN_PASSWORD` for a one-time `python -m scripts.seed_admin` invocation in the API service shell. Remove the bootstrap variables after the account is created. **Do not use the development demo seeder in production.**

## Cross-origin session requirements

The frontend and API use different hostnames, so production requires `AMS_COOKIE_SAMESITE=none`, HTTPS, `Secure` and `HttpOnly` cookies, and an exact CORS origin allowlist with credentials. The API also rejects unsafe browser requests whose `Origin` is outside that allowlist. Do not use a wildcard CORS origin with cookies.

The browser API base URL is compiled into the Vite bundle. Changing `VITE_API_BASE_URL` requires a new Vercel build/deployment.

## Local data fixtures

After starting the local Compose stack and applying migrations, run:

```powershell
docker compose exec backend python -m scripts.seed_demo
```

The idempotent, development-only seeder creates an admin, faculty, six students, one department/year/semester/section, three courses and allocations, timetable entries, conducted lecture attendance, a pending request, an announcement, a notification, and the attendance threshold. All demo accounts use `AMS_DEMO_PASSWORD` (default `SolarisDemo2026!`). Never enable demo fixtures on a production database.

## Acceptance gates before public launch

- All Python unit and integration tests pass against PostgreSQL, plus frontend type-check/build.
- Login works with `SameSite=None` cookies from the real Vercel hostname; role-scoped student, faculty, and admin journeys pass.
- WebSocket attendance events work through the public Render endpoint.
- S3 uploads/download authorization and password reset email are verified with real provider credentials.
- Camera recognition is validated only with enrolled, consenting profiles and deployed vision dependencies; manual marking remains the fallback.
- Configure Render backup/recovery and monitor service health/logs. A 256 MB database is suitable only for a small project/demo workload; size it for expected data and connections.

## Important limitations

- This repository's UI is Vite/React rather than the design document's locked Next.js stack. Vercel supports the current Vite app, but the implementation remains a documented architecture deviation.
- The Render Blueprint configures an S3-compatible storage backend and requests its settings; external bucket creation and credentials are account-side steps.
- Real provider credentials, custom domains, deployment, and first production admin provisioning must be supplied/applied in the relevant cloud accounts.
