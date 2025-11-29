<!-- 本ファイルは tools/coverage_phase3_report.py により自動生成されます -->

# Phase 3 Coverage Summary

まだ `make coverage-phase3` を実行していません。

以下のコマンドで最新のカバレッジレポートを生成できます。

```bash
make coverage-phase3
```

## 対象モジュール

- `analyzer.graph_builder`: 依存関係グラフ構築
- `analyzer.unified_analyzer`: 解析パイプライン
- `utils.test_generator`: テスト自動生成
- `utils.tree_sitter_checker`: Tree-sitter ベースのコード解析

## 実行方法

```bash
# プロジェクトルートで
make coverage-phase3
```

実行後、以下のファイルが生成・更新されます：

- `.coverage-phase3`: カバレッジデータファイル
- `docs/coverage_phase3_summary.md`: このファイル（自動更新）

---

**注意**: このファイルは `make coverage-phase3` 実行時に自動的に上書きされます。

