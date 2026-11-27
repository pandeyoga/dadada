#!/usr/bin/env python3
"""Optimasi PNG tangkapan layar (lossless) dan perkecil halaman penuh ponsel ke lebar 488 px (~@1,25)
agar total docs/prototype/screens < 40 MB. Layar pertama dan dasbor pengelola tidak diubah ukurannya.
Pakai: python3 frontend/scripts/optimize-screens.py [folder]"""
import glob, os, sys
from PIL import Image

root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "../../docs/prototype/screens")
W = 488
for f in sorted(glob.glob(os.path.join(root, "*", "*.png"))):
    name = os.path.basename(f)
    im = Image.open(f)
    im.load()
    full_mobile = not name.startswith("00-") and not name.endswith("--layar.png") and "06-pengelola" not in f
    if full_mobile and im.width > W:
        im = im.resize((W, round(im.height * W / im.width)), Image.LANCZOS)
    im.save(f, optimize=True)
