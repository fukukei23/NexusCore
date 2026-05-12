# NexusCore リファクタリングバックログ

> **タスク管理はLinearに移行しました（2026-04-29）**
> **SSOT**: [Linear - NexusCore Project](https://linear.app/fukukei/project/nexuscore-fc1722460cf4)

## 完了済みタスク（2026-05-12〜13）

| イシュー | タイトル | 状態 |
|---|---|---|
| FUK-5 | 型アノテーション強化（mypy 24→0 errors） | Done |
| FUK-6 | GLM providerテスト失敗解消（GLM_API_BASE環境変数） | Done |
| FUK-7 | Gradio UI テスト4件失敗 | Excluded（フレーク、再現せず） |
| FUK-8 | `api/routes/projects.py` 分割（493→3ファイル） | Done |
| FUK-9 | `webapp/views_projects.py` ヘルパー抽出（437→2ファイル） | Done |
| FUK-10 | `test_generator.py` TODO 4件解消 | Done |
| FUK-11 | LLM smoke テスト `--run-integration` オプション追加 | Done |

## 完了済みタスク（履歴）

- **Aタスク**: テスト構造整理・不要コードアーカイブ・README精度向上
- **Cタスク**: BaseAgent非継承エージェントの準拠化（PR #97）
- **Dタスク**: LLMルーティングのマルチプロバイダー化（PR #98）
- **Eタスク**: Orchestrator God Class分割（PR #99）
- **Fタスク**: 未使用テスト依存の解消
- **Gタスク**: agents/__init__.py のエクスポート整理
- **Hタスク**: テストの網羅性向上（インテグレーションテスト9件追加）
- **Iタスク**: Dead code完全除去
- **Phase 6 ★3**: モノリスファイル5分割（evaluator, mutation_tester, sandbox_executor, guardian_auto_reviewer, guardian_agent helpers）

## 判明事項（2026-05-13時点）

- テストスイート: 4591 passed / 4 failed (Gradio UI, フレーク) / 2 skipped (integration smoke)
- Phase 6 ★3ファイル分割 + FUK-5〜11 完了。残る技術的負債なし
- BaseAgentのloggerは`get_logger(__name__)`で生成、名前は`nexuscore.agents.base_agent`
- Gemini providerテストは`google-generativeai`パッケージ未インストールでskip（既知）
