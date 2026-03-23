def add_two_integers(a, b):
    """
    2つの整数を加算して返す。
    整数以外の型が与えられた場合は ValueError を投げる。
    """
    if not isinstance(a, int) or not isinstance(b, int):
        raise ValueError("入力は整数である必要があります")
    return a + b
