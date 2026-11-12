"""The bundled API index, and which of its endpoints the CLI has commands for.

``data/api_paths.json`` is a compact copy of Cribl's API reference (method,
path, area, one-line summary) produced by ``scripts/update_api_paths.py``. It
backs ``cribl api-spec`` and the coverage test, which uses ``cli_endpoints()``
to catch two kinds of drift:

- a command that calls a path the API does not have (a typo'd or renamed
  endpoint, which only ever returns 404), and
- an API endpoint that silently lost its command.
"""

from __future__ import annotations

import ast
import json
import re
from functools import lru_cache
from pathlib import Path

_PACKAGE = Path(__file__).resolve().parent.parent
_INDEX = _PACKAGE / "data" / "api_paths.json"
_HTTP = {"get", "post", "put", "patch", "delete"}


def normalize(path: str) -> str:
    """Reduce a request path or a reference path to one comparable form.

    Works on path *templates* (``/api/v1/m/{group}/lib/jobs/{id}``): drops the
    query string, the ``/api/v1`` root and the ``/m/{group}`` or ``/w/{node}``
    scoping prefix, and replaces every parameter with ``{}``.
    """
    path = path.split("?")[0]
    path = re.sub(r"^/api/v1", "", path)
    path = re.sub(r"\{[^}]*\}", "{}", path)
    path = re.sub(r"^/(m|w)/\{\}", "", path)
    return "/" + path.strip("/")


@lru_cache(maxsize=1)
def load_index() -> dict:
    return json.loads(_INDEX.read_text())


def load_operations() -> list[dict]:
    """Every documented operation: ``{method, path, tag, summary}``."""
    return load_index()["operations"]


def spec_endpoints() -> set[tuple[str, str]]:
    return {(op["method"], normalize(op["path"])) for op in load_operations()}


# ---------------------------------------------------------------------------
# What the CLI calls
# ---------------------------------------------------------------------------

def _registry_endpoints() -> dict[tuple[str, str], set[str]]:
    from cribl_cli.commands.registry import REGISTRY

    found: dict[tuple[str, str], set[str]] = {}
    for reg in REGISTRY:
        ep = reg.endpoint
        bases = {
            "global": [ep.path],
            # Group resources can also be addressed inside a pack (-P/--pack).
            "group": [ep.path, f"p/{{}}/{ep.path}"],
            "search": [f"search/{ep.path}"],
            "searchgroup": [ep.path],
            "lake": [f"products/lake/lakes/{{}}/{ep.path}"],
        }[ep.scope]
        for base in bases:
            one = base if ep.singleton else f"{base}/{{}}"
            for op in reg.operations:
                method, path = {
                    "list": ("GET", base), "get": ("GET", one), "create": ("POST", base),
                    "update": ("PATCH", one), "delete": ("DELETE", one),
                }[op]
                found.setdefault((method, normalize("/" + path)), set()).add(f"registry:{reg.name}")
    return found


def _render(node: ast.AST, helpers: dict[str, str]) -> str | None:
    """Rebuild the URL template a call is made with; parameters become ``{}``."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        out = ""
        for part in node.values:
            if isinstance(part, ast.Constant):
                out += str(part.value)
                continue
            inner = part.value  # type: ignore[attr-defined]
            if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name) and inner.func.id in helpers:
                out += helpers[inner.func.id]
            elif isinstance(inner, ast.Name) and inner.id in helpers:
                out += helpers[inner.id]
            else:
                out += "{}"
        return out
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in helpers:
        return helpers[node.func.id]
    if isinstance(node, ast.Name) and node.id in helpers:
        return helpers[node.id]
    return None


def _source_endpoints() -> dict[tuple[str, str], set[str]]:
    """Endpoints called by hand-written code, found by reading the source.

    Looks for ``client.get/post/put/patch/delete(<url>, ...)`` where the URL is
    a literal, an f-string, or built from a module-level constant or a small
    helper that returns one (``_base(group)``). ``client.request`` is skipped:
    it is the generic passthrough behind ``cribl api``.
    """
    found: dict[tuple[str, str], set[str]] = {}
    for file in sorted(_PACKAGE.rglob("*.py")):
        tree = ast.parse(file.read_text())
        helpers: dict[str, str] = {}
        multi: dict[str, set[str]] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                value = _render(node.value, helpers)
                if value and value.startswith("/"):
                    helpers[node.targets[0].id] = value
        for _ in range(2):  # a helper may be defined in terms of another
            for node in ast.walk(tree):
                if not isinstance(node, ast.FunctionDef):
                    continue
                returns = {
                    _render(r.value, helpers)
                    for r in ast.walk(node) if isinstance(r, ast.Return) and r.value is not None
                }
                returns.discard(None)
                if returns and all(r.startswith("/") for r in returns):  # type: ignore[union-attr]
                    if len(returns) == 1:
                        helpers[node.name] = next(iter(returns))  # type: ignore[assignment]
                    else:
                        multi[node.name] = returns  # type: ignore[assignment]

        rel = file.relative_to(_PACKAGE)
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr in _HTTP and node.args):
                continue
            arg = node.args[0]
            templates: list[str | None] = []
            if isinstance(arg, ast.JoinedStr):
                used = [
                    p.value.func.id for p in arg.values  # type: ignore[attr-defined]
                    if isinstance(p, ast.FormattedValue) and isinstance(p.value, ast.Call)
                    and isinstance(p.value.func, ast.Name)
                ]
                branching = [name for name in used if name in multi]
                if branching:
                    templates = [_render(arg, {**helpers, branching[0]: alt}) for alt in multi[branching[0]]]
            if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id in multi:
                templates = list(multi[arg.func.id])
            if not templates:
                templates = [_render(arg, helpers)]
            for template in templates:
                if template and template.startswith("/api/v1"):
                    key = (node.func.attr.upper(), normalize(template))
                    found.setdefault(key, set()).add(f"{rel}:{node.lineno}")
    return found


@lru_cache(maxsize=1)
def cli_endpoints() -> dict[tuple[str, str], frozenset[str]]:
    """``{(METHOD, normalized path): where it is called from}`` for the whole CLI."""
    merged: dict[tuple[str, str], set[str]] = {}
    for source in (_registry_endpoints(), _source_endpoints()):
        for key, where in source.items():
            merged.setdefault(key, set()).update(where)
    return {key: frozenset(where) for key, where in merged.items()}


def coverage() -> dict:
    """Compare the CLI against the index.

    Returns ``covered`` and ``missing`` (documented endpoints with / without a
    command) and ``unknown`` (endpoints the CLI calls that are not documented).
    """
    spec = spec_endpoints()
    cli = cli_endpoints()
    return {
        "covered": sorted(k for k in spec if k in cli),
        "missing": sorted(k for k in spec if k not in cli),
        "unknown": {k: sorted(v) for k, v in sorted(cli.items()) if k not in spec},
    }
