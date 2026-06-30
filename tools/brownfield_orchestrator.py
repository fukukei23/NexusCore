"""後方互換エントリ。実体は tools/brownfield/ パッケージ（リファクタ v3 P1）。

起動方法（変更なし）: python tools/brownfield_orchestrator.py --ui

tools/ は __init__.py を持たないフラットなスクリプト集のため、brownfield/ パッケージを
解決するには tools/ 自身を sys.path に含める必要がある（shim ローカルで一時挿入）。
"""
import sys
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from brownfield.__main__ import main  # 正規パッケージロード（相対import解決の前提）

if __name__ == "__main__":
    sys.exit(main())
