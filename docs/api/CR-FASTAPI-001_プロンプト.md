# CR-FASTAPI-001: FastAPI Skeleton Introduction

> これは Cursor のチャットにそのまま貼る「タスク指示」です。

```text
#project: NexusCore

CR-FASTAPI-001: FastAPI skeleton introduction

目的:
今後の移行先となる FastAPI アプリケーションの最小スケルトンを作成し、
- /api/v1/health エンドポイント
- ルータ分割の土台
- テスト基盤
を整える。

前提:
- `.cursorrules` に定義された FastAPI / Pydantic / /api/v1 のルールに従うこと。
- 既存の Flask アプリには手を入れない（このタスクでは影響を与えない）。

やりたいこと:

1. FastAPI アプリ本体の作成
   - ファイル: `src/nexuscore/api/fastapi_app.py`
   - 内容:
     - `FastAPI` インスタンスの生成
       - title: "NexusCore API"
       - version: "1.0.0"
       - docs_url: "/api/docs"
       - openapi_url: "/api/openapi.json"
     - 将来ルータを追加できるように、ダミーの include_router 呼び出しのプレースホルダコメントを入れる。
     - health ルータ（後述）を組み込む。

2. Health ルータの作成
   - ファイル: `src/nexuscore/api/routes/health.py`
   - 内容:
     - `APIRouter` を使用。
     - GET `/api/v1/health` エンドポイントを定義。
     - レスポンスは Pydantic BaseModel を使用 (例: `HealthStatus` モデル)。
       - fields:
         - status: Literal["ok"]
         - version: str (アプリバージョン)
         - timestamp: datetime
     - 単純な実装でよいが、「Pydantic + 明示的レスポンスモデル」のパターンを示すこと。

3. Schemas モジュールの用意
   - ファイル: `src/nexuscore/api/schemas/health.py`
   - 内容:
     - 上記 `HealthStatus` Pydantic モデルを定義。
   - 将来の拡張に備えて、schemas 配下モジュールとして切り出しておく。

4. エントリポイント（あれば）
   - 既に `run_orchestrator.py` 等が存在する場合、それとは独立して
     - Uvicorn で立ち上げ可能なスクリプトの雛形をコメントでサジェストしておく。
     - 例: `# uvicorn nexuscore.api.fastapi_app:app --reload` というコメントを fastapi_app.py の末尾に。

5. テストの追加
   - ファイル: `tests/api/test_fastapi_health.py`
   - 内容:
     - FastAPI `TestClient` を使って `/api/v1/health` に対する GET を実行。
     - ステータスコード 200 を検証。
     - レスポンス JSON が `{"status": "ok", ...}` を含むことを検証。
     - OpenAPI 上にも `/api/v1/health` が定義されていることを最低限確認。
       - 例: `/openapi.json` を叩いて paths にキーが存在するかチェック。

6. 変更の前提
   - 既存の Flask アプリケーション設定には触れないこと。
   - 新規ファイル追加と最小限の import のみ。
   - 動作確認は pytest ベースのテストで行う前提とし、`if __name__ == "__main__":` ブロックは不要。

出力フォーマット:
1. 追加・修正されるファイルごとの unified diff:
   - src/nexuscore/api/fastapi_app.py
   - src/nexuscore/api/routes/health.py
   - src/nexuscore/api/schemas/health.py
   - tests/api/test_fastapi_health.py
2. 最後に、ローカル実行のためのコマンド例だけテキストで示すこと:
   - 例: `uvicorn nexuscore.api.fastapi_app:app --reload`

このタスクでは「FastAPI の土台」と「/api/v1/health」のみを扱い、
既存の Flask ルートの移行は一切行わない。
```

