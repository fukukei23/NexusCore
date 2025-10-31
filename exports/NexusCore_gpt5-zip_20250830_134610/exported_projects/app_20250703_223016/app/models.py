# app/models.py
from app import db
from datetime import datetime

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    brand = db.Column(db.String(128))
    purchase_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    supplier_url = db.Column(db.String(500))
    image_url = db.Column(db.String(500))
    stock_status = db.Column(db.Boolean, default=True)
    profit = db.Column(db.Float)
    listings = db.relationship('Listing', backref='product', lazy='dynamic')

    # 経費項目
    transaction_fee = db.Column(db.Float, default=0.0)
    shipping_cost = db.Column(db.Float, default=0.0)
    customs_duty = db.Column(db.Float, default=0.0)
    procurement_fee = db.Column(db.Float, default=0.0)

    def calculate_profit(self, fee_rate=0.15):
        """None対策済みの利益計算式"""
        calculated_profit = (
            (self.selling_price or 0) 
            - (self.purchase_price or 0)
            - ((self.selling_price or 0) * fee_rate)
            - (self.transaction_fee or 0)
            - (self.shipping_cost or 0)
            - (self.customs_duty or 0)
            - (self.procurement_fee or 0)
        )
        self.profit = calculated_profit
        return calculated_profit

    def __repr__(self):
        return f"<Product {self.name}>"

class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50), nullable=False)
    fee_rate = db.Column(db.Float)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    listing_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
