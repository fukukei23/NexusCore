# NexusCore リファクタリングバックログ v2

> 最終更新: 2026-05-10
> 前提: v1バックログ（P0×3 + P1×3 + P2×4 = 10項目）は完了済み
> 対象: src/nexuscore/ 配下（~32,000行）、tests/（~96,000行）

---

## 優先度P0（セキュリティ・安定性、すぐやる）

### P0-1. ハードコード値の設定化
- **対象**: `core/sandbox_executor.py`（メモリ上限512MB、CPU 30秒等）、LLMプロバイダーのダミーキー
- **問題**: セキュリティ・リソース設定がハードコード、テスト用ダミーキー残存
- **工数**: 2-3時間
- **修正**: 環境変数 or unified_config に集約、ダミーキー除去

### P0-2. 汎用Exceptionキャッチの修正
- **対象**: `npe/budget.py`（USAGE_LEDGER書き込み）、`llm/providers/*.py`（API呼び出し）
- **問題**: `except Exception: pass` でエラー詳細が失われる
- **工数**: 4-6時間
- **修正**: 具体的例外型のキャッチ、logger.error 追加

### P0-3. self_healing_service.py の分割
- **対象**: `services/self_healing_service.py`（1,006行）
- **問題**: 単一クラスにGit操作・テスト実行・パッチ生成が混在
- **工数**: 8-12時間
- **修正**: GitHubIntegrationService / TestExecutionService / PatchGenerationService / SelfHealingOrchestrator に分割

### P0-4. API入力検証の強化
- **対象**: `api/routes/projects.py`（repo_url/local_path検証不足）
- **問題**: パストラバーサル防止なし、URL有効性チェックなし
- **工数**: 3-4時間
- **修正**: Pydantic validator 追加、パス正規化

**P0合計**: 17-25時間（約3-4日）

---

## 優先度P1（UX・アーキテクチャ、次にやる）

### P1-1. CLI/エラーメッセージの改善
- **対象**: `main_cli.py`、各API route
- **問題**: 技術的エラーがそのまま表示、解決策の提示なし
- **工数**: 4-6時間
- **修正**: エラー分類（VALIDATION/AUTH/DB等）、ユーザーアクション可能なエラーに解決策提示

### P1-2. authority_runner.py の分割
- **対象**: `orchestrator/authority_runner.py`（846行）
- **問題**: 権限制御・実行制御・ロック管理が混在
- **工数**: 10-14時間
- **修正**: AuthorityValidator / ExecutionController / LockManager に分割

### P1-3. LLMプロバイダーのリトライロジック共通化
- **対象**: `llm/providers/openai_provider.py`, `anthropic_provider.py`, `gemini_provider.py`
- **問題**: 同じリトライロジックが各プロバイダーに重複
- **工数**: 6-8時間
- **修正**: BaseRetryableLLM 基底クラス化、LLMResponseParser 共通化

### P1-4. github_pr_comment.py の分割
- **対象**: `integration/github_pr_comment.py`（867行）
- **問題**: コメント生成の責務が過度に複雑
- **工数**: 6-8時間
- **修正**: CommentBuilder（テンプレート） / MarkdownFormatter / ContextEnricher に分割

### P1-5. GuardianAgent の責務分離
- **対象**: `agents/guardian_agent.py`
- **問題**: レビュー実行とGit操作が混在
- **工数**: 6-8時間
- **修正**: CodeReviewer（レビュー） / GitIntegration（Git操作） / GuardianWorkflow（統合）

**P1合計**: 32-44時間（約5-6日）

---

## 優先度P2（改善・品質向上、余裕があれば）

### P2-1. N+1クエリの解消
- **対象**: `webapp/views_projects.py`, `views_dashboard.py`
- **問題**: `project.runs.all()` ループでN+1クエリ
- **工数**: 4-6時間
- **修正**: `joinedload` / `subqueryload` の使用

### P2-2. 設定UI（Gradioタブ）の追加
- **対象**: `ui/` 配下
- **問題**: 環境変数20+の手動設定が必要
- **工数**: 6-8時間
- **修正**: LLM設定・コスト見積もりのGradioタブ追加

### P2-3. 進捗表示の改善
- **対象**: `orchestrator/authority_runner.py`
- **問題**: 長時間実行時のフィードバック不足
- **工数**: 6-8時間
- **修正**: tqdm進捗バー、フェーズごとの詳細ログ

### P2-4. ログフォーマットの統一
- **対象**: 全モジュール（`print()` 残存箇所含む）
- **問題**: ログフォーマットが不統一、`print()` 混在
- **工数**: 4-6時間
- **修正**: 構造化ログ、`print()` → `logger` 統一、コンテキスト情報付与

### P2-5. Webapp DBクエリの共通化
- **対象**: `webapp/views_projects.py`, `views_logs.py`, `views_dashboard.py`
- **問題**: 同じ `filter_by(owner_id=user.id)` パターンが重複
- **工数**: 4-6時間
- **修正**: UserScopedQuery ヘルパー / PaginationMixin

### P2-6. Dead code・未使用importの除去
- **対象**: 全モジュール
- **問題**: `# type: ignore` 過多、未使用import残存
- **工数**: 2-4時間
- **修正**: pylint unused-import 有効化、一括除去

**P2合計**: 26-38時間（約4-5日）

---

## 工数サマリー

| 優先度 | 項目数 | 工数 | リスク |
|--------|--------|------|--------|
| P0 | 4 | 17-25h (3-4日) | 高（セキュリティ・安定性） |
| P1 | 5 | 32-44h (5-6日) | 中（アーキテクチャ） |
| P2 | 6 | 26-38h (4-5日) | 低（品質向上） |
| **総計** | **15** | **75-107h (12-15日)** | |

## 依存関係

```
P0-1 (ハードコード) ──> P1-2 (authority_runner分割)
P0-2 (例外ハンドリング) ──> P1-3 (LLM共通化)
P0-3 (self_healing分割) ──> P1-5 (GuardianAgent分離)

P1-1 (エラーメッセージ) は独立
P2-1〜P2-6 は独立実行可能
```

## 推奨実行順序

1. **Day 1-2**: P0-1 + P0-2（ハードコード設定化 + 例外修正）
2. **Day 3**: P0-4（API入力検証）
3. **Day 4-5**: P0-3（self_healing分割）
4. **Day 6-7**: P1-1 + P1-3（エラーメッセージ + LLM共通化）
5. **Day 8-10**: P1-2 + P1-4 + P1-5（大ファイル分割）
6. **Day 11-15**: P2項目から優先度の高いもの
