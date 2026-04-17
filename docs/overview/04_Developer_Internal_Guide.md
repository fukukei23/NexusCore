**Title**: 開発者向け環境構築・運用ガイド
**Version**: v1.0
**Status**: CURRENT
**Last reviewed**: 2025-12-16
**Related docs**:
- Charter: `docs/overview/NEXUSCORE_PRODUCT_CHARTER.md`
- SRS: `docs/srs/NEXUSCORE_SRS.md`
- Governance: `docs/governance/NEXUSCORE_GOVERNANCE.md`
- CR Specs: `docs/spec/`
- Overview Index: `docs/overview/00_OVERVIEW_INDEX.md`

---

# NexusCore 開発環境・運用ガイド

## 1. 開発環境の原則
NexusCoreはLinux環境を前提としているため、Windows上での開発には**WSL (Ubuntu)**の使用が必須です。

* **編集**: Windows側のVSCode（WSLモードで接続）。
* **実行・Git**: 必ずWSL内のターミナルで行う。
* **禁止事項**: Windows側のディレクトリにNexusCoreを置かないこと、PowerShellでGit操作を行わないこと。

## 2. ディレクトリ構成と基本操作
* **場所**: ~/NexusCore (WSL内)。
* **起動**: WSLターミナルで cd ~/NexusCore -> code .。
* **VSCode設定**: 左下が >< WSL: Ubuntu となっていることを常に確認する。

## 3. Git運用ルール
1.  **作業前**: git pull origin main で最新化し、cleanを確認 [cite: 398-402]。
2.  **ブランチ**: git checkout -b feature/xxxx で作業用ブランチを作成。
3.  **コミット**: WSLターミナルから git add . -> git commit -> git push [cite: 406-408]。

## 4. セットアップ手順
自動化スクリプト setup_nexuscore_wsl.sh を使用して環境を構築します。
1.  WSL (Ubuntu) のインストール。
2.  リポジトリのクローン。
3.  Python venvの作成と .env.local の設定。

この構成を守ることで、環境差異によるエラーやファイルの不整合を完全に防ぎます。

---

## Delta / Updates（現状との差分・追記）

運用ルールは、SRS/Governance/CR 運用と矛盾しないよう最小限の追記を行う。

- **Spec-driven development（仕様駆動）**: 変更は CR（`docs/spec/`）を起点にし、必要に応じて SRS（`docs/srs/`）を参照する。CR 冒頭の SRS Traceability は固定フォーマット（`docs/srs/README.md`）。
- **WSL テスト実行の規約**: テストは WSL 上で `bash dev_tools/run_tests.sh tests/…` を推奨する（例: `docs/test_result_reporting.md`）。
- **凍結境界の尊重**: 統治/凍結は `docs/governance/NEXUSCORE_GOVERNANCE.md` を正とし、凍結領域は小型PRで段階的に扱う。
- **

## Revision History

- 2025-12-16: v0.1（DRAFT）相当の原文を保存し、v1.0 としてヘッダ統一・差分追記を実施。


