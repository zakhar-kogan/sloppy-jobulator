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
