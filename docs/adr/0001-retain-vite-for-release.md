# ADR 0001: Retain the supplied Vite frontend for this release

- **Status:** Accepted for this release
- **Date:** 2026-10-11
- **Decision owner:** Repository owner

## Context

The approved system design specifies Next.js with React and TypeScript. The supplied and currently integrated frontend is Vite with React and TypeScript, deployed as a static SPA. The owner is already preparing the Vercel project for that app.

## Decision

Retain the existing Vite + React + TypeScript frontend for this release. The owner approved this scoped architecture deviation from the system design's Next.js target. The application is already integrated as a Vite static SPA, and keeping it avoids changing the supplied frontend architecture and Vercel build/runtime contract during release preparation.

## Consequences

- The current Vercel project must use `frontend/` as its root, Vite build output `dist`, and the SPA rewrite in `frontend/vercel.json`.
- `VITE_API_BASE_URL` is compiled into the static bundle. Changing the API URL requires a new frontend build/deployment.
- A future Next.js migration requires a separate owner decision, estimate, route/API regression plan, and deployment rehearsal; it is not part of this release.
- This decision approves retaining Vite for this release only. It does not by itself approve deployment or establish production readiness.
