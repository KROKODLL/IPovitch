import type { Node, NodeProps } from "@xyflow/react";
import type { FlowNodeData } from "../../flow/adapters";
import { BaseNode } from "./BaseNode";

export function GatewayNode({ data }: NodeProps<Node<FlowNodeData>>) {
  return <BaseNode accent="amber" data={data} />;
}
