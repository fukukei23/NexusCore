from flask import Blueprint, render_template, redirect, url_for, request, flash, Response
from app import db
from app.models import Product
from app.forms import ProductForm
import csv
import io
from datetime import datetime

bp = Blueprint('main', __name__)

@bp.route('/manage', methods=['GET', 'POST'])
def manage_products():
    form = ProductForm()
    if form.validate_on_submit():
        product = Product(
            name=form.name.data,
            brand=form.brand.data,
            purchase_price=form.purchase_price.data,
            selling_price=form.selling_price.data,
            supplier_url=form.supplier_url.data,
            image_url=form.image_url.data,
            stock_status=form.stock_status.data,
            transaction_fee=form.transaction_fee.data,
            shipping_cost=form.shipping_cost.data,
            customs_duty=form.customs_duty.data,
            procurement_fee=form.procurement_fee.data
        )
        if hasattr(product, "calculate_profit"):
            product.profit = product.calculate_profit()
        db.session.add(product)
        db.session.commit()
        flash('商品を登録しました', 'success')
        return redirect(url_for('main.manage_products'))
    products = Product.query.all()
    return render_template('products/manage.html', form=form, products=products)

@bp.route('/products/<int:id>/delete', methods=['POST'])
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash('商品を削除しました', 'success')
    return redirect(url_for('main.manage_products'))

@bp.route('/import_csv', methods=['POST'])
def import_csv():
    if 'file' not in request.files:
        flash('ファイルがアップロードされていません', 'error')
        return redirect(url_for('main.manage_products'))
    file = request.files['file']
    if file.filename == '':
        flash('ファイルが選択されていません', 'error')
        return redirect(url_for('main.manage_products'))
    if file and file.filename.endswith('.csv'):
        try:
            stream = io.StringIO(file.stream.read().decode('utf-8'))
            csv_reader = csv.DictReader(stream)
            count = 0
            for row in csv_reader:
                required_fields = ['name', 'purchase_price', 'selling_price']
                if not all(field in row for field in required_fields):
                    flash('CSVに必須項目が不足しています', 'error')
                    return redirect(url_for('main.manage_products'))
                product = Product(
                    name=row['name'],
                    brand=row.get('brand', ''),
                    purchase_price=float(row['purchase_price']),
                    selling_price=float(row['selling_price']),
                    supplier_url=row.get('supplier_url', ''),
                    image_url=row.get('image_url', ''),
                    stock_status=row.get('stock_status', 'true').lower() in ['true', '1', 'yes'],
                    transaction_fee=float(row.get('transaction_fee', 0)),
                    shipping_cost=float(row.get('shipping_cost', 0)),
                    customs_duty=float(row.get('customs_duty', 0)),
                    procurement_fee=float(row.get('procurement_fee', 0))
                )
                if hasattr(product, "calculate_profit"):
                    product.profit = product.calculate_profit()
                db.session.add(product)
                count += 1
            db.session.commit()
            flash(f'{count}件の商品をインポートしました', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'CSVインポート中にエラーが発生しました: {str(e)}', 'error')
    else:
        flash('CSVファイルのみアップロード可能です', 'error')
    return redirect(url_for('main.manage_products'))

@bp.route('/export_csv')
def export_csv():
    try:
        products = Product.query.all()
        output = io.StringIO()
        writer = csv.writer(output)

        # ヘッダー書き込み
        writer.writerow([
            'name', 'brand', 'purchase_price', 'selling_price',
            'transaction_fee', 'shipping_cost', 'customs_duty', 'procurement_fee',
            'supplier_url', 'image_url', 'stock_status'
        ])

        # データ書き込み
        for product in products:
            writer.writerow([
                product.name,
                product.brand,
                product.purchase_price,
                product.selling_price,
                product.transaction_fee,
                product.shipping_cost,
                product.customs_duty,
                product.procurement_fee,
                product.supplier_url,
                product.image_url,
                'true' if product.stock_status else 'false'
            ])

        output.seek(0)
        date_str = datetime.now().strftime('%Y%m%d%H%M%S')
        # 文字化け対策: BOM付きUTF-8
        bom = '\ufeff'
        csv_data = bom + output.getvalue()

        return Response(
            csv_data,
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment;filename=products_{date_str}.csv",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )

    except Exception as e:
        flash(f'CSVエクスポート中にエラーが発生しました: {str(e)}', 'error')
        return redirect(url_for('main.manage_products'))

@bp.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    form = ProductForm(obj=product)
    if form.validate_on_submit():
        form.populate_obj(product)
        if hasattr(product, "calculate_profit"):
            product.profit = product.calculate_profit()
        db.session.commit()
        flash('商品情報を更新しました', 'success')
        return redirect(url_for('main.manage_products'))
    return render_template('products/edit.html', form=form, product=product)

@bp.route('/')
def index():
    return redirect(url_for('main.manage_products'))
