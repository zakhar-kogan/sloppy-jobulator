import { proxyAdminRequest } from "../../../../lib/admin-api";

export async function GET(request: Request) {
  const query = new URL(request.url).searchParams.toString();
  const path = query ? `/admin/modules?${query}` : "/admin/modules";
  return proxyAdminRequest(path, { method: "GET" });
}
