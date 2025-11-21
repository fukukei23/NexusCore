# Codex Instruction Manifest (NexusCore Edition)

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
- 主なキー: `OPENAI_API_KEY`, `GEMINI_API_KEY`, `DEEPSEEK_API_KEY`, `KIMI_API_KEY`, `NEXUS_REAL_CALLS=1`
- `.env` 自体は Git に含めない。必要なら値の取得方法を README に追記。

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
3. LLMRouter がスタブモードになっていないか (`nexus_core_run.log` に "initialized in REAL-CALL mode" が出ているか) 常に監視。

---

## 6. イシュー記録

- 新しい課題を見つけたら `codex_bridge/diffs/` に整理し、`docs/` 配下にメモを追加。
- 再発した問題は `codex_runlog_sync` の RunLog とまとめて Postmortem Agent に送信し、自己修復サイクルに活用する。

---

Codex は「差分ログ」「RunLog」「テスト結果」の 3 点セットを必ず残してください。これが NexusCore の自律進化タスクの前提になります。
