import { proxyAdminRequest } from "../../../../lib/admin-api";
import { buildCandidatesListPath } from "../../../../lib/admin-proxy-paths";

export async function GET(request: Request) {
  return proxyAdminRequest(buildCandidatesListPath(request.url), { method: "GET" });
}
