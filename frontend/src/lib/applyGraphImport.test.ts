import { describe, expect, it, vi } from "vitest";
import { API_UNREACHABLE } from "../api/errors";
import { applyGraphImport } from "./applyGraphImport";

describe("applyGraphImport", () => {
  it("clears error and applies graph on success", async () => {
    const hooks = {
      setParseError: vi.fn(),
      setGraph: vi.fn(),
      setSelectedId: vi.fn(),
      t: (k: string) => k,
    };
    const graph = { edges: [], nodes: [], schemaVersion: 1 };
    await applyGraphImport(async () => graph, hooks, "errors.parseFailed");
    expect(hooks.setParseError).toHaveBeenCalledWith(null);
    expect(hooks.setGraph).toHaveBeenCalledWith(graph);
    expect(hooks.setSelectedId).toHaveBeenCalledWith(null);
  });

  it("uses api-offline translation when fetch failed", async () => {
    const hooks = {
      setParseError: vi.fn(),
      setGraph: vi.fn(),
      setSelectedId: vi.fn(),
      t: (k: string) => `T:${k}`,
    };
    await applyGraphImport(async () => {
      throw new Error(API_UNREACHABLE);
    }, hooks, "errors.parseFailed");
    expect(hooks.setParseError).toHaveBeenCalledWith("T:errors.apiOffline");
    expect(hooks.setGraph).not.toHaveBeenCalled();
  });

  it("uses keyed error translation for other failures", async () => {
    const hooks = {
      setParseError: vi.fn(),
      setGraph: vi.fn(),
      setSelectedId: vi.fn(),
      t: (k: string) => `T:${k}`,
    };
    await applyGraphImport(async () => {
      throw new Error("NMAP_XML_INVALID");
    }, hooks, "errors.hostIpTable");
    expect(hooks.setParseError).toHaveBeenCalledWith("T:errors.hostIpTable");
  });
});
