import type { Node, NodeProps } from "@xyflow/react";
import type { FlowNodeData } from "../../flow/adapters";
import { BaseNode } from "./BaseNode";

export function HostNode({ data }: NodeProps<Node<FlowNodeData>>) {
  return <BaseNode accent="cyan" data={data} />;
}
