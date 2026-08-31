# orchestrator パッケージ利用実態棚卸し（デッドコード判定）

- 日付: 2026-08-31
- 起票: 2026-08-30 W4（棚卸し）・バックログ「NexusCore orchestrator利用実態の棚卸し（デッドコード判定）」
- 目的: `src/nexuscore/orchestrator/`（835行級+テスト15ファイル）が本体フローに未統合＝デッドコードか否かを参照検索で判定し、ハーネスPhase 4/5のorchestrator統合判断に输入する
- テスト方針: 該当なし（参照検索と棚卸し報告が主体・実コード変更なし）

---

## 1. 対象の実体

| 対象 | 行数 | 備考 |
|---|---|---|
| `orchestrator/authority_runner.py` | 285 | 権限レベル別フェーズ実行(run_with_authority / resume_run) |
| `orchestrator/_authority_runner_helpers/` 計 | 538 | resume 257 / state 97 / lock_lease 72 / context 55 / __init__ 35 / phase_logging 22 |
| **上記 小計（起票「835行」の実体）** | **823** | 起票時点の概数と一致 |
| `orchestrator/run_lock.py` | 234 | 実行ロック取得/更新/stale reclaim |
| `orchestrator/run_state_integrity.py` | 134 | RunState HMAC-SHA256 署名(CR-NEXUS-026) |
| `orchestrator/run_state_store.py` | 92 | RunState JSON 永続化 |
| `orchestrator/run_state_schema_validator.py` | 37 | resume時スキーマ検証(CR-020) |
| `orchestrator/constants.py` + `explainability.py` + `__init__.py` | 53 | AuthorityLevel / 失敗理由生成 |
| **パッケージ合計** | **1373** | |
| `tests/orchestrator/` | 15ファイル / 118テスト | 111 passed / 7 skipped（後述） |

## 2. 参照マップ（全grep実測・src内+tests）

### 2.1 本体フローからの到達経路（ライブ）

```
Makefile:191 uvicorn nexuscore.api.fastapi_app:app   ← make server のエントリ
  └─ fastapi_app.py:39  app.include_router(run_view.canonical_router, prefix="/api/v1")
      └─ api/routes/run_view.py  3エンドポイント
          ├─ GET  /api/v1/runs/{run_id}        → run_state_store.load_state
          ├─ POST /api/v1/runs/{run_id}/resume → authority_runner.resume_run
          └─ POST /api/v1/runs                 → authority_runner.run_with_authority
              └─ authority_runner
                  ├─ _authority_runner_helpers/{context,lock_lease,phase_logging,resume,state}
                  │    ├─ run_lock（ロック取得/更新/stale reclaim）
                  │    └─ run_state_schema_validator（resume検証）
                  ├─ constants / explainability
                  └─ run_state_store → run_state_integrity（HMAC署名）
          └─ api/dependencies/orchestrator.py get_orchestrator
              └─ assemble_agent_team → core.orchestrator.Orchestrator
```

- authority_runner が要求する6フェーズメソッド（`run_requirements_phase` 等）は `core/phase_runner_mixin.py:205-646` に実在し、`core/orchestrator.py:67` `class Orchestrator(PhaseRunnerMixin)` で継承 → **推測インターフェースではなく実在統合**
- API側テスト: `tests/api/test_fastapi_run_view*.py` 4ファイル（2026-08-31 実測: 11 passed, 1 xfailed）

### 2.2 到達しない経路（未統合）

| 経路 | 実態 | 根拠 |
|---|---|---|
| **main_cli.py（CLI）** | authority_runner 未使用。`orchestrator.run_full_project` 直呼び + `--dynamic` は core/dynamic_orchestrator | main_cli.py に authority 系参照0件（grep実測） |
| **webapp（Flask/celery）** | 本パッケージ不使用。`webapp/orchestrator_helper.py:12` が core.Orchestrator を直接利用 | grep実測 |
| **cli/run_view.py** | `build_run_view` は API adapter からのみ使用（CLIコマンドとしては未配線） | `api/utils/run_view_adapter.py:5` のみ参照 |

### 2.3 モジュール別の外部参照有無

| モジュール | src内参照 | テスト参照 |
|---|---|---|
| authority_runner + helpers(823行) | routes/run_view.py（ライブ） | tests/orchestrator + tests/api |
| run_lock / schema_validator / integrity | パッケージ内で全て使用（外部直接参照なし） | tests/orchestrator |
| 全モジュール | **src内孤立モジュール 0件** | — |

## 3. テスト実測（2026-08-31）

```
$ python -m pytest tests/orchestrator/ -q
111 passed, 7 skipped in 2.63s   EXIT=0

$ python -m pytest tests/api/test_fastapi_run_view*.py -q
11 passed, 1 xfailed in 4.25s    EXIT=0
```

7 skipped の内訳:
- `test_main_cli_authority_level.py` 3件 — `_build_arg_parser not yet implemented in main_cli`
- `test_main_cli_authority_runner_wiring.py` 2件 — `run_cli() not yet implemented`
- `test_main_cli_dynamic_mode.py` 2件 — dynamic系skip

**⚠️ skipのうち wiring 2件は stale**: monkeypatch対象の `main_cli._load_guardian_credentials` が GuardianAgent cred集約（A'案・2026完了）で廃止済み。unskip すれば AttributeError で失敗する見込み（skipのため未発火）。

## 4. 3択判断

**判定: ① 統合維持（デッドコードではない）**

- REST API（`POST /api/v1/runs` 等3エンドポイント）経由で uvicorn 本体から完全に到達可能。RunState署名・ロック・resume・権限レベル制御という独立機能を持つ
- 依存グラフ上、孤立モジュールは0件。823行すべてがライブパスに連なる
- ハーネス Phase 4/5 の入力: **orchestrator統合先としては FastAPI run_view 経路が既存の実動作ポイント**。CLI配線は未実装の選択肢として残る（③への発展は別タスク）

| 選択肢 | 判定 | 理由 |
|---|---|---|
| ① 統合維持（現状） | **採用** | API経路がライブで111+11テスト緑。削除は実動作機能の除去 |
| ② デッドコード削除 | 却下 | 全モジュール到達可能・src内孤立0件（実測） |
| ③ 統合推進（CLI配線） | 見送り（別タスク候補） | 7つのskipテストが意図を示すが未実装。staleなmonkeypatch 2件の修正が先行条件 |

### 派生フォロー候補（本タスク範囲外・記録のみ）
1. `test_main_cli_authority_runner_wiring.py` の stale monkeypatch 修正（`_load_guardian_credentials` 廃止追従）
2. CLI（main_cli）への authority-level 配線実装（③）— ハーネス Phase 4/5 判定後に取捨

## 5. 検証宣言（a′ 4点セット）

- (a) 実行コマンド: `grep -rn "authority_runner" src --include="*.py"` / `python -m pytest tests/orchestrator/ -q` / `python -m pytest tests/api/test_fastapi_run_view*.py -q`
- (b) 生exit code: いずれも `EXIT=0`（本文中に添付）
- (c) 観測出力: 「111 passed, 7 skipped」「11 passed, 1 xfailed」+ 参照マップの行番号は実grep出力の引用
- (d) 不合格閾値: 参照0件で「デッドコード」と断定する場合、fastapi_appのrouter登録とphase_runner_mixinの実装を直接Readで確認すること（本判定は両方確認済み）。テストは1件でもfailなら判定保留
