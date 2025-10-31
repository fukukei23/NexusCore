# ==============================================================================
# 操作するソフト: VSCode (または任意のテキストエディタ)
# レジストリ/フォルダ: C:\Users\USER\tools\NexusCore\
# ファイル名: api_client_test.py
# 日付: 2025/09/02
#
# 使用方法:
#   1. APIサーバー(server.py)を起動したまま、**別のターミナル**を開きます。
#   2. 新しいターミナルで `python api_client_test.py` と入力して実行します。
#   3. サーバー側のターミナルに、エージェントが動き出すログが表示されれば成功です。
#
# 改修内容:
#   - `NameError`を解決するため、ファイルの先頭に`import os`を追加しました。
# ==============================================================================

import requests
import json
import time
import os

# APIサーバーのアドレス
API_BASE_URL = "http://127.0.0.1:5001"

def start_development_task(requirement: str, project_path: str) -> str:
    """
    APIサーバーに新しい開発タスクを開始するようリクエストする。
    """
    endpoint = f"{API_BASE_URL}/api/v1/execute"
    payload = {
        "requirement": requirement,
        "project_path": project_path
    }
    
    print(f"🚀 タスク開始リクエストを送信中...\n   エンドポイント: {endpoint}\n   要件: {requirement}")
    
    try:
        response = requests.post(endpoint, json=payload, timeout=10)
        response.raise_for_status()  # HTTPエラーがあれば例外を発生させる
        
        data = response.json()
        task_id = data.get("task_id")
        
        if not task_id:
            raise ValueError("APIからの応答にtask_idが含まれていません。")
            
        print(f"✅ タスク受理成功！\n   タスクID: {task_id}")
        print(f"   進捗確認URL: {API_BASE_URL}{data.get('status_url')}")
        return task_id
        
    except requests.exceptions.RequestException as e:
        print(f"❌ APIリクエスト失敗: {e}")
        print("   APIサーバー(server.py)が起動しているか確認してください。")
        return ""

def poll_task_status(task_id: str, interval: int = 5, timeout: int = 300):
    """
    タスクのステータスを定期的に確認する。
    """
    if not task_id:
        return

    print(f"\n🔄 タスク '{task_id}' の進捗を監視中 ( {interval}秒ごと )...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            endpoint = f"{API_BASE_URL}/api/v1/status/{task_id}"
            response = requests.get(endpoint, timeout=5)
            response.raise_for_status()
            
            status = response.json()
            status_msg = status.get('status', '不明')
            message = status.get('message', '詳細なし')
            
            print(f"   [{time.strftime('%H:%M:%S')}] ステータス: {status_msg} - {message}")

            if status_msg in ["completed", "error"]:
                print(f"🏁 タスク '{task_id}' が状態 '{status_msg}' で終了しました。")
                break
                
            time.sleep(interval)
            
        except requests.exceptions.RequestException as e:
            print(f"❌ 進捗確認中にエラーが発生: {e}")
            break
    else:
        print(f"⏰ タイムアウト ({timeout}秒) しました。タスクはまだ実行中かもしれません。")


if __name__ == "__main__":
    # --- ここにAIに実行させたいタスクを記述 ---
    
    # 例：シンプルな電卓アプリの作成をAIに依頼する
    user_requirement = "2つの数値を入力として受け取り、その合計を返す`add`関数を持つPythonの電卓ライブラリを作成してください。"
    
    # AIがコードを生成するプロジェクトのパス (このリポジトリのルートを指す)
    # 注意: このパスはAPIサーバーを実行しているマシンから見たパスである必要があります。
    target_project_path = os.path.abspath(os.path.dirname(__file__))

    # 1. 開発タスクを開始
    new_task_id = start_development_task(user_requirement, target_project_path)
    
    # 2. タスクの進捗を監視
    if new_task_id:
        poll_task_status(new_task_id)

