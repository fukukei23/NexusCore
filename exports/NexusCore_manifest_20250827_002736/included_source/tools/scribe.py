# ==============================================================================
# フォルダ: tools/
# ファイル名: scribe.py
# メモ: 手動での開発活動をプロジェクト・クロニクルに記録するためのツール。
#      "git commit"のように、開発の意図を一行で記録する。
#      Watcher Agentからインポートして利用できるように改良。
#
# 使い方 (手動実行):
# python tools/scribe.py "DebuggerAgentのリファクタリングとKnowledgeManagerの導入作業"
# ==============================================================================
import os
import json
import sys
from datetime import datetime, timezone
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def log_manual_event(project_path: str, summary: str):
    """
    手動での開発イベントをプロジェクト・クロニクルに追記する。
    """
    if not summary:
        logging.error("記録する内容が指定されていません。")
        return

    chronicle_path = os.path.join(project_path, "project_chronicle.jsonl")
    
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": "MANUAL_DEV_LOG",
        "agent": "HumanDeveloper",
        "data": {
            "summary": summary
        }
    }

    try:
        # "a" (append)モードでファイルを開き、追記する
        with open(chronicle_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        logging.info(f"✅ 開発活動をクロニクルに記録しました: {summary}")
    except FileNotFoundError:
        logging.error(f"エラー: クロニクルファイルが見つかりません: {chronicle_path}")
        logging.error("先に 'genesis_analyzer.py' を実行して、最初の記憶を生成してください。")
    except Exception as e:
        logging.error(f"クロニクルへの書き込み中にエラーが発生しました: {e}")

# このファイルが直接実行された時のみ、コマンドライン引数を処理する
if __name__ == "__main__":
    # コマンドライン引数から記録内容を取得
    if len(sys.argv) < 2:
        print("Usage: python tools/scribe.py \"<記録したい開発内容の要約>\"")
        sys.exit(1)
    
    # プロジェクトのルートパスをスクリプトからの相対パスで解決
    # このスクリプトが tools/ にあることを想定
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    log_summary = sys.argv[1]
    log_manual_event(project_root, log_summary)
