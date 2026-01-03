# テスト実行ガイド

## 概要

NexusCore のテストを実行する方法を説明します。

## 推奨される実行方法

### 方法1: Makefile を使用（推奨）

```bash
# 通常のテスト実行
make test

# カバレッジ付きテスト実行
make test-coverage  # HTML + XML レポート
make test-cov       # XML レポートのみ（CI 用）

# Phase3 アナライザー テスト
make test-phase3
```

### 方法2: dev_tools/run_tests.sh を使用

```bash
# テスト実行 + レポート生成
bash dev_tools/run_tests.sh tests/

# レポートなしで実行
bash dev_tools/run_tests.sh tests/ --no-report
```

### 方法3: pytest を直接実行

```bash
# 仮想環境を有効化
source myenv_linux/bin/activate

# テスト実行
python -m pytest tests/ -v --tb=short

# カバレッジ付き
python -m pytest tests/ --cov=src --cov-report=xml --cov-report=term-missing
```

## テストファイル構成

- `tests/webapp/` - Flask Webapp UI スモークテスト
- `tests/gradio/` - Gradio UI スモークテスト
- `tests/api/` - API スモークテスト
- `tests/analyzer/` - Phase3 アナライザー E2E テスト
- `tests/utils/` - ユーティリティテスト

## テスト結果レポート

テスト実行時に `test_results/` ディレクトリに以下のファイルが生成されます：

- `TEST_RESULT_YYYYMMDD_HHMMSS.md` - Markdown レポート（人間が読む用）
- `TEST_RESULT_YYYYMMDD_HHMMSS.json` - JSON レポート（機械読み取り用）

## 注意事項

### 依存関係のバージョン

テスト実行時は、`requirements.txt` で指定されたバージョンレンジ内の依存関係がインストールされていることを前提としています。

主要な依存関係のバージョンレンジ：
- `openai>=1.30.0,<2.0.0` - OpenAI SDK は 1.x 系を前提
- `tensorflow>=2.14.0,<3.0.0` - TensorFlow は 2.x 系を前提
- `gradio>=4.16.0,<5.0.0` - Gradio は 4.x 系を前提
- `pytest>=7.4.0,<8.0.0` - pytest は 7.x 系を前提

詳細は `requirements.txt` を参照してください。

### WSL環境での注意

WSL環境では、出力キャプチャの問題により、テスト結果が正しく表示されない場合があります。
その場合は、`test_results/` ディレクトリのレポートファイルを直接確認してください。

