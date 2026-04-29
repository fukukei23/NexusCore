# NexusCore リファクタリングバックログ

## 進捗状況
- [x] **Aタスク**: テスト構造整理・不要コードアーカイブ・README精度向上（完了・mainマージ済み）
- [x] **Cタスク**: BaseAgent非継承エージェントの準拠化（完了・PR #97）
- [x] **Dタスク**: LLMルーティングのマルチプロバイダー化（完了・PR #98）※追修正: provider_factory未登録により全タスクGLMフォールバック → commit `1e6516f2`で修正
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

### ~~Hタスク: テストの網羅性向上~~ ✅完了 (2026-04-29)
- **完了内容**: コア層インテグレーションテスト9件追加（実LLM API呼び出し）
- **実績**: LLMRouter(2) + Phase実行(5) + フルパイプライン(2) = 9テスト全合格

## 優先度3: 低（長期改善）

### ~~Iタスク: Dead code完全除去~~ ✅完了 (2026-04-29)
- **完了内容**: 4ファイル・5件の未使用import削除（tqdm/colorama/speech_recognitionのdead try/except含む）
- **結果**: 850/851 tests passed（1件はgemini未インストールの既知問題）

### Jタスク候補: 型アノテーション強化
- **問題**: 型カバレッジ96.4%（867関数中31件無型、129件部分型）
- **提案**: `__init__`の`-> None`等はmypy自動修正に任せる。手作業コスパ低
- **優先度**: 低 — 96.4%で実用上十分

---

## 判明事項（2026-04-29時点）
- BaseAgentのloggerは`get_logger(__name__)`で生成、名前は`nexuscore.agents.base_agent`
- KnowledgeCuratorAgentのapi_key/modelは実際には未使用（デッドパラメータ）だった→Cタスクで削除済み
- LLMプロバイダーファイルは8つ全て物理存在（GLM/MiniMax-only時代も削除されていなかった）
- Gemini providerテストは`google-generativeai`パッケージ未インストールで1件失敗（既知）
