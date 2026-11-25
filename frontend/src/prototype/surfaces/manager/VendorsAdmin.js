import React, { useCallback, useState } from "react";
import ManagerPage, { Panel, Table, Loading, TH, TD, SMALL_BTN } from "./ManagerPage";
import StatusChip from "../../components/StatusChip";
import { listVendors, setVendorStatus } from "../../services/api/manager";
import useLoad from "../../lib/useLoad";

function VendorTable({ label, rows, onToggle }) {
  return (
    <Table label={label}>
      <thead><tr className="border-b border-[color:var(--rdg-line)]"><th className={TH}>Nama</th><th className={TH}>Lokasi</th><th className={TH}>Kategori</th><th className={TH}>Status</th><th className={TH}><span className="sr-only">Aksi</span></th></tr></thead>
      <tbody>
        {rows.map((v) => {
          const off = v.status === "ditangguhkan";
          return (
            <tr key={v.id} className="border-b border-[color:var(--rdg-line)] last:border-0">
              <td className={`${TD} font-bold`}>{v.name}</td><td className={TD}>{v.place}</td><td className={TD}>{v.category}</td>
              <td className={TD}><StatusChip tone={off ? "danger" : "ok"}>{off ? "Ditangguhkan" : "Aktif"}</StatusChip></td>
              <td className={`${TD} text-right`}>
                <button type="button" className={`rdg-btn-ghost ${SMALL_BTN}`} aria-label={`${off ? "Aktifkan" : "Tangguhkan"} ${v.name}`} onClick={() => onToggle(v)}>{off ? "Aktifkan" : "Tangguhkan"}</button>
              </td>
            </tr>
          );
        })}
      </tbody>
    </Table>
  );
}

/** K7: mitra penyewa ruko dan penyedia jasa. Mitra yang ditangguhkan hilang dari Pasar warga dan Jasa rumah. */
export default function VendorsAdmin() {
  const { data, error } = useLoad(useCallback(() => listVendors(), []), ["manager"]);
  const [err, setErr] = useState("");
  const toggle = async (v) => {
    try { await setVendorStatus(v.id, v.status === "ditangguhkan" ? "aktif" : "ditangguhkan"); setErr(""); } catch (e) { setErr(e.message); }
  };
  return (
    <ManagerPage id="K7" title="Mitra layanan dan pasar" subtitle="Menangguhkan mitra langsung menyembunyikan produk dan jasanya dari warga.">
      {err && <p role="alert" className="text-[14px] font-semibold text-[color:var(--rdg-sos-ink)]">{err}</p>}
      {!data && <Loading error={error} />}
      {data && (
        <>
          <Panel title="Penyewa ruko (Pasar warga)"><VendorTable label="Penyewa ruko" rows={data.filter((v) => v.kind === "tenant")} onToggle={toggle} /></Panel>
          <Panel title="Penyedia jasa rumah"><VendorTable label="Penyedia jasa" rows={data.filter((v) => v.kind === "jasa")} onToggle={toggle} /></Panel>
        </>
      )}
    </ManagerPage>
  );
}
