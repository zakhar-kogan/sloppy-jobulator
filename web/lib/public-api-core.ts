export type PublicProxyResult = {
  status: number;
  payload: unknown;
};

type PublicRequestConfig = {
  apiBaseUrl: string;
};

export function getPublicApiConfigFromEnv(env: NodeJS.ProcessEnv): PublicRequestConfig {
  const apiBaseUrl = env.SJ_API_URL?.replace(/\/+$/, "");
  if (!apiBaseUrl) {
    throw new Error("Missing SJ_API_URL environment variable.");
  }
  return { apiBaseUrl };
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

export async function forwardPublicRequest(
  path: string,
  init: { method: "GET" },
  env: NodeJS.ProcessEnv = process.env,
  fetchImpl: typeof fetch = fetch
): Promise<PublicProxyResult> {
  const config = getPublicApiConfigFromEnv(env);
  const response = await fetchImpl(`${config.apiBaseUrl}${path}`, {
    method: init.method,
    cache: "no-store"
  });

  const payload = await parseBackendBody(response);
  return { status: response.status, payload };
}
