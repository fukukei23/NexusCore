# CR-NEXUS-027: CLI UX Projection Contract 完了レポート

## 実装日時

2025-12-22

## 概要

### 目的
CLI の UX 投影を実装し、内部 RunState / Explainability を直接表示せず、RunView（投影モデル）を生成して CLI に出力する。

### ゴール
- RunState JSON の直接出力を廃止（stdout への JSON dump 禁止）
- RunView 投影モデルによる人間向け表示
- CONFLICT / FAILED / ABORTED 時に Explainability（what/why/next_action）を必ず表示
- Explainability のキー揺れ（why_code / why）を吸収
- 既存テストの動作維持

### 原則
- CLI は RunView による投影のみで、判断ロジックは Runner 正本
- Contract Layer（CR-016〜023）は一切変更しない
- authority_runner / core/orchestrator.py の実行ロジックは原則変更しない
- RunState JSON を print / dump しない（debug用途でも stdout に出さない）

## 実装ステップ

### Step 1: RunView 投影モジュールの作成

**実施内容**:
- `src/nexuscore/cli/run_view.py` を新規作成
- `build_run_view()`: Runner の戻り値（RunState + explainability）から RunView dict を生成
  - run_id, status, phase, authority_level, updated_at, explainability を抽出
- `format_run_view_cli()`: RunView を CLI 向け文字列に整形
  - ステータス別フォーマット（RUNNING / PAUSED / CONFLICT / FAILED / ABORTED）
  - Explainability の表示（what/why/next_action）
- `_format_explainability()`: Explainability のキー揺れ（why_code / why）を吸収

**結果**: ✅ 実装完了

### Step 2: CLI エントリでの RunView 表示統合

**実施内容**:
- `main_cli.py` の `run_with_authority()` と `resume_run()` の戻り値を RunView に変換
- RunState を読み込んで追加フィールド（authority_level, updated_at など）を取得
- `print(format_run_view_cli(run_view))` で投影表示
- 構文エラー（先頭行のコメント記号不足）を修正

**結果**: ✅ 実装完了

### Step 3: テスト追加

**実施内容**:
- `tests/cli/test_run_view_projection.py` を新規作成
- 8つのテストケースを追加:
  1. `test_run_view_running`: RUNNING ステータスで run_id と status が表示されることを確認 ✅
  2. `test_run_view_paused_with_phase`: PAUSED ステータスで phase と resume 指示が表示されることを確認 ✅
  3. `test_run_view_conflict_shows_explainability`: CONFLICT ステータスで Explainability が表示されることを確認 ✅
  4. `test_run_view_failed_shows_explainability`: FAILED ステータスで Explainability が表示されることを確認 ✅
  5. `test_run_view_aborted_shows_explainability`: ABORTED ステータスで Explainability が表示されることを確認 ✅
  6. `test_run_view_handles_why_code_variation`: why_code / why のキー揺れが正しく処理されることを確認 ✅
  7. `test_run_view_extracts_authority_level_from_run_state`: RunState から authority_level が正しく抽出されることを確認 ✅
  8. `test_run_view_completed_status`: completed ステータスが正しくフォーマットされることを確認 ✅

**結果**: ✅ 全テストが成功

## 変更ファイル一覧

### 新規作成ファイル
- `src/nexuscore/cli/run_view.py`: RunView 投影モジュール（build_run_view, format_run_view_cli, _format_explainability）
- `tests/cli/test_run_view_projection.py`: RunView 投影のテスト（8テストケース）

### 変更ファイル
- `main_cli.py`:
  - `run_with_authority()` と `resume_run()` の戻り値を RunView に変換して表示
  - RunState を読み込んで追加フィールドを取得
  - 構文エラー修正（先頭行のコメント記号追加）

## 動作確認結果

### テスト結果

**テスト実行コマンド**:
```bash
bash dev_tools/run_tests.sh tests/cli/test_run_view_projection.py
bash dev_tools/run_tests.sh tests/orchestrator/test_run_state_store.py
```

**結果**:
- ✅ `tests/cli/test_run_view_projection.py`: 8/8 PASS
  - 実行時間: 約 0.19 秒
  - テスト結果レポート: `test_results/TEST_RESULT_20251222_104446.md`
- ✅ `tests/orchestrator/test_run_state_store.py`: 1/1 PASS
  - 実行時間: 約 0.03 秒

**テスト結果サマリー**:
- 合計: 9 / 成功: 9 / 失敗: 0 / スキップ: 0 / エラー: 0

### 静的解析結果
- リンターエラー: なし
- 型チェック: 問題なし

## 設計上の改善点

### アーキテクチャの改善
1. **投影レイヤーの分離**
   - CLI 表示ロジックを RunView 投影モジュールに分離
   - 内部実装（RunState JSON / 契約）を CLI に露出しない

2. **Explainability の統一表示**
   - CONFLICT / FAILED / ABORTED 時に必ず Explainability を表示
   - キー揺れ（why_code / why）を吸収して統一的な表示

3. **人間向けフォーマット**
   - ステータス別の分かりやすいフォーマット
   - PAUSED 時に resume コマンドを表示

## 既知の制約・注意事項

### 制約
1. **CLI 投影のみ**: 本 CR は CLI の UX 投影のみを対象とする。API/Web UI は別 CR で扱う
2. **判断ロジック不在**: CLI は RunView による投影のみで、判断ロジックは Runner 正本に依存

### 注意事項
1. **RunState の読み込み失敗**: RunState が読み込めない場合は、result のみを使用して RunView を生成する
2. **Explainability のキー揺れ**: why_code と why の両方に対応しているが、build_explainability() は why を返すため、通常は why が使用される

## 次のステップ（推奨されるフォローアップアクション）

1. **API/Web UI への拡張**
   - API レスポンスにも RunView 投影を適用
   - Web UI での表示にも RunView を使用

2. **表示フォーマットのカスタマイズ**
   - オプションで JSON 形式の出力を追加（--json フラグなど）
   - 詳細表示モード（--verbose）の追加

## 関連ドキュメント

- CR-NEXUS-026: HMAC RunState Integrity
- CR-NEXUS-025: FS Run Lock Mode B + TTL Refresh
- CR-NEXUS-018: Resume Failure Explainability Contract

## まとめ

CR-NEXUS-027 の実装により、CLI の UX 投影が実装されました。これにより、内部 RunState / Explainability を直接表示せず、RunView（投影モデル）を生成して CLI に出力するようになりました。

主要機能は実装完了し、全テストが成功しています。RunState JSON の直接出力は廃止され、人間向けの分かりやすい表示が可能になりました。

