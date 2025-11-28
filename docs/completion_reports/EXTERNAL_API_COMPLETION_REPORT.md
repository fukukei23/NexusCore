# 外部統合 API 実装完了レポート

## 実装日時

2025-11-28

## 概要

VSCode / Chrome 拡張などの外部ツールから NexusCore SaaS の Self-Healing Run を発火できる REST API を実装しました。

## 実装ステップ

### E-1: APIキー認証つき外部統合 API

#### E-1-1. APIキー認証ヘルパーの追加

**ファイル**: `src/nexuscore/webapp/auth_api.py`（新規作成）

**実装内容**:
- `_resolve_user_from_api_key()`: API キーから User を解決する関数
  - `ApiKey.hash_token()` を使用してトークンをハッシュ化
  - `token_hash` で ApiKey を検索
  - 対応する User を返す
- `api_key_required`: API キー認証を要求するデコレータ
  - `X-Api-Key` ヘッダまたは `api_key` クエリパラメータから API キーを取得
  - 有効な場合は `g.current_api_user` に User をセット
  - 無効な場合は 401 JSON を返す

#### E-1-2. 外部統合用 API Blueprint の追加

**ファイル**: `src/nexuscore/webapp/api_external.py`（新規作成）

**実装内容**:
- `external_api_bp`: `/api/v1` プレフィックスの Blueprint を作成
- **GET /api/v1/projects**: プロジェクト一覧を取得
  - 認証: `@api_key_required`
  - レスポンス: ユーザーが所有するプロジェクト一覧（id, name, repo_url, local_path, created_at）
- **POST /api/v1/projects/<project_id>/run**: Self-Healing Run を発火
  - 認証: `@api_key_required`
  - リクエスト: `requirement`, `autonomy_level`, `fast_lane`
  - 動作: プロジェクトの所有権を確認 → Run を作成 → Celery/同期実行
  - レスポンス: `run_id`, `project_id`, `status`, `queue_mode`
  - ステータスコード: 200（同期）/ 202（非同期）
- **GET /api/v1/projects/<project_id>/runs/latest**: 最新の Run ステータスを取得
  - 認証: `@api_key_required`
  - レスポンス: 最新 Run の概要（id, run_id, status, started_at, finished_at）

#### E-1-3. Blueprint 登録 & CORS 対応

**ファイル**: `src/nexuscore/webapp/__init__.py`

**実装内容**:
- `api_external.external_api_bp` を Flask アプリに登録
- Flask-CORS を使用して `/api/v1/*` に対して CORS を許可
  - 開発フェーズでは `origins: "*"`（本番ではホスト制限を推奨）
  - `flask-cors` がインストールされていない場合は警告ログのみ

**ファイル**: `requirements.txt`

**実装内容**:
- `Flask-CORS` を依存関係に追加

#### E-1-4. 簡易テスト追加

**ファイル**: `tests/webapp/test_external_api.py`（新規作成）

**テスト内容**:
- API キーなしでアクセス → 401 が返る
- 有効な API キーでプロジェクト一覧取得 → 200 & 自分のプロジェクトだけ返る
- 無効な API キー → 401
- `requirement` 未指定で Run 発火 → 400
- 正常なリクエストで Run 発火 → 200/202 & Run が作成される
- 存在しないプロジェクト → 404
- 最新 Run 取得 → 200 & Run 情報が返る
- Run が存在しない場合 → 200 & `run: null`

### E-2: VSCode / Chrome 拡張から Run 発火

#### E-2-1. 外部統合ガイドの追加

**ファイル**: `docs/external_run_api_examples.md`（新規作成）

**内容**:
- エンドポイント概要
- curl リクエスト例
- VSCode Extension (TypeScript) サンプル
- Chrome Extension (Manifest V3) サンプル
- Python クライアント例
- API キーの発行方法
- エラーハンドリング
- ステータス確認方法

#### E-2-2. README から docs へのリンク追加

**ファイル**: `README.md`

**実装内容**:
- 「External Integrations」セクションを追加
- `docs/external_run_api_examples.md` へのリンクを追加

## 変更ファイル一覧

### 新規作成ファイル

1. **`src/nexuscore/webapp/auth_api.py`**
   - APIキー認証ヘルパー

2. **`src/nexuscore/webapp/api_external.py`**
   - 外部統合用 API Blueprint

3. **`tests/webapp/test_external_api.py`**
   - 外部統合 API のテスト

4. **`docs/external_run_api_examples.md`**
   - 外部統合ガイド（VSCode / Chrome / Python サンプル）

### 変更ファイル

1. **`src/nexuscore/webapp/__init__.py`**
   - `api_external.external_api_bp` を登録
   - Flask-CORS を設定

2. **`requirements.txt`**
   - `Flask-CORS` を追加

3. **`README.md`**
   - 「External Integrations」セクションを追加

## 動作確認結果

### 静的解析結果

- リンターエラー: なし
- 型チェック: 問題なし

### 設計上の改善点

1. **認証の分離**:
   - API キー認証は `auth_api.py` に分離し、既存の OAuth 認証と独立
   - `g.current_api_user` を使用して、API キー経由のユーザーを識別

2. **エラーハンドリング**:
   - 無効な API キー: 401 Unauthorized
   - プロジェクト未所有: 404 Not Found
   - 必須パラメータ欠落: 400 Bad Request
   - 実行エラー: 500 Internal Server Error（同期実行時）

3. **CORS 対応**:
   - 開発フェーズでは `origins: "*"` で全ドメインを許可
   - 本番環境では使用ドメインに限定することを推奨

4. **実行モードの選択**:
   - `NEXUS_USE_CELERY` 環境変数で Celery 非同期 / 同期実行を切り替え
   - 非同期: 202 Accepted（キューに入った）
   - 同期: 200 OK（実行完了）または 500（エラー）

## 既知の制約・注意事項

1. **API キーの発行**:
   - 現在はデータベースに直接登録する必要があります
   - 将来的には Webapp UI から API キーを発行できる機能を追加予定

2. **CORS 設定**:
   - 開発フェーズでは `origins: "*"` を使用
   - 本番環境では使用ドメインに限定することを強く推奨

3. **認証トークンの管理**:
   - API キーは SHA-256 でハッシュ化して保存
   - 生成されたキーは一度だけ表示可能（紛失時は再発行が必要）

4. **プロジェクト所有権**:
   - API キーで認証されたユーザーが所有するプロジェクトのみアクセス可能
   - 他のユーザーのプロジェクトにはアクセスできない

## 次のステップ

### 推奨される動作確認

1. **API エンドポイントの確認**:
   ```bash
   # プロジェクト一覧取得
   curl -H "X-Api-Key: YOUR_API_KEY" https://your-nexuscore-host/api/v1/projects

   # Run 発火
   curl -X POST -H "X-Api-Key: YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"requirement": "Test"}' \
     https://your-nexuscore-host/api/v1/projects/1/run
   ```

2. **テストの実行**:
   ```bash
   python -m pytest tests/webapp/test_external_api.py -v
   ```

3. **CORS の確認**:
   - ブラウザの開発者ツールで CORS ヘッダーが正しく設定されているか確認

### 将来の拡張

1. **API キー管理 UI**:
   - Webapp UI から API キーの発行・削除・一覧表示

2. **レート制限**:
   - API キーごとのレート制限（例: 1分間に10リクエスト）

3. **Webhook 通知**:
   - Run 完了時に外部 URL に Webhook を送信

4. **API バージョニング**:
   - `/api/v2/` などのバージョン管理

## 関連ドキュメント

- `docs/external_run_api_examples.md` - 外部統合 API の使用例
- `docs/saas_architecture.md` - SaaS アーキテクチャの詳細

