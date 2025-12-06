#!/usr/bin/env python3
"""
Cursor IDE チャット履歴自動エクスポートスクリプト

Cursor IDEのチャット履歴を自動的にMarkdown形式でエクスポートします。
このスクリプトは、Cursor IDEのデータベースファイルを監視して、
新しいチャット履歴を検出したら自動的にエクスポートします。

使用方法:
    # 1回だけエクスポート
    python tools/export_cursor_chat_history.py

    # 監視モード（新しいチャットを自動エクスポート）
    python tools/export_cursor_chat_history.py --watch

    # 特定の日付範囲をエクスポート
    python tools/export_cursor_chat_history.py --from-date 2025-12-01 --to-date 2025-12-05
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# プロジェクトルートを取得
PROJECT_ROOT = Path(__file__).parent.parent
CHAT_HISTORY_DIR = PROJECT_ROOT / ".cursor" / "chat_history"

# Windows側のCursor IDEデータベースの場所（WSL環境の場合）
# 実際のパスは環境によって異なる可能性があります
CURSOR_DB_PATHS = [
    # Windows側のパス（WSLからアクセス）
    Path("/mnt/c/Users") / Path.home().name / "AppData/Roaming/Cursor/User/globalStorage",
    Path("/mnt/c/Users") / Path.home().name / "AppData/Roaming/Cursor/User/workspaceStorage",
    # Linux環境の場合
    Path.home() / ".config/Cursor/User/globalStorage",
    Path.home() / ".config/Cursor/User/workspaceStorage",
]


def find_cursor_database() -> Path | None:
    """
    Cursor IDEのチャット履歴データベースファイルを探す。

    Returns:
        データベースファイルのパス、見つからない場合はNone
    """
    for base_path in CURSOR_DB_PATHS:
        if not base_path.exists():
            continue

        # SQLiteデータベースファイルを探す
        for db_file in base_path.rglob("*.db"):
            # チャット履歴関連のファイル名を探す
            if "chat" in db_file.name.lower() or "history" in db_file.name.lower():
                return db_file

        # workspaceStorage内の各ワークスペースのデータベースを探す
        for workspace_dir in base_path.iterdir():
            if workspace_dir.is_dir():
                for db_file in workspace_dir.rglob("*.db"):
                    if "chat" in db_file.name.lower() or "history" in db_file.name.lower():
                        return db_file

    return None


def export_chat_history(
    db_path: Path,
    output_dir: Path = CHAT_HISTORY_DIR,
    from_date: str | None = None,
    to_date: str | None = None,
) -> list[Path]:
    """
    チャット履歴をMarkdown形式でエクスポートする。

    Args:
        db_path: Cursor IDEのデータベースファイルのパス
        output_dir: エクスポート先のディレクトリ
        from_date: 開始日（YYYY-MM-DD形式）
        to_date: 終了日（YYYY-MM-DD形式）

    Returns:
        エクスポートされたファイルのパスのリスト
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # テーブル一覧を取得
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        exported_files = []

        # チャット履歴テーブルを探す
        chat_tables = [t for t in tables if "chat" in t.lower() or "message" in t.lower()]

        if not chat_tables:
            print(f"⚠️  チャット履歴テーブルが見つかりませんでした。")
            print(f"   利用可能なテーブル: {', '.join(tables)}")
            return exported_files

        for table_name in chat_tables:
            try:
                # テーブルの構造を確認
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [row[1] for row in cursor.fetchall()]

                # データを取得
                query = f"SELECT * FROM {table_name}"
                conditions = []

                if from_date:
                    # 日付カラムを推測（created_at, timestamp, date など）
                    date_columns = [c for c in columns if "date" in c.lower() or "time" in c.lower()]
                    if date_columns:
                        conditions.append(f"{date_columns[0]} >= '{from_date}'")

                if to_date:
                    date_columns = [c for c in columns if "date" in c.lower() or "time" in c.lower()]
                    if date_columns:
                        conditions.append(f"{date_columns[0]} <= '{to_date}'")

                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

                cursor.execute(query)
                rows = cursor.fetchall()

                if not rows:
                    continue

                # Markdown形式でエクスポート
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = output_dir / f"chat_{table_name}_{timestamp}.md"

                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(f"# Chat History - {table_name}\n\n")
                    f.write(f"**Export Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write(f"**Source Database**: {db_path}\n\n")
                    f.write("---\n\n")

                    for row in rows:
                        # 行をMarkdown形式で出力
                        f.write("## Chat Entry\n\n")
                        for col in columns:
                            value = row[col]
                            if value:
                                # JSON形式の場合は整形
                                if isinstance(value, str) and (value.startswith("{") or value.startswith("[")):
                                    try:
                                        value = json.dumps(json.loads(value), indent=2, ensure_ascii=False)
                                    except (json.JSONDecodeError, TypeError):
                                        pass

                                f.write(f"**{col}**:\n\n")
                                f.write(f"```\n{value}\n```\n\n")
                        f.write("---\n\n")

                exported_files.append(output_file)
                print(f"✅ エクスポート完了: {output_file} ({len(rows)}件)")

            except sqlite3.Error as e:
                print(f"⚠️  テーブル {table_name} のエクスポートに失敗: {e}")
                continue

        conn.close()
        return exported_files

    except sqlite3.Error as e:
        print(f"❌ データベースエラー: {e}")
        return []
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
        import traceback

        traceback.print_exc()
        return []


def watch_mode(db_path: Path, output_dir: Path = CHAT_HISTORY_DIR, interval: int = 60):
    """
    監視モード: 定期的にチャット履歴をチェックしてエクスポートする。

    Args:
        db_path: Cursor IDEのデータベースファイルのパス
        output_dir: エクスポート先のディレクトリ
        interval: チェック間隔（秒）
    """
    import time

    print(f"👀 監視モード開始: {db_path}")
    print(f"   チェック間隔: {interval}秒")
    print(f"   エクスポート先: {output_dir}")
    print("   Ctrl+C で停止\n")

    last_export_time = datetime.now()

    try:
        while True:
            # データベースの更新時刻を確認
            db_mtime = datetime.fromtimestamp(db_path.stat().st_mtime)

            if db_mtime > last_export_time:
                print(f"🔄 データベースが更新されました ({db_mtime.strftime('%Y-%m-%d %H:%M:%S')})")
                exported_files = export_chat_history(db_path, output_dir)
                if exported_files:
                    print(f"✅ {len(exported_files)}件のファイルをエクスポートしました\n")
                last_export_time = datetime.now()
            else:
                print(f"⏳ チェック中... ({datetime.now().strftime('%H:%M:%S')})")

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\n👋 監視モードを終了します")


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="Cursor IDE チャット履歴自動エクスポート")
    parser.add_argument(
        "--watch",
        action="store_true",
        help="監視モード: 定期的にチャット履歴をチェックしてエクスポート",
    )
    parser.add_argument("--interval", type=int, default=60, help="監視モードのチェック間隔（秒）")
    parser.add_argument("--from-date", type=str, help="開始日（YYYY-MM-DD形式）")
    parser.add_argument("--to-date", type=str, help="終了日（YYYY-MM-DD形式）")
    parser.add_argument("--output-dir", type=Path, default=CHAT_HISTORY_DIR, help="エクスポート先ディレクトリ")

    args = parser.parse_args()

    print("🔍 Cursor IDEのデータベースを検索中...")
    db_path = find_cursor_database()

    if not db_path:
        print("❌ Cursor IDEのデータベースファイルが見つかりませんでした。")
        print("\n以下の場所を確認してください:")
        for path in CURSOR_DB_PATHS:
            print(f"  - {path}")
        print("\n手動でデータベースファイルのパスを指定する場合は、")
        print("スクリプトを編集して CURSOR_DB_PATHS に追加してください。")
        return 1

    print(f"✅ データベースファイルを発見: {db_path}\n")

    if args.watch:
        watch_mode(db_path, args.output_dir, args.interval)
    else:
        exported_files = export_chat_history(db_path, args.output_dir, args.from_date, args.to_date)
        if exported_files:
            print(f"\n✅ 合計 {len(exported_files)}件のファイルをエクスポートしました")
        else:
            print("\n⚠️  エクスポートされたファイルがありませんでした")

    return 0


if __name__ == "__main__":
    sys.exit(main())
