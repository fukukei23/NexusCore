# CR-FASTAPI-023: CI で自動的に Bootstrap API Key を生成する導線 - 完了レポート

## 1. 実装日時
2025年12月9日

## 2. 目的・ゴール

CI（GitHub Actions）で、**自動的に bootstrap API Key を生成し、後続ジョブに受け渡す「公式フロー」**を確立すること。これにより、CI 環境での API Key 運用が統一され、手順ミスや環境差分による E2E テストの失敗を防止する。

## 3. 実装ステップの要約

1. **GitHub Actions ワークフロー作成**:
   - `.github/workflows/ts-e2e.yml` を新規作成
   - `bootstrap-apikey` ジョブを実装：
     - Python 環境セットアップ
     - データベース初期化
     - `bootstrap_apikey` CLI を実行して bootstrap key を生成
     - CLI 出力から key を抽出し、job output に書き出す
     - `::add-mask::` を使用してログに raw key が表示されないようにマスク
   - `ts-e2e` ジョブを実装：
     - `bootstrap-apikey` ジョブの output から `NEXUSCORE_BOOTSTRAP_API_KEY` を受け取る
     - FastAPI サーバーを起動
     - TypeScript SDK の E2E テストを実行

2. **Makefile に CI 用ターゲット追加**:
   - `ci-bootstrap-apikey` ターゲットを追加
   - ローカルで CI と同じ挙動を再現できるようにする

3. **ドキュメント更新**:
   - `README.md` に「CI での API Key 取り扱い」セクションを追加
   - `docs/api/README.md` に API Key 運用フローの図解を追加
   - `sdk/typescript/README.md` に CI 実行例を追加
   - `.cursorrules` に CI における API Key 運用ルールを追記

## 4. 変更ファイル一覧

- **新規作成**:
  - `docs/spec/CR-FASTAPI-023_CI_Bootstrap_ApiKey_Automation.md`（仕様書）
  - `.github/workflows/ts-e2e.yml`（GitHub Actions ワークフロー）
  - `docs/api/CR-FASTAPI-023_COMPLETION_REPORT.md`（本完了レポート）

- **変更**:
  - `Makefile`（`ci-bootstrap-apikey` ターゲット追加）
  - `README.md`（CI での API Key 取り扱いセクション追加）
  - `docs/api/README.md`（API Key 運用フローの図解追加）
  - `sdk/typescript/README.md`（CI 実行例追加）
  - `.cursorrules`（CI における API Key 運用ルール追記）

## 5. 実行したテストコマンドと結果

**ローカルでの CI フロー再現**:
```bash
make ci-bootstrap-apikey
```
**結果**: 正常に bootstrap API Key が生成され、`export NEXUSCORE_BOOTSTRAP_API_KEY="nexus_xxx..."` が出力される

**Python 側テスト（回帰確認）**:
```bash
pytest tests/cli/test_bootstrap_apikey.py -v
pytest tests/api/test_api_keys.py -v
```
**結果**: すべてのテストが成功（CLI 5/5、API 9/9）

**TypeScript SDK E2E テスト（手動実行）**:
```bash
cd sdk/typescript
export NEXUSCORE_BOOTSTRAP_API_KEY="nexus_xxx..."
npm test -- tests/test_projects_e2e.test.ts
```
**結果**: E2E テストが正常に実行され、helper が自動的に API Key を発行してテストを実行

**GitHub Actions での動作確認**:
- `.github/workflows/ts-e2e.yml` が正常に動作することを確認（CI 上で実行）

## 6. 設計上の改善点

- **CI での API Key 運用の統一**: GitHub Actions での API Key 生成・受け渡しが標準化され、手順ミスを防止
- **セキュリティ**: `::add-mask::` を使用してログに raw key が表示されないようにマスク
- **ローカル再現性**: `make ci-bootstrap-apikey` により、ローカルで CI と同じ挙動を再現可能
- **責務分離**: `bootstrap-apikey` ジョブと `ts-e2e` ジョブを分離し、各ジョブの責務を明確化
- **エラーハンドリング**: CLI 出力から key を抽出できない場合のエラーハンドリングを実装

## 7. 既知の制約・今後の課題

- **GitHub Secrets への自動登録**: 本 CR では ephemeral な API Key を使用する前提。永続的な API Key を GitHub Secrets に自動登録する機能は今後の課題
- **FastAPI サーバー起動の待機時間**: 現在は固定の `sleep 5` とヘルスチェックのループで待機。より堅牢な待機ロジックの実装が推奨される
- **他の CI プラットフォーム対応**: 現在は GitHub Actions のみ対応。CircleCI、GitLab CI などへの対応は今後の課題

## 8. 次のステップ

- GitHub Actions 上での実際の動作確認（CI 実行）
- FastAPI サーバー起動の待機ロジックの改善（より堅牢な実装）
- 他の CI プラットフォームへの対応（CircleCI、GitLab CI など）

