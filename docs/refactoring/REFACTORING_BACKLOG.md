# NexusCore リファクタリングバックログ

> **タスク管理はLinearに移行しました（2026-04-29）**
> **SSOT**: [Linear - NexusCore Project](https://linear.app/fukukei/project/nexuscore-fc1722460cf4)

## アクティブなタスク

| イシュー | タイトル | 優先度 | 状態 |
|---|---|---|---|
| [FUK-5](https://linear.app/fukukei/issue/FUK-5/) | 型アノテーション強化（Jタスク） | Low | Backlog |
| [FUK-6](https://linear.app/fukukei/issue/FUK-6/) | Gemini providerテスト失敗の解消 | Medium | Backlog |

## 完了済みタスク（履歴）

- **Aタスク**: テスト構造整理・不要コードアーカイブ・README精度向上
- **Cタスク**: BaseAgent非継承エージェントの準拠化（PR #97）
- **Dタスク**: LLMルーティングのマルチプロバイダー化（PR #98）
- **Eタスク**: Orchestrator God Class分割（PR #99）
- **Fタスク**: 未使用テスト依存の解消
- **Gタスク**: agents/__init__.py のエクスポート整理
- **Hタスク**: テストの網羅性向上（インテグレーションテスト9件追加）
- **Iタスク**: Dead code完全除去

## 判明事項（2026-04-29時点）

- BaseAgentのloggerは`get_logger(__name__)`で生成、名前は`nexuscore.agents.base_agent`
- KnowledgeCuratorAgentのapi_key/modelは実際には未使用（デッドパラメータ）→Cタスクで削除済み
- LLMプロバイダーファイルは8つ全て物理存在（GLM/MiniMax-only時代も削除されていなかった）
- Gemini providerテストは`google-generativeai`パッケージ未インストールで1件失敗（既知）
