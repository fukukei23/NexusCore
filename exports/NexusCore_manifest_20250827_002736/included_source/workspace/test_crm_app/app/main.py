def add_user(username: str, email: str = None, phone: str = None, address: str = None) -> bool:
    """ユーザーを追加する関数。ユーザー名は必須。その他の情報はオプション。

    Args:
        username (str): 追加するユーザー名（必須）
        email (str, optional): ユーザーのメールアドレス（オプション）. Defaults to None.
        phone (str, optional): ユーザーの電話番号（オプション）. Defaults to None.
        address (str, optional): ユーザーの住所（オプション）. Defaults to None.

    Returns:
        bool: ユーザーの追加に成功した場合はTrue、失敗した場合はFalseを返す
    """

    if not username:
        return False  # ユーザー名が空の場合はFalseを返す

    # ここではユーザーを追加する処理を想定した擬似的な実装を行います。
    # 実際のアプリケーションでは、データベースへの登録やAPI呼び出しなどを行う必要があります。

    user_data = {"username": username}
    if email:
        user_data["email"] = email
    if phone:
        user_data["phone"] = phone  # phoneを使用
    if address:
        user_data["address"] = address

    # usersをグローバル変数として使用せず、関数内で辞書を管理するように変更
    if 'users' not in globals():
        global users
        users = {}


    if username in users:
        return False  # ユーザー名が既に存在する場合はFalseを返す
    users[username] = user_data

    return True


def get_user(username: str) -> dict:
    """ユーザー名に基づいてユーザー情報を取得する関数。

    Args:
        username (str): 取得したいユーザー名

    Returns:
        dict: ユーザー情報を含む辞書。存在しない場合は空の辞書を返す。
    """
    if 'users' not in globals():
        return {}  # usersが初期化されていない場合は空の辞書を返す
    if username in users:
        return users[username]
    else:
        return {}


def get_all_users() -> list:
    """登録されているすべてのユーザーの情報を取得する関数。

    Returns:
        list: ユーザー情報（辞書）のリストを返す。
    """
    if 'users' not in globals():
        return []  # usersが初期化されていない場合は空のリストを返す
    return list(users.values())