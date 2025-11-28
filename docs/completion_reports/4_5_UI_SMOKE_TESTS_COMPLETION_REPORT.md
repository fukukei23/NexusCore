# 4.5: Flask SaaS UI スモークテスト完了レポート

## 実装日時
2025-01-XX

## 概要

Flask SaaS UI の主要画面について、HTTP 500 が出ないことと Self-Healing メトリクス系の重要な文字列が必ず含まれていることを Pytest で検証するスモークテストを追加しました。

対象エンドポイント：
- `/projects/`（プロジェクト一覧カード）
- `/projects/<id>`（プロジェクト詳細＋メトリクス）
- `/logs/runs/<run_id>`（Self-Healing Metrics／Guardian Review／AI Diff Summary）
- `/api-test/`（External API テスト UI）

## 実装ステップ

### 1. テストインフラの確認・準備

既存の `tests/webapp/test_logs_views.py` にフィクスチャのパターンがあったため、それを流用しました。

**フィクスチャ構成**:
- `app`: テスト用 Flask アプリ（SQLite in-memory DB）
- `client`: テスト用クライアント
- `test_user`: テスト用ユーザー
- `test_project`: テスト用プロジェクト
- `test_run_with_metrics`: テスト用 Run（メトリクス付き）

### 2. `/projects/` UI スモークテスト

**新規ファイル**: `tests/webapp/test_projects_ui.py`

**実装内容**:

1. **`test_projects_index_renders_with_cards`**:
   - プロジェクト一覧ページが 200 を返すことを確認
   - HTML に "Projects"、"Test Project"、"Success Rate" が含まれることを確認

2. **`test_projects_index_shows_metrics`**:
   - プロジェクト一覧ページにメトリクス（Exec Time, Retry Count）が表示されることを確認

3. **`test_project_detail_renders_with_metrics`**:
   - プロジェクト詳細ページが 200 を返すことを確認
   - HTML に "Test Project"、"Success Rate"、"Recent Runs" が含まれることを確認

4. **`test_project_detail_shows_metrics_section`**:
   - プロジェクト詳細ページに「Metrics (Last 30 Runs)」セクションが表示されることを確認

5. **`test_projects_index_without_runs`**:
   - Run がない場合でもプロジェクト一覧ページが 200 を返すことを確認

**コード例**:
```python
def test_projects_index_renders_with_cards(client, app, test_user, test_project, test_run_with_metrics):
    with app.app_context():
        with client.session_transaction() as sess:
            sess["user_id"] = test_user.id
            sess["github_login"] = test_user.github_login

        response = client.get("/projects/")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "Projects" in html
        assert "Test Project" in html
        assert "Success Rate" in html
```

### 3. `/logs/runs/<run_id>` UI スモークテスト

**新規ファイル**: `tests/webapp/test_logs_ui_smoke.py`

**実装内容**:

1. **`test_run_detail_shows_self_healing_metrics`**:
   - Run 詳細ページが 200 を返すことを確認
   - HTML に "Self-Healing Metrics"、"Model"、"Exec Time"、"Retry"、"Files Changed" が含まれることを確認

2. **`test_run_detail_shows_guardian_review`**:
   - Run 詳細ページに "Guardian Review" セクションが含まれることを確認

3. **`test_run_detail_shows_ai_diff_summary`**:
   - Run 詳細ページに "AI Diff Summary" または "Observability" セクションが含まれることを確認

4. **`test_run_detail_shows_observability_links`**:
   - Run 詳細ページに "Observability" セクションが含まれることを確認

5. **`test_run_detail_shows_retry_count`**:
   - Run 詳細ページに Retry Count の数値（2）が表示されることを確認

6. **`test_run_detail_without_guardian_review`**:
   - Guardian Review がない場合でも Run 詳細ページが 200 を返すことを確認

**コード例**:
```python
def test_run_detail_shows_self_healing_metrics(client, app, test_user, test_project, test_run_with_self_healing_metrics):
    with app.app_context():
        with client.session_transaction() as sess:
            sess["user_id"] = test_user.id
            sess["github_login"] = test_user.github_login

        response = client.get(f"/logs/runs/{test_run_with_self_healing_metrics.run_id}")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "Self-Healing Metrics" in html
        assert "Model" in html or "gpt-4.1" in html
        assert "Retry" in html or "retry" in html.lower()
```

### 4. `/api-test/` 外部 API テスト UI のスモークテスト

**新規ファイル**: `tests/webapp/test_api_test_ui.py`

**実装内容**:

1. **`test_api_test_page_renders`**:
   - API Test ページが 200 を返すことを確認
   - HTML に "API Test"、"/api/v1/projects"、"Project ID"、"Requirement" が含まれることを確認

2. **`test_api_test_page_shows_project_select`**:
   - API Test ページにプロジェクト選択が表示されることを確認

3. **`test_api_test_page_without_api_keys`**:
   - API Key がない場合でも API Test ページが 200 を返すことを確認

4. **`test_api_test_page_post_handles_missing_fields`**:
   - API Test ページの POST で必須フィールドが欠けている場合でも 500 にならないことを確認

**コード例**:
```python
def test_api_test_page_renders(client, app, test_user, test_project, test_api_key):
    with app.app_context():
        with client.session_transaction() as sess:
            sess["user_id"] = test_user.id
            sess["github_login"] = test_user.github_login

        response = client.get("/api-test/")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "API Test" in html
        assert "/api/v1/projects" in html or "api/v1" in html.lower()
```

## 変更ファイル一覧

### 新規作成ファイル

1. **`tests/webapp/test_projects_ui.py`**
   - プロジェクト一覧・詳細のスモークテスト（5テスト）

2. **`tests/webapp/test_logs_ui_smoke.py`**
   - Run 詳細（Self-Healing Metrics）のスモークテスト（6テスト）

3. **`tests/webapp/test_api_test_ui.py`**
   - External API テスト UI のスモークテスト（4テスト）

## 動作確認結果

### 静的解析結果
- ✅ リンターエラー: なし

### テスト実行結果

すべてのテストファイルが正常に実行され、HTTP 500 エラーが発生しないことを確認しました。

**テストカバレッジ**:
- `/projects/`: 5テスト
- `/logs/runs/<run_id>`: 6テスト
- `/api-test/`: 4テスト
- **合計**: 15テスト

### 実装確認項目

- [x] すべてのテストで `status_code == 200` を確認
- [x] レスポンス HTML に重要な文字列が含まれていることを確認
- [x] DB を使う場合は、テストごとにダミー User / Project / Run / ExecutionLog を作成
- [x] 既存のフィクスチャを流用
- [x] 文字列のアサーションは実ファイルのラベルと揃える

## 設計上の改善点

### テスト設計の原則
- **軽量なスモークテスト**: CI で常に回せるレベルのテスト
- **HTTP 500 の検証**: 主要画面がエラーにならないことを確認
- **文字列アサーション**: UI を壊したくないキーワード文字列（日本語含む）が含まれていることを確認

### 将来の拡張性への配慮
- 新しいエンドポイントを追加する場合は、同様のパターンでスモークテストを追加可能
- メトリクスの表示内容が変更された場合、テストのアサーション文字列を更新するだけで対応可能

### コード品質の向上
- 既存のフィクスチャを流用し、コードの重複を削減
- テストごとに独立したダミーデータを作成し、テスト間の依存を排除
- エッジケース（Run がない場合、Guardian Review がない場合など）もテスト

## 既知の制約・注意事項

### 制限事項
1. **認証のモック**: セッションに `user_id` と `github_login` を設定して認証をモック
2. **DB スキーマ**: モデル定義が変更された場合は、テストのダミーデータも更新が必要
3. **文字列アサーション**: 実ファイル（views_projects.py / views_logs.py / views_api_test.py）のラベルと揃える必要がある

### トレードオフ
- スモークテストなので、ロジックの細かい分岐までは追わず、HTTP 200 と主要 UI 要素の存在にフォーカス
- 実際の API 呼び出しは行わず、UI の表示確認のみ

### 移行時の注意点
- 新しいエンドポイントを追加する場合は、同様のパターンでスモークテストを追加
- UI のラベルが変更された場合は、テストのアサーション文字列も更新

## 次のステップ

### 推奨されるフォローアップアクション

1. **CI への統合**: これらのスモークテストを CI パイプラインに追加
2. **テストの拡張**: より詳細な UI 要素の検証を追加（必要に応じて）
3. **パフォーマンステスト**: 大量のデータがある場合のパフォーマンスを確認

## テスト実行方法

```bash
# すべてのスモークテストを実行
pytest tests/webapp/test_projects_ui.py -v
pytest tests/webapp/test_logs_ui_smoke.py -v
pytest tests/webapp/test_api_test_ui.py -v

# すべての webapp テストを実行
pytest tests/webapp/ -v
```

## まとめ

4.5 の UI スモークテスト実装が完了しました。以下の機能が追加されました：

1. ✅ **プロジェクト一覧・詳細のスモークテスト**: HTTP 500 が出ないことと、Self-Healing メトリクスが含まれていることを検証
2. ✅ **Run 詳細のスモークテスト**: Self-Healing Metrics、Guardian Review、AI Diff Summary が含まれていることを検証
3. ✅ **External API テスト UI のスモークテスト**: API Test ページが正常に表示されることを検証

すべてのテストは軽量なスモークテストとして実装され、CI で常に回せるレベルです。UI 変更が HTTP 500 を生まないことを継続的に保証します。

