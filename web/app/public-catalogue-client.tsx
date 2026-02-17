"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type PostingStatus = "active" | "stale" | "archived" | "closed";
type TextOperator = "contains" | "starts_with" | "equals";

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
  created_at: string;
};

type SelectFilterKey = "discipline" | "country" | "type" | "author" | "status";
type OpenPopup = SelectFilterKey | "description" | null;

function formatDate(value: string): string {
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) return value;
  return new Date(parsed).toLocaleDateString();
}

function discipline(row: PostingListRow): string {
  return row.areas[0] ?? row.tags[0] ?? "-";
}

function postingType(row: PostingListRow): string {
  return row.opportunity_kind ?? (row.remote ? "remote" : "unspecified");
}

function matchesText(haystack: string, needle: string, operator: TextOperator): boolean {
  if (!needle.trim()) return true;
  const h = haystack.toLowerCase();
  const n = needle.trim().toLowerCase();
  if (operator === "equals") return h === n;
  if (operator === "starts_with") return h.startsWith(n);
  return h.includes(n);
}

function HeaderCell(props: { label: string; children?: React.ReactNode }): JSX.Element {
  return (
    <div className="bs-header-cell">
      <span>{props.label}</span>
      {props.children}
    </div>
  );
}

export function PublicCatalogueClient(): JSX.Element {
  const [rows, setRows] = useState<PostingListRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [openPopup, setOpenPopup] = useState<OpenPopup>(null);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const [selectedDiscipline, setSelectedDiscipline] = useState<string[]>([]);
  const [selectedCountry, setSelectedCountry] = useState<string[]>([]);
  const [selectedType, setSelectedType] = useState<string[]>([]);
  const [selectedAuthor, setSelectedAuthor] = useState<string[]>([]);
  const [selectedStatus, setSelectedStatus] = useState<string[]>([]);

  const [searchDiscipline, setSearchDiscipline] = useState("");
  const [searchCountry, setSearchCountry] = useState("");
  const [searchType, setSearchType] = useState("");
  const [searchAuthor, setSearchAuthor] = useState("");
  const [searchStatus, setSearchStatus] = useState("");

  const [descOperator, setDescOperator] = useState<TextOperator>("contains");
  const [descQuery, setDescQuery] = useState("");

  const [pageSize, setPageSize] = useState(20);
  const [page, setPage] = useState(0);

  const shellRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    void fetch("/api/postings?limit=200&sort_by=updated_at&sort_dir=desc", { cache: "no-store" })
      .then(async (response) => {
        const payload: unknown = await response.json();
        if (!response.ok) throw new Error("Failed to load postings.");
        if (!Array.isArray(payload)) throw new Error("Invalid postings payload.");
        if (!cancelled) setRows(payload as PostingListRow[]);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setRows([]);
          setError(err instanceof Error ? err.message : "Failed to load postings.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    function handleOutsideClick(event: MouseEvent): void {
      if (!openPopup || !shellRef.current) return;
      if (event.target instanceof Node && !shellRef.current.contains(event.target)) {
        setOpenPopup(null);
      }
    }
    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, [openPopup]);

  const disciplineOptions = useMemo(
    () => Array.from(new Set(rows.map((row) => discipline(row)))).sort((a, b) => a.localeCompare(b)),
    [rows]
  );
  const countryOptions = useMemo(
    () => Array.from(new Set(rows.map((row) => row.country ?? "-"))).sort((a, b) => a.localeCompare(b)),
    [rows]
  );
  const typeOptions = useMemo(
    () => Array.from(new Set(rows.map((row) => postingType(row)))).sort((a, b) => a.localeCompare(b)),
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
        const d = discipline(row);
        const c = row.country ?? "-";
        const t = postingType(row);
        const a = row.organization_name;
        const s = row.status;
        const desc = row.description_text ?? "";
        return (
          (selectedDiscipline.length === 0 || selectedDiscipline.includes(d)) &&
          (selectedCountry.length === 0 || selectedCountry.includes(c)) &&
          (selectedType.length === 0 || selectedType.includes(t)) &&
          (selectedAuthor.length === 0 || selectedAuthor.includes(a)) &&
          (selectedStatus.length === 0 || selectedStatus.includes(s)) &&
          matchesText(d, searchDiscipline, "contains") &&
          matchesText(c, searchCountry, "contains") &&
          matchesText(t, searchType, "contains") &&
          matchesText(a, searchAuthor, "contains") &&
          matchesText(s, searchStatus, "contains") &&
          matchesText(desc, descQuery, descOperator)
        );
      }),
    [
      descOperator,
      descQuery,
      rows,
      searchAuthor,
      searchCountry,
      searchDiscipline,
      searchStatus,
      searchType,
      selectedAuthor,
      selectedCountry,
      selectedDiscipline,
      selectedStatus,
      selectedType
    ]
  );

  const pageCount = Math.max(1, Math.ceil(filteredRows.length / pageSize));
  const currentPage = Math.min(page, pageCount - 1);
  const pageRows = filteredRows.slice(currentPage * pageSize, currentPage * pageSize + pageSize);

  function clearFilters(): void {
    setSelectedDiscipline([]);
    setSelectedCountry([]);
    setSelectedType([]);
    setSelectedAuthor([]);
    setSelectedStatus([]);
    setSearchDiscipline("");
    setSearchCountry("");
    setSearchType("");
    setSearchAuthor("");
    setSearchStatus("");
    setDescOperator("contains");
    setDescQuery("");
    setOpenPopup(null);
    setPage(0);
  }

  function renderDescription(row: PostingListRow): JSX.Element {
    const text = row.description_text?.trim() ?? "";
    if (!text) return <span>-</span>;
    const expanded = expandedIds.has(row.id);
    const isLong = text.length > 130;
    if (!isLong) return <span>{text}</span>;
    return (
      <span>
        {expanded ? text : `${text.slice(0, 127)}...`}{" "}
        <button
          className="inline-button"
          type="button"
          onClick={() =>
            setExpandedIds((prev) => {
              const next = new Set(prev);
              if (next.has(row.id)) next.delete(row.id);
              else next.add(row.id);
              return next;
            })
          }
        >
          {expanded ? "less" : "more"}
        </button>
      </span>
    );
  }

  function selectPopup(
    key: SelectFilterKey,
    options: string[],
    selected: string[],
    setSelected: (next: string[]) => void,
    search: string,
    setSearch: (next: string) => void
  ): JSX.Element {
    const allSelected = selected.length === 0 || selected.length === options.length;
    return (
      <div className="bs-popup">
        <input className="bs-popup-input" placeholder="Filter..." value={search} onChange={(event) => setSearch(event.target.value)} />
        <label className="bs-popup-option">
          <input type="checkbox" checked={allSelected} onChange={() => setSelected([])} />
          (Select All)
        </label>
        <div className="bs-popup-list">
          {options.map((option) => (
            <label key={`${key}-${option}`} className="bs-popup-option">
              <input
                type="checkbox"
                checked={selected.includes(option)}
                onChange={() => {
                  if (selected.includes(option)) setSelected(selected.filter((item) => item !== option));
                  else setSelected([...selected, option]);
                }}
              />
              {option}
            </label>
          ))}
        </div>
      </div>
    );
  }

  const hasActiveFilters =
    selectedDiscipline.length > 0 ||
    selectedCountry.length > 0 ||
    selectedType.length > 0 ||
    selectedAuthor.length > 0 ||
    selectedStatus.length > 0 ||
    searchDiscipline.trim().length > 0 ||
    searchCountry.trim().length > 0 ||
    searchType.trim().length > 0 ||
    searchAuthor.trim().length > 0 ||
    searchStatus.trim().length > 0 ||
    descQuery.trim().length > 0;

  return (
    <section className="catalogue-shell">
      {loading ? <p className="status">Loading postings...</p> : null}
      {error ? <p className="status status-error">{error}</p> : null}

      <div className="bs-table-shell" ref={shellRef}>
        {hasActiveFilters ? (
          <div className="bs-table-topbar">
            <button className="clear-filters-link" type="button" onClick={clearFilters}>
              clear filters
            </button>
          </div>
        ) : null}
        <div className="bs-table-viewport">
          <table className="policy-table bs-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>
                  <HeaderCell label="Discipline">
                    <button className="header-filter-trigger" type="button" onClick={() => setOpenPopup(openPopup === "discipline" ? null : "discipline")}>⌄</button>
                    {openPopup === "discipline"
                      ? selectPopup("discipline", disciplineOptions, selectedDiscipline, setSelectedDiscipline, searchDiscipline, setSearchDiscipline)
                      : null}
                  </HeaderCell>
                </th>
                <th>
                  <HeaderCell label="Country">
                    <button className="header-filter-trigger" type="button" onClick={() => setOpenPopup(openPopup === "country" ? null : "country")}>⌄</button>
                    {openPopup === "country" ? selectPopup("country", countryOptions, selectedCountry, setSelectedCountry, searchCountry, setSearchCountry) : null}
                  </HeaderCell>
                </th>
                <th>
                  <HeaderCell label="Type">
                    <button className="header-filter-trigger" type="button" onClick={() => setOpenPopup(openPopup === "type" ? null : "type")}>⌄</button>
                    {openPopup === "type" ? selectPopup("type", typeOptions, selectedType, setSelectedType, searchType, setSearchType) : null}
                  </HeaderCell>
                </th>
                <th>
                  <HeaderCell label="Author">
                    <button className="header-filter-trigger" type="button" onClick={() => setOpenPopup(openPopup === "author" ? null : "author")}>⌄</button>
                    {openPopup === "author" ? selectPopup("author", authorOptions, selectedAuthor, setSelectedAuthor, searchAuthor, setSearchAuthor) : null}
                  </HeaderCell>
                </th>
                <th>
                  <HeaderCell label="Status">
                    <button className="header-filter-trigger" type="button" onClick={() => setOpenPopup(openPopup === "status" ? null : "status")}>⌄</button>
                    {openPopup === "status" ? selectPopup("status", statusOptions, selectedStatus, setSelectedStatus, searchStatus, setSearchStatus) : null}
                  </HeaderCell>
                </th>
                <th>
                  <HeaderCell label="Position">
                    <button className="header-filter-trigger" type="button" onClick={() => setOpenPopup(openPopup === "description" ? null : "description")}>⌄</button>
                    {openPopup === "description" ? (
                      <div className="bs-popup">
                        <select
                          className="bs-popup-input"
                          value={descOperator}
                          onChange={(event) => setDescOperator(event.target.value as TextOperator)}
                        >
                          <option value="contains">Contains</option>
                          <option value="starts_with">Starts with</option>
                          <option value="equals">Equals</option>
                        </select>
                        <input className="bs-popup-input" placeholder="Filter..." value={descQuery} onChange={(event) => setDescQuery(event.target.value)} />
                      </div>
                    ) : null}
                  </HeaderCell>
                </th>
                <th>Link</th>
              </tr>
            </thead>
            <tbody>
              {pageRows.map((row) => (
                <tr key={row.id}>
                  <td>{formatDate(row.created_at)}</td>
                  <td>{discipline(row)}</td>
                  <td>{row.country ?? "-"}</td>
                  <td>{postingType(row)}</td>
                  <td>{row.organization_name}</td>
                  <td className="description-cell">{renderDescription(row)}</td>
                  <td>
                    <a className="inline-link inline-link-compact" href={row.canonical_url} target="_blank" rel="noreferrer">
                      View Post
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="table-pager table-pager-integrated">
          <label className="control">
            <span>Page Size</span>
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
            {currentPage * pageSize + 1} to {Math.min((currentPage + 1) * pageSize, filteredRows.length)} of {filteredRows.length}
          </p>
          <div className="actions">
            <button className="button" type="button" onClick={() => setPage(0)} disabled={currentPage === 0}>
              |&lt;
            </button>
            <button className="button" type="button" onClick={() => setPage((prev) => Math.max(0, prev - 1))} disabled={currentPage === 0}>
              &lt;
            </button>
            <span className="status">
              Page {currentPage + 1} of {pageCount}
            </span>
            <button className="button" type="button" onClick={() => setPage((prev) => Math.min(pageCount - 1, prev + 1))} disabled={currentPage >= pageCount - 1}>
              &gt;
            </button>
            <button className="button" type="button" onClick={() => setPage(pageCount - 1)} disabled={currentPage >= pageCount - 1}>
              &gt;|
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
