/** Buang kode penelusuran internal (FASE X, PS-0x, D-0x, MD-0x, KN_18 §…) dari teks yang tampil ke pengguna. */
export function stripInternalCodes(text) {
  if (!text) return text;
  return String(text)
    .replace(/\s*\((?:FASE|Fase)\s+[A-Z0-9][^)]*\)/g, "")
    .replace(/\s*\((?:PS|D|MD|E)-?\d+[^)]*\)/g, "")
    .replace(/\s*\(KN_18[^)]*\)/g, "")
    .replace(/(?:FASE|Fase)\s+[A-Z](?:-\d+)?\s*[:·—-]?\s*/g, "")
    .replace(/\b(?:PS|D|MD)-\d{2}(?:\/(?:PS|D|MD)-\d{2})*\s*[:·—-]?\s*/g, "")
    .replace(/KN_18\s*§?[\d.]*\s*/g, "")
    .replace(/\bkeputusan\s+(?=[.,)])/gi, "")
    .replace(/\s{2,}/g, " ")
    .replace(/\s+([.,;)])/g, "$1")
    .trim();
}
