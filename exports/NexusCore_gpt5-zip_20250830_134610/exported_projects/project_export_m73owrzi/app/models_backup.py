# app/models.py
from app import db # app/__init__.py で定義されたdbオブジェクトをインポート

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    brand = db.Column(db.String(60))
    purchase_price = db.Column(db.Float)
    selling_price = db.Column(db.Float)
    supplier_url = db.Column(db.String(500))
    image_url = db.Column(db.String(500))
    stock_status = db.Column(db.Boolean, default=True)
    profit_margin = db.Column(db.Float) # これは手動で更新するか、calculate_profitで計算後に保存

    def calculate_profit(self):
        # 手数料15%仮定。必要であれば、config.py などで設定できるようにしても良い
        # shipping_costは別途考慮が必要な場合、引数で渡すか、Productモデルに含める
        return self.selling_price - self.purchase_price - (self.selling_price * 0.15)

    def __repr__(self):
        return f"<Product {self.name}>"