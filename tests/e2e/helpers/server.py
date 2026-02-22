"""
FastAPI サーバー起動ヘルパー

uvicorn をサブプロセスでバックグラウンド起動し、E2E テストで使用する。
"""

from __future__ import annotations

import subprocess
import time
import urllib.request
from pathlib import Path

# プロジェクトルートを取得
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


def start_fastapi_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    python_path: str | None = None,
) -> subprocess.Popen:
    """
    FastAPI アプリを uvicorn でバックグラウンド起動する。

    Args:
        host: サーバーのホスト名（デフォルト: 127.0.0.1）
        port: サーバーのポート番号（デフォルト: 8000）
        python_path: Python 実行パス（None の場合はシステムの python を使用）

    Returns:
        subprocess.Popen: 起動したプロセスの Popen オブジェクト

    Raises:
        RuntimeError: サーバーの起動に失敗した場合
    """
    if python_path is None:
        python_path = "python"

    # PYTHONPATH を設定して FastAPI アプリを起動
    env = {
        **subprocess.os.environ.copy(),
        "PYTHONPATH": str(PROJECT_ROOT / "src"),
    }

    cmd = [
        python_path,
        "-m",
        "uvicorn",
        "nexuscore.api.fastapi_app:app",
        "--host",
        host,
        "--port",
        str(port),
    ]

    try:
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(PROJECT_ROOT),
        )
        return process
    except Exception as e:
        raise RuntimeError(f"Failed to start FastAPI server: {e}") from e


def wait_for_server(url: str, timeout: int = 30) -> bool:
    """
    サーバーが起動するまで待機する。

    Args:
        url: サーバーの URL（例: http://127.0.0.1:8000/api/v1/health）
        timeout: タイムアウト時間（秒、デフォルト: 30）

    Returns:
        bool: サーバーが起動した場合 True、タイムアウトした場合 False
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(0.5)
    return False


def stop_fastapi_server(process: subprocess.Popen) -> None:
    """
    FastAPI サーバーを停止する。

    Args:
        process: 停止するプロセスの Popen オブジェクト
    """
    if process is None:
        return

    try:
        process.terminate()
        # プロセスが終了するまで待機（最大5秒）
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # 強制終了
            process.kill()
            process.wait()
    except Exception:
        # プロセスが既に終了している場合は無視
        pass
