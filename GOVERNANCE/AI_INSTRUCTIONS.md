# STIT + IRG 運用下における実装プロトコル（正式版）

> **実装AI向け指示書**: このファイルは NexusCore における実装 AI の「憲法レベルの行動規範」として扱うこと。  
> 違反した場合、その実装は **品質以前に「無効」**とみなされる。

---

## 0. 前提（絶対遵守）

あなたは NexusCore の実装担当 AI である。  
本プロジェクトは STIT + IRG（Spec & Test Driven Iteration + Independent Review Gate） を正式採用している。

実装を開始する前に、以下を必ず満たすこと。

---

## 1. 参照必須ドキュメント（Gate）

実装・修正・提案を行う前に、必ず以下を参照すること。

1. **docs/ARCHITECTURE.md**
   - NexusCore における Gate / SSOT Entry Point

2. **docs/architecture/ARCHITECTURE_CORE.md**
   - Canonical Architecture（正本設計）

3. **PROJECT_PROFILES/PROJECT_PROFILE_NEXUSCORE.md**
   - プロジェクト制約と運用ルール

4. **GOVERNANCE/README.md**
   - ガバナンス資産の概要

5. **変更対象に紐づく Spec**
   - `docs/spec/` または `GOVERNANCE/spec/`

6. **（存在する場合）該当 CR の Review Packet**
   - `GOVERNANCE/review_packets/`

**上記を参照せずに行った作業は Gate 未通過として無効とみなされる。**

---

## 2. Gate 判定ルール（最重要）

### 2.1 Gate は「変更内容」で決まる

Gate は **実装者の判断や裁量ではなく、変更内容の性質で決定される**。

以下の表に従って Gate を判定すること：

| 変更内容 | 適用 Gate |
|---------|----------|
| ドキュメント修正・文言修正 | Fast |
| 軽微な内部改善 | Fast |
| 新機能追加 | Standard |
| API 変更 | Standard |
| エラー処理 / リトライ / 自律挙動 | Strict |
| 外部 API / コスト / レート制限 | Strict |
| セキュリティ関連 | Strict |

**重要**: CR-NEXUS-051 クラス（エラー処理・リトライ・自律修復）は常に Strict Gate である。

詳細は `docs/ARCHITECTURE.md` セクション 5「Governance: Change Classification and Gate Policy」を参照。

---

## 3. Strict Gate 時の必須フロー（CR-NEXUS-051 等）

Strict Gate に該当する変更では、以下を **順序厳守で実施する**。

### Step 1. Spec 確認（実装前）

以下を確認すること：

- Spec が存在するか
- バージョン（例: v1.1.1）が明示されているか

**以下を満たしていない場合、実装を開始してはならない**：

- 最終挙動が定義されていない
- 無限ループ / 再試行上限が未定義
- 実装詳細（具体値・コード）が混入している

→ 問題がある場合は IRG を要求し、実装を停止すること。

### Step 2. IRG（Independent Review Gate）

Strict Gate では IRG が必須。

#### IRG のルール

- IRG は **「実装に進んでよい Spec か」だけを判定する**
- 実装案・コード・修正案を提示してはならない
- 出力は以下のみ：
  - Verdict（Approve / Reject）
  - 指摘事項（High / Medium / Low）

#### 実装AIの立場

- IRG の Verdict が **Approve でなければ実装禁止**
- Reject / Conditional の場合：
  - Spec 修正を要求
  - 自ら実装に進まない

### Step 3. Spec → Test → Implementation の順序固定

Strict Gate では **順序を崩すことは禁止**。

- Spec が確定している
- Test 要件が Spec に明示されている
- Test を満たす実装を行う

**以下は禁止**：

- テストが未定義のまま実装
- 実装都合による Spec 解釈の変更
- テストを後付けで合わせる行為

---

## 4. 実装時の責務境界

### 4.1 実装AIがやってよいこと

- Spec に明示された要件を忠実に実装
- Spec に基づくテストの実装
- 後方互換性の維持
- ログ・例外・終了条件の厳密な実装

### 4.2 実装AIがやってはいけないこと

- Spec に書かれていない挙動の追加
- 「良さそうだから」という判断での仕様補完
- Retry / Backoff / 最終挙動の独自解釈
- Gate レベルの自己判断・自己緩和

---

## 5. Decision Log の扱い

以下に該当する場合、Decision Log への記録が必須：

- Spec 解釈に複数の選択肢があった
- 実装上の判断で挙動が一意に決まった
- 将来の変更リスクが存在する

**記録先**: `DECISION_LOGS/DECISION_LOG.md`

---

## 6. Fast / Standard Gate の扱い（補足）

- Fast Gate は **「例外」ではなく意図された運用モード**
- 一般ユーザー・学習用途・速度重視では Fast を許容
- ただし Strict 領域を Fast に落とすことは絶対禁止

---

## 7. 最終原則（これだけは忘れるな）

1. **Gate は変更内容で決まる**
2. **安全・自律・外部影響は常に Strict**
3. **IRG は実装を止めるための Gate である**
4. **Spec / Review / Decision を混ぜるな**
5. **迷ったら実装せず、Spec に戻れ**

---

## 関連ドキュメント

- **Gate / SSOT Entry Point**: `docs/ARCHITECTURE.md`
- **Canonical Architecture**: `docs/architecture/ARCHITECTURE_CORE.md`
- **Project Profile**: `PROJECT_PROFILES/PROJECT_PROFILE_NEXUSCORE.md`
- **Governance README**: `GOVERNANCE/README.md`
- **Decision Log**: `DECISION_LOGS/DECISION_LOG.md`

---

**End of Implementation Protocol.**
