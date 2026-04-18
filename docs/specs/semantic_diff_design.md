# Semantic Diff 設計メモ

## 概要

Semantic Diff は、Self-Healing が行った変更について、「どの関数が増えた／消えた／シグネチャ変更されたか」「どのロジックが意味的に変わったか（例: 例外追加・バリデーション追加）」を構造化情報として抽出する機能です。

既存の「LLM ベースの一行サマリー」から一段進めて、AST + ヒューリスティックな「意味的 diff」レイヤーを差し込むことで、より詳細で構造化された変更情報を提供します。

## 何をもって「Semantic Diff」と定義しているか

### 関数レベルの変更

- **追加 (added)**: 新しい関数が追加された
- **削除 (removed)**: 既存の関数が削除された
- **変更 (modified)**: 関数のシグネチャ（引数、戻り値型）や docstring が変更された

### 振る舞いの変化ヒント

行レベル diff + 簡易ルールから推定した「振る舞いの変化ヒント」:

- **例外パスの追加/削除**: `raise` 文が追加/削除された
- **条件分岐の追加/削除**: `if` 文が追加/削除された
- **戻り値パスの追加/削除**: `return` 文の数が変化した
- **バリデーションの追加**: `assert` 文が追加された

各ヒントには `risk_level`（`low`, `medium`, `high`）が付与されます。

## 現状の実装レベル

### AST ベースの解析

- Python の `ast` モジュールを使用してコードをパース
- トップレベル関数とクラスメソッドのシグネチャを抽出
- Before/After の関数セットを比較して差分を計算

### ヒューリスティックな振る舞い検出

- `difflib.unified_diff()` を使用して行レベル diff を取得
- 簡易ルール（`raise`、`if`、`return`、`assert` の出現パターン）から振る舞いの変化を推定

### 失敗時の Graceful Degrade

- パースエラーや I/O エラーが発生しても例外を投げず、最低限 `raw_line_diff_summary` だけ埋めて返す
- ログに警告を記録しつつ、処理を継続

## LLM を使った要約との関係

### semantic_diffs → guardian_agent.generate_diff_summary の入力

`semantic_diffs` は `guardian_agent.generate_diff_summary()` の入力として使用できます（現状は軽めの統合）。

将来的には、以下のようなプロンプトで LLM に意味的な変更サマリーを生成させることができます：

```
あなたはコードレビューアシスタントです。
以下の情報をもとに、「何がどのように改善されたか」を日本語で3〜5行で要約してください。

- ファイル: {file_path}
- 関数レベルの変更 (added/removed/modified):
  {pretty_print(function_changes)}
- 振る舞いの変化ヒント:
  {pretty_print(behavior_hints)}
- 行レベル diff (必要に応じて):
  {truncated_unified_diff}
```

### 現状の実装

- `guardian_agent.generate_diff_summary()` に `semantic_diffs` パラメータを追加（後方互換性を維持）
- 現時点では `semantic_diffs` はプロンプトに直接含めていないが、将来の拡張用にプロトコルを整備

## 使用箇所

### 1. Self-Healing Service

`self_healing_service.py` で、パッチ適用後に `compute_semantic_diff()` を呼び出し、結果を `details["semantic_diffs"]` に格納。

### 2. GitHub PR コメント

`github_pr_comment.py` の `format_semantic_diff_block()` で、`semantic_diffs` を Markdown 形式（`<details>` タグ）でレンダリング。

### 3. Flask UI（将来）

Run 詳細画面で `semantic_diffs` を表示し、変更内容を可視化。

## データ構造

### SemanticDiffResult

```python
@dataclass
class SemanticDiffResult:
    file_path: Path
    functions: List[FunctionChange] = field(default_factory=list)
    behavior_hints: List[BehaviorChangeHint] = field(default_factory=list)
    raw_line_diff_summary: Optional[str] = None
```

### FunctionChange

```python
@dataclass
class FunctionChange:
    name: str
    kind: ChangeKind  # "added" | "removed" | "modified"
    signature_before: Optional[str] = None
    signature_after: Optional[str] = None
    doc_before: Optional[str] = None
    doc_after: Optional[str] = None
```

### BehaviorChangeHint

```python
@dataclass
class BehaviorChangeHint:
    description: str
    risk_level: Literal["low", "medium", "high"] = "medium"
```

## 制限事項

### 現状の実装レベル

- **Python のみ対応**: 現状は `language="python"` のみ対応。他の言語は `raw_line_diff_summary` のみ生成。
- **簡易ヒューリスティック**: 振る舞いの変化検出は簡易ルールベース。より高度な解析（データフロー解析など）は将来の拡張。
- **トップレベル関数のみ**: クラスメソッドの検出は部分的（将来の拡張余地あり）。

### 失敗時の挙動

- パースエラーや I/O エラーが発生しても例外を投げず、最低限の情報（`raw_line_diff_summary`）だけ返す
- ログに警告を記録しつつ、処理を継続

## 将来の拡張

### より高度な解析

- **データフロー解析**: 変数の使用箇所の変化を検出
- **制御フロー解析**: 分岐条件の変化をより詳細に検出
- **型情報の活用**: 型アノテーションから型の変化を検出

### 多言語対応

- JavaScript/TypeScript
- Java
- Go
- Rust

### LLM との統合強化

- `semantic_diffs` を LLM プロンプトに直接含めて、より詳細な要約を生成
- 関数レベルの変更と振る舞いの変化ヒントを組み合わせた、より構造化された要約

## 関連ファイル

- `src/nexuscore/diff/semantic_diff.py`: コア実装
- `src/nexuscore/services/self_healing_service.py`: Semantic Diff の生成と統合
- `src/nexuscore/agents/guardian_agent.py`: LLM サマリーへの統合（将来の拡張用）
- `src/nexuscore/integration/github_pr_comment.py`: PR コメントへのレンダリング
- `tests/diff/test_semantic_diff_basic.py`: 基本テスト

