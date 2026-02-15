"use client";

import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import {
  getApiErrorDetail,
  type URLNormalizationOverride,
} from "../../../lib/url-normalization-overrides";

type EnabledFilter = "all" | "true" | "false";

function encodeListQuery(params: {
  domain: string;
  enabled: EnabledFilter;
  limit: number;
  offset: number;
}): string {
  const query = new URLSearchParams();

  if (params.domain.trim().length > 0) {
    query.set("domain", params.domain.trim());
  }
  if (params.enabled !== "all") {
    query.set("enabled", params.enabled);
  }
  query.set("limit", String(params.limit));
  query.set("offset", String(params.offset));
  return query.toString();
}

function parseCsv(value: string): string[] {
  return value
    .split(",")
    .map((token) => token.trim())
    .filter((token) => token.length > 0);
}

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) {
    return value;
  }
  return date.toLocaleString();
}

export function URLNormalizationOverridesAdminClient(): JSX.Element {
  const [rows, setRows] = useState<URLNormalizationOverride[]>([]);
  const [loadingList, setLoadingList] = useState(false);
  const [listError, setListError] = useState<string | null>(null);

  const [domainFilter, setDomainFilter] = useState("");
  const [enabledFilter, setEnabledFilter] = useState<EnabledFilter>("all");
  const [limit, setLimit] = useState(50);
  const [offset, setOffset] = useState(0);

  const [domain, setDomain] = useState("");
  const [stripQueryParams, setStripQueryParams] = useState("");
  const [stripQueryPrefixes, setStripQueryPrefixes] = useState("");
  const [stripWww, setStripWww] = useState(false);
  const [forceHttps, setForceHttps] = useState(false);
  const [enabled, setEnabled] = useState(true);

  const [formBusy, setFormBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [toggleBusyDomain, setToggleBusyDomain] = useState<string | null>(null);

  const queryString = useMemo(
    () =>
      encodeListQuery({
        domain: domainFilter,
        enabled: enabledFilter,
        limit,
        offset
      }),
    [domainFilter, enabledFilter, limit, offset]
  );

  const loadRows = useCallback(async () => {
    setLoadingList(true);
    setListError(null);
    try {
      const response = await fetch(`/api/admin/url-normalization-overrides?${queryString}`, {
        method: "GET",
        cache: "no-store"
      });
      const payload: unknown = await response.json();
      if (!response.ok) {
        throw new Error(getApiErrorDetail(payload, "Failed to load URL normalization overrides."));
      }
      if (!Array.isArray(payload)) {
        throw new Error("URL normalization override list response is invalid.");
      }
      setRows(payload as URLNormalizationOverride[]);
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Failed to load URL normalization overrides.";
      setListError(detail);
      setRows([]);
    } finally {
      setLoadingList(false);
    }
  }, [queryString]);

  useEffect(() => {
    void loadRows();
  }, [loadRows]);

  async function handleUpsert(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setActionError(null);
    setMessage(null);

    const normalizedDomain = domain.trim().toLowerCase();
    if (!normalizedDomain) {
      setActionError("domain is required.");
      return;
    }

    setFormBusy(true);
    try {
      const response = await fetch(`/api/admin/url-normalization-overrides/${encodeURIComponent(normalizedDomain)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          strip_query_params: parseCsv(stripQueryParams),
          strip_query_prefixes: parseCsv(stripQueryPrefixes),
          strip_www: stripWww,
          force_https: forceHttps,
          enabled
        })
      });
      const payload: unknown = await response.json();
      if (!response.ok) {
        throw new Error(getApiErrorDetail(payload, "Failed to upsert URL normalization override."));
      }
      setMessage(`Saved override for ${normalizedDomain}.`);
      await loadRows();
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Failed to upsert URL normalization override.";
      setActionError(detail);
    } finally {
      setFormBusy(false);
    }
  }

  async function handleToggle(row: URLNormalizationOverride): Promise<void> {
    setActionError(null);
    setMessage(null);
    setToggleBusyDomain(row.domain);
    try {
      const response = await fetch(`/api/admin/url-normalization-overrides/${encodeURIComponent(row.domain)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: !row.enabled })
      });
      const payload: unknown = await response.json();
      if (!response.ok) {
        throw new Error(getApiErrorDetail(payload, `Failed to toggle ${row.domain}.`));
      }
      setMessage(`Updated enabled=${String(!row.enabled)} for ${row.domain}.`);
      await loadRows();
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Failed to toggle override.";
      setActionError(detail);
    } finally {
      setToggleBusyDomain(null);
    }
  }

  function loadIntoForm(row: URLNormalizationOverride): void {
    setDomain(row.domain);
    setStripQueryParams(row.strip_query_params.join(", "));
    setStripQueryPrefixes(row.strip_query_prefixes.join(", "));
    setStripWww(row.strip_www);
    setForceHttps(row.force_https);
    setEnabled(row.enabled);
    setMessage(`Loaded ${row.domain} into form.`);
    setActionError(null);
  }

  return (
    <section className="admin-grid">
      <article className="panel">
        <h2>Override Filters</h2>
        <div className="control-grid">
          <label className="control">
            <span>Domain</span>
            <input
              value={domainFilter}
              onChange={(event) => setDomainFilter(event.target.value)}
              placeholder="example.edu"
            />
          </label>

          <label className="control">
            <span>Enabled</span>
            <select value={enabledFilter} onChange={(event) => setEnabledFilter(event.target.value as EnabledFilter)}>
              <option value="all">all</option>
              <option value="true">true</option>
              <option value="false">false</option>
            </select>
          </label>

          <label className="control">
            <span>Limit</span>
            <input
              value={limit}
              onChange={(event) => setLimit(Number(event.target.value) || 1)}
              type="number"
              min={1}
              max={200}
            />
          </label>

          <label className="control">
            <span>Offset</span>
            <input
              value={offset}
              onChange={(event) => setOffset(Math.max(0, Number(event.target.value) || 0))}
              type="number"
              min={0}
            />
          </label>
        </div>

        <div className="actions">
          <button className="button button-primary" onClick={() => void loadRows()} type="button">
            Refresh List
          </button>
          {loadingList ? <p className="status">Loading overrides…</p> : null}
          {listError ? <p className="status status-error">{listError}</p> : null}
        </div>
      </article>

      <article className="panel">
        <h2>Upsert Override</h2>
        <form onSubmit={(event) => void handleUpsert(event)} className="stack">
          <label className="control">
            <span>Domain</span>
            <input
              value={domain}
              onChange={(event) => setDomain(event.target.value)}
              placeholder="example.edu"
              required
            />
          </label>

          <label className="control">
            <span>strip_query_params (comma-separated)</span>
            <input
              value={stripQueryParams}
              onChange={(event) => setStripQueryParams(event.target.value)}
              placeholder="sessionid, token"
            />
          </label>

          <label className="control">
            <span>strip_query_prefixes (comma-separated)</span>
            <input
              value={stripQueryPrefixes}
              onChange={(event) => setStripQueryPrefixes(event.target.value)}
              placeholder="cmp_, trk_"
            />
          </label>

          <label className="checkbox-control">
            <input type="checkbox" checked={stripWww} onChange={(event) => setStripWww(event.target.checked)} />
            <span>strip_www</span>
          </label>

          <label className="checkbox-control">
            <input type="checkbox" checked={forceHttps} onChange={(event) => setForceHttps(event.target.checked)} />
            <span>force_https</span>
          </label>

          <label className="checkbox-control">
            <input type="checkbox" checked={enabled} onChange={(event) => setEnabled(event.target.checked)} />
            <span>enabled</span>
          </label>

          <div className="actions">
            <button className="button button-primary" type="submit" disabled={formBusy}>
              {formBusy ? "Saving…" : "Save Override"}
            </button>
            {message ? <p className="status status-ok">{message}</p> : null}
            {actionError ? <p className="status status-error">{actionError}</p> : null}
          </div>
        </form>
      </article>

      <article className="panel panel-wide">
        <h2>Overrides</h2>
        {rows.length === 0 ? (
          <p className="status">No overrides matched current filters.</p>
        ) : (
          <div className="table-wrap">
            <table className="policy-table">
              <thead>
                <tr>
                  <th>Domain</th>
                  <th>Enabled</th>
                  <th>strip_www</th>
                  <th>force_https</th>
                  <th>strip_query_params</th>
                  <th>strip_query_prefixes</th>
                  <th>Updated</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => {
                  const toggleBusy = toggleBusyDomain === row.domain;
                  return (
                    <tr key={row.domain}>
                      <td>{row.domain}</td>
                      <td>{String(row.enabled)}</td>
                      <td>{String(row.strip_www)}</td>
                      <td>{String(row.force_https)}</td>
                      <td>{row.strip_query_params.join(", ") || "—"}</td>
                      <td>{row.strip_query_prefixes.join(", ") || "—"}</td>
                      <td>{formatTimestamp(row.updated_at)}</td>
                      <td>
                        <div className="row-actions">
                          <button className="button" type="button" onClick={() => loadIntoForm(row)} disabled={toggleBusy}>
                            Edit
                          </button>
                          <button
                            className="button button-ghost"
                            type="button"
                            onClick={() => void handleToggle(row)}
                            disabled={toggleBusy}
                          >
                            {toggleBusy ? "Updating…" : row.enabled ? "Disable" : "Enable"}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </article>
    </section>
  );
}
