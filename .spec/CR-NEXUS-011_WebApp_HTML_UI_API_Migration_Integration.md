# CR-NEXUS-011: WebApp HTML UI の API 移行整合 & クリーンアップ

- **Status:** Draft

- **Author:** AI Codex

- **Date:** 2024-12-04

- **Related Issues / PRs:** CR-FASTAPI-001〜010A 完了後

## 1. Overview & Context

### 目的 (Why)

Flask 時代の内部 HTML UI（`nexuscore.webapp` 配下）が、旧 Flask REST API（`/api/...`）前提のままになっている箇所、もしくは「どの API を叩く想定か不明瞭な箇所」を整理し、すべて FastAPI `/api/v1/*` を前提とした UI に揃える。

併せて、「HTML UI = 人間向け画面」「FastAPI = 外部/機械向け API」という責務分離を明文化する。

### 背景 (Background)

CR-FASTAPI-001〜010A までで、REST API は FastAPI `/api/v1/*` に統一済み。Flask 側の REST エンドポイントは CR-FASTAPI-008/010 で削除済みだが、WebApp 側の HTML テンプレートや view 関数の一部は、旧 `/api/...` を前提としたまま、あるいは今どの API を想定しているか曖昧という状態の可能性がある。

**現状の問題点:**

1. **URL の不整合リスク**: HTML UI 内にハードコードされた `/api/...` 形式の URL が残っている可能性
2. **責務の不明瞭さ**: Flask WebApp が HTML レンダリングと JSON API の両方を担当している状態
3. **将来の保守性**: どの API が正か毎回コードから逆算する必要がある
4. **サイレント破壊リスク**: API の URL 変更時に UI が壊れやすい

**現状の確認結果:**

- `views_api_test.py`: `/api/v1/projects/{id}/run` をコメントで言及しているが、実際の API 呼び出しは行っていない（シミュレーションのみ）
- `views_projects.py`: 直接データベースからデータを取得して HTML を生成。API を呼び出していない
- `views_dashboard.py`: 同様に直接データベースからデータを取得
- `views_logs.py`: 直接データベースからデータを取得

**重要な発見:**

現在の WebApp HTML UI は、**FastAPI を経由せず、直接データベースからデータを取得している**。これは「HTML UI = 人間向け画面」という責務分離の観点では問題ないが、以下の点を明確化する必要がある：

1. 各画面が「どの FastAPI エンドポイントに対応するか」を docstring/コメントで明示
2. 将来 UI を FastAPI 経由に変更する場合の設計方針を明文化
3. バッジ表示など、外部公開される URL が `/api/v1/*` に統一されているか確認

### 参照 (References)

- `docs/api/FASTAPI_MIGRATION_STATUS.md` - FastAPI 移行状況
- `docs/api/CR-FASTAPI-010_COMPLETION_REPORT.md` - Flask REST API 削除完了レポート
- `docs/api/CR-FASTAPI-010A_COMPLETION_REPORT.md` - Badges パス統一完了レポート
- `src/nexuscore/webapp/views_*.py` - 対象となる WebApp ビューファイル
- `.cursorrules` - API Architecture Rules（FastAPI 必須、`/api/v1/*` プレフィックス）

## 2. Scope

### ✅ In-Scope (やること)

#### A. URL 整理と統一

- [ ] HTML テンプレート・View 関数にハードコードされている `/api/...` 形式の URL を洗い出し、`/api/v1/...` に統一
- [ ] バッジ表示（shields.io 形式）の URL が `/api/v1/projects/{id}/badge/...` になっているか確認・修正
- [ ] 「いまはどの API も叩いていないダミー UI」があれば、コメントで「将来の FastAPI エンドポイント候補」を明示

#### B. 役割コメントの追加

- [ ] 各 View 関数上部に「この画面はどの FastAPI エンドポイントを前提にしているか」を docstring/コメントで明記
  - 例: `# Uses FastAPI GET /api/v1/projects` のような形
  - 直接 DB アクセスの場合は「Direct DB access (no API call)」と明記
- [ ] 「Flask = HTML、FastAPI = JSON API」という責務分離ルールを docstring に追加

#### C. 不要 UI / 死んでいるリンクの整理

- [ ] 旧 Flask API 専用だった UI 部品で、現 FastAPI 構成では使わないものがあれば削除 or 明示的に非表示にする
- [ ] `views_api_test.py` のシミュレーション部分を、実際の FastAPI エンドポイントへのリンク・説明に更新

#### D. ドキュメント作成

- [ ] 「WebApp HTML UI が前提とする FastAPI `/api/v1/*` エンドポイント一覧」ドキュメントを作成
  - 各画面（Projects / Runs / Logs / Badges / API Test UI）の:
    - 画面ごとの目的
    - 使用する API（または「Direct DB access」）
    - 主要なボタン/リンクと遷移先 URL
- [ ] 「Flask = HTML、FastAPI = JSON API」という責務分離ルールの明文化
- [ ] 今後 UI を増やすときのルール（新画面を作る場合、必ず `/api/v1/*` を前提にする、など）

#### E. テスト調整

- [ ] `tests/webapp/` 配下のテストを、現状の HTML UI の責務に合わせて調整
- [ ] 少なくとも「主要ページが 200 で表示される」「リンクのパスが `/api/v1/...` になっている」程度はカバー

### ❌ Out-of-Scope (やらないこと)

- [ ] CSS・デザインの大幅リニューアル
- [ ] SPA 化（React / Vue などへの置き換え）
- [ ] Gradio UI や Streamlit UI の大規模改修
- [ ] 新規 API エンドポイントの追加（それは別 CR：FastAPI 側でやる）
- [ ] WebApp HTML UI の動作ロジック変更（直接 DB アクセスから FastAPI 経由への変更は将来の検討事項）

## 3. Implementation Plan

### Step 1: 現状調査と洗い出し

1. **URL パターンの検索**
   - `src/nexuscore/webapp/` 配下で `/api/` を含む文字列を検索
   - ハードコードされた URL の一覧を作成

2. **各 View 関数の分析**
   - `views_projects.py`, `views_logs.py`, `views_dashboard.py`, `views_api_test.py` を確認
   - 各画面が「どの API を使うか / 使わないか」を整理

3. **バッジ URL の確認**
   - HTML 内に埋め込まれるバッジ画像 URL（`/api/v1/projects/{id}/badge/...`）が正しいか確認

### Step 2: コメント・docstring の追加

1. **各 View 関数に docstring 追加**
   - 画面の目的
   - 使用する FastAPI エンドポイント（または「Direct DB access」）
   - 主要なリンク・ボタンの遷移先

2. **責務分離ルールの明文化**
   - `src/nexuscore/webapp/__init__.py` または各 View ファイルの先頭にコメント追加

### Step 3: URL の統一と修正

1. **ハードコード URL の修正**
   - `/api/...` → `/api/v1/...` への置換
   - バッジ URL の確認・修正

2. **`views_api_test.py` の更新**
   - シミュレーション部分を実際の FastAPI エンドポイントへの説明に更新
   - curl コマンド例を `/api/v1/*` に統一

### Step 4: ドキュメント作成

1. **エンドポイント一覧ドキュメント作成**
   - `docs/api/WEBAPP_UI_API_MAPPING.md` を作成
   - 各画面と FastAPI エンドポイントの対応関係を記載

2. **責務分離ルールドキュメント更新**
   - `docs/api/README.md` または新規ドキュメントに追加

### Step 5: テスト調整

1. **既存テストの確認**
   - `tests/webapp/` 配下のテストを実行
   - URL パスのアサーションを `/api/v1/*` に更新

2. **新規テスト追加（必要に応じて）**
   - 主要ページの 200 レスポンス確認
   - リンクのパス確認

### Step 6: 完了レポート作成

1. **変更ファイル一覧の整理**
2. **テスト結果の記録**
3. **既知の制約・注意事項の記載**

## 4. Testing Strategy

### テスト方針

- **ユニットテスト**: View 関数の docstring が正しく追加されているか確認
- **結合テスト**: 主要ページが 200 で表示されることを確認
- **回帰テスト**: 既存の HTML UI の動作が壊れていないことを確認

### 主な検証観点

- **正常系**: 各画面が正常に表示される
- **URL 整合性**: ハードコードされた URL が `/api/v1/*` になっている
- **リンク動作**: バッジ表示などの外部リンクが正しい URL を指している
- **既存機能への影響**: 直接 DB アクセスの画面が引き続き動作する

### テストコマンド

```bash
# WebApp のテスト実行
cd /home/yn441611/NexusCore
source myenv_linux/bin/activate
python -m pytest tests/webapp/ -v

# 特定の View のテスト
python -m pytest tests/webapp/test_views_projects.py -v

# URL パターンの検証（手動確認）
grep -r "/api/" src/nexuscore/webapp/ --include="*.py"
```

### 非機能要件の確認

- **パフォーマンス**: 直接 DB アクセスの画面は既存のパフォーマンスを維持
- **セキュリティ**: 認証チェック（`@require_auth`）が正しく機能していることを確認
- **保守性**: docstring が充実し、将来の開発者が理解しやすい状態になっている

