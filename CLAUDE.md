# CLAUDE.md — NexusCore

## プロジェクト概要

AIエージェントによるソフトウェア開発自動化フレームワーク。
- 14の自律エージェントがコード修復・テスト生成・デバッグを自動化
- Python / FastAPI / Flask / Celery / Redis / マルチLLMプロバイダー
- バージョン: 8.2.0

## アーキテクチャ

```
src/nexuscore/
├── agents/     # 14個の自律エージェント（BaseAgent継承）
├── core/       # オーケストレーション・ジョブ状態機械
├── llm/        # LLMルーティング（9プロファイル / 8プロバイダー）
├── npe/        # 予算・ポリシー・ログ管理
├── api/        # FastAPI REST API
├── webapp/     # Flask SaaSアプリ
└── utils/      # ユーティリティ
```

## 主要コマンド

```bash
source .venv/bin/activate
PYTHONPATH=src

# テスト
python -m pytest tests/ -x -q

# 品質チェック
make qa        # format + lint + typecheck + test

# 実行
python main_cli.py --project-path /tmp/test "タスク"
python src/nexuscore/ui/unified_gradio_ui.py   # 統合UI (localhost:7860)
```

## サーバー起動

```bash
# FastAPI サーバー（SDK生成・REST API）
make server    # uvicorn → http://127.0.0.1:8000
               # OpenAPI docs: http://127.0.0.1:8000/api/docs

# 統合UI (Gradio)
PYTHONPATH=src python src/nexuscore/ui/unified_gradio_ui.py   # http://localhost:7860
```

## LLMルーティング（2層構成）

| ティア | プロバイダー | モデル | 用途 |
|---|---|---|---|
| 品質 | OpenAI / Anthropic / Google | GPT-5.5 / Sonnet 4.6 / Gemini 3.1 | コード生成・推論・設計 |
| 軽量 | GLM / MiniMax | GLM-5.1 / MiniMax M2.7 | チャット・分類・分析 |

- プロファイル: `src/nexuscore/llm/llm_profiles.py`
- タスクマップ: `src/nexuscore/llm/task_model_map.py`

## テスト

- フレームワーク: pytest（カバレッジ目標80%）
- CI-safe: 外部パッケージ依存テストはモック必須
- 詳細: `docs/testing/testing_guide.md`

## 環境変数

`.env.template` を参照。最低1つのLLMプロバイダーAPIキーが必要。
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`
- `GLM_API_KEY`, `MINIMAX_API_KEY`

## コミット規約

```
feat: / fix: / docs: / test: / refactor: / perf: / chore:
```

## 変更記録ルール

- 機能追加・バグ修正・リファクタリングなどの変更をコミットした際、`docs/CHANGELOG.md` に追記すること
- フォーマットは Keep a Changelog 準拠（Added / Changed / Fixed / Removed / Deprecated）
- セッション終了時またはタスク完了時に更新

## 詳細ドキュメント

| 内容 | 場所 |
|---|---|
| セットアップ | `docs/setup/development_setup.md` |
| アーキテクチャ | `docs/architecture/ARCHITECTURE_CORE.md` |
| API仕様 | `docs/srs/NEXUSCORE_SRS.md` |
| テストガイド | `docs/testing/testing_guide.md` |
| 開発ガイド | `docs/DEVELOPMENT.md` |
| リファクタリング | `docs/refactoring/REFACTORING_BACKLOG.md` |
