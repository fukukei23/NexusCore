# app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, BooleanField, SubmitField, URLField
from wtforms.validators import DataRequired, NumberRange, URL, Optional

class ProductForm(FlaskForm):
    # 基本情報
    name = StringField('商品名', validators=[DataRequired()])
    brand = StringField('ブランド')
    purchase_price = FloatField('仕入価格', validators=[
        DataRequired(),
        NumberRange(min=0, message="0以上の数値を入力してください")
    ])
    selling_price = FloatField('販売価格', validators=[
        DataRequired(),
        NumberRange(min=0, message="0以上の数値を入力してください")
    ])
    
    # 経費項目（追加部分）
    transaction_fee = FloatField('取引手数料', validators=[Optional()])
    shipping_cost = FloatField('送料・梱包費', validators=[Optional()])
    customs_duty = FloatField('関税・輸入消費税', validators=[Optional()])
    procurement_fee = FloatField('買付代行料', validators=[Optional()])
    
    # URL関連
    supplier_url = URLField('仕入先URL', validators=[
        URL(message='有効なURLを入力してください', require_tld=False)
    ])
    image_url = URLField('画像URL', validators=[
        URL(message='有効なURLを入力してください', require_tld=False)
    ])
    
    # 在庫
    stock_status = BooleanField('在庫あり')
    
    submit = SubmitField('登録/更新')

class ProfitFilterForm(FlaskForm):
    min_profit = FloatField('最低利益額', validators=[
        NumberRange(min=0, message="0以上の数値を入力してください")
    ])
    submit = SubmitField('絞り込み')
