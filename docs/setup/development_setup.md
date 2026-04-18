# NexusCore 開発環境セットアップ

## 概要

このドキュメントでは、NexusCore プロジェクトの開発環境を整えるための設定ファイルとツールの導入方法を説明します。

## 設定ファイル一覧

以下の設定ファイルがプロジェクトルートに配置されています：

- `.cursorignore` - Cursor AI が読み込むファイル/フォルダを制御
- `pyproject.toml` - Ruff / Black の設定
- `mypy.ini` - mypy 静的型チェックの設定
- `pyrightconfig.json` - Pyright 型チェックの設定（既存）
- `.vscode/settings.json` - VSCode / Cursor のエディタ設定

## ツールのインストール

### 1. 開発依存パッケージのインストール

```bash
cd /path/to/nexuscore-project
source .venv/bin/activate  # or .\.venv\Scripts\activate on Windows

# 開発依存パッケージをインストール
pip install -r requirements-dev.txt

# または個別にインストール
pip install black ruff mypy
```

### 2. VSCode / Cursor 拡張機能

以下の拡張機能をインストールすることを推奨します：

- **Python** (Microsoft) - Python 言語サポート
- **Ruff** (Astral Software) - Ruff リンター/フォーマッタ
- **Pylance** (Microsoft) - Pyright ベースの型チェック

## よく使うコマンド

### フォーマット & Lint

```bash
# Black でフォーマット
black src tests

# Ruff で Lint チェック
ruff check src tests

# Ruff で自動修正込み
ruff check src tests --fix
```

### 型チェック

```bash
# mypy で型チェック
mypy src

# Pyright は VSCode / Cursor が自動で実行
```

## 設定ファイルの役割

### `.cursorignore`

Cursor AI が読み込むファイル/フォルダを制御します。重いフォルダ（`node_modules`、`chroma_db` など）を除外することで、AI の応答速度を向上させます。

### `pyproject.toml`

- **Black**: コードフォーマッタ（行長 100、Python 3.12 対応）
- **Ruff**: 高速な Linter とフォーマッタ（pycodestyle、pyflakes、isort など）

### `mypy.ini`

静的型チェックツール mypy の設定：
- Python 3.12 をターゲット
- `src/` 以下をメインターゲット
- `tests/` は最初は無視（段階的に厳しくしていく）

### `pyrightconfig.json`

Pyright 型チェックの設定：
- `src` と `tests` を対象
- 不要なディレクトリを除外
- 型チェックモード: `basic`

### `.vscode/settings.json`

VSCode / Cursor のエディタ設定：
- Python インタプリタの自動検出（`.venv` 優先）
- 保存時の自動フォーマット（Black + Ruff）
- 不要なフォルダをエクスプローラ・検索から除外

## 導入順序のおすすめ

1. **`.cursorignore` を配置** - すぐに効果が出る
2. **`pyproject.toml` で Ruff / Black を設定** - コードスタイルを統一
3. **`.vscode/settings.json` でエディタ設定** - 開発体験を向上
4. **`mypy.ini` を配置** - 型チェックを段階的に導入

## 効果

これらの設定により：

- ✅ AI が変なフォルダを読み漁って重くなる問題が減る
- ✅ コードスタイルが自然と揃う
- ✅ 型のヤバいところだけ早めに見つかる
- ✅ 開発環境が統一され、快適に開発できる

## トラブルシューティング

### Ruff が見つからない

```bash
pip install ruff
```

VSCode / Cursor で Ruff 拡張機能をインストールしているか確認してください。

### Black が見つからない

```bash
pip install black
```

### mypy のエラーが多い

`mypy.ini` で `ignore_errors = True` を設定しているディレクトリがあるか確認してください。段階的に型チェックを厳しくしていくことができます。

### Pyright のエラーが多い

`pyrightconfig.json` の `typeCheckingMode` を `basic` から `standard` や `strict` に変更する前に、既存のコードを修正することをお勧めします。

