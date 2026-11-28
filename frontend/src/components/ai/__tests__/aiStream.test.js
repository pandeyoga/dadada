import { createSseParser } from "../aiStream";

describe("createSseParser", () => {
  test("mengurai potongan yang terpotong di tengah event", () => {
    const got = [];
    const p = createSseParser((e) => got.push(e));
    const full = 'data: {"type":"step_started","id":"1"}\n\ndata: {"type":"text_delta","text":"Halo"}\n\n';
    // potong di tengah JSON, lalu di tengah pemisah event
    p.push(full.slice(0, 20));
    expect(got).toHaveLength(0);
    p.push(full.slice(20, 66));
    p.push(full.slice(66));
    expect(got).toEqual([
      { type: "step_started", id: "1" },
      { type: "text_delta", text: "Halo" },
    ]);
  });

  test("event rusak diabaikan dan CRLF didukung", () => {
    const got = [];
    const p = createSseParser((e) => got.push(e));
    p.push('data: {rusak\r\n\r\ndata: {"type":"done"}\r\n\r\n');
    expect(got).toEqual([{ type: "done" }]);
  });
});
