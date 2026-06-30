# brownfield_orchestrator.py God file 分割 設計（spec）

- 作成日: 2026-07-01
- 対象リポジトリ: NexusCore（`tools/brownfield_orchestrator.py`・485行・v2.13）
- 優先度: v3レビュー P1（技術債）
- 状態: 設計承認済 → 実装計画(writing-plans)へ

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
4. `build_ui()` が `launch(prevent_thread_lock=True)` で例外なく构建できること

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

### 3.2 thin shim（importlib ローダ）★致命的欠陥への対処

`from tools.brownfield.__main__ import main` は **`python tools/brownfield_orchestrator.py` 直接実行時に ImportError**（`tools/` は `__init__.py` がなくパッケージでない・cwd 依存）。これを避けるため `importlib` で物理パスからロードする。

```python
# tools/brownfield_orchestrator.py（shim）
"""後方互換エントリ。実体は tools/brownfield/__main__.py（リファクタ v3 P1）。"""
import importlib.util, sys
from pathlib import Path

if __name__ == "__main__":
    _pkg_main = Path(__file__).resolve().parent / "brownfield" / "__main__.py"
    spec = importlib.util.spec_from_file_location("brownfield.__main__", _pkg_main)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["brownfield.__main__"] = mod
    spec.loader.exec_module(mod)
    mod.main()
```

→ `sys.path` 操作なし・`tools/` のパッケージ化なしで元のコマンド文字列が完全動作。

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

### 3.5 モジュール依存方向（循環なし）

```
utils（葉: 定数 + IO/helper + stream_run + detect_latest_snapshot + orchestrator adapter）
  ↑
core（run_brownfield_stream）
  ↑
ui（build_ui, auto_launch_with_increment）→ core, runner系(utils内), utils
  ↑
__main__（parse_args, main）→ ui, core, utils
```

- `core` は `utils` のみ依存（業務コア）
- `ui` は `core`・`utils` に依存
- `__main__` はすべてに依存
- 単方向のみ・循環なし ✅

### 3.6 streaming 契約の明示（`core.py` docstring）

`run_brownfield_stream` が `yield`/`return` する status 辞書の形状を docstring で明示:

```python
def run_brownfield_stream(...) -> Generator[dict, None, Tuple[bool, str]]:
    """Brownfield スナップショットをストリーミング実行。

    Yields（進捗イベント）:
        {"summary": str, "line": str, "zip_path": str | None}
    Returns（最終結果）:
        (ok: bool, message: str)
    """
```

## 4. 検証戦略（baseline 前後比較）★致命的指摘への対処

smoke test（import + `--help`）だけでは「振る舞い保存」を保証できない。以下を最小構成で実施:

### 4.1 リファクタ前 baseline 取得
1. 現状の `tools/brownfield_orchestrator.py` で golden input を用意
2. `stream_run`（subprocess）を mock し、`run_brownfield_stream` の yield イベント列（順序含む）を記録
3. `build_ui()` を `launch(prevent_thread_lock=True)` で构建し成功を記録

### 4.2 リファクタ後の回帰比較
1. 同一 golden input + 同一 mock で `brownfield.core.run_brownfield_stream` を実行
2. yield イベント列が baseline と**完全一致**することを assert
3. `brownfield.ui.build_ui()` が同様に构建できることを assert
4. importlib shim 経由で `main()` が呼べることを assert

### 4.3 テストファイル構成
- `test_imports.py`: 各モジュールの import + lazy `__getattr__` の動作
- `test_shim_loader.py`: `tools/brownfield_orchestrator.py` 経由の `main` 起動
- `test_core_stream.py`: mock subprocess での status イベント列 assert（前後比較の正体）
- `test_ui_build.py`: `build_ui()` 実构建（`prevent_thread_lock=True`）

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

- MiniMax 弁証論レビュー1回実施。致命2件（shim import パス・振る舞い保存検証）・重要4件を検出
- 全指摘を設計に反映（shim importlib 化・HERE ずれ対処・lazy `__getattr__`・adapters 層の検討→utils 混入採用・baseline 前後比較テスト）
- sentaku L2（評価軸マトリクス）でモジュール配置(a)・検証戦略(b)を定量比較し a2/b1 を採用
