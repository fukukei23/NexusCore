# ==============================================================================
# ファイル名: C:\Users\USER\tools\NexusCore\src\nexuscore\npe\logger.py
# ==============================================================================
# 目的:
# システム全体の監査証跡（Audit Trail）を記録するための汎用ロガー。
# NPEの活動だけでなく、Orchestratorや各Agentの行動も記録することで、
# トレーサビリティとガバナンスを確保する。
# ==============================================================================
import datetime
import json

def log_transaction(log_data: dict, log_file: str = "npe_audit_log.jsonl"):
    """
    実行された処理（トランザクション）をJSON Lines形式で記録する。
    
    Args:
        log_data (dict): ログとして記録したいデータ。
        log_file (str): ログの出力先ファイル名。
    """
    # ログに必須の情報を付与
    log_data["event_timestamp_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    # ログエントリをJSON形式の文字列に変換（人間が読みやすいようにインデント）
    log_entry_pretty = json.dumps(log_data, indent=2, ensure_ascii=False)
    
    # --- コンソールへの出力（PoCでの確認用）---
    print("\n--- NPE AUDIT LOG ---")
    print(log_entry_pretty)
    print("---------------------\n")
    # ----------------------------------------
    
    # 永続化のためのファイル書き込み
    # 監査ログは追記が基本なので、'a'モードでオープンする
    try:
        # 実際にファイルに書き込む際は、インデントなしの1行JSON（JSON Lines形式）が一般的
        log_entry_compact = json.dumps(log_data, ensure_ascii=False)
        
        # プロジェクトのルートディレクトリにログファイルを出力することを想定
        # (実際にはconfigでログディレクトリを指定できるようにすべき)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry_compact + "\n")
            
    except Exception as e:
        print(f"[NPE-Logger] CRITICAL: Failed to write to audit log file '{log_file}'. Error: {e}")
