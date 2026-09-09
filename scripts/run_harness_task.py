"""v4 ラッパー: harness計測データ蓄積の定題実行（Phase 5 Task 27・review v4確定仕様）

設計正典: obsidian-ssot 00_SYSTEM/マルチLLMレビュー/2026-09-09_ハーネス計測段階拡張レビュー/
revised_proposal.md「r3 統合 — パラメータ確定版 v4」

v4 確定パラメータの実装対応:
- P3  抽出時にカテゴリ均等化を強制+ユニーク≥6（重複1許容）
- P8  題庫残<3題で警告・0題で停止（Phase C昇格時は閾値を1日分run数へ変更・現状Phase B固定）
- P9  watchdog: 直近50runの正規化hashユニーク<8で警告・<5で緊急停止（二段）
- P10 月額上限: 暫定HARNESS_MONTHLY_TOKEN_BUDGET（既定16M tok・$5相当の概算・第1週実績で再確定）
      到達時は短冊お題優先モード（残りお題を短い順に実行）
- P11 1runトークン上限: ソフト100k警告・ハード200k（**事後検知**。run中遮断はloop側改修が必要なため
      本ラッパーでは記録+無効扱いにする）
- P12 1run時間上限: ソフト10分警告・ハード15分強制終了（subprocess timeout）
- P15 metrics_history.jsonl にrun毎の計測6項目を恒久追記（run_stateは30日gzip圧縮は本ラッパー外）
- P16 連続欠損>3日で切替候補ログ・>5日で強制（短冊）モード（簡易実装: ログ出力）

無人モード（既定）は題庫の「無人用（読む系）」セクションのみ実行（ask fail-closed維持）。
手動用（書く系）は --manual でふくけい付き添い時に実行。

使い方:
    python scripts/run_harness_task.py --repo /path/to/NexusCore [--manual] [--dry-run]
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import unicodedata
import urllib.request
from datetime import UTC, datetime, timedelta
from datetime import timezone as tzmod
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

SOFT_TOKEN_LIMIT = 100_000   # P11 ソフト上限（警告）
HARD_TOKEN_LIMIT = 200_000   # P11 ハード上限（事後検知・無効扱い）
SOFT_TIME_SEC = 600          # P12 ソフト10分（警告）
HARD_TIME_SEC = 900          # P12 ハード15分（強制終了）
DEFAULT_MONTHLY_TOKEN_BUDGET = 16_000_000  # P10 暫定（$5相当の概算・第1週実績で再確定）
WATCHDOG_WARN_UNIQUE = 8     # P9 二段
WATCHDOG_STOP_UNIQUE = 5
POOL_LOW_WARN = 3            # P8 題庫残<3で警告
CRON_EXIT_SKIP = 3           # cron-setup規定: 同日skip
CRON_EXIT_SELFCHECK = 78     # v2: 起動時selfcheck NG

_SECTIONS = {"無人用（読む系）": "auto", "手動用（書く系）": "manual"}
_TOPIC_RE = re.compile(r"^- \[( |x)\] ([^:：]+)[:：](.+)$")


def normalize(text: str) -> str:
    """正規化hash用の題文正規化（P9・空白/記号/全半角の揺れを吸収）"""
    t = unicodedata.normalize("NFKC", text).casefold()
    return re.sub(r"[\s\W_]+", "", t, flags=re.UNICODE)


def task_hash(text: str) -> str:
    return hashlib.sha256(normalize(text).encode()).hexdigest()[:16]


def parse_pool(pool_path: Path) -> dict[str, list[dict]]:
    """題庫mdをパースし {mode: [{category, text, done, line_no}]} を返す"""
    mode_key = None
    topics: dict[str, list[dict]] = {"auto": [], "manual": []}
    for i, line in enumerate(pool_path.read_text().splitlines(), 1):
        for header, key in _SECTIONS.items():
            if header in line and line.strip().startswith("#"):
                mode_key = key
        m = _TOPIC_RE.match(line.strip())
        if m and mode_key:
            topics[mode_key].append({
                "done": m.group(1) == "x",
                "category": m.group(2).strip(),
                "text": m.group(3).strip(),
                "line_no": i,
            })
    return topics


def pick_topic(topics: list[dict], week_seed: str,
               budget_mode: bool) -> tuple[dict | None, str]:
    """P3: カテゴリ均等化強制の非復元ランダム抽出（週シード）

    budget_mode=True は P10 短冊お題優先（残りを短い順）。
    """
    open_topics = [t for t in topics if not t["done"]]
    if not open_topics:
        return None, "pool_exhausted"
    rng = random.Random(week_seed)
    done_cats: dict[str, int] = {}
    for t in topics:
        if t["done"]:
            done_cats[t["category"]] = done_cats.get(t["category"], 0) + 1
    if budget_mode:
        return min(open_topics, key=lambda t: len(t["text"])), "budget_mode_shortest"
    min_done = min(done_cats.get(t["category"], 0) for t in open_topics)
    least = [t for t in open_topics if done_cats.get(t["category"], 0) == min_done]
    return rng.choice(least), "category_balanced"


def load_history(history_path: Path) -> list[dict]:
    if not history_path.exists():
        return []
    out = []
    for line in history_path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            print(f"[wrapper] WARN: 履歴の破損行をskip: {line[:50]}", flush=True)
    return out


def watchdog_check(history: list[dict]) -> str:
    """P9 二段watchdog（直近50runの正規化hashユニーク数）"""
    recent = [h for h in history[-50:] if h.get("task_hash")]
    uniq = len({h["task_hash"] for h in recent})
    if len(recent) >= 10 and uniq < WATCHDOG_STOP_UNIQUE:
        return f"stop: unique_tasks={uniq}/{len(recent)}"
    if len(recent) >= 10 and uniq < WATCHDOG_WARN_UNIQUE:
        return f"warn: unique_tasks={uniq}/{len(recent)}"
    return "ok"


def monthly_tokens(history: list[dict]) -> int:
    """当月累積トークン（P10）"""
    now = datetime.now(UTC).strftime("%Y-%m")
    total = 0
    for h in history:
        ts = str(h.get("ts", ""))
        if len(ts) >= 7 and ts[:7] == now:  # 不正形式tsは当月に含めない（r3 OR）
            total += h.get("tokens_used") or 0
    return total


def run_harness(repo: Path, task: str, state_path: Path, timeout: int) -> tuple[int, str, str]:
    """harness_cli実行（無人=読む系のみ・--ask無し fail-closed）"""
    provider = os.environ.get("NEXUS_HARNESS_PROVIDER", "deepseek")
    model = os.environ.get("NEXUS_HARNESS_MODEL", "deepseek:deepseek-chat")
    cmd = [str(repo / ".venv/bin/python"), "-m", "nexuscore.cli.harness_cli",
           task, "--provider", provider, "--model", model,
           "--state-path", str(state_path)]
    proc = subprocess.run(cmd, cwd=repo, capture_output=True, text=True,
                          timeout=timeout)
    return proc.returncode, proc.stdout, proc.stderr


def mark_done(pool_path: Path, line_no: int, topic_text: str = "") -> bool:
    """題庫の[x]マーカーを原子的更新（flock失敗時はskip）

    r2 Gemini#1/OR#2: line_no単独は実行中の題庫編集で別行を誤[x]化するため、
    該当行がtopic_textを含むか検証してから置換する（不一致時は題文で再探索）。
    """
    lock = pool_path.with_suffix(pool_path.suffix + ".lock")
    with open(lock, "w") as lf:
        try:
            fcntl.flock(lf.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("[wrapper] 題庫lock競合 → [x]更新をskip", flush=True)
            return False
        lines = pool_path.read_text().splitlines()
        idx = line_no - 1
        if idx >= len(lines) or topic_text not in lines[idx]:
            matches = [i for i, ln in enumerate(lines) if topic_text and topic_text in ln]
            if not matches:
                print("[wrapper] 題文が題庫に見つからず [x]更新をskip", flush=True)
                return False
            idx = matches[0]
        lines[idx] = lines[idx].replace("- [ ]", "- [x]", 1)
        tmp = pool_path.with_suffix(pool_path.suffix + ".tmp")
        tmp.write_text("\n".join(lines) + "\n")
        tmp.replace(pool_path)  # 原子的置換（Gemini#1 r2）
        return True


_WRAPPER_LOCK_FP = None  # flock保持用（GCでlockが解放される事故の対策・テストで実測捕捉）


def today_jst() -> str:
    """当日スタンプの日付文字列（JST明示・r1 MiniMax TZ指摘対応）"""
    return datetime.now(tzmod(timedelta(hours=9))).strftime("%Y-%m-%d")


def stamp_path(repo: Path) -> Path:
    return repo / "artifacts/harness/.stamp-last-success"


def check_daily_stamp(repo: Path, force: bool) -> bool:
    """cron-setup規定: 当日成功スタンプが既にあればskip（成功時のみ書込=失敗翌日再試行可）"""
    if force:
        return True
    sp = stamp_path(repo)
    try:
        return sp.read_text().strip() != today_jst()
    except OSError:
        return True


def write_stamp(repo: Path) -> None:
    stamp_path(repo).parent.mkdir(parents=True, exist_ok=True)
    stamp_path(repo).write_text(today_jst())


def heartbeat(repo: Path) -> None:
    """v2 Gemini critical2: 成功時の死活痕跡（mtimeでstale検知）"""
    hb = repo / "artifacts/harness/heartbeat"
    hb.parent.mkdir(parents=True, exist_ok=True)
    hb.touch()


def selfcheck(repo: Path) -> str | None:
    """v2 MiniMax fail条件提案: 起動時自己診断（NG理由を返す・OKはNone）"""
    if not (repo / ".venv/bin/python").exists():
        return "venv python不在"
    pool = repo / "docs/harness_題庫.md"
    if not pool.exists() or not parse_pool(pool)["auto"] and not parse_pool(pool)["manual"]:
        if not pool.exists():
            return "題庫ファイル不在"
    return None


def notify_failure(repo: Path, message: str) -> None:
    """v2 MiniMax#3: Discord通知はbest-effort・失敗時は.notify.fail退避"""
    url = os.environ.get("DISCORD_CLAUDE_WEBHOOK")
    (repo / "artifacts/harness").mkdir(parents=True, exist_ok=True)
    if not url:
        with open(repo / "artifacts/harness/.notify.fail", "a") as f:
            f.write(f"{today_jst()} no-webhook-url: {message}\n")
        return
    try:
        req = urllib.request.Request(
            url, data=json.dumps({"content": f"[harness cron] {message}"}).encode(),
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    except Exception as exc:  # noqa: BLE001 best-effort・通知失敗も退避
        with open(repo / "artifacts/harness/.notify.fail", "a") as f:
            f.write(f"{today_jst()} notify_error: {exc}: {message}\n")


def acquire_wrapper_lock(repo: Path) -> bool:
    """ラッパー全体の二重起動防止（MiniMax r3-critical・cron多重発火で同一お題二重実行を防ぐ）"""
    global _WRAPPER_LOCK_FP
    lock = repo / "artifacts/harness/wrapper.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    lf = open(lock, "w")
    try:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lf.close()
        print("[wrapper] 二重起動検出 → skip（exit 0）", flush=True)
        return False
    _WRAPPER_LOCK_FP = lf  # モジュール参照で保持（解放されない・プロセス終了まで有効）
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="v4 ラッパー: harness定題実行")
    ap.add_argument("--repo", type=Path, default=REPO)
    ap.add_argument("--manual", action="store_true", help="手動用（書く系）お題を実行")
    ap.add_argument("--dry-run", action="store_true", help="抽出のみで実行しない")
    ap.add_argument("--monthly-token-budget", type=int,
                    default=DEFAULT_MONTHLY_TOKEN_BUDGET)
    ap.add_argument("--force", action="store_true",
                    help="当日スタンプを無視して再実行（手動用・MiniMax r1逆シナリオ対応）")
    args = ap.parse_args()
    repo: Path = args.repo
    ng = selfcheck(repo)
    if ng and not args.dry_run:
        print(f"[wrapper] SELFCHECK NG: {ng} → exit {CRON_EXIT_SELFCHECK}", flush=True)
        notify_failure(repo, f"selfcheck NG: {ng}")
        return CRON_EXIT_SELFCHECK
    if not args.dry_run and not args.force and not check_daily_stamp(repo, False):
        print("[wrapper] 当日成功済み → skip", flush=True)
        return CRON_EXIT_SKIP
    if not args.dry_run and not acquire_wrapper_lock(repo):
        return 0
    (repo / "artifacts/harness").mkdir(parents=True, exist_ok=True)  # r2 Gemini#3 親dir不在
    pool_path = repo / "docs/harness_題庫.md"
    history_path = repo / "artifacts/harness/metrics_history.jsonl"
    mode = "manual" if args.manual else "auto"
    warnings: list[str] = []

    topics = parse_pool(pool_path)[mode]
    history = load_history(history_path)
    open_topics = [t for t in topics if not t["done"]]

    # P8 題庫枯渇（Phase B: 残<3警告・0停止）
    if not open_topics:
        print("[wrapper] STOP: お題プール枯渇（0題）", flush=True)
        return 4
    if len(open_topics) <= POOL_LOW_WARN:
        warnings.append(f"pool_low: 残り{len(open_topics)}題（警告閾値{POOL_LOW_WARN}）")

    # P10 月額予算
    used = monthly_tokens(history)
    budget_mode = used >= args.monthly_token_budget
    if budget_mode:
        warnings.append(f"monthly_budget_exceeded: {used} >= {args.monthly_token_budget}")

    # P16 連続欠損（簡易: 履歴に記録のある最終日からの日数）
    if history:
        last_day = str(history[-1].get("ts", ""))[:10]
        gap_days = (datetime.now(UTC).date()
                    - datetime.fromisoformat(last_day).date()).days
        if gap_days > 5:
            warnings.append(f"run_gap: {gap_days}日連続欠損（強制短冊モード推奨）")
        elif gap_days > 3:
            warnings.append(f"run_gap: {gap_days}日欠損（切替候補）")

    wd = watchdog_check(history)
    if wd.startswith("stop"):
        print(f"[wrapper] STOP: watchdog緊急停止（{wd}）", flush=True)
        return 5
    if wd.startswith("warn"):
        warnings.append(f"watchdog_{wd}")

    week_seed = datetime.now(UTC).strftime("%G-W%V") + mode
    topic, how = pick_topic(topics, week_seed, budget_mode)
    if topic is None:
        print("[wrapper] STOP: 抽出失敗", flush=True)
        return 4
    print(f"[wrapper] topic: {topic['category']}: {topic['text'][:60]} "
          f"(pick={how}・hash={task_hash(topic['text'])})", flush=True)
    for w in warnings:
        print(f"[wrapper] WARN: {w}", flush=True)
    if args.dry_run:
        return 0

    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    state_path = repo / f"artifacts/harness/run_state_{ts}.json"
    t0 = datetime.now(UTC)
    try:
        rc, out, err = run_harness(repo, topic["text"], state_path, HARD_TIME_SEC)
    except subprocess.TimeoutExpired:
        rc, out, err = -9, "", f"timeout after {HARD_TIME_SEC}s"
        warnings.append(f"hard_time_limit: {HARD_TIME_SEC}s超過で強制終了")
    duration = int((datetime.now(UTC) - t0).total_seconds())
    if duration >= SOFT_TIME_SEC:
        warnings.append(f"soft_time_limit: {duration}s >= {SOFT_TIME_SEC}s")
    try:
        final = json.loads(out.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        final = {}
    tokens = final.get("tokens_used") or 0
    if tokens >= HARD_TOKEN_LIMIT:
        warnings.append(f"hard_token_limit: {tokens} >= {HARD_TOKEN_LIMIT}（無効扱い）")
    elif tokens >= SOFT_TOKEN_LIMIT:
        warnings.append(f"soft_token_limit: {tokens} >= {SOFT_TOKEN_LIMIT}")
    if rc != 0:
        err_tail = (err or "").strip().splitlines()[-1][:120] if (err or "").strip() else "stderr空"
        warnings.append(f"harness_exit={rc}: {err_tail}")  # r2 Gemini#2 stderr握りつぶし対策

    rec = {"ts": datetime.now(UTC).isoformat(),
           "task_hash": task_hash(topic["text"]), "category": topic["category"],
           "mode": mode, "interactive": args.manual, "ask_used": args.manual,
           "provider": "deepseek", "model": "deepseek-chat",
           "harness_version": subprocess.run(
               ["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
               capture_output=True, text=True).stdout.strip(),
           "loop_steps": final.get("loop_steps"), "tokens_used": tokens,
           "abort_reason": final.get("abort_reason"),
           "breaker_state": final.get("breaker_state"),
           "duration_sec": duration, "state_file": str(state_path),
           "warnings": warnings}
    hlock = history_path.with_suffix(history_path.suffix + ".lock")
    with open(hlock, "w") as hl, open(history_path, "a") as f:
        fcntl.flock(hl.fileno(), fcntl.LOCK_EX)  # r3 MiniMax: 並行追記競合対策
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        f.flush()

    if not mark_done(pool_path, topic["line_no"], topic["text"]):
        warnings.append("marker_update_skipped")
    if final.get("abort_reason") is None:
        write_stamp(repo)   # cron-setup規定: 成功時のみスタンプ（失敗翌日は再試行可）
        heartbeat(repo)     # v2 Gemini#2: 成功時死活痕跡
    else:
        notify_failure(repo, f"abort: {final.get('abort_reason')} tokens={tokens}")
    subprocess.run([sys.executable, str(repo / "scripts/collect_harness_metrics.py"),
                    "--root", str(repo)], cwd=repo, capture_output=True)
    for w in warnings:
        print(f"[wrapper] POST: {w}", flush=True)
    print(f"[wrapper] done: tokens={tokens} abort={final.get('abort_reason')}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
