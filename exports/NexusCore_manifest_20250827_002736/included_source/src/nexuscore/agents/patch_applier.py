# ==============================================================================
# フォルダ: src/agents
# ファイル名: patch_applier.py
# メモ: 堅牢性と信頼性を最大化するため、専門ライブラリ`patch`を
#      正しく、安全に利用する完成版。
# ==============================================================================
import logging
import os
import patch # 専門ライブラリをインポート

class PatchApplier:
    """
    'unified diff' 形式のパッチをソースコードファイルに適用するためのクラス。
    専門ライブラリ`patch`を利用し、複雑なパッチも正確に適用する。
    """

    def apply(self, patch_str: str, project_path: str) -> bool:
        """
        指定されたプロジェクトパスを基準にパッチを適用します。

        Args:
            patch_str (str): unified diff形式のパッチ文字列。
            project_path (str): パッチを適用するプロジェクトのルートパス。

        Returns:
            bool: パッチの適用が成功した場合はTrue、失敗した場合はFalse。
        """
        if not patch_str:
            logging.warning("Patch is empty. Nothing to apply.")
            return False

        try:
            # パッチ文字列からパッチセットを解析
            patch_set = patch.fromstring(patch_str.encode('utf-8'))
            
            # ★ 解析失敗時のエラーハンドリングを追加
            if not patch_set:
                logging.error("Failed to parse patch string. It might be invalid or malformed.")
                logging.debug(f"Invalid patch string:\n{patch_str}")
                return False
            
            # ★ パッチを適用する基準ディレクトリ(root)を、プロジェクトのパスに正しく設定
            success = patch_set.apply(root=project_path)
            
            if success:
                logging.info(f"Successfully applied patch within project: {project_path}")
                return True
            else:
                logging.error(f"Failed to apply patch within project: {project_path}. The patch may be invalid or already applied.")
                return False
        except Exception as e:
            logging.error(f"An error occurred while applying patch with 'patch' library: {e}", exc_info=True)
            return False
