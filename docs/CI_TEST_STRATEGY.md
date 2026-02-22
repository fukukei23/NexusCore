# CI テスト戦略（CI Test Strategy）

## 概要

NexusCore の CI は、**Safe Tests** と **Full Tests** の2つのジョブに分かれています。

## ジョブ構成

### Safe Tests（必須チェック）

**目的**: PR のマージ可否を判定する必須チェック

**対象**:
- `tests/api/`
- `tests/governance/`

**依存関係**:
- `requirements-ci-safe.txt` を使用
- Gradio を除いた最小限の依存関係のみ
- 依存インストール失敗時は即時に CI を FAIL させる（`|| true` なし）

**実行コマンド**:
```bash
python -m pytest tests/api/ tests/governance/ -q --tb=short
```

**重要事項**:
- 部分実行は禁止（`tests/api/` と `tests/governance/` を毎回実行）
- このジョブが FAIL した場合、PR のマージは不可
- 依存関係は最小化され、不要な依存は含めない

### Full Tests（参考チェック）

**目的**: すべてのテストを実行し、包括的な品質チェックを行う

**対象**:
- すべてのテスト（`tests/` 配下すべて）

**依存関係**:
- `requirements-ci-full.txt` を使用（`requirements.txt` + `requirements-dev.txt` を含む）
- Gradio を含むすべての依存関係

**実行コマンド**:
```bash
python -m pytest --cov=src --cov-report=xml --cov-report=term-missing
```

**重要事項**:
- `continue-on-error: true` が設定されているため、FAIL しても CI 全体は PASS する
- Gradio 依存の問題など、UI 関連のテスト失敗は許容される
- **定期的に解消する必要があるが、Safe Tests とは独立して運用**

## 運用ルール

### Safe Tests の運用

- **赤ならマージ不可**: Safe Tests が FAIL した PR はマージしてはいけない
- **依存関係の追加は慎重に**: `requirements-ci-safe.txt` への依存追加は、本当に必要なものだけに限定する
- **再現性を保つ**: grep 等の動的加工は禁止、固定ファイルのみを使用

### Full Tests の運用

- **赤でもOK**: Full Tests が FAIL しても PR のマージは可能（Safe Tests が PASS している限り）
- **定期的な解消**: Gradio 依存の問題など、定期的（例：月1回）に Full Tests の失敗を解消する
- **優先度は低い**: Safe Tests の安定化が最優先、Full Tests の安定化は後回しでよい

## 依存関係管理

### requirements-ci-safe.txt

- Gradio を除いた最小限の依存関係のみ
- tests/api と tests/governance を実行するのに必要なものだけを含める
- Flask 系（Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-CORS, authlib）は、tests/api で FastAPI を使っているため、原則として不要
- uvicorn/websockets/httpcore/requests も、FastAPI の TestClient が実際に必要としない限り除外

### requirements-ci-full.txt

- `requirements.txt` と `requirements-dev.txt` を含む
- すべての依存関係を含む（Gradio 含む）

## トラブルシューティング

### Safe Tests が FAIL する場合

1. 依存関係の不足: `requirements-ci-safe.txt` に必要な依存を追加（最小限に）
2. テストコードの問題: テストコード自体のバグを修正

### Full Tests が FAIL する場合（Safe Tests は PASS）

1. Gradio 依存の問題: 一時的に許容、定期的に解消
2. UI 関連のテスト失敗: Safe Tests に影響しない限り、後回しでよい

## 依存関係の Lock 化

CI Safe テストの再現性を最大化するため、`requirements-ci-safe.lock` を使用しています。

### Lock ファイルの概要

- **`requirements-ci-safe.txt`**: 依存関係の要件定義（範囲指定）
- **`requirements-ci-safe.lock`**: 実際にインストールされる依存関係の固定バージョン（ハッシュ付き）

CI Safe job は `requirements-ci-safe.lock` から依存関係をインストールします：
```bash
pip install --require-hashes -r requirements-ci-safe.lock
```

### Lock ファイルの更新

Lock ファイルの更新手順については、[CI Safe Lock 運用ガイド](./CI_SAFE_LOCK.md) を参照してください。

**要点**:
- `requirements-ci-safe.txt` を変更したら、lock ファイルも必ず更新する
- lock ファイルは `pip-compile` で生成する（手編集禁止）
- PR には `requirements-ci-safe.txt` と `requirements-ci-safe.lock` の両方を含める

## 関連ファイル

- `.github/workflows/ci.yml` - CI ワークフロー定義
- `requirements-ci-safe.txt` - Safe Tests 用依存関係（要件定義）
- `requirements-ci-safe.lock` - Safe Tests 用依存関係（固定バージョン、ハッシュ付き）
- `requirements-ci-full.txt` - Full Tests 用依存関係
- `docs/CI_SAFE_LOCK.md` - Lock ファイルの運用ガイド

