"""壁2-B: 削除を含むパッチ適用後のソースがAST的に安全か検証（最小実装）.

nexuscore-bench Phase 0 spec §3「壁2解消」:
allow_deletions=True 化に伴うハルシネーション過剰削除を防ぐため、
削除適用後ソースの構文検証+空ファイル化検出を行う。
Guardian reject 時は human_approval_required フラグを返し、人手承認を必須とする。
"""
import ast


def check_delete_safety(before: str, after: str) -> dict:
    """削除適用後のソース安全性を検証する.

    Args:
        before: 削除適用前のソース全文（現状未使用・将来の差分分析用に保持）
        after: 削除適用後のソース全文

    Returns:
        {"ok": bool, "reason": str, "human_approval_required": bool}
    """
    if after.strip() == "":
        return {
            "ok": False,
            "reason": "file_emptied: 削除によりファイルが空になった",
            "human_approval_required": True,
        }
    try:
        ast.parse(after)
    except SyntaxError as e:
        return {
            "ok": False,
            "reason": f"syntax_broken: 削除後に構文エラー({e.msg} line {e.lineno})",
            "human_approval_required": True,
        }
    return {"ok": True, "reason": "", "human_approval_required": False}
