"""FakeClaude — skrip respons untuk pengujian (tanpa panggilan API nyata)."""


class FakeClaude:
    def __init__(self, script: list):
        self.script = list(script)
        self.calls: list = []

    async def turn(self, *, model, system, messages, tools, effort, max_tokens, on_text, context,
                   output_format=None) -> dict:
        self.calls.append({"model": model, "system": system, "messages": messages, "tools": tools,
                           "effort": effort, "max_tokens": max_tokens, "context": context,
                           "output_format": output_format})
        if not self.script:
            raise AssertionError("FakeClaude: skrip habis")
        resp = self.script.pop(0)
        if isinstance(resp, Exception):
            raise resp
        resp = {"stop_reason": "end_turn", "stop_details": None, "usage": {}, "model": model, **resp}
        if on_text:
            for b in resp["content"]:
                if b.get("type") == "text":
                    await on_text(b["text"])
        return resp
