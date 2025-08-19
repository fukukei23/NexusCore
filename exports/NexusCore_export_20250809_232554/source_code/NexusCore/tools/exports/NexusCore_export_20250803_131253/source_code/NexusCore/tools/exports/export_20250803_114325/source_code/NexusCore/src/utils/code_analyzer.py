# src/utils/code_analyzer.py

import subprocess
import re
import json

def run_pylint(file_path: str) -> float:
    """指定されたファイルに対してPylintを実行し、スコアを返す"""
    print(f"🔬 Running Pylint on {file_path}...")
    command = ["pylint", file_path]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        output = result.stdout
        match = re.search(r"Your code has been rated at (\d+\.\d+)/10", output)
        if match:
            score = float(match.group(1))
            print(f"✅ Pylint score: {score}/10")
            return score
        print(f"⚠️ Pylint score not found in output.")
        return 0.0
    except Exception as e:
        print(f"🚨 An error occurred while running Pylint: {e}")
        return 0.0

def run_mypy(file_path: str) -> tuple[bool, str]:
    """指定されたファイルに対してMyPyを実行し、(成功フラグ, 結果メッセージ)を返す"""
    print(f"🔬 Running MyPy on {file_path}...")
    command = ["mypy", file_path]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        output = result.stdout + result.stderr
        if "Success: no issues found" in output:
            print("✅ MyPy found no issues.")
            return True, "Passed"
        else:
            error_summary = "\n".join(line for line in output.splitlines() if "error:" in line)
            print(f"❌ MyPy found issues.")
            return False, error_summary
    except Exception as e:
        print(f"🚨 An error occurred while running MyPy: {e}")
        return False, str(e)

def run_bandit(target_path: str) -> tuple[bool, str]:
    """指定されたパスに対してBanditを実行し、(成功フラグ, 結果メッセージ)を返す"""
    print(f"🔬 Running Bandit security scan on {target_path}...")
    command = ["bandit", "-r", target_path, "-f", "json"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        report = json.loads(result.stdout)
        high_medium_issues = [
            f"- {res['issue_text']} (Severity: {res['issue_severity']}, File: {res['filename']}:{res['line_number']})"
            for res in report["results"]
            if res["issue_severity"] in ["HIGH", "MEDIUM"]
        ]
        if not high_medium_issues:
            print("✅ Bandit: No high or medium severity issues found.")
            return True, "Passed"
        else:
            issue_summary = "\n".join(high_medium_issues)
            print("❌ Bandit found security issues.")
            return False, issue_summary
    except json.JSONDecodeError:
        print("✅ Bandit: No security issues reported.")
        return True, "Passed"
    except Exception as e:
        print(f"🚨 An error occurred while running Bandit: {e}")
        return False, str(e)

def run_pytest_cov(project_path: str) -> float:
    """
    指定されたプロジェクトパスを基準にテストとカバレッジ計測を実行する。
    設定はpyproject.tomlから読み込まれる。
    """
    print(f"🔬 Running pytest-cov on {project_path}...")
    # 設定ファイルがあるので、コマンドはシンプルに 'pytest' だけで良い
    command = ["pytest"]
    try:
        # cwdを指定して、対象プロジェクトのルートでコマンドを実行する
        result = subprocess.run(
            command,
            cwd=project_path,  # これが重要！
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        output = result.stdout
        match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", output)
        if match:
            coverage = float(match.group(1))
            print(f"✅ Pytest-cov coverage: {coverage}%")
            return coverage
        print(f"⚠️ Pytest-cov coverage not found. Output:\n{output}")
        return 0.0
    except Exception as e:
        print(f"🚨 An error occurred while running pytest-cov: {e}")
        return 0.0