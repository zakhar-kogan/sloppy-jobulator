import { NextResponse } from "next/server";

import { forwardAdminRequest } from "./admin-api-core";

export async function proxyAdminRequest(
  path: string,
  init: { method: "GET" | "POST" | "PUT" | "PATCH"; body?: unknown }
): Promise<NextResponse> {
  try {
    const forwarded = await forwardAdminRequest(path, init);
    return NextResponse.json(forwarded.payload, { status: forwarded.status });
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Admin API configuration is invalid.";
    return NextResponse.json({ detail }, { status: 500 });
  }
}
