import sys
from PIL import Image, ImageDraw
shots, out = sys.argv[1], sys.argv[2]
def rounded(im, r):
    im = im.convert("RGBA")
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, im.size[0]-1, im.size[1]-1], r, fill=255)
    im.putalpha(m); return im
# phone screens (600 wide originals)
for n in ["02","03","04","05","07","08","09"]:
    im = Image.open(f"{shots}/keluarga_ningrat/ios_{n}.png")
    im = im.resize((480, int(im.size[1]*480/im.size[0])))
    rounded(im, 36).save(f"{out}/app_{n}.png")
crops = {
  # name: (file, box) in original pixels
  "mitra_sim":     ("mitra/mitra_04_product.png",  (1760, 1980, 2620, 3620)),
  "mitra_hero":    ("mitra/mitra_04_product.png",  (100, 180, 2632, 1940)),
  "mitra_catalog": ("mitra/mitra_04_product.png",  (100, 4180, 2632, 6560)),
  "mitra_reg":     ("mitra/mitra_02_register.png", (1340, 300, 2540, 2240)),
  "mitra_tools":   ("mitra/mitra_01_landing.png",  (0, 7950, 2732, 9900)),
  "mitra_benefit": ("mitra/mitra_01_landing.png",  (0, 6050, 2732, 7900)),
}
for name, (f, box) in crops.items():
    im = Image.open(f"{shots}/{f}")
    c = im.crop(box)
    w = 1400 if c.size[0] > 1400 else c.size[0]
    c = c.resize((w, int(c.size[1]*w/c.size[0])))
    rounded(c, 28).save(f"{out}/{name}.png")
    print(name, c.size)
