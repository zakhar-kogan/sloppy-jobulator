import { proxyAdminRequest } from "../../../../lib/admin-api";

export async function GET(request: Request) {
  const query = new URL(request.url).searchParams.toString();
  const path = query ? `/admin/jobs?${query}` : "/admin/jobs";
  return proxyAdminRequest(path, { method: "GET" });
}
