export type ResolveApiBaseInput = {
  viteApiBase?: string;
  isDev: boolean;
};

export function resolveApiBaseFromEnv(input: ResolveApiBaseInput): string {
  const raw = input.viteApiBase?.trim();
  if (!raw) {
    return input.isDev ? "http://127.0.0.1:8001" : "http://127.0.0.1:8000";
  }
  if (!/^https?:\/\//i.test(raw)) {
    throw new Error("VITE_API_BASE must start with http:// or https://");
  }
  let parsed: URL;
  try {
    parsed = new URL(raw);
  } catch {
    throw new Error("VITE_API_BASE is not a valid URL");
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    throw new Error("VITE_API_BASE must use http or https");
  }
  if (parsed.username !== "" || parsed.password !== "") {
    throw new Error("VITE_API_BASE must not include credentials");
  }
  return raw.replace(/\/+$/, "");
}
