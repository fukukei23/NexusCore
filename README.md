# NexusCore

**NexusCore** は自律型 AI エージェント群を組み合わせてソフトウェア開発支援を行うフレームワークです。
道具立て（エージェント／Orchestrator／LLM ルーター）を分離しつつ、必要なツール・UI・テストを同一リポジトリ内で管理する設計になっています。

---

**Self-Healing Status (NexusCore SaaS MVP)**

<!-- NOTE: {PROJECT_ID} は実際の Project.id に置き換えてください（例: 1）。your-nexuscore-host は運用環境のホスト名に置き換えてください。 -->

[![Self-Healing Success Rate](https://your-nexuscore-host/api/v1/projects/1/badge/success_rate)](https://your-nexuscore-host/dashboard/projects/1)
[![Self-Healing Last Run](https://your-nexuscore-host/api/v1/projects/1/badge/last_run)](https://your-nexuscore-host/dashboard/projects/1)

- 🧠 **AIコード修復／開発支援**：Requirement→Planning→Coding→Testing まで各フェーズを担当するエージェント。
- ☁️ **SaaS展開を意識した分離設計**：LLM/エージェント/オーケストレータを独立レイヤーで構築。

---

## 📂 プロジェクト構成


主要な構成を踏まえ、以下のディレクトリ構成と設定ファイルが重要です。

### 主要ディレクトリ構成

```
NexusCore/
├── src/nexuscore/
│   ├── agents/           # 構成エージェント（planner, coder, debugger, guardian, policy 等）
│   ├── core/             # Orchestrator、NPE インテグレーション、主要フロー制御
│   ├── llm/              # LLMRouter、Provider 統合、プロンプト管理
│   ├── modules/          # エージェントから呼ばれるコード生成・テスト・差分表示ツール
│   ├── npe/              # 予算・ポリシー・ログ・ガード機能の集合
│   └── gradio_app/       # UI/ダッシュボード/修復タイムライン（必要に応じて Streamlit 構成も）
├── dev_tools/             # Fast Lane チェックや開発支援スクリプト
├── tools/                 # ファイル一覧取得・エクスポート・ダッシュボードなどの補助ユーティリティ
├── tests/                 # pytest ベースのユニット / 統合テスト群
├── output/                # 実行ログ / 集計 / 一時ファイル（gitignore 対象）
└── .venv/                 # 仮想環境（WSL 操作時に生成・使用）
```

### 重要な設定ファイル

- `.env` / `.env.template` … OpenAI や Gemini など LLM API キー、予算、動作モードなど環境変数をまとめたファイル。`.env` は `.env.template` をコピーして内容を埋めたもの。
- `requirements.txt` / `requirements.lock.txt` / `pyproject.toml` … Python 依存の宣言とロック。依存追加時は `pip freeze > requirements.lock.txt` などで整合を取るのが重要です。
- `dev_tools/fast_lane_check.py` … 差分解析と Fast Lane 判定用。CI に組み込む場合は `python -m dev_tools.fast_lane_check --json` をコマンド化します。
- `.gitignore` / `output/` 以下 / `.venv/` … ログや生成ファイル、仮想環境などの除外を定義。`output/core_files.txt` などの共有リストを活用する際も位置を参考に。
- `src/nexuscore/config/config.py` & `src/nexuscore/config/generate_secrets.py` … プロジェクト固有の設定ロードと秘密情報生成を担うモジュール。README 内の環境変数手順と合わせて使います。

---

## 🔌 External Integrations

NexusCore can be triggered from VSCode extensions, Chrome extensions, or other tools via a simple REST API.

- See `docs/external_run_api_examples.md` for concrete examples (TypeScript / JavaScript / Python / curl).

### API 構成

NexusCore の API は以下のように構成されています：

- **FastAPI**: 公開 API 層（`/api/v1/*`）- 正式版（単一の正）
  - 外部統合向けの REST API は FastAPI ベースで実装されています
  - 統一された認証（API Key）、エラーハンドリング、OpenAPI スキーマを提供
  - すべてのクライアントは FastAPI エンドポイント（`/api/v1/*`）を使用する必要があります
  - 詳細は `docs/api/README.md` を参照してください

- **Flask**: Web UI 層（`/projects/*`, `/dashboard/*` など）- 当面存続
  - HTML テンプレート・ビューを提供する Web UI は Flask ベースで実装されています
  - Flask REST API（`/api/v1/*` 配下のエンドポイント）は **CR-FASTAPI-010 で完全削除済み**です
  - すべての REST API は FastAPI 側に統一されました
  - 詳細は `docs/api/FASTAPI_MIGRATION_STATUS.md` を参照してください

**重要**: Flask REST API (`/api/v1/*` 配下のエンドポイント) は CR-FASTAPI-010 で完全削除されました。すべてのクライアントは FastAPI エンドポイント（`/api/v1/*`）を使用する必要があります。

### アーキテクチャ: WebApp と FastAPI の責務分離

- **WebApp (Flask)**: サーバー内部 UI（人間向け HTML 画面）
  - HTML レンダリングとフォーム受け付けを担当
  - データ取得は FastAPI 経由ではなく、直接データベースアクセスまたは services 層を使用
  - FastAPI API migration の対象外（責務分離のため）
  - 詳細は `docs/api/WEBAPP_UI_API_MAPPING.md` を参照してください

- **FastAPI**: 公開 API（外部/機械向け JSON API）
  - SDK / CLI / 外部統合向けのエンドポイント（`/api/v1/*`）
  - 統一された認証、エラーハンドリング、OpenAPI スキーマを提供

### SDK 自動生成

NexusCore の FastAPI API から OpenAPI 仕様書を取得し、Python / TypeScript 向け SDK を自動生成できます。

- **OpenAPI 仕様書**: FastAPI アプリから自動生成（`/api/openapi.json`）
- **SDK 生成ツール**: `tools/generate_sdk.py`（OpenAPI Generator CLI を使用）
- **生成コマンド**: `make sdk`（すべての SDK を生成）、`make sdk-python`（Python のみ）、`make sdk-ts`（TypeScript のみ）

**重要**: SDK コードは手書きせず、必ず `tools/generate_sdk.py` を使用して OpenAPI 仕様書から自動生成してください。OpenAPI 仕様書が SDK の単一のソース（Single Source of Truth）です。

### E2E テスト

生成された SDK と FastAPI アプリの連携を実際に検証する E2E テストを実行できます：

```bash
# SDK を生成（事前に実行）
make sdk-python

# E2E テストを実行
make test-e2e
```

**注意**: SDK が生成されていない場合、E2E テストは自動的にスキップされます。
これは「テスト環境の問題」であり、SDK / API 実装のバグではありません。

詳細は `docs/api/README.md` の「SDK 自動生成」と「E2E テスト」セクションを参照してください。

---

## 🚀 Quick Start

### 1. WSL (Ubuntu) 環境での基本手順

1. `\\wsl.localhost\Ubuntu\home\yn441611\NexusCore`（Linux シェルでは `/home/yn441611/NexusCore`）に移動し、これを作業ルートにします。
2. システム Python には `pip` が入っていないため、`python3 -m venv venv` で仮想環境を作成します。
3. `source venv/bin/activate` で仮想環境を有効化し、`pip install -r requirements.txt` で依存をインストール。
   - 開発ツールも含める場合: `pip install -r requirements.txt -r requirements-dev.txt`
   - 主要な依存関係はバージョンレンジで固定されています（例: `openai>=1.30.0,<2.0.0`）。詳細は `requirements.txt` を参照してください。
4. 実行時は仮想環境を有効化（`source activate` または `source venv/bin/activate`）してから `python` / `pip` を呼び出してください。
   - より簡単な方法: プロジェクトルートで `source activate` を実行（推奨）
   - 詳細は `README_VENV.md` を参照してください。
5. ネイティブなログ・出力先は `/home/yn441611/NexusCore/...` に向け、権限エラーを回避します。
6. 依存を追加したら `pip freeze > requirements.lock.txt` などでロックファイルを更新して共有してください。

### 2. 依存要件

- Python **3.11+**
- Git
- Docker（任意：サービス連携 / デプロイ用）
- `pip-tools`：`pip install pip-tools`

### 3. ローカルで試すコマンド

- **Fast lane regression gate**
  リポジトリの差分検査には `dev_tools.fast_lane_check` を使います。

  ```bash
  .venv/bin/python -m dev_tools.fast_lane_check --json
  ```

  - `--base` … 比較対象ブランチ（既定 `origin/main`）
  - `--max-files` / `--max-lines-total` / `--max-lines-per-file` … 切り分けパラメータ
  - `FAST_LANE_FORCE=1` を使うとしきい値を無視

- **重要ファイル一覧の取得**

  ```bash
  .venv/bin/python -m tools.list_core_files --format text
  ```

  `--include` / `--exclude` でパターンを追加したり、`--format json` / `--output` で整形できます。

## 💬 Codex / AI への指示

- 対話の最初に Codex や他の AI に渡すプロンプトの冒頭で `「日本語でお願いします」` のテンプレート文を使うようにしてください。この README にそのテンプレートを残しておくと、各チャットが新しくなっても同じ日本語指定を繰り返し注入でき、記述忘れも防げます。

### 4. CLI 起動例

```bash
.venv/bin/python main_cli.py --project-path /tmp/nxcore --language ja "ChatOps ダッシュボードを作る"
```

引数例：`--constitution-text` でプロジェクト方針、`--requirement-ui` で RequirementAgent UI モード、`-v` で詳細ログ出力。

---

## 🧪 テストと検証

- `PYTHONPATH=src .venv/bin/pytest tests/core/test_orchestrator.py`
- `PYTHONPATH=src .venv/bin/pytest tests/agents/test_policy_agent.py`
- `PYTHONPATH=src .venv/bin/pytest tests/gradio_app/test_app_ui.py`
- `rg --files tests/agents` や `coverage run -m pytest tests/agents` / `coverage html` でテストファイルやカバレッジ状況を定期的に可視化すると、どのエージェント層が未テストか把握しやすくなります。

全体のテスト・CI は `PYTHONPATH=src` を忘れずに設定してください。

---

## 📚 ドキュメント構成

NexusCore プロジェクトの詳細ドキュメントは `docs/` ディレクトリに整理されています。

- **[ドキュメント全体インデックス](docs/DOCS_INDEX.md)** - すべてのドキュメントへのナビゲーション
- **[仮想環境の使い方](README_VENV.md)** - 仮想環境の簡単な使い方

**役割別の導線:**
- **新規開発者向け**: [開発環境セットアップ](docs/development_setup.md) → [README_VENV.md](README_VENV.md) → [Makefile ガイド](docs/makefile_guide.md)
- **運用担当者向け**: [Kubernetes クイックスタート](docs/k8s_quick_start_guide.md) → [SaaS アーキテクチャ](docs/saas_architecture.md)
- **AI / Cursor 向け**: [コードレビュー対応 Playbook](docs/cursor_nexuscore_playbook.md) → [Codex 指示マニフェスト](docs/codex_instruction_manifest.md)

### Specification (Spec) 管理ルール

本プロジェクトでは、全ての CR / 機能追加 / 設計変更について、仕様書（Spec）を `docs/spec/` に保存しています。

- **フォーマット**: Markdown (.md)
- **保存場所**: `docs/spec/`
- **命名規則**: `CR-NEXUS-XXX_xxx.md` / `CR-FASTAPI-XXX_xxx.md`
- **Cursor が実装する際は、必ず関連 Spec を読み込んでから実装する**

**作業フロー**: Spec → 実装 → テスト → レポート → ドキュメント更新 までが1セットの作業単位となります。

詳細は [Spec テンプレート](docs/spec/SPEC_TEMPLATE.md) を参照してください。

---

## 🧰 補足メモ

- `.env.template` をコピーして `.env` を作成し、API キーや最大予算などを記入してください。
- `output/` 以下にログや自動テスト結果がたまりますので、コミット不要のものは `.gitignore` に入れています。
- 大型変更を加えるときは `python -m tools.list_core_files --format json` などで影響範囲を確認しつつ、`tests/` の適切なユニットを更新してください。
- 新しい LLM プロバイダ追加時は下記フローに従ってください。
  1. `src/nexuscore/llm/providers/` に `<vendor>_provider.py` を新規作成し、`BaseLLM` を継承したクラスで実装（API キーの `None` 判定と `HTTP_CLIENT_FACTORY` の Session 取得が必須）。
  2. JSON 整形／スタブ応答には `src/nexuscore/llm/helpers.py` の `_strip_jsonish` / `_stub_response` / `DEFAULT_STUB_CONTENT` を利用し、例外は `self.logger` で `real`/`stub-fallback` のモードを分かるように記録する。
  3. `src/nexuscore/llm/providers/__init__.py` に新クラスを export し、`src/nexuscore/llm/llm_router.py` の `_make_client()` へファミリ判定を追加する。
  4. `LLMRouter` のタスクモデルマップ（`TASK_MODEL_MAP_DEFAULT` など）に新モデルを登録した上で、`nexuscore/npe` の budget/policy 設定にもモデル名を加える。
  5. ランタイム状態の確認には `from nexuscore.llm.runtime import log_runtime_status` を使い、`pytest tests/llm` にプロバイダ用のスタブテスト（API キーなし時の挙動等）を追加する。
- 2025-11-22 00:51 JST / Version 2.3.5-hotfix 時点で `src/nexuscore/llm/http_client.py` に `HttpClientFactory` を実装し、429/5xx リトライや `requests` 未導入時のスタブ降格処理を一元管理しています。LLM プロバイダを追加／拡張する際はこのモジュールから Session を取得してください。
