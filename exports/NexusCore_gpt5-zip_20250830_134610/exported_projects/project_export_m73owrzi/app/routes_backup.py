# app/routes.py
@app.route('/products/filter', methods=['GET', 'POST'])
def filter_products():
    form = ProfitFilterForm()
    if form.validate_on_submit():
        return redirect(url_for('index', min_profit=form.min_profit.data))
    return render_template('filter.html', form=form)
