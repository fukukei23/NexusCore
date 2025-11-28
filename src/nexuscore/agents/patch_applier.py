# ==============================================================================
# PatchApplier: 安全な unified diff 適用ユーティリティ（dry-run / Danger Guard 対応版）
# ==============================================================================
import difflib
import logging
import os
from typing import Dict, Any

import patch  # python-patch / python-patch-ng 系ライブラリを想定


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
    ) -> Dict[str, Any]:
        """
        パッチをプロジェクト配下に適用する。

        :param patch_text: unified diff 文字列
        :param project_path: プロジェクトのルートディレクトリ
        :param dry_run: True の場合は適用せず検証のみ行う
        :param allow_deletions: True の場合のみ削除行を許可
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
        result: Dict[str, Any] = {
            "applied": False,
            "dry_run": dry_run,
            "dangerous": False,
            "delete_lines": 0,
            "reason": "",
            "error": None,
        }

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

        # 2. python-patch でパッチをパース
        try:
            # python-patch(-ng) の API: fromstring(diff) -> PatchSet
            # 文字列をバイト列に変換（python-patch-ng は bytes を期待する場合がある）
            if isinstance(patch_text, str):
                patch_bytes = patch_text.encode('utf-8')
            else:
                patch_bytes = patch_text
            patch_set = patch.fromstring(patch_bytes)
        except Exception as e:
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

        # 4. 実際に適用
        try:
            # root をプロジェクトのパスに設定
            # strip 引数はオプション（python-patch-ng では strip=0 がデフォルト）
            try:
                success = patch_set.apply(root=project_path, strip=0)
            except TypeError:
                # strip 引数がサポートされていない場合は root のみ
                success = patch_set.apply(root=project_path)
            if success:
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
        except Exception as e:
            msg = f"Exception occurred while applying patch: {e}"
            result["reason"] = msg
            result["error"] = str(e)
            self.logger.error(msg, exc_info=True)

        return result

    # ------------------------------------------------------------------ #
    # Helper: 危険度判定
    # ------------------------------------------------------------------ #
    def _detect_danger(self, patch_text: str) -> Dict[str, Any]:
        """
        非常に単純な危険度判定:
          - 行頭が '-' で、かつ '--- ' ではない行を「削除行」とみなす。
        """
        delete_lines = 0
        for line in patch_text.splitlines():
            # ヘッダ行 '--- a/file' は除外
            if line.startswith('--- '):
                continue
            # 実際の削除行
            if line.startswith('-'):
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
