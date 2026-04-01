import { isApiUnreachable } from "../api/errors";
import type { NetworkGraph } from "../types/graph";

export type GraphImportHooks = {
  setParseError: (value: string | null) => void;
  setGraph: (graph: NetworkGraph) => void;
  setSelectedId: (id: string | null) => void;
  t: (key: string) => string;
};

export async function applyGraphImport(
  load: () => Promise<NetworkGraph>,
  hooks: GraphImportHooks,
  errorI18nKey: string,
): Promise<void> {
  hooks.setParseError(null);
  try {
    const g = await load();
    hooks.setGraph(g);
    hooks.setSelectedId(null);
  } catch (e) {
    hooks.setParseError(isApiUnreachable(e) ? hooks.t("errors.apiOffline") : hooks.t(errorI18nKey));
  }
}
