import React, { useEffect, useState } from "react";
import { getPhoto } from "../lib/photos";

/**
 * Foto lokal dari manifes. `className` menentukan ukuran kotak (sama seperti SVG lama);
 * `fallback` (SVG lama) tampil bila kunci tak dikenal atau gambar gagal dimuat.
 */
export default function Photo({ photoKey, alt, className = "", fallback = null, tag = true }) {
  const [failed, setFailed] = useState(false);
  const photo = getPhoto(photoKey);
  const src = photo ? photo.src : null;
  useEffect(() => { setFailed(false); }, [src]);
  if (!photo || failed) return fallback;
  return (
    <span className={`rdg-photo-box ${className}`}>
      <img src={photo.src} alt={alt || photo.alt} loading="lazy" decoding="async" className="rdg-photo" onError={() => setFailed(true)} />
      {photo.illustrative && tag && <span className="rdg-photo-tag">Foto ilustrasi</span>}
    </span>
  );
}
