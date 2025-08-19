
# === NexusCore/src\sandbox_executor.py ===
# ファイル名: sandbox_executor.py
# メモ:
# - run_code_in_sandbox()を呼び出し、標準出力・標準エラー・出力ファイルを返す
# - エラー・タイムアウトも判定しやすい
# - opencodeinterpreter_webui.py等からimportして使う

from sandbox_runner import run_code_in_sandbox

def execute_code_and_return_output(
    code,
    jupyter_state=None,      # 互換性のため残しているが未使用
    lang="python",
    input_files=None,
    output_files=None,
    timeout=10,
    cpu="0.5",
    memory="256m"
):
    """
    サンドボックスでコードを実行し、結果・エラー・出力ファイルを返す
    """
    try:
        stdout, stderr, returncode, outputs = run_code_in_sandbox(
            code=code,
            lang=lang,
            input_files=input_files,
            output_files=output_files,
            timeout=timeout,
            cpu=cpu,
            memory=memory
        )
        if returncode == 0:
            return stdout, "OK", outputs
        elif stderr == "Timeout":
            return "Timeout", "Timeout", outputs
        else:
            return stderr, "Error", outputs
    except Exception as e:
        return str(e), "Error", {}

# === NexusCore/exported_projects\app_20250703_223016\app\utils\csv_handler.py ===
# app/utils/csv_handler.py
import csv
from io import TextIOWrapper
from app import db # dbオブジェクトをインポート
from app.models import Product # Productモデルをインポート

def import_products_from_csv(file):
    # ファイルをUTF-8で開く
    csv_file = TextIOWrapper(file, encoding='utf-8')
    reader = csv.DictReader(csv_file)
    
    # 既存のデータをクリアするか、更新するかは要検討
    # ここでは単純に追加する例

    for row in reader:
        try:
            # CSVの列名とProductモデルの属性名を合わせる
            # CSVファイルが以下の列を持つと仮定: '商品名', 'ブランド', '仕入価格', '販売価格', '仕入先URL', '画像URL', '在庫状況'
            product = Product(
                name=row.get('商品名', ''),
                brand=row.get('ブランド', ''),
                purchase_price=float(row.get('仕入価格', 0.0)),
                selling_price=float(row.get('販売価格', 0.0)),
                supplier_url=row.get('仕入先URL', ''),
                image_url=row.get('画像URL', ''),
                stock_status=(row.get('在庫状況', 'True').lower() == 'true') # 'True'/'False'文字列を真偽値に変換
            )
            # 利益率を計算して設定
            product.profit_margin = product.calculate_profit()
            db.session.add(product)
        except ValueError as e:
            print(f"CSVインポートエラー: 数値変換失敗 - {row}, エラー: {e}")
            # エラー処理。スキップするか、ログに記録するかなど
            continue
        except KeyError as e:
            print(f"CSVインポートエラー: 必須列が見つかりません - {e}, 行データ: {row}")
            continue

    db.session.commit()

# === NexusCore/exported_projects\project_export_m73owrzi\app\utils\csv_handler.py ===
# app/utils/csv_handler.py
import csv
from io import TextIOWrapper
from app import db # dbオブジェクトをインポート
from app.models import Product # Productモデルをインポート

def import_products_from_csv(file):
    # ファイルをUTF-8で開く
    csv_file = TextIOWrapper(file, encoding='utf-8')
    reader = csv.DictReader(csv_file)
    
    # 既存のデータをクリアするか、更新するかは要検討
    # ここでは単純に追加する例

    for row in reader:
        try:
            # CSVの列名とProductモデルの属性名を合わせる
            # CSVファイルが以下の列を持つと仮定: '商品名', 'ブランド', '仕入価格', '販売価格', '仕入先URL', '画像URL', '在庫状況'
            product = Product(
                name=row.get('商品名', ''),
                brand=row.get('ブランド', ''),
                purchase_price=float(row.get('仕入価格', 0.0)),
                selling_price=float(row.get('販売価格', 0.0)),
                supplier_url=row.get('仕入先URL', ''),
                image_url=row.get('画像URL', ''),
                stock_status=(row.get('在庫状況', 'True').lower() == 'true') # 'True'/'False'文字列を真偽値に変換
            )
            # 利益率を計算して設定
            product.profit_margin = product.calculate_profit()
            db.session.add(product)
        except ValueError as e:
            print(f"CSVインポートエラー: 数値変換失敗 - {row}, エラー: {e}")
            # エラー処理。スキップするか、ログに記録するかなど
            continue
        except KeyError as e:
            print(f"CSVインポートエラー: 必須列が見つかりません - {e}, 行データ: {row}")
            continue

    db.session.commit()

# === NexusCore/exported_projects\project_export_xb_l70t8\app\utils\csv_handler.py ===
# app/utils/csv_handler.py
import csv
from io import TextIOWrapper
from app import db # dbオブジェクトをインポート
from app.models import Product # Productモデルをインポート

def import_products_from_csv(file):
    # ファイルをUTF-8で開く
    csv_file = TextIOWrapper(file, encoding='utf-8')
    reader = csv.DictReader(csv_file)
    
    # 既存のデータをクリアするか、更新するかは要検討
    # ここでは単純に追加する例

    for row in reader:
        try:
            # CSVの列名とProductモデルの属性名を合わせる
            # CSVファイルが以下の列を持つと仮定: '商品名', 'ブランド', '仕入価格', '販売価格', '仕入先URL', '画像URL', '在庫状況'
            product = Product(
                name=row.get('商品名', ''),
                brand=row.get('ブランド', ''),
                purchase_price=float(row.get('仕入価格', 0.0)),
                selling_price=float(row.get('販売価格', 0.0)),
                supplier_url=row.get('仕入先URL', ''),
                image_url=row.get('画像URL', ''),
                stock_status=(row.get('在庫状況', 'True').lower() == 'true') # 'True'/'False'文字列を真偽値に変換
            )
            # 利益率を計算して設定
            product.profit_margin = product.calculate_profit()
            db.session.add(product)
        except ValueError as e:
            print(f"CSVインポートエラー: 数値変換失敗 - {row}, エラー: {e}")
            # エラー処理。スキップするか、ログに記録するかなど
            continue
        except KeyError as e:
            print(f"CSVインポートエラー: 必須列が見つかりません - {e}, 行データ: {row}")
            continue

    db.session.commit()

# === NexusCore/exported_projects\project_export_y7xxp1v8\app\utils\csv_handler.py ===
# app/utils/csv_handler.py
import csv
from io import TextIOWrapper
from app import db # dbオブジェクトをインポート
from app.models import Product # Productモデルをインポート

def import_products_from_csv(file):
    # ファイルをUTF-8で開く
    csv_file = TextIOWrapper(file, encoding='utf-8')
    reader = csv.DictReader(csv_file)
    
    # 既存のデータをクリアするか、更新するかは要検討
    # ここでは単純に追加する例

    for row in reader:
        try:
            # CSVの列名とProductモデルの属性名を合わせる
            # CSVファイルが以下の列を持つと仮定: '商品名', 'ブランド', '仕入価格', '販売価格', '仕入先URL', '画像URL', '在庫状況'
            product = Product(
                name=row.get('商品名', ''),
                brand=row.get('ブランド', ''),
                purchase_price=float(row.get('仕入価格', 0.0)),
                selling_price=float(row.get('販売価格', 0.0)),
                supplier_url=row.get('仕入先URL', ''),
                image_url=row.get('画像URL', ''),
                stock_status=(row.get('在庫状況', 'True').lower() == 'true') # 'True'/'False'文字列を真偽値に変換
            )
            # 利益率を計算して設定
            product.profit_margin = product.calculate_profit()
            db.session.add(product)
        except ValueError as e:
            print(f"CSVインポートエラー: 数値変換失敗 - {row}, エラー: {e}")
            # エラー処理。スキップするか、ログに記録するかなど
            continue
        except KeyError as e:
            print(f"CSVインポートエラー: 必須列が見つかりません - {e}, 行データ: {row}")
            continue

    db.session.commit()

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_executor.py ===
# ファイル名: sandbox_executor.py
# メモ:
# - run_code_in_sandbox()を呼び出し、標準出力・標準エラー・出力ファイルを返す
# - エラー・タイムアウトも判定しやすい
# - opencodeinterpreter_webui.py等からimportして使う

from sandbox_runner import run_code_in_sandbox

def execute_code_and_return_output(
    code,
    jupyter_state=None,      # 互換性のため残しているが未使用
    lang="python",
    input_files=None,
    output_files=None,
    timeout=10,
    cpu="0.5",
    memory="256m"
):
    """
    サンドボックスでコードを実行し、結果・エラー・出力ファイルを返す
    """
    try:
        stdout, stderr, returncode, outputs = run_code_in_sandbox(
            code=code,
            lang=lang,
            input_files=input_files,
            output_files=output_files,
            timeout=timeout,
            cpu=cpu,
            memory=memory
        )
        if returncode == 0:
            return stdout, "OK", outputs
        elif stderr == "Timeout":
            return "Timeout", "Timeout", outputs
        else:
            return stderr, "Error", outputs
    except Exception as e:
        return str(e), "Error", {}

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\app_20250703_223016\app\utils\csv_handler.py ===
# app/utils/csv_handler.py
import csv
from io import TextIOWrapper
from app import db # dbオブジェクトをインポート
from app.models import Product # Productモデルをインポート

def import_products_from_csv(file):
    # ファイルをUTF-8で開く
    csv_file = TextIOWrapper(file, encoding='utf-8')
    reader = csv.DictReader(csv_file)
    
    # 既存のデータをクリアするか、更新するかは要検討
    # ここでは単純に追加する例

    for row in reader:
        try:
            # CSVの列名とProductモデルの属性名を合わせる
            # CSVファイルが以下の列を持つと仮定: '商品名', 'ブランド', '仕入価格', '販売価格', '仕入先URL', '画像URL', '在庫状況'
            product = Product(
                name=row.get('商品名', ''),
                brand=row.get('ブランド', ''),
                purchase_price=float(row.get('仕入価格', 0.0)),
                selling_price=float(row.get('販売価格', 0.0)),
                supplier_url=row.get('仕入先URL', ''),
                image_url=row.get('画像URL', ''),
                stock_status=(row.get('在庫状況', 'True').lower() == 'true') # 'True'/'False'文字列を真偽値に変換
            )
            # 利益率を計算して設定
            product.profit_margin = product.calculate_profit()
            db.session.add(product)
        except ValueError as e:
            print(f"CSVインポートエラー: 数値変換失敗 - {row}, エラー: {e}")
            # エラー処理。スキップするか、ログに記録するかなど
            continue
        except KeyError as e:
            print(f"CSVインポートエラー: 必須列が見つかりません - {e}, 行データ: {row}")
            continue

    db.session.commit()

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\project_export_m73owrzi\app\utils\csv_handler.py ===
# app/utils/csv_handler.py
import csv
from io import TextIOWrapper
from app import db # dbオブジェクトをインポート
from app.models import Product # Productモデルをインポート

def import_products_from_csv(file):
    # ファイルをUTF-8で開く
    csv_file = TextIOWrapper(file, encoding='utf-8')
    reader = csv.DictReader(csv_file)
    
    # 既存のデータをクリアするか、更新するかは要検討
    # ここでは単純に追加する例

    for row in reader:
        try:
            # CSVの列名とProductモデルの属性名を合わせる
            # CSVファイルが以下の列を持つと仮定: '商品名', 'ブランド', '仕入価格', '販売価格', '仕入先URL', '画像URL', '在庫状況'
            product = Product(
                name=row.get('商品名', ''),
                brand=row.get('ブランド', ''),
                purchase_price=float(row.get('仕入価格', 0.0)),
                selling_price=float(row.get('販売価格', 0.0)),
                supplier_url=row.get('仕入先URL', ''),
                image_url=row.get('画像URL', ''),
                stock_status=(row.get('在庫状況', 'True').lower() == 'true') # 'True'/'False'文字列を真偽値に変換
            )
            # 利益率を計算して設定
            product.profit_margin = product.calculate_profit()
            db.session.add(product)
        except ValueError as e:
            print(f"CSVインポートエラー: 数値変換失敗 - {row}, エラー: {e}")
            # エラー処理。スキップするか、ログに記録するかなど
            continue
        except KeyError as e:
            print(f"CSVインポートエラー: 必須列が見つかりません - {e}, 行データ: {row}")
            continue

    db.session.commit()

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\project_export_xb_l70t8\app\utils\csv_handler.py ===
# app/utils/csv_handler.py
import csv
from io import TextIOWrapper
from app import db # dbオブジェクトをインポート
from app.models import Product # Productモデルをインポート

def import_products_from_csv(file):
    # ファイルをUTF-8で開く
    csv_file = TextIOWrapper(file, encoding='utf-8')
    reader = csv.DictReader(csv_file)
    
    # 既存のデータをクリアするか、更新するかは要検討
    # ここでは単純に追加する例

    for row in reader:
        try:
            # CSVの列名とProductモデルの属性名を合わせる
            # CSVファイルが以下の列を持つと仮定: '商品名', 'ブランド', '仕入価格', '販売価格', '仕入先URL', '画像URL', '在庫状況'
            product = Product(
                name=row.get('商品名', ''),
                brand=row.get('ブランド', ''),
                purchase_price=float(row.get('仕入価格', 0.0)),
                selling_price=float(row.get('販売価格', 0.0)),
                supplier_url=row.get('仕入先URL', ''),
                image_url=row.get('画像URL', ''),
                stock_status=(row.get('在庫状況', 'True').lower() == 'true') # 'True'/'False'文字列を真偽値に変換
            )
            # 利益率を計算して設定
            product.profit_margin = product.calculate_profit()
            db.session.add(product)
        except ValueError as e:
            print(f"CSVインポートエラー: 数値変換失敗 - {row}, エラー: {e}")
            # エラー処理。スキップするか、ログに記録するかなど
            continue
        except KeyError as e:
            print(f"CSVインポートエラー: 必須列が見つかりません - {e}, 行データ: {row}")
            continue

    db.session.commit()

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\project_export_y7xxp1v8\app\utils\csv_handler.py ===
# app/utils/csv_handler.py
import csv
from io import TextIOWrapper
from app import db # dbオブジェクトをインポート
from app.models import Product # Productモデルをインポート

def import_products_from_csv(file):
    # ファイルをUTF-8で開く
    csv_file = TextIOWrapper(file, encoding='utf-8')
    reader = csv.DictReader(csv_file)
    
    # 既存のデータをクリアするか、更新するかは要検討
    # ここでは単純に追加する例

    for row in reader:
        try:
            # CSVの列名とProductモデルの属性名を合わせる
            # CSVファイルが以下の列を持つと仮定: '商品名', 'ブランド', '仕入価格', '販売価格', '仕入先URL', '画像URL', '在庫状況'
            product = Product(
                name=row.get('商品名', ''),
                brand=row.get('ブランド', ''),
                purchase_price=float(row.get('仕入価格', 0.0)),
                selling_price=float(row.get('販売価格', 0.0)),
                supplier_url=row.get('仕入先URL', ''),
                image_url=row.get('画像URL', ''),
                stock_status=(row.get('在庫状況', 'True').lower() == 'true') # 'True'/'False'文字列を真偽値に変換
            )
            # 利益率を計算して設定
            product.profit_margin = product.calculate_profit()
            db.session.add(product)
        except ValueError as e:
            print(f"CSVインポートエラー: 数値変換失敗 - {row}, エラー: {e}")
            # エラー処理。スキップするか、ログに記録するかなど
            continue
        except KeyError as e:
            print(f"CSVインポートエラー: 必須列が見つかりません - {e}, 行データ: {row}")
            continue

    db.session.commit()

# === NexusCore/openenv\Lib\site-packages\numpy\lib\_arraysetops_impl.py ===
"""
Set operations for arrays based on sorting.

Notes
-----

For floating point arrays, inaccurate results may appear due to usual round-off
and floating point comparison issues.

Speed could be gained in some operations by an implementation of
`numpy.sort`, that can provide directly the permutation vectors, thus avoiding
calls to `numpy.argsort`.

Original author: Robert Cimrman

"""
import functools
import warnings
from typing import NamedTuple

import numpy as np
from numpy._core import overrides
from numpy._core._multiarray_umath import _array_converter, _unique_hash

array_function_dispatch = functools.partial(
    overrides.array_function_dispatch, module='numpy')


__all__ = [
    "ediff1d", "in1d", "intersect1d", "isin", "setdiff1d", "setxor1d",
    "union1d", "unique", "unique_all", "unique_counts", "unique_inverse",
    "unique_values"
]


def _ediff1d_dispatcher(ary, to_end=None, to_begin=None):
    return (ary, to_end, to_begin)


@array_function_dispatch(_ediff1d_dispatcher)
def ediff1d(ary, to_end=None, to_begin=None):
    """
    The differences between consecutive elements of an array.

    Parameters
    ----------
    ary : array_like
        If necessary, will be flattened before the differences are taken.
    to_end : array_like, optional
        Number(s) to append at the end of the returned differences.
    to_begin : array_like, optional
        Number(s) to prepend at the beginning of the returned differences.

    Returns
    -------
    ediff1d : ndarray
        The differences. Loosely, this is ``ary.flat[1:] - ary.flat[:-1]``.

    See Also
    --------
    diff, gradient

    Notes
    -----
    When applied to masked arrays, this function drops the mask information
    if the `to_begin` and/or `to_end` parameters are used.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.array([1, 2, 4, 7, 0])
    >>> np.ediff1d(x)
    array([ 1,  2,  3, -7])

    >>> np.ediff1d(x, to_begin=-99, to_end=np.array([88, 99]))
    array([-99,   1,   2, ...,  -7,  88,  99])

    The returned array is always 1D.

    >>> y = [[1, 2, 4], [1, 6, 24]]
    >>> np.ediff1d(y)
    array([ 1,  2, -3,  5, 18])

    """
    conv = _array_converter(ary)
    # Convert to (any) array and ravel:
    ary = conv[0].ravel()

    # enforce that the dtype of `ary` is used for the output
    dtype_req = ary.dtype

    # fast track default case
    if to_begin is None and to_end is None:
        return ary[1:] - ary[:-1]

    if to_begin is None:
        l_begin = 0
    else:
        to_begin = np.asanyarray(to_begin)
        if not np.can_cast(to_begin, dtype_req, casting="same_kind"):
            raise TypeError("dtype of `to_begin` must be compatible "
                            "with input `ary` under the `same_kind` rule.")

        to_begin = to_begin.ravel()
        l_begin = len(to_begin)

    if to_end is None:
        l_end = 0
    else:
        to_end = np.asanyarray(to_end)
        if not np.can_cast(to_end, dtype_req, casting="same_kind"):
            raise TypeError("dtype of `to_end` must be compatible "
                            "with input `ary` under the `same_kind` rule.")

        to_end = to_end.ravel()
        l_end = len(to_end)

    # do the calculation in place and copy to_begin and to_end
    l_diff = max(len(ary) - 1, 0)
    result = np.empty_like(ary, shape=l_diff + l_begin + l_end)

    if l_begin > 0:
        result[:l_begin] = to_begin
    if l_end > 0:
        result[l_begin + l_diff:] = to_end
    np.subtract(ary[1:], ary[:-1], result[l_begin:l_begin + l_diff])

    return conv.wrap(result)


def _unpack_tuple(x):
    """ Unpacks one-element tuples for use as return values """
    if len(x) == 1:
        return x[0]
    else:
        return x


def _unique_dispatcher(ar, return_index=None, return_inverse=None,
                       return_counts=None, axis=None, *, equal_nan=None,
                       sorted=True):
    return (ar,)


@array_function_dispatch(_unique_dispatcher)
def unique(ar, return_index=False, return_inverse=False,
           return_counts=False, axis=None, *, equal_nan=True,
           sorted=True):
    """
    Find the unique elements of an array.

    Returns the sorted unique elements of an array. There are three optional
    outputs in addition to the unique elements:

    * the indices of the input array that give the unique values
    * the indices of the unique array that reconstruct the input array
    * the number of times each unique value comes up in the input array

    Parameters
    ----------
    ar : array_like
        Input array. Unless `axis` is specified, this will be flattened if it
        is not already 1-D.
    return_index : bool, optional
        If True, also return the indices of `ar` (along the specified axis,
        if provided, or in the flattened array) that result in the unique array.
    return_inverse : bool, optional
        If True, also return the indices of the unique array (for the specified
        axis, if provided) that can be used to reconstruct `ar`.
    return_counts : bool, optional
        If True, also return the number of times each unique item appears
        in `ar`.
    axis : int or None, optional
        The axis to operate on. If None, `ar` will be flattened. If an integer,
        the subarrays indexed by the given axis will be flattened and treated
        as the elements of a 1-D array with the dimension of the given axis,
        see the notes for more details.  Object arrays or structured arrays
        that contain objects are not supported if the `axis` kwarg is used. The
        default is None.

    equal_nan : bool, optional
        If True, collapses multiple NaN values in the return array into one.

        .. versionadded:: 1.24

    sorted : bool, optional
        If True, the unique elements are sorted. Elements may be sorted in
        practice even if ``sorted=False``, but this could change without
        notice.

        .. versionadded:: 2.3

    Returns
    -------
    unique : ndarray
        The sorted unique values.
    unique_indices : ndarray, optional
        The indices of the first occurrences of the unique values in the
        original array. Only provided if `return_index` is True.
    unique_inverse : ndarray, optional
        The indices to reconstruct the original array from the
        unique array. Only provided if `return_inverse` is True.
    unique_counts : ndarray, optional
        The number of times each of the unique values comes up in the
        original array. Only provided if `return_counts` is True.

    See Also
    --------
    repeat : Repeat elements of an array.
    sort : Return a sorted copy of an array.

    Notes
    -----
    When an axis is specified the subarrays indexed by the axis are sorted.
    This is done by making the specified axis the first dimension of the array
    (move the axis to the first dimension to keep the order of the other axes)
    and then flattening the subarrays in C order. The flattened subarrays are
    then viewed as a structured type with each element given a label, with the
    effect that we end up with a 1-D array of structured types that can be
    treated in the same way as any other 1-D array. The result is that the
    flattened subarrays are sorted in lexicographic order starting with the
    first element.

    .. versionchanged:: 1.21
        Like np.sort, NaN will sort to the end of the values.
        For complex arrays all NaN values are considered equivalent
        (no matter whether the NaN is in the real or imaginary part).
        As the representant for the returned array the smallest one in the
        lexicographical order is chosen - see np.sort for how the lexicographical
        order is defined for complex arrays.

    .. versionchanged:: 2.0
        For multi-dimensional inputs, ``unique_inverse`` is reshaped
        such that the input can be reconstructed using
        ``np.take(unique, unique_inverse, axis=axis)``. The result is
        now not 1-dimensional when ``axis=None``.

        Note that in NumPy 2.0.0 a higher dimensional array was returned also
        when ``axis`` was not ``None``.  This was reverted, but
        ``inverse.reshape(-1)`` can be used to ensure compatibility with both
        versions.

    Examples
    --------
    >>> import numpy as np
    >>> np.unique([1, 1, 2, 2, 3, 3])
    array([1, 2, 3])
    >>> a = np.array([[1, 1], [2, 3]])
    >>> np.unique(a)
    array([1, 2, 3])

    Return the unique rows of a 2D array

    >>> a = np.array([[1, 0, 0], [1, 0, 0], [2, 3, 4]])
    >>> np.unique(a, axis=0)
    array([[1, 0, 0], [2, 3, 4]])

    Return the indices of the original array that give the unique values:

    >>> a = np.array(['a', 'b', 'b', 'c', 'a'])
    >>> u, indices = np.unique(a, return_index=True)
    >>> u
    array(['a', 'b', 'c'], dtype='<U1')
    >>> indices
    array([0, 1, 3])
    >>> a[indices]
    array(['a', 'b', 'c'], dtype='<U1')

    Reconstruct the input array from the unique values and inverse:

    >>> a = np.array([1, 2, 6, 4, 2, 3, 2])
    >>> u, indices = np.unique(a, return_inverse=True)
    >>> u
    array([1, 2, 3, 4, 6])
    >>> indices
    array([0, 1, 4, 3, 1, 2, 1])
    >>> u[indices]
    array([1, 2, 6, 4, 2, 3, 2])

    Reconstruct the input values from the unique values and counts:

    >>> a = np.array([1, 2, 6, 4, 2, 3, 2])
    >>> values, counts = np.unique(a, return_counts=True)
    >>> values
    array([1, 2, 3, 4, 6])
    >>> counts
    array([1, 3, 1, 1, 1])
    >>> np.repeat(values, counts)
    array([1, 2, 2, 2, 3, 4, 6])    # original order not preserved

    """
    ar = np.asanyarray(ar)
    if axis is None:
        ret = _unique1d(ar, return_index, return_inverse, return_counts,
                        equal_nan=equal_nan, inverse_shape=ar.shape, axis=None,
                        sorted=sorted)
        return _unpack_tuple(ret)

    # axis was specified and not None
    try:
        ar = np.moveaxis(ar, axis, 0)
    except np.exceptions.AxisError:
        # this removes the "axis1" or "axis2" prefix from the error message
        raise np.exceptions.AxisError(axis, ar.ndim) from None
    inverse_shape = [1] * ar.ndim
    inverse_shape[axis] = ar.shape[0]

    # Must reshape to a contiguous 2D array for this to work...
    orig_shape, orig_dtype = ar.shape, ar.dtype
    ar = ar.reshape(orig_shape[0], np.prod(orig_shape[1:], dtype=np.intp))
    ar = np.ascontiguousarray(ar)
    dtype = [(f'f{i}', ar.dtype) for i in range(ar.shape[1])]

    # At this point, `ar` has shape `(n, m)`, and `dtype` is a structured
    # data type with `m` fields where each field has the data type of `ar`.
    # In the following, we create the array `consolidated`, which has
    # shape `(n,)` with data type `dtype`.
    try:
        if ar.shape[1] > 0:
            consolidated = ar.view(dtype)
        else:
            # If ar.shape[1] == 0, then dtype will be `np.dtype([])`, which is
            # a data type with itemsize 0, and the call `ar.view(dtype)` will
            # fail.  Instead, we'll use `np.empty` to explicitly create the
            # array with shape `(len(ar),)`.  Because `dtype` in this case has
            # itemsize 0, the total size of the result is still 0 bytes.
            consolidated = np.empty(len(ar), dtype=dtype)
    except TypeError as e:
        # There's no good way to do this for object arrays, etc...
        msg = 'The axis argument to unique is not supported for dtype {dt}'
        raise TypeError(msg.format(dt=ar.dtype)) from e

    def reshape_uniq(uniq):
        n = len(uniq)
        uniq = uniq.view(orig_dtype)
        uniq = uniq.reshape(n, *orig_shape[1:])
        uniq = np.moveaxis(uniq, 0, axis)
        return uniq

    output = _unique1d(consolidated, return_index,
                       return_inverse, return_counts,
                       equal_nan=equal_nan, inverse_shape=inverse_shape,
                       axis=axis, sorted=sorted)
    output = (reshape_uniq(output[0]),) + output[1:]
    return _unpack_tuple(output)


def _unique1d(ar, return_index=False, return_inverse=False,
              return_counts=False, *, equal_nan=True, inverse_shape=None,
              axis=None, sorted=True):
    """
    Find the unique elements of an array, ignoring shape.

    Uses a hash table to find the unique elements if possible.
    """
    ar = np.asanyarray(ar).flatten()
    if len(ar.shape) != 1:
        # np.matrix, and maybe some other array subclasses, insist on keeping
        # two dimensions for all operations. Coerce to an ndarray in such cases.
        ar = np.asarray(ar).flatten()

    optional_indices = return_index or return_inverse

    # masked arrays are not supported yet.
    if not optional_indices and not return_counts and not np.ma.is_masked(ar):
        # First we convert the array to a numpy array, later we wrap it back
        # in case it was a subclass of numpy.ndarray.
        conv = _array_converter(ar)
        ar_, = conv

        if (hash_unique := _unique_hash(ar_)) is not NotImplemented:
            if sorted:
                hash_unique.sort()
            # We wrap the result back in case it was a subclass of numpy.ndarray.
            return (conv.wrap(hash_unique),)

    # If we don't use the hash map, we use the slower sorting method.
    if optional_indices:
        perm = ar.argsort(kind='mergesort' if return_index else 'quicksort')
        aux = ar[perm]
    else:
        ar.sort()
        aux = ar
    mask = np.empty(aux.shape, dtype=np.bool)
    mask[:1] = True
    if (equal_nan and aux.shape[0] > 0 and aux.dtype.kind in "cfmM" and
            np.isnan(aux[-1])):
        if aux.dtype.kind == "c":  # for complex all NaNs are considered equivalent
            aux_firstnan = np.searchsorted(np.isnan(aux), True, side='left')
        else:
            aux_firstnan = np.searchsorted(aux, aux[-1], side='left')
        if aux_firstnan > 0:
            mask[1:aux_firstnan] = (
                aux[1:aux_firstnan] != aux[:aux_firstnan - 1])
        mask[aux_firstnan] = True
        mask[aux_firstnan + 1:] = False
    else:
        mask[1:] = aux[1:] != aux[:-1]

    ret = (aux[mask],)
    if return_index:
        ret += (perm[mask],)
    if return_inverse:
        imask = np.cumsum(mask) - 1
        inv_idx = np.empty(mask.shape, dtype=np.intp)
        inv_idx[perm] = imask
        ret += (inv_idx.reshape(inverse_shape) if axis is None else inv_idx,)
    if return_counts:
        idx = np.concatenate(np.nonzero(mask) + ([mask.size],))
        ret += (np.diff(idx),)
    return ret


# Array API set functions

class UniqueAllResult(NamedTuple):
    values: np.ndarray
    indices: np.ndarray
    inverse_indices: np.ndarray
    counts: np.ndarray


class UniqueCountsResult(NamedTuple):
    values: np.ndarray
    counts: np.ndarray


class UniqueInverseResult(NamedTuple):
    values: np.ndarray
    inverse_indices: np.ndarray


def _unique_all_dispatcher(x, /):
    return (x,)


@array_function_dispatch(_unique_all_dispatcher)
def unique_all(x):
    """
    Find the unique elements of an array, and counts, inverse, and indices.

    This function is an Array API compatible alternative to::

        np.unique(x, return_index=True, return_inverse=True,
                  return_counts=True, equal_nan=False, sorted=False)

    but returns a namedtuple for easier access to each output.

    .. note::
        This function currently always returns a sorted result, however,
        this could change in any NumPy minor release.

    Parameters
    ----------
    x : array_like
        Input array. It will be flattened if it is not already 1-D.

    Returns
    -------
    out : namedtuple
        The result containing:

        * values - The unique elements of an input array.
        * indices - The first occurring indices for each unique element.
        * inverse_indices - The indices from the set of unique elements
          that reconstruct `x`.
        * counts - The corresponding counts for each unique element.

    See Also
    --------
    unique : Find the unique elements of an array.

    Examples
    --------
    >>> import numpy as np
    >>> x = [1, 1, 2]
    >>> uniq = np.unique_all(x)
    >>> uniq.values
    array([1, 2])
    >>> uniq.indices
    array([0, 2])
    >>> uniq.inverse_indices
    array([0, 0, 1])
    >>> uniq.counts
    array([2, 1])
    """
    result = unique(
        x,
        return_index=True,
        return_inverse=True,
        return_counts=True,
        equal_nan=False,
    )
    return UniqueAllResult(*result)


def _unique_counts_dispatcher(x, /):
    return (x,)


@array_function_dispatch(_unique_counts_dispatcher)
def unique_counts(x):
    """
    Find the unique elements and counts of an input array `x`.

    This function is an Array API compatible alternative to::

        np.unique(x, return_counts=True, equal_nan=False, sorted=False)

    but returns a namedtuple for easier access to each output.

    .. note::
        This function currently always returns a sorted result, however,
        this could change in any NumPy minor release.

    Parameters
    ----------
    x : array_like
        Input array. It will be flattened if it is not already 1-D.

    Returns
    -------
    out : namedtuple
        The result containing:

        * values - The unique elements of an input array.
        * counts - The corresponding counts for each unique element.

    See Also
    --------
    unique : Find the unique elements of an array.

    Examples
    --------
    >>> import numpy as np
    >>> x = [1, 1, 2]
    >>> uniq = np.unique_counts(x)
    >>> uniq.values
    array([1, 2])
    >>> uniq.counts
    array([2, 1])
    """
    result = unique(
        x,
        return_index=False,
        return_inverse=False,
        return_counts=True,
        equal_nan=False,
    )
    return UniqueCountsResult(*result)


def _unique_inverse_dispatcher(x, /):
    return (x,)


@array_function_dispatch(_unique_inverse_dispatcher)
def unique_inverse(x):
    """
    Find the unique elements of `x` and indices to reconstruct `x`.

    This function is an Array API compatible alternative to::

        np.unique(x, return_inverse=True, equal_nan=False, sorted=False)

    but returns a namedtuple for easier access to each output.

    .. note::
        This function currently always returns a sorted result, however,
        this could change in any NumPy minor release.

    Parameters
    ----------
    x : array_like
        Input array. It will be flattened if it is not already 1-D.

    Returns
    -------
    out : namedtuple
        The result containing:

        * values - The unique elements of an input array.
        * inverse_indices - The indices from the set of unique elements
          that reconstruct `x`.

    See Also
    --------
    unique : Find the unique elements of an array.

    Examples
    --------
    >>> import numpy as np
    >>> x = [1, 1, 2]
    >>> uniq = np.unique_inverse(x)
    >>> uniq.values
    array([1, 2])
    >>> uniq.inverse_indices
    array([0, 0, 1])
    """
    result = unique(
        x,
        return_index=False,
        return_inverse=True,
        return_counts=False,
        equal_nan=False,
    )
    return UniqueInverseResult(*result)


def _unique_values_dispatcher(x, /):
    return (x,)


@array_function_dispatch(_unique_values_dispatcher)
def unique_values(x):
    """
    Returns the unique elements of an input array `x`.

    This function is an Array API compatible alternative to::

        np.unique(x, equal_nan=False, sorted=False)

    .. versionchanged:: 2.3
       The algorithm was changed to a faster one that does not rely on
       sorting, and hence the results are no longer implicitly sorted.

    Parameters
    ----------
    x : array_like
        Input array. It will be flattened if it is not already 1-D.

    Returns
    -------
    out : ndarray
        The unique elements of an input array.

    See Also
    --------
    unique : Find the unique elements of an array.

    Examples
    --------
    >>> import numpy as np
    >>> np.unique_values([1, 1, 2])
    array([1, 2])  # may vary

    """
    return unique(
        x,
        return_index=False,
        return_inverse=False,
        return_counts=False,
        equal_nan=False,
        sorted=False,
    )


def _intersect1d_dispatcher(
        ar1, ar2, assume_unique=None, return_indices=None):
    return (ar1, ar2)


@array_function_dispatch(_intersect1d_dispatcher)
def intersect1d(ar1, ar2, assume_unique=False, return_indices=False):
    """
    Find the intersection of two arrays.

    Return the sorted, unique values that are in both of the input arrays.

    Parameters
    ----------
    ar1, ar2 : array_like
        Input arrays. Will be flattened if not already 1D.
    assume_unique : bool
        If True, the input arrays are both assumed to be unique, which
        can speed up the calculation.  If True but ``ar1`` or ``ar2`` are not
        unique, incorrect results and out-of-bounds indices could result.
        Default is False.
    return_indices : bool
        If True, the indices which correspond to the intersection of the two
        arrays are returned. The first instance of a value is used if there are
        multiple. Default is False.

    Returns
    -------
    intersect1d : ndarray
        Sorted 1D array of common and unique elements.
    comm1 : ndarray
        The indices of the first occurrences of the common values in `ar1`.
        Only provided if `return_indices` is True.
    comm2 : ndarray
        The indices of the first occurrences of the common values in `ar2`.
        Only provided if `return_indices` is True.

    Examples
    --------
    >>> import numpy as np
    >>> np.intersect1d([1, 3, 4, 3], [3, 1, 2, 1])
    array([1, 3])

    To intersect more than two arrays, use functools.reduce:

    >>> from functools import reduce
    >>> reduce(np.intersect1d, ([1, 3, 4, 3], [3, 1, 2, 1], [6, 3, 4, 2]))
    array([3])

    To return the indices of the values common to the input arrays
    along with the intersected values:

    >>> x = np.array([1, 1, 2, 3, 4])
    >>> y = np.array([2, 1, 4, 6])
    >>> xy, x_ind, y_ind = np.intersect1d(x, y, return_indices=True)
    >>> x_ind, y_ind
    (array([0, 2, 4]), array([1, 0, 2]))
    >>> xy, x[x_ind], y[y_ind]
    (array([1, 2, 4]), array([1, 2, 4]), array([1, 2, 4]))

    """
    ar1 = np.asanyarray(ar1)
    ar2 = np.asanyarray(ar2)

    if not assume_unique:
        if return_indices:
            ar1, ind1 = unique(ar1, return_index=True)
            ar2, ind2 = unique(ar2, return_index=True)
        else:
            ar1 = unique(ar1)
            ar2 = unique(ar2)
    else:
        ar1 = ar1.ravel()
        ar2 = ar2.ravel()

    aux = np.concatenate((ar1, ar2))
    if return_indices:
        aux_sort_indices = np.argsort(aux, kind='mergesort')
        aux = aux[aux_sort_indices]
    else:
        aux.sort()

    mask = aux[1:] == aux[:-1]
    int1d = aux[:-1][mask]

    if return_indices:
        ar1_indices = aux_sort_indices[:-1][mask]
        ar2_indices = aux_sort_indices[1:][mask] - ar1.size
        if not assume_unique:
            ar1_indices = ind1[ar1_indices]
            ar2_indices = ind2[ar2_indices]

        return int1d, ar1_indices, ar2_indices
    else:
        return int1d


def _setxor1d_dispatcher(ar1, ar2, assume_unique=None):
    return (ar1, ar2)


@array_function_dispatch(_setxor1d_dispatcher)
def setxor1d(ar1, ar2, assume_unique=False):
    """
    Find the set exclusive-or of two arrays.

    Return the sorted, unique values that are in only one (not both) of the
    input arrays.

    Parameters
    ----------
    ar1, ar2 : array_like
        Input arrays.
    assume_unique : bool
        If True, the input arrays are both assumed to be unique, which
        can speed up the calculation. Default is False.

    Returns
    -------
    setxor1d : ndarray
        Sorted 1D array of unique values that are in only one of the input
        arrays.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([1, 2, 3, 2, 4])
    >>> b = np.array([2, 3, 5, 7, 5])
    >>> np.setxor1d(a,b)
    array([1, 4, 5, 7])

    """
    if not assume_unique:
        ar1 = unique(ar1)
        ar2 = unique(ar2)

    aux = np.concatenate((ar1, ar2), axis=None)
    if aux.size == 0:
        return aux

    aux.sort()
    flag = np.concatenate(([True], aux[1:] != aux[:-1], [True]))
    return aux[flag[1:] & flag[:-1]]


def _in1d_dispatcher(ar1, ar2, assume_unique=None, invert=None, *,
                     kind=None):
    return (ar1, ar2)


@array_function_dispatch(_in1d_dispatcher)
def in1d(ar1, ar2, assume_unique=False, invert=False, *, kind=None):
    """
    Test whether each element of a 1-D array is also present in a second array.

    .. deprecated:: 2.0
        Use :func:`isin` instead of `in1d` for new code.

    Returns a boolean array the same length as `ar1` that is True
    where an element of `ar1` is in `ar2` and False otherwise.

    Parameters
    ----------
    ar1 : (M,) array_like
        Input array.
    ar2 : array_like
        The values against which to test each value of `ar1`.
    assume_unique : bool, optional
        If True, the input arrays are both assumed to be unique, which
        can speed up the calculation.  Default is False.
    invert : bool, optional
        If True, the values in the returned array are inverted (that is,
        False where an element of `ar1` is in `ar2` and True otherwise).
        Default is False. ``np.in1d(a, b, invert=True)`` is equivalent
        to (but is faster than) ``np.invert(in1d(a, b))``.
    kind : {None, 'sort', 'table'}, optional
        The algorithm to use. This will not affect the final result,
        but will affect the speed and memory use. The default, None,
        will select automatically based on memory considerations.

        * If 'sort', will use a mergesort-based approach. This will have
          a memory usage of roughly 6 times the sum of the sizes of
          `ar1` and `ar2`, not accounting for size of dtypes.
        * If 'table', will use a lookup table approach similar
          to a counting sort. This is only available for boolean and
          integer arrays. This will have a memory usage of the
          size of `ar1` plus the max-min value of `ar2`. `assume_unique`
          has no effect when the 'table' option is used.
        * If None, will automatically choose 'table' if
          the required memory allocation is less than or equal to
          6 times the sum of the sizes of `ar1` and `ar2`,
          otherwise will use 'sort'. This is done to not use
          a large amount of memory by default, even though
          'table' may be faster in most cases. If 'table' is chosen,
          `assume_unique` will have no effect.

    Returns
    -------
    in1d : (M,) ndarray, bool
        The values `ar1[in1d]` are in `ar2`.

    See Also
    --------
    isin                  : Version of this function that preserves the
                            shape of ar1.

    Notes
    -----
    `in1d` can be considered as an element-wise function version of the
    python keyword `in`, for 1-D sequences. ``in1d(a, b)`` is roughly
    equivalent to ``np.array([item in b for item in a])``.
    However, this idea fails if `ar2` is a set, or similar (non-sequence)
    container:  As ``ar2`` is converted to an array, in those cases
    ``asarray(ar2)`` is an object array rather than the expected array of
    contained values.

    Using ``kind='table'`` tends to be faster than `kind='sort'` if the
    following relationship is true:
    ``log10(len(ar2)) > (log10(max(ar2)-min(ar2)) - 2.27) / 0.927``,
    but may use greater memory. The default value for `kind` will
    be automatically selected based only on memory usage, so one may
    manually set ``kind='table'`` if memory constraints can be relaxed.

    Examples
    --------
    >>> import numpy as np
    >>> test = np.array([0, 1, 2, 5, 0])
    >>> states = [0, 2]
    >>> mask = np.in1d(test, states)
    >>> mask
    array([ True, False,  True, False,  True])
    >>> test[mask]
    array([0, 2, 0])
    >>> mask = np.in1d(test, states, invert=True)
    >>> mask
    array([False,  True, False,  True, False])
    >>> test[mask]
    array([1, 5])
    """

    # Deprecated in NumPy 2.0, 2023-08-18
    warnings.warn(
        "`in1d` is deprecated. Use `np.isin` instead.",
        DeprecationWarning,
        stacklevel=2
    )

    return _in1d(ar1, ar2, assume_unique, invert, kind=kind)


def _in1d(ar1, ar2, assume_unique=False, invert=False, *, kind=None):
    # Ravel both arrays, behavior for the first array could be different
    ar1 = np.asarray(ar1).ravel()
    ar2 = np.asarray(ar2).ravel()

    # Ensure that iteration through object arrays yields size-1 arrays
    if ar2.dtype == object:
        ar2 = ar2.reshape(-1, 1)

    if kind not in {None, 'sort', 'table'}:
        raise ValueError(
            f"Invalid kind: '{kind}'. Please use None, 'sort' or 'table'.")

    # Can use the table method if all arrays are integers or boolean:
    is_int_arrays = all(ar.dtype.kind in ("u", "i", "b") for ar in (ar1, ar2))
    use_table_method = is_int_arrays and kind in {None, 'table'}

    if use_table_method:
        if ar2.size == 0:
            if invert:
                return np.ones_like(ar1, dtype=bool)
            else:
                return np.zeros_like(ar1, dtype=bool)

        # Convert booleans to uint8 so we can use the fast integer algorithm
        if ar1.dtype == bool:
            ar1 = ar1.astype(np.uint8)
        if ar2.dtype == bool:
            ar2 = ar2.astype(np.uint8)

        ar2_min = int(np.min(ar2))
        ar2_max = int(np.max(ar2))

        ar2_range = ar2_max - ar2_min

        # Constraints on whether we can actually use the table method:
        #  1. Assert memory usage is not too large
        below_memory_constraint = ar2_range <= 6 * (ar1.size + ar2.size)
        #  2. Check overflows for (ar2 - ar2_min); dtype=ar2.dtype
        range_safe_from_overflow = ar2_range <= np.iinfo(ar2.dtype).max

        # Optimal performance is for approximately
        # log10(size) > (log10(range) - 2.27) / 0.927.
        # However, here we set the requirement that by default
        # the intermediate array can only be 6x
        # the combined memory allocation of the original
        # arrays. See discussion on
        # https://github.com/numpy/numpy/pull/12065.

        if (
            range_safe_from_overflow and
            (below_memory_constraint or kind == 'table')
        ):

            if invert:
                outgoing_array = np.ones_like(ar1, dtype=bool)
            else:
                outgoing_array = np.zeros_like(ar1, dtype=bool)

            # Make elements 1 where the integer exists in ar2
            if invert:
                isin_helper_ar = np.ones(ar2_range + 1, dtype=bool)
                isin_helper_ar[ar2 - ar2_min] = 0
            else:
                isin_helper_ar = np.zeros(ar2_range + 1, dtype=bool)
                isin_helper_ar[ar2 - ar2_min] = 1

            # Mask out elements we know won't work
            basic_mask = (ar1 <= ar2_max) & (ar1 >= ar2_min)
            in_range_ar1 = ar1[basic_mask]
            if in_range_ar1.size == 0:
                # Nothing more to do, since all values are out of range.
                return outgoing_array

            # Unfortunately, ar2_min can be out of range for `intp` even
            # if the calculation result must fit in range (and be positive).
            # In that case, use ar2.dtype which must work for all unmasked
            # values.
            try:
                ar2_min = np.array(ar2_min, dtype=np.intp)
                dtype = np.intp
            except OverflowError:
                dtype = ar2.dtype

            out = np.empty_like(in_range_ar1, dtype=np.intp)
            outgoing_array[basic_mask] = isin_helper_ar[
                    np.subtract(in_range_ar1, ar2_min, dtype=dtype,
                                out=out, casting="unsafe")]

            return outgoing_array
        elif kind == 'table':  # not range_safe_from_overflow
            raise RuntimeError(
                "You have specified kind='table', "
                "but the range of values in `ar2` or `ar1` exceed the "
                "maximum integer of the datatype. "
                "Please set `kind` to None or 'sort'."
            )
    elif kind == 'table':
        raise ValueError(
            "The 'table' method is only "
            "supported for boolean or integer arrays. "
            "Please select 'sort' or None for kind."
        )

    # Check if one of the arrays may contain arbitrary objects
    contains_object = ar1.dtype.hasobject or ar2.dtype.hasobject

    # This code is run when
    # a) the first condition is true, making the code significantly faster
    # b) the second condition is true (i.e. `ar1` or `ar2` may contain
    #    arbitrary objects), since then sorting is not guaranteed to work
    if len(ar2) < 10 * len(ar1) ** 0.145 or contains_object:
        if invert:
            mask = np.ones(len(ar1), dtype=bool)
            for a in ar2:
                mask &= (ar1 != a)
        else:
            mask = np.zeros(len(ar1), dtype=bool)
            for a in ar2:
                mask |= (ar1 == a)
        return mask

    # Otherwise use sorting
    if not assume_unique:
        ar1, rev_idx = np.unique(ar1, return_inverse=True)
        ar2 = np.unique(ar2)

    ar = np.concatenate((ar1, ar2))
    # We need this to be a stable sort, so always use 'mergesort'
    # here. The values from the first array should always come before
    # the values from the second array.
    order = ar.argsort(kind='mergesort')
    sar = ar[order]
    if invert:
        bool_ar = (sar[1:] != sar[:-1])
    else:
        bool_ar = (sar[1:] == sar[:-1])
    flag = np.concatenate((bool_ar, [invert]))
    ret = np.empty(ar.shape, dtype=bool)
    ret[order] = flag

    if assume_unique:
        return ret[:len(ar1)]
    else:
        return ret[rev_idx]


def _isin_dispatcher(element, test_elements, assume_unique=None, invert=None,
                     *, kind=None):
    return (element, test_elements)


@array_function_dispatch(_isin_dispatcher)
def isin(element, test_elements, assume_unique=False, invert=False, *,
         kind=None):
    """
    Calculates ``element in test_elements``, broadcasting over `element` only.
    Returns a boolean array of the same shape as `element` that is True
    where an element of `element` is in `test_elements` and False otherwise.

    Parameters
    ----------
    element : array_like
        Input array.
    test_elements : array_like
        The values against which to test each value of `element`.
        This argument is flattened if it is an array or array_like.
        See notes for behavior with non-array-like parameters.
    assume_unique : bool, optional
        If True, the input arrays are both assumed to be unique, which
        can speed up the calculation.  Default is False.
    invert : bool, optional
        If True, the values in the returned array are inverted, as if
        calculating `element not in test_elements`. Default is False.
        ``np.isin(a, b, invert=True)`` is equivalent to (but faster
        than) ``np.invert(np.isin(a, b))``.
    kind : {None, 'sort', 'table'}, optional
        The algorithm to use. This will not affect the final result,
        but will affect the speed and memory use. The default, None,
        will select automatically based on memory considerations.

        * If 'sort', will use a mergesort-based approach. This will have
          a memory usage of roughly 6 times the sum of the sizes of
          `element` and `test_elements`, not accounting for size of dtypes.
        * If 'table', will use a lookup table approach similar
          to a counting sort. This is only available for boolean and
          integer arrays. This will have a memory usage of the
          size of `element` plus the max-min value of `test_elements`.
          `assume_unique` has no effect when the 'table' option is used.
        * If None, will automatically choose 'table' if
          the required memory allocation is less than or equal to
          6 times the sum of the sizes of `element` and `test_elements`,
          otherwise will use 'sort'. This is done to not use
          a large amount of memory by default, even though
          'table' may be faster in most cases. If 'table' is chosen,
          `assume_unique` will have no effect.


    Returns
    -------
    isin : ndarray, bool
        Has the same shape as `element`. The values `element[isin]`
        are in `test_elements`.

    Notes
    -----
    `isin` is an element-wise function version of the python keyword `in`.
    ``isin(a, b)`` is roughly equivalent to
    ``np.array([item in b for item in a])`` if `a` and `b` are 1-D sequences.

    `element` and `test_elements` are converted to arrays if they are not
    already. If `test_elements` is a set (or other non-sequence collection)
    it will be converted to an object array with one element, rather than an
    array of the values contained in `test_elements`. This is a consequence
    of the `array` constructor's way of handling non-sequence collections.
    Converting the set to a list usually gives the desired behavior.

    Using ``kind='table'`` tends to be faster than `kind='sort'` if the
    following relationship is true:
    ``log10(len(test_elements)) >
    (log10(max(test_elements)-min(test_elements)) - 2.27) / 0.927``,
    but may use greater memory. The default value for `kind` will
    be automatically selected based only on memory usage, so one may
    manually set ``kind='table'`` if memory constraints can be relaxed.

    Examples
    --------
    >>> import numpy as np
    >>> element = 2*np.arange(4).reshape((2, 2))
    >>> element
    array([[0, 2],
           [4, 6]])
    >>> test_elements = [1, 2, 4, 8]
    >>> mask = np.isin(element, test_elements)
    >>> mask
    array([[False,  True],
           [ True, False]])
    >>> element[mask]
    array([2, 4])

    The indices of the matched values can be obtained with `nonzero`:

    >>> np.nonzero(mask)
    (array([0, 1]), array([1, 0]))

    The test can also be inverted:

    >>> mask = np.isin(element, test_elements, invert=True)
    >>> mask
    array([[ True, False],
           [False,  True]])
    >>> element[mask]
    array([0, 6])

    Because of how `array` handles sets, the following does not
    work as expected:

    >>> test_set = {1, 2, 4, 8}
    >>> np.isin(element, test_set)
    array([[False, False],
           [False, False]])

    Casting the set to a list gives the expected result:

    >>> np.isin(element, list(test_set))
    array([[False,  True],
           [ True, False]])
    """
    element = np.asarray(element)
    return _in1d(element, test_elements, assume_unique=assume_unique,
                 invert=invert, kind=kind).reshape(element.shape)


def _union1d_dispatcher(ar1, ar2):
    return (ar1, ar2)


@array_function_dispatch(_union1d_dispatcher)
def union1d(ar1, ar2):
    """
    Find the union of two arrays.

    Return the unique, sorted array of values that are in either of the two
    input arrays.

    Parameters
    ----------
    ar1, ar2 : array_like
        Input arrays. They are flattened if they are not already 1D.

    Returns
    -------
    union1d : ndarray
        Unique, sorted union of the input arrays.

    Examples
    --------
    >>> import numpy as np
    >>> np.union1d([-1, 0, 1], [-2, 0, 2])
    array([-2, -1,  0,  1,  2])

    To find the union of more than two arrays, use functools.reduce:

    >>> from functools import reduce
    >>> reduce(np.union1d, ([1, 3, 4, 3], [3, 1, 2, 1], [6, 3, 4, 2]))
    array([1, 2, 3, 4, 6])
    """
    return unique(np.concatenate((ar1, ar2), axis=None))


def _setdiff1d_dispatcher(ar1, ar2, assume_unique=None):
    return (ar1, ar2)


@array_function_dispatch(_setdiff1d_dispatcher)
def setdiff1d(ar1, ar2, assume_unique=False):
    """
    Find the set difference of two arrays.

    Return the unique values in `ar1` that are not in `ar2`.

    Parameters
    ----------
    ar1 : array_like
        Input array.
    ar2 : array_like
        Input comparison array.
    assume_unique : bool
        If True, the input arrays are both assumed to be unique, which
        can speed up the calculation.  Default is False.

    Returns
    -------
    setdiff1d : ndarray
        1D array of values in `ar1` that are not in `ar2`. The result
        is sorted when `assume_unique=False`, but otherwise only sorted
        if the input is sorted.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([1, 2, 3, 2, 4, 1])
    >>> b = np.array([3, 4, 5, 6])
    >>> np.setdiff1d(a, b)
    array([1, 2])

    """
    if assume_unique:
        ar1 = np.asarray(ar1).ravel()
    else:
        ar1 = unique(ar1)
        ar2 = unique(ar2)
    return ar1[_in1d(ar1, ar2, assume_unique=True, invert=True)]

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\_arraysetops_impl.py ===
"""
Set operations for arrays based on sorting.

Notes
-----

For floating point arrays, inaccurate results may appear due to usual round-off
and floating point comparison issues.

Speed could be gained in some operations by an implementation of
`numpy.sort`, that can provide directly the permutation vectors, thus avoiding
calls to `numpy.argsort`.

Original author: Robert Cimrman

"""
import functools
import warnings
from typing import NamedTuple

import numpy as np
from numpy._core import overrides
from numpy._core._multiarray_umath import _array_converter, _unique_hash

array_function_dispatch = functools.partial(
    overrides.array_function_dispatch, module='numpy')


__all__ = [
    "ediff1d", "in1d", "intersect1d", "isin", "setdiff1d", "setxor1d",
    "union1d", "unique", "unique_all", "unique_counts", "unique_inverse",
    "unique_values"
]


def _ediff1d_dispatcher(ary, to_end=None, to_begin=None):
    return (ary, to_end, to_begin)


@array_function_dispatch(_ediff1d_dispatcher)
def ediff1d(ary, to_end=None, to_begin=None):
    """
    The differences between consecutive elements of an array.

    Parameters
    ----------
    ary : array_like
        If necessary, will be flattened before the differences are taken.
    to_end : array_like, optional
        Number(s) to append at the end of the returned differences.
    to_begin : array_like, optional
        Number(s) to prepend at the beginning of the returned differences.

    Returns
    -------
    ediff1d : ndarray
        The differences. Loosely, this is ``ary.flat[1:] - ary.flat[:-1]``.

    See Also
    --------
    diff, gradient

    Notes
    -----
    When applied to masked arrays, this function drops the mask information
    if the `to_begin` and/or `to_end` parameters are used.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.array([1, 2, 4, 7, 0])
    >>> np.ediff1d(x)
    array([ 1,  2,  3, -7])

    >>> np.ediff1d(x, to_begin=-99, to_end=np.array([88, 99]))
    array([-99,   1,   2, ...,  -7,  88,  99])

    The returned array is always 1D.

    >>> y = [[1, 2, 4], [1, 6, 24]]
    >>> np.ediff1d(y)
    array([ 1,  2, -3,  5, 18])

    """
    conv = _array_converter(ary)
    # Convert to (any) array and ravel:
    ary = conv[0].ravel()

    # enforce that the dtype of `ary` is used for the output
    dtype_req = ary.dtype

    # fast track default case
    if to_begin is None and to_end is None:
        return ary[1:] - ary[:-1]

    if to_begin is None:
        l_begin = 0
    else:
        to_begin = np.asanyarray(to_begin)
        if not np.can_cast(to_begin, dtype_req, casting="same_kind"):
            raise TypeError("dtype of `to_begin` must be compatible "
                            "with input `ary` under the `same_kind` rule.")

        to_begin = to_begin.ravel()
        l_begin = len(to_begin)

    if to_end is None:
        l_end = 0
    else:
        to_end = np.asanyarray(to_end)
        if not np.can_cast(to_end, dtype_req, casting="same_kind"):
            raise TypeError("dtype of `to_end` must be compatible "
                            "with input `ary` under the `same_kind` rule.")

        to_end = to_end.ravel()
        l_end = len(to_end)

    # do the calculation in place and copy to_begin and to_end
    l_diff = max(len(ary) - 1, 0)
    result = np.empty_like(ary, shape=l_diff + l_begin + l_end)

    if l_begin > 0:
        result[:l_begin] = to_begin
    if l_end > 0:
        result[l_begin + l_diff:] = to_end
    np.subtract(ary[1:], ary[:-1], result[l_begin:l_begin + l_diff])

    return conv.wrap(result)


def _unpack_tuple(x):
    """ Unpacks one-element tuples for use as return values """
    if len(x) == 1:
        return x[0]
    else:
        return x


def _unique_dispatcher(ar, return_index=None, return_inverse=None,
                       return_counts=None, axis=None, *, equal_nan=None,
                       sorted=True):
    return (ar,)


@array_function_dispatch(_unique_dispatcher)
def unique(ar, return_index=False, return_inverse=False,
           return_counts=False, axis=None, *, equal_nan=True,
           sorted=True):
    """
    Find the unique elements of an array.

    Returns the sorted unique elements of an array. There are three optional
    outputs in addition to the unique elements:

    * the indices of the input array that give the unique values
    * the indices of the unique array that reconstruct the input array
    * the number of times each unique value comes up in the input array

    Parameters
    ----------
    ar : array_like
        Input array. Unless `axis` is specified, this will be flattened if it
        is not already 1-D.
    return_index : bool, optional
        If True, also return the indices of `ar` (along the specified axis,
        if provided, or in the flattened array) that result in the unique array.
    return_inverse : bool, optional
        If True, also return the indices of the unique array (for the specified
        axis, if provided) that can be used to reconstruct `ar`.
    return_counts : bool, optional
        If True, also return the number of times each unique item appears
        in `ar`.
    axis : int or None, optional
        The axis to operate on. If None, `ar` will be flattened. If an integer,
        the subarrays indexed by the given axis will be flattened and treated
        as the elements of a 1-D array with the dimension of the given axis,
        see the notes for more details.  Object arrays or structured arrays
        that contain objects are not supported if the `axis` kwarg is used. The
        default is None.

    equal_nan : bool, optional
        If True, collapses multiple NaN values in the return array into one.

        .. versionadded:: 1.24

    sorted : bool, optional
        If True, the unique elements are sorted. Elements may be sorted in
        practice even if ``sorted=False``, but this could change without
        notice.

        .. versionadded:: 2.3

    Returns
    -------
    unique : ndarray
        The sorted unique values.
    unique_indices : ndarray, optional
        The indices of the first occurrences of the unique values in the
        original array. Only provided if `return_index` is True.
    unique_inverse : ndarray, optional
        The indices to reconstruct the original array from the
        unique array. Only provided if `return_inverse` is True.
    unique_counts : ndarray, optional
        The number of times each of the unique values comes up in the
        original array. Only provided if `return_counts` is True.

    See Also
    --------
    repeat : Repeat elements of an array.
    sort : Return a sorted copy of an array.

    Notes
    -----
    When an axis is specified the subarrays indexed by the axis are sorted.
    This is done by making the specified axis the first dimension of the array
    (move the axis to the first dimension to keep the order of the other axes)
    and then flattening the subarrays in C order. The flattened subarrays are
    then viewed as a structured type with each element given a label, with the
    effect that we end up with a 1-D array of structured types that can be
    treated in the same way as any other 1-D array. The result is that the
    flattened subarrays are sorted in lexicographic order starting with the
    first element.

    .. versionchanged:: 1.21
        Like np.sort, NaN will sort to the end of the values.
        For complex arrays all NaN values are considered equivalent
        (no matter whether the NaN is in the real or imaginary part).
        As the representant for the returned array the smallest one in the
        lexicographical order is chosen - see np.sort for how the lexicographical
        order is defined for complex arrays.

    .. versionchanged:: 2.0
        For multi-dimensional inputs, ``unique_inverse`` is reshaped
        such that the input can be reconstructed using
        ``np.take(unique, unique_inverse, axis=axis)``. The result is
        now not 1-dimensional when ``axis=None``.

        Note that in NumPy 2.0.0 a higher dimensional array was returned also
        when ``axis`` was not ``None``.  This was reverted, but
        ``inverse.reshape(-1)`` can be used to ensure compatibility with both
        versions.

    Examples
    --------
    >>> import numpy as np
    >>> np.unique([1, 1, 2, 2, 3, 3])
    array([1, 2, 3])
    >>> a = np.array([[1, 1], [2, 3]])
    >>> np.unique(a)
    array([1, 2, 3])

    Return the unique rows of a 2D array

    >>> a = np.array([[1, 0, 0], [1, 0, 0], [2, 3, 4]])
    >>> np.unique(a, axis=0)
    array([[1, 0, 0], [2, 3, 4]])

    Return the indices of the original array that give the unique values:

    >>> a = np.array(['a', 'b', 'b', 'c', 'a'])
    >>> u, indices = np.unique(a, return_index=True)
    >>> u
    array(['a', 'b', 'c'], dtype='<U1')
    >>> indices
    array([0, 1, 3])
    >>> a[indices]
    array(['a', 'b', 'c'], dtype='<U1')

    Reconstruct the input array from the unique values and inverse:

    >>> a = np.array([1, 2, 6, 4, 2, 3, 2])
    >>> u, indices = np.unique(a, return_inverse=True)
    >>> u
    array([1, 2, 3, 4, 6])
    >>> indices
    array([0, 1, 4, 3, 1, 2, 1])
    >>> u[indices]
    array([1, 2, 6, 4, 2, 3, 2])

    Reconstruct the input values from the unique values and counts:

    >>> a = np.array([1, 2, 6, 4, 2, 3, 2])
    >>> values, counts = np.unique(a, return_counts=True)
    >>> values
    array([1, 2, 3, 4, 6])
    >>> counts
    array([1, 3, 1, 1, 1])
    >>> np.repeat(values, counts)
    array([1, 2, 2, 2, 3, 4, 6])    # original order not preserved

    """
    ar = np.asanyarray(ar)
    if axis is None:
        ret = _unique1d(ar, return_index, return_inverse, return_counts,
                        equal_nan=equal_nan, inverse_shape=ar.shape, axis=None,
                        sorted=sorted)
        return _unpack_tuple(ret)

    # axis was specified and not None
    try:
        ar = np.moveaxis(ar, axis, 0)
    except np.exceptions.AxisError:
        # this removes the "axis1" or "axis2" prefix from the error message
        raise np.exceptions.AxisError(axis, ar.ndim) from None
    inverse_shape = [1] * ar.ndim
    inverse_shape[axis] = ar.shape[0]

    # Must reshape to a contiguous 2D array for this to work...
    orig_shape, orig_dtype = ar.shape, ar.dtype
    ar = ar.reshape(orig_shape[0], np.prod(orig_shape[1:], dtype=np.intp))
    ar = np.ascontiguousarray(ar)
    dtype = [(f'f{i}', ar.dtype) for i in range(ar.shape[1])]

    # At this point, `ar` has shape `(n, m)`, and `dtype` is a structured
    # data type with `m` fields where each field has the data type of `ar`.
    # In the following, we create the array `consolidated`, which has
    # shape `(n,)` with data type `dtype`.
    try:
        if ar.shape[1] > 0:
            consolidated = ar.view(dtype)
        else:
            # If ar.shape[1] == 0, then dtype will be `np.dtype([])`, which is
            # a data type with itemsize 0, and the call `ar.view(dtype)` will
            # fail.  Instead, we'll use `np.empty` to explicitly create the
            # array with shape `(len(ar),)`.  Because `dtype` in this case has
            # itemsize 0, the total size of the result is still 0 bytes.
            consolidated = np.empty(len(ar), dtype=dtype)
    except TypeError as e:
        # There's no good way to do this for object arrays, etc...
        msg = 'The axis argument to unique is not supported for dtype {dt}'
        raise TypeError(msg.format(dt=ar.dtype)) from e

    def reshape_uniq(uniq):
        n = len(uniq)
        uniq = uniq.view(orig_dtype)
        uniq = uniq.reshape(n, *orig_shape[1:])
        uniq = np.moveaxis(uniq, 0, axis)
        return uniq

    output = _unique1d(consolidated, return_index,
                       return_inverse, return_counts,
                       equal_nan=equal_nan, inverse_shape=inverse_shape,
                       axis=axis, sorted=sorted)
    output = (reshape_uniq(output[0]),) + output[1:]
    return _unpack_tuple(output)


def _unique1d(ar, return_index=False, return_inverse=False,
              return_counts=False, *, equal_nan=True, inverse_shape=None,
              axis=None, sorted=True):
    """
    Find the unique elements of an array, ignoring shape.

    Uses a hash table to find the unique elements if possible.
    """
    ar = np.asanyarray(ar).flatten()
    if len(ar.shape) != 1:
        # np.matrix, and maybe some other array subclasses, insist on keeping
        # two dimensions for all operations. Coerce to an ndarray in such cases.
        ar = np.asarray(ar).flatten()

    optional_indices = return_index or return_inverse

    # masked arrays are not supported yet.
    if not optional_indices and not return_counts and not np.ma.is_masked(ar):
        # First we convert the array to a numpy array, later we wrap it back
        # in case it was a subclass of numpy.ndarray.
        conv = _array_converter(ar)
        ar_, = conv

        if (hash_unique := _unique_hash(ar_)) is not NotImplemented:
            if sorted:
                hash_unique.sort()
            # We wrap the result back in case it was a subclass of numpy.ndarray.
            return (conv.wrap(hash_unique),)

    # If we don't use the hash map, we use the slower sorting method.
    if optional_indices:
        perm = ar.argsort(kind='mergesort' if return_index else 'quicksort')
        aux = ar[perm]
    else:
        ar.sort()
        aux = ar
    mask = np.empty(aux.shape, dtype=np.bool)
    mask[:1] = True
    if (equal_nan and aux.shape[0] > 0 and aux.dtype.kind in "cfmM" and
            np.isnan(aux[-1])):
        if aux.dtype.kind == "c":  # for complex all NaNs are considered equivalent
            aux_firstnan = np.searchsorted(np.isnan(aux), True, side='left')
        else:
            aux_firstnan = np.searchsorted(aux, aux[-1], side='left')
        if aux_firstnan > 0:
            mask[1:aux_firstnan] = (
                aux[1:aux_firstnan] != aux[:aux_firstnan - 1])
        mask[aux_firstnan] = True
        mask[aux_firstnan + 1:] = False
    else:
        mask[1:] = aux[1:] != aux[:-1]

    ret = (aux[mask],)
    if return_index:
        ret += (perm[mask],)
    if return_inverse:
        imask = np.cumsum(mask) - 1
        inv_idx = np.empty(mask.shape, dtype=np.intp)
        inv_idx[perm] = imask
        ret += (inv_idx.reshape(inverse_shape) if axis is None else inv_idx,)
    if return_counts:
        idx = np.concatenate(np.nonzero(mask) + ([mask.size],))
        ret += (np.diff(idx),)
    return ret


# Array API set functions

class UniqueAllResult(NamedTuple):
    values: np.ndarray
    indices: np.ndarray
    inverse_indices: np.ndarray
    counts: np.ndarray


class UniqueCountsResult(NamedTuple):
    values: np.ndarray
    counts: np.ndarray


class UniqueInverseResult(NamedTuple):
    values: np.ndarray
    inverse_indices: np.ndarray


def _unique_all_dispatcher(x, /):
    return (x,)


@array_function_dispatch(_unique_all_dispatcher)
def unique_all(x):
    """
    Find the unique elements of an array, and counts, inverse, and indices.

    This function is an Array API compatible alternative to::

        np.unique(x, return_index=True, return_inverse=True,
                  return_counts=True, equal_nan=False, sorted=False)

    but returns a namedtuple for easier access to each output.

    .. note::
        This function currently always returns a sorted result, however,
        this could change in any NumPy minor release.

    Parameters
    ----------
    x : array_like
        Input array. It will be flattened if it is not already 1-D.

    Returns
    -------
    out : namedtuple
        The result containing:

        * values - The unique elements of an input array.
        * indices - The first occurring indices for each unique element.
        * inverse_indices - The indices from the set of unique elements
          that reconstruct `x`.
        * counts - The corresponding counts for each unique element.

    See Also
    --------
    unique : Find the unique elements of an array.

    Examples
    --------
    >>> import numpy as np
    >>> x = [1, 1, 2]
    >>> uniq = np.unique_all(x)
    >>> uniq.values
    array([1, 2])
    >>> uniq.indices
    array([0, 2])
    >>> uniq.inverse_indices
    array([0, 0, 1])
    >>> uniq.counts
    array([2, 1])
    """
    result = unique(
        x,
        return_index=True,
        return_inverse=True,
        return_counts=True,
        equal_nan=False,
    )
    return UniqueAllResult(*result)


def _unique_counts_dispatcher(x, /):
    return (x,)


@array_function_dispatch(_unique_counts_dispatcher)
def unique_counts(x):
    """
    Find the unique elements and counts of an input array `x`.

    This function is an Array API compatible alternative to::

        np.unique(x, return_counts=True, equal_nan=False, sorted=False)

    but returns a namedtuple for easier access to each output.

    .. note::
        This function currently always returns a sorted result, however,
        this could change in any NumPy minor release.

    Parameters
    ----------
    x : array_like
        Input array. It will be flattened if it is not already 1-D.

    Returns
    -------
    out : namedtuple
        The result containing:

        * values - The unique elements of an input array.
        * counts - The corresponding counts for each unique element.

    See Also
    --------
    unique : Find the unique elements of an array.

    Examples
    --------
    >>> import numpy as np
    >>> x = [1, 1, 2]
    >>> uniq = np.unique_counts(x)
    >>> uniq.values
    array([1, 2])
    >>> uniq.counts
    array([2, 1])
    """
    result = unique(
        x,
        return_index=False,
        return_inverse=False,
        return_counts=True,
        equal_nan=False,
    )
    return UniqueCountsResult(*result)


def _unique_inverse_dispatcher(x, /):
    return (x,)


@array_function_dispatch(_unique_inverse_dispatcher)
def unique_inverse(x):
    """
    Find the unique elements of `x` and indices to reconstruct `x`.

    This function is an Array API compatible alternative to::

        np.unique(x, return_inverse=True, equal_nan=False, sorted=False)

    but returns a namedtuple for easier access to each output.

    .. note::
        This function currently always returns a sorted result, however,
        this could change in any NumPy minor release.

    Parameters
    ----------
    x : array_like
        Input array. It will be flattened if it is not already 1-D.

    Returns
    -------
    out : namedtuple
        The result containing:

        * values - The unique elements of an input array.
        * inverse_indices - The indices from the set of unique elements
          that reconstruct `x`.

    See Also
    --------
    unique : Find the unique elements of an array.

    Examples
    --------
    >>> import numpy as np
    >>> x = [1, 1, 2]
    >>> uniq = np.unique_inverse(x)
    >>> uniq.values
    array([1, 2])
    >>> uniq.inverse_indices
    array([0, 0, 1])
    """
    result = unique(
        x,
        return_index=False,
        return_inverse=True,
        return_counts=False,
        equal_nan=False,
    )
    return UniqueInverseResult(*result)


def _unique_values_dispatcher(x, /):
    return (x,)


@array_function_dispatch(_unique_values_dispatcher)
def unique_values(x):
    """
    Returns the unique elements of an input array `x`.

    This function is an Array API compatible alternative to::

        np.unique(x, equal_nan=False, sorted=False)

    .. versionchanged:: 2.3
       The algorithm was changed to a faster one that does not rely on
       sorting, and hence the results are no longer implicitly sorted.

    Parameters
    ----------
    x : array_like
        Input array. It will be flattened if it is not already 1-D.

    Returns
    -------
    out : ndarray
        The unique elements of an input array.

    See Also
    --------
    unique : Find the unique elements of an array.

    Examples
    --------
    >>> import numpy as np
    >>> np.unique_values([1, 1, 2])
    array([1, 2])  # may vary

    """
    return unique(
        x,
        return_index=False,
        return_inverse=False,
        return_counts=False,
        equal_nan=False,
        sorted=False,
    )


def _intersect1d_dispatcher(
        ar1, ar2, assume_unique=None, return_indices=None):
    return (ar1, ar2)


@array_function_dispatch(_intersect1d_dispatcher)
def intersect1d(ar1, ar2, assume_unique=False, return_indices=False):
    """
    Find the intersection of two arrays.

    Return the sorted, unique values that are in both of the input arrays.

    Parameters
    ----------
    ar1, ar2 : array_like
        Input arrays. Will be flattened if not already 1D.
    assume_unique : bool
        If True, the input arrays are both assumed to be unique, which
        can speed up the calculation.  If True but ``ar1`` or ``ar2`` are not
        unique, incorrect results and out-of-bounds indices could result.
        Default is False.
    return_indices : bool
        If True, the indices which correspond to the intersection of the two
        arrays are returned. The first instance of a value is used if there are
        multiple. Default is False.

    Returns
    -------
    intersect1d : ndarray
        Sorted 1D array of common and unique elements.
    comm1 : ndarray
        The indices of the first occurrences of the common values in `ar1`.
        Only provided if `return_indices` is True.
    comm2 : ndarray
        The indices of the first occurrences of the common values in `ar2`.
        Only provided if `return_indices` is True.

    Examples
    --------
    >>> import numpy as np
    >>> np.intersect1d([1, 3, 4, 3], [3, 1, 2, 1])
    array([1, 3])

    To intersect more than two arrays, use functools.reduce:

    >>> from functools import reduce
    >>> reduce(np.intersect1d, ([1, 3, 4, 3], [3, 1, 2, 1], [6, 3, 4, 2]))
    array([3])

    To return the indices of the values common to the input arrays
    along with the intersected values:

    >>> x = np.array([1, 1, 2, 3, 4])
    >>> y = np.array([2, 1, 4, 6])
    >>> xy, x_ind, y_ind = np.intersect1d(x, y, return_indices=True)
    >>> x_ind, y_ind
    (array([0, 2, 4]), array([1, 0, 2]))
    >>> xy, x[x_ind], y[y_ind]
    (array([1, 2, 4]), array([1, 2, 4]), array([1, 2, 4]))

    """
    ar1 = np.asanyarray(ar1)
    ar2 = np.asanyarray(ar2)

    if not assume_unique:
        if return_indices:
            ar1, ind1 = unique(ar1, return_index=True)
            ar2, ind2 = unique(ar2, return_index=True)
        else:
            ar1 = unique(ar1)
            ar2 = unique(ar2)
    else:
        ar1 = ar1.ravel()
        ar2 = ar2.ravel()

    aux = np.concatenate((ar1, ar2))
    if return_indices:
        aux_sort_indices = np.argsort(aux, kind='mergesort')
        aux = aux[aux_sort_indices]
    else:
        aux.sort()

    mask = aux[1:] == aux[:-1]
    int1d = aux[:-1][mask]

    if return_indices:
        ar1_indices = aux_sort_indices[:-1][mask]
        ar2_indices = aux_sort_indices[1:][mask] - ar1.size
        if not assume_unique:
            ar1_indices = ind1[ar1_indices]
            ar2_indices = ind2[ar2_indices]

        return int1d, ar1_indices, ar2_indices
    else:
        return int1d


def _setxor1d_dispatcher(ar1, ar2, assume_unique=None):
    return (ar1, ar2)


@array_function_dispatch(_setxor1d_dispatcher)
def setxor1d(ar1, ar2, assume_unique=False):
    """
    Find the set exclusive-or of two arrays.

    Return the sorted, unique values that are in only one (not both) of the
    input arrays.

    Parameters
    ----------
    ar1, ar2 : array_like
        Input arrays.
    assume_unique : bool
        If True, the input arrays are both assumed to be unique, which
        can speed up the calculation. Default is False.

    Returns
    -------
    setxor1d : ndarray
        Sorted 1D array of unique values that are in only one of the input
        arrays.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([1, 2, 3, 2, 4])
    >>> b = np.array([2, 3, 5, 7, 5])
    >>> np.setxor1d(a,b)
    array([1, 4, 5, 7])

    """
    if not assume_unique:
        ar1 = unique(ar1)
        ar2 = unique(ar2)

    aux = np.concatenate((ar1, ar2), axis=None)
    if aux.size == 0:
        return aux

    aux.sort()
    flag = np.concatenate(([True], aux[1:] != aux[:-1], [True]))
    return aux[flag[1:] & flag[:-1]]


def _in1d_dispatcher(ar1, ar2, assume_unique=None, invert=None, *,
                     kind=None):
    return (ar1, ar2)


@array_function_dispatch(_in1d_dispatcher)
def in1d(ar1, ar2, assume_unique=False, invert=False, *, kind=None):
    """
    Test whether each element of a 1-D array is also present in a second array.

    .. deprecated:: 2.0
        Use :func:`isin` instead of `in1d` for new code.

    Returns a boolean array the same length as `ar1` that is True
    where an element of `ar1` is in `ar2` and False otherwise.

    Parameters
    ----------
    ar1 : (M,) array_like
        Input array.
    ar2 : array_like
        The values against which to test each value of `ar1`.
    assume_unique : bool, optional
        If True, the input arrays are both assumed to be unique, which
        can speed up the calculation.  Default is False.
    invert : bool, optional
        If True, the values in the returned array are inverted (that is,
        False where an element of `ar1` is in `ar2` and True otherwise).
        Default is False. ``np.in1d(a, b, invert=True)`` is equivalent
        to (but is faster than) ``np.invert(in1d(a, b))``.
    kind : {None, 'sort', 'table'}, optional
        The algorithm to use. This will not affect the final result,
        but will affect the speed and memory use. The default, None,
        will select automatically based on memory considerations.

        * If 'sort', will use a mergesort-based approach. This will have
          a memory usage of roughly 6 times the sum of the sizes of
          `ar1` and `ar2`, not accounting for size of dtypes.
        * If 'table', will use a lookup table approach similar
          to a counting sort. This is only available for boolean and
          integer arrays. This will have a memory usage of the
          size of `ar1` plus the max-min value of `ar2`. `assume_unique`
          has no effect when the 'table' option is used.
        * If None, will automatically choose 'table' if
          the required memory allocation is less than or equal to
          6 times the sum of the sizes of `ar1` and `ar2`,
          otherwise will use 'sort'. This is done to not use
          a large amount of memory by default, even though
          'table' may be faster in most cases. If 'table' is chosen,
          `assume_unique` will have no effect.

    Returns
    -------
    in1d : (M,) ndarray, bool
        The values `ar1[in1d]` are in `ar2`.

    See Also
    --------
    isin                  : Version of this function that preserves the
                            shape of ar1.

    Notes
    -----
    `in1d` can be considered as an element-wise function version of the
    python keyword `in`, for 1-D sequences. ``in1d(a, b)`` is roughly
    equivalent to ``np.array([item in b for item in a])``.
    However, this idea fails if `ar2` is a set, or similar (non-sequence)
    container:  As ``ar2`` is converted to an array, in those cases
    ``asarray(ar2)`` is an object array rather than the expected array of
    contained values.

    Using ``kind='table'`` tends to be faster than `kind='sort'` if the
    following relationship is true:
    ``log10(len(ar2)) > (log10(max(ar2)-min(ar2)) - 2.27) / 0.927``,
    but may use greater memory. The default value for `kind` will
    be automatically selected based only on memory usage, so one may
    manually set ``kind='table'`` if memory constraints can be relaxed.

    Examples
    --------
    >>> import numpy as np
    >>> test = np.array([0, 1, 2, 5, 0])
    >>> states = [0, 2]
    >>> mask = np.in1d(test, states)
    >>> mask
    array([ True, False,  True, False,  True])
    >>> test[mask]
    array([0, 2, 0])
    >>> mask = np.in1d(test, states, invert=True)
    >>> mask
    array([False,  True, False,  True, False])
    >>> test[mask]
    array([1, 5])
    """

    # Deprecated in NumPy 2.0, 2023-08-18
    warnings.warn(
        "`in1d` is deprecated. Use `np.isin` instead.",
        DeprecationWarning,
        stacklevel=2
    )

    return _in1d(ar1, ar2, assume_unique, invert, kind=kind)


def _in1d(ar1, ar2, assume_unique=False, invert=False, *, kind=None):
    # Ravel both arrays, behavior for the first array could be different
    ar1 = np.asarray(ar1).ravel()
    ar2 = np.asarray(ar2).ravel()

    # Ensure that iteration through object arrays yields size-1 arrays
    if ar2.dtype == object:
        ar2 = ar2.reshape(-1, 1)

    if kind not in {None, 'sort', 'table'}:
        raise ValueError(
            f"Invalid kind: '{kind}'. Please use None, 'sort' or 'table'.")

    # Can use the table method if all arrays are integers or boolean:
    is_int_arrays = all(ar.dtype.kind in ("u", "i", "b") for ar in (ar1, ar2))
    use_table_method = is_int_arrays and kind in {None, 'table'}

    if use_table_method:
        if ar2.size == 0:
            if invert:
                return np.ones_like(ar1, dtype=bool)
            else:
                return np.zeros_like(ar1, dtype=bool)

        # Convert booleans to uint8 so we can use the fast integer algorithm
        if ar1.dtype == bool:
            ar1 = ar1.astype(np.uint8)
        if ar2.dtype == bool:
            ar2 = ar2.astype(np.uint8)

        ar2_min = int(np.min(ar2))
        ar2_max = int(np.max(ar2))

        ar2_range = ar2_max - ar2_min

        # Constraints on whether we can actually use the table method:
        #  1. Assert memory usage is not too large
        below_memory_constraint = ar2_range <= 6 * (ar1.size + ar2.size)
        #  2. Check overflows for (ar2 - ar2_min); dtype=ar2.dtype
        range_safe_from_overflow = ar2_range <= np.iinfo(ar2.dtype).max

        # Optimal performance is for approximately
        # log10(size) > (log10(range) - 2.27) / 0.927.
        # However, here we set the requirement that by default
        # the intermediate array can only be 6x
        # the combined memory allocation of the original
        # arrays. See discussion on
        # https://github.com/numpy/numpy/pull/12065.

        if (
            range_safe_from_overflow and
            (below_memory_constraint or kind == 'table')
        ):

            if invert:
                outgoing_array = np.ones_like(ar1, dtype=bool)
            else:
                outgoing_array = np.zeros_like(ar1, dtype=bool)

            # Make elements 1 where the integer exists in ar2
            if invert:
                isin_helper_ar = np.ones(ar2_range + 1, dtype=bool)
                isin_helper_ar[ar2 - ar2_min] = 0
            else:
                isin_helper_ar = np.zeros(ar2_range + 1, dtype=bool)
                isin_helper_ar[ar2 - ar2_min] = 1

            # Mask out elements we know won't work
            basic_mask = (ar1 <= ar2_max) & (ar1 >= ar2_min)
            in_range_ar1 = ar1[basic_mask]
            if in_range_ar1.size == 0:
                # Nothing more to do, since all values are out of range.
                return outgoing_array

            # Unfortunately, ar2_min can be out of range for `intp` even
            # if the calculation result must fit in range (and be positive).
            # In that case, use ar2.dtype which must work for all unmasked
            # values.
            try:
                ar2_min = np.array(ar2_min, dtype=np.intp)
                dtype = np.intp
            except OverflowError:
                dtype = ar2.dtype

            out = np.empty_like(in_range_ar1, dtype=np.intp)
            outgoing_array[basic_mask] = isin_helper_ar[
                    np.subtract(in_range_ar1, ar2_min, dtype=dtype,
                                out=out, casting="unsafe")]

            return outgoing_array
        elif kind == 'table':  # not range_safe_from_overflow
            raise RuntimeError(
                "You have specified kind='table', "
                "but the range of values in `ar2` or `ar1` exceed the "
                "maximum integer of the datatype. "
                "Please set `kind` to None or 'sort'."
            )
    elif kind == 'table':
        raise ValueError(
            "The 'table' method is only "
            "supported for boolean or integer arrays. "
            "Please select 'sort' or None for kind."
        )

    # Check if one of the arrays may contain arbitrary objects
    contains_object = ar1.dtype.hasobject or ar2.dtype.hasobject

    # This code is run when
    # a) the first condition is true, making the code significantly faster
    # b) the second condition is true (i.e. `ar1` or `ar2` may contain
    #    arbitrary objects), since then sorting is not guaranteed to work
    if len(ar2) < 10 * len(ar1) ** 0.145 or contains_object:
        if invert:
            mask = np.ones(len(ar1), dtype=bool)
            for a in ar2:
                mask &= (ar1 != a)
        else:
            mask = np.zeros(len(ar1), dtype=bool)
            for a in ar2:
                mask |= (ar1 == a)
        return mask

    # Otherwise use sorting
    if not assume_unique:
        ar1, rev_idx = np.unique(ar1, return_inverse=True)
        ar2 = np.unique(ar2)

    ar = np.concatenate((ar1, ar2))
    # We need this to be a stable sort, so always use 'mergesort'
    # here. The values from the first array should always come before
    # the values from the second array.
    order = ar.argsort(kind='mergesort')
    sar = ar[order]
    if invert:
        bool_ar = (sar[1:] != sar[:-1])
    else:
        bool_ar = (sar[1:] == sar[:-1])
    flag = np.concatenate((bool_ar, [invert]))
    ret = np.empty(ar.shape, dtype=bool)
    ret[order] = flag

    if assume_unique:
        return ret[:len(ar1)]
    else:
        return ret[rev_idx]


def _isin_dispatcher(element, test_elements, assume_unique=None, invert=None,
                     *, kind=None):
    return (element, test_elements)


@array_function_dispatch(_isin_dispatcher)
def isin(element, test_elements, assume_unique=False, invert=False, *,
         kind=None):
    """
    Calculates ``element in test_elements``, broadcasting over `element` only.
    Returns a boolean array of the same shape as `element` that is True
    where an element of `element` is in `test_elements` and False otherwise.

    Parameters
    ----------
    element : array_like
        Input array.
    test_elements : array_like
        The values against which to test each value of `element`.
        This argument is flattened if it is an array or array_like.
        See notes for behavior with non-array-like parameters.
    assume_unique : bool, optional
        If True, the input arrays are both assumed to be unique, which
        can speed up the calculation.  Default is False.
    invert : bool, optional
        If True, the values in the returned array are inverted, as if
        calculating `element not in test_elements`. Default is False.
        ``np.isin(a, b, invert=True)`` is equivalent to (but faster
        than) ``np.invert(np.isin(a, b))``.
    kind : {None, 'sort', 'table'}, optional
        The algorithm to use. This will not affect the final result,
        but will affect the speed and memory use. The default, None,
        will select automatically based on memory considerations.

        * If 'sort', will use a mergesort-based approach. This will have
          a memory usage of roughly 6 times the sum of the sizes of
          `element` and `test_elements`, not accounting for size of dtypes.
        * If 'table', will use a lookup table approach similar
          to a counting sort. This is only available for boolean and
          integer arrays. This will have a memory usage of the
          size of `element` plus the max-min value of `test_elements`.
          `assume_unique` has no effect when the 'table' option is used.
        * If None, will automatically choose 'table' if
          the required memory allocation is less than or equal to
          6 times the sum of the sizes of `element` and `test_elements`,
          otherwise will use 'sort'. This is done to not use
          a large amount of memory by default, even though
          'table' may be faster in most cases. If 'table' is chosen,
          `assume_unique` will have no effect.


    Returns
    -------
    isin : ndarray, bool
        Has the same shape as `element`. The values `element[isin]`
        are in `test_elements`.

    Notes
    -----
    `isin` is an element-wise function version of the python keyword `in`.
    ``isin(a, b)`` is roughly equivalent to
    ``np.array([item in b for item in a])`` if `a` and `b` are 1-D sequences.

    `element` and `test_elements` are converted to arrays if they are not
    already. If `test_elements` is a set (or other non-sequence collection)
    it will be converted to an object array with one element, rather than an
    array of the values contained in `test_elements`. This is a consequence
    of the `array` constructor's way of handling non-sequence collections.
    Converting the set to a list usually gives the desired behavior.

    Using ``kind='table'`` tends to be faster than `kind='sort'` if the
    following relationship is true:
    ``log10(len(test_elements)) >
    (log10(max(test_elements)-min(test_elements)) - 2.27) / 0.927``,
    but may use greater memory. The default value for `kind` will
    be automatically selected based only on memory usage, so one may
    manually set ``kind='table'`` if memory constraints can be relaxed.

    Examples
    --------
    >>> import numpy as np
    >>> element = 2*np.arange(4).reshape((2, 2))
    >>> element
    array([[0, 2],
           [4, 6]])
    >>> test_elements = [1, 2, 4, 8]
    >>> mask = np.isin(element, test_elements)
    >>> mask
    array([[False,  True],
           [ True, False]])
    >>> element[mask]
    array([2, 4])

    The indices of the matched values can be obtained with `nonzero`:

    >>> np.nonzero(mask)
    (array([0, 1]), array([1, 0]))

    The test can also be inverted:

    >>> mask = np.isin(element, test_elements, invert=True)
    >>> mask
    array([[ True, False],
           [False,  True]])
    >>> element[mask]
    array([0, 6])

    Because of how `array` handles sets, the following does not
    work as expected:

    >>> test_set = {1, 2, 4, 8}
    >>> np.isin(element, test_set)
    array([[False, False],
           [False, False]])

    Casting the set to a list gives the expected result:

    >>> np.isin(element, list(test_set))
    array([[False,  True],
           [ True, False]])
    """
    element = np.asarray(element)
    return _in1d(element, test_elements, assume_unique=assume_unique,
                 invert=invert, kind=kind).reshape(element.shape)


def _union1d_dispatcher(ar1, ar2):
    return (ar1, ar2)


@array_function_dispatch(_union1d_dispatcher)
def union1d(ar1, ar2):
    """
    Find the union of two arrays.

    Return the unique, sorted array of values that are in either of the two
    input arrays.

    Parameters
    ----------
    ar1, ar2 : array_like
        Input arrays. They are flattened if they are not already 1D.

    Returns
    -------
    union1d : ndarray
        Unique, sorted union of the input arrays.

    Examples
    --------
    >>> import numpy as np
    >>> np.union1d([-1, 0, 1], [-2, 0, 2])
    array([-2, -1,  0,  1,  2])

    To find the union of more than two arrays, use functools.reduce:

    >>> from functools import reduce
    >>> reduce(np.union1d, ([1, 3, 4, 3], [3, 1, 2, 1], [6, 3, 4, 2]))
    array([1, 2, 3, 4, 6])
    """
    return unique(np.concatenate((ar1, ar2), axis=None))


def _setdiff1d_dispatcher(ar1, ar2, assume_unique=None):
    return (ar1, ar2)


@array_function_dispatch(_setdiff1d_dispatcher)
def setdiff1d(ar1, ar2, assume_unique=False):
    """
    Find the set difference of two arrays.

    Return the unique values in `ar1` that are not in `ar2`.

    Parameters
    ----------
    ar1 : array_like
        Input array.
    ar2 : array_like
        Input comparison array.
    assume_unique : bool
        If True, the input arrays are both assumed to be unique, which
        can speed up the calculation.  Default is False.

    Returns
    -------
    setdiff1d : ndarray
        1D array of values in `ar1` that are not in `ar2`. The result
        is sorted when `assume_unique=False`, but otherwise only sorted
        if the input is sorted.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([1, 2, 3, 2, 4, 1])
    >>> b = np.array([3, 4, 5, 6])
    >>> np.setdiff1d(a, b)
    array([1, 2])

    """
    if assume_unique:
        ar1 = np.asarray(ar1).ravel()
    else:
        ar1 = unique(ar1)
        ar2 = unique(ar2)
    return ar1[_in1d(ar1, ar2, assume_unique=True, invert=True)]

# === NexusCore/openenv\Lib\site-packages\numpy\lib\_twodim_base_impl.py ===
""" Basic functions for manipulating 2d arrays

"""
import functools
import operator

from numpy._core import iinfo, overrides
from numpy._core._multiarray_umath import _array_converter
from numpy._core.numeric import (
    arange,
    asanyarray,
    asarray,
    diagonal,
    empty,
    greater_equal,
    indices,
    int8,
    int16,
    int32,
    int64,
    intp,
    multiply,
    nonzero,
    ones,
    promote_types,
    where,
    zeros,
)
from numpy._core.overrides import finalize_array_function_like, set_module
from numpy.lib._stride_tricks_impl import broadcast_to

__all__ = [
    'diag', 'diagflat', 'eye', 'fliplr', 'flipud', 'tri', 'triu',
    'tril', 'vander', 'histogram2d', 'mask_indices', 'tril_indices',
    'tril_indices_from', 'triu_indices', 'triu_indices_from', ]


array_function_dispatch = functools.partial(
    overrides.array_function_dispatch, module='numpy')


i1 = iinfo(int8)
i2 = iinfo(int16)
i4 = iinfo(int32)


def _min_int(low, high):
    """ get small int that fits the range """
    if high <= i1.max and low >= i1.min:
        return int8
    if high <= i2.max and low >= i2.min:
        return int16
    if high <= i4.max and low >= i4.min:
        return int32
    return int64


def _flip_dispatcher(m):
    return (m,)


@array_function_dispatch(_flip_dispatcher)
def fliplr(m):
    """
    Reverse the order of elements along axis 1 (left/right).

    For a 2-D array, this flips the entries in each row in the left/right
    direction. Columns are preserved, but appear in a different order than
    before.

    Parameters
    ----------
    m : array_like
        Input array, must be at least 2-D.

    Returns
    -------
    f : ndarray
        A view of `m` with the columns reversed.  Since a view
        is returned, this operation is :math:`\\mathcal O(1)`.

    See Also
    --------
    flipud : Flip array in the up/down direction.
    flip : Flip array in one or more dimensions.
    rot90 : Rotate array counterclockwise.

    Notes
    -----
    Equivalent to ``m[:,::-1]`` or ``np.flip(m, axis=1)``.
    Requires the array to be at least 2-D.

    Examples
    --------
    >>> import numpy as np
    >>> A = np.diag([1.,2.,3.])
    >>> A
    array([[1.,  0.,  0.],
           [0.,  2.,  0.],
           [0.,  0.,  3.]])
    >>> np.fliplr(A)
    array([[0.,  0.,  1.],
           [0.,  2.,  0.],
           [3.,  0.,  0.]])

    >>> rng = np.random.default_rng()
    >>> A = rng.normal(size=(2,3,5))
    >>> np.all(np.fliplr(A) == A[:,::-1,...])
    True

    """
    m = asanyarray(m)
    if m.ndim < 2:
        raise ValueError("Input must be >= 2-d.")
    return m[:, ::-1]


@array_function_dispatch(_flip_dispatcher)
def flipud(m):
    """
    Reverse the order of elements along axis 0 (up/down).

    For a 2-D array, this flips the entries in each column in the up/down
    direction. Rows are preserved, but appear in a different order than before.

    Parameters
    ----------
    m : array_like
        Input array.

    Returns
    -------
    out : array_like
        A view of `m` with the rows reversed.  Since a view is
        returned, this operation is :math:`\\mathcal O(1)`.

    See Also
    --------
    fliplr : Flip array in the left/right direction.
    flip : Flip array in one or more dimensions.
    rot90 : Rotate array counterclockwise.

    Notes
    -----
    Equivalent to ``m[::-1, ...]`` or ``np.flip(m, axis=0)``.
    Requires the array to be at least 1-D.

    Examples
    --------
    >>> import numpy as np
    >>> A = np.diag([1.0, 2, 3])
    >>> A
    array([[1.,  0.,  0.],
           [0.,  2.,  0.],
           [0.,  0.,  3.]])
    >>> np.flipud(A)
    array([[0.,  0.,  3.],
           [0.,  2.,  0.],
           [1.,  0.,  0.]])

    >>> rng = np.random.default_rng()
    >>> A = rng.normal(size=(2,3,5))
    >>> np.all(np.flipud(A) == A[::-1,...])
    True

    >>> np.flipud([1,2])
    array([2, 1])

    """
    m = asanyarray(m)
    if m.ndim < 1:
        raise ValueError("Input must be >= 1-d.")
    return m[::-1, ...]


@finalize_array_function_like
@set_module('numpy')
def eye(N, M=None, k=0, dtype=float, order='C', *, device=None, like=None):
    """
    Return a 2-D array with ones on the diagonal and zeros elsewhere.

    Parameters
    ----------
    N : int
      Number of rows in the output.
    M : int, optional
      Number of columns in the output. If None, defaults to `N`.
    k : int, optional
      Index of the diagonal: 0 (the default) refers to the main diagonal,
      a positive value refers to an upper diagonal, and a negative value
      to a lower diagonal.
    dtype : data-type, optional
      Data-type of the returned array.
    order : {'C', 'F'}, optional
        Whether the output should be stored in row-major (C-style) or
        column-major (Fortran-style) order in memory.
    device : str, optional
        The device on which to place the created array. Default: None.
        For Array-API interoperability only, so must be ``"cpu"`` if passed.

        .. versionadded:: 2.0.0
    ${ARRAY_FUNCTION_LIKE}

        .. versionadded:: 1.20.0

    Returns
    -------
    I : ndarray of shape (N,M)
      An array where all elements are equal to zero, except for the `k`-th
      diagonal, whose values are equal to one.

    See Also
    --------
    identity : (almost) equivalent function
    diag : diagonal 2-D array from a 1-D array specified by the user.

    Examples
    --------
    >>> import numpy as np
    >>> np.eye(2, dtype=int)
    array([[1, 0],
           [0, 1]])
    >>> np.eye(3, k=1)
    array([[0.,  1.,  0.],
           [0.,  0.,  1.],
           [0.,  0.,  0.]])

    """
    if like is not None:
        return _eye_with_like(
            like, N, M=M, k=k, dtype=dtype, order=order, device=device
        )
    if M is None:
        M = N
    m = zeros((N, M), dtype=dtype, order=order, device=device)
    if k >= M:
        return m
    # Ensure M and k are integers, so we don't get any surprise casting
    # results in the expressions `M-k` and `M+1` used below.  This avoids
    # a problem with inputs with type (for example) np.uint64.
    M = operator.index(M)
    k = operator.index(k)
    if k >= 0:
        i = k
    else:
        i = (-k) * M
    m[:M - k].flat[i::M + 1] = 1
    return m


_eye_with_like = array_function_dispatch()(eye)


def _diag_dispatcher(v, k=None):
    return (v,)


@array_function_dispatch(_diag_dispatcher)
def diag(v, k=0):
    """
    Extract a diagonal or construct a diagonal array.

    See the more detailed documentation for ``numpy.diagonal`` if you use this
    function to extract a diagonal and wish to write to the resulting array;
    whether it returns a copy or a view depends on what version of numpy you
    are using.

    Parameters
    ----------
    v : array_like
        If `v` is a 2-D array, return a copy of its `k`-th diagonal.
        If `v` is a 1-D array, return a 2-D array with `v` on the `k`-th
        diagonal.
    k : int, optional
        Diagonal in question. The default is 0. Use `k>0` for diagonals
        above the main diagonal, and `k<0` for diagonals below the main
        diagonal.

    Returns
    -------
    out : ndarray
        The extracted diagonal or constructed diagonal array.

    See Also
    --------
    diagonal : Return specified diagonals.
    diagflat : Create a 2-D array with the flattened input as a diagonal.
    trace : Sum along diagonals.
    triu : Upper triangle of an array.
    tril : Lower triangle of an array.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.arange(9).reshape((3,3))
    >>> x
    array([[0, 1, 2],
           [3, 4, 5],
           [6, 7, 8]])

    >>> np.diag(x)
    array([0, 4, 8])
    >>> np.diag(x, k=1)
    array([1, 5])
    >>> np.diag(x, k=-1)
    array([3, 7])

    >>> np.diag(np.diag(x))
    array([[0, 0, 0],
           [0, 4, 0],
           [0, 0, 8]])

    """
    v = asanyarray(v)
    s = v.shape
    if len(s) == 1:
        n = s[0] + abs(k)
        res = zeros((n, n), v.dtype)
        if k >= 0:
            i = k
        else:
            i = (-k) * n
        res[:n - k].flat[i::n + 1] = v
        return res
    elif len(s) == 2:
        return diagonal(v, k)
    else:
        raise ValueError("Input must be 1- or 2-d.")


@array_function_dispatch(_diag_dispatcher)
def diagflat(v, k=0):
    """
    Create a two-dimensional array with the flattened input as a diagonal.

    Parameters
    ----------
    v : array_like
        Input data, which is flattened and set as the `k`-th
        diagonal of the output.
    k : int, optional
        Diagonal to set; 0, the default, corresponds to the "main" diagonal,
        a positive (negative) `k` giving the number of the diagonal above
        (below) the main.

    Returns
    -------
    out : ndarray
        The 2-D output array.

    See Also
    --------
    diag : MATLAB work-alike for 1-D and 2-D arrays.
    diagonal : Return specified diagonals.
    trace : Sum along diagonals.

    Examples
    --------
    >>> import numpy as np
    >>> np.diagflat([[1,2], [3,4]])
    array([[1, 0, 0, 0],
           [0, 2, 0, 0],
           [0, 0, 3, 0],
           [0, 0, 0, 4]])

    >>> np.diagflat([1,2], 1)
    array([[0, 1, 0],
           [0, 0, 2],
           [0, 0, 0]])

    """
    conv = _array_converter(v)
    v, = conv.as_arrays(subok=False)
    v = v.ravel()
    s = len(v)
    n = s + abs(k)
    res = zeros((n, n), v.dtype)
    if (k >= 0):
        i = arange(0, n - k, dtype=intp)
        fi = i + k + i * n
    else:
        i = arange(0, n + k, dtype=intp)
        fi = i + (i - k) * n
    res.flat[fi] = v

    return conv.wrap(res)


@finalize_array_function_like
@set_module('numpy')
def tri(N, M=None, k=0, dtype=float, *, like=None):
    """
    An array with ones at and below the given diagonal and zeros elsewhere.

    Parameters
    ----------
    N : int
        Number of rows in the array.
    M : int, optional
        Number of columns in the array.
        By default, `M` is taken equal to `N`.
    k : int, optional
        The sub-diagonal at and below which the array is filled.
        `k` = 0 is the main diagonal, while `k` < 0 is below it,
        and `k` > 0 is above.  The default is 0.
    dtype : dtype, optional
        Data type of the returned array.  The default is float.
    ${ARRAY_FUNCTION_LIKE}

        .. versionadded:: 1.20.0

    Returns
    -------
    tri : ndarray of shape (N, M)
        Array with its lower triangle filled with ones and zero elsewhere;
        in other words ``T[i,j] == 1`` for ``j <= i + k``, 0 otherwise.

    Examples
    --------
    >>> import numpy as np
    >>> np.tri(3, 5, 2, dtype=int)
    array([[1, 1, 1, 0, 0],
           [1, 1, 1, 1, 0],
           [1, 1, 1, 1, 1]])

    >>> np.tri(3, 5, -1)
    array([[0.,  0.,  0.,  0.,  0.],
           [1.,  0.,  0.,  0.,  0.],
           [1.,  1.,  0.,  0.,  0.]])

    """
    if like is not None:
        return _tri_with_like(like, N, M=M, k=k, dtype=dtype)

    if M is None:
        M = N

    m = greater_equal.outer(arange(N, dtype=_min_int(0, N)),
                            arange(-k, M - k, dtype=_min_int(-k, M - k)))

    # Avoid making a copy if the requested type is already bool
    m = m.astype(dtype, copy=False)

    return m


_tri_with_like = array_function_dispatch()(tri)


def _trilu_dispatcher(m, k=None):
    return (m,)


@array_function_dispatch(_trilu_dispatcher)
def tril(m, k=0):
    """
    Lower triangle of an array.

    Return a copy of an array with elements above the `k`-th diagonal zeroed.
    For arrays with ``ndim`` exceeding 2, `tril` will apply to the final two
    axes.

    Parameters
    ----------
    m : array_like, shape (..., M, N)
        Input array.
    k : int, optional
        Diagonal above which to zero elements.  `k = 0` (the default) is the
        main diagonal, `k < 0` is below it and `k > 0` is above.

    Returns
    -------
    tril : ndarray, shape (..., M, N)
        Lower triangle of `m`, of same shape and data-type as `m`.

    See Also
    --------
    triu : same thing, only for the upper triangle

    Examples
    --------
    >>> import numpy as np
    >>> np.tril([[1,2,3],[4,5,6],[7,8,9],[10,11,12]], -1)
    array([[ 0,  0,  0],
           [ 4,  0,  0],
           [ 7,  8,  0],
           [10, 11, 12]])

    >>> np.tril(np.arange(3*4*5).reshape(3, 4, 5))
    array([[[ 0,  0,  0,  0,  0],
            [ 5,  6,  0,  0,  0],
            [10, 11, 12,  0,  0],
            [15, 16, 17, 18,  0]],
           [[20,  0,  0,  0,  0],
            [25, 26,  0,  0,  0],
            [30, 31, 32,  0,  0],
            [35, 36, 37, 38,  0]],
           [[40,  0,  0,  0,  0],
            [45, 46,  0,  0,  0],
            [50, 51, 52,  0,  0],
            [55, 56, 57, 58,  0]]])

    """
    m = asanyarray(m)
    mask = tri(*m.shape[-2:], k=k, dtype=bool)

    return where(mask, m, zeros(1, m.dtype))


@array_function_dispatch(_trilu_dispatcher)
def triu(m, k=0):
    """
    Upper triangle of an array.

    Return a copy of an array with the elements below the `k`-th diagonal
    zeroed. For arrays with ``ndim`` exceeding 2, `triu` will apply to the
    final two axes.

    Please refer to the documentation for `tril` for further details.

    See Also
    --------
    tril : lower triangle of an array

    Examples
    --------
    >>> import numpy as np
    >>> np.triu([[1,2,3],[4,5,6],[7,8,9],[10,11,12]], -1)
    array([[ 1,  2,  3],
           [ 4,  5,  6],
           [ 0,  8,  9],
           [ 0,  0, 12]])

    >>> np.triu(np.arange(3*4*5).reshape(3, 4, 5))
    array([[[ 0,  1,  2,  3,  4],
            [ 0,  6,  7,  8,  9],
            [ 0,  0, 12, 13, 14],
            [ 0,  0,  0, 18, 19]],
           [[20, 21, 22, 23, 24],
            [ 0, 26, 27, 28, 29],
            [ 0,  0, 32, 33, 34],
            [ 0,  0,  0, 38, 39]],
           [[40, 41, 42, 43, 44],
            [ 0, 46, 47, 48, 49],
            [ 0,  0, 52, 53, 54],
            [ 0,  0,  0, 58, 59]]])

    """
    m = asanyarray(m)
    mask = tri(*m.shape[-2:], k=k - 1, dtype=bool)

    return where(mask, zeros(1, m.dtype), m)


def _vander_dispatcher(x, N=None, increasing=None):
    return (x,)


# Originally borrowed from John Hunter and matplotlib
@array_function_dispatch(_vander_dispatcher)
def vander(x, N=None, increasing=False):
    """
    Generate a Vandermonde matrix.

    The columns of the output matrix are powers of the input vector. The
    order of the powers is determined by the `increasing` boolean argument.
    Specifically, when `increasing` is False, the `i`-th output column is
    the input vector raised element-wise to the power of ``N - i - 1``. Such
    a matrix with a geometric progression in each row is named for Alexandre-
    Theophile Vandermonde.

    Parameters
    ----------
    x : array_like
        1-D input array.
    N : int, optional
        Number of columns in the output.  If `N` is not specified, a square
        array is returned (``N = len(x)``).
    increasing : bool, optional
        Order of the powers of the columns.  If True, the powers increase
        from left to right, if False (the default) they are reversed.

    Returns
    -------
    out : ndarray
        Vandermonde matrix.  If `increasing` is False, the first column is
        ``x^(N-1)``, the second ``x^(N-2)`` and so forth. If `increasing` is
        True, the columns are ``x^0, x^1, ..., x^(N-1)``.

    See Also
    --------
    polynomial.polynomial.polyvander

    Examples
    --------
    >>> import numpy as np
    >>> x = np.array([1, 2, 3, 5])
    >>> N = 3
    >>> np.vander(x, N)
    array([[ 1,  1,  1],
           [ 4,  2,  1],
           [ 9,  3,  1],
           [25,  5,  1]])

    >>> np.column_stack([x**(N-1-i) for i in range(N)])
    array([[ 1,  1,  1],
           [ 4,  2,  1],
           [ 9,  3,  1],
           [25,  5,  1]])

    >>> x = np.array([1, 2, 3, 5])
    >>> np.vander(x)
    array([[  1,   1,   1,   1],
           [  8,   4,   2,   1],
           [ 27,   9,   3,   1],
           [125,  25,   5,   1]])
    >>> np.vander(x, increasing=True)
    array([[  1,   1,   1,   1],
           [  1,   2,   4,   8],
           [  1,   3,   9,  27],
           [  1,   5,  25, 125]])

    The determinant of a square Vandermonde matrix is the product
    of the differences between the values of the input vector:

    >>> np.linalg.det(np.vander(x))
    48.000000000000043 # may vary
    >>> (5-3)*(5-2)*(5-1)*(3-2)*(3-1)*(2-1)
    48

    """
    x = asarray(x)
    if x.ndim != 1:
        raise ValueError("x must be a one-dimensional array or sequence.")
    if N is None:
        N = len(x)

    v = empty((len(x), N), dtype=promote_types(x.dtype, int))
    tmp = v[:, ::-1] if not increasing else v

    if N > 0:
        tmp[:, 0] = 1
    if N > 1:
        tmp[:, 1:] = x[:, None]
        multiply.accumulate(tmp[:, 1:], out=tmp[:, 1:], axis=1)

    return v


def _histogram2d_dispatcher(x, y, bins=None, range=None, density=None,
                            weights=None):
    yield x
    yield y

    # This terrible logic is adapted from the checks in histogram2d
    try:
        N = len(bins)
    except TypeError:
        N = 1
    if N == 2:
        yield from bins  # bins=[x, y]
    else:
        yield bins

    yield weights


@array_function_dispatch(_histogram2d_dispatcher)
def histogram2d(x, y, bins=10, range=None, density=None, weights=None):
    """
    Compute the bi-dimensional histogram of two data samples.

    Parameters
    ----------
    x : array_like, shape (N,)
        An array containing the x coordinates of the points to be
        histogrammed.
    y : array_like, shape (N,)
        An array containing the y coordinates of the points to be
        histogrammed.
    bins : int or array_like or [int, int] or [array, array], optional
        The bin specification:

        * If int, the number of bins for the two dimensions (nx=ny=bins).
        * If array_like, the bin edges for the two dimensions
          (x_edges=y_edges=bins).
        * If [int, int], the number of bins in each dimension
          (nx, ny = bins).
        * If [array, array], the bin edges in each dimension
          (x_edges, y_edges = bins).
        * A combination [int, array] or [array, int], where int
          is the number of bins and array is the bin edges.

    range : array_like, shape(2,2), optional
        The leftmost and rightmost edges of the bins along each dimension
        (if not specified explicitly in the `bins` parameters):
        ``[[xmin, xmax], [ymin, ymax]]``. All values outside of this range
        will be considered outliers and not tallied in the histogram.
    density : bool, optional
        If False, the default, returns the number of samples in each bin.
        If True, returns the probability *density* function at the bin,
        ``bin_count / sample_count / bin_area``.
    weights : array_like, shape(N,), optional
        An array of values ``w_i`` weighing each sample ``(x_i, y_i)``.
        Weights are normalized to 1 if `density` is True. If `density` is
        False, the values of the returned histogram are equal to the sum of
        the weights belonging to the samples falling into each bin.

    Returns
    -------
    H : ndarray, shape(nx, ny)
        The bi-dimensional histogram of samples `x` and `y`. Values in `x`
        are histogrammed along the first dimension and values in `y` are
        histogrammed along the second dimension.
    xedges : ndarray, shape(nx+1,)
        The bin edges along the first dimension.
    yedges : ndarray, shape(ny+1,)
        The bin edges along the second dimension.

    See Also
    --------
    histogram : 1D histogram
    histogramdd : Multidimensional histogram

    Notes
    -----
    When `density` is True, then the returned histogram is the sample
    density, defined such that the sum over bins of the product
    ``bin_value * bin_area`` is 1.

    Please note that the histogram does not follow the Cartesian convention
    where `x` values are on the abscissa and `y` values on the ordinate
    axis.  Rather, `x` is histogrammed along the first dimension of the
    array (vertical), and `y` along the second dimension of the array
    (horizontal).  This ensures compatibility with `histogramdd`.

    Examples
    --------
    >>> import numpy as np
    >>> from matplotlib.image import NonUniformImage
    >>> import matplotlib.pyplot as plt

    Construct a 2-D histogram with variable bin width. First define the bin
    edges:

    >>> xedges = [0, 1, 3, 5]
    >>> yedges = [0, 2, 3, 4, 6]

    Next we create a histogram H with random bin content:

    >>> x = np.random.normal(2, 1, 100)
    >>> y = np.random.normal(1, 1, 100)
    >>> H, xedges, yedges = np.histogram2d(x, y, bins=(xedges, yedges))
    >>> # Histogram does not follow Cartesian convention (see Notes),
    >>> # therefore transpose H for visualization purposes.
    >>> H = H.T

    :func:`imshow <matplotlib.pyplot.imshow>` can only display square bins:

    >>> fig = plt.figure(figsize=(7, 3))
    >>> ax = fig.add_subplot(131, title='imshow: square bins')
    >>> plt.imshow(H, interpolation='nearest', origin='lower',
    ...         extent=[xedges[0], xedges[-1], yedges[0], yedges[-1]])
    <matplotlib.image.AxesImage object at 0x...>

    :func:`pcolormesh <matplotlib.pyplot.pcolormesh>` can display actual edges:

    >>> ax = fig.add_subplot(132, title='pcolormesh: actual edges',
    ...         aspect='equal')
    >>> X, Y = np.meshgrid(xedges, yedges)
    >>> ax.pcolormesh(X, Y, H)
    <matplotlib.collections.QuadMesh object at 0x...>

    :class:`NonUniformImage <matplotlib.image.NonUniformImage>` can be used to
    display actual bin edges with interpolation:

    >>> ax = fig.add_subplot(133, title='NonUniformImage: interpolated',
    ...         aspect='equal', xlim=xedges[[0, -1]], ylim=yedges[[0, -1]])
    >>> im = NonUniformImage(ax, interpolation='bilinear')
    >>> xcenters = (xedges[:-1] + xedges[1:]) / 2
    >>> ycenters = (yedges[:-1] + yedges[1:]) / 2
    >>> im.set_data(xcenters, ycenters, H)
    >>> ax.add_image(im)
    >>> plt.show()

    It is also possible to construct a 2-D histogram without specifying bin
    edges:

    >>> # Generate non-symmetric test data
    >>> n = 10000
    >>> x = np.linspace(1, 100, n)
    >>> y = 2*np.log(x) + np.random.rand(n) - 0.5
    >>> # Compute 2d histogram. Note the order of x/y and xedges/yedges
    >>> H, yedges, xedges = np.histogram2d(y, x, bins=20)

    Now we can plot the histogram using
    :func:`pcolormesh <matplotlib.pyplot.pcolormesh>`, and a
    :func:`hexbin <matplotlib.pyplot.hexbin>` for comparison.

    >>> # Plot histogram using pcolormesh
    >>> fig, (ax1, ax2) = plt.subplots(ncols=2, sharey=True)
    >>> ax1.pcolormesh(xedges, yedges, H, cmap='rainbow')
    >>> ax1.plot(x, 2*np.log(x), 'k-')
    >>> ax1.set_xlim(x.min(), x.max())
    >>> ax1.set_ylim(y.min(), y.max())
    >>> ax1.set_xlabel('x')
    >>> ax1.set_ylabel('y')
    >>> ax1.set_title('histogram2d')
    >>> ax1.grid()

    >>> # Create hexbin plot for comparison
    >>> ax2.hexbin(x, y, gridsize=20, cmap='rainbow')
    >>> ax2.plot(x, 2*np.log(x), 'k-')
    >>> ax2.set_title('hexbin')
    >>> ax2.set_xlim(x.min(), x.max())
    >>> ax2.set_xlabel('x')
    >>> ax2.grid()

    >>> plt.show()
    """
    from numpy import histogramdd

    if len(x) != len(y):
        raise ValueError('x and y must have the same length.')

    try:
        N = len(bins)
    except TypeError:
        N = 1

    if N not in {1, 2}:
        xedges = yedges = asarray(bins)
        bins = [xedges, yedges]
    hist, edges = histogramdd([x, y], bins, range, density, weights)
    return hist, edges[0], edges[1]


@set_module('numpy')
def mask_indices(n, mask_func, k=0):
    """
    Return the indices to access (n, n) arrays, given a masking function.

    Assume `mask_func` is a function that, for a square array a of size
    ``(n, n)`` with a possible offset argument `k`, when called as
    ``mask_func(a, k)`` returns a new array with zeros in certain locations
    (functions like `triu` or `tril` do precisely this). Then this function
    returns the indices where the non-zero values would be located.

    Parameters
    ----------
    n : int
        The returned indices will be valid to access arrays of shape (n, n).
    mask_func : callable
        A function whose call signature is similar to that of `triu`, `tril`.
        That is, ``mask_func(x, k)`` returns a boolean array, shaped like `x`.
        `k` is an optional argument to the function.
    k : scalar
        An optional argument which is passed through to `mask_func`. Functions
        like `triu`, `tril` take a second argument that is interpreted as an
        offset.

    Returns
    -------
    indices : tuple of arrays.
        The `n` arrays of indices corresponding to the locations where
        ``mask_func(np.ones((n, n)), k)`` is True.

    See Also
    --------
    triu, tril, triu_indices, tril_indices

    Examples
    --------
    >>> import numpy as np

    These are the indices that would allow you to access the upper triangular
    part of any 3x3 array:

    >>> iu = np.mask_indices(3, np.triu)

    For example, if `a` is a 3x3 array:

    >>> a = np.arange(9).reshape(3, 3)
    >>> a
    array([[0, 1, 2],
           [3, 4, 5],
           [6, 7, 8]])
    >>> a[iu]
    array([0, 1, 2, 4, 5, 8])

    An offset can be passed also to the masking function.  This gets us the
    indices starting on the first diagonal right of the main one:

    >>> iu1 = np.mask_indices(3, np.triu, 1)

    with which we now extract only three elements:

    >>> a[iu1]
    array([1, 2, 5])

    """
    m = ones((n, n), int)
    a = mask_func(m, k)
    return nonzero(a != 0)


@set_module('numpy')
def tril_indices(n, k=0, m=None):
    """
    Return the indices for the lower-triangle of an (n, m) array.

    Parameters
    ----------
    n : int
        The row dimension of the arrays for which the returned
        indices will be valid.
    k : int, optional
        Diagonal offset (see `tril` for details).
    m : int, optional
        The column dimension of the arrays for which the returned
        arrays will be valid.
        By default `m` is taken equal to `n`.


    Returns
    -------
    inds : tuple of arrays
        The row and column indices, respectively. The row indices are sorted
        in non-decreasing order, and the correspdonding column indices are
        strictly increasing for each row.

    See also
    --------
    triu_indices : similar function, for upper-triangular.
    mask_indices : generic function accepting an arbitrary mask function.
    tril, triu

    Examples
    --------
    >>> import numpy as np

    Compute two different sets of indices to access 4x4 arrays, one for the
    lower triangular part starting at the main diagonal, and one starting two
    diagonals further right:

    >>> il1 = np.tril_indices(4)
    >>> il1
    (array([0, 1, 1, 2, 2, 2, 3, 3, 3, 3]), array([0, 0, 1, 0, 1, 2, 0, 1, 2, 3]))

    Note that row indices (first array) are non-decreasing, and the corresponding
    column indices (second array) are strictly increasing for each row.
    Here is how they can be used with a sample array:

    >>> a = np.arange(16).reshape(4, 4)
    >>> a
    array([[ 0,  1,  2,  3],
           [ 4,  5,  6,  7],
           [ 8,  9, 10, 11],
           [12, 13, 14, 15]])

    Both for indexing:

    >>> a[il1]
    array([ 0,  4,  5, ..., 13, 14, 15])

    And for assigning values:

    >>> a[il1] = -1
    >>> a
    array([[-1,  1,  2,  3],
           [-1, -1,  6,  7],
           [-1, -1, -1, 11],
           [-1, -1, -1, -1]])

    These cover almost the whole array (two diagonals right of the main one):

    >>> il2 = np.tril_indices(4, 2)
    >>> a[il2] = -10
    >>> a
    array([[-10, -10, -10,   3],
           [-10, -10, -10, -10],
           [-10, -10, -10, -10],
           [-10, -10, -10, -10]])

    """
    tri_ = tri(n, m, k=k, dtype=bool)

    return tuple(broadcast_to(inds, tri_.shape)[tri_]
                 for inds in indices(tri_.shape, sparse=True))


def _trilu_indices_form_dispatcher(arr, k=None):
    return (arr,)


@array_function_dispatch(_trilu_indices_form_dispatcher)
def tril_indices_from(arr, k=0):
    """
    Return the indices for the lower-triangle of arr.

    See `tril_indices` for full details.

    Parameters
    ----------
    arr : array_like
        The indices will be valid for square arrays whose dimensions are
        the same as arr.
    k : int, optional
        Diagonal offset (see `tril` for details).

    Examples
    --------
    >>> import numpy as np

    Create a 4 by 4 array

    >>> a = np.arange(16).reshape(4, 4)
    >>> a
    array([[ 0,  1,  2,  3],
           [ 4,  5,  6,  7],
           [ 8,  9, 10, 11],
           [12, 13, 14, 15]])

    Pass the array to get the indices of the lower triangular elements.

    >>> trili = np.tril_indices_from(a)
    >>> trili
    (array([0, 1, 1, 2, 2, 2, 3, 3, 3, 3]), array([0, 0, 1, 0, 1, 2, 0, 1, 2, 3]))

    >>> a[trili]
    array([ 0,  4,  5,  8,  9, 10, 12, 13, 14, 15])

    This is syntactic sugar for tril_indices().

    >>> np.tril_indices(a.shape[0])
    (array([0, 1, 1, 2, 2, 2, 3, 3, 3, 3]), array([0, 0, 1, 0, 1, 2, 0, 1, 2, 3]))

    Use the `k` parameter to return the indices for the lower triangular array
    up to the k-th diagonal.

    >>> trili1 = np.tril_indices_from(a, k=1)
    >>> a[trili1]
    array([ 0,  1,  4,  5,  6,  8,  9, 10, 11, 12, 13, 14, 15])

    See Also
    --------
    tril_indices, tril, triu_indices_from
    """
    if arr.ndim != 2:
        raise ValueError("input array must be 2-d")
    return tril_indices(arr.shape[-2], k=k, m=arr.shape[-1])


@set_module('numpy')
def triu_indices(n, k=0, m=None):
    """
    Return the indices for the upper-triangle of an (n, m) array.

    Parameters
    ----------
    n : int
        The size of the arrays for which the returned indices will
        be valid.
    k : int, optional
        Diagonal offset (see `triu` for details).
    m : int, optional
        The column dimension of the arrays for which the returned
        arrays will be valid.
        By default `m` is taken equal to `n`.


    Returns
    -------
    inds : tuple, shape(2) of ndarrays, shape(`n`)
        The row and column indices, respectively. The row indices are sorted
        in non-decreasing order, and the correspdonding column indices are
        strictly increasing for each row.

    See also
    --------
    tril_indices : similar function, for lower-triangular.
    mask_indices : generic function accepting an arbitrary mask function.
    triu, tril

    Examples
    --------
    >>> import numpy as np

    Compute two different sets of indices to access 4x4 arrays, one for the
    upper triangular part starting at the main diagonal, and one starting two
    diagonals further right:

    >>> iu1 = np.triu_indices(4)
    >>> iu1
    (array([0, 0, 0, 0, 1, 1, 1, 2, 2, 3]), array([0, 1, 2, 3, 1, 2, 3, 2, 3, 3]))

    Note that row indices (first array) are non-decreasing, and the corresponding
    column indices (second array) are strictly increasing for each row.

    Here is how they can be used with a sample array:

    >>> a = np.arange(16).reshape(4, 4)
    >>> a
    array([[ 0,  1,  2,  3],
           [ 4,  5,  6,  7],
           [ 8,  9, 10, 11],
           [12, 13, 14, 15]])

    Both for indexing:

    >>> a[iu1]
    array([ 0,  1,  2, ..., 10, 11, 15])

    And for assigning values:

    >>> a[iu1] = -1
    >>> a
    array([[-1, -1, -1, -1],
           [ 4, -1, -1, -1],
           [ 8,  9, -1, -1],
           [12, 13, 14, -1]])

    These cover only a small part of the whole array (two diagonals right
    of the main one):

    >>> iu2 = np.triu_indices(4, 2)
    >>> a[iu2] = -10
    >>> a
    array([[ -1,  -1, -10, -10],
           [  4,  -1,  -1, -10],
           [  8,   9,  -1,  -1],
           [ 12,  13,  14,  -1]])

    """
    tri_ = ~tri(n, m, k=k - 1, dtype=bool)

    return tuple(broadcast_to(inds, tri_.shape)[tri_]
                 for inds in indices(tri_.shape, sparse=True))


@array_function_dispatch(_trilu_indices_form_dispatcher)
def triu_indices_from(arr, k=0):
    """
    Return the indices for the upper-triangle of arr.

    See `triu_indices` for full details.

    Parameters
    ----------
    arr : ndarray, shape(N, N)
        The indices will be valid for square arrays.
    k : int, optional
        Diagonal offset (see `triu` for details).

    Returns
    -------
    triu_indices_from : tuple, shape(2) of ndarray, shape(N)
        Indices for the upper-triangle of `arr`.

    Examples
    --------
    >>> import numpy as np

    Create a 4 by 4 array

    >>> a = np.arange(16).reshape(4, 4)
    >>> a
    array([[ 0,  1,  2,  3],
           [ 4,  5,  6,  7],
           [ 8,  9, 10, 11],
           [12, 13, 14, 15]])

    Pass the array to get the indices of the upper triangular elements.

    >>> triui = np.triu_indices_from(a)
    >>> triui
    (array([0, 0, 0, 0, 1, 1, 1, 2, 2, 3]), array([0, 1, 2, 3, 1, 2, 3, 2, 3, 3]))

    >>> a[triui]
    array([ 0,  1,  2,  3,  5,  6,  7, 10, 11, 15])

    This is syntactic sugar for triu_indices().

    >>> np.triu_indices(a.shape[0])
    (array([0, 0, 0, 0, 1, 1, 1, 2, 2, 3]), array([0, 1, 2, 3, 1, 2, 3, 2, 3, 3]))

    Use the `k` parameter to return the indices for the upper triangular array
    from the k-th diagonal.

    >>> triuim1 = np.triu_indices_from(a, k=1)
    >>> a[triuim1]
    array([ 1,  2,  3,  6,  7, 11])


    See Also
    --------
    triu_indices, triu, tril_indices_from
    """
    if arr.ndim != 2:
        raise ValueError("input array must be 2-d")
    return triu_indices(arr.shape[-2], k=k, m=arr.shape[-1])

# === NexusCore/openenv\Lib\site-packages\win32\lib\win32timezone.py ===
"""
win32timezone:
    Module for handling datetime.tzinfo time zones using the windows
registry for time zone information.  The time zone names are dependent
on the registry entries defined by the operating system.

    This module may be tested using the doctest module.

    Written by Jason R. Coombs (jaraco@jaraco.com).
    Copyright © 2003-2012.
    All Rights Reserved.

    This module is licenced for use in Mark Hammond's pywin32
library under the same terms as the pywin32 library.

    To use this time zone module with the datetime module, simply pass
the TimeZoneInfo object to the datetime constructor.  For example,

>>> import win32timezone, datetime
>>> assert 'Mountain Standard Time' in win32timezone.TimeZoneInfo.get_sorted_time_zone_names()
>>> MST = win32timezone.TimeZoneInfo('Mountain Standard Time')
>>> now = datetime.datetime.now(MST)

    The now object is now a time-zone aware object, and daylight savings-
aware methods may be called on it.

>>> now.utcoffset() in (datetime.timedelta(-1, 61200), datetime.timedelta(-1, 64800))
True

(note that the result of utcoffset call will be different based on when now was
generated, unless standard time is always used)

>>> now = datetime.datetime.now(win32timezone.TimeZoneInfo('Mountain Standard Time', True))
>>> now.utcoffset()
datetime.timedelta(days=-1, seconds=61200)

>>> aug2 = datetime.datetime(2003, 8, 2, tzinfo = MST)
>>> tuple(aug2.utctimetuple())
(2003, 8, 2, 6, 0, 0, 5, 214, 0)
>>> nov2 = datetime.datetime(2003, 11, 25, tzinfo = MST)
>>> tuple(nov2.utctimetuple())
(2003, 11, 25, 7, 0, 0, 1, 329, 0)

To convert from one timezone to another, just use the astimezone method.

>>> aug2.isoformat()
'2003-08-02T00:00:00-06:00'
>>> aug2est = aug2.astimezone(win32timezone.TimeZoneInfo('Eastern Standard Time'))
>>> aug2est.isoformat()
'2003-08-02T02:00:00-04:00'

calling the displayName member will return the display name as set in the
registry.

>>> est = win32timezone.TimeZoneInfo('Eastern Standard Time')
>>> str(est.displayName)
'(UTC-05:00) Eastern Time (US & Canada)'

>>> gmt = win32timezone.TimeZoneInfo('GMT Standard Time', True)
>>> str(gmt.displayName)
'(UTC+00:00) Dublin, Edinburgh, Lisbon, London'

To get the complete list of available time zone keys,
>>> zones = win32timezone.TimeZoneInfo.get_all_time_zones()

If you want to get them in an order that's sorted longitudinally
>>> zones = win32timezone.TimeZoneInfo.get_sorted_time_zones()

TimeZoneInfo now supports being pickled and comparison
>>> import pickle
>>> tz = win32timezone.TimeZoneInfo('China Standard Time')
>>> tz == pickle.loads(pickle.dumps(tz))
True

It's possible to construct a TimeZoneInfo from a TimeZoneDescription
including the currently-defined zone.
>>> code, info = win32timezone.TimeZoneDefinition.current()
>>> tz = win32timezone.TimeZoneInfo(info, not code)
>>> tz == pickle.loads(pickle.dumps(tz))
True

Although it's easier to use TimeZoneInfo.local() to get the local info
>>> tz == TimeZoneInfo.local()
True

>>> aest = win32timezone.TimeZoneInfo('AUS Eastern Standard Time')
>>> est = win32timezone.TimeZoneInfo('E. Australia Standard Time')
>>> dt = datetime.datetime(2006, 11, 11, 1, 0, 0, tzinfo = aest)
>>> estdt = dt.astimezone(est)
>>> estdt.strftime('%Y-%m-%d %H:%M:%S')
'2006-11-11 00:00:00'

>>> dt = datetime.datetime(2007, 1, 12, 1, 0, 0, tzinfo = aest)
>>> estdt = dt.astimezone(est)
>>> estdt.strftime('%Y-%m-%d %H:%M:%S')
'2007-01-12 00:00:00'

>>> dt = datetime.datetime(2007, 6, 13, 1, 0, 0, tzinfo = aest)
>>> estdt = dt.astimezone(est)
>>> estdt.strftime('%Y-%m-%d %H:%M:%S')
'2007-06-13 01:00:00'

Microsoft now has a patch for handling time zones in 2007 (see
https://learn.microsoft.com/en-us/troubleshoot/windows-client/system-management-components/daylight-saving-time-help-support)

As a result, patched systems will give an incorrect result for
dates prior to the designated year except for Vista and its
successors, which have dynamic time zone support.
>>> nov2_pre_change = datetime.datetime(2003, 11, 2, tzinfo = MST)
>>> old_response = (2003, 11, 2, 7, 0, 0, 6, 306, 0)
>>> incorrect_patch_response = (2003, 11, 2, 6, 0, 0, 6, 306, 0)
>>> pre_response = nov2_pre_change.utctimetuple()
>>> pre_response in (old_response, incorrect_patch_response)
True

Furthermore, unpatched systems pre-Vista will give an incorrect
result for dates after 2007.
>>> nov2_post_change = datetime.datetime(2007, 11, 2, tzinfo = MST)
>>> incorrect_unpatched_response = (2007, 11, 2, 7, 0, 0, 4, 306, 0)
>>> new_response = (2007, 11, 2, 6, 0, 0, 4, 306, 0)
>>> post_response = nov2_post_change.utctimetuple()
>>> post_response in (new_response, incorrect_unpatched_response)
True


There is a function you can call to get some capabilities of the time
zone data.
>>> caps = GetTZCapabilities()
>>> isinstance(caps, dict)
True
>>> 'MissingTZPatch' in caps
True
>>> 'DynamicTZSupport' in caps
True

>>> both_dates_correct = (pre_response == old_response and post_response == new_response)
>>> old_dates_wrong = (pre_response == incorrect_patch_response)
>>> new_dates_wrong = (post_response == incorrect_unpatched_response)

>>> caps['DynamicTZSupport'] == both_dates_correct
True

>>> (not caps['DynamicTZSupport'] and caps['MissingTZPatch']) == new_dates_wrong
True

>>> (not caps['DynamicTZSupport'] and not caps['MissingTZPatch']) == old_dates_wrong
True

This test helps ensure language support for unicode characters
>>> x = TIME_ZONE_INFORMATION(0, 'français')


Test conversion from one time zone to another at a DST boundary
===============================================================

>>> tz_hi = TimeZoneInfo('Hawaiian Standard Time')
>>> tz_pac = TimeZoneInfo('Pacific Standard Time')
>>> time_before = datetime.datetime(2011, 11, 5, 15, 59, 59, tzinfo=tz_hi)
>>> tz_hi.utcoffset(time_before)
datetime.timedelta(days=-1, seconds=50400)
>>> tz_hi.dst(time_before)
datetime.timedelta(0)

Hawaii doesn't need dynamic TZ info
>>> getattr(tz_hi, 'dynamicInfo', None)

Here's a time that gave some trouble as reported in #3523104
because one minute later, the equivalent UTC time changes from DST
in the U.S.
>>> dt_hi = datetime.datetime(2011, 11, 5, 15, 59, 59, 0, tzinfo=tz_hi)
>>> dt_hi.timetuple()
time.struct_time(tm_year=2011, tm_mon=11, tm_mday=5, tm_hour=15, tm_min=59, tm_sec=59, tm_wday=5, tm_yday=309, tm_isdst=0)
>>> dt_hi.utctimetuple()
time.struct_time(tm_year=2011, tm_mon=11, tm_mday=6, tm_hour=1, tm_min=59, tm_sec=59, tm_wday=6, tm_yday=310, tm_isdst=0)

Convert the time to pacific time.
>>> dt_pac = dt_hi.astimezone(tz_pac)
>>> dt_pac.timetuple()
time.struct_time(tm_year=2011, tm_mon=11, tm_mday=5, tm_hour=18, tm_min=59, tm_sec=59, tm_wday=5, tm_yday=309, tm_isdst=1)

Notice that the UTC time is almost 2am.
>>> dt_pac.utctimetuple()
time.struct_time(tm_year=2011, tm_mon=11, tm_mday=6, tm_hour=1, tm_min=59, tm_sec=59, tm_wday=6, tm_yday=310, tm_isdst=0)

Now do the same tests one minute later in Hawaii.
>>> time_after = datetime.datetime(2011, 11, 5, 16, 0, 0, 0, tzinfo=tz_hi)
>>> tz_hi.utcoffset(time_after)
datetime.timedelta(days=-1, seconds=50400)
>>> tz_hi.dst(time_before)
datetime.timedelta(0)

>>> dt_hi = datetime.datetime(2011, 11, 5, 16, 0, 0, 0, tzinfo=tz_hi)
>>> print(dt_hi.timetuple())
time.struct_time(tm_year=2011, tm_mon=11, tm_mday=5, tm_hour=16, tm_min=0, tm_sec=0, tm_wday=5, tm_yday=309, tm_isdst=0)
>>> print(dt_hi.utctimetuple())
time.struct_time(tm_year=2011, tm_mon=11, tm_mday=6, tm_hour=2, tm_min=0, tm_sec=0, tm_wday=6, tm_yday=310, tm_isdst=0)

According to the docs, this is what astimezone does.
>>> utc = (dt_hi - dt_hi.utcoffset()).replace(tzinfo=tz_pac)
>>> utc
datetime.datetime(2011, 11, 6, 2, 0, tzinfo=TimeZoneInfo('Pacific Standard Time'))
>>> tz_pac.fromutc(utc) == dt_hi.astimezone(tz_pac)
True
>>> tz_pac.fromutc(utc)
datetime.datetime(2011, 11, 5, 19, 0, tzinfo=TimeZoneInfo('Pacific Standard Time'))

Make sure the converted time is correct.
>>> dt_pac = dt_hi.astimezone(tz_pac)
>>> dt_pac.timetuple()
time.struct_time(tm_year=2011, tm_mon=11, tm_mday=5, tm_hour=19, tm_min=0, tm_sec=0, tm_wday=5, tm_yday=309, tm_isdst=1)
>>> dt_pac.utctimetuple()
time.struct_time(tm_year=2011, tm_mon=11, tm_mday=6, tm_hour=2, tm_min=0, tm_sec=0, tm_wday=6, tm_yday=310, tm_isdst=0)

Check some internal methods
>>> tz_pac._getStandardBias(datetime.datetime(2011, 1, 1))
datetime.timedelta(seconds=28800)
>>> tz_pac._getDaylightBias(datetime.datetime(2011, 1, 1))
datetime.timedelta(seconds=25200)

Test the offsets
>>> offset = tz_pac.utcoffset(datetime.datetime(2011, 11, 6, 2, 0))
>>> offset == datetime.timedelta(hours=-8)
True
>>> dst_offset = tz_pac.dst(datetime.datetime(2011, 11, 6, 2, 0) + offset)
>>> dst_offset == datetime.timedelta(hours=1)
True
>>> (offset + dst_offset) == datetime.timedelta(hours=-7)
True


Test offsets that occur right at the DST changeover
>>> datetime.datetime.utcfromtimestamp(1320570000).replace(
...     tzinfo=TimeZoneInfo.utc()).astimezone(tz_pac)
datetime.datetime(2011, 11, 6, 1, 0, tzinfo=TimeZoneInfo('Pacific Standard Time'))

"""

from __future__ import annotations

import datetime
import functools
import logging
import operator
import re
import struct
import winreg
from itertools import count
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Dict,
    Generator,
    Iterable,
    Mapping,
    TypeVar,
    overload,
)

import win32api

if TYPE_CHECKING:
    from _operator import _SupportsComparison

    from _typeshed import SupportsKeysAndGetItem
    from typing_extensions import Self

__author__ = "Jason R. Coombs <jaraco@jaraco.com>"

_RangeMapKT = TypeVar("_RangeMapKT", bound="_SupportsComparison")

_T = TypeVar("_T")
_VT = TypeVar("_VT")

log = logging.getLogger(__file__)


# A couple of objects for working with objects as if they were native C-type
# structures.
class _SimpleStruct:
    _fields_: ClassVar[list[tuple[str, type]]] = []  # must be overridden by subclasses

    def __init__(self, *args, **kw) -> None:
        for i, (name, typ) in enumerate(self._fields_):
            def_arg = None
            if i < len(args):
                def_arg = args[i]
            if name in kw:
                def_arg = kw[name]
            if def_arg is not None:
                if not isinstance(def_arg, tuple):
                    def_arg = (def_arg,)
            else:
                def_arg = ()
            if len(def_arg) == 1 and isinstance(def_arg[0], typ):
                # already an object of this type.
                # XXX - should copy.copy???
                def_val = def_arg[0]
            else:
                def_val = typ(*def_arg)
            setattr(self, name, def_val)

    def field_names(self) -> list[str]:
        return [f[0] for f in self._fields_]

    def __eq__(self, other) -> bool:
        if not hasattr(other, "_fields_"):
            return False
        if self._fields_ != other._fields_:
            return False
        for name, _ in self._fields_:
            if getattr(self, name) != getattr(other, name):
                return False
        return True

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)


class SYSTEMTIME(_SimpleStruct):
    _fields_ = [
        ("year", int),
        ("month", int),
        ("day_of_week", int),
        ("day", int),
        ("hour", int),
        ("minute", int),
        ("second", int),
        ("millisecond", int),
    ]


class TIME_ZONE_INFORMATION(_SimpleStruct):
    _fields_ = [
        ("bias", int),
        ("standard_name", str),
        ("standard_start", SYSTEMTIME),
        ("standard_bias", int),
        ("daylight_name", str),
        ("daylight_start", SYSTEMTIME),
        ("daylight_bias", int),
    ]


class DYNAMIC_TIME_ZONE_INFORMATION(TIME_ZONE_INFORMATION):
    _fields_ = TIME_ZONE_INFORMATION._fields_ + [
        ("key_name", str),
        ("dynamic_daylight_time_disabled", bool),
    ]


class TimeZoneDefinition(DYNAMIC_TIME_ZONE_INFORMATION):
    """
    A time zone definition class based on the win32
    DYNAMIC_TIME_ZONE_INFORMATION structure.

    Describes a bias against UTC (bias), and two dates at which a separate
    additional bias applies (standard_bias and daylight_bias).
    """

    def __init__(self, *args, **kwargs) -> None:
        """
        >>> test_args = [1] * 44

        Try to construct a TimeZoneDefinition from:

        a) [DYNAMIC_]TIME_ZONE_INFORMATION args
        >>> TimeZoneDefinition(*test_args).bias
        datetime.timedelta(seconds=60)

        b) another TimeZoneDefinition or [DYNAMIC_]TIME_ZONE_INFORMATION
        >>> TimeZoneDefinition(TimeZoneDefinition(*test_args)).bias
        datetime.timedelta(seconds=60)
        >>> TimeZoneDefinition(DYNAMIC_TIME_ZONE_INFORMATION(*test_args)).bias
        datetime.timedelta(seconds=60)
        >>> TimeZoneDefinition(TIME_ZONE_INFORMATION(*test_args)).bias
        datetime.timedelta(seconds=60)

        c) a byte structure (using _from_bytes)
        >>> TimeZoneDefinition(bytes(test_args)).bias
        datetime.timedelta(days=11696, seconds=46140)
        """
        try:
            super().__init__(*args, **kwargs)
            return
        except (TypeError, ValueError):
            pass

        try:
            self.__init_from_other(*args, **kwargs)
            return
        except TypeError:
            pass

        try:
            self.__init_from_bytes(*args, **kwargs)
            return
        except TypeError:
            pass

        raise TypeError(f"Invalid arguments for {self.__class__}")

    def __init_from_bytes(
        self,
        bytes,
        standard_name="",
        daylight_name="",
        key_name="",
        daylight_disabled=False,
    ):
        format = "3l8h8h"
        components = struct.unpack(format, bytes)
        bias, standard_bias, daylight_bias = components[:3]
        standard_start = SYSTEMTIME(*components[3:11])
        daylight_start = SYSTEMTIME(*components[11:19])
        super().__init__(
            bias,
            standard_name,
            standard_start,
            standard_bias,
            daylight_name,
            daylight_start,
            daylight_bias,
            key_name,
            daylight_disabled,
        )

    def __init_from_other(self, other: TIME_ZONE_INFORMATION) -> None:
        if not isinstance(other, TIME_ZONE_INFORMATION):
            raise TypeError("Not a TIME_ZONE_INFORMATION")
        for name in other.field_names():
            # explicitly get the value from the underlying structure
            value = super(TIME_ZONE_INFORMATION, other).__getattribute__(name)
            setattr(self, name, value)
        # consider instead of the loop above just copying the memory directly
        # size = max(ctypes.sizeof(DYNAMIC_TIME_ZONE_INFO), ctypes.sizeof(other))
        # ctypes.memmove(ctypes.addressof(self), other, size)

    if TYPE_CHECKING:
        # TIME_ZONE_INFORMATION fields as obtained by __getattribute__
        bias: datetime.timedelta
        standard_name: str
        standard_start: SYSTEMTIME
        standard_bias: datetime.timedelta
        daylight_name: str
        daylight_start: SYSTEMTIME
        daylight_bias: datetime.timedelta

    def __getattribute__(self, attr: str) -> Any:
        value = super().__getattribute__(attr)
        if "bias" in attr:
            value = datetime.timedelta(minutes=value)
        return value

    @classmethod
    def current(cls):
        "Windows Platform SDK GetTimeZoneInformation"
        code, tzi = win32api.GetTimeZoneInformation(True)
        return code, cls(*tzi)

    def set(self) -> None:
        tzi = tuple(getattr(self, n) for n, t in self._fields_)
        win32api.SetTimeZoneInformation(tzi)

    def copy(self) -> Self:
        # XXX - this is no longer a copy!
        return self.__class__(self)

    def locate_daylight_start(self, year) -> datetime.datetime:
        return self._locate_day(year, self.daylight_start)

    def locate_standard_start(self, year) -> datetime.datetime:
        return self._locate_day(year, self.standard_start)

    @staticmethod
    def _locate_day(year, cutoff) -> datetime.datetime:
        """
        Takes a SYSTEMTIME object, such as retrieved from a TIME_ZONE_INFORMATION
        structure or call to GetTimeZoneInformation and interprets it based on the given
        year to identify the actual day.

        This method is necessary because the SYSTEMTIME structure refers to a day by its
        day of the week and week of the month (e.g. 4th saturday in March).

        >>> SATURDAY = 6
        >>> MARCH = 3
        >>> st = SYSTEMTIME(2000, MARCH, SATURDAY, 4, 0, 0, 0, 0)

        # according to my calendar, the 4th Saturday in March in 2009 was the 28th
        >>> expected_date = datetime.datetime(2009, 3, 28)
        >>> TimeZoneDefinition._locate_day(2009, st) == expected_date
        True
        """
        # MS stores Sunday as 0, Python datetime stores Monday as zero
        target_weekday = (cutoff.day_of_week + 6) % 7
        # For SYSTEMTIMEs relating to time zone information, cutoff.day
        #  is the week of the month
        week_of_month = cutoff.day
        # so the following is the first day of that week
        day = (week_of_month - 1) * 7 + 1
        result = datetime.datetime(
            year,
            cutoff.month,
            day,
            cutoff.hour,
            cutoff.minute,
            cutoff.second,
            cutoff.millisecond,
        )
        # now the result is the correct week, but not necessarily the correct day of the week
        days_to_go = (target_weekday - result.weekday()) % 7
        result += datetime.timedelta(days_to_go)
        # if we selected a day in the month following the target month,
        #  move back a week or two.
        # This is necessary because Microsoft defines the fifth week in a month
        #  to be the last week in a month and adding the time delta might have
        #  pushed the result into the next month.
        while result.month == cutoff.month + 1:
            result -= datetime.timedelta(weeks=1)
        return result


class TimeZoneInfo(datetime.tzinfo):
    """
    Main class for handling Windows time zones.
    Usage:
        TimeZoneInfo(<Time Zone Standard Name>, [<Fix Standard Time>])

    If <Fix Standard Time> evaluates to True, daylight savings time is
    calculated in the same way as standard time.

    >>> tzi = TimeZoneInfo('Pacific Standard Time')
    >>> march31 = datetime.datetime(2000,3,31)

    We know that time zone definitions haven't changed from 2007
    to 2012, so regardless of whether dynamic info is available,
    there should be consistent results for these years.
    >>> subsequent_years = [march31.replace(year=year)
    ...     for year in range(2007, 2013)]
    >>> offsets = set(tzi.utcoffset(year) for year in subsequent_years)
    >>> len(offsets)
    1

    Cannot create a `TimeZoneInfo` with an invalid name.
    >>> TimeZoneInfo('Does not exist')
    Traceback (most recent call last):
    ...
    ValueError: Timezone Name 'Does not exist' not found
    >>> TimeZoneInfo(None)
    Traceback (most recent call last):
    ...
    ValueError: subkey name cannot be empty
    >>> TimeZoneInfo("")
    Traceback (most recent call last):
    ...
    ValueError: subkey name cannot be empty
    """

    # this key works for WinNT+, but not for the Win95 line.
    tzRegKey = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Time Zones"

    def __init__(
        self,
        param: str | TimeZoneDefinition,
        fix_standard_time: bool = False,
    ) -> None:
        if isinstance(param, TimeZoneDefinition):
            self._LoadFromTZI(param)
        else:
            self.timeZoneName = param
            self._LoadInfoFromKey()
        self.fixedStandardTime = fix_standard_time

    # For tzinfo pickle support
    def __getinitargs__(self) -> tuple[TimeZoneDefinition, bool]:
        return (self.staticInfo, self.fixedStandardTime)

    def _FindTimeZoneKey(self) -> _RegKeyDict:
        """Find the registry key for the time zone name (self.timeZoneName)."""
        # for multi-language compatability, match the time zone name in the
        # "Std" key of the time zone key.
        zoneNames = dict(self._get_indexed_time_zone_keys("Std"))
        # Also match the time zone key name itself, to be compatible with
        # English-based hard-coded time zones.
        timeZoneName = zoneNames.get(self.timeZoneName, self.timeZoneName)
        key = _RegKeyDict.open(winreg.HKEY_LOCAL_MACHINE, self.tzRegKey)
        try:
            result = key.subkey(timeZoneName)
        except FileNotFoundError:
            # Don't catch ValueError, keep the original error message
            raise ValueError(f"Timezone Name {timeZoneName!r} not found")
        return result

    def _LoadInfoFromKey(self) -> None:
        """Loads the information from an opened time zone registry key
        into relevant fields of this TZI object"""
        key = self._FindTimeZoneKey()
        self.displayName = key["Display"]
        self.standardName = key["Std"]
        self.daylightName = key["Dlt"]
        self.staticInfo = TimeZoneDefinition(key["TZI"])
        self._LoadDynamicInfoFromKey(key)

    def _LoadFromTZI(self, tzi: TimeZoneDefinition):
        self.timeZoneName = tzi.standard_name
        self.displayName = "Unknown"
        self.standardName = tzi.standard_name
        self.daylightName = tzi.daylight_name
        self.staticInfo = tzi

    def _LoadDynamicInfoFromKey(self, key) -> None:
        """
        >>> tzi = TimeZoneInfo('Central Standard Time')

        Here's how the RangeMap is supposed to work:
        >>> m = RangeMap(zip([2006,2007], 'BC'),
        ...     sort_params = {"reverse": True},
        ...     key_match_comparator=operator.ge)
        >>> m.get(2000, 'A')
        'A'
        >>> m[2006]
        'B'
        >>> m[2007]
        'C'
        >>> m[2008]
        'C'

        >>> m[RangeMap.last_item]
        'B'

        >>> m.get(2008, m[RangeMap.last_item])
        'C'


        Now test the dynamic info (but fallback to our simple RangeMap
        on systems that don't have dynamicInfo).

        >>> dinfo = getattr(tzi, 'dynamicInfo', m)
        >>> 2007 in dinfo
        True
        >>> 2008 in dinfo
        False
        >>> dinfo[2007] == dinfo[2008] == dinfo[2012]
        True
        """
        try:
            info = key.subkey("Dynamic DST")
        except FileNotFoundError:
            return
        del info["FirstEntry"]
        del info["LastEntry"]

        infos = [
            (int(year), TimeZoneDefinition(values)) for year, values in info.items()
        ]
        # create a range mapping that searches by descending year and matches
        # if the target year is greater or equal.
        self.dynamicInfo = RangeMap(
            infos,
            sort_params={"reverse": True},
            key_match_comparator=operator.ge,
        )

    def __repr__(self) -> str:
        result = f"{self.__class__.__name__}({self.timeZoneName!r}"
        if self.fixedStandardTime:
            result += ", True"
        result += ")"
        return result

    def __str__(self) -> str:
        return self.displayName

    @overload  # type: ignore[override] # Split definition into overrides
    def tzname(self, dt: datetime.datetime) -> str: ...
    @overload
    def tzname(self, dt: None) -> None: ...
    def tzname(self, dt: datetime.datetime | None) -> str | None:
        """
        >>> MST = TimeZoneInfo('Mountain Standard Time')
        >>> MST.tzname(datetime.datetime(2003, 8, 2))
        'Mountain Daylight Time'
        >>> MST.tzname(datetime.datetime(2003, 11, 25))
        'Mountain Standard Time'
        >>> MST.tzname(None)

        """
        # https://docs.python.org/3/library/datetime.html#datetime.tzinfo.tzname
        # > [...] returning `None` is appropriate if the class wishes to say
        # > that `time` objects don’t participate in the `tzinfo` protocols.
        if dt is None:
            return None

        dst = self.dst(dt)
        winInfo = self.getWinInfo(dt.year)
        if dst == -winInfo.daylight_bias:
            return self.daylightName
        elif dst == -winInfo.standard_bias:
            return self.standardName

        raise ValueError(
            "Unexpected daylight bias",
            dt,
            dst,
            winInfo.daylight_bias,
            winInfo.standard_bias,
        )

    def getWinInfo(self, targetYear: int) -> TimeZoneDefinition:
        """
        Return the most relevant "info" for this time zone
        in the target year.
        """
        if not getattr(self, "dynamicInfo", {}):
            return self.staticInfo
        # Find the greatest year entry in self.dynamicInfo which is for
        #  a year greater than or equal to our targetYear. If not found,
        #  default to the earliest year.
        return self.dynamicInfo.get(targetYear, self.dynamicInfo[RangeMap.last_item])

    def _getStandardBias(self, dt):
        winInfo = self.getWinInfo(dt.year)
        return winInfo.bias + winInfo.standard_bias

    def _getDaylightBias(self, dt):
        winInfo = self.getWinInfo(dt.year)
        return winInfo.bias + winInfo.daylight_bias

    @overload  # type: ignore[override] # False-positive, our overload covers all base types
    def utcoffset(self, dt: None) -> None: ...
    @overload
    def utcoffset(self, dt: datetime.datetime) -> datetime.timedelta: ...
    def utcoffset(self, dt: datetime.datetime | None) -> datetime.timedelta | None:
        "Calculates the utcoffset according to the datetime.tzinfo spec"
        if dt is None:
            return None
        winInfo = self.getWinInfo(dt.year)
        return -winInfo.bias + self.dst(dt)

    @overload  # type: ignore[override] # False-positive, our overload covers all base types
    def dst(self, dt: None) -> None: ...
    @overload
    def dst(self, dt: datetime.datetime) -> datetime.timedelta: ...
    def dst(self, dt: datetime.datetime | None) -> datetime.timedelta | None:
        """
        Calculate the daylight savings offset according to the
        datetime.tzinfo spec.
        """
        if dt is None:
            return None
        winInfo = self.getWinInfo(dt.year)
        if not self.fixedStandardTime and self._inDaylightSavings(dt):
            result = winInfo.daylight_bias
        else:
            result = winInfo.standard_bias
        return -result

    def _inDaylightSavings(self, dt):
        dt = dt.replace(tzinfo=None)
        winInfo = self.getWinInfo(dt.year)
        try:
            dstStart = self.GetDSTStartTime(dt.year)
            dstEnd = self.GetDSTEndTime(dt.year)

            # at the end of DST, when clocks are moved back, there's a period
            #  of daylight_bias where it's ambiguous whether we're in DST or
            #  not.
            dstEndAdj = dstEnd + winInfo.daylight_bias

            # the same thing could theoretically happen at the start of DST
            #  if there's a standard_bias (which I suspect is always 0).
            dstStartAdj = dstStart + winInfo.standard_bias

            if dstStart < dstEnd:
                in_dst = dstStartAdj <= dt < dstEndAdj
            else:
                # in the southern hemisphere, daylight savings time
                #  typically ends before it begins in a given year.
                in_dst = not (dstEndAdj < dt <= dstStartAdj)
        except ValueError:
            # there was an error parsing the time zone, which is normal when a
            #  start and end time are not specified.
            in_dst = False

        return in_dst

    def GetDSTStartTime(self, year: int) -> datetime.datetime:
        "Given a year, determines the time when daylight savings time starts"
        return self.getWinInfo(year).locate_daylight_start(year)

    def GetDSTEndTime(self, year: int) -> datetime.datetime:
        "Given a year, determines the time when daylight savings ends."
        return self.getWinInfo(year).locate_standard_start(year)

    def __eq__(self, other: object) -> bool:
        return self.__dict__ == other.__dict__

    def __ne__(self, other: object) -> bool:
        return self.__dict__ != other.__dict__

    @classmethod
    def local(cls) -> Self:
        """Returns the local time zone as defined by the operating system in the
        registry.
        >>> localTZ = TimeZoneInfo.local()
        >>> now_local = datetime.datetime.now(localTZ)
        >>> now_UTC = datetime.datetime.utcnow()  # deprecated
        >>> (now_UTC - now_local) < datetime.timedelta(seconds = 5)
        Traceback (most recent call last):
        ...
        TypeError: can't subtract offset-naive and offset-aware datetimes

        >>> now_UTC = now_UTC.replace(tzinfo = TimeZoneInfo('GMT Standard Time', True))

        Now one can compare the results of the two offset aware values
        >>> (now_UTC - now_local) < datetime.timedelta(seconds = 5)
        True

        Or use the newer `datetime.timezone.utc`
        >>> now_UTC = datetime.datetime.now(datetime.timezone.utc)
        >>> (now_UTC - now_local) < datetime.timedelta(seconds = 5)
        True
        """
        code, info = TimeZoneDefinition.current()
        # code is 0 if daylight savings is disabled or not defined
        #  code is 1 or 2 if daylight savings is enabled, 2 if currently active
        fix_standard_time = not code
        # note that although the given information is sufficient
        # to construct a WinTZI object, it's
        # not sufficient to represent the time zone in which
        # the current user is operating due
        # to dynamic time zones.
        return cls(info, fix_standard_time)

    _tzutc: ClassVar[Self | None] = None

    @classmethod
    def utc(cls) -> Self:
        """Returns a time-zone representing UTC.

        Same as TimeZoneInfo('GMT Standard Time', True) but caches the result
        for performance.

        >>> isinstance(TimeZoneInfo.utc(), TimeZoneInfo)
        True
        """
        if not cls._tzutc:
            cls._tzutc = cls("GMT Standard Time", True)
        return cls._tzutc

    # helper methods for accessing the timezone info from the registry
    @staticmethod
    def _get_time_zone_key(subkey=None):
        "Return the registry key that stores time zone details"
        key = _RegKeyDict.open(winreg.HKEY_LOCAL_MACHINE, TimeZoneInfo.tzRegKey)
        if subkey:
            key = key.subkey(subkey)
        return key

    @staticmethod
    def _get_time_zone_key_names():
        "Returns the names of the (registry keys of the) time zones"
        return TimeZoneInfo._get_time_zone_key().subkeys()

    @staticmethod
    def _get_indexed_time_zone_keys(index_key="Index"):
        """
        Get the names of the registry keys indexed by a value in that key,
        ignoring any keys for which that value is empty or missing.
        """
        key_names = list(TimeZoneInfo._get_time_zone_key_names())

        def get_index_value(key_name):
            key = TimeZoneInfo._get_time_zone_key(key_name)
            return key.get(index_key)

        values = map(get_index_value, key_names)

        return (
            (value, key_name) for value, key_name in zip(values, key_names) if value
        )

    @staticmethod
    def get_sorted_time_zone_names() -> list[str]:
        """
        Return a list of time zone names that can
        be used to initialize TimeZoneInfo instances.
        """
        tzs = TimeZoneInfo.get_sorted_time_zones()
        return [tz.standardName for tz in tzs]

    @staticmethod
    def get_all_time_zones() -> list[TimeZoneInfo]:
        return [TimeZoneInfo(n) for n in TimeZoneInfo._get_time_zone_key_names()]

    @staticmethod
    def get_sorted_time_zones(key=None) -> list[TimeZoneInfo]:
        """
        Return the time zones sorted by some key.
        key must be a function that takes a TimeZoneInfo object and returns
        a value suitable for sorting on.
        The key defaults to the bias (descending), as is done in Windows
        (see https://web.archive.org/web/20130723075340/http://blogs.msdn.com/b/michkap/archive/2006/12/22/1350684.aspx)
        """
        key = key or (lambda tzi: -tzi.staticInfo.bias)
        zones = TimeZoneInfo.get_all_time_zones()
        zones.sort(key=key)
        return zones


class _RegKeyDict(Dict[str, str]):
    def __init__(self, key: winreg._KeyType):
        dict.__init__(self)
        self.key = key
        self.__load_values()

    @classmethod
    def open(
        cls, key: winreg._KeyType, sub_key: str, reserved: int = 0, access: int = 131097
    ) -> _RegKeyDict:
        return _RegKeyDict(winreg.OpenKeyEx(key, sub_key, reserved, access))

    def subkey(self, name: str) -> _RegKeyDict:
        if not name:
            raise ValueError("subkey name cannot be empty")
        return _RegKeyDict(winreg.OpenKeyEx(self.key, name))

    def __load_values(self):
        pairs = [(n, v) for (n, v, t) in self._enumerate_reg_values(self.key)]
        self.update(pairs)

    def subkeys(self):
        return self._enumerate_reg_keys(self.key)

    @staticmethod
    def _enumerate_reg_values(key):
        return _RegKeyDict._enumerate_reg(key, winreg.EnumValue)

    @staticmethod
    def _enumerate_reg_keys(key):
        return _RegKeyDict._enumerate_reg(key, winreg.EnumKey)

    @staticmethod
    def _enumerate_reg(
        key: _T, func: Callable[[_T, int], _VT]
    ) -> Generator[_VT, None, None]:
        "Enumerates an open registry key as an iterable generator"
        try:
            for index in count():
                yield func(key, index)
        except OSError:
            pass


def utcnow() -> datetime.datetime:
    """
    Return the UTC time now with timezone awareness as enabled
    by this module
    >>> now = utcnow()

    >>> (now - datetime.datetime.now(datetime.timezone.utc)) < datetime.timedelta(seconds = 5)
    True
    >>> type(now.tzinfo) is TimeZoneInfo
    True
    """
    return datetime.datetime.now(TimeZoneInfo.utc())


def now() -> datetime.datetime:
    """
    Return the local time now with timezone awareness as enabled
    by this module
    >>> now_local = now()

    >>> (now_local - datetime.datetime.now(datetime.timezone.utc)) < datetime.timedelta(seconds = 5)
    True
    >>> type(now_local.tzinfo) is TimeZoneInfo
    True
    """
    return datetime.datetime.now(TimeZoneInfo.local())


def GetTZCapabilities() -> dict[str, bool]:
    """
    Run a few known tests to determine the capabilities of
    the time zone database on this machine.
    Note Dynamic Time Zone support is not available on any
    platform at this time; this
    is a limitation of this library, not the platform."""
    tzi = TimeZoneInfo("Mountain Standard Time")
    MissingTZPatch = datetime.datetime(2007, 11, 2, tzinfo=tzi).utctimetuple() != (
        2007,
        11,
        2,
        6,
        0,
        0,
        4,
        306,
        0,
    )
    DynamicTZSupport = not MissingTZPatch and datetime.datetime(
        2003, 11, 2, tzinfo=tzi
    ).utctimetuple() == (2003, 11, 2, 7, 0, 0, 6, 306, 0)
    del tzi
    return locals()


class DLLHandleCache:
    def __init__(self) -> None:
        self.__cache: dict[str, int] = {}

    def __getitem__(self, filename: str) -> int:
        key = filename.lower()
        return self.__cache.setdefault(key, win32api.LoadLibrary(key))


DLLCache = DLLHandleCache()


def resolveMUITimeZone(spec: str) -> str | None:
    """Resolve a multilingual user interface resource for the time zone name

    spec should be of the format @path,-stringID[;comment]
    see https://learn.microsoft.com/en-ca/windows/win32/api/timezoneapi/ns-timezoneapi-time_zone_information
    for details

    >>> import sys
    >>> result = resolveMUITimeZone('@tzres.dll,-110')
    >>> expectedResultType = [type(None),str][sys.getwindowsversion() >= (6,)]
    >>> type(result) is expectedResultType
    True
    """
    pattern = re.compile(r"@(?P<dllname>.*),-(?P<index>\d+)(?:;(?P<comment>.*))?")
    matcher = pattern.match(spec)
    assert matcher, "Could not parse MUI spec"

    groupdict = matcher.groupdict()
    try:
        handle = DLLCache[groupdict["dllname"]]
        result: str | None = win32api.LoadString(handle, int(groupdict["index"]))
    except win32api.error:
        result = None
    return result


# from jaraco.collections 5.1
class RangeMap(Dict[_RangeMapKT, _VT]):
    """
    A dictionary-like object that uses the keys as bounds for a range.
    Inclusion of the value for that range is determined by the
    key_match_comparator, which defaults to less-than-or-equal.
    A value is returned for a key if it is the first key that matches in
    the sorted list of keys.

    One may supply keyword parameters to be passed to the sort function used
    to sort keys (i.e. key, reverse) as sort_params.

    Create a map that maps 1-3 -> 'a', 4-6 -> 'b'

    >>> r = RangeMap({3: 'a', 6: 'b'})  # boy, that was easy
    >>> r[1], r[2], r[3], r[4], r[5], r[6]
    ('a', 'a', 'a', 'b', 'b', 'b')

    Even float values should work so long as the comparison operator
    supports it.

    >>> r[4.5]
    'b'

    Notice that the way rangemap is defined, it must be open-ended
    on one side.

    >>> r[0]
    'a'
    >>> r[-1]
    'a'

    One can close the open-end of the RangeMap by using undefined_value

    >>> r = RangeMap({0: RangeMap.undefined_value, 3: 'a', 6: 'b'})
    >>> r[0]
    Traceback (most recent call last):
    ...
    KeyError: 0

    One can get the first or last elements in the range by using RangeMap.Item

    >>> last_item = RangeMap.Item(-1)
    >>> r[last_item]
    'b'

    .last_item is a shortcut for Item(-1)

    >>> r[RangeMap.last_item]
    'b'

    Sometimes it's useful to find the bounds for a RangeMap

    >>> r.bounds()
    (0, 6)

    RangeMap supports .get(key, default)

    >>> r.get(0, 'not found')
    'not found'

    >>> r.get(7, 'not found')
    'not found'

    One often wishes to define the ranges by their left-most values,
    which requires use of sort params and a key_match_comparator.

    >>> r = RangeMap({1: 'a', 4: 'b'},
    ...     sort_params=dict(reverse=True),
    ...     key_match_comparator=operator.ge)
    >>> r[1], r[2], r[3], r[4], r[5], r[6]
    ('a', 'a', 'a', 'b', 'b', 'b')

    That wasn't nearly as easy as before, so an alternate constructor
    is provided:

    >>> r = RangeMap.left({1: 'a', 4: 'b', 7: RangeMap.undefined_value})
    >>> r[1], r[2], r[3], r[4], r[5], r[6]
    ('a', 'a', 'a', 'b', 'b', 'b')

    """

    def __init__(
        self,
        source: (
            SupportsKeysAndGetItem[_RangeMapKT, _VT] | Iterable[tuple[_RangeMapKT, _VT]]
        ),
        sort_params: Mapping[str, Any] = {},
        key_match_comparator: Callable[[_RangeMapKT, _RangeMapKT], bool] = operator.le,
    ) -> None:
        dict.__init__(self, source)
        self.sort_params = sort_params
        self.match = key_match_comparator

    @classmethod
    def left(
        cls,
        source: (
            SupportsKeysAndGetItem[_RangeMapKT, _VT] | Iterable[tuple[_RangeMapKT, _VT]]
        ),
    ) -> Self:
        return cls(
            source, sort_params={"reverse": True}, key_match_comparator=operator.ge
        )

    def __getitem__(self, item: _RangeMapKT) -> _VT:
        sorted_keys = sorted(self, **self.sort_params)
        if isinstance(item, RangeMap.Item):
            result = self.__getitem__(sorted_keys[item])
        else:
            key = self._find_first_match_(sorted_keys, item)
            result = dict.__getitem__(self, key)
            if result is RangeMap.undefined_value:
                raise KeyError(key)
        return result

    @overload  # type: ignore[override] # Signature simplified over dict and Mapping
    def get(self, key: _RangeMapKT, default: _T) -> _VT | _T: ...
    @overload
    def get(self, key: _RangeMapKT, default: None = None) -> _VT | None: ...
    def get(self, key: _RangeMapKT, default: _T | None = None) -> _VT | _T | None:
        """
        Return the value for key if key is in the dictionary, else default.
        If default is not given, it defaults to None, so that this method
        never raises a KeyError.
        """
        # Necessary to use our own __getitem__ and not dict's
        try:
            return self[key]
        except KeyError:
            return default

    def _find_first_match_(
        self, keys: Iterable[_RangeMapKT], item: _RangeMapKT
    ) -> _RangeMapKT:
        is_match = functools.partial(self.match, item)
        matches = filter(is_match, keys)
        try:
            return next(matches)
        except StopIteration:
            raise KeyError(item) from None

    def bounds(self) -> tuple[_RangeMapKT, _RangeMapKT]:
        sorted_keys = sorted(self, **self.sort_params)
        return (sorted_keys[RangeMap.first_item], sorted_keys[RangeMap.last_item])

    # some special values for the RangeMap
    undefined_value = type("RangeValueUndefined", (), {})()

    class Item(int):
        """RangeMap Item"""

    first_item = Item(0)
    last_item = Item(-1)

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\_twodim_base_impl.py ===
""" Basic functions for manipulating 2d arrays

"""
import functools
import operator

from numpy._core import iinfo, overrides
from numpy._core._multiarray_umath import _array_converter
from numpy._core.numeric import (
    arange,
    asanyarray,
    asarray,
    diagonal,
    empty,
    greater_equal,
    indices,
    int8,
    int16,
    int32,
    int64,
    intp,
    multiply,
    nonzero,
    ones,
    promote_types,
    where,
    zeros,
)
from numpy._core.overrides import finalize_array_function_like, set_module
from numpy.lib._stride_tricks_impl import broadcast_to

__all__ = [
    'diag', 'diagflat', 'eye', 'fliplr', 'flipud', 'tri', 'triu',
    'tril', 'vander', 'histogram2d', 'mask_indices', 'tril_indices',
    'tril_indices_from', 'triu_indices', 'triu_indices_from', ]


array_function_dispatch = functools.partial(
    overrides.array_function_dispatch, module='numpy')


i1 = iinfo(int8)
i2 = iinfo(int16)
i4 = iinfo(int32)


def _min_int(low, high):
    """ get small int that fits the range """
    if high <= i1.max and low >= i1.min:
        return int8
    if high <= i2.max and low >= i2.min:
        return int16
    if high <= i4.max and low >= i4.min:
        return int32
    return int64


def _flip_dispatcher(m):
    return (m,)


@array_function_dispatch(_flip_dispatcher)
def fliplr(m):
    """
    Reverse the order of elements along axis 1 (left/right).

    For a 2-D array, this flips the entries in each row in the left/right
    direction. Columns are preserved, but appear in a different order than
    before.

    Parameters
    ----------
    m : array_like
        Input array, must be at least 2-D.

    Returns
    -------
    f : ndarray
        A view of `m` with the columns reversed.  Since a view
        is returned, this operation is :math:`\\mathcal O(1)`.

    See Also
    --------
    flipud : Flip array in the up/down direction.
    flip : Flip array in one or more dimensions.
    rot90 : Rotate array counterclockwise.

    Notes
    -----
    Equivalent to ``m[:,::-1]`` or ``np.flip(m, axis=1)``.
    Requires the array to be at least 2-D.

    Examples
    --------
    >>> import numpy as np
    >>> A = np.diag([1.,2.,3.])
    >>> A
    array([[1.,  0.,  0.],
           [0.,  2.,  0.],
           [0.,  0.,  3.]])
    >>> np.fliplr(A)
    array([[0.,  0.,  1.],
           [0.,  2.,  0.],
           [3.,  0.,  0.]])

    >>> rng = np.random.default_rng()
    >>> A = rng.normal(size=(2,3,5))
    >>> np.all(np.fliplr(A) == A[:,::-1,...])
    True

    """
    m = asanyarray(m)
    if m.ndim < 2:
        raise ValueError("Input must be >= 2-d.")
    return m[:, ::-1]


@array_function_dispatch(_flip_dispatcher)
def flipud(m):
    """
    Reverse the order of elements along axis 0 (up/down).

    For a 2-D array, this flips the entries in each column in the up/down
    direction. Rows are preserved, but appear in a different order than before.

    Parameters
    ----------
    m : array_like
        Input array.

    Returns
    -------
    out : array_like
        A view of `m` with the rows reversed.  Since a view is
        returned, this operation is :math:`\\mathcal O(1)`.

    See Also
    --------
    fliplr : Flip array in the left/right direction.
    flip : Flip array in one or more dimensions.
    rot90 : Rotate array counterclockwise.

    Notes
    -----
    Equivalent to ``m[::-1, ...]`` or ``np.flip(m, axis=0)``.
    Requires the array to be at least 1-D.

    Examples
    --------
    >>> import numpy as np
    >>> A = np.diag([1.0, 2, 3])
    >>> A
    array([[1.,  0.,  0.],
           [0.,  2.,  0.],
           [0.,  0.,  3.]])
    >>> np.flipud(A)
    array([[0.,  0.,  3.],
           [0.,  2.,  0.],
           [1.,  0.,  0.]])

    >>> rng = np.random.default_rng()
    >>> A = rng.normal(size=(2,3,5))
    >>> np.all(np.flipud(A) == A[::-1,...])
    True

    >>> np.flipud([1,2])
    array([2, 1])

    """
    m = asanyarray(m)
    if m.ndim < 1:
        raise ValueError("Input must be >= 1-d.")
    return m[::-1, ...]


@finalize_array_function_like
@set_module('numpy')
def eye(N, M=None, k=0, dtype=float, order='C', *, device=None, like=None):
    """
    Return a 2-D array with ones on the diagonal and zeros elsewhere.

    Parameters
    ----------
    N : int
      Number of rows in the output.
    M : int, optional
      Number of columns in the output. If None, defaults to `N`.
    k : int, optional
      Index of the diagonal: 0 (the default) refers to the main diagonal,
      a positive value refers to an upper diagonal, and a negative value
      to a lower diagonal.
    dtype : data-type, optional
      Data-type of the returned array.
    order : {'C', 'F'}, optional
        Whether the output should be stored in row-major (C-style) or
        column-major (Fortran-style) order in memory.
    device : str, optional
        The device on which to place the created array. Default: None.
        For Array-API interoperability only, so must be ``"cpu"`` if passed.

        .. versionadded:: 2.0.0
    ${ARRAY_FUNCTION_LIKE}

        .. versionadded:: 1.20.0

    Returns
    -------
    I : ndarray of shape (N,M)
      An array where all elements are equal to zero, except for the `k`-th
      diagonal, whose values are equal to one.

    See Also
    --------
    identity : (almost) equivalent function
    diag : diagonal 2-D array from a 1-D array specified by the user.

    Examples
    --------
    >>> import numpy as np
    >>> np.eye(2, dtype=int)
    array([[1, 0],
           [0, 1]])
    >>> np.eye(3, k=1)
    array([[0.,  1.,  0.],
           [0.,  0.,  1.],
           [0.,  0.,  0.]])

    """
    if like is not None:
        return _eye_with_like(
            like, N, M=M, k=k, dtype=dtype, order=order, device=device
        )
    if M is None:
        M = N
    m = zeros((N, M), dtype=dtype, order=order, device=device)
    if k >= M:
        return m
    # Ensure M and k are integers, so we don't get any surprise casting
    # results in the expressions `M-k` and `M+1` used below.  This avoids
    # a problem with inputs with type (for example) np.uint64.
    M = operator.index(M)
    k = operator.index(k)
    if k >= 0:
        i = k
    else:
        i = (-k) * M
    m[:M - k].flat[i::M + 1] = 1
    return m


_eye_with_like = array_function_dispatch()(eye)


def _diag_dispatcher(v, k=None):
    return (v,)


@array_function_dispatch(_diag_dispatcher)
def diag(v, k=0):
    """
    Extract a diagonal or construct a diagonal array.

    See the more detailed documentation for ``numpy.diagonal`` if you use this
    function to extract a diagonal and wish to write to the resulting array;
    whether it returns a copy or a view depends on what version of numpy you
    are using.

    Parameters
    ----------
    v : array_like
        If `v` is a 2-D array, return a copy of its `k`-th diagonal.
        If `v` is a 1-D array, return a 2-D array with `v` on the `k`-th
        diagonal.
    k : int, optional
        Diagonal in question. The default is 0. Use `k>0` for diagonals
        above the main diagonal, and `k<0` for diagonals below the main
        diagonal.

    Returns
    -------
    out : ndarray
        The extracted diagonal or constructed diagonal array.

    See Also
    --------
    diagonal : Return specified diagonals.
    diagflat : Create a 2-D array with the flattened input as a diagonal.
    trace : Sum along diagonals.
    triu : Upper triangle of an array.
    tril : Lower triangle of an array.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.arange(9).reshape((3,3))
    >>> x
    array([[0, 1, 2],
           [3, 4, 5],
           [6, 7, 8]])

    >>> np.diag(x)
    array([0, 4, 8])
    >>> np.diag(x, k=1)
    array([1, 5])
    >>> np.diag(x, k=-1)
    array([3, 7])

    >>> np.diag(np.diag(x))
    array([[0, 0, 0],
           [0, 4, 0],
           [0, 0, 8]])

    """
    v = asanyarray(v)
    s = v.shape
    if len(s) == 1:
        n = s[0] + abs(k)
        res = zeros((n, n), v.dtype)
        if k >= 0:
            i = k
        else:
            i = (-k) * n
        res[:n - k].flat[i::n + 1] = v
        return res
    elif len(s) == 2:
        return diagonal(v, k)
    else:
        raise ValueError("Input must be 1- or 2-d.")


@array_function_dispatch(_diag_dispatcher)
def diagflat(v, k=0):
    """
    Create a two-dimensional array with the flattened input as a diagonal.

    Parameters
    ----------
    v : array_like
        Input data, which is flattened and set as the `k`-th
        diagonal of the output.
    k : int, optional
        Diagonal to set; 0, the default, corresponds to the "main" diagonal,
        a positive (negative) `k` giving the number of the diagonal above
        (below) the main.

    Returns
    -------
    out : ndarray
        The 2-D output array.

    See Also
    --------
    diag : MATLAB work-alike for 1-D and 2-D arrays.
    diagonal : Return specified diagonals.
    trace : Sum along diagonals.

    Examples
    --------
    >>> import numpy as np
    >>> np.diagflat([[1,2], [3,4]])
    array([[1, 0, 0, 0],
           [0, 2, 0, 0],
           [0, 0, 3, 0],
           [0, 0, 0, 4]])

    >>> np.diagflat([1,2], 1)
    array([[0, 1, 0],
           [0, 0, 2],
           [0, 0, 0]])

    """
    conv = _array_converter(v)
    v, = conv.as_arrays(subok=False)
    v = v.ravel()
    s = len(v)
    n = s + abs(k)
    res = zeros((n, n), v.dtype)
    if (k >= 0):
        i = arange(0, n - k, dtype=intp)
        fi = i + k + i * n
    else:
        i = arange(0, n + k, dtype=intp)
        fi = i + (i - k) * n
    res.flat[fi] = v

    return conv.wrap(res)


@finalize_array_function_like
@set_module('numpy')
def tri(N, M=None, k=0, dtype=float, *, like=None):
    """
    An array with ones at and below the given diagonal and zeros elsewhere.

    Parameters
    ----------
    N : int
        Number of rows in the array.
    M : int, optional
        Number of columns in the array.
        By default, `M` is taken equal to `N`.
    k : int, optional
        The sub-diagonal at and below which the array is filled.
        `k` = 0 is the main diagonal, while `k` < 0 is below it,
        and `k` > 0 is above.  The default is 0.
    dtype : dtype, optional
        Data type of the returned array.  The default is float.
    ${ARRAY_FUNCTION_LIKE}

        .. versionadded:: 1.20.0

    Returns
    -------
    tri : ndarray of shape (N, M)
        Array with its lower triangle filled with ones and zero elsewhere;
        in other words ``T[i,j] == 1`` for ``j <= i + k``, 0 otherwise.

    Examples
    --------
    >>> import numpy as np
    >>> np.tri(3, 5, 2, dtype=int)
    array([[1, 1, 1, 0, 0],
           [1, 1, 1, 1, 0],
           [1, 1, 1, 1, 1]])

    >>> np.tri(3, 5, -1)
    array([[0.,  0.,  0.,  0.,  0.],
           [1.,  0.,  0.,  0.,  0.],
           [1.,  1.,  0.,  0.,  0.]])

    """
    if like is not None:
        return _tri_with_like(like, N, M=M, k=k, dtype=dtype)

    if M is None:
        M = N

    m = greater_equal.outer(arange(N, dtype=_min_int(0, N)),
                            arange(-k, M - k, dtype=_min_int(-k, M - k)))

    # Avoid making a copy if the requested type is already bool
    m = m.astype(dtype, copy=False)

    return m


_tri_with_like = array_function_dispatch()(tri)


def _trilu_dispatcher(m, k=None):
    return (m,)


@array_function_dispatch(_trilu_dispatcher)
def tril(m, k=0):
    """
    Lower triangle of an array.

    Return a copy of an array with elements above the `k`-th diagonal zeroed.
    For arrays with ``ndim`` exceeding 2, `tril` will apply to the final two
    axes.

    Parameters
    ----------
    m : array_like, shape (..., M, N)
        Input array.
    k : int, optional
        Diagonal above which to zero elements.  `k = 0` (the default) is the
        main diagonal, `k < 0` is below it and `k > 0` is above.

    Returns
    -------
    tril : ndarray, shape (..., M, N)
        Lower triangle of `m`, of same shape and data-type as `m`.

    See Also
    --------
    triu : same thing, only for the upper triangle

    Examples
    --------
    >>> import numpy as np
    >>> np.tril([[1,2,3],[4,5,6],[7,8,9],[10,11,12]], -1)
    array([[ 0,  0,  0],
           [ 4,  0,  0],
           [ 7,  8,  0],
           [10, 11, 12]])

    >>> np.tril(np.arange(3*4*5).reshape(3, 4, 5))
    array([[[ 0,  0,  0,  0,  0],
            [ 5,  6,  0,  0,  0],
            [10, 11, 12,  0,  0],
            [15, 16, 17, 18,  0]],
           [[20,  0,  0,  0,  0],
            [25, 26,  0,  0,  0],
            [30, 31, 32,  0,  0],
            [35, 36, 37, 38,  0]],
           [[40,  0,  0,  0,  0],
            [45, 46,  0,  0,  0],
            [50, 51, 52,  0,  0],
            [55, 56, 57, 58,  0]]])

    """
    m = asanyarray(m)
    mask = tri(*m.shape[-2:], k=k, dtype=bool)

    return where(mask, m, zeros(1, m.dtype))


@array_function_dispatch(_trilu_dispatcher)
def triu(m, k=0):
    """
    Upper triangle of an array.

    Return a copy of an array with the elements below the `k`-th diagonal
    zeroed. For arrays with ``ndim`` exceeding 2, `triu` will apply to the
    final two axes.

    Please refer to the documentation for `tril` for further details.

    See Also
    --------
    tril : lower triangle of an array

    Examples
    --------
    >>> import numpy as np
    >>> np.triu([[1,2,3],[4,5,6],[7,8,9],[10,11,12]], -1)
    array([[ 1,  2,  3],
           [ 4,  5,  6],
           [ 0,  8,  9],
           [ 0,  0, 12]])

    >>> np.triu(np.arange(3*4*5).reshape(3, 4, 5))
    array([[[ 0,  1,  2,  3,  4],
            [ 0,  6,  7,  8,  9],
            [ 0,  0, 12, 13, 14],
            [ 0,  0,  0, 18, 19]],
           [[20, 21, 22, 23, 24],
            [ 0, 26, 27, 28, 29],
            [ 0,  0, 32, 33, 34],
            [ 0,  0,  0, 38, 39]],
           [[40, 41, 42, 43, 44],
            [ 0, 46, 47, 48, 49],
            [ 0,  0, 52, 53, 54],
            [ 0,  0,  0, 58, 59]]])

    """
    m = asanyarray(m)
    mask = tri(*m.shape[-2:], k=k - 1, dtype=bool)

    return where(mask, zeros(1, m.dtype), m)


def _vander_dispatcher(x, N=None, increasing=None):
    return (x,)


# Originally borrowed from John Hunter and matplotlib
@array_function_dispatch(_vander_dispatcher)
def vander(x, N=None, increasing=False):
    """
    Generate a Vandermonde matrix.

    The columns of the output matrix are powers of the input vector. The
    order of the powers is determined by the `increasing` boolean argument.
    Specifically, when `increasing` is False, the `i`-th output column is
    the input vector raised element-wise to the power of ``N - i - 1``. Such
    a matrix with a geometric progression in each row is named for Alexandre-
    Theophile Vandermonde.

    Parameters
    ----------
    x : array_like
        1-D input array.
    N : int, optional
        Number of columns in the output.  If `N` is not specified, a square
        array is returned (``N = len(x)``).
    increasing : bool, optional
        Order of the powers of the columns.  If True, the powers increase
        from left to right, if False (the default) they are reversed.

    Returns
    -------
    out : ndarray
        Vandermonde matrix.  If `increasing` is False, the first column is
        ``x^(N-1)``, the second ``x^(N-2)`` and so forth. If `increasing` is
        True, the columns are ``x^0, x^1, ..., x^(N-1)``.

    See Also
    --------
    polynomial.polynomial.polyvander

    Examples
    --------
    >>> import numpy as np
    >>> x = np.array([1, 2, 3, 5])
    >>> N = 3
    >>> np.vander(x, N)
    array([[ 1,  1,  1],
           [ 4,  2,  1],
           [ 9,  3,  1],
           [25,  5,  1]])

    >>> np.column_stack([x**(N-1-i) for i in range(N)])
    array([[ 1,  1,  1],
           [ 4,  2,  1],
           [ 9,  3,  1],
           [25,  5,  1]])

    >>> x = np.array([1, 2, 3, 5])
    >>> np.vander(x)
    array([[  1,   1,   1,   1],
           [  8,   4,   2,   1],
           [ 27,   9,   3,   1],
           [125,  25,   5,   1]])
    >>> np.vander(x, increasing=True)
    array([[  1,   1,   1,   1],
           [  1,   2,   4,   8],
           [  1,   3,   9,  27],
           [  1,   5,  25, 125]])

    The determinant of a square Vandermonde matrix is the product
    of the differences between the values of the input vector:

    >>> np.linalg.det(np.vander(x))
    48.000000000000043 # may vary
    >>> (5-3)*(5-2)*(5-1)*(3-2)*(3-1)*(2-1)
    48

    """
    x = asarray(x)
    if x.ndim != 1:
        raise ValueError("x must be a one-dimensional array or sequence.")
    if N is None:
        N = len(x)

    v = empty((len(x), N), dtype=promote_types(x.dtype, int))
    tmp = v[:, ::-1] if not increasing else v

    if N > 0:
        tmp[:, 0] = 1
    if N > 1:
        tmp[:, 1:] = x[:, None]
        multiply.accumulate(tmp[:, 1:], out=tmp[:, 1:], axis=1)

    return v


def _histogram2d_dispatcher(x, y, bins=None, range=None, density=None,
                            weights=None):
    yield x
    yield y

    # This terrible logic is adapted from the checks in histogram2d
    try:
        N = len(bins)
    except TypeError:
        N = 1
    if N == 2:
        yield from bins  # bins=[x, y]
    else:
        yield bins

    yield weights


@array_function_dispatch(_histogram2d_dispatcher)
def histogram2d(x, y, bins=10, range=None, density=None, weights=None):
    """
    Compute the bi-dimensional histogram of two data samples.

    Parameters
    ----------
    x : array_like, shape (N,)
        An array containing the x coordinates of the points to be
        histogrammed.
    y : array_like, shape (N,)
        An array containing the y coordinates of the points to be
        histogrammed.
    bins : int or array_like or [int, int] or [array, array], optional
        The bin specification:

        * If int, the number of bins for the two dimensions (nx=ny=bins).
        * If array_like, the bin edges for the two dimensions
          (x_edges=y_edges=bins).
        * If [int, int], the number of bins in each dimension
          (nx, ny = bins).
        * If [array, array], the bin edges in each dimension
          (x_edges, y_edges = bins).
        * A combination [int, array] or [array, int], where int
          is the number of bins and array is the bin edges.

    range : array_like, shape(2,2), optional
        The leftmost and rightmost edges of the bins along each dimension
        (if not specified explicitly in the `bins` parameters):
        ``[[xmin, xmax], [ymin, ymax]]``. All values outside of this range
        will be considered outliers and not tallied in the histogram.
    density : bool, optional
        If False, the default, returns the number of samples in each bin.
        If True, returns the probability *density* function at the bin,
        ``bin_count / sample_count / bin_area``.
    weights : array_like, shape(N,), optional
        An array of values ``w_i`` weighing each sample ``(x_i, y_i)``.
        Weights are normalized to 1 if `density` is True. If `density` is
        False, the values of the returned histogram are equal to the sum of
        the weights belonging to the samples falling into each bin.

    Returns
    -------
    H : ndarray, shape(nx, ny)
        The bi-dimensional histogram of samples `x` and `y`. Values in `x`
        are histogrammed along the first dimension and values in `y` are
        histogrammed along the second dimension.
    xedges : ndarray, shape(nx+1,)
        The bin edges along the first dimension.
    yedges : ndarray, shape(ny+1,)
        The bin edges along the second dimension.

    See Also
    --------
    histogram : 1D histogram
    histogramdd : Multidimensional histogram

    Notes
    -----
    When `density` is True, then the returned histogram is the sample
    density, defined such that the sum over bins of the product
    ``bin_value * bin_area`` is 1.

    Please note that the histogram does not follow the Cartesian convention
    where `x` values are on the abscissa and `y` values on the ordinate
    axis.  Rather, `x` is histogrammed along the first dimension of the
    array (vertical), and `y` along the second dimension of the array
    (horizontal).  This ensures compatibility with `histogramdd`.

    Examples
    --------
    >>> import numpy as np
    >>> from matplotlib.image import NonUniformImage
    >>> import matplotlib.pyplot as plt

    Construct a 2-D histogram with variable bin width. First define the bin
    edges:

    >>> xedges = [0, 1, 3, 5]
    >>> yedges = [0, 2, 3, 4, 6]

    Next we create a histogram H with random bin content:

    >>> x = np.random.normal(2, 1, 100)
    >>> y = np.random.normal(1, 1, 100)
    >>> H, xedges, yedges = np.histogram2d(x, y, bins=(xedges, yedges))
    >>> # Histogram does not follow Cartesian convention (see Notes),
    >>> # therefore transpose H for visualization purposes.
    >>> H = H.T

    :func:`imshow <matplotlib.pyplot.imshow>` can only display square bins:

    >>> fig = plt.figure(figsize=(7, 3))
    >>> ax = fig.add_subplot(131, title='imshow: square bins')
    >>> plt.imshow(H, interpolation='nearest', origin='lower',
    ...         extent=[xedges[0], xedges[-1], yedges[0], yedges[-1]])
    <matplotlib.image.AxesImage object at 0x...>

    :func:`pcolormesh <matplotlib.pyplot.pcolormesh>` can display actual edges:

    >>> ax = fig.add_subplot(132, title='pcolormesh: actual edges',
    ...         aspect='equal')
    >>> X, Y = np.meshgrid(xedges, yedges)
    >>> ax.pcolormesh(X, Y, H)
    <matplotlib.collections.QuadMesh object at 0x...>

    :class:`NonUniformImage <matplotlib.image.NonUniformImage>` can be used to
    display actual bin edges with interpolation:

    >>> ax = fig.add_subplot(133, title='NonUniformImage: interpolated',
    ...         aspect='equal', xlim=xedges[[0, -1]], ylim=yedges[[0, -1]])
    >>> im = NonUniformImage(ax, interpolation='bilinear')
    >>> xcenters = (xedges[:-1] + xedges[1:]) / 2
    >>> ycenters = (yedges[:-1] + yedges[1:]) / 2
    >>> im.set_data(xcenters, ycenters, H)
    >>> ax.add_image(im)
    >>> plt.show()

    It is also possible to construct a 2-D histogram without specifying bin
    edges:

    >>> # Generate non-symmetric test data
    >>> n = 10000
    >>> x = np.linspace(1, 100, n)
    >>> y = 2*np.log(x) + np.random.rand(n) - 0.5
    >>> # Compute 2d histogram. Note the order of x/y and xedges/yedges
    >>> H, yedges, xedges = np.histogram2d(y, x, bins=20)

    Now we can plot the histogram using
    :func:`pcolormesh <matplotlib.pyplot.pcolormesh>`, and a
    :func:`hexbin <matplotlib.pyplot.hexbin>` for comparison.

    >>> # Plot histogram using pcolormesh
    >>> fig, (ax1, ax2) = plt.subplots(ncols=2, sharey=True)
    >>> ax1.pcolormesh(xedges, yedges, H, cmap='rainbow')
    >>> ax1.plot(x, 2*np.log(x), 'k-')
    >>> ax1.set_xlim(x.min(), x.max())
    >>> ax1.set_ylim(y.min(), y.max())
    >>> ax1.set_xlabel('x')
    >>> ax1.set_ylabel('y')
    >>> ax1.set_title('histogram2d')
    >>> ax1.grid()

    >>> # Create hexbin plot for comparison
    >>> ax2.hexbin(x, y, gridsize=20, cmap='rainbow')
    >>> ax2.plot(x, 2*np.log(x), 'k-')
    >>> ax2.set_title('hexbin')
    >>> ax2.set_xlim(x.min(), x.max())
    >>> ax2.set_xlabel('x')
    >>> ax2.grid()

    >>> plt.show()
    """
    from numpy import histogramdd

    if len(x) != len(y):
        raise ValueError('x and y must have the same length.')

    try:
        N = len(bins)
    except TypeError:
        N = 1

    if N not in {1, 2}:
        xedges = yedges = asarray(bins)
        bins = [xedges, yedges]
    hist, edges = histogramdd([x, y], bins, range, density, weights)
    return hist, edges[0], edges[1]


@set_module('numpy')
def mask_indices(n, mask_func, k=0):
    """
    Return the indices to access (n, n) arrays, given a masking function.

    Assume `mask_func` is a function that, for a square array a of size
    ``(n, n)`` with a possible offset argument `k`, when called as
    ``mask_func(a, k)`` returns a new array with zeros in certain locations
    (functions like `triu` or `tril` do precisely this). Then this function
    returns the indices where the non-zero values would be located.

    Parameters
    ----------
    n : int
        The returned indices will be valid to access arrays of shape (n, n).
    mask_func : callable
        A function whose call signature is similar to that of `triu`, `tril`.
        That is, ``mask_func(x, k)`` returns a boolean array, shaped like `x`.
        `k` is an optional argument to the function.
    k : scalar
        An optional argument which is passed through to `mask_func`. Functions
        like `triu`, `tril` take a second argument that is interpreted as an
        offset.

    Returns
    -------
    indices : tuple of arrays.
        The `n` arrays of indices corresponding to the locations where
        ``mask_func(np.ones((n, n)), k)`` is True.

    See Also
    --------
    triu, tril, triu_indices, tril_indices

    Examples
    --------
    >>> import numpy as np

    These are the indices that would allow you to access the upper triangular
    part of any 3x3 array:

    >>> iu = np.mask_indices(3, np.triu)

    For example, if `a` is a 3x3 array:

    >>> a = np.arange(9).reshape(3, 3)
    >>> a
    array([[0, 1, 2],
           [3, 4, 5],
           [6, 7, 8]])
    >>> a[iu]
    array([0, 1, 2, 4, 5, 8])

    An offset can be passed also to the masking function.  This gets us the
    indices starting on the first diagonal right of the main one:

    >>> iu1 = np.mask_indices(3, np.triu, 1)

    with which we now extract only three elements:

    >>> a[iu1]
    array([1, 2, 5])

    """
    m = ones((n, n), int)
    a = mask_func(m, k)
    return nonzero(a != 0)


@set_module('numpy')
def tril_indices(n, k=0, m=None):
    """
    Return the indices for the lower-triangle of an (n, m) array.

    Parameters
    ----------
    n : int
        The row dimension of the arrays for which the returned
        indices will be valid.
    k : int, optional
        Diagonal offset (see `tril` for details).
    m : int, optional
        The column dimension of the arrays for which the returned
        arrays will be valid.
        By default `m` is taken equal to `n`.


    Returns
    -------
    inds : tuple of arrays
        The row and column indices, respectively. The row indices are sorted
        in non-decreasing order, and the correspdonding column indices are
        strictly increasing for each row.

    See also
    --------
    triu_indices : similar function, for upper-triangular.
    mask_indices : generic function accepting an arbitrary mask function.
    tril, triu

    Examples
    --------
    >>> import numpy as np

    Compute two different sets of indices to access 4x4 arrays, one for the
    lower triangular part starting at the main diagonal, and one starting two
    diagonals further right:

    >>> il1 = np.tril_indices(4)
    >>> il1
    (array([0, 1, 1, 2, 2, 2, 3, 3, 3, 3]), array([0, 0, 1, 0, 1, 2, 0, 1, 2, 3]))

    Note that row indices (first array) are non-decreasing, and the corresponding
    column indices (second array) are strictly increasing for each row.
    Here is how they can be used with a sample array:

    >>> a = np.arange(16).reshape(4, 4)
    >>> a
    array([[ 0,  1,  2,  3],
           [ 4,  5,  6,  7],
           [ 8,  9, 10, 11],
           [12, 13, 14, 15]])

    Both for indexing:

    >>> a[il1]
    array([ 0,  4,  5, ..., 13, 14, 15])

    And for assigning values:

    >>> a[il1] = -1
    >>> a
    array([[-1,  1,  2,  3],
           [-1, -1,  6,  7],
           [-1, -1, -1, 11],
           [-1, -1, -1, -1]])

    These cover almost the whole array (two diagonals right of the main one):

    >>> il2 = np.tril_indices(4, 2)
    >>> a[il2] = -10
    >>> a
    array([[-10, -10, -10,   3],
           [-10, -10, -10, -10],
           [-10, -10, -10, -10],
           [-10, -10, -10, -10]])

    """
    tri_ = tri(n, m, k=k, dtype=bool)

    return tuple(broadcast_to(inds, tri_.shape)[tri_]
                 for inds in indices(tri_.shape, sparse=True))


def _trilu_indices_form_dispatcher(arr, k=None):
    return (arr,)


@array_function_dispatch(_trilu_indices_form_dispatcher)
def tril_indices_from(arr, k=0):
    """
    Return the indices for the lower-triangle of arr.

    See `tril_indices` for full details.

    Parameters
    ----------
    arr : array_like
        The indices will be valid for square arrays whose dimensions are
        the same as arr.
    k : int, optional
        Diagonal offset (see `tril` for details).

    Examples
    --------
    >>> import numpy as np

    Create a 4 by 4 array

    >>> a = np.arange(16).reshape(4, 4)
    >>> a
    array([[ 0,  1,  2,  3],
           [ 4,  5,  6,  7],
           [ 8,  9, 10, 11],
           [12, 13, 14, 15]])

    Pass the array to get the indices of the lower triangular elements.

    >>> trili = np.tril_indices_from(a)
    >>> trili
    (array([0, 1, 1, 2, 2, 2, 3, 3, 3, 3]), array([0, 0, 1, 0, 1, 2, 0, 1, 2, 3]))

    >>> a[trili]
    array([ 0,  4,  5,  8,  9, 10, 12, 13, 14, 15])

    This is syntactic sugar for tril_indices().

    >>> np.tril_indices(a.shape[0])
    (array([0, 1, 1, 2, 2, 2, 3, 3, 3, 3]), array([0, 0, 1, 0, 1, 2, 0, 1, 2, 3]))

    Use the `k` parameter to return the indices for the lower triangular array
    up to the k-th diagonal.

    >>> trili1 = np.tril_indices_from(a, k=1)
    >>> a[trili1]
    array([ 0,  1,  4,  5,  6,  8,  9, 10, 11, 12, 13, 14, 15])

    See Also
    --------
    tril_indices, tril, triu_indices_from
    """
    if arr.ndim != 2:
        raise ValueError("input array must be 2-d")
    return tril_indices(arr.shape[-2], k=k, m=arr.shape[-1])


@set_module('numpy')
def triu_indices(n, k=0, m=None):
    """
    Return the indices for the upper-triangle of an (n, m) array.

    Parameters
    ----------
    n : int
        The size of the arrays for which the returned indices will
        be valid.
    k : int, optional
        Diagonal offset (see `triu` for details).
    m : int, optional
        The column dimension of the arrays for which the returned
        arrays will be valid.
        By default `m` is taken equal to `n`.


    Returns
    -------
    inds : tuple, shape(2) of ndarrays, shape(`n`)
        The row and column indices, respectively. The row indices are sorted
        in non-decreasing order, and the correspdonding column indices are
        strictly increasing for each row.

    See also
    --------
    tril_indices : similar function, for lower-triangular.
    mask_indices : generic function accepting an arbitrary mask function.
    triu, tril

    Examples
    --------
    >>> import numpy as np

    Compute two different sets of indices to access 4x4 arrays, one for the
    upper triangular part starting at the main diagonal, and one starting two
    diagonals further right:

    >>> iu1 = np.triu_indices(4)
    >>> iu1
    (array([0, 0, 0, 0, 1, 1, 1, 2, 2, 3]), array([0, 1, 2, 3, 1, 2, 3, 2, 3, 3]))

    Note that row indices (first array) are non-decreasing, and the corresponding
    column indices (second array) are strictly increasing for each row.

    Here is how they can be used with a sample array:

    >>> a = np.arange(16).reshape(4, 4)
    >>> a
    array([[ 0,  1,  2,  3],
           [ 4,  5,  6,  7],
           [ 8,  9, 10, 11],
           [12, 13, 14, 15]])

    Both for indexing:

    >>> a[iu1]
    array([ 0,  1,  2, ..., 10, 11, 15])

    And for assigning values:

    >>> a[iu1] = -1
    >>> a
    array([[-1, -1, -1, -1],
           [ 4, -1, -1, -1],
           [ 8,  9, -1, -1],
           [12, 13, 14, -1]])

    These cover only a small part of the whole array (two diagonals right
    of the main one):

    >>> iu2 = np.triu_indices(4, 2)
    >>> a[iu2] = -10
    >>> a
    array([[ -1,  -1, -10, -10],
           [  4,  -1,  -1, -10],
           [  8,   9,  -1,  -1],
           [ 12,  13,  14,  -1]])

    """
    tri_ = ~tri(n, m, k=k - 1, dtype=bool)

    return tuple(broadcast_to(inds, tri_.shape)[tri_]
                 for inds in indices(tri_.shape, sparse=True))


@array_function_dispatch(_trilu_indices_form_dispatcher)
def triu_indices_from(arr, k=0):
    """
    Return the indices for the upper-triangle of arr.

    See `triu_indices` for full details.

    Parameters
    ----------
    arr : ndarray, shape(N, N)
        The indices will be valid for square arrays.
    k : int, optional
        Diagonal offset (see `triu` for details).

    Returns
    -------
    triu_indices_from : tuple, shape(2) of ndarray, shape(N)
        Indices for the upper-triangle of `arr`.

    Examples
    --------
    >>> import numpy as np

    Create a 4 by 4 array

    >>> a = np.arange(16).reshape(4, 4)
    >>> a
    array([[ 0,  1,  2,  3],
           [ 4,  5,  6,  7],
           [ 8,  9, 10, 11],
           [12, 13, 14, 15]])

    Pass the array to get the indices of the upper triangular elements.

    >>> triui = np.triu_indices_from(a)
    >>> triui
    (array([0, 0, 0, 0, 1, 1, 1, 2, 2, 3]), array([0, 1, 2, 3, 1, 2, 3, 2, 3, 3]))

    >>> a[triui]
    array([ 0,  1,  2,  3,  5,  6,  7, 10, 11, 15])

    This is syntactic sugar for triu_indices().

    >>> np.triu_indices(a.shape[0])
    (array([0, 0, 0, 0, 1, 1, 1, 2, 2, 3]), array([0, 1, 2, 3, 1, 2, 3, 2, 3, 3]))

    Use the `k` parameter to return the indices for the upper triangular array
    from the k-th diagonal.

    >>> triuim1 = np.triu_indices_from(a, k=1)
    >>> a[triuim1]
    array([ 1,  2,  3,  6,  7, 11])


    See Also
    --------
    triu_indices, triu, tril_indices_from
    """
    if arr.ndim != 2:
        raise ValueError("input array must be 2-d")
    return triu_indices(arr.shape[-2], k=k, m=arr.shape[-1])

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\win32\lib\win32timezone.py ===
"""
win32timezone:
    Module for handling datetime.tzinfo time zones using the windows
registry for time zone information.  The time zone names are dependent
on the registry entries defined by the operating system.

    This module may be tested using the doctest module.

    Written by Jason R. Coombs (jaraco@jaraco.com).
    Copyright © 2003-2012.
    All Rights Reserved.

    This module is licenced for use in Mark Hammond's pywin32
library under the same terms as the pywin32 library.

    To use this time zone module with the datetime module, simply pass
the TimeZoneInfo object to the datetime constructor.  For example,

>>> import win32timezone, datetime
>>> assert 'Mountain Standard Time' in win32timezone.TimeZoneInfo.get_sorted_time_zone_names()
>>> MST = win32timezone.TimeZoneInfo('Mountain Standard Time')
>>> now = datetime.datetime.now(MST)

    The now object is now a time-zone aware object, and daylight savings-
aware methods may be called on it.

>>> now.utcoffset() in (datetime.timedelta(-1, 61200), datetime.timedelta(-1, 64800))
True

(note that the result of utcoffset call will be different based on when now was
generated, unless standard time is always used)

>>> now = datetime.datetime.now(win32timezone.TimeZoneInfo('Mountain Standard Time', True))
>>> now.utcoffset()
datetime.timedelta(days=-1, seconds=61200)

>>> aug2 = datetime.datetime(2003, 8, 2, tzinfo = MST)
>>> tuple(aug2.utctimetuple())
(2003, 8, 2, 6, 0, 0, 5, 214, 0)
>>> nov2 = datetime.datetime(2003, 11, 25, tzinfo = MST)
>>> tuple(nov2.utctimetuple())
(2003, 11, 25, 7, 0, 0, 1, 329, 0)

To convert from one timezone to another, just use the astimezone method.

>>> aug2.isoformat()
'2003-08-02T00:00:00-06:00'
>>> aug2est = aug2.astimezone(win32timezone.TimeZoneInfo('Eastern Standard Time'))
>>> aug2est.isoformat()
'2003-08-02T02:00:00-04:00'

calling the displayName member will return the display name as set in the
registry.

>>> est = win32timezone.TimeZoneInfo('Eastern Standard Time')
>>> str(est.displayName)
'(UTC-05:00) Eastern Time (US & Canada)'

>>> gmt = win32timezone.TimeZoneInfo('GMT Standard Time', True)
>>> str(gmt.displayName)
'(UTC+00:00) Dublin, Edinburgh, Lisbon, London'

To get the complete list of available time zone keys,
>>> zones = win32timezone.TimeZoneInfo.get_all_time_zones()

If you want to get them in an order that's sorted longitudinally
>>> zones = win32timezone.TimeZoneInfo.get_sorted_time_zones()

TimeZoneInfo now supports being pickled and comparison
>>> import pickle
>>> tz = win32timezone.TimeZoneInfo('China Standard Time')
>>> tz == pickle.loads(pickle.dumps(tz))
True

It's possible to construct a TimeZoneInfo from a TimeZoneDescription
including the currently-defined zone.
>>> code, info = win32timezone.TimeZoneDefinition.current()
>>> tz = win32timezone.TimeZoneInfo(info, not code)
>>> tz == pickle.loads(pickle.dumps(tz))
True

Although it's easier to use TimeZoneInfo.local() to get the local info
>>> tz == TimeZoneInfo.local()
True

>>> aest = win32timezone.TimeZoneInfo('AUS Eastern Standard Time')
>>> est = win32timezone.TimeZoneInfo('E. Australia Standard Time')
>>> dt = datetime.datetime(2006, 11, 11, 1, 0, 0, tzinfo = aest)
>>> estdt = dt.astimezone(est)
>>> estdt.strftime('%Y-%m-%d %H:%M:%S')
'2006-11-11 00:00:00'

>>> dt = datetime.datetime(2007, 1, 12, 1, 0, 0, tzinfo = aest)
>>> estdt = dt.astimezone(est)
>>> estdt.strftime('%Y-%m-%d %H:%M:%S')
'2007-01-12 00:00:00'

>>> dt = datetime.datetime(2007, 6, 13, 1, 0, 0, tzinfo = aest)
>>> estdt = dt.astimezone(est)
>>> estdt.strftime('%Y-%m-%d %H:%M:%S')
'2007-06-13 01:00:00'

Microsoft now has a patch for handling time zones in 2007 (see
https://learn.microsoft.com/en-us/troubleshoot/windows-client/system-management-components/daylight-saving-time-help-support)

As a result, patched systems will give an incorrect result for
dates prior to the designated year except for Vista and its
successors, which have dynamic time zone support.
>>> nov2_pre_change = datetime.datetime(2003, 11, 2, tzinfo = MST)
>>> old_response = (2003, 11, 2, 7, 0, 0, 6, 306, 0)
>>> incorrect_patch_response = (2003, 11, 2, 6, 0, 0, 6, 306, 0)
>>> pre_response = nov2_pre_change.utctimetuple()
>>> pre_response in (old_response, incorrect_patch_response)
True

Furthermore, unpatched systems pre-Vista will give an incorrect
result for dates after 2007.
>>> nov2_post_change = datetime.datetime(2007, 11, 2, tzinfo = MST)
>>> incorrect_unpatched_response = (2007, 11, 2, 7, 0, 0, 4, 306, 0)
>>> new_response = (2007, 11, 2, 6, 0, 0, 4, 306, 0)
>>> post_response = nov2_post_change.utctimetuple()
>>> post_response in (new_response, incorrect_unpatched_response)
True


There is a function you can call to get some capabilities of the time
zone data.
>>> caps = GetTZCapabilities()
>>> isinstance(caps, dict)
True
>>> 'MissingTZPatch' in caps
True
>>> 'DynamicTZSupport' in caps
True

>>> both_dates_correct = (pre_response == old_response and post_response == new_response)
>>> old_dates_wrong = (pre_response == incorrect_patch_response)
>>> new_dates_wrong = (post_response == incorrect_unpatched_response)

>>> caps['DynamicTZSupport'] == both_dates_correct
True

>>> (not caps['DynamicTZSupport'] and caps['MissingTZPatch']) == new_dates_wrong
True

>>> (not caps['DynamicTZSupport'] and not caps['MissingTZPatch']) == old_dates_wrong
True

This test helps ensure language support for unicode characters
>>> x = TIME_ZONE_INFORMATION(0, 'français')


Test conversion from one time zone to another at a DST boundary
===============================================================

>>> tz_hi = TimeZoneInfo('Hawaiian Standard Time')
>>> tz_pac = TimeZoneInfo('Pacific Standard Time')
>>> time_before = datetime.datetime(2011, 11, 5, 15, 59, 59, tzinfo=tz_hi)
>>> tz_hi.utcoffset(time_before)
datetime.timedelta(days=-1, seconds=50400)
>>> tz_hi.dst(time_before)
datetime.timedelta(0)

Hawaii doesn't need dynamic TZ info
>>> getattr(tz_hi, 'dynamicInfo', None)

Here's a time that gave some trouble as reported in #3523104
because one minute later, the equivalent UTC time changes from DST
in the U.S.
>>> dt_hi = datetime.datetime(2011, 11, 5, 15, 59, 59, 0, tzinfo=tz_hi)
>>> dt_hi.timetuple()
time.struct_time(tm_year=2011, tm_mon=11, tm_mday=5, tm_hour=15, tm_min=59, tm_sec=59, tm_wday=5, tm_yday=309, tm_isdst=0)
>>> dt_hi.utctimetuple()
time.struct_time(tm_year=2011, tm_mon=11, tm_mday=6, tm_hour=1, tm_min=59, tm_sec=59, tm_wday=6, tm_yday=310, tm_isdst=0)

Convert the time to pacific time.
>>> dt_pac = dt_hi.astimezone(tz_pac)
>>> dt_pac.timetuple()
time.struct_time(tm_year=2011, tm_mon=11, tm_mday=5, tm_hour=18, tm_min=59, tm_sec=59, tm_wday=5, tm_yday=309, tm_isdst=1)

Notice that the UTC time is almost 2am.
>>> dt_pac.utctimetuple()
time.struct_time(tm_year=2011, tm_mon=11, tm_mday=6, tm_hour=1, tm_min=59, tm_sec=59, tm_wday=6, tm_yday=310, tm_isdst=0)

Now do the same tests one minute later in Hawaii.
>>> time_after = datetime.datetime(2011, 11, 5, 16, 0, 0, 0, tzinfo=tz_hi)
>>> tz_hi.utcoffset(time_after)
datetime.timedelta(days=-1, seconds=50400)
>>> tz_hi.dst(time_before)
datetime.timedelta(0)

>>> dt_hi = datetime.datetime(2011, 11, 5, 16, 0, 0, 0, tzinfo=tz_hi)
>>> print(dt_hi.timetuple())
time.struct_time(tm_year=2011, tm_mon=11, tm_mday=5, tm_hour=16, tm_min=0, tm_sec=0, tm_wday=5, tm_yday=309, tm_isdst=0)
>>> print(dt_hi.utctimetuple())
time.struct_time(tm_year=2011, tm_mon=11, tm_mday=6, tm_hour=2, tm_min=0, tm_sec=0, tm_wday=6, tm_yday=310, tm_isdst=0)

According to the docs, this is what astimezone does.
>>> utc = (dt_hi - dt_hi.utcoffset()).replace(tzinfo=tz_pac)
>>> utc
datetime.datetime(2011, 11, 6, 2, 0, tzinfo=TimeZoneInfo('Pacific Standard Time'))
>>> tz_pac.fromutc(utc) == dt_hi.astimezone(tz_pac)
True
>>> tz_pac.fromutc(utc)
datetime.datetime(2011, 11, 5, 19, 0, tzinfo=TimeZoneInfo('Pacific Standard Time'))

Make sure the converted time is correct.
>>> dt_pac = dt_hi.astimezone(tz_pac)
>>> dt_pac.timetuple()
time.struct_time(tm_year=2011, tm_mon=11, tm_mday=5, tm_hour=19, tm_min=0, tm_sec=0, tm_wday=5, tm_yday=309, tm_isdst=1)
>>> dt_pac.utctimetuple()
time.struct_time(tm_year=2011, tm_mon=11, tm_mday=6, tm_hour=2, tm_min=0, tm_sec=0, tm_wday=6, tm_yday=310, tm_isdst=0)

Check some internal methods
>>> tz_pac._getStandardBias(datetime.datetime(2011, 1, 1))
datetime.timedelta(seconds=28800)
>>> tz_pac._getDaylightBias(datetime.datetime(2011, 1, 1))
datetime.timedelta(seconds=25200)

Test the offsets
>>> offset = tz_pac.utcoffset(datetime.datetime(2011, 11, 6, 2, 0))
>>> offset == datetime.timedelta(hours=-8)
True
>>> dst_offset = tz_pac.dst(datetime.datetime(2011, 11, 6, 2, 0) + offset)
>>> dst_offset == datetime.timedelta(hours=1)
True
>>> (offset + dst_offset) == datetime.timedelta(hours=-7)
True


Test offsets that occur right at the DST changeover
>>> datetime.datetime.utcfromtimestamp(1320570000).replace(
...     tzinfo=TimeZoneInfo.utc()).astimezone(tz_pac)
datetime.datetime(2011, 11, 6, 1, 0, tzinfo=TimeZoneInfo('Pacific Standard Time'))

"""

from __future__ import annotations

import datetime
import functools
import logging
import operator
import re
import struct
import winreg
from itertools import count
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Dict,
    Generator,
    Iterable,
    Mapping,
    TypeVar,
    overload,
)

import win32api

if TYPE_CHECKING:
    from _operator import _SupportsComparison

    from _typeshed import SupportsKeysAndGetItem
    from typing_extensions import Self

__author__ = "Jason R. Coombs <jaraco@jaraco.com>"

_RangeMapKT = TypeVar("_RangeMapKT", bound="_SupportsComparison")

_T = TypeVar("_T")
_VT = TypeVar("_VT")

log = logging.getLogger(__file__)


# A couple of objects for working with objects as if they were native C-type
# structures.
class _SimpleStruct:
    _fields_: ClassVar[list[tuple[str, type]]] = []  # must be overridden by subclasses

    def __init__(self, *args, **kw) -> None:
        for i, (name, typ) in enumerate(self._fields_):
            def_arg = None
            if i < len(args):
                def_arg = args[i]
            if name in kw:
                def_arg = kw[name]
            if def_arg is not None:
                if not isinstance(def_arg, tuple):
                    def_arg = (def_arg,)
            else:
                def_arg = ()
            if len(def_arg) == 1 and isinstance(def_arg[0], typ):
                # already an object of this type.
                # XXX - should copy.copy???
                def_val = def_arg[0]
            else:
                def_val = typ(*def_arg)
            setattr(self, name, def_val)

    def field_names(self) -> list[str]:
        return [f[0] for f in self._fields_]

    def __eq__(self, other) -> bool:
        if not hasattr(other, "_fields_"):
            return False
        if self._fields_ != other._fields_:
            return False
        for name, _ in self._fields_:
            if getattr(self, name) != getattr(other, name):
                return False
        return True

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)


class SYSTEMTIME(_SimpleStruct):
    _fields_ = [
        ("year", int),
        ("month", int),
        ("day_of_week", int),
        ("day", int),
        ("hour", int),
        ("minute", int),
        ("second", int),
        ("millisecond", int),
    ]


class TIME_ZONE_INFORMATION(_SimpleStruct):
    _fields_ = [
        ("bias", int),
        ("standard_name", str),
        ("standard_start", SYSTEMTIME),
        ("standard_bias", int),
        ("daylight_name", str),
        ("daylight_start", SYSTEMTIME),
        ("daylight_bias", int),
    ]


class DYNAMIC_TIME_ZONE_INFORMATION(TIME_ZONE_INFORMATION):
    _fields_ = TIME_ZONE_INFORMATION._fields_ + [
        ("key_name", str),
        ("dynamic_daylight_time_disabled", bool),
    ]


class TimeZoneDefinition(DYNAMIC_TIME_ZONE_INFORMATION):
    """
    A time zone definition class based on the win32
    DYNAMIC_TIME_ZONE_INFORMATION structure.

    Describes a bias against UTC (bias), and two dates at which a separate
    additional bias applies (standard_bias and daylight_bias).
    """

    def __init__(self, *args, **kwargs) -> None:
        """
        >>> test_args = [1] * 44

        Try to construct a TimeZoneDefinition from:

        a) [DYNAMIC_]TIME_ZONE_INFORMATION args
        >>> TimeZoneDefinition(*test_args).bias
        datetime.timedelta(seconds=60)

        b) another TimeZoneDefinition or [DYNAMIC_]TIME_ZONE_INFORMATION
        >>> TimeZoneDefinition(TimeZoneDefinition(*test_args)).bias
        datetime.timedelta(seconds=60)
        >>> TimeZoneDefinition(DYNAMIC_TIME_ZONE_INFORMATION(*test_args)).bias
        datetime.timedelta(seconds=60)
        >>> TimeZoneDefinition(TIME_ZONE_INFORMATION(*test_args)).bias
        datetime.timedelta(seconds=60)

        c) a byte structure (using _from_bytes)
        >>> TimeZoneDefinition(bytes(test_args)).bias
        datetime.timedelta(days=11696, seconds=46140)
        """
        try:
            super().__init__(*args, **kwargs)
            return
        except (TypeError, ValueError):
            pass

        try:
            self.__init_from_other(*args, **kwargs)
            return
        except TypeError:
            pass

        try:
            self.__init_from_bytes(*args, **kwargs)
            return
        except TypeError:
            pass

        raise TypeError(f"Invalid arguments for {self.__class__}")

    def __init_from_bytes(
        self,
        bytes,
        standard_name="",
        daylight_name="",
        key_name="",
        daylight_disabled=False,
    ):
        format = "3l8h8h"
        components = struct.unpack(format, bytes)
        bias, standard_bias, daylight_bias = components[:3]
        standard_start = SYSTEMTIME(*components[3:11])
        daylight_start = SYSTEMTIME(*components[11:19])
        super().__init__(
            bias,
            standard_name,
            standard_start,
            standard_bias,
            daylight_name,
            daylight_start,
            daylight_bias,
            key_name,
            daylight_disabled,
        )

    def __init_from_other(self, other: TIME_ZONE_INFORMATION) -> None:
        if not isinstance(other, TIME_ZONE_INFORMATION):
            raise TypeError("Not a TIME_ZONE_INFORMATION")
        for name in other.field_names():
            # explicitly get the value from the underlying structure
            value = super(TIME_ZONE_INFORMATION, other).__getattribute__(name)
            setattr(self, name, value)
        # consider instead of the loop above just copying the memory directly
        # size = max(ctypes.sizeof(DYNAMIC_TIME_ZONE_INFO), ctypes.sizeof(other))
        # ctypes.memmove(ctypes.addressof(self), other, size)

    if TYPE_CHECKING:
        # TIME_ZONE_INFORMATION fields as obtained by __getattribute__
        bias: datetime.timedelta
        standard_name: str
        standard_start: SYSTEMTIME
        standard_bias: datetime.timedelta
        daylight_name: str
        daylight_start: SYSTEMTIME
        daylight_bias: datetime.timedelta

    def __getattribute__(self, attr: str) -> Any:
        value = super().__getattribute__(attr)
        if "bias" in attr:
            value = datetime.timedelta(minutes=value)
        return value

    @classmethod
    def current(cls):
        "Windows Platform SDK GetTimeZoneInformation"
        code, tzi = win32api.GetTimeZoneInformation(True)
        return code, cls(*tzi)

    def set(self) -> None:
        tzi = tuple(getattr(self, n) for n, t in self._fields_)
        win32api.SetTimeZoneInformation(tzi)

    def copy(self) -> Self:
        # XXX - this is no longer a copy!
        return self.__class__(self)

    def locate_daylight_start(self, year) -> datetime.datetime:
        return self._locate_day(year, self.daylight_start)

    def locate_standard_start(self, year) -> datetime.datetime:
        return self._locate_day(year, self.standard_start)

    @staticmethod
    def _locate_day(year, cutoff) -> datetime.datetime:
        """
        Takes a SYSTEMTIME object, such as retrieved from a TIME_ZONE_INFORMATION
        structure or call to GetTimeZoneInformation and interprets it based on the given
        year to identify the actual day.

        This method is necessary because the SYSTEMTIME structure refers to a day by its
        day of the week and week of the month (e.g. 4th saturday in March).

        >>> SATURDAY = 6
        >>> MARCH = 3
        >>> st = SYSTEMTIME(2000, MARCH, SATURDAY, 4, 0, 0, 0, 0)

        # according to my calendar, the 4th Saturday in March in 2009 was the 28th
        >>> expected_date = datetime.datetime(2009, 3, 28)
        >>> TimeZoneDefinition._locate_day(2009, st) == expected_date
        True
        """
        # MS stores Sunday as 0, Python datetime stores Monday as zero
        target_weekday = (cutoff.day_of_week + 6) % 7
        # For SYSTEMTIMEs relating to time zone information, cutoff.day
        #  is the week of the month
        week_of_month = cutoff.day
        # so the following is the first day of that week
        day = (week_of_month - 1) * 7 + 1
        result = datetime.datetime(
            year,
            cutoff.month,
            day,
            cutoff.hour,
            cutoff.minute,
            cutoff.second,
            cutoff.millisecond,
        )
        # now the result is the correct week, but not necessarily the correct day of the week
        days_to_go = (target_weekday - result.weekday()) % 7
        result += datetime.timedelta(days_to_go)
        # if we selected a day in the month following the target month,
        #  move back a week or two.
        # This is necessary because Microsoft defines the fifth week in a month
        #  to be the last week in a month and adding the time delta might have
        #  pushed the result into the next month.
        while result.month == cutoff.month + 1:
            result -= datetime.timedelta(weeks=1)
        return result


class TimeZoneInfo(datetime.tzinfo):
    """
    Main class for handling Windows time zones.
    Usage:
        TimeZoneInfo(<Time Zone Standard Name>, [<Fix Standard Time>])

    If <Fix Standard Time> evaluates to True, daylight savings time is
    calculated in the same way as standard time.

    >>> tzi = TimeZoneInfo('Pacific Standard Time')
    >>> march31 = datetime.datetime(2000,3,31)

    We know that time zone definitions haven't changed from 2007
    to 2012, so regardless of whether dynamic info is available,
    there should be consistent results for these years.
    >>> subsequent_years = [march31.replace(year=year)
    ...     for year in range(2007, 2013)]
    >>> offsets = set(tzi.utcoffset(year) for year in subsequent_years)
    >>> len(offsets)
    1

    Cannot create a `TimeZoneInfo` with an invalid name.
    >>> TimeZoneInfo('Does not exist')
    Traceback (most recent call last):
    ...
    ValueError: Timezone Name 'Does not exist' not found
    >>> TimeZoneInfo(None)
    Traceback (most recent call last):
    ...
    ValueError: subkey name cannot be empty
    >>> TimeZoneInfo("")
    Traceback (most recent call last):
    ...
    ValueError: subkey name cannot be empty
    """

    # this key works for WinNT+, but not for the Win95 line.
    tzRegKey = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Time Zones"

    def __init__(
        self,
        param: str | TimeZoneDefinition,
        fix_standard_time: bool = False,
    ) -> None:
        if isinstance(param, TimeZoneDefinition):
            self._LoadFromTZI(param)
        else:
            self.timeZoneName = param
            self._LoadInfoFromKey()
        self.fixedStandardTime = fix_standard_time

    # For tzinfo pickle support
    def __getinitargs__(self) -> tuple[TimeZoneDefinition, bool]:
        return (self.staticInfo, self.fixedStandardTime)

    def _FindTimeZoneKey(self) -> _RegKeyDict:
        """Find the registry key for the time zone name (self.timeZoneName)."""
        # for multi-language compatability, match the time zone name in the
        # "Std" key of the time zone key.
        zoneNames = dict(self._get_indexed_time_zone_keys("Std"))
        # Also match the time zone key name itself, to be compatible with
        # English-based hard-coded time zones.
        timeZoneName = zoneNames.get(self.timeZoneName, self.timeZoneName)
        key = _RegKeyDict.open(winreg.HKEY_LOCAL_MACHINE, self.tzRegKey)
        try:
            result = key.subkey(timeZoneName)
        except FileNotFoundError:
            # Don't catch ValueError, keep the original error message
            raise ValueError(f"Timezone Name {timeZoneName!r} not found")
        return result

    def _LoadInfoFromKey(self) -> None:
        """Loads the information from an opened time zone registry key
        into relevant fields of this TZI object"""
        key = self._FindTimeZoneKey()
        self.displayName = key["Display"]
        self.standardName = key["Std"]
        self.daylightName = key["Dlt"]
        self.staticInfo = TimeZoneDefinition(key["TZI"])
        self._LoadDynamicInfoFromKey(key)

    def _LoadFromTZI(self, tzi: TimeZoneDefinition):
        self.timeZoneName = tzi.standard_name
        self.displayName = "Unknown"
        self.standardName = tzi.standard_name
        self.daylightName = tzi.daylight_name
        self.staticInfo = tzi

    def _LoadDynamicInfoFromKey(self, key) -> None:
        """
        >>> tzi = TimeZoneInfo('Central Standard Time')

        Here's how the RangeMap is supposed to work:
        >>> m = RangeMap(zip([2006,2007], 'BC'),
        ...     sort_params = {"reverse": True},
        ...     key_match_comparator=operator.ge)
        >>> m.get(2000, 'A')
        'A'
        >>> m[2006]
        'B'
        >>> m[2007]
        'C'
        >>> m[2008]
        'C'

        >>> m[RangeMap.last_item]
        'B'

        >>> m.get(2008, m[RangeMap.last_item])
        'C'


        Now test the dynamic info (but fallback to our simple RangeMap
        on systems that don't have dynamicInfo).

        >>> dinfo = getattr(tzi, 'dynamicInfo', m)
        >>> 2007 in dinfo
        True
        >>> 2008 in dinfo
        False
        >>> dinfo[2007] == dinfo[2008] == dinfo[2012]
        True
        """
        try:
            info = key.subkey("Dynamic DST")
        except FileNotFoundError:
            return
        del info["FirstEntry"]
        del info["LastEntry"]

        infos = [
            (int(year), TimeZoneDefinition(values)) for year, values in info.items()
        ]
        # create a range mapping that searches by descending year and matches
        # if the target year is greater or equal.
        self.dynamicInfo = RangeMap(
            infos,
            sort_params={"reverse": True},
            key_match_comparator=operator.ge,
        )

    def __repr__(self) -> str:
        result = f"{self.__class__.__name__}({self.timeZoneName!r}"
        if self.fixedStandardTime:
            result += ", True"
        result += ")"
        return result

    def __str__(self) -> str:
        return self.displayName

    @overload  # type: ignore[override] # Split definition into overrides
    def tzname(self, dt: datetime.datetime) -> str: ...
    @overload
    def tzname(self, dt: None) -> None: ...
    def tzname(self, dt: datetime.datetime | None) -> str | None:
        """
        >>> MST = TimeZoneInfo('Mountain Standard Time')
        >>> MST.tzname(datetime.datetime(2003, 8, 2))
        'Mountain Daylight Time'
        >>> MST.tzname(datetime.datetime(2003, 11, 25))
        'Mountain Standard Time'
        >>> MST.tzname(None)

        """
        # https://docs.python.org/3/library/datetime.html#datetime.tzinfo.tzname
        # > [...] returning `None` is appropriate if the class wishes to say
        # > that `time` objects don’t participate in the `tzinfo` protocols.
        if dt is None:
            return None

        dst = self.dst(dt)
        winInfo = self.getWinInfo(dt.year)
        if dst == -winInfo.daylight_bias:
            return self.daylightName
        elif dst == -winInfo.standard_bias:
            return self.standardName

        raise ValueError(
            "Unexpected daylight bias",
            dt,
            dst,
            winInfo.daylight_bias,
            winInfo.standard_bias,
        )

    def getWinInfo(self, targetYear: int) -> TimeZoneDefinition:
        """
        Return the most relevant "info" for this time zone
        in the target year.
        """
        if not getattr(self, "dynamicInfo", {}):
            return self.staticInfo
        # Find the greatest year entry in self.dynamicInfo which is for
        #  a year greater than or equal to our targetYear. If not found,
        #  default to the earliest year.
        return self.dynamicInfo.get(targetYear, self.dynamicInfo[RangeMap.last_item])

    def _getStandardBias(self, dt):
        winInfo = self.getWinInfo(dt.year)
        return winInfo.bias + winInfo.standard_bias

    def _getDaylightBias(self, dt):
        winInfo = self.getWinInfo(dt.year)
        return winInfo.bias + winInfo.daylight_bias

    @overload  # type: ignore[override] # False-positive, our overload covers all base types
    def utcoffset(self, dt: None) -> None: ...
    @overload
    def utcoffset(self, dt: datetime.datetime) -> datetime.timedelta: ...
    def utcoffset(self, dt: datetime.datetime | None) -> datetime.timedelta | None:
        "Calculates the utcoffset according to the datetime.tzinfo spec"
        if dt is None:
            return None
        winInfo = self.getWinInfo(dt.year)
        return -winInfo.bias + self.dst(dt)

    @overload  # type: ignore[override] # False-positive, our overload covers all base types
    def dst(self, dt: None) -> None: ...
    @overload
    def dst(self, dt: datetime.datetime) -> datetime.timedelta: ...
    def dst(self, dt: datetime.datetime | None) -> datetime.timedelta | None:
        """
        Calculate the daylight savings offset according to the
        datetime.tzinfo spec.
        """
        if dt is None:
            return None
        winInfo = self.getWinInfo(dt.year)
        if not self.fixedStandardTime and self._inDaylightSavings(dt):
            result = winInfo.daylight_bias
        else:
            result = winInfo.standard_bias
        return -result

    def _inDaylightSavings(self, dt):
        dt = dt.replace(tzinfo=None)
        winInfo = self.getWinInfo(dt.year)
        try:
            dstStart = self.GetDSTStartTime(dt.year)
            dstEnd = self.GetDSTEndTime(dt.year)

            # at the end of DST, when clocks are moved back, there's a period
            #  of daylight_bias where it's ambiguous whether we're in DST or
            #  not.
            dstEndAdj = dstEnd + winInfo.daylight_bias

            # the same thing could theoretically happen at the start of DST
            #  if there's a standard_bias (which I suspect is always 0).
            dstStartAdj = dstStart + winInfo.standard_bias

            if dstStart < dstEnd:
                in_dst = dstStartAdj <= dt < dstEndAdj
            else:
                # in the southern hemisphere, daylight savings time
                #  typically ends before it begins in a given year.
                in_dst = not (dstEndAdj < dt <= dstStartAdj)
        except ValueError:
            # there was an error parsing the time zone, which is normal when a
            #  start and end time are not specified.
            in_dst = False

        return in_dst

    def GetDSTStartTime(self, year: int) -> datetime.datetime:
        "Given a year, determines the time when daylight savings time starts"
        return self.getWinInfo(year).locate_daylight_start(year)

    def GetDSTEndTime(self, year: int) -> datetime.datetime:
        "Given a year, determines the time when daylight savings ends."
        return self.getWinInfo(year).locate_standard_start(year)

    def __eq__(self, other: object) -> bool:
        return self.__dict__ == other.__dict__

    def __ne__(self, other: object) -> bool:
        return self.__dict__ != other.__dict__

    @classmethod
    def local(cls) -> Self:
        """Returns the local time zone as defined by the operating system in the
        registry.
        >>> localTZ = TimeZoneInfo.local()
        >>> now_local = datetime.datetime.now(localTZ)
        >>> now_UTC = datetime.datetime.utcnow()  # deprecated
        >>> (now_UTC - now_local) < datetime.timedelta(seconds = 5)
        Traceback (most recent call last):
        ...
        TypeError: can't subtract offset-naive and offset-aware datetimes

        >>> now_UTC = now_UTC.replace(tzinfo = TimeZoneInfo('GMT Standard Time', True))

        Now one can compare the results of the two offset aware values
        >>> (now_UTC - now_local) < datetime.timedelta(seconds = 5)
        True

        Or use the newer `datetime.timezone.utc`
        >>> now_UTC = datetime.datetime.now(datetime.timezone.utc)
        >>> (now_UTC - now_local) < datetime.timedelta(seconds = 5)
        True
        """
        code, info = TimeZoneDefinition.current()
        # code is 0 if daylight savings is disabled or not defined
        #  code is 1 or 2 if daylight savings is enabled, 2 if currently active
        fix_standard_time = not code
        # note that although the given information is sufficient
        # to construct a WinTZI object, it's
        # not sufficient to represent the time zone in which
        # the current user is operating due
        # to dynamic time zones.
        return cls(info, fix_standard_time)

    _tzutc: ClassVar[Self | None] = None

    @classmethod
    def utc(cls) -> Self:
        """Returns a time-zone representing UTC.

        Same as TimeZoneInfo('GMT Standard Time', True) but caches the result
        for performance.

        >>> isinstance(TimeZoneInfo.utc(), TimeZoneInfo)
        True
        """
        if not cls._tzutc:
            cls._tzutc = cls("GMT Standard Time", True)
        return cls._tzutc

    # helper methods for accessing the timezone info from the registry
    @staticmethod
    def _get_time_zone_key(subkey=None):
        "Return the registry key that stores time zone details"
        key = _RegKeyDict.open(winreg.HKEY_LOCAL_MACHINE, TimeZoneInfo.tzRegKey)
        if subkey:
            key = key.subkey(subkey)
        return key

    @staticmethod
    def _get_time_zone_key_names():
        "Returns the names of the (registry keys of the) time zones"
        return TimeZoneInfo._get_time_zone_key().subkeys()

    @staticmethod
    def _get_indexed_time_zone_keys(index_key="Index"):
        """
        Get the names of the registry keys indexed by a value in that key,
        ignoring any keys for which that value is empty or missing.
        """
        key_names = list(TimeZoneInfo._get_time_zone_key_names())

        def get_index_value(key_name):
            key = TimeZoneInfo._get_time_zone_key(key_name)
            return key.get(index_key)

        values = map(get_index_value, key_names)

        return (
            (value, key_name) for value, key_name in zip(values, key_names) if value
        )

    @staticmethod
    def get_sorted_time_zone_names() -> list[str]:
        """
        Return a list of time zone names that can
        be used to initialize TimeZoneInfo instances.
        """
        tzs = TimeZoneInfo.get_sorted_time_zones()
        return [tz.standardName for tz in tzs]

    @staticmethod
    def get_all_time_zones() -> list[TimeZoneInfo]:
        return [TimeZoneInfo(n) for n in TimeZoneInfo._get_time_zone_key_names()]

    @staticmethod
    def get_sorted_time_zones(key=None) -> list[TimeZoneInfo]:
        """
        Return the time zones sorted by some key.
        key must be a function that takes a TimeZoneInfo object and returns
        a value suitable for sorting on.
        The key defaults to the bias (descending), as is done in Windows
        (see https://web.archive.org/web/20130723075340/http://blogs.msdn.com/b/michkap/archive/2006/12/22/1350684.aspx)
        """
        key = key or (lambda tzi: -tzi.staticInfo.bias)
        zones = TimeZoneInfo.get_all_time_zones()
        zones.sort(key=key)
        return zones


class _RegKeyDict(Dict[str, str]):
    def __init__(self, key: winreg._KeyType):
        dict.__init__(self)
        self.key = key
        self.__load_values()

    @classmethod
    def open(
        cls, key: winreg._KeyType, sub_key: str, reserved: int = 0, access: int = 131097
    ) -> _RegKeyDict:
        return _RegKeyDict(winreg.OpenKeyEx(key, sub_key, reserved, access))

    def subkey(self, name: str) -> _RegKeyDict:
        if not name:
            raise ValueError("subkey name cannot be empty")
        return _RegKeyDict(winreg.OpenKeyEx(self.key, name))

    def __load_values(self):
        pairs = [(n, v) for (n, v, t) in self._enumerate_reg_values(self.key)]
        self.update(pairs)

    def subkeys(self):
        return self._enumerate_reg_keys(self.key)

    @staticmethod
    def _enumerate_reg_values(key):
        return _RegKeyDict._enumerate_reg(key, winreg.EnumValue)

    @staticmethod
    def _enumerate_reg_keys(key):
        return _RegKeyDict._enumerate_reg(key, winreg.EnumKey)

    @staticmethod
    def _enumerate_reg(
        key: _T, func: Callable[[_T, int], _VT]
    ) -> Generator[_VT, None, None]:
        "Enumerates an open registry key as an iterable generator"
        try:
            for index in count():
                yield func(key, index)
        except OSError:
            pass


def utcnow() -> datetime.datetime:
    """
    Return the UTC time now with timezone awareness as enabled
    by this module
    >>> now = utcnow()

    >>> (now - datetime.datetime.now(datetime.timezone.utc)) < datetime.timedelta(seconds = 5)
    True
    >>> type(now.tzinfo) is TimeZoneInfo
    True
    """
    return datetime.datetime.now(TimeZoneInfo.utc())


def now() -> datetime.datetime:
    """
    Return the local time now with timezone awareness as enabled
    by this module
    >>> now_local = now()

    >>> (now_local - datetime.datetime.now(datetime.timezone.utc)) < datetime.timedelta(seconds = 5)
    True
    >>> type(now_local.tzinfo) is TimeZoneInfo
    True
    """
    return datetime.datetime.now(TimeZoneInfo.local())


def GetTZCapabilities() -> dict[str, bool]:
    """
    Run a few known tests to determine the capabilities of
    the time zone database on this machine.
    Note Dynamic Time Zone support is not available on any
    platform at this time; this
    is a limitation of this library, not the platform."""
    tzi = TimeZoneInfo("Mountain Standard Time")
    MissingTZPatch = datetime.datetime(2007, 11, 2, tzinfo=tzi).utctimetuple() != (
        2007,
        11,
        2,
        6,
        0,
        0,
        4,
        306,
        0,
    )
    DynamicTZSupport = not MissingTZPatch and datetime.datetime(
        2003, 11, 2, tzinfo=tzi
    ).utctimetuple() == (2003, 11, 2, 7, 0, 0, 6, 306, 0)
    del tzi
    return locals()


class DLLHandleCache:
    def __init__(self) -> None:
        self.__cache: dict[str, int] = {}

    def __getitem__(self, filename: str) -> int:
        key = filename.lower()
        return self.__cache.setdefault(key, win32api.LoadLibrary(key))


DLLCache = DLLHandleCache()


def resolveMUITimeZone(spec: str) -> str | None:
    """Resolve a multilingual user interface resource for the time zone name

    spec should be of the format @path,-stringID[;comment]
    see https://learn.microsoft.com/en-ca/windows/win32/api/timezoneapi/ns-timezoneapi-time_zone_information
    for details

    >>> import sys
    >>> result = resolveMUITimeZone('@tzres.dll,-110')
    >>> expectedResultType = [type(None),str][sys.getwindowsversion() >= (6,)]
    >>> type(result) is expectedResultType
    True
    """
    pattern = re.compile(r"@(?P<dllname>.*),-(?P<index>\d+)(?:;(?P<comment>.*))?")
    matcher = pattern.match(spec)
    assert matcher, "Could not parse MUI spec"

    groupdict = matcher.groupdict()
    try:
        handle = DLLCache[groupdict["dllname"]]
        result: str | None = win32api.LoadString(handle, int(groupdict["index"]))
    except win32api.error:
        result = None
    return result


# from jaraco.collections 5.1
class RangeMap(Dict[_RangeMapKT, _VT]):
    """
    A dictionary-like object that uses the keys as bounds for a range.
    Inclusion of the value for that range is determined by the
    key_match_comparator, which defaults to less-than-or-equal.
    A value is returned for a key if it is the first key that matches in
    the sorted list of keys.

    One may supply keyword parameters to be passed to the sort function used
    to sort keys (i.e. key, reverse) as sort_params.

    Create a map that maps 1-3 -> 'a', 4-6 -> 'b'

    >>> r = RangeMap({3: 'a', 6: 'b'})  # boy, that was easy
    >>> r[1], r[2], r[3], r[4], r[5], r[6]
    ('a', 'a', 'a', 'b', 'b', 'b')

    Even float values should work so long as the comparison operator
    supports it.

    >>> r[4.5]
    'b'

    Notice that the way rangemap is defined, it must be open-ended
    on one side.

    >>> r[0]
    'a'
    >>> r[-1]
    'a'

    One can close the open-end of the RangeMap by using undefined_value

    >>> r = RangeMap({0: RangeMap.undefined_value, 3: 'a', 6: 'b'})
    >>> r[0]
    Traceback (most recent call last):
    ...
    KeyError: 0

    One can get the first or last elements in the range by using RangeMap.Item

    >>> last_item = RangeMap.Item(-1)
    >>> r[last_item]
    'b'

    .last_item is a shortcut for Item(-1)

    >>> r[RangeMap.last_item]
    'b'

    Sometimes it's useful to find the bounds for a RangeMap

    >>> r.bounds()
    (0, 6)

    RangeMap supports .get(key, default)

    >>> r.get(0, 'not found')
    'not found'

    >>> r.get(7, 'not found')
    'not found'

    One often wishes to define the ranges by their left-most values,
    which requires use of sort params and a key_match_comparator.

    >>> r = RangeMap({1: 'a', 4: 'b'},
    ...     sort_params=dict(reverse=True),
    ...     key_match_comparator=operator.ge)
    >>> r[1], r[2], r[3], r[4], r[5], r[6]
    ('a', 'a', 'a', 'b', 'b', 'b')

    That wasn't nearly as easy as before, so an alternate constructor
    is provided:

    >>> r = RangeMap.left({1: 'a', 4: 'b', 7: RangeMap.undefined_value})
    >>> r[1], r[2], r[3], r[4], r[5], r[6]
    ('a', 'a', 'a', 'b', 'b', 'b')

    """

    def __init__(
        self,
        source: (
            SupportsKeysAndGetItem[_RangeMapKT, _VT] | Iterable[tuple[_RangeMapKT, _VT]]
        ),
        sort_params: Mapping[str, Any] = {},
        key_match_comparator: Callable[[_RangeMapKT, _RangeMapKT], bool] = operator.le,
    ) -> None:
        dict.__init__(self, source)
        self.sort_params = sort_params
        self.match = key_match_comparator

    @classmethod
    def left(
        cls,
        source: (
            SupportsKeysAndGetItem[_RangeMapKT, _VT] | Iterable[tuple[_RangeMapKT, _VT]]
        ),
    ) -> Self:
        return cls(
            source, sort_params={"reverse": True}, key_match_comparator=operator.ge
        )

    def __getitem__(self, item: _RangeMapKT) -> _VT:
        sorted_keys = sorted(self, **self.sort_params)
        if isinstance(item, RangeMap.Item):
            result = self.__getitem__(sorted_keys[item])
        else:
            key = self._find_first_match_(sorted_keys, item)
            result = dict.__getitem__(self, key)
            if result is RangeMap.undefined_value:
                raise KeyError(key)
        return result

    @overload  # type: ignore[override] # Signature simplified over dict and Mapping
    def get(self, key: _RangeMapKT, default: _T) -> _VT | _T: ...
    @overload
    def get(self, key: _RangeMapKT, default: None = None) -> _VT | None: ...
    def get(self, key: _RangeMapKT, default: _T | None = None) -> _VT | _T | None:
        """
        Return the value for key if key is in the dictionary, else default.
        If default is not given, it defaults to None, so that this method
        never raises a KeyError.
        """
        # Necessary to use our own __getitem__ and not dict's
        try:
            return self[key]
        except KeyError:
            return default

    def _find_first_match_(
        self, keys: Iterable[_RangeMapKT], item: _RangeMapKT
    ) -> _RangeMapKT:
        is_match = functools.partial(self.match, item)
        matches = filter(is_match, keys)
        try:
            return next(matches)
        except StopIteration:
            raise KeyError(item) from None

    def bounds(self) -> tuple[_RangeMapKT, _RangeMapKT]:
        sorted_keys = sorted(self, **self.sort_params)
        return (sorted_keys[RangeMap.first_item], sorted_keys[RangeMap.last_item])

    # some special values for the RangeMap
    undefined_value = type("RangeValueUndefined", (), {})()

    class Item(int):
        """RangeMap Item"""

    first_item = Item(0)
    last_item = Item(-1)

# === NexusCore/openenv\Lib\site-packages\nltk\app\wordfreq_app.py ===
# Natural Language Toolkit: Wordfreq Application
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Sumukh Ghodke <sghodke@csse.unimelb.edu.au>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

from matplotlib import pylab

from nltk.corpus import gutenberg
from nltk.text import Text


def plot_word_freq_dist(text):
    fd = text.vocab()

    samples = [item for item, _ in fd.most_common(50)]
    values = [fd[sample] for sample in samples]
    values = [sum(values[: i + 1]) * 100.0 / fd.N() for i in range(len(values))]
    pylab.title(text.name)
    pylab.xlabel("Samples")
    pylab.ylabel("Cumulative Percentage")
    pylab.plot(values)
    pylab.xticks(range(len(samples)), [str(s) for s in samples], rotation=90)
    pylab.show()


def app():
    t1 = Text(gutenberg.words("melville-moby_dick.txt"))
    plot_word_freq_dist(t1)


if __name__ == "__main__":
    app()

__all__ = ["app"]

# === NexusCore/src\code_interpreter\repair_module.py ===
# 📁 ファイル: repair_module.py
# 📂 場所: /src/code_interpreter/repair_module.py

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_fix(code: str, traceback: str) -> str:
    prompt = f"""
以下はユーザーが書いたPythonコードと、その実行時に発生したエラーです。
エラーの原因を推論し、修正されたコードを出力してください。

--- 元のコード ---
{code}

--- エラー内容 ---
{traceback}

--- 修正済みコード ---
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "あなたは熟練のPythonエンジニアです。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"GPT修正エラー: {e}")
        return code  # フェイルセーフ：元コードを返す

# === NexusCore/src\gradio_app\streamlit_migrated_tab.py ===
# src/gradio_app/streamlit_migrated_tab.py

import gradio as gr
import os
from whisper_handler import transcribe_audio
from modules.chat_handler import handle_chat  # ✅ モジュールから読み込み

def tab_streamlit_port():
    with gr.Blocks() as tab:
        gr.Markdown("### 📤 音声ファイルアップロード → Whisper文字起こし → GPTチャット対応")

        with gr.Row():
            audio_input = gr.Audio(label="🎧 音声ファイルアップロード", type="filepath")
            transcript_box = gr.Textbox(label="📝 Whisper文字起こし結果", lines=2)
            transcribe_btn = gr.Button("🗣 Whisper文字起こし")

        with gr.Row():
            user_input = gr.Textbox(label="💬 GPTへの質問", lines=2)
            chat_output = gr.Textbox(label="🤖 GPT応答", lines=10)
            send_btn = gr.Button("📨 送信")

        state = gr.State([])

        transcribe_btn.click(
            fn=lambda audio: transcribe_audio(audio) if audio else "⚠️ 音声ファイルが未指定です",
            inputs=audio_input,
            outputs=transcript_box
        )

        send_btn.click(
            fn=handle_chat,
            inputs=[user_input, state],
            outputs=[chat_output, state]
        )

    return tab

# === NexusCore/src\modules\tester.py ===
# modules/tester.py

import os
import subprocess

SANDBOX_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sandbox_output"))
SAMPLE_FILE = os.path.join(SANDBOX_DIR, "sample.py")
TEST_FILE = os.path.join(SANDBOX_DIR, "test_sample.py")
RESULT_LOG = os.path.join(SANDBOX_DIR, "test_result.log")

# 保存＋pytest実行
def save_and_test_code(code: str) -> str:
    os.makedirs(SANDBOX_DIR, exist_ok=True)

    with open(SAMPLE_FILE, "w", encoding="utf-8") as f:
        f.write(code)

    if not os.path.exists(TEST_FILE):
        with open(TEST_FILE, "w", encoding="utf-8") as f:
            f.write("""import sample

def test_dummy():
    assert hasattr(sample, '__doc__')  # ダミー
""")

    try:
        result = subprocess.run(["pytest", TEST_FILE],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True)
        output = result.stdout + "\n" + result.stderr
        with open(RESULT_LOG, "w", encoding="utf-8") as f:
            f.write(output)
        return output
    except Exception as e:
        return f"⚠️ Test failed: {e}"

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\nltk\app\wordfreq_app.py ===
# Natural Language Toolkit: Wordfreq Application
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Sumukh Ghodke <sghodke@csse.unimelb.edu.au>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

from matplotlib import pylab

from nltk.corpus import gutenberg
from nltk.text import Text


def plot_word_freq_dist(text):
    fd = text.vocab()

    samples = [item for item, _ in fd.most_common(50)]
    values = [fd[sample] for sample in samples]
    values = [sum(values[: i + 1]) * 100.0 / fd.N() for i in range(len(values))]
    pylab.title(text.name)
    pylab.xlabel("Samples")
    pylab.ylabel("Cumulative Percentage")
    pylab.plot(values)
    pylab.xticks(range(len(samples)), [str(s) for s in samples], rotation=90)
    pylab.show()


def app():
    t1 = Text(gutenberg.words("melville-moby_dick.txt"))
    plot_word_freq_dist(t1)


if __name__ == "__main__":
    app()

__all__ = ["app"]

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\code_interpreter\repair_module.py ===
# 📁 ファイル: repair_module.py
# 📂 場所: /src/code_interpreter/repair_module.py

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_fix(code: str, traceback: str) -> str:
    prompt = f"""
以下はユーザーが書いたPythonコードと、その実行時に発生したエラーです。
エラーの原因を推論し、修正されたコードを出力してください。

--- 元のコード ---
{code}

--- エラー内容 ---
{traceback}

--- 修正済みコード ---
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "あなたは熟練のPythonエンジニアです。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"GPT修正エラー: {e}")
        return code  # フェイルセーフ：元コードを返す

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\gradio_app\streamlit_migrated_tab.py ===
# src/gradio_app/streamlit_migrated_tab.py

import gradio as gr
import os
from whisper_handler import transcribe_audio
from modules.chat_handler import handle_chat  # ✅ モジュールから読み込み

def tab_streamlit_port():
    with gr.Blocks() as tab:
        gr.Markdown("### 📤 音声ファイルアップロード → Whisper文字起こし → GPTチャット対応")

        with gr.Row():
            audio_input = gr.Audio(label="🎧 音声ファイルアップロード", type="filepath")
            transcript_box = gr.Textbox(label="📝 Whisper文字起こし結果", lines=2)
            transcribe_btn = gr.Button("🗣 Whisper文字起こし")

        with gr.Row():
            user_input = gr.Textbox(label="💬 GPTへの質問", lines=2)
            chat_output = gr.Textbox(label="🤖 GPT応答", lines=10)
            send_btn = gr.Button("📨 送信")

        state = gr.State([])

        transcribe_btn.click(
            fn=lambda audio: transcribe_audio(audio) if audio else "⚠️ 音声ファイルが未指定です",
            inputs=audio_input,
            outputs=transcript_box
        )

        send_btn.click(
            fn=handle_chat,
            inputs=[user_input, state],
            outputs=[chat_output, state]
        )

    return tab

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\modules\tester.py ===
# modules/tester.py

import os
import subprocess

SANDBOX_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sandbox_output"))
SAMPLE_FILE = os.path.join(SANDBOX_DIR, "sample.py")
TEST_FILE = os.path.join(SANDBOX_DIR, "test_sample.py")
RESULT_LOG = os.path.join(SANDBOX_DIR, "test_result.log")

# 保存＋pytest実行
def save_and_test_code(code: str) -> str:
    os.makedirs(SANDBOX_DIR, exist_ok=True)

    with open(SAMPLE_FILE, "w", encoding="utf-8") as f:
        f.write(code)

    if not os.path.exists(TEST_FILE):
        with open(TEST_FILE, "w", encoding="utf-8") as f:
            f.write("""import sample

def test_dummy():
    assert hasattr(sample, '__doc__')  # ダミー
""")

    try:
        result = subprocess.run(["pytest", TEST_FILE],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True)
        output = result.stdout + "\n" + result.stderr
        with open(RESULT_LOG, "w", encoding="utf-8") as f:
            f.write(output)
        return output
    except Exception as e:
        return f"⚠️ Test failed: {e}"

# === NexusCore/src\agents\coder_agent.py ===
# ==============================================================================
# フォルダ: src/agents
# ファイル名: coder_agent.py
# ==============================================================================
from .base_agent import BaseAgent

class CoderAgent(BaseAgent):
    SYSTEM_PROMPT = "あなたは、クリーンで効率的なコードを書くことを得意とする、世界クラスのPython開発者です。あなたの唯一の仕事は、与えられた指示に基づき、完全に動作するPythonコードを生成することです。"

    def implement_code(self, task_description: str, existing_code: str) -> str:
        # ★★★★★ ここからが最重要修正ポイント ★★★★★
        # AIが混乱しないよう、プロンプトを構造化し、厳格な出力ルールを課します。
        prompt = f"""
# 既存のコード
```python
{existing_code}
```

# あなたへの指示
上記の既存コードに対して、以下のタスクを実装してください。

## タスク内容
「{task_description}」

# 重要：
もしタスク内容に `[Orchestratorからの具体的指示]` や `[Guardianからのフィードバック]` が含まれている場合は、元のタスクよりも、そのフィードバックの内容を解決することを最優先してください。

# 絶対的な出力ルール
- **修正後の完全なPythonコードのみ**を出力してください。
- コードの前に前置きや言い訳、後に結びの言葉や要約など、**コード以外のテキストは一切含めないでください。**
- あなたの思考プロセスや解釈を、Pythonのコメント（`#`）以外でコードに含めてはなりません。
- 出力は、そのまま `.py` ファイルとして保存できる、純粋なPythonコードでなければなりません。
"""
        # ★★★★★ ここまでが最重要修正ポイント ★★★★★
        return self._call_llm(prompt, self.SYSTEM_PROMPT)

# === NexusCore/src\sandbox_output\sample.py ===
# encoding: utf-8
import sys
import os
import pytest
from pathlib import Path

# --- sandbox_output をインポートパスに追加 ---
sandbox_path = Path(__file__).parent.parent / "sandbox_output"
if str(sandbox_path) not in sys.path:
    sys.path.append(str(sandbox_path))

try:
    from sample import add_two_integers
except ImportError:
    add_two_integers = None


# --- テストスイート ---
@pytest.mark.skipif(add_two_integers is None, reason="sample.py が見つかりません")
class TestAddTwoIntegers:

    @pytest.mark.parametrize(
        "a, b, expected",
        [(1, 2, 3), (-1, 2, 1), (0, 0, 0), (-5, -10, -15), (10000, 20000, 30000)]
    )
    def test_add_normally(self, a, b, expected):
        assert add_two_integers(a, b) == expected

    @pytest.mark.parametrize(
        "a, b",
        [("1", 2), (1, "2"), (1.5, 2), (1, None)]
    )
    def test_raises_error_with_invalid_types(self, a, b):
        with pytest.raises(ValueError, match=r"入力は整数である必要があります"):
            add_two_integers(a, b)

# === NexusCore/src\utils\test_generator.py ===
# 📁 test_generator.py
# 📂 保存場所: /src/utils/test_generator.py

from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_unit_tests(code: str) -> str:
    prompt = f"""次のPythonコードに対して、pytest形式のユニットテストを生成してください。

# 対象コード
{code}

# 出力形式（必須）
```python
# test_sample.py
import pytest

# ユニットテスト内容
# ...
```"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "あなたは優秀なPythonのテストエンジニアです。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
    )

    return response.choices[0].message.content

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\agents\coder_agent.py ===
# ==============================================================================
# フォルダ: src/agents
# ファイル名: coder_agent.py
# ==============================================================================
from .base_agent import BaseAgent

class CoderAgent(BaseAgent):
    SYSTEM_PROMPT = "あなたは、クリーンで効率的なコードを書くことを得意とする、世界クラスのPython開発者です。あなたの唯一の仕事は、与えられた指示に基づき、完全に動作するPythonコードを生成することです。"

    def implement_code(self, task_description: str, existing_code: str) -> str:
        # ★★★★★ ここからが最重要修正ポイント ★★★★★
        # AIが混乱しないよう、プロンプトを構造化し、厳格な出力ルールを課します。
        prompt = f"""
# 既存のコード
```python
{existing_code}
```

# あなたへの指示
上記の既存コードに対して、以下のタスクを実装してください。

## タスク内容
「{task_description}」

# 重要：
もしタスク内容に `[Orchestratorからの具体的指示]` や `[Guardianからのフィードバック]` が含まれている場合は、元のタスクよりも、そのフィードバックの内容を解決することを最優先してください。

# 絶対的な出力ルール
- **修正後の完全なPythonコードのみ**を出力してください。
- コードの前に前置きや言い訳、後に結びの言葉や要約など、**コード以外のテキストは一切含めないでください。**
- あなたの思考プロセスや解釈を、Pythonのコメント（`#`）以外でコードに含めてはなりません。
- 出力は、そのまま `.py` ファイルとして保存できる、純粋なPythonコードでなければなりません。
"""
        # ★★★★★ ここまでが最重要修正ポイント ★★★★★
        return self._call_llm(prompt, self.SYSTEM_PROMPT)

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_output\sample.py ===
# encoding: utf-8
import sys
import os
import pytest
from pathlib import Path

# --- sandbox_output をインポートパスに追加 ---
sandbox_path = Path(__file__).parent.parent / "sandbox_output"
if str(sandbox_path) not in sys.path:
    sys.path.append(str(sandbox_path))

try:
    from sample import add_two_integers
except ImportError:
    add_two_integers = None


# --- テストスイート ---
@pytest.mark.skipif(add_two_integers is None, reason="sample.py が見つかりません")
class TestAddTwoIntegers:

    @pytest.mark.parametrize(
        "a, b, expected",
        [(1, 2, 3), (-1, 2, 1), (0, 0, 0), (-5, -10, -15), (10000, 20000, 30000)]
    )
    def test_add_normally(self, a, b, expected):
        assert add_two_integers(a, b) == expected

    @pytest.mark.parametrize(
        "a, b",
        [("1", 2), (1, "2"), (1.5, 2), (1, None)]
    )
    def test_raises_error_with_invalid_types(self, a, b):
        with pytest.raises(ValueError, match=r"入力は整数である必要があります"):
            add_two_integers(a, b)

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\utils\test_generator.py ===
# 📁 test_generator.py
# 📂 保存場所: /src/utils/test_generator.py

from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_unit_tests(code: str) -> str:
    prompt = f"""次のPythonコードに対して、pytest形式のユニットテストを生成してください。

# 対象コード
{code}

# 出力形式（必須）
```python
# test_sample.py
import pytest

# ユニットテスト内容
# ...
```"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "あなたは優秀なPythonのテストエンジニアです。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
    )

    return response.choices[0].message.content

# === NexusCore/openenv\Lib\site-packages\numpy\lib\tests\test_loadtxt.py ===
"""
Tests specific to `np.loadtxt` added during the move of loadtxt to be backed
by C code.
These tests complement those found in `test_io.py`.
"""

import os
import sys
from io import StringIO
from tempfile import NamedTemporaryFile, mkstemp

import pytest

import numpy as np
from numpy.ma.testutils import assert_equal
from numpy.testing import HAS_REFCOUNT, IS_PYPY, assert_array_equal


def test_scientific_notation():
    """Test that both 'e' and 'E' are parsed correctly."""
    data = StringIO(

            "1.0e-1,2.0E1,3.0\n"
            "4.0e-2,5.0E-1,6.0\n"
            "7.0e-3,8.0E1,9.0\n"
            "0.0e-4,1.0E-1,2.0"

    )
    expected = np.array(
        [[0.1, 20., 3.0], [0.04, 0.5, 6], [0.007, 80., 9], [0, 0.1, 2]]
    )
    assert_array_equal(np.loadtxt(data, delimiter=","), expected)


@pytest.mark.parametrize("comment", ["..", "//", "@-", "this is a comment:"])
def test_comment_multiple_chars(comment):
    content = "# IGNORE\n1.5, 2.5# ABC\n3.0,4.0# XXX\n5.5,6.0\n"
    txt = StringIO(content.replace("#", comment))
    a = np.loadtxt(txt, delimiter=",", comments=comment)
    assert_equal(a, [[1.5, 2.5], [3.0, 4.0], [5.5, 6.0]])


@pytest.fixture
def mixed_types_structured():
    """
    Fixture providing heterogeneous input data with a structured dtype, along
    with the associated structured array.
    """
    data = StringIO(

            "1000;2.4;alpha;-34\n"
            "2000;3.1;beta;29\n"
            "3500;9.9;gamma;120\n"
            "4090;8.1;delta;0\n"
            "5001;4.4;epsilon;-99\n"
            "6543;7.8;omega;-1\n"

    )
    dtype = np.dtype(
        [('f0', np.uint16), ('f1', np.float64), ('f2', 'S7'), ('f3', np.int8)]
    )
    expected = np.array(
        [
            (1000, 2.4, "alpha", -34),
            (2000, 3.1, "beta", 29),
            (3500, 9.9, "gamma", 120),
            (4090, 8.1, "delta", 0),
            (5001, 4.4, "epsilon", -99),
            (6543, 7.8, "omega", -1)
        ],
        dtype=dtype
    )
    return data, dtype, expected


@pytest.mark.parametrize('skiprows', [0, 1, 2, 3])
def test_structured_dtype_and_skiprows_no_empty_lines(
        skiprows, mixed_types_structured):
    data, dtype, expected = mixed_types_structured
    a = np.loadtxt(data, dtype=dtype, delimiter=";", skiprows=skiprows)
    assert_array_equal(a, expected[skiprows:])


def test_unpack_structured(mixed_types_structured):
    data, dtype, expected = mixed_types_structured

    a, b, c, d = np.loadtxt(data, dtype=dtype, delimiter=";", unpack=True)
    assert_array_equal(a, expected["f0"])
    assert_array_equal(b, expected["f1"])
    assert_array_equal(c, expected["f2"])
    assert_array_equal(d, expected["f3"])


def test_structured_dtype_with_shape():
    dtype = np.dtype([("a", "u1", 2), ("b", "u1", 2)])
    data = StringIO("0,1,2,3\n6,7,8,9\n")
    expected = np.array([((0, 1), (2, 3)), ((6, 7), (8, 9))], dtype=dtype)
    assert_array_equal(np.loadtxt(data, delimiter=",", dtype=dtype), expected)


def test_structured_dtype_with_multi_shape():
    dtype = np.dtype([("a", "u1", (2, 2))])
    data = StringIO("0 1 2 3\n")
    expected = np.array([(((0, 1), (2, 3)),)], dtype=dtype)
    assert_array_equal(np.loadtxt(data, dtype=dtype), expected)


def test_nested_structured_subarray():
    # Test from gh-16678
    point = np.dtype([('x', float), ('y', float)])
    dt = np.dtype([('code', int), ('points', point, (2,))])
    data = StringIO("100,1,2,3,4\n200,5,6,7,8\n")
    expected = np.array(
        [
            (100, [(1., 2.), (3., 4.)]),
            (200, [(5., 6.), (7., 8.)]),
        ],
        dtype=dt
    )
    assert_array_equal(np.loadtxt(data, dtype=dt, delimiter=","), expected)


def test_structured_dtype_offsets():
    # An aligned structured dtype will have additional padding
    dt = np.dtype("i1, i4, i1, i4, i1, i4", align=True)
    data = StringIO("1,2,3,4,5,6\n7,8,9,10,11,12\n")
    expected = np.array([(1, 2, 3, 4, 5, 6), (7, 8, 9, 10, 11, 12)], dtype=dt)
    assert_array_equal(np.loadtxt(data, delimiter=",", dtype=dt), expected)


@pytest.mark.parametrize("param", ("skiprows", "max_rows"))
def test_exception_negative_row_limits(param):
    """skiprows and max_rows should raise for negative parameters."""
    with pytest.raises(ValueError, match="argument must be nonnegative"):
        np.loadtxt("foo.bar", **{param: -3})


@pytest.mark.parametrize("param", ("skiprows", "max_rows"))
def test_exception_noninteger_row_limits(param):
    with pytest.raises(TypeError, match="argument must be an integer"):
        np.loadtxt("foo.bar", **{param: 1.0})


@pytest.mark.parametrize(
    "data, shape",
    [
        ("1 2 3 4 5\n", (1, 5)),  # Single row
        ("1\n2\n3\n4\n5\n", (5, 1)),  # Single column
    ]
)
def test_ndmin_single_row_or_col(data, shape):
    arr = np.array([1, 2, 3, 4, 5])
    arr2d = arr.reshape(shape)

    assert_array_equal(np.loadtxt(StringIO(data), dtype=int), arr)
    assert_array_equal(np.loadtxt(StringIO(data), dtype=int, ndmin=0), arr)
    assert_array_equal(np.loadtxt(StringIO(data), dtype=int, ndmin=1), arr)
    assert_array_equal(np.loadtxt(StringIO(data), dtype=int, ndmin=2), arr2d)


@pytest.mark.parametrize("badval", [-1, 3, None, "plate of shrimp"])
def test_bad_ndmin(badval):
    with pytest.raises(ValueError, match="Illegal value of ndmin keyword"):
        np.loadtxt("foo.bar", ndmin=badval)


@pytest.mark.parametrize(
    "ws",
    (
            " ",  # space
            "\t",  # tab
            "\u2003",  # em
            "\u00A0",  # non-break
            "\u3000",  # ideographic space
    )
)
def test_blank_lines_spaces_delimit(ws):
    txt = StringIO(
        f"1 2{ws}30\n\n{ws}\n"
        f"4 5 60{ws}\n  {ws}  \n"
        f"7 8 {ws} 90\n  # comment\n"
        f"3 2 1"
    )
    # NOTE: It is unclear that the `  # comment` should succeed. Except
    #       for delimiter=None, which should use any whitespace (and maybe
    #       should just be implemented closer to Python
    expected = np.array([[1, 2, 30], [4, 5, 60], [7, 8, 90], [3, 2, 1]])
    assert_equal(
        np.loadtxt(txt, dtype=int, delimiter=None, comments="#"), expected
    )


def test_blank_lines_normal_delimiter():
    txt = StringIO('1,2,30\n\n4,5,60\n\n7,8,90\n# comment\n3,2,1')
    expected = np.array([[1, 2, 30], [4, 5, 60], [7, 8, 90], [3, 2, 1]])
    assert_equal(
        np.loadtxt(txt, dtype=int, delimiter=',', comments="#"), expected
    )


@pytest.mark.parametrize("dtype", (float, object))
def test_maxrows_no_blank_lines(dtype):
    txt = StringIO("1.5,2.5\n3.0,4.0\n5.5,6.0")
    res = np.loadtxt(txt, dtype=dtype, delimiter=",", max_rows=2)
    assert_equal(res.dtype, dtype)
    assert_equal(res, np.array([["1.5", "2.5"], ["3.0", "4.0"]], dtype=dtype))


@pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                    reason="PyPy bug in error formatting")
@pytest.mark.parametrize("dtype", (np.dtype("f8"), np.dtype("i2")))
def test_exception_message_bad_values(dtype):
    txt = StringIO("1,2\n3,XXX\n5,6")
    msg = f"could not convert string 'XXX' to {dtype} at row 1, column 2"
    with pytest.raises(ValueError, match=msg):
        np.loadtxt(txt, dtype=dtype, delimiter=",")


def test_converters_negative_indices():
    txt = StringIO('1.5,2.5\n3.0,XXX\n5.5,6.0')
    conv = {-1: lambda s: np.nan if s == 'XXX' else float(s)}
    expected = np.array([[1.5, 2.5], [3.0, np.nan], [5.5, 6.0]])
    res = np.loadtxt(txt, dtype=np.float64, delimiter=",", converters=conv)
    assert_equal(res, expected)


def test_converters_negative_indices_with_usecols():
    txt = StringIO('1.5,2.5,3.5\n3.0,4.0,XXX\n5.5,6.0,7.5\n')
    conv = {-1: lambda s: np.nan if s == 'XXX' else float(s)}
    expected = np.array([[1.5, 3.5], [3.0, np.nan], [5.5, 7.5]])
    res = np.loadtxt(
        txt,
        dtype=np.float64,
        delimiter=",",
        converters=conv,
        usecols=[0, -1],
    )
    assert_equal(res, expected)

    # Second test with variable number of rows:
    res = np.loadtxt(StringIO('''0,1,2\n0,1,2,3,4'''), delimiter=",",
                     usecols=[0, -1], converters={-1: (lambda x: -1)})
    assert_array_equal(res, [[0, -1], [0, -1]])


def test_ragged_error():
    rows = ["1,2,3", "1,2,3", "4,3,2,1"]
    with pytest.raises(ValueError,
            match="the number of columns changed from 3 to 4 at row 3"):
        np.loadtxt(rows, delimiter=",")


def test_ragged_usecols():
    # usecols, and negative ones, work even with varying number of columns.
    txt = StringIO("0,0,XXX\n0,XXX,0,XXX\n0,XXX,XXX,0,XXX\n")
    expected = np.array([[0, 0], [0, 0], [0, 0]])
    res = np.loadtxt(txt, dtype=float, delimiter=",", usecols=[0, -2])
    assert_equal(res, expected)

    txt = StringIO("0,0,XXX\n0\n0,XXX,XXX,0,XXX\n")
    with pytest.raises(ValueError,
                match="invalid column index -2 at row 2 with 1 columns"):
        # There is no -2 column in the second row:
        np.loadtxt(txt, dtype=float, delimiter=",", usecols=[0, -2])


def test_empty_usecols():
    txt = StringIO("0,0,XXX\n0,XXX,0,XXX\n0,XXX,XXX,0,XXX\n")
    res = np.loadtxt(txt, dtype=np.dtype([]), delimiter=",", usecols=[])
    assert res.shape == (3,)
    assert res.dtype == np.dtype([])


@pytest.mark.parametrize("c1", ["a", "の", "🫕"])
@pytest.mark.parametrize("c2", ["a", "の", "🫕"])
def test_large_unicode_characters(c1, c2):
    # c1 and c2 span ascii, 16bit and 32bit range.
    txt = StringIO(f"a,{c1},c,1.0\ne,{c2},2.0,g")
    res = np.loadtxt(txt, dtype=np.dtype('U12'), delimiter=",")
    expected = np.array(
        [f"a,{c1},c,1.0".split(","), f"e,{c2},2.0,g".split(",")],
        dtype=np.dtype('U12')
    )
    assert_equal(res, expected)


def test_unicode_with_converter():
    txt = StringIO("cat,dog\nαβγ,δεζ\nabc,def\n")
    conv = {0: lambda s: s.upper()}
    res = np.loadtxt(
        txt,
        dtype=np.dtype("U12"),
        converters=conv,
        delimiter=",",
        encoding=None
    )
    expected = np.array([['CAT', 'dog'], ['ΑΒΓ', 'δεζ'], ['ABC', 'def']])
    assert_equal(res, expected)


def test_converter_with_structured_dtype():
    txt = StringIO('1.5,2.5,Abc\n3.0,4.0,dEf\n5.5,6.0,ghI\n')
    dt = np.dtype([('m', np.int32), ('r', np.float32), ('code', 'U8')])
    conv = {0: lambda s: int(10 * float(s)), -1: lambda s: s.upper()}
    res = np.loadtxt(txt, dtype=dt, delimiter=",", converters=conv)
    expected = np.array(
        [(15, 2.5, 'ABC'), (30, 4.0, 'DEF'), (55, 6.0, 'GHI')], dtype=dt
    )
    assert_equal(res, expected)


def test_converter_with_unicode_dtype():
    """
    With the 'bytes' encoding, tokens are encoded prior to being
    passed to the converter. This means that the output of the converter may
    be bytes instead of unicode as expected by `read_rows`.

    This test checks that outputs from the above scenario are properly decoded
    prior to parsing by `read_rows`.
    """
    txt = StringIO('abc,def\nrst,xyz')
    conv = bytes.upper
    res = np.loadtxt(
            txt, dtype=np.dtype("U3"), converters=conv, delimiter=",",
            encoding="bytes")
    expected = np.array([['ABC', 'DEF'], ['RST', 'XYZ']])
    assert_equal(res, expected)


def test_read_huge_row():
    row = "1.5, 2.5," * 50000
    row = row[:-1] + "\n"
    txt = StringIO(row * 2)
    res = np.loadtxt(txt, delimiter=",", dtype=float)
    assert_equal(res, np.tile([1.5, 2.5], (2, 50000)))


@pytest.mark.parametrize("dtype", "edfgFDG")
def test_huge_float(dtype):
    # Covers a non-optimized path that is rarely taken:
    field = "0" * 1000 + ".123456789"
    dtype = np.dtype(dtype)
    value = np.loadtxt([field], dtype=dtype)[()]
    assert value == dtype.type("0.123456789")


@pytest.mark.parametrize(
    ("given_dtype", "expected_dtype"),
    [
        ("S", np.dtype("S5")),
        ("U", np.dtype("U5")),
    ],
)
def test_string_no_length_given(given_dtype, expected_dtype):
    """
    The given dtype is just 'S' or 'U' with no length. In these cases, the
    length of the resulting dtype is determined by the longest string found
    in the file.
    """
    txt = StringIO("AAA,5-1\nBBBBB,0-3\nC,4-9\n")
    res = np.loadtxt(txt, dtype=given_dtype, delimiter=",")
    expected = np.array(
        [['AAA', '5-1'], ['BBBBB', '0-3'], ['C', '4-9']], dtype=expected_dtype
    )
    assert_equal(res, expected)
    assert_equal(res.dtype, expected_dtype)


def test_float_conversion():
    """
    Some tests that the conversion to float64 works as accurately as the
    Python built-in `float` function. In a naive version of the float parser,
    these strings resulted in values that were off by an ULP or two.
    """
    strings = [
        '0.9999999999999999',
        '9876543210.123456',
        '5.43215432154321e+300',
        '0.901',
        '0.333',
    ]
    txt = StringIO('\n'.join(strings))
    res = np.loadtxt(txt)
    expected = np.array([float(s) for s in strings])
    assert_equal(res, expected)


def test_bool():
    # Simple test for bool via integer
    txt = StringIO("1, 0\n10, -1")
    res = np.loadtxt(txt, dtype=bool, delimiter=",")
    assert res.dtype == bool
    assert_array_equal(res, [[True, False], [True, True]])
    # Make sure we use only 1 and 0 on the byte level:
    assert_array_equal(res.view(np.uint8), [[1, 0], [1, 1]])


@pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                    reason="PyPy bug in error formatting")
@pytest.mark.parametrize("dtype", np.typecodes["AllInteger"])
@pytest.mark.filterwarnings("error:.*integer via a float.*:DeprecationWarning")
def test_integer_signs(dtype):
    dtype = np.dtype(dtype)
    assert np.loadtxt(["+2"], dtype=dtype) == 2
    if dtype.kind == "u":
        with pytest.raises(ValueError):
            np.loadtxt(["-1\n"], dtype=dtype)
    else:
        assert np.loadtxt(["-2\n"], dtype=dtype) == -2

    for sign in ["++", "+-", "--", "-+"]:
        with pytest.raises(ValueError):
            np.loadtxt([f"{sign}2\n"], dtype=dtype)


@pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                    reason="PyPy bug in error formatting")
@pytest.mark.parametrize("dtype", np.typecodes["AllInteger"])
@pytest.mark.filterwarnings("error:.*integer via a float.*:DeprecationWarning")
def test_implicit_cast_float_to_int_fails(dtype):
    txt = StringIO("1.0, 2.1, 3.7\n4, 5, 6")
    with pytest.raises(ValueError):
        np.loadtxt(txt, dtype=dtype, delimiter=",")

@pytest.mark.parametrize("dtype", (np.complex64, np.complex128))
@pytest.mark.parametrize("with_parens", (False, True))
def test_complex_parsing(dtype, with_parens):
    s = "(1.0-2.5j),3.75,(7+-5.0j)\n(4),(-19e2j),(0)"
    if not with_parens:
        s = s.replace("(", "").replace(")", "")

    res = np.loadtxt(StringIO(s), dtype=dtype, delimiter=",")
    expected = np.array(
        [[1.0 - 2.5j, 3.75, 7 - 5j], [4.0, -1900j, 0]], dtype=dtype
    )
    assert_equal(res, expected)


def test_read_from_generator():
    def gen():
        for i in range(4):
            yield f"{i},{2 * i},{i**2}"

    res = np.loadtxt(gen(), dtype=int, delimiter=",")
    expected = np.array([[0, 0, 0], [1, 2, 1], [2, 4, 4], [3, 6, 9]])
    assert_equal(res, expected)


def test_read_from_generator_multitype():
    def gen():
        for i in range(3):
            yield f"{i} {i / 4}"

    res = np.loadtxt(gen(), dtype="i, d", delimiter=" ")
    expected = np.array([(0, 0.0), (1, 0.25), (2, 0.5)], dtype="i, d")
    assert_equal(res, expected)


def test_read_from_bad_generator():
    def gen():
        yield from ["1,2", b"3, 5", 12738]

    with pytest.raises(
            TypeError, match=r"non-string returned while reading data"):
        np.loadtxt(gen(), dtype="i, i", delimiter=",")


@pytest.mark.skipif(not HAS_REFCOUNT, reason="Python lacks refcounts")
def test_object_cleanup_on_read_error():
    sentinel = object()
    already_read = 0

    def conv(x):
        nonlocal already_read
        if already_read > 4999:
            raise ValueError("failed half-way through!")
        already_read += 1
        return sentinel

    txt = StringIO("x\n" * 10000)

    with pytest.raises(ValueError, match="at row 5000, column 1"):
        np.loadtxt(txt, dtype=object, converters={0: conv})

    assert sys.getrefcount(sentinel) == 2


@pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                    reason="PyPy bug in error formatting")
def test_character_not_bytes_compatible():
    """Test exception when a character cannot be encoded as 'S'."""
    data = StringIO("–")  # == \u2013
    with pytest.raises(ValueError):
        np.loadtxt(data, dtype="S5")


@pytest.mark.parametrize("conv", (0, [float], ""))
def test_invalid_converter(conv):
    msg = (
        "converters must be a dictionary mapping columns to converter "
        "functions or a single callable."
    )
    with pytest.raises(TypeError, match=msg):
        np.loadtxt(StringIO("1 2\n3 4"), converters=conv)


@pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                    reason="PyPy bug in error formatting")
def test_converters_dict_raises_non_integer_key():
    with pytest.raises(TypeError, match="keys of the converters dict"):
        np.loadtxt(StringIO("1 2\n3 4"), converters={"a": int})
    with pytest.raises(TypeError, match="keys of the converters dict"):
        np.loadtxt(StringIO("1 2\n3 4"), converters={"a": int}, usecols=0)


@pytest.mark.parametrize("bad_col_ind", (3, -3))
def test_converters_dict_raises_non_col_key(bad_col_ind):
    data = StringIO("1 2\n3 4")
    with pytest.raises(ValueError, match="converter specified for column"):
        np.loadtxt(data, converters={bad_col_ind: int})


def test_converters_dict_raises_val_not_callable():
    with pytest.raises(TypeError,
                match="values of the converters dictionary must be callable"):
        np.loadtxt(StringIO("1 2\n3 4"), converters={0: 1})


@pytest.mark.parametrize("q", ('"', "'", "`"))
def test_quoted_field(q):
    txt = StringIO(
        f"{q}alpha, x{q}, 2.5\n{q}beta, y{q}, 4.5\n{q}gamma, z{q}, 5.0\n"
    )
    dtype = np.dtype([('f0', 'U8'), ('f1', np.float64)])
    expected = np.array(
        [("alpha, x", 2.5), ("beta, y", 4.5), ("gamma, z", 5.0)], dtype=dtype
    )

    res = np.loadtxt(txt, dtype=dtype, delimiter=",", quotechar=q)
    assert_array_equal(res, expected)


@pytest.mark.parametrize("q", ('"', "'", "`"))
def test_quoted_field_with_whitepace_delimiter(q):
    txt = StringIO(
        f"{q}alpha, x{q}     2.5\n{q}beta, y{q} 4.5\n{q}gamma, z{q}   5.0\n"
    )
    dtype = np.dtype([('f0', 'U8'), ('f1', np.float64)])
    expected = np.array(
        [("alpha, x", 2.5), ("beta, y", 4.5), ("gamma, z", 5.0)], dtype=dtype
    )

    res = np.loadtxt(txt, dtype=dtype, delimiter=None, quotechar=q)
    assert_array_equal(res, expected)


def test_quote_support_default():
    """Support for quoted fields is disabled by default."""
    txt = StringIO('"lat,long", 45, 30\n')
    dtype = np.dtype([('f0', 'U24'), ('f1', np.float64), ('f2', np.float64)])

    with pytest.raises(ValueError,
            match="the dtype passed requires 3 columns but 4 were"):
        np.loadtxt(txt, dtype=dtype, delimiter=",")

    # Enable quoting support with non-None value for quotechar param
    txt.seek(0)
    expected = np.array([("lat,long", 45., 30.)], dtype=dtype)

    res = np.loadtxt(txt, dtype=dtype, delimiter=",", quotechar='"')
    assert_array_equal(res, expected)


@pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                    reason="PyPy bug in error formatting")
def test_quotechar_multichar_error():
    txt = StringIO("1,2\n3,4")
    msg = r".*must be a single unicode character or None"
    with pytest.raises(TypeError, match=msg):
        np.loadtxt(txt, delimiter=",", quotechar="''")


def test_comment_multichar_error_with_quote():
    txt = StringIO("1,2\n3,4")
    msg = (
        "when multiple comments or a multi-character comment is given, "
        "quotes are not supported."
    )
    with pytest.raises(ValueError, match=msg):
        np.loadtxt(txt, delimiter=",", comments="123", quotechar='"')
    with pytest.raises(ValueError, match=msg):
        np.loadtxt(txt, delimiter=",", comments=["#", "%"], quotechar='"')

    # A single character string in a tuple is unpacked though:
    res = np.loadtxt(txt, delimiter=",", comments=("#",), quotechar="'")
    assert_equal(res, [[1, 2], [3, 4]])


def test_structured_dtype_with_quotes():
    data = StringIO(

            "1000;2.4;'alpha';-34\n"
            "2000;3.1;'beta';29\n"
            "3500;9.9;'gamma';120\n"
            "4090;8.1;'delta';0\n"
            "5001;4.4;'epsilon';-99\n"
            "6543;7.8;'omega';-1\n"

    )
    dtype = np.dtype(
        [('f0', np.uint16), ('f1', np.float64), ('f2', 'S7'), ('f3', np.int8)]
    )
    expected = np.array(
        [
            (1000, 2.4, "alpha", -34),
            (2000, 3.1, "beta", 29),
            (3500, 9.9, "gamma", 120),
            (4090, 8.1, "delta", 0),
            (5001, 4.4, "epsilon", -99),
            (6543, 7.8, "omega", -1)
        ],
        dtype=dtype
    )
    res = np.loadtxt(data, dtype=dtype, delimiter=";", quotechar="'")
    assert_array_equal(res, expected)


def test_quoted_field_is_not_empty():
    txt = StringIO('1\n\n"4"\n""')
    expected = np.array(["1", "4", ""], dtype="U1")
    res = np.loadtxt(txt, delimiter=",", dtype="U1", quotechar='"')
    assert_equal(res, expected)

def test_quoted_field_is_not_empty_nonstrict():
    # Same as test_quoted_field_is_not_empty but check that we are not strict
    # about missing closing quote (this is the `csv.reader` default also)
    txt = StringIO('1\n\n"4"\n"')
    expected = np.array(["1", "4", ""], dtype="U1")
    res = np.loadtxt(txt, delimiter=",", dtype="U1", quotechar='"')
    assert_equal(res, expected)

def test_consecutive_quotechar_escaped():
    txt = StringIO('"Hello, my name is ""Monty""!"')
    expected = np.array('Hello, my name is "Monty"!', dtype="U40")
    res = np.loadtxt(txt, dtype="U40", delimiter=",", quotechar='"')
    assert_equal(res, expected)


@pytest.mark.parametrize("data", ("", "\n\n\n", "# 1 2 3\n# 4 5 6\n"))
@pytest.mark.parametrize("ndmin", (0, 1, 2))
@pytest.mark.parametrize("usecols", [None, (1, 2, 3)])
def test_warn_on_no_data(data, ndmin, usecols):
    """Check that a UserWarning is emitted when no data is read from input."""
    if usecols is not None:
        expected_shape = (0, 3)
    elif ndmin == 2:
        expected_shape = (0, 1)  # guess a single column?!
    else:
        expected_shape = (0,)

    txt = StringIO(data)
    with pytest.warns(UserWarning, match="input contained no data"):
        res = np.loadtxt(txt, ndmin=ndmin, usecols=usecols)
    assert res.shape == expected_shape

    with NamedTemporaryFile(mode="w") as fh:
        fh.write(data)
        fh.seek(0)
        with pytest.warns(UserWarning, match="input contained no data"):
            res = np.loadtxt(txt, ndmin=ndmin, usecols=usecols)
        assert res.shape == expected_shape

@pytest.mark.parametrize("skiprows", (2, 3))
def test_warn_on_skipped_data(skiprows):
    data = "1 2 3\n4 5 6"
    txt = StringIO(data)
    with pytest.warns(UserWarning, match="input contained no data"):
        np.loadtxt(txt, skiprows=skiprows)


@pytest.mark.parametrize(["dtype", "value"], [
        ("i2", 0x0001), ("u2", 0x0001),
        ("i4", 0x00010203), ("u4", 0x00010203),
        ("i8", 0x0001020304050607), ("u8", 0x0001020304050607),
        # The following values are constructed to lead to unique bytes:
        ("float16", 3.07e-05),
        ("float32", 9.2557e-41), ("complex64", 9.2557e-41 + 2.8622554e-29j),
        ("float64", -1.758571353180402e-24),
        # Here and below, the repr side-steps a small loss of precision in
        # complex `str` in PyPy (which is probably fine, as repr works):
        ("complex128", repr(5.406409232372729e-29 - 1.758571353180402e-24j)),
        # Use integer values that fit into double.  Everything else leads to
        # problems due to longdoubles going via double and decimal strings
        # causing rounding errors.
        ("longdouble", 0x01020304050607),
        ("clongdouble", repr(0x01020304050607 + (0x00121314151617 * 1j))),
        ("U2", "\U00010203\U000a0b0c")])
@pytest.mark.parametrize("swap", [True, False])
def test_byteswapping_and_unaligned(dtype, value, swap):
    # Try to create "interesting" values within the valid unicode range:
    dtype = np.dtype(dtype)
    data = [f"x,{value}\n"]  # repr as PyPy `str` truncates some
    if swap:
        dtype = dtype.newbyteorder()
    full_dt = np.dtype([("a", "S1"), ("b", dtype)], align=False)
    # The above ensures that the interesting "b" field is unaligned:
    assert full_dt.fields["b"][1] == 1
    res = np.loadtxt(data, dtype=full_dt, delimiter=",",
                     max_rows=1)  # max-rows prevents over-allocation
    assert res["b"] == dtype.type(value)


@pytest.mark.parametrize("dtype",
        np.typecodes["AllInteger"] + "efdFD" + "?")
def test_unicode_whitespace_stripping(dtype):
    # Test that all numeric types (and bool) strip whitespace correctly
    # \u202F is a narrow no-break space, `\n` is just a whitespace if quoted.
    # Currently, skip float128 as it did not always support this and has no
    # "custom" parsing:
    txt = StringIO(' 3 ,"\u202F2\n"')
    res = np.loadtxt(txt, dtype=dtype, delimiter=",", quotechar='"')
    assert_array_equal(res, np.array([3, 2]).astype(dtype))


@pytest.mark.parametrize("dtype", "FD")
def test_unicode_whitespace_stripping_complex(dtype):
    # Complex has a few extra cases since it has two components and
    # parentheses
    line = " 1 , 2+3j , ( 4+5j ), ( 6+-7j )  , 8j , ( 9j ) \n"
    data = [line, line.replace(" ", "\u202F")]
    res = np.loadtxt(data, dtype=dtype, delimiter=',')
    assert_array_equal(res, np.array([[1, 2 + 3j, 4 + 5j, 6 - 7j, 8j, 9j]] * 2))


@pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                    reason="PyPy bug in error formatting")
@pytest.mark.parametrize("dtype", "FD")
@pytest.mark.parametrize("field",
        ["1 +2j", "1+ 2j", "1+2 j", "1+-+3", "(1j", "(1", "(1+2j", "1+2j)"])
def test_bad_complex(dtype, field):
    with pytest.raises(ValueError):
        np.loadtxt([field + "\n"], dtype=dtype, delimiter=",")


@pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                    reason="PyPy bug in error formatting")
@pytest.mark.parametrize("dtype",
            np.typecodes["AllInteger"] + "efgdFDG" + "?")
def test_nul_character_error(dtype):
    # Test that a \0 character is correctly recognized as an error even if
    # what comes before is valid (not everything gets parsed internally).
    if dtype.lower() == "g":
        pytest.xfail("longdouble/clongdouble assignment may misbehave.")
    with pytest.raises(ValueError):
        np.loadtxt(["1\000"], dtype=dtype, delimiter=",", quotechar='"')


@pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                    reason="PyPy bug in error formatting")
@pytest.mark.parametrize("dtype",
        np.typecodes["AllInteger"] + "efgdFDG" + "?")
def test_no_thousands_support(dtype):
    # Mainly to document behaviour, Python supports thousands like 1_1.
    # (e and G may end up using different conversion and support it, this is
    # a bug but happens...)
    if dtype == "e":
        pytest.skip("half assignment currently uses Python float converter")
    if dtype in "eG":
        pytest.xfail("clongdouble assignment is buggy (uses `complex`?).")

    assert int("1_1") == float("1_1") == complex("1_1") == 11
    with pytest.raises(ValueError):
        np.loadtxt(["1_1\n"], dtype=dtype)


@pytest.mark.parametrize("data", [
    ["1,2\n", "2\n,3\n"],
    ["1,2\n", "2\r,3\n"]])
def test_bad_newline_in_iterator(data):
    # In NumPy <=1.22 this was accepted, because newlines were completely
    # ignored when the input was an iterable.  This could be changed, but right
    # now, we raise an error.
    msg = "Found an unquoted embedded newline within a single line"
    with pytest.raises(ValueError, match=msg):
        np.loadtxt(data, delimiter=",")


@pytest.mark.parametrize("data", [
    ["1,2\n", "2,3\r\n"],  # a universal newline
    ["1,2\n", "'2\n',3\n"],  # a quoted newline
    ["1,2\n", "'2\r',3\n"],
    ["1,2\n", "'2\r\n',3\n"],
])
def test_good_newline_in_iterator(data):
    # The quoted newlines will be untransformed here, but are just whitespace.
    res = np.loadtxt(data, delimiter=",", quotechar="'")
    assert_array_equal(res, [[1., 2.], [2., 3.]])


@pytest.mark.parametrize("newline", ["\n", "\r", "\r\n"])
def test_universal_newlines_quoted(newline):
    # Check that universal newline support within the tokenizer is not applied
    # to quoted fields.  (note that lines must end in newline or quoted
    # fields will not include a newline at all)
    data = ['1,"2\n"\n', '3,"4\n', '1"\n']
    data = [row.replace("\n", newline) for row in data]
    res = np.loadtxt(data, dtype=object, delimiter=",", quotechar='"')
    assert_array_equal(res, [['1', f'2{newline}'], ['3', f'4{newline}1']])


def test_null_character():
    # Basic tests to check that the NUL character is not special:
    res = np.loadtxt(["1\0002\0003\n", "4\0005\0006"], delimiter="\000")
    assert_array_equal(res, [[1, 2, 3], [4, 5, 6]])

    # Also not as part of a field (avoid unicode/arrays as unicode strips \0)
    res = np.loadtxt(["1\000,2\000,3\n", "4\000,5\000,6"],
                     delimiter=",", dtype=object)
    assert res.tolist() == [["1\000", "2\000", "3"], ["4\000", "5\000", "6"]]


def test_iterator_fails_getting_next_line():
    class BadSequence:
        def __len__(self):
            return 100

        def __getitem__(self, item):
            if item == 50:
                raise RuntimeError("Bad things happened!")
            return f"{item}, {item + 1}"

    with pytest.raises(RuntimeError, match="Bad things happened!"):
        np.loadtxt(BadSequence(), dtype=int, delimiter=",")


class TestCReaderUnitTests:
    # These are internal tests for path that should not be possible to hit
    # unless things go very very wrong somewhere.
    def test_not_an_filelike(self):
        with pytest.raises(AttributeError, match=".*read"):
            np._core._multiarray_umath._load_from_filelike(
                object(), dtype=np.dtype("i"), filelike=True)

    def test_filelike_read_fails(self):
        # Can only be reached if loadtxt opens the file, so it is hard to do
        # via the public interface (although maybe not impossible considering
        # the current "DataClass" backing).
        class BadFileLike:
            counter = 0

            def read(self, size):
                self.counter += 1
                if self.counter > 20:
                    raise RuntimeError("Bad bad bad!")
                return "1,2,3\n"

        with pytest.raises(RuntimeError, match="Bad bad bad!"):
            np._core._multiarray_umath._load_from_filelike(
                BadFileLike(), dtype=np.dtype("i"), filelike=True)

    def test_filelike_bad_read(self):
        # Can only be reached if loadtxt opens the file, so it is hard to do
        # via the public interface (although maybe not impossible considering
        # the current "DataClass" backing).

        class BadFileLike:
            counter = 0

            def read(self, size):
                return 1234  # not a string!

        with pytest.raises(TypeError,
                    match="non-string returned while reading data"):
            np._core._multiarray_umath._load_from_filelike(
                BadFileLike(), dtype=np.dtype("i"), filelike=True)

    def test_not_an_iter(self):
        with pytest.raises(TypeError,
                    match="error reading from object, expected an iterable"):
            np._core._multiarray_umath._load_from_filelike(
                object(), dtype=np.dtype("i"), filelike=False)

    def test_bad_type(self):
        with pytest.raises(TypeError, match="internal error: dtype must"):
            np._core._multiarray_umath._load_from_filelike(
                object(), dtype="i", filelike=False)

    def test_bad_encoding(self):
        with pytest.raises(TypeError, match="encoding must be a unicode"):
            np._core._multiarray_umath._load_from_filelike(
                object(), dtype=np.dtype("i"), filelike=False, encoding=123)

    @pytest.mark.parametrize("newline", ["\r", "\n", "\r\n"])
    def test_manual_universal_newlines(self, newline):
        # This is currently not available to users, because we should always
        # open files with universal newlines enabled `newlines=None`.
        # (And reading from an iterator uses slightly different code paths.)
        # We have no real support for `newline="\r"` or `newline="\n" as the
        # user cannot specify those options.
        data = StringIO('0\n1\n"2\n"\n3\n4 #\n'.replace("\n", newline),
                        newline="")

        res = np._core._multiarray_umath._load_from_filelike(
            data, dtype=np.dtype("U10"), filelike=True,
            quote='"', comment="#", skiplines=1)
        assert_array_equal(res[:, 0], ["1", f"2{newline}", "3", "4 "])


def test_delimiter_comment_collision_raises():
    with pytest.raises(TypeError, match=".*control characters.*incompatible"):
        np.loadtxt(StringIO("1, 2, 3"), delimiter=",", comments=",")


def test_delimiter_quotechar_collision_raises():
    with pytest.raises(TypeError, match=".*control characters.*incompatible"):
        np.loadtxt(StringIO("1, 2, 3"), delimiter=",", quotechar=",")


def test_comment_quotechar_collision_raises():
    with pytest.raises(TypeError, match=".*control characters.*incompatible"):
        np.loadtxt(StringIO("1 2 3"), comments="#", quotechar="#")


def test_delimiter_and_multiple_comments_collision_raises():
    with pytest.raises(
        TypeError, match="Comment characters.*cannot include the delimiter"
    ):
        np.loadtxt(StringIO("1, 2, 3"), delimiter=",", comments=["#", ","])


@pytest.mark.parametrize(
    "ws",
    (
        " ",  # space
        "\t",  # tab
        "\u2003",  # em
        "\u00A0",  # non-break
        "\u3000",  # ideographic space
    )
)
def test_collision_with_default_delimiter_raises(ws):
    with pytest.raises(TypeError, match=".*control characters.*incompatible"):
        np.loadtxt(StringIO(f"1{ws}2{ws}3\n4{ws}5{ws}6\n"), comments=ws)
    with pytest.raises(TypeError, match=".*control characters.*incompatible"):
        np.loadtxt(StringIO(f"1{ws}2{ws}3\n4{ws}5{ws}6\n"), quotechar=ws)


@pytest.mark.parametrize("nl", ("\n", "\r"))
def test_control_character_newline_raises(nl):
    txt = StringIO(f"1{nl}2{nl}3{nl}{nl}4{nl}5{nl}6{nl}{nl}")
    msg = "control character.*cannot be a newline"
    with pytest.raises(TypeError, match=msg):
        np.loadtxt(txt, delimiter=nl)
    with pytest.raises(TypeError, match=msg):
        np.loadtxt(txt, comments=nl)
    with pytest.raises(TypeError, match=msg):
        np.loadtxt(txt, quotechar=nl)


@pytest.mark.parametrize(
    ("generic_data", "long_datum", "unitless_dtype", "expected_dtype"),
    [
        ("2012-03", "2013-01-15", "M8", "M8[D]"),  # Datetimes
        ("spam-a-lot", "tis_but_a_scratch", "U", "U17"),  # str
    ],
)
@pytest.mark.parametrize("nrows", (10, 50000, 60000))  # lt, eq, gt chunksize
def test_parametric_unit_discovery(
    generic_data, long_datum, unitless_dtype, expected_dtype, nrows
):
    """Check that the correct unit (e.g. month, day, second) is discovered from
    the data when a user specifies a unitless datetime."""
    # Unit should be "D" (days) due to last entry
    data = [generic_data] * nrows + [long_datum]
    expected = np.array(data, dtype=expected_dtype)
    assert len(data) == nrows + 1
    assert len(data) == len(expected)

    # file-like path
    txt = StringIO("\n".join(data))
    a = np.loadtxt(txt, dtype=unitless_dtype)
    assert len(a) == len(expected)
    assert a.dtype == expected.dtype
    assert_equal(a, expected)

    # file-obj path
    fd, fname = mkstemp()
    os.close(fd)
    with open(fname, "w") as fh:
        fh.write("\n".join(data) + "\n")
    # loading the full file...
    a = np.loadtxt(fname, dtype=unitless_dtype)
    assert len(a) == len(expected)
    assert a.dtype == expected.dtype
    assert_equal(a, expected)
    # loading half of the file...
    a = np.loadtxt(fname, dtype=unitless_dtype, max_rows=int(nrows / 2))
    os.remove(fname)
    assert len(a) == int(nrows / 2)
    assert_equal(a, expected[:int(nrows / 2)])


def test_str_dtype_unit_discovery_with_converter():
    data = ["spam-a-lot"] * 60000 + ["XXXtis_but_a_scratch"]
    expected = np.array(
        ["spam-a-lot"] * 60000 + ["tis_but_a_scratch"], dtype="U17"
    )
    conv = lambda s: s.removeprefix("XXX")

    # file-like path
    txt = StringIO("\n".join(data))
    a = np.loadtxt(txt, dtype="U", converters=conv)
    assert a.dtype == expected.dtype
    assert_equal(a, expected)

    # file-obj path
    fd, fname = mkstemp()
    os.close(fd)
    with open(fname, "w") as fh:
        fh.write("\n".join(data))
    a = np.loadtxt(fname, dtype="U", converters=conv)
    os.remove(fname)
    assert a.dtype == expected.dtype
    assert_equal(a, expected)


@pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                    reason="PyPy bug in error formatting")
def test_control_character_empty():
    with pytest.raises(TypeError, match="Text reading control character must"):
        np.loadtxt(StringIO("1 2 3"), delimiter="")
    with pytest.raises(TypeError, match="Text reading control character must"):
        np.loadtxt(StringIO("1 2 3"), quotechar="")
    with pytest.raises(ValueError, match="comments cannot be an empty string"):
        np.loadtxt(StringIO("1 2 3"), comments="")
    with pytest.raises(ValueError, match="comments cannot be an empty string"):
        np.loadtxt(StringIO("1 2 3"), comments=["#", ""])


def test_control_characters_as_bytes():
    """Byte control characters (comments, delimiter) are supported."""
    a = np.loadtxt(StringIO("#header\n1,2,3"), comments=b"#", delimiter=b",")
    assert_equal(a, [1, 2, 3])


@pytest.mark.filterwarnings('ignore::UserWarning')
def test_field_growing_cases():
    # Test empty field appending/growing (each field still takes 1 character)
    # to see if the final field appending does not create issues.
    res = np.loadtxt([""], delimiter=",", dtype=bytes)
    assert len(res) == 0

    for i in range(1, 1024):
        res = np.loadtxt(["," * i], delimiter=",", dtype=bytes, max_rows=10)
        assert len(res) == i + 1

@pytest.mark.parametrize("nmax", (10000, 50000, 55000, 60000))
def test_maxrows_exceeding_chunksize(nmax):
    # tries to read all of the file,
    # or less, equal, greater than _loadtxt_chunksize
    file_length = 60000

    # file-like path
    data = ["a 0.5 1"] * file_length
    txt = StringIO("\n".join(data))
    res = np.loadtxt(txt, dtype=str, delimiter=" ", max_rows=nmax)
    assert len(res) == nmax

    # file-obj path
    fd, fname = mkstemp()
    os.close(fd)
    with open(fname, "w") as fh:
        fh.write("\n".join(data))
    res = np.loadtxt(fname, dtype=str, delimiter=" ", max_rows=nmax)
    os.remove(fname)
    assert len(res) == nmax

@pytest.mark.parametrize("nskip", (0, 10000, 12345, 50000, 67891, 100000))
def test_skiprow_exceeding_maxrows_exceeding_chunksize(tmpdir, nskip):
    # tries to read a file in chunks by skipping a variable amount of lines,
    # less, equal, greater than max_rows
    file_length = 110000
    data = "\n".join(f"{i} a 0.5 1" for i in range(1, file_length + 1))
    expected_length = min(60000, file_length - nskip)
    expected = np.arange(nskip + 1, nskip + 1 + expected_length).astype(str)

    # file-like path
    txt = StringIO(data)
    res = np.loadtxt(txt, dtype='str', delimiter=" ", skiprows=nskip, max_rows=60000)
    assert len(res) == expected_length
    # are the right lines read in res?
    assert_array_equal(expected, res[:, 0])

    # file-obj path
    tmp_file = tmpdir / "test_data.txt"
    tmp_file.write(data)
    fname = str(tmp_file)
    res = np.loadtxt(fname, dtype='str', delimiter=" ", skiprows=nskip, max_rows=60000)
    assert len(res) == expected_length
    # are the right lines read in res?
    assert_array_equal(expected, res[:, 0])

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\tests\test_loadtxt.py ===
"""
Tests specific to `np.loadtxt` added during the move of loadtxt to be backed
by C code.
These tests complement those found in `test_io.py`.
"""

import os
import sys
from io import StringIO
from tempfile import NamedTemporaryFile, mkstemp

import pytest

import numpy as np
from numpy.ma.testutils import assert_equal
from numpy.testing import HAS_REFCOUNT, IS_PYPY, assert_array_equal


def test_scientific_notation():
    """Test that both 'e' and 'E' are parsed correctly."""
    data = StringIO(

            "1.0e-1,2.0E1,3.0\n"
            "4.0e-2,5.0E-1,6.0\n"
            "7.0e-3,8.0E1,9.0\n"
            "0.0e-4,1.0E-1,2.0"

    )
    expected = np.array(
        [[0.1, 20., 3.0], [0.04, 0.5, 6], [0.007, 80., 9], [0, 0.1, 2]]
    )
    assert_array_equal(np.loadtxt(data, delimiter=","), expected)


@pytest.mark.parametrize("comment", ["..", "//", "@-", "this is a comment:"])
def test_comment_multiple_chars(comment):
    content = "# IGNORE\n1.5, 2.5# ABC\n3.0,4.0# XXX\n5.5,6.0\n"
    txt = StringIO(content.replace("#", comment))
    a = np.loadtxt(txt, delimiter=",", comments=comment)
    assert_equal(a, [[1.5, 2.5], [3.0, 4.0], [5.5, 6.0]])


@pytest.fixture
def mixed_types_structured():
    """
    Fixture providing heterogeneous input data with a structured dtype, along
    with the associated structured array.
    """
    data = StringIO(

            "1000;2.4;alpha;-34\n"
            "2000;3.1;beta;29\n"
            "3500;9.9;gamma;120\n"
            "4090;8.1;delta;0\n"
            "5001;4.4;epsilon;-99\n"
            "6543;7.8;omega;-1\n"

    )
    dtype = np.dtype(
        [('f0', np.uint16), ('f1', np.float64), ('f2', 'S7'), ('f3', np.int8)]
    )
    expected = np.array(
        [
            (1000, 2.4, "alpha", -34),
            (2000, 3.1, "beta", 29),
            (3500, 9.9, "gamma", 120),
            (4090, 8.1, "delta", 0),
            (5001, 4.4, "epsilon", -99),
            (6543, 7.8, "omega", -1)
        ],
        dtype=dtype
    )
    return data, dtype, expected


@pytest.mark.parametrize('skiprows', [0, 1, 2, 3])
def test_structured_dtype_and_skiprows_no_empty_lines(
        skiprows, mixed_types_structured):
    data, dtype, expected = mixed_types_structured
    a = np.loadtxt(data, dtype=dtype, delimiter=";", skiprows=skiprows)
    assert_array_equal(a, expected[skiprows:])


def test_unpack_structured(mixed_types_structured):
    data, dtype, expected = mixed_types_structured

    a, b, c, d = np.loadtxt(data, dtype=dtype, delimiter=";", unpack=True)
    assert_array_equal(a, expected["f0"])
    assert_array_equal(b, expected["f1"])
    assert_array_equal(c, expected["f2"])
    assert_array_equal(d, expected["f3"])


def test_structured_dtype_with_shape():
    dtype = np.dtype([("a", "u1", 2), ("b", "u1", 2)])
    data = StringIO("0,1,2,3\n6,7,8,9\n")
    expected = np.array([((0, 1), (2, 3)), ((6, 7), (8, 9))], dtype=dtype)
    assert_array_equal(np.loadtxt(data, delimiter=",", dtype=dtype), expected)


def test_structured_dtype_with_multi_shape():
    dtype = np.dtype([("a", "u1", (2, 2))])
    data = StringIO("0 1 2 3\n")
    expected = np.array([(((0, 1), (2, 3)),)], dtype=dtype)
    assert_array_equal(np.loadtxt(data, dtype=dtype), expected)


def test_nested_structured_subarray():
    # Test from gh-16678
    point = np.dtype([('x', float), ('y', float)])
    dt = np.dtype([('code', int), ('points', point, (2,))])
    data = StringIO("100,1,2,3,4\n200,5,6,7,8\n")
    expected = np.array(
        [
            (100, [(1., 2.), (3., 4.)]),
            (200, [(5., 6.), (7., 8.)]),
        ],
        dtype=dt
    )
    assert_array_equal(np.loadtxt(data, dtype=dt, delimiter=","), expected)


def test_structured_dtype_offsets():
    # An aligned structured dtype will have additional padding
    dt = np.dtype("i1, i4, i1, i4, i1, i4", align=True)
    data = StringIO("1,2,3,4,5,6\n7,8,9,10,11,12\n")
    expected = np.array([(1, 2, 3, 4, 5, 6), (7, 8, 9, 10, 11, 12)], dtype=dt)
    assert_array_equal(np.loadtxt(data, delimiter=",", dtype=dt), expected)


@pytest.mark.parametrize("param", ("skiprows", "max_rows"))
def test_exception_negative_row_limits(param):
    """skiprows and max_rows should raise for negative parameters."""
    with pytest.raises(ValueError, match="argument must be nonnegative"):
        np.loadtxt("foo.bar", **{param: -3})


@pytest.mark.parametrize("param", ("skiprows", "max_rows"))
def test_exception_noninteger_row_limits(param):
    with pytest.raises(TypeError, match="argument must be an integer"):
        np.loadtxt("foo.bar", **{param: 1.0})


@pytest.mark.parametrize(
    "data, shape",
    [
        ("1 2 3 4 5\n", (1, 5)),  # Single row
        ("1\n2\n3\n4\n5\n", (5, 1)),  # Single column
    ]
)
def test_ndmin_single_row_or_col(data, shape):
    arr = np.array([1, 2, 3, 4, 5])
    arr2d = arr.reshape(shape)

    assert_array_equal(np.loadtxt(StringIO(data), dtype=int), arr)
    assert_array_equal(np.loadtxt(StringIO(data), dtype=int, ndmin=0), arr)
    assert_array_equal(np.loadtxt(StringIO(data), dtype=int, ndmin=1), arr)
    assert_array_equal(np.loadtxt(StringIO(data), dtype=int, ndmin=2), arr2d)


@pytest.mark.parametrize("badval", [-1, 3, None, "plate of shrimp"])
def test_bad_ndmin(badval):
    with pytest.raises(ValueError, match="Illegal value of ndmin keyword"):
        np.loadtxt("foo.bar", ndmin=badval)


@pytest.mark.parametrize(
    "ws",
    (
            " ",  # space
            "\t",  # tab
            "\u2003",  # em
            "\u00A0",  # non-break
            "\u3000",  # ideographic space
    )
)
def test_blank_lines_spaces_delimit(ws):
    txt = StringIO(
        f"1 2{ws}30\n\n{ws}\n"
        f"4 5 60{ws}\n  {ws}  \n"
        f"7 8 {ws} 90\n  # comment\n"
        f"3 2 1"
    )
    # NOTE: It is unclear that the `  # comment` should succeed. Except
    #       for delimiter=None, which should use any whitespace (and maybe
    #       should just be implemented closer to Python
    expected = np.array([[1, 2, 30], [4, 5, 60], [7, 8, 90], [3, 2, 1]])
    assert_equal(
        np.loadtxt(txt, dtype=int, delimiter=None, comments="#"), expected
    )


def test_blank_lines_normal_delimiter():
    txt = StringIO('1,2,30\n\n4,5,60\n\n7,8,90\n# comment\n3,2,1')
    expected = np.array([[1, 2, 30], [4, 5, 60], [7, 8, 90], [3, 2, 1]])
    assert_equal(
        np.loadtxt(txt, dtype=int, delimiter=',', comments="#"), expected
    )


@pytest.mark.parametrize("dtype", (float, object))
def test_maxrows_no_blank_lines(dtype):
    txt = StringIO("1.5,2.5\n3.0,4.0\n5.5,6.0")
    res = np.loadtxt(txt, dtype=dtype, delimiter=",", max_rows=2)
    assert_equal(res.dtype, dtype)
    assert_equal(res, np.array([["1.5", "2.5"], ["3.0", "4.0"]], dtype=dtype))


@pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                    reason="PyPy bug in error formatting")
@pytest.mark.parametrize("dtype", (np.dtype("f8"), np.dtype("i2")))
def test_exception_message_bad_values(dtype):
    txt = StringIO("1,2\n3,XXX\n5,6")
    msg = f"could not convert string 'XXX' to {dtype} at row 1, column 2"
    with pytest.raises(ValueError, match=msg):
        np.loadtxt(txt, dtype=dtype, delimiter=",")


def test_converters_negative_indices():
    txt = StringIO('1.5,2.5\n3.0,XXX\n5.5,6.0')
    conv = {-1: lambda s: np.nan if s == 'XXX' else float(s)}
    expected = np.array([[1.5, 2.5], [3.0, np.nan], [5.5, 6.0]])
    res = np.loadtxt(txt, dtype=np.float64, delimiter=",", converters=conv)
    assert_equal(res, expected)


def test_converters_negative_indices_with_usecols():
    txt = StringIO('1.5,2.5,3.5\n3.0,4.0,XXX\n5.5,6.0,7.5\n')
    conv = {-1: lambda s: np.nan if s == 'XXX' else float(s)}
    expected = np.array([[1.5, 3.5], [3.0, np.nan], [5.5, 7.5]])
    res = np.loadtxt(
        txt,
        dtype=np.float64,
        delimiter=",",
        converters=conv,
        usecols=[0, -1],
    )
    assert_equal(res, expected)

    # Second test with variable number of rows:
    res = np.loadtxt(StringIO('''0,1,2\n0,1,2,3,4'''), delimiter=",",
                     usecols=[0, -1], converters={-1: (lambda x: -1)})
    assert_array_equal(res, [[0, -1], [0, -1]])


def test_ragged_error():
    rows = ["1,2,3", "1,2,3", "4,3,2,1"]
    with pytest.raises(ValueError,
            match="the number of columns changed from 3 to 4 at row 3"):
        np.loadtxt(rows, delimiter=",")


def test_ragged_usecols():
    # usecols, and negative ones, work even with varying number of columns.
    txt = StringIO("0,0,XXX\n0,XXX,0,XXX\n0,XXX,XXX,0,XXX\n")
    expected = np.array([[0, 0], [0, 0], [0, 0]])
    res = np.loadtxt(txt, dtype=float, delimiter=",", usecols=[0, -2])
    assert_equal(res, expected)

    txt = StringIO("0,0,XXX\n0\n0,XXX,XXX,0,XXX\n")
    with pytest.raises(ValueError,
                match="invalid column index -2 at row 2 with 1 columns"):
        # There is no -2 column in the second row:
        np.loadtxt(txt, dtype=float, delimiter=",", usecols=[0, -2])


def test_empty_usecols():
    txt = StringIO("0,0,XXX\n0,XXX,0,XXX\n0,XXX,XXX,0,XXX\n")
    res = np.loadtxt(txt, dtype=np.dtype([]), delimiter=",", usecols=[])
    assert res.shape == (3,)
    assert res.dtype == np.dtype([])


@pytest.mark.parametrize("c1", ["a", "の", "🫕"])
@pytest.mark.parametrize("c2", ["a", "の", "🫕"])
def test_large_unicode_characters(c1, c2):
    # c1 and c2 span ascii, 16bit and 32bit range.
    txt = StringIO(f"a,{c1},c,1.0\ne,{c2},2.0,g")
    res = np.loadtxt(txt, dtype=np.dtype('U12'), delimiter=",")
    expected = np.array(
        [f"a,{c1},c,1.0".split(","), f"e,{c2},2.0,g".split(",")],
        dtype=np.dtype('U12')
    )
    assert_equal(res, expected)


def test_unicode_with_converter():
    txt = StringIO("cat,dog\nαβγ,δεζ\nabc,def\n")
    conv = {0: lambda s: s.upper()}
    res = np.loadtxt(
        txt,
        dtype=np.dtype("U12"),
        converters=conv,
        delimiter=",",
        encoding=None
    )
    expected = np.array([['CAT', 'dog'], ['ΑΒΓ', 'δεζ'], ['ABC', 'def']])
    assert_equal(res, expected)


def test_converter_with_structured_dtype():
    txt = StringIO('1.5,2.5,Abc\n3.0,4.0,dEf\n5.5,6.0,ghI\n')
    dt = np.dtype([('m', np.int32), ('r', np.float32), ('code', 'U8')])
    conv = {0: lambda s: int(10 * float(s)), -1: lambda s: s.upper()}
    res = np.loadtxt(txt, dtype=dt, delimiter=",", converters=conv)
    expected = np.array(
        [(15, 2.5, 'ABC'), (30, 4.0, 'DEF'), (55, 6.0, 'GHI')], dtype=dt
    )
    assert_equal(res, expected)


def test_converter_with_unicode_dtype():
    """
    With the 'bytes' encoding, tokens are encoded prior to being
    passed to the converter. This means that the output of the converter may
    be bytes instead of unicode as expected by `read_rows`.

    This test checks that outputs from the above scenario are properly decoded
    prior to parsing by `read_rows`.
    """
    txt = StringIO('abc,def\nrst,xyz')
    conv = bytes.upper
    res = np.loadtxt(
            txt, dtype=np.dtype("U3"), converters=conv, delimiter=",",
            encoding="bytes")
    expected = np.array([['ABC', 'DEF'], ['RST', 'XYZ']])
    assert_equal(res, expected)


def test_read_huge_row():
    row = "1.5, 2.5," * 50000
    row = row[:-1] + "\n"
    txt = StringIO(row * 2)
    res = np.loadtxt(txt, delimiter=",", dtype=float)
    assert_equal(res, np.tile([1.5, 2.5], (2, 50000)))


@pytest.mark.parametrize("dtype", "edfgFDG")
def test_huge_float(dtype):
    # Covers a non-optimized path that is rarely taken:
    field = "0" * 1000 + ".123456789"
    dtype = np.dtype(dtype)
    value = np.loadtxt([field], dtype=dtype)[()]
    assert value == dtype.type("0.123456789")


@pytest.mark.parametrize(
    ("given_dtype", "expected_dtype"),
    [
        ("S", np.dtype("S5")),
        ("U", np.dtype("U5")),
    ],
)
def test_string_no_length_given(given_dtype, expected_dtype):
    """
    The given dtype is just 'S' or 'U' with no length. In these cases, the
    length of the resulting dtype is determined by the longest string found
    in the file.
    """
    txt = StringIO("AAA,5-1\nBBBBB,0-3\nC,4-9\n")
    res = np.loadtxt(txt, dtype=given_dtype, delimiter=",")
    expected = np.array(
        [['AAA', '5-1'], ['BBBBB', '0-3'], ['C', '4-9']], dtype=expected_dtype
    )
    assert_equal(res, expected)
    assert_equal(res.dtype, expected_dtype)


def test_float_conversion():
    """
    Some tests that the conversion to float64 works as accurately as the
    Python built-in `float` function. In a naive version of the float parser,
    these strings resulted in values that were off by an ULP or two.
    """
    strings = [
        '0.9999999999999999',
        '9876543210.123456',
        '5.43215432154321e+300',
        '0.901',
        '0.333',
    ]
    txt = StringIO('\n'.join(strings))
    res = np.loadtxt(txt)
    expected = np.array([float(s) for s in strings])
    assert_equal(res, expected)


def test_bool():
    # Simple test for bool via integer
    txt = StringIO("1, 0\n10, -1")
    res = np.loadtxt(txt, dtype=bool, delimiter=",")
    assert res.dtype == bool
    assert_array_equal(res, [[True, False], [True, True]])
    # Make sure we use only 1 and 0 on the byte level:
    assert_array_equal(res.view(np.uint8), [[1, 0], [1, 1]])


@pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                    reason="PyPy bug in error formatting")
@pytest.mark.parametrize("dtype", np.typecodes["AllInteger"])
@pytest.mark.filterwarnings("error:.*integer via a float.*:DeprecationWarning")
def test_integer_signs(dtype):
    dtype = np.dtype(dtype)
    assert np.loadtxt(["+2"], dtype=dtype) == 2
    if dtype.kind == "u":
        with pytest.raises(ValueError):
            np.loadtxt(["-1\n"], dtype=dtype)
    else:
        assert np.loadtxt(["-2\n"], dtype=dtype) == -2

    for sign in ["++", "+-", "--", "-+"]:
        with pytest.raises(ValueError):
            np.loadtxt([f"{sign}2\n"], dtype=dtype)


@pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                    reason="PyPy bug in error formatting")
@pytest.mark.parametrize("dtype", np.typecodes["AllInteger"])
@pytest.mark.filterwarnings("error:.*integer via a float.*:DeprecationWarning")
def test_implicit_cast_float_to_int_fails(dtype):
    txt = StringIO("1.0, 2.1, 3.7\n4, 5, 6")
    with pytest.raises(ValueError):
        np.loadtxt(txt, dtype=dtype, delimiter=",")

@pytest.mark.parametrize("dtype", (np.complex64, np.complex128))
@pytest.mark.parametrize("with_parens", (False, True))
def test_complex_parsing(dtype, with_parens):
    s = "(1.0-2.5j),3.75,(7+-5.0j)\n(4),(-19e2j),(0)"
    if not with_parens:
        s = s.replace("(", "").replace(")", "")

    res = np.loadtxt(StringIO(s), dtype=dtype, delimiter=",")
    expected = np.array(
        [[1.0 - 2.5j, 3.75, 7 - 5j], [4.0, -1900j, 0]], dtype=dtype
    )
    assert_equal(res, expected)


def test_read_from_generator():
    def gen():
        for i in range(4):
            yield f"{i},{2 * i},{i**2}"

    res = np.loadtxt(gen(), dtype=int, delimiter=",")
    expected = np.array([[0, 0, 0], [1, 2, 1], [2, 4, 4], [3, 6, 9]])
    assert_equal(res, expected)


def test_read_from_generator_multitype():
    def gen():
        for i in range(3):
            yield f"{i} {i / 4}"

    res = np.loadtxt(gen(), dtype="i, d", delimiter=" ")
    expected = np.array([(0, 0.0), (1, 0.25), (2, 0.5)], dtype="i, d")
    assert_equal(res, expected)


def test_read_from_bad_generator():
    def gen():
        yield from ["1,2", b"3, 5", 12738]

    with pytest.raises(
            TypeError, match=r"non-string returned while reading data"):
        np.loadtxt(gen(), dtype="i, i", delimiter=",")


@pytest.mark.skipif(not HAS_REFCOUNT, reason="Python lacks refcounts")
def test_object_cleanup_on_read_error():
    sentinel = object()
    already_read = 0

    def conv(x):
        nonlocal already_read
        if already_read > 4999:
            raise ValueError("failed half-way through!")
        already_read += 1
        return sentinel

    txt = StringIO("x\n" * 10000)

    with pytest.raises(ValueError, match="at row 5000, column 1"):
        np.loadtxt(txt, dtype=object, converters={0: conv})

    assert sys.getrefcount(sentinel) == 2


@pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                    reason="PyPy bug in error formatting")
def test_character_not_bytes_compatible():
    """Test exception when a character cannot be encoded as 'S'."""
    data = StringIO("–")  # == \u2013
    with pytest.raises(ValueError):
        np.loadtxt(data, dtype="S5")


@pytest.mark.parametrize("conv", (0, [float], ""))
def test_invalid_converter(conv):
    msg = (
        "converters must be a dictionary mapping columns to converter "
        "functions or a single callable."
    )
    with pytest.raises(TypeError, match=msg):
        np.loadtxt(StringIO("1 2\n3 4"), converters=conv)


@pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                    reason="PyPy bug in error formatting")
def test_converters_dict_raises_non_integer_key():
    with pytest.raises(TypeError, match="keys of the converters dict"):
        np.loadtxt(StringIO("1 2\n3 4"), converters={"a": int})
    with pytest.raises(TypeError, match="keys of the converters dict"):
        np.loadtxt(StringIO("1 2\n3 4"), converters={"a": int}, usecols=0)


@pytest.mark.parametrize("bad_col_ind", (3, -3))
def test_converters_dict_raises_non_col_key(bad_col_ind):
    data = StringIO("1 2\n3 4")
    with pytest.raises(ValueError, match="converter specified for column"):
        np.loadtxt(data, converters={bad_col_ind: int})


def test_converters_dict_raises_val_not_callable():
    with pytest.raises(TypeError,
                match="values of the converters dictionary must be callable"):
        np.loadtxt(StringIO("1 2\n3 4"), converters={0: 1})


@pytest.mark.parametrize("q", ('"', "'", "`"))
def test_quoted_field(q):
    txt = StringIO(
        f"{q}alpha, x{q}, 2.5\n{q}beta, y{q}, 4.5\n{q}gamma, z{q}, 5.0\n"
    )
    dtype = np.dtype([('f0', 'U8'), ('f1', np.float64)])
    expected = np.array(
        [("alpha, x", 2.5), ("beta, y", 4.5), ("gamma, z", 5.0)], dtype=dtype
    )

    res = np.loadtxt(txt, dtype=dtype, delimiter=",", quotechar=q)
    assert_array_equal(res, expected)


@pytest.mark.parametrize("q", ('"', "'", "`"))
def test_quoted_field_with_whitepace_delimiter(q):
    txt = StringIO(
        f"{q}alpha, x{q}     2.5\n{q}beta, y{q} 4.5\n{q}gamma, z{q}   5.0\n"
    )
    dtype = np.dtype([('f0', 'U8'), ('f1', np.float64)])
    expected = np.array(
        [("alpha, x", 2.5), ("beta, y", 4.5), ("gamma, z", 5.0)], dtype=dtype
    )

    res = np.loadtxt(txt, dtype=dtype, delimiter=None, quotechar=q)
    assert_array_equal(res, expected)


def test_quote_support_default():
    """Support for quoted fields is disabled by default."""
    txt = StringIO('"lat,long", 45, 30\n')
    dtype = np.dtype([('f0', 'U24'), ('f1', np.float64), ('f2', np.float64)])

    with pytest.raises(ValueError,
            match="the dtype passed requires 3 columns but 4 were"):
        np.loadtxt(txt, dtype=dtype, delimiter=",")

    # Enable quoting support with non-None value for quotechar param
    txt.seek(0)
    expected = np.array([("lat,long", 45., 30.)], dtype=dtype)

    res = np.loadtxt(txt, dtype=dtype, delimiter=",", quotechar='"')
    assert_array_equal(res, expected)


@pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                    reason="PyPy bug in error formatting")
def test_quotechar_multichar_error():
    txt = StringIO("1,2\n3,4")
    msg = r".*must be a single unicode character or None"
    with pytest.raises(TypeError, match=msg):
        np.loadtxt(txt, delimiter=",", quotechar="''")


def test_comment_multichar_error_with_quote():
    txt = StringIO("1,2\n3,4")
    msg = (
        "when multiple comments or a multi-character comment is given, "
        "quotes are not supported."
    )
    with pytest.raises(ValueError, match=msg):
        np.loadtxt(txt, delimiter=",", comments="123", quotechar='"')
    with pytest.raises(ValueError, match=msg):
        np.loadtxt(txt, delimiter=",", comments=["#", "%"], quotechar='"')

    # A single character string in a tuple is unpacked though:
    res = np.loadtxt(txt, delimiter=",", comments=("#",), quotechar="'")
    assert_equal(res, [[1, 2], [3, 4]])


def test_structured_dtype_with_quotes():
    data = StringIO(

            "1000;2.4;'alpha';-34\n"
            "2000;3.1;'beta';29\n"
            "3500;9.9;'gamma';120\n"
            "4090;8.1;'delta';0\n"
            "5001;4.4;'epsilon';-99\n"
            "6543;7.8;'omega';-1\n"

    )
    dtype = np.dtype(
        [('f0', np.uint16), ('f1', np.float64), ('f2', 'S7'), ('f3', np.int8)]
    )
    expected = np.array(
        [
            (1000, 2.4, "alpha", -34),
            (2000, 3.1, "beta", 29),
            (3500, 9.9, "gamma", 120),
            (4090, 8.1, "delta", 0),
            (5001, 4.4, "epsilon", -99),
            (6543, 7.8, "omega", -1)
        ],
        dtype=dtype
    )
    res = np.loadtxt(data, dtype=dtype, delimiter=";", quotechar="'")
    assert_array_equal(res, expected)


def test_quoted_field_is_not_empty():
    txt = StringIO('1\n\n"4"\n""')
    expected = np.array(["1", "4", ""], dtype="U1")
    res = np.loadtxt(txt, delimiter=",", dtype="U1", quotechar='"')
    assert_equal(res, expected)

def test_quoted_field_is_not_empty_nonstrict():
    # Same as test_quoted_field_is_not_empty but check that we are not strict
    # about missing closing quote (this is the `csv.reader` default also)
    txt = StringIO('1\n\n"4"\n"')
    expected = np.array(["1", "4", ""], dtype="U1")
    res = np.loadtxt(txt, delimiter=",", dtype="U1", quotechar='"')
    assert_equal(res, expected)

def test_consecutive_quotechar_escaped():
    txt = StringIO('"Hello, my name is ""Monty""!"')
    expected = np.array('Hello, my name is "Monty"!', dtype="U40")
    res = np.loadtxt(txt, dtype="U40", delimiter=",", quotechar='"')
    assert_equal(res, expected)


@pytest.mark.parametrize("data", ("", "\n\n\n", "# 1 2 3\n# 4 5 6\n"))
@pytest.mark.parametrize("ndmin", (0, 1, 2))
@pytest.mark.parametrize("usecols", [None, (1, 2, 3)])
def test_warn_on_no_data(data, ndmin, usecols):
    """Check that a UserWarning is emitted when no data is read from input."""
    if usecols is not None:
        expected_shape = (0, 3)
    elif ndmin == 2:
        expected_shape = (0, 1)  # guess a single column?!
    else:
        expected_shape = (0,)

    txt = StringIO(data)
    with pytest.warns(UserWarning, match="input contained no data"):
        res = np.loadtxt(txt, ndmin=ndmin, usecols=usecols)
    assert res.shape == expected_shape

    with NamedTemporaryFile(mode="w") as fh:
        fh.write(data)
        fh.seek(0)
        with pytest.warns(UserWarning, match="input contained no data"):
            res = np.loadtxt(txt, ndmin=ndmin, usecols=usecols)
        assert res.shape == expected_shape

@pytest.mark.parametrize("skiprows", (2, 3))
def test_warn_on_skipped_data(skiprows):
    data = "1 2 3\n4 5 6"
    txt = StringIO(data)
    with pytest.warns(UserWarning, match="input contained no data"):
        np.loadtxt(txt, skiprows=skiprows)


@pytest.mark.parametrize(["dtype", "value"], [
        ("i2", 0x0001), ("u2", 0x0001),
        ("i4", 0x00010203), ("u4", 0x00010203),
        ("i8", 0x0001020304050607), ("u8", 0x0001020304050607),
        # The following values are constructed to lead to unique bytes:
        ("float16", 3.07e-05),
        ("float32", 9.2557e-41), ("complex64", 9.2557e-41 + 2.8622554e-29j),
        ("float64", -1.758571353180402e-24),
        # Here and below, the repr side-steps a small loss of precision in
        # complex `str` in PyPy (which is probably fine, as repr works):
        ("complex128", repr(5.406409232372729e-29 - 1.758571353180402e-24j)),
        # Use integer values that fit into double.  Everything else leads to
        # problems due to longdoubles going via double and decimal strings
        # causing rounding errors.
        ("longdouble", 0x01020304050607),
        ("clongdouble", repr(0x01020304050607 + (0x00121314151617 * 1j))),
        ("U2", "\U00010203\U000a0b0c")])
@pytest.mark.parametrize("swap", [True, False])
def test_byteswapping_and_unaligned(dtype, value, swap):
    # Try to create "interesting" values within the valid unicode range:
    dtype = np.dtype(dtype)
    data = [f"x,{value}\n"]  # repr as PyPy `str` truncates some
    if swap:
        dtype = dtype.newbyteorder()
    full_dt = np.dtype([("a", "S1"), ("b", dtype)], align=False)
    # The above ensures that the interesting "b" field is unaligned:
    assert full_dt.fields["b"][1] == 1
    res = np.loadtxt(data, dtype=full_dt, delimiter=",",
                     max_rows=1)  # max-rows prevents over-allocation
    assert res["b"] == dtype.type(value)


@pytest.mark.parametrize("dtype",
        np.typecodes["AllInteger"] + "efdFD" + "?")
def test_unicode_whitespace_stripping(dtype):
    # Test that all numeric types (and bool) strip whitespace correctly
    # \u202F is a narrow no-break space, `\n` is just a whitespace if quoted.
    # Currently, skip float128 as it did not always support this and has no
    # "custom" parsing:
    txt = StringIO(' 3 ,"\u202F2\n"')
    res = np.loadtxt(txt, dtype=dtype, delimiter=",", quotechar='"')
    assert_array_equal(res, np.array([3, 2]).astype(dtype))


@pytest.mark.parametrize("dtype", "FD")
def test_unicode_whitespace_stripping_complex(dtype):
    # Complex has a few extra cases since it has two components and
    # parentheses
    line = " 1 , 2+3j , ( 4+5j ), ( 6+-7j )  , 8j , ( 9j ) \n"
    data = [line, line.replace(" ", "\u202F")]
    res = np.loadtxt(data, dtype=dtype, delimiter=',')
    assert_array_equal(res, np.array([[1, 2 + 3j, 4 + 5j, 6 - 7j, 8j, 9j]] * 2))


@pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                    reason="PyPy bug in error formatting")
@pytest.mark.parametrize("dtype", "FD")
@pytest.mark.parametrize("field",
        ["1 +2j", "1+ 2j", "1+2 j", "1+-+3", "(1j", "(1", "(1+2j", "1+2j)"])
def test_bad_complex(dtype, field):
    with pytest.raises(ValueError):
        np.loadtxt([field + "\n"], dtype=dtype, delimiter=",")


@pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                    reason="PyPy bug in error formatting")
@pytest.mark.parametrize("dtype",
            np.typecodes["AllInteger"] + "efgdFDG" + "?")
def test_nul_character_error(dtype):
    # Test that a \0 character is correctly recognized as an error even if
    # what comes before is valid (not everything gets parsed internally).
    if dtype.lower() == "g":
        pytest.xfail("longdouble/clongdouble assignment may misbehave.")
    with pytest.raises(ValueError):
        np.loadtxt(["1\000"], dtype=dtype, delimiter=",", quotechar='"')


@pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                    reason="PyPy bug in error formatting")
@pytest.mark.parametrize("dtype",
        np.typecodes["AllInteger"] + "efgdFDG" + "?")
def test_no_thousands_support(dtype):
    # Mainly to document behaviour, Python supports thousands like 1_1.
    # (e and G may end up using different conversion and support it, this is
    # a bug but happens...)
    if dtype == "e":
        pytest.skip("half assignment currently uses Python float converter")
    if dtype in "eG":
        pytest.xfail("clongdouble assignment is buggy (uses `complex`?).")

    assert int("1_1") == float("1_1") == complex("1_1") == 11
    with pytest.raises(ValueError):
        np.loadtxt(["1_1\n"], dtype=dtype)


@pytest.mark.parametrize("data", [
    ["1,2\n", "2\n,3\n"],
    ["1,2\n", "2\r,3\n"]])
def test_bad_newline_in_iterator(data):
    # In NumPy <=1.22 this was accepted, because newlines were completely
    # ignored when the input was an iterable.  This could be changed, but right
    # now, we raise an error.
    msg = "Found an unquoted embedded newline within a single line"
    with pytest.raises(ValueError, match=msg):
        np.loadtxt(data, delimiter=",")


@pytest.mark.parametrize("data", [
    ["1,2\n", "2,3\r\n"],  # a universal newline
    ["1,2\n", "'2\n',3\n"],  # a quoted newline
    ["1,2\n", "'2\r',3\n"],
    ["1,2\n", "'2\r\n',3\n"],
])
def test_good_newline_in_iterator(data):
    # The quoted newlines will be untransformed here, but are just whitespace.
    res = np.loadtxt(data, delimiter=",", quotechar="'")
    assert_array_equal(res, [[1., 2.], [2., 3.]])


@pytest.mark.parametrize("newline", ["\n", "\r", "\r\n"])
def test_universal_newlines_quoted(newline):
    # Check that universal newline support within the tokenizer is not applied
    # to quoted fields.  (note that lines must end in newline or quoted
    # fields will not include a newline at all)
    data = ['1,"2\n"\n', '3,"4\n', '1"\n']
    data = [row.replace("\n", newline) for row in data]
    res = np.loadtxt(data, dtype=object, delimiter=",", quotechar='"')
    assert_array_equal(res, [['1', f'2{newline}'], ['3', f'4{newline}1']])


def test_null_character():
    # Basic tests to check that the NUL character is not special:
    res = np.loadtxt(["1\0002\0003\n", "4\0005\0006"], delimiter="\000")
    assert_array_equal(res, [[1, 2, 3], [4, 5, 6]])

    # Also not as part of a field (avoid unicode/arrays as unicode strips \0)
    res = np.loadtxt(["1\000,2\000,3\n", "4\000,5\000,6"],
                     delimiter=",", dtype=object)
    assert res.tolist() == [["1\000", "2\000", "3"], ["4\000", "5\000", "6"]]


def test_iterator_fails_getting_next_line():
    class BadSequence:
        def __len__(self):
            return 100

        def __getitem__(self, item):
            if item == 50:
                raise RuntimeError("Bad things happened!")
            return f"{item}, {item + 1}"

    with pytest.raises(RuntimeError, match="Bad things happened!"):
        np.loadtxt(BadSequence(), dtype=int, delimiter=",")


class TestCReaderUnitTests:
    # These are internal tests for path that should not be possible to hit
    # unless things go very very wrong somewhere.
    def test_not_an_filelike(self):
        with pytest.raises(AttributeError, match=".*read"):
            np._core._multiarray_umath._load_from_filelike(
                object(), dtype=np.dtype("i"), filelike=True)

    def test_filelike_read_fails(self):
        # Can only be reached if loadtxt opens the file, so it is hard to do
        # via the public interface (although maybe not impossible considering
        # the current "DataClass" backing).
        class BadFileLike:
            counter = 0

            def read(self, size):
                self.counter += 1
                if self.counter > 20:
                    raise RuntimeError("Bad bad bad!")
                return "1,2,3\n"

        with pytest.raises(RuntimeError, match="Bad bad bad!"):
            np._core._multiarray_umath._load_from_filelike(
                BadFileLike(), dtype=np.dtype("i"), filelike=True)

    def test_filelike_bad_read(self):
        # Can only be reached if loadtxt opens the file, so it is hard to do
        # via the public interface (although maybe not impossible considering
        # the current "DataClass" backing).

        class BadFileLike:
            counter = 0

            def read(self, size):
                return 1234  # not a string!

        with pytest.raises(TypeError,
                    match="non-string returned while reading data"):
            np._core._multiarray_umath._load_from_filelike(
                BadFileLike(), dtype=np.dtype("i"), filelike=True)

    def test_not_an_iter(self):
        with pytest.raises(TypeError,
                    match="error reading from object, expected an iterable"):
            np._core._multiarray_umath._load_from_filelike(
                object(), dtype=np.dtype("i"), filelike=False)

    def test_bad_type(self):
        with pytest.raises(TypeError, match="internal error: dtype must"):
            np._core._multiarray_umath._load_from_filelike(
                object(), dtype="i", filelike=False)

    def test_bad_encoding(self):
        with pytest.raises(TypeError, match="encoding must be a unicode"):
            np._core._multiarray_umath._load_from_filelike(
                object(), dtype=np.dtype("i"), filelike=False, encoding=123)

    @pytest.mark.parametrize("newline", ["\r", "\n", "\r\n"])
    def test_manual_universal_newlines(self, newline):
        # This is currently not available to users, because we should always
        # open files with universal newlines enabled `newlines=None`.
        # (And reading from an iterator uses slightly different code paths.)
        # We have no real support for `newline="\r"` or `newline="\n" as the
        # user cannot specify those options.
        data = StringIO('0\n1\n"2\n"\n3\n4 #\n'.replace("\n", newline),
                        newline="")

        res = np._core._multiarray_umath._load_from_filelike(
            data, dtype=np.dtype("U10"), filelike=True,
            quote='"', comment="#", skiplines=1)
        assert_array_equal(res[:, 0], ["1", f"2{newline}", "3", "4 "])


def test_delimiter_comment_collision_raises():
    with pytest.raises(TypeError, match=".*control characters.*incompatible"):
        np.loadtxt(StringIO("1, 2, 3"), delimiter=",", comments=",")


def test_delimiter_quotechar_collision_raises():
    with pytest.raises(TypeError, match=".*control characters.*incompatible"):
        np.loadtxt(StringIO("1, 2, 3"), delimiter=",", quotechar=",")


def test_comment_quotechar_collision_raises():
    with pytest.raises(TypeError, match=".*control characters.*incompatible"):
        np.loadtxt(StringIO("1 2 3"), comments="#", quotechar="#")


def test_delimiter_and_multiple_comments_collision_raises():
    with pytest.raises(
        TypeError, match="Comment characters.*cannot include the delimiter"
    ):
        np.loadtxt(StringIO("1, 2, 3"), delimiter=",", comments=["#", ","])


@pytest.mark.parametrize(
    "ws",
    (
        " ",  # space
        "\t",  # tab
        "\u2003",  # em
        "\u00A0",  # non-break
        "\u3000",  # ideographic space
    )
)
def test_collision_with_default_delimiter_raises(ws):
    with pytest.raises(TypeError, match=".*control characters.*incompatible"):
        np.loadtxt(StringIO(f"1{ws}2{ws}3\n4{ws}5{ws}6\n"), comments=ws)
    with pytest.raises(TypeError, match=".*control characters.*incompatible"):
        np.loadtxt(StringIO(f"1{ws}2{ws}3\n4{ws}5{ws}6\n"), quotechar=ws)


@pytest.mark.parametrize("nl", ("\n", "\r"))
def test_control_character_newline_raises(nl):
    txt = StringIO(f"1{nl}2{nl}3{nl}{nl}4{nl}5{nl}6{nl}{nl}")
    msg = "control character.*cannot be a newline"
    with pytest.raises(TypeError, match=msg):
        np.loadtxt(txt, delimiter=nl)
    with pytest.raises(TypeError, match=msg):
        np.loadtxt(txt, comments=nl)
    with pytest.raises(TypeError, match=msg):
        np.loadtxt(txt, quotechar=nl)


@pytest.mark.parametrize(
    ("generic_data", "long_datum", "unitless_dtype", "expected_dtype"),
    [
        ("2012-03", "2013-01-15", "M8", "M8[D]"),  # Datetimes
        ("spam-a-lot", "tis_but_a_scratch", "U", "U17"),  # str
    ],
)
@pytest.mark.parametrize("nrows", (10, 50000, 60000))  # lt, eq, gt chunksize
def test_parametric_unit_discovery(
    generic_data, long_datum, unitless_dtype, expected_dtype, nrows
):
    """Check that the correct unit (e.g. month, day, second) is discovered from
    the data when a user specifies a unitless datetime."""
    # Unit should be "D" (days) due to last entry
    data = [generic_data] * nrows + [long_datum]
    expected = np.array(data, dtype=expected_dtype)
    assert len(data) == nrows + 1
    assert len(data) == len(expected)

    # file-like path
    txt = StringIO("\n".join(data))
    a = np.loadtxt(txt, dtype=unitless_dtype)
    assert len(a) == len(expected)
    assert a.dtype == expected.dtype
    assert_equal(a, expected)

    # file-obj path
    fd, fname = mkstemp()
    os.close(fd)
    with open(fname, "w") as fh:
        fh.write("\n".join(data) + "\n")
    # loading the full file...
    a = np.loadtxt(fname, dtype=unitless_dtype)
    assert len(a) == len(expected)
    assert a.dtype == expected.dtype
    assert_equal(a, expected)
    # loading half of the file...
    a = np.loadtxt(fname, dtype=unitless_dtype, max_rows=int(nrows / 2))
    os.remove(fname)
    assert len(a) == int(nrows / 2)
    assert_equal(a, expected[:int(nrows / 2)])


def test_str_dtype_unit_discovery_with_converter():
    data = ["spam-a-lot"] * 60000 + ["XXXtis_but_a_scratch"]
    expected = np.array(
        ["spam-a-lot"] * 60000 + ["tis_but_a_scratch"], dtype="U17"
    )
    conv = lambda s: s.removeprefix("XXX")

    # file-like path
    txt = StringIO("\n".join(data))
    a = np.loadtxt(txt, dtype="U", converters=conv)
    assert a.dtype == expected.dtype
    assert_equal(a, expected)

    # file-obj path
    fd, fname = mkstemp()
    os.close(fd)
    with open(fname, "w") as fh:
        fh.write("\n".join(data))
    a = np.loadtxt(fname, dtype="U", converters=conv)
    os.remove(fname)
    assert a.dtype == expected.dtype
    assert_equal(a, expected)


@pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                    reason="PyPy bug in error formatting")
def test_control_character_empty():
    with pytest.raises(TypeError, match="Text reading control character must"):
        np.loadtxt(StringIO("1 2 3"), delimiter="")
    with pytest.raises(TypeError, match="Text reading control character must"):
        np.loadtxt(StringIO("1 2 3"), quotechar="")
    with pytest.raises(ValueError, match="comments cannot be an empty string"):
        np.loadtxt(StringIO("1 2 3"), comments="")
    with pytest.raises(ValueError, match="comments cannot be an empty string"):
        np.loadtxt(StringIO("1 2 3"), comments=["#", ""])


def test_control_characters_as_bytes():
    """Byte control characters (comments, delimiter) are supported."""
    a = np.loadtxt(StringIO("#header\n1,2,3"), comments=b"#", delimiter=b",")
    assert_equal(a, [1, 2, 3])


@pytest.mark.filterwarnings('ignore::UserWarning')
def test_field_growing_cases():
    # Test empty field appending/growing (each field still takes 1 character)
    # to see if the final field appending does not create issues.
    res = np.loadtxt([""], delimiter=",", dtype=bytes)
    assert len(res) == 0

    for i in range(1, 1024):
        res = np.loadtxt(["," * i], delimiter=",", dtype=bytes, max_rows=10)
        assert len(res) == i + 1

@pytest.mark.parametrize("nmax", (10000, 50000, 55000, 60000))
def test_maxrows_exceeding_chunksize(nmax):
    # tries to read all of the file,
    # or less, equal, greater than _loadtxt_chunksize
    file_length = 60000

    # file-like path
    data = ["a 0.5 1"] * file_length
    txt = StringIO("\n".join(data))
    res = np.loadtxt(txt, dtype=str, delimiter=" ", max_rows=nmax)
    assert len(res) == nmax

    # file-obj path
    fd, fname = mkstemp()
    os.close(fd)
    with open(fname, "w") as fh:
        fh.write("\n".join(data))
    res = np.loadtxt(fname, dtype=str, delimiter=" ", max_rows=nmax)
    os.remove(fname)
    assert len(res) == nmax

@pytest.mark.parametrize("nskip", (0, 10000, 12345, 50000, 67891, 100000))
def test_skiprow_exceeding_maxrows_exceeding_chunksize(tmpdir, nskip):
    # tries to read a file in chunks by skipping a variable amount of lines,
    # less, equal, greater than max_rows
    file_length = 110000
    data = "\n".join(f"{i} a 0.5 1" for i in range(1, file_length + 1))
    expected_length = min(60000, file_length - nskip)
    expected = np.arange(nskip + 1, nskip + 1 + expected_length).astype(str)

    # file-like path
    txt = StringIO(data)
    res = np.loadtxt(txt, dtype='str', delimiter=" ", skiprows=nskip, max_rows=60000)
    assert len(res) == expected_length
    # are the right lines read in res?
    assert_array_equal(expected, res[:, 0])

    # file-obj path
    tmp_file = tmpdir / "test_data.txt"
    tmp_file.write(data)
    fname = str(tmp_file)
    res = np.loadtxt(fname, dtype='str', delimiter=" ", skiprows=nskip, max_rows=60000)
    assert len(res) == expected_length
    # are the right lines read in res?
    assert_array_equal(expected, res[:, 0])