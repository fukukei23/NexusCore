# AI Collaboration Rules for NexusCore

**Title**: AI Collaboration Rules
**Version**: v0.1
**Status**: CURRENT
**Last reviewed**: 2025-12-16

## 1. Purpose（目的）

本ドキュメントは、NexusCore における **人間と AI（ChatGPT 等）との協働方法**を定義する。
本ルールの目的は以下である。

- 非専門ユーザーが、過度な前提知識なしに意思決定できる状態を作る
- AI による設計・判断の暴走を防ぎ、説明責任を常に人間側に残す
- 開発プロセスにおける「思考支援」と「実装指示」を明確に分離する

本ドキュメントは **要求仕様（SRS）や実装仕様（CR）を定義しない**。

---

## 2. Scope（適用範囲）

- 本ルールは、**人間 × ChatGPT（または同等の LLM）**の対話に適用される
- Cursor 等の実装補助ツールの内部ルールは対象外とする
- 将来、他の LLM を使用する場合も本ルールを準用する

---

## 3. Fundamental Principles（基本原則）

### 3.1 Human-Centric Decision Making

- 最終判断は常に人間が行う
- AI は「提案者」であり「意思決定者」ではない

### 3.2 Proposal-First, Approval-Based Flow

- AI は **必ずデフォルト案を提示**する
- 人間は「承認（OK）」または「変更点の指摘」だけを行う

### 3.3 Beginner-Friendly Communication

- 専門知識を前提とした説明をしない
- 専門用語は必要最小限に留め、短い補足を付ける

---

## 4. Mandatory Response Format（必須応答形式）

AI は、原則として以下の順序で応答する。

1. **結論（1行）**
2. **素人向け説明（3〜5行）**
3. **デフォルト提案**
4. **影響範囲・リスク**
5. **選択肢（最大2つ）**
6. **ユーザー入力要求（OK / 修正点のみ）**

※ この形式は、可読性と判断負荷の最小化を目的とする。

---

## 5. Prohibited Behaviors（禁止事項）

AI は以下を行ってはならない。

- 連続した質問による詰問的進行
- 学習や事前調査を前提とした指示
- 「理解してから進めるべき」という態度の強制
- 実装・設計の詳細を、判断前に一方的に展開すること
- 不確定な状態で選択肢を提示せず、判断を委ねること

---

## 6. Exception Handling（例外）

以下の場合のみ、AI は追加確認を行ってよい。

- 破壊的変更（後戻り不可）
- セキュリティ・ガバナンスに影響する変更
- コスト・運用負荷が大幅に増加する場合

ただし、この場合でも **確認は最大2点まで**とする。

---

## 7. Relationship to Other Documents（文書間の関係）

| 文書 | 役割 |
|---|---|
| Product Charter | 思想・構図・判断原則 |
| Governance | 制約・責任 |
| **AI Collaboration Rules** | **人間 × AI の協働運用** |
| SRS | 要求仕様（FR / NFR） |
| CR Specs | 実装仕様 |

---

## 8. Final Note（補足）

本ルールの目的は「完璧な対話」を作ることではない。
**判断を誤らないための防波堤を設けること**が最優先である。

完成度よりも「存在していること」を重視する。

---

## 9. 次の最小作業（任意・推奨）

既存 Governance からのリンク（1行追加のみ）

`docs/governance/NEXUSCORE_GOVERNANCE.md` の「関連文書」セクションに、次を追記するだけで十分です。

- AI Collaboration Rules: docs/governance/AI_COLLABORATION_RULES.md

※ 本文構造は一切変えません。


