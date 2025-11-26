"""
Simple static checks to catch flaky or weak regression tests.

Usage:
    python -m dev_tools.check_test_quality tests/llm/test_xxx.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


class TestSmellVisitor(ast.NodeVisitor):
    """Lightweight AST visitor that records testing anti-patterns."""

    def __init__(self) -> None:
        self.issues: list[str] = []
        self.in_test_function: bool = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        prev = self.in_test_function
        self.in_test_function = node.name.startswith("test_")
        self.generic_visit(node)
        self.in_test_function = prev

    def visit_Call(self, node: ast.Call) -> None:
        # time.sleep in tests
        if isinstance(node.func, ast.Attribute):
            if (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "time"
                and node.func.attr == "sleep"
            ):
                self.issues.append(
                    f"{node.lineno}:{node.col_offset}: use of time.sleep() in tests"
                )

        # direct open on project root (rough heuristic)
        if isinstance(node.func, ast.Name) and node.func.id == "open":
            self.issues.append(
                f"{node.lineno}:{node.col_offset}: open() used directly in test; consider tmp_path or fixtures"
            )

        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        # having asserts is good, so no issue here
        self.generic_visit(node)


def check_file(path: Path) -> list[str]:
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(path))
    visitor = TestSmellVisitor()
    visitor.visit(tree)

    # very simple heuristic: no assert at all
    if "assert " not in src and ".assert" not in src:
        visitor.issues.append("0:0: file contains no explicit asserts")

    return visitor.issues


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: python -m dev_tools.check_test_quality tests/llm/test_xxx.py")
        return 1

    root = Path.cwd()
    exit_code = 0

    for arg in argv[1:]:
        path = (root / arg).resolve()
        if not path.is_file():
            print(f"[WARN] not a file: {path}")
            continue

        issues = check_file(path)
        if not issues:
            print(f"[OK] {arg}")
        else:
            exit_code = 1
            print(f"[NG] {arg}")
            for msg in issues:
                print("  -", msg)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

