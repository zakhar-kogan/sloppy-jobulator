import { NextResponse } from "next/server";

type AdminMethod = "GET" | "POST" | "PUT" | "PATCH";

function getAdminApiConfig(): { apiBaseUrl: string; bearerToken: string } {
  const apiBaseUrl = process.env.SJ_API_URL?.replace(/\/+$/, "");
  const bearerToken = process.env.SJ_ADMIN_BEARER;

  if (!apiBaseUrl) {
    throw new Error("Missing SJ_API_URL environment variable.");
  }

  if (!bearerToken) {
    throw new Error("Missing SJ_ADMIN_BEARER environment variable.");
  }

  return { apiBaseUrl, bearerToken };
}

async function parseBackendBody(response: Response): Promise<unknown> {
  const raw = await response.text();
  if (!raw) {
    return {};
  }

  try {
    return JSON.parse(raw);
  } catch {
    return { detail: raw };
  }
}

export async function proxyAdminRequest(
  path: string,
  init: { method: AdminMethod; body?: unknown }
): Promise<NextResponse> {
  let config: { apiBaseUrl: string; bearerToken: string };
  try {
    config = getAdminApiConfig();
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Admin API configuration is invalid.";
    return NextResponse.json({ detail }, { status: 500 });
  }

  const response = await fetch(`${config.apiBaseUrl}${path}`, {
    method: init.method,
    headers: {
      Authorization: `Bearer ${config.bearerToken}`,
      "Content-Type": "application/json"
    },
    body: init.body === undefined ? undefined : JSON.stringify(init.body),
    cache: "no-store"
  });

  const payload = await parseBackendBody(response);
  return NextResponse.json(payload, { status: response.status });
}
