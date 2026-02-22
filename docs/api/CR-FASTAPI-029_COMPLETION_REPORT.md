# CR-FASTAPI-029: Orchestrator Dependency Injection for API - 完了レポート

## 実装日時

2025年12月22日

## 概要

### 目的

FastAPI 経由の Run / Resume において、Orchestrator の生成・注入（Dependency Injection）をリクエストスコープで行う。
API 経路でグローバル setter に依存しない安全な実行を成立させる。

### ゴール

- FastAPI dependency による Orchestrator 生成・注入
- API 経由の run_with_authority / resume_run の成立
- set_resume_orchestrator() 依存の解消（API経路のみ）
- レスポンス型の統一（成功/409/400 いずれも RunViewResponse）

### 原則

- Runner 正本は維持（API は Runner を呼ぶだけ）
- Orchestrator は Request-scoped（リクエスト間で共有しない）
- グローバル setter を使わない
- API の I/O は RunView に統一

## 実装ステップ

### Step 1: Orchestrator DI の実装

**新規作成ファイル:**
- `src/nexuscore/api/deps/orchestrator.py`
  - `get_orchestrator()`: FastAPI dependency として Orchestrator を生成

**実装内容:**
- リクエストごとに新規 Orchestrator を生成
- グローバル set_resume_orchestrator() は API 経路では使用しない

### Step 2: API Run / Resume の実装

**変更ファイル:**
- `src/nexuscore/api/routes/run_view.py`
  - `POST /api/v1/run-view/runs`: Depends(get_orchestrator) で Orchestrator 注入
  - `POST /api/v1/run-view/runs/{run_id}/resume`: Orchestrator を注入して resume を実行

**実装内容:**
- run_with_authority(orchestrator=..., ...) を呼ぶ
- resume_run には一時的な factory 差し替えを実装（暫定）

### Step 3: レスポンス型の統一

**変更ファイル:**
- `src/nexuscore/api/routes/run_view.py`
  - 成功/409/400 はすべて RunViewResponse を返す
  - HTTPException(detail=RunView) は使用しない
  - JSONResponse を使用

### Step 4: テストの更新

**変更ファイル:**
- `tests/api/test_fastapi_run_view.py`
  - Orchestrator DI を使用するようにテストを更新

## 変更ファイル一覧

### 新規作成ファイル
- `src/nexuscore/api/deps/orchestrator.py` - Orchestrator DI の実装

### 変更ファイル
- `src/nexuscore/api/routes/run_view.py` - Orchestrator DI の適用、レスポンス型の統一
- `tests/api/test_fastapi_run_view.py` - Orchestrator DI を使用するようにテストを更新

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
- ✅ POST /api/v1/run-view/runs が実行可能
- ✅ Orchestrator がリクエスト間で共有されない
- ✅ レスポンス型が RunViewResponse に統一されている

### コードレビュー結果
- ✅ `.cursorrules` のルールに準拠
- ✅ API 経路でグローバル setter を使用しない（暫定実装あり）
- ✅ レスポンス型が統一されている

## 設計上の改善点

### アーキテクチャの改善
1. **Request-scoped Orchestrator**
   - リクエストごとに新規 Orchestrator を生成
   - リクエスト間で共有されない

2. **レスポンス型の統一**
   - 成功/409/400 いずれも RunViewResponse
   - JSONResponse による一貫したレスポンス

### 将来の拡張性への配慮
- Resume 経路の完全な request-safe 化（CR-FASTAPI-030 で実装予定）
- グローバル状態の完全排除

## 既知の制約・注意事項

### 既存コードとの互換性
- ✅ Contract Layer の変更なし
- ✅ Runner の挙動変更なし
- ✅ CLI 経路への影響なし

### 制限事項やトレードオフ
- Resume 経路では暫定的にグローバル factory 差し替えを使用（CR-FASTAPI-030 で解消予定）
- Orchestrator 生成コストが高い場合、リクエスト遅延の可能性あり（正しさ優先）

## 次のステップ

### 推奨されるフォローアップアクション

1. **Resume Dependency Injection Hardening（CR-FASTAPI-030）**
   - Resume 経路の完全な request-safe 化
   - グローバル factory 差し替えの削除

2. **パフォーマンス最適化**
   - Orchestrator 生成コストの最適化
   - キャッシュの検討

## 関連ドキュメント

- [CR-FASTAPI-028 Completion Report](./CR-FASTAPI-028_COMPLETION_REPORT.md)
- [CR-FASTAPI-030 Completion Report](./CR-FASTAPI-030_COMPLETION_REPORT.md)

## まとめ

CR-FASTAPI-029 の実装により、FastAPI 経由の Run / Resume に Orchestrator Dependency Injection が導入されました。API 経路でグローバル setter に依存しない安全な実行が成立しました。すべてのテストが成功し、`.cursorrules` のルールに準拠した実装が完了しています。

