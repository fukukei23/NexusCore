# CR-NEXUS-048: README/Completion Report テンプレ自動生成（scaffold） - 完了レポート

## 実装日時

2025年12月25日

## 概要

### 目的

README と Completion Report の作成を人手で行うと、フィールド漏れ・ステータス不整合・必須見出し・内容不足・ルールに合わせた雛形の書き方が毎回ブレる問題が発生する。CR を開始する時点で、README の CR エントリ雛形と Completion Report 雛形（必須見出し＋内容品質ゲートに通る最低限の骨格）を自動生成する scaffold を追加する。

### ゴール

- `tools/scaffold_cr.py` を新規作成（CLI）
- `tests/api/test_scaffold_cr.py` を新規作成（scaffold の成果物が品質ゲート要件を満たすことを検証）
- README CR エントリと Completion Report 雛形を自動生成する機能を実装
- 品質ゲート（041〜046）の要件を満たす雛形を生成する

### 原則

- 既存挙動を変えない（必要な場合は例外理由を明記）
- テストで機械的に担保する
- scaffold は骨格のみ生成する（実内容は作業完了時に追記）

## 実装ステップ

### Step 1: scaffold CLI の実装

**実施内容**:
- `tools/scaffold_cr.py` を新規作成
- CLI インターフェースを実装：
  - 必須引数: `--cr-id`, `--title`
  - 任意引数: `--readme-path`, `--docs-dir`, `--status`, `--dry-run`
  - 終了コード: 成功=0, 入力不正=2, 既存衝突=3

**実装詳細**:
- CR-ID の解析・検証機能（`parse_cr_id`）
- README から既存 CR エントリを抽出する機能（`extract_existing_cr_entries`）
- 新しい CR エントリの挿入位置を決定する機能（`find_insert_position`）
- README CR エントリ雛形の生成（`generate_readme_entry`）
- Completion Report 雛形の生成（`generate_completion_report`）

### Step 2: 品質ゲート要件を満たす雛形の設計

**実施内容**:
- README CR エントリの固定テンプレートを実装
  - 必須フィールド（ファイル/目的/出力/ステータス）を全て含む
  - 目的/出力が実質空でない（is_effectively_empty に抵触しない）プレースホルダを使用
- Completion Report 雛形の実装
  - 必須見出し（042 の要件）を全て含む
  - 実装ステップに Step 1 を含む
  - 変更ファイル一覧にファイルパスを含む
  - 動作確認結果に証跡（pytest 実行コマンド等）を含む

**実装詳細**:
- プレースホルダ目的: "本 CR の作業内容をここに記載する（scaffold 生成）"（品質ゲートに引っかからない文）
- CR-ID の数値順で挿入位置を決定（同じ系統（NEXUS/FASTAPI）のまとまりを維持）

### Step 3: 品質ゲートテストの実装

**実施内容**:
- `tests/api/test_scaffold_cr.py` を新規作成
- scaffold の成果物が品質ゲート要件を満たすことを検証するテストを実装：
  1. README エントリが 046 の品質ゲートに抵触しない構造であること
  2. Completion Report が 042/044 の品質ゲート最小要件を満たすこと

**実装詳細**:
- `tmp_path` を使って実ファイルを汚さない
- 既存のヘルパー関数（`_readme_cr_helpers`, `_completion_report_helpers`）を再利用
- CR-ID パース、挿入順序、既存 CR-ID 検出のテストも追加

### Step 4: 冪等性の実装

**実施内容**:
- README に CR-ID が既に存在する場合：追記せず終了コード 3 を返す
- Completion Report が既に存在する場合：上書きしない（スキップして続行）
- `--dry-run` オプションでファイルを書かず、変更内容（差分）だけを表示

## 変更ファイル一覧

### 新規作成ファイル
- `tools/scaffold_cr.py` - CR 雛形生成ツール
- `tests/api/test_scaffold_cr.py` - scaffold 品質ゲートテスト

### 変更ファイル
- `docs/api/README.md` - CR エントリ追加（scaffold 生成）

## 動作確認結果

### テスト結果

**実行コマンド**:
```bash
python -m pytest tests/api/test_scaffold_cr.py -q
python -m pytest tests/api/test_completion_reports_exist.py tests/api/test_completion_reports_for_completed_crs.py tests/api/test_completion_report_quality_gate.py tests/api/test_completion_report_content_quality_gate.py tests/api/test_readme_cr_status_quality_gate.py tests/api/test_readme_cr_entry_quality_gate.py -q
```

**結果**:
- ✅ `test_scaffold_cr.py`: 6 passed
- ✅ Completion Report 関連テスト: 11 passed
- ✅ 全テスト: 17 passed

**確認項目**:
- ✅ scaffold が生成する README エントリが 046 の品質ゲートに抵触しない
- ✅ scaffold が生成する Completion Report が 042/044 の品質ゲート最小要件を満たす
- ✅ CR-ID パース機能が正常に動作
- ✅ 挿入順序が数値順になっている
- ✅ 既存 CR-ID の検出が正常に動作
- ✅ `--dry-run` オプションが正常に動作

### 静的解析結果
- リンターエラー: なし
- 型チェック: 問題なし

## 設計上の改善点

### 保守性の向上
1. **雛形の標準化**
   - README CR エントリと Completion Report の雛形が標準化され、作業ブレ・記載漏れを削減
   - 品質ゲート要件を満たす骨格を自動生成することで、品質の一貫性を確保

2. **冪等性の確保**
   - 既存 CR-ID が存在する場合は追記しない（終了コード 3）
   - Completion Report が既に存在する場合は上書きしない（スキップ）
   - `--dry-run` オプションで事前確認が可能

3. **拡張性の確保**
   - CR-ID の解析機能により、将来的に CR-ID 形式が変更されても対応可能な構造
   - ステータスの検証（045 の状態機械に準拠）により、不正なステータスの設定を防止

### 開発効率の向上
1. **作業時間の短縮**
   - CR 開始時の雛形作成作業が自動化され、作業時間を短縮
   - 品質ゲート要件を満たす雛形が自動生成されるため、後で修正する必要がなくなる

2. **品質の担保**
   - 生成された雛形が品質ゲート要件を満たすことがテストで保証される
   - 品質ゲートに抵触しない構造を保証することで、後続作業の効率化

## 既知の制約・注意事項

### 制約
- scaffold は骨格のみ生成する。実内容は作業完了時に追記する必要がある
- README の挿入位置は数値順を優先するが、既存 README の並びに倣う（最終的には既存構造優先）
- Completion Report が既に存在する場合、上書きしない（手動で削除する必要がある）

### 注意事項
- `tools/scaffold_cr.py` は `tests/api/_readme_cr_helpers.py` と `tests/api/_completion_report_helpers.py` を直接 import しない（相互 import 禁止を維持）
- scaffold ロジックは関数分離により、テストから直接使える構造になっている

## 次のステップ

### 推奨アクション
1. **scaffold の活用**
   - 新しい CR を開始する際は、scaffold を使用して雛形を生成する
   - 生成された雛形をベースに、実内容を追記する

2. **雛形の改善**
   - 実運用で得たフィードバックを反映し、雛形を改善する
   - 必要に応じて、雛形のテンプレートを更新する

## まとめ

CR-NEXUS-048 の実装により、README CR エントリと Completion Report の雛形を自動生成する scaffold が追加されました。これにより、CR 開始時の雛形作成作業が自動化され、品質ゲート要件を満たす雛形が自動生成されるようになりました。すべてのテストが PASS し、品質ゲート要件を満たすことが確認されました。
