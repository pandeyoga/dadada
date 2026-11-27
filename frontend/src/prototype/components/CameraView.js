import React, { useEffect, useId, useState } from "react";
import { useNow } from "../services/useStore";
import { pickScene } from "./cameraScenes";
import { getPhoto, cctvKeyFor } from "../lib/photos";

const pad = (n) => String(n).padStart(2, "0");
function clock(t) {
  const d = new Date(t + 7 * 3600000); // WIB
  return `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}`;
}

/**
 * Tampilan kamera simulasi: foto lokal (dipilih dari label/`cameraId`; SVG
 * cadangan bila gagal dimuat), penanda LIVE, dan jam berjalan (WIB).
 */
export default function CameraView({ cameraId, label, live = true }) {
  const t = useNow(1000);
  const u = `cam${useId().replace(/[^a-zA-Z0-9]/g, "")}`;
  const { Scene, mirror, name } = pickScene(cameraId, label);
  const [failed, setFailed] = useState(false);
  const photo = getPhoto(cctvKeyFor(cameraId, label));
  const src = photo ? photo.src : null;
  useEffect(() => { setFailed(false); }, [src]);
  return (
    <figure className="rdg-cam" data-scene={name} aria-label={`Kamera ${label}${live ? ", siaran langsung" : ""}`}>
      {photo && !failed ? (
        <img className="rdg-cam-photo" src={photo.src} alt="" aria-hidden="true" loading="lazy" decoding="async" onError={() => setFailed(true)} />
      ) : (
        <svg className="rdg-cam-scene" viewBox="0 0 320 180" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
          <g transform={mirror ? "matrix(-1 0 0 1 320 0)" : undefined}>
            <Scene u={u} />
          </g>
        </svg>
      )}
      {live && <span className="rdg-cam-scan" aria-hidden="true" />}
      {live ? (
        <span className="rdg-cam-live"><span className="rdg-cam-dot" aria-hidden="true" />LIVE</span>
      ) : (
        <span className="rdg-cam-rec">REKAMAN</span>
      )}
      <span className="rdg-cam-sim">Simulasi</span>
      <figcaption className="rdg-cam-label">{label}</figcaption>
      <span className="rdg-cam-clock" aria-hidden="true">{clock(t)}</span>
    </figure>
  );
}
