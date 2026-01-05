# NexusCore Architecture
> **Gate / SSOT Entrypoint**

本ドキュメントは **NexusCore におけるアーキテクチャ情報の唯一の入口（SSOT Entry Point）** である。
開発・修正・レビュー・AI実装を行う前に、必ず本ファイルを参照すること。

---

## 1. Purpose（このドキュメントの役割）

- アーキテクチャ情報の **参照ゲート（Gate）** を提供する
- 詳細設計の所在を明示し、重複・分散を防ぐ
- STIT+IRG ガバナンスとの接続点を定義する

※ 本ファイル自体には **詳細設計・実装仕様を記載しない**

---

## 2. Canonical Architecture（正本設計）

NexusCore の詳細なアーキテクチャ設計は、以下の **Canonical Design** に集約されている。

- **Canonical Design**
  - `docs/architecture/ARCHITECTURE_CORE.md`

本リポジトリ内で「設計内容そのもの」を参照する場合は、必ず上記ファイルを参照すること。

---

## 3. Gate（参照強制ルール）

開発タスク開始前に、必ず以下を参照すること：

1. 本ドキュメント
   - `docs/ARCHITECTURE.md`（Gate / SSOT Entrypoint）
2. Canonical Architecture
   - `docs/architecture/ARCHITECTURE_CORE.md`
3. Project Constraints
   - `PROJECT_PROFILES/PROJECT_PROFILE_NEXUSCORE.md`
4. Governance Assets
   - `GOVERNANCE/README.md`
   - `GOVERNANCE/MASTER_PROTOCOL_TEMPLATE.md`
5. 変更対象に関連する Spec
   - `GOVERNANCE/spec/` または `docs/spec/`

これらを参照せずに行われた実装・修正・提案は、Gate 未通過として扱う。

---

## 4. STIT+IRG Governance

NexusCore は以下のガバナンスモデルに従う：

- **STIT**: Spec & Test Driven Iteration
- **IRG（Phase 2.5）**: Independent Review Gate

重要な判断・却下・方針変更は、必ず以下に記録する：

- `DECISION_LOGS/DECISION_LOG.md`

---

## 5. Scope of This File（明示的に含まないもの）

以下は **本ファイルには含めない**：

- コンポーネント詳細
- データフロー図
- Mermaid 図
- API / クラス / 関数仕様
- 実装例・コードブロック

それらはすべて **Canonical Architecture** 側に記載する。

---

## 6. Change Policy（変更ポリシー）

- 本ファイルは **Gate と導線のみ** を扱う
- 設計変更が発生した場合：
  1. Canonical Architecture を更新
  2. 必要に応じて本ファイルのリンク・参照先のみ調整
  3. Decision Log に記録（append-only）

---

End of Gate Document.
