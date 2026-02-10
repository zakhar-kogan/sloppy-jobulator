import { proxyAdminRequest } from "../../../../../lib/admin-api";
import { buildCandidatePatchPath } from "../../../../../lib/admin-proxy-paths";

type RouteContext = { params: { candidateId: string } };

export async function PATCH(request: Request, { params }: RouteContext) {
  const body = (await request.json()) as unknown;
  return proxyAdminRequest(buildCandidatePatchPath(params.candidateId), {
    method: "PATCH",
    body
  });
}
