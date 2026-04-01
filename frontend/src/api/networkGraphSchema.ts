import { z } from "zod";

import type { NetworkGraph } from "../types/graph";

const nodeDataSchema = z.object({
  label: z.string(),
  ip: z.string(),
  os: z.string().optional(),
  ports: z.array(z.number()),
  services: z.array(z.string()).optional(),
});

const networkNodeSchema = z.object({
  id: z.string(),
  type: z.enum(["host", "gateway", "subnet", "unknown"]),
  data: nodeDataSchema,
});

const networkEdgeSchema = z.object({
  id: z.string(),
  source: z.string(),
  target: z.string(),
  label: z.string().optional(),
});

export const networkGraphSchema = z.object({
  schemaVersion: z.number(),
  nodes: z.array(networkNodeSchema),
  edges: z.array(networkEdgeSchema),
});

export function parseNetworkGraphJson(json: unknown): NetworkGraph {
  const parsed = networkGraphSchema.safeParse(json);
  if (!parsed.success) {
    throw new Error("GRAPH_RESPONSE_INVALID");
  }
  return parsed.data;
}
