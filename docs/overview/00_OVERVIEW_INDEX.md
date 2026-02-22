# NexusCore Overview Index

**Version**: v1.0
**Status**: CURRENT
**Last reviewed**: 2025-12-16

## 1. このディレクトリの位置づけ

`docs/overview/` は NexusCore の上位ドキュメント群（ビジョン/アーキテクチャ/ロードマップ/運用）を集約する。

## 2. ドキュメント体系（役割分担）

- **Charter（思想/全体像）**: WHY / 全体モデル（作成予定）
  - `docs/overview/NEXUSCORE_PRODUCT_CHARTER.md`（planned）
- **SRS（要求）**: WHAT / FR・NFR（要求仕様）
  - `docs/srs/NEXUSCORE_SRS.md`
- **Governance（制約/責務）**: Rules / 統治・禁止事項・凍結方針
  - `docs/governance/NEXUSCORE_GOVERNANCE.md`
- **CR（実装仕様）**: HOW / 実装タスクと検証
  - `docs/spec/`
- **Overview（横断）**: ビジネス/技術/計画/運用の統合
  - 本ディレクトリの 01〜04

## 3. ファイル一覧（最新導線）

- **01 ビジョン（ビジネス）**: `docs/overview/01_Project_Vision_and_Strategy.md`
- **02 技術構造（アーキテクチャ）**: `docs/overview/02_Technical_Architecture.md`
- **03 進行計画（ロードマップ）**: `docs/overview/03_Development_Roadmap.md`
- **04 開発運用（マニュアル）**: `docs/overview/04_Developer_Internal_Guide.md`

## 4. 引用メモ（[cite: ...]）の扱い

これらの Overview 文書には、出典メモとして `[cite: 123]` の形式が含まれる場合がある。現時点ではリポジトリ内で参照解決できないため、対応表を `docs/refs/REFERENCE_NOTES.md` に置く（後で回収する）。

## 5. 更新方針

- Overview 文書は、SRS/Governance/CR と矛盾しない範囲で追記・整形する。
- 断定的な「実装済み」表現は、CR/コード/テストで裏付けできる場合に限る（根拠リンクを添える）。


