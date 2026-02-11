import assert from "node:assert/strict";
import test from "node:test";

import { forwardAdminRequest } from "../lib/admin-api-core.ts";
import { buildCandidatesListPath, buildJobsListPath } from "../lib/admin-proxy-paths.ts";

type EnvSnapshot = {
  SJ_API_URL?: string;
  SJ_ADMIN_BEARER?: string;
};

function captureEnv(): EnvSnapshot {
  return {
    SJ_API_URL: process.env.SJ_API_URL,
    SJ_ADMIN_BEARER: process.env.SJ_ADMIN_BEARER
  };
}

function restoreEnv(snapshot: EnvSnapshot): void {
  if (snapshot.SJ_API_URL === undefined) {
    delete process.env.SJ_API_URL;
  } else {
    process.env.SJ_API_URL = snapshot.SJ_API_URL;
  }

  if (snapshot.SJ_ADMIN_BEARER === undefined) {
    delete process.env.SJ_ADMIN_BEARER;
  } else {
    process.env.SJ_ADMIN_BEARER = snapshot.SJ_ADMIN_BEARER;
  }
}

test("admin candidates proxy preserves backend limit-bounds validation response", async () => {
  const envBefore = captureEnv();
  const fetchBefore = globalThis.fetch;
  try {
    process.env.SJ_API_URL = "http://api.internal";
    process.env.SJ_ADMIN_BEARER = "admin-token";

    let forwardedUrl = "";
    let forwardedInit: RequestInit | undefined;
    globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
      forwardedUrl = String(url);
      forwardedInit = init;
      return new Response(
        JSON.stringify({
          detail: [
            {
              type: "less_than_equal",
              loc: ["query", "limit"],
              msg: "Input should be less than or equal to 100",
              input: "999",
              ctx: { le: 100 }
            }
          ]
        }),
        { status: 422, headers: { "content-type": "application/json" } }
      );
    }) as typeof fetch;

    const response = await forwardAdminRequest(
      buildCandidatesListPath("http://web.local/api/admin/candidates?state=needs_review&limit=999"),
      { method: "GET" }
    );

    assert.equal(response.status, 422);
    assert.equal(forwardedUrl, "http://api.internal/candidates?state=needs_review&limit=999");
    assert.equal(forwardedInit?.method, "GET");
    assert.equal(
      (forwardedInit?.headers as Record<string, string>)?.Authorization,
      "Bearer admin-token"
    );

    const payload = response.payload as { detail?: Array<{ loc?: unknown }> };
    assert.ok(Array.isArray(payload.detail));
    assert.deepEqual(payload.detail?.[0]?.loc, ["query", "limit"]);
  } finally {
    globalThis.fetch = fetchBefore;
    restoreEnv(envBefore);
  }
});

test("admin jobs proxy preserves backend 503 payload and status", async () => {
  const envBefore = captureEnv();
  const fetchBefore = globalThis.fetch;
  try {
    process.env.SJ_API_URL = "http://api.internal";
    process.env.SJ_ADMIN_BEARER = "admin-token";

    globalThis.fetch = (async () =>
      new Response(JSON.stringify({ detail: "database unavailable", code: "DB_DOWN" }), {
        status: 503,
        headers: { "content-type": "application/json" }
      })) as typeof fetch;

    const response = await forwardAdminRequest(
      buildJobsListPath("http://web.local/api/admin/jobs?status=queued&limit=50"),
      { method: "GET" }
    );
    assert.equal(response.status, 503);
    const payload = response.payload as Record<string, unknown>;
    assert.deepEqual(payload, { detail: "database unavailable", code: "DB_DOWN" });
  } finally {
    globalThis.fetch = fetchBefore;
    restoreEnv(envBefore);
  }
});

test("proxy maps non-json backend failures to stable detail shape", async () => {
  const envBefore = captureEnv();
  const fetchBefore = globalThis.fetch;
  try {
    process.env.SJ_API_URL = "http://api.internal";
    process.env.SJ_ADMIN_BEARER = "admin-token";

    globalThis.fetch = (async () =>
      new Response("upstream exploded", {
        status: 500,
        headers: { "content-type": "text/plain" }
      })) as typeof fetch;

    const response = await forwardAdminRequest("/admin/jobs?limit=5", { method: "GET" });
    assert.equal(response.status, 500);
    const payload = response.payload as { detail?: unknown };
    assert.deepEqual(payload, { detail: "upstream exploded" });
  } finally {
    globalThis.fetch = fetchBefore;
    restoreEnv(envBefore);
  }
});

test("forward proxy fails fast when required env is missing", async () => {
  const envBefore = captureEnv();
  const fetchBefore = globalThis.fetch;
  try {
    delete process.env.SJ_API_URL;
    process.env.SJ_ADMIN_BEARER = "admin-token";

    let fetchCalled = false;
    globalThis.fetch = (async () => {
      fetchCalled = true;
      return new Response("unexpected");
    }) as typeof fetch;

    await assert.rejects(
      async () => {
        await forwardAdminRequest("/admin/jobs", { method: "GET" });
      },
      (error: unknown) => {
        assert.equal(error instanceof Error, true);
        assert.equal((error as Error).message, "Missing SJ_API_URL environment variable.");
        return true;
      }
    );
    assert.equal(fetchCalled, false);
  } finally {
    globalThis.fetch = fetchBefore;
    restoreEnv(envBefore);
  }
});
