function withOptionalQuery(path: string, requestUrl: string): string {
  const query = new URL(requestUrl).searchParams.toString();
  return query ? `${path}?${query}` : path;
}

export function buildPostingsListPath(requestUrl: string): string {
  return withOptionalQuery("/postings", requestUrl);
}

export function buildPostingDetailPath(postingId: string): string {
  return `/postings/${encodeURIComponent(postingId)}`;
}
