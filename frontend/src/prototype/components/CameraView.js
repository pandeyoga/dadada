import React, { useId } from "react";
import { useNow } from "../services/useStore";
import { pickScene } from "./cameraScenes";

const pad = (n) => String(n).padStart(2, "0");
function clock(t) {
  const d = new Date(t + 7 * 3600000); // WIB
  return `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}`;
}

/**
 * Tampilan kamera simulasi: ilustrasi SVG lokal (rumah/jalan/gerbang/taman,
 * berbeda per `cameraId`), penanda LIVE, dan jam berjalan (WIB).
 */
export default function CameraView({ cameraId, label, live = true }) {
  const t = useNow(1000);
  const u = `cam${useId().replace(/[^a-zA-Z0-9]/g, "")}`;
  const { Scene, mirror, name } = pickScene(cameraId, label);
  return (
    <figure className="rdg-cam" data-scene={name} aria-label={`Kamera ${label}${live ? ", siaran langsung" : ""}`}>
      <svg className="rdg-cam-scene" viewBox="0 0 320 180" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
        <g transform={mirror ? "matrix(-1 0 0 1 320 0)" : undefined}>
          <Scene u={u} />
        </g>
      </svg>
      {live && <span className="rdg-cam-scan" aria-hidden="true" />}
      {live ? (
        <span className="rdg-cam-live"><span className="rdg-cam-dot" aria-hidden="true" />LIVE</span>
      ) : (
        <span className="rdg-cam-rec">REKAMAN</span>
      )}
      <figcaption className="rdg-cam-label">{label}</figcaption>
      <span className="rdg-cam-clock" aria-hidden="true">{clock(t)}</span>
    </figure>
  );
}
