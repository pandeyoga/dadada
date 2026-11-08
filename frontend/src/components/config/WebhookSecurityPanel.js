import React, { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Info, Lock, RefreshCw, ShieldAlert, ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ErrorState, LoadingCards } from "@/components/patterns/StateViews";
import WebhookChannelTable, { SecurityBadge } from "@/components/config/WebhookChannelTable";
import WebhookSecretDialog, { webhookError } from "@/components/config/WebhookSecretDialog";
import WebhookClearDialog from "@/components/config/WebhookClearDialog";
import { useAuth } from "@/context/AuthContext";
import api from "@/services/apiClient";
import { WEBHOOK_SEC } from "@/constants/testIds";

function Summary({ d }) {
  const bad = (d.channels || []).filter((c) => !c.secure);
  return d.all_secure ? (
    <div data-testid={WEBHOOK_SEC.summary} data-state="secure"
      className="flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
      <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
      <p><b>Semua kanal bertanda tangan.</b> Permintaan tanpa tanda tangan yang cocok ditolak di setiap kanal di bawah.</p>
    </div>
  ) : (
    <div data-testid={WEBHOOK_SEC.summary} data-state="insecure"
      className="flex items-start gap-2 rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
      <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
      <p>
        <b>{bad.length} kanal belum aman:</b> {bad.map((c) => c.label).join(", ")}. Kanal tanpa rahasia menerima
        permintaan dari siapa pun — tidak masalah untuk mode simulasi/uji, tetapi isi rahasianya sebelum kanal dipakai sungguhan.
      </p>
    </div>
  );
}

function OpsNote({ policy }) {
  return (
    <div data-testid={WEBHOOK_SEC.opsNote} className="flex gap-2 rounded-xl border bg-card p-3 text-xs text-muted-foreground shadow-[var(--shadow-card)]">
      <Info className="mt-0.5 h-4 w-4 shrink-0" />
      <ul className="list-disc space-y-1 pl-4">
        <li><b>Rahasia yang sama harus dipasang di dashboard penyedia</b> (Meta, Google Ads, TikTok). Kalau tidak,
          lead asli ikut ditolak dan <b>tidak</b> masuk antrean &ldquo;Gagal Masuk&rdquo;.</li>
        <li>Penolakan dijawab seragam (401/403) tanpa menyebut penyebabnya; hitungan di tabel ini satu-satunya jejaknya.
          Bila angka &ldquo;ditolak&rdquo; naik padahal lead asli tidak masuk, periksa kecocokan rahasia di kedua sisi.</li>
        <li>Nilai rahasia tidak pernah ditampilkan ulang oleh sistem; yang terlihat hanya terisi atau belum.</li>
        {policy ? <li>{policy}</li> : null}
      </ul>
    </div>
  );
}

function OthersTable({ others }) {
  if (!others?.length) return null;
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold">Kanal lain</h3>
      <div data-testid={WEBHOOK_SEC.others} className="divide-y rounded-xl border bg-card shadow-[var(--shadow-card)]">
        {others.map((o) => (
          <div key={o.channel} className="flex flex-wrap items-center justify-between gap-2 p-3 text-sm">
            <div>
              <p className="font-medium">{o.label}</p>
              <p className="font-mono text-[11px] text-muted-foreground">{o.path}</p>
              <p className="text-xs text-muted-foreground">{o.method}</p>
            </div>
            {o.secure === null || o.secure === undefined
              ? <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs font-semibold">Publik</span>
              : <SecurityBadge secure={o.secure} channel={o.channel} />}
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Pusat Konfigurasi › Keamanan Webhook (H-C). Menampilkan `GET /webhooks/status` dan mengelola rahasia lewat
 * `PUT /webhooks/secrets/{kanal}`. Melihat butuh `settings:view`; mengubah butuh `settings:manage` (tombolnya
 * disembunyikan untuk peran lain). WhatsApp diatur di tab Integrasi WhatsApp.
 */
export default function WebhookSecurityPanel() {
  const { can } = useAuth();
  const canManage = can("settings", "manage");
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(null);
  const [clearing, setClearing] = useState(null);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      setData((await api.get("/webhooks/status")).data.data);
    } catch (e) {
      setError(e?.response?.status === 403
        ? "Peran Anda tidak boleh melihat status keamanan webhook."
        : webhookError(e, "Gagal memuat status keamanan webhook."));
    } finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const saved = (fresh) => { setEditing(null); setClearing(null); if (fresh) setData(fresh); else load(); };
  const openWa = () => { const n = new URLSearchParams(params); n.set("tab", "whatsapp"); setParams(n); };

  if (loading && !data) return <LoadingCards count={3} />;
  if (error && !data) return <ErrorState message={error} onRetry={load} />;

  return (
    <div data-testid={WEBHOOK_SEC.panel} className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <p className="max-w-2xl text-xs text-muted-foreground">
          Webhook publik menerima lead dari Meta, WhatsApp, Google, dan TikTok. Kanal yang rahasianya sudah diisi
          mewajibkan tanda tangan; yang belum diisi tetap menerima (simulasi) dan ditandai di sini.
        </p>
        <Button size="sm" variant="outline" data-testid={WEBHOOK_SEC.refresh} disabled={loading} onClick={load}>
          <RefreshCw className={`mr-1 h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} /> Muat ulang
        </Button>
      </div>
      {error ? <p className="text-xs text-rose-700">{error}</p> : null}
      {!canManage ? (
        <p data-testid={WEBHOOK_SEC.readonly}
          className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          <Lock className="h-3.5 w-3.5" />
          Mode hanya baca — hanya owner/admin yang dapat mengisi atau mencabut rahasia webhook.
        </p>
      ) : null}
      <Summary d={data} />
      <div className="rounded-xl border bg-card shadow-[var(--shadow-card)]">
        <WebhookChannelTable channels={data.channels || []} canManage={canManage}
          onSet={setEditing} onClear={setClearing} onOpenWa={openWa} />
      </div>
      <OpsNote policy={data.policy} />
      <OthersTable others={data.others} />
      {editing ? <WebhookSecretDialog channel={editing} onClose={() => setEditing(null)} onSaved={saved} /> : null}
      {clearing ? <WebhookClearDialog channel={clearing} onClose={() => setClearing(null)} onSaved={saved} /> : null}
    </div>
  );
}
