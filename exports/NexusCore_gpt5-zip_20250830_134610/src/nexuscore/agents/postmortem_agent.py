# ==============================================================================
# 操作するソフト: VSCode (または任意のテキストエディタ)
# フォルダ: src/nexuscore/agents/
# ファイル名: postmortem_agent.py
# バージョン: 2.2 (堅牢性強化・最終版)
#
# メモ:
# あなたから頂いた最終レビューの内容を完全に反映しました。
# これにより、LLMとのデータ送受信における安全性が飛躍的に向上し、
# 運用事故（不正JSON、壊れた正規表現、秘匿情報混入）を未然に防ぎます。
#
# 【主な改良点 (最終ブラッシュアップ)】
# 1. 入力データのサニタイズ (Safety):
#    - `_truncate`と`_redact`ヘルパーを導入し、LLMに渡すコンテキストから
#      秘匿情報（APIキー等）をマスクし、長すぎる入力を自動で切り詰めます。
# 2. 出力データの厳格な検証 (Validation):
#    - `_validate_and_normalize`ヘルパーを導入し、LLMが生成したJSONが、
#      必須キー、データ型、正規表現の妥当性といったスキーマを完全に満たして
#      いることを保証します。
# 3. JSON抽出の堅牢化 (Robustness):
#    - LLMからの応答を、まず`json.loads`で直接パースし、失敗した場合のみ
#      フォールバックとして正規表現での抽出を試みる、より安全な方式に変更しました。
# ==============================================================================
import json
import re
import logging
import os
from typing import Any, Dict, Optional

from .base_agent import BaseAgent

# ★★★★★ ここからが最終ブラッシュアップの核心 (1/3) ★★★★★
# --- 入力/出力データを安全に処理するためのヘルパー関数 ---

ALLOWED_TARGETS = {"source_file", "test_file", "both"}
MAX_CTX = int(os.getenv("FKB_CONTEXT_LIMIT", "20000"))  # プロンプトに含める各コンテキストの最大文字数

def _truncate(s: str, limit: int = MAX_CTX) -> str:
    """文字列が長すぎる場合に、中央を省略して切り詰める"""
    if s is None or len(s) <= limit:
        return s
    head = s[: limit // 2]
    tail = s[-limit // 2 :]
    return f"{head}\n...\n{tail}"

def _redact(s: str) -> str:
    """文字列から既知の秘匿情報パターンをマスクする"""
    if not s:
        return s
    # AWSキーや一般的なAPIキーのパターンをマスク
    s = re.sub(r"AKIA[0-9A-Z]{16}", "****AWS_KEY_REDACTED****", s)
    s = re.sub(r"(?i)api[_-]?key[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]", "api_key:'****REDACTED****'", s)
    return s

def _validate_and_normalize(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """LLMが生成したJSONのスキーマと内容を検証・正規化する"""
    required = {"id", "error_signature", "cause", "target", "solution_pattern", "description"}
    if not isinstance(payload, dict) or not required.issubset(payload.keys()):
        return None
    
    # targetを正規化
    tgt = str(payload.get("target", "")).strip().lower()
    if tgt not in ALLOWED_TARGETS:
        return None
    payload["target"] = tgt

    # solution_patternを検証
    sp = payload.get("solution_pattern")
    if not isinstance(sp, dict) or sp.get("type") != "llm_diagnose_and_fix" or not sp.get("instruction"):
        return None

    # error_signatureが有効な正規表現か検証
    try:
        re.compile(str(payload["error_signature"]))
    except re.error:
        return None
        
    return payload
# ★★★★★ ここまで ★★★★★


class PostmortemAgent(BaseAgent):
    SYSTEM_PROMPT = """
あなたは、非常に経験豊富なソフトウェア開発者であり、根本原因分析（RCA）の専門家です。
あなたの仕事は、他のAIエージェントが解決に失敗したテストエラーの完全なコンテキストを分析し、
そのエラーを将来解決するための「知識」をJSON形式で生成することです。
"""

    def analyze_failure_and_suggest_fkb_entry(
        self,
        error_log: str,
        source_code: str,
        test_code: str,
        source_file_path: str,
        test_file_path: str
    ) -> Optional[dict]:
        """
        未知のエラーを分析し、KnowledgeBaseに追加すべき新しいエントリを提案する。
        """
        self.logger.info(f"Analyzing failed test to generate new FKB entry (source={source_file_path}, test={test_file_path})")

        # ★★★★★ ここからが最終ブラッシュアップの核心 (2/3) ★★★★★
        # LLMに渡す前に、コンテキストを安全な形にサニタイズする
        error_log_s = _redact(_truncate(error_log))
        source_code_s = _redact(_truncate(source_code))
        test_code_s   = _redact(_truncate(test_code))
        # ★★★★★ ここまで ★★★★★

        prompt = f"""
# 状況
我々のAI開発システムが、以下のテストエラーの自己修復に失敗しました。
原因は、故障知識ベース（FKB）に、このエラーを解決するためのルールが存在しなかったことです。
あなたの任務は、この失敗事例を分析し、FKBに追加すべき新しい知識エントリを1つ生成することです。

# 分析対象データ
---
## 1. 失敗したテストのエラーログ
```
{error_log_s}
```
---
## 2. エラーが発生したソースコード (`{source_file_path}`)
```python
{source_code_s}
```
---
## 3. 失敗したテストコード (`{test_file_path}`)
```python
{test_code_s}
```
---

# あなたへの厳格な指示
上記の情報に基づき、以下の思考プロセスに従って、FKBエントリを生成してください。

## 思考プロセス
1.  **根本原因の特定**: エラーログとコードを注意深く読み、バグの根本原因を特定せよ。（例：「テストコードが、ネストされた関数を直接インポートしようとしている」）
2.  **エラーシグネチャの一般化**: エラーログから、この種のエラーを将来確実に捕捉できる、汎用的な正規表現（regex）を `error_signature` として考案せよ。
3.  **完全な解決策の考案**: このバグを修正し、**テストを完全にパスさせる**には、どのファイルをどのように変更する必要があるかを具体的に考えよ。
    -   例えば、`ImportError`を修正する場合、`import`文の修正だけでなく、そのインポートを利用している箇所の**関数名**も修正する必要があるかもしれない。
    -   例えば、ソースコードの関数名を変更する場合、テストコードの呼び出し箇所も変更する必要がある。
    -   この具体的な修正を、`llm_diagnose_and_fix`の`instruction`として記述せよ。
4.  **最終的なJSONの構築**: 上記の分析結果を基に、`id`, `error_signature`, `cause`, `target`, `solution_pattern`, `description` を持つ、単一のJSONオブジェクトを生成せよ。

## `solution_pattern` の詳細なルール
- `solution_pattern` は、必ず "type" キーを持つ **JSONオブジェクト（辞書）**でなければならない。
- `type` が `"llm_diagnose_and_fix"` の場合: `"instruction"` キーに、**テストを完全にパスさせるための、包括的な修正指示**を記述せよ。

## JSON出力例
```json
{{
  "id": "FKB-SUGGESTION-0001",
  "error_signature": "ImportError: cannot import name 'add'",
  "cause": "テストコードが、ネストされた関数や、誤った名前の関数を直接インポートしようとしている。",
  "target": "test_file",
  "solution_pattern": {{
    "type": "llm_diagnose_and_fix",
    "instruction": "The test failed with an ImportError. Analyze the source code to find the correct way to access the intended function. Modify the test code to import the parent function and then call it to get the nested function, or fix the imported function name if it's a simple typo. The goal is to make the test pass."
  }},
  "description": "ネストされた関数やタイポによる不正なインポートが原因のエラーを、テストコード側を修正することで解決する知識。"
}}
```

# 絶対的な出力ルール
- **生成したJSONオブジェクトのみ**を出力すること。
- 説明、前置き、その他のテキストは一切含めてはならない。
- `id` は `"FKB-SUGGESTION-XXXX"` の形式とせよ。
- `cause` と `description` は、日本語で簡潔に記述すること。
- JSONは必ず `{{` で始まり、 `}}` で終わる単一のオブジェクトであること。
"""
        try:
            response_str = self.execute_llm_task(prompt, temperature=0.3, as_json=True)
            
            if not response_str:
                self.logger.error("LLM response was empty.")
                return None

            # ★★★★★ ここからが最終ブラッシュアップの核心 (3/3) ★★★★★
            # LLMからの出力を安全にパースし、検証する
            candidate = None
            try:
                # まず、文字列全体がJSONであると信じてパースを試みる
                candidate = json.loads(response_str)
            except json.JSONDecodeError:
                # 失敗した場合のみ、フォールバックとして波括弧で囲まれた部分を抽出
                match = re.search(r'\{.*\}', response_str, re.DOTALL)
                if not match:
                    self.logger.error(f"LLM response does not contain a JSON object. Raw response:\n{response_str}")
                    return None
                try:
                    candidate = json.loads(match.group(0))
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse extracted JSON: {e}. Raw extract:\n{match.group(0)}")
                    return None
            
            # スキーマと内容の検証
            normalized = _validate_and_normalize(candidate)
            if not normalized:
                self.logger.error(f"Generated JSON failed schema/regex validation. Raw candidate:\n{candidate}")
                return None
            
            self.logger.info("Successfully generated and validated a new FKB suggestion.")
            return normalized
            # ★★★★★ ここまで ★★★★★

        except Exception as e:
            self.logger.error(f"An unexpected error occurred in PostmortemAgent: {e}", exc_info=True)
            return None
