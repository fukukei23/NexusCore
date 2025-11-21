# Codex Bridge for NexusCore

Codex エージェント側で発生したクリティカル差分や RunLog を NexusCore に同期するための補助スクリプト群です。

```
codex_bridge/
├── diffs/                # クリティカルパッチを保存
├── runlogs/              # RunLog を保存
├── codex_diff_capture.py # diff 保存 + Git コミット補助
├── codex_runlog_sync.py  # RunLog 保存 + Postmortem 連携
└── README.md
```

## 1. 差分キャプチャ & Git 連携

```python
from codex_bridge.codex_diff_capture import save_critical_diff, commit_diff_to_git

patch_path, summary_path = save_critical_diff(diff_text, summary_text)
commit_diff_to_git("Fixed planner stub fallback")
```

- `codex_bridge/diffs/{timestamp}_critical.patch` に diff を保存。
- `codex_bridge/diffs/{timestamp}_codex_summary.txt` に Codex の要約を保存。
- `commit_diff_to_git()` は `[CodexCriticalFix] {要約}` 形式でコミットします。

Codex で Apply Patch が完了したタイミングで上記関数を呼び出してください。

## 2. RunLog を NexusCore Postmortem へ送信

```python
from codex_bridge.codex_runlog_sync import save_runlog, send_runlog_to_postmortem

json_path, ctx_path = save_runlog(runlog_json, run_context_text)
send_runlog_to_postmortem(str(json_path))
```

Postmortem Agent 呼び出しは内部で `PostmortemAgent.record_failure(runlog_text, source="codex")` を利用しています。

## 3. フック実装ポイント

- **差分フック**: Codex の Apply Patch / Critical Fix が成功した時点で `save_critical_diff()` → `commit_diff_to_git()` を呼ぶ。
- **RunLog フック**: Codex の実行ループ終了後、`save_runlog()` でログを保存し、重大なケースのみ `send_runlog_to_postmortem()` で NexusCore へ送信。

## 4. 動作確認手順

1. `python codex_bridge/codex_diff_capture.py` を単独実行し、`codex_bridge/diffs/` にファイルが作られることを確認。
2. `python codex_bridge/codex_runlog_sync.py` を単独実行し、`codex_bridge/runlogs/` へファイルが作成されることを確認。
3. Git で `codex_bridge/diffs` がコミットされることを確認 (`git log -- codex_bridge/diffs`など)。
4. Postmortem Agent ログ (`logs/` 以下) に `source="codex"` のエントリが出力されることを確認。

## 5. 想定環境

WSL / Windows 共通で動作するよう pathlib を使用しています。
