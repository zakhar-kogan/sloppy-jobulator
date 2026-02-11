import type { CandidateState } from "./admin-cockpit";

const ALLOWED_CANDIDATE_TRANSITIONS: Record<CandidateState, readonly CandidateState[]> = {
  discovered: ["processed", "needs_review", "rejected", "archived"],
  processed: ["publishable", "needs_review", "rejected", "archived"],
  needs_review: ["publishable", "rejected", "archived", "processed"],
  publishable: ["published", "rejected", "needs_review", "archived"],
  published: ["archived", "closed"],
  archived: ["published", "closed"],
  closed: ["archived"],
  rejected: ["needs_review", "archived"]
};

export function encodeAdminQuery(params: Record<string, string | number | boolean | null | undefined>): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) {
      continue;
    }
    if (typeof value === "string" && value.trim().length === 0) {
      continue;
    }
    query.set(key, String(value));
  }
  return query.toString();
}

export function parseAdminCount(payload: unknown): number {
  if (!payload || typeof payload !== "object") {
    return 0;
  }

  const count = (payload as { count?: unknown }).count;
  if (typeof count === "number" && Number.isFinite(count)) {
    return count;
  }

  return 0;
}

export function coerceBoundedInteger(
  rawValue: string,
  options: {
    min: number;
    max: number;
    fallback: number;
  }
): number {
  const { min, max, fallback } = options;
  const parsed = Number(rawValue);
  if (!Number.isFinite(parsed)) {
    return fallback;
  }

  const normalized = Math.trunc(parsed);
  return Math.min(max, Math.max(min, normalized));
}

export function canTransitionCandidateState(fromState: CandidateState, toState: CandidateState): boolean {
  if (fromState === toState) {
    return true;
  }

  return ALLOWED_CANDIDATE_TRANSITIONS[fromState].includes(toState);
}

export function listPatchCandidateStates(
  fromState: CandidateState | null,
  allStates: readonly CandidateState[]
): CandidateState[] {
  if (!fromState) {
    return [...allStates];
  }

  return allStates.filter((candidateState) => canTransitionCandidateState(fromState, candidateState));
}
