# CR-NEXUS-017: Resume Orchestrator Reconstruction Model

SRS Traceability

Related SRS: docs/srs/NEXUSCORE_SRS.md

This CR satisfies: FR-1; FR-2; NFR-1; NFR-3

## 1. 概要（Overview）

本 CR は、Pause / Resume における **Orchestrator 再構築（Reconstruction）モデル**を「設計契約（Design Contract）」として定義する。

本 CR は **設計定義のみ**であり、実装コードには一切触れない。

## 2. 背景（Background）

CR-NEXUS-015 により、Runner によるフェーズ境界停止（Pause）と `run_id` による Resume が成立した。
一方で、Resume 時に「同一 Orchestrator インスタンスの継続」か「Orchestrator の再構築」かが明文化されていないと、運用・監査・障害対応において誤解が生じる。

本 CR では Resume のモデルを **明示的に再構築方式**として固定し、RunState と責務境界の正本を定義する。

## 3. 用語（Terms）

- **Runner**: AuthorityLevel の解釈、停止判断、RunState 永続化、Resume 制御など、実行制御の外側レイヤ。
- **Orchestrator**: 既存の実行エンジン（core）。フェーズ実行の責務を担うが、Pause/Resume の運用契約の正本にはならない。
- **RunState**: Pause/Resume のための永続状態（再開に必要な最小情報を保持する）。
- **Reconstruction（再構築）**: Resume の度に Orchestrator を「新しいプロセス / 新しいインスタンス」として構築し直し、RunState を入力として再開する方式。

## 4. スコープ（In Scope / Out of Scope）

### In Scope

- Resume 時に Orchestrator が再構築されることの明文化
- RunState が唯一の再開正本（Single Source of Truth）であることの明文化
- Runner / Orchestrator の責務境界（Contract Boundary）の明文化

### Out of Scope

- RunState 保存形式の変更
- Resume ロジック・フェーズ制御の再設計
- core/orchestrator.py の変更
- API 化・分散実行・ワーカー管理（別 CR）

## 5. 設計契約（Design Contract）

### 5.1 Resume 時の Orchestrator 再構築（必須契約）

- Resume は **Orchestrator の継続実行（同一インスタンスの再開）**ではない。
- Resume は **Orchestrator を再構築し、RunState を入力として再開する**。
- したがって、Pause と Resume の間に存在するインメモリ状態（プロセス内状態）に依存してはならない。

この契約により、以下が成立する。

- OS プロセス再起動や CLI 再実行でも Resume が成立する
- 実行環境差分（端末・シェル・再起動）に影響されにくい
- 監査・説明責任の観点で「RunState に基づく再開」であることを明確化できる

### 5.2 RunState の正本性（Single Source of Truth）

- Resume の判断と再開点（例: `next_phase`）は **RunState を唯一の正本**とする。
- Runner は Resume 時に RunState を読み取り、その内容に従って再開を試行する。
- CLI の引数（例: `--authority-level`）は、Resume 時には **正本にならない**（RunState の値に従う）。

### 5.3 Runner / Orchestrator の責務境界（Boundary）

#### Runner の責務（正本）

- AuthorityLevel の意味解釈と停止方針の決定
- 停止判断（どのフェーズ境界で止めるか、止まった理由の説明）
- 外部 stop/pause 指示の取り込み（SessionController 等の外部指示を利用する場合を含む）
- RunState の永続化・読み取り・更新
- Resume 時の再開入力の構築（RunState から再開点を決める）
- 監査・運用上の識別子（run_id）をユーザーに提示する UX の提供（※出力仕様は別 CR で定義）

#### Orchestrator の責務（非正本）

- フェーズ実行（与えられた入力に基づく手続き実行）
- 内部フェーズの詳細処理（Requirement→Plan→Architecture→...）
- Runner が指定した開始点からの実行（ただし Orchestrator 自身が Pause/Resume の契約正本にならない）

#### 禁止（この契約が要求する禁止事項）

- Orchestrator が AuthorityLevel を解釈し、停止判断の正本になること
- Orchestrator が RunState 永続化の正本になること
- Resume を「前回のインメモリ状態の継続」を前提にすること

## 6. Resume の概念フロー（Conceptual Flow）

本 CR は実装を要求しないが、責務境界を明確にするため概念フローを定義する。

1. ユーザーが `run_id` を指定して Resume を要求する
2. Runner が RunState を読み取る（RunState が正本）
3. Runner が RunState に基づき、再開点（例: `next_phase`）と制御ポリシー（例: `authority_level`）を確定する
4. Runner が Orchestrator を **新規に構築**し、再開点から実行を試行する
5. 完了または失敗に応じて、Runner が RunState を更新する（RunState が正本）

## 7. 非機能要件（NFR）

- `core/orchestrator.py` は無変更であること（凍結前提）
- 既存テストの意味論を壊さないこと
- `run_id` により監査・説明が可能であること（識別子として一意に追跡可能）

## 8. リスク・制約

- RunState が最小であるほど、再構築方式では「再開できる情報の範囲」が限定される。
- ただし本 CR は「再構築方式である」という契約を定義するものであり、どの情報を RunState に含めるかは別 CR の対象とする。

## 9. 完了条件（Done Definition）

- Resume 時に Orchestrator が再構築されることが明文化されている
- RunState が唯一の再開正本であることが示されている
- Runner / Orchestrator の責務境界が明確である


