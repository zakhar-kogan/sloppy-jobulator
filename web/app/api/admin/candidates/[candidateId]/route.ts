import { proxyAdminRequest } from "../../../../../lib/admin-api";

type RouteContext = { params: { candidateId: string } };

export async function PATCH(request: Request, { params }: RouteContext) {
  const body = (await request.json()) as unknown;
  const candidateId = encodeURIComponent(params.candidateId);
  return proxyAdminRequest(`/candidates/${candidateId}`, {
    method: "PATCH",
    body
  });
}
