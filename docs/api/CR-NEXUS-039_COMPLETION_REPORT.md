# CR-NEXUS-039: PR コメント生成の責務境界の明文化 - 完了レポート

## 実装日時

2025年12月24日

## 概要

### 目的

PR コメント生成の責務境界を固定し、`format_pr_comment()` と `build_pr_comment()` の関係を明文化する。また、DB/Flask 依存を排除して純粋関数化する。

### ゴール

- `format_pr_comment()` が必ず `## Self-Healing Result` セクションを出す（固定）
- `build_pr_comment(ctx)` は Guardian / Diff / Links 等の付随セクションのみを出す
- `format_pr_comment()` から DB/Flask 依存を排除し、result パラメータだけでコメントを生成できるようにする
- 将来の改修で `build_pr_comment()` が Self-Healing Result を出してしまう事故（重複・テスト不安定）を防ぐ

## 実装ステップ

### Step 1: 問題の原因の特定

**確認した問題**:
- `format_pr_comment()` が DB を参照しようとして Flask アプリケーションコンテキスト外で `RuntimeError` が発生する可能性があった
- `format_pr_comment()` と `build_pr_comment()` の責務境界が不明確だった
- 将来の改修で `build_pr_comment()` が誤って `## Self-Healing Result` を出力し、二重化するリスクがあった

**発生箇所**:
- `src/nexuscore/api/github_self_healing_webhook.py` の `format_pr_comment()` 関数
- `src/nexuscore/integration/github_pr_comment.py` の `build_pr_comment()` 関数

### Step 2: 修正内容

**変更ファイル**:
- `src/nexuscore/api/github_self_healing_webhook.py`
- `src/nexuscore/integration/github_pr_comment.py`
- `tests/api/test_github_self_healing_webhook.py`

**修正内容**:

1. **`format_pr_comment()` の修正**:
   - DB/Flask 依存を排除し、result パラメータだけでコメントを生成できるように修正
   - `## Self-Healing Result` ヘッダーを固定で付与するように修正
   - `build_pr_comment()` が誤って `## Self-Healing Result` を出力した場合の二重出力防止ガードを追加
   - セクション全体を除去するロジックを実装（`## Self-Healing Result` から次の `## ` 見出しまで、または末尾まで）

2. **`build_pr_comment()` の docstring 更新**:
   - 責務境界を明記: 「Self-Healing Result はこの関数では出さない。上位の `format_pr_comment()` が固定で付与する」
   - 「この関数は Guardian/Diff/Links/MarkdownReport 等、付随セクションの組み立てに限定する」ことを明記

3. **テストの追加**:
   - `test_format_pr_comment_includes_self_healing_result_header_once()`: `format_pr_comment()` が Self-Healing Result ヘッダーを 1 回だけ含むことを検証
   - テスト関数内で `format_pr_comment` を明示的に import して、import 依存を排除

**修正の意図**:
- `format_pr_comment()` を純粋関数化し、DB/Flask 依存を排除
- 責務境界を明文化し、将来の改修で重複出力を防ぐ
- テストの独立性を向上させる

## 変更ファイル一覧

### 変更ファイル
- `src/nexuscore/api/github_self_healing_webhook.py` - DB 依存削除、二重出力防止ガード追加
- `src/nexuscore/integration/github_pr_comment.py` - docstring 更新
- `tests/api/test_github_self_healing_webhook.py` - テスト追加、import 依存排除

## 動作確認結果

### テスト結果

**実行コマンド**:
```bash
python -m pytest tests/api/test_github_self_healing_webhook.py -q
```

**結果**:
- 全テスト PASS
- `test_format_pr_comment_includes_self_healing_result_header_once`: PASS

## 設計上の改善点

### アーキテクチャの改善
1. **責務境界の明確化**
   - `format_pr_comment()` と `build_pr_comment()` の責務を明確に分離
   - DB/Flask 依存を排除し、純粋関数化

2. **二重出力防止**
   - 将来の改修で重複出力が発生しないようガードを追加

## 既知の制約・注意事項

### 制約
- `build_pr_comment()` の内部実装変更は実施していない（docstring 更新のみ）
- 既存の CR-NEXUS-039 の「DB/Flask 非依存」条件を維持

## 次のステップ

- 他の Webhook 処理での同様の責務分離の適用

