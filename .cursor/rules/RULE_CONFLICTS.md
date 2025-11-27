# NexusCore ルールファイル 重複・矛盾分析（更新版）

## ✅ 統合済み

### 1. 完全重複ファイルの削除
- ✅ `nexuscore-アーキテクチャルール.mdc` → `nexuscore-architecture-rules.mdc` に統合
- ✅ `nexuscore-プロジェクトルール.mdc` → `nexuscore-project-rules.mdc` に統合

### 2. 安全関連ルールの統合
- ✅ `nexuscore-firewall.mdc` → `nexuscore-safety.mdc` に統合
- ✅ `nexuscore-safe-shell.mdc` → `nexuscore-safety.mdc` に統合
- ✅ `nexuscore-safe-test-execution.mdc` → `nexuscore-safety.mdc` に統合
- ✅ `nexuscore-security-safety.mdc` → `nexuscore-safety.mdc` に統合

### 3. 参照の統一
- ✅ `nexuscore-auto-test.mdc` → `nexuscore-safety.mdc` を参照
- ✅ `nexuscore-codex-template.mdc` → 関連ルールを参照
- ✅ `nexuscore-starter-rules.mdc` → `nexuscore-llm-routing.mdc` を参照

## 📋 現在のルールファイル構成

1. **nexuscore-starter-rules.mdc** - 基本方針・開発原則（メインルール）
2. **nexuscore-architecture-rules.mdc** - アーキテクチャ制約
3. **nexuscore-safety.mdc** - 安全・セキュリティ・テスト実行（統合済み）
4. **nexuscore-llm-routing.mdc** - LLM モデル選択ルール
5. **nexuscore-auto-test.mdc** - テスト自動実行トリガー
6. **nexuscore-codex-template.mdc** - コード生成テンプレート
7. **nexuscore-test-quality.mdc** - テスト品質ガイドライン
8. **nexuscore-project-rules.mdc** - プロジェクト固有ルール（統合検討中）

## 🔄 今後の統合候補

### プロジェクトルールの統合
- `nexuscore-project-rules.mdc` と `nexuscore-starter-rules.mdc` は内容が重複
- 統合を検討中（`nexuscore-starter-rules.mdc` を基準に統合予定）

## 📝 ルール参照ガイド

- **開発を始める時**: `nexuscore-starter-rules.mdc`
- **アーキテクチャを変更する時**: `nexuscore-architecture-rules.mdc`
- **安全な操作を確認する時**: `nexuscore-safety.mdc`
- **LLM を呼び出す時**: `nexuscore-llm-routing.mdc`
- **テストを書く時**: `nexuscore-test-quality.mdc`
- **コードを生成する時**: `nexuscore-codex-template.mdc`
