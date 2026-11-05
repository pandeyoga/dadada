"""Validasi wajar komponen biaya kontrak (audit KT-22).

`contracts_engine.set_costs` menerima angka apa pun: potongan Rp 900 jt di atas harga Rp 850 jt
(nett_price jadi negatif), `dp_percent` 150, `plafon_kredit` Rp 99 miliar pada kontrak TUNAI,
atau nilai negatif acak yang diam-diam berarti "kosongkan". Angka-angka ini langsung tercetak di
SPR yang ditandatangani pembeli. Penjagaan di sini sengaja sederhana dan konservatif — hanya
menolak yang JELAS tidak wajar; persetujuan potongan harga (pricing:approve) adalah keputusan
kebijakan pemilik dan tidak diubah di sini.
"""
LABEL = {"bphtb": "BPHTB", "notary_fee": "Biaya notaris / akad", "bank_fee": "Biaya bank",
         "insurance": "Asuransi", "pph_seller": "PPh penjual", "promo_discount": "Potongan harga",
         "plafon_kredit": "Plafon kredit", "dp_percent": "Persentase DP"}
RP_FIELDS = ("bphtb", "notary_fee", "bank_fee", "insurance", "pph_seller", "promo_discount",
             "plafon_kredit")


def _rp(v) -> str:
    return f"Rp {int(v or 0):,}".replace(",", ".")


async def validate(org: str, contract: dict, payload: dict) -> None:
    """Tolak masukan biaya yang tidak wajar (ValueError → HTTP 400)."""
    import contracts_engine as ce
    gross = None
    for k in (*RP_FIELDS, "dp_percent"):
        v = payload.get(k)
        if v is None:
            continue
        if v < 0:
            if v != -1:
                raise ValueError(f"{LABEL[k]}: nilai negatif tidak sah. Untuk menghapus nilai yang "
                                 "sudah diisi gunakan tombol 'Kosongkan' (kembali menjadi 'belum diisi').")
            continue
        if k == "dp_percent":
            if v > 100:
                raise ValueError("Persentase DP harus antara 0 dan 100.")
            continue
        if k == "plafon_kredit" and contract.get("scheme") != "kpr":
            raise ValueError("Plafon kredit bank hanya berlaku untuk kontrak berskema KPR.")
        if gross is None:
            gross = int((await ce.build_breakdown(org, contract)).get("gross_price") or 0)
        if gross > 0 and int(v) > gross:
            raise ValueError(f"{LABEL[k]} {_rp(v)} melebihi harga unit {_rp(gross)} — angka tidak "
                             "wajar, periksa kembali (potongan di atas harga tidak diterima).")
