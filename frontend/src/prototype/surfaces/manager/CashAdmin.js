import React, { useCallback } from "react";
import ManagerPage, { Panel, Table, Loading, TH, TD } from "./ManagerPage";
import { getCashReport } from "../../services/api/bills";
import { rupiah } from "../../lib/format";
import useLoad from "../../lib/useLoad";

function Bar({ value, max, color }) {
  return <div className="rdg-progress !h-2.5 w-full min-w-[80px]" aria-hidden="true"><span style={{ width: `${Math.round((value / max) * 100)}%`, background: color }} /></div>;
}

/** K5: laporan kas per bulan (tabel + batang sederhana, tanpa pustaka grafik). */
export default function CashAdmin() {
  const { data, error } = useLoad(useCallback(() => getCashReport(), []), ["bills"]);
  const months = data ? [...data.months].reverse() : [];
  const max = data ? Math.max(...data.months.map((m) => Math.max(m.in, m.out))) : 1;
  const last = months[0];
  return (
    <ManagerPage id="K5" title="Laporan kas" subtitle="Kas kawasan dari iuran IPL: yang masuk, yang dipakai, dan saldonya.">
      {!data && <Loading error={error} />}
      {data && last && (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            {[["Saldo kas terakhir", rupiah(last.balance)], ["Pemasukan bulan terakhir", rupiah(last.in)], ["Pengeluaran bulan terakhir", rupiah(last.out)]].map(([l, v]) => (
              <div key={l} className="rdg-frost !p-5"><p className="text-[13.5px] font-semibold text-[color:var(--rdg-muted)]">{l}</p><p className="mt-1 text-[24px] font-extrabold text-rdg-ink900">{v}</p></div>
            ))}
          </div>
          <Panel title="Per bulan">
            <Table label="Laporan kas per bulan">
              <thead><tr className="border-b border-[color:var(--rdg-line)]">
                <th className={TH}>Bulan</th><th className={TH}>Masuk</th><th className={TH}>Keluar</th><th className={TH}>Saldo</th><th className={`${TH} w-[26%]`}>Perbandingan</th>
              </tr></thead>
              <tbody>
                {months.map((m) => (
                  <tr key={m.month} className="border-b border-[color:var(--rdg-line)] last:border-0">
                    <th scope="row" className={`${TD} text-left font-bold`}>{m.month}</th>
                    <td className={TD}>{rupiah(m.in)}</td>
                    <td className={TD}>{rupiah(m.out)}</td>
                    <td className={`${TD} font-bold`}>{rupiah(m.balance)}</td>
                    <td className={TD}>
                      <div className="space-y-1"><Bar value={m.in} max={max} color="linear-gradient(90deg, #15874b, #0a8460)" /><Bar value={m.out} max={max} color="linear-gradient(90deg, #b9741a, #8a5410)" /></div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
            <p className="mt-2 flex gap-4 text-[12.5px] text-[color:var(--rdg-muted)]"><span>Hijau: masuk</span><span>Cokelat: keluar</span></p>
          </Panel>
          <Panel title={`Rincian ${last.month}`}>
            <ul className="divide-y divide-[color:var(--rdg-line)]">
              {last.items.map((it) => (
                <li key={it.label} className="flex justify-between gap-3 py-2 text-[14px]"><span>{it.label}</span><b>{`${it.amount < 0 ? "−" : "+"}${rupiah(Math.abs(it.amount))}`}</b></li>
              ))}
            </ul>
          </Panel>
        </>
      )}
    </ManagerPage>
  );
}
