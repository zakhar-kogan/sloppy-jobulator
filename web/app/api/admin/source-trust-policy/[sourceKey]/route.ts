import { NextResponse } from "next/server";

import { proxySourceTrustPolicyRequest } from "../../../../../lib/admin-source-trust-policy-api";

type RouteParams = {
  params: {
    sourceKey: string;
  };
};

export async function PUT(request: Request, { params }: RouteParams): Promise<NextResponse> {
  const payload = await request.json();
  const sourceKey = encodeURIComponent(params.sourceKey);
  return proxySourceTrustPolicyRequest(`/admin/source-trust-policy/${sourceKey}`, {
    method: "PUT",
    body: payload
  });
}

export async function PATCH(request: Request, { params }: RouteParams): Promise<NextResponse> {
  const payload = await request.json();
  const sourceKey = encodeURIComponent(params.sourceKey);
  return proxySourceTrustPolicyRequest(`/admin/source-trust-policy/${sourceKey}`, {
    method: "PATCH",
    body: payload
  });
}
