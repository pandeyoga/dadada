import { Settings2, Trash2 } from "lucide-react";
import { formatCurrency } from "../../utils/formatters";

const Row = ({ label, value, testId }) => <div className="spec-row" data-testid={testId}><dt>{label}</dt><dd>{value ?? "—"}</dd></div>;

/** Tab "Informasi produk": spesifikasi tersusun 2 kolom, atribut varian sebagai chip. */
export const FamilyInfoTab = ({ family, caps, onPolicy, onArchive }) => <div className="catalog-information" data-testid="catalog-info-tab">
  <div className="info-grid">
    <section className="info-card">
      <h2 data-testid="family-description-title">Deskripsi produk</h2>
      <p data-testid="family-description-text" className="info-desc">{family.description || "Belum ada deskripsi."}</p>
    </section>
    <section className="info-card">
      <h2>Spesifikasi teknis</h2>
      <dl className="spec-list">
        <Row label="Kategori" value={family.category} />
        <Row label="Jenis kain" value={family.fabric_type} />
        <Row label="Motif" value={family.motif} />
        <Row label="Tahapan" value={{ finished: "Kain jadi", greige: "Greige", yarn: "Benang", dyed: "Celup" }[family.stage] || family.stage} />
        <Row label="Satuan dasar" value={family.base_unit} />
        <Row label="Gramasi" value={family.gramasi ? `${family.gramasi} gsm` : null} />
        <Row label="Lebar" value={family.lebar ? `${family.lebar} m` : null} />
        <Row label="Benang" value={family.yarn_count ? `${family.yarn_count} ${family.yarn_count_system || ""}` : null} />
        <Row label="Harga dasar" value={formatCurrency(family.base_price || 0)} />
        <Row label="HPP" value={family.harga_pokok ? formatCurrency(family.harga_pokok) : null} />
        <Row label="Supplier" value={family.supplier} />
        <Row label="Lini produk" value={family.line_code} />
        <Row label="Eksklusivitas" value={family.exclusivity} />
        <Row label="Prefix SKU" value={<code>{family.sku_prefix}</code>} />
      </dl>
    </section>
    <section className="info-card">
      <h2 data-testid="family-base-fabric-title">Kain dasar (master data)</h2>
      <p data-testid="family-base-fabric-text">{family.base_fabric_name ? `${family.base_fabric_name}${family.base_fabric_sku_prefix ? ` · ${family.base_fabric_sku_prefix}` : ""}` : "Tidak ada — produk tidak bersumber dari kain master data lain."}</p>
    </section>
    <section className="info-card">
      <h2 data-testid="family-axis-title">Atribut varian</h2>
      {family.axes.length ? family.axes.map(a => <div key={a.key} className="axis-row" data-testid={`family-axis-info-${a.key}`}><b>{a.label}</b><span className="axis-chips">{a.options.map(o => <span key={o.code} className="catalog-swatch">{o.hex && <i style={{ background: o.hex }} />}{o.label}<small>{o.code}</small></span>)}</span></div>) : <p className="text-sm text-[#737780]">Induk satu varian — belum ada atribut.</p>}
    </section>
  </div>
  <div className="flex flex-wrap gap-2 pt-2">
    {caps.rnd_view && <button data-testid="catalog-rnd-policy" className="secondary-button" onClick={onPolicy}><Settings2 size={14} />Kebijakan produk baru</button>}
    {caps.delete && !family.variant_count && <button data-testid="catalog-archive" className="secondary-button text-red-700" onClick={onArchive}><Trash2 size={14} />Arsipkan induk kosong</button>}
  </div>
</div>;
