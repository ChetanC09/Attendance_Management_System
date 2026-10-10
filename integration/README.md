# Integration Track

The supplied Vite/React frontend is connected to the FastAPI API. This directory contains the API contract, a read-only role/API smoke script, and the planned browser/API fixtures and end-to-end flows.

Run the authenticated API smoke checks inside the local backend container after seeding development data. The local `.env` supplies the private `AMS_DEMO_PASSWORD`:

```powershell
docker compose exec -e AMS_SEED_DEMO=true backend python -m scripts.seed_demo
docker compose cp integration/scripts/smoke_api.py backend:/tmp/smoke_api.py
docker compose exec backend sh -c "pip install -q '.[dev]' && python /tmp/smoke_api.py"
```

The script requires the configured development password and `httpx` from the backend's `[dev]` extras. It performs read-only role, route, and invalid-Origin checks; it does not replace browser end-to-end testing. Browser journeys were manually verified during the current integration pass; automated browser flows in `e2e/` are still pending.

## Local authenticated load probe

`scripts/load_test.py` creates authenticated cookie sessions from seeded accounts, then issues a read-only burst across student, faculty, and administrator routes. Run it only against a disposable/development database:

```powershell
docker compose cp integration/scripts/load_test.py backend:/tmp/load_test.py
docker compose exec backend sh -c "PYTHONPATH=/srv/ams python /tmp/load_test.py --concurrency 100 --request-concurrency 100"
```

The runner explicitly imports `/srv/ams` so it exercises the current source rather than an installed wheel. It reuses eight demo accounts, so it tests concurrent authenticated sessions, not 100 distinct people. Each login checks the returned role and cookie; each read checks HTTP success, JSON decoding, and required route fields; each logout checks an empty HTTP 204 response. A barrier releases all authenticated sessions together. It does not write attendance, exercise live vision, or call providers. `--request-concurrency` controls client fan-out; the API separately limits in-flight HTTP requests to the configured `AMS_HTTP_REQUEST_CONCURRENCY` (default 15, which must not exceed pool capacity).

The original unbounded burst exposed pool saturation, so the API now bounds in-flight requests at `AMS_HTTP_REQUEST_CONCURRENCY` and returns a generic retryable 503 if a pool checkout still times out. A later 97/100 run had three client `RemoteProtocolError` resets with no matching API errors. Investigation found the default Uvicorn 5-second keep-alive timeout: the barrier waits until every login finishes, and the oldest authenticated sessions then reused idle HTTP connections at about 4.9 seconds. HTTPCore reported a reused connection and failed while receiving response headers; the requests were absent from API access logs, with no application exception or pool checkout error. An initial controlled server run with keep-alive set to 30 seconds completed five consecutive probes cleanly. The repository now starts Uvicorn through `app.server` with that 30-second setting; the HTTP semaphore and database pool were not enlarged. A separate five-run sequence against the rebuilt image is recorded below.

After rebuilding the local image with the repository entrypoint, five consecutive 100-session probes each completed 100/100 valid reads and 100/100 empty-204 logouts, with zero resets, HTTP errors, timeouts, or pool errors. Every session's read reused its login connection; all 300 response-header trace events completed per run. Database sampled peak was 17/100 connections (active peak 2). Aggregate read latency p95/p99, seconds, by run: 1.776/1.814; 1.713/1.764; 1.716/1.760; 1.694/1.742; 1.604/1.627. Read bursts completed in 1.71–1.90 seconds. The load runner preserves request failures in `error_categories`, includes diagnostic details, and exits nonzero on any failure. The workload uses eight unique seeded principals, not 100 distinct users; this is local evidence against the seeded database only, not production capacity certification or proof of 100 production users.
