# テスト結果ディレクトリ

このディレクトリには、テスト実行時に自動生成される結果レポートが保存されます。

## ファイル形式

- **TEST_RESULT_YYYYMMDD_HHMMSS.md** - テスト結果のMarkdownレポート（人間が読む用）
- **TEST_RESULT_YYYYMMDD_HHMMSS.json** - テスト結果のJSONレポート（機械読み取り用）

## レポートの内容

各レポートには以下の情報が含まれます：

- 実行日時
- テストターゲット
- ステータス（成功/失敗/スキップのみ）
- サマリー（合計テスト数、成功数、失敗数、スキップ数、エラー数、成功率）
- 実行時間
- 失敗したテストの一覧
- エラーテストの一覧
- 詳細出力（pytest標準出力）

## 使用方法

テスト実行時に自動的に生成されます：

```bash
bash dev_tools/run_tests_with_report.sh [テストターゲット]
```

または、既存のテスト出力からレポートを生成：

```bash
python -m dev_tools.test_result_generator <pytest_output_file> <test_target> [output_dir]
```

## 関連ドキュメント

- `docs/testing_guide.md` - テスト実行ガイド
- `dev_tools/run_tests_with_report.sh` - テスト実行＋レポート生成スクリプト
- `dev_tools/test_result_generator.py` - レポート生成ツール

