# CR-FASTAPI-003: GitHub Self-Healing Webhook API の FastAPI 移行 - 完了レポート

## 実装日時

2025年12月3日

## 概要

### 目的
GitHub Self-Healing Webhook を FastAPI 化し、正式な `/api/v1/github/webhook` API として実装する。
既存の Flask 実装 (`src/nexuscore/api/github_webhook_handler.py`) と互換性を保ちながら、
Pydantic による型安全性と OpenAPI スキーマへの自動反映を実現する。

### ゴール
- GitHub Webhook（pull_request events）を FastAPI で受ける
- Pydantic BaseModel による型定義
- 署名検証ロジックの実装（GitHub Webhook 標準）
- Self-Healing Service を確実に呼べるように統合
- FastAPI TestClient によるテスト作成
- OpenAPI 定義に反映
- 既存の Flask 実装を破壊しない

### 原則
- 既存の Flask アプリケーション設定には触れない
- 既存の `github_webhook()` 関数を再利用
- 既存のテスト (`tests/api/test_github_self_healing_webhook.py`) の期待値に準拠
- すべての差分は unified diff 形式で提示

## 実装ステップ

### Step 1: 仕様調査（既存のFlask実装を読み取る）

**確認したファイル**:
- `src/nexuscore/api/server.py` - Flask実装のエンドポイント (`/api/github/webhook`)
- `src/nexuscore/api/github_webhook_handler.py` - Webhook処理ロジック
- `src/nexuscore/api/github_self_healing_webhook.py` - Self-Healing実行ロジック
- `tests/api/test_github_self_healing_webhook.py` - 既存のテスト（仕様ドキュメントとして使用）

**解析結果**:
- **パス**: `/api/github/webhook`
- **HTTPメソッド**: POST
- **使用ヘッダ**:
  - `X-GitHub-Event`: イベントタイプ（"pull_request" のみ処理）
  - `X-GitHub-Delivery`: Webhook delivery ID（デバッグ用）
- **使用している payload のフィールド**:
  - `action`: イベントアクション（"opened", "synchronize", "reopened", "ready_for_review"）
  - `repository.full_name`: リポジトリのフルネーム
  - `pull_request.number`: PR番号
  - `pull_request.draft`: ドラフトPRかどうか
  - `pull_request.labels`: ラベル一覧
  - `pull_request.head.sha`: head ブランチのコミットSHA
  - `pull_request.base.ref`: base ブランチ名
- **呼び出しているサービス関数**: `github_webhook()` (`nexuscore.api.github_self_healing_webhook`)
- **レスポンス形式**:
  - 成功時: `{"accepted": True, "result": {...}}`
  - 拒否時: `{"accepted": False, "reason": "..."}`
  - エラー時: `{"accepted": False, "error": "..."}`

### Step 2: Pydantic Schema を作成

**ファイル**: `src/nexuscore/api/schemas/github_webhook.py`

**実装内容**:
1. **GitHubRepository**:
   - `full_name: str` (必須)

2. **GitHubPullRequestLabel**:
   - `name: str` (必須)

3. **GitHubPullRequestHead**:
   - `sha: str` (必須)

4. **GitHubPullRequestBase**:
   - `ref: str` (必須)

5. **GitHubPullRequest**:
   - `number: int` (必須)
   - `draft: bool` (デフォルト: False)
   - `labels: List[GitHubPullRequestLabel]` (デフォルト: [])
   - `head: GitHubPullRequestHead` (必須)
   - `base: GitHubPullRequestBase` (必須)

6. **GitHubWebhookPayload**:
   - `action: str` (必須)
   - `repository: GitHubRepository` (必須)
   - `pull_request: GitHubPullRequest` (必須)
   - `extra = "allow"` (追加フィールドを許容)

7. **GitHubWebhookResponse**:
   - `accepted: bool` (必須)
   - `result: Optional[Dict[str, Any]]` (任意)
   - `reason: Optional[str]` (任意)
   - `error: Optional[str]` (任意)
   - `status: Optional[Literal["skipped", "fixed", "not_fixed", "no_issues", "error"]]` (任意)
   - `summary: Optional[str]` (任意)

**実装理由**:
- 既存のFlask実装の仕様に完全に準拠
- Pydantic の型安全性を活用
- OpenAPI スキーマに自動反映される
- 既存の実装で実際に使用されているフィールドのみを定義

### Step 3: FastAPI ルータ実装

**ファイル**: `src/nexuscore/api/routes/github_webhook.py`

**実装内容**:
1. **署名検証関数** (`verify_github_signature`):
   - GitHub Webhook の標準的な署名検証を実装
   - `X-Hub-Signature-256` ヘッダーを使用
   - `GITHUB_WEBHOOK_SECRET` 環境変数からシークレットを取得
   - `hmac.compare_digest` を使用してタイミング攻撃を防止

2. **POST `/api/v1/github/webhook` エンドポイント**:
   - リクエストヘッダー: `X-GitHub-Event`, `X-GitHub-Delivery`, `X-Hub-Signature-256`
   - リクエストボディ: JSON形式のGitHub Webhookペイロード
   - レスポンスモデル: `GitHubWebhookResponse`
   - ステータスコード: 200 (成功), 401 (署名検証失敗), 500 (内部エラー)

3. **処理フロー**:
   - イベントタイプの確認（"pull_request" のみ処理）
   - リクエストボディの取得
   - 署名検証（オプション、`GITHUB_WEBHOOK_SECRET` が設定されている場合のみ）
   - JSON ペイロードのパース（Pydanticモデルで検証）
   - `github_webhook()` 関数の呼び出し（既存の実装を再利用）
   - PR コメント投稿（オプション、`GITHUB_SELF_HEALING_TOKEN` が設定されている場合）
   - Slack 通知送信（オプション、`NEXUS_SLACK_WEBHOOK_URL` が設定されている場合）

4. **ヘルパー関数**:
   - `_post_pr_comment_if_configured()`: PR コメント投稿（既存のFlask実装と同じロジック）
   - `_send_slack_notification_if_configured()`: Slack 通知送信（既存のFlask実装と同じロジック）

**実装理由**:
- 既存のFlask実装と互換性を保つ
- GitHub Webhook の標準的な署名検証を実装
- 既存の `github_webhook()` 関数を再利用することで、既存のロジックを壊さない

### Step 4: FastAPI アプリへのルータ登録

**ファイル**: `src/nexuscore/api/fastapi_app.py`

**変更内容**:
- `from .routes import github_webhook` を追加
- `app.include_router(github_webhook.router)` を追加

**確認事項**:
- OpenAPI スキーマに `/api/v1/github/webhook` が自動反映される
- `/api/docs` でエンドポイントが表示される

### Step 5: FastAPI 用テストの作成

**ファイル**: `tests/api/test_fastapi_github_webhook.py`

**実装内容**:
8個のテストケースを実装：
1. `test_webhook_endpoint_accepts_valid_pull_request_event` - 正常系：署名 OK、対象イベント（PR opened/synchronize）
2. `test_webhook_endpoint_rejects_invalid_signature` - エラー系：署名不正 → 401
3. `test_webhook_endpoint_ignores_non_pull_request_event` - イベント対象外：pull_request 以外のイベント → status == "ignored"
4. `test_webhook_endpoint_handles_missing_signature_header` - 署名ヘッダーがない場合の処理
5. `test_webhook_endpoint_handles_skipped_pr` - PRが条件を満たさない場合（ラベルなし、draft PRなど）の処理
6. `test_webhook_endpoint_is_documented_in_openapi` - OpenAPI スキーマの確認
7. `test_webhook_endpoint_handles_invalid_json` - 不正なJSONペイロードの処理
8. `test_webhook_endpoint_without_secret_allows_requests` - シークレットが設定されていない場合、署名検証をスキップする

**実装理由**:
- 既存のFlaskテスト (`tests/api/test_github_self_healing_webhook.py`) の期待値に準拠
- FastAPI版の動作を保証
- OpenAPI スキーマの整合性を確認
- 署名検証の動作を確認

## 変更ファイル一覧

### 新規作成ファイル
- `src/nexuscore/api/schemas/github_webhook.py` - GitHub Webhook API 用のPydanticスキーマ
- `src/nexuscore/api/routes/github_webhook.py` - GitHub Webhook ルータの実装
- `tests/api/test_fastapi_github_webhook.py` - FastAPI GitHub Webhook エンドポイントのテスト

### 変更ファイル
- `src/nexuscore/api/fastapi_app.py` - GitHub Webhook ルータの登録

### 変更なし（既存実装を再利用）
- `src/nexuscore/api/github_self_healing_webhook.py` - 既存の `github_webhook()` 関数を再利用
- `src/nexuscore/api/github_webhook_handler.py` - 既存のFlask実装（変更なし）

## 動作確認結果

### 静的解析結果
- リンターエラー: なし
- 型チェック: 問題なし

### テスト結果

**実行コマンド**:
```bash
source myenv_linux/bin/activate
export PYTHONPATH=/home/yn441611/NexusCore/src:$PYTHONPATH
export GITHUB_WEBHOOK_SECRET=test-webhook-secret-123
python -m pytest tests/api/test_fastapi_github_webhook.py -v
```

**結果**:
- 8個のテストケース中、8個が成功
- すべてのテストが正常に通過

**確認項目**:
- ✅ `/api/v1/github/webhook` エンドポイントが 200 を返す
- ✅ レスポンスに `accepted`, `result` が含まれる
- ✅ 署名検証が正しく動作する（不正な署名で 401 を返す）
- ✅ pull_request 以外のイベントを拒否する
- ✅ PRが条件を満たさない場合に適切に処理する
- ✅ OpenAPI スキーマに `/api/v1/github/webhook` が定義されている
- ✅ 不正なJSONペイロードを適切に処理する
- ✅ シークレットが設定されていない場合、署名検証をスキップする

### コードレビュー結果
- ✅ `.cursorrules` のルールに準拠
- ✅ Pydantic BaseModel を使用したリクエスト/レスポンスモデル
- ✅ `/api/v1` プレフィックスの使用
- ✅ 既存のFlask実装に影響なし
- ✅ 既存の `github_webhook()` 関数を再利用

## 設計上の改善点

### アーキテクチャの改善
1. **型安全性の向上**
   - Pydantic モデルによるリクエスト/レスポンスの型定義
   - OpenAPI スキーマへの自動反映
   - IDE での型補完とエラーチェックが可能に

2. **署名検証の実装**
   - GitHub Webhook の標準的な署名検証を実装
   - `hmac.compare_digest` を使用してタイミング攻撃を防止
   - 開発環境では署名検証をスキップ可能（`GITHUB_WEBHOOK_SECRET` が設定されていない場合）

3. **既存実装との共存**
   - 既存の `github_webhook()` 関数を再利用
   - 既存のFlask実装と共存可能な設計
   - 段階的な移行が可能

### 将来の拡張性への配慮
1. **他のイベントタイプへの対応**
   - 現時点では `pull_request` イベントのみ処理
   - 将来的に `push`, `issue_comment` などのイベントにも対応可能な構造

2. **署名検証方式の拡張**
   - 現時点では `X-Hub-Signature-256` のみ対応
   - 将来的に `X-Hub-Signature` (SHA-1) にも対応可能な構造

### コード品質の向上
1. **明確な型定義**
   - Pydantic BaseModel による明示的なリクエスト/レスポンスモデル
   - OpenAPI スキーマへの自動反映
   - ドキュメント生成の自動化

2. **テストカバレッジ**
   - 既存のFlaskテストの期待値に準拠したテスト実装
   - FastAPI版の動作を保証
   - OpenAPI スキーマの整合性を確認

## 既知の制約・注意事項

### 既存コードとの互換性
- ✅ 既存の Flask アプリケーション (`src/nexuscore/api/server.py`) には影響なし
- ✅ 既存の `github_webhook()` 関数を再利用（既存のロジックを壊さない）
- ✅ 既存のFlask実装と共存可能な設計

### 制限事項やトレードオフ
1. **署名検証**
   - 現時点では `X-Hub-Signature-256` (SHA-256) のみ対応
   - `GITHUB_WEBHOOK_SECRET` 環境変数が設定されていない場合、署名検証をスキップ（開発環境など）

2. **イベントタイプ**
   - 現時点では `pull_request` イベントのみ処理
   - 他のイベントタイプは拒否される（既存のFlask実装と同じ動作）

3. **実行環境**
   - WSL Ubuntu 環境での動作確認済み
   - `myenv_linux` 仮想環境での動作確認済み
   - `GITHUB_WEBHOOK_SECRET` 環境変数の設定が必要（本番環境）

### 移行時の注意点
- FastAPI アプリは既存の Flask アプリとは別ポートで実行可能
- 既存の `github_webhook()` 関数を再利用するため、既存のロジックを壊さない
- 将来的に Flask から FastAPI への完全移行を検討する際は、段階的な移行を推奨

## 次のステップ

### 推奨されるフォローアップアクション

1. **他のエンドポイントの移行**
   - CR-FASTAPI-000 で棚卸しした Public endpoints の移行を継続
   - `/api/projects`, `/api/runs` などの移行

2. **イベントタイプの拡張**
   - `push` イベントの対応
   - `issue_comment` イベントの対応

3. **署名検証方式の拡張**
   - `X-Hub-Signature` (SHA-1) への対応（後方互換性のため）

4. **ドキュメント整備**
   - OpenAPI スキーマの詳細化
   - エンドポイントごとの説明文追加
   - 使用例の追加

5. **監視・ロギングの改善**
   - Webhook 受信のログ記録
   - エラー発生時のアラート通知

## 関連ドキュメント

- [API Inventory (CR-FASTAPI-000)](./api_inventory.md)
- [FastAPI Migration Prompts](./README.md)
- [CR-FASTAPI-001 Completion Report](./CR-FASTAPI-001_COMPLETION_REPORT.md)
- [CR-FASTAPI-002 Completion Report](./CR-FASTAPI-002_COMPLETION_REPORT.md)
- [.cursorrules](../../.cursorrules)

## まとめ

CR-FASTAPI-003 の実装により、GitHub Self-Healing Webhook API の FastAPI 版が完成しました。既存のFlask実装と互換性を保ちながら、Pydantic による型安全性と OpenAPI スキーマへの自動反映を実現しました。既存の `github_webhook()` 関数を再利用することで、既存のロジックを壊さず、段階的な移行が可能になりました。

すべてのテストが成功し、`.cursorrules` のルールに準拠した実装が完了しています。

