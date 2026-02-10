export type CandidateState =
  | "discovered"
  | "processed"
  | "publishable"
  | "published"
  | "rejected"
  | "closed"
  | "archived"
  | "needs_review";

export type PostingStatus = "active" | "stale" | "archived" | "closed";

export type Candidate = {
  id: string;
  state: CandidateState;
  dedupe_confidence: number | null;
  risk_flags: string[];
  extracted_fields: Record<string, unknown>;
  discovery_ids: string[];
  posting_id: string | null;
  created_at: string;
  updated_at: string;
};

export type ModuleKind = "connector" | "processor";
export type ModuleTrustLevel = "trusted" | "semi_trusted" | "untrusted";

export type AdminModule = {
  id: string;
  module_id: string;
  name: string;
  kind: ModuleKind;
  enabled: boolean;
  scopes: string[];
  trust_level: ModuleTrustLevel;
  created_at: string;
  updated_at: string;
};

export type JobStatus = "queued" | "claimed" | "done" | "failed" | "dead_letter";
export type JobKind = "dedupe" | "extract" | "enrich" | "check_freshness" | "resolve_url_redirects";

export type AdminJob = {
  id: string;
  kind: JobKind;
  target_type: string;
  target_id: string | null;
  status: JobStatus;
  attempt: number;
  locked_by_module_id: string | null;
  lease_expires_at: string | null;
  next_run_at: string;
  created_at: string;
  updated_at: string;
};

export type AdminCountResult = {
  count: number;
};

export function getApiErrorDetail(payload: unknown, fallback: string): string {
  if (payload && typeof payload === "object") {
    const maybeError = payload as { detail?: unknown };
    if (typeof maybeError.detail === "string" && maybeError.detail.trim().length > 0) {
      return maybeError.detail;
    }
  }

  return fallback;
}

export function formatTimestamp(value: string | null): string {
  if (!value) {
    return "-";
  }

  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) {
    return value;
  }

  return date.toLocaleString();
}

export function coerceTitle(extractedFields: Record<string, unknown>): string {
  const candidate = extractedFields.title;
  if (typeof candidate === "string" && candidate.trim().length > 0) {
    return candidate.trim();
  }
  return "Untitled candidate";
}
