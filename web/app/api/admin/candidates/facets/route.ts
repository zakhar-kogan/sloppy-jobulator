import { proxyAdminRequest } from "../../../../../lib/admin-api";
import { buildCandidatesFacetsPath } from "../../../../../lib/admin-proxy-paths";

export async function GET(request: Request) {
  return proxyAdminRequest(buildCandidatesFacetsPath(request.url), { method: "GET" });
}
