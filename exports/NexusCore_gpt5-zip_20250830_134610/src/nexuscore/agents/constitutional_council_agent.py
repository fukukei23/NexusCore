# nexuscore/agents/constitutional_council_agent.py
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional
from flask import Flask, render_template_string, redirect, url_for

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class ConstitutionalCouncilAgent(BaseAgent):
    def __init__(self, llm_client, tools, policy_path="config/policy_rules.json", amendments_dir="amendments"):
        super().__init__(llm_client, tools)
        self.policy_path = Path(policy_path)
        self.amendments_dir = Path(amendments_dir)
        self.amendments_dir.mkdir(parents=True, exist_ok=True)

    def _load_policies(self) -> list[dict]:
        if not self.policy_path.exists():
            logger.warning(f"[Council] Policy file not found: {self.policy_path}")
            return []
        try:
            with self.policy_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load current policies: {e}")

    def _save_policies(self, policies: list[dict]) -> None:
        backup_path = self.policy_path.with_suffix(".bak.json")
        if self.policy_path.exists():
            self.policy_path.replace(backup_path)
        with self.policy_path.open("w", encoding="utf-8") as f:
            json.dump(policies, f, ensure_ascii=False, indent=2)
        logger.info(f"[Council] Policies updated. Backup saved: {backup_path}")

    def _validate_amendment(self, proposal: Dict[str, Any]) -> bool:
        allowed_keys = {"policy_id", "description", "rules", "delete_policy_id"}
        return bool(set(proposal.keys()) <= allowed_keys)

    def _invoke_llm_with_retry(self, prompt: str, retries: int = 2, delay: float = 1.0) -> Optional[str]:
        last_err = None
        for attempt in range(retries + 1):
            try:
                response = self.llm_client.invoke(prompt)
                if response and isinstance(response, str):
                    return response
                else:
                    raise ValueError("Empty or invalid LLM response")
            except Exception as e:
                last_err = e
                logger.warning(f"[Council] LLM invoke failed (attempt {attempt+1}): {e}")
                time.sleep(delay * (2 ** attempt))
        logger.error(f"[Council] LLM invoke failed after {retries+1} attempts: {last_err}")
        return None

    def review_and_amend(self, postmortem_report: dict, knowledge_brief: dict) -> None:
        logger.info("[Council] New session convened.")
        current_policies = self._load_policies()

        prompt = f"""
# Constitutional Review Mandate
## Current Constitution:
{json.dumps(current_policies, indent=2, ensure_ascii=False)}

## Case Files:
### Postmortem Report:
- Failure: {postmortem_report.get('failure_summary')}
- Root Cause Analysis: {postmortem_report.get('root_cause')}

### Knowledge Brief:
- Inefficiency Pattern: {knowledge_brief.get('pattern')}
- Suggested Improvement: {knowledge_brief.get('suggestion')}

## Task:
Analyze weaknesses and propose one amendment.
Respond with:
- JSON object for addition/modification
- or {{"delete_policy_id": "..."}} for deletion
- or {{}} if no changes are needed.
"""
        raw_response = self._invoke_llm_with_retry(prompt, retries=2, delay=1.0)
        if raw_response is None:
            logger.error("[Council] No valid response from LLM. Session aborted.")
            return
        try:
            proposal = json.loads(raw_response)
        except json.JSONDecodeError as e:
            logger.error(f"[Council] Invalid JSON amendment from LLM: {e}")
            return

        if not proposal:
            logger.info("[Council] Constitution deemed sufficient. Session adjourned.")
            return
        if not self._validate_amendment(proposal):
            logger.error("[Council] Amendment failed validation. Session aborted.")
            return

        pending_path = self.amendments_dir / f"pending_{int(time.time())}.json"
        with pending_path.open("w", encoding="utf-8") as f:
            json.dump(proposal, f, ensure_ascii=False, indent=2)
        logger.info(f"[Council] Amendment proposal saved for approval: {pending_path}")

    def approve_amendment(self, pending_file: Path) -> None:
        if not pending_file.exists():
            logger.error(f"[Council] Pending amendment file not found: {pending_file}")
            return
        try:
            with pending_file.open("r", encoding="utf-8") as f:
                proposal = json.load(f)
        except Exception as e:
            logger.error(f"[Council] Failed to load pending amendment: {e}")
            return

        current_policies = self._load_policies()
        if "delete_policy_id" in proposal:
            pid = proposal["delete_policy_id"]
            new_policies = [p for p in current_policies if p.get("policy_id") != pid]
            logger.info(f"[Council] Policy '{pid}' repealed.")
        else:
            new_policies = current_policies.copy()
            for i, p in enumerate(new_policies):
                if p.get("policy_id") == proposal.get("policy_id"):
                    new_policies[i] = proposal
                    logger.info(f"[Council] Policy '{proposal.get('policy_id')}' amended.")
                    break
            else:
                new_policies.append(proposal)
                logger.info(f"[Council] New policy '{proposal.get('policy_id')}' enacted.")
        self._save_policies(new_policies)
        enacted_path = self.amendments_dir / f"enacted_{int(time.time())}.json"
        pending_file.replace(enacted_path)
        logger.info(f"[Council] Amendment enacted and archived: {enacted_path}")

    def reject_amendment(self, pending_file: Path) -> None:
        if pending_file.exists():
            rejected_path = self.amendments_dir / f"rejected_{int(time.time())}.json"
            pending_file.replace(rejected_path)
            logger.info(f"[Council] Amendment rejected and archived: {rejected_path}")

    def cli_menu(self):
        while True:
            pending_files = list(self.amendments_dir.glob("pending_*.json"))
            if not pending_files:
                print("保留中の改正案はありません。")
                break
            print("\n=== 保留中の改正案一覧 ===")
            for idx, f in enumerate(pending_files):
                print(f"[{idx}] {f.name}")
            choice = input("承認する改正案番号（qで終了）: ").strip()
            if choice.lower() == "q":
                break
            if not choice.isdigit() or int(choice) not in range(len(pending_files)):
                print("無効な選択です。")
                continue
            self.approve_amendment(pending_files[int(choice)])

    def run_web_ui(self, host="127.0.0.1", port=5000):
        app = Flask(__name__)
        agent = self
        TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>憲法改正案管理</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
<div class="container py-4">
<h1 class="mb-4">憲法改正案 管理画面</h1>
{% if files %}
<div class="row">
{% for fname, content in files %}
<div class="col-md-6">
<div class="card mb-4 shadow-sm">
<div class="card-header"><strong>{{ fname }}</strong></div>
<div class="card-body">
<pre class="small bg-light p-2">{{ content }}</pre>
<a class="btn btn-success btn-sm" onclick="return confirm('承認しますか？')" href="{{ url_for('approve', filename=fname) }}">承認</a>
<a class="btn btn-danger btn-sm" onclick="return confirm('却下しますか？')" href="{{ url_for('reject', filename=fname) }}">却下</a>
</div></div></div>
{% endfor %}
</div>
{% else %}
<div class="alert alert-info">保留中の改正案はありません。</div>
{% endif %}
</div>
</body></html>"""
        @app.route("/")
        def index():
            files_data = []
            for f in agent.amendments_dir.glob("pending_*.json"):
                try:
                    with f.open("r", encoding="utf-8") as fp:
                        content = json.dumps(json.load(fp), ensure_ascii=False, indent=2)
                except Exception:
                    content = "読み込みエラー"
                files_data.append((f.name, content))
            return render_template_string(TEMPLATE, files=files_data)
        @app.route("/approve/<filename>")
        def approve(filename):
            agent.approve_amendment(agent.amendments_dir / filename)
            return redirect(url_for('index'))
        @app.route("/reject/<filename>")
        def reject(filename):
            agent.reject_amendment(agent.amendments_dir / filename)
            return redirect(url_for('index'))
        app.run(host=host, port=port)
