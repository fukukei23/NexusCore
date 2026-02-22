"""
CR ガバナンス定義（Single Source of Truth）

このモジュールは、CR（Change Request）に関するすべての定義を一元管理します。
- Completion Report の必須セクション
- README CR エントリの必須フィールド
- CR ステータスとルール
- scaffold 用テンプレート部品

制約:
- 純データのみを持ち、ロジックは禁止
- tests / tools を import してはならない
- 判定ロジック（placeholder 判定など）を書いてはならない
"""

from dataclasses import dataclass
from typing import Literal


# ============================================================================
# 1. Completion Report 定義
# ============================================================================


@dataclass
class CompletionReportSection:
    """Completion Report セクションの定義"""

    name: str  # セクション見出し文字列（Markdown 用）
    order: int  # 表示順序
    required: bool = True  # 必須かどうか
    must_not_be_empty: bool = True  # 非空必須かどうか
    placeholder_forbidden: bool = True  # プレースホルダ禁止かどうか
    evidence_required: bool = False  # 証跡（pytest 実行結果など）必須かどうか
    min_steps_required: int = 0  # 最低要件（例：実装ステップ数が 1 以上）
    requires_file_paths: bool = False  # ファイルパス表記が必須かどうか


# Completion Report 必須セクション一覧（順序あり）
COMPLETION_REPORT_SECTIONS = [
    CompletionReportSection(
        name="実装日時",
        order=1,
        required=True,
        must_not_be_empty=True,
        placeholder_forbidden=True,
    ),
    CompletionReportSection(
        name="概要",
        order=2,
        required=True,
        must_not_be_empty=True,
        placeholder_forbidden=True,
    ),
    CompletionReportSection(
        name="実装ステップ",
        order=3,
        required=True,
        must_not_be_empty=True,
        placeholder_forbidden=True,
        min_steps_required=1,  # Step が 1 つ以上必要
    ),
    CompletionReportSection(
        name="変更ファイル一覧",
        order=4,
        required=True,
        must_not_be_empty=True,
        placeholder_forbidden=True,
        requires_file_paths=True,  # ファイルパス表記が必須
    ),
    CompletionReportSection(
        name="動作確認結果",
        order=5,
        required=True,
        must_not_be_empty=True,
        placeholder_forbidden=True,
        evidence_required=True,  # 証跡（実行コマンドなど）必須
    ),
    CompletionReportSection(
        name="設計上の改善点",
        order=6,
        required=True,
        must_not_be_empty=True,
        placeholder_forbidden=True,
    ),
    CompletionReportSection(
        name="既知の制約・注意事項",
        order=7,
        required=True,
        must_not_be_empty=True,
        placeholder_forbidden=True,
    ),
    CompletionReportSection(
        name="次のステップ",
        order=8,
        required=True,
        must_not_be_empty=True,
        placeholder_forbidden=True,
    ),
]


# ============================================================================
# 2. README CR エントリ定義
# ============================================================================


# README CR エントリ必須フィールド一覧
README_CR_REQUIRED_FIELDS = [
    "ファイル",
    "目的",
    "出力",
    "ステータス",
]

# 許容ステータス一覧（README 表記と一致させる）
ALLOWED_STATUSES = [
    "📝 計画中",
    "🚧 実装中",
    "⏳ 進行中",
    "✅ 完了",
    "⏸ 保留",
    "❌ 中断",
]

# ステータス別ルール
STATUS_RULES = {
    "✅ 完了": {
        "completion_report_required": True,  # Completion Report 必須
        "reason_required": False,
    },
    "⏸ 保留": {
        "completion_report_required": False,
        "reason_required": True,  # 理由必須
    },
    "❌ 中断": {
        "completion_report_required": False,
        "reason_required": True,  # 理由必須
    },
}


# ============================================================================
# 3. scaffold 用テンプレート部品
# ============================================================================

# README CR エントリ雛形のフィールド順序（定義順）
README_ENTRY_FIELD_ORDER = [
    "ファイル",
    "目的",
    "出力",
    "ステータス",
    "完了レポート",  # ステータスが「✅ 完了」の場合のみ
]

# scaffold 用プレースホルダ（実質空判定に引っかからない文）
SCAFFOLD_PLACEHOLDERS = {
    "purpose": "本 CR の作業内容をここに記載する（scaffold 生成）",
    "goal": "本 CR のゴールをここに列挙する（scaffold 生成）",
    "principle": "既存挙動を変えない（必要な場合は例外理由を明記）\n- テストで機械的に担保する",
    "step_description": "何を変更したか（scaffold 生成）",
    "step_reason": "なぜ変更したか（scaffold 生成）",
    "validation_command": "python -m pytest tests/api/test_scaffold_cr.py -q",
    "validation_result": "- ✅ 全テスト PASS（scaffold 生成：ここに PASS/FAIL の証跡を記載）",
    "completion_report_not_created": "（未作成）",
}

# Completion Report 雛形のセクション構造（定義から組み立て可能）
COMPLETION_REPORT_TEMPLATE_STRUCTURE = {
    "title_suffix": " - 完了レポート",
    "sections": [
        {"name": "実装日時", "placeholder": "{date}"},
        {"name": "概要", "subsections": ["目的", "ゴール", "原則"]},
        {"name": "実装ステップ", "has_steps": True, "step_count": 1},
        {"name": "変更ファイル一覧", "has_file_paths": True},
        {"name": "動作確認結果", "has_evidence": True},
        {"name": "設計上の改善点"},
        {"name": "既知の制約・注意事項"},
        {"name": "次のステップ"},
    ],
}
