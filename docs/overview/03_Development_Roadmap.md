**Title**: 開発ロードマップとマイルストーン
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

# NexusCore 開発ロードマップ

## Phase 1: 基盤統合と堅牢化 (Current Priority)
[cite_start]技術的負債を返済し、強固な単一アーキテクチャを確立します [cite: 31]。

* [cite_start]**Step 1: アーキテクチャ統合**: Orchestratorを唯一の頭脳とし、重複するUIやロジック（Gradio等）を整理・統合する [cite: 32, 35]。
* [cite_start]**Step 2: 自己修復の完成**: DebuggerAgentによる自動修正ロジックの完全自動化 [cite: 39]。
* [cite_start]**Step 3: 品質ゲートの実装**: テストカバレッジや静的解析スコアに基づく、コード改善の強制ループの実装 [cite: 550]。

## Phase 2: ミニマムSaaS基盤 (MVP)
[cite_start]Seed調達と初期顧客獲得に向けた機能実装です [cite: 276]。

* [cite_start]**認証基盤**: GitHub OAuthによるログインとユーザー管理 [cite: 280]。
* [cite_start]**プロジェクト管理**: 実行ログ、修正パッチ、テスト結果をプロジェクト単位でDB保存 [cite: 284]。
* [cite_start]**ログ観測**: Agentの思考プロセスと実行結果を可視化するダッシュボード [cite: 294]。

## Phase 3: エンタープライズ対応と拡張
[cite_start]商用レベルの安全性とスケーラビリティを確保します [cite: 51]。

* [cite_start]**分離機構**: Dockerコンテナによる完全なサンドボックス環境（マルチテナント対応） [cite: 54, 189]。
* [cite_start]**RAG導入**: 大規模コードベースに対応するため、ベクトルDBを用いたRetrieval-Augmented Generationの実装 [cite: 56, 195]。
* [cite_start]**IDE連携強化**: VSCode拡張機能をLSP（Language Server Protocol）ベースへ進化させ、リアルタイムフィードバックを実現 [cite: 47]。

---

## Delta / Updates（現状との差分・追記）

ロードマップは将来計画を含むため、実装の「確定事項」は SRS/Governance/CR を優先する。

- **要求（SRS）を起点にする**: 直近は `docs/srs/NEXUSCORE_SRS.md` の FR/NFR を満たす順番で CR を切る（感覚論ではなく要求→実装の線を優先）。
- **統治（Governance）を前提にする**: 凍結境界や禁止事項は `docs/governance/NEXUSCORE_GOVERNANCE.md` を正とする。
- **CR 運用（Spec-driven）**: 新規 CR は `docs/spec/` に置き、CR 冒頭で SRS トレーサビリティを固定フォーマットで付与する（`docs/srs/README.md`）。
- **AuthorityLevel の導入**: AuthorityLevel/互換/テスト容易性に関する最小要件は SRS（FR-1/FR-2/FR-4, NFR-3）で固定し、実装は CR で追う。
- **[cite: ...] の扱い**: `[cite: ...]` は現状「出典メモ」。対応表は `docs/refs/REFERENCE_NOTES.md` に置く。

## Revision History

- 2025-12-16: v0.1（DRAFT）相当の原文を保存し、v1.0 としてヘッダ統一・差分追記を実施。


