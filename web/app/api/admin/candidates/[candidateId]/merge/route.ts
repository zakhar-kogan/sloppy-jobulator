import { proxyAdminRequest } from "../../../../../../lib/admin-api";
import { buildCandidateMergePath } from "../../../../../../lib/admin-proxy-paths";

type RouteContext = { params: { candidateId: string } };

export async function POST(request: Request, { params }: RouteContext) {
  const body = (await request.json()) as unknown;
  return proxyAdminRequest(buildCandidateMergePath(params.candidateId), {
    method: "POST",
    body
  });
}
