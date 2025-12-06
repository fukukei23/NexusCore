# CR-FASTAPI-012A: SDK Generator Tooling Hardening（ツール固定＋安全テスト追加）

- **CR-ID**: CR-FASTAPI-012A
- **Status**: In-Progress
- **Author**: AI Codex
- **Date**: 2024-12-04
- **Related CR**: CR-FASTAPI-012

## 1. 概要（Overview）

CR-FASTAPI-012 で構築された SDK 自動生成導線（`tools/generate_sdk.py`）を、長期運用時に壊れにくくするための「ハードニング」を実施する。

### 目的

- SDK 生成に使うツールとバージョンを明示し、依存関係として固定する
- `tools/generate_sdk.py` が壊れていないことを確認する最小限の pytest を追加する
- Spec、README、.cursorrules に反映し、「SDK 生成の運用ルール」として一貫させる

### ゴール

1. ジェネレーターのツール・バージョンの明示と固定
2. `generate_sdk.py` の「壊れていないこと」を確認するテスト追加
3. ドキュメント更新（Spec、README、.cursorrules）

### 原則

- 既存の実装（CR-FASTAPI-012）を壊さない
- 軽量テストのみ追加（実際の SDK 生成は行わない）
- ツールのバージョン情報を明示し、長期運用時のブレを防ぐ

## 2. コンテキストと前提

### 2.1 既存実装の確認

CR-FASTAPI-012 で以下が実装済み：

- `tools/generate_sdk.py` - SDK 自動生成スクリプト
- Makefile コマンド（`make sdk`, `make sdk-python`, `make sdk-ts`）
- `docs/api/README.md` に SDK 生成手順を追加
- `.cursorrules` に SDK Auto-Generation Rules を追加

### 2.2 現状の問題点

- 使用しているジェネレーター（`openapi-generator-cli`）のバージョンが明示されていない
- `tools/generate_sdk.py` が壊れていないことを確認するテストが存在しない
- 依存関係の管理方法が不明確

### 2.3 使用ツールの確認

`tools/generate_sdk.py` を確認した結果：

- **ツール名**: `openapi-generator-cli`
- **実行方法**:
  - `npx --yes openapi-generator-cli`（推奨）
  - `openapi-generator`（Java版、フォールバック）
- **バージョン**: 明示されていない（npx 経由の場合は最新版が自動取得される）

## 3. スコープ（Scope）

### In Scope

#### A. ジェネレーターのツール・バージョンの明示と固定

1. **現状調査**
   - `tools/generate_sdk.py` を確認し、実際にどのツール・ライブラリを使っているかを特定
   - 結果: `openapi-generator-cli`（npx 経由または Java 版）

2. **依存関係の固定**
   - `openapi-generator-cli` は外部 CLI ツール（npm パッケージまたは Java アプリ）のため、Python の requirements には追加しない
   - Spec と docs に、必要なツールと推奨バージョンを明記する

3. **Spec の更新**
   - `docs/spec/CR-FASTAPI-012A_SDK_Tooling_Hardening.md`（本 Spec）に以下を記載：
     - 使用するジェネレーター名: `openapi-generator-cli`
     - 推奨バージョン: 最新版（npx 経由の場合）または 7.x 系（Java 版の場合）
     - 前提となるインストール方法（npm/npx または Java）

#### B. generate_sdk.py の「壊れていないこと」を確認するテスト追加

1. **新規テストファイルの追加**
   - `tests/tools/test_generate_sdk_safe.py` を新規作成

2. **テスト内容**
   - `tools/generate_sdk.py` が正常に import できること
   - `--help` 相当の呼び出しがエラーなく動くこと
   - 内部関数の呼び出しが正常に動作すること（subprocess はモック）

3. **実装方針**
   - subprocess.run は monkeypatch や unittest.mock.patch で差し替え
   - 呼び出し自体が行われること、例外を投げないことだけを検証
   - 実ファイル生成（sdk/python/*, sdk/typescript/*）は行わない

#### C. ドキュメント更新

1. **docs/api/README.md**
   - 「SDK 生成」セクションに以下を追記：
     - 使用するジェネレーター名とバージョン
     - 依存関係のインストール手順（npm/npx または Java）
     - `make sdk`, `make sdk-python`, `make sdk-ts` の前提条件

2. **README.md**
   - 「API / SDK」関連のセクションがあれば、そこにも簡潔に：
     - 「OpenAPI from FastAPI」
     - 「tools/generate_sdk.py で SDK 自動生成」
     - 「手書き SDK を禁止し、OpenAPI を単一のソースとする」方針を一文で明記

3. **.cursorrules**
   - 既存の「SDK Auto-Generation Rules」を拡張：
     - AI に SDK コードを「新規で手書きさせない」
     - SDK の変更は必ず `tools/generate_sdk.py` と Spec の更新を伴う

### Out of Scope

- SDK の生成ロジック自体を大きく組み替えること
- 新しいジェネレーターへの乗り換え（例: 別ツールへの全面移行）
- OpenAPI スキーマ（FastAPI 側）に対する仕様変更
- SDK ソース（sdk/python/, sdk/typescript/ 以下）の手書き編集
- CI / GitHub Actions の大きな再設計

## 4. 実装方針（Design / Implementation Plan）

### 4.1 ツール・バージョンの明示

- **ツール名**: `@openapitools/openapi-generator-cli`
- **推奨インストール方法**: `npx --yes openapi-generator-cli`（最新版を自動取得）
- **代替方法**: Java 版 `openapi-generator`（バージョン 7.x 系推奨）
- **ドキュメント化**: Spec と README に明記

### 4.2 テスト実装

- **テストファイル**: `tests/tools/test_generate_sdk_safe.py`
- **テスト内容**:
  1. `tools.generate_sdk` モジュールの import が成功すること
  2. `main()` 関数が `--help` 引数で正常終了すること（subprocess はモック）
  3. `check_openapi_generator()` 関数が正常に動作すること（subprocess はモック）

### 4.3 ドキュメント更新

- Spec、README、.cursorrules を一貫性を持って更新
- 「SDK 生成の運用ルール」として明確化

## 5. テスト方針（Testing Strategy）

### 5.1 追加するテスト

- `test_generate_sdk_import()`: モジュールの import が成功すること
- `test_generate_sdk_help_runs()`: `--help` オプションが正常に動作すること
- `test_check_openapi_generator_mocked()`: `check_openapi_generator()` が正常に動作すること（subprocess はモック）

### 5.2 テスト実行コマンド

```bash
# SDK ツールが壊れていないことの確認
python tools/generate_sdk.py --help

# 追加したテストのみ（時間短縮のため）
pytest tests/tools/test_generate_sdk_safe.py -q
```

## 6. 完了条件（Definition of Done）

- [ ] `docs/spec/CR-FASTAPI-012A_SDK_Tooling_Hardening.md` を作成（本 Spec）
- [ ] `tests/tools/test_generate_sdk_safe.py` を追加
- [ ] `docs/api/README.md` を更新（SDK 生成セクションにツール・バージョン情報を追加）
- [ ] `README.md` を更新（SDK 自動生成の説明を追加）
- [ ] `.cursorrules` を更新（SDK 手書き禁止ルールを追加）
- [ ] テスト実行（`python tools/generate_sdk.py --help` と `pytest tests/tools/test_generate_sdk_safe.py -q`）
- [ ] 完了レポート作成（`docs/api/CR-FASTAPI-012A_COMPLETION_REPORT.md`）

## 7. 参照（References）

- [CR-FASTAPI-012 Spec](./CR-FASTAPI-012_SDK_Auto_Generation.md) - 前提となる CR
- [CR-FASTAPI-012 Completion Report](../api/CR-FASTAPI-012_COMPLETION_REPORT.md) - 前提となる CR の完了レポート
- [SDK Generation Script](../../tools/generate_sdk.py) - SDK 自動生成スクリプト
- [API README](../api/README.md) - FastAPI Migration Prompts & Documentation

