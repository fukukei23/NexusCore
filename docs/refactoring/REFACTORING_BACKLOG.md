# NexusCore リファクタリングバックログ

## 進捗状況
- [x] **Aタスク**: テスト構造整理・不要コードアーカイブ・README精度向上（完了・mainマージ済み）
- [x] **Cタスク**: BaseAgent非継承エージェントの準拠化（完了・PR #97）
- [x] **Dタスク**: LLMルーティングのマルチプロバイダー化（完了・PR #98）
- [x] **Eタスク**: Orchestrator God Class分割（完了・PR #99）
- [x] **Fタスク**: 未使用テスト依存の解消（完了）

---

## 優先度1: 高（品質・保守性に直結）

### Eタスク候補: God Class分割 — orchestrator.py
- **対象**: `src/nexuscore/core/orchestrator.py`
- **問題**: 複数の責務（ルーティング、デバッグ、テスト実行、FKB管理、セッション管理）が1ファイルに集約
- **提案**: 責務ごとにモジュール分割（例: `orchestrator_router.py`, `orchestrator_session.py`）
- **影響範囲**: 呼び出し側（server.py, execute.py等）のimport変更

### Fタスク候補: 未使用テスト依存の解消
- **対象**: `tests/agents/test_knowledge_curator_agent_ultimate.py::test_content_analysis_system`
- **問題**: openai パッケージ未インストールで失敗（Cタスクとは無関係の既存問題）
- **提案**: openai依存をモック化するか、テストをCI-safe要件に準拠させる

## 優先度2: 中（コード品質向上）

### Gタスク候補: agents/__init__.py のエクスポート整理
- **対象**: `src/nexuscore/agents/__init__.py`
- **問題**: ContextAgentをanalyzer/に移動したが、再エクスポートの整合性確認が必要
- **提案**: 全エージェントのimportパスが統一されているか監査

### Hタスク候補: テストの網羅性向上
- **問題**: 一部テストがモックに依存しすぎ、実際のビジネスロジックを検証していない
- **提案**: コアロジックの統合テスト追加（サンドボックス内で実行）

## 優先度3: 低（長期改善）

### Iタスク候補: Dead code完全除去
- **問題**: Aタスクで主要なdead codeは除去したが、細かい未使用関数・インポートが残存する可能性
- **提案**: pyflakes/pylint等で未使用コードを一括スキャン

### Jタスク候補: 型アノテーション強化
- **問題**: 一部モジュールで型ヒントが不完全
- **提案**: mypy strict modeで段階的に型カバレッジを向上

---

## 判明事項（2026-04-29時点）
- BaseAgentのloggerは`get_logger(__name__)`で生成、名前は`nexuscore.agents.base_agent`
- KnowledgeCuratorAgentのapi_key/modelは実際には未使用（デッドパラメータ）だった→Cタスクで削除済み
- LLMプロバイダーファイルは8つ全て物理存在（GLM/MiniMax-only時代も削除されていなかった）
- Gemini providerテストは`google-generativeai`パッケージ未インストールで1件失敗（既知）
