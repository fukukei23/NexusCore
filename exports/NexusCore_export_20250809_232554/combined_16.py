
# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\tests\test_nanfunctions.py ===
import inspect
import warnings
from functools import partial

import pytest

import numpy as np
from numpy._core.numeric import normalize_axis_tuple
from numpy.exceptions import AxisError, ComplexWarning
from numpy.lib._nanfunctions_impl import _nan_mask, _replace_nan
from numpy.testing import (
    assert_,
    assert_almost_equal,
    assert_array_equal,
    assert_equal,
    assert_raises,
    assert_raises_regex,
    suppress_warnings,
)

# Test data
_ndat = np.array([[0.6244, np.nan, 0.2692, 0.0116, np.nan, 0.1170],
                  [0.5351, -0.9403, np.nan, 0.2100, 0.4759, 0.2833],
                  [np.nan, np.nan, np.nan, 0.1042, np.nan, -0.5954],
                  [0.1610, np.nan, np.nan, 0.1859, 0.3146, np.nan]])


# Rows of _ndat with nans removed
_rdat = [np.array([0.6244, 0.2692, 0.0116, 0.1170]),
         np.array([0.5351, -0.9403, 0.2100, 0.4759, 0.2833]),
         np.array([0.1042, -0.5954]),
         np.array([0.1610, 0.1859, 0.3146])]

# Rows of _ndat with nans converted to ones
_ndat_ones = np.array([[0.6244, 1.0, 0.2692, 0.0116, 1.0, 0.1170],
                       [0.5351, -0.9403, 1.0, 0.2100, 0.4759, 0.2833],
                       [1.0, 1.0, 1.0, 0.1042, 1.0, -0.5954],
                       [0.1610, 1.0, 1.0, 0.1859, 0.3146, 1.0]])

# Rows of _ndat with nans converted to zeros
_ndat_zeros = np.array([[0.6244, 0.0, 0.2692, 0.0116, 0.0, 0.1170],
                        [0.5351, -0.9403, 0.0, 0.2100, 0.4759, 0.2833],
                        [0.0, 0.0, 0.0, 0.1042, 0.0, -0.5954],
                        [0.1610, 0.0, 0.0, 0.1859, 0.3146, 0.0]])


class TestSignatureMatch:
    NANFUNCS = {
        np.nanmin: np.amin,
        np.nanmax: np.amax,
        np.nanargmin: np.argmin,
        np.nanargmax: np.argmax,
        np.nansum: np.sum,
        np.nanprod: np.prod,
        np.nancumsum: np.cumsum,
        np.nancumprod: np.cumprod,
        np.nanmean: np.mean,
        np.nanmedian: np.median,
        np.nanpercentile: np.percentile,
        np.nanquantile: np.quantile,
        np.nanvar: np.var,
        np.nanstd: np.std,
    }
    IDS = [k.__name__ for k in NANFUNCS]

    @staticmethod
    def get_signature(func, default="..."):
        """Construct a signature and replace all default parameter-values."""
        prm_list = []
        signature = inspect.signature(func)
        for prm in signature.parameters.values():
            if prm.default is inspect.Parameter.empty:
                prm_list.append(prm)
            else:
                prm_list.append(prm.replace(default=default))
        return inspect.Signature(prm_list)

    @pytest.mark.parametrize("nan_func,func", NANFUNCS.items(), ids=IDS)
    def test_signature_match(self, nan_func, func):
        # Ignore the default parameter-values as they can sometimes differ
        # between the two functions (*e.g.* one has `False` while the other
        # has `np._NoValue`)
        signature = self.get_signature(func)
        nan_signature = self.get_signature(nan_func)
        np.testing.assert_equal(signature, nan_signature)

    def test_exhaustiveness(self):
        """Validate that all nan functions are actually tested."""
        np.testing.assert_equal(
            set(self.IDS), set(np.lib._nanfunctions_impl.__all__)
        )


class TestNanFunctions_MinMax:

    nanfuncs = [np.nanmin, np.nanmax]
    stdfuncs = [np.min, np.max]

    def test_mutation(self):
        # Check that passed array is not modified.
        ndat = _ndat.copy()
        for f in self.nanfuncs:
            f(ndat)
            assert_equal(ndat, _ndat)

    def test_keepdims(self):
        mat = np.eye(3)
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            for axis in [None, 0, 1]:
                tgt = rf(mat, axis=axis, keepdims=True)
                res = nf(mat, axis=axis, keepdims=True)
                assert_(res.ndim == tgt.ndim)

    def test_out(self):
        mat = np.eye(3)
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            resout = np.zeros(3)
            tgt = rf(mat, axis=1)
            res = nf(mat, axis=1, out=resout)
            assert_almost_equal(res, resout)
            assert_almost_equal(res, tgt)

    def test_dtype_from_input(self):
        codes = 'efdgFDG'
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            for c in codes:
                mat = np.eye(3, dtype=c)
                tgt = rf(mat, axis=1).dtype.type
                res = nf(mat, axis=1).dtype.type
                assert_(res is tgt)
                # scalar case
                tgt = rf(mat, axis=None).dtype.type
                res = nf(mat, axis=None).dtype.type
                assert_(res is tgt)

    def test_result_values(self):
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            tgt = [rf(d) for d in _rdat]
            res = nf(_ndat, axis=1)
            assert_almost_equal(res, tgt)

    @pytest.mark.parametrize("axis", [None, 0, 1])
    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    @pytest.mark.parametrize("array", [
        np.array(np.nan),
        np.full((3, 3), np.nan),
    ], ids=["0d", "2d"])
    def test_allnans(self, axis, dtype, array):
        if axis is not None and array.ndim == 0:
            pytest.skip("`axis != None` not supported for 0d arrays")

        array = array.astype(dtype)
        match = "All-NaN slice encountered"
        for func in self.nanfuncs:
            with pytest.warns(RuntimeWarning, match=match):
                out = func(array, axis=axis)
            assert np.isnan(out).all()
            assert out.dtype == array.dtype

    def test_masked(self):
        mat = np.ma.fix_invalid(_ndat)
        msk = mat._mask.copy()
        for f in [np.nanmin]:
            res = f(mat, axis=1)
            tgt = f(_ndat, axis=1)
            assert_equal(res, tgt)
            assert_equal(mat._mask, msk)
            assert_(not np.isinf(mat).any())

    def test_scalar(self):
        for f in self.nanfuncs:
            assert_(f(0.) == 0.)

    def test_subclass(self):
        class MyNDArray(np.ndarray):
            pass

        # Check that it works and that type and
        # shape are preserved
        mine = np.eye(3).view(MyNDArray)
        for f in self.nanfuncs:
            res = f(mine, axis=0)
            assert_(isinstance(res, MyNDArray))
            assert_(res.shape == (3,))
            res = f(mine, axis=1)
            assert_(isinstance(res, MyNDArray))
            assert_(res.shape == (3,))
            res = f(mine)
            assert_(res.shape == ())

        # check that rows of nan are dealt with for subclasses (#4628)
        mine[1] = np.nan
        for f in self.nanfuncs:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                res = f(mine, axis=0)
                assert_(isinstance(res, MyNDArray))
                assert_(not np.any(np.isnan(res)))
                assert_(len(w) == 0)

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                res = f(mine, axis=1)
                assert_(isinstance(res, MyNDArray))
                assert_(np.isnan(res[1]) and not np.isnan(res[0])
                        and not np.isnan(res[2]))
                assert_(len(w) == 1, 'no warning raised')
                assert_(issubclass(w[0].category, RuntimeWarning))

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                res = f(mine)
                assert_(res.shape == ())
                assert_(res != np.nan)
                assert_(len(w) == 0)

    def test_object_array(self):
        arr = np.array([[1.0, 2.0], [np.nan, 4.0], [np.nan, np.nan]], dtype=object)
        assert_equal(np.nanmin(arr), 1.0)
        assert_equal(np.nanmin(arr, axis=0), [1.0, 2.0])

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            # assert_equal does not work on object arrays of nan
            assert_equal(list(np.nanmin(arr, axis=1)), [1.0, 4.0, np.nan])
            assert_(len(w) == 1, 'no warning raised')
            assert_(issubclass(w[0].category, RuntimeWarning))

    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    def test_initial(self, dtype):
        class MyNDArray(np.ndarray):
            pass

        ar = np.arange(9).astype(dtype)
        ar[:5] = np.nan

        for f in self.nanfuncs:
            initial = 100 if f is np.nanmax else 0

            ret1 = f(ar, initial=initial)
            assert ret1.dtype == dtype
            assert ret1 == initial

            ret2 = f(ar.view(MyNDArray), initial=initial)
            assert ret2.dtype == dtype
            assert ret2 == initial

    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    def test_where(self, dtype):
        class MyNDArray(np.ndarray):
            pass

        ar = np.arange(9).reshape(3, 3).astype(dtype)
        ar[0, :] = np.nan
        where = np.ones_like(ar, dtype=np.bool)
        where[:, 0] = False

        for f in self.nanfuncs:
            reference = 4 if f is np.nanmin else 8

            ret1 = f(ar, where=where, initial=5)
            assert ret1.dtype == dtype
            assert ret1 == reference

            ret2 = f(ar.view(MyNDArray), where=where, initial=5)
            assert ret2.dtype == dtype
            assert ret2 == reference


class TestNanFunctions_ArgminArgmax:

    nanfuncs = [np.nanargmin, np.nanargmax]

    def test_mutation(self):
        # Check that passed array is not modified.
        ndat = _ndat.copy()
        for f in self.nanfuncs:
            f(ndat)
            assert_equal(ndat, _ndat)

    def test_result_values(self):
        for f, fcmp in zip(self.nanfuncs, [np.greater, np.less]):
            for row in _ndat:
                with suppress_warnings() as sup:
                    sup.filter(RuntimeWarning, "invalid value encountered in")
                    ind = f(row)
                    val = row[ind]
                    # comparing with NaN is tricky as the result
                    # is always false except for NaN != NaN
                    assert_(not np.isnan(val))
                    assert_(not fcmp(val, row).any())
                    assert_(not np.equal(val, row[:ind]).any())

    @pytest.mark.parametrize("axis", [None, 0, 1])
    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    @pytest.mark.parametrize("array", [
        np.array(np.nan),
        np.full((3, 3), np.nan),
    ], ids=["0d", "2d"])
    def test_allnans(self, axis, dtype, array):
        if axis is not None and array.ndim == 0:
            pytest.skip("`axis != None` not supported for 0d arrays")

        array = array.astype(dtype)
        for func in self.nanfuncs:
            with pytest.raises(ValueError, match="All-NaN slice encountered"):
                func(array, axis=axis)

    def test_empty(self):
        mat = np.zeros((0, 3))
        for f in self.nanfuncs:
            for axis in [0, None]:
                assert_raises_regex(
                        ValueError,
                        "attempt to get argm.. of an empty sequence",
                        f, mat, axis=axis)
            for axis in [1]:
                res = f(mat, axis=axis)
                assert_equal(res, np.zeros(0))

    def test_scalar(self):
        for f in self.nanfuncs:
            assert_(f(0.) == 0.)

    def test_subclass(self):
        class MyNDArray(np.ndarray):
            pass

        # Check that it works and that type and
        # shape are preserved
        mine = np.eye(3).view(MyNDArray)
        for f in self.nanfuncs:
            res = f(mine, axis=0)
            assert_(isinstance(res, MyNDArray))
            assert_(res.shape == (3,))
            res = f(mine, axis=1)
            assert_(isinstance(res, MyNDArray))
            assert_(res.shape == (3,))
            res = f(mine)
            assert_(res.shape == ())

    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    def test_keepdims(self, dtype):
        ar = np.arange(9).astype(dtype)
        ar[:5] = np.nan

        for f in self.nanfuncs:
            reference = 5 if f is np.nanargmin else 8
            ret = f(ar, keepdims=True)
            assert ret.ndim == ar.ndim
            assert ret == reference

    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    def test_out(self, dtype):
        ar = np.arange(9).astype(dtype)
        ar[:5] = np.nan

        for f in self.nanfuncs:
            out = np.zeros((), dtype=np.intp)
            reference = 5 if f is np.nanargmin else 8
            ret = f(ar, out=out)
            assert ret is out
            assert ret == reference


_TEST_ARRAYS = {
    "0d": np.array(5),
    "1d": np.array([127, 39, 93, 87, 46])
}
for _v in _TEST_ARRAYS.values():
    _v.setflags(write=False)


@pytest.mark.parametrize(
    "dtype",
    np.typecodes["AllInteger"] + np.typecodes["AllFloat"] + "O",
)
@pytest.mark.parametrize("mat", _TEST_ARRAYS.values(), ids=_TEST_ARRAYS.keys())
class TestNanFunctions_NumberTypes:
    nanfuncs = {
        np.nanmin: np.min,
        np.nanmax: np.max,
        np.nanargmin: np.argmin,
        np.nanargmax: np.argmax,
        np.nansum: np.sum,
        np.nanprod: np.prod,
        np.nancumsum: np.cumsum,
        np.nancumprod: np.cumprod,
        np.nanmean: np.mean,
        np.nanmedian: np.median,
        np.nanvar: np.var,
        np.nanstd: np.std,
    }
    nanfunc_ids = [i.__name__ for i in nanfuncs]

    @pytest.mark.parametrize("nanfunc,func", nanfuncs.items(), ids=nanfunc_ids)
    @np.errstate(over="ignore")
    def test_nanfunc(self, mat, dtype, nanfunc, func):
        mat = mat.astype(dtype)
        tgt = func(mat)
        out = nanfunc(mat)

        assert_almost_equal(out, tgt)
        if dtype == "O":
            assert type(out) is type(tgt)
        else:
            assert out.dtype == tgt.dtype

    @pytest.mark.parametrize(
        "nanfunc,func",
        [(np.nanquantile, np.quantile), (np.nanpercentile, np.percentile)],
        ids=["nanquantile", "nanpercentile"],
    )
    def test_nanfunc_q(self, mat, dtype, nanfunc, func):
        mat = mat.astype(dtype)
        if mat.dtype.kind == "c":
            assert_raises(TypeError, func, mat, q=1)
            assert_raises(TypeError, nanfunc, mat, q=1)

        else:
            tgt = func(mat, q=1)
            out = nanfunc(mat, q=1)

            assert_almost_equal(out, tgt)

            if dtype == "O":
                assert type(out) is type(tgt)
            else:
                assert out.dtype == tgt.dtype

    @pytest.mark.parametrize(
        "nanfunc,func",
        [(np.nanvar, np.var), (np.nanstd, np.std)],
        ids=["nanvar", "nanstd"],
    )
    def test_nanfunc_ddof(self, mat, dtype, nanfunc, func):
        mat = mat.astype(dtype)
        tgt = func(mat, ddof=0.5)
        out = nanfunc(mat, ddof=0.5)

        assert_almost_equal(out, tgt)
        if dtype == "O":
            assert type(out) is type(tgt)
        else:
            assert out.dtype == tgt.dtype

    @pytest.mark.parametrize(
        "nanfunc", [np.nanvar, np.nanstd]
    )
    def test_nanfunc_correction(self, mat, dtype, nanfunc):
        mat = mat.astype(dtype)
        assert_almost_equal(
            nanfunc(mat, correction=0.5), nanfunc(mat, ddof=0.5)
        )

        err_msg = "ddof and correction can't be provided simultaneously."
        with assert_raises_regex(ValueError, err_msg):
            nanfunc(mat, ddof=0.5, correction=0.5)

        with assert_raises_regex(ValueError, err_msg):
            nanfunc(mat, ddof=1, correction=0)


class SharedNanFunctionsTestsMixin:
    def test_mutation(self):
        # Check that passed array is not modified.
        ndat = _ndat.copy()
        for f in self.nanfuncs:
            f(ndat)
            assert_equal(ndat, _ndat)

    def test_keepdims(self):
        mat = np.eye(3)
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            for axis in [None, 0, 1]:
                tgt = rf(mat, axis=axis, keepdims=True)
                res = nf(mat, axis=axis, keepdims=True)
                assert_(res.ndim == tgt.ndim)

    def test_out(self):
        mat = np.eye(3)
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            resout = np.zeros(3)
            tgt = rf(mat, axis=1)
            res = nf(mat, axis=1, out=resout)
            assert_almost_equal(res, resout)
            assert_almost_equal(res, tgt)

    def test_dtype_from_dtype(self):
        mat = np.eye(3)
        codes = 'efdgFDG'
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            for c in codes:
                with suppress_warnings() as sup:
                    if nf in {np.nanstd, np.nanvar} and c in 'FDG':
                        # Giving the warning is a small bug, see gh-8000
                        sup.filter(ComplexWarning)
                    tgt = rf(mat, dtype=np.dtype(c), axis=1).dtype.type
                    res = nf(mat, dtype=np.dtype(c), axis=1).dtype.type
                    assert_(res is tgt)
                    # scalar case
                    tgt = rf(mat, dtype=np.dtype(c), axis=None).dtype.type
                    res = nf(mat, dtype=np.dtype(c), axis=None).dtype.type
                    assert_(res is tgt)

    def test_dtype_from_char(self):
        mat = np.eye(3)
        codes = 'efdgFDG'
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            for c in codes:
                with suppress_warnings() as sup:
                    if nf in {np.nanstd, np.nanvar} and c in 'FDG':
                        # Giving the warning is a small bug, see gh-8000
                        sup.filter(ComplexWarning)
                    tgt = rf(mat, dtype=c, axis=1).dtype.type
                    res = nf(mat, dtype=c, axis=1).dtype.type
                    assert_(res is tgt)
                    # scalar case
                    tgt = rf(mat, dtype=c, axis=None).dtype.type
                    res = nf(mat, dtype=c, axis=None).dtype.type
                    assert_(res is tgt)

    def test_dtype_from_input(self):
        codes = 'efdgFDG'
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            for c in codes:
                mat = np.eye(3, dtype=c)
                tgt = rf(mat, axis=1).dtype.type
                res = nf(mat, axis=1).dtype.type
                assert_(res is tgt, f"res {res}, tgt {tgt}")
                # scalar case
                tgt = rf(mat, axis=None).dtype.type
                res = nf(mat, axis=None).dtype.type
                assert_(res is tgt)

    def test_result_values(self):
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            tgt = [rf(d) for d in _rdat]
            res = nf(_ndat, axis=1)
            assert_almost_equal(res, tgt)

    def test_scalar(self):
        for f in self.nanfuncs:
            assert_(f(0.) == 0.)

    def test_subclass(self):
        class MyNDArray(np.ndarray):
            pass

        # Check that it works and that type and
        # shape are preserved
        array = np.eye(3)
        mine = array.view(MyNDArray)
        for f in self.nanfuncs:
            expected_shape = f(array, axis=0).shape
            res = f(mine, axis=0)
            assert_(isinstance(res, MyNDArray))
            assert_(res.shape == expected_shape)
            expected_shape = f(array, axis=1).shape
            res = f(mine, axis=1)
            assert_(isinstance(res, MyNDArray))
            assert_(res.shape == expected_shape)
            expected_shape = f(array).shape
            res = f(mine)
            assert_(isinstance(res, MyNDArray))
            assert_(res.shape == expected_shape)


class TestNanFunctions_SumProd(SharedNanFunctionsTestsMixin):

    nanfuncs = [np.nansum, np.nanprod]
    stdfuncs = [np.sum, np.prod]

    @pytest.mark.parametrize("axis", [None, 0, 1])
    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    @pytest.mark.parametrize("array", [
        np.array(np.nan),
        np.full((3, 3), np.nan),
    ], ids=["0d", "2d"])
    def test_allnans(self, axis, dtype, array):
        if axis is not None and array.ndim == 0:
            pytest.skip("`axis != None` not supported for 0d arrays")

        array = array.astype(dtype)
        for func, identity in zip(self.nanfuncs, [0, 1]):
            out = func(array, axis=axis)
            assert np.all(out == identity)
            assert out.dtype == array.dtype

    def test_empty(self):
        for f, tgt_value in zip([np.nansum, np.nanprod], [0, 1]):
            mat = np.zeros((0, 3))
            tgt = [tgt_value] * 3
            res = f(mat, axis=0)
            assert_equal(res, tgt)
            tgt = []
            res = f(mat, axis=1)
            assert_equal(res, tgt)
            tgt = tgt_value
            res = f(mat, axis=None)
            assert_equal(res, tgt)

    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    def test_initial(self, dtype):
        ar = np.arange(9).astype(dtype)
        ar[:5] = np.nan

        for f in self.nanfuncs:
            reference = 28 if f is np.nansum else 3360
            ret = f(ar, initial=2)
            assert ret.dtype == dtype
            assert ret == reference

    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    def test_where(self, dtype):
        ar = np.arange(9).reshape(3, 3).astype(dtype)
        ar[0, :] = np.nan
        where = np.ones_like(ar, dtype=np.bool)
        where[:, 0] = False

        for f in self.nanfuncs:
            reference = 26 if f is np.nansum else 2240
            ret = f(ar, where=where, initial=2)
            assert ret.dtype == dtype
            assert ret == reference


class TestNanFunctions_CumSumProd(SharedNanFunctionsTestsMixin):

    nanfuncs = [np.nancumsum, np.nancumprod]
    stdfuncs = [np.cumsum, np.cumprod]

    @pytest.mark.parametrize("axis", [None, 0, 1])
    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    @pytest.mark.parametrize("array", [
        np.array(np.nan),
        np.full((3, 3), np.nan)
    ], ids=["0d", "2d"])
    def test_allnans(self, axis, dtype, array):
        if axis is not None and array.ndim == 0:
            pytest.skip("`axis != None` not supported for 0d arrays")

        array = array.astype(dtype)
        for func, identity in zip(self.nanfuncs, [0, 1]):
            out = func(array)
            assert np.all(out == identity)
            assert out.dtype == array.dtype

    def test_empty(self):
        for f, tgt_value in zip(self.nanfuncs, [0, 1]):
            mat = np.zeros((0, 3))
            tgt = tgt_value * np.ones((0, 3))
            res = f(mat, axis=0)
            assert_equal(res, tgt)
            tgt = mat
            res = f(mat, axis=1)
            assert_equal(res, tgt)
            tgt = np.zeros(0)
            res = f(mat, axis=None)
            assert_equal(res, tgt)

    def test_keepdims(self):
        for f, g in zip(self.nanfuncs, self.stdfuncs):
            mat = np.eye(3)
            for axis in [None, 0, 1]:
                tgt = f(mat, axis=axis, out=None)
                res = g(mat, axis=axis, out=None)
                assert_(res.ndim == tgt.ndim)

        for f in self.nanfuncs:
            d = np.ones((3, 5, 7, 11))
            # Randomly set some elements to NaN:
            rs = np.random.RandomState(0)
            d[rs.rand(*d.shape) < 0.5] = np.nan
            res = f(d, axis=None)
            assert_equal(res.shape, (1155,))
            for axis in np.arange(4):
                res = f(d, axis=axis)
                assert_equal(res.shape, (3, 5, 7, 11))

    def test_result_values(self):
        for axis in (-2, -1, 0, 1, None):
            tgt = np.cumprod(_ndat_ones, axis=axis)
            res = np.nancumprod(_ndat, axis=axis)
            assert_almost_equal(res, tgt)
            tgt = np.cumsum(_ndat_zeros, axis=axis)
            res = np.nancumsum(_ndat, axis=axis)
            assert_almost_equal(res, tgt)

    def test_out(self):
        mat = np.eye(3)
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            resout = np.eye(3)
            for axis in (-2, -1, 0, 1):
                tgt = rf(mat, axis=axis)
                res = nf(mat, axis=axis, out=resout)
                assert_almost_equal(res, resout)
                assert_almost_equal(res, tgt)


class TestNanFunctions_MeanVarStd(SharedNanFunctionsTestsMixin):

    nanfuncs = [np.nanmean, np.nanvar, np.nanstd]
    stdfuncs = [np.mean, np.var, np.std]

    def test_dtype_error(self):
        for f in self.nanfuncs:
            for dtype in [np.bool, np.int_, np.object_]:
                assert_raises(TypeError, f, _ndat, axis=1, dtype=dtype)

    def test_out_dtype_error(self):
        for f in self.nanfuncs:
            for dtype in [np.bool, np.int_, np.object_]:
                out = np.empty(_ndat.shape[0], dtype=dtype)
                assert_raises(TypeError, f, _ndat, axis=1, out=out)

    def test_ddof(self):
        nanfuncs = [np.nanvar, np.nanstd]
        stdfuncs = [np.var, np.std]
        for nf, rf in zip(nanfuncs, stdfuncs):
            for ddof in [0, 1]:
                tgt = [rf(d, ddof=ddof) for d in _rdat]
                res = nf(_ndat, axis=1, ddof=ddof)
                assert_almost_equal(res, tgt)

    def test_ddof_too_big(self):
        nanfuncs = [np.nanvar, np.nanstd]
        stdfuncs = [np.var, np.std]
        dsize = [len(d) for d in _rdat]
        for nf, rf in zip(nanfuncs, stdfuncs):
            for ddof in range(5):
                with suppress_warnings() as sup:
                    sup.record(RuntimeWarning)
                    sup.filter(ComplexWarning)
                    tgt = [ddof >= d for d in dsize]
                    res = nf(_ndat, axis=1, ddof=ddof)
                    assert_equal(np.isnan(res), tgt)
                    if any(tgt):
                        assert_(len(sup.log) == 1)
                    else:
                        assert_(len(sup.log) == 0)

    @pytest.mark.parametrize("axis", [None, 0, 1])
    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    @pytest.mark.parametrize("array", [
        np.array(np.nan),
        np.full((3, 3), np.nan),
    ], ids=["0d", "2d"])
    def test_allnans(self, axis, dtype, array):
        if axis is not None and array.ndim == 0:
            pytest.skip("`axis != None` not supported for 0d arrays")

        array = array.astype(dtype)
        match = "(Degrees of freedom <= 0 for slice.)|(Mean of empty slice)"
        for func in self.nanfuncs:
            with pytest.warns(RuntimeWarning, match=match):
                out = func(array, axis=axis)
            assert np.isnan(out).all()

            # `nanvar` and `nanstd` convert complex inputs to their
            # corresponding floating dtype
            if func is np.nanmean:
                assert out.dtype == array.dtype
            else:
                assert out.dtype == np.abs(array).dtype

    def test_empty(self):
        mat = np.zeros((0, 3))
        for f in self.nanfuncs:
            for axis in [0, None]:
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter('always')
                    assert_(np.isnan(f(mat, axis=axis)).all())
                    assert_(len(w) == 1)
                    assert_(issubclass(w[0].category, RuntimeWarning))
            for axis in [1]:
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter('always')
                    assert_equal(f(mat, axis=axis), np.zeros([]))
                    assert_(len(w) == 0)

    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    def test_where(self, dtype):
        ar = np.arange(9).reshape(3, 3).astype(dtype)
        ar[0, :] = np.nan
        where = np.ones_like(ar, dtype=np.bool)
        where[:, 0] = False

        for f, f_std in zip(self.nanfuncs, self.stdfuncs):
            reference = f_std(ar[where][2:])
            dtype_reference = dtype if f is np.nanmean else ar.real.dtype

            ret = f(ar, where=where)
            assert ret.dtype == dtype_reference
            np.testing.assert_allclose(ret, reference)

    def test_nanstd_with_mean_keyword(self):
        # Setting the seed to make the test reproducible
        rng = np.random.RandomState(1234)
        A = rng.randn(10, 20, 5) + 0.5
        A[:, 5, :] = np.nan

        mean_out = np.zeros((10, 1, 5))
        std_out = np.zeros((10, 1, 5))

        mean = np.nanmean(A,
                       out=mean_out,
                       axis=1,
                       keepdims=True)

        # The returned  object should be the object specified during calling
        assert mean_out is mean

        std = np.nanstd(A,
                     out=std_out,
                     axis=1,
                     keepdims=True,
                     mean=mean)

        # The returned  object should be the object specified during calling
        assert std_out is std

        # Shape of returned mean and std should be same
        assert std.shape == mean.shape
        assert std.shape == (10, 1, 5)

        # Output should be the same as from the individual algorithms
        std_old = np.nanstd(A, axis=1, keepdims=True)

        assert std_old.shape == mean.shape
        assert_almost_equal(std, std_old)


_TIME_UNITS = (
    "Y", "M", "W", "D", "h", "m", "s", "ms", "us", "ns", "ps", "fs", "as"
)

# All `inexact` + `timdelta64` type codes
_TYPE_CODES = list(np.typecodes["AllFloat"])
_TYPE_CODES += [f"m8[{unit}]" for unit in _TIME_UNITS]


class TestNanFunctions_Median:

    def test_mutation(self):
        # Check that passed array is not modified.
        ndat = _ndat.copy()
        np.nanmedian(ndat)
        assert_equal(ndat, _ndat)

    def test_keepdims(self):
        mat = np.eye(3)
        for axis in [None, 0, 1]:
            tgt = np.median(mat, axis=axis, out=None, overwrite_input=False)
            res = np.nanmedian(mat, axis=axis, out=None, overwrite_input=False)
            assert_(res.ndim == tgt.ndim)

        d = np.ones((3, 5, 7, 11))
        # Randomly set some elements to NaN:
        w = np.random.random((4, 200)) * np.array(d.shape)[:, None]
        w = w.astype(np.intp)
        d[tuple(w)] = np.nan
        with suppress_warnings() as sup:
            sup.filter(RuntimeWarning)
            res = np.nanmedian(d, axis=None, keepdims=True)
            assert_equal(res.shape, (1, 1, 1, 1))
            res = np.nanmedian(d, axis=(0, 1), keepdims=True)
            assert_equal(res.shape, (1, 1, 7, 11))
            res = np.nanmedian(d, axis=(0, 3), keepdims=True)
            assert_equal(res.shape, (1, 5, 7, 1))
            res = np.nanmedian(d, axis=(1,), keepdims=True)
            assert_equal(res.shape, (3, 1, 7, 11))
            res = np.nanmedian(d, axis=(0, 1, 2, 3), keepdims=True)
            assert_equal(res.shape, (1, 1, 1, 1))
            res = np.nanmedian(d, axis=(0, 1, 3), keepdims=True)
            assert_equal(res.shape, (1, 1, 7, 1))

    @pytest.mark.parametrize(
        argnames='axis',
        argvalues=[
            None,
            1,
            (1, ),
            (0, 1),
            (-3, -1),
        ]
    )
    @pytest.mark.filterwarnings("ignore:All-NaN slice:RuntimeWarning")
    def test_keepdims_out(self, axis):
        d = np.ones((3, 5, 7, 11))
        # Randomly set some elements to NaN:
        w = np.random.random((4, 200)) * np.array(d.shape)[:, None]
        w = w.astype(np.intp)
        d[tuple(w)] = np.nan
        if axis is None:
            shape_out = (1,) * d.ndim
        else:
            axis_norm = normalize_axis_tuple(axis, d.ndim)
            shape_out = tuple(
                1 if i in axis_norm else d.shape[i] for i in range(d.ndim))
        out = np.empty(shape_out)
        result = np.nanmedian(d, axis=axis, keepdims=True, out=out)
        assert result is out
        assert_equal(result.shape, shape_out)

    def test_out(self):
        mat = np.random.rand(3, 3)
        nan_mat = np.insert(mat, [0, 2], np.nan, axis=1)
        resout = np.zeros(3)
        tgt = np.median(mat, axis=1)
        res = np.nanmedian(nan_mat, axis=1, out=resout)
        assert_almost_equal(res, resout)
        assert_almost_equal(res, tgt)
        # 0-d output:
        resout = np.zeros(())
        tgt = np.median(mat, axis=None)
        res = np.nanmedian(nan_mat, axis=None, out=resout)
        assert_almost_equal(res, resout)
        assert_almost_equal(res, tgt)
        res = np.nanmedian(nan_mat, axis=(0, 1), out=resout)
        assert_almost_equal(res, resout)
        assert_almost_equal(res, tgt)

    def test_small_large(self):
        # test the small and large code paths, current cutoff 400 elements
        for s in [5, 20, 51, 200, 1000]:
            d = np.random.randn(4, s)
            # Randomly set some elements to NaN:
            w = np.random.randint(0, d.size, size=d.size // 5)
            d.ravel()[w] = np.nan
            d[:, 0] = 1.  # ensure at least one good value
            # use normal median without nans to compare
            tgt = []
            for x in d:
                nonan = np.compress(~np.isnan(x), x)
                tgt.append(np.median(nonan, overwrite_input=True))

            assert_array_equal(np.nanmedian(d, axis=-1), tgt)

    def test_result_values(self):
        tgt = [np.median(d) for d in _rdat]
        res = np.nanmedian(_ndat, axis=1)
        assert_almost_equal(res, tgt)

    @pytest.mark.parametrize("axis", [None, 0, 1])
    @pytest.mark.parametrize("dtype", _TYPE_CODES)
    def test_allnans(self, dtype, axis):
        mat = np.full((3, 3), np.nan).astype(dtype)
        with suppress_warnings() as sup:
            sup.record(RuntimeWarning)

            output = np.nanmedian(mat, axis=axis)
            assert output.dtype == mat.dtype
            assert np.isnan(output).all()

            if axis is None:
                assert_(len(sup.log) == 1)
            else:
                assert_(len(sup.log) == 3)

            # Check scalar
            scalar = np.array(np.nan).astype(dtype)[()]
            output_scalar = np.nanmedian(scalar)
            assert output_scalar.dtype == scalar.dtype
            assert np.isnan(output_scalar)

            if axis is None:
                assert_(len(sup.log) == 2)
            else:
                assert_(len(sup.log) == 4)

    def test_empty(self):
        mat = np.zeros((0, 3))
        for axis in [0, None]:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                assert_(np.isnan(np.nanmedian(mat, axis=axis)).all())
                assert_(len(w) == 1)
                assert_(issubclass(w[0].category, RuntimeWarning))
        for axis in [1]:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                assert_equal(np.nanmedian(mat, axis=axis), np.zeros([]))
                assert_(len(w) == 0)

    def test_scalar(self):
        assert_(np.nanmedian(0.) == 0.)

    def test_extended_axis_invalid(self):
        d = np.ones((3, 5, 7, 11))
        assert_raises(AxisError, np.nanmedian, d, axis=-5)
        assert_raises(AxisError, np.nanmedian, d, axis=(0, -5))
        assert_raises(AxisError, np.nanmedian, d, axis=4)
        assert_raises(AxisError, np.nanmedian, d, axis=(0, 4))
        assert_raises(ValueError, np.nanmedian, d, axis=(1, 1))

    def test_float_special(self):
        with suppress_warnings() as sup:
            sup.filter(RuntimeWarning)
            for inf in [np.inf, -np.inf]:
                a = np.array([[inf,  np.nan], [np.nan, np.nan]])
                assert_equal(np.nanmedian(a, axis=0), [inf,  np.nan])
                assert_equal(np.nanmedian(a, axis=1), [inf,  np.nan])
                assert_equal(np.nanmedian(a), inf)

                # minimum fill value check
                a = np.array([[np.nan, np.nan, inf],
                             [np.nan, np.nan, inf]])
                assert_equal(np.nanmedian(a), inf)
                assert_equal(np.nanmedian(a, axis=0), [np.nan, np.nan, inf])
                assert_equal(np.nanmedian(a, axis=1), inf)

                # no mask path
                a = np.array([[inf, inf], [inf, inf]])
                assert_equal(np.nanmedian(a, axis=1), inf)

                a = np.array([[inf, 7, -inf, -9],
                              [-10, np.nan, np.nan, 5],
                              [4, np.nan, np.nan, inf]],
                              dtype=np.float32)
                if inf > 0:
                    assert_equal(np.nanmedian(a, axis=0), [4., 7., -inf, 5.])
                    assert_equal(np.nanmedian(a), 4.5)
                else:
                    assert_equal(np.nanmedian(a, axis=0), [-10., 7., -inf, -9.])
                    assert_equal(np.nanmedian(a), -2.5)
                assert_equal(np.nanmedian(a, axis=-1), [-1., -2.5, inf])

                for i in range(10):
                    for j in range(1, 10):
                        a = np.array([([np.nan] * i) + ([inf] * j)] * 2)
                        assert_equal(np.nanmedian(a), inf)
                        assert_equal(np.nanmedian(a, axis=1), inf)
                        assert_equal(np.nanmedian(a, axis=0),
                                     ([np.nan] * i) + [inf] * j)

                        a = np.array([([np.nan] * i) + ([-inf] * j)] * 2)
                        assert_equal(np.nanmedian(a), -inf)
                        assert_equal(np.nanmedian(a, axis=1), -inf)
                        assert_equal(np.nanmedian(a, axis=0),
                                     ([np.nan] * i) + [-inf] * j)


class TestNanFunctions_Percentile:

    def test_mutation(self):
        # Check that passed array is not modified.
        ndat = _ndat.copy()
        np.nanpercentile(ndat, 30)
        assert_equal(ndat, _ndat)

    def test_keepdims(self):
        mat = np.eye(3)
        for axis in [None, 0, 1]:
            tgt = np.percentile(mat, 70, axis=axis, out=None,
                                overwrite_input=False)
            res = np.nanpercentile(mat, 70, axis=axis, out=None,
                                   overwrite_input=False)
            assert_(res.ndim == tgt.ndim)

        d = np.ones((3, 5, 7, 11))
        # Randomly set some elements to NaN:
        w = np.random.random((4, 200)) * np.array(d.shape)[:, None]
        w = w.astype(np.intp)
        d[tuple(w)] = np.nan
        with suppress_warnings() as sup:
            sup.filter(RuntimeWarning)
            res = np.nanpercentile(d, 90, axis=None, keepdims=True)
            assert_equal(res.shape, (1, 1, 1, 1))
            res = np.nanpercentile(d, 90, axis=(0, 1), keepdims=True)
            assert_equal(res.shape, (1, 1, 7, 11))
            res = np.nanpercentile(d, 90, axis=(0, 3), keepdims=True)
            assert_equal(res.shape, (1, 5, 7, 1))
            res = np.nanpercentile(d, 90, axis=(1,), keepdims=True)
            assert_equal(res.shape, (3, 1, 7, 11))
            res = np.nanpercentile(d, 90, axis=(0, 1, 2, 3), keepdims=True)
            assert_equal(res.shape, (1, 1, 1, 1))
            res = np.nanpercentile(d, 90, axis=(0, 1, 3), keepdims=True)
            assert_equal(res.shape, (1, 1, 7, 1))

    @pytest.mark.parametrize('q', [7, [1, 7]])
    @pytest.mark.parametrize(
        argnames='axis',
        argvalues=[
            None,
            1,
            (1,),
            (0, 1),
            (-3, -1),
        ]
    )
    @pytest.mark.filterwarnings("ignore:All-NaN slice:RuntimeWarning")
    def test_keepdims_out(self, q, axis):
        d = np.ones((3, 5, 7, 11))
        # Randomly set some elements to NaN:
        w = np.random.random((4, 200)) * np.array(d.shape)[:, None]
        w = w.astype(np.intp)
        d[tuple(w)] = np.nan
        if axis is None:
            shape_out = (1,) * d.ndim
        else:
            axis_norm = normalize_axis_tuple(axis, d.ndim)
            shape_out = tuple(
                1 if i in axis_norm else d.shape[i] for i in range(d.ndim))
        shape_out = np.shape(q) + shape_out

        out = np.empty(shape_out)
        result = np.nanpercentile(d, q, axis=axis, keepdims=True, out=out)
        assert result is out
        assert_equal(result.shape, shape_out)

    @pytest.mark.parametrize("weighted", [False, True])
    def test_out(self, weighted):
        mat = np.random.rand(3, 3)
        nan_mat = np.insert(mat, [0, 2], np.nan, axis=1)
        resout = np.zeros(3)
        if weighted:
            w_args = {"weights": np.ones_like(mat), "method": "inverted_cdf"}
            nan_w_args = {
                "weights": np.ones_like(nan_mat), "method": "inverted_cdf"
            }
        else:
            w_args = {}
            nan_w_args = {}
        tgt = np.percentile(mat, 42, axis=1, **w_args)
        res = np.nanpercentile(nan_mat, 42, axis=1, out=resout, **nan_w_args)
        assert_almost_equal(res, resout)
        assert_almost_equal(res, tgt)
        # 0-d output:
        resout = np.zeros(())
        tgt = np.percentile(mat, 42, axis=None, **w_args)
        res = np.nanpercentile(
            nan_mat, 42, axis=None, out=resout, **nan_w_args
        )
        assert_almost_equal(res, resout)
        assert_almost_equal(res, tgt)
        res = np.nanpercentile(
            nan_mat, 42, axis=(0, 1), out=resout, **nan_w_args
        )
        assert_almost_equal(res, resout)
        assert_almost_equal(res, tgt)

    def test_complex(self):
        arr_c = np.array([0.5 + 3.0j, 2.1 + 0.5j, 1.6 + 2.3j], dtype='G')
        assert_raises(TypeError, np.nanpercentile, arr_c, 0.5)
        arr_c = np.array([0.5 + 3.0j, 2.1 + 0.5j, 1.6 + 2.3j], dtype='D')
        assert_raises(TypeError, np.nanpercentile, arr_c, 0.5)
        arr_c = np.array([0.5 + 3.0j, 2.1 + 0.5j, 1.6 + 2.3j], dtype='F')
        assert_raises(TypeError, np.nanpercentile, arr_c, 0.5)

    @pytest.mark.parametrize("weighted", [False, True])
    @pytest.mark.parametrize("use_out", [False, True])
    def test_result_values(self, weighted, use_out):
        if weighted:
            percentile = partial(np.percentile, method="inverted_cdf")
            nanpercentile = partial(np.nanpercentile, method="inverted_cdf")

            def gen_weights(d):
                return np.ones_like(d)

        else:
            percentile = np.percentile
            nanpercentile = np.nanpercentile

            def gen_weights(d):
                return None

        tgt = [percentile(d, 28, weights=gen_weights(d)) for d in _rdat]
        out = np.empty_like(tgt) if use_out else None
        res = nanpercentile(_ndat, 28, axis=1,
                            weights=gen_weights(_ndat), out=out)
        assert_almost_equal(res, tgt)
        # Transpose the array to fit the output convention of numpy.percentile
        tgt = np.transpose([percentile(d, (28, 98), weights=gen_weights(d))
                            for d in _rdat])
        out = np.empty_like(tgt) if use_out else None
        res = nanpercentile(_ndat, (28, 98), axis=1,
                            weights=gen_weights(_ndat), out=out)
        assert_almost_equal(res, tgt)

    @pytest.mark.parametrize("axis", [None, 0, 1])
    @pytest.mark.parametrize("dtype", np.typecodes["Float"])
    @pytest.mark.parametrize("array", [
        np.array(np.nan),
        np.full((3, 3), np.nan),
    ], ids=["0d", "2d"])
    def test_allnans(self, axis, dtype, array):
        if axis is not None and array.ndim == 0:
            pytest.skip("`axis != None` not supported for 0d arrays")

        array = array.astype(dtype)
        with pytest.warns(RuntimeWarning, match="All-NaN slice encountered"):
            out = np.nanpercentile(array, 60, axis=axis)
        assert np.isnan(out).all()
        assert out.dtype == array.dtype

    def test_empty(self):
        mat = np.zeros((0, 3))
        for axis in [0, None]:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                assert_(np.isnan(np.nanpercentile(mat, 40, axis=axis)).all())
                assert_(len(w) == 1)
                assert_(issubclass(w[0].category, RuntimeWarning))
        for axis in [1]:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                assert_equal(np.nanpercentile(mat, 40, axis=axis), np.zeros([]))
                assert_(len(w) == 0)

    def test_scalar(self):
        assert_equal(np.nanpercentile(0., 100), 0.)
        a = np.arange(6)
        r = np.nanpercentile(a, 50, axis=0)
        assert_equal(r, 2.5)
        assert_(np.isscalar(r))

    def test_extended_axis_invalid(self):
        d = np.ones((3, 5, 7, 11))
        assert_raises(AxisError, np.nanpercentile, d, q=5, axis=-5)
        assert_raises(AxisError, np.nanpercentile, d, q=5, axis=(0, -5))
        assert_raises(AxisError, np.nanpercentile, d, q=5, axis=4)
        assert_raises(AxisError, np.nanpercentile, d, q=5, axis=(0, 4))
        assert_raises(ValueError, np.nanpercentile, d, q=5, axis=(1, 1))

    def test_multiple_percentiles(self):
        perc = [50, 100]
        mat = np.ones((4, 3))
        nan_mat = np.nan * mat
        # For checking consistency in higher dimensional case
        large_mat = np.ones((3, 4, 5))
        large_mat[:, 0:2:4, :] = 0
        large_mat[:, :, 3:] *= 2
        for axis in [None, 0, 1]:
            for keepdim in [False, True]:
                with suppress_warnings() as sup:
                    sup.filter(RuntimeWarning, "All-NaN slice encountered")
                    val = np.percentile(mat, perc, axis=axis, keepdims=keepdim)
                    nan_val = np.nanpercentile(nan_mat, perc, axis=axis,
                                               keepdims=keepdim)
                    assert_equal(nan_val.shape, val.shape)

                    val = np.percentile(large_mat, perc, axis=axis,
                                        keepdims=keepdim)
                    nan_val = np.nanpercentile(large_mat, perc, axis=axis,
                                               keepdims=keepdim)
                    assert_equal(nan_val, val)

        megamat = np.ones((3, 4, 5, 6))
        assert_equal(
            np.nanpercentile(megamat, perc, axis=(1, 2)).shape, (2, 3, 6)
        )

    @pytest.mark.parametrize("nan_weight", [0, 1, 2, 3, 1e200])
    def test_nan_value_with_weight(self, nan_weight):
        x = [1, np.nan, 2, 3]
        result = np.float64(2.0)
        q_unweighted = np.nanpercentile(x, 50, method="inverted_cdf")
        assert_equal(q_unweighted, result)

        # The weight value at the nan position should not matter.
        w = [1.0, nan_weight, 1.0, 1.0]
        q_weighted = np.nanpercentile(x, 50, weights=w, method="inverted_cdf")
        assert_equal(q_weighted, result)

    @pytest.mark.parametrize("axis", [0, 1, 2])
    def test_nan_value_with_weight_ndim(self, axis):
        # Create a multi-dimensional array to test
        np.random.seed(1)
        x_no_nan = np.random.random(size=(100, 99, 2))
        # Set some places to NaN (not particularly smart) so there is always
        # some non-Nan.
        x = x_no_nan.copy()
        x[np.arange(99), np.arange(99), 0] = np.nan

        p = np.array([[20., 50., 30], [70, 33, 80]])

        # We just use ones as weights, but replace it with 0 or 1e200 at the
        # NaN positions below.
        weights = np.ones_like(x)

        # For comparison use weighted normal percentile with nan weights at
        # 0 (and no NaNs); not sure this is strictly identical but should be
        # sufficiently so (if a percentile lies exactly on a 0 value).
        weights[np.isnan(x)] = 0
        p_expected = np.percentile(
            x_no_nan, p, axis=axis, weights=weights, method="inverted_cdf")

        p_unweighted = np.nanpercentile(
            x, p, axis=axis, method="inverted_cdf")
        # The normal and unweighted versions should be identical:
        assert_equal(p_unweighted, p_expected)

        weights[np.isnan(x)] = 1e200  # huge value, shouldn't matter
        p_weighted = np.nanpercentile(
            x, p, axis=axis, weights=weights, method="inverted_cdf")
        assert_equal(p_weighted, p_expected)
        # Also check with out passed:
        out = np.empty_like(p_weighted)
        res = np.nanpercentile(
            x, p, axis=axis, weights=weights, out=out, method="inverted_cdf")

        assert res is out
        assert_equal(out, p_expected)


class TestNanFunctions_Quantile:
    # most of this is already tested by TestPercentile

    @pytest.mark.parametrize("weighted", [False, True])
    def test_regression(self, weighted):
        ar = np.arange(24).reshape(2, 3, 4).astype(float)
        ar[0][1] = np.nan
        if weighted:
            w_args = {"weights": np.ones_like(ar), "method": "inverted_cdf"}
        else:
            w_args = {}

        assert_equal(np.nanquantile(ar, q=0.5, **w_args),
                     np.nanpercentile(ar, q=50, **w_args))
        assert_equal(np.nanquantile(ar, q=0.5, axis=0, **w_args),
                     np.nanpercentile(ar, q=50, axis=0, **w_args))
        assert_equal(np.nanquantile(ar, q=0.5, axis=1, **w_args),
                     np.nanpercentile(ar, q=50, axis=1, **w_args))
        assert_equal(np.nanquantile(ar, q=[0.5], axis=1, **w_args),
                     np.nanpercentile(ar, q=[50], axis=1, **w_args))
        assert_equal(np.nanquantile(ar, q=[0.25, 0.5, 0.75], axis=1, **w_args),
                     np.nanpercentile(ar, q=[25, 50, 75], axis=1, **w_args))

    def test_basic(self):
        x = np.arange(8) * 0.5
        assert_equal(np.nanquantile(x, 0), 0.)
        assert_equal(np.nanquantile(x, 1), 3.5)
        assert_equal(np.nanquantile(x, 0.5), 1.75)

    def test_complex(self):
        arr_c = np.array([0.5 + 3.0j, 2.1 + 0.5j, 1.6 + 2.3j], dtype='G')
        assert_raises(TypeError, np.nanquantile, arr_c, 0.5)
        arr_c = np.array([0.5 + 3.0j, 2.1 + 0.5j, 1.6 + 2.3j], dtype='D')
        assert_raises(TypeError, np.nanquantile, arr_c, 0.5)
        arr_c = np.array([0.5 + 3.0j, 2.1 + 0.5j, 1.6 + 2.3j], dtype='F')
        assert_raises(TypeError, np.nanquantile, arr_c, 0.5)

    def test_no_p_overwrite(self):
        # this is worth retesting, because quantile does not make a copy
        p0 = np.array([0, 0.75, 0.25, 0.5, 1.0])
        p = p0.copy()
        np.nanquantile(np.arange(100.), p, method="midpoint")
        assert_array_equal(p, p0)

        p0 = p0.tolist()
        p = p.tolist()
        np.nanquantile(np.arange(100.), p, method="midpoint")
        assert_array_equal(p, p0)

    @pytest.mark.parametrize("axis", [None, 0, 1])
    @pytest.mark.parametrize("dtype", np.typecodes["Float"])
    @pytest.mark.parametrize("array", [
        np.array(np.nan),
        np.full((3, 3), np.nan),
    ], ids=["0d", "2d"])
    def test_allnans(self, axis, dtype, array):
        if axis is not None and array.ndim == 0:
            pytest.skip("`axis != None` not supported for 0d arrays")

        array = array.astype(dtype)
        with pytest.warns(RuntimeWarning, match="All-NaN slice encountered"):
            out = np.nanquantile(array, 1, axis=axis)
        assert np.isnan(out).all()
        assert out.dtype == array.dtype

@pytest.mark.parametrize("arr, expected", [
    # array of floats with some nans
    (np.array([np.nan, 5.0, np.nan, np.inf]),
     np.array([False, True, False, True])),
    # int64 array that can't possibly have nans
    (np.array([1, 5, 7, 9], dtype=np.int64),
     True),
    # bool array that can't possibly have nans
    (np.array([False, True, False, True]),
     True),
    # 2-D complex array with nans
    (np.array([[np.nan, 5.0],
               [np.nan, np.inf]], dtype=np.complex64),
     np.array([[False, True],
               [False, True]])),
    ])
def test__nan_mask(arr, expected):
    for out in [None, np.empty(arr.shape, dtype=np.bool)]:
        actual = _nan_mask(arr, out=out)
        assert_equal(actual, expected)
        # the above won't distinguish between True proper
        # and an array of True values; we want True proper
        # for types that can't possibly contain NaN
        if type(expected) is not np.ndarray:
            assert actual is True


def test__replace_nan():
    """ Test that _replace_nan returns the original array if there are no
    NaNs, not a copy.
    """
    for dtype in [np.bool, np.int32, np.int64]:
        arr = np.array([0, 1], dtype=dtype)
        result, mask = _replace_nan(arr, 0)
        assert mask is None
        # do not make a copy if there are no nans
        assert result is arr

    for dtype in [np.float32, np.float64]:
        arr = np.array([0, 1], dtype=dtype)
        result, mask = _replace_nan(arr, 2)
        assert (mask == False).all()
        # mask is not None, so we make a copy
        assert result is not arr
        assert_equal(result, arr)

        arr_nan = np.array([0, 1, np.nan], dtype=dtype)
        result_nan, mask_nan = _replace_nan(arr_nan, 2)
        assert_equal(mask_nan, np.array([False, False, True]))
        assert result_nan is not arr_nan
        assert_equal(result_nan, np.array([0, 1, 2]))
        assert np.isnan(arr_nan[-1])


def test_memmap_takes_fast_route(tmpdir):
    # We want memory mapped arrays to take the fast route through nanmax,
    # which avoids creating a mask by using fmax.reduce (see gh-28721). So we
    # check that on bad input, the error is from fmax (rather than maximum).
    a = np.arange(10., dtype=float)
    with open(tmpdir.join("data.bin"), "w+b") as fh:
        fh.write(a.tobytes())
        mm = np.memmap(fh, dtype=a.dtype, shape=a.shape)
        with pytest.raises(ValueError, match="reduction operation fmax"):
            np.nanmax(mm, out=np.zeros(2))
        # For completeness, same for nanmin.
        with pytest.raises(ValueError, match="reduction operation fmin"):
            np.nanmin(mm, out=np.zeros(2))

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\tests\test_nanfunctions.py ===
import inspect
import warnings
from functools import partial

import pytest

import numpy as np
from numpy._core.numeric import normalize_axis_tuple
from numpy.exceptions import AxisError, ComplexWarning
from numpy.lib._nanfunctions_impl import _nan_mask, _replace_nan
from numpy.testing import (
    assert_,
    assert_almost_equal,
    assert_array_equal,
    assert_equal,
    assert_raises,
    assert_raises_regex,
    suppress_warnings,
)

# Test data
_ndat = np.array([[0.6244, np.nan, 0.2692, 0.0116, np.nan, 0.1170],
                  [0.5351, -0.9403, np.nan, 0.2100, 0.4759, 0.2833],
                  [np.nan, np.nan, np.nan, 0.1042, np.nan, -0.5954],
                  [0.1610, np.nan, np.nan, 0.1859, 0.3146, np.nan]])


# Rows of _ndat with nans removed
_rdat = [np.array([0.6244, 0.2692, 0.0116, 0.1170]),
         np.array([0.5351, -0.9403, 0.2100, 0.4759, 0.2833]),
         np.array([0.1042, -0.5954]),
         np.array([0.1610, 0.1859, 0.3146])]

# Rows of _ndat with nans converted to ones
_ndat_ones = np.array([[0.6244, 1.0, 0.2692, 0.0116, 1.0, 0.1170],
                       [0.5351, -0.9403, 1.0, 0.2100, 0.4759, 0.2833],
                       [1.0, 1.0, 1.0, 0.1042, 1.0, -0.5954],
                       [0.1610, 1.0, 1.0, 0.1859, 0.3146, 1.0]])

# Rows of _ndat with nans converted to zeros
_ndat_zeros = np.array([[0.6244, 0.0, 0.2692, 0.0116, 0.0, 0.1170],
                        [0.5351, -0.9403, 0.0, 0.2100, 0.4759, 0.2833],
                        [0.0, 0.0, 0.0, 0.1042, 0.0, -0.5954],
                        [0.1610, 0.0, 0.0, 0.1859, 0.3146, 0.0]])


class TestSignatureMatch:
    NANFUNCS = {
        np.nanmin: np.amin,
        np.nanmax: np.amax,
        np.nanargmin: np.argmin,
        np.nanargmax: np.argmax,
        np.nansum: np.sum,
        np.nanprod: np.prod,
        np.nancumsum: np.cumsum,
        np.nancumprod: np.cumprod,
        np.nanmean: np.mean,
        np.nanmedian: np.median,
        np.nanpercentile: np.percentile,
        np.nanquantile: np.quantile,
        np.nanvar: np.var,
        np.nanstd: np.std,
    }
    IDS = [k.__name__ for k in NANFUNCS]

    @staticmethod
    def get_signature(func, default="..."):
        """Construct a signature and replace all default parameter-values."""
        prm_list = []
        signature = inspect.signature(func)
        for prm in signature.parameters.values():
            if prm.default is inspect.Parameter.empty:
                prm_list.append(prm)
            else:
                prm_list.append(prm.replace(default=default))
        return inspect.Signature(prm_list)

    @pytest.mark.parametrize("nan_func,func", NANFUNCS.items(), ids=IDS)
    def test_signature_match(self, nan_func, func):
        # Ignore the default parameter-values as they can sometimes differ
        # between the two functions (*e.g.* one has `False` while the other
        # has `np._NoValue`)
        signature = self.get_signature(func)
        nan_signature = self.get_signature(nan_func)
        np.testing.assert_equal(signature, nan_signature)

    def test_exhaustiveness(self):
        """Validate that all nan functions are actually tested."""
        np.testing.assert_equal(
            set(self.IDS), set(np.lib._nanfunctions_impl.__all__)
        )


class TestNanFunctions_MinMax:

    nanfuncs = [np.nanmin, np.nanmax]
    stdfuncs = [np.min, np.max]

    def test_mutation(self):
        # Check that passed array is not modified.
        ndat = _ndat.copy()
        for f in self.nanfuncs:
            f(ndat)
            assert_equal(ndat, _ndat)

    def test_keepdims(self):
        mat = np.eye(3)
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            for axis in [None, 0, 1]:
                tgt = rf(mat, axis=axis, keepdims=True)
                res = nf(mat, axis=axis, keepdims=True)
                assert_(res.ndim == tgt.ndim)

    def test_out(self):
        mat = np.eye(3)
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            resout = np.zeros(3)
            tgt = rf(mat, axis=1)
            res = nf(mat, axis=1, out=resout)
            assert_almost_equal(res, resout)
            assert_almost_equal(res, tgt)

    def test_dtype_from_input(self):
        codes = 'efdgFDG'
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            for c in codes:
                mat = np.eye(3, dtype=c)
                tgt = rf(mat, axis=1).dtype.type
                res = nf(mat, axis=1).dtype.type
                assert_(res is tgt)
                # scalar case
                tgt = rf(mat, axis=None).dtype.type
                res = nf(mat, axis=None).dtype.type
                assert_(res is tgt)

    def test_result_values(self):
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            tgt = [rf(d) for d in _rdat]
            res = nf(_ndat, axis=1)
            assert_almost_equal(res, tgt)

    @pytest.mark.parametrize("axis", [None, 0, 1])
    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    @pytest.mark.parametrize("array", [
        np.array(np.nan),
        np.full((3, 3), np.nan),
    ], ids=["0d", "2d"])
    def test_allnans(self, axis, dtype, array):
        if axis is not None and array.ndim == 0:
            pytest.skip("`axis != None` not supported for 0d arrays")

        array = array.astype(dtype)
        match = "All-NaN slice encountered"
        for func in self.nanfuncs:
            with pytest.warns(RuntimeWarning, match=match):
                out = func(array, axis=axis)
            assert np.isnan(out).all()
            assert out.dtype == array.dtype

    def test_masked(self):
        mat = np.ma.fix_invalid(_ndat)
        msk = mat._mask.copy()
        for f in [np.nanmin]:
            res = f(mat, axis=1)
            tgt = f(_ndat, axis=1)
            assert_equal(res, tgt)
            assert_equal(mat._mask, msk)
            assert_(not np.isinf(mat).any())

    def test_scalar(self):
        for f in self.nanfuncs:
            assert_(f(0.) == 0.)

    def test_subclass(self):
        class MyNDArray(np.ndarray):
            pass

        # Check that it works and that type and
        # shape are preserved
        mine = np.eye(3).view(MyNDArray)
        for f in self.nanfuncs:
            res = f(mine, axis=0)
            assert_(isinstance(res, MyNDArray))
            assert_(res.shape == (3,))
            res = f(mine, axis=1)
            assert_(isinstance(res, MyNDArray))
            assert_(res.shape == (3,))
            res = f(mine)
            assert_(res.shape == ())

        # check that rows of nan are dealt with for subclasses (#4628)
        mine[1] = np.nan
        for f in self.nanfuncs:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                res = f(mine, axis=0)
                assert_(isinstance(res, MyNDArray))
                assert_(not np.any(np.isnan(res)))
                assert_(len(w) == 0)

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                res = f(mine, axis=1)
                assert_(isinstance(res, MyNDArray))
                assert_(np.isnan(res[1]) and not np.isnan(res[0])
                        and not np.isnan(res[2]))
                assert_(len(w) == 1, 'no warning raised')
                assert_(issubclass(w[0].category, RuntimeWarning))

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                res = f(mine)
                assert_(res.shape == ())
                assert_(res != np.nan)
                assert_(len(w) == 0)

    def test_object_array(self):
        arr = np.array([[1.0, 2.0], [np.nan, 4.0], [np.nan, np.nan]], dtype=object)
        assert_equal(np.nanmin(arr), 1.0)
        assert_equal(np.nanmin(arr, axis=0), [1.0, 2.0])

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            # assert_equal does not work on object arrays of nan
            assert_equal(list(np.nanmin(arr, axis=1)), [1.0, 4.0, np.nan])
            assert_(len(w) == 1, 'no warning raised')
            assert_(issubclass(w[0].category, RuntimeWarning))

    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    def test_initial(self, dtype):
        class MyNDArray(np.ndarray):
            pass

        ar = np.arange(9).astype(dtype)
        ar[:5] = np.nan

        for f in self.nanfuncs:
            initial = 100 if f is np.nanmax else 0

            ret1 = f(ar, initial=initial)
            assert ret1.dtype == dtype
            assert ret1 == initial

            ret2 = f(ar.view(MyNDArray), initial=initial)
            assert ret2.dtype == dtype
            assert ret2 == initial

    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    def test_where(self, dtype):
        class MyNDArray(np.ndarray):
            pass

        ar = np.arange(9).reshape(3, 3).astype(dtype)
        ar[0, :] = np.nan
        where = np.ones_like(ar, dtype=np.bool)
        where[:, 0] = False

        for f in self.nanfuncs:
            reference = 4 if f is np.nanmin else 8

            ret1 = f(ar, where=where, initial=5)
            assert ret1.dtype == dtype
            assert ret1 == reference

            ret2 = f(ar.view(MyNDArray), where=where, initial=5)
            assert ret2.dtype == dtype
            assert ret2 == reference


class TestNanFunctions_ArgminArgmax:

    nanfuncs = [np.nanargmin, np.nanargmax]

    def test_mutation(self):
        # Check that passed array is not modified.
        ndat = _ndat.copy()
        for f in self.nanfuncs:
            f(ndat)
            assert_equal(ndat, _ndat)

    def test_result_values(self):
        for f, fcmp in zip(self.nanfuncs, [np.greater, np.less]):
            for row in _ndat:
                with suppress_warnings() as sup:
                    sup.filter(RuntimeWarning, "invalid value encountered in")
                    ind = f(row)
                    val = row[ind]
                    # comparing with NaN is tricky as the result
                    # is always false except for NaN != NaN
                    assert_(not np.isnan(val))
                    assert_(not fcmp(val, row).any())
                    assert_(not np.equal(val, row[:ind]).any())

    @pytest.mark.parametrize("axis", [None, 0, 1])
    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    @pytest.mark.parametrize("array", [
        np.array(np.nan),
        np.full((3, 3), np.nan),
    ], ids=["0d", "2d"])
    def test_allnans(self, axis, dtype, array):
        if axis is not None and array.ndim == 0:
            pytest.skip("`axis != None` not supported for 0d arrays")

        array = array.astype(dtype)
        for func in self.nanfuncs:
            with pytest.raises(ValueError, match="All-NaN slice encountered"):
                func(array, axis=axis)

    def test_empty(self):
        mat = np.zeros((0, 3))
        for f in self.nanfuncs:
            for axis in [0, None]:
                assert_raises_regex(
                        ValueError,
                        "attempt to get argm.. of an empty sequence",
                        f, mat, axis=axis)
            for axis in [1]:
                res = f(mat, axis=axis)
                assert_equal(res, np.zeros(0))

    def test_scalar(self):
        for f in self.nanfuncs:
            assert_(f(0.) == 0.)

    def test_subclass(self):
        class MyNDArray(np.ndarray):
            pass

        # Check that it works and that type and
        # shape are preserved
        mine = np.eye(3).view(MyNDArray)
        for f in self.nanfuncs:
            res = f(mine, axis=0)
            assert_(isinstance(res, MyNDArray))
            assert_(res.shape == (3,))
            res = f(mine, axis=1)
            assert_(isinstance(res, MyNDArray))
            assert_(res.shape == (3,))
            res = f(mine)
            assert_(res.shape == ())

    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    def test_keepdims(self, dtype):
        ar = np.arange(9).astype(dtype)
        ar[:5] = np.nan

        for f in self.nanfuncs:
            reference = 5 if f is np.nanargmin else 8
            ret = f(ar, keepdims=True)
            assert ret.ndim == ar.ndim
            assert ret == reference

    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    def test_out(self, dtype):
        ar = np.arange(9).astype(dtype)
        ar[:5] = np.nan

        for f in self.nanfuncs:
            out = np.zeros((), dtype=np.intp)
            reference = 5 if f is np.nanargmin else 8
            ret = f(ar, out=out)
            assert ret is out
            assert ret == reference


_TEST_ARRAYS = {
    "0d": np.array(5),
    "1d": np.array([127, 39, 93, 87, 46])
}
for _v in _TEST_ARRAYS.values():
    _v.setflags(write=False)


@pytest.mark.parametrize(
    "dtype",
    np.typecodes["AllInteger"] + np.typecodes["AllFloat"] + "O",
)
@pytest.mark.parametrize("mat", _TEST_ARRAYS.values(), ids=_TEST_ARRAYS.keys())
class TestNanFunctions_NumberTypes:
    nanfuncs = {
        np.nanmin: np.min,
        np.nanmax: np.max,
        np.nanargmin: np.argmin,
        np.nanargmax: np.argmax,
        np.nansum: np.sum,
        np.nanprod: np.prod,
        np.nancumsum: np.cumsum,
        np.nancumprod: np.cumprod,
        np.nanmean: np.mean,
        np.nanmedian: np.median,
        np.nanvar: np.var,
        np.nanstd: np.std,
    }
    nanfunc_ids = [i.__name__ for i in nanfuncs]

    @pytest.mark.parametrize("nanfunc,func", nanfuncs.items(), ids=nanfunc_ids)
    @np.errstate(over="ignore")
    def test_nanfunc(self, mat, dtype, nanfunc, func):
        mat = mat.astype(dtype)
        tgt = func(mat)
        out = nanfunc(mat)

        assert_almost_equal(out, tgt)
        if dtype == "O":
            assert type(out) is type(tgt)
        else:
            assert out.dtype == tgt.dtype

    @pytest.mark.parametrize(
        "nanfunc,func",
        [(np.nanquantile, np.quantile), (np.nanpercentile, np.percentile)],
        ids=["nanquantile", "nanpercentile"],
    )
    def test_nanfunc_q(self, mat, dtype, nanfunc, func):
        mat = mat.astype(dtype)
        if mat.dtype.kind == "c":
            assert_raises(TypeError, func, mat, q=1)
            assert_raises(TypeError, nanfunc, mat, q=1)

        else:
            tgt = func(mat, q=1)
            out = nanfunc(mat, q=1)

            assert_almost_equal(out, tgt)

            if dtype == "O":
                assert type(out) is type(tgt)
            else:
                assert out.dtype == tgt.dtype

    @pytest.mark.parametrize(
        "nanfunc,func",
        [(np.nanvar, np.var), (np.nanstd, np.std)],
        ids=["nanvar", "nanstd"],
    )
    def test_nanfunc_ddof(self, mat, dtype, nanfunc, func):
        mat = mat.astype(dtype)
        tgt = func(mat, ddof=0.5)
        out = nanfunc(mat, ddof=0.5)

        assert_almost_equal(out, tgt)
        if dtype == "O":
            assert type(out) is type(tgt)
        else:
            assert out.dtype == tgt.dtype

    @pytest.mark.parametrize(
        "nanfunc", [np.nanvar, np.nanstd]
    )
    def test_nanfunc_correction(self, mat, dtype, nanfunc):
        mat = mat.astype(dtype)
        assert_almost_equal(
            nanfunc(mat, correction=0.5), nanfunc(mat, ddof=0.5)
        )

        err_msg = "ddof and correction can't be provided simultaneously."
        with assert_raises_regex(ValueError, err_msg):
            nanfunc(mat, ddof=0.5, correction=0.5)

        with assert_raises_regex(ValueError, err_msg):
            nanfunc(mat, ddof=1, correction=0)


class SharedNanFunctionsTestsMixin:
    def test_mutation(self):
        # Check that passed array is not modified.
        ndat = _ndat.copy()
        for f in self.nanfuncs:
            f(ndat)
            assert_equal(ndat, _ndat)

    def test_keepdims(self):
        mat = np.eye(3)
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            for axis in [None, 0, 1]:
                tgt = rf(mat, axis=axis, keepdims=True)
                res = nf(mat, axis=axis, keepdims=True)
                assert_(res.ndim == tgt.ndim)

    def test_out(self):
        mat = np.eye(3)
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            resout = np.zeros(3)
            tgt = rf(mat, axis=1)
            res = nf(mat, axis=1, out=resout)
            assert_almost_equal(res, resout)
            assert_almost_equal(res, tgt)

    def test_dtype_from_dtype(self):
        mat = np.eye(3)
        codes = 'efdgFDG'
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            for c in codes:
                with suppress_warnings() as sup:
                    if nf in {np.nanstd, np.nanvar} and c in 'FDG':
                        # Giving the warning is a small bug, see gh-8000
                        sup.filter(ComplexWarning)
                    tgt = rf(mat, dtype=np.dtype(c), axis=1).dtype.type
                    res = nf(mat, dtype=np.dtype(c), axis=1).dtype.type
                    assert_(res is tgt)
                    # scalar case
                    tgt = rf(mat, dtype=np.dtype(c), axis=None).dtype.type
                    res = nf(mat, dtype=np.dtype(c), axis=None).dtype.type
                    assert_(res is tgt)

    def test_dtype_from_char(self):
        mat = np.eye(3)
        codes = 'efdgFDG'
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            for c in codes:
                with suppress_warnings() as sup:
                    if nf in {np.nanstd, np.nanvar} and c in 'FDG':
                        # Giving the warning is a small bug, see gh-8000
                        sup.filter(ComplexWarning)
                    tgt = rf(mat, dtype=c, axis=1).dtype.type
                    res = nf(mat, dtype=c, axis=1).dtype.type
                    assert_(res is tgt)
                    # scalar case
                    tgt = rf(mat, dtype=c, axis=None).dtype.type
                    res = nf(mat, dtype=c, axis=None).dtype.type
                    assert_(res is tgt)

    def test_dtype_from_input(self):
        codes = 'efdgFDG'
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            for c in codes:
                mat = np.eye(3, dtype=c)
                tgt = rf(mat, axis=1).dtype.type
                res = nf(mat, axis=1).dtype.type
                assert_(res is tgt, f"res {res}, tgt {tgt}")
                # scalar case
                tgt = rf(mat, axis=None).dtype.type
                res = nf(mat, axis=None).dtype.type
                assert_(res is tgt)

    def test_result_values(self):
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            tgt = [rf(d) for d in _rdat]
            res = nf(_ndat, axis=1)
            assert_almost_equal(res, tgt)

    def test_scalar(self):
        for f in self.nanfuncs:
            assert_(f(0.) == 0.)

    def test_subclass(self):
        class MyNDArray(np.ndarray):
            pass

        # Check that it works and that type and
        # shape are preserved
        array = np.eye(3)
        mine = array.view(MyNDArray)
        for f in self.nanfuncs:
            expected_shape = f(array, axis=0).shape
            res = f(mine, axis=0)
            assert_(isinstance(res, MyNDArray))
            assert_(res.shape == expected_shape)
            expected_shape = f(array, axis=1).shape
            res = f(mine, axis=1)
            assert_(isinstance(res, MyNDArray))
            assert_(res.shape == expected_shape)
            expected_shape = f(array).shape
            res = f(mine)
            assert_(isinstance(res, MyNDArray))
            assert_(res.shape == expected_shape)


class TestNanFunctions_SumProd(SharedNanFunctionsTestsMixin):

    nanfuncs = [np.nansum, np.nanprod]
    stdfuncs = [np.sum, np.prod]

    @pytest.mark.parametrize("axis", [None, 0, 1])
    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    @pytest.mark.parametrize("array", [
        np.array(np.nan),
        np.full((3, 3), np.nan),
    ], ids=["0d", "2d"])
    def test_allnans(self, axis, dtype, array):
        if axis is not None and array.ndim == 0:
            pytest.skip("`axis != None` not supported for 0d arrays")

        array = array.astype(dtype)
        for func, identity in zip(self.nanfuncs, [0, 1]):
            out = func(array, axis=axis)
            assert np.all(out == identity)
            assert out.dtype == array.dtype

    def test_empty(self):
        for f, tgt_value in zip([np.nansum, np.nanprod], [0, 1]):
            mat = np.zeros((0, 3))
            tgt = [tgt_value] * 3
            res = f(mat, axis=0)
            assert_equal(res, tgt)
            tgt = []
            res = f(mat, axis=1)
            assert_equal(res, tgt)
            tgt = tgt_value
            res = f(mat, axis=None)
            assert_equal(res, tgt)

    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    def test_initial(self, dtype):
        ar = np.arange(9).astype(dtype)
        ar[:5] = np.nan

        for f in self.nanfuncs:
            reference = 28 if f is np.nansum else 3360
            ret = f(ar, initial=2)
            assert ret.dtype == dtype
            assert ret == reference

    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    def test_where(self, dtype):
        ar = np.arange(9).reshape(3, 3).astype(dtype)
        ar[0, :] = np.nan
        where = np.ones_like(ar, dtype=np.bool)
        where[:, 0] = False

        for f in self.nanfuncs:
            reference = 26 if f is np.nansum else 2240
            ret = f(ar, where=where, initial=2)
            assert ret.dtype == dtype
            assert ret == reference


class TestNanFunctions_CumSumProd(SharedNanFunctionsTestsMixin):

    nanfuncs = [np.nancumsum, np.nancumprod]
    stdfuncs = [np.cumsum, np.cumprod]

    @pytest.mark.parametrize("axis", [None, 0, 1])
    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    @pytest.mark.parametrize("array", [
        np.array(np.nan),
        np.full((3, 3), np.nan)
    ], ids=["0d", "2d"])
    def test_allnans(self, axis, dtype, array):
        if axis is not None and array.ndim == 0:
            pytest.skip("`axis != None` not supported for 0d arrays")

        array = array.astype(dtype)
        for func, identity in zip(self.nanfuncs, [0, 1]):
            out = func(array)
            assert np.all(out == identity)
            assert out.dtype == array.dtype

    def test_empty(self):
        for f, tgt_value in zip(self.nanfuncs, [0, 1]):
            mat = np.zeros((0, 3))
            tgt = tgt_value * np.ones((0, 3))
            res = f(mat, axis=0)
            assert_equal(res, tgt)
            tgt = mat
            res = f(mat, axis=1)
            assert_equal(res, tgt)
            tgt = np.zeros(0)
            res = f(mat, axis=None)
            assert_equal(res, tgt)

    def test_keepdims(self):
        for f, g in zip(self.nanfuncs, self.stdfuncs):
            mat = np.eye(3)
            for axis in [None, 0, 1]:
                tgt = f(mat, axis=axis, out=None)
                res = g(mat, axis=axis, out=None)
                assert_(res.ndim == tgt.ndim)

        for f in self.nanfuncs:
            d = np.ones((3, 5, 7, 11))
            # Randomly set some elements to NaN:
            rs = np.random.RandomState(0)
            d[rs.rand(*d.shape) < 0.5] = np.nan
            res = f(d, axis=None)
            assert_equal(res.shape, (1155,))
            for axis in np.arange(4):
                res = f(d, axis=axis)
                assert_equal(res.shape, (3, 5, 7, 11))

    def test_result_values(self):
        for axis in (-2, -1, 0, 1, None):
            tgt = np.cumprod(_ndat_ones, axis=axis)
            res = np.nancumprod(_ndat, axis=axis)
            assert_almost_equal(res, tgt)
            tgt = np.cumsum(_ndat_zeros, axis=axis)
            res = np.nancumsum(_ndat, axis=axis)
            assert_almost_equal(res, tgt)

    def test_out(self):
        mat = np.eye(3)
        for nf, rf in zip(self.nanfuncs, self.stdfuncs):
            resout = np.eye(3)
            for axis in (-2, -1, 0, 1):
                tgt = rf(mat, axis=axis)
                res = nf(mat, axis=axis, out=resout)
                assert_almost_equal(res, resout)
                assert_almost_equal(res, tgt)


class TestNanFunctions_MeanVarStd(SharedNanFunctionsTestsMixin):

    nanfuncs = [np.nanmean, np.nanvar, np.nanstd]
    stdfuncs = [np.mean, np.var, np.std]

    def test_dtype_error(self):
        for f in self.nanfuncs:
            for dtype in [np.bool, np.int_, np.object_]:
                assert_raises(TypeError, f, _ndat, axis=1, dtype=dtype)

    def test_out_dtype_error(self):
        for f in self.nanfuncs:
            for dtype in [np.bool, np.int_, np.object_]:
                out = np.empty(_ndat.shape[0], dtype=dtype)
                assert_raises(TypeError, f, _ndat, axis=1, out=out)

    def test_ddof(self):
        nanfuncs = [np.nanvar, np.nanstd]
        stdfuncs = [np.var, np.std]
        for nf, rf in zip(nanfuncs, stdfuncs):
            for ddof in [0, 1]:
                tgt = [rf(d, ddof=ddof) for d in _rdat]
                res = nf(_ndat, axis=1, ddof=ddof)
                assert_almost_equal(res, tgt)

    def test_ddof_too_big(self):
        nanfuncs = [np.nanvar, np.nanstd]
        stdfuncs = [np.var, np.std]
        dsize = [len(d) for d in _rdat]
        for nf, rf in zip(nanfuncs, stdfuncs):
            for ddof in range(5):
                with suppress_warnings() as sup:
                    sup.record(RuntimeWarning)
                    sup.filter(ComplexWarning)
                    tgt = [ddof >= d for d in dsize]
                    res = nf(_ndat, axis=1, ddof=ddof)
                    assert_equal(np.isnan(res), tgt)
                    if any(tgt):
                        assert_(len(sup.log) == 1)
                    else:
                        assert_(len(sup.log) == 0)

    @pytest.mark.parametrize("axis", [None, 0, 1])
    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    @pytest.mark.parametrize("array", [
        np.array(np.nan),
        np.full((3, 3), np.nan),
    ], ids=["0d", "2d"])
    def test_allnans(self, axis, dtype, array):
        if axis is not None and array.ndim == 0:
            pytest.skip("`axis != None` not supported for 0d arrays")

        array = array.astype(dtype)
        match = "(Degrees of freedom <= 0 for slice.)|(Mean of empty slice)"
        for func in self.nanfuncs:
            with pytest.warns(RuntimeWarning, match=match):
                out = func(array, axis=axis)
            assert np.isnan(out).all()

            # `nanvar` and `nanstd` convert complex inputs to their
            # corresponding floating dtype
            if func is np.nanmean:
                assert out.dtype == array.dtype
            else:
                assert out.dtype == np.abs(array).dtype

    def test_empty(self):
        mat = np.zeros((0, 3))
        for f in self.nanfuncs:
            for axis in [0, None]:
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter('always')
                    assert_(np.isnan(f(mat, axis=axis)).all())
                    assert_(len(w) == 1)
                    assert_(issubclass(w[0].category, RuntimeWarning))
            for axis in [1]:
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter('always')
                    assert_equal(f(mat, axis=axis), np.zeros([]))
                    assert_(len(w) == 0)

    @pytest.mark.parametrize("dtype", np.typecodes["AllFloat"])
    def test_where(self, dtype):
        ar = np.arange(9).reshape(3, 3).astype(dtype)
        ar[0, :] = np.nan
        where = np.ones_like(ar, dtype=np.bool)
        where[:, 0] = False

        for f, f_std in zip(self.nanfuncs, self.stdfuncs):
            reference = f_std(ar[where][2:])
            dtype_reference = dtype if f is np.nanmean else ar.real.dtype

            ret = f(ar, where=where)
            assert ret.dtype == dtype_reference
            np.testing.assert_allclose(ret, reference)

    def test_nanstd_with_mean_keyword(self):
        # Setting the seed to make the test reproducible
        rng = np.random.RandomState(1234)
        A = rng.randn(10, 20, 5) + 0.5
        A[:, 5, :] = np.nan

        mean_out = np.zeros((10, 1, 5))
        std_out = np.zeros((10, 1, 5))

        mean = np.nanmean(A,
                       out=mean_out,
                       axis=1,
                       keepdims=True)

        # The returned  object should be the object specified during calling
        assert mean_out is mean

        std = np.nanstd(A,
                     out=std_out,
                     axis=1,
                     keepdims=True,
                     mean=mean)

        # The returned  object should be the object specified during calling
        assert std_out is std

        # Shape of returned mean and std should be same
        assert std.shape == mean.shape
        assert std.shape == (10, 1, 5)

        # Output should be the same as from the individual algorithms
        std_old = np.nanstd(A, axis=1, keepdims=True)

        assert std_old.shape == mean.shape
        assert_almost_equal(std, std_old)


_TIME_UNITS = (
    "Y", "M", "W", "D", "h", "m", "s", "ms", "us", "ns", "ps", "fs", "as"
)

# All `inexact` + `timdelta64` type codes
_TYPE_CODES = list(np.typecodes["AllFloat"])
_TYPE_CODES += [f"m8[{unit}]" for unit in _TIME_UNITS]


class TestNanFunctions_Median:

    def test_mutation(self):
        # Check that passed array is not modified.
        ndat = _ndat.copy()
        np.nanmedian(ndat)
        assert_equal(ndat, _ndat)

    def test_keepdims(self):
        mat = np.eye(3)
        for axis in [None, 0, 1]:
            tgt = np.median(mat, axis=axis, out=None, overwrite_input=False)
            res = np.nanmedian(mat, axis=axis, out=None, overwrite_input=False)
            assert_(res.ndim == tgt.ndim)

        d = np.ones((3, 5, 7, 11))
        # Randomly set some elements to NaN:
        w = np.random.random((4, 200)) * np.array(d.shape)[:, None]
        w = w.astype(np.intp)
        d[tuple(w)] = np.nan
        with suppress_warnings() as sup:
            sup.filter(RuntimeWarning)
            res = np.nanmedian(d, axis=None, keepdims=True)
            assert_equal(res.shape, (1, 1, 1, 1))
            res = np.nanmedian(d, axis=(0, 1), keepdims=True)
            assert_equal(res.shape, (1, 1, 7, 11))
            res = np.nanmedian(d, axis=(0, 3), keepdims=True)
            assert_equal(res.shape, (1, 5, 7, 1))
            res = np.nanmedian(d, axis=(1,), keepdims=True)
            assert_equal(res.shape, (3, 1, 7, 11))
            res = np.nanmedian(d, axis=(0, 1, 2, 3), keepdims=True)
            assert_equal(res.shape, (1, 1, 1, 1))
            res = np.nanmedian(d, axis=(0, 1, 3), keepdims=True)
            assert_equal(res.shape, (1, 1, 7, 1))

    @pytest.mark.parametrize(
        argnames='axis',
        argvalues=[
            None,
            1,
            (1, ),
            (0, 1),
            (-3, -1),
        ]
    )
    @pytest.mark.filterwarnings("ignore:All-NaN slice:RuntimeWarning")
    def test_keepdims_out(self, axis):
        d = np.ones((3, 5, 7, 11))
        # Randomly set some elements to NaN:
        w = np.random.random((4, 200)) * np.array(d.shape)[:, None]
        w = w.astype(np.intp)
        d[tuple(w)] = np.nan
        if axis is None:
            shape_out = (1,) * d.ndim
        else:
            axis_norm = normalize_axis_tuple(axis, d.ndim)
            shape_out = tuple(
                1 if i in axis_norm else d.shape[i] for i in range(d.ndim))
        out = np.empty(shape_out)
        result = np.nanmedian(d, axis=axis, keepdims=True, out=out)
        assert result is out
        assert_equal(result.shape, shape_out)

    def test_out(self):
        mat = np.random.rand(3, 3)
        nan_mat = np.insert(mat, [0, 2], np.nan, axis=1)
        resout = np.zeros(3)
        tgt = np.median(mat, axis=1)
        res = np.nanmedian(nan_mat, axis=1, out=resout)
        assert_almost_equal(res, resout)
        assert_almost_equal(res, tgt)
        # 0-d output:
        resout = np.zeros(())
        tgt = np.median(mat, axis=None)
        res = np.nanmedian(nan_mat, axis=None, out=resout)
        assert_almost_equal(res, resout)
        assert_almost_equal(res, tgt)
        res = np.nanmedian(nan_mat, axis=(0, 1), out=resout)
        assert_almost_equal(res, resout)
        assert_almost_equal(res, tgt)

    def test_small_large(self):
        # test the small and large code paths, current cutoff 400 elements
        for s in [5, 20, 51, 200, 1000]:
            d = np.random.randn(4, s)
            # Randomly set some elements to NaN:
            w = np.random.randint(0, d.size, size=d.size // 5)
            d.ravel()[w] = np.nan
            d[:, 0] = 1.  # ensure at least one good value
            # use normal median without nans to compare
            tgt = []
            for x in d:
                nonan = np.compress(~np.isnan(x), x)
                tgt.append(np.median(nonan, overwrite_input=True))

            assert_array_equal(np.nanmedian(d, axis=-1), tgt)

    def test_result_values(self):
        tgt = [np.median(d) for d in _rdat]
        res = np.nanmedian(_ndat, axis=1)
        assert_almost_equal(res, tgt)

    @pytest.mark.parametrize("axis", [None, 0, 1])
    @pytest.mark.parametrize("dtype", _TYPE_CODES)
    def test_allnans(self, dtype, axis):
        mat = np.full((3, 3), np.nan).astype(dtype)
        with suppress_warnings() as sup:
            sup.record(RuntimeWarning)

            output = np.nanmedian(mat, axis=axis)
            assert output.dtype == mat.dtype
            assert np.isnan(output).all()

            if axis is None:
                assert_(len(sup.log) == 1)
            else:
                assert_(len(sup.log) == 3)

            # Check scalar
            scalar = np.array(np.nan).astype(dtype)[()]
            output_scalar = np.nanmedian(scalar)
            assert output_scalar.dtype == scalar.dtype
            assert np.isnan(output_scalar)

            if axis is None:
                assert_(len(sup.log) == 2)
            else:
                assert_(len(sup.log) == 4)

    def test_empty(self):
        mat = np.zeros((0, 3))
        for axis in [0, None]:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                assert_(np.isnan(np.nanmedian(mat, axis=axis)).all())
                assert_(len(w) == 1)
                assert_(issubclass(w[0].category, RuntimeWarning))
        for axis in [1]:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                assert_equal(np.nanmedian(mat, axis=axis), np.zeros([]))
                assert_(len(w) == 0)

    def test_scalar(self):
        assert_(np.nanmedian(0.) == 0.)

    def test_extended_axis_invalid(self):
        d = np.ones((3, 5, 7, 11))
        assert_raises(AxisError, np.nanmedian, d, axis=-5)
        assert_raises(AxisError, np.nanmedian, d, axis=(0, -5))
        assert_raises(AxisError, np.nanmedian, d, axis=4)
        assert_raises(AxisError, np.nanmedian, d, axis=(0, 4))
        assert_raises(ValueError, np.nanmedian, d, axis=(1, 1))

    def test_float_special(self):
        with suppress_warnings() as sup:
            sup.filter(RuntimeWarning)
            for inf in [np.inf, -np.inf]:
                a = np.array([[inf,  np.nan], [np.nan, np.nan]])
                assert_equal(np.nanmedian(a, axis=0), [inf,  np.nan])
                assert_equal(np.nanmedian(a, axis=1), [inf,  np.nan])
                assert_equal(np.nanmedian(a), inf)

                # minimum fill value check
                a = np.array([[np.nan, np.nan, inf],
                             [np.nan, np.nan, inf]])
                assert_equal(np.nanmedian(a), inf)
                assert_equal(np.nanmedian(a, axis=0), [np.nan, np.nan, inf])
                assert_equal(np.nanmedian(a, axis=1), inf)

                # no mask path
                a = np.array([[inf, inf], [inf, inf]])
                assert_equal(np.nanmedian(a, axis=1), inf)

                a = np.array([[inf, 7, -inf, -9],
                              [-10, np.nan, np.nan, 5],
                              [4, np.nan, np.nan, inf]],
                              dtype=np.float32)
                if inf > 0:
                    assert_equal(np.nanmedian(a, axis=0), [4., 7., -inf, 5.])
                    assert_equal(np.nanmedian(a), 4.5)
                else:
                    assert_equal(np.nanmedian(a, axis=0), [-10., 7., -inf, -9.])
                    assert_equal(np.nanmedian(a), -2.5)
                assert_equal(np.nanmedian(a, axis=-1), [-1., -2.5, inf])

                for i in range(10):
                    for j in range(1, 10):
                        a = np.array([([np.nan] * i) + ([inf] * j)] * 2)
                        assert_equal(np.nanmedian(a), inf)
                        assert_equal(np.nanmedian(a, axis=1), inf)
                        assert_equal(np.nanmedian(a, axis=0),
                                     ([np.nan] * i) + [inf] * j)

                        a = np.array([([np.nan] * i) + ([-inf] * j)] * 2)
                        assert_equal(np.nanmedian(a), -inf)
                        assert_equal(np.nanmedian(a, axis=1), -inf)
                        assert_equal(np.nanmedian(a, axis=0),
                                     ([np.nan] * i) + [-inf] * j)


class TestNanFunctions_Percentile:

    def test_mutation(self):
        # Check that passed array is not modified.
        ndat = _ndat.copy()
        np.nanpercentile(ndat, 30)
        assert_equal(ndat, _ndat)

    def test_keepdims(self):
        mat = np.eye(3)
        for axis in [None, 0, 1]:
            tgt = np.percentile(mat, 70, axis=axis, out=None,
                                overwrite_input=False)
            res = np.nanpercentile(mat, 70, axis=axis, out=None,
                                   overwrite_input=False)
            assert_(res.ndim == tgt.ndim)

        d = np.ones((3, 5, 7, 11))
        # Randomly set some elements to NaN:
        w = np.random.random((4, 200)) * np.array(d.shape)[:, None]
        w = w.astype(np.intp)
        d[tuple(w)] = np.nan
        with suppress_warnings() as sup:
            sup.filter(RuntimeWarning)
            res = np.nanpercentile(d, 90, axis=None, keepdims=True)
            assert_equal(res.shape, (1, 1, 1, 1))
            res = np.nanpercentile(d, 90, axis=(0, 1), keepdims=True)
            assert_equal(res.shape, (1, 1, 7, 11))
            res = np.nanpercentile(d, 90, axis=(0, 3), keepdims=True)
            assert_equal(res.shape, (1, 5, 7, 1))
            res = np.nanpercentile(d, 90, axis=(1,), keepdims=True)
            assert_equal(res.shape, (3, 1, 7, 11))
            res = np.nanpercentile(d, 90, axis=(0, 1, 2, 3), keepdims=True)
            assert_equal(res.shape, (1, 1, 1, 1))
            res = np.nanpercentile(d, 90, axis=(0, 1, 3), keepdims=True)
            assert_equal(res.shape, (1, 1, 7, 1))

    @pytest.mark.parametrize('q', [7, [1, 7]])
    @pytest.mark.parametrize(
        argnames='axis',
        argvalues=[
            None,
            1,
            (1,),
            (0, 1),
            (-3, -1),
        ]
    )
    @pytest.mark.filterwarnings("ignore:All-NaN slice:RuntimeWarning")
    def test_keepdims_out(self, q, axis):
        d = np.ones((3, 5, 7, 11))
        # Randomly set some elements to NaN:
        w = np.random.random((4, 200)) * np.array(d.shape)[:, None]
        w = w.astype(np.intp)
        d[tuple(w)] = np.nan
        if axis is None:
            shape_out = (1,) * d.ndim
        else:
            axis_norm = normalize_axis_tuple(axis, d.ndim)
            shape_out = tuple(
                1 if i in axis_norm else d.shape[i] for i in range(d.ndim))
        shape_out = np.shape(q) + shape_out

        out = np.empty(shape_out)
        result = np.nanpercentile(d, q, axis=axis, keepdims=True, out=out)
        assert result is out
        assert_equal(result.shape, shape_out)

    @pytest.mark.parametrize("weighted", [False, True])
    def test_out(self, weighted):
        mat = np.random.rand(3, 3)
        nan_mat = np.insert(mat, [0, 2], np.nan, axis=1)
        resout = np.zeros(3)
        if weighted:
            w_args = {"weights": np.ones_like(mat), "method": "inverted_cdf"}
            nan_w_args = {
                "weights": np.ones_like(nan_mat), "method": "inverted_cdf"
            }
        else:
            w_args = {}
            nan_w_args = {}
        tgt = np.percentile(mat, 42, axis=1, **w_args)
        res = np.nanpercentile(nan_mat, 42, axis=1, out=resout, **nan_w_args)
        assert_almost_equal(res, resout)
        assert_almost_equal(res, tgt)
        # 0-d output:
        resout = np.zeros(())
        tgt = np.percentile(mat, 42, axis=None, **w_args)
        res = np.nanpercentile(
            nan_mat, 42, axis=None, out=resout, **nan_w_args
        )
        assert_almost_equal(res, resout)
        assert_almost_equal(res, tgt)
        res = np.nanpercentile(
            nan_mat, 42, axis=(0, 1), out=resout, **nan_w_args
        )
        assert_almost_equal(res, resout)
        assert_almost_equal(res, tgt)

    def test_complex(self):
        arr_c = np.array([0.5 + 3.0j, 2.1 + 0.5j, 1.6 + 2.3j], dtype='G')
        assert_raises(TypeError, np.nanpercentile, arr_c, 0.5)
        arr_c = np.array([0.5 + 3.0j, 2.1 + 0.5j, 1.6 + 2.3j], dtype='D')
        assert_raises(TypeError, np.nanpercentile, arr_c, 0.5)
        arr_c = np.array([0.5 + 3.0j, 2.1 + 0.5j, 1.6 + 2.3j], dtype='F')
        assert_raises(TypeError, np.nanpercentile, arr_c, 0.5)

    @pytest.mark.parametrize("weighted", [False, True])
    @pytest.mark.parametrize("use_out", [False, True])
    def test_result_values(self, weighted, use_out):
        if weighted:
            percentile = partial(np.percentile, method="inverted_cdf")
            nanpercentile = partial(np.nanpercentile, method="inverted_cdf")

            def gen_weights(d):
                return np.ones_like(d)

        else:
            percentile = np.percentile
            nanpercentile = np.nanpercentile

            def gen_weights(d):
                return None

        tgt = [percentile(d, 28, weights=gen_weights(d)) for d in _rdat]
        out = np.empty_like(tgt) if use_out else None
        res = nanpercentile(_ndat, 28, axis=1,
                            weights=gen_weights(_ndat), out=out)
        assert_almost_equal(res, tgt)
        # Transpose the array to fit the output convention of numpy.percentile
        tgt = np.transpose([percentile(d, (28, 98), weights=gen_weights(d))
                            for d in _rdat])
        out = np.empty_like(tgt) if use_out else None
        res = nanpercentile(_ndat, (28, 98), axis=1,
                            weights=gen_weights(_ndat), out=out)
        assert_almost_equal(res, tgt)

    @pytest.mark.parametrize("axis", [None, 0, 1])
    @pytest.mark.parametrize("dtype", np.typecodes["Float"])
    @pytest.mark.parametrize("array", [
        np.array(np.nan),
        np.full((3, 3), np.nan),
    ], ids=["0d", "2d"])
    def test_allnans(self, axis, dtype, array):
        if axis is not None and array.ndim == 0:
            pytest.skip("`axis != None` not supported for 0d arrays")

        array = array.astype(dtype)
        with pytest.warns(RuntimeWarning, match="All-NaN slice encountered"):
            out = np.nanpercentile(array, 60, axis=axis)
        assert np.isnan(out).all()
        assert out.dtype == array.dtype

    def test_empty(self):
        mat = np.zeros((0, 3))
        for axis in [0, None]:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                assert_(np.isnan(np.nanpercentile(mat, 40, axis=axis)).all())
                assert_(len(w) == 1)
                assert_(issubclass(w[0].category, RuntimeWarning))
        for axis in [1]:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                assert_equal(np.nanpercentile(mat, 40, axis=axis), np.zeros([]))
                assert_(len(w) == 0)

    def test_scalar(self):
        assert_equal(np.nanpercentile(0., 100), 0.)
        a = np.arange(6)
        r = np.nanpercentile(a, 50, axis=0)
        assert_equal(r, 2.5)
        assert_(np.isscalar(r))

    def test_extended_axis_invalid(self):
        d = np.ones((3, 5, 7, 11))
        assert_raises(AxisError, np.nanpercentile, d, q=5, axis=-5)
        assert_raises(AxisError, np.nanpercentile, d, q=5, axis=(0, -5))
        assert_raises(AxisError, np.nanpercentile, d, q=5, axis=4)
        assert_raises(AxisError, np.nanpercentile, d, q=5, axis=(0, 4))
        assert_raises(ValueError, np.nanpercentile, d, q=5, axis=(1, 1))

    def test_multiple_percentiles(self):
        perc = [50, 100]
        mat = np.ones((4, 3))
        nan_mat = np.nan * mat
        # For checking consistency in higher dimensional case
        large_mat = np.ones((3, 4, 5))
        large_mat[:, 0:2:4, :] = 0
        large_mat[:, :, 3:] *= 2
        for axis in [None, 0, 1]:
            for keepdim in [False, True]:
                with suppress_warnings() as sup:
                    sup.filter(RuntimeWarning, "All-NaN slice encountered")
                    val = np.percentile(mat, perc, axis=axis, keepdims=keepdim)
                    nan_val = np.nanpercentile(nan_mat, perc, axis=axis,
                                               keepdims=keepdim)
                    assert_equal(nan_val.shape, val.shape)

                    val = np.percentile(large_mat, perc, axis=axis,
                                        keepdims=keepdim)
                    nan_val = np.nanpercentile(large_mat, perc, axis=axis,
                                               keepdims=keepdim)
                    assert_equal(nan_val, val)

        megamat = np.ones((3, 4, 5, 6))
        assert_equal(
            np.nanpercentile(megamat, perc, axis=(1, 2)).shape, (2, 3, 6)
        )

    @pytest.mark.parametrize("nan_weight", [0, 1, 2, 3, 1e200])
    def test_nan_value_with_weight(self, nan_weight):
        x = [1, np.nan, 2, 3]
        result = np.float64(2.0)
        q_unweighted = np.nanpercentile(x, 50, method="inverted_cdf")
        assert_equal(q_unweighted, result)

        # The weight value at the nan position should not matter.
        w = [1.0, nan_weight, 1.0, 1.0]
        q_weighted = np.nanpercentile(x, 50, weights=w, method="inverted_cdf")
        assert_equal(q_weighted, result)

    @pytest.mark.parametrize("axis", [0, 1, 2])
    def test_nan_value_with_weight_ndim(self, axis):
        # Create a multi-dimensional array to test
        np.random.seed(1)
        x_no_nan = np.random.random(size=(100, 99, 2))
        # Set some places to NaN (not particularly smart) so there is always
        # some non-Nan.
        x = x_no_nan.copy()
        x[np.arange(99), np.arange(99), 0] = np.nan

        p = np.array([[20., 50., 30], [70, 33, 80]])

        # We just use ones as weights, but replace it with 0 or 1e200 at the
        # NaN positions below.
        weights = np.ones_like(x)

        # For comparison use weighted normal percentile with nan weights at
        # 0 (and no NaNs); not sure this is strictly identical but should be
        # sufficiently so (if a percentile lies exactly on a 0 value).
        weights[np.isnan(x)] = 0
        p_expected = np.percentile(
            x_no_nan, p, axis=axis, weights=weights, method="inverted_cdf")

        p_unweighted = np.nanpercentile(
            x, p, axis=axis, method="inverted_cdf")
        # The normal and unweighted versions should be identical:
        assert_equal(p_unweighted, p_expected)

        weights[np.isnan(x)] = 1e200  # huge value, shouldn't matter
        p_weighted = np.nanpercentile(
            x, p, axis=axis, weights=weights, method="inverted_cdf")
        assert_equal(p_weighted, p_expected)
        # Also check with out passed:
        out = np.empty_like(p_weighted)
        res = np.nanpercentile(
            x, p, axis=axis, weights=weights, out=out, method="inverted_cdf")

        assert res is out
        assert_equal(out, p_expected)


class TestNanFunctions_Quantile:
    # most of this is already tested by TestPercentile

    @pytest.mark.parametrize("weighted", [False, True])
    def test_regression(self, weighted):
        ar = np.arange(24).reshape(2, 3, 4).astype(float)
        ar[0][1] = np.nan
        if weighted:
            w_args = {"weights": np.ones_like(ar), "method": "inverted_cdf"}
        else:
            w_args = {}

        assert_equal(np.nanquantile(ar, q=0.5, **w_args),
                     np.nanpercentile(ar, q=50, **w_args))
        assert_equal(np.nanquantile(ar, q=0.5, axis=0, **w_args),
                     np.nanpercentile(ar, q=50, axis=0, **w_args))
        assert_equal(np.nanquantile(ar, q=0.5, axis=1, **w_args),
                     np.nanpercentile(ar, q=50, axis=1, **w_args))
        assert_equal(np.nanquantile(ar, q=[0.5], axis=1, **w_args),
                     np.nanpercentile(ar, q=[50], axis=1, **w_args))
        assert_equal(np.nanquantile(ar, q=[0.25, 0.5, 0.75], axis=1, **w_args),
                     np.nanpercentile(ar, q=[25, 50, 75], axis=1, **w_args))

    def test_basic(self):
        x = np.arange(8) * 0.5
        assert_equal(np.nanquantile(x, 0), 0.)
        assert_equal(np.nanquantile(x, 1), 3.5)
        assert_equal(np.nanquantile(x, 0.5), 1.75)

    def test_complex(self):
        arr_c = np.array([0.5 + 3.0j, 2.1 + 0.5j, 1.6 + 2.3j], dtype='G')
        assert_raises(TypeError, np.nanquantile, arr_c, 0.5)
        arr_c = np.array([0.5 + 3.0j, 2.1 + 0.5j, 1.6 + 2.3j], dtype='D')
        assert_raises(TypeError, np.nanquantile, arr_c, 0.5)
        arr_c = np.array([0.5 + 3.0j, 2.1 + 0.5j, 1.6 + 2.3j], dtype='F')
        assert_raises(TypeError, np.nanquantile, arr_c, 0.5)

    def test_no_p_overwrite(self):
        # this is worth retesting, because quantile does not make a copy
        p0 = np.array([0, 0.75, 0.25, 0.5, 1.0])
        p = p0.copy()
        np.nanquantile(np.arange(100.), p, method="midpoint")
        assert_array_equal(p, p0)

        p0 = p0.tolist()
        p = p.tolist()
        np.nanquantile(np.arange(100.), p, method="midpoint")
        assert_array_equal(p, p0)

    @pytest.mark.parametrize("axis", [None, 0, 1])
    @pytest.mark.parametrize("dtype", np.typecodes["Float"])
    @pytest.mark.parametrize("array", [
        np.array(np.nan),
        np.full((3, 3), np.nan),
    ], ids=["0d", "2d"])
    def test_allnans(self, axis, dtype, array):
        if axis is not None and array.ndim == 0:
            pytest.skip("`axis != None` not supported for 0d arrays")

        array = array.astype(dtype)
        with pytest.warns(RuntimeWarning, match="All-NaN slice encountered"):
            out = np.nanquantile(array, 1, axis=axis)
        assert np.isnan(out).all()
        assert out.dtype == array.dtype

@pytest.mark.parametrize("arr, expected", [
    # array of floats with some nans
    (np.array([np.nan, 5.0, np.nan, np.inf]),
     np.array([False, True, False, True])),
    # int64 array that can't possibly have nans
    (np.array([1, 5, 7, 9], dtype=np.int64),
     True),
    # bool array that can't possibly have nans
    (np.array([False, True, False, True]),
     True),
    # 2-D complex array with nans
    (np.array([[np.nan, 5.0],
               [np.nan, np.inf]], dtype=np.complex64),
     np.array([[False, True],
               [False, True]])),
    ])
def test__nan_mask(arr, expected):
    for out in [None, np.empty(arr.shape, dtype=np.bool)]:
        actual = _nan_mask(arr, out=out)
        assert_equal(actual, expected)
        # the above won't distinguish between True proper
        # and an array of True values; we want True proper
        # for types that can't possibly contain NaN
        if type(expected) is not np.ndarray:
            assert actual is True


def test__replace_nan():
    """ Test that _replace_nan returns the original array if there are no
    NaNs, not a copy.
    """
    for dtype in [np.bool, np.int32, np.int64]:
        arr = np.array([0, 1], dtype=dtype)
        result, mask = _replace_nan(arr, 0)
        assert mask is None
        # do not make a copy if there are no nans
        assert result is arr

    for dtype in [np.float32, np.float64]:
        arr = np.array([0, 1], dtype=dtype)
        result, mask = _replace_nan(arr, 2)
        assert (mask == False).all()
        # mask is not None, so we make a copy
        assert result is not arr
        assert_equal(result, arr)

        arr_nan = np.array([0, 1, np.nan], dtype=dtype)
        result_nan, mask_nan = _replace_nan(arr_nan, 2)
        assert_equal(mask_nan, np.array([False, False, True]))
        assert result_nan is not arr_nan
        assert_equal(result_nan, np.array([0, 1, 2]))
        assert np.isnan(arr_nan[-1])


def test_memmap_takes_fast_route(tmpdir):
    # We want memory mapped arrays to take the fast route through nanmax,
    # which avoids creating a mask by using fmax.reduce (see gh-28721). So we
    # check that on bad input, the error is from fmax (rather than maximum).
    a = np.arange(10., dtype=float)
    with open(tmpdir.join("data.bin"), "w+b") as fh:
        fh.write(a.tobytes())
        mm = np.memmap(fh, dtype=a.dtype, shape=a.shape)
        with pytest.raises(ValueError, match="reduction operation fmax"):
            np.nanmax(mm, out=np.zeros(2))
        # For completeness, same for nanmin.
        with pytest.raises(ValueError, match="reduction operation fmin"):
            np.nanmin(mm, out=np.zeros(2))

# === NexusCore/openenv\Lib\site-packages\numpy\lib\tests\test_arraypad.py ===
"""Tests for the array padding functions.

"""
import pytest

import numpy as np
from numpy.lib._arraypad_impl import _as_pairs
from numpy.testing import assert_allclose, assert_array_equal, assert_equal

_numeric_dtypes = (
    np._core.sctypes["uint"]
    + np._core.sctypes["int"]
    + np._core.sctypes["float"]
    + np._core.sctypes["complex"]
)
_all_modes = {
    'constant': {'constant_values': 0},
    'edge': {},
    'linear_ramp': {'end_values': 0},
    'maximum': {'stat_length': None},
    'mean': {'stat_length': None},
    'median': {'stat_length': None},
    'minimum': {'stat_length': None},
    'reflect': {'reflect_type': 'even'},
    'symmetric': {'reflect_type': 'even'},
    'wrap': {},
    'empty': {}
}


class TestAsPairs:
    def test_single_value(self):
        """Test casting for a single value."""
        expected = np.array([[3, 3]] * 10)
        for x in (3, [3], [[3]]):
            result = _as_pairs(x, 10)
            assert_equal(result, expected)
        # Test with dtype=object
        obj = object()
        assert_equal(
            _as_pairs(obj, 10),
            np.array([[obj, obj]] * 10)
        )

    def test_two_values(self):
        """Test proper casting for two different values."""
        # Broadcasting in the first dimension with numbers
        expected = np.array([[3, 4]] * 10)
        for x in ([3, 4], [[3, 4]]):
            result = _as_pairs(x, 10)
            assert_equal(result, expected)
        # and with dtype=object
        obj = object()
        assert_equal(
            _as_pairs(["a", obj], 10),
            np.array([["a", obj]] * 10)
        )

        # Broadcasting in the second / last dimension with numbers
        assert_equal(
            _as_pairs([[3], [4]], 2),
            np.array([[3, 3], [4, 4]])
        )
        # and with dtype=object
        assert_equal(
            _as_pairs([["a"], [obj]], 2),
            np.array([["a", "a"], [obj, obj]])
        )

    def test_with_none(self):
        expected = ((None, None), (None, None), (None, None))
        assert_equal(
            _as_pairs(None, 3, as_index=False),
            expected
        )
        assert_equal(
            _as_pairs(None, 3, as_index=True),
            expected
        )

    def test_pass_through(self):
        """Test if `x` already matching desired output are passed through."""
        expected = np.arange(12).reshape((6, 2))
        assert_equal(
            _as_pairs(expected, 6),
            expected
        )

    def test_as_index(self):
        """Test results if `as_index=True`."""
        assert_equal(
            _as_pairs([2.6, 3.3], 10, as_index=True),
            np.array([[3, 3]] * 10, dtype=np.intp)
        )
        assert_equal(
            _as_pairs([2.6, 4.49], 10, as_index=True),
            np.array([[3, 4]] * 10, dtype=np.intp)
        )
        for x in (-3, [-3], [[-3]], [-3, 4], [3, -4], [[-3, 4]], [[4, -3]],
                  [[1, 2]] * 9 + [[1, -2]]):
            with pytest.raises(ValueError, match="negative values"):
                _as_pairs(x, 10, as_index=True)

    def test_exceptions(self):
        """Ensure faulty usage is discovered."""
        with pytest.raises(ValueError, match="more dimensions than allowed"):
            _as_pairs([[[3]]], 10)
        with pytest.raises(ValueError, match="could not be broadcast"):
            _as_pairs([[1, 2], [3, 4]], 3)
        with pytest.raises(ValueError, match="could not be broadcast"):
            _as_pairs(np.ones((2, 3)), 3)


class TestConditionalShortcuts:
    @pytest.mark.parametrize("mode", _all_modes.keys())
    def test_zero_padding_shortcuts(self, mode):
        test = np.arange(120).reshape(4, 5, 6)
        pad_amt = [(0, 0) for _ in test.shape]
        assert_array_equal(test, np.pad(test, pad_amt, mode=mode))

    @pytest.mark.parametrize("mode", ['maximum', 'mean', 'median', 'minimum',])
    def test_shallow_statistic_range(self, mode):
        test = np.arange(120).reshape(4, 5, 6)
        pad_amt = [(1, 1) for _ in test.shape]
        assert_array_equal(np.pad(test, pad_amt, mode='edge'),
                           np.pad(test, pad_amt, mode=mode, stat_length=1))

    @pytest.mark.parametrize("mode", ['maximum', 'mean', 'median', 'minimum',])
    def test_clip_statistic_range(self, mode):
        test = np.arange(30).reshape(5, 6)
        pad_amt = [(3, 3) for _ in test.shape]
        assert_array_equal(np.pad(test, pad_amt, mode=mode),
                           np.pad(test, pad_amt, mode=mode, stat_length=30))


class TestStatistic:
    def test_check_mean_stat_length(self):
        a = np.arange(100).astype('f')
        a = np.pad(a, ((25, 20), ), 'mean', stat_length=((2, 3), ))
        b = np.array(
            [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5,
             0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5,
             0.5, 0.5, 0.5, 0.5, 0.5,

             0., 1., 2., 3., 4., 5., 6., 7., 8., 9.,
             10., 11., 12., 13., 14., 15., 16., 17., 18., 19.,
             20., 21., 22., 23., 24., 25., 26., 27., 28., 29.,
             30., 31., 32., 33., 34., 35., 36., 37., 38., 39.,
             40., 41., 42., 43., 44., 45., 46., 47., 48., 49.,
             50., 51., 52., 53., 54., 55., 56., 57., 58., 59.,
             60., 61., 62., 63., 64., 65., 66., 67., 68., 69.,
             70., 71., 72., 73., 74., 75., 76., 77., 78., 79.,
             80., 81., 82., 83., 84., 85., 86., 87., 88., 89.,
             90., 91., 92., 93., 94., 95., 96., 97., 98., 99.,

             98., 98., 98., 98., 98., 98., 98., 98., 98., 98.,
             98., 98., 98., 98., 98., 98., 98., 98., 98., 98.
             ])
        assert_array_equal(a, b)

    def test_check_maximum_1(self):
        a = np.arange(100)
        a = np.pad(a, (25, 20), 'maximum')
        b = np.array(
            [99, 99, 99, 99, 99, 99, 99, 99, 99, 99,
             99, 99, 99, 99, 99, 99, 99, 99, 99, 99,
             99, 99, 99, 99, 99,

             0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
             20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
             30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
             40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
             50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
             60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
             70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
             80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
             90, 91, 92, 93, 94, 95, 96, 97, 98, 99,

             99, 99, 99, 99, 99, 99, 99, 99, 99, 99,
             99, 99, 99, 99, 99, 99, 99, 99, 99, 99]
            )
        assert_array_equal(a, b)

    def test_check_maximum_2(self):
        a = np.arange(100) + 1
        a = np.pad(a, (25, 20), 'maximum')
        b = np.array(
            [100, 100, 100, 100, 100, 100, 100, 100, 100, 100,
             100, 100, 100, 100, 100, 100, 100, 100, 100, 100,
             100, 100, 100, 100, 100,

             1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
             11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
             21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
             31, 32, 33, 34, 35, 36, 37, 38, 39, 40,
             41, 42, 43, 44, 45, 46, 47, 48, 49, 50,
             51, 52, 53, 54, 55, 56, 57, 58, 59, 60,
             61, 62, 63, 64, 65, 66, 67, 68, 69, 70,
             71, 72, 73, 74, 75, 76, 77, 78, 79, 80,
             81, 82, 83, 84, 85, 86, 87, 88, 89, 90,
             91, 92, 93, 94, 95, 96, 97, 98, 99, 100,

             100, 100, 100, 100, 100, 100, 100, 100, 100, 100,
             100, 100, 100, 100, 100, 100, 100, 100, 100, 100]
            )
        assert_array_equal(a, b)

    def test_check_maximum_stat_length(self):
        a = np.arange(100) + 1
        a = np.pad(a, (25, 20), 'maximum', stat_length=10)
        b = np.array(
            [10, 10, 10, 10, 10, 10, 10, 10, 10, 10,
             10, 10, 10, 10, 10, 10, 10, 10, 10, 10,
             10, 10, 10, 10, 10,

              1,  2,  3,  4,  5,  6,  7,  8,  9, 10,
             11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
             21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
             31, 32, 33, 34, 35, 36, 37, 38, 39, 40,
             41, 42, 43, 44, 45, 46, 47, 48, 49, 50,
             51, 52, 53, 54, 55, 56, 57, 58, 59, 60,
             61, 62, 63, 64, 65, 66, 67, 68, 69, 70,
             71, 72, 73, 74, 75, 76, 77, 78, 79, 80,
             81, 82, 83, 84, 85, 86, 87, 88, 89, 90,
             91, 92, 93, 94, 95, 96, 97, 98, 99, 100,

             100, 100, 100, 100, 100, 100, 100, 100, 100, 100,
             100, 100, 100, 100, 100, 100, 100, 100, 100, 100]
            )
        assert_array_equal(a, b)

    def test_check_minimum_1(self):
        a = np.arange(100)
        a = np.pad(a, (25, 20), 'minimum')
        b = np.array(
            [ 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
              0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
              0,  0,  0,  0,  0,

              0,  1,  2,  3,  4,  5,  6,  7,  8,  9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
             20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
             30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
             40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
             50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
             60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
             70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
             80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
             90, 91, 92, 93, 94, 95, 96, 97, 98, 99,

             0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
             0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            )
        assert_array_equal(a, b)

    def test_check_minimum_2(self):
        a = np.arange(100) + 2
        a = np.pad(a, (25, 20), 'minimum')
        b = np.array(
            [ 2,  2,  2,  2,  2,  2,  2,  2,  2,  2,
              2,  2,  2,  2,  2,  2,  2,  2,  2,  2,
              2,  2,  2,  2,  2,

              2,  3,  4,  5,  6,  7,  8,  9, 10, 11,
             12, 13, 14, 15, 16, 17, 18, 19, 20, 21,
             22, 23, 24, 25, 26, 27, 28, 29, 30, 31,
             32, 33, 34, 35, 36, 37, 38, 39, 40, 41,
             42, 43, 44, 45, 46, 47, 48, 49, 50, 51,
             52, 53, 54, 55, 56, 57, 58, 59, 60, 61,
             62, 63, 64, 65, 66, 67, 68, 69, 70, 71,
             72, 73, 74, 75, 76, 77, 78, 79, 80, 81,
             82, 83, 84, 85, 86, 87, 88, 89, 90, 91,
             92, 93, 94, 95, 96, 97, 98, 99, 100, 101,

             2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
             2, 2, 2, 2, 2, 2, 2, 2, 2, 2]
            )
        assert_array_equal(a, b)

    def test_check_minimum_stat_length(self):
        a = np.arange(100) + 1
        a = np.pad(a, (25, 20), 'minimum', stat_length=10)
        b = np.array(
            [ 1,  1,  1,  1,  1,  1,  1,  1,  1,  1,
              1,  1,  1,  1,  1,  1,  1,  1,  1,  1,
              1,  1,  1,  1,  1,

              1,  2,  3,  4,  5,  6,  7,  8,  9, 10,
             11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
             21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
             31, 32, 33, 34, 35, 36, 37, 38, 39, 40,
             41, 42, 43, 44, 45, 46, 47, 48, 49, 50,
             51, 52, 53, 54, 55, 56, 57, 58, 59, 60,
             61, 62, 63, 64, 65, 66, 67, 68, 69, 70,
             71, 72, 73, 74, 75, 76, 77, 78, 79, 80,
             81, 82, 83, 84, 85, 86, 87, 88, 89, 90,
             91, 92, 93, 94, 95, 96, 97, 98, 99, 100,

             91, 91, 91, 91, 91, 91, 91, 91, 91, 91,
             91, 91, 91, 91, 91, 91, 91, 91, 91, 91]
            )
        assert_array_equal(a, b)

    def test_check_median(self):
        a = np.arange(100).astype('f')
        a = np.pad(a, (25, 20), 'median')
        b = np.array(
            [49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5,
             49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5,
             49.5, 49.5, 49.5, 49.5, 49.5,

             0., 1., 2., 3., 4., 5., 6., 7., 8., 9.,
             10., 11., 12., 13., 14., 15., 16., 17., 18., 19.,
             20., 21., 22., 23., 24., 25., 26., 27., 28., 29.,
             30., 31., 32., 33., 34., 35., 36., 37., 38., 39.,
             40., 41., 42., 43., 44., 45., 46., 47., 48., 49.,
             50., 51., 52., 53., 54., 55., 56., 57., 58., 59.,
             60., 61., 62., 63., 64., 65., 66., 67., 68., 69.,
             70., 71., 72., 73., 74., 75., 76., 77., 78., 79.,
             80., 81., 82., 83., 84., 85., 86., 87., 88., 89.,
             90., 91., 92., 93., 94., 95., 96., 97., 98., 99.,

             49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5,
             49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5]
            )
        assert_array_equal(a, b)

    def test_check_median_01(self):
        a = np.array([[3, 1, 4], [4, 5, 9], [9, 8, 2]])
        a = np.pad(a, 1, 'median')
        b = np.array(
            [[4, 4, 5, 4, 4],

             [3, 3, 1, 4, 3],
             [5, 4, 5, 9, 5],
             [8, 9, 8, 2, 8],

             [4, 4, 5, 4, 4]]
            )
        assert_array_equal(a, b)

    def test_check_median_02(self):
        a = np.array([[3, 1, 4], [4, 5, 9], [9, 8, 2]])
        a = np.pad(a.T, 1, 'median').T
        b = np.array(
            [[5, 4, 5, 4, 5],

             [3, 3, 1, 4, 3],
             [5, 4, 5, 9, 5],
             [8, 9, 8, 2, 8],

             [5, 4, 5, 4, 5]]
            )
        assert_array_equal(a, b)

    def test_check_median_stat_length(self):
        a = np.arange(100).astype('f')
        a[1] = 2.
        a[97] = 96.
        a = np.pad(a, (25, 20), 'median', stat_length=(3, 5))
        b = np.array(
            [ 2.,  2.,  2.,  2.,  2.,  2.,  2.,  2.,  2.,  2.,
              2.,  2.,  2.,  2.,  2.,  2.,  2.,  2.,  2.,  2.,
              2.,  2.,  2.,  2.,  2.,

              0.,  2.,  2.,  3.,  4.,  5.,  6.,  7.,  8.,  9.,
             10., 11., 12., 13., 14., 15., 16., 17., 18., 19.,
             20., 21., 22., 23., 24., 25., 26., 27., 28., 29.,
             30., 31., 32., 33., 34., 35., 36., 37., 38., 39.,
             40., 41., 42., 43., 44., 45., 46., 47., 48., 49.,
             50., 51., 52., 53., 54., 55., 56., 57., 58., 59.,
             60., 61., 62., 63., 64., 65., 66., 67., 68., 69.,
             70., 71., 72., 73., 74., 75., 76., 77., 78., 79.,
             80., 81., 82., 83., 84., 85., 86., 87., 88., 89.,
             90., 91., 92., 93., 94., 95., 96., 96., 98., 99.,

             96., 96., 96., 96., 96., 96., 96., 96., 96., 96.,
             96., 96., 96., 96., 96., 96., 96., 96., 96., 96.]
            )
        assert_array_equal(a, b)

    def test_check_mean_shape_one(self):
        a = [[4, 5, 6]]
        a = np.pad(a, (5, 7), 'mean', stat_length=2)
        b = np.array(
            [[4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],
             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],
             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],
             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],
             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],

             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],

             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],
             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],
             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],
             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],
             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],
             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],
             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6]]
            )
        assert_array_equal(a, b)

    def test_check_mean_2(self):
        a = np.arange(100).astype('f')
        a = np.pad(a, (25, 20), 'mean')
        b = np.array(
            [49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5,
             49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5,
             49.5, 49.5, 49.5, 49.5, 49.5,

             0., 1., 2., 3., 4., 5., 6., 7., 8., 9.,
             10., 11., 12., 13., 14., 15., 16., 17., 18., 19.,
             20., 21., 22., 23., 24., 25., 26., 27., 28., 29.,
             30., 31., 32., 33., 34., 35., 36., 37., 38., 39.,
             40., 41., 42., 43., 44., 45., 46., 47., 48., 49.,
             50., 51., 52., 53., 54., 55., 56., 57., 58., 59.,
             60., 61., 62., 63., 64., 65., 66., 67., 68., 69.,
             70., 71., 72., 73., 74., 75., 76., 77., 78., 79.,
             80., 81., 82., 83., 84., 85., 86., 87., 88., 89.,
             90., 91., 92., 93., 94., 95., 96., 97., 98., 99.,

             49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5,
             49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5]
            )
        assert_array_equal(a, b)

    @pytest.mark.parametrize("mode", [
        "mean",
        "median",
        "minimum",
        "maximum"
    ])
    def test_same_prepend_append(self, mode):
        """ Test that appended and prepended values are equal """
        # This test is constructed to trigger floating point rounding errors in
        # a way that caused gh-11216 for mode=='mean'
        a = np.array([-1, 2, -1]) + np.array([0, 1e-12, 0], dtype=np.float64)
        a = np.pad(a, (1, 1), mode)
        assert_equal(a[0], a[-1])

    @pytest.mark.parametrize("mode", ["mean", "median", "minimum", "maximum"])
    @pytest.mark.parametrize(
        "stat_length", [-2, (-2,), (3, -1), ((5, 2), (-2, 3)), ((-4,), (2,))]
    )
    def test_check_negative_stat_length(self, mode, stat_length):
        arr = np.arange(30).reshape((6, 5))
        match = "index can't contain negative values"
        with pytest.raises(ValueError, match=match):
            np.pad(arr, 2, mode, stat_length=stat_length)

    def test_simple_stat_length(self):
        a = np.arange(30)
        a = np.reshape(a, (6, 5))
        a = np.pad(a, ((2, 3), (3, 2)), mode='mean', stat_length=(3,))
        b = np.array(
            [[6, 6, 6, 5, 6, 7, 8, 9, 8, 8],
             [6, 6, 6, 5, 6, 7, 8, 9, 8, 8],

             [1, 1, 1, 0, 1, 2, 3, 4, 3, 3],
             [6, 6, 6, 5, 6, 7, 8, 9, 8, 8],
             [11, 11, 11, 10, 11, 12, 13, 14, 13, 13],
             [16, 16, 16, 15, 16, 17, 18, 19, 18, 18],
             [21, 21, 21, 20, 21, 22, 23, 24, 23, 23],
             [26, 26, 26, 25, 26, 27, 28, 29, 28, 28],

             [21, 21, 21, 20, 21, 22, 23, 24, 23, 23],
             [21, 21, 21, 20, 21, 22, 23, 24, 23, 23],
             [21, 21, 21, 20, 21, 22, 23, 24, 23, 23]]
            )
        assert_array_equal(a, b)

    @pytest.mark.filterwarnings("ignore:Mean of empty slice:RuntimeWarning")
    @pytest.mark.filterwarnings(
        "ignore:invalid value encountered in( scalar)? divide:RuntimeWarning"
    )
    @pytest.mark.parametrize("mode", ["mean", "median"])
    def test_zero_stat_length_valid(self, mode):
        arr = np.pad([1., 2.], (1, 2), mode, stat_length=0)
        expected = np.array([np.nan, 1., 2., np.nan, np.nan])
        assert_equal(arr, expected)

    @pytest.mark.parametrize("mode", ["minimum", "maximum"])
    def test_zero_stat_length_invalid(self, mode):
        match = "stat_length of 0 yields no value for padding"
        with pytest.raises(ValueError, match=match):
            np.pad([1., 2.], 0, mode, stat_length=0)
        with pytest.raises(ValueError, match=match):
            np.pad([1., 2.], 0, mode, stat_length=(1, 0))
        with pytest.raises(ValueError, match=match):
            np.pad([1., 2.], 1, mode, stat_length=0)
        with pytest.raises(ValueError, match=match):
            np.pad([1., 2.], 1, mode, stat_length=(1, 0))


class TestConstant:
    def test_check_constant(self):
        a = np.arange(100)
        a = np.pad(a, (25, 20), 'constant', constant_values=(10, 20))
        b = np.array(
            [10, 10, 10, 10, 10, 10, 10, 10, 10, 10,
             10, 10, 10, 10, 10, 10, 10, 10, 10, 10,
             10, 10, 10, 10, 10,

             0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
             20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
             30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
             40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
             50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
             60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
             70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
             80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
             90, 91, 92, 93, 94, 95, 96, 97, 98, 99,

             20, 20, 20, 20, 20, 20, 20, 20, 20, 20,
             20, 20, 20, 20, 20, 20, 20, 20, 20, 20]
            )
        assert_array_equal(a, b)

    def test_check_constant_zeros(self):
        a = np.arange(100)
        a = np.pad(a, (25, 20), 'constant')
        b = np.array(
            [ 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
              0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
              0,  0,  0,  0,  0,

             0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
             20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
             30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
             40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
             50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
             60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
             70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
             80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
             90, 91, 92, 93, 94, 95, 96, 97, 98, 99,

              0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
              0,  0,  0,  0,  0,  0,  0,  0,  0,  0]
            )
        assert_array_equal(a, b)

    def test_check_constant_float(self):
        # If input array is int, but constant_values are float, the dtype of
        # the array to be padded is kept
        arr = np.arange(30).reshape(5, 6)
        test = np.pad(arr, (1, 2), mode='constant',
                   constant_values=1.1)
        expected = np.array(
            [[1,  1,  1,  1,  1,  1,  1,  1,  1],

             [1,  0,  1,  2,  3,  4,  5,  1,  1],
             [1,  6,  7,  8,  9, 10, 11,  1,  1],
             [1, 12, 13, 14, 15, 16, 17,  1,  1],
             [1, 18, 19, 20, 21, 22, 23,  1,  1],
             [1, 24, 25, 26, 27, 28, 29,  1,  1],

             [1,  1,  1,  1,  1,  1,  1,  1,  1],
             [1,  1,  1,  1,  1,  1,  1,  1,  1]]
            )
        assert_allclose(test, expected)

    def test_check_constant_float2(self):
        # If input array is float, and constant_values are float, the dtype of
        # the array to be padded is kept - here retaining the float constants
        arr = np.arange(30).reshape(5, 6)
        arr_float = arr.astype(np.float64)
        test = np.pad(arr_float, ((1, 2), (1, 2)), mode='constant',
                   constant_values=1.1)
        expected = np.array(
            [[1.1,   1.1,   1.1,   1.1,   1.1,   1.1,   1.1,   1.1,   1.1],

             [1.1,   0. ,   1. ,   2. ,   3. ,   4. ,   5. ,   1.1,   1.1],  # noqa: E203
             [1.1,   6. ,   7. ,   8. ,   9. ,  10. ,  11. ,   1.1,   1.1],  # noqa: E203
             [1.1,  12. ,  13. ,  14. ,  15. ,  16. ,  17. ,   1.1,   1.1],  # noqa: E203
             [1.1,  18. ,  19. ,  20. ,  21. ,  22. ,  23. ,   1.1,   1.1],  # noqa: E203
             [1.1,  24. ,  25. ,  26. ,  27. ,  28. ,  29. ,   1.1,   1.1],  # noqa: E203

             [1.1,   1.1,   1.1,   1.1,   1.1,   1.1,   1.1,   1.1,   1.1],
             [1.1,   1.1,   1.1,   1.1,   1.1,   1.1,   1.1,   1.1,   1.1]]
            )
        assert_allclose(test, expected)

    def test_check_constant_float3(self):
        a = np.arange(100, dtype=float)
        a = np.pad(a, (25, 20), 'constant', constant_values=(-1.1, -1.2))
        b = np.array(
            [-1.1, -1.1, -1.1, -1.1, -1.1, -1.1, -1.1, -1.1, -1.1, -1.1,
             -1.1, -1.1, -1.1, -1.1, -1.1, -1.1, -1.1, -1.1, -1.1, -1.1,
             -1.1, -1.1, -1.1, -1.1, -1.1,

             0,  1,  2,  3,  4,  5,  6,  7,  8,  9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
             20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
             30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
             40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
             50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
             60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
             70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
             80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
             90, 91, 92, 93, 94, 95, 96, 97, 98, 99,

             -1.2, -1.2, -1.2, -1.2, -1.2, -1.2, -1.2, -1.2, -1.2, -1.2,
             -1.2, -1.2, -1.2, -1.2, -1.2, -1.2, -1.2, -1.2, -1.2, -1.2]
            )
        assert_allclose(a, b)

    def test_check_constant_odd_pad_amount(self):
        arr = np.arange(30).reshape(5, 6)
        test = np.pad(arr, ((1,), (2,)), mode='constant',
                   constant_values=3)
        expected = np.array(
            [[3,  3,  3,  3,  3,  3,  3,  3,  3,  3],

             [3,  3,  0,  1,  2,  3,  4,  5,  3,  3],
             [3,  3,  6,  7,  8,  9, 10, 11,  3,  3],
             [3,  3, 12, 13, 14, 15, 16, 17,  3,  3],
             [3,  3, 18, 19, 20, 21, 22, 23,  3,  3],
             [3,  3, 24, 25, 26, 27, 28, 29,  3,  3],

             [3,  3,  3,  3,  3,  3,  3,  3,  3,  3]]
            )
        assert_allclose(test, expected)

    def test_check_constant_pad_2d(self):
        arr = np.arange(4).reshape(2, 2)
        test = np.pad(arr, ((1, 2), (1, 3)), mode='constant',
                          constant_values=((1, 2), (3, 4)))
        expected = np.array(
            [[3, 1, 1, 4, 4, 4],
             [3, 0, 1, 4, 4, 4],
             [3, 2, 3, 4, 4, 4],
             [3, 2, 2, 4, 4, 4],
             [3, 2, 2, 4, 4, 4]]
        )
        assert_allclose(test, expected)

    def test_check_large_integers(self):
        uint64_max = 2 ** 64 - 1
        arr = np.full(5, uint64_max, dtype=np.uint64)
        test = np.pad(arr, 1, mode="constant", constant_values=arr.min())
        expected = np.full(7, uint64_max, dtype=np.uint64)
        assert_array_equal(test, expected)

        int64_max = 2 ** 63 - 1
        arr = np.full(5, int64_max, dtype=np.int64)
        test = np.pad(arr, 1, mode="constant", constant_values=arr.min())
        expected = np.full(7, int64_max, dtype=np.int64)
        assert_array_equal(test, expected)

    def test_check_object_array(self):
        arr = np.empty(1, dtype=object)
        obj_a = object()
        arr[0] = obj_a
        obj_b = object()
        obj_c = object()
        arr = np.pad(arr, pad_width=1, mode='constant',
                     constant_values=(obj_b, obj_c))

        expected = np.empty((3,), dtype=object)
        expected[0] = obj_b
        expected[1] = obj_a
        expected[2] = obj_c

        assert_array_equal(arr, expected)

    def test_pad_empty_dimension(self):
        arr = np.zeros((3, 0, 2))
        result = np.pad(arr, [(0,), (2,), (1,)], mode="constant")
        assert result.shape == (3, 4, 4)


class TestLinearRamp:
    def test_check_simple(self):
        a = np.arange(100).astype('f')
        a = np.pad(a, (25, 20), 'linear_ramp', end_values=(4, 5))
        b = np.array(
            [4.00, 3.84, 3.68, 3.52, 3.36, 3.20, 3.04, 2.88, 2.72, 2.56,
             2.40, 2.24, 2.08, 1.92, 1.76, 1.60, 1.44, 1.28, 1.12, 0.96,
             0.80, 0.64, 0.48, 0.32, 0.16,

             0.00, 1.00, 2.00, 3.00, 4.00, 5.00, 6.00, 7.00, 8.00, 9.00,
             10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0,
             20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0, 29.0,
             30.0, 31.0, 32.0, 33.0, 34.0, 35.0, 36.0, 37.0, 38.0, 39.0,
             40.0, 41.0, 42.0, 43.0, 44.0, 45.0, 46.0, 47.0, 48.0, 49.0,
             50.0, 51.0, 52.0, 53.0, 54.0, 55.0, 56.0, 57.0, 58.0, 59.0,
             60.0, 61.0, 62.0, 63.0, 64.0, 65.0, 66.0, 67.0, 68.0, 69.0,
             70.0, 71.0, 72.0, 73.0, 74.0, 75.0, 76.0, 77.0, 78.0, 79.0,
             80.0, 81.0, 82.0, 83.0, 84.0, 85.0, 86.0, 87.0, 88.0, 89.0,
             90.0, 91.0, 92.0, 93.0, 94.0, 95.0, 96.0, 97.0, 98.0, 99.0,

             94.3, 89.6, 84.9, 80.2, 75.5, 70.8, 66.1, 61.4, 56.7, 52.0,
             47.3, 42.6, 37.9, 33.2, 28.5, 23.8, 19.1, 14.4, 9.7, 5.]
            )
        assert_allclose(a, b, rtol=1e-5, atol=1e-5)

    def test_check_2d(self):
        arr = np.arange(20).reshape(4, 5).astype(np.float64)
        test = np.pad(arr, (2, 2), mode='linear_ramp', end_values=(0, 0))
        expected = np.array(
            [[0.,   0.,   0.,   0.,   0.,   0.,   0.,    0.,   0.],
             [0.,   0.,   0.,  0.5,   1.,  1.5,   2.,    1.,   0.],
             [0.,   0.,   0.,   1.,   2.,   3.,   4.,    2.,   0.],
             [0.,  2.5,   5.,   6.,   7.,   8.,   9.,   4.5,   0.],
             [0.,   5.,  10.,  11.,  12.,  13.,  14.,    7.,   0.],
             [0.,  7.5,  15.,  16.,  17.,  18.,  19.,   9.5,   0.],
             [0., 3.75,  7.5,   8.,  8.5,   9.,  9.5,  4.75,   0.],
             [0.,   0.,   0.,   0.,   0.,   0.,   0.,    0.,   0.]])
        assert_allclose(test, expected)

    @pytest.mark.xfail(exceptions=(AssertionError,))
    def test_object_array(self):
        from fractions import Fraction
        arr = np.array([Fraction(1, 2), Fraction(-1, 2)])
        actual = np.pad(arr, (2, 3), mode='linear_ramp', end_values=0)

        # deliberately chosen to have a non-power-of-2 denominator such that
        # rounding to floats causes a failure.
        expected = np.array([
            Fraction( 0, 12),
            Fraction( 3, 12),
            Fraction( 6, 12),
            Fraction(-6, 12),
            Fraction(-4, 12),
            Fraction(-2, 12),
            Fraction(-0, 12),
        ])
        assert_equal(actual, expected)

    def test_end_values(self):
        """Ensure that end values are exact."""
        a = np.pad(np.ones(10).reshape(2, 5), (223, 123), mode="linear_ramp")
        assert_equal(a[:, 0], 0.)
        assert_equal(a[:, -1], 0.)
        assert_equal(a[0, :], 0.)
        assert_equal(a[-1, :], 0.)

    @pytest.mark.parametrize("dtype", _numeric_dtypes)
    def test_negative_difference(self, dtype):
        """
        Check correct behavior of unsigned dtypes if there is a negative
        difference between the edge to pad and `end_values`. Check both cases
        to be independent of implementation. Test behavior for all other dtypes
        in case dtype casting interferes with complex dtypes. See gh-14191.
        """
        x = np.array([3], dtype=dtype)
        result = np.pad(x, 3, mode="linear_ramp", end_values=0)
        expected = np.array([0, 1, 2, 3, 2, 1, 0], dtype=dtype)
        assert_equal(result, expected)

        x = np.array([0], dtype=dtype)
        result = np.pad(x, 3, mode="linear_ramp", end_values=3)
        expected = np.array([3, 2, 1, 0, 1, 2, 3], dtype=dtype)
        assert_equal(result, expected)


class TestReflect:
    def test_check_simple(self):
        a = np.arange(100)
        a = np.pad(a, (25, 20), 'reflect')
        b = np.array(
            [25, 24, 23, 22, 21, 20, 19, 18, 17, 16,
             15, 14, 13, 12, 11, 10, 9, 8, 7, 6,
             5, 4, 3, 2, 1,

             0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
             20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
             30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
             40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
             50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
             60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
             70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
             80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
             90, 91, 92, 93, 94, 95, 96, 97, 98, 99,

             98, 97, 96, 95, 94, 93, 92, 91, 90, 89,
             88, 87, 86, 85, 84, 83, 82, 81, 80, 79]
            )
        assert_array_equal(a, b)

    def test_check_odd_method(self):
        a = np.arange(100)
        a = np.pad(a, (25, 20), 'reflect', reflect_type='odd')
        b = np.array(
            [-25, -24, -23, -22, -21, -20, -19, -18, -17, -16,
             -15, -14, -13, -12, -11, -10, -9, -8, -7, -6,
             -5, -4, -3, -2, -1,

             0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
             20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
             30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
             40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
             50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
             60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
             70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
             80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
             90, 91, 92, 93, 94, 95, 96, 97, 98, 99,

             100, 101, 102, 103, 104, 105, 106, 107, 108, 109,
             110, 111, 112, 113, 114, 115, 116, 117, 118, 119]
            )
        assert_array_equal(a, b)

    def test_check_large_pad(self):
        a = [[4, 5, 6], [6, 7, 8]]
        a = np.pad(a, (5, 7), 'reflect')
        b = np.array(
            [[7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7],

             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7],

             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5]]
            )
        assert_array_equal(a, b)

    def test_check_shape(self):
        a = [[4, 5, 6]]
        a = np.pad(a, (5, 7), 'reflect')
        b = np.array(
            [[5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],

             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],

             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5]]
            )
        assert_array_equal(a, b)

    def test_check_01(self):
        a = np.pad([1, 2, 3], 2, 'reflect')
        b = np.array([3, 2, 1, 2, 3, 2, 1])
        assert_array_equal(a, b)

    def test_check_02(self):
        a = np.pad([1, 2, 3], 3, 'reflect')
        b = np.array([2, 3, 2, 1, 2, 3, 2, 1, 2])
        assert_array_equal(a, b)

    def test_check_03(self):
        a = np.pad([1, 2, 3], 4, 'reflect')
        b = np.array([1, 2, 3, 2, 1, 2, 3, 2, 1, 2, 3])
        assert_array_equal(a, b)

    def test_check_04(self):
        a = np.pad([1, 2, 3], [1, 10], 'reflect')
        b = np.array([2, 1, 2, 3, 2, 1, 2, 3, 2, 1, 2, 3, 2, 1])
        assert_array_equal(a, b)

    def test_check_05(self):
        a = np.pad([1, 2, 3, 4], [45, 10], 'reflect')
        b = np.array(
            [4, 3, 2, 1, 2, 3, 4, 3, 2, 1,
             2, 3, 4, 3, 2, 1, 2, 3, 4, 3,
             2, 1, 2, 3, 4, 3, 2, 1, 2, 3,
             4, 3, 2, 1, 2, 3, 4, 3, 2, 1,
             2, 3, 4, 3, 2, 1, 2, 3, 4, 3,
             2, 1, 2, 3, 4, 3, 2, 1, 2])
        assert_array_equal(a, b)

    def test_check_06(self):
        a = np.pad([1, 2, 3, 4], [15, 2], 'symmetric')
        b = np.array(
            [2, 3, 4, 4, 3, 2, 1, 1, 2, 3,
             4, 4, 3, 2, 1, 1, 2, 3, 4, 4,
             3]
        )
        assert_array_equal(a, b)

    def test_check_07(self):
        a = np.pad([1, 2, 3, 4, 5, 6], [45, 3], 'symmetric')
        b = np.array(
            [4, 5, 6, 6, 5, 4, 3, 2, 1, 1,
             2, 3, 4, 5, 6, 6, 5, 4, 3, 2,
             1, 1, 2, 3, 4, 5, 6, 6, 5, 4,
             3, 2, 1, 1, 2, 3, 4, 5, 6, 6,
             5, 4, 3, 2, 1, 1, 2, 3, 4, 5,
             6, 6, 5, 4])
        assert_array_equal(a, b)


class TestEmptyArray:
    """Check how padding behaves on arrays with an empty dimension."""

    @pytest.mark.parametrize(
        # Keep parametrization ordered, otherwise pytest-xdist might believe
        # that different tests were collected during parallelization
        "mode", sorted(_all_modes.keys() - {"constant", "empty"})
    )
    def test_pad_empty_dimension(self, mode):
        match = ("can't extend empty axis 0 using modes other than 'constant' "
                 "or 'empty'")
        with pytest.raises(ValueError, match=match):
            np.pad([], 4, mode=mode)
        with pytest.raises(ValueError, match=match):
            np.pad(np.ndarray(0), 4, mode=mode)
        with pytest.raises(ValueError, match=match):
            np.pad(np.zeros((0, 3)), ((1,), (0,)), mode=mode)

    @pytest.mark.parametrize("mode", _all_modes.keys())
    def test_pad_non_empty_dimension(self, mode):
        result = np.pad(np.ones((2, 0, 2)), ((3,), (0,), (1,)), mode=mode)
        assert result.shape == (8, 0, 4)


class TestSymmetric:
    def test_check_simple(self):
        a = np.arange(100)
        a = np.pad(a, (25, 20), 'symmetric')
        b = np.array(
            [24, 23, 22, 21, 20, 19, 18, 17, 16, 15,
             14, 13, 12, 11, 10, 9, 8, 7, 6, 5,
             4, 3, 2, 1, 0,

             0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
             20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
             30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
             40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
             50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
             60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
             70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
             80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
             90, 91, 92, 93, 94, 95, 96, 97, 98, 99,

             99, 98, 97, 96, 95, 94, 93, 92, 91, 90,
             89, 88, 87, 86, 85, 84, 83, 82, 81, 80]
            )
        assert_array_equal(a, b)

    def test_check_odd_method(self):
        a = np.arange(100)
        a = np.pad(a, (25, 20), 'symmetric', reflect_type='odd')
        b = np.array(
            [-24, -23, -22, -21, -20, -19, -18, -17, -16, -15,
             -14, -13, -12, -11, -10, -9, -8, -7, -6, -5,
             -4, -3, -2, -1, 0,

             0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
             20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
             30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
             40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
             50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
             60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
             70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
             80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
             90, 91, 92, 93, 94, 95, 96, 97, 98, 99,

             99, 100, 101, 102, 103, 104, 105, 106, 107, 108,
             109, 110, 111, 112, 113, 114, 115, 116, 117, 118]
            )
        assert_array_equal(a, b)

    def test_check_large_pad(self):
        a = [[4, 5, 6], [6, 7, 8]]
        a = np.pad(a, (5, 7), 'symmetric')
        b = np.array(
            [[5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [7, 8, 8, 7, 6, 6, 7, 8, 8, 7, 6, 6, 7, 8, 8],
             [7, 8, 8, 7, 6, 6, 7, 8, 8, 7, 6, 6, 7, 8, 8],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],

             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [7, 8, 8, 7, 6, 6, 7, 8, 8, 7, 6, 6, 7, 8, 8],

             [7, 8, 8, 7, 6, 6, 7, 8, 8, 7, 6, 6, 7, 8, 8],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [7, 8, 8, 7, 6, 6, 7, 8, 8, 7, 6, 6, 7, 8, 8],
             [7, 8, 8, 7, 6, 6, 7, 8, 8, 7, 6, 6, 7, 8, 8],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6]]
            )

        assert_array_equal(a, b)

    def test_check_large_pad_odd(self):
        a = [[4, 5, 6], [6, 7, 8]]
        a = np.pad(a, (5, 7), 'symmetric', reflect_type='odd')
        b = np.array(
            [[-3, -2, -2, -1,  0,  0,  1,  2,  2,  3,  4,  4,  5,  6,  6],
             [-3, -2, -2, -1,  0,  0,  1,  2,  2,  3,  4,  4,  5,  6,  6],
             [-1,  0,  0,  1,  2,  2,  3,  4,  4,  5,  6,  6,  7,  8,  8],
             [-1,  0,  0,  1,  2,  2,  3,  4,  4,  5,  6,  6,  7,  8,  8],
             [ 1,  2,  2,  3,  4,  4,  5,  6,  6,  7,  8,  8,  9, 10, 10],

             [ 1,  2,  2,  3,  4,  4,  5,  6,  6,  7,  8,  8,  9, 10, 10],
             [ 3,  4,  4,  5,  6,  6,  7,  8,  8,  9, 10, 10, 11, 12, 12],

             [ 3,  4,  4,  5,  6,  6,  7,  8,  8,  9, 10, 10, 11, 12, 12],
             [ 5,  6,  6,  7,  8,  8,  9, 10, 10, 11, 12, 12, 13, 14, 14],
             [ 5,  6,  6,  7,  8,  8,  9, 10, 10, 11, 12, 12, 13, 14, 14],
             [ 7,  8,  8,  9, 10, 10, 11, 12, 12, 13, 14, 14, 15, 16, 16],
             [ 7,  8,  8,  9, 10, 10, 11, 12, 12, 13, 14, 14, 15, 16, 16],
             [ 9, 10, 10, 11, 12, 12, 13, 14, 14, 15, 16, 16, 17, 18, 18],
             [ 9, 10, 10, 11, 12, 12, 13, 14, 14, 15, 16, 16, 17, 18, 18]]
            )
        assert_array_equal(a, b)

    def test_check_shape(self):
        a = [[4, 5, 6]]
        a = np.pad(a, (5, 7), 'symmetric')
        b = np.array(
            [[5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],

             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],

             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6]]
            )
        assert_array_equal(a, b)

    def test_check_01(self):
        a = np.pad([1, 2, 3], 2, 'symmetric')
        b = np.array([2, 1, 1, 2, 3, 3, 2])
        assert_array_equal(a, b)

    def test_check_02(self):
        a = np.pad([1, 2, 3], 3, 'symmetric')
        b = np.array([3, 2, 1, 1, 2, 3, 3, 2, 1])
        assert_array_equal(a, b)

    def test_check_03(self):
        a = np.pad([1, 2, 3], 6, 'symmetric')
        b = np.array([1, 2, 3, 3, 2, 1, 1, 2, 3, 3, 2, 1, 1, 2, 3])
        assert_array_equal(a, b)


class TestWrap:
    def test_check_simple(self):
        a = np.arange(100)
        a = np.pad(a, (25, 20), 'wrap')
        b = np.array(
            [75, 76, 77, 78, 79, 80, 81, 82, 83, 84,
             85, 86, 87, 88, 89, 90, 91, 92, 93, 94,
             95, 96, 97, 98, 99,

             0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
             20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
             30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
             40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
             50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
             60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
             70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
             80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
             90, 91, 92, 93, 94, 95, 96, 97, 98, 99,

             0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
            )
        assert_array_equal(a, b)

    def test_check_large_pad(self):
        a = np.arange(12)
        a = np.reshape(a, (3, 4))
        a = np.pad(a, (10, 12), 'wrap')
        b = np.array(
            [[10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10,
              11, 8, 9, 10, 11, 8, 9, 10, 11],
             [2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2,
              3, 0, 1, 2, 3, 0, 1, 2, 3],
             [6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6,
              7, 4, 5, 6, 7, 4, 5, 6, 7],
             [10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10,
              11, 8, 9, 10, 11, 8, 9, 10, 11],
             [2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2,
              3, 0, 1, 2, 3, 0, 1, 2, 3],
             [6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6,
              7, 4, 5, 6, 7, 4, 5, 6, 7],
             [10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10,
              11, 8, 9, 10, 11, 8, 9, 10, 11],
             [2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2,
              3, 0, 1, 2, 3, 0, 1, 2, 3],
             [6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6,
              7, 4, 5, 6, 7, 4, 5, 6, 7],
             [10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10,
              11, 8, 9, 10, 11, 8, 9, 10, 11],

             [2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2,
              3, 0, 1, 2, 3, 0, 1, 2, 3],
             [6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6,
              7, 4, 5, 6, 7, 4, 5, 6, 7],
             [10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10,
              11, 8, 9, 10, 11, 8, 9, 10, 11],

             [2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2,
              3, 0, 1, 2, 3, 0, 1, 2, 3],
             [6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6,
              7, 4, 5, 6, 7, 4, 5, 6, 7],
             [10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10,
              11, 8, 9, 10, 11, 8, 9, 10, 11],
             [2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2,
              3, 0, 1, 2, 3, 0, 1, 2, 3],
             [6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6,
              7, 4, 5, 6, 7, 4, 5, 6, 7],
             [10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10,
              11, 8, 9, 10, 11, 8, 9, 10, 11],
             [2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2,
              3, 0, 1, 2, 3, 0, 1, 2, 3],
             [6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6,
              7, 4, 5, 6, 7, 4, 5, 6, 7],
             [10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10,
              11, 8, 9, 10, 11, 8, 9, 10, 11],
             [2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2,
              3, 0, 1, 2, 3, 0, 1, 2, 3],
             [6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6,
              7, 4, 5, 6, 7, 4, 5, 6, 7],
             [10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10,
              11, 8, 9, 10, 11, 8, 9, 10, 11]]
            )
        assert_array_equal(a, b)

    def test_check_01(self):
        a = np.pad([1, 2, 3], 3, 'wrap')
        b = np.array([1, 2, 3, 1, 2, 3, 1, 2, 3])
        assert_array_equal(a, b)

    def test_check_02(self):
        a = np.pad([1, 2, 3], 4, 'wrap')
        b = np.array([3, 1, 2, 3, 1, 2, 3, 1, 2, 3, 1])
        assert_array_equal(a, b)

    def test_pad_with_zero(self):
        a = np.ones((3, 5))
        b = np.pad(a, (0, 5), mode="wrap")
        assert_array_equal(a, b[:-5, :-5])

    def test_repeated_wrapping(self):
        """
        Check wrapping on each side individually if the wrapped area is longer
        than the original array.
        """
        a = np.arange(5)
        b = np.pad(a, (12, 0), mode="wrap")
        assert_array_equal(np.r_[a, a, a, a][3:], b)

        a = np.arange(5)
        b = np.pad(a, (0, 12), mode="wrap")
        assert_array_equal(np.r_[a, a, a, a][:-3], b)

    def test_repeated_wrapping_multiple_origin(self):
        """
        Assert that 'wrap' pads only with multiples of the original area if
        the pad width is larger than the original array.
        """
        a = np.arange(4).reshape(2, 2)
        a = np.pad(a, [(1, 3), (3, 1)], mode='wrap')
        b = np.array(
            [[3, 2, 3, 2, 3, 2],
             [1, 0, 1, 0, 1, 0],
             [3, 2, 3, 2, 3, 2],
             [1, 0, 1, 0, 1, 0],
             [3, 2, 3, 2, 3, 2],
             [1, 0, 1, 0, 1, 0]]
        )
        assert_array_equal(a, b)


class TestEdge:
    def test_check_simple(self):
        a = np.arange(12)
        a = np.reshape(a, (4, 3))
        a = np.pad(a, ((2, 3), (3, 2)), 'edge')
        b = np.array(
            [[0, 0, 0, 0, 1, 2, 2, 2],
             [0, 0, 0, 0, 1, 2, 2, 2],

             [0, 0, 0, 0, 1, 2, 2, 2],
             [3, 3, 3, 3, 4, 5, 5, 5],
             [6, 6, 6, 6, 7, 8, 8, 8],
             [9, 9, 9, 9, 10, 11, 11, 11],

             [9, 9, 9, 9, 10, 11, 11, 11],
             [9, 9, 9, 9, 10, 11, 11, 11],
             [9, 9, 9, 9, 10, 11, 11, 11]]
            )
        assert_array_equal(a, b)

    def test_check_width_shape_1_2(self):
        # Check a pad_width of the form ((1, 2),).
        # Regression test for issue gh-7808.
        a = np.array([1, 2, 3])
        padded = np.pad(a, ((1, 2),), 'edge')
        expected = np.array([1, 1, 2, 3, 3, 3])
        assert_array_equal(padded, expected)

        a = np.array([[1, 2, 3], [4, 5, 6]])
        padded = np.pad(a, ((1, 2),), 'edge')
        expected = np.pad(a, ((1, 2), (1, 2)), 'edge')
        assert_array_equal(padded, expected)

        a = np.arange(24).reshape(2, 3, 4)
        padded = np.pad(a, ((1, 2),), 'edge')
        expected = np.pad(a, ((1, 2), (1, 2), (1, 2)), 'edge')
        assert_array_equal(padded, expected)


class TestEmpty:
    def test_simple(self):
        arr = np.arange(24).reshape(4, 6)
        result = np.pad(arr, [(2, 3), (3, 1)], mode="empty")
        assert result.shape == (9, 10)
        assert_equal(arr, result[2:-3, 3:-1])

    def test_pad_empty_dimension(self):
        arr = np.zeros((3, 0, 2))
        result = np.pad(arr, [(0,), (2,), (1,)], mode="empty")
        assert result.shape == (3, 4, 4)


def test_legacy_vector_functionality():
    def _padwithtens(vector, pad_width, iaxis, kwargs):
        vector[:pad_width[0]] = 10
        vector[-pad_width[1]:] = 10

    a = np.arange(6).reshape(2, 3)
    a = np.pad(a, 2, _padwithtens)
    b = np.array(
        [[10, 10, 10, 10, 10, 10, 10],
         [10, 10, 10, 10, 10, 10, 10],

         [10, 10,  0,  1,  2, 10, 10],
         [10, 10,  3,  4,  5, 10, 10],

         [10, 10, 10, 10, 10, 10, 10],
         [10, 10, 10, 10, 10, 10, 10]]
        )
    assert_array_equal(a, b)


def test_unicode_mode():
    a = np.pad([1], 2, mode='constant')
    b = np.array([0, 0, 1, 0, 0])
    assert_array_equal(a, b)


@pytest.mark.parametrize("mode", ["edge", "symmetric", "reflect", "wrap"])
def test_object_input(mode):
    # Regression test for issue gh-11395.
    a = np.full((4, 3), fill_value=None)
    pad_amt = ((2, 3), (3, 2))
    b = np.full((9, 8), fill_value=None)
    assert_array_equal(np.pad(a, pad_amt, mode=mode), b)


class TestPadWidth:
    @pytest.mark.parametrize("pad_width", [
        (4, 5, 6, 7),
        ((1,), (2,), (3,)),
        ((1, 2), (3, 4), (5, 6)),
        ((3, 4, 5), (0, 1, 2)),
    ])
    @pytest.mark.parametrize("mode", _all_modes.keys())
    def test_misshaped_pad_width(self, pad_width, mode):
        arr = np.arange(30).reshape((6, 5))
        match = "operands could not be broadcast together"
        with pytest.raises(ValueError, match=match):
            np.pad(arr, pad_width, mode)

    @pytest.mark.parametrize("mode", _all_modes.keys())
    def test_misshaped_pad_width_2(self, mode):
        arr = np.arange(30).reshape((6, 5))
        match = ("input operand has more dimensions than allowed by the axis "
                 "remapping")
        with pytest.raises(ValueError, match=match):
            np.pad(arr, (((3,), (4,), (5,)), ((0,), (1,), (2,))), mode)

    @pytest.mark.parametrize(
        "pad_width", [-2, (-2,), (3, -1), ((5, 2), (-2, 3)), ((-4,), (2,))])
    @pytest.mark.parametrize("mode", _all_modes.keys())
    def test_negative_pad_width(self, pad_width, mode):
        arr = np.arange(30).reshape((6, 5))
        match = "index can't contain negative values"
        with pytest.raises(ValueError, match=match):
            np.pad(arr, pad_width, mode)

    @pytest.mark.parametrize("pad_width, dtype", [
        ("3", None),
        ("word", None),
        (None, None),
        (object(), None),
        (3.4, None),
        (((2, 3, 4), (3, 2)), object),
        (complex(1, -1), None),
        (((-2.1, 3), (3, 2)), None),
    ])
    @pytest.mark.parametrize("mode", _all_modes.keys())
    def test_bad_type(self, pad_width, dtype, mode):
        arr = np.arange(30).reshape((6, 5))
        match = "`pad_width` must be of integral type."
        if dtype is not None:
            # avoid DeprecationWarning when not specifying dtype
            with pytest.raises(TypeError, match=match):
                np.pad(arr, np.array(pad_width, dtype=dtype), mode)
        else:
            with pytest.raises(TypeError, match=match):
                np.pad(arr, pad_width, mode)
            with pytest.raises(TypeError, match=match):
                np.pad(arr, np.array(pad_width), mode)

    def test_pad_width_as_ndarray(self):
        a = np.arange(12)
        a = np.reshape(a, (4, 3))
        a = np.pad(a, np.array(((2, 3), (3, 2))), 'edge')
        b = np.array(
            [[0,  0,  0,    0,  1,  2,    2,  2],
             [0,  0,  0,    0,  1,  2,    2,  2],

             [0,  0,  0,    0,  1,  2,    2,  2],
             [3,  3,  3,    3,  4,  5,    5,  5],
             [6,  6,  6,    6,  7,  8,    8,  8],
             [9,  9,  9,    9, 10, 11,   11, 11],

             [9,  9,  9,    9, 10, 11,   11, 11],
             [9,  9,  9,    9, 10, 11,   11, 11],
             [9,  9,  9,    9, 10, 11,   11, 11]]
            )
        assert_array_equal(a, b)

    @pytest.mark.parametrize("pad_width", [0, (0, 0), ((0, 0), (0, 0))])
    @pytest.mark.parametrize("mode", _all_modes.keys())
    def test_zero_pad_width(self, pad_width, mode):
        arr = np.arange(30).reshape(6, 5)
        assert_array_equal(arr, np.pad(arr, pad_width, mode=mode))


@pytest.mark.parametrize("mode", _all_modes.keys())
def test_kwargs(mode):
    """Test behavior of pad's kwargs for the given mode."""
    allowed = _all_modes[mode]
    not_allowed = {}
    for kwargs in _all_modes.values():
        if kwargs != allowed:
            not_allowed.update(kwargs)
    # Test if allowed keyword arguments pass
    np.pad([1, 2, 3], 1, mode, **allowed)
    # Test if prohibited keyword arguments of other modes raise an error
    for key, value in not_allowed.items():
        match = f"unsupported keyword arguments for mode '{mode}'"
        with pytest.raises(ValueError, match=match):
            np.pad([1, 2, 3], 1, mode, **{key: value})


def test_constant_zero_default():
    arr = np.array([1, 1])
    assert_array_equal(np.pad(arr, 2), [0, 0, 1, 1, 0, 0])


@pytest.mark.parametrize("mode", [1, "const", object(), None, True, False])
def test_unsupported_mode(mode):
    match = f"mode '{mode}' is not supported"
    with pytest.raises(ValueError, match=match):
        np.pad([1, 2, 3], 4, mode=mode)


@pytest.mark.parametrize("mode", _all_modes.keys())
def test_non_contiguous_array(mode):
    arr = np.arange(24).reshape(4, 6)[::2, ::2]
    result = np.pad(arr, (2, 3), mode)
    assert result.shape == (7, 8)
    assert_equal(result[2:-3, 2:-3], arr)


@pytest.mark.parametrize("mode", _all_modes.keys())
def test_memory_layout_persistence(mode):
    """Test if C and F order is preserved for all pad modes."""
    x = np.ones((5, 10), order='C')
    assert np.pad(x, 5, mode).flags["C_CONTIGUOUS"]
    x = np.ones((5, 10), order='F')
    assert np.pad(x, 5, mode).flags["F_CONTIGUOUS"]


@pytest.mark.parametrize("dtype", _numeric_dtypes)
@pytest.mark.parametrize("mode", _all_modes.keys())
def test_dtype_persistence(dtype, mode):
    arr = np.zeros((3, 2, 1), dtype=dtype)
    result = np.pad(arr, 1, mode=mode)
    assert result.dtype == dtype

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\tests\test_arraypad.py ===
"""Tests for the array padding functions.

"""
import pytest

import numpy as np
from numpy.lib._arraypad_impl import _as_pairs
from numpy.testing import assert_allclose, assert_array_equal, assert_equal

_numeric_dtypes = (
    np._core.sctypes["uint"]
    + np._core.sctypes["int"]
    + np._core.sctypes["float"]
    + np._core.sctypes["complex"]
)
_all_modes = {
    'constant': {'constant_values': 0},
    'edge': {},
    'linear_ramp': {'end_values': 0},
    'maximum': {'stat_length': None},
    'mean': {'stat_length': None},
    'median': {'stat_length': None},
    'minimum': {'stat_length': None},
    'reflect': {'reflect_type': 'even'},
    'symmetric': {'reflect_type': 'even'},
    'wrap': {},
    'empty': {}
}


class TestAsPairs:
    def test_single_value(self):
        """Test casting for a single value."""
        expected = np.array([[3, 3]] * 10)
        for x in (3, [3], [[3]]):
            result = _as_pairs(x, 10)
            assert_equal(result, expected)
        # Test with dtype=object
        obj = object()
        assert_equal(
            _as_pairs(obj, 10),
            np.array([[obj, obj]] * 10)
        )

    def test_two_values(self):
        """Test proper casting for two different values."""
        # Broadcasting in the first dimension with numbers
        expected = np.array([[3, 4]] * 10)
        for x in ([3, 4], [[3, 4]]):
            result = _as_pairs(x, 10)
            assert_equal(result, expected)
        # and with dtype=object
        obj = object()
        assert_equal(
            _as_pairs(["a", obj], 10),
            np.array([["a", obj]] * 10)
        )

        # Broadcasting in the second / last dimension with numbers
        assert_equal(
            _as_pairs([[3], [4]], 2),
            np.array([[3, 3], [4, 4]])
        )
        # and with dtype=object
        assert_equal(
            _as_pairs([["a"], [obj]], 2),
            np.array([["a", "a"], [obj, obj]])
        )

    def test_with_none(self):
        expected = ((None, None), (None, None), (None, None))
        assert_equal(
            _as_pairs(None, 3, as_index=False),
            expected
        )
        assert_equal(
            _as_pairs(None, 3, as_index=True),
            expected
        )

    def test_pass_through(self):
        """Test if `x` already matching desired output are passed through."""
        expected = np.arange(12).reshape((6, 2))
        assert_equal(
            _as_pairs(expected, 6),
            expected
        )

    def test_as_index(self):
        """Test results if `as_index=True`."""
        assert_equal(
            _as_pairs([2.6, 3.3], 10, as_index=True),
            np.array([[3, 3]] * 10, dtype=np.intp)
        )
        assert_equal(
            _as_pairs([2.6, 4.49], 10, as_index=True),
            np.array([[3, 4]] * 10, dtype=np.intp)
        )
        for x in (-3, [-3], [[-3]], [-3, 4], [3, -4], [[-3, 4]], [[4, -3]],
                  [[1, 2]] * 9 + [[1, -2]]):
            with pytest.raises(ValueError, match="negative values"):
                _as_pairs(x, 10, as_index=True)

    def test_exceptions(self):
        """Ensure faulty usage is discovered."""
        with pytest.raises(ValueError, match="more dimensions than allowed"):
            _as_pairs([[[3]]], 10)
        with pytest.raises(ValueError, match="could not be broadcast"):
            _as_pairs([[1, 2], [3, 4]], 3)
        with pytest.raises(ValueError, match="could not be broadcast"):
            _as_pairs(np.ones((2, 3)), 3)


class TestConditionalShortcuts:
    @pytest.mark.parametrize("mode", _all_modes.keys())
    def test_zero_padding_shortcuts(self, mode):
        test = np.arange(120).reshape(4, 5, 6)
        pad_amt = [(0, 0) for _ in test.shape]
        assert_array_equal(test, np.pad(test, pad_amt, mode=mode))

    @pytest.mark.parametrize("mode", ['maximum', 'mean', 'median', 'minimum',])
    def test_shallow_statistic_range(self, mode):
        test = np.arange(120).reshape(4, 5, 6)
        pad_amt = [(1, 1) for _ in test.shape]
        assert_array_equal(np.pad(test, pad_amt, mode='edge'),
                           np.pad(test, pad_amt, mode=mode, stat_length=1))

    @pytest.mark.parametrize("mode", ['maximum', 'mean', 'median', 'minimum',])
    def test_clip_statistic_range(self, mode):
        test = np.arange(30).reshape(5, 6)
        pad_amt = [(3, 3) for _ in test.shape]
        assert_array_equal(np.pad(test, pad_amt, mode=mode),
                           np.pad(test, pad_amt, mode=mode, stat_length=30))


class TestStatistic:
    def test_check_mean_stat_length(self):
        a = np.arange(100).astype('f')
        a = np.pad(a, ((25, 20), ), 'mean', stat_length=((2, 3), ))
        b = np.array(
            [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5,
             0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5,
             0.5, 0.5, 0.5, 0.5, 0.5,

             0., 1., 2., 3., 4., 5., 6., 7., 8., 9.,
             10., 11., 12., 13., 14., 15., 16., 17., 18., 19.,
             20., 21., 22., 23., 24., 25., 26., 27., 28., 29.,
             30., 31., 32., 33., 34., 35., 36., 37., 38., 39.,
             40., 41., 42., 43., 44., 45., 46., 47., 48., 49.,
             50., 51., 52., 53., 54., 55., 56., 57., 58., 59.,
             60., 61., 62., 63., 64., 65., 66., 67., 68., 69.,
             70., 71., 72., 73., 74., 75., 76., 77., 78., 79.,
             80., 81., 82., 83., 84., 85., 86., 87., 88., 89.,
             90., 91., 92., 93., 94., 95., 96., 97., 98., 99.,

             98., 98., 98., 98., 98., 98., 98., 98., 98., 98.,
             98., 98., 98., 98., 98., 98., 98., 98., 98., 98.
             ])
        assert_array_equal(a, b)

    def test_check_maximum_1(self):
        a = np.arange(100)
        a = np.pad(a, (25, 20), 'maximum')
        b = np.array(
            [99, 99, 99, 99, 99, 99, 99, 99, 99, 99,
             99, 99, 99, 99, 99, 99, 99, 99, 99, 99,
             99, 99, 99, 99, 99,

             0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
             20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
             30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
             40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
             50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
             60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
             70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
             80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
             90, 91, 92, 93, 94, 95, 96, 97, 98, 99,

             99, 99, 99, 99, 99, 99, 99, 99, 99, 99,
             99, 99, 99, 99, 99, 99, 99, 99, 99, 99]
            )
        assert_array_equal(a, b)

    def test_check_maximum_2(self):
        a = np.arange(100) + 1
        a = np.pad(a, (25, 20), 'maximum')
        b = np.array(
            [100, 100, 100, 100, 100, 100, 100, 100, 100, 100,
             100, 100, 100, 100, 100, 100, 100, 100, 100, 100,
             100, 100, 100, 100, 100,

             1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
             11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
             21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
             31, 32, 33, 34, 35, 36, 37, 38, 39, 40,
             41, 42, 43, 44, 45, 46, 47, 48, 49, 50,
             51, 52, 53, 54, 55, 56, 57, 58, 59, 60,
             61, 62, 63, 64, 65, 66, 67, 68, 69, 70,
             71, 72, 73, 74, 75, 76, 77, 78, 79, 80,
             81, 82, 83, 84, 85, 86, 87, 88, 89, 90,
             91, 92, 93, 94, 95, 96, 97, 98, 99, 100,

             100, 100, 100, 100, 100, 100, 100, 100, 100, 100,
             100, 100, 100, 100, 100, 100, 100, 100, 100, 100]
            )
        assert_array_equal(a, b)

    def test_check_maximum_stat_length(self):
        a = np.arange(100) + 1
        a = np.pad(a, (25, 20), 'maximum', stat_length=10)
        b = np.array(
            [10, 10, 10, 10, 10, 10, 10, 10, 10, 10,
             10, 10, 10, 10, 10, 10, 10, 10, 10, 10,
             10, 10, 10, 10, 10,

              1,  2,  3,  4,  5,  6,  7,  8,  9, 10,
             11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
             21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
             31, 32, 33, 34, 35, 36, 37, 38, 39, 40,
             41, 42, 43, 44, 45, 46, 47, 48, 49, 50,
             51, 52, 53, 54, 55, 56, 57, 58, 59, 60,
             61, 62, 63, 64, 65, 66, 67, 68, 69, 70,
             71, 72, 73, 74, 75, 76, 77, 78, 79, 80,
             81, 82, 83, 84, 85, 86, 87, 88, 89, 90,
             91, 92, 93, 94, 95, 96, 97, 98, 99, 100,

             100, 100, 100, 100, 100, 100, 100, 100, 100, 100,
             100, 100, 100, 100, 100, 100, 100, 100, 100, 100]
            )
        assert_array_equal(a, b)

    def test_check_minimum_1(self):
        a = np.arange(100)
        a = np.pad(a, (25, 20), 'minimum')
        b = np.array(
            [ 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
              0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
              0,  0,  0,  0,  0,

              0,  1,  2,  3,  4,  5,  6,  7,  8,  9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
             20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
             30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
             40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
             50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
             60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
             70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
             80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
             90, 91, 92, 93, 94, 95, 96, 97, 98, 99,

             0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
             0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            )
        assert_array_equal(a, b)

    def test_check_minimum_2(self):
        a = np.arange(100) + 2
        a = np.pad(a, (25, 20), 'minimum')
        b = np.array(
            [ 2,  2,  2,  2,  2,  2,  2,  2,  2,  2,
              2,  2,  2,  2,  2,  2,  2,  2,  2,  2,
              2,  2,  2,  2,  2,

              2,  3,  4,  5,  6,  7,  8,  9, 10, 11,
             12, 13, 14, 15, 16, 17, 18, 19, 20, 21,
             22, 23, 24, 25, 26, 27, 28, 29, 30, 31,
             32, 33, 34, 35, 36, 37, 38, 39, 40, 41,
             42, 43, 44, 45, 46, 47, 48, 49, 50, 51,
             52, 53, 54, 55, 56, 57, 58, 59, 60, 61,
             62, 63, 64, 65, 66, 67, 68, 69, 70, 71,
             72, 73, 74, 75, 76, 77, 78, 79, 80, 81,
             82, 83, 84, 85, 86, 87, 88, 89, 90, 91,
             92, 93, 94, 95, 96, 97, 98, 99, 100, 101,

             2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
             2, 2, 2, 2, 2, 2, 2, 2, 2, 2]
            )
        assert_array_equal(a, b)

    def test_check_minimum_stat_length(self):
        a = np.arange(100) + 1
        a = np.pad(a, (25, 20), 'minimum', stat_length=10)
        b = np.array(
            [ 1,  1,  1,  1,  1,  1,  1,  1,  1,  1,
              1,  1,  1,  1,  1,  1,  1,  1,  1,  1,
              1,  1,  1,  1,  1,

              1,  2,  3,  4,  5,  6,  7,  8,  9, 10,
             11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
             21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
             31, 32, 33, 34, 35, 36, 37, 38, 39, 40,
             41, 42, 43, 44, 45, 46, 47, 48, 49, 50,
             51, 52, 53, 54, 55, 56, 57, 58, 59, 60,
             61, 62, 63, 64, 65, 66, 67, 68, 69, 70,
             71, 72, 73, 74, 75, 76, 77, 78, 79, 80,
             81, 82, 83, 84, 85, 86, 87, 88, 89, 90,
             91, 92, 93, 94, 95, 96, 97, 98, 99, 100,

             91, 91, 91, 91, 91, 91, 91, 91, 91, 91,
             91, 91, 91, 91, 91, 91, 91, 91, 91, 91]
            )
        assert_array_equal(a, b)

    def test_check_median(self):
        a = np.arange(100).astype('f')
        a = np.pad(a, (25, 20), 'median')
        b = np.array(
            [49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5,
             49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5,
             49.5, 49.5, 49.5, 49.5, 49.5,

             0., 1., 2., 3., 4., 5., 6., 7., 8., 9.,
             10., 11., 12., 13., 14., 15., 16., 17., 18., 19.,
             20., 21., 22., 23., 24., 25., 26., 27., 28., 29.,
             30., 31., 32., 33., 34., 35., 36., 37., 38., 39.,
             40., 41., 42., 43., 44., 45., 46., 47., 48., 49.,
             50., 51., 52., 53., 54., 55., 56., 57., 58., 59.,
             60., 61., 62., 63., 64., 65., 66., 67., 68., 69.,
             70., 71., 72., 73., 74., 75., 76., 77., 78., 79.,
             80., 81., 82., 83., 84., 85., 86., 87., 88., 89.,
             90., 91., 92., 93., 94., 95., 96., 97., 98., 99.,

             49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5,
             49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5]
            )
        assert_array_equal(a, b)

    def test_check_median_01(self):
        a = np.array([[3, 1, 4], [4, 5, 9], [9, 8, 2]])
        a = np.pad(a, 1, 'median')
        b = np.array(
            [[4, 4, 5, 4, 4],

             [3, 3, 1, 4, 3],
             [5, 4, 5, 9, 5],
             [8, 9, 8, 2, 8],

             [4, 4, 5, 4, 4]]
            )
        assert_array_equal(a, b)

    def test_check_median_02(self):
        a = np.array([[3, 1, 4], [4, 5, 9], [9, 8, 2]])
        a = np.pad(a.T, 1, 'median').T
        b = np.array(
            [[5, 4, 5, 4, 5],

             [3, 3, 1, 4, 3],
             [5, 4, 5, 9, 5],
             [8, 9, 8, 2, 8],

             [5, 4, 5, 4, 5]]
            )
        assert_array_equal(a, b)

    def test_check_median_stat_length(self):
        a = np.arange(100).astype('f')
        a[1] = 2.
        a[97] = 96.
        a = np.pad(a, (25, 20), 'median', stat_length=(3, 5))
        b = np.array(
            [ 2.,  2.,  2.,  2.,  2.,  2.,  2.,  2.,  2.,  2.,
              2.,  2.,  2.,  2.,  2.,  2.,  2.,  2.,  2.,  2.,
              2.,  2.,  2.,  2.,  2.,

              0.,  2.,  2.,  3.,  4.,  5.,  6.,  7.,  8.,  9.,
             10., 11., 12., 13., 14., 15., 16., 17., 18., 19.,
             20., 21., 22., 23., 24., 25., 26., 27., 28., 29.,
             30., 31., 32., 33., 34., 35., 36., 37., 38., 39.,
             40., 41., 42., 43., 44., 45., 46., 47., 48., 49.,
             50., 51., 52., 53., 54., 55., 56., 57., 58., 59.,
             60., 61., 62., 63., 64., 65., 66., 67., 68., 69.,
             70., 71., 72., 73., 74., 75., 76., 77., 78., 79.,
             80., 81., 82., 83., 84., 85., 86., 87., 88., 89.,
             90., 91., 92., 93., 94., 95., 96., 96., 98., 99.,

             96., 96., 96., 96., 96., 96., 96., 96., 96., 96.,
             96., 96., 96., 96., 96., 96., 96., 96., 96., 96.]
            )
        assert_array_equal(a, b)

    def test_check_mean_shape_one(self):
        a = [[4, 5, 6]]
        a = np.pad(a, (5, 7), 'mean', stat_length=2)
        b = np.array(
            [[4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],
             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],
             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],
             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],
             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],

             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],

             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],
             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],
             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],
             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],
             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],
             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],
             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6]]
            )
        assert_array_equal(a, b)

    def test_check_mean_2(self):
        a = np.arange(100).astype('f')
        a = np.pad(a, (25, 20), 'mean')
        b = np.array(
            [49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5,
             49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5,
             49.5, 49.5, 49.5, 49.5, 49.5,

             0., 1., 2., 3., 4., 5., 6., 7., 8., 9.,
             10., 11., 12., 13., 14., 15., 16., 17., 18., 19.,
             20., 21., 22., 23., 24., 25., 26., 27., 28., 29.,
             30., 31., 32., 33., 34., 35., 36., 37., 38., 39.,
             40., 41., 42., 43., 44., 45., 46., 47., 48., 49.,
             50., 51., 52., 53., 54., 55., 56., 57., 58., 59.,
             60., 61., 62., 63., 64., 65., 66., 67., 68., 69.,
             70., 71., 72., 73., 74., 75., 76., 77., 78., 79.,
             80., 81., 82., 83., 84., 85., 86., 87., 88., 89.,
             90., 91., 92., 93., 94., 95., 96., 97., 98., 99.,

             49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5,
             49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5]
            )
        assert_array_equal(a, b)

    @pytest.mark.parametrize("mode", [
        "mean",
        "median",
        "minimum",
        "maximum"
    ])
    def test_same_prepend_append(self, mode):
        """ Test that appended and prepended values are equal """
        # This test is constructed to trigger floating point rounding errors in
        # a way that caused gh-11216 for mode=='mean'
        a = np.array([-1, 2, -1]) + np.array([0, 1e-12, 0], dtype=np.float64)
        a = np.pad(a, (1, 1), mode)
        assert_equal(a[0], a[-1])

    @pytest.mark.parametrize("mode", ["mean", "median", "minimum", "maximum"])
    @pytest.mark.parametrize(
        "stat_length", [-2, (-2,), (3, -1), ((5, 2), (-2, 3)), ((-4,), (2,))]
    )
    def test_check_negative_stat_length(self, mode, stat_length):
        arr = np.arange(30).reshape((6, 5))
        match = "index can't contain negative values"
        with pytest.raises(ValueError, match=match):
            np.pad(arr, 2, mode, stat_length=stat_length)

    def test_simple_stat_length(self):
        a = np.arange(30)
        a = np.reshape(a, (6, 5))
        a = np.pad(a, ((2, 3), (3, 2)), mode='mean', stat_length=(3,))
        b = np.array(
            [[6, 6, 6, 5, 6, 7, 8, 9, 8, 8],
             [6, 6, 6, 5, 6, 7, 8, 9, 8, 8],

             [1, 1, 1, 0, 1, 2, 3, 4, 3, 3],
             [6, 6, 6, 5, 6, 7, 8, 9, 8, 8],
             [11, 11, 11, 10, 11, 12, 13, 14, 13, 13],
             [16, 16, 16, 15, 16, 17, 18, 19, 18, 18],
             [21, 21, 21, 20, 21, 22, 23, 24, 23, 23],
             [26, 26, 26, 25, 26, 27, 28, 29, 28, 28],

             [21, 21, 21, 20, 21, 22, 23, 24, 23, 23],
             [21, 21, 21, 20, 21, 22, 23, 24, 23, 23],
             [21, 21, 21, 20, 21, 22, 23, 24, 23, 23]]
            )
        assert_array_equal(a, b)

    @pytest.mark.filterwarnings("ignore:Mean of empty slice:RuntimeWarning")
    @pytest.mark.filterwarnings(
        "ignore:invalid value encountered in( scalar)? divide:RuntimeWarning"
    )
    @pytest.mark.parametrize("mode", ["mean", "median"])
    def test_zero_stat_length_valid(self, mode):
        arr = np.pad([1., 2.], (1, 2), mode, stat_length=0)
        expected = np.array([np.nan, 1., 2., np.nan, np.nan])
        assert_equal(arr, expected)

    @pytest.mark.parametrize("mode", ["minimum", "maximum"])
    def test_zero_stat_length_invalid(self, mode):
        match = "stat_length of 0 yields no value for padding"
        with pytest.raises(ValueError, match=match):
            np.pad([1., 2.], 0, mode, stat_length=0)
        with pytest.raises(ValueError, match=match):
            np.pad([1., 2.], 0, mode, stat_length=(1, 0))
        with pytest.raises(ValueError, match=match):
            np.pad([1., 2.], 1, mode, stat_length=0)
        with pytest.raises(ValueError, match=match):
            np.pad([1., 2.], 1, mode, stat_length=(1, 0))


class TestConstant:
    def test_check_constant(self):
        a = np.arange(100)
        a = np.pad(a, (25, 20), 'constant', constant_values=(10, 20))
        b = np.array(
            [10, 10, 10, 10, 10, 10, 10, 10, 10, 10,
             10, 10, 10, 10, 10, 10, 10, 10, 10, 10,
             10, 10, 10, 10, 10,

             0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
             20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
             30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
             40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
             50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
             60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
             70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
             80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
             90, 91, 92, 93, 94, 95, 96, 97, 98, 99,

             20, 20, 20, 20, 20, 20, 20, 20, 20, 20,
             20, 20, 20, 20, 20, 20, 20, 20, 20, 20]
            )
        assert_array_equal(a, b)

    def test_check_constant_zeros(self):
        a = np.arange(100)
        a = np.pad(a, (25, 20), 'constant')
        b = np.array(
            [ 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
              0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
              0,  0,  0,  0,  0,

             0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
             20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
             30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
             40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
             50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
             60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
             70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
             80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
             90, 91, 92, 93, 94, 95, 96, 97, 98, 99,

              0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
              0,  0,  0,  0,  0,  0,  0,  0,  0,  0]
            )
        assert_array_equal(a, b)

    def test_check_constant_float(self):
        # If input array is int, but constant_values are float, the dtype of
        # the array to be padded is kept
        arr = np.arange(30).reshape(5, 6)
        test = np.pad(arr, (1, 2), mode='constant',
                   constant_values=1.1)
        expected = np.array(
            [[1,  1,  1,  1,  1,  1,  1,  1,  1],

             [1,  0,  1,  2,  3,  4,  5,  1,  1],
             [1,  6,  7,  8,  9, 10, 11,  1,  1],
             [1, 12, 13, 14, 15, 16, 17,  1,  1],
             [1, 18, 19, 20, 21, 22, 23,  1,  1],
             [1, 24, 25, 26, 27, 28, 29,  1,  1],

             [1,  1,  1,  1,  1,  1,  1,  1,  1],
             [1,  1,  1,  1,  1,  1,  1,  1,  1]]
            )
        assert_allclose(test, expected)

    def test_check_constant_float2(self):
        # If input array is float, and constant_values are float, the dtype of
        # the array to be padded is kept - here retaining the float constants
        arr = np.arange(30).reshape(5, 6)
        arr_float = arr.astype(np.float64)
        test = np.pad(arr_float, ((1, 2), (1, 2)), mode='constant',
                   constant_values=1.1)
        expected = np.array(
            [[1.1,   1.1,   1.1,   1.1,   1.1,   1.1,   1.1,   1.1,   1.1],

             [1.1,   0. ,   1. ,   2. ,   3. ,   4. ,   5. ,   1.1,   1.1],  # noqa: E203
             [1.1,   6. ,   7. ,   8. ,   9. ,  10. ,  11. ,   1.1,   1.1],  # noqa: E203
             [1.1,  12. ,  13. ,  14. ,  15. ,  16. ,  17. ,   1.1,   1.1],  # noqa: E203
             [1.1,  18. ,  19. ,  20. ,  21. ,  22. ,  23. ,   1.1,   1.1],  # noqa: E203
             [1.1,  24. ,  25. ,  26. ,  27. ,  28. ,  29. ,   1.1,   1.1],  # noqa: E203

             [1.1,   1.1,   1.1,   1.1,   1.1,   1.1,   1.1,   1.1,   1.1],
             [1.1,   1.1,   1.1,   1.1,   1.1,   1.1,   1.1,   1.1,   1.1]]
            )
        assert_allclose(test, expected)

    def test_check_constant_float3(self):
        a = np.arange(100, dtype=float)
        a = np.pad(a, (25, 20), 'constant', constant_values=(-1.1, -1.2))
        b = np.array(
            [-1.1, -1.1, -1.1, -1.1, -1.1, -1.1, -1.1, -1.1, -1.1, -1.1,
             -1.1, -1.1, -1.1, -1.1, -1.1, -1.1, -1.1, -1.1, -1.1, -1.1,
             -1.1, -1.1, -1.1, -1.1, -1.1,

             0,  1,  2,  3,  4,  5,  6,  7,  8,  9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
             20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
             30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
             40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
             50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
             60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
             70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
             80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
             90, 91, 92, 93, 94, 95, 96, 97, 98, 99,

             -1.2, -1.2, -1.2, -1.2, -1.2, -1.2, -1.2, -1.2, -1.2, -1.2,
             -1.2, -1.2, -1.2, -1.2, -1.2, -1.2, -1.2, -1.2, -1.2, -1.2]
            )
        assert_allclose(a, b)

    def test_check_constant_odd_pad_amount(self):
        arr = np.arange(30).reshape(5, 6)
        test = np.pad(arr, ((1,), (2,)), mode='constant',
                   constant_values=3)
        expected = np.array(
            [[3,  3,  3,  3,  3,  3,  3,  3,  3,  3],

             [3,  3,  0,  1,  2,  3,  4,  5,  3,  3],
             [3,  3,  6,  7,  8,  9, 10, 11,  3,  3],
             [3,  3, 12, 13, 14, 15, 16, 17,  3,  3],
             [3,  3, 18, 19, 20, 21, 22, 23,  3,  3],
             [3,  3, 24, 25, 26, 27, 28, 29,  3,  3],

             [3,  3,  3,  3,  3,  3,  3,  3,  3,  3]]
            )
        assert_allclose(test, expected)

    def test_check_constant_pad_2d(self):
        arr = np.arange(4).reshape(2, 2)
        test = np.pad(arr, ((1, 2), (1, 3)), mode='constant',
                          constant_values=((1, 2), (3, 4)))
        expected = np.array(
            [[3, 1, 1, 4, 4, 4],
             [3, 0, 1, 4, 4, 4],
             [3, 2, 3, 4, 4, 4],
             [3, 2, 2, 4, 4, 4],
             [3, 2, 2, 4, 4, 4]]
        )
        assert_allclose(test, expected)

    def test_check_large_integers(self):
        uint64_max = 2 ** 64 - 1
        arr = np.full(5, uint64_max, dtype=np.uint64)
        test = np.pad(arr, 1, mode="constant", constant_values=arr.min())
        expected = np.full(7, uint64_max, dtype=np.uint64)
        assert_array_equal(test, expected)

        int64_max = 2 ** 63 - 1
        arr = np.full(5, int64_max, dtype=np.int64)
        test = np.pad(arr, 1, mode="constant", constant_values=arr.min())
        expected = np.full(7, int64_max, dtype=np.int64)
        assert_array_equal(test, expected)

    def test_check_object_array(self):
        arr = np.empty(1, dtype=object)
        obj_a = object()
        arr[0] = obj_a
        obj_b = object()
        obj_c = object()
        arr = np.pad(arr, pad_width=1, mode='constant',
                     constant_values=(obj_b, obj_c))

        expected = np.empty((3,), dtype=object)
        expected[0] = obj_b
        expected[1] = obj_a
        expected[2] = obj_c

        assert_array_equal(arr, expected)

    def test_pad_empty_dimension(self):
        arr = np.zeros((3, 0, 2))
        result = np.pad(arr, [(0,), (2,), (1,)], mode="constant")
        assert result.shape == (3, 4, 4)


class TestLinearRamp:
    def test_check_simple(self):
        a = np.arange(100).astype('f')
        a = np.pad(a, (25, 20), 'linear_ramp', end_values=(4, 5))
        b = np.array(
            [4.00, 3.84, 3.68, 3.52, 3.36, 3.20, 3.04, 2.88, 2.72, 2.56,
             2.40, 2.24, 2.08, 1.92, 1.76, 1.60, 1.44, 1.28, 1.12, 0.96,
             0.80, 0.64, 0.48, 0.32, 0.16,

             0.00, 1.00, 2.00, 3.00, 4.00, 5.00, 6.00, 7.00, 8.00, 9.00,
             10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0,
             20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0, 29.0,
             30.0, 31.0, 32.0, 33.0, 34.0, 35.0, 36.0, 37.0, 38.0, 39.0,
             40.0, 41.0, 42.0, 43.0, 44.0, 45.0, 46.0, 47.0, 48.0, 49.0,
             50.0, 51.0, 52.0, 53.0, 54.0, 55.0, 56.0, 57.0, 58.0, 59.0,
             60.0, 61.0, 62.0, 63.0, 64.0, 65.0, 66.0, 67.0, 68.0, 69.0,
             70.0, 71.0, 72.0, 73.0, 74.0, 75.0, 76.0, 77.0, 78.0, 79.0,
             80.0, 81.0, 82.0, 83.0, 84.0, 85.0, 86.0, 87.0, 88.0, 89.0,
             90.0, 91.0, 92.0, 93.0, 94.0, 95.0, 96.0, 97.0, 98.0, 99.0,

             94.3, 89.6, 84.9, 80.2, 75.5, 70.8, 66.1, 61.4, 56.7, 52.0,
             47.3, 42.6, 37.9, 33.2, 28.5, 23.8, 19.1, 14.4, 9.7, 5.]
            )
        assert_allclose(a, b, rtol=1e-5, atol=1e-5)

    def test_check_2d(self):
        arr = np.arange(20).reshape(4, 5).astype(np.float64)
        test = np.pad(arr, (2, 2), mode='linear_ramp', end_values=(0, 0))
        expected = np.array(
            [[0.,   0.,   0.,   0.,   0.,   0.,   0.,    0.,   0.],
             [0.,   0.,   0.,  0.5,   1.,  1.5,   2.,    1.,   0.],
             [0.,   0.,   0.,   1.,   2.,   3.,   4.,    2.,   0.],
             [0.,  2.5,   5.,   6.,   7.,   8.,   9.,   4.5,   0.],
             [0.,   5.,  10.,  11.,  12.,  13.,  14.,    7.,   0.],
             [0.,  7.5,  15.,  16.,  17.,  18.,  19.,   9.5,   0.],
             [0., 3.75,  7.5,   8.,  8.5,   9.,  9.5,  4.75,   0.],
             [0.,   0.,   0.,   0.,   0.,   0.,   0.,    0.,   0.]])
        assert_allclose(test, expected)

    @pytest.mark.xfail(exceptions=(AssertionError,))
    def test_object_array(self):
        from fractions import Fraction
        arr = np.array([Fraction(1, 2), Fraction(-1, 2)])
        actual = np.pad(arr, (2, 3), mode='linear_ramp', end_values=0)

        # deliberately chosen to have a non-power-of-2 denominator such that
        # rounding to floats causes a failure.
        expected = np.array([
            Fraction( 0, 12),
            Fraction( 3, 12),
            Fraction( 6, 12),
            Fraction(-6, 12),
            Fraction(-4, 12),
            Fraction(-2, 12),
            Fraction(-0, 12),
        ])
        assert_equal(actual, expected)

    def test_end_values(self):
        """Ensure that end values are exact."""
        a = np.pad(np.ones(10).reshape(2, 5), (223, 123), mode="linear_ramp")
        assert_equal(a[:, 0], 0.)
        assert_equal(a[:, -1], 0.)
        assert_equal(a[0, :], 0.)
        assert_equal(a[-1, :], 0.)

    @pytest.mark.parametrize("dtype", _numeric_dtypes)
    def test_negative_difference(self, dtype):
        """
        Check correct behavior of unsigned dtypes if there is a negative
        difference between the edge to pad and `end_values`. Check both cases
        to be independent of implementation. Test behavior for all other dtypes
        in case dtype casting interferes with complex dtypes. See gh-14191.
        """
        x = np.array([3], dtype=dtype)
        result = np.pad(x, 3, mode="linear_ramp", end_values=0)
        expected = np.array([0, 1, 2, 3, 2, 1, 0], dtype=dtype)
        assert_equal(result, expected)

        x = np.array([0], dtype=dtype)
        result = np.pad(x, 3, mode="linear_ramp", end_values=3)
        expected = np.array([3, 2, 1, 0, 1, 2, 3], dtype=dtype)
        assert_equal(result, expected)


class TestReflect:
    def test_check_simple(self):
        a = np.arange(100)
        a = np.pad(a, (25, 20), 'reflect')
        b = np.array(
            [25, 24, 23, 22, 21, 20, 19, 18, 17, 16,
             15, 14, 13, 12, 11, 10, 9, 8, 7, 6,
             5, 4, 3, 2, 1,

             0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
             20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
             30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
             40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
             50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
             60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
             70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
             80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
             90, 91, 92, 93, 94, 95, 96, 97, 98, 99,

             98, 97, 96, 95, 94, 93, 92, 91, 90, 89,
             88, 87, 86, 85, 84, 83, 82, 81, 80, 79]
            )
        assert_array_equal(a, b)

    def test_check_odd_method(self):
        a = np.arange(100)
        a = np.pad(a, (25, 20), 'reflect', reflect_type='odd')
        b = np.array(
            [-25, -24, -23, -22, -21, -20, -19, -18, -17, -16,
             -15, -14, -13, -12, -11, -10, -9, -8, -7, -6,
             -5, -4, -3, -2, -1,

             0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
             20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
             30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
             40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
             50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
             60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
             70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
             80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
             90, 91, 92, 93, 94, 95, 96, 97, 98, 99,

             100, 101, 102, 103, 104, 105, 106, 107, 108, 109,
             110, 111, 112, 113, 114, 115, 116, 117, 118, 119]
            )
        assert_array_equal(a, b)

    def test_check_large_pad(self):
        a = [[4, 5, 6], [6, 7, 8]]
        a = np.pad(a, (5, 7), 'reflect')
        b = np.array(
            [[7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7],

             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7],

             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5]]
            )
        assert_array_equal(a, b)

    def test_check_shape(self):
        a = [[4, 5, 6]]
        a = np.pad(a, (5, 7), 'reflect')
        b = np.array(
            [[5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],

             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],

             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5]]
            )
        assert_array_equal(a, b)

    def test_check_01(self):
        a = np.pad([1, 2, 3], 2, 'reflect')
        b = np.array([3, 2, 1, 2, 3, 2, 1])
        assert_array_equal(a, b)

    def test_check_02(self):
        a = np.pad([1, 2, 3], 3, 'reflect')
        b = np.array([2, 3, 2, 1, 2, 3, 2, 1, 2])
        assert_array_equal(a, b)

    def test_check_03(self):
        a = np.pad([1, 2, 3], 4, 'reflect')
        b = np.array([1, 2, 3, 2, 1, 2, 3, 2, 1, 2, 3])
        assert_array_equal(a, b)

    def test_check_04(self):
        a = np.pad([1, 2, 3], [1, 10], 'reflect')
        b = np.array([2, 1, 2, 3, 2, 1, 2, 3, 2, 1, 2, 3, 2, 1])
        assert_array_equal(a, b)

    def test_check_05(self):
        a = np.pad([1, 2, 3, 4], [45, 10], 'reflect')
        b = np.array(
            [4, 3, 2, 1, 2, 3, 4, 3, 2, 1,
             2, 3, 4, 3, 2, 1, 2, 3, 4, 3,
             2, 1, 2, 3, 4, 3, 2, 1, 2, 3,
             4, 3, 2, 1, 2, 3, 4, 3, 2, 1,
             2, 3, 4, 3, 2, 1, 2, 3, 4, 3,
             2, 1, 2, 3, 4, 3, 2, 1, 2])
        assert_array_equal(a, b)

    def test_check_06(self):
        a = np.pad([1, 2, 3, 4], [15, 2], 'symmetric')
        b = np.array(
            [2, 3, 4, 4, 3, 2, 1, 1, 2, 3,
             4, 4, 3, 2, 1, 1, 2, 3, 4, 4,
             3]
        )
        assert_array_equal(a, b)

    def test_check_07(self):
        a = np.pad([1, 2, 3, 4, 5, 6], [45, 3], 'symmetric')
        b = np.array(
            [4, 5, 6, 6, 5, 4, 3, 2, 1, 1,
             2, 3, 4, 5, 6, 6, 5, 4, 3, 2,
             1, 1, 2, 3, 4, 5, 6, 6, 5, 4,
             3, 2, 1, 1, 2, 3, 4, 5, 6, 6,
             5, 4, 3, 2, 1, 1, 2, 3, 4, 5,
             6, 6, 5, 4])
        assert_array_equal(a, b)


class TestEmptyArray:
    """Check how padding behaves on arrays with an empty dimension."""

    @pytest.mark.parametrize(
        # Keep parametrization ordered, otherwise pytest-xdist might believe
        # that different tests were collected during parallelization
        "mode", sorted(_all_modes.keys() - {"constant", "empty"})
    )
    def test_pad_empty_dimension(self, mode):
        match = ("can't extend empty axis 0 using modes other than 'constant' "
                 "or 'empty'")
        with pytest.raises(ValueError, match=match):
            np.pad([], 4, mode=mode)
        with pytest.raises(ValueError, match=match):
            np.pad(np.ndarray(0), 4, mode=mode)
        with pytest.raises(ValueError, match=match):
            np.pad(np.zeros((0, 3)), ((1,), (0,)), mode=mode)

    @pytest.mark.parametrize("mode", _all_modes.keys())
    def test_pad_non_empty_dimension(self, mode):
        result = np.pad(np.ones((2, 0, 2)), ((3,), (0,), (1,)), mode=mode)
        assert result.shape == (8, 0, 4)


class TestSymmetric:
    def test_check_simple(self):
        a = np.arange(100)
        a = np.pad(a, (25, 20), 'symmetric')
        b = np.array(
            [24, 23, 22, 21, 20, 19, 18, 17, 16, 15,
             14, 13, 12, 11, 10, 9, 8, 7, 6, 5,
             4, 3, 2, 1, 0,

             0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
             20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
             30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
             40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
             50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
             60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
             70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
             80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
             90, 91, 92, 93, 94, 95, 96, 97, 98, 99,

             99, 98, 97, 96, 95, 94, 93, 92, 91, 90,
             89, 88, 87, 86, 85, 84, 83, 82, 81, 80]
            )
        assert_array_equal(a, b)

    def test_check_odd_method(self):
        a = np.arange(100)
        a = np.pad(a, (25, 20), 'symmetric', reflect_type='odd')
        b = np.array(
            [-24, -23, -22, -21, -20, -19, -18, -17, -16, -15,
             -14, -13, -12, -11, -10, -9, -8, -7, -6, -5,
             -4, -3, -2, -1, 0,

             0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
             20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
             30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
             40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
             50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
             60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
             70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
             80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
             90, 91, 92, 93, 94, 95, 96, 97, 98, 99,

             99, 100, 101, 102, 103, 104, 105, 106, 107, 108,
             109, 110, 111, 112, 113, 114, 115, 116, 117, 118]
            )
        assert_array_equal(a, b)

    def test_check_large_pad(self):
        a = [[4, 5, 6], [6, 7, 8]]
        a = np.pad(a, (5, 7), 'symmetric')
        b = np.array(
            [[5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [7, 8, 8, 7, 6, 6, 7, 8, 8, 7, 6, 6, 7, 8, 8],
             [7, 8, 8, 7, 6, 6, 7, 8, 8, 7, 6, 6, 7, 8, 8],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],

             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [7, 8, 8, 7, 6, 6, 7, 8, 8, 7, 6, 6, 7, 8, 8],

             [7, 8, 8, 7, 6, 6, 7, 8, 8, 7, 6, 6, 7, 8, 8],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [7, 8, 8, 7, 6, 6, 7, 8, 8, 7, 6, 6, 7, 8, 8],
             [7, 8, 8, 7, 6, 6, 7, 8, 8, 7, 6, 6, 7, 8, 8],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6]]
            )

        assert_array_equal(a, b)

    def test_check_large_pad_odd(self):
        a = [[4, 5, 6], [6, 7, 8]]
        a = np.pad(a, (5, 7), 'symmetric', reflect_type='odd')
        b = np.array(
            [[-3, -2, -2, -1,  0,  0,  1,  2,  2,  3,  4,  4,  5,  6,  6],
             [-3, -2, -2, -1,  0,  0,  1,  2,  2,  3,  4,  4,  5,  6,  6],
             [-1,  0,  0,  1,  2,  2,  3,  4,  4,  5,  6,  6,  7,  8,  8],
             [-1,  0,  0,  1,  2,  2,  3,  4,  4,  5,  6,  6,  7,  8,  8],
             [ 1,  2,  2,  3,  4,  4,  5,  6,  6,  7,  8,  8,  9, 10, 10],

             [ 1,  2,  2,  3,  4,  4,  5,  6,  6,  7,  8,  8,  9, 10, 10],
             [ 3,  4,  4,  5,  6,  6,  7,  8,  8,  9, 10, 10, 11, 12, 12],

             [ 3,  4,  4,  5,  6,  6,  7,  8,  8,  9, 10, 10, 11, 12, 12],
             [ 5,  6,  6,  7,  8,  8,  9, 10, 10, 11, 12, 12, 13, 14, 14],
             [ 5,  6,  6,  7,  8,  8,  9, 10, 10, 11, 12, 12, 13, 14, 14],
             [ 7,  8,  8,  9, 10, 10, 11, 12, 12, 13, 14, 14, 15, 16, 16],
             [ 7,  8,  8,  9, 10, 10, 11, 12, 12, 13, 14, 14, 15, 16, 16],
             [ 9, 10, 10, 11, 12, 12, 13, 14, 14, 15, 16, 16, 17, 18, 18],
             [ 9, 10, 10, 11, 12, 12, 13, 14, 14, 15, 16, 16, 17, 18, 18]]
            )
        assert_array_equal(a, b)

    def test_check_shape(self):
        a = [[4, 5, 6]]
        a = np.pad(a, (5, 7), 'symmetric')
        b = np.array(
            [[5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],

             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],

             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6]]
            )
        assert_array_equal(a, b)

    def test_check_01(self):
        a = np.pad([1, 2, 3], 2, 'symmetric')
        b = np.array([2, 1, 1, 2, 3, 3, 2])
        assert_array_equal(a, b)

    def test_check_02(self):
        a = np.pad([1, 2, 3], 3, 'symmetric')
        b = np.array([3, 2, 1, 1, 2, 3, 3, 2, 1])
        assert_array_equal(a, b)

    def test_check_03(self):
        a = np.pad([1, 2, 3], 6, 'symmetric')
        b = np.array([1, 2, 3, 3, 2, 1, 1, 2, 3, 3, 2, 1, 1, 2, 3])
        assert_array_equal(a, b)


class TestWrap:
    def test_check_simple(self):
        a = np.arange(100)
        a = np.pad(a, (25, 20), 'wrap')
        b = np.array(
            [75, 76, 77, 78, 79, 80, 81, 82, 83, 84,
             85, 86, 87, 88, 89, 90, 91, 92, 93, 94,
             95, 96, 97, 98, 99,

             0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
             20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
             30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
             40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
             50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
             60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
             70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
             80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
             90, 91, 92, 93, 94, 95, 96, 97, 98, 99,

             0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
            )
        assert_array_equal(a, b)

    def test_check_large_pad(self):
        a = np.arange(12)
        a = np.reshape(a, (3, 4))
        a = np.pad(a, (10, 12), 'wrap')
        b = np.array(
            [[10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10,
              11, 8, 9, 10, 11, 8, 9, 10, 11],
             [2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2,
              3, 0, 1, 2, 3, 0, 1, 2, 3],
             [6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6,
              7, 4, 5, 6, 7, 4, 5, 6, 7],
             [10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10,
              11, 8, 9, 10, 11, 8, 9, 10, 11],
             [2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2,
              3, 0, 1, 2, 3, 0, 1, 2, 3],
             [6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6,
              7, 4, 5, 6, 7, 4, 5, 6, 7],
             [10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10,
              11, 8, 9, 10, 11, 8, 9, 10, 11],
             [2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2,
              3, 0, 1, 2, 3, 0, 1, 2, 3],
             [6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6,
              7, 4, 5, 6, 7, 4, 5, 6, 7],
             [10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10,
              11, 8, 9, 10, 11, 8, 9, 10, 11],

             [2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2,
              3, 0, 1, 2, 3, 0, 1, 2, 3],
             [6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6,
              7, 4, 5, 6, 7, 4, 5, 6, 7],
             [10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10,
              11, 8, 9, 10, 11, 8, 9, 10, 11],

             [2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2,
              3, 0, 1, 2, 3, 0, 1, 2, 3],
             [6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6,
              7, 4, 5, 6, 7, 4, 5, 6, 7],
             [10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10,
              11, 8, 9, 10, 11, 8, 9, 10, 11],
             [2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2,
              3, 0, 1, 2, 3, 0, 1, 2, 3],
             [6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6,
              7, 4, 5, 6, 7, 4, 5, 6, 7],
             [10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10,
              11, 8, 9, 10, 11, 8, 9, 10, 11],
             [2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2,
              3, 0, 1, 2, 3, 0, 1, 2, 3],
             [6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6,
              7, 4, 5, 6, 7, 4, 5, 6, 7],
             [10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10,
              11, 8, 9, 10, 11, 8, 9, 10, 11],
             [2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2,
              3, 0, 1, 2, 3, 0, 1, 2, 3],
             [6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6,
              7, 4, 5, 6, 7, 4, 5, 6, 7],
             [10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10,
              11, 8, 9, 10, 11, 8, 9, 10, 11]]
            )
        assert_array_equal(a, b)

    def test_check_01(self):
        a = np.pad([1, 2, 3], 3, 'wrap')
        b = np.array([1, 2, 3, 1, 2, 3, 1, 2, 3])
        assert_array_equal(a, b)

    def test_check_02(self):
        a = np.pad([1, 2, 3], 4, 'wrap')
        b = np.array([3, 1, 2, 3, 1, 2, 3, 1, 2, 3, 1])
        assert_array_equal(a, b)

    def test_pad_with_zero(self):
        a = np.ones((3, 5))
        b = np.pad(a, (0, 5), mode="wrap")
        assert_array_equal(a, b[:-5, :-5])

    def test_repeated_wrapping(self):
        """
        Check wrapping on each side individually if the wrapped area is longer
        than the original array.
        """
        a = np.arange(5)
        b = np.pad(a, (12, 0), mode="wrap")
        assert_array_equal(np.r_[a, a, a, a][3:], b)

        a = np.arange(5)
        b = np.pad(a, (0, 12), mode="wrap")
        assert_array_equal(np.r_[a, a, a, a][:-3], b)

    def test_repeated_wrapping_multiple_origin(self):
        """
        Assert that 'wrap' pads only with multiples of the original area if
        the pad width is larger than the original array.
        """
        a = np.arange(4).reshape(2, 2)
        a = np.pad(a, [(1, 3), (3, 1)], mode='wrap')
        b = np.array(
            [[3, 2, 3, 2, 3, 2],
             [1, 0, 1, 0, 1, 0],
             [3, 2, 3, 2, 3, 2],
             [1, 0, 1, 0, 1, 0],
             [3, 2, 3, 2, 3, 2],
             [1, 0, 1, 0, 1, 0]]
        )
        assert_array_equal(a, b)


class TestEdge:
    def test_check_simple(self):
        a = np.arange(12)
        a = np.reshape(a, (4, 3))
        a = np.pad(a, ((2, 3), (3, 2)), 'edge')
        b = np.array(
            [[0, 0, 0, 0, 1, 2, 2, 2],
             [0, 0, 0, 0, 1, 2, 2, 2],

             [0, 0, 0, 0, 1, 2, 2, 2],
             [3, 3, 3, 3, 4, 5, 5, 5],
             [6, 6, 6, 6, 7, 8, 8, 8],
             [9, 9, 9, 9, 10, 11, 11, 11],

             [9, 9, 9, 9, 10, 11, 11, 11],
             [9, 9, 9, 9, 10, 11, 11, 11],
             [9, 9, 9, 9, 10, 11, 11, 11]]
            )
        assert_array_equal(a, b)

    def test_check_width_shape_1_2(self):
        # Check a pad_width of the form ((1, 2),).
        # Regression test for issue gh-7808.
        a = np.array([1, 2, 3])
        padded = np.pad(a, ((1, 2),), 'edge')
        expected = np.array([1, 1, 2, 3, 3, 3])
        assert_array_equal(padded, expected)

        a = np.array([[1, 2, 3], [4, 5, 6]])
        padded = np.pad(a, ((1, 2),), 'edge')
        expected = np.pad(a, ((1, 2), (1, 2)), 'edge')
        assert_array_equal(padded, expected)

        a = np.arange(24).reshape(2, 3, 4)
        padded = np.pad(a, ((1, 2),), 'edge')
        expected = np.pad(a, ((1, 2), (1, 2), (1, 2)), 'edge')
        assert_array_equal(padded, expected)


class TestEmpty:
    def test_simple(self):
        arr = np.arange(24).reshape(4, 6)
        result = np.pad(arr, [(2, 3), (3, 1)], mode="empty")
        assert result.shape == (9, 10)
        assert_equal(arr, result[2:-3, 3:-1])

    def test_pad_empty_dimension(self):
        arr = np.zeros((3, 0, 2))
        result = np.pad(arr, [(0,), (2,), (1,)], mode="empty")
        assert result.shape == (3, 4, 4)


def test_legacy_vector_functionality():
    def _padwithtens(vector, pad_width, iaxis, kwargs):
        vector[:pad_width[0]] = 10
        vector[-pad_width[1]:] = 10

    a = np.arange(6).reshape(2, 3)
    a = np.pad(a, 2, _padwithtens)
    b = np.array(
        [[10, 10, 10, 10, 10, 10, 10],
         [10, 10, 10, 10, 10, 10, 10],

         [10, 10,  0,  1,  2, 10, 10],
         [10, 10,  3,  4,  5, 10, 10],

         [10, 10, 10, 10, 10, 10, 10],
         [10, 10, 10, 10, 10, 10, 10]]
        )
    assert_array_equal(a, b)


def test_unicode_mode():
    a = np.pad([1], 2, mode='constant')
    b = np.array([0, 0, 1, 0, 0])
    assert_array_equal(a, b)


@pytest.mark.parametrize("mode", ["edge", "symmetric", "reflect", "wrap"])
def test_object_input(mode):
    # Regression test for issue gh-11395.
    a = np.full((4, 3), fill_value=None)
    pad_amt = ((2, 3), (3, 2))
    b = np.full((9, 8), fill_value=None)
    assert_array_equal(np.pad(a, pad_amt, mode=mode), b)


class TestPadWidth:
    @pytest.mark.parametrize("pad_width", [
        (4, 5, 6, 7),
        ((1,), (2,), (3,)),
        ((1, 2), (3, 4), (5, 6)),
        ((3, 4, 5), (0, 1, 2)),
    ])
    @pytest.mark.parametrize("mode", _all_modes.keys())
    def test_misshaped_pad_width(self, pad_width, mode):
        arr = np.arange(30).reshape((6, 5))
        match = "operands could not be broadcast together"
        with pytest.raises(ValueError, match=match):
            np.pad(arr, pad_width, mode)

    @pytest.mark.parametrize("mode", _all_modes.keys())
    def test_misshaped_pad_width_2(self, mode):
        arr = np.arange(30).reshape((6, 5))
        match = ("input operand has more dimensions than allowed by the axis "
                 "remapping")
        with pytest.raises(ValueError, match=match):
            np.pad(arr, (((3,), (4,), (5,)), ((0,), (1,), (2,))), mode)

    @pytest.mark.parametrize(
        "pad_width", [-2, (-2,), (3, -1), ((5, 2), (-2, 3)), ((-4,), (2,))])
    @pytest.mark.parametrize("mode", _all_modes.keys())
    def test_negative_pad_width(self, pad_width, mode):
        arr = np.arange(30).reshape((6, 5))
        match = "index can't contain negative values"
        with pytest.raises(ValueError, match=match):
            np.pad(arr, pad_width, mode)

    @pytest.mark.parametrize("pad_width, dtype", [
        ("3", None),
        ("word", None),
        (None, None),
        (object(), None),
        (3.4, None),
        (((2, 3, 4), (3, 2)), object),
        (complex(1, -1), None),
        (((-2.1, 3), (3, 2)), None),
    ])
    @pytest.mark.parametrize("mode", _all_modes.keys())
    def test_bad_type(self, pad_width, dtype, mode):
        arr = np.arange(30).reshape((6, 5))
        match = "`pad_width` must be of integral type."
        if dtype is not None:
            # avoid DeprecationWarning when not specifying dtype
            with pytest.raises(TypeError, match=match):
                np.pad(arr, np.array(pad_width, dtype=dtype), mode)
        else:
            with pytest.raises(TypeError, match=match):
                np.pad(arr, pad_width, mode)
            with pytest.raises(TypeError, match=match):
                np.pad(arr, np.array(pad_width), mode)

    def test_pad_width_as_ndarray(self):
        a = np.arange(12)
        a = np.reshape(a, (4, 3))
        a = np.pad(a, np.array(((2, 3), (3, 2))), 'edge')
        b = np.array(
            [[0,  0,  0,    0,  1,  2,    2,  2],
             [0,  0,  0,    0,  1,  2,    2,  2],

             [0,  0,  0,    0,  1,  2,    2,  2],
             [3,  3,  3,    3,  4,  5,    5,  5],
             [6,  6,  6,    6,  7,  8,    8,  8],
             [9,  9,  9,    9, 10, 11,   11, 11],

             [9,  9,  9,    9, 10, 11,   11, 11],
             [9,  9,  9,    9, 10, 11,   11, 11],
             [9,  9,  9,    9, 10, 11,   11, 11]]
            )
        assert_array_equal(a, b)

    @pytest.mark.parametrize("pad_width", [0, (0, 0), ((0, 0), (0, 0))])
    @pytest.mark.parametrize("mode", _all_modes.keys())
    def test_zero_pad_width(self, pad_width, mode):
        arr = np.arange(30).reshape(6, 5)
        assert_array_equal(arr, np.pad(arr, pad_width, mode=mode))


@pytest.mark.parametrize("mode", _all_modes.keys())
def test_kwargs(mode):
    """Test behavior of pad's kwargs for the given mode."""
    allowed = _all_modes[mode]
    not_allowed = {}
    for kwargs in _all_modes.values():
        if kwargs != allowed:
            not_allowed.update(kwargs)
    # Test if allowed keyword arguments pass
    np.pad([1, 2, 3], 1, mode, **allowed)
    # Test if prohibited keyword arguments of other modes raise an error
    for key, value in not_allowed.items():
        match = f"unsupported keyword arguments for mode '{mode}'"
        with pytest.raises(ValueError, match=match):
            np.pad([1, 2, 3], 1, mode, **{key: value})


def test_constant_zero_default():
    arr = np.array([1, 1])
    assert_array_equal(np.pad(arr, 2), [0, 0, 1, 1, 0, 0])


@pytest.mark.parametrize("mode", [1, "const", object(), None, True, False])
def test_unsupported_mode(mode):
    match = f"mode '{mode}' is not supported"
    with pytest.raises(ValueError, match=match):
        np.pad([1, 2, 3], 4, mode=mode)


@pytest.mark.parametrize("mode", _all_modes.keys())
def test_non_contiguous_array(mode):
    arr = np.arange(24).reshape(4, 6)[::2, ::2]
    result = np.pad(arr, (2, 3), mode)
    assert result.shape == (7, 8)
    assert_equal(result[2:-3, 2:-3], arr)


@pytest.mark.parametrize("mode", _all_modes.keys())
def test_memory_layout_persistence(mode):
    """Test if C and F order is preserved for all pad modes."""
    x = np.ones((5, 10), order='C')
    assert np.pad(x, 5, mode).flags["C_CONTIGUOUS"]
    x = np.ones((5, 10), order='F')
    assert np.pad(x, 5, mode).flags["F_CONTIGUOUS"]


@pytest.mark.parametrize("dtype", _numeric_dtypes)
@pytest.mark.parametrize("mode", _all_modes.keys())
def test_dtype_persistence(dtype, mode):
    arr = np.zeros((3, 2, 1), dtype=dtype)
    result = np.pad(arr, 1, mode=mode)
    assert result.dtype == dtype

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\tests\test_arraypad.py ===
"""Tests for the array padding functions.

"""
import pytest

import numpy as np
from numpy.lib._arraypad_impl import _as_pairs
from numpy.testing import assert_allclose, assert_array_equal, assert_equal

_numeric_dtypes = (
    np._core.sctypes["uint"]
    + np._core.sctypes["int"]
    + np._core.sctypes["float"]
    + np._core.sctypes["complex"]
)
_all_modes = {
    'constant': {'constant_values': 0},
    'edge': {},
    'linear_ramp': {'end_values': 0},
    'maximum': {'stat_length': None},
    'mean': {'stat_length': None},
    'median': {'stat_length': None},
    'minimum': {'stat_length': None},
    'reflect': {'reflect_type': 'even'},
    'symmetric': {'reflect_type': 'even'},
    'wrap': {},
    'empty': {}
}


class TestAsPairs:
    def test_single_value(self):
        """Test casting for a single value."""
        expected = np.array([[3, 3]] * 10)
        for x in (3, [3], [[3]]):
            result = _as_pairs(x, 10)
            assert_equal(result, expected)
        # Test with dtype=object
        obj = object()
        assert_equal(
            _as_pairs(obj, 10),
            np.array([[obj, obj]] * 10)
        )

    def test_two_values(self):
        """Test proper casting for two different values."""
        # Broadcasting in the first dimension with numbers
        expected = np.array([[3, 4]] * 10)
        for x in ([3, 4], [[3, 4]]):
            result = _as_pairs(x, 10)
            assert_equal(result, expected)
        # and with dtype=object
        obj = object()
        assert_equal(
            _as_pairs(["a", obj], 10),
            np.array([["a", obj]] * 10)
        )

        # Broadcasting in the second / last dimension with numbers
        assert_equal(
            _as_pairs([[3], [4]], 2),
            np.array([[3, 3], [4, 4]])
        )
        # and with dtype=object
        assert_equal(
            _as_pairs([["a"], [obj]], 2),
            np.array([["a", "a"], [obj, obj]])
        )

    def test_with_none(self):
        expected = ((None, None), (None, None), (None, None))
        assert_equal(
            _as_pairs(None, 3, as_index=False),
            expected
        )
        assert_equal(
            _as_pairs(None, 3, as_index=True),
            expected
        )

    def test_pass_through(self):
        """Test if `x` already matching desired output are passed through."""
        expected = np.arange(12).reshape((6, 2))
        assert_equal(
            _as_pairs(expected, 6),
            expected
        )

    def test_as_index(self):
        """Test results if `as_index=True`."""
        assert_equal(
            _as_pairs([2.6, 3.3], 10, as_index=True),
            np.array([[3, 3]] * 10, dtype=np.intp)
        )
        assert_equal(
            _as_pairs([2.6, 4.49], 10, as_index=True),
            np.array([[3, 4]] * 10, dtype=np.intp)
        )
        for x in (-3, [-3], [[-3]], [-3, 4], [3, -4], [[-3, 4]], [[4, -3]],
                  [[1, 2]] * 9 + [[1, -2]]):
            with pytest.raises(ValueError, match="negative values"):
                _as_pairs(x, 10, as_index=True)

    def test_exceptions(self):
        """Ensure faulty usage is discovered."""
        with pytest.raises(ValueError, match="more dimensions than allowed"):
            _as_pairs([[[3]]], 10)
        with pytest.raises(ValueError, match="could not be broadcast"):
            _as_pairs([[1, 2], [3, 4]], 3)
        with pytest.raises(ValueError, match="could not be broadcast"):
            _as_pairs(np.ones((2, 3)), 3)


class TestConditionalShortcuts:
    @pytest.mark.parametrize("mode", _all_modes.keys())
    def test_zero_padding_shortcuts(self, mode):
        test = np.arange(120).reshape(4, 5, 6)
        pad_amt = [(0, 0) for _ in test.shape]
        assert_array_equal(test, np.pad(test, pad_amt, mode=mode))

    @pytest.mark.parametrize("mode", ['maximum', 'mean', 'median', 'minimum',])
    def test_shallow_statistic_range(self, mode):
        test = np.arange(120).reshape(4, 5, 6)
        pad_amt = [(1, 1) for _ in test.shape]
        assert_array_equal(np.pad(test, pad_amt, mode='edge'),
                           np.pad(test, pad_amt, mode=mode, stat_length=1))

    @pytest.mark.parametrize("mode", ['maximum', 'mean', 'median', 'minimum',])
    def test_clip_statistic_range(self, mode):
        test = np.arange(30).reshape(5, 6)
        pad_amt = [(3, 3) for _ in test.shape]
        assert_array_equal(np.pad(test, pad_amt, mode=mode),
                           np.pad(test, pad_amt, mode=mode, stat_length=30))


class TestStatistic:
    def test_check_mean_stat_length(self):
        a = np.arange(100).astype('f')
        a = np.pad(a, ((25, 20), ), 'mean', stat_length=((2, 3), ))
        b = np.array(
            [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5,
             0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5,
             0.5, 0.5, 0.5, 0.5, 0.5,

             0., 1., 2., 3., 4., 5., 6., 7., 8., 9.,
             10., 11., 12., 13., 14., 15., 16., 17., 18., 19.,
             20., 21., 22., 23., 24., 25., 26., 27., 28., 29.,
             30., 31., 32., 33., 34., 35., 36., 37., 38., 39.,
             40., 41., 42., 43., 44., 45., 46., 47., 48., 49.,
             50., 51., 52., 53., 54., 55., 56., 57., 58., 59.,
             60., 61., 62., 63., 64., 65., 66., 67., 68., 69.,
             70., 71., 72., 73., 74., 75., 76., 77., 78., 79.,
             80., 81., 82., 83., 84., 85., 86., 87., 88., 89.,
             90., 91., 92., 93., 94., 95., 96., 97., 98., 99.,

             98., 98., 98., 98., 98., 98., 98., 98., 98., 98.,
             98., 98., 98., 98., 98., 98., 98., 98., 98., 98.
             ])
        assert_array_equal(a, b)

    def test_check_maximum_1(self):
        a = np.arange(100)
        a = np.pad(a, (25, 20), 'maximum')
        b = np.array(
            [99, 99, 99, 99, 99, 99, 99, 99, 99, 99,
             99, 99, 99, 99, 99, 99, 99, 99, 99, 99,
             99, 99, 99, 99, 99,

             0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
             20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
             30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
             40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
             50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
             60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
             70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
             80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
             90, 91, 92, 93, 94, 95, 96, 97, 98, 99,

             99, 99, 99, 99, 99, 99, 99, 99, 99, 99,
             99, 99, 99, 99, 99, 99, 99, 99, 99, 99]
            )
        assert_array_equal(a, b)

    def test_check_maximum_2(self):
        a = np.arange(100) + 1
        a = np.pad(a, (25, 20), 'maximum')
        b = np.array(
            [100, 100, 100, 100, 100, 100, 100, 100, 100, 100,
             100, 100, 100, 100, 100, 100, 100, 100, 100, 100,
             100, 100, 100, 100, 100,

             1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
             11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
             21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
             31, 32, 33, 34, 35, 36, 37, 38, 39, 40,
             41, 42, 43, 44, 45, 46, 47, 48, 49, 50,
             51, 52, 53, 54, 55, 56, 57, 58, 59, 60,
             61, 62, 63, 64, 65, 66, 67, 68, 69, 70,
             71, 72, 73, 74, 75, 76, 77, 78, 79, 80,
             81, 82, 83, 84, 85, 86, 87, 88, 89, 90,
             91, 92, 93, 94, 95, 96, 97, 98, 99, 100,

             100, 100, 100, 100, 100, 100, 100, 100, 100, 100,
             100, 100, 100, 100, 100, 100, 100, 100, 100, 100]
            )
        assert_array_equal(a, b)

    def test_check_maximum_stat_length(self):
        a = np.arange(100) + 1
        a = np.pad(a, (25, 20), 'maximum', stat_length=10)
        b = np.array(
            [10, 10, 10, 10, 10, 10, 10, 10, 10, 10,
             10, 10, 10, 10, 10, 10, 10, 10, 10, 10,
             10, 10, 10, 10, 10,

              1,  2,  3,  4,  5,  6,  7,  8,  9, 10,
             11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
             21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
             31, 32, 33, 34, 35, 36, 37, 38, 39, 40,
             41, 42, 43, 44, 45, 46, 47, 48, 49, 50,
             51, 52, 53, 54, 55, 56, 57, 58, 59, 60,
             61, 62, 63, 64, 65, 66, 67, 68, 69, 70,
             71, 72, 73, 74, 75, 76, 77, 78, 79, 80,
             81, 82, 83, 84, 85, 86, 87, 88, 89, 90,
             91, 92, 93, 94, 95, 96, 97, 98, 99, 100,

             100, 100, 100, 100, 100, 100, 100, 100, 100, 100,
             100, 100, 100, 100, 100, 100, 100, 100, 100, 100]
            )
        assert_array_equal(a, b)

    def test_check_minimum_1(self):
        a = np.arange(100)
        a = np.pad(a, (25, 20), 'minimum')
        b = np.array(
            [ 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
              0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
              0,  0,  0,  0,  0,

              0,  1,  2,  3,  4,  5,  6,  7,  8,  9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
             20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
             30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
             40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
             50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
             60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
             70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
             80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
             90, 91, 92, 93, 94, 95, 96, 97, 98, 99,

             0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
             0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            )
        assert_array_equal(a, b)

    def test_check_minimum_2(self):
        a = np.arange(100) + 2
        a = np.pad(a, (25, 20), 'minimum')
        b = np.array(
            [ 2,  2,  2,  2,  2,  2,  2,  2,  2,  2,
              2,  2,  2,  2,  2,  2,  2,  2,  2,  2,
              2,  2,  2,  2,  2,

              2,  3,  4,  5,  6,  7,  8,  9, 10, 11,
             12, 13, 14, 15, 16, 17, 18, 19, 20, 21,
             22, 23, 24, 25, 26, 27, 28, 29, 30, 31,
             32, 33, 34, 35, 36, 37, 38, 39, 40, 41,
             42, 43, 44, 45, 46, 47, 48, 49, 50, 51,
             52, 53, 54, 55, 56, 57, 58, 59, 60, 61,
             62, 63, 64, 65, 66, 67, 68, 69, 70, 71,
             72, 73, 74, 75, 76, 77, 78, 79, 80, 81,
             82, 83, 84, 85, 86, 87, 88, 89, 90, 91,
             92, 93, 94, 95, 96, 97, 98, 99, 100, 101,

             2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
             2, 2, 2, 2, 2, 2, 2, 2, 2, 2]
            )
        assert_array_equal(a, b)

    def test_check_minimum_stat_length(self):
        a = np.arange(100) + 1
        a = np.pad(a, (25, 20), 'minimum', stat_length=10)
        b = np.array(
            [ 1,  1,  1,  1,  1,  1,  1,  1,  1,  1,
              1,  1,  1,  1,  1,  1,  1,  1,  1,  1,
              1,  1,  1,  1,  1,

              1,  2,  3,  4,  5,  6,  7,  8,  9, 10,
             11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
             21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
             31, 32, 33, 34, 35, 36, 37, 38, 39, 40,
             41, 42, 43, 44, 45, 46, 47, 48, 49, 50,
             51, 52, 53, 54, 55, 56, 57, 58, 59, 60,
             61, 62, 63, 64, 65, 66, 67, 68, 69, 70,
             71, 72, 73, 74, 75, 76, 77, 78, 79, 80,
             81, 82, 83, 84, 85, 86, 87, 88, 89, 90,
             91, 92, 93, 94, 95, 96, 97, 98, 99, 100,

             91, 91, 91, 91, 91, 91, 91, 91, 91, 91,
             91, 91, 91, 91, 91, 91, 91, 91, 91, 91]
            )
        assert_array_equal(a, b)

    def test_check_median(self):
        a = np.arange(100).astype('f')
        a = np.pad(a, (25, 20), 'median')
        b = np.array(
            [49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5,
             49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5,
             49.5, 49.5, 49.5, 49.5, 49.5,

             0., 1., 2., 3., 4., 5., 6., 7., 8., 9.,
             10., 11., 12., 13., 14., 15., 16., 17., 18., 19.,
             20., 21., 22., 23., 24., 25., 26., 27., 28., 29.,
             30., 31., 32., 33., 34., 35., 36., 37., 38., 39.,
             40., 41., 42., 43., 44., 45., 46., 47., 48., 49.,
             50., 51., 52., 53., 54., 55., 56., 57., 58., 59.,
             60., 61., 62., 63., 64., 65., 66., 67., 68., 69.,
             70., 71., 72., 73., 74., 75., 76., 77., 78., 79.,
             80., 81., 82., 83., 84., 85., 86., 87., 88., 89.,
             90., 91., 92., 93., 94., 95., 96., 97., 98., 99.,

             49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5,
             49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5]
            )
        assert_array_equal(a, b)

    def test_check_median_01(self):
        a = np.array([[3, 1, 4], [4, 5, 9], [9, 8, 2]])
        a = np.pad(a, 1, 'median')
        b = np.array(
            [[4, 4, 5, 4, 4],

             [3, 3, 1, 4, 3],
             [5, 4, 5, 9, 5],
             [8, 9, 8, 2, 8],

             [4, 4, 5, 4, 4]]
            )
        assert_array_equal(a, b)

    def test_check_median_02(self):
        a = np.array([[3, 1, 4], [4, 5, 9], [9, 8, 2]])
        a = np.pad(a.T, 1, 'median').T
        b = np.array(
            [[5, 4, 5, 4, 5],

             [3, 3, 1, 4, 3],
             [5, 4, 5, 9, 5],
             [8, 9, 8, 2, 8],

             [5, 4, 5, 4, 5]]
            )
        assert_array_equal(a, b)

    def test_check_median_stat_length(self):
        a = np.arange(100).astype('f')
        a[1] = 2.
        a[97] = 96.
        a = np.pad(a, (25, 20), 'median', stat_length=(3, 5))
        b = np.array(
            [ 2.,  2.,  2.,  2.,  2.,  2.,  2.,  2.,  2.,  2.,
              2.,  2.,  2.,  2.,  2.,  2.,  2.,  2.,  2.,  2.,
              2.,  2.,  2.,  2.,  2.,

              0.,  2.,  2.,  3.,  4.,  5.,  6.,  7.,  8.,  9.,
             10., 11., 12., 13., 14., 15., 16., 17., 18., 19.,
             20., 21., 22., 23., 24., 25., 26., 27., 28., 29.,
             30., 31., 32., 33., 34., 35., 36., 37., 38., 39.,
             40., 41., 42., 43., 44., 45., 46., 47., 48., 49.,
             50., 51., 52., 53., 54., 55., 56., 57., 58., 59.,
             60., 61., 62., 63., 64., 65., 66., 67., 68., 69.,
             70., 71., 72., 73., 74., 75., 76., 77., 78., 79.,
             80., 81., 82., 83., 84., 85., 86., 87., 88., 89.,
             90., 91., 92., 93., 94., 95., 96., 96., 98., 99.,

             96., 96., 96., 96., 96., 96., 96., 96., 96., 96.,
             96., 96., 96., 96., 96., 96., 96., 96., 96., 96.]
            )
        assert_array_equal(a, b)

    def test_check_mean_shape_one(self):
        a = [[4, 5, 6]]
        a = np.pad(a, (5, 7), 'mean', stat_length=2)
        b = np.array(
            [[4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],
             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],
             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],
             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],
             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],

             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],

             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],
             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],
             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],
             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],
             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],
             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6],
             [4, 4, 4, 4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6]]
            )
        assert_array_equal(a, b)

    def test_check_mean_2(self):
        a = np.arange(100).astype('f')
        a = np.pad(a, (25, 20), 'mean')
        b = np.array(
            [49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5,
             49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5,
             49.5, 49.5, 49.5, 49.5, 49.5,

             0., 1., 2., 3., 4., 5., 6., 7., 8., 9.,
             10., 11., 12., 13., 14., 15., 16., 17., 18., 19.,
             20., 21., 22., 23., 24., 25., 26., 27., 28., 29.,
             30., 31., 32., 33., 34., 35., 36., 37., 38., 39.,
             40., 41., 42., 43., 44., 45., 46., 47., 48., 49.,
             50., 51., 52., 53., 54., 55., 56., 57., 58., 59.,
             60., 61., 62., 63., 64., 65., 66., 67., 68., 69.,
             70., 71., 72., 73., 74., 75., 76., 77., 78., 79.,
             80., 81., 82., 83., 84., 85., 86., 87., 88., 89.,
             90., 91., 92., 93., 94., 95., 96., 97., 98., 99.,

             49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5,
             49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5, 49.5]
            )
        assert_array_equal(a, b)

    @pytest.mark.parametrize("mode", [
        "mean",
        "median",
        "minimum",
        "maximum"
    ])
    def test_same_prepend_append(self, mode):
        """ Test that appended and prepended values are equal """
        # This test is constructed to trigger floating point rounding errors in
        # a way that caused gh-11216 for mode=='mean'
        a = np.array([-1, 2, -1]) + np.array([0, 1e-12, 0], dtype=np.float64)
        a = np.pad(a, (1, 1), mode)
        assert_equal(a[0], a[-1])

    @pytest.mark.parametrize("mode", ["mean", "median", "minimum", "maximum"])
    @pytest.mark.parametrize(
        "stat_length", [-2, (-2,), (3, -1), ((5, 2), (-2, 3)), ((-4,), (2,))]
    )
    def test_check_negative_stat_length(self, mode, stat_length):
        arr = np.arange(30).reshape((6, 5))
        match = "index can't contain negative values"
        with pytest.raises(ValueError, match=match):
            np.pad(arr, 2, mode, stat_length=stat_length)

    def test_simple_stat_length(self):
        a = np.arange(30)
        a = np.reshape(a, (6, 5))
        a = np.pad(a, ((2, 3), (3, 2)), mode='mean', stat_length=(3,))
        b = np.array(
            [[6, 6, 6, 5, 6, 7, 8, 9, 8, 8],
             [6, 6, 6, 5, 6, 7, 8, 9, 8, 8],

             [1, 1, 1, 0, 1, 2, 3, 4, 3, 3],
             [6, 6, 6, 5, 6, 7, 8, 9, 8, 8],
             [11, 11, 11, 10, 11, 12, 13, 14, 13, 13],
             [16, 16, 16, 15, 16, 17, 18, 19, 18, 18],
             [21, 21, 21, 20, 21, 22, 23, 24, 23, 23],
             [26, 26, 26, 25, 26, 27, 28, 29, 28, 28],

             [21, 21, 21, 20, 21, 22, 23, 24, 23, 23],
             [21, 21, 21, 20, 21, 22, 23, 24, 23, 23],
             [21, 21, 21, 20, 21, 22, 23, 24, 23, 23]]
            )
        assert_array_equal(a, b)

    @pytest.mark.filterwarnings("ignore:Mean of empty slice:RuntimeWarning")
    @pytest.mark.filterwarnings(
        "ignore:invalid value encountered in( scalar)? divide:RuntimeWarning"
    )
    @pytest.mark.parametrize("mode", ["mean", "median"])
    def test_zero_stat_length_valid(self, mode):
        arr = np.pad([1., 2.], (1, 2), mode, stat_length=0)
        expected = np.array([np.nan, 1., 2., np.nan, np.nan])
        assert_equal(arr, expected)

    @pytest.mark.parametrize("mode", ["minimum", "maximum"])
    def test_zero_stat_length_invalid(self, mode):
        match = "stat_length of 0 yields no value for padding"
        with pytest.raises(ValueError, match=match):
            np.pad([1., 2.], 0, mode, stat_length=0)
        with pytest.raises(ValueError, match=match):
            np.pad([1., 2.], 0, mode, stat_length=(1, 0))
        with pytest.raises(ValueError, match=match):
            np.pad([1., 2.], 1, mode, stat_length=0)
        with pytest.raises(ValueError, match=match):
            np.pad([1., 2.], 1, mode, stat_length=(1, 0))


class TestConstant:
    def test_check_constant(self):
        a = np.arange(100)
        a = np.pad(a, (25, 20), 'constant', constant_values=(10, 20))
        b = np.array(
            [10, 10, 10, 10, 10, 10, 10, 10, 10, 10,
             10, 10, 10, 10, 10, 10, 10, 10, 10, 10,
             10, 10, 10, 10, 10,

             0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
             20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
             30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
             40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
             50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
             60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
             70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
             80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
             90, 91, 92, 93, 94, 95, 96, 97, 98, 99,

             20, 20, 20, 20, 20, 20, 20, 20, 20, 20,
             20, 20, 20, 20, 20, 20, 20, 20, 20, 20]
            )
        assert_array_equal(a, b)

    def test_check_constant_zeros(self):
        a = np.arange(100)
        a = np.pad(a, (25, 20), 'constant')
        b = np.array(
            [ 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
              0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
              0,  0,  0,  0,  0,

             0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
             20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
             30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
             40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
             50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
             60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
             70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
             80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
             90, 91, 92, 93, 94, 95, 96, 97, 98, 99,

              0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
              0,  0,  0,  0,  0,  0,  0,  0,  0,  0]
            )
        assert_array_equal(a, b)

    def test_check_constant_float(self):
        # If input array is int, but constant_values are float, the dtype of
        # the array to be padded is kept
        arr = np.arange(30).reshape(5, 6)
        test = np.pad(arr, (1, 2), mode='constant',
                   constant_values=1.1)
        expected = np.array(
            [[1,  1,  1,  1,  1,  1,  1,  1,  1],

             [1,  0,  1,  2,  3,  4,  5,  1,  1],
             [1,  6,  7,  8,  9, 10, 11,  1,  1],
             [1, 12, 13, 14, 15, 16, 17,  1,  1],
             [1, 18, 19, 20, 21, 22, 23,  1,  1],
             [1, 24, 25, 26, 27, 28, 29,  1,  1],

             [1,  1,  1,  1,  1,  1,  1,  1,  1],
             [1,  1,  1,  1,  1,  1,  1,  1,  1]]
            )
        assert_allclose(test, expected)

    def test_check_constant_float2(self):
        # If input array is float, and constant_values are float, the dtype of
        # the array to be padded is kept - here retaining the float constants
        arr = np.arange(30).reshape(5, 6)
        arr_float = arr.astype(np.float64)
        test = np.pad(arr_float, ((1, 2), (1, 2)), mode='constant',
                   constant_values=1.1)
        expected = np.array(
            [[1.1,   1.1,   1.1,   1.1,   1.1,   1.1,   1.1,   1.1,   1.1],

             [1.1,   0. ,   1. ,   2. ,   3. ,   4. ,   5. ,   1.1,   1.1],  # noqa: E203
             [1.1,   6. ,   7. ,   8. ,   9. ,  10. ,  11. ,   1.1,   1.1],  # noqa: E203
             [1.1,  12. ,  13. ,  14. ,  15. ,  16. ,  17. ,   1.1,   1.1],  # noqa: E203
             [1.1,  18. ,  19. ,  20. ,  21. ,  22. ,  23. ,   1.1,   1.1],  # noqa: E203
             [1.1,  24. ,  25. ,  26. ,  27. ,  28. ,  29. ,   1.1,   1.1],  # noqa: E203

             [1.1,   1.1,   1.1,   1.1,   1.1,   1.1,   1.1,   1.1,   1.1],
             [1.1,   1.1,   1.1,   1.1,   1.1,   1.1,   1.1,   1.1,   1.1]]
            )
        assert_allclose(test, expected)

    def test_check_constant_float3(self):
        a = np.arange(100, dtype=float)
        a = np.pad(a, (25, 20), 'constant', constant_values=(-1.1, -1.2))
        b = np.array(
            [-1.1, -1.1, -1.1, -1.1, -1.1, -1.1, -1.1, -1.1, -1.1, -1.1,
             -1.1, -1.1, -1.1, -1.1, -1.1, -1.1, -1.1, -1.1, -1.1, -1.1,
             -1.1, -1.1, -1.1, -1.1, -1.1,

             0,  1,  2,  3,  4,  5,  6,  7,  8,  9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
             20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
             30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
             40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
             50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
             60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
             70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
             80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
             90, 91, 92, 93, 94, 95, 96, 97, 98, 99,

             -1.2, -1.2, -1.2, -1.2, -1.2, -1.2, -1.2, -1.2, -1.2, -1.2,
             -1.2, -1.2, -1.2, -1.2, -1.2, -1.2, -1.2, -1.2, -1.2, -1.2]
            )
        assert_allclose(a, b)

    def test_check_constant_odd_pad_amount(self):
        arr = np.arange(30).reshape(5, 6)
        test = np.pad(arr, ((1,), (2,)), mode='constant',
                   constant_values=3)
        expected = np.array(
            [[3,  3,  3,  3,  3,  3,  3,  3,  3,  3],

             [3,  3,  0,  1,  2,  3,  4,  5,  3,  3],
             [3,  3,  6,  7,  8,  9, 10, 11,  3,  3],
             [3,  3, 12, 13, 14, 15, 16, 17,  3,  3],
             [3,  3, 18, 19, 20, 21, 22, 23,  3,  3],
             [3,  3, 24, 25, 26, 27, 28, 29,  3,  3],

             [3,  3,  3,  3,  3,  3,  3,  3,  3,  3]]
            )
        assert_allclose(test, expected)

    def test_check_constant_pad_2d(self):
        arr = np.arange(4).reshape(2, 2)
        test = np.pad(arr, ((1, 2), (1, 3)), mode='constant',
                          constant_values=((1, 2), (3, 4)))
        expected = np.array(
            [[3, 1, 1, 4, 4, 4],
             [3, 0, 1, 4, 4, 4],
             [3, 2, 3, 4, 4, 4],
             [3, 2, 2, 4, 4, 4],
             [3, 2, 2, 4, 4, 4]]
        )
        assert_allclose(test, expected)

    def test_check_large_integers(self):
        uint64_max = 2 ** 64 - 1
        arr = np.full(5, uint64_max, dtype=np.uint64)
        test = np.pad(arr, 1, mode="constant", constant_values=arr.min())
        expected = np.full(7, uint64_max, dtype=np.uint64)
        assert_array_equal(test, expected)

        int64_max = 2 ** 63 - 1
        arr = np.full(5, int64_max, dtype=np.int64)
        test = np.pad(arr, 1, mode="constant", constant_values=arr.min())
        expected = np.full(7, int64_max, dtype=np.int64)
        assert_array_equal(test, expected)

    def test_check_object_array(self):
        arr = np.empty(1, dtype=object)
        obj_a = object()
        arr[0] = obj_a
        obj_b = object()
        obj_c = object()
        arr = np.pad(arr, pad_width=1, mode='constant',
                     constant_values=(obj_b, obj_c))

        expected = np.empty((3,), dtype=object)
        expected[0] = obj_b
        expected[1] = obj_a
        expected[2] = obj_c

        assert_array_equal(arr, expected)

    def test_pad_empty_dimension(self):
        arr = np.zeros((3, 0, 2))
        result = np.pad(arr, [(0,), (2,), (1,)], mode="constant")
        assert result.shape == (3, 4, 4)


class TestLinearRamp:
    def test_check_simple(self):
        a = np.arange(100).astype('f')
        a = np.pad(a, (25, 20), 'linear_ramp', end_values=(4, 5))
        b = np.array(
            [4.00, 3.84, 3.68, 3.52, 3.36, 3.20, 3.04, 2.88, 2.72, 2.56,
             2.40, 2.24, 2.08, 1.92, 1.76, 1.60, 1.44, 1.28, 1.12, 0.96,
             0.80, 0.64, 0.48, 0.32, 0.16,

             0.00, 1.00, 2.00, 3.00, 4.00, 5.00, 6.00, 7.00, 8.00, 9.00,
             10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0,
             20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0, 29.0,
             30.0, 31.0, 32.0, 33.0, 34.0, 35.0, 36.0, 37.0, 38.0, 39.0,
             40.0, 41.0, 42.0, 43.0, 44.0, 45.0, 46.0, 47.0, 48.0, 49.0,
             50.0, 51.0, 52.0, 53.0, 54.0, 55.0, 56.0, 57.0, 58.0, 59.0,
             60.0, 61.0, 62.0, 63.0, 64.0, 65.0, 66.0, 67.0, 68.0, 69.0,
             70.0, 71.0, 72.0, 73.0, 74.0, 75.0, 76.0, 77.0, 78.0, 79.0,
             80.0, 81.0, 82.0, 83.0, 84.0, 85.0, 86.0, 87.0, 88.0, 89.0,
             90.0, 91.0, 92.0, 93.0, 94.0, 95.0, 96.0, 97.0, 98.0, 99.0,

             94.3, 89.6, 84.9, 80.2, 75.5, 70.8, 66.1, 61.4, 56.7, 52.0,
             47.3, 42.6, 37.9, 33.2, 28.5, 23.8, 19.1, 14.4, 9.7, 5.]
            )
        assert_allclose(a, b, rtol=1e-5, atol=1e-5)

    def test_check_2d(self):
        arr = np.arange(20).reshape(4, 5).astype(np.float64)
        test = np.pad(arr, (2, 2), mode='linear_ramp', end_values=(0, 0))
        expected = np.array(
            [[0.,   0.,   0.,   0.,   0.,   0.,   0.,    0.,   0.],
             [0.,   0.,   0.,  0.5,   1.,  1.5,   2.,    1.,   0.],
             [0.,   0.,   0.,   1.,   2.,   3.,   4.,    2.,   0.],
             [0.,  2.5,   5.,   6.,   7.,   8.,   9.,   4.5,   0.],
             [0.,   5.,  10.,  11.,  12.,  13.,  14.,    7.,   0.],
             [0.,  7.5,  15.,  16.,  17.,  18.,  19.,   9.5,   0.],
             [0., 3.75,  7.5,   8.,  8.5,   9.,  9.5,  4.75,   0.],
             [0.,   0.,   0.,   0.,   0.,   0.,   0.,    0.,   0.]])
        assert_allclose(test, expected)

    @pytest.mark.xfail(exceptions=(AssertionError,))
    def test_object_array(self):
        from fractions import Fraction
        arr = np.array([Fraction(1, 2), Fraction(-1, 2)])
        actual = np.pad(arr, (2, 3), mode='linear_ramp', end_values=0)

        # deliberately chosen to have a non-power-of-2 denominator such that
        # rounding to floats causes a failure.
        expected = np.array([
            Fraction( 0, 12),
            Fraction( 3, 12),
            Fraction( 6, 12),
            Fraction(-6, 12),
            Fraction(-4, 12),
            Fraction(-2, 12),
            Fraction(-0, 12),
        ])
        assert_equal(actual, expected)

    def test_end_values(self):
        """Ensure that end values are exact."""
        a = np.pad(np.ones(10).reshape(2, 5), (223, 123), mode="linear_ramp")
        assert_equal(a[:, 0], 0.)
        assert_equal(a[:, -1], 0.)
        assert_equal(a[0, :], 0.)
        assert_equal(a[-1, :], 0.)

    @pytest.mark.parametrize("dtype", _numeric_dtypes)
    def test_negative_difference(self, dtype):
        """
        Check correct behavior of unsigned dtypes if there is a negative
        difference between the edge to pad and `end_values`. Check both cases
        to be independent of implementation. Test behavior for all other dtypes
        in case dtype casting interferes with complex dtypes. See gh-14191.
        """
        x = np.array([3], dtype=dtype)
        result = np.pad(x, 3, mode="linear_ramp", end_values=0)
        expected = np.array([0, 1, 2, 3, 2, 1, 0], dtype=dtype)
        assert_equal(result, expected)

        x = np.array([0], dtype=dtype)
        result = np.pad(x, 3, mode="linear_ramp", end_values=3)
        expected = np.array([3, 2, 1, 0, 1, 2, 3], dtype=dtype)
        assert_equal(result, expected)


class TestReflect:
    def test_check_simple(self):
        a = np.arange(100)
        a = np.pad(a, (25, 20), 'reflect')
        b = np.array(
            [25, 24, 23, 22, 21, 20, 19, 18, 17, 16,
             15, 14, 13, 12, 11, 10, 9, 8, 7, 6,
             5, 4, 3, 2, 1,

             0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
             20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
             30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
             40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
             50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
             60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
             70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
             80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
             90, 91, 92, 93, 94, 95, 96, 97, 98, 99,

             98, 97, 96, 95, 94, 93, 92, 91, 90, 89,
             88, 87, 86, 85, 84, 83, 82, 81, 80, 79]
            )
        assert_array_equal(a, b)

    def test_check_odd_method(self):
        a = np.arange(100)
        a = np.pad(a, (25, 20), 'reflect', reflect_type='odd')
        b = np.array(
            [-25, -24, -23, -22, -21, -20, -19, -18, -17, -16,
             -15, -14, -13, -12, -11, -10, -9, -8, -7, -6,
             -5, -4, -3, -2, -1,

             0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
             20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
             30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
             40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
             50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
             60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
             70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
             80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
             90, 91, 92, 93, 94, 95, 96, 97, 98, 99,

             100, 101, 102, 103, 104, 105, 106, 107, 108, 109,
             110, 111, 112, 113, 114, 115, 116, 117, 118, 119]
            )
        assert_array_equal(a, b)

    def test_check_large_pad(self):
        a = [[4, 5, 6], [6, 7, 8]]
        a = np.pad(a, (5, 7), 'reflect')
        b = np.array(
            [[7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7],

             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7],

             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7, 8, 7, 6, 7],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5]]
            )
        assert_array_equal(a, b)

    def test_check_shape(self):
        a = [[4, 5, 6]]
        a = np.pad(a, (5, 7), 'reflect')
        b = np.array(
            [[5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],

             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],

             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5],
             [5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5, 6, 5, 4, 5]]
            )
        assert_array_equal(a, b)

    def test_check_01(self):
        a = np.pad([1, 2, 3], 2, 'reflect')
        b = np.array([3, 2, 1, 2, 3, 2, 1])
        assert_array_equal(a, b)

    def test_check_02(self):
        a = np.pad([1, 2, 3], 3, 'reflect')
        b = np.array([2, 3, 2, 1, 2, 3, 2, 1, 2])
        assert_array_equal(a, b)

    def test_check_03(self):
        a = np.pad([1, 2, 3], 4, 'reflect')
        b = np.array([1, 2, 3, 2, 1, 2, 3, 2, 1, 2, 3])
        assert_array_equal(a, b)

    def test_check_04(self):
        a = np.pad([1, 2, 3], [1, 10], 'reflect')
        b = np.array([2, 1, 2, 3, 2, 1, 2, 3, 2, 1, 2, 3, 2, 1])
        assert_array_equal(a, b)

    def test_check_05(self):
        a = np.pad([1, 2, 3, 4], [45, 10], 'reflect')
        b = np.array(
            [4, 3, 2, 1, 2, 3, 4, 3, 2, 1,
             2, 3, 4, 3, 2, 1, 2, 3, 4, 3,
             2, 1, 2, 3, 4, 3, 2, 1, 2, 3,
             4, 3, 2, 1, 2, 3, 4, 3, 2, 1,
             2, 3, 4, 3, 2, 1, 2, 3, 4, 3,
             2, 1, 2, 3, 4, 3, 2, 1, 2])
        assert_array_equal(a, b)

    def test_check_06(self):
        a = np.pad([1, 2, 3, 4], [15, 2], 'symmetric')
        b = np.array(
            [2, 3, 4, 4, 3, 2, 1, 1, 2, 3,
             4, 4, 3, 2, 1, 1, 2, 3, 4, 4,
             3]
        )
        assert_array_equal(a, b)

    def test_check_07(self):
        a = np.pad([1, 2, 3, 4, 5, 6], [45, 3], 'symmetric')
        b = np.array(
            [4, 5, 6, 6, 5, 4, 3, 2, 1, 1,
             2, 3, 4, 5, 6, 6, 5, 4, 3, 2,
             1, 1, 2, 3, 4, 5, 6, 6, 5, 4,
             3, 2, 1, 1, 2, 3, 4, 5, 6, 6,
             5, 4, 3, 2, 1, 1, 2, 3, 4, 5,
             6, 6, 5, 4])
        assert_array_equal(a, b)


class TestEmptyArray:
    """Check how padding behaves on arrays with an empty dimension."""

    @pytest.mark.parametrize(
        # Keep parametrization ordered, otherwise pytest-xdist might believe
        # that different tests were collected during parallelization
        "mode", sorted(_all_modes.keys() - {"constant", "empty"})
    )
    def test_pad_empty_dimension(self, mode):
        match = ("can't extend empty axis 0 using modes other than 'constant' "
                 "or 'empty'")
        with pytest.raises(ValueError, match=match):
            np.pad([], 4, mode=mode)
        with pytest.raises(ValueError, match=match):
            np.pad(np.ndarray(0), 4, mode=mode)
        with pytest.raises(ValueError, match=match):
            np.pad(np.zeros((0, 3)), ((1,), (0,)), mode=mode)

    @pytest.mark.parametrize("mode", _all_modes.keys())
    def test_pad_non_empty_dimension(self, mode):
        result = np.pad(np.ones((2, 0, 2)), ((3,), (0,), (1,)), mode=mode)
        assert result.shape == (8, 0, 4)


class TestSymmetric:
    def test_check_simple(self):
        a = np.arange(100)
        a = np.pad(a, (25, 20), 'symmetric')
        b = np.array(
            [24, 23, 22, 21, 20, 19, 18, 17, 16, 15,
             14, 13, 12, 11, 10, 9, 8, 7, 6, 5,
             4, 3, 2, 1, 0,

             0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
             20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
             30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
             40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
             50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
             60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
             70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
             80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
             90, 91, 92, 93, 94, 95, 96, 97, 98, 99,

             99, 98, 97, 96, 95, 94, 93, 92, 91, 90,
             89, 88, 87, 86, 85, 84, 83, 82, 81, 80]
            )
        assert_array_equal(a, b)

    def test_check_odd_method(self):
        a = np.arange(100)
        a = np.pad(a, (25, 20), 'symmetric', reflect_type='odd')
        b = np.array(
            [-24, -23, -22, -21, -20, -19, -18, -17, -16, -15,
             -14, -13, -12, -11, -10, -9, -8, -7, -6, -5,
             -4, -3, -2, -1, 0,

             0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
             20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
             30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
             40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
             50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
             60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
             70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
             80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
             90, 91, 92, 93, 94, 95, 96, 97, 98, 99,

             99, 100, 101, 102, 103, 104, 105, 106, 107, 108,
             109, 110, 111, 112, 113, 114, 115, 116, 117, 118]
            )
        assert_array_equal(a, b)

    def test_check_large_pad(self):
        a = [[4, 5, 6], [6, 7, 8]]
        a = np.pad(a, (5, 7), 'symmetric')
        b = np.array(
            [[5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [7, 8, 8, 7, 6, 6, 7, 8, 8, 7, 6, 6, 7, 8, 8],
             [7, 8, 8, 7, 6, 6, 7, 8, 8, 7, 6, 6, 7, 8, 8],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],

             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [7, 8, 8, 7, 6, 6, 7, 8, 8, 7, 6, 6, 7, 8, 8],

             [7, 8, 8, 7, 6, 6, 7, 8, 8, 7, 6, 6, 7, 8, 8],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [7, 8, 8, 7, 6, 6, 7, 8, 8, 7, 6, 6, 7, 8, 8],
             [7, 8, 8, 7, 6, 6, 7, 8, 8, 7, 6, 6, 7, 8, 8],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6]]
            )

        assert_array_equal(a, b)

    def test_check_large_pad_odd(self):
        a = [[4, 5, 6], [6, 7, 8]]
        a = np.pad(a, (5, 7), 'symmetric', reflect_type='odd')
        b = np.array(
            [[-3, -2, -2, -1,  0,  0,  1,  2,  2,  3,  4,  4,  5,  6,  6],
             [-3, -2, -2, -1,  0,  0,  1,  2,  2,  3,  4,  4,  5,  6,  6],
             [-1,  0,  0,  1,  2,  2,  3,  4,  4,  5,  6,  6,  7,  8,  8],
             [-1,  0,  0,  1,  2,  2,  3,  4,  4,  5,  6,  6,  7,  8,  8],
             [ 1,  2,  2,  3,  4,  4,  5,  6,  6,  7,  8,  8,  9, 10, 10],

             [ 1,  2,  2,  3,  4,  4,  5,  6,  6,  7,  8,  8,  9, 10, 10],
             [ 3,  4,  4,  5,  6,  6,  7,  8,  8,  9, 10, 10, 11, 12, 12],

             [ 3,  4,  4,  5,  6,  6,  7,  8,  8,  9, 10, 10, 11, 12, 12],
             [ 5,  6,  6,  7,  8,  8,  9, 10, 10, 11, 12, 12, 13, 14, 14],
             [ 5,  6,  6,  7,  8,  8,  9, 10, 10, 11, 12, 12, 13, 14, 14],
             [ 7,  8,  8,  9, 10, 10, 11, 12, 12, 13, 14, 14, 15, 16, 16],
             [ 7,  8,  8,  9, 10, 10, 11, 12, 12, 13, 14, 14, 15, 16, 16],
             [ 9, 10, 10, 11, 12, 12, 13, 14, 14, 15, 16, 16, 17, 18, 18],
             [ 9, 10, 10, 11, 12, 12, 13, 14, 14, 15, 16, 16, 17, 18, 18]]
            )
        assert_array_equal(a, b)

    def test_check_shape(self):
        a = [[4, 5, 6]]
        a = np.pad(a, (5, 7), 'symmetric')
        b = np.array(
            [[5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],

             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],

             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6],
             [5, 6, 6, 5, 4, 4, 5, 6, 6, 5, 4, 4, 5, 6, 6]]
            )
        assert_array_equal(a, b)

    def test_check_01(self):
        a = np.pad([1, 2, 3], 2, 'symmetric')
        b = np.array([2, 1, 1, 2, 3, 3, 2])
        assert_array_equal(a, b)

    def test_check_02(self):
        a = np.pad([1, 2, 3], 3, 'symmetric')
        b = np.array([3, 2, 1, 1, 2, 3, 3, 2, 1])
        assert_array_equal(a, b)

    def test_check_03(self):
        a = np.pad([1, 2, 3], 6, 'symmetric')
        b = np.array([1, 2, 3, 3, 2, 1, 1, 2, 3, 3, 2, 1, 1, 2, 3])
        assert_array_equal(a, b)


class TestWrap:
    def test_check_simple(self):
        a = np.arange(100)
        a = np.pad(a, (25, 20), 'wrap')
        b = np.array(
            [75, 76, 77, 78, 79, 80, 81, 82, 83, 84,
             85, 86, 87, 88, 89, 90, 91, 92, 93, 94,
             95, 96, 97, 98, 99,

             0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
             20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
             30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
             40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
             50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
             60, 61, 62, 63, 64, 65, 66, 67, 68, 69,
             70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
             80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
             90, 91, 92, 93, 94, 95, 96, 97, 98, 99,

             0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
            )
        assert_array_equal(a, b)

    def test_check_large_pad(self):
        a = np.arange(12)
        a = np.reshape(a, (3, 4))
        a = np.pad(a, (10, 12), 'wrap')
        b = np.array(
            [[10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10,
              11, 8, 9, 10, 11, 8, 9, 10, 11],
             [2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2,
              3, 0, 1, 2, 3, 0, 1, 2, 3],
             [6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6,
              7, 4, 5, 6, 7, 4, 5, 6, 7],
             [10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10,
              11, 8, 9, 10, 11, 8, 9, 10, 11],
             [2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2,
              3, 0, 1, 2, 3, 0, 1, 2, 3],
             [6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6,
              7, 4, 5, 6, 7, 4, 5, 6, 7],
             [10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10,
              11, 8, 9, 10, 11, 8, 9, 10, 11],
             [2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2,
              3, 0, 1, 2, 3, 0, 1, 2, 3],
             [6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6,
              7, 4, 5, 6, 7, 4, 5, 6, 7],
             [10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10,
              11, 8, 9, 10, 11, 8, 9, 10, 11],

             [2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2,
              3, 0, 1, 2, 3, 0, 1, 2, 3],
             [6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6,
              7, 4, 5, 6, 7, 4, 5, 6, 7],
             [10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10,
              11, 8, 9, 10, 11, 8, 9, 10, 11],

             [2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2,
              3, 0, 1, 2, 3, 0, 1, 2, 3],
             [6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6,
              7, 4, 5, 6, 7, 4, 5, 6, 7],
             [10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10,
              11, 8, 9, 10, 11, 8, 9, 10, 11],
             [2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2,
              3, 0, 1, 2, 3, 0, 1, 2, 3],
             [6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6,
              7, 4, 5, 6, 7, 4, 5, 6, 7],
             [10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10,
              11, 8, 9, 10, 11, 8, 9, 10, 11],
             [2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2,
              3, 0, 1, 2, 3, 0, 1, 2, 3],
             [6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6,
              7, 4, 5, 6, 7, 4, 5, 6, 7],
             [10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10,
              11, 8, 9, 10, 11, 8, 9, 10, 11],
             [2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2,
              3, 0, 1, 2, 3, 0, 1, 2, 3],
             [6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5, 6,
              7, 4, 5, 6, 7, 4, 5, 6, 7],
             [10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10, 11, 8, 9, 10,
              11, 8, 9, 10, 11, 8, 9, 10, 11]]
            )
        assert_array_equal(a, b)

    def test_check_01(self):
        a = np.pad([1, 2, 3], 3, 'wrap')
        b = np.array([1, 2, 3, 1, 2, 3, 1, 2, 3])
        assert_array_equal(a, b)

    def test_check_02(self):
        a = np.pad([1, 2, 3], 4, 'wrap')
        b = np.array([3, 1, 2, 3, 1, 2, 3, 1, 2, 3, 1])
        assert_array_equal(a, b)

    def test_pad_with_zero(self):
        a = np.ones((3, 5))
        b = np.pad(a, (0, 5), mode="wrap")
        assert_array_equal(a, b[:-5, :-5])

    def test_repeated_wrapping(self):
        """
        Check wrapping on each side individually if the wrapped area is longer
        than the original array.
        """
        a = np.arange(5)
        b = np.pad(a, (12, 0), mode="wrap")
        assert_array_equal(np.r_[a, a, a, a][3:], b)

        a = np.arange(5)
        b = np.pad(a, (0, 12), mode="wrap")
        assert_array_equal(np.r_[a, a, a, a][:-3], b)

    def test_repeated_wrapping_multiple_origin(self):
        """
        Assert that 'wrap' pads only with multiples of the original area if
        the pad width is larger than the original array.
        """
        a = np.arange(4).reshape(2, 2)
        a = np.pad(a, [(1, 3), (3, 1)], mode='wrap')
        b = np.array(
            [[3, 2, 3, 2, 3, 2],
             [1, 0, 1, 0, 1, 0],
             [3, 2, 3, 2, 3, 2],
             [1, 0, 1, 0, 1, 0],
             [3, 2, 3, 2, 3, 2],
             [1, 0, 1, 0, 1, 0]]
        )
        assert_array_equal(a, b)


class TestEdge:
    def test_check_simple(self):
        a = np.arange(12)
        a = np.reshape(a, (4, 3))
        a = np.pad(a, ((2, 3), (3, 2)), 'edge')
        b = np.array(
            [[0, 0, 0, 0, 1, 2, 2, 2],
             [0, 0, 0, 0, 1, 2, 2, 2],

             [0, 0, 0, 0, 1, 2, 2, 2],
             [3, 3, 3, 3, 4, 5, 5, 5],
             [6, 6, 6, 6, 7, 8, 8, 8],
             [9, 9, 9, 9, 10, 11, 11, 11],

             [9, 9, 9, 9, 10, 11, 11, 11],
             [9, 9, 9, 9, 10, 11, 11, 11],
             [9, 9, 9, 9, 10, 11, 11, 11]]
            )
        assert_array_equal(a, b)

    def test_check_width_shape_1_2(self):
        # Check a pad_width of the form ((1, 2),).
        # Regression test for issue gh-7808.
        a = np.array([1, 2, 3])
        padded = np.pad(a, ((1, 2),), 'edge')
        expected = np.array([1, 1, 2, 3, 3, 3])
        assert_array_equal(padded, expected)

        a = np.array([[1, 2, 3], [4, 5, 6]])
        padded = np.pad(a, ((1, 2),), 'edge')
        expected = np.pad(a, ((1, 2), (1, 2)), 'edge')
        assert_array_equal(padded, expected)

        a = np.arange(24).reshape(2, 3, 4)
        padded = np.pad(a, ((1, 2),), 'edge')
        expected = np.pad(a, ((1, 2), (1, 2), (1, 2)), 'edge')
        assert_array_equal(padded, expected)


class TestEmpty:
    def test_simple(self):
        arr = np.arange(24).reshape(4, 6)
        result = np.pad(arr, [(2, 3), (3, 1)], mode="empty")
        assert result.shape == (9, 10)
        assert_equal(arr, result[2:-3, 3:-1])

    def test_pad_empty_dimension(self):
        arr = np.zeros((3, 0, 2))
        result = np.pad(arr, [(0,), (2,), (1,)], mode="empty")
        assert result.shape == (3, 4, 4)


def test_legacy_vector_functionality():
    def _padwithtens(vector, pad_width, iaxis, kwargs):
        vector[:pad_width[0]] = 10
        vector[-pad_width[1]:] = 10

    a = np.arange(6).reshape(2, 3)
    a = np.pad(a, 2, _padwithtens)
    b = np.array(
        [[10, 10, 10, 10, 10, 10, 10],
         [10, 10, 10, 10, 10, 10, 10],

         [10, 10,  0,  1,  2, 10, 10],
         [10, 10,  3,  4,  5, 10, 10],

         [10, 10, 10, 10, 10, 10, 10],
         [10, 10, 10, 10, 10, 10, 10]]
        )
    assert_array_equal(a, b)


def test_unicode_mode():
    a = np.pad([1], 2, mode='constant')
    b = np.array([0, 0, 1, 0, 0])
    assert_array_equal(a, b)


@pytest.mark.parametrize("mode", ["edge", "symmetric", "reflect", "wrap"])
def test_object_input(mode):
    # Regression test for issue gh-11395.
    a = np.full((4, 3), fill_value=None)
    pad_amt = ((2, 3), (3, 2))
    b = np.full((9, 8), fill_value=None)
    assert_array_equal(np.pad(a, pad_amt, mode=mode), b)


class TestPadWidth:
    @pytest.mark.parametrize("pad_width", [
        (4, 5, 6, 7),
        ((1,), (2,), (3,)),
        ((1, 2), (3, 4), (5, 6)),
        ((3, 4, 5), (0, 1, 2)),
    ])
    @pytest.mark.parametrize("mode", _all_modes.keys())
    def test_misshaped_pad_width(self, pad_width, mode):
        arr = np.arange(30).reshape((6, 5))
        match = "operands could not be broadcast together"
        with pytest.raises(ValueError, match=match):
            np.pad(arr, pad_width, mode)

    @pytest.mark.parametrize("mode", _all_modes.keys())
    def test_misshaped_pad_width_2(self, mode):
        arr = np.arange(30).reshape((6, 5))
        match = ("input operand has more dimensions than allowed by the axis "
                 "remapping")
        with pytest.raises(ValueError, match=match):
            np.pad(arr, (((3,), (4,), (5,)), ((0,), (1,), (2,))), mode)

    @pytest.mark.parametrize(
        "pad_width", [-2, (-2,), (3, -1), ((5, 2), (-2, 3)), ((-4,), (2,))])
    @pytest.mark.parametrize("mode", _all_modes.keys())
    def test_negative_pad_width(self, pad_width, mode):
        arr = np.arange(30).reshape((6, 5))
        match = "index can't contain negative values"
        with pytest.raises(ValueError, match=match):
            np.pad(arr, pad_width, mode)

    @pytest.mark.parametrize("pad_width, dtype", [
        ("3", None),
        ("word", None),
        (None, None),
        (object(), None),
        (3.4, None),
        (((2, 3, 4), (3, 2)), object),
        (complex(1, -1), None),
        (((-2.1, 3), (3, 2)), None),
    ])
    @pytest.mark.parametrize("mode", _all_modes.keys())
    def test_bad_type(self, pad_width, dtype, mode):
        arr = np.arange(30).reshape((6, 5))
        match = "`pad_width` must be of integral type."
        if dtype is not None:
            # avoid DeprecationWarning when not specifying dtype
            with pytest.raises(TypeError, match=match):
                np.pad(arr, np.array(pad_width, dtype=dtype), mode)
        else:
            with pytest.raises(TypeError, match=match):
                np.pad(arr, pad_width, mode)
            with pytest.raises(TypeError, match=match):
                np.pad(arr, np.array(pad_width), mode)

    def test_pad_width_as_ndarray(self):
        a = np.arange(12)
        a = np.reshape(a, (4, 3))
        a = np.pad(a, np.array(((2, 3), (3, 2))), 'edge')
        b = np.array(
            [[0,  0,  0,    0,  1,  2,    2,  2],
             [0,  0,  0,    0,  1,  2,    2,  2],

             [0,  0,  0,    0,  1,  2,    2,  2],
             [3,  3,  3,    3,  4,  5,    5,  5],
             [6,  6,  6,    6,  7,  8,    8,  8],
             [9,  9,  9,    9, 10, 11,   11, 11],

             [9,  9,  9,    9, 10, 11,   11, 11],
             [9,  9,  9,    9, 10, 11,   11, 11],
             [9,  9,  9,    9, 10, 11,   11, 11]]
            )
        assert_array_equal(a, b)

    @pytest.mark.parametrize("pad_width", [0, (0, 0), ((0, 0), (0, 0))])
    @pytest.mark.parametrize("mode", _all_modes.keys())
    def test_zero_pad_width(self, pad_width, mode):
        arr = np.arange(30).reshape(6, 5)
        assert_array_equal(arr, np.pad(arr, pad_width, mode=mode))


@pytest.mark.parametrize("mode", _all_modes.keys())
def test_kwargs(mode):
    """Test behavior of pad's kwargs for the given mode."""
    allowed = _all_modes[mode]
    not_allowed = {}
    for kwargs in _all_modes.values():
        if kwargs != allowed:
            not_allowed.update(kwargs)
    # Test if allowed keyword arguments pass
    np.pad([1, 2, 3], 1, mode, **allowed)
    # Test if prohibited keyword arguments of other modes raise an error
    for key, value in not_allowed.items():
        match = f"unsupported keyword arguments for mode '{mode}'"
        with pytest.raises(ValueError, match=match):
            np.pad([1, 2, 3], 1, mode, **{key: value})


def test_constant_zero_default():
    arr = np.array([1, 1])
    assert_array_equal(np.pad(arr, 2), [0, 0, 1, 1, 0, 0])


@pytest.mark.parametrize("mode", [1, "const", object(), None, True, False])
def test_unsupported_mode(mode):
    match = f"mode '{mode}' is not supported"
    with pytest.raises(ValueError, match=match):
        np.pad([1, 2, 3], 4, mode=mode)


@pytest.mark.parametrize("mode", _all_modes.keys())
def test_non_contiguous_array(mode):
    arr = np.arange(24).reshape(4, 6)[::2, ::2]
    result = np.pad(arr, (2, 3), mode)
    assert result.shape == (7, 8)
    assert_equal(result[2:-3, 2:-3], arr)


@pytest.mark.parametrize("mode", _all_modes.keys())
def test_memory_layout_persistence(mode):
    """Test if C and F order is preserved for all pad modes."""
    x = np.ones((5, 10), order='C')
    assert np.pad(x, 5, mode).flags["C_CONTIGUOUS"]
    x = np.ones((5, 10), order='F')
    assert np.pad(x, 5, mode).flags["F_CONTIGUOUS"]


@pytest.mark.parametrize("dtype", _numeric_dtypes)
@pytest.mark.parametrize("mode", _all_modes.keys())
def test_dtype_persistence(dtype, mode):
    arr = np.zeros((3, 2, 1), dtype=dtype)
    result = np.pad(arr, 1, mode=mode)
    assert result.dtype == dtype

# === NexusCore/src\nexuscore\utils\test_utils.py ===
# C:\Users\USER\tools\OpenCodeInterpreter\src\utils\test_utils.py

import subprocess
import sys
import os
import locale # OSの言語設定を取得するためのライブラリをインポート

def run_tests(project_path: str) -> tuple[bool, str]:
    """
    指定されたプロジェクトパスでpytestを実行し、成功したかどうかと、
    その出力結果を返します。
    """
    try:
        python_executable = sys.executable
        
        # --- ★★★★★ ここが最重要修正点 ★★★★★ ---
        # OSが使用しているデフォルトの文字コード（方言）を自動で取得します。
        # これにより、Windows, Mac, Linuxなど、どの環境でも柔軟に対応できます。
        preferred_encoding = locale.getpreferredencoding(False)
        print(f"🔧 使用する文字コード: {preferred_encoding}")

        result = subprocess.run(
            [python_executable, "-m", "pytest"],
            cwd=project_path,
            capture_output=True,
            text=True,
            encoding=preferred_encoding, # 自動取得した文字コードを使用
            errors='replace',            # 万が一変換できない文字があっても、?に置き換えて処理を続行する
            check=False
        )
        
        # UnicodeDecodeErrorで結果がNoneになる可能性を考慮し、安全に結合します。
        stdout = result.stdout if result.stdout is not None else ""
        stderr = result.stderr if result.stderr is not None else ""
        output = stdout + "\n" + stderr
        
        return result.returncode == 0, output

    except FileNotFoundError:
        return False, "pytestコマンドが見つかりませんでした。仮想環境が有効で、pytestがインストールされているか確認してください。"
    except Exception as e:
        return False, f"テスト実行中に予期せぬエラーが発生しました: {e}"


# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\utils\test_utils.py ===
# C:\Users\USER\tools\OpenCodeInterpreter\src\utils\test_utils.py

import subprocess
import sys
import os
import locale # OSの言語設定を取得するためのライブラリをインポート

def run_tests(project_path: str) -> tuple[bool, str]:
    """
    指定されたプロジェクトパスでpytestを実行し、成功したかどうかと、
    その出力結果を返します。
    """
    try:
        python_executable = sys.executable
        
        # --- ★★★★★ ここが最重要修正点 ★★★★★ ---
        # OSが使用しているデフォルトの文字コード（方言）を自動で取得します。
        # これにより、Windows, Mac, Linuxなど、どの環境でも柔軟に対応できます。
        preferred_encoding = locale.getpreferredencoding(False)
        print(f"🔧 使用する文字コード: {preferred_encoding}")

        result = subprocess.run(
            [python_executable, "-m", "pytest"],
            cwd=project_path,
            capture_output=True,
            text=True,
            encoding=preferred_encoding, # 自動取得した文字コードを使用
            errors='replace',            # 万が一変換できない文字があっても、?に置き換えて処理を続行する
            check=False
        )
        
        # UnicodeDecodeErrorで結果がNoneになる可能性を考慮し、安全に結合します。
        stdout = result.stdout if result.stdout is not None else ""
        stderr = result.stderr if result.stderr is not None else ""
        output = stdout + "\n" + stderr
        
        return result.returncode == 0, output

    except FileNotFoundError:
        return False, "pytestコマンドが見つかりませんでした。仮想環境が有効で、pytestがインストールされているか確認してください。"
    except Exception as e:
        return False, f"テスト実行中に予期せぬエラーが発生しました: {e}"


# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\utils\test_utils.py ===
# C:\Users\USER\tools\OpenCodeInterpreter\src\utils\test_utils.py

import subprocess
import sys
import os
import locale # OSの言語設定を取得するためのライブラリをインポート

def run_tests(project_path: str) -> tuple[bool, str]:
    """
    指定されたプロジェクトパスでpytestを実行し、成功したかどうかと、
    その出力結果を返します。
    """
    try:
        python_executable = sys.executable
        
        # --- ★★★★★ ここが最重要修正点 ★★★★★ ---
        # OSが使用しているデフォルトの文字コード（方言）を自動で取得します。
        # これにより、Windows, Mac, Linuxなど、どの環境でも柔軟に対応できます。
        preferred_encoding = locale.getpreferredencoding(False)
        print(f"🔧 使用する文字コード: {preferred_encoding}")

        result = subprocess.run(
            [python_executable, "-m", "pytest"],
            cwd=project_path,
            capture_output=True,
            text=True,
            encoding=preferred_encoding, # 自動取得した文字コードを使用
            errors='replace',            # 万が一変換できない文字があっても、?に置き換えて処理を続行する
            check=False
        )
        
        # UnicodeDecodeErrorで結果がNoneになる可能性を考慮し、安全に結合します。
        stdout = result.stdout if result.stdout is not None else ""
        stderr = result.stderr if result.stderr is not None else ""
        output = stdout + "\n" + stderr
        
        return result.returncode == 0, output

    except FileNotFoundError:
        return False, "pytestコマンドが見つかりませんでした。仮想環境が有効で、pytestがインストールされているか確認してください。"
    except Exception as e:
        return False, f"テスト実行中に予期せぬエラーが発生しました: {e}"


# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\tools\exports\export_20250803_114325\source_code\NexusCore\src\utils\test_utils.py ===
# C:\Users\USER\tools\OpenCodeInterpreter\src\utils\test_utils.py

import subprocess
import sys
import os
import locale # OSの言語設定を取得するためのライブラリをインポート

def run_tests(project_path: str) -> tuple[bool, str]:
    """
    指定されたプロジェクトパスでpytestを実行し、成功したかどうかと、
    その出力結果を返します。
    """
    try:
        python_executable = sys.executable
        
        # --- ★★★★★ ここが最重要修正点 ★★★★★ ---
        # OSが使用しているデフォルトの文字コード（方言）を自動で取得します。
        # これにより、Windows, Mac, Linuxなど、どの環境でも柔軟に対応できます。
        preferred_encoding = locale.getpreferredencoding(False)
        print(f"🔧 使用する文字コード: {preferred_encoding}")

        result = subprocess.run(
            [python_executable, "-m", "pytest"],
            cwd=project_path,
            capture_output=True,
            text=True,
            encoding=preferred_encoding, # 自動取得した文字コードを使用
            errors='replace',            # 万が一変換できない文字があっても、?に置き換えて処理を続行する
            check=False
        )
        
        # UnicodeDecodeErrorで結果がNoneになる可能性を考慮し、安全に結合します。
        stdout = result.stdout if result.stdout is not None else ""
        stderr = result.stderr if result.stderr is not None else ""
        output = stdout + "\n" + stderr
        
        return result.returncode == 0, output

    except FileNotFoundError:
        return False, "pytestコマンドが見つかりませんでした。仮想環境が有効で、pytestがインストールされているか確認してください。"
    except Exception as e:
        return False, f"テスト実行中に予期せぬエラーが発生しました: {e}"


# === NexusCore/exported_projects\app_20250703_223016\app\forms.py ===
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

# === NexusCore/exported_projects\project_export_m73owrzi\app\forms.py ===
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

# === NexusCore/exported_projects\project_export_xb_l70t8\app\forms.py ===
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

# === NexusCore/exported_projects\project_export_y7xxp1v8\app\forms.py ===
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

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\app_20250703_223016\app\forms.py ===
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

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\project_export_m73owrzi\app\forms.py ===
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

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\project_export_xb_l70t8\app\forms.py ===
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

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\project_export_y7xxp1v8\app\forms.py ===
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

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\exported_projects\app_20250703_223016\app\forms.py ===
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

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\exported_projects\project_export_m73owrzi\app\forms.py ===
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

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\exported_projects\project_export_xb_l70t8\app\forms.py ===
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

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\exported_projects\project_export_y7xxp1v8\app\forms.py ===
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

# === NexusCore/openenv\Lib\site-packages\win32\lib\winnt.py ===
# Generated by h2py from \mssdk\include\winnt.h

APPLICATION_ERROR_MASK = 536870912
ERROR_SEVERITY_SUCCESS = 0
ERROR_SEVERITY_INFORMATIONAL = 1073741824
ERROR_SEVERITY_WARNING = -2147483648
ERROR_SEVERITY_ERROR = -1073741824
MINCHAR = 128
MAXCHAR = 127
MINSHORT = 32768
MAXSHORT = 32767
MINLONG = -2147483648
MAXLONG = 2147483647
MAXBYTE = 255
MAXWORD = 65535
MAXDWORD = -1
LANG_NEUTRAL = 0
LANG_AFRIKAANS = 54
LANG_ALBANIAN = 28
LANG_ARABIC = 1
LANG_BASQUE = 45
LANG_BELARUSIAN = 35
LANG_BULGARIAN = 2
LANG_CATALAN = 3
LANG_CHINESE = 4
LANG_CROATIAN = 26
LANG_CZECH = 5
LANG_DANISH = 6
LANG_DUTCH = 19
LANG_ENGLISH = 9
LANG_ESTONIAN = 37
LANG_FAEROESE = 56
LANG_FARSI = 41
LANG_FINNISH = 11
LANG_FRENCH = 12
LANG_GERMAN = 7
LANG_GREEK = 8
LANG_HEBREW = 13
LANG_HINDI = 57
LANG_HUNGARIAN = 14
LANG_ICELANDIC = 15
LANG_INDONESIAN = 33
LANG_ITALIAN = 16
LANG_JAPANESE = 17
LANG_KOREAN = 18
LANG_LATVIAN = 38
LANG_LITHUANIAN = 39
LANG_MACEDONIAN = 47
LANG_MALAY = 62
LANG_NORWEGIAN = 20
LANG_POLISH = 21
LANG_PORTUGUESE = 22
LANG_ROMANIAN = 24
LANG_RUSSIAN = 25
LANG_SERBIAN = 26
LANG_SLOVAK = 27
LANG_SLOVENIAN = 36
LANG_SPANISH = 10
LANG_SWAHILI = 65
LANG_SWEDISH = 29
LANG_THAI = 30
LANG_TURKISH = 31
LANG_UKRAINIAN = 34
LANG_VIETNAMESE = 42
SUBLANG_NEUTRAL = 0
SUBLANG_DEFAULT = 1
SUBLANG_SYS_DEFAULT = 2
SUBLANG_ARABIC_SAUDI_ARABIA = 1
SUBLANG_ARABIC_IRAQ = 2
SUBLANG_ARABIC_EGYPT = 3
SUBLANG_ARABIC_LIBYA = 4
SUBLANG_ARABIC_ALGERIA = 5
SUBLANG_ARABIC_MOROCCO = 6
SUBLANG_ARABIC_TUNISIA = 7
SUBLANG_ARABIC_OMAN = 8
SUBLANG_ARABIC_YEMEN = 9
SUBLANG_ARABIC_SYRIA = 10
SUBLANG_ARABIC_JORDAN = 11
SUBLANG_ARABIC_LEBANON = 12
SUBLANG_ARABIC_KUWAIT = 13
SUBLANG_ARABIC_UAE = 14
SUBLANG_ARABIC_BAHRAIN = 15
SUBLANG_ARABIC_QATAR = 16
SUBLANG_CHINESE_TRADITIONAL = 1
SUBLANG_CHINESE_SIMPLIFIED = 2
SUBLANG_CHINESE_HONGKONG = 3
SUBLANG_CHINESE_SINGAPORE = 4
SUBLANG_CHINESE_MACAU = 5
SUBLANG_DUTCH = 1
SUBLANG_DUTCH_BELGIAN = 2
SUBLANG_ENGLISH_US = 1
SUBLANG_ENGLISH_UK = 2
SUBLANG_ENGLISH_AUS = 3
SUBLANG_ENGLISH_CAN = 4
SUBLANG_ENGLISH_NZ = 5
SUBLANG_ENGLISH_EIRE = 6
SUBLANG_ENGLISH_SOUTH_AFRICA = 7
SUBLANG_ENGLISH_JAMAICA = 8
SUBLANG_ENGLISH_CARIBBEAN = 9
SUBLANG_ENGLISH_BELIZE = 10
SUBLANG_ENGLISH_TRINIDAD = 11
SUBLANG_ENGLISH_ZIMBABWE = 12
SUBLANG_ENGLISH_PHILIPPINES = 13
SUBLANG_FRENCH = 1
SUBLANG_FRENCH_BELGIAN = 2
SUBLANG_FRENCH_CANADIAN = 3
SUBLANG_FRENCH_SWISS = 4
SUBLANG_FRENCH_LUXEMBOURG = 5
SUBLANG_FRENCH_MONACO = 6
SUBLANG_GERMAN = 1
SUBLANG_GERMAN_SWISS = 2
SUBLANG_GERMAN_AUSTRIAN = 3
SUBLANG_GERMAN_LUXEMBOURG = 4
SUBLANG_GERMAN_LIECHTENSTEIN = 5
SUBLANG_ITALIAN = 1
SUBLANG_ITALIAN_SWISS = 2
SUBLANG_KOREAN = 1
SUBLANG_KOREAN_JOHAB = 2
SUBLANG_LITHUANIAN = 1
SUBLANG_LITHUANIAN_CLASSIC = 2
SUBLANG_MALAY_MALAYSIA = 1
SUBLANG_MALAY_BRUNEI_DARUSSALAM = 2
SUBLANG_NORWEGIAN_BOKMAL = 1
SUBLANG_NORWEGIAN_NYNORSK = 2
SUBLANG_PORTUGUESE = 2
SUBLANG_PORTUGUESE_BRAZILIAN = 1
SUBLANG_SERBIAN_LATIN = 2
SUBLANG_SERBIAN_CYRILLIC = 3
SUBLANG_SPANISH = 1
SUBLANG_SPANISH_MEXICAN = 2
SUBLANG_SPANISH_MODERN = 3
SUBLANG_SPANISH_GUATEMALA = 4
SUBLANG_SPANISH_COSTA_RICA = 5
SUBLANG_SPANISH_PANAMA = 6
SUBLANG_SPANISH_DOMINICAN_REPUBLIC = 7
SUBLANG_SPANISH_VENEZUELA = 8
SUBLANG_SPANISH_COLOMBIA = 9
SUBLANG_SPANISH_PERU = 10
SUBLANG_SPANISH_ARGENTINA = 11
SUBLANG_SPANISH_ECUADOR = 12
SUBLANG_SPANISH_CHILE = 13
SUBLANG_SPANISH_URUGUAY = 14
SUBLANG_SPANISH_PARAGUAY = 15
SUBLANG_SPANISH_BOLIVIA = 16
SUBLANG_SPANISH_EL_SALVADOR = 17
SUBLANG_SPANISH_HONDURAS = 18
SUBLANG_SPANISH_NICARAGUA = 19
SUBLANG_SPANISH_PUERTO_RICO = 20
SUBLANG_SWEDISH = 1
SUBLANG_SWEDISH_FINLAND = 2
SORT_DEFAULT = 0
SORT_JAPANESE_XJIS = 0
SORT_JAPANESE_UNICODE = 1
SORT_CHINESE_BIG5 = 0
SORT_CHINESE_PRCP = 0
SORT_CHINESE_UNICODE = 1
SORT_CHINESE_PRC = 2
SORT_KOREAN_KSC = 0
SORT_KOREAN_UNICODE = 1
SORT_GERMAN_PHONE_BOOK = 1


def PRIMARYLANGID(lgid):
    return (lgid) & 1023


def SUBLANGID(lgid):
    return (lgid) >> 10


NLS_VALID_LOCALE_MASK = 1048575


def LANGIDFROMLCID(lcid):
    return lcid


def SORTIDFROMLCID(lcid):
    return ((lcid) & NLS_VALID_LOCALE_MASK) >> 16


MAXIMUM_WAIT_OBJECTS = 64
MAXIMUM_SUSPEND_COUNT = MAXCHAR

EXCEPTION_NONCONTINUABLE = 1
EXCEPTION_MAXIMUM_PARAMETERS = 15
PROCESS_TERMINATE = 1
PROCESS_CREATE_THREAD = 2
PROCESS_VM_OPERATION = 8
PROCESS_VM_READ = 16
PROCESS_VM_WRITE = 32
PROCESS_DUP_HANDLE = 64
PROCESS_CREATE_PROCESS = 128
PROCESS_SET_QUOTA = 256
PROCESS_SET_INFORMATION = 512
PROCESS_QUERY_INFORMATION = 1024
PROCESS_SUSPEND_RESUME = 2048
PROCESS_QUERY_LIMITED_INFORMATION = 4096
PROCESS_SET_LIMITED_INFORMATION = 8192
MAXIMUM_PROCESSORS = 32
THREAD_TERMINATE = 1
THREAD_SUSPEND_RESUME = 2
THREAD_GET_CONTEXT = 8
THREAD_SET_CONTEXT = 16
THREAD_SET_INFORMATION = 32
THREAD_QUERY_INFORMATION = 64
THREAD_SET_THREAD_TOKEN = 128
THREAD_IMPERSONATE = 256
THREAD_DIRECT_IMPERSONATION = 512
THREAD_SET_LIMITED_INFORMATION = 1024
THREAD_QUERY_LIMITED_INFORMATION = 2048
THREAD_RESUME = 4096
JOB_OBJECT_ASSIGN_PROCESS = 1
JOB_OBJECT_SET_ATTRIBUTES = 2
JOB_OBJECT_QUERY = 4
JOB_OBJECT_TERMINATE = 8
TLS_MINIMUM_AVAILABLE = 64
THREAD_BASE_PRIORITY_LOWRT = 15
THREAD_BASE_PRIORITY_MAX = 2
THREAD_BASE_PRIORITY_MIN = -2
THREAD_BASE_PRIORITY_IDLE = -15
JOB_OBJECT_LIMIT_WORKINGSET = 1
JOB_OBJECT_LIMIT_PROCESS_TIME = 2
JOB_OBJECT_LIMIT_JOB_TIME = 4
JOB_OBJECT_LIMIT_ACTIVE_PROCESS = 8
JOB_OBJECT_LIMIT_AFFINITY = 16
JOB_OBJECT_LIMIT_PRIORITY_CLASS = 32
JOB_OBJECT_LIMIT_VALID_FLAGS = 63
EVENT_MODIFY_STATE = 2
MUTANT_QUERY_STATE = 1
SEMAPHORE_MODIFY_STATE = 2
TIME_ZONE_ID_UNKNOWN = 0
TIME_ZONE_ID_STANDARD = 1
TIME_ZONE_ID_DAYLIGHT = 2
PROCESSOR_INTEL_386 = 386
PROCESSOR_INTEL_486 = 486
PROCESSOR_INTEL_PENTIUM = 586
PROCESSOR_MIPS_R4000 = 4000
PROCESSOR_ALPHA_21064 = 21064
PROCESSOR_HITACHI_SH3 = 10003
PROCESSOR_HITACHI_SH3E = 10004
PROCESSOR_HITACHI_SH4 = 10005
PROCESSOR_MOTOROLA_821 = 821
PROCESSOR_ARM_7TDMI = 70001
PROCESSOR_ARCHITECTURE_INTEL = 0
PROCESSOR_ARCHITECTURE_MIPS = 1
PROCESSOR_ARCHITECTURE_ALPHA = 2
PROCESSOR_ARCHITECTURE_PPC = 3
PROCESSOR_ARCHITECTURE_SH = 4
PROCESSOR_ARCHITECTURE_ARM = 5
PROCESSOR_ARCHITECTURE_IA64 = 6
PROCESSOR_ARCHITECTURE_ALPHA64 = 7
PROCESSOR_ARCHITECTURE_MSIL = 8
PROCESSOR_ARCHITECTURE_AMD64 = 9
PROCESSOR_ARCHITECTURE_IA32_ON_WIN64 = 10
PROCESSOR_ARCHITECTURE_UNKNOWN = 65535
PF_FLOATING_POINT_PRECISION_ERRATA = 0
PF_FLOATING_POINT_EMULATED = 1
PF_COMPARE_EXCHANGE_DOUBLE = 2
PF_MMX_INSTRUCTIONS_AVAILABLE = 3
PF_PPC_MOVEMEM_64BIT_OK = 4
PF_ALPHA_BYTE_INSTRUCTIONS = 5
SECTION_QUERY = 1
SECTION_MAP_WRITE = 2
SECTION_MAP_READ = 4
SECTION_MAP_EXECUTE = 8
SECTION_EXTEND_SIZE = 16
PAGE_NOACCESS = 1
PAGE_READONLY = 2
PAGE_READWRITE = 4
PAGE_WRITECOPY = 8
PAGE_EXECUTE = 16
PAGE_EXECUTE_READ = 32
PAGE_EXECUTE_READWRITE = 64
PAGE_EXECUTE_WRITECOPY = 128
PAGE_GUARD = 256
PAGE_NOCACHE = 512
MEM_COMMIT = 4096
MEM_RESERVE = 8192
MEM_DECOMMIT = 16384
MEM_RELEASE = 32768
MEM_FREE = 65536
MEM_PRIVATE = 131072
MEM_MAPPED = 262144
MEM_RESET = 524288
MEM_TOP_DOWN = 1048576
MEM_4MB_PAGES = -2147483648
SEC_FILE = 8388608
SEC_IMAGE = 16777216
SEC_VLM = 33554432
SEC_RESERVE = 67108864
SEC_COMMIT = 134217728
SEC_NOCACHE = 268435456
MEM_IMAGE = SEC_IMAGE
FILE_READ_DATA = 1
FILE_LIST_DIRECTORY = 1
FILE_WRITE_DATA = 2
FILE_ADD_FILE = 2
FILE_APPEND_DATA = 4
FILE_ADD_SUBDIRECTORY = 4
FILE_CREATE_PIPE_INSTANCE = 4
FILE_READ_EA = 8
FILE_WRITE_EA = 16
FILE_EXECUTE = 32
FILE_TRAVERSE = 32
FILE_DELETE_CHILD = 64
FILE_READ_ATTRIBUTES = 128
FILE_WRITE_ATTRIBUTES = 256
FILE_SHARE_READ = 1
FILE_SHARE_WRITE = 2
FILE_SHARE_DELETE = 4
FILE_ATTRIBUTE_READONLY = 1
FILE_ATTRIBUTE_HIDDEN = 2
FILE_ATTRIBUTE_SYSTEM = 4
FILE_ATTRIBUTE_DIRECTORY = 16
FILE_ATTRIBUTE_ARCHIVE = 32
FILE_ATTRIBUTE_DEVICE = 64
FILE_ATTRIBUTE_NORMAL = 128
FILE_ATTRIBUTE_TEMPORARY = 256
FILE_ATTRIBUTE_SPARSE_FILE = 512
FILE_ATTRIBUTE_REPARSE_POINT = 1024
FILE_ATTRIBUTE_COMPRESSED = 2048
FILE_ATTRIBUTE_OFFLINE = 4096
FILE_ATTRIBUTE_NOT_CONTENT_INDEXED = 8192
FILE_ATTRIBUTE_ENCRYPTED = 16384
FILE_ATTRIBUTE_VIRTUAL = 65536
FILE_NOTIFY_CHANGE_FILE_NAME = 1
FILE_NOTIFY_CHANGE_DIR_NAME = 2
FILE_NOTIFY_CHANGE_ATTRIBUTES = 4
FILE_NOTIFY_CHANGE_SIZE = 8
FILE_NOTIFY_CHANGE_LAST_WRITE = 16
FILE_NOTIFY_CHANGE_LAST_ACCESS = 32
FILE_NOTIFY_CHANGE_CREATION = 64
FILE_NOTIFY_CHANGE_SECURITY = 256
FILE_ACTION_ADDED = 1
FILE_ACTION_REMOVED = 2
FILE_ACTION_MODIFIED = 3
FILE_ACTION_RENAMED_OLD_NAME = 4
FILE_ACTION_RENAMED_NEW_NAME = 5
FILE_CASE_SENSITIVE_SEARCH = 1
FILE_CASE_PRESERVED_NAMES = 2
FILE_UNICODE_ON_DISK = 4
FILE_PERSISTENT_ACLS = 8
FILE_FILE_COMPRESSION = 16
FILE_VOLUME_QUOTAS = 32
FILE_SUPPORTS_SPARSE_FILES = 64
FILE_SUPPORTS_REPARSE_POINTS = 128
FILE_SUPPORTS_REMOTE_STORAGE = 256
FILE_VOLUME_IS_COMPRESSED = 32768
FILE_SUPPORTS_OBJECT_IDS = 65536
FILE_SUPPORTS_ENCRYPTION = 131072

MAXIMUM_REPARSE_DATA_BUFFER_SIZE = 16 * 1024
IO_REPARSE_TAG_RESERVED_ZERO = 0
IO_REPARSE_TAG_RESERVED_ONE = 1
IO_REPARSE_TAG_SYMBOLIC_LINK = 2
IO_REPARSE_TAG_NSS = 5
IO_REPARSE_TAG_FILTER_MANAGER = -2147483637
IO_REPARSE_TAG_DFS = -2147483638
IO_REPARSE_TAG_SIS = -2147483641
IO_REPARSE_TAG_MOUNT_POINT = -1610612733
IO_REPARSE_TAG_HSM = -1073741820
IO_REPARSE_TAG_NSSRECOVER = 8
IO_REPARSE_TAG_RESERVED_MS_RANGE = 256
IO_REPARSE_TAG_RESERVED_RANGE = IO_REPARSE_TAG_RESERVED_ONE
IO_COMPLETION_MODIFY_STATE = 2

DUPLICATE_CLOSE_SOURCE = 1
DUPLICATE_SAME_ACCESS = 2
DELETE = 65536
READ_CONTROL = 131072
WRITE_DAC = 262144
WRITE_OWNER = 524288
SYNCHRONIZE = 1048576
STANDARD_RIGHTS_REQUIRED = 983040
STANDARD_RIGHTS_READ = READ_CONTROL
STANDARD_RIGHTS_WRITE = READ_CONTROL
STANDARD_RIGHTS_EXECUTE = READ_CONTROL
STANDARD_RIGHTS_ALL = 2031616
SPECIFIC_RIGHTS_ALL = 65535
IO_COMPLETION_ALL_ACCESS = STANDARD_RIGHTS_REQUIRED | SYNCHRONIZE | 0x3
ACCESS_SYSTEM_SECURITY = 16777216
MAXIMUM_ALLOWED = 33554432
GENERIC_READ = -2147483648
GENERIC_WRITE = 1073741824
GENERIC_EXECUTE = 536870912
GENERIC_ALL = 268435456

# Included from pshpack4.h

# Included from poppack.h
SID_REVISION = 1
SID_MAX_SUB_AUTHORITIES = 15
SID_RECOMMENDED_SUB_AUTHORITIES = 1

SidTypeUser = 1
SidTypeGroup = 2
SidTypeDomain = 3
SidTypeAlias = 4
SidTypeWellKnownGroup = 5
SidTypeDeletedAccount = 6
SidTypeInvalid = 7
SidTypeUnknown = 8

SECURITY_NULL_RID = 0
SECURITY_WORLD_RID = 0
SECURITY_LOCAL_RID = 0x00000000
SECURITY_CREATOR_OWNER_RID = 0
SECURITY_CREATOR_GROUP_RID = 1
SECURITY_CREATOR_OWNER_SERVER_RID = 2
SECURITY_CREATOR_GROUP_SERVER_RID = 3
SECURITY_DIALUP_RID = 1
SECURITY_NETWORK_RID = 2
SECURITY_BATCH_RID = 3
SECURITY_INTERACTIVE_RID = 4
SECURITY_SERVICE_RID = 6
SECURITY_ANONYMOUS_LOGON_RID = 7
SECURITY_PROXY_RID = 8
SECURITY_SERVER_LOGON_RID = 9
SECURITY_PRINCIPAL_SELF_RID = 10
SECURITY_AUTHENTICATED_USER_RID = 11
SECURITY_LOGON_IDS_RID = 5
SECURITY_LOGON_IDS_RID_COUNT = 3
SECURITY_LOCAL_SYSTEM_RID = 18
SECURITY_NT_NON_UNIQUE = 21
SECURITY_BUILTIN_DOMAIN_RID = 32
DOMAIN_USER_RID_ADMIN = 500
DOMAIN_USER_RID_GUEST = 501
DOMAIN_GROUP_RID_ADMINS = 512
DOMAIN_GROUP_RID_USERS = 513
DOMAIN_GROUP_RID_GUESTS = 514
DOMAIN_ALIAS_RID_ADMINS = 544
DOMAIN_ALIAS_RID_USERS = 545
DOMAIN_ALIAS_RID_GUESTS = 546
DOMAIN_ALIAS_RID_POWER_USERS = 547
DOMAIN_ALIAS_RID_ACCOUNT_OPS = 548
DOMAIN_ALIAS_RID_SYSTEM_OPS = 549
DOMAIN_ALIAS_RID_PRINT_OPS = 550
DOMAIN_ALIAS_RID_BACKUP_OPS = 551
DOMAIN_ALIAS_RID_REPLICATOR = 552
SE_GROUP_MANDATORY = 1
SE_GROUP_ENABLED_BY_DEFAULT = 2
SE_GROUP_ENABLED = 4
SE_GROUP_OWNER = 8
SE_GROUP_LOGON_ID = -1073741824
ACL_REVISION = 2
ACL_REVISION_DS = 4
ACL_REVISION1 = 1
ACL_REVISION2 = 2
ACL_REVISION3 = 3
ACL_REVISION4 = 4
MAX_ACL_REVISION = ACL_REVISION4

## ACE types
ACCESS_MIN_MS_ACE_TYPE = 0
ACCESS_ALLOWED_ACE_TYPE = 0
ACCESS_DENIED_ACE_TYPE = 1
SYSTEM_AUDIT_ACE_TYPE = 2
SYSTEM_ALARM_ACE_TYPE = 3
ACCESS_MAX_MS_V2_ACE_TYPE = 3
ACCESS_ALLOWED_COMPOUND_ACE_TYPE = 4
ACCESS_MAX_MS_V3_ACE_TYPE = 4
ACCESS_MIN_MS_OBJECT_ACE_TYPE = 5
ACCESS_ALLOWED_OBJECT_ACE_TYPE = 5
ACCESS_DENIED_OBJECT_ACE_TYPE = 6
SYSTEM_AUDIT_OBJECT_ACE_TYPE = 7
SYSTEM_ALARM_OBJECT_ACE_TYPE = 8
ACCESS_MAX_MS_OBJECT_ACE_TYPE = 8
ACCESS_MAX_MS_V4_ACE_TYPE = 8
ACCESS_MAX_MS_ACE_TYPE = 8
ACCESS_ALLOWED_CALLBACK_ACE_TYPE = 9
ACCESS_DENIED_CALLBACK_ACE_TYPE = 10
ACCESS_ALLOWED_CALLBACK_OBJECT_ACE_TYPE = 11
ACCESS_DENIED_CALLBACK_OBJECT_ACE_TYPE = 12
SYSTEM_AUDIT_CALLBACK_ACE_TYPE = 13
SYSTEM_ALARM_CALLBACK_ACE_TYPE = 14
SYSTEM_AUDIT_CALLBACK_OBJECT_ACE_TYPE = 15
SYSTEM_ALARM_CALLBACK_OBJECT_ACE_TYPE = 16
SYSTEM_MANDATORY_LABEL_ACE_TYPE = 17
ACCESS_MAX_MS_V5_ACE_TYPE = 17

## ACE inheritance flags
OBJECT_INHERIT_ACE = 1
CONTAINER_INHERIT_ACE = 2
NO_PROPAGATE_INHERIT_ACE = 4
INHERIT_ONLY_ACE = 8
INHERITED_ACE = 16
VALID_INHERIT_FLAGS = 31


SUCCESSFUL_ACCESS_ACE_FLAG = 64
FAILED_ACCESS_ACE_FLAG = 128
ACE_OBJECT_TYPE_PRESENT = 1
ACE_INHERITED_OBJECT_TYPE_PRESENT = 2
SECURITY_DESCRIPTOR_REVISION = 1
SECURITY_DESCRIPTOR_REVISION1 = 1
SECURITY_DESCRIPTOR_MIN_LENGTH = 20
SE_OWNER_DEFAULTED = 1
SE_GROUP_DEFAULTED = 2
SE_DACL_PRESENT = 4
SE_DACL_DEFAULTED = 8
SE_SACL_PRESENT = 16
SE_SACL_DEFAULTED = 32
SE_DACL_AUTO_INHERIT_REQ = 256
SE_SACL_AUTO_INHERIT_REQ = 512
SE_DACL_AUTO_INHERITED = 1024
SE_SACL_AUTO_INHERITED = 2048
SE_DACL_PROTECTED = 4096
SE_SACL_PROTECTED = 8192
SE_SELF_RELATIVE = 32768
ACCESS_OBJECT_GUID = 0
ACCESS_PROPERTY_SET_GUID = 1
ACCESS_PROPERTY_GUID = 2
ACCESS_MAX_LEVEL = 4
AUDIT_ALLOW_NO_PRIVILEGE = 1
ACCESS_DS_SOURCE_A = "Directory Service"
ACCESS_DS_OBJECT_TYPE_NAME_A = "Directory Service Object"
SE_PRIVILEGE_ENABLED_BY_DEFAULT = 1
SE_PRIVILEGE_ENABLED = 2
SE_PRIVILEGE_USED_FOR_ACCESS = -2147483648
PRIVILEGE_SET_ALL_NECESSARY = 1

SE_CREATE_TOKEN_NAME = "SeCreateTokenPrivilege"
SE_ASSIGNPRIMARYTOKEN_NAME = "SeAssignPrimaryTokenPrivilege"
SE_LOCK_MEMORY_NAME = "SeLockMemoryPrivilege"
SE_INCREASE_QUOTA_NAME = "SeIncreaseQuotaPrivilege"
SE_UNSOLICITED_INPUT_NAME = "SeUnsolicitedInputPrivilege"
SE_MACHINE_ACCOUNT_NAME = "SeMachineAccountPrivilege"
SE_TCB_NAME = "SeTcbPrivilege"
SE_SECURITY_NAME = "SeSecurityPrivilege"
SE_TAKE_OWNERSHIP_NAME = "SeTakeOwnershipPrivilege"
SE_LOAD_DRIVER_NAME = "SeLoadDriverPrivilege"
SE_SYSTEM_PROFILE_NAME = "SeSystemProfilePrivilege"
SE_SYSTEMTIME_NAME = "SeSystemtimePrivilege"
SE_PROF_SINGLE_PROCESS_NAME = "SeProfileSingleProcessPrivilege"
SE_INC_BASE_PRIORITY_NAME = "SeIncreaseBasePriorityPrivilege"
SE_CREATE_PAGEFILE_NAME = "SeCreatePagefilePrivilege"
SE_CREATE_PERMANENT_NAME = "SeCreatePermanentPrivilege"
SE_BACKUP_NAME = "SeBackupPrivilege"
SE_RESTORE_NAME = "SeRestorePrivilege"
SE_SHUTDOWN_NAME = "SeShutdownPrivilege"
SE_DEBUG_NAME = "SeDebugPrivilege"
SE_AUDIT_NAME = "SeAuditPrivilege"
SE_SYSTEM_ENVIRONMENT_NAME = "SeSystemEnvironmentPrivilege"
SE_CHANGE_NOTIFY_NAME = "SeChangeNotifyPrivilege"
SE_REMOTE_SHUTDOWN_NAME = "SeRemoteShutdownPrivilege"
TOKEN_ASSIGN_PRIMARY = 1
TOKEN_DUPLICATE = 2
TOKEN_IMPERSONATE = 4
TOKEN_QUERY = 8
TOKEN_QUERY_SOURCE = 16
TOKEN_ADJUST_PRIVILEGES = 32
TOKEN_ADJUST_GROUPS = 64
TOKEN_ADJUST_DEFAULT = 128
TOKEN_ALL_ACCESS = (
    STANDARD_RIGHTS_REQUIRED
    | TOKEN_ASSIGN_PRIMARY
    | TOKEN_DUPLICATE
    | TOKEN_IMPERSONATE
    | TOKEN_QUERY
    | TOKEN_QUERY_SOURCE
    | TOKEN_ADJUST_PRIVILEGES
    | TOKEN_ADJUST_GROUPS
    | TOKEN_ADJUST_DEFAULT
)
TOKEN_READ = STANDARD_RIGHTS_READ | TOKEN_QUERY
TOKEN_WRITE = (
    STANDARD_RIGHTS_WRITE
    | TOKEN_ADJUST_PRIVILEGES
    | TOKEN_ADJUST_GROUPS
    | TOKEN_ADJUST_DEFAULT
)
TOKEN_EXECUTE = STANDARD_RIGHTS_EXECUTE
TOKEN_SOURCE_LENGTH = 8

# Token types
TokenPrimary = 1
TokenImpersonation = 2

# TOKEN_INFORMATION_CLASS, used with Get/SetTokenInformation
TokenUser = 1
TokenGroups = 2
TokenPrivileges = 3
TokenOwner = 4
TokenPrimaryGroup = 5
TokenDefaultDacl = 6
TokenSource = 7
TokenType = 8
TokenImpersonationLevel = 9
TokenStatistics = 10
TokenRestrictedSids = 11
TokenSessionId = 12
TokenGroupsAndPrivileges = 13
TokenSessionReference = 14
TokenSandBoxInert = 15
TokenAuditPolicy = 16
TokenOrigin = 17
TokenElevationType = 18
TokenLinkedToken = 19
TokenElevation = 20
TokenHasRestrictions = 21
TokenAccessInformation = 22
TokenVirtualizationAllowed = 23
TokenVirtualizationEnabled = 24
TokenIntegrityLevel = 25
TokenUIAccess = 26
TokenMandatoryPolicy = 27
TokenLogonSid = 28

OWNER_SECURITY_INFORMATION = 0x00000001
GROUP_SECURITY_INFORMATION = 0x00000002
DACL_SECURITY_INFORMATION = 0x00000004
SACL_SECURITY_INFORMATION = 0x00000008
LABEL_SECURITY_INFORMATION = 0x00000010

IMAGE_DOS_SIGNATURE = 23117
IMAGE_OS2_SIGNATURE = 17742
IMAGE_OS2_SIGNATURE_LE = 17740
IMAGE_VXD_SIGNATURE = 17740
IMAGE_NT_SIGNATURE = 17744
IMAGE_SIZEOF_FILE_HEADER = 20
IMAGE_FILE_RELOCS_STRIPPED = 1
IMAGE_FILE_EXECUTABLE_IMAGE = 2
IMAGE_FILE_LINE_NUMS_STRIPPED = 4
IMAGE_FILE_LOCAL_SYMS_STRIPPED = 8
IMAGE_FILE_AGGRESIVE_WS_TRIM = 16
IMAGE_FILE_LARGE_ADDRESS_AWARE = 32
IMAGE_FILE_BYTES_REVERSED_LO = 128
IMAGE_FILE_32BIT_MACHINE = 256
IMAGE_FILE_DEBUG_STRIPPED = 512
IMAGE_FILE_REMOVABLE_RUN_FROM_SWAP = 1024
IMAGE_FILE_NET_RUN_FROM_SWAP = 2048
IMAGE_FILE_SYSTEM = 4096
IMAGE_FILE_DLL = 8192
IMAGE_FILE_UP_SYSTEM_ONLY = 16384
IMAGE_FILE_BYTES_REVERSED_HI = 32768
IMAGE_FILE_MACHINE_UNKNOWN = 0
IMAGE_FILE_MACHINE_I386 = 332
IMAGE_FILE_MACHINE_R3000 = 354
IMAGE_FILE_MACHINE_R4000 = 358
IMAGE_FILE_MACHINE_R10000 = 360
IMAGE_FILE_MACHINE_WCEMIPSV2 = 361
IMAGE_FILE_MACHINE_ALPHA = 388
IMAGE_FILE_MACHINE_POWERPC = 496
IMAGE_FILE_MACHINE_SH3 = 418
IMAGE_FILE_MACHINE_SH3E = 420
IMAGE_FILE_MACHINE_SH4 = 422
IMAGE_FILE_MACHINE_ARM = 448
IMAGE_NUMBEROF_DIRECTORY_ENTRIES = 16
IMAGE_SIZEOF_ROM_OPTIONAL_HEADER = 56
IMAGE_SIZEOF_STD_OPTIONAL_HEADER = 28
IMAGE_SIZEOF_NT_OPTIONAL_HEADER = 224
IMAGE_NT_OPTIONAL_HDR_MAGIC = 267
IMAGE_ROM_OPTIONAL_HDR_MAGIC = 263
IMAGE_SUBSYSTEM_UNKNOWN = 0
IMAGE_SUBSYSTEM_NATIVE = 1
IMAGE_SUBSYSTEM_WINDOWS_GUI = 2
IMAGE_SUBSYSTEM_WINDOWS_CUI = 3
IMAGE_SUBSYSTEM_WINDOWS_CE_GUI = 4
IMAGE_SUBSYSTEM_OS2_CUI = 5
IMAGE_SUBSYSTEM_POSIX_CUI = 7
IMAGE_SUBSYSTEM_RESERVED8 = 8
IMAGE_DLLCHARACTERISTICS_WDM_DRIVER = 8192
IMAGE_DIRECTORY_ENTRY_EXPORT = 0
IMAGE_DIRECTORY_ENTRY_IMPORT = 1
IMAGE_DIRECTORY_ENTRY_RESOURCE = 2
IMAGE_DIRECTORY_ENTRY_EXCEPTION = 3
IMAGE_DIRECTORY_ENTRY_SECURITY = 4
IMAGE_DIRECTORY_ENTRY_BASERELOC = 5
IMAGE_DIRECTORY_ENTRY_DEBUG = 6
IMAGE_DIRECTORY_ENTRY_COPYRIGHT = 7
IMAGE_DIRECTORY_ENTRY_GLOBALPTR = 8
IMAGE_DIRECTORY_ENTRY_TLS = 9
IMAGE_DIRECTORY_ENTRY_LOAD_CONFIG = 10
IMAGE_DIRECTORY_ENTRY_BOUND_IMPORT = 11
IMAGE_DIRECTORY_ENTRY_IAT = 12
IMAGE_SIZEOF_SHORT_NAME = 8
IMAGE_SIZEOF_SECTION_HEADER = 40
IMAGE_SCN_TYPE_NO_PAD = 8
IMAGE_SCN_CNT_CODE = 32
IMAGE_SCN_CNT_INITIALIZED_DATA = 64
IMAGE_SCN_CNT_UNINITIALIZED_DATA = 128
IMAGE_SCN_LNK_OTHER = 256
IMAGE_SCN_LNK_INFO = 512
IMAGE_SCN_LNK_REMOVE = 2048
IMAGE_SCN_LNK_COMDAT = 4096
IMAGE_SCN_MEM_FARDATA = 32768
IMAGE_SCN_MEM_PURGEABLE = 131072
IMAGE_SCN_MEM_16BIT = 131072
IMAGE_SCN_MEM_LOCKED = 262144
IMAGE_SCN_MEM_PRELOAD = 524288
IMAGE_SCN_ALIGN_1BYTES = 1048576
IMAGE_SCN_ALIGN_2BYTES = 2097152
IMAGE_SCN_ALIGN_4BYTES = 3145728
IMAGE_SCN_ALIGN_8BYTES = 4194304
IMAGE_SCN_ALIGN_16BYTES = 5242880
IMAGE_SCN_ALIGN_32BYTES = 6291456
IMAGE_SCN_ALIGN_64BYTES = 7340032
IMAGE_SCN_LNK_NRELOC_OVFL = 16777216
IMAGE_SCN_MEM_DISCARDABLE = 33554432
IMAGE_SCN_MEM_NOT_CACHED = 67108864
IMAGE_SCN_MEM_NOT_PAGED = 134217728
IMAGE_SCN_MEM_SHARED = 268435456
IMAGE_SCN_MEM_EXECUTE = 536870912
IMAGE_SCN_MEM_READ = 1073741824
IMAGE_SCN_MEM_WRITE = -2147483648
IMAGE_SCN_SCALE_INDEX = 1
IMAGE_SIZEOF_SYMBOL = 18
IMAGE_SYM_TYPE_NULL = 0
IMAGE_SYM_TYPE_VOID = 1
IMAGE_SYM_TYPE_CHAR = 2
IMAGE_SYM_TYPE_SHORT = 3
IMAGE_SYM_TYPE_INT = 4
IMAGE_SYM_TYPE_LONG = 5
IMAGE_SYM_TYPE_FLOAT = 6
IMAGE_SYM_TYPE_DOUBLE = 7
IMAGE_SYM_TYPE_STRUCT = 8
IMAGE_SYM_TYPE_UNION = 9
IMAGE_SYM_TYPE_ENUM = 10
IMAGE_SYM_TYPE_MOE = 11
IMAGE_SYM_TYPE_BYTE = 12
IMAGE_SYM_TYPE_WORD = 13
IMAGE_SYM_TYPE_UINT = 14
IMAGE_SYM_TYPE_DWORD = 15
IMAGE_SYM_TYPE_PCODE = 32768
IMAGE_SYM_DTYPE_NULL = 0
IMAGE_SYM_DTYPE_POINTER = 1
IMAGE_SYM_DTYPE_FUNCTION = 2
IMAGE_SYM_DTYPE_ARRAY = 3
IMAGE_SYM_CLASS_NULL = 0
IMAGE_SYM_CLASS_AUTOMATIC = 1
IMAGE_SYM_CLASS_EXTERNAL = 2
IMAGE_SYM_CLASS_STATIC = 3
IMAGE_SYM_CLASS_REGISTER = 4
IMAGE_SYM_CLASS_EXTERNAL_DEF = 5
IMAGE_SYM_CLASS_LABEL = 6
IMAGE_SYM_CLASS_UNDEFINED_LABEL = 7
IMAGE_SYM_CLASS_MEMBER_OF_STRUCT = 8
IMAGE_SYM_CLASS_ARGUMENT = 9
IMAGE_SYM_CLASS_STRUCT_TAG = 10
IMAGE_SYM_CLASS_MEMBER_OF_UNION = 11
IMAGE_SYM_CLASS_UNION_TAG = 12
IMAGE_SYM_CLASS_TYPE_DEFINITION = 13
IMAGE_SYM_CLASS_UNDEFINED_STATIC = 14
IMAGE_SYM_CLASS_ENUM_TAG = 15
IMAGE_SYM_CLASS_MEMBER_OF_ENUM = 16
IMAGE_SYM_CLASS_REGISTER_PARAM = 17
IMAGE_SYM_CLASS_BIT_FIELD = 18
IMAGE_SYM_CLASS_FAR_EXTERNAL = 68
IMAGE_SYM_CLASS_BLOCK = 100
IMAGE_SYM_CLASS_FUNCTION = 101
IMAGE_SYM_CLASS_END_OF_STRUCT = 102
IMAGE_SYM_CLASS_FILE = 103
IMAGE_SYM_CLASS_SECTION = 104
IMAGE_SYM_CLASS_WEAK_EXTERNAL = 105
N_BTMASK = 15
N_TMASK = 48
N_TMASK1 = 192
N_TMASK2 = 240
N_BTSHFT = 4
N_TSHIFT = 2


def BTYPE(x):
    return (x) & N_BTMASK


def ISPTR(x):
    return ((x) & N_TMASK) == (IMAGE_SYM_DTYPE_POINTER << N_BTSHFT)


def ISFCN(x):
    return ((x) & N_TMASK) == (IMAGE_SYM_DTYPE_FUNCTION << N_BTSHFT)


def ISARY(x):
    return ((x) & N_TMASK) == (IMAGE_SYM_DTYPE_ARRAY << N_BTSHFT)


def INCREF(x):
    return (
        (((x) & ~N_BTMASK) << N_TSHIFT)
        | (IMAGE_SYM_DTYPE_POINTER << N_BTSHFT)
        | ((x) & N_BTMASK)
    )


def DECREF(x):
    return (((x) >> N_TSHIFT) & ~N_BTMASK) | ((x) & N_BTMASK)


IMAGE_SIZEOF_AUX_SYMBOL = 18
IMAGE_COMDAT_SELECT_NODUPLICATES = 1
IMAGE_COMDAT_SELECT_ANY = 2
IMAGE_COMDAT_SELECT_SAME_SIZE = 3
IMAGE_COMDAT_SELECT_EXACT_MATCH = 4
IMAGE_COMDAT_SELECT_ASSOCIATIVE = 5
IMAGE_COMDAT_SELECT_LARGEST = 6
IMAGE_COMDAT_SELECT_NEWEST = 7
IMAGE_WEAK_EXTERN_SEARCH_NOLIBRARY = 1
IMAGE_WEAK_EXTERN_SEARCH_LIBRARY = 2
IMAGE_WEAK_EXTERN_SEARCH_ALIAS = 3
IMAGE_SIZEOF_RELOCATION = 10
IMAGE_REL_I386_ABSOLUTE = 0
IMAGE_REL_I386_DIR16 = 1
IMAGE_REL_I386_REL16 = 2
IMAGE_REL_I386_DIR32 = 6
IMAGE_REL_I386_DIR32NB = 7
IMAGE_REL_I386_SEG12 = 9
IMAGE_REL_I386_SECTION = 10
IMAGE_REL_I386_SECREL = 11
IMAGE_REL_I386_REL32 = 20
IMAGE_REL_MIPS_ABSOLUTE = 0
IMAGE_REL_MIPS_REFHALF = 1
IMAGE_REL_MIPS_REFWORD = 2
IMAGE_REL_MIPS_JMPADDR = 3
IMAGE_REL_MIPS_REFHI = 4
IMAGE_REL_MIPS_REFLO = 5
IMAGE_REL_MIPS_GPREL = 6
IMAGE_REL_MIPS_LITERAL = 7
IMAGE_REL_MIPS_SECTION = 10
IMAGE_REL_MIPS_SECREL = 11
IMAGE_REL_MIPS_SECRELLO = 12
IMAGE_REL_MIPS_SECRELHI = 13
IMAGE_REL_MIPS_REFWORDNB = 34
IMAGE_REL_MIPS_PAIR = 37
IMAGE_REL_ALPHA_ABSOLUTE = 0
IMAGE_REL_ALPHA_REFLONG = 1
IMAGE_REL_ALPHA_REFQUAD = 2
IMAGE_REL_ALPHA_GPREL32 = 3
IMAGE_REL_ALPHA_LITERAL = 4
IMAGE_REL_ALPHA_LITUSE = 5
IMAGE_REL_ALPHA_GPDISP = 6
IMAGE_REL_ALPHA_BRADDR = 7
IMAGE_REL_ALPHA_HINT = 8
IMAGE_REL_ALPHA_INLINE_REFLONG = 9
IMAGE_REL_ALPHA_REFHI = 10
IMAGE_REL_ALPHA_REFLO = 11
IMAGE_REL_ALPHA_PAIR = 12
IMAGE_REL_ALPHA_MATCH = 13
IMAGE_REL_ALPHA_SECTION = 14
IMAGE_REL_ALPHA_SECREL = 15
IMAGE_REL_ALPHA_REFLONGNB = 16
IMAGE_REL_ALPHA_SECRELLO = 17
IMAGE_REL_ALPHA_SECRELHI = 18
IMAGE_REL_PPC_ABSOLUTE = 0
IMAGE_REL_PPC_ADDR64 = 1
IMAGE_REL_PPC_ADDR32 = 2
IMAGE_REL_PPC_ADDR24 = 3
IMAGE_REL_PPC_ADDR16 = 4
IMAGE_REL_PPC_ADDR14 = 5
IMAGE_REL_PPC_REL24 = 6
IMAGE_REL_PPC_REL14 = 7
IMAGE_REL_PPC_TOCREL16 = 8
IMAGE_REL_PPC_TOCREL14 = 9
IMAGE_REL_PPC_ADDR32NB = 10
IMAGE_REL_PPC_SECREL = 11
IMAGE_REL_PPC_SECTION = 12
IMAGE_REL_PPC_IFGLUE = 13
IMAGE_REL_PPC_IMGLUE = 14
IMAGE_REL_PPC_SECREL16 = 15
IMAGE_REL_PPC_REFHI = 16
IMAGE_REL_PPC_REFLO = 17
IMAGE_REL_PPC_PAIR = 18
IMAGE_REL_PPC_SECRELLO = 19
IMAGE_REL_PPC_SECRELHI = 20
IMAGE_REL_PPC_TYPEMASK = 255
IMAGE_REL_PPC_NEG = 256
IMAGE_REL_PPC_BRTAKEN = 512
IMAGE_REL_PPC_BRNTAKEN = 1024
IMAGE_REL_PPC_TOCDEFN = 2048
IMAGE_REL_SH3_ABSOLUTE = 0
IMAGE_REL_SH3_DIRECT16 = 1
IMAGE_REL_SH3_DIRECT32 = 2
IMAGE_REL_SH3_DIRECT8 = 3
IMAGE_REL_SH3_DIRECT8_WORD = 4
IMAGE_REL_SH3_DIRECT8_LONG = 5
IMAGE_REL_SH3_DIRECT4 = 6
IMAGE_REL_SH3_DIRECT4_WORD = 7
IMAGE_REL_SH3_DIRECT4_LONG = 8
IMAGE_REL_SH3_PCREL8_WORD = 9
IMAGE_REL_SH3_PCREL8_LONG = 10
IMAGE_REL_SH3_PCREL12_WORD = 11
IMAGE_REL_SH3_STARTOF_SECTION = 12
IMAGE_REL_SH3_SIZEOF_SECTION = 13
IMAGE_REL_SH3_SECTION = 14
IMAGE_REL_SH3_SECREL = 15
IMAGE_REL_SH3_DIRECT32_NB = 16
IMAGE_SIZEOF_LINENUMBER = 6
IMAGE_SIZEOF_BASE_RELOCATION = 8
IMAGE_REL_BASED_ABSOLUTE = 0
IMAGE_REL_BASED_HIGH = 1
IMAGE_REL_BASED_LOW = 2
IMAGE_REL_BASED_HIGHLOW = 3
IMAGE_REL_BASED_HIGHADJ = 4
IMAGE_REL_BASED_MIPS_JMPADDR = 5
IMAGE_REL_BASED_SECTION = 6
IMAGE_REL_BASED_REL32 = 7
IMAGE_ARCHIVE_START_SIZE = 8
IMAGE_ARCHIVE_START = "!<arch>\n"
IMAGE_ARCHIVE_END = "`\n"
IMAGE_ARCHIVE_PAD = "\n"
IMAGE_ARCHIVE_LINKER_MEMBER = "/               "
IMAGE_SIZEOF_ARCHIVE_MEMBER_HDR = 60
IMAGE_ORDINAL_FLAG = -2147483648


def IMAGE_SNAP_BY_ORDINAL(Ordinal):
    return (Ordinal & IMAGE_ORDINAL_FLAG) != 0


def IMAGE_ORDINAL(Ordinal):
    return Ordinal & 65535


IMAGE_RESOURCE_NAME_IS_STRING = -2147483648
IMAGE_RESOURCE_DATA_IS_DIRECTORY = -2147483648
IMAGE_DEBUG_TYPE_UNKNOWN = 0
IMAGE_DEBUG_TYPE_COFF = 1
IMAGE_DEBUG_TYPE_CODEVIEW = 2
IMAGE_DEBUG_TYPE_FPO = 3
IMAGE_DEBUG_TYPE_MISC = 4
IMAGE_DEBUG_TYPE_EXCEPTION = 5
IMAGE_DEBUG_TYPE_FIXUP = 6
IMAGE_DEBUG_TYPE_OMAP_TO_SRC = 7
IMAGE_DEBUG_TYPE_OMAP_FROM_SRC = 8
IMAGE_DEBUG_TYPE_BORLAND = 9
FRAME_FPO = 0
FRAME_TRAP = 1
FRAME_TSS = 2
FRAME_NONFPO = 3
SIZEOF_RFPO_DATA = 16
IMAGE_DEBUG_MISC_EXENAME = 1
IMAGE_SEPARATE_DEBUG_SIGNATURE = 18756
IMAGE_SEPARATE_DEBUG_FLAGS_MASK = 32768
IMAGE_SEPARATE_DEBUG_MISMATCH = 32768

# Included from string.h
_NLSCMPERROR = 2147483647
NULL = 0
HEAP_NO_SERIALIZE = 1
HEAP_GROWABLE = 2
HEAP_GENERATE_EXCEPTIONS = 4
HEAP_ZERO_MEMORY = 8
HEAP_REALLOC_IN_PLACE_ONLY = 16
HEAP_TAIL_CHECKING_ENABLED = 32
HEAP_FREE_CHECKING_ENABLED = 64
HEAP_DISABLE_COALESCE_ON_FREE = 128
HEAP_CREATE_ALIGN_16 = 65536
HEAP_CREATE_ENABLE_TRACING = 131072
HEAP_MAXIMUM_TAG = 4095
HEAP_PSEUDO_TAG_FLAG = 32768
HEAP_TAG_SHIFT = 16
IS_TEXT_UNICODE_ASCII16 = 1
IS_TEXT_UNICODE_REVERSE_ASCII16 = 16
IS_TEXT_UNICODE_STATISTICS = 2
IS_TEXT_UNICODE_REVERSE_STATISTICS = 32
IS_TEXT_UNICODE_CONTROLS = 4
IS_TEXT_UNICODE_REVERSE_CONTROLS = 64
IS_TEXT_UNICODE_SIGNATURE = 8
IS_TEXT_UNICODE_REVERSE_SIGNATURE = 128
IS_TEXT_UNICODE_ILLEGAL_CHARS = 256
IS_TEXT_UNICODE_ODD_LENGTH = 512
IS_TEXT_UNICODE_DBCS_LEADBYTE = 1024
IS_TEXT_UNICODE_NULL_BYTES = 4096
IS_TEXT_UNICODE_UNICODE_MASK = 15
IS_TEXT_UNICODE_REVERSE_MASK = 240
IS_TEXT_UNICODE_NOT_UNICODE_MASK = 3840
IS_TEXT_UNICODE_NOT_ASCII_MASK = 61440
COMPRESSION_FORMAT_NONE = 0
COMPRESSION_FORMAT_DEFAULT = 1
COMPRESSION_FORMAT_LZNT1 = 2
COMPRESSION_ENGINE_STANDARD = 0
COMPRESSION_ENGINE_MAXIMUM = 256
MESSAGE_RESOURCE_UNICODE = 1
RTL_CRITSECT_TYPE = 0
RTL_RESOURCE_TYPE = 1
SEF_DACL_AUTO_INHERIT = 1
SEF_SACL_AUTO_INHERIT = 2
SEF_DEFAULT_DESCRIPTOR_FOR_OBJECT = 4
SEF_AVOID_PRIVILEGE_CHECK = 8
DLL_PROCESS_ATTACH = 1
DLL_THREAD_ATTACH = 2
DLL_THREAD_DETACH = 3
DLL_PROCESS_DETACH = 0
EVENTLOG_SEQUENTIAL_READ = 0x0001
EVENTLOG_SEEK_READ = 0x0002
EVENTLOG_FORWARDS_READ = 0x0004
EVENTLOG_BACKWARDS_READ = 0x0008
EVENTLOG_SUCCESS = 0x0000
EVENTLOG_ERROR_TYPE = 1
EVENTLOG_WARNING_TYPE = 2
EVENTLOG_INFORMATION_TYPE = 4
EVENTLOG_AUDIT_SUCCESS = 8
EVENTLOG_AUDIT_FAILURE = 16
EVENTLOG_START_PAIRED_EVENT = 1
EVENTLOG_END_PAIRED_EVENT = 2
EVENTLOG_END_ALL_PAIRED_EVENTS = 4
EVENTLOG_PAIRED_EVENT_ACTIVE = 8
EVENTLOG_PAIRED_EVENT_INACTIVE = 16
KEY_QUERY_VALUE = 1
KEY_SET_VALUE = 2
KEY_CREATE_SUB_KEY = 4
KEY_ENUMERATE_SUB_KEYS = 8
KEY_NOTIFY = 16
KEY_CREATE_LINK = 32
KEY_READ = (
    STANDARD_RIGHTS_READ | KEY_QUERY_VALUE | KEY_ENUMERATE_SUB_KEYS | KEY_NOTIFY
) & (~SYNCHRONIZE)
KEY_WRITE = (STANDARD_RIGHTS_WRITE | KEY_SET_VALUE | KEY_CREATE_SUB_KEY) & (
    ~SYNCHRONIZE
)
KEY_EXECUTE = (KEY_READ) & (~SYNCHRONIZE)
KEY_ALL_ACCESS = (
    STANDARD_RIGHTS_ALL
    | KEY_QUERY_VALUE
    | KEY_SET_VALUE
    | KEY_CREATE_SUB_KEY
    | KEY_ENUMERATE_SUB_KEYS
    | KEY_NOTIFY
    | KEY_CREATE_LINK
) & (~SYNCHRONIZE)
REG_OPTION_RESERVED = 0
REG_OPTION_NON_VOLATILE = 0
REG_OPTION_VOLATILE = 1
REG_OPTION_CREATE_LINK = 2
REG_OPTION_BACKUP_RESTORE = 4
REG_OPTION_OPEN_LINK = 8
REG_LEGAL_OPTION = (
    REG_OPTION_RESERVED
    | REG_OPTION_NON_VOLATILE
    | REG_OPTION_VOLATILE
    | REG_OPTION_CREATE_LINK
    | REG_OPTION_BACKUP_RESTORE
    | REG_OPTION_OPEN_LINK
)

## dispositions returned from RegCreateKeyEx
REG_CREATED_NEW_KEY = 1
REG_OPENED_EXISTING_KEY = 2

## flags used with RegSaveKeyEx
REG_STANDARD_FORMAT = 1
REG_LATEST_FORMAT = 2
REG_NO_COMPRESSION = 4

## flags used with RegRestoreKey
REG_WHOLE_HIVE_VOLATILE = 1
REG_REFRESH_HIVE = 2
REG_NO_LAZY_FLUSH = 4
REG_FORCE_RESTORE = 8

REG_NOTIFY_CHANGE_NAME = 1
REG_NOTIFY_CHANGE_ATTRIBUTES = 2
REG_NOTIFY_CHANGE_LAST_SET = 4
REG_NOTIFY_CHANGE_SECURITY = 8
REG_LEGAL_CHANGE_FILTER = (
    REG_NOTIFY_CHANGE_NAME
    | REG_NOTIFY_CHANGE_ATTRIBUTES
    | REG_NOTIFY_CHANGE_LAST_SET
    | REG_NOTIFY_CHANGE_SECURITY
)
REG_NONE = 0
REG_SZ = 1
REG_EXPAND_SZ = 2
REG_BINARY = 3
REG_DWORD = 4
REG_DWORD_LITTLE_ENDIAN = 4
REG_DWORD_BIG_ENDIAN = 5
REG_LINK = 6
REG_MULTI_SZ = 7
REG_RESOURCE_LIST = 8
REG_FULL_RESOURCE_DESCRIPTOR = 9
REG_RESOURCE_REQUIREMENTS_LIST = 10
SERVICE_KERNEL_DRIVER = 1
SERVICE_FILE_SYSTEM_DRIVER = 2
SERVICE_ADAPTER = 4
SERVICE_RECOGNIZER_DRIVER = 8
SERVICE_DRIVER = (
    SERVICE_KERNEL_DRIVER | SERVICE_FILE_SYSTEM_DRIVER | SERVICE_RECOGNIZER_DRIVER
)
SERVICE_WIN32_OWN_PROCESS = 16
SERVICE_WIN32_SHARE_PROCESS = 32
SERVICE_WIN32 = SERVICE_WIN32_OWN_PROCESS | SERVICE_WIN32_SHARE_PROCESS
SERVICE_INTERACTIVE_PROCESS = 256
SERVICE_TYPE_ALL = (
    SERVICE_WIN32 | SERVICE_ADAPTER | SERVICE_DRIVER | SERVICE_INTERACTIVE_PROCESS
)
SERVICE_BOOT_START = 0
SERVICE_SYSTEM_START = 1
SERVICE_AUTO_START = 2
SERVICE_DEMAND_START = 3
SERVICE_DISABLED = 4
SERVICE_ERROR_IGNORE = 0
SERVICE_ERROR_NORMAL = 1
SERVICE_ERROR_SEVERE = 2
SERVICE_ERROR_CRITICAL = 3
TAPE_ERASE_SHORT = 0
TAPE_ERASE_LONG = 1
TAPE_LOAD = 0
TAPE_UNLOAD = 1
TAPE_TENSION = 2
TAPE_LOCK = 3
TAPE_UNLOCK = 4
TAPE_FORMAT = 5
TAPE_SETMARKS = 0
TAPE_FILEMARKS = 1
TAPE_SHORT_FILEMARKS = 2
TAPE_LONG_FILEMARKS = 3
TAPE_ABSOLUTE_POSITION = 0
TAPE_LOGICAL_POSITION = 1
TAPE_PSEUDO_LOGICAL_POSITION = 2
TAPE_REWIND = 0
TAPE_ABSOLUTE_BLOCK = 1
TAPE_LOGICAL_BLOCK = 2
TAPE_PSEUDO_LOGICAL_BLOCK = 3
TAPE_SPACE_END_OF_DATA = 4
TAPE_SPACE_RELATIVE_BLOCKS = 5
TAPE_SPACE_FILEMARKS = 6
TAPE_SPACE_SEQUENTIAL_FMKS = 7
TAPE_SPACE_SETMARKS = 8
TAPE_SPACE_SEQUENTIAL_SMKS = 9
TAPE_DRIVE_FIXED = 1
TAPE_DRIVE_SELECT = 2
TAPE_DRIVE_INITIATOR = 4
TAPE_DRIVE_ERASE_SHORT = 16
TAPE_DRIVE_ERASE_LONG = 32
TAPE_DRIVE_ERASE_BOP_ONLY = 64
TAPE_DRIVE_ERASE_IMMEDIATE = 128
TAPE_DRIVE_TAPE_CAPACITY = 256
TAPE_DRIVE_TAPE_REMAINING = 512
TAPE_DRIVE_FIXED_BLOCK = 1024
TAPE_DRIVE_VARIABLE_BLOCK = 2048
TAPE_DRIVE_WRITE_PROTECT = 4096
TAPE_DRIVE_EOT_WZ_SIZE = 8192
TAPE_DRIVE_ECC = 65536
TAPE_DRIVE_COMPRESSION = 131072
TAPE_DRIVE_PADDING = 262144
TAPE_DRIVE_REPORT_SMKS = 524288
TAPE_DRIVE_GET_ABSOLUTE_BLK = 1048576
TAPE_DRIVE_GET_LOGICAL_BLK = 2097152
TAPE_DRIVE_SET_EOT_WZ_SIZE = 4194304
TAPE_DRIVE_EJECT_MEDIA = 16777216
TAPE_DRIVE_RESERVED_BIT = -2147483648
TAPE_DRIVE_LOAD_UNLOAD = -2147483647
TAPE_DRIVE_TENSION = -2147483646
TAPE_DRIVE_LOCK_UNLOCK = -2147483644
TAPE_DRIVE_REWIND_IMMEDIATE = -2147483640
TAPE_DRIVE_SET_BLOCK_SIZE = -2147483632
TAPE_DRIVE_LOAD_UNLD_IMMED = -2147483616
TAPE_DRIVE_TENSION_IMMED = -2147483584
TAPE_DRIVE_LOCK_UNLK_IMMED = -2147483520
TAPE_DRIVE_SET_ECC = -2147483392
TAPE_DRIVE_SET_COMPRESSION = -2147483136
TAPE_DRIVE_SET_PADDING = -2147482624
TAPE_DRIVE_SET_REPORT_SMKS = -2147481600
TAPE_DRIVE_ABSOLUTE_BLK = -2147479552
TAPE_DRIVE_ABS_BLK_IMMED = -2147475456
TAPE_DRIVE_LOGICAL_BLK = -2147467264
TAPE_DRIVE_LOG_BLK_IMMED = -2147450880
TAPE_DRIVE_END_OF_DATA = -2147418112
TAPE_DRIVE_RELATIVE_BLKS = -2147352576
TAPE_DRIVE_FILEMARKS = -2147221504
TAPE_DRIVE_SEQUENTIAL_FMKS = -2146959360
TAPE_DRIVE_SETMARKS = -2146435072
TAPE_DRIVE_SEQUENTIAL_SMKS = -2145386496
TAPE_DRIVE_REVERSE_POSITION = -2143289344
TAPE_DRIVE_SPACE_IMMEDIATE = -2139095040
TAPE_DRIVE_WRITE_SETMARKS = -2130706432
TAPE_DRIVE_WRITE_FILEMARKS = -2113929216
TAPE_DRIVE_WRITE_SHORT_FMKS = -2080374784
TAPE_DRIVE_WRITE_LONG_FMKS = -2013265920
TAPE_DRIVE_WRITE_MARK_IMMED = -1879048192
TAPE_DRIVE_FORMAT = -1610612736
TAPE_DRIVE_FORMAT_IMMEDIATE = -1073741824
TAPE_DRIVE_HIGH_FEATURES = -2147483648
TAPE_FIXED_PARTITIONS = 0
TAPE_SELECT_PARTITIONS = 1
TAPE_INITIATOR_PARTITIONS = 2

TRANSACTIONMANAGER_QUERY_INFORMATION = 0x0001
TRANSACTIONMANAGER_SET_INFORMATION = 0x0002
TRANSACTIONMANAGER_RECOVER = 0x0004
TRANSACTIONMANAGER_RENAME = 0x0008
TRANSACTIONMANAGER_CREATE_RM = 0x0010
TRANSACTIONMANAGER_BIND_TRANSACTION = 0x0020
TRANSACTIONMANAGER_GENERIC_READ = (
    STANDARD_RIGHTS_READ | TRANSACTIONMANAGER_QUERY_INFORMATION
)
TRANSACTIONMANAGER_GENERIC_WRITE = (
    STANDARD_RIGHTS_WRITE
    | TRANSACTIONMANAGER_SET_INFORMATION
    | TRANSACTIONMANAGER_RECOVER
    | TRANSACTIONMANAGER_RENAME
    | TRANSACTIONMANAGER_CREATE_RM
)
TRANSACTIONMANAGER_GENERIC_EXECUTE = STANDARD_RIGHTS_EXECUTE
TRANSACTIONMANAGER_ALL_ACCESS = (
    STANDARD_RIGHTS_REQUIRED
    | TRANSACTIONMANAGER_GENERIC_READ
    | TRANSACTIONMANAGER_GENERIC_WRITE
    | TRANSACTIONMANAGER_GENERIC_EXECUTE
    | TRANSACTIONMANAGER_BIND_TRANSACTION
)

TRANSACTION_QUERY_INFORMATION = 0x0001
TRANSACTION_SET_INFORMATION = 0x0002
TRANSACTION_ENLIST = 0x0004
TRANSACTION_COMMIT = 0x0008
TRANSACTION_ROLLBACK = 0x0010
TRANSACTION_PROPAGATE = 0x0020
TRANSACTION_SAVEPOINT = 0x0040
TRANSACTION_MARSHALL = TRANSACTION_QUERY_INFORMATION
TRANSACTION_GENERIC_READ = (
    STANDARD_RIGHTS_READ | TRANSACTION_QUERY_INFORMATION | SYNCHRONIZE
)
TRANSACTION_GENERIC_WRITE = (
    STANDARD_RIGHTS_WRITE
    | TRANSACTION_SET_INFORMATION
    | TRANSACTION_COMMIT
    | TRANSACTION_ENLIST
    | TRANSACTION_ROLLBACK
    | TRANSACTION_PROPAGATE
    | TRANSACTION_SAVEPOINT
    | SYNCHRONIZE
)
TRANSACTION_GENERIC_EXECUTE = (
    STANDARD_RIGHTS_EXECUTE | TRANSACTION_COMMIT | TRANSACTION_ROLLBACK | SYNCHRONIZE
)
TRANSACTION_ALL_ACCESS = (
    STANDARD_RIGHTS_REQUIRED
    | TRANSACTION_GENERIC_READ
    | TRANSACTION_GENERIC_WRITE
    | TRANSACTION_GENERIC_EXECUTE
)
TRANSACTION_RESOURCE_MANAGER_RIGHTS = (
    TRANSACTION_GENERIC_READ
    | STANDARD_RIGHTS_WRITE
    | TRANSACTION_SET_INFORMATION
    | TRANSACTION_ENLIST
    | TRANSACTION_ROLLBACK
    | TRANSACTION_PROPAGATE
    | SYNCHRONIZE
)

RESOURCEMANAGER_QUERY_INFORMATION = 0x0001
RESOURCEMANAGER_SET_INFORMATION = 0x0002
RESOURCEMANAGER_RECOVER = 0x0004
RESOURCEMANAGER_ENLIST = 0x0008
RESOURCEMANAGER_GET_NOTIFICATION = 0x0010
RESOURCEMANAGER_REGISTER_PROTOCOL = 0x0020
RESOURCEMANAGER_COMPLETE_PROPAGATION = 0x0040
RESOURCEMANAGER_GENERIC_READ = (
    STANDARD_RIGHTS_READ | RESOURCEMANAGER_QUERY_INFORMATION | SYNCHRONIZE
)
RESOURCEMANAGER_GENERIC_WRITE = (
    STANDARD_RIGHTS_WRITE
    | RESOURCEMANAGER_SET_INFORMATION
    | RESOURCEMANAGER_RECOVER
    | RESOURCEMANAGER_ENLIST
    | RESOURCEMANAGER_GET_NOTIFICATION
    | RESOURCEMANAGER_REGISTER_PROTOCOL
    | RESOURCEMANAGER_COMPLETE_PROPAGATION
    | SYNCHRONIZE
)
RESOURCEMANAGER_GENERIC_EXECUTE = (
    STANDARD_RIGHTS_EXECUTE
    | RESOURCEMANAGER_RECOVER
    | RESOURCEMANAGER_ENLIST
    | RESOURCEMANAGER_GET_NOTIFICATION
    | RESOURCEMANAGER_COMPLETE_PROPAGATION
    | SYNCHRONIZE
)
RESOURCEMANAGER_ALL_ACCESS = (
    STANDARD_RIGHTS_REQUIRED
    | RESOURCEMANAGER_GENERIC_READ
    | RESOURCEMANAGER_GENERIC_WRITE
    | RESOURCEMANAGER_GENERIC_EXECUTE
)

ENLISTMENT_QUERY_INFORMATION = 0x0001
ENLISTMENT_SET_INFORMATION = 0x0002
ENLISTMENT_RECOVER = 0x0004
ENLISTMENT_SUBORDINATE_RIGHTS = 0x0008
ENLISTMENT_SUPERIOR_RIGHTS = 0x0010
ENLISTMENT_GENERIC_READ = STANDARD_RIGHTS_READ | ENLISTMENT_QUERY_INFORMATION
ENLISTMENT_GENERIC_WRITE = (
    STANDARD_RIGHTS_WRITE
    | ENLISTMENT_SET_INFORMATION
    | ENLISTMENT_RECOVER
    | ENLISTMENT_SUBORDINATE_RIGHTS
    | ENLISTMENT_SUPERIOR_RIGHTS
)
ENLISTMENT_GENERIC_EXECUTE = (
    STANDARD_RIGHTS_EXECUTE
    | ENLISTMENT_RECOVER
    | ENLISTMENT_SUBORDINATE_RIGHTS
    | ENLISTMENT_SUPERIOR_RIGHTS
)
ENLISTMENT_ALL_ACCESS = (
    STANDARD_RIGHTS_REQUIRED
    | ENLISTMENT_GENERIC_READ
    | ENLISTMENT_GENERIC_WRITE
    | ENLISTMENT_GENERIC_EXECUTE
)


## TRANSACTION_OUTCOME enum
TransactionOutcomeUndetermined = 1
TransactionOutcomeCommitted = 2
TransactionOutcomeAborted = 3

## TRANSACTION_STATE enum
TransactionStateNormal = 1
TransactionStateIndoubt = 2
TransactionStateCommittedNotify = 3

## TRANSACTION_INFORMATION_CLASS enum
TransactionBasicInformation = 0
TransactionPropertiesInformation = 1
TransactionEnlistmentInformation = 2
TransactionFullInformation = 3

## TRANSACTIONMANAGER_INFORMATION_CLASS enum
TransactionManagerBasicInformation = 0
TransactionManagerLogInformation = 1
TransactionManagerLogPathInformation = 2
TransactionManagerOnlineProbeInformation = 3

## RESOURCEMANAGER_INFORMATION_CLASS ENUM
ResourceManagerBasicInformation = 0
ResourceManagerCompletionInformation = 1
ResourceManagerFullInformation = 2
ResourceManagerNameInformation = 3

## ENLISTMENT_INFORMATION_CLASS enum
EnlistmentBasicInformation = 0
EnlistmentRecoveryInformation = 1
EnlistmentFullInformation = 2
EnlistmentNameInformation = 3

## KTMOBJECT_TYPE enum
KTMOBJECT_TRANSACTION = 0
KTMOBJECT_TRANSACTION_MANAGER = 1
KTMOBJECT_RESOURCE_MANAGER = 2
KTMOBJECT_ENLISTMENT = 3
KTMOBJECT_INVALID = 4

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\win32\lib\winnt.py ===
# Generated by h2py from \mssdk\include\winnt.h

APPLICATION_ERROR_MASK = 536870912
ERROR_SEVERITY_SUCCESS = 0
ERROR_SEVERITY_INFORMATIONAL = 1073741824
ERROR_SEVERITY_WARNING = -2147483648
ERROR_SEVERITY_ERROR = -1073741824
MINCHAR = 128
MAXCHAR = 127
MINSHORT = 32768
MAXSHORT = 32767
MINLONG = -2147483648
MAXLONG = 2147483647
MAXBYTE = 255
MAXWORD = 65535
MAXDWORD = -1
LANG_NEUTRAL = 0
LANG_AFRIKAANS = 54
LANG_ALBANIAN = 28
LANG_ARABIC = 1
LANG_BASQUE = 45
LANG_BELARUSIAN = 35
LANG_BULGARIAN = 2
LANG_CATALAN = 3
LANG_CHINESE = 4
LANG_CROATIAN = 26
LANG_CZECH = 5
LANG_DANISH = 6
LANG_DUTCH = 19
LANG_ENGLISH = 9
LANG_ESTONIAN = 37
LANG_FAEROESE = 56
LANG_FARSI = 41
LANG_FINNISH = 11
LANG_FRENCH = 12
LANG_GERMAN = 7
LANG_GREEK = 8
LANG_HEBREW = 13
LANG_HINDI = 57
LANG_HUNGARIAN = 14
LANG_ICELANDIC = 15
LANG_INDONESIAN = 33
LANG_ITALIAN = 16
LANG_JAPANESE = 17
LANG_KOREAN = 18
LANG_LATVIAN = 38
LANG_LITHUANIAN = 39
LANG_MACEDONIAN = 47
LANG_MALAY = 62
LANG_NORWEGIAN = 20
LANG_POLISH = 21
LANG_PORTUGUESE = 22
LANG_ROMANIAN = 24
LANG_RUSSIAN = 25
LANG_SERBIAN = 26
LANG_SLOVAK = 27
LANG_SLOVENIAN = 36
LANG_SPANISH = 10
LANG_SWAHILI = 65
LANG_SWEDISH = 29
LANG_THAI = 30
LANG_TURKISH = 31
LANG_UKRAINIAN = 34
LANG_VIETNAMESE = 42
SUBLANG_NEUTRAL = 0
SUBLANG_DEFAULT = 1
SUBLANG_SYS_DEFAULT = 2
SUBLANG_ARABIC_SAUDI_ARABIA = 1
SUBLANG_ARABIC_IRAQ = 2
SUBLANG_ARABIC_EGYPT = 3
SUBLANG_ARABIC_LIBYA = 4
SUBLANG_ARABIC_ALGERIA = 5
SUBLANG_ARABIC_MOROCCO = 6
SUBLANG_ARABIC_TUNISIA = 7
SUBLANG_ARABIC_OMAN = 8
SUBLANG_ARABIC_YEMEN = 9
SUBLANG_ARABIC_SYRIA = 10
SUBLANG_ARABIC_JORDAN = 11
SUBLANG_ARABIC_LEBANON = 12
SUBLANG_ARABIC_KUWAIT = 13
SUBLANG_ARABIC_UAE = 14
SUBLANG_ARABIC_BAHRAIN = 15
SUBLANG_ARABIC_QATAR = 16
SUBLANG_CHINESE_TRADITIONAL = 1
SUBLANG_CHINESE_SIMPLIFIED = 2
SUBLANG_CHINESE_HONGKONG = 3
SUBLANG_CHINESE_SINGAPORE = 4
SUBLANG_CHINESE_MACAU = 5
SUBLANG_DUTCH = 1
SUBLANG_DUTCH_BELGIAN = 2
SUBLANG_ENGLISH_US = 1
SUBLANG_ENGLISH_UK = 2
SUBLANG_ENGLISH_AUS = 3
SUBLANG_ENGLISH_CAN = 4
SUBLANG_ENGLISH_NZ = 5
SUBLANG_ENGLISH_EIRE = 6
SUBLANG_ENGLISH_SOUTH_AFRICA = 7
SUBLANG_ENGLISH_JAMAICA = 8
SUBLANG_ENGLISH_CARIBBEAN = 9
SUBLANG_ENGLISH_BELIZE = 10
SUBLANG_ENGLISH_TRINIDAD = 11
SUBLANG_ENGLISH_ZIMBABWE = 12
SUBLANG_ENGLISH_PHILIPPINES = 13
SUBLANG_FRENCH = 1
SUBLANG_FRENCH_BELGIAN = 2
SUBLANG_FRENCH_CANADIAN = 3
SUBLANG_FRENCH_SWISS = 4
SUBLANG_FRENCH_LUXEMBOURG = 5
SUBLANG_FRENCH_MONACO = 6
SUBLANG_GERMAN = 1
SUBLANG_GERMAN_SWISS = 2
SUBLANG_GERMAN_AUSTRIAN = 3
SUBLANG_GERMAN_LUXEMBOURG = 4
SUBLANG_GERMAN_LIECHTENSTEIN = 5
SUBLANG_ITALIAN = 1
SUBLANG_ITALIAN_SWISS = 2
SUBLANG_KOREAN = 1
SUBLANG_KOREAN_JOHAB = 2
SUBLANG_LITHUANIAN = 1
SUBLANG_LITHUANIAN_CLASSIC = 2
SUBLANG_MALAY_MALAYSIA = 1
SUBLANG_MALAY_BRUNEI_DARUSSALAM = 2
SUBLANG_NORWEGIAN_BOKMAL = 1
SUBLANG_NORWEGIAN_NYNORSK = 2
SUBLANG_PORTUGUESE = 2
SUBLANG_PORTUGUESE_BRAZILIAN = 1
SUBLANG_SERBIAN_LATIN = 2
SUBLANG_SERBIAN_CYRILLIC = 3
SUBLANG_SPANISH = 1
SUBLANG_SPANISH_MEXICAN = 2
SUBLANG_SPANISH_MODERN = 3
SUBLANG_SPANISH_GUATEMALA = 4
SUBLANG_SPANISH_COSTA_RICA = 5
SUBLANG_SPANISH_PANAMA = 6
SUBLANG_SPANISH_DOMINICAN_REPUBLIC = 7
SUBLANG_SPANISH_VENEZUELA = 8
SUBLANG_SPANISH_COLOMBIA = 9
SUBLANG_SPANISH_PERU = 10
SUBLANG_SPANISH_ARGENTINA = 11
SUBLANG_SPANISH_ECUADOR = 12
SUBLANG_SPANISH_CHILE = 13
SUBLANG_SPANISH_URUGUAY = 14
SUBLANG_SPANISH_PARAGUAY = 15
SUBLANG_SPANISH_BOLIVIA = 16
SUBLANG_SPANISH_EL_SALVADOR = 17
SUBLANG_SPANISH_HONDURAS = 18
SUBLANG_SPANISH_NICARAGUA = 19
SUBLANG_SPANISH_PUERTO_RICO = 20
SUBLANG_SWEDISH = 1
SUBLANG_SWEDISH_FINLAND = 2
SORT_DEFAULT = 0
SORT_JAPANESE_XJIS = 0
SORT_JAPANESE_UNICODE = 1
SORT_CHINESE_BIG5 = 0
SORT_CHINESE_PRCP = 0
SORT_CHINESE_UNICODE = 1
SORT_CHINESE_PRC = 2
SORT_KOREAN_KSC = 0
SORT_KOREAN_UNICODE = 1
SORT_GERMAN_PHONE_BOOK = 1


def PRIMARYLANGID(lgid):
    return (lgid) & 1023


def SUBLANGID(lgid):
    return (lgid) >> 10


NLS_VALID_LOCALE_MASK = 1048575


def LANGIDFROMLCID(lcid):
    return lcid


def SORTIDFROMLCID(lcid):
    return ((lcid) & NLS_VALID_LOCALE_MASK) >> 16


MAXIMUM_WAIT_OBJECTS = 64
MAXIMUM_SUSPEND_COUNT = MAXCHAR

EXCEPTION_NONCONTINUABLE = 1
EXCEPTION_MAXIMUM_PARAMETERS = 15
PROCESS_TERMINATE = 1
PROCESS_CREATE_THREAD = 2
PROCESS_VM_OPERATION = 8
PROCESS_VM_READ = 16
PROCESS_VM_WRITE = 32
PROCESS_DUP_HANDLE = 64
PROCESS_CREATE_PROCESS = 128
PROCESS_SET_QUOTA = 256
PROCESS_SET_INFORMATION = 512
PROCESS_QUERY_INFORMATION = 1024
PROCESS_SUSPEND_RESUME = 2048
PROCESS_QUERY_LIMITED_INFORMATION = 4096
PROCESS_SET_LIMITED_INFORMATION = 8192
MAXIMUM_PROCESSORS = 32
THREAD_TERMINATE = 1
THREAD_SUSPEND_RESUME = 2
THREAD_GET_CONTEXT = 8
THREAD_SET_CONTEXT = 16
THREAD_SET_INFORMATION = 32
THREAD_QUERY_INFORMATION = 64
THREAD_SET_THREAD_TOKEN = 128
THREAD_IMPERSONATE = 256
THREAD_DIRECT_IMPERSONATION = 512
THREAD_SET_LIMITED_INFORMATION = 1024
THREAD_QUERY_LIMITED_INFORMATION = 2048
THREAD_RESUME = 4096
JOB_OBJECT_ASSIGN_PROCESS = 1
JOB_OBJECT_SET_ATTRIBUTES = 2
JOB_OBJECT_QUERY = 4
JOB_OBJECT_TERMINATE = 8
TLS_MINIMUM_AVAILABLE = 64
THREAD_BASE_PRIORITY_LOWRT = 15
THREAD_BASE_PRIORITY_MAX = 2
THREAD_BASE_PRIORITY_MIN = -2
THREAD_BASE_PRIORITY_IDLE = -15
JOB_OBJECT_LIMIT_WORKINGSET = 1
JOB_OBJECT_LIMIT_PROCESS_TIME = 2
JOB_OBJECT_LIMIT_JOB_TIME = 4
JOB_OBJECT_LIMIT_ACTIVE_PROCESS = 8
JOB_OBJECT_LIMIT_AFFINITY = 16
JOB_OBJECT_LIMIT_PRIORITY_CLASS = 32
JOB_OBJECT_LIMIT_VALID_FLAGS = 63
EVENT_MODIFY_STATE = 2
MUTANT_QUERY_STATE = 1
SEMAPHORE_MODIFY_STATE = 2
TIME_ZONE_ID_UNKNOWN = 0
TIME_ZONE_ID_STANDARD = 1
TIME_ZONE_ID_DAYLIGHT = 2
PROCESSOR_INTEL_386 = 386
PROCESSOR_INTEL_486 = 486
PROCESSOR_INTEL_PENTIUM = 586
PROCESSOR_MIPS_R4000 = 4000
PROCESSOR_ALPHA_21064 = 21064
PROCESSOR_HITACHI_SH3 = 10003
PROCESSOR_HITACHI_SH3E = 10004
PROCESSOR_HITACHI_SH4 = 10005
PROCESSOR_MOTOROLA_821 = 821
PROCESSOR_ARM_7TDMI = 70001
PROCESSOR_ARCHITECTURE_INTEL = 0
PROCESSOR_ARCHITECTURE_MIPS = 1
PROCESSOR_ARCHITECTURE_ALPHA = 2
PROCESSOR_ARCHITECTURE_PPC = 3
PROCESSOR_ARCHITECTURE_SH = 4
PROCESSOR_ARCHITECTURE_ARM = 5
PROCESSOR_ARCHITECTURE_IA64 = 6
PROCESSOR_ARCHITECTURE_ALPHA64 = 7
PROCESSOR_ARCHITECTURE_MSIL = 8
PROCESSOR_ARCHITECTURE_AMD64 = 9
PROCESSOR_ARCHITECTURE_IA32_ON_WIN64 = 10
PROCESSOR_ARCHITECTURE_UNKNOWN = 65535
PF_FLOATING_POINT_PRECISION_ERRATA = 0
PF_FLOATING_POINT_EMULATED = 1
PF_COMPARE_EXCHANGE_DOUBLE = 2
PF_MMX_INSTRUCTIONS_AVAILABLE = 3
PF_PPC_MOVEMEM_64BIT_OK = 4
PF_ALPHA_BYTE_INSTRUCTIONS = 5
SECTION_QUERY = 1
SECTION_MAP_WRITE = 2
SECTION_MAP_READ = 4
SECTION_MAP_EXECUTE = 8
SECTION_EXTEND_SIZE = 16
PAGE_NOACCESS = 1
PAGE_READONLY = 2
PAGE_READWRITE = 4
PAGE_WRITECOPY = 8
PAGE_EXECUTE = 16
PAGE_EXECUTE_READ = 32
PAGE_EXECUTE_READWRITE = 64
PAGE_EXECUTE_WRITECOPY = 128
PAGE_GUARD = 256
PAGE_NOCACHE = 512
MEM_COMMIT = 4096
MEM_RESERVE = 8192
MEM_DECOMMIT = 16384
MEM_RELEASE = 32768
MEM_FREE = 65536
MEM_PRIVATE = 131072
MEM_MAPPED = 262144
MEM_RESET = 524288
MEM_TOP_DOWN = 1048576
MEM_4MB_PAGES = -2147483648
SEC_FILE = 8388608
SEC_IMAGE = 16777216
SEC_VLM = 33554432
SEC_RESERVE = 67108864
SEC_COMMIT = 134217728
SEC_NOCACHE = 268435456
MEM_IMAGE = SEC_IMAGE
FILE_READ_DATA = 1
FILE_LIST_DIRECTORY = 1
FILE_WRITE_DATA = 2
FILE_ADD_FILE = 2
FILE_APPEND_DATA = 4
FILE_ADD_SUBDIRECTORY = 4
FILE_CREATE_PIPE_INSTANCE = 4
FILE_READ_EA = 8
FILE_WRITE_EA = 16
FILE_EXECUTE = 32
FILE_TRAVERSE = 32
FILE_DELETE_CHILD = 64
FILE_READ_ATTRIBUTES = 128
FILE_WRITE_ATTRIBUTES = 256
FILE_SHARE_READ = 1
FILE_SHARE_WRITE = 2
FILE_SHARE_DELETE = 4
FILE_ATTRIBUTE_READONLY = 1
FILE_ATTRIBUTE_HIDDEN = 2
FILE_ATTRIBUTE_SYSTEM = 4
FILE_ATTRIBUTE_DIRECTORY = 16
FILE_ATTRIBUTE_ARCHIVE = 32
FILE_ATTRIBUTE_DEVICE = 64
FILE_ATTRIBUTE_NORMAL = 128
FILE_ATTRIBUTE_TEMPORARY = 256
FILE_ATTRIBUTE_SPARSE_FILE = 512
FILE_ATTRIBUTE_REPARSE_POINT = 1024
FILE_ATTRIBUTE_COMPRESSED = 2048
FILE_ATTRIBUTE_OFFLINE = 4096
FILE_ATTRIBUTE_NOT_CONTENT_INDEXED = 8192
FILE_ATTRIBUTE_ENCRYPTED = 16384
FILE_ATTRIBUTE_VIRTUAL = 65536
FILE_NOTIFY_CHANGE_FILE_NAME = 1
FILE_NOTIFY_CHANGE_DIR_NAME = 2
FILE_NOTIFY_CHANGE_ATTRIBUTES = 4
FILE_NOTIFY_CHANGE_SIZE = 8
FILE_NOTIFY_CHANGE_LAST_WRITE = 16
FILE_NOTIFY_CHANGE_LAST_ACCESS = 32
FILE_NOTIFY_CHANGE_CREATION = 64
FILE_NOTIFY_CHANGE_SECURITY = 256
FILE_ACTION_ADDED = 1
FILE_ACTION_REMOVED = 2
FILE_ACTION_MODIFIED = 3
FILE_ACTION_RENAMED_OLD_NAME = 4
FILE_ACTION_RENAMED_NEW_NAME = 5
FILE_CASE_SENSITIVE_SEARCH = 1
FILE_CASE_PRESERVED_NAMES = 2
FILE_UNICODE_ON_DISK = 4
FILE_PERSISTENT_ACLS = 8
FILE_FILE_COMPRESSION = 16
FILE_VOLUME_QUOTAS = 32
FILE_SUPPORTS_SPARSE_FILES = 64
FILE_SUPPORTS_REPARSE_POINTS = 128
FILE_SUPPORTS_REMOTE_STORAGE = 256
FILE_VOLUME_IS_COMPRESSED = 32768
FILE_SUPPORTS_OBJECT_IDS = 65536
FILE_SUPPORTS_ENCRYPTION = 131072

MAXIMUM_REPARSE_DATA_BUFFER_SIZE = 16 * 1024
IO_REPARSE_TAG_RESERVED_ZERO = 0
IO_REPARSE_TAG_RESERVED_ONE = 1
IO_REPARSE_TAG_SYMBOLIC_LINK = 2
IO_REPARSE_TAG_NSS = 5
IO_REPARSE_TAG_FILTER_MANAGER = -2147483637
IO_REPARSE_TAG_DFS = -2147483638
IO_REPARSE_TAG_SIS = -2147483641
IO_REPARSE_TAG_MOUNT_POINT = -1610612733
IO_REPARSE_TAG_HSM = -1073741820
IO_REPARSE_TAG_NSSRECOVER = 8
IO_REPARSE_TAG_RESERVED_MS_RANGE = 256
IO_REPARSE_TAG_RESERVED_RANGE = IO_REPARSE_TAG_RESERVED_ONE
IO_COMPLETION_MODIFY_STATE = 2

DUPLICATE_CLOSE_SOURCE = 1
DUPLICATE_SAME_ACCESS = 2
DELETE = 65536
READ_CONTROL = 131072
WRITE_DAC = 262144
WRITE_OWNER = 524288
SYNCHRONIZE = 1048576
STANDARD_RIGHTS_REQUIRED = 983040
STANDARD_RIGHTS_READ = READ_CONTROL
STANDARD_RIGHTS_WRITE = READ_CONTROL
STANDARD_RIGHTS_EXECUTE = READ_CONTROL
STANDARD_RIGHTS_ALL = 2031616
SPECIFIC_RIGHTS_ALL = 65535
IO_COMPLETION_ALL_ACCESS = STANDARD_RIGHTS_REQUIRED | SYNCHRONIZE | 0x3
ACCESS_SYSTEM_SECURITY = 16777216
MAXIMUM_ALLOWED = 33554432
GENERIC_READ = -2147483648
GENERIC_WRITE = 1073741824
GENERIC_EXECUTE = 536870912
GENERIC_ALL = 268435456

# Included from pshpack4.h

# Included from poppack.h
SID_REVISION = 1
SID_MAX_SUB_AUTHORITIES = 15
SID_RECOMMENDED_SUB_AUTHORITIES = 1

SidTypeUser = 1
SidTypeGroup = 2
SidTypeDomain = 3
SidTypeAlias = 4
SidTypeWellKnownGroup = 5
SidTypeDeletedAccount = 6
SidTypeInvalid = 7
SidTypeUnknown = 8

SECURITY_NULL_RID = 0
SECURITY_WORLD_RID = 0
SECURITY_LOCAL_RID = 0x00000000
SECURITY_CREATOR_OWNER_RID = 0
SECURITY_CREATOR_GROUP_RID = 1
SECURITY_CREATOR_OWNER_SERVER_RID = 2
SECURITY_CREATOR_GROUP_SERVER_RID = 3
SECURITY_DIALUP_RID = 1
SECURITY_NETWORK_RID = 2
SECURITY_BATCH_RID = 3
SECURITY_INTERACTIVE_RID = 4
SECURITY_SERVICE_RID = 6
SECURITY_ANONYMOUS_LOGON_RID = 7
SECURITY_PROXY_RID = 8
SECURITY_SERVER_LOGON_RID = 9
SECURITY_PRINCIPAL_SELF_RID = 10
SECURITY_AUTHENTICATED_USER_RID = 11
SECURITY_LOGON_IDS_RID = 5
SECURITY_LOGON_IDS_RID_COUNT = 3
SECURITY_LOCAL_SYSTEM_RID = 18
SECURITY_NT_NON_UNIQUE = 21
SECURITY_BUILTIN_DOMAIN_RID = 32
DOMAIN_USER_RID_ADMIN = 500
DOMAIN_USER_RID_GUEST = 501
DOMAIN_GROUP_RID_ADMINS = 512
DOMAIN_GROUP_RID_USERS = 513
DOMAIN_GROUP_RID_GUESTS = 514
DOMAIN_ALIAS_RID_ADMINS = 544
DOMAIN_ALIAS_RID_USERS = 545
DOMAIN_ALIAS_RID_GUESTS = 546
DOMAIN_ALIAS_RID_POWER_USERS = 547
DOMAIN_ALIAS_RID_ACCOUNT_OPS = 548
DOMAIN_ALIAS_RID_SYSTEM_OPS = 549
DOMAIN_ALIAS_RID_PRINT_OPS = 550
DOMAIN_ALIAS_RID_BACKUP_OPS = 551
DOMAIN_ALIAS_RID_REPLICATOR = 552
SE_GROUP_MANDATORY = 1
SE_GROUP_ENABLED_BY_DEFAULT = 2
SE_GROUP_ENABLED = 4
SE_GROUP_OWNER = 8
SE_GROUP_LOGON_ID = -1073741824
ACL_REVISION = 2
ACL_REVISION_DS = 4
ACL_REVISION1 = 1
ACL_REVISION2 = 2
ACL_REVISION3 = 3
ACL_REVISION4 = 4
MAX_ACL_REVISION = ACL_REVISION4

## ACE types
ACCESS_MIN_MS_ACE_TYPE = 0
ACCESS_ALLOWED_ACE_TYPE = 0
ACCESS_DENIED_ACE_TYPE = 1
SYSTEM_AUDIT_ACE_TYPE = 2
SYSTEM_ALARM_ACE_TYPE = 3
ACCESS_MAX_MS_V2_ACE_TYPE = 3
ACCESS_ALLOWED_COMPOUND_ACE_TYPE = 4
ACCESS_MAX_MS_V3_ACE_TYPE = 4
ACCESS_MIN_MS_OBJECT_ACE_TYPE = 5
ACCESS_ALLOWED_OBJECT_ACE_TYPE = 5
ACCESS_DENIED_OBJECT_ACE_TYPE = 6
SYSTEM_AUDIT_OBJECT_ACE_TYPE = 7
SYSTEM_ALARM_OBJECT_ACE_TYPE = 8
ACCESS_MAX_MS_OBJECT_ACE_TYPE = 8
ACCESS_MAX_MS_V4_ACE_TYPE = 8
ACCESS_MAX_MS_ACE_TYPE = 8
ACCESS_ALLOWED_CALLBACK_ACE_TYPE = 9
ACCESS_DENIED_CALLBACK_ACE_TYPE = 10
ACCESS_ALLOWED_CALLBACK_OBJECT_ACE_TYPE = 11
ACCESS_DENIED_CALLBACK_OBJECT_ACE_TYPE = 12
SYSTEM_AUDIT_CALLBACK_ACE_TYPE = 13
SYSTEM_ALARM_CALLBACK_ACE_TYPE = 14
SYSTEM_AUDIT_CALLBACK_OBJECT_ACE_TYPE = 15
SYSTEM_ALARM_CALLBACK_OBJECT_ACE_TYPE = 16
SYSTEM_MANDATORY_LABEL_ACE_TYPE = 17
ACCESS_MAX_MS_V5_ACE_TYPE = 17

## ACE inheritance flags
OBJECT_INHERIT_ACE = 1
CONTAINER_INHERIT_ACE = 2
NO_PROPAGATE_INHERIT_ACE = 4
INHERIT_ONLY_ACE = 8
INHERITED_ACE = 16
VALID_INHERIT_FLAGS = 31


SUCCESSFUL_ACCESS_ACE_FLAG = 64
FAILED_ACCESS_ACE_FLAG = 128
ACE_OBJECT_TYPE_PRESENT = 1
ACE_INHERITED_OBJECT_TYPE_PRESENT = 2
SECURITY_DESCRIPTOR_REVISION = 1
SECURITY_DESCRIPTOR_REVISION1 = 1
SECURITY_DESCRIPTOR_MIN_LENGTH = 20
SE_OWNER_DEFAULTED = 1
SE_GROUP_DEFAULTED = 2
SE_DACL_PRESENT = 4
SE_DACL_DEFAULTED = 8
SE_SACL_PRESENT = 16
SE_SACL_DEFAULTED = 32
SE_DACL_AUTO_INHERIT_REQ = 256
SE_SACL_AUTO_INHERIT_REQ = 512
SE_DACL_AUTO_INHERITED = 1024
SE_SACL_AUTO_INHERITED = 2048
SE_DACL_PROTECTED = 4096
SE_SACL_PROTECTED = 8192
SE_SELF_RELATIVE = 32768
ACCESS_OBJECT_GUID = 0
ACCESS_PROPERTY_SET_GUID = 1
ACCESS_PROPERTY_GUID = 2
ACCESS_MAX_LEVEL = 4
AUDIT_ALLOW_NO_PRIVILEGE = 1
ACCESS_DS_SOURCE_A = "Directory Service"
ACCESS_DS_OBJECT_TYPE_NAME_A = "Directory Service Object"
SE_PRIVILEGE_ENABLED_BY_DEFAULT = 1
SE_PRIVILEGE_ENABLED = 2
SE_PRIVILEGE_USED_FOR_ACCESS = -2147483648
PRIVILEGE_SET_ALL_NECESSARY = 1

SE_CREATE_TOKEN_NAME = "SeCreateTokenPrivilege"
SE_ASSIGNPRIMARYTOKEN_NAME = "SeAssignPrimaryTokenPrivilege"
SE_LOCK_MEMORY_NAME = "SeLockMemoryPrivilege"
SE_INCREASE_QUOTA_NAME = "SeIncreaseQuotaPrivilege"
SE_UNSOLICITED_INPUT_NAME = "SeUnsolicitedInputPrivilege"
SE_MACHINE_ACCOUNT_NAME = "SeMachineAccountPrivilege"
SE_TCB_NAME = "SeTcbPrivilege"
SE_SECURITY_NAME = "SeSecurityPrivilege"
SE_TAKE_OWNERSHIP_NAME = "SeTakeOwnershipPrivilege"
SE_LOAD_DRIVER_NAME = "SeLoadDriverPrivilege"
SE_SYSTEM_PROFILE_NAME = "SeSystemProfilePrivilege"
SE_SYSTEMTIME_NAME = "SeSystemtimePrivilege"
SE_PROF_SINGLE_PROCESS_NAME = "SeProfileSingleProcessPrivilege"
SE_INC_BASE_PRIORITY_NAME = "SeIncreaseBasePriorityPrivilege"
SE_CREATE_PAGEFILE_NAME = "SeCreatePagefilePrivilege"
SE_CREATE_PERMANENT_NAME = "SeCreatePermanentPrivilege"
SE_BACKUP_NAME = "SeBackupPrivilege"
SE_RESTORE_NAME = "SeRestorePrivilege"
SE_SHUTDOWN_NAME = "SeShutdownPrivilege"
SE_DEBUG_NAME = "SeDebugPrivilege"
SE_AUDIT_NAME = "SeAuditPrivilege"
SE_SYSTEM_ENVIRONMENT_NAME = "SeSystemEnvironmentPrivilege"
SE_CHANGE_NOTIFY_NAME = "SeChangeNotifyPrivilege"
SE_REMOTE_SHUTDOWN_NAME = "SeRemoteShutdownPrivilege"
TOKEN_ASSIGN_PRIMARY = 1
TOKEN_DUPLICATE = 2
TOKEN_IMPERSONATE = 4
TOKEN_QUERY = 8
TOKEN_QUERY_SOURCE = 16
TOKEN_ADJUST_PRIVILEGES = 32
TOKEN_ADJUST_GROUPS = 64
TOKEN_ADJUST_DEFAULT = 128
TOKEN_ALL_ACCESS = (
    STANDARD_RIGHTS_REQUIRED
    | TOKEN_ASSIGN_PRIMARY
    | TOKEN_DUPLICATE
    | TOKEN_IMPERSONATE
    | TOKEN_QUERY
    | TOKEN_QUERY_SOURCE
    | TOKEN_ADJUST_PRIVILEGES
    | TOKEN_ADJUST_GROUPS
    | TOKEN_ADJUST_DEFAULT
)
TOKEN_READ = STANDARD_RIGHTS_READ | TOKEN_QUERY
TOKEN_WRITE = (
    STANDARD_RIGHTS_WRITE
    | TOKEN_ADJUST_PRIVILEGES
    | TOKEN_ADJUST_GROUPS
    | TOKEN_ADJUST_DEFAULT
)
TOKEN_EXECUTE = STANDARD_RIGHTS_EXECUTE
TOKEN_SOURCE_LENGTH = 8

# Token types
TokenPrimary = 1
TokenImpersonation = 2

# TOKEN_INFORMATION_CLASS, used with Get/SetTokenInformation
TokenUser = 1
TokenGroups = 2
TokenPrivileges = 3
TokenOwner = 4
TokenPrimaryGroup = 5
TokenDefaultDacl = 6
TokenSource = 7
TokenType = 8
TokenImpersonationLevel = 9
TokenStatistics = 10
TokenRestrictedSids = 11
TokenSessionId = 12
TokenGroupsAndPrivileges = 13
TokenSessionReference = 14
TokenSandBoxInert = 15
TokenAuditPolicy = 16
TokenOrigin = 17
TokenElevationType = 18
TokenLinkedToken = 19
TokenElevation = 20
TokenHasRestrictions = 21
TokenAccessInformation = 22
TokenVirtualizationAllowed = 23
TokenVirtualizationEnabled = 24
TokenIntegrityLevel = 25
TokenUIAccess = 26
TokenMandatoryPolicy = 27
TokenLogonSid = 28

OWNER_SECURITY_INFORMATION = 0x00000001
GROUP_SECURITY_INFORMATION = 0x00000002
DACL_SECURITY_INFORMATION = 0x00000004
SACL_SECURITY_INFORMATION = 0x00000008
LABEL_SECURITY_INFORMATION = 0x00000010

IMAGE_DOS_SIGNATURE = 23117
IMAGE_OS2_SIGNATURE = 17742
IMAGE_OS2_SIGNATURE_LE = 17740
IMAGE_VXD_SIGNATURE = 17740
IMAGE_NT_SIGNATURE = 17744
IMAGE_SIZEOF_FILE_HEADER = 20
IMAGE_FILE_RELOCS_STRIPPED = 1
IMAGE_FILE_EXECUTABLE_IMAGE = 2
IMAGE_FILE_LINE_NUMS_STRIPPED = 4
IMAGE_FILE_LOCAL_SYMS_STRIPPED = 8
IMAGE_FILE_AGGRESIVE_WS_TRIM = 16
IMAGE_FILE_LARGE_ADDRESS_AWARE = 32
IMAGE_FILE_BYTES_REVERSED_LO = 128
IMAGE_FILE_32BIT_MACHINE = 256
IMAGE_FILE_DEBUG_STRIPPED = 512
IMAGE_FILE_REMOVABLE_RUN_FROM_SWAP = 1024
IMAGE_FILE_NET_RUN_FROM_SWAP = 2048
IMAGE_FILE_SYSTEM = 4096
IMAGE_FILE_DLL = 8192
IMAGE_FILE_UP_SYSTEM_ONLY = 16384
IMAGE_FILE_BYTES_REVERSED_HI = 32768
IMAGE_FILE_MACHINE_UNKNOWN = 0
IMAGE_FILE_MACHINE_I386 = 332
IMAGE_FILE_MACHINE_R3000 = 354
IMAGE_FILE_MACHINE_R4000 = 358
IMAGE_FILE_MACHINE_R10000 = 360
IMAGE_FILE_MACHINE_WCEMIPSV2 = 361
IMAGE_FILE_MACHINE_ALPHA = 388
IMAGE_FILE_MACHINE_POWERPC = 496
IMAGE_FILE_MACHINE_SH3 = 418
IMAGE_FILE_MACHINE_SH3E = 420
IMAGE_FILE_MACHINE_SH4 = 422
IMAGE_FILE_MACHINE_ARM = 448
IMAGE_NUMBEROF_DIRECTORY_ENTRIES = 16
IMAGE_SIZEOF_ROM_OPTIONAL_HEADER = 56
IMAGE_SIZEOF_STD_OPTIONAL_HEADER = 28
IMAGE_SIZEOF_NT_OPTIONAL_HEADER = 224
IMAGE_NT_OPTIONAL_HDR_MAGIC = 267
IMAGE_ROM_OPTIONAL_HDR_MAGIC = 263
IMAGE_SUBSYSTEM_UNKNOWN = 0
IMAGE_SUBSYSTEM_NATIVE = 1
IMAGE_SUBSYSTEM_WINDOWS_GUI = 2
IMAGE_SUBSYSTEM_WINDOWS_CUI = 3
IMAGE_SUBSYSTEM_WINDOWS_CE_GUI = 4
IMAGE_SUBSYSTEM_OS2_CUI = 5
IMAGE_SUBSYSTEM_POSIX_CUI = 7
IMAGE_SUBSYSTEM_RESERVED8 = 8
IMAGE_DLLCHARACTERISTICS_WDM_DRIVER = 8192
IMAGE_DIRECTORY_ENTRY_EXPORT = 0
IMAGE_DIRECTORY_ENTRY_IMPORT = 1
IMAGE_DIRECTORY_ENTRY_RESOURCE = 2
IMAGE_DIRECTORY_ENTRY_EXCEPTION = 3
IMAGE_DIRECTORY_ENTRY_SECURITY = 4
IMAGE_DIRECTORY_ENTRY_BASERELOC = 5
IMAGE_DIRECTORY_ENTRY_DEBUG = 6
IMAGE_DIRECTORY_ENTRY_COPYRIGHT = 7
IMAGE_DIRECTORY_ENTRY_GLOBALPTR = 8
IMAGE_DIRECTORY_ENTRY_TLS = 9
IMAGE_DIRECTORY_ENTRY_LOAD_CONFIG = 10
IMAGE_DIRECTORY_ENTRY_BOUND_IMPORT = 11
IMAGE_DIRECTORY_ENTRY_IAT = 12
IMAGE_SIZEOF_SHORT_NAME = 8
IMAGE_SIZEOF_SECTION_HEADER = 40
IMAGE_SCN_TYPE_NO_PAD = 8
IMAGE_SCN_CNT_CODE = 32
IMAGE_SCN_CNT_INITIALIZED_DATA = 64
IMAGE_SCN_CNT_UNINITIALIZED_DATA = 128
IMAGE_SCN_LNK_OTHER = 256
IMAGE_SCN_LNK_INFO = 512
IMAGE_SCN_LNK_REMOVE = 2048
IMAGE_SCN_LNK_COMDAT = 4096
IMAGE_SCN_MEM_FARDATA = 32768
IMAGE_SCN_MEM_PURGEABLE = 131072
IMAGE_SCN_MEM_16BIT = 131072
IMAGE_SCN_MEM_LOCKED = 262144
IMAGE_SCN_MEM_PRELOAD = 524288
IMAGE_SCN_ALIGN_1BYTES = 1048576
IMAGE_SCN_ALIGN_2BYTES = 2097152
IMAGE_SCN_ALIGN_4BYTES = 3145728
IMAGE_SCN_ALIGN_8BYTES = 4194304
IMAGE_SCN_ALIGN_16BYTES = 5242880
IMAGE_SCN_ALIGN_32BYTES = 6291456
IMAGE_SCN_ALIGN_64BYTES = 7340032
IMAGE_SCN_LNK_NRELOC_OVFL = 16777216
IMAGE_SCN_MEM_DISCARDABLE = 33554432
IMAGE_SCN_MEM_NOT_CACHED = 67108864
IMAGE_SCN_MEM_NOT_PAGED = 134217728
IMAGE_SCN_MEM_SHARED = 268435456
IMAGE_SCN_MEM_EXECUTE = 536870912
IMAGE_SCN_MEM_READ = 1073741824
IMAGE_SCN_MEM_WRITE = -2147483648
IMAGE_SCN_SCALE_INDEX = 1
IMAGE_SIZEOF_SYMBOL = 18
IMAGE_SYM_TYPE_NULL = 0
IMAGE_SYM_TYPE_VOID = 1
IMAGE_SYM_TYPE_CHAR = 2
IMAGE_SYM_TYPE_SHORT = 3
IMAGE_SYM_TYPE_INT = 4
IMAGE_SYM_TYPE_LONG = 5
IMAGE_SYM_TYPE_FLOAT = 6
IMAGE_SYM_TYPE_DOUBLE = 7
IMAGE_SYM_TYPE_STRUCT = 8
IMAGE_SYM_TYPE_UNION = 9
IMAGE_SYM_TYPE_ENUM = 10
IMAGE_SYM_TYPE_MOE = 11
IMAGE_SYM_TYPE_BYTE = 12
IMAGE_SYM_TYPE_WORD = 13
IMAGE_SYM_TYPE_UINT = 14
IMAGE_SYM_TYPE_DWORD = 15
IMAGE_SYM_TYPE_PCODE = 32768
IMAGE_SYM_DTYPE_NULL = 0
IMAGE_SYM_DTYPE_POINTER = 1
IMAGE_SYM_DTYPE_FUNCTION = 2
IMAGE_SYM_DTYPE_ARRAY = 3
IMAGE_SYM_CLASS_NULL = 0
IMAGE_SYM_CLASS_AUTOMATIC = 1
IMAGE_SYM_CLASS_EXTERNAL = 2
IMAGE_SYM_CLASS_STATIC = 3
IMAGE_SYM_CLASS_REGISTER = 4
IMAGE_SYM_CLASS_EXTERNAL_DEF = 5
IMAGE_SYM_CLASS_LABEL = 6
IMAGE_SYM_CLASS_UNDEFINED_LABEL = 7
IMAGE_SYM_CLASS_MEMBER_OF_STRUCT = 8
IMAGE_SYM_CLASS_ARGUMENT = 9
IMAGE_SYM_CLASS_STRUCT_TAG = 10
IMAGE_SYM_CLASS_MEMBER_OF_UNION = 11
IMAGE_SYM_CLASS_UNION_TAG = 12
IMAGE_SYM_CLASS_TYPE_DEFINITION = 13
IMAGE_SYM_CLASS_UNDEFINED_STATIC = 14
IMAGE_SYM_CLASS_ENUM_TAG = 15
IMAGE_SYM_CLASS_MEMBER_OF_ENUM = 16
IMAGE_SYM_CLASS_REGISTER_PARAM = 17
IMAGE_SYM_CLASS_BIT_FIELD = 18
IMAGE_SYM_CLASS_FAR_EXTERNAL = 68
IMAGE_SYM_CLASS_BLOCK = 100
IMAGE_SYM_CLASS_FUNCTION = 101
IMAGE_SYM_CLASS_END_OF_STRUCT = 102
IMAGE_SYM_CLASS_FILE = 103
IMAGE_SYM_CLASS_SECTION = 104
IMAGE_SYM_CLASS_WEAK_EXTERNAL = 105
N_BTMASK = 15
N_TMASK = 48
N_TMASK1 = 192
N_TMASK2 = 240
N_BTSHFT = 4
N_TSHIFT = 2


def BTYPE(x):
    return (x) & N_BTMASK


def ISPTR(x):
    return ((x) & N_TMASK) == (IMAGE_SYM_DTYPE_POINTER << N_BTSHFT)


def ISFCN(x):
    return ((x) & N_TMASK) == (IMAGE_SYM_DTYPE_FUNCTION << N_BTSHFT)


def ISARY(x):
    return ((x) & N_TMASK) == (IMAGE_SYM_DTYPE_ARRAY << N_BTSHFT)


def INCREF(x):
    return (
        (((x) & ~N_BTMASK) << N_TSHIFT)
        | (IMAGE_SYM_DTYPE_POINTER << N_BTSHFT)
        | ((x) & N_BTMASK)
    )


def DECREF(x):
    return (((x) >> N_TSHIFT) & ~N_BTMASK) | ((x) & N_BTMASK)


IMAGE_SIZEOF_AUX_SYMBOL = 18
IMAGE_COMDAT_SELECT_NODUPLICATES = 1
IMAGE_COMDAT_SELECT_ANY = 2
IMAGE_COMDAT_SELECT_SAME_SIZE = 3
IMAGE_COMDAT_SELECT_EXACT_MATCH = 4
IMAGE_COMDAT_SELECT_ASSOCIATIVE = 5
IMAGE_COMDAT_SELECT_LARGEST = 6
IMAGE_COMDAT_SELECT_NEWEST = 7
IMAGE_WEAK_EXTERN_SEARCH_NOLIBRARY = 1
IMAGE_WEAK_EXTERN_SEARCH_LIBRARY = 2
IMAGE_WEAK_EXTERN_SEARCH_ALIAS = 3
IMAGE_SIZEOF_RELOCATION = 10
IMAGE_REL_I386_ABSOLUTE = 0
IMAGE_REL_I386_DIR16 = 1
IMAGE_REL_I386_REL16 = 2
IMAGE_REL_I386_DIR32 = 6
IMAGE_REL_I386_DIR32NB = 7
IMAGE_REL_I386_SEG12 = 9
IMAGE_REL_I386_SECTION = 10
IMAGE_REL_I386_SECREL = 11
IMAGE_REL_I386_REL32 = 20
IMAGE_REL_MIPS_ABSOLUTE = 0
IMAGE_REL_MIPS_REFHALF = 1
IMAGE_REL_MIPS_REFWORD = 2
IMAGE_REL_MIPS_JMPADDR = 3
IMAGE_REL_MIPS_REFHI = 4
IMAGE_REL_MIPS_REFLO = 5
IMAGE_REL_MIPS_GPREL = 6
IMAGE_REL_MIPS_LITERAL = 7
IMAGE_REL_MIPS_SECTION = 10
IMAGE_REL_MIPS_SECREL = 11
IMAGE_REL_MIPS_SECRELLO = 12
IMAGE_REL_MIPS_SECRELHI = 13
IMAGE_REL_MIPS_REFWORDNB = 34
IMAGE_REL_MIPS_PAIR = 37
IMAGE_REL_ALPHA_ABSOLUTE = 0
IMAGE_REL_ALPHA_REFLONG = 1
IMAGE_REL_ALPHA_REFQUAD = 2
IMAGE_REL_ALPHA_GPREL32 = 3
IMAGE_REL_ALPHA_LITERAL = 4
IMAGE_REL_ALPHA_LITUSE = 5
IMAGE_REL_ALPHA_GPDISP = 6
IMAGE_REL_ALPHA_BRADDR = 7
IMAGE_REL_ALPHA_HINT = 8
IMAGE_REL_ALPHA_INLINE_REFLONG = 9
IMAGE_REL_ALPHA_REFHI = 10
IMAGE_REL_ALPHA_REFLO = 11
IMAGE_REL_ALPHA_PAIR = 12
IMAGE_REL_ALPHA_MATCH = 13
IMAGE_REL_ALPHA_SECTION = 14
IMAGE_REL_ALPHA_SECREL = 15
IMAGE_REL_ALPHA_REFLONGNB = 16
IMAGE_REL_ALPHA_SECRELLO = 17
IMAGE_REL_ALPHA_SECRELHI = 18
IMAGE_REL_PPC_ABSOLUTE = 0
IMAGE_REL_PPC_ADDR64 = 1
IMAGE_REL_PPC_ADDR32 = 2
IMAGE_REL_PPC_ADDR24 = 3
IMAGE_REL_PPC_ADDR16 = 4
IMAGE_REL_PPC_ADDR14 = 5
IMAGE_REL_PPC_REL24 = 6
IMAGE_REL_PPC_REL14 = 7
IMAGE_REL_PPC_TOCREL16 = 8
IMAGE_REL_PPC_TOCREL14 = 9
IMAGE_REL_PPC_ADDR32NB = 10
IMAGE_REL_PPC_SECREL = 11
IMAGE_REL_PPC_SECTION = 12
IMAGE_REL_PPC_IFGLUE = 13
IMAGE_REL_PPC_IMGLUE = 14
IMAGE_REL_PPC_SECREL16 = 15
IMAGE_REL_PPC_REFHI = 16
IMAGE_REL_PPC_REFLO = 17
IMAGE_REL_PPC_PAIR = 18
IMAGE_REL_PPC_SECRELLO = 19
IMAGE_REL_PPC_SECRELHI = 20
IMAGE_REL_PPC_TYPEMASK = 255
IMAGE_REL_PPC_NEG = 256
IMAGE_REL_PPC_BRTAKEN = 512
IMAGE_REL_PPC_BRNTAKEN = 1024
IMAGE_REL_PPC_TOCDEFN = 2048
IMAGE_REL_SH3_ABSOLUTE = 0
IMAGE_REL_SH3_DIRECT16 = 1
IMAGE_REL_SH3_DIRECT32 = 2
IMAGE_REL_SH3_DIRECT8 = 3
IMAGE_REL_SH3_DIRECT8_WORD = 4
IMAGE_REL_SH3_DIRECT8_LONG = 5
IMAGE_REL_SH3_DIRECT4 = 6
IMAGE_REL_SH3_DIRECT4_WORD = 7
IMAGE_REL_SH3_DIRECT4_LONG = 8
IMAGE_REL_SH3_PCREL8_WORD = 9
IMAGE_REL_SH3_PCREL8_LONG = 10
IMAGE_REL_SH3_PCREL12_WORD = 11
IMAGE_REL_SH3_STARTOF_SECTION = 12
IMAGE_REL_SH3_SIZEOF_SECTION = 13
IMAGE_REL_SH3_SECTION = 14
IMAGE_REL_SH3_SECREL = 15
IMAGE_REL_SH3_DIRECT32_NB = 16
IMAGE_SIZEOF_LINENUMBER = 6
IMAGE_SIZEOF_BASE_RELOCATION = 8
IMAGE_REL_BASED_ABSOLUTE = 0
IMAGE_REL_BASED_HIGH = 1
IMAGE_REL_BASED_LOW = 2
IMAGE_REL_BASED_HIGHLOW = 3
IMAGE_REL_BASED_HIGHADJ = 4
IMAGE_REL_BASED_MIPS_JMPADDR = 5
IMAGE_REL_BASED_SECTION = 6
IMAGE_REL_BASED_REL32 = 7
IMAGE_ARCHIVE_START_SIZE = 8
IMAGE_ARCHIVE_START = "!<arch>\n"
IMAGE_ARCHIVE_END = "`\n"
IMAGE_ARCHIVE_PAD = "\n"
IMAGE_ARCHIVE_LINKER_MEMBER = "/               "
IMAGE_SIZEOF_ARCHIVE_MEMBER_HDR = 60
IMAGE_ORDINAL_FLAG = -2147483648


def IMAGE_SNAP_BY_ORDINAL(Ordinal):
    return (Ordinal & IMAGE_ORDINAL_FLAG) != 0


def IMAGE_ORDINAL(Ordinal):
    return Ordinal & 65535


IMAGE_RESOURCE_NAME_IS_STRING = -2147483648
IMAGE_RESOURCE_DATA_IS_DIRECTORY = -2147483648
IMAGE_DEBUG_TYPE_UNKNOWN = 0
IMAGE_DEBUG_TYPE_COFF = 1
IMAGE_DEBUG_TYPE_CODEVIEW = 2
IMAGE_DEBUG_TYPE_FPO = 3
IMAGE_DEBUG_TYPE_MISC = 4
IMAGE_DEBUG_TYPE_EXCEPTION = 5
IMAGE_DEBUG_TYPE_FIXUP = 6
IMAGE_DEBUG_TYPE_OMAP_TO_SRC = 7
IMAGE_DEBUG_TYPE_OMAP_FROM_SRC = 8
IMAGE_DEBUG_TYPE_BORLAND = 9
FRAME_FPO = 0
FRAME_TRAP = 1
FRAME_TSS = 2
FRAME_NONFPO = 3
SIZEOF_RFPO_DATA = 16
IMAGE_DEBUG_MISC_EXENAME = 1
IMAGE_SEPARATE_DEBUG_SIGNATURE = 18756
IMAGE_SEPARATE_DEBUG_FLAGS_MASK = 32768
IMAGE_SEPARATE_DEBUG_MISMATCH = 32768

# Included from string.h
_NLSCMPERROR = 2147483647
NULL = 0
HEAP_NO_SERIALIZE = 1
HEAP_GROWABLE = 2
HEAP_GENERATE_EXCEPTIONS = 4
HEAP_ZERO_MEMORY = 8
HEAP_REALLOC_IN_PLACE_ONLY = 16
HEAP_TAIL_CHECKING_ENABLED = 32
HEAP_FREE_CHECKING_ENABLED = 64
HEAP_DISABLE_COALESCE_ON_FREE = 128
HEAP_CREATE_ALIGN_16 = 65536
HEAP_CREATE_ENABLE_TRACING = 131072
HEAP_MAXIMUM_TAG = 4095
HEAP_PSEUDO_TAG_FLAG = 32768
HEAP_TAG_SHIFT = 16
IS_TEXT_UNICODE_ASCII16 = 1
IS_TEXT_UNICODE_REVERSE_ASCII16 = 16
IS_TEXT_UNICODE_STATISTICS = 2
IS_TEXT_UNICODE_REVERSE_STATISTICS = 32
IS_TEXT_UNICODE_CONTROLS = 4
IS_TEXT_UNICODE_REVERSE_CONTROLS = 64
IS_TEXT_UNICODE_SIGNATURE = 8
IS_TEXT_UNICODE_REVERSE_SIGNATURE = 128
IS_TEXT_UNICODE_ILLEGAL_CHARS = 256
IS_TEXT_UNICODE_ODD_LENGTH = 512
IS_TEXT_UNICODE_DBCS_LEADBYTE = 1024
IS_TEXT_UNICODE_NULL_BYTES = 4096
IS_TEXT_UNICODE_UNICODE_MASK = 15
IS_TEXT_UNICODE_REVERSE_MASK = 240
IS_TEXT_UNICODE_NOT_UNICODE_MASK = 3840
IS_TEXT_UNICODE_NOT_ASCII_MASK = 61440
COMPRESSION_FORMAT_NONE = 0
COMPRESSION_FORMAT_DEFAULT = 1
COMPRESSION_FORMAT_LZNT1 = 2
COMPRESSION_ENGINE_STANDARD = 0
COMPRESSION_ENGINE_MAXIMUM = 256
MESSAGE_RESOURCE_UNICODE = 1
RTL_CRITSECT_TYPE = 0
RTL_RESOURCE_TYPE = 1
SEF_DACL_AUTO_INHERIT = 1
SEF_SACL_AUTO_INHERIT = 2
SEF_DEFAULT_DESCRIPTOR_FOR_OBJECT = 4
SEF_AVOID_PRIVILEGE_CHECK = 8
DLL_PROCESS_ATTACH = 1
DLL_THREAD_ATTACH = 2
DLL_THREAD_DETACH = 3
DLL_PROCESS_DETACH = 0
EVENTLOG_SEQUENTIAL_READ = 0x0001
EVENTLOG_SEEK_READ = 0x0002
EVENTLOG_FORWARDS_READ = 0x0004
EVENTLOG_BACKWARDS_READ = 0x0008
EVENTLOG_SUCCESS = 0x0000
EVENTLOG_ERROR_TYPE = 1
EVENTLOG_WARNING_TYPE = 2
EVENTLOG_INFORMATION_TYPE = 4
EVENTLOG_AUDIT_SUCCESS = 8
EVENTLOG_AUDIT_FAILURE = 16
EVENTLOG_START_PAIRED_EVENT = 1
EVENTLOG_END_PAIRED_EVENT = 2
EVENTLOG_END_ALL_PAIRED_EVENTS = 4
EVENTLOG_PAIRED_EVENT_ACTIVE = 8
EVENTLOG_PAIRED_EVENT_INACTIVE = 16
KEY_QUERY_VALUE = 1
KEY_SET_VALUE = 2
KEY_CREATE_SUB_KEY = 4
KEY_ENUMERATE_SUB_KEYS = 8
KEY_NOTIFY = 16
KEY_CREATE_LINK = 32
KEY_READ = (
    STANDARD_RIGHTS_READ | KEY_QUERY_VALUE | KEY_ENUMERATE_SUB_KEYS | KEY_NOTIFY
) & (~SYNCHRONIZE)
KEY_WRITE = (STANDARD_RIGHTS_WRITE | KEY_SET_VALUE | KEY_CREATE_SUB_KEY) & (
    ~SYNCHRONIZE
)
KEY_EXECUTE = (KEY_READ) & (~SYNCHRONIZE)
KEY_ALL_ACCESS = (
    STANDARD_RIGHTS_ALL
    | KEY_QUERY_VALUE
    | KEY_SET_VALUE
    | KEY_CREATE_SUB_KEY
    | KEY_ENUMERATE_SUB_KEYS
    | KEY_NOTIFY
    | KEY_CREATE_LINK
) & (~SYNCHRONIZE)
REG_OPTION_RESERVED = 0
REG_OPTION_NON_VOLATILE = 0
REG_OPTION_VOLATILE = 1
REG_OPTION_CREATE_LINK = 2
REG_OPTION_BACKUP_RESTORE = 4
REG_OPTION_OPEN_LINK = 8
REG_LEGAL_OPTION = (
    REG_OPTION_RESERVED
    | REG_OPTION_NON_VOLATILE
    | REG_OPTION_VOLATILE
    | REG_OPTION_CREATE_LINK
    | REG_OPTION_BACKUP_RESTORE
    | REG_OPTION_OPEN_LINK
)

## dispositions returned from RegCreateKeyEx
REG_CREATED_NEW_KEY = 1
REG_OPENED_EXISTING_KEY = 2

## flags used with RegSaveKeyEx
REG_STANDARD_FORMAT = 1
REG_LATEST_FORMAT = 2
REG_NO_COMPRESSION = 4

## flags used with RegRestoreKey
REG_WHOLE_HIVE_VOLATILE = 1
REG_REFRESH_HIVE = 2
REG_NO_LAZY_FLUSH = 4
REG_FORCE_RESTORE = 8

REG_NOTIFY_CHANGE_NAME = 1
REG_NOTIFY_CHANGE_ATTRIBUTES = 2
REG_NOTIFY_CHANGE_LAST_SET = 4
REG_NOTIFY_CHANGE_SECURITY = 8
REG_LEGAL_CHANGE_FILTER = (
    REG_NOTIFY_CHANGE_NAME
    | REG_NOTIFY_CHANGE_ATTRIBUTES
    | REG_NOTIFY_CHANGE_LAST_SET
    | REG_NOTIFY_CHANGE_SECURITY
)
REG_NONE = 0
REG_SZ = 1
REG_EXPAND_SZ = 2
REG_BINARY = 3
REG_DWORD = 4
REG_DWORD_LITTLE_ENDIAN = 4
REG_DWORD_BIG_ENDIAN = 5
REG_LINK = 6
REG_MULTI_SZ = 7
REG_RESOURCE_LIST = 8
REG_FULL_RESOURCE_DESCRIPTOR = 9
REG_RESOURCE_REQUIREMENTS_LIST = 10
SERVICE_KERNEL_DRIVER = 1
SERVICE_FILE_SYSTEM_DRIVER = 2
SERVICE_ADAPTER = 4
SERVICE_RECOGNIZER_DRIVER = 8
SERVICE_DRIVER = (
    SERVICE_KERNEL_DRIVER | SERVICE_FILE_SYSTEM_DRIVER | SERVICE_RECOGNIZER_DRIVER
)
SERVICE_WIN32_OWN_PROCESS = 16
SERVICE_WIN32_SHARE_PROCESS = 32
SERVICE_WIN32 = SERVICE_WIN32_OWN_PROCESS | SERVICE_WIN32_SHARE_PROCESS
SERVICE_INTERACTIVE_PROCESS = 256
SERVICE_TYPE_ALL = (
    SERVICE_WIN32 | SERVICE_ADAPTER | SERVICE_DRIVER | SERVICE_INTERACTIVE_PROCESS
)
SERVICE_BOOT_START = 0
SERVICE_SYSTEM_START = 1
SERVICE_AUTO_START = 2
SERVICE_DEMAND_START = 3
SERVICE_DISABLED = 4
SERVICE_ERROR_IGNORE = 0
SERVICE_ERROR_NORMAL = 1
SERVICE_ERROR_SEVERE = 2
SERVICE_ERROR_CRITICAL = 3
TAPE_ERASE_SHORT = 0
TAPE_ERASE_LONG = 1
TAPE_LOAD = 0
TAPE_UNLOAD = 1
TAPE_TENSION = 2
TAPE_LOCK = 3
TAPE_UNLOCK = 4
TAPE_FORMAT = 5
TAPE_SETMARKS = 0
TAPE_FILEMARKS = 1
TAPE_SHORT_FILEMARKS = 2
TAPE_LONG_FILEMARKS = 3
TAPE_ABSOLUTE_POSITION = 0
TAPE_LOGICAL_POSITION = 1
TAPE_PSEUDO_LOGICAL_POSITION = 2
TAPE_REWIND = 0
TAPE_ABSOLUTE_BLOCK = 1
TAPE_LOGICAL_BLOCK = 2
TAPE_PSEUDO_LOGICAL_BLOCK = 3
TAPE_SPACE_END_OF_DATA = 4
TAPE_SPACE_RELATIVE_BLOCKS = 5
TAPE_SPACE_FILEMARKS = 6
TAPE_SPACE_SEQUENTIAL_FMKS = 7
TAPE_SPACE_SETMARKS = 8
TAPE_SPACE_SEQUENTIAL_SMKS = 9
TAPE_DRIVE_FIXED = 1
TAPE_DRIVE_SELECT = 2
TAPE_DRIVE_INITIATOR = 4
TAPE_DRIVE_ERASE_SHORT = 16
TAPE_DRIVE_ERASE_LONG = 32
TAPE_DRIVE_ERASE_BOP_ONLY = 64
TAPE_DRIVE_ERASE_IMMEDIATE = 128
TAPE_DRIVE_TAPE_CAPACITY = 256
TAPE_DRIVE_TAPE_REMAINING = 512
TAPE_DRIVE_FIXED_BLOCK = 1024
TAPE_DRIVE_VARIABLE_BLOCK = 2048
TAPE_DRIVE_WRITE_PROTECT = 4096
TAPE_DRIVE_EOT_WZ_SIZE = 8192
TAPE_DRIVE_ECC = 65536
TAPE_DRIVE_COMPRESSION = 131072
TAPE_DRIVE_PADDING = 262144
TAPE_DRIVE_REPORT_SMKS = 524288
TAPE_DRIVE_GET_ABSOLUTE_BLK = 1048576
TAPE_DRIVE_GET_LOGICAL_BLK = 2097152
TAPE_DRIVE_SET_EOT_WZ_SIZE = 4194304
TAPE_DRIVE_EJECT_MEDIA = 16777216
TAPE_DRIVE_RESERVED_BIT = -2147483648
TAPE_DRIVE_LOAD_UNLOAD = -2147483647
TAPE_DRIVE_TENSION = -2147483646
TAPE_DRIVE_LOCK_UNLOCK = -2147483644
TAPE_DRIVE_REWIND_IMMEDIATE = -2147483640
TAPE_DRIVE_SET_BLOCK_SIZE = -2147483632
TAPE_DRIVE_LOAD_UNLD_IMMED = -2147483616
TAPE_DRIVE_TENSION_IMMED = -2147483584
TAPE_DRIVE_LOCK_UNLK_IMMED = -2147483520
TAPE_DRIVE_SET_ECC = -2147483392
TAPE_DRIVE_SET_COMPRESSION = -2147483136
TAPE_DRIVE_SET_PADDING = -2147482624
TAPE_DRIVE_SET_REPORT_SMKS = -2147481600
TAPE_DRIVE_ABSOLUTE_BLK = -2147479552
TAPE_DRIVE_ABS_BLK_IMMED = -2147475456
TAPE_DRIVE_LOGICAL_BLK = -2147467264
TAPE_DRIVE_LOG_BLK_IMMED = -2147450880
TAPE_DRIVE_END_OF_DATA = -2147418112
TAPE_DRIVE_RELATIVE_BLKS = -2147352576
TAPE_DRIVE_FILEMARKS = -2147221504
TAPE_DRIVE_SEQUENTIAL_FMKS = -2146959360
TAPE_DRIVE_SETMARKS = -2146435072
TAPE_DRIVE_SEQUENTIAL_SMKS = -2145386496
TAPE_DRIVE_REVERSE_POSITION = -2143289344
TAPE_DRIVE_SPACE_IMMEDIATE = -2139095040
TAPE_DRIVE_WRITE_SETMARKS = -2130706432
TAPE_DRIVE_WRITE_FILEMARKS = -2113929216
TAPE_DRIVE_WRITE_SHORT_FMKS = -2080374784
TAPE_DRIVE_WRITE_LONG_FMKS = -2013265920
TAPE_DRIVE_WRITE_MARK_IMMED = -1879048192
TAPE_DRIVE_FORMAT = -1610612736
TAPE_DRIVE_FORMAT_IMMEDIATE = -1073741824
TAPE_DRIVE_HIGH_FEATURES = -2147483648
TAPE_FIXED_PARTITIONS = 0
TAPE_SELECT_PARTITIONS = 1
TAPE_INITIATOR_PARTITIONS = 2

TRANSACTIONMANAGER_QUERY_INFORMATION = 0x0001
TRANSACTIONMANAGER_SET_INFORMATION = 0x0002
TRANSACTIONMANAGER_RECOVER = 0x0004
TRANSACTIONMANAGER_RENAME = 0x0008
TRANSACTIONMANAGER_CREATE_RM = 0x0010
TRANSACTIONMANAGER_BIND_TRANSACTION = 0x0020
TRANSACTIONMANAGER_GENERIC_READ = (
    STANDARD_RIGHTS_READ | TRANSACTIONMANAGER_QUERY_INFORMATION
)
TRANSACTIONMANAGER_GENERIC_WRITE = (
    STANDARD_RIGHTS_WRITE
    | TRANSACTIONMANAGER_SET_INFORMATION
    | TRANSACTIONMANAGER_RECOVER
    | TRANSACTIONMANAGER_RENAME
    | TRANSACTIONMANAGER_CREATE_RM
)
TRANSACTIONMANAGER_GENERIC_EXECUTE = STANDARD_RIGHTS_EXECUTE
TRANSACTIONMANAGER_ALL_ACCESS = (
    STANDARD_RIGHTS_REQUIRED
    | TRANSACTIONMANAGER_GENERIC_READ
    | TRANSACTIONMANAGER_GENERIC_WRITE
    | TRANSACTIONMANAGER_GENERIC_EXECUTE
    | TRANSACTIONMANAGER_BIND_TRANSACTION
)

TRANSACTION_QUERY_INFORMATION = 0x0001
TRANSACTION_SET_INFORMATION = 0x0002
TRANSACTION_ENLIST = 0x0004
TRANSACTION_COMMIT = 0x0008
TRANSACTION_ROLLBACK = 0x0010
TRANSACTION_PROPAGATE = 0x0020
TRANSACTION_SAVEPOINT = 0x0040
TRANSACTION_MARSHALL = TRANSACTION_QUERY_INFORMATION
TRANSACTION_GENERIC_READ = (
    STANDARD_RIGHTS_READ | TRANSACTION_QUERY_INFORMATION | SYNCHRONIZE
)
TRANSACTION_GENERIC_WRITE = (
    STANDARD_RIGHTS_WRITE
    | TRANSACTION_SET_INFORMATION
    | TRANSACTION_COMMIT
    | TRANSACTION_ENLIST
    | TRANSACTION_ROLLBACK
    | TRANSACTION_PROPAGATE
    | TRANSACTION_SAVEPOINT
    | SYNCHRONIZE
)
TRANSACTION_GENERIC_EXECUTE = (
    STANDARD_RIGHTS_EXECUTE | TRANSACTION_COMMIT | TRANSACTION_ROLLBACK | SYNCHRONIZE
)
TRANSACTION_ALL_ACCESS = (
    STANDARD_RIGHTS_REQUIRED
    | TRANSACTION_GENERIC_READ
    | TRANSACTION_GENERIC_WRITE
    | TRANSACTION_GENERIC_EXECUTE
)
TRANSACTION_RESOURCE_MANAGER_RIGHTS = (
    TRANSACTION_GENERIC_READ
    | STANDARD_RIGHTS_WRITE
    | TRANSACTION_SET_INFORMATION
    | TRANSACTION_ENLIST
    | TRANSACTION_ROLLBACK
    | TRANSACTION_PROPAGATE
    | SYNCHRONIZE
)

RESOURCEMANAGER_QUERY_INFORMATION = 0x0001
RESOURCEMANAGER_SET_INFORMATION = 0x0002
RESOURCEMANAGER_RECOVER = 0x0004
RESOURCEMANAGER_ENLIST = 0x0008
RESOURCEMANAGER_GET_NOTIFICATION = 0x0010
RESOURCEMANAGER_REGISTER_PROTOCOL = 0x0020
RESOURCEMANAGER_COMPLETE_PROPAGATION = 0x0040
RESOURCEMANAGER_GENERIC_READ = (
    STANDARD_RIGHTS_READ | RESOURCEMANAGER_QUERY_INFORMATION | SYNCHRONIZE
)
RESOURCEMANAGER_GENERIC_WRITE = (
    STANDARD_RIGHTS_WRITE
    | RESOURCEMANAGER_SET_INFORMATION
    | RESOURCEMANAGER_RECOVER
    | RESOURCEMANAGER_ENLIST
    | RESOURCEMANAGER_GET_NOTIFICATION
    | RESOURCEMANAGER_REGISTER_PROTOCOL
    | RESOURCEMANAGER_COMPLETE_PROPAGATION
    | SYNCHRONIZE
)
RESOURCEMANAGER_GENERIC_EXECUTE = (
    STANDARD_RIGHTS_EXECUTE
    | RESOURCEMANAGER_RECOVER
    | RESOURCEMANAGER_ENLIST
    | RESOURCEMANAGER_GET_NOTIFICATION
    | RESOURCEMANAGER_COMPLETE_PROPAGATION
    | SYNCHRONIZE
)
RESOURCEMANAGER_ALL_ACCESS = (
    STANDARD_RIGHTS_REQUIRED
    | RESOURCEMANAGER_GENERIC_READ
    | RESOURCEMANAGER_GENERIC_WRITE
    | RESOURCEMANAGER_GENERIC_EXECUTE
)

ENLISTMENT_QUERY_INFORMATION = 0x0001
ENLISTMENT_SET_INFORMATION = 0x0002
ENLISTMENT_RECOVER = 0x0004
ENLISTMENT_SUBORDINATE_RIGHTS = 0x0008
ENLISTMENT_SUPERIOR_RIGHTS = 0x0010
ENLISTMENT_GENERIC_READ = STANDARD_RIGHTS_READ | ENLISTMENT_QUERY_INFORMATION
ENLISTMENT_GENERIC_WRITE = (
    STANDARD_RIGHTS_WRITE
    | ENLISTMENT_SET_INFORMATION
    | ENLISTMENT_RECOVER
    | ENLISTMENT_SUBORDINATE_RIGHTS
    | ENLISTMENT_SUPERIOR_RIGHTS
)
ENLISTMENT_GENERIC_EXECUTE = (
    STANDARD_RIGHTS_EXECUTE
    | ENLISTMENT_RECOVER
    | ENLISTMENT_SUBORDINATE_RIGHTS
    | ENLISTMENT_SUPERIOR_RIGHTS
)
ENLISTMENT_ALL_ACCESS = (
    STANDARD_RIGHTS_REQUIRED
    | ENLISTMENT_GENERIC_READ
    | ENLISTMENT_GENERIC_WRITE
    | ENLISTMENT_GENERIC_EXECUTE
)


## TRANSACTION_OUTCOME enum
TransactionOutcomeUndetermined = 1
TransactionOutcomeCommitted = 2
TransactionOutcomeAborted = 3

## TRANSACTION_STATE enum
TransactionStateNormal = 1
TransactionStateIndoubt = 2
TransactionStateCommittedNotify = 3

## TRANSACTION_INFORMATION_CLASS enum
TransactionBasicInformation = 0
TransactionPropertiesInformation = 1
TransactionEnlistmentInformation = 2
TransactionFullInformation = 3

## TRANSACTIONMANAGER_INFORMATION_CLASS enum
TransactionManagerBasicInformation = 0
TransactionManagerLogInformation = 1
TransactionManagerLogPathInformation = 2
TransactionManagerOnlineProbeInformation = 3

## RESOURCEMANAGER_INFORMATION_CLASS ENUM
ResourceManagerBasicInformation = 0
ResourceManagerCompletionInformation = 1
ResourceManagerFullInformation = 2
ResourceManagerNameInformation = 3

## ENLISTMENT_INFORMATION_CLASS enum
EnlistmentBasicInformation = 0
EnlistmentRecoveryInformation = 1
EnlistmentFullInformation = 2
EnlistmentNameInformation = 3

## KTMOBJECT_TYPE enum
KTMOBJECT_TRANSACTION = 0
KTMOBJECT_TRANSACTION_MANAGER = 1
KTMOBJECT_RESOURCE_MANAGER = 2
KTMOBJECT_ENLISTMENT = 3
KTMOBJECT_INVALID = 4