import React, { useCallback, useState } from "react";
import { Receipt } from "lucide-react";
import Page, { Loading } from "../../buyer/Page";
import { FrostCard } from "../../../components/GlassCard";
import ListRow from "../../../components/ListRow";
import StatusChip from "../../../components/StatusChip";
import EmptyState from "../../../components/EmptyState";
import ReceiptCard from "../../../components/pay/ReceiptCard";
import { listReceipts } from "../../../services/api/bills";
import { rupiah, tanggal } from "../../../lib/format";
import useLoad from "../../../lib/useLoad";

const KIND = { bill: "IPL", ppob: "Isi ulang", installment: "Rumah" };

/** W11: riwayat semua kuitansi (IPL, isi ulang, dan cicilan rumah), terbaru dulu. */
export default function BillHistory() {
  const fetcher = useCallback(() => listReceipts(), []);
  const { data, error } = useLoad(fetcher, ["bills"]);
  const [openId, setOpenId] = useState(null);
  return (
    <Page id="W11" title="Riwayat pembayaran" back="/app/warga/tagihan" nav="resident">
      {!data && <Loading error={error} />}
      {data && data.length === 0 && <EmptyState title="Belum ada pembayaran" body="Kuitansi muncul di sini setelah Anda membayar." />}
      {data && data.length > 0 && (
        <FrostCard className="divide-y divide-[color:var(--rdg-line)] !p-1">
          {data.map((r) => (
            <div key={r.id}>
              <ListRow
                icon={Receipt}
                title={r.title}
                subtitle={`${tanggal(r.paidAt)} · ${rupiah(r.amount)}`}
                right={<StatusChip tone="neutral" icon={null}>{KIND[r.targetType] || "Lainnya"}</StatusChip>}
                onClick={() => setOpenId(openId === r.id ? null : r.id)}
              />
              {openId === r.id && <div className="px-3 pb-3"><ReceiptCard receipt={r} /></div>}
            </div>
          ))}
        </FrostCard>
      )}
    </Page>
  );
}
