# 📁 test_generator.py
# 📂 保存場所: /src/utils/test_generator.py
"""
test_generator: pytest テストコード生成モジュール

生成方針:
- pytest ベースの関数名（test_ で始まる）
- if __name__ == "__main__": を書かない
- DB 接続を行わない
- ファイル書き込み I/O を行わない（必要なら mock を書くよう明示）
- 危険な操作（os.system, subprocess, eval, exec など）を禁止
"""

from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Optional, Tuple
from dotenv import load_dotenv

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    OpenAI = None  # type: ignore

from nexuscore.utils.test_utils import (
    validate_test_code,
    extract_code_from_markdown,
    create_fallback_test_file,
    project_path_to_module_path,
)

load_dotenv()
logger = logging.getLogger(__name__)

# クライアントは必要に応じて初期化（グローバルに持たない）
_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    """OpenAI クライアントを取得（遅延初期化）"""
    global _client
    if _client is None:
        if not HAS_OPENAI:
            raise ImportError("openai package is not installed")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        _client = OpenAI(api_key=api_key)
    return _client


def generate_unit_tests(
    code: str,
    file_path: Optional[Path] = None,
    project_root: Optional[Path] = None,
    module_path: Optional[str] = None,
) -> str:
    """
    Python コードに対して pytest 形式のユニットテストを生成する。
    
    Args:
        code: テスト対象の Python コード
        file_path: 対象ファイルのパス（import path 生成に使用）
        project_root: プロジェクトルート（import path 生成に使用）
        module_path: モジュールパス（指定されている場合）
    
    Returns:
        生成されたテストコード（Markdown コードブロックを含む可能性がある）
    """
    # import path の決定
    if module_path is None and file_path is not None and project_root is not None:
        module_path = project_path_to_module_path(project_root, file_path)
    
    # プロンプトの構築（絶対守ってほしい制約を明文化）
    prompt = f"""次のPythonコードに対して、pytest形式のユニットテストを生成してください。

# 対象コード
```python
{code}
```

# 絶対守ってほしい制約（必須）
1. pytest ベースの関数名（test_ で始まる）を使用してください
2. if __name__ == "__main__": を書かないでください
3. DB 接続を行わないでください（必要なら mock を使用）
4. ファイル書き込み I/O（open(..., "w"), open(..., "a")）を行わないでください（必要なら mock を使用）
5. 危険な操作（os.system, subprocess, eval, exec, __import__）を絶対に使用しないでください
6. 外部API依存は必ずモック化してください
7. time.sleep は使わないでください
8. ランダム値は固定してください

# 理想的なテスト例
```python
import pytest
from unittest.mock import Mock, patch, MagicMock

# モジュールパス: {module_path or "your_module"}

def test_function_name_normal_case():
    \"\"\"正常系のテスト\"\"\"
    # テストコード
    assert True

def test_function_name_edge_case():
    \"\"\"エッジケースのテスト\"\"\"
    # テストコード
    assert True

def test_function_name_error_case():
    \"\"\"異常系のテスト\"\"\"
    # テストコード
    with pytest.raises(ValueError):
        # エラーが発生するコード
        pass
```

# 出力形式（必須）
上記の例に従って、pytest テストコードを生成してください。
コードブロック（```python ... ```）で囲んで出力してください。
"""

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4"),
            messages=[
                {
                    "role": "system",
                    "content": "あなたは優秀なPythonのテストエンジニアです。安全性と品質を最優先に、pytest形式のテストコードを生成します。"
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        
        generated_code = response.choices[0].message.content
        return generated_code
        
    except Exception as e:
        logger.error(f"Test generation failed: {e}")
        # エラー時のフォールバック
        if file_path:
            return create_fallback_test_file(file_path, str(e))
        raise


def generate_and_validate_test_code(
    code: str,
    file_path: Optional[Path] = None,
    project_root: Optional[Path] = None,
    module_path: Optional[str] = None,
) -> Tuple[str, bool, Optional[str], list[str]]:
    """
    テストコードを生成し、検証も行う。
    
    Args:
        code: テスト対象の Python コード
        file_path: 対象ファイルのパス
        project_root: プロジェクトルート
        module_path: モジュールパス
    
    Returns:
        (test_code, is_valid, error_message, warnings) のタプル
    """
    # テストコードを生成
    generated = generate_unit_tests(code, file_path, project_root, module_path)
    
    # Markdown からコードを抽出
    test_code = extract_code_from_markdown(generated)
    
    # 検証
    is_valid, error_message, warnings = validate_test_code(test_code)
    
    # 警告をログ出力
    if warnings:
        logger.warning(f"Test code validation warnings: {warnings}")
    
    # エラーがある場合はフォールバック
    if not is_valid and error_message:
        logger.error(f"Generated test code is invalid: {error_message}")
        if file_path:
            test_code = create_fallback_test_file(file_path, error_message)
            is_valid = True  # フォールバックファイルは有効
            error_message = None
    
    return test_code, is_valid, error_message, warnings
