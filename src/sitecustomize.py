# FILE: src/sitecustomize.py
from pathlib import Path

from dotenv import load_dotenv

# リポジトリ直下の .env を読む（NexusCore/ の直下にある想定）
proj_root = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=proj_root / ".env", override=False)
