import { expect, test, type Route } from "@playwright/test";

type CandidateState =
  | "discovered"
  | "processed"
  | "publishable"
  | "published"
  | "rejected"
  | "closed"
  | "archived"
  | "needs_review";

type CandidateRecord = {
  id: string;
  state: CandidateState;
  dedupe_confidence: number | null;
  risk_flags: string[];
  extracted_fields: Record<string, unknown>;
  discovery_ids: string[];
  posting_id: string | null;
  created_at: string;
  updated_at: string;
};

type ModuleRecord = {
  id: string;
  module_id: string;
  name: string;
  kind: "connector" | "processor";
  enabled: boolean;
  scopes: string[];
  trust_level: "trusted" | "semi_trusted" | "untrusted";
  created_at: string;
  updated_at: string;
};

type JobRecord = {
  id: string;
  kind: "dedupe" | "extract" | "enrich" | "check_freshness" | "resolve_url_redirects";
  target_type: string;
  target_id: string | null;
  status: "queued" | "claimed" | "done" | "failed" | "dead_letter";
  attempt: number;
  locked_by_module_id: string | null;
  lease_expires_at: string | null;
  next_run_at: string;
  created_at: string;
  updated_at: string;
};

type Capture = {
  mergeBodies: Array<{ secondary_candidate_id: string; reason?: string }>;
  patchBodies: Array<{ state: CandidateState; reason?: string }>;
  overrideBodies: Array<{ state: CandidateState; reason?: string; posting_status?: string }>;
  moduleBodies: Array<{ enabled: boolean }>;
  enqueueCalls: number;
  reapCalls: number;
};

const PRIMARY_CANDIDATE_ID = "6f45bcbf-8dc2-4c70-a35d-e8732898a0eb";
const SECONDARY_CANDIDATE_ID = "514bb58e-a5f2-49de-aa90-a655fdf22d40";
const POSTING_ID = "12cad25c-7e6e-47a1-b695-e6b1ae3c3409";
const LOCAL_PROCESSOR_ID = "local-processor";

function jsonResponse(route: Route, payload: unknown, status = 200): Promise<void> {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(payload)
  });
}

test("admin cockpit handles candidate, module, and jobs operator actions", async ({ page }) => {
  const startedAt = "2026-02-10T20:02:39.338252Z";
  let postingStatus: "active" | "stale" | "archived" | "closed" = "active";

  const candidate: CandidateRecord = {
    id: PRIMARY_CANDIDATE_ID,
    state: "needs_review",
    dedupe_confidence: 0.91,
    risk_flags: ["manual_review_needed"],
    extracted_fields: {
      title: "E2E Primary Candidate",
      source_key: "default:untrusted"
    },
    discovery_ids: ["c0315d98-ef37-49a3-b7ba-1cae768c8964"],
    posting_id: POSTING_ID,
    created_at: startedAt,
    updated_at: startedAt
  };

  const modules: ModuleRecord[] = [
    {
      id: "connector-1",
      module_id: "local-connector",
      name: "Local Connector",
      kind: "connector",
      enabled: true,
      scopes: ["discoveries:write", "evidence:write"],
      trust_level: "trusted",
      created_at: startedAt,
      updated_at: startedAt
    },
    {
      id: "processor-1",
      module_id: LOCAL_PROCESSOR_ID,
      name: "Local Processor",
      kind: "processor",
      enabled: true,
      scopes: ["jobs:read", "jobs:write"],
      trust_level: "trusted",
      created_at: startedAt,
      updated_at: startedAt
    }
  ];

  const jobs: JobRecord[] = [
    {
      id: "7c8f0543-bcdd-43f4-a366-869a88feb202",
      kind: "extract",
      target_type: "discovery",
      target_id: "ce9ac1af-5b1f-4afd-afea-096085beaf48",
      status: "done",
      attempt: 1,
      locked_by_module_id: null,
      lease_expires_at: null,
      next_run_at: startedAt,
      created_at: startedAt,
      updated_at: startedAt
    }
  ];

  const capture: Capture = {
    mergeBodies: [],
    patchBodies: [],
    overrideBodies: [],
    moduleBodies: [],
    enqueueCalls: 0,
    reapCalls: 0
  };

  await page.route(/\/api\/admin\/candidates\/[^/?]+\/merge(?:\?.*)?$/, async (route) => {
    if (route.request().method() !== "POST") {
      return route.fulfill({ status: 405 });
    }
    const body = route.request().postDataJSON() as { secondary_candidate_id: string; reason?: string };
    capture.mergeBodies.push(body);
    const mergedDiscoveryIds = [...new Set([...candidate.discovery_ids, SECONDARY_CANDIDATE_ID])];
    candidate.discovery_ids = mergedDiscoveryIds;
    return jsonResponse(route, candidate);
  });

  await page.route(/\/api\/admin\/candidates\/[^/?]+\/override(?:\?.*)?$/, async (route) => {
    if (route.request().method() !== "POST") {
      return route.fulfill({ status: 405 });
    }
    const body = route.request().postDataJSON() as {
      state: CandidateState;
      reason?: string;
      posting_status?: string;
    };
    capture.overrideBodies.push(body);
    candidate.state = body.state;
    candidate.updated_at = "2026-02-10T20:05:49.458526Z";
    if (body.posting_status === "active" || body.posting_status === "stale" || body.posting_status === "archived" || body.posting_status === "closed") {
      postingStatus = body.posting_status;
    }
    return jsonResponse(route, candidate);
  });

  await page.route(/\/api\/admin\/candidates\/[^/?]+(?:\?.*)?$/, async (route) => {
    if (route.request().method() !== "PATCH") {
      return route.fulfill({ status: 405 });
    }
    const body = route.request().postDataJSON() as { state: CandidateState; reason?: string };
    capture.patchBodies.push(body);
    candidate.state = body.state;
    candidate.updated_at = "2026-02-10T20:05:14.752532Z";
    return jsonResponse(route, candidate);
  });

  await page.route(/\/api\/admin\/candidates(?:\?.*)?$/, async (route) => {
    const url = new URL(route.request().url());
    const state = url.searchParams.get("state");
    const data = state ? (candidate.state === state ? [candidate] : []) : [candidate];
    return jsonResponse(route, data);
  });

  await page.route(/\/api\/admin\/modules\/[^/?]+(?:\?.*)?$/, async (route) => {
    if (route.request().method() !== "PATCH") {
      return route.fulfill({ status: 405 });
    }
    const body = route.request().postDataJSON() as { enabled: boolean };
    capture.moduleBodies.push(body);
    const module = modules.find((row) => row.module_id === LOCAL_PROCESSOR_ID);
    if (module) {
      module.enabled = body.enabled;
      module.updated_at = body.enabled ? "2026-02-10T20:06:17.830493Z" : "2026-02-10T20:05:58.843173Z";
    }
    return jsonResponse(route, module ?? { detail: "module not found" }, module ? 200 : 404);
  });

  await page.route(/\/api\/admin\/modules(?:\?.*)?$/, async (route) => {
    const url = new URL(route.request().url());
    const moduleId = url.searchParams.get("module_id") ?? url.searchParams.get("moduleId");
    if (moduleId) {
      return jsonResponse(route, modules.filter((module) => module.module_id === moduleId));
    }
    return jsonResponse(route, modules);
  });

  await page.route(/\/api\/admin\/jobs\/enqueue-freshness(?:\?.*)?$/, async (route) => {
    capture.enqueueCalls += 1;
    return jsonResponse(route, { count: 0 });
  });

  await page.route(/\/api\/admin\/jobs\/reap-expired(?:\?.*)?$/, async (route) => {
    capture.reapCalls += 1;
    return jsonResponse(route, { count: 0 });
  });

  await page.route(/\/api\/admin\/jobs(?:\?.*)?$/, async (route) => {
    return jsonResponse(route, jobs);
  });

  await page.goto("/admin/cockpit");

  await expect(page.getByRole("heading", { name: "Operator Cockpit" })).toBeVisible();
  const initialCandidateRow = page
    .locator("article:has(h2:text-is('Candidate Queue')) tbody tr")
    .filter({ hasText: PRIMARY_CANDIDATE_ID });
  await expect(initialCandidateRow).toHaveCount(1);

  const actionForms = page.locator("article:has(h2:text-is('Selected Candidate Actions')) form");
  const patchForm = actionForms.nth(0);
  const mergeForm = actionForms.nth(1);
  const overrideForm = actionForms.nth(2);

  await mergeForm.getByLabel("Secondary Candidate ID").fill(SECONDARY_CANDIDATE_ID);
  await mergeForm.getByLabel("Reason").fill("merge validation via playwright");
  await mergeForm.getByRole("button", { name: "Merge Candidate" }).click();
  await expect(page.getByText(`Candidate merge action completed for ${PRIMARY_CANDIDATE_ID}.`)).toBeVisible();

  await patchForm.getByLabel("State").selectOption("publishable");
  await patchForm.getByLabel("Reason").fill("approve path validation via playwright");
  await patchForm.getByRole("button", { name: "Apply State Patch" }).click();
  await expect(page.getByText(`Candidate patch action completed for ${PRIMARY_CANDIDATE_ID}.`)).toBeVisible();
  await expect(page.getByText("No candidates found for current filters.")).toBeVisible();

  const queueFilters = page.locator("article:has(h2:text-is('Candidate Queue Filters'))");
  await queueFilters.getByLabel("State").selectOption("publishable");
  await queueFilters.getByRole("button", { name: "Refresh Candidates" }).click();
  await expect(page.getByText(`${PRIMARY_CANDIDATE_ID} (publishable)`)).toBeVisible();

  await overrideForm.getByLabel("State").selectOption("rejected");
  await overrideForm.getByLabel("Posting Status (optional)").selectOption("archived");
  await overrideForm.getByLabel("Reason").fill("override validation via playwright");
  await overrideForm.getByRole("button", { name: "Apply Override" }).click();
  await expect(page.getByText(`Candidate override action completed for ${PRIMARY_CANDIDATE_ID}.`)).toBeVisible();

  const processorRow = page.locator("article:has(h2:text-is('Modules Table')) tbody tr").filter({
    hasText: LOCAL_PROCESSOR_ID
  });

  await processorRow.getByRole("button", { name: "Disable" }).click();
  await expect(page.getByText("Updated local-processor enabled=false.")).toBeVisible();
  await expect(processorRow).toContainText("false");

  await processorRow.getByRole("button", { name: "Enable" }).click();
  await expect(page.getByText("Updated local-processor enabled=true.")).toBeVisible();
  await expect(processorRow).toContainText("true");

  await page.getByRole("button", { name: "Enqueue Freshness" }).click();
  await expect(page.getByText("Enqueued 0 freshness jobs.")).toBeVisible();

  await page.getByRole("button", { name: "Reap Expired" }).click();
  await expect(page.getByText("Requeued 0 expired claimed jobs.")).toBeVisible();

  expect(capture.mergeBodies).toEqual([
    {
      secondary_candidate_id: SECONDARY_CANDIDATE_ID,
      reason: "merge validation via playwright"
    }
  ]);
  expect(capture.patchBodies).toEqual([
    {
      state: "publishable",
      reason: "approve path validation via playwright"
    }
  ]);
  expect(capture.overrideBodies).toEqual([
    {
      state: "rejected",
      reason: "override validation via playwright",
      posting_status: "archived"
    }
  ]);
  expect(capture.moduleBodies).toEqual([{ enabled: false }, { enabled: true }]);
  expect(capture.enqueueCalls).toBe(1);
  expect(capture.reapCalls).toBe(1);
  expect(postingStatus).toBe("archived");
});

test("merge form rejects selecting the same candidate as secondary", async ({ page }) => {
  const startedAt = "2026-02-10T20:02:39.338252Z";
  const candidate: CandidateRecord = {
    id: PRIMARY_CANDIDATE_ID,
    state: "needs_review",
    dedupe_confidence: 0.91,
    risk_flags: ["manual_review_needed"],
    extracted_fields: { title: "E2E Primary Candidate" },
    discovery_ids: ["c0315d98-ef37-49a3-b7ba-1cae768c8964"],
    posting_id: POSTING_ID,
    created_at: startedAt,
    updated_at: startedAt,
  };

  await page.route(/\/api\/admin\/candidates(?:\?.*)?$/, async (route) => {
    return jsonResponse(route, [candidate]);
  });
  await page.route(/\/api\/admin\/modules(?:\?.*)?$/, async (route) => {
    return jsonResponse(route, []);
  });
  await page.route(/\/api\/admin\/jobs(?:\?.*)?$/, async (route) => {
    return jsonResponse(route, []);
  });
  await page.route(/\/api\/admin\/candidates\/[^/?]+\/merge(?:\?.*)?$/, async (route) => {
    return route.fulfill({ status: 500, body: "should not be called" });
  });

  await page.goto("/admin/cockpit");
  await expect(page.getByRole("heading", { name: "Operator Cockpit" })).toBeVisible();

  const mergeForm = page.locator("article:has(h2:text-is('Selected Candidate Actions')) form").nth(1);
  await mergeForm.getByLabel("Secondary Candidate ID").fill(PRIMARY_CANDIDATE_ID);
  await mergeForm.getByLabel("Reason").fill("self merge should be blocked");
  await mergeForm.getByRole("button", { name: "Merge Candidate" }).click();

  await expect(page.getByText("secondary_candidate_id must differ from selected candidate.")).toBeVisible();
});

test("patch transitions are constrained and terminal transitions require reason", async ({ page }) => {
  const startedAt = "2026-02-10T20:02:39.338252Z";
  const candidate: CandidateRecord = {
    id: PRIMARY_CANDIDATE_ID,
    state: "needs_review",
    dedupe_confidence: 0.91,
    risk_flags: ["manual_review_needed"],
    extracted_fields: { title: "E2E Primary Candidate" },
    discovery_ids: ["c0315d98-ef37-49a3-b7ba-1cae768c8964"],
    posting_id: POSTING_ID,
    created_at: startedAt,
    updated_at: startedAt
  };

  let patchCalls = 0;

  await page.route(/\/api\/admin\/candidates(?:\?.*)?$/, async (route) => jsonResponse(route, [candidate]));
  await page.route(/\/api\/admin\/modules(?:\?.*)?$/, async (route) => jsonResponse(route, []));
  await page.route(/\/api\/admin\/jobs(?:\?.*)?$/, async (route) => jsonResponse(route, []));
  await page.route(/\/api\/admin\/candidates\/[^/?]+(?:\?.*)?$/, async (route) => {
    patchCalls += 1;
    const body = route.request().postDataJSON() as { state: CandidateState; reason?: string };
    candidate.state = body.state;
    return jsonResponse(route, candidate);
  });

  await page.goto("/admin/cockpit");
  await expect(page.getByRole("heading", { name: "Operator Cockpit" })).toBeVisible();
  await expect(page.getByText(`${PRIMARY_CANDIDATE_ID} (needs_review)`)).toBeVisible();

  const patchForm = page.locator("article:has(h2:text-is('Selected Candidate Actions')) form").nth(0);
  const patchStateSelect = patchForm.getByLabel("State");
  const patchStateOptions = await patchStateSelect
    .locator("option")
    .evaluateAll((nodes) => nodes.map((node) => (node as HTMLOptionElement).value));
  expect(patchStateOptions).toEqual(["processed", "publishable", "rejected", "archived", "needs_review"]);

  await patchStateSelect.selectOption("rejected");
  const patchSubmit = patchForm.getByRole("button", { name: "Apply State Patch" });
  await expect(patchSubmit).toBeDisabled();
  expect(patchCalls).toBe(0);

  await patchForm.getByLabel("Reason").fill("close candidate from UI guardrail test");
  await expect(patchSubmit).toBeEnabled();
  await patchSubmit.click();

  await expect(page.getByText(`Candidate patch action completed for ${PRIMARY_CANDIDATE_ID}.`)).toBeVisible();
  expect(patchCalls).toBe(1);
});

test("merge and override actions require reason before submit", async ({ page }) => {
  const startedAt = "2026-02-10T20:02:39.338252Z";
  const primaryCandidate: CandidateRecord = {
    id: PRIMARY_CANDIDATE_ID,
    state: "needs_review",
    dedupe_confidence: 0.91,
    risk_flags: ["manual_review_needed"],
    extracted_fields: { title: "E2E Primary Candidate" },
    discovery_ids: ["c0315d98-ef37-49a3-b7ba-1cae768c8964"],
    posting_id: POSTING_ID,
    created_at: startedAt,
    updated_at: startedAt
  };
  const secondaryCandidate: CandidateRecord = {
    id: SECONDARY_CANDIDATE_ID,
    state: "needs_review",
    dedupe_confidence: 0.72,
    risk_flags: [],
    extracted_fields: { title: "E2E Secondary Candidate" },
    discovery_ids: ["9ab15d98-ef37-49a3-b7ba-1cae768c8964"],
    posting_id: null,
    created_at: startedAt,
    updated_at: startedAt
  };

  let mergeCalls = 0;
  let overrideCalls = 0;

  await page.route(/\/api\/admin\/candidates(?:\?.*)?$/, async (route) =>
    jsonResponse(route, [primaryCandidate, secondaryCandidate])
  );
  await page.route(/\/api\/admin\/modules(?:\?.*)?$/, async (route) => jsonResponse(route, []));
  await page.route(/\/api\/admin\/jobs(?:\?.*)?$/, async (route) => jsonResponse(route, []));
  await page.route(/\/api\/admin\/candidates\/[^/?]+\/merge(?:\?.*)?$/, async (route) => {
    mergeCalls += 1;
    return jsonResponse(route, primaryCandidate);
  });
  await page.route(/\/api\/admin\/candidates\/[^/?]+\/override(?:\?.*)?$/, async (route) => {
    overrideCalls += 1;
    return jsonResponse(route, primaryCandidate);
  });

  await page.goto("/admin/cockpit");
  await expect(page.getByRole("heading", { name: "Operator Cockpit" })).toBeVisible();

  const forms = page.locator("article:has(h2:text-is('Selected Candidate Actions')) form");
  const mergeForm = forms.nth(1);
  const overrideForm = forms.nth(2);

  await mergeForm.getByLabel("Secondary Candidate ID").fill(SECONDARY_CANDIDATE_ID);
  const mergeButton = mergeForm.getByRole("button", { name: "Merge Candidate" });
  await expect(mergeButton).toBeDisabled();
  expect(mergeCalls).toBe(0);

  await mergeForm.getByLabel("Reason").fill("required reason merge");
  await expect(mergeButton).toBeEnabled();
  await mergeButton.click();
  await expect(page.getByText(`Candidate merge action completed for ${PRIMARY_CANDIDATE_ID}.`)).toBeVisible();
  expect(mergeCalls).toBe(1);

  const overrideButton = overrideForm.getByRole("button", { name: "Apply Override" });
  await expect(overrideButton).toBeDisabled();
  expect(overrideCalls).toBe(0);

  await overrideForm.getByLabel("Reason").fill("required reason override");
  await expect(overrideButton).toBeEnabled();
  await overrideButton.click();
  await expect(page.getByText(`Candidate override action completed for ${PRIMARY_CANDIDATE_ID}.`)).toBeVisible();
  expect(overrideCalls).toBe(1);
});

test("cockpit clamps filter and maintenance limits to backend contract bounds", async ({ page }) => {
  const startedAt = "2026-02-10T20:02:39.338252Z";
  const candidate: CandidateRecord = {
    id: PRIMARY_CANDIDATE_ID,
    state: "needs_review",
    dedupe_confidence: 0.91,
    risk_flags: ["manual_review_needed"],
    extracted_fields: { title: "E2E Primary Candidate" },
    discovery_ids: ["c0315d98-ef37-49a3-b7ba-1cae768c8964"],
    posting_id: POSTING_ID,
    created_at: startedAt,
    updated_at: startedAt
  };

  const candidatesQueries: string[] = [];
  const enqueueQueries: string[] = [];

  await page.route(/\/api\/admin\/candidates(?:\?.*)?$/, async (route) => {
    const url = new URL(route.request().url());
    candidatesQueries.push(url.searchParams.toString());
    return jsonResponse(route, [candidate]);
  });
  await page.route(/\/api\/admin\/modules(?:\?.*)?$/, async (route) => jsonResponse(route, []));
  await page.route(/\/api\/admin\/jobs(?:\?.*)?$/, async (route) => jsonResponse(route, []));
  await page.route(/\/api\/admin\/jobs\/enqueue-freshness(?:\?.*)?$/, async (route) => {
    const url = new URL(route.request().url());
    enqueueQueries.push(url.searchParams.toString());
    return jsonResponse(route, { count: 0 });
  });

  await page.goto("/admin/cockpit");
  await expect(page.getByRole("heading", { name: "Operator Cockpit" })).toBeVisible();

  const candidateFilters = page.locator("article:has(h2:text-is('Candidate Queue Filters'))");
  await candidateFilters.getByLabel("Limit").fill("999");
  await candidateFilters.getByRole("button", { name: "Refresh Candidates" }).click();
  await expect(page.getByText(`${PRIMARY_CANDIDATE_ID} (needs_review)`)).toBeVisible();

  const lastCandidatesQuery = candidatesQueries.at(-1) ?? "";
  expect(lastCandidatesQuery).toContain("limit=100");

  const jobsPanel = page.locator("article:has(h2:text-is('Jobs'))");
  await jobsPanel.getByLabel("Maintenance Limit").fill("5000");
  await jobsPanel.getByRole("button", { name: "Enqueue Freshness" }).click();
  await expect(page.getByText("Enqueued 0 freshness jobs.")).toBeVisible();

  const lastEnqueueQuery = enqueueQueries.at(-1) ?? "";
  expect(lastEnqueueQuery).toContain("limit=1000");
});
