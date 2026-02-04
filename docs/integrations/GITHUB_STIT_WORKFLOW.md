# GitHub STIT Workflow

## v1.0 ― GitHub プラットフォーム連携プロトコル

---

**目的**:
本ドキュメントは、Spec & Test Driven Iteration（STIT）をGitHubプラットフォーム上で運用するための
**ワークフロー定義**を定義する。

本ドキュメントは [STIT_STANDARD.md](../STIT_STANDARD.md) を基盤とし、
GitHub固有のIssue、Pull Request、Actions、Projectsとの連携ルールを規定する。

---

## 1. 目的と適用範囲

### 1.1 本ドキュメントの目的

STITの運用をGitHubプラットフォーム上で効率的かつ一貫して実施するためのルールを定義する。AIアシスタントがGitHub上の情報からコンテキストを正確に取得し、STITプロセスを適切に実行するためのガイドラインを提供する。

### 1.2 適用範囲

本ドキュメントは以下のGitHub機能との連携を定義する。

| 機能 | 用途 |
|------|------|
| Issues | STIT Gateway、仕様定義、Decision Log |
| Pull Requests | 実装、テスト、Review Gate |
| Projects | カンバンボード、スケジュール管理 |
| Actions | CI/CD、テスト実行、自动化 |
| Discussions | 設計議論、Q&A |

### 1.3 前提条件

本ドキュメントは [STIT_STANDARD.md](../STIT_STANDARD.md) のすべてのルールを継承する。STIT_STANDARD.md と本ドキュメントで矛盾が生じた場合、STIT_STANDARD.md が優先される。

### 1.4 リポジトリ情報

本ドキュメントは以下のリポジトリを前提とする。

| 項目 | 値 |
|------|-----|
| リポジトリURL | <https://github.com/fukukei23/NexusCore> |
| デフォルトブランチ | main |
| ブランチ保護 | PR必須、レビュー必須、テスト通過必須 |

---

## 2. Issue 運用ルール

### 2.1 ブランチ命名規則

すべての開発作業は、ブランチを作成して開始する。ブランチ名は以下の命名規則に従う。

| 接頭辞 | 用途 | 命名規則 | 例 |
|--------|------|----------|-----|
| `claude/` | AI開発ブランチ | `{接頭辞}/{cr-XXX}-{簡易説明}` | `claude/cr-nexus-051-b-retry-policy-mS11E` |
| `rescue/` | 救出用・再試行ブランチ | `{接頭辞}/{cr-XXX}_{日付}` | `rescue/cr-nexus-051-wip_20260112` |
| `feature/` | 機能開発（通常） | `{接頭辞}/{機能名}` | `feature/user-authentication` |
| `hotfix/` | 緊急修正 | `{接頭辞}/{修正内容}` | `hotfix/critical-security-fix` |

#### ブランチ作成フロー

```
[STIT Gateway Issue 作成]
    ↓
[ブランチ命名規則に従い作成]
    ↓
[実装・テスト]
    ↓
[PR 作成]
    ↓
[Review & Merge]
```

### 2.2 STIT Gateway Issue

すべての開発タスクは、STIT Gateway Issue として作成することを原則とする。Gate評価（コンテキスト存在確認、版の正当性確認）をIssue上で実施することで、チーム全体で判断の根拠を共有できる。

#### 2.1.1 Issue テンプレート

STIT Gateway Issue は以下の構造に従う。

```markdown
# STIT Gateway - [タスク名]

## ゲート評価

### Gate 1: コンテキスト存在確認

- [ ] システム設計コンテキストが明示されている
- [ ] プロジェクトの目的・制約が明示されている
- [ ] 変更対象が明確に定義されている

### Gate 2: 版の正当性確認

- [ ] 参照仕様がバージョン付きで確認可能
- [ ] 最終更新情報が明記されている

### 判定

- [ ] PASS → Spec定義へ
- [ ] BLOCK → 不足情報を要求
```

#### 2.1.2 タイトル規則

STIT Gateway Issue のタイトルは `[STIT-GATE]` 接頭辞を付与する。例：`[STIT-GATE] ユーザー認証機能の改善`

### 2.2 仕様定義 Issue

Gate評価 PASS 後、仕様定義は Issue または Issue 内のセクションとして作成する。仕様定義 Issue は `[STIT-SPEC]` 接頭辞を付与する。

#### 2.2.1 必須セクション

| セクション | 内容 |
|-----------|------|
| 期待される挙動 | 正常系・異常系すべてを明記 |
| 失敗時・境界条件 | エラー処理、例外パターンを明記 |
| テスト観点 | 合否判定基準を明記 |
| 未定義挙動 | 未定義となる条件を明記 |

### 2.3 Decision Log Issue

Gate BLOCK、複数の選択肢、Reject/Deferred の場合、Decision Log を Issue として記録する。Decision Log Issue は `[STIT-DECISION]` 接頭辞を付与する。

#### 2.3.1 記録ルール

- 既存の Decision Log  Issue へのコメントとして記録（append-only）
- 判断理由を必ず明記
- 日時と対象タスクを明記

---

## 3. Pull Request 運用ルール

### 3.1 PR 作成規則

STIT に基づき、Spec・Test の定義完了後に PR を作成する。PR は実装とテストを含み、Review Gate への提出として機能する。

#### 3.1.1 PR タイトル規則

PR タイトルは対応する STIT Issue 番号を含める。例：`feat: ユーザー認証機能の追加 (#42)`

#### 3.1.2 PR Description テンプレート

```markdown
## 関連 STIT Issue

- STIT Gateway: #[番号]
- Spec 定義: #[番号]

## マージ時に自動クローズ

```

Fixes #[番号]

```

PR マージ時に指定した Issue を自動クローズする。

## 実装概要

[実装内容の要約]

## テスト結果

- [ ] ユニットテスト: passed/failed
- [ ] 統合テスト: passed/failed
- [ ] 既存テスト: all passed

## Review 要望事項

[レビュアーに確認してほしい観点]
```

### 3.2 Review Gate

PR は GitHub のレビュー機能を使用して Independent Review Gate を実施する。Reviewer は STIT Gateway Issue および Spec 定義を参照し、仕様に沿っているか確認する。

#### 3.2.1 承認条件

| 条件 | 確認項目 |
|------|----------|
| 仕様準拠 | Spec 定義との整合性 |
| テスト品質 | 合否判定基準の充足 |
| コード品質 | コーディング規約、テストカバレッジ |
| ドキュメント | 必要に応じたAPIドキュメント更新 |

#### 3.2.2 レビュー結果

- **Approve**: Review Gate PASS、Merge 可能
- **Request Changes**: 不足・問題あり、修正后再レビュー
- **Comment**: 軽微な指摘・質問

### 3.3 マージ戦略

Main ブランチへの直接マージは禁止し、Pull Request を介す。Squash Merge を推奨し、コミット履歴を簡潔に保つ。

---

## 4. GitHub Actions 自動化

### 4.1 CI/CD パイプライン

STIT の Test フェーズを GitHub Actions で自動化する。

#### 4.1.1 必須ワークフロー

```yaml
name: STIT Test Pipeline

on:
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Tests
        run: pytest --stit-mode
      - name: Report Results
        run: pytest --report
```

#### 4.1.2 テスト結果レポート

テスト実行結果は PR にコメントとして自動投稿する。テスト結果レポートは STIT Report として保存する。

### 4.2 STIT ゲート自動化

GitHub Actions で Gate 評価の一部を自動化する。

| ゲート | 自動化項目 |
|--------|-----------|
| Gate 2: 版の正当性確認 | 依存関係のバージョン確認 |
| Gate 4: テスト可能性 | テストの存在確認 |
| Review Gate | 必須ファイルの存在確認 |

---

## 5. GitHub Projects 運用

### 5.1 カンバンボード構造

GitHub Projects を使用して、STIT の進行状況を可視化する。

| カラム | STIT フェーズ |
|--------|---------------|
| Backlog | タスク検討中 |
| STIT Gateway | ゲート評価待ち |
| Spec 定義 | 仕様策定中 |
| Test 定義 | テスト設計中 |
| In Progress | 実装中 |
| Review | レビュ中 |
| Done | 完了 |

### 5.2 Issue  Projects 連携

各 STIT Issue を Projects のカードとして管理し、フェーズ移行時にカードを移動する。

---

## 6. DECISION_LOGS 運用

### 6.1 Decision Log の保存場所

Decision Log は GitHub Discussions または Wiki に保存することを推奨する。プロジェクトに応じて Issue や専用リポジトリも可。

#### 6.1.1 Decision Log エントリテンプレート

```markdown
# Decision Log - [日付]

## ケース

[Gate BLOCK / 複数選択肢 / Reject / Deferred]

## 状況

[背景・問題定義]

## 選択肢

| 選択肢 | メリット | デメリット |
|--------|---------|-----------|
| A | ... | ... |
| B | ... | ... |

## 決定

[選択したオプションと理由]

## 判断根拠

[詳細な判断理由]
```

### 6.2 記録タイミング

Decision Log は以下のタイミングで記録する。

| タイミング | 内容 |
|-----------|------|
| Gate BLOCK 時 | 不足情報の特定、推定原因 |
| 選択肢比較時 | 各選択肢の評価、選択理由 |
| Reject/Deferred 時 | 拒否・延期理由、代替案 |

---

## 7. ファイル配置規則

### 7.1 推奨ディレクトリ構造

```
root/
  GOVERNANCE/
    SPEC_TEST_DRIVEN_ITERATION.md  ← STIT 本体
  docs/
    STIT_STANDARD.md               ← 汎用STIT定義（配布用）
    integrations/
      GITHUB_STIT_WORKFLOW.md      ← GitHub連携（本ファイル）
  .github/
    workflows/
      stit-test-pipeline.yml       ← CI/CD
```

### 7.2 テンプレート配置

Issue テンプレート、PR テンプレートは `.github/` ディレクトリに配置する。

```
.github/
  ISSUE_TEMPLATE/
    stit-gate.md
    stit-spec.md
    stit-decision.md
  PULL_REQUEST_TEMPLATE.md
  workflows/
    stit-test-pipeline.yml
```

#### 7.2.1 Issue テンプレート例

**.github/ISSUE_TEMPLATE/stit-gate.md**

```markdown
---
name: STIT Gateway Issue
about: STIT Gateway 評価用の Issue テンプレート
title: "[STIT-GATE] "
labels: "stit-gate"
---

## ゲート評価

### Gate 1: コンテキスト存在確認

**システム設計コンテキスト**
[システム全体構造と対象変更の論理的範囲を記述]

**プロジェクトの目的・制約**
[何のための変更か、リスク許容度を記述]

**変更対象**
[何を変更するか、明示的に含まないものを記述]

### Gate 2: 版の正当性確認

| 参照情報 | バージョン | 最終更新 |
|---------|-----------|----------|
| [仕様書] | v1.0 | 2026-01-01 |
| [設計書] | v2.1 | 2026-01-15 |

### 判定

- [ ] PASS → Spec定義へ移行
- [ ] BLOCK → 不足情報を要求
```

**.github/ISSUE_TEMPLATE/stit-spec.md**

```markdown
---
name: STIT Spec Definition
about: 仕様定義用の Issue テンプレート
title: "[STIT-SPEC] "
labels: "stit-spec"
---

## 期待される挙動

[正常系の動作を明記]

## 失敗時・境界条件

[エラー処理、例外パターンを明記]

## テスト観点

[合否判定基準を明記]

## 未定義挙動

[未定義となる条件を明記]
```

#### 7.2.2 PR テンプレート例

**.github/PULL_REQUEST_TEMPLATE.md**

```markdown
## 関連 STIT Issue

- STIT Gateway: #[番号]
- Spec 定義: #[番号]

## マージ時に自動クローズ

```

Fixes #[番号]

```

## 実装概要

[実装内容の要約]

## 変更ファイル

[変更したファイルのリスト]

## テスト結果

- [ ] ユニットテスト: passed/failed
- [ ] 統合テスト: passed/failed
- [ ] 既存テスト: all passed

## Review 要望事項

[レビュアーに確認してほしい観点]
```

---

## 8. バージョン履歴

- **v1.1**: ブランチ命名規則、Issue/PR連携、テンプレート例を追加
- **v1.0**: 初版

---

**End of GitHub STIT Workflow v1.1**
