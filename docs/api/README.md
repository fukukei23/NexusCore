# FastAPI Migration Prompts & Documentation

このディレクトリには、NexusCore の Flask → FastAPI 移行に関するプロンプトテンプレートと完了レポートが含まれています。

## 重要: API 構成の変更

**外部公開 API は FastAPI ベースの `/api/v1/**` が正式版です（単一の正）。**

Flask REST API（`/api/v1/*` 配下のエンドポイント）は **CR-FASTAPI-010 で完全削除されました**。
すべての REST API は FastAPI 側に統一されました。

詳細は [FASTAPI_MIGRATION_STATUS.md](./FASTAPI_MIGRATION_STATUS.md) を参照してください。

- **FastAPI**: 公開 API 層（`/api/v1/*`）- 正式版（単一の正）
- **Flask**: Web UI 層（`/projects/*`, `/dashboard/*` など）- 当面存続（REST API は提供していません）

## 責務分離: WebApp HTML UI と FastAPI API

- **WebApp HTML UI (Flask)**: サーバー内部 UI（人間向け HTML 画面）
  - HTML レンダリングとフォーム受け付けを担当
  - データ取得は FastAPI 経由ではなく、直接データベースアクセスまたは services 層を使用
  - FastAPI API migration の対象外（責務分離のため）
  - 詳細は [WEBAPP_UI_API_MAPPING.md](./WEBAPP_UI_API_MAPPING.md) を参照してください

- **FastAPI API**: 公開 API（外部/機械向け JSON API）
  - SDK / CLI / 外部統合向けのエンドポイント（`/api/v1/*`）
  - 統一された認証、エラーハンドリング、OpenAPI スキーマを提供

## プロンプト一覧

### CR-FASTAPI-000: API Inventory
- **ファイル**: [CR-FASTAPI-000_PROMPT.md](./CR-FASTAPI-000_PROMPT.md)
- **目的**: 既存の Flask ベース API を全て棚卸しし、public / internal / 廃止候補を分類
- **出力**: `docs/api/api_inventory.md`
- **ステータス**: ✅ 完了

### CR-FASTAPI-001: FastAPI Skeleton
- **ファイル**: [CR-FASTAPI-001_PROMPT.md](./CR-FASTAPI-001_PROMPT.md)
- **目的**: FastAPI アプリケーションの最小スケルトンと `/api/v1/health` エンドポイントを作成
- **出力**: FastAPI アプリ本体、ルータ、スキーマ、テスト
- **ステータス**: ✅ 完了
- **完了レポート**: [CR-FASTAPI-001_COMPLETION_REPORT.md](./CR-FASTAPI-001_COMPLETION_REPORT.md)
- **追加改善レポート**: [CR-FASTAPI-001_ENHANCEMENT_REPORT.md](./CR-FASTAPI-001_ENHANCEMENT_REPORT.md)

### CR-FASTAPI-002: Execute & Status Endpoints
- **ファイル**: プロンプトは CR-FASTAPI-002 として実行
- **目的**: `/api/v1/execute` と `/api/v1/status/{task_id}` エンドポイントの FastAPI 版実装
- **出力**: Execute スキーマ、ルータ、認証依存、テスト
- **ステータス**: ✅ 完了
- **完了レポート**: [CR-FASTAPI-002_COMPLETION_REPORT.md](./CR-FASTAPI-002_COMPLETION_REPORT.md)

### CR-FASTAPI-003: GitHub Self-Healing Webhook API
- **ファイル**: プロンプトは CR-FASTAPI-003 として実行
- **目的**: `/api/v1/github/webhook` エンドポイントの FastAPI 版実装（GitHub Self-Healing Webhook）
- **出力**: GitHub Webhook スキーマ、ルータ、署名検証、テスト
- **ステータス**: ✅ 完了
- **完了レポート**: [CR-FASTAPI-003_COMPLETION_REPORT.md](./CR-FASTAPI-003_COMPLETION_REPORT.md)

### CR-FASTAPI-004: 認証 DI 統一
- **ファイル**: プロンプトは CR-FASTAPI-004 として実行
- **目的**: FastAPI の標準 DI（Depends）形式に統一された認証レイヤーの実装
- **出力**: 認証依存モジュール、すべての Public API への認証 DI 適用、テスト
- **ステータス**: ✅ 完了
- **完了レポート**: [CR-FASTAPI-004_COMPLETION_REPORT.md](./CR-FASTAPI-004_COMPLETION_REPORT.md)

### CR-FASTAPI-005: Pydantic モデルの分離と API 型安全化
- **ファイル**: プロンプトは CR-FASTAPI-005 として実行
- **目的**: 既存 Flask/混在コードから移行してくる API 仕様を FastAPI で完全型安全化
- **出力**: Projects/Runs/Plans スキーマ、ルータ、テスト
- **ステータス**: ✅ 完了
- **完了レポート**: [CR-FASTAPI-005_COMPLETION_REPORT.md](./CR-FASTAPI-005_COMPLETION_REPORT.md)

### CR-FASTAPI-006: Error Handling Unification（エラー標準化）
- **ファイル**: プロンプトは CR-FASTAPI-006 として実行
- **目的**: FastAPI 全 API で返すエラーを 1つの標準構造に統一
- **出力**: エラービルダー関数、すべてのルータのエラーハンドリング統一、OpenAPI スキーマにエラーレスポンス追加、テスト
- **ステータス**: ✅ 完了
- **完了レポート**: [CR-FASTAPI-006_COMPLETION_REPORT.md](./CR-FASTAPI-006_COMPLETION_REPORT.md)

### CR-FASTAPI-007: Flask REST API の棚卸し・非推奨化・削除計画の策定
- **ファイル**: プロンプトは CR-FASTAPI-007 として実行
- **目的**: Flask REST API の棚卸し、非推奨化、削除計画の策定
- **出力**: 移行状況ドキュメント、Flask REST API の非推奨化、削除計画
- **ステータス**: ✅ 完了
- **完了レポート**: [CR-FASTAPI-007_COMPLETION_REPORT.md](./CR-FASTAPI-007_COMPLETION_REPORT.md)
- **移行状況**: [FASTAPI_MIGRATION_STATUS.md](./FASTAPI_MIGRATION_STATUS.md)

### CR-FASTAPI-008: Flask 内部 REST API の削除
- **ファイル**: プロンプトは CR-FASTAPI-008 として実行
- **目的**: Flask 内部 REST API (`/api/v1/execute`, `/api/v1/status`) の物理削除
- **出力**: Flask エンドポイント削除、テスト整理、ドキュメント更新
- **ステータス**: ✅ 完了
- **完了レポート**: [CR-FASTAPI-008_COMPLETION_REPORT.md](./CR-FASTAPI-008_COMPLETION_REPORT.md)

### CR-FASTAPI-009: Project Run & Badge エンドポイントの移行
- **ファイル**: プロンプトは CR-FASTAPI-009 として実行
- **目的**: Flask ベースの Project Run と Badge エンドポイントを FastAPI に移行
  - `/api/v1/projects/<id>/run` (POST)
  - `/api/v1/projects/<id>/runs/latest` (GET)
  - `/api/v1/projects/<id>/badge/success_rate` (GET)
  - `/api/v1/projects/<id>/badge/last_run` (GET)
- **出力**: FastAPI ルータ、Pydantic スキーマ、テスト
- **ステータス**: ✅ 完了
- **完了レポート**: [CR-FASTAPI-009_COMPLETION_REPORT.md](./CR-FASTAPI-009_COMPLETION_REPORT.md)

### CR-FASTAPI-010: WebApp 側 Flask API の完全削除
- **ファイル**: プロンプトは CR-FASTAPI-010 として実行
- **目的**: WebApp 側の Flask REST API (`api_external.py`, `api_badges.py`) を完全削除
- **出力**: Flask Blueprint 削除、テスト整理、ドキュメント更新
- **ステータス**: ✅ 完了
- **完了レポート**: [CR-FASTAPI-010_COMPLETION_REPORT.md](./CR-FASTAPI-010_COMPLETION_REPORT.md)

### CR-FASTAPI-010A: Badges パス統一 & Health エラーインポート Hotfix
- **ファイル**: プロンプトは CR-FASTAPI-010A として実行
- **目的**: Badges エンドポイントのパスを `/api/v1/projects/...` に統一、Health の ErrorResponse インポート確認
- **出力**: パス統一、ドキュメント更新
- **ステータス**: ✅ 完了
- **完了レポート**: [CR-FASTAPI-010A_COMPLETION_REPORT.md](./CR-FASTAPI-010A_COMPLETION_REPORT.md)

### CR-NEXUS-011: WebApp HTML UI の API 移行整合 & クリーンアップ
- **ファイル**: プロンプトは CR-NEXUS-011 として実行
- **目的**: WebApp HTML UI の URL 正規化、docstring 整備、責務分離の明文化
- **出力**: docstring 追加、ドキュメント作成、URL 統一確認
- **ステータス**: ✅ 完了
- **完了レポート**: [CR-NEXUS-011_COMPLETION_REPORT.md](./CR-NEXUS-011_COMPLETION_REPORT.md)
- **関連ドキュメント**: [WEBAPP_UI_API_MAPPING.md](./WEBAPP_UI_API_MAPPING.md)

### CR-FASTAPI-012: SDK 自動生成導線の構築
- **ファイル**: プロンプトは CR-FASTAPI-012 として実行
- **目的**: OpenAPI 仕様書を元に Python / TypeScript 向け SDK を自動生成できる導線を追加
- **出力**: SDK 生成スクリプト、Makefile コマンド、ドキュメント更新
- **ステータス**: ✅ 完了
- **完了レポート**: [CR-FASTAPI-012_COMPLETION_REPORT.md](./CR-FASTAPI-012_COMPLETION_REPORT.md)
- **関連 Spec**: [CR-FASTAPI-012 Spec](../spec/CR-FASTAPI-012_SDK_Auto_Generation.md)

### CR-FASTAPI-012A: SDK Generator Tooling Hardening
- **ファイル**: プロンプトは CR-FASTAPI-012A として実行
- **目的**: SDK 生成ツールの固定化と安全性テストの追加
- **出力**: ツール・バージョン情報の明示、軽量テスト追加、ドキュメント更新
- **ステータス**: ✅ 完了
- **完了レポート**: [CR-FASTAPI-012A_COMPLETION_REPORT.md](./CR-FASTAPI-012A_COMPLETION_REPORT.md)
- **関連 Spec**: [CR-FASTAPI-012A Spec](../spec/CR-FASTAPI-012A_SDK_Tooling_Hardening.md)

### CR-FASTAPI-013: SDK / FastAPI E2E テスト基盤構築
- **ファイル**: プロンプトは CR-FASTAPI-013 として実行
- **目的**: FastAPI アプリと SDK の連携を実際に検証する E2E テスト基盤の構築
- **出力**: uvicorn 起動ヘルパー、E2E テスト、Makefile コマンド、ドキュメント更新
- **ステータス**: ✅ 完了
- **完了レポート**: [CR-FASTAPI-013_COMPLETION_REPORT.md](./CR-FASTAPI-013_COMPLETION_REPORT.md)
- **関連 Spec**: [CR-FASTAPI-013 Spec](../spec/CR-FASTAPI-013_SDK_E2E_Testing.md)

### CR-FASTAPI-013A: SDK E2E Tests – Real SDK Integration
- **ファイル**: プロンプトは CR-FASTAPI-013A として実行
- **目的**: 実際に生成された Python SDK を使用した E2E テストの実装
- **出力**: SDK クライアントヘルパー、実際の SDK API に合わせた E2E テスト、ドキュメント更新
- **ステータス**: ✅ 完了
- **完了レポート**: [CR-FASTAPI-013A_COMPLETION_REPORT.md](./CR-FASTAPI-013A_COMPLETION_REPORT.md)
- **関連 Spec**: [CR-FASTAPI-013A Spec](../spec/CR-FASTAPI-013A_SDK_E2E_RealSDK.md)

## SDK 自動生成

NexusCore の FastAPI API から OpenAPI 仕様書を取得し、Python / TypeScript 向け SDK を自動生成できます。

### 前提条件

SDK 生成には以下のツールが必要です：

- **推奨**: `@openapitools/openapi-generator-cli`（npm パッケージ）
  - インストール方法: `npx --yes openapi-generator-cli`（最新版を自動取得）
  - または: `npm install -g @openapitools/openapi-generator-cli`
- **代替**: Java 版 `openapi-generator`（バージョン 7.x 系推奨）
  - Java がインストールされている必要があります

**重要**: SDK コードは手書きせず、必ず `tools/generate_sdk.py` を使用して OpenAPI 仕様書から自動生成してください。OpenAPI 仕様書が SDK の単一のソース（Single Source of Truth）です。

### SDK 生成方法

#### すべての SDK を生成

```bash
make sdk
# または
python tools/generate_sdk.py --all
```

#### Python SDK のみ生成

```bash
make sdk-python
# または
python tools/generate_sdk.py --python
```

#### TypeScript SDK のみ生成

```bash
make sdk-ts
# または
python tools/generate_sdk.py --typescript
```

### 生成物の場所

- **Python SDK**: `sdk/python/`
- **TypeScript SDK**: `sdk/typescript/`

### 生成物の活用例

#### Python

```python
from nexuscore_sdk import NexusCoreClient

client = NexusCoreClient(base_url="http://localhost:8000")
response = client.health()
```

#### TypeScript

```typescript
import { NexusCoreClient } from 'nexuscore-sdk';

const client = new NexusCoreClient({ baseURL: 'http://localhost:8000' });
const response = await client.health();
```

### 注意事項

- SDK 生成時は FastAPI アプリが起動している必要があります（`http://localhost:8000/api/openapi.json` から OpenAPI 仕様書を取得）
- または `--openapi-file` オプションで OpenAPI JSON ファイルを直接指定できます
- 生成された SDK は `.gitignore` で除外されています（再生成可能なため）

## E2E テスト

生成された SDK と FastAPI アプリの連携を実際に検証する E2E テストを実行できます。

### 前提条件

- SDK が事前に生成されていること（`make sdk-python` を実行）
- FastAPI アプリが正常に起動できること
- 必要な環境変数（API Key など）が設定されていること

### E2E テストの実行

**重要**: E2E テストを実行するには、事前に SDK を生成する必要があります。

```bash
# 1. SDK を生成（事前に実行）
make sdk-python

# 2. E2E テストを実行
make test-e2e

# または直接実行
pytest tests/e2e/test_sdk_e2e.py -v
```

**注意**: SDK が生成されていない場合、E2E テストは自動的にスキップされます。
これは「テスト環境の問題」であり、SDK / API 実装のバグではありません。

### E2E テストの内容

E2E テストでは以下のケースを検証します：

1. **Health エンドポイント** (`test_health_e2e`):
   - Python SDK 経由で `/api/v1/health` を呼び出し
   - HTTP ステータス 200、status == "ok"、version が非空文字列、timestamp が ISO8601 形式を検証

2. **Projects API** (`test_projects_list_e2e`):
   - Python SDK 経由で `/api/v1/projects` の一覧取得を行う
   - 呼び出しが例外なく完了、戻り値が list / iterable、各要素に id, name など Project スキーマに準拠したフィールドが存在することを検証

3. **Execute API** (`test_execute_e2e`):
   - Python SDK 経由で `/api/v1/execute` を呼び出す
   - 正しい API Key を付けた場合の正常系（task_id, status_url など）を検証
   - API Key を付けない／不正なキーの場合の Unauthorized エラーを検証

### E2E テストの仕組み

- FastAPI アプリを uvicorn でバックグラウンド起動（`tests/e2e/helpers/server.py`）
- 生成された Python SDK を使用して API を呼び出し（`tests/e2e/helpers/sdk_client.py`）
- テスト終了時にサーバーを自動停止
- SDK が存在しない場合は適切にスキップ

詳細は `tests/e2e/test_sdk_e2e.py` を参照してください。

## 使用方法

1. 各プロンプトファイルを開く
2. コードブロック内のテキストをコピー
3. Cursor のチャットに貼り付けて実行

## FastAPI アプリケーションの起動方法

### ローカル開発環境（WSL Ubuntu）

```bash
# 仮想環境を有効化
source myenv_linux/bin/activate
# または venv を使用している場合
# source venv/bin/activate

# PYTHONPATH を設定して FastAPI アプリを起動
export PYTHONPATH=/home/yn441611/NexusCore/src:$PYTHONPATH
uvicorn nexuscore.api.fastapi_app:app --reload --host 127.0.0.1 --port 8000
```

**重要**: `PYTHONPATH` を設定しないと `ModuleNotFoundError: No module named 'nexuscore'` エラーが発生します。

### アクセス先

- **FastAPI アプリ**: http://127.0.0.1:8000
- **API ドキュメント**: http://127.0.0.1:8000/api/docs
- **OpenAPI スキーマ**: http://127.0.0.1:8000/api/openapi.json
- **Health エンドポイント**: http://127.0.0.1:8000/api/v1/health

### ポート設計

- **Flask アプリ**: ポート 5000（既存の Web UI）
- **FastAPI アプリ**: ポート 8000（新規 API）
- 両方を同時に起動可能（別ポートのため）

## 実装パターンと .cursorrules の対応

CR-FASTAPI-001 で確立された実装パターンは、`.cursorrules` のルールに完全に準拠しています：

### ディレクトリ構造
- **FastAPI ルート**: `src/nexuscore/api/routes/` 配下に作成
  - 例: `src/nexuscore/api/routes/health.py`
- **レスポンススキーマ**: `src/nexuscore/api/schemas/` 配下に Pydantic BaseModel で定義
  - 例: `src/nexuscore/api/schemas/health.py`
- **認証依存関係**: `src/nexuscore/api/dependencies/` 配下に配置
  - 例: `src/nexuscore/api/dependencies/auth.py`

### API パス規則
- **Public API**: `/api/v1/*` プレフィックスを使用
  - 例: `/api/v1/health`, `/api/v1/execute`
- **Internal API**: `/internal/*` または `/system/*` を使用（将来実装）

### レスポンスモデル
- すべてのエンドポイントで Pydantic BaseModel を使用
- `response_model` パラメータで明示的に指定
- OpenAPI スキーマに自動反映

### テスト
- FastAPI `TestClient` を使用
- `tests/api/` 配下に配置
- PYTHONPATH 設定が必要: `export PYTHONPATH=/home/yn441611/NexusCore/src:$PYTHONPATH`

## エラー標準化（CR-FASTAPI-006）

CR-FASTAPI-006 により、FastAPI 全 API で返すエラーが統一された構造に統一されました。

### エラーレスポンス形式

すべてのエラーは以下の形式で返されます：

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Project with id 123 not found"
  }
}
```

### エラーコード一覧

| HTTP Status | Code | 説明 |
|------------|------|------|
| 400 | INVALID_REQUEST | パラメータ不正 |
| 401 | UNAUTHORIZED | API Key 不正 |
| 403 | FORBIDDEN | 権限なし |
| 404 | NOT_FOUND | リソース未検出 |
| 409 | CONFLICT | 既存・重複エラー |
| 422 | VALIDATION_ERROR | バリデーション不正 |
| 500 | INTERNAL_ERROR | サーバー内部エラー |

### 使用方法

エラーハンドリングは `src/nexuscore/api/utils/errors.py` の `make_error()` 関数を使用します：

```python
from nexuscore.api.utils.errors import make_not_found_error

raise make_not_found_error("Project", str(project_id))
```

## 認証 DI 統一（CR-FASTAPI-004）

すべての Public API は FastAPI の標準 DI（Depends）形式で認証を行います。

### 認証方式

**API Key 認証**
- Header: `X-API-Key`
- 値: 環境変数 `NEXUSCORE_API_KEY` または `secrets.json` の `NEXUSCORE_API_KEY`

### 使用方法

```python
from fastapi import Depends
from nexuscore.api.dependencies.auth import get_current_user, AuthenticatedUser

@router.post("/api/v1/example")
async def example_endpoint(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    # 認証済みユーザー情報を使用
    user_id = current_user.user_id
    roles = current_user.roles
    ...
```

### API Key の設定

**環境変数から設定**:
```bash
export NEXUSCORE_API_KEY=your-api-key-here
```

**secrets.json から設定**:
```json
{
  "NEXUSCORE_API_KEY": "your-api-key-here"
}
```

### 認証が必要なエンドポイント

- `/api/v1/execute` - 必須認証
- `/api/v1/status/{task_id}` - 必須認証

### 認証不要なエンドポイント

- `/api/v1/health` - 認証不要（公開エンドポイント）

### 例外

- `/api/v1/github/webhook` - GitHub Webhook の署名認証（X-Hub-Signature-256）のみ使用。API Key 認証は不要。

### 認証エラー

- **401 Unauthorized**: API Key が無効または欠如
- **500 Internal Server Error**: サーバー設定エラー（API Key が設定されていない）

## 注意事項

- すべてのプロンプトは `#project: NexusCore` タグで始まります
- 既存の Flask アプリには影響を与えないよう注意してください
- 変更は unified diff 形式で提示されます
- Flask と FastAPI は別ポートで同時起動可能です
- すべての Public API は `Depends(get_current_user)` を通す必要があります（GitHub Webhook は例外）

