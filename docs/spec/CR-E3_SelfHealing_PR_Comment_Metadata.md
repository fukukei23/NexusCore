# CR-E3: Self-Healing PR コメント メタ情報強化

**作成日**: 2025-12-10
**ステータス**: Completed
**優先度**: High
**対象**: NexusCore Self-Healing / GitHub 連携 / CI

---

## 1. 背景

NexusCore では、Self-Healing 実行結果を GitHub PR コメントとして投稿しているが、現状は「レビューコメント的なテキスト」が中心であり、以下の課題がある：

- 実行時間・成功率・使用モデルなどの **定量情報が PR から一目で分からない**
- どの RunHistory / LogHistory に対応するかが不透明で、**後からトレースしにくい**
- VC・企業向けデモで「どれだけ自己修復が効いているか」を説明するための材料が足りない

本 CR（E-3）では、Self-Healing 実行結果の PR コメントに **メタ情報ブロックを標準化して追加**し、「NexusCore がどの程度 Self-Healing を実現しているか」を外部から即座に判断できる状態を作る。

---

## 2. 目的・ゴール

### 2.1 目的

- Self-Healing 実行結果の PR コメントに、以下のメタ情報を含める：
  - 実行時間（開始・終了時刻 / 所要時間）
  - 過去 N 回（例: 30 回）の Self-Healing 成功率
  - 使用モデル（例: gpt-4.1, gpt-4.1-mini など）
  - 生成パッチの行数（+行 / -行）
  - 影響ファイル数
  - run_id（RunHistory / LogHistory と紐づく一意 ID）

- PR コメントの組み立てを **1 箇所（build_pr_comment() 等）に集約**し、今後の拡張が容易な設計にする。

### 2.2 Definition of Done（完了条件）

- Self-Healing 実行後の PR コメント内に、標準化されたメタ情報ブロックが追加されている。
- メタ情報には少なくとも以下が含まれる：
  - start_time / end_time / duration
  - success_rate（過去 N 回）
  - model_name
  - added_lines / removed_lines / changed_files
  - run_id
- Comment 組み立てロジックが一箇所に集約されている（build_pr_comment() 等）。
- 関連テスト（ユニット・統合）が追加され CI でグリーン。
- 既存の PR コメントフォーマットとの後方互換性が保たれている（少なくとも壊れていない）。

---

## 3. スコープ / 非スコープ

### 3.1 スコープ

- Self-Healing 実行結果からメタ情報を収集するロジックの追加・整備
- 収集したメタ情報を PR コメントに整形するロジック（build_pr_comment）
- GitHub 連携部分（Webhook ハンドラ or GitHub Actions 側スクリプト）の修正
- メタ情報に関するテスト追加（フォーマット / 値の整合性）

### 3.2 非スコープ

- Self-Healing 自体のアルゴリズム変更
- RunHistory / LogHistory の構造変更（必要なら読み出しロジックのみ修正）
- Before/After 差分サマリー（これは E-4 の対象）
- Observability ダッシュボード（別 CR）

---

## 4. 仕様詳細

### 4.1 メタ情報フィールド定義

1. **実行時間**
   - `start_time`: Self-Healing 開始時刻（ISO8601 / UTC）
   - `end_time`: Self-Healing 終了時刻（ISO8601 / UTC）
   - `duration_seconds`: 経過時間（秒）

2. **成功率**
   - `success_rate_last_n`: 過去 N 回（デフォルト 30）の成功率（%）
   - `recent_runs_window`: N の値（コメントに表示してもよい）

3. **使用モデル**
   - `primary_model`: メインで利用したモデル名（例: `gpt-4.1`）
   - `aux_models`: 補助的に使用したモデル（あれば配列）

4. **変更規模**
   - `changed_files`: 影響を受けたファイル数
   - `added_lines`: 追加行数（diff ベース）
   - `removed_lines`: 削除行数（diff ベース）

5. **Run 識別情報**
   - `run_id`: Self-Healing 実行単位の一意 ID
   - `pr_number`: 関連 PR 番号
   - `commit_sha`: 対象コミットの SHA（短縮／フルは実装側で選択）

### 4.2 PR コメントフォーマット（例）

Markdown ブロックの例：

```markdown
### 🛠 Self-Healing Summary

- Run ID: `RUN-20251210-00123`
- PR: #123
- Commit: `abc1234`

**Execution**
- Start: 2025-12-10T07:11:30Z
- End:   2025-12-10T07:11:49Z
- Duration: 19.7s
- Model: gpt-4.1 (primary), gpt-4.1-mini (aux)

**Effect**
- Changed files: 3
- +120 / -40 lines

**Reliability**
- Success rate (last 30 runs): 86.7%
```

実際には絵文字不要など方針があれば簡略化してよい。重要なのは **機械的に parse 可能な構造** を維持すること。

### 4.3 設計方針

#### 4.3.1 build_pr_comment() の新設

PR コメントは、下記情報を引数に取る関数で組み立てる：

```python
def build_pr_comment(
    run_id: str,
    pr_number: int | str,
    commit_sha: str,
    start_time: datetime,
    end_time: datetime,
    model_name: str,
    changed_files: int,
    added_lines: int,
    removed_lines: int,
    success_rate_last_n: float | None = None,
    recent_runs_window: int = 30,
    summary_text: str | None = None,  # Self-Healing の自然言語サマリ
) -> str:
    ...
```

GitHub 連携側（Webhook ハンドラ or Actions）は、この関数を呼び出すだけにする。

これにより、PR コメントフォーマットが中央集約される。

**注意**: 既存の `build_pr_comment(ctx: PRCommentContext)` が存在するため、既存実装を拡張する形で実装する。

#### 4.3.2 メタ情報の取得元

- `run_id` → Self-Healing 実行パイプライン側（実行開始時に払い出し）
- `start_time` / `end_time` → 実行パイプラインから
- `model_name` → Self-Healing 実行コンフィグ or ログ
- `changed_files` / `added_lines` / `removed_lines` → diff ツールの結果（既存の diff_tools.py 等から）
- `success_rate_last_n` → RunHistory から直近 N 件を取得し、成功率を算出

#### 4.3.3 整合性ルール

- `run_id` をキーに、RunHistory / LogHistory / PR コメント の三者を紐づける。
- `run_id` はコメント内に必ず埋め込む（人間・機械双方がたどれるようにする）。

---

## 5. 変更対象ファイル

**既存実装の確認**:
- `src/nexuscore/integration/github_pr_comment.py` - 既存の `build_pr_comment(ctx: PRCommentContext)` と `PRCommentContext` モデルが存在
- `src/nexuscore/integration/github_pr_comment.py` - `_collect_run_metrics()` 関数で既に一部のメトリクスを収集
- `src/nexuscore/integration/github_pr_comment.py` - `_compute_recent_success_rate()` 関数で成功率を計算
- `src/nexuscore/api/github_self_healing_webhook.py` - `format_pr_comment()` 関数が PR コメントを生成

**変更が必要なファイル**:
- `src/nexuscore/integration/github_pr_comment.py` - `build_pr_comment()` を拡張してメタ情報ブロックを追加
- `src/nexuscore/integration/github_pr_comment.py` - `PRCommentContext` モデルにメタ情報フィールドを追加（必要に応じて）
- `src/nexuscore/integration/github_pr_comment.py` - `_collect_run_metrics()` を拡張して追加のメタ情報を収集

**新規作成が必要なファイル**:
- `tests/integration/test_github_pr_comment_metadata.py` - メタ情報ブロックのテスト

---

## 6. リスクと対策

### 6.1 PR コメントが長くなりすぎるリスク

**対策**: 詳細な差分内容（E-4 対象）は別 CR に切り、E-3 ではサマリのみとする。

### 6.2 RunHistory に依存することで、履歴データが壊れていると成功率が出せないリスク

**対策**: 成功率計算に失敗した場合は「N/A」表示とし、コメント出力自体は継続。

### 6.3 build_pr_comment() が将来肥大化するリスク

**対策**: メタ情報の構造を dataclass / Pydantic モデル等で定義し、フォーマットロジックと分離。

---

## 7. 完了後のフォロー

- E-4（差分サマリー）の PR コメント統合では、本 CR で導入した `build_pr_comment()` を拡張する。
- Observability ダッシュボードから `run_id` 経由で PR コメントビューに飛べるようにする構想の前提になる。

---

## 2. Cursor 用実装指示書（Implementation Instruction for Cursor）

### 1. タスクの目的

このタスク (E-3) でやることは「Self-Healing の実行結果を GitHub PR コメントに出すときに、メタ情報ブロックを追加すること」。

メタ情報とは、以下のような情報を指す：
- 実行時間（開始・終了・所要時間）
- 過去 N 回の Self-Healing 成功率
- 使用モデル名
- 変更ファイル数・追加行数・削除行数
- run_id（RunHistory と紐づく ID）
- PR 番号 / 対象コミット SHA

### 2. スコープ

AI が変更してよいのは、Self-Healing PR コメント出力に直接関係する範囲のみ。

**変更してよいファイル（例）**
- GitHub 連携レイヤ
  - `src/nexuscore/api/routes/github_webhook.py`
  - `src/nexuscore/integration/github_pr_comment.py`（PR コメントヘルパーなど）
- Self-Healing 実行レイヤ
  - `src/nexuscore/services/self_healing_service.py`
- diff / 統計
  - `src/nexuscore/utils/diff_tools.py` または類似ユーティリティ
- テスト
  - `tests/**`（Self-Healing / PR コメント関連のテストのみ）
- ドキュメント
  - `docs/spec/CR-E3_SelfHealing_PR_Comment_Metadata.md`
  - `docs/api/README.md`（必要なら簡単な追記）

**変更してはならないもの**
- FastAPI のエンドポイント仕様そのもの（ルーティング・リクエスト/レスポンス定義の変更）
- Self-Healing のアルゴリズムや自己修復ロジック（E-3 の範囲を超える改変）
- Observability ダッシュボードの UI / 構成
- SDK 実装（CR-FASTAPI-019 の範囲）

E-3 では「コメント内容」と「コメントに埋め込むためのメタ情報取得」だけに集中する。

### 3. 実装ルール

1. **build_pr_comment() の導入・利用**
   - PR コメント本文は、必ず `build_pr_comment()`（または同等の単一関数）で組み立てる。
   - この関数は、run_id / start_time / end_time / model_name / changed_files などの引数から、Markdown テキストを構成する。
   - **注意**: 既存の `build_pr_comment(ctx: PRCommentContext)` が存在するため、既存実装を拡張する形で実装する。

2. **メタ情報の取得**
   - run_id, start_time, end_time, model_name は Self-Healing 実行パイプラインから取得する。
   - changed_files / added_lines / removed_lines は diff ユーティリティから取得する。
   - success_rate_last_n は RunHistory から「直近 N 件」を集計して算出する。
   - どこから取得するかをコードコメントで明示する。

3. **後方互換性**
   - 既存の PR コメント本文（レビュー内容など）が消えないようにする。
   - 既存コメントに「メタ情報ブロックを追加」する方針で実装すること。

### 4. テスト

- AI は、PR コメント生成に関するテストを **必ず追加・更新** する。
- テストでは、少なくとも次を検証すること：
  - run_id / model_name / duration / changed_files の文字列がコメント内に含まれること
  - success_rate_last_n が数値としてフォーマットされているか（利用可能な場合）
- テストを無効化 (skip, xfail) したりコメントアウトしてはならない。

### 5. 禁止事項

AI は以下をしてはならない：
- Self-Healing のアルゴリズムを変更する（パッチ生成ロジック等）
- 新しいエンドポイントを勝手に追加する
- PR コメントへの出力を完全に別形式（HTML など）に変える
- E-4（差分サマリー）に相当する詳細な diff コンテンツを追加する
  → 差分サマリは別タスク (E-4) で扱う

### 6. Diff 出力のルール

- 変更内容を出すときは、必ず unified diff 形式（`---` / `+++` / `@@`）で出す。
- Diff は「このタスクで変更を許可されたファイル」に限定する。
- 関係ないファイルの差分が混ざった場合は、すぐに scope を修正して出し直す。

### 7. 完了条件（AI 観点）

AI は、以下がすべて true のとき「E-3 は完了」とみなす：
- PR コメントにメタ情報ブロックが含まれている。
- コメント内に run_id / 実行時間 / 使用モデル / 変更規模 / 成功率（可能な場合）が出力されている。
- 既存の PR コメントの内容が消えていない。
- 関連テストが追加され、CI でグリーンになっている。

---

## 関連ドキュメント

- [CR-FASTAPI-019 Completion Report](../api/CR-FASTAPI-019_COMPLETION_REPORT.md) - TypeScript SDK 商品化
- [エラーコードカタログ](../api/ERROR_CODE_CATALOG.md)
- [API README](../api/README.md)

