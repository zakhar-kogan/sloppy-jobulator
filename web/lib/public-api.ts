import { NextResponse } from "next/server";

import { forwardPublicRequest } from "./public-api-core";

export async function proxyPublicRequest(path: string): Promise<NextResponse> {
  try {
    const forwarded = await forwardPublicRequest(path, { method: "GET" });
    return NextResponse.json(forwarded.payload, { status: forwarded.status });
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Public API configuration is invalid.";
    return NextResponse.json({ detail }, { status: 500 });
  }
}
