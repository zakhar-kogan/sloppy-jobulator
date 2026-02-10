import assert from "node:assert/strict";
import test from "node:test";

import {
  buildCandidateMergePath,
  buildCandidateOverridePath,
  buildCandidatePatchPath,
  buildCandidatesListPath,
  buildJobsEnqueueFreshnessPath,
  buildJobsListPath,
  buildJobsReapExpiredPath,
  buildModulePatchPath,
  buildModulesListPath
} from "../lib/admin-proxy-paths.ts";

test("buildCandidatesListPath preserves query string", () => {
  const requestUrl = "https://example.local/api/admin/candidates?state=needs_review&limit=10";
  assert.equal(buildCandidatesListPath(requestUrl), "/candidates?state=needs_review&limit=10");
});

test("buildCandidatesListPath returns base path without query", () => {
  const requestUrl = "https://example.local/api/admin/candidates";
  assert.equal(buildCandidatesListPath(requestUrl), "/candidates");
});

test("candidate mutation paths encode candidate ids", () => {
  const candidateId = "candidate/with slash";
  assert.equal(buildCandidatePatchPath(candidateId), "/candidates/candidate%2Fwith%20slash");
  assert.equal(buildCandidateMergePath(candidateId), "/candidates/candidate%2Fwith%20slash/merge");
  assert.equal(buildCandidateOverridePath(candidateId), "/candidates/candidate%2Fwith%20slash/override");
});

test("module list and patch paths preserve contracts", () => {
  const listUrl = "https://example.local/api/admin/modules?kind=processor&enabled=true";
  assert.equal(buildModulesListPath(listUrl), "/admin/modules?kind=processor&enabled=true");

  const moduleId = "processor/main";
  assert.equal(buildModulePatchPath(moduleId), "/admin/modules/processor%2Fmain");
});

test("jobs paths preserve query and base route mapping", () => {
  const listUrl = "https://example.local/api/admin/jobs?status=queued&kind=extract";
  const limitUrl = "https://example.local/api/admin/jobs/reap-expired?limit=25";

  assert.equal(buildJobsListPath(listUrl), "/admin/jobs?status=queued&kind=extract");
  assert.equal(buildJobsReapExpiredPath(limitUrl), "/admin/jobs/reap-expired?limit=25");
  assert.equal(
    buildJobsEnqueueFreshnessPath("https://example.local/api/admin/jobs/enqueue-freshness"),
    "/admin/jobs/enqueue-freshness"
  );
});
