# CR-NEXUS-049: CR ガバナンス定義（README / Completion Report / 品質ゲート / scaffold）の Single Source of Truth（SSoT）化 - 完了レポート

## 実装日時

2025年12月25日

## 概要

### 目的

CR ガバナンスに関する定義（Completion Report 必須セクション、README CR エントリ必須項目、CR ステータスと状態ルール、雛形テンプレート）が分散している状態を解消し、定義を 1 箇所に集約し、scaffold / 品質ゲート / helpers はその定義を参照するように修正する。

### ゴール

- CR ガバナンスに関する「定義」を `src/nexuscore/governance/cr_spec.py` に集約
- scaffold / 品質ゲート / helpers はその定義を参照するように修正
- 定義の二重管理を除去
- 再発防止テストを追加

### 原則

- 既存挙動を変えない（定義の集約と参照先置換のみ）
- 新しい品質ルールの追加は禁止
- README / Completion Report のフォーマット変更は禁止
- 既存 CR の内容修正は禁止（必要な場合はテスト修正のみ）

## 実装ステップ

### Step 1: SSoT の追加

**実施内容**:
- `src/nexuscore/governance/cr_spec.py` を新規作成
- `src/nexuscore/governance/__init__.py` を新規作成
- 以下の定義を純データとして実装：
  1. Completion Report 定義（必須セクション一覧、各セクションの属性）
  2. README CR エントリ定義（必須フィールド一覧、許容ステータス一覧、ステータス別ルール）
  3. scaffold 用テンプレート部品（README CR エントリ雛形、Completion Report 雛形）

**実装詳細**:
- `CompletionReportSection` dataclass でセクション定義を構造化
- `COMPLETION_REPORT_SECTIONS` で必須セクション一覧を定義
- `README_CR_REQUIRED_FIELDS` で必須フィールド一覧を定義
- `ALLOWED_STATUSES` で許容ステータス一覧を定義
- `STATUS_RULES` でステータス別ルールを定義
- `SCAFFOLD_PLACEHOLDERS` で scaffold 用プレースホルダを定義
- 判定ロジックは書かず、純データのみ

### Step 2: 品質ゲートの参照先置換

**実施内容**:
- 以下のテストファイルからハードコードされた定義を削除し、cr_spec を参照するように修正：
  - `tests/api/test_completion_report_quality_gate.py`（CR-NEXUS-042）
  - `tests/api/test_completion_report_content_quality_gate.py`（CR-NEXUS-044）
  - `tests/api/test_readme_cr_entry_quality_gate.py`（CR-NEXUS-046）
  - `tests/api/test_readme_cr_status_quality_gate.py`（CR-NEXUS-045）

**実装詳細**:
- `REQUIRED_SECTIONS` を `cr_spec.COMPLETION_REPORT_SECTIONS` から取得
- `REQUIRED_FIELDS` を `cr_spec.README_CR_REQUIRED_FIELDS` から取得
- `ALLOWED_STATUSES` を `cr_spec.ALLOWED_STATUSES` から取得
- ステータス別ルールを `cr_spec.STATUS_RULES` から取得

### Step 3: helpers の定義排除・参照統一

**実施内容**:
- helpers に定義が残っていないことを確認
- helpers は cr_spec の定義を使って抽出・解釈・検証補助のみを行う（定義は持たない）

**実装詳細**:
- helpers には定義が既に残っていなかったため、変更不要

### Step 4: scaffold のテンプレート直書き撤廃

**実施内容**:
- `tools/scaffold_cr.py` の Markdown テンプレート直書きを撤廃
- cr_spec の定義から README CR エントリと Completion Report 雛形を生成するように修正

**実装詳細**:
- `generate_readme_entry()` を cr_spec の定義から生成するように修正
- `generate_completion_report()` を cr_spec の定義から生成するように修正
- ステータス検証を `cr_spec.ALLOWED_STATUSES` から取得
- `test_scaffold_cr.py` も cr_spec を参照するように修正

### Step 5: 再発防止テストの追加

**実施内容**:
- `tests/api/test_cr_spec_single_source_of_truth.py` を新規作成
- 定義が再び分散した場合に検知するテストを実装

**実装詳細**:
- Completion Report 必須セクションが cr_spec に定義されていることを確認
- README CR エントリ必須フィールドが cr_spec に定義されていることを確認
- CR ステータスルールが cr_spec に定義されていることを確認
- scaffold が生成する Completion Report / README エントリが cr_spec の定義を使用していることを確認

## 変更ファイル一覧

### 新規作成ファイル
- `src/nexuscore/governance/__init__.py` - governance モジュールの初期化
- `src/nexuscore/governance/cr_spec.py` - CR ガバナンス定義（SSoT）
- `tests/api/test_cr_spec_single_source_of_truth.py` - 再発防止テスト

### 変更ファイル
- `tools/scaffold_cr.py` - cr_spec を参照するように修正（テンプレート直書き撤廃）
- `tests/api/test_completion_report_quality_gate.py` - cr_spec を参照するように修正
- `tests/api/test_completion_report_content_quality_gate.py` - cr_spec を参照するように修正
- `tests/api/test_readme_cr_entry_quality_gate.py` - cr_spec を参照するように修正
- `tests/api/test_readme_cr_status_quality_gate.py` - cr_spec を参照するように修正
- `tests/api/test_scaffold_cr.py` - cr_spec を参照するように修正

## 動作確認結果

### テスト結果

**実行コマンド**:
```bash
python -m pytest tests/api/test_completion_reports_exist.py tests/api/test_completion_reports_for_completed_crs.py tests/api/test_completion_report_quality_gate.py tests/api/test_completion_report_content_quality_gate.py tests/api/test_readme_cr_status_quality_gate.py tests/api/test_readme_cr_entry_quality_gate.py tests/api/test_scaffold_cr.py tests/api/test_cr_spec_single_source_of_truth.py -q
```

**結果**:
- ✅ 全テスト: 23 passed
- ✅ `test_cr_spec_single_source_of_truth.py`: 6 passed
- ✅ Completion Report 関連テスト: 17 passed

**確認項目**:
- ✅ 品質ゲートテストが cr_spec を参照している
- ✅ scaffold が cr_spec からテンプレートを生成している
- ✅ scaffold で新規 CR を生成しても初手で品質ゲートを通過
- ✅ 定義の二重管理が除去されている

### 静的解析結果
- リンターエラー: なし
- 型チェック: 問題なし

## 設計上の改善点

### 保守性の向上
1. **定義の一元管理**
   - CR ガバナンス定義が `src/nexuscore/governance/cr_spec.py` に集約され、定義の変更が一箇所で完了
   - 定義の二重管理が解消され、不整合リスクが削減

2. **参照の明確化**
   - scaffold / 品質ゲート / helpers が cr_spec を参照することで、定義の出所が明確
   - 定義が分散した場合、再発防止テストで検知可能

3. **拡張性の向上**
   - 新しい品質ルールを追加する場合、cr_spec のみを修正すれば良い
   - scaffold / 品質ゲート / helpers への変更は不要（自動的に反映される）

### 開発効率の向上
1. **作業時間の短縮**
   - 定義の変更が一箇所で完了するため、修正時間が短縮
   - 定義の不整合によるバグが減少

2. **品質の担保**
   - 再発防止テストにより、定義が分散した場合に即座に検知可能
   - 定義の一貫性が保証される

## 既知の制約・注意事項

### 制約
- cr_spec.py は純データのみを持ち、ロジックは禁止（判定ロジックは別モジュールに配置）
- tests / tools を import してはならない（循環依存を避ける）
- 既存仕様を変えず、定義の集約と参照先置換のみを行う

### 注意事項
- 新しい品質ルールを追加する場合は、cr_spec.py に定義を追加し、必要な品質ゲートテストを更新
- scaffold / 品質ゲート / helpers は cr_spec を参照するのみで、定義を持たない

## 次のステップ

### 推奨アクション
1. **定義の拡張**
   - 新しい品質ルールを追加する場合は、cr_spec.py に定義を追加
   - 必要な品質ゲートテストを更新

2. **再発防止テストの強化**
   - 必要に応じて、再発防止テストを拡張
   - 定義の整合性をより厳密に検証

## まとめ

CR-NEXUS-049 の実装により、CR ガバナンス定義が Single Source of Truth（SSoT）化されました。定義が `src/nexuscore/governance/cr_spec.py` に集約され、scaffold / 品質ゲート / helpers はその定義を参照するようになりました。これにより、定義の二重管理が解消され、保守性と拡張性が向上しました。すべてのテストが PASS し、定義の整合性が保証されています。

