from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def clone_or_update_repo(
    *,
    repo_full_name: str,
    pr_number: int,
    head_sha: str,
    target_dir: Path,
) -> None:
    """
    sandbox ディレクトリに対象リポジトリを clone し、指定の head_sha を checkout する。

    優先度:
      1. 環境変数 NEXUS_REPO_BASE_DIR が設定されている場合:
         - そこに {owner}/{repo} が既に clone 済みである前提で、そこからコピーする
      2. それ以外:
         - https://github.com/{repo_full_name}.git を clone する（public repo 想定）

    認証が必要な場合は、NEXUS_GITHUB_CLONE_URL_TEMPLATE を使う:
      例) "https://x-access-token:{TOKEN}@github.com/{repo_full_name}.git"
    """
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.parent.mkdir(parents=True, exist_ok=True)

    base_dir = os.getenv("NEXUS_REPO_BASE_DIR")
    if base_dir:
        from_repo = Path(base_dir) / repo_full_name
        if from_repo.exists():
            logger.info(f"Copying existing repo from {from_repo} to sandbox {target_dir}")
            shutil.copytree(from_repo, target_dir)
        else:
            logger.warning(
                f"NEXUS_REPO_BASE_DIR is set but repo {from_repo} does not exist. "
                f"Falling back to direct clone."
            )

    if not target_dir.exists():
        template = os.getenv("NEXUS_GITHUB_CLONE_URL_TEMPLATE")
        if template:
            if "{repo_full_name}" in template:
                clone_url = template.format(repo_full_name=repo_full_name)
            else:
                clone_url = template
        else:
            clone_url = f"https://github.com/{repo_full_name}.git"

        logger.info(f"Cloning repo: {clone_url} -> {target_dir}")
        try:
            subprocess.run(
                ["git", "clone", clone_url, str(target_dir)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"git clone failed: {e.stdout}", exc_info=True)
            raise

    try:
        logger.info(f"Checking out commit {head_sha} in {target_dir}")
        subprocess.run(
            ["git", "-C", str(target_dir), "checkout", head_sha],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"git checkout {head_sha} failed: {e.stdout}", exc_info=True)
        raise


def get_changed_files(
    project_path: Path,
    base_ref: str | None,
    head_ref: str | None,
) -> list[str]:
    """
    PR で変更されたファイル一覧を git diff から取得する。

    優先度:
      1. base_ref / head_ref が指定されている場合:
         - git diff --name-only base_ref...head_ref
      2. それ以外:
         - 直近のコミット差分: git diff --name-only HEAD~1..HEAD
    """
    try:
        if base_ref and head_ref:
            diff_range = f"{base_ref}...{head_ref}"
            cmd = ["git", "-C", str(project_path), "diff", "--name-only", diff_range]
        else:
            cmd = ["git", "-C", str(project_path), "diff", "--name-only", "HEAD~1..HEAD"]

        logger.info(f"Running git diff to get changed files: {' '.join(cmd)}")
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        if proc.returncode != 0:
            logger.warning(f"git diff failed (code={proc.returncode}): {proc.stderr}")
            return []

        files: list[str] = []
        for line in proc.stdout.splitlines():
            path = line.strip()
            if path:
                files.append(path)

        return files
    except Exception as e:
        logger.error(f"get_changed_files failed: {e}", exc_info=True)
        return []
