import type { Edge, Node } from "@xyflow/react";
import type { NetworkGraph, NetworkNodeType } from "../types/graph";

export function parseOptionalPort(raw: string): number | undefined {
  const trimmed = raw.trim();
  if (trimmed === "") {
    return undefined;
  }
  const n = Number(trimmed);
  return Number.isFinite(n) ? n : undefined;
}

export type FlowNodeData = {
  ip: string;
  label: string;
  os?: string;
  ports: number[];
  services?: string[];
};

export function graphToNodes(graph: NetworkGraph): Node<FlowNodeData>[] {
  return graph.nodes.map((n) => ({
    data: {
      ip: n.data.ip,
      label: n.data.label,
      os: n.data.os,
      ports: n.data.ports,
      services: n.data.services,
    },
    id: n.id,
    position: { x: 0, y: 0 },
    type: n.type,
  }));
}

export function graphToEdges(graph: NetworkGraph): Edge[] {
  return graph.edges.map((e) => ({
    id: e.id,
    label: e.label,
    source: e.source,
    target: e.target,
  }));
}

export function filterGraph(
  graph: NetworkGraph,
  portMin: number | undefined,
  portMax: number | undefined,
  allowedTypes: Set<NetworkNodeType>,
): NetworkGraph {
  const nodes = graph.nodes.filter((n) => {
    if (!allowedTypes.has(n.type)) {
      return false;
    }
    if (portMin === undefined && portMax === undefined) {
      return true;
    }
    const ports = n.data.ports;
    if (ports.length === 0) {
      return false;
    }
    return ports.some((p) => {
      if (portMin !== undefined && p < portMin) {
        return false;
      }
      if (portMax !== undefined && p > portMax) {
        return false;
      }
      return true;
    });
  });
  const ids = new Set(nodes.map((x) => x.id));
  const edges = graph.edges.filter((e) => ids.has(e.source) && ids.has(e.target));
  return {
    edges,
    nodes,
    schemaVersion: graph.schemaVersion,
  };
}
