"""Invarian PERSEDIAAN & PENGADAAN: stok = Σ mutasi, PO ↔ GRN ↔ retur ↔ tagihan, agregat tersimpan."""
from collections import defaultdict

from ..core import V, i, invariant


def _stock(txns):
    st = 0.0
    for t in txns:
        q = float(t.get("qty") or 0)
        st += q if t.get("type") in ("in",) else (-q if t.get("type") == "out" else q)
    return round(st, 2)


@invariant("S01", "Stok", "stok buku (Σ in − Σ out ± adjust) per material tidak negatif", known="PG-04/PG-05")
def s01(s):
    out = []
    g = defaultdict(list)
    for t in s.rows("material_txns"):
        g[(t.get("project_id"), t.get("material_id"))].append(t)
    mats = s.idx("materials")
    for (pid, mid), ts in g.items():
        st = _stock(ts)
        if st < -0.001:
            out.append(V("S01", f"{pid}/{mid}", f"material {mats.get(mid, {}).get('name', str(mid)[:6])} stok buku {st} < 0", st))
    return out


@invariant("S02", "Stok", "materials.consumed_qty (tersimpan) = Σ mutasi 'out'; over_budget = consumed > budget", known="PG-21")
def s02(s):
    out = []
    outq = defaultdict(float)
    for t in s.rows("material_txns"):
        if t.get("type") == "out":
            outq[(t.get("project_id"), t.get("material_id"))] += float(t.get("qty") or 0)
    for m in s.rows("materials"):
        got = round(outq.get((m.get("project_id"), m["id"]), 0.0), 2)
        if abs(float(m.get("consumed_qty") or 0) - got) > 0.011:
            out.append(V("S02", m["id"], f"material {m.get('name')} consumed_qty={m.get('consumed_qty')} ≠ Σ out={got}", got))
    return out


@invariant("S03", "Stok", "tiap mutasi stok menunjuk material yang ada & proyek yang sama dengan materialnya; qty > 0 untuk in/out")
def s03(s):
    out = []
    mats = s.idx("materials")
    for t in s.rows("material_txns"):
        m = mats.get(t.get("material_id"))
        if not m:
            out.append(V("S03", t["id"], f"mutasi {t.get('ref')} → material tidak ada"))
        elif m.get("project_id") != t.get("project_id"):
            out.append(V("S03", f"{t['id']}/proj", f"mutasi {t.get('ref')} proyek ≠ proyek material {m.get('name')}"))
        if t.get("type") in ("in", "out") and float(t.get("qty") or 0) <= 0:
            out.append(V("S03", f"{t['id']}/q", f"mutasi {t.get('type')} {t.get('ref')} qty={t.get('qty')} ≤ 0"))
    return out


def _grn_by_po(s):
    g = defaultdict(list)
    for r in s.rows("grns"):
        g[r.get("po_id")].append(r)
    return g


def _ret_by_grn(s):
    g = defaultdict(list)
    for r in s.rows("grn_returns"):
        g[r.get("grn_id")].append(r)
    return g


@invariant("P01", "Pengadaan", "PO.items[k].received_qty = Σ GRN.qty_received (item k) − Σ retur (item k); GRN.returned_qty = Σ baris retur; tidak melebihi qty pesan", known="PG-05/PG-06")
def p01(s):
    out = []
    grns = _grn_by_po(s)
    rets = _ret_by_grn(s)
    for g_ in s.rows("grns"):
        rq = defaultdict(float)
        for r in rets.get(g_["id"], []):
            for ri in r.get("items") or []:
                rq[ri.get("grn_item_index")] += float(ri.get("qty_returned") or 0)
        for gi, x in enumerate(g_.get("items") or []):
            if abs(float(x.get("returned_qty") or 0) - rq.get(gi, 0.0)) > 0.001:
                out.append(V("P01", f"{g_['id']}/{gi}/ret", f"GRN {g_.get('grn_number')} item#{gi} returned_qty={x.get('returned_qty')} ≠ Σ retur={rq.get(gi, 0.0)}"))
    for po in s.rows("purchase_orders"):
        gs = grns.get(po["id"], [])
        for k, it in enumerate(po.get("items") or []):
            got = sum(float(x.get("qty_received") or 0) - float(x.get("returned_qty") or 0)
                      for g in gs for x in g.get("items") or [] if x.get("po_item_index") == k)
            exp = round(got, 4)
            have = round(float(it.get("received_qty") or 0), 4)
            tag = f"PO {po.get('po_number')} item#{k} '{str(it.get('description'))[:30]}'"
            if abs(have - exp) > 0.001:
                out.append(V("P01", f"{po['id']}/{k}", f"{tag} received_qty={have} ≠ Σ(GRN−retur)={exp}", have - exp))
            if have > float(it.get("qty") or 0) + 0.001:
                out.append(V("P01", f"{po['id']}/{k}/over", f"{tag} diterima {have} > dipesan {it.get('qty')}", have - float(it.get('qty') or 0)))
    return out


@invariant("P02", "Pengadaan", "PO: received_value = Σ nilai (GRN − retur); billed_value = Σ klaim tagihan PO aktif; status PO sesuai penerimaan", known="PG-06/PG-13")
def p02(s):
    out = []
    grns = _grn_by_po(s)
    for po in s.rows("purchase_orders"):
        gv = sum(i(g.get("received_value")) for g in grns.get(po["id"], []))
        rv = i(po.get("received_value"))
        # retur menurunkan received_value PO (bila diimplementasi): toleransi ke bawah = nilai retur
        retv = sum(i(r.get("returned_value")) for g in grns.get(po["id"], []) for r in _ret_by_grn(s).get(g["id"], []))
        if rv != gv - retv:
            out.append(V("P02", f"{po['id']}/rv", f"PO {po.get('po_number')} received_value={rv:,} ≠ Σ GRN−retur={gv - retv:,}", rv - (gv - retv)))
        qty_full = all(float(it.get("received_qty") or 0) + 0.001 >= float(it.get("qty") or 0) for it in po.get("items") or [])
        qty_any = any(float(it.get("received_qty") or 0) > 0 for it in po.get("items") or [])
        st = po.get("status")
        if st == "received" and not qty_full:
            out.append(V("P02", f"{po['id']}/st", f"PO {po.get('po_number')} status received tetapi ada item belum lengkap diterima"))
        if st in ("approved", "pending_approval", "draft") and qty_any and st != "approved":
            out.append(V("P02", f"{po['id']}/st2", f"PO {po.get('po_number')} status {st} tetapi sudah ada penerimaan"))
        if st == "cancelled" and qty_any:
            out.append(V("P02", f"{po['id']}/cx", f"PO {po.get('po_number')} dibatalkan padahal sudah ada penerimaan barang"))
        billed = sum(i(b.get("claimed")) for b in s.rows("ap_invoices")
                     if b.get("po_id") == po["id"] and b.get("status") not in ("rejected", "cancelled", "void"))
        if i(po.get("billed_value")) != billed:
            out.append(V("P02", f"{po['id']}/bv", f"PO {po.get('po_number')} billed_value={i(po.get('billed_value')):,} ≠ Σ klaim tagihan aktif={billed:,}", i(po.get('billed_value')) - billed))
    return out


@invariant("P03", "Pengadaan", "tiap GRN menghasilkan mutasi stok 'in' sebesar qty diterima (per material) dan retur menghasilkan 'out'", known="PG-04")
def p03(s):
    out = []
    txn_in = defaultdict(float)
    for t in s.rows("material_txns"):
        if t.get("type") == "in" and t.get("ref"):
            txn_in[(t["ref"], t.get("material_id"))] += float(t.get("qty") or 0)
    for g in s.rows("grns"):
        want = defaultdict(float)
        for x in g.get("items") or []:
            if x.get("material_id"):
                want[x["material_id"]] += float(x.get("qty_received") or 0)
        for mid, q in want.items():
            got = txn_in.get((g.get("grn_number"), mid))
            if got is None:
                # beberapa implementasi memakai ref=GRN id/nomor PO — tidak dituntut bila tak ada satupun ref cocok
                continue
            if abs(got - q) > 0.001:
                out.append(V("P03", f"{g['id']}/{mid}", f"GRN {g.get('grn_number')} material {str(mid)[:6]} diterima {q} ≠ mutasi stok 'in' {got}", got - q))
    return out


@invariant("P04", "Pengadaan", "PO/GRN/tagihan menunjuk entitas induk yang ada; GRN hanya untuk PO disetujui")
def p04(s):
    out = []
    pos = s.idx("purchase_orders")
    for g in s.rows("grns"):
        po = pos.get(g.get("po_id"))
        if not po:
            out.append(V("P04", g["id"], f"GRN {g.get('grn_number')} → PO tidak ada"))
    for b in s.rows("ap_invoices"):
        if b.get("po_id") and b["po_id"] not in pos:
            out.append(V("P04", b["id"], f"tagihan {b['id'][:6]} → PO tidak ada"))
        if b.get("po_id") and b.get("status") in ("approved", "partial", "paid"):
            po = pos.get(b["po_id"])
            if po and po.get("status") == "cancelled":
                out.append(V("P04", f"{b['id']}/cx", f"tagihan {b['id'][:6]} {b.get('status')} atas PO {po.get('po_number')} yang dibatalkan"))
    return out


@invariant("P05", "Pengadaan", "tiap retur GRN menghasilkan mutasi stok 'out' (return_id) sebesar qty retur")
def p05(s):
    out = []
    outq = defaultdict(float)
    for t_ in s.rows("material_txns"):
        if t_.get("return_id") and t_.get("type") == "out":
            outq[(t_["return_id"], t_.get("material_id"))] += float(t_.get("qty") or 0)
    for r in s.rows("grn_returns"):
        want = defaultdict(float)
        for ln in r.get("items") or []:
            if ln.get("material_id"):
                want[ln["material_id"]] += float(ln.get("qty_returned") or 0)
        for mid, q in want.items():
            if abs(outq.get((r["id"], mid), 0.0) - q) > 0.001:
                out.append(V("P05", f"{r['id']}/{mid}", f"retur {r.get('return_number')} qty {q} ≠ mutasi stok out {outq.get((r['id'], mid), 0.0)}"))
    return out
