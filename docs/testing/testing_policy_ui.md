# UI Testing Policy (Flask SaaS / Gradio)

このドキュメントは、NexusCore SaaS UI に関する **UI テストポリシー** を定義します。
目的は、UI 変更に対して最小限のコストで **壊れにくい状態** を維持することです。

---

## 対象

- **Flask Webapp UI**
  - `/projects/` (Project 一覧)
  - `/projects/<id>` (Project 詳細)
  - `/logs/runs/<run_id>` (Run 詳細 / Self-Healing Metrics)
  - `/api-test/` (External API Test UI)
- 将来追加されるすべての Flask Web 画面

- **Gradio UI (NexusCore Unified UI)**
  - `src/nexuscore/ui/unified_gradio_ui.py` で定義される Gradio ベースの UI
  - タブ構成:
    - 📝 Code / Prompt
    - 🤖 AI Revision
    - 🧪 Test Runner
    - 📜 History & Diff

---

## ポリシー

### 1. UI 修正時のルール

- 既存の Flask テンプレートを変更する場合は、必ず **`tests/webapp/ui_keywords.py`** を確認すること。

- 画面上のラベルやセクション名を変更した場合：
  - 対応する `*_KEYWORDS` 内の文字列を更新する。
  - `pytest -q tests/webapp/` をローカルで実行し、テストが通ることを確認する。

### 2. 新しい画面を追加する場合のルール

新規に Flask 画面を追加する場合は、**必ず以下を行う**：

1. URL / エンドポイントを決める（例：`/new-page/`）。

2. `tests/webapp/ui_keywords.py` に対応するキーワードリストを追加する：

   ```python
   NEW_PAGE_KEYWORDS = [
       "New Page Title",
       "Key Element",
   ]
   ```

3. `tests/webapp/test_new_page_ui.py` などテストファイルを作成し、以下のパターンでスモークテストを追加する：

   ```python
   from tests.webapp.helpers import assert_page_keywords, login_user
   from tests.webapp.ui_keywords import NEW_PAGE_KEYWORDS

   def test_new_page_renders(client, app, test_user):
       with app.app_context():
           login_user(client, test_user)
           response = client.get("/new-page/")
           assert_page_keywords(response, NEW_PAGE_KEYWORDS)
   ```

4. `pytest -q tests/webapp/` を実行してテストが通ることを確認する。

### 3. 「何を保証するテストか」

UI スモークテストは「中身のビジネスロジック」ではなく、次を保証する：

- **HTTP 500 が発生しないこと**
- **ページ上に「最低限存在してほしい UI 要素（キーワード）」があること**
- **HTML の細かい構造には依存しない（レイアウト変更に強い）**

---

## 運用

- **CI（GitHub Actions）**では、すべての PR で `pytest -q tests/webapp/` を必ず実行する。
- **Seed / PoC フェーズ**では、本ポリシーをもって「UI に対する自動テストが存在する」ことを説明可能。

---

## Gradio UI (NexusCore Unified UI)

### 対象

- `src/nexuscore/ui/unified_gradio_ui.py` で定義される Gradio ベースの UI
  - タブ構成:
    - 📝 Code / Prompt
    - 🤖 AI Revision
    - 🧪 Test Runner
    - 📜 History & Diff

### ポリシー

1. **ラベル変更時のルール**

   - Gradio タブ名・主要ボタン名を変更する場合は、
     - `tests/gradio/ui_keywords_gradio.py` のキーワードを更新すること。
   - 変更後は必ず `pytest -q tests/gradio/` を実行し、スモークテストが通ることを確認する。

2. **新しいタブ・画面を追加する場合**

   - 新タブ / 新ボタンを追加する場合は、
     - `ui_keywords_gradio.py` に対応する文字列を追加し、
     - `test_unified_gradio_ui.py` か新しいテストでその存在を確認する。
   - 方針は Flask UI と同じく「インポートエラーを出さず、必須ラベルが存在するか」を見るスモークテストのみ。

3. **目的**

   - Gradio UI の構造変更・ラベル変更により、
     - コア機能は変わらないのに「必要なボタン・タブが消えた」事故を防ぐ。
   - レイアウトや細かいスタイルには依存しない。

---

## 今後の拡張

- API 応答用のスモークテストポリシー（JSONレスポンスの検証）

---

## 関連ドキュメント

- [SaaS Architecture](./saas_architecture.md) - SaaS アーキテクチャの概要
- [4.5 UI Integration Completion Report](./completion_reports/4_5_UI_INTEGRATION_COMPLETION_REPORT.md) - UI 統合の実装詳細
- [4.5 UI Smoke Tests Refactoring Completion Report](./completion_reports/4_5_UI_SMOKE_TESTS_REFACTORING_COMPLETION_REPORT.md) - スモークテストのリファクタリング詳細

## テスト実行方法

### ローカル実行

```bash
# Webapp UI スモークテスト
pytest -q tests/webapp/

# API スモークテスト
pytest -q tests/api/test_external_api_smoke.py

# Gradio UI スモークテスト
pytest -q tests/gradio/

# すべてのスモークテスト
pytest -q tests/webapp/ tests/api/test_external_api_smoke.py tests/gradio/
```

### CI での実行

GitHub Actions の CI パイプライン（`.github/workflows/ci.yml`）で、すべての PR に対して自動的に実行されます。

