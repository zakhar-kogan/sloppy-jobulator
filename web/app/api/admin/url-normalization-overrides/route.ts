import { type NextRequest, NextResponse } from "next/server";

import { proxyURLNormalizationOverridesRequest } from "../../../../lib/admin-url-normalization-overrides-api";

export async function GET(request: NextRequest): Promise<NextResponse> {
  const query = request.nextUrl.searchParams.toString();
  const path = query ? `/admin/url-normalization-overrides?${query}` : "/admin/url-normalization-overrides";
  return proxyURLNormalizationOverridesRequest(path, { method: "GET" });
}
