"""KN-A13 (audit 2026-09-21) — SATU sumber toleransi numerik.

Sebelum ini tiap modul mendefinisikan `EPS` sendiri (0.01 · 0.005 · 1e-6) dan dua modul yang
harus sepakat memakai ambang berbeda (perencana reservasi 0,01 vs pemotong roll 0,001).
Pakai konstanta di sini; jangan menulis angka ajaib baru.
"""
MONEY_EPS = 0.01     # rupiah: selisih ≤ 1 sen dianggap nol
QTY_EPS = 0.001      # kuantitas/panjang satuan dasar (meter/yard/kg)
RATE_EPS = 1e-6      # rasio / persen
