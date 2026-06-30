# brownfield_orchestrator.py God file 分割 設計（spec）

- 作成日: 2026-07-01
- 対象リポジトリ: NexusCore（`tools/brownfield_orchestrator.py`・485行・v2.13）
- 優先度: v3レビュー P1（技術債）
- 状態: 設計承認済（MiniMax第2回レビュー反映）→ 実装計画(writing-plans)へ

## 1. 目的・成功基準

### 主目的（A案）
**純粋な構造リファクタリング**。既存の動作は完全に保存し、外部API（CLIエントリ・`build_ui`）も維持する。God file（5責務混在）を責務別モジュールへ分割し、保守性・テスト容易性を向上する。

### スコープ（含める / 含めない）

| 含める（In-scope） | 含めない（Out-of-scope・フォローアップIssue化） |
|---|---|
| 構造分割（パッケージ化 + thin shim） | C: セキュリティ監査指摘の解消（B602 subprocess / B104 0.0.0.0） |
| 振る舞い保存（CLI/build_ui 後方互換） | D: 将来フェーズ追加を見据えた拡張基盤整備 |
| 最小 smoke test + baseline 前後比較テスト | 過剰な単体テスト全面追加 |

> C/D は `reserve-optimizer CRMService匿名ID化` のフォローアップ Issue #2/#3/#4 と同じ運用で別Issue化する。

### 成功基準
1. `python tools/brownfield_orchestrator.py --ui` が**変更なしで動作**すること（後方互換）
2. 各モジュールが単独 import 可能で、依存が単方向（循環なし）であること
3. baseline 前後比較テストで `run_brownfield_stream` の status イベント列が一致すること
4. `build_ui()` が `gr.Blocks` を返し、`launch(prevent_thread_lock=True)` 呼出が例外なく捕捉されること（launch 実体は mock・port bind なし・S3対策）

## 2. 現状分析

### 対象ファイルの5責務（混在）
| 行 | 責務 | 主要関数 |
|---|---|---|
| 49–129 | ユーティリティ | `now_tag`, `candidate_paths`, `phase_cmd`, `_read_json_safe`, `load_policy_meta`, `inject_policy_meta_to_manifest`, `stream_run` |
| 131–233 | Brownfield実行コア | `run_brownfield_stream`（+ 内部 `emit`） |
| 235–317 | 検出・実行切替 | `try_build_dir_picker`, `detect_latest_snapshot`, `is_orchestrator_importable`, `run_orchestrator_cli`, `run_orchestrator_func` |
| 318–444 | Gradio UI | `build_ui`, `auto_launch_with_increment` |
| 445–485 | エントリ | `parse_args`, `main` |

### top-level 定数（現状）
`JST`, `HERE`(`=__file__`), `PROJECT_TOP`, `SRC_DIR`, `TOOLS_DIR`, `ORCHESTRATOR_MODULE_NAME`, `PICKER_ROOT`(env), `PHASE_KEYS`, `DEFAULT_PROFILES`, `DEFAULT_OUT`

### 既存テスト
**brownfield 関連テストはゼロ**（`tests/tools/`, `tests/orchestrator/` に brownfield 由来なし）。これが baseline 前後比較を必須とする理由。

### 外部API参照
- CLI: `python tools/brownfield_orchestrator.py --ui`（ファイルヘッダ冒頭に使用方法として明記）
- `build_ui`: `tests/ui/test_opencodeinterpreter_webui*.py` が参照（※別物の可能性高いが、念のため公開APIとして維持）

## 3. 設計（確定案）

### 3.1 パッケージ構造
```
tools/
├── brownfield_orchestrator.py        # importlib ローダ shim（後方互換・後述3.2）
└── brownfield/                       # 新パッケージ
    ├── __init__.py                   # lazy __getattr__（main/build_ui・gradioを引かない・後述3.3）
    ├── __main__.py                   # parse_args + main（エントリ）
    ├── utils.py                      # 定数 + IO/helper + stream_run
    │                                 #   + detect_latest_snapshot
    │                                 #   + is_orchestrator_importable/run_orchestrator_cli/func（adapter・docstring明記）
    ├── core.py                       # run_brownfield_stream（業務コア・streaming契約docstring）
    └── ui.py                         # build_ui, auto_launch_with_increment
tests/tools/brownfield/
    ├── __init__.py
    ├── test_imports.py               # 各モジュールimport・lazy __getattr__
    ├── test_shim_loader.py           # importlib shim 経由 main 起動
    ├── test_core_stream.py           # mock subprocess で status イベント列 assert（baseline前後比較）
    └── test_ui_build.py              # build_ui() launch(prevent_thread_lock) で実构建
```

### 3.2 thin shim（正規パッケージ import）★致命的欠陥(S1)への対処

**S1の問題**: 当初の importlib ローダ案(`spec_from_file_location("brownfield.__main__", path)`)では、親パッケージ `brownfield` が `sys.modules` に未登録のため、`__main__.py` 内の相対import(`from .core import ...`)が `ImportError: attempted relative import with no known parent package` で**起動時に確実死**。

**解決策**: shim で `tools/` を `sys.path` に一時追加し、`brownfield` パッケージを**正規 import** する（`__init__.py` 経由でロード → `sys.modules["brownfield"]` 登録 → 相対import解決）。

```python
# tools/brownfield_orchestrator.py（shim）
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
    main()
```

> **代替起動方法（推奨・併記）**: `python -m brownfield`（要: cwd=repo root または tools/ in sys.path）。shim は `python tools/brownfield_orchestrator.py` 形式の後方互換用。両方で `main()` が呼べることを `test_shim_loader.py` で検証。

### 3.3 `__init__.py`（lazy `__getattr__`）★gradio 副作用回避

```python
# tools/brownfield/__init__.py
"""brownfield orchestrator パッケージ。import 時に gradio を引かないよう lazy 読み込み。"""
__all__ = ["main", "build_ui"]

def __getattr__(name):
    if name == "main":
        from .__main__ import main
        return main
    if name == "build_ui":
        from .ui import build_ui
        return build_ui
    raise AttributeError(f"module 'brownfield' has no attribute {name!r}")
```

→ `import brownfield` するだけでは gradio が読み込まれず、テスト・REPL で軽量。

**W6 対策（型補完）**: lazy `__getattr__` は mypy/pyright/IDE の補完が効かないため、`TYPE_CHECKING` ブロックを併記:
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .__main__ import main as main
    from .ui import build_ui as build_ui
```

### 3.4 定数の再定義（`utils.py`）★HERE ずれ対処

```python
# tools/brownfield/utils.py 顶部
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent          # brownfield/
# REPO_ROOT は本ファイル物理位置基準。symlink/zipapp では要再考。
REPO_ROOT   = PACKAGE_DIR.parents[1]                    # brownfield/ -> tools/ -> repo root
PROJECT_TOP = REPO_ROOT
SRC_DIR     = REPO_ROOT / "src"
TOOLS_DIR   = REPO_ROOT / "tools"
DEFAULT_OUT = REPO_ROOT / "brownfield_snapshots"
# ORCHESTRATOR_MODULE_NAME, PICKER_ROOT(env), PHASE_KEYS, DEFAULT_PROFILES, JST もここへ
```

> **注意**: 現状 `HERE.parents[1]` は仓库根を指すが、`utils.py` に移ると `parents[1]` は `tools/` になる。上記のように `PACKAGE_DIR.parents[1]` で仓库根を明示取得する。

**実コード grep 結果（m3 対策）**: top-level の Path 定数は `HERE`(L52) と `PICKER_ROOT`(L58) の**2つのみ**。それ以外（L142/144/199/240/334/336/396/466/468）はすべて**関数内のローカル Path**（引数由来・定数化不要）。したがって utils.py に移す定数は上記 REPO_ROOT 系 + `PICKER_ROOT` + `SRC_DIR`/`PROJECT_TOP`（`stream_run` が PYTHONPATH 構築で使用）+ `PHASE_KEYS`/`DEFAULT_PROFILES`/`DEFAULT_OUT`/`ORCHESTRATOR_MODULE_NAME`/`JST` のみ。

**実装時チェックリスト**: `rg "Path\(|__file__|os\.path\.|os\.chdir" tools/brownfield_orchestrator.py` で残存 Path 依存を確認し、top-level のみ utils.py へ吸収（関数内ローカルは触らない）。

### 3.5 モジュール依存方向（循環なし・W1修正）

```
utils（葉: 定数 + IO/helper + stream_run + detect_latest_snapshot + orchestrator adapter3関数）
  ↑                                    ↑
core（run_brownfield_stream）          |
  ↑                                    |
ui（build_ui, auto_launch_with_increment）
  ↑                                    ↑
__main__（parse_args, main）→ ui + core + utils（集約点・両方参照）
```

- `core` は `utils` のみ依存（業務コア）
- `ui` は `core`・`utils`（detect_latest_snapshot, is_orchestrator_importable, run_orchestrator_cli/func）に依存
- `__main__` は `ui`（--ui時）と `core`（CLI実行時）の**両方**を参照する集約点。循環なし・単方向 ✅

### 3.6 streaming 契約の明示（`core.py` docstring）★実コード事実（訂正版）

**実コードから抽出した正確なシグネチャ**（元specの「yield dict・return (bool,str)」は誤り）:

```python
def run_brownfield_stream(
    project_root: str, out_root: str, profiles: List[str], selected_phases: List[str],
    policy_profile_ui: str, policy_version_ui: str, policy_icon_ui: str,
    richness_mode: str, include_full_archive: bool,
) -> Generator[Tuple[str, str, Optional[str]], None, None]:
    """Brownfield スナップショットをストリーミング実行。

    Yields（進捗イベント・各タプル）:
        (log_text: str, summary: str, zip_path: str | None)
      ※ log_text は「それまでの全行を結合した文字列」（差分ではない）
    Returns: なし（return文なし・yield のみ）
    """
```

**内部構造の注意点（振る舞い保存のため保持）**:
- `emit(line, summary, zip_path)` は**クロージャ内 generator function**（log_buf に蓄積→join して yield）。本体では **`yield from emit(...)` で正しく消費**される（第3回レビューで実測・第2回の「未消費」懸念は誤りと判明）。この `yield from emit` 構造をそのまま保持する。
- `stream_run`（utils）は `Generator[str, None, Tuple[bool, str]]`（行を yield・最終 `(ok, out)` を return）。**return 値は呼出側で `StopIteration.value` から取り出す（模式B）**。subprocess 直依存・`SRC_DIR`/`PROJECT_TOP` で PYTHONPATH 構築。
- `detect_latest_snapshot(out_root: str) -> str`：最新snapshot無しは**空文字列 `""` を返す**（例外なし）。

## 4. 検証戦略（baseline 前後比較）★致命的指摘(S2/S3)への対処

smoke test（import + `--help`）だけでは「振る舞い保存」を保証できない。以下を最小構成で実施。

### 4.0 mock の patch 境界（S2対策・N1修正・決定）
- **境界は `stream_run`**。subprocess は触らない。
- **★重要: core.py の import を `from .utils import stream_run` に固定**（N1対処）。これにより `brownfield.core` モジュール内に `stream_run` 名が束縛され、`monkeypatch.setattr(brownfield.core, "stream_run", fake_stream_run)` で**確実に置換**される（utils 側ではなく core が参照する名前を置き換える）。
- **消費方式は模式B（実コード確定）**: `gen = stream_run(cmd_list, cwd=PROJECT_TOP); ... while True: yield from emit(next(gen)) except StopIteration as si: ok, out_text = si.value`。つまり **stream_run の return `(ok, out_text)` を `StopIteration.value` から取り出す**。
- したがって `fake_stream_run(cmd, cwd)` は `Generator[str, None, Tuple[bool, str]]` を返し、**必ず return する**（例: 固定行を yield し `return (True, "fake output")`）。**return 忘れは `si.value` が None になりテスト破損**。
- ファイルIO系（`load_policy_meta`, `inject_policy_meta_to_manifest`, `candidate_paths`）も `tmp_path` または mock で決定論化。
- 旧コード（単一ファイル）と新コード（分割）で**同一の fake_stream_run** を使い、yield イベント列を比較。

### 4.1 golden input（固定入力・W4対策）
`run_brownfield_stream` を以下の固定引数で呼ぶ:
```python
project_root = str(tmp_path / "proj")          # 一時ディレクトリ
out_root     = str(tmp_path / "out")
profiles     = ["gemini-single-file"]           # DEFAULT_PROFILES の部分集合
selected_phases = ["structure", "snapshot"]     # PHASE_KEYS の部分集合
policy_profile_ui = policy_version_ui = policy_icon_ui = ""
richness_mode = "Light (fast)"
include_full_archive = False
```
（※ `PHASE_KEYS` / `DEFAULT_PROFILES` の実値は Appendix 参照）

### 4.2 baseline 取得手順（m1対策・順序厳守）
**リファクタ前** に以下を実施しイベント列を記録（旧485行ファイルに対して）:
1. `tests/tools/brownfield/_baseline_helper.py`（一時）: 旧ファイルから `run_brownfield_stream` を import し、4.1 の golden input + 4.0 の fake_stream_run で実行、yield タプル列（`[(log_text, summary, zip_path), ...]`）を JSON 保存
2. この JSON が「正解（baseline）」

### 4.3 リファクタ後の回帰比較
1. 新 `brownfield.core.run_brownfield_stream` を同一 golden input + fake で実行
2. yield タプル列が baseline JSON と**完全一致**することを assert（`test_core_stream.py`）
3. `detect_latest_snapshot` の3ケース（空ディレクトリ→`""`・存在しない→`""`・複数候補→最新）を assert

### 4.4 `build_ui()` テスト（S3対策・launch を潰す）
**B104（0.0.0.0 bind）を踏まない**ため、実際に `launch` しない:
```python
def test_build_ui(monkeypatch):
    import brownfield.ui as ui
    captured = {}
    def fake_launch(self, *a, **kw):
        captured["kw"] = kw
    monkeypatch.setattr("gradio.Blocks.launch", fake_launch, raise=False)
    demo = ui.build_ui()
    assert demo is not None              # gr.Blocks インスタンス
    demo.launch(prevent_thread_lock=True)
    assert captured["kw"].get("prevent_thread_lock") is True
```
→ port bind なし・B104 再現なし・成功基準4（构建可能+prevent_thread_lock 引数）を検証。

### 4.5 `main()` シグネチャと argv 注入（W2/m5対策）
`main(argv: list[str] | None = None) -> int` に拡張:
- `parse_args(argv)` を呼ぶ（`argparse.parse_args(argv)`）
- テストから `main(["--ui"])` で sys.argv 非依存
- `sys.exit(main())` の責務は main 内（戻り `int`）。shim は `from brownfield.__main__ import main; main()`（sys.exit は main 内）

### 4.6 テストファイル構成
- `test_imports.py`: 各モジュール import + lazy `__getattr__` 動作（`import brownfield` で gradio 非読込を確認）
- `test_shim_loader.py`: shim 経由 `main(["--help"])` 起動。test 骨格:
```python
def test_shim_help(monkeypatch, capsys):
    import brownfield.__main__ as m
    with pytest.raises(SystemExit) as exc:
        m.main(["--help"])
    assert exc.value.code == 0
    assert "--ui" in capsys.readouterr().out
```
  + `python -m brownfield` 等価確認（`runpy.run_module("brownfield", run_name="__main__")` で SystemExit を捕捉）
- `test_core_stream.py`: 4.1-4.3（mock でのイベント列前後比較・detect_latest_snapshot 3ケース）
- `test_ui_build.py`: 4.4（build_ui 構築 + launch 引数 assert）

### 4.7 pytest 設定（m8対策）
- 既存 `pyproject.toml` の `[tool.pytest.ini_options]` `testpaths=["tests"]`・`pytest.ini` の `pythonpath`（repo root）を確認済み → `tests/tools/brownfield/` を作れば**自動収集**・新規 conftest 不要（`tests/conftest.py` の sys.modules 隔離が継承）
- CIで走ることを `pytest tests/tools/brownfield/` で実確認

## 5. リスクと緩和

| リスク | 重大度 | 緩和策 |
|---|---|---|
| shim importlib ローダのパス解決ミス | 高 | `test_shim_loader.py` で実起動検証 |
| 定数 HERE/REPO_ROOT のずれ | 高 | 3.4 の明示再定義 + テスト |
| gradio バージョン互換（v3→v4） | 中 | `build_ui()` 実构建テストで捕捉 |
| streaming 契約の暗黙変更 | 中 | docstring 明示 + 前後比較テスト |
| `import brownfield` で gradio 読み込み | 低 | lazy `__getattr__`（3.3） |

## 6. フォローアップ（別Issue化）

- **Issue: B602 subprocess shell=True 対策** — `stream_run` の `cmd` 出所検証を含めた別タスク（C案）
- **Issue: B104 0.0.0.0 バインド切替機構** — デバッグ用 host の切替（C案）
- **Issue: brownfield テストカバレッジ拡充** — 本リファクタ後の最小テストを土台に単体テスト追加（B案の拡張）

## 7. レビュー経緯（doubt-driven）

### 第1回 MiniMax 弁証論レビュー
- 致命2件（shim import パス・振る舞い保存検証）・重要4件を検出
- 反映: HERE ずれ対処・lazy `__getattr__`・adapters 層の検討→utils 混入(a2)採用・baseline 前後比較テスト(b1)
- sentaku L2 でモジュール配置(a)・検証戦略(b)を定量比較し a2/b1 を採用

### 第2回 MiniMax 弁証論レビュー（spec完成稿）
- 致命3件（**S1**: shim相対import確実死・**S2**: シグネチャ未定義・**S3**: launch testがB104再現）+ 未決定17項目を検出
- **S1修正**: importlib ローダ廃止 → sys.path 一時挿入 + `brownfield` 正規import（3.2）
- **S2修正**: `run_brownfield_stream` シグネチャ実測・mock 境界=`stream_run`・golden input 具体化（3.6・4.0-4.1）
- **S3修正**: `launch` を monkeypatch で潰し port bind なし（4.4）
- 実コードから抽出: streaming契約訂正（yieldのみ・returnなし）・CLI引数10個・定数具体値・Path依存grep・pytest設定（Appendix）
- W1/W2/W3/W6/W7/m1/m3/m4/m5/m8 を各セクションに反映

### 第3回 MiniMax 弁証論レビュー（spec 補強稿）
- 第2回17項のうち **13完全解決・2部分解決**（S2 mock対象・W13 強化）を指摘・第3回評価 6.5/10
- **N1修正（致命）**: mock 対象の矛盾解消 → core.py の `from .utils import stream_run` import を固定・`monkeypatch.setattr(brownfield.core, "stream_run", ...)` で確実置換（4.0）
- **模式B固定（致命）**: stream_run の return `(ok, out_text)` を `StopIteration.value` で消費（実コード確定）。fake は必ず return（4.0・3.6）
- **emit 訂正**: 「未消費」懸念は誤り（`yield from emit(...)` で正しく消費）→ Known Limitation ではなく正常構造として保持に訂正（3.6）
- **P1**: shim test 骨格（`pytest.raises(SystemExit)`）追記（4.6）
- 第3回残り4項（P0×2 + P1×2）すべて解決 → **writing-plans 移行可（8.5/10）**

## 8. Appendix（実コード抽出・実装時参照）

### A. CLI引数完全リスト（`parse_args`・成功基準1の判定基準）
| 引数 | 型 | デフォルト | 備考 |
|---|---|---|---|
| `--project-root` | str | `str(PICKER_ROOT)` | 解析対象ルート（CLI時） |
| `--out` | str | `str(DEFAULT_OUT)` | スナップショット出力先（親） |
| `--profiles` | str(CSV) | `",".join(DEFAULT_PROFILES)` | AIエクスポートプロフィール |
| `--skip` | str(CSV) | `""` | スキップフェーズ |
| `--policy-profile` | str | `""` | manifest注入用 |
| `--policy-version` | str | `""` | manifest注入用 |
| `--policy-icon` | str | `""` | manifest注入用 |
| `--richness` | str | `"Light (fast)"` | choices: `Light (fast)` / `Code-Rich (more .py)` |
| `--full-archive` | flag | False | ソース全体ZIP同梱 |
| `--ui` | flag | False | Gradio UI 起動 |

> これら引数が**1つでも欠損/変更されたら成功基準1違反**。

### B. 定数具体値（utils.py へ移動）
```python
PHASE_KEYS  = ["structure", "snapshot", "unified", "graphs", "history", "quality", "ai_export"]
DEFAULT_PROFILES = ["gemini-single-file", "gpt5-zip"]
DEFAULT_OUT = REPO_ROOT / "brownfield_snapshots"
ORCHESTRATOR_MODULE_NAME = "nexuscore.core.orchestrator"
PICKER_ROOT = Path(os.getenv("NEXUS_BROWNFIELD_PICKER_ROOT", str(REPO_ROOT.parent))).resolve()
JST = timezone(timedelta(hours=9))
# UI起動関連(main内で参照)
#   NEXUS_BROWNFIELD_UI_PORT (default "7862"), NEXUS_BROWNFIELD_UI_SHARE (default "0")
```

### C. 旧ファイル削除手順（W3対策）
1. 新パッケージ `tools/brownfield/`（6ファイル）を新規作成
2. `tools/brownfield_orchestrator.py`（旧485行）を 3.2 の shim 内容で**上書き**（git は置換として追跡・`git mv` ではなく上書きで履歴保持）
3. 旧ファイルの `if __name__ == "__main__": main()` エントリは shim に集約（shim 側で `main()` 呼出）
4. `python tools/brownfield_orchestrator.py --ui` と `python tools/brownfield_orchestrator.py --help` の実行確認（コミット前）
5. docs/CI スクリプト内の `brownfield_orchestrator.py` 参照を grep 確認（`rg "brownfield_orchestrator" docs/ .github/`）→ パス変更なければ追記不要

### D. utils.py 行数監視（W7対策）
- 想定: 定数 + IO/helper + stream_run + detect_latest_snapshot + orchestrator adapter3関数 ≈ **150-250行**
- soft limit **300行**。超える場合は `adapters/orchestrator.py` に orchestrator 関数3つを切り出し（将来の先行事例）
- 判断は硬直化させず、実装時に実測して決定
