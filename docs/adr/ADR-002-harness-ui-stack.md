# ADR-002: ハーネス Web UI スタック決定

日付: 2026-09-08（Task 22実施時・plan Task 22の2026-08-30雛形を実施日で確定）
ステータス: 承認済み（plan Task 22どおりの決定 A・Phase 3チェックポイント合格承認後）

## 背景

エージェントハーネス（Phase 0-5・plan `docs/superpowers/plans/2026-08-30-nexuscore-agent-harness.md`）のPhase 4として、タスク入力・ask承認・実行モニタを提供するWeb UIが必要。成果目標は「CLI版が必須・Web UIは補助」（plan Phase 4節）。

## 候補

- **A: FastAPI + HTMX** — 既存 `api/fastapi_app.py`（`app = FastAPI()`・L110実在確認）にAPIRouterとして統合
- **B: Streamlit** — 独立アプリ・短時間で組めるが既存webapp/Flaskと別stackが増える
- **C: Gradio** — 既存 `ui/unified_gradio_ui.py` に統合・ask承認の対話フロー（select(2)的・順次1問承認）をフォームとして表現しにくい

## 決定

**A: FastAPI + HTMX**（既存FastAPIアプリの拡張として実装）

理由:
- 既存 `api/fastapi_app.py` 資産の再利用（新規サーバー起動構成を増やさない）
- ask承認UIとツール実行モニタを1画面で提供できる（HTMXの部分更新でポーリング表示が軽い）
- plan Task 23の実装雛形（`APIRouter(prefix="/harness")`）とそのまま整合

占除下: B（stack増加・Flask/FastAPI/Streamlitの3構成化）・C（対話承認フローとの不整合）

## 影響

- Task 23で `APIRouter` を `fastapi_app.py` に include する（ハーネス専用ルート・既存ルートに影響なし）
- HTMXはCDN/静的配信で足す（Python依存は増やさない）
- ファイル名はplan雛形（`2026-08-30-harness-ui-stack.md`）から本repoのADR命名規約（`ADR-001-threat-model.md` 型）に合わせ `ADR-002-harness-ui-stack.md` へ変更（実契約突合の意図的変更・変更記録方式）
