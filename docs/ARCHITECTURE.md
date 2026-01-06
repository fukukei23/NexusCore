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

## 5. Governance: Change Classification and Gate Policy

### 5.1 Gate レベル定義

NexusCore の変更管理は、以下の 3 レベルの Gate で分類される。

#### Fast Gate

- **主目的**: 開発速度の最大化
- **対象ユーザー**: 一般利用者、開発者（内部改善）
- **IRG の要否**: 不要
- **適用範囲**: ドキュメント修正、文言変更、既存機能の軽微な改善

#### Standard Gate

- **主目的**: 品質と安全性のバランス
- **対象ユーザー**: 開発者、内部システム
- **IRG の要否**: 条件付き（変更内容により判断）
- **適用範囲**: 新機能追加、既存機能の拡張、API の変更

#### Strict Gate

- **主目的**: 公開耐性と自律システムの安全性確保
- **対象ユーザー**: 商用・自律系、外部公開
- **IRG の要否**: 必須
- **適用範囲**: エラー処理・リトライ・自律修復、外部 API 連携、コスト・レート制限に影響する変更

### 5.2 Change-Type Based Gate Matrix

Gate は「開発者」ではなく「変更内容」で決定される。以下の表に従って Gate を適用すること。

| 変更カテゴリ | 具体例 | Spec 更新要否 | Test 更新要否 | IRG 要否 | Decision Log 要否 | 適用 Gate |
|------------|--------|-------------|-------------|---------|------------------|----------|
| ドキュメント修正 | README 更新、コメント修正 | 不要 | 不要 | 不要 | 不要 | Fast |
| 文言変更 | エラーメッセージ、ログ出力 | 不要 | 条件付き | 不要 | 不要 | Fast |
| 軽微な改善 | リファクタリング、パフォーマンス最適化 | 条件付き | 条件付き | 不要 | 条件付き | Fast |
| 新機能追加 | ユーザー向け機能の追加 | 必須 | 必須 | 条件付き | 条件付き | Standard |
| API 変更 | エンドポイント追加・変更 | 必須 | 必須 | 条件付き | 必須 | Standard |
| エラー処理・リトライ | エラー分類、リトライ戦略、自律修復 | 必須 | 必須 | 必須 | 必須 | Strict |
| 外部 API 連携 | LLM API、外部サービス統合 | 必須 | 必須 | 必須 | 必須 | Strict |
| コスト・レート制限 | 予算管理、レート制限処理 | 必須 | 必須 | 必須 | 必須 | Strict |
| セキュリティ関連 | 認証・認可、機密情報処理 | 必須 | 必須 | 必須 | 必須 | Strict |

**注意**: CR-NEXUS-051 クラス（エラー処理・リトライ・自律修復）の変更は、常に Strict Gate を適用する。

### 5.3 Independent Review Gate（IRG）の定義

#### IRG の目的

IRG は実装品質ではなく「実装に進んでよい Spec か」を判定する Gate である。

IRG は以下の観点で Spec を評価する：

- 仕様の完全性（必須要件の欠落がないか）
- 安全性（retry / failure 制御、無限ループのリスク）
- 将来拡張耐性（設計の拡張可能性）
- 暗黙仕様の混入有無（実装詳細が仕様に含まれていないか）

#### IRG の性質

IRG は以下の性質を持つ：

- **実装案・修正案・コードは提示しない**: IRG は判断・指摘のみを行う
- **別コンテキストで実施**: 実装者とは別コンテキスト（別 AI / 別セッション）で行う
- **出力は Review Packet と Verdict のみ**: Review Packet には Verdict（Approve / Reject）と指摘事項（High / Medium / Low Severity）を含める

#### IRG が必須となる変更

以下の変更は IRG が必須である：

- 失敗時の最終挙動を定義するもの
- 再試行・ループ・自律挙動に関与するもの
- 外部 API / コスト / レート制限に影響するもの

### 5.4 設計原則（Design Principles）

NexusCore の変更管理は、以下の原則に従う：

1. **Gate は変更種別で決まる**: 開発者の裁量ではなく、変更内容の性質により Gate が決定される
2. **安全・自律・外部影響領域は常に Strict**: エラー処理、リトライ、自律挙動、外部 API 連携、コスト管理は常に Strict Gate を適用する
3. **Fast は例外ではなく「意図された運用モード」**: Fast Gate は品質を犠牲にするものではなく、適切な変更に対して意図的に適用される
4. **IRG は形式チェックではない**: IRG は Spec の妥当性を評価する Gate であり、単なる形式チェックではない
5. **Spec / Review / Decision の三点分離を破らない**: Spec、Review Packet、Decision Log は独立した文書として管理し、相互に混在させない

---

## 6. Scope of This File（明示的に含まないもの）

以下は **本ファイルには含めない**：

- コンポーネント詳細
- データフロー図
- Mermaid 図
- API / クラス / 関数仕様
- 実装例・コードブロック

それらはすべて **Canonical Architecture** 側に記載する。

---

## 7. Change Policy（変更ポリシー）

- 本ファイルは **Gate と導線のみ** を扱う
- 設計変更が発生した場合：
  1. Canonical Architecture を更新
  2. 必要に応じて本ファイルのリンク・参照先のみ調整
  3. Decision Log に記録（append-only）

---

End of Gate Document.
