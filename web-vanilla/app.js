const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const AUTO_REFRESH_MS = 5000;

const filtersForm = document.getElementById("filters");
const rowsBody = document.getElementById("rows");
const statusLine = document.getElementById("statusLine");
const prevButton = document.getElementById("prevButton");
const nextButton = document.getElementById("nextButton");
const resetButton = document.getElementById("resetButton");
const apiBaseInput = document.getElementById("apiBaseUrl");

let offset = 0;
let lastRowCount = 0;
let latestQueryKey = "";

function readSearchParams() {
  const url = new URL(window.location.href);
  return url.searchParams;
}

function writeSearchParams(params) {
  const url = new URL(window.location.href);
  url.search = params.toString();
  window.history.replaceState(null, "", url.toString());
}

function getApiBaseUrl(searchParams) {
  const fromQuery = searchParams.get("api_base_url");
  const fromStorage = window.localStorage.getItem("sj_api_base_url");
  return (fromQuery || fromStorage || DEFAULT_API_BASE_URL).replace(/\/+$/, "");
}

function truncate(value, length = 140) {
  if (!value) return "-";
  const normalized = String(value).trim();
  if (normalized.length <= length) return normalized;
  return `${normalized.slice(0, length - 3)}...`;
}

function formatTimestamp(value) {
  if (!value) return "-";
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) return value;
  return new Date(parsed).toLocaleString();
}

function toQueryString(formData) {
  const query = new URLSearchParams();
  const apiBaseUrl = (formData.get("api_base_url") || "").toString().trim();
  if (apiBaseUrl) query.set("api_base_url", apiBaseUrl);

  const fields = [
    "q",
    "organization_name",
    "country",
    "tag",
    "status",
    "sort_by",
    "sort_dir",
    "limit"
  ];
  for (const field of fields) {
    const value = (formData.get(field) || "").toString().trim();
    if (value.length > 0) {
      query.set(field, value);
    }
  }

  const remoteFilter = (formData.get("remote_filter") || "all").toString();
  query.set("remote_filter", remoteFilter);
  if (remoteFilter === "remote") query.set("remote", "true");
  if (remoteFilter === "onsite") query.set("remote", "false");

  query.set("offset", String(offset));
  return query;
}

function syncFormFromParams(params) {
  apiBaseInput.value = getApiBaseUrl(params);
  const set = (name, fallback = "") => {
    const element = filtersForm.elements.namedItem(name);
    if (!(element instanceof HTMLInputElement || element instanceof HTMLSelectElement)) return;
    element.value = params.get(name) ?? fallback;
  };
  set("q");
  set("organization_name");
  set("country");
  set("tag");
  set("status");
  set("sort_by", "updated_at");
  set("sort_dir", "desc");
  set("limit", "20");
  set("remote_filter", "all");

  const offsetValue = Number(params.get("offset") ?? "0");
  offset = Number.isInteger(offsetValue) && offsetValue >= 0 ? offsetValue : 0;
}

function renderRows(rows) {
  rowsBody.innerHTML = "";
  if (rows.length === 0) {
    const row = document.createElement("tr");
    row.innerHTML = '<td colspan="7">No rows found.</td>';
    rowsBody.appendChild(row);
    return;
  }

  for (const posting of rows) {
    const tr = document.createElement("tr");
    const tags = (posting.tags || []).slice(0, 2).map((tag) => `<span class="badge">${tag}</span>`).join("");
    const location = [posting.country || "-", posting.remote ? "remote" : ""].filter(Boolean).join(" · ");
    tr.innerHTML = `
      <td>${posting.title || "-"}</td>
      <td>${posting.organization_name || "-"}</td>
      <td>${truncate(posting.description_text)}</td>
      <td>${location}</td>
      <td><span class="badge">${posting.status || "-"}</span>${tags}</td>
      <td>${formatTimestamp(posting.updated_at)}</td>
      <td>
        <a href="${posting.canonical_url}" target="_blank" rel="noreferrer">Source</a>
        ·
        <a href="?${latestQueryKey}&posting_id=${encodeURIComponent(posting.id)}">Details</a>
      </td>
    `;
    rowsBody.appendChild(tr);
  }
}

async function fetchRows() {
  const formData = new FormData(filtersForm);
  const queryParams = toQueryString(formData);
  latestQueryKey = queryParams.toString();
  writeSearchParams(queryParams);

  const apiBaseUrl = getApiBaseUrl(queryParams);
  window.localStorage.setItem("sj_api_base_url", apiBaseUrl);

  const apiParams = new URLSearchParams(queryParams);
  apiParams.delete("api_base_url");
  apiParams.delete("remote_filter");

  statusLine.textContent = "Loading…";
  try {
    const response = await fetch(`${apiBaseUrl}/postings?${apiParams.toString()}`);
    const payload = await response.json();
    if (!response.ok) {
      const detail = payload && typeof payload === "object" && "detail" in payload ? payload.detail : "request failed";
      throw new Error(String(detail));
    }
    if (!Array.isArray(payload)) {
      throw new Error("Invalid API response");
    }

    lastRowCount = payload.length;
    prevButton.disabled = offset === 0;
    nextButton.disabled = payload.length < Number(queryParams.get("limit") || "20");
    statusLine.textContent = `Offset ${offset} · Showing ${payload.length} row(s) · Auto-refresh ${AUTO_REFRESH_MS / 1000}s`;
    renderRows(payload);
  } catch (error) {
    statusLine.textContent = `Error: ${error instanceof Error ? error.message : "unknown error"}`;
    rowsBody.innerHTML = "";
  }
}

filtersForm.addEventListener("submit", (event) => {
  event.preventDefault();
  offset = 0;
  void fetchRows();
});

resetButton.addEventListener("click", () => {
  offset = 0;
  const clean = new URLSearchParams();
  clean.set("remote_filter", "all");
  clean.set("sort_by", "updated_at");
  clean.set("sort_dir", "desc");
  clean.set("limit", "20");
  clean.set("offset", "0");
  clean.set("api_base_url", apiBaseInput.value.trim() || DEFAULT_API_BASE_URL);
  writeSearchParams(clean);
  syncFormFromParams(clean);
  void fetchRows();
});

prevButton.addEventListener("click", () => {
  offset = Math.max(0, offset - Number(filtersForm.elements.namedItem("limit").value || "20"));
  void fetchRows();
});

nextButton.addEventListener("click", () => {
  if (lastRowCount === 0) return;
  offset += Number(filtersForm.elements.namedItem("limit").value || "20");
  void fetchRows();
});

const initial = readSearchParams();
if (!initial.has("remote_filter")) initial.set("remote_filter", "all");
if (!initial.has("sort_by")) initial.set("sort_by", "updated_at");
if (!initial.has("sort_dir")) initial.set("sort_dir", "desc");
if (!initial.has("limit")) initial.set("limit", "20");
if (!initial.has("offset")) initial.set("offset", "0");
if (!initial.has("api_base_url")) initial.set("api_base_url", getApiBaseUrl(initial));
writeSearchParams(initial);
syncFormFromParams(initial);
void fetchRows();
window.setInterval(() => void fetchRows(), AUTO_REFRESH_MS);
