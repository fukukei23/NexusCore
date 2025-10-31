# ==============================================================================
# フォルダ: scripts
# ファイル名: backup_tool.py
# メモ: Gitリポジトリを効率的にバックアップし、世代管理も行うツール。【バグ修正版 v3】
# ==============================================================================

import os
import re
import subprocess
import logging
from datetime import datetime, timedelta

# ==============================================================================
# 設定項目
# ==============================================================================

# バックアップ対象のプロジェクト（Gitリポジトリ）のフルパスを指定
# raw文字列(r"...")を使うことで、パス区切り文字(\)を気にせず記述できます
SOURCE_DIRECTORIES = [
    r"C:\Users\USER\tools\NexusCore",
]

# バックアップファイルの保存先ディレクトリのフルパスを指定
# フォルダ名にスペースを含めないことで、予期せぬエラーを防ぎます
BACKUP_DESTINATION = r"C:\Users\USER\tools\BackupNexusCore"

# バックアップファイルを保持する日数（この日数を超えた古いファイルは自動で削除されます）
RETENTION_DAYS = 30

# ログファイルの保存先ディレクトリ
LOG_DIRECTORY = os.path.join(BACKUP_DESTINATION, "logs")

# ==============================================================================
# スクリプト本体
# ==============================================================================

def setup_logging():
    """ロギング機能のセットアップ"""
    os.makedirs(LOG_DIRECTORY, exist_ok=True)
    log_file = os.path.join(LOG_DIRECTORY, f"backup_{datetime.now():%Y-%m-%d}.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def sanitize_filename(name: str) -> str:
    """ファイル名に使用できない文字を除去・置換する"""
    # Windows/Linuxなどでファイル名として使えない文字をアンダースコアに置換
    invalid_chars = r'[<>:"/\\|?*\s]'
    return re.sub(invalid_chars, '_', name)

def create_git_bundle(repo_path: str, dest_dir: str) -> bool:
    """
    指定されたGitリポジトリのバンドルファイルを作成する。
    """
    repo_name = sanitize_filename(os.path.basename(repo_path))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bundle_filename = f"{repo_name}_{timestamp}.bundle"
    bundle_filepath = os.path.join(dest_dir, bundle_filename)

    logging.info(f"リポジトリ '{repo_name}' のバックアップを開始します...")

    # .gitディレクトリの存在確認を強化
    git_dir = os.path.join(repo_path, ".git")
    if not (os.path.isdir(git_dir) or os.path.isfile(git_dir)):
        logging.error(f"'{repo_path}' はGitリポジトリではありません。スキップします。")
        return False

    try:
        # git bundleコマンド実行
        cmd = ["git", "bundle", "create", bundle_filepath, "--all"]
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8',
            timeout=300  # 5分のタイムアウトを追加。巨大なリポジトリでもハングしないようにする
        )
        
        # バンドルファイルのサイズ確認
        if os.path.exists(bundle_filepath):
            file_size = os.path.getsize(bundle_filepath)
            if file_size == 0:
                logging.error(f"生成されたバンドルファイルが空です。削除します: {bundle_filepath}")
                os.remove(bundle_filepath)
                return False
            
            logging.info(f"バンドルファイルを作成しました: {bundle_filepath} ({file_size:,} bytes)")
        
        return True
        
    except subprocess.TimeoutExpired:
        logging.error(f"バンドル作成がタイムアウトしました（5分以上経過）: {repo_name}")
        return False
    except FileNotFoundError:
        logging.error("'git' コマンドが見つかりません。Gitがインストールされ、PATHが通っているか確認してください。")
        return False
    except subprocess.CalledProcessError as e:
        logging.error(f"バンドルファイルの作成に失敗しました: {repo_name}")
        logging.error(f"リターンコード: {e.returncode}")
        logging.error(f"エラー出力:\n{e.stderr}")
        return False
    except Exception as e:
        logging.error(f"予期せぬエラーが発生しました: {e}", exc_info=True)
        return False

def rotate_backups(dest_dir: str):
    """指定されたディレクトリ内の古いバックアップファイルを削除する"""
    logging.info(f"バックアップの世代管理を開始します (保持期間: {RETENTION_DAYS}日)...")
    cutoff_date = datetime.now() - timedelta(days=RETENTION_DAYS)
    
    try:
        bundle_files = [f for f in os.listdir(dest_dir) if f.endswith(".bundle")]
        
        for filename in bundle_files:
            filepath = os.path.join(dest_dir, filename)
            
            # より厳密な正規表現による日付抽出
            match = re.search(r'_(\d{8})_\d{6}\.bundle$', filename)
            
            if not match:
                logging.warning(f"ファイル名の形式が不正です。スキップします: {filename}")
                continue
            
            try:
                date_str = match.group(1)
                file_date = datetime.strptime(date_str, "%Y%m%d")
                
                if file_date < cutoff_date:
                    logging.info(f"古いバックアップファイルを削除します: {filename}")
                    os.remove(filepath)
                else:
                    logging.debug(f"保持対象のファイルです: {filename}")

            except ValueError as e:
                logging.error(f"ファイル名に含まれる日付の解析に失敗しました ({filename}): {e}")
            except Exception as e:
                logging.error(f"ファイル処理中に予期せぬエラーが発生しました ({filename}): {e}")

    except FileNotFoundError:
        logging.warning(f"バックアップディレクトリが見つかりません: {dest_dir}")
    except Exception as e:
        logging.error(f"世代管理中に予期せぬエラーが発生しました: {e}", exc_info=True)

def main():
    """メイン処理"""
    setup_logging()
    logging.info("================ バックアップ処理開始 ================")

    # バックアップ先ディレクトリの作成
    try:
        os.makedirs(BACKUP_DESTINATION, exist_ok=True)
        logging.info(f"バックアップ先ディレクトリ: {BACKUP_DESTINATION}")
    except Exception as e:
        logging.critical(f"バックアップ先ディレクトリの作成に失敗しました: {e}")
        return

    # 各リポジトリのバックアップ実行
    success_count = 0
    for src_dir in SOURCE_DIRECTORIES:
        if not os.path.isdir(src_dir):
            logging.warning(f"指定されたソースディレクトリが見つかりません: {src_dir}")
            continue
            
        if create_git_bundle(src_dir, BACKUP_DESTINATION):
            success_count += 1

    logging.info(f"バックアップ作成完了 ({success_count}/{len(SOURCE_DIRECTORIES)}件 成功)")

    # 古いバックアップの削除
    rotate_backups(BACKUP_DESTINATION)

    logging.info("================ バックアップ処理終了 ================")

if __name__ == "__main__":
    main()
