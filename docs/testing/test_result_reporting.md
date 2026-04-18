# テスト結果レポート自動生成機能

## 概要

NexusCore のテスト実行時に、結果を構造化されたMarkdownレポートとして自動生成する機能です。

テスト実行後に結果ファイルが作成され、サマリーと詳細が確認できます。

## 機能

- **自動レポート生成**: テスト実行後に結果レポートを自動生成
- **Markdown形式**: 人間が読みやすい形式で結果を保存
- **JSON形式**: 機械読み取り用の構造化データ
- **結果確認**: テスト実行後にサマリーを自動表示

## 使用方法

### 方法1: レポート付きテスト実行（推奨）

```bash
bash dev_tools/run_tests.sh [テストターゲット]
```

レポートを生成したくない場合は：

```bash
bash dev_tools/run_tests.sh [テストターゲット] --no-report
```

### 方法2: 専用スクリプトを使用

```bash
bash dev_tools/run_tests_with_report.sh [テストターゲット]
```

### 方法3: 既存のテスト出力からレポート生成

```bash
python -m dev_tools.test_result_generator <pytest_output_file> <test_target> [output_dir]
```

## レポートの保存場所

レポートは `test_results/` ディレクトリに保存されます：

- `test_results/TEST_RESULT_YYYYMMDD_HHMMSS.md` - Markdownレポート
- `test_results/TEST_RESULT_YYYYMMDD_HHMMSS.json` - JSONレポート

## レポートの内容

### Markdownレポート

- **実行日時**: テスト実行の日時
- **テストターゲット**: 実行したテストのパス
- **ステータス**: 成功/失敗/スキップのみ
- **サマリー**: 合計テスト数、成功数、失敗数、スキップ数、エラー数、成功率、実行時間
- **詳細**: 失敗したテストの一覧、エラーテストの一覧
- **詳細出力**: pytest の標準出力（折りたたみ形式）

### JSONレポート

- `timestamp`: タイムスタンプ（YYYYMMDD_HHMMSS形式）
- `executed_at`: ISO形式の実行日時
- `test_target`: テストターゲット
- `result`: テスト結果データ（合計数、成功数、失敗数、失敗したテスト一覧など）

## レポートの確認

テスト実行後、自動的にサマリーが表示されます。完全なレポートを確認するには：

```bash
# 最新のレポートを確認
ls -t test_results/TEST_RESULT_*.md | head -1 | xargs cat

# 特定のレポートを確認
cat test_results/TEST_RESULT_20251128_123456.md
```

## 実装の詳細

### test_result_generator.py

テスト結果を解析してレポートを生成するツールです。

**主要機能**:
- pytest の標準出力を解析
- Markdownレポートを生成
- JSONレポートを生成
- 失敗したテストの詳細を抽出

**使用方法**:
```bash
python -m dev_tools.test_result_generator <pytest_output_file> <test_target> [output_dir]
```

### run_tests.sh の拡張

既存のテストスクリプト（`dev_tools/run_tests.sh`）にレポート生成機能を統合しました。

テスト実行後、自動的に：
1. pytest の標準出力を一時ファイルに保存
2. 結果レポートを生成（Markdown + JSON）
3. サマリーを表示
4. レポートファイルの場所を表示
5. 一時ファイルを削除

## 今後の拡張予定

- [ ] テスト結果の比較（前回との差分表示）
- [ ] カバレッジ情報の統合
- [ ] 失敗したテストの自動再実行
- [ ] テスト結果の可視化（グラフやチャート）
- [ ] CI/CD連携（テスト結果をGitHub Actionsに投稿）

## 完了レポートとの関係

完了レポートを出す変更では、必ずテストを実行し、その結果をレポートに含める。ルールの詳細は [CR と実装計画の結果の保存先](CR_AND_REPORTS_SAVE_LOCATIONS.md) の「必ずテストするルール」「完了レポートに含める項目」を参照。

## 関連ファイル

- `dev_tools/test_result_generator.py` - レポート生成ツール
- `dev_tools/run_tests.sh` - テスト実行スクリプト（レポート生成統合済み）
- `dev_tools/run_tests_with_report.sh` - レポート専用テストスクリプト
- `test_results/README.md` - テスト結果ディレクトリの説明
- `docs/testing_guide.md` - テスト実行ガイド
