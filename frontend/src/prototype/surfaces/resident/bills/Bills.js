import React, { useCallback, useState } from "react";
import { CalendarClock, CircleCheck, Wallet, History, ChartColumn, Smartphone } from "lucide-react";
import Page, { Loading } from "../../buyer/Page";
import { FrostCard } from "../../../components/GlassCard";
import ListRow from "../../../components/ListRow";
import StatusChip from "../../../components/StatusChip";
import PayFlow from "../../../components/PayFlow";
import ReceiptCard from "../../../components/pay/ReceiptCard";
import { listBills, listReceipts } from "../../../services/api/bills";
import { rupiah, tanggal } from "../../../lib/format";
import useLoad from "../../../lib/useLoad";

const BACK = "/app/warga";
const fetchAll = () => Promise.all([listBills(), listReceipts()]).then(([bills, receipts]) => ({ bills, receipts }));
const CHIP = { paid: ["ok", "Lunas"], pending: ["warn", "Menunggu pembayaran"], unpaid: ["neutral", "Belum dibayar"] };

/** W10: tagihan IPL bulan ini dan pintu ke riwayat, laporan kas, dan isi ulang. */
export default function Bills() {
  const fetcher = useCallback(fetchAll, []);
  const { data, error } = useLoad(fetcher, ["bills"]);
  const [payTarget, setPayTarget] = useState(null); // dipertahankan agar kuitansi tetap tampil setelah tagihan lunas
  const due = data && data.bills.find((b) => b.status !== "paid");
  const lastPaid = data && data.receipts.find((r) => r.targetType === "bill");
  return (
    <Page id="W10" title="Tagihan" back={BACK} nav="resident">
      {!data && <Loading error={error} />}
      {data && (
        <>
          {due ? (
            <FrostCard>
              <p className="text-[13.5px] font-semibold text-[color:var(--rdg-muted)]">IPL {due.period}</p>
              <p className="text-[34px] font-extrabold leading-tight tracking-[-0.02em]">{rupiah(due.amount)}</p>
              <p className="mt-1 flex items-center gap-1.5 text-[14px] text-[color:var(--rdg-muted)]">
                <CalendarClock size={15} aria-hidden="true" /> {`Jatuh tempo ${tanggal(due.dueDate)}`}
              </p>
              <button type="button" className="rdg-btn-primary mt-4 w-full" onClick={() => setPayTarget({ type: "bill", id: due.id, title: `IPL ${due.period}`, amount: due.amount })}>
                <Wallet size={19} aria-hidden="true" /> {due.status === "pending" ? "Lanjutkan pembayaran" : "Bayar sekarang"}
              </button>
              <p className="mt-2 text-[13px] text-[color:var(--rdg-muted)]">Bisa juga kirim link bayar ke WhatsApp keluarga.</p>
            </FrostCard>
          ) : (
            <FrostCard className="flex items-center gap-3">
              <CircleCheck size={30} className="flex-none text-rdg-green" aria-hidden="true" />
              <div>
                <p className="text-[17px] font-extrabold">Semua tagihan lunas</p>
                <p className="text-[13.5px] text-[color:var(--rdg-muted)]">Tagihan IPL berikutnya muncul bulan depan.</p>
              </div>
            </FrostCard>
          )}
          {!due && lastPaid && (
            <section aria-labelledby="w10-kuitansi" className="space-y-2">
              <h2 id="w10-kuitansi" className="text-[16px] font-extrabold">Kuitansi terakhir</h2>
              <ReceiptCard receipt={lastPaid} />
            </section>
          )}
          <section aria-labelledby="w10-daftar">
            <h2 id="w10-daftar" className="mb-2 text-[16px] font-extrabold">Tagihan IPL</h2>
            <FrostCard className="divide-y divide-[color:var(--rdg-line)] !p-1">
              {data.bills.map((b) => {
                const [tone, text] = CHIP[b.status] || CHIP.unpaid;
                return (
                  <ListRow key={b.id} icon={Wallet} title={`IPL ${b.period}`} subtitle={rupiah(b.amount)} right={<StatusChip tone={tone}>{text}</StatusChip>} />
                );
              })}
            </FrostCard>
          </section>
          <FrostCard className="divide-y divide-[color:var(--rdg-line)] !p-1">
            <ListRow icon={History} title="Riwayat pembayaran" subtitle="Semua kuitansi Anda" to="/app/warga/tagihan/riwayat" />
            <ListRow icon={ChartColumn} title="Laporan kas kawasan" subtitle="Uang iuran masuk dan keluar tiap bulan" to="/app/warga/tagihan/kas" />
            <ListRow icon={Smartphone} title="Isi ulang" subtitle="Pulsa, paket data, token listrik, air" to="/app/warga/isi-ulang" />
          </FrostCard>
          <PayFlow open={Boolean(payTarget)} onClose={() => setPayTarget(null)} target={payTarget} onPaid={() => {}} />
        </>
      )}
    </Page>
  );
}
