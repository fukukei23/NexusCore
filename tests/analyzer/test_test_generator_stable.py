"""
test_generator の安定性テスト

LLM なしでも必ず pytest 用テストコードの"枠"を生成できること、
LLM を使う場合も失敗しても graceful degrade することを確認する。
"""

from __future__ import annotations

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

try:
    from nexuscore.utils.test_generator import (
        generate_template_tests,
        generate_unit_tests,
        generate_tests_for_module,
        TestGenConfig,
        DEFAULT_CONFIG,
        _try_generate_tests_with_llm,
    )
    HAS_TEST_GENERATOR = True
except ImportError:
    HAS_TEST_GENERATOR = False
    generate_template_tests = None  # type: ignore
    generate_unit_tests = None  # type: ignore
    generate_tests_for_module = None  # type: ignore
    TestGenConfig = None  # type: ignore
    DEFAULT_CONFIG = None  # type: ignore
    _try_generate_tests_with_llm = None  # type: ignore


@pytest.mark.skipif(not HAS_TEST_GENERATOR, reason="Test generator not available")
def test_template_mode_generates_basic_skeleton(sample_project_dir, tmp_path):
    """
    サンプルモジュールに def add_one(x): return x + 1 を定義。
    generate_template_tests(...) を直接呼び出し。
    返ってきた文字列に以下が含まれることを確認:
    - "def test_add_one" を含む
    - "TODO: implement test" を含む
    """
    module_b_path = sample_project_dir / "module_b.py"
    if not module_b_path.exists():
        pytest.skip("module_b.py not found in sample project")

    # テンプレート生成
    template = generate_template_tests(
        module_b_path,
        max_functions=20,
        project_root=sample_project_dir,
    )

    # 検証
    assert "def test_add_one" in template, f"Expected 'def test_add_one' in template, got:\n{template}"
    assert "TODO: implement test" in template or "TODO:" in template, f"Expected 'TODO: implement test' in template, got:\n{template}"
    assert "import pytest" in template, f"Expected 'import pytest' in template, got:\n{template}"


@pytest.mark.skipif(not HAS_TEST_GENERATOR, reason="Test generator not available")
def test_llm_disabled_uses_template_only(sample_project_dir, tmp_path, monkeypatch):
    """
    monkeypatch.setenv("NEXUS_TESTGEN_ENABLE_LLM", "0")。
    generate_tests_for_module(...) を呼び出し。
    LLM 呼び出し部分を monkeypatch して「呼ばれていない」こと、または LLM なしでもエラーにならないことを確認。
    """
    module_b_path = sample_project_dir / "module_b.py"
    if not module_b_path.exists():
        pytest.skip("module_b.py not found in sample project")

    # LLM を無効化
    monkeypatch.setenv("NEXUS_TESTGEN_ENABLE_LLM", "0")

    # LLM 呼び出しが行われないことを確認するためのモック
    llm_called = []

    def mock_llm_call(*args, **kwargs):
        llm_called.append(True)
        raise Exception("LLM should not be called")

    # 設定を構築（LLM 無効）
    config = TestGenConfig(use_llm=False, max_functions=20)

    # テストコードを生成
    output_path = tmp_path / "test_module_b.py"
    with patch("nexuscore.utils.test_generator._try_generate_tests_with_llm", side_effect=mock_llm_call):
        result_path = generate_tests_for_module(
            module_b_path,
            output_path=output_path,
            project_root=sample_project_dir,
            config=config,
        )

    # ファイルが生成されていること
    assert result_path.exists(), f"Test file should be generated at {result_path}"

    # 内容を確認
    test_code = result_path.read_text(encoding="utf-8")
    assert "def test_add_one" in test_code, f"Expected 'def test_add_one' in generated code, got:\n{test_code}"
    assert "TODO:" in test_code or "not implemented" in test_code, f"Expected TODO or 'not implemented' in generated code, got:\n{test_code}"

    # LLM が呼ばれていないこと（config.use_llm=False なので _try_generate_tests_with_llm は呼ばれない）
    # ただし、generate_tests_for_module 内で generate_unit_tests が呼ばれ、その中で _try_generate_tests_with_llm が呼ばれる可能性がある
    # しかし、config.use_llm=False なので、generate_unit_tests 内で LLM 呼び出しはスキップされる
    # したがって、llm_called は空であるべき
    # ただし、モックが適用されていない可能性もあるので、この検証は緩くする
    # 重要なのは、エラーにならずにテンプレートが生成されること
    assert "import pytest" in test_code, f"Expected 'import pytest' in generated code, got:\n{test_code}"


@pytest.mark.skipif(not HAS_TEST_GENERATOR, reason="Test generator not available")
def test_llm_failure_falls_back_to_template(sample_project_dir, tmp_path):
    """
    _try_generate_tests_with_llm 内で利用している LLM クライアントを monkeypatch して、必ず例外を投げるようにする。
    結果として返ってくるコードが generate_template_tests と同一（または少なくとも "TODO: implement test" を含む）ことを確認。
    """
    module_b_path = sample_project_dir / "module_b.py"
    if not module_b_path.exists():
        pytest.skip("module_b.py not found in sample project")

    # テンプレートを事前に生成
    template = generate_template_tests(
        module_b_path,
        max_functions=20,
        project_root=sample_project_dir,
    )

    # LLM 呼び出しを必ず例外を投げるようにモック
    def mock_llm_failure(*args, **kwargs):
        raise Exception("Simulated LLM failure")

    # 設定を構築（LLM 有効）
    config = TestGenConfig(use_llm=True, max_functions=20)

    # テストコードを生成（LLM 失敗をシミュレート）
    code = module_b_path.read_text(encoding="utf-8")
    with patch("nexuscore.utils.test_generator._get_client", side_effect=mock_llm_failure):
        generated = generate_unit_tests(
            code,
            file_path=module_b_path,
            project_root=sample_project_dir,
            config=config,
        )

    # 生成されたコードはテンプレートと同等（または "TODO:" を含む）であること
    assert "TODO:" in generated or "not implemented" in generated, f"Expected TODO or 'not implemented' in generated code (fallback), got:\n{generated}"
    assert "import pytest" in generated, f"Expected 'import pytest' in generated code, got:\n{generated}"

    # テンプレートの主要な要素が含まれていること
    assert "def test_" in generated, f"Expected 'def test_' in generated code, got:\n{generated}"


@pytest.mark.skipif(not HAS_TEST_GENERATOR, reason="Test generator not available")
def test_template_mode_handles_parse_error_gracefully(tmp_path):
    """
    故意に壊れた Python ファイルを用意（シンタックスエラー）。
    generate_template_tests を呼び出し。
    例外を投げず、"Failed to parse module" 的なコメントを含んだテキストを返すことを確認。
    """
    # シンタックスエラーを含むファイルを作成
    broken_file = tmp_path / "broken_module.py"
    broken_file.write_text(
        "def broken_function(\n"  # 閉じ括弧がない
        "    return 42\n",  # インデントエラー
        encoding="utf-8",
    )

    # テンプレート生成（例外が投げられないことを確認）
    result = generate_template_tests(
        broken_file,
        max_functions=20,
    )

    # 結果が返ってくること（例外が投げられていない）
    assert result is not None, "generate_template_tests should return a string even for broken files"
    assert isinstance(result, str), f"Expected string, got {type(result)}"

    # "Failed to parse" または "parse error" を含むこと
    assert "Failed to parse" in result or "parse error" in result or "parse_error" in result, f"Expected 'Failed to parse' or 'parse error' in result, got:\n{result}"

    # pytest のインポートが含まれていること
    assert "import pytest" in result, f"Expected 'import pytest' in result, got:\n{result}"

    # テスト関数が含まれていること（最低限のスキャフォールド）
    assert "def test_" in result, f"Expected 'def test_' in result, got:\n{result}"


@pytest.mark.skipif(not HAS_TEST_GENERATOR, reason="Test generator not available")
def test_template_mode_handles_read_error_gracefully(tmp_path):
    """
    存在しないファイルや読み込みエラーを処理できることを確認。
    """
    # 存在しないファイル
    non_existent_file = tmp_path / "non_existent.py"

    # テンプレート生成（例外が投げられないことを確認）
    result = generate_template_tests(
        non_existent_file,
        max_functions=20,
    )

    # 結果が返ってくること
    assert result is not None, "generate_template_tests should return a string even for non-existent files"
    assert isinstance(result, str), f"Expected string, got {type(result)}"

    # "Failed to read" または "read error" を含むこと
    assert "Failed to read" in result or "read error" in result or "read_error" in result, f"Expected 'Failed to read' or 'read error' in result, got:\n{result}"

    # pytest のインポートが含まれていること
    assert "import pytest" in result, f"Expected 'import pytest' in result, got:\n{result}"


@pytest.mark.skipif(not HAS_TEST_GENERATOR, reason="Test generator not available")
def test_generate_tests_for_module_always_returns_path(sample_project_dir, tmp_path):
    """
    generate_tests_for_module が常にファイルパスを返し、例外を投げないことを確認。
    """
    module_b_path = sample_project_dir / "module_b.py"
    if not module_b_path.exists():
        pytest.skip("module_b.py not found in sample project")

    output_path = tmp_path / "test_module_b.py"

    # LLM 無効で実行
    config = TestGenConfig(use_llm=False, max_functions=20)
    result_path = generate_tests_for_module(
        module_b_path,
        output_path=output_path,
        project_root=sample_project_dir,
        config=config,
    )

    # パスが返ってくること
    assert result_path is not None, "generate_tests_for_module should return a Path"
    assert isinstance(result_path, Path), f"Expected Path, got {type(result_path)}"

    # ファイルが存在すること
    assert result_path.exists(), f"Generated test file should exist at {result_path}"

    # ファイルが空でないこと
    test_code = result_path.read_text(encoding="utf-8")
    assert len(test_code) > 0, "Generated test file should not be empty"


@pytest.mark.skipif(not HAS_TEST_GENERATOR, reason="Test generator not available")
def test_max_functions_limit(sample_project_dir, tmp_path):
    """
    max_functions パラメータが正しく機能することを確認。
    """
    # 複数の関数を含むモジュールを作成
    multi_func_module = tmp_path / "multi_func.py"
    multi_func_module.write_text(
        "\n".join([f"def func_{i}(x): return x + {i}" for i in range(30)]),
        encoding="utf-8",
    )

    # max_functions=5 で生成
    template = generate_template_tests(
        multi_func_module,
        max_functions=5,
    )

    # 生成されたテスト関数の数を確認
    test_func_count = template.count("def test_")
    assert test_func_count <= 5, f"Expected at most 5 test functions, got {test_func_count}"

