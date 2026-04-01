import { describe, expect, it } from "vitest";
import { parseNetworkGraphJson } from "./networkGraphSchema";

describe("parseNetworkGraphJson", () => {
  it("accepts a minimal valid graph", () => {
    const g = parseNetworkGraphJson({
      schemaVersion: 1,
      nodes: [],
      edges: [],
    });
    expect(g.schemaVersion).toBe(1);
    expect(g.nodes).toEqual([]);
    expect(g.edges).toEqual([]);
  });

  it("rejects malformed payloads", () => {
    expect(() => parseNetworkGraphJson({})).toThrow("GRAPH_RESPONSE_INVALID");
    expect(() => parseNetworkGraphJson(null)).toThrow("GRAPH_RESPONSE_INVALID");
    expect(() =>
      parseNetworkGraphJson({
        schemaVersion: 1,
        nodes: "x",
        edges: [],
      }),
    ).toThrow("GRAPH_RESPONSE_INVALID");
  });
});
