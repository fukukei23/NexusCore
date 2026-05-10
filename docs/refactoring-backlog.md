# NexusCore リファクタリングバックログ

> 最終更新: 2026-05-10
> 前提: 216ファイル評価のコードレビュー結果に基づく
> 基準: P0 = 影響大/工数小、P1 = 影響大/工数中、P2 = 影響中/工数中
> コア層品質: avg 4.08/5（104ファイル、~734KB） -- 高品質
> API/CLI層品質: avg 3.7/5（39ファイル、~330KB） -- 改善余地あり

---

## 優先度P0（すぐやる）

### P0-1. `_get_user_id_from_auth()` のDRY違反解消

- **問題**: 同一ヘルパー関数が4箇所以上に重複定義されている
- **影響**: コード修正時の整合性リスク、テスト重複
- **対象ファイル**:
  - `src/nexuscore/api/routes/runs.py`
  - `src/nexuscore/api/routes/api_keys.py`
  - `src/nexuscore/api/routes/projects.py`
  - `docs/api/CR-FASTAPI-005_COMPLETION_REPORT.md`（参照確認）
- **修正方針**:
  1. `src/nexuscore/api/dependencies/auth.py`（既存、11KB）に統合
  2. 各routeファイルから重複定義を削除し、`from nexuscore.api.dependencies.auth import get_user_id_from_auth` に置換
  3. FastAPIの `Depends()` インジェクションで統一
- **推定工数**: 1-2時間
- **テスト影響**: 既存テストのimport修正のみ

### P0-2. `server.py`（非推奨Flask）の削除または明示的な非推奨マーク

- **問題**: `src/nexuscore/api/server.py`（11.5KB、評価2/5）が非推奨のまま残存。FastAPI移行後もFlaskサーバーが残っており、新規Contributorが混乱する
- **影響**: アーキテクチャの二重化、メンテナンスコスト
- **対象ファイル**: `src/nexuscore/api/server.py`
- **修正方針（いずれかを選択）**:
  - **Option A（推奨）**: `archive/` に移動し、`fastapi_app.py` を唯一のエントリポイントにする
  - **Option B**: ファイル先頭に `DeprecationWarning` を追加し、READMEに移行ステータスを明記
- **推定工数**: 30分（Option A）、1時間（Option B）
- **前提**: `fastapi_app.py`（8KB）で全機能が代替済みであることの確認が必要

### P0-3. `dependencies/` と `deps/` の統合

- **問題**: `src/nexuscore/api/dependencies/`（auth.py）と `src/nexuscore/api/deps/`（orchestrator.py）が似た目的で並存。FastAPIの依存性注入パッケージとして混乱
- **対象ファイル**:
  - `src/nexuscore/api/dependencies/__init__.py`
  - `src/nexuscore/api/dependencies/auth.py`（11.3KB）
  - `src/nexuscore/api/deps/__init__.py`
  - `src/nexuscore/api/deps/orchestrator.py`（5.3KB）
- **修正方針**:
  1. `deps/` の内容を `dependencies/` に統合
  2. `deps/orchestrator.py` -> `dependencies/orchestrator.py`
  3. `deps/` ディレクトリを削除
  4. 全routeファイルのimportパスを更新
- **推定工数**: 1時間
- **依存**: P0-1（auth.pyの修正と競合する可能性）

---

## 優先度P1（次にやる）

### P1-1. Flask -> FastAPI移行の完了

- **問題**: `src/nexuscore/webapp/` 配下にFlask由来のviews群が残存し、FastAPI（`src/nexuscore/api/`）と混在状態
- **影響**: フレームワーク二重化によるメンテナンスコスト増大
- **対象ファイル**:
  - `src/nexuscore/webapp/views_dashboard.py`（18KB）
  - `src/nexuscore/webapp/views_projects.py`（24.3KB）
  - `src/nexuscore/webapp/views_logs.py`（15.8KB）
  - `src/nexuscore/webapp/views_api_test.py`（7.4KB）
  - `src/nexuscore/webapp/auth.py`（4.9KB）
  - `src/nexuscore/webapp/celery_app.py`（9.6KB）
- **方針決定が必要**:
  - **Option A（推奨）**: Flask viewsをFastAPI routesに段階的に移行
    - Phase 1: `views_dashboard.py` -> `api/routes/dashboard.py`
    - Phase 2: `views_projects.py` -> 統合（既存 `api/routes/projects.py` と統合）
    - Phase 3: `views_logs.py` -> `api/routes/logs.py`
    - Phase 4: webapp/ 配下のFlask固有コードを削除
  - **Option B**: FlaskをAPI専用、FastAPIをWebhook/外部API専用として並行維持
- **推定工数**: 2-3日（Option A）、0日（Option B、現状維持）
- **注意**: `webapp/models.py`（7.3KB）、`webapp/celery_app.py`（9.6KB）はFlask依存が深い可能性あり

### P1-2. `unified_gradio_ui.py` のモノリス分割

- **問題**: `src/nexuscore/ui/unified_gradio_ui.py`（31KB、評価3/5）が単一ファイルで巨大
- **影響**: 可読性低下、テスト困難、変更競合リスク
- **対象ファイル**: `src/nexuscore/ui/unified_gradio_ui.py`
- **修正方針**:
  1. UIコンポーネント単位で分割:
     - `src/nexuscore/ui/dashboard_tab.py`
     - `src/nexuscore/ui/projects_tab.py`
     - `src/nexuscore/ui/runs_tab.py`
     - `src/nexuscore/ui/logs_tab.py`
     - `src/nexuscore/ui/settings_tab.py`
     - `src/nexuscore/ui/app_factory.py`（Gradio app生成・統合）
  2. `unified_gradio_ui.py` は各タブをインポートして統合する薄いラッパーにする
- **推定工数**: 4-6時間
- **テスト影響**: UIテストのimportパス修正

### P1-3. `webapp/` 内のOrchestratorヘルパー統合

- **問題**: `orchestrator_helper.py`（3.3KB）と `orchestrator_inline.py`（2.8KB）が似た目的で並存
- **対象ファイル**:
  - `src/nexuscore/webapp/orchestrator_helper.py`
  - `src/nexuscore/webapp/orchestrator_inline.py`
- **修正方針**:
  1. 両ファイルの役割を確認（helper = 非同期委譲、inline = 同期実行？）
  2. 重複部分を統合し、単一の `orchestrator_bridge.py` にする
- **推定工数**: 2-3時間
- **依存**: P1-1（Flask移行の進行に依存）

---

## 優先度P2（余裕があれば）

### P2-1. `explainability.py` のドキュメンテーション改善

- **問題**: `src/nexuscore/orchestrator/explainability.py`（評価3/5）のドキュメンテーション不足
- **影響**: 機能理解・保守性への影響は中程度
- **対象ファイル**: `src/nexuscore/orchestrator/explainability.py`
- **修正方針**:
  1. モジュールレベルdocstring追加
  2. 各クラス・メソッドのdocstring追加（引数・戻り値・使用例）
  3. READMEまたはdocsに使用ガイド追加
- **推定工数**: 1-2時間

### P2-2. `math_ops.py` の評価見直し

- **問題**: `math_ops.py`（評価2/5）が非常にシンプルな関数群。評価基準に対してスコアが低すぎる可能性
- **修正方針**:
  1. 実際のファイル場所を特定して内容確認（コード検索で見つからず、旧パスの可能性）
  2. シンプルなユーティリティ関数群であれば、他のutilsモジュールに統合を検討
  3. もし使用されていなければ削除も検討
- **推定工数**: 30分-1時間

### P2-3. `clean_output.py` の改善

- **問題**: `src/nexuscore/utils/clean_output.py`（評価3/5）が単純な文字列処理
- **修正方針**:
  1. docstring・型ヒントの追加
  2. エッジケースのテスト追加
  3. 同モジュール内の他ユーティリティとの統合可能性を検討
- **推定工数**: 30分

### P2-4. `run_view.py` の重複整理

- **問題**: `run_view.py` が3箇所に存在:
  - `src/nexuscore/cli/run_view.py`
  - `src/nexuscore/api/utils/run_view.py`
  - `src/nexuscore/api/routes/run_view.py`
  - `src/nexuscore/api/schemas/run_view.py`
- **修正方針**:
  1. 各ファイルの役割を確認（CLI表示、APIユーティリティ、APIルート、APIスキーマ）
  2. 名前の重複による混乱を解消（役割に応じたリネーム）
  3. 共通ロジックがあれば `api/utils/` に抽出
- **推定工数**: 1-2時間

---

## 高品質ファイル（変更不要・参考モデル）

以下のファイルは評価5/5を達成しており、コードベースの品質モデルとして参照すること。

### エージェント層
- `src/nexuscore/agents/base_agent.py`
- `src/nexuscore/agents/constitutional_council_agent.py`
- `src/nexuscore/agents/guardian_agent.py`
- `src/nexuscore/agents/tester_agent.py`

### LLM/プロバイダー層
- `src/nexuscore/llm/llm_router.py`
- `src/nexuscore/llm/anthropic_provider.py`
- `src/nexuscore/llm/openai_provider.py`

### コア/インフラ層
- `src/nexuscore/core/errors.py`
- `src/nexuscore/core/job_state_machine.py`
- `src/nexuscore/core/orchestrator.py`
- `src/nexuscore/core/retry_policy.py`
- `src/nexuscore/core/retry_utils.py`
- `src/nexuscore/core/sandbox_executor.py`

### 解析/チェッカー層
- `src/nexuscore/analyzer/unified_analyzer.py`
- `src/nexuscore/diff/semantic_diff.py`
- `src/nexuscore/guard/tree_sitter_checker.py`

### 設定
- `src/nexuscore/config/unified_config.py`

---

## 工数サマリー

| 優先度 | 項目 | 推定工数 | リスク |
|--------|------|----------|--------|
| P0-1 | `_get_user_id_from_auth` DRY解消 | 1-2h | 低 |
| P0-2 | `server.py` 削除/非推奨化 | 0.5-1h | 低 |
| P0-3 | `dependencies/` と `deps/` 統合 | 1h | 低 |
| **P0合計** | | **2.5-4h** | |
| P1-1 | Flask -> FastAPI移行完了 | 2-3日 | 中 |
| P1-2 | `unified_gradio_ui.py` 分割 | 4-6h | 中 |
| P1-3 | Orchestratorヘルパー統合 | 2-3h | 低 |
| **P1合計** | | **3-4日** | |
| P2-1 | `explainability.py` doc改善 | 1-2h | 低 |
| P2-2 | `math_ops.py` 評価見直し | 0.5-1h | 低 |
| P2-3 | `clean_output.py` 改善 | 0.5h | 低 |
| P2-4 | `run_view.py` 重複整理 | 1-2h | 低 |
| **P2合計** | | **3-6h** | |
| **総計** | | **約4-5日** | |

---

## 依存関係

```
P0-1 (auth DRY) ──┐
                   ├──> P0-3 (deps統合) ──> P1-1 (Flask移行)
P0-2 (server.py) ─┘                              │
                                                  v
                                          P1-2 (Gradio分割)  ──> P1-3 (helper統合)

P2-1~P2-4 は独立実行可能（P0/P1に依存しない）
```

### 推奨実行順序

1. **Day 1午前**: P0-1 + P0-2（auth DRY解消 + server.py整理）
2. **Day 1午後**: P0-3（deps統合）
3. **Day 2-3**: P1-1（Flask移行、段階的に）
4. **Day 4午前**: P1-2（Gradio分割）
5. **Day 4午後**: P1-3 + P2項目から優先度の高いもの

---

## Flask -> FastAPI移行の方針

**推奨: 移行を完了させる（Option A）**

理由:
- `fastapi_app.py` が既に稼働しており、逆行する意味がない
- Flask views（`webapp/`）の機能は FastAPI routes（`api/routes/`）で概ね代替済み
- 二重化によるメンテナンスコストが継続的に増大
- 移行不完全による新規Contributorの混乱を防ぐ

移行ステップ:
1. 各Flask viewのエンドポイントとFastAPI routeの対応表を作成
2. 未移行のエンドポイントを特定
3. 1エンドポイントずつ移行し、テストで動作確認
4. 全エンドポイント移行後、Flask依存を削除
5. `requirements.txt` から `flask` を削除（段階的に）
