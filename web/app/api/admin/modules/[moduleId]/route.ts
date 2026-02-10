import { proxyAdminRequest } from "../../../../../lib/admin-api";
import { buildModulePatchPath } from "../../../../../lib/admin-proxy-paths";

type RouteContext = { params: { moduleId: string } };

export async function PATCH(request: Request, { params }: RouteContext) {
  const body = (await request.json()) as unknown;
  return proxyAdminRequest(buildModulePatchPath(params.moduleId), {
    method: "PATCH",
    body
  });
}
