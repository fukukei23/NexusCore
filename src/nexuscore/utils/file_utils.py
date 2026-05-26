import json
import logging
import os
from datetime import datetime
from pathlib import Path  # pathlibをインポート

# 既存の関数の定義 (変更なし)
MAX_FILE_SIZE_MB = 5
MAX_TOTAL_SIZE_MB = 20
FRONTEND_PREVIEW_CHARS = 100


def extract_file_content(file):
    # ... (既存の関数の実装はそのまま) ...
    logging.info("DEBUG: extract_file_content - start")
    logging.info("DEBUG: file type: %s", type(file))
    logging.info("DEBUG: file attributes: %s", dir(file))
    logging.info("DEBUG: file __dict__: %s", getattr(file, "__dict__", "no __dict__"))
    try:
        if hasattr(file, "name") and os.path.exists(file.name):
            try:
                with open(file.name, encoding="utf-8") as f:
                    content = f.read()
                    logging.info("DEBUG: open utf-8 (preview): %s", content[:100])
                    return content
            except Exception:
                with open(file.name, encoding="cp932", errors="ignore") as f:
                    content = f.read()
                    logging.info("DEBUG: open cp932 (preview): %s", content[:100])
                    return content
        # ... (以下、既存の関数の実装が続く) ...
    except Exception as e:
        logging.error(f"Error in extract_file_content: {e}")
        return ""


def file_list_display(files):
    # ... (既存の関数の実装はそのまま) ...
    if not files:
        return "（ファイル未選択）"
    if not isinstance(files, list):
        files = [files]
    names = []
    for file in files:
        if hasattr(file, "name"):
            names.append(file.name)
        else:
            names.append(str(file))
    return "\n".join(names)


def download_history(history):
    # ... (既存の関数の実装はそのまま) ...
    fn = f"history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(fn, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    return fn


# --- ★★★★★ ここからが最重要修正点 ★★★★★ ---
# 古いcreate_project_structure関数を、新しいインテリジェントなバージョンに置き換えます。
def create_project_structure(root_path: str, files: list):
    """
    指定されたルートパスに、設計データに基づいたファイルとフォルダの構造を再帰的に作成します。

    Args:
        root_path (str): プロジェクトが作成されるベースディレクトリ。
        files (list): ファイル/フォルダ情報を格納した辞書のリスト。
                      各辞書は 'name', 'type', 'content' (ファイルの場合) のキーを持つ。
    """
    logger = logging.getLogger(__name__)
    root = Path(root_path)
    logger.info(f"Creating project structure at: {root}")

    # ルートディレクトリが存在することを確認
    root.mkdir(parents=True, exist_ok=True)

    if not isinstance(files, list):
        logger.error(f"Invalid 'files' format. Expected a list, but got {type(files)}")
        return

    for item in files:
        item_path_str = item.get("name")
        item_type = item.get("type")

        if not item_path_str or not item_type:
            logger.warning(f"Skipping invalid item in design data: {item}")
            continue

        # item_path_str内のバックスラッシュをスラッシュに統一し、先頭のスラッシュを削除
        normalized_path = item_path_str.replace("\\\\", "/").lstrip("/")
        full_path = root / normalized_path

        try:
            if item_type == "folder":
                full_path.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Created directory: {full_path}")
            elif item_type == "file":
                # ファイルを書き込む前に、親ディレクトリが存在することを確認
                full_path.parent.mkdir(parents=True, exist_ok=True)
                content = item.get("content", "")
                full_path.write_text(content, encoding="utf-8")
                logger.debug(f"Created file: {full_path}")
        except Exception as e:
            logger.error(f"Failed to create {item_type} at {full_path}: {e}")


# --- ★★★★★ ここまで ★★★★★ ---
