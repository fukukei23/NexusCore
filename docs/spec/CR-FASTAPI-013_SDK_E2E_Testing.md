# CR-FASTAPI-013: SDK / FastAPI E2E テスト基盤構築

- **CR-ID**: CR-FASTAPI-013
- **Status**: In-Progress
- **Author**: AI Codex
- **Date**: 2024-12-05
- **Related CR**: CR-FASTAPI-012, CR-FASTAPI-012A

## 1. 概要（Overview）

CR-FASTAPI-012 と CR-FASTAPI-012A で構築された SDK 自動生成導線は完成しているが、FastAPI 実サーバーと SDK の連携を「実際に叩いて確認する E2E テスト」が存在しない。

本 CR では、FastAPI アプリをローカルで立ち上げ、生成された SDK を用いて `/api/v1/*` を叩く「E2E テスト基盤」を作成する。

### 目的

- FastAPI アプリと SDK の連携を実際に検証する E2E テスト基盤を構築する
- 生成された SDK が正しく動作することを確認する
- CI/CD で E2E テストを実行できるようにする

### ゴール

1. uvicorn をサブプロセスでバックグラウンド起動するヘルパー作成
2. SDK を import し、API 呼び出し E2E を行う pytest 作成
3. 最小 3 ケースを実装：
   - health が 200 を返す
   - projects API の一覧取得が動作する
   - execute API がトークン必須で動作エラーなく返る
4. teardown で uvicorn を stop
5. Makefile に `make test-e2e` を追加
6. ドキュメント更新

### 原則

- 既存の FastAPI テスト（TestClient 使用）は変更しない
- E2E テストは実際の HTTP サーバーを起動して実行する
- SDK は事前に生成されていることを前提とする（生成自体は E2E テストの範囲外）

## 2. コンテキストと前提

### 2.1 既存実装の確認

CR-FASTAPI-012 と CR-FASTAPI-012A で以下が実装済み：

- `tools/generate_sdk.py` - SDK 自動生成スクリプト
- `tests/tools/test_generate_sdk_safe.py` - SDK 生成スクリプトの安全性テスト
- Makefile コマンド（`make sdk`, `make sdk-python`, `make sdk-ts`）

### 2.2 既存の FastAPI テスト

- `tests/api/test_fastapi_*.py` - FastAPI TestClient を使用したユニットテスト
- TestClient は実際の HTTP サーバーを起動しないため、E2E テストとは別物

### 2.3 現状の問題点

- 生成された SDK が実際に動作することを確認するテストが存在しない
- FastAPI アプリと SDK の連携を検証する E2E テストが存在しない
- CI/CD で E2E テストを実行する仕組みが存在しない

## 3. スコープ（Scope）

### In Scope

#### A. uvicorn 起動ヘルパーの作成

1. **新規作成ファイル**: `tests/e2e/helpers/server.py`
   - FastAPI アプリを uvicorn でバックグラウンド起動する関数
   - サーバーの停止処理
   - サーバーの起動確認（ヘルスチェック）

2. **実装内容**:
   - `start_fastapi_server()`: uvicorn をサブプロセスで起動
   - `stop_fastapi_server()`: サーバーを停止
   - `wait_for_server()`: サーバーが起動するまで待機（ヘルスチェック）

#### B. E2E テストの作成

1. **新規作成ファイル**: `tests/e2e/test_sdk_e2e.py`

2. **実装内容**:
   - pytest fixture でサーバーを起動・停止
   - SDK を import して API 呼び出し
   - 最小 3 ケースを実装：
     - `test_health_e2e()`: `/api/v1/health` が 200 を返す
     - `test_projects_list_e2e()`: `/api/v1/projects` の一覧取得が動作する
     - `test_execute_e2e()`: `/api/v1/execute` がトークン必須で動作エラーなく返る

3. **実装方針**:
   - SDK は `sdk/python/` から import（事前に生成されていることを前提）
   - 認証が必要なエンドポイントは API Key を設定
   - サーバーの起動・停止は pytest fixture で管理

#### C. Makefile コマンドの追加

1. **変更ファイル**: `Makefile`
   - `make test-e2e`: E2E テストを実行

2. **実装内容**:
   - SDK が生成されていることを確認
   - E2E テストを実行

#### D. ドキュメント更新

1. **docs/api/README.md**
   - E2E テスト手順を追加
   - SDK 生成 → E2E テスト実行の流れを説明

2. **README.md**
   - E2E テストの説明を追加（必要に応じて）

#### E. .gitignore の更新

1. **変更ファイル**: `.gitignore`
   - E2E テスト用の一時ファイルがあれば追加

### Out of Scope

- SDK の生成ロジックそのものの変更
- CLI の移行（これは CR-NEXUS-012）
- 複雑なプロジェクト生成（最小ケースのみ実施）
- CI/CD の自動化（後続 CR で扱う）

## 4. 実装方針（Design / Implementation Plan）

### 4.1 サーバー起動ヘルパー

- **実装場所**: `tests/e2e/helpers/server.py`
- **機能**:
  - `start_fastapi_server(host: str, port: int) -> subprocess.Popen`: uvicorn をバックグラウンド起動
  - `stop_fastapi_server(process: subprocess.Popen) -> None`: サーバーを停止
  - `wait_for_server(url: str, timeout: int = 30) -> bool`: サーバーが起動するまで待機

### 4.2 E2E テスト

- **実装場所**: `tests/e2e/test_sdk_e2e.py`
- **テストケース**:
  1. `test_health_e2e()`: `/api/v1/health` が 200 を返す
  2. `test_projects_list_e2e()`: `/api/v1/projects` の一覧取得が動作する（認証必要）
  3. `test_execute_e2e()`: `/api/v1/execute` がトークン必須で動作エラーなく返る

- **pytest fixture**:
  - `fastapi_server`: サーバーを起動・停止する fixture
  - `sdk_client`: SDK クライアントの fixture

### 4.3 Makefile コマンド

- **コマンド**: `make test-e2e`
- **実装内容**:
  - SDK が生成されていることを確認
  - E2E テストを実行

## 5. テスト方針（Testing Strategy）

### 5.1 E2E テストの実行条件

- SDK が事前に生成されていること（`sdk/python/` が存在すること）
- FastAPI アプリが正常に起動できること
- 必要な環境変数（API Key など）が設定されていること

### 5.2 テスト実行コマンド

```bash
# SDK を生成（事前に実行）
make sdk-python

# E2E テストを実行
make test-e2e

# または直接実行
pytest tests/e2e/test_sdk_e2e.py -v
```

### 5.3 テストの独立性

- 各テストは独立して実行可能であること
- サーバーの起動・停止は fixture で管理し、テスト間で干渉しないこと

## 6. 完了条件（Definition of Done）

- [ ] `docs/spec/CR-FASTAPI-013_SDK_E2E_Testing.md` を作成（本 Spec）
- [ ] `tests/e2e/helpers/server.py` を作成
- [ ] `tests/e2e/test_sdk_e2e.py` を作成（最小 3 ケース）
- [ ] Makefile に `make test-e2e` を追加
- [ ] `docs/api/README.md` を更新（E2E テスト手順を追加）
- [ ] `.gitignore` を更新（必要に応じて）
- [ ] テスト実行（`make test-e2e`）
- [ ] 完了レポート作成（`docs/api/CR-FASTAPI-013_完了報告.md`）

## 7. 参照（References）

- [CR-FASTAPI-012 Spec](./CR-FASTAPI-012_SDK_Auto_Generation.md) - SDK 自動生成導線の Spec
- [CR-FASTAPI-012A Spec](./CR-FASTAPI-012A_SDK_Tooling_Hardening.md) - SDK 生成ツールのハードニング Spec
- [CR-FASTAPI-012 Completion Report](../api/CR-FASTAPI-012_完了報告.md) - SDK 自動生成導線の完了レポート
- [CR-FASTAPI-012A Completion Report](../api/CR-FASTAPI-012A_完了報告.md) - SDK 生成ツールのハードニング完了レポート
- [SDK Generation Script](../../tools/generate_sdk.py) - SDK 自動生成スクリプト
- [FastAPI App Source](../../src/nexuscore/api/fastapi_app.py) - FastAPI アプリケーション

