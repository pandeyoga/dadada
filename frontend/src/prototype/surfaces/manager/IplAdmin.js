import React, { useCallback, useState } from "react";
import { Send, FilePlus2 } from "lucide-react";
import ManagerPage, { Panel, Table, Loading, FIELD, TH, TD, SMALL_BTN } from "./ManagerPage";
import StatusChip from "../../components/StatusChip";
import { getIplOverview, issueIplBills, sendIplReminders, periodLabel } from "../../services/api/manager";
import { rupiah } from "../../lib/format";
import useLoad from "../../lib/useLoad";

const TONE = { lunas: "ok", belum: "warn", terlambat: "danger" };
const TEXT = { lunas: "Lunas", belum: "Belum bayar", terlambat: "Terlambat" };
const nextPeriod = (p) => {
  const [y, m] = p.split("-").map(Number);
  return m === 12 ? `${y + 1}-01` : `${y}-${String(m + 1).padStart(2, "0")}`;
};
// Periode berjalan + 12 bulan berikutnya (nama bulan bahasa Indonesia, tidak bergantung bahasa peramban).
const periodOptions = (p) => {
  const out = [p];
  while (out.length < 13) out.push(nextPeriod(out[out.length - 1]));
  return out;
};

/** K2: tagihan IPL per unit, terbitkan periode baru, kirim pengingat. */
export default function IplAdmin() {
  const fetcher = useCallback(() => getIplOverview(), []);
  const { data, error } = useLoad(fetcher, ["manager", "bills"]);
  const [period, setPeriod] = useState(null);
  const [picked, setPicked] = useState([]);
  const [msg, setMsg] = useState({ ok: "", err: "" });
  const [busy, setBusy] = useState(false);

  const run = async (job) => {
    setBusy(true);
    try { setMsg({ ok: await job(), err: "" }); } catch (e) { setMsg({ ok: "", err: e.message }); }
    setBusy(false);
  };
  const value = period == null ? (data ? nextPeriod(data.period) : "") : period;
  const issue = () => run(async () => {
    const { created } = await issueIplBills(value);
    return `${created} tagihan periode ${periodLabel(value)} diterbitkan.`;
  });
  const remind = () => run(async () => {
    const { sent } = await sendIplReminders(picked);
    setPicked([]);
    return `Pengingat terkirim ke ${sent} unit.`;
  });
  const toggle = (b) => setPicked((p) => (p.includes(b) ? p.filter((x) => x !== b) : [...p, b]));

  return (
    <ManagerPage id="K2" title="Tagihan IPL" subtitle="Terbitkan iuran bulanan dan pantau siapa yang sudah membayar.">
      {!data && <Loading error={error} />}
      {data && (
        <>
          <Panel title="Terbitkan tagihan periode baru">
            <div className="flex flex-wrap items-end gap-3">
              <label className="block text-[13.5px] font-semibold">
                Periode tagihan
                <select value={value} onChange={(e) => setPeriod(e.target.value)} className={`${FIELD} w-[220px]`}>
                  {periodOptions(data.period).map((p) => <option key={p} value={p}>{periodLabel(p)}</option>)}
                </select>
              </label>
              <button type="button" className="rdg-btn-primary" onClick={issue} disabled={busy || !value}>
                <FilePlus2 size={18} aria-hidden="true" /> Terbitkan tagihan
              </button>
            </div>
            <p className="mt-2 text-[13px] text-[color:var(--rdg-muted)]">Satu tagihan Rp150.000 untuk setiap unit. Warga langsung melihatnya di aplikasi.</p>
            <div aria-live="polite">
              {msg.err && <p role="alert" className="mt-2 text-[14px] font-semibold text-[color:var(--rdg-sos-ink)]">{msg.err}</p>}
              {msg.ok && <p role="status" className="mt-2 text-[14px] font-semibold text-rdg-forest">{msg.ok}</p>}
            </div>
          </Panel>
          <Panel
            title={`Status unit · ${data.label} (${data.paid} dari ${data.total} lunas)`}
            right={
              <div className="flex flex-wrap gap-2">
                <button type="button" className={`rdg-btn-ghost ${SMALL_BTN}`} onClick={() => setPicked(data.units.filter((u) => u.status !== "lunas").map((u) => u.block))}>Pilih yang belum lunas</button>
                <button type="button" className={`rdg-btn-primary ${SMALL_BTN}`} disabled={busy || picked.length === 0} onClick={remind}>
                  <Send size={15} aria-hidden="true" /> {`Kirim pengingat${picked.length ? ` (${picked.length})` : ""}`}
                </button>
              </div>
            }
          >
            <Table label="Tagihan IPL per unit">
              <thead><tr className="border-b border-[color:var(--rdg-line)]">
                <th className={TH}><span className="sr-only">Pilih</span></th><th className={TH}>Blok</th><th className={TH}>Pemilik</th>
                <th className={`${TH} hidden xl:table-cell`}>Telepon</th><th className={TH}>Nominal</th><th className={TH}>Status</th>
              </tr></thead>
              <tbody>
                {data.units.map((u) => (
                  <tr key={u.block} className="border-b border-[color:var(--rdg-line)] last:border-0">
                    <td className={TD}>
                      <input type="checkbox" className="h-5 w-5 accent-[#006747]" aria-label={`Pilih ${u.block}`} checked={picked.includes(u.block)} onChange={() => toggle(u.block)} />
                    </td>
                    <td className={`${TD} font-bold`}>{u.block}</td>
                    <td className={TD}>{u.owner}</td>
                    <td className={`${TD} hidden xl:table-cell`}>{u.phone}</td>
                    <td className={TD}>{rupiah(u.amount)}</td>
                    <td className={TD}><StatusChip tone={TONE[u.status]}>{TEXT[u.status]}</StatusChip></td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </Panel>
        </>
      )}
    </ManagerPage>
  );
}
