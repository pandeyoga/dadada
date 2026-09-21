/** Rincian OD — panel info: item custom (kiri), pelanggan + riwayat status (kanan). Gaya seragam dgn panel Fase 2–4. */
import { Clock, Package, User, History } from "lucide-react";
import { STATUS_STYLE, fmtNum, fmtDate } from "./SpecialOrderShared";

const K = ({ children }) => <p className="text-[10px] font-bold uppercase tracking-wide text-[#8E8E93]">{children}</p>;
const Head = ({ icon: Icon, children, right }) => (
  <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
    <p className="flex items-center gap-1 text-[10.5px] font-bold uppercase tracking-wide text-[#8E8E93]">{Icon && <Icon size={12} />} {children}</p>
    {right}
  </div>
);

export function SpecialOrderInfoPanels({ order }) {
  const ci = order.custom_item || {};
  const specs = Object.entries(ci.specifications || {}).filter(([, v]) => v !== "" && v != null);
  const addr = order.shipping_address;
  return (
    <div className="grid items-start gap-3 md:grid-cols-2" data-testid="special-order-info-panels">
      <section className="section-card !p-3" data-testid="od-item-panel">
        <Head icon={Package}>Rincian item custom</Head>
        <div className="grid gap-2.5 text-[12px]">
          <div><K>Deskripsi</K><p className="font-semibold" data-testid="od-item-description">{ci.description || order.title || "—"}</p></div>
          {specs.length > 0 ? (
            <div><K>Spesifikasi custom</K>
              <dl className="mt-0.5 grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-[11.5px]">
                {specs.map(([k, v]) => <><dt key={`k-${k}`} className="text-[#6B6B73]">{k}</dt><dd key={`v-${k}`} className="font-medium">{String(v)}</dd></>)}
              </dl>
            </div>
          ) : <p className="text-[11px] italic text-[#9A9BA3]">Belum ada spesifikasi custom di item — lihat panel Spesifikasi target di atas.</p>}
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <Cell label="Jumlah" testId="od-item-qty"><b>{fmtNum(ci.quantity, 2)}</b> {ci.unit}</Cell>
            <Cell label="Harga target" testId="od-item-target">Rp {fmtNum(ci.target_price, 0)}</Cell>
            <Cell label="Nilai pesanan" testId="od-item-total"><b className="text-[#0058CC]">Rp {fmtNum(order.total_amount, 0)}</b></Cell>
            <Cell label="Perkiraan kirim" testId="od-item-eta"><Clock size={11} className="mr-1 inline" />{fmtDate(order.expected_delivery)}</Cell>
          </div>
          {order.notes && <div><K>Catatan</K><p className="whitespace-pre-wrap text-[11.5px] text-[#3C3C43]">{order.notes}</p></div>}
        </div>
      </section>

      <div className="grid gap-3">
        <section className="section-card !p-3" data-testid="od-customer-panel">
          <Head icon={User}>Info pelanggan</Head>
          <div className="grid gap-1.5 text-[12px] sm:grid-cols-2">
            <div><K>Nama</K><p className="font-semibold">{order.customer_name || "—"}</p></div>
            {order.customer_phone && <div><K>Telepon</K><p>{order.customer_phone}</p></div>}
            {order.customer_email && <div><K>Email</K><p className="truncate" title={order.customer_email}>{order.customer_email}</p></div>}
            {addr && (addr.street || addr.city) && (
              <div className="sm:col-span-2"><K>Alamat kirim</K>
                <p className="text-[11.5px]">{[addr.street, [addr.city, addr.province].filter(Boolean).join(", "), addr.postal_code].filter(Boolean).join(" · ")}</p>
              </div>
            )}
          </div>
        </section>

        {order.status_history?.length > 0 && (
          <section className="section-card !p-3" data-testid="od-status-timeline">
            <Head icon={History}>Riwayat status · {order.status_history.length}</Head>
            <ol className="grid gap-1.5">
              {order.status_history.slice().reverse().map((h, i) => {
                const s = STATUS_STYLE[h.status] || {};
                const Icon = s.icon || Clock;
                return (
                  <li key={i} className="flex items-start gap-2 text-[11.5px]">
                    <Icon size={13} className="mt-0.5 shrink-0 text-[#8E8E93]" />
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold">{s.label || h.status}{h.note && <span className="font-normal text-[#3C3C43]"> — {h.note}</span>}</p>
                      <p className="text-[10.5px] text-[#8E8E93]">{fmtDate(h.timestamp)} · {h.user || "sistem"}</p>
                    </div>
                  </li>
                );
              })}
            </ol>
          </section>
        )}
      </div>
    </div>
  );
}

function Cell({ label, children, testId }) {
  return <div className="rounded-lg border border-[#EFF0F2] bg-white p-2" data-testid={testId}><K>{label}</K><div className="mt-0.5 text-[12px]">{children}</div></div>;
}
