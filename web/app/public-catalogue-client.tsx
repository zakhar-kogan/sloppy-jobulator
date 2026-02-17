"use client";

import { useEffect, useMemo, useState } from "react";

type PostingStatus = "active" | "stale" | "archived" | "closed";

type PostingListRow = {
  id: string;
  title: string;
  organization_name: string;
  opportunity_kind: string | null;
  areas: string[];
  description_text: string | null;
  canonical_url: string;
  status: PostingStatus;
  country: string | null;
  remote: boolean;
  tags: string[];
  updated_at: string;
  created_at: string;
};

type FilterDropdownProps = {
  label: string;
  options: string[];
  selected: string[];
  onSelectedChange: (next: string[]) => void;
};

function formatDate(value: string | null): string {
  if (!value) return "-";
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) return value;
  return new Date(parsed).toLocaleDateString();
}

function disciplineForRow(row: PostingListRow): string {
  return row.areas[0] ?? row.tags[0] ?? "-";
}

function postingTypeForRow(row: PostingListRow): string {
  return row.opportunity_kind ?? (row.remote ? "remote" : "unspecified");
}

function FilterDropdown({ label, options, selected, onSelectedChange }: FilterDropdownProps): JSX.Element {
  const allSelected = selected.length === 0 || selected.length === options.length;

  function toggle(value: string): void {
    const exists = selected.includes(value);
    if (exists) {
      onSelectedChange(selected.filter((item) => item !== value));
      return;
    }
    onSelectedChange([...selected, value]);
  }

  return (
    <details className="table-filter">
      <summary>{label}</summary>
      <div className="table-filter-menu">
        <label className="table-filter-option">
          <input
            type="checkbox"
            checked={allSelected}
            onChange={() => {
              onSelectedChange([]);
            }}
          />
          (Select All)
        </label>
        {options.map((option) => (
          <label className="table-filter-option" key={`${label}-${option}`}>
            <input type="checkbox" checked={selected.includes(option)} onChange={() => toggle(option)} />
            {option}
          </label>
        ))}
      </div>
    </details>
  );
}

export function PublicCatalogueClient(): JSX.Element {
  const [rows, setRows] = useState<PostingListRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pageSize, setPageSize] = useState(20);
  const [page, setPage] = useState(0);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const [disciplineFilter, setDisciplineFilter] = useState<string[]>([]);
  const [countryFilter, setCountryFilter] = useState<string[]>([]);
  const [typeFilter, setTypeFilter] = useState<string[]>([]);
  const [authorFilter, setAuthorFilter] = useState<string[]>([]);
  const [statusFilter, setStatusFilter] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    void fetch("/api/postings?limit=100&sort_by=updated_at&sort_dir=desc", { cache: "no-store" })
      .then(async (response) => {
        const payload: unknown = await response.json();
        if (!response.ok) {
          throw new Error("Failed to load postings.");
        }
        if (!Array.isArray(payload)) {
          throw new Error("Invalid postings payload.");
        }
        if (!cancelled) setRows(payload as PostingListRow[]);
      })
      .catch((fetchError: unknown) => {
        if (!cancelled) {
          setRows([]);
          setError(fetchError instanceof Error ? fetchError.message : "Failed to load postings.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const disciplineOptions = useMemo(
    () => Array.from(new Set(rows.map((row) => disciplineForRow(row)))).sort((a, b) => a.localeCompare(b)),
    [rows]
  );
  const countryOptions = useMemo(
    () => Array.from(new Set(rows.map((row) => row.country ?? "-"))).sort((a, b) => a.localeCompare(b)),
    [rows]
  );
  const typeOptions = useMemo(
    () => Array.from(new Set(rows.map((row) => postingTypeForRow(row)))).sort((a, b) => a.localeCompare(b)),
    [rows]
  );
  const authorOptions = useMemo(
    () => Array.from(new Set(rows.map((row) => row.organization_name))).sort((a, b) => a.localeCompare(b)),
    [rows]
  );
  const statusOptions = ["active", "stale", "archived", "closed"];

  const filteredRows = useMemo(
    () =>
      rows.filter((row) => {
        const discipline = disciplineForRow(row);
        const country = row.country ?? "-";
        const postingType = postingTypeForRow(row);
        return (
          (disciplineFilter.length === 0 || disciplineFilter.includes(discipline)) &&
          (countryFilter.length === 0 || countryFilter.includes(country)) &&
          (typeFilter.length === 0 || typeFilter.includes(postingType)) &&
          (authorFilter.length === 0 || authorFilter.includes(row.organization_name)) &&
          (statusFilter.length === 0 || statusFilter.includes(row.status))
        );
      }),
    [authorFilter, countryFilter, disciplineFilter, rows, statusFilter, typeFilter]
  );

  const pageCount = Math.max(1, Math.ceil(filteredRows.length / pageSize));
  const safePage = Math.min(page, pageCount - 1);
  const pagedRows = filteredRows.slice(safePage * pageSize, safePage * pageSize + pageSize);

  function toggleExpanded(id: string): void {
    setExpandedIds((previous) => {
      const next = new Set(previous);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function shortDescription(row: PostingListRow): JSX.Element {
    const text = row.description_text?.trim() ?? "";
    if (!text) return <span>-</span>;
    const expanded = expandedIds.has(row.id);
    const isLong = text.length > 120;
    if (!isLong) return <span>{text}</span>;
    return (
      <span>
        {expanded ? text : `${text.slice(0, 117)}...`}{" "}
        <button className="inline-button" type="button" onClick={() => toggleExpanded(row.id)}>
          {expanded ? "less" : "more"}
        </button>
      </span>
    );
  }

  return (
    <section className="catalogue-shell">
      <div className="table-filter-bar">
        <FilterDropdown label="Discipline" options={disciplineOptions} selected={disciplineFilter} onSelectedChange={setDisciplineFilter} />
        <FilterDropdown label="Country" options={countryOptions} selected={countryFilter} onSelectedChange={setCountryFilter} />
        <FilterDropdown label="Posting Type" options={typeOptions} selected={typeFilter} onSelectedChange={setTypeFilter} />
        <FilterDropdown label="Author" options={authorOptions} selected={authorFilter} onSelectedChange={setAuthorFilter} />
        <FilterDropdown label="Status" options={statusOptions} selected={statusFilter} onSelectedChange={setStatusFilter} />
      </div>

      {loading ? <p className="status">Loading postings…</p> : null}
      {error ? <p className="status status-error">{error}</p> : null}

      <section className="table-wrap" aria-label="posting list">
        {!loading && !error && filteredRows.length === 0 ? <p className="status">No matches found.</p> : null}
        {filteredRows.length > 0 ? (
          <table className="policy-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Discipline</th>
                <th>Country</th>
                <th>Posting Type</th>
                <th>Author</th>
                <th>Short Description</th>
                <th>Link</th>
              </tr>
            </thead>
            <tbody>
              {pagedRows.map((row) => (
                <tr key={row.id}>
                  <td>{formatDate(row.created_at)}</td>
                  <td>{disciplineForRow(row)}</td>
                  <td>{row.country ?? "-"}</td>
                  <td>{postingTypeForRow(row)}</td>
                  <td>{row.organization_name}</td>
                  <td className="description-cell">{shortDescription(row)}</td>
                  <td>
                    <a className="inline-link inline-link-compact" href={row.canonical_url} target="_blank" rel="noreferrer">
                      Open link
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </section>

      <div className="table-pager">
        <label className="control">
          <span>Rows Per Page</span>
          <select
            value={pageSize}
            onChange={(event) => {
              setPageSize(Number(event.target.value));
              setPage(0);
            }}
          >
            <option value={10}>10</option>
            <option value={20}>20</option>
            <option value={50}>50</option>
          </select>
        </label>
        <p className="status">
          Page {safePage + 1} / {pageCount} · Showing {pagedRows.length} of {filteredRows.length}
        </p>
        <div className="actions">
          <button className="button" type="button" onClick={() => setPage(0)} disabled={safePage === 0}>
            First
          </button>
          <button className="button" type="button" onClick={() => setPage((prev) => Math.max(0, prev - 1))} disabled={safePage === 0}>
            Previous
          </button>
          <button
            className="button"
            type="button"
            onClick={() => setPage((prev) => Math.min(pageCount - 1, prev + 1))}
            disabled={safePage >= pageCount - 1}
          >
            Next
          </button>
          <button className="button" type="button" onClick={() => setPage(pageCount - 1)} disabled={safePage >= pageCount - 1}>
            Last
          </button>
        </div>
      </div>
    </section>
  );
}
