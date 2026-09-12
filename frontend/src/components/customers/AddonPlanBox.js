import React from "react";
import { Link } from "react-router-dom";
import { ExternalLink, Info, Package } from "lucide-react";

import MoneyText from "@/components/patterns/MoneyText";
import ReceiptProofLinks from "@/components/finance/ReceiptProofLinks";
import { formatDateWIB } from "@/utils/formatters";
import { CRMC } from "@/constants/testIds";

const paidOf = (item) => Number(item.paid_amount ?? item.paid ?? 0);

/**
 * AddonPlanBox — tagihan ADD-ON per kontrak, DIPISAH dari termin unit (seperti kotak Biaya
 * all-in). Add-on bukan dasar KPR (`kpr_excluded`): pencairan bank tidak melunasinya, jadi
 * pembeli harus tahu berapa yang wajib dibayar sendiri, kapan, dan dari kuitansi mana.
 */
export default function AddonPlanBox({ deal, items, receipts, planState, late }) {
  if (!items.length) return null;
  const master = Object.fromEntries((deal.addons || []).map((a) => [a.code, a]));
  const total = items.reduce((a, i) => a + Number(i.amount || 0), 0);
  const paid = items.reduce((a, i) => a + paidOf(i), 0);
  const ids = new Set(items.map((i) => i.id));
  const rcpts = (receipts || []).map((r) => ({
    ...r,
    addon_amount: (r.allocations || []).filter((al) => ids.has(al.item_id))
      .reduce((a, al) => a + Number(al.amount || 0), 0),
  })).filter((r) => r.addon_amount > 0);
  const overdue = items.filter((i) => planState(i, late).key === "terlambat").length;

  return (
    <div data-testid={CRMC.planAddon} className="space-y-2 rounded-xl border bg-card p-4 shadow-[var(--shadow-card)]">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="section-title flex items-center gap-1.5">
            <Package className="h-4 w-4" /> Add-on · {deal.unit_code || "Unit"}
          </p>
          <p className="text-[12px] text-muted-foreground">{items.length} item · ditagih terpisah dari termin unit</p>
        </div>
        <Link to="/finance?tab=ar" className="inline-flex items-center gap-1 text-[12px] font-medium text-primary hover:underline">
          Terima pembayaran di Keuangan <ExternalLink className="h-3 w-3" />
        </Link>
      </div>
      <p className="flex items-start gap-1.5 rounded-lg border border-sky-200 bg-sky-50 px-2.5 py-2 text-[12px] text-sky-900">
        <Info className="mt-0.5 h-4 w-4 shrink-0" />
        <span>
          Add-on (kelebihan tanah, upgrade, dsb.) <b>bukan bagian harga unit</b> dan <b>tidak dilunasi pencairan KPR</b>
          — dibayar pembeli sendiri sesuai jatuh tempo di bawah.
        </span>
      </p>
      <div data-testid={CRMC.planAddonSummary} className="grid gap-2 sm:grid-cols-4">
        {[["Total add-on", total], ["Sudah dibayar", paid], ["Sisa", total - paid],
          [`Terlambat · ${overdue} item`, items.filter((i) => planState(i, late).key === "terlambat")
            .reduce((a, i) => a + Number(i.amount || 0) - paidOf(i), 0)]].map(([label, val]) => (
          <div key={label} className="rounded-lg border bg-secondary/40 px-2.5 py-1.5">
            <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</p>
            <p className="font-semibold tabular-nums"><MoneyText value={val} /></p>
          </div>
        ))}
      </div>
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-[12px]">
          <thead className="bg-secondary/60 text-left text-[11px] text-muted-foreground">
            <tr>
              <th className="px-2.5 py-1.5">Item</th>
              <th className="px-2.5 py-1.5">Rincian</th>
              <th className="px-2.5 py-1.5">Jatuh tempo</th>
              <th className="px-2.5 py-1.5 text-right">Tagihan</th>
              <th className="px-2.5 py-1.5 text-right">Dibayar</th>
              <th className="px-2.5 py-1.5 text-right">Sisa</th>
              <th className="px-2.5 py-1.5">Keadaan</th>
            </tr>
          </thead>
          <tbody>
            {items.map((it) => {
              const m = master[it.addon_code] || {};
              const st = planState(it, late);
              const gross = Number(m.amount || 0);
              const cut = gross > Number(it.amount || 0) ? gross - Number(it.amount || 0) : 0;
              return (
                <tr key={it.id} data-testid={CRMC.planAddonRow} data-state={st.key} className="border-t">
                  <td className="px-2.5 py-1.5 font-medium">{m.name || (it.label || "").replace(/^Add-on · /, "")}</td>
                  <td className="px-2.5 py-1.5 text-muted-foreground">
                    {m.qty ? `${m.qty} ${m.uom || ""} × ` : ""}{m.unit_price ? <MoneyText value={m.unit_price} /> : "—"}
                    {cut ? <span className="ml-1 text-emerald-700">(potongan <MoneyText value={cut} />)</span> : null}
                  </td>
                  <td className="px-2.5 py-1.5 text-muted-foreground">{it.due_date ? formatDateWIB(it.due_date) : "—"}</td>
                  <td className="px-2.5 py-1.5 text-right tabular-nums"><MoneyText value={it.amount} /></td>
                  <td className="px-2.5 py-1.5 text-right tabular-nums"><MoneyText value={paidOf(it)} /></td>
                  <td className="px-2.5 py-1.5 text-right tabular-nums"><MoneyText value={Number(it.amount || 0) - paidOf(it)} /></td>
                  <td className="px-2.5 py-1.5">
                    <span className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${st.tone}`}>{st.label}</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {rcpts.length ? (
        <ul className="space-y-1">
          {rcpts.map((r) => (
            <li key={r.id} data-testid={CRMC.planAddonReceipt}
              className="flex items-center justify-between rounded-lg border px-2.5 py-1 text-[12px]">
              <span>{r.receipt_no || "Kuitansi"} · {formatDateWIB(r.created_at)}{r.method ? ` · ${r.method}` : ""}
                {" "}<ReceiptProofLinks receipt={r} /></span>
              <span className="font-semibold tabular-nums"><MoneyText value={r.addon_amount} /></span>
            </li>
          ))}
        </ul>
      ) : <p className="text-[12px] text-muted-foreground">Belum ada penerimaan yang dialokasikan ke add-on.</p>}
    </div>
  );
}
