import json
import logging
import os
import time
from pathlib import Path
from typing import Any

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
        super().__init__()
        self.policy_path = Path(policy_path)
        self.amendments_dir = Path(amendments_dir)
        self.amendments_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------
    # I/O: Policies
    # -------------------------------
    def _load_policies(self) -> list[dict]:
        if not self.policy_path.exists():
            logger.warning("[Council] Policy file not found: %s", self.policy_path)
            return []
        try:
            with self.policy_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to load or parse current policies from %s: %s", self.policy_path, e)
            raise RuntimeError(f"Failed to load current policies: {e}") from e

    def _save_policies(self, policies: list[dict]) -> None:
        try:
            if self.policy_path.exists():
                ts = int(time.time())
                backup_path = self.policy_path.with_suffix(f".{ts}.bak.json")
                self.policy_path.replace(backup_path)
                logger.info("[Council] Policies backup created: %s", backup_path)
            else:
                logger.info("[Council] No existing policy file to backup.")

            with self.policy_path.open("w", encoding="utf-8") as f:
                json.dump(policies, f, ensure_ascii=False, indent=2)
            logger.info("[Council] Policies updated and saved: %s", self.policy_path)
        except Exception as e:
            logger.error("Failed to save policies to %s: %s", self.policy_path, e)
            raise RuntimeError(f"Failed to save policies: {e}") from e

    # -------------------------------
    # Validation
    # -------------------------------
    def _validate_amendment(self, proposal: dict[str, Any]) -> bool:
        if not isinstance(proposal, dict):
            logger.warning("[Council] Invalid proposal format: not a dict.")
            return False

        if not proposal:
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
            logger.warning("[Council] Proposal contains unknown keys: %s", unknown_keys)
            return False

        if "delete_policy_id" in proposal and len(proposal) > 1:
            logger.warning("[Council] 'delete_policy_id' must be the only key if present.")
            return False

        if "policy_id" in proposal and "delete_policy_id" in proposal:
            logger.warning("[Council] Proposal cannot contain both 'policy_id' and 'delete_policy_id'.")
            return False

        return True

    # -------------------------------
    # LLM Invocation
    # -------------------------------
    def _invoke_llm_with_retry(
        self, prompt: str, retries: int = 2, delay: float = 1.0
    ) -> str | None:
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
                    "[Council] LLM execute failed (attempt %d/%d): %s",
                    attempt + 1, retries + 1, e,
                )
                if attempt < retries:
                    time.sleep(delay * (2**attempt))
        logger.error("[Council] LLM execute failed after %d attempts: %s", retries + 1, last_err)
        return None

    # -------------------------------
    # Main: Review & Propose
    # -------------------------------
    def review_and_amend(self, postmortem_report: dict, knowledge_brief: dict) -> None:
        logger.info("[Council] New session convened to review constitution.")

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
                    "[Council] Failed to load policies (attempt %d/%d): %s. Retrying in %ds...",
                    attempt + 1, retry_attempts, e, wait,
                )
                time.sleep(wait)
        if current_policies is None:
            logger.error(
                "[Council] Aborting session: Could not load policies after %d attempts. Last error: %s",
                retry_attempts, last_load_err,
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
            txt = raw_response.strip()
            if txt.startswith("```"):
                txt = txt.strip("`")
                txt = txt.replace("json", "", 1).strip()
            proposal = json.loads(txt)
        except json.JSONDecodeError as e:
            logger.error("[Council] Invalid JSON amendment from LLM: %s. Raw response: %s", e, raw_response)
            return

        if not isinstance(proposal, dict):
            logger.error("[Council] Invalid proposal format (not a dict). Aborting. Proposal: %s", proposal)
            return

        if not proposal:
            logger.info("[Council] Constitution deemed sufficient. No changes proposed. Session adjourned.")
            return

        if not self._validate_amendment(proposal):
            logger.error("[Council] Amendment proposal failed validation. Session aborted. Proposal: %s", proposal)
            return

        timestamp = int(time.time())
        pending_path = self.amendments_dir / f"pending_{timestamp}.json"
        try:
            with pending_path.open("w", encoding="utf-8") as f:
                json.dump(proposal, f, ensure_ascii=False, indent=2)
            logger.info("[Council] Amendment proposal saved for human approval: %s", pending_path)
        except Exception as e:
            logger.error("[Council] Failed to save pending amendment: %s", e)

    # -------------------------------
    # Archive helper
    # -------------------------------
    def _archive_amendment(self, pending_file: Path, status: str) -> bool:
        if not (pending_file.exists() and pending_file.name.startswith("pending_")):
            logger.error("[Council] Archive failed: File not found or invalid: %s", pending_file)
            return False

        new_name = pending_file.name.replace("pending_", f"{status}_")
        archive_path = self.amendments_dir / new_name

        retry_attempts = 3
        last_err = None
        for attempt in range(retry_attempts):
            try:
                pending_file.replace(archive_path)
                logger.info("[Council] Amendment archived as %s: %s", status, archive_path)
                return True
            except Exception as e:
                last_err = e
                wait = 2**attempt
                logger.error(
                    "[Council] Error archiving file (attempt %d/%d): %s. Retrying in %ds...",
                    attempt + 1, retry_attempts, e, wait,
                )
                time.sleep(wait)

        logger.error(
            "[Council] Failed to archive amendment %s after %d attempts. Last error: %s",
            pending_file.name, retry_attempts, last_err,
        )
        return False

    # -------------------------------
    # Approve / Reject
    # -------------------------------
    def approve_amendment(self, pending_file: Path) -> bool:
        if not pending_file.exists() or not pending_file.name.startswith("pending_"):
            logger.error("[Council] Pending amendment file not found or invalid: %s", pending_file)
            return False

        try:
            with pending_file.open("r", encoding="utf-8") as f:
                proposal = json.load(f)
            logger.info("[Council] Approving amendment: %s", pending_file.name)
        except Exception as e:
            logger.error("[Council] Failed to load pending amendment %s: %s", pending_file, e)
            return False

        try:
            current_policies = self._load_policies()
        except RuntimeError as e:
            logger.error("[Council] Approval failed: Could not load policies. Error: %s", e)
            return False

        if "delete_policy_id" in proposal:
            pid = proposal["delete_policy_id"]
            new_policies = [p for p in current_policies if p.get("policy_id") != pid]
            if len(new_policies) == len(current_policies):
                logger.warning("[Council] Policy '%s' to delete was not found.", pid)
            else:
                logger.info("[Council] Policy '%s' repealed.", pid)
        elif "policy_id" in proposal:
            new_policies = current_policies.copy()
            pid = proposal["policy_id"]
            found = False
            for i, p in enumerate(new_policies):
                if p.get("policy_id") == pid:
                    merged = {**p, **proposal}
                    new_policies[i] = merged
                    logger.info("[Council] Policy '%s' amended.", pid)
                    found = True
                    break
            if not found:
                new_policies.append(proposal)
                logger.info("[Council] New policy '%s' enacted.", pid)
        else:
            logger.error("[Council] Invalid proposal structure: %s", proposal)
            return False

        try:
            self._save_policies(new_policies)
        except Exception as e:
            logger.error("[Council] Failed to save policies: %s", e)
            return False

        if not self._archive_amendment(pending_file, "enacted"):
            logger.error(
                "[Council] CRITICAL: Policies saved, but failed to archive %s. Manual cleanup required.",
                pending_file.name,
            )
            return False

        return True

    def reject_amendment(self, pending_file: Path) -> bool:
        return self._archive_amendment(pending_file, "rejected")

    # -------------------------------
    # UI entry points (delegates)
    # -------------------------------
    def cli_menu(self):
        from .council_cli import run_cli_menu
        run_cli_menu(self)

    def run_web_ui(self, host: str = "127.0.0.1", port: int = 5000):
        from .council_webui import run_web_ui
        run_web_ui(self, host=host, port=port)


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
