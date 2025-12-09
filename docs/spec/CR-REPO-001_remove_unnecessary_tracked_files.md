# CR-REPO-001: リポジトリから不要な追跡ファイルを削除

**作成日**: 2025-12-09
**ステータス**: Draft
**優先度**: High
**影響範囲**: Repository Structure, CI/CD Performance
**担当者**: Repository Maintainer

---

## 1. 背景と目的

### 1.1 現状の問題

NexusCore リポジトリには、本来 Git 管理対象外とすべきファイルが大量に追跡されています。

**現状の統計**:
- 総追跡ファイル数: **9,537 ファイル**
- 不要ファイル数: **約 6,990 ファイル** (73.3%)
- 不要ファイルサイズ: **約 113 MB**

**主な問題**:
1. ⚠️ **リポジトリ肥大化**: クローン・プル時間が増大
2. ⚠️ **CI/CD 遅延**: GitHub Actions で不要ファイルをチェックアウト
3. ⚠️ **開発者体験の悪化**: 差分レビューに無関係なファイルが含まれる
4. ⚠️ **セキュリティリスク**: ログファイルに機密情報が含まれる可能性
5. ⚠️ **依存関係の衝突**: node_modules がコミットされると、各環境で不整合

### 1.2 目的

- ✅ リポジトリサイズを約 73% 削減 (6,990 ファイル削除)
- ✅ .gitignore を修正し、今後の誤コミット防止
- ✅ CI/CD パフォーマンスを改善
- ✅ 開発者体験を向上

---

## 2. 削除対象ファイル・ディレクトリ

### 2.1 対象リスト

| カテゴリ | パス | ファイル数 | サイズ | 理由 |
|---------|------|-----------|--------|------|
| **node_modules (ルート)** | `node_modules/` | 3,247 | 39 MB | npm 依存関係（package.json で管理） |
| **node_modules (VSCode拡張)** | `vscode-extension/node_modules/` | 3,075 | 18 MB | 同上 |
| **エクスポート成果物** | `exports/` | 584 | 56 MB | 一時的な生成物 |
| **ログファイル** | 複数箇所 | 30 | < 1 MB | 実行時ログ（追跡不要） |
| **バックアップファイル** | `.env.bak` | 1 | < 1 KB | 機密情報を含む可能性 |
| **ZIPファイル** | `vscode-extension.zip` など | 12 | 数 MB | ビルド成果物 |
| **その他不明ファイル** | `8.0`, `MONCLER_OFFICIAL` など | ~50 | < 1 MB | 用途不明 |
| **合計** | - | **約 6,990** | **約 113 MB** | - |

### 2.2 詳細な対象パス

#### A. node_modules 関連（6,326 ファイル）

```
node_modules/
├── .bin/
├── @borewit/
├── @inquirer/
├── @isaacs/
├── @lukeed/
├── @nestjs/
├── @nuxt/
├── @openapitools/
├── @tokenizer/
├── @tootallnate/
├── agent-base/
├── ansi-*/
├── axios/
├── ... (計 147 パッケージ)

vscode-extension/node_modules/
├── @eslint/
├── @eslint-community/
├── @humanwhocodes/
├── @types/
├── acorn/
├── eslint/
├── typescript/
├── ... (計 200+ パッケージ)
```

**判断基準**:
- ✅ `package.json` / `package-lock.json` で依存関係を管理
- ✅ 各開発者が `npm install` で復元可能
- ✅ Git 追跡は不要（NPM レジストリから取得）

#### B. exports/ ディレクトリ（584 ファイル）

```
exports/
├── NexusCore_gemini-chronicle_20251116_180001.zip
├── NexusCore_gemini-chronicle_20251116_205543.zip
├── NexusCore_gemini-chronicle_20251116_205939.zip
├── NexusCore_gemini-chronicle_20251116_210446.zip
├── NexusCore_gemini-chronicle_20251116_213018.zip
├── NexusCore_gemini-chronicle_20251116_213119.zip
├── NexusCore_gpt5-zip_20251116_215341.zip
├── NexusCore_gpt5-zip_20251116_215341/    # 展開済みディレクトリ（大量ファイル）
│   ├── .env.bak
│   ├── .coverage
│   ├── codex_history/
│   ├── src/
│   └── ...
├── NexusCore_export_run_20251116_210924.txt
└── NexusCore_export_run_20251116_213633.txt
```

**判断基準**:
- ✅ エクスポート成果物（一時的な生成物）
- ✅ CI/CD やローカルビルドで自動生成される
- ✅ 履歴管理する価値なし

#### C. ログファイル（30 ファイル）

```
.env.bak                                     # 機密情報リスク ⚠️
.logs/genesis_analyzer.log
launch_dev.debug.log
nexus_core_run.log
codex_history/
├── 20251115-064305_success_run.log
├── 20251115-065745_success_run.log
├── ... (17 個)
logs/orchestrator/
├── orchestrator_1763437158.log
├── orchestrator_1763473821.log
├── ... (8 個)
src/nexuscore/gradio_app/logs/app_20250806.log
src/sandbox_output/test_result.log
tools/analyzer.log
```

**判断基準**:
- ✅ 実行時に生成されるログ
- ⚠️ `.env.bak` は機密情報（API キー）を含む可能性
- ✅ `.gitignore` に `*.log` があるが、追跡済み（後述の手順で削除）

#### D. ZIPファイル（12 ファイル）

```
vscode-extension.zip                         # 11.7 MB
tools/exports/NexusCore_gemini_20250803_134101.zip
tools/exports/NexusCore_gemini_20250803_134101/COMBINED_CODE.zip
tools/exports/NexusCore_source_20250803_131253.zip
tools/exports/source_20250803_114325.zip
```

**判断基準**:
- ✅ ビルド成果物・バックアップ
- ✅ Git LFS でも管理不要（再生成可能）

#### E. その他不明ファイル

```
8.0                                          # 内容不明
MONCLER_OFFICIAL                             # 空ファイル
test_localsystem.txt                         # テスト用一時ファイル
how mainREADME.md  Set-Clipboard             # 謎のファイル名（スペース含む）
```

**判断基準**:
- ❓ 用途不明
- ✅ 削除して問題ないと判断

---

## 3. 実装手順

### 3.1 事前準備

#### ステップ 0: バックアップ作成（任意）

```bash
# 現在のブランチを別名で保存
git branch backup/before-cleanup-$(date +%Y%m%d)

# または、リモートにバックアップブランチをプッシュ
git push origin HEAD:backup/before-cleanup-$(date +%Y%m%d)
```

#### ステップ 1: 作業ブランチ作成

```bash
git checkout -b feature/remove-unnecessary-tracked-files
```

### 3.2 .gitignore の修正

#### 修正内容

既存の `.gitignore` に以下を追加：

```diff
diff --git a/.gitignore b/.gitignore
index xxxx..yyyy 100644
--- a/.gitignore
+++ b/.gitignore
@@ -1,3 +1,10 @@
+# ============================================================
+# Node.js dependencies (CR-REPO-001)
+# ============================================================
+node_modules/
+**/node_modules/
+package-lock.json  # ← オプション: チーム方針による
+
 # --- Secrets ---
 # APIキーやパスワードなどの秘密情報
 .env
@@ -89,9 +96,16 @@
 *.log

-# バックアップ・エクスポート
+# ============================================================
+# Exports and Backups (CR-REPO-001)
+# ============================================================
+# エクスポートディレクトリ全体を除外
+exports/
+!exports/.gitkeep
+
+# バックアップファイル
 NexusCore_backup.zip
-exports/*.zip
+*.bak

 # 一時ファイル
 *.tmp
@@ -104,3 +118,12 @@

 # ローカルデータベース
 nexus_local.db
+
+# ============================================================
+# Unknown files (CR-REPO-001)
+# ============================================================
+8.0
+MONCLER_OFFICIAL
+test_localsystem.txt
+# ファイル名にスペースを含むファイル（エスケープ必要）
+"how mainREADME.md  Set-Clipboard"
```

#### 実行コマンド

```bash
# .gitignore を編集（上記の diff を適用）
vim .gitignore

# または、追記
cat >> .gitignore << 'EOF'

# ============================================================
# Node.js dependencies (CR-REPO-001)
# ============================================================
node_modules/
**/node_modules/

# ============================================================
# Exports and Backups (CR-REPO-001)
# ============================================================
exports/
!exports/.gitkeep
*.bak

# ============================================================
# Unknown files (CR-REPO-001)
# ============================================================
8.0
MONCLER_OFFICIAL
test_localsystem.txt
"how mainREADME.md  Set-Clipboard"
EOF
```

### 3.3 Git 追跡からの削除

#### ⚠️ 重要な注意事項

- `git rm --cached` を使用することで、**ローカルファイルは削除されず**、Git 追跡のみ解除されます
- `git rm` (--cached なし) は実ファイルも削除するため、**絶対に使用しない**

#### 実行コマンド

```bash
# ============================================================
# A. node_modules の削除
# ============================================================
git rm -r --cached node_modules/
git rm -r --cached vscode-extension/node_modules/

# ============================================================
# B. exports/ の削除
# ============================================================
git rm -r --cached exports/

# ============================================================
# C. ログファイルの削除
# ============================================================
# 個別のログファイル
git rm --cached .env.bak
git rm --cached launch_dev.debug.log
git rm --cached nexus_core_run.log

# パターンマッチ（.log で終わる全てのファイル）
git ls-files | grep '\.log$' | xargs git rm --cached

# ディレクトリ内のログ（既に追跡されているもののみ）
git rm -r --cached .logs/ 2>/dev/null || true
git rm -r --cached logs/ 2>/dev/null || true
git rm -r --cached codex_history/*.log 2>/dev/null || true
git rm -r --cached src/nexuscore/gradio_app/logs/ 2>/dev/null || true
git rm -r --cached src/sandbox_output/*.log 2>/dev/null || true
git rm --cached tools/analyzer.log 2>/dev/null || true

# ============================================================
# D. ZIPファイルの削除
# ============================================================
git rm --cached vscode-extension.zip
git rm --cached tools/exports/*.zip 2>/dev/null || true

# ============================================================
# E. その他不明ファイルの削除
# ============================================================
git rm --cached 8.0 2>/dev/null || true
git rm --cached MONCLER_OFFICIAL 2>/dev/null || true
git rm --cached test_localsystem.txt 2>/dev/null || true
git rm --cached "how mainREADME.md  Set-Clipboard" 2>/dev/null || true
```

#### 一括実行スクリプト（推奨）

```bash
#!/bin/bash
# cleanup_git_tracked_files.sh

set -e  # エラー時に停止

echo "=== CR-REPO-001: Git追跡ファイルのクリーンアップ ==="

# A. node_modules
echo "[1/5] Removing node_modules..."
git rm -r --cached node_modules/ 2>/dev/null || echo "  - node_modules/ already removed"
git rm -r --cached vscode-extension/node_modules/ 2>/dev/null || echo "  - vscode-extension/node_modules/ already removed"

# B. exports
echo "[2/5] Removing exports/..."
git rm -r --cached exports/ 2>/dev/null || echo "  - exports/ already removed"

# C. ログファイル
echo "[3/5] Removing log files..."
git ls-files | grep '\.log$' | xargs -r git rm --cached
git rm --cached .env.bak 2>/dev/null || echo "  - .env.bak already removed"
git rm --cached launch_dev.debug.log 2>/dev/null || echo "  - launch_dev.debug.log already removed"
git rm --cached nexus_core_run.log 2>/dev/null || echo "  - nexus_core_run.log already removed"

# D. ZIPファイル
echo "[4/5] Removing ZIP files..."
git rm --cached vscode-extension.zip 2>/dev/null || echo "  - vscode-extension.zip already removed"
git ls-files | grep '\.zip$' | xargs -r git rm --cached

# E. その他
echo "[5/5] Removing unknown files..."
git rm --cached 8.0 2>/dev/null || echo "  - 8.0 already removed"
git rm --cached MONCLER_OFFICIAL 2>/dev/null || echo "  - MONCLER_OFFICIAL already removed"
git rm --cached test_localsystem.txt 2>/dev/null || echo "  - test_localsystem.txt already removed"

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "Next steps:"
echo "  1. Review changes: git status"
echo "  2. Commit: git commit -m 'CR-REPO-001: Remove unnecessary tracked files'"
echo "  3. Push: git push origin feature/remove-unnecessary-tracked-files"
```

### 3.4 変更の確認

```bash
# 削除されたファイル数を確認
git status | grep "deleted:" | wc -l

# 期待値: 約 6,990 ファイル

# 詳細確認
git status --short | head -50
```

### 3.5 コミット

```bash
git add .gitignore

git commit -m "$(cat <<'EOF'
CR-REPO-001: Remove unnecessary tracked files from repository

## Summary
Removed 6,990 unnecessary files (73% of total) from Git tracking.

## Changes
- Remove node_modules/ (3,247 files, 39MB)
- Remove vscode-extension/node_modules/ (3,075 files, 18MB)
- Remove exports/ directory (584 files, 56MB)
- Remove log files (30 files)
- Remove backup files (.env.bak)
- Remove ZIP files (12 files)
- Remove unknown files (8.0, MONCLER_OFFICIAL, etc.)

## Impact
- Repository size reduced by ~113MB
- Faster git clone/pull operations
- Improved CI/CD performance
- Better developer experience (cleaner diffs)

## Migration
Developers must run after pulling:
  npm install                    # Root dependencies
  cd vscode-extension && npm install  # Extension dependencies

## References
- Spec: docs/spec/CR-REPO-001_remove_unnecessary_tracked_files.md
EOF
)"
```

### 3.6 プッシュとPR作成

```bash
# プッシュ
git push origin feature/remove-unnecessary-tracked-files

# PR作成（GitHub CLI使用）
gh pr create \
  --title "CR-REPO-001: Remove unnecessary tracked files from repository" \
  --body "$(cat <<'EOF'
## 概要
リポジトリから不要な追跡ファイル（約6,990ファイル、113MB）を削除します。

## 変更内容
- ✅ node_modules/ の削除（6,326ファイル）
- ✅ exports/ の削除（584ファイル）
- ✅ ログファイルの削除（30ファイル）
- ✅ .gitignore の修正

## 影響
- リポジトリサイズ 73% 削減
- git clone 時間短縮
- CI/CD 高速化

## 移行手順
マージ後、全開発者は以下を実行：
\`\`\`bash
git pull
npm install
cd vscode-extension && npm install
\`\`\`

## 仕様書
docs/spec/CR-REPO-001_remove_unnecessary_tracked_files.md

## チェックリスト
- [x] .gitignore 修正
- [x] node_modules 削除
- [x] exports 削除
- [x] ログファイル削除
- [ ] PR レビュー
- [ ] マージ
- [ ] チームへの通知
EOF
)"
```

---

## 4. 影響範囲とリスク評価

### 4.1 影響を受けるステークホルダー

| ステークホルダー | 影響 | 対応 |
|---------------|------|------|
| **開発者** | マージ後に `npm install` 必要 | 移行手順を README に記載 |
| **CI/CD** | チェックアウト時間短縮 | 自動で改善、対応不要 |
| **本番環境** | 影響なし（デプロイプロセスは変わらず） | - |

### 4.2 リスクと対策

| リスク | 発生確率 | 影響度 | 対策 |
|--------|---------|--------|------|
| **開発者がnpm installを忘れる** | 中 | 中 | エラーメッセージに手順を追加、README更新 |
| **ローカルnode_modulesが古い** | 低 | 低 | package-lock.json を維持すれば問題なし |
| **exports/に重要ファイルがある** | 極低 | 高 | 事前レビュー必須、バックアップ作成 |
| **ログに機密情報が含まれる** | 低 | 高 | `.env.bak` 削除で対処、履歴から完全削除は別タスク |
| **Git履歴が残る** | 確実 | 中 | 別タスクで `git filter-repo` による履歴削除を検討 |

### 4.3 ロールバックプラン

```bash
# 方法1: コミット取り消し（マージ前）
git revert <commit-hash>

# 方法2: バックアップブランチから復元
git checkout backup/before-cleanup-20251209
git checkout -b feature/restore-files

# 方法3: 特定ファイルのみ復元
git checkout <commit-hash> -- node_modules/
```

---

## 5. テストと検証

### 5.1 事前検証

```bash
# ステップ1: 削除対象ファイルの存在確認
echo "=== Verification: Files to be removed ==="
git ls-files | grep "^node_modules/" | wc -l          # 期待: 3247
git ls-files | grep "^vscode-extension/node_modules" | wc -l  # 期待: 3075
git ls-files | grep "^exports/" | wc -l               # 期待: 584
git ls-files | grep "\.log$" | wc -l                  # 期待: 30

# ステップ2: exports/に重要ファイルがないか確認
git ls-files exports/ | grep -v "\.zip$" | grep -v "\.txt$" | head -20
# → .md, .py, .json など重要そうなファイルがあれば要レビュー
```

### 5.2 削除後の検証

```bash
# ステップ1: 削除されたファイル数確認
git status --short | grep "^D" | wc -l
# 期待: 約 6990

# ステップ2: 実ファイルが残っているか確認
ls -d node_modules/ 2>/dev/null && echo "✅ node_modules/ still exists locally"
ls -d exports/ 2>/dev/null && echo "✅ exports/ still exists locally"

# ステップ3: .gitignore が機能しているか確認
git status
# node_modules/ や exports/ が "Untracked files" に表示されないこと

# ステップ4: 新規ファイル作成テスト
touch node_modules/test.txt
git status | grep "test.txt"
# → 表示されなければ .gitignore が正しく機能
rm node_modules/test.txt
```

### 5.3 CI/CD テスト

マージ前に以下を確認：

```yaml
# .github/workflows/ci.yml が正常に動作するか
# - npm install が自動実行されるか
# - テストが通るか
```

---

## 6. 移行ガイド（開発者向け）

### 6.1 既存の開発者

#### マージ後の手順

```bash
# ステップ1: 最新コードを取得
git checkout main
git pull origin main

# ステップ2: node_modules を削除して再インストール
rm -rf node_modules/ vscode-extension/node_modules/
npm install
cd vscode-extension && npm install && cd ..

# ステップ3: 動作確認
npm run test  # または make test
```

### 6.2 新規の開発者

```bash
# ステップ1: クローン
git clone <repository_url>
cd NexusCore

# ステップ2: 依存関係インストール
npm install
cd vscode-extension && npm install && cd ..

# ステップ3: Python環境セットアップ
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 6.3 トラブルシューティング

#### Q1: `npm install` でエラーが出る

```bash
# package-lock.json を削除して再生成
rm package-lock.json
npm install
```

#### Q2: node_modules が Git に表示される

```bash
# .gitignore が正しく適用されているか確認
git check-ignore node_modules/
# → "node_modules/" と表示されればOK

# キャッシュをクリア
git rm -r --cached node_modules/
git add .gitignore
git commit -m "Fix .gitignore for node_modules"
```

#### Q3: 古い exports/ が残っている

```bash
# ローカルの exports/ を削除（必要なファイルをバックアップ後）
rm -rf exports/
mkdir exports/
touch exports/.gitkeep
```

---

## 7. 今後の対応（オプション）

### 7.1 Git履歴からの完全削除

現在の対応では、Git履歴には削除したファイルが残ります。完全に削除する場合：

```bash
# git-filter-repo を使用（推奨）
pip install git-filter-repo

git filter-repo --path node_modules --invert-paths
git filter-repo --path exports --invert-paths
git filter-repo --path vscode-extension/node_modules --invert-paths

# 強制プッシュ（⚠️ チーム全体の合意が必要）
git push origin --force --all
```

⚠️ **注意**: 履歴の書き換えは全開発者に影響します。実施前に必ずチーム合意を得てください。

### 7.2 Git LFS の導入検討

将来的に大きなバイナリファイルを管理する場合：

```bash
# Git LFS インストール
git lfs install

# 追跡するファイルタイプを指定
git lfs track "*.zip"
git lfs track "*.tar.gz"
git lfs track "*.psd"

git add .gitattributes
git commit -m "Add Git LFS tracking"
```

### 7.3 pre-commit フックの導入

誤って node_modules/ をコミットしないようにする：

```bash
# .git/hooks/pre-commit
#!/bin/bash

if git diff --cached --name-only | grep -q "node_modules/"; then
  echo "❌ Error: Attempting to commit node_modules/"
  echo "Please remove it from staging area:"
  echo "  git reset HEAD node_modules/"
  exit 1
fi
```

---

## 8. チェックリスト

### 実装前
- [ ] バックアップブランチ作成
- [ ] exports/ 内の重要ファイル確認
- [ ] チームへの事前通知

### 実装中
- [ ] 作業ブランチ作成
- [ ] .gitignore 修正
- [ ] Git追跡からファイル削除（--cached使用）
- [ ] 削除ファイル数確認（約6990）
- [ ] 実ファイルが残っているか確認
- [ ] .gitignore動作確認
- [ ] コミット
- [ ] プッシュ

### 実装後
- [ ] PR作成
- [ ] CI/CD正常動作確認
- [ ] レビュー依頼
- [ ] マージ
- [ ] チームへの移行手順通知（npm install必要）
- [ ] README更新（セットアップ手順）

### フォローアップ
- [ ] 全開発者が正常に移行できたか確認（1週間後）
- [ ] リポジトリサイズ削減を確認
- [ ] CI/CD時間短縮を確認
- [ ] Git履歴からの完全削除を検討（オプション）

---

## 9. 参考資料

### 関連ドキュメント
- [Git - .gitignore Documentation](https://git-scm.com/docs/gitignore)
- [npm - package.json and package-lock.json](https://docs.npmjs.com/cli/v10/configuring-npm/package-json)
- [GitHub - Managing large files](https://docs.github.com/en/repositories/working-with-files/managing-large-files)

### 内部ドキュメント
- `README.md` - セットアップ手順
- `docs/development_setup.md` - 開発環境構築
- `docs/makefile_guide.md` - Makefile コマンド

### 関連 Issue/PR
- (マージ後に追記)

---

## 10. 変更履歴

| 日付 | バージョン | 変更内容 | 担当者 |
|------|-----------|---------|--------|
| 2025-12-09 | 1.0 | 初版作成 | Claude (Sonnet 4.5) |

---

**承認者サイン**:
- [ ] Tech Lead: ________________
- [ ] Repository Maintainer: ________________
- [ ] Security Review: ________________

**実装完了日**: ________________
