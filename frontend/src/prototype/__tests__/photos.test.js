import fs from "fs";
import path from "path";
import photos from "../lib/photos.json";
import { buildInitialState } from "../services/initialState";

const PUBLIC = path.resolve(__dirname, "../../../public");

const REQUIRED_KEYS = [
  "market/nasi-kuning", "market/brownies", "market/keripik", "market/kopi", "market/kopi-aren", "market/cabai",
  "market/pot", "market/sprei", "market/telur", "market/rajut", "market/beras", "market/laundry",
  "progress/lahan", "progress/pondasi", "progress/dinding", "progress/kusen", "progress/atap", "progress/plester",
  "unit/tipe-30", "unit/tipe-36", "unit/tipe-45",
  "promo/pr-1", "promo/pr-2", "promo/pr-3",
  "cctv/teras-depan", "cctv/taman-belakang", "cctv/gerbang-utama", "cctv/pos-satpam", "cctv/taman-bermain",
  "cctv/jalan-blok", "cctv/lapangan", "cctv/gerbang-belakang",
  "facility/lapangan", "facility/musala", "facility/balai", "facility/taman",
  "ticket/bocor-dapur",
];

function collectImgKeys(node, out) {
  if (Array.isArray(node)) { node.forEach((n) => collectImgKeys(n, out)); return out; }
  if (node && typeof node === "object") {
    Object.entries(node).forEach(([k, v]) => {
      if (k === "img" && typeof v === "string") out.add(v);
      else if (k === "photos" && Array.isArray(v)) v.forEach((p) => typeof p === "string" && out.add(p));
      else collectImgKeys(v, out);
    });
  }
  return out;
}

describe("manifest foto", () => {
  test("memuat tepat 37 kunci yang dibutuhkan", () => {
    expect(Object.keys(photos).sort()).toEqual([...REQUIRED_KEYS].sort());
    expect(REQUIRED_KEYS).toHaveLength(37);
  });

  test("tiap entri valid, berkas ada dan <= 150 KB", () => {
    Object.entries(photos).forEach(([key, p]) => {
      expect(p.src).toMatch(/^\/rdg\/foto\/[a-z]+\/[a-z0-9-]+\.jpg$/);
      const file = path.join(PUBLIC, p.src);
      expect(fs.existsSync(file)).toBe(true);
      expect(fs.statSync(file).size).toBeLessThanOrEqual(150 * 1024);
      expect(typeof p.alt).toBe("string");
      expect(p.alt.trim().length).toBeGreaterThan(0);
      expect(typeof p.illustrative).toBe("boolean");
      expect(p.credit.photographer.length).toBeGreaterThan(0);
      expect(p.credit.url.startsWith("https://www.pexels.com/photo/")).toBe(true);
      expect(key.length).toBeGreaterThan(0);
    });
  });

  test("flag illustrative sesuai kategori", () => {
    Object.entries(photos).forEach(([key, p]) => {
      const cat = key.split("/")[0];
      expect(p.illustrative).toBe(!["market", "cctv"].includes(cat));
    });
  });

  test("total ukuran <= 6 MB", () => {
    const total = Object.values(photos).reduce((s, p) => s + fs.statSync(path.join(PUBLIC, p.src)).size, 0);
    expect(total).toBeLessThanOrEqual(6 * 1024 * 1024);
  });

  test("setiap kunci img di fixture ada di manifest", () => {
    const keys = [...collectImgKeys(buildInitialState(Date.UTC(2026, 10, 25, 3)), new Set())];
    expect(keys.length).toBeGreaterThan(10);
    keys.forEach((k) => expect(Object.keys(photos)).toContain(k));
  });
});
