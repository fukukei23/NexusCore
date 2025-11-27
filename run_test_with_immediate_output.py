#!/usr/bin/env python3
"""
run_test_with_immediate_output.py

WSL環境でCursorのrun_terminal_cmdで出力が取得できない問題を解決するための
リアルタイム出力スクリプト。

使用方法:
    python run_test_with_immediate_output.py <command> [args...]

例:
    python run_test_with_immediate_output.py pytest tests/ -v
    python run_test_with_immediate_output.py python tools/run_browser_use.py --site MONCLER_OFFICIAL
"""

from __future__ import annotations

import os
import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime


def run_with_immediate_output(
    command: list[str],
    log_file: str | None = None,
    unbuffered: bool = True,
) -> int:
    """
    コマンドを実行し、リアルタイムで出力を表示する。

    Args:
        command: 実行するコマンド（リスト形式）
        log_file: ログファイルのパス（Noneの場合はログファイルを作成しない）
        unbuffered: Pythonのバッファリングを無効化するか

    Returns:
        コマンドの終了コード
    """
    # 環境変数を設定
    env = os.environ.copy()
    if unbuffered:
        env["PYTHONUNBUFFERED"] = "1"

    # ログファイルを開く（指定されている場合）
    log_fp = None
    if log_file:
        log_fp = open(log_file, "w", encoding="utf-8")
        print(f"📝 ログファイル: {log_file}", flush=True)

    try:
        # プロセスを起動
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            text=True,
            bufsize=1,  # 行バッファリング
            universal_newlines=True,
        )

        # リアルタイムで出力を読み取り
        while True:
            output = process.stdout.readline()
            if output == "" and process.poll() is not None:
                break
            if output:
                # 標準出力に表示
                print(output, end="", flush=True)
                # ログファイルに書き込み（指定されている場合）
                if log_fp:
                    log_fp.write(output)
                    log_fp.flush()

        # 終了コードを取得
        return_code = process.poll()
        return return_code if return_code is not None else 1

    except KeyboardInterrupt:
        print("\n⚠️  中断されました", flush=True)
        if process:
            process.terminate()
        return 130

    except Exception as e:
        print(f"❌ エラー: {e}", file=sys.stderr, flush=True)
        return 1

    finally:
        if log_fp:
            log_fp.close()
            print(f"\n✅ ログファイルに保存されました: {log_file}", flush=True)


def main() -> int:
    """メイン関数"""
    if len(sys.argv) < 2:
        print("使用方法: python run_test_with_immediate_output.py <command> [args...]", file=sys.stderr)
        print("\n例:")
        print("  python run_test_with_immediate_output.py pytest tests/ -v")
        print("  python run_test_with_immediate_output.py python tools/run_browser_use.py --site MONCLER_OFFICIAL")
        return 1

    # コマンドを取得
    command = sys.argv[1:]

    # ログファイル名を生成（オプション）
    log_file = None
    if "--log" in sys.argv:
        idx = sys.argv.index("--log")
        if idx + 1 < len(sys.argv):
            log_file = sys.argv[idx + 1]
            command = [c for c in command if c != "--log" and c != log_file]
        else:
            # デフォルトのログファイル名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = f"output_{timestamp}.log"
            command = [c for c in command if c != "--log"]
    elif os.getenv("AUTO_LOG", "0") == "1":
        # 環境変数で自動ログを有効化
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"output_{timestamp}.log"

    # コマンドを実行
    print(f"🚀 実行中: {' '.join(command)}", flush=True)
    if log_file:
        print(f"📝 ログファイル: {log_file}", flush=True)
    print("-" * 80, flush=True)

    return_code = run_with_immediate_output(command, log_file=log_file)

    print("-" * 80, flush=True)
    if return_code == 0:
        print("✅ 正常終了", flush=True)
    else:
        print(f"❌ エラー終了 (終了コード: {return_code})", flush=True)

    return return_code


if __name__ == "__main__":
    sys.exit(main())

