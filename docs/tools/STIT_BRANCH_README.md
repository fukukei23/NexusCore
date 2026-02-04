# STIT Branch Automation CLI Tool

## 概要

STIT（Spec & Test Driven Iteration）ワークフローのためのブランチ管理CLIツールです。命名規則の自動適用、リスク緩和機能、人間承認プロセスをサポートします。

GitHubリポジトリ: <https://github.com/fukukei23/NexusCore>

---

## 特徴

- **命名規則の自動適用**: `claude/`, `rescue/`, `feature/`, `hotfix/` プリフィックスをサポート
- **リスク緩和機能**: Dry-runモード、読み取り専用モード、入力検証
- **人間承認プロセス**: Phase 3完全自動化に向けた承認リクエスト機能
- **設定ファイル**: ユーザー固有の設定を保存可能
- **クロスプラットフォーム**: Windows、macOS、Linux対応

---

## インストール

### 方法1: 直接実行

```bash
# 実行権限を付与
chmod +x tools/stit_branch.py

# パスを通す場合
export PATH="$PATH:$(pwd)/tools"

# 実行
stit_branch.py create -t cr-051 -d retry-policy
```

### 方法2: pip install（推奨）

```bash
# インストール
pip install -e .

# 実行
stit-branch create -t cr-051 -d retry-policy
```

### 必要条件

- Python 3.8以上
- Git
- GitHubアカウント

---

## 使用方法

### ブランチの作成

```bash
# 推奨: 常に 먼저 Dry-run を実行
stit-branch create -t cr-051 -d retry-policy --dry-run

# ブランチを作成
stit-branch create -t cr-051 -d retry-policy

# ブランチを作成してプッシュ
stit-branch create -t cr-051 -d retry-policy --push
```

### ブランチ名の検証

```bash
# ブランチ名を検証
stit-branch validate -b claude/cr-051-retry-policy

# 詳細出力付き検証
stit-branch validate -b claude/cr-051-retry-policy --verbose
```

### ブランチ一覧

```bash
# 全ブランチ一覧
stit-branch list

# 特定プリフィックスでフィルタ
stit-branch list -p claude

# リモートブランチ一覧
stit-branch list --remote
```

### ブランチの削除

```bash
# ブランチを削除（マージ済みのみ）
stit-branch delete -b claude/cr-051-retry-policy

# 強制削除
stit-branch delete -b claude/cr-051-retry-policy --force
```

### 承認リクエスト（Phase 3）

```bash
# 承認リクエストを作成
stit-branch request -b claude/cr-051 -t cr-051 -d "retry policy implementation"

# リクエストを承認
stit-branch approve -r SR-20260204120000 -a "human-reviewer"

# リクエストを却下
stit-branch reject -r SR-20260204120000 -a "human-reviewer" -R "詳細な説明が必要です"

# 保留中リクエスト一覧
stit-branch pending
```

### 設定管理

```bash
# 現在の設定を表示
stit-branch config --show

# デフォルトプリフィックスを設定
stit-branch config --default-prefix claude
```

---

## コマンドリファレンス

### create - ブランチ作成

```bash
stit-branch create -t <task-id> -d <description> [options]
```

| オプション | 短縮形 | 説明 |
|-----------|--------|------|
| --task-id | -t | タスクID（例: cr-051）必須 |
| --desc | -d | 説明 必須 |
| --prefix | -p | プリフィックス（claude/rescue/feature/hotfix） |
| --dry-run | -n | 実際の操作を実行せず表示のみ |
| --push | -u | 作成後にリモートにプッシュ |

### validate - ブランチ名検証

```bash
stit-branch validate -b <branch-name> [options]
```

| オプション | 短縮形 | 説明 |
|-----------|--------|------|
| --branch-name | -b | 検証するブランチ名 必須 |
| --verbose | -v | 詳細出力を有効化 |

### list - ブランチ一覧

```bash
stit-branch list [options]
```

| オプション | 短縮形 | 説明 |
|-----------|--------|------|
| --prefix | -p | プリフィックスでフィルタ |
| --remote | -r | リモートブランチを表示 |

### delete - ブランチ削除

```bash
stit-branch delete -b <branch-name> [options]
```

| オプション | 短縮形 | 説明 |
|-----------|--------|------|
| --branch-name | -b | 削除するブランチ名 必須 |
| --force | -f | 強制削除（マージ済みチェックをスキップ） |
| --dry-run | -n | 実際の操作を実行せず表示のみ |

### request - 承認リクエスト作成

```bash
stit-branch request -b <branch> -t <task-id> -d <desc> [options]
```

| オプション | 短縮形 | 説明 |
|-----------|--------|------|
| --branch | -b | ブランチ名 必須 |
| --task-id | -t | タスクID 必須 |
| --desc | -d | 説明 必須 |
| --requester | -r | リクエスト元（デフォルト: AI） |

### approve - リクエスト承認

```bash
stit-branch approve -r <request-id> -a <approver> [options]
```

| オプション | 短縮形 | 説明 |
|-----------|--------|------|
| --request-id | -r | リクエストID 必須 |
| --approver | -a | 承認者名 必須 |
| --comment | -c | コメント（オプション） |

### reject - リクエスト却下

```bash
stit-branch reject -r <request-id> -a <rejecter> -R <reason>
```

| オプション | 短縮形 | 説明 |
|-----------|--------|------|
| --request-id | -r | リクエストID 必須 |
| --rejecter | -a | 却下者名 必須 |
| --reason | -R | 却下理由 必須 |

### pending - 保留中リクエスト一覧

```bash
stit-branch pending
```

### config - 設定管理

```bash
stit-branch config [options]
```

| オプション | 短縮形 | 説明 |
|-----------|--------|------|
| --show | -s | 現在の設定を表示 |
| --default-prefix | -p | デフォルトプリフィックスを設定 |

---

## 命名規則

### プリフィックス

| プリフィックス | 用途 | 例 |
|---------------|------|-----|
| `claude/` | AI開発ブランチ | `claude/cr-051-retry-policy` |
| `rescue/` | 救出用・再試行ブランチ | `rescue/cr-051-wip_20260112` |
| `feature/` | 機能開発（通常） | `feature/user-authentication` |
| `hotfix/` | 緊急修正 | `hotfix/security-fix` |

### タスクID形式

- 形式: `cr-XXX`（3桁の数字）
- 例: `cr-051`, `cr-100`, `cr-999`

### 説明フィールド規則

- 使用文字: 半角英数字とダッシュ（-）のみ
- 禁止文字: スペース、アンダースコア、特殊文字、大文字
- 長さ: 50文字以内推奨

### 正解・不正解の例

| 不正解 | 正解 | 理由 |
|--------|------|------|
| `feature/UserAuth` | `feature/user-authentication` | 大文字は使用しない |
| `claude/cr_051` | `claude/cr-051` | アンダースコアは使用しない |
| `my-branch` | `claude/cr-051-my-branch` | プリフィックスが必要 |
| `claude/cr-051 retry policy` | `claude/cr-051-retry-policy` | スペースは使用しない |

---

## リスク緩和機能

### Dry-run モード

常にDry-runを最初に実行することを強く推奨：

```bash
# 何が起きるか確認
stit-branch create -t cr-051 -d retry-policy --dry-run

# 問題なければ実際の実行
stit-branch create -t cr-051 -d retry-policy --push
```

### 読み取り専用モード

安全性を確認するためのモード：

```bash
stit-branch create -t cr-051 -d retry-policy --read-only
```

### 入力検証

自動的に適用される検証：

- 危険なパターンの検出（`..`, `~`, `^` など）
- プリフィックスの検証
- 長さ制限（100文字以内）
- スペース検出
- 大文字検出

### ブランチ保護

以下の操作は保護されています：

- mainブランチへの直接プッシュ
- 存在しないブランチへの操作
- 不正な命名規則の適用

---

## 設定ファイル

ユーザー固有の設定は `~/.stit_branch_config.json` に保存されます：

```json
{
  "default_prefix": "claude"
}
```

設定可能なオプション：

| オプション | 説明 | デフォルト |
|------------|------|-----------|
| default_prefix | デフォルトのプリフィックス | claude |

---

## 承認プロセス（Phase 3）

### ワークフロー

```
[AI ブランチ作成]
    ↓
[--dry-run で確認]
    ↓
[承認リクエスト作成]
    ↓
[人間 承認/却下]
    ↓
[承認時: 自動実行]
[却下時: AI 再考]
```

### 承認リクエストの管理

```bash
# リクエストを作成
stit-branch request -b claude/cr-051 -t cr-051 -d "retry policy"

# 保留中リクエストを確認
stit-branch pending

# 承認
stit-branch approve -r SR-20260204120000 -a "human-name"

# 却下（理由を必ず記載）
stit-branch reject -r SR-20260204120000 -a "human-name" -R "理由"
```

### 承認ファイル

承認リクエストは `.stit_approvals.json` に保存されます：

```json
{
  "SR-20260204120000": {
    "branch_name": "claude/cr-051",
    "task_id": "cr-051",
    "description": "retry policy",
    "requester": "AI",
    "status": "approved",
    "created_at": "2026-02-04T12:00:00",
    "approved_by": "human-name",
    "approved_at": "2026-02-04T12:30:00",
    "comments": []
  }
}
```

---

## GitHub統合

### Issue連携

- STIT Gateway Issue を先に作成
- Issue番号をブランチ名に反映（cr-XXX）
- PR作成時にIssueへのリンクを含める

### Pull Request

- PRタイトルにIssue番号を含める: `feat: 認証機能 (#42)`
- PR DescriptionにSTIT Issueをリンク
- `Fixes #番号` でマージ時の自動クローズを設定

### ブランチ保護ルール

GitHubで以下のルールを設定することを推奨：

- mainブランチへの直接プッシュ禁止
- PR必須
- レビュー必須
- テスト通過必須

---

## トラブルシューティング

### エラー: "Git command not found"

Gitがインストールされていません。Gitをインストール后再実行してください。

### エラー: "Remote repository not found"

リモートリポジトリが設定されていません：

```bash
git remote add origin https://github.com/fukukei23/NexusCore.git
```

### エラー: "Permission denied"

GitHubのアクセス権限を確認してください。Personal Access Tokenが必要な場合があります。

### エラー: "Branch already exists"

同じ名前のブランチがすでに存在します。別の説明を使用するか、既存ブランチを削除后再実行してください。

### 色が正しく表示されない

Windowsの場合、以下のコマンドを実行后再実行してください：

```bash
# Command Prompt
reg add HKCU\Console /v VirtualTerminalLevel /t REG_DWORD /d 1 /f

# PowerShell
$host.UI.RawUI.VirtualTerminalLevel = $True
```

---

## 開発者向け情報

### ファイル構成

```
tools/
  stit_branch.py           # CLIツール本体

docs/
  integrations/
    GITHUB_STIT_WORKFLOW.md  # GitHub STITワークフロー

.cursor/
  rules/
    nexuscore-stit-compliance.mdc  # Cursorルール
```

### テスト実行

```bash
# Dry-run テスト
python tools/stit_branch.py create -t cr-999 -d test-feature --dry-run

# 検証テスト
python tools/stit_branch.py validate -b claude/cr-999-test-feature
```

### 貢献

バグ報告や機能要望は、GitHubのIssueで受け付けています。

---

## 関連ドキュメント

- [GitHub STIT Workflow](../integrations/GITHUB_STIT_WORKFLOW.md)
- [STIT Standard](../STIT_STANDARD.md)
- [STIT Compliance (.cursor/rules)](../../.cursor/rules/nexuscore-stit-compliance.mdc)
- [Phase 3 自動化計画](../plans/PHASE3_HUMAN_APPROVED_AUTOMATION.md)

---

## ライセンス

NexusCoreプロジェクトの一部として、MITライセンスの下で配布されています。

---

## バージョン履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|----------|
| 1.1.0 | 2026-02-04 | 承認システム、追加コマンド、設定ファイル対応 |
| 1.0.0 | 2026-02-04 | 初版 |

---

**STIT Branch Automation v1.1.0**
