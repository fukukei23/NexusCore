"""旧 brownfield_orchestrator.py から baseline イベント列を取得（リファクタ前）。"""
import json, re, sys
from pathlib import Path
from typing import List, Tuple, Optional, Generator


def normalize(events):
    """タイムスタンプ・tmpパスを正規化して決定論化（baseline前後比較用）。

    Task4 (test_core_stream.py) でも capture() の戻りを比較前に必ず通すこと。
    3パターンをプレースホルダ化:
      - tmp_path : /tmp/<tmpdir>/...        → <TMP>/
      - now_tag  : 2026-07-01_01-05-51_JST   → <TS>
      - isoformat: 2026-07-01T01:05:51.021093+09:00 → <TS>
    """
    s = json.dumps(events, ensure_ascii=False)
    s = re.sub(r"/tmp/[A-Za-z0-9_]+/", "<TMP>/", s)
    s = re.sub(r"\d{4}-\d{2}-\d{2}_[\d\-:]+_JST", "<TS>", s)
    s = re.sub(r"\d{4}-\d{2}-\d{2}T[\d.\-:+]+", "<TS>", s)
    return json.loads(s)

# 旧ファイルを import するため sys.path に tools/ を追加
_TOOLS = Path(__file__).resolve().parents[3] / "tools"
sys.path.insert(0, str(_TOOLS))
import brownfield_orchestrator as old  # 旧485行ファイル（まだ shim 化前）

def fake_stream_run(cmd, cwd) -> Generator[str, None, Tuple[bool, str]]:
    """決定論的 fake。stream_run と同じ形状（yield 行 → return (ok, out)）。"""
    yield "--- [fake] phase line 1\n"
    yield "--- [fake] phase line 2\n"
    return (True, "fake output")

def capture(tmp_path: Path) -> List[Tuple[str, str, Optional[str]]]:
    events = []
    # stream_run を fake に置換（旧モジュール内の参照）
    old.stream_run = fake_stream_run
    # !!IMPORTANT!! Task4 (test_core_stream.py) でもこの2つの mock が必須:
    #   old.stream_run       = fake_stream_run           # 決定論的フェイク出力
    #   old.load_policy_meta = lambda *a, **k: {}        # 実ファイル読み込み回避（空 dict）
    # load_policy_meta は PROJECT_TOP の実ファイルを読むため tmp 配下で完結せず、
    # これを mock しないと環境差分で summary が変わり baseline 比較が破壊される。
    # run_brownfield_stream 内は .get() 既定値で動作する。
    old.load_policy_meta = lambda *a, **k: {}
    gen = old.run_brownfield_stream(
        project_root=str(tmp_path / "proj"),
        out_root=str(tmp_path / "out"),
        profiles=["gemini-single-file"],
        selected_phases=["structure", "snapshot"],
        policy_profile_ui="", policy_version_ui="", policy_icon_ui="",
        richness_mode="Light (fast)",
        include_full_archive=False,
    )
    if gen:
        for ev in gen:
            events.append(list(ev))  # (log_text, summary, zip_path) → JSON 用に list 化
    return events

if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        events = capture(Path(td))
    # baseline は人間が diff で読むため indent=2 で整形。
    # タイムスタンプ・tmpパスは normalize() で正規化して決定論化（Task4 再利用）。
    events = normalize(events)
    out = Path(__file__).parent / "_baseline_events.json"
    out.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved {len(events)} events -> {out}")
