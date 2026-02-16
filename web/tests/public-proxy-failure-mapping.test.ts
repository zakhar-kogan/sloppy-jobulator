import assert from "node:assert/strict";
import test from "node:test";

import { forwardPublicRequest } from "../lib/public-api-core.ts";

type EnvSnapshot = {
  SJ_API_URL?: string;
};

function captureEnv(): EnvSnapshot {
  return {
    SJ_API_URL: process.env.SJ_API_URL
  };
}

function restoreEnv(snapshot: EnvSnapshot): void {
  if (snapshot.SJ_API_URL === undefined) {
    delete process.env.SJ_API_URL;
  } else {
    process.env.SJ_API_URL = snapshot.SJ_API_URL;
  }
}

test("public postings proxy preserves backend validation payload", async () => {
  const envBefore = captureEnv();
  const fetchBefore = globalThis.fetch;
  try {
    process.env.SJ_API_URL = "http://api.internal";

    let forwardedUrl = "";
    globalThis.fetch = (async (url: string | URL | Request) => {
      forwardedUrl = String(url);
      return new Response(JSON.stringify({ detail: "invalid status filter" }), {
        status: 422,
        headers: { "content-type": "application/json" }
      });
    }) as typeof fetch;

    const response = await forwardPublicRequest("/postings?status=not-valid", { method: "GET" });
    assert.equal(response.status, 422);
    assert.equal(forwardedUrl, "http://api.internal/postings?status=not-valid");
    assert.deepEqual(response.payload, { detail: "invalid status filter" });
  } finally {
    globalThis.fetch = fetchBefore;
    restoreEnv(envBefore);
  }
});

test("public proxy maps non-json failures into detail payload", async () => {
  const envBefore = captureEnv();
  const fetchBefore = globalThis.fetch;
  try {
    process.env.SJ_API_URL = "http://api.internal";

    globalThis.fetch = (async () =>
      new Response("upstream failed", {
        status: 503,
        headers: { "content-type": "text/plain" }
      })) as typeof fetch;

    const response = await forwardPublicRequest("/postings?limit=5", { method: "GET" });
    assert.equal(response.status, 503);
    assert.deepEqual(response.payload, { detail: "upstream failed" });
  } finally {
    globalThis.fetch = fetchBefore;
    restoreEnv(envBefore);
  }
});

test("public proxy fails fast when SJ_API_URL is missing", async () => {
  const envBefore = captureEnv();
  const fetchBefore = globalThis.fetch;
  try {
    delete process.env.SJ_API_URL;

    let fetchCalled = false;
    globalThis.fetch = (async () => {
      fetchCalled = true;
      return new Response("unexpected");
    }) as typeof fetch;

    await assert.rejects(
      async () => {
        await forwardPublicRequest("/postings", { method: "GET" });
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
