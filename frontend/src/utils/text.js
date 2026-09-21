// K-1 (feedback klien 2026-09) — EYD otomatis di sisi form (cermin backend/services/text_normalize.py).
const LEGAL = new Set(["PT", "CV", "UD", "PD", "TB", "TBK", "FA", "NV", "BUMN", "BUMD", "UMKM"]);
const LOWER = new Set(["dan", "atau", "of", "and", "di", "ke", "dari", "the", "de", "van", "der", "bin", "binti", "al"]);
const cap = (w) => w.toLowerCase().replace(/(^|[-/])([a-z])/g, (_, a, b) => a + b.toUpperCase());

export function namaOrang(raw) {
  const s = String(raw || "").trim().replace(/\s+/g, " ");
  if (!s) return "";
  return s.split(" ").map((w, i) => {
    if (/^(?:[A-Za-z]\.)+,?$/.test(w)) return w.toUpperCase();
    if (i > 0 && LOWER.has(w.toLowerCase())) return w.toLowerCase();
    return cap(w);
  }).join(" ");
}

export function namaUsaha(raw) {
  const s = String(raw || "").trim().replace(/^[.,]+|[.,]+$/g, "").replace(/\s+/g, " ");
  if (!s) return "";
  return s.split(" ").map((w, i) => {
    const core = w.replace(/[^A-Za-z]/g, "");
    const up = core.toUpperCase();
    if (LEGAL.has(up)) return up === "TBK" ? "Tbk" : w.toUpperCase();
    if (core && core === up && core.length <= 4 && i > 0) return w;
    if (i > 0 && LOWER.has(w.toLowerCase())) return w.toLowerCase();
    return cap(w);
  }).join(" ");
}

/** Format tampil nomor WA `6281234567890` → `+62 812-3456-7890`. Nilai lain dikembalikan apa adanya. */
export function formatPhone(raw) {
  const d = String(raw || "").replace(/\D/g, "");
  if (!/^62[2-9]\d{7,11}$/.test(d)) return raw || "";
  const rest = d.slice(2);
  return `+62 ${rest.slice(0, 3)}-${rest.slice(3, 7)}${rest.length > 7 ? "-" + rest.slice(7) : ""}`;
}
