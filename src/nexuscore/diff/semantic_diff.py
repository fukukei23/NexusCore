from __future__ import annotations

import ast
import difflib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

ChangeKind = Literal["added", "removed", "modified"]


@dataclass
class FunctionChange:
    """関数レベルの変更情報"""

    name: str
    kind: ChangeKind  # added / removed / modified
    signature_before: str | None = None
    signature_after: str | None = None
    doc_before: str | None = None
    doc_after: str | None = None


@dataclass
class BehaviorChangeHint:
    """行レベル diff + 簡易ルールから推定した「振る舞いの変化ヒント」"""

    description: str  # 「例外パスが追加されました」など
    risk_level: Literal["low", "medium", "high"] = "medium"


@dataclass
class SemanticDiffResult:
    """意味的差分の結果"""

    file_path: Path
    functions: list[FunctionChange] = field(default_factory=list)
    behavior_hints: list[BehaviorChangeHint] = field(default_factory=list)
    raw_line_diff_summary: str | None = None  # 数行に要約した line diff

    def to_dict(self) -> dict[str, object]:
        """Run.details に突っ込みやすいように dict 化"""
        return {
            "file_path": str(self.file_path),
            "functions": [
                {
                    "name": f.name,
                    "kind": f.kind,
                    "signature_before": f.signature_before,
                    "signature_after": f.signature_after,
                    "doc_before": f.doc_before,
                    "doc_after": f.doc_after,
                }
                for f in self.functions
            ],
            "behavior_hints": [
                {
                    "description": h.description,
                    "risk_level": h.risk_level,
                }
                for h in self.behavior_hints
            ],
            "raw_line_diff_summary": self.raw_line_diff_summary,
        }


def _extract_functions_from_ast(tree: ast.AST) -> dict[str, dict[str, str | None]]:
    """
    AST から関数情報を抽出する。

    Returns:
        {関数名: {"signature": "...", "doc": "..."}} の辞書
    """
    functions: dict[str, dict[str, str | None]] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # シグネチャを構築
            args = []
            for arg in node.args.args:
                arg_name = arg.arg
                if arg.annotation:
                    args.append(f"{arg_name}: {ast.unparse(arg.annotation)}")
                else:
                    args.append(arg_name)

            signature = f"{node.name}({', '.join(args)})"
            if node.returns:
                signature += f" -> {ast.unparse(node.returns)}"

            # docstring を取得
            doc = ast.get_docstring(node)

            functions[node.name] = {
                "signature": signature,
                "doc": doc,
            }

    return functions


def _build_behavior_hints_from_diff(
    lines_before: list[str], lines_after: list[str]
) -> list[BehaviorChangeHint]:
    """
    行レベル diff から振る舞いの変化ヒントを構築する。

    Args:
        lines_before: Before コードの行リスト
        lines_after: After コードの行リスト

    Returns:
        BehaviorChangeHint のリスト
    """
    hints: list[BehaviorChangeHint] = []

    # unified_diff を取得
    diff_lines = list(
        difflib.unified_diff(
            lines_before,
            lines_after,
            fromfile="before",
            tofile="after",
            lineterm="",
            n=3,  # コンテキスト行数
        )
    )

    # raise 行が増えたかチェック
    added_raises = 0
    removed_raises = 0
    for line in diff_lines:
        if line.startswith("+") and "raise" in line.lower():
            added_raises += 1
        elif line.startswith("-") and "raise" in line.lower():
            removed_raises += 1

    if added_raises > 0:
        hints.append(
            BehaviorChangeHint(
                description=f"例外パスが追加されました（{added_raises}箇所）",
                risk_level="medium",
            )
        )
    if removed_raises > 0:
        hints.append(
            BehaviorChangeHint(
                description=f"例外パスが削除されました（{removed_raises}箇所）",
                risk_level="medium",
            )
        )

    # if 行が増えたかチェック
    added_ifs = sum(
        1 for line in diff_lines if line.startswith("+") and line.strip().startswith("if ")
    )
    removed_ifs = sum(
        1 for line in diff_lines if line.startswith("-") and line.strip().startswith("if ")
    )

    if added_ifs > 0:
        hints.append(
            BehaviorChangeHint(
                description=f"条件分岐が追加されました（{added_ifs}箇所）",
                risk_level="low",
            )
        )
    if removed_ifs > 0:
        hints.append(
            BehaviorChangeHint(
                description=f"条件分岐が削除されました（{removed_ifs}箇所）",
                risk_level="medium",
            )
        )

    # return 行の変化をチェック（簡易版）
    added_returns = sum(
        1 for line in diff_lines if line.startswith("+") and "return" in line.lower()
    )
    removed_returns = sum(
        1 for line in diff_lines if line.startswith("-") and "return" in line.lower()
    )

    if added_returns > removed_returns:
        hints.append(
            BehaviorChangeHint(
                description="戻り値パスが追加されました",
                risk_level="low",
            )
        )
    elif removed_returns > added_returns:
        hints.append(
            BehaviorChangeHint(
                description="戻り値パスが削除されました",
                risk_level="medium",
            )
        )

    # assert 行が増えたかチェック（バリデーション追加の可能性）
    added_asserts = sum(
        1 for line in diff_lines if line.startswith("+") and "assert" in line.lower()
    )
    if added_asserts > 0:
        hints.append(
            BehaviorChangeHint(
                description=f"アサーション（バリデーション）が追加されました（{added_asserts}箇所）",
                risk_level="low",
            )
        )

    return hints


def compute_semantic_diff(
    file_path: Path,
    before_code: str,
    after_code: str,
    *,
    language: str = "python",
) -> SemanticDiffResult:
    """
    Before/After のコードから「意味的な変更点」を抽出する。

    - 失敗した場合も例外を投げず、最低限 raw_line_diff_summary だけ埋めて返す。

    Args:
        file_path: ファイルパス（相対パスでも可）
        before_code: Before コード
        after_code: After コード
        language: 言語（現状は "python" のみ対応）

    Returns:
        SemanticDiffResult
    """
    result = SemanticDiffResult(file_path=file_path)

    # Python 以外は raw diff のみ
    if language != "python":
        lines_before = before_code.splitlines()
        lines_after = after_code.splitlines()
        diff_lines = list(
            difflib.unified_diff(
                lines_before,
                lines_after,
                fromfile="before",
                tofile="after",
                lineterm="",
                n=3,
            )
        )[
            :20
        ]  # 最初の20行だけ
        result.raw_line_diff_summary = "\n".join(diff_lines)
        return result

    # Python コードの解析
    try:
        # Before の AST 解析
        tree_before: ast.AST | None = None
        functions_before: dict[str, dict[str, str | None]] = {}
        try:
            tree_before = ast.parse(before_code, filename=str(file_path))
            functions_before = _extract_functions_from_ast(tree_before)
        except SyntaxError as e:
            logger.warning(f"Failed to parse before code for {file_path}: {e}")

        # After の AST 解析
        tree_after: ast.AST | None = None
        functions_after: dict[str, dict[str, str | None]] = {}
        try:
            tree_after = ast.parse(after_code, filename=str(file_path))
            functions_after = _extract_functions_from_ast(tree_after)
        except SyntaxError as e:
            logger.warning(f"Failed to parse after code for {file_path}: {e}")

        # 関数レベルの差分を計算
        all_function_names = set(functions_before.keys()) | set(functions_after.keys())

        for func_name in all_function_names:
            before_info = functions_before.get(func_name)
            after_info = functions_after.get(func_name)

            if before_info is None and after_info is not None:
                # 追加
                result.functions.append(
                    FunctionChange(
                        name=func_name,
                        kind="added",
                        signature_after=after_info.get("signature"),
                        doc_after=after_info.get("doc"),
                    )
                )
            elif before_info is not None and after_info is None:
                # 削除
                result.functions.append(
                    FunctionChange(
                        name=func_name,
                        kind="removed",
                        signature_before=before_info.get("signature"),
                        doc_before=before_info.get("doc"),
                    )
                )
            elif before_info is not None and after_info is not None:
                # 変更の可能性をチェック
                sig_before = before_info.get("signature")
                sig_after = after_info.get("signature")
                doc_before = before_info.get("doc")
                doc_after = after_info.get("doc")

                if sig_before != sig_after or doc_before != doc_after:
                    result.functions.append(
                        FunctionChange(
                            name=func_name,
                            kind="modified",
                            signature_before=sig_before,
                            signature_after=sig_after,
                            doc_before=doc_before,
                            doc_after=doc_after,
                        )
                    )

        # 振る舞いの変化ヒントを構築
        lines_before = before_code.splitlines()
        lines_after = after_code.splitlines()
        result.behavior_hints = _build_behavior_hints_from_diff(lines_before, lines_after)

        # raw diff サマリー（最初の20行だけ）
        diff_lines = list(
            difflib.unified_diff(
                lines_before,
                lines_after,
                fromfile="before",
                tofile="after",
                lineterm="",
                n=3,
            )
        )[:20]
        result.raw_line_diff_summary = "\n".join(diff_lines)

    except Exception as e:
        # どこかで例外が出ても SemanticDiffResult を返すようにする
        logger.warning(f"Error computing semantic diff for {file_path}: {e}", exc_info=True)
        # 最低限 raw diff だけは埋める
        try:
            lines_before = before_code.splitlines()
            lines_after = after_code.splitlines()
            diff_lines = list(
                difflib.unified_diff(
                    lines_before,
                    lines_after,
                    fromfile="before",
                    tofile="after",
                    lineterm="",
                    n=3,
                )
            )[:20]
            result.raw_line_diff_summary = "\n".join(diff_lines)
        except Exception:
            pass  # 最後の手段も失敗した場合は空のまま返す

    return result
