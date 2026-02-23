# src/file_creator.py
import os


def create_code_file(filename: str, code: str, folder: str = "src/generated") -> str:
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    return path
