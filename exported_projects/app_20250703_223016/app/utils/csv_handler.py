# app/utils/csv_handler.py
import csv
from io import TextIOWrapper
from app import db # dbオブジェクトをインポート
from app.models import Product # Productモデルをインポート

def import_products_from_csv(file):
    # ファイルをUTF-8で開く
    csv_file = TextIOWrapper(file, encoding='utf-8')
    reader = csv.DictReader(csv_file)
    
    # 既存のデータをクリアするか、更新するかは要検討
    # ここでは単純に追加する例

    for row in reader:
        try:
            # CSVの列名とProductモデルの属性名を合わせる
            # CSVファイルが以下の列を持つと仮定: '商品名', 'ブランド', '仕入価格', '販売価格', '仕入先URL', '画像URL', '在庫状況'
            product = Product(
                name=row.get('商品名', ''),
                brand=row.get('ブランド', ''),
                purchase_price=float(row.get('仕入価格', 0.0)),
                selling_price=float(row.get('販売価格', 0.0)),
                supplier_url=row.get('仕入先URL', ''),
                image_url=row.get('画像URL', ''),
                stock_status=(row.get('在庫状況', 'True').lower() == 'true') # 'True'/'False'文字列を真偽値に変換
            )
            # 利益率を計算して設定
            product.profit_margin = product.calculate_profit()
            db.session.add(product)
        except ValueError as e:
            print(f"CSVインポートエラー: 数値変換失敗 - {row}, エラー: {e}")
            # エラー処理。スキップするか、ログに記録するかなど
            continue
        except KeyError as e:
            print(f"CSVインポートエラー: 必須列が見つかりません - {e}, 行データ: {row}")
            continue

    db.session.commit()