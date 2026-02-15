import { NextResponse } from "next/server";

import { proxyURLNormalizationOverridesRequest } from "../../../../../lib/admin-url-normalization-overrides-api";

type RouteParams = {
  params: {
    domain: string;
  };
};

export async function PUT(request: Request, { params }: RouteParams): Promise<NextResponse> {
  const payload = await request.json();
  const domain = encodeURIComponent(params.domain);
  return proxyURLNormalizationOverridesRequest(`/admin/url-normalization-overrides/${domain}`, {
    method: "PUT",
    body: payload
  });
}

export async function PATCH(request: Request, { params }: RouteParams): Promise<NextResponse> {
  const payload = await request.json();
  const domain = encodeURIComponent(params.domain);
  return proxyURLNormalizationOverridesRequest(`/admin/url-normalization-overrides/${domain}`, {
    method: "PATCH",
    body: payload
  });
}
