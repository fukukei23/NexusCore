# =============================================================================
# FILE:         src/nexuscore/agents/constitutional_council_agent.py
# DATE:         2025-11-03 (JST)
# REGISTRY:     nexuscore.agents.ConstitutionalCouncilAgent
# DESC:
#   - BaseAgent の LLM 経由呼び出しに統一（execute_llm_task）
#   - ポリシー保存時のバックアップを「タイムスタンプ付き」でローテーション
#   - Flask Web UI の Bootstrap CDN URL 修正（[] を除去）
#   - 承認/却下時のアーカイブ失敗も分かるように flash メッセージ整備
# USAGE:
#   - CLI:  python src/nexuscore/agents/constitutional_council_agent.py
#   - WEB:  set FLASK_SECRET_KEY=your_prod_secret & ^
#            python src/nexuscore/agents/constitutional_council_agent.py web
# NOTE:
#   - policy_path の既定は "config/policy_rules.json"
#   - amendments_dir には pending_*.json を保存し、approve/reject で enacted_/rejected_ に更名
# =============================================================================

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

from flask import Flask, flash, redirect, render_template_string, url_for

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ConstitutionalCouncilAgent(BaseAgent):
    def __init__(
        self, policy_path: str = "config/policy_rules.json", amendments_dir: str = "amendments"
    ):
        """
        憲法評議会エージェント（Constitutional Council Agent）
        インシデント（Postmortem）や新知見（Knowledge）に基づき、
        システムの行動規範（ポリシー）の改正案を提案・承認・却下する。
        """
        super().__init__()  # BaseAgent の LLMRouter, logger を継承
        self.policy_path = Path(policy_path)
        self.amendments_dir = Path(amendments_dir)
        self.amendments_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------
    # I/O: Policies
    # -------------------------------
    def _load_policies(self) -> list[dict]:
        """現在のポリシー（憲法）をファイルから読み込む"""
        if not self.policy_path.exists():
            logger.warning(f"[Council] Policy file not found: {self.policy_path}")
            return []
        try:
            with self.policy_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load or parse current policies from {self.policy_path}: {e}")
            raise RuntimeError(f"Failed to load current policies: {e}") from e

    def _save_policies(self, policies: list[dict]) -> None:
        """
        ポリシー（憲法）をファイルに保存し、既存を「タイムスタンプ付き .bak.json」にバックアップ。
        例: policy_rules.json -> policy_rules.1730617200.bak.json
        """
        try:
            if self.policy_path.exists():
                ts = int(time.time())
                backup_path = self.policy_path.with_suffix(f".{ts}.bak.json")
                self.policy_path.replace(backup_path)
                logger.info(f"[Council] Policies backup created: {backup_path}")
            else:
                logger.info("[Council] No existing policy file to backup.")

            with self.policy_path.open("w", encoding="utf-8") as f:
                json.dump(policies, f, ensure_ascii=False, indent=2)
            logger.info(f"[Council] Policies updated and saved: {self.policy_path}")
        except Exception as e:
            logger.error(f"Failed to save policies to {self.policy_path}: {e}")
            raise RuntimeError(f"Failed to save policies: {e}") from e

    # -------------------------------
    # Validation
    # -------------------------------
    def _validate_amendment(self, proposal: dict[str, Any]) -> bool:
        """LLMによって提案された改正案の形式を検証する"""
        if not isinstance(proposal, dict):
            logger.warning("[Council] Invalid proposal format: not a dict.")
            return False

        if not proposal:  # {} は「変更なし」として許可
            return True

        allowed_keys = {
            "policy_id", "description", "rules", "delete_policy_id",
            "category", "tags", "priority", "enabled",
            "target_file_pattern", "detection_pattern",
            "severity", "suggestion", "exception_rules",
            "version", "owner",
        }
        unknown_keys = set(proposal.keys()) - allowed_keys
        if unknown_keys:
            logger.warning(f"[Council] Proposal contains unknown keys: {unknown_keys}")
            return False

        if "delete_policy_id" in proposal and len(proposal) > 1:
            logger.warning("[Council] 'delete_policy_id' must be the only key if present.")
            return False

        if "policy_id" in proposal and "delete_policy_id" in proposal:
            logger.warning(
                "[Council] Proposal cannot contain both 'policy_id' and 'delete_policy_id'."
            )
            return False

        return True

    # -------------------------------
    # LLM Invocation
    # -------------------------------
    def _invoke_llm_with_retry(
        self, prompt: str, retries: int = 2, delay: float = 1.0
    ) -> str | None:
        """
        BaseAgent.execute_llm_task を用い、指数バックオフで再試行。
        """
        last_err = None
        for attempt in range(retries + 1):
            try:
                resp = self.execute_llm_task(prompt, as_json=False)
                if not resp:
                    raise ValueError("Empty response from execute_llm_task")
                return resp if isinstance(resp, str) else str(resp)
            except Exception as e:
                last_err = e
                logger.warning(
                    f"[Council] LLM execute failed (attempt {attempt+1}/{retries+1}): {e}"
                )
                if attempt < retries:
                    time.sleep(delay * (2**attempt))
        logger.error(f"[Council] LLM execute failed after {retries+1} attempts: {last_err}")
        return None

    # -------------------------------
    # Main: Review & Propose
    # -------------------------------
    def review_and_amend(self, postmortem_report: dict, knowledge_brief: dict) -> None:
        """
        インシデント報告とナレッジに基づき、憲法（ポリシー）の見直しと改正案の提案を行う。
        """
        logger.info("[Council] New session convened to review constitution.")

        # ポリシー読み込み（リトライ）
        current_policies = None
        retry_attempts = 3
        last_load_err = None
        for attempt in range(retry_attempts):
            try:
                current_policies = self._load_policies()
                break
            except RuntimeError as e:
                last_load_err = e
                wait = 2**attempt
                logger.warning(
                    f"[Council] Failed to load policies (attempt {attempt+1}/{retry_attempts}): {e}. Retrying in {wait}s..."
                )
                time.sleep(wait)
        if current_policies is None:
            logger.error(
                f"[Council] Aborting session: Could not load policies after {retry_attempts} attempts. Last error: {last_load_err}"
            )
            return

        prompt = f"""
# Constitutional Review Mandate

## Current Constitution
{json.dumps(current_policies, indent=2, ensure_ascii=False)}

## Case Files
### Postmortem Report
- Failure Summary: {postmortem_report.get('failure_summary', 'N/A')}
- Root Cause Analysis: {postmortem_report.get('root_cause', 'N/A')}

### Knowledge Brief
- Inefficiency Pattern: {knowledge_brief.get('pattern', 'N/A')}
- Suggested Improvement: {knowledge_brief.get('suggestion', 'N/A')}

## Task
Analyze the case files in light of the current constitution and propose exactly ONE amendment.

## Response Format (strict JSON):
- Add/Modify: {{"policy_id": "PID-XXX", "description": "...", "category": "SECURITY", "tags": ["security"], "priority": 1, "severity": "CRITICAL", "target_file_pattern": ".*\\.py$", "detection_pattern": "...", "suggestion": "...", "exception_rules": {{"allowed_patterns": [], "allowlisted_files": [], "project_exclusions": []}}}}
- Delete: {{"delete_policy_id": "PID-YYY"}}
- No change: {{}}
"""
        raw_response = self._invoke_llm_with_retry(prompt, retries=2, delay=1.0)
        if raw_response is None:
            logger.error("[Council] No valid response from LLM. Session aborted.")
            return

        try:
            # コードブロック対策
            txt = raw_response.strip()
            if txt.startswith("```"):
                txt = txt.strip("`")
                txt = txt.replace("json", "", 1).strip()
            proposal = json.loads(txt)
        except json.JSONDecodeError as e:
            logger.error(
                f"[Council] Invalid JSON amendment from LLM: {e}. Raw response: {raw_response}"
            )
            return

        if not isinstance(proposal, dict):
            logger.error(
                f"[Council] Invalid proposal format (not a dict). Aborting. Proposal: {proposal}"
            )
            return

        if not proposal:
            logger.info(
                "[Council] Constitution deemed sufficient. No changes proposed. Session adjourned."
            )
            return

        if not self._validate_amendment(proposal):
            logger.error(
                f"[Council] Amendment proposal failed validation. Session aborted. Proposal: {proposal}"
            )
            return

        # 検証を通過 → 保留ファイル保存
        timestamp = int(time.time())
        pending_path = self.amendments_dir / f"pending_{timestamp}.json"
        try:
            with pending_path.open("w", encoding="utf-8") as f:
                json.dump(proposal, f, ensure_ascii=False, indent=2)
            logger.info(f"[Council] Amendment proposal saved for human approval: {pending_path}")
        except Exception as e:
            logger.error(f"[Council] Failed to save pending amendment: {e}")

    # -------------------------------
    # Archive helper
    # -------------------------------
    def _archive_amendment(self, pending_file: Path, status: str) -> bool:
        """
        改正案ファイルを『status_*.json』に更名（リトライ付き）
        status: 'enacted' or 'rejected'
        """
        if not (pending_file.exists() and pending_file.name.startswith("pending_")):
            logger.error(f"[Council] Archive failed: File not found or invalid: {pending_file}")
            return False

        new_name = pending_file.name.replace("pending_", f"{status}_")
        archive_path = self.amendments_dir / new_name

        retry_attempts = 3
        last_err = None
        for attempt in range(retry_attempts):
            try:
                pending_file.replace(archive_path)
                logger.info(f"[Council] Amendment archived as {status}: {archive_path}")
                return True
            except Exception as e:
                last_err = e
                wait = 2**attempt
                logger.error(
                    f"[Council] Error archiving file (attempt {attempt+1}/{retry_attempts}): {e}. Retrying in {wait}s..."
                )
                time.sleep(wait)

        logger.error(
            f"[Council] Failed to archive amendment {pending_file.name} after {retry_attempts} attempts. Last error: {last_err}"
        )
        return False

    # -------------------------------
    # Approve / Reject
    # -------------------------------
    def approve_amendment(self, pending_file: Path) -> bool:
        """pending_*.json を憲法に適用し、enacted_*.json にアーカイブ"""
        if not pending_file.exists() or not pending_file.name.startswith("pending_"):
            logger.error(f"[Council] Pending amendment file not found or invalid: {pending_file}")
            return False

        try:
            with pending_file.open("r", encoding="utf-8") as f:
                proposal = json.load(f)
            logger.info(f"[Council] Approving amendment: {pending_file.name}")
        except Exception as e:
            logger.error(f"[Council] Failed to load pending amendment {pending_file}: {e}")
            return False

        try:
            current_policies = self._load_policies()
        except RuntimeError as e:
            logger.error(f"[Council] Approval failed: Could not load policies. Error: {e}")
            return False

        if "delete_policy_id" in proposal:
            pid = proposal["delete_policy_id"]
            new_policies = [p for p in current_policies if p.get("policy_id") != pid]
            if len(new_policies) == len(current_policies):
                logger.warning(f"[Council] Policy '{pid}' to delete was not found.")
            else:
                logger.info(f"[Council] Policy '{pid}' repealed.")
        elif "policy_id" in proposal:
            new_policies = current_policies.copy()
            pid = proposal["policy_id"]
            found = False
            for i, p in enumerate(new_policies):
                if p.get("policy_id") == pid:
                    # 既存ポリシーに新フィールドをマージ（既存値を新値で上書き）
                    merged = {**p, **proposal}
                    new_policies[i] = merged
                    logger.info(f"[Council] Policy '{pid}' amended.")
                    found = True
                    break
            if not found:
                new_policies.append(proposal)
                logger.info(f"[Council] New policy '{pid}' enacted.")
        else:
            logger.error(
                f"[Council] Invalid proposal structure (no 'delete_policy_id' or 'policy_id'): {proposal}"
            )
            return False

        try:
            self._save_policies(new_policies)
        except Exception as e:
            logger.error(f"[Council] Failed to save policies: {e}")
            return False

        # アーカイブ（enacted_）へ
        if not self._archive_amendment(pending_file, "enacted"):
            logger.error(
                f"[Council] CRITICAL: Policies saved, but failed to archive {pending_file.name}. Manual cleanup required."
            )
            return False

        return True

    def reject_amendment(self, pending_file: Path) -> bool:
        """pending_*.json を rejected_*.json にアーカイブ"""
        return self._archive_amendment(pending_file, "rejected")

    # -------------------------------
    # CLI menu (for manual ops)
    # -------------------------------
    def cli_menu(self):
        logger.info("--- [Constitutional Council CLI] ---")
        while True:
            try:
                pending_files = sorted(
                    list(self.amendments_dir.glob("pending_*.json")),
                    key=lambda f: f.stat().st_mtime,
                )
            except Exception as e:
                logger.error("Error reading amendments directory: %s", e)
                break

            if not pending_files:
                logger.info("保留中の改正案はありません。(No pending amendments.)")
                break

            logger.info("=== 保留中の改正案一覧 (Pending Amendments) ===")
            for idx, f in enumerate(pending_files):
                try:
                    with f.open("r", encoding="utf-8") as fp:
                        proposal = json.load(fp)
                        summary = proposal.get(
                            "description", proposal.get("delete_policy_id", "N/A")
                        )
                        logger.info("[%d] %s (Summary: %s...)", idx, f.name, str(summary)[:50])
                except Exception as e:
                    logger.error("[%d] %s (Error reading content: %s)", idx, f.name, e)

            logger.info("------------------------------------------")
            choice = (
                input("番号を選択 (a:承認, r:却下, q:終了) [例: a 0] -> ").strip().lower().split()
            )
            if not choice:
                continue

            action = choice[0]
            if action == "q":
                logger.info("CLIを終了します。")
                break

            if len(choice) != 2 or not choice[1].isdigit():
                logger.warning("無効な入力です。例: 'a 0' または 'r 1'")
                continue

            idx = int(choice[1])
            if idx not in range(len(pending_files)):
                logger.warning("無効な番号です。")
                continue

            target_file = pending_files[idx]
            if action == "a":
                logger.info("承認中: %s...", target_file.name)
                if self.approve_amendment(target_file):
                    logger.info("承認成功。")
                else:
                    logger.error("承認失敗。ログを確認してください。")
            elif action == "r":
                logger.info("却下中: %s...", target_file.name)
                if self.reject_amendment(target_file):
                    logger.info("却下成功。")
                else:
                    logger.error("却下失敗。ログを確認してください。")
            else:
                logger.warning("無効なアクションです。(a, r, q のみ)")

    # -------------------------------
    # Minimal Flask Web UI
    # -------------------------------
    def run_web_ui(self, host: str = "127.0.0.1", port: int = 5000):
        app = Flask(__name__)
        app.secret_key = os.getenv(
            "FLASK_SECRET_KEY", "dev_only_secret_key_for_council_ui_fallback"
        )
        agent = self

        TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>憲法改正案管理 (Constitutional Amendment)</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js" defer></script>
<style>
  body { background-color: #f8f9fa; }
  .card-header { background-color: #e9ecef; }
  pre {
    white-space: pre-wrap;
    word-break: break-all;
    background-color: #fff;
    border: 1px solid #dee2e6;
    border-radius: 0.25rem;
  }
</style>
</head>
<body class="bg-light">
<div class="container py-4">
{% with messages = get_flashed_messages(with_categories=true) %}
  {% if messages %}
    {% for category, message in messages %}
      <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
        {{ message }}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
      </div>
    {% endfor %}
  {% endif %}
{% endwith %}
<h1 class="mb-4">憲法改正案 管理画面</h1>
<h2 class="h5 mb-3 text-muted">Pending Amendments</h2>
{% if files %}
<div class="row">
{% for fname, content in files %}
  <div class="col-lg-6">
    <div class="card mb-4 shadow-sm">
      <div class="card-header"><strong>{{ fname }}</strong></div>
      <div class="card-body">
        <pre class="small p-3">{{ content }}</pre>
        <div class="d-flex justify-content-end gap-2 mt-3">
          <a class="btn btn-success" onclick="return confirm('本当に承認しますか？\\nApprove this amendment?')" href="{{ url_for('approve', filename=fname) }}">承認 (Approve)</a>
          <a class="btn btn-danger"  onclick="return confirm('本当に却下しますか？\\nReject this amendment?')"   href="{{ url_for('reject', filename=fname) }}">却下 (Reject)</a>
        </div>
      </div>
    </div>
  </div>
{% endfor %}
</div>
{% else %}
  <div class="alert alert-info shadow-sm">保留中の改正案はありません。(No pending amendments.)</div>
{% endif %}
</div>
</body></html>"""

        @app.route("/")
        def index():
            files_data = []
            try:
                pending_files = sorted(
                    agent.amendments_dir.glob("pending_*.json"),
                    key=lambda f: f.stat().st_mtime,
                    reverse=True,
                )
            except Exception as e:
                logger.error(f"[WEB-UI] Error reading amendments directory: {e}")
                flash(f"改正案ディレクトリの読み込みに失敗しました: {e}", "danger")
                pending_files = []

            for f in pending_files:
                try:
                    with f.open("r", encoding="utf-8") as fp:
                        content = json.dumps(json.load(fp), ensure_ascii=False, indent=2)
                except Exception as e:
                    logger.error(f"[WEB-UI] Error reading file {f}: {e}")
                    content = f"読み込みエラー (Error reading file: {e})"
                files_data.append((f.name, content))
            return render_template_string(TEMPLATE, files=files_data)

        def _is_safe_filename(filename: str) -> bool:
            if not filename:
                return False
            if ".." in filename or "/" in filename or "\\" in filename or filename.startswith("/"):
                return False
            if not (filename.startswith("pending_") and filename.endswith(".json")):
                logger.warning(f"[WEB-UI] Filename format mismatch: {filename}")
                return False
            core = filename[len("pending_") : -len(".json")]
            if not core:
                logger.warning(f"[WEB-UI] Filename has empty core: {filename}")
                return False
            if re.search(r"[^\w\-]", core):
                logger.warning(f"[WEB-UI] Filename core contains invalid characters: {filename}")
                return False
            return True

        @app.route("/approve/<path:filename>")
        def approve(filename: str):
            if not _is_safe_filename(filename):
                logger.warning(f"[WEB-UI] Invalid path/filename detected in approve: {filename}")
                flash(f"無効なファイル名です: {filename}", "danger")
                return redirect(url_for("index"))
            try:
                file_path = agent.amendments_dir.joinpath(filename).resolve()
                if file_path.parent != agent.amendments_dir.resolve():
                    logger.error(f"[WEB-UI] Resolved path mismatch: {file_path}")
                    flash("セキュリティ違反が検出されました。", "danger")
                    return redirect(url_for("index"))

                ok = agent.approve_amendment(file_path)
                if ok:
                    flash(f"改正案 '{filename}' は正常に承認されました。", "success")
                else:
                    # False の場合、アーカイブ失敗 or 途中エラー。存在チェックで分岐。
                    if (agent.amendments_dir / filename).exists():
                        flash(
                            f"改正案 '{filename}' のアーカイブに失敗しました。ポリシーは更新済みの可能性があります。手動確認を。",
                            "danger",
                        )
                    else:
                        flash(
                            f"改正案 '{filename}' の承認に失敗しました。ログを確認してください。",
                            "danger",
                        )
            except Exception as e:
                logger.error(f"[WEB-UI] Error during approval of {filename}: {e}")
                flash(f"承認処理中に予期せぬエラー: {e}", "danger")
            return redirect(url_for("index"))

        @app.route("/reject/<path:filename>")
        def reject(filename: str):
            if not _is_safe_filename(filename):
                logger.warning(f"[WEB-UI] Invalid path/filename detected in reject: {filename}")
                flash(f"無効なファイル名です: {filename}", "danger")
                return redirect(url_for("index"))
            try:
                file_path = agent.amendments_dir.joinpath(filename).resolve()
                if file_path.parent != agent.amendments_dir.resolve():
                    logger.error(f"[WEB-UI] Resolved path mismatch: {file_path}")
                    flash("セキュリティ違反が検出されました。", "danger")
                    return redirect(url_for("index"))

                if agent.reject_amendment(file_path):
                    flash(f"改正案 '{filename}' は正常に却下されました。", "info")
                else:
                    flash(
                        f"改正案 '{filename}' の却下（アーカイブ）に失敗しました。ログを確認してください。",
                        "danger",
                    )
            except Exception as e:
                logger.error(f"[WEB-UI] Error during rejection of {filename}: {e}")
                flash(f"却下処理中に予期せぬエラー: {e}", "danger")
            return redirect(url_for("index"))

        logger.info(f"[Council] Starting Web UI at http://{host}:{port}")
        app.run(host=host, port=port)


# --------------------------------
# Standalone
# --------------------------------
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    council_agent = ConstitutionalCouncilAgent()

    if len(sys.argv) > 1 and sys.argv[1] == "web":
        logger.info("Starting Web UI mode...")
        if os.getenv("FLASK_SECRET_KEY") is None:
            logger.warning("WARNING: 'FLASK_SECRET_KEY' not set. Using insecure fallback key.")
        council_agent.run_web_ui()
    else:
        logger.info("Starting CLI mode...")
        council_agent.cli_menu()
