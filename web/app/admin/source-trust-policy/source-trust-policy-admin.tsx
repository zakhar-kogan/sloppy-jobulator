"use client";

import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import {
  getApiErrorDetail,
  type ModuleTrustLevel,
  type SourceTrustPolicy
} from "../../../lib/source-trust-policy";

const TRUST_LEVEL_OPTIONS: ModuleTrustLevel[] = ["trusted", "semi_trusted", "untrusted"];

type EnabledFilter = "all" | "true" | "false";

function encodeListQuery(params: {
  sourceKey: string;
  enabled: EnabledFilter;
  trustLevel: "all" | ModuleTrustLevel;
  limit: number;
  offset: number;
}): string {
  const query = new URLSearchParams();

  if (params.sourceKey.trim().length > 0) {
    query.set("source_key", params.sourceKey.trim());
  }
  if (params.enabled !== "all") {
    query.set("enabled", params.enabled);
  }
  if (params.trustLevel !== "all") {
    query.set("trust_level", params.trustLevel);
  }

  query.set("limit", String(params.limit));
  query.set("offset", String(params.offset));

  return query.toString();
}

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) {
    return value;
  }

  return date.toLocaleString();
}

export function SourceTrustPolicyAdminClient(): JSX.Element {
  const [policies, setPolicies] = useState<SourceTrustPolicy[]>([]);
  const [loadingList, setLoadingList] = useState(false);
  const [listError, setListError] = useState<string | null>(null);

  const [sourceFilter, setSourceFilter] = useState("");
  const [enabledFilter, setEnabledFilter] = useState<EnabledFilter>("all");
  const [trustLevelFilter, setTrustLevelFilter] = useState<"all" | ModuleTrustLevel>("all");
  const [limit, setLimit] = useState(50);
  const [offset, setOffset] = useState(0);

  const [sourceKey, setSourceKey] = useState("");
  const [trustLevel, setTrustLevel] = useState<ModuleTrustLevel>("semi_trusted");
  const [autoPublish, setAutoPublish] = useState(false);
  const [enabled, setEnabled] = useState(true);

  const [formBusy, setFormBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [toggleBusyKey, setToggleBusyKey] = useState<string | null>(null);

  const queryString = useMemo(
    () =>
      encodeListQuery({
        sourceKey: sourceFilter,
        enabled: enabledFilter,
        trustLevel: trustLevelFilter,
        limit,
        offset
      }),
    [enabledFilter, limit, offset, sourceFilter, trustLevelFilter]
  );

  const loadPolicies = useCallback(async () => {
    setLoadingList(true);
    setListError(null);

    try {
      const response = await fetch(`/api/admin/source-trust-policy?${queryString}`, {
        method: "GET",
        cache: "no-store"
      });

      const payload: unknown = await response.json();
      if (!response.ok) {
        throw new Error(getApiErrorDetail(payload, "Failed to load source trust policies."));
      }
      if (!Array.isArray(payload)) {
        throw new Error("Source trust policy list response is invalid.");
      }

      setPolicies(payload as SourceTrustPolicy[]);
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Failed to load source trust policies.";
      setListError(detail);
      setPolicies([]);
    } finally {
      setLoadingList(false);
    }
  }, [queryString]);

  useEffect(() => {
    void loadPolicies();
  }, [loadPolicies]);

  async function handleUpsert(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setActionError(null);
    setMessage(null);

    const normalizedSourceKey = sourceKey.trim();
    if (!normalizedSourceKey) {
      setActionError("source_key is required.");
      return;
    }

    setFormBusy(true);

    try {
      const response = await fetch(`/api/admin/source-trust-policy/${encodeURIComponent(normalizedSourceKey)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          trust_level: trustLevel,
          auto_publish: autoPublish,
          requires_moderation: !autoPublish,
          rules_json: {},
          enabled
        })
      });

      const payload: unknown = await response.json();
      if (!response.ok) {
        throw new Error(getApiErrorDetail(payload, "Failed to upsert source trust policy."));
      }

      setMessage(`Saved policy for ${normalizedSourceKey}.`);
      await loadPolicies();
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Failed to upsert source trust policy.";
      setActionError(detail);
    } finally {
      setFormBusy(false);
    }
  }

  async function handleToggle(policy: SourceTrustPolicy): Promise<void> {
    setActionError(null);
    setMessage(null);
    setToggleBusyKey(policy.source_key);

    try {
      const response = await fetch(`/api/admin/source-trust-policy/${encodeURIComponent(policy.source_key)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: !policy.enabled })
      });

      const payload: unknown = await response.json();
      if (!response.ok) {
        throw new Error(getApiErrorDetail(payload, `Failed to toggle ${policy.source_key}.`));
      }

      setMessage(`Updated enabled=${String(!policy.enabled)} for ${policy.source_key}.`);
      await loadPolicies();
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Failed to toggle policy.";
      setActionError(detail);
    } finally {
      setToggleBusyKey(null);
    }
  }

  function loadPolicyIntoForm(policy: SourceTrustPolicy): void {
    setSourceKey(policy.source_key);
    setTrustLevel(policy.trust_level);
    setAutoPublish(policy.auto_publish);
    setEnabled(policy.enabled);
    setMessage(`Loaded ${policy.source_key} into form.`);
    setActionError(null);
  }

  return (
    <section className="admin-grid">
      <article className="panel">
        <h2>Policy Filters</h2>
        <div className="control-grid">
          <label className="control">
            <span>Source Key</span>
            <input
              value={sourceFilter}
              onChange={(event) => setSourceFilter(event.target.value)}
              placeholder="source:high-risk-feed"
            />
          </label>

          <label className="control">
            <span>Enabled</span>
            <select
              value={enabledFilter}
              onChange={(event) => setEnabledFilter(event.target.value as EnabledFilter)}
            >
              <option value="all">all</option>
              <option value="true">true</option>
              <option value="false">false</option>
            </select>
          </label>

          <label className="control">
            <span>Trust Level</span>
            <select
              value={trustLevelFilter}
              onChange={(event) => setTrustLevelFilter(event.target.value as "all" | ModuleTrustLevel)}
            >
              <option value="all">all</option>
              {TRUST_LEVEL_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
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
          <button className="button button-primary" onClick={() => void loadPolicies()} type="button">
            Refresh List
          </button>
          {loadingList ? <p className="status">Loading policies…</p> : null}
          {listError ? <p className="status status-error">{listError}</p> : null}
        </div>
      </article>

      <article className="panel">
        <h2>Upsert Policy</h2>
        <form onSubmit={(event) => void handleUpsert(event)} className="stack">
          <label className="control">
            <span>Source Key</span>
            <input
              value={sourceKey}
              onChange={(event) => setSourceKey(event.target.value)}
              placeholder="source:high-risk-feed"
              required
            />
          </label>

          <label className="control">
            <span>Trust Level</span>
            <select value={trustLevel} onChange={(event) => setTrustLevel(event.target.value as ModuleTrustLevel)}>
              {TRUST_LEVEL_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>

          <label className="checkbox-control">
            <input type="checkbox" checked={autoPublish} onChange={(event) => setAutoPublish(event.target.checked)} />
            <span>auto_publish</span>
          </label>

          <label className="checkbox-control">
            <input type="checkbox" checked={enabled} onChange={(event) => setEnabled(event.target.checked)} />
            <span>enabled</span>
          </label>
          <p className="status">
            Advanced policy rules are hidden in 80/20 mode. Queue routing uses default moderation behavior.
          </p>

          <div className="actions">
            <button className="button button-primary" type="submit" disabled={formBusy}>
              {formBusy ? "Saving…" : "Save Policy"}
            </button>
            {message ? <p className="status status-ok">{message}</p> : null}
            {actionError ? <p className="status status-error">{actionError}</p> : null}
          </div>
        </form>
      </article>

      <article className="panel panel-wide">
        <h2>Policies</h2>
        {policies.length === 0 ? (
          <p className="status">No policies matched current filters.</p>
        ) : (
          <div className="table-wrap">
            <table className="policy-table">
              <thead>
                <tr>
                  <th>Source Key</th>
                  <th>Trust</th>
                  <th>Enabled</th>
                  <th>Auto Publish</th>
                  <th>Requires Moderation</th>
                  <th>Updated</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {policies.map((policy) => {
                  const toggleBusy = toggleBusyKey === policy.source_key;
                  return (
                    <tr key={policy.source_key}>
                      <td>{policy.source_key}</td>
                      <td>{policy.trust_level}</td>
                      <td>{String(policy.enabled)}</td>
                      <td>{String(policy.auto_publish)}</td>
                      <td>{String(policy.requires_moderation)}</td>
                      <td>{formatTimestamp(policy.updated_at)}</td>
                      <td>
                        <div className="row-actions">
                          <button
                            className="button"
                            type="button"
                            onClick={() => loadPolicyIntoForm(policy)}
                            disabled={toggleBusy}
                          >
                            Edit
                          </button>
                          <button
                            className="button button-ghost"
                            type="button"
                            onClick={() => void handleToggle(policy)}
                            disabled={toggleBusy}
                          >
                            {toggleBusy ? "Updating…" : policy.enabled ? "Disable" : "Enable"}
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
