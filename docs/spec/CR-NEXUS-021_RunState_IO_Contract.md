# CR-NEXUS-021: RunState I/O Contract

SRS Traceability

Related SRS: docs/srs/NEXUSCORE_SRS.md

This CR satisfies: FR-1; FR-4; FR-6; NFR-1; NFR-7

## 1. 概要（Overview）

本 CR は、RunState を中心とした Run / Pause / Resume における **入出力契約（I/O Contract）**を定義する。

ここでの I/O とは以下を指す。

- **入力（Input）**: 外部から与えられる「イベント（Event）」であり、状態遷移を引き起こす。
- **出力（Output）**: 外部に提示される「RunState の投影（Projection）」であり、監査・運用・UI・API が参照する。

本 CR は **契約の定義のみ**であり、実装コードの変更・UI 仕様・ログ形式の統一は要求しない。

## 2. 前提（Dependencies / Alignment）

本 CR は以下の CR を前提とし、整合する。

- CR-NEXUS-019: Status / State Machine Contract（status 語彙と遷移）
- CR-NEXUS-018: Resume Failure Explainability Contract（FAILED の説明責務）
- CR-NEXUS-020: RunState JSON Schema Contract（RunState スキーマ正本）

## 3. 基本原則（I/O Principles）

- **RunState スキーマの正本は CR-NEXUS-020** とする
- **Status 語彙は CR-NEXUS-019** に従う
- **Explainability は CR-NEXUS-018** に従う
- **Orchestrator を I/O の正本にしない**
- 入力はイベント、出力は RunState 投影である（I/O の分離）

## 4. 用語（Terms）

- **Event（イベント）**: 状態遷移を要求する外部入力（例: start, pause, resume, stop, abort）
- **Projection（投影）**: RunState を外部に提示するための表現（CLI 表示/API レスポンス/Web 表示など）
- **I/O 正本（Source of Truth）**: 入出力契約の主体（誰が入力を解釈し、状態を更新し、出力を提示するか）

## 5. I/O 正本（Source of I/O Contract）

### 5.1 正本の所在

- I/O 契約の正本は **Runner** にある。
- Orchestrator は I/O 契約の正本にならない。
- RunState は永続化された事実データであり、I/O の解釈主体ではない。

### 5.2 役割分担（要点）

- **Runner**: Event を受け取り解釈し、RunState（CR-020）を更新し、外部へ投影を提供する。
- **Orchestrator**: Runner から与えられた実行入力に従ってフェーズ処理を実行する（I/O 契約の主体ではない）。

## 6. 入力（Input Contract）: Event

### 6.1 入力は「イベント」である

RunState の I/O において、外部入力は以下の性質を持つ。

- 直接「状態（status）」を指定するのではなく、**イベントを指定する**
- イベントが **状態遷移**を引き起こす（遷移の契約は CR-019）

### 6.2 チャネル別入力（CLI / API / Web）

#### CLI

- CLI はイベントを入力として受け取る（例: start, resume, stop, abort）。
- 入力は「実行要求」または「再開要求」であり、status の直接指定ではない。

#### API

- API はイベント入力を受け取る（例: resume_requested）。
- API は status の直接書き換え（RUNNING へ強制遷移等）を契約として許容しない。

#### Web

- Web UI はイベント入力を発行する（例: Pause ボタン→pause_requested）。
- Web UI は status の直接書き換えを契約として許容しない。

## 7. 出力（Output Contract）: RunState Projection

### 7.1 出力は「RunState 投影」である

- 外部出力は RunState（CR-020）の **投影**として表現される。
- 投影は、チャネル（CLI / API / Web）ごとに表示形式は異なり得るが、根拠データは RunState に整合すること。

### 7.2 チャネル別出力（CLI / API / Web）

#### CLI

- CLI は RunState の主要フィールド（例: run_id, status, authority_level, next_phase, updated_at）を投影する。
- FAILED の場合、可能な範囲で Explainability（CR-018）の要素（What/Why/Next Action）を投影し得る。

#### API

- API は RunState（CR-020）と整合した投影を返す。
- status 語彙は CR-019 と一致する。
- FAILED の場合、last_error（CR-020）を含む投影が望ましい（形式は本 CR で固定しない）。

#### Web

- Web は RunState を投影し、運用者が状態（status）を分類できる表示を提供する。
- FAILED の場合、Explainability（CR-018）に沿う情報を投影し得る。

## 8. 禁止事項（Prohibited）

- Orchestrator を I/O 正本として扱うこと（入力解釈・status 更新主体・外部投影の正本にしない）
- 外部入力として status を直接指定し、Runner の状態遷移契約（CR-019）をバイパスすること
- RunState スキーマ（CR-020）と矛盾する投影を「正」として扱うこと
- Explainability（CR-018）と矛盾する失敗表現（FAILED の意味・分類の破壊）
- 本 CR に TODO や実装提案を追加すること
- core/orchestrator.py の変更を前提とすること

## 9. 非目標（Explicit Non-Goals）

- API エンドポイント仕様（パス、認証、レスポンス形式）の確定
- UI 表示の詳細仕様
- ログフォーマットの統一
- 具体的なイベント名の固定（CR-019 の遷移表を超える詳細化）

## 10. 完了条件（Done Definition）

- CLI / API / Web の入力・出力契約が整理されている
- 禁止事項が明文化されている
- CR-015〜020 と整合している


