# NexusCore Minimal Governance

## 0. このドキュメントの位置づけ

- 対象: NexusCore（自己修復型・自律エージェント基盤）。AKM（Atelier-Kyo-Manager）には適用しない。
- 目的: AI/Orchestrator/Human の行動を「最小限の統治ルール」で制約し、外部提供（SaaS/API）に耐える説明責任を確保する。
- 優先順位: 速度よりも **安全性・証跡・再現性** を優先する（ただし探索を止めない最小統治に留める）。
- 関連文書: AI Collaboration Rules: docs/governance/AI_COLLABORATION_RULES.md

## 1. NexusCore の基本原則（Principles）

- 自己修復は許可するが、自己正当化（根拠なしに「正しい」と断言する）は禁止。
- 進化（試行錯誤）は許可するが、不可逆変更（戻せない変更）は禁止。
- AI は「提案者」であり「最終決定者ではない」。
- 失敗は負債ではなく資産。失敗証跡の保存は成功ログより優先。

## 2. システム構成と責務境界（Responsibility Boundaries）

- Human: 統治者（ルール制定・承認・例外判断）
- Orchestrator: 実行統制者（権限境界の強制、監査ログ、実行計画、停止判断）
- Agents: 実働部隊（収集・修復・解析・提案）
- Experimental: 破棄前提の試験領域（本番資産への影響を遮断）

## 3. 禁止事項（Hard Constraints）

> ここは「AIがやってはいけないこと」を明示し、例外を作らない。

- Governance 自体の改訂・削除・無効化
- Freeze 対象（後述）のコード/設定の直接変更（AI単独では不可）
- 監査証跡（ログ、差分、失敗分析、スクショ、HAR 等）の削除・改ざん
- コスト上限・LLM ルーティング・シークレット（APIキー等）の自己変更
- 外部への無承認送信（ログ/HTML/機密情報を第三者へ送る行為）

## 4. Freeze ポリシー（Minimal）

### 4.1 Freeze 対象（厳格）

- Orchestrator（実行統制ロジック）
- LLM Controller（プロバイダ/モデル選択、フォールバック、キャッシュ、コスト計上）
- RunContext / History / Diff / Evidence（証跡管理）

### 4.2 Freeze 非対象（自由度高）

- 個別 Agent の戦術ロジック
- プロンプト・テンプレート
- サイト別セレクタ・設定（ただし証跡と差分は必須）
- UI/CLI（ただし監査ログ連携を壊さない）

## 5. 変更の分類と許可レベル

- Level 0: AI 不可（Human 専権）
- Level 1: AI 提案のみ（Human 承認が必要）
- Level 2: 条件付き実行可（テスト・差分・証跡が条件）
- Level 3: 自動実行可（自己修復領域）
- Level 4: 完全自律（実験領域、破棄前提）

---

# 権限レベル定義（本書では Level 0 / Level 1 のみ文章化）

## Level 0（AI 不可）

### 定義

AI が「提案」すら実行のトリガーにできない領域。変更は Human が直接行い、監査ログに記録する。

### 対象（最低限）

- Governance 文書・Freeze Policy の改訂
- Orchestrator の権限強制ロジック、境界判定ロジック
- LLM Controller のプロバイダ/モデル/コスト上限/鍵管理
- 証跡（RunContext/History/Diff/Evidence）の保存方式・削除規則

### 要件（必須）

- 変更は必ず差分として保存（例: patch / diff / commit）
- 変更理由（Why）と影響範囲（Impact）をセットで残す

## Level 1（AI 提案のみ）

### 定義

AI は差分案を作成してよいが、適用（マージ/上書き/デプロイ）は Human の承認を必須とする。

### 対象（例）

- Orchestrator の非本質的改修（ログ整形、メッセージ改善、軽微な互換修正）
- Core API（外部連携）周りの仕様変更
- 重要なデータモデル（ResultModel、Evidence Schema）の変更

### AI が出すべき成果物（最低限）

- 変更提案（差分/パッチ）
- 影響範囲（どのモジュール・どのユースケースに影響するか）
- リスク（破壊的変更、後方互換、コスト増）
- 代替案（少なくとも1つ）
- ロールバック手順（戻し方）

---

# 以降は後回し（見出しのみ確保）

## 6. 失敗・自己修復の扱い

## 7. 外部公開・SaaS 時の前提

## 8. 改訂ルール


