import ast
import json
from pathlib import Path


SRC = Path("/tmp/kn-audit/backend/services/product_template_service.py")
OUT = Path("/app/test_reports/isolated_normalize_axes_result.json")


def load_functions_from_source(path: Path):
    tree = ast.parse(path.read_text())
    wanted = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in {"_slug", "_normalize_axes"}:
            wanted[node.name] = node
    module = ast.Module(body=[wanted["_slug"], wanted["_normalize_axes"]], type_ignores=[])
    code = compile(module, filename=str(path), mode="exec")
    ns = {}
    exec(code, {"re": __import__("re"), "List": list, "Dict": dict, "Any": object}, ns)
    return ns["_normalize_axes"]


def main():
    normalize_axes = load_functions_from_source(SRC)

    ensure_parent_default_axes = [
        {"key": "color", "label": "Warna", "values": []},
        {"key": "grade", "label": "Grade", "values": ["A", "B", "C"]},
    ]
    normalized_default = normalize_axes(ensure_parent_default_axes)

    ui_color_axis = [
        {
            "key": "color",
            "label": "Warna",
            "options": [
                {"label": "Merah", "code": "MRH", "value": "MRH", "hex": "#FF0000"},
                {"label": "Biru", "code": "BRU", "value": "BRU", "hex": "#0000FF"},
            ],
        }
    ]
    normalized_ui = normalize_axes(ui_color_axis)

    result = {
        "source": str(SRC),
        "probe_type": "isolated-pure-function",
        "cases": {
            "ensure_parent_default_axes_values_shape": {
                "input": ensure_parent_default_axes,
                "output": normalized_default,
                "output_is_empty": normalized_default == [],
                "finding": "values-based default axes are discarded by _normalize_axes",
            },
            "ui_color_hex_preservation": {
                "input": ui_color_axis,
                "output": normalized_ui,
                "output_first_option_keys": sorted(list((normalized_ui[0]["options"][0] if normalized_ui else {}).keys())),
                "hex_present_after_normalize": "hex" in ((normalized_ui[0]["options"][0]) if normalized_ui else {}),
                "finding": "hex metadata is dropped by _normalize_axes",
            },
        },
    }

    OUT.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
