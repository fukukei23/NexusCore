import pandas as pd

# CSVファイルをcp932で読み込む（正しいパスに修正）
df = pd.read_csv('../buyma_products.csv', encoding='cp932')

def check_constraints(product):
    errors = []
    # 必要に応じて型変換
    try:
        price = float(product.get("価格", 0))
        weight = float(product.get("重量", 0))
        battery = str(product.get("電池有無", "")).strip()
        size_sum = float(product.get("3辺和", 0))
        insurance = float(product.get("保険金額", 0))
        region = str(product.get("地域", "")).strip()
        anonymity = str(product.get("匿名希望", "")).strip() == "あり"
        shipping = str(product.get("発送方法", "")).strip()
    except Exception as e:
        errors.append(f"データ型エラー: {e}")
        return errors

    if price >= 500000 and shipping == "DHL EXPRESS":
        errors.append("DHLは50万円以上の商品不可")
    if weight > 10 and shipping == "DHL EXPRESS":
        errors.append("DHLは10kg超不可")
    if battery == "あり" and shipping == "Speedpost":
        errors.append("Speedpostは電池類不可")
    if size_sum > 200 and shipping == "BUYMA YAMATO":
        errors.append("BUYMA YAMATOは3辺和200cm超不可")
    if insurance > 500 and shipping == "USPS特別割引":
        errors.append("USPS特別割引は$500超不可")
    return errors

def select_shipping(product):
    price = float(product.get("価格", 0))
    weight = float(product.get("重量", 0))
    battery = str(product.get("電池有無", "")).strip()
    region = str(product.get("地域", "")).strip()
    anonymity = str(product.get("匿名希望", "")).strip() == "あり"

    if price >= 500000 or weight > 10:
        return "BUYMA YAMATO" if region == "北米" else "個別見積もり"
    if battery == "あり":
        return "DHL EXPRESS"
    if region == "北米" and anonymity:
        return "BUYMA YAMATO"
    if price <= 500 and region == "アメリカ":
        return "USPS特別割引"
    if region == "香港" and battery != "あり":
        return "Speedpost"
    return "標準発送"

# 商品ごとに判定＆チェック
for idx, row in df.iterrows():
    product = row.to_dict()
    product["発送方法自動判定"] = select_shipping(product)
    errors = check_constraints(product)
    if errors:
        print(f"エラー: {product.get('商品管理番号', idx+1)} - {', '.join(errors)}")
    else:
        print(f"OK: {product.get('商品管理番号', idx+1)} - {product['発送方法自動判定']}")

# 発送方法自動判定をCSVに保存
df["発送方法自動判定"] = df.apply(select_shipping, axis=1)
df.to_csv('../buyma_products_checked.csv', encoding='cp932', index=False)
print("\n判定結果を '../buyma_products_checked.csv' に保存しました。")
