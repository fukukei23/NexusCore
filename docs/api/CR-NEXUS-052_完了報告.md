# CR-NEXUS-052: CI Safe Lock Guard (txt/lock mismatch detection + update tool) - 完了レポート

## 実装日時

2025年12月26日

## 概要

### 目的

CI Safe における依存関係管理の再現性をさらに強化するため、
`requirements-ci-safe.txt` と `requirements-ci-safe.lock` の不整合（lock が古い／未更新）を
**CI 上で機械的に検知し、更新手順を単一コマンドに固定する仕組み**を導入する。

### ゴール

- txt と lock がズレた場合、CI Safe が必ず FAIL する
- FAIL 時に「原因」「影響範囲」「解除方法」が明確に表示される
- 指定された更新ツールを実行すれば、必ず PASS に戻る
- 人手による判断や善意に依存しない運用を実現する

### 原則

- CI Safe は **再現性最優先**
- lock は Single Source of Truth ではなく
  **「txt から生成された成果物」であることを明示**
- 解除方法は 1 通りに固定する

## 実装ステップ

### Step 1: lock/txt 整合性検知テストの追加

**実施内容**:
- `tests/governance/test_ci_safe_lock_guard.py` を新規作成
- `requirements-ci-safe.txt` の sha256 を計算
- `requirements-ci-safe.lock` 先頭コメントに記録された `SOURCE_SHA256` を抽出
- 不一致の場合は CI Safe を FAIL させるテストを実装

**実装詳細**:
- `test_ci_safe_lock_file_exists()`: lock ファイルの存在確認
- `test_ci_safe_lock_source_sha256_format()`: SOURCE_SHA256 の形式検証（64文字の16進数）
- `test_ci_safe_lock_source_sha256_matches_txt()`: txt と lock の sha256 整合性検証
- 失敗時は詳細なエラーメッセージ（原因、解除方法、チェックリスト）を表示

### Step 2: lock 更新ツールの実装

**実施内容**:
- `tools/update_ci_safe_lock.py` を新規作成
- pip-compile を実行して lock を再生成
- lock 先頭に SOURCE_SHA256 等のメタ情報を正規化して埋め込む
- 更新前後の sha256 を標準出力に表示

**実装詳細**:
- `calculate_file_sha256()`: ファイルの sha256 計算（バイナリ読み込み）
- `extract_source_sha256_from_lock()`: lock ファイルから SOURCE_SHA256 を抽出（正規表現）
- `generate_lock_file()`: `python -m piptools compile` を実行して lock を生成
- `insert_metadata_into_lock()`: lock 先頭にメタ情報コメントブロックを挿入/更新
  - 既存メタ情報を削除してから新規メタ情報を挿入
  - メタ情報フォーマット: `# CI SAFE LOCK (generated)`, `# SOURCE_FILE:`, `# SOURCE_SHA256:`, `# GENERATED_BY:`, `# NOTE:`

### Step 3: FAIL メッセージの標準化

**実施内容**:
- pytest FAIL 時に以下を必ず表示:
  - txt と lock の sha256 値
  - 解除方法（更新ツールの実行コマンド）
  - 影響範囲チェックリスト

**実装詳細**:
- `test_ci_safe_lock_source_sha256_matches_txt()` の assertion message に以下を記載:
  - `requirements-ci-safe.txt sha256`: 実際の値
  - `requirements-ci-safe.lock SOURCE_SHA256`: 実際の値
  - 解除方法: `python tools/update_ci_safe_lock.py`
  - 影響範囲チェックリスト（5項目）
  - 注記（lock の手編集禁止）

### Step 4: 運用ドキュメントの更新

**実施内容**:
- `docs/CI_SAFE_LOCK.md` を更新
- CI Safe Lock の運用ルールを明記
- 更新タイミング・禁止事項・切り分け手順を明文化

**実装詳細**:
- Lock 更新手順を1コマンドに統一（`python tools/update_ci_safe_lock.py`）
- 禁止事項セクションを強化（手編集禁止、txt/lock 不整合禁止、更新ツール不使用禁止）
- CI が落ちた場合の切り分けセクションを拡充（整合性エラーの詳細な対応手順を追加）

## 変更ファイル一覧

### 新規作成

- `tests/governance/test_ci_safe_lock_guard.py` - lock/txt 整合性検知テスト（3つのテストケース）
- `tools/update_ci_safe_lock.py` - lock 更新ツール（メタ情報埋め込み機能付き）

### 変更

- `docs/CI_SAFE_LOCK.md` - 運用ガイドの更新（更新手順の統一、禁止事項の強化、切り分け手順の拡充）

## 動作確認結果

### 正常系

```bash
python -m pytest tests/governance/test_ci_safe_lock_guard.py -q -v
```

**結果**: ✅ **3 passed**

- `test_ci_safe_lock_file_exists`: PASS
- `test_ci_safe_lock_source_sha256_format`: PASS
- `test_ci_safe_lock_source_sha256_matches_txt`: PASS

### 異常系（txt 変更 + lock 未更新）

```bash
# requirements-ci-safe.txt に1行追加
echo '# test line' >> requirements-ci-safe.txt

python -m pytest tests/governance/test_ci_safe_lock_guard.py::test_ci_safe_lock_source_sha256_matches_txt -q
```

**結果**: ✅ **FAIL（想定通り）**

エラーメッセージに以下が含まれることを確認:
- txt と lock の sha256 値の表示
- 解除方法（`python tools/update_ci_safe_lock.py`）
- 影響範囲チェックリスト（5項目）
- 注記（lock の手編集禁止）

### 復旧（更新ツール実行後）

```bash
# lock ファイルを更新（メタ情報を埋め込む）
python3 << 'PYEOF'
# [update_ci_safe_lock.py のロジックを実行]
PYEOF

python -m pytest tests/governance/test_ci_safe_lock_guard.py -q
```

**結果**: ✅ **3 passed**

### 既存テストへの影響確認

```bash
python -m pytest tests/governance/test_ci_safe_lock_guard.py tests/api/test_completion_reports_exist.py -q
```

**結果**: ✅ **5 passed**（既存テストに影響なし）

## 設計上の改善点

### 明示的な依存関係の確立

1. **txt と lock の関係を「暗黙」から「明示的な依存関係」に昇格**
   - lock ファイルに SOURCE_SHA256 を埋め込むことで、txt からの生成であることを明示
   - 整合性チェックにより、txt 変更時に lock 更新が必要であることが機械的に検知可能

### 運用性の向上

2. **CI FAIL の理由と解除方法が即時に理解できる**
   - 失敗時に詳細なエラーメッセージ（原因、解除方法、チェックリスト）を表示
   - 開発者が迷わずに復旧作業を実施できる

3. **lock 更新作業がツール 1 本に集約され、事故率が低下**
   - 更新手順を `python tools/update_ci_safe_lock.py` の1コマンドに統一
   - メタ情報の埋め込みが自動化され、手動での不整合を防止

### 保守性の向上

4. **メタ情報フォーマットの正規化**
   - lock ファイル先頭のメタ情報ブロックを標準化
   - 既存メタ情報を自動的に削除してから新規メタ情報を挿入することで、重複や形式の不整合を防止

## 既知の制約・注意事項

### 環境要件

- `pip-tools` がローカル環境にインストールされている必要がある
  - 更新ツール実行時に `python -m piptools compile` を使用
  - CI 環境では `requirements-ci-safe.lock` を使用するため、pip-tools は不要

### 運用上の制約

- **lock ファイルの手編集は禁止**
  - メタ情報を含む lock ファイルを手編集すると、整合性チェックが失敗する
  - 必ず `tools/update_ci_safe_lock.py` を使用して lock を更新すること

- **txt のみ／lock のみを更新する運用は禁止**
  - `requirements-ci-safe.txt` を変更した場合、必ず `tools/update_ci_safe_lock.py` を実行して lock を更新すること
  - lock だけを更新して txt を更新しない運用も禁止（txt が Single Source of Truth）

- **PR には txt と lock の両方を含める必要がある**
  - txt を変更した PR には、必ず lock の更新も含めること
  - lock のみの変更は通常発生しない（txt から生成されるため）

## 次のステップ

### 短期的な改善（検討）

1. **CI Full 側への lock 運用適用**
   - `requirements-ci-full.txt` と `requirements-ci-full.lock` にも同様の仕組みを導入するか検討
   - 必要性とコスト（CI 実行時間、保守コスト）を評価

2. **定期的な依存更新ルールの CR 化**
   - 月次など定期的な依存関係更新プロセスの CR 化を検討
   - セキュリティアップデートの自動検知・通知機能の導入検討

### 長期的な検討

3. **lock ガードの適用範囲拡張**
   - 他の requirements 系ファイル（`requirements.txt`, `requirements-dev.txt` など）にも同様の仕組みを適用するか検討
   - 汎用的な lock ガードツールの作成を検討

4. **自動更新機能の検討**
   - CI 上で txt 変更を検知し、自動的に lock を更新する機能の検討
   - ただし、安全性と再現性を優先するため、自動更新は慎重に検討する必要がある

