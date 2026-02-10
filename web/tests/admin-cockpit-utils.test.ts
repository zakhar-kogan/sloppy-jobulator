import assert from "node:assert/strict";
import test from "node:test";

import { encodeAdminQuery, parseAdminCount } from "../lib/admin-cockpit-utils.ts";

test("encodeAdminQuery omits null, undefined, and blank string values", () => {
  const query = encodeAdminQuery({
    state: "needs_review",
    empty: "   ",
    missing: undefined,
    nothing: null,
    limit: 50,
    enabled: false
  });

  assert.equal(query, "state=needs_review&limit=50&enabled=false");
});

test("encodeAdminQuery keeps zero and boolean true values", () => {
  const query = encodeAdminQuery({
    offset: 0,
    enabled: true
  });

  assert.equal(query, "offset=0&enabled=true");
});

test("parseAdminCount returns 0 for invalid payloads", () => {
  assert.equal(parseAdminCount(null), 0);
  assert.equal(parseAdminCount({}), 0);
  assert.equal(parseAdminCount({ count: "4" }), 0);
});

test("parseAdminCount returns numeric count values", () => {
  assert.equal(parseAdminCount({ count: 7 }), 7);
});
