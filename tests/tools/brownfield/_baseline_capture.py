"""旧 brownfield_orchestrator.py から baseline イベント列を取得（リファクタ前）。"""
import json, sys
from pathlib import Path
from typing import List, Tuple, Optional, Generator

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
    # load_policy_meta は PROJECT_TOP の実ファイルを読むため tmp 配下で完結しない。
    # 決定論性のため空 dict を返す mock に置換（run_brownfield_stream 内は .get() 既定値で動作）。
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
    out = Path(__file__).parent / "_baseline_events.json"
    out.write_text(json.dumps(events, ensure_ascii=False), encoding="utf-8")
    print(f"saved {len(events)} events -> {out}")
