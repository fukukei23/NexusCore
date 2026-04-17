**Title**: NexusOS 技術アーキテクチャ仕様書
**Version**: v1.1
**Status**: CURRENT
**Last reviewed**: 2026-04-17
**Related docs**:
- Charter: `docs/overview/NEXUSCORE_PRODUCT_CHARTER.md`
- SRS: `docs/srs/NEXUSCORE_SRS.md`
- Governance: `docs/governance/NEXUSCORE_GOVERNANCE.md`
- CR Specs: `docs/spec/`
- Overview Index: `docs/overview/00_OVERVIEW_INDEX.md`

---

# NexusOS 技術アーキテクチャ仕様書

## 1. アーキテクチャ概要: NexusOS
NexusCoreは、自己統治・自己回復能力を備えたオペレーティングシステム「NexusOS」として設計されています。

* **カーネル**: Orchestrator（司令塔）、VCS（バージョン管理）。
* **システムサービス**: Coder, Tester, Guardianなどの専門エージェント群。
* **データ永続化**:
    * *ステートストア (Redis)*: 作業中の一時データ管理。
    * *ナレッジベース (PostgreSQL)*: 知識やログの恒久的な保存。

## 2. エージェント構成 (The Team)
Orchestratorを中心としたマルチエージェントシステム（MAS）。

| エージェント | 役割 |
| :--- | :--- |
| **Orchestrator** | 開発プロセス全体を指揮する現場監督。 |
| **ArchitectAgent** | プロジェクト全体の設計図を作成。 |
| **PlannerAgent** | 要求をタスクに分解するPM。 |
| **CoderAgent** | コードを実装する開発者。 |
| **TesterAgent** | テストコードを生成・実行するQA。 |
| **DebuggerAgent** | エラー分析と自己修復を行う専門家。 |
| **GuardianAgent** | 成果物をレビューし承認するCTO。 |
| **Postmortem/KnowledgeCurator** | 未知の失敗から学び、知識を検証・蓄積する研究開発部門。 |

## 3. 自己修復と学習メカニズム (Immune System)
NexusCoreの最大の特徴は、未知のエラーから学習する能力です。

1.  **検知**: テスト失敗を検知。
2.  **分析**: 既知のFKB（故障知識ベース）で解決できない場合、PostmortemAgentが原因を分析。
3.  **生成**: 新しい解決策（知識）をJSON形式で提案。
4.  **検証**: KnowledgeCuratorAgentがサンドボックス内で検証。
5.  **更新**: 検証に成功すればFKBを自動更新し、DebuggerAgentが再試行。

## 4. 品質保証システム
* **静的解析**: Pylint, MyPy, Banditによるコード品質チェック。
* **動的解析**: pytestによるテスト実行とカバレッジ計測。
* **Mutation Testing**: 意図的にバグを埋め込み、テストの「鋭さ」を検証する。

---

## Delta / Updates（現状との差分・追記）

実装現況に合わせ、最小限の整合情報を追記する。

- **AuthorityLevel / autonomy_level**: 要求仕様は `docs/srs/NEXUSCORE_SRS.md`（FR-ORC-003, FR-ORC-004）を正とする。CR としては `docs/spec/CR-NEXUS-012_Authority_Level_Control.md` を参照する。
- **凍結（Freeze）境界**: 統治上の凍結方針は `docs/governance/NEXUSCORE_GOVERNANCE.md` を正とする。
- **エージェント構成（実装現況）**: 現在のエージェント群は `src/nexuscore/core/orchestrator.py` の import/組み立てを一次根拠とする（文書の表は概念図であり、実装差異は CR/コードを優先）。
- **仕様駆動開発（Spec-driven）**: Spec 形式/保存規約は `docs/spec/` および `docs/spec/SPEC_TEMPLATE.md` を参照する。

## 改訂履歴

- 2026-04-17: v1.1 [cite:...]出典メモを除去。Charter参照を「planned」から実ファイルに更新。FR参照を新番号体系に更新。
- 2025-12-16: v1.0 初版作成。
