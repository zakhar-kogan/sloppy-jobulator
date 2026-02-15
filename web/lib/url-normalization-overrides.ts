export type URLNormalizationOverride = {
  domain: string;
  strip_query_params: string[];
  strip_query_prefixes: string[];
  strip_www: boolean;
  force_https: boolean;
  enabled: boolean;
  created_at: string;
  updated_at: string;
};

export type URLNormalizationOverrideUpsertRequest = {
  strip_query_params: string[];
  strip_query_prefixes: string[];
  strip_www: boolean;
  force_https: boolean;
  enabled: boolean;
};

export type URLNormalizationOverrideEnabledPatchRequest = {
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
