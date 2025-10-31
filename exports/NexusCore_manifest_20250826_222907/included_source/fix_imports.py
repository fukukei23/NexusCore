# ==============================================================================
# ファイル名: fix_imports.py
# メモ: NexusCore インポートパス修正・プロジェクト構造検証ツール
#
# 機能:
# 1. プロジェクト内のPythonファイルのインポートパスを絶対パスに修正
# 2. 不足している __init__.py ファイルを自動生成
# 3. プロジェクトの基本構造を検証
#
# 使い方:
# プロジェクトのルートディレクトリで以下のコマンドを実行
# python fix_imports.py
#
# 特定のディレクトリを対象にする場合:
# python fix_imports.py --directory src
#
# 変更を実際に行わずに、修正対象のファイルを確認する場合 (Dry Run):
# python fix_imports.py --dry-run
# ==============================================================================

import os
import re
import argparse
from pathlib import Path

def fix_import_paths(root_dir: str, dry_run: bool = False):
    """
    指定されたディレクトリ内のPythonファイルのインポートパスを修正します。

    Args:
        root_dir (str): 修正対象のルートディレクトリ。
        dry_run (bool): Trueの場合、ファイルの変更は行わず、修正対象を表示するだけ。
    """
    print(f"🔍 '{root_dir}' ディレクトリのインポートパスをスキャン中...")
    if dry_run:
        print("⚠️ ドライランモード: ファイルの変更は行われません。")

    # 単語境界(\b)を追加し、より正確なマッチングを行うように正規表現を改善
    # これにより、'my_agents' のような類似名を持つ無関係なモジュールへの誤マッチを防ぎます。
    patterns = [
        (r'from \bagents\b', 'from nexuscore.agents'),
        (r'from \bcore\b', 'from nexuscore.core'),
        (r'from \butils\b', 'from nexuscore.utils'),
        (r'from \bmodules\b', 'from nexuscore.modules'),
        (r'from \bapi\b', 'from nexuscore.api'),
        (r'from \baudio\b', 'from nexuscore.audio'),
        (r'from \bcode_interpreter\b', 'from nexuscore.code_interpreter'),
        (r'from \bgradio_app\b', 'from nexuscore.gradio_app'),
        # 相対インポートの修正 (例: from .agents -> from nexuscore.agents)
        (r'from \.(agents|core|utils|modules|api|audio|code_interpreter|gradio_app)', r'from nexuscore.\1')
    ]

    fixed_count = 0
    changed_files = []
    root_path = Path(root_dir)

    if not root_path.is_dir():
        print(f"❌ エラー: ディレクトリ '{root_dir}' が見つかりません。")
        print(f"現在の作業ディレクトリ: {Path.cwd()}")
        return

    for py_file in root_path.rglob("*.py"):
        try:
            content = py_file.read_text(encoding='utf-8', errors='ignore')
            original_content = content
            
            for old_pattern, new_pattern in patterns:
                content = re.sub(old_pattern, new_pattern, content)

            if content != original_content:
                changed_files.append(py_file)
                if not dry_run:
                    py_file.write_text(content, encoding='utf-8')
                fixed_count += 1
                
        except Exception as e:
            print(f"❌ '{py_file}' の処理中にエラーが発生しました: {e}")

    if changed_files:
        print("\n--- 修正対象ファイル ---")
        current_dir = Path.cwd()
        for f in changed_files:
            # ★★★ エラー修正: 安全な相対パス計算 ★★★
            # relative_to() が失敗するエッジケース (例: ドライブが異なる) を考慮し、
            # 例外処理を追加して堅牢性を高める。
            try:
                display_path = f.relative_to(current_dir)
            except ValueError:
                # パス計算に失敗した場合は、ファイルパスをそのまま表示する
                display_path = f
            print(f"  - {display_path}")
        print("--------------------")

    if dry_run:
        print(f"\n✅ スキャン完了: {fixed_count} 個のファイルが修正対象です。")
    else:
        print(f"\n✅ 修正完了: {fixed_count} 個のファイルのインポートパスを修正しました。")


def create_missing_init_files(dry_run: bool = False):
    """
    プロジェクト内の重要なディレクトリに不足している__init__.pyファイルを作成します。
    """
    print("\n🔍 __init__.py ファイルをチェック中...")
    if dry_run:
        print("⚠️ ドライランモード: ファイルの作成は行われません。")

    # プロジェクトのパッケージとして認識させるべき重要なディレクトリ
    important_dirs = [
        "src/nexuscore",
        "src/nexuscore/agents",
        "src/nexuscore/core",
        "src/nexuscore/utils",
        "src/nexuscore/modules",
        "src/nexuscore/api",
        "src/nexuscore/audio",
        "src/nexuscore/code_interpreter",
        "src/nexuscore/gradio_app",
        "tests",
        "tests/unit",
        "tests/integration",
    ]
    
    # srcディレクトリ自体もパッケージルートとしてマーク
    if Path("src").is_dir():
        important_dirs.insert(0, "src")

    created_count = 0
    for dir_path_str in important_dirs:
        dir_path = Path(dir_path_str)
        if not dir_path.is_dir():
            continue

        init_file = dir_path / "__init__.py"
        if not init_file.exists():
            print(f"📄 作成対象: {init_file}")
            if not dry_run:
                init_file.write_text("# This file makes this a Python package\n", encoding='utf-8')
            created_count += 1
        else:
            # 既存のファイルはスキップ
            pass
            
    if created_count > 0:
        if dry_run:
            print(f"\n✅ チェック完了: {created_count} 個の __init__.py ファイルが作成対象です。")
        else:
            print(f"\n✅ 作成完了: {created_count} 個の __init__.py ファイルを新規作成しました。")
    else:
        print("✅ すべての重要ディレクトリに __init__.py は存在します。")


def verify_structure():
    """
    プロジェクトの基本的なファイル構造が期待通りかを確認します。
    """
    print("\n📊 プロジェクト構造の検証:")
    print("="*50)

    key_elements = [
        "src/nexuscore",
        "src/nexuscore/__init__.py",
        "pyproject.toml",
        "tests",
    ]

    for element_path in key_elements:
        path = Path(element_path)
        status = "✅ 存在します" if path.exists() else "❌ 見つかりません"
        print(f"  - {element_path:<30} -> {status}")

    print("="*50)


def main():
    """
    メインの実行関数。コマンドライン引数を処理し、各機能を呼び出します。
    """
    parser = argparse.ArgumentParser(
        description="NexusCore プロジェクトのインポートパス修正と構造検証を行うツール",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "-d", "--directory",
        default="src",
        help="スキャン対象のルートディレクトリ (デフォルト: 'src')"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実際の変更を行わず、修正・作成されるファイルの一覧を表示します。"
    )
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="実行前の確認プロンプトをスキップします。"
    )
    args = parser.parse_args()

    print("🚀 NexusCore メンテナンスツール 🚀")
    print("="*60)
    print(f"作業ディレクトリ: {Path.cwd()}")
    print(f"対象ディレクトリ: {args.directory}")
    if args.dry_run:
        print("モード: ⚠️ ドライラン (変更は行われません)")
    print("="*60)

    if not args.dry_run and not args.no_interactive:
        response = input("上記のディレクトリに対して変更処理を実行しますか？ (y/N): ").lower()
        if response != 'y':
            print("🚫 処理を中断しました。")
            return

    # Step 1: 構造の検証
    verify_structure()

    # Step 2: __init__.py ファイルの作成
    create_missing_init_files(dry_run=args.dry_run)

    # Step 3: インポートパスの修正
    fix_import_paths(root_dir=args.directory, dry_run=args.dry_run)

    print("\n🎉 全ての処理が完了しました。")
    if args.dry_run:
        print("ドライランモードだったため、実際のファイル変更はありません。")
        print("変更を実行するには、--dry-run オプションを外して再実行してください。")
    else:
        print("\n🎯 次のコマンドでテストを実行し、変更内容に問題がないか確認してください：")
        print("pytest --cov=src --cov-report=term-missing tests/")


if __name__ == "__main__":
    main()
