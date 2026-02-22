**Title**: プロジェクト・ビジョンとビジネス戦略
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

# NexusCore プロジェクト・ビジョンとビジネス戦略

## 1. NexusCoreの定義
[cite_start]NexusCoreは、単なるコード生成ツールではありません。「自分で考えてプログラムを作り、間違いを自分で直し、人間が定めた品質基準を守りながら成長し続ける、AIのソフトウェア開発チーム」です [cite: 2]。
[cite_start]従来のツールが「個人の能力最大化」を目指すのに対し、NexusCoreは失敗から学び、その教訓を組織全体の知識として蓄積する「自己進化する開発エコシステム」を目指しています [cite: 3]。

## 2. コア・バリューと競合優位性
* [cite_start]**自律的な開発サイクル**: 設計、計画、実装、テスト、レビューの一連のワークフローを、Orchestratorの指揮下で自律的に実行します [cite: 6]。
* [cite_start]**自己進化する品質保証**: 失敗から学び、FKB（故障知識ベース）を更新することで、同じ間違いを二度と繰り返しません [cite: 6, 608]。
* [cite_start]**エンタープライズ・ガバナンス**: 独自のコード機密性、セキュリティ、コンプライアンスを最重視する企業向けに設計されています [cite: 535]。

## 3. ビジネス戦略とターゲット
### 3.1 ターゲット市場
[cite_start]汎用AIアシスタント市場の消耗戦を避け、「エンタープライズ・ガバナンス」というニッチ市場を狙います [cite: 535]。
* **ターゲット**: セキュリティと独自性を重視する企業。
* [cite_start]**Seed準備**: ターゲットセグメントの痛みの強さと予算をスコアリングし、優先ターゲットを絞り込みます [cite: 260, 261]。

### 3.2 SaaSビジネスモデル
* [cite_start]**PoCパッケージ**: 4週間の期間で、対象リポジトリの解析、技術的負債レポート、改善パッチ提供などを行います [cite: 269, 271]。
* [cite_start]**収益モデル**: 固定料金＋成果報酬のオプションを用意します [cite: 272]。

## 4. 目指すべき姿
[cite_start]最終的には、人間の開発者が自然言語で要求するだけで、AIチームが全ての工程を完結させるSaaSプラットフォームの構築を目指します [cite: 593]。

---

## Delta / Updates（現状との差分・追記）

この文書は「ビジョン/戦略」を扱うため、実装状況と 1:1 に一致しない将来像（aspirational）を含み得る。現状の NexusCore に合わせ、以下を追記する。

- **要求（SRS）との整合**: AuthorityLevel/ガバナンス/説明責任は、要求仕様として `docs/srs/NEXUSCORE_SRS.md`（FR/NFR）に集約した。
- **統治（Governance）との整合**: 最小統治ルールは `docs/governance/NEXUSCORE_GOVERNANCE.md` を正として参照する。
- **実装仕様（CR）との整合**: 実装の根拠は `docs/spec/` の CR を正とする（例: `docs/spec/CR-NEXUS-012_Authority_Level_Control.md`）。
- **[cite: ...] の扱い**: `[cite: 123]` は現状「出典メモ」であり、対応表は `docs/refs/REFERENCE_NOTES.md` に置く（後で回収する）。

## Revision History

- 2025-12-16: v0.1（DRAFT）相当の原文を保存し、v1.0 としてヘッダ統一・差分追記を実施。


