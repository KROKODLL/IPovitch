import { describe, expect, it } from "vitest";
import { resolveApiBaseFromEnv } from "./resolveApiBase";

describe("resolveApiBaseFromEnv", () => {
  it("uses dev default when unset", () => {
    expect(resolveApiBaseFromEnv({ isDev: true })).toBe("http://127.0.0.1:8001");
  });

  it("uses prod default when unset", () => {
    expect(resolveApiBaseFromEnv({ isDev: false })).toBe("http://127.0.0.1:8000");
  });

  it("accepts http URL and strips trailing slashes", () => {
    expect(
      resolveApiBaseFromEnv({
        isDev: true,
        viteApiBase: "http://127.0.0.1:9000///",
      }),
    ).toBe("http://127.0.0.1:9000");
  });

  it("accepts https URL", () => {
    expect(
      resolveApiBaseFromEnv({
        isDev: false,
        viteApiBase: "https://api.example.com",
      }),
    ).toBe("https://api.example.com");
  });

  it("rejects non-http schemes", () => {
    expect(() =>
      resolveApiBaseFromEnv({ isDev: true, viteApiBase: "ftp://x" }),
    ).toThrow(/http/);
  });

  it("rejects URLs with credentials", () => {
    expect(() =>
      resolveApiBaseFromEnv({ isDev: true, viteApiBase: "http://u:p@127.0.0.1:1" }),
    ).toThrow(/credentials/);
  });

  it("rejects invalid URL", () => {
    expect(() =>
      resolveApiBaseFromEnv({ isDev: true, viteApiBase: "http://a b" }),
    ).toThrow(/valid URL/);
  });
});
