# CR-NEXUS-040: FastAPI Projects 契約化 - 完了レポート

## 実装日時

2025年12月24日

## 概要

### 目的

`/api/v1/projects` 配下のエンドポイントの Response Model を Pydantic で明示し、OpenAPI に反映する。
既存の「トップレベル {"error": ...}」方針（CR-NEXUS-034 Option A）に沿って、projects 系のエラー応答が `{"detail": ...}` にならないことを保証する。
smoke テストが前提としているレスポンス shape を契約（Contract）としてドキュメント化し、契約テストで固定する。

### ゴール

- OpenAPI において projects 系エンドポイントの 200 レスポンスが Pydantic schema により定義されている
- tests/api/test_external_api_smoke.py が引き続き PASS
- projects 系で 401/403/404/500 のレスポンスが必ずトップレベル `{"error": {...}}` で返り、`{"detail": ...}` が外部に露出しない
- 契約ドキュメントに、projects 系の成功応答／エラー応答の例が明記されている
- 契約テスト（新規）で、projects 系のレスポンス shape が固定されている（将来壊れたらテストが落ちる）

### 原則

- Pydantic スキーマを単一ソースにして routes がそれを返す
- Run のように DB/ORM を直返ししない（dict化・Schema化）
- エラーは CR-NEXUS-034/038 の方式に合わせ、例外ハンドラ + make_error 系の包絡を尊重する
- 既存のスキーマ定義とルーティングは変更しない（確認のみ）

## 実装ステップ

### Step 1: 既存スキーマの確認

**確認内容:**
- `src/nexuscore/api/schemas/project.py`: `ProjectListResponse`, `ProjectSummary`, `ProjectResponse` が定義済み
- `src/nexuscore/api/schemas/project_run.py`: `LatestRunResponse`, `LatestRunDetail` が定義済み
- `src/nexuscore/api/routes/projects.py`: 既に `response_model` が設定済み

**結果:**
- 既存のスキーマ定義は要件を満たしているため、変更なし

### Step 2: 契約テストの追加

**新規作成ファイル:**
- `tests/api/test_projects_contract.py`

**テスト内容:**
- `GET /api/v1/projects` の成功レスポンス shape 検証（トップレベルに `projects` キー）
- `GET /api/v1/projects/{project_id}/runs/latest` の成功レスポンス shape 検証（トップレベルに `run` キー、null 許容）
- エラーレスポンス envelope 検証（401/404 でトップレベル `error` キー、`detail` がないこと）
- OpenAPI schema に response_model が含まれることを検証

### Step 3: 契約ドキュメントの追加

**新規作成ファイル:**
- `docs/api/プロジェクトAPI契約.md`

**記載内容:**
- GET /api/v1/projects の成功レスポンス例（JSON例）
- GET /api/v1/projects/{project_id}/runs/latest の成功レスポンス例（runあり/なし）
- エラー（401/403/404/500）の共通 envelope 仕様：トップレベル error のキー一覧
- 互換性ルール（追加キーはOK、既存キー削除や型変更は破壊的変更）

## 変更ファイル一覧

### 新規作成ファイル
- `tests/api/test_projects_contract.py` - Projects API の契約テスト
- `docs/api/プロジェクトAPI契約.md` - Projects API の契約仕様ドキュメント

### 変更ファイル
- なし（既存のスキーマ定義とルーティングは要件を満たしていたため変更なし）

## 動作確認結果

### 静的解析結果
- リンターエラー: なし
- 型チェック: 問題なし

### テスト結果

**実行コマンド:**
```bash
python -m pytest tests/api/test_external_api_smoke.py tests/api/test_projects_contract.py -q
```

**結果:**
- 13 passed（test_external_api_smoke: 7 passed, test_projects_contract: 6 passed）
- 23 warnings（型チェッカーの警告のみ、実行時には問題なし）

### OpenAPI Schema 確認

**確認内容:**
- GET /api/v1/projects の 200 レスポンスが `ProjectListResponse` スキーマを参照
- GET /api/v1/projects/{project_id}/runs/latest の 200 レスポンスが `LatestRunResponse` スキーマを参照
- エラーレスポンス（401/404/500）が `ErrorResponse` スキーマを参照

## 設計上の改善点

### アーキテクチャの改善

- **契約の明文化**: レスポンス shape を契約テストで固定することで、将来の破壊的変更を早期に検知できるようになった
- **OpenAPI 整合性**: response_model が OpenAPI schema に正しく反映されることを確認

### 将来の拡張性への配慮

- **互換性ルール**: 追加キーの許容と破壊的変更の禁止を明記することで、API の進化方向が明確になった
- **契約テスト**: レスポンス shape が変更された場合、テストが失敗することで開発者が契約違反に気づける

### コード品質の向上

- **テストカバレッジ**: projects 系エンドポイントの契約がテストで固定された
- **ドキュメント**: API 利用者が期待できるレスポンス形式が明確に文書化された

## 既知の制約・注意事項

### 既存コードとの互換性

- 既存のスキーマ定義（`ProjectListResponse`, `LatestRunResponse` 等）は変更していないため、後方互換性は維持されている
- `test_external_api_smoke.py` は引き続き PASS しており、既存の動作に影響がないことを確認

### 制限事項やトレードオフ

- 契約テストはレスポンス shape のみを検証しているため、ビジネスロジックの正しさは別途検証が必要
- エラーレスポンス envelope は CR-NEXUS-034 の global exception handler に依存している

## Out of Scope（本CRでは実施しなかったこと）

- **スキーマ定義の変更**: 既存のスキーマが要件を満たしていたため、変更なし
- **ルーティングの変更**: `/api/v1/projects` パスは変更なし
- **ビジネスロジックの改修**: 取得条件、権限仕様の変更は対象外

## 次のステップ

推奨されるフォローアップアクション：

- 他の API エンドポイント（run-records, plans 等）についても同様の契約化を検討
- 契約ドキュメントを OpenAPI 仕様と同期させる仕組みの検討

