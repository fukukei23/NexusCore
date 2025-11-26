#!/usr/bin/env python3
"""
WSL環境でテストを実行するラッパースクリプト
WindowsからでもWSL経由でテストを実行できる
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

def run_wsl_command(cmd: str) -> int:
    """WSLでコマンドを実行"""
    try:
        # WSL経由でコマンドを実行
        result = subprocess.run(
            ["wsl", "bash", "-c", cmd],
            capture_output=True,
            text=True,
            check=False,
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result.returncode
    except FileNotFoundError:
        print("Error: WSL not found. Please run this from WSL terminal directly.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

def main():
    project_root = Path(__file__).parent.parent
    test_target = sys.argv[1] if len(sys.argv) > 1 else "tests/"

    cmd = f"""
cd /home/yn441611/NexusCore && \
source myenv_linux/bin/activate && \
python -m pytest {test_target} -v
"""

    print(f"Running tests in WSL: {test_target}")
    print("-" * 60)
    exit_code = run_wsl_command(cmd)
    print("-" * 60)

    if exit_code == 0:
        print("✅ Tests passed!")
    else:
        print(f"❌ Tests failed with exit code {exit_code}")

    return exit_code

if __name__ == "__main__":
    sys.exit(main())

