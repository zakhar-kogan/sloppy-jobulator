import { proxyAdminRequest } from "../../../../lib/admin-api";
import { buildJobsListPath } from "../../../../lib/admin-proxy-paths";

export async function GET(request: Request) {
  return proxyAdminRequest(buildJobsListPath(request.url), { method: "GET" });
}
