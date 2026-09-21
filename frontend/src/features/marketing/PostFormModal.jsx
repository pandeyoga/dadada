/** PostFormModal — buat / ubah konten: judul, caption, hashtag, platform, jadwal, PIC, kampanye, bahan (desain/produk/OD). */
import { useEffect, useState } from "react";
import { Megaphone, Search, X } from "lucide-react";
import FormModal from "../../components/FormModal";
import { KNSelect } from "../../components/KNSelect";
import { Field } from "../rnd/RndField";
import axios, { API } from "../../services/apiClient";
import { mktApi, PLATFORM_STYLE } from "./marketingShared";

export default function PostFormModal({ meta, campaigns = [], initial = {}, post = null, onClose, onSaved }) {
  const [f, setF] = useState({
    title: post?.title || "", caption: post?.caption || "", hashtags: (post?.hashtags || []).map((h) => `#${h}`).join(" "),
    platforms: post?.platforms || [], content_type: post?.content_type || "foto", publish_at: post?.publish_at || initial.publish_at || "",
    campaign_id: post?.campaign_id || "", pic_user_id: post?.pic_user_id || "", cta: post?.cta || "", notes: post?.notes || "", assets: post?.assets || [],
    account_ids: (post?.accounts || []).map((a) => a.id),
  });
  const [accounts, setAccounts] = useState([]);
  useEffect(() => { axios.get(`${API}/marketing/accounts`).then((r) => setAccounts((r.data || []).filter((a) => a.active))).catch(() => {}); }, []);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [q, setQ] = useState("");
  const [found, setFound] = useState(null);
  const set = (k, v) => setF((s) => ({ ...s, [k]: v }));
  const toggle = (c) => set("platforms", f.platforms.includes(c) ? f.platforms.filter((x) => x !== c) : [...f.platforms, c]);

  useEffect(() => {
    if (q.length < 2) { setFound(null); return undefined; }
    const t = setTimeout(() => mktApi.assets(q).then(setFound).catch(() => {}), 300);
    return () => clearTimeout(t);
  }, [q]);

  const addAsset = (ref_type, item) => {
    const label = ref_type === "design" ? `${item.code} · ${item.title || ""}` : ref_type === "product" ? `${item.sku} · ${item.name}` : `${item.number} · ${item.title || item.customer_name}`;
    if (f.assets.some((a) => a.ref_id === item.id)) return;
    set("assets", [...f.assets, { ref_type, ref_id: item.id, label }]); setQ(""); setFound(null);
  };

  const submit = async () => {
    setBusy(true); setErr("");
    try {
      const body = { ...f, hashtags: f.hashtags };
      const saved = post ? await mktApi.updatePost(post.id, body) : await mktApi.createPost(body);
      onSaved?.(saved);
    } catch (e) { setErr(e.response?.data?.detail || "Gagal menyimpan konten."); } finally { setBusy(false); }
  };

  const capLen = f.caption.length;
  return (
    <FormModal open title={post ? `Ubah konten · ${post.title}` : "Konten baru"} subtitle="Rencanakan post: apa, di mana, kapan, siapa yang memposting." icon={Megaphone} size="lg"
      onClose={onClose} onSubmit={submit} busy={busy} error={err} submitLabel={post ? "Simpan perubahan" : "Simpan sebagai ide"} testId="mkt-post-form" submitTestId="mkt-post-submit" cancelTestId="mkt-post-cancel">
      <div className="grid gap-3">
        <Field label="Judul konten *"><input className="field w-full" value={f.title} onChange={(e) => set("title", e.target.value)} placeholder="mis. Koleksi Batik Mega Mendung — warna baru Navy" data-testid="mkt-f-title" /></Field>
        <Field label="Platform *">
          <div className="flex flex-wrap gap-1.5" data-testid="mkt-f-platforms">
            {Object.entries(PLATFORM_STYLE).map(([c, p]) => (
              <button key={c} type="button" onClick={() => toggle(c)} data-testid={`mkt-f-platform-${c}`}
                className={`rounded-full border px-3 py-1 text-[11px] font-bold ${f.platforms.includes(c) ? "border-transparent" : "border-[#E5E5EA] bg-white text-[#6B6B73]"}`}
                style={f.platforms.includes(c) ? { background: p.bg, color: p.fg } : undefined}>{p.label}</button>
            ))}
          </div>
        </Field>
        {accounts.filter((a) => f.platforms.includes(a.platform)).length > 0 && (
          <Field label={`Akun sosmed yang memposting · ${meta?.active_entity_name || ""}`}>
            <div className="flex flex-wrap gap-1.5" data-testid="mkt-f-accounts">
              {accounts.filter((a) => f.platforms.includes(a.platform)).map((a) => {
                const on = f.account_ids.includes(a.id); const p = PLATFORM_STYLE[a.platform] || {};
                return <button key={a.id} type="button" data-testid={`mkt-f-account-${a.id}`} onClick={() => set("account_ids", on ? f.account_ids.filter((x) => x !== a.id) : [...f.account_ids, a.id])}
                  className={`rounded-full border px-2.5 py-1 text-[11px] font-bold ${on ? "border-transparent" : "border-[#E5E5EA] bg-white text-[#6B6B73]"}`} style={on ? { background: p.bg, color: p.fg } : undefined}>@{a.handle}{a.label ? ` · ${a.label}` : ""}</button>;
              })}
            </div>
          </Field>
        )}
        {!post && meta?.active_entity_name && <p className="text-[10.5px] text-[#8E8E93]" data-testid="mkt-f-entity-note">Konten ini dibuat untuk badan usaha <b>{meta.active_entity_name}</b>.</p>}
        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="Jenis konten"><KNSelect data-testid="mkt-f-type" className="field" value={f.content_type} onValueChange={(v) => set("content_type", v)} options={(meta?.content_types || ["foto"]).map((t) => ({ value: t, label: t }))} /></Field>
          <Field label="Tanggal & jam tayang"><input type="datetime-local" className="field w-full" value={f.publish_at} onChange={(e) => set("publish_at", e.target.value)} data-testid="mkt-f-publish-at" /></Field>
          <Field label="PIC (yang memposting)"><KNSelect data-testid="mkt-f-pic" className="field" value={f.pic_user_id} onValueChange={(v) => set("pic_user_id", v)} options={[{ value: "", label: "— pilih —" }, ...(meta?.pic_options || []).map((u) => ({ value: u.id, label: `${u.name} (${u.role})` }))]} /></Field>
        </div>
        <Field label="Kampanye"><KNSelect data-testid="mkt-f-campaign" className="field" value={f.campaign_id} onValueChange={(v) => set("campaign_id", v)} options={[{ value: "", label: "— tanpa kampanye —" }, ...campaigns.filter((c) => c.status !== "archived").map((c) => ({ value: c.id, label: `${c.name}${c.start_date ? ` (${c.start_date} → ${c.end_date || "…"})` : ""}` }))]} /></Field>
        <Field label={`Caption · ${capLen} karakter${capLen > 2200 ? " (melebihi batas Instagram 2.200)" : ""}`}>
          <textarea className="field w-full" rows={5} value={f.caption} onChange={(e) => set("caption", e.target.value)} placeholder="Tulis caption lengkap di sini…" data-testid="mkt-f-caption" />
        </Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Hashtag (pisahkan spasi)"><input className="field w-full" value={f.hashtags} onChange={(e) => set("hashtags", e.target.value)} placeholder="#kainnusantara #batik #kainpremium" data-testid="mkt-f-hashtags" /></Field>
          <Field label="Ajakan (CTA)"><input className="field w-full" value={f.cta} onChange={(e) => set("cta", e.target.value)} placeholder="mis. DM untuk katalog / Klik link di bio" data-testid="mkt-f-cta" /></Field>
        </div>
        <Field label="Bahan konten — tautkan desain galeri / produk / pesanan khusus">
          <div className="relative">
            <Search size={12} className="absolute left-2 top-2.5 text-[#9A9BA3]" />
            <input className="field w-full !pl-7" value={q} onChange={(e) => setQ(e.target.value)} placeholder="cari kode desain, SKU, nama produk, nomor OD…" data-testid="mkt-f-asset-search" />
            {found && (
              <div className="absolute z-20 mt-1 max-h-56 w-full overflow-auto rounded-lg border border-[#E5E5EA] bg-white p-1 text-[11px] shadow-lg" data-testid="mkt-f-asset-results">
                {found.designs.map((d) => <Row key={d.id} onClick={() => addAsset("design", d)} tag="Desain" text={`${d.code} · ${d.title || ""}`} />)}
                {found.products.map((p) => <Row key={p.id} onClick={() => addAsset("product", p)} tag="Produk" text={`${p.sku} · ${p.name}`} />)}
                {found.special_orders.map((o) => <Row key={o.id} onClick={() => addAsset("special_order", o)} tag="OD" text={`${o.number} · ${o.title || o.customer_name}`} />)}
                {!found.designs.length && !found.products.length && !found.special_orders.length && <p className="p-2 text-[#9A9BA3]">tidak ada hasil</p>}
              </div>
            )}
          </div>
          <div className="mt-1.5 flex flex-wrap gap-1.5" data-testid="mkt-f-assets">
            {f.assets.map((a) => <span key={a.ref_id} className="inline-flex items-center gap-1 rounded-full bg-[#F2F2F7] px-2 py-0.5 text-[10.5px]" data-testid={`mkt-f-asset-${a.ref_id}`}>{a.label}<button type="button" onClick={() => set("assets", f.assets.filter((x) => x.ref_id !== a.ref_id))}><X size={10} /></button></span>)}
          </div>
        </Field>
        <Field label="Catatan internal"><input className="field w-full" value={f.notes} onChange={(e) => set("notes", e.target.value)} placeholder="brief untuk desainer / referensi visual" data-testid="mkt-f-notes" /></Field>
      </div>
    </FormModal>
  );
}

function Row({ onClick, tag, text }) {
  return <button type="button" onClick={onClick} className="flex w-full items-center gap-2 rounded-md px-2 py-1 text-left hover:bg-[#F2F6FF]"><span className="w-12 rounded bg-[#EEF2FF] px-1 text-center text-[9.5px] font-bold text-[#3730A3]">{tag}</span><span className="truncate">{text}</span></button>;
}
