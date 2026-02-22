# CR-FASTAPI-028: RunView API Projection - 完了レポート

## 実装日時

2025年12月22日

## 概要

### 目的

RunState ベースの RunView 投影 API を FastAPI で実装する。
外部 API は RunView のみを返し、RunState の生 JSON を公開しない。

### ゴール

- RunView API エンドポイントの実装
- RunState の生 JSON 露出を禁止
- 認証必須の実装
- HTTP ステータスコード（409 / 400 等）の正しい返却
- CONFLICT / FAILED / ABORTED 時に Explainability を返す

### 原則

- 外部 API は RunView のみを返す
- RunState の raw JSON を返さない
- 認証は `Depends(get_current_user)` を使用
- エラーハンドリングは統一された形式を使用

## 実装ステップ

### Step 1: RunView スキーマの作成

**新規作成ファイル:**
- `src/nexuscore/api/schemas/run_view.py`
  - `ExplainabilityModel`: Explainability 投影モデル
  - `RunViewResponse`: RunView 投影レスポンスモデル
  - `RunCreateRequest`: Run 作成リクエストモデル

### Step 2: RunView API ルータの実装

**新規作成ファイル:**
- `src/nexuscore/api/routes/run_view.py`
  - `GET /api/v1/run-view/runs/{run_id}`: RunView 取得
  - `POST /api/v1/run-view/runs/{run_id}/resume`: Run 再開
  - `POST /api/v1/run-view/runs`: Run 作成

**実装内容:**
- RunState から RunView への投影ロジック
- HTTP ステータスコードのマッピング（CONFLICT → 409, FAILED/ABORTED → 400）
- Explainability の必須化（CONFLICT, FAILED, ABORTED 時）

### Step 3: FastAPI アプリへのルータ登録

**変更ファイル:**
- `src/nexuscore/api/fastapi_app.py`
  - RunView ルータを `/api/v1` プレフィックスでマウント

### Step 4: テストの作成

**新規作成ファイル:**
- `tests/api/test_fastapi_run_view.py`
  - RunView API の正常系・異常系テスト

## 変更ファイル一覧

### 新規作成ファイル
- `src/nexuscore/api/schemas/run_view.py` - RunView API 用の Pydantic スキーマ
- `src/nexuscore/api/routes/run_view.py` - RunView ルータの実装
- `tests/api/test_fastapi_run_view.py` - RunView API エンドポイントのテスト

### 変更ファイル
- `src/nexuscore/api/fastapi_app.py` - RunView ルータの登録

## 動作確認結果

### 静的解析結果
- リンターエラー: なし
- 型チェック: 問題なし

### テスト結果

**実行コマンド:**
```bash
bash dev_tools/run_tests.sh tests/api/test_fastapi_run_view.py
```

**結果:**
- RunView API テスト: 8個のテストケース
- すべてのテストが正常に通過

**確認項目:**
- ✅ `/api/v1/run-view/runs/{run_id}` GET が 200 を返す
- ✅ `/api/v1/run-view/runs/{run_id}/resume` POST が 409 (CONFLICT) を返す
- ✅ `/api/v1/run-view/runs/{run_id}/resume` POST が 400 (FAILED/ABORTED) を返す
- ✅ RunState の raw JSON を返さない
- ✅ Explainability が CONFLICT / FAILED / ABORTED 時に含まれる

### コードレビュー結果
- ✅ `.cursorrules` のルールに準拠
- ✅ RunState の raw JSON を公開しない
- ✅ 認証必須の実装
- ✅ 統一されたエラーハンドリング

## 設計上の改善点

### アーキテクチャの改善
1. **RunView 投影の分離**
   - RunState と RunView の責務分離
   - 外部 API と内部実装の分離

2. **Explainability の必須化**
   - CONFLICT / FAILED / ABORTED 時に Explainability を返す
   - ユーザーに次のアクションを提示

### 将来の拡張性への配慮
- RunView スキーマの拡張が容易
- Explainability モデルの拡張が可能

## 既知の制約・注意事項

### 既存コードとの互換性
- ✅ Contract Layer の変更なし
- ✅ Runner の挙動変更なし
- ✅ CLI 経路への影響なし

### 制限事項やトレードオフ
- RunView は RunState の投影であり、完全な情報を含まない
- RunState の raw JSON へのアクセスは外部 API 経由では不可能

## 次のステップ

### 推奨されるフォローアップアクション

1. **Orchestrator DI の導入（CR-FASTAPI-029）**
   - API 経路で request-scoped Orchestrator DI を導入
   - グローバル状態への依存を排除

2. **RunView スキーマの拡張**
   - 必要に応じて RunView スキーマを拡張

## 関連ドキュメント

- [CR-NEXUS-027 Completion Report](./CR-NEXUS-027_COMPLETION_REPORT.md)
- [CR-FASTAPI-029 Completion Report](./CR-FASTAPI-029_COMPLETION_REPORT.md)

## まとめ

CR-FASTAPI-028 の実装により、RunState ベースの RunView 投影 API が完成しました。外部 API は RunView のみを返し、RunState の生 JSON を公開しない設計を実現しました。すべてのテストが成功し、`.cursorrules` のルールに準拠した実装が完了しています。

