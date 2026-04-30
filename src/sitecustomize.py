# FILE: src/sitecustomize.py
from pathlib import Path

try:
    from dotenv import load_dotenv

    proj_root = Path(__file__).resolve().parents[1]
    load_dotenv(dotenv_path=proj_root / ".env", override=False)
except ImportError:
    pass
