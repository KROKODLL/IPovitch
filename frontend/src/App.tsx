import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  Panel,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type Connection,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useCallback, useEffect, useMemo, useRef, useState, type ChangeEvent } from "react";
import { useTranslation } from "react-i18next";
import {
  parseHostIpPastedText,
  parseHostIpTableUpload,
  parseNmapUpload,
  parseTabularUpload,
  validateGraphJson,
} from "./api/client";
import { ApiSessionPanel } from "./components/ApiSessionPanel";
import { GatewayNode } from "./components/nodes/GatewayNode";
import { HostNode } from "./components/nodes/HostNode";
import { SubnetNode } from "./components/nodes/SubnetNode";
import { UnknownNode } from "./components/nodes/UnknownNode";
import {
  type FlowNodeData,
  filterGraph,
  graphToEdges,
  graphToNodes,
  parseOptionalPort,
} from "./flow/adapters";
import {
  type DagreRankDir,
  type DagreSpacingPreset,
  layoutWithDagre,
  spacingValues,
} from "./flow/layout";
import { VIEW_FIT } from "./flow/viewFit";
import { setLocale } from "./i18n";
import {
  exitDocumentFullscreen,
  getFullscreenElement,
  requestElementFullscreen,
} from "./lib/fullscreenDocument";
import { applyGraphImport, type GraphImportHooks } from "./lib/applyGraphImport";
import { captureReactFlowRootToPngDataUrl } from "./lib/reactFlowSnapshot";
import { downloadTopologyPdfReport } from "./lib/topologyPdfReport";
import type { NetworkGraph, NetworkNodeType } from "./types/graph";

const EMPTY_GRAPH: NetworkGraph = { edges: [], nodes: [], schemaVersion: 1 };

const nodeTypes = {
  gateway: GatewayNode,
  host: HostNode,
  subnet: SubnetNode,
  unknown: UnknownNode,
};

function InnerApp() {
  const { t } = useTranslation();
  const { fitView } = useReactFlow();
  const flowWrapRef = useRef<HTMLElement | null>(null);
  const flowContainerRef = useRef<HTMLDivElement | null>(null);
  const prevVisibleKeyRef = useRef<string | null>(null);
  const nodesRef = useRef<Node<FlowNodeData>[]>([]);
  const graphObjRef = useRef<NetworkGraph | null>(null);
  const rankDirPrevRef = useRef<DagreRankDir>("TB");
  const spacingPrevRef = useRef<DagreSpacingPreset>("normal");
  const [graph, setGraph] = useState<NetworkGraph | null>(null);
  const [rankDir, setRankDir] = useState<DagreRankDir>("TB");
  const [spacingPreset, setSpacingPreset] = useState<DagreSpacingPreset>("normal");
  const [parseError, setParseError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [portMin, setPortMin] = useState("");
  const [portMax, setPortMax] = useState("");
  const [typeHost, setTypeHost] = useState(true);
  const [typeGateway, setTypeGateway] = useState(true);
  const [typeSubnet, setTypeSubnet] = useState(true);
  const [typeUnknown, setTypeUnknown] = useState(true);
  const [tabularSource, setTabularSource] = useState("src");
  const [tabularTarget, setTabularTarget] = useState("dst");
  const [tabularLabel, setTabularLabel] = useState("");
  const [newNodeType, setNewNodeType] = useState<NetworkNodeType>("host");
  const [newNodeLabel, setNewNodeLabel] = useState("");
  const [newNodeIp, setNewNodeIp] = useState("");
  const [hostIpPasteText, setHostIpPasteText] = useState("");
  const [isGraphFullscreen, setIsGraphFullscreen] = useState(false);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<FlowNodeData>>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const graphImportHooks = useMemo<GraphImportHooks>(
    () => ({
      setParseError,
      setGraph,
      setSelectedId,
      t,
    }),
    [t],
  );

  nodesRef.current = nodes;

  const scheduleRefitAfterResize = useCallback(() => {
    if (!graph) {
      return;
    }
    const run = () => {
      fitView({ ...VIEW_FIT });
    };
    queueMicrotask(run);
    requestAnimationFrame(() => {
      requestAnimationFrame(run);
    });
    window.setTimeout(run, 60);
    window.setTimeout(run, 200);
    window.setTimeout(run, 450);
  }, [fitView, graph]);

  useEffect(() => {
    const onFsChange = () => {
      const pane = flowWrapRef.current;
      setIsGraphFullscreen(!!pane && getFullscreenElement() === pane);
      if (!graph) {
        return;
      }
      scheduleRefitAfterResize();
    };
    document.addEventListener("fullscreenchange", onFsChange);
    document.addEventListener("webkitfullscreenchange", onFsChange);
    return () => {
      document.removeEventListener("fullscreenchange", onFsChange);
      document.removeEventListener("webkitfullscreenchange", onFsChange);
    };
  }, [graph, scheduleRefitAfterResize]);

  useEffect(() => {
    const el = flowContainerRef.current;
    if (!el || !graph || !isGraphFullscreen) {
      return;
    }
    let debounce: number | undefined;
    const ro = new ResizeObserver(() => {
      if (debounce !== undefined) {
        window.clearTimeout(debounce);
      }
      debounce = window.setTimeout(() => {
        debounce = undefined;
        fitView({ ...VIEW_FIT, duration: 200 });
      }, 120);
    });
    ro.observe(el);
    return () => {
      if (debounce !== undefined) {
        window.clearTimeout(debounce);
      }
      ro.disconnect();
    };
  }, [fitView, graph, isGraphFullscreen]);

  useEffect(() => {
    const pane = flowWrapRef.current;
    if (!graph && pane && getFullscreenElement() === pane) {
      void exitDocumentFullscreen();
    }
  }, [graph]);

  const allowedTypes = useMemo(() => {
    const s = new Set<NetworkNodeType>();
    if (typeHost) {
      s.add("host");
    }
    if (typeGateway) {
      s.add("gateway");
    }
    if (typeSubnet) {
      s.add("subnet");
    }
    if (typeUnknown) {
      s.add("unknown");
    }
    return s;
  }, [typeGateway, typeHost, typeSubnet, typeUnknown]);

  useEffect(() => {
    if (!graph) {
      prevVisibleKeyRef.current = null;
      graphObjRef.current = null;
      setNodes([]);
      setEdges([]);
      return;
    }
    const graphBecameNew = graph !== graphObjRef.current;
    if (graphBecameNew) {
      prevVisibleKeyRef.current = null;
    }
    const pmin = parseOptionalPort(portMin);
    const pmax = parseOptionalPort(portMax);
    const fg = filterGraph(graph, pmin, pmax, allowedTypes);
    const visible = new Set(fg.nodes.map((n) => n.id));
    const visibleKey = [...visible].sort().join(",");
    const visibilityChanged =
      prevVisibleKeyRef.current !== null && prevVisibleKeyRef.current !== visibleKey;
    prevVisibleKeyRef.current = visibleKey;
    const nBase = graphToNodes(graph);
    const vn = nBase.filter((n) => visible.has(n.id));
    const eBase = graphToEdges(graph).map((e) => ({
      ...e,
      hidden: !visible.has(e.source) || !visible.has(e.target),
    }));
    const ve = eBase.filter((e) => !e.hidden);
    const laid = layoutWithDagre(vn, ve, {
      rankdir: rankDir,
      ...spacingValues(spacingPreset),
    });
    const layoutPos = new Map(laid.map((n) => [n.id, n.position]));
    const prev = nodesRef.current;
    const prevPos = (id: string) => prev.find((x) => x.id === id)?.position;

    const dirChanged = rankDir !== rankDirPrevRef.current;
    const spacingChanged = spacingPreset !== spacingPrevRef.current;
    graphObjRef.current = graph;
    rankDirPrevRef.current = rankDir;
    spacingPrevRef.current = spacingPreset;
    const fullRelayout = graphBecameNew || dirChanged || spacingChanged;

    const mergedNodes = nBase.map((n) => ({
      ...n,
      hidden: !visible.has(n.id),
      position:
        fullRelayout || !prevPos(n.id)
          ? (layoutPos.get(n.id) ?? { x: 0, y: 0 })
          : prevPos(n.id)!,
    }));
    setNodes(mergedNodes);
    setEdges(eBase);
    if (fullRelayout || visibilityChanged) {
      queueMicrotask(() => {
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            fitView({ ...VIEW_FIT });
          });
        });
      });
    }
  }, [
    allowedTypes,
    fitView,
    graph,
    portMax,
    portMin,
    rankDir,
    setEdges,
    setNodes,
    spacingPreset,
  ]);

  const onFitViewClick = useCallback(() => {
    fitView({ ...VIEW_FIT });
  }, [fitView]);

  const toggleGraphFullscreen = useCallback(async () => {
    const el = flowWrapRef.current;
    if (!el || !graph) {
      return;
    }
    try {
      if (getFullscreenElement() === el) {
        await exitDocumentFullscreen();
      } else {
        await requestElementFullscreen(el);
      }
    } catch {
      void 0;
    }
  }, [graph]);

  const selectedNode = useMemo(() => {
    if (!graph || !selectedId) {
      return null;
    }
    return graph.nodes.find((x) => x.id === selectedId) ?? null;
  }, [graph, selectedId]);

  const onNmapChange = useCallback(
    async (e: ChangeEvent<HTMLInputElement>) => {
      const f = e.target.files?.[0];
      e.target.value = "";
      if (!f) {
        return;
      }
      await applyGraphImport(() => parseNmapUpload(f), graphImportHooks, "errors.parseFailed");
    },
    [graphImportHooks],
  );

  const onHostIpTablePick = useCallback(
    async (e: ChangeEvent<HTMLInputElement>) => {
      const f = e.target.files?.[0];
      e.target.value = "";
      if (!f) {
        return;
      }
      await applyGraphImport(() => parseHostIpTableUpload(f), graphImportHooks, "errors.hostIpTable");
    },
    [graphImportHooks],
  );

  const onHostIpPaste = useCallback(async () => {
    const trimmed = hostIpPasteText.trim();
    if (!trimmed) {
      return;
    }
    await applyGraphImport(
      () => parseHostIpPastedText(trimmed),
      graphImportHooks,
      "errors.hostIpTable",
    );
  }, [graphImportHooks, hostIpPasteText]);

  const onTabularPick = useCallback(
    async (e: ChangeEvent<HTMLInputElement>) => {
      const f = e.target.files?.[0];
      e.target.value = "";
      if (!f) {
        return;
      }
      const mapping: { sourceKey: string; targetKey: string; labelKey?: string } = {
        sourceKey: tabularSource,
        targetKey: tabularTarget,
      };
      if (tabularLabel.trim()) {
        mapping.labelKey = tabularLabel.trim();
      }
      await applyGraphImport(
        () => parseTabularUpload(f, mapping),
        graphImportHooks,
        "errors.parseFailed",
      );
    },
    [graphImportHooks, tabularLabel, tabularSource, tabularTarget],
  );

  const onJsonPick = useCallback(
    async (e: ChangeEvent<HTMLInputElement>) => {
      const f = e.target.files?.[0];
      e.target.value = "";
      if (!f) {
        return;
      }
      await applyGraphImport(
        async () => {
          const text = await f.text();
          const parsed: unknown = JSON.parse(text);
          return validateGraphJson(parsed);
        },
        graphImportHooks,
        "errors.graphInvalid",
      );
    },
    [graphImportHooks],
  );

  const onConnect = useCallback((c: Connection) => {
    if (!c.source || !c.target) {
      return;
    }
    setGraph((g) => {
      if (!g) {
        return g;
      }
      const dup = g.edges.some((e) => e.source === c.source && e.target === c.target);
      if (dup) {
        return g;
      }
      const id = `e-${c.source}-${c.target}-${Date.now()}`;
      return {
        ...g,
        edges: [...g.edges, { id, source: c.source, target: c.target }],
      };
    });
  }, []);

  const newBlankGraph = useCallback(() => {
    setParseError(null);
    setGraph({ ...EMPTY_GRAPH, nodes: [], edges: [] });
    setSelectedId(null);
  }, []);

  const addNode = useCallback(() => {
    const label = newNodeLabel.trim() || t("editor.defaultNodeLabel");
    const ip = newNodeIp.trim() || `node-${crypto.randomUUID().slice(0, 8)}`;
    const id = ip;
    setGraph((g) => {
      const base = g ?? EMPTY_GRAPH;
      if (base.nodes.some((n) => n.id === id)) {
        return base;
      }
      const node = {
        data: { ip, label, ports: [] as number[] },
        id,
        type: newNodeType,
      };
      return { ...base, nodes: [...base.nodes, node] };
    });
    setNewNodeLabel("");
    setNewNodeIp("");
  }, [newNodeIp, newNodeLabel, newNodeType, t]);

  const deleteSelected = useCallback(() => {
    if (!selectedId || !graph) {
      return;
    }
    setGraph({
      ...graph,
      edges: graph.edges.filter((e) => e.source !== selectedId && e.target !== selectedId),
      nodes: graph.nodes.filter((n) => n.id !== selectedId),
    });
    setSelectedId(null);
  }, [graph, selectedId]);

  const exportPng = useCallback(async () => {
    const root = flowWrapRef.current?.querySelector(".react-flow") as HTMLElement | null;
    if (!root) {
      return;
    }
    const dataUrl = await captureReactFlowRootToPngDataUrl(root);
    const a = document.createElement("a");
    a.href = dataUrl;
    a.download = t("export.filePng");
    a.click();
  }, [t]);

  const exportPdf = useCallback(async () => {
    const root = flowWrapRef.current?.querySelector(".react-flow") as HTMLElement | null;
    if (!root) {
      return;
    }
    const dataUrl = await captureReactFlowRootToPngDataUrl(root);
    await downloadTopologyPdfReport({
      dataUrl,
      fileName: t("export.filePdf"),
      titleLine: t("title"),
    });
  }, [t]);

  const exportJson = useCallback(() => {
    if (!graph) {
      return;
    }
    const blob = new Blob([JSON.stringify(graph, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = t("export.fileJson");
    a.click();
    URL.revokeObjectURL(url);
  }, [graph, t]);

  return (
    <div className="flex h-svh min-h-0 flex-col bg-zinc-950 text-zinc-200">
      <header className="flex h-9 shrink-0 items-center gap-1.5 border-b border-zinc-800 bg-zinc-950 px-2 text-[11px] text-zinc-400">
        <span className="select-none pr-2 font-medium tracking-tight text-zinc-200">{t("title")}</span>
        <details className="relative">
          <summary
            aria-label={t("a11y.menuImport")}
            className="cursor-pointer list-none rounded border border-zinc-700 bg-zinc-900 px-2 py-0.5 hover:bg-zinc-800 [&::-webkit-details-marker]:hidden"
          >
            {t("toolbar.import")}
          </summary>
          <div className="absolute left-0 z-[100] mt-0.5 flex min-w-[11rem] flex-col border border-zinc-700 bg-zinc-950 py-0.5 shadow-md">
            <label className="cursor-pointer px-2 py-1 hover:bg-zinc-900">
              <span className="text-zinc-300">{t("upload.nmap")}</span>
              <input
                accept=".xml,.gnmap,application/xml,text/xml"
                aria-label={t("a11y.uploadNmap")}
                className="hidden"
                onChange={onNmapChange}
                type="file"
              />
            </label>
            <label className="cursor-pointer px-2 py-1 hover:bg-zinc-900">
              <span className="text-zinc-300">{t("upload.hostIpTable")}</span>
              <input
                accept=".txt,.tsv,text/plain,text/tab-separated-values"
                aria-label={t("a11y.uploadHostIpTable")}
                className="hidden"
                onChange={(e) => void onHostIpTablePick(e)}
                type="file"
              />
            </label>
            <label className="cursor-pointer px-2 py-1 hover:bg-zinc-900">
              <span className="text-zinc-300">{t("upload.tabular")}</span>
              <input
                accept=".csv,.json,text/csv,application/json"
                aria-label={t("a11y.uploadTabular")}
                className="hidden"
                onChange={onTabularPick}
                type="file"
              />
            </label>
            <label className="cursor-pointer px-2 py-1 hover:bg-zinc-900">
              <span className="text-zinc-300">{t("upload.json")}</span>
              <input
                accept=".json,application/json"
                aria-label={t("a11y.uploadJson")}
                className="hidden"
                onChange={(e) => void onJsonPick(e)}
                type="file"
              />
            </label>
          </div>
        </details>
        <button
          aria-label={t("a11y.layoutFitView")}
          className="rounded border border-zinc-700 bg-zinc-900 px-2 py-0.5 hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-40"
          disabled={!graph}
          onClick={onFitViewClick}
          type="button"
        >
          {t("toolbar.fit")}
        </button>
        <button
          aria-label={t("a11y.graphFullscreen")}
          className="rounded border border-zinc-700 bg-zinc-900 px-2 py-0.5 hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-40"
          disabled={!graph}
          onClick={() => void toggleGraphFullscreen()}
          type="button"
        >
          {t("toolbar.fs")}
        </button>
        <details className="relative">
          <summary
            aria-label={t("a11y.menuExport")}
            className="cursor-pointer list-none rounded border border-zinc-700 bg-zinc-900 px-2 py-0.5 hover:bg-zinc-800 [&::-webkit-details-marker]:hidden"
          >
            {t("toolbar.export")}
          </summary>
          <div className="absolute left-0 z-[100] mt-0.5 flex min-w-[7rem] flex-col border border-zinc-700 bg-zinc-950 py-0.5 shadow-md">
            <button
              aria-label={t("a11y.exportPng")}
              className="px-2 py-1 text-left hover:bg-zinc-900 disabled:cursor-not-allowed disabled:opacity-40"
              disabled={!graph}
              onClick={() => void exportPng()}
              type="button"
            >
              {t("export.png")}
            </button>
            <button
              aria-label={t("a11y.exportPdf")}
              className="px-2 py-1 text-left hover:bg-zinc-900 disabled:cursor-not-allowed disabled:opacity-40"
              disabled={!graph}
              onClick={() => void exportPdf()}
              type="button"
            >
              {t("export.pdf")}
            </button>
            <button
              aria-label={t("a11y.exportJson")}
              className="px-2 py-1 text-left hover:bg-zinc-900 disabled:cursor-not-allowed disabled:opacity-40"
              disabled={!graph}
              onClick={exportJson}
              type="button"
            >
              {t("export.json")}
            </button>
          </div>
        </details>
        <div className="min-w-2 flex-1" />
        <button
          aria-label={t("a11y.langEn")}
          className="rounded px-1.5 py-0.5 text-[10px] text-zinc-500 hover:bg-zinc-900 hover:text-zinc-300"
          onClick={() => setLocale("en")}
          title={t("lang.en")}
          type="button"
        >
          EN
        </button>
        <button
          aria-label={t("a11y.langFr")}
          className="rounded px-1.5 py-0.5 text-[10px] text-zinc-500 hover:bg-zinc-900 hover:text-zinc-300"
          onClick={() => setLocale("fr")}
          title={t("lang.fr")}
          type="button"
        >
          FR
        </button>
      </header>
      {parseError ? (
        <div className="border-b border-red-950/80 bg-red-950/30 px-3 py-1.5 text-[11px] text-red-300/90">
          {parseError}
        </div>
      ) : null}
      <div className="flex min-h-0 flex-1">
        <aside className="w-[15rem] shrink-0 overflow-y-auto border-r border-zinc-800 bg-zinc-950 p-2.5 text-[11px] leading-snug text-zinc-400">
          <ApiSessionPanel />
          <section className="mb-3 space-y-1.5 border-b border-zinc-800 pb-3">
            <h2 className="text-[10px] font-semibold uppercase tracking-wide text-zinc-500">
              {t("guide.title")}
            </h2>
            <ul className="list-inside list-disc space-y-1 text-[10px] leading-relaxed text-zinc-500">
              <li>{t("guide.stepImport")}</li>
              <li>{t("guide.stepExplore")}</li>
              <li>{t("guide.stepLayout")}</li>
            </ul>
          </section>
          <section className="space-y-2">
            <h2 className="text-[10px] font-semibold uppercase tracking-wide text-zinc-500">
              {t("editor.title")}
            </h2>
            <div className="flex flex-col gap-1.5">
              <label className="block text-zinc-500">
                {t("editor.nodeType")}
                <select
                  className="mt-0.5 w-full rounded border border-zinc-700 bg-zinc-900 px-1.5 py-1 text-zinc-200"
                  onChange={(e) => setNewNodeType(e.target.value as NetworkNodeType)}
                  value={newNodeType}
                >
                  <option value="host">{t("filters.typeHost")}</option>
                  <option value="gateway">{t("filters.typeGateway")}</option>
                  <option value="subnet">{t("filters.typeSubnet")}</option>
                  <option value="unknown">{t("filters.typeUnknown")}</option>
                </select>
              </label>
              <label className="block text-zinc-500">
                {t("editor.nodeLabel")}
                <input
                  className="mt-0.5 w-full rounded border border-zinc-700 bg-zinc-900 px-1.5 py-1 text-zinc-200"
                  onChange={(e) => setNewNodeLabel(e.target.value)}
                  value={newNodeLabel}
                />
              </label>
              <label className="block text-zinc-500">
                {t("editor.nodeId")}
                <input
                  className="mt-0.5 w-full rounded border border-zinc-700 bg-zinc-900 px-1.5 py-1 font-mono text-zinc-200"
                  onChange={(e) => setNewNodeIp(e.target.value)}
                  placeholder={t("editor.nodeIdPlaceholder")}
                  value={newNodeIp}
                />
              </label>
              <div className="flex gap-1">
                <button
                  aria-label={t("a11y.addNode")}
                  className="flex-1 rounded border border-zinc-700 bg-zinc-900 py-1 hover:bg-zinc-800"
                  onClick={addNode}
                  type="button"
                >
                  {t("editor.addNode")}
                </button>
                <button
                  aria-label={t("a11y.deleteSelection")}
                  className="flex-1 rounded border border-zinc-700 bg-zinc-900 py-1 hover:bg-zinc-800 disabled:opacity-40"
                  disabled={!selectedId}
                  onClick={deleteSelected}
                  type="button"
                >
                  {t("editor.deleteSelection")}
                </button>
              </div>
              <button
                aria-label={t("a11y.newGraph")}
                className="w-full rounded border border-zinc-800 py-1 text-[10px] text-zinc-600 hover:border-zinc-700 hover:text-zinc-400"
                onClick={newBlankGraph}
                type="button"
              >
                {t("toolbar.clear")}
              </button>
            </div>
          </section>
          <section className="mt-4 space-y-2 border-t border-zinc-800 pt-3">
            <h2 className="text-[10px] font-semibold uppercase tracking-wide text-zinc-500">
              {t("layout.title")}
            </h2>
            <label className="block text-zinc-500">
              {t("layout.direction")}
              <select
                aria-label={t("a11y.layoutDirection")}
                className="mt-0.5 w-full rounded border border-zinc-700 bg-zinc-900 px-1.5 py-1 text-zinc-200"
                disabled={!graph}
                onChange={(e) => setRankDir(e.target.value as DagreRankDir)}
                value={rankDir}
              >
                <option value="TB">{t("layout.tb")}</option>
                <option value="LR">{t("layout.lr")}</option>
                <option value="BT">{t("layout.bt")}</option>
                <option value="RL">{t("layout.rl")}</option>
              </select>
            </label>
            <label className="block text-zinc-500">
              {t("layout.spacing")}
              <select
                aria-label={t("a11y.layoutSpacing")}
                className="mt-0.5 w-full rounded border border-zinc-700 bg-zinc-900 px-1.5 py-1 text-zinc-200"
                disabled={!graph}
                onChange={(e) => setSpacingPreset(e.target.value as DagreSpacingPreset)}
                value={spacingPreset}
              >
                <option value="compact">{t("layout.spacingCompact")}</option>
                <option value="normal">{t("layout.spacingNormal")}</option>
                <option value="relaxed">{t("layout.spacingRelaxed")}</option>
              </select>
            </label>
          </section>
          <section className="mt-4 space-y-2 border-t border-zinc-800 pt-3">
            <h2 className="text-[10px] font-semibold uppercase tracking-wide text-zinc-500">
              {t("filters.title")}
            </h2>
            <div className="space-y-1">
              <label className="flex cursor-pointer items-center gap-2">
                <input checked={typeHost} onChange={(e) => setTypeHost(e.target.checked)} type="checkbox" />
                <span>{t("filters.typeHost")}</span>
              </label>
              <label className="flex cursor-pointer items-center gap-2">
                <input
                  checked={typeGateway}
                  onChange={(e) => setTypeGateway(e.target.checked)}
                  type="checkbox"
                />
                <span>{t("filters.typeGateway")}</span>
              </label>
              <label className="flex cursor-pointer items-center gap-2">
                <input
                  checked={typeSubnet}
                  onChange={(e) => setTypeSubnet(e.target.checked)}
                  type="checkbox"
                />
                <span>{t("filters.typeSubnet")}</span>
              </label>
              <label className="flex cursor-pointer items-center gap-2">
                <input
                  checked={typeUnknown}
                  onChange={(e) => setTypeUnknown(e.target.checked)}
                  type="checkbox"
                />
                <span>{t("filters.typeUnknown")}</span>
              </label>
            </div>
            <div className="grid grid-cols-2 gap-1.5 pt-1">
              <label className="block text-zinc-500">
                {t("filters.portMin")}
                <input
                  className="mt-0.5 w-full rounded border border-zinc-700 bg-zinc-900 px-1.5 py-0.5 font-mono"
                  inputMode="numeric"
                  onChange={(e) => setPortMin(e.target.value)}
                  value={portMin}
                />
              </label>
              <label className="block text-zinc-500">
                {t("filters.portMax")}
                <input
                  className="mt-0.5 w-full rounded border border-zinc-700 bg-zinc-900 px-1.5 py-0.5 font-mono"
                  inputMode="numeric"
                  onChange={(e) => setPortMax(e.target.value)}
                  value={portMax}
                />
              </label>
            </div>
          </section>
          <section className="mt-4 space-y-2 border-t border-zinc-800 pt-3">
            <h2 className="text-[10px] font-semibold uppercase tracking-wide text-zinc-500">
              {t("hostIpTable.sectionTitle")}
            </h2>
            <textarea
              aria-label={t("a11y.hostIpPaste")}
              className="min-h-[96px] w-full resize-y rounded border border-zinc-700 bg-zinc-900 px-1.5 py-1 font-mono text-[10px] text-zinc-300 placeholder:text-zinc-700"
              onChange={(e) => setHostIpPasteText(e.target.value)}
              placeholder={t("hostIpTable.pastePlaceholder")}
              spellCheck={false}
              value={hostIpPasteText}
            />
            <button
              aria-label={t("a11y.hostIpPasteSubmit")}
              className="w-full rounded border border-zinc-700 bg-zinc-900 py-1 hover:bg-zinc-800 disabled:opacity-40"
              disabled={!hostIpPasteText.trim()}
              onClick={() => void onHostIpPaste()}
              type="button"
            >
              {t("hostIpTable.pasteSubmit")}
            </button>
          </section>
          <section className="mt-4 space-y-2 border-t border-zinc-800 pt-3">
            <h2 className="text-[10px] font-semibold uppercase tracking-wide text-zinc-500">
              {t("tabular.title")}
            </h2>
            <label className="block text-zinc-500">
              {t("tabular.sourceKey")}
              <input
                className="mt-0.5 w-full rounded border border-zinc-700 bg-zinc-900 px-1.5 py-1 font-mono text-zinc-200"
                onChange={(e) => setTabularSource(e.target.value)}
                value={tabularSource}
              />
            </label>
            <label className="block text-zinc-500">
              {t("tabular.targetKey")}
              <input
                className="mt-0.5 w-full rounded border border-zinc-700 bg-zinc-900 px-1.5 py-1 font-mono text-zinc-200"
                onChange={(e) => setTabularTarget(e.target.value)}
                value={tabularTarget}
              />
            </label>
            <label className="block text-zinc-500">
              {t("tabular.labelKey")}
              <input
                className="mt-0.5 w-full rounded border border-zinc-700 bg-zinc-900 px-1.5 py-1 font-mono text-zinc-200"
                onChange={(e) => setTabularLabel(e.target.value)}
                value={tabularLabel}
              />
            </label>
          </section>
        </aside>
        <main
          className="graph-fs-root relative min-h-0 min-w-0 flex-1 bg-zinc-950"
          ref={flowWrapRef}
        >
          {!graph ? (
            <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center px-6">
              <div className="max-w-sm text-center">
                <p className="font-mono text-[12px] text-zinc-500">{t("graph.empty")}</p>
                <p className="mt-2 text-[10px] leading-relaxed text-zinc-600">{t("graph.emptyHint")}</p>
              </div>
            </div>
          ) : null}
          <div
            className="graph-fs-flow absolute inset-0 flex h-full min-h-0 w-full min-w-0 flex-col"
            ref={flowContainerRef}
          >
            <ReactFlow
              className="min-h-0 w-full flex-1"
              connectionLineStyle={{ stroke: "#52525b" }}
              deleteKeyCode={["Backspace", "Delete"]}
              edges={edges}
              fitViewOptions={{
                maxZoom: VIEW_FIT.maxZoom,
                minZoom: VIEW_FIT.minZoom,
                padding: VIEW_FIT.padding,
              }}
              maxZoom={2}
              minZoom={0.02}
              nodes={nodes}
              nodeTypes={nodeTypes}
              onConnect={onConnect}
              onEdgesChange={onEdgesChange}
              onNodeClick={(_, n) => setSelectedId(n.id)}
              onNodesChange={onNodesChange}
              onNodesDelete={(deleted) => {
                const ids = new Set(deleted.map((n) => n.id));
                setGraph((g) => {
                  if (!g) {
                    return g;
                  }
                  return {
                    ...g,
                    edges: g.edges.filter((e) => !ids.has(e.source) && !ids.has(e.target)),
                    nodes: g.nodes.filter((n) => !ids.has(n.id)),
                  };
                });
                if (selectedId && ids.has(selectedId)) {
                  setSelectedId(null);
                }
              }}
            >
              {graph && isGraphFullscreen ? (
                <Panel className="!m-2" position="top-right">
                  <button
                    aria-label={t("a11y.graphExitFullscreen")}
                    className="rounded border border-zinc-700 bg-zinc-900 px-2 py-1 text-[11px] hover:bg-zinc-800"
                    onClick={() => void exitDocumentFullscreen()}
                    type="button"
                  >
                    {t("layout.exitFullscreen")}
                  </button>
                </Panel>
              ) : null}
              <MiniMap
                className="!bg-zinc-900/95 !border-zinc-800"
                maskColor="rgb(24,24,27,0.72)"
                nodeStrokeWidth={2}
              />
              <Controls className="!border-zinc-800 !bg-zinc-900/95" />
              <Background color="#3f3f46" gap={22} variant={BackgroundVariant.Dots} />
            </ReactFlow>
          </div>
        </main>
        <aside className="w-[15rem] shrink-0 overflow-y-auto border-l border-zinc-800 bg-zinc-950 p-2.5 text-[11px] text-zinc-400">
          <h2 className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-zinc-500">
            {t("inspector.title")}
          </h2>
          {!selectedNode ? (
            <p className="font-mono text-[10px] text-zinc-600">{t("inspector.noSelection")}</p>
          ) : (
            <dl className="space-y-2.5">
              <div>
                <dt className="text-[10px] uppercase text-zinc-600">{t("inspector.label")}</dt>
                <dd className="text-zinc-200">{selectedNode.data.label}</dd>
              </div>
              <div>
                <dt className="text-[10px] uppercase text-zinc-600">{t("inspector.ip")}</dt>
                <dd className="break-all font-mono text-zinc-300">{selectedNode.data.ip}</dd>
              </div>
              {selectedNode.data.os ? (
                <div>
                  <dt className="text-[10px] uppercase text-zinc-600">{t("inspector.os")}</dt>
                  <dd className="text-zinc-300">{selectedNode.data.os}</dd>
                </div>
              ) : null}
              <div>
                <dt className="text-[10px] uppercase text-zinc-600">{t("inspector.ports")}</dt>
                <dd className="font-mono text-[10px] text-zinc-400">
                  {selectedNode.data.ports.length
                    ? selectedNode.data.ports.join(", ")
                    : t("common.emptyDisplay")}
                </dd>
              </div>
              {selectedNode.data.services?.length ? (
                <div>
                  <dt className="text-[10px] uppercase text-zinc-600">{t("inspector.services")}</dt>
                  <dd className="text-[10px] text-zinc-400">{selectedNode.data.services.join(", ")}</dd>
                </div>
              ) : null}
            </dl>
          )}
        </aside>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ReactFlowProvider>
      <InnerApp />
    </ReactFlowProvider>
  );
}
