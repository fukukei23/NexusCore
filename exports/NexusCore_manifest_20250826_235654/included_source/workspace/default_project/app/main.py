def add(num1: float, num2: float) -> float:
    """二つの数値を受け取り、その合計を返す関数。

    Args:
        num1 (float): 最初の数値
        num2 (float): 二番目の数値

    Returns:
        float: 二つの数値の合計
    """
    if not isinstance(num1, (int, float)) or not isinstance(num2, (int, float)):
        raise TypeError("Invalid input type")

    return float(num1) + float(num2)


def subtract(a: float, b: float) -> float:
    """二つの数値を引く。

    Args:
        a (int or float): 引かれる数
        b (int or float): 引く数

    Returns:
        int or float: a - b の結果
    """
    return a - b