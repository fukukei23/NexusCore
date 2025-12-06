# CR-FASTAPI-013A: SDK E2E Tests – Real SDK Integration（現物 SDK 前提版）

- **CR-ID**: CR-FASTAPI-013A
- **Status**: In-Progress
- **Author**: AI Codex
- **Date**: 2024-12-05
- **Related CR**: CR-FASTAPI-012, CR-FASTAPI-012A, CR-FASTAPI-013

## 1. 概要（Overview）

CR-FASTAPI-012 / 012A で SDK 自動生成の導線とツールのハードニングは完了済み。
CR-FASTAPI-013 で「SDK を使った E2E テストの枠」は作成済みだが、実際に生成された Python SDK の API 形状に完全には追従していない。

本 CR では、実際に生成された Python SDK を前提に、`tests/e2e/test_sdk_e2e.py` を「本物の SDK をそのまま叩く E2E テスト」として仕上げる。

### 目的

- 実際に生成された Python SDK を使用した E2E テストを実装する
- SDK が存在しない／import に失敗する環境では適切にスキップする
- README / docs に「現物 SDK 前提の E2E テスト手順」を明示する

### ゴール

1. Python SDK の実 API 形状の把握
2. `tests/e2e/test_sdk_e2e.py` を実際の SDK API に合わせて更新
3. 必要に応じて `tests/e2e/helpers/sdk_client.py` を作成
4. スキップ条件の整理と pytest スキップ実装
5. ドキュメント更新（README / docs/api/README.md）
6. Spec / 完了レポート作成

### 原則

- 実際に生成された SDK の構造に基づいて実装する
- SDK が存在しない場合は適切にスキップする
- テスト環境の問題と実装のバグを区別する

## 2. 変更理由（Why）

- CR-FASTAPI-013 で作成された E2E テストは、実際の SDK API の構造に完全には対応していない
- 実際に生成された SDK を使用した E2E テストが必要
- SDK が存在しない環境でも適切に動作する必要がある

## 3. スコープ（Scope）

### In Scope

#### A. Python SDK の実 API 形状の把握

1. **調査対象**: `sdk/python/` 以下（生成済み SDK）
   - パッケージ / クラス構造の確認
   - HTTP クライアントのエントリポイントの特定
   - health, projects, execute に相当するメソッド名・引数・戻り値の特定

2. **調査方法**:
   - `sdk/python/nexuscore_sdk/api/` 配下のファイルを確認
   - `sdk/python/nexuscore_sdk/models/` 配下のモデルクラスを確認
   - 実際のメソッド名とシグネチャを確認

#### B. SDK クライアントヘルパーの作成（必要に応じて）

1. **新規作成ファイル**: `tests/e2e/helpers/sdk_client.py`（必要に応じて）

2. **実装内容**:
   - `create_sdk_client(base_url: str, api_key: str)` のようなユーティリティ関数
   - SDK クライアントの生成処理を 1 箇所にまとめる

#### C. E2E テストの「現物 SDK 対応」

1. **変更ファイル**: `tests/e2e/test_sdk_e2e.py`

2. **実装内容**:
   - モジュール先頭で Python SDK を try/except ImportError 付きで import
   - SDK が import できない場合は pytest.skip でクラス／モジュール単位スキップ
   - `test_health_e2e`: Python SDK 経由で `/api/v1/health` を呼び出す実装に書き換え
   - `test_projects_list_e2e`: Python SDK 経由で `/api/v1/projects` 一覧取得を行う
   - `test_execute_e2e`: Python SDK 経由で `/api/v1/execute` を呼び出す

3. **検証内容**:
   - `test_health_e2e`: HTTP ステータス 200、status == "ok"、version が非空文字列、timestamp が ISO8601 形式
   - `test_projects_list_e2e`: 呼び出しが例外なく完了、戻り値が list / iterable、各要素に id, name など Project スキーマに準拠したフィールドが存在
   - `test_execute_e2e`: 正しい API Key を付けた場合の正常系、API Key を付けない／不正なキーの場合の Unauthorized エラー

#### D. スキップ条件の整理

1. **スキップ条件**:
   - Python SDK が import できない（ModuleNotFoundError）
   - E2E 用 FastAPI サーバが起動できない（wait_for_server が timeout 等）

2. **実装方針**:
   - これらは「テスト環境の問題」であり、SDK / API 実装のバグではないことを docstring / コメントに明記

#### E. ドキュメント更新

1. **docs/api/README.md**:
   - Python SDK 生成 → E2E テスト実行までの手順を 1 本のフローとして記載
   - SDK 未生成時に `tests/e2e/test_sdk_e2e.py` が skipped になる仕様を明記

2. **README.md**:
   - 概要レベルで同じ情報を反映

### Out of Scope

- FastAPI 側のエンドポイント仕様（パス / スキーマ）の変更
- TypeScript SDK の E2E テスト実装
- SDK 生成スクリプト `tools/generate_sdk.py` のロジック変更（バグがない限り触らない）
- CI 設定ファイル（GitHub Actions など）の変更

## 4. 実装方針（Design / Implementation Plan）

### 4.1 SDK 構造の調査

- **調査対象**: `sdk/python/nexuscore_sdk/` 配下
- **確認項目**:
  - API クラスの構造（DefaultApi またはタグごとの API クラス）
  - メソッド名の命名規則（operationId ベースまたは自動生成）
  - 認証方法（API Key の設定方法）
  - レスポンスモデルの構造

### 4.2 E2E テストの実装

- **実装場所**: `tests/e2e/test_sdk_e2e.py`
- **実装方針**:
  - SDK の import を try/except で囲む
  - SDK が存在しない場合は適切にスキップ
  - 実際の SDK API に合わせてメソッド呼び出しを実装
  - レスポンスの検証を厳密に行う

### 4.3 SDK クライアントヘルパー（必要に応じて）

- **実装場所**: `tests/e2e/helpers/sdk_client.py`
- **実装内容**:
  - SDK クライアントの生成処理を共通化
  - 認証設定を簡潔に行えるようにする

## 5. テスト方針（Testing Strategy）

### 5.1 E2E テストの実行条件

- SDK が事前に生成されていること（`sdk/python/nexuscore_sdk/` が存在すること）
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

### 5.3 スキップ条件

- SDK が存在しない場合: `pytest.skip("Python SDK not generated; run make sdk-python")`
- サーバーが起動できない場合: `pytest.skip("FastAPI server failed to start")`

## 6. 完了条件（Definition of Done）

- [ ] `docs/spec/CR-FASTAPI-013A_SDK_E2E_RealSDK.md` を作成（本 Spec）
- [ ] Python SDK の実 API 形状を調査
- [ ] `tests/e2e/helpers/sdk_client.py` を作成（必要に応じて）
- [ ] `tests/e2e/test_sdk_e2e.py` を実際の SDK API に合わせて更新
- [ ] スキップ条件の整理と pytest スキップ実装
- [ ] `docs/api/README.md` を更新（E2E テスト手順を追加）
- [ ] `README.md` を更新（必要に応じて）
- [ ] テスト実行（`pytest tests/e2e/test_sdk_e2e.py -v`）
- [ ] 完了レポート作成（`docs/api/CR-FASTAPI-013A_COMPLETION_REPORT.md`）

## 7. 参照（References）

- [CR-FASTAPI-012 Spec](./CR-FASTAPI-012_SDK_Auto_Generation.md) - SDK 自動生成導線の Spec
- [CR-FASTAPI-012A Spec](./CR-FASTAPI-012A_SDK_Tooling_Hardening.md) - SDK 生成ツールのハードニング Spec
- [CR-FASTAPI-013 Spec](./CR-FASTAPI-013_SDK_E2E_Testing.md) - SDK E2E テスト基盤の Spec
- [CR-FASTAPI-013 Completion Report](../api/CR-FASTAPI-013_COMPLETION_REPORT.md) - SDK E2E テスト基盤の完了レポート
- [SDK Generation Script](../../tools/generate_sdk.py) - SDK 自動生成スクリプト
- [FastAPI App Source](../../src/nexuscore/api/fastapi_app.py) - FastAPI アプリケーション

