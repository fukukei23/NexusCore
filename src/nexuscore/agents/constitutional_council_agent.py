# nexuscore/agents/constitutional_council_agent.py
import json
import logging
import time
import os  # (ご提案 #1 に基づき os をインポート)
import re  # (ご提案 #3 に基づき re をインポート)
from pathlib import Path
from typing import Any, Dict, Optional
# (ご提案 #3 に基づき flash をインポート)
from flask import Flask, render_template_string, redirect, url_for, flash

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class ConstitutionalCouncilAgent(BaseAgent):
    def __init__(self, policy_path="config/policy_rules.json", amendments_dir="amendments"):
        """
        憲法評議会エージェント（Constitutional Council Agent）
        AIエージェントシステムの行動規範（ポリシー）を管理し、
        インシデント（Postmortem）や新しい知見（Knowledge）に基づき、
        ポリシーの改正案を提案・承認する役割を担う。
        
        Args:
            policy_path (str): 現在のポリシー（憲法）が保存されているJSONファイルのパス
            amendments_dir (str): 改正案（pending/enacted/rejected）を保存するディレクトリのパス
        """
        super().__init__()
        self.policy_path = Path(policy_path)
        self.amendments_dir = Path(amendments_dir)
        self.amendments_dir.mkdir(parents=True, exist_ok=True)

    def _load_policies(self) -> list[dict]:
        """現在のポリシー（憲法）をファイルから読み込む"""
        if not self.policy_path.exists():
            logger.warning(f"[Council] Policy file not found: {self.policy_path}")
            return []
        try:
            with self.policy_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            # ファイルが空、またはJSONとして不正な場合も考慮
            logger.error(f"Failed to load or parse current policies from {self.policy_path}: {e}")
            # 実行時エラーとし、システムの起動シーケンスで検知できるようにする
            raise RuntimeError(f"Failed to load current policies: {e}")

    def _save_policies(self, policies: list[dict]) -> None:
        """ポリシー（憲法）をファイルに保存し、既存のファイルをバックアップする"""
        backup_path = self.policy_path.with_suffix(".bak.json")
        try:
            if self.policy_path.exists():
                self.policy_path.replace(backup_path)
                logger.info(f"[Council] Policies backup created: {backup_path}")
            else:
                logger.info(f"[Council] No existing policy file to backup.")
                
            with self.policy_path.open("w", encoding="utf-8") as f:
                json.dump(policies, f, ensure_ascii=False, indent=2)
            logger.info(f"[Council] Policies updated and saved: {self.policy_path}")
        except Exception as e:
            logger.error(f"Failed to save policies to {self.policy_path}: {e}")
            # ポリシーの保存失敗は重大なエラー
            raise RuntimeError(f"Failed to save policies: {e}")


    def _validate_amendment(self, proposal: Dict[str, Any]) -> bool:
        """LLMによって提案された改正案の形式を検証する"""
        if not isinstance(proposal, dict):
            logger.warning(f"[Council] Invalid proposal format: not a dict.")
            return False
            
        if not proposal: # 空の辞書 {} は「変更なし」として許可
            return True

        allowed_keys = {"policy_id", "description", "rules", "delete_policy_id"}
        unknown_keys = set(proposal.keys()) - allowed_keys
        
        if unknown_keys:
            logger.warning(f"[Council] Proposal contains unknown keys: {unknown_keys}")
            return False
            
        if "delete_policy_id" in proposal and len(proposal) > 1:
            logger.warning(f"[Council] 'delete_policy_id' must be the only key if present.")
            return False
            
        if "policy_id" in proposal and "delete_policy_id" in proposal:
            logger.warning(f"[Council] Proposal cannot contain both 'policy_id' and 'delete_policy_id'.")
            return False

        logger.debug("[Council] Proposal format validated.")
        return True

    def _invoke_llm_with_retry(self, prompt: str, retries: int = 2, delay: float = 1.0) -> Optional[str]:
        """
        LLMRouter 経由でLLMを実行（後方互換の薄ラッパ）
        BaseAgentのexecute_llm_taskを呼び出す。
        """
        last_err = None
        for attempt in range(retries + 1):
            try:
                # BaseAgentのexecute_llm_taskメソッドを使用
                resp = self.execute_llm_task(prompt, as_json=False)
                
                if not resp:
                    raise ValueError("Empty response from execute_llm_task")

                if isinstance(resp, str):
                    logger.debug(f"[Council] LLM raw response (str) received.")
                    return resp
                
                logger.debug(f"[Council] LLM response (non-str) received, casting to str.")
                return str(resp) # それ以外(dictなど)が返ってきた場合もstrにキャスト
                
            except Exception as e:
                last_err = e
                logger.warning(f"[Council] LLM execute failed (attempt {attempt+1}/{retries+1}): {e}")
                if attempt < retries:
                    time.sleep(delay * (2 ** attempt)) # 指数関数的バックオフ
                
        logger.error(f"[Council] LLM execute failed after {retries+1} attempts: {last_err}")
        return None

    def review_and_amend(self, postmortem_report: dict, knowledge_brief: dict) -> None:
        """
        インシデント報告とナレッジに基づき、憲法（ポリシー）の見直しと改正案の提案を行う。
        """
        logger.info("[Council] New session convened to review constitution.")
        
        # (ご提案 #4 に基づき、ポリシー読み込みにリトライ処理を追加)
        current_policies = None
        retry_attempts = 3
        last_load_err = None
        for attempt in range(retry_attempts):
            try:
                current_policies = self._load_policies()
                break # 成功したらループを抜ける
            except RuntimeError as e:
                last_load_err = e
                wait = 2 ** attempt
                logger.warning(f"[Council] Failed to load policies (attempt {attempt + 1}/{retry_attempts}): {e}. Retrying in {wait}s...")
                time.sleep(wait)  # 指数バックオフ
        
        if current_policies is None:
            logger.error(f"[Council] Aborting session: Could not load policies after {retry_attempts} attempts. Last error: {last_load_err}")
            return

        prompt = f"""
# Constitutional Review Mandate (憲法レビュー指令)

## Current Constitution (現行憲法):
{json.dumps(current_policies, indent=2, ensure_ascii=False)}

## Case Files (案件ファイル):

### Postmortem Report (インシデント事後分析報告):
- Failure Summary: {postmortem_report.get('failure_summary', 'N/A')}
- Root Cause Analysis: {postmortem_report.get('root_cause', 'N/A')}

### Knowledge Brief (ナレッジ・ブリーフ):
- Inefficiency Pattern: {knowledge_brief.get('pattern', 'N/A')}
- Suggested Improvement: {knowledge_brief.get('suggestion', 'N/A')}

## Task (タスク):
Analyze the provided case files in light of the current constitution.
Identify weaknesses, loopholes, or inefficiencies.
Propose exactly ONE amendment to address the most critical issue found.

## Response Format (回答フォーマット):
- To ADD or MODIFY a policy: Respond with a single JSON object.
  {{"policy_id": "PID-XXX", "description": "...", "rules": ["..."]}}
- To DELETE a policy: Respond with a JSON object specifying the ID to delete.
  {{"delete_policy_id": "PID-YYY"}}
- If NO CHANGE is necessary: Respond with an empty JSON object.
  {{}}

Your JSON response (must be valid JSON):
"""
        raw_response = self._invoke_llm_with_retry(prompt, retries=2, delay=1.0)
        
        if raw_response is None:
            logger.error("[Council] No valid response from LLM. Session aborted.")
            return

        try:
            # LLMの応答からJSON部分を抽出する（Markdownコードブロックなどに対応）
            json_str = raw_response.strip().lstrip("```json").lstrip("```").rstrip("```")
            proposal = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"[Council] Invalid JSON amendment from LLM: {e}. Raw response: {raw_response}")
            return

        if not isinstance(proposal, dict):
            logger.error(f"[Council] Invalid proposal format (not a dict). Aborting. Proposal: {proposal}")
            return

        if not proposal: # {} の場合
            logger.info("[Council] Constitution deemed sufficient. No changes proposed. Session adjourned.")
            return
            
        if not self._validate_amendment(proposal):
            logger.error(f"[Council] Amendment proposal failed validation. Session aborted. Proposal: {proposal}")
            return

        # 検証を通過した提案を保留ファイルとして保存
        timestamp = int(time.time())
        pending_path = self.amendments_dir / f"pending_{timestamp}.json"
        try:
            with pending_path.open("w", encoding="utf-8") as f:
                json.dump(proposal, f, ensure_ascii=False, indent=2)
            logger.info(f"[Council] Amendment proposal saved for human approval: {pending_path}")
        except Exception as e:
            logger.error(f"[Council] Failed to save pending amendment: {e}")

    def _archive_amendment(self, pending_file: Path, status: str) -> bool:
        """
        改正案ファイルをリトライ付きでアーカイブ（リネーム）するヘルパー
        (ご提案 #5 に基づく)
        
        Args:
            pending_file (Path): 'pending_*.json' ファイル
            status (str): 'enacted' または 'rejected'
        
        Returns:
            bool: アーカイブ成功時は True, 失敗時は False
        """
        if not (pending_file.exists() and pending_file.name.startswith("pending_")):
             logger.error(f"[Council] Archive failed: File not found or invalid: {pending_file}")
             return False
             
        new_name = pending_file.name.replace("pending_", f"{status}_")
        archive_path = self.amendments_dir / new_name

        retry_attempts = 3
        last_rename_err = None
        for attempt in range(retry_attempts):
            try:
                pending_file.replace(archive_path)
                logger.info(f"[Council] Amendment archived as {status}: {archive_path}")
                return True # 成功
            except Exception as e:
                last_rename_err = e
                wait = 2 ** attempt
                logger.error(f"[Council] Error archiving file (attempt {attempt + 1}/{retry_attempts}): {e}. Retrying in {wait}s...")
                time.sleep(wait) # 指数バックオフ
        
        logger.error(f"[Council] Failed to archive amendment {pending_file.name} after {retry_attempts} attempts. Last error: {last_rename_err}")
        return False # 失敗

    def approve_amendment(self, pending_file: Path) -> bool:
        """
        保留中の改正案（pending_*.json）を承認し、憲法（ポリシー）に適用する。
        (ご提案 #3 のため、成功/失敗を bool で返すように変更)
        """
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
                    new_policies[i] = proposal
                    logger.info(f"[Council] Policy '{pid}' amended.")
                    found = True
                    break
            if not found:
                new_policies.append(proposal)
                logger.info(f"[Council] New policy '{pid}' enacted.")
        else:
            logger.error(f"[Council] Invalid proposal structure (no 'delete_policy_id' or 'policy_id'): {proposal}")
            return False

        try:
            self._save_policies(new_policies)
        except Exception as e:
            logger.error(f"[Council] Failed to save policies: {e}")
            return False # ポリシー保存失敗は重大エラー

        # (ご提案 #5 に基づき、リトライ付きのアーカイブ処理を呼び出す)
        if not self._archive_amendment(pending_file, "enacted"):
            # ポリシーは保存されたが、アーカイブに失敗したケース
            logger.error(f"[Council] CRITICAL: Policies saved, but failed to archive {pending_file.name}. Manual cleanup required.")
            # (ご提案 #3 に基づき、UIに flash メッセージを送るため、ここではFalseを返す。flash自体は呼び出し元の @app.route で行う)
            return False # アーカイブ失敗もエラーとして扱う

        return True # すべて成功

    def reject_amendment(self, pending_file: Path) -> bool:
        """
        保留中の改正案（pending_*.json）を却下する。
        (ご提案 #3 のため、成功/失敗を bool で返すように変更)
        """
        # (ご提案 #5 に基づき、リトライ付きのアーカイブ処理を呼び出す)
        return self._archive_amendment(pending_file, "rejected")

    def cli_menu(self):
        """
        保留中の改正案を承認または却下するためのCUIメニュー。
        （主にデバッグや直接操作用）
        """
        print("\n--- [Constitutional Council CLI] ---")
        while True:
            try:
                pending_files = sorted(list(self.amendments_dir.glob("pending_*.json")), key=lambda f: f.stat().st_mtime)
            except Exception as e:
                print(f"Error reading amendments directory: {e}")
                break
                
            if not pending_files:
                print("保留中の改正案はありません。(No pending amendments.)")
                break
                
            print("\n=== 保留中の改正案一覧 (Pending Amendments) ===")
            for idx, f in enumerate(pending_files):
                try:
                    with f.open('r', encoding='utf-8') as fp:
                        proposal = json.load(fp)
                        summary = proposal.get('description', proposal.get('delete_policy_id', 'N/A'))
                        print(f"[{idx}] {f.name} (Summary: {summary[:50]}...)")
                except Exception as e:
                    print(f"[{idx}] {f.name} (Error reading content: {e})")

            print("------------------------------------------")
            choice = input("番号を選択 (a:承認, r:却下, q:終了) [例: a 0] -> ").strip().lower().split()

            if not choice:
                continue
            
            action = choice[0]
            if action == 'q':
                print("CLIを終了します。")
                break
            
            if len(choice) != 2 or not choice[1].isdigit():
                print("無効な入力です。例: 'a 0' (0番を承認) または 'r 1' (1番を却下)")
                continue
                
            idx = int(choice[1])
            if idx not in range(len(pending_files)):
                print("無効な番号です。")
                continue
                
            target_file = pending_files[idx]
            
            if action == 'a':
                print(f"承認中: {target_file.name}...")
                if self.approve_amendment(target_file):
                    print("承認成功。")
                else:
                    print("承認失敗。ログを確認してください。")
            elif action == 'r':
                print(f"却下中: {target_file.name}...")
                if self.reject_amendment(target_file):
                    print("却下成功。")
                else:
                    print("却下失敗。ログを確認してください。")
            else:
                print("無効なアクションです。(a, r, q のみ)")

    def run_web_ui(self, host="127.0.0.1", port=5000):
        """
        保留中の改正案を管理するためのシンプルなFlask Web UIを実行する。
        """
        app = Flask(__name__)
        # (ご提案 #1 に基づき、環境変数から secret_key を読み込む)
        # 本番環境では 'FLASK_SECRET_KEY' 環境変数を設定する必要がある
        app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev_only_secret_key_for_council_ui_fallback')
        
        agent = self # Flaskのクロージャ内でエージェントインスタンスを参照できるようにする
        
        # (ご提案 #2, #5 に基づき、BootstrapのURLから [] を削除)
        TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>憲法改正案管理 (Constitutional Amendment)</title>
<link href="[https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css](https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css)" rel="stylesheet">
<!-- Flashメッセージのアラートを閉じるためにBootstrap JSを追加 (URL修正) -->
<script src="[https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js](https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js)" defer></script>
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

<!-- Flashメッセージ表示領域 (ご提案 #3) -->
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
<!-- /Flashメッセージ表示領域 -->

<h1 class="mb-4">憲法改正案 管理画面</h1>
<h2 class="h5 mb-3 text-muted">Pending Amendments</h2>
{% if files %}
<div class="row">
{% for fname, content in files %}
<!-- HTMLタイポ修正 (class. -> class=) -->
<div class="col-lg-6">
<div class="card mb-4 shadow-sm">
<div class="card-header"><strong>{{ fname }}</strong></div>
<div class="card-body">
<pre class="small p-3">{{ content }}</pre>
<div class="d-flex justify-content-end gap-2 mt-3">
<a class="btn btn-success" onclick="return confirm('本当に承認しますか？\\nApprove this amendment?')" href="{{ url_for('approve', filename=fname) }}">承認 (Approve)</a>
<a class="btn btn-danger" onclick="return confirm('本当に却下しますか？\\nReject this amendment?')" href="{{ url_for('reject', filename=fname) }}">却下 (Reject)</a>
</div>
</div></div></div>
{% endfor %}
</div>
{% else %}
<!-- (ご提案 #2 の確認: エラーハンドリングは index() 側で行われる) -->
<div class="alert alert-info shadow-sm">保留中の改正案はありません。(No pending amendments.)</div>
{% endif %}
</div>
</body></html>"""

        @app.route("/")
        def index():
            files_data = []
            # mtime (更新日時) の降順でソート
            try:
                pending_files = sorted(
                    agent.amendments_dir.glob("pending_*.json"), 
                    key=lambda f: f.stat().st_mtime, 
                    reverse=True
                )
            except Exception as e:
                logger.error(f"[WEB-UI] Error reading amendments directory: {e}")
                # (ご提案 #3 に基づき flash メッセージを設定)
                flash(f"改正案ディレクトリの読み込みに失敗しました: {e}", "danger")
                pending_files = []
                
            for f in pending_files:
                try:
                    with f.open("r", encoding="utf-8") as fp:
                        content = json.dumps(json.load(fp), ensure_ascii=False, indent=2)
                except Exception as e:
                    # (ご提案 #2 の確認: エラーメッセージを content に設定し、UIに表示)
                    logger.error(f"[WEB-UI] Error reading file {f}: {e}")
                    content = f"読み込みエラー (Error reading file: {e})"
                files_data.append((f.name, content))
            return render_template_string(TEMPLATE, files=files_data)

        def _is_safe_filename(filename):
            """
            ファイル名が安全かどうかを検証する
            (ご提案 #3 に基づき正規表現チェックを追加)
            """
            if not filename:
                return False
            # ディレクトリトラバーサル攻撃のチェック
            if ".." in filename or "/" in filename or "\\" in filename or filename.startswith("/"):
                return False
            # ファイル名の規則を厳密に確認（`pending_` で始まり `.json` で終わる）
            if not (filename.startswith("pending_") and filename.endswith(".json")):
                logger.warning(f"[WEB-UI] Filename format mismatch: {filename}")
                return False
            
            # (ご提案 #3 拡張) コア部分（pending_ と .json の間）の文字を厳密にチェック
            # タイムスタンプ (数字) や UUID (英数字ハイフン) を想定
            core_filename = filename[len("pending_"):-len(".json")]
            if not core_filename: # pending_.json は不正
                 logger.warning(f"[WEB-UI] Filename has empty core: {filename}")
                 return False
            # \w (英数字[a-zA-Z0-9_]) とハイフン (-) 以外の文字が含まれていないかチェック
            if re.search(r'[^\w\-]', core_filename): 
                logger.warning(f"[WEB-UI] Filename core contains invalid characters: {filename}")
                return False

            return True

        @app.route("/approve/<filename>")
        def approve(filename):
            if not _is_safe_filename(filename):
                logger.warning(f"[WEB-UI] Invalid path/filename detected in approve: {filename}")
                # (ご提案 #3 に基づき flash メッセージを設定)
                flash(f"無効なファイル名です: {filename}", "danger")
                return redirect(url_for('index'))
            try:
                file_path = agent.amendments_dir.joinpath(filename).resolve()
                if file_path.parent != agent.amendments_dir.resolve():
                    logger.error(f"[WEB-UI] Resolved path mismatch (Security Breach Attempt?): {file_path}")
                    flash("セキュリティ違反が検出されました。", "danger")
                    return redirect(url_for('index'))
                    
                # (ご提案 #4 の確認: 成功/失敗メッセージを分岐)
                if agent.approve_amendment(file_path):
                    flash(f"改正案 '{filename}' は正常に承認されました。", "success")
                else:
                    # (ご提案 #3 のアーカイブ失敗時 flash をここで追加)
                    # approve_amendment が False を返した場合、アーカイブ失敗か他のエラーか
                    if not (agent.amendments_dir / filename).exists():
                         # ファイルが存在しない = アーカイブ成功 (他の理由で失敗した？)
                         # → approve_amendment のロジックでは、アーカイブ失敗時に False を返す
                         #   しかし、ファイルは既にリネームされている。
                         #   したがって、アーカイブ失敗の検知は「ファイルがまだ存在するか」で行う
                         #   (リネーム失敗 = ファイルがまだ 'pending_' として存在する)
                        flash(f"改正案 '{filename}' の承認に失敗しました。ログを確認してください。", "danger")
                    else:
                         # アーカイブ失敗 (approve_amendment が False を返し、ファイルがまだ存在する)
                        flash(f"改正案 '{filename}' のアーカイブに失敗しました。ポリシーは更新されましたが、手動でのファイル確認が必要です。", "danger")
                    
            except Exception as e:
                logger.error(f"[WEB-UI] Error during approval of {filename}: {e}")
                flash(f"承認処理中に予期せぬエラーが発生しました: {e}", "danger")
            return redirect(url_for('index'))

        @app.route("/reject/<filename>")
        def reject(filename):
            if not _is_safe_filename(filename):
                logger.warning(f"[WEB-UI] Invalid path/filename detected in reject: {filename}")
                # (ご提案 #3 に基づき flash メッセージを設定)
                flash(f"無効なファイル名です: {filename}", "danger")
                return redirect(url_for('index'))
            try:
                file_path = agent.amendments_dir.joinpath(filename).resolve()
                if file_path.parent != agent.amendments_dir.resolve():
                    logger.error(f"[WEB-UI] Resolved path mismatch (Security Breach Attempt?): {file_path}")
                    flash("セキュリティ違反が検出されました。", "danger")
                    return redirect(url_for('index'))

                # (ご提案 #4 の確認: 成功/失敗メッセージを分岐)
                if agent.reject_amendment(file_path):
                    flash(f"改正案 '{filename}' は正常に却下されました。", "info")
                else:
                    # (ご提案 #3 のアーカイブ失敗時 flash をここで追加)
                    flash(f"改正案 '{filename}' の却下（アーカイブ）に失敗しました。ログを確認してください。", "danger")
                    
            except Exception as e:
                logger.error(f"[WEB-UI] Error during rejection of {filename}: {e}")
                flash(f"却下処理中に予期せぬエラーが発生しました: {e}", "danger")
            return redirect(url_for('index'))

        logger.info(f"[Council] Starting Web UI at http://{host}:{port}")
        app.run(host=host, port=port)

# スクリプトとして直接実行された場合の動作（CLIメニューまたはWeb UIの起動）
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # このエージェントはBaseAgentのLLM機能(execute_llm_task)に依存する
    # BaseAgentがLLMRouterや設定を適切にロードできるよう、
    # 本来は main.py や上位のファクトリ経由で初期化される想定。
    # ここでは、デバッグ用に直接インスタンス化する。
    
    # 注意: このスタンドアロン実行では、BaseAgentが依存する
    # LLMRouterが正しく初期化されない可能性があります。
    # Web UI / CLI の「承認/却下」機能のテストは可能ですが、
    # 「review_and_amend」の実行は失敗する可能性が高いです。
    
    council_agent = ConstitutionalCouncilAgent()
    
    if len(sys.argv) > 1 and sys.argv[1] == 'web':
        print("Starting Web UI mode...")
        print("NOTE: 'review_and_amend' (LLM call) may not work in standalone mode.")
        # (ご提案 #6 の確認: 警告メッセージは維持)
        if os.getenv('FLASK_SECRET_KEY') is None:
            print("WARNING: 'FLASK_SECRET_KEY' env var not set. Using insecure fallback key.")
        council_agent.run_web_ui()
    else:
        print("Starting CLI mode...")
        print("NOTE: 'review_and_amend' (LLM call) may not work in standalone mode.")
        council_agent.cli_menu()

