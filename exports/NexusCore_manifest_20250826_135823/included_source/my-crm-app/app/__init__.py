# ==============================================================================
# フォルダ: my-crm-app/app
# ファイル名: __init__.py
# メモ: アプリケーションの心臓部。ハードコードされた設定を排除し、
#      config.pyからすべての設定を読み込むように修正。
#      これにより、設定の一元管理アーキテクチャが完成します。
# ==============================================================================
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# --- ★★★ ここからが最重要修正点 ★★★ ---
# 1. 親ディレクトリにあるconfig.pyからConfigクラスをインポート
from config import Config
# --- ★★★ ここまで ★★★ ---

# SQLAlchemyのインスタンスを作成
db = SQLAlchemy()

def create_app(config_class=Config):
    """
    アプリケーションファクトリ関数。
    Flaskアプリケーションのインスタンスを生成し、設定を読み込み、
    拡張機能とブループリントを初期化します。
    """
    app = Flask(__name__, instance_relative_config=True)

    # --- ★★★ ここからが最重要修正点 ★★★ ---
    # 2. config.pyのConfigクラスから設定を読み込む
    app.config.from_object(config_class)
    # --- ★★★ ここまで ★★★ ---

    # instanceフォルダが存在することを確認（DBファイルなどが保存される）
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # 拡張機能（データベース）をアプリケーションに登録
    db.init_app(app)

    # --- ★★★ ここからが最重要修正点 ★★★ ---
    # 3. routes.pyで定義したBlueprintをアプリケーションに登録
    from . import routes
    app.register_blueprint(routes.bp)
    # --- ★★★ ここまで ★★★ ---
    
    return app
