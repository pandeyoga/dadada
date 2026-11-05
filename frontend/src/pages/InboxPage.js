import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  MessagesSquare, Pencil, Send, Zap, Clock, ShieldAlert, UserPlus, Search, ArrowLeft, Info, Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import StatusPill from "@/components/patterns/StatusPill";
import EmptyState from "@/components/patterns/EmptyState";
import { ErrorState } from "@/components/patterns/StateViews";
import InboxContextPanel from "@/components/omni/InboxContextPanel";
import MessageBubble from "@/components/omni/MessageBubble";
import EditConvContactDialog from "@/components/omni/EditConvContactDialog";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";
import { fromNow } from "@/utils/formatters";
import api from "@/services/apiClient";
import { INBOX, P94, P97, CONTACT_EDIT } from "@/constants/testIds";

/**
 * Percakapan WhatsApp — tata letak 3 panel setinggi layar (daftar | percakapan | konteks lead).
 *
 * Audit WA-01..07 (docs/audit/05_WHATSAPP_INBOX.md): dulu halaman memanjang mengikuti jumlah chat
 * (daftar tanpa wadah gulir), hanya 50 chat pertama terjangkau, `scrollIntoView` menggulung
 * seluruh halaman, setiap aksi membongkar layar dengan skeleton, dan tidak ada pembaruan langsung.
 * Sekarang: setiap panel punya gulir SENDIRI, daftar berpaginasi + pencarian, gulir pesan hanya
 * di kotak pesan, muat-ulang berjalan diam-diam (tanpa skeleton), polling ringan tiap 10 detik,
 * dan di layar kecil dipakai pola daftar → percakapan → info.
 */
const PAGE = 30;
const POLL_MS = 10000;
const FILTERS = [
  { v: "all", l: "Semua", tid: INBOX.filterAll },
  { v: "mine", l: "Saya", tid: INBOX.filterMine },
  { v: "unanswered", l: "Belum dibalas", tid: INBOX.filterUnanswered },
  { v: "unread", l: "Belum dibaca", tid: "inbox-filter-unread" },
];

const isDesktop = () => typeof window !== "undefined" && window.matchMedia("(min-width: 1024px)").matches;

function ConvSkeleton() {
  return (
    <div className="space-y-2 p-2" aria-busy="true">
      {[0, 1, 2, 3, 4, 5].map((i) => <div key={i} className="h-[88px] animate-pulse rounded-xl border bg-secondary/50" />)}
    </div>
  );
}

export default function InboxPage() {
  const navigate = useNavigate();
  const { can } = useAuth();
  const [editOpen, setEditOpen] = useState(false);
  const [convs, setConvs] = useState([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState(null);
  const [firstLoad, setFirstLoad] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("all");
  const [q, setQ] = useState("");
  const [dq, setDq] = useState("");
  const [activeId, setActiveId] = useState(null);
  const [thread, setThread] = useState(null);
  const [threadLoading, setThreadLoading] = useState(false);
  const [olderLoading, setOlderLoading] = useState(false);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [templates, setTemplates] = useState([]);
  const [tmplCode, setTmplCode] = useState("");
  const [waMode, setWaMode] = useState("simulation");
  const [mobileView, setMobileView] = useState("list"); // list | thread | info (hanya < lg)

  const msgBoxRef = useRef(null);
  const stickRef = useRef(true);       // user sedang di dasar kotak pesan → ikut pesan baru
  const scrollJobRef = useRef(null);   // "bottom" | {prepend: oldScrollHeight}
  const readRef = useRef(null);        // id percakapan yang sudah ditandai terbaca oleh user
  const activeRef = useRef(null);
  const listLenRef = useRef(0);
  activeRef.current = activeId;
  listLenRef.current = convs.length;

  // ---------- daftar percakapan ----------
  const fetchList = useCallback(async ({ silent = false, more = false } = {}) => {
    if (more) setLoadingMore(true);
    try {
      const skip = more ? listLenRef.current : 0;
      const limit = more ? PAGE : Math.min(200, Math.max(PAGE, listLenRef.current));
      const res = await api.get("/inbox", { params: { filter, q: dq || undefined, skip, limit } });
      const rows = res.data.data || [];
      setTotal(res.data.total ?? rows.length);
      setConvs((cur) => {
        if (!more) return rows;
        const seen = new Set(cur.map((c) => c.id));
        return [...cur, ...rows.filter((c) => !seen.has(c.id))];
      });
      setError("");
      return rows;
    } catch (e) {
      if (!silent) setError(e?.response?.data?.detail || "Gagal memuat percakapan.");
      return null;
    } finally {
      setFirstLoad(false);
      if (more) setLoadingMore(false);
    }
  }, [filter, dq]);

  const fetchStats = useCallback(async () => {
    try { setStats((await api.get("/inbox/stats")).data.data); } catch { /* hitungan hanya pelengkap */ }
  }, []);

  useEffect(() => { const t = setTimeout(() => setDq(q.trim()), 300); return () => clearTimeout(t); }, [q]);

  // Muat ulang dari awal saat filter/pencarian berubah. Skeleton hanya pada pemuatan pertama;
  // setelah itu daftar lama tetap tampil sampai data baru datang (tidak ada kedip layar).
  useEffect(() => {
    let alive = true;
    (async () => {
      const rows = await fetchList({ silent: false });
      if (!alive || !rows) return;
      // Layar lebar: pilih percakapan teratas SEBAGAI PRATINJAU tanpa menandainya terbaca (WA-07).
      if (isDesktop() && !activeRef.current && rows.length) setActiveId(rows[0].id);
    })();
    fetchStats();
    return () => { alive = false; };
  }, [fetchList, fetchStats]);

  useEffect(() => {
    api.get("/wa-templates").then((r) => setTemplates(r.data.data || [])).catch(() => {});
    api.get("/wa/config").then((r) => setWaMode(r.data.data?.effective_mode || "simulation")).catch(() => {});
  }, []);

  // ---------- percakapan terpilih ----------
  const loadThread = useCallback(async (id, { markRead = false, silent = false } = {}) => {
    if (!id) { setThread(null); return; }
    if (!silent) setThreadLoading(true);
    try {
      const res = await api.get(`/inbox/${id}`, { params: { limit: 100, mark_read: markRead } });
      if (activeRef.current !== id) return;           // user sudah pindah percakapan
      const d = res.data.data;
      setThread((cur) => {
        const same = cur && cur.conversation.id === id;
        if (!same || stickRef.current) scrollJobRef.current = "bottom";
        // Pembaruan diam-diam: pertahankan pesan lama yang sudah dimuat user ("muat sebelumnya").
        if (silent && same && cur.messages.length > d.messages.length) {
          const firstNew = d.messages[0]?.created_at;
          const older = cur.messages.filter((m) => firstNew && m.created_at < firstNew);
          return { ...d, messages: [...older, ...d.messages], has_more: cur.has_more, next_before: cur.next_before };
        }
        return d;
      });
      if (markRead) {
        readRef.current = id;
        setConvs((cur) => cur.map((c) => (c.id === id ? { ...c, unread: 0 } : c)));
        fetchStats();
      }
    } catch {
      if (!silent) toast.error("Gagal memuat pesan.");
    } finally {
      if (!silent) setThreadLoading(false);
    }
  }, [fetchStats]);

  // Pilihan eksplisit user (klik) menandai terbaca; pratinjau otomatis di layar lebar TIDAK (WA-07).
  useEffect(() => {
    stickRef.current = true;
    scrollJobRef.current = "bottom";
    setThread(null);
    if (activeId) loadThread(activeId, { markRead: readRef.current === activeId });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeId]);

  const loadOlder = async () => {
    if (!thread?.has_more || !activeId) return;
    setOlderLoading(true);
    try {
      const box = msgBoxRef.current;
      const before = box ? box.scrollHeight : 0;
      const res = await api.get(`/inbox/${activeId}`, {
        params: { limit: 100, before: thread.next_before, mark_read: false } });
      const d = res.data.data;
      scrollJobRef.current = { prepend: before };
      setThread((cur) => (cur ? {
        ...cur, messages: [...d.messages, ...cur.messages], has_more: d.has_more, next_before: d.next_before,
      } : cur));
    } catch { toast.error("Gagal memuat pesan sebelumnya."); }
    finally { setOlderLoading(false); }
  };

  // Gulir HANYA kotak pesan (bukan seluruh halaman) — WA-04.
  useLayoutEffect(() => {
    const box = msgBoxRef.current;
    const job = scrollJobRef.current;
    if (!box || !job) return;
    if (job === "bottom") box.scrollTop = box.scrollHeight;
    else if (job.prepend != null) box.scrollTop = box.scrollHeight - job.prepend;
    scrollJobRef.current = null;
  }, [thread]);

  const onMsgScroll = () => {
    const b = msgBoxRef.current;
    if (b) stickRef.current = b.scrollHeight - b.scrollTop - b.clientHeight < 80;
  };

  // ---------- pembaruan langsung (polling ringan, hanya saat tab terlihat) ----------
  useEffect(() => {
    const t = setInterval(() => {
      if (document.visibilityState !== "visible") return;
      fetchList({ silent: true });
      fetchStats();
      if (activeRef.current) loadThread(activeRef.current, { markRead: readRef.current === activeRef.current, silent: true });
    }, POLL_MS);
    return () => clearInterval(t);
  }, [fetchList, fetchStats, loadThread]);

  const refresh = () => { loadThread(activeId, { markRead: true, silent: true }); fetchList({ silent: true }); };

  const markReadNow = () => {
    if (!activeId || readRef.current === activeId) return;
    loadThread(activeId, { markRead: true, silent: true });
  };

  const pick = (id) => {
    readRef.current = id;               // klik eksplisit = user melihatnya
    setActiveId(id);
    setMobileView("thread");
    if (id === activeId) loadThread(id, { markRead: true, silent: true });
  };

  const windowOpen = thread?.conversation?.window_open;
  const canSimulate = waMode !== "live";

  const send = async (direction) => {
    if (!text.trim() || !activeId) return;
    setBusy(true);
    try {
      await api.post(`/inbox/${activeId}/messages`, { body: text, direction });
      setText("");
      stickRef.current = true;
      readRef.current = activeId;
      await loadThread(activeId, { markRead: true, silent: true });
      if (direction === "in") toast.success("Pesan masuk (simulasi) — automation rule diproses.");
      fetchList({ silent: true });
    } catch (e) { toast.error(e?.response?.data?.detail || "Gagal mengirim pesan."); }
    finally { setBusy(false); }
  };

  const sendTemplate = async () => {
    if (!tmplCode || !activeId) { toast.error("Pilih template terlebih dahulu."); return; }
    setBusy(true);
    try {
      await api.post(`/inbox/${activeId}/messages`, { body: "", direction: "out", template_code: tmplCode });
      setTmplCode("");
      toast.success("Template terkirim (simulasi).");
      stickRef.current = true;
      readRef.current = activeId;
      await loadThread(activeId, { markRead: true, silent: true });
      fetchList({ silent: true });
    } catch (e) { toast.error(e?.response?.data?.detail || "Gagal mengirim template."); }
    finally { setBusy(false); }
  };

  const countFor = useMemo(() => ({
    all: stats?.all, mine: stats?.mine, unanswered: stats?.unanswered, unread: stats?.unread,
  }), [stats]);

  const hasMore = convs.length < total;
  const paneH = "h-[calc(100dvh-12rem)] min-h-[480px]";

  return (
    <div data-testid={INBOX.page} className="space-y-3">
      <EditConvContactDialog conversation={thread?.conversation} open={editOpen} onOpenChange={setEditOpen} onDone={refresh} />
      <div className="flex flex-wrap items-center gap-2">
        <MessagesSquare className="h-5 w-5 text-primary" />
        <h1 className="page-title">Inbox WhatsApp</h1>
        <StatusPill status={waMode === "live" ? "live" : "simulation"} label={waMode === "live" ? "LIVE" : "SIMULASI"} />
        <span data-testid={P94.modeBadge} className="sr-only">{waMode}</span>
        <div className="ml-auto flex flex-wrap gap-1">
          <Button data-testid={P97.inboxCaptureLink} size="sm" variant="secondary" onClick={() => navigate("/wa-capture")}
            title="Antrean kontak WhatsApp yang belum menjadi lead">
            <UserPlus className="mr-1 h-4 w-4" /> Kontak WA → Lead
          </Button>
        </div>
      </div>

      {error && !convs.length ? <ErrorState message={error} onRetry={() => fetchList({})} /> : (
        <div className={cn("grid gap-3 lg:grid-cols-[19rem_minmax(0,1fr)_19rem]", paneH)}>
          {/* ===== Daftar percakapan (gulir sendiri) ===== */}
          <section className={cn("min-h-0 flex-col rounded-xl border bg-card shadow-[var(--shadow-card)]",
            mobileView === "list" ? "flex" : "hidden", "lg:flex")} data-testid="inbox-list-pane">
            <div className="space-y-2 border-b p-2.5">
              <div className="relative">
                <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input data-testid="inbox-search" value={q} onChange={(e) => setQ(e.target.value)}
                  placeholder="Cari nama atau nomor HP…" className="h-9 pl-8" />
              </div>
              <div className="flex flex-wrap gap-1">
                {FILTERS.map((f) => (
                  <Button key={f.v} data-testid={f.tid} size="sm" className="h-7 px-2 text-xs"
                    variant={filter === f.v ? "default" : "outline"} onClick={() => setFilter(f.v)}>
                    {f.l}{countFor[f.v] != null ? <span className="ml-1 tabular-nums opacity-80">{countFor[f.v]}</span> : null}
                  </Button>
                ))}
              </div>
            </div>
            <div className="min-h-0 flex-1 space-y-2 overflow-y-auto p-2" data-testid="inbox-list-scroll">
              {firstLoad ? <ConvSkeleton /> : !convs.length ? (
                <EmptyState icon={MessagesSquare}
                  title={dq || filter !== "all" ? "Tidak ada percakapan yang cocok" : "Belum ada percakapan"}
                  description={dq || filter !== "all"
                    ? "Ubah kata kunci atau filter."
                    : "Percakapan muncul saat ada lead masuk via WhatsApp (simulasi). Coba 'Simulasi Lead Masuk' di halaman Lead."} />
              ) : (
                <>
                  {convs.map((c) => (
                    <button key={c.id} data-testid={INBOX.convItem} onClick={() => pick(c.id)}
                      className={cn("w-full rounded-xl border bg-card p-3 text-left transition-colors",
                        activeId === c.id ? "border-primary ring-1 ring-primary/30" : "hover:bg-secondary")}>
                      <div className="flex items-center justify-between gap-2">
                        <p className="truncate font-medium">{c.contact_name || c.contact_phone}</p>
                        {c.unread ? <span className="rounded-full bg-primary px-1.5 text-[10px] font-semibold text-primary-foreground">{c.unread}</span> : null}
                      </div>
                      <p className="text-xs text-muted-foreground">{c.contact_phone}</p>
                      <div className="mt-1 flex flex-wrap items-center gap-2">
                        <span className={cn("inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] font-medium",
                          c.window_open ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700")}>
                          <Clock className="h-3 w-3" /> {c.window_open ? "Sesi aktif" : "Perlu template"}
                        </span>
                        {c.last_direction === "in" ? <span className="text-[10px] font-medium text-amber-600">Belum dibalas</span> : null}
                        <span className="ml-auto text-[11px] text-muted-foreground">
                          {c.last_message_at ? fromNow(c.last_message_at) : "Belum ada pesan"}
                        </span>
                      </div>
                    </button>
                  ))}
                  {hasMore ? (
                    <Button data-testid="inbox-load-more" variant="outline" size="sm" className="w-full"
                      disabled={loadingMore} onClick={() => fetchList({ more: true })}>
                      {loadingMore ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : null}
                      Muat lagi ({convs.length} dari {total})
                    </Button>
                  ) : (
                    <p className="py-1 text-center text-[11px] text-muted-foreground">{total} percakapan</p>
                  )}
                </>
              )}
            </div>
          </section>

          {/* ===== Percakapan (gulir sendiri di kotak pesan) ===== */}
          <section data-testid={INBOX.thread}
            className={cn("min-h-0 flex-col rounded-xl border bg-card shadow-[var(--shadow-card)]",
              mobileView === "thread" ? "flex" : "hidden", "lg:flex")}>
            {thread ? (
              <>
                <div className="flex items-center justify-between gap-2 border-b px-3 py-2.5">
                  <div className="flex min-w-0 items-center gap-2">
                    <Button size="icon" variant="ghost" className="h-8 w-8 lg:hidden" title="Kembali ke daftar"
                      onClick={() => setMobileView("list")}><ArrowLeft className="h-4 w-4" /></Button>
                    <div className="min-w-0">
                      <p className="truncate font-medium">{thread.conversation.contact_name || thread.conversation.contact_phone}</p>
                      <p className="text-xs text-muted-foreground">{thread.conversation.contact_phone}</p>
                    </div>
                    {can("leads", "update") ? (
                      <Button data-testid={CONTACT_EDIT.inboxBtn} size="icon" variant="ghost" className="h-7 w-7"
                        onClick={() => setEditOpen(true)} title="Edit kontak">
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                    ) : null}
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span data-testid={INBOX.windowBadge} className={cn("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
                      windowOpen ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700")}>
                      <Clock className="h-3.5 w-3.5" /> {windowOpen ? "Sesi 24 jam aktif" : "Sesi tertutup"}
                      {windowOpen && thread.conversation.window_remaining_minutes != null ? (
                        <span data-testid={P94.windowRemaining} className="tabular-nums">
                          · sisa {String(Math.floor(thread.conversation.window_remaining_minutes / 60)).padStart(2, "0")}:{String(thread.conversation.window_remaining_minutes % 60).padStart(2, "0")}
                        </span>
                      ) : null}
                    </span>
                    <Button size="icon" variant="outline" className="h-8 w-8 lg:hidden" title="Info lead"
                      onClick={() => setMobileView("info")}><Info className="h-4 w-4" /></Button>
                  </div>
                </div>
                <div ref={msgBoxRef} onScroll={onMsgScroll} onClick={markReadNow} data-testid="inbox-messages"
                  className="min-h-0 flex-1 space-y-2.5 overflow-y-auto p-4">
                  {thread.has_more ? (
                    <div className="flex justify-center">
                      <Button data-testid="inbox-load-older" size="sm" variant="outline" disabled={olderLoading} onClick={loadOlder}>
                        {olderLoading ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : null}
                        Muat pesan sebelumnya
                      </Button>
                    </div>
                  ) : null}
                  {thread.messages.map((m) => <MessageBubble key={m.id} m={m} />)}
                </div>
                <div className="border-t p-3">
                  {!windowOpen ? (
                    <div className="mb-2 flex items-center gap-1.5 rounded-lg bg-amber-50 px-2.5 py-1.5 text-[11px] text-amber-700">
                      <ShieldAlert className="h-3.5 w-3.5" /> Sesi 24 jam tertutup — mulai dengan template WA pra-approved.
                    </div>
                  ) : null}
                  <div className="mb-2 flex items-center gap-2">
                    <Select value={tmplCode} onValueChange={setTmplCode}>
                      <SelectTrigger data-testid={INBOX.templatePick} className="h-9">
                        <SelectValue placeholder="Kirim template…" />
                      </SelectTrigger>
                      <SelectContent>
                        {templates.map((t) => <SelectItem key={t.id} value={t.code}>{t.name}</SelectItem>)}
                      </SelectContent>
                    </Select>
                    <Button data-testid={INBOX.templateBtn} size="sm" variant="secondary"
                      onClick={sendTemplate} disabled={busy || !tmplCode}>Kirim Template</Button>
                  </div>
                  <Textarea data-testid={INBOX.messageInput} rows={2} onFocus={markReadNow}
                    placeholder={windowOpen ? "Ketik balasan…" : "Sesi tertutup — gunakan template di atas"}
                    value={text} onChange={(e) => setText(e.target.value)} disabled={!windowOpen} />
                  <div className="mt-2 flex justify-between gap-2">
                    {canSimulate ? (
                      <Button data-testid={INBOX.simulateInbound} variant="outline" size="sm"
                        title="Hanya untuk uji coba (mode simulasi): mencatat teks sebagai pesan dari pelanggan"
                        onClick={() => send("in")} disabled={busy || !text.trim()}>
                        <Zap className="mr-1.5 h-4 w-4" /> Kirim sbg Pesan Masuk (simulasi)
                      </Button>
                    ) : <span />}
                    <Button data-testid={INBOX.sendBtn} size="sm" onClick={() => send("out")}
                      disabled={busy || !text.trim() || !windowOpen}>
                      <Send className="mr-1.5 h-4 w-4" /> Balas
                    </Button>
                  </div>
                </div>
              </>
            ) : (
              <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
                {threadLoading || activeId ? <Loader2 className="h-5 w-5 animate-spin" /> : "Pilih percakapan"}
              </div>
            )}
          </section>

          {/* ===== Konteks lead (gulir sendiri) ===== */}
          <section data-testid="inbox-context-pane"
            className={cn("min-h-0 flex-col overflow-y-auto", mobileView === "info" ? "flex" : "hidden", "lg:flex")}>
            {thread ? (
              <>
                <Button size="sm" variant="ghost" className="mb-2 w-fit lg:hidden" onClick={() => setMobileView("thread")}>
                  <ArrowLeft className="mr-1 h-4 w-4" /> Kembali ke percakapan
                </Button>
                <InboxContextPanel leadId={thread.conversation.lead_id}
                  conversationId={thread.conversation.id}
                  contactPhone={thread.conversation.contact_phone} onChanged={refresh} />
              </>
            ) : (
              <div className="rounded-xl border bg-card p-4 text-sm text-muted-foreground shadow-[var(--shadow-card)]">Konteks lead tampil di sini.</div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
