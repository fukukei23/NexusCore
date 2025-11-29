# Phase 3: Orchestrator / 解析系テスト戦略

このドキュメントは、NexusCore の **Phase 3（Orchestrator / 解析系）** に関するテスト戦略を定義します。

## 対象

- **graph_builder.py**: 依存関係グラフ構築
- **unified_analyzer.py**: 解析パイプライン
- **test_generator.py**: テスト自動生成

## テスト方針

### 軽量 E2E テスト

Phase 3 のテストは、**小さなサンプルプロジェクトを対象にした軽量 E2E テスト**を中心とします。

- **目的**: パイプラインが「最後まで走る」「最低限のキーを返す」ことを保証する
- **対象**: 細かい分岐ではなく、主要なフローが動作することを確認
- **実行時間**: 短時間で完了（CI で常に実行可能）

### テスト用ミニプロジェクト

`tests/analyzer/fixtures_sample_project.py` で定義される最小限の Python プロジェクトを使用：

- `module_a.py`: `module_b.add_one()` を呼び出す
- `module_b.py`: `add_one()` 関数を定義

この「小さな依存関係」が軽量 E2E のターゲットになります。

## 各テストの目的

### graph_builder: 依存グラフ構築の E2E

**テストファイル**: `tests/analyzer/test_graph_builder_e2e.py`

**目的**:
- サンプルプロジェクトを渡したときに、グラフ生成が通り、ノードとエッジが最低限存在することを確認

**検証項目**:
- グラフが空でないこと
- サンプルプロジェクトのモジュール（module_a, module_b）がノードに含まれていること
- エッジが存在すること（依存関係が検出されていること）

### unified_analyzer: 解析パイプラインの E2E

**テストファイル**: `tests/analyzer/test_unified_analyzer_e2e.py`

**目的**:
- サンプルプロジェクトを入力として unified_analyzer を実行し、返り値に最低限のキーが存在することを確認
- キャッシュ機能が正しく動作することを確認

**検証項目**:
- 解析結果が空でないこと
- 各結果に `success` キーが含まれていること
- 成功した場合、`file_path` または `data` キーが含まれていること
- **キャッシュ機能**:
  - 1回目実行時：キャッシュファイル（`.nexuscache/unified_analyzer.json`）が生成されること
  - 2回目実行時：キャッシュが使用され、解析結果が同じ構造で返ること
  - ファイル変更時：変更されたファイルだけ再解析されること
  - パフォーマンス：2回目は1回目より高速であること
  - 環境変数制御：`NEXUS_UNIFIED_ANALYZER_ENABLE_CACHE` でキャッシュを ON/OFF できること
  - RESET_CACHE 環境変数：`NEXUS_UNIFIED_ANALYZER_RESET_CACHE=1` でキャッシュをクリアできること

### test_generator: テスト自動生成 + pytest 実行の E2E

**テストファイル**:
- `tests/analyzer/test_test_generator_e2e.py`: LLM ベースの E2E テスト（LLM が必要）
- `tests/analyzer/test_test_generator_stable.py`: 安定性テスト（LLM 不要）

**目的**:
- サンプルプロジェクト内の関数に対して、テストコードを生成し、最低限「pytest でインポート可能なテストファイル」が得られること
- **LLM なしでも必ず pytest 用テストコードの"枠"を生成できること**
- **LLM を使う場合も失敗しても graceful degrade すること**

**test_generator の役割**:
- 「LLM が使えるときは肉付け、使えなくても必ず pytest ひな形を出す」安全な層であること
- 2回実行しても常に成功し、LLM 側の障害やネットワークエラーで落ちないこと

**safe/template モード**:
- AST ベースで関数一覧を拾い、`test_<func>` の枠を自動生成する
- LLM が使えない場合や失敗した場合、必ずテンプレートコードにフォールバックする
- パースエラーや I/O エラーが発生しても、例外を投げずに最低限のテストスキャフォールドを返す

**検証項目**:
- テストファイルが生成されること
- 生成されたテストファイルがインポート可能であること
- （可能であれば）pytest で実行してエラーにならないこと
- **LLM を完全に無効化してもエラーにならず、pytest 用テストひな形が生成されること**
- **LLM 有効時、LLM エラーが発生しても例外が外に漏れず、テンプレートコードにフォールバックされること**
- **シンタックスエラーや読み込みエラーが発生しても、例外を投げずに最低限のテストスキャフォールドを返すこと**

**環境変数**:
- **`NEXUS_TESTGEN_ENABLE_LLM`**:
  - `"0"` / `"false"` / `"no"` の場合は LLM 完全無効（template mode のみ）
  - それ以外は有効（デフォルト: 有効）
- **`NEXUS_TESTGEN_MAX_FUNCTIONS`**:
  - 1ファイルあたり最大何関数までテスト生成するか（デフォルト: 20）

**CLI オプション**:
- `--safe-only` / `--no-llm`: LLM を無効化し、template mode のみを使用
- `--enable-llm`: LLM を有効化（環境変数を上書き）
- `--max-functions <N>`: 最大関数数を指定（環境変数を上書き）

**テストポリシー**:
- 2回実行しても常に成功し、LLM 側の障害やネットワークエラーで落ちないこと
- パースエラーや I/O エラーが発生しても、例外を投げずに最低限のテストスキャフォールドを返すこと
- CI で常に回せる軽量な E2E テストを用意すること

**注意**: LLM ベースのテスト生成は不安定な可能性があるため、インポートエラーの検証に留めることも検討

## カバレッジとの関係

### カバレッジの見せ方

これらの軽量 E2E により、analyzer レイヤのカバレッジが一気に押し上がります。

- **coverage.xml**: CI で生成されるカバレッジレポート
- **analyzer モジュールのカバレッジ**: `src/nexuscore/analyzer/` 配下のカバレッジを CI で可視化可能

### カバレッジ確認コマンド

```bash
# Phase3 テスト + カバレッジ
pytest tests/analyzer/ --cov=src/nexuscore/analyzer --cov-report=term-missing

# または Makefile 経由
make test-phase3

# 全体のカバレッジ（src 全体）
make test-coverage  # HTML + XML レポート生成
make test-cov       # XML レポートのみ（CI 用）
```

### Coverage 計測の方針

NexusCore では `pytest-cov` プラグインを使用してカバレッジを計測します。

**ローカル実行**:
- `make test-coverage`: HTML レポート（`htmlcov/index.html`）と XML レポート（`coverage.xml`）を生成
- `make test-cov`: XML レポートのみ生成（CI 用）

**CI での実行**:
- GitHub Actions で `pytest --cov=src --cov-report=xml` を実行
- `coverage.xml` を Codecov にアップロード（オプション）
- 将来的に PR コメントや Web UI に coverage % を表示

**Self-Healing Run との統合**:
- `self_healing_service._finalize()` に TODO コメントで coverage 統合の構想を記載
- テスト実行後に coverage を測定し、`Run.details["coverage_pct"]` に保存する予定
- PR コメントや Web UI に coverage % を表示できるようにする

## 実行方法

### ローカル実行

```bash
# Phase3 テストのみ
pytest tests/analyzer/

# Phase3 テスト + カバレッジ
pytest tests/analyzer/ --cov=src/nexuscore/analyzer --cov-report=term-missing
```

### CI での実行

- これらの `tests/analyzer/` 系は、既存の pytest 実行に自然に含まれるようにする（特別なジョブ追加は必須ではない）
- 重くなりすぎる場合は、`@pytest.mark.slow` を付けて、通常 CI では skip / nightly では実行、といった運用も可能
- まずは「小さなサンプルプロジェクト」に限定して軽量に保つことを優先

## テストの特徴

### スモークテスト的な性質

- **細かい分岐までは追わない**: 主要なフローが動作することを確認
- **構造の存在確認**: 主要キーが構造として存在することを確認
- **実行時間**: 短時間で完了（CI で常に実行可能）

### 将来の拡張

- **より複雑なサンプルプロジェクト**: 必要に応じて追加
- **パフォーマンステスト**: 大きなプロジェクトでの実行時間測定
- **エッジケーステスト**: 異常系のテスト（別途追加）

## unified_analyzer キャッシュ機能

### キャッシュの目的

同一プロジェクトを繰り返し解析する際の速度を大幅に改善するため、ファイル内容が変わっていない場合、前回の解析結果をキャッシュから再利用します。

### キャッシュファイルの場所と JSON サンプル構造

**キャッシュファイル**: `project_root/.nexuscache/unified_analyzer.json`

**JSON フォーマット**:
```json
{
  "schema_version": 1,
  "analyzer_version": "0.1.0",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:01Z",
  "project_root": "/path/to/project",
  "files": {
    "relative/path.py": {
      "hash": "sha256:xxxx...",
      "last_analyzed": "2025-01-01T00:00:00Z",
      "result": { /* unified_analyzer の per-file 結果 */ }
    }
  }
}
```

### 環境変数一覧

- **`NEXUS_UNIFIED_ANALYZER_ENABLE_CACHE`**:
  - `"0"` / `"false"` / `"no"` の場合はキャッシュ完全無効
  - それ以外は有効（デフォルト: 有効）

- **`NEXUS_UNIFIED_ANALYZER_CACHE_DIR`**:
  - 指定されていればそのディレクトリ配下に JSON を作成
  - 未指定なら `project_root / ".nexuscache"` を使う

- **`NEXUS_UNIFIED_ANALYZER_RESET_CACHE`**:
  - 真の場合、`analyze_project()` の最初に `cache.clear()` を呼び出す

### 運用方針の例

- **ローカル開発**: キャッシュを ON（デフォルト）で、再解析の速度を改善
- **CI**: キャッシュを OFF（`NEXUS_UNIFIED_ANALYZER_ENABLE_CACHE=0`）にして、常に最新の解析結果を得る
- **一時的なキャッシュクリア**: `NEXUS_UNIFIED_ANALYZER_RESET_CACHE=1` を設定して実行

### キャッシュの動作

1. **1回目の解析**: 全ファイルを解析し、結果をキャッシュに保存
2. **2回目以降の解析**: ファイル内容のハッシュ（SHA256）を計算し、キャッシュと比較
   - ハッシュが一致: キャッシュから結果を取得（解析をスキップ）
   - ハッシュが不一致: ファイルを再解析し、キャッシュを更新

### テスト

詳細なテストは `tests/analyzer/test_unified_analyzer_cache.py` を参照してください。

## 関連ドキュメント

- [UI Testing Policy](./testing_policy_ui.md) - UI テストポリシー
- [SaaS Architecture](./saas_architecture.md) - SaaS アーキテクチャの概要

