function withOptionalQuery(path: string, requestUrl: string): string {
  const query = new URL(requestUrl).searchParams.toString();
  return query ? `${path}?${query}` : path;
}

export function buildCandidatesListPath(requestUrl: string): string {
  return withOptionalQuery("/candidates", requestUrl);
}

export function buildCandidatePatchPath(candidateId: string): string {
  return `/candidates/${encodeURIComponent(candidateId)}`;
}

export function buildCandidateMergePath(candidateId: string): string {
  return `/candidates/${encodeURIComponent(candidateId)}/merge`;
}

export function buildCandidateOverridePath(candidateId: string): string {
  return `/candidates/${encodeURIComponent(candidateId)}/override`;
}

export function buildModulesListPath(requestUrl: string): string {
  return withOptionalQuery("/admin/modules", requestUrl);
}

export function buildModulePatchPath(moduleId: string): string {
  return `/admin/modules/${encodeURIComponent(moduleId)}`;
}

export function buildJobsListPath(requestUrl: string): string {
  return withOptionalQuery("/admin/jobs", requestUrl);
}

export function buildJobsReapExpiredPath(requestUrl: string): string {
  return withOptionalQuery("/admin/jobs/reap-expired", requestUrl);
}

export function buildJobsEnqueueFreshnessPath(requestUrl: string): string {
  return withOptionalQuery("/admin/jobs/enqueue-freshness", requestUrl);
}
