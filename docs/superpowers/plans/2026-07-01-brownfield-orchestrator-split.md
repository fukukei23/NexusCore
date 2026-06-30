# brownfield_orchestrator.py God file 分割 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `tools/brownfield_orchestrator.py`（485行 God file）を `tools/brownfield/` パッケージ（6モジュール）へ分割し、振る舞いを完全保存して `python tools/brownfield_orchestrator.py --ui` の後方互換を維持する。

**Architecture:** パッケージ化 + importlib によらない sys.path 挿入型 thin shim（相対import問題を回避）。依存方向 `utils ← core ← ui ← __main__`（循環なし）。振る舞い保存は baseline 前後比較（stream_run を mock 境界にした golden input のイベント列 diff）で保証。

**Tech Stack:** Python 3（`from __future__ import annotations`）・Gradio・pytest・monkeypatch。リポジトリ: NexusCore。

**前提spec:** `docs/superpowers/specs/2026-07-01-brownfield-orchestrator-split-design.md`

**転記の原則:** 各モジュールは**旧 `tools/brownfield_orchestrator.py`（commit f7bb6100 時点）から該当行を転記**する。本計画は転記元行番号 + 調整点（import 文・定数の REPO_ROOT 化）を明示する。転記時に**関数本体のロジックは一切変更しない**（振る舞い保存）。

---

## File Structure

| ファイル | 責務 | 由来（旧ファイル行） |
|---|---|---|
| `tools/brownfield/__init__.py` | lazy `__getattr__`（main/build_ui）・gradio を引かない | 新規 |
| `tools/brownfield/__main__.py` | `parse_args` + `main(argv)` エントリ | L445-485 |
| `tools/brownfield/utils.py` | 定数 + IO/helper + stream_run + detect_latest_snapshot + orchestrator adapter | L47-128, L239-253, L255-317 |
| `tools/brownfield/core.py` | `run_brownfield_stream`（業務コア） | L131-233 |
| `tools/brownfield/ui.py` | `build_ui`, `auto_launch_with_increment`, `try_build_dir_picker` | L235-238, L318-443 |
| `tools/brownfield_orchestrator.py` | thin shim（後方互換・上書き） | 新規（旧ファイルと置換） |
| `tests/tools/brownfield/test_*.py` | smoke + baseline比較テスト群 | 新規 |

---

## Task 1: baseline イベント列取得（旧コードで正解記録）

**Files:**
- Create: `tests/tools/brownfield/__init__.py`（空）
- Create: `tests/tools/brownfield/_baseline_capture.py`（一時・旧コードから取得）
- Create: `tests/tools/brownfield/_baseline_events.json`（生成物）

- [ ] **Step 1: テストパッケージ雛形 + baseline 取得スクリプト作成**

`tests/tools/brownfield/__init__.py` を空ファイルで作成。

`tests/tools/brownfield/_baseline_capture.py`:
```python
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
```

- [ ] **Step 2: baseline 取得を実行**

Run: `cd ~/projects/NexusCore && python3 tests/tools/brownfield/_baseline_capture.py`
Expected: `saved N events -> .../_baseline_events.json`（N>=1）

> **注意:** 旧ファイル実行時、`run_brownfield_stream` 内で `load_policy_meta` 等のファイルIOが走る可能性。`tmp_path` 配下で完結しない場合は、Step1 の `capture` 内で `old.load_policy_meta = lambda *a, **k: {}` 等の追加 mock を差し込み、イベント列が安定するようにする。その場合、Task 4 の新コード側にも**同一 mock** を適用すること。

- [ ] **Step 3: baseline JSON が生成されたことを確認**

Run: `head -c 200 tests/tools/brownfield/_baseline_events.json`
Expected: JSON 配列（例: `[["...log text...", "", null], ...]`）

- [ ] **Step 4: commit**

```bash
git add tests/tools/brownfield/__init__.py tests/tools/brownfield/_baseline_capture.py tests/tools/brownfield/_baseline_events.json
git commit -m "test(brownfield): baseline イベント列取得(旧コード・リファクタ前)"
```

---

## Task 2: brownfield パッケージ雛形 + `__init__.py`（lazy `__getattr__`）

**Files:**
- Create: `tools/brownfield/__init__.py`
- Test: `tests/tools/brownfield/test_imports.py`

- [ ] **Step 1: 失敗テストを書く**

`tests/tools/brownfield/test_imports.py`:
```python
"""パッケージ import と lazy __getattr__ の検証。"""
import sys

def test_import_brownfield_does_not_load_gradio():
    """import brownfield だけでは gradio を読み込まない（lazy __getattr__）。"""
    sys.modules.pop("gradio", None)
    sys.modules.pop("brownfield", None)
    import brownfield  # noqa: F401
    assert "gradio" not in sys.modules, "lazy __getattr__ 失敗: gradio が読み込まれた"

def test_getattr_main():
    sys.modules.pop("brownfield", None)
    import brownfield
    assert callable(brownfield.main)

def test_getattr_build_ui():
    sys.modules.pop("brownfield", None)
    import brownfield
    assert callable(brownfield.build_ui)

def test_getattr_unknown_raises():
    sys.modules.pop("brownfield", None)
    import brownfield
    import pytest
    with pytest.raises(AttributeError):
        brownfield.nonexistent_attr
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `cd ~/projects/NexusCore && python3 -m pytest tests/tools/brownfield/test_imports.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'brownfield'`）

- [ ] **Step 3: `__init__.py` を実装**

`tools/brownfield/__init__.py`:
```python
"""brownfield orchestrator パッケージ。

import 時に gradio を引かないよう lazy 読み込みする。
"""
from typing import TYPE_CHECKING

__all__ = ["main", "build_ui"]

def __getattr__(name):
    if name == "main":
        from .__main__ import main
        return main
    if name == "build_ui":
        from .ui import build_ui
        return build_ui
    raise AttributeError(f"module 'brownfield' has no attribute {name!r}")

if TYPE_CHECKING:
    from .__main__ import main as main  # noqa: F401
    from .ui import build_ui as build_ui  # noqa: F401
```

- [ ] **Step 4: main/build_ui 用のダミーモジュールでテストを通す**

> `__init__.py` は `.__main__` と `.ui` に依存するが、これらは後続タスクで作成。`__getattr__` の遅延性テスト（gradio 非読込）は `test_import_brownfield_does_not_load_gradio` のみ。`test_getattr_main`/`test_getattr_build_ui` は Task 4/5 完了後に通るため、**本タスクでは `test_import_brownfield_does_not_load_gradio` と `test_getattr_unknown_raises` のみ検証**。

Run: `python3 -m pytest tests/tools/brownfield/test_imports.py::test_import_brownfield_does_not_load_gradio tests/tools/brownfield/test_imports.py::test_getattr_unknown_raises -v`
Expected: 2 PASS

> 注: `__getattr__("main")` が `.ui`（未作成）経由で gradio を引く可能性があるため、`test_import_brownfield_does_not_load_gradio` は `import brownfield` のみ（属性アクセスなし）で検証する。属性アクセス系テストは Task 6 で全件再実行する。

- [ ] **Step 5: commit**

```bash
git add tools/brownfield/__init__.py tests/tools/brownfield/test_imports.py
git commit -m "feat(brownfield): パッケージ雛形 + __init__.py lazy __getattr__"
```

---

## Task 3: `utils.py`（定数 + IO/helper + stream_run + detect_latest_snapshot + orchestrator adapter）

**Files:**
- Create: `tools/brownfield/utils.py`
- Test: `tests/tools/brownfield/test_utils.py`

- [ ] **Step 1: 失敗テストを書く**

`tests/tools/brownfield/test_utils.py`:
```python
"""utils.py の純粋関数テスト。"""
from pathlib import Path
from brownfield import utils as U

def test_repo_root_resolves_to_nexuscore_root():
    """REPO_ROOT は NexusCore 仓库根（.git があるディレクトリ）。"""
    assert (U.REPO_ROOT / ".git").exists() or (U.REPO_ROOT / "pyproject.toml").exists()
    assert U.REPO_ROOT.name == "NexusCore"

def test_package_dir_is_brownfield():
    assert U.PACKAGE_DIR.name == "brownfield"
    assert U.PACKAGE_DIR.parent.name == "tools"

def test_detect_latest_snapshot_empty(tmp_path):
    """存在しない/空ディレクトリは空文字列。"""
    assert U.detect_latest_snapshot(str(tmp_path / "noexist")) == ""
    assert U.detect_latest_snapshot(str(tmp_path)) == ""  # 空ディレクトリ

def test_detect_latest_snapshot_picks_newest(tmp_path):
    (tmp_path / "20260701_120000").mkdir()
    (tmp_path / "20260701_180000").mkdir()
    result = U.detect_latest_snapshot(str(tmp_path))
    assert result.endswith("20260701_180000")

def test_constants_values():
    assert "structure" in U.PHASE_KEYS
    assert "ai_export" in U.PHASE_KEYS
    assert "gemini-single-file" in U.DEFAULT_PROFILES
    assert U.DEFAULT_OUT == U.REPO_ROOT / "brownfield_snapshots"
    assert U.ORCHESTRATOR_MODULE_NAME == "nexuscore.core.orchestrator"
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `python3 -m pytest tests/tools/brownfield/test_utils.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'brownfield.utils'`）

- [ ] **Step 3: `utils.py` を実装（旧ファイルから転記 + 定数 REPO_ROOT 化）**

`tools/brownfield/utils.py` を作成。以下を記述:

1. **import 文**（旧ファイル L41-42 と同じ）:
```python
from __future__ import annotations
import os, sys, json, shlex, shutil, argparse, subprocess, zipfile
import threading, queue, time, traceback, importlib, importlib.util
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple, Callable, Generator, Optional, Union
```

2. **定数（旧 L48-62 を REPO_ROOT 化して転記）**:
```python
JST = timezone(timedelta(hours=9))

# 本ファイル物理位置基準。symlink/zipapp では要再考。
PACKAGE_DIR = Path(__file__).resolve().parent              # brownfield/
REPO_ROOT   = PACKAGE_DIR.parents[1]                        # brownfield -> tools -> repo root
PROJECT_TOP = REPO_ROOT
SRC_DIR     = REPO_ROOT / "src"
TOOLS_DIR   = REPO_ROOT / "tools"
ORCHESTRATOR_MODULE_NAME = "nexuscore.core.orchestrator"

PICKER_ROOT = Path(os.getenv("NEXUS_BROWNFIELD_PICKER_ROOT", str(PROJECT_TOP.parent))).resolve()
PHASE_KEYS = ["structure", "snapshot", "unified", "graphs", "history", "quality", "ai_export"]
DEFAULT_PROFILES = ["gemini-single-file", "gpt5-zip"]
DEFAULT_OUT = REPO_ROOT / "brownfield_snapshots"
```

3. **共通ヘルパー（旧 L47-128 を転記・ロジック不改）**: `now_tag`, `candidate_paths`, `phase_cmd`, `_read_json_safe`, `load_policy_meta`, `inject_policy_meta_to_manifest`, `stream_run` を旧ファイル L49-128 から**そのまま転記**。`stream_run` が `SRC_DIR`/`PROJECT_TOP` を参照することを確認（上記定数で解決）。

4. **detect_latest_snapshot（旧 L239-243 を転記）**:
```python
def detect_latest_snapshot(out_root: str) -> str:
    root = Path(out_root)
    if not root.exists(): return ""
    dirs = [p for p in root.iterdir() if p.is_dir()]
    return str(sorted(dirs, key=lambda p: p.name, reverse=True)[0]) if dirs else ""
```

5. **orchestrator adapter 関数（旧 L245-317 を転記・docstring で adapter 明記）**: `is_orchestrator_importable`（L245-253）, `run_orchestrator_cli`（L255-280）, `run_orchestrator_func`（L281-317）を旧ファイルから**そのまま転記**。各関数の直前に docstring 追記:
```python
def is_orchestrator_importable() -> bool:
    """adapter: 外部モジュル nexuscore.core.orchestrator の importability を検証。"""
    ...
```

- [ ] **Step 4: テストを実行して成功を確認**

Run: `python3 -m pytest tests/tools/brownfield/test_utils.py -v`
Expected: 5 PASS

- [ ] **Step 5: commit**

```bash
git add tools/brownfield/utils.py tests/tools/brownfield/test_utils.py
git commit -m "feat(brownfield): utils.py(定数+IO/helper+stream_run+detect_latest_snapshot+orchestrator adapter)"
```

---

## Task 4: `core.py`（`run_brownfield_stream`）+ baseline 前後比較

**Files:**
- Create: `tools/brownfield/core.py`
- Test: `tests/tools/brownfield/test_core_stream.py`

- [ ] **Step 1: 失敗テストを書く（baseline 比較）**

`tests/tools/brownfield/test_core_stream.py`:
```python
"""run_brownfield_stream の baseline 前後比較テスト（振る舞い保存の正体）。"""
import json, sys
from pathlib import Path
from typing import List, Tuple, Optional, Generator

_BASELINE = Path(__file__).parent / "_baseline_events.json"

def _fake_stream_run(cmd, cwd) -> Generator[str, None, Tuple[bool, str]]:
    """Task1 の _baseline_capture.py の fake と**完全一致**させること。"""
    yield "--- [fake] phase line 1\n"
    yield "--- [fake] phase line 2\n"
    return (True, "fake output")

def test_run_brownfield_stream_matches_baseline(tmp_path, monkeypatch):
    """新 core.run_brownfield_stream のイベント列が baseline と完全一致。"""
    from brownfield import core
    # core モジュール内の stream_run 参照を置換（core.py は 'from .utils import stream_run'）
    monkeypatch.setattr(core, "stream_run", _fake_stream_run)

    events = []
    gen = core.run_brownfield_stream(
        project_root=str(tmp_path / "proj"),
        out_root=str(tmp_path / "out"),
        profiles=["gemini-single-file"],
        selected_phases=["structure", "snapshot"],
        policy_profile_ui="", policy_version_ui="", policy_icon_ui="",
        richness_mode="Light (fast)",
        include_full_archive=False,
    )
    for ev in gen:
        events.append(list(ev))

    expected = json.loads(_BASELINE.read_text(encoding="utf-8"))
    assert events == expected, f"baseline 不一致: got {len(events)} events, expected {len(expected)}"
```

> **重要:** Task 1 Step2 で `load_policy_meta` 等の追加 mock を入れた場合、本テストでも `monkeypatch.setattr(core, "load_policy_meta", lambda *a, **k: {})` 等、**同一 mock** を適用すること。

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `python3 -m pytest tests/tools/brownfield/test_core_stream.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'brownfield.core'`）

- [ ] **Step 3: `core.py` を実装（旧 L131-233 を転記）**

`tools/brownfield/core.py`:
1. **import 文**:
```python
from __future__ import annotations
from typing import Dict, List, Tuple, Generator, Optional
from pathlib import Path

from .utils import (
    stream_run,            # ★ from .utils import（mock 境界・N1対策）
    load_policy_meta,
    inject_policy_meta_to_manifest,
    candidate_paths,
    phase_cmd,
    now_tag,
    PROJECT_TOP,
)
```

2. **`run_brownfield_stream`（旧 L131-233 をそのまま転記）**: 関数シグネチャ `def run_brownfield_stream(project_root: str, out_root: str, profiles: List[str], selected_phases: List[str], policy_profile_ui: str, policy_version_ui: str, policy_icon_ui: str, richness_mode: str, include_full_archive: bool) -> Generator[Tuple[str, str, Optional[str]], None, None]:` と本体（emit クロージャ含む `yield from emit(...)` 構造）を旧ファイル L131-233 から**ロジック不改で転記**。docstring に streaming 契約（spec 3.6）を追記:
```python
    """Brownfield スナップショットをストリーミング実行。

    Yields: (log_text: str, summary: str, zip_path: str | None)
      ※ log_text は「それまでの全行を結合した文字列」
    Returns: なし（yield のみ）
    """
```

> 転記時、`stream_run(cmd_list, cwd=PROJECT_TOP)` の呼び出しは `from .utils import` で束縛した `stream_run` を参照する（mock が効く）。

- [ ] **Step 4: テストを実行して成功（baseline 一致）を確認**

Run: `python3 -m pytest tests/tools/brownfield/test_core_stream.py -v`
Expected: PASS（イベント列が baseline JSON と完全一致）

> **もし不一致（FAIL）**: 転記漏れ・import 参照違いが原因。旧 L131-233 との diff を取り、`yield from emit` の位置・`stream_run` 呼出・`StopIteration.value` 取得が一致するか確認。ロジック変更は禁止（一致しない場合は転記ミス）。

- [ ] **Step 5: commit**

```bash
git add tools/brownfield/core.py tests/tools/brownfield/test_core_stream.py
git commit -m "feat(brownfield): core.py(run_brownfield_stream) + baseline 前後比較テスト PASS"
```

---

## Task 5: `ui.py`（Gradio UI）

**Files:**
- Create: `tools/brownfield/ui.py`
- Test: `tests/tools/brownfield/test_ui_build.py`

- [ ] **Step 1: 失敗テストを書く（launch monkeypatch・S3対策）**

`tests/tools/brownfield/test_ui_build.py`:
```python
"""build_ui 構築テスト（launch は monkeypatch で潰す・port bind なし）。"""
def test_build_ui_returns_blocks_and_launch_args(monkeypatch):
    from brownfield import ui

    captured = {}
    def fake_launch(self, *args, **kwargs):
        captured["kwargs"] = kwargs
    # gradio.Blocks.launch を潰す（実起動回避・B104 踏まない）
    import gradio
    monkeypatch.setattr(gradio.Blocks, "launch", fake_launch)

    demo = ui.build_ui()
    assert demo is not None  # gr.Blocks インスタンス
    demo.launch(prevent_thread_lock=True)
    assert captured["kwargs"].get("prevent_thread_lock") is True
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `python3 -m pytest tests/tools/brownfield/test_ui_build.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'brownfield.ui'`）

- [ ] **Step 3: `ui.py` を実装（旧 L235-238, L318-443 を転記）**

`tools/brownfield/ui.py`:
1. **import 文**（旧ファイル冒頭の標準 import のうち UI が必要なもの + 相対 import）:
```python
from __future__ import annotations
import os, shutil, zipfile, threading, time
from pathlib import Path
from typing import Optional

from .core import run_brownfield_stream
from .utils import (
    detect_latest_snapshot,
    is_orchestrator_importable,
    run_orchestrator_cli,
    run_orchestrator_func,
    PICKER_ROOT, PHASE_KEYS, DEFAULT_PROFILES, DEFAULT_OUT,
)
```

2. **`try_build_dir_picker`（旧 L235-238 を転記）**: 関数内 `from gradio import FileExplorer` は**関数内 import のまま保持**（gradio を module-level に上げない・spec m6）。

3. **`build_ui`（旧 L318-431 を転記）**: `import gradio as gr` は**関数内 import のまま**保持。旧 L318-431 の本体をロジック不改で転記。`build_ui` 内で参照する `PICKER_ROOT`, `PHASE_KEYS`, `DEFAULT_PROFILES`, `run_brownfield_stream`, `detect_latest_snapshot`, `is_orchestrator_importable`, `run_orchestrator_cli`, `run_orchestrator_func` は上記 import で解決。

4. **`auto_launch_with_increment`（旧 L432-443 を転記）**: 旧 L432-443 をそのまま転記。

- [ ] **Step 4: テストを実行して成功を確認**

Run: `python3 -m pytest tests/tools/brownfield/test_ui_build.py -v`
Expected: PASS（demo が gr.Blocks・launch の prevent_thread_lock=True を捕捉）

- [ ] **Step 5: commit**

```bash
git add tools/brownfield/ui.py tests/tools/brownfield/test_ui_build.py
git commit -m "feat(brownfield): ui.py(build_ui+auto_launch+try_build_dir_picker)"
```

---

## Task 6: `__main__.py` + shim 上書き

**Files:**
- Create: `tools/brownfield/__main__.py`
- Modify: `tools/brownfield_orchestrator.py`（旧485行 → shim に上書き）
- Test: `tests/tools/brownfield/test_shim_loader.py`

- [ ] **Step 1: 失敗テストを書く（shim + main(argv)）**

`tests/tools/brownfield/test_shim_loader.py`:
```python
"""shim 経由起動と main(argv) のテスト。"""
import sys
import pytest

def test_main_help_exits_zero(capsys):
    """main(['--help']) は SystemExit(0)。"""
    from brownfield.__main__ import main
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    assert "--ui" in capsys.readouterr().out

def test_shim_module_loads_main():
    """shim ファイル経由で main が解決できる（sys.path 注入経路）。"""
    sys.path.pop(0) if str(__import__("pathlib").Path(__file__).resolve().parents[3] / "tools") in sys.path else None
    tools_dir = str(__import__("pathlib").Path(__file__).resolve().parents[3] / "tools")
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    # brownfield.__main__ を正規 import（shim と同じ経路）
    import importlib
    mod = importlib.import_module("brownfield.__main__")
    assert callable(mod.main)
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `python3 -m pytest tests/tools/brownfield/test_shim_loader.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'brownfield.__main__'`）

- [ ] **Step 3: `__main__.py` を実装（旧 L445-485 を転記・`main(argv=None)->int` 化）**

`tools/brownfield/__main__.py`:
1. **import 文**:
```python
from __future__ import annotations
import os, argparse
from pathlib import Path
from typing import Optional

from .ui import build_ui, auto_launch_with_increment
from .core import run_brownfield_stream
from .utils import PICKER_ROOT, PHASE_KEYS, DEFAULT_PROFILES, DEFAULT_OUT, load_policy_meta
```

2. **`parse_args`（旧 L445-458 を転記）**: シグネチャを `def parse_args(argv: Optional[list] = None) -> argparse.Namespace:` に変更し、最後を `return p.parse_args(argv)` にする（それ以外は旧 L446-457 のまま）。

3. **`main`（旧 L459-481 を転記・シグネチャ変更）**:
```python
def main(argv: Optional[list] = None) -> int:
    args = parse_args(argv)
    if args.ui:
        base_port = int(os.getenv("NEXUS_BROWNFIELD_UI_PORT", "7862"))
        share = os.getenv("NEXUS_BROWNFIELD_UI_SHARE", "0") == "1"
        demo = build_ui(); auto_launch_with_increment(demo, base_port, share)
        return 0
    else:
        target = Path(args.project_root).resolve()
        if target.is_file(): target = target.parent
        out_root = Path(args.out).resolve(); out_root.mkdir(parents=True, exist_ok=True)
        profiles = [s.strip() for s in (args.profiles or "").split(",") if s.strip()] or DEFAULT_PROFILES
        skip = [s.strip() for s in (args.skip or "").split(",") if s.strip()]
        selected_phases = [p for p in PHASE_KEYS if p not in set(skip)]
        meta = load_policy_meta()
        if args.policy_profile: meta["policy_profile"] = args.policy_profile
        if args.policy_version: meta["policy_version"] = args.policy_version
        if args.policy_icon:    meta["policy_icon"] = args.policy_icon
        summary, zip_path = "", None
        gen = run_brownfield_stream(str(target), str(out_root), profiles, selected_phases,
            meta.get("policy_profile",""), meta.get("policy_version",""), meta.get("policy_icon",""),
            args.richness, args.full_archive)
        if gen:
            for _, summary, zip_path in gen: pass
        print(summary)
        if zip_path: print(f"[ZIP] {zip_path}")
        return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
```

- [ ] **Step 4: テストを実行して成功を確認**

Run: `python3 -m pytest tests/tools/brownfield/test_shim_loader.py -v`
Expected: 2 PASS

- [ ] **Step 5: shim で `tools/brownfield_orchestrator.py` を上書き**

旧485行の `tools/brownfield_orchestrator.py` を**以下の shim で完全上書き**（ファイル全体を置換）:
```python
"""後方互換エントリ。実体は tools/brownfield/ パッケージ（リファクタ v3 P1）。

起動方法（変更なし）: python tools/brownfield_orchestrator.py --ui

tools/ は __init__.py を持たないフラットなスクリプト集のため、brownfield/ パッケージを
解決するには tools/ 自身を sys.path に含める必要がある（shim ローカルで一時挿入）。
"""
import sys
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from brownfield.__main__ import main  # 正規パッケージロード（相対import解決の前提）

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: shim 経由の実起動を確認**

Run: `cd ~/projects/NexusCore && python3 tools/brownfield_orchestrator.py --help`
Expected: argparse のヘルプが表示（`--ui` を含む）・exit 0

- [ ] **Step 7: commit**

```bash
git add tools/brownfield/__main__.py tools/brownfield_orchestrator.py tests/tools/brownfield/test_shim_loader.py
git commit -m "feat(brownfield): __main__.py(main(argv)->int) + shim上書き(後方互換)"
```

---

## Task 7: 旧コード重複除去 + 全テスト + 最終検証

**Files:**
- Verify: `tools/brownfield_orchestrator.py`（shim のみ・485行のコードは削除済）

- [ ] **Step 1: shim ファイルが旧コードを含まないことを確認**

Run: `wc -l tools/brownfield_orchestrator.py`
Expected: 20行前後（shim のみ）。485行のコードは残っていない。

Run: `grep -c 'def run_brownfield_stream' tools/brownfield_orchestrator.py`
Expected: `0`（旧コードの関数定義は shim に無い）

- [ ] **Step 2: brownfield 全テストを実行**

Run: `cd ~/projects/NexusCore && python3 -m pytest tests/tools/brownfield/ -v`
Expected: 全 PASS（test_imports 4件 + test_utils 5件 + test_core_stream 1件 + test_ui_build 1件 + test_shim_loader 2件 = 13件）

- [ ] **Step 3: 既存テスト全体の回帰確認**

Run: `cd ~/projects/NexusCore && python3 -m pytest tests/ -q --ignore=tests/tools/brownfield 2>&1 | tail -5`
Expected: 既存テストが brownfield リファクタ前と同等に PASS（既存の失敗がある場合は、それが brownfield 由来でないことを確認）

- [ ] **Step 4: docs/CI 内の参照にパス変更が不要か確認**

Run: `cd ~/projects/NexusCore && rg "brownfield_orchestrator" docs/ .github/ 2>/dev/null | head`
Expected: 監査レポート等の言及のみ（`python tools/brownfield_orchestrator.py` パスは不変・追記不要）。パス変更を示唆する参照がなければ OK。

- [ ] **Step 5: baseline 一時ファイルの整理検討**

`tests/tools/brownfield/_baseline_capture.py` は baseline 取得後も再実行可能なため残置可、または `_baseline_events.json` のみ残して capture スクリプトは削除。チーム判断だが、**`_baseline_events.json` は必ず残す**（test_core_stream が依存）。

Run: `ls tests/tools/brownfield/_baseline_events.json`
Expected: 存在

- [ ] **Step 6: 最終 commit**

```bash
git add -A
git commit -m "chore(brownfield): 旧コード重複除去 + 全テスト PASS(13件) + 最終検証完了

God file分割完了: 485行→パッケージ6モジュール + shim
振る舞い保存: baseline前後比較 PASS
後方互換: python tools/brownfield_orchestrator.py --ui 動作確認"
```

---

## 完了条件（spec 成功基準との対応）

| spec 成功基準 | 検証タスク |
|---|---|
| 1. `python tools/brownfield_orchestrator.py --ui` が変更なしで動作 | Task 6 Step6（--help）+ 実機で --ui 起動確認 |
| 2. 各モジュール単独 import・依存単方向 | Task 2/3/4/5 の各テスト |
| 3. baseline 前後比較でイベント列一致 | Task 1 + Task 4（test_core_stream PASS） |
| 4. build_ui() が gr.Blocks 返し launch 引数捕捉 | Task 5（test_ui_build PASS） |

## フォローアップ（別Issue・本計画の scope 外）

- B602 subprocess shell=True 対策（stream_run の cmd 出所検証）
- B104 0.0.0.0 バインド切替機構
- brownfield 単体テスト拡充（本最小テストを土台に）
