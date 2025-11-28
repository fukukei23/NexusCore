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
  - 1回目実行時：キャッシュファイル（`.nexuscache/analyzer_cache.json`）が生成されること
  - 2回目実行時：キャッシュが使用され、解析結果が同じ構造で返ること
  - ファイル変更時：変更されたファイルだけ再解析されること
  - パフォーマンス：2回目は1回目より高速であること

### test_generator: テスト自動生成 + pytest 実行の E2E

**テストファイル**: `tests/analyzer/test_test_generator_e2e.py`

**目的**:
- サンプルプロジェクト内の関数に対して、テストコードを生成し、最低限「pytest でインポート可能なテストファイル」が得られること

**検証項目**:
- テストファイルが生成されること
- 生成されたテストファイルがインポート可能であること
- （可能であれば）pytest で実行してエラーにならないこと

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
```

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

## 関連ドキュメント

- [UI Testing Policy](./testing_policy_ui.md) - UI テストポリシー
- [SaaS Architecture](./saas_architecture.md) - SaaS アーキテクチャの概要

