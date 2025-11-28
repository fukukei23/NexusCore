# CI への正式組み込みと API スモークテスト完了レポート

## 実装日時
2025-01-XX

## 概要

既存の UI スモークテスト基盤を活用し、以下を実装しました：

1. **CI への正式組み込み**: GitHub Actions で UI スモークテストを自動実行
2. **UI テストポリシー文書の作成**: UI 変更時のルールとテスト追加方法を文書化
3. **API 側スモークテストの同パターン化**: 外部統合 API の軽量テストを追加

これにより、UI と API の両方に対して「壊れていないこと」を保証する自動テストが整備されました。

## 実装ステップ

### タスク 1: CI への正式組み込み（GitHub Actions）

#### 1-1. 既存の GitHub Actions 設定の確認

既存のワークフローを確認：
- `.github/workflows/ci.yml`: pytest を実行しているメイン CI
- `.github/workflows/nexuscore-safe-tests.yml`: 安全なテストサブセットを実行

#### 1-2. 既存ワークフローにステップ追加

**変更ファイル**: `.github/workflows/ci.yml`

**変更内容**:
- `Run tests and generate coverage report` ステップの後に、`Run webapp UI smoke tests` ステップを追加
- `pytest -q tests/webapp/` を実行して UI スモークテストを確実に実行

**変更例**:
```yaml
- name: Run tests and generate coverage report
  run: |
    python -m pytest --cov=src --cov-report=xml

- name: Run webapp UI smoke tests
  run: |
    pytest -q tests/webapp/

- name: Upload coverage to Codecov
  ...
```

**変更ファイル**: `.github/workflows/nexuscore-safe-tests.yml`

**変更内容**:
- `Run unit tests (safe subset)` ステップの後に、`Run webapp UI smoke tests` ステップを追加

**効果**:
- すべての PR で UI スモークテストが自動実行される
- UI の破壊的変更が CI で即検知される

### タスク 2: UI テストポリシー文書の作成

**新規ファイル**: `docs/testing_policy_ui.md`

**実装内容**:
- UI テストポリシーの定義
- UI 修正時のルール
- 新しい画面を追加する場合のルール
- 「何を保証するテストか」の説明
- 運用方法（CI での自動実行）
- 今後の拡張計画

**主要セクション**:

1. **対象**: Flask Webapp UI の対象ページ一覧
2. **ポリシー**:
   - UI 修正時のルール（`ui_keywords.py` の確認と更新）
   - 新しい画面を追加する場合のルール（キーワード追加、テスト作成）
   - 「何を保証するテストか」（HTTP 500 の検知、UI 要素の存在確認）
3. **運用**: CI での自動実行
4. **今後の拡張**: Gradio UI、API 応答用のスモークテスト

**効果**:
- UI 変更時のルールが明確化
- 新しい画面追加時の手順が標準化
- テストポリシーを説明可能に

### タスク 3: API 側スモークテストの同パターン化

#### 3-1. API 用ヘルパーの追加

**新規ファイル**: `tests/api/helpers_api.py`

**実装内容**:
- `assert_json_keys(obj, keys)`: JSON オブジェクトに指定されたキーがすべて含まれていることを確認

**コード例**:
```python
def assert_json_keys(obj: dict, keys: Iterable[str]) -> None:
    for k in keys:
        assert k in obj, f"Missing key in JSON response: {k}"
```

#### 3-2. API スモークテストファイルの追加

**新規ファイル**: `tests/api/test_external_api_smoke.py`

**実装内容**:
- 外部統合 API（`/api/v1/*`）の HTTP ステータスと最低限の JSON キーを検証する軽量テスト
- UI スモークテストと同様、「壊れていないこと」を保証する用途

**テストケース**:

1. **`test_get_projects_requires_api_key`**: API キーなしでプロジェクト一覧を取得すると 401 が返る
2. **`test_get_projects_with_api_key`**: 有効な API キーでプロジェクト一覧を取得できる
3. **`test_post_run_requires_api_key`**: API キーなしで Run を実行すると 401 が返る
4. **`test_post_run_with_api_key`**: 有効な API キーで Run を実行できる
5. **`test_get_latest_run_requires_api_key`**: API キーなしで最新 Run を取得すると 401 が返る
6. **`test_get_latest_run_with_api_key`**: 有効な API キーで最新 Run を取得できる
7. **`test_get_latest_run_without_runs`**: Run がない場合でも最新 Run 取得が 200 を返す

**テスト対象エンドポイント**:
- `GET /api/v1/projects`
- `POST /api/v1/projects/<id>/run`
- `GET /api/v1/projects/<id>/runs/latest`

**実装パターン**:
```python
def test_get_projects_with_api_key(client, app, test_user, test_project, test_api_key):
    with app.app_context():
        raw_token, _ = test_api_key
        headers = {"X-Api-Key": raw_token}
        resp = client.get("/api/v1/projects", headers=headers)

        assert resp.status_code == 200
        data = resp.get_json()
        assert "projects" in data
        if data["projects"]:
            project = data["projects"][0]
            assert_json_keys(project, ["id", "name"])
```

**効果**:
- API の破壊的変更が CI で即検知される
- API レスポンスの最低限の構造が保証される
- UI スモークテストと同様のパターンで保守性が向上

## 変更ファイル一覧

### 新規作成ファイル

1. **`docs/testing_policy_ui.md`**
   - UI テストポリシーの定義
   - UI 変更時のルールとテスト追加方法

2. **`tests/api/helpers_api.py`**
   - API スモークテスト共通ヘルパー
   - `assert_json_keys()` 関数

3. **`tests/api/test_external_api_smoke.py`**
   - API スモークテスト（7テスト）
   - 外部統合 API の軽量テスト

### 変更ファイル

1. **`.github/workflows/ci.yml`**
   - `Run webapp UI smoke tests` ステップを追加

2. **`.github/workflows/nexuscore-safe-tests.yml`**
   - `Run webapp UI smoke tests` ステップを追加

## 動作確認結果

### 静的解析結果
- ✅ リンターエラー: なし

### テスト実行結果

すべてのテストファイルが正常に実行され、CI での自動実行が可能な状態であることを確認しました。

**テストカバレッジ**:
- UI スモークテスト: 15テスト（既存）
- API スモークテスト: 7テスト（新規）
- **合計**: 22テスト

### 実装確認項目

- [x] CI で UI スモークテストが自動実行される
- [x] UI テストポリシー文書が作成されている
- [x] API スモークテストが実装されている
- [x] API ヘルパー関数が実装されている
- [x] すべてのテストが正常に実行される

## 設計上の改善点

### 保守性の向上
- **UI と API の統一パターン**: 同じパターンでスモークテストを実装することで、保守性が向上
- **共通ヘルパーの活用**: `assert_json_keys()` で API テストの重複を削減
- **ポリシー文書化**: UI 変更時のルールが明確化

### 将来の拡張性への配慮
- **新しい API エンドポイント追加時**: 同様のパターンでスモークテストを追加可能
- **CI への統合**: 新しいテストも自動的に CI で実行される
- **ポリシー文書の拡張**: Gradio UI、API 応答用のスモークテストポリシーを追加可能

### コード品質の向上
- **DRY 原則**: 共通ヘルパーでコードの重複を削減
- **可読性**: テストコードが簡潔になり、意図が明確
- **保守性**: UI/API 変更時の修正箇所が明確

## 既知の制約・注意事項

### 制限事項
1. **スモークテストの範囲**: ロジックの細かい分岐までは追わず、HTTP ステータスと主要 JSON キーの存在にフォーカス
2. **API キーの管理**: テスト用 API キーは `conftest.py` の `test_api_key` フィクスチャで管理

### トレードオフ
- **スモークテスト**: 機能テストではなく、「壊れていないこと」を見る軽量テスト
- **キーワードベース**: HTML/JSON の詳細構造には依存しない（フロント改修に強い）

### 移行時の注意点
- 既存の `tests/webapp/test_external_api.py` と共存（機能テスト vs スモークテスト）
- CI での実行時間を考慮し、軽量なスモークテストに留める

## 次のステップ

### 推奨されるフォローアップアクション

1. **新しい API エンドポイント追加時**: 同様のパターンでスモークテストを追加
2. **Gradio UI 用のスモークテスト**: ポリシー文書に記載された拡張計画を実装
3. **CI での実行時間最適化**: 必要に応じて並列実行やキャッシュを検討

## テスト実行方法

### ローカル実行

```bash
# Webapp UI スモークテスト
pytest -q tests/webapp/

# API スモークテスト
pytest -q tests/api/test_external_api_smoke.py

# すべてのスモークテスト
pytest -q tests/webapp/ tests/api/test_external_api_smoke.py
```

### CI での実行

GitHub Actions の CI パイプライン（`.github/workflows/ci.yml`）で、すべての PR に対して自動的に実行されます。

## 完成後の期待状態

✅ **main ブランチ向け PR で必ず UI スモークテストが走る**

すべての PR で `.github/workflows/ci.yml` と `.github/workflows/nexuscore-safe-tests.yml` の両方で UI スモークテストが実行されます。

✅ **UI の変更ポリシーとテストポリシーをドキュメントとして説明可能**

`docs/testing_policy_ui.md` に UI 変更時のルールとテスト追加方法が文書化されています。

✅ **API についても最低限の壊れ検知レイヤーが整った状態**

`tests/api/test_external_api_smoke.py` で外部統合 API の軽量テストが実装され、CI で自動実行されます。

## まとめ

CI への正式組み込みと API スモークテストの実装が完了しました。以下の機能が追加・改善されました：

1. ✅ **CI への正式組み込み**: GitHub Actions で UI スモークテストを自動実行
2. ✅ **UI テストポリシー文書の作成**: UI 変更時のルールとテスト追加方法を文書化
3. ✅ **API 側スモークテストの同パターン化**: 外部統合 API の軽量テストを追加

すべての実装は後方互換性を維持しており、既存のテストに影響を与えません。UI と API の両方に対して「壊れていないこと」を保証する自動テストが整備され、CI で継続的に検証される体制が構築されました。

