type AdminMethod = "GET" | "POST" | "PUT" | "PATCH";

type AdminRequestConfig = {
  apiBaseUrl: string;
  bearerToken: string;
};

export type AdminProxyResult = {
  status: number;
  payload: unknown;
};

export function getAdminApiConfigFromEnv(env: NodeJS.ProcessEnv): AdminRequestConfig {
  const apiBaseUrl = env.SJ_API_URL?.replace(/\/+$/, "");
  const bearerToken = env.SJ_ADMIN_BEARER;

  if (!apiBaseUrl) {
    throw new Error("Missing SJ_API_URL environment variable.");
  }

  if (!bearerToken) {
    throw new Error("Missing SJ_ADMIN_BEARER environment variable.");
  }

  return { apiBaseUrl, bearerToken };
}

export async function parseBackendBody(response: Response): Promise<unknown> {
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

export async function forwardAdminRequest(
  path: string,
  init: { method: AdminMethod; body?: unknown },
  env: NodeJS.ProcessEnv = process.env,
  fetchImpl: typeof fetch = fetch
): Promise<AdminProxyResult> {
  const config = getAdminApiConfigFromEnv(env);
  const response = await fetchImpl(`${config.apiBaseUrl}${path}`, {
    method: init.method,
    headers: {
      Authorization: `Bearer ${config.bearerToken}`,
      "Content-Type": "application/json"
    },
    body: init.body === undefined ? undefined : JSON.stringify(init.body),
    cache: "no-store"
  });

  const payload = await parseBackendBody(response);
  return { status: response.status, payload };
}
