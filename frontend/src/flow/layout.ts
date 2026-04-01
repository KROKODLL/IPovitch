import dagre from "dagre";
import type { Edge, Node } from "@xyflow/react";

const NODE_W = 200;
const NODE_H = 56;

export type DagreRankDir = "TB" | "LR" | "BT" | "RL";

export type DagreSpacingPreset = "compact" | "normal" | "relaxed";

export type DagreLayoutOptions = {
  nodesep?: number;
  rankdir?: DagreRankDir;
  ranksep?: number;
};

const SPACING: Record<
  DagreSpacingPreset,
  { nodesep: number; ranksep: number }
> = {
  compact: { nodesep: 36, ranksep: 64 },
  normal: { nodesep: 48, ranksep: 88 },
  relaxed: { nodesep: 64, ranksep: 120 },
};

export function layoutWithDagre(
  nodes: Node[],
  edges: Edge[],
  options: DagreLayoutOptions = {},
): Node[] {
  if (nodes.length === 0) {
    return nodes;
  }
  const { rankdir = "TB", ranksep = SPACING.normal.ranksep, nodesep = SPACING.normal.nodesep } =
    options;
  const g = new dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir, ranksep, nodesep });
  for (const n of nodes) {
    g.setNode(n.id, { height: NODE_H, width: NODE_W });
  }
  for (const e of edges) {
    if (g.hasNode(e.source) && g.hasNode(e.target)) {
      g.setEdge(e.source, e.target);
    }
  }
  dagre.layout(g);
  return nodes.map((n) => {
    const pos = g.node(n.id);
    return {
      ...n,
      position: { x: pos.x - NODE_W / 2, y: pos.y - NODE_H / 2 },
    };
  });
}

export function spacingValues(preset: DagreSpacingPreset): { nodesep: number; ranksep: number } {
  return SPACING[preset];
}
