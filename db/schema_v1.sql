-- Sloppy Jobulator v1 baseline schema
-- Source: docs/spec/SPEC_v1.2.md

create extension if not exists pgcrypto;

create type module_kind as enum ('connector', 'processor');
create type module_trust_level as enum ('trusted', 'semi_trusted', 'untrusted');
create type evidence_kind as enum (
  'url_fetch',
  'html_snapshot',
  'screenshot',
  'text',
  'rss_item',
  'social_post',
  'telegram_message',
  'other'
);
create type candidate_state as enum (
  'discovered',
  'processed',
  'publishable',
  'published',
  'rejected',
  'closed',
  'archived',
  'needs_review'
);
create type posting_status as enum ('active', 'stale', 'archived', 'closed');
create type job_kind as enum (
  'dedupe',
  'extract',
  'enrich',
  'check_freshness',
  'resolve_url_redirects'
);
create type job_status as enum ('queued', 'claimed', 'done', 'failed', 'dead_letter');
create type merge_decision as enum ('auto_merged', 'manual_merged', 'rejected', 'needs_review');
create type submission_status as enum ('queued', 'approved', 'rejected');

create table modules (
  id uuid primary key default gen_random_uuid(),
  module_id text not null unique,
  name text not null,
  kind module_kind not null,
  enabled boolean not null default true,
  scopes text[] not null default '{}',
  config_schema jsonb not null default '{}'::jsonb,
  default_config jsonb not null default '{}'::jsonb,
  trust_level module_trust_level not null default 'untrusted',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table module_credentials (
  id uuid primary key default gen_random_uuid(),
  module_id uuid not null references modules(id) on delete cascade,
  key_hint text not null,
  key_hash text not null,
  is_active boolean not null default true,
  expires_at timestamptz,
  created_at timestamptz not null default now(),
  revoked_at timestamptz,
  unique (module_id, key_hint)
);

create table discoveries (
  id uuid primary key default gen_random_uuid(),
  origin_module_id uuid not null references modules(id),
  external_id text,
  discovered_at timestamptz not null,
  url text,
  normalized_url text,
  canonical_hash text,
  title_hint text,
  text_hint text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index discoveries_origin_external_unique
  on discoveries(origin_module_id, external_id)
  where external_id is not null;

create unique index discoveries_origin_normalized_unique
  on discoveries(origin_module_id, normalized_url)
  where external_id is null and normalized_url is not null;

create index discoveries_origin_created_idx on discoveries(origin_module_id, created_at desc);
create index discoveries_canonical_hash_idx on discoveries(canonical_hash);

create table evidence (
  id uuid primary key default gen_random_uuid(),
  discovery_id uuid references discoveries(id) on delete cascade,
  kind evidence_kind not null,
  uri text not null,
  content_hash text not null,
  captured_at timestamptz not null,
  content_type text,
  byte_size bigint,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index evidence_discovery_idx on evidence(discovery_id);
create index evidence_content_hash_idx on evidence(content_hash);

create table posting_candidates (
  id uuid primary key default gen_random_uuid(),
  state candidate_state not null default 'discovered',
  dedupe_bucket_key text,
  dedupe_confidence numeric(5,4),
  extracted_fields jsonb not null default '{}'::jsonb,
  risk_flags text[] not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table candidate_discoveries (
  candidate_id uuid not null references posting_candidates(id) on delete cascade,
  discovery_id uuid not null references discoveries(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (candidate_id, discovery_id)
);

create table candidate_evidence (
  candidate_id uuid not null references posting_candidates(id) on delete cascade,
  evidence_id uuid not null references evidence(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (candidate_id, evidence_id)
);

create table postings (
  id uuid primary key default gen_random_uuid(),
  candidate_id uuid unique references posting_candidates(id),
  title text not null,
  canonical_url text not null,
  normalized_url text not null,
  canonical_hash text not null,
  sector text,
  degree_level text,
  opportunity_kind text,
  organization_name text not null,
  country text,
  region text,
  city text,
  remote boolean not null default false,
  tags text[] not null default '{}',
  areas text[] not null default '{}',
  description_text text,
  application_url text,
  deadline timestamptz,
  source_refs jsonb not null default '[]'::jsonb,
  status posting_status not null default 'active',
  published_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index postings_canonical_hash_unique on postings(canonical_hash);
create index postings_status_updated_idx on postings(status, updated_at desc);
create index postings_search_idx on postings using gin (to_tsvector('english', coalesce(title, '') || ' ' || coalesce(organization_name, '')));

create table jobs (
  id uuid primary key default gen_random_uuid(),
  kind job_kind not null,
  target_type text not null,
  target_id uuid,
  inputs_json jsonb not null default '{}'::jsonb,
  status job_status not null default 'queued',
  attempt integer not null default 0,
  locked_by_module_id uuid references modules(id),
  locked_at timestamptz,
  lease_expires_at timestamptz,
  next_run_at timestamptz not null default now(),
  result_json jsonb,
  error_json jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index jobs_status_next_run_idx on jobs(status, next_run_at);
create index jobs_lock_expiry_idx on jobs(lease_expires_at);

create table provenance_events (
  id bigint generated by default as identity primary key,
  entity_type text not null,
  entity_id uuid,
  event_type text not null,
  actor_type text not null,
  actor_id uuid,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index provenance_entity_idx on provenance_events(entity_type, entity_id, created_at desc);

create table candidate_merge_decisions (
  id uuid primary key default gen_random_uuid(),
  primary_candidate_id uuid not null references posting_candidates(id),
  secondary_candidate_id uuid not null references posting_candidates(id),
  decision merge_decision not null,
  confidence numeric(5,4),
  decided_by text not null,
  rationale text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (primary_candidate_id, secondary_candidate_id)
);

create table submission_queue (
  id uuid primary key default gen_random_uuid(),
  submitted_by_user_id uuid not null,
  candidate_id uuid references posting_candidates(id),
  payload jsonb not null,
  status submission_status not null default 'queued',
  moderation_notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table source_trust_policy (
  id uuid primary key default gen_random_uuid(),
  source_key text not null unique,
  trust_level module_trust_level not null,
  auto_publish boolean not null default false,
  requires_moderation boolean not null default true,
  rules_json jsonb not null default '{}'::jsonb,
  enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create or replace function set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger modules_updated_at
before update on modules
for each row execute procedure set_updated_at();

create trigger discoveries_updated_at
before update on discoveries
for each row execute procedure set_updated_at();

create trigger candidates_updated_at
before update on posting_candidates
for each row execute procedure set_updated_at();

create trigger postings_updated_at
before update on postings
for each row execute procedure set_updated_at();

create trigger jobs_updated_at
before update on jobs
for each row execute procedure set_updated_at();

create trigger submission_queue_updated_at
before update on submission_queue
for each row execute procedure set_updated_at();

create trigger source_trust_policy_updated_at
before update on source_trust_policy
for each row execute procedure set_updated_at();
