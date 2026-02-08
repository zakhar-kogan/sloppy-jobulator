-- Bootstrap defaults for v1.

insert into source_trust_policy (source_key, trust_level, auto_publish, requires_moderation, rules_json)
values
  ('default:trusted', 'trusted', true, false, '{"min_confidence": 0.95}'::jsonb),
  ('default:semi_trusted', 'semi_trusted', true, true, '{"min_confidence": 0.98, "allow_if_no_conflicts": true}'::jsonb),
  ('default:untrusted', 'untrusted', false, true, '{"require_human_review": true}'::jsonb)
on conflict (source_key) do nothing;

-- Local development modules + machine credentials.
-- Raw local keys:
-- - local-connector-key
-- - local-processor-key
insert into modules (module_id, name, kind, enabled, scopes, trust_level)
values
  ('local-connector', 'Local Connector', 'connector', true, array['discoveries:write', 'evidence:write'], 'trusted'),
  ('local-processor', 'Local Processor', 'processor', true, array['jobs:read', 'jobs:write'], 'trusted')
on conflict (module_id) do update
set
  name = excluded.name,
  kind = excluded.kind,
  enabled = excluded.enabled,
  scopes = excluded.scopes,
  trust_level = excluded.trust_level;

insert into module_credentials (module_id, key_hint, key_hash, is_active)
select
  m.id,
  c.key_hint,
  c.key_hash,
  true
from modules m
join (
  values
    ('local-connector', 'local-connector', 'a061dd1a62bc85bc23d5625af753a75aec0d8f9e8e0ab21d4161ce1c6bd6a6d0'),
    ('local-processor', 'local-processor', 'e64d946e424d9cce9cdc8f8d346391e584599ab1c0f2aac2ea22d88e24e6d517')
) as c(module_id, key_hint, key_hash)
  on c.module_id = m.module_id
on conflict (module_id, key_hint) do update
set
  key_hash = excluded.key_hash,
  is_active = true,
  revoked_at = null;
