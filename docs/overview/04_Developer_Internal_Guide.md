**Title**: 開発者向け環境構築・運用ガイド
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

# NexusCore 開発環境・運用ガイド

## 1. 開発環境の原則
[cite_start]NexusCoreはLinux環境を前提としているため、Windows上での開発には**WSL (Ubuntu)**の使用が必須です [cite: 375, 386]。

* [cite_start]**編集**: Windows側のVSCode（WSLモードで接続） [cite: 389]。
* [cite_start]**実行・Git**: 必ずWSL内のターミナルで行う [cite: 390, 391]。
* [cite_start]**禁止事項**: Windows側のディレクトリにNexusCoreを置かないこと、PowerShellでGit操作を行わないこと [cite: 439, 440]。

## 2. ディレクトリ構成と基本操作
* [cite_start]**場所**: ~/NexusCore (WSL内) [cite: 381]。
* [cite_start]**起動**: WSLターミナルで cd ~/NexusCore -> code . [cite: 395]。
* [cite_start]**VSCode設定**: 左下が >< WSL: Ubuntu となっていることを常に確認する [cite: 396]。

## 3. Git運用ルール
1.  [cite_start]**作業前**: git pull origin main で最新化し、cleanを確認 [cite: 398-402]。
2.  [cite_start]**ブランチ**: git checkout -b feature/xxxx で作業用ブランチを作成 [cite: 404]。
3.  [cite_start]**コミット**: WSLターミナルから git add . -> git commit -> git push [cite: 406-408]。

## 4. セットアップ手順
[cite_start]自動化スクリプト setup_nexuscore_wsl.sh を使用して環境を構築します [cite: 426]。
1.  WSL (Ubuntu) のインストール。
2.  リポジトリのクローン。
3.  [cite_start]Python venvの作成と .env.local の設定 [cite: 431, 433]。

[cite_start]この構成を守ることで、環境差異によるエラーやファイルの不整合を完全に防ぎます [cite: 448, 449]。

---

## Delta / Updates（現状との差分・追記）

運用ルールは、SRS/Governance/CR 運用と矛盾しないよう最小限の追記を行う。

- **Spec-driven development（仕様駆動）**: 変更は CR（`docs/spec/`）を起点にし、必要に応じて SRS（`docs/srs/`）を参照する。CR 冒頭の SRS Traceability は固定フォーマット（`docs/srs/README.md`）。
- **WSL テスト実行の規約**: テストは WSL 上で `bash dev_tools/run_tests.sh tests/…` を推奨する（例: `docs/test_result_reporting.md`）。
- **凍結境界の尊重**: 統治/凍結は `docs/governance/NEXUSCORE_GOVERNANCE.md` を正とし、凍結領域は小型PRで段階的に扱う。
- **[cite: ...] の扱い**: `[cite: ...]` は現状「出典メモ」。対応表は `docs/refs/REFERENCE_NOTES.md` に置く。

## Revision History

- 2025-12-16: v0.1（DRAFT）相当の原文を保存し、v1.0 としてヘッダ統一・差分追記を実施。


