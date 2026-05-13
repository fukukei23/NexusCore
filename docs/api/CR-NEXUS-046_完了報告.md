# CR-NEXUS-046: README CR エントリ品質ゲート（項目欠落・フォーマットぶれ検証）- 完了レポート

## 実装日時

2025年12月25日

## 概要

### 目的

docs/api/README.md の CR エントリの"項目欠落"と"フォーマットぶれ"を機械的に検出する。CR-NEXUS-041〜045 で Completion Report の存在・構造・内容品質とステータス整合性は担保できたが、README の各 CR ブロック自体に「目的/出力/完了レポート等の必須項目」が欠落しても検出できない状態だった。ここを品質ゲートで塞ぐ。

### ゴール

- すべての CR ブロックに「目的」と「出力」が存在し、かつ実質的に空でないことを検証
- ✅ 完了の CR ブロックに「完了レポート」が存在し、かつ実質的に空でないことを検証
- プレースホルダ（TBD、TODO、未定など）を検出して NG とする

### 原則

- Option A（軽量）で実装（README の既存フォーマットを大きく変更しない）
- 既存ヘルパー `tests/api/_readme_cr_helpers.py` を拡張して再利用（重複ロジック禁止）
- 既存テスト群（041〜045）と責務が被りすぎないように、README の"項目有無"に限定

## 実装ステップ

### Step 1: ヘルパー関数の拡張

**実施内容**:
- `tests/api/_readme_cr_helpers.py` に汎用関数を追加
- `extract_cr_field()`: CR ブロックから指定フィールドの値を抽出する汎用関数
- `is_effectively_empty()`: 値が実質的に空（空文字、空白のみ、プレースホルダのみ）かどうかを判定するユーティリティ

**実装詳細**:
- `extract_cr_field()`: `- **<field_name>**: <value>` または `**<field_name>**: <value>` の両方を許容
- `is_effectively_empty()`: 空文字、Markdown記号だけ、プレースホルダパターン（TBD、TODO、未定、後で、作成中など）を検出
- 既存関数との後方互換性を維持

### Step 2: エントリ品質ゲートテストの作成

**実施内容**:
- `tests/api/test_readme_cr_entry_quality_gate.py` を新規作成
- 2つのテストを実装：
  1. `test_readme_cr_blocks_have_required_fields()`: すべての CR ブロックに「目的」と「出力」が存在し、かつ実質的に空でないことを検証（Rule E）
  2. `test_completed_cr_blocks_have_completion_report_field()`: ステータス == "✅ 完了" の CR ブロックに「完了レポート」が存在し、かつ実質的に空でないことを検証（Rule E）

### Step 3: README の最小修正

**実施内容**:
- CR-FASTAPI-000 に「完了レポート」フィールドを追加
- テストが FAIL した箇所のみ最小限で修正

## 変更ファイル一覧

### 新規作成ファイル
- `tests/api/test_readme_cr_entry_quality_gate.py` - README CR エントリ品質ゲートテスト

### 変更ファイル
- `tests/api/_readme_cr_helpers.py` - 汎用関数の追加（`extract_cr_field`, `is_effectively_empty`）
- `docs/api/README.md` - CR-FASTAPI-000 に「完了レポート」フィールドを追加

## 動作確認結果

### テスト結果

**実行コマンド**:
```bash
python -m pytest tests/api/test_readme_cr_entry_quality_gate.py -q
python -m pytest tests/api/test_completion_reports_exist.py tests/api/test_completion_reports_for_completed_crs.py tests/api/test_completion_report_quality_gate.py tests/api/test_completion_report_content_quality_gate.py tests/api/test_readme_cr_status_quality_gate.py tests/api/test_readme_cr_entry_quality_gate.py -q
```

**結果**:
- ✅ `test_readme_cr_blocks_have_required_fields`: PASS
- ✅ `test_completed_cr_blocks_have_completion_report_field`: PASS
- ✅ 全 Completion Report 関連テスト: 11 passed

**確認項目**:
- ✅ すべての CR ブロックに「目的」と「出力」が存在し、実質的に空でない
- ✅ ✅ 完了の CR ブロックに「完了レポート」が存在し、実質的に空でない

### 静的解析結果
- リンターエラー: なし
- 型チェック: 問題なし

## 設計上の改善点

### ガバナンスの強化
1. **品質ゲートの階層化の完成**
   - CR-NEXUS-041: Completion Report 存在チェック
   - CR-NEXUS-042: Completion Report 構造（見出し）チェック
   - CR-NEXUS-044: Completion Report 内容品質チェック
   - CR-NEXUS-045: README CR ステータス整合性チェック
   - CR-NEXUS-046: README CR エントリ項目欠落チェック
   - Completion Report 運用の品質ゲートが完成

2. **責務の明確な分離**
   - 045: ステータスの正当性
   - 046: README エントリとして最低限読めること（目的/出力が埋まっていること）
   - Completion Report の中身品質は 044 が担当

### 保守性の向上
1. **ヘルパー関数の汎用化**
   - `extract_cr_field()` により、任意のフィールドを抽出可能に
   - 将来の拡張（他の必須フィールドの追加など）に対応可能な構造

2. **プレースホルダ検出**
   - `is_effectively_empty()` により、空文字やプレースホルダを統一的に検出
   - 大小文字・全半角揺れを許容して検出

## 既知の制約・注意事項

### 制約
- **ファイル**フィールドは必須化していない（README 内にある CR とない CR が混在し得るため）
- 過去 CR の大規模修正を避けるため、最小限の修正に留めた

### 注意事項
- プレースホルダ検出は簡易的なパターンマッチング（完全な意味解析ではない）
- 既存テスト（041〜045）と責務が被りすぎないように、README の"項目有無"に限定

## README 修正内容

以下の CR ブロックを修正しました：

- **CR-FASTAPI-000**: 「完了レポート」フィールドを追加

## 次のステップ

### 推奨アクション
1. **Option B の検討（将来）**
   - **ファイル**フィールドの必須化
   - その他の必須フィールドの追加

2. **プレースホルダ検出の拡張**
   - 必要に応じてプレースホルダパターンを拡張
   - README の実態に合わせて調整

## まとめ

CR-NEXUS-046 の実装により、README の CR エントリの項目欠落とフォーマットぶれを機械的に検出する仕組みが確立されました。これにより、CR-NEXUS-041〜045 と合わせて Completion Report 運用の品質ゲートが完成しました。すべてのテストが PASS し、既存の README 形式に影響を与えることなく、最小限の修正で導入できました。

