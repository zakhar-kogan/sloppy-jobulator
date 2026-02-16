import { proxyPublicRequest } from "../../../../lib/public-api";
import { buildPostingDetailPath } from "../../../../lib/public-proxy-paths";

export async function GET(
  _request: Request,
  context: { params: Promise<{ postingId: string }> }
): Promise<Response> {
  const { postingId } = await context.params;
  return proxyPublicRequest(buildPostingDetailPath(postingId));
}
