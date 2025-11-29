"""
semantic_diff の基本テスト

軽量スモークテストで、基本的な機能が動作することを確認する。
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    from nexuscore.diff.semantic_diff import (
        compute_semantic_diff,
        SemanticDiffResult,
        FunctionChange,
    )
    HAS_SEMANTIC_DIFF = True
except ImportError:
    HAS_SEMANTIC_DIFF = False
    compute_semantic_diff = None  # type: ignore
    SemanticDiffResult = None  # type: ignore
    FunctionChange = None  # type: ignore


@pytest.mark.skipif(not HAS_SEMANTIC_DIFF, reason="semantic_diff module not available")
def test_semantic_diff_detects_added_function(tmp_path: Path) -> None:
    """追加された関数を検出できることを確認"""
    before = "def foo(x):\n    return x\n"
    after = before + "\n\ndef bar(y):\n    return y * 2\n"
    file_path = tmp_path / "sample.py"

    result = compute_semantic_diff(file_path, before, after, language="python")

    assert isinstance(result, SemanticDiffResult)
    assert result.file_path == file_path

    # 関数の変更を確認
    names_kinds = {(f.name, f.kind) for f in result.functions}
    assert ("bar", "added") in names_kinds
    assert ("foo", "added") in names_kinds or ("foo", "modified") in names_kinds


@pytest.mark.skipif(not HAS_SEMANTIC_DIFF, reason="semantic_diff module not available")
def test_semantic_diff_detects_removed_function(tmp_path: Path) -> None:
    """削除された関数を検出できることを確認"""
    before = "def foo(x):\n    return x\n\ndef bar(y):\n    return y * 2\n"
    after = "def foo(x):\n    return x\n"
    file_path = tmp_path / "sample.py"

    result = compute_semantic_diff(file_path, before, after, language="python")

    names_kinds = {(f.name, f.kind) for f in result.functions}
    assert ("bar", "removed") in names_kinds


@pytest.mark.skipif(not HAS_SEMANTIC_DIFF, reason="semantic_diff module not available")
def test_semantic_diff_detects_modified_function(tmp_path: Path) -> None:
    """シグネチャが変更された関数を検出できることを確認"""
    before = "def foo(x):\n    return x\n"
    after = "def foo(x, y=0):\n    return x + y\n"
    file_path = tmp_path / "sample.py"

    result = compute_semantic_diff(file_path, before, after, language="python")

    names_kinds = {(f.name, f.kind) for f in result.functions}
    assert ("foo", "modified") in names_kinds

    # シグネチャの変更を確認
    foo_change = next((f for f in result.functions if f.name == "foo" and f.kind == "modified"), None)
    assert foo_change is not None
    assert foo_change.signature_before is not None
    assert foo_change.signature_after is not None
    assert foo_change.signature_before != foo_change.signature_after


@pytest.mark.skipif(not HAS_SEMANTIC_DIFF, reason="semantic_diff module not available")
def test_semantic_diff_detects_behavior_hints(tmp_path: Path) -> None:
    """振る舞いの変化ヒントを検出できることを確認"""
    before = "def foo(x):\n    return x\n"
    after = "def foo(x):\n    if x < 0:\n        raise ValueError('x must be non-negative')\n    return x\n"
    file_path = tmp_path / "sample.py"

    result = compute_semantic_diff(file_path, before, after, language="python")

    # raise が追加されたので、例外パス追加のヒントがあるはず
    hint_descriptions = [h.description for h in result.behavior_hints]
    assert any("例外" in desc or "raise" in desc.lower() for desc in hint_descriptions)


@pytest.mark.skipif(not HAS_SEMANTIC_DIFF, reason="semantic_diff module not available")
def test_semantic_diff_handles_parse_error_gracefully(tmp_path: Path) -> None:
    """パースエラーが発生しても例外を投げずに結果を返すことを確認"""
    before = "def foo(x):\n    return x\n"
    after = "def foo(x\n    return x\n"  # シンタックスエラー
    file_path = tmp_path / "sample.py"

    # 例外が投げられないことを確認
    result = compute_semantic_diff(file_path, before, after, language="python")

    assert isinstance(result, SemanticDiffResult)
    # raw_line_diff_summary は埋まっているはず
    assert result.raw_line_diff_summary is not None or len(result.raw_line_diff_summary or "") > 0


@pytest.mark.skipif(not HAS_SEMANTIC_DIFF, reason="semantic_diff module not available")
def test_semantic_diff_to_dict(tmp_path: Path) -> None:
    """to_dict() メソッドが正しく動作することを確認"""
    before = "def foo(x):\n    return x\n"
    after = before + "\n\ndef bar(y):\n    return y * 2\n"
    file_path = tmp_path / "sample.py"

    result = compute_semantic_diff(file_path, before, after, language="python")
    result_dict = result.to_dict()

    assert isinstance(result_dict, dict)
    assert "file_path" in result_dict
    assert "functions" in result_dict
    assert "behavior_hints" in result_dict
    assert isinstance(result_dict["functions"], list)
    assert isinstance(result_dict["behavior_hints"], list)

