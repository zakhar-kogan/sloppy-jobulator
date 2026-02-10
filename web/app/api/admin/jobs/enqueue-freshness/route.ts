import { proxyAdminRequest } from "../../../../../lib/admin-api";
import { buildJobsEnqueueFreshnessPath } from "../../../../../lib/admin-proxy-paths";

export async function POST(request: Request) {
  return proxyAdminRequest(buildJobsEnqueueFreshnessPath(request.url), { method: "POST" });
}
