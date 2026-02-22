**Title**: NexusOS 技術アーキテクチャ仕様書
**Version**: v1.0
**Status**: CURRENT
**Last reviewed**: 2025-12-16
**Related docs**:
- Charter: `docs/overview/NEXUSCORE_PRODUCT_CHARTER.md`（planned）
- SRS: `docs/srs/NEXUSCORE_SRS.md`
- Governance: `docs/governance/NEXUSCORE_GOVERNANCE.md`
- CR Specs: `docs/spec/`
- Overview Index: `docs/overview/00_OVERVIEW_INDEX.md`

---

# NexusOS 技術アーキテクチャ仕様書

## 1. アーキテクチャ概要: NexusOS
[cite_start]NexusCoreは、自己統治・自己回復能力を備えたオペレーティングシステム「NexusOS」として設計されています [cite: 66, 71]。

* **カーネル**: Orchestrator（司令塔）、VCS（バージョン管理）。
* **システムサービス**: Coder, Tester, Guardianなどの専門エージェント群。
* **データ永続化**:
    * [cite_start]*ステートストア (Redis)*: 作業中の一時データ管理 [cite: 80, 180]。
    * [cite_start]*ナレッジベース (PostgreSQL)*: 知識やログの恒久的な保存 [cite: 81, 181]。

## 2. エージェント構成 (The Team)
[cite_start]Orchestratorを中心としたマルチエージェントシステム（MAS）です [cite: 221, 598]。

| エージェント | 役割 |
| :--- | :--- |
| **Orchestrator** | [cite_start]開発プロセス全体を指揮する現場監督 [cite: 597]。 |
| **ArchitectAgent** | [cite_start]プロジェクト全体の設計図を作成 [cite: 599]。 |
| **PlannerAgent** | [cite_start]要求をタスクに分解するPM [cite: 600]。 |
| **CoderAgent** | [cite_start]コードを実装する開発者 [cite: 601]。 |
| **TesterAgent** | [cite_start]テストコードを生成・実行するQA [cite: 602]。 |
| **DebuggerAgent** | [cite_start]エラー分析と自己修復を行う専門家 [cite: 603]。 |
| **GuardianAgent** | [cite_start]成果物をレビューし承認するCTO [cite: 604]。 |
| **Postmortem/KnowledgeCurator** | [cite_start]未知の失敗から学び、知識を検証・蓄積する研究開発部門 [cite: 610, 611]。 |

## 3. 自己修復と学習メカニズム (Immune System)
[cite_start]NexusCoreの最大の特徴は、未知のエラーから学習する能力です [cite: 608]。

1.  **検知**: テスト失敗を検知。
2.  [cite_start]**分析**: 既知のFKB（故障知識ベース）で解決できない場合、PostmortemAgentが原因を分析 [cite: 610]。
3.  [cite_start]**生成**: 新しい解決策（知識）をJSON形式で提案 [cite: 154]。
4.  [cite_start]**検証**: KnowledgeCuratorAgentがサンドボックス内で検証 [cite: 131]。
5.  [cite_start]**更新**: 検証に成功すればFKBを自動更新し、DebuggerAgentが再試行 [cite: 132]。

## 4. 品質保証システム
* [cite_start]**静的解析**: Pylint, MyPy, Banditによるコード品質チェック [cite: 549]。
* [cite_start]**動的解析**: pytestによるテスト実行とカバレッジ計測 [cite: 550]。
* [cite_start]**Mutation Testing**: 意図的にバグを埋め込み、テストの「鋭さ」を検証する [cite: 555]。

---

## Delta / Updates（現状との差分・追記）

実装現況に合わせ、最小限の整合情報を追記する。

- **AuthorityLevel / autonomy_level**: 要求仕様は `docs/srs/NEXUSCORE_SRS.md`（FR-1/FR-2/FR-4, NFR-3）を正とする。CR としては `docs/spec/CR-NEXUS-012_Authority_Level_Control.md` を参照する。
- **凍結（Freeze）境界**: 統治上の凍結方針は `docs/governance/NEXUSCORE_GOVERNANCE.md` を正とする。
- **エージェント構成（実装現況）**: 現在のエージェント群は `src/nexuscore/core/orchestrator.py` の import/組み立てを一次根拠とする（文書の表は概念図であり、実装差異は CR/コードを優先）。
- **仕様駆動開発（Spec-driven）**: Spec 形式/保存規約は `docs/spec/` および `docs/spec/SPEC_TEMPLATE.md`、ならびに標準化レポート `docs/spec/CR-NEXUS-SPEC-STANDARDIZATION_COMPLETION_REPORT.md` を参照する。
- **[cite: ...] の扱い**: `[cite: ...]` は現状「出典メモ」。対応表は `docs/refs/REFERENCE_NOTES.md` に置く。

## Revision History

- 2025-12-16: v0.1（DRAFT）相当の原文を保存し、v1.0 としてヘッダ統一・差分追記を実施。


