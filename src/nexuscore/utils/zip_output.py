import os
import zipfile
from datetime import datetime


def zip_project(output_dir="deploy_output"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = os.path.join(output_dir, f"OpenCodeInterpreter_{timestamp}.zip")

    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
        for foldername, subfolders, filenames in os.walk("."):
            if any(x in foldername for x in [".git", "__pycache__", "venv", ".mypy_cache"]):
                continue
            for filename in filenames:
                filepath = os.path.join(foldername, filename)
                arcname = os.path.relpath(filepath, ".")
                zipf.write(filepath, arcname)
    print(f"✅ プロジェクトが {zip_filename} に保存されました")
