/** Alamat dokumen yang bisa dibagikan: {origin}/?doc=SO-0007 → dibuka langsung ke detailnya. */
export function docLink(number) {
  const n = String(number || "").trim();
  return `${window.location.origin}/?doc=${encodeURIComponent(n)}`;
}
export function waShareLink(number, label = "") {
  const text = `${label ? label + " " : ""}${number}\n${docLink(number)}`;
  return `https://wa.me/?text=${encodeURIComponent(text)}`;
}
export async function copyDocLink(number) {
  const url = docLink(number);
  try { await navigator.clipboard.writeText(url); return true; } catch { return false; }
}
