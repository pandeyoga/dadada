"""Satu event loop bersama untuk tes yang memanggil fungsi async backend LANGSUNG (tanpa server).

Klien Motor global (`db.py`) terikat pada event loop pertama yang memakainya; `asyncio.run()` membuat loop baru tiap panggilan,
jadi dua tes yang sama-sama memakai `asyncio.run` di satu proses bertabrakan ("attached to a different loop"), bergantung urutan.
Semua tes seperti itu wajib memakai `aio.run(coro)` agar memakai SATU loop.
"""
import asyncio

_LOOP = None


def run(coro):
    global _LOOP
    if _LOOP is None or _LOOP.is_closed():
        _LOOP = asyncio.new_event_loop()
    return _LOOP.run_until_complete(coro)
