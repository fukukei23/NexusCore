# CR-FASTAPI-012: SDK 自動生成導線の構築

- **CR-ID**: CR-FASTAPI-012
- **Status**: In-Progress
- **Author**: AI Codex
- **Date**: 2024-12-04
- **Related CR**: CR-FASTAPI-001, CR-FASTAPI-010, CR-NEXUS-SPEC-STANDARDIZATION

## 1. 概要（Overview）

FastAPI 移行（CR-FASTAPI-001〜010A）により `/api/v1/*` が NexusCore の唯一の Public API となったため、OpenAPI 仕様書を元に Python / TypeScript 向け SDK を自動生成できる導線を追加する。

## 2. 変更理由（Why）

- API は FastAPI に統一されたが、SDK（クライアントライブラリ）が無いため外部連携のハードルが高い
- SaaS 提供を見据えた場合、SDK 自動生成導線は必須
- CI/CD や CR 実行時に、任意のタイミングで SDK を生成・配布できる仕組みが必要

## 3. スコープ（Scope）

### In Scope

- SDK 自動生成スクリプトの作成（`tools/generate_sdk.py`）
- Makefile / CLI 導線の追加（`make sdk`, `make sdk-python`, `make sdk-ts`）
- `docs/api/README.md` に SDK 生成手順を追加
- `.cursorrules` に SDK 破壊検証ルールを追加
- 完了レポート作成

### Out of Scope

- SDK の中身のカスタマイズ（OpenAPI generator の基本出力のままで可）
- CI/CD の自動配布機能（後続 CR で扱う）
- PyPI/npm への公開（後続 CR で扱う）

## 4. 実装方針（Design / Implementation Plan）

### 4.1 OpenAPI の取得方法

- `http://localhost:8000/api/openapi.json` から取得
- または FastAPI アプリを Python 内で直接読み込む方式でも可

### 4.2 SDK 生成ツール

- `tools/generate_sdk.py` を作成
- openapi-generator-cli（Java版 or npx）を使用
- Python SDK と TypeScript SDK を生成
- 出力先：
  - `sdk/python/`
  - `sdk/typescript/`

### 4.3 Makefile コマンド

- `make sdk` - すべての SDK を生成
- `make sdk-python` - Python SDK のみ生成
- `make sdk-ts` - TypeScript SDK のみ生成

### 4.4 検証

- 生成結果（フォルダ・ファイルの有無）を確認する簡易チェックコードを `tools/generate_sdk.py` に内蔵

## 5. テスト方針（Testing Strategy）

- pytest 追加は不要（コード生成が主体のため）
- 生成結果の確認を `tools/generate_sdk.py` に内蔵
- 生成された SDK のフォルダ・ファイルの存在確認

## 6. 完了条件（Definition of Done）

- [ ] `tools/generate_sdk.py` を作成
- [ ] `sdk/.gitkeep` を作成
- [ ] Makefile にコマンドを追加
- [ ] `docs/api/README.md` を更新
- [ ] `.cursorrules` を更新
- [ ] README.md を更新（必要なら）
- [ ] 完了レポート作成

## 7. 参照（References）

- [FastAPI Migration Status](../api/FASTAPI_MIGRATION_STATUS.md)
- [CR-FASTAPI-010 Completion Report](../api/CR-FASTAPI-010_COMPLETION_REPORT.md)
- [CR-NEXUS-SPEC-STANDARDIZATION Completion Report](./CR-NEXUS-SPEC-STANDARDIZATION_COMPLETION_REPORT.md)
- [FastAPI App Source](../../src/nexuscore/api/fastapi_app.py)

