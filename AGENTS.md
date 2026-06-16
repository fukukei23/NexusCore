# AGENTS.md — NexusCore

> マルチ AI コーディングツール共通プロジェクトガイド。
> Claude Code / Cursor / Codex / OpenCode / Aider / Devin / Gemini CLI 等はこのファイルを読む。
> ツール固有の細則は `CLAUDE.md` と `.claude/rules.md` を参照。

## 1. プロジェクト概要

**NexusCore** は AI エージェントによるソフトウェア開発自動化フレームワーク。
14 個の自律エージェントが、要求分析・アーキテクチャ設計・コード生成・テスト・品質保証までを一気通貫で担当する。
中核は **8 プロバイダ / 2 ティアの LLM ルーティング** と **2 段品質ゲート(Tier1 静的解析 + Tier2 ミューテーションテスト)**。

- バージョン: 8.2.0
- ライセンス: Apache 2.0
- 言語: Python 3.12+
- 配布: pip / Docker / k8s
- GitHub: <https://github.com/fukukei23/NexusCore>

## 2. クイックスタート

### セットアップ

```bash
git clone https://github.com/fukukei23/NexusCore.git
cd NexusCore
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.template .env
# .env に最低 1 つの LLM API キーを設定
#   OPENAI_API_KEY / ANTHROPIC_API_KEY / GEMINI_API_KEY
#   GLM_API_KEY    / MINIMAX_API_KEY   / DEEPSEEK_API_KEY / MOONSHOT_API_KEY
```

### 基本コマンド

```bash
# テスト(全件)
PYTHONPATH=src python -m pytest tests/ -x -q

# テスト(カバレッジ付き)
PYTHONPATH=src python -m pytest tests/ --cov=src/nexuscore --cov-report=html

# 品質スイープ (format + lint + typecheck + test)
make qa

# 開発サーバー
make server                                                 # FastAPI → http://127.0.0.1:8000 (OpenAPI: /api/docs)
PYTHONPATH=src python src/nexuscore/ui/unified_gradio_ui.py  # Gradio → http://localhost:7860

# CLI 実行
python main_cli.py --project-path /tmp/test "Pythonで二分探索を実装して"
```

## 3. ディレクトリ構造(前提 — 変更禁止)

```
NexusCore/
├── src/nexuscore/
│   ├── agents/      # 14 個の AI エージェント(BaseAgent 継承)
│   ├── api/         # FastAPI 公開 API(/api/v1/*)
│   ├── webapp/      # Flask SaaS 管理 UI(移行対象外、ブラウザ HTML 専用)
│   ├── ui/          # Gradio 統合 UI
│   ├── core/        # オーケストレータ、ジョブ状態機械、リトライ
│   ├── llm/         # LLM ルーティング(8 プロバイダ / 9 プロファイル)
│   ├── npe/         # 予算・ポリシー・ガードエンジン
│   ├── services/    # Self-Healing、パッチ適用
│   ├── governance/  # CR(Change Request)管理
│   ├── guard/       # 品質ゲート、コードレビュー
│   └── utils/       # Git、ログ、テスト戦略ユーティリティ
├── tests/           # テストスイート(agents / api / core / 他で構造化)
├── docs/            # ドキュメント
│   ├── overview/    # ビジョン、アーキ、ロードマップ
│   ├── spec/        # CR 仕様(spec-driven 開発)
│   ├── api/         # API 設計、エラーコードカタログ
│   ├── architecture/# アーキ詳細
│   ├── testing/     # テスト戦略
│   ├── governance/  # ガバナンス
│   └── adr/         # Architecture Decision Records
├── tools/           # scaffold_cr.py など補助スクリプト
└── sdk/             # 自動生成 SDK (Python / TypeScript)
```

> ⚠️ この構造は明示的指示なく変更しない。Flask の `webapp/` はブラウザ HTML 専用で FastAPI 移行の対象外。

## 4. アーキテクチャ要点

```
User / Developer
        ↓
   Orchestrator
        ↓
   ┌──────────────────────────────┐
   │ Agent Layer (14 専門エージェント) │
   └──────────────────────────────┘
        ↓      LLM Router      ↓
   [GPT-5.5 | Sonnet 4.6 | Gemini 3.1 | GLM-5.1 | DeepSeek | Moonshot | MiniMax]
                ↓
           Budget Manager (NPE)
                ↓
        Quality Gates
           ├── Tier 1: カバレッジ 80%+/Pylint 8.0+/Mypy/Bandit
           └── Tier 2: ミューテーションテスト
```

- **LLM 2 ティア構成**
  - 品質ティア(コード生成・推論・設計): OpenAI / Anthropic / Google
  - 軽量ティア(チャット・分類・分析): GLM / MiniMax / DeepSeek / Moonshot
- **Authority Runner**: 3 段階で自律レベルを切替
  - `HUMAN_CONTROLLED` / `PARTIALLY_AUTONOMOUS` / `FULLY_AUTONOMOUS`
- **CR(Change Request)駆動**: `docs/spec/` 配下の CR 仕様書が開発フローの起点

## 5. 規約(全 AI 共通)

### 5.1 API 設計(強規約)

- **新規 HTTP API は FastAPI 必須**。Flask での API 追加禁止
- 公開エンドポイントは `/api/v1/*` プレフィックス(内部用は `/internal/*` or ルーティングなし)
- Request/Response は **Pydantic BaseModel** 必須(`dict` / `Any` 直返しは禁止)
- 公開 API の単一仕様は **OpenAPI**。コメント隠し仕様を作らない
- ルートハンドラは薄く保つ(パース → サービス呼び出し → レスポンスマッピング)
- ビジネスロジックは `services/` か `core/` に置く
- FastAPI から Gradio / UI を import しない

### 5.2 認証 / セキュリティ

- `Depends(get_current_user)` または `Depends(get_api_key)` を使う
- `/api/v1/*` 配下の認証方式は一貫させる
- 例外: GitHub Webhook は署名検証のみ
- **シークレットは環境変数か設定モジュール経由**。`.env` を直接読み書きしない

### 5.3 エラーレスポンス

```json
{
  "error": {
    "code": "SOME_CODE",
    "message": "Human-readable message"
  }
}
```

- 生の例外オブジェクト / スタックトレースをクライアントに返さない
- エラーコードは `docs/api/エラーコードカタログ.md` で一元管理(SSOT)

### 5.4 テスト

- フレームワーク: pytest(カバレッジ目標 80%)
- 新規 API テストは `TestClient` を使用
- 既存 Flask テストは移行期間中 skip 可
- **CI-safe**: 外部ネットワーク・外部 API 依存テストはモック必須

### 5.5 コミット規約

Conventional Commits 準拠:

```
feat:      新機能
fix:       バグ修正
docs:      ドキュメント
test:      テスト追加・修正
refactor:  リファクタリング
perf:      性能改善
chore:     その他(ビルド、依存関係など)
```

### 5.6 変更履歴(必須)

コミットした変更(機能追加・バグ修正・リファクタ)は `docs/変更履歴.md` へ
**Keep a Changelog** 形式(Added / Changed / Fixed / Removed / Deprecated)で追記する。
セッション終了時 or タスク完了時に必ず更新。

## 6. タスク分類(重要)

### Tier 1 — 実装前に仕様確認 + ユーザー承認

- 認証 / 認可、決済 / 課金
- データ移行 / DB スキーマ変更
- 公開 API 設計
- セキュリティ関連(暗号化、CORS、CSRF、OAuth、JWT)
- `.env` / API キー関連、秘密情報の取り扱い変更

→ 必ず 3 項目(what / constraints / scope)で仕様提示 → ユーザー確認 → 実装

### Tier 2 — 直接実装OK

- ビジネスロジック実装、UI 実装
- バグ修正、リファクタ
- テスト追加、ドキュメント更新

## 7. やってはいけないこと(全 AI 共通)

- 🚫 `.env` ファイルの中身を読み取ってチャット / コミット / SSOT に貼り出す
- 🚫 API キー / シークレットをコードにハードコード
- 🚫 `git push --force` / `--no-verify` を独断で実行
- 🚫 ディレクトリ構造を明示的指示なく変更
- 🚫 Flask での新規 API 追加
- 🚫 `dict` / `Any` を返す API ハンドラ
- 🚫 外部依存テストをモックなしで CI に混ぜる
- 🚫 `rm -rf` 系の破壊削除(`mavis-trash` 等の復元可能手段を使う)
- 🚫 `.env` を直接書き換える(必ず `.env.template` 経由で手順を確認する)
- 🚫 Tier 1 タスクの暗黙実装
- 🚫 エラースタックトレースをそのまま API レスポンスに含める

## 8. 言語ポリシー

- **人間向け出力**: 日本語優先
- **ファイルパス・関数名・クラス名・コード内識別子**: 英語のまま
- **コミットメッセージ**: 英語 or 日本語どちらでも OK(チーム慣習に従う)
- **ドキュメント**: 原則日本語(コード例は英語 OK)

## 9. 関連ドキュメント

| 内容 | 場所 |
|---|---|
| 開発者向けセットアップ詳細 | `docs/setup/development_setup.md` |
| アーキテクチャ詳細 | `docs/architecture/ARCHITECTURE_CORE.md` |
| ビジョン・ロードマップ | `docs/overview/00_OVERVIEW_INDEX.md` |
| API 仕様 | `docs/srs/NEXUSCORE_SRS.md` |
| テスト戦略 | `docs/testing/testing_guide.md` |
| 開発ガイド | `docs/開発ガイド.md` |
| ガバナンス | `docs/governance/NEXUSCORE_GOVERNANCE.md` |
| リファクタリングバックログ | `docs/refactoring/REFACTORING_BACKLOG.md` |
| エラーコードカタログ(SSOT) | `docs/api/エラーコードカタログ.md` |
| **Claude 固有ルール** | `CLAUDE.md`, `.claude/rules.md` |
| **変更履歴** | `docs/変更履歴.md` |

## 10. AI ツール別ヒント

- **Claude Code**: `CLAUDE.md` と `.claude/rules.md` を必ず併読
- **Cursor**: `.cursor/` 配下の設定を尊重。`/api/v1` 規約とディレクトリ構造を厳守
- **Codex / OpenCode / Aider**: このファイル単独で自己完結する
- **Devin**: §4(アーキ)と §3(ディレクトリ構造)を特に重視
- **CI / 自動エージェント**: §6 の Tier 分類と §7 の禁止事項を厳守
- **コードレビュー Bot**: §5 の規約と §6 の Tier 分類を判定基準に使う
