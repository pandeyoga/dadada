import { useEffect } from "react";

// Selama prototipe terpasang, pasang manifest PWA "Rumah Dalam Genggaman" dan warna tema
// sendiri; saat dilepas, kembalikan nilai aplikasi staf (atau hapus tag yang kita buat).
export const RDG_MANIFEST = `${process.env.PUBLIC_URL || ""}/rdg/manifest.json`;
export const RDG_THEME = "#00454D";

function swap(selector, create, attr, value) {
  let el = document.head.querySelector(selector);
  const created = !el;
  if (created) {
    el = create();
    document.head.appendChild(el);
  }
  const before = el.getAttribute(attr);
  el.setAttribute(attr, value);
  return () => {
    if (created) el.remove();
    else if (before === null) el.removeAttribute(attr);
    else el.setAttribute(attr, before);
  };
}

export function usePwaManifest(enabled) {
  useEffect(() => {
    if (!enabled || typeof document === "undefined") return undefined;
    const undoManifest = swap(
      'link[rel="manifest"]',
      () => Object.assign(document.createElement("link"), { rel: "manifest" }),
      "href",
      RDG_MANIFEST
    );
    const undoTheme = swap(
      'meta[name="theme-color"]',
      () => Object.assign(document.createElement("meta"), { name: "theme-color" }),
      "content",
      RDG_THEME
    );
    return () => {
      undoManifest();
      undoTheme();
    };
  }, [enabled]);
}
