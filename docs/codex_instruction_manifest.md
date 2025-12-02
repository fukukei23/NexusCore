# Codex Instruction Manifest (NexusCore Edition)

> **注意**: このファイルは「AI / Cursor 向けの指示とプレイブック」です。
> 全体のドキュメントインデックスは [DOCS_INDEX.md](DOCS_INDEX.md) を参照してください。

NexusCore はマルチエージェント開発 OS です。Codex が作業を引き継ぐ際は、以下の手順と約束事を守ってください。

---

## 1. リポジトリ構成

- ルート: `/home/yn441611/NexusCore`（WSL） / `C:\Users\yn441611\tools\NexusCore`（Windows）
- Codex フック用フォルダ: `codex_bridge/`
- メインエントリ: `main_cli.py`
- NPE/LLM ルータ: `src/nexuscore/core/orchestrator.py`, `src/nexuscore/llm/llm_router.py`

---

## 2. Codex が行うべきルーチン

1. **差分保存**
   - Apply Patch/クリティカル修正後に
     ```python
     from codex_bridge.codex_diff_capture import save_critical_diff, commit_diff_to_git
     patch, summary = save_critical_diff(diff_text, summary_text)
     commit_diff_to_git(summary_text)
     ```
   - `codex_bridge/diffs/` にファイルが生成されることを確認。

2. **RunLog 同期**
   - 実行ログや異常が発生した場合は
     ```python
     from codex_bridge.codex_runlog_sync import save_runlog, send_runlog_to_postmortem
     json_path, ctx_path = save_runlog(runlog_payload, run_context)
     send_runlog_to_postmortem(str(json_path))
     ```
   - Postmortem Agent 側のログに `source="codex"` が記録されているかをチェック。

3. **テスト実行**
   - 標準テストコマンド
     ```bash
     python main_cli.py --project-path ~/test_app "簡単なToDoアプリを作って。CLI ベースで。"
     ```
   - 可能であれば `pytest` / `scripts/` 下の専用テストも実行。

---

## 3. .env / API キーの扱い

- `.env.template` を `.env` にコピーして編集。
- 主なキー: `OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, `KIMI_API_KEY`（使わない場合は空で可）, `NEXUS_REAL_CALLS=1`
- `.env` 自体は Git に含めない。必要なら値の取得方法を README に追記。
- 実コール確認ショートカット:
  - OpenAI/Gemini: `curl` で `/v1/models` (要 BASE_URL 設定)
  - Claude: `curl -H "x-api-key: $ANTHROPIC_API_KEY" -H "anthropic-version: 2023-06-01" https://api.anthropic.com/v1/models`
- 実コールしたいときは `NEXUS_REAL_CALLS=1` を明示。スタブにしたいときは `0` を明示。
- LLM利用方針: 旧モデル (例: gpt-4o, gemini-1.5-pro/flash, llama3-local-8b など) は使用しない。現行は gpt-5.1 系 / gemini-2.5 系 / claude-3.5-sonnet を基本ラインとする。
- SaaS展開を見据え、環境変数はデフォルト値として扱いつつ、テナント/プロジェクト/リクエスト単位で安全に上書きできる設計方針で進める。

---

## 4. 作業ログとコミット方針

- `codex_history/` に自動で RunLog と diff が保存される。削除しない。
- Git コミットメッセージ:
  - クリティカル修正: `[CodexCriticalFix] ...`
  - その他: `[Codex] <短い説明>`
- `codex_bridge/README.md` に記載された手順を随時更新する。

---

## 5. エージェント連携手順

1. CLI/オーケストレータを走らせて現状を把握。
2. 失敗時は RunLog を Postmortem Agent に送信し、`logs/` を確認。
3. LLMRouter がスタブモードになっていないか (`logs/llm_calls.jsonl` の `mode=real`、`nexus_core_run.log` の "REAL-CALL mode") を常に監視。`NEXUS_REAL_CALLS` やキー設定漏れに注意。

---

## 6. イシュー記録

- 新しい課題を見つけたら `codex_bridge/diffs/` に整理し、`docs/` 配下にメモを追加。
- 再発した問題は `codex_runlog_sync` の RunLog とまとめて Postmortem Agent に送信し、自己修復サイクルに活用する。

---

## 7. LLM ルーティング（2025-11 三枚看板版）

- モデル役割:
  - OpenAI: `gpt-5.1-*`（コード生成/修復/ポリシー高推論）
  - Gemini: `gemini-2.5-pro/flash`（要件・設計・大量軽量処理）
  - Claude: `claude-3.5-sonnet`（レビュー/ポリシー/セカンドオピニオン）
- タスクマップは `src/nexuscore/llm/llm_router.py` の `TASK_MODEL_MAP_DEFAULT`。cheap モード時もタスクごとに軽量モデルへ自動アサイン。
- 環境変数:
  - `NEXUS_LLM_MODE=cheap` で安価系優先
  - `NEXUS_CLASSIFIER_MODEL` でタスク分類モデルを上書き可能（デフォルト `openai:gpt-5.1-instant`）

---

## 8. 30日ロードマップ（BUYMA排除版・引き継ぎ用要約）

- Day 1–5: 環境固定化（WSL/venv/VSCode、Docker排除、Python 3.12、requirements整備、.env分離、ログ/設定固定）
- Day 6–10: LLMRouter整合 & テスト緑化（タスクマップ最新化、get_llm_for_task再定義、Fake/Dummy互換、classify→route→execute統一、テスト全緑）
- Day 11–15: Orchestrator自律ループ安定化（Planner→Architect→Coder→Tester→Guardian→NPE一貫、Debugger/PatchApplier/Guardian safe commit、NPE v8整合）
- Day 16–20: VSCode拡張正式連携（WebSocket/child_processで Orchestrator 呼び出し、Diagnostics連携、ASTビュー、UI返却）
- Day 21–25: パッケージング（フォルダ整理、config/secrets/policy体系化、context bundle、Streamlitダッシュボード、コスト可視化、CLI統一）
- Day 26–30: SaaS準備（nexuscore-server/client、FastAPI REST、Stripeサブスク、Lite版、ログポリシー、docker-compose、TTL/キュー制御、ドキュメント/LP整備）
- 推定工数: 57–83h（集中時 40–55h）。BUYMAモジュールは完全除外の前提。

---

## 9. 全体アーキテクチャ（役割早見）

- Orchestrator（統制層）: プロジェクト全体のタスクフローとエージェント連携を管理。
- エージェント層:
  - Requirement → Planner → Architect → Coder → Tester → Debugger → Guardian → Postmortem
  - Knowledge Curator（KB管理）、Policy Agent（ポリシー監査）、Constitutional Council（憲法管理）
- データフロー:
  ユーザー要求 → Requirement → Planner → Architect → Coder → Tester → Debugger → Guardian → Postmortem
  知識ベース → Knowledge Curator → Policy → Constitutional Council
- ツール層: LLM Router（モデル選択）、Budget Manager（予算）、Logging System（監査ログ）、Security Systems（機密検出/マスキング）
- インタラクション: Gradio UI/Policy UI、API/Webhooks で外部連携。

---

Codex は「差分ログ」「RunLog」「テスト結果」の 3 点セットを必ず残してください。これが NexusCore の自律進化タスクの前提になります。
