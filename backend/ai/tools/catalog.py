"""Memuat semua alat bawaan ke registri (idempoten). Tambahan alat (mis. laporan Task 6) cukup `registry.register(Tool(...))`."""
from ai.tools import read_tools

_loaded = False


def load() -> None:
    global _loaded
    if _loaded:
        return
    read_tools.register_all()
    try:
        from ai import propose_tools
        propose_tools.register_all()
    except ImportError:
        pass
    from ai import report_tool
    report_tool.register_all()
    _loaded = True


load()
