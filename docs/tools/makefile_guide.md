# Makefile 使い方ガイド

## 概要

NexusCore プロジェクトには `Makefile` が用意されており、よく使うコマンドを簡単に実行できます。

## 基本的な使い方

### 1. ヘルプを表示

```bash
make help
```

利用可能なすべてのコマンドが表示されます。

### 2. 仮想環境の作成

```bash
make venv
```

`.venv` ディレクトリに仮想環境を作成します。

### 3. 開発ツールのインストール

```bash
make install-dev
```

`requirements-dev.txt` から開発ツール（black, ruff, mypy, pytest など）をインストールします。

## 開発フロー

### コードを書いた後

```bash
# 1. コードを整形
make format

# 2. Lint チェック
make lint

# 3. 自動修正付き Lint
make lint-fix

# 4. 型チェック
make typecheck

# 5. テスト実行
make test
```

### 一括で品質チェック

```bash
# すべてを一括実行（format + lint-fix + typecheck + test）
make qa
```

## テスト関連

### 高速テスト（カバレッジなし、並列実行）

```bash
make test-fast
```

開発中はこちらがおすすめです。

### カバレッジ付きテスト

```bash
make test-coverage
```

カバレッジレポートは `htmlcov/index.html` に生成されます。

### 通常のテスト

```bash
make test
```

## クリーンアップ

```bash
# キャッシュファイルを削除
make clean
```

以下のファイル/ディレクトリが削除されます：
- `.pytest_cache/`
- `.mypy_cache/`
- `htmlcov/`
- `.coverage`
- `__pycache__/` ディレクトリ
- `*.pyc` ファイル

## よく使うコマンドの組み合わせ

### 初回セットアップ

```bash
make venv
source .venv/bin/activate  # または source activate
make install-dev
```

### 日常的な開発

```bash
# コードを書いたら
make qa

# または個別に
make format
make lint-fix
make test-fast
```

### CI/CD 前の最終確認

```bash
make qa
make test-coverage
```

## 注意事項

- `make` コマンドは仮想環境を自動検出します（`myenv_linux` → `.venv` → `venv` の順）
- 仮想環境がない場合は、`make venv` で作成してください
- 仮想環境が有効化されていない場合でも、`make` は仮想環境内の Python を使用します

## トラブルシューティング

### make コマンドが見つからない

```bash
# Ubuntu/Debian
sudo apt-get install make

# または WSL で
sudo apt install make
```

### 仮想環境が検出されない

```bash
# 仮想環境を作成
make venv

# または既存の仮想環境を有効化
source activate  # または source myenv_linux/bin/activate
```

### パッケージが見つからない

```bash
# 開発ツールを再インストール
make install-dev
```

