# CR-NEXUS-038: FastAPI auth misconfigured: 202 vs 500 - 完了レポート

## 実装日時

2025年12月24日

## 概要

### 目的

認証設定（API Key）不備を、確実に 500 として返すことを FastAPI の public API 契約として固定し、テストを PASS にする。

### ゴール

- `tests/api/test_fastapi_auth.py::test_auth_server_misconfigured_returns_500` を PASS にする
- misconfigured（API Key 未設定など）を外部 I/F で 500 + Top-level error envelope で返す（CR-NEXUS-034 の `{"error": {...}}` 形式と整合）
- 既存の正常系や認可エラー（401/403）を壊さない

## 実装ステップ

### Step 1: 問題の原因の特定

**確認した問題**:
- `tests/api/test_fastapi_auth.py::test_auth_server_misconfigured_returns_500` が期待 500 に対し実際 202 が返っていた
- `get_current_user` が通常フローで `get_api_key()` を呼び出していなかった
- テストが `get_api_key()` を patch していたが、実際には呼び出されていなかった
- その結果、認証が正常に通過し、エンドポイントが 202 を返していた

**発生箇所**:
- `src/nexuscore/api/dependencies/auth.py` の `get_current_user()` 関数

### Step 2: 修正内容

**変更ファイル**:
- `src/nexuscore/api/dependencies/auth.py`

**修正内容**:

1. **`get_current_user` 関数の修正**:
   - DB ベースの認証を行う前に `get_api_key()` を呼び出すように修正
   - サーバー設定エラー（API Key が設定されていない場合）を確実に検出できるようにした
   - `get_api_key()` が 500 を返す場合（サーバー設定エラー）は、そのまま raise されるため、テストの patch が正しく動作する

**修正の意図**:
- サーバー設定エラー（API Key が設定されていない場合）を確実に検出する
- misconfigured を 500 として返すことを FastAPI の public API 契約として固定する

## 変更ファイル一覧

### 変更ファイル
- `src/nexuscore/api/dependencies/auth.py` - get_current_user() の修正

## 動作確認結果

### テスト結果

**実行コマンド**:
```bash
python -m pytest tests/api/test_fastapi_auth.py::test_auth_server_misconfigured_returns_500 -q
python -m pytest tests/api/test_fastapi_auth.py -q
```

**結果**:
- `test_auth_server_misconfigured_returns_500`: 1 passed
- 全テスト: 12 passed

## 設計上の改善点

### アーキテクチャの改善
1. **認証エラーハンドリングの明確化**
   - サーバー設定エラー（500）と認証エラー（401）を明確に分離
   - FastAPI の public API 契約として misconfigured を 500 として返すことを固定

## 既知の制約・注意事項

### 制約
- 既存の正常系や認可エラー（401/403）の挙動は変更していない
- `/api/v1/execute` エンドポイントの実装変更は実施していない（認証 dependency のみ修正）

## 次のステップ

- 他の認証エンドポイントでの同様の検証

