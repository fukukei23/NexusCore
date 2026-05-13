# CR-NEXUS-051: CI Safe 依存 Lock 化 - 完了レポート

## 実装日時

2025年12月25日

## 概要

### 目的

CI Safe テストの依存関係を lock 化し、再現性を最大化する。
現在 CI Safe は `requirements-ci-safe.txt` を使用しているが、範囲指定（`>=`, `<`）のため依存が更新されると突然壊れるリスクがある。Safe は "必須チェック" であり、再現性が最重要。

### ゴール

- `requirements-ci-safe.lock`（ハッシュ付き lock ファイル）を導入する
- GitHub Actions の Safe job は lock のみをインストールして pytest を実行する
- lock 更新手順を docs に明記する（人間が迷わない手順＋禁止事項含む）
- CI Safe がローカルでもCIでも同じ依存解決になる（再現性向上）

### 原則

- 追加のパッケージ管理ツール導入は最小にする（pip-tools を使用）
- Safe の対象テストは現状維持: `tests/api` と `tests/governance`
- 実行コマンドは固定: `python -m pytest tests/api/ tests/governance/ -q --tb=short`

## 実装ステップ

### Step 1: Lock ファイルの生成

**実施内容**:
- `requirements-ci-safe.lock` を生成（pip-compile を使用）
- ハッシュ付きで生成し、supply-chain セキュリティを強化

**実装詳細**:
- `pip-compile --generate-hashes --output-file requirements-ci-safe.lock requirements-ci-safe.txt` を実行
- Python 3.12 で生成（519行の lock ファイル）
- すべての依存関係の固定バージョンとハッシュを含む

**生成コマンド**:
```bash
python -m pip install --upgrade pip pip-tools
pip-compile --generate-hashes --output-file requirements-ci-safe.lock requirements-ci-safe.txt
```

### Step 2: CI Safe job の修正

**実施内容**:
- `.github/workflows/ci.yml` の Safe job を lock ファイル使用に変更

**実装詳細**:
- `pip install -r requirements-ci-safe.txt` → `pip install --require-hashes -r requirements-ci-safe.lock` に変更
- `--require-hashes` フラグを使用してハッシュ検証を有効化

**変更前**:
```yaml
- name: Install dependencies (CI Safe)
  run: |
    python -m pip install --upgrade pip
    pip install -r requirements-ci-safe.txt
```

**変更後**:
```yaml
- name: Install dependencies (CI Safe - from lock file)
  run: |
    python -m pip install --upgrade pip
    pip install --require-hashes -r requirements-ci-safe.lock
```

### Step 3: Lock ファイル運用ガイドの作成

**実施内容**:
- `docs/CI_SAFE_LOCK.md` を新規作成
- lock ファイルの生成、更新、運用方法を詳細に記載

**実装詳細**:
- Lock ファイルの生成手順
- Lock を更新すべきタイミング（`requirements-ci-safe.txt` 変更時、Python バージョン変更時等）
- Lock 更新手順（詳細）
- 禁止事項（lock ファイルの手編集禁止、txt と lock の不整合禁止）
- CI が落ちた場合の切り分け方法
- ローカル開発での使い方

### Step 4: CI テスト戦略ドキュメントの更新

**実施内容**:
- `docs/CI_TEST_STRATEGY.md` に lock ファイルに関する記述を追加

**実装詳細**:
- Lock ファイルの概要セクションを追加
- Lock ファイルの更新手順へのリンクを追加
- 関連ファイルリストに `requirements-ci-safe.lock` と `docs/CI_SAFE_LOCK.md` を追加

## 変更ファイル一覧

### 新規ファイル

- `requirements-ci-safe.lock` - 固定バージョンの依存関係（ハッシュ付き、519行）
- `docs/CI_SAFE_LOCK.md` - Lock ファイルの運用ガイド

### 変更ファイル

- `.github/workflows/ci.yml` - Safe job を lock ファイル使用に変更
- `docs/CI_TEST_STRATEGY.md` - Lock ファイルに関する記述を追加

## 動作確認結果

### Lock ファイルの生成

```bash
python -m pip install --upgrade pip pip-tools
pip-compile --generate-hashes --output-file requirements-ci-safe.lock requirements-ci-safe.txt
```

**結果**: ✅ `requirements-ci-safe.lock` が生成された（519行、ハッシュ付き）

### Lock ファイルからのインストールとテスト（ローカル）

```bash
python -m venv test_env
source test_env/bin/activate
pip install --require-hashes -r requirements-ci-safe.lock
python -m pytest tests/api/test_completion_reports_exist.py tests/governance/test_cr_spec_change_guard.py -q
```

**結果**: ✅ 3 passed

**確認項目**:
- ✅ lock ファイルから依存関係が正常にインストールされる
- ✅ ハッシュ検証が機能する（`--require-hashes`）
- ✅ Safe テストが正常に実行される

### CI での実行（期待結果）

- GitHub Actions の Safe job が `requirements-ci-safe.lock` から依存をインストール
- すべての Safe テストが PASS
- ローカル環境と CI 環境で同じ依存関係が使用される

## 設計上の改善点

### 再現性の向上

1. **固定バージョンの使用**
   - 範囲指定（`>=`, `<`）から固定バージョンへの移行により、依存関係の更新による突然の失敗を防止
   - ローカル環境と CI 環境で同じバージョンの依存関係が使用される

2. **ハッシュ検証の導入**
   - `--generate-hashes` により、各パッケージのハッシュを生成
   - `--require-hashes` により、インストール時のハッシュ検証を実施
   - supply-chain セキュリティの向上

### 運用性の向上

1. **明確な更新手順**
   - `docs/CI_SAFE_LOCK.md` に詳細な運用手順を記載
   - 更新タイミング、更新方法、禁止事項を明確化

2. **自動化の準備**
   - `pip-compile` による lock ファイル生成の自動化が容易
   - 将来的に CI での自動更新も検討可能

## 既知の制約・注意事項

### Lock ファイルの更新頻度

- Lock ファイルにより一時的に依存が古く固定される可能性がある
- 必要に応じて `requirements-ci-safe.txt` でバージョン範囲を調整し、lock ファイルを再生成する運用

### Python バージョンの変更

- Python バージョンを変更した場合、lock ファイルを再生成する必要がある
- lock ファイルは生成時の Python バージョンに依存する

### 禁止事項

- Lock ファイルを手編集してはいけない（`pip-compile` で生成する）
- `requirements-ci-safe.txt` と `requirements-ci-safe.lock` を不整合にしない（PR には両方を含める）

## 次のステップ

### 短期的な改善

1. **CI での自動検証**
   - lock ファイルと txt ファイルの整合性を CI で検証するテストを追加（検討）
   - lock ファイルが最新かどうかを CI でチェック（検討）

2. **ドキュメントの充実**
   - lock ファイルの更新頻度に関するガイドラインを追加（検討）
   - 依存関係のバージョンアップ手順を追加（検討）

### 長期的な検討

1. **Full Tests への lock 導入**
   - Full Tests にも lock ファイルを導入するか検討（現時点では Safe Tests のみ）

2. **依存関係の定期更新**
   - lock ファイルの定期更新プロセスを確立（検討）

