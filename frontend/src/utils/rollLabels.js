import QRCode from "qrcode";

const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
/** QR berisi NOMOR ROLL → HP gudang memindai label tanpa RFID (GET /rfid/lookup?code=). */
const qrFor = async (text) => { try { return await QRCode.toDataURL(String(text || ""), { margin: 0, width: 120 }); } catch (_) { return ""; } };
const openPrint = (html) => { const w = window.open("", "_blank", "width=420,height=360"); if (!w) return; w.document.open(); w.document.write(html); w.document.close(); };
const LABEL_CSS = `@page{size:58mm 40mm;margin:2mm}body{font-family:Arial,sans-serif;margin:0;width:54mm}section{page-break-after:always;padding-bottom:2mm;display:flex;gap:2mm}
.qr{width:22mm;height:22mm;flex:none}.txt{flex:1;min-width:0}.no{font-size:17px;font-weight:800;letter-spacing:.3px;word-break:break-all}.row{font-size:10px;margin-top:2px}.b{font-weight:700}.small{font-size:8.5px;color:#444;margin-top:3px}`;

/** Label kecil 58mm untuk potongan sampel: QR nomor roll anak, pelanggan, panjang, produk, SO. */
export async function printSampleLabel(r) {
  const qr = await qrFor(r.child_roll_no);
  openPrint(`<!doctype html><html lang="id"><head><meta charset="utf-8"><title>Label ${esc(r.child_roll_no)}</title><style>${LABEL_CSS}</style></head>
<body><section>${qr ? `<img class="qr" src="${qr}" alt="QR ${esc(r.child_roll_no)}">` : ""}<div class="txt"><div class="no">${esc(r.child_roll_no)}</div>
<div class="row b">${esc(r.customer_name)}</div>
<div class="row">${esc(r.product_name)} · ${esc(r.sku)}</div>
<div class="row"><span class="b">${esc(r.length)} ${esc(r.unit)}</span> · dari ${esc(r.cut_roll_no)}</div>
<div class="small">${esc(r.number)} · ${esc(r.sales_order_number || "")} · ${new Date().toLocaleDateString("id-ID")}</div></div></section>
<script>window.onload=function(){window.print();}</script></body></html>`);
}

/** Label roll (58×40 mm per roll): QR nomor roll, produk, panjang, grade, lot. Dipakai inbound & cetak ulang. */
export async function printInboundRollLabels(task, rolls) {
  const qrs = await Promise.all((rolls || []).map((r) => qrFor(r.roll_no)));
  const pages = (rolls || []).map((r, i) => `<section>${qrs[i] ? `<img class="qr" src="${qrs[i]}" alt="QR ${esc(r.roll_no)}">` : ""}<div class="txt"><div class="no">${esc(r.roll_no)}</div>
<div class="row b">${esc(task.product_name || task.product_id)}</div>
<div class="row"><span class="b">${esc(r.length)} ${esc(r.unit || task.unit || "")}</span> · Grade ${esc(r.grade || "A")}</div>
<div class="row">Lot ${esc(r.lot || "-")}${r.dye_lot ? ` · Dye ${esc(r.dye_lot)}` : ""}</div>
${r.supplier_roll_no || r.rfid_epc ? `<div class="small">${r.supplier_roll_no ? `Sup ${esc(r.supplier_roll_no)}${r.supplier_sku ? ` · ${esc(r.supplier_sku)}` : ""}` : ""}${r.rfid_epc ? ` · EPC ${esc(r.rfid_epc)}` : ""}</div>` : ""}
<div class="small">${esc(task.po_number || "")} · ${esc(task.warehouse_name || task.warehouse_id || "")} · ${new Date().toLocaleDateString("id-ID")}</div></div></section>`).join("");
  openPrint(`<!doctype html><html lang="id"><head><meta charset="utf-8"><title>Label roll</title><style>${LABEL_CSS}</style></head>
<body>${pages}<script>window.onload=function(){window.print();}</script></body></html>`);
}

export async function printRollLabelsBulk(rolls, ctx = {}) {
  const groups = new Map();
  (rolls || []).forEach((r) => { const k = r.product_name || r.product_id || ""; if (!groups.has(k)) groups.set(k, []); groups.get(k).push(r); });
  for (const [name, rs] of groups) await printInboundRollLabels({ product_name: name, po_number: ctx.po_number, warehouse_id: rs[0]?.warehouse_id }, rs);
}

/** Cetak ulang label QR satu roll (label rusak/hilang) dari dokumen roll apa adanya. */
export function reprintRollLabel(roll, productName) {
  return printInboundRollLabels(
    { product_name: productName || roll.product_name || roll.product_id, unit: roll.unit, warehouse_id: roll.warehouse_id },
    [{ roll_no: roll.roll_no, length: roll.length_remaining ?? roll.length, unit: roll.unit, grade: roll.grade, lot: roll.lot || roll.supplier_lot, dye_lot: roll.dye_lot,
       supplier_roll_no: roll.supplier_roll_no, supplier_sku: roll.supplier_sku, rfid_epc: roll.rfid_epc }]);
}
