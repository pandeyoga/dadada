/** Gulir ke atas saat pindah layar (jsdom tidak mengimplementasikan scrollTo). */
export function scrollToTop() {
  if (typeof window === "undefined" || typeof window.scrollTo !== "function") return;
  if (/jsdom/i.test(window.navigator.userAgent)) return;
  window.scrollTo(0, 0);
}
