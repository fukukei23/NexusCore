# PROJECT_PROFILE_NEXUSCORE.md
> Project Constraints & Operating Rules (STIT+IRG)

## Metadata
- Project: NexusCore
- ProfileVersion: 0.1.0
- LastUpdated: 2025-01-05
- Owner: <your-name-or-handle>
- Status: Draft (Bootstrap)

---

## 1. Purpose（このプロファイルの目的）
本書は NexusCore の開発・運用における「制約（Constraints）」を宣言し、AI実装・レビュー・意思決定が推測で逸脱しないよう統制する。

- 何を固定するか：
  - スコープ境界（やる/やらない）
  - 非機能要件（品質・安全・運用）
  - 禁止事項（やってはいけない）
  - 変更管理（Spec / Phase 2.5 / Decision Log）

---

## 2. Scope（対象範囲）
### 2.1 In Scope（やる）
- AI駆動の開発支援ワークフロー（要件→設計→実装→テスト→レビュー→記録）
- 差分（diff）中心の反復修正と履歴管理
- 依存関係/構文解析（例：tree-sitter等）
- テスト生成・実行・結果の可視化（例：pytest等）
- ガバナンス運用（STIT+IRG：Spec、Independent Review、Decision Log）

### 2.2 Out of Scope（やらない / 別管理）
- <TODO: 認証/課金/本番SRE等、今は対象外なら明記>
- <TODO: 顧客案件固有の仕様は別Spec管理>
- <TODO: 違法・規約違反を助長する用途>

---

## 3. Operating Model（運用モデル）
### 3.1 Gate（参照強制）
開発タスク開始前に必ず参照する：
- `docs/ARCHITECTURE.md`（SSOT入口）
- [Project Profile](../PROJECT_PROFILES/PROJECT_PROFILE_NEXUSCORE.md)（このファイル）
- [Governance](../GOVERNANCE/README.md)
- `GOVERNANCE/MASTER_PROTOCOL_TEMPLATE.md`（プロトコル）
- 変更対象に関連する Spec（`docs/spec/` または `GOVERNANCE/spec/`）

### 3.2 STIT（Spec & Test Driven Iteration）
- 仕様（Spec）を先に書く。テスト可能な受入条件を含める。
- 実装は Spec を満たす最小差分に限定する。

### 3.3 IRG（Independent Review Gate / Phase 2.5）
- 実装者とは別コンテキスト（別チャット/別AI/別セッション）でレビューする。
- IDE内の自己チェックは Gate 通過とみなさない。
- 結果は Decision Log に必ず転記する（Reject含む）。

---

## 4. Quality & Non-Functional Requirements（非機能要件）
### 4.1 Reliability
- 失敗時に復旧可能（ログ・差分・再実行手順が残る）
- 同一入力で再現可能な振る舞い（可能な範囲で）

### 4.2 Security / Secrets
- APIキー、トークン、個人情報を Git 管理下に入れない
- ログ/ZIP出力/共有物に秘密情報が混入しない設計を優先
- 外部LLMへ送信する情報は最小化し、機密は原則遮断

### 4.3 Observability（観測性）
- 重要イベント（実行、失敗、修正、レビュー結果）を追跡可能にする
- 何がいつ変わったかを Git と Decision Log で追える状態を維持

---

## 5. Constraints（制約）
### 5.1 Architectural Constraints
- SSOTはドキュメント（ARCHITECTURE/Spec/Decision Log）に置く。UIに依存させない
- 責務境界：
  - Agent：判断/生成
  - Utility：I/O、ファイル操作、差分適用、テスト実行
  - Router：モデル選択/予算/ポリシー
- 既存構造の大規模移動は、別Specで段階的に扱う（本プロファイルでは抑制）

### 5.2 Documentation Constraints
- **ガバナンス資産（GOVERNANCE/**, PROJECT_PROFILES/**, DECISION_LOGS/**）内に絶対パスや環境依存パスを書かない**（例示でも禁止）
- `docs/` 配下の既存ドキュメントは対象外（WSL環境での運用手順として必要なパスを含む場合がある）
- チャット由来の疑似パス/疑似アーティファクト文字列を「実在」として扱わない
- SSOT（Git管理ファイル）以外を根拠にしない
- 衛生チェック対象は **GOVERNANCE/**, **PROJECT_PROFILES/**, **DECISION_LOGS/** に限定する（`docs/` は対象外）

---

## 6. Decision Log Policy（意思決定ログ）
- 重要な判断・却下（Reject）・方針変更は `DECISION_LOGS/DECISION_LOG.md` に追記する
- 過去エントリを編集しない（append-only）

---

## 7. Open Questions（要確認 / TODO）
- [ ] 実行エントリポイント（例：app.py / server.py / main_ui.py 等）
- [ ] 永続化の実体（ログ/履歴/ナレッジの保存先と形式）
- [ ] 外部LLM接続（OpenAI等）の扱い（送信範囲、マスキング方針）
- [ ] CIの有無、テストの標準実行方法
- [ ] 公開範囲（OSS/Private）と含めない情報の範囲

---
End of Project Profile.
