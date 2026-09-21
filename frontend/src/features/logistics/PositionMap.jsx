import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Peta kecil posisi sopir (OpenStreetMap). Titik = posisi ber-GPS, garis = urutan perjalanan.
const dot = (color) => L.divIcon({ className: "", iconSize: [14, 14], iconAnchor: [7, 7],
  html: `<span style="display:block;width:14px;height:14px;border-radius:50%;background:${color};border:2px solid #fff;box-shadow:0 0 0 2px ${color}55"></span>` });

export default function PositionMap({ positions = [], height = 220 }) {
  const ref = useRef(null);
  const mapRef = useRef(null);
  const pts = positions.filter((p) => p.lat != null && p.lng != null && p.lat !== "" && p.lng !== ""
    && Number.isFinite(Number(p.lat)) && Number.isFinite(Number(p.lng)))
    .map((p) => ({ ...p, lat: Number(p.lat), lng: Number(p.lng) }));

  useEffect(() => {
    if (!ref.current || pts.length === 0) return;
    if (!mapRef.current) {
      mapRef.current = L.map(ref.current, { zoomControl: false, attributionControl: true });
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: "© OpenStreetMap" }).addTo(mapRef.current);
      L.control.zoom({ position: "bottomright" }).addTo(mapRef.current);
    }
    const map = mapRef.current;
    const layer = L.layerGroup().addTo(map);
    const latlngs = pts.map((p) => [p.lat, p.lng]);
    if (latlngs.length > 1) L.polyline(latlngs, { color: "#0058CC", weight: 3, opacity: 0.7, dashArray: "6 6" }).addTo(layer);
    pts.forEach((p, i) => {
      const last = i === pts.length - 1;
      L.marker([p.lat, p.lng], { icon: dot(last ? "#C0341D" : "#0058CC") })
        .bindPopup(`<b>${p.location || "Posisi"}</b><br/>${String(p.at || "").slice(0, 16).replace("T", " ")}${p.note ? `<br/>${p.note}` : ""}`)
        .addTo(layer);
    });
    if (latlngs.length === 1) map.setView(latlngs[0], 14); else map.fitBounds(latlngs, { padding: [24, 24] });
    setTimeout(() => map.invalidateSize(), 50);
    return () => { layer.remove(); };
  }, [JSON.stringify(pts)]); // eslint-disable-line

  useEffect(() => () => { if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; } }, []);

  if (pts.length === 0) {
    return <p className="text-[10.5px] text-[#9A9BA3]" data-testid="logistics-map-empty">Belum ada posisi ber-GPS. Sopir dapat menekan "Ambil GPS" saat mencatat posisi.</p>;
  }
  return <div ref={ref} data-testid="logistics-map" className="w-full rounded-md overflow-hidden border border-[#E1E4EA]" style={{ height }} />;
}
