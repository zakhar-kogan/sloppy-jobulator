import { proxyAdminRequest } from "../../../../../lib/admin-api";
import { buildJobsReapExpiredPath } from "../../../../../lib/admin-proxy-paths";

export async function POST(request: Request) {
  return proxyAdminRequest(buildJobsReapExpiredPath(request.url), { method: "POST" });
}
