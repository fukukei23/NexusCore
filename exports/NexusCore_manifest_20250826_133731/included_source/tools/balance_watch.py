import os, json
from pathlib import Path
from datetime import datetime
import requests

USAGE_DIR = Path(os.getenv("NEXUS_USAGE_DIR","./data/usage"))
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL","")
DEEPSEEK_PREPAID = float(os.getenv("DEEPSEEK_PREPAID_USD","0") or 0)
DEEPSEEK_ALERT = float(os.getenv("DEEPSEEK_ALERT_USD","5") or 5)
MOONSHOT_BUDGET = float(os.getenv("MOONSHOT_BUDGET_USD","0") or 0)
MOONSHOT_ALERT_RATIO = float(os.getenv("MOONSHOT_ALERT_RATIO","0.8") or 0.8)

def load_this_month():
    ym = datetime.utcnow().strftime("%Y%m")
    fp = USAGE_DIR / f"usage_{ym}.jsonl"
    rows=[]
    if fp.exists():
        for line in fp.read_text(encoding="utf-8").splitlines():
            try: rows.append(json.loads(line))
            except: pass
    return rows

def aggregate(rows):
    total = 0.0; per = {}
    for r in rows:
        amt = float(r.get("total_usd") or 0)
        prov = r.get("provider","unknown")
        total += amt
        per[prov] = per.get(prov,0.0) + amt
    return total, per

def usd(v): return f"${v:,.2f}"

def slack(msg):
    if not SLACK_WEBHOOK: 
        print("[DRYRUN]\n"+msg); return
    try:
        requests.post(SLACK_WEBHOOK, json={"text": msg}, timeout=10)
    except Exception as e:
        print("Slack post failed:", e)

def main():
    rows = load_this_month()
    total, byp = aggregate(rows)
    lines = [f":bar_chart: This month total {usd(total)}",
             "・by provider: " + ", ".join(f"{k} {usd(v)}" for k,v in byp.items())]

    if DEEPSEEK_PREPAID > 0:
        used = byp.get("deepseek", 0.0)
        left = max(DEEPSEEK_PREPAID - used, 0.0)
        lines.append(f"DeepSeek: used {usd(used)} / prepaid {usd(DEEPSEEK_PREPAID)} -> left {usd(left)}")
        if left <= DEEPSEEK_ALERT:
            slack(f":warning: DeepSeek 残高が閾値を下回りました。残り {usd(left)}")

    if MOONSHOT_BUDGET > 0:
        used = byp.get("moonshot", 0.0)
        ratio = used / MOONSHOT_BUDGET if MOONSHOT_BUDGET else 0
        lines.append(f"Moonshot: used {usd(used)} / budget {usd(MOONSHOT_BUDGET)} ({ratio*100:.1f}%)")
        if ratio >= MOONSHOT_ALERT_RATIO:
            slack(f":warning: Moonshot 月次使用が {ratio*100:.1f}%（{usd(used)} / {usd(MOONSHOT_BUDGET)}）")

    msg = "\n".join(lines)
    slack(msg); print(msg)

if __name__ == "__main__":
    main()
