"use client";

import { useEffect, useMemo, useState } from "react";

type PostingStatus = "active" | "stale" | "archived" | "closed";
type SortBy = "created_at" | "updated_at" | "deadline" | "published_at";
type SortDir = "asc" | "desc";

type PostingListRow = {
  id: string;
  title: string;
  organization_name: string;
  canonical_url: string;
  status: PostingStatus;
  country: string | null;
  remote: boolean;
  tags: string[];
  updated_at: string;
  created_at: string;
};

type PostingDetail = {
  id: string;
  title: string;
  canonical_url: string;
  organization_name: string;
  status: PostingStatus;
  country: string | null;
  city: string | null;
  region: string | null;
  remote: boolean;
  tags: string[];
  areas: string[];
  description_text: string | null;
  application_url: string | null;
  deadline: string | null;
  published_at: string | null;
  updated_at: string;
};

type RemoteFilter = "all" | "remote" | "onsite";
type StatusFilter = "all" | PostingStatus;

function encodeQuery(params: Record<string, string | number | boolean | undefined>): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined) {
      continue;
    }
    if (typeof value === "string" && value.trim().length === 0) {
      continue;
    }
    query.set(key, String(value));
  }
  return query.toString();
}

function formatTimestamp(value: string | null): string {
  if (!value) {
    return "-";
  }
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) {
    return value;
  }
  return new Date(parsed).toLocaleString();
}

function getApiErrorDetail(payload: unknown, fallback: string): string {
  if (payload && typeof payload === "object") {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === "string" && detail.trim().length > 0) {
      return detail;
    }
  }
  return fallback;
}

export function PublicCatalogueClient(): JSX.Element {
  const [q, setQ] = useState("");
  const [organization, setOrganization] = useState("");
  const [country, setCountry] = useState("");
  const [tag, setTag] = useState("");
  const [remoteFilter, setRemoteFilter] = useState<RemoteFilter>("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("active");
  const [sortBy, setSortBy] = useState<SortBy>("updated_at");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [limit, setLimit] = useState(20);
  const [offset, setOffset] = useState(0);

  const [rows, setRows] = useState<PostingListRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedPostingId, setSelectedPostingId] = useState<string | null>(null);
  const [detailById, setDetailById] = useState<Record<string, PostingDetail>>({});
  const [detailLoadingId, setDetailLoadingId] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);

  const queryString = useMemo(
    () =>
      encodeQuery({
        q,
        organization_name: organization,
        country,
        tag,
        remote: remoteFilter === "all" ? undefined : remoteFilter === "remote",
        status: statusFilter === "all" ? undefined : statusFilter,
        sort_by: sortBy,
        sort_dir: sortDir,
        limit,
        offset
      }),
    [country, limit, offset, organization, q, remoteFilter, sortBy, sortDir, statusFilter, tag]
  );

  useEffect(() => {
    let isCancelled = false;

    async function run(): Promise<void> {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`/api/postings?${queryString}`, {
          method: "GET",
          cache: "no-store"
        });
        const payload: unknown = await response.json();
        if (!response.ok) {
          throw new Error(getApiErrorDetail(payload, "Failed to load postings."));
        }
        if (!Array.isArray(payload)) {
          throw new Error("Postings response is invalid.");
        }
        if (!isCancelled) {
          setRows(payload as PostingListRow[]);
          if (selectedPostingId && !(payload as PostingListRow[]).some((row) => row.id === selectedPostingId)) {
            setSelectedPostingId(null);
            setDetailError(null);
          }
        }
      } catch (fetchError) {
        const detail = fetchError instanceof Error ? fetchError.message : "Failed to load postings.";
        if (!isCancelled) {
          setError(detail);
          setRows([]);
        }
      } finally {
        if (!isCancelled) {
          setLoading(false);
        }
      }
    }

    void run();
    return () => {
      isCancelled = true;
    };
  }, [queryString, selectedPostingId]);

  const selectedDetail = selectedPostingId ? detailById[selectedPostingId] : null;

  async function openPostingPreview(postingId: string): Promise<void> {
    setSelectedPostingId(postingId);
    setDetailError(null);
    if (detailById[postingId]) {
      return;
    }

    setDetailLoadingId(postingId);
    try {
      const response = await fetch(`/api/postings/${encodeURIComponent(postingId)}`, {
        method: "GET",
        cache: "no-store"
      });
      const payload: unknown = await response.json();
      if (!response.ok) {
        throw new Error(getApiErrorDetail(payload, "Failed to load posting detail."));
      }
      setDetailById((previous) => ({
        ...previous,
        [postingId]: payload as PostingDetail
      }));
    } catch (detailErrorValue) {
      const detail = detailErrorValue instanceof Error ? detailErrorValue.message : "Failed to load posting detail.";
      setDetailError(detail);
    } finally {
      setDetailLoadingId(null);
    }
  }

  function handleResetFilters(): void {
    setQ("");
    setOrganization("");
    setCountry("");
    setTag("");
    setRemoteFilter("all");
    setStatusFilter("active");
    setSortBy("updated_at");
    setSortDir("desc");
    setLimit(20);
    setOffset(0);
  }

  return (
    <section className="catalogue-shell">
      <div className="controls">
        <label className="control">
          <span>Search</span>
          <input
            value={q}
            onChange={(event) => {
              setQ(event.target.value);
              setOffset(0);
            }}
            placeholder="keyword, organization, description"
          />
        </label>

        <label className="control">
          <span>Organization</span>
          <input
            value={organization}
            onChange={(event) => {
              setOrganization(event.target.value);
              setOffset(0);
            }}
            placeholder="e.g., University"
          />
        </label>

        <label className="control">
          <span>Country</span>
          <input
            value={country}
            onChange={(event) => {
              setCountry(event.target.value);
              setOffset(0);
            }}
            placeholder="e.g., US"
          />
        </label>

        <label className="control">
          <span>Tag</span>
          <input
            value={tag}
            onChange={(event) => {
              setTag(event.target.value);
              setOffset(0);
            }}
            placeholder="e.g., biology"
          />
        </label>

        <label className="control">
          <span>Remote</span>
          <select
            value={remoteFilter}
            onChange={(event) => {
              setRemoteFilter(event.target.value as RemoteFilter);
              setOffset(0);
            }}
          >
            <option value="all">all</option>
            <option value="remote">remote</option>
            <option value="onsite">onsite</option>
          </select>
        </label>

        <label className="control">
          <span>Status</span>
          <select
            value={statusFilter}
            onChange={(event) => {
              setStatusFilter(event.target.value as StatusFilter);
              setOffset(0);
            }}
          >
            <option value="all">all</option>
            <option value="active">active</option>
            <option value="stale">stale</option>
            <option value="archived">archived</option>
            <option value="closed">closed</option>
          </select>
        </label>

        <label className="control">
          <span>Sort By</span>
          <select
            value={sortBy}
            onChange={(event) => {
              setSortBy(event.target.value as SortBy);
              setOffset(0);
            }}
          >
            <option value="updated_at">updated_at</option>
            <option value="created_at">created_at</option>
            <option value="deadline">deadline</option>
            <option value="published_at">published_at</option>
          </select>
        </label>

        <label className="control">
          <span>Direction</span>
          <select
            value={sortDir}
            onChange={(event) => {
              setSortDir(event.target.value as SortDir);
              setOffset(0);
            }}
          >
            <option value="desc">desc</option>
            <option value="asc">asc</option>
          </select>
        </label>

        <label className="control">
          <span>Page Size</span>
          <select
            value={limit}
            onChange={(event) => {
              setLimit(Number(event.target.value));
              setOffset(0);
            }}
          >
            <option value={10}>10</option>
            <option value={20}>20</option>
            <option value={50}>50</option>
          </select>
        </label>
      </div>

      <div className="actions">
        <button className="button" type="button" onClick={handleResetFilters}>
          Reset Filters
        </button>
        <button
          className="button"
          type="button"
          onClick={() => setOffset((previous) => Math.max(0, previous - limit))}
          disabled={loading || offset === 0}
        >
          Previous
        </button>
        <button
          className="button"
          type="button"
          onClick={() => setOffset((previous) => previous + limit)}
          disabled={loading || rows.length < limit}
        >
          Next
        </button>
        <p className="status">Offset {offset} · Showing {rows.length} row(s)</p>
      </div>

      {loading ? <p className="status">Loading postings…</p> : null}
      {error ? <p className="status status-error">{error}</p> : null}

      <section className="grid" aria-label="posting list">
        {!loading && !error && rows.length === 0 ? (
          <article className="card">
            <h3>No matches found</h3>
            <p className="status">Try broader search terms or reset filters.</p>
          </article>
        ) : null}

        {rows.map((row) => (
          <article className="card" key={row.id}>
            <h3>{row.title}</h3>
            <p className="status">
              {row.organization_name}
              {row.country ? ` · ${row.country}` : ""}
              {row.remote ? " · remote" : ""}
            </p>
            <p className="status">Updated {formatTimestamp(row.updated_at)}</p>
            <div className="tag-row">
              {row.tags.slice(0, 4).map((item) => (
                <span key={`${row.id}-${item}`} className="badge">
                  {item}
                </span>
              ))}
              <span className="badge">{row.status}</span>
            </div>
            <div className="row-actions">
              <a className="inline-link" href={row.canonical_url} target="_blank" rel="noreferrer">
                Open source
              </a>
              <button className="button button-ghost" type="button" onClick={() => void openPostingPreview(row.id)}>
                Preview
              </button>
            </div>
          </article>
        ))}
      </section>

      {selectedPostingId ? (
        <article className="card detail-card">
          <h3>Posting Preview</h3>
          {detailLoadingId === selectedPostingId ? <p className="status">Loading detail…</p> : null}
          {detailError ? <p className="status status-error">{detailError}</p> : null}
          {selectedDetail ? (
            <>
              <p>
                <strong>{selectedDetail.title}</strong>
              </p>
              <p className="status">
                {selectedDetail.organization_name}
                {selectedDetail.country ? ` · ${selectedDetail.country}` : ""}
                {selectedDetail.region ? ` · ${selectedDetail.region}` : ""}
                {selectedDetail.city ? ` · ${selectedDetail.city}` : ""}
              </p>
              <p className="status">Status: {selectedDetail.status}</p>
              <p className="status">Deadline: {formatTimestamp(selectedDetail.deadline)}</p>
              <p className="status">Published: {formatTimestamp(selectedDetail.published_at)}</p>
              <p className="status">Updated: {formatTimestamp(selectedDetail.updated_at)}</p>
              {selectedDetail.description_text ? <p>{selectedDetail.description_text}</p> : null}
              <div className="tag-row">
                {selectedDetail.tags.map((item) => (
                  <span key={`${selectedDetail.id}-detail-${item}`} className="badge">
                    {item}
                  </span>
                ))}
              </div>
              {selectedDetail.application_url ? (
                <p>
                  <a className="inline-link" href={selectedDetail.application_url} target="_blank" rel="noreferrer">
                    Apply
                  </a>
                </p>
              ) : null}
            </>
          ) : null}
        </article>
      ) : null}
    </section>
  );
}
