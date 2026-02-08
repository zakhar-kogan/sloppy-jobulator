-- Bootstrap defaults for v1.

insert into source_trust_policy (source_key, trust_level, auto_publish, requires_moderation, rules_json)
values
  ('default:trusted', 'trusted', true, false, '{"min_confidence": 0.95}'::jsonb),
  ('default:semi_trusted', 'semi_trusted', true, true, '{"min_confidence": 0.98, "allow_if_no_conflicts": true}'::jsonb),
  ('default:untrusted', 'untrusted', false, true, '{"require_human_review": true}'::jsonb)
on conflict (source_key) do nothing;
