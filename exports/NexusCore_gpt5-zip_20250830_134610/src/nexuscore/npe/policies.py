# ==============================================================================
# ファイル名: C:\Users\USER\tools\NexusCore\src\nexuscore\npe\policies.py
# ==============================================================================
# 目的:
# NPEのセキュリティポリシー関連の具体的なチェック処理を実装するモジュール。
# ここでは、形式的かつ高速に実行できるチェック（例：機密情報のスキャン）を担当する。
# ==============================================================================
import re

def context_scanner(code: str) -> str:
    """
    与えられたコード（コンテキスト）をスキャンし、機密情報の有無を判定する。
    NPEの「自動セキュリティゲート」の役割を担う。

    Args:
        code (str): 分析対象のコードやテキスト。

    Returns:
        str: スキャン結果 ('safe' または 'sensitive')。
    """
    print("[NPE-PolicyScanner] Context scan initiated...")
    
    # チェックする機密情報のパターンを正規表現で定義
    # 将来的には、このリストを外部の設定ファイルから読み込むように拡張できる
    sensitive_patterns = [
        # 例: API_KEY = "...", SECRET_KEY = '...' など
        r'(API_KEY|SECRET_KEY|TOKEN)\s*=\s*["\'][^"\']+["\']',
        # 例: 一般的なAWSアクセスキーのパターン
        r'AKIA[0-9A-Z]{16}',
    ]

    for pattern in sensitive_patterns:
        if re.search(pattern, code, re.IGNORECASE):
            match = re.search(pattern, code, re.IGNORECASE).group(0)
            print(f"[NPE-PolicyScanner] RESULT: Sensitive pattern found. Match: '{match}'")
            return "sensitive"
    
    print("[NPE-PolicyScanner] RESULT: No sensitive patterns found.")
    return "safe"


def secure_context_builder(code: str) -> str:
    """
    機密情報をマスキング（匿名化）処理する。
    クラウドLLMに情報を渡す前に、この関数でコンテキストを浄化する。

    Args:
        code (str): マスキング対象のコード。

    Returns:
        str: 機密情報がマスキングされたコード。
    """
    print("[NPE-SecureBuilder] Masking sensitive data in context...")
    
    # context_scannerと一貫性のあるパターンでマスキングを行う
    # ここでは、キーの値を '[REDACTED_BY_NPE]' という文字列に置換する
    masked_code = re.sub(
        r'(API_KEY|SECRET_KEY|TOKEN)\s*=\s*["\'][^"\']+["\']',
        r'\1 = "[REDACTED_BY_NPE]"',
        code,
        flags=re.IGNORECASE
    )
    
    masked_code = re.sub(
        r'AKIA[0-9A-Z]{16}',
        '[REDACTED_AWS_KEY_BY_NPE]',
        masked_code,
        flags=re.IGNORECASE
    )
    
    return masked_code

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