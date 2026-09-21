import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@/index.css";
import App from "@/App";
import { Toaster } from "@/components/ui/toaster";
import ConfirmHost from "@/components/ConfirmHost";

// Suppress benign "ResizeObserver loop ..." error yang dimunculkan overlay dev
// CRA saat Radix Popover/cmdk mengukur layout. Tidak berdampak fungsional &
// tidak muncul di production build.
const RESIZE_OBSERVER_MSG = "ResizeObserver loop";
window.addEventListener("error", (e) => {
  if (e.message && e.message.includes(RESIZE_OBSERVER_MSG)) {
    e.stopImmediatePropagation();
    e.preventDefault();
  }
});


// Sesi 15 — service worker: app shell + data tugas terakhir agar HP gudang bisa dibuka tanpa sinyal.
// Hanya di production build (dev server CRA memakai hot reload sendiri).
if ("serviceWorker" in navigator && process.env.NODE_ENV === "production") {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").then((reg) => reg.update()).catch(() => {});
    // Bila bundle di halaman ini sudah tidak ada di server (build baru), muat ulang sekali.
    window.addEventListener("error", (ev) => {
      const src = ev?.target?.src || "";
      if (/\/static\/js\//.test(src) && !sessionStorage.getItem("kn-reloaded")) {
        sessionStorage.setItem("kn-reloaded", "1");
        caches?.keys?.().then((ks) => Promise.all(ks.map((k) => caches.delete(k)))).finally(() => window.location.reload());
      }
    }, true);
  });
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      refetchOnWindowFocus: false,
    },
  },
});

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
      <Toaster />
      {/* FASE P5 — satu instansi dialog konfirmasi untuk seluruh aplikasi, supaya
          `askConfirm()/askReason()/askText()` bisa dipanggil dari layar & hook mana pun
          tanpa `window.confirm` yang memblokir peramban. Lihat services/confirmService.js. */}
      <ConfirmHost />
    </QueryClientProvider>
  </React.StrictMode>,
);
