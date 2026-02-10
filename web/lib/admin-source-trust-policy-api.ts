import { proxyAdminRequest } from "./admin-api";

export async function proxySourceTrustPolicyRequest(
  path: string,
  init: { method: "GET" | "PUT" | "PATCH"; body?: unknown }
) {
  return proxyAdminRequest(path, init);
}
