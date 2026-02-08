# Project Context

## Product
1. What is being built: public research opportunities aggregator with connector/processor ingestion and moderation-backed publishing.
2. Target users: public visitors, authenticated submitters, moderators/admins, connector/processor bots.
3. Primary outcomes: fresh searchable catalogue, high-precision dedupe, full provenance trail for each published posting.

## Architecture
1. Frontend: Next.js (`web/`) intended for Vercel.
2. Backend/API: FastAPI (`api/`) intended for Cloud Run.
3. Data store: Supabase Postgres/Auth (`db/` schema baseline in-repo).
4. Jobs/workers: Python worker runtime (`workers/`) with durable job ledger contract.
5. Hosting/deploy: Vercel + Cloud Run + Supabase (target architecture; infra IaC pending).

## Core Constraints
1. Discoveries are append-only and evidence is stored by pointer.
2. URL normalization is conservative/deterministic; redirect resolution is async.
3. Dedupe is precision-first with moderation for uncertain merges.
4. Human auth and machine auth remain separated from day one.

## Current Source of Truth
1. Main spec: `handoff/SPEC_v1.2.md`
2. Data/schema docs: `db/schema_v1.sql`
3. Implementation roadmap: `handoff/IMPLEMENTATION_PLAN_v1.2.md`
