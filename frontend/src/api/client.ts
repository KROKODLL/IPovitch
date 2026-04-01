import type { NetworkGraph } from "../types/graph";
import { API_UNREACHABLE } from "./errors";
import { parseNetworkGraphJson } from "./networkGraphSchema";
import { resolveApiBaseFromEnv } from "./resolveApiBase";
import { clearAccessToken, getAccessToken, setAccessToken } from "./sessionToken";

const API_BASE = resolveApiBaseFromEnv({
  isDev: import.meta.env.DEV,
  viteApiBase: import.meta.env.VITE_API_BASE,
});

const API_V1 = `${API_BASE}/v1`;

const API_KEY = (import.meta.env.VITE_API_KEY as string | undefined)?.trim();

export type AuthStatus = {
  tokenLogin: boolean;
  requiresAuth: boolean;
};

function bearerHeaders(): HeadersInit {
  const session = getAccessToken();
  if (session) {
    return { Authorization: `Bearer ${session}` };
  }
  if (API_KEY) {
    return { Authorization: `Bearer ${API_KEY}` };
  }
  return {};
}

export async function fetchAuthStatus(): Promise<AuthStatus> {
  const res = await fetch(`${API_V1}/auth/status`, { credentials: "omit" });
  if (!res.ok) {
    throw new Error(`HTTP_${res.status}`);
  }
  return (await res.json()) as AuthStatus;
}

export async function loginWithPassword(password: string): Promise<void> {
  const res = await fetch(`${API_V1}/auth/token`, {
    body: JSON.stringify({ password }),
    credentials: "omit",
    headers: { "Content-Type": "application/json" },
    method: "POST",
  });
  if (res.status === 404) {
    throw new Error("TOKEN_LOGIN_DISABLED");
  }
  if (res.status === 429) {
    throw new Error("LOGIN_RATE_LIMITED");
  }
  if (!res.ok) {
    throw new Error("LOGIN_FAILED");
  }
  const data = (await res.json()) as { access_token: string };
  setAccessToken(data.access_token);
}

export function logoutSession(): void {
  clearAccessToken();
}

export { getAccessToken } from "./sessionToken";
export { API_UNREACHABLE, isApiUnreachable } from "./errors";

async function apiFetch(input: string, init?: RequestInit): Promise<Response> {
  const headers = new Headers(init?.headers);
  for (const [k, v] of Object.entries(bearerHeaders())) {
    if (!headers.has(k)) {
      headers.set(k, v);
    }
  }
  try {
    return await fetch(input, { ...init, headers, credentials: "omit" });
  } catch {
    throw new Error(API_UNREACHABLE);
  }
}

async function parseResponse(res: Response): Promise<NetworkGraph> {
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { code?: string; detail?: string };
    const hint = body.code ?? body.detail ?? `HTTP_${res.status}`;
    throw new Error(hint);
  }
  const json: unknown = await res.json();
  return parseNetworkGraphJson(json);
}

export async function parseNmapUpload(file: File): Promise<NetworkGraph> {
  const fd = new FormData();
  fd.append("file", file);
  const res = await apiFetch(`${API_V1}/parse/nmap`, { method: "POST", body: fd });
  return parseResponse(res);
}

export async function parseHostIpTableUpload(file: File): Promise<NetworkGraph> {
  const fd = new FormData();
  fd.append("file", file);
  const res = await apiFetch(`${API_V1}/parse/host-ip-table`, { method: "POST", body: fd });
  return parseResponse(res);
}

export async function parseHostIpPastedText(text: string): Promise<NetworkGraph> {
  const res = await apiFetch(`${API_V1}/parse/host-ip-table-paste`, {
    body: JSON.stringify({ text }),
    headers: { "Content-Type": "application/json" },
    method: "POST",
  });
  return parseResponse(res);
}

export async function parseTabularUpload(
  file: File,
  mapping: { sourceKey: string; targetKey: string; labelKey?: string },
): Promise<NetworkGraph> {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("mapping", JSON.stringify(mapping));
  const res = await apiFetch(`${API_V1}/parse/tabular`, { method: "POST", body: fd });
  return parseResponse(res);
}

export async function validateGraphJson(payload: unknown): Promise<NetworkGraph> {
  const res = await apiFetch(`${API_V1}/graph/validate`, {
    body: JSON.stringify(payload),
    headers: { "Content-Type": "application/json" },
    method: "POST",
  });
  return parseResponse(res);
}
