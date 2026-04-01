type DocumentWithLegacyFullscreen = Document & {
  mozCancelFullScreen?: () => Promise<void>;
  mozFullScreenElement?: Element | null;
  webkitExitFullscreen?: () => Promise<void>;
  webkitFullscreenElement?: Element | null;
};

type ElementWithLegacyFullscreen = HTMLElement & {
  mozRequestFullScreen?: () => Promise<void>;
  webkitRequestFullscreen?: () => Promise<void>;
};

export function getFullscreenElement(): Element | null {
  const d = document as DocumentWithLegacyFullscreen;
  return (
    document.fullscreenElement ?? d.webkitFullscreenElement ?? d.mozFullScreenElement ?? null
  );
}

export async function exitDocumentFullscreen(): Promise<void> {
  const d = document as DocumentWithLegacyFullscreen;
  if (document.exitFullscreen) {
    await document.exitFullscreen();
  } else if (d.webkitExitFullscreen) {
    await d.webkitExitFullscreen();
  } else if (d.mozCancelFullScreen) {
    await d.mozCancelFullScreen();
  }
}

export async function requestElementFullscreen(el: HTMLElement): Promise<void> {
  const e = el as ElementWithLegacyFullscreen;
  if (el.requestFullscreen) {
    await el.requestFullscreen();
  } else if (e.webkitRequestFullscreen) {
    await e.webkitRequestFullscreen();
  } else if (e.mozRequestFullScreen) {
    await e.mozRequestFullScreen();
  }
}
