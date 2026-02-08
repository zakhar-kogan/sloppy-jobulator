# Architecture Snapshot

## Services

1. `web/` (Next.js on Vercel): public catalogue and operator UI.
2. `api/` (FastAPI on Cloud Run): ingestion, jobs, moderation, public read APIs.
3. `workers/` (Cloud Run Jobs): extraction/dedupe/enrichment/freshness processors.
4. `db/` (Supabase Postgres/Auth): core relational model, auth integration, RLS.

## Core Contracts

1. Connector intake: `POST /discoveries`, `POST /evidence`.
2. Processor control-plane: `GET /jobs`, `POST /jobs/{id}/claim`, `POST /jobs/{id}/result`.
3. Public catalogue: `GET /postings`, `GET /postings/{id}` (detail pending implementation).

## Current Status

1. Monorepo scaffold created.
2. Baseline schema + migration created (`db/schema_v1.sql`, `db/migrations/0001_schema_v1.sql`).
3. API and worker use in-memory stores for bootstrap and will move to Postgres in next phase.
