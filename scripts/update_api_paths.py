#!/usr/bin/env python3
"""Refresh cribl_cli/data/api_paths.json from a Cribl OpenAPI document.

The CLI ships a compact index of the API (method, path, tag, summary) so that
`cribl api-spec search` can find any endpoint and the coverage test can tell
which ones have a dedicated command. Regenerate it after a Cribl upgrade:

    cribl api GET /static/swagger/openapi.json --raw > /tmp/openapi.json
    python scripts/update_api_paths.py /tmp/openapi.json

Only the public reference (paths and one-line summaries) is kept; nothing from
the environment the document was downloaded from ends up in the index.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

METHODS = ("get", "post", "put", "patch", "delete")
OUT = Path(__file__).resolve().parent.parent / "cribl_cli" / "data" / "api_paths.json"


def build(spec: dict) -> dict:
    ops = []
    for path, item in spec.get("paths", {}).items():
        for method, op in item.items():
            if method not in METHODS or not isinstance(op, dict):
                continue
            tag = (op.get("tags") or [""])[0]
            # A few tags in the document are whole sentences; keep them short.
            tag = tag if len(tag) <= 40 and " " not in tag.strip() else tag.split()[0] if tag else ""
            summary = " ".join(str(op.get("summary") or op.get("description") or "").split())
            ops.append({"method": method.upper(), "path": path, "tag": tag, "summary": summary[:140]})
    ops.sort(key=lambda o: (o["path"], o["method"]))
    return {"version": spec.get("info", {}).get("version", ""), "operations": ops}


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    index = build(json.loads(Path(sys.argv[1]).read_text()))
    OUT.write_text(json.dumps(index, indent=0, separators=(",", ":")) + "\n")
    print(f"wrote {len(index['operations'])} operations (API {index['version']}) to {OUT}")


if __name__ == "__main__":
    main()
