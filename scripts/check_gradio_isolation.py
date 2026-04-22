#!/usr/bin/env python3
"""
check_gradio_isolation.py

Issue #72: Gradio UI <-> Core separation verification.

Detects gradio dependencies in src/nexuscore/ Core modules.
UI layer (gradio_app/, ui/, webapp/) is excluded.
Core layer (agents/, core/, llm/, orchestrator/, etc.) gradio imports
are reported as architecture violations.

Usage:
    python scripts/check_gradio_isolation.py [--strict] [--json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

UI_DIRS = {
    "gradio_app",
    "ui",
    "webapp",
}

GRADIO_PATTERNS = [
    re.compile(r"^\s*import gradio", re.MULTILINE),
    re.compile(r"^\s*from gradio", re.MULTILINE),
]


def find_violations(src_root: Path) -> list[dict]:
    violations = []
    for py_file in sorted(src_root.rglob("*.py")):
        rel = py_file.relative_to(src_root)
        parts = rel.parts
        if len(parts) > 1 and parts[0] in UI_DIRS:
            continue
        if py_file.name == "__init__.py":
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            for pattern in GRADIO_PATTERNS:
                if pattern.search(line):
                    is_lazy = _is_lazy_import(lines, i - 1)
                    violations.append({
                        "file": str(rel),
                        "line": i,
                        "content": line.strip(),
                        "lazy": is_lazy,
                        "severity": "warning" if is_lazy else "error",
                    })
    return violations


def _is_lazy_import(lines: list[str], line_idx: int) -> bool:
    for j in range(max(0, line_idx - 5), line_idx):
        stripped = lines[j].strip()
        if stripped.startswith("try:"):
            return True
    return False


def main():
    parser = argparse.ArgumentParser(description="Check Gradio isolation in Core modules")
    parser.add_argument("--strict", action="store_true", help="Treat lazy imports as errors")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--src-dir", default="src/nexuscore", help="Source directory")
    args = parser.parse_args()

    src_root = Path(args.src_dir)
    if not src_root.exists():
        print(f"Error: {args.src_dir} not found")
        sys.exit(1)

    violations = find_violations(src_root)

    if args.json:
        print(json.dumps(violations, indent=2, ensure_ascii=False))
    else:
        errors = [v for v in violations if v["severity"] == "error"]
        warnings = [v for v in violations if v["severity"] == "warning"]

        if args.strict:
            errors.extend(warnings)
            warnings = []

        if errors:
            print(f"Found {len(errors)} violation(s) in Core modules:")
            for v in errors:
                print(f"  {v['file']}:{v['line']} - {v['content']}")

        if warnings:
            print(f"Found {len(warnings)} lazy import(s) (allowed, use --strict to fail):")
            for v in warnings:
                print(f"  {v['file']}:{v['line']} - {v['content']}")

        if not errors and not warnings:
            print("No gradio dependencies found in Core modules")

        if errors or (args.strict and warnings):
            sys.exit(1)


if __name__ == "__main__":
    main()
