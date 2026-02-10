export type ModuleTrustLevel = "trusted" | "semi_trusted" | "untrusted";

export type SourceTrustPolicy = {
  source_key: string;
  trust_level: ModuleTrustLevel;
  auto_publish: boolean;
  requires_moderation: boolean;
  rules_json: Record<string, unknown>;
  enabled: boolean;
  created_at: string;
  updated_at: string;
};

export type SourceTrustPolicyUpsertRequest = {
  trust_level: ModuleTrustLevel;
  auto_publish: boolean;
  requires_moderation: boolean;
  rules_json: Record<string, unknown>;
  enabled: boolean;
};

export type SourceTrustPolicyEnabledPatchRequest = {
  enabled: boolean;
};

type ApiErrorLike = {
  detail?: unknown;
};

export function getApiErrorDetail(payload: unknown, fallback: string): string {
  if (payload && typeof payload === "object") {
    const maybeError = payload as ApiErrorLike;
    if (typeof maybeError.detail === "string" && maybeError.detail.trim().length > 0) {
      return maybeError.detail;
    }
  }

  return fallback;
}
