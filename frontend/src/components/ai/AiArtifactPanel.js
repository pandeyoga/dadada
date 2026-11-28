import React, { useState } from "react";
import { Download, X } from "lucide-react";
import { downloadArtifact, friendlyError } from "./aiApi";
import { renderMarkdown } from "./aiMarkdown";

const BAR_COLORS = ["#006284", "#007F83", "#01916F", "#209F59", "#49AE42"];

/**
 * Artefak: { id, title, subtitle, is_sample, updated_at, sources, kinds?: ["pdf","xlsx"],
 *   blocks: [{type:"bars", title, items:[{label,value}]} | {type:"table", title, columns, rows} | {type:"markdown", text}] }
 */
export default function AiArtifactPanel({ artifact, onClose, onAskAgent }) {
  const [tab, setTab] = useState("preview");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState("");
  if (!artifact) return null;
  const blocks = artifact.blocks || [];
  const tables = blocks.filter((b) => b.type === "table");
  const kinds = artifact.kinds || ["pdf", "xlsx"];

  const dl = async (kind) => {
    setBusy(kind); setErr("");
    try { await downloadArtifact(artifact, kind); } catch (e) { setErr(friendlyError(e, "Unduhan gagal.")); }
    finally { setBusy(""); }
  };

  return (
    <section aria-label="Panel laporan" data-testid="ai-artifact-panel"
      className={"box-border flex min-w-0 flex-col gap-4 border-l border-[#E1EAE7] bg-white px-[22px] py-[18px] "
        // < 2xl (mis. 1280–1440 px dengan sidebar aplikasi terbuka): laci di kanan menimpa chat, tidak turun ke bawah.
        + "fixed bottom-0 right-0 top-16 z-40 w-[min(460px,100vw)] overflow-y-auto shadow-[-8px_0_24px_rgba(18,49,47,0.14)] "
        + "2xl:static 2xl:z-auto 2xl:w-auto 2xl:flex-[1_1_440px] 2xl:overflow-visible 2xl:shadow-none"}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 flex-col">
          <span className="text-xs font-semibold text-[#3E5653]">LAPORAN</span>
          <h2 className="m-0 font-['Space_Grotesk',Inter,sans-serif] text-xl">{artifact.title}</h2>
        </div>
        <div className="flex flex-none items-center gap-2">
          {artifact.is_sample ? (
            <span className="rounded-md bg-[#FFF4E5] px-2 py-1 text-xs font-semibold text-[#7A3E00]">Data contoh</span>
          ) : null}
          <button type="button" onClick={onClose} aria-label="Tutup panel laporan"
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-[#DDE7E3] text-[#3E5653]">
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      </div>

      <div role="tablist" className="flex gap-1 self-start rounded-[10px] bg-[#EEF3F1] p-1">
        {[["preview", "Pratinjau"], ["data", "Data"]].map(([k, l]) => (
          <button key={k} role="tab" type="button" aria-selected={tab === k} onClick={() => setTab(k)}
            className={`min-h-[34px] rounded-lg px-3.5 text-[13px] font-semibold ${tab === k ? "bg-white text-[#12312F]" : "text-[#3E5653]"}`}>
            {l}
          </button>
        ))}
      </div>

      {tab === "preview" ? blocks.map((b, i) => <Block key={i} block={b} />) : (
        tables.length ? tables.map((b, i) => <DataTable key={i} block={b} />)
          : <p className="text-sm text-[#3E5653]">Laporan ini tidak punya tabel data.</p>
      )}
      {!blocks.length ? <p className="text-sm text-[#3E5653]">Laporan masih disiapkan atau kosong.</p> : null}

      <div className="mt-auto flex flex-wrap gap-2">
        {kinds.includes("pdf") ? (
          <button type="button" onClick={() => dl("pdf")} disabled={!!busy} data-testid="ai-dl-pdf"
            className="inline-flex min-h-[44px] items-center gap-1.5 rounded-[10px] bg-[#006284] px-3.5 text-sm font-semibold text-white hover:bg-[#00454D] disabled:opacity-60">
            <Download className="h-4 w-4" aria-hidden="true" /> Unduh PDF
          </button>
        ) : null}
        {kinds.includes("xlsx") ? (
          <button type="button" onClick={() => dl("xlsx")} disabled={!!busy} data-testid="ai-dl-xlsx"
            className="inline-flex min-h-[44px] items-center gap-1.5 rounded-[10px] border border-[#B9CFC8] bg-white px-3.5 text-sm font-semibold text-[#12312F] disabled:opacity-60">
            <Download className="h-4 w-4" aria-hidden="true" /> Unduh Excel
          </button>
        ) : null}
        <button type="button" onClick={() => onAskAgent?.(`Kirim laporan "${artifact.title}" ke WhatsApp. Tanyakan dulu nomor tujuannya.`)}
          className="inline-flex min-h-[44px] items-center rounded-[10px] border border-[#B9CFC8] bg-white px-3.5 text-sm font-semibold text-[#12312F]">
          Kirim ke WhatsApp
        </button>
      </div>
      {err ? <p role="alert" className="m-0 text-[13px] text-[#9B1C1C]">{err}</p> : null}
      <p className="m-0 text-xs text-[#3E5653]">
        {artifact.updated_at ? `Diperbarui ${new Date(artifact.updated_at).toLocaleString("id-ID")}` : ""}
        {artifact.sources?.length ? ` · Sumber: ${artifact.sources.join(", ")}` : ""}
      </p>
    </section>
  );
}

function Block({ block }) {
  if (block.type === "bars") {
    const items = block.items || [];
    const max = Math.max(1, ...items.map((x) => Number(x.value) || 0));
    return (
      <figure className="m-0 flex flex-col gap-2" role="img"
        aria-label={`${block.title || "Grafik"}: ${items.map((x) => `${x.label} ${x.value}`).join(", ")}`}>
        <figcaption className="text-[13px] font-semibold text-[#2B4744]">{block.title}</figcaption>
        <div className="grid grid-cols-[96px_minmax(0,1fr)_56px] items-center gap-2 text-[13px]">
          {items.map((x, i) => (
            <React.Fragment key={x.label}>
              <span>{x.label}</span>
              <div className="h-[26px] rounded-md" style={{ width: `${Math.max(2, ((Number(x.value) || 0) / max) * 100)}%`, background: BAR_COLORS[i % BAR_COLORS.length] }} />
              <b>{x.value}</b>
            </React.Fragment>
          ))}
        </div>
      </figure>
    );
  }
  if (block.type === "table") return <DataTable block={block} />;
  if (block.type === "markdown") {
    // Teks laporan = markdown ringan: di-escape lalu disanitasi DOMPurify (tag terbatas, tanpa atribut).
    return <div className="ai-md m-0 text-sm leading-relaxed [&_ol]:my-1.5 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:my-1.5 [&_ul]:my-1.5 [&_ul]:list-disc [&_ul]:pl-5"
      data-testid="ai-artifact-text" dangerouslySetInnerHTML={{ __html: renderMarkdown(block.text) }} />;
  }
  return null;
}

function DataTable({ block }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-[13px]">
        {block.title ? <caption className="pb-1.5 text-left font-semibold text-[#2B4744]">{block.title}</caption> : null}
        <thead>
          <tr className="text-left text-[#3E5653]">
            {(block.columns || []).map((c) => <th key={c} className="border-b border-[#E1EAE7] px-1.5 py-2">{c}</th>)}
          </tr>
        </thead>
        <tbody>
          {(block.rows || []).map((r, i) => (
            <tr key={i}>{r.map((v, j) => <td key={j} className="border-b border-[#EEF3F1] px-1.5 py-2">{v}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
