#!/usr/bin/env python3
"""
STIT Branch Automation CLI Tool

This script provides CLI commands for STIT workflow automation.
It implements safety features based on risk mitigation strategies.

Usage:
    python stit_branch.py create -t cr-051 -d retry-policy
    python stit_branch.py create -t cr-051 -d retry-policy --dry-run
    python stit_branch.py validate -b claude/cr-051-retry-policy
    python stit_branch.py approve -r 123
"""

import argparse
import os
import sys
import subprocess
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Optional


# =============================================================================
# Version Info
# =============================================================================

__version__ = "1.1.0"
__author__ = "NexusCore Team"


# =============================================================================
# Configuration
# =============================================================================

BRANCH_PREFIXES = {
    "claude": "AI開発ブランチ",
    "rescue": "救出用・再試行ブランチ",
    "feature": "機能開発（通常）",
    "hotfix": "緊急修正",
}

DEFAULT_PREFIX = "claude"

RISK_MITIGATION = {
    "dry_run": True,
    "validation": True,
    "atomic_operation": True,
    "read_only_mode": False,
}

# Colors for terminal output (ANSI codes)
class Colors:
    """Terminal color codes with Windows compatibility."""
    RESET = "\033[0m" if sys.stdout.isatty() else ""
    BOLD = "\033[1m" if sys.stdout.isatty() else ""

    # Foreground colors
    BLACK = "\033[30m" if sys.stdout.isatty() else ""
    RED = "\033[31m" if sys.stdout.isatty() else ""
    GREEN = "\033[32m" if sys.stdout.isatty() else ""
    YELLOW = "\033[33m" if sys.stdout.isatty() else ""
    BLUE = "\033[34m" if sys.stdout.isatty() else ""
    MAGENTA = "\033[35m" if sys.stdout.isatty() else ""
    CYAN = "\033[36m" if sys.stdout.isatty() else ""
    WHITE = "\033[37m" if sys.stdout.isatty() else ""

    # Background colors
    BG_RED = "\033[41m" if sys.stdout.isatty() else ""
    BG_GREEN = "\033[42m" if sys.stdout.isatty() else ""
    BG_YELLOW = "\033[43m" if sys.stdout.isatty() else ""

    # Styles
    DIM = "\033[2m" if sys.stdout.isatty() else ""


# =============================================================================
# Utility Functions
# =============================================================================

def print_header(text: str, dry_run: bool = False) -> None:
    """Print a formatted header."""
    status = f"{Colors.YELLOW}[DRY-RUN]{Colors.RESET} " if dry_run else ""
    print(f"\n{Colors.BOLD}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}STIT Branch Automation v{__version__}{Colors.RESET} {status}- Risk Mitigation Active")
    print(f"{Colors.BOLD}{'=' * 60}{Colors.RESET}")


def print_section(title: str, dry_run: bool = False) -> None:
    """Print a section header."""
    prefix = f"{Colors.YELLOW}[DRY-RUN] {Colors.RESET}" if dry_run else ""
    print(f"\n{prefix}{Colors.BOLD}[{title}]{Colors.RESET}")


def print_success(message: str) -> None:
    """Print a success message."""
    print(f"\n{Colors.GREEN}[SUCCESS]{Colors.RESET} {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    print(f"\n{Colors.RED}[ERROR]{Colors.RESET} {message}", file=sys.stderr)


def print_warning(message: str) -> None:
    """Print a warning message."""
    print(f"\n{Colors.YELLOW}[WARNING]{Colors.RESET} {message}")


def print_info(label: str, value: str, dry_run: bool = False) -> None:
    """Print an info line."""
    prefix = f"{Colors.YELLOW}[DRY-RUN]{Colors.RESET} " if dry_run else ""
    print(f"{prefix}{Colors.CYAN}{label}:{Colors.RESET} {value}")


def get_current_branch() -> Optional[str]:
    """Get the current git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception:
        return None


def get_git_remote() -> Optional[str]:
    """Get the git remote URL (origin)."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception:
        return None


# =============================================================================
# Configuration File
# =============================================================================

CONFIG_FILE = Path.home() / ".stit_branch_config.json"


def load_config() -> dict:
    """Load configuration from file."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_config(config: dict) -> None:
    """Save configuration to file."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_default_prefix() -> str:
    """Get the default prefix from config or use DEFAULT_PREFIX."""
    config = load_config()
    return config.get("default_prefix", DEFAULT_PREFIX)


# =============================================================================
# Risk Mitigation Functions
# =============================================================================

def validate_branch_name(branch_name: str) -> tuple[bool, str]:
    """
    Validate branch name against naming conventions.

    Returns:
        tuple: (is_valid, error_message)
    """
    if not branch_name:
        return False, "ブランチ名が空です"

    # Check for dangerous patterns
    dangerous_patterns = [
        (r"\.\.", "Double dots (..)"),
        (r"~", "Tilde (~)"),
        (r"\^", "Caret (^)"),
        (r":", "Colon (:)"),
        (r"^\.", "Starts with dot (.)"),
        (r"@\{", "Ref syntax (@{)"),
    ]

    for pattern, description in dangerous_patterns:
        if re.search(pattern, branch_name):
            return False, f"危険なパターンが検出されました: {description}"

    # Check prefix validity
    prefix = branch_name.split("/")[0] if "/" in branch_name else ""
    if prefix and prefix not in BRANCH_PREFIXES:
        valid_prefixes = ", ".join(BRANCH_PREFIXES.keys())
        return False, f"未知の接頭辞: '{prefix}'。有効な接頭辞: {valid_prefixes}"

    # Check branch name length
    if len(branch_name) > 100:
        return False, "ブランチ名が長すぎます（100文字以内）"

    # Check for spaces
    if " " in branch_name:
        return False, "ブランチ名にスペースは含めません（Dash を使用してください）"

    # Check for uppercase letters (convention)
    if branch_name != branch_name.lower():
        return False, "ブランチ名は大文字を含みません（すべて小文字）"

    return True, ""


def validate_task_id(task_id: str) -> tuple[bool, str]:
    """
    Validate task ID format.

    Expected format: cr-XXX (e.g., cr-051)
    """
    if not task_id:
        return False, "タスクIDが空です"

    pattern = r"^cr-\d{3}$"
    if not re.match(pattern, task_id):
        return False, f"無効なタスクID形式: '{task_id}'。期待形式: cr-XXX (例: cr-051)"

    return True, ""


def git_operation(command: list[str], dry_run: bool = False, check_remote: bool = False) -> tuple[bool, str]:
    """
    Execute git operation with safety checks.

    Args:
        command: Git command as list of strings
        dry_run: If True, only print command without executing
        check_remote: If True, check if remote exists first

    Returns:
        tuple: (success, output)
    """
    if RISK_MITIGATION["read_only_mode"] and not dry_run:
        return False, "読み取り専用モードが有効です。操作をスキップしました。"

    cmd_str = " ".join(command)

    if dry_run:
        print_info("Executing", cmd_str)
        return True, cmd_str

    # Check remote first if needed
    if check_remote and "push" in cmd_str:
        remote = get_git_remote()
        if not remote:
            return False, "リモートリポジトリが設定されていません"

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return False, f"Git command failed: {result.stderr.strip()}"

        return True, result.stdout.strip()

    except subprocess.TimeoutExpired:
        return False, "Git command timed out"
    except FileNotFoundError:
        return False, "Git command not found. Please install git."
    except Exception as e:
        return False, f"Git command error: {str(e)}"


# =============================================================================
# Branch Creation Functions
# =============================================================================

def generate_branch_name(prefix: str, task_id: str, description: str) -> str:
    """
    Generate branch name according to naming conventions.

    Format: {prefix}/{cr-XXX}-{description}

    Examples:
        - claude/cr-051-retry-policy
        - feature/user-authentication
        - hotfix/security-fix
    """
    # Sanitize description
    description = re.sub(r"[^a-zA-Z0-9\-]", "-", description)
    description = re.sub(r"-+", "-", description)  # Remove duplicate dashes
    description = description.strip("-")
    description = description.lower()  # Force lowercase

    return f"{prefix}/{task_id}-{description}"


def create_branch(
    task_id: str,
    description: str,
    prefix: Optional[str] = None,
    dry_run: bool = False,
    push: bool = False,
) -> tuple[bool, str]:
    """
    Create and optionally push a new branch for STIT workflow.

    Args:
        task_id: Task ID (e.g., cr-051)
        description: Brief description of the task
        prefix: Branch prefix (claude/rescue/feature/hotfix)
        dry_run: If True, only show what would be done
        push: If True, push the branch to remote

    Returns:
        tuple: (success, message)
    """
    # Use default prefix if not specified
    if prefix is None:
        prefix = get_default_prefix()

    # Validation
    is_valid, error = validate_task_id(task_id)
    if not is_valid:
        return False, f"タスクID検証失敗: {error}"

    branch_name = generate_branch_name(prefix, task_id, description)

    is_valid, error = validate_branch_name(branch_name)
    if not is_valid:
        return False, f"ブランチ名検証失敗: {error}"

    # Print risk mitigation info
    print_header("STIT Branch Automation", dry_run)

    print_info("Prefix", f"{prefix} ({BRANCH_PREFIXES.get(prefix, 'Unknown')})", dry_run)
    print_info("Task ID", task_id, dry_run)
    print_info("Description", description, dry_run)
    print_info("Branch Name", branch_name, dry_run)
    print_info("Dry Run", "Yes" if dry_run else "No", dry_run)
    print_info("Push", "Yes" if push else "No", dry_run)

    # Get current branch
    current_branch = get_current_branch()
    if current_branch:
        print_info("Current Branch", current_branch, dry_run)

    # Create branch
    print_section("Creating Branch", dry_run)
    success, output = git_operation(
        ["git", "checkout", "-b", branch_name],
        dry_run
    )

    if not success:
        return False, f"ブランチ作成失敗: {output}"

    print_success(f"Branch created: {branch_name}")

    # Optionally push
    if push:
        print_section("Pushing to Remote", dry_run)
        success, output = git_operation(
            ["git", "push", "-u", "origin", branch_name],
            dry_run,
            check_remote=True
        )

        if not success:
            return False, f"プッシュ失敗: {output}"

        print_success(f"Pushed to origin: {branch_name}")

    # Summary
    print_section("Operation Summary", dry_run)
    print(f"  {Colors.BOLD}Branch:{Colors.RESET} {branch_name}")

    if not push:
        push_cmd = f"git push -u origin {branch_name}"
        print(f"  {Colors.BOLD}Push Command:{Colors.RESET} {push_cmd}")

    return True, f"ブランチ作成完了: {branch_name}"


def validate_branch(branch_name: str, verbose: bool = False) -> tuple[bool, str]:
    """
    Validate an existing branch name against conventions.

    Args:
        branch_name: Branch name to validate
        verbose: If True, show detailed validation results

    Returns:
        tuple: (is_valid, message)
    """
    is_valid, error = validate_branch_name(branch_name)

    if is_valid:
        prefix = branch_name.split("/")[0] if "/" in branch_name else ""
        prefix_desc = BRANCH_PREFIXES.get(prefix, "Unknown")
        return True, f"ブランチ名 '{branch_name}' は命名規則に準拠しています ({prefix_desc})"

    return False, f"ブランチ名 '{branch_name}' に問題があります: {error}"


def delete_branch(branch_name: str, force: bool = False, dry_run: bool = False) -> tuple[bool, str]:
    """
    Delete a local branch.

    Args:
        branch_name: Branch name to delete
        force: If True, force delete
        dry_run: If True, only show what would be done

    Returns:
        tuple: (success, message)
    """
    # Validation
    is_valid, error = validate_branch_name(branch_name)
    if not is_valid:
        return False, f"ブランチ名検証失敗: {error}"

    print_header("Delete Branch", dry_run)
    print_info("Branch Name", branch_name, dry_run)
    print_info("Force Delete", "Yes" if force else "No", dry_run)

    # Check if branch exists
    success, output = git_operation(["git", "rev-parse", "--verify", branch_name], dry_run)
    if not success:
        return False, f"ブランチ '{branch_name}' は存在しません"

    # Delete branch
    cmd = ["git", "branch", "-D" if force else "-d", branch_name]
    success, output = git_operation(cmd, dry_run)

    if not success:
        return False, f"ブランチ削除失敗: {output}"

    print_success(f"Branch deleted: {branch_name}")
    return True, f"ブランチ削除完了: {branch_name}"


def list_branches(prefix: Optional[str] = None, remote: bool = False) -> tuple[bool, list[str]]:
    """
    List branches with optional filtering.

    Args:
        prefix: Filter by prefix (e.g., 'claude')
        remote: If True, list remote branches

    Returns:
        tuple: (success, list of branch names)
    """
    cmd = ["git", "branch", "-a" if remote else "-l"]

    success, output = git_operation(cmd)
    if not success:
        return False, []

    branches = []
    for line in output.split("\n"):
        line = line.strip()
        if not line:
            continue

        # Remove branch indicator (* for current branch)
        line = line.lstrip("* ").strip()

        if remote:
            # Handle remotes/origin/branch format
            if line.startswith("remotes/"):
                line = "/".join(line.split("/", 2)[1:])  # Remove 'remotes/'

        # Filter by prefix if specified
        if prefix:
            if line.startswith(f"{prefix}/"):
                branches.append(line)
        else:
            branches.append(line)

    return True, sorted(branches)


# =============================================================================
# Approval System (Phase 3)
# =============================================================================

APPROVAL_FILE = Path(".stit_approvals.json")


def load_approvals() -> dict:
    """Load approvals from file."""
    if APPROVAL_FILE.exists():
        try:
            with open(APPROVAL_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_approvals(approvals: dict) -> None:
    """Save approvals to file."""
    with open(APPROVAL_FILE, "w", encoding="utf-8") as f:
        json.dump(approvals, f, indent=2, ensure_ascii=False)


def create_approval_request(
    branch_name: str,
    task_id: str,
    description: str,
    requester: str = "AI",
) -> tuple[bool, str]:
    """
    Create an approval request for a branch.

    Args:
        branch_name: Name of the branch
        task_id: Task ID (e.g., cr-051)
        description: Brief description
        requester: Who is requesting (AI or human)

    Returns:
        tuple: (success, request_id)
    """
    approvals = load_approvals()

    # Generate request ID
    request_id = f"SR-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    approvals[request_id] = {
        "branch_name": branch_name,
        "task_id": task_id,
        "description": description,
        "requester": requester,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "approved_by": None,
        "approved_at": None,
        "comments": [],
    }

    save_approvals(approvals)

    return True, request_id


def approve_request(request_id: str, approver: str, comment: Optional[str] = None) -> tuple[bool, str]:
    """
    Approve an approval request.

    Args:
        request_id: Request ID to approve
        approver: Who is approving
        comment: Optional comment

    Returns:
        tuple: (success, message)
    """
    approvals = load_approvals()

    if request_id not in approvals:
        return False, f"リクエスト '{request_id}' が見つかりません"

    if approvals[request_id]["status"] != "pending":
        return False, f"リクエストはすでに '{approvals[request_id]['status']}' です"

    approvals[request_id]["status"] = "approved"
    approvals[request_id]["approved_by"] = approver
    approvals[request_id]["approved_at"] = datetime.now().isoformat()

    if comment:
        approvals[request_id]["comments"].append({
            "author": approver,
            "comment": comment,
            "timestamp": datetime.now().isoformat(),
        })

    save_approvals(approvals)

    return True, f"リクエスト '{request_id}' が承認されました"


def reject_request(request_id: str, rejecter: str, reason: str) -> tuple[bool, str]:
    """
    Reject an approval request.

    Args:
        request_id: Request ID to reject
        rejecter: Who is rejecting
        reason: Rejection reason

    Returns:
        tuple: (success, message)
    """
    approvals = load_approvals()

    if request_id not in approvals:
        return False, f"リクエスト '{request_id}' が見つかりません"

    approvals[request_id]["status"] = "rejected"
    approvals[request_id]["rejected_by"] = rejecter
    approvals[request_id]["rejected_at"] = datetime.now().isoformat()
    approvals[request_id]["rejection_reason"] = reason

    save_approvals(approvals)

    return True, f"リクエスト '{request_id}' が却下されました"


def list_pending_requests() -> list[dict]:
    """List all pending approval requests."""
    approvals = load_approvals()
    return [v for v in approvals.values() if v["status"] == "pending"]


# =============================================================================
# Main CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description=f"{Colors.BOLD}STIT Branch Automation CLI Tool v{__version__}{Colors.RESET}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
{Colors.BOLD}Examples:{Colors.RESET}
    # Create a branch (always dry-run first!)
    $ python stit_branch.py create -t cr-051 -d retry-policy --dry-run

    # Actually create the branch
    $ python stit_branch.py create -t cr-051 -d retry-policy --push

    # Validate a branch name
    $ python stit_branch.py validate -b claude/cr-051-retry-policy

    # List branches by prefix
    $ python stit_branch.py list -p claude

    # Create approval request
    $ python stit_branch.py request -b claude/cr-051 -t cr-051 -d "retry policy"

    # Approve a request
    $ python stit_branch.py approve -r SR-20260204120000 -a "human-reviewer"

{Colors.BOLD}Risk Mitigation:{Colors.RESET}
    --dry-run       Show what would be done without executing (ALWAYS USE FIRST)
    --read-only    Enable read-only mode for safe testing
    --verbose      Show detailed validation results

{Colors.BOLD}Quick Links:{Colors.RESET}
    GitHub: https://github.com/fukukei23/NexusCore
    Docs:   docs/integrations/GITHUB_STIT_WORKFLOW.md
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Version command
    parser.add_argument(
        "--version", "-V",
        action="version",
        version=f"STIT Branch Automation v{__version__}"
    )

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new STIT branch")
    create_parser.add_argument(
        "--task-id", "-t",
        required=True,
        help="Task ID (e.g., cr-051)"
    )
    create_parser.add_argument(
        "--desc", "-d",
        required=True,
        help="Brief description of the task"
    )
    create_parser.add_argument(
        "--prefix", "-p",
        choices=list(BRANCH_PREFIXES.keys()),
        help=f"Branch prefix (default: {DEFAULT_PREFIX})"
    )
    create_parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be done without executing"
    )
    create_parser.add_argument(
        "--push", "-u",
        action="store_true",
        help="Push the branch to remote after creation"
    )

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate a branch name")
    validate_parser.add_argument(
        "--branch-name", "-b",
        required=True,
        help="Branch name to validate"
    )
    validate_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed validation results"
    )

    # List command
    list_parser = subparsers.add_parser("list", help="List branches")
    list_parser.add_argument(
        "--prefix", "-p",
        choices=list(BRANCH_PREFIXES.keys()),
        help="Filter by prefix"
    )
    list_parser.add_argument(
        "--remote", "-r",
        action="store_true",
        help="List remote branches"
    )

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a branch")
    delete_parser.add_argument(
        "--branch-name", "-b",
        required=True,
        help="Branch name to delete"
    )
    delete_parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force delete (even if not merged)"
    )
    delete_parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be done without executing"
    )

    # Request command (Phase 3)
    request_parser = subparsers.add_parser("request", help="Create an approval request")
    request_parser.add_argument(
        "--branch", "-b",
        required=True,
        help="Branch name for the request"
    )
    request_parser.add_argument(
        "--task-id", "-t",
        required=True,
        help="Task ID"
    )
    request_parser.add_argument(
        "--desc", "-d",
        required=True,
        help="Brief description"
    )
    request_parser.add_argument(
        "--requester", "-r",
        default="AI",
        help="Requester name (default: AI)"
    )

    # Approve command (Phase 3)
    approve_parser = subparsers.add_parser("approve", help="Approve a request")
    approve_parser.add_argument(
        "--request-id", "-r",
        required=True,
        help="Request ID to approve"
    )
    approve_parser.add_argument(
        "--approver", "-a",
        required=True,
        help="Approver name"
    )
    approve_parser.add_argument(
        "--comment", "-c",
        help="Optional comment"
    )

    # Reject command (Phase 3)
    reject_parser = subparsers.add_parser("reject", help="Reject a request")
    reject_parser.add_argument(
        "--request-id", "-r",
        required=True,
        help="Request ID to reject"
    )
    reject_parser.add_argument(
        "--rejecter", "-a",
        required=True,
        help="Rejecter name"
    )
    reject_parser.add_argument(
        "--reason", "-R",
        required=True,
        help="Rejection reason"
    )

    # Pending command (Phase 3)
    pending_parser = subparsers.add_parser("pending", help="List pending requests")

    # Config command
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_parser.add_argument(
        "--default-prefix", "-p",
        choices=list(BRANCH_PREFIXES.keys()),
        help="Set default prefix"
    )
    config_parser.add_argument(
        "--show", "-s",
        action="store_true",
        help="Show current configuration"
    )

    # Global options
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="Enable read-only mode (safe for testing)"
    )

    args = parser.parse_args()

    # Apply global options
    if args.read_only:
        RISK_MITIGATION["read_only_mode"] = True
        print_warning("Read-only mode enabled. No actual changes will be made.\n")

    # Execute command
    try:
        if args.command == "create":
            success, message = create_branch(
                task_id=args.task_id,
                description=args.desc,
                prefix=args.prefix,
                dry_run=args.dry_run or RISK_MITIGATION["read_only_mode"],
                push=args.push and not RISK_MITIGATION["read_only_mode"],
            )

            if not success:
                print_error(message)
                sys.exit(1)

            print_success(message)
            sys.exit(0)

        elif args.command == "validate":
            is_valid, message = validate_branch(args.branch_name, args.verbose)

            if is_valid:
                print_success(message)
                sys.exit(0)
            else:
                print_error(message)
                sys.exit(1)

        elif args.command == "list":
            success, branches = list_branches(args.prefix, args.remote)

            if success:
                print(f"\n{Colors.BOLD}Branches:{Colors.RESET}")
                for branch in branches:
                    print(f"  - {branch}")
                sys.exit(0)
            else:
                print_error("Failed to list branches")
                sys.exit(1)

        elif args.command == "delete":
            success, message = delete_branch(
                args.branch_name,
                force=args.force,
                dry_run=args.dry_run or RISK_MITIGATION["read_only_mode"],
            )

            if not success:
                print_error(message)
                sys.exit(1)

            print_success(message)
            sys.exit(0)

        elif args.command == "request":
            success, request_id = create_approval_request(
                args.branch,
                args.task_id,
                args.desc,
                args.requester,
            )

            if success:
                print_success(f"Approval request created: {request_id}")
                print(f"  Use: python stit_branch.py approve -r {request_id} -a <name>")
                sys.exit(0)
            else:
                print_error(request_id)
                sys.exit(1)

        elif args.command == "approve":
            success, message = approve_request(
                args.request_id,
                args.approver,
                args.comment,
            )

            if success:
                print_success(message)
                sys.exit(0)
            else:
                print_error(message)
                sys.exit(1)

        elif args.command == "reject":
            success, message = reject_request(
                args.request_id,
                args.rejecter,
                args.reason,
            )

            if success:
                print_success(message)
                sys.exit(0)
            else:
                print_error(message)
                sys.exit(1)

        elif args.command == "pending":
            requests = list_pending_requests()

            if requests:
                print(f"\n{Colors.BOLD}Pending Requests:{Colors.RESET}")
                for req in requests:
                    print(f"  - {req['branch_name']} ({req['task_id']}): {req['description']}")
                sys.exit(0)
            else:
                print_success("No pending requests")
                sys.exit(0)

        elif args.command == "config":
            if args.show:
                config = load_config()
                print(f"\n{Colors.BOLD}Current Configuration:{Colors.RESET}")
                print(f"  Default Prefix: {config.get('default_prefix', DEFAULT_PREFIX)}")
                sys.exit(0)

            if args.default_prefix:
                config = load_config()
                config["default_prefix"] = args.default_prefix
                save_config(config)
                print_success(f"Default prefix set to: {args.default_prefix}")
                sys.exit(0)

            parser.print_help()
            sys.exit(0)

        else:
            parser.print_help()
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(130)
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
