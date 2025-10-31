# app/utils/pricing_calculator.py

def calculate_profit(purchase_price, selling_price, shipping_cost=0, fee_rate=0.15):
    """
    商品の利益を計算します。
    :param purchase_price: 仕入価格
    :param selling_price: 販売価格
    :param shipping_cost: 想定される発送費用 (固定値または動的に計算)
    :param fee_rate: 販売プラットフォームの手数料率 (例: BUYMAの15%)
    :return: 利益
    """
    fees = selling_price * fee_rate
    profit = selling_price - purchase_price - fees - shipping_cost
    return profit