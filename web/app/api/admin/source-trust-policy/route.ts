import { type NextRequest, NextResponse } from "next/server";

import { proxySourceTrustPolicyRequest } from "../../../../lib/admin-source-trust-policy-api";

export async function GET(request: NextRequest): Promise<NextResponse> {
  const query = request.nextUrl.searchParams.toString();
  const path = query ? `/admin/source-trust-policy?${query}` : "/admin/source-trust-policy";
  return proxySourceTrustPolicyRequest(path, { method: "GET" });
}
