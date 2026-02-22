# CI Safe Lock ファイル運用ガイド

## 概要

CI Safe テストの依存関係を再現可能にするため、`requirements-ci-safe.lock` を使用します。
この lock ファイルにより、ローカル環境と CI 環境で同じバージョンの依存関係がインストールされます。

## ファイル構成

- **`requirements-ci-safe.txt`**: 依存関係の要件定義（範囲指定: `>=`, `<`）
- **`requirements-ci-safe.lock`**: 実際にインストールされる依存関係の固定バージョン（ハッシュ付き）

## Lock ファイルの生成・更新

### 前提条件

- Python 3.11 以上
- pip-tools がインストールされていること

### 更新手順（推奨：1コマンド）

**重要**: `requirements-ci-safe.txt` を変更した場合は、**必ず**以下のコマンドを実行してください。

```bash
python tools/update_ci_safe_lock.py
```

このコマンドは以下を行います：
1. `requirements-ci-safe.txt` の sha256 を計算
2. `pip-compile` を使用して `requirements-ci-safe.lock` を生成
3. lock ファイルの先頭にメタ情報（SOURCE_SHA256 など）を埋め込む

### 手動生成（非推奨）

手動で生成する場合（通常は不要）:

```bash
# pip-tools をインストール（未インストールの場合）
python -m pip install --upgrade pip pip-tools

# lock ファイルを生成
pip-compile --generate-hashes --output-file requirements-ci-safe.lock requirements-ci-safe.txt

# その後、メタ情報を手動で追加する必要がある（非推奨）
```

**注意**: 手動生成後は、`tools/update_ci_safe_lock.py` を実行してメタ情報を正しく設定してください。

### 生成コマンドの説明

- `--generate-hashes`: 各パッケージのハッシュを生成（supply-chain セキュリティ向上）
- `--output-file requirements-ci-safe.lock`: 出力ファイル名を指定
- `requirements-ci-safe.txt`: 入力となる要件定義ファイル

## Lock を更新すべきタイミング

1. **`requirements-ci-safe.txt` を変更したとき**（必須）
   - 新しい依存関係を追加した場合
   - 既存の依存関係のバージョン範囲を変更した場合
   - **この場合、必ず `python tools/update_ci_safe_lock.py` を実行してください**

2. **Python バージョンを変更したとき**
   - CI Safe job の Python バージョンが変更された場合

3. **定期的な依存関係の更新**
   - セキュリティアップデートがある場合
   - 主要ライブラリ（pytest, fastapi など）のバージョンを上げたい場合

## Lock 更新手順（詳細）

### Step 1: requirements-ci-safe.txt を確認・編集

```bash
# 必要な依存関係を追加または更新
vim requirements-ci-safe.txt
```

### Step 2: Lock ファイルを更新（1コマンド）

```bash
python tools/update_ci_safe_lock.py
```

このコマンドは以下を行います：
- `requirements-ci-safe.txt` の sha256 を計算
- `pip-compile` を使用して lock ファイルを生成
- lock ファイルの先頭にメタ情報（SOURCE_SHA256）を埋め込む

**重要**: txt を変更したら、このコマンドを実行しないと CI Safe が FAIL します。

### Step 3: 生成された lock ファイルを確認

```bash
# 変更内容を確認
git diff requirements-ci-safe.lock
```

**確認すべきポイント**:
- 依存関係の増減が意図したとおりか
- 主要ライブラリ（pytest, fastapi, httpx など）のバージョン変化
- 新規に追加された依存関係のハッシュが正しく生成されているか
- lock ファイルの先頭に SOURCE_SHA256 が正しく埋め込まれているか

### Step 4: ローカルでテスト

```bash
# 仮想環境を作成（推奨）
python -m venv test_env
source test_env/bin/activate

# lock ファイルから依存関係をインストール
pip install --require-hashes -r requirements-ci-safe.lock

# Safe テストを実行（lock guard テストも含む）
python -m pytest tests/api/ tests/governance/ -q --tb=short
```

### Step 5: PR を作成

```bash
git add requirements-ci-safe.txt requirements-ci-safe.lock
git commit -m "chore: update CI Safe dependencies"
git push
```

**注意**: PR には `requirements-ci-safe.txt` と `requirements-ci-safe.lock` の**両方**を含めてください。

## 禁止事項

### ❌ Lock ファイルを手編集しない

`requirements-ci-safe.lock` を直接編集してはいけません。
必ず `tools/update_ci_safe_lock.py` を使って生成してください。

```bash
# ❌ 悪い例
vim requirements-ci-safe.lock  # 手編集は禁止

# ✅ 良い例
vim requirements-ci-safe.txt   # txt を編集
python tools/update_ci_safe_lock.py  # lock を更新
```

### ❌ txt と lock を不整合にしない

`requirements-ci-safe.txt` と `requirements-ci-safe.lock` は常に整合性を保つ必要があります。

- `requirements-ci-safe.txt` を変更した場合は、**必ず** `python tools/update_ci_safe_lock.py` を実行する
- PR には `requirements-ci-safe.txt` と `requirements-ci-safe.lock` の両方を含める
- txt だけを更新して lock を更新しない（CI Safe が FAIL します）
- lock だけを更新して txt を更新しない（不整合の原因になります）

### ❌ 更新ツールを使わずに lock を生成しない

`pip-compile` を直接実行して lock を生成しても、メタ情報（SOURCE_SHA256）が埋め込まれないため、CI Safe が FAIL します。
必ず `tools/update_ci_safe_lock.py` を使用してください。

## CI が落ちた場合の切り分け

### ケース1: txt と lock の整合性エラー（最も一般的）

**症状**: CI Safe job で `test_ci_safe_lock_source_sha256_matches_txt` が FAIL する

**エラーメッセージ例**:
```
CI Safe lock/txt の整合性エラー: requirements-ci-safe.lock が古い（または不整合）です。
- requirements-ci-safe.txt sha256 : abc123...
- requirements-ci-safe.lock SOURCE_SHA256 : def456...
```

**原因**: `requirements-ci-safe.txt` が更新されたが、`requirements-ci-safe.lock` が更新されていない

**対応（最短復旧手順）**:
```bash
# 1. lock ファイルを更新
python tools/update_ci_safe_lock.py

# 2. 変更をコミット
git add requirements-ci-safe.lock
git commit -m "chore: update CI Safe lock file"
git push
```

### ケース2: 依存関係のバージョン競合

**症状**: `pip install --require-hashes` が失敗する

**原因**: 依存関係のバージョンが互換性がない

**対応**:
1. `requirements-ci-safe.txt` でバージョン範囲を調整
2. `python tools/update_ci_safe_lock.py` を実行して lock を再生成

### ケース3: ハッシュ検証エラー

**症状**: `--require-hashes` でハッシュ検証に失敗する

**原因**: パッケージのハッシュが変更された（まれ）

**対応**:
1. `python tools/update_ci_safe_lock.py` を実行して lock を再生成（ハッシュを更新）

### ケース4: 更新ツールが実行できない

**症状**: `python tools/update_ci_safe_lock.py` が失敗する

**原因**: pip-tools がインストールされていない、または piptools モジュールが見つからない

**対応**:
```bash
# pip-tools をインストール
python -m pip install --upgrade pip pip-tools

# 再度更新ツールを実行
python tools/update_ci_safe_lock.py
```

## ローカル開発での使い方

### CI Safe テストを実行する場合

```bash
# Lock ファイルから依存関係をインストール（推奨）
pip install --require-hashes -r requirements-ci-safe.lock

# Safe テストを実行
python -m pytest tests/api/ tests/governance/ -q --tb=short
```

### 新しい依存関係を追加したい場合

1. `requirements-ci-safe.txt` に追加
2. lock ファイルを再生成
3. ローカルでテスト
4. PR を作成

## 関連ファイル

- `requirements-ci-safe.txt` - 依存関係の要件定義
- `requirements-ci-safe.lock` - 固定バージョンの依存関係（ハッシュ付き）
- `.github/workflows/ci.yml` - CI Safe job の定義
- `docs/CI_TEST_STRATEGY.md` - CI テスト戦略の概要

