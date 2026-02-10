import { proxyAdminRequest } from "../../../../../../lib/admin-api";
import { buildCandidateOverridePath } from "../../../../../../lib/admin-proxy-paths";

type RouteContext = { params: { candidateId: string } };

export async function POST(request: Request, { params }: RouteContext) {
  const body = (await request.json()) as unknown;
  return proxyAdminRequest(buildCandidateOverridePath(params.candidateId), {
    method: "POST",
    body
  });
}
