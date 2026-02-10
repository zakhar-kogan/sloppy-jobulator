import { proxyAdminRequest } from "../../../../../lib/admin-api";

type RouteContext = { params: { moduleId: string } };

export async function PATCH(request: Request, { params }: RouteContext) {
  const body = (await request.json()) as unknown;
  const moduleId = encodeURIComponent(params.moduleId);
  return proxyAdminRequest(`/admin/modules/${moduleId}`, {
    method: "PATCH",
    body
  });
}
