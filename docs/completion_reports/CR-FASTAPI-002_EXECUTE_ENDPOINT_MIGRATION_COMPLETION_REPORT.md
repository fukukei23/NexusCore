# CR-FASTAPI-002: /api/v1/execute エンドポイントの FastAPI 移植 - 完了レポート

## 実装日時
2025-12-02

## 概要

NexusCore のメイン実行エントリ `/api/v1/execute` を Flask から FastAPI に移植し、Request/Response を Pydantic モデルで明確化しました。

### 目的
- `/api/v1/execute` エンドポイントを FastAPI + Pydantic ベースに移行する
- 既存の Flask 実装と共存させ、段階的に移行できる構造にする
- Request/Response を型安全な Pydantic モデルで定義する
- 既存のビジネスロジックを維持しつつ、API 層を FastAPI 化する

### 達成内容
- Execute エンドポイントの FastAPI 実装
- Pydantic BaseModel によるリクエスト/レスポンスモデル定義
- 既存の Orchestrator 実行ロジックの再利用
- 既存 Flask 実装への LEGACY コメント追加

### 原則
- 既存の Flask `server.py` の `/api/v1/execute` は削除せず、LEGACY コメントを追加
- 既存のビジネスロジック（`run_orchestrator_task`）をそのまま再利用
- 認証は CR-FASTAPI-003 で追加予定（現時点ではコメントで明記）
- Pydantic による型安全性とバリデーションを活用

## 実装ステップ

### Step 1: Request/Response スキーマの定義
**ファイル**: `src/nexuscore/api/schemas/execute.py`（新規作成）

- `ExecuteRequest` モデルを定義
  - `requirement`: 実行要件（必須）
  - `project_path`: プロジェクトパス（必須）
  - `constitution_text`: 憲法テキスト（オプション、デフォルト: "Default constitution."）
- `ExecuteResponse` モデルを定義
  - `message`: タスク受け入れメッセージ
  - `task_id`: タスクID（UUID）
  - `status_url`: ステータス確認用URL

**主要コード**:
```python
class ExecuteRequest(BaseModel):
    requirement: str = Field(..., description="実行要件")
    project_path: str = Field(..., description="プロジェクトパス")
    constitution_text: str | None = Field(
        default="Default constitution.",
        description="憲法テキスト（オプション）"
    )

class ExecuteResponse(BaseModel):
    message: str = Field(..., description="タスク受け入れメッセージ")
    task_id: str = Field(..., description="タスクID（UUID）")
    status_url: str = Field(..., description="ステータス確認用URL")
```

### Step 2: Execute エンドポイントの実装
**ファイル**: `src/nexuscore/api/routes/execute.py`（新規作成）

- APIRouter を使用して `/execute` エンドポイントを定義
- 既存の Flask 実装と同じ `run_orchestrator_task` 関数を再利用
- バックグラウンドスレッドで Orchestrator を実行
- 認証は CR-FASTAPI-003 で追加予定（コメントで明記）

**主要コード**:
```python
@router.post(
    "/execute",
    response_model=ExecuteResponse,
    summary="Run self-healing job",
    status_code=status.HTTP_202_ACCEPTED,
)
async def execute_endpoint(
    payload: ExecuteRequest,
    # current_user: AuthenticatedUser = Depends(get_current_user),  # CR-FASTAPI-003 で有効化
) -> ExecuteResponse:
    task_id = str(uuid.uuid4())
    project_path = os.path.abspath(payload.project_path)
    constitution = {"description": payload.constitution_text or "Default constitution."}

    thread = threading.Thread(
        target=run_orchestrator_task,
        args=(task_id, payload.requirement, project_path, constitution)
    )
    thread.daemon = True
    thread.start()

    return ExecuteResponse(
        message="Task accepted and is running in the background.",
        task_id=task_id,
        status_url=f"/api/v1/status/{task_id}"
    )
```

### Step 3: FastAPI アプリケーションへの統合
**ファイル**: `src/nexuscore/api/fastapi_app.py`（変更）

- `execute` router をインポート
- `/api/v1` prefix で execute router をマウント

**変更内容**:
```python
from .routes import health, execute

def create_app() -> FastAPI:
    app = FastAPI(...)
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(execute.router, prefix="/api/v1")  # 追加
    return app
```

### Step 4: 既存 Flask 実装への LEGACY コメント追加
**ファイル**: `src/nexuscore/api/server.py`（変更）

- 既存の `/api/v1/execute` エンドポイントに `# LEGACY` コメントを追加
- 将来の削除予定であることを明示

**変更内容**:
```python
# LEGACY: will be removed after FastAPI migration is completed
@app.route('/api/v1/execute', methods=['POST'])
@require_auth
def execute_task():
    ...
```

## 変更ファイル一覧

### 新規作成ファイル（2ファイル）
1. `src/nexuscore/api/routes/execute.py` - Execute エンドポイント実装
2. `src/nexuscore/api/schemas/execute.py` - Execute リクエスト/レスポンスモデル

### 変更ファイル（2ファイル）
1. `src/nexuscore/api/fastapi_app.py` - execute router の追加
2. `src/nexuscore/api/server.py` - LEGACY コメント追加

## 動作確認結果

### 静的解析結果
- リンターエラー: なし
- 型チェック: 未実施（このタスクではテストファイル未作成）

### コードレビュー結果
- `.cursorrules` の FastAPI 実装ルールに準拠
- Pydantic BaseModel を使用した型安全な実装
- APIRouter を使用した適切な構造
- 既存のビジネスロジックを維持

### テスト結果
**このタスクではテストファイルは作成していません。**

理由:
- CR-FASTAPI-002 は「エンドポイント移植」のみを目的とする
- 後続の CR-FASTAPI-005 で TestClient ベースのテストを追加予定

## 設計上の改善点

### アーキテクチャの改善
1. **型安全性の向上**
   - Pydantic BaseModel によるリクエスト/レスポンスの型定義
   - FastAPI の自動バリデーション機能を活用
   - 必須フィールドとオプションフィールドの明確化

2. **コードの明確化**
   - Request/Response モデルが独立したファイルに定義され、再利用可能
   - エンドポイントの責務が明確（ビジネスロジックは既存関数を呼ぶだけ）

3. **拡張性の確保**
   - 認証を後から追加しやすい構造（コメントで明記）
   - 既存の Flask 実装と共存し、段階的に移行可能

### 将来の拡張性への配慮
- 認証実装（CR-FASTAPI-003）で `Depends(get_current_user)` を追加可能
- エラーハンドリングの統一（CR-FASTAPI-004 で ErrorResponse を使用予定）
- テスト追加（CR-FASTAPI-005 で TestClient ベースのテストを追加予定）

## 既知の制約・注意事項

### 既存コードとの互換性
- 既存の Flask `server.py` の `/api/v1/execute` は変更していないため、既存の API 呼び出しに影響なし
- FastAPI と Flask は別々のポートで起動する想定（共存状態）
- `tasks` 辞書は FastAPI と Flask で別々のインスタンス（共有されない）

### 制限事項やトレードオフ
1. **認証未実装**
   - 現時点では認証チェックなしで実行可能
   - CR-FASTAPI-003 で API Key 認証を追加予定

2. **テスト未実装**
   - このタスクではテストファイルを作成していない
   - CR-FASTAPI-005 で TestClient ベースのテストを追加予定

3. **ビジネスロジックの重複**
   - `run_orchestrator_task` 関数が FastAPI と Flask の両方に存在
   - 将来的にはサービスレイヤーに切り出すことを推奨

4. **タスク管理の分離**
   - FastAPI と Flask で `tasks` 辞書が別々のインスタンス
   - 完全移行後は統一されたタスク管理が必要

### 移行時の注意点
- FastAPI アプリケーションを起動するには、別途エントリポイント（例: `uvicorn src.nexuscore.api.fastapi_app:app`）が必要
- 既存の Flask アプリケーションとは別プロセスで起動する想定
- 完全移行後は Flask の `/api/v1/execute` を削除する必要がある

## 次のステップ

### 推奨されるフォローアップアクション

1. **CR-FASTAPI-003: 認証実装**
   - API Key 認証の実装
   - `get_current_user()` Dependency の実装
   - `execute` エンドポイントへの認証追加

2. **CR-FASTAPI-004: public API の移行**
   - `/api/v1/status` などの他の public API を FastAPI に移行
   - ErrorResponse モデルの統一

3. **CR-FASTAPI-005: テスト追加**
   - TestClient を使用した `/api/v1/execute` のテスト
   - 正常系/異常系のテストケース追加

4. **ビジネスロジックのリファクタリング**
   - `run_orchestrator_task` をサービスレイヤーに切り出し
   - FastAPI と Flask の両方から呼び出せる共通関数化

5. **タスク管理の統一**
   - FastAPI と Flask で共有できるタスク管理システムの導入
   - データベースや Redis を使用した永続化

## 関連ファイル

- `.cursorrules` - FastAPI 実装ルール定義
- `src/nexuscore/api/server.py` - 既存の Flask 実装（LEGACY コメント追加済み）
- `src/nexuscore/api/fastapi_app.py` - FastAPI アプリケーションエントリポイント
- `docs/completion_reports/CR-FASTAPI-001_FASTAPI_SKELETON_COMPLETION_REPORT.md` - 前回の完了レポート

## 備考

このタスクは「FastAPI 移行の第二歩」として、メインの実行エンドポイントを FastAPI に移植しました。
既存の Flask 実装を壊すことなく、新しい FastAPI ベースの実装を並行して構築できる状態になっています。

認証とテストは後続のタスクで実装予定です。

