# ファイル名: gradio_project_export_ui.py
# メモ:
# - 出力フォルダは「exported_projects」配下にまとめて管理
# - サブフォルダ名は「プロジェクト名_YYYYMMDD_HHMMSS」で分かりやすく自動生成
# - ダウンロードボタンは常に有効化、出力完了時に明確な通知
# - 出力ボタンはvariant="primary"で青色に強調
# - 古いエクスポートフォルダは自動クリーンアップ（1時間）
# - ファイルコピーは自動削除されるのでHDD圧迫を防止

import gradio as gr
import os
import json
import zipfile
import tempfile
import shutil
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

EXPORT_PARENT_DIR = "exported_projects"
os.makedirs(EXPORT_PARENT_DIR, exist_ok=True)
CLEANUP_SECONDS = 60 * 60  # 1時間

def cleanup_exported_projects():
    now = time.time()
    for folder in os.listdir(EXPORT_PARENT_DIR):
        folder_path = os.path.join(EXPORT_PARENT_DIR, folder)
        if os.path.isdir(folder_path):
            try:
                mtime = os.path.getmtime(folder_path)
                if now - mtime > CLEANUP_SECONDS:
                    shutil.rmtree(folder_path)
                    logging.info(f"Cleaned up old export folder: {folder_path}")
            except Exception as e:
                logging.warning(f"Failed to cleanup {folder_path}: {e}")

def export_structure_and_code(uploaded_file, extensions, prefix, suffix):
    cleanup_exported_projects()

    # ファイル名取得
    if hasattr(uploaded_file, "name") and isinstance(uploaded_file.name, str):
        filename = os.path.basename(uploaded_file.name)
        input_path = uploaded_file.name
    elif isinstance(uploaded_file, str):
        filename = os.path.basename(uploaded_file)
        input_path = uploaded_file
    else:
        filename = "uploaded_file"
        input_path = os.path.join(EXPORT_PARENT_DIR, filename)
        with open(input_path, "wb") as f:
            f.write(uploaded_file.read())

    # プロジェクト名・時刻でサブフォルダ名生成
    base_name = os.path.splitext(filename)[0]
    nowstr = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_dir = os.path.join(EXPORT_PARENT_DIR, f"{base_name}_{nowstr}")
    os.makedirs(export_dir, exist_ok=True)

    _, ext = os.path.splitext(filename)
    ext = ext.lower()

    if ext == ".zip":
        try:
            with zipfile.ZipFile(input_path, 'r') as zip_ref:
                zip_ref.extractall(export_dir)
            logging.info(f"Extracted zip to {export_dir}")
        except Exception as e:
            shutil.rmtree(export_dir)
            logging.error(f"ZIP extraction failed: {e}")
            raise gr.Error(f"ZIPファイルの解凍に失敗しました: {e}")
        extracted_items = os.listdir(export_dir)
        if len(extracted_items) == 1 and os.path.isdir(os.path.join(export_dir, extracted_items[0])):
            project_root = os.path.join(export_dir, extracted_items[0])
            folder_name = os.path.basename(project_root)
        else:
            project_root = export_dir
            folder_name = base_name
    else:
        try:
            project_root = os.path.join(export_dir, "single_file_project")
            os.makedirs(project_root, exist_ok=True)
            dest_path = os.path.join(project_root, filename)
            shutil.copy(input_path, dest_path)
            folder_name = base_name
            logging.info(f"Copied file to {dest_path}")
        except Exception as e:
            shutil.rmtree(export_dir)
            logging.error(f"File copy failed: {e}")
            raise gr.Error(f"ファイルのコピーに失敗しました: {e}")

    def create_folder_structure_json(path):
        result = {'name': os.path.basename(path), 'type': 'folder', 'children': []}
        if not os.path.isdir(path):
            return result
        try:
            entries = sorted(os.listdir(path))
        except Exception as e:
            logging.error(f"Failed to listdir {path}: {e}")
            return {'name': os.path.basename(path), 'type': 'folder', 'children': [], 'error': str(e)}
        for entry in entries:
            full_path = os.path.join(path, entry)
            if os.path.isdir(full_path):
                result['children'].append(create_folder_structure_json(full_path))
            else:
                result['children'].append({'name': entry, 'type': 'file'})
        return result

    structure = create_folder_structure_json(project_root)
    structure_json = os.path.join(export_dir, f"{prefix}{folder_name}{suffix}_structure_{nowstr}.json")
    combined_code = os.path.join(export_dir, f"{prefix}{folder_name}{suffix}_combined_code_{nowstr}.txt")

    try:
        with open(structure_json, "w", encoding="utf-8") as f:
            json.dump(structure, f, indent=4, ensure_ascii=False)
        logging.info(f"Saved structure JSON: {structure_json}")
    except Exception as e:
        logging.error(f"Failed to save structure JSON: {e}")
        raise gr.Error(f"構造JSONの保存に失敗: {e}")

    exts = [e.strip() for e in extensions.split(",") if e.strip()]
    files_found = 0
    try:
        with open(combined_code, "w", encoding="utf-8") as outfile:
            for dirpath, _, filenames in os.walk(project_root):
                for filename in sorted(filenames):
                    if any(filename.endswith(ext) for ext in exts):
                        file_path = os.path.join(dirpath, filename)
                        rel_path = os.path.relpath(file_path, project_root)
                        outfile.write(f"\n\n# === File: {rel_path} ===\n\n")
                        try:
                            with open(file_path, "r", encoding="utf-8") as infile:
                                outfile.write(infile.read())
                            files_found += 1
                        except Exception as e:
                            outfile.write(f"[読み込みエラー: {e}]\n")
                            logging.warning(f"Failed to read file {file_path}: {e}")
        logging.info(f"Saved combined code: {combined_code} (files found: {files_found})")
    except Exception as e:
        logging.error(f"Failed to save combined code: {e}")
        raise gr.Error(f"統合コードファイルの保存に失敗: {e}")

    if files_found == 0:
        logging.warning("No files found for the specified extensions.")
        raise gr.Warning("指定した拡張子のファイルが見つかりませんでした。")

    notify_msg = f"出力が完了しました！\n{os.path.basename(export_dir)}\n構造JSON: {os.path.basename(structure_json)}\n統合コード: {os.path.basename(combined_code)}"
    return structure_json, combined_code, notify_msg

with gr.Blocks() as demo:
    gr.Markdown("""
    # プロジェクト構造＆コード統合ファイル 出力ツール
    1. プロジェクトフォルダ(zip)または個別ファイル（.py, .txt, .md, .jsonなど）をアップロード
    2. 統合したい拡張子をカンマ区切りで入力（例: .py,.txt,.md）
    3. 出力ファイル名のプレフィックス・サフィックスを指定（任意）
    4. 「出力」ボタンを押すと、ダウンロードボタンと通知が表示されます
    """)

    file_input = gr.File(
        label="プロジェクトフォルダ（zip）または個別ファイルをアップロード",
        file_types=[".zip", ".py", ".txt", ".md", ".json"]
    )
    ext_input = gr.Textbox(label="統合する拡張子（カンマ区切り）", value=".py,.txt,.md", placeholder=".py,.txt,.md など")
    prefix_input = gr.Textbox(label="出力ファイル名のプレフィックス", value="", placeholder="例: my_")
    suffix_input = gr.Textbox(label="出力ファイル名のサフィックス", value="", placeholder="例: _v1")
    out1 = gr.DownloadButton(label="Download 構造JSON", visible=True)
    out2 = gr.DownloadButton(label="Download 統合コード", visible=True)
    notify = gr.Textbox(label="通知", visible=True)
    btn = gr.Button("出力", interactive=True, variant="primary")  # ここで青色ボタンに

    def enable_btn(file):
        return gr.update(interactive=True)

    file_input.change(enable_btn, inputs=file_input, outputs=btn)

    def on_click(uploaded_file, extensions, prefix, suffix):
        if uploaded_file is None:
            raise gr.Error("zipまたはファイルをアップロードしてください。")
        return export_structure_and_code(uploaded_file, extensions, prefix, suffix)

    btn.click(on_click, inputs=[file_input, ext_input, prefix_input, suffix_input], outputs=[out1, out2, notify])

demo.launch(inbrowser=True)
