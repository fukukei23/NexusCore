# ==============================================================================
# フォルダ: src/agents
# ファイル名: debugger_agent.py
# メモ: FKBの'target'ヒントを解釈し、「修正計画」を返す分析官にアップグレード。
#      エラーログとファイルコンテキストを受け取り、修正対象とパッチを特定します。
# ==============================================================================
import os
import json
import re
import difflib
import logging
from .base_agent import BaseAgent

class DebuggerAgent(BaseAgent):
    """
    エラーログを分析し、FKBの知識に基づいて、どのファイルにどのような修正を
    適用すべきかという「修正計画」を立案する分析官エージェント。
    """
    def __init__(self, api_key: str, model: str, knowledge_base_path: str = "fkb_local.json"):
        super().__init__(api_key, model)
        self.knowledge_base_path = knowledge_base_path
        self.fkb = self._load_fkb()
        
        if self.fkb:
            print(f"[OK] DebuggerAgent initialized. {len(self.fkb)} known issues loaded from: {self.knowledge_base_path}")
        else:
            print(f"[WARNING] DebuggerAgent initialized with an EMPTY knowledge base. File not found or empty at: {self.knowledge_base_path}")

    def _load_fkb(self) -> list:
        """
        Failure Knowledge Base (FKB)をロードします。
        サンドボックス実行を考慮し、カレントディレクトリからの相対パスで検索します。
        """
        try:
            path = self.knowledge_base_path
            if not os.path.isabs(path):
                path = os.path.join(os.getcwd(), self.knowledge_base_path)
            if not os.path.exists(path): return []
            with open(path, 'r', encoding='utf-8') as f: return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Failed to load FKB: {e}")
            return []

    def debug(self, error_log: str, files_context: dict) -> dict | None:
        """
        エラーログを分析し、パッチとターゲットファイルを含む「修正計画」を返します。

        Args:
            error_log (str): pytestなどから出力されたエラーログ。
            files_context (dict): 修正対象となりうるファイルのパスを格納した辞書。
                                  例: {"source_file": "/path/to/app.py", "test_file": "/path/to/test_app.py"}

        Returns:
            dict | None: 修正計画の辞書、または解決策が見つからない場合はNone。
                         例: {"patch": "...", "target": "test_file", "entry": {...}}
        """
        logging.info(f"Debugging error... (log size: {len(error_log)} chars)")

        for entry in self.fkb:
            if re.search(entry["error_signature"], error_log, re.DOTALL | re.IGNORECASE):
                logging.info(f"Found known issue: {entry['cause']}")
                
                # FKBから修正対象のヒント（"source_file" or "test_file"）を取得
                target_hint = entry.get("target", "source_file") # デフォルトはソースファイル
                
                file_to_read_path = files_context.get(target_hint)
                if not file_to_read_path or not os.path.exists(file_to_read_path):
                    logging.error(f"Target file for reading not found in context: {target_hint}")
                    continue

                try:
                    with open(file_to_read_path, 'r', encoding='utf-8') as f:
                        original_code = f.read()
                    
                    modified_code = self._apply_solution_pattern(original_code, entry["solution_pattern"])

                    if modified_code and original_code != modified_code:
                        diff = self._create_diff(original_code, modified_code, file_to_read_path)
                        logging.info(f"Generated patch for '{target_hint}':\n{diff}")
                        # 「修正計画」を辞書として返す
                        return {"patch": diff, "target": target_hint, "entry": entry}
                    else:
                        logging.warning(f"Solution pattern did not result in code changes for file: {file_to_read_path}")
                
                except Exception as e:
                    logging.error(f"Error applying solution for '{entry['cause']}': {e}", exc_info=True)
                
                # 1つのルールに一致したら、その結果（成功でも失敗でも）を返して終了
                return None

        logging.warning("No known solution found in FKB for this error.")
        return None

    def _apply_solution_pattern(self, code: str, solution: dict) -> str | None:
        """FKBの解決策パターンに基づき、コードを修正します。"""
        solution_type = solution.get("type")
        if solution_type == "regex_replace":
            search_pattern = solution["search"]
            replace_template = solution["replace"]
            # FKBの$1, $2... を re.subが解釈できる \\1, \\2... に変換
            replace_template = re.sub(r'\$(\d)', r'\\\1', replace_template)
            return re.sub(search_pattern, replace_template, code, flags=re.DOTALL)
        elif solution_type == "add_import":
            import_statement = solution["import"]
            if import_statement not in code:
                return f"{import_statement}\n{code}"
            return code
        return None

    def _create_diff(self, original_code: str, modified_code: str, filename: str) -> str:
        """2つのコード文字列からunified diff形式のパッチを生成します。"""
        diff = difflib.unified_diff(
            original_code.splitlines(keepends=True),
            modified_code.splitlines(keepends=True),
            fromfile=filename,
            tofile=filename,
        )
        return "".join(diff)
