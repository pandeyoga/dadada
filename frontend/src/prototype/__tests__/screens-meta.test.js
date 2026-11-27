import screens from "../screens.json";

const names = require("../../../scripts/screen-names");

describe("screens.json desc", () => {
  test.each(screens.map((s) => [s.id, s]))("%s punya desc 20-110 karakter tanpa Ningrat", (id, s) => {
    expect(typeof s.desc).toBe("string");
    expect(s.desc.length).toBeGreaterThanOrEqual(20);
    expect(s.desc.length).toBeLessThanOrEqual(110);
    expect(s.desc).not.toMatch(/ningrat/i);
  });
});

describe("screen-names", () => {
  test("nama berkas unik, cocok pola, 59 entri", () => {
    expect(screens).toHaveLength(59);
    const all = screens.map((s) => names.screenFileName(s));
    all.forEach((n) => expect(n).toMatch(/^[A-Z]\d{2}-[a-z0-9-]+$/));
    expect(new Set(all).size).toBe(59);
  });

  test("P10 dan W29 berbeda walau rute sama", () => {
    const p = names.screenFileName({ id: "P10", title: "Ajak teman" });
    const w = names.screenFileName({ id: "W29", title: "Ajak teman" });
    expect(p).toBe("P10-ajak-teman");
    expect(w).toBe("W29-ajak-teman");
  });

  test("slugify", () => {
    expect(names.slugify("Pembatalan & refund")).toBe("pembatalan-dan-refund");
    expect(names.slugify("Bayar & Isi Ulang")).toBe("bayar-dan-isi-ulang");
    expect(names.slugify("Café · Ünïcode!")).toBe("cafe-unicode");
    const long = names.slugify("Satu dua tiga empat lima enam tujuh delapan sembilan sepuluh");
    expect(long.length).toBeLessThanOrEqual(40);
    expect(long.endsWith("-")).toBe(false);
    expect(names.screenFileName({ id: "W18", title: "Pasar warga" })).toBe("W18-pasar-warga");
  });

  test("id2 dan folderFor", () => {
    expect(names.id2("W18")).toBe("W18");
    expect(names.id2("U1")).toBe("U01");
    expect(names.id2("P10")).toBe("P10");
    const map = { U1: "01-demo", P3: "02-pembeli", T1: "03-serah-terima", W9: "04-warga", S2: "05-satpam", K4: "06-pengelola", M5: "07-mitra" };
    Object.entries(map).forEach(([id, f]) => expect(names.folderFor(id)).toBe(f));
  });
});
