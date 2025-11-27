#!/usr/bin/env python3
"""
export_cursor_chat_history.py

Cursorのチャット履歴をMarkdown形式でエクスポートするスクリプト。

使用方法:
    python tools/export_cursor_chat_history.py [--output-dir .cursor/chat_history]

注意:
    Cursorのチャット履歴はSQLiteデータベースに保存されています。
    このスクリプトは、データベースファイルを直接読み取ることはできませんが、
    手動でエクスポートしたデータをMarkdown形式に変換する際に使用できます。
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def export_chat_to_markdown(
    chat_data: Dict[str, Any],
    output_path: Path,
) -> None:
    """
    チャットデータをMarkdown形式でエクスポートする。

    Args:
        chat_data: チャットデータ（JSON形式）
        output_path: 出力先のパス
    """
    lines = [
        f"# Chat History - {chat_data.get('date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}",
        "",
        f"**Title**: {chat_data.get('title', 'Untitled')}",
        f"**Created**: {chat_data.get('created_at', 'Unknown')}",
        "",
        "---",
        "",
    ]

    messages = chat_data.get("messages", [])
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        if role == "user":
            lines.append(f"## 👤 ユーザー")
        elif role == "assistant":
            lines.append(f"## 🤖 AI")
        else:
            lines.append(f"## {role}")

        lines.append("")
        lines.append(content)
        lines.append("")
        lines.append("---")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ エクスポート完了: {output_path}")


def find_cursor_chat_history() -> List[Path]:
    """
    Cursorのチャット履歴データベースファイルを探す。

    Returns:
        見つかったデータベースファイルのパスリスト
    """
    possible_paths = []

    # Windows
    if sys.platform == "win32":
        appdata = os.getenv("APPDATA", "")
        if appdata:
            possible_paths.append(
                Path(appdata) / "Cursor" / "User" / "workspaceStorage"
            )

    # macOS
    elif sys.platform == "darwin":
        home = Path.home()
        possible_paths.append(
            home / "Library" / "Application Support" / "Cursor" / "User" / "workspaceStorage"
        )

    # Linux
    else:
        home = Path.home()
        possible_paths.append(
            home / ".config" / "Cursor" / "User" / "workspaceStorage"
        )

    found_files = []
    for base_path in possible_paths:
        if base_path.exists():
            # SQLiteデータベースファイルを探す
            for db_file in base_path.rglob("*.db"):
                found_files.append(db_file)
            for db_file in base_path.rglob("state.vscdb"):
                found_files.append(db_file)

    return found_files


def main() -> int:
    """メイン関数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Cursorのチャット履歴をMarkdown形式でエクスポート"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=".cursor/chat_history",
        help="出力先ディレクトリ（デフォルト: .cursor/chat_history）",
    )
    parser.add_argument(
        "--input-json",
        type=str,
        help="入力JSONファイル（Cursorから手動エクスポートしたもの）",
    )

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.input_json:
        # JSONファイルから読み込み
        input_path = Path(args.input_json)
        if not input_path.exists():
            print(f"❌ ファイルが見つかりません: {input_path}", file=sys.stderr)
            return 1

        try:
            with input_path.open("r", encoding="utf-8") as f:
                chat_data = json.load(f)

            output_path = output_dir / f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            export_chat_to_markdown(chat_data, output_path)
            return 0

        except Exception as e:
            print(f"❌ エラー: {e}", file=sys.stderr)
            return 1

    else:
        # データベースファイルを探す
        print("🔍 Cursorのチャット履歴データベースを検索中...")
        db_files = find_cursor_chat_history()

        if not db_files:
            print("⚠️  データベースファイルが見つかりませんでした。")
            print("\n手動でエクスポートする方法:")
            print("1. Cursorの設定から「Export Chat History」を探す")
            print("2. エクスポートしたJSONファイルを --input-json で指定")
            print("\nまたは、以下のパスを確認してください:")
            if sys.platform == "win32":
                print("  %APPDATA%\\Cursor\\User\\workspaceStorage\\")
            elif sys.platform == "darwin":
                print("  ~/Library/Application Support/Cursor/User/workspaceStorage/")
            else:
                print("  ~/.config/Cursor/User/workspaceStorage/")
            return 1

        print(f"✅ {len(db_files)}個のデータベースファイルが見つかりました")
        print("\n注意: SQLiteデータベースの直接読み取りは現在サポートされていません。")
        print("Cursorの設定からチャット履歴をエクスポートし、--input-json で指定してください。")

        return 0


if __name__ == "__main__":
    sys.exit(main())

