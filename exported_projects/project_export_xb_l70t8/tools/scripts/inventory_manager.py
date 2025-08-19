import pandas as pd
import json
from datetime import datetime
import os

# 設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE_DIR, 'tools', 'buyma_products.csv')
INVENTORY_FILE = os.path.join(BASE_DIR, 'tools', 'inventory.json')

class InventoryManager:
    """在庫管理システム"""
    def __init__(self):
        self.inventory = {}
        self.load_inventory()
    
    def load_inventory(self):
        try:
            with open(INVENTORY_FILE, 'r', encoding='utf-8') as f:
                self.inventory = json.load(f)
        except FileNotFoundError:
            self.inventory = {}
    
    def save_inventory(self):
        with open(INVENTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.inventory, f, ensure_ascii=False, indent=2)
    
    def update_stock(self, item_id, quantity):
        self.inventory[item_id] = {
            "quantity": quantity,
            "last_updated": datetime.now().isoformat(),
            "status": "在庫あり" if quantity > 0 else "在庫切れ"
        }
        self.save_inventory()
    
    def get_stock(self, item_id):
        return self.inventory.get(item_id, {"quantity": 0, "status": "未登録"})

def detect_category(text):
    """カテゴリ自動判定ロジック（テキストのみ）"""
    if not isinstance(text, str):
        text = str(text)  # 念のため型変換
    text = text.lower()
    categories = {
        "バッグ": ["bag", "バッグ", "トート", "ショルダー"],
        "財布": ["wallet", "財布", "コインケース"],
        "時計": ["watch", "時計", "クロノグラフ"],
        "アクセサリー": ["jewelry", "ネックレス", "ブレスレット"],
        "服飾": ["coat", "ジャケット", "ドレス", "スカート"]
    }
    for cat, keywords in categories.items():
        if any(kw in text for kw in keywords):
            return cat
    return "その他"

def process_products(inventory):
    """商品データ処理メインロジック（自動アクセスなし）"""
    df = pd.read_csv(CSV_PATH, encoding='cp932')
    results = []
    
    for idx, row in df.iterrows():
        product = row.to_dict()
        item_id = product.get("商品管理番号", f"ITEM-{idx+1:03d}")
        
        # 在庫情報取得
        stock = inventory.get_stock(item_id)
        
        # カテゴリ自動判定（商品名や説明から）
        category = detect_category(product.get("商品名", "") + " " + product.get("商品説明", ""))
        
        # 発送方法判定
        price = product.get("販売価格", 0)
        weight = product.get("重量", 0)
        if price >= 500000:
            shipping_method = "DHL EXPRESS"
        elif weight > 10:
            shipping_method = "特別大型便"
        elif category == "バッグ":
            shipping_method = "BUYMA YAMATO"
        else:
            shipping_method = "標準発送"
        
        # データ統合
        processed = {
            **product,
            "在庫数": stock["quantity"],
            "在庫ステータス": stock["status"],
            "カテゴリ（自動判定）": category,
            "発送方法（自動判定）": shipping_method
        }
        results.append(processed)
        
        # 在庫更新（サンプル実装）
        inventory.update_stock(item_id, processed.get("在庫数", 0))
        
    return pd.DataFrame(results)

def main():
    inventory = InventoryManager()
    
    processed_df = process_products(inventory)
    output_path = os.path.join(BASE_DIR, 'tools', 'processed_products.csv')
    processed_df.to_csv(output_path, index=False, encoding='cp932')
    print(f"処理完了: {len(processed_df)}件の商品を出力")
    
    # 在庫アラート
    low_stock = [k for k,v in inventory.inventory.items() if v['quantity'] < 5]
    if low_stock:
        print(f"警告: 在庫不足商品 {len(low_stock)}件")
    
    inventory.save_inventory()

if __name__ == "__main__":
    main()
