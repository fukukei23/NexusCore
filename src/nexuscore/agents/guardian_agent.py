# ==============================================================================
# 操作するソフト: VSCode (または任意のテキストエディタ)
# フォルダ: src/nexuscore/agents/
# ファイル名: guardian_agent.py
# 日付: 2025/09/03
#
# 使用方法:
#   この内容で既存のファイルを上書きしてください。
#   BaseAgentの近代化された__init__契約に準拠させるための修正です。
#
# 改修内容:
#   - super().__init__()を、引数なしで呼び出すように修正しました。
#   - 受け取ったmodel名は、自身の属性として保持するようにしました。
# ==============================================================================

from __future__ import annotations

import os
import json
import git
from typing import Any, Dict, Optional, Callable, List, Union

from .base_agent import BaseAgent
from nexuscore.utils.vcs import GitController

try:
    from .guardian_auto_reviewer import GuardianAutoReviewer, ReviewDecision, ReviewResult
except ImportError:
    GuardianAutoReviewer = None  # type: ignore
    ReviewDecision = None  # type: ignore
    ReviewResult = None  # type: ignore

class GuardianAgent(BaseAgent):
    """
    コードの品質、セキュリティ、プロジェクト憲法への準拠をレビューし、
    承認時のみ Git に記録する CTO エージェント。
    """
    SYSTEM_PROMPT = """
あなたはCTO（最高技術責任者）です。
開発チームから提出されたコード、テスト結果、その他の情報を総合的にレビューし、
その変更を承認（APPROVE）するか、修正のために差し戻す（REJECT）かを判断してください。
判断は、プロジェクトの憲法と、提示された技術的証拠に厳密に基づいてください。
"""
    on_budget_tick: Optional[Callable[[str], None]] = None

    # ▼▼▼【最重要修正点】ここから▼▼▼
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        api_key/model はオプション扱い。未指定でも BaseAgent のルーター経由でスタブ/実コールが走る。
        実運用で専用モデルを強制したい場合は model を明示する。
        """
        super().__init__()  # 引数なしで呼び出すのが正しい作法
        self.model = model or ""  # model名は自身の属性として保持
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        # ▲▲▲【最重要修正点】ここまで▲▲▲
        try:
            self.vcs = GitController()
        except git.InvalidGitRepositoryError:
            self.vcs = None
            print("⚠️ GuardianAgent: Gitリポジトリが見つからないため、コミット機能は無効です。")

    def _budget(self, step: str) -> None:
        try:
            if callable(self.on_budget_tick):
                self.on_budget_tick(step)
        except Exception:
            pass

    def review(
        self,
        code_draft: str,
        test_code: str,
        test_result: str,
        testimony: str,
        constitution: str,
        task_description: str
    ) -> Dict[str, Any]:
        """
        コードと証跡をレビューして JSON を返す（コミットはしない）
        """
        self._budget("guardian:review")

        prompt = f"""
# レビュー対象の情報
- **プロジェクト憲法**: {constitution}
- **元のタスク**: {task_description}
- **提出コード**:
```python
{code_draft}
```
- **テストコード**:
```python
{test_code}
```
- **テスト結果**:
```
{test_result}
```
- **開発者の証言**: {testimony}

# あなたへの指示
上記の情報に基づき、このコード変更を承認するかを判断してください。

# 出力要件
必ず decision (APPROVEまたはREJECT) と reason (判断理由) を含むJSON形式で出力してください。
REJECTする場合、feedback_for_coder キーに具体的な修正指示を含めてください。
"""
        review_result_json = self.execute_llm_task(prompt, as_json=True)
        try:
            review_data = json.loads(review_result_json)
        except json.JSONDecodeError:
            print("❌ GuardianAgentのレビュー出力が不正なJSONでした。")
            return {"decision": "REJECT", "reason": "Invalid JSON response from Guardian."}

        review_data.setdefault("decision", "REJECT")
        review_data.setdefault("reason", "理由不明。")
        if review_data["decision"] == "REJECT":
            review_data.setdefault("feedback_for_coder", review_data["reason"])
        return review_data

    def review_and_commit(
        self,
        code_draft: str,
        test_code: str,
        test_result: str,
        testimony: str,
        constitution: str,
        task_description: str,
        changed_files: List[str],
        debug_info: Optional[Dict[str, Any]] = None,
        *,
        allow_commit: bool = True,
        branch_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        レビューし、APPROVE かつ allow_commit=True の場合のみコミットする。
        """
        review_data = self.review(
            code_draft=code_draft,
            test_code=test_code,
            test_result=test_result,
            testimony=testimony,
            constitution=constitution,
            task_description=task_description
        )
        decision = review_data.get("decision", "REJECTT")
        if decision != "APPROVE":
            return review_data

        if not allow_commit:
            review_data["commit"] = "Commit blocked by autonomy policy (review-only)."
            return review_data

        if not self.vcs:
            review_data["commit"] = "Git repository not available."
            return review_data

        try:
            if branch_name:
                self._prepare_branch(branch_name)
        except Exception as e:
            review_data["commit"] = f"Failed to prepare branch '{branch_name}': {e}"
            return review_data

        commit_message = self._generate_commit_message(review_data, changed_files, debug_info)
        commit_hash = self.vcs.commit_changes(changed_files, commit_message)
        review_data["commit"] = commit_hash or "Commit failed or no changes detected."
        return review_data

    def _prepare_branch(self, branch_name: str) -> None:
        """
        GitPython を使って <branch_name> に -B 相当で移動。
        """
        try:
            repo = git.Repo(os.getcwd())
        except Exception as e:
            raise RuntimeError(f"Git repo not found: {e}")
        repo.git.checkout("-B", branch_name)

    def _generate_commit_message(self, review_data: dict, changed_files: list, debug_info: dict = None) -> str:
        scope = "auto"
        body = f"Reviewed by: GuardianAgent (Model: {self.model})\n"
        body += f"Reason for approval: {review_data.get('reason', 'N/A')}\n"

        if debug_info:
            commit_type = "fix"
            header = f"{commit_type}({scope}): Self-healed by DebuggerAgent"
            body += f"\n[DEBUGGER ACTIVITY]\n"
            body += f"Error Signature: {debug_info.get('error_signature', 'N/A')}\n"
            solution_type = debug_info.get('solution_pattern', {}).get('type', 'N/A')
            body += f"Applied Solution Type: {solution_type}\n"
        else:
            commit_type = "feat"
            header = f"{commit_type}({scope}): Implemented new functionality via CoderAgent"

        return f"{header}\n\n{body}"

    def review_unified_diff(
        self,
        diff_text: str,
        project_name: str = "nexuscore",
    ) -> Dict[str, Any]:
        """
        unified diff テキストを自動レビューする。

        GuardianAutoReviewer を使用して、パターンベースの自動レビューを実行し、
        その結果を LLM レビューと組み合わせて最終判断を返す。

        :param diff_text: git diff --unified=0 形式の diff テキスト
        :param project_name: プロジェクト名（nexuscore / atelier-kyo-manager など）
        :return: {"decision": "approve"|"reject"|"manual_review", "reason": "...", "auto_review": {...}}
        """
        result: Dict[str, Any] = {
            "decision": "APPROVE",
            "reason": "",
            "auto_review": None,
        }

        # 自動レビューを実行
        if GuardianAutoReviewer is not None:
            try:
                reviewer = GuardianAutoReviewer(project_name=project_name)
                auto_result: ReviewResult = reviewer.review_unified_diff(diff_text)

                result["auto_review"] = {
                    "decision": auto_result.decision.value,
                    "summary": auto_result.summary(),
                    "has_errors": auto_result.has_errors,
                    "has_warnings": auto_result.has_warnings,
                    "issue_count": len(auto_result.issues),
                }

                # 自動レビューで REJECT の場合は即座に REJECT
                if auto_result.decision == ReviewDecision.REJECT:
                    result["decision"] = "REJECT"
                    result["reason"] = f"自動レビューで拒否されました:\n{auto_result.summary()}"
                    return result

                # MANUAL_REVIEW の場合は LLM レビューに回す（後続処理）
                if auto_result.decision == ReviewDecision.MANUAL_REVIEW:
                    result["decision"] = "MANUAL_REVIEW"
                    result["reason"] = f"自動レビューで警告が検出されました:\n{auto_result.summary()}"
                    # この場合は LLM レビューも実行する（後続処理）

            except Exception as e:
                # 自動レビューが失敗しても LLM レビューは続行
                result["auto_review"] = {"error": str(e)}
                self.logger.warning(f"GuardianAutoReviewer failed: {e}")

        # LLM レビューを実行（自動レビューで REJECT されていない場合）
        if result["decision"] != "REJECT":
            # diff を簡潔に要約して LLM に渡す
            diff_summary = self._summarize_diff_for_llm(diff_text)
            llm_review = self._review_with_llm(diff_summary, result.get("auto_review"))

            # LLM レビューの結果を統合
            llm_decision = llm_review.get("decision", "APPROVE")
            if llm_decision == "REJECT":
                result["decision"] = "REJECT"
                result["reason"] = llm_review.get("reason", "LLM レビューで拒否されました")
            elif result["decision"] == "MANUAL_REVIEW" or llm_decision == "MANUAL_REVIEW":
                result["decision"] = "MANUAL_REVIEW"
                if not result["reason"]:
                    result["reason"] = llm_review.get("reason", "人間レビューが必要です")

        return result

    def _summarize_diff_for_llm(self, diff_text: str) -> str:
        """
        diff テキストを LLM に渡しやすい形式に要約する。
        """
        lines = diff_text.splitlines()
        file_count = sum(1 for line in lines if line.startswith("+++"))
        hunk_count = sum(1 for line in lines if line.startswith("@@"))

        # 最初の 50 行だけ抽出（長すぎる diff を避ける）
        preview_lines = lines[:50]
        if len(lines) > 50:
            preview_lines.append(f"... (残り {len(lines) - 50} 行)")

        return f"""
変更ファイル数: {file_count}
変更ブロック数: {hunk_count}

Diff プレビュー:
{chr(10).join(preview_lines)}
"""

    def _review_with_llm(
        self,
        diff_summary: str,
        auto_review: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        LLM を使って diff をレビューする。
        """
        self._budget("guardian:review_diff")

        auto_review_text = ""
        if auto_review:
            auto_review_text = f"""
自動レビュー結果:
- 決定: {auto_review.get('decision', 'N/A')}
- 問題数: {auto_review.get('issue_count', 0)}
- 要約:
{auto_review.get('summary', 'N/A')}
"""

        prompt = f"""
以下のコード変更をレビューしてください。

{diff_summary}

{auto_review_text}

# 出力要件
必ず decision (APPROVE / REJECT / MANUAL_REVIEW) と reason (判断理由) を含むJSON形式で出力してください。
"""

        try:
            review_result_json = self.execute_llm_task(prompt, as_json=True)
            review_data = json.loads(review_result_json)
            review_data.setdefault("decision", "APPROVE")
            review_data.setdefault("reason", "理由なし")
            return review_data
        except Exception as e:
            self.logger.error(f"LLM review failed: {e}", exc_info=True)
            return {"decision": "MANUAL_REVIEW", "reason": f"LLM レビューエラー: {e}"}

    # ------------------------------------------------------------------ #
    # E-4/E-5: Before/After 差分サマリー生成（複数ファイル対応）
    # ------------------------------------------------------------------ #
    def generate_diff_summary(
        self,
        before_code: Optional[str] = None,
        after_code: Optional[str] = None,
        file_diffs: Optional[Dict[str, Dict[str, str]]] = None,
        semantic_diffs: Optional[Dict[str, Dict[str, Any]]] = None,
        model: str = "gpt-4.1",
    ) -> Union[str, Dict[str, str]]:
        """
        パッチ適用前後のコードを LLM に渡し、改善点を要約する。

        Args:
            before_code: 変更前のコード（単一ファイル用、後方互換性のため）
            after_code: 変更後のコード（単一ファイル用、後方互換性のため）
            file_diffs: 複数ファイルの差分（E-5 新機能）
                {
                    "a.py": {"before": "...", "after": "..."},
                    "b.py": {"before": "...", "after": "..."},
                }
            semantic_diffs: 意味的差分情報（Semantic Diff）
                {
                    "a.py": {
                        "functions": [...],
                        "behavior_hints": [...],
                    }
                }
            model: 使用する LLM モデル（デフォルト: "gpt-4.1"）

        Returns:
            単一ファイルの場合: 5行以内の改善点要約（Markdown 形式）
            複数ファイルの場合: {"a.py": "要約...", "b.py": "要約..."} の辞書
        """
        self._budget("guardian:diff_summary")

        # E-5: 複数ファイル対応
        if file_diffs:
            return self._generate_multi_file_diff_summary(file_diffs, semantic_diffs, model)

        # E-4: 単一ファイル対応（後方互換性）
        if before_code is None or after_code is None:
            return "差分サマリーの生成に失敗しました: before_code または after_code が指定されていません"

        prompt = f"""
以下のコード変更をレビューし、改善点を5行以内で要約してください。

## 変更前のコード
```python
{before_code}
```

## 変更後のコード
```python
{after_code}
```

## 出力要件
- 改善点を5行以内で要約してください
- 各項目は箇条書き（- で始まる）で記述してください
- 技術的な改善点（簡潔化、複雑度低減、バグ修正など）を明確に示してください
- Markdown 形式で出力してください

出力例:
- XXX が簡潔化され、可読性が向上
- 複雑度が低減され、保守性が改善
- エラーハンドリングが追加され、堅牢性が向上
"""

        try:
            # 一時的に model を変更（指定されたモデルを使用）
            original_model = self.model
            self.model = model

            summary = self.execute_llm_task(prompt, as_json=False)

            # model を元に戻す
            self.model = original_model

            # 5行以内に制限（行数チェック）
            lines = summary.strip().split("\n")
            if len(lines) > 5:
                # 最初の5行だけを取得
                summary = "\n".join(lines[:5])
                summary += "\n_(要約が長いため、最初の5行のみ表示)_"

            return summary.strip()

        except Exception as e:
            self.logger.error(f"Failed to generate diff summary: {e}", exc_info=True)
            return f"差分サマリーの生成に失敗しました: {e}"

    def _generate_multi_file_diff_summary(
        self,
        file_diffs: Dict[str, Dict[str, str]],
        semantic_diffs: Optional[Dict[str, Dict[str, Any]]] = None,
        model: str = "gpt-4.1",
    ) -> Dict[str, str]:
        """
        複数ファイルの差分サマリーを生成する（E-5）。

        Args:
            file_diffs: ファイル名をキー、{"before": "...", "after": "..."} を値とする辞書
            model: 使用する LLM モデル

        Returns:
            {"a.py": "要約...", "b.py": "要約..."} の辞書
        """
        result: Dict[str, str] = {}

        # 各ファイルに対して個別に要約を生成
        for file_path, diff_pair in file_diffs.items():
            before_code = diff_pair.get("before", "")
            after_code = diff_pair.get("after", "")

            if not before_code or not after_code:
                result[file_path] = "差分サマリーの生成に失敗しました: before/after が空です"
                continue

            try:
                # semantic_diffs があれば、プロンプトに追加情報を含める
                semantic_info = None
                if semantic_diffs and file_path in semantic_diffs:
                    semantic_info = semantic_diffs[file_path]

                # 単一ファイル用の要約生成を再利用（semantic_diffs は現状は使わないが、将来の拡張用）
                summary = self.generate_diff_summary(
                    before_code=before_code,
                    after_code=after_code,
                    semantic_diffs={file_path: semantic_info} if semantic_info else None,
                    model=model,
                )
                result[file_path] = summary if isinstance(summary, str) else "要約生成に失敗しました"
            except Exception as e:
                self.logger.warning(f"Failed to generate diff summary for {file_path}: {e}", exc_info=True)
                result[file_path] = f"差分サマリーの生成に失敗しました: {e}"

        return result
