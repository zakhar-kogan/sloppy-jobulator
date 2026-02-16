import assert from "node:assert/strict";
import test from "node:test";

import { buildPostingDetailPath, buildPostingsListPath } from "../lib/public-proxy-paths.ts";

test("buildPostingsListPath preserves query string", () => {
  const requestUrl = "https://example.local/api/postings?q=biology&status=active&limit=20";
  assert.equal(buildPostingsListPath(requestUrl), "/postings?q=biology&status=active&limit=20");
});

test("buildPostingsListPath returns base path without query", () => {
  const requestUrl = "https://example.local/api/postings";
  assert.equal(buildPostingsListPath(requestUrl), "/postings");
});

test("buildPostingDetailPath encodes posting id", () => {
  const postingId = "posting/with slash";
  assert.equal(buildPostingDetailPath(postingId), "/postings/posting%2Fwith%20slash");
});
