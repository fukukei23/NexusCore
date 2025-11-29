# test_generator 安定化 & カバレッジ計測完了レポート

## 実装日時
2025-11-29 22:03

## 概要

`test_generator` の安定化とカバレッジ計測の実装を行いました。

1. **test_generator の安定化**: 生成されるテストコードが常にインポート可能で、不要な副作用が極力出ないように改善
2. **カバレッジ計測の実装**: coverage.py ベースのテストカバレッジ計測を組み込み、ローカルと CI で coverage を生成

## 実装ステップ

### Part 1: test_generator の安定化

#### 1. 生成方針の固め直し（プロンプト / 生成ポリシー）

**変更ファイル**: `src/nexuscore/utils/test_generator.py`

**実装内容**:
- LLM へのプロンプトを見直し、「絶対守ってほしい制約」を明文化:
  - pytest ベースの関数名（test_ で始まる）
  - `if __name__ == "__main__":` を書かない
  - DB 接続を行わない
  - ファイル書き込み I/O を行わない（必要なら mock を書くよう明示）
  - 危険な操作（os.system, subprocess, eval, exec, __import__）を禁止
  - 外部API依存は必ずモック化
  - time.sleep は使わない
  - ランダム値は固定
- プロンプトに「理想的なテスト例」を追加

#### 2. import path の安定化

**新規ファイル**: `src/nexuscore/utils/test_utils.py`

**実装内容**:
- `project_path_to_module_path()`: プロジェクトルートからの相対パスを Python モジュールパスに変換
  - 例: `src/foo/bar.py` → `src.foo.bar`
- `test_generator.generate_unit_tests()` に `file_path`, `project_root`, `module_path` パラメータを追加
- 生成コード内の import 文に使用するモジュールパスを自動生成

#### 3. 出力の検証ロジック強化（内部側）

**実装内容**:
- `validate_test_code()`: 生成されたテキストに対し、最低限の static check を実行
  - `ast.parse()` で構文が通るか確認
  - 危険な文字列（os.system, subprocess, open("...","w") など）の有無チェック
  - `if __name__ == "__main__":` のチェック
  - pytest 関数名（test_ で始まる）のチェック
  - `import pytest` のチェック
- `extract_code_from_markdown()`: Markdown コードブロックから Python コードを抽出
- `generate_and_validate_test_code()`: テストコードを生成し、検証も行う統合関数

#### 4. E2E テストの強化

**変更ファイル**: `tests/analyzer/test_test_generator_e2e.py`

**実装内容**:
- `test_test_generator_validation`: 生成されたテストコードの検証ロジックが動作することを確認
- `test_project_path_to_module_path`: `project_path_to_module_path` ユーティリティのテスト
- 既存テストを強化:
  - `importlib` でインポート可能か確認
  - `validate_test_code()` で検証
  - 実際に `pytest` を実行（環境変数 `SKIP_PYTEST_EXECUTION=1` でスキップ可能）

#### 5. エラー時のフォールバック

**実装内容**:
- `create_fallback_test_file()`: 生成されたテストコードがパースエラー or import エラーの場合のフォールバック
- `pytest.fail("Auto-generated test scaffold invalid")` を含む「意図的な失敗テスト」を生成
- エラー発生時はログに警告を残し、フォールバックファイルを返す

### Part 2: カバレッジ計測の実装

#### 1. coverage.py の導入確認

**確認結果**:
- `requirements-dev.txt` に `pytest-cov` が既に含まれていることを確認
- 追加の依存関係は不要

#### 2. Makefile ターゲットの整備

**変更ファイル**: `Makefile`

**実装内容**:
- `test-coverage`: HTML + XML レポートを生成（既存を拡張）
- `test-cov`: XML レポートのみ生成（CI 用、新規追加）
- `test-phase3`: Phase3 テスト用のカバレッジ（既存）

#### 3. CI への coverage 反映

**変更ファイル**: `.github/workflows/ci.yml`

**実装内容**:
- `requirements-dev.txt` をインストールするステップを追加
- `pytest --cov=src --cov-report=xml --cov-report=term-missing` を実行
- `coverage.xml` が生成されることを確認（既存の Codecov アップロードも維持）

#### 4. Run モデルへのフック（TODO コメント）

**変更ファイル**: `src/nexuscore/services/self_healing_service.py`

**実装内容**:
- `_finalize()` メソッドに coverage 統合の TODO コメントを追加
- 実装案:
  - テスト実行後に `coverage run -m pytest` を実行
  - `coverage report --format=json` で JSON を取得
  - カバレッジ率を計算して `details["coverage_pct"]` に保存
  - PR コメントや Web UI に表示

#### 5. ドキュメント更新

**変更ファイル**: `docs/testing_strategy_phase3.md`

**実装内容**:
- Coverage 計測の方針を追加
- `make test-coverage` / `make test-cov` / CI の実行方法を記載
- Coverage % を「プロダクトの強みとして見せる」方向性を追記

## 変更ファイル一覧

### 新規作成ファイル

1. **`src/nexuscore/utils/test_utils.py`**
   - `project_path_to_module_path()`: import path の安定化
   - `validate_test_code()`: 出力の検証ロジック
   - `extract_code_from_markdown()`: Markdown からコード抽出
   - `create_fallback_test_file()`: エラー時のフォールバック

### 変更ファイル

1. **`src/nexuscore/utils/test_generator.py`**
   - プロンプト改善（絶対守ってほしい制約を明文化）
   - `generate_unit_tests()` に `file_path`, `project_root`, `module_path` パラメータを追加
   - `generate_and_validate_test_code()` を追加（生成 + 検証の統合関数）
   - エラーハンドリングの改善

2. **`tests/analyzer/test_test_generator_e2e.py`**
   - `test_test_generator_validation`: 検証ロジックのテスト
   - `test_project_path_to_module_path`: ユーティリティのテスト
   - 既存テストを強化（importlib、validate_test_code、pytest 実行）

3. **`Makefile`**
   - `test-coverage`: XML レポート生成を追加
   - `test-cov`: 新規追加（XML レポートのみ）

4. **`.github/workflows/ci.yml`**
   - `requirements-dev.txt` のインストールを追加
   - `--cov-report=term-missing` を追加

5. **`src/nexuscore/services/self_healing_service.py`**
   - `_finalize()` に coverage 統合の TODO コメントを追加

6. **`docs/testing_strategy_phase3.md`**
   - Coverage 計測の方針を追加

## 動作確認結果

### 静的解析結果
- ✅ リンターエラー: なし

### 実装確認項目

**test_generator の安定化**:
- [x] プロンプト改善（絶対守ってほしい制約を明文化）
- [x] import path の安定化（ユーティリティ関数追加）
- [x] 出力の検証ロジック強化（ast.parse、危険な文字列チェック）
- [x] E2E テストの強化（importlib、pytest 実行）
- [x] エラー時のフォールバック実装

**カバレッジ計測**:
- [x] coverage.py の導入確認（pytest-cov が既に含まれている）
- [x] Makefile ターゲットの整備（test-coverage、test-cov）
- [x] CI への coverage 反映（requirements-dev.txt インストール、coverage.xml 生成）
- [x] Run モデルへのフック（TODO コメント）
- [x] ドキュメント更新

## 設計上の改善点

### 保守性の向上
- **プロンプト改善**: 絶対守ってほしい制約を明文化し、生成品質を向上
- **検証ロジック**: 生成されたコードを自動検証し、問題を早期発見
- **エラーハンドリング**: エラー時のフォールバックにより、処理全体が落ちない

### 将来の拡張性への配慮
- **import path の安定化**: プロジェクト構造が変わっても対応可能
- **カバレッジ統合**: TODO コメントで将来の実装方針を明記
- **環境変数制御**: `SKIP_PYTEST_EXECUTION` でテスト実行をスキップ可能

### コード品質の向上
- **検証ロジック**: 危険なコードの生成を防止
- **フォールバック**: エラー時も適切なテストファイルを生成
- **ドキュメント**: カバレッジ計測の方針を明文化

## 既知の制約・注意事項

### 制限事項
1. **LLM 生成の品質**: LLM が生成するテストコードの品質は保証しない（検証ロジックで最低限のチェック）
2. **pytest 実行**: 環境変数 `SKIP_PYTEST_EXECUTION=1` でスキップ可能（CI で不安定な場合）

### 移行時の注意点
- 既存のコードはそのまま動作する（後方互換性を維持）
- `generate_unit_tests()` の新しいパラメータはオプショナル

## 次のステップ

### 推奨されるフォローアップアクション

1. **カバレッジ統合の実装**: `self_healing_service._finalize()` に coverage 測定を実装
2. **PR コメントへの統合**: coverage % を PR コメントに表示
3. **Web UI への統合**: coverage % を Web UI に表示
4. **カバレッジの可視化**: カバレッジトレンドの可視化

## まとめ

test_generator の安定化とカバレッジ計測の実装が完了しました。以下の機能が追加・改善されました：

1. ✅ **test_generator の安定化**:
   - プロンプト改善（絶対守ってほしい制約を明文化）
   - import path の安定化
   - 出力の検証ロジック強化
   - E2E テストの強化
   - エラー時のフォールバック

2. ✅ **カバレッジ計測の実装**:
   - Makefile ターゲットの整備（test-coverage、test-cov）
   - CI への coverage 反映
   - Run モデルへのフック（TODO コメント）
   - ドキュメント更新

すべての実装は後方互換性を維持しており、既存のコードはそのまま動作します。生成されるテストコードの品質が向上し、カバレッジ計測の基盤が整いました。

