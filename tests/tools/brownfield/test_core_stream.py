"""run_brownfield_stream の baseline 剴後比較テスト（振る舞い保存の正体）。"""
import json
import tempfile
from pathlib import Path
from typing import Generator, Tuple

_BASELINE = Path(__file__).parent / "_baseline_events.json"

# baseline は tempfile.TemporaryDirectory()（/tmp/<dir>/ 単層）で取得済み。
# pytest の tmp_path は /tmp/pytest-of-<user>/pytest-<N>/... と多層になり、
# Task1 の normalize regex (/tmp/[A-Za-z0-9_]+/) が取り残すため、
# ここでも tempfile 単層生成を使いパス形状を baseline に合わせる。


def _fake_stream_run(cmd, cwd) -> Generator[str, None, Tuple[bool, str]]:
    """Task1 の _baseline_capture.py の fake と完全一致させること。"""
    yield "--- [fake] phase line 1\n"
    yield "--- [fake] phase line 2\n"
    return (True, "fake output")


def test_run_brownfield_stream_matches_baseline(monkeypatch):
    """新 core.run_brownfield_stream のイベント列が baseline と完全一致（正規化後）。"""
    from brownfield import core
    from tests.tools.brownfield._baseline_capture import normalize  # Task1 共通正規化関数

    # ★ Task1 と同一の mock 2つ（必須・漏れ注意）
    monkeypatch.setattr(core, "stream_run", _fake_stream_run)
    monkeypatch.setattr(core, "load_policy_meta", lambda *a, **k: {})

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        events = []
        gen = core.run_brownfield_stream(
            project_root=str(td_path / "proj"),
            out_root=str(td_path / "out"),
            profiles=["gemini-single-file"],
            selected_phases=["structure", "snapshot"],
            policy_profile_ui="", policy_version_ui="", policy_icon_ui="",
            richness_mode="Light (fast)",
            include_full_archive=False,
        )
        for ev in gen:
            events.append(list(ev))

    expected = json.loads(_BASELINE.read_text(encoding="utf-8"))
    # baseline は既に正規化済み（<TS>/<TMP>）。実行結果も正規化して比較。
    assert normalize(events) == expected, (
        f"baseline 不一致: got {len(events)} events, expected {len(expected)}"
    )
