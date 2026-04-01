import { Handle, Position } from "@xyflow/react";
import { useTranslation } from "react-i18next";
import type { FlowNodeData } from "../../flow/adapters";

const accents: Record<string, string> = {
  amber: "border-l-amber-700",
  cyan: "border-l-emerald-800",
  violet: "border-l-sky-800",
  zinc: "border-l-zinc-600",
};

export function BaseNode({
  accent,
  data,
}: {
  accent: keyof typeof accents;
  data: FlowNodeData;
}) {
  const { t } = useTranslation();
  const ring = accents[accent] ?? accents.zinc;
  const ports = data.ports.length ? data.ports.join(", ") : t("common.emptyDisplay");
  return (
    <div
      className={`min-w-[158px] rounded border border-zinc-700 bg-zinc-950/90 py-2 pl-2.5 pr-2.5 text-zinc-200 border-l-2 ${ring}`}
    >
      <Handle className="!h-2 !w-2 !border-zinc-600 !bg-zinc-600" position={Position.Left} type="target" />
      <Handle className="!h-2 !w-2 !border-zinc-600 !bg-zinc-600" position={Position.Right} type="source" />
      <div className="text-[11px] font-medium leading-tight">{data.label}</div>
      <div className="font-mono text-[10px] text-zinc-500">{data.ip}</div>
      <div className="font-mono text-[10px] text-zinc-600">{ports}</div>
    </div>
  );
}
