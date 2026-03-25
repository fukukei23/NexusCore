# ==============================================================================
# フォルダ: src/nexuscore/agents/
# ファイル名: coder_agent.py (リファクタリング版)
# メモ: 新しいBaseAgentに準拠するようリファクタリング。
#      - __init__を明示的に呼び出すように変更。
#      - LLM呼び出しをexecute_llm_taskメソッドに統一。
# ==============================================================================
import ast
import logging
import re

from .base_agent import BaseAgent


class CoderAgent(BaseAgent):
    SYSTEM_PROMPT = "あなたは、クリーンで効率的なコードを書くことを得意とする、世界クラスのPython開発者です。あなたの唯一の仕事は、与えられた指示に基づき、完全に動作するPythonコードを生成することです。"
    RETRY_LIMIT = 2

    # ★★★★★ ここからが最重要修正点 (1/2) ★★★★★
    def __init__(self):
        """
        CoderAgentを初期化する。
        新しいBaseAgentの__init__を呼び出すことで、LLMRouterが自動的にセットアップされる。
        """
        super().__init__()

    # ★★★★★ ここまで ★★★★★

    # ------------------------------------------------------------------
    # AST 構文検査 + 簡易リトライ
    # ------------------------------------------------------------------
    def _validate_python_syntax(self, code: str) -> tuple[bool, str]:
        try:
            ast.parse(code)
            return True, ""
        except SyntaxError as e:
            return False, f"SyntaxError: {e}"
        except Exception as e:
            return False, f"ParseError: {e}"

    def implement_code(
        self, task_description: str, existing_code: str, code_language: str = "python"
    ) -> str:
        """
        生成→AST検査→失敗時リトライを最短1秒以内で回す。
        """
        prompt = f"""
# 既存のコード
```python
{existing_code}
```

# あなたへの指示
上記の既存コードに対して、以下のタスクを実装してください。

## タスク内容
「{task_description}」

# 重要：
もしタスク内容に `[Orchestratorからの具体的指示]` や `[Guardianからのフィードバック]` が含まれている場合は、元のタスクよりも、そのフィードバックの内容を解決することを最優先してください。

# 絶対的な出力ルール
- **修正後の完全なPythonコードのみ**を出力してください。
- コードの前に前置きや言い訳、後に結びの言葉や要約など、**コード以外のテキストは一切含めないでください。**
- あなたの思考プロセスや解釈を、Pythonのコメント（`#`）以外でコードに含めてはなりません。
- 出力は、そのまま `.py` ファイルとして保存できる、純粋なPythonコードでなければなりません。
"""
        for attempt in range(self.RETRY_LIMIT):
            raw_response = self.execute_llm_task(prompt, task_type="code_generate")
            # マークダウンコードブロックからコードを抽出
            code = self._extract_code_from_response(raw_response, code_language)
            ok, err = self._validate_code(code_language, code)
            if ok:
                return code
            logging.getLogger(self.__class__.__name__).warning(
                "AST validation failed (attempt %s/%s): %s",
                attempt + 1,
                self.RETRY_LIMIT,
                err,
            )
            # フィードバックをプロンプトに追記して再試行
            prompt += f"\n# AST検査フィードバック: {err}\n# 構文エラーを必ず修正してください。"
        return code

    def _extract_code_from_response(self, response: str, language: str = "python") -> str:
        """
        LLMレスポンスからコードを抽出する。
        マークダウンコードブロック（```python ... ```）からコードを抽出し、
        コードブロックが見つからない場合はレスポンス全体を返す。
        """
        # マークダウンコードブロックを抽出
        # パターン: ```python\n...\n``` または ```python\n...\n``` または ```\n...\n```
        code_block_pattern = re.compile(r"```(?:\w+)?\s*\n(.*?)```", re.DOTALL | re.MULTILINE)
        matches = code_block_pattern.findall(response)

        if matches:
            # 最初のコードブロックを使用
            extracted = matches[0].strip()
            # 先頭の説明文やコメント行を除去（「以下はコードです」などの前置きを削除）
            lines = extracted.split("\n")
            # Pythonコードとして妥当な行から開始（import, def, class, # から始まる行など）
            start_idx = 0
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped and (
                    stripped.startswith(("import ", "from ", "def ", "class ", "#", '"', "'"))
                    or stripped.startswith(("print", "if ", "for ", "while ", "return ", "="))
                ):
                    start_idx = i
                    break
            return "\n".join(lines[start_idx:]).strip()

        # コードブロックが見つからない場合は、レスポンス全体から不要な前置きを削除
        lines = response.split("\n")
        cleaned_lines = []
        code_started = False
        for line in lines:
            stripped = line.strip()
            # コードらしい行が見つかったら開始
            if (
                not code_started
                and stripped
                and (
                    stripped.startswith(("import ", "from ", "def ", "class ", "print", "#"))
                    or stripped.startswith(("if ", "for ", "while ", "return "))
                )
            ):
                code_started = True
            if code_started or stripped.startswith("#") or stripped.startswith('"""'):
                cleaned_lines.append(line)

        cleaned = "\n".join(cleaned_lines).strip()
        # コードらしい行が一切検出できない場合は、レスポンス全体を返す
        # （テストや短いコード片の生成で、単一行が返るケースを想定）
        return cleaned if cleaned else response.strip()

    def _validate_code(self, language: str, code: str) -> tuple[bool, str]:
        lang = (language or "python").lower()
        if lang == "python":
            return self._validate_python_syntax(code)
        # Tree-sitter オプション検査（対応言語のみ）
        try:
            from nexuscore.utils.tree_sitter_checker import SemanticAnalyzer

            analyzer = SemanticAnalyzer()
            available, msg = analyzer.check_availability()
            if not available:
                return True, ""  # 利用不可ならスキップして成功扱い
            if not analyzer.setup_parsers([lang]):
                return True, ""  # 言語未対応ならスキップ
            result = analyzer.analyze_source_code(code, language=lang)
            if getattr(result, "success", False) and not result.data.get("errors", {}).get(
                "has_syntax_errors"
            ):
                return True, ""
            return False, f"Tree-sitter validation failed for {lang}"
        except Exception:
            return True, ""  # チェッカー呼び出し失敗でもブロックしない
