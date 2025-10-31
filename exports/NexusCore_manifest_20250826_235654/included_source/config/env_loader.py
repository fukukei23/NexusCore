# src/nexuscore/config/env_loader.py
import os
from pathlib import Path
from dotenv import load_dotenv

def load_env_safe(env_path: str = ".env"):
    """
    安全に .env を読み込む（改行・空白除去＋UTF-8強制）
    """
    env_file = Path(env_path)

    if not env_file.exists():
        raise FileNotFoundError(f".env file not found at {env_file.resolve()}")

    # UTF-8で読み込み（BOM除去も含む）
    with open(env_file, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()

    cleaned_lines = []
    for line in lines:
        # 改行や前後空白を除去
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            cleaned_lines.append(stripped)

    # 一時ファイルに書き戻して dotenv 読み込み
    tmp_env_path = env_file.parent / ".env.cleaned"
    with open(tmp_env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(cleaned_lines))

    load_dotenv(dotenv_path=tmp_env_path, override=True)

    # 確認ログ
    for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]:
        if key in os.environ:
            val = os.environ[key]
            print(f"[ENV] {key}: len={len(val)} head={val[:6]}... tail={val[-5:]}")
        else:
            print(f"[ENV] {key}: (not set)")

    # 安全のため一時ファイル削除
    try:
        tmp_env_path.unlink()
    except:
        pass
