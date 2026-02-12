"use client";

import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import {
  coerceTitle,
  type AdminJob,
  type AdminModule,
  type Candidate,
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
type ModuleKindFilter = "all" | ModuleKind;
type JobKindFilter = "all" | JobKind;
type JobStatusFilter = "all" | JobStatus;

type CandidateAction = "patch" | "merge" | "override";

const PATCH_REASON_REQUIRED_STATES = new Set<CandidateState>(["rejected", "archived", "closed"]);

function requiresPatchReason(state: CandidateState): boolean {
  return PATCH_REASON_REQUIRED_STATES.has(state);
}

export function ModeratorCockpitClient(): JSX.Element {
  const [candidateStateFilter, setCandidateStateFilter] = useState<CandidateStateFilter>("needs_review");
  const [candidateLimit, setCandidateLimit] = useState(50);
  const [candidateOffset, setCandidateOffset] = useState(0);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [candidateListLoading, setCandidateListLoading] = useState(false);
  const [candidateListError, setCandidateListError] = useState<string | null>(null);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string>("");

  const [patchState, setPatchState] = useState<CandidateState>("publishable");
  const [patchReason, setPatchReason] = useState("");
  const [mergeSecondaryCandidateId, setMergeSecondaryCandidateId] = useState("");
  const [mergeReason, setMergeReason] = useState("");
  const [overrideState, setOverrideState] = useState<CandidateState>("publishable");
  const [overrideReason, setOverrideReason] = useState("");
  const [overridePostingStatus, setOverridePostingStatus] = useState<"" | PostingStatus>("");
  const [candidateActionBusy, setCandidateActionBusy] = useState<CandidateAction | null>(null);
  const [candidateMessage, setCandidateMessage] = useState<string | null>(null);
  const [candidateActionError, setCandidateActionError] = useState<string | null>(null);

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
  const [jobMaintenanceBusy, setJobMaintenanceBusy] = useState<"enqueue" | "reap" | null>(null);

  const candidateQueryString = useMemo(
    () =>
      encodeAdminQuery({
        state: candidateStateFilter === "all" ? undefined : candidateStateFilter,
        limit: candidateLimit,
        offset: candidateOffset
      }),
    [candidateLimit, candidateOffset, candidateStateFilter]
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
  const patchStateOptions = useMemo(
    () => listPatchCandidateStates(selectedCandidate?.state ?? null, CANDIDATE_STATES),
    [selectedCandidate]
  );
  const mergeCandidateOptions = useMemo(
    () => candidates.filter((candidate) => candidate.id !== selectedCandidateId),
    [candidates, selectedCandidateId]
  );
  const patchSubmitDisabled =
    candidateActionBusy !== null || !selectedCandidateId || (requiresPatchReason(patchState) && patchReason.trim().length === 0);
  const mergeSubmitDisabled =
    candidateActionBusy !== null ||
    !selectedCandidateId ||
    mergeSecondaryCandidateId.trim().length === 0 ||
    mergeReason.trim().length === 0;
  const overrideSubmitDisabled =
    candidateActionBusy !== null || !selectedCandidateId || overrideReason.trim().length === 0;

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
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Failed to load candidates.";
      setCandidateListError(detail);
      setCandidates([]);
      setSelectedCandidateId("");
    } finally {
      setCandidateListLoading(false);
    }
  }, [candidateQueryString, selectedCandidateId]);

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

  async function runJobsMaintenance(kind: "enqueue" | "reap"): Promise<void> {
    if (maintenanceConfirmation.trim().toUpperCase() !== MAINTENANCE_CONFIRM_TOKEN) {
      setJobError(`Type ${MAINTENANCE_CONFIRM_TOKEN} to confirm maintenance actions.`);
      return;
    }

    setJobMaintenanceBusy(kind);
    setJobError(null);
    setJobMessage(null);

    const path =
      kind === "enqueue"
        ? `/api/admin/jobs/enqueue-freshness?${encodeAdminQuery({ limit: maintenanceLimit })}`
        : `/api/admin/jobs/reap-expired?${encodeAdminQuery({ limit: maintenanceLimit })}`;

    try {
      const response = await fetch(path, { method: "POST" });
      const payload: unknown = await response.json();
      if (!response.ok) {
        throw new Error(getApiErrorDetail(payload, "Failed to run jobs maintenance action."));
      }

      const count = parseAdminCount(payload);
      setJobMessage(
        kind === "enqueue"
          ? `Enqueued ${count} freshness jobs.`
          : `Requeued ${count} expired claimed jobs.`
      );
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
              onChange={(event) => setCandidateStateFilter(event.target.value as CandidateStateFilter)}
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

        <div className="actions">
          <button className="button button-primary" type="button" onClick={() => void loadCandidates()}>
            Refresh Candidates
          </button>
          {candidateListLoading ? <p className="status">Loading candidates…</p> : null}
          {candidateListError ? <p className="status status-error">{candidateListError}</p> : null}
          {candidateMessage ? <p className="status status-ok">{candidateMessage}</p> : null}
          {candidateActionError ? <p className="status status-error">{candidateActionError}</p> : null}
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
      </article>

      <article className="panel panel-wide">
        <h2>Candidate Queue</h2>
        <div className="table-wrap">
          <table className="policy-table">
            <thead>
              <tr>
                <th>Candidate</th>
                <th>State</th>
                <th>Dedupe</th>
                <th>Risk Flags</th>
                <th>Updated</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((candidate) => (
                <tr key={candidate.id}>
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
                      onClick={() => setSelectedCandidateId(candidate.id)}
                    >
                      {selectedCandidateId === candidate.id ? "Selected" : "Select"}
                    </button>
                  </td>
                </tr>
              ))}
              {candidates.length === 0 ? (
                <tr>
                  <td colSpan={6}>No candidates found for current filters.</td>
                </tr>
              ) : null}
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
          <button
            className="button"
            type="button"
            onClick={() => void runJobsMaintenance("reap")}
            disabled={
              jobMaintenanceBusy !== null ||
              maintenanceConfirmation.trim().toUpperCase() !== MAINTENANCE_CONFIRM_TOKEN
            }
          >
            {jobMaintenanceBusy === "reap" ? "Running…" : "Reap Expired"}
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
              {modules.map((module) => (
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
              ))}
              {modules.length === 0 ? (
                <tr>
                  <td colSpan={7}>No modules found for current filters.</td>
                </tr>
              ) : null}
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
                <th>Lease Expires</th>
                <th>Next Run</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
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
                  <td>{formatTimestamp(job.lease_expires_at)}</td>
                  <td>{formatTimestamp(job.next_run_at)}</td>
                  <td>{formatTimestamp(job.updated_at)}</td>
                </tr>
              ))}
              {jobs.length === 0 ? (
                <tr>
                  <td colSpan={8}>No jobs found for current filters.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </article>
    </section>
  );
}
