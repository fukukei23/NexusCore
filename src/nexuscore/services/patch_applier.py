import difflib
import logging
import os
from typing import Any

try:
    import patch  # python-patch ライブラリを使用

    HAS_PATCH = True
except ImportError:
    HAS_PATCH = False
    patch = None


class PatchApplier:
    """
    'unified diff' 形式のパッチをソースコードに適用するクラス。

    - python-patch (patch.py) の fromstring/apply を利用
    - dry-run モードで「適用せず検証だけ」可能
    - 危険な削除行を含むパッチをガード (allow_deletions=False のとき)
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def apply_patch(
        self,
        patch_text: str,
        project_path: str,
        dry_run: bool = False,
        allow_deletions: bool = False,
        max_delete_lines: int = 20,
    ) -> dict[str, Any]:
        """
        パッチをプロジェクト配下に適用する。

        :param patch_text: unified diff 文字列
        :param project_path: プロジェクトのルートディレクトリ
        :param dry_run: True の場合は適用せず検証のみ行う
        :param allow_deletions: True の場合のみ削除行を許可
        :param max_delete_lines: 削除許可時の削除行数上限（壁2-Aガード・超過はブロック）
        :return: 結果を表す dict（詳細な情報を含む）

        戻り値の例:
        {
            "applied": True/False,
            "dry_run": True/False,
            "dangerous": True/False,
            "delete_lines": 10,
            "reason": "...",
            "error": "例外メッセージ or None",
        }
        """
        result: dict[str, Any] = {
            "applied": False,
            "dry_run": dry_run,
            "dangerous": False,
            "delete_lines": 0,
            "reason": "",
            "error": None,
        }

        if not HAS_PATCH:
            result["reason"] = "python-patch library not available. Install with: pip install patch"
            self.logger.error(result["reason"])
            return result

        if not patch_text.strip():
            result["reason"] = "Empty patch text."
            self.logger.warning("apply_patch called with empty patch_text.")
            return result

        if not os.path.isdir(project_path):
            result["reason"] = f"Project path not found: {project_path}"
            self.logger.error(result["reason"])
            return result

        # 1. 危険度チェック（削除行の有無）
        danger_info = self._detect_danger(patch_text)
        result["dangerous"] = danger_info["has_delete"]
        result["delete_lines"] = danger_info["delete_lines"]

        if danger_info["has_delete"] and not allow_deletions:
            msg = (
                f"Patch contains {danger_info['delete_lines']} deleted lines. "
                f"allow_deletions=False のため適用をブロックしました。"
            )
            result["reason"] = msg
            self.logger.warning(msg)
            return result

        # 壁2-A: 削除許可時でも削除行数上限を超えたらブロック（nexuscore-bench Phase 0）
        if allow_deletions and danger_info["has_delete"]:
            delete_count = int(danger_info["delete_lines"])
            if delete_count > max_delete_lines:
                msg = (
                    f"削除行数 {delete_count} が上限 {max_delete_lines} を超えたため"
                    "ブロックしました（壁2-Aガード）"
                )
                result["reason"] = msg
                result["blocked_reason"] = "delete_cap_exceeded"
                result["max_delete_lines"] = max_delete_lines
                self.logger.warning(msg)
                return result

        # 2. python-patch でパッチをパース
        try:
            # python-patch(-ng) の API: fromstring(diff) -> PatchSet
            # 文字列をバイト列に変換（python-patch-ng は bytes を期待する場合がある）
            if isinstance(patch_text, str):
                patch_bytes = patch_text.encode("utf-8")
            else:
                patch_bytes = patch_text
            patch_set = patch.fromstring(patch_bytes)
        except Exception as e:  # noqa: BLE001
            msg = f"Failed to parse patch text with python-patch: {e}"
            result["reason"] = msg
            result["error"] = str(e)
            self.logger.error(msg, exc_info=True)
            return result

        # 3. dry-run の場合はここで終了（将来的に apply のシミュレーションも可能）
        if dry_run:
            # patch_set が作れた時点で「少なくとも構文としては有効」
            msg = "Dry-run only: patch parsed successfully but not applied."
            result["reason"] = msg
            self.logger.info(msg)
            return result

        # 4. 実際に適用（壁2-B: 削除を含む場合は適用前スナップショット取得）
        snapshots: dict[str, str] = {}
        if allow_deletions and danger_info["has_delete"]:
            for item in getattr(patch_set, "items", []):
                raw_target = getattr(item, "target", "")
                if isinstance(raw_target, bytes):
                    raw_target = raw_target.decode("utf-8", errors="replace")
                target = str(raw_target)
                if target:
                    abs_path = os.path.join(project_path, target.lstrip("./"))
                    if os.path.isfile(abs_path):
                        try:
                            with open(abs_path, encoding="utf-8") as f:
                                snapshots[abs_path] = f.read()
                        except OSError:
                            pass
        try:
            # root をプロジェクトのパスに設定
            # strip 引数はオプション（python-patch-ng では strip=0 がデフォルト）
            try:
                success = patch_set.apply(root=project_path, strip=0)
            except TypeError:
                # strip 引数がサポートされていない場合は root のみ
                success = patch_set.apply(root=project_path)
            if success:
                # 壁2-B: 削除適用後にAST安全検証（nexuscore-bench Phase 0）
                if snapshots:
                    from src.nexuscore.agents._guardian_helpers.ast_safety import (
                        check_delete_safety,
                    )

                    for abs_path, before_text in snapshots.items():
                        if not abs_path.endswith(".py"):
                            continue
                        try:
                            with open(abs_path, encoding="utf-8") as f:
                                after_text = f.read()
                        except OSError:
                            continue
                        verdict = check_delete_safety(before_text, after_text)
                        if not verdict["ok"]:
                            # ロールバック（安全側: 適用前の内容へ復元）
                            with open(abs_path, "w", encoding="utf-8") as f:
                                f.write(before_text)
                            msg = (
                                f"Guardian AST reject: {verdict['reason']} "
                                f"({abs_path})。適用をロールバックしました。"
                            )
                            result["applied"] = False
                            result["reason"] = msg
                            result["blocked_reason"] = "ast_safety_reject"
                            result["human_approval_required"] = True
                            self.logger.warning(msg)
                            return result
                result["applied"] = True
                result["reason"] = f"Patch successfully applied in: {project_path}"
                self.logger.info(result["reason"])
            else:
                result["applied"] = False
                result["reason"] = (
                    f"Patch application failed in: {project_path}. "
                    f"The patch may be invalid or already applied."
                )
                self.logger.error(result["reason"])
        except Exception as e:  # noqa: BLE001
            msg = f"Exception occurred while applying patch: {e}"
            result["reason"] = msg
            result["error"] = str(e)
            self.logger.error(msg, exc_info=True)

        return result

    # ------------------------------------------------------------------ #
    # Helper: 危険度判定
    # ------------------------------------------------------------------ #
    def _detect_danger(self, patch_text: str) -> dict[str, Any]:
        """
        非常に単純な危険度判定:
          - 行頭が '-' で、かつ '--- ' ではない行を「削除行」とみなす。
        """
        delete_lines = 0
        for line in patch_text.splitlines():
            # ヘッダ行 '--- a/file' は除外
            if line.startswith("--- "):
                continue
            # 実際の削除行
            if line.startswith("-"):
                delete_lines += 1

        return {
            "has_delete": delete_lines > 0,
            "delete_lines": delete_lines,
        }

    # ------------------------------------------------------------------ #
    # 互換用: 旧インターフェースが bool を返していた場合のラッパー
    # ------------------------------------------------------------------ #
    def apply_patch_bool(self, patch_text: str, project_path: str) -> bool:
        """
        旧コードとの互換性のためのラッパー。
        - 危険度チェックはデフォルト（allow_deletions=False）
        - dry_run=False で実際に適用
        """
        result = self.apply_patch(
            patch_text=patch_text,
            project_path=project_path,
            dry_run=False,
            allow_deletions=False,
        )
        return bool(result.get("applied"))

    # ------------------------------------------------------------------ #
    # 旧インターフェース互換: apply() メソッド（後方互換性のため）
    # ------------------------------------------------------------------ #
    def apply(self, patch_str: str, project_path: str) -> bool:
        """
        旧インターフェースとの互換性のためのメソッド。
        apply_patch_bool() のエイリアス。
        """
        return self.apply_patch_bool(patch_str, project_path)

    # ------------------------------------------------------------------ #
    # E-4: Before/After 差分抽出
    # ------------------------------------------------------------------ #
    @staticmethod
    def get_text_diff(before: str, after: str) -> str:
        """
        Before/After の差分を unified diff 形式の文字列で返す。

        Args:
            before: 変更前のコード
            after: 変更後のコード

        Returns:
            unified diff 形式の文字列
        """
        before_lines = before.splitlines(keepends=True)
        after_lines = after.splitlines(keepends=True)

        # difflib.unified_diff を使用
        diff_lines = difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile="before",
            tofile="after",
            lineterm="",
        )

        return "".join(diff_lines)
