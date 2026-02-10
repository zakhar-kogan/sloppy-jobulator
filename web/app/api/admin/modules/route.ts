import { proxyAdminRequest } from "../../../../lib/admin-api";
import { buildModulesListPath } from "../../../../lib/admin-proxy-paths";

export async function GET(request: Request) {
  return proxyAdminRequest(buildModulesListPath(request.url), { method: "GET" });
}
