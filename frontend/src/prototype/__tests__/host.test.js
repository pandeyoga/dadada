import { isPrototypeHost } from "@/prototype/lib/host";

test.each(["localhost", "127.0.0.1", "", "demo.estora.id", "trial.estora.id"])("%s diizinkan", (h) => expect(isPrototypeHost(h)).toBe(true));
test.each(["hl5.estora.id", "estora.id", "app.demo-estora.com", "evil-demo.estora.id"])("%s ditolak", (h) => expect(isPrototypeHost(h)).toBe(false));
