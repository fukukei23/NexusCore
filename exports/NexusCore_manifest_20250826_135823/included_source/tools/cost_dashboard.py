# ==============================================================================
# ファイル: tools/cost_dashboard.py
# 目的  : 1K in + 2K out の単価テーブルをもとに、件数/日→月額を即時計算。
# 実行  : streamlit run tools/cost_dashboard.py
# 依存  : pip install streamlit pandas
# 備考  : 実運用では COST_TABLE を .env or JSON 読み込みに変更推奨。
# ==============================================================================

import os
import json
import pandas as pd
import streamlit as st

DEFAULT_COST = {
    "gpt-4o":               {"in": 2.50,  "out": 10.00},
    "gemini-1.5-flash-latest": {"in": 0.0375, "out": 0.15},
    "claude-3.5-sonnet":    {"in": 3.00,  "out": 15.00},
    "claude-3.5-haiku":     {"in": 0.80,  "out": 1.00},
    "deepseek-reasoner":    {"in": 0.55,  "out": 2.19},
    "command-r-plus-08-2024":{"in": 2.50,  "out": 10.00},
    "kimi-k2":              {"in": 0.15,  "out": 2.50},
}

st.set_page_config(page_title="NexusCore LLM Cost Dashboard", layout="wide")

st.title("📊 NexusCore LLM コスト見積ダッシュボード")
st.caption("※ 価格は参考値。必ず最新の公式価格で上書きしてください。")

# コストテーブルの読み込み（任意 JSON パス）
json_path = st.text_input("コスト表JSONパス（任意）", value="")
cost_table = DEFAULT_COST.copy()
if json_path and os.path.exists(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        cost_table = json.load(f)

in_tok = st.number_input("1件あたり入力トークン", min_value=0, value=1000, step=100)
out_tok = st.number_input("1件あたり出力トークン", min_value=0, value=2000, step=100)
tasks_per_month = st.number_input("月間タスク件数", min_value=0, value=1000, step=100)
jpy_rate = st.number_input("USD→JPY 換算レート", min_value=1.0, value=155.0, step=0.5)

rows = []
for name, p in cost_table.items():
    usd = (p["in"] * (in_tok/1_000_000)) + (p["out"] * (out_tok/1_000_000))
    monthly_usd = usd * tasks_per_month
    rows.append({
        "モデル": name,
        "1件USD": round(usd, 6),
        "月額USD": round(monthly_usd, 2),
        "月額JPY(参考)": round(monthly_usd * jpy_rate),
        "備考": ""
    })

df = pd.DataFrame(rows).sort_values("月額USD")
st.dataframe(df, use_container_width=True)

st.bar_chart(df.set_index("モデル")["月額USD"])
