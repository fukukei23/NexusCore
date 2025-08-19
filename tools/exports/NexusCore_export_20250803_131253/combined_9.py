
# === NexusCore/src\dev_tools\test_manager.py ===
# test_manager.py
import os
import sys
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# モジュールパスを追加（src配下を明示）
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # src/
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, "modules"))

# モジュールインポート（例）
try:
    from whisper_handler import transcribe_audio
    from code_generator import generate_code_from_text
    from tester import save_and_test_code
    from diff_viewer import generate_diff
except ImportError as e:
    print(f"❌ モジュールの読み込みに失敗しました: {e}")
    sys.exit(1)

# テスト関数
def run_all_tests(audio_path=None, transcript_text=None):
    if not api_key:
        print("❌ .envにOPENAI_API_KEYが定義されていません。")
        return

    print("✅ OpenCodeInterpreter テスト開始\n")

    if audio_path:
        print(f"🎤 音声ファイル文字起こし: {audio_path}")
        transcript = transcribe_audio(audio_path)
    elif transcript_text:
        print(f"📝 指定されたテキストからコード生成：{transcript_text}")
        transcript = transcript_text
    else:
        print("⚠️ 音声ファイルまたはテキストを指定してください。")
        return

    print("\n🧠 GPTコード生成中...")
    code = generate_code_from_text(transcript)
    print("\n" + code)

    print("\n🧪 テスト実行中...")
    result = save_and_test_code(code)
    print("\n" + result)

    print("\n🔍 差分表示...")
    diff = generate_diff("", code)
    print(diff)

    print("\n✅ テスト完了")

# 実行例（任意の音声 or テキストで切り替え）
if __name__ == "__main__":
    # audio_path = os.path.join(BASE_DIR, "sandbox_output", "sample_audio.wav")
    audio_path = None  # 音声ファイルがない場合は None
    transcript_text = "偶数か奇数かを判定するPython関数を作成して"

    run_all_tests(audio_path, transcript_text)

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pythonwin\pywin\Demos\app\demoutils.py ===
# Utilities for the demos

import sys

import win32api
import win32con
import win32ui

NotScriptMsg = """\
This demo program is not designed to be run as a Script, but is
probably used by some other test program.  Please try another demo.
"""

NeedGUIMsg = """\
This demo program can only be run from inside of Pythonwin

You must start Pythonwin, and select 'Run' from the toolbar or File menu
"""


NeedAppMsg = """\
This demo program is a 'Pythonwin Application'.

It is more demo code than an example of Pythonwin's capabilities.

To run it, you must execute the command:
pythonwin.exe /app "%s"

Would you like to execute it now?
"""


def NotAScript():
    import win32ui

    win32ui.MessageBox(NotScriptMsg, "Demos")


def NeedGoodGUI():
    from pywin.framework.app import HaveGoodGUI

    rc = HaveGoodGUI()
    if not rc:
        win32ui.MessageBox(NeedGUIMsg, "Demos")
    return rc


def NeedApp():
    import win32ui

    rc = win32ui.MessageBox(NeedAppMsg % sys.argv[0], "Demos", win32con.MB_YESNO)
    if rc == win32con.IDYES:
        try:
            parent = win32ui.GetMainFrame().GetSafeHwnd()
            win32api.ShellExecute(
                parent, None, "pythonwin.exe", '/app "%s"' % sys.argv[0], None, 1
            )
        except win32api.error as details:
            win32ui.MessageBox("Error executing command - %s" % (details), "Demos")


if __name__ == "__main__":
    NotAScript()

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\dev_tools\test_manager.py ===
# test_manager.py
import os
import sys
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# モジュールパスを追加（src配下を明示）
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # src/
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, "modules"))

# モジュールインポート（例）
try:
    from whisper_handler import transcribe_audio
    from code_generator import generate_code_from_text
    from tester import save_and_test_code
    from diff_viewer import generate_diff
except ImportError as e:
    print(f"❌ モジュールの読み込みに失敗しました: {e}")
    sys.exit(1)

# テスト関数
def run_all_tests(audio_path=None, transcript_text=None):
    if not api_key:
        print("❌ .envにOPENAI_API_KEYが定義されていません。")
        return

    print("✅ OpenCodeInterpreter テスト開始\n")

    if audio_path:
        print(f"🎤 音声ファイル文字起こし: {audio_path}")
        transcript = transcribe_audio(audio_path)
    elif transcript_text:
        print(f"📝 指定されたテキストからコード生成：{transcript_text}")
        transcript = transcript_text
    else:
        print("⚠️ 音声ファイルまたはテキストを指定してください。")
        return

    print("\n🧠 GPTコード生成中...")
    code = generate_code_from_text(transcript)
    print("\n" + code)

    print("\n🧪 テスト実行中...")
    result = save_and_test_code(code)
    print("\n" + result)

    print("\n🔍 差分表示...")
    diff = generate_diff("", code)
    print(diff)

    print("\n✅ テスト完了")

# 実行例（任意の音声 or テキストで切り替え）
if __name__ == "__main__":
    # audio_path = os.path.join(BASE_DIR, "sandbox_output", "sample_audio.wav")
    audio_path = None  # 音声ファイルがない場合は None
    transcript_text = "偶数か奇数かを判定するPython関数を作成して"

    run_all_tests(audio_path, transcript_text)

# === NexusCore/openenv\Lib\site-packages\numpy\lib\_nanfunctions_impl.py ===
"""
Functions that ignore NaN.

Functions
---------

- `nanmin` -- minimum non-NaN value
- `nanmax` -- maximum non-NaN value
- `nanargmin` -- index of minimum non-NaN value
- `nanargmax` -- index of maximum non-NaN value
- `nansum` -- sum of non-NaN values
- `nanprod` -- product of non-NaN values
- `nancumsum` -- cumulative sum of non-NaN values
- `nancumprod` -- cumulative product of non-NaN values
- `nanmean` -- mean of non-NaN values
- `nanvar` -- variance of non-NaN values
- `nanstd` -- standard deviation of non-NaN values
- `nanmedian` -- median of non-NaN values
- `nanquantile` -- qth quantile of non-NaN values
- `nanpercentile` -- qth percentile of non-NaN values

"""
import functools
import warnings

import numpy as np
import numpy._core.numeric as _nx
from numpy._core import overrides
from numpy.lib import _function_base_impl as fnb
from numpy.lib._function_base_impl import _weights_are_valid

array_function_dispatch = functools.partial(
    overrides.array_function_dispatch, module='numpy')


__all__ = [
    'nansum', 'nanmax', 'nanmin', 'nanargmax', 'nanargmin', 'nanmean',
    'nanmedian', 'nanpercentile', 'nanvar', 'nanstd', 'nanprod',
    'nancumsum', 'nancumprod', 'nanquantile'
    ]


def _nan_mask(a, out=None):
    """
    Parameters
    ----------
    a : array-like
        Input array with at least 1 dimension.
    out : ndarray, optional
        Alternate output array in which to place the result.  The default
        is ``None``; if provided, it must have the same shape as the
        expected output and will prevent the allocation of a new array.

    Returns
    -------
    y : bool ndarray or True
        A bool array where ``np.nan`` positions are marked with ``False``
        and other positions are marked with ``True``. If the type of ``a``
        is such that it can't possibly contain ``np.nan``, returns ``True``.
    """
    # we assume that a is an array for this private function

    if a.dtype.kind not in 'fc':
        return True

    y = np.isnan(a, out=out)
    y = np.invert(y, out=y)
    return y

def _replace_nan(a, val):
    """
    If `a` is of inexact type, make a copy of `a`, replace NaNs with
    the `val` value, and return the copy together with a boolean mask
    marking the locations where NaNs were present. If `a` is not of
    inexact type, do nothing and return `a` together with a mask of None.

    Note that scalars will end up as array scalars, which is important
    for using the result as the value of the out argument in some
    operations.

    Parameters
    ----------
    a : array-like
        Input array.
    val : float
        NaN values are set to val before doing the operation.

    Returns
    -------
    y : ndarray
        If `a` is of inexact type, return a copy of `a` with the NaNs
        replaced by the fill value, otherwise return `a`.
    mask: {bool, None}
        If `a` is of inexact type, return a boolean mask marking locations of
        NaNs, otherwise return None.

    """
    a = np.asanyarray(a)

    if a.dtype == np.object_:
        # object arrays do not support `isnan` (gh-9009), so make a guess
        mask = np.not_equal(a, a, dtype=bool)
    elif issubclass(a.dtype.type, np.inexact):
        mask = np.isnan(a)
    else:
        mask = None

    if mask is not None:
        a = np.array(a, subok=True, copy=True)
        np.copyto(a, val, where=mask)

    return a, mask


def _copyto(a, val, mask):
    """
    Replace values in `a` with NaN where `mask` is True.  This differs from
    copyto in that it will deal with the case where `a` is a numpy scalar.

    Parameters
    ----------
    a : ndarray or numpy scalar
        Array or numpy scalar some of whose values are to be replaced
        by val.
    val : numpy scalar
        Value used a replacement.
    mask : ndarray, scalar
        Boolean array. Where True the corresponding element of `a` is
        replaced by `val`. Broadcasts.

    Returns
    -------
    res : ndarray, scalar
        Array with elements replaced or scalar `val`.

    """
    if isinstance(a, np.ndarray):
        np.copyto(a, val, where=mask, casting='unsafe')
    else:
        a = a.dtype.type(val)
    return a


def _remove_nan_1d(arr1d, second_arr1d=None, overwrite_input=False):
    """
    Equivalent to arr1d[~arr1d.isnan()], but in a different order

    Presumably faster as it incurs fewer copies

    Parameters
    ----------
    arr1d : ndarray
        Array to remove nans from
    second_arr1d : ndarray or None
        A second array which will have the same positions removed as arr1d.
    overwrite_input : bool
        True if `arr1d` can be modified in place

    Returns
    -------
    res : ndarray
        Array with nan elements removed
    second_res : ndarray or None
        Second array with nan element positions of first array removed.
    overwrite_input : bool
        True if `res` can be modified in place, given the constraint on the
        input
    """
    if arr1d.dtype == object:
        # object arrays do not support `isnan` (gh-9009), so make a guess
        c = np.not_equal(arr1d, arr1d, dtype=bool)
    else:
        c = np.isnan(arr1d)

    s = np.nonzero(c)[0]
    if s.size == arr1d.size:
        warnings.warn("All-NaN slice encountered", RuntimeWarning,
                      stacklevel=6)
        if second_arr1d is None:
            return arr1d[:0], None, True
        else:
            return arr1d[:0], second_arr1d[:0], True
    elif s.size == 0:
        return arr1d, second_arr1d, overwrite_input
    else:
        if not overwrite_input:
            arr1d = arr1d.copy()
        # select non-nans at end of array
        enonan = arr1d[-s.size:][~c[-s.size:]]
        # fill nans in beginning of array with non-nans of end
        arr1d[s[:enonan.size]] = enonan

        if second_arr1d is None:
            return arr1d[:-s.size], None, True
        else:
            if not overwrite_input:
                second_arr1d = second_arr1d.copy()
            enonan = second_arr1d[-s.size:][~c[-s.size:]]
            second_arr1d[s[:enonan.size]] = enonan

            return arr1d[:-s.size], second_arr1d[:-s.size], True


def _divide_by_count(a, b, out=None):
    """
    Compute a/b ignoring invalid results. If `a` is an array the division
    is done in place. If `a` is a scalar, then its type is preserved in the
    output. If out is None, then a is used instead so that the division
    is in place. Note that this is only called with `a` an inexact type.

    Parameters
    ----------
    a : {ndarray, numpy scalar}
        Numerator. Expected to be of inexact type but not checked.
    b : {ndarray, numpy scalar}
        Denominator.
    out : ndarray, optional
        Alternate output array in which to place the result.  The default
        is ``None``; if provided, it must have the same shape as the
        expected output, but the type will be cast if necessary.

    Returns
    -------
    ret : {ndarray, numpy scalar}
        The return value is a/b. If `a` was an ndarray the division is done
        in place. If `a` is a numpy scalar, the division preserves its type.

    """
    with np.errstate(invalid='ignore', divide='ignore'):
        if isinstance(a, np.ndarray):
            if out is None:
                return np.divide(a, b, out=a, casting='unsafe')
            else:
                return np.divide(a, b, out=out, casting='unsafe')
        elif out is None:
            # Precaution against reduced object arrays
            try:
                return a.dtype.type(a / b)
            except AttributeError:
                return a / b
        else:
            # This is questionable, but currently a numpy scalar can
            # be output to a zero dimensional array.
            return np.divide(a, b, out=out, casting='unsafe')


def _nanmin_dispatcher(a, axis=None, out=None, keepdims=None,
                       initial=None, where=None):
    return (a, out)


@array_function_dispatch(_nanmin_dispatcher)
def nanmin(a, axis=None, out=None, keepdims=np._NoValue, initial=np._NoValue,
           where=np._NoValue):
    """
    Return minimum of an array or minimum along an axis, ignoring any NaNs.
    When all-NaN slices are encountered a ``RuntimeWarning`` is raised and
    Nan is returned for that slice.

    Parameters
    ----------
    a : array_like
        Array containing numbers whose minimum is desired. If `a` is not an
        array, a conversion is attempted.
    axis : {int, tuple of int, None}, optional
        Axis or axes along which the minimum is computed. The default is to compute
        the minimum of the flattened array.
    out : ndarray, optional
        Alternate output array in which to place the result.  The default
        is ``None``; if provided, it must have the same shape as the
        expected output, but the type will be cast if necessary. See
        :ref:`ufuncs-output-type` for more details.
    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the original `a`.

        If the value is anything but the default, then
        `keepdims` will be passed through to the `min` method
        of sub-classes of `ndarray`.  If the sub-classes methods
        does not implement `keepdims` any exceptions will be raised.
    initial : scalar, optional
        The maximum value of an output element. Must be present to allow
        computation on empty slice. See `~numpy.ufunc.reduce` for details.

        .. versionadded:: 1.22.0
    where : array_like of bool, optional
        Elements to compare for the minimum. See `~numpy.ufunc.reduce`
        for details.

        .. versionadded:: 1.22.0

    Returns
    -------
    nanmin : ndarray
        An array with the same shape as `a`, with the specified axis
        removed.  If `a` is a 0-d array, or if axis is None, an ndarray
        scalar is returned.  The same dtype as `a` is returned.

    See Also
    --------
    nanmax :
        The maximum value of an array along a given axis, ignoring any NaNs.
    amin :
        The minimum value of an array along a given axis, propagating any NaNs.
    fmin :
        Element-wise minimum of two arrays, ignoring any NaNs.
    minimum :
        Element-wise minimum of two arrays, propagating any NaNs.
    isnan :
        Shows which elements are Not a Number (NaN).
    isfinite:
        Shows which elements are neither NaN nor infinity.

    amax, fmax, maximum

    Notes
    -----
    NumPy uses the IEEE Standard for Binary Floating-Point for Arithmetic
    (IEEE 754). This means that Not a Number is not equivalent to infinity.
    Positive infinity is treated as a very large number and negative
    infinity is treated as a very small (i.e. negative) number.

    If the input has a integer type the function is equivalent to np.min.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[1, 2], [3, np.nan]])
    >>> np.nanmin(a)
    1.0
    >>> np.nanmin(a, axis=0)
    array([1.,  2.])
    >>> np.nanmin(a, axis=1)
    array([1.,  3.])

    When positive infinity and negative infinity are present:

    >>> np.nanmin([1, 2, np.nan, np.inf])
    1.0
    >>> np.nanmin([1, 2, np.nan, -np.inf])
    -inf

    """
    kwargs = {}
    if keepdims is not np._NoValue:
        kwargs['keepdims'] = keepdims
    if initial is not np._NoValue:
        kwargs['initial'] = initial
    if where is not np._NoValue:
        kwargs['where'] = where

    if (type(a) is np.ndarray or type(a) is np.memmap) and a.dtype != np.object_:
        # Fast, but not safe for subclasses of ndarray, or object arrays,
        # which do not implement isnan (gh-9009), or fmin correctly (gh-8975)
        res = np.fmin.reduce(a, axis=axis, out=out, **kwargs)
        if np.isnan(res).any():
            warnings.warn("All-NaN slice encountered", RuntimeWarning,
                          stacklevel=2)
    else:
        # Slow, but safe for subclasses of ndarray
        a, mask = _replace_nan(a, +np.inf)
        res = np.amin(a, axis=axis, out=out, **kwargs)
        if mask is None:
            return res

        # Check for all-NaN axis
        kwargs.pop("initial", None)
        mask = np.all(mask, axis=axis, **kwargs)
        if np.any(mask):
            res = _copyto(res, np.nan, mask)
            warnings.warn("All-NaN axis encountered", RuntimeWarning,
                          stacklevel=2)
    return res


def _nanmax_dispatcher(a, axis=None, out=None, keepdims=None,
                       initial=None, where=None):
    return (a, out)


@array_function_dispatch(_nanmax_dispatcher)
def nanmax(a, axis=None, out=None, keepdims=np._NoValue, initial=np._NoValue,
           where=np._NoValue):
    """
    Return the maximum of an array or maximum along an axis, ignoring any
    NaNs.  When all-NaN slices are encountered a ``RuntimeWarning`` is
    raised and NaN is returned for that slice.

    Parameters
    ----------
    a : array_like
        Array containing numbers whose maximum is desired. If `a` is not an
        array, a conversion is attempted.
    axis : {int, tuple of int, None}, optional
        Axis or axes along which the maximum is computed. The default is to compute
        the maximum of the flattened array.
    out : ndarray, optional
        Alternate output array in which to place the result.  The default
        is ``None``; if provided, it must have the same shape as the
        expected output, but the type will be cast if necessary. See
        :ref:`ufuncs-output-type` for more details.
    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the original `a`.
        If the value is anything but the default, then
        `keepdims` will be passed through to the `max` method
        of sub-classes of `ndarray`.  If the sub-classes methods
        does not implement `keepdims` any exceptions will be raised.
    initial : scalar, optional
        The minimum value of an output element. Must be present to allow
        computation on empty slice. See `~numpy.ufunc.reduce` for details.

        .. versionadded:: 1.22.0
    where : array_like of bool, optional
        Elements to compare for the maximum. See `~numpy.ufunc.reduce`
        for details.

        .. versionadded:: 1.22.0

    Returns
    -------
    nanmax : ndarray
        An array with the same shape as `a`, with the specified axis removed.
        If `a` is a 0-d array, or if axis is None, an ndarray scalar is
        returned.  The same dtype as `a` is returned.

    See Also
    --------
    nanmin :
        The minimum value of an array along a given axis, ignoring any NaNs.
    amax :
        The maximum value of an array along a given axis, propagating any NaNs.
    fmax :
        Element-wise maximum of two arrays, ignoring any NaNs.
    maximum :
        Element-wise maximum of two arrays, propagating any NaNs.
    isnan :
        Shows which elements are Not a Number (NaN).
    isfinite:
        Shows which elements are neither NaN nor infinity.

    amin, fmin, minimum

    Notes
    -----
    NumPy uses the IEEE Standard for Binary Floating-Point for Arithmetic
    (IEEE 754). This means that Not a Number is not equivalent to infinity.
    Positive infinity is treated as a very large number and negative
    infinity is treated as a very small (i.e. negative) number.

    If the input has a integer type the function is equivalent to np.max.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[1, 2], [3, np.nan]])
    >>> np.nanmax(a)
    3.0
    >>> np.nanmax(a, axis=0)
    array([3.,  2.])
    >>> np.nanmax(a, axis=1)
    array([2.,  3.])

    When positive infinity and negative infinity are present:

    >>> np.nanmax([1, 2, np.nan, -np.inf])
    2.0
    >>> np.nanmax([1, 2, np.nan, np.inf])
    inf

    """
    kwargs = {}
    if keepdims is not np._NoValue:
        kwargs['keepdims'] = keepdims
    if initial is not np._NoValue:
        kwargs['initial'] = initial
    if where is not np._NoValue:
        kwargs['where'] = where

    if (type(a) is np.ndarray or type(a) is np.memmap) and a.dtype != np.object_:
        # Fast, but not safe for subclasses of ndarray, or object arrays,
        # which do not implement isnan (gh-9009), or fmax correctly (gh-8975)
        res = np.fmax.reduce(a, axis=axis, out=out, **kwargs)
        if np.isnan(res).any():
            warnings.warn("All-NaN slice encountered", RuntimeWarning,
                          stacklevel=2)
    else:
        # Slow, but safe for subclasses of ndarray
        a, mask = _replace_nan(a, -np.inf)
        res = np.amax(a, axis=axis, out=out, **kwargs)
        if mask is None:
            return res

        # Check for all-NaN axis
        kwargs.pop("initial", None)
        mask = np.all(mask, axis=axis, **kwargs)
        if np.any(mask):
            res = _copyto(res, np.nan, mask)
            warnings.warn("All-NaN axis encountered", RuntimeWarning,
                          stacklevel=2)
    return res


def _nanargmin_dispatcher(a, axis=None, out=None, *, keepdims=None):
    return (a,)


@array_function_dispatch(_nanargmin_dispatcher)
def nanargmin(a, axis=None, out=None, *, keepdims=np._NoValue):
    """
    Return the indices of the minimum values in the specified axis ignoring
    NaNs. For all-NaN slices ``ValueError`` is raised. Warning: the results
    cannot be trusted if a slice contains only NaNs and Infs.

    Parameters
    ----------
    a : array_like
        Input data.
    axis : int, optional
        Axis along which to operate.  By default flattened input is used.
    out : array, optional
        If provided, the result will be inserted into this array. It should
        be of the appropriate shape and dtype.

        .. versionadded:: 1.22.0
    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the array.

        .. versionadded:: 1.22.0

    Returns
    -------
    index_array : ndarray
        An array of indices or a single index value.

    See Also
    --------
    argmin, nanargmax

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[np.nan, 4], [2, 3]])
    >>> np.argmin(a)
    0
    >>> np.nanargmin(a)
    2
    >>> np.nanargmin(a, axis=0)
    array([1, 1])
    >>> np.nanargmin(a, axis=1)
    array([1, 0])

    """
    a, mask = _replace_nan(a, np.inf)
    if mask is not None and mask.size:
        mask = np.all(mask, axis=axis)
        if np.any(mask):
            raise ValueError("All-NaN slice encountered")
    res = np.argmin(a, axis=axis, out=out, keepdims=keepdims)
    return res


def _nanargmax_dispatcher(a, axis=None, out=None, *, keepdims=None):
    return (a,)


@array_function_dispatch(_nanargmax_dispatcher)
def nanargmax(a, axis=None, out=None, *, keepdims=np._NoValue):
    """
    Return the indices of the maximum values in the specified axis ignoring
    NaNs. For all-NaN slices ``ValueError`` is raised. Warning: the
    results cannot be trusted if a slice contains only NaNs and -Infs.


    Parameters
    ----------
    a : array_like
        Input data.
    axis : int, optional
        Axis along which to operate.  By default flattened input is used.
    out : array, optional
        If provided, the result will be inserted into this array. It should
        be of the appropriate shape and dtype.

        .. versionadded:: 1.22.0
    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the array.

        .. versionadded:: 1.22.0

    Returns
    -------
    index_array : ndarray
        An array of indices or a single index value.

    See Also
    --------
    argmax, nanargmin

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[np.nan, 4], [2, 3]])
    >>> np.argmax(a)
    0
    >>> np.nanargmax(a)
    1
    >>> np.nanargmax(a, axis=0)
    array([1, 0])
    >>> np.nanargmax(a, axis=1)
    array([1, 1])

    """
    a, mask = _replace_nan(a, -np.inf)
    if mask is not None and mask.size:
        mask = np.all(mask, axis=axis)
        if np.any(mask):
            raise ValueError("All-NaN slice encountered")
    res = np.argmax(a, axis=axis, out=out, keepdims=keepdims)
    return res


def _nansum_dispatcher(a, axis=None, dtype=None, out=None, keepdims=None,
                       initial=None, where=None):
    return (a, out)


@array_function_dispatch(_nansum_dispatcher)
def nansum(a, axis=None, dtype=None, out=None, keepdims=np._NoValue,
           initial=np._NoValue, where=np._NoValue):
    """
    Return the sum of array elements over a given axis treating Not a
    Numbers (NaNs) as zero.

    In NumPy versions <= 1.9.0 Nan is returned for slices that are all-NaN or
    empty. In later versions zero is returned.

    Parameters
    ----------
    a : array_like
        Array containing numbers whose sum is desired. If `a` is not an
        array, a conversion is attempted.
    axis : {int, tuple of int, None}, optional
        Axis or axes along which the sum is computed. The default is to compute the
        sum of the flattened array.
    dtype : data-type, optional
        The type of the returned array and of the accumulator in which the
        elements are summed.  By default, the dtype of `a` is used.  An
        exception is when `a` has an integer type with less precision than
        the platform (u)intp. In that case, the default will be either
        (u)int32 or (u)int64 depending on whether the platform is 32 or 64
        bits. For inexact inputs, dtype must be inexact.
    out : ndarray, optional
        Alternate output array in which to place the result.  The default
        is ``None``. If provided, it must have the same shape as the
        expected output, but the type will be cast if necessary.  See
        :ref:`ufuncs-output-type` for more details. The casting of NaN to integer
        can yield unexpected results.
    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the original `a`.

        If the value is anything but the default, then
        `keepdims` will be passed through to the `mean` or `sum` methods
        of sub-classes of `ndarray`.  If the sub-classes methods
        does not implement `keepdims` any exceptions will be raised.
    initial : scalar, optional
        Starting value for the sum. See `~numpy.ufunc.reduce` for details.

        .. versionadded:: 1.22.0
    where : array_like of bool, optional
        Elements to include in the sum. See `~numpy.ufunc.reduce` for details.

        .. versionadded:: 1.22.0

    Returns
    -------
    nansum : ndarray.
        A new array holding the result is returned unless `out` is
        specified, in which it is returned. The result has the same
        size as `a`, and the same shape as `a` if `axis` is not None
        or `a` is a 1-d array.

    See Also
    --------
    numpy.sum : Sum across array propagating NaNs.
    isnan : Show which elements are NaN.
    isfinite : Show which elements are not NaN or +/-inf.

    Notes
    -----
    If both positive and negative infinity are present, the sum will be Not
    A Number (NaN).

    Examples
    --------
    >>> import numpy as np
    >>> np.nansum(1)
    1
    >>> np.nansum([1])
    1
    >>> np.nansum([1, np.nan])
    1.0
    >>> a = np.array([[1, 1], [1, np.nan]])
    >>> np.nansum(a)
    3.0
    >>> np.nansum(a, axis=0)
    array([2.,  1.])
    >>> np.nansum([1, np.nan, np.inf])
    inf
    >>> np.nansum([1, np.nan, -np.inf])
    -inf
    >>> from numpy.testing import suppress_warnings
    >>> with np.errstate(invalid="ignore"):
    ...     np.nansum([1, np.nan, np.inf, -np.inf]) # both +/- infinity present
    np.float64(nan)

    """
    a, mask = _replace_nan(a, 0)
    return np.sum(a, axis=axis, dtype=dtype, out=out, keepdims=keepdims,
                  initial=initial, where=where)


def _nanprod_dispatcher(a, axis=None, dtype=None, out=None, keepdims=None,
                        initial=None, where=None):
    return (a, out)


@array_function_dispatch(_nanprod_dispatcher)
def nanprod(a, axis=None, dtype=None, out=None, keepdims=np._NoValue,
            initial=np._NoValue, where=np._NoValue):
    """
    Return the product of array elements over a given axis treating Not a
    Numbers (NaNs) as ones.

    One is returned for slices that are all-NaN or empty.

    Parameters
    ----------
    a : array_like
        Array containing numbers whose product is desired. If `a` is not an
        array, a conversion is attempted.
    axis : {int, tuple of int, None}, optional
        Axis or axes along which the product is computed. The default is to compute
        the product of the flattened array.
    dtype : data-type, optional
        The type of the returned array and of the accumulator in which the
        elements are summed.  By default, the dtype of `a` is used.  An
        exception is when `a` has an integer type with less precision than
        the platform (u)intp. In that case, the default will be either
        (u)int32 or (u)int64 depending on whether the platform is 32 or 64
        bits. For inexact inputs, dtype must be inexact.
    out : ndarray, optional
        Alternate output array in which to place the result.  The default
        is ``None``. If provided, it must have the same shape as the
        expected output, but the type will be cast if necessary. See
        :ref:`ufuncs-output-type` for more details. The casting of NaN to integer
        can yield unexpected results.
    keepdims : bool, optional
        If True, the axes which are reduced are left in the result as
        dimensions with size one. With this option, the result will
        broadcast correctly against the original `arr`.
    initial : scalar, optional
        The starting value for this product. See `~numpy.ufunc.reduce`
        for details.

        .. versionadded:: 1.22.0
    where : array_like of bool, optional
        Elements to include in the product. See `~numpy.ufunc.reduce`
        for details.

        .. versionadded:: 1.22.0

    Returns
    -------
    nanprod : ndarray
        A new array holding the result is returned unless `out` is
        specified, in which case it is returned.

    See Also
    --------
    numpy.prod : Product across array propagating NaNs.
    isnan : Show which elements are NaN.

    Examples
    --------
    >>> import numpy as np
    >>> np.nanprod(1)
    1
    >>> np.nanprod([1])
    1
    >>> np.nanprod([1, np.nan])
    1.0
    >>> a = np.array([[1, 2], [3, np.nan]])
    >>> np.nanprod(a)
    6.0
    >>> np.nanprod(a, axis=0)
    array([3., 2.])

    """
    a, mask = _replace_nan(a, 1)
    return np.prod(a, axis=axis, dtype=dtype, out=out, keepdims=keepdims,
                   initial=initial, where=where)


def _nancumsum_dispatcher(a, axis=None, dtype=None, out=None):
    return (a, out)


@array_function_dispatch(_nancumsum_dispatcher)
def nancumsum(a, axis=None, dtype=None, out=None):
    """
    Return the cumulative sum of array elements over a given axis treating Not a
    Numbers (NaNs) as zero.  The cumulative sum does not change when NaNs are
    encountered and leading NaNs are replaced by zeros.

    Zeros are returned for slices that are all-NaN or empty.

    Parameters
    ----------
    a : array_like
        Input array.
    axis : int, optional
        Axis along which the cumulative sum is computed. The default
        (None) is to compute the cumsum over the flattened array.
    dtype : dtype, optional
        Type of the returned array and of the accumulator in which the
        elements are summed.  If `dtype` is not specified, it defaults
        to the dtype of `a`, unless `a` has an integer dtype with a
        precision less than that of the default platform integer.  In
        that case, the default platform integer is used.
    out : ndarray, optional
        Alternative output array in which to place the result. It must
        have the same shape and buffer length as the expected output
        but the type will be cast if necessary. See :ref:`ufuncs-output-type` for
        more details.

    Returns
    -------
    nancumsum : ndarray.
        A new array holding the result is returned unless `out` is
        specified, in which it is returned. The result has the same
        size as `a`, and the same shape as `a` if `axis` is not None
        or `a` is a 1-d array.

    See Also
    --------
    numpy.cumsum : Cumulative sum across array propagating NaNs.
    isnan : Show which elements are NaN.

    Examples
    --------
    >>> import numpy as np
    >>> np.nancumsum(1)
    array([1])
    >>> np.nancumsum([1])
    array([1])
    >>> np.nancumsum([1, np.nan])
    array([1.,  1.])
    >>> a = np.array([[1, 2], [3, np.nan]])
    >>> np.nancumsum(a)
    array([1.,  3.,  6.,  6.])
    >>> np.nancumsum(a, axis=0)
    array([[1.,  2.],
           [4.,  2.]])
    >>> np.nancumsum(a, axis=1)
    array([[1.,  3.],
           [3.,  3.]])

    """
    a, mask = _replace_nan(a, 0)
    return np.cumsum(a, axis=axis, dtype=dtype, out=out)


def _nancumprod_dispatcher(a, axis=None, dtype=None, out=None):
    return (a, out)


@array_function_dispatch(_nancumprod_dispatcher)
def nancumprod(a, axis=None, dtype=None, out=None):
    """
    Return the cumulative product of array elements over a given axis treating Not a
    Numbers (NaNs) as one.  The cumulative product does not change when NaNs are
    encountered and leading NaNs are replaced by ones.

    Ones are returned for slices that are all-NaN or empty.

    Parameters
    ----------
    a : array_like
        Input array.
    axis : int, optional
        Axis along which the cumulative product is computed.  By default
        the input is flattened.
    dtype : dtype, optional
        Type of the returned array, as well as of the accumulator in which
        the elements are multiplied.  If *dtype* is not specified, it
        defaults to the dtype of `a`, unless `a` has an integer dtype with
        a precision less than that of the default platform integer.  In
        that case, the default platform integer is used instead.
    out : ndarray, optional
        Alternative output array in which to place the result. It must
        have the same shape and buffer length as the expected output
        but the type of the resulting values will be cast if necessary.

    Returns
    -------
    nancumprod : ndarray
        A new array holding the result is returned unless `out` is
        specified, in which case it is returned.

    See Also
    --------
    numpy.cumprod : Cumulative product across array propagating NaNs.
    isnan : Show which elements are NaN.

    Examples
    --------
    >>> import numpy as np
    >>> np.nancumprod(1)
    array([1])
    >>> np.nancumprod([1])
    array([1])
    >>> np.nancumprod([1, np.nan])
    array([1.,  1.])
    >>> a = np.array([[1, 2], [3, np.nan]])
    >>> np.nancumprod(a)
    array([1.,  2.,  6.,  6.])
    >>> np.nancumprod(a, axis=0)
    array([[1.,  2.],
           [3.,  2.]])
    >>> np.nancumprod(a, axis=1)
    array([[1.,  2.],
           [3.,  3.]])

    """
    a, mask = _replace_nan(a, 1)
    return np.cumprod(a, axis=axis, dtype=dtype, out=out)


def _nanmean_dispatcher(a, axis=None, dtype=None, out=None, keepdims=None,
                        *, where=None):
    return (a, out)


@array_function_dispatch(_nanmean_dispatcher)
def nanmean(a, axis=None, dtype=None, out=None, keepdims=np._NoValue,
            *, where=np._NoValue):
    """
    Compute the arithmetic mean along the specified axis, ignoring NaNs.

    Returns the average of the array elements.  The average is taken over
    the flattened array by default, otherwise over the specified axis.
    `float64` intermediate and return values are used for integer inputs.

    For all-NaN slices, NaN is returned and a `RuntimeWarning` is raised.

    Parameters
    ----------
    a : array_like
        Array containing numbers whose mean is desired. If `a` is not an
        array, a conversion is attempted.
    axis : {int, tuple of int, None}, optional
        Axis or axes along which the means are computed. The default is to compute
        the mean of the flattened array.
    dtype : data-type, optional
        Type to use in computing the mean.  For integer inputs, the default
        is `float64`; for inexact inputs, it is the same as the input
        dtype.
    out : ndarray, optional
        Alternate output array in which to place the result.  The default
        is ``None``; if provided, it must have the same shape as the
        expected output, but the type will be cast if necessary.
        See :ref:`ufuncs-output-type` for more details.
    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the original `a`.

        If the value is anything but the default, then
        `keepdims` will be passed through to the `mean` or `sum` methods
        of sub-classes of `ndarray`.  If the sub-classes methods
        does not implement `keepdims` any exceptions will be raised.
    where : array_like of bool, optional
        Elements to include in the mean. See `~numpy.ufunc.reduce` for details.

        .. versionadded:: 1.22.0

    Returns
    -------
    m : ndarray, see dtype parameter above
        If `out=None`, returns a new array containing the mean values,
        otherwise a reference to the output array is returned. Nan is
        returned for slices that contain only NaNs.

    See Also
    --------
    average : Weighted average
    mean : Arithmetic mean taken while not ignoring NaNs
    var, nanvar

    Notes
    -----
    The arithmetic mean is the sum of the non-NaN elements along the axis
    divided by the number of non-NaN elements.

    Note that for floating-point input, the mean is computed using the same
    precision the input has.  Depending on the input data, this can cause
    the results to be inaccurate, especially for `float32`.  Specifying a
    higher-precision accumulator using the `dtype` keyword can alleviate
    this issue.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[1, np.nan], [3, 4]])
    >>> np.nanmean(a)
    2.6666666666666665
    >>> np.nanmean(a, axis=0)
    array([2.,  4.])
    >>> np.nanmean(a, axis=1)
    array([1.,  3.5]) # may vary

    """
    arr, mask = _replace_nan(a, 0)
    if mask is None:
        return np.mean(arr, axis=axis, dtype=dtype, out=out, keepdims=keepdims,
                       where=where)

    if dtype is not None:
        dtype = np.dtype(dtype)
    if dtype is not None and not issubclass(dtype.type, np.inexact):
        raise TypeError("If a is inexact, then dtype must be inexact")
    if out is not None and not issubclass(out.dtype.type, np.inexact):
        raise TypeError("If a is inexact, then out must be inexact")

    cnt = np.sum(~mask, axis=axis, dtype=np.intp, keepdims=keepdims,
                 where=where)
    tot = np.sum(arr, axis=axis, dtype=dtype, out=out, keepdims=keepdims,
                 where=where)
    avg = _divide_by_count(tot, cnt, out=out)

    isbad = (cnt == 0)
    if isbad.any():
        warnings.warn("Mean of empty slice", RuntimeWarning, stacklevel=2)
        # NaN is the only possible bad value, so no further
        # action is needed to handle bad results.
    return avg


def _nanmedian1d(arr1d, overwrite_input=False):
    """
    Private function for rank 1 arrays. Compute the median ignoring NaNs.
    See nanmedian for parameter usage
    """
    arr1d_parsed, _, overwrite_input = _remove_nan_1d(
        arr1d, overwrite_input=overwrite_input,
    )

    if arr1d_parsed.size == 0:
        # Ensure that a nan-esque scalar of the appropriate type (and unit)
        # is returned for `timedelta64` and `complexfloating`
        return arr1d[-1]

    return np.median(arr1d_parsed, overwrite_input=overwrite_input)


def _nanmedian(a, axis=None, out=None, overwrite_input=False):
    """
    Private function that doesn't support extended axis or keepdims.
    These methods are extended to this function using _ureduce
    See nanmedian for parameter usage

    """
    if axis is None or a.ndim == 1:
        part = a.ravel()
        if out is None:
            return _nanmedian1d(part, overwrite_input)
        else:
            out[...] = _nanmedian1d(part, overwrite_input)
            return out
    else:
        # for small medians use sort + indexing which is still faster than
        # apply_along_axis
        # benchmarked with shuffled (50, 50, x) containing a few NaN
        if a.shape[axis] < 600:
            return _nanmedian_small(a, axis, out, overwrite_input)
        result = np.apply_along_axis(_nanmedian1d, axis, a, overwrite_input)
        if out is not None:
            out[...] = result
        return result


def _nanmedian_small(a, axis=None, out=None, overwrite_input=False):
    """
    sort + indexing median, faster for small medians along multiple
    dimensions due to the high overhead of apply_along_axis

    see nanmedian for parameter usage
    """
    a = np.ma.masked_array(a, np.isnan(a))
    m = np.ma.median(a, axis=axis, overwrite_input=overwrite_input)
    for i in range(np.count_nonzero(m.mask.ravel())):
        warnings.warn("All-NaN slice encountered", RuntimeWarning,
                      stacklevel=5)

    fill_value = np.timedelta64("NaT") if m.dtype.kind == "m" else np.nan
    if out is not None:
        out[...] = m.filled(fill_value)
        return out
    return m.filled(fill_value)


def _nanmedian_dispatcher(
        a, axis=None, out=None, overwrite_input=None, keepdims=None):
    return (a, out)


@array_function_dispatch(_nanmedian_dispatcher)
def nanmedian(a, axis=None, out=None, overwrite_input=False, keepdims=np._NoValue):
    """
    Compute the median along the specified axis, while ignoring NaNs.

    Returns the median of the array elements.

    Parameters
    ----------
    a : array_like
        Input array or object that can be converted to an array.
    axis : {int, sequence of int, None}, optional
        Axis or axes along which the medians are computed. The default
        is to compute the median along a flattened version of the array.
        A sequence of axes is supported since version 1.9.0.
    out : ndarray, optional
        Alternative output array in which to place the result. It must
        have the same shape and buffer length as the expected output,
        but the type (of the output) will be cast if necessary.
    overwrite_input : bool, optional
       If True, then allow use of memory of input array `a` for
       calculations. The input array will be modified by the call to
       `median`. This will save memory when you do not need to preserve
       the contents of the input array. Treat the input as undefined,
       but it will probably be fully or partially sorted. Default is
       False. If `overwrite_input` is ``True`` and `a` is not already an
       `ndarray`, an error will be raised.
    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the original `a`.

        If this is anything but the default value it will be passed
        through (in the special case of an empty array) to the
        `mean` function of the underlying array.  If the array is
        a sub-class and `mean` does not have the kwarg `keepdims` this
        will raise a RuntimeError.

    Returns
    -------
    median : ndarray
        A new array holding the result. If the input contains integers
        or floats smaller than ``float64``, then the output data-type is
        ``np.float64``.  Otherwise, the data-type of the output is the
        same as that of the input. If `out` is specified, that array is
        returned instead.

    See Also
    --------
    mean, median, percentile

    Notes
    -----
    Given a vector ``V`` of length ``N``, the median of ``V`` is the
    middle value of a sorted copy of ``V``, ``V_sorted`` - i.e.,
    ``V_sorted[(N-1)/2]``, when ``N`` is odd and the average of the two
    middle values of ``V_sorted`` when ``N`` is even.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[10.0, 7, 4], [3, 2, 1]])
    >>> a[0, 1] = np.nan
    >>> a
    array([[10., nan,  4.],
           [ 3.,  2.,  1.]])
    >>> np.median(a)
    np.float64(nan)
    >>> np.nanmedian(a)
    3.0
    >>> np.nanmedian(a, axis=0)
    array([6.5, 2. , 2.5])
    >>> np.median(a, axis=1)
    array([nan,  2.])
    >>> b = a.copy()
    >>> np.nanmedian(b, axis=1, overwrite_input=True)
    array([7.,  2.])
    >>> assert not np.all(a==b)
    >>> b = a.copy()
    >>> np.nanmedian(b, axis=None, overwrite_input=True)
    3.0
    >>> assert not np.all(a==b)

    """
    a = np.asanyarray(a)
    # apply_along_axis in _nanmedian doesn't handle empty arrays well,
    # so deal them upfront
    if a.size == 0:
        return np.nanmean(a, axis, out=out, keepdims=keepdims)

    return fnb._ureduce(a, func=_nanmedian, keepdims=keepdims,
                        axis=axis, out=out,
                        overwrite_input=overwrite_input)


def _nanpercentile_dispatcher(
        a, q, axis=None, out=None, overwrite_input=None,
        method=None, keepdims=None, *, weights=None, interpolation=None):
    return (a, q, out, weights)


@array_function_dispatch(_nanpercentile_dispatcher)
def nanpercentile(
        a,
        q,
        axis=None,
        out=None,
        overwrite_input=False,
        method="linear",
        keepdims=np._NoValue,
        *,
        weights=None,
        interpolation=None,
):
    """
    Compute the qth percentile of the data along the specified axis,
    while ignoring nan values.

    Returns the qth percentile(s) of the array elements.

    Parameters
    ----------
    a : array_like
        Input array or object that can be converted to an array, containing
        nan values to be ignored.
    q : array_like of float
        Percentile or sequence of percentiles to compute, which must be
        between 0 and 100 inclusive.
    axis : {int, tuple of int, None}, optional
        Axis or axes along which the percentiles are computed. The default
        is to compute the percentile(s) along a flattened version of the
        array.
    out : ndarray, optional
        Alternative output array in which to place the result. It must have
        the same shape and buffer length as the expected output, but the
        type (of the output) will be cast if necessary.
    overwrite_input : bool, optional
        If True, then allow the input array `a` to be modified by
        intermediate calculations, to save memory. In this case, the
        contents of the input `a` after this function completes is
        undefined.
    method : str, optional
        This parameter specifies the method to use for estimating the
        percentile.  There are many different methods, some unique to NumPy.
        See the notes for explanation.  The options sorted by their R type
        as summarized in the H&F paper [1]_ are:

        1. 'inverted_cdf'
        2. 'averaged_inverted_cdf'
        3. 'closest_observation'
        4. 'interpolated_inverted_cdf'
        5. 'hazen'
        6. 'weibull'
        7. 'linear'  (default)
        8. 'median_unbiased'
        9. 'normal_unbiased'

        The first three methods are discontinuous.  NumPy further defines the
        following discontinuous variations of the default 'linear' (7.) option:

        * 'lower'
        * 'higher',
        * 'midpoint'
        * 'nearest'

        .. versionchanged:: 1.22.0
            This argument was previously called "interpolation" and only
            offered the "linear" default and last four options.

    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left in
        the result as dimensions with size one. With this option, the
        result will broadcast correctly against the original array `a`.

        If this is anything but the default value it will be passed
        through (in the special case of an empty array) to the
        `mean` function of the underlying array.  If the array is
        a sub-class and `mean` does not have the kwarg `keepdims` this
        will raise a RuntimeError.

    weights : array_like, optional
        An array of weights associated with the values in `a`. Each value in
        `a` contributes to the percentile according to its associated weight.
        The weights array can either be 1-D (in which case its length must be
        the size of `a` along the given axis) or of the same shape as `a`.
        If `weights=None`, then all data in `a` are assumed to have a
        weight equal to one.
        Only `method="inverted_cdf"` supports weights.

        .. versionadded:: 2.0.0

    interpolation : str, optional
        Deprecated name for the method keyword argument.

        .. deprecated:: 1.22.0

    Returns
    -------
    percentile : scalar or ndarray
        If `q` is a single percentile and `axis=None`, then the result
        is a scalar. If multiple percentiles are given, first axis of
        the result corresponds to the percentiles. The other axes are
        the axes that remain after the reduction of `a`. If the input
        contains integers or floats smaller than ``float64``, the output
        data-type is ``float64``. Otherwise, the output data-type is the
        same as that of the input. If `out` is specified, that array is
        returned instead.

    See Also
    --------
    nanmean
    nanmedian : equivalent to ``nanpercentile(..., 50)``
    percentile, median, mean
    nanquantile : equivalent to nanpercentile, except q in range [0, 1].

    Notes
    -----
    The behavior of `numpy.nanpercentile` with percentage `q` is that of
    `numpy.quantile` with argument ``q/100`` (ignoring nan values).
    For more information, please see `numpy.quantile`.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[10., 7., 4.], [3., 2., 1.]])
    >>> a[0][1] = np.nan
    >>> a
    array([[10.,  nan,   4.],
          [ 3.,   2.,   1.]])
    >>> np.percentile(a, 50)
    np.float64(nan)
    >>> np.nanpercentile(a, 50)
    3.0
    >>> np.nanpercentile(a, 50, axis=0)
    array([6.5, 2. , 2.5])
    >>> np.nanpercentile(a, 50, axis=1, keepdims=True)
    array([[7.],
           [2.]])
    >>> m = np.nanpercentile(a, 50, axis=0)
    >>> out = np.zeros_like(m)
    >>> np.nanpercentile(a, 50, axis=0, out=out)
    array([6.5, 2. , 2.5])
    >>> m
    array([6.5,  2. ,  2.5])

    >>> b = a.copy()
    >>> np.nanpercentile(b, 50, axis=1, overwrite_input=True)
    array([7., 2.])
    >>> assert not np.all(a==b)

    References
    ----------
    .. [1] R. J. Hyndman and Y. Fan,
       "Sample quantiles in statistical packages,"
       The American Statistician, 50(4), pp. 361-365, 1996

    """
    if interpolation is not None:
        method = fnb._check_interpolation_as_method(
            method, interpolation, "nanpercentile")

    a = np.asanyarray(a)
    if a.dtype.kind == "c":
        raise TypeError("a must be an array of real numbers")

    q = np.true_divide(q, a.dtype.type(100) if a.dtype.kind == "f" else 100, out=...)
    if not fnb._quantile_is_valid(q):
        raise ValueError("Percentiles must be in the range [0, 100]")

    if weights is not None:
        if method != "inverted_cdf":
            msg = ("Only method 'inverted_cdf' supports weights. "
                   f"Got: {method}.")
            raise ValueError(msg)
        if axis is not None:
            axis = _nx.normalize_axis_tuple(axis, a.ndim, argname="axis")
        weights = _weights_are_valid(weights=weights, a=a, axis=axis)
        if np.any(weights < 0):
            raise ValueError("Weights must be non-negative.")

    return _nanquantile_unchecked(
        a, q, axis, out, overwrite_input, method, keepdims, weights)


def _nanquantile_dispatcher(a, q, axis=None, out=None, overwrite_input=None,
                            method=None, keepdims=None, *, weights=None,
                            interpolation=None):
    return (a, q, out, weights)


@array_function_dispatch(_nanquantile_dispatcher)
def nanquantile(
        a,
        q,
        axis=None,
        out=None,
        overwrite_input=False,
        method="linear",
        keepdims=np._NoValue,
        *,
        weights=None,
        interpolation=None,
):
    """
    Compute the qth quantile of the data along the specified axis,
    while ignoring nan values.
    Returns the qth quantile(s) of the array elements.

    Parameters
    ----------
    a : array_like
        Input array or object that can be converted to an array, containing
        nan values to be ignored
    q : array_like of float
        Probability or sequence of probabilities for the quantiles to compute.
        Values must be between 0 and 1 inclusive.
    axis : {int, tuple of int, None}, optional
        Axis or axes along which the quantiles are computed. The
        default is to compute the quantile(s) along a flattened
        version of the array.
    out : ndarray, optional
        Alternative output array in which to place the result. It must
        have the same shape and buffer length as the expected output,
        but the type (of the output) will be cast if necessary.
    overwrite_input : bool, optional
        If True, then allow the input array `a` to be modified by intermediate
        calculations, to save memory. In this case, the contents of the input
        `a` after this function completes is undefined.
    method : str, optional
        This parameter specifies the method to use for estimating the
        quantile.  There are many different methods, some unique to NumPy.
        See the notes for explanation.  The options sorted by their R type
        as summarized in the H&F paper [1]_ are:

        1. 'inverted_cdf'
        2. 'averaged_inverted_cdf'
        3. 'closest_observation'
        4. 'interpolated_inverted_cdf'
        5. 'hazen'
        6. 'weibull'
        7. 'linear'  (default)
        8. 'median_unbiased'
        9. 'normal_unbiased'

        The first three methods are discontinuous.  NumPy further defines the
        following discontinuous variations of the default 'linear' (7.) option:

        * 'lower'
        * 'higher',
        * 'midpoint'
        * 'nearest'

        .. versionchanged:: 1.22.0
            This argument was previously called "interpolation" and only
            offered the "linear" default and last four options.

    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left in
        the result as dimensions with size one. With this option, the
        result will broadcast correctly against the original array `a`.

        If this is anything but the default value it will be passed
        through (in the special case of an empty array) to the
        `mean` function of the underlying array.  If the array is
        a sub-class and `mean` does not have the kwarg `keepdims` this
        will raise a RuntimeError.

    weights : array_like, optional
        An array of weights associated with the values in `a`. Each value in
        `a` contributes to the quantile according to its associated weight.
        The weights array can either be 1-D (in which case its length must be
        the size of `a` along the given axis) or of the same shape as `a`.
        If `weights=None`, then all data in `a` are assumed to have a
        weight equal to one.
        Only `method="inverted_cdf"` supports weights.

        .. versionadded:: 2.0.0

    interpolation : str, optional
        Deprecated name for the method keyword argument.

        .. deprecated:: 1.22.0

    Returns
    -------
    quantile : scalar or ndarray
        If `q` is a single probability and `axis=None`, then the result
        is a scalar. If multiple probability levels are given, first axis of
        the result corresponds to the quantiles. The other axes are
        the axes that remain after the reduction of `a`. If the input
        contains integers or floats smaller than ``float64``, the output
        data-type is ``float64``. Otherwise, the output data-type is the
        same as that of the input. If `out` is specified, that array is
        returned instead.

    See Also
    --------
    quantile
    nanmean, nanmedian
    nanmedian : equivalent to ``nanquantile(..., 0.5)``
    nanpercentile : same as nanquantile, but with q in the range [0, 100].

    Notes
    -----
    The behavior of `numpy.nanquantile` is the same as that of
    `numpy.quantile` (ignoring nan values).
    For more information, please see `numpy.quantile`.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[10., 7., 4.], [3., 2., 1.]])
    >>> a[0][1] = np.nan
    >>> a
    array([[10.,  nan,   4.],
          [ 3.,   2.,   1.]])
    >>> np.quantile(a, 0.5)
    np.float64(nan)
    >>> np.nanquantile(a, 0.5)
    3.0
    >>> np.nanquantile(a, 0.5, axis=0)
    array([6.5, 2. , 2.5])
    >>> np.nanquantile(a, 0.5, axis=1, keepdims=True)
    array([[7.],
           [2.]])
    >>> m = np.nanquantile(a, 0.5, axis=0)
    >>> out = np.zeros_like(m)
    >>> np.nanquantile(a, 0.5, axis=0, out=out)
    array([6.5, 2. , 2.5])
    >>> m
    array([6.5,  2. ,  2.5])
    >>> b = a.copy()
    >>> np.nanquantile(b, 0.5, axis=1, overwrite_input=True)
    array([7., 2.])
    >>> assert not np.all(a==b)

    References
    ----------
    .. [1] R. J. Hyndman and Y. Fan,
       "Sample quantiles in statistical packages,"
       The American Statistician, 50(4), pp. 361-365, 1996

    """

    if interpolation is not None:
        method = fnb._check_interpolation_as_method(
            method, interpolation, "nanquantile")

    a = np.asanyarray(a)
    if a.dtype.kind == "c":
        raise TypeError("a must be an array of real numbers")

    # Use dtype of array if possible (e.g., if q is a python int or float).
    if isinstance(q, (int, float)) and a.dtype.kind == "f":
        q = np.asanyarray(q, dtype=a.dtype)
    else:
        q = np.asanyarray(q)

    if not fnb._quantile_is_valid(q):
        raise ValueError("Quantiles must be in the range [0, 1]")

    if weights is not None:
        if method != "inverted_cdf":
            msg = ("Only method 'inverted_cdf' supports weights. "
                   f"Got: {method}.")
            raise ValueError(msg)
        if axis is not None:
            axis = _nx.normalize_axis_tuple(axis, a.ndim, argname="axis")
        weights = _weights_are_valid(weights=weights, a=a, axis=axis)
        if np.any(weights < 0):
            raise ValueError("Weights must be non-negative.")

    return _nanquantile_unchecked(
        a, q, axis, out, overwrite_input, method, keepdims, weights)


def _nanquantile_unchecked(
        a,
        q,
        axis=None,
        out=None,
        overwrite_input=False,
        method="linear",
        keepdims=np._NoValue,
        weights=None,
):
    """Assumes that q is in [0, 1], and is an ndarray"""
    # apply_along_axis in _nanpercentile doesn't handle empty arrays well,
    # so deal them upfront
    if a.size == 0:
        return np.nanmean(a, axis, out=out, keepdims=keepdims)
    return fnb._ureduce(a,
                        func=_nanquantile_ureduce_func,
                        q=q,
                        weights=weights,
                        keepdims=keepdims,
                        axis=axis,
                        out=out,
                        overwrite_input=overwrite_input,
                        method=method)


def _nanquantile_ureduce_func(
        a: np.array,
        q: np.array,
        weights: np.array,
        axis: int | None = None,
        out=None,
        overwrite_input: bool = False,
        method="linear",
):
    """
    Private function that doesn't support extended axis or keepdims.
    These methods are extended to this function using _ureduce
    See nanpercentile for parameter usage
    """
    if axis is None or a.ndim == 1:
        part = a.ravel()
        wgt = None if weights is None else weights.ravel()
        result = _nanquantile_1d(part, q, overwrite_input, method, weights=wgt)
    # Note that this code could try to fill in `out` right away
    elif weights is None:
        result = np.apply_along_axis(_nanquantile_1d, axis, a, q,
                                     overwrite_input, method, weights)
        # apply_along_axis fills in collapsed axis with results.
        # Move those axes to the beginning to match percentile's
        # convention.
        if q.ndim != 0:
            from_ax = [axis + i for i in range(q.ndim)]
            result = np.moveaxis(result, from_ax, list(range(q.ndim)))
    else:
        # We need to apply along axis over 2 arrays, a and weights.
        # move operation axes to end for simplicity:
        a = np.moveaxis(a, axis, -1)
        if weights is not None:
            weights = np.moveaxis(weights, axis, -1)
        if out is not None:
            result = out
        else:
            # weights are limited to `inverted_cdf` so the result dtype
            # is known to be identical to that of `a` here:
            result = np.empty_like(a, shape=q.shape + a.shape[:-1])

        for ii in np.ndindex(a.shape[:-1]):
            result[(...,) + ii] = _nanquantile_1d(
                    a[ii], q, weights=weights[ii],
                    overwrite_input=overwrite_input, method=method,
            )
        # This path dealt with `out` already...
        return result

    if out is not None:
        out[...] = result
    return result


def _nanquantile_1d(
    arr1d, q, overwrite_input=False, method="linear", weights=None,
):
    """
    Private function for rank 1 arrays. Compute quantile ignoring NaNs.
    See nanpercentile for parameter usage
    """
    # TODO: What to do when arr1d = [1, np.nan] and weights = [0, 1]?
    arr1d, weights, overwrite_input = _remove_nan_1d(arr1d,
        second_arr1d=weights, overwrite_input=overwrite_input)
    if arr1d.size == 0:
        # convert to scalar
        return np.full(q.shape, np.nan, dtype=arr1d.dtype)[()]

    return fnb._quantile_unchecked(
        arr1d,
        q,
        overwrite_input=overwrite_input,
        method=method,
        weights=weights,
    )


def _nanvar_dispatcher(a, axis=None, dtype=None, out=None, ddof=None,
                       keepdims=None, *, where=None, mean=None,
                       correction=None):
    return (a, out)


@array_function_dispatch(_nanvar_dispatcher)
def nanvar(a, axis=None, dtype=None, out=None, ddof=0, keepdims=np._NoValue,
           *, where=np._NoValue, mean=np._NoValue, correction=np._NoValue):
    """
    Compute the variance along the specified axis, while ignoring NaNs.

    Returns the variance of the array elements, a measure of the spread of
    a distribution.  The variance is computed for the flattened array by
    default, otherwise over the specified axis.

    For all-NaN slices or slices with zero degrees of freedom, NaN is
    returned and a `RuntimeWarning` is raised.

    Parameters
    ----------
    a : array_like
        Array containing numbers whose variance is desired.  If `a` is not an
        array, a conversion is attempted.
    axis : {int, tuple of int, None}, optional
        Axis or axes along which the variance is computed.  The default is to compute
        the variance of the flattened array.
    dtype : data-type, optional
        Type to use in computing the variance.  For arrays of integer type
        the default is `float64`; for arrays of float types it is the same as
        the array type.
    out : ndarray, optional
        Alternate output array in which to place the result.  It must have
        the same shape as the expected output, but the type is cast if
        necessary.
    ddof : {int, float}, optional
        "Delta Degrees of Freedom": the divisor used in the calculation is
        ``N - ddof``, where ``N`` represents the number of non-NaN
        elements. By default `ddof` is zero.
    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the original `a`.
    where : array_like of bool, optional
        Elements to include in the variance. See `~numpy.ufunc.reduce` for
        details.

        .. versionadded:: 1.22.0

    mean : array_like, optional
        Provide the mean to prevent its recalculation. The mean should have
        a shape as if it was calculated with ``keepdims=True``.
        The axis for the calculation of the mean should be the same as used in
        the call to this var function.

        .. versionadded:: 2.0.0

    correction : {int, float}, optional
        Array API compatible name for the ``ddof`` parameter. Only one of them
        can be provided at the same time.

        .. versionadded:: 2.0.0

    Returns
    -------
    variance : ndarray, see dtype parameter above
        If `out` is None, return a new array containing the variance,
        otherwise return a reference to the output array. If ddof is >= the
        number of non-NaN elements in a slice or the slice contains only
        NaNs, then the result for that slice is NaN.

    See Also
    --------
    std : Standard deviation
    mean : Average
    var : Variance while not ignoring NaNs
    nanstd, nanmean
    :ref:`ufuncs-output-type`

    Notes
    -----
    The variance is the average of the squared deviations from the mean,
    i.e.,  ``var = mean(abs(x - x.mean())**2)``.

    The mean is normally calculated as ``x.sum() / N``, where ``N = len(x)``.
    If, however, `ddof` is specified, the divisor ``N - ddof`` is used
    instead.  In standard statistical practice, ``ddof=1`` provides an
    unbiased estimator of the variance of a hypothetical infinite
    population.  ``ddof=0`` provides a maximum likelihood estimate of the
    variance for normally distributed variables.

    Note that for complex numbers, the absolute value is taken before
    squaring, so that the result is always real and nonnegative.

    For floating-point input, the variance is computed using the same
    precision the input has.  Depending on the input data, this can cause
    the results to be inaccurate, especially for `float32` (see example
    below).  Specifying a higher-accuracy accumulator using the ``dtype``
    keyword can alleviate this issue.

    For this function to work on sub-classes of ndarray, they must define
    `sum` with the kwarg `keepdims`

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[1, np.nan], [3, 4]])
    >>> np.nanvar(a)
    1.5555555555555554
    >>> np.nanvar(a, axis=0)
    array([1.,  0.])
    >>> np.nanvar(a, axis=1)
    array([0.,  0.25])  # may vary

    """
    arr, mask = _replace_nan(a, 0)
    if mask is None:
        return np.var(arr, axis=axis, dtype=dtype, out=out, ddof=ddof,
                      keepdims=keepdims, where=where, mean=mean,
                      correction=correction)

    if dtype is not None:
        dtype = np.dtype(dtype)
    if dtype is not None and not issubclass(dtype.type, np.inexact):
        raise TypeError("If a is inexact, then dtype must be inexact")
    if out is not None and not issubclass(out.dtype.type, np.inexact):
        raise TypeError("If a is inexact, then out must be inexact")

    if correction != np._NoValue:
        if ddof != 0:
            raise ValueError(
                "ddof and correction can't be provided simultaneously."
            )
        else:
            ddof = correction

    # Compute mean
    if type(arr) is np.matrix:
        _keepdims = np._NoValue
    else:
        _keepdims = True

    cnt = np.sum(~mask, axis=axis, dtype=np.intp, keepdims=_keepdims,
                     where=where)

    if mean is not np._NoValue:
        avg = mean
    else:
        # we need to special case matrix for reverse compatibility
        # in order for this to work, these sums need to be called with
        # keepdims=True, however matrix now raises an error in this case, but
        # the reason that it drops the keepdims kwarg is to force keepdims=True
        # so this used to work by serendipity.
        avg = np.sum(arr, axis=axis, dtype=dtype,
                     keepdims=_keepdims, where=where)
        avg = _divide_by_count(avg, cnt)

    # Compute squared deviation from mean.
    np.subtract(arr, avg, out=arr, casting='unsafe', where=where)
    arr = _copyto(arr, 0, mask)
    if issubclass(arr.dtype.type, np.complexfloating):
        sqr = np.multiply(arr, arr.conj(), out=arr, where=where).real
    else:
        sqr = np.multiply(arr, arr, out=arr, where=where)

    # Compute variance.
    var = np.sum(sqr, axis=axis, dtype=dtype, out=out, keepdims=keepdims,
                 where=where)

    # Precaution against reduced object arrays
    try:
        var_ndim = var.ndim
    except AttributeError:
        var_ndim = np.ndim(var)
    if var_ndim < cnt.ndim:
        # Subclasses of ndarray may ignore keepdims, so check here.
        cnt = cnt.squeeze(axis)
    dof = cnt - ddof
    var = _divide_by_count(var, dof)

    isbad = (dof <= 0)
    if np.any(isbad):
        warnings.warn("Degrees of freedom <= 0 for slice.", RuntimeWarning,
                      stacklevel=2)
        # NaN, inf, or negative numbers are all possible bad
        # values, so explicitly replace them with NaN.
        var = _copyto(var, np.nan, isbad)
    return var


def _nanstd_dispatcher(a, axis=None, dtype=None, out=None, ddof=None,
                       keepdims=None, *, where=None, mean=None,
                       correction=None):
    return (a, out)


@array_function_dispatch(_nanstd_dispatcher)
def nanstd(a, axis=None, dtype=None, out=None, ddof=0, keepdims=np._NoValue,
           *, where=np._NoValue, mean=np._NoValue, correction=np._NoValue):
    """
    Compute the standard deviation along the specified axis, while
    ignoring NaNs.

    Returns the standard deviation, a measure of the spread of a
    distribution, of the non-NaN array elements. The standard deviation is
    computed for the flattened array by default, otherwise over the
    specified axis.

    For all-NaN slices or slices with zero degrees of freedom, NaN is
    returned and a `RuntimeWarning` is raised.

    Parameters
    ----------
    a : array_like
        Calculate the standard deviation of the non-NaN values.
    axis : {int, tuple of int, None}, optional
        Axis or axes along which the standard deviation is computed. The default is
        to compute the standard deviation of the flattened array.
    dtype : dtype, optional
        Type to use in computing the standard deviation. For arrays of
        integer type the default is float64, for arrays of float types it
        is the same as the array type.
    out : ndarray, optional
        Alternative output array in which to place the result. It must have
        the same shape as the expected output but the type (of the
        calculated values) will be cast if necessary.
    ddof : {int, float}, optional
        Means Delta Degrees of Freedom.  The divisor used in calculations
        is ``N - ddof``, where ``N`` represents the number of non-NaN
        elements.  By default `ddof` is zero.

    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the original `a`.

        If this value is anything but the default it is passed through
        as-is to the relevant functions of the sub-classes.  If these
        functions do not have a `keepdims` kwarg, a RuntimeError will
        be raised.
    where : array_like of bool, optional
        Elements to include in the standard deviation.
        See `~numpy.ufunc.reduce` for details.

        .. versionadded:: 1.22.0

    mean : array_like, optional
        Provide the mean to prevent its recalculation. The mean should have
        a shape as if it was calculated with ``keepdims=True``.
        The axis for the calculation of the mean should be the same as used in
        the call to this std function.

        .. versionadded:: 2.0.0

    correction : {int, float}, optional
        Array API compatible name for the ``ddof`` parameter. Only one of them
        can be provided at the same time.

        .. versionadded:: 2.0.0

    Returns
    -------
    standard_deviation : ndarray, see dtype parameter above.
        If `out` is None, return a new array containing the standard
        deviation, otherwise return a reference to the output array. If
        ddof is >= the number of non-NaN elements in a slice or the slice
        contains only NaNs, then the result for that slice is NaN.

    See Also
    --------
    var, mean, std
    nanvar, nanmean
    :ref:`ufuncs-output-type`

    Notes
    -----
    The standard deviation is the square root of the average of the squared
    deviations from the mean: ``std = sqrt(mean(abs(x - x.mean())**2))``.

    The average squared deviation is normally calculated as
    ``x.sum() / N``, where ``N = len(x)``.  If, however, `ddof` is
    specified, the divisor ``N - ddof`` is used instead. In standard
    statistical practice, ``ddof=1`` provides an unbiased estimator of the
    variance of the infinite population. ``ddof=0`` provides a maximum
    likelihood estimate of the variance for normally distributed variables.
    The standard deviation computed in this function is the square root of
    the estimated variance, so even with ``ddof=1``, it will not be an
    unbiased estimate of the standard deviation per se.

    Note that, for complex numbers, `std` takes the absolute value before
    squaring, so that the result is always real and nonnegative.

    For floating-point input, the *std* is computed using the same
    precision the input has. Depending on the input data, this can cause
    the results to be inaccurate, especially for float32 (see example
    below).  Specifying a higher-accuracy accumulator using the `dtype`
    keyword can alleviate this issue.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[1, np.nan], [3, 4]])
    >>> np.nanstd(a)
    1.247219128924647
    >>> np.nanstd(a, axis=0)
    array([1., 0.])
    >>> np.nanstd(a, axis=1)
    array([0.,  0.5]) # may vary

    """
    var = nanvar(a, axis=axis, dtype=dtype, out=out, ddof=ddof,
                 keepdims=keepdims, where=where, mean=mean,
                 correction=correction)
    if isinstance(var, np.ndarray):
        std = np.sqrt(var, out=var)
    elif hasattr(var, 'dtype'):
        std = var.dtype.type(np.sqrt(var))
    else:
        std = np.sqrt(var)
    return std

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\_nanfunctions_impl.py ===
"""
Functions that ignore NaN.

Functions
---------

- `nanmin` -- minimum non-NaN value
- `nanmax` -- maximum non-NaN value
- `nanargmin` -- index of minimum non-NaN value
- `nanargmax` -- index of maximum non-NaN value
- `nansum` -- sum of non-NaN values
- `nanprod` -- product of non-NaN values
- `nancumsum` -- cumulative sum of non-NaN values
- `nancumprod` -- cumulative product of non-NaN values
- `nanmean` -- mean of non-NaN values
- `nanvar` -- variance of non-NaN values
- `nanstd` -- standard deviation of non-NaN values
- `nanmedian` -- median of non-NaN values
- `nanquantile` -- qth quantile of non-NaN values
- `nanpercentile` -- qth percentile of non-NaN values

"""
import functools
import warnings

import numpy as np
import numpy._core.numeric as _nx
from numpy._core import overrides
from numpy.lib import _function_base_impl as fnb
from numpy.lib._function_base_impl import _weights_are_valid

array_function_dispatch = functools.partial(
    overrides.array_function_dispatch, module='numpy')


__all__ = [
    'nansum', 'nanmax', 'nanmin', 'nanargmax', 'nanargmin', 'nanmean',
    'nanmedian', 'nanpercentile', 'nanvar', 'nanstd', 'nanprod',
    'nancumsum', 'nancumprod', 'nanquantile'
    ]


def _nan_mask(a, out=None):
    """
    Parameters
    ----------
    a : array-like
        Input array with at least 1 dimension.
    out : ndarray, optional
        Alternate output array in which to place the result.  The default
        is ``None``; if provided, it must have the same shape as the
        expected output and will prevent the allocation of a new array.

    Returns
    -------
    y : bool ndarray or True
        A bool array where ``np.nan`` positions are marked with ``False``
        and other positions are marked with ``True``. If the type of ``a``
        is such that it can't possibly contain ``np.nan``, returns ``True``.
    """
    # we assume that a is an array for this private function

    if a.dtype.kind not in 'fc':
        return True

    y = np.isnan(a, out=out)
    y = np.invert(y, out=y)
    return y

def _replace_nan(a, val):
    """
    If `a` is of inexact type, make a copy of `a`, replace NaNs with
    the `val` value, and return the copy together with a boolean mask
    marking the locations where NaNs were present. If `a` is not of
    inexact type, do nothing and return `a` together with a mask of None.

    Note that scalars will end up as array scalars, which is important
    for using the result as the value of the out argument in some
    operations.

    Parameters
    ----------
    a : array-like
        Input array.
    val : float
        NaN values are set to val before doing the operation.

    Returns
    -------
    y : ndarray
        If `a` is of inexact type, return a copy of `a` with the NaNs
        replaced by the fill value, otherwise return `a`.
    mask: {bool, None}
        If `a` is of inexact type, return a boolean mask marking locations of
        NaNs, otherwise return None.

    """
    a = np.asanyarray(a)

    if a.dtype == np.object_:
        # object arrays do not support `isnan` (gh-9009), so make a guess
        mask = np.not_equal(a, a, dtype=bool)
    elif issubclass(a.dtype.type, np.inexact):
        mask = np.isnan(a)
    else:
        mask = None

    if mask is not None:
        a = np.array(a, subok=True, copy=True)
        np.copyto(a, val, where=mask)

    return a, mask


def _copyto(a, val, mask):
    """
    Replace values in `a` with NaN where `mask` is True.  This differs from
    copyto in that it will deal with the case where `a` is a numpy scalar.

    Parameters
    ----------
    a : ndarray or numpy scalar
        Array or numpy scalar some of whose values are to be replaced
        by val.
    val : numpy scalar
        Value used a replacement.
    mask : ndarray, scalar
        Boolean array. Where True the corresponding element of `a` is
        replaced by `val`. Broadcasts.

    Returns
    -------
    res : ndarray, scalar
        Array with elements replaced or scalar `val`.

    """
    if isinstance(a, np.ndarray):
        np.copyto(a, val, where=mask, casting='unsafe')
    else:
        a = a.dtype.type(val)
    return a


def _remove_nan_1d(arr1d, second_arr1d=None, overwrite_input=False):
    """
    Equivalent to arr1d[~arr1d.isnan()], but in a different order

    Presumably faster as it incurs fewer copies

    Parameters
    ----------
    arr1d : ndarray
        Array to remove nans from
    second_arr1d : ndarray or None
        A second array which will have the same positions removed as arr1d.
    overwrite_input : bool
        True if `arr1d` can be modified in place

    Returns
    -------
    res : ndarray
        Array with nan elements removed
    second_res : ndarray or None
        Second array with nan element positions of first array removed.
    overwrite_input : bool
        True if `res` can be modified in place, given the constraint on the
        input
    """
    if arr1d.dtype == object:
        # object arrays do not support `isnan` (gh-9009), so make a guess
        c = np.not_equal(arr1d, arr1d, dtype=bool)
    else:
        c = np.isnan(arr1d)

    s = np.nonzero(c)[0]
    if s.size == arr1d.size:
        warnings.warn("All-NaN slice encountered", RuntimeWarning,
                      stacklevel=6)
        if second_arr1d is None:
            return arr1d[:0], None, True
        else:
            return arr1d[:0], second_arr1d[:0], True
    elif s.size == 0:
        return arr1d, second_arr1d, overwrite_input
    else:
        if not overwrite_input:
            arr1d = arr1d.copy()
        # select non-nans at end of array
        enonan = arr1d[-s.size:][~c[-s.size:]]
        # fill nans in beginning of array with non-nans of end
        arr1d[s[:enonan.size]] = enonan

        if second_arr1d is None:
            return arr1d[:-s.size], None, True
        else:
            if not overwrite_input:
                second_arr1d = second_arr1d.copy()
            enonan = second_arr1d[-s.size:][~c[-s.size:]]
            second_arr1d[s[:enonan.size]] = enonan

            return arr1d[:-s.size], second_arr1d[:-s.size], True


def _divide_by_count(a, b, out=None):
    """
    Compute a/b ignoring invalid results. If `a` is an array the division
    is done in place. If `a` is a scalar, then its type is preserved in the
    output. If out is None, then a is used instead so that the division
    is in place. Note that this is only called with `a` an inexact type.

    Parameters
    ----------
    a : {ndarray, numpy scalar}
        Numerator. Expected to be of inexact type but not checked.
    b : {ndarray, numpy scalar}
        Denominator.
    out : ndarray, optional
        Alternate output array in which to place the result.  The default
        is ``None``; if provided, it must have the same shape as the
        expected output, but the type will be cast if necessary.

    Returns
    -------
    ret : {ndarray, numpy scalar}
        The return value is a/b. If `a` was an ndarray the division is done
        in place. If `a` is a numpy scalar, the division preserves its type.

    """
    with np.errstate(invalid='ignore', divide='ignore'):
        if isinstance(a, np.ndarray):
            if out is None:
                return np.divide(a, b, out=a, casting='unsafe')
            else:
                return np.divide(a, b, out=out, casting='unsafe')
        elif out is None:
            # Precaution against reduced object arrays
            try:
                return a.dtype.type(a / b)
            except AttributeError:
                return a / b
        else:
            # This is questionable, but currently a numpy scalar can
            # be output to a zero dimensional array.
            return np.divide(a, b, out=out, casting='unsafe')


def _nanmin_dispatcher(a, axis=None, out=None, keepdims=None,
                       initial=None, where=None):
    return (a, out)


@array_function_dispatch(_nanmin_dispatcher)
def nanmin(a, axis=None, out=None, keepdims=np._NoValue, initial=np._NoValue,
           where=np._NoValue):
    """
    Return minimum of an array or minimum along an axis, ignoring any NaNs.
    When all-NaN slices are encountered a ``RuntimeWarning`` is raised and
    Nan is returned for that slice.

    Parameters
    ----------
    a : array_like
        Array containing numbers whose minimum is desired. If `a` is not an
        array, a conversion is attempted.
    axis : {int, tuple of int, None}, optional
        Axis or axes along which the minimum is computed. The default is to compute
        the minimum of the flattened array.
    out : ndarray, optional
        Alternate output array in which to place the result.  The default
        is ``None``; if provided, it must have the same shape as the
        expected output, but the type will be cast if necessary. See
        :ref:`ufuncs-output-type` for more details.
    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the original `a`.

        If the value is anything but the default, then
        `keepdims` will be passed through to the `min` method
        of sub-classes of `ndarray`.  If the sub-classes methods
        does not implement `keepdims` any exceptions will be raised.
    initial : scalar, optional
        The maximum value of an output element. Must be present to allow
        computation on empty slice. See `~numpy.ufunc.reduce` for details.

        .. versionadded:: 1.22.0
    where : array_like of bool, optional
        Elements to compare for the minimum. See `~numpy.ufunc.reduce`
        for details.

        .. versionadded:: 1.22.0

    Returns
    -------
    nanmin : ndarray
        An array with the same shape as `a`, with the specified axis
        removed.  If `a` is a 0-d array, or if axis is None, an ndarray
        scalar is returned.  The same dtype as `a` is returned.

    See Also
    --------
    nanmax :
        The maximum value of an array along a given axis, ignoring any NaNs.
    amin :
        The minimum value of an array along a given axis, propagating any NaNs.
    fmin :
        Element-wise minimum of two arrays, ignoring any NaNs.
    minimum :
        Element-wise minimum of two arrays, propagating any NaNs.
    isnan :
        Shows which elements are Not a Number (NaN).
    isfinite:
        Shows which elements are neither NaN nor infinity.

    amax, fmax, maximum

    Notes
    -----
    NumPy uses the IEEE Standard for Binary Floating-Point for Arithmetic
    (IEEE 754). This means that Not a Number is not equivalent to infinity.
    Positive infinity is treated as a very large number and negative
    infinity is treated as a very small (i.e. negative) number.

    If the input has a integer type the function is equivalent to np.min.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[1, 2], [3, np.nan]])
    >>> np.nanmin(a)
    1.0
    >>> np.nanmin(a, axis=0)
    array([1.,  2.])
    >>> np.nanmin(a, axis=1)
    array([1.,  3.])

    When positive infinity and negative infinity are present:

    >>> np.nanmin([1, 2, np.nan, np.inf])
    1.0
    >>> np.nanmin([1, 2, np.nan, -np.inf])
    -inf

    """
    kwargs = {}
    if keepdims is not np._NoValue:
        kwargs['keepdims'] = keepdims
    if initial is not np._NoValue:
        kwargs['initial'] = initial
    if where is not np._NoValue:
        kwargs['where'] = where

    if (type(a) is np.ndarray or type(a) is np.memmap) and a.dtype != np.object_:
        # Fast, but not safe for subclasses of ndarray, or object arrays,
        # which do not implement isnan (gh-9009), or fmin correctly (gh-8975)
        res = np.fmin.reduce(a, axis=axis, out=out, **kwargs)
        if np.isnan(res).any():
            warnings.warn("All-NaN slice encountered", RuntimeWarning,
                          stacklevel=2)
    else:
        # Slow, but safe for subclasses of ndarray
        a, mask = _replace_nan(a, +np.inf)
        res = np.amin(a, axis=axis, out=out, **kwargs)
        if mask is None:
            return res

        # Check for all-NaN axis
        kwargs.pop("initial", None)
        mask = np.all(mask, axis=axis, **kwargs)
        if np.any(mask):
            res = _copyto(res, np.nan, mask)
            warnings.warn("All-NaN axis encountered", RuntimeWarning,
                          stacklevel=2)
    return res


def _nanmax_dispatcher(a, axis=None, out=None, keepdims=None,
                       initial=None, where=None):
    return (a, out)


@array_function_dispatch(_nanmax_dispatcher)
def nanmax(a, axis=None, out=None, keepdims=np._NoValue, initial=np._NoValue,
           where=np._NoValue):
    """
    Return the maximum of an array or maximum along an axis, ignoring any
    NaNs.  When all-NaN slices are encountered a ``RuntimeWarning`` is
    raised and NaN is returned for that slice.

    Parameters
    ----------
    a : array_like
        Array containing numbers whose maximum is desired. If `a` is not an
        array, a conversion is attempted.
    axis : {int, tuple of int, None}, optional
        Axis or axes along which the maximum is computed. The default is to compute
        the maximum of the flattened array.
    out : ndarray, optional
        Alternate output array in which to place the result.  The default
        is ``None``; if provided, it must have the same shape as the
        expected output, but the type will be cast if necessary. See
        :ref:`ufuncs-output-type` for more details.
    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the original `a`.
        If the value is anything but the default, then
        `keepdims` will be passed through to the `max` method
        of sub-classes of `ndarray`.  If the sub-classes methods
        does not implement `keepdims` any exceptions will be raised.
    initial : scalar, optional
        The minimum value of an output element. Must be present to allow
        computation on empty slice. See `~numpy.ufunc.reduce` for details.

        .. versionadded:: 1.22.0
    where : array_like of bool, optional
        Elements to compare for the maximum. See `~numpy.ufunc.reduce`
        for details.

        .. versionadded:: 1.22.0

    Returns
    -------
    nanmax : ndarray
        An array with the same shape as `a`, with the specified axis removed.
        If `a` is a 0-d array, or if axis is None, an ndarray scalar is
        returned.  The same dtype as `a` is returned.

    See Also
    --------
    nanmin :
        The minimum value of an array along a given axis, ignoring any NaNs.
    amax :
        The maximum value of an array along a given axis, propagating any NaNs.
    fmax :
        Element-wise maximum of two arrays, ignoring any NaNs.
    maximum :
        Element-wise maximum of two arrays, propagating any NaNs.
    isnan :
        Shows which elements are Not a Number (NaN).
    isfinite:
        Shows which elements are neither NaN nor infinity.

    amin, fmin, minimum

    Notes
    -----
    NumPy uses the IEEE Standard for Binary Floating-Point for Arithmetic
    (IEEE 754). This means that Not a Number is not equivalent to infinity.
    Positive infinity is treated as a very large number and negative
    infinity is treated as a very small (i.e. negative) number.

    If the input has a integer type the function is equivalent to np.max.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[1, 2], [3, np.nan]])
    >>> np.nanmax(a)
    3.0
    >>> np.nanmax(a, axis=0)
    array([3.,  2.])
    >>> np.nanmax(a, axis=1)
    array([2.,  3.])

    When positive infinity and negative infinity are present:

    >>> np.nanmax([1, 2, np.nan, -np.inf])
    2.0
    >>> np.nanmax([1, 2, np.nan, np.inf])
    inf

    """
    kwargs = {}
    if keepdims is not np._NoValue:
        kwargs['keepdims'] = keepdims
    if initial is not np._NoValue:
        kwargs['initial'] = initial
    if where is not np._NoValue:
        kwargs['where'] = where

    if (type(a) is np.ndarray or type(a) is np.memmap) and a.dtype != np.object_:
        # Fast, but not safe for subclasses of ndarray, or object arrays,
        # which do not implement isnan (gh-9009), or fmax correctly (gh-8975)
        res = np.fmax.reduce(a, axis=axis, out=out, **kwargs)
        if np.isnan(res).any():
            warnings.warn("All-NaN slice encountered", RuntimeWarning,
                          stacklevel=2)
    else:
        # Slow, but safe for subclasses of ndarray
        a, mask = _replace_nan(a, -np.inf)
        res = np.amax(a, axis=axis, out=out, **kwargs)
        if mask is None:
            return res

        # Check for all-NaN axis
        kwargs.pop("initial", None)
        mask = np.all(mask, axis=axis, **kwargs)
        if np.any(mask):
            res = _copyto(res, np.nan, mask)
            warnings.warn("All-NaN axis encountered", RuntimeWarning,
                          stacklevel=2)
    return res


def _nanargmin_dispatcher(a, axis=None, out=None, *, keepdims=None):
    return (a,)


@array_function_dispatch(_nanargmin_dispatcher)
def nanargmin(a, axis=None, out=None, *, keepdims=np._NoValue):
    """
    Return the indices of the minimum values in the specified axis ignoring
    NaNs. For all-NaN slices ``ValueError`` is raised. Warning: the results
    cannot be trusted if a slice contains only NaNs and Infs.

    Parameters
    ----------
    a : array_like
        Input data.
    axis : int, optional
        Axis along which to operate.  By default flattened input is used.
    out : array, optional
        If provided, the result will be inserted into this array. It should
        be of the appropriate shape and dtype.

        .. versionadded:: 1.22.0
    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the array.

        .. versionadded:: 1.22.0

    Returns
    -------
    index_array : ndarray
        An array of indices or a single index value.

    See Also
    --------
    argmin, nanargmax

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[np.nan, 4], [2, 3]])
    >>> np.argmin(a)
    0
    >>> np.nanargmin(a)
    2
    >>> np.nanargmin(a, axis=0)
    array([1, 1])
    >>> np.nanargmin(a, axis=1)
    array([1, 0])

    """
    a, mask = _replace_nan(a, np.inf)
    if mask is not None and mask.size:
        mask = np.all(mask, axis=axis)
        if np.any(mask):
            raise ValueError("All-NaN slice encountered")
    res = np.argmin(a, axis=axis, out=out, keepdims=keepdims)
    return res


def _nanargmax_dispatcher(a, axis=None, out=None, *, keepdims=None):
    return (a,)


@array_function_dispatch(_nanargmax_dispatcher)
def nanargmax(a, axis=None, out=None, *, keepdims=np._NoValue):
    """
    Return the indices of the maximum values in the specified axis ignoring
    NaNs. For all-NaN slices ``ValueError`` is raised. Warning: the
    results cannot be trusted if a slice contains only NaNs and -Infs.


    Parameters
    ----------
    a : array_like
        Input data.
    axis : int, optional
        Axis along which to operate.  By default flattened input is used.
    out : array, optional
        If provided, the result will be inserted into this array. It should
        be of the appropriate shape and dtype.

        .. versionadded:: 1.22.0
    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the array.

        .. versionadded:: 1.22.0

    Returns
    -------
    index_array : ndarray
        An array of indices or a single index value.

    See Also
    --------
    argmax, nanargmin

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[np.nan, 4], [2, 3]])
    >>> np.argmax(a)
    0
    >>> np.nanargmax(a)
    1
    >>> np.nanargmax(a, axis=0)
    array([1, 0])
    >>> np.nanargmax(a, axis=1)
    array([1, 1])

    """
    a, mask = _replace_nan(a, -np.inf)
    if mask is not None and mask.size:
        mask = np.all(mask, axis=axis)
        if np.any(mask):
            raise ValueError("All-NaN slice encountered")
    res = np.argmax(a, axis=axis, out=out, keepdims=keepdims)
    return res


def _nansum_dispatcher(a, axis=None, dtype=None, out=None, keepdims=None,
                       initial=None, where=None):
    return (a, out)


@array_function_dispatch(_nansum_dispatcher)
def nansum(a, axis=None, dtype=None, out=None, keepdims=np._NoValue,
           initial=np._NoValue, where=np._NoValue):
    """
    Return the sum of array elements over a given axis treating Not a
    Numbers (NaNs) as zero.

    In NumPy versions <= 1.9.0 Nan is returned for slices that are all-NaN or
    empty. In later versions zero is returned.

    Parameters
    ----------
    a : array_like
        Array containing numbers whose sum is desired. If `a` is not an
        array, a conversion is attempted.
    axis : {int, tuple of int, None}, optional
        Axis or axes along which the sum is computed. The default is to compute the
        sum of the flattened array.
    dtype : data-type, optional
        The type of the returned array and of the accumulator in which the
        elements are summed.  By default, the dtype of `a` is used.  An
        exception is when `a` has an integer type with less precision than
        the platform (u)intp. In that case, the default will be either
        (u)int32 or (u)int64 depending on whether the platform is 32 or 64
        bits. For inexact inputs, dtype must be inexact.
    out : ndarray, optional
        Alternate output array in which to place the result.  The default
        is ``None``. If provided, it must have the same shape as the
        expected output, but the type will be cast if necessary.  See
        :ref:`ufuncs-output-type` for more details. The casting of NaN to integer
        can yield unexpected results.
    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the original `a`.

        If the value is anything but the default, then
        `keepdims` will be passed through to the `mean` or `sum` methods
        of sub-classes of `ndarray`.  If the sub-classes methods
        does not implement `keepdims` any exceptions will be raised.
    initial : scalar, optional
        Starting value for the sum. See `~numpy.ufunc.reduce` for details.

        .. versionadded:: 1.22.0
    where : array_like of bool, optional
        Elements to include in the sum. See `~numpy.ufunc.reduce` for details.

        .. versionadded:: 1.22.0

    Returns
    -------
    nansum : ndarray.
        A new array holding the result is returned unless `out` is
        specified, in which it is returned. The result has the same
        size as `a`, and the same shape as `a` if `axis` is not None
        or `a` is a 1-d array.

    See Also
    --------
    numpy.sum : Sum across array propagating NaNs.
    isnan : Show which elements are NaN.
    isfinite : Show which elements are not NaN or +/-inf.

    Notes
    -----
    If both positive and negative infinity are present, the sum will be Not
    A Number (NaN).

    Examples
    --------
    >>> import numpy as np
    >>> np.nansum(1)
    1
    >>> np.nansum([1])
    1
    >>> np.nansum([1, np.nan])
    1.0
    >>> a = np.array([[1, 1], [1, np.nan]])
    >>> np.nansum(a)
    3.0
    >>> np.nansum(a, axis=0)
    array([2.,  1.])
    >>> np.nansum([1, np.nan, np.inf])
    inf
    >>> np.nansum([1, np.nan, -np.inf])
    -inf
    >>> from numpy.testing import suppress_warnings
    >>> with np.errstate(invalid="ignore"):
    ...     np.nansum([1, np.nan, np.inf, -np.inf]) # both +/- infinity present
    np.float64(nan)

    """
    a, mask = _replace_nan(a, 0)
    return np.sum(a, axis=axis, dtype=dtype, out=out, keepdims=keepdims,
                  initial=initial, where=where)


def _nanprod_dispatcher(a, axis=None, dtype=None, out=None, keepdims=None,
                        initial=None, where=None):
    return (a, out)


@array_function_dispatch(_nanprod_dispatcher)
def nanprod(a, axis=None, dtype=None, out=None, keepdims=np._NoValue,
            initial=np._NoValue, where=np._NoValue):
    """
    Return the product of array elements over a given axis treating Not a
    Numbers (NaNs) as ones.

    One is returned for slices that are all-NaN or empty.

    Parameters
    ----------
    a : array_like
        Array containing numbers whose product is desired. If `a` is not an
        array, a conversion is attempted.
    axis : {int, tuple of int, None}, optional
        Axis or axes along which the product is computed. The default is to compute
        the product of the flattened array.
    dtype : data-type, optional
        The type of the returned array and of the accumulator in which the
        elements are summed.  By default, the dtype of `a` is used.  An
        exception is when `a` has an integer type with less precision than
        the platform (u)intp. In that case, the default will be either
        (u)int32 or (u)int64 depending on whether the platform is 32 or 64
        bits. For inexact inputs, dtype must be inexact.
    out : ndarray, optional
        Alternate output array in which to place the result.  The default
        is ``None``. If provided, it must have the same shape as the
        expected output, but the type will be cast if necessary. See
        :ref:`ufuncs-output-type` for more details. The casting of NaN to integer
        can yield unexpected results.
    keepdims : bool, optional
        If True, the axes which are reduced are left in the result as
        dimensions with size one. With this option, the result will
        broadcast correctly against the original `arr`.
    initial : scalar, optional
        The starting value for this product. See `~numpy.ufunc.reduce`
        for details.

        .. versionadded:: 1.22.0
    where : array_like of bool, optional
        Elements to include in the product. See `~numpy.ufunc.reduce`
        for details.

        .. versionadded:: 1.22.0

    Returns
    -------
    nanprod : ndarray
        A new array holding the result is returned unless `out` is
        specified, in which case it is returned.

    See Also
    --------
    numpy.prod : Product across array propagating NaNs.
    isnan : Show which elements are NaN.

    Examples
    --------
    >>> import numpy as np
    >>> np.nanprod(1)
    1
    >>> np.nanprod([1])
    1
    >>> np.nanprod([1, np.nan])
    1.0
    >>> a = np.array([[1, 2], [3, np.nan]])
    >>> np.nanprod(a)
    6.0
    >>> np.nanprod(a, axis=0)
    array([3., 2.])

    """
    a, mask = _replace_nan(a, 1)
    return np.prod(a, axis=axis, dtype=dtype, out=out, keepdims=keepdims,
                   initial=initial, where=where)


def _nancumsum_dispatcher(a, axis=None, dtype=None, out=None):
    return (a, out)


@array_function_dispatch(_nancumsum_dispatcher)
def nancumsum(a, axis=None, dtype=None, out=None):
    """
    Return the cumulative sum of array elements over a given axis treating Not a
    Numbers (NaNs) as zero.  The cumulative sum does not change when NaNs are
    encountered and leading NaNs are replaced by zeros.

    Zeros are returned for slices that are all-NaN or empty.

    Parameters
    ----------
    a : array_like
        Input array.
    axis : int, optional
        Axis along which the cumulative sum is computed. The default
        (None) is to compute the cumsum over the flattened array.
    dtype : dtype, optional
        Type of the returned array and of the accumulator in which the
        elements are summed.  If `dtype` is not specified, it defaults
        to the dtype of `a`, unless `a` has an integer dtype with a
        precision less than that of the default platform integer.  In
        that case, the default platform integer is used.
    out : ndarray, optional
        Alternative output array in which to place the result. It must
        have the same shape and buffer length as the expected output
        but the type will be cast if necessary. See :ref:`ufuncs-output-type` for
        more details.

    Returns
    -------
    nancumsum : ndarray.
        A new array holding the result is returned unless `out` is
        specified, in which it is returned. The result has the same
        size as `a`, and the same shape as `a` if `axis` is not None
        or `a` is a 1-d array.

    See Also
    --------
    numpy.cumsum : Cumulative sum across array propagating NaNs.
    isnan : Show which elements are NaN.

    Examples
    --------
    >>> import numpy as np
    >>> np.nancumsum(1)
    array([1])
    >>> np.nancumsum([1])
    array([1])
    >>> np.nancumsum([1, np.nan])
    array([1.,  1.])
    >>> a = np.array([[1, 2], [3, np.nan]])
    >>> np.nancumsum(a)
    array([1.,  3.,  6.,  6.])
    >>> np.nancumsum(a, axis=0)
    array([[1.,  2.],
           [4.,  2.]])
    >>> np.nancumsum(a, axis=1)
    array([[1.,  3.],
           [3.,  3.]])

    """
    a, mask = _replace_nan(a, 0)
    return np.cumsum(a, axis=axis, dtype=dtype, out=out)


def _nancumprod_dispatcher(a, axis=None, dtype=None, out=None):
    return (a, out)


@array_function_dispatch(_nancumprod_dispatcher)
def nancumprod(a, axis=None, dtype=None, out=None):
    """
    Return the cumulative product of array elements over a given axis treating Not a
    Numbers (NaNs) as one.  The cumulative product does not change when NaNs are
    encountered and leading NaNs are replaced by ones.

    Ones are returned for slices that are all-NaN or empty.

    Parameters
    ----------
    a : array_like
        Input array.
    axis : int, optional
        Axis along which the cumulative product is computed.  By default
        the input is flattened.
    dtype : dtype, optional
        Type of the returned array, as well as of the accumulator in which
        the elements are multiplied.  If *dtype* is not specified, it
        defaults to the dtype of `a`, unless `a` has an integer dtype with
        a precision less than that of the default platform integer.  In
        that case, the default platform integer is used instead.
    out : ndarray, optional
        Alternative output array in which to place the result. It must
        have the same shape and buffer length as the expected output
        but the type of the resulting values will be cast if necessary.

    Returns
    -------
    nancumprod : ndarray
        A new array holding the result is returned unless `out` is
        specified, in which case it is returned.

    See Also
    --------
    numpy.cumprod : Cumulative product across array propagating NaNs.
    isnan : Show which elements are NaN.

    Examples
    --------
    >>> import numpy as np
    >>> np.nancumprod(1)
    array([1])
    >>> np.nancumprod([1])
    array([1])
    >>> np.nancumprod([1, np.nan])
    array([1.,  1.])
    >>> a = np.array([[1, 2], [3, np.nan]])
    >>> np.nancumprod(a)
    array([1.,  2.,  6.,  6.])
    >>> np.nancumprod(a, axis=0)
    array([[1.,  2.],
           [3.,  2.]])
    >>> np.nancumprod(a, axis=1)
    array([[1.,  2.],
           [3.,  3.]])

    """
    a, mask = _replace_nan(a, 1)
    return np.cumprod(a, axis=axis, dtype=dtype, out=out)


def _nanmean_dispatcher(a, axis=None, dtype=None, out=None, keepdims=None,
                        *, where=None):
    return (a, out)


@array_function_dispatch(_nanmean_dispatcher)
def nanmean(a, axis=None, dtype=None, out=None, keepdims=np._NoValue,
            *, where=np._NoValue):
    """
    Compute the arithmetic mean along the specified axis, ignoring NaNs.

    Returns the average of the array elements.  The average is taken over
    the flattened array by default, otherwise over the specified axis.
    `float64` intermediate and return values are used for integer inputs.

    For all-NaN slices, NaN is returned and a `RuntimeWarning` is raised.

    Parameters
    ----------
    a : array_like
        Array containing numbers whose mean is desired. If `a` is not an
        array, a conversion is attempted.
    axis : {int, tuple of int, None}, optional
        Axis or axes along which the means are computed. The default is to compute
        the mean of the flattened array.
    dtype : data-type, optional
        Type to use in computing the mean.  For integer inputs, the default
        is `float64`; for inexact inputs, it is the same as the input
        dtype.
    out : ndarray, optional
        Alternate output array in which to place the result.  The default
        is ``None``; if provided, it must have the same shape as the
        expected output, but the type will be cast if necessary.
        See :ref:`ufuncs-output-type` for more details.
    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the original `a`.

        If the value is anything but the default, then
        `keepdims` will be passed through to the `mean` or `sum` methods
        of sub-classes of `ndarray`.  If the sub-classes methods
        does not implement `keepdims` any exceptions will be raised.
    where : array_like of bool, optional
        Elements to include in the mean. See `~numpy.ufunc.reduce` for details.

        .. versionadded:: 1.22.0

    Returns
    -------
    m : ndarray, see dtype parameter above
        If `out=None`, returns a new array containing the mean values,
        otherwise a reference to the output array is returned. Nan is
        returned for slices that contain only NaNs.

    See Also
    --------
    average : Weighted average
    mean : Arithmetic mean taken while not ignoring NaNs
    var, nanvar

    Notes
    -----
    The arithmetic mean is the sum of the non-NaN elements along the axis
    divided by the number of non-NaN elements.

    Note that for floating-point input, the mean is computed using the same
    precision the input has.  Depending on the input data, this can cause
    the results to be inaccurate, especially for `float32`.  Specifying a
    higher-precision accumulator using the `dtype` keyword can alleviate
    this issue.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[1, np.nan], [3, 4]])
    >>> np.nanmean(a)
    2.6666666666666665
    >>> np.nanmean(a, axis=0)
    array([2.,  4.])
    >>> np.nanmean(a, axis=1)
    array([1.,  3.5]) # may vary

    """
    arr, mask = _replace_nan(a, 0)
    if mask is None:
        return np.mean(arr, axis=axis, dtype=dtype, out=out, keepdims=keepdims,
                       where=where)

    if dtype is not None:
        dtype = np.dtype(dtype)
    if dtype is not None and not issubclass(dtype.type, np.inexact):
        raise TypeError("If a is inexact, then dtype must be inexact")
    if out is not None and not issubclass(out.dtype.type, np.inexact):
        raise TypeError("If a is inexact, then out must be inexact")

    cnt = np.sum(~mask, axis=axis, dtype=np.intp, keepdims=keepdims,
                 where=where)
    tot = np.sum(arr, axis=axis, dtype=dtype, out=out, keepdims=keepdims,
                 where=where)
    avg = _divide_by_count(tot, cnt, out=out)

    isbad = (cnt == 0)
    if isbad.any():
        warnings.warn("Mean of empty slice", RuntimeWarning, stacklevel=2)
        # NaN is the only possible bad value, so no further
        # action is needed to handle bad results.
    return avg


def _nanmedian1d(arr1d, overwrite_input=False):
    """
    Private function for rank 1 arrays. Compute the median ignoring NaNs.
    See nanmedian for parameter usage
    """
    arr1d_parsed, _, overwrite_input = _remove_nan_1d(
        arr1d, overwrite_input=overwrite_input,
    )

    if arr1d_parsed.size == 0:
        # Ensure that a nan-esque scalar of the appropriate type (and unit)
        # is returned for `timedelta64` and `complexfloating`
        return arr1d[-1]

    return np.median(arr1d_parsed, overwrite_input=overwrite_input)


def _nanmedian(a, axis=None, out=None, overwrite_input=False):
    """
    Private function that doesn't support extended axis or keepdims.
    These methods are extended to this function using _ureduce
    See nanmedian for parameter usage

    """
    if axis is None or a.ndim == 1:
        part = a.ravel()
        if out is None:
            return _nanmedian1d(part, overwrite_input)
        else:
            out[...] = _nanmedian1d(part, overwrite_input)
            return out
    else:
        # for small medians use sort + indexing which is still faster than
        # apply_along_axis
        # benchmarked with shuffled (50, 50, x) containing a few NaN
        if a.shape[axis] < 600:
            return _nanmedian_small(a, axis, out, overwrite_input)
        result = np.apply_along_axis(_nanmedian1d, axis, a, overwrite_input)
        if out is not None:
            out[...] = result
        return result


def _nanmedian_small(a, axis=None, out=None, overwrite_input=False):
    """
    sort + indexing median, faster for small medians along multiple
    dimensions due to the high overhead of apply_along_axis

    see nanmedian for parameter usage
    """
    a = np.ma.masked_array(a, np.isnan(a))
    m = np.ma.median(a, axis=axis, overwrite_input=overwrite_input)
    for i in range(np.count_nonzero(m.mask.ravel())):
        warnings.warn("All-NaN slice encountered", RuntimeWarning,
                      stacklevel=5)

    fill_value = np.timedelta64("NaT") if m.dtype.kind == "m" else np.nan
    if out is not None:
        out[...] = m.filled(fill_value)
        return out
    return m.filled(fill_value)


def _nanmedian_dispatcher(
        a, axis=None, out=None, overwrite_input=None, keepdims=None):
    return (a, out)


@array_function_dispatch(_nanmedian_dispatcher)
def nanmedian(a, axis=None, out=None, overwrite_input=False, keepdims=np._NoValue):
    """
    Compute the median along the specified axis, while ignoring NaNs.

    Returns the median of the array elements.

    Parameters
    ----------
    a : array_like
        Input array or object that can be converted to an array.
    axis : {int, sequence of int, None}, optional
        Axis or axes along which the medians are computed. The default
        is to compute the median along a flattened version of the array.
        A sequence of axes is supported since version 1.9.0.
    out : ndarray, optional
        Alternative output array in which to place the result. It must
        have the same shape and buffer length as the expected output,
        but the type (of the output) will be cast if necessary.
    overwrite_input : bool, optional
       If True, then allow use of memory of input array `a` for
       calculations. The input array will be modified by the call to
       `median`. This will save memory when you do not need to preserve
       the contents of the input array. Treat the input as undefined,
       but it will probably be fully or partially sorted. Default is
       False. If `overwrite_input` is ``True`` and `a` is not already an
       `ndarray`, an error will be raised.
    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the original `a`.

        If this is anything but the default value it will be passed
        through (in the special case of an empty array) to the
        `mean` function of the underlying array.  If the array is
        a sub-class and `mean` does not have the kwarg `keepdims` this
        will raise a RuntimeError.

    Returns
    -------
    median : ndarray
        A new array holding the result. If the input contains integers
        or floats smaller than ``float64``, then the output data-type is
        ``np.float64``.  Otherwise, the data-type of the output is the
        same as that of the input. If `out` is specified, that array is
        returned instead.

    See Also
    --------
    mean, median, percentile

    Notes
    -----
    Given a vector ``V`` of length ``N``, the median of ``V`` is the
    middle value of a sorted copy of ``V``, ``V_sorted`` - i.e.,
    ``V_sorted[(N-1)/2]``, when ``N`` is odd and the average of the two
    middle values of ``V_sorted`` when ``N`` is even.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[10.0, 7, 4], [3, 2, 1]])
    >>> a[0, 1] = np.nan
    >>> a
    array([[10., nan,  4.],
           [ 3.,  2.,  1.]])
    >>> np.median(a)
    np.float64(nan)
    >>> np.nanmedian(a)
    3.0
    >>> np.nanmedian(a, axis=0)
    array([6.5, 2. , 2.5])
    >>> np.median(a, axis=1)
    array([nan,  2.])
    >>> b = a.copy()
    >>> np.nanmedian(b, axis=1, overwrite_input=True)
    array([7.,  2.])
    >>> assert not np.all(a==b)
    >>> b = a.copy()
    >>> np.nanmedian(b, axis=None, overwrite_input=True)
    3.0
    >>> assert not np.all(a==b)

    """
    a = np.asanyarray(a)
    # apply_along_axis in _nanmedian doesn't handle empty arrays well,
    # so deal them upfront
    if a.size == 0:
        return np.nanmean(a, axis, out=out, keepdims=keepdims)

    return fnb._ureduce(a, func=_nanmedian, keepdims=keepdims,
                        axis=axis, out=out,
                        overwrite_input=overwrite_input)


def _nanpercentile_dispatcher(
        a, q, axis=None, out=None, overwrite_input=None,
        method=None, keepdims=None, *, weights=None, interpolation=None):
    return (a, q, out, weights)


@array_function_dispatch(_nanpercentile_dispatcher)
def nanpercentile(
        a,
        q,
        axis=None,
        out=None,
        overwrite_input=False,
        method="linear",
        keepdims=np._NoValue,
        *,
        weights=None,
        interpolation=None,
):
    """
    Compute the qth percentile of the data along the specified axis,
    while ignoring nan values.

    Returns the qth percentile(s) of the array elements.

    Parameters
    ----------
    a : array_like
        Input array or object that can be converted to an array, containing
        nan values to be ignored.
    q : array_like of float
        Percentile or sequence of percentiles to compute, which must be
        between 0 and 100 inclusive.
    axis : {int, tuple of int, None}, optional
        Axis or axes along which the percentiles are computed. The default
        is to compute the percentile(s) along a flattened version of the
        array.
    out : ndarray, optional
        Alternative output array in which to place the result. It must have
        the same shape and buffer length as the expected output, but the
        type (of the output) will be cast if necessary.
    overwrite_input : bool, optional
        If True, then allow the input array `a` to be modified by
        intermediate calculations, to save memory. In this case, the
        contents of the input `a` after this function completes is
        undefined.
    method : str, optional
        This parameter specifies the method to use for estimating the
        percentile.  There are many different methods, some unique to NumPy.
        See the notes for explanation.  The options sorted by their R type
        as summarized in the H&F paper [1]_ are:

        1. 'inverted_cdf'
        2. 'averaged_inverted_cdf'
        3. 'closest_observation'
        4. 'interpolated_inverted_cdf'
        5. 'hazen'
        6. 'weibull'
        7. 'linear'  (default)
        8. 'median_unbiased'
        9. 'normal_unbiased'

        The first three methods are discontinuous.  NumPy further defines the
        following discontinuous variations of the default 'linear' (7.) option:

        * 'lower'
        * 'higher',
        * 'midpoint'
        * 'nearest'

        .. versionchanged:: 1.22.0
            This argument was previously called "interpolation" and only
            offered the "linear" default and last four options.

    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left in
        the result as dimensions with size one. With this option, the
        result will broadcast correctly against the original array `a`.

        If this is anything but the default value it will be passed
        through (in the special case of an empty array) to the
        `mean` function of the underlying array.  If the array is
        a sub-class and `mean` does not have the kwarg `keepdims` this
        will raise a RuntimeError.

    weights : array_like, optional
        An array of weights associated with the values in `a`. Each value in
        `a` contributes to the percentile according to its associated weight.
        The weights array can either be 1-D (in which case its length must be
        the size of `a` along the given axis) or of the same shape as `a`.
        If `weights=None`, then all data in `a` are assumed to have a
        weight equal to one.
        Only `method="inverted_cdf"` supports weights.

        .. versionadded:: 2.0.0

    interpolation : str, optional
        Deprecated name for the method keyword argument.

        .. deprecated:: 1.22.0

    Returns
    -------
    percentile : scalar or ndarray
        If `q` is a single percentile and `axis=None`, then the result
        is a scalar. If multiple percentiles are given, first axis of
        the result corresponds to the percentiles. The other axes are
        the axes that remain after the reduction of `a`. If the input
        contains integers or floats smaller than ``float64``, the output
        data-type is ``float64``. Otherwise, the output data-type is the
        same as that of the input. If `out` is specified, that array is
        returned instead.

    See Also
    --------
    nanmean
    nanmedian : equivalent to ``nanpercentile(..., 50)``
    percentile, median, mean
    nanquantile : equivalent to nanpercentile, except q in range [0, 1].

    Notes
    -----
    The behavior of `numpy.nanpercentile` with percentage `q` is that of
    `numpy.quantile` with argument ``q/100`` (ignoring nan values).
    For more information, please see `numpy.quantile`.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[10., 7., 4.], [3., 2., 1.]])
    >>> a[0][1] = np.nan
    >>> a
    array([[10.,  nan,   4.],
          [ 3.,   2.,   1.]])
    >>> np.percentile(a, 50)
    np.float64(nan)
    >>> np.nanpercentile(a, 50)
    3.0
    >>> np.nanpercentile(a, 50, axis=0)
    array([6.5, 2. , 2.5])
    >>> np.nanpercentile(a, 50, axis=1, keepdims=True)
    array([[7.],
           [2.]])
    >>> m = np.nanpercentile(a, 50, axis=0)
    >>> out = np.zeros_like(m)
    >>> np.nanpercentile(a, 50, axis=0, out=out)
    array([6.5, 2. , 2.5])
    >>> m
    array([6.5,  2. ,  2.5])

    >>> b = a.copy()
    >>> np.nanpercentile(b, 50, axis=1, overwrite_input=True)
    array([7., 2.])
    >>> assert not np.all(a==b)

    References
    ----------
    .. [1] R. J. Hyndman and Y. Fan,
       "Sample quantiles in statistical packages,"
       The American Statistician, 50(4), pp. 361-365, 1996

    """
    if interpolation is not None:
        method = fnb._check_interpolation_as_method(
            method, interpolation, "nanpercentile")

    a = np.asanyarray(a)
    if a.dtype.kind == "c":
        raise TypeError("a must be an array of real numbers")

    q = np.true_divide(q, a.dtype.type(100) if a.dtype.kind == "f" else 100, out=...)
    if not fnb._quantile_is_valid(q):
        raise ValueError("Percentiles must be in the range [0, 100]")

    if weights is not None:
        if method != "inverted_cdf":
            msg = ("Only method 'inverted_cdf' supports weights. "
                   f"Got: {method}.")
            raise ValueError(msg)
        if axis is not None:
            axis = _nx.normalize_axis_tuple(axis, a.ndim, argname="axis")
        weights = _weights_are_valid(weights=weights, a=a, axis=axis)
        if np.any(weights < 0):
            raise ValueError("Weights must be non-negative.")

    return _nanquantile_unchecked(
        a, q, axis, out, overwrite_input, method, keepdims, weights)


def _nanquantile_dispatcher(a, q, axis=None, out=None, overwrite_input=None,
                            method=None, keepdims=None, *, weights=None,
                            interpolation=None):
    return (a, q, out, weights)


@array_function_dispatch(_nanquantile_dispatcher)
def nanquantile(
        a,
        q,
        axis=None,
        out=None,
        overwrite_input=False,
        method="linear",
        keepdims=np._NoValue,
        *,
        weights=None,
        interpolation=None,
):
    """
    Compute the qth quantile of the data along the specified axis,
    while ignoring nan values.
    Returns the qth quantile(s) of the array elements.

    Parameters
    ----------
    a : array_like
        Input array or object that can be converted to an array, containing
        nan values to be ignored
    q : array_like of float
        Probability or sequence of probabilities for the quantiles to compute.
        Values must be between 0 and 1 inclusive.
    axis : {int, tuple of int, None}, optional
        Axis or axes along which the quantiles are computed. The
        default is to compute the quantile(s) along a flattened
        version of the array.
    out : ndarray, optional
        Alternative output array in which to place the result. It must
        have the same shape and buffer length as the expected output,
        but the type (of the output) will be cast if necessary.
    overwrite_input : bool, optional
        If True, then allow the input array `a` to be modified by intermediate
        calculations, to save memory. In this case, the contents of the input
        `a` after this function completes is undefined.
    method : str, optional
        This parameter specifies the method to use for estimating the
        quantile.  There are many different methods, some unique to NumPy.
        See the notes for explanation.  The options sorted by their R type
        as summarized in the H&F paper [1]_ are:

        1. 'inverted_cdf'
        2. 'averaged_inverted_cdf'
        3. 'closest_observation'
        4. 'interpolated_inverted_cdf'
        5. 'hazen'
        6. 'weibull'
        7. 'linear'  (default)
        8. 'median_unbiased'
        9. 'normal_unbiased'

        The first three methods are discontinuous.  NumPy further defines the
        following discontinuous variations of the default 'linear' (7.) option:

        * 'lower'
        * 'higher',
        * 'midpoint'
        * 'nearest'

        .. versionchanged:: 1.22.0
            This argument was previously called "interpolation" and only
            offered the "linear" default and last four options.

    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left in
        the result as dimensions with size one. With this option, the
        result will broadcast correctly against the original array `a`.

        If this is anything but the default value it will be passed
        through (in the special case of an empty array) to the
        `mean` function of the underlying array.  If the array is
        a sub-class and `mean` does not have the kwarg `keepdims` this
        will raise a RuntimeError.

    weights : array_like, optional
        An array of weights associated with the values in `a`. Each value in
        `a` contributes to the quantile according to its associated weight.
        The weights array can either be 1-D (in which case its length must be
        the size of `a` along the given axis) or of the same shape as `a`.
        If `weights=None`, then all data in `a` are assumed to have a
        weight equal to one.
        Only `method="inverted_cdf"` supports weights.

        .. versionadded:: 2.0.0

    interpolation : str, optional
        Deprecated name for the method keyword argument.

        .. deprecated:: 1.22.0

    Returns
    -------
    quantile : scalar or ndarray
        If `q` is a single probability and `axis=None`, then the result
        is a scalar. If multiple probability levels are given, first axis of
        the result corresponds to the quantiles. The other axes are
        the axes that remain after the reduction of `a`. If the input
        contains integers or floats smaller than ``float64``, the output
        data-type is ``float64``. Otherwise, the output data-type is the
        same as that of the input. If `out` is specified, that array is
        returned instead.

    See Also
    --------
    quantile
    nanmean, nanmedian
    nanmedian : equivalent to ``nanquantile(..., 0.5)``
    nanpercentile : same as nanquantile, but with q in the range [0, 100].

    Notes
    -----
    The behavior of `numpy.nanquantile` is the same as that of
    `numpy.quantile` (ignoring nan values).
    For more information, please see `numpy.quantile`.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[10., 7., 4.], [3., 2., 1.]])
    >>> a[0][1] = np.nan
    >>> a
    array([[10.,  nan,   4.],
          [ 3.,   2.,   1.]])
    >>> np.quantile(a, 0.5)
    np.float64(nan)
    >>> np.nanquantile(a, 0.5)
    3.0
    >>> np.nanquantile(a, 0.5, axis=0)
    array([6.5, 2. , 2.5])
    >>> np.nanquantile(a, 0.5, axis=1, keepdims=True)
    array([[7.],
           [2.]])
    >>> m = np.nanquantile(a, 0.5, axis=0)
    >>> out = np.zeros_like(m)
    >>> np.nanquantile(a, 0.5, axis=0, out=out)
    array([6.5, 2. , 2.5])
    >>> m
    array([6.5,  2. ,  2.5])
    >>> b = a.copy()
    >>> np.nanquantile(b, 0.5, axis=1, overwrite_input=True)
    array([7., 2.])
    >>> assert not np.all(a==b)

    References
    ----------
    .. [1] R. J. Hyndman and Y. Fan,
       "Sample quantiles in statistical packages,"
       The American Statistician, 50(4), pp. 361-365, 1996

    """

    if interpolation is not None:
        method = fnb._check_interpolation_as_method(
            method, interpolation, "nanquantile")

    a = np.asanyarray(a)
    if a.dtype.kind == "c":
        raise TypeError("a must be an array of real numbers")

    # Use dtype of array if possible (e.g., if q is a python int or float).
    if isinstance(q, (int, float)) and a.dtype.kind == "f":
        q = np.asanyarray(q, dtype=a.dtype)
    else:
        q = np.asanyarray(q)

    if not fnb._quantile_is_valid(q):
        raise ValueError("Quantiles must be in the range [0, 1]")

    if weights is not None:
        if method != "inverted_cdf":
            msg = ("Only method 'inverted_cdf' supports weights. "
                   f"Got: {method}.")
            raise ValueError(msg)
        if axis is not None:
            axis = _nx.normalize_axis_tuple(axis, a.ndim, argname="axis")
        weights = _weights_are_valid(weights=weights, a=a, axis=axis)
        if np.any(weights < 0):
            raise ValueError("Weights must be non-negative.")

    return _nanquantile_unchecked(
        a, q, axis, out, overwrite_input, method, keepdims, weights)


def _nanquantile_unchecked(
        a,
        q,
        axis=None,
        out=None,
        overwrite_input=False,
        method="linear",
        keepdims=np._NoValue,
        weights=None,
):
    """Assumes that q is in [0, 1], and is an ndarray"""
    # apply_along_axis in _nanpercentile doesn't handle empty arrays well,
    # so deal them upfront
    if a.size == 0:
        return np.nanmean(a, axis, out=out, keepdims=keepdims)
    return fnb._ureduce(a,
                        func=_nanquantile_ureduce_func,
                        q=q,
                        weights=weights,
                        keepdims=keepdims,
                        axis=axis,
                        out=out,
                        overwrite_input=overwrite_input,
                        method=method)


def _nanquantile_ureduce_func(
        a: np.array,
        q: np.array,
        weights: np.array,
        axis: int | None = None,
        out=None,
        overwrite_input: bool = False,
        method="linear",
):
    """
    Private function that doesn't support extended axis or keepdims.
    These methods are extended to this function using _ureduce
    See nanpercentile for parameter usage
    """
    if axis is None or a.ndim == 1:
        part = a.ravel()
        wgt = None if weights is None else weights.ravel()
        result = _nanquantile_1d(part, q, overwrite_input, method, weights=wgt)
    # Note that this code could try to fill in `out` right away
    elif weights is None:
        result = np.apply_along_axis(_nanquantile_1d, axis, a, q,
                                     overwrite_input, method, weights)
        # apply_along_axis fills in collapsed axis with results.
        # Move those axes to the beginning to match percentile's
        # convention.
        if q.ndim != 0:
            from_ax = [axis + i for i in range(q.ndim)]
            result = np.moveaxis(result, from_ax, list(range(q.ndim)))
    else:
        # We need to apply along axis over 2 arrays, a and weights.
        # move operation axes to end for simplicity:
        a = np.moveaxis(a, axis, -1)
        if weights is not None:
            weights = np.moveaxis(weights, axis, -1)
        if out is not None:
            result = out
        else:
            # weights are limited to `inverted_cdf` so the result dtype
            # is known to be identical to that of `a` here:
            result = np.empty_like(a, shape=q.shape + a.shape[:-1])

        for ii in np.ndindex(a.shape[:-1]):
            result[(...,) + ii] = _nanquantile_1d(
                    a[ii], q, weights=weights[ii],
                    overwrite_input=overwrite_input, method=method,
            )
        # This path dealt with `out` already...
        return result

    if out is not None:
        out[...] = result
    return result


def _nanquantile_1d(
    arr1d, q, overwrite_input=False, method="linear", weights=None,
):
    """
    Private function for rank 1 arrays. Compute quantile ignoring NaNs.
    See nanpercentile for parameter usage
    """
    # TODO: What to do when arr1d = [1, np.nan] and weights = [0, 1]?
    arr1d, weights, overwrite_input = _remove_nan_1d(arr1d,
        second_arr1d=weights, overwrite_input=overwrite_input)
    if arr1d.size == 0:
        # convert to scalar
        return np.full(q.shape, np.nan, dtype=arr1d.dtype)[()]

    return fnb._quantile_unchecked(
        arr1d,
        q,
        overwrite_input=overwrite_input,
        method=method,
        weights=weights,
    )


def _nanvar_dispatcher(a, axis=None, dtype=None, out=None, ddof=None,
                       keepdims=None, *, where=None, mean=None,
                       correction=None):
    return (a, out)


@array_function_dispatch(_nanvar_dispatcher)
def nanvar(a, axis=None, dtype=None, out=None, ddof=0, keepdims=np._NoValue,
           *, where=np._NoValue, mean=np._NoValue, correction=np._NoValue):
    """
    Compute the variance along the specified axis, while ignoring NaNs.

    Returns the variance of the array elements, a measure of the spread of
    a distribution.  The variance is computed for the flattened array by
    default, otherwise over the specified axis.

    For all-NaN slices or slices with zero degrees of freedom, NaN is
    returned and a `RuntimeWarning` is raised.

    Parameters
    ----------
    a : array_like
        Array containing numbers whose variance is desired.  If `a` is not an
        array, a conversion is attempted.
    axis : {int, tuple of int, None}, optional
        Axis or axes along which the variance is computed.  The default is to compute
        the variance of the flattened array.
    dtype : data-type, optional
        Type to use in computing the variance.  For arrays of integer type
        the default is `float64`; for arrays of float types it is the same as
        the array type.
    out : ndarray, optional
        Alternate output array in which to place the result.  It must have
        the same shape as the expected output, but the type is cast if
        necessary.
    ddof : {int, float}, optional
        "Delta Degrees of Freedom": the divisor used in the calculation is
        ``N - ddof``, where ``N`` represents the number of non-NaN
        elements. By default `ddof` is zero.
    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the original `a`.
    where : array_like of bool, optional
        Elements to include in the variance. See `~numpy.ufunc.reduce` for
        details.

        .. versionadded:: 1.22.0

    mean : array_like, optional
        Provide the mean to prevent its recalculation. The mean should have
        a shape as if it was calculated with ``keepdims=True``.
        The axis for the calculation of the mean should be the same as used in
        the call to this var function.

        .. versionadded:: 2.0.0

    correction : {int, float}, optional
        Array API compatible name for the ``ddof`` parameter. Only one of them
        can be provided at the same time.

        .. versionadded:: 2.0.0

    Returns
    -------
    variance : ndarray, see dtype parameter above
        If `out` is None, return a new array containing the variance,
        otherwise return a reference to the output array. If ddof is >= the
        number of non-NaN elements in a slice or the slice contains only
        NaNs, then the result for that slice is NaN.

    See Also
    --------
    std : Standard deviation
    mean : Average
    var : Variance while not ignoring NaNs
    nanstd, nanmean
    :ref:`ufuncs-output-type`

    Notes
    -----
    The variance is the average of the squared deviations from the mean,
    i.e.,  ``var = mean(abs(x - x.mean())**2)``.

    The mean is normally calculated as ``x.sum() / N``, where ``N = len(x)``.
    If, however, `ddof` is specified, the divisor ``N - ddof`` is used
    instead.  In standard statistical practice, ``ddof=1`` provides an
    unbiased estimator of the variance of a hypothetical infinite
    population.  ``ddof=0`` provides a maximum likelihood estimate of the
    variance for normally distributed variables.

    Note that for complex numbers, the absolute value is taken before
    squaring, so that the result is always real and nonnegative.

    For floating-point input, the variance is computed using the same
    precision the input has.  Depending on the input data, this can cause
    the results to be inaccurate, especially for `float32` (see example
    below).  Specifying a higher-accuracy accumulator using the ``dtype``
    keyword can alleviate this issue.

    For this function to work on sub-classes of ndarray, they must define
    `sum` with the kwarg `keepdims`

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[1, np.nan], [3, 4]])
    >>> np.nanvar(a)
    1.5555555555555554
    >>> np.nanvar(a, axis=0)
    array([1.,  0.])
    >>> np.nanvar(a, axis=1)
    array([0.,  0.25])  # may vary

    """
    arr, mask = _replace_nan(a, 0)
    if mask is None:
        return np.var(arr, axis=axis, dtype=dtype, out=out, ddof=ddof,
                      keepdims=keepdims, where=where, mean=mean,
                      correction=correction)

    if dtype is not None:
        dtype = np.dtype(dtype)
    if dtype is not None and not issubclass(dtype.type, np.inexact):
        raise TypeError("If a is inexact, then dtype must be inexact")
    if out is not None and not issubclass(out.dtype.type, np.inexact):
        raise TypeError("If a is inexact, then out must be inexact")

    if correction != np._NoValue:
        if ddof != 0:
            raise ValueError(
                "ddof and correction can't be provided simultaneously."
            )
        else:
            ddof = correction

    # Compute mean
    if type(arr) is np.matrix:
        _keepdims = np._NoValue
    else:
        _keepdims = True

    cnt = np.sum(~mask, axis=axis, dtype=np.intp, keepdims=_keepdims,
                     where=where)

    if mean is not np._NoValue:
        avg = mean
    else:
        # we need to special case matrix for reverse compatibility
        # in order for this to work, these sums need to be called with
        # keepdims=True, however matrix now raises an error in this case, but
        # the reason that it drops the keepdims kwarg is to force keepdims=True
        # so this used to work by serendipity.
        avg = np.sum(arr, axis=axis, dtype=dtype,
                     keepdims=_keepdims, where=where)
        avg = _divide_by_count(avg, cnt)

    # Compute squared deviation from mean.
    np.subtract(arr, avg, out=arr, casting='unsafe', where=where)
    arr = _copyto(arr, 0, mask)
    if issubclass(arr.dtype.type, np.complexfloating):
        sqr = np.multiply(arr, arr.conj(), out=arr, where=where).real
    else:
        sqr = np.multiply(arr, arr, out=arr, where=where)

    # Compute variance.
    var = np.sum(sqr, axis=axis, dtype=dtype, out=out, keepdims=keepdims,
                 where=where)

    # Precaution against reduced object arrays
    try:
        var_ndim = var.ndim
    except AttributeError:
        var_ndim = np.ndim(var)
    if var_ndim < cnt.ndim:
        # Subclasses of ndarray may ignore keepdims, so check here.
        cnt = cnt.squeeze(axis)
    dof = cnt - ddof
    var = _divide_by_count(var, dof)

    isbad = (dof <= 0)
    if np.any(isbad):
        warnings.warn("Degrees of freedom <= 0 for slice.", RuntimeWarning,
                      stacklevel=2)
        # NaN, inf, or negative numbers are all possible bad
        # values, so explicitly replace them with NaN.
        var = _copyto(var, np.nan, isbad)
    return var


def _nanstd_dispatcher(a, axis=None, dtype=None, out=None, ddof=None,
                       keepdims=None, *, where=None, mean=None,
                       correction=None):
    return (a, out)


@array_function_dispatch(_nanstd_dispatcher)
def nanstd(a, axis=None, dtype=None, out=None, ddof=0, keepdims=np._NoValue,
           *, where=np._NoValue, mean=np._NoValue, correction=np._NoValue):
    """
    Compute the standard deviation along the specified axis, while
    ignoring NaNs.

    Returns the standard deviation, a measure of the spread of a
    distribution, of the non-NaN array elements. The standard deviation is
    computed for the flattened array by default, otherwise over the
    specified axis.

    For all-NaN slices or slices with zero degrees of freedom, NaN is
    returned and a `RuntimeWarning` is raised.

    Parameters
    ----------
    a : array_like
        Calculate the standard deviation of the non-NaN values.
    axis : {int, tuple of int, None}, optional
        Axis or axes along which the standard deviation is computed. The default is
        to compute the standard deviation of the flattened array.
    dtype : dtype, optional
        Type to use in computing the standard deviation. For arrays of
        integer type the default is float64, for arrays of float types it
        is the same as the array type.
    out : ndarray, optional
        Alternative output array in which to place the result. It must have
        the same shape as the expected output but the type (of the
        calculated values) will be cast if necessary.
    ddof : {int, float}, optional
        Means Delta Degrees of Freedom.  The divisor used in calculations
        is ``N - ddof``, where ``N`` represents the number of non-NaN
        elements.  By default `ddof` is zero.

    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the original `a`.

        If this value is anything but the default it is passed through
        as-is to the relevant functions of the sub-classes.  If these
        functions do not have a `keepdims` kwarg, a RuntimeError will
        be raised.
    where : array_like of bool, optional
        Elements to include in the standard deviation.
        See `~numpy.ufunc.reduce` for details.

        .. versionadded:: 1.22.0

    mean : array_like, optional
        Provide the mean to prevent its recalculation. The mean should have
        a shape as if it was calculated with ``keepdims=True``.
        The axis for the calculation of the mean should be the same as used in
        the call to this std function.

        .. versionadded:: 2.0.0

    correction : {int, float}, optional
        Array API compatible name for the ``ddof`` parameter. Only one of them
        can be provided at the same time.

        .. versionadded:: 2.0.0

    Returns
    -------
    standard_deviation : ndarray, see dtype parameter above.
        If `out` is None, return a new array containing the standard
        deviation, otherwise return a reference to the output array. If
        ddof is >= the number of non-NaN elements in a slice or the slice
        contains only NaNs, then the result for that slice is NaN.

    See Also
    --------
    var, mean, std
    nanvar, nanmean
    :ref:`ufuncs-output-type`

    Notes
    -----
    The standard deviation is the square root of the average of the squared
    deviations from the mean: ``std = sqrt(mean(abs(x - x.mean())**2))``.

    The average squared deviation is normally calculated as
    ``x.sum() / N``, where ``N = len(x)``.  If, however, `ddof` is
    specified, the divisor ``N - ddof`` is used instead. In standard
    statistical practice, ``ddof=1`` provides an unbiased estimator of the
    variance of the infinite population. ``ddof=0`` provides a maximum
    likelihood estimate of the variance for normally distributed variables.
    The standard deviation computed in this function is the square root of
    the estimated variance, so even with ``ddof=1``, it will not be an
    unbiased estimate of the standard deviation per se.

    Note that, for complex numbers, `std` takes the absolute value before
    squaring, so that the result is always real and nonnegative.

    For floating-point input, the *std* is computed using the same
    precision the input has. Depending on the input data, this can cause
    the results to be inaccurate, especially for float32 (see example
    below).  Specifying a higher-accuracy accumulator using the `dtype`
    keyword can alleviate this issue.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[1, np.nan], [3, 4]])
    >>> np.nanstd(a)
    1.247219128924647
    >>> np.nanstd(a, axis=0)
    array([1., 0.])
    >>> np.nanstd(a, axis=1)
    array([0.,  0.5]) # may vary

    """
    var = nanvar(a, axis=axis, dtype=dtype, out=out, ddof=ddof,
                 keepdims=keepdims, where=where, mean=mean,
                 correction=correction)
    if isinstance(var, np.ndarray):
        std = np.sqrt(var, out=var)
    elif hasattr(var, 'dtype'):
        std = var.dtype.type(np.sqrt(var))
    else:
        std = np.sqrt(var)
    return std

# === NexusCore/openenv\Lib\site-packages\win32\lib\win32cryptcon.py ===
# Generated by h2py from WinCrypt.h
def GET_ALG_CLASS(x):
    return x & (7 << 13)


def GET_ALG_TYPE(x):
    return x & (15 << 9)


def GET_ALG_SID(x):
    return x & (511)


ALG_CLASS_ANY = 0
ALG_CLASS_SIGNATURE = 1 << 13
ALG_CLASS_MSG_ENCRYPT = 2 << 13
ALG_CLASS_DATA_ENCRYPT = 3 << 13
ALG_CLASS_HASH = 4 << 13
ALG_CLASS_KEY_EXCHANGE = 5 << 13
ALG_CLASS_ALL = 7 << 13
ALG_TYPE_ANY = 0
ALG_TYPE_DSS = 1 << 9
ALG_TYPE_RSA = 2 << 9
ALG_TYPE_BLOCK = 3 << 9
ALG_TYPE_STREAM = 4 << 9
ALG_TYPE_DH = 5 << 9
ALG_TYPE_SECURECHANNEL = 6 << 9
ALG_SID_ANY = 0
ALG_SID_RSA_ANY = 0
ALG_SID_RSA_PKCS = 1
ALG_SID_RSA_MSATWORK = 2
ALG_SID_RSA_ENTRUST = 3
ALG_SID_RSA_PGP = 4
ALG_SID_DSS_ANY = 0
ALG_SID_DSS_PKCS = 1
ALG_SID_DSS_DMS = 2
ALG_SID_DES = 1
ALG_SID_3DES = 3
ALG_SID_DESX = 4
ALG_SID_IDEA = 5
ALG_SID_CAST = 6
ALG_SID_SAFERSK64 = 7
ALG_SID_SAFERSK128 = 8
ALG_SID_3DES_112 = 9
ALG_SID_CYLINK_MEK = 12
ALG_SID_RC5 = 13
ALG_SID_AES_128 = 14
ALG_SID_AES_192 = 15
ALG_SID_AES_256 = 16
ALG_SID_AES = 17
ALG_SID_SKIPJACK = 10
ALG_SID_TEK = 11
CRYPT_MODE_CBCI = 6
CRYPT_MODE_CFBP = 7
CRYPT_MODE_OFBP = 8
CRYPT_MODE_CBCOFM = 9
CRYPT_MODE_CBCOFMI = 10
ALG_SID_RC2 = 2
ALG_SID_RC4 = 1
ALG_SID_SEAL = 2
ALG_SID_DH_SANDF = 1
ALG_SID_DH_EPHEM = 2
ALG_SID_AGREED_KEY_ANY = 3
ALG_SID_KEA = 4
ALG_SID_MD2 = 1
ALG_SID_MD4 = 2
ALG_SID_MD5 = 3
ALG_SID_SHA = 4
ALG_SID_SHA1 = 4
ALG_SID_MAC = 5
ALG_SID_RIPEMD = 6
ALG_SID_RIPEMD160 = 7
ALG_SID_SSL3SHAMD5 = 8
ALG_SID_HMAC = 9
ALG_SID_TLS1PRF = 10
ALG_SID_HASH_REPLACE_OWF = 11
ALG_SID_SHA_256 = 12
ALG_SID_SHA_384 = 13
ALG_SID_SHA_512 = 14
ALG_SID_SSL3_MASTER = 1
ALG_SID_SCHANNEL_MASTER_HASH = 2
ALG_SID_SCHANNEL_MAC_KEY = 3
ALG_SID_PCT1_MASTER = 4
ALG_SID_SSL2_MASTER = 5
ALG_SID_TLS1_MASTER = 6
ALG_SID_SCHANNEL_ENC_KEY = 7
ALG_SID_EXAMPLE = 80
CALG_MD2 = ALG_CLASS_HASH | ALG_TYPE_ANY | ALG_SID_MD2
CALG_MD4 = ALG_CLASS_HASH | ALG_TYPE_ANY | ALG_SID_MD4
CALG_MD5 = ALG_CLASS_HASH | ALG_TYPE_ANY | ALG_SID_MD5
CALG_SHA = ALG_CLASS_HASH | ALG_TYPE_ANY | ALG_SID_SHA
CALG_SHA1 = ALG_CLASS_HASH | ALG_TYPE_ANY | ALG_SID_SHA1
CALG_MAC = ALG_CLASS_HASH | ALG_TYPE_ANY | ALG_SID_MAC
CALG_RSA_SIGN = ALG_CLASS_SIGNATURE | ALG_TYPE_RSA | ALG_SID_RSA_ANY
CALG_DSS_SIGN = ALG_CLASS_SIGNATURE | ALG_TYPE_DSS | ALG_SID_DSS_ANY
CALG_NO_SIGN = ALG_CLASS_SIGNATURE | ALG_TYPE_ANY | ALG_SID_ANY
CALG_RSA_KEYX = ALG_CLASS_KEY_EXCHANGE | ALG_TYPE_RSA | ALG_SID_RSA_ANY
CALG_DES = ALG_CLASS_DATA_ENCRYPT | ALG_TYPE_BLOCK | ALG_SID_DES
CALG_3DES_112 = ALG_CLASS_DATA_ENCRYPT | ALG_TYPE_BLOCK | ALG_SID_3DES_112
CALG_3DES = ALG_CLASS_DATA_ENCRYPT | ALG_TYPE_BLOCK | ALG_SID_3DES
CALG_DESX = ALG_CLASS_DATA_ENCRYPT | ALG_TYPE_BLOCK | ALG_SID_DESX
CALG_RC2 = ALG_CLASS_DATA_ENCRYPT | ALG_TYPE_BLOCK | ALG_SID_RC2
CALG_RC4 = ALG_CLASS_DATA_ENCRYPT | ALG_TYPE_STREAM | ALG_SID_RC4
CALG_SEAL = ALG_CLASS_DATA_ENCRYPT | ALG_TYPE_STREAM | ALG_SID_SEAL
CALG_DH_SF = ALG_CLASS_KEY_EXCHANGE | ALG_TYPE_DH | ALG_SID_DH_SANDF
CALG_DH_EPHEM = ALG_CLASS_KEY_EXCHANGE | ALG_TYPE_DH | ALG_SID_DH_EPHEM
CALG_AGREEDKEY_ANY = ALG_CLASS_KEY_EXCHANGE | ALG_TYPE_DH | ALG_SID_AGREED_KEY_ANY
CALG_KEA_KEYX = ALG_CLASS_KEY_EXCHANGE | ALG_TYPE_DH | ALG_SID_KEA
CALG_HUGHES_MD5 = ALG_CLASS_KEY_EXCHANGE | ALG_TYPE_ANY | ALG_SID_MD5
CALG_SKIPJACK = ALG_CLASS_DATA_ENCRYPT | ALG_TYPE_BLOCK | ALG_SID_SKIPJACK
CALG_TEK = ALG_CLASS_DATA_ENCRYPT | ALG_TYPE_BLOCK | ALG_SID_TEK
CALG_CYLINK_MEK = ALG_CLASS_DATA_ENCRYPT | ALG_TYPE_BLOCK | ALG_SID_CYLINK_MEK
CALG_SSL3_SHAMD5 = ALG_CLASS_HASH | ALG_TYPE_ANY | ALG_SID_SSL3SHAMD5
CALG_SSL3_MASTER = ALG_CLASS_MSG_ENCRYPT | ALG_TYPE_SECURECHANNEL | ALG_SID_SSL3_MASTER
CALG_SCHANNEL_MASTER_HASH = (
    ALG_CLASS_MSG_ENCRYPT | ALG_TYPE_SECURECHANNEL | ALG_SID_SCHANNEL_MASTER_HASH
)
CALG_SCHANNEL_MAC_KEY = (
    ALG_CLASS_MSG_ENCRYPT | ALG_TYPE_SECURECHANNEL | ALG_SID_SCHANNEL_MAC_KEY
)
CALG_SCHANNEL_ENC_KEY = (
    ALG_CLASS_MSG_ENCRYPT | ALG_TYPE_SECURECHANNEL | ALG_SID_SCHANNEL_ENC_KEY
)
CALG_PCT1_MASTER = ALG_CLASS_MSG_ENCRYPT | ALG_TYPE_SECURECHANNEL | ALG_SID_PCT1_MASTER
CALG_SSL2_MASTER = ALG_CLASS_MSG_ENCRYPT | ALG_TYPE_SECURECHANNEL | ALG_SID_SSL2_MASTER
CALG_TLS1_MASTER = ALG_CLASS_MSG_ENCRYPT | ALG_TYPE_SECURECHANNEL | ALG_SID_TLS1_MASTER
CALG_RC5 = ALG_CLASS_DATA_ENCRYPT | ALG_TYPE_BLOCK | ALG_SID_RC5
CALG_HMAC = ALG_CLASS_HASH | ALG_TYPE_ANY | ALG_SID_HMAC
CALG_TLS1PRF = ALG_CLASS_HASH | ALG_TYPE_ANY | ALG_SID_TLS1PRF
CALG_HASH_REPLACE_OWF = ALG_CLASS_HASH | ALG_TYPE_ANY | ALG_SID_HASH_REPLACE_OWF
CALG_AES_128 = ALG_CLASS_DATA_ENCRYPT | ALG_TYPE_BLOCK | ALG_SID_AES_128
CALG_AES_192 = ALG_CLASS_DATA_ENCRYPT | ALG_TYPE_BLOCK | ALG_SID_AES_192
CALG_AES_256 = ALG_CLASS_DATA_ENCRYPT | ALG_TYPE_BLOCK | ALG_SID_AES_256
CALG_AES = ALG_CLASS_DATA_ENCRYPT | ALG_TYPE_BLOCK | ALG_SID_AES
CALG_SHA_256 = ALG_CLASS_HASH | ALG_TYPE_ANY | ALG_SID_SHA_256
CALG_SHA_384 = ALG_CLASS_HASH | ALG_TYPE_ANY | ALG_SID_SHA_384
CALG_SHA_512 = ALG_CLASS_HASH | ALG_TYPE_ANY | ALG_SID_SHA_512
CRYPT_VERIFYCONTEXT = -268435456
CRYPT_NEWKEYSET = 0x00000008
CRYPT_DELETEKEYSET = 0x00000010
CRYPT_MACHINE_KEYSET = 0x00000020
CRYPT_SILENT = 0x00000040
CRYPT_EXPORTABLE = 0x00000001
CRYPT_USER_PROTECTED = 0x00000002
CRYPT_CREATE_SALT = 0x00000004
CRYPT_UPDATE_KEY = 0x00000008
CRYPT_NO_SALT = 0x00000010
CRYPT_PREGEN = 0x00000040
CRYPT_RECIPIENT = 0x00000010
CRYPT_INITIATOR = 0x00000040
CRYPT_ONLINE = 0x00000080
CRYPT_SF = 0x00000100
CRYPT_CREATE_IV = 0x00000200
CRYPT_KEK = 0x00000400
CRYPT_DATA_KEY = 0x00000800
CRYPT_VOLATILE = 0x00001000
CRYPT_SGCKEY = 0x00002000
CRYPT_ARCHIVABLE = 0x00004000
RSA1024BIT_KEY = 0x04000000
CRYPT_SERVER = 0x00000400
KEY_LENGTH_MASK = -65536
CRYPT_Y_ONLY = 0x00000001
CRYPT_SSL2_FALLBACK = 0x00000002
CRYPT_DESTROYKEY = 0x00000004
CRYPT_OAEP = 0x00000040
CRYPT_BLOB_VER3 = 0x00000080
CRYPT_IPSEC_HMAC_KEY = 0x00000100
CRYPT_DECRYPT_RSA_NO_PADDING_CHECK = 0x00000020
CRYPT_SECRETDIGEST = 0x00000001
CRYPT_OWF_REPL_LM_HASH = 0x00000001
CRYPT_LITTLE_ENDIAN = 0x00000001
CRYPT_NOHASHOID = 0x00000001
CRYPT_TYPE2_FORMAT = 0x00000002
CRYPT_X931_FORMAT = 0x00000004
CRYPT_MACHINE_DEFAULT = 0x00000001
CRYPT_USER_DEFAULT = 0x00000002
CRYPT_DELETE_DEFAULT = 0x00000004
SIMPLEBLOB = 0x1
PUBLICKEYBLOB = 0x6
PRIVATEKEYBLOB = 0x7
PLAINTEXTKEYBLOB = 0x8
OPAQUEKEYBLOB = 0x9
PUBLICKEYBLOBEX = 0xA
SYMMETRICWRAPKEYBLOB = 0xB
AT_KEYEXCHANGE = 1
AT_SIGNATURE = 2
CRYPT_USERDATA = 1
KP_IV = 1
KP_SALT = 2
KP_PADDING = 3
KP_MODE = 4
KP_MODE_BITS = 5
KP_PERMISSIONS = 6
KP_ALGID = 7
KP_BLOCKLEN = 8
KP_KEYLEN = 9
KP_SALT_EX = 10
KP_P = 11
KP_G = 12
KP_Q = 13
KP_X = 14
KP_Y = 15
KP_RA = 16
KP_RB = 17
KP_INFO = 18
KP_EFFECTIVE_KEYLEN = 19
KP_SCHANNEL_ALG = 20
KP_CLIENT_RANDOM = 21
KP_SERVER_RANDOM = 22
KP_RP = 23
KP_PRECOMP_MD5 = 24
KP_PRECOMP_SHA = 25
KP_CERTIFICATE = 26
KP_CLEAR_KEY = 27
KP_PUB_EX_LEN = 28
KP_PUB_EX_VAL = 29
KP_KEYVAL = 30
KP_ADMIN_PIN = 31
KP_KEYEXCHANGE_PIN = 32
KP_SIGNATURE_PIN = 33
KP_PREHASH = 34
KP_ROUNDS = 35
KP_OAEP_PARAMS = 36
KP_CMS_KEY_INFO = 37
KP_CMS_DH_KEY_INFO = 38
KP_PUB_PARAMS = 39
KP_VERIFY_PARAMS = 40
KP_HIGHEST_VERSION = 41
KP_GET_USE_COUNT = 42
PKCS5_PADDING = 1
RANDOM_PADDING = 2
ZERO_PADDING = 3
CRYPT_MODE_CBC = 1
CRYPT_MODE_ECB = 2
CRYPT_MODE_OFB = 3
CRYPT_MODE_CFB = 4
CRYPT_MODE_CTS = 5
CRYPT_ENCRYPT = 0x0001
CRYPT_DECRYPT = 0x0002
CRYPT_EXPORT = 0x0004
CRYPT_READ = 0x0008
CRYPT_WRITE = 0x0010
CRYPT_MAC = 0x0020
CRYPT_EXPORT_KEY = 0x0040
CRYPT_IMPORT_KEY = 0x0080
CRYPT_ARCHIVE = 0x0100
HP_ALGID = 0x0001
HP_HASHVAL = 0x0002
HP_HASHSIZE = 0x0004
HP_HMAC_INFO = 0x0005
HP_TLS1PRF_LABEL = 0x0006
HP_TLS1PRF_SEED = 0x0007

CRYPT_FAILED = 0
CRYPT_SUCCEED = 1


def RCRYPT_SUCCEEDED(rt):
    return (rt) == CRYPT_SUCCEED


def RCRYPT_FAILED(rt):
    return (rt) == CRYPT_FAILED


PP_ENUMALGS = 1
PP_ENUMCONTAINERS = 2
PP_IMPTYPE = 3
PP_NAME = 4
PP_VERSION = 5
PP_CONTAINER = 6
PP_CHANGE_PASSWORD = 7
PP_KEYSET_SEC_DESCR = 8
PP_CERTCHAIN = 9
PP_KEY_TYPE_SUBTYPE = 10
PP_PROVTYPE = 16
PP_KEYSTORAGE = 17
PP_APPLI_CERT = 18
PP_SYM_KEYSIZE = 19
PP_SESSION_KEYSIZE = 20
PP_UI_PROMPT = 21
PP_ENUMALGS_EX = 22
PP_ENUMMANDROOTS = 25
PP_ENUMELECTROOTS = 26
PP_KEYSET_TYPE = 27
PP_ADMIN_PIN = 31
PP_KEYEXCHANGE_PIN = 32
PP_SIGNATURE_PIN = 33
PP_SIG_KEYSIZE_INC = 34
PP_KEYX_KEYSIZE_INC = 35
PP_UNIQUE_CONTAINER = 36
PP_SGC_INFO = 37
PP_USE_HARDWARE_RNG = 38
PP_KEYSPEC = 39
PP_ENUMEX_SIGNING_PROT = 40
PP_CRYPT_COUNT_KEY_USE = 41
CRYPT_FIRST = 1
CRYPT_NEXT = 2
CRYPT_SGC_ENUM = 4
CRYPT_IMPL_HARDWARE = 1
CRYPT_IMPL_SOFTWARE = 2
CRYPT_IMPL_MIXED = 3
CRYPT_IMPL_UNKNOWN = 4
CRYPT_IMPL_REMOVABLE = 8
CRYPT_SEC_DESCR = 0x00000001
CRYPT_PSTORE = 0x00000002
CRYPT_UI_PROMPT = 0x00000004
CRYPT_FLAG_PCT1 = 0x0001
CRYPT_FLAG_SSL2 = 0x0002
CRYPT_FLAG_SSL3 = 0x0004
CRYPT_FLAG_TLS1 = 0x0008
CRYPT_FLAG_IPSEC = 0x0010
CRYPT_FLAG_SIGNING = 0x0020
CRYPT_SGC = 0x0001
CRYPT_FASTSGC = 0x0002
PP_CLIENT_HWND = 1
PP_CONTEXT_INFO = 11
PP_KEYEXCHANGE_KEYSIZE = 12
PP_SIGNATURE_KEYSIZE = 13
PP_KEYEXCHANGE_ALG = 14
PP_SIGNATURE_ALG = 15
PP_DELETEKEY = 24
PROV_RSA_FULL = 1
PROV_RSA_SIG = 2
PROV_DSS = 3
PROV_FORTEZZA = 4
PROV_MS_EXCHANGE = 5
PROV_SSL = 6
PROV_RSA_SCHANNEL = 12
PROV_DSS_DH = 13
PROV_EC_ECDSA_SIG = 14
PROV_EC_ECNRA_SIG = 15
PROV_EC_ECDSA_FULL = 16
PROV_EC_ECNRA_FULL = 17
PROV_DH_SCHANNEL = 18
PROV_SPYRUS_LYNKS = 20
PROV_RNG = 21
PROV_INTEL_SEC = 22
PROV_REPLACE_OWF = 23
PROV_RSA_AES = 24
MS_DEF_PROV_A = "Microsoft Base Cryptographic Provider v1.0"
MS_DEF_PROV = MS_DEF_PROV_A
MS_ENHANCED_PROV_A = "Microsoft Enhanced Cryptographic Provider v1.0"
MS_ENHANCED_PROV = MS_ENHANCED_PROV_A
MS_STRONG_PROV_A = "Microsoft Strong Cryptographic Provider"
MS_STRONG_PROV = MS_STRONG_PROV_A
MS_DEF_RSA_SIG_PROV_A = "Microsoft RSA Signature Cryptographic Provider"
MS_DEF_RSA_SIG_PROV = MS_DEF_RSA_SIG_PROV_A
MS_DEF_RSA_SCHANNEL_PROV_A = "Microsoft RSA SChannel Cryptographic Provider"
MS_DEF_RSA_SCHANNEL_PROV = MS_DEF_RSA_SCHANNEL_PROV_A
MS_DEF_DSS_PROV_A = "Microsoft Base DSS Cryptographic Provider"
MS_DEF_DSS_PROV = MS_DEF_DSS_PROV_A
MS_DEF_DSS_DH_PROV_A = "Microsoft Base DSS and Diffie-Hellman Cryptographic Provider"
MS_DEF_DSS_DH_PROV = MS_DEF_DSS_DH_PROV_A
MS_ENH_DSS_DH_PROV_A = (
    "Microsoft Enhanced DSS and Diffie-Hellman Cryptographic Provider"
)
MS_ENH_DSS_DH_PROV = MS_ENH_DSS_DH_PROV_A
MS_DEF_DH_SCHANNEL_PROV_A = "Microsoft DH SChannel Cryptographic Provider"
MS_DEF_DH_SCHANNEL_PROV = MS_DEF_DH_SCHANNEL_PROV_A
MS_SCARD_PROV_A = "Microsoft Base Smart Card Crypto Provider"
MS_SCARD_PROV = MS_SCARD_PROV_A
MS_ENH_RSA_AES_PROV_A = "Microsoft Enhanced RSA and AES Cryptographic Provider"
MS_ENH_RSA_AES_PROV = MS_ENH_RSA_AES_PROV_A
MAXUIDLEN = 64
EXPO_OFFLOAD_REG_VALUE = "ExpoOffload"
EXPO_OFFLOAD_FUNC_NAME = "OffloadModExpo"
szKEY_CRYPTOAPI_PRIVATE_KEY_OPTIONS = "Software\\Policies\\Microsoft\\Cryptography"
szFORCE_KEY_PROTECTION = "ForceKeyProtection"
dwFORCE_KEY_PROTECTION_DISABLED = 0x0
dwFORCE_KEY_PROTECTION_USER_SELECT = 0x1
dwFORCE_KEY_PROTECTION_HIGH = 0x2
szKEY_CACHE_ENABLED = "CachePrivateKeys"
szKEY_CACHE_SECONDS = "PrivateKeyLifetimeSeconds"
CUR_BLOB_VERSION = 2
SCHANNEL_MAC_KEY = 0x00000000
SCHANNEL_ENC_KEY = 0x00000001
INTERNATIONAL_USAGE = 0x00000001
szOID_RSA = "1.2.840.113549"
szOID_PKCS = "1.2.840.113549.1"
szOID_RSA_HASH = "1.2.840.113549.2"
szOID_RSA_ENCRYPT = "1.2.840.113549.3"
szOID_PKCS_1 = "1.2.840.113549.1.1"
szOID_PKCS_2 = "1.2.840.113549.1.2"
szOID_PKCS_3 = "1.2.840.113549.1.3"
szOID_PKCS_4 = "1.2.840.113549.1.4"
szOID_PKCS_5 = "1.2.840.113549.1.5"
szOID_PKCS_6 = "1.2.840.113549.1.6"
szOID_PKCS_7 = "1.2.840.113549.1.7"
szOID_PKCS_8 = "1.2.840.113549.1.8"
szOID_PKCS_9 = "1.2.840.113549.1.9"
szOID_PKCS_10 = "1.2.840.113549.1.10"
szOID_PKCS_12 = "1.2.840.113549.1.12"
szOID_RSA_RSA = "1.2.840.113549.1.1.1"
szOID_RSA_MD2RSA = "1.2.840.113549.1.1.2"
szOID_RSA_MD4RSA = "1.2.840.113549.1.1.3"
szOID_RSA_MD5RSA = "1.2.840.113549.1.1.4"
szOID_RSA_SHA1RSA = "1.2.840.113549.1.1.5"
szOID_RSA_SETOAEP_RSA = "1.2.840.113549.1.1.6"
szOID_RSA_DH = "1.2.840.113549.1.3.1"
szOID_RSA_data = "1.2.840.113549.1.7.1"
szOID_RSA_signedData = "1.2.840.113549.1.7.2"
szOID_RSA_envelopedData = "1.2.840.113549.1.7.3"
szOID_RSA_signEnvData = "1.2.840.113549.1.7.4"
szOID_RSA_digestedData = "1.2.840.113549.1.7.5"
szOID_RSA_hashedData = "1.2.840.113549.1.7.5"
szOID_RSA_encryptedData = "1.2.840.113549.1.7.6"
szOID_RSA_emailAddr = "1.2.840.113549.1.9.1"
szOID_RSA_unstructName = "1.2.840.113549.1.9.2"
szOID_RSA_contentType = "1.2.840.113549.1.9.3"
szOID_RSA_messageDigest = "1.2.840.113549.1.9.4"
szOID_RSA_signingTime = "1.2.840.113549.1.9.5"
szOID_RSA_counterSign = "1.2.840.113549.1.9.6"
szOID_RSA_challengePwd = "1.2.840.113549.1.9.7"
szOID_RSA_unstructAddr = "1.2.840.113549.1.9.8"
szOID_RSA_extCertAttrs = "1.2.840.113549.1.9.9"
szOID_RSA_certExtensions = "1.2.840.113549.1.9.14"
szOID_RSA_SMIMECapabilities = "1.2.840.113549.1.9.15"
szOID_RSA_preferSignedData = "1.2.840.113549.1.9.15.1"
szOID_RSA_SMIMEalg = "1.2.840.113549.1.9.16.3"
szOID_RSA_SMIMEalgESDH = "1.2.840.113549.1.9.16.3.5"
szOID_RSA_SMIMEalgCMS3DESwrap = "1.2.840.113549.1.9.16.3.6"
szOID_RSA_SMIMEalgCMSRC2wrap = "1.2.840.113549.1.9.16.3.7"
szOID_RSA_MD2 = "1.2.840.113549.2.2"
szOID_RSA_MD4 = "1.2.840.113549.2.4"
szOID_RSA_MD5 = "1.2.840.113549.2.5"
szOID_RSA_RC2CBC = "1.2.840.113549.3.2"
szOID_RSA_RC4 = "1.2.840.113549.3.4"
szOID_RSA_DES_EDE3_CBC = "1.2.840.113549.3.7"
szOID_RSA_RC5_CBCPad = "1.2.840.113549.3.9"
szOID_ANSI_X942 = "1.2.840.10046"
szOID_ANSI_X942_DH = "1.2.840.10046.2.1"
szOID_X957 = "1.2.840.10040"
szOID_X957_DSA = "1.2.840.10040.4.1"
szOID_X957_SHA1DSA = "1.2.840.10040.4.3"
szOID_DS = "2.5"
szOID_DSALG = "2.5.8"
szOID_DSALG_CRPT = "2.5.8.1"
szOID_DSALG_HASH = "2.5.8.2"
szOID_DSALG_SIGN = "2.5.8.3"
szOID_DSALG_RSA = "2.5.8.1.1"
szOID_OIW = "1.3.14"
szOID_OIWSEC = "1.3.14.3.2"
szOID_OIWSEC_md4RSA = "1.3.14.3.2.2"
szOID_OIWSEC_md5RSA = "1.3.14.3.2.3"
szOID_OIWSEC_md4RSA2 = "1.3.14.3.2.4"
szOID_OIWSEC_desECB = "1.3.14.3.2.6"
szOID_OIWSEC_desCBC = "1.3.14.3.2.7"
szOID_OIWSEC_desOFB = "1.3.14.3.2.8"
szOID_OIWSEC_desCFB = "1.3.14.3.2.9"
szOID_OIWSEC_desMAC = "1.3.14.3.2.10"
szOID_OIWSEC_rsaSign = "1.3.14.3.2.11"
szOID_OIWSEC_dsa = "1.3.14.3.2.12"
szOID_OIWSEC_shaDSA = "1.3.14.3.2.13"
szOID_OIWSEC_mdc2RSA = "1.3.14.3.2.14"
szOID_OIWSEC_shaRSA = "1.3.14.3.2.15"
szOID_OIWSEC_dhCommMod = "1.3.14.3.2.16"
szOID_OIWSEC_desEDE = "1.3.14.3.2.17"
szOID_OIWSEC_sha = "1.3.14.3.2.18"
szOID_OIWSEC_mdc2 = "1.3.14.3.2.19"
szOID_OIWSEC_dsaComm = "1.3.14.3.2.20"
szOID_OIWSEC_dsaCommSHA = "1.3.14.3.2.21"
szOID_OIWSEC_rsaXchg = "1.3.14.3.2.22"
szOID_OIWSEC_keyHashSeal = "1.3.14.3.2.23"
szOID_OIWSEC_md2RSASign = "1.3.14.3.2.24"
szOID_OIWSEC_md5RSASign = "1.3.14.3.2.25"
szOID_OIWSEC_sha1 = "1.3.14.3.2.26"
szOID_OIWSEC_dsaSHA1 = "1.3.14.3.2.27"
szOID_OIWSEC_dsaCommSHA1 = "1.3.14.3.2.28"
szOID_OIWSEC_sha1RSASign = "1.3.14.3.2.29"
szOID_OIWDIR = "1.3.14.7.2"
szOID_OIWDIR_CRPT = "1.3.14.7.2.1"
szOID_OIWDIR_HASH = "1.3.14.7.2.2"
szOID_OIWDIR_SIGN = "1.3.14.7.2.3"
szOID_OIWDIR_md2 = "1.3.14.7.2.2.1"
szOID_OIWDIR_md2RSA = "1.3.14.7.2.3.1"
szOID_INFOSEC = "2.16.840.1.101.2.1"
szOID_INFOSEC_sdnsSignature = "2.16.840.1.101.2.1.1.1"
szOID_INFOSEC_mosaicSignature = "2.16.840.1.101.2.1.1.2"
szOID_INFOSEC_sdnsConfidentiality = "2.16.840.1.101.2.1.1.3"
szOID_INFOSEC_mosaicConfidentiality = "2.16.840.1.101.2.1.1.4"
szOID_INFOSEC_sdnsIntegrity = "2.16.840.1.101.2.1.1.5"
szOID_INFOSEC_mosaicIntegrity = "2.16.840.1.101.2.1.1.6"
szOID_INFOSEC_sdnsTokenProtection = "2.16.840.1.101.2.1.1.7"
szOID_INFOSEC_mosaicTokenProtection = "2.16.840.1.101.2.1.1.8"
szOID_INFOSEC_sdnsKeyManagement = "2.16.840.1.101.2.1.1.9"
szOID_INFOSEC_mosaicKeyManagement = "2.16.840.1.101.2.1.1.10"
szOID_INFOSEC_sdnsKMandSig = "2.16.840.1.101.2.1.1.11"
szOID_INFOSEC_mosaicKMandSig = "2.16.840.1.101.2.1.1.12"
szOID_INFOSEC_SuiteASignature = "2.16.840.1.101.2.1.1.13"
szOID_INFOSEC_SuiteAConfidentiality = "2.16.840.1.101.2.1.1.14"
szOID_INFOSEC_SuiteAIntegrity = "2.16.840.1.101.2.1.1.15"
szOID_INFOSEC_SuiteATokenProtection = "2.16.840.1.101.2.1.1.16"
szOID_INFOSEC_SuiteAKeyManagement = "2.16.840.1.101.2.1.1.17"
szOID_INFOSEC_SuiteAKMandSig = "2.16.840.1.101.2.1.1.18"
szOID_INFOSEC_mosaicUpdatedSig = "2.16.840.1.101.2.1.1.19"
szOID_INFOSEC_mosaicKMandUpdSig = "2.16.840.1.101.2.1.1.20"
szOID_INFOSEC_mosaicUpdatedInteg = "2.16.840.1.101.2.1.1.21"
szOID_COMMON_NAME = "2.5.4.3"
szOID_SUR_NAME = "2.5.4.4"
szOID_DEVICE_SERIAL_NUMBER = "2.5.4.5"
szOID_COUNTRY_NAME = "2.5.4.6"
szOID_LOCALITY_NAME = "2.5.4.7"
szOID_STATE_OR_PROVINCE_NAME = "2.5.4.8"
szOID_STREET_ADDRESS = "2.5.4.9"
szOID_ORGANIZATION_NAME = "2.5.4.10"
szOID_ORGANIZATIONAL_UNIT_NAME = "2.5.4.11"
szOID_TITLE = "2.5.4.12"
szOID_DESCRIPTION = "2.5.4.13"
szOID_SEARCH_GUIDE = "2.5.4.14"
szOID_BUSINESS_CATEGORY = "2.5.4.15"
szOID_POSTAL_ADDRESS = "2.5.4.16"
szOID_POSTAL_CODE = "2.5.4.17"
szOID_POST_OFFICE_BOX = "2.5.4.18"
szOID_PHYSICAL_DELIVERY_OFFICE_NAME = "2.5.4.19"
szOID_TELEPHONE_NUMBER = "2.5.4.20"
szOID_TELEX_NUMBER = "2.5.4.21"
szOID_TELETEXT_TERMINAL_IDENTIFIER = "2.5.4.22"
szOID_FACSIMILE_TELEPHONE_NUMBER = "2.5.4.23"
szOID_X21_ADDRESS = "2.5.4.24"
szOID_INTERNATIONAL_ISDN_NUMBER = "2.5.4.25"
szOID_REGISTERED_ADDRESS = "2.5.4.26"
szOID_DESTINATION_INDICATOR = "2.5.4.27"
szOID_PREFERRED_DELIVERY_METHOD = "2.5.4.28"
szOID_PRESENTATION_ADDRESS = "2.5.4.29"
szOID_SUPPORTED_APPLICATION_CONTEXT = "2.5.4.30"
szOID_MEMBER = "2.5.4.31"
szOID_OWNER = "2.5.4.32"
szOID_ROLE_OCCUPANT = "2.5.4.33"
szOID_SEE_ALSO = "2.5.4.34"
szOID_USER_PASSWORD = "2.5.4.35"
szOID_USER_CERTIFICATE = "2.5.4.36"
szOID_CA_CERTIFICATE = "2.5.4.37"
szOID_AUTHORITY_REVOCATION_LIST = "2.5.4.38"
szOID_CERTIFICATE_REVOCATION_LIST = "2.5.4.39"
szOID_CROSS_CERTIFICATE_PAIR = "2.5.4.40"
szOID_GIVEN_NAME = "2.5.4.42"
szOID_INITIALS = "2.5.4.43"
szOID_DN_QUALIFIER = "2.5.4.46"
szOID_DOMAIN_COMPONENT = "0.9.2342.19200300.100.1.25"
szOID_PKCS_12_FRIENDLY_NAME_ATTR = "1.2.840.113549.1.9.20"
szOID_PKCS_12_LOCAL_KEY_ID = "1.2.840.113549.1.9.21"
szOID_PKCS_12_KEY_PROVIDER_NAME_ATTR = "1.3.6.1.4.1.311.17.1"
szOID_LOCAL_MACHINE_KEYSET = "1.3.6.1.4.1.311.17.2"
szOID_KEYID_RDN = "1.3.6.1.4.1.311.10.7.1"
CERT_RDN_ANY_TYPE = 0
CERT_RDN_ENCODED_BLOB = 1
CERT_RDN_OCTET_STRING = 2
CERT_RDN_NUMERIC_STRING = 3
CERT_RDN_PRINTABLE_STRING = 4
CERT_RDN_TELETEX_STRING = 5
CERT_RDN_T61_STRING = 5
CERT_RDN_VIDEOTEX_STRING = 6
CERT_RDN_IA5_STRING = 7
CERT_RDN_GRAPHIC_STRING = 8
CERT_RDN_VISIBLE_STRING = 9
CERT_RDN_ISO646_STRING = 9
CERT_RDN_GENERAL_STRING = 10
CERT_RDN_UNIVERSAL_STRING = 11
CERT_RDN_INT4_STRING = 11
CERT_RDN_BMP_STRING = 12
CERT_RDN_UNICODE_STRING = 12
CERT_RDN_UTF8_STRING = 13
CERT_RDN_TYPE_MASK = 0x000000FF
CERT_RDN_FLAGS_MASK = -16777216
CERT_RDN_ENABLE_T61_UNICODE_FLAG = -2147483648
CERT_RDN_ENABLE_UTF8_UNICODE_FLAG = 0x20000000
CERT_RDN_DISABLE_CHECK_TYPE_FLAG = 0x40000000
CERT_RDN_DISABLE_IE4_UTF8_FLAG = 0x01000000
CERT_RSA_PUBLIC_KEY_OBJID = szOID_RSA_RSA
CERT_DEFAULT_OID_PUBLIC_KEY_SIGN = szOID_RSA_RSA
CERT_DEFAULT_OID_PUBLIC_KEY_XCHG = szOID_RSA_RSA
CERT_V1 = 0
CERT_V2 = 1
CERT_V3 = 2
CERT_INFO_VERSION_FLAG = 1
CERT_INFO_SERIAL_NUMBER_FLAG = 2
CERT_INFO_SIGNATURE_ALGORITHM_FLAG = 3
CERT_INFO_ISSUER_FLAG = 4
CERT_INFO_NOT_BEFORE_FLAG = 5
CERT_INFO_NOT_AFTER_FLAG = 6
CERT_INFO_SUBJECT_FLAG = 7
CERT_INFO_SUBJECT_PUBLIC_KEY_INFO_FLAG = 8
CERT_INFO_ISSUER_UNIQUE_ID_FLAG = 9
CERT_INFO_SUBJECT_UNIQUE_ID_FLAG = 10
CERT_INFO_EXTENSION_FLAG = 11
CRL_V1 = 0
CRL_V2 = 1
CERT_REQUEST_V1 = 0
CERT_KEYGEN_REQUEST_V1 = 0
CTL_V1 = 0
CERT_ENCODING_TYPE_MASK = 0x0000FFFF
CMSG_ENCODING_TYPE_MASK = -65536


def GET_CERT_ENCODING_TYPE(X):
    return X & CERT_ENCODING_TYPE_MASK


def GET_CMSG_ENCODING_TYPE(X):
    return X & CMSG_ENCODING_TYPE_MASK


CRYPT_ASN_ENCODING = 0x00000001
CRYPT_NDR_ENCODING = 0x00000002
X509_ASN_ENCODING = 0x00000001
X509_NDR_ENCODING = 0x00000002
PKCS_7_ASN_ENCODING = 0x00010000
PKCS_7_NDR_ENCODING = 0x00020000
CRYPT_FORMAT_STR_MULTI_LINE = 0x0001
CRYPT_FORMAT_STR_NO_HEX = 0x0010
CRYPT_FORMAT_SIMPLE = 0x0001
CRYPT_FORMAT_X509 = 0x0002
CRYPT_FORMAT_OID = 0x0004
CRYPT_FORMAT_RDN_SEMICOLON = 0x0100
CRYPT_FORMAT_RDN_CRLF = 0x0200
CRYPT_FORMAT_RDN_UNQUOTE = 0x0400
CRYPT_FORMAT_RDN_REVERSE = 0x0800
CRYPT_FORMAT_COMMA = 0x1000
CRYPT_FORMAT_SEMICOLON = CRYPT_FORMAT_RDN_SEMICOLON
CRYPT_FORMAT_CRLF = CRYPT_FORMAT_RDN_CRLF
CRYPT_ENCODE_NO_SIGNATURE_BYTE_REVERSAL_FLAG = 0x8
CRYPT_ENCODE_ALLOC_FLAG = 0x8000
CRYPT_UNICODE_NAME_ENCODE_ENABLE_T61_UNICODE_FLAG = CERT_RDN_ENABLE_T61_UNICODE_FLAG
CRYPT_UNICODE_NAME_ENCODE_ENABLE_UTF8_UNICODE_FLAG = CERT_RDN_ENABLE_UTF8_UNICODE_FLAG
CRYPT_UNICODE_NAME_ENCODE_DISABLE_CHECK_TYPE_FLAG = CERT_RDN_DISABLE_CHECK_TYPE_FLAG
CRYPT_SORTED_CTL_ENCODE_HASHED_SUBJECT_IDENTIFIER_FLAG = 0x10000
CRYPT_DECODE_NOCOPY_FLAG = 0x1
CRYPT_DECODE_TO_BE_SIGNED_FLAG = 0x2
CRYPT_DECODE_SHARE_OID_STRING_FLAG = 0x4
CRYPT_DECODE_NO_SIGNATURE_BYTE_REVERSAL_FLAG = 0x8
CRYPT_DECODE_ALLOC_FLAG = 0x8000
CRYPT_UNICODE_NAME_DECODE_DISABLE_IE4_UTF8_FLAG = CERT_RDN_DISABLE_IE4_UTF8_FLAG

CRYPT_ENCODE_DECODE_NONE = 0
X509_CERT = 1
X509_CERT_TO_BE_SIGNED = 2
X509_CERT_CRL_TO_BE_SIGNED = 3
X509_CERT_REQUEST_TO_BE_SIGNED = 4
X509_EXTENSIONS = 5
X509_NAME_VALUE = 6
X509_NAME = 7
X509_PUBLIC_KEY_INFO = 8
X509_AUTHORITY_KEY_ID = 9
X509_KEY_ATTRIBUTES = 10
X509_KEY_USAGE_RESTRICTION = 11
X509_ALTERNATE_NAME = 12
X509_BASIC_CONSTRAINTS = 13
X509_KEY_USAGE = 14
X509_BASIC_CONSTRAINTS2 = 15
X509_CERT_POLICIES = 16
PKCS_UTC_TIME = 17
PKCS_TIME_REQUEST = 18
RSA_CSP_PUBLICKEYBLOB = 19
X509_UNICODE_NAME = 20
X509_KEYGEN_REQUEST_TO_BE_SIGNED = 21
PKCS_ATTRIBUTE = 22
PKCS_CONTENT_INFO_SEQUENCE_OF_ANY = 23
X509_UNICODE_NAME_VALUE = 24
X509_ANY_STRING = X509_NAME_VALUE
X509_UNICODE_ANY_STRING = X509_UNICODE_NAME_VALUE
X509_OCTET_STRING = 25
X509_BITS = 26
X509_INTEGER = 27
X509_MULTI_BYTE_INTEGER = 28
X509_ENUMERATED = 29
X509_CHOICE_OF_TIME = 30
X509_AUTHORITY_KEY_ID2 = 31
X509_AUTHORITY_INFO_ACCESS = 32
X509_SUBJECT_INFO_ACCESS = X509_AUTHORITY_INFO_ACCESS
X509_CRL_REASON_CODE = X509_ENUMERATED
PKCS_CONTENT_INFO = 33
X509_SEQUENCE_OF_ANY = 34
X509_CRL_DIST_POINTS = 35
X509_ENHANCED_KEY_USAGE = 36
PKCS_CTL = 37
X509_MULTI_BYTE_UINT = 38
X509_DSS_PUBLICKEY = X509_MULTI_BYTE_UINT
X509_DSS_PARAMETERS = 39
X509_DSS_SIGNATURE = 40
PKCS_RC2_CBC_PARAMETERS = 41
PKCS_SMIME_CAPABILITIES = 42
X509_QC_STATEMENTS_EXT = 42
PKCS_RSA_PRIVATE_KEY = 43
PKCS_PRIVATE_KEY_INFO = 44
PKCS_ENCRYPTED_PRIVATE_KEY_INFO = 45
X509_PKIX_POLICY_QUALIFIER_USERNOTICE = 46
X509_DH_PUBLICKEY = X509_MULTI_BYTE_UINT
X509_DH_PARAMETERS = 47
PKCS_ATTRIBUTES = 48
PKCS_SORTED_CTL = 49
X509_ECC_SIGNATURE = 47
X942_DH_PARAMETERS = 50
X509_BITS_WITHOUT_TRAILING_ZEROES = 51
X942_OTHER_INFO = 52
X509_CERT_PAIR = 53
X509_ISSUING_DIST_POINT = 54
X509_NAME_CONSTRAINTS = 55
X509_POLICY_MAPPINGS = 56
X509_POLICY_CONSTRAINTS = 57
X509_CROSS_CERT_DIST_POINTS = 58
CMC_DATA = 59
CMC_RESPONSE = 60
CMC_STATUS = 61
CMC_ADD_EXTENSIONS = 62
CMC_ADD_ATTRIBUTES = 63
X509_CERTIFICATE_TEMPLATE = 64
OCSP_SIGNED_REQUEST = 65
OCSP_REQUEST = 66
OCSP_RESPONSE = 67
OCSP_BASIC_SIGNED_RESPONSE = 68
OCSP_BASIC_RESPONSE = 69
X509_LOGOTYPE_EXT = 70
X509_BIOMETRIC_EXT = 71
CNG_RSA_PUBLIC_KEY_BLOB = 72
X509_OBJECT_IDENTIFIER = 73
X509_ALGORITHM_IDENTIFIER = 74
PKCS_RSA_SSA_PSS_PARAMETERS = 75
PKCS_RSAES_OAEP_PARAMETERS = 76
ECC_CMS_SHARED_INFO = 77
TIMESTAMP_REQUEST = 78
TIMESTAMP_RESPONSE = 79
TIMESTAMP_INFO = 80
X509_CERT_BUNDLE = 81
PKCS7_SIGNER_INFO = 500
CMS_SIGNER_INFO = 501

szOID_AUTHORITY_KEY_IDENTIFIER = "2.5.29.1"
szOID_KEY_ATTRIBUTES = "2.5.29.2"
szOID_CERT_POLICIES_95 = "2.5.29.3"
szOID_KEY_USAGE_RESTRICTION = "2.5.29.4"
szOID_SUBJECT_ALT_NAME = "2.5.29.7"
szOID_ISSUER_ALT_NAME = "2.5.29.8"
szOID_BASIC_CONSTRAINTS = "2.5.29.10"
szOID_KEY_USAGE = "2.5.29.15"
szOID_PRIVATEKEY_USAGE_PERIOD = "2.5.29.16"
szOID_BASIC_CONSTRAINTS2 = "2.5.29.19"
szOID_CERT_POLICIES = "2.5.29.32"
szOID_ANY_CERT_POLICY = "2.5.29.32.0"
szOID_AUTHORITY_KEY_IDENTIFIER2 = "2.5.29.35"
szOID_SUBJECT_KEY_IDENTIFIER = "2.5.29.14"
szOID_SUBJECT_ALT_NAME2 = "2.5.29.17"
szOID_ISSUER_ALT_NAME2 = "2.5.29.18"
szOID_CRL_REASON_CODE = "2.5.29.21"
szOID_REASON_CODE_HOLD = "2.5.29.23"
szOID_CRL_DIST_POINTS = "2.5.29.31"
szOID_ENHANCED_KEY_USAGE = "2.5.29.37"
szOID_CRL_NUMBER = "2.5.29.20"
szOID_DELTA_CRL_INDICATOR = "2.5.29.27"
szOID_ISSUING_DIST_POINT = "2.5.29.28"
szOID_FRESHEST_CRL = "2.5.29.46"
szOID_NAME_CONSTRAINTS = "2.5.29.30"
szOID_POLICY_MAPPINGS = "2.5.29.33"
szOID_LEGACY_POLICY_MAPPINGS = "2.5.29.5"
szOID_POLICY_CONSTRAINTS = "2.5.29.36"
szOID_RENEWAL_CERTIFICATE = "1.3.6.1.4.1.311.13.1"
szOID_ENROLLMENT_NAME_VALUE_PAIR = "1.3.6.1.4.1.311.13.2.1"
szOID_ENROLLMENT_CSP_PROVIDER = "1.3.6.1.4.1.311.13.2.2"
szOID_OS_VERSION = "1.3.6.1.4.1.311.13.2.3"
szOID_ENROLLMENT_AGENT = "1.3.6.1.4.1.311.20.2.1"
szOID_PKIX = "1.3.6.1.5.5.7"
szOID_PKIX_PE = "1.3.6.1.5.5.7.1"
szOID_AUTHORITY_INFO_ACCESS = "1.3.6.1.5.5.7.1.1"
szOID_CERT_EXTENSIONS = "1.3.6.1.4.1.311.2.1.14"
szOID_NEXT_UPDATE_LOCATION = "1.3.6.1.4.1.311.10.2"
szOID_REMOVE_CERTIFICATE = "1.3.6.1.4.1.311.10.8.1"
szOID_CROSS_CERT_DIST_POINTS = "1.3.6.1.4.1.311.10.9.1"
szOID_CTL = "1.3.6.1.4.1.311.10.1"
szOID_SORTED_CTL = "1.3.6.1.4.1.311.10.1.1"
szOID_SERIALIZED = "1.3.6.1.4.1.311.10.3.3.1"
szOID_NT_PRINCIPAL_NAME = "1.3.6.1.4.1.311.20.2.3"
szOID_PRODUCT_UPDATE = "1.3.6.1.4.1.311.31.1"
szOID_ANY_APPLICATION_POLICY = "1.3.6.1.4.1.311.10.12.1"
szOID_AUTO_ENROLL_CTL_USAGE = "1.3.6.1.4.1.311.20.1"
szOID_ENROLL_CERTTYPE_EXTENSION = "1.3.6.1.4.1.311.20.2"
szOID_CERT_MANIFOLD = "1.3.6.1.4.1.311.20.3"
szOID_CERTSRV_CA_VERSION = "1.3.6.1.4.1.311.21.1"
szOID_CERTSRV_PREVIOUS_CERT_HASH = "1.3.6.1.4.1.311.21.2"
szOID_CRL_VIRTUAL_BASE = "1.3.6.1.4.1.311.21.3"
szOID_CRL_NEXT_PUBLISH = "1.3.6.1.4.1.311.21.4"
szOID_KP_CA_EXCHANGE = "1.3.6.1.4.1.311.21.5"
szOID_KP_KEY_RECOVERY_AGENT = "1.3.6.1.4.1.311.21.6"
szOID_CERTIFICATE_TEMPLATE = "1.3.6.1.4.1.311.21.7"
szOID_ENTERPRISE_OID_ROOT = "1.3.6.1.4.1.311.21.8"
szOID_RDN_DUMMY_SIGNER = "1.3.6.1.4.1.311.21.9"
szOID_APPLICATION_CERT_POLICIES = "1.3.6.1.4.1.311.21.10"
szOID_APPLICATION_POLICY_MAPPINGS = "1.3.6.1.4.1.311.21.11"
szOID_APPLICATION_POLICY_CONSTRAINTS = "1.3.6.1.4.1.311.21.12"
szOID_ARCHIVED_KEY_ATTR = "1.3.6.1.4.1.311.21.13"
szOID_CRL_SELF_CDP = "1.3.6.1.4.1.311.21.14"
szOID_REQUIRE_CERT_CHAIN_POLICY = "1.3.6.1.4.1.311.21.15"
szOID_ARCHIVED_KEY_CERT_HASH = "1.3.6.1.4.1.311.21.16"
szOID_ISSUED_CERT_HASH = "1.3.6.1.4.1.311.21.17"
szOID_DS_EMAIL_REPLICATION = "1.3.6.1.4.1.311.21.19"
szOID_REQUEST_CLIENT_INFO = "1.3.6.1.4.1.311.21.20"
szOID_ENCRYPTED_KEY_HASH = "1.3.6.1.4.1.311.21.21"
szOID_CERTSRV_CROSSCA_VERSION = "1.3.6.1.4.1.311.21.22"
szOID_NTDS_REPLICATION = "1.3.6.1.4.1.311.25.1"
szOID_SUBJECT_DIR_ATTRS = "2.5.29.9"
szOID_PKIX_KP = "1.3.6.1.5.5.7.3"
szOID_PKIX_KP_SERVER_AUTH = "1.3.6.1.5.5.7.3.1"
szOID_PKIX_KP_CLIENT_AUTH = "1.3.6.1.5.5.7.3.2"
szOID_PKIX_KP_CODE_SIGNING = "1.3.6.1.5.5.7.3.3"
szOID_PKIX_KP_EMAIL_PROTECTION = "1.3.6.1.5.5.7.3.4"
szOID_PKIX_KP_IPSEC_END_SYSTEM = "1.3.6.1.5.5.7.3.5"
szOID_PKIX_KP_IPSEC_TUNNEL = "1.3.6.1.5.5.7.3.6"
szOID_PKIX_KP_IPSEC_USER = "1.3.6.1.5.5.7.3.7"
szOID_PKIX_KP_TIMESTAMP_SIGNING = "1.3.6.1.5.5.7.3.8"
szOID_IPSEC_KP_IKE_INTERMEDIATE = "1.3.6.1.5.5.8.2.2"
szOID_KP_CTL_USAGE_SIGNING = "1.3.6.1.4.1.311.10.3.1"
szOID_KP_TIME_STAMP_SIGNING = "1.3.6.1.4.1.311.10.3.2"
szOID_SERVER_GATED_CRYPTO = "1.3.6.1.4.1.311.10.3.3"
szOID_SGC_NETSCAPE = "2.16.840.1.113730.4.1"
szOID_KP_EFS = "1.3.6.1.4.1.311.10.3.4"
szOID_EFS_RECOVERY = "1.3.6.1.4.1.311.10.3.4.1"
szOID_WHQL_CRYPTO = "1.3.6.1.4.1.311.10.3.5"
szOID_NT5_CRYPTO = "1.3.6.1.4.1.311.10.3.6"
szOID_OEM_WHQL_CRYPTO = "1.3.6.1.4.1.311.10.3.7"
szOID_EMBEDDED_NT_CRYPTO = "1.3.6.1.4.1.311.10.3.8"
szOID_ROOT_LIST_SIGNER = "1.3.6.1.4.1.311.10.3.9"
szOID_KP_QUALIFIED_SUBORDINATION = "1.3.6.1.4.1.311.10.3.10"
szOID_KP_KEY_RECOVERY = "1.3.6.1.4.1.311.10.3.11"
szOID_KP_DOCUMENT_SIGNING = "1.3.6.1.4.1.311.10.3.12"
szOID_KP_LIFETIME_SIGNING = "1.3.6.1.4.1.311.10.3.13"
szOID_KP_MOBILE_DEVICE_SOFTWARE = "1.3.6.1.4.1.311.10.3.14"
szOID_DRM = "1.3.6.1.4.1.311.10.5.1"
szOID_DRM_INDIVIDUALIZATION = "1.3.6.1.4.1.311.10.5.2"
szOID_LICENSES = "1.3.6.1.4.1.311.10.6.1"
szOID_LICENSE_SERVER = "1.3.6.1.4.1.311.10.6.2"
szOID_KP_SMARTCARD_LOGON = "1.3.6.1.4.1.311.20.2.2"
szOID_YESNO_TRUST_ATTR = "1.3.6.1.4.1.311.10.4.1"
szOID_PKIX_POLICY_QUALIFIER_CPS = "1.3.6.1.5.5.7.2.1"
szOID_PKIX_POLICY_QUALIFIER_USERNOTICE = "1.3.6.1.5.5.7.2.2"
szOID_CERT_POLICIES_95_QUALIFIER1 = "2.16.840.1.113733.1.7.1.1"
CERT_UNICODE_RDN_ERR_INDEX_MASK = 0x3FF
CERT_UNICODE_RDN_ERR_INDEX_SHIFT = 22
CERT_UNICODE_ATTR_ERR_INDEX_MASK = 0x003F
CERT_UNICODE_ATTR_ERR_INDEX_SHIFT = 16
CERT_UNICODE_VALUE_ERR_INDEX_MASK = 0x0000FFFF
CERT_UNICODE_VALUE_ERR_INDEX_SHIFT = 0
CERT_DIGITAL_SIGNATURE_KEY_USAGE = 0x80
CERT_NON_REPUDIATION_KEY_USAGE = 0x40
CERT_KEY_ENCIPHERMENT_KEY_USAGE = 0x20
CERT_DATA_ENCIPHERMENT_KEY_USAGE = 0x10
CERT_KEY_AGREEMENT_KEY_USAGE = 0x08
CERT_KEY_CERT_SIGN_KEY_USAGE = 0x04
CERT_OFFLINE_CRL_SIGN_KEY_USAGE = 0x02
CERT_CRL_SIGN_KEY_USAGE = 0x02
CERT_ENCIPHER_ONLY_KEY_USAGE = 0x01
CERT_DECIPHER_ONLY_KEY_USAGE = 0x80
CERT_ALT_NAME_OTHER_NAME = 1
CERT_ALT_NAME_RFC822_NAME = 2
CERT_ALT_NAME_DNS_NAME = 3
CERT_ALT_NAME_X400_ADDRESS = 4
CERT_ALT_NAME_DIRECTORY_NAME = 5
CERT_ALT_NAME_EDI_PARTY_NAME = 6
CERT_ALT_NAME_URL = 7
CERT_ALT_NAME_IP_ADDRESS = 8
CERT_ALT_NAME_REGISTERED_ID = 9
CERT_ALT_NAME_ENTRY_ERR_INDEX_MASK = 0xFF
CERT_ALT_NAME_ENTRY_ERR_INDEX_SHIFT = 16
CERT_ALT_NAME_VALUE_ERR_INDEX_MASK = 0x0000FFFF
CERT_ALT_NAME_VALUE_ERR_INDEX_SHIFT = 0
CERT_CA_SUBJECT_FLAG = 0x80
CERT_END_ENTITY_SUBJECT_FLAG = 0x40
szOID_PKIX_ACC_DESCR = "1.3.6.1.5.5.7.48"
szOID_PKIX_OCSP = "1.3.6.1.5.5.7.48.1"
szOID_PKIX_CA_ISSUERS = "1.3.6.1.5.5.7.48.2"
CRL_REASON_UNSPECIFIED = 0
CRL_REASON_KEY_COMPROMISE = 1
CRL_REASON_CA_COMPROMISE = 2
CRL_REASON_AFFILIATION_CHANGED = 3
CRL_REASON_SUPERSEDED = 4
CRL_REASON_CESSATION_OF_OPERATION = 5
CRL_REASON_CERTIFICATE_HOLD = 6
CRL_REASON_REMOVE_FROM_CRL = 8
CRL_DIST_POINT_NO_NAME = 0
CRL_DIST_POINT_FULL_NAME = 1
CRL_DIST_POINT_ISSUER_RDN_NAME = 2
CRL_REASON_UNUSED_FLAG = 0x80
CRL_REASON_KEY_COMPROMISE_FLAG = 0x40
CRL_REASON_CA_COMPROMISE_FLAG = 0x20
CRL_REASON_AFFILIATION_CHANGED_FLAG = 0x10
CRL_REASON_SUPERSEDED_FLAG = 0x08
CRL_REASON_CESSATION_OF_OPERATION_FLAG = 0x04
CRL_REASON_CERTIFICATE_HOLD_FLAG = 0x02
CRL_DIST_POINT_ERR_INDEX_MASK = 0x7F
CRL_DIST_POINT_ERR_INDEX_SHIFT = 24

CRL_DIST_POINT_ERR_CRL_ISSUER_BIT = -2147483648

CROSS_CERT_DIST_POINT_ERR_INDEX_MASK = 0xFF
CROSS_CERT_DIST_POINT_ERR_INDEX_SHIFT = 24

CERT_EXCLUDED_SUBTREE_BIT = -2147483648

SORTED_CTL_EXT_FLAGS_OFFSET = 0 * 4
SORTED_CTL_EXT_COUNT_OFFSET = 1 * 4
SORTED_CTL_EXT_MAX_COLLISION_OFFSET = 2 * 4
SORTED_CTL_EXT_HASH_BUCKET_OFFSET = 3 * 4
SORTED_CTL_EXT_HASHED_SUBJECT_IDENTIFIER_FLAG = 0x1
CERT_DSS_R_LEN = 20
CERT_DSS_S_LEN = 20
CERT_DSS_SIGNATURE_LEN = CERT_DSS_R_LEN + CERT_DSS_S_LEN
CERT_MAX_ASN_ENCODED_DSS_SIGNATURE_LEN = 2 + 2 * (2 + 20 + 1)
CRYPT_X942_COUNTER_BYTE_LENGTH = 4
CRYPT_X942_KEY_LENGTH_BYTE_LENGTH = 4
CRYPT_X942_PUB_INFO_BYTE_LENGTH = 512 / 8
CRYPT_RC2_40BIT_VERSION = 160
CRYPT_RC2_56BIT_VERSION = 52
CRYPT_RC2_64BIT_VERSION = 120
CRYPT_RC2_128BIT_VERSION = 58
szOID_VERISIGN_PRIVATE_6_9 = "2.16.840.1.113733.1.6.9"
szOID_VERISIGN_ONSITE_JURISDICTION_HASH = "2.16.840.1.113733.1.6.11"
szOID_VERISIGN_BITSTRING_6_13 = "2.16.840.1.113733.1.6.13"
szOID_VERISIGN_ISS_STRONG_CRYPTO = "2.16.840.1.113733.1.8.1"
szOID_NETSCAPE = "2.16.840.1.113730"
szOID_NETSCAPE_CERT_EXTENSION = "2.16.840.1.113730.1"
szOID_NETSCAPE_CERT_TYPE = "2.16.840.1.113730.1.1"
szOID_NETSCAPE_BASE_URL = "2.16.840.1.113730.1.2"
szOID_NETSCAPE_REVOCATION_URL = "2.16.840.1.113730.1.3"
szOID_NETSCAPE_CA_REVOCATION_URL = "2.16.840.1.113730.1.4"
szOID_NETSCAPE_CERT_RENEWAL_URL = "2.16.840.1.113730.1.7"
szOID_NETSCAPE_CA_POLICY_URL = "2.16.840.1.113730.1.8"
szOID_NETSCAPE_SSL_SERVER_NAME = "2.16.840.1.113730.1.12"
szOID_NETSCAPE_COMMENT = "2.16.840.1.113730.1.13"
szOID_NETSCAPE_DATA_TYPE = "2.16.840.1.113730.2"
szOID_NETSCAPE_CERT_SEQUENCE = "2.16.840.1.113730.2.5"
NETSCAPE_SSL_CLIENT_AUTH_CERT_TYPE = 0x80
NETSCAPE_SSL_SERVER_AUTH_CERT_TYPE = 0x40
NETSCAPE_SMIME_CERT_TYPE = 0x20
NETSCAPE_SIGN_CERT_TYPE = 0x10
NETSCAPE_SSL_CA_CERT_TYPE = 0x04
NETSCAPE_SMIME_CA_CERT_TYPE = 0x02
NETSCAPE_SIGN_CA_CERT_TYPE = 0x01
szOID_CT_PKI_DATA = "1.3.6.1.5.5.7.12.2"
szOID_CT_PKI_RESPONSE = "1.3.6.1.5.5.7.12.3"
szOID_PKIX_NO_SIGNATURE = "1.3.6.1.5.5.7.6.2"
szOID_CMC = "1.3.6.1.5.5.7.7"
szOID_CMC_STATUS_INFO = "1.3.6.1.5.5.7.7.1"
szOID_CMC_IDENTIFICATION = "1.3.6.1.5.5.7.7.2"
szOID_CMC_IDENTITY_PROOF = "1.3.6.1.5.5.7.7.3"
szOID_CMC_DATA_RETURN = "1.3.6.1.5.5.7.7.4"
szOID_CMC_TRANSACTION_ID = "1.3.6.1.5.5.7.7.5"
szOID_CMC_SENDER_NONCE = "1.3.6.1.5.5.7.7.6"
szOID_CMC_RECIPIENT_NONCE = "1.3.6.1.5.5.7.7.7"
szOID_CMC_ADD_EXTENSIONS = "1.3.6.1.5.5.7.7.8"
szOID_CMC_ENCRYPTED_POP = "1.3.6.1.5.5.7.7.9"
szOID_CMC_DECRYPTED_POP = "1.3.6.1.5.5.7.7.10"
szOID_CMC_LRA_POP_WITNESS = "1.3.6.1.5.5.7.7.11"
szOID_CMC_GET_CERT = "1.3.6.1.5.5.7.7.15"
szOID_CMC_GET_CRL = "1.3.6.1.5.5.7.7.16"
szOID_CMC_REVOKE_REQUEST = "1.3.6.1.5.5.7.7.17"
szOID_CMC_REG_INFO = "1.3.6.1.5.5.7.7.18"
szOID_CMC_RESPONSE_INFO = "1.3.6.1.5.5.7.7.19"
szOID_CMC_QUERY_PENDING = "1.3.6.1.5.5.7.7.21"
szOID_CMC_ID_POP_LINK_RANDOM = "1.3.6.1.5.5.7.7.22"
szOID_CMC_ID_POP_LINK_WITNESS = "1.3.6.1.5.5.7.7.23"
szOID_CMC_ID_CONFIRM_CERT_ACCEPTANCE = "1.3.6.1.5.5.7.7.24"
szOID_CMC_ADD_ATTRIBUTES = "1.3.6.1.4.1.311.10.10.1"
CMC_TAGGED_CERT_REQUEST_CHOICE = 1
CMC_OTHER_INFO_NO_CHOICE = 0
CMC_OTHER_INFO_FAIL_CHOICE = 1
CMC_OTHER_INFO_PEND_CHOICE = 2
CMC_STATUS_SUCCESS = 0
CMC_STATUS_FAILED = 2
CMC_STATUS_PENDING = 3
CMC_STATUS_NO_SUPPORT = 4
CMC_STATUS_CONFIRM_REQUIRED = 5
CMC_FAIL_BAD_ALG = 0
CMC_FAIL_BAD_MESSAGE_CHECK = 1
CMC_FAIL_BAD_REQUEST = 2
CMC_FAIL_BAD_TIME = 3
CMC_FAIL_BAD_CERT_ID = 4
CMC_FAIL_UNSUPORTED_EXT = 5  # Yes Microsoft made a typo in "UNSUPPORTED"
CMC_FAIL_MUST_ARCHIVE_KEYS = 6
CMC_FAIL_BAD_IDENTITY = 7
CMC_FAIL_POP_REQUIRED = 8
CMC_FAIL_POP_FAILED = 9
CMC_FAIL_NO_KEY_REUSE = 10
CMC_FAIL_INTERNAL_CA_ERROR = 11
CMC_FAIL_TRY_LATER = 12
CRYPT_OID_ENCODE_OBJECT_FUNC = "CryptDllEncodeObject"
CRYPT_OID_DECODE_OBJECT_FUNC = "CryptDllDecodeObject"
CRYPT_OID_ENCODE_OBJECT_EX_FUNC = "CryptDllEncodeObjectEx"
CRYPT_OID_DECODE_OBJECT_EX_FUNC = "CryptDllDecodeObjectEx"
CRYPT_OID_CREATE_COM_OBJECT_FUNC = "CryptDllCreateCOMObject"
CRYPT_OID_VERIFY_REVOCATION_FUNC = "CertDllVerifyRevocation"
CRYPT_OID_VERIFY_CTL_USAGE_FUNC = "CertDllVerifyCTLUsage"
CRYPT_OID_FORMAT_OBJECT_FUNC = "CryptDllFormatObject"
CRYPT_OID_FIND_OID_INFO_FUNC = "CryptDllFindOIDInfo"
CRYPT_OID_FIND_LOCALIZED_NAME_FUNC = "CryptDllFindLocalizedName"

CRYPT_OID_REGPATH = "Software\\Microsoft\\Cryptography\\OID"
CRYPT_OID_REG_ENCODING_TYPE_PREFIX = "EncodingType "
CRYPT_OID_REG_DLL_VALUE_NAME = "Dll"
CRYPT_OID_REG_FUNC_NAME_VALUE_NAME = "FuncName"
CRYPT_OID_REG_FUNC_NAME_VALUE_NAME_A = "FuncName"
CRYPT_OID_REG_FLAGS_VALUE_NAME = "CryptFlags"
CRYPT_DEFAULT_OID = "DEFAULT"
CRYPT_INSTALL_OID_FUNC_BEFORE_FLAG = 1
CRYPT_GET_INSTALLED_OID_FUNC_FLAG = 0x1
CRYPT_REGISTER_FIRST_INDEX = 0
CRYPT_REGISTER_LAST_INDEX = -1
CRYPT_MATCH_ANY_ENCODING_TYPE = -1
CRYPT_HASH_ALG_OID_GROUP_ID = 1
CRYPT_ENCRYPT_ALG_OID_GROUP_ID = 2
CRYPT_PUBKEY_ALG_OID_GROUP_ID = 3
CRYPT_SIGN_ALG_OID_GROUP_ID = 4
CRYPT_RDN_ATTR_OID_GROUP_ID = 5
CRYPT_EXT_OR_ATTR_OID_GROUP_ID = 6
CRYPT_ENHKEY_USAGE_OID_GROUP_ID = 7
CRYPT_POLICY_OID_GROUP_ID = 8
CRYPT_TEMPLATE_OID_GROUP_ID = 9
CRYPT_LAST_OID_GROUP_ID = 9
CRYPT_FIRST_ALG_OID_GROUP_ID = CRYPT_HASH_ALG_OID_GROUP_ID
CRYPT_LAST_ALG_OID_GROUP_ID = CRYPT_SIGN_ALG_OID_GROUP_ID
CRYPT_OID_INHIBIT_SIGNATURE_FORMAT_FLAG = 0x1
CRYPT_OID_USE_PUBKEY_PARA_FOR_PKCS7_FLAG = 0x2
CRYPT_OID_NO_NULL_ALGORITHM_PARA_FLAG = 0x4
CRYPT_OID_INFO_OID_KEY = 1
CRYPT_OID_INFO_NAME_KEY = 2
CRYPT_OID_INFO_ALGID_KEY = 3
CRYPT_OID_INFO_SIGN_KEY = 4
CRYPT_INSTALL_OID_INFO_BEFORE_FLAG = 1
CRYPT_LOCALIZED_NAME_ENCODING_TYPE = 0
CRYPT_LOCALIZED_NAME_OID = "LocalizedNames"
szOID_PKCS_7_DATA = "1.2.840.113549.1.7.1"
szOID_PKCS_7_SIGNED = "1.2.840.113549.1.7.2"
szOID_PKCS_7_ENVELOPED = "1.2.840.113549.1.7.3"
szOID_PKCS_7_SIGNEDANDENVELOPED = "1.2.840.113549.1.7.4"
szOID_PKCS_7_DIGESTED = "1.2.840.113549.1.7.5"
szOID_PKCS_7_ENCRYPTED = "1.2.840.113549.1.7.6"
szOID_PKCS_9_CONTENT_TYPE = "1.2.840.113549.1.9.3"
szOID_PKCS_9_MESSAGE_DIGEST = "1.2.840.113549.1.9.4"
CMSG_DATA = 1
CMSG_SIGNED = 2
CMSG_ENVELOPED = 3
CMSG_SIGNED_AND_ENVELOPED = 4
CMSG_HASHED = 5
CMSG_ENCRYPTED = 6

CMSG_ALL_FLAGS = -1
CMSG_DATA_FLAG = 1 << CMSG_DATA
CMSG_SIGNED_FLAG = 1 << CMSG_SIGNED
CMSG_ENVELOPED_FLAG = 1 << CMSG_ENVELOPED
CMSG_SIGNED_AND_ENVELOPED_FLAG = 1 << CMSG_SIGNED_AND_ENVELOPED
CMSG_HASHED_FLAG = 1 << CMSG_HASHED
CMSG_ENCRYPTED_FLAG = 1 << CMSG_ENCRYPTED
CERT_ID_ISSUER_SERIAL_NUMBER = 1
CERT_ID_KEY_IDENTIFIER = 2
CERT_ID_SHA1_HASH = 3
CMSG_KEY_AGREE_EPHEMERAL_KEY_CHOICE = 1
CMSG_KEY_AGREE_STATIC_KEY_CHOICE = 2
CMSG_MAIL_LIST_HANDLE_KEY_CHOICE = 1
CMSG_KEY_TRANS_RECIPIENT = 1
CMSG_KEY_AGREE_RECIPIENT = 2
CMSG_MAIL_LIST_RECIPIENT = 3
CMSG_SP3_COMPATIBLE_ENCRYPT_FLAG = -2147483648
CMSG_RC4_NO_SALT_FLAG = 0x40000000
CMSG_INDEFINITE_LENGTH = -1
CMSG_BARE_CONTENT_FLAG = 0x00000001
CMSG_LENGTH_ONLY_FLAG = 0x00000002
CMSG_DETACHED_FLAG = 0x00000004
CMSG_AUTHENTICATED_ATTRIBUTES_FLAG = 0x00000008
CMSG_CONTENTS_OCTETS_FLAG = 0x00000010
CMSG_MAX_LENGTH_FLAG = 0x00000020
CMSG_CMS_ENCAPSULATED_CONTENT_FLAG = 0x00000040
CMSG_CRYPT_RELEASE_CONTEXT_FLAG = 0x00008000
CMSG_TYPE_PARAM = 1
CMSG_CONTENT_PARAM = 2
CMSG_BARE_CONTENT_PARAM = 3
CMSG_INNER_CONTENT_TYPE_PARAM = 4
CMSG_SIGNER_COUNT_PARAM = 5
CMSG_SIGNER_INFO_PARAM = 6
CMSG_SIGNER_CERT_INFO_PARAM = 7
CMSG_SIGNER_HASH_ALGORITHM_PARAM = 8
CMSG_SIGNER_AUTH_ATTR_PARAM = 9
CMSG_SIGNER_UNAUTH_ATTR_PARAM = 10
CMSG_CERT_COUNT_PARAM = 11
CMSG_CERT_PARAM = 12
CMSG_CRL_COUNT_PARAM = 13
CMSG_CRL_PARAM = 14
CMSG_ENVELOPE_ALGORITHM_PARAM = 15
CMSG_RECIPIENT_COUNT_PARAM = 17
CMSG_RECIPIENT_INDEX_PARAM = 18
CMSG_RECIPIENT_INFO_PARAM = 19
CMSG_HASH_ALGORITHM_PARAM = 20
CMSG_HASH_DATA_PARAM = 21
CMSG_COMPUTED_HASH_PARAM = 22
CMSG_ENCRYPT_PARAM = 26
CMSG_ENCRYPTED_DIGEST = 27
CMSG_ENCODED_SIGNER = 28
CMSG_ENCODED_MESSAGE = 29
CMSG_VERSION_PARAM = 30
CMSG_ATTR_CERT_COUNT_PARAM = 31
CMSG_ATTR_CERT_PARAM = 32
CMSG_CMS_RECIPIENT_COUNT_PARAM = 33
CMSG_CMS_RECIPIENT_INDEX_PARAM = 34
CMSG_CMS_RECIPIENT_ENCRYPTED_KEY_INDEX_PARAM = 35
CMSG_CMS_RECIPIENT_INFO_PARAM = 36
CMSG_UNPROTECTED_ATTR_PARAM = 37
CMSG_SIGNER_CERT_ID_PARAM = 38
CMSG_CMS_SIGNER_INFO_PARAM = 39
CMSG_SIGNED_DATA_V1 = 1
CMSG_SIGNED_DATA_V3 = 3
CMSG_SIGNED_DATA_PKCS_1_5_VERSION = CMSG_SIGNED_DATA_V1
CMSG_SIGNED_DATA_CMS_VERSION = CMSG_SIGNED_DATA_V3
CMSG_SIGNER_INFO_V1 = 1
CMSG_SIGNER_INFO_V3 = 3
CMSG_SIGNER_INFO_PKCS_1_5_VERSION = CMSG_SIGNER_INFO_V1
CMSG_SIGNER_INFO_CMS_VERSION = CMSG_SIGNER_INFO_V3
CMSG_HASHED_DATA_V0 = 0
CMSG_HASHED_DATA_V2 = 2
CMSG_HASHED_DATA_PKCS_1_5_VERSION = CMSG_HASHED_DATA_V0
CMSG_HASHED_DATA_CMS_VERSION = CMSG_HASHED_DATA_V2
CMSG_ENVELOPED_DATA_V0 = 0
CMSG_ENVELOPED_DATA_V2 = 2
CMSG_ENVELOPED_DATA_PKCS_1_5_VERSION = CMSG_ENVELOPED_DATA_V0
CMSG_ENVELOPED_DATA_CMS_VERSION = CMSG_ENVELOPED_DATA_V2
CMSG_KEY_AGREE_ORIGINATOR_CERT = 1
CMSG_KEY_AGREE_ORIGINATOR_PUBLIC_KEY = 2
CMSG_ENVELOPED_RECIPIENT_V0 = 0
CMSG_ENVELOPED_RECIPIENT_V2 = 2
CMSG_ENVELOPED_RECIPIENT_V3 = 3
CMSG_ENVELOPED_RECIPIENT_V4 = 4
CMSG_KEY_TRANS_PKCS_1_5_VERSION = CMSG_ENVELOPED_RECIPIENT_V0
CMSG_KEY_TRANS_CMS_VERSION = CMSG_ENVELOPED_RECIPIENT_V2
CMSG_KEY_AGREE_VERSION = CMSG_ENVELOPED_RECIPIENT_V3
CMSG_MAIL_LIST_VERSION = CMSG_ENVELOPED_RECIPIENT_V4
CMSG_CTRL_VERIFY_SIGNATURE = 1
CMSG_CTRL_DECRYPT = 2
CMSG_CTRL_VERIFY_HASH = 5
CMSG_CTRL_ADD_SIGNER = 6
CMSG_CTRL_DEL_SIGNER = 7
CMSG_CTRL_ADD_SIGNER_UNAUTH_ATTR = 8
CMSG_CTRL_DEL_SIGNER_UNAUTH_ATTR = 9
CMSG_CTRL_ADD_CERT = 10
CMSG_CTRL_DEL_CERT = 11
CMSG_CTRL_ADD_CRL = 12
CMSG_CTRL_DEL_CRL = 13
CMSG_CTRL_ADD_ATTR_CERT = 14
CMSG_CTRL_DEL_ATTR_CERT = 15
CMSG_CTRL_KEY_TRANS_DECRYPT = 16
CMSG_CTRL_KEY_AGREE_DECRYPT = 17
CMSG_CTRL_MAIL_LIST_DECRYPT = 18
CMSG_CTRL_VERIFY_SIGNATURE_EX = 19
CMSG_CTRL_ADD_CMS_SIGNER_INFO = 20
CMSG_VERIFY_SIGNER_PUBKEY = 1
CMSG_VERIFY_SIGNER_CERT = 2
CMSG_VERIFY_SIGNER_CHAIN = 3
CMSG_VERIFY_SIGNER_NULL = 4
CMSG_OID_GEN_ENCRYPT_KEY_FUNC = "CryptMsgDllGenEncryptKey"
CMSG_OID_EXPORT_ENCRYPT_KEY_FUNC = "CryptMsgDllExportEncryptKey"
CMSG_OID_IMPORT_ENCRYPT_KEY_FUNC = "CryptMsgDllImportEncryptKey"
CMSG_CONTENT_ENCRYPT_PAD_ENCODED_LEN_FLAG = 0x00000001
CMSG_DEFAULT_INSTALLABLE_FUNC_OID = 1
CMSG_CONTENT_ENCRYPT_FREE_PARA_FLAG = 0x00000001
CMSG_CONTENT_ENCRYPT_RELEASE_CONTEXT_FLAG = 0x00008000
CMSG_OID_GEN_CONTENT_ENCRYPT_KEY_FUNC = "CryptMsgDllGenContentEncryptKey"
CMSG_KEY_TRANS_ENCRYPT_FREE_PARA_FLAG = 0x00000001
CMSG_OID_EXPORT_KEY_TRANS_FUNC = "CryptMsgDllExportKeyTrans"
CMSG_KEY_AGREE_ENCRYPT_FREE_PARA_FLAG = 0x00000001
CMSG_KEY_AGREE_ENCRYPT_FREE_MATERIAL_FLAG = 0x00000002
CMSG_KEY_AGREE_ENCRYPT_FREE_PUBKEY_ALG_FLAG = 0x00000004
CMSG_KEY_AGREE_ENCRYPT_FREE_PUBKEY_PARA_FLAG = 0x00000008
CMSG_KEY_AGREE_ENCRYPT_FREE_PUBKEY_BITS_FLAG = 0x00000010
CMSG_OID_EXPORT_KEY_AGREE_FUNC = "CryptMsgDllExportKeyAgree"
CMSG_MAIL_LIST_ENCRYPT_FREE_PARA_FLAG = 0x00000001
CMSG_OID_EXPORT_MAIL_LIST_FUNC = "CryptMsgDllExportMailList"
CMSG_OID_IMPORT_KEY_TRANS_FUNC = "CryptMsgDllImportKeyTrans"
CMSG_OID_IMPORT_KEY_AGREE_FUNC = "CryptMsgDllImportKeyAgree"
CMSG_OID_IMPORT_MAIL_LIST_FUNC = "CryptMsgDllImportMailList"

# Certificate property id's used with CertGetCertificateContextProperty
CERT_KEY_PROV_HANDLE_PROP_ID = 1
CERT_KEY_PROV_INFO_PROP_ID = 2
CERT_SHA1_HASH_PROP_ID = 3
CERT_MD5_HASH_PROP_ID = 4
CERT_HASH_PROP_ID = CERT_SHA1_HASH_PROP_ID
CERT_KEY_CONTEXT_PROP_ID = 5
CERT_KEY_SPEC_PROP_ID = 6
CERT_IE30_RESERVED_PROP_ID = 7
CERT_PUBKEY_HASH_RESERVED_PROP_ID = 8
CERT_ENHKEY_USAGE_PROP_ID = 9
CERT_CTL_USAGE_PROP_ID = CERT_ENHKEY_USAGE_PROP_ID
CERT_NEXT_UPDATE_LOCATION_PROP_ID = 10
CERT_FRIENDLY_NAME_PROP_ID = 11
CERT_PVK_FILE_PROP_ID = 12
CERT_DESCRIPTION_PROP_ID = 13
CERT_ACCESS_STATE_PROP_ID = 14
CERT_SIGNATURE_HASH_PROP_ID = 15
CERT_SMART_CARD_DATA_PROP_ID = 16
CERT_EFS_PROP_ID = 17
CERT_FORTEZZA_DATA_PROP_ID = 18
CERT_ARCHIVED_PROP_ID = 19
CERT_KEY_IDENTIFIER_PROP_ID = 20
CERT_AUTO_ENROLL_PROP_ID = 21
CERT_PUBKEY_ALG_PARA_PROP_ID = 22
CERT_CROSS_CERT_DIST_POINTS_PROP_ID = 23
CERT_ISSUER_PUBLIC_KEY_MD5_HASH_PROP_ID = 24
CERT_SUBJECT_PUBLIC_KEY_MD5_HASH_PROP_ID = 25
CERT_ENROLLMENT_PROP_ID = 26
CERT_DATE_STAMP_PROP_ID = 27
CERT_ISSUER_SERIAL_NUMBER_MD5_HASH_PROP_ID = 28
CERT_SUBJECT_NAME_MD5_HASH_PROP_ID = 29
CERT_EXTENDED_ERROR_INFO_PROP_ID = 30
CERT_RENEWAL_PROP_ID = 64
CERT_ARCHIVED_KEY_HASH_PROP_ID = 65
CERT_AUTO_ENROLL_RETRY_PROP_ID = 66
CERT_AIA_URL_RETRIEVED_PROP_ID = 67
CERT_AUTHORITY_INFO_ACCESS_PROP_ID = 68
CERT_BACKED_UP_PROP_ID = 69
CERT_OCSP_RESPONSE_PROP_ID = 70
CERT_REQUEST_ORIGINATOR_PROP_ID = 71
CERT_SOURCE_LOCATION_PROP_ID = 72
CERT_SOURCE_URL_PROP_ID = 73
CERT_NEW_KEY_PROP_ID = 74
CERT_OCSP_CACHE_PREFIX_PROP_ID = 75
CERT_SMART_CARD_ROOT_INFO_PROP_ID = 76
CERT_NO_AUTO_EXPIRE_CHECK_PROP_ID = 77
CERT_NCRYPT_KEY_HANDLE_PROP_ID = 78
CERT_HCRYPTPROV_OR_NCRYPT_KEY_HANDLE_PROP_ID = 79
CERT_SUBJECT_INFO_ACCESS_PROP_ID = 80
CERT_CA_OCSP_AUTHORITY_INFO_ACCESS_PROP_ID = 81
CERT_CA_DISABLE_CRL_PROP_ID = 82
CERT_ROOT_PROGRAM_CERT_POLICIES_PROP_ID = 83
CERT_ROOT_PROGRAM_NAME_CONSTRAINTS_PROP_ID = 84
CERT_SUBJECT_OCSP_AUTHORITY_INFO_ACCESS_PROP_ID = 85
CERT_SUBJECT_DISABLE_CRL_PROP_ID = 86
CERT_CEP_PROP_ID = 87
CERT_SIGN_HASH_CNG_ALG_PROP_ID = 89
CERT_SCARD_PIN_ID_PROP_ID = 90
CERT_SCARD_PIN_INFO_PROP_ID = 91
CERT_FIRST_RESERVED_PROP_ID = 92
CERT_LAST_RESERVED_PROP_ID = 0x00007FFF
CERT_FIRST_USER_PROP_ID = 0x00008000
CERT_LAST_USER_PROP_ID = 0x0000FFFF

szOID_CERT_PROP_ID_PREFIX = "1.3.6.1.4.1.311.10.11."
szOID_CERT_KEY_IDENTIFIER_PROP_ID = "1.3.6.1.4.1.311.10.11.20"
szOID_CERT_ISSUER_SERIAL_NUMBER_MD5_HASH_PROP_ID = "1.3.6.1.4.1.311.10.11.28"
szOID_CERT_SUBJECT_NAME_MD5_HASH_PROP_ID = "1.3.6.1.4.1.311.10.11.29"
CERT_ACCESS_STATE_WRITE_PERSIST_FLAG = 0x1
CERT_ACCESS_STATE_SYSTEM_STORE_FLAG = 0x2
CERT_ACCESS_STATE_LM_SYSTEM_STORE_FLAG = 0x4
CERT_SET_KEY_PROV_HANDLE_PROP_ID = 0x00000001
CERT_SET_KEY_CONTEXT_PROP_ID = 0x00000001
sz_CERT_STORE_PROV_MEMORY = "Memory"
sz_CERT_STORE_PROV_FILENAME_W = "File"
sz_CERT_STORE_PROV_FILENAME = sz_CERT_STORE_PROV_FILENAME_W
sz_CERT_STORE_PROV_SYSTEM_W = "System"
sz_CERT_STORE_PROV_SYSTEM = sz_CERT_STORE_PROV_SYSTEM_W
sz_CERT_STORE_PROV_PKCS7 = "PKCS7"
sz_CERT_STORE_PROV_SERIALIZED = "Serialized"
sz_CERT_STORE_PROV_COLLECTION = "Collection"
sz_CERT_STORE_PROV_SYSTEM_REGISTRY_W = "SystemRegistry"
sz_CERT_STORE_PROV_SYSTEM_REGISTRY = sz_CERT_STORE_PROV_SYSTEM_REGISTRY_W
sz_CERT_STORE_PROV_PHYSICAL_W = "Physical"
sz_CERT_STORE_PROV_PHYSICAL = sz_CERT_STORE_PROV_PHYSICAL_W
sz_CERT_STORE_PROV_SMART_CARD_W = "SmartCard"
sz_CERT_STORE_PROV_SMART_CARD = sz_CERT_STORE_PROV_SMART_CARD_W
sz_CERT_STORE_PROV_LDAP_W = "Ldap"
sz_CERT_STORE_PROV_LDAP = sz_CERT_STORE_PROV_LDAP_W
CERT_STORE_SIGNATURE_FLAG = 0x00000001
CERT_STORE_TIME_VALIDITY_FLAG = 0x00000002
CERT_STORE_REVOCATION_FLAG = 0x00000004
CERT_STORE_NO_CRL_FLAG = 0x00010000
CERT_STORE_NO_ISSUER_FLAG = 0x00020000
CERT_STORE_BASE_CRL_FLAG = 0x00000100
CERT_STORE_DELTA_CRL_FLAG = 0x00000200
CERT_STORE_NO_CRYPT_RELEASE_FLAG = 0x00000001
CERT_STORE_SET_LOCALIZED_NAME_FLAG = 0x00000002
CERT_STORE_DEFER_CLOSE_UNTIL_LAST_FREE_FLAG = 0x00000004
CERT_STORE_DELETE_FLAG = 0x00000010
CERT_STORE_UNSAFE_PHYSICAL_FLAG = 0x00000020
CERT_STORE_SHARE_STORE_FLAG = 0x00000040
CERT_STORE_SHARE_CONTEXT_FLAG = 0x00000080
CERT_STORE_MANIFOLD_FLAG = 0x00000100
CERT_STORE_ENUM_ARCHIVED_FLAG = 0x00000200
CERT_STORE_UPDATE_KEYID_FLAG = 0x00000400
CERT_STORE_BACKUP_RESTORE_FLAG = 0x00000800
CERT_STORE_READONLY_FLAG = 0x00008000
CERT_STORE_OPEN_EXISTING_FLAG = 0x00004000
CERT_STORE_CREATE_NEW_FLAG = 0x00002000
CERT_STORE_MAXIMUM_ALLOWED_FLAG = 0x00001000
CERT_SYSTEM_STORE_MASK = -65536
CERT_SYSTEM_STORE_RELOCATE_FLAG = -2147483648
CERT_SYSTEM_STORE_UNPROTECTED_FLAG = 0x40000000
CERT_SYSTEM_STORE_LOCATION_MASK = 0x00FF0000
CERT_SYSTEM_STORE_LOCATION_SHIFT = 16
CERT_SYSTEM_STORE_CURRENT_USER_ID = 1
CERT_SYSTEM_STORE_LOCAL_MACHINE_ID = 2
CERT_SYSTEM_STORE_CURRENT_SERVICE_ID = 4
CERT_SYSTEM_STORE_SERVICES_ID = 5
CERT_SYSTEM_STORE_USERS_ID = 6
CERT_SYSTEM_STORE_CURRENT_USER_GROUP_POLICY_ID = 7
CERT_SYSTEM_STORE_LOCAL_MACHINE_GROUP_POLICY_ID = 8
CERT_SYSTEM_STORE_LOCAL_MACHINE_ENTERPRISE_ID = 9
CERT_SYSTEM_STORE_CURRENT_USER = (
    CERT_SYSTEM_STORE_CURRENT_USER_ID << CERT_SYSTEM_STORE_LOCATION_SHIFT
)
CERT_SYSTEM_STORE_LOCAL_MACHINE = (
    CERT_SYSTEM_STORE_LOCAL_MACHINE_ID << CERT_SYSTEM_STORE_LOCATION_SHIFT
)
CERT_SYSTEM_STORE_CURRENT_SERVICE = (
    CERT_SYSTEM_STORE_CURRENT_SERVICE_ID << CERT_SYSTEM_STORE_LOCATION_SHIFT
)
CERT_SYSTEM_STORE_SERVICES = (
    CERT_SYSTEM_STORE_SERVICES_ID << CERT_SYSTEM_STORE_LOCATION_SHIFT
)
CERT_SYSTEM_STORE_USERS = CERT_SYSTEM_STORE_USERS_ID << CERT_SYSTEM_STORE_LOCATION_SHIFT
CERT_SYSTEM_STORE_CURRENT_USER_GROUP_POLICY = (
    CERT_SYSTEM_STORE_CURRENT_USER_GROUP_POLICY_ID << CERT_SYSTEM_STORE_LOCATION_SHIFT
)
CERT_SYSTEM_STORE_LOCAL_MACHINE_GROUP_POLICY = (
    CERT_SYSTEM_STORE_LOCAL_MACHINE_GROUP_POLICY_ID << CERT_SYSTEM_STORE_LOCATION_SHIFT
)
CERT_SYSTEM_STORE_LOCAL_MACHINE_ENTERPRISE = (
    CERT_SYSTEM_STORE_LOCAL_MACHINE_ENTERPRISE_ID << CERT_SYSTEM_STORE_LOCATION_SHIFT
)
CERT_PROT_ROOT_DISABLE_CURRENT_USER_FLAG = 0x1
CERT_PROT_ROOT_INHIBIT_ADD_AT_INIT_FLAG = 0x2
CERT_PROT_ROOT_INHIBIT_PURGE_LM_FLAG = 0x4
CERT_PROT_ROOT_DISABLE_LM_AUTH_FLAG = 0x8
CERT_PROT_ROOT_ONLY_LM_GPT_FLAG = 0x8
CERT_PROT_ROOT_DISABLE_NT_AUTH_REQUIRED_FLAG = 0x10
CERT_PROT_ROOT_DISABLE_NOT_DEFINED_NAME_CONSTRAINT_FLAG = 0x20
CERT_TRUST_PUB_ALLOW_TRUST_MASK = 0x00000003
CERT_TRUST_PUB_ALLOW_END_USER_TRUST = 0x00000000
CERT_TRUST_PUB_ALLOW_MACHINE_ADMIN_TRUST = 0x00000001
CERT_TRUST_PUB_ALLOW_ENTERPRISE_ADMIN_TRUST = 0x00000002
CERT_TRUST_PUB_CHECK_PUBLISHER_REV_FLAG = 0x00000100
CERT_TRUST_PUB_CHECK_TIMESTAMP_REV_FLAG = 0x00000200

CERT_AUTH_ROOT_AUTO_UPDATE_DISABLE_UNTRUSTED_ROOT_LOGGING_FLAG = 0x1
CERT_AUTH_ROOT_AUTO_UPDATE_DISABLE_PARTIAL_CHAIN_LOGGING_FLAG = 0x2
CERT_AUTH_ROOT_AUTO_UPDATE_ROOT_DIR_URL_VALUE_NAME = "RootDirUrl"
CERT_AUTH_ROOT_AUTO_UPDATE_SYNC_DELTA_TIME_VALUE_NAME = "SyncDeltaTime"
CERT_AUTH_ROOT_AUTO_UPDATE_FLAGS_VALUE_NAME = "Flags"
CERT_AUTH_ROOT_CTL_FILENAME = "authroot.stl"
CERT_AUTH_ROOT_CTL_FILENAME_A = "authroot.stl"
CERT_AUTH_ROOT_CAB_FILENAME = "authrootstl.cab"
CERT_AUTH_ROOT_SEQ_FILENAME = "authrootseq.txt"
CERT_AUTH_ROOT_CERT_EXT = ".crt"

CERT_GROUP_POLICY_SYSTEM_STORE_REGPATH = (
    r"Software\Policies\Microsoft\SystemCertificates"
)
CERT_EFSBLOB_REGPATH = CERT_GROUP_POLICY_SYSTEM_STORE_REGPATH + r"\EFS"
CERT_EFSBLOB_VALUE_NAME = "EFSBlob"
CERT_PROT_ROOT_FLAGS_REGPATH = (
    CERT_GROUP_POLICY_SYSTEM_STORE_REGPATH + r"\Root\ProtectedRoots"
)
CERT_PROT_ROOT_FLAGS_VALUE_NAME = "Flags"
CERT_TRUST_PUB_SAFER_GROUP_POLICY_REGPATH = (
    CERT_GROUP_POLICY_SYSTEM_STORE_REGPATH + r"\TrustedPublisher\Safer"
)
CERT_LOCAL_MACHINE_SYSTEM_STORE_REGPATH = r"Software\Microsoft\SystemCertificates"
CERT_TRUST_PUB_SAFER_LOCAL_MACHINE_REGPATH = (
    CERT_LOCAL_MACHINE_SYSTEM_STORE_REGPATH + r"\TrustedPublisher\Safer"
)
CERT_TRUST_PUB_AUTHENTICODE_FLAGS_VALUE_NAME = "AuthenticodeFlags"
CERT_OCM_SUBCOMPONENTS_LOCAL_MACHINE_REGPATH = (
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Setup\OC Manager\Subcomponents"
)
CERT_OCM_SUBCOMPONENTS_ROOT_AUTO_UPDATE_VALUE_NAME = r"RootAutoUpdate"
CERT_DISABLE_ROOT_AUTO_UPDATE_REGPATH = (
    CERT_GROUP_POLICY_SYSTEM_STORE_REGPATH + r"\AuthRoot"
)
CERT_DISABLE_ROOT_AUTO_UPDATE_VALUE_NAME = "DisableRootAutoUpdate"
CERT_AUTH_ROOT_AUTO_UPDATE_LOCAL_MACHINE_REGPATH = (
    CERT_LOCAL_MACHINE_SYSTEM_STORE_REGPATH + r"\AuthRoot\AutoUpdate"
)

CERT_REGISTRY_STORE_REMOTE_FLAG = 0x10000
CERT_REGISTRY_STORE_SERIALIZED_FLAG = 0x20000
CERT_REGISTRY_STORE_CLIENT_GPT_FLAG = -2147483648
CERT_REGISTRY_STORE_LM_GPT_FLAG = 0x01000000
CERT_REGISTRY_STORE_ROAMING_FLAG = 0x40000
CERT_REGISTRY_STORE_MY_IE_DIRTY_FLAG = 0x80000
CERT_IE_DIRTY_FLAGS_REGPATH = r"Software\Microsoft\Cryptography\IEDirtyFlags"

CERT_FILE_STORE_COMMIT_ENABLE_FLAG = 0x10000
CERT_LDAP_STORE_SIGN_FLAG = 0x10000
CERT_LDAP_STORE_AREC_EXCLUSIVE_FLAG = 0x20000
CERT_LDAP_STORE_OPENED_FLAG = 0x40000
CERT_LDAP_STORE_UNBIND_FLAG = 0x80000
CRYPT_OID_OPEN_STORE_PROV_FUNC = "CertDllOpenStoreProv"

CERT_STORE_PROV_EXTERNAL_FLAG = 0x1
CERT_STORE_PROV_DELETED_FLAG = 0x2
CERT_STORE_PROV_NO_PERSIST_FLAG = 0x4
CERT_STORE_PROV_SYSTEM_STORE_FLAG = 0x8
CERT_STORE_PROV_LM_SYSTEM_STORE_FLAG = 0x10
CERT_STORE_PROV_CLOSE_FUNC = 0
CERT_STORE_PROV_READ_CERT_FUNC = 1
CERT_STORE_PROV_WRITE_CERT_FUNC = 2
CERT_STORE_PROV_DELETE_CERT_FUNC = 3
CERT_STORE_PROV_SET_CERT_PROPERTY_FUNC = 4
CERT_STORE_PROV_READ_CRL_FUNC = 5
CERT_STORE_PROV_WRITE_CRL_FUNC = 6
CERT_STORE_PROV_DELETE_CRL_FUNC = 7
CERT_STORE_PROV_SET_CRL_PROPERTY_FUNC = 8
CERT_STORE_PROV_READ_CTL_FUNC = 9
CERT_STORE_PROV_WRITE_CTL_FUNC = 10
CERT_STORE_PROV_DELETE_CTL_FUNC = 11
CERT_STORE_PROV_SET_CTL_PROPERTY_FUNC = 12
CERT_STORE_PROV_CONTROL_FUNC = 13
CERT_STORE_PROV_FIND_CERT_FUNC = 14
CERT_STORE_PROV_FREE_FIND_CERT_FUNC = 15
CERT_STORE_PROV_GET_CERT_PROPERTY_FUNC = 16
CERT_STORE_PROV_FIND_CRL_FUNC = 17
CERT_STORE_PROV_FREE_FIND_CRL_FUNC = 18
CERT_STORE_PROV_GET_CRL_PROPERTY_FUNC = 19
CERT_STORE_PROV_FIND_CTL_FUNC = 20
CERT_STORE_PROV_FREE_FIND_CTL_FUNC = 21
CERT_STORE_PROV_GET_CTL_PROPERTY_FUNC = 22
CERT_STORE_PROV_WRITE_ADD_FLAG = 0x1
CERT_STORE_SAVE_AS_STORE = 1
CERT_STORE_SAVE_AS_PKCS7 = 2
CERT_STORE_SAVE_TO_FILE = 1
CERT_STORE_SAVE_TO_MEMORY = 2
CERT_STORE_SAVE_TO_FILENAME_A = 3
CERT_STORE_SAVE_TO_FILENAME_W = 4
CERT_STORE_SAVE_TO_FILENAME = CERT_STORE_SAVE_TO_FILENAME_W
CERT_CLOSE_STORE_FORCE_FLAG = 0x00000001
CERT_CLOSE_STORE_CHECK_FLAG = 0x00000002
CERT_COMPARE_MASK = 0xFFFF
CERT_COMPARE_SHIFT = 16
CERT_COMPARE_ANY = 0
CERT_COMPARE_SHA1_HASH = 1
CERT_COMPARE_NAME = 2
CERT_COMPARE_ATTR = 3
CERT_COMPARE_MD5_HASH = 4
CERT_COMPARE_PROPERTY = 5
CERT_COMPARE_PUBLIC_KEY = 6
CERT_COMPARE_HASH = CERT_COMPARE_SHA1_HASH
CERT_COMPARE_NAME_STR_A = 7
CERT_COMPARE_NAME_STR_W = 8
CERT_COMPARE_KEY_SPEC = 9
CERT_COMPARE_ENHKEY_USAGE = 10
CERT_COMPARE_CTL_USAGE = CERT_COMPARE_ENHKEY_USAGE
CERT_COMPARE_SUBJECT_CERT = 11
CERT_COMPARE_ISSUER_OF = 12
CERT_COMPARE_EXISTING = 13
CERT_COMPARE_SIGNATURE_HASH = 14
CERT_COMPARE_KEY_IDENTIFIER = 15
CERT_COMPARE_CERT_ID = 16
CERT_COMPARE_CROSS_CERT_DIST_POINTS = 17
CERT_COMPARE_PUBKEY_MD5_HASH = 18
CERT_FIND_ANY = CERT_COMPARE_ANY << CERT_COMPARE_SHIFT
CERT_FIND_SHA1_HASH = CERT_COMPARE_SHA1_HASH << CERT_COMPARE_SHIFT
CERT_FIND_MD5_HASH = CERT_COMPARE_MD5_HASH << CERT_COMPARE_SHIFT
CERT_FIND_SIGNATURE_HASH = CERT_COMPARE_SIGNATURE_HASH << CERT_COMPARE_SHIFT
CERT_FIND_KEY_IDENTIFIER = CERT_COMPARE_KEY_IDENTIFIER << CERT_COMPARE_SHIFT
CERT_FIND_HASH = CERT_FIND_SHA1_HASH
CERT_FIND_PROPERTY = CERT_COMPARE_PROPERTY << CERT_COMPARE_SHIFT
CERT_FIND_PUBLIC_KEY = CERT_COMPARE_PUBLIC_KEY << CERT_COMPARE_SHIFT
CERT_FIND_SUBJECT_NAME = (
    CERT_COMPARE_NAME << CERT_COMPARE_SHIFT | CERT_INFO_SUBJECT_FLAG
)
CERT_FIND_SUBJECT_ATTR = (
    CERT_COMPARE_ATTR << CERT_COMPARE_SHIFT | CERT_INFO_SUBJECT_FLAG
)
CERT_FIND_ISSUER_NAME = CERT_COMPARE_NAME << CERT_COMPARE_SHIFT | CERT_INFO_ISSUER_FLAG
CERT_FIND_ISSUER_ATTR = CERT_COMPARE_ATTR << CERT_COMPARE_SHIFT | CERT_INFO_ISSUER_FLAG
CERT_FIND_SUBJECT_STR_A = (
    CERT_COMPARE_NAME_STR_A << CERT_COMPARE_SHIFT | CERT_INFO_SUBJECT_FLAG
)
CERT_FIND_SUBJECT_STR_W = (
    CERT_COMPARE_NAME_STR_W << CERT_COMPARE_SHIFT | CERT_INFO_SUBJECT_FLAG
)
CERT_FIND_SUBJECT_STR = CERT_FIND_SUBJECT_STR_W
CERT_FIND_ISSUER_STR_A = (
    CERT_COMPARE_NAME_STR_A << CERT_COMPARE_SHIFT | CERT_INFO_ISSUER_FLAG
)
CERT_FIND_ISSUER_STR_W = (
    CERT_COMPARE_NAME_STR_W << CERT_COMPARE_SHIFT | CERT_INFO_ISSUER_FLAG
)
CERT_FIND_ISSUER_STR = CERT_FIND_ISSUER_STR_W
CERT_FIND_KEY_SPEC = CERT_COMPARE_KEY_SPEC << CERT_COMPARE_SHIFT
CERT_FIND_ENHKEY_USAGE = CERT_COMPARE_ENHKEY_USAGE << CERT_COMPARE_SHIFT
CERT_FIND_CTL_USAGE = CERT_FIND_ENHKEY_USAGE
CERT_FIND_SUBJECT_CERT = CERT_COMPARE_SUBJECT_CERT << CERT_COMPARE_SHIFT
CERT_FIND_ISSUER_OF = CERT_COMPARE_ISSUER_OF << CERT_COMPARE_SHIFT
CERT_FIND_EXISTING = CERT_COMPARE_EXISTING << CERT_COMPARE_SHIFT
CERT_FIND_CERT_ID = CERT_COMPARE_CERT_ID << CERT_COMPARE_SHIFT
CERT_FIND_CROSS_CERT_DIST_POINTS = (
    CERT_COMPARE_CROSS_CERT_DIST_POINTS << CERT_COMPARE_SHIFT
)
CERT_FIND_PUBKEY_MD5_HASH = CERT_COMPARE_PUBKEY_MD5_HASH << CERT_COMPARE_SHIFT
CERT_FIND_OPTIONAL_ENHKEY_USAGE_FLAG = 0x1
CERT_FIND_EXT_ONLY_ENHKEY_USAGE_FLAG = 0x2
CERT_FIND_PROP_ONLY_ENHKEY_USAGE_FLAG = 0x4
CERT_FIND_NO_ENHKEY_USAGE_FLAG = 0x8
CERT_FIND_OR_ENHKEY_USAGE_FLAG = 0x10
CERT_FIND_VALID_ENHKEY_USAGE_FLAG = 0x20
CERT_FIND_OPTIONAL_CTL_USAGE_FLAG = CERT_FIND_OPTIONAL_ENHKEY_USAGE_FLAG
CERT_FIND_EXT_ONLY_CTL_USAGE_FLAG = CERT_FIND_EXT_ONLY_ENHKEY_USAGE_FLAG
CERT_FIND_PROP_ONLY_CTL_USAGE_FLAG = CERT_FIND_PROP_ONLY_ENHKEY_USAGE_FLAG
CERT_FIND_NO_CTL_USAGE_FLAG = CERT_FIND_NO_ENHKEY_USAGE_FLAG
CERT_FIND_OR_CTL_USAGE_FLAG = CERT_FIND_OR_ENHKEY_USAGE_FLAG
CERT_FIND_VALID_CTL_USAGE_FLAG = CERT_FIND_VALID_ENHKEY_USAGE_FLAG
CERT_SET_PROPERTY_IGNORE_PERSIST_ERROR_FLAG = -2147483648
CERT_SET_PROPERTY_INHIBIT_PERSIST_FLAG = 0x40000000
CTL_ENTRY_FROM_PROP_CHAIN_FLAG = 0x1
CRL_FIND_ANY = 0
CRL_FIND_ISSUED_BY = 1
CRL_FIND_EXISTING = 2
CRL_FIND_ISSUED_FOR = 3
CRL_FIND_ISSUED_BY_AKI_FLAG = 0x1
CRL_FIND_ISSUED_BY_SIGNATURE_FLAG = 0x2
CRL_FIND_ISSUED_BY_DELTA_FLAG = 0x4
CRL_FIND_ISSUED_BY_BASE_FLAG = 0x8
CERT_STORE_ADD_NEW = 1
CERT_STORE_ADD_USE_EXISTING = 2
CERT_STORE_ADD_REPLACE_EXISTING = 3
CERT_STORE_ADD_ALWAYS = 4
CERT_STORE_ADD_REPLACE_EXISTING_INHERIT_PROPERTIES = 5
CERT_STORE_ADD_NEWER = 6
CERT_STORE_ADD_NEWER_INHERIT_PROPERTIES = 7
CERT_STORE_CERTIFICATE_CONTEXT = 1
CERT_STORE_CRL_CONTEXT = 2
CERT_STORE_CTL_CONTEXT = 3

CERT_STORE_ALL_CONTEXT_FLAG = -1
CERT_STORE_CERTIFICATE_CONTEXT_FLAG = 1 << CERT_STORE_CERTIFICATE_CONTEXT
CERT_STORE_CRL_CONTEXT_FLAG = 1 << CERT_STORE_CRL_CONTEXT
CERT_STORE_CTL_CONTEXT_FLAG = 1 << CERT_STORE_CTL_CONTEXT
CTL_ANY_SUBJECT_TYPE = 1
CTL_CERT_SUBJECT_TYPE = 2
CTL_FIND_ANY = 0
CTL_FIND_SHA1_HASH = 1
CTL_FIND_MD5_HASH = 2
CTL_FIND_USAGE = 3
CTL_FIND_SUBJECT = 4
CTL_FIND_EXISTING = 5
CTL_FIND_NO_LIST_ID_CBDATA = -1
CTL_FIND_SAME_USAGE_FLAG = 0x1
CERT_STORE_CTRL_RESYNC = 1
CERT_STORE_CTRL_NOTIFY_CHANGE = 2
CERT_STORE_CTRL_COMMIT = 3
CERT_STORE_CTRL_AUTO_RESYNC = 4
CERT_STORE_CTRL_CANCEL_NOTIFY = 5
CERT_STORE_CTRL_INHIBIT_DUPLICATE_HANDLE_FLAG = 0x1
CERT_STORE_CTRL_COMMIT_FORCE_FLAG = 0x1
CERT_STORE_CTRL_COMMIT_CLEAR_FLAG = 0x2
CERT_STORE_LOCALIZED_NAME_PROP_ID = 0x1000
CERT_CREATE_CONTEXT_NOCOPY_FLAG = 0x1
CERT_CREATE_CONTEXT_SORTED_FLAG = 0x2
CERT_CREATE_CONTEXT_NO_HCRYPTMSG_FLAG = 0x4
CERT_CREATE_CONTEXT_NO_ENTRY_FLAG = 0x8

CERT_PHYSICAL_STORE_ADD_ENABLE_FLAG = 0x1
CERT_PHYSICAL_STORE_OPEN_DISABLE_FLAG = 0x2
CERT_PHYSICAL_STORE_REMOTE_OPEN_DISABLE_FLAG = 0x4
CERT_PHYSICAL_STORE_INSERT_COMPUTER_NAME_ENABLE_FLAG = 0x8
CERT_PHYSICAL_STORE_PREDEFINED_ENUM_FLAG = 0x1

# Names of physical cert stores
CERT_PHYSICAL_STORE_DEFAULT_NAME = ".Default"
CERT_PHYSICAL_STORE_GROUP_POLICY_NAME = ".GroupPolicy"
CERT_PHYSICAL_STORE_LOCAL_MACHINE_NAME = ".LocalMachine"
CERT_PHYSICAL_STORE_DS_USER_CERTIFICATE_NAME = ".UserCertificate"
CERT_PHYSICAL_STORE_LOCAL_MACHINE_GROUP_POLICY_NAME = ".LocalMachineGroupPolicy"
CERT_PHYSICAL_STORE_ENTERPRISE_NAME = ".Enterprise"
CERT_PHYSICAL_STORE_AUTH_ROOT_NAME = ".AuthRoot"
CERT_PHYSICAL_STORE_SMART_CARD_NAME = ".SmartCard"

CRYPT_OID_OPEN_SYSTEM_STORE_PROV_FUNC = "CertDllOpenSystemStoreProv"
CRYPT_OID_REGISTER_SYSTEM_STORE_FUNC = "CertDllRegisterSystemStore"
CRYPT_OID_UNREGISTER_SYSTEM_STORE_FUNC = "CertDllUnregisterSystemStore"
CRYPT_OID_ENUM_SYSTEM_STORE_FUNC = "CertDllEnumSystemStore"
CRYPT_OID_REGISTER_PHYSICAL_STORE_FUNC = "CertDllRegisterPhysicalStore"
CRYPT_OID_UNREGISTER_PHYSICAL_STORE_FUNC = "CertDllUnregisterPhysicalStore"
CRYPT_OID_ENUM_PHYSICAL_STORE_FUNC = "CertDllEnumPhysicalStore"
CRYPT_OID_SYSTEM_STORE_LOCATION_VALUE_NAME = "SystemStoreLocation"

CMSG_TRUSTED_SIGNER_FLAG = 0x1
CMSG_SIGNER_ONLY_FLAG = 0x2
CMSG_USE_SIGNER_INDEX_FLAG = 0x4
CMSG_CMS_ENCAPSULATED_CTL_FLAG = 0x00008000
CMSG_ENCODE_SORTED_CTL_FLAG = 0x1
CMSG_ENCODE_HASHED_SUBJECT_IDENTIFIER_FLAG = 0x2
CERT_VERIFY_INHIBIT_CTL_UPDATE_FLAG = 0x1
CERT_VERIFY_TRUSTED_SIGNERS_FLAG = 0x2
CERT_VERIFY_NO_TIME_CHECK_FLAG = 0x4
CERT_VERIFY_ALLOW_MORE_USAGE_FLAG = 0x8
CERT_VERIFY_UPDATED_CTL_FLAG = 0x1
CERT_CONTEXT_REVOCATION_TYPE = 1
CERT_VERIFY_REV_CHAIN_FLAG = 0x00000001
CERT_VERIFY_CACHE_ONLY_BASED_REVOCATION = 0x00000002
CERT_VERIFY_REV_ACCUMULATIVE_TIMEOUT_FLAG = 0x00000004
CERT_UNICODE_IS_RDN_ATTRS_FLAG = 0x1
CERT_CASE_INSENSITIVE_IS_RDN_ATTRS_FLAG = 0x2
CRYPT_VERIFY_CERT_SIGN_SUBJECT_BLOB = 1
CRYPT_VERIFY_CERT_SIGN_SUBJECT_CERT = 2
CRYPT_VERIFY_CERT_SIGN_SUBJECT_CRL = 3
CRYPT_VERIFY_CERT_SIGN_ISSUER_PUBKEY = 1
CRYPT_VERIFY_CERT_SIGN_ISSUER_CERT = 2
CRYPT_VERIFY_CERT_SIGN_ISSUER_CHAIN = 3
CRYPT_VERIFY_CERT_SIGN_ISSUER_NULL = 4
CRYPT_DEFAULT_CONTEXT_AUTO_RELEASE_FLAG = 0x00000001
CRYPT_DEFAULT_CONTEXT_PROCESS_FLAG = 0x00000002
CRYPT_DEFAULT_CONTEXT_CERT_SIGN_OID = 1
CRYPT_DEFAULT_CONTEXT_MULTI_CERT_SIGN_OID = 2
CRYPT_OID_EXPORT_PUBLIC_KEY_INFO_FUNC = "CryptDllExportPublicKeyInfoEx"
CRYPT_OID_IMPORT_PUBLIC_KEY_INFO_FUNC = "CryptDllImportPublicKeyInfoEx"
CRYPT_ACQUIRE_CACHE_FLAG = 0x00000001
CRYPT_ACQUIRE_USE_PROV_INFO_FLAG = 0x00000002
CRYPT_ACQUIRE_COMPARE_KEY_FLAG = 0x00000004
CRYPT_ACQUIRE_SILENT_FLAG = 0x00000040
CRYPT_FIND_USER_KEYSET_FLAG = 0x00000001
CRYPT_FIND_MACHINE_KEYSET_FLAG = 0x00000002
CRYPT_FIND_SILENT_KEYSET_FLAG = 0x00000040
CRYPT_OID_IMPORT_PRIVATE_KEY_INFO_FUNC = "CryptDllImportPrivateKeyInfoEx"
CRYPT_OID_EXPORT_PRIVATE_KEY_INFO_FUNC = "CryptDllExportPrivateKeyInfoEx"
CRYPT_DELETE_KEYSET = CRYPT_DELETEKEYSET
CERT_SIMPLE_NAME_STR = 1
CERT_OID_NAME_STR = 2
CERT_X500_NAME_STR = 3
CERT_NAME_STR_SEMICOLON_FLAG = 0x40000000
CERT_NAME_STR_NO_PLUS_FLAG = 0x20000000
CERT_NAME_STR_NO_QUOTING_FLAG = 0x10000000
CERT_NAME_STR_CRLF_FLAG = 0x08000000
CERT_NAME_STR_COMMA_FLAG = 0x04000000
CERT_NAME_STR_REVERSE_FLAG = 0x02000000
CERT_NAME_STR_DISABLE_IE4_UTF8_FLAG = 0x00010000
CERT_NAME_STR_ENABLE_T61_UNICODE_FLAG = 0x00020000
CERT_NAME_STR_ENABLE_UTF8_UNICODE_FLAG = 0x00040000
CERT_NAME_EMAIL_TYPE = 1
CERT_NAME_RDN_TYPE = 2
CERT_NAME_ATTR_TYPE = 3
CERT_NAME_SIMPLE_DISPLAY_TYPE = 4
CERT_NAME_FRIENDLY_DISPLAY_TYPE = 5
CERT_NAME_DNS_TYPE = 6
CERT_NAME_URL_TYPE = 7
CERT_NAME_UPN_TYPE = 8
CERT_NAME_ISSUER_FLAG = 0x1
CERT_NAME_DISABLE_IE4_UTF8_FLAG = 0x00010000
CRYPT_MESSAGE_BARE_CONTENT_OUT_FLAG = 0x00000001
CRYPT_MESSAGE_ENCAPSULATED_CONTENT_OUT_FLAG = 0x00000002
CRYPT_MESSAGE_KEYID_SIGNER_FLAG = 0x00000004
CRYPT_MESSAGE_SILENT_KEYSET_FLAG = 0x00000040
CRYPT_MESSAGE_KEYID_RECIPIENT_FLAG = 0x4
CERT_QUERY_OBJECT_FILE = 0x00000001
CERT_QUERY_OBJECT_BLOB = 0x00000002
CERT_QUERY_CONTENT_CERT = 1
CERT_QUERY_CONTENT_CTL = 2
CERT_QUERY_CONTENT_CRL = 3
CERT_QUERY_CONTENT_SERIALIZED_STORE = 4
CERT_QUERY_CONTENT_SERIALIZED_CERT = 5
CERT_QUERY_CONTENT_SERIALIZED_CTL = 6
CERT_QUERY_CONTENT_SERIALIZED_CRL = 7
CERT_QUERY_CONTENT_PKCS7_SIGNED = 8
CERT_QUERY_CONTENT_PKCS7_UNSIGNED = 9
CERT_QUERY_CONTENT_PKCS7_SIGNED_EMBED = 10
CERT_QUERY_CONTENT_PKCS10 = 11
CERT_QUERY_CONTENT_PFX = 12
CERT_QUERY_CONTENT_CERT_PAIR = 13
CERT_QUERY_CONTENT_FLAG_CERT = 1 << CERT_QUERY_CONTENT_CERT
CERT_QUERY_CONTENT_FLAG_CTL = 1 << CERT_QUERY_CONTENT_CTL
CERT_QUERY_CONTENT_FLAG_CRL = 1 << CERT_QUERY_CONTENT_CRL
CERT_QUERY_CONTENT_FLAG_SERIALIZED_STORE = 1 << CERT_QUERY_CONTENT_SERIALIZED_STORE
CERT_QUERY_CONTENT_FLAG_SERIALIZED_CERT = 1 << CERT_QUERY_CONTENT_SERIALIZED_CERT
CERT_QUERY_CONTENT_FLAG_SERIALIZED_CTL = 1 << CERT_QUERY_CONTENT_SERIALIZED_CTL
CERT_QUERY_CONTENT_FLAG_SERIALIZED_CRL = 1 << CERT_QUERY_CONTENT_SERIALIZED_CRL
CERT_QUERY_CONTENT_FLAG_PKCS7_SIGNED = 1 << CERT_QUERY_CONTENT_PKCS7_SIGNED
CERT_QUERY_CONTENT_FLAG_PKCS7_UNSIGNED = 1 << CERT_QUERY_CONTENT_PKCS7_UNSIGNED
CERT_QUERY_CONTENT_FLAG_PKCS7_SIGNED_EMBED = 1 << CERT_QUERY_CONTENT_PKCS7_SIGNED_EMBED
CERT_QUERY_CONTENT_FLAG_PKCS10 = 1 << CERT_QUERY_CONTENT_PKCS10
CERT_QUERY_CONTENT_FLAG_PFX = 1 << CERT_QUERY_CONTENT_PFX
CERT_QUERY_CONTENT_FLAG_CERT_PAIR = 1 << CERT_QUERY_CONTENT_CERT_PAIR
CERT_QUERY_CONTENT_FLAG_ALL = (
    CERT_QUERY_CONTENT_FLAG_CERT
    | CERT_QUERY_CONTENT_FLAG_CTL
    | CERT_QUERY_CONTENT_FLAG_CRL
    | CERT_QUERY_CONTENT_FLAG_SERIALIZED_STORE
    | CERT_QUERY_CONTENT_FLAG_SERIALIZED_CERT
    | CERT_QUERY_CONTENT_FLAG_SERIALIZED_CTL
    | CERT_QUERY_CONTENT_FLAG_SERIALIZED_CRL
    | CERT_QUERY_CONTENT_FLAG_PKCS7_SIGNED
    | CERT_QUERY_CONTENT_FLAG_PKCS7_UNSIGNED
    | CERT_QUERY_CONTENT_FLAG_PKCS7_SIGNED_EMBED
    | CERT_QUERY_CONTENT_FLAG_PKCS10
    | CERT_QUERY_CONTENT_FLAG_PFX
    | CERT_QUERY_CONTENT_FLAG_CERT_PAIR
)
CERT_QUERY_FORMAT_BINARY = 1
CERT_QUERY_FORMAT_BASE64_ENCODED = 2
CERT_QUERY_FORMAT_ASN_ASCII_HEX_ENCODED = 3
CERT_QUERY_FORMAT_FLAG_BINARY = 1 << CERT_QUERY_FORMAT_BINARY
CERT_QUERY_FORMAT_FLAG_BASE64_ENCODED = 1 << CERT_QUERY_FORMAT_BASE64_ENCODED
CERT_QUERY_FORMAT_FLAG_ASN_ASCII_HEX_ENCODED = (
    1 << CERT_QUERY_FORMAT_ASN_ASCII_HEX_ENCODED
)
CERT_QUERY_FORMAT_FLAG_ALL = (
    CERT_QUERY_FORMAT_FLAG_BINARY
    | CERT_QUERY_FORMAT_FLAG_BASE64_ENCODED
    | CERT_QUERY_FORMAT_FLAG_ASN_ASCII_HEX_ENCODED
)

CREDENTIAL_OID_PASSWORD_CREDENTIALS_A = 1
CREDENTIAL_OID_PASSWORD_CREDENTIALS_W = 2
CREDENTIAL_OID_PASSWORD_CREDENTIALS = CREDENTIAL_OID_PASSWORD_CREDENTIALS_W

SCHEME_OID_RETRIEVE_ENCODED_OBJECT_FUNC = "SchemeDllRetrieveEncodedObject"
SCHEME_OID_RETRIEVE_ENCODED_OBJECTW_FUNC = "SchemeDllRetrieveEncodedObjectW"
CONTEXT_OID_CREATE_OBJECT_CONTEXT_FUNC = "ContextDllCreateObjectContext"
CONTEXT_OID_CERTIFICATE = 1
CONTEXT_OID_CRL = 2
CONTEXT_OID_CTL = 3
CONTEXT_OID_PKCS7 = 4
CONTEXT_OID_CAPI2_ANY = 5
CONTEXT_OID_OCSP_RESP = 6

CRYPT_RETRIEVE_MULTIPLE_OBJECTS = 0x00000001
CRYPT_CACHE_ONLY_RETRIEVAL = 0x00000002
CRYPT_WIRE_ONLY_RETRIEVAL = 0x00000004
CRYPT_DONT_CACHE_RESULT = 0x00000008
CRYPT_ASYNC_RETRIEVAL = 0x00000010
CRYPT_STICKY_CACHE_RETRIEVAL = 0x00001000
CRYPT_LDAP_SCOPE_BASE_ONLY_RETRIEVAL = 0x00002000
CRYPT_OFFLINE_CHECK_RETRIEVAL = 0x00004000
CRYPT_LDAP_INSERT_ENTRY_ATTRIBUTE = 0x00008000
CRYPT_LDAP_SIGN_RETRIEVAL = 0x00010000
CRYPT_NO_AUTH_RETRIEVAL = 0x00020000
CRYPT_LDAP_AREC_EXCLUSIVE_RETRIEVAL = 0x00040000
CRYPT_AIA_RETRIEVAL = 0x00080000
CRYPT_VERIFY_CONTEXT_SIGNATURE = 0x00000020
CRYPT_VERIFY_DATA_HASH = 0x00000040
CRYPT_KEEP_TIME_VALID = 0x00000080
CRYPT_DONT_VERIFY_SIGNATURE = 0x00000100
CRYPT_DONT_CHECK_TIME_VALIDITY = 0x00000200
CRYPT_CHECK_FRESHNESS_TIME_VALIDITY = 0x00000400
CRYPT_ACCUMULATIVE_TIMEOUT = 0x00000800
CRYPT_PARAM_ASYNC_RETRIEVAL_COMPLETION = 1
CRYPT_PARAM_CANCEL_ASYNC_RETRIEVAL = 2
CRYPT_GET_URL_FROM_PROPERTY = 0x00000001
CRYPT_GET_URL_FROM_EXTENSION = 0x00000002
CRYPT_GET_URL_FROM_UNAUTH_ATTRIBUTE = 0x00000004
CRYPT_GET_URL_FROM_AUTH_ATTRIBUTE = 0x00000008
URL_OID_GET_OBJECT_URL_FUNC = "UrlDllGetObjectUrl"
TIME_VALID_OID_GET_OBJECT_FUNC = "TimeValidDllGetObject"
TIME_VALID_OID_FLUSH_OBJECT_FUNC = "TimeValidDllFlushObject"

TIME_VALID_OID_GET_CTL = 1
TIME_VALID_OID_GET_CRL = 2
TIME_VALID_OID_GET_CRL_FROM_CERT = 3
TIME_VALID_OID_GET_FRESHEST_CRL_FROM_CERT = 4
TIME_VALID_OID_GET_FRESHEST_CRL_FROM_CRL = 5

TIME_VALID_OID_FLUSH_CTL = 1
TIME_VALID_OID_FLUSH_CRL = 2
TIME_VALID_OID_FLUSH_CRL_FROM_CERT = 3
TIME_VALID_OID_FLUSH_FRESHEST_CRL_FROM_CERT = 4
TIME_VALID_OID_FLUSH_FRESHEST_CRL_FROM_CRL = 5

CRYPTPROTECT_PROMPT_ON_UNPROTECT = 0x1
CRYPTPROTECT_PROMPT_ON_PROTECT = 0x2
CRYPTPROTECT_PROMPT_RESERVED = 0x04
CRYPTPROTECT_PROMPT_STRONG = 0x08
CRYPTPROTECT_PROMPT_REQUIRE_STRONG = 0x10
CRYPTPROTECT_UI_FORBIDDEN = 0x1
CRYPTPROTECT_LOCAL_MACHINE = 0x4
CRYPTPROTECT_CRED_SYNC = 0x8
CRYPTPROTECT_AUDIT = 0x10
CRYPTPROTECT_NO_RECOVERY = 0x20
CRYPTPROTECT_VERIFY_PROTECTION = 0x40
CRYPTPROTECT_CRED_REGENERATE = 0x80
CRYPTPROTECT_FIRST_RESERVED_FLAGVAL = 0x0FFFFFFF
CRYPTPROTECT_LAST_RESERVED_FLAGVAL = -1
CRYPTPROTECTMEMORY_BLOCK_SIZE = 16
CRYPTPROTECTMEMORY_SAME_PROCESS = 0x00
CRYPTPROTECTMEMORY_CROSS_PROCESS = 0x01
CRYPTPROTECTMEMORY_SAME_LOGON = 0x02
CERT_CREATE_SELFSIGN_NO_SIGN = 1
CERT_CREATE_SELFSIGN_NO_KEY_INFO = 2
CRYPT_KEYID_MACHINE_FLAG = 0x00000020
CRYPT_KEYID_ALLOC_FLAG = 0x00008000
CRYPT_KEYID_DELETE_FLAG = 0x00000010
CRYPT_KEYID_SET_NEW_FLAG = 0x00002000
CERT_CHAIN_MAX_AIA_URL_COUNT_IN_CERT_DEFAULT = 5
CERT_CHAIN_MAX_AIA_URL_RETRIEVAL_COUNT_PER_CHAIN_DEFAULT = 10
CERT_CHAIN_MAX_AIA_URL_RETRIEVAL_BYTE_COUNT_DEFAULT = 100000
CERT_CHAIN_MAX_AIA_URL_RETRIEVAL_CERT_COUNT_DEFAULT = 10
CERT_CHAIN_CACHE_END_CERT = 0x00000001
CERT_CHAIN_THREAD_STORE_SYNC = 0x00000002
CERT_CHAIN_CACHE_ONLY_URL_RETRIEVAL = 0x00000004
CERT_CHAIN_USE_LOCAL_MACHINE_STORE = 0x00000008
CERT_CHAIN_ENABLE_CACHE_AUTO_UPDATE = 0x00000010
CERT_CHAIN_ENABLE_SHARE_STORE = 0x00000020
CERT_TRUST_NO_ERROR = 0x00000000
CERT_TRUST_IS_NOT_TIME_VALID = 0x00000001
CERT_TRUST_IS_NOT_TIME_NESTED = 0x00000002
CERT_TRUST_IS_REVOKED = 0x00000004
CERT_TRUST_IS_NOT_SIGNATURE_VALID = 0x00000008
CERT_TRUST_IS_NOT_VALID_FOR_USAGE = 0x00000010
CERT_TRUST_IS_UNTRUSTED_ROOT = 0x00000020
CERT_TRUST_REVOCATION_STATUS_UNKNOWN = 0x00000040
CERT_TRUST_IS_CYCLIC = 0x00000080
CERT_TRUST_INVALID_EXTENSION = 0x00000100
CERT_TRUST_INVALID_POLICY_CONSTRAINTS = 0x00000200
CERT_TRUST_INVALID_BASIC_CONSTRAINTS = 0x00000400
CERT_TRUST_INVALID_NAME_CONSTRAINTS = 0x00000800
CERT_TRUST_HAS_NOT_SUPPORTED_NAME_CONSTRAINT = 0x00001000
CERT_TRUST_HAS_NOT_DEFINED_NAME_CONSTRAINT = 0x00002000
CERT_TRUST_HAS_NOT_PERMITTED_NAME_CONSTRAINT = 0x00004000
CERT_TRUST_HAS_EXCLUDED_NAME_CONSTRAINT = 0x00008000
CERT_TRUST_IS_OFFLINE_REVOCATION = 0x01000000
CERT_TRUST_NO_ISSUANCE_CHAIN_POLICY = 0x02000000
CERT_TRUST_IS_PARTIAL_CHAIN = 0x00010000
CERT_TRUST_CTL_IS_NOT_TIME_VALID = 0x00020000
CERT_TRUST_CTL_IS_NOT_SIGNATURE_VALID = 0x00040000
CERT_TRUST_CTL_IS_NOT_VALID_FOR_USAGE = 0x00080000
CERT_TRUST_HAS_EXACT_MATCH_ISSUER = 0x00000001
CERT_TRUST_HAS_KEY_MATCH_ISSUER = 0x00000002
CERT_TRUST_HAS_NAME_MATCH_ISSUER = 0x00000004
CERT_TRUST_IS_SELF_SIGNED = 0x00000008
CERT_TRUST_HAS_PREFERRED_ISSUER = 0x00000100
CERT_TRUST_HAS_ISSUANCE_CHAIN_POLICY = 0x00000200
CERT_TRUST_HAS_VALID_NAME_CONSTRAINTS = 0x00000400
CERT_TRUST_IS_COMPLEX_CHAIN = 0x00010000
USAGE_MATCH_TYPE_AND = 0x00000000
USAGE_MATCH_TYPE_OR = 0x00000001
CERT_CHAIN_REVOCATION_CHECK_END_CERT = 0x10000000
CERT_CHAIN_REVOCATION_CHECK_CHAIN = 0x20000000
CERT_CHAIN_REVOCATION_CHECK_CHAIN_EXCLUDE_ROOT = 0x40000000
CERT_CHAIN_REVOCATION_CHECK_CACHE_ONLY = -2147483648
CERT_CHAIN_REVOCATION_ACCUMULATIVE_TIMEOUT = 0x08000000
CERT_CHAIN_DISABLE_PASS1_QUALITY_FILTERING = 0x00000040
CERT_CHAIN_RETURN_LOWER_QUALITY_CONTEXTS = 0x00000080
CERT_CHAIN_DISABLE_AUTH_ROOT_AUTO_UPDATE = 0x00000100
CERT_CHAIN_TIMESTAMP_TIME = 0x00000200
REVOCATION_OID_CRL_REVOCATION = 1
CERT_CHAIN_FIND_BY_ISSUER = 1
CERT_CHAIN_FIND_BY_ISSUER_COMPARE_KEY_FLAG = 0x0001
CERT_CHAIN_FIND_BY_ISSUER_COMPLEX_CHAIN_FLAG = 0x0002
CERT_CHAIN_FIND_BY_ISSUER_CACHE_ONLY_URL_FLAG = 0x0004
CERT_CHAIN_FIND_BY_ISSUER_LOCAL_MACHINE_FLAG = 0x0008
CERT_CHAIN_FIND_BY_ISSUER_NO_KEY_FLAG = 0x4000
CERT_CHAIN_FIND_BY_ISSUER_CACHE_ONLY_FLAG = 0x8000
CERT_CHAIN_POLICY_IGNORE_NOT_TIME_VALID_FLAG = 0x00000001
CERT_CHAIN_POLICY_IGNORE_CTL_NOT_TIME_VALID_FLAG = 0x00000002
CERT_CHAIN_POLICY_IGNORE_NOT_TIME_NESTED_FLAG = 0x00000004
CERT_CHAIN_POLICY_IGNORE_INVALID_BASIC_CONSTRAINTS_FLAG = 0x00000008
CERT_CHAIN_POLICY_IGNORE_ALL_NOT_TIME_VALID_FLAGS = (
    CERT_CHAIN_POLICY_IGNORE_NOT_TIME_VALID_FLAG
    | CERT_CHAIN_POLICY_IGNORE_CTL_NOT_TIME_VALID_FLAG
    | CERT_CHAIN_POLICY_IGNORE_NOT_TIME_NESTED_FLAG
)
CERT_CHAIN_POLICY_ALLOW_UNKNOWN_CA_FLAG = 0x00000010
CERT_CHAIN_POLICY_IGNORE_WRONG_USAGE_FLAG = 0x00000020
CERT_CHAIN_POLICY_IGNORE_INVALID_NAME_FLAG = 0x00000040
CERT_CHAIN_POLICY_IGNORE_INVALID_POLICY_FLAG = 0x00000080
CERT_CHAIN_POLICY_IGNORE_END_REV_UNKNOWN_FLAG = 0x00000100
CERT_CHAIN_POLICY_IGNORE_CTL_SIGNER_REV_UNKNOWN_FLAG = 0x00000200
CERT_CHAIN_POLICY_IGNORE_CA_REV_UNKNOWN_FLAG = 0x00000400
CERT_CHAIN_POLICY_IGNORE_ROOT_REV_UNKNOWN_FLAG = 0x00000800
CERT_CHAIN_POLICY_IGNORE_ALL_REV_UNKNOWN_FLAGS = (
    CERT_CHAIN_POLICY_IGNORE_END_REV_UNKNOWN_FLAG
    | CERT_CHAIN_POLICY_IGNORE_CTL_SIGNER_REV_UNKNOWN_FLAG
    | CERT_CHAIN_POLICY_IGNORE_CA_REV_UNKNOWN_FLAG
    | CERT_CHAIN_POLICY_IGNORE_ROOT_REV_UNKNOWN_FLAG
)
CERT_CHAIN_POLICY_ALLOW_TESTROOT_FLAG = 0x00008000
CERT_CHAIN_POLICY_TRUST_TESTROOT_FLAG = 0x00004000
CRYPT_OID_VERIFY_CERTIFICATE_CHAIN_POLICY_FUNC = "CertDllVerifyCertificateChainPolicy"
AUTHTYPE_CLIENT = 1
AUTHTYPE_SERVER = 2
BASIC_CONSTRAINTS_CERT_CHAIN_POLICY_CA_FLAG = -2147483648
BASIC_CONSTRAINTS_CERT_CHAIN_POLICY_END_ENTITY_FLAG = 0x40000000
MICROSOFT_ROOT_CERT_CHAIN_POLICY_ENABLE_TEST_ROOT_FLAG = 0x00010000
CRYPT_STRING_BASE64HEADER = 0x00000000
CRYPT_STRING_BASE64 = 0x00000001
CRYPT_STRING_BINARY = 0x00000002
CRYPT_STRING_BASE64REQUESTHEADER = 0x00000003
CRYPT_STRING_HEX = 0x00000004
CRYPT_STRING_HEXASCII = 0x00000005
CRYPT_STRING_BASE64_ANY = 0x00000006
CRYPT_STRING_ANY = 0x00000007
CRYPT_STRING_HEX_ANY = 0x00000008
CRYPT_STRING_BASE64X509CRLHEADER = 0x00000009
CRYPT_STRING_HEXADDR = 0x0000000A
CRYPT_STRING_HEXASCIIADDR = 0x0000000B
CRYPT_STRING_NOCR = -2147483648
CRYPT_USER_KEYSET = 0x00001000
PKCS12_IMPORT_RESERVED_MASK = -65536
REPORT_NO_PRIVATE_KEY = 0x0001
REPORT_NOT_ABLE_TO_EXPORT_PRIVATE_KEY = 0x0002
EXPORT_PRIVATE_KEYS = 0x0004
PKCS12_EXPORT_RESERVED_MASK = -65536

# Certificate store provider types used with CertOpenStore
CERT_STORE_PROV_MSG = 1
CERT_STORE_PROV_MEMORY = 2
CERT_STORE_PROV_FILE = 3
CERT_STORE_PROV_REG = 4
CERT_STORE_PROV_PKCS7 = 5
CERT_STORE_PROV_SERIALIZED = 6
CERT_STORE_PROV_FILENAME = 8
CERT_STORE_PROV_SYSTEM = 10
CERT_STORE_PROV_COLLECTION = 11
CERT_STORE_PROV_SYSTEM_REGISTRY = 13
CERT_STORE_PROV_PHYSICAL = 14
CERT_STORE_PROV_SMART_CARD = 15
CERT_STORE_PROV_LDAP = 16

URL_OID_CERTIFICATE_ISSUER = 1
URL_OID_CERTIFICATE_CRL_DIST_POINT = 2
URL_OID_CTL_ISSUER = 3
URL_OID_CTL_NEXT_UPDATE = 4
URL_OID_CRL_ISSUER = 5
URL_OID_CERTIFICATE_FRESHEST_CRL = 6
URL_OID_CRL_FRESHEST_CRL = 7
URL_OID_CROSS_CERT_DIST_POINT = 8
URL_OID_CERTIFICATE_OCSP = 9
URL_OID_CERTIFICATE_OCSP_AND_CRL_DIST_POINT = 10
URL_OID_CERTIFICATE_CRL_DIST_POINT_AND_OCSP = 11
URL_OID_CROSS_CERT_SUBJECT_INFO_ACCESS = 12
URL_OID_CERTIFICATE_ONLY_OCSP = 13

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\win32\lib\win32cryptcon.py ===
# Generated by h2py from WinCrypt.h
def GET_ALG_CLASS(x):
    return x & (7 << 13)


def GET_ALG_TYPE(x):
    return x & (15 << 9)


def GET_ALG_SID(x):
    return x & (511)


ALG_CLASS_ANY = 0
ALG_CLASS_SIGNATURE = 1 << 13
ALG_CLASS_MSG_ENCRYPT = 2 << 13
ALG_CLASS_DATA_ENCRYPT = 3 << 13
ALG_CLASS_HASH = 4 << 13
ALG_CLASS_KEY_EXCHANGE = 5 << 13
ALG_CLASS_ALL = 7 << 13
ALG_TYPE_ANY = 0
ALG_TYPE_DSS = 1 << 9
ALG_TYPE_RSA = 2 << 9
ALG_TYPE_BLOCK = 3 << 9
ALG_TYPE_STREAM = 4 << 9
ALG_TYPE_DH = 5 << 9
ALG_TYPE_SECURECHANNEL = 6 << 9
ALG_SID_ANY = 0
ALG_SID_RSA_ANY = 0
ALG_SID_RSA_PKCS = 1
ALG_SID_RSA_MSATWORK = 2
ALG_SID_RSA_ENTRUST = 3
ALG_SID_RSA_PGP = 4
ALG_SID_DSS_ANY = 0
ALG_SID_DSS_PKCS = 1
ALG_SID_DSS_DMS = 2
ALG_SID_DES = 1
ALG_SID_3DES = 3
ALG_SID_DESX = 4
ALG_SID_IDEA = 5
ALG_SID_CAST = 6
ALG_SID_SAFERSK64 = 7
ALG_SID_SAFERSK128 = 8
ALG_SID_3DES_112 = 9
ALG_SID_CYLINK_MEK = 12
ALG_SID_RC5 = 13
ALG_SID_AES_128 = 14
ALG_SID_AES_192 = 15
ALG_SID_AES_256 = 16
ALG_SID_AES = 17
ALG_SID_SKIPJACK = 10
ALG_SID_TEK = 11
CRYPT_MODE_CBCI = 6
CRYPT_MODE_CFBP = 7
CRYPT_MODE_OFBP = 8
CRYPT_MODE_CBCOFM = 9
CRYPT_MODE_CBCOFMI = 10
ALG_SID_RC2 = 2
ALG_SID_RC4 = 1
ALG_SID_SEAL = 2
ALG_SID_DH_SANDF = 1
ALG_SID_DH_EPHEM = 2
ALG_SID_AGREED_KEY_ANY = 3
ALG_SID_KEA = 4
ALG_SID_MD2 = 1
ALG_SID_MD4 = 2
ALG_SID_MD5 = 3
ALG_SID_SHA = 4
ALG_SID_SHA1 = 4
ALG_SID_MAC = 5
ALG_SID_RIPEMD = 6
ALG_SID_RIPEMD160 = 7
ALG_SID_SSL3SHAMD5 = 8
ALG_SID_HMAC = 9
ALG_SID_TLS1PRF = 10
ALG_SID_HASH_REPLACE_OWF = 11
ALG_SID_SHA_256 = 12
ALG_SID_SHA_384 = 13
ALG_SID_SHA_512 = 14
ALG_SID_SSL3_MASTER = 1
ALG_SID_SCHANNEL_MASTER_HASH = 2
ALG_SID_SCHANNEL_MAC_KEY = 3
ALG_SID_PCT1_MASTER = 4
ALG_SID_SSL2_MASTER = 5
ALG_SID_TLS1_MASTER = 6
ALG_SID_SCHANNEL_ENC_KEY = 7
ALG_SID_EXAMPLE = 80
CALG_MD2 = ALG_CLASS_HASH | ALG_TYPE_ANY | ALG_SID_MD2
CALG_MD4 = ALG_CLASS_HASH | ALG_TYPE_ANY | ALG_SID_MD4
CALG_MD5 = ALG_CLASS_HASH | ALG_TYPE_ANY | ALG_SID_MD5
CALG_SHA = ALG_CLASS_HASH | ALG_TYPE_ANY | ALG_SID_SHA
CALG_SHA1 = ALG_CLASS_HASH | ALG_TYPE_ANY | ALG_SID_SHA1
CALG_MAC = ALG_CLASS_HASH | ALG_TYPE_ANY | ALG_SID_MAC
CALG_RSA_SIGN = ALG_CLASS_SIGNATURE | ALG_TYPE_RSA | ALG_SID_RSA_ANY
CALG_DSS_SIGN = ALG_CLASS_SIGNATURE | ALG_TYPE_DSS | ALG_SID_DSS_ANY
CALG_NO_SIGN = ALG_CLASS_SIGNATURE | ALG_TYPE_ANY | ALG_SID_ANY
CALG_RSA_KEYX = ALG_CLASS_KEY_EXCHANGE | ALG_TYPE_RSA | ALG_SID_RSA_ANY
CALG_DES = ALG_CLASS_DATA_ENCRYPT | ALG_TYPE_BLOCK | ALG_SID_DES
CALG_3DES_112 = ALG_CLASS_DATA_ENCRYPT | ALG_TYPE_BLOCK | ALG_SID_3DES_112
CALG_3DES = ALG_CLASS_DATA_ENCRYPT | ALG_TYPE_BLOCK | ALG_SID_3DES
CALG_DESX = ALG_CLASS_DATA_ENCRYPT | ALG_TYPE_BLOCK | ALG_SID_DESX
CALG_RC2 = ALG_CLASS_DATA_ENCRYPT | ALG_TYPE_BLOCK | ALG_SID_RC2
CALG_RC4 = ALG_CLASS_DATA_ENCRYPT | ALG_TYPE_STREAM | ALG_SID_RC4
CALG_SEAL = ALG_CLASS_DATA_ENCRYPT | ALG_TYPE_STREAM | ALG_SID_SEAL
CALG_DH_SF = ALG_CLASS_KEY_EXCHANGE | ALG_TYPE_DH | ALG_SID_DH_SANDF
CALG_DH_EPHEM = ALG_CLASS_KEY_EXCHANGE | ALG_TYPE_DH | ALG_SID_DH_EPHEM
CALG_AGREEDKEY_ANY = ALG_CLASS_KEY_EXCHANGE | ALG_TYPE_DH | ALG_SID_AGREED_KEY_ANY
CALG_KEA_KEYX = ALG_CLASS_KEY_EXCHANGE | ALG_TYPE_DH | ALG_SID_KEA
CALG_HUGHES_MD5 = ALG_CLASS_KEY_EXCHANGE | ALG_TYPE_ANY | ALG_SID_MD5
CALG_SKIPJACK = ALG_CLASS_DATA_ENCRYPT | ALG_TYPE_BLOCK | ALG_SID_SKIPJACK
CALG_TEK = ALG_CLASS_DATA_ENCRYPT | ALG_TYPE_BLOCK | ALG_SID_TEK
CALG_CYLINK_MEK = ALG_CLASS_DATA_ENCRYPT | ALG_TYPE_BLOCK | ALG_SID_CYLINK_MEK
CALG_SSL3_SHAMD5 = ALG_CLASS_HASH | ALG_TYPE_ANY | ALG_SID_SSL3SHAMD5
CALG_SSL3_MASTER = ALG_CLASS_MSG_ENCRYPT | ALG_TYPE_SECURECHANNEL | ALG_SID_SSL3_MASTER
CALG_SCHANNEL_MASTER_HASH = (
    ALG_CLASS_MSG_ENCRYPT | ALG_TYPE_SECURECHANNEL | ALG_SID_SCHANNEL_MASTER_HASH
)
CALG_SCHANNEL_MAC_KEY = (
    ALG_CLASS_MSG_ENCRYPT | ALG_TYPE_SECURECHANNEL | ALG_SID_SCHANNEL_MAC_KEY
)
CALG_SCHANNEL_ENC_KEY = (
    ALG_CLASS_MSG_ENCRYPT | ALG_TYPE_SECURECHANNEL | ALG_SID_SCHANNEL_ENC_KEY
)
CALG_PCT1_MASTER = ALG_CLASS_MSG_ENCRYPT | ALG_TYPE_SECURECHANNEL | ALG_SID_PCT1_MASTER
CALG_SSL2_MASTER = ALG_CLASS_MSG_ENCRYPT | ALG_TYPE_SECURECHANNEL | ALG_SID_SSL2_MASTER
CALG_TLS1_MASTER = ALG_CLASS_MSG_ENCRYPT | ALG_TYPE_SECURECHANNEL | ALG_SID_TLS1_MASTER
CALG_RC5 = ALG_CLASS_DATA_ENCRYPT | ALG_TYPE_BLOCK | ALG_SID_RC5
CALG_HMAC = ALG_CLASS_HASH | ALG_TYPE_ANY | ALG_SID_HMAC
CALG_TLS1PRF = ALG_CLASS_HASH | ALG_TYPE_ANY | ALG_SID_TLS1PRF
CALG_HASH_REPLACE_OWF = ALG_CLASS_HASH | ALG_TYPE_ANY | ALG_SID_HASH_REPLACE_OWF
CALG_AES_128 = ALG_CLASS_DATA_ENCRYPT | ALG_TYPE_BLOCK | ALG_SID_AES_128
CALG_AES_192 = ALG_CLASS_DATA_ENCRYPT | ALG_TYPE_BLOCK | ALG_SID_AES_192
CALG_AES_256 = ALG_CLASS_DATA_ENCRYPT | ALG_TYPE_BLOCK | ALG_SID_AES_256
CALG_AES = ALG_CLASS_DATA_ENCRYPT | ALG_TYPE_BLOCK | ALG_SID_AES
CALG_SHA_256 = ALG_CLASS_HASH | ALG_TYPE_ANY | ALG_SID_SHA_256
CALG_SHA_384 = ALG_CLASS_HASH | ALG_TYPE_ANY | ALG_SID_SHA_384
CALG_SHA_512 = ALG_CLASS_HASH | ALG_TYPE_ANY | ALG_SID_SHA_512
CRYPT_VERIFYCONTEXT = -268435456
CRYPT_NEWKEYSET = 0x00000008
CRYPT_DELETEKEYSET = 0x00000010
CRYPT_MACHINE_KEYSET = 0x00000020
CRYPT_SILENT = 0x00000040
CRYPT_EXPORTABLE = 0x00000001
CRYPT_USER_PROTECTED = 0x00000002
CRYPT_CREATE_SALT = 0x00000004
CRYPT_UPDATE_KEY = 0x00000008
CRYPT_NO_SALT = 0x00000010
CRYPT_PREGEN = 0x00000040
CRYPT_RECIPIENT = 0x00000010
CRYPT_INITIATOR = 0x00000040
CRYPT_ONLINE = 0x00000080
CRYPT_SF = 0x00000100
CRYPT_CREATE_IV = 0x00000200
CRYPT_KEK = 0x00000400
CRYPT_DATA_KEY = 0x00000800
CRYPT_VOLATILE = 0x00001000
CRYPT_SGCKEY = 0x00002000
CRYPT_ARCHIVABLE = 0x00004000
RSA1024BIT_KEY = 0x04000000
CRYPT_SERVER = 0x00000400
KEY_LENGTH_MASK = -65536
CRYPT_Y_ONLY = 0x00000001
CRYPT_SSL2_FALLBACK = 0x00000002
CRYPT_DESTROYKEY = 0x00000004
CRYPT_OAEP = 0x00000040
CRYPT_BLOB_VER3 = 0x00000080
CRYPT_IPSEC_HMAC_KEY = 0x00000100
CRYPT_DECRYPT_RSA_NO_PADDING_CHECK = 0x00000020
CRYPT_SECRETDIGEST = 0x00000001
CRYPT_OWF_REPL_LM_HASH = 0x00000001
CRYPT_LITTLE_ENDIAN = 0x00000001
CRYPT_NOHASHOID = 0x00000001
CRYPT_TYPE2_FORMAT = 0x00000002
CRYPT_X931_FORMAT = 0x00000004
CRYPT_MACHINE_DEFAULT = 0x00000001
CRYPT_USER_DEFAULT = 0x00000002
CRYPT_DELETE_DEFAULT = 0x00000004
SIMPLEBLOB = 0x1
PUBLICKEYBLOB = 0x6
PRIVATEKEYBLOB = 0x7
PLAINTEXTKEYBLOB = 0x8
OPAQUEKEYBLOB = 0x9
PUBLICKEYBLOBEX = 0xA
SYMMETRICWRAPKEYBLOB = 0xB
AT_KEYEXCHANGE = 1
AT_SIGNATURE = 2
CRYPT_USERDATA = 1
KP_IV = 1
KP_SALT = 2
KP_PADDING = 3
KP_MODE = 4
KP_MODE_BITS = 5
KP_PERMISSIONS = 6
KP_ALGID = 7
KP_BLOCKLEN = 8
KP_KEYLEN = 9
KP_SALT_EX = 10
KP_P = 11
KP_G = 12
KP_Q = 13
KP_X = 14
KP_Y = 15
KP_RA = 16
KP_RB = 17
KP_INFO = 18
KP_EFFECTIVE_KEYLEN = 19
KP_SCHANNEL_ALG = 20
KP_CLIENT_RANDOM = 21
KP_SERVER_RANDOM = 22
KP_RP = 23
KP_PRECOMP_MD5 = 24
KP_PRECOMP_SHA = 25
KP_CERTIFICATE = 26
KP_CLEAR_KEY = 27
KP_PUB_EX_LEN = 28
KP_PUB_EX_VAL = 29
KP_KEYVAL = 30
KP_ADMIN_PIN = 31
KP_KEYEXCHANGE_PIN = 32
KP_SIGNATURE_PIN = 33
KP_PREHASH = 34
KP_ROUNDS = 35
KP_OAEP_PARAMS = 36
KP_CMS_KEY_INFO = 37
KP_CMS_DH_KEY_INFO = 38
KP_PUB_PARAMS = 39
KP_VERIFY_PARAMS = 40
KP_HIGHEST_VERSION = 41
KP_GET_USE_COUNT = 42
PKCS5_PADDING = 1
RANDOM_PADDING = 2
ZERO_PADDING = 3
CRYPT_MODE_CBC = 1
CRYPT_MODE_ECB = 2
CRYPT_MODE_OFB = 3
CRYPT_MODE_CFB = 4
CRYPT_MODE_CTS = 5
CRYPT_ENCRYPT = 0x0001
CRYPT_DECRYPT = 0x0002
CRYPT_EXPORT = 0x0004
CRYPT_READ = 0x0008
CRYPT_WRITE = 0x0010
CRYPT_MAC = 0x0020
CRYPT_EXPORT_KEY = 0x0040
CRYPT_IMPORT_KEY = 0x0080
CRYPT_ARCHIVE = 0x0100
HP_ALGID = 0x0001
HP_HASHVAL = 0x0002
HP_HASHSIZE = 0x0004
HP_HMAC_INFO = 0x0005
HP_TLS1PRF_LABEL = 0x0006
HP_TLS1PRF_SEED = 0x0007

CRYPT_FAILED = 0
CRYPT_SUCCEED = 1


def RCRYPT_SUCCEEDED(rt):
    return (rt) == CRYPT_SUCCEED


def RCRYPT_FAILED(rt):
    return (rt) == CRYPT_FAILED


PP_ENUMALGS = 1
PP_ENUMCONTAINERS = 2
PP_IMPTYPE = 3
PP_NAME = 4
PP_VERSION = 5
PP_CONTAINER = 6
PP_CHANGE_PASSWORD = 7
PP_KEYSET_SEC_DESCR = 8
PP_CERTCHAIN = 9
PP_KEY_TYPE_SUBTYPE = 10
PP_PROVTYPE = 16
PP_KEYSTORAGE = 17
PP_APPLI_CERT = 18
PP_SYM_KEYSIZE = 19
PP_SESSION_KEYSIZE = 20
PP_UI_PROMPT = 21
PP_ENUMALGS_EX = 22
PP_ENUMMANDROOTS = 25
PP_ENUMELECTROOTS = 26
PP_KEYSET_TYPE = 27
PP_ADMIN_PIN = 31
PP_KEYEXCHANGE_PIN = 32
PP_SIGNATURE_PIN = 33
PP_SIG_KEYSIZE_INC = 34
PP_KEYX_KEYSIZE_INC = 35
PP_UNIQUE_CONTAINER = 36
PP_SGC_INFO = 37
PP_USE_HARDWARE_RNG = 38
PP_KEYSPEC = 39
PP_ENUMEX_SIGNING_PROT = 40
PP_CRYPT_COUNT_KEY_USE = 41
CRYPT_FIRST = 1
CRYPT_NEXT = 2
CRYPT_SGC_ENUM = 4
CRYPT_IMPL_HARDWARE = 1
CRYPT_IMPL_SOFTWARE = 2
CRYPT_IMPL_MIXED = 3
CRYPT_IMPL_UNKNOWN = 4
CRYPT_IMPL_REMOVABLE = 8
CRYPT_SEC_DESCR = 0x00000001
CRYPT_PSTORE = 0x00000002
CRYPT_UI_PROMPT = 0x00000004
CRYPT_FLAG_PCT1 = 0x0001
CRYPT_FLAG_SSL2 = 0x0002
CRYPT_FLAG_SSL3 = 0x0004
CRYPT_FLAG_TLS1 = 0x0008
CRYPT_FLAG_IPSEC = 0x0010
CRYPT_FLAG_SIGNING = 0x0020
CRYPT_SGC = 0x0001
CRYPT_FASTSGC = 0x0002
PP_CLIENT_HWND = 1
PP_CONTEXT_INFO = 11
PP_KEYEXCHANGE_KEYSIZE = 12
PP_SIGNATURE_KEYSIZE = 13
PP_KEYEXCHANGE_ALG = 14
PP_SIGNATURE_ALG = 15
PP_DELETEKEY = 24
PROV_RSA_FULL = 1
PROV_RSA_SIG = 2
PROV_DSS = 3
PROV_FORTEZZA = 4
PROV_MS_EXCHANGE = 5
PROV_SSL = 6
PROV_RSA_SCHANNEL = 12
PROV_DSS_DH = 13
PROV_EC_ECDSA_SIG = 14
PROV_EC_ECNRA_SIG = 15
PROV_EC_ECDSA_FULL = 16
PROV_EC_ECNRA_FULL = 17
PROV_DH_SCHANNEL = 18
PROV_SPYRUS_LYNKS = 20
PROV_RNG = 21
PROV_INTEL_SEC = 22
PROV_REPLACE_OWF = 23
PROV_RSA_AES = 24
MS_DEF_PROV_A = "Microsoft Base Cryptographic Provider v1.0"
MS_DEF_PROV = MS_DEF_PROV_A
MS_ENHANCED_PROV_A = "Microsoft Enhanced Cryptographic Provider v1.0"
MS_ENHANCED_PROV = MS_ENHANCED_PROV_A
MS_STRONG_PROV_A = "Microsoft Strong Cryptographic Provider"
MS_STRONG_PROV = MS_STRONG_PROV_A
MS_DEF_RSA_SIG_PROV_A = "Microsoft RSA Signature Cryptographic Provider"
MS_DEF_RSA_SIG_PROV = MS_DEF_RSA_SIG_PROV_A
MS_DEF_RSA_SCHANNEL_PROV_A = "Microsoft RSA SChannel Cryptographic Provider"
MS_DEF_RSA_SCHANNEL_PROV = MS_DEF_RSA_SCHANNEL_PROV_A
MS_DEF_DSS_PROV_A = "Microsoft Base DSS Cryptographic Provider"
MS_DEF_DSS_PROV = MS_DEF_DSS_PROV_A
MS_DEF_DSS_DH_PROV_A = "Microsoft Base DSS and Diffie-Hellman Cryptographic Provider"
MS_DEF_DSS_DH_PROV = MS_DEF_DSS_DH_PROV_A
MS_ENH_DSS_DH_PROV_A = (
    "Microsoft Enhanced DSS and Diffie-Hellman Cryptographic Provider"
)
MS_ENH_DSS_DH_PROV = MS_ENH_DSS_DH_PROV_A
MS_DEF_DH_SCHANNEL_PROV_A = "Microsoft DH SChannel Cryptographic Provider"
MS_DEF_DH_SCHANNEL_PROV = MS_DEF_DH_SCHANNEL_PROV_A
MS_SCARD_PROV_A = "Microsoft Base Smart Card Crypto Provider"
MS_SCARD_PROV = MS_SCARD_PROV_A
MS_ENH_RSA_AES_PROV_A = "Microsoft Enhanced RSA and AES Cryptographic Provider"
MS_ENH_RSA_AES_PROV = MS_ENH_RSA_AES_PROV_A
MAXUIDLEN = 64
EXPO_OFFLOAD_REG_VALUE = "ExpoOffload"
EXPO_OFFLOAD_FUNC_NAME = "OffloadModExpo"
szKEY_CRYPTOAPI_PRIVATE_KEY_OPTIONS = "Software\\Policies\\Microsoft\\Cryptography"
szFORCE_KEY_PROTECTION = "ForceKeyProtection"
dwFORCE_KEY_PROTECTION_DISABLED = 0x0
dwFORCE_KEY_PROTECTION_USER_SELECT = 0x1
dwFORCE_KEY_PROTECTION_HIGH = 0x2
szKEY_CACHE_ENABLED = "CachePrivateKeys"
szKEY_CACHE_SECONDS = "PrivateKeyLifetimeSeconds"
CUR_BLOB_VERSION = 2
SCHANNEL_MAC_KEY = 0x00000000
SCHANNEL_ENC_KEY = 0x00000001
INTERNATIONAL_USAGE = 0x00000001
szOID_RSA = "1.2.840.113549"
szOID_PKCS = "1.2.840.113549.1"
szOID_RSA_HASH = "1.2.840.113549.2"
szOID_RSA_ENCRYPT = "1.2.840.113549.3"
szOID_PKCS_1 = "1.2.840.113549.1.1"
szOID_PKCS_2 = "1.2.840.113549.1.2"
szOID_PKCS_3 = "1.2.840.113549.1.3"
szOID_PKCS_4 = "1.2.840.113549.1.4"
szOID_PKCS_5 = "1.2.840.113549.1.5"
szOID_PKCS_6 = "1.2.840.113549.1.6"
szOID_PKCS_7 = "1.2.840.113549.1.7"
szOID_PKCS_8 = "1.2.840.113549.1.8"
szOID_PKCS_9 = "1.2.840.113549.1.9"
szOID_PKCS_10 = "1.2.840.113549.1.10"
szOID_PKCS_12 = "1.2.840.113549.1.12"
szOID_RSA_RSA = "1.2.840.113549.1.1.1"
szOID_RSA_MD2RSA = "1.2.840.113549.1.1.2"
szOID_RSA_MD4RSA = "1.2.840.113549.1.1.3"
szOID_RSA_MD5RSA = "1.2.840.113549.1.1.4"
szOID_RSA_SHA1RSA = "1.2.840.113549.1.1.5"
szOID_RSA_SETOAEP_RSA = "1.2.840.113549.1.1.6"
szOID_RSA_DH = "1.2.840.113549.1.3.1"
szOID_RSA_data = "1.2.840.113549.1.7.1"
szOID_RSA_signedData = "1.2.840.113549.1.7.2"
szOID_RSA_envelopedData = "1.2.840.113549.1.7.3"
szOID_RSA_signEnvData = "1.2.840.113549.1.7.4"
szOID_RSA_digestedData = "1.2.840.113549.1.7.5"
szOID_RSA_hashedData = "1.2.840.113549.1.7.5"
szOID_RSA_encryptedData = "1.2.840.113549.1.7.6"
szOID_RSA_emailAddr = "1.2.840.113549.1.9.1"
szOID_RSA_unstructName = "1.2.840.113549.1.9.2"
szOID_RSA_contentType = "1.2.840.113549.1.9.3"
szOID_RSA_messageDigest = "1.2.840.113549.1.9.4"
szOID_RSA_signingTime = "1.2.840.113549.1.9.5"
szOID_RSA_counterSign = "1.2.840.113549.1.9.6"
szOID_RSA_challengePwd = "1.2.840.113549.1.9.7"
szOID_RSA_unstructAddr = "1.2.840.113549.1.9.8"
szOID_RSA_extCertAttrs = "1.2.840.113549.1.9.9"
szOID_RSA_certExtensions = "1.2.840.113549.1.9.14"
szOID_RSA_SMIMECapabilities = "1.2.840.113549.1.9.15"
szOID_RSA_preferSignedData = "1.2.840.113549.1.9.15.1"
szOID_RSA_SMIMEalg = "1.2.840.113549.1.9.16.3"
szOID_RSA_SMIMEalgESDH = "1.2.840.113549.1.9.16.3.5"
szOID_RSA_SMIMEalgCMS3DESwrap = "1.2.840.113549.1.9.16.3.6"
szOID_RSA_SMIMEalgCMSRC2wrap = "1.2.840.113549.1.9.16.3.7"
szOID_RSA_MD2 = "1.2.840.113549.2.2"
szOID_RSA_MD4 = "1.2.840.113549.2.4"
szOID_RSA_MD5 = "1.2.840.113549.2.5"
szOID_RSA_RC2CBC = "1.2.840.113549.3.2"
szOID_RSA_RC4 = "1.2.840.113549.3.4"
szOID_RSA_DES_EDE3_CBC = "1.2.840.113549.3.7"
szOID_RSA_RC5_CBCPad = "1.2.840.113549.3.9"
szOID_ANSI_X942 = "1.2.840.10046"
szOID_ANSI_X942_DH = "1.2.840.10046.2.1"
szOID_X957 = "1.2.840.10040"
szOID_X957_DSA = "1.2.840.10040.4.1"
szOID_X957_SHA1DSA = "1.2.840.10040.4.3"
szOID_DS = "2.5"
szOID_DSALG = "2.5.8"
szOID_DSALG_CRPT = "2.5.8.1"
szOID_DSALG_HASH = "2.5.8.2"
szOID_DSALG_SIGN = "2.5.8.3"
szOID_DSALG_RSA = "2.5.8.1.1"
szOID_OIW = "1.3.14"
szOID_OIWSEC = "1.3.14.3.2"
szOID_OIWSEC_md4RSA = "1.3.14.3.2.2"
szOID_OIWSEC_md5RSA = "1.3.14.3.2.3"
szOID_OIWSEC_md4RSA2 = "1.3.14.3.2.4"
szOID_OIWSEC_desECB = "1.3.14.3.2.6"
szOID_OIWSEC_desCBC = "1.3.14.3.2.7"
szOID_OIWSEC_desOFB = "1.3.14.3.2.8"
szOID_OIWSEC_desCFB = "1.3.14.3.2.9"
szOID_OIWSEC_desMAC = "1.3.14.3.2.10"
szOID_OIWSEC_rsaSign = "1.3.14.3.2.11"
szOID_OIWSEC_dsa = "1.3.14.3.2.12"
szOID_OIWSEC_shaDSA = "1.3.14.3.2.13"
szOID_OIWSEC_mdc2RSA = "1.3.14.3.2.14"
szOID_OIWSEC_shaRSA = "1.3.14.3.2.15"
szOID_OIWSEC_dhCommMod = "1.3.14.3.2.16"
szOID_OIWSEC_desEDE = "1.3.14.3.2.17"
szOID_OIWSEC_sha = "1.3.14.3.2.18"
szOID_OIWSEC_mdc2 = "1.3.14.3.2.19"
szOID_OIWSEC_dsaComm = "1.3.14.3.2.20"
szOID_OIWSEC_dsaCommSHA = "1.3.14.3.2.21"
szOID_OIWSEC_rsaXchg = "1.3.14.3.2.22"
szOID_OIWSEC_keyHashSeal = "1.3.14.3.2.23"
szOID_OIWSEC_md2RSASign = "1.3.14.3.2.24"
szOID_OIWSEC_md5RSASign = "1.3.14.3.2.25"
szOID_OIWSEC_sha1 = "1.3.14.3.2.26"
szOID_OIWSEC_dsaSHA1 = "1.3.14.3.2.27"
szOID_OIWSEC_dsaCommSHA1 = "1.3.14.3.2.28"
szOID_OIWSEC_sha1RSASign = "1.3.14.3.2.29"
szOID_OIWDIR = "1.3.14.7.2"
szOID_OIWDIR_CRPT = "1.3.14.7.2.1"
szOID_OIWDIR_HASH = "1.3.14.7.2.2"
szOID_OIWDIR_SIGN = "1.3.14.7.2.3"
szOID_OIWDIR_md2 = "1.3.14.7.2.2.1"
szOID_OIWDIR_md2RSA = "1.3.14.7.2.3.1"
szOID_INFOSEC = "2.16.840.1.101.2.1"
szOID_INFOSEC_sdnsSignature = "2.16.840.1.101.2.1.1.1"
szOID_INFOSEC_mosaicSignature = "2.16.840.1.101.2.1.1.2"
szOID_INFOSEC_sdnsConfidentiality = "2.16.840.1.101.2.1.1.3"
szOID_INFOSEC_mosaicConfidentiality = "2.16.840.1.101.2.1.1.4"
szOID_INFOSEC_sdnsIntegrity = "2.16.840.1.101.2.1.1.5"
szOID_INFOSEC_mosaicIntegrity = "2.16.840.1.101.2.1.1.6"
szOID_INFOSEC_sdnsTokenProtection = "2.16.840.1.101.2.1.1.7"
szOID_INFOSEC_mosaicTokenProtection = "2.16.840.1.101.2.1.1.8"
szOID_INFOSEC_sdnsKeyManagement = "2.16.840.1.101.2.1.1.9"
szOID_INFOSEC_mosaicKeyManagement = "2.16.840.1.101.2.1.1.10"
szOID_INFOSEC_sdnsKMandSig = "2.16.840.1.101.2.1.1.11"
szOID_INFOSEC_mosaicKMandSig = "2.16.840.1.101.2.1.1.12"
szOID_INFOSEC_SuiteASignature = "2.16.840.1.101.2.1.1.13"
szOID_INFOSEC_SuiteAConfidentiality = "2.16.840.1.101.2.1.1.14"
szOID_INFOSEC_SuiteAIntegrity = "2.16.840.1.101.2.1.1.15"
szOID_INFOSEC_SuiteATokenProtection = "2.16.840.1.101.2.1.1.16"
szOID_INFOSEC_SuiteAKeyManagement = "2.16.840.1.101.2.1.1.17"
szOID_INFOSEC_SuiteAKMandSig = "2.16.840.1.101.2.1.1.18"
szOID_INFOSEC_mosaicUpdatedSig = "2.16.840.1.101.2.1.1.19"
szOID_INFOSEC_mosaicKMandUpdSig = "2.16.840.1.101.2.1.1.20"
szOID_INFOSEC_mosaicUpdatedInteg = "2.16.840.1.101.2.1.1.21"
szOID_COMMON_NAME = "2.5.4.3"
szOID_SUR_NAME = "2.5.4.4"
szOID_DEVICE_SERIAL_NUMBER = "2.5.4.5"
szOID_COUNTRY_NAME = "2.5.4.6"
szOID_LOCALITY_NAME = "2.5.4.7"
szOID_STATE_OR_PROVINCE_NAME = "2.5.4.8"
szOID_STREET_ADDRESS = "2.5.4.9"
szOID_ORGANIZATION_NAME = "2.5.4.10"
szOID_ORGANIZATIONAL_UNIT_NAME = "2.5.4.11"
szOID_TITLE = "2.5.4.12"
szOID_DESCRIPTION = "2.5.4.13"
szOID_SEARCH_GUIDE = "2.5.4.14"
szOID_BUSINESS_CATEGORY = "2.5.4.15"
szOID_POSTAL_ADDRESS = "2.5.4.16"
szOID_POSTAL_CODE = "2.5.4.17"
szOID_POST_OFFICE_BOX = "2.5.4.18"
szOID_PHYSICAL_DELIVERY_OFFICE_NAME = "2.5.4.19"
szOID_TELEPHONE_NUMBER = "2.5.4.20"
szOID_TELEX_NUMBER = "2.5.4.21"
szOID_TELETEXT_TERMINAL_IDENTIFIER = "2.5.4.22"
szOID_FACSIMILE_TELEPHONE_NUMBER = "2.5.4.23"
szOID_X21_ADDRESS = "2.5.4.24"
szOID_INTERNATIONAL_ISDN_NUMBER = "2.5.4.25"
szOID_REGISTERED_ADDRESS = "2.5.4.26"
szOID_DESTINATION_INDICATOR = "2.5.4.27"
szOID_PREFERRED_DELIVERY_METHOD = "2.5.4.28"
szOID_PRESENTATION_ADDRESS = "2.5.4.29"
szOID_SUPPORTED_APPLICATION_CONTEXT = "2.5.4.30"
szOID_MEMBER = "2.5.4.31"
szOID_OWNER = "2.5.4.32"
szOID_ROLE_OCCUPANT = "2.5.4.33"
szOID_SEE_ALSO = "2.5.4.34"
szOID_USER_PASSWORD = "2.5.4.35"
szOID_USER_CERTIFICATE = "2.5.4.36"
szOID_CA_CERTIFICATE = "2.5.4.37"
szOID_AUTHORITY_REVOCATION_LIST = "2.5.4.38"
szOID_CERTIFICATE_REVOCATION_LIST = "2.5.4.39"
szOID_CROSS_CERTIFICATE_PAIR = "2.5.4.40"
szOID_GIVEN_NAME = "2.5.4.42"
szOID_INITIALS = "2.5.4.43"
szOID_DN_QUALIFIER = "2.5.4.46"
szOID_DOMAIN_COMPONENT = "0.9.2342.19200300.100.1.25"
szOID_PKCS_12_FRIENDLY_NAME_ATTR = "1.2.840.113549.1.9.20"
szOID_PKCS_12_LOCAL_KEY_ID = "1.2.840.113549.1.9.21"
szOID_PKCS_12_KEY_PROVIDER_NAME_ATTR = "1.3.6.1.4.1.311.17.1"
szOID_LOCAL_MACHINE_KEYSET = "1.3.6.1.4.1.311.17.2"
szOID_KEYID_RDN = "1.3.6.1.4.1.311.10.7.1"
CERT_RDN_ANY_TYPE = 0
CERT_RDN_ENCODED_BLOB = 1
CERT_RDN_OCTET_STRING = 2
CERT_RDN_NUMERIC_STRING = 3
CERT_RDN_PRINTABLE_STRING = 4
CERT_RDN_TELETEX_STRING = 5
CERT_RDN_T61_STRING = 5
CERT_RDN_VIDEOTEX_STRING = 6
CERT_RDN_IA5_STRING = 7
CERT_RDN_GRAPHIC_STRING = 8
CERT_RDN_VISIBLE_STRING = 9
CERT_RDN_ISO646_STRING = 9
CERT_RDN_GENERAL_STRING = 10
CERT_RDN_UNIVERSAL_STRING = 11
CERT_RDN_INT4_STRING = 11
CERT_RDN_BMP_STRING = 12
CERT_RDN_UNICODE_STRING = 12
CERT_RDN_UTF8_STRING = 13
CERT_RDN_TYPE_MASK = 0x000000FF
CERT_RDN_FLAGS_MASK = -16777216
CERT_RDN_ENABLE_T61_UNICODE_FLAG = -2147483648
CERT_RDN_ENABLE_UTF8_UNICODE_FLAG = 0x20000000
CERT_RDN_DISABLE_CHECK_TYPE_FLAG = 0x40000000
CERT_RDN_DISABLE_IE4_UTF8_FLAG = 0x01000000
CERT_RSA_PUBLIC_KEY_OBJID = szOID_RSA_RSA
CERT_DEFAULT_OID_PUBLIC_KEY_SIGN = szOID_RSA_RSA
CERT_DEFAULT_OID_PUBLIC_KEY_XCHG = szOID_RSA_RSA
CERT_V1 = 0
CERT_V2 = 1
CERT_V3 = 2
CERT_INFO_VERSION_FLAG = 1
CERT_INFO_SERIAL_NUMBER_FLAG = 2
CERT_INFO_SIGNATURE_ALGORITHM_FLAG = 3
CERT_INFO_ISSUER_FLAG = 4
CERT_INFO_NOT_BEFORE_FLAG = 5
CERT_INFO_NOT_AFTER_FLAG = 6
CERT_INFO_SUBJECT_FLAG = 7
CERT_INFO_SUBJECT_PUBLIC_KEY_INFO_FLAG = 8
CERT_INFO_ISSUER_UNIQUE_ID_FLAG = 9
CERT_INFO_SUBJECT_UNIQUE_ID_FLAG = 10
CERT_INFO_EXTENSION_FLAG = 11
CRL_V1 = 0
CRL_V2 = 1
CERT_REQUEST_V1 = 0
CERT_KEYGEN_REQUEST_V1 = 0
CTL_V1 = 0
CERT_ENCODING_TYPE_MASK = 0x0000FFFF
CMSG_ENCODING_TYPE_MASK = -65536


def GET_CERT_ENCODING_TYPE(X):
    return X & CERT_ENCODING_TYPE_MASK


def GET_CMSG_ENCODING_TYPE(X):
    return X & CMSG_ENCODING_TYPE_MASK


CRYPT_ASN_ENCODING = 0x00000001
CRYPT_NDR_ENCODING = 0x00000002
X509_ASN_ENCODING = 0x00000001
X509_NDR_ENCODING = 0x00000002
PKCS_7_ASN_ENCODING = 0x00010000
PKCS_7_NDR_ENCODING = 0x00020000
CRYPT_FORMAT_STR_MULTI_LINE = 0x0001
CRYPT_FORMAT_STR_NO_HEX = 0x0010
CRYPT_FORMAT_SIMPLE = 0x0001
CRYPT_FORMAT_X509 = 0x0002
CRYPT_FORMAT_OID = 0x0004
CRYPT_FORMAT_RDN_SEMICOLON = 0x0100
CRYPT_FORMAT_RDN_CRLF = 0x0200
CRYPT_FORMAT_RDN_UNQUOTE = 0x0400
CRYPT_FORMAT_RDN_REVERSE = 0x0800
CRYPT_FORMAT_COMMA = 0x1000
CRYPT_FORMAT_SEMICOLON = CRYPT_FORMAT_RDN_SEMICOLON
CRYPT_FORMAT_CRLF = CRYPT_FORMAT_RDN_CRLF
CRYPT_ENCODE_NO_SIGNATURE_BYTE_REVERSAL_FLAG = 0x8
CRYPT_ENCODE_ALLOC_FLAG = 0x8000
CRYPT_UNICODE_NAME_ENCODE_ENABLE_T61_UNICODE_FLAG = CERT_RDN_ENABLE_T61_UNICODE_FLAG
CRYPT_UNICODE_NAME_ENCODE_ENABLE_UTF8_UNICODE_FLAG = CERT_RDN_ENABLE_UTF8_UNICODE_FLAG
CRYPT_UNICODE_NAME_ENCODE_DISABLE_CHECK_TYPE_FLAG = CERT_RDN_DISABLE_CHECK_TYPE_FLAG
CRYPT_SORTED_CTL_ENCODE_HASHED_SUBJECT_IDENTIFIER_FLAG = 0x10000
CRYPT_DECODE_NOCOPY_FLAG = 0x1
CRYPT_DECODE_TO_BE_SIGNED_FLAG = 0x2
CRYPT_DECODE_SHARE_OID_STRING_FLAG = 0x4
CRYPT_DECODE_NO_SIGNATURE_BYTE_REVERSAL_FLAG = 0x8
CRYPT_DECODE_ALLOC_FLAG = 0x8000
CRYPT_UNICODE_NAME_DECODE_DISABLE_IE4_UTF8_FLAG = CERT_RDN_DISABLE_IE4_UTF8_FLAG

CRYPT_ENCODE_DECODE_NONE = 0
X509_CERT = 1
X509_CERT_TO_BE_SIGNED = 2
X509_CERT_CRL_TO_BE_SIGNED = 3
X509_CERT_REQUEST_TO_BE_SIGNED = 4
X509_EXTENSIONS = 5
X509_NAME_VALUE = 6
X509_NAME = 7
X509_PUBLIC_KEY_INFO = 8
X509_AUTHORITY_KEY_ID = 9
X509_KEY_ATTRIBUTES = 10
X509_KEY_USAGE_RESTRICTION = 11
X509_ALTERNATE_NAME = 12
X509_BASIC_CONSTRAINTS = 13
X509_KEY_USAGE = 14
X509_BASIC_CONSTRAINTS2 = 15
X509_CERT_POLICIES = 16
PKCS_UTC_TIME = 17
PKCS_TIME_REQUEST = 18
RSA_CSP_PUBLICKEYBLOB = 19
X509_UNICODE_NAME = 20
X509_KEYGEN_REQUEST_TO_BE_SIGNED = 21
PKCS_ATTRIBUTE = 22
PKCS_CONTENT_INFO_SEQUENCE_OF_ANY = 23
X509_UNICODE_NAME_VALUE = 24
X509_ANY_STRING = X509_NAME_VALUE
X509_UNICODE_ANY_STRING = X509_UNICODE_NAME_VALUE
X509_OCTET_STRING = 25
X509_BITS = 26
X509_INTEGER = 27
X509_MULTI_BYTE_INTEGER = 28
X509_ENUMERATED = 29
X509_CHOICE_OF_TIME = 30
X509_AUTHORITY_KEY_ID2 = 31
X509_AUTHORITY_INFO_ACCESS = 32
X509_SUBJECT_INFO_ACCESS = X509_AUTHORITY_INFO_ACCESS
X509_CRL_REASON_CODE = X509_ENUMERATED
PKCS_CONTENT_INFO = 33
X509_SEQUENCE_OF_ANY = 34
X509_CRL_DIST_POINTS = 35
X509_ENHANCED_KEY_USAGE = 36
PKCS_CTL = 37
X509_MULTI_BYTE_UINT = 38
X509_DSS_PUBLICKEY = X509_MULTI_BYTE_UINT
X509_DSS_PARAMETERS = 39
X509_DSS_SIGNATURE = 40
PKCS_RC2_CBC_PARAMETERS = 41
PKCS_SMIME_CAPABILITIES = 42
X509_QC_STATEMENTS_EXT = 42
PKCS_RSA_PRIVATE_KEY = 43
PKCS_PRIVATE_KEY_INFO = 44
PKCS_ENCRYPTED_PRIVATE_KEY_INFO = 45
X509_PKIX_POLICY_QUALIFIER_USERNOTICE = 46
X509_DH_PUBLICKEY = X509_MULTI_BYTE_UINT
X509_DH_PARAMETERS = 47
PKCS_ATTRIBUTES = 48
PKCS_SORTED_CTL = 49
X509_ECC_SIGNATURE = 47
X942_DH_PARAMETERS = 50
X509_BITS_WITHOUT_TRAILING_ZEROES = 51
X942_OTHER_INFO = 52
X509_CERT_PAIR = 53
X509_ISSUING_DIST_POINT = 54
X509_NAME_CONSTRAINTS = 55
X509_POLICY_MAPPINGS = 56
X509_POLICY_CONSTRAINTS = 57
X509_CROSS_CERT_DIST_POINTS = 58
CMC_DATA = 59
CMC_RESPONSE = 60
CMC_STATUS = 61
CMC_ADD_EXTENSIONS = 62
CMC_ADD_ATTRIBUTES = 63
X509_CERTIFICATE_TEMPLATE = 64
OCSP_SIGNED_REQUEST = 65
OCSP_REQUEST = 66
OCSP_RESPONSE = 67
OCSP_BASIC_SIGNED_RESPONSE = 68
OCSP_BASIC_RESPONSE = 69
X509_LOGOTYPE_EXT = 70
X509_BIOMETRIC_EXT = 71
CNG_RSA_PUBLIC_KEY_BLOB = 72
X509_OBJECT_IDENTIFIER = 73
X509_ALGORITHM_IDENTIFIER = 74
PKCS_RSA_SSA_PSS_PARAMETERS = 75
PKCS_RSAES_OAEP_PARAMETERS = 76
ECC_CMS_SHARED_INFO = 77
TIMESTAMP_REQUEST = 78
TIMESTAMP_RESPONSE = 79
TIMESTAMP_INFO = 80
X509_CERT_BUNDLE = 81
PKCS7_SIGNER_INFO = 500
CMS_SIGNER_INFO = 501

szOID_AUTHORITY_KEY_IDENTIFIER = "2.5.29.1"
szOID_KEY_ATTRIBUTES = "2.5.29.2"
szOID_CERT_POLICIES_95 = "2.5.29.3"
szOID_KEY_USAGE_RESTRICTION = "2.5.29.4"
szOID_SUBJECT_ALT_NAME = "2.5.29.7"
szOID_ISSUER_ALT_NAME = "2.5.29.8"
szOID_BASIC_CONSTRAINTS = "2.5.29.10"
szOID_KEY_USAGE = "2.5.29.15"
szOID_PRIVATEKEY_USAGE_PERIOD = "2.5.29.16"
szOID_BASIC_CONSTRAINTS2 = "2.5.29.19"
szOID_CERT_POLICIES = "2.5.29.32"
szOID_ANY_CERT_POLICY = "2.5.29.32.0"
szOID_AUTHORITY_KEY_IDENTIFIER2 = "2.5.29.35"
szOID_SUBJECT_KEY_IDENTIFIER = "2.5.29.14"
szOID_SUBJECT_ALT_NAME2 = "2.5.29.17"
szOID_ISSUER_ALT_NAME2 = "2.5.29.18"
szOID_CRL_REASON_CODE = "2.5.29.21"
szOID_REASON_CODE_HOLD = "2.5.29.23"
szOID_CRL_DIST_POINTS = "2.5.29.31"
szOID_ENHANCED_KEY_USAGE = "2.5.29.37"
szOID_CRL_NUMBER = "2.5.29.20"
szOID_DELTA_CRL_INDICATOR = "2.5.29.27"
szOID_ISSUING_DIST_POINT = "2.5.29.28"
szOID_FRESHEST_CRL = "2.5.29.46"
szOID_NAME_CONSTRAINTS = "2.5.29.30"
szOID_POLICY_MAPPINGS = "2.5.29.33"
szOID_LEGACY_POLICY_MAPPINGS = "2.5.29.5"
szOID_POLICY_CONSTRAINTS = "2.5.29.36"
szOID_RENEWAL_CERTIFICATE = "1.3.6.1.4.1.311.13.1"
szOID_ENROLLMENT_NAME_VALUE_PAIR = "1.3.6.1.4.1.311.13.2.1"
szOID_ENROLLMENT_CSP_PROVIDER = "1.3.6.1.4.1.311.13.2.2"
szOID_OS_VERSION = "1.3.6.1.4.1.311.13.2.3"
szOID_ENROLLMENT_AGENT = "1.3.6.1.4.1.311.20.2.1"
szOID_PKIX = "1.3.6.1.5.5.7"
szOID_PKIX_PE = "1.3.6.1.5.5.7.1"
szOID_AUTHORITY_INFO_ACCESS = "1.3.6.1.5.5.7.1.1"
szOID_CERT_EXTENSIONS = "1.3.6.1.4.1.311.2.1.14"
szOID_NEXT_UPDATE_LOCATION = "1.3.6.1.4.1.311.10.2"
szOID_REMOVE_CERTIFICATE = "1.3.6.1.4.1.311.10.8.1"
szOID_CROSS_CERT_DIST_POINTS = "1.3.6.1.4.1.311.10.9.1"
szOID_CTL = "1.3.6.1.4.1.311.10.1"
szOID_SORTED_CTL = "1.3.6.1.4.1.311.10.1.1"
szOID_SERIALIZED = "1.3.6.1.4.1.311.10.3.3.1"
szOID_NT_PRINCIPAL_NAME = "1.3.6.1.4.1.311.20.2.3"
szOID_PRODUCT_UPDATE = "1.3.6.1.4.1.311.31.1"
szOID_ANY_APPLICATION_POLICY = "1.3.6.1.4.1.311.10.12.1"
szOID_AUTO_ENROLL_CTL_USAGE = "1.3.6.1.4.1.311.20.1"
szOID_ENROLL_CERTTYPE_EXTENSION = "1.3.6.1.4.1.311.20.2"
szOID_CERT_MANIFOLD = "1.3.6.1.4.1.311.20.3"
szOID_CERTSRV_CA_VERSION = "1.3.6.1.4.1.311.21.1"
szOID_CERTSRV_PREVIOUS_CERT_HASH = "1.3.6.1.4.1.311.21.2"
szOID_CRL_VIRTUAL_BASE = "1.3.6.1.4.1.311.21.3"
szOID_CRL_NEXT_PUBLISH = "1.3.6.1.4.1.311.21.4"
szOID_KP_CA_EXCHANGE = "1.3.6.1.4.1.311.21.5"
szOID_KP_KEY_RECOVERY_AGENT = "1.3.6.1.4.1.311.21.6"
szOID_CERTIFICATE_TEMPLATE = "1.3.6.1.4.1.311.21.7"
szOID_ENTERPRISE_OID_ROOT = "1.3.6.1.4.1.311.21.8"
szOID_RDN_DUMMY_SIGNER = "1.3.6.1.4.1.311.21.9"
szOID_APPLICATION_CERT_POLICIES = "1.3.6.1.4.1.311.21.10"
szOID_APPLICATION_POLICY_MAPPINGS = "1.3.6.1.4.1.311.21.11"
szOID_APPLICATION_POLICY_CONSTRAINTS = "1.3.6.1.4.1.311.21.12"
szOID_ARCHIVED_KEY_ATTR = "1.3.6.1.4.1.311.21.13"
szOID_CRL_SELF_CDP = "1.3.6.1.4.1.311.21.14"
szOID_REQUIRE_CERT_CHAIN_POLICY = "1.3.6.1.4.1.311.21.15"
szOID_ARCHIVED_KEY_CERT_HASH = "1.3.6.1.4.1.311.21.16"
szOID_ISSUED_CERT_HASH = "1.3.6.1.4.1.311.21.17"
szOID_DS_EMAIL_REPLICATION = "1.3.6.1.4.1.311.21.19"
szOID_REQUEST_CLIENT_INFO = "1.3.6.1.4.1.311.21.20"
szOID_ENCRYPTED_KEY_HASH = "1.3.6.1.4.1.311.21.21"
szOID_CERTSRV_CROSSCA_VERSION = "1.3.6.1.4.1.311.21.22"
szOID_NTDS_REPLICATION = "1.3.6.1.4.1.311.25.1"
szOID_SUBJECT_DIR_ATTRS = "2.5.29.9"
szOID_PKIX_KP = "1.3.6.1.5.5.7.3"
szOID_PKIX_KP_SERVER_AUTH = "1.3.6.1.5.5.7.3.1"
szOID_PKIX_KP_CLIENT_AUTH = "1.3.6.1.5.5.7.3.2"
szOID_PKIX_KP_CODE_SIGNING = "1.3.6.1.5.5.7.3.3"
szOID_PKIX_KP_EMAIL_PROTECTION = "1.3.6.1.5.5.7.3.4"
szOID_PKIX_KP_IPSEC_END_SYSTEM = "1.3.6.1.5.5.7.3.5"
szOID_PKIX_KP_IPSEC_TUNNEL = "1.3.6.1.5.5.7.3.6"
szOID_PKIX_KP_IPSEC_USER = "1.3.6.1.5.5.7.3.7"
szOID_PKIX_KP_TIMESTAMP_SIGNING = "1.3.6.1.5.5.7.3.8"
szOID_IPSEC_KP_IKE_INTERMEDIATE = "1.3.6.1.5.5.8.2.2"
szOID_KP_CTL_USAGE_SIGNING = "1.3.6.1.4.1.311.10.3.1"
szOID_KP_TIME_STAMP_SIGNING = "1.3.6.1.4.1.311.10.3.2"
szOID_SERVER_GATED_CRYPTO = "1.3.6.1.4.1.311.10.3.3"
szOID_SGC_NETSCAPE = "2.16.840.1.113730.4.1"
szOID_KP_EFS = "1.3.6.1.4.1.311.10.3.4"
szOID_EFS_RECOVERY = "1.3.6.1.4.1.311.10.3.4.1"
szOID_WHQL_CRYPTO = "1.3.6.1.4.1.311.10.3.5"
szOID_NT5_CRYPTO = "1.3.6.1.4.1.311.10.3.6"
szOID_OEM_WHQL_CRYPTO = "1.3.6.1.4.1.311.10.3.7"
szOID_EMBEDDED_NT_CRYPTO = "1.3.6.1.4.1.311.10.3.8"
szOID_ROOT_LIST_SIGNER = "1.3.6.1.4.1.311.10.3.9"
szOID_KP_QUALIFIED_SUBORDINATION = "1.3.6.1.4.1.311.10.3.10"
szOID_KP_KEY_RECOVERY = "1.3.6.1.4.1.311.10.3.11"
szOID_KP_DOCUMENT_SIGNING = "1.3.6.1.4.1.311.10.3.12"
szOID_KP_LIFETIME_SIGNING = "1.3.6.1.4.1.311.10.3.13"
szOID_KP_MOBILE_DEVICE_SOFTWARE = "1.3.6.1.4.1.311.10.3.14"
szOID_DRM = "1.3.6.1.4.1.311.10.5.1"
szOID_DRM_INDIVIDUALIZATION = "1.3.6.1.4.1.311.10.5.2"
szOID_LICENSES = "1.3.6.1.4.1.311.10.6.1"
szOID_LICENSE_SERVER = "1.3.6.1.4.1.311.10.6.2"
szOID_KP_SMARTCARD_LOGON = "1.3.6.1.4.1.311.20.2.2"
szOID_YESNO_TRUST_ATTR = "1.3.6.1.4.1.311.10.4.1"
szOID_PKIX_POLICY_QUALIFIER_CPS = "1.3.6.1.5.5.7.2.1"
szOID_PKIX_POLICY_QUALIFIER_USERNOTICE = "1.3.6.1.5.5.7.2.2"
szOID_CERT_POLICIES_95_QUALIFIER1 = "2.16.840.1.113733.1.7.1.1"
CERT_UNICODE_RDN_ERR_INDEX_MASK = 0x3FF
CERT_UNICODE_RDN_ERR_INDEX_SHIFT = 22
CERT_UNICODE_ATTR_ERR_INDEX_MASK = 0x003F
CERT_UNICODE_ATTR_ERR_INDEX_SHIFT = 16
CERT_UNICODE_VALUE_ERR_INDEX_MASK = 0x0000FFFF
CERT_UNICODE_VALUE_ERR_INDEX_SHIFT = 0
CERT_DIGITAL_SIGNATURE_KEY_USAGE = 0x80
CERT_NON_REPUDIATION_KEY_USAGE = 0x40
CERT_KEY_ENCIPHERMENT_KEY_USAGE = 0x20
CERT_DATA_ENCIPHERMENT_KEY_USAGE = 0x10
CERT_KEY_AGREEMENT_KEY_USAGE = 0x08
CERT_KEY_CERT_SIGN_KEY_USAGE = 0x04
CERT_OFFLINE_CRL_SIGN_KEY_USAGE = 0x02
CERT_CRL_SIGN_KEY_USAGE = 0x02
CERT_ENCIPHER_ONLY_KEY_USAGE = 0x01
CERT_DECIPHER_ONLY_KEY_USAGE = 0x80
CERT_ALT_NAME_OTHER_NAME = 1
CERT_ALT_NAME_RFC822_NAME = 2
CERT_ALT_NAME_DNS_NAME = 3
CERT_ALT_NAME_X400_ADDRESS = 4
CERT_ALT_NAME_DIRECTORY_NAME = 5
CERT_ALT_NAME_EDI_PARTY_NAME = 6
CERT_ALT_NAME_URL = 7
CERT_ALT_NAME_IP_ADDRESS = 8
CERT_ALT_NAME_REGISTERED_ID = 9
CERT_ALT_NAME_ENTRY_ERR_INDEX_MASK = 0xFF
CERT_ALT_NAME_ENTRY_ERR_INDEX_SHIFT = 16
CERT_ALT_NAME_VALUE_ERR_INDEX_MASK = 0x0000FFFF
CERT_ALT_NAME_VALUE_ERR_INDEX_SHIFT = 0
CERT_CA_SUBJECT_FLAG = 0x80
CERT_END_ENTITY_SUBJECT_FLAG = 0x40
szOID_PKIX_ACC_DESCR = "1.3.6.1.5.5.7.48"
szOID_PKIX_OCSP = "1.3.6.1.5.5.7.48.1"
szOID_PKIX_CA_ISSUERS = "1.3.6.1.5.5.7.48.2"
CRL_REASON_UNSPECIFIED = 0
CRL_REASON_KEY_COMPROMISE = 1
CRL_REASON_CA_COMPROMISE = 2
CRL_REASON_AFFILIATION_CHANGED = 3
CRL_REASON_SUPERSEDED = 4
CRL_REASON_CESSATION_OF_OPERATION = 5
CRL_REASON_CERTIFICATE_HOLD = 6
CRL_REASON_REMOVE_FROM_CRL = 8
CRL_DIST_POINT_NO_NAME = 0
CRL_DIST_POINT_FULL_NAME = 1
CRL_DIST_POINT_ISSUER_RDN_NAME = 2
CRL_REASON_UNUSED_FLAG = 0x80
CRL_REASON_KEY_COMPROMISE_FLAG = 0x40
CRL_REASON_CA_COMPROMISE_FLAG = 0x20
CRL_REASON_AFFILIATION_CHANGED_FLAG = 0x10
CRL_REASON_SUPERSEDED_FLAG = 0x08
CRL_REASON_CESSATION_OF_OPERATION_FLAG = 0x04
CRL_REASON_CERTIFICATE_HOLD_FLAG = 0x02
CRL_DIST_POINT_ERR_INDEX_MASK = 0x7F
CRL_DIST_POINT_ERR_INDEX_SHIFT = 24

CRL_DIST_POINT_ERR_CRL_ISSUER_BIT = -2147483648

CROSS_CERT_DIST_POINT_ERR_INDEX_MASK = 0xFF
CROSS_CERT_DIST_POINT_ERR_INDEX_SHIFT = 24

CERT_EXCLUDED_SUBTREE_BIT = -2147483648

SORTED_CTL_EXT_FLAGS_OFFSET = 0 * 4
SORTED_CTL_EXT_COUNT_OFFSET = 1 * 4
SORTED_CTL_EXT_MAX_COLLISION_OFFSET = 2 * 4
SORTED_CTL_EXT_HASH_BUCKET_OFFSET = 3 * 4
SORTED_CTL_EXT_HASHED_SUBJECT_IDENTIFIER_FLAG = 0x1
CERT_DSS_R_LEN = 20
CERT_DSS_S_LEN = 20
CERT_DSS_SIGNATURE_LEN = CERT_DSS_R_LEN + CERT_DSS_S_LEN
CERT_MAX_ASN_ENCODED_DSS_SIGNATURE_LEN = 2 + 2 * (2 + 20 + 1)
CRYPT_X942_COUNTER_BYTE_LENGTH = 4
CRYPT_X942_KEY_LENGTH_BYTE_LENGTH = 4
CRYPT_X942_PUB_INFO_BYTE_LENGTH = 512 / 8
CRYPT_RC2_40BIT_VERSION = 160
CRYPT_RC2_56BIT_VERSION = 52
CRYPT_RC2_64BIT_VERSION = 120
CRYPT_RC2_128BIT_VERSION = 58
szOID_VERISIGN_PRIVATE_6_9 = "2.16.840.1.113733.1.6.9"
szOID_VERISIGN_ONSITE_JURISDICTION_HASH = "2.16.840.1.113733.1.6.11"
szOID_VERISIGN_BITSTRING_6_13 = "2.16.840.1.113733.1.6.13"
szOID_VERISIGN_ISS_STRONG_CRYPTO = "2.16.840.1.113733.1.8.1"
szOID_NETSCAPE = "2.16.840.1.113730"
szOID_NETSCAPE_CERT_EXTENSION = "2.16.840.1.113730.1"
szOID_NETSCAPE_CERT_TYPE = "2.16.840.1.113730.1.1"
szOID_NETSCAPE_BASE_URL = "2.16.840.1.113730.1.2"
szOID_NETSCAPE_REVOCATION_URL = "2.16.840.1.113730.1.3"
szOID_NETSCAPE_CA_REVOCATION_URL = "2.16.840.1.113730.1.4"
szOID_NETSCAPE_CERT_RENEWAL_URL = "2.16.840.1.113730.1.7"
szOID_NETSCAPE_CA_POLICY_URL = "2.16.840.1.113730.1.8"
szOID_NETSCAPE_SSL_SERVER_NAME = "2.16.840.1.113730.1.12"
szOID_NETSCAPE_COMMENT = "2.16.840.1.113730.1.13"
szOID_NETSCAPE_DATA_TYPE = "2.16.840.1.113730.2"
szOID_NETSCAPE_CERT_SEQUENCE = "2.16.840.1.113730.2.5"
NETSCAPE_SSL_CLIENT_AUTH_CERT_TYPE = 0x80
NETSCAPE_SSL_SERVER_AUTH_CERT_TYPE = 0x40
NETSCAPE_SMIME_CERT_TYPE = 0x20
NETSCAPE_SIGN_CERT_TYPE = 0x10
NETSCAPE_SSL_CA_CERT_TYPE = 0x04
NETSCAPE_SMIME_CA_CERT_TYPE = 0x02
NETSCAPE_SIGN_CA_CERT_TYPE = 0x01
szOID_CT_PKI_DATA = "1.3.6.1.5.5.7.12.2"
szOID_CT_PKI_RESPONSE = "1.3.6.1.5.5.7.12.3"
szOID_PKIX_NO_SIGNATURE = "1.3.6.1.5.5.7.6.2"
szOID_CMC = "1.3.6.1.5.5.7.7"
szOID_CMC_STATUS_INFO = "1.3.6.1.5.5.7.7.1"
szOID_CMC_IDENTIFICATION = "1.3.6.1.5.5.7.7.2"
szOID_CMC_IDENTITY_PROOF = "1.3.6.1.5.5.7.7.3"
szOID_CMC_DATA_RETURN = "1.3.6.1.5.5.7.7.4"
szOID_CMC_TRANSACTION_ID = "1.3.6.1.5.5.7.7.5"
szOID_CMC_SENDER_NONCE = "1.3.6.1.5.5.7.7.6"
szOID_CMC_RECIPIENT_NONCE = "1.3.6.1.5.5.7.7.7"
szOID_CMC_ADD_EXTENSIONS = "1.3.6.1.5.5.7.7.8"
szOID_CMC_ENCRYPTED_POP = "1.3.6.1.5.5.7.7.9"
szOID_CMC_DECRYPTED_POP = "1.3.6.1.5.5.7.7.10"
szOID_CMC_LRA_POP_WITNESS = "1.3.6.1.5.5.7.7.11"
szOID_CMC_GET_CERT = "1.3.6.1.5.5.7.7.15"
szOID_CMC_GET_CRL = "1.3.6.1.5.5.7.7.16"
szOID_CMC_REVOKE_REQUEST = "1.3.6.1.5.5.7.7.17"
szOID_CMC_REG_INFO = "1.3.6.1.5.5.7.7.18"
szOID_CMC_RESPONSE_INFO = "1.3.6.1.5.5.7.7.19"
szOID_CMC_QUERY_PENDING = "1.3.6.1.5.5.7.7.21"
szOID_CMC_ID_POP_LINK_RANDOM = "1.3.6.1.5.5.7.7.22"
szOID_CMC_ID_POP_LINK_WITNESS = "1.3.6.1.5.5.7.7.23"
szOID_CMC_ID_CONFIRM_CERT_ACCEPTANCE = "1.3.6.1.5.5.7.7.24"
szOID_CMC_ADD_ATTRIBUTES = "1.3.6.1.4.1.311.10.10.1"
CMC_TAGGED_CERT_REQUEST_CHOICE = 1
CMC_OTHER_INFO_NO_CHOICE = 0
CMC_OTHER_INFO_FAIL_CHOICE = 1
CMC_OTHER_INFO_PEND_CHOICE = 2
CMC_STATUS_SUCCESS = 0
CMC_STATUS_FAILED = 2
CMC_STATUS_PENDING = 3
CMC_STATUS_NO_SUPPORT = 4
CMC_STATUS_CONFIRM_REQUIRED = 5
CMC_FAIL_BAD_ALG = 0
CMC_FAIL_BAD_MESSAGE_CHECK = 1
CMC_FAIL_BAD_REQUEST = 2
CMC_FAIL_BAD_TIME = 3
CMC_FAIL_BAD_CERT_ID = 4
CMC_FAIL_UNSUPORTED_EXT = 5  # Yes Microsoft made a typo in "UNSUPPORTED"
CMC_FAIL_MUST_ARCHIVE_KEYS = 6
CMC_FAIL_BAD_IDENTITY = 7
CMC_FAIL_POP_REQUIRED = 8
CMC_FAIL_POP_FAILED = 9
CMC_FAIL_NO_KEY_REUSE = 10
CMC_FAIL_INTERNAL_CA_ERROR = 11
CMC_FAIL_TRY_LATER = 12
CRYPT_OID_ENCODE_OBJECT_FUNC = "CryptDllEncodeObject"
CRYPT_OID_DECODE_OBJECT_FUNC = "CryptDllDecodeObject"
CRYPT_OID_ENCODE_OBJECT_EX_FUNC = "CryptDllEncodeObjectEx"
CRYPT_OID_DECODE_OBJECT_EX_FUNC = "CryptDllDecodeObjectEx"
CRYPT_OID_CREATE_COM_OBJECT_FUNC = "CryptDllCreateCOMObject"
CRYPT_OID_VERIFY_REVOCATION_FUNC = "CertDllVerifyRevocation"
CRYPT_OID_VERIFY_CTL_USAGE_FUNC = "CertDllVerifyCTLUsage"
CRYPT_OID_FORMAT_OBJECT_FUNC = "CryptDllFormatObject"
CRYPT_OID_FIND_OID_INFO_FUNC = "CryptDllFindOIDInfo"
CRYPT_OID_FIND_LOCALIZED_NAME_FUNC = "CryptDllFindLocalizedName"

CRYPT_OID_REGPATH = "Software\\Microsoft\\Cryptography\\OID"
CRYPT_OID_REG_ENCODING_TYPE_PREFIX = "EncodingType "
CRYPT_OID_REG_DLL_VALUE_NAME = "Dll"
CRYPT_OID_REG_FUNC_NAME_VALUE_NAME = "FuncName"
CRYPT_OID_REG_FUNC_NAME_VALUE_NAME_A = "FuncName"
CRYPT_OID_REG_FLAGS_VALUE_NAME = "CryptFlags"
CRYPT_DEFAULT_OID = "DEFAULT"
CRYPT_INSTALL_OID_FUNC_BEFORE_FLAG = 1
CRYPT_GET_INSTALLED_OID_FUNC_FLAG = 0x1
CRYPT_REGISTER_FIRST_INDEX = 0
CRYPT_REGISTER_LAST_INDEX = -1
CRYPT_MATCH_ANY_ENCODING_TYPE = -1
CRYPT_HASH_ALG_OID_GROUP_ID = 1
CRYPT_ENCRYPT_ALG_OID_GROUP_ID = 2
CRYPT_PUBKEY_ALG_OID_GROUP_ID = 3
CRYPT_SIGN_ALG_OID_GROUP_ID = 4
CRYPT_RDN_ATTR_OID_GROUP_ID = 5
CRYPT_EXT_OR_ATTR_OID_GROUP_ID = 6
CRYPT_ENHKEY_USAGE_OID_GROUP_ID = 7
CRYPT_POLICY_OID_GROUP_ID = 8
CRYPT_TEMPLATE_OID_GROUP_ID = 9
CRYPT_LAST_OID_GROUP_ID = 9
CRYPT_FIRST_ALG_OID_GROUP_ID = CRYPT_HASH_ALG_OID_GROUP_ID
CRYPT_LAST_ALG_OID_GROUP_ID = CRYPT_SIGN_ALG_OID_GROUP_ID
CRYPT_OID_INHIBIT_SIGNATURE_FORMAT_FLAG = 0x1
CRYPT_OID_USE_PUBKEY_PARA_FOR_PKCS7_FLAG = 0x2
CRYPT_OID_NO_NULL_ALGORITHM_PARA_FLAG = 0x4
CRYPT_OID_INFO_OID_KEY = 1
CRYPT_OID_INFO_NAME_KEY = 2
CRYPT_OID_INFO_ALGID_KEY = 3
CRYPT_OID_INFO_SIGN_KEY = 4
CRYPT_INSTALL_OID_INFO_BEFORE_FLAG = 1
CRYPT_LOCALIZED_NAME_ENCODING_TYPE = 0
CRYPT_LOCALIZED_NAME_OID = "LocalizedNames"
szOID_PKCS_7_DATA = "1.2.840.113549.1.7.1"
szOID_PKCS_7_SIGNED = "1.2.840.113549.1.7.2"
szOID_PKCS_7_ENVELOPED = "1.2.840.113549.1.7.3"
szOID_PKCS_7_SIGNEDANDENVELOPED = "1.2.840.113549.1.7.4"
szOID_PKCS_7_DIGESTED = "1.2.840.113549.1.7.5"
szOID_PKCS_7_ENCRYPTED = "1.2.840.113549.1.7.6"
szOID_PKCS_9_CONTENT_TYPE = "1.2.840.113549.1.9.3"
szOID_PKCS_9_MESSAGE_DIGEST = "1.2.840.113549.1.9.4"
CMSG_DATA = 1
CMSG_SIGNED = 2
CMSG_ENVELOPED = 3
CMSG_SIGNED_AND_ENVELOPED = 4
CMSG_HASHED = 5
CMSG_ENCRYPTED = 6

CMSG_ALL_FLAGS = -1
CMSG_DATA_FLAG = 1 << CMSG_DATA
CMSG_SIGNED_FLAG = 1 << CMSG_SIGNED
CMSG_ENVELOPED_FLAG = 1 << CMSG_ENVELOPED
CMSG_SIGNED_AND_ENVELOPED_FLAG = 1 << CMSG_SIGNED_AND_ENVELOPED
CMSG_HASHED_FLAG = 1 << CMSG_HASHED
CMSG_ENCRYPTED_FLAG = 1 << CMSG_ENCRYPTED
CERT_ID_ISSUER_SERIAL_NUMBER = 1
CERT_ID_KEY_IDENTIFIER = 2
CERT_ID_SHA1_HASH = 3
CMSG_KEY_AGREE_EPHEMERAL_KEY_CHOICE = 1
CMSG_KEY_AGREE_STATIC_KEY_CHOICE = 2
CMSG_MAIL_LIST_HANDLE_KEY_CHOICE = 1
CMSG_KEY_TRANS_RECIPIENT = 1
CMSG_KEY_AGREE_RECIPIENT = 2
CMSG_MAIL_LIST_RECIPIENT = 3
CMSG_SP3_COMPATIBLE_ENCRYPT_FLAG = -2147483648
CMSG_RC4_NO_SALT_FLAG = 0x40000000
CMSG_INDEFINITE_LENGTH = -1
CMSG_BARE_CONTENT_FLAG = 0x00000001
CMSG_LENGTH_ONLY_FLAG = 0x00000002
CMSG_DETACHED_FLAG = 0x00000004
CMSG_AUTHENTICATED_ATTRIBUTES_FLAG = 0x00000008
CMSG_CONTENTS_OCTETS_FLAG = 0x00000010
CMSG_MAX_LENGTH_FLAG = 0x00000020
CMSG_CMS_ENCAPSULATED_CONTENT_FLAG = 0x00000040
CMSG_CRYPT_RELEASE_CONTEXT_FLAG = 0x00008000
CMSG_TYPE_PARAM = 1
CMSG_CONTENT_PARAM = 2
CMSG_BARE_CONTENT_PARAM = 3
CMSG_INNER_CONTENT_TYPE_PARAM = 4
CMSG_SIGNER_COUNT_PARAM = 5
CMSG_SIGNER_INFO_PARAM = 6
CMSG_SIGNER_CERT_INFO_PARAM = 7
CMSG_SIGNER_HASH_ALGORITHM_PARAM = 8
CMSG_SIGNER_AUTH_ATTR_PARAM = 9
CMSG_SIGNER_UNAUTH_ATTR_PARAM = 10
CMSG_CERT_COUNT_PARAM = 11
CMSG_CERT_PARAM = 12
CMSG_CRL_COUNT_PARAM = 13
CMSG_CRL_PARAM = 14
CMSG_ENVELOPE_ALGORITHM_PARAM = 15
CMSG_RECIPIENT_COUNT_PARAM = 17
CMSG_RECIPIENT_INDEX_PARAM = 18
CMSG_RECIPIENT_INFO_PARAM = 19
CMSG_HASH_ALGORITHM_PARAM = 20
CMSG_HASH_DATA_PARAM = 21
CMSG_COMPUTED_HASH_PARAM = 22
CMSG_ENCRYPT_PARAM = 26
CMSG_ENCRYPTED_DIGEST = 27
CMSG_ENCODED_SIGNER = 28
CMSG_ENCODED_MESSAGE = 29
CMSG_VERSION_PARAM = 30
CMSG_ATTR_CERT_COUNT_PARAM = 31
CMSG_ATTR_CERT_PARAM = 32
CMSG_CMS_RECIPIENT_COUNT_PARAM = 33
CMSG_CMS_RECIPIENT_INDEX_PARAM = 34
CMSG_CMS_RECIPIENT_ENCRYPTED_KEY_INDEX_PARAM = 35
CMSG_CMS_RECIPIENT_INFO_PARAM = 36
CMSG_UNPROTECTED_ATTR_PARAM = 37
CMSG_SIGNER_CERT_ID_PARAM = 38
CMSG_CMS_SIGNER_INFO_PARAM = 39
CMSG_SIGNED_DATA_V1 = 1
CMSG_SIGNED_DATA_V3 = 3
CMSG_SIGNED_DATA_PKCS_1_5_VERSION = CMSG_SIGNED_DATA_V1
CMSG_SIGNED_DATA_CMS_VERSION = CMSG_SIGNED_DATA_V3
CMSG_SIGNER_INFO_V1 = 1
CMSG_SIGNER_INFO_V3 = 3
CMSG_SIGNER_INFO_PKCS_1_5_VERSION = CMSG_SIGNER_INFO_V1
CMSG_SIGNER_INFO_CMS_VERSION = CMSG_SIGNER_INFO_V3
CMSG_HASHED_DATA_V0 = 0
CMSG_HASHED_DATA_V2 = 2
CMSG_HASHED_DATA_PKCS_1_5_VERSION = CMSG_HASHED_DATA_V0
CMSG_HASHED_DATA_CMS_VERSION = CMSG_HASHED_DATA_V2
CMSG_ENVELOPED_DATA_V0 = 0
CMSG_ENVELOPED_DATA_V2 = 2
CMSG_ENVELOPED_DATA_PKCS_1_5_VERSION = CMSG_ENVELOPED_DATA_V0
CMSG_ENVELOPED_DATA_CMS_VERSION = CMSG_ENVELOPED_DATA_V2
CMSG_KEY_AGREE_ORIGINATOR_CERT = 1
CMSG_KEY_AGREE_ORIGINATOR_PUBLIC_KEY = 2
CMSG_ENVELOPED_RECIPIENT_V0 = 0
CMSG_ENVELOPED_RECIPIENT_V2 = 2
CMSG_ENVELOPED_RECIPIENT_V3 = 3
CMSG_ENVELOPED_RECIPIENT_V4 = 4
CMSG_KEY_TRANS_PKCS_1_5_VERSION = CMSG_ENVELOPED_RECIPIENT_V0
CMSG_KEY_TRANS_CMS_VERSION = CMSG_ENVELOPED_RECIPIENT_V2
CMSG_KEY_AGREE_VERSION = CMSG_ENVELOPED_RECIPIENT_V3
CMSG_MAIL_LIST_VERSION = CMSG_ENVELOPED_RECIPIENT_V4
CMSG_CTRL_VERIFY_SIGNATURE = 1
CMSG_CTRL_DECRYPT = 2
CMSG_CTRL_VERIFY_HASH = 5
CMSG_CTRL_ADD_SIGNER = 6
CMSG_CTRL_DEL_SIGNER = 7
CMSG_CTRL_ADD_SIGNER_UNAUTH_ATTR = 8
CMSG_CTRL_DEL_SIGNER_UNAUTH_ATTR = 9
CMSG_CTRL_ADD_CERT = 10
CMSG_CTRL_DEL_CERT = 11
CMSG_CTRL_ADD_CRL = 12
CMSG_CTRL_DEL_CRL = 13
CMSG_CTRL_ADD_ATTR_CERT = 14
CMSG_CTRL_DEL_ATTR_CERT = 15
CMSG_CTRL_KEY_TRANS_DECRYPT = 16
CMSG_CTRL_KEY_AGREE_DECRYPT = 17
CMSG_CTRL_MAIL_LIST_DECRYPT = 18
CMSG_CTRL_VERIFY_SIGNATURE_EX = 19
CMSG_CTRL_ADD_CMS_SIGNER_INFO = 20
CMSG_VERIFY_SIGNER_PUBKEY = 1
CMSG_VERIFY_SIGNER_CERT = 2
CMSG_VERIFY_SIGNER_CHAIN = 3
CMSG_VERIFY_SIGNER_NULL = 4
CMSG_OID_GEN_ENCRYPT_KEY_FUNC = "CryptMsgDllGenEncryptKey"
CMSG_OID_EXPORT_ENCRYPT_KEY_FUNC = "CryptMsgDllExportEncryptKey"
CMSG_OID_IMPORT_ENCRYPT_KEY_FUNC = "CryptMsgDllImportEncryptKey"
CMSG_CONTENT_ENCRYPT_PAD_ENCODED_LEN_FLAG = 0x00000001
CMSG_DEFAULT_INSTALLABLE_FUNC_OID = 1
CMSG_CONTENT_ENCRYPT_FREE_PARA_FLAG = 0x00000001
CMSG_CONTENT_ENCRYPT_RELEASE_CONTEXT_FLAG = 0x00008000
CMSG_OID_GEN_CONTENT_ENCRYPT_KEY_FUNC = "CryptMsgDllGenContentEncryptKey"
CMSG_KEY_TRANS_ENCRYPT_FREE_PARA_FLAG = 0x00000001
CMSG_OID_EXPORT_KEY_TRANS_FUNC = "CryptMsgDllExportKeyTrans"
CMSG_KEY_AGREE_ENCRYPT_FREE_PARA_FLAG = 0x00000001
CMSG_KEY_AGREE_ENCRYPT_FREE_MATERIAL_FLAG = 0x00000002
CMSG_KEY_AGREE_ENCRYPT_FREE_PUBKEY_ALG_FLAG = 0x00000004
CMSG_KEY_AGREE_ENCRYPT_FREE_PUBKEY_PARA_FLAG = 0x00000008
CMSG_KEY_AGREE_ENCRYPT_FREE_PUBKEY_BITS_FLAG = 0x00000010
CMSG_OID_EXPORT_KEY_AGREE_FUNC = "CryptMsgDllExportKeyAgree"
CMSG_MAIL_LIST_ENCRYPT_FREE_PARA_FLAG = 0x00000001
CMSG_OID_EXPORT_MAIL_LIST_FUNC = "CryptMsgDllExportMailList"
CMSG_OID_IMPORT_KEY_TRANS_FUNC = "CryptMsgDllImportKeyTrans"
CMSG_OID_IMPORT_KEY_AGREE_FUNC = "CryptMsgDllImportKeyAgree"
CMSG_OID_IMPORT_MAIL_LIST_FUNC = "CryptMsgDllImportMailList"

# Certificate property id's used with CertGetCertificateContextProperty
CERT_KEY_PROV_HANDLE_PROP_ID = 1
CERT_KEY_PROV_INFO_PROP_ID = 2
CERT_SHA1_HASH_PROP_ID = 3
CERT_MD5_HASH_PROP_ID = 4
CERT_HASH_PROP_ID = CERT_SHA1_HASH_PROP_ID
CERT_KEY_CONTEXT_PROP_ID = 5
CERT_KEY_SPEC_PROP_ID = 6
CERT_IE30_RESERVED_PROP_ID = 7
CERT_PUBKEY_HASH_RESERVED_PROP_ID = 8
CERT_ENHKEY_USAGE_PROP_ID = 9
CERT_CTL_USAGE_PROP_ID = CERT_ENHKEY_USAGE_PROP_ID
CERT_NEXT_UPDATE_LOCATION_PROP_ID = 10
CERT_FRIENDLY_NAME_PROP_ID = 11
CERT_PVK_FILE_PROP_ID = 12
CERT_DESCRIPTION_PROP_ID = 13
CERT_ACCESS_STATE_PROP_ID = 14
CERT_SIGNATURE_HASH_PROP_ID = 15
CERT_SMART_CARD_DATA_PROP_ID = 16
CERT_EFS_PROP_ID = 17
CERT_FORTEZZA_DATA_PROP_ID = 18
CERT_ARCHIVED_PROP_ID = 19
CERT_KEY_IDENTIFIER_PROP_ID = 20
CERT_AUTO_ENROLL_PROP_ID = 21
CERT_PUBKEY_ALG_PARA_PROP_ID = 22
CERT_CROSS_CERT_DIST_POINTS_PROP_ID = 23
CERT_ISSUER_PUBLIC_KEY_MD5_HASH_PROP_ID = 24
CERT_SUBJECT_PUBLIC_KEY_MD5_HASH_PROP_ID = 25
CERT_ENROLLMENT_PROP_ID = 26
CERT_DATE_STAMP_PROP_ID = 27
CERT_ISSUER_SERIAL_NUMBER_MD5_HASH_PROP_ID = 28
CERT_SUBJECT_NAME_MD5_HASH_PROP_ID = 29
CERT_EXTENDED_ERROR_INFO_PROP_ID = 30
CERT_RENEWAL_PROP_ID = 64
CERT_ARCHIVED_KEY_HASH_PROP_ID = 65
CERT_AUTO_ENROLL_RETRY_PROP_ID = 66
CERT_AIA_URL_RETRIEVED_PROP_ID = 67
CERT_AUTHORITY_INFO_ACCESS_PROP_ID = 68
CERT_BACKED_UP_PROP_ID = 69
CERT_OCSP_RESPONSE_PROP_ID = 70
CERT_REQUEST_ORIGINATOR_PROP_ID = 71
CERT_SOURCE_LOCATION_PROP_ID = 72
CERT_SOURCE_URL_PROP_ID = 73
CERT_NEW_KEY_PROP_ID = 74
CERT_OCSP_CACHE_PREFIX_PROP_ID = 75
CERT_SMART_CARD_ROOT_INFO_PROP_ID = 76
CERT_NO_AUTO_EXPIRE_CHECK_PROP_ID = 77
CERT_NCRYPT_KEY_HANDLE_PROP_ID = 78
CERT_HCRYPTPROV_OR_NCRYPT_KEY_HANDLE_PROP_ID = 79
CERT_SUBJECT_INFO_ACCESS_PROP_ID = 80
CERT_CA_OCSP_AUTHORITY_INFO_ACCESS_PROP_ID = 81
CERT_CA_DISABLE_CRL_PROP_ID = 82
CERT_ROOT_PROGRAM_CERT_POLICIES_PROP_ID = 83
CERT_ROOT_PROGRAM_NAME_CONSTRAINTS_PROP_ID = 84
CERT_SUBJECT_OCSP_AUTHORITY_INFO_ACCESS_PROP_ID = 85
CERT_SUBJECT_DISABLE_CRL_PROP_ID = 86
CERT_CEP_PROP_ID = 87
CERT_SIGN_HASH_CNG_ALG_PROP_ID = 89
CERT_SCARD_PIN_ID_PROP_ID = 90
CERT_SCARD_PIN_INFO_PROP_ID = 91
CERT_FIRST_RESERVED_PROP_ID = 92
CERT_LAST_RESERVED_PROP_ID = 0x00007FFF
CERT_FIRST_USER_PROP_ID = 0x00008000
CERT_LAST_USER_PROP_ID = 0x0000FFFF

szOID_CERT_PROP_ID_PREFIX = "1.3.6.1.4.1.311.10.11."
szOID_CERT_KEY_IDENTIFIER_PROP_ID = "1.3.6.1.4.1.311.10.11.20"
szOID_CERT_ISSUER_SERIAL_NUMBER_MD5_HASH_PROP_ID = "1.3.6.1.4.1.311.10.11.28"
szOID_CERT_SUBJECT_NAME_MD5_HASH_PROP_ID = "1.3.6.1.4.1.311.10.11.29"
CERT_ACCESS_STATE_WRITE_PERSIST_FLAG = 0x1
CERT_ACCESS_STATE_SYSTEM_STORE_FLAG = 0x2
CERT_ACCESS_STATE_LM_SYSTEM_STORE_FLAG = 0x4
CERT_SET_KEY_PROV_HANDLE_PROP_ID = 0x00000001
CERT_SET_KEY_CONTEXT_PROP_ID = 0x00000001
sz_CERT_STORE_PROV_MEMORY = "Memory"
sz_CERT_STORE_PROV_FILENAME_W = "File"
sz_CERT_STORE_PROV_FILENAME = sz_CERT_STORE_PROV_FILENAME_W
sz_CERT_STORE_PROV_SYSTEM_W = "System"
sz_CERT_STORE_PROV_SYSTEM = sz_CERT_STORE_PROV_SYSTEM_W
sz_CERT_STORE_PROV_PKCS7 = "PKCS7"
sz_CERT_STORE_PROV_SERIALIZED = "Serialized"
sz_CERT_STORE_PROV_COLLECTION = "Collection"
sz_CERT_STORE_PROV_SYSTEM_REGISTRY_W = "SystemRegistry"
sz_CERT_STORE_PROV_SYSTEM_REGISTRY = sz_CERT_STORE_PROV_SYSTEM_REGISTRY_W
sz_CERT_STORE_PROV_PHYSICAL_W = "Physical"
sz_CERT_STORE_PROV_PHYSICAL = sz_CERT_STORE_PROV_PHYSICAL_W
sz_CERT_STORE_PROV_SMART_CARD_W = "SmartCard"
sz_CERT_STORE_PROV_SMART_CARD = sz_CERT_STORE_PROV_SMART_CARD_W
sz_CERT_STORE_PROV_LDAP_W = "Ldap"
sz_CERT_STORE_PROV_LDAP = sz_CERT_STORE_PROV_LDAP_W
CERT_STORE_SIGNATURE_FLAG = 0x00000001
CERT_STORE_TIME_VALIDITY_FLAG = 0x00000002
CERT_STORE_REVOCATION_FLAG = 0x00000004
CERT_STORE_NO_CRL_FLAG = 0x00010000
CERT_STORE_NO_ISSUER_FLAG = 0x00020000
CERT_STORE_BASE_CRL_FLAG = 0x00000100
CERT_STORE_DELTA_CRL_FLAG = 0x00000200
CERT_STORE_NO_CRYPT_RELEASE_FLAG = 0x00000001
CERT_STORE_SET_LOCALIZED_NAME_FLAG = 0x00000002
CERT_STORE_DEFER_CLOSE_UNTIL_LAST_FREE_FLAG = 0x00000004
CERT_STORE_DELETE_FLAG = 0x00000010
CERT_STORE_UNSAFE_PHYSICAL_FLAG = 0x00000020
CERT_STORE_SHARE_STORE_FLAG = 0x00000040
CERT_STORE_SHARE_CONTEXT_FLAG = 0x00000080
CERT_STORE_MANIFOLD_FLAG = 0x00000100
CERT_STORE_ENUM_ARCHIVED_FLAG = 0x00000200
CERT_STORE_UPDATE_KEYID_FLAG = 0x00000400
CERT_STORE_BACKUP_RESTORE_FLAG = 0x00000800
CERT_STORE_READONLY_FLAG = 0x00008000
CERT_STORE_OPEN_EXISTING_FLAG = 0x00004000
CERT_STORE_CREATE_NEW_FLAG = 0x00002000
CERT_STORE_MAXIMUM_ALLOWED_FLAG = 0x00001000
CERT_SYSTEM_STORE_MASK = -65536
CERT_SYSTEM_STORE_RELOCATE_FLAG = -2147483648
CERT_SYSTEM_STORE_UNPROTECTED_FLAG = 0x40000000
CERT_SYSTEM_STORE_LOCATION_MASK = 0x00FF0000
CERT_SYSTEM_STORE_LOCATION_SHIFT = 16
CERT_SYSTEM_STORE_CURRENT_USER_ID = 1
CERT_SYSTEM_STORE_LOCAL_MACHINE_ID = 2
CERT_SYSTEM_STORE_CURRENT_SERVICE_ID = 4
CERT_SYSTEM_STORE_SERVICES_ID = 5
CERT_SYSTEM_STORE_USERS_ID = 6
CERT_SYSTEM_STORE_CURRENT_USER_GROUP_POLICY_ID = 7
CERT_SYSTEM_STORE_LOCAL_MACHINE_GROUP_POLICY_ID = 8
CERT_SYSTEM_STORE_LOCAL_MACHINE_ENTERPRISE_ID = 9
CERT_SYSTEM_STORE_CURRENT_USER = (
    CERT_SYSTEM_STORE_CURRENT_USER_ID << CERT_SYSTEM_STORE_LOCATION_SHIFT
)
CERT_SYSTEM_STORE_LOCAL_MACHINE = (
    CERT_SYSTEM_STORE_LOCAL_MACHINE_ID << CERT_SYSTEM_STORE_LOCATION_SHIFT
)
CERT_SYSTEM_STORE_CURRENT_SERVICE = (
    CERT_SYSTEM_STORE_CURRENT_SERVICE_ID << CERT_SYSTEM_STORE_LOCATION_SHIFT
)
CERT_SYSTEM_STORE_SERVICES = (
    CERT_SYSTEM_STORE_SERVICES_ID << CERT_SYSTEM_STORE_LOCATION_SHIFT
)
CERT_SYSTEM_STORE_USERS = CERT_SYSTEM_STORE_USERS_ID << CERT_SYSTEM_STORE_LOCATION_SHIFT
CERT_SYSTEM_STORE_CURRENT_USER_GROUP_POLICY = (
    CERT_SYSTEM_STORE_CURRENT_USER_GROUP_POLICY_ID << CERT_SYSTEM_STORE_LOCATION_SHIFT
)
CERT_SYSTEM_STORE_LOCAL_MACHINE_GROUP_POLICY = (
    CERT_SYSTEM_STORE_LOCAL_MACHINE_GROUP_POLICY_ID << CERT_SYSTEM_STORE_LOCATION_SHIFT
)
CERT_SYSTEM_STORE_LOCAL_MACHINE_ENTERPRISE = (
    CERT_SYSTEM_STORE_LOCAL_MACHINE_ENTERPRISE_ID << CERT_SYSTEM_STORE_LOCATION_SHIFT
)
CERT_PROT_ROOT_DISABLE_CURRENT_USER_FLAG = 0x1
CERT_PROT_ROOT_INHIBIT_ADD_AT_INIT_FLAG = 0x2
CERT_PROT_ROOT_INHIBIT_PURGE_LM_FLAG = 0x4
CERT_PROT_ROOT_DISABLE_LM_AUTH_FLAG = 0x8
CERT_PROT_ROOT_ONLY_LM_GPT_FLAG = 0x8
CERT_PROT_ROOT_DISABLE_NT_AUTH_REQUIRED_FLAG = 0x10
CERT_PROT_ROOT_DISABLE_NOT_DEFINED_NAME_CONSTRAINT_FLAG = 0x20
CERT_TRUST_PUB_ALLOW_TRUST_MASK = 0x00000003
CERT_TRUST_PUB_ALLOW_END_USER_TRUST = 0x00000000
CERT_TRUST_PUB_ALLOW_MACHINE_ADMIN_TRUST = 0x00000001
CERT_TRUST_PUB_ALLOW_ENTERPRISE_ADMIN_TRUST = 0x00000002
CERT_TRUST_PUB_CHECK_PUBLISHER_REV_FLAG = 0x00000100
CERT_TRUST_PUB_CHECK_TIMESTAMP_REV_FLAG = 0x00000200

CERT_AUTH_ROOT_AUTO_UPDATE_DISABLE_UNTRUSTED_ROOT_LOGGING_FLAG = 0x1
CERT_AUTH_ROOT_AUTO_UPDATE_DISABLE_PARTIAL_CHAIN_LOGGING_FLAG = 0x2
CERT_AUTH_ROOT_AUTO_UPDATE_ROOT_DIR_URL_VALUE_NAME = "RootDirUrl"
CERT_AUTH_ROOT_AUTO_UPDATE_SYNC_DELTA_TIME_VALUE_NAME = "SyncDeltaTime"
CERT_AUTH_ROOT_AUTO_UPDATE_FLAGS_VALUE_NAME = "Flags"
CERT_AUTH_ROOT_CTL_FILENAME = "authroot.stl"
CERT_AUTH_ROOT_CTL_FILENAME_A = "authroot.stl"
CERT_AUTH_ROOT_CAB_FILENAME = "authrootstl.cab"
CERT_AUTH_ROOT_SEQ_FILENAME = "authrootseq.txt"
CERT_AUTH_ROOT_CERT_EXT = ".crt"

CERT_GROUP_POLICY_SYSTEM_STORE_REGPATH = (
    r"Software\Policies\Microsoft\SystemCertificates"
)
CERT_EFSBLOB_REGPATH = CERT_GROUP_POLICY_SYSTEM_STORE_REGPATH + r"\EFS"
CERT_EFSBLOB_VALUE_NAME = "EFSBlob"
CERT_PROT_ROOT_FLAGS_REGPATH = (
    CERT_GROUP_POLICY_SYSTEM_STORE_REGPATH + r"\Root\ProtectedRoots"
)
CERT_PROT_ROOT_FLAGS_VALUE_NAME = "Flags"
CERT_TRUST_PUB_SAFER_GROUP_POLICY_REGPATH = (
    CERT_GROUP_POLICY_SYSTEM_STORE_REGPATH + r"\TrustedPublisher\Safer"
)
CERT_LOCAL_MACHINE_SYSTEM_STORE_REGPATH = r"Software\Microsoft\SystemCertificates"
CERT_TRUST_PUB_SAFER_LOCAL_MACHINE_REGPATH = (
    CERT_LOCAL_MACHINE_SYSTEM_STORE_REGPATH + r"\TrustedPublisher\Safer"
)
CERT_TRUST_PUB_AUTHENTICODE_FLAGS_VALUE_NAME = "AuthenticodeFlags"
CERT_OCM_SUBCOMPONENTS_LOCAL_MACHINE_REGPATH = (
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Setup\OC Manager\Subcomponents"
)
CERT_OCM_SUBCOMPONENTS_ROOT_AUTO_UPDATE_VALUE_NAME = r"RootAutoUpdate"
CERT_DISABLE_ROOT_AUTO_UPDATE_REGPATH = (
    CERT_GROUP_POLICY_SYSTEM_STORE_REGPATH + r"\AuthRoot"
)
CERT_DISABLE_ROOT_AUTO_UPDATE_VALUE_NAME = "DisableRootAutoUpdate"
CERT_AUTH_ROOT_AUTO_UPDATE_LOCAL_MACHINE_REGPATH = (
    CERT_LOCAL_MACHINE_SYSTEM_STORE_REGPATH + r"\AuthRoot\AutoUpdate"
)

CERT_REGISTRY_STORE_REMOTE_FLAG = 0x10000
CERT_REGISTRY_STORE_SERIALIZED_FLAG = 0x20000
CERT_REGISTRY_STORE_CLIENT_GPT_FLAG = -2147483648
CERT_REGISTRY_STORE_LM_GPT_FLAG = 0x01000000
CERT_REGISTRY_STORE_ROAMING_FLAG = 0x40000
CERT_REGISTRY_STORE_MY_IE_DIRTY_FLAG = 0x80000
CERT_IE_DIRTY_FLAGS_REGPATH = r"Software\Microsoft\Cryptography\IEDirtyFlags"

CERT_FILE_STORE_COMMIT_ENABLE_FLAG = 0x10000
CERT_LDAP_STORE_SIGN_FLAG = 0x10000
CERT_LDAP_STORE_AREC_EXCLUSIVE_FLAG = 0x20000
CERT_LDAP_STORE_OPENED_FLAG = 0x40000
CERT_LDAP_STORE_UNBIND_FLAG = 0x80000
CRYPT_OID_OPEN_STORE_PROV_FUNC = "CertDllOpenStoreProv"

CERT_STORE_PROV_EXTERNAL_FLAG = 0x1
CERT_STORE_PROV_DELETED_FLAG = 0x2
CERT_STORE_PROV_NO_PERSIST_FLAG = 0x4
CERT_STORE_PROV_SYSTEM_STORE_FLAG = 0x8
CERT_STORE_PROV_LM_SYSTEM_STORE_FLAG = 0x10
CERT_STORE_PROV_CLOSE_FUNC = 0
CERT_STORE_PROV_READ_CERT_FUNC = 1
CERT_STORE_PROV_WRITE_CERT_FUNC = 2
CERT_STORE_PROV_DELETE_CERT_FUNC = 3
CERT_STORE_PROV_SET_CERT_PROPERTY_FUNC = 4
CERT_STORE_PROV_READ_CRL_FUNC = 5
CERT_STORE_PROV_WRITE_CRL_FUNC = 6
CERT_STORE_PROV_DELETE_CRL_FUNC = 7
CERT_STORE_PROV_SET_CRL_PROPERTY_FUNC = 8
CERT_STORE_PROV_READ_CTL_FUNC = 9
CERT_STORE_PROV_WRITE_CTL_FUNC = 10
CERT_STORE_PROV_DELETE_CTL_FUNC = 11
CERT_STORE_PROV_SET_CTL_PROPERTY_FUNC = 12
CERT_STORE_PROV_CONTROL_FUNC = 13
CERT_STORE_PROV_FIND_CERT_FUNC = 14
CERT_STORE_PROV_FREE_FIND_CERT_FUNC = 15
CERT_STORE_PROV_GET_CERT_PROPERTY_FUNC = 16
CERT_STORE_PROV_FIND_CRL_FUNC = 17
CERT_STORE_PROV_FREE_FIND_CRL_FUNC = 18
CERT_STORE_PROV_GET_CRL_PROPERTY_FUNC = 19
CERT_STORE_PROV_FIND_CTL_FUNC = 20
CERT_STORE_PROV_FREE_FIND_CTL_FUNC = 21
CERT_STORE_PROV_GET_CTL_PROPERTY_FUNC = 22
CERT_STORE_PROV_WRITE_ADD_FLAG = 0x1
CERT_STORE_SAVE_AS_STORE = 1
CERT_STORE_SAVE_AS_PKCS7 = 2
CERT_STORE_SAVE_TO_FILE = 1
CERT_STORE_SAVE_TO_MEMORY = 2
CERT_STORE_SAVE_TO_FILENAME_A = 3
CERT_STORE_SAVE_TO_FILENAME_W = 4
CERT_STORE_SAVE_TO_FILENAME = CERT_STORE_SAVE_TO_FILENAME_W
CERT_CLOSE_STORE_FORCE_FLAG = 0x00000001
CERT_CLOSE_STORE_CHECK_FLAG = 0x00000002
CERT_COMPARE_MASK = 0xFFFF
CERT_COMPARE_SHIFT = 16
CERT_COMPARE_ANY = 0
CERT_COMPARE_SHA1_HASH = 1
CERT_COMPARE_NAME = 2
CERT_COMPARE_ATTR = 3
CERT_COMPARE_MD5_HASH = 4
CERT_COMPARE_PROPERTY = 5
CERT_COMPARE_PUBLIC_KEY = 6
CERT_COMPARE_HASH = CERT_COMPARE_SHA1_HASH
CERT_COMPARE_NAME_STR_A = 7
CERT_COMPARE_NAME_STR_W = 8
CERT_COMPARE_KEY_SPEC = 9
CERT_COMPARE_ENHKEY_USAGE = 10
CERT_COMPARE_CTL_USAGE = CERT_COMPARE_ENHKEY_USAGE
CERT_COMPARE_SUBJECT_CERT = 11
CERT_COMPARE_ISSUER_OF = 12
CERT_COMPARE_EXISTING = 13
CERT_COMPARE_SIGNATURE_HASH = 14
CERT_COMPARE_KEY_IDENTIFIER = 15
CERT_COMPARE_CERT_ID = 16
CERT_COMPARE_CROSS_CERT_DIST_POINTS = 17
CERT_COMPARE_PUBKEY_MD5_HASH = 18
CERT_FIND_ANY = CERT_COMPARE_ANY << CERT_COMPARE_SHIFT
CERT_FIND_SHA1_HASH = CERT_COMPARE_SHA1_HASH << CERT_COMPARE_SHIFT
CERT_FIND_MD5_HASH = CERT_COMPARE_MD5_HASH << CERT_COMPARE_SHIFT
CERT_FIND_SIGNATURE_HASH = CERT_COMPARE_SIGNATURE_HASH << CERT_COMPARE_SHIFT
CERT_FIND_KEY_IDENTIFIER = CERT_COMPARE_KEY_IDENTIFIER << CERT_COMPARE_SHIFT
CERT_FIND_HASH = CERT_FIND_SHA1_HASH
CERT_FIND_PROPERTY = CERT_COMPARE_PROPERTY << CERT_COMPARE_SHIFT
CERT_FIND_PUBLIC_KEY = CERT_COMPARE_PUBLIC_KEY << CERT_COMPARE_SHIFT
CERT_FIND_SUBJECT_NAME = (
    CERT_COMPARE_NAME << CERT_COMPARE_SHIFT | CERT_INFO_SUBJECT_FLAG
)
CERT_FIND_SUBJECT_ATTR = (
    CERT_COMPARE_ATTR << CERT_COMPARE_SHIFT | CERT_INFO_SUBJECT_FLAG
)
CERT_FIND_ISSUER_NAME = CERT_COMPARE_NAME << CERT_COMPARE_SHIFT | CERT_INFO_ISSUER_FLAG
CERT_FIND_ISSUER_ATTR = CERT_COMPARE_ATTR << CERT_COMPARE_SHIFT | CERT_INFO_ISSUER_FLAG
CERT_FIND_SUBJECT_STR_A = (
    CERT_COMPARE_NAME_STR_A << CERT_COMPARE_SHIFT | CERT_INFO_SUBJECT_FLAG
)
CERT_FIND_SUBJECT_STR_W = (
    CERT_COMPARE_NAME_STR_W << CERT_COMPARE_SHIFT | CERT_INFO_SUBJECT_FLAG
)
CERT_FIND_SUBJECT_STR = CERT_FIND_SUBJECT_STR_W
CERT_FIND_ISSUER_STR_A = (
    CERT_COMPARE_NAME_STR_A << CERT_COMPARE_SHIFT | CERT_INFO_ISSUER_FLAG
)
CERT_FIND_ISSUER_STR_W = (
    CERT_COMPARE_NAME_STR_W << CERT_COMPARE_SHIFT | CERT_INFO_ISSUER_FLAG
)
CERT_FIND_ISSUER_STR = CERT_FIND_ISSUER_STR_W
CERT_FIND_KEY_SPEC = CERT_COMPARE_KEY_SPEC << CERT_COMPARE_SHIFT
CERT_FIND_ENHKEY_USAGE = CERT_COMPARE_ENHKEY_USAGE << CERT_COMPARE_SHIFT
CERT_FIND_CTL_USAGE = CERT_FIND_ENHKEY_USAGE
CERT_FIND_SUBJECT_CERT = CERT_COMPARE_SUBJECT_CERT << CERT_COMPARE_SHIFT
CERT_FIND_ISSUER_OF = CERT_COMPARE_ISSUER_OF << CERT_COMPARE_SHIFT
CERT_FIND_EXISTING = CERT_COMPARE_EXISTING << CERT_COMPARE_SHIFT
CERT_FIND_CERT_ID = CERT_COMPARE_CERT_ID << CERT_COMPARE_SHIFT
CERT_FIND_CROSS_CERT_DIST_POINTS = (
    CERT_COMPARE_CROSS_CERT_DIST_POINTS << CERT_COMPARE_SHIFT
)
CERT_FIND_PUBKEY_MD5_HASH = CERT_COMPARE_PUBKEY_MD5_HASH << CERT_COMPARE_SHIFT
CERT_FIND_OPTIONAL_ENHKEY_USAGE_FLAG = 0x1
CERT_FIND_EXT_ONLY_ENHKEY_USAGE_FLAG = 0x2
CERT_FIND_PROP_ONLY_ENHKEY_USAGE_FLAG = 0x4
CERT_FIND_NO_ENHKEY_USAGE_FLAG = 0x8
CERT_FIND_OR_ENHKEY_USAGE_FLAG = 0x10
CERT_FIND_VALID_ENHKEY_USAGE_FLAG = 0x20
CERT_FIND_OPTIONAL_CTL_USAGE_FLAG = CERT_FIND_OPTIONAL_ENHKEY_USAGE_FLAG
CERT_FIND_EXT_ONLY_CTL_USAGE_FLAG = CERT_FIND_EXT_ONLY_ENHKEY_USAGE_FLAG
CERT_FIND_PROP_ONLY_CTL_USAGE_FLAG = CERT_FIND_PROP_ONLY_ENHKEY_USAGE_FLAG
CERT_FIND_NO_CTL_USAGE_FLAG = CERT_FIND_NO_ENHKEY_USAGE_FLAG
CERT_FIND_OR_CTL_USAGE_FLAG = CERT_FIND_OR_ENHKEY_USAGE_FLAG
CERT_FIND_VALID_CTL_USAGE_FLAG = CERT_FIND_VALID_ENHKEY_USAGE_FLAG
CERT_SET_PROPERTY_IGNORE_PERSIST_ERROR_FLAG = -2147483648
CERT_SET_PROPERTY_INHIBIT_PERSIST_FLAG = 0x40000000
CTL_ENTRY_FROM_PROP_CHAIN_FLAG = 0x1
CRL_FIND_ANY = 0
CRL_FIND_ISSUED_BY = 1
CRL_FIND_EXISTING = 2
CRL_FIND_ISSUED_FOR = 3
CRL_FIND_ISSUED_BY_AKI_FLAG = 0x1
CRL_FIND_ISSUED_BY_SIGNATURE_FLAG = 0x2
CRL_FIND_ISSUED_BY_DELTA_FLAG = 0x4
CRL_FIND_ISSUED_BY_BASE_FLAG = 0x8
CERT_STORE_ADD_NEW = 1
CERT_STORE_ADD_USE_EXISTING = 2
CERT_STORE_ADD_REPLACE_EXISTING = 3
CERT_STORE_ADD_ALWAYS = 4
CERT_STORE_ADD_REPLACE_EXISTING_INHERIT_PROPERTIES = 5
CERT_STORE_ADD_NEWER = 6
CERT_STORE_ADD_NEWER_INHERIT_PROPERTIES = 7
CERT_STORE_CERTIFICATE_CONTEXT = 1
CERT_STORE_CRL_CONTEXT = 2
CERT_STORE_CTL_CONTEXT = 3

CERT_STORE_ALL_CONTEXT_FLAG = -1
CERT_STORE_CERTIFICATE_CONTEXT_FLAG = 1 << CERT_STORE_CERTIFICATE_CONTEXT
CERT_STORE_CRL_CONTEXT_FLAG = 1 << CERT_STORE_CRL_CONTEXT
CERT_STORE_CTL_CONTEXT_FLAG = 1 << CERT_STORE_CTL_CONTEXT
CTL_ANY_SUBJECT_TYPE = 1
CTL_CERT_SUBJECT_TYPE = 2
CTL_FIND_ANY = 0
CTL_FIND_SHA1_HASH = 1
CTL_FIND_MD5_HASH = 2
CTL_FIND_USAGE = 3
CTL_FIND_SUBJECT = 4
CTL_FIND_EXISTING = 5
CTL_FIND_NO_LIST_ID_CBDATA = -1
CTL_FIND_SAME_USAGE_FLAG = 0x1
CERT_STORE_CTRL_RESYNC = 1
CERT_STORE_CTRL_NOTIFY_CHANGE = 2
CERT_STORE_CTRL_COMMIT = 3
CERT_STORE_CTRL_AUTO_RESYNC = 4
CERT_STORE_CTRL_CANCEL_NOTIFY = 5
CERT_STORE_CTRL_INHIBIT_DUPLICATE_HANDLE_FLAG = 0x1
CERT_STORE_CTRL_COMMIT_FORCE_FLAG = 0x1
CERT_STORE_CTRL_COMMIT_CLEAR_FLAG = 0x2
CERT_STORE_LOCALIZED_NAME_PROP_ID = 0x1000
CERT_CREATE_CONTEXT_NOCOPY_FLAG = 0x1
CERT_CREATE_CONTEXT_SORTED_FLAG = 0x2
CERT_CREATE_CONTEXT_NO_HCRYPTMSG_FLAG = 0x4
CERT_CREATE_CONTEXT_NO_ENTRY_FLAG = 0x8

CERT_PHYSICAL_STORE_ADD_ENABLE_FLAG = 0x1
CERT_PHYSICAL_STORE_OPEN_DISABLE_FLAG = 0x2
CERT_PHYSICAL_STORE_REMOTE_OPEN_DISABLE_FLAG = 0x4
CERT_PHYSICAL_STORE_INSERT_COMPUTER_NAME_ENABLE_FLAG = 0x8
CERT_PHYSICAL_STORE_PREDEFINED_ENUM_FLAG = 0x1

# Names of physical cert stores
CERT_PHYSICAL_STORE_DEFAULT_NAME = ".Default"
CERT_PHYSICAL_STORE_GROUP_POLICY_NAME = ".GroupPolicy"
CERT_PHYSICAL_STORE_LOCAL_MACHINE_NAME = ".LocalMachine"
CERT_PHYSICAL_STORE_DS_USER_CERTIFICATE_NAME = ".UserCertificate"
CERT_PHYSICAL_STORE_LOCAL_MACHINE_GROUP_POLICY_NAME = ".LocalMachineGroupPolicy"
CERT_PHYSICAL_STORE_ENTERPRISE_NAME = ".Enterprise"
CERT_PHYSICAL_STORE_AUTH_ROOT_NAME = ".AuthRoot"
CERT_PHYSICAL_STORE_SMART_CARD_NAME = ".SmartCard"

CRYPT_OID_OPEN_SYSTEM_STORE_PROV_FUNC = "CertDllOpenSystemStoreProv"
CRYPT_OID_REGISTER_SYSTEM_STORE_FUNC = "CertDllRegisterSystemStore"
CRYPT_OID_UNREGISTER_SYSTEM_STORE_FUNC = "CertDllUnregisterSystemStore"
CRYPT_OID_ENUM_SYSTEM_STORE_FUNC = "CertDllEnumSystemStore"
CRYPT_OID_REGISTER_PHYSICAL_STORE_FUNC = "CertDllRegisterPhysicalStore"
CRYPT_OID_UNREGISTER_PHYSICAL_STORE_FUNC = "CertDllUnregisterPhysicalStore"
CRYPT_OID_ENUM_PHYSICAL_STORE_FUNC = "CertDllEnumPhysicalStore"
CRYPT_OID_SYSTEM_STORE_LOCATION_VALUE_NAME = "SystemStoreLocation"

CMSG_TRUSTED_SIGNER_FLAG = 0x1
CMSG_SIGNER_ONLY_FLAG = 0x2
CMSG_USE_SIGNER_INDEX_FLAG = 0x4
CMSG_CMS_ENCAPSULATED_CTL_FLAG = 0x00008000
CMSG_ENCODE_SORTED_CTL_FLAG = 0x1
CMSG_ENCODE_HASHED_SUBJECT_IDENTIFIER_FLAG = 0x2
CERT_VERIFY_INHIBIT_CTL_UPDATE_FLAG = 0x1
CERT_VERIFY_TRUSTED_SIGNERS_FLAG = 0x2
CERT_VERIFY_NO_TIME_CHECK_FLAG = 0x4
CERT_VERIFY_ALLOW_MORE_USAGE_FLAG = 0x8
CERT_VERIFY_UPDATED_CTL_FLAG = 0x1
CERT_CONTEXT_REVOCATION_TYPE = 1
CERT_VERIFY_REV_CHAIN_FLAG = 0x00000001
CERT_VERIFY_CACHE_ONLY_BASED_REVOCATION = 0x00000002
CERT_VERIFY_REV_ACCUMULATIVE_TIMEOUT_FLAG = 0x00000004
CERT_UNICODE_IS_RDN_ATTRS_FLAG = 0x1
CERT_CASE_INSENSITIVE_IS_RDN_ATTRS_FLAG = 0x2
CRYPT_VERIFY_CERT_SIGN_SUBJECT_BLOB = 1
CRYPT_VERIFY_CERT_SIGN_SUBJECT_CERT = 2
CRYPT_VERIFY_CERT_SIGN_SUBJECT_CRL = 3
CRYPT_VERIFY_CERT_SIGN_ISSUER_PUBKEY = 1
CRYPT_VERIFY_CERT_SIGN_ISSUER_CERT = 2
CRYPT_VERIFY_CERT_SIGN_ISSUER_CHAIN = 3
CRYPT_VERIFY_CERT_SIGN_ISSUER_NULL = 4
CRYPT_DEFAULT_CONTEXT_AUTO_RELEASE_FLAG = 0x00000001
CRYPT_DEFAULT_CONTEXT_PROCESS_FLAG = 0x00000002
CRYPT_DEFAULT_CONTEXT_CERT_SIGN_OID = 1
CRYPT_DEFAULT_CONTEXT_MULTI_CERT_SIGN_OID = 2
CRYPT_OID_EXPORT_PUBLIC_KEY_INFO_FUNC = "CryptDllExportPublicKeyInfoEx"
CRYPT_OID_IMPORT_PUBLIC_KEY_INFO_FUNC = "CryptDllImportPublicKeyInfoEx"
CRYPT_ACQUIRE_CACHE_FLAG = 0x00000001
CRYPT_ACQUIRE_USE_PROV_INFO_FLAG = 0x00000002
CRYPT_ACQUIRE_COMPARE_KEY_FLAG = 0x00000004
CRYPT_ACQUIRE_SILENT_FLAG = 0x00000040
CRYPT_FIND_USER_KEYSET_FLAG = 0x00000001
CRYPT_FIND_MACHINE_KEYSET_FLAG = 0x00000002
CRYPT_FIND_SILENT_KEYSET_FLAG = 0x00000040
CRYPT_OID_IMPORT_PRIVATE_KEY_INFO_FUNC = "CryptDllImportPrivateKeyInfoEx"
CRYPT_OID_EXPORT_PRIVATE_KEY_INFO_FUNC = "CryptDllExportPrivateKeyInfoEx"
CRYPT_DELETE_KEYSET = CRYPT_DELETEKEYSET
CERT_SIMPLE_NAME_STR = 1
CERT_OID_NAME_STR = 2
CERT_X500_NAME_STR = 3
CERT_NAME_STR_SEMICOLON_FLAG = 0x40000000
CERT_NAME_STR_NO_PLUS_FLAG = 0x20000000
CERT_NAME_STR_NO_QUOTING_FLAG = 0x10000000
CERT_NAME_STR_CRLF_FLAG = 0x08000000
CERT_NAME_STR_COMMA_FLAG = 0x04000000
CERT_NAME_STR_REVERSE_FLAG = 0x02000000
CERT_NAME_STR_DISABLE_IE4_UTF8_FLAG = 0x00010000
CERT_NAME_STR_ENABLE_T61_UNICODE_FLAG = 0x00020000
CERT_NAME_STR_ENABLE_UTF8_UNICODE_FLAG = 0x00040000
CERT_NAME_EMAIL_TYPE = 1
CERT_NAME_RDN_TYPE = 2
CERT_NAME_ATTR_TYPE = 3
CERT_NAME_SIMPLE_DISPLAY_TYPE = 4
CERT_NAME_FRIENDLY_DISPLAY_TYPE = 5
CERT_NAME_DNS_TYPE = 6
CERT_NAME_URL_TYPE = 7
CERT_NAME_UPN_TYPE = 8
CERT_NAME_ISSUER_FLAG = 0x1
CERT_NAME_DISABLE_IE4_UTF8_FLAG = 0x00010000
CRYPT_MESSAGE_BARE_CONTENT_OUT_FLAG = 0x00000001
CRYPT_MESSAGE_ENCAPSULATED_CONTENT_OUT_FLAG = 0x00000002
CRYPT_MESSAGE_KEYID_SIGNER_FLAG = 0x00000004
CRYPT_MESSAGE_SILENT_KEYSET_FLAG = 0x00000040
CRYPT_MESSAGE_KEYID_RECIPIENT_FLAG = 0x4
CERT_QUERY_OBJECT_FILE = 0x00000001
CERT_QUERY_OBJECT_BLOB = 0x00000002
CERT_QUERY_CONTENT_CERT = 1
CERT_QUERY_CONTENT_CTL = 2
CERT_QUERY_CONTENT_CRL = 3
CERT_QUERY_CONTENT_SERIALIZED_STORE = 4
CERT_QUERY_CONTENT_SERIALIZED_CERT = 5
CERT_QUERY_CONTENT_SERIALIZED_CTL = 6
CERT_QUERY_CONTENT_SERIALIZED_CRL = 7
CERT_QUERY_CONTENT_PKCS7_SIGNED = 8
CERT_QUERY_CONTENT_PKCS7_UNSIGNED = 9
CERT_QUERY_CONTENT_PKCS7_SIGNED_EMBED = 10
CERT_QUERY_CONTENT_PKCS10 = 11
CERT_QUERY_CONTENT_PFX = 12
CERT_QUERY_CONTENT_CERT_PAIR = 13
CERT_QUERY_CONTENT_FLAG_CERT = 1 << CERT_QUERY_CONTENT_CERT
CERT_QUERY_CONTENT_FLAG_CTL = 1 << CERT_QUERY_CONTENT_CTL
CERT_QUERY_CONTENT_FLAG_CRL = 1 << CERT_QUERY_CONTENT_CRL
CERT_QUERY_CONTENT_FLAG_SERIALIZED_STORE = 1 << CERT_QUERY_CONTENT_SERIALIZED_STORE
CERT_QUERY_CONTENT_FLAG_SERIALIZED_CERT = 1 << CERT_QUERY_CONTENT_SERIALIZED_CERT
CERT_QUERY_CONTENT_FLAG_SERIALIZED_CTL = 1 << CERT_QUERY_CONTENT_SERIALIZED_CTL
CERT_QUERY_CONTENT_FLAG_SERIALIZED_CRL = 1 << CERT_QUERY_CONTENT_SERIALIZED_CRL
CERT_QUERY_CONTENT_FLAG_PKCS7_SIGNED = 1 << CERT_QUERY_CONTENT_PKCS7_SIGNED
CERT_QUERY_CONTENT_FLAG_PKCS7_UNSIGNED = 1 << CERT_QUERY_CONTENT_PKCS7_UNSIGNED
CERT_QUERY_CONTENT_FLAG_PKCS7_SIGNED_EMBED = 1 << CERT_QUERY_CONTENT_PKCS7_SIGNED_EMBED
CERT_QUERY_CONTENT_FLAG_PKCS10 = 1 << CERT_QUERY_CONTENT_PKCS10
CERT_QUERY_CONTENT_FLAG_PFX = 1 << CERT_QUERY_CONTENT_PFX
CERT_QUERY_CONTENT_FLAG_CERT_PAIR = 1 << CERT_QUERY_CONTENT_CERT_PAIR
CERT_QUERY_CONTENT_FLAG_ALL = (
    CERT_QUERY_CONTENT_FLAG_CERT
    | CERT_QUERY_CONTENT_FLAG_CTL
    | CERT_QUERY_CONTENT_FLAG_CRL
    | CERT_QUERY_CONTENT_FLAG_SERIALIZED_STORE
    | CERT_QUERY_CONTENT_FLAG_SERIALIZED_CERT
    | CERT_QUERY_CONTENT_FLAG_SERIALIZED_CTL
    | CERT_QUERY_CONTENT_FLAG_SERIALIZED_CRL
    | CERT_QUERY_CONTENT_FLAG_PKCS7_SIGNED
    | CERT_QUERY_CONTENT_FLAG_PKCS7_UNSIGNED
    | CERT_QUERY_CONTENT_FLAG_PKCS7_SIGNED_EMBED
    | CERT_QUERY_CONTENT_FLAG_PKCS10
    | CERT_QUERY_CONTENT_FLAG_PFX
    | CERT_QUERY_CONTENT_FLAG_CERT_PAIR
)
CERT_QUERY_FORMAT_BINARY = 1
CERT_QUERY_FORMAT_BASE64_ENCODED = 2
CERT_QUERY_FORMAT_ASN_ASCII_HEX_ENCODED = 3
CERT_QUERY_FORMAT_FLAG_BINARY = 1 << CERT_QUERY_FORMAT_BINARY
CERT_QUERY_FORMAT_FLAG_BASE64_ENCODED = 1 << CERT_QUERY_FORMAT_BASE64_ENCODED
CERT_QUERY_FORMAT_FLAG_ASN_ASCII_HEX_ENCODED = (
    1 << CERT_QUERY_FORMAT_ASN_ASCII_HEX_ENCODED
)
CERT_QUERY_FORMAT_FLAG_ALL = (
    CERT_QUERY_FORMAT_FLAG_BINARY
    | CERT_QUERY_FORMAT_FLAG_BASE64_ENCODED
    | CERT_QUERY_FORMAT_FLAG_ASN_ASCII_HEX_ENCODED
)

CREDENTIAL_OID_PASSWORD_CREDENTIALS_A = 1
CREDENTIAL_OID_PASSWORD_CREDENTIALS_W = 2
CREDENTIAL_OID_PASSWORD_CREDENTIALS = CREDENTIAL_OID_PASSWORD_CREDENTIALS_W

SCHEME_OID_RETRIEVE_ENCODED_OBJECT_FUNC = "SchemeDllRetrieveEncodedObject"
SCHEME_OID_RETRIEVE_ENCODED_OBJECTW_FUNC = "SchemeDllRetrieveEncodedObjectW"
CONTEXT_OID_CREATE_OBJECT_CONTEXT_FUNC = "ContextDllCreateObjectContext"
CONTEXT_OID_CERTIFICATE = 1
CONTEXT_OID_CRL = 2
CONTEXT_OID_CTL = 3
CONTEXT_OID_PKCS7 = 4
CONTEXT_OID_CAPI2_ANY = 5
CONTEXT_OID_OCSP_RESP = 6

CRYPT_RETRIEVE_MULTIPLE_OBJECTS = 0x00000001
CRYPT_CACHE_ONLY_RETRIEVAL = 0x00000002
CRYPT_WIRE_ONLY_RETRIEVAL = 0x00000004
CRYPT_DONT_CACHE_RESULT = 0x00000008
CRYPT_ASYNC_RETRIEVAL = 0x00000010
CRYPT_STICKY_CACHE_RETRIEVAL = 0x00001000
CRYPT_LDAP_SCOPE_BASE_ONLY_RETRIEVAL = 0x00002000
CRYPT_OFFLINE_CHECK_RETRIEVAL = 0x00004000
CRYPT_LDAP_INSERT_ENTRY_ATTRIBUTE = 0x00008000
CRYPT_LDAP_SIGN_RETRIEVAL = 0x00010000
CRYPT_NO_AUTH_RETRIEVAL = 0x00020000
CRYPT_LDAP_AREC_EXCLUSIVE_RETRIEVAL = 0x00040000
CRYPT_AIA_RETRIEVAL = 0x00080000
CRYPT_VERIFY_CONTEXT_SIGNATURE = 0x00000020
CRYPT_VERIFY_DATA_HASH = 0x00000040
CRYPT_KEEP_TIME_VALID = 0x00000080
CRYPT_DONT_VERIFY_SIGNATURE = 0x00000100
CRYPT_DONT_CHECK_TIME_VALIDITY = 0x00000200
CRYPT_CHECK_FRESHNESS_TIME_VALIDITY = 0x00000400
CRYPT_ACCUMULATIVE_TIMEOUT = 0x00000800
CRYPT_PARAM_ASYNC_RETRIEVAL_COMPLETION = 1
CRYPT_PARAM_CANCEL_ASYNC_RETRIEVAL = 2
CRYPT_GET_URL_FROM_PROPERTY = 0x00000001
CRYPT_GET_URL_FROM_EXTENSION = 0x00000002
CRYPT_GET_URL_FROM_UNAUTH_ATTRIBUTE = 0x00000004
CRYPT_GET_URL_FROM_AUTH_ATTRIBUTE = 0x00000008
URL_OID_GET_OBJECT_URL_FUNC = "UrlDllGetObjectUrl"
TIME_VALID_OID_GET_OBJECT_FUNC = "TimeValidDllGetObject"
TIME_VALID_OID_FLUSH_OBJECT_FUNC = "TimeValidDllFlushObject"

TIME_VALID_OID_GET_CTL = 1
TIME_VALID_OID_GET_CRL = 2
TIME_VALID_OID_GET_CRL_FROM_CERT = 3
TIME_VALID_OID_GET_FRESHEST_CRL_FROM_CERT = 4
TIME_VALID_OID_GET_FRESHEST_CRL_FROM_CRL = 5

TIME_VALID_OID_FLUSH_CTL = 1
TIME_VALID_OID_FLUSH_CRL = 2
TIME_VALID_OID_FLUSH_CRL_FROM_CERT = 3
TIME_VALID_OID_FLUSH_FRESHEST_CRL_FROM_CERT = 4
TIME_VALID_OID_FLUSH_FRESHEST_CRL_FROM_CRL = 5

CRYPTPROTECT_PROMPT_ON_UNPROTECT = 0x1
CRYPTPROTECT_PROMPT_ON_PROTECT = 0x2
CRYPTPROTECT_PROMPT_RESERVED = 0x04
CRYPTPROTECT_PROMPT_STRONG = 0x08
CRYPTPROTECT_PROMPT_REQUIRE_STRONG = 0x10
CRYPTPROTECT_UI_FORBIDDEN = 0x1
CRYPTPROTECT_LOCAL_MACHINE = 0x4
CRYPTPROTECT_CRED_SYNC = 0x8
CRYPTPROTECT_AUDIT = 0x10
CRYPTPROTECT_NO_RECOVERY = 0x20
CRYPTPROTECT_VERIFY_PROTECTION = 0x40
CRYPTPROTECT_CRED_REGENERATE = 0x80
CRYPTPROTECT_FIRST_RESERVED_FLAGVAL = 0x0FFFFFFF
CRYPTPROTECT_LAST_RESERVED_FLAGVAL = -1
CRYPTPROTECTMEMORY_BLOCK_SIZE = 16
CRYPTPROTECTMEMORY_SAME_PROCESS = 0x00
CRYPTPROTECTMEMORY_CROSS_PROCESS = 0x01
CRYPTPROTECTMEMORY_SAME_LOGON = 0x02
CERT_CREATE_SELFSIGN_NO_SIGN = 1
CERT_CREATE_SELFSIGN_NO_KEY_INFO = 2
CRYPT_KEYID_MACHINE_FLAG = 0x00000020
CRYPT_KEYID_ALLOC_FLAG = 0x00008000
CRYPT_KEYID_DELETE_FLAG = 0x00000010
CRYPT_KEYID_SET_NEW_FLAG = 0x00002000
CERT_CHAIN_MAX_AIA_URL_COUNT_IN_CERT_DEFAULT = 5
CERT_CHAIN_MAX_AIA_URL_RETRIEVAL_COUNT_PER_CHAIN_DEFAULT = 10
CERT_CHAIN_MAX_AIA_URL_RETRIEVAL_BYTE_COUNT_DEFAULT = 100000
CERT_CHAIN_MAX_AIA_URL_RETRIEVAL_CERT_COUNT_DEFAULT = 10
CERT_CHAIN_CACHE_END_CERT = 0x00000001
CERT_CHAIN_THREAD_STORE_SYNC = 0x00000002
CERT_CHAIN_CACHE_ONLY_URL_RETRIEVAL = 0x00000004
CERT_CHAIN_USE_LOCAL_MACHINE_STORE = 0x00000008
CERT_CHAIN_ENABLE_CACHE_AUTO_UPDATE = 0x00000010
CERT_CHAIN_ENABLE_SHARE_STORE = 0x00000020
CERT_TRUST_NO_ERROR = 0x00000000
CERT_TRUST_IS_NOT_TIME_VALID = 0x00000001
CERT_TRUST_IS_NOT_TIME_NESTED = 0x00000002
CERT_TRUST_IS_REVOKED = 0x00000004
CERT_TRUST_IS_NOT_SIGNATURE_VALID = 0x00000008
CERT_TRUST_IS_NOT_VALID_FOR_USAGE = 0x00000010
CERT_TRUST_IS_UNTRUSTED_ROOT = 0x00000020
CERT_TRUST_REVOCATION_STATUS_UNKNOWN = 0x00000040
CERT_TRUST_IS_CYCLIC = 0x00000080
CERT_TRUST_INVALID_EXTENSION = 0x00000100
CERT_TRUST_INVALID_POLICY_CONSTRAINTS = 0x00000200
CERT_TRUST_INVALID_BASIC_CONSTRAINTS = 0x00000400
CERT_TRUST_INVALID_NAME_CONSTRAINTS = 0x00000800
CERT_TRUST_HAS_NOT_SUPPORTED_NAME_CONSTRAINT = 0x00001000
CERT_TRUST_HAS_NOT_DEFINED_NAME_CONSTRAINT = 0x00002000
CERT_TRUST_HAS_NOT_PERMITTED_NAME_CONSTRAINT = 0x00004000
CERT_TRUST_HAS_EXCLUDED_NAME_CONSTRAINT = 0x00008000
CERT_TRUST_IS_OFFLINE_REVOCATION = 0x01000000
CERT_TRUST_NO_ISSUANCE_CHAIN_POLICY = 0x02000000
CERT_TRUST_IS_PARTIAL_CHAIN = 0x00010000
CERT_TRUST_CTL_IS_NOT_TIME_VALID = 0x00020000
CERT_TRUST_CTL_IS_NOT_SIGNATURE_VALID = 0x00040000
CERT_TRUST_CTL_IS_NOT_VALID_FOR_USAGE = 0x00080000
CERT_TRUST_HAS_EXACT_MATCH_ISSUER = 0x00000001
CERT_TRUST_HAS_KEY_MATCH_ISSUER = 0x00000002
CERT_TRUST_HAS_NAME_MATCH_ISSUER = 0x00000004
CERT_TRUST_IS_SELF_SIGNED = 0x00000008
CERT_TRUST_HAS_PREFERRED_ISSUER = 0x00000100
CERT_TRUST_HAS_ISSUANCE_CHAIN_POLICY = 0x00000200
CERT_TRUST_HAS_VALID_NAME_CONSTRAINTS = 0x00000400
CERT_TRUST_IS_COMPLEX_CHAIN = 0x00010000
USAGE_MATCH_TYPE_AND = 0x00000000
USAGE_MATCH_TYPE_OR = 0x00000001
CERT_CHAIN_REVOCATION_CHECK_END_CERT = 0x10000000
CERT_CHAIN_REVOCATION_CHECK_CHAIN = 0x20000000
CERT_CHAIN_REVOCATION_CHECK_CHAIN_EXCLUDE_ROOT = 0x40000000
CERT_CHAIN_REVOCATION_CHECK_CACHE_ONLY = -2147483648
CERT_CHAIN_REVOCATION_ACCUMULATIVE_TIMEOUT = 0x08000000
CERT_CHAIN_DISABLE_PASS1_QUALITY_FILTERING = 0x00000040
CERT_CHAIN_RETURN_LOWER_QUALITY_CONTEXTS = 0x00000080
CERT_CHAIN_DISABLE_AUTH_ROOT_AUTO_UPDATE = 0x00000100
CERT_CHAIN_TIMESTAMP_TIME = 0x00000200
REVOCATION_OID_CRL_REVOCATION = 1
CERT_CHAIN_FIND_BY_ISSUER = 1
CERT_CHAIN_FIND_BY_ISSUER_COMPARE_KEY_FLAG = 0x0001
CERT_CHAIN_FIND_BY_ISSUER_COMPLEX_CHAIN_FLAG = 0x0002
CERT_CHAIN_FIND_BY_ISSUER_CACHE_ONLY_URL_FLAG = 0x0004
CERT_CHAIN_FIND_BY_ISSUER_LOCAL_MACHINE_FLAG = 0x0008
CERT_CHAIN_FIND_BY_ISSUER_NO_KEY_FLAG = 0x4000
CERT_CHAIN_FIND_BY_ISSUER_CACHE_ONLY_FLAG = 0x8000
CERT_CHAIN_POLICY_IGNORE_NOT_TIME_VALID_FLAG = 0x00000001
CERT_CHAIN_POLICY_IGNORE_CTL_NOT_TIME_VALID_FLAG = 0x00000002
CERT_CHAIN_POLICY_IGNORE_NOT_TIME_NESTED_FLAG = 0x00000004
CERT_CHAIN_POLICY_IGNORE_INVALID_BASIC_CONSTRAINTS_FLAG = 0x00000008
CERT_CHAIN_POLICY_IGNORE_ALL_NOT_TIME_VALID_FLAGS = (
    CERT_CHAIN_POLICY_IGNORE_NOT_TIME_VALID_FLAG
    | CERT_CHAIN_POLICY_IGNORE_CTL_NOT_TIME_VALID_FLAG
    | CERT_CHAIN_POLICY_IGNORE_NOT_TIME_NESTED_FLAG
)
CERT_CHAIN_POLICY_ALLOW_UNKNOWN_CA_FLAG = 0x00000010
CERT_CHAIN_POLICY_IGNORE_WRONG_USAGE_FLAG = 0x00000020
CERT_CHAIN_POLICY_IGNORE_INVALID_NAME_FLAG = 0x00000040
CERT_CHAIN_POLICY_IGNORE_INVALID_POLICY_FLAG = 0x00000080
CERT_CHAIN_POLICY_IGNORE_END_REV_UNKNOWN_FLAG = 0x00000100
CERT_CHAIN_POLICY_IGNORE_CTL_SIGNER_REV_UNKNOWN_FLAG = 0x00000200
CERT_CHAIN_POLICY_IGNORE_CA_REV_UNKNOWN_FLAG = 0x00000400
CERT_CHAIN_POLICY_IGNORE_ROOT_REV_UNKNOWN_FLAG = 0x00000800
CERT_CHAIN_POLICY_IGNORE_ALL_REV_UNKNOWN_FLAGS = (
    CERT_CHAIN_POLICY_IGNORE_END_REV_UNKNOWN_FLAG
    | CERT_CHAIN_POLICY_IGNORE_CTL_SIGNER_REV_UNKNOWN_FLAG
    | CERT_CHAIN_POLICY_IGNORE_CA_REV_UNKNOWN_FLAG
    | CERT_CHAIN_POLICY_IGNORE_ROOT_REV_UNKNOWN_FLAG
)
CERT_CHAIN_POLICY_ALLOW_TESTROOT_FLAG = 0x00008000
CERT_CHAIN_POLICY_TRUST_TESTROOT_FLAG = 0x00004000
CRYPT_OID_VERIFY_CERTIFICATE_CHAIN_POLICY_FUNC = "CertDllVerifyCertificateChainPolicy"
AUTHTYPE_CLIENT = 1
AUTHTYPE_SERVER = 2
BASIC_CONSTRAINTS_CERT_CHAIN_POLICY_CA_FLAG = -2147483648
BASIC_CONSTRAINTS_CERT_CHAIN_POLICY_END_ENTITY_FLAG = 0x40000000
MICROSOFT_ROOT_CERT_CHAIN_POLICY_ENABLE_TEST_ROOT_FLAG = 0x00010000
CRYPT_STRING_BASE64HEADER = 0x00000000
CRYPT_STRING_BASE64 = 0x00000001
CRYPT_STRING_BINARY = 0x00000002
CRYPT_STRING_BASE64REQUESTHEADER = 0x00000003
CRYPT_STRING_HEX = 0x00000004
CRYPT_STRING_HEXASCII = 0x00000005
CRYPT_STRING_BASE64_ANY = 0x00000006
CRYPT_STRING_ANY = 0x00000007
CRYPT_STRING_HEX_ANY = 0x00000008
CRYPT_STRING_BASE64X509CRLHEADER = 0x00000009
CRYPT_STRING_HEXADDR = 0x0000000A
CRYPT_STRING_HEXASCIIADDR = 0x0000000B
CRYPT_STRING_NOCR = -2147483648
CRYPT_USER_KEYSET = 0x00001000
PKCS12_IMPORT_RESERVED_MASK = -65536
REPORT_NO_PRIVATE_KEY = 0x0001
REPORT_NOT_ABLE_TO_EXPORT_PRIVATE_KEY = 0x0002
EXPORT_PRIVATE_KEYS = 0x0004
PKCS12_EXPORT_RESERVED_MASK = -65536

# Certificate store provider types used with CertOpenStore
CERT_STORE_PROV_MSG = 1
CERT_STORE_PROV_MEMORY = 2
CERT_STORE_PROV_FILE = 3
CERT_STORE_PROV_REG = 4
CERT_STORE_PROV_PKCS7 = 5
CERT_STORE_PROV_SERIALIZED = 6
CERT_STORE_PROV_FILENAME = 8
CERT_STORE_PROV_SYSTEM = 10
CERT_STORE_PROV_COLLECTION = 11
CERT_STORE_PROV_SYSTEM_REGISTRY = 13
CERT_STORE_PROV_PHYSICAL = 14
CERT_STORE_PROV_SMART_CARD = 15
CERT_STORE_PROV_LDAP = 16

URL_OID_CERTIFICATE_ISSUER = 1
URL_OID_CERTIFICATE_CRL_DIST_POINT = 2
URL_OID_CTL_ISSUER = 3
URL_OID_CTL_NEXT_UPDATE = 4
URL_OID_CRL_ISSUER = 5
URL_OID_CERTIFICATE_FRESHEST_CRL = 6
URL_OID_CRL_FRESHEST_CRL = 7
URL_OID_CROSS_CERT_DIST_POINT = 8
URL_OID_CERTIFICATE_OCSP = 9
URL_OID_CERTIFICATE_OCSP_AND_CRL_DIST_POINT = 10
URL_OID_CERTIFICATE_CRL_DIST_POINT_AND_OCSP = 11
URL_OID_CROSS_CERT_SUBJECT_INFO_ACCESS = 12
URL_OID_CERTIFICATE_ONLY_OCSP = 13

# === NexusCore/src\agents\architect_agent.py ===
# フォルダ: src/agents
# ファイル名: architect_agent.py
# メモ: 『アーキテクト・ファースト』アプローチの設計専門AI。
#      BaseAgentを継承して作ります。
# ==============================================================================
from .base_agent import BaseAgent

class ArchitectAgent(BaseAgent):
    SYSTEM_PROMPT = """
あなたは、ベストプラクティスに精通したシニアソフトウェアアーキテクトです。
ユーザーの高レベルな要求を解釈し、堅牢でスケーラブルなプロジェクトの完全なファイル構造と、
各ファイルのスケルトンコード（骨格）、そして依存関係を定義するJSONを出力してください。
"""

    def design_project_structure(self, user_requirement: str) -> str:
        prompt = f"""
以下のユーザー要求を満たすための、完全なプロジェクト構造を設計してください。

# ユーザー要求
{user_requirement}

# 出力要件
- ルートは単一の `project` オブジェクトとします。
- ファイル構造は `files` 配列で、ネストされたオブジェクトとして表現してください。
- 各ファイルオブジェクトは `name` (ディレクトリを含むフルパス), `type` ('folder' or 'file'), `content` (スケルトンコード) のキーを持つ必要があります。
- `content`には、クラス定義、関数シグネチャ、主要なロジックをTODOコメントとして記述してください。
- 必要なライブラリは `requirements.txt` に含めてください。
- 必ずJSON形式で出力してください。

# JSON出力例
{{
  "project": {{
    "files": [
      {{
        "name": "app/",
        "type": "folder",
        "content": ""
      }},
      {{
        "name": "app/main.py",
        "type": "file",
        "content": "# TODO: Flask app initialization\\n\\ndef main():\\n    pass"
      }},
      {{
        "name": "requirements.txt",
        "type": "file",
        "content": "flask\\nsqlalchemy"
      }}
    ]
  }}
}}
"""
        # JSON形式の出力を期待するため、as_json=True を指定
        return self._call_llm(prompt, self.SYSTEM_PROMPT, as_json=True)

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\agents\architect_agent.py ===
# フォルダ: src/agents
# ファイル名: architect_agent.py
# メモ: 『アーキテクト・ファースト』アプローチの設計専門AI。
#      BaseAgentを継承して作ります。
# ==============================================================================
from .base_agent import BaseAgent

class ArchitectAgent(BaseAgent):
    SYSTEM_PROMPT = """
あなたは、ベストプラクティスに精通したシニアソフトウェアアーキテクトです。
ユーザーの高レベルな要求を解釈し、堅牢でスケーラブルなプロジェクトの完全なファイル構造と、
各ファイルのスケルトンコード（骨格）、そして依存関係を定義するJSONを出力してください。
"""

    def design_project_structure(self, user_requirement: str) -> str:
        prompt = f"""
以下のユーザー要求を満たすための、完全なプロジェクト構造を設計してください。

# ユーザー要求
{user_requirement}

# 出力要件
- ルートは単一の `project` オブジェクトとします。
- ファイル構造は `files` 配列で、ネストされたオブジェクトとして表現してください。
- 各ファイルオブジェクトは `name` (ディレクトリを含むフルパス), `type` ('folder' or 'file'), `content` (スケルトンコード) のキーを持つ必要があります。
- `content`には、クラス定義、関数シグネチャ、主要なロジックをTODOコメントとして記述してください。
- 必要なライブラリは `requirements.txt` に含めてください。
- 必ずJSON形式で出力してください。

# JSON出力例
{{
  "project": {{
    "files": [
      {{
        "name": "app/",
        "type": "folder",
        "content": ""
      }},
      {{
        "name": "app/main.py",
        "type": "file",
        "content": "# TODO: Flask app initialization\\n\\ndef main():\\n    pass"
      }},
      {{
        "name": "requirements.txt",
        "type": "file",
        "content": "flask\\nsqlalchemy"
      }}
    ]
  }}
}}
"""
        # JSON形式の出力を期待するため、as_json=True を指定
        return self._call_llm(prompt, self.SYSTEM_PROMPT, as_json=True)

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\Demos\app\helloapp.py ===
##
## helloapp.py
##
##
## A nice, small 'hello world' Pythonwin application.
## NOT an MDI application - just a single, normal, top-level window.
##
## MUST be run with the command line "pythonwin.exe /app helloapp.py"
## (or if you are really keen, rename "pythonwin.exe" to something else, then
## using MSVC or similar, edit the string section in the .EXE to name this file)
##
## Originally by Willy Heineman <wheineman@uconect.net>


import win32con
import win32ui
from pywin.mfc import window
from pywin.mfc.thread import WinApp


# The main frame.
# Does almost nothing at all - doesn't even create a child window!
class HelloWindow(window.Wnd):
    def __init__(self):
        # The window.Wnd ctor creates a Window object, and places it in
        # self._obj_.  Note the window object exists, but the window itself
        # does not!
        window.Wnd.__init__(self, win32ui.CreateWnd())

        # Now we ask the window object to create the window itself.
        self._obj_.CreateWindowEx(
            win32con.WS_EX_CLIENTEDGE,
            win32ui.RegisterWndClass(0, 0, win32con.COLOR_WINDOW + 1),
            "Hello World!",
            win32con.WS_OVERLAPPEDWINDOW,
            (100, 100, 400, 300),
            None,
            0,
            None,
        )


# The application object itself.
class HelloApp(WinApp):
    def InitInstance(self):
        self.frame = HelloWindow()
        self.frame.ShowWindow(win32con.SW_SHOWNORMAL)
        # We need to tell MFC what our main frame is.
        self.SetMainFrame(self.frame)


# Now create the application object itself!
app = HelloApp()

# === NexusCore/src\agents\patch_applier.py ===
# ==============================================================================
# フォルダ: src/agents
# ファイル名: patch_applier.py
# メモ: 堅牢性と信頼性を最大化するため、専門ライブラリ`patch`を
#      正しく、安全に利用する完成版。
# ==============================================================================
import logging
import os
import patch # 専門ライブラリをインポート

class PatchApplier:
    """
    'unified diff' 形式のパッチをソースコードファイルに適用するためのクラス。
    専門ライブラリ`patch`を利用し、複雑なパッチも正確に適用する。
    """

    def apply(self, patch_str: str, project_path: str) -> bool:
        """
        指定されたプロジェクトパスを基準にパッチを適用します。

        Args:
            patch_str (str): unified diff形式のパッチ文字列。
            project_path (str): パッチを適用するプロジェクトのルートパス。

        Returns:
            bool: パッチの適用が成功した場合はTrue、失敗した場合はFalse。
        """
        if not patch_str:
            logging.warning("Patch is empty. Nothing to apply.")
            return False

        try:
            # パッチ文字列からパッチセットを解析
            patch_set = patch.fromstring(patch_str.encode('utf-8'))
            
            # ★ 解析失敗時のエラーハンドリングを追加
            if not patch_set:
                logging.error("Failed to parse patch string. It might be invalid or malformed.")
                logging.debug(f"Invalid patch string:\n{patch_str}")
                return False
            
            # ★ パッチを適用する基準ディレクトリ(root)を、プロジェクトのパスに正しく設定
            success = patch_set.apply(root=project_path)
            
            if success:
                logging.info(f"Successfully applied patch within project: {project_path}")
                return True
            else:
                logging.error(f"Failed to apply patch within project: {project_path}. The patch may be invalid or already applied.")
                return False
        except Exception as e:
            logging.error(f"An error occurred while applying patch with 'patch' library: {e}", exc_info=True)
            return False

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pythonwin\pywin\Demos\app\helloapp.py ===
##
## helloapp.py
##
##
## A nice, small 'hello world' Pythonwin application.
## NOT an MDI application - just a single, normal, top-level window.
##
## MUST be run with the command line "pythonwin.exe /app helloapp.py"
## (or if you are really keen, rename "pythonwin.exe" to something else, then
## using MSVC or similar, edit the string section in the .EXE to name this file)
##
## Originally by Willy Heineman <wheineman@uconect.net>


import win32con
import win32ui
from pywin.mfc import window
from pywin.mfc.thread import WinApp


# The main frame.
# Does almost nothing at all - doesn't even create a child window!
class HelloWindow(window.Wnd):
    def __init__(self):
        # The window.Wnd ctor creates a Window object, and places it in
        # self._obj_.  Note the window object exists, but the window itself
        # does not!
        window.Wnd.__init__(self, win32ui.CreateWnd())

        # Now we ask the window object to create the window itself.
        self._obj_.CreateWindowEx(
            win32con.WS_EX_CLIENTEDGE,
            win32ui.RegisterWndClass(0, 0, win32con.COLOR_WINDOW + 1),
            "Hello World!",
            win32con.WS_OVERLAPPEDWINDOW,
            (100, 100, 400, 300),
            None,
            0,
            None,
        )


# The application object itself.
class HelloApp(WinApp):
    def InitInstance(self):
        self.frame = HelloWindow()
        self.frame.ShowWindow(win32con.SW_SHOWNORMAL)
        # We need to tell MFC what our main frame is.
        self.SetMainFrame(self.frame)


# Now create the application object itself!
app = HelloApp()

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\agents\patch_applier.py ===
# ==============================================================================
# フォルダ: src/agents
# ファイル名: patch_applier.py
# メモ: 堅牢性と信頼性を最大化するため、専門ライブラリ`patch`を
#      正しく、安全に利用する完成版。
# ==============================================================================
import logging
import os
import patch # 専門ライブラリをインポート

class PatchApplier:
    """
    'unified diff' 形式のパッチをソースコードファイルに適用するためのクラス。
    専門ライブラリ`patch`を利用し、複雑なパッチも正確に適用する。
    """

    def apply(self, patch_str: str, project_path: str) -> bool:
        """
        指定されたプロジェクトパスを基準にパッチを適用します。

        Args:
            patch_str (str): unified diff形式のパッチ文字列。
            project_path (str): パッチを適用するプロジェクトのルートパス。

        Returns:
            bool: パッチの適用が成功した場合はTrue、失敗した場合はFalse。
        """
        if not patch_str:
            logging.warning("Patch is empty. Nothing to apply.")
            return False

        try:
            # パッチ文字列からパッチセットを解析
            patch_set = patch.fromstring(patch_str.encode('utf-8'))
            
            # ★ 解析失敗時のエラーハンドリングを追加
            if not patch_set:
                logging.error("Failed to parse patch string. It might be invalid or malformed.")
                logging.debug(f"Invalid patch string:\n{patch_str}")
                return False
            
            # ★ パッチを適用する基準ディレクトリ(root)を、プロジェクトのパスに正しく設定
            success = patch_set.apply(root=project_path)
            
            if success:
                logging.info(f"Successfully applied patch within project: {project_path}")
                return True
            else:
                logging.error(f"Failed to apply patch within project: {project_path}. The patch may be invalid or already applied.")
                return False
        except Exception as e:
            logging.error(f"An error occurred while applying patch with 'patch' library: {e}", exc_info=True)
            return False

# === NexusCore/src\agents\tester_agent.py ===
# C:\Users\USER\tools\OpenCodeInterpreter\src\agents\tester_agent.py

import json
from .base_agent import BaseAgent

class TesterAgent(BaseAgent):
    SYSTEM_PROMPT = """
あなたは、細部まで見逃さない、経験豊富な品質保証（QA）エンジニアです。
専門はpytestを用いた自動テストの作成です。
あなたの仕事は、与えられたPythonコードや実装計画に対して、その正しさを証明するための
高品質なテストコードと、そのテスト設計に関する「証言」を生成することです。
"""

    def generate_tests_and_testimony(self, code_to_test: str) -> str:
        """【旧メソッド】コードを基にテストを生成する"""
        prompt = f"""
# テスト対象コード
```python
{code_to_test}
```
# あなたへの指示
上記のコードに対して、pytest形式のユニットテストと、そのテスト設計に関する「証言」を生成してください。
# 出力要件
- テストコードは、正常系、異常系、そして考えうるエッジケースを網羅してください。
- 「証言」には、どのようなテストケースを、どのような意図で設計したかを簡潔に記述してください。
- 必ず以下のキーを持つJSON形式で出力してください: `test_code`, `testimony`
"""
        return self._call_llm(prompt, self.SYSTEM_PROMPT, as_json=True)

    # ★★★★★ ここが最重要修正点 (2/2) ★★★★★
    # メソッドの定義に module_to_import を追加し、プロンプト内でそれを使用します。
    def generate_tests_from_plan(self, plan: dict, module_to_import: str) -> str:
        """実装計画を基に、テストコードと証言を生成する"""
        plan_str = json.dumps(plan, indent=2, ensure_ascii=False)
        prompt = f"""
# 実装計画
```json
{plan_str}
```
# あなたへの指示
上記のJSON形式の実装計画に記述された全ての関数に対する、pytest形式のユニットテストとそのテスト設計に関する「証言」を生成してください。

# 重要：テスト対象のインポート
テスト対象の関数は、必ず `{module_to_import}` モジュールからインポートしてください。
例: `from {module_to_import} import function_name`

# 出力要件
- テストコードは、計画に記述された仕様（引数、返り値、振る舞い）を完全に満たすことを検証してください。
- 正常系、異常系、エッジケースを網羅し、高品質なテストを作成してください。
- 必ず以下のキーを持つJSON形式で出力してください: `test_code`, `testimony`
"""
        return self._call_llm(prompt, self.SYSTEM_PROMPT, as_json=True)

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\agents\tester_agent.py ===
# C:\Users\USER\tools\OpenCodeInterpreter\src\agents\tester_agent.py

import json
from .base_agent import BaseAgent

class TesterAgent(BaseAgent):
    SYSTEM_PROMPT = """
あなたは、細部まで見逃さない、経験豊富な品質保証（QA）エンジニアです。
専門はpytestを用いた自動テストの作成です。
あなたの仕事は、与えられたPythonコードや実装計画に対して、その正しさを証明するための
高品質なテストコードと、そのテスト設計に関する「証言」を生成することです。
"""

    def generate_tests_and_testimony(self, code_to_test: str) -> str:
        """【旧メソッド】コードを基にテストを生成する"""
        prompt = f"""
# テスト対象コード
```python
{code_to_test}
```
# あなたへの指示
上記のコードに対して、pytest形式のユニットテストと、そのテスト設計に関する「証言」を生成してください。
# 出力要件
- テストコードは、正常系、異常系、そして考えうるエッジケースを網羅してください。
- 「証言」には、どのようなテストケースを、どのような意図で設計したかを簡潔に記述してください。
- 必ず以下のキーを持つJSON形式で出力してください: `test_code`, `testimony`
"""
        return self._call_llm(prompt, self.SYSTEM_PROMPT, as_json=True)

    # ★★★★★ ここが最重要修正点 (2/2) ★★★★★
    # メソッドの定義に module_to_import を追加し、プロンプト内でそれを使用します。
    def generate_tests_from_plan(self, plan: dict, module_to_import: str) -> str:
        """実装計画を基に、テストコードと証言を生成する"""
        plan_str = json.dumps(plan, indent=2, ensure_ascii=False)
        prompt = f"""
# 実装計画
```json
{plan_str}
```
# あなたへの指示
上記のJSON形式の実装計画に記述された全ての関数に対する、pytest形式のユニットテストとそのテスト設計に関する「証言」を生成してください。

# 重要：テスト対象のインポート
テスト対象の関数は、必ず `{module_to_import}` モジュールからインポートしてください。
例: `from {module_to_import} import function_name`

# 出力要件
- テストコードは、計画に記述された仕様（引数、返り値、振る舞い）を完全に満たすことを検証してください。
- 正常系、異常系、エッジケースを網羅し、高品質なテストを作成してください。
- 必ず以下のキーを持つJSON形式で出力してください: `test_code`, `testimony`
"""
        return self._call_llm(prompt, self.SYSTEM_PROMPT, as_json=True)

# === NexusCore/openenv\Lib\site-packages\numpy\lib\recfunctions.py ===
"""
Collection of utilities to manipulate structured arrays.

Most of these functions were initially implemented by John Hunter for
matplotlib.  They have been rewritten and extended for convenience.

"""
import itertools

import numpy as np
import numpy.ma as ma
import numpy.ma.mrecords as mrec
from numpy._core.overrides import array_function_dispatch
from numpy.lib._iotools import _is_string_like

__all__ = [
    'append_fields', 'apply_along_fields', 'assign_fields_by_name',
    'drop_fields', 'find_duplicates', 'flatten_descr',
    'get_fieldstructure', 'get_names', 'get_names_flat',
    'join_by', 'merge_arrays', 'rec_append_fields',
    'rec_drop_fields', 'rec_join', 'recursive_fill_fields',
    'rename_fields', 'repack_fields', 'require_fields',
    'stack_arrays', 'structured_to_unstructured', 'unstructured_to_structured',
    ]


def _recursive_fill_fields_dispatcher(input, output):
    return (input, output)


@array_function_dispatch(_recursive_fill_fields_dispatcher)
def recursive_fill_fields(input, output):
    """
    Fills fields from output with fields from input,
    with support for nested structures.

    Parameters
    ----------
    input : ndarray
        Input array.
    output : ndarray
        Output array.

    Notes
    -----
    * `output` should be at least the same size as `input`

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.lib import recfunctions as rfn
    >>> a = np.array([(1, 10.), (2, 20.)], dtype=[('A', np.int64), ('B', np.float64)])
    >>> b = np.zeros((3,), dtype=a.dtype)
    >>> rfn.recursive_fill_fields(a, b)
    array([(1, 10.), (2, 20.), (0,  0.)], dtype=[('A', '<i8'), ('B', '<f8')])

    """
    newdtype = output.dtype
    for field in newdtype.names:
        try:
            current = input[field]
        except ValueError:
            continue
        if current.dtype.names is not None:
            recursive_fill_fields(current, output[field])
        else:
            output[field][:len(current)] = current
    return output


def _get_fieldspec(dtype):
    """
    Produce a list of name/dtype pairs corresponding to the dtype fields

    Similar to dtype.descr, but the second item of each tuple is a dtype, not a
    string. As a result, this handles subarray dtypes

    Can be passed to the dtype constructor to reconstruct the dtype, noting that
    this (deliberately) discards field offsets.

    Examples
    --------
    >>> import numpy as np
    >>> dt = np.dtype([(('a', 'A'), np.int64), ('b', np.double, 3)])
    >>> dt.descr
    [(('a', 'A'), '<i8'), ('b', '<f8', (3,))]
    >>> _get_fieldspec(dt)
    [(('a', 'A'), dtype('int64')), ('b', dtype(('<f8', (3,))))]

    """
    if dtype.names is None:
        # .descr returns a nameless field, so we should too
        return [('', dtype)]
    else:
        fields = ((name, dtype.fields[name]) for name in dtype.names)
        # keep any titles, if present
        return [
            (name if len(f) == 2 else (f[2], name), f[0])
            for name, f in fields
        ]


def get_names(adtype):
    """
    Returns the field names of the input datatype as a tuple. Input datatype
    must have fields otherwise error is raised.

    Parameters
    ----------
    adtype : dtype
        Input datatype

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.lib import recfunctions as rfn
    >>> rfn.get_names(np.empty((1,), dtype=[('A', int)]).dtype)
    ('A',)
    >>> rfn.get_names(np.empty((1,), dtype=[('A',int), ('B', float)]).dtype)
    ('A', 'B')
    >>> adtype = np.dtype([('a', int), ('b', [('ba', int), ('bb', int)])])
    >>> rfn.get_names(adtype)
    ('a', ('b', ('ba', 'bb')))
    """
    listnames = []
    names = adtype.names
    for name in names:
        current = adtype[name]
        if current.names is not None:
            listnames.append((name, tuple(get_names(current))))
        else:
            listnames.append(name)
    return tuple(listnames)


def get_names_flat(adtype):
    """
    Returns the field names of the input datatype as a tuple. Input datatype
    must have fields otherwise error is raised.
    Nested structure are flattened beforehand.

    Parameters
    ----------
    adtype : dtype
        Input datatype

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.lib import recfunctions as rfn
    >>> rfn.get_names_flat(np.empty((1,), dtype=[('A', int)]).dtype) is None
    False
    >>> rfn.get_names_flat(np.empty((1,), dtype=[('A',int), ('B', str)]).dtype)
    ('A', 'B')
    >>> adtype = np.dtype([('a', int), ('b', [('ba', int), ('bb', int)])])
    >>> rfn.get_names_flat(adtype)
    ('a', 'b', 'ba', 'bb')
    """
    listnames = []
    names = adtype.names
    for name in names:
        listnames.append(name)
        current = adtype[name]
        if current.names is not None:
            listnames.extend(get_names_flat(current))
    return tuple(listnames)


def flatten_descr(ndtype):
    """
    Flatten a structured data-type description.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.lib import recfunctions as rfn
    >>> ndtype = np.dtype([('a', '<i4'), ('b', [('ba', '<f8'), ('bb', '<i4')])])
    >>> rfn.flatten_descr(ndtype)
    (('a', dtype('int32')), ('ba', dtype('float64')), ('bb', dtype('int32')))

    """
    names = ndtype.names
    if names is None:
        return (('', ndtype),)
    else:
        descr = []
        for field in names:
            (typ, _) = ndtype.fields[field]
            if typ.names is not None:
                descr.extend(flatten_descr(typ))
            else:
                descr.append((field, typ))
        return tuple(descr)


def _zip_dtype(seqarrays, flatten=False):
    newdtype = []
    if flatten:
        for a in seqarrays:
            newdtype.extend(flatten_descr(a.dtype))
    else:
        for a in seqarrays:
            current = a.dtype
            if current.names is not None and len(current.names) == 1:
                # special case - dtypes of 1 field are flattened
                newdtype.extend(_get_fieldspec(current))
            else:
                newdtype.append(('', current))
    return np.dtype(newdtype)


def _zip_descr(seqarrays, flatten=False):
    """
    Combine the dtype description of a series of arrays.

    Parameters
    ----------
    seqarrays : sequence of arrays
        Sequence of arrays
    flatten : {boolean}, optional
        Whether to collapse nested descriptions.
    """
    return _zip_dtype(seqarrays, flatten=flatten).descr


def get_fieldstructure(adtype, lastname=None, parents=None,):
    """
    Returns a dictionary with fields indexing lists of their parent fields.

    This function is used to simplify access to fields nested in other fields.

    Parameters
    ----------
    adtype : np.dtype
        Input datatype
    lastname : optional
        Last processed field name (used internally during recursion).
    parents : dictionary
        Dictionary of parent fields (used internally during recursion).

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.lib import recfunctions as rfn
    >>> ndtype =  np.dtype([('A', int),
    ...                     ('B', [('BA', int),
    ...                            ('BB', [('BBA', int), ('BBB', int)])])])
    >>> rfn.get_fieldstructure(ndtype)
    ... # XXX: possible regression, order of BBA and BBB is swapped
    {'A': [], 'B': [], 'BA': ['B'], 'BB': ['B'], 'BBA': ['B', 'BB'], 'BBB': ['B', 'BB']}

    """
    if parents is None:
        parents = {}
    names = adtype.names
    for name in names:
        current = adtype[name]
        if current.names is not None:
            if lastname:
                parents[name] = [lastname, ]
            else:
                parents[name] = []
            parents.update(get_fieldstructure(current, name, parents))
        else:
            lastparent = list(parents.get(lastname, []) or [])
            if lastparent:
                lastparent.append(lastname)
            elif lastname:
                lastparent = [lastname, ]
            parents[name] = lastparent or []
    return parents


def _izip_fields_flat(iterable):
    """
    Returns an iterator of concatenated fields from a sequence of arrays,
    collapsing any nested structure.

    """
    for element in iterable:
        if isinstance(element, np.void):
            yield from _izip_fields_flat(tuple(element))
        else:
            yield element


def _izip_fields(iterable):
    """
    Returns an iterator of concatenated fields from a sequence of arrays.

    """
    for element in iterable:
        if (hasattr(element, '__iter__') and
                not isinstance(element, str)):
            yield from _izip_fields(element)
        elif isinstance(element, np.void) and len(tuple(element)) == 1:
            # this statement is the same from the previous expression
            yield from _izip_fields(element)
        else:
            yield element


def _izip_records(seqarrays, fill_value=None, flatten=True):
    """
    Returns an iterator of concatenated items from a sequence of arrays.

    Parameters
    ----------
    seqarrays : sequence of arrays
        Sequence of arrays.
    fill_value : {None, integer}
        Value used to pad shorter iterables.
    flatten : {True, False},
        Whether to
    """

    # Should we flatten the items, or just use a nested approach
    if flatten:
        zipfunc = _izip_fields_flat
    else:
        zipfunc = _izip_fields

    for tup in itertools.zip_longest(*seqarrays, fillvalue=fill_value):
        yield tuple(zipfunc(tup))


def _fix_output(output, usemask=True, asrecarray=False):
    """
    Private function: return a recarray, a ndarray, a MaskedArray
    or a MaskedRecords depending on the input parameters
    """
    if not isinstance(output, ma.MaskedArray):
        usemask = False
    if usemask:
        if asrecarray:
            output = output.view(mrec.MaskedRecords)
    else:
        output = ma.filled(output)
        if asrecarray:
            output = output.view(np.recarray)
    return output


def _fix_defaults(output, defaults=None):
    """
    Update the fill_value and masked data of `output`
    from the default given in a dictionary defaults.
    """
    names = output.dtype.names
    (data, mask, fill_value) = (output.data, output.mask, output.fill_value)
    for (k, v) in (defaults or {}).items():
        if k in names:
            fill_value[k] = v
            data[k][mask[k]] = v
    return output


def _merge_arrays_dispatcher(seqarrays, fill_value=None, flatten=None,
                             usemask=None, asrecarray=None):
    return seqarrays


@array_function_dispatch(_merge_arrays_dispatcher)
def merge_arrays(seqarrays, fill_value=-1, flatten=False,
                 usemask=False, asrecarray=False):
    """
    Merge arrays field by field.

    Parameters
    ----------
    seqarrays : sequence of ndarrays
        Sequence of arrays
    fill_value : {float}, optional
        Filling value used to pad missing data on the shorter arrays.
    flatten : {False, True}, optional
        Whether to collapse nested fields.
    usemask : {False, True}, optional
        Whether to return a masked array or not.
    asrecarray : {False, True}, optional
        Whether to return a recarray (MaskedRecords) or not.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.lib import recfunctions as rfn
    >>> rfn.merge_arrays((np.array([1, 2]), np.array([10., 20., 30.])))
    array([( 1, 10.), ( 2, 20.), (-1, 30.)],
          dtype=[('f0', '<i8'), ('f1', '<f8')])

    >>> rfn.merge_arrays((np.array([1, 2], dtype=np.int64),
    ...         np.array([10., 20., 30.])), usemask=False)
     array([(1, 10.0), (2, 20.0), (-1, 30.0)],
             dtype=[('f0', '<i8'), ('f1', '<f8')])
    >>> rfn.merge_arrays((np.array([1, 2]).view([('a', np.int64)]),
    ...               np.array([10., 20., 30.])),
    ...              usemask=False, asrecarray=True)
    rec.array([( 1, 10.), ( 2, 20.), (-1, 30.)],
              dtype=[('a', '<i8'), ('f1', '<f8')])

    Notes
    -----
    * Without a mask, the missing value will be filled with something,
      depending on what its corresponding type:

      * ``-1``      for integers
      * ``-1.0``    for floating point numbers
      * ``'-'``     for characters
      * ``'-1'``    for strings
      * ``True``    for boolean values
    * XXX: I just obtained these values empirically
    """
    # Only one item in the input sequence ?
    if (len(seqarrays) == 1):
        seqarrays = np.asanyarray(seqarrays[0])
    # Do we have a single ndarray as input ?
    if isinstance(seqarrays, (np.ndarray, np.void)):
        seqdtype = seqarrays.dtype
        # Make sure we have named fields
        if seqdtype.names is None:
            seqdtype = np.dtype([('', seqdtype)])
        if not flatten or _zip_dtype((seqarrays,), flatten=True) == seqdtype:
            # Minimal processing needed: just make sure everything's a-ok
            seqarrays = seqarrays.ravel()
            # Find what type of array we must return
            if usemask:
                if asrecarray:
                    seqtype = mrec.MaskedRecords
                else:
                    seqtype = ma.MaskedArray
            elif asrecarray:
                seqtype = np.recarray
            else:
                seqtype = np.ndarray
            return seqarrays.view(dtype=seqdtype, type=seqtype)
        else:
            seqarrays = (seqarrays,)
    else:
        # Make sure we have arrays in the input sequence
        seqarrays = [np.asanyarray(_m) for _m in seqarrays]
    # Find the sizes of the inputs and their maximum
    sizes = tuple(a.size for a in seqarrays)
    maxlength = max(sizes)
    # Get the dtype of the output (flattening if needed)
    newdtype = _zip_dtype(seqarrays, flatten=flatten)
    # Initialize the sequences for data and mask
    seqdata = []
    seqmask = []
    # If we expect some kind of MaskedArray, make a special loop.
    if usemask:
        for (a, n) in zip(seqarrays, sizes):
            nbmissing = (maxlength - n)
            # Get the data and mask
            data = a.ravel().__array__()
            mask = ma.getmaskarray(a).ravel()
            # Get the filling value (if needed)
            if nbmissing:
                fval = mrec._check_fill_value(fill_value, a.dtype)
                if isinstance(fval, (np.ndarray, np.void)):
                    if len(fval.dtype) == 1:
                        fval = fval.item()[0]
                        fmsk = True
                    else:
                        fval = np.array(fval, dtype=a.dtype, ndmin=1)
                        fmsk = np.ones((1,), dtype=mask.dtype)
            else:
                fval = None
                fmsk = True
            # Store an iterator padding the input to the expected length
            seqdata.append(itertools.chain(data, [fval] * nbmissing))
            seqmask.append(itertools.chain(mask, [fmsk] * nbmissing))
        # Create an iterator for the data
        data = tuple(_izip_records(seqdata, flatten=flatten))
        output = ma.array(np.fromiter(data, dtype=newdtype, count=maxlength),
                          mask=list(_izip_records(seqmask, flatten=flatten)))
        if asrecarray:
            output = output.view(mrec.MaskedRecords)
    else:
        # Same as before, without the mask we don't need...
        for (a, n) in zip(seqarrays, sizes):
            nbmissing = (maxlength - n)
            data = a.ravel().__array__()
            if nbmissing:
                fval = mrec._check_fill_value(fill_value, a.dtype)
                if isinstance(fval, (np.ndarray, np.void)):
                    if len(fval.dtype) == 1:
                        fval = fval.item()[0]
                    else:
                        fval = np.array(fval, dtype=a.dtype, ndmin=1)
            else:
                fval = None
            seqdata.append(itertools.chain(data, [fval] * nbmissing))
        output = np.fromiter(tuple(_izip_records(seqdata, flatten=flatten)),
                             dtype=newdtype, count=maxlength)
        if asrecarray:
            output = output.view(np.recarray)
    # And we're done...
    return output


def _drop_fields_dispatcher(base, drop_names, usemask=None, asrecarray=None):
    return (base,)


@array_function_dispatch(_drop_fields_dispatcher)
def drop_fields(base, drop_names, usemask=True, asrecarray=False):
    """
    Return a new array with fields in `drop_names` dropped.

    Nested fields are supported.

    Parameters
    ----------
    base : array
        Input array
    drop_names : string or sequence
        String or sequence of strings corresponding to the names of the
        fields to drop.
    usemask : {False, True}, optional
        Whether to return a masked array or not.
    asrecarray : string or sequence, optional
        Whether to return a recarray or a mrecarray (`asrecarray=True`) or
        a plain ndarray or masked array with flexible dtype. The default
        is False.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.lib import recfunctions as rfn
    >>> a = np.array([(1, (2, 3.0)), (4, (5, 6.0))],
    ...   dtype=[('a', np.int64), ('b', [('ba', np.double), ('bb', np.int64)])])
    >>> rfn.drop_fields(a, 'a')
    array([((2., 3),), ((5., 6),)],
          dtype=[('b', [('ba', '<f8'), ('bb', '<i8')])])
    >>> rfn.drop_fields(a, 'ba')
    array([(1, (3,)), (4, (6,))], dtype=[('a', '<i8'), ('b', [('bb', '<i8')])])
    >>> rfn.drop_fields(a, ['ba', 'bb'])
    array([(1,), (4,)], dtype=[('a', '<i8')])
    """
    if _is_string_like(drop_names):
        drop_names = [drop_names]
    else:
        drop_names = set(drop_names)

    def _drop_descr(ndtype, drop_names):
        names = ndtype.names
        newdtype = []
        for name in names:
            current = ndtype[name]
            if name in drop_names:
                continue
            if current.names is not None:
                descr = _drop_descr(current, drop_names)
                if descr:
                    newdtype.append((name, descr))
            else:
                newdtype.append((name, current))
        return newdtype

    newdtype = _drop_descr(base.dtype, drop_names)

    output = np.empty(base.shape, dtype=newdtype)
    output = recursive_fill_fields(base, output)
    return _fix_output(output, usemask=usemask, asrecarray=asrecarray)


def _keep_fields(base, keep_names, usemask=True, asrecarray=False):
    """
    Return a new array keeping only the fields in `keep_names`,
    and preserving the order of those fields.

    Parameters
    ----------
    base : array
        Input array
    keep_names : string or sequence
        String or sequence of strings corresponding to the names of the
        fields to keep. Order of the names will be preserved.
    usemask : {False, True}, optional
        Whether to return a masked array or not.
    asrecarray : string or sequence, optional
        Whether to return a recarray or a mrecarray (`asrecarray=True`) or
        a plain ndarray or masked array with flexible dtype. The default
        is False.
    """
    newdtype = [(n, base.dtype[n]) for n in keep_names]
    output = np.empty(base.shape, dtype=newdtype)
    output = recursive_fill_fields(base, output)
    return _fix_output(output, usemask=usemask, asrecarray=asrecarray)


def _rec_drop_fields_dispatcher(base, drop_names):
    return (base,)


@array_function_dispatch(_rec_drop_fields_dispatcher)
def rec_drop_fields(base, drop_names):
    """
    Returns a new numpy.recarray with fields in `drop_names` dropped.
    """
    return drop_fields(base, drop_names, usemask=False, asrecarray=True)


def _rename_fields_dispatcher(base, namemapper):
    return (base,)


@array_function_dispatch(_rename_fields_dispatcher)
def rename_fields(base, namemapper):
    """
    Rename the fields from a flexible-datatype ndarray or recarray.

    Nested fields are supported.

    Parameters
    ----------
    base : ndarray
        Input array whose fields must be modified.
    namemapper : dictionary
        Dictionary mapping old field names to their new version.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.lib import recfunctions as rfn
    >>> a = np.array([(1, (2, [3.0, 30.])), (4, (5, [6.0, 60.]))],
    ...   dtype=[('a', int),('b', [('ba', float), ('bb', (float, 2))])])
    >>> rfn.rename_fields(a, {'a':'A', 'bb':'BB'})
    array([(1, (2., [ 3., 30.])), (4, (5., [ 6., 60.]))],
          dtype=[('A', '<i8'), ('b', [('ba', '<f8'), ('BB', '<f8', (2,))])])

    """
    def _recursive_rename_fields(ndtype, namemapper):
        newdtype = []
        for name in ndtype.names:
            newname = namemapper.get(name, name)
            current = ndtype[name]
            if current.names is not None:
                newdtype.append(
                    (newname, _recursive_rename_fields(current, namemapper))
                    )
            else:
                newdtype.append((newname, current))
        return newdtype
    newdtype = _recursive_rename_fields(base.dtype, namemapper)
    return base.view(newdtype)


def _append_fields_dispatcher(base, names, data, dtypes=None,
                              fill_value=None, usemask=None, asrecarray=None):
    yield base
    yield from data


@array_function_dispatch(_append_fields_dispatcher)
def append_fields(base, names, data, dtypes=None,
                  fill_value=-1, usemask=True, asrecarray=False):
    """
    Add new fields to an existing array.

    The names of the fields are given with the `names` arguments,
    the corresponding values with the `data` arguments.
    If a single field is appended, `names`, `data` and `dtypes` do not have
    to be lists but just values.

    Parameters
    ----------
    base : array
        Input array to extend.
    names : string, sequence
        String or sequence of strings corresponding to the names
        of the new fields.
    data : array or sequence of arrays
        Array or sequence of arrays storing the fields to add to the base.
    dtypes : sequence of datatypes, optional
        Datatype or sequence of datatypes.
        If None, the datatypes are estimated from the `data`.
    fill_value : {float}, optional
        Filling value used to pad missing data on the shorter arrays.
    usemask : {False, True}, optional
        Whether to return a masked array or not.
    asrecarray : {False, True}, optional
        Whether to return a recarray (MaskedRecords) or not.

    """
    # Check the names
    if isinstance(names, (tuple, list)):
        if len(names) != len(data):
            msg = "The number of arrays does not match the number of names"
            raise ValueError(msg)
    elif isinstance(names, str):
        names = [names, ]
        data = [data, ]
    #
    if dtypes is None:
        data = [np.array(a, copy=None, subok=True) for a in data]
        data = [a.view([(name, a.dtype)]) for (name, a) in zip(names, data)]
    else:
        if not isinstance(dtypes, (tuple, list)):
            dtypes = [dtypes, ]
        if len(data) != len(dtypes):
            if len(dtypes) == 1:
                dtypes = dtypes * len(data)
            else:
                msg = "The dtypes argument must be None, a dtype, or a list."
                raise ValueError(msg)
        data = [np.array(a, copy=None, subok=True, dtype=d).view([(n, d)])
                for (a, n, d) in zip(data, names, dtypes)]
    #
    base = merge_arrays(base, usemask=usemask, fill_value=fill_value)
    if len(data) > 1:
        data = merge_arrays(data, flatten=True, usemask=usemask,
                            fill_value=fill_value)
    else:
        data = data.pop()
    #
    output = ma.masked_all(
        max(len(base), len(data)),
        dtype=_get_fieldspec(base.dtype) + _get_fieldspec(data.dtype))
    output = recursive_fill_fields(base, output)
    output = recursive_fill_fields(data, output)
    #
    return _fix_output(output, usemask=usemask, asrecarray=asrecarray)


def _rec_append_fields_dispatcher(base, names, data, dtypes=None):
    yield base
    yield from data


@array_function_dispatch(_rec_append_fields_dispatcher)
def rec_append_fields(base, names, data, dtypes=None):
    """
    Add new fields to an existing array.

    The names of the fields are given with the `names` arguments,
    the corresponding values with the `data` arguments.
    If a single field is appended, `names`, `data` and `dtypes` do not have
    to be lists but just values.

    Parameters
    ----------
    base : array
        Input array to extend.
    names : string, sequence
        String or sequence of strings corresponding to the names
        of the new fields.
    data : array or sequence of arrays
        Array or sequence of arrays storing the fields to add to the base.
    dtypes : sequence of datatypes, optional
        Datatype or sequence of datatypes.
        If None, the datatypes are estimated from the `data`.

    See Also
    --------
    append_fields

    Returns
    -------
    appended_array : np.recarray
    """
    return append_fields(base, names, data=data, dtypes=dtypes,
                         asrecarray=True, usemask=False)


def _repack_fields_dispatcher(a, align=None, recurse=None):
    return (a,)


@array_function_dispatch(_repack_fields_dispatcher)
def repack_fields(a, align=False, recurse=False):
    """
    Re-pack the fields of a structured array or dtype in memory.

    The memory layout of structured datatypes allows fields at arbitrary
    byte offsets. This means the fields can be separated by padding bytes,
    their offsets can be non-monotonically increasing, and they can overlap.

    This method removes any overlaps and reorders the fields in memory so they
    have increasing byte offsets, and adds or removes padding bytes depending
    on the `align` option, which behaves like the `align` option to
    `numpy.dtype`.

    If `align=False`, this method produces a "packed" memory layout in which
    each field starts at the byte the previous field ended, and any padding
    bytes are removed.

    If `align=True`, this methods produces an "aligned" memory layout in which
    each field's offset is a multiple of its alignment, and the total itemsize
    is a multiple of the largest alignment, by adding padding bytes as needed.

    Parameters
    ----------
    a : ndarray or dtype
       array or dtype for which to repack the fields.
    align : boolean
       If true, use an "aligned" memory layout, otherwise use a "packed" layout.
    recurse : boolean
       If True, also repack nested structures.

    Returns
    -------
    repacked : ndarray or dtype
       Copy of `a` with fields repacked, or `a` itself if no repacking was
       needed.

    Examples
    --------
    >>> import numpy as np

    >>> from numpy.lib import recfunctions as rfn
    >>> def print_offsets(d):
    ...     print("offsets:", [d.fields[name][1] for name in d.names])
    ...     print("itemsize:", d.itemsize)
    ...
    >>> dt = np.dtype('u1, <i8, <f8', align=True)
    >>> dt
    dtype({'names': ['f0', 'f1', 'f2'], 'formats': ['u1', '<i8', '<f8'], \
'offsets': [0, 8, 16], 'itemsize': 24}, align=True)
    >>> print_offsets(dt)
    offsets: [0, 8, 16]
    itemsize: 24
    >>> packed_dt = rfn.repack_fields(dt)
    >>> packed_dt
    dtype([('f0', 'u1'), ('f1', '<i8'), ('f2', '<f8')])
    >>> print_offsets(packed_dt)
    offsets: [0, 1, 9]
    itemsize: 17

    """
    if not isinstance(a, np.dtype):
        dt = repack_fields(a.dtype, align=align, recurse=recurse)
        return a.astype(dt, copy=False)

    if a.names is None:
        return a

    fieldinfo = []
    for name in a.names:
        tup = a.fields[name]
        if recurse:
            fmt = repack_fields(tup[0], align=align, recurse=True)
        else:
            fmt = tup[0]

        if len(tup) == 3:
            name = (tup[2], name)

        fieldinfo.append((name, fmt))

    dt = np.dtype(fieldinfo, align=align)
    return np.dtype((a.type, dt))

def _get_fields_and_offsets(dt, offset=0):
    """
    Returns a flat list of (dtype, count, offset) tuples of all the
    scalar fields in the dtype "dt", including nested fields, in left
    to right order.
    """

    # counts up elements in subarrays, including nested subarrays, and returns
    # base dtype and count
    def count_elem(dt):
        count = 1
        while dt.shape != ():
            for size in dt.shape:
                count *= size
            dt = dt.base
        return dt, count

    fields = []
    for name in dt.names:
        field = dt.fields[name]
        f_dt, f_offset = field[0], field[1]
        f_dt, n = count_elem(f_dt)

        if f_dt.names is None:
            fields.append((np.dtype((f_dt, (n,))), n, f_offset + offset))
        else:
            subfields = _get_fields_and_offsets(f_dt, f_offset + offset)
            size = f_dt.itemsize

            for i in range(n):
                if i == 0:
                    # optimization: avoid list comprehension if no subarray
                    fields.extend(subfields)
                else:
                    fields.extend([(d, c, o + i * size) for d, c, o in subfields])
    return fields

def _common_stride(offsets, counts, itemsize):
    """
    Returns the stride between the fields, or None if the stride is not
    constant. The values in "counts" designate the lengths of
    subarrays. Subarrays are treated as many contiguous fields, with
    always positive stride.
    """
    if len(offsets) <= 1:
        return itemsize

    negative = offsets[1] < offsets[0]  # negative stride
    if negative:
        # reverse, so offsets will be ascending
        it = zip(reversed(offsets), reversed(counts))
    else:
        it = zip(offsets, counts)

    prev_offset = None
    stride = None
    for offset, count in it:
        if count != 1:  # subarray: always c-contiguous
            if negative:
                return None  # subarrays can never have a negative stride
            if stride is None:
                stride = itemsize
            if stride != itemsize:
                return None
            end_offset = offset + (count - 1) * itemsize
        else:
            end_offset = offset

        if prev_offset is not None:
            new_stride = offset - prev_offset
            if stride is None:
                stride = new_stride
            if stride != new_stride:
                return None

        prev_offset = end_offset

    if negative:
        return -stride
    return stride


def _structured_to_unstructured_dispatcher(arr, dtype=None, copy=None,
                                           casting=None):
    return (arr,)

@array_function_dispatch(_structured_to_unstructured_dispatcher)
def structured_to_unstructured(arr, dtype=None, copy=False, casting='unsafe'):
    """
    Converts an n-D structured array into an (n+1)-D unstructured array.

    The new array will have a new last dimension equal in size to the
    number of field-elements of the input array. If not supplied, the output
    datatype is determined from the numpy type promotion rules applied to all
    the field datatypes.

    Nested fields, as well as each element of any subarray fields, all count
    as a single field-elements.

    Parameters
    ----------
    arr : ndarray
       Structured array or dtype to convert. Cannot contain object datatype.
    dtype : dtype, optional
       The dtype of the output unstructured array.
    copy : bool, optional
        If true, always return a copy. If false, a view is returned if
        possible, such as when the `dtype` and strides of the fields are
        suitable and the array subtype is one of `numpy.ndarray`,
        `numpy.recarray` or `numpy.memmap`.

        .. versionchanged:: 1.25.0
            A view can now be returned if the fields are separated by a
            uniform stride.

    casting : {'no', 'equiv', 'safe', 'same_kind', 'unsafe'}, optional
        See casting argument of `numpy.ndarray.astype`. Controls what kind of
        data casting may occur.

    Returns
    -------
    unstructured : ndarray
       Unstructured array with one more dimension.

    Examples
    --------
    >>> import numpy as np

    >>> from numpy.lib import recfunctions as rfn
    >>> a = np.zeros(4, dtype=[('a', 'i4'), ('b', 'f4,u2'), ('c', 'f4', 2)])
    >>> a
    array([(0, (0., 0), [0., 0.]), (0, (0., 0), [0., 0.]),
           (0, (0., 0), [0., 0.]), (0, (0., 0), [0., 0.])],
          dtype=[('a', '<i4'), ('b', [('f0', '<f4'), ('f1', '<u2')]), ('c', '<f4', (2,))])
    >>> rfn.structured_to_unstructured(a)
    array([[0., 0., 0., 0., 0.],
           [0., 0., 0., 0., 0.],
           [0., 0., 0., 0., 0.],
           [0., 0., 0., 0., 0.]])

    >>> b = np.array([(1, 2, 5), (4, 5, 7), (7, 8 ,11), (10, 11, 12)],
    ...              dtype=[('x', 'i4'), ('y', 'f4'), ('z', 'f8')])
    >>> np.mean(rfn.structured_to_unstructured(b[['x', 'z']]), axis=-1)
    array([ 3. ,  5.5,  9. , 11. ])

    """  # noqa: E501
    if arr.dtype.names is None:
        raise ValueError('arr must be a structured array')

    fields = _get_fields_and_offsets(arr.dtype)
    n_fields = len(fields)
    if n_fields == 0 and dtype is None:
        raise ValueError("arr has no fields. Unable to guess dtype")
    elif n_fields == 0:
        # too many bugs elsewhere for this to work now
        raise NotImplementedError("arr with no fields is not supported")

    dts, counts, offsets = zip(*fields)
    names = [f'f{n}' for n in range(n_fields)]

    if dtype is None:
        out_dtype = np.result_type(*[dt.base for dt in dts])
    else:
        out_dtype = np.dtype(dtype)

    # Use a series of views and casts to convert to an unstructured array:

    # first view using flattened fields (doesn't work for object arrays)
    # Note: dts may include a shape for subarrays
    flattened_fields = np.dtype({'names': names,
                                 'formats': dts,
                                 'offsets': offsets,
                                 'itemsize': arr.dtype.itemsize})
    arr = arr.view(flattened_fields)

    # we only allow a few types to be unstructured by manipulating the
    # strides, because we know it won't work with, for example, np.matrix nor
    # np.ma.MaskedArray.
    can_view = type(arr) in (np.ndarray, np.recarray, np.memmap)
    if (not copy) and can_view and all(dt.base == out_dtype for dt in dts):
        # all elements have the right dtype already; if they have a common
        # stride, we can just return a view
        common_stride = _common_stride(offsets, counts, out_dtype.itemsize)
        if common_stride is not None:
            wrap = arr.__array_wrap__

            new_shape = arr.shape + (sum(counts), out_dtype.itemsize)
            new_strides = arr.strides + (abs(common_stride), 1)

            arr = arr[..., np.newaxis].view(np.uint8)  # view as bytes
            arr = arr[..., min(offsets):]  # remove the leading unused data
            arr = np.lib.stride_tricks.as_strided(arr,
                                                  new_shape,
                                                  new_strides,
                                                  subok=True)

            # cast and drop the last dimension again
            arr = arr.view(out_dtype)[..., 0]

            if common_stride < 0:
                arr = arr[..., ::-1]  # reverse, if the stride was negative
            if type(arr) is not type(wrap.__self__):
                # Some types (e.g. recarray) turn into an ndarray along the
                # way, so we have to wrap it again in order to match the
                # behavior with copy=True.
                arr = wrap(arr)
            return arr

    # next cast to a packed format with all fields converted to new dtype
    packed_fields = np.dtype({'names': names,
                              'formats': [(out_dtype, dt.shape) for dt in dts]})
    arr = arr.astype(packed_fields, copy=copy, casting=casting)

    # finally is it safe to view the packed fields as the unstructured type
    return arr.view((out_dtype, (sum(counts),)))


def _unstructured_to_structured_dispatcher(arr, dtype=None, names=None,
                                           align=None, copy=None, casting=None):
    return (arr,)

@array_function_dispatch(_unstructured_to_structured_dispatcher)
def unstructured_to_structured(arr, dtype=None, names=None, align=False,
                               copy=False, casting='unsafe'):
    """
    Converts an n-D unstructured array into an (n-1)-D structured array.

    The last dimension of the input array is converted into a structure, with
    number of field-elements equal to the size of the last dimension of the
    input array. By default all output fields have the input array's dtype, but
    an output structured dtype with an equal number of fields-elements can be
    supplied instead.

    Nested fields, as well as each element of any subarray fields, all count
    towards the number of field-elements.

    Parameters
    ----------
    arr : ndarray
       Unstructured array or dtype to convert.
    dtype : dtype, optional
       The structured dtype of the output array
    names : list of strings, optional
       If dtype is not supplied, this specifies the field names for the output
       dtype, in order. The field dtypes will be the same as the input array.
    align : boolean, optional
       Whether to create an aligned memory layout.
    copy : bool, optional
        See copy argument to `numpy.ndarray.astype`. If true, always return a
        copy. If false, and `dtype` requirements are satisfied, a view is
        returned.
    casting : {'no', 'equiv', 'safe', 'same_kind', 'unsafe'}, optional
        See casting argument of `numpy.ndarray.astype`. Controls what kind of
        data casting may occur.

    Returns
    -------
    structured : ndarray
       Structured array with fewer dimensions.

    Examples
    --------
    >>> import numpy as np

    >>> from numpy.lib import recfunctions as rfn
    >>> dt = np.dtype([('a', 'i4'), ('b', 'f4,u2'), ('c', 'f4', 2)])
    >>> a = np.arange(20).reshape((4,5))
    >>> a
    array([[ 0,  1,  2,  3,  4],
           [ 5,  6,  7,  8,  9],
           [10, 11, 12, 13, 14],
           [15, 16, 17, 18, 19]])
    >>> rfn.unstructured_to_structured(a, dt)
    array([( 0, ( 1.,  2), [ 3.,  4.]), ( 5, ( 6.,  7), [ 8.,  9.]),
           (10, (11., 12), [13., 14.]), (15, (16., 17), [18., 19.])],
          dtype=[('a', '<i4'), ('b', [('f0', '<f4'), ('f1', '<u2')]), ('c', '<f4', (2,))])

    """  # noqa: E501
    if arr.shape == ():
        raise ValueError('arr must have at least one dimension')
    n_elem = arr.shape[-1]
    if n_elem == 0:
        # too many bugs elsewhere for this to work now
        raise NotImplementedError("last axis with size 0 is not supported")

    if dtype is None:
        if names is None:
            names = [f'f{n}' for n in range(n_elem)]
        out_dtype = np.dtype([(n, arr.dtype) for n in names], align=align)
        fields = _get_fields_and_offsets(out_dtype)
        dts, counts, offsets = zip(*fields)
    else:
        if names is not None:
            raise ValueError("don't supply both dtype and names")
        # if dtype is the args of np.dtype, construct it
        dtype = np.dtype(dtype)
        # sanity check of the input dtype
        fields = _get_fields_and_offsets(dtype)
        if len(fields) == 0:
            dts, counts, offsets = [], [], []
        else:
            dts, counts, offsets = zip(*fields)

        if n_elem != sum(counts):
            raise ValueError('The length of the last dimension of arr must '
                             'be equal to the number of fields in dtype')
        out_dtype = dtype
        if align and not out_dtype.isalignedstruct:
            raise ValueError("align was True but dtype is not aligned")

    names = [f'f{n}' for n in range(len(fields))]

    # Use a series of views and casts to convert to a structured array:

    # first view as a packed structured array of one dtype
    packed_fields = np.dtype({'names': names,
                              'formats': [(arr.dtype, dt.shape) for dt in dts]})
    arr = np.ascontiguousarray(arr).view(packed_fields)

    # next cast to an unpacked but flattened format with varied dtypes
    flattened_fields = np.dtype({'names': names,
                                 'formats': dts,
                                 'offsets': offsets,
                                 'itemsize': out_dtype.itemsize})
    arr = arr.astype(flattened_fields, copy=copy, casting=casting)

    # finally view as the final nested dtype and remove the last axis
    return arr.view(out_dtype)[..., 0]

def _apply_along_fields_dispatcher(func, arr):
    return (arr,)

@array_function_dispatch(_apply_along_fields_dispatcher)
def apply_along_fields(func, arr):
    """
    Apply function 'func' as a reduction across fields of a structured array.

    This is similar to `numpy.apply_along_axis`, but treats the fields of a
    structured array as an extra axis. The fields are all first cast to a
    common type following the type-promotion rules from `numpy.result_type`
    applied to the field's dtypes.

    Parameters
    ----------
    func : function
       Function to apply on the "field" dimension. This function must
       support an `axis` argument, like `numpy.mean`, `numpy.sum`, etc.
    arr : ndarray
       Structured array for which to apply func.

    Returns
    -------
    out : ndarray
       Result of the reduction operation

    Examples
    --------
    >>> import numpy as np

    >>> from numpy.lib import recfunctions as rfn
    >>> b = np.array([(1, 2, 5), (4, 5, 7), (7, 8 ,11), (10, 11, 12)],
    ...              dtype=[('x', 'i4'), ('y', 'f4'), ('z', 'f8')])
    >>> rfn.apply_along_fields(np.mean, b)
    array([ 2.66666667,  5.33333333,  8.66666667, 11.        ])
    >>> rfn.apply_along_fields(np.mean, b[['x', 'z']])
    array([ 3. ,  5.5,  9. , 11. ])

    """
    if arr.dtype.names is None:
        raise ValueError('arr must be a structured array')

    uarr = structured_to_unstructured(arr)
    return func(uarr, axis=-1)
    # works and avoids axis requirement, but very, very slow:
    #return np.apply_along_axis(func, -1, uarr)

def _assign_fields_by_name_dispatcher(dst, src, zero_unassigned=None):
    return dst, src

@array_function_dispatch(_assign_fields_by_name_dispatcher)
def assign_fields_by_name(dst, src, zero_unassigned=True):
    """
    Assigns values from one structured array to another by field name.

    Normally in numpy >= 1.14, assignment of one structured array to another
    copies fields "by position", meaning that the first field from the src is
    copied to the first field of the dst, and so on, regardless of field name.

    This function instead copies "by field name", such that fields in the dst
    are assigned from the identically named field in the src. This applies
    recursively for nested structures. This is how structure assignment worked
    in numpy >= 1.6 to <= 1.13.

    Parameters
    ----------
    dst : ndarray
    src : ndarray
        The source and destination arrays during assignment.
    zero_unassigned : bool, optional
        If True, fields in the dst for which there was no matching
        field in the src are filled with the value 0 (zero). This
        was the behavior of numpy <= 1.13. If False, those fields
        are not modified.
    """

    if dst.dtype.names is None:
        dst[...] = src
        return

    for name in dst.dtype.names:
        if name not in src.dtype.names:
            if zero_unassigned:
                dst[name] = 0
        else:
            assign_fields_by_name(dst[name], src[name],
                                  zero_unassigned)

def _require_fields_dispatcher(array, required_dtype):
    return (array,)

@array_function_dispatch(_require_fields_dispatcher)
def require_fields(array, required_dtype):
    """
    Casts a structured array to a new dtype using assignment by field-name.

    This function assigns from the old to the new array by name, so the
    value of a field in the output array is the value of the field with the
    same name in the source array. This has the effect of creating a new
    ndarray containing only the fields "required" by the required_dtype.

    If a field name in the required_dtype does not exist in the
    input array, that field is created and set to 0 in the output array.

    Parameters
    ----------
    a : ndarray
       array to cast
    required_dtype : dtype
       datatype for output array

    Returns
    -------
    out : ndarray
        array with the new dtype, with field values copied from the fields in
        the input array with the same name

    Examples
    --------
    >>> import numpy as np

    >>> from numpy.lib import recfunctions as rfn
    >>> a = np.ones(4, dtype=[('a', 'i4'), ('b', 'f8'), ('c', 'u1')])
    >>> rfn.require_fields(a, [('b', 'f4'), ('c', 'u1')])
    array([(1., 1), (1., 1), (1., 1), (1., 1)],
      dtype=[('b', '<f4'), ('c', 'u1')])
    >>> rfn.require_fields(a, [('b', 'f4'), ('newf', 'u1')])
    array([(1., 0), (1., 0), (1., 0), (1., 0)],
      dtype=[('b', '<f4'), ('newf', 'u1')])

    """
    out = np.empty(array.shape, dtype=required_dtype)
    assign_fields_by_name(out, array)
    return out


def _stack_arrays_dispatcher(arrays, defaults=None, usemask=None,
                             asrecarray=None, autoconvert=None):
    return arrays


@array_function_dispatch(_stack_arrays_dispatcher)
def stack_arrays(arrays, defaults=None, usemask=True, asrecarray=False,
                 autoconvert=False):
    """
    Superposes arrays fields by fields

    Parameters
    ----------
    arrays : array or sequence
        Sequence of input arrays.
    defaults : dictionary, optional
        Dictionary mapping field names to the corresponding default values.
    usemask : {True, False}, optional
        Whether to return a MaskedArray (or MaskedRecords is
        `asrecarray==True`) or a ndarray.
    asrecarray : {False, True}, optional
        Whether to return a recarray (or MaskedRecords if `usemask==True`)
        or just a flexible-type ndarray.
    autoconvert : {False, True}, optional
        Whether automatically cast the type of the field to the maximum.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.lib import recfunctions as rfn
    >>> x = np.array([1, 2,])
    >>> rfn.stack_arrays(x) is x
    True
    >>> z = np.array([('A', 1), ('B', 2)], dtype=[('A', '|S3'), ('B', float)])
    >>> zz = np.array([('a', 10., 100.), ('b', 20., 200.), ('c', 30., 300.)],
    ...   dtype=[('A', '|S3'), ('B', np.double), ('C', np.double)])
    >>> test = rfn.stack_arrays((z,zz))
    >>> test
    masked_array(data=[(b'A', 1.0, --), (b'B', 2.0, --), (b'a', 10.0, 100.0),
                       (b'b', 20.0, 200.0), (b'c', 30.0, 300.0)],
                 mask=[(False, False,  True), (False, False,  True),
                       (False, False, False), (False, False, False),
                       (False, False, False)],
           fill_value=(b'N/A', 1e+20, 1e+20),
                dtype=[('A', 'S3'), ('B', '<f8'), ('C', '<f8')])

    """
    if isinstance(arrays, np.ndarray):
        return arrays
    elif len(arrays) == 1:
        return arrays[0]
    seqarrays = [np.asanyarray(a).ravel() for a in arrays]
    nrecords = [len(a) for a in seqarrays]
    ndtype = [a.dtype for a in seqarrays]
    fldnames = [d.names for d in ndtype]
    #
    dtype_l = ndtype[0]
    newdescr = _get_fieldspec(dtype_l)
    names = [n for n, d in newdescr]
    for dtype_n in ndtype[1:]:
        for fname, fdtype in _get_fieldspec(dtype_n):
            if fname not in names:
                newdescr.append((fname, fdtype))
                names.append(fname)
            else:
                nameidx = names.index(fname)
                _, cdtype = newdescr[nameidx]
                if autoconvert:
                    newdescr[nameidx] = (fname, max(fdtype, cdtype))
                elif fdtype != cdtype:
                    raise TypeError(f"Incompatible type '{cdtype}' <> '{fdtype}'")
    # Only one field: use concatenate
    if len(newdescr) == 1:
        output = ma.concatenate(seqarrays)
    else:
        #
        output = ma.masked_all((np.sum(nrecords),), newdescr)
        offset = np.cumsum(np.r_[0, nrecords])
        seen = []
        for (a, n, i, j) in zip(seqarrays, fldnames, offset[:-1], offset[1:]):
            names = a.dtype.names
            if names is None:
                output[f'f{len(seen)}'][i:j] = a
            else:
                for name in n:
                    output[name][i:j] = a[name]
                    if name not in seen:
                        seen.append(name)
    #
    return _fix_output(_fix_defaults(output, defaults),
                       usemask=usemask, asrecarray=asrecarray)


def _find_duplicates_dispatcher(
        a, key=None, ignoremask=None, return_index=None):
    return (a,)


@array_function_dispatch(_find_duplicates_dispatcher)
def find_duplicates(a, key=None, ignoremask=True, return_index=False):
    """
    Find the duplicates in a structured array along a given key

    Parameters
    ----------
    a : array-like
        Input array
    key : {string, None}, optional
        Name of the fields along which to check the duplicates.
        If None, the search is performed by records
    ignoremask : {True, False}, optional
        Whether masked data should be discarded or considered as duplicates.
    return_index : {False, True}, optional
        Whether to return the indices of the duplicated values.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.lib import recfunctions as rfn
    >>> ndtype = [('a', int)]
    >>> a = np.ma.array([1, 1, 1, 2, 2, 3, 3],
    ...         mask=[0, 0, 1, 0, 0, 0, 1]).view(ndtype)
    >>> rfn.find_duplicates(a, ignoremask=True, return_index=True)
    (masked_array(data=[(1,), (1,), (2,), (2,)],
                 mask=[(False,), (False,), (False,), (False,)],
           fill_value=(999999,),
                dtype=[('a', '<i8')]), array([0, 1, 3, 4]))
    """
    a = np.asanyarray(a).ravel()
    # Get a dictionary of fields
    fields = get_fieldstructure(a.dtype)
    # Get the sorting data (by selecting the corresponding field)
    base = a
    if key:
        for f in fields[key]:
            base = base[f]
        base = base[key]
    # Get the sorting indices and the sorted data
    sortidx = base.argsort()
    sortedbase = base[sortidx]
    sorteddata = sortedbase.filled()
    # Compare the sorting data
    flag = (sorteddata[:-1] == sorteddata[1:])
    # If masked data must be ignored, set the flag to false where needed
    if ignoremask:
        sortedmask = sortedbase.recordmask
        flag[sortedmask[1:]] = False
    flag = np.concatenate(([False], flag))
    # We need to take the point on the left as well (else we're missing it)
    flag[:-1] = flag[:-1] + flag[1:]
    duplicates = a[sortidx][flag]
    if return_index:
        return (duplicates, sortidx[flag])
    else:
        return duplicates


def _join_by_dispatcher(
        key, r1, r2, jointype=None, r1postfix=None, r2postfix=None,
        defaults=None, usemask=None, asrecarray=None):
    return (r1, r2)


@array_function_dispatch(_join_by_dispatcher)
def join_by(key, r1, r2, jointype='inner', r1postfix='1', r2postfix='2',
            defaults=None, usemask=True, asrecarray=False):
    """
    Join arrays `r1` and `r2` on key `key`.

    The key should be either a string or a sequence of string corresponding
    to the fields used to join the array.  An exception is raised if the
    `key` field cannot be found in the two input arrays.  Neither `r1` nor
    `r2` should have any duplicates along `key`: the presence of duplicates
    will make the output quite unreliable. Note that duplicates are not
    looked for by the algorithm.

    Parameters
    ----------
    key : {string, sequence}
        A string or a sequence of strings corresponding to the fields used
        for comparison.
    r1, r2 : arrays
        Structured arrays.
    jointype : {'inner', 'outer', 'leftouter'}, optional
        If 'inner', returns the elements common to both r1 and r2.
        If 'outer', returns the common elements as well as the elements of
        r1 not in r2 and the elements of not in r2.
        If 'leftouter', returns the common elements and the elements of r1
        not in r2.
    r1postfix : string, optional
        String appended to the names of the fields of r1 that are present
        in r2 but absent of the key.
    r2postfix : string, optional
        String appended to the names of the fields of r2 that are present
        in r1 but absent of the key.
    defaults : {dictionary}, optional
        Dictionary mapping field names to the corresponding default values.
    usemask : {True, False}, optional
        Whether to return a MaskedArray (or MaskedRecords is
        `asrecarray==True`) or a ndarray.
    asrecarray : {False, True}, optional
        Whether to return a recarray (or MaskedRecords if `usemask==True`)
        or just a flexible-type ndarray.

    Notes
    -----
    * The output is sorted along the key.
    * A temporary array is formed by dropping the fields not in the key for
      the two arrays and concatenating the result. This array is then
      sorted, and the common entries selected. The output is constructed by
      filling the fields with the selected entries. Matching is not
      preserved if there are some duplicates...

    """
    # Check jointype
    if jointype not in ('inner', 'outer', 'leftouter'):
        raise ValueError(
                "The 'jointype' argument should be in 'inner', "
                "'outer' or 'leftouter' (got '%s' instead)" % jointype
                )
    # If we have a single key, put it in a tuple
    if isinstance(key, str):
        key = (key,)

    # Check the keys
    if len(set(key)) != len(key):
        dup = next(x for n, x in enumerate(key) if x in key[n + 1:])
        raise ValueError(f"duplicate join key {dup!r}")
    for name in key:
        if name not in r1.dtype.names:
            raise ValueError(f'r1 does not have key field {name!r}')
        if name not in r2.dtype.names:
            raise ValueError(f'r2 does not have key field {name!r}')

    # Make sure we work with ravelled arrays
    r1 = r1.ravel()
    r2 = r2.ravel()
    (nb1, nb2) = (len(r1), len(r2))
    (r1names, r2names) = (r1.dtype.names, r2.dtype.names)

    # Check the names for collision
    collisions = (set(r1names) & set(r2names)) - set(key)
    if collisions and not (r1postfix or r2postfix):
        msg = "r1 and r2 contain common names, r1postfix and r2postfix "
        msg += "can't both be empty"
        raise ValueError(msg)

    # Make temporary arrays of just the keys
    #  (use order of keys in `r1` for back-compatibility)
    key1 = [n for n in r1names if n in key]
    r1k = _keep_fields(r1, key1)
    r2k = _keep_fields(r2, key1)

    # Concatenate the two arrays for comparison
    aux = ma.concatenate((r1k, r2k))
    idx_sort = aux.argsort(order=key)
    aux = aux[idx_sort]
    #
    # Get the common keys
    flag_in = ma.concatenate(([False], aux[1:] == aux[:-1]))
    flag_in[:-1] = flag_in[1:] + flag_in[:-1]
    idx_in = idx_sort[flag_in]
    idx_1 = idx_in[(idx_in < nb1)]
    idx_2 = idx_in[(idx_in >= nb1)] - nb1
    (r1cmn, r2cmn) = (len(idx_1), len(idx_2))
    if jointype == 'inner':
        (r1spc, r2spc) = (0, 0)
    elif jointype == 'outer':
        idx_out = idx_sort[~flag_in]
        idx_1 = np.concatenate((idx_1, idx_out[(idx_out < nb1)]))
        idx_2 = np.concatenate((idx_2, idx_out[(idx_out >= nb1)] - nb1))
        (r1spc, r2spc) = (len(idx_1) - r1cmn, len(idx_2) - r2cmn)
    elif jointype == 'leftouter':
        idx_out = idx_sort[~flag_in]
        idx_1 = np.concatenate((idx_1, idx_out[(idx_out < nb1)]))
        (r1spc, r2spc) = (len(idx_1) - r1cmn, 0)
    # Select the entries from each input
    (s1, s2) = (r1[idx_1], r2[idx_2])
    #
    # Build the new description of the output array .......
    # Start with the key fields
    ndtype = _get_fieldspec(r1k.dtype)

    # Add the fields from r1
    for fname, fdtype in _get_fieldspec(r1.dtype):
        if fname not in key:
            ndtype.append((fname, fdtype))

    # Add the fields from r2
    for fname, fdtype in _get_fieldspec(r2.dtype):
        # Have we seen the current name already ?
        # we need to rebuild this list every time
        names = [name for name, dtype in ndtype]
        try:
            nameidx = names.index(fname)
        except ValueError:
            #... we haven't: just add the description to the current list
            ndtype.append((fname, fdtype))
        else:
            # collision
            _, cdtype = ndtype[nameidx]
            if fname in key:
                # The current field is part of the key: take the largest dtype
                ndtype[nameidx] = (fname, max(fdtype, cdtype))
            else:
                # The current field is not part of the key: add the suffixes,
                # and place the new field adjacent to the old one
                ndtype[nameidx:nameidx + 1] = [
                    (fname + r1postfix, cdtype),
                    (fname + r2postfix, fdtype)
                ]
    # Rebuild a dtype from the new fields
    ndtype = np.dtype(ndtype)
    # Find the largest nb of common fields :
    # r1cmn and r2cmn should be equal, but...
    cmn = max(r1cmn, r2cmn)
    # Construct an empty array
    output = ma.masked_all((cmn + r1spc + r2spc,), dtype=ndtype)
    names = output.dtype.names
    for f in r1names:
        selected = s1[f]
        if f not in names or (f in r2names and not r2postfix and f not in key):
            f += r1postfix
        current = output[f]
        current[:r1cmn] = selected[:r1cmn]
        if jointype in ('outer', 'leftouter'):
            current[cmn:cmn + r1spc] = selected[r1cmn:]
    for f in r2names:
        selected = s2[f]
        if f not in names or (f in r1names and not r1postfix and f not in key):
            f += r2postfix
        current = output[f]
        current[:r2cmn] = selected[:r2cmn]
        if (jointype == 'outer') and r2spc:
            current[-r2spc:] = selected[r2cmn:]
    # Sort and finalize the output
    output.sort(order=key)
    kwargs = {'usemask': usemask, 'asrecarray': asrecarray}
    return _fix_output(_fix_defaults(output, defaults), **kwargs)


def _rec_join_dispatcher(
        key, r1, r2, jointype=None, r1postfix=None, r2postfix=None,
        defaults=None):
    return (r1, r2)


@array_function_dispatch(_rec_join_dispatcher)
def rec_join(key, r1, r2, jointype='inner', r1postfix='1', r2postfix='2',
             defaults=None):
    """
    Join arrays `r1` and `r2` on keys.
    Alternative to join_by, that always returns a np.recarray.

    See Also
    --------
    join_by : equivalent function
    """
    kwargs = {'jointype': jointype, 'r1postfix': r1postfix, 'r2postfix': r2postfix,
                  'defaults': defaults, 'usemask': False, 'asrecarray': True}
    return join_by(key, r1, r2, **kwargs)


del array_function_dispatch