# ==============================================================================
# フォルダ: my-crm-app
# ファイル名: run.py
# メモ: .envからホスト名やポート番号を読み込んで、安全な設定で
#      Flaskサーバーを起動するように修正。
# ==============================================================================
import os
from app import create_app

# アプリケーションインスタンスを作成
# create_app() は内部で config.py を読み込むことを想定しています。
# (この設定は app/__init__.py で行われます)
app = create_app()

if __name__ == '__main__':
    # .envからサーバー設定を読み込む
    # .envに設定がない場合は、安全なデフォルト値が使用されます。
    host = os.getenv("SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("API_SERVER_PORT", 5000)) # 他のサーバーと衝突しないポート
    debug = app.config.get("DEBUG", False) # configからデバッグモードを取得

    print(f"✅ CRM Appサーバーを http://{host}:{port} で起動します。")
    
    # 読み込んだ設定を使ってサーバーを起動
    app.run(host=host, port=port, debug=debug)
