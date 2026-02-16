import { proxyPublicRequest } from "../../../lib/public-api";
import { buildPostingsListPath } from "../../../lib/public-proxy-paths";

export async function GET(request: Request): Promise<Response> {
  return proxyPublicRequest(buildPostingsListPath(request.url));
}
