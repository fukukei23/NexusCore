"""
test_generator_prompt.py

AI テスト生成用のプロンプトテンプレート。

tester_agent が LLM にテスト生成を依頼する際の
プロンプトテンプレートを提供します。
"""

from __future__ import annotations


def build_test_generation_prompt(
    target_file_path: str,
    target_code: str,
    existing_tests: str | None = None,
    test_level: str = "unit",  # "unit" | "component" | "e2e"
    risk_level: str = "B",  # "S" | "A" | "B"
    strategy: str = "ai_first_only",
    requirements: list[str] | None = None,
    min_coverage: int = 60,
    module_name: str | None = None,
    additional_requirements: str | None = None,
) -> str:
    """
    テスト生成用のプロンプトを組み立てる。

    Args:
        target_file_path: 対象ファイルのパス
        target_code: 対象ファイルのコード
        existing_tests: 既存のテストコード（あれば）
        test_level: テストレベル（"unit" | "component" | "e2e"）
        risk_level: リスクランク（"S" | "A" | "B"）
        strategy: テスト生成戦略
        requirements: 追加の要件・懸念事項（自然文のリスト）
        min_coverage: 目標カバレッジ（%）
        module_name: モジュール名（webapp. で始まる場合はHTTP/Flask向けの指示を追加）
        additional_requirements: 追加の要件（文字列）

    Returns:
        LLM に送るプロンプト文字列
    """
    lines = [
        "# テスト生成タスク",
        "",
        "## 対象ファイル",
        f"`{target_file_path}`",
        "",
        "## 対象コード",
        "```python",
        target_code,
        "```",
        "",
    ]

    # 既存テストがあれば追加
    if existing_tests:
        lines.extend(
            [
                "## 既存テスト",
                "```python",
                existing_tests,
                "```",
                "",
            ]
        )

    # テストレベルに応じた指示
    test_level_instructions = {
        "unit": """
## テストレベル: ユニットテスト

以下の観点でテストを生成してください：
- 各関数の入出力の検証
- エッジケース（空文字列、None、境界値など）
- 例外処理の確認
- 戻り値の型と内容の検証

外部依存（LLM API、ファイルシステム、サブプロセス）はモック化してください。
""",
        "component": """
## テストレベル: コンポーネントテスト

以下の観点でテストを生成してください：
- モジュール全体の振る舞いの検証
- 外部依存（LLM API、ファイルシステム、サブプロセス）をモック化
- エラーハンドリングの確認
- 状態遷移の確認（あれば）

モックは適切に設定し、実装の詳細に依存しすぎないようにしてください。
""",
        "e2e": """
## テストレベル: E2E / シナリオテスト

以下の観点でテストを生成してください：
- 典型的なユーザーフローの確認
- エンドツーエンドのワークフローの検証
- 統合的な動作の確認

実際の外部依存を使う場合は、テスト環境を適切に設定してください。
""",
    }

    lines.append(test_level_instructions.get(test_level, test_level_instructions["unit"]))
    lines.append("")

    # リスクランクに応じた指示
    risk_instructions = {
        "S": """
## ⚠️ 重要: クリティカルモジュール

このモジュールは **クリティカル** なため、以下の点を特に注意してください：
- 安全性に関するテストを必ず含める
- エッジケースを網羅的にカバーする
- 例外処理のテストを充実させる
- 境界値テストを必ず含める

生成後、人間によるレビューが必須です。
""",
        "A": """
## 重要: 重要モジュール

このモジュールは **重要** なため、以下の点を注意してください：
- 主要な機能のテストを網羅する
- エッジケースを適切にカバーする
- 例外処理のテストを含める

生成後、人間によるレビューを推奨します。
""",
        "B": """
## 非クリティカルモジュール

このモジュールは非クリティカルなため、基本的なテストを生成してください。
重大なバグを検出できる程度のテストで十分です。
""",
    }

    lines.append(risk_instructions.get(risk_level, risk_instructions["B"]))
    lines.append("")

    # Web/API モジュール向けの特別な指示
    is_webapp_module = module_name is not None and module_name.startswith("webapp.")
    webapp_instructions = ""
    if is_webapp_module:
        webapp_instructions = """
## Web/API テストの特別な要件

このモジュールは Flask アプリケーションの Web/API レイヤーです。以下の点を特に注意してください：

- Flask アプリケーションのテストであることを想定してください
- HTTP エンドポイントに対するテストクライアント（Flaskの `test_client()` または既存のテストユーティリティ）を利用してください
- 認証が必要なエンドポイントについては、認証済み / 非認証の両方のパターンをテストしてください
- ステータスコード（200, 401, 403, 404, 500 など）、レスポンスボディ、権限エラー（401/403）も検証してください
- 異常系（存在しないリソースID、権限のないユーザーによるアクセス、不正なリクエストボディなど）も最低1ケース以上含めてください
- セッション管理やクッキーのテストも必要に応じて含めてください
"""
        lines.append(webapp_instructions)
        lines.append("")

    # 追加要件があれば追加
    if additional_requirements:
        lines.append("## 追加要件")
        lines.append(additional_requirements)
        lines.append("")

    if requirements:
        lines.append("## 追加要件・懸念事項")
        for i, req in enumerate(requirements, 1):
            lines.append(f"{i}. {req}")
        lines.append("")

    # カバレッジ目標
    lines.extend(
        [
            "## 目標カバレッジ",
            f"{min_coverage}% 以上を目指してください。",
            "",
        ]
    )

    # 出力形式
    lines.extend(
        [
            "## 出力形式",
            "",
            "以下の形式で pytest テストコードを生成してください：",
            "",
            "```python",
            f"# tests/test_{target_file_path.replace('/', '_').replace('.py', '')}.py",
            "",
            "import pytest",
            "from unittest.mock import Mock, patch, MagicMock",
            "",
            "# テストコードをここに記述",
            "```",
            "",
            "## 注意事項",
            "",
            "- `time.sleep` は使わない",
            "- 外部API依存は必ずモック化",
            "- ランダム値は固定する",
            "- 実ファイル削除は行わない（tmp_path を使用）",
            "- 実行時間は短く（〜500ms）",
            "- 1テスト = 1責務",
            "- 公開APIに対するテスト",
            "- 内部実装に依存しない",
            "",
        ]
    )

    return "\n".join(lines)


def build_specification_based_test_prompt(
    module_name: str,
    specifications: list[str],
    existing_code: str | None = None,
) -> str:
    """
    仕様ベースのテスト生成用プロンプトを組み立てる。

    開発者が自然文で書いた仕様・懸念・エッジケースから
    テストを生成するためのプロンプトです。

    Args:
        module_name: モジュール名
        specifications: 仕様・懸念・エッジケースのリスト（自然文）
        existing_code: 既存のコード（あれば）

    Returns:
        LLM に送るプロンプト文字列
    """
    lines = [
        "# 仕様ベーステスト生成タスク",
        "",
        "## 対象モジュール",
        f"`{module_name}`",
        "",
    ]

    if existing_code:
        lines.extend(
            [
                "## 既存コード",
                "```python",
                existing_code,
                "```",
                "",
            ]
        )

    lines.extend(
        [
            "## 仕様・懸念・エッジケース",
            "",
            "以下の仕様・懸念・エッジケースが **破られていないこと** を確認する",
            "pytest テストを生成してください：",
            "",
        ]
    )

    for i, spec in enumerate(specifications, 1):
        lines.append(f"{i}. {spec}")

    lines.extend(
        [
            "",
            "## 出力形式",
            "",
            "各仕様項目について、以下の形式でテストを生成してください：",
            "",
            "```python",
            "def test_<仕様の要約>():",
            '    """',
            "    仕様: <元の仕様文>",
            '    """',
            "    # テストコード",
            "    assert ...",
            "```",
            "",
            "## 注意事項",
            "",
            "- 仕様の意図を正確に反映したテストを書く",
            "- 仕様が破られた場合にテストが失敗することを確認する",
            "- エッジケースも適切にカバーする",
            "- テストは明確で読みやすいものにする",
            "",
        ]
    )

    return "\n".join(lines)
