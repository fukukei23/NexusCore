# ==============================================================================
# フォルダ: src/agents
# ファイル名: patch_applier.py
# メモ: 内部ロジックを簡素化し、OS標準の`patch`コマンドを直接呼び出すことで
#      信頼性と堅牢性を向上させた最終バージョン。
# ==============================================================================
import logging
import os
import shutil
import subprocess
import tempfile
import re

class PatchApplier:
    """
    'unified diff' 形式のパッチをソースコードファイルに適用するためのクラス。
    DebuggerAgentによって生成されたパッチを解釈し、対象ファイルを安全に更新する。
    """

    def apply(self, patch_str: str, target_file_path: str) -> bool:
        """
        指定されたファイルにパッチを適用します。

        Args:
            patch_str (str): unified diff形式のパッチ文字列。
            target_file_path (str): パッチを適用するファイルのパス。

        Returns:
            bool: パッチの適用が成功した場合はTrue、失敗した場合はFalse。
        """
        if not patch_str:
            logging.warning("Patch is empty. Nothing to apply.")
            return False

        if not os.path.exists(target_file_path):
            logging.error(f"Target file not found: {target_file_path}")
            return False

        # `patch` コマンドラインツールが利用可能かチェック
        if shutil.which("patch"):
            logging.info("Found 'patch' command. Using the standard system tool for reliability.")
            return self._apply_with_patch_command(patch_str, target_file_path)
        else:
            logging.warning("'patch' command not found. Attempting to apply patch using a built-in Python method. This is less robust for complex patches but avoids external dependencies.")
            return self._apply_with_python_fallback(patch_str, target_file_path)

    def _apply_with_patch_command(self, patch_str: str, target_file_path: str) -> bool:
        """
        `patch` コマンドを使用してパッチを適用します。最も信頼性の高い方法です。
        """
        try:
            # パッチ文字列を一時ファイルに書き込む
            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.patch', encoding='utf-8', newline='\n') as patch_file:
                patch_file.write(patch_str)
                patch_filename = patch_file.name

            # patchコマンドを実行
            result = subprocess.run(
                ['patch', '-u', target_file_path, '-i', patch_filename],
                capture_output=True, text=True, encoding='utf-8', errors='replace'
            )

            # 一時ファイルを削除
            os.unlink(patch_filename)

            if result.returncode == 0:
                logging.info(f"Successfully applied patch to {target_file_path} using 'patch' command.")
                return True
            else:
                # パッチ適用失敗時のエラーログを詳細に出力
                logging.error(f"Failed to apply patch using 'patch' command. Stderr:\n{result.stderr}")
                return False
        except Exception as e:
            logging.error(f"An error occurred while using 'patch' command: {e}", exc_info=True)
            return False

    def _apply_with_python_fallback(self, patch_str: str, target_file_path: str) -> bool:
        """
        `patch`コマンドが見つからない場合の、Pythonのみでパッチ適用を試みるフォールバック。
        """
        try:
            with open(target_file_path, 'r', encoding='utf-8') as f:
                original_lines = f.readlines()

            patch_lines = patch_str.splitlines(True)
            patched_lines = []
            original_idx = 0
            patch_idx = 0

            # ヘッダーをスキップ
            while patch_idx < len(patch_lines) and not patch_lines[patch_idx].startswith('@@'):
                patch_idx += 1

            if patch_idx >= len(patch_lines):
                logging.error("Patch does not contain any hunk headers ('@@').")
                return False

            # ハンク（変更箇所）を処理
            while patch_idx < len(patch_lines):
                if not patch_lines[patch_idx].startswith('@@'):
                    patch_idx += 1
                    continue
                
                hunk_header = patch_lines[patch_idx]
                match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', hunk_header)
                if not match:
                    logging.error(f"Could not parse hunk header: {hunk_header.strip()}")
                    return False
                
                old_start = int(match.group(1))
                
                # ハンクの前の行を元のファイルからコピー
                patched_lines.extend(original_lines[original_idx : old_start - 1])
                original_idx = old_start - 1
                patch_idx += 1

                # ハンク内の行を適用
                while patch_idx < len(patch_lines) and not patch_lines[patch_idx].startswith('@@'):
                    line = patch_lines[patch_idx]
                    if line.startswith('+'):
                        patched_lines.append(line[1:])
                    elif line.startswith('-'):
                        original_idx += 1 # 元のファイルの行をスキップ
                    elif line.startswith(' '):
                        if original_idx < len(original_lines):
                            patched_lines.append(original_lines[original_idx])
                        else: # 元のファイルに行がない場合は、パッチのコンテキスト行をそのまま使う
                            patched_lines.append(line[1:])
                        original_idx += 1
                    patch_idx += 1
            
            # 残りの行を元のファイルからコピー
            patched_lines.extend(original_lines[original_idx:])

            # 変更後の内容をファイルに書き戻す
            with open(target_file_path, 'w', encoding='utf-8', newline='') as f:
                f.writelines(patched_lines)

            return True
        except Exception as e:
            logging.error(f"Python fallback patch applicator failed: {e}", exc_info=True)
            return False
