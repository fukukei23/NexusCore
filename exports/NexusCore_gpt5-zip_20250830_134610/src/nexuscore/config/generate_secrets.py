# ================================================================
# ファイル名: generate_secrets.py
# 目的: .env をもとに secrets.py/.env.template を自動生成する
# 保存場所: src/nexuscore/config/
# ================================================================

import os
from pathlib import Path
from dotenv import dotenv_values

# ============================================
# パス設定（プロジェクトルートに .env がある前提）
# ============================================
ROOT_PATH = Path(__file__).resolve().parents[3]
ENV_PATH = ROOT_PATH / ".env"
TEMPLATE_PATH = ROOT_PATH / ".env.template"
SECRETS_PATH = Path(__file__).parent / "secrets.py"

# ============================================
# .env の存在確認
# ============================================
if not ENV_PATH.exists():
    raise FileNotFoundError(f".env ファイルが存在しません: {ENV_PATH}")

# ============================================
# .env 読み込み
# ============================================
env_vars = dotenv_values(ENV_PATH)

# ============================================
# secrets.py の内容生成
# ============================================
secrets_lines = [
    '"""',
    "secrets.py - 自動生成ファイル（.envから取得）",
    '"""',
    "",
    "class Secrets:",
]
for key, value in env_vars.items():
    safe_value = value.replace('"', '\\"') if value else ""
    secrets_lines.append(f'    {key} = "{safe_value}"')

# ============================================
# .env.template の内容生成
# ============================================
template_lines = [
    "# .env.template - 自動生成ファイル",
    "# 各項目を手動で入力してください",
]
for key in env_vars.keys():
    template_lines.append(f"{key}=")

# ============================================
# ファイル出力
# ============================================
SECRETS_PATH.write_text("\n".join(secrets_lines), encoding="utf-8")
print(f"[OK] secrets.py を生成しました → {SECRETS_PATH}")

TEMPLATE_PATH.write_text("\n".join(template_lines), encoding="utf-8")
print(f"[OK] .env.template を生成しました → {TEMPLATE_PATH}")
