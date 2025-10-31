# ==============================================================================
# フォルダ: my-crm-app
# ファイル名: config.py
# メモ: NexusCoreプロジェクトの.envファイルから設定を読み込むようにアップグレード。
#      これにより、CRMアプリもメインシステムと設定を共有し、一元管理を実現します。
# ==============================================================================
import os
from dotenv import load_dotenv
from pathlib import Path

# このファイルの2階層上 (NexusCore) にある .env ファイルのパスを解決
# これにより、このCRMアプリがサブモジュールとしてどこに配置されても正しく動作します。
project_root = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=project_root / '.env')

class Config:
    """
    Flaskアプリケーションの設定を.envファイルから読み込むためのクラス。
    .envに値がない場合は、安全なデフォルト値が使用されます。
    """
    # Flaskのデバッグモード。本番環境では必ずFalseにすべき。
    DEBUG = os.getenv("FLASK_DEBUG_MODE", "True").lower() in ('true', '1', 't')

    # セッションの暗号化などに使われる秘密鍵。本番環境では必ず複雑なものに変更。
    SECRET_KEY = os.getenv("SECRET_KEY", "a-super-secret-key-that-should-be-changed")

    # SQLAlchemy（データベース）関連の設定
    # .envにDATABASE_URLがなければ、プロジェクトのinstanceフォルダにDBファイルを作成
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{project_root / 'instance' / 'crm_app.db'}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
