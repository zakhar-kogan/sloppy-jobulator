import { expect, test } from "@playwright/test";

const API_BASE_URL = process.env.SJ_LIVE_E2E_API_URL ?? "http://127.0.0.1:8000";

const CONNECTOR_HEADERS = {
  "X-Module-Id": "local-connector",
  "X-API-Key": "local-connector-key",
};

const PROCESSOR_HEADERS = {
  "X-Module-Id": "local-processor",
  "X-API-Key": "local-processor-key",
};

const ADMIN_HEADERS = {
  Authorization: "Bearer admin-token",
};

const MODERATOR_HEADERS = {
  Authorization: "Bearer moderator-token",
};

type DiscoveryAccepted = {
  discovery_id: string;
  normalized_url: string;
  canonical_hash: string;
};

type Job = {
  id: string;
  target_id: string | null;
  status: string;
};

type Candidate = {
  id: string;
  state: string;
  discovery_ids: string[];
  posting_id: string | null;
};

type CandidateEvent = {
  id: number;
  entity_type: string;
  entity_id: string | null;
  event_type: string;
  actor_type: string;
  actor_id: string | null;
  payload: Record<string, unknown>;
  created_at: string;
};

type AdminModule = {
  id: string;
  module_id: string;
  enabled: boolean;
  updated_at: string;
};

type AdminJob = {
  id: string;
  kind: string;
  status: string;
  target_type: string;
  target_id: string | null;
  locked_by_module_id: string | null;
  lease_expires_at: string | null;
};

function uniqueSuffix(): string {
  return `${Date.now()}-${Math.floor(Math.random() * 100000)}`;
}

async function createDiscovery(
  request: import("@playwright/test").APIRequestContext,
  externalId: string,
  canonicalSlug: string,
  title: string,
): Promise<DiscoveryAccepted> {
  const discoveredAt = new Date().toISOString();
  const discoveryResp = await request.post(`${API_BASE_URL}/discoveries`, {
    headers: CONNECTOR_HEADERS,
    data: {
      origin_module_id: "local-connector",
      external_id: externalId,
      discovered_at: discoveredAt,
      url: `https://example.edu/jobs/${canonicalSlug}`,
      title_hint: title,
      text_hint: "Live E2E cockpit seed payload",
      metadata: { source: "playwright-live-e2e" },
    },
  });
  expect(discoveryResp.ok()).toBeTruthy();
  return (await discoveryResp.json()) as DiscoveryAccepted;
}

async function createDiscoveryAndProcess(
  request: import("@playwright/test").APIRequestContext,
  externalId: string,
  canonicalSlug: string,
  title: string,
  includePosting: boolean,
): Promise<{ discoveryId: string; candidateHash: string }> {
  const discovery = await createDiscovery(request, externalId, canonicalSlug, title);

  const jobsResp = await request.get(`${API_BASE_URL}/jobs`, { headers: PROCESSOR_HEADERS });
  expect(jobsResp.ok()).toBeTruthy();
  const jobs = (await jobsResp.json()) as Job[];
  const job = jobs.find((row) => row.target_id === discovery.discovery_id && row.status === "queued");
  expect(job).toBeDefined();
  const jobId = job!.id;

  const claimResp = await request.post(`${API_BASE_URL}/jobs/${jobId}/claim`, {
    headers: PROCESSOR_HEADERS,
    data: { lease_seconds: 120 },
  });
  expect(claimResp.ok()).toBeTruthy();

  const resultResp = await request.post(`${API_BASE_URL}/jobs/${jobId}/result`, {
    headers: PROCESSOR_HEADERS,
    data: {
      status: "done",
      result_json: {
        dedupe_confidence: 0.91,
        risk_flags: includePosting
          ? ["manual_review_needed"]
          : ["manual_review_needed", "manual_review_low_signal"],
        posting: includePosting
          ? {
              title,
              organization_name: "Example University",
              canonical_url: `https://example.edu/jobs/${canonicalSlug}`,
              normalized_url: discovery.normalized_url,
              canonical_hash: discovery.canonical_hash,
              country: "US",
              remote: true,
              tags: ["e2e", "cockpit"],
              areas: ["testing"],
              description_text: "Live cockpit E2E posting payload",
              source_refs: [{ kind: "discovery", id: discovery.discovery_id }],
            }
          : undefined,
      },
    },
  });
  expect(resultResp.ok()).toBeTruthy();

  return { discoveryId: discovery.discovery_id, candidateHash: discovery.canonical_hash };
}

async function listCandidates(
  request: import("@playwright/test").APIRequestContext,
  query = "limit=100",
): Promise<Candidate[]> {
  const response = await request.get(`${API_BASE_URL}/candidates?${query}`, { headers: ADMIN_HEADERS });
  if (!response.ok()) {
    throw new Error(`candidates request failed (${response.status()}): ${await response.text()}`);
  }
  return (await response.json()) as Candidate[];
}

async function findCandidateByDiscovery(
  request: import("@playwright/test").APIRequestContext,
  discoveryId: string,
): Promise<Candidate> {
  const candidates = await listCandidates(request);
  const candidate = candidates.find((row) => row.discovery_ids.includes(discoveryId));
  if (!candidate) {
    throw new Error(`candidate for discovery ${discoveryId} not found`);
  }
  return candidate;
}

async function listCandidateEvents(
  request: import("@playwright/test").APIRequestContext,
  candidateId: string,
  query = "limit=200",
): Promise<CandidateEvent[]> {
  const response = await request.get(`${API_BASE_URL}/candidates/${candidateId}/events?${query}`, {
    headers: ADMIN_HEADERS,
  });
  if (!response.ok()) {
    throw new Error(`candidate events request failed (${response.status()}): ${await response.text()}`);
  }
  return (await response.json()) as CandidateEvent[];
}

async function listAdminModules(
  request: import("@playwright/test").APIRequestContext,
  query = "limit=50",
): Promise<AdminModule[]> {
  const response = await request.get(`${API_BASE_URL}/admin/modules?${query}`, {
    headers: ADMIN_HEADERS,
  });
  if (!response.ok()) {
    throw new Error(`modules request failed (${response.status()}): ${await response.text()}`);
  }
  return (await response.json()) as AdminModule[];
}

async function getAdminModule(
  request: import("@playwright/test").APIRequestContext,
  moduleId: string,
): Promise<AdminModule> {
  const modules = await listAdminModules(request, `module_id=${encodeURIComponent(moduleId)}&limit=5`);
  const module = modules.find((row) => row.module_id === moduleId);
  if (!module) {
    throw new Error(`module ${moduleId} not found`);
  }
  return module;
}

async function listAdminJobs(
  request: import("@playwright/test").APIRequestContext,
  query = "limit=200",
): Promise<AdminJob[]> {
  const response = await request.get(`${API_BASE_URL}/admin/jobs?${query}`, {
    headers: ADMIN_HEADERS,
  });
  if (!response.ok()) {
    throw new Error(`admin jobs request failed (${response.status()}): ${await response.text()}`);
  }
  return (await response.json()) as AdminJob[];
}

test("cockpit live flow persists merge, moderation, module toggles, and posting override status", async ({
  page,
  request,
}) => {
  const suffix = uniqueSuffix();
  const primary = await createDiscoveryAndProcess(
    request,
    `live-primary-${suffix}`,
    `live-primary-${suffix}`,
    `Live Primary Candidate ${suffix}`,
    true,
  );
  const secondary = await createDiscoveryAndProcess(
    request,
    `live-secondary-${suffix}`,
    `live-secondary-${suffix}`,
    `Live Secondary Candidate ${suffix}`,
    false,
  );

  const primaryCandidate = await findCandidateByDiscovery(request, primary.discoveryId);
  const secondaryCandidate = await findCandidateByDiscovery(request, secondary.discoveryId);
  expect(primaryCandidate!.id).not.toEqual(secondaryCandidate!.id);
  const moduleBeforeToggle = await getAdminModule(request, "local-processor");
  const moduleBeforeToggleUpdatedAt = Date.parse(moduleBeforeToggle.updated_at);

  await page.goto("/admin/cockpit");
  await expect(page.getByRole("heading", { name: "Operator Cockpit" })).toBeVisible();

  const queueFilters = page.locator("article:has(h2:text-is('Candidate Queue Filters'))");
  await queueFilters.getByLabel("State").selectOption("needs_review");
  await queueFilters.getByRole("button", { name: "Refresh Candidates" }).click();

  const candidateTable = page.locator("article:has(h2:text-is('Candidate Queue'))");
  const primaryRow = candidateTable.locator("tbody tr").filter({ hasText: primaryCandidate!.id });
  await expect(primaryRow).toHaveCount(1);
  await primaryRow.getByRole("button", { name: /Select|Selected/ }).click();

  const actionForms = page.locator("article:has(h2:text-is('Selected Candidate Actions')) form");
  const patchForm = actionForms.nth(0);
  const mergeForm = actionForms.nth(1);
  const overrideForm = actionForms.nth(2);

  await mergeForm.getByLabel("Secondary Candidate ID").fill(secondaryCandidate!.id);
  await mergeForm.getByLabel("Reason").fill("live merge validation");
  await mergeForm.getByRole("button", { name: "Merge Candidate" }).click();
  await expect(page.getByText(`Candidate merge action completed for ${primaryCandidate!.id}.`)).toBeVisible();

  await patchForm.getByLabel("State").selectOption("publishable");
  await patchForm.getByLabel("Reason").fill("live patch validation");
  await patchForm.getByRole("button", { name: "Apply State Patch" }).click();
  await expect(page.getByText(`Candidate patch action completed for ${primaryCandidate!.id}.`)).toBeVisible();

  await queueFilters.getByLabel("State").selectOption("publishable");
  await queueFilters.getByRole("button", { name: "Refresh Candidates" }).click();
  await expect(candidateTable.locator("tbody tr").filter({ hasText: primaryCandidate!.id })).toHaveCount(1);

  await overrideForm.getByLabel("State").selectOption("rejected");
  await overrideForm.getByLabel("Posting Status (optional)").selectOption("archived");
  await overrideForm.getByLabel("Reason").fill("live override validation");
  await overrideForm.getByRole("button", { name: "Apply Override" }).click();
  await expect(page.getByText(`Candidate override action completed for ${primaryCandidate!.id}.`)).toBeVisible();

  const primaryEvents = await listCandidateEvents(request, primaryCandidate.id);
  const primaryPatchEvent = primaryEvents.find((event) => event.event_type === "state_changed");
  expect(primaryPatchEvent).toBeDefined();
  expect(primaryPatchEvent!.payload.from_state).toBe("needs_review");
  expect(primaryPatchEvent!.payload.to_state).toBe("publishable");
  expect(primaryPatchEvent!.payload.reason).toBe("live patch validation");

  const primaryMergeEvent = primaryEvents.find((event) => event.event_type === "merge_applied");
  expect(primaryMergeEvent).toBeDefined();
  expect(primaryMergeEvent!.payload.secondary_candidate_id).toBe(secondaryCandidate.id);
  const primaryOverrideEvent = primaryEvents.find((event) => event.event_type === "state_overridden");
  expect(primaryOverrideEvent).toBeDefined();
  expect(primaryOverrideEvent!.payload.candidate_state).toBe("rejected");
  expect(primaryOverrideEvent!.payload.posting_status).toBe("archived");

  const secondaryEvents = await listCandidateEvents(request, secondaryCandidate.id);
  const secondaryMergedAwayEvent = secondaryEvents.find((event) => event.event_type === "merged_away");
  expect(secondaryMergedAwayEvent).toBeDefined();
  expect(secondaryMergedAwayEvent!.payload.primary_candidate_id).toBe(primaryCandidate.id);

  const modulesTable = page.locator("article:has(h2:text-is('Modules Table'))");
  const processorRow = modulesTable.locator("tbody tr").filter({ hasText: "local-processor" });
  await expect(processorRow).toHaveCount(1);

  await processorRow.getByRole("button", { name: "Disable" }).click();
  await expect(page.getByText("Updated local-processor enabled=false.")).toBeVisible();
  const moduleAfterDisable = await getAdminModule(request, "local-processor");
  expect(moduleAfterDisable.enabled).toBe(false);
  expect(Date.parse(moduleAfterDisable.updated_at)).toBeGreaterThanOrEqual(moduleBeforeToggleUpdatedAt);

  await processorRow.getByRole("button", { name: "Enable" }).click();
  await expect(page.getByText("Updated local-processor enabled=true.")).toBeVisible();
  const moduleAfterEnable = await getAdminModule(request, "local-processor");
  expect(moduleAfterEnable.enabled).toBe(true);
  expect(Date.parse(moduleAfterEnable.updated_at)).toBeGreaterThanOrEqual(Date.parse(moduleAfterDisable.updated_at));

  await createDiscoveryAndProcess(
    request,
    `live-freshness-seed-${suffix}`,
    `live-freshness-seed-${suffix}`,
    `Live Freshness Seed ${suffix}`,
    true,
  );

  const queuedFreshnessJobsBefore = await listAdminJobs(request, "status=queued&kind=check_freshness&limit=200");
  const queuedFreshnessJobIdsBefore = new Set(queuedFreshnessJobsBefore.map((job) => job.id));
  const maintenanceLimitInput = page.getByLabel("Maintenance Limit");
  const maintenanceConfirmationInput = page.getByLabel("Maintenance Confirmation");
  const enqueueButton = page.getByRole("button", { name: "Enqueue Freshness" });
  const reapButton = page.getByRole("button", { name: "Reap Expired" });
  await expect(maintenanceLimitInput).toBeVisible();
  await expect(maintenanceConfirmationInput).toBeVisible();
  await maintenanceLimitInput.fill("1");
  await expect(enqueueButton).toBeDisabled();
  await expect(reapButton).toBeDisabled();
  await maintenanceConfirmationInput.fill("CONFIRM");
  await expect(enqueueButton).toBeEnabled();
  await expect(reapButton).toBeEnabled();

  await enqueueButton.click();
  const enqueueStatus = page.getByText(/Enqueued \d+ freshness jobs\./).first();
  await expect(enqueueStatus).toBeVisible();
  const enqueueMessage = await enqueueStatus.innerText();
  const enqueueCountMatch = enqueueMessage.match(/Enqueued (\d+) freshness jobs\./);
  expect(enqueueCountMatch).toBeTruthy();
  const enqueueCount = Number(enqueueCountMatch![1]);
  const queuedFreshnessJobsAfter = await listAdminJobs(request, "status=queued&kind=check_freshness&limit=200");
  const newQueuedFreshnessJobs = queuedFreshnessJobsAfter.filter((job) => !queuedFreshnessJobIdsBefore.has(job.id));
  expect(newQueuedFreshnessJobs.length).toBe(enqueueCount);

  const reaperSeed = await createDiscovery(
    request,
    `live-reap-seed-${suffix}`,
    `live-reap-seed-${suffix}`,
    `Live Reap Seed ${suffix}`,
  );
  const pendingJobsResp = await request.get(`${API_BASE_URL}/jobs`, { headers: PROCESSOR_HEADERS });
  expect(pendingJobsResp.ok()).toBeTruthy();
  const pendingJobs = (await pendingJobsResp.json()) as Job[];
  const expiringJob = pendingJobs.find(
    (job) => job.target_id === reaperSeed.discovery_id && job.status === "queued",
  );
  expect(expiringJob).toBeDefined();

  const expiringClaimResp = await request.post(`${API_BASE_URL}/jobs/${expiringJob!.id}/claim`, {
    headers: PROCESSOR_HEADERS,
    data: { lease_seconds: 1 },
  });
  expect(expiringClaimResp.ok()).toBeTruthy();

  await page.waitForTimeout(1500);
  const claimedJobsBeforeReap = await listAdminJobs(request, "status=claimed&limit=200");
  expect(claimedJobsBeforeReap.some((job) => job.id === expiringJob!.id)).toBeTruthy();

  await reapButton.click();
  await expect(page.getByText(/Requeued \d+ expired claimed jobs\./)).toBeVisible();
  const claimedJobsAfterReap = await listAdminJobs(request, "status=claimed&limit=200");
  expect(claimedJobsAfterReap.some((job) => job.id === expiringJob!.id)).toBeFalsy();
  const queuedJobsAfterReap = await listAdminJobs(request, "status=queued&limit=200");
  const requeuedExpiredJob = queuedJobsAfterReap.find((job) => job.id === expiringJob!.id);
  expect(requeuedExpiredJob).toBeDefined();
  expect(requeuedExpiredJob!.locked_by_module_id).toBeNull();
  expect(requeuedExpiredJob!.lease_expires_at).toBeNull();

  const rejectedResp = await request.get(`${API_BASE_URL}/candidates?state=rejected&limit=100`, {
    headers: ADMIN_HEADERS,
  });
  expect(rejectedResp.ok()).toBeTruthy();
  const rejected = (await rejectedResp.json()) as Candidate[];
  const persistedPrimary = rejected.find((candidate) => candidate.id === primaryCandidate!.id);
  expect(persistedPrimary).toBeDefined();
  expect(persistedPrimary!.state).toBe("rejected");
  expect(persistedPrimary!.discovery_ids).toContain(secondary.discoveryId);
  expect(persistedPrimary!.posting_id).toBeTruthy();

  const postingResp = await request.get(`${API_BASE_URL}/postings/${persistedPrimary!.posting_id}`);
  expect(postingResp.ok()).toBeTruthy();
  const posting = (await postingResp.json()) as { status: string };
  expect(posting.status).toBe("archived");

  const finalProcessorModule = await getAdminModule(request, "local-processor");
  expect(finalProcessorModule.enabled).toBe(true);
});

test("cockpit live merge conflict path surfaces backend detail", async ({ page, request }) => {
  const suffix = uniqueSuffix();
  const primary = await createDiscoveryAndProcess(
    request,
    `live-conflict-primary-${suffix}`,
    `live-conflict-primary-${suffix}`,
    `Live Conflict Primary ${suffix}`,
    true,
  );
  const secondary = await createDiscoveryAndProcess(
    request,
    `live-conflict-secondary-${suffix}`,
    `live-conflict-secondary-${suffix}`,
    `Live Conflict Secondary ${suffix}`,
    true,
  );

  const primaryCandidate = await findCandidateByDiscovery(request, primary.discoveryId);
  const secondaryCandidate = await findCandidateByDiscovery(request, secondary.discoveryId);
  expect(primaryCandidate.id).not.toEqual(secondaryCandidate.id);

  await page.goto("/admin/cockpit");
  await expect(page.getByRole("heading", { name: "Operator Cockpit" })).toBeVisible();

  const queueFilters = page.locator("article:has(h2:text-is('Candidate Queue Filters'))");
  await queueFilters.getByLabel("State").selectOption("needs_review");
  await queueFilters.getByRole("button", { name: "Refresh Candidates" }).click();

  const candidateTable = page.locator("article:has(h2:text-is('Candidate Queue'))");
  const primaryRow = candidateTable.locator("tbody tr").filter({ hasText: primaryCandidate.id });
  await expect(primaryRow).toHaveCount(1);
  await primaryRow.getByRole("button", { name: /Select|Selected/ }).click();
  await expect(page.locator("article:has(h2:text-is('Selected Candidate Actions'))")).toContainText(primaryCandidate.id);

  const mergeForm = page.locator("article:has(h2:text-is('Selected Candidate Actions')) form").nth(1);
  await mergeForm.getByLabel("Secondary Candidate ID").fill(secondaryCandidate.id);
  await mergeForm.getByLabel("Reason").fill("live merge conflict validation");
  await mergeForm.getByRole("button", { name: "Merge Candidate" }).click();

  await expect(page.getByText("cannot merge candidates that both already have postings")).toBeVisible();
  await expect(page.getByText(`Candidate merge action completed for ${primaryCandidate.id}.`)).toHaveCount(0);

  const primaryEvents = await listCandidateEvents(request, primaryCandidate.id);
  expect(primaryEvents.some((event) => event.event_type === "merge_applied")).toBeFalsy();
});

test("cockpit live applies operator guardrails for patch transitions and reasoned mutations", async ({
  page,
  request,
}) => {
  const suffix = uniqueSuffix();
  const primary = await createDiscoveryAndProcess(
    request,
    `live-guardrail-primary-${suffix}`,
    `live-guardrail-primary-${suffix}`,
    `Live Guardrail Primary ${suffix}`,
    true,
  );
  const secondary = await createDiscoveryAndProcess(
    request,
    `live-guardrail-secondary-${suffix}`,
    `live-guardrail-secondary-${suffix}`,
    `Live Guardrail Secondary ${suffix}`,
    false,
  );
  const primaryCandidate = await findCandidateByDiscovery(request, primary.discoveryId);
  const secondaryCandidate = await findCandidateByDiscovery(request, secondary.discoveryId);

  await page.goto("/admin/cockpit");
  await expect(page.getByRole("heading", { name: "Operator Cockpit" })).toBeVisible();

  const queueFilters = page.locator("article:has(h2:text-is('Candidate Queue Filters'))");
  await queueFilters.getByLabel("State").selectOption("all");
  await queueFilters.getByRole("button", { name: "Refresh Candidates" }).click();

  const candidateTable = page.locator("article:has(h2:text-is('Candidate Queue'))");
  const primaryRow = candidateTable.locator("tbody tr").filter({ hasText: primaryCandidate.id });
  await expect(primaryRow).toHaveCount(1);
  await primaryRow.getByRole("button", { name: /Select|Selected/ }).click();

  const actionForms = page.locator("article:has(h2:text-is('Selected Candidate Actions')) form");
  const patchForm = actionForms.nth(0);
  const mergeForm = actionForms.nth(1);
  const overrideForm = actionForms.nth(2);

  const patchStateOptions = await patchForm
    .getByLabel("State")
    .locator("option")
    .evaluateAll((nodes) => nodes.map((node) => (node as HTMLOptionElement).value));
  expect(patchStateOptions).not.toContain("closed");

  await mergeForm.getByLabel("Secondary Candidate ID").fill(secondaryCandidate.id);
  const mergeButton = mergeForm.getByRole("button", { name: "Merge Candidate" });
  await expect(mergeButton).toBeDisabled();
  await mergeForm.getByLabel("Reason").fill("live guardrail merge reason");
  await expect(mergeButton).toBeEnabled();

  const overrideButton = overrideForm.getByRole("button", { name: "Apply Override" });
  await expect(overrideButton).toBeDisabled();
  await overrideForm.getByLabel("Reason").fill("live guardrail override reason");
  await expect(overrideButton).toBeEnabled();
  await overrideForm.getByLabel("Reason").fill("");
  await expect(overrideButton).toBeDisabled();

  await primaryRow.getByRole("button", { name: /Select|Selected/ }).click();
  await expect(page.locator("article:has(h2:text-is('Selected Candidate Actions'))")).toContainText(primaryCandidate.id);
  await patchForm.getByLabel("State").selectOption("rejected");
  const patchButton = patchForm.getByRole("button", { name: "Apply State Patch" });
  await expect(patchButton).toBeDisabled();
  await patchForm.getByLabel("Reason").fill("live guardrail patch reason");
  await expect(patchButton).toBeEnabled();
  await patchButton.click();
  await expect
    .poll(async () => {
      const persistedCandidate = await findCandidateByDiscovery(request, primary.discoveryId);
      return persistedCandidate.state;
    })
    .toBe("rejected");
});

test("cockpit live queue pagination drives patch action against selected candidate", async ({ page, request }) => {
  const suffix = uniqueSuffix();
  await createDiscoveryAndProcess(
    request,
    `live-pagination-a-${suffix}`,
    `live-pagination-a-${suffix}`,
    `Live Pagination A ${suffix}`,
    false,
  );
  await createDiscoveryAndProcess(
    request,
    `live-pagination-b-${suffix}`,
    `live-pagination-b-${suffix}`,
    `Live Pagination B ${suffix}`,
    false,
  );
  await createDiscoveryAndProcess(
    request,
    `live-pagination-c-${suffix}`,
    `live-pagination-c-${suffix}`,
    `Live Pagination C ${suffix}`,
    false,
  );

  await page.goto("/admin/cockpit");
  await expect(page.getByRole("heading", { name: "Operator Cockpit" })).toBeVisible();

  const queueFilters = page.locator("article:has(h2:text-is('Candidate Queue Filters'))");
  await queueFilters.getByLabel("State").selectOption("needs_review");
  await queueFilters.getByLabel("Limit").fill("1");
  await queueFilters.getByLabel("Offset").fill("1");
  await queueFilters.getByRole("button", { name: "Refresh Candidates" }).click();

  const expectedPageCandidates = await listCandidates(request, "state=needs_review&limit=1&offset=1");
  expect(expectedPageCandidates.length).toBe(1);
  const selectedCandidateId = expectedPageCandidates[0].id;

  const candidateTable = page.locator("article:has(h2:text-is('Candidate Queue'))");
  const candidateRow = candidateTable.locator("tbody tr").filter({ hasText: selectedCandidateId });
  await expect(candidateRow).toHaveCount(1);

  await candidateRow.getByRole("button", { name: /Select|Selected/ }).click();
  const patchForm = page.locator("article:has(h2:text-is('Selected Candidate Actions')) form").nth(0);
  await patchForm.getByLabel("State").selectOption("publishable");
  await patchForm.getByLabel("Reason").fill("live pagination patch");
  await patchForm.getByRole("button", { name: "Apply State Patch" }).click();
  await expect(page.getByText(`Candidate patch action completed for ${selectedCandidateId}.`)).toBeVisible();

  await expect
    .poll(async () => {
      const publishable = await listCandidates(request, "state=publishable&limit=100");
      return publishable.some((candidate) => candidate.id === selectedCandidateId);
    })
    .toBeTruthy();
});

test("cockpit live backend rejects non-admin and invalid requests", async ({ request }) => {
  const suffix = uniqueSuffix();
  const seeded = await createDiscoveryAndProcess(
    request,
    `live-negative-${suffix}`,
    `live-negative-${suffix}`,
    `Live Negative Candidate ${suffix}`,
    false,
  );
  const seededCandidate = await findCandidateByDiscovery(request, seeded.discoveryId);

  const missingTokenResp = await request.get(`${API_BASE_URL}/candidates?limit=1`);
  expect(missingTokenResp.status()).toBe(401);
  const missingTokenPayload = (await missingTokenResp.json()) as { detail?: unknown };
  expect(missingTokenPayload.detail).toBe("human auth requires bearer token");

  const nonAdminResp = await request.get(`${API_BASE_URL}/admin/modules?limit=1`, {
    headers: MODERATOR_HEADERS,
  });
  expect(nonAdminResp.status()).toBe(403);
  const nonAdminPayload = (await nonAdminResp.json()) as { detail?: unknown };
  expect(typeof nonAdminPayload.detail).toBe("string");
  expect(String(nonAdminPayload.detail)).toContain("admin:write");

  const invalidPayloadResp = await request.patch(`${API_BASE_URL}/candidates/${seededCandidate.id}`, {
    headers: ADMIN_HEADERS,
    data: { state: "definitely_invalid" },
  });
  expect(invalidPayloadResp.status()).toBe(422);
  const invalidPayload = (await invalidPayloadResp.json()) as { detail?: unknown };
  expect(Array.isArray(invalidPayload.detail)).toBeTruthy();
});
