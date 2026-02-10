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

function uniqueSuffix(): string {
  return `${Date.now()}-${Math.floor(Math.random() * 100000)}`;
}

async function createDiscoveryAndProcess(
  request: import("@playwright/test").APIRequestContext,
  externalId: string,
  canonicalSlug: string,
  title: string,
  includePosting: boolean,
): Promise<{ discoveryId: string; candidateHash: string }> {
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
  const discovery = (await discoveryResp.json()) as DiscoveryAccepted;

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

  const modulesTable = page.locator("article:has(h2:text-is('Modules Table'))");
  const processorRow = modulesTable.locator("tbody tr").filter({ hasText: "local-processor" });
  await expect(processorRow).toHaveCount(1);

  await processorRow.getByRole("button", { name: "Disable" }).click();
  await expect(page.getByText("Updated local-processor enabled=false.")).toBeVisible();

  await processorRow.getByRole("button", { name: "Enable" }).click();
  await expect(page.getByText("Updated local-processor enabled=true.")).toBeVisible();

  await page.getByRole("button", { name: "Enqueue Freshness" }).click();
  await expect(page.getByText(/Enqueued \d+ freshness jobs\./)).toBeVisible();

  await page.getByRole("button", { name: "Reap Expired" }).click();
  await expect(page.getByText(/Requeued \d+ expired claimed jobs\./)).toBeVisible();

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

  const moduleResp = await request.get(`${API_BASE_URL}/admin/modules?module_id=local-processor&limit=5`, {
    headers: ADMIN_HEADERS,
  });
  expect(moduleResp.ok()).toBeTruthy();
  const moduleRows = (await moduleResp.json()) as Array<{ module_id: string; enabled: boolean }>;
  const processor = moduleRows.find((row) => row.module_id === "local-processor");
  expect(processor).toBeDefined();
  expect(processor!.enabled).toBe(true);
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

  const mergeForm = page.locator("article:has(h2:text-is('Selected Candidate Actions')) form").nth(1);
  await mergeForm.getByLabel("Secondary Candidate ID").fill(secondaryCandidate.id);
  await mergeForm.getByLabel("Reason").fill("live merge conflict validation");
  await mergeForm.getByRole("button", { name: "Merge Candidate" }).click();

  await expect(page.getByText("cannot merge candidates that both already have postings")).toBeVisible();
  await expect(page.getByText(`Candidate merge action completed for ${primaryCandidate.id}.`)).toHaveCount(0);
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
