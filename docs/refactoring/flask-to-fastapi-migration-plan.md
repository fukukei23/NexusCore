# P1-1: Flask Views → FastAPI 移行計画

> ステータス: 計画済み（Phase 1 未着手）
> 作成日: 2026-05-10
> SSOT詳細: `obsidian-ssot/01_DECISIONS/NexusCore/2026-05-10_flask-to-fastapi-migration.md`

## 概要

Flask webapp/views_*.py（4ファイル / 1,959行 / 10エンドポイント）をFastAPIに移行する。
インラインHTML文字列が views 内に約400行混在しており、可読性・保守性が著しく低下している。

## 現状分析

### Flask Views

| ファイル | 行数 | エンドポイント | HTML行数(推定) |
|---|---|---|---|
| views_projects.py | 716 | 4 | ~400 |
| views_dashboard.py | 599 | 3 | ~350 |
| views_logs.py | 442 | 2 | ~200 |
| views_api_test.py | 202 | 1 | ~100 |
| **合計** | **1,959** | **10** | **~1,050** |

### 既存FastAPI

`src/nexuscore/api/` に既に9ルーターモジュールが存在。
認証（`dependencies/auth.py`）・スキーマ（`schemas/`）・エラー処理（`utils/errors.py`）は整備済み。

### Flask依存機能

| 機能 | 使用箇所 |
|---|---|
| Blueprint | 4ファイル |
| `@require_auth` | 全10エンドポイント |
| `request.form` | views_projects（create）、views_api_test |
| `flash()` / `get_flashed_messages` | views_projects（create成功/失敗） |
| `redirect()` / `url_for()` | views_projects（POST後リダイレクト） |
| `jsonify()` | views_api_test |
| `db.session` (Flask-SQLAlchemy) | 全ファイル |
| `render_template_string` 相当 | 全ファイル（インラインHTML文字列） |

## 移行Phase

### Phase 1: インラインHTML → Jinja2テンプレート分離（4-5h）

**目標**: FlaskのままHTMLを外部ファイル化し、ロジックとテンプレートを分離。

| 作業 | 詳細 |
|---|---|
| テンプレートディレクトリ作成 | `webapp/templates/` を新設 |
| HTML抽出 | views 内のインラインHTML文字列を個別 `.html` ファイルに抽出 |
| ヘルパー関数のテンプレート化 | `_render_run_status_badge` → Jinja2 macro |
| `render_template` に切替 | `html = f"..."; return html` → `return render_template("xxx.html", ...)` |
| テスト通過確認 | 既存2,080行テストが全て通ること |

**完了条件**: Flask動作のまま、HTMLがテンプレートファイルに分離済み

### Phase 2: Flask → FastAPI ルーター移行（6-8h）

**前提**: Phase 1完了後

| 移行元 | 移行先 |
|---|---|
| views_projects.py | `api/routes/ui/projects.py`（新設） |
| views_dashboard.py | `api/routes/ui/dashboard.py`（新設） |
| views_logs.py | `api/routes/ui/logs.py`（新設） |
| views_api_test.py | `api/routes/ui/api_test.py`（新設） |

新規ディレクトリ:
```
api/routes/ui/
├── __init__.py
├── projects.py
├── dashboard.py
├── logs.py
└── api_test.py

api/templates/          ← Phase 1のテンプレートを移動
├── projects/
├── dashboard/
├── logs/
└── api_test/
```

### Phase 3: 認証・DB依存のFastAPI化（2-3h）

| Flask依存 | FastAPI代替 |
|---|---|
| `@require_auth` | `Depends(get_current_user)` |
| `db.session` | `Depends(get_db)` |
| `flash()` | cookie-based or クエリパラメータ |
| `url_for()` | `request.url_for()` or ハードコード |
| `request.form` | `Form(...)` パラメータ |

### Phase 4: Flask依存除去・テスト更新（2-3h）

- `server.py` から webapp Blueprint 登録を除去
- テスト2,080行を FastAPI TestClient ベースに書き換え
- Flask関連パッケージの requirements.txt 除去を検討

## 工数見積もり

| Phase | 工数 | 依存 |
|---|---|---|
| Phase 1: HTML分離 | 4-5h | なし |
| Phase 2: ルーター移行 | 6-8h | Phase 1 |
| Phase 3: 認証・DB | 2-3h | Phase 2（同時進行可） |
| Phase 4: Flask除去 | 2-3h | Phase 2-3 |
| **合計** | **14-19h** | |

## リスク

| リスク | 影響 | 対策 |
|---|---|---|
| インラインHTMLの行数が多い | Phase 1の工数増 | 段階的に1ファイルずつ |
| flash()の代替手段が限定的 | UX低下 | cookie-basedで同等機能を実装 |
| DB操作の非同期化 | 全エンドポイント | 同期エンジンで開始、後から非同期化 |
| Celery同期呼び出し | 実行トリガー | FastAPIでも同期Celery呼び出し可能 |

## 推奨実行戦略

Phase 1だけを先に実行（4-5h）。完了時点で評価し、Phase 2以降に進むか判断する。
Phase 1だけでも可読性が劇的に改善する。

## テンプレート一覧（Phase 1で作成）

| テンプレート | 元ファイル | 内容 |
|---|---|---|
| projects/list.html | views_projects.py `_render_project_list` | プロジェクト一覧 |
| projects/detail.html | views_projects.py `_render_project_detail` | プロジェクト詳細+Run一覧 |
| projects/new.html | views_projects.py `_render_new_project_form` | 新規プロジェクト作成フォーム |
| dashboard/index.html | views_dashboard.py | ダッシュボード |
| dashboard/project.html | views_dashboard.py | プロジェクトダッシュボード |
| dashboard/gradio.html | views_dashboard.py | Gradio UI iframe |
| logs/project.html | views_logs.py | プロジェクトログ一覧 |
| logs/run.html | views_logs.py | Run詳細ログ |
| api_test/index.html | views_api_test.py | APIテストUI |
| components/run_table.html | views_projects.py `render_run_table` | 共通Run一覧テーブル |
| components/status_badge.html | views_projects.py `_render_run_status_badge` | ステータスバッジmacro |
