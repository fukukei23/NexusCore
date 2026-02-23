"""
SDK 生成スクリプトの安全性テスト

tools/generate_sdk.py が壊れていないことを確認する軽量テスト。
実際の SDK 生成は行わず、import と基本的な関数呼び出しのみを検証する。
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# プロジェクトルートを取得
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))


def test_generate_sdk_import():
    """tools/generate_sdk.py が正常に import できることを確認する"""
    try:
        import generate_sdk  # noqa: F401
    except ImportError as e:
        pytest.fail(f"Failed to import generate_sdk: {e}")


def test_generate_sdk_help_runs():
    """--help オプションが正常に動作することを確認する"""
    import generate_sdk

    # argparse の help 表示は SystemExit(0) を投げるため、それを捕捉
    with pytest.raises(SystemExit) as exc_info:
        with patch("sys.argv", ["generate_sdk.py", "--help"]):
            generate_sdk.main()

    # SystemExit(0) は正常終了を示す
    assert exc_info.value.code == 0


def test_check_openapi_generator_mocked():
    """check_openapi_generator() が正常に動作することを確認する（subprocess はモック）"""
    import generate_sdk

    # npx 経由の openapi-generator-cli が利用可能な場合をモック
    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "7.2.0"
        mock_run.return_value = mock_result

        is_available, generator_cmd = generate_sdk.check_openapi_generator()

        # モックが呼ばれたことを確認
        assert mock_run.called
        # 結果が返されることを確認（モックのため、実際の値は環境依存）
        assert isinstance(is_available, bool)
        assert generator_cmd is None or isinstance(generator_cmd, str)


def test_check_openapi_generator_not_available():
    """check_openapi_generator() が openapi-generator が見つからない場合を正しく処理することを確認する"""
    import generate_sdk

    # すべての subprocess.run が FileNotFoundError を投げる場合をモック
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError("Command not found")

        is_available, generator_cmd = generate_sdk.check_openapi_generator()

        # 利用不可と判定されることを確認
        assert is_available is False
        assert generator_cmd is None


def test_generate_sdk_module_has_required_functions():
    """generate_sdk モジュールに必要な関数が存在することを確認する"""
    import generate_sdk

    # 必要な関数が存在することを確認
    assert hasattr(generate_sdk, "check_openapi_generator")
    assert hasattr(generate_sdk, "fetch_openapi_spec")
    assert hasattr(generate_sdk, "generate_python_sdk")
    assert hasattr(generate_sdk, "generate_typescript_sdk")
    assert hasattr(generate_sdk, "verify_generated_sdk")
    assert hasattr(generate_sdk, "main")

    # 関数が呼び出し可能であることを確認
    assert callable(generate_sdk.check_openapi_generator)
    assert callable(generate_sdk.fetch_openapi_spec)
    assert callable(generate_sdk.generate_python_sdk)
    assert callable(generate_sdk.generate_typescript_sdk)
    assert callable(generate_sdk.verify_generated_sdk)
    assert callable(generate_sdk.main)
