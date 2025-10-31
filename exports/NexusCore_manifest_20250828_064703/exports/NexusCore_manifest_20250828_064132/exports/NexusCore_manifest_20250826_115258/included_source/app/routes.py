# app/routes.py
from flask import Blueprint, render_template, redirect, url_for, request, flash, Response
from app import db
from app.models import Product                      # ← models.py で定義した ORM クラス[1]
from app.forms  import ProductForm                  # ← WTForms フォーム
import csv, io
from datetime import datetime

bp = Blueprint('main', __name__)                    # ① Blueprint 宣言

# --------------------------------------------------
# ② 一覧＋新規登録
# --------------------------------------------------
@bp.route('/products', methods=['GET', 'POST'])
def manage_products():
    form = ProductForm()
    if form.validate_on_submit():                   # 追加ボタンが押されたとき
        product = Product(
            name= form.name.data,
            brand=form.brand.data,
            purchase_price=form.purchase_price.data,
            selling_price =form.selling_price.data,
            supplier_url  =form.supplier_url.data,
            image_url     =form.image_url.data,
            stock_status  =form.stock_status.data,
            transaction_fee=form.transaction_fee.data,
            shipping_cost   =form.shipping_cost.data,
            customs_duty    =form.customs_duty.data,
            procurement_fee =form.procurement_fee.data,
        )
        # 利益をその場で計算して保存
        product.profit = product.calculate_profit()      # [1]
        db.session.add(product)
        db.session.commit()
        flash('商品を登録しました', 'success')
        return redirect(url_for('main.manage_products'))

    products = Product.query.all()
    return render_template('products/manage.html',
                           form=form, products=products)

# --------------------------------------------------
# ③ CSV 取込
# --------------------------------------------------
@bp.route('/products/import', methods=['POST'])
def import_csv():
    if 'file' not in request.files:
        flash('CSV ファイルがありません', 'error')
        return redirect(url_for('main.manage_products'))

    f = request.files['file']
    if not f.filename.endswith('.csv'):
        flash('CSV だけアップロードできます', 'error')
        return redirect(url_for('main.manage_products'))

    stream  = io.StringIO(f.stream.read().decode('utf-8-sig'))
    reader  = csv.DictReader(stream)
    created = 0
    for row in reader:
        # 必須カラムチェック
        if not all(k in row for k in ('name', 'purchaseprice', 'sellingprice')):
            flash('必須列が不足しています', 'error')
            return redirect(url_for('main.manage_products'))

        p = Product(
            name = row['name'],
            brand= row.get('brand', ''),
            purchase_price=float(row['purchaseprice']),
            selling_price =float(row['sellingprice']),
            supplier_url  =row.get('supplierurl', ''),
            image_url     =row.get('imageurl', ''),
            stock_status  =row.get('stockstatus', 'true').lower() in ('true','1','yes'),
            transaction_fee=float(row.get('transactionfee',0)),
            shipping_cost   =float(row.get('shippingcost',0)),
            customs_duty    =float(row.get('customsduty',0)),
            procurement_fee =float(row.get('procurementfee',0)),
        )
        p.profit = p.calculate_profit()                 # [1]
        db.session.add(p)
        created += 1
    db.session.commit()
    flash(f'{created} 件取り込みました', 'success')
    return redirect(url_for('main.manage_products'))

# --------------------------------------------------
# ③ CSV 書出し
# --------------------------------------------------
@bp.route('/products/export')
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'name','brand','purchaseprice','sellingprice',
        'transactionfee','shippingcost','customsduty','procurementfee',
        'supplierurl','imageurl','stockstatus'
    ])
    for p in Product.query.all():
        writer.writerow([
            p.name, p.brand, p.purchase_price, p.selling_price,
            p.transaction_fee, p.shipping_cost, p.customs_duty, p.procurement_fee,
            p.supplier_url, p.image_url, 'true' if p.stock_status else 'false'
        ])
    output.seek(0)
    data = '\ufeff' + output.getvalue()                  # UTF-8 BOM 付き[1]
    dt   = datetime.now().strftime('%Y%m%d%H%M%S')
    return Response(
        data, mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=products_{dt}.csv'}
    )

# --------------------------------------------------
# ④ 編集・削除
# --------------------------------------------------
@bp.route('/products/<int:pid>/edit', methods=['GET','POST'])
def edit_product(pid):
    product = Product.query.get_or_404(pid)
    form = ProductForm(obj=product)
    if form.validate_on_submit():
        form.populate_obj(product)
        product.profit = product.calculate_profit()
        db.session.commit()
        flash('更新しました', 'success')
        return redirect(url_for('main.manage_products'))
    return render_template('products/edit.html', form=form, product=product)

@bp.route('/products/<int:pid>/delete', methods=['POST'])
def delete_product(pid):
    product = Product.query.get_or_404(pid)
    db.session.delete(product)
    db.session.commit()
    flash('削除しました', 'success')
    return redirect(url_for('main.manage_products'))

# --------------------------------------------------
# ⑤ ルートリダイレクト
# --------------------------------------------------
@bp.route('/')
def index():
    return redirect(url_for('main.manage_products'))
