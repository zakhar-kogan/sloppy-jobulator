"use client";

import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import {
  coerceTitle,
  type AdminJob,
  type AdminModule,
  type Candidate,
  type CandidateAgeBucket,
  type CandidateFacet,
  type CandidateQueueFacets,
  type CandidateState,
  formatTimestamp,
  getApiErrorDetail,
  type JobKind,
  type JobStatus,
  type ModuleKind,
  type PostingStatus
} from "../../../lib/admin-cockpit";
import {
  canTransitionCandidateState,
  coerceBoundedInteger,
  encodeAdminQuery,
  listPatchCandidateStates,
  parseAdminCount
} from "../../../lib/admin-cockpit-utils";

const CANDIDATE_STATES: CandidateState[] = [
  "discovered",
  "processed",
  "publishable",
  "published",
  "rejected",
  "closed",
  "archived",
  "needs_review"
];
const MODULE_KINDS: ModuleKind[] = ["connector", "processor"];
const JOB_KINDS: JobKind[] = ["dedupe", "extract", "enrich", "check_freshness", "resolve_url_redirects"];
const JOB_STATUSES: JobStatus[] = ["queued", "claimed", "done", "failed", "dead_letter"];
const POSTING_STATUSES: PostingStatus[] = ["active", "stale", "archived", "closed"];
const CANDIDATE_LIMIT_MAX = 100;
const MODULE_LIMIT_MAX = 200;
const JOB_LIMIT_MAX = 200;
const MAINTENANCE_LIMIT_MAX = 1000;
const MAINTENANCE_CONFIRM_TOKEN = "CONFIRM";

type BoolFilter = "all" | "true" | "false";
type CandidateStateFilter = "all" | CandidateState;
type CandidateAgeFilter = "all" | CandidateAgeBucket;
type ModuleKindFilter = "all" | ModuleKind;
type JobKindFilter = "all" | JobKind;
type JobStatusFilter = "all" | JobStatus;

type CandidateAction = "patch" | "merge" | "override";

const PATCH_REASON_REQUIRED_STATES = new Set<CandidateState>(["rejected", "archived", "closed"]);
const QUEUE_AGE_BUCKETS: Array<{ value: CandidateAgeBucket; label: string }> = [
  { value: "lt_24h", label: "<24h" },
  { value: "d1_3", label: "1-3d" },
  { value: "d3_7", label: "3-7d" },
  { value: "gt_7d", label: "7d+" }
];
const OPERATOR_TIMESTAMP = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short"
});

function requiresPatchReason(state: CandidateState): boolean {
  return PATCH_REASON_REQUIRED_STATES.has(state);
}

function asObject(value: unknown): Record<string, unknown> {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return {};
}

function asText(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function asNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  return null;
}

function formatRetryWindow(nextRunAt: string): string | null {
  const nextRunMs = Date.parse(nextRunAt);
  if (!Number.isFinite(nextRunMs)) {
    return null;
  }
  const deltaSeconds = Math.round((nextRunMs - Date.now()) / 1000);
  if (deltaSeconds <= 0) {
    return "retry due now";
  }
  if (deltaSeconds < 60) {
    return `retry in ${deltaSeconds}s`;
  }
  return `retry in ${Math.ceil(deltaSeconds / 60)}m`;
}

function formatJobPayload(payload: Record<string, unknown>): string {
  if (Object.keys(payload).length === 0) {
    return "{}";
  }
  return JSON.stringify(payload, null, 2);
}

function formatOperatorTimestamp(value: string): string {
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) {
    return value;
  }
  return OPERATOR_TIMESTAMP.format(new Date(parsed));
}

function describeJobError(errorJson: Record<string, unknown>): string | null {
  return (
    asText(errorJson.detail) ??
    asText(errorJson.message) ??
    asText(errorJson.error) ??
    asText(errorJson.reason) ??
    null
  );
}

function describeRedirectVisibility(job: AdminJob): string[] {
  if (job.kind !== "resolve_url_redirects") {
    return [];
  }

  const result = asObject(job.result_json);
  const repositoryOutcome = asObject(result.repository_outcome);
  const details: string[] = [];
  const resolutionStatus = asText(repositoryOutcome.status);
  if (resolutionStatus) {
    details.push(`repository outcome: ${resolutionStatus}`);
  }

  const resolverReason = asText(result.reason) ?? asText(repositoryOutcome.resolver_reason);
  if (resolverReason) {
    details.push(`resolver reason: ${resolverReason}`);
  }

  const hopCount = asNumber(result.redirect_hop_count) ?? asNumber(repositoryOutcome.redirect_hop_count);
  if (hopCount !== null) {
    details.push(`redirect hops: ${hopCount}`);
  }

  const resolvedNormalizedUrl = asText(repositoryOutcome.resolved_normalized_url) ?? asText(result.resolved_normalized_url);
  if (resolvedNormalizedUrl) {
    details.push(`resolved normalized URL: ${resolvedNormalizedUrl}`);
  }

  return details;
}

function parseCandidateFacets(payload: unknown): CandidateQueueFacets {
  if (!payload || typeof payload !== "object") {
    throw new Error("Candidate facets response is invalid.");
  }
  const asFacets = payload as Partial<CandidateQueueFacets>;
  const toFacetArray = (value: unknown): CandidateFacet[] =>
    Array.isArray(value)
      ? value
          .filter((item): item is CandidateFacet => {
            if (!item || typeof item !== "object") {
              return false;
            }
            const typed = item as Partial<CandidateFacet>;
            return typeof typed.value === "string" && typeof typed.count === "number" && Number.isFinite(typed.count);
          })
          .map((item) => ({ value: item.value, count: item.count }))
      : [];

  const total = typeof asFacets.total === "number" && Number.isFinite(asFacets.total) ? asFacets.total : 0;
  return {
    total,
    states: toFacetArray(asFacets.states),
    sources: toFacetArray(asFacets.sources),
    ages: toFacetArray(asFacets.ages)
  };
}

export function ModeratorCockpitClient(): JSX.Element {
  const [candidateStateFilter, setCandidateStateFilter] = useState<CandidateStateFilter>("needs_review");
  const [candidateSourceFilter, setCandidateSourceFilter] = useState("all");
  const [candidateAgeFilter, setCandidateAgeFilter] = useState<CandidateAgeFilter>("all");
  const [candidateLimit, setCandidateLimit] = useState(50);
  const [candidateOffset, setCandidateOffset] = useState(0);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [candidateFacets, setCandidateFacets] = useState<CandidateQueueFacets>({
    total: 0,
    states: [],
    sources: [],
    ages: []
  });
  const [candidateFacetLoading, setCandidateFacetLoading] = useState(false);
  const [candidateFacetError, setCandidateFacetError] = useState<string | null>(null);
  const [candidateListLoading, setCandidateListLoading] = useState(false);
  const [candidateListError, setCandidateListError] = useState<string | null>(null);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string>("");
  const [selectedCandidateIds, setSelectedCandidateIds] = useState<string[]>([]);

  const [patchState, setPatchState] = useState<CandidateState>("publishable");
  const [patchReason, setPatchReason] = useState("");
  const [bulkPatchState, setBulkPatchState] = useState<CandidateState>("publishable");
  const [bulkPatchReason, setBulkPatchReason] = useState("");
  const [mergeSecondaryCandidateId, setMergeSecondaryCandidateId] = useState("");
  const [mergeReason, setMergeReason] = useState("");
  const [overrideState, setOverrideState] = useState<CandidateState>("publishable");
  const [overrideReason, setOverrideReason] = useState("");
  const [overridePostingStatus, setOverridePostingStatus] = useState<"" | PostingStatus>("");
  const [candidateActionBusy, setCandidateActionBusy] = useState<CandidateAction | null>(null);
  const [candidateMessage, setCandidateMessage] = useState<string | null>(null);
  const [candidateActionError, setCandidateActionError] = useState<string | null>(null);
  const [bulkActionBusy, setBulkActionBusy] = useState(false);
  const [bulkActionMessage, setBulkActionMessage] = useState<string | null>(null);
  const [bulkActionError, setBulkActionError] = useState<string | null>(null);

  const [moduleIdFilter, setModuleIdFilter] = useState("");
  const [moduleKindFilter, setModuleKindFilter] = useState<ModuleKindFilter>("all");
  const [moduleEnabledFilter, setModuleEnabledFilter] = useState<BoolFilter>("all");
  const [moduleLimit, setModuleLimit] = useState(50);
  const [moduleOffset, setModuleOffset] = useState(0);
  const [modules, setModules] = useState<AdminModule[]>([]);
  const [moduleListLoading, setModuleListLoading] = useState(false);
  const [moduleError, setModuleError] = useState<string | null>(null);
  const [moduleMessage, setModuleMessage] = useState<string | null>(null);
  const [moduleToggleBusyId, setModuleToggleBusyId] = useState<string | null>(null);

  const [jobStatusFilter, setJobStatusFilter] = useState<JobStatusFilter>("all");
  const [jobKindFilter, setJobKindFilter] = useState<JobKindFilter>("all");
  const [jobTargetTypeFilter, setJobTargetTypeFilter] = useState("");
  const [jobLimit, setJobLimit] = useState(50);
  const [jobOffset, setJobOffset] = useState(0);
  const [jobs, setJobs] = useState<AdminJob[]>([]);
  const [jobListLoading, setJobListLoading] = useState(false);
  const [jobError, setJobError] = useState<string | null>(null);
  const [jobMessage, setJobMessage] = useState<string | null>(null);
  const [maintenanceLimit, setMaintenanceLimit] = useState(100);
  const [maintenanceConfirmation, setMaintenanceConfirmation] = useState("");
  const [jobMaintenanceBusy, setJobMaintenanceBusy] = useState<"enqueue" | null>(null);

  const candidateQueryString = useMemo(
    () =>
      encodeAdminQuery({
        state: candidateStateFilter === "all" ? undefined : candidateStateFilter,
        source: candidateSourceFilter === "all" ? undefined : candidateSourceFilter,
        age: candidateAgeFilter === "all" ? undefined : candidateAgeFilter,
        limit: candidateLimit,
        offset: candidateOffset
      }),
    [candidateAgeFilter, candidateLimit, candidateOffset, candidateSourceFilter, candidateStateFilter]
  );

  const moduleQueryString = useMemo(
    () =>
      encodeAdminQuery({
        module_id: moduleIdFilter,
        kind: moduleKindFilter === "all" ? undefined : moduleKindFilter,
        enabled: moduleEnabledFilter === "all" ? undefined : moduleEnabledFilter,
        limit: moduleLimit,
        offset: moduleOffset
      }),
    [moduleEnabledFilter, moduleIdFilter, moduleKindFilter, moduleLimit, moduleOffset]
  );

  const jobsQueryString = useMemo(
    () =>
      encodeAdminQuery({
        status: jobStatusFilter === "all" ? undefined : jobStatusFilter,
        kind: jobKindFilter === "all" ? undefined : jobKindFilter,
        target_type: jobTargetTypeFilter,
        limit: jobLimit,
        offset: jobOffset
      }),
    [jobKindFilter, jobLimit, jobOffset, jobStatusFilter, jobTargetTypeFilter]
  );

  const selectedCandidate = useMemo(
    () => candidates.find((candidate) => candidate.id === selectedCandidateId) ?? null,
    [candidates, selectedCandidateId]
  );
  const selectedCandidateRows = useMemo(
    () => candidates.filter((candidate) => selectedCandidateIds.includes(candidate.id)),
    [candidates, selectedCandidateIds]
  );
  const bulkTransitionBlockedCandidates = useMemo(
    () =>
      selectedCandidateRows
        .filter((candidate) => !canTransitionCandidateState(candidate.state, bulkPatchState))
        .map((candidate) => candidate.id),
    [bulkPatchState, selectedCandidateRows]
  );
  const patchStateOptions = useMemo(
    () => listPatchCandidateStates(selectedCandidate?.state ?? null, CANDIDATE_STATES),
    [selectedCandidate]
  );
  const mergeCandidateOptions = useMemo(
    () => candidates.filter((candidate) => candidate.id !== selectedCandidateId),
    [candidates, selectedCandidateId]
  );
  const stateFacetCountByValue = useMemo(
    () => new Map(candidateFacets.states.map((item) => [item.value, item.count])),
    [candidateFacets.states]
  );
  const ageFacetCountByValue = useMemo(
    () => new Map(candidateFacets.ages.map((item) => [item.value, item.count])),
    [candidateFacets.ages]
  );
  const sourceFacetOptions = useMemo(() => {
    const ranked = [...candidateFacets.sources].sort((left, right) => right.count - left.count || left.value.localeCompare(right.value));
    if (candidateSourceFilter === "all" || ranked.some((item) => item.value === candidateSourceFilter)) {
      return ranked;
    }
    return [{ value: candidateSourceFilter, count: 0 }, ...ranked];
  }, [candidateFacets.sources, candidateSourceFilter]);
  const patchSubmitDisabled =
    candidateActionBusy !== null || !selectedCandidateId || (requiresPatchReason(patchState) && patchReason.trim().length === 0);
  const mergeSubmitDisabled =
    candidateActionBusy !== null ||
    !selectedCandidateId ||
    mergeSecondaryCandidateId.trim().length === 0 ||
    mergeReason.trim().length === 0;
  const overrideSubmitDisabled =
    candidateActionBusy !== null || !selectedCandidateId || overrideReason.trim().length === 0;
  const bulkSubmitDisabled =
    bulkActionBusy ||
    selectedCandidateRows.length === 0 ||
    (requiresPatchReason(bulkPatchState) && bulkPatchReason.trim().length === 0) ||
    bulkTransitionBlockedCandidates.length > 0;

  const loadCandidates = useCallback(async () => {
    setCandidateListLoading(true);
    setCandidateListError(null);

    try {
      const response = await fetch(`/api/admin/candidates?${candidateQueryString}`, {
        method: "GET",
        cache: "no-store"
      });
      const payload: unknown = await response.json();
      if (!response.ok) {
        throw new Error(getApiErrorDetail(payload, "Failed to load candidates."));
      }
      if (!Array.isArray(payload)) {
        throw new Error("Candidates response is invalid.");
      }

      const rows = payload as Candidate[];
      setCandidates(rows);
      if (rows.length === 0) {
        setSelectedCandidateId("");
      } else if (!rows.some((candidate) => candidate.id === selectedCandidateId)) {
        setSelectedCandidateId(rows[0].id);
      }
      setSelectedCandidateIds((previousIds) => previousIds.filter((candidateId) => rows.some((row) => row.id === candidateId)));
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Failed to load candidates.";
      setCandidateListError(detail);
      setCandidates([]);
      setSelectedCandidateId("");
      setSelectedCandidateIds([]);
    } finally {
      setCandidateListLoading(false);
    }
  }, [candidateQueryString, selectedCandidateId]);

  const loadCandidateFacets = useCallback(async () => {
    setCandidateFacetLoading(true);
    setCandidateFacetError(null);
    try {
      const response = await fetch("/api/admin/candidates/facets", {
        method: "GET",
        cache: "no-store"
      });
      const payload: unknown = await response.json();
      if (!response.ok) {
        throw new Error(getApiErrorDetail(payload, "Failed to load candidate facets."));
      }
      setCandidateFacets(parseCandidateFacets(payload));
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Failed to load candidate facets.";
      setCandidateFacetError(detail);
      setCandidateFacets({ total: 0, states: [], sources: [], ages: [] });
    } finally {
      setCandidateFacetLoading(false);
    }
  }, []);

  const loadModules = useCallback(async () => {
    setModuleListLoading(true);
    setModuleError(null);

    try {
      const response = await fetch(`/api/admin/modules?${moduleQueryString}`, {
        method: "GET",
        cache: "no-store"
      });
      const payload: unknown = await response.json();
      if (!response.ok) {
        throw new Error(getApiErrorDetail(payload, "Failed to load modules."));
      }
      if (!Array.isArray(payload)) {
        throw new Error("Modules response is invalid.");
      }

      setModules(payload as AdminModule[]);
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Failed to load modules.";
      setModuleError(detail);
      setModules([]);
    } finally {
      setModuleListLoading(false);
    }
  }, [moduleQueryString]);

  const loadJobs = useCallback(async () => {
    setJobListLoading(true);
    setJobError(null);

    try {
      const response = await fetch(`/api/admin/jobs?${jobsQueryString}`, {
        method: "GET",
        cache: "no-store"
      });
      const payload: unknown = await response.json();
      if (!response.ok) {
        throw new Error(getApiErrorDetail(payload, "Failed to load jobs."));
      }
      if (!Array.isArray(payload)) {
        throw new Error("Jobs response is invalid.");
      }

      setJobs(payload as AdminJob[]);
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Failed to load jobs.";
      setJobError(detail);
      setJobs([]);
    } finally {
      setJobListLoading(false);
    }
  }, [jobsQueryString]);

  useEffect(() => {
    void loadCandidates();
  }, [loadCandidates]);

  useEffect(() => {
    void loadCandidateFacets();
  }, [loadCandidateFacets]);

  useEffect(() => {
    void loadModules();
  }, [loadModules]);

  useEffect(() => {
    void loadJobs();
  }, [loadJobs]);

  useEffect(() => {
    if (!patchStateOptions.includes(patchState)) {
      setPatchState(patchStateOptions[0] ?? "needs_review");
    }
  }, [patchState, patchStateOptions]);

  function handleCandidateQuickSelect(candidateId: string): void {
    setSelectedCandidateId(candidateId);
    setSelectedCandidateIds((previousIds) => (previousIds.includes(candidateId) ? previousIds : [...previousIds, candidateId]));
  }

  function handleCandidateCheckboxToggle(candidateId: string, checked: boolean): void {
    setSelectedCandidateIds((previousIds) => {
      if (checked) {
        return previousIds.includes(candidateId) ? previousIds : [...previousIds, candidateId];
      }
      return previousIds.filter((value) => value !== candidateId);
    });
  }

  function handleSelectAllCandidatesOnPage(): void {
    setSelectedCandidateIds(candidates.map((candidate) => candidate.id));
  }

  function handleClearCandidateSelection(): void {
    setSelectedCandidateIds([]);
  }

  function applyCandidateStateFilter(value: CandidateStateFilter): void {
    setCandidateStateFilter(value);
    setCandidateOffset(0);
  }

  function applyCandidateSourceFilter(value: string): void {
    setCandidateSourceFilter(value);
    setCandidateOffset(0);
  }

  function applyCandidateAgeFilter(value: CandidateAgeFilter): void {
    setCandidateAgeFilter(value);
    setCandidateOffset(0);
  }

  async function runCandidateAction(action: CandidateAction, body: Record<string, unknown>): Promise<void> {
    if (!selectedCandidateId) {
      setCandidateActionError("Select a candidate first.");
      return;
    }

    setCandidateActionBusy(action);
    setCandidateActionError(null);
    setCandidateMessage(null);

    const encodedCandidateId = encodeURIComponent(selectedCandidateId);
    const path =
      action === "patch"
        ? `/api/admin/candidates/${encodedCandidateId}`
        : action === "merge"
          ? `/api/admin/candidates/${encodedCandidateId}/merge`
          : `/api/admin/candidates/${encodedCandidateId}/override`;
    const method = action === "patch" ? "PATCH" : "POST";

    try {
      const response = await fetch(path, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      const payload: unknown = await response.json();
      if (!response.ok) {
        throw new Error(getApiErrorDetail(payload, `Failed to ${action} candidate.`));
      }

      if (action === "merge") {
        setMergeSecondaryCandidateId("");
        setMergeReason("");
      } else if (action === "patch") {
        setPatchReason("");
      } else if (action === "override") {
        setOverrideReason("");
        setOverridePostingStatus("");
      }
      setCandidateMessage(`Candidate ${action} action completed for ${selectedCandidateId}.`);
      await loadCandidates();
    } catch (error) {
      const detail = error instanceof Error ? error.message : `Failed to ${action} candidate.`;
      setCandidateActionError(detail);
    } finally {
      setCandidateActionBusy(null);
    }
  }

  async function patchCandidateById(candidateId: string, body: Record<string, unknown>): Promise<void> {
    const response = await fetch(`/api/admin/candidates/${encodeURIComponent(candidateId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    const payload: unknown = await response.json();
    if (!response.ok) {
      throw new Error(getApiErrorDetail(payload, `Failed to patch candidate ${candidateId}.`));
    }
  }

  async function handlePatch(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!selectedCandidate) {
      setCandidateActionError("Select a candidate first.");
      return;
    }

    if (!canTransitionCandidateState(selectedCandidate.state, patchState)) {
      setCandidateActionError(`invalid state transition for patch: ${selectedCandidate.state} -> ${patchState}`);
      return;
    }

    const reason = patchReason.trim();
    if (requiresPatchReason(patchState) && reason.length === 0) {
      setCandidateActionError(`reason is required when patching candidate to ${patchState}.`);
      return;
    }

    await runCandidateAction("patch", {
      state: patchState,
      reason: reason || undefined
    });
  }

  async function handleMerge(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const secondaryCandidateId = mergeSecondaryCandidateId.trim();
    if (!secondaryCandidateId) {
      setCandidateActionError("secondary_candidate_id is required for merge.");
      return;
    }
    if (selectedCandidateId && secondaryCandidateId === selectedCandidateId) {
      setCandidateActionError("secondary_candidate_id must differ from selected candidate.");
      return;
    }
    const reason = mergeReason.trim();
    if (!reason) {
      setCandidateActionError("reason is required for merge.");
      return;
    }

    await runCandidateAction("merge", {
      secondary_candidate_id: secondaryCandidateId,
      reason
    });
  }

  async function handleOverride(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const reason = overrideReason.trim();
    if (!reason) {
      setCandidateActionError("reason is required for override.");
      return;
    }
    await runCandidateAction("override", {
      state: overrideState,
      reason,
      posting_status: overridePostingStatus || undefined
    });
  }

  async function handleBulkPatch(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const reason = bulkPatchReason.trim();
    if (requiresPatchReason(bulkPatchState) && !reason) {
      setBulkActionError(`reason is required when bulk patching candidates to ${bulkPatchState}.`);
      return;
    }
    if (selectedCandidateRows.length === 0) {
      setBulkActionError("Select at least one candidate for bulk actions.");
      return;
    }
    if (bulkTransitionBlockedCandidates.length > 0) {
      setBulkActionError(
        `Cannot bulk patch due to invalid transitions for: ${bulkTransitionBlockedCandidates.slice(0, 4).join(", ")}${bulkTransitionBlockedCandidates.length > 4 ? ", ..." : ""}`
      );
      return;
    }

    setBulkActionBusy(true);
    setBulkActionError(null);
    setBulkActionMessage(null);
    let successCount = 0;
    const failures: string[] = [];

    for (const candidate of selectedCandidateRows) {
      try {
        await patchCandidateById(candidate.id, {
          state: bulkPatchState,
          reason: reason || undefined
        });
        successCount += 1;
      } catch (error) {
        const detail = error instanceof Error ? error.message : `Failed to patch candidate ${candidate.id}.`;
        failures.push(`${candidate.id}: ${detail}`);
      }
    }

    if (failures.length === 0) {
      setBulkActionMessage(`Bulk patched ${successCount} candidate(s) to ${bulkPatchState}.`);
      setBulkPatchReason("");
    } else {
      setBulkActionError(
        `Bulk patch completed with ${successCount} success(es) and ${failures.length} failure(s): ${failures.slice(0, 2).join(" | ")}`
      );
    }

    await loadCandidates();
    setBulkActionBusy(false);
  }

  async function handleModuleToggle(module: AdminModule): Promise<void> {
    setModuleToggleBusyId(module.module_id);
    setModuleError(null);
    setModuleMessage(null);

    try {
      const response = await fetch(`/api/admin/modules/${encodeURIComponent(module.module_id)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: !module.enabled })
      });
      const payload: unknown = await response.json();
      if (!response.ok) {
        throw new Error(getApiErrorDetail(payload, `Failed to update module ${module.module_id}.`));
      }

      setModuleMessage(`Updated ${module.module_id} enabled=${String(!module.enabled)}.`);
      await loadModules();
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Failed to update module.";
      setModuleError(detail);
    } finally {
      setModuleToggleBusyId(null);
    }
  }

  async function runJobsMaintenance(kind: "enqueue"): Promise<void> {
    if (maintenanceConfirmation.trim().toUpperCase() !== MAINTENANCE_CONFIRM_TOKEN) {
      setJobError(`Type ${MAINTENANCE_CONFIRM_TOKEN} to confirm maintenance actions.`);
      return;
    }

    setJobMaintenanceBusy(kind);
    setJobError(null);
    setJobMessage(null);

    const path = `/api/admin/jobs/enqueue-freshness?${encodeAdminQuery({ limit: maintenanceLimit })}`;

    try {
      const response = await fetch(path, { method: "POST" });
      const payload: unknown = await response.json();
      if (!response.ok) {
        throw new Error(getApiErrorDetail(payload, "Failed to run jobs maintenance action."));
      }

      const count = parseAdminCount(payload);
      setJobMessage(`Enqueued ${count} freshness jobs.`);
      await loadJobs();
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Failed to run jobs maintenance action.";
      setJobError(detail);
    } finally {
      setJobMaintenanceBusy(null);
    }
  }

  return (
    <section className="admin-grid">
      <article className="panel">
        <h2>Candidate Queue Filters</h2>
        <div className="control-grid">
          <label className="control">
            <span>State</span>
            <select
              value={candidateStateFilter}
              onChange={(event) => applyCandidateStateFilter(event.target.value as CandidateStateFilter)}
            >
              <option value="all">all</option>
              {CANDIDATE_STATES.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>

          <label className="control">
            <span>Source</span>
            <select value={candidateSourceFilter} onChange={(event) => applyCandidateSourceFilter(event.target.value)}>
              <option value="all">all</option>
              {sourceFacetOptions.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.value}
                </option>
              ))}
            </select>
          </label>

          <label className="control">
            <span>Age</span>
            <select value={candidateAgeFilter} onChange={(event) => applyCandidateAgeFilter(event.target.value as CandidateAgeFilter)}>
              <option value="all">all</option>
              {QUEUE_AGE_BUCKETS.map((bucket) => (
                <option key={bucket.value} value={bucket.value}>
                  {bucket.label}
                </option>
              ))}
            </select>
          </label>

          <label className="control">
            <span>Limit</span>
            <input
              value={candidateLimit}
              onChange={(event) =>
                setCandidateLimit(
                  coerceBoundedInteger(event.target.value, {
                    min: 1,
                    max: CANDIDATE_LIMIT_MAX,
                    fallback: candidateLimit
                  })
                )
              }
              type="number"
              min={1}
              max={CANDIDATE_LIMIT_MAX}
            />
          </label>

          <label className="control">
            <span>Offset</span>
            <input
              value={candidateOffset}
              onChange={(event) => setCandidateOffset(Math.max(0, Number(event.target.value) || 0))}
              type="number"
              min={0}
            />
          </label>
        </div>

        <div className="facet-groups">
          <p className="status">
            Quick filters with queue counts by <code>state</code>, <code>source</code>, and <code>age</code>.
          </p>
          <div className="facet-row">
            <button
              className={`facet-chip ${candidateStateFilter === "all" ? "facet-chip-active" : ""}`}
              type="button"
              onClick={() => applyCandidateStateFilter("all")}
            >
              state: all <span className="facet-chip-count">{candidateFacets.total}</span>
            </button>
            {CANDIDATE_STATES.map((state) => (
              <button
                key={`state-${state}`}
                className={`facet-chip ${candidateStateFilter === state ? "facet-chip-active" : ""}`}
                type="button"
                onClick={() => applyCandidateStateFilter(state)}
              >
                {state} <span className="facet-chip-count">{stateFacetCountByValue.get(state) ?? 0}</span>
              </button>
            ))}
          </div>
          <div className="facet-row">
            <button
              className={`facet-chip ${candidateSourceFilter === "all" ? "facet-chip-active" : ""}`}
              type="button"
              onClick={() => applyCandidateSourceFilter("all")}
            >
              source: all <span className="facet-chip-count">{candidateFacets.total}</span>
            </button>
            {sourceFacetOptions.slice(0, 8).map((sourceFacet) => (
              <button
                key={`source-${sourceFacet.value}`}
                className={`facet-chip ${candidateSourceFilter === sourceFacet.value ? "facet-chip-active" : ""}`}
                type="button"
                onClick={() => applyCandidateSourceFilter(sourceFacet.value)}
              >
                {sourceFacet.value} <span className="facet-chip-count">{sourceFacet.count}</span>
              </button>
            ))}
          </div>
          <div className="facet-row">
            <button
              className={`facet-chip ${candidateAgeFilter === "all" ? "facet-chip-active" : ""}`}
              type="button"
              onClick={() => applyCandidateAgeFilter("all")}
            >
              age: all <span className="facet-chip-count">{candidateFacets.total}</span>
            </button>
            {QUEUE_AGE_BUCKETS.map((bucket) => (
              <button
                key={`age-${bucket.value}`}
                className={`facet-chip ${candidateAgeFilter === bucket.value ? "facet-chip-active" : ""}`}
                type="button"
                onClick={() => applyCandidateAgeFilter(bucket.value)}
              >
                {bucket.label} <span className="facet-chip-count">{ageFacetCountByValue.get(bucket.value) ?? 0}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="actions">
          <button
            className="button button-primary"
            type="button"
            onClick={() =>
              void Promise.all([
                loadCandidates(),
                loadCandidateFacets()
              ])
            }
          >
            Refresh Candidates
          </button>
          <button
            className="button"
            type="button"
            onClick={() => {
              applyCandidateStateFilter("all");
              applyCandidateSourceFilter("all");
              applyCandidateAgeFilter("all");
            }}
          >
            Reset Quick Filters
          </button>
          <button className="button" type="button" onClick={handleSelectAllCandidatesOnPage} disabled={candidates.length === 0}>
            Select All On Page
          </button>
          <button className="button" type="button" onClick={handleClearCandidateSelection} disabled={selectedCandidateIds.length === 0}>
            Clear Selection
          </button>
          <p className="status">
            Selected <strong>{selectedCandidateIds.length}</strong> of {candidates.length} candidate(s) on this page.
          </p>
          {candidateListLoading ? <p className="status">Loading candidates…</p> : null}
          {candidateListError ? <p className="status status-error">{candidateListError}</p> : null}
          {candidateFacetLoading ? <p className="status">Loading queue facets…</p> : null}
          {candidateFacetError ? <p className="status status-error">{candidateFacetError}</p> : null}
          {candidateMessage ? <p className="status status-ok">{candidateMessage}</p> : null}
          {candidateActionError ? <p className="status status-error">{candidateActionError}</p> : null}
          {bulkActionMessage ? <p className="status status-ok">{bulkActionMessage}</p> : null}
          {bulkActionError ? <p className="status status-error">{bulkActionError}</p> : null}
        </div>
      </article>

      <article className="panel">
        <h2>Selected Candidate Actions</h2>
        <p className="status">
          {selectedCandidate
            ? `${selectedCandidate.id} (${selectedCandidate.state})`
            : "Select a candidate from the queue table."}
        </p>

        <form className="stack" onSubmit={(event) => void handlePatch(event)}>
          <h3 className="small-heading">Approve / Reject</h3>
          <label className="control">
            <span>State</span>
            <select value={patchState} onChange={(event) => setPatchState(event.target.value as CandidateState)}>
              {patchStateOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          {selectedCandidate ? (
            <p className="status">
              Patch transitions from <code>{selectedCandidate.state}</code>: {patchStateOptions.join(", ")}.
            </p>
          ) : null}
          <label className="control">
            <span>Reason</span>
            <input
              value={patchReason}
              onChange={(event) => setPatchReason(event.target.value)}
              placeholder={requiresPatchReason(patchState) ? "Required for rejected/archived/closed" : "Optional state-change reason"}
            />
          </label>
          <button className="button" type="submit" disabled={patchSubmitDisabled}>
            {candidateActionBusy === "patch" ? "Applying…" : "Apply State Patch"}
          </button>
        </form>

        <form className="stack" onSubmit={(event) => void handleMerge(event)}>
          <h3 className="small-heading">Merge</h3>
          <label className="control">
            <span>Quick Pick Candidate</span>
            <select
              value={mergeCandidateOptions.some((candidate) => candidate.id === mergeSecondaryCandidateId) ? mergeSecondaryCandidateId : ""}
              onChange={(event) => setMergeSecondaryCandidateId(event.target.value)}
            >
              <option value="">manual entry</option>
              {mergeCandidateOptions.map((candidate) => (
                <option key={candidate.id} value={candidate.id}>
                  {coerceTitle(candidate.extracted_fields)} ({candidate.state})
                </option>
              ))}
            </select>
          </label>
          <label className="control">
            <span>Secondary Candidate ID</span>
            <input
              value={mergeSecondaryCandidateId}
              onChange={(event) => setMergeSecondaryCandidateId(event.target.value)}
              placeholder="UUID"
            />
          </label>
          <label className="control">
            <span>Reason</span>
            <input
              value={mergeReason}
              onChange={(event) => setMergeReason(event.target.value)}
              placeholder="Required merge reason"
            />
          </label>
          <button className="button" type="submit" disabled={mergeSubmitDisabled}>
            {candidateActionBusy === "merge" ? "Merging…" : "Merge Candidate"}
          </button>
        </form>

        <form className="stack" onSubmit={(event) => void handleOverride(event)}>
          <h3 className="small-heading">Override</h3>
          <label className="control">
            <span>State</span>
            <select value={overrideState} onChange={(event) => setOverrideState(event.target.value as CandidateState)}>
              {CANDIDATE_STATES.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <label className="control">
            <span>Posting Status (optional)</span>
            <select
              value={overridePostingStatus}
              onChange={(event) => setOverridePostingStatus(event.target.value as "" | PostingStatus)}
            >
              <option value="">no_change</option>
              {POSTING_STATUSES.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <label className="control">
            <span>Reason</span>
            <input
              value={overrideReason}
              onChange={(event) => setOverrideReason(event.target.value)}
              placeholder="Required override reason"
            />
          </label>
          <button className="button" type="submit" disabled={overrideSubmitDisabled}>
            {candidateActionBusy === "override" ? "Overriding…" : "Apply Override"}
          </button>
        </form>

        <form className="stack" onSubmit={(event) => void handleBulkPatch(event)}>
          <h3 className="small-heading">Bulk Patch</h3>
          <p className="status">
            Apply one state transition across selected candidates in the queue table.
          </p>
          <label className="control">
            <span>State</span>
            <select value={bulkPatchState} onChange={(event) => setBulkPatchState(event.target.value as CandidateState)}>
              {CANDIDATE_STATES.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <label className="control">
            <span>Reason</span>
            <input
              value={bulkPatchReason}
              onChange={(event) => setBulkPatchReason(event.target.value)}
              placeholder={requiresPatchReason(bulkPatchState) ? "Required for rejected/archived/closed" : "Optional bulk reason"}
            />
          </label>
          <p className="status">
            Transition-ready: {selectedCandidateRows.length - bulkTransitionBlockedCandidates.length} / {selectedCandidateRows.length}
          </p>
          {bulkTransitionBlockedCandidates.length > 0 ? (
            <p className="status status-error">
              Invalid transitions for selected candidates: {bulkTransitionBlockedCandidates.slice(0, 3).join(", ")}
              {bulkTransitionBlockedCandidates.length > 3 ? ", ..." : ""}.
            </p>
          ) : null}
          <button className="button" type="submit" disabled={bulkSubmitDisabled}>
            {bulkActionBusy ? "Applying Bulk Patch…" : "Apply Bulk Patch"}
          </button>
        </form>
      </article>

      <article className="panel panel-wide">
        <h2>Candidate Queue</h2>
        <div className="table-wrap">
          <table className="policy-table">
            <thead>
              <tr>
                <th>Select</th>
                <th>Candidate</th>
                <th>State</th>
                <th>Dedupe</th>
                <th>Risk Flags</th>
                <th>Updated</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {candidateListLoading ? (
                <tr>
                  <td colSpan={7}>Loading candidate queue…</td>
                </tr>
              ) : candidateListError ? (
                <tr>
                  <td colSpan={7}>Unable to load candidate queue: {candidateListError}</td>
                </tr>
              ) : candidates.length === 0 ? (
                <tr>
                  <td colSpan={7}>No candidates found for current filters. Adjust state/offset or refresh.</td>
                </tr>
              ) : (
                candidates.map((candidate) => (
                  <tr key={candidate.id}>
                    <td>
                      <input
                        aria-label={`Select candidate ${candidate.id}`}
                        type="checkbox"
                        checked={selectedCandidateIds.includes(candidate.id)}
                        onChange={(event) => handleCandidateCheckboxToggle(candidate.id, event.target.checked)}
                      />
                    </td>
                    <td>
                      <div>
                        <strong>{coerceTitle(candidate.extracted_fields)}</strong>
                      </div>
                      <code>{candidate.id}</code>
                    </td>
                    <td>{candidate.state}</td>
                    <td>{candidate.dedupe_confidence ?? "-"}</td>
                    <td>{candidate.risk_flags.length > 0 ? candidate.risk_flags.join(", ") : "-"}</td>
                    <td>{formatTimestamp(candidate.updated_at)}</td>
                    <td>
                      <button
                        className="button button-ghost"
                        type="button"
                        onClick={() => handleCandidateQuickSelect(candidate.id)}
                      >
                        {selectedCandidateId === candidate.id ? "Selected" : "Select"}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </article>

      <article className="panel">
        <h2>Modules</h2>
        <div className="control-grid">
          <label className="control">
            <span>Module ID</span>
            <input value={moduleIdFilter} onChange={(event) => setModuleIdFilter(event.target.value)} />
          </label>

          <label className="control">
            <span>Kind</span>
            <select value={moduleKindFilter} onChange={(event) => setModuleKindFilter(event.target.value as ModuleKindFilter)}>
              <option value="all">all</option>
              {MODULE_KINDS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>

          <label className="control">
            <span>Enabled</span>
            <select value={moduleEnabledFilter} onChange={(event) => setModuleEnabledFilter(event.target.value as BoolFilter)}>
              <option value="all">all</option>
              <option value="true">true</option>
              <option value="false">false</option>
            </select>
          </label>

          <label className="control">
            <span>Limit</span>
            <input
              value={moduleLimit}
              onChange={(event) =>
                setModuleLimit(
                  coerceBoundedInteger(event.target.value, {
                    min: 1,
                    max: MODULE_LIMIT_MAX,
                    fallback: moduleLimit
                  })
                )
              }
              type="number"
              min={1}
              max={MODULE_LIMIT_MAX}
            />
          </label>

          <label className="control">
            <span>Offset</span>
            <input
              value={moduleOffset}
              onChange={(event) => setModuleOffset(Math.max(0, Number(event.target.value) || 0))}
              type="number"
              min={0}
            />
          </label>
        </div>
        <div className="actions">
          <button className="button button-primary" type="button" onClick={() => void loadModules()}>
            Refresh Modules
          </button>
          {moduleListLoading ? <p className="status">Loading modules…</p> : null}
          {moduleError ? <p className="status status-error">{moduleError}</p> : null}
          {moduleMessage ? <p className="status status-ok">{moduleMessage}</p> : null}
        </div>
      </article>

      <article className="panel">
        <h2>Jobs</h2>
        <div className="control-grid">
          <label className="control">
            <span>Status</span>
            <select value={jobStatusFilter} onChange={(event) => setJobStatusFilter(event.target.value as JobStatusFilter)}>
              <option value="all">all</option>
              {JOB_STATUSES.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>

          <label className="control">
            <span>Kind</span>
            <select value={jobKindFilter} onChange={(event) => setJobKindFilter(event.target.value as JobKindFilter)}>
              <option value="all">all</option>
              {JOB_KINDS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>

          <label className="control">
            <span>Target Type</span>
            <input value={jobTargetTypeFilter} onChange={(event) => setJobTargetTypeFilter(event.target.value)} />
          </label>

          <label className="control">
            <span>Limit</span>
            <input
              value={jobLimit}
              onChange={(event) =>
                setJobLimit(
                  coerceBoundedInteger(event.target.value, {
                    min: 1,
                    max: JOB_LIMIT_MAX,
                    fallback: jobLimit
                  })
                )
              }
              type="number"
              min={1}
              max={JOB_LIMIT_MAX}
            />
          </label>

          <label className="control">
            <span>Offset</span>
            <input
              value={jobOffset}
              onChange={(event) => setJobOffset(Math.max(0, Number(event.target.value) || 0))}
              type="number"
              min={0}
            />
          </label>

          <label className="control">
            <span>Maintenance Limit</span>
            <input
              value={maintenanceLimit}
              onChange={(event) =>
                setMaintenanceLimit(
                  coerceBoundedInteger(event.target.value, {
                    min: 1,
                    max: MAINTENANCE_LIMIT_MAX,
                    fallback: maintenanceLimit
                  })
                )
              }
              type="number"
              min={1}
              max={MAINTENANCE_LIMIT_MAX}
            />
          </label>
          <label className="control">
            <span>Maintenance Confirmation</span>
            <input
              value={maintenanceConfirmation}
              onChange={(event) => setMaintenanceConfirmation(event.target.value)}
              placeholder={`Type ${MAINTENANCE_CONFIRM_TOKEN}`}
            />
          </label>
        </div>
        <p className="status">
          High-impact maintenance actions require confirmation: <code>{MAINTENANCE_CONFIRM_TOKEN}</code>.
        </p>

        <div className="actions">
          <button className="button button-primary" type="button" onClick={() => void loadJobs()}>
            Refresh Jobs
          </button>
          <button
            className="button"
            type="button"
            onClick={() => void runJobsMaintenance("enqueue")}
            disabled={
              jobMaintenanceBusy !== null ||
              maintenanceConfirmation.trim().toUpperCase() !== MAINTENANCE_CONFIRM_TOKEN
            }
          >
            {jobMaintenanceBusy === "enqueue" ? "Running…" : "Enqueue Freshness"}
          </button>
          {jobListLoading ? <p className="status">Loading jobs…</p> : null}
          {jobError ? <p className="status status-error">{jobError}</p> : null}
          {jobMessage ? <p className="status status-ok">{jobMessage}</p> : null}
        </div>
      </article>

      <article className="panel panel-wide">
        <h2>Modules Table</h2>
        <div className="table-wrap">
          <table className="policy-table">
            <thead>
              <tr>
                <th>Module</th>
                <th>Kind</th>
                <th>Trust</th>
                <th>Scopes</th>
                <th>Enabled</th>
                <th>Updated</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {moduleListLoading ? (
                <tr>
                  <td colSpan={7}>Loading modules…</td>
                </tr>
              ) : moduleError ? (
                <tr>
                  <td colSpan={7}>Unable to load modules: {moduleError}</td>
                </tr>
              ) : modules.length === 0 ? (
                <tr>
                  <td colSpan={7}>No modules found for current filters.</td>
                </tr>
              ) : (
                modules.map((module) => (
                  <tr key={module.id}>
                    <td>
                      <div>
                        <strong>{module.name}</strong>
                      </div>
                      <code>{module.module_id}</code>
                    </td>
                    <td>{module.kind}</td>
                    <td>{module.trust_level}</td>
                    <td>{module.scopes.length > 0 ? module.scopes.join(", ") : "-"}</td>
                    <td>{String(module.enabled)}</td>
                    <td>{formatTimestamp(module.updated_at)}</td>
                    <td>
                      <button
                        className="button button-ghost"
                        type="button"
                        onClick={() => void handleModuleToggle(module)}
                        disabled={moduleToggleBusyId === module.module_id}
                      >
                        {moduleToggleBusyId === module.module_id
                          ? "Updating…"
                          : module.enabled
                            ? "Disable"
                            : "Enable"}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </article>

      <article className="panel panel-wide">
        <h2>Jobs Table</h2>
        <div className="table-wrap">
          <table className="policy-table">
            <thead>
              <tr>
                <th>Job</th>
                <th>Kind</th>
                <th>Status</th>
                <th>Target</th>
                <th>Attempt</th>
                <th>Operator Visibility</th>
                <th>Lease Expires</th>
                <th>Next Run</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {jobListLoading ? (
                <tr>
                  <td colSpan={9}>Loading jobs…</td>
                </tr>
              ) : jobError && jobs.length === 0 ? (
                <tr>
                  <td colSpan={9}>Unable to load jobs: {jobError}</td>
                </tr>
              ) : jobs.length === 0 ? (
                <tr>
                  <td colSpan={9}>No jobs found for current filters.</td>
                </tr>
              ) : (
                jobs.map((job) => {
                const inputs = asObject(job.inputs_json);
                const result = asObject(job.result_json);
                const error = asObject(job.error_json);
                const retryLabel = job.status === "queued" && job.attempt > 0 ? formatRetryWindow(job.next_run_at) : null;
                const redirectVisibility = describeRedirectVisibility(job);
                const errorSummary = describeJobError(error);

                return (
                  <tr key={job.id}>
                    <td>
                      <code>{job.id}</code>
                    </td>
                    <td>{job.kind}</td>
                    <td>{job.status}</td>
                    <td>
                      <div>{job.target_type}</div>
                      <code>{job.target_id ?? "-"}</code>
                    </td>
                    <td>{job.attempt}</td>
                    <td>
                      {retryLabel ? <p className="status">{retryLabel}</p> : null}
                      {redirectVisibility.map((detail) => (
                        <p key={`${job.id}-${detail}`} className="status">
                          {detail}
                        </p>
                      ))}
                      {errorSummary ? <p className="status status-error">{errorSummary}</p> : null}
                      <details className="job-details">
                        <summary>Inspect payloads</summary>
                        <p className="status">inputs_json</p>
                        <pre>{formatJobPayload(inputs)}</pre>
                        <p className="status">result_json</p>
                        <pre>{formatJobPayload(result)}</pre>
                        <p className="status">error_json</p>
                        <pre>{formatJobPayload(error)}</pre>
                      </details>
                    </td>
                    <td>{formatTimestamp(job.lease_expires_at)}</td>
                    <td>
                      <div>{formatTimestamp(job.next_run_at)}</div>
                      <p className="status">{formatOperatorTimestamp(job.next_run_at)}</p>
                    </td>
                    <td>{formatTimestamp(job.updated_at)}</td>
                  </tr>
                );
              })
              )}
            </tbody>
          </table>
        </div>
      </article>
    </section>
  );
}
