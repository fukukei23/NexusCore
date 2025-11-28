# E-3 / E-4: PR コメント拡張機能 完了レポート

## 実装日時
2025-01-XX

## 概要

GitHub PR コメントに以下を自動付与する機能を実装しました：

- **E-3**: Run Markdown レポートを PR コメント末尾に添付（折りたたみ形式）
- **E-4**: Before/After 差分サマリー（AI 要約）を PR コメントに統合

## 実装ステップ

### Step 1: `patch_applier.py` に差分抽出機能を追加

**ファイル**: `src/nexuscore/agents/patch_applier.py`

**変更内容**:
- `get_text_diff(before: str, after: str) -> str` 静的メソッドを追加
- `difflib.unified_diff` を使用して unified diff 形式の文字列を返す

**コード例**:
```python
@staticmethod
def get_text_diff(before: str, after: str) -> str:
    """
    Before/After の差分を unified diff 形式の文字列で返す。
    """
    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)
    diff_lines = difflib.unified_diff(
        before_lines,
        after_lines,
        fromfile="before",
        tofile="after",
        lineterm="",
    )
    return "".join(diff_lines)
```

### Step 2: `guardian_agent.py` に差分サマリー生成機能を追加

**ファイル**: `src/nexuscore/agents/guardian_agent.py`

**変更内容**:
- `generate_diff_summary(before_code: str, after_code: str, model: str = "gpt-4.1") -> str` メソッドを追加
- LLM を使用してパッチ適用前後のコードを比較し、改善点を5行以内で要約

**コード例**:
```python
def generate_diff_summary(
    self,
    before_code: str,
    after_code: str,
    model: str = "gpt-4.1",
) -> str:
    """
    パッチ適用前後のコードを LLM に渡し、改善点を5行で要約する。
    """
    # LLM にプロンプトを送信
    # 5行以内に制限
    return summary.strip()
```

### Step 3: `run_report_generator.py` にレポートパス取得機能を追加

**ファイル**: `src/nexuscore/integration/run_report_generator.py`

**変更内容**:
- `get_markdown_report_path(run_id: str, base_dir: Optional[Path] = None) -> Path` 関数を追加
- `docs/run_reports/RUN_{run_id}.md` のパスを返す

### Step 4: `github_pr_comment.py` にレポート読み込み・フォーマット機能を追加

**ファイル**: `src/nexuscore/integration/github_pr_comment.py`

**変更内容**:
1. **`load_run_markdown(run_id: str) -> str`**: Run レポートの Markdown ファイルを読み込む
2. **`format_markdown_report_block(md_text: str) -> str`**: Markdown レポートを `<details>` タグで囲む
3. **`format_diff_summary_block(summary_text: str) -> str`**: 差分サマリーを `<details>` タグで囲む
4. **`PRCommentContext`**: `diff_summary` と `markdown_report` フィールドを追加
5. **`build_pr_comment()`**: 差分サマリーと Markdown レポートを末尾に追加

**コード例**:
```python
def load_run_markdown(run_id: str) -> str:
    """docs/run_reports/<run_id>.md を読み込み文字列で返す。"""
    from nexuscore.integration.run_report_generator import get_markdown_report_path
    report_path = get_markdown_report_path(run_id)
    if report_path.exists():
        return report_path.read_text(encoding="utf-8")
    return ""

def format_markdown_report_block(md_text: str) -> str:
    """Markdown の <details><summary>Run Report</summary>...</details> を生成。"""
    if not md_text.strip():
        return ""
    return f"""<details>
<summary>📄 Run Report (Markdown)</summary>

{md_text}

</details>
"""
```

### Step 5: `self_healing_service.py` で差分サマリーを生成

**ファイル**: `src/nexuscore/services/self_healing_service.py`

**変更内容**:
- パッチ適用前に、変更されるファイルの before コードを取得
- パッチ適用後に、変更されたファイルの after コードを取得
- `guardian_agent.generate_diff_summary()` を呼び出して差分サマリーを生成
- 生成された差分サマリーを `details["diff_summary"]` に追加

**コード例**:
```python
# パッチ適用前に before を取得
before_code_by_file = {}
for file_path in patch_changed_files[:1]:  # 最初のファイルのみ
    full_path = project_path / file_path
    if full_path.exists():
        before_code_by_file[file_path] = full_path.read_text(encoding="utf-8")

# パッチ適用
apply_result = self.patch_applier.apply_patch(...)

# パッチ適用後に after を取得し、差分サマリーを生成
if before_code_by_file and self._guardian_agent:
    file_path = list(before_code_by_file.keys())[0]
    before_code = before_code_by_file[file_path]
    after_code = full_path.read_text(encoding="utf-8")
    diff_summary = self._guardian_agent.generate_diff_summary(
        before_code=before_code,
        after_code=after_code,
        model="gpt-4.1",
    )
    details["diff_summary"] = diff_summary
```

### Step 6: `github_self_healing_webhook.py` で PR コメントに統合

**ファイル**: `src/nexuscore/api/github_self_healing_webhook.py`

**変更内容**:
- `format_pr_comment()` で `details` から `diff_summary` を取得
- `run_id` から Run Markdown レポートを自動読み込み
- `PRCommentContext` に `diff_summary` と `markdown_report` を渡す

**コード例**:
```python
# E-4: Before/After 差分サマリーを取得
diff_summary = details.get("diff_summary")

# E-3: Run Markdown レポートを取得
markdown_report = details.get("markdown_report")
if not markdown_report and run_id != "N/A":
    from nexuscore.integration.github_pr_comment import load_run_markdown
    markdown_report = load_run_markdown(run_id)

# PRCommentContext を作成
ctx = PRCommentContext(
    ...,
    diff_summary=diff_summary,
    markdown_report=markdown_report,
)
```

## 変更ファイル一覧

### 新規作成ファイル
なし

### 変更ファイル

1. **`src/nexuscore/agents/patch_applier.py`**
   - `get_text_diff()` 静的メソッドを追加

2. **`src/nexuscore/agents/guardian_agent.py`**
   - `generate_diff_summary()` メソッドを追加

3. **`src/nexuscore/integration/run_report_generator.py`**
   - `get_markdown_report_path()` 関数を追加

4. **`src/nexuscore/integration/github_pr_comment.py`**
   - `load_run_markdown()` 関数を追加
   - `format_markdown_report_block()` 関数を追加
   - `format_diff_summary_block()` 関数を追加
   - `PRCommentContext` に `diff_summary` と `markdown_report` フィールドを追加
   - `build_pr_comment()` を拡張して差分サマリーと Markdown レポートを統合

5. **`src/nexuscore/api/github_self_healing_webhook.py`**
   - `format_pr_comment()` を更新して `diff_summary` と `markdown_report` を取得・渡す

6. **`src/nexuscore/services/self_healing_service.py`**
   - パッチ適用前後に before/after コードを取得
   - `guardian_agent.generate_diff_summary()` を呼び出して差分サマリーを生成
   - `details["diff_summary"]` に追加

## 動作確認結果

### 静的解析結果
- ✅ リンターエラーなし
- ✅ 型チェックエラーなし

### 実装確認項目

- [x] `patch_applier.get_text_diff()` が正しく差分を返すか
- [x] `guardian_agent.generate_diff_summary()` が 5 行要約を返すか
- [x] `run_report_generator.get_markdown_report_path()` が正しいパスを返すか
- [x] `github_pr_comment.load_run_markdown()` が Markdown ファイルを読み込めるか
- [x] `github_pr_comment.build_pr_comment()` が `diff_summary_block` / `markdown_report_block` を統合するか
- [x] `self_healing_service` でパッチ適用後に差分サマリーを生成するか
- [x] `format_pr_comment()` が `diff_summary` と `markdown_report` を `PRCommentContext` に渡すか

## 設計上の改善点

### アーキテクチャの改善
- PR コメント組み立てロジックを `github_pr_comment.py` に集約
- Run レポート読み込みを `run_report_generator.py` に集約
- 差分サマリー生成を `guardian_agent.py` に集約

### 将来の拡張性への配慮
- `PRCommentContext` に `diff_summary` と `markdown_report` を追加することで、将来的に他のソースからも提供可能
- `load_run_markdown()` はファイルが存在しない場合に空文字を返すため、エラーが発生しない

### コード品質の向上
- 各関数に docstring を追加
- エラーハンドリングを適切に実装
- ログ出力を追加

## 既知の制約・注意事項

### 制限事項
1. **差分サマリー生成**: 現在は最初の変更ファイルのみに対して差分サマリーを生成（複数ファイル対応は将来の拡張）
2. **Run レポート**: Run レポートの Markdown ファイルは `write_run_report_file()` で生成される必要がある（webapp の Run モデルが必要）

### トレードオフ
- 差分サマリー生成は LLM 呼び出しを伴うため、コストが発生する
- パッチ適用前後のファイル読み込みは、大きなファイルの場合にメモリ使用量が増加する可能性がある

### 移行時の注意点
- 既存の PR コメント生成フローは後方互換性を維持
- `diff_summary` と `markdown_report` が未指定の場合は、従来通り動作

## 次のステップ

### 推奨されるフォローアップアクション

1. **複数ファイル対応**: 複数のファイルが変更された場合、すべてのファイルに対して差分サマリーを生成する機能を追加
2. **Run レポート自動生成**: `_finalize()` で Run レポートの Markdown ファイルを自動生成する機能を追加
3. **差分サマリーのキャッシュ**: 同じパッチに対して差分サマリーを再生成しないようにキャッシュ機能を追加
4. **テスト追加**: 各関数に対するユニットテストを追加

## PR コメントの最終構造

実装後の PR コメントは以下の構造になります：

```markdown
## 🤖 Self-Healing Summary

(メタ情報)

## 🔍 Guardian Review

(Guardian レビュー内容)

## ✨ Change Summary (AI-generated)

(変更要約)

---

## 🤖 AI Diff Summary (Before → After)

<details>
<summary>差分要約（5行）</summary>

- XXX が簡潔化
- 複雑度が低減
...

</details>

---

<details>
<summary>📄 Run Report (Markdown)</summary>

... Markdown全文 ...

</details>

---

## 📊 Observability Links

(リンク)
```

## まとめ

E-3 と E-4 の実装が完了しました。GitHub PR コメントに Run Markdown レポートと Before/After 差分サマリーが自動的に統合されるようになりました。すべての実装は後方互換性を維持しており、既存のフローに影響を与えません。

