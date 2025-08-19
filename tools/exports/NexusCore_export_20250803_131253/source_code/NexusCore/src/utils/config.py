# フォルダ: src/utils
# ファイル名: config.py
# メモ: プロジェクト全体の設定値（APIキー、秘密鍵、データベース接続情報など）を
#      一元管理するためのファイルです。すべての設定はここから読み込みます。

import os
from dotenv import load_dotenv

# プロジェクトのルートにある.envファイルを読み込む
# このファイルの場所から2階層上のディレクトリをルートと仮定
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
dotenv_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path=dotenv_path)

class Config:
    """
    環境変数から設定を読み込むための設定クラス。
    アプリケーション全体でこのクラスのインスタンスをインポートして使用します。
    """
    # --- OpenAI API ---
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")# フォルダ: src/utils
# ファイル名: config.py
# メモ: プロジェクト全体の設定値（APIキー、秘密鍵、データベース接続情報など）を
#      一元管理するためのファイルです。すべての設定はここから読み込みます。

import os
from dotenv import load_dotenv

# プロジェクトのルートにある.envファイルを読み込む
# このファイルの場所から2階層上のディレクトリをルートと仮定
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
dotenv_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path=dotenv_path)

class Config:
    """
    環境変数から設定を読み込むための設定クラス。
    アプリケーション全体でこのクラスのインスタンスをインポートして使用します。
    """
    # --- OpenAI API ---
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # --- Gemini API (Multi-Agent System) ---
    # ◀️ マルチエージェントシステム用のAPIキーを追加
    # エージェントA（生成役）用のキー
    GEMINI_API_KEY_AGENT_A = os.getenv("GEMINI_API_KEY_AGENT_A")
    # エージェントB（批評・改善役）用のキー
    GEMINI_API_KEY_AGENT_B = os.getenv("GEMINI_API_KEY_AGENT_B")


    # --- Flask Application ---
    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "a-very-secret-key-for-development-only")
    
    # --- Database ---
    DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///db.sqlite3")
    
    # --- Celery (for background tasks) ---
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# アプリケーション全体で共有するためのConfigクラスのインスタンス
config = Config()

# APIキーが設定されていない場合に警告を表示
if not config.OPENAI_API_KEY:
    print("⚠️ 警告: OPENAI_API_KEYが.envファイルに設定されていません。")

# ◀️ Gemini APIキーの警告を追加
if not config.GEMINI_API_KEY_AGENT_A or not config.GEMINI_API_KEY_AGENT_B:
    print("⚠️ 警告: マルチエージェント用のGEMINI_API_KEYが設定されていません。")



    # --- Flask Application ---
    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "a-very-secret-key-for-development-only")
    
    # --- Database ---
    DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///db.sqlite3")
    
    # --- Celery (for background tasks) ---
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# アプリケーション全体で共有するためのConfigクラスのインスタンス
config = Config()

# APIキーが設定されていない場合に警告を表示
if not config.OPENAI_API_KEY:
    print("⚠️ 警告: OPENAI_API_KEYが.envファイルに設定されていません。")

