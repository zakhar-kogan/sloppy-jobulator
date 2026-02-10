import { proxyAdminRequest } from "../../../../lib/admin-api";

export async function GET(request: Request) {
  const query = new URL(request.url).searchParams.toString();
  const path = query ? `/candidates?${query}` : "/candidates";
  return proxyAdminRequest(path, { method: "GET" });
}
