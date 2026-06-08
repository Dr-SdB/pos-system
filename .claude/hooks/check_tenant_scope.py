#!/usr/bin/env python3
"""
PostToolUse hook — warns when an edited Python file contains a queryset on a
store-scoped model that is not filtered to the current tenant.

Opt out per line:   SomeModel.objects.filter(...)  # noqa: tenant-scope

Exit 1 surfaces the output as a visible warning to Claude Code.
"""
import json
import re
import sys
from pathlib import Path

# Models that must always carry a tenant filter, and the required keyword arg.
SCOPED = {
    "Sale":            "tenant=",
    "Product":         "tenant=",
    "UserProfile":     "tenant=",
    "ProductVariant":  "product__tenant=",
    "StockAdjustment": "product_variant__product__tenant=",
}

# Queryset entry-points that READ from the DB (writes like .create() are excluded).
_READ_OPS = (
    "filter", "get", "exclude", "all", "first", "last",
    "select_for_update", "get_or_create",
)

QS_RE = re.compile(
    r'\b(' + "|".join(re.escape(m) for m in SCOPED) + r')'
    r'\.objects\.'
    r'(?:' + "|".join(_READ_OPS) + r')'
    r'\s*[\(\.]'
)

# Paths to skip — management commands and tests operate cross-tenant by design.
_SKIP_PATTERNS = (
    "migrations" + "/",
    "migrations" + "\\",
    "management/commands",
    "management\\commands",
    "tests.py",
)


def should_skip(path: str) -> bool:
    return any(pat in path for pat in _SKIP_PATTERNS)


def check_file(path: str) -> list[str]:
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return []

    issues = []
    for i, line in enumerate(lines):
        if "# noqa: tenant-scope" in line:
            continue
        m = QS_RE.search(line)
        if not m:
            continue
        model = m.group(1)
        required = SCOPED[model]
        # Check a window of 8 lines for the tenant filter argument.
        window = "\n".join(lines[i : i + 8])
        if required not in window:
            issues.append(
                f"  line {i + 1}: {model}.objects query — "
                f"missing `{required}`  (add filter or `# noqa: tenant-scope`)"
            )
    return issues


def main() -> None:
    payload = json.loads(sys.stdin.read())
    tool = payload.get("tool_name", "")
    inp = payload.get("tool_input", {})

    path = inp.get("file_path", "")
    if tool not in ("Edit", "Write") or not path.endswith(".py"):
        return
    if should_skip(path):
        return

    issues = check_file(path)
    if issues:
        print(
            f"[tenant-scope] {len(issues)} possible unscoped queryset(s) in {path}:"
        )
        for w in issues:
            print(w)
        sys.exit(1)


main()
