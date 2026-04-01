export type NetworkNodeType = "host" | "gateway" | "subnet" | "unknown";

export interface NodeDataPayload {
  label: string;
  ip: string;
  os?: string;
  ports: number[];
  services?: string[];
}

export interface NetworkNode {
  id: string;
  type: NetworkNodeType;
  data: NodeDataPayload;
}

export interface NetworkEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
}

export interface NetworkGraph {
  schemaVersion: number;
  nodes: NetworkNode[];
  edges: NetworkEdge[];
}
