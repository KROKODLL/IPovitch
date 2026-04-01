const EXPORT_BG = "#09090b";

function exportImageFilter(domNode: HTMLElement): boolean {
  const { classList } = domNode;
  if (
    classList.contains("react-flow__panel") ||
    classList.contains("react-flow__controls") ||
    classList.contains("react-flow__attribution")
  ) {
    return false;
  }
  return true;
}

export const REACT_FLOW_EXPORT_IMAGE_OPTIONS = {
  backgroundColor: EXPORT_BG,
  cacheBust: true,
  filter: exportImageFilter,
  pixelRatio: 2,
} as const;

export function loadDataUrlAsImage(dataUrl: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      resolve(img);
    };
    img.onerror = () => {
      reject(new Error("export image load failed"));
    };
    img.src = dataUrl;
  });
}

export async function captureReactFlowRootToPngDataUrl(root: HTMLElement): Promise<string> {
  const { toPng } = await import("html-to-image");
  return toPng(root, REACT_FLOW_EXPORT_IMAGE_OPTIONS);
}
