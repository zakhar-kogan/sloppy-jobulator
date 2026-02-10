import { proxyAdminRequest } from "../../../../../lib/admin-api";

export async function POST(request: Request) {
  const query = new URL(request.url).searchParams.toString();
  const path = query ? `/admin/jobs/reap-expired?${query}` : "/admin/jobs/reap-expired";
  return proxyAdminRequest(path, { method: "POST" });
}
