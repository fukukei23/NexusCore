# NexusCore: 最小 SRS（v0.1）

**Version**: v0.1（最小）
**Scope**: NexusCore（自己修復型・自律エージェント基盤）
**Purpose**: 要求仕様（SRS）を明文化し、CR（実装仕様）との **遡及トレーサビリティ**を確立する。

---

## 1. 目的（Why）

NexusCore は AI/Orchestrator/Human が協調して開発・自己修復を行う基盤である。現状は CR（実装仕様）が先行し、「何の要求を満たすための変更か」を上位要求として追跡できない課題がある。

本 SRS（v0.1）は以下を目的とする。

- **権限レベル（AuthorityLevel）**と運用上の **ガバナンス/説明責任**を要求として固定する
- CR が満たすべき要求（FR/NFR）を列挙し、**CR → SRS** の一方向トレースを可能にする
- 将来の大きな改修（例: core/orchestrator 改修が必要な CR）に向け、要求→実装→監査の線を準備する

---

## 2. ステークホルダー定義

- **Operator**: NexusCore を実運用/実行する担当者（CLI/API/UI を利用してジョブ実行・停止・確認を行う）
- **Reviewer**: 変更の妥当性・安全性・証跡を確認し承認/差し戻しする担当者
- **Developer**: NexusCore を拡張・保守する開発者（CR を作成し実装する）
- **External Consumer**: API/SDK/UI を介して NexusCore の機能を利用する外部利用者（SaaS/外部提供を含む）

---

## 3. 用語定義（Glossary）

- **Orchestrator**: 開発フロー（複数フェーズ）を統制し、実行/停止/証跡を制御する中核コンポーネント
- **Phase**: Orchestrator が順序立てて実行する工程単位（例: requirements / planning / architecture / implementation / testing / review）
- **AuthorityLevel**: 自律性（権限レベル）を段階化した識別子。どこまで自動実行できるか、どこで人間介入が必須かを規定する
- **autonomy_level**: 既存の自動化レベル指定（数値）。AuthorityLevel と整合/互換を保つ必要がある
- **Constitution**: 実行ポリシーを保持する設定/構造（例: automation_policy を含む）

---

## 4. ユースケース（Use Cases）

- **UC-1（Operator）**: 権限レベルを指定してジョブを実行し、必要なら停止/中断する
- **UC-2（Reviewer）**: 実行の証跡（いつ/どこまで/なぜ）を確認し、変更や実行の承認判断に利用する
- **UC-3（Developer）**: 新規 CR を作成し、SRS の FR/NFR を参照して実装範囲と検証を定義する
- **UC-4（External Consumer）**: 公開された導線（API/SDK/UI）を通じて機能を利用し、互換性のある振る舞いを期待する

---

## 5. 機能要求（FR: Functional Requirements）

### FR-1: 権限レベル制御

システムは AuthorityLevel に基づき、オーケストレーション実行の自律範囲（どこまで自動実行するか、どこで止めるか）を制御できなければならない。

### FR-2: AuthorityLevel と autonomy_level の互換

既存の `autonomy_level` 指定と新設の AuthorityLevel は矛盾なく共存し、互換性を保たなければならない（既存運用の破壊を禁止）。

### FR-3: CLI/API 導線

Operator/External Consumer は CLI/API（および必要に応じ UI）から、権限レベル/自動化レベルを指定して実行を開始できなければならない。

### FR-4: テスト可能性

AuthorityLevel による制御は、実 LLM 呼び出し無しのユニットテストで検証可能でなければならない（Fake/Mock/Stub を許容）。

---

## 6. 非機能要求（NFR: Non-Functional Requirements）

### NFR-1: 監査可能性（Auditability）

実行・変更・判断は追跡可能でなければならない。少なくとも「いつ/何を/どこまで/なぜ」が説明できる証跡が残ること。

### NFR-2: 安全性（Fail-safe）

不確実な状況では安全側に倒れ、停止/中断が可能であること。失敗証跡の保存が優先されること。

### NFR-3: 変更容易性（core 凍結前提）

中核（凍結）領域を安易に変更せずに、周辺（外側の薄い層）で拡張・制御できる構造であること。

---

## 7. 制約条件（Constraints）

- `src/nexuscore/core/orchestrator.py` は凍結対象であり、無制限な変更を前提にしない
- SRS v0.1 は最小粒度に留め、詳細設計（SDD）を含めない（将来 CR-NEXUS-020 以降で拡張）
- CR は SRS の FR/NFR を参照して記述する。SRS は CR の上位文書である

---

## 8. 受け入れ条件（Acceptance）

- `docs/srs/NEXUSCORE_SRS.md` が存在し、FR-1〜FR-4 / NFR-1〜NFR-3 を含む v0.1 として成立している
- `docs/spec/CR-NEXUS-*.md` の各 CR 冒頭に、SRS 参照と満たす FR/NFR の明示（SRS Traceability）が付与されている
- トレーサビリティは **CR → SRS** の一方向であり、CR 本文の意味/結論を後付けで変更していない

---

## 9. 関連ドキュメント

- **Governance**: `docs/governance/NEXUSCORE_GOVERNANCE.md`
- **CR（Specs）**: `docs/spec/` 配下（例: `CR-NEXUS-*`, `CR-FASTAPI-*`）


