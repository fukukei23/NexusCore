**Title**: 開発ロードマップとマイルストーン
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

# NexusCore 開発ロードマップ

## Phase 1: 基盤統合と堅牢化 (Current Priority)
技術的負債を返済し、強固な単一アーキテクチャを確立します。

* **Step 1: アーキテクチャ統合**: Orchestratorを唯一の頭脳とし、重複するUIやロジック（Gradio等）を整理・統合する。
* **Step 2: 自己修復の完成**: DebuggerAgentによる自動修正ロジックの完全自動化。
* **Step 3: 品質ゲートの実装**: テストカバレッジや静的解析スコアに基づく、コード改善の強制ループの実装。

## Phase 2: ミニマムSaaS基盤 (MVP)
Seed調達と初期顧客獲得に向けた機能実装です。

* **認証基盤**: GitHub OAuthによるログインとユーザー管理。
* **プロジェクト管理**: 実行ログ、修正パッチ、テスト結果をプロジェクト単位でDB保存。
* **ログ観測**: Agentの思考プロセスと実行結果を可視化するダッシュボード。

## Phase 3: エンタープライズ対応と拡張
商用レベルの安全性とスケーラビリティを確保します。

* **分離機構**: Dockerコンテナによる完全なサンドボックス環境（マルチテナント対応）。
* **RAG導入**: 大規模コードベースに対応するため、ベクトルDBを用いたRetrieval-Augmented Generationの実装。
* **IDE連携強化**: VSCode拡張機能をLSP（Language Server Protocol）ベースへ進化させ、リアルタイムフィードバックを実現。

---

## Delta / Updates（現状との差分・追記）

ロードマップは将来計画を含むため、実装の「確定事項」は SRS/Governance/CR を優先する。

- **要求（SRS）を起点にする**: 直近は `docs/srs/NEXUSCORE_SRS.md` の FR/NFR を満たす順番で CR を切る（感覚論ではなく要求→実装の線を優先）。
- **統治（Governance）を前提にする**: 凍結境界や禁止事項は `docs/governance/NEXUSCORE_GOVERNANCE.md` を正とする。
- **CR 運用（Spec-driven）**: 新規 CR は `docs/spec/` に置き、CR 冒頭で SRS トレーサビリティを固定フォーマットで付与する（`docs/srs/README.md`）。
- **AuthorityLevel の導入**: AuthorityLevel/互換/テスト容易性に関する最小要件は SRS（FR-ORC-003, FR-ORC-004, NFR-SEC-003）で固定し、実装は CR で追う。

## 改訂履歴

- 2026-04-17: v1.1 [cite:...]出典メモを除去。Charter参照を「planned」から実ファイルに更新。FR参照を新番号体系に更新。
- 2025-12-16: v1.0 初版作成。
