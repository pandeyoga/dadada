"""Pemisahan tugas (maker-checker) di API — audit PK-07.

Sebelumnya UI menonaktifkan tombol "Setujui" milik sendiri, tetapi API tidak membandingkan
pembuat dengan pemberi persetujuan/pembayar, sehingga satu akun bisa menjalankan rantai
PO → persetujuan → GRN → tagihan → persetujuan → bayar sendirian.

Aturan di sini dipakai di lapisan router/engine yang menerima aktor nyata (bukan seed):
  * pembuat dokumen ≠ pemberi persetujuan;
  * pemberi persetujuan ≠ pembayar;
  * pemohon ≠ pencair pengajuannya sendiri.

PENGECUALIAN (satu-satunya, mengikuti pola `SENIOR_ROLES` di procurement_router): `super_admin`.
Super Admin adalah akun darurat/operator platform; tenant yang hanya punya satu orang tetap bisa
bekerja lewat akun itu, dan setiap tindakannya tetap tercatat di audit log. Peran `owner` TIDAK
dikecualikan: owner yang membuat dokumen harus meminta orang lain (atau super_admin) menyetujuinya.
"""

EXEMPT_ROLES = ("super_admin",)


def _same(a, b) -> bool:
    return bool(a) and bool(b) and str(a).strip().lower() == str(b).strip().lower()


def assert_separate(user: dict, other_email, message: str) -> None:
    """Lempar ValueError(message) bila `user` adalah orang yang sama dengan `other_email`."""
    if (user or {}).get("role") in EXEMPT_ROLES:
        return
    if _same((user or {}).get("email"), other_email):
        raise ValueError(message)
