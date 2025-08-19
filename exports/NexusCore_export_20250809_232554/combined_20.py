
# === NexusCore/openenv\Lib\site-packages\numpy\lib\tests\test_arraysetops.py ===
"""Test functions for 1D array set operations.

"""
import pytest

import numpy as np
from numpy import ediff1d, intersect1d, isin, setdiff1d, setxor1d, union1d, unique
from numpy.exceptions import AxisError
from numpy.testing import (
    assert_array_equal,
    assert_equal,
    assert_raises,
    assert_raises_regex,
)


class TestSetOps:

    def test_intersect1d(self):
        # unique inputs
        a = np.array([5, 7, 1, 2])
        b = np.array([2, 4, 3, 1, 5])

        ec = np.array([1, 2, 5])
        c = intersect1d(a, b, assume_unique=True)
        assert_array_equal(c, ec)

        # non-unique inputs
        a = np.array([5, 5, 7, 1, 2])
        b = np.array([2, 1, 4, 3, 3, 1, 5])

        ed = np.array([1, 2, 5])
        c = intersect1d(a, b)
        assert_array_equal(c, ed)
        assert_array_equal([], intersect1d([], []))

    def test_intersect1d_array_like(self):
        # See gh-11772
        class Test:
            def __array__(self, dtype=None, copy=None):
                return np.arange(3)

        a = Test()
        res = intersect1d(a, a)
        assert_array_equal(res, a)
        res = intersect1d([1, 2, 3], [1, 2, 3])
        assert_array_equal(res, [1, 2, 3])

    def test_intersect1d_indices(self):
        # unique inputs
        a = np.array([1, 2, 3, 4])
        b = np.array([2, 1, 4, 6])
        c, i1, i2 = intersect1d(a, b, assume_unique=True, return_indices=True)
        ee = np.array([1, 2, 4])
        assert_array_equal(c, ee)
        assert_array_equal(a[i1], ee)
        assert_array_equal(b[i2], ee)

        # non-unique inputs
        a = np.array([1, 2, 2, 3, 4, 3, 2])
        b = np.array([1, 8, 4, 2, 2, 3, 2, 3])
        c, i1, i2 = intersect1d(a, b, return_indices=True)
        ef = np.array([1, 2, 3, 4])
        assert_array_equal(c, ef)
        assert_array_equal(a[i1], ef)
        assert_array_equal(b[i2], ef)

        # non1d, unique inputs
        a = np.array([[2, 4, 5, 6], [7, 8, 1, 15]])
        b = np.array([[3, 2, 7, 6], [10, 12, 8, 9]])
        c, i1, i2 = intersect1d(a, b, assume_unique=True, return_indices=True)
        ui1 = np.unravel_index(i1, a.shape)
        ui2 = np.unravel_index(i2, b.shape)
        ea = np.array([2, 6, 7, 8])
        assert_array_equal(ea, a[ui1])
        assert_array_equal(ea, b[ui2])

        # non1d, not assumed to be uniqueinputs
        a = np.array([[2, 4, 5, 6, 6], [4, 7, 8, 7, 2]])
        b = np.array([[3, 2, 7, 7], [10, 12, 8, 7]])
        c, i1, i2 = intersect1d(a, b, return_indices=True)
        ui1 = np.unravel_index(i1, a.shape)
        ui2 = np.unravel_index(i2, b.shape)
        ea = np.array([2, 7, 8])
        assert_array_equal(ea, a[ui1])
        assert_array_equal(ea, b[ui2])

    def test_setxor1d(self):
        a = np.array([5, 7, 1, 2])
        b = np.array([2, 4, 3, 1, 5])

        ec = np.array([3, 4, 7])
        c = setxor1d(a, b)
        assert_array_equal(c, ec)

        a = np.array([1, 2, 3])
        b = np.array([6, 5, 4])

        ec = np.array([1, 2, 3, 4, 5, 6])
        c = setxor1d(a, b)
        assert_array_equal(c, ec)

        a = np.array([1, 8, 2, 3])
        b = np.array([6, 5, 4, 8])

        ec = np.array([1, 2, 3, 4, 5, 6])
        c = setxor1d(a, b)
        assert_array_equal(c, ec)

        assert_array_equal([], setxor1d([], []))

    def test_setxor1d_unique(self):
        a = np.array([1, 8, 2, 3])
        b = np.array([6, 5, 4, 8])

        ec = np.array([1, 2, 3, 4, 5, 6])
        c = setxor1d(a, b, assume_unique=True)
        assert_array_equal(c, ec)

        a = np.array([[1], [8], [2], [3]])
        b = np.array([[6, 5], [4, 8]])

        ec = np.array([1, 2, 3, 4, 5, 6])
        c = setxor1d(a, b, assume_unique=True)
        assert_array_equal(c, ec)

    def test_ediff1d(self):
        zero_elem = np.array([])
        one_elem = np.array([1])
        two_elem = np.array([1, 2])

        assert_array_equal([], ediff1d(zero_elem))
        assert_array_equal([0], ediff1d(zero_elem, to_begin=0))
        assert_array_equal([0], ediff1d(zero_elem, to_end=0))
        assert_array_equal([-1, 0], ediff1d(zero_elem, to_begin=-1, to_end=0))
        assert_array_equal([], ediff1d(one_elem))
        assert_array_equal([1], ediff1d(two_elem))
        assert_array_equal([7, 1, 9], ediff1d(two_elem, to_begin=7, to_end=9))
        assert_array_equal([5, 6, 1, 7, 8],
                           ediff1d(two_elem, to_begin=[5, 6], to_end=[7, 8]))
        assert_array_equal([1, 9], ediff1d(two_elem, to_end=9))
        assert_array_equal([1, 7, 8], ediff1d(two_elem, to_end=[7, 8]))
        assert_array_equal([7, 1], ediff1d(two_elem, to_begin=7))
        assert_array_equal([5, 6, 1], ediff1d(two_elem, to_begin=[5, 6]))

    @pytest.mark.parametrize("ary, prepend, append, expected", [
        # should fail because trying to cast
        # np.nan standard floating point value
        # into an integer array:
        (np.array([1, 2, 3], dtype=np.int64),
         None,
         np.nan,
         'to_end'),
        # should fail because attempting
        # to downcast to int type:
        (np.array([1, 2, 3], dtype=np.int64),
         np.array([5, 7, 2], dtype=np.float32),
         None,
         'to_begin'),
        # should fail because attempting to cast
        # two special floating point values
        # to integers (on both sides of ary),
        # `to_begin` is in the error message as the impl checks this first:
        (np.array([1., 3., 9.], dtype=np.int8),
         np.nan,
         np.nan,
         'to_begin'),
         ])
    def test_ediff1d_forbidden_type_casts(self, ary, prepend, append, expected):
        # verify resolution of gh-11490

        # specifically, raise an appropriate
        # Exception when attempting to append or
        # prepend with an incompatible type
        msg = f'dtype of `{expected}` must be compatible'
        with assert_raises_regex(TypeError, msg):
            ediff1d(ary=ary,
                    to_end=append,
                    to_begin=prepend)

    @pytest.mark.parametrize(
        "ary,prepend,append,expected",
        [
         (np.array([1, 2, 3], dtype=np.int16),
          2**16,  # will be cast to int16 under same kind rule.
          2**16 + 4,
          np.array([0, 1, 1, 4], dtype=np.int16)),
         (np.array([1, 2, 3], dtype=np.float32),
          np.array([5], dtype=np.float64),
          None,
          np.array([5, 1, 1], dtype=np.float32)),
         (np.array([1, 2, 3], dtype=np.int32),
          0,
          0,
          np.array([0, 1, 1, 0], dtype=np.int32)),
         (np.array([1, 2, 3], dtype=np.int64),
          3,
          -9,
          np.array([3, 1, 1, -9], dtype=np.int64)),
        ]
    )
    def test_ediff1d_scalar_handling(self,
                                     ary,
                                     prepend,
                                     append,
                                     expected):
        # maintain backwards-compatibility
        # of scalar prepend / append behavior
        # in ediff1d following fix for gh-11490
        actual = np.ediff1d(ary=ary,
                            to_end=append,
                            to_begin=prepend)
        assert_equal(actual, expected)
        assert actual.dtype == expected.dtype

    @pytest.mark.parametrize("kind", [None, "sort", "table"])
    def test_isin(self, kind):
        def _isin_slow(a, b):
            b = np.asarray(b).flatten().tolist()
            return a in b
        isin_slow = np.vectorize(_isin_slow, otypes=[bool], excluded={1})

        def assert_isin_equal(a, b):
            x = isin(a, b, kind=kind)
            y = isin_slow(a, b)
            assert_array_equal(x, y)

        # multidimensional arrays in both arguments
        a = np.arange(24).reshape([2, 3, 4])
        b = np.array([[10, 20, 30], [0, 1, 3], [11, 22, 33]])
        assert_isin_equal(a, b)

        # array-likes as both arguments
        c = [(9, 8), (7, 6)]
        d = (9, 7)
        assert_isin_equal(c, d)

        # zero-d array:
        f = np.array(3)
        assert_isin_equal(f, b)
        assert_isin_equal(a, f)
        assert_isin_equal(f, f)

        # scalar:
        assert_isin_equal(5, b)
        assert_isin_equal(a, 6)
        assert_isin_equal(5, 6)

        # empty array-like:
        if kind != "table":
            # An empty list will become float64,
            # which is invalid for kind="table"
            x = []
            assert_isin_equal(x, b)
            assert_isin_equal(a, x)
            assert_isin_equal(x, x)

        # empty array with various types:
        for dtype in [bool, np.int64, np.float64]:
            if kind == "table" and dtype == np.float64:
                continue

            if dtype in {np.int64, np.float64}:
                ar = np.array([10, 20, 30], dtype=dtype)
            elif dtype in {bool}:
                ar = np.array([True, False, False])

            empty_array = np.array([], dtype=dtype)

            assert_isin_equal(empty_array, ar)
            assert_isin_equal(ar, empty_array)
            assert_isin_equal(empty_array, empty_array)

    @pytest.mark.parametrize("kind", [None, "sort", "table"])
    def test_isin_additional(self, kind):
        # we use two different sizes for the b array here to test the
        # two different paths in isin().
        for mult in (1, 10):
            # One check without np.array to make sure lists are handled correct
            a = [5, 7, 1, 2]
            b = [2, 4, 3, 1, 5] * mult
            ec = np.array([True, False, True, True])
            c = isin(a, b, assume_unique=True, kind=kind)
            assert_array_equal(c, ec)

            a[0] = 8
            ec = np.array([False, False, True, True])
            c = isin(a, b, assume_unique=True, kind=kind)
            assert_array_equal(c, ec)

            a[0], a[3] = 4, 8
            ec = np.array([True, False, True, False])
            c = isin(a, b, assume_unique=True, kind=kind)
            assert_array_equal(c, ec)

            a = np.array([5, 4, 5, 3, 4, 4, 3, 4, 3, 5, 2, 1, 5, 5])
            b = [2, 3, 4] * mult
            ec = [False, True, False, True, True, True, True, True, True,
                  False, True, False, False, False]
            c = isin(a, b, kind=kind)
            assert_array_equal(c, ec)

            b = b + [5, 5, 4] * mult
            ec = [True, True, True, True, True, True, True, True, True, True,
                  True, False, True, True]
            c = isin(a, b, kind=kind)
            assert_array_equal(c, ec)

            a = np.array([5, 7, 1, 2])
            b = np.array([2, 4, 3, 1, 5] * mult)
            ec = np.array([True, False, True, True])
            c = isin(a, b, kind=kind)
            assert_array_equal(c, ec)

            a = np.array([5, 7, 1, 1, 2])
            b = np.array([2, 4, 3, 3, 1, 5] * mult)
            ec = np.array([True, False, True, True, True])
            c = isin(a, b, kind=kind)
            assert_array_equal(c, ec)

            a = np.array([5, 5])
            b = np.array([2, 2] * mult)
            ec = np.array([False, False])
            c = isin(a, b, kind=kind)
            assert_array_equal(c, ec)

        a = np.array([5])
        b = np.array([2])
        ec = np.array([False])
        c = isin(a, b, kind=kind)
        assert_array_equal(c, ec)

        if kind in {None, "sort"}:
            assert_array_equal(isin([], [], kind=kind), [])

    def test_isin_char_array(self):
        a = np.array(['a', 'b', 'c', 'd', 'e', 'c', 'e', 'b'])
        b = np.array(['a', 'c'])

        ec = np.array([True, False, True, False, False, True, False, False])
        c = isin(a, b)

        assert_array_equal(c, ec)

    @pytest.mark.parametrize("kind", [None, "sort", "table"])
    def test_isin_invert(self, kind):
        "Test isin's invert parameter"
        # We use two different sizes for the b array here to test the
        # two different paths in isin().
        for mult in (1, 10):
            a = np.array([5, 4, 5, 3, 4, 4, 3, 4, 3, 5, 2, 1, 5, 5])
            b = [2, 3, 4] * mult
            assert_array_equal(np.invert(isin(a, b, kind=kind)),
                               isin(a, b, invert=True, kind=kind))

        # float:
        if kind in {None, "sort"}:
            for mult in (1, 10):
                a = np.array([5, 4, 5, 3, 4, 4, 3, 4, 3, 5, 2, 1, 5, 5],
                            dtype=np.float32)
                b = [2, 3, 4] * mult
                b = np.array(b, dtype=np.float32)
                assert_array_equal(np.invert(isin(a, b, kind=kind)),
                                   isin(a, b, invert=True, kind=kind))

    def test_isin_hit_alternate_algorithm(self):
        """Hit the standard isin code with integers"""
        # Need extreme range to hit standard code
        # This hits it without the use of kind='table'
        a = np.array([5, 4, 5, 3, 4, 4, 1e9], dtype=np.int64)
        b = np.array([2, 3, 4, 1e9], dtype=np.int64)
        expected = np.array([0, 1, 0, 1, 1, 1, 1], dtype=bool)
        assert_array_equal(expected, isin(a, b))
        assert_array_equal(np.invert(expected), isin(a, b, invert=True))

        a = np.array([5, 7, 1, 2], dtype=np.int64)
        b = np.array([2, 4, 3, 1, 5, 1e9], dtype=np.int64)
        ec = np.array([True, False, True, True])
        c = isin(a, b, assume_unique=True)
        assert_array_equal(c, ec)

    @pytest.mark.parametrize("kind", [None, "sort", "table"])
    def test_isin_boolean(self, kind):
        """Test that isin works for boolean input"""
        a = np.array([True, False])
        b = np.array([False, False, False])
        expected = np.array([False, True])
        assert_array_equal(expected,
                           isin(a, b, kind=kind))
        assert_array_equal(np.invert(expected),
                           isin(a, b, invert=True, kind=kind))

    @pytest.mark.parametrize("kind", [None, "sort"])
    def test_isin_timedelta(self, kind):
        """Test that isin works for timedelta input"""
        rstate = np.random.RandomState(0)
        a = rstate.randint(0, 100, size=10)
        b = rstate.randint(0, 100, size=10)
        truth = isin(a, b)
        a_timedelta = a.astype("timedelta64[s]")
        b_timedelta = b.astype("timedelta64[s]")
        assert_array_equal(truth, isin(a_timedelta, b_timedelta, kind=kind))

    def test_isin_table_timedelta_fails(self):
        a = np.array([0, 1, 2], dtype="timedelta64[s]")
        b = a
        # Make sure it raises a value error:
        with pytest.raises(ValueError):
            isin(a, b, kind="table")

    @pytest.mark.parametrize(
        "dtype1,dtype2",
        [
            (np.int8, np.int16),
            (np.int16, np.int8),
            (np.uint8, np.uint16),
            (np.uint16, np.uint8),
            (np.uint8, np.int16),
            (np.int16, np.uint8),
            (np.uint64, np.int64),
        ]
    )
    @pytest.mark.parametrize("kind", [None, "sort", "table"])
    def test_isin_mixed_dtype(self, dtype1, dtype2, kind):
        """Test that isin works as expected for mixed dtype input."""
        is_dtype2_signed = np.issubdtype(dtype2, np.signedinteger)
        ar1 = np.array([0, 0, 1, 1], dtype=dtype1)

        if is_dtype2_signed:
            ar2 = np.array([-128, 0, 127], dtype=dtype2)
        else:
            ar2 = np.array([127, 0, 255], dtype=dtype2)

        expected = np.array([True, True, False, False])

        expect_failure = kind == "table" and (
            dtype1 == np.int16 and dtype2 == np.int8)

        if expect_failure:
            with pytest.raises(RuntimeError, match="exceed the maximum"):
                isin(ar1, ar2, kind=kind)
        else:
            assert_array_equal(isin(ar1, ar2, kind=kind), expected)

    @pytest.mark.parametrize("data", [
        np.array([2**63, 2**63 + 1], dtype=np.uint64),
        np.array([-2**62, -2**62 - 1], dtype=np.int64),
    ])
    @pytest.mark.parametrize("kind", [None, "sort", "table"])
    def test_isin_mixed_huge_vals(self, kind, data):
        """Test values outside intp range (negative ones if 32bit system)"""
        query = data[1]
        res = np.isin(data, query, kind=kind)
        assert_array_equal(res, [False, True])
        # Also check that nothing weird happens for values can't possibly
        # in range.
        data = data.astype(np.int32)  # clearly different values
        res = np.isin(data, query, kind=kind)
        assert_array_equal(res, [False, False])

    @pytest.mark.parametrize("kind", [None, "sort", "table"])
    def test_isin_mixed_boolean(self, kind):
        """Test that isin works as expected for bool/int input."""
        for dtype in np.typecodes["AllInteger"]:
            a = np.array([True, False, False], dtype=bool)
            b = np.array([0, 0, 0, 0], dtype=dtype)
            expected = np.array([False, True, True], dtype=bool)
            assert_array_equal(isin(a, b, kind=kind), expected)

            a, b = b, a
            expected = np.array([True, True, True, True], dtype=bool)
            assert_array_equal(isin(a, b, kind=kind), expected)

    def test_isin_first_array_is_object(self):
        ar1 = [None]
        ar2 = np.array([1] * 10)
        expected = np.array([False])
        result = np.isin(ar1, ar2)
        assert_array_equal(result, expected)

    def test_isin_second_array_is_object(self):
        ar1 = 1
        ar2 = np.array([None] * 10)
        expected = np.array([False])
        result = np.isin(ar1, ar2)
        assert_array_equal(result, expected)

    def test_isin_both_arrays_are_object(self):
        ar1 = [None]
        ar2 = np.array([None] * 10)
        expected = np.array([True])
        result = np.isin(ar1, ar2)
        assert_array_equal(result, expected)

    def test_isin_both_arrays_have_structured_dtype(self):
        # Test arrays of a structured data type containing an integer field
        # and a field of dtype `object` allowing for arbitrary Python objects
        dt = np.dtype([('field1', int), ('field2', object)])
        ar1 = np.array([(1, None)], dtype=dt)
        ar2 = np.array([(1, None)] * 10, dtype=dt)
        expected = np.array([True])
        result = np.isin(ar1, ar2)
        assert_array_equal(result, expected)

    def test_isin_with_arrays_containing_tuples(self):
        ar1 = np.array([(1,), 2], dtype=object)
        ar2 = np.array([(1,), 2], dtype=object)
        expected = np.array([True, True])
        result = np.isin(ar1, ar2)
        assert_array_equal(result, expected)
        result = np.isin(ar1, ar2, invert=True)
        assert_array_equal(result, np.invert(expected))

        # An integer is added at the end of the array to make sure
        # that the array builder will create the array with tuples
        # and after it's created the integer is removed.
        # There's a bug in the array constructor that doesn't handle
        # tuples properly and adding the integer fixes that.
        ar1 = np.array([(1,), (2, 1), 1], dtype=object)
        ar1 = ar1[:-1]
        ar2 = np.array([(1,), (2, 1), 1], dtype=object)
        ar2 = ar2[:-1]
        expected = np.array([True, True])
        result = np.isin(ar1, ar2)
        assert_array_equal(result, expected)
        result = np.isin(ar1, ar2, invert=True)
        assert_array_equal(result, np.invert(expected))

        ar1 = np.array([(1,), (2, 3), 1], dtype=object)
        ar1 = ar1[:-1]
        ar2 = np.array([(1,), 2], dtype=object)
        expected = np.array([True, False])
        result = np.isin(ar1, ar2)
        assert_array_equal(result, expected)
        result = np.isin(ar1, ar2, invert=True)
        assert_array_equal(result, np.invert(expected))

    def test_isin_errors(self):
        """Test that isin raises expected errors."""

        # Error 1: `kind` is not one of 'sort' 'table' or None.
        ar1 = np.array([1, 2, 3, 4, 5])
        ar2 = np.array([2, 4, 6, 8, 10])
        assert_raises(ValueError, isin, ar1, ar2, kind='quicksort')

        # Error 2: `kind="table"` does not work for non-integral arrays.
        obj_ar1 = np.array([1, 'a', 3, 'b', 5], dtype=object)
        obj_ar2 = np.array([1, 'a', 3, 'b', 5], dtype=object)
        assert_raises(ValueError, isin, obj_ar1, obj_ar2, kind='table')

        for dtype in [np.int32, np.int64]:
            ar1 = np.array([-1, 2, 3, 4, 5], dtype=dtype)
            # The range of this array will overflow:
            overflow_ar2 = np.array([-1, np.iinfo(dtype).max], dtype=dtype)

            # Error 3: `kind="table"` will trigger a runtime error
            #  if there is an integer overflow expected when computing the
            #  range of ar2
            assert_raises(
                RuntimeError,
                isin, ar1, overflow_ar2, kind='table'
            )

            # Non-error: `kind=None` will *not* trigger a runtime error
            #  if there is an integer overflow, it will switch to
            #  the `sort` algorithm.
            result = np.isin(ar1, overflow_ar2, kind=None)
            assert_array_equal(result, [True] + [False] * 4)
            result = np.isin(ar1, overflow_ar2, kind='sort')
            assert_array_equal(result, [True] + [False] * 4)

    def test_union1d(self):
        a = np.array([5, 4, 7, 1, 2])
        b = np.array([2, 4, 3, 3, 2, 1, 5])

        ec = np.array([1, 2, 3, 4, 5, 7])
        c = union1d(a, b)
        assert_array_equal(c, ec)

        # Tests gh-10340, arguments to union1d should be
        # flattened if they are not already 1D
        x = np.array([[0, 1, 2], [3, 4, 5]])
        y = np.array([0, 1, 2, 3, 4])
        ez = np.array([0, 1, 2, 3, 4, 5])
        z = union1d(x, y)
        assert_array_equal(z, ez)

        assert_array_equal([], union1d([], []))

    def test_setdiff1d(self):
        a = np.array([6, 5, 4, 7, 1, 2, 7, 4])
        b = np.array([2, 4, 3, 3, 2, 1, 5])

        ec = np.array([6, 7])
        c = setdiff1d(a, b)
        assert_array_equal(c, ec)

        a = np.arange(21)
        b = np.arange(19)
        ec = np.array([19, 20])
        c = setdiff1d(a, b)
        assert_array_equal(c, ec)

        assert_array_equal([], setdiff1d([], []))
        a = np.array((), np.uint32)
        assert_equal(setdiff1d(a, []).dtype, np.uint32)

    def test_setdiff1d_unique(self):
        a = np.array([3, 2, 1])
        b = np.array([7, 5, 2])
        expected = np.array([3, 1])
        actual = setdiff1d(a, b, assume_unique=True)
        assert_equal(actual, expected)

    def test_setdiff1d_char_array(self):
        a = np.array(['a', 'b', 'c'])
        b = np.array(['a', 'b', 's'])
        assert_array_equal(setdiff1d(a, b), np.array(['c']))

    def test_manyways(self):
        a = np.array([5, 7, 1, 2, 8])
        b = np.array([9, 8, 2, 4, 3, 1, 5])

        c1 = setxor1d(a, b)
        aux1 = intersect1d(a, b)
        aux2 = union1d(a, b)
        c2 = setdiff1d(aux2, aux1)
        assert_array_equal(c1, c2)


class TestUnique:

    def check_all(self, a, b, i1, i2, c, dt):
        base_msg = 'check {0} failed for type {1}'

        msg = base_msg.format('values', dt)
        v = unique(a)
        assert_array_equal(v, b, msg)
        assert type(v) == type(b)

        msg = base_msg.format('return_index', dt)
        v, j = unique(a, True, False, False)
        assert_array_equal(v, b, msg)
        assert_array_equal(j, i1, msg)
        assert type(v) == type(b)

        msg = base_msg.format('return_inverse', dt)
        v, j = unique(a, False, True, False)
        assert_array_equal(v, b, msg)
        assert_array_equal(j, i2, msg)
        assert type(v) == type(b)

        msg = base_msg.format('return_counts', dt)
        v, j = unique(a, False, False, True)
        assert_array_equal(v, b, msg)
        assert_array_equal(j, c, msg)
        assert type(v) == type(b)

        msg = base_msg.format('return_index and return_inverse', dt)
        v, j1, j2 = unique(a, True, True, False)
        assert_array_equal(v, b, msg)
        assert_array_equal(j1, i1, msg)
        assert_array_equal(j2, i2, msg)
        assert type(v) == type(b)

        msg = base_msg.format('return_index and return_counts', dt)
        v, j1, j2 = unique(a, True, False, True)
        assert_array_equal(v, b, msg)
        assert_array_equal(j1, i1, msg)
        assert_array_equal(j2, c, msg)
        assert type(v) == type(b)

        msg = base_msg.format('return_inverse and return_counts', dt)
        v, j1, j2 = unique(a, False, True, True)
        assert_array_equal(v, b, msg)
        assert_array_equal(j1, i2, msg)
        assert_array_equal(j2, c, msg)
        assert type(v) == type(b)

        msg = base_msg.format(('return_index, return_inverse '
                                'and return_counts'), dt)
        v, j1, j2, j3 = unique(a, True, True, True)
        assert_array_equal(v, b, msg)
        assert_array_equal(j1, i1, msg)
        assert_array_equal(j2, i2, msg)
        assert_array_equal(j3, c, msg)
        assert type(v) == type(b)

    def get_types(self):
        types = []
        types.extend(np.typecodes['AllInteger'])
        types.extend(np.typecodes['AllFloat'])
        types.append('datetime64[D]')
        types.append('timedelta64[D]')
        return types

    def test_unique_1d(self):

        a = [5, 7, 1, 2, 1, 5, 7] * 10
        b = [1, 2, 5, 7]
        i1 = [2, 3, 0, 1]
        i2 = [2, 3, 0, 1, 0, 2, 3] * 10
        c = np.multiply([2, 1, 2, 2], 10)

        # test for numeric arrays
        types = self.get_types()
        for dt in types:
            aa = np.array(a, dt)
            bb = np.array(b, dt)
            self.check_all(aa, bb, i1, i2, c, dt)

        # test for object arrays
        dt = 'O'
        aa = np.empty(len(a), dt)
        aa[:] = a
        bb = np.empty(len(b), dt)
        bb[:] = b
        self.check_all(aa, bb, i1, i2, c, dt)

        # test for structured arrays
        dt = [('', 'i'), ('', 'i')]
        aa = np.array(list(zip(a, a)), dt)
        bb = np.array(list(zip(b, b)), dt)
        self.check_all(aa, bb, i1, i2, c, dt)

        # test for ticket #2799
        aa = [1. + 0.j, 1 - 1.j, 1]
        assert_array_equal(np.unique(aa), [1. - 1.j, 1. + 0.j])

        # test for ticket #4785
        a = [(1, 2), (1, 2), (2, 3)]
        unq = [1, 2, 3]
        inv = [[0, 1], [0, 1], [1, 2]]
        a1 = unique(a)
        assert_array_equal(a1, unq)
        a2, a2_inv = unique(a, return_inverse=True)
        assert_array_equal(a2, unq)
        assert_array_equal(a2_inv, inv)

        # test for chararrays with return_inverse (gh-5099)
        a = np.char.chararray(5)
        a[...] = ''
        a2, a2_inv = np.unique(a, return_inverse=True)
        assert_array_equal(a2_inv, np.zeros(5))

        # test for ticket #9137
        a = []
        a1_idx = np.unique(a, return_index=True)[1]
        a2_inv = np.unique(a, return_inverse=True)[1]
        a3_idx, a3_inv = np.unique(a, return_index=True,
                                   return_inverse=True)[1:]
        assert_equal(a1_idx.dtype, np.intp)
        assert_equal(a2_inv.dtype, np.intp)
        assert_equal(a3_idx.dtype, np.intp)
        assert_equal(a3_inv.dtype, np.intp)

        # test for ticket 2111 - float
        a = [2.0, np.nan, 1.0, np.nan]
        ua = [1.0, 2.0, np.nan]
        ua_idx = [2, 0, 1]
        ua_inv = [1, 2, 0, 2]
        ua_cnt = [1, 1, 2]
        assert_equal(np.unique(a), ua)
        assert_equal(np.unique(a, return_index=True), (ua, ua_idx))
        assert_equal(np.unique(a, return_inverse=True), (ua, ua_inv))
        assert_equal(np.unique(a, return_counts=True), (ua, ua_cnt))

        # test for ticket 2111 - complex
        a = [2.0 - 1j, np.nan, 1.0 + 1j, complex(0.0, np.nan), complex(1.0, np.nan)]
        ua = [1.0 + 1j, 2.0 - 1j, complex(0.0, np.nan)]
        ua_idx = [2, 0, 3]
        ua_inv = [1, 2, 0, 2, 2]
        ua_cnt = [1, 1, 3]
        assert_equal(np.unique(a), ua)
        assert_equal(np.unique(a, return_index=True), (ua, ua_idx))
        assert_equal(np.unique(a, return_inverse=True), (ua, ua_inv))
        assert_equal(np.unique(a, return_counts=True), (ua, ua_cnt))

        # test for ticket 2111 - datetime64
        nat = np.datetime64('nat')
        a = [np.datetime64('2020-12-26'), nat, np.datetime64('2020-12-24'), nat]
        ua = [np.datetime64('2020-12-24'), np.datetime64('2020-12-26'), nat]
        ua_idx = [2, 0, 1]
        ua_inv = [1, 2, 0, 2]
        ua_cnt = [1, 1, 2]
        assert_equal(np.unique(a), ua)
        assert_equal(np.unique(a, return_index=True), (ua, ua_idx))
        assert_equal(np.unique(a, return_inverse=True), (ua, ua_inv))
        assert_equal(np.unique(a, return_counts=True), (ua, ua_cnt))

        # test for ticket 2111 - timedelta
        nat = np.timedelta64('nat')
        a = [np.timedelta64(1, 'D'), nat, np.timedelta64(1, 'h'), nat]
        ua = [np.timedelta64(1, 'h'), np.timedelta64(1, 'D'), nat]
        ua_idx = [2, 0, 1]
        ua_inv = [1, 2, 0, 2]
        ua_cnt = [1, 1, 2]
        assert_equal(np.unique(a), ua)
        assert_equal(np.unique(a, return_index=True), (ua, ua_idx))
        assert_equal(np.unique(a, return_inverse=True), (ua, ua_inv))
        assert_equal(np.unique(a, return_counts=True), (ua, ua_cnt))

        # test for gh-19300
        all_nans = [np.nan] * 4
        ua = [np.nan]
        ua_idx = [0]
        ua_inv = [0, 0, 0, 0]
        ua_cnt = [4]
        assert_equal(np.unique(all_nans), ua)
        assert_equal(np.unique(all_nans, return_index=True), (ua, ua_idx))
        assert_equal(np.unique(all_nans, return_inverse=True), (ua, ua_inv))
        assert_equal(np.unique(all_nans, return_counts=True), (ua, ua_cnt))

    def test_unique_zero_sized(self):
        # test for zero-sized arrays
        for dt in self.get_types():
            a = np.array([], dt)
            b = np.array([], dt)
            i1 = np.array([], np.int64)
            i2 = np.array([], np.int64)
            c = np.array([], np.int64)
            self.check_all(a, b, i1, i2, c, dt)

    def test_unique_subclass(self):
        class Subclass(np.ndarray):
            pass

        i1 = [2, 3, 0, 1]
        i2 = [2, 3, 0, 1, 0, 2, 3] * 10
        c = np.multiply([2, 1, 2, 2], 10)

        # test for numeric arrays
        types = self.get_types()
        for dt in types:
            a = np.array([5, 7, 1, 2, 1, 5, 7] * 10, dtype=dt)
            b = np.array([1, 2, 5, 7], dtype=dt)
            aa = Subclass(a.shape, dtype=dt, buffer=a)
            bb = Subclass(b.shape, dtype=dt, buffer=b)
            self.check_all(aa, bb, i1, i2, c, dt)

    @pytest.mark.parametrize("arg", ["return_index", "return_inverse", "return_counts"])
    def test_unsupported_hash_based(self, arg):
        """These currently never use the hash-based solution.  However,
        it seems easier to just allow it.

        When the hash-based solution is added, this test should fail and be
        replaced with something more comprehensive.
        """
        a = np.array([1, 5, 2, 3, 4, 8, 199, 1, 3, 5])

        res_not_sorted = np.unique([1, 1], sorted=False, **{arg: True})
        res_sorted = np.unique([1, 1], sorted=True, **{arg: True})
        # The following should fail without first sorting `res_not_sorted`.
        for arr, expected in zip(res_not_sorted, res_sorted):
            assert_array_equal(arr, expected)

    def test_unique_axis_errors(self):
        assert_raises(TypeError, self._run_axis_tests, object)
        assert_raises(TypeError, self._run_axis_tests,
                      [('a', int), ('b', object)])

        assert_raises(AxisError, unique, np.arange(10), axis=2)
        assert_raises(AxisError, unique, np.arange(10), axis=-2)

    def test_unique_axis_list(self):
        msg = "Unique failed on list of lists"
        inp = [[0, 1, 0], [0, 1, 0]]
        inp_arr = np.asarray(inp)
        assert_array_equal(unique(inp, axis=0), unique(inp_arr, axis=0), msg)
        assert_array_equal(unique(inp, axis=1), unique(inp_arr, axis=1), msg)

    def test_unique_axis(self):
        types = []
        types.extend(np.typecodes['AllInteger'])
        types.extend(np.typecodes['AllFloat'])
        types.append('datetime64[D]')
        types.append('timedelta64[D]')
        types.append([('a', int), ('b', int)])
        types.append([('a', int), ('b', float)])

        for dtype in types:
            self._run_axis_tests(dtype)

        msg = 'Non-bitwise-equal booleans test failed'
        data = np.arange(10, dtype=np.uint8).reshape(-1, 2).view(bool)
        result = np.array([[False, True], [True, True]], dtype=bool)
        assert_array_equal(unique(data, axis=0), result, msg)

        msg = 'Negative zero equality test failed'
        data = np.array([[-0.0, 0.0], [0.0, -0.0], [-0.0, 0.0], [0.0, -0.0]])
        result = np.array([[-0.0, 0.0]])
        assert_array_equal(unique(data, axis=0), result, msg)

    @pytest.mark.parametrize("axis", [0, -1])
    def test_unique_1d_with_axis(self, axis):
        x = np.array([4, 3, 2, 3, 2, 1, 2, 2])
        uniq = unique(x, axis=axis)
        assert_array_equal(uniq, [1, 2, 3, 4])

    @pytest.mark.parametrize("axis", [None, 0, -1])
    def test_unique_inverse_with_axis(self, axis):
        x = np.array([[4, 4, 3], [2, 2, 1], [2, 2, 1], [4, 4, 3]])
        uniq, inv = unique(x, return_inverse=True, axis=axis)
        assert_equal(inv.ndim, x.ndim if axis is None else 1)
        assert_array_equal(x, np.take(uniq, inv, axis=axis))

    def test_unique_axis_zeros(self):
        # issue 15559
        single_zero = np.empty(shape=(2, 0), dtype=np.int8)
        uniq, idx, inv, cnt = unique(single_zero, axis=0, return_index=True,
                                     return_inverse=True, return_counts=True)

        # there's 1 element of shape (0,) along axis 0
        assert_equal(uniq.dtype, single_zero.dtype)
        assert_array_equal(uniq, np.empty(shape=(1, 0)))
        assert_array_equal(idx, np.array([0]))
        assert_array_equal(inv, np.array([0, 0]))
        assert_array_equal(cnt, np.array([2]))

        # there's 0 elements of shape (2,) along axis 1
        uniq, idx, inv, cnt = unique(single_zero, axis=1, return_index=True,
                                     return_inverse=True, return_counts=True)

        assert_equal(uniq.dtype, single_zero.dtype)
        assert_array_equal(uniq, np.empty(shape=(2, 0)))
        assert_array_equal(idx, np.array([]))
        assert_array_equal(inv, np.array([]))
        assert_array_equal(cnt, np.array([]))

        # test a "complicated" shape
        shape = (0, 2, 0, 3, 0, 4, 0)
        multiple_zeros = np.empty(shape=shape)
        for axis in range(len(shape)):
            expected_shape = list(shape)
            if shape[axis] == 0:
                expected_shape[axis] = 0
            else:
                expected_shape[axis] = 1

            assert_array_equal(unique(multiple_zeros, axis=axis),
                               np.empty(shape=expected_shape))

    def test_unique_masked(self):
        # issue 8664
        x = np.array([64, 0, 1, 2, 3, 63, 63, 0, 0, 0, 1, 2, 0, 63, 0],
                     dtype='uint8')
        y = np.ma.masked_equal(x, 0)

        v = np.unique(y)
        v2, i, c = np.unique(y, return_index=True, return_counts=True)

        msg = 'Unique returned different results when asked for index'
        assert_array_equal(v.data, v2.data, msg)
        assert_array_equal(v.mask, v2.mask, msg)

    def test_unique_sort_order_with_axis(self):
        # These tests fail if sorting along axis is done by treating subarrays
        # as unsigned byte strings.  See gh-10495.
        fmt = "sort order incorrect for integer type '%s'"
        for dt in 'bhilq':
            a = np.array([[-1], [0]], dt)
            b = np.unique(a, axis=0)
            assert_array_equal(a, b, fmt % dt)

    def _run_axis_tests(self, dtype):
        data = np.array([[0, 1, 0, 0],
                         [1, 0, 0, 0],
                         [0, 1, 0, 0],
                         [1, 0, 0, 0]]).astype(dtype)

        msg = 'Unique with 1d array and axis=0 failed'
        result = np.array([0, 1])
        assert_array_equal(unique(data), result.astype(dtype), msg)

        msg = 'Unique with 2d array and axis=0 failed'
        result = np.array([[0, 1, 0, 0], [1, 0, 0, 0]])
        assert_array_equal(unique(data, axis=0), result.astype(dtype), msg)

        msg = 'Unique with 2d array and axis=1 failed'
        result = np.array([[0, 0, 1], [0, 1, 0], [0, 0, 1], [0, 1, 0]])
        assert_array_equal(unique(data, axis=1), result.astype(dtype), msg)

        msg = 'Unique with 3d array and axis=2 failed'
        data3d = np.array([[[1, 1],
                            [1, 0]],
                           [[0, 1],
                            [0, 0]]]).astype(dtype)
        result = np.take(data3d, [1, 0], axis=2)
        assert_array_equal(unique(data3d, axis=2), result, msg)

        uniq, idx, inv, cnt = unique(data, axis=0, return_index=True,
                                     return_inverse=True, return_counts=True)
        msg = "Unique's return_index=True failed with axis=0"
        assert_array_equal(data[idx], uniq, msg)
        msg = "Unique's return_inverse=True failed with axis=0"
        assert_array_equal(np.take(uniq, inv, axis=0), data)
        msg = "Unique's return_counts=True failed with axis=0"
        assert_array_equal(cnt, np.array([2, 2]), msg)

        uniq, idx, inv, cnt = unique(data, axis=1, return_index=True,
                                     return_inverse=True, return_counts=True)
        msg = "Unique's return_index=True failed with axis=1"
        assert_array_equal(data[:, idx], uniq)
        msg = "Unique's return_inverse=True failed with axis=1"
        assert_array_equal(np.take(uniq, inv, axis=1), data)
        msg = "Unique's return_counts=True failed with axis=1"
        assert_array_equal(cnt, np.array([2, 1, 1]), msg)

    def test_unique_nanequals(self):
        # issue 20326
        a = np.array([1, 1, np.nan, np.nan, np.nan])
        unq = np.unique(a)
        not_unq = np.unique(a, equal_nan=False)
        assert_array_equal(unq, np.array([1, np.nan]))
        assert_array_equal(not_unq, np.array([1, np.nan, np.nan, np.nan]))

    def test_unique_array_api_functions(self):
        arr = np.array([np.nan, 1, 4, 1, 3, 4, np.nan, 5, 1])

        for res_unique_array_api, res_unique in [
            (
                np.unique_values(arr),
                np.unique(arr, equal_nan=False)
            ),
            (
                np.unique_counts(arr),
                np.unique(arr, return_counts=True, equal_nan=False)
            ),
            (
                np.unique_inverse(arr),
                np.unique(arr, return_inverse=True, equal_nan=False)
            ),
            (
                np.unique_all(arr),
                np.unique(
                    arr,
                    return_index=True,
                    return_inverse=True,
                    return_counts=True,
                    equal_nan=False
                )
            )
        ]:
            assert len(res_unique_array_api) == len(res_unique)
            for actual, expected in zip(res_unique_array_api, res_unique):
                assert_array_equal(actual, expected)

    def test_unique_inverse_shape(self):
        # Regression test for https://github.com/numpy/numpy/issues/25552
        arr = np.array([[1, 2, 3], [2, 3, 1]])
        expected_values, expected_inverse = np.unique(arr, return_inverse=True)
        expected_inverse = expected_inverse.reshape(arr.shape)
        for func in np.unique_inverse, np.unique_all:
            result = func(arr)
            assert_array_equal(expected_values, result.values)
            assert_array_equal(expected_inverse, result.inverse_indices)
            assert_array_equal(arr, result.values[result.inverse_indices])

    @pytest.mark.parametrize(
        'data',
        [[[1, 1, 1],
          [1, 1, 1]],
         [1, 3, 2],
         1],
    )
    @pytest.mark.parametrize('transpose', [False, True])
    @pytest.mark.parametrize('dtype', [np.int32, np.float64])
    def test_unique_with_matrix(self, data, transpose, dtype):
        mat = np.matrix(data).astype(dtype)
        if transpose:
            mat = mat.T
        u = np.unique(mat)
        expected = np.unique(np.asarray(mat))
        assert_array_equal(u, expected, strict=True)

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\tests\test_arraysetops.py ===
"""Test functions for 1D array set operations.

"""
import pytest

import numpy as np
from numpy import ediff1d, intersect1d, isin, setdiff1d, setxor1d, union1d, unique
from numpy.exceptions import AxisError
from numpy.testing import (
    assert_array_equal,
    assert_equal,
    assert_raises,
    assert_raises_regex,
)


class TestSetOps:

    def test_intersect1d(self):
        # unique inputs
        a = np.array([5, 7, 1, 2])
        b = np.array([2, 4, 3, 1, 5])

        ec = np.array([1, 2, 5])
        c = intersect1d(a, b, assume_unique=True)
        assert_array_equal(c, ec)

        # non-unique inputs
        a = np.array([5, 5, 7, 1, 2])
        b = np.array([2, 1, 4, 3, 3, 1, 5])

        ed = np.array([1, 2, 5])
        c = intersect1d(a, b)
        assert_array_equal(c, ed)
        assert_array_equal([], intersect1d([], []))

    def test_intersect1d_array_like(self):
        # See gh-11772
        class Test:
            def __array__(self, dtype=None, copy=None):
                return np.arange(3)

        a = Test()
        res = intersect1d(a, a)
        assert_array_equal(res, a)
        res = intersect1d([1, 2, 3], [1, 2, 3])
        assert_array_equal(res, [1, 2, 3])

    def test_intersect1d_indices(self):
        # unique inputs
        a = np.array([1, 2, 3, 4])
        b = np.array([2, 1, 4, 6])
        c, i1, i2 = intersect1d(a, b, assume_unique=True, return_indices=True)
        ee = np.array([1, 2, 4])
        assert_array_equal(c, ee)
        assert_array_equal(a[i1], ee)
        assert_array_equal(b[i2], ee)

        # non-unique inputs
        a = np.array([1, 2, 2, 3, 4, 3, 2])
        b = np.array([1, 8, 4, 2, 2, 3, 2, 3])
        c, i1, i2 = intersect1d(a, b, return_indices=True)
        ef = np.array([1, 2, 3, 4])
        assert_array_equal(c, ef)
        assert_array_equal(a[i1], ef)
        assert_array_equal(b[i2], ef)

        # non1d, unique inputs
        a = np.array([[2, 4, 5, 6], [7, 8, 1, 15]])
        b = np.array([[3, 2, 7, 6], [10, 12, 8, 9]])
        c, i1, i2 = intersect1d(a, b, assume_unique=True, return_indices=True)
        ui1 = np.unravel_index(i1, a.shape)
        ui2 = np.unravel_index(i2, b.shape)
        ea = np.array([2, 6, 7, 8])
        assert_array_equal(ea, a[ui1])
        assert_array_equal(ea, b[ui2])

        # non1d, not assumed to be uniqueinputs
        a = np.array([[2, 4, 5, 6, 6], [4, 7, 8, 7, 2]])
        b = np.array([[3, 2, 7, 7], [10, 12, 8, 7]])
        c, i1, i2 = intersect1d(a, b, return_indices=True)
        ui1 = np.unravel_index(i1, a.shape)
        ui2 = np.unravel_index(i2, b.shape)
        ea = np.array([2, 7, 8])
        assert_array_equal(ea, a[ui1])
        assert_array_equal(ea, b[ui2])

    def test_setxor1d(self):
        a = np.array([5, 7, 1, 2])
        b = np.array([2, 4, 3, 1, 5])

        ec = np.array([3, 4, 7])
        c = setxor1d(a, b)
        assert_array_equal(c, ec)

        a = np.array([1, 2, 3])
        b = np.array([6, 5, 4])

        ec = np.array([1, 2, 3, 4, 5, 6])
        c = setxor1d(a, b)
        assert_array_equal(c, ec)

        a = np.array([1, 8, 2, 3])
        b = np.array([6, 5, 4, 8])

        ec = np.array([1, 2, 3, 4, 5, 6])
        c = setxor1d(a, b)
        assert_array_equal(c, ec)

        assert_array_equal([], setxor1d([], []))

    def test_setxor1d_unique(self):
        a = np.array([1, 8, 2, 3])
        b = np.array([6, 5, 4, 8])

        ec = np.array([1, 2, 3, 4, 5, 6])
        c = setxor1d(a, b, assume_unique=True)
        assert_array_equal(c, ec)

        a = np.array([[1], [8], [2], [3]])
        b = np.array([[6, 5], [4, 8]])

        ec = np.array([1, 2, 3, 4, 5, 6])
        c = setxor1d(a, b, assume_unique=True)
        assert_array_equal(c, ec)

    def test_ediff1d(self):
        zero_elem = np.array([])
        one_elem = np.array([1])
        two_elem = np.array([1, 2])

        assert_array_equal([], ediff1d(zero_elem))
        assert_array_equal([0], ediff1d(zero_elem, to_begin=0))
        assert_array_equal([0], ediff1d(zero_elem, to_end=0))
        assert_array_equal([-1, 0], ediff1d(zero_elem, to_begin=-1, to_end=0))
        assert_array_equal([], ediff1d(one_elem))
        assert_array_equal([1], ediff1d(two_elem))
        assert_array_equal([7, 1, 9], ediff1d(two_elem, to_begin=7, to_end=9))
        assert_array_equal([5, 6, 1, 7, 8],
                           ediff1d(two_elem, to_begin=[5, 6], to_end=[7, 8]))
        assert_array_equal([1, 9], ediff1d(two_elem, to_end=9))
        assert_array_equal([1, 7, 8], ediff1d(two_elem, to_end=[7, 8]))
        assert_array_equal([7, 1], ediff1d(two_elem, to_begin=7))
        assert_array_equal([5, 6, 1], ediff1d(two_elem, to_begin=[5, 6]))

    @pytest.mark.parametrize("ary, prepend, append, expected", [
        # should fail because trying to cast
        # np.nan standard floating point value
        # into an integer array:
        (np.array([1, 2, 3], dtype=np.int64),
         None,
         np.nan,
         'to_end'),
        # should fail because attempting
        # to downcast to int type:
        (np.array([1, 2, 3], dtype=np.int64),
         np.array([5, 7, 2], dtype=np.float32),
         None,
         'to_begin'),
        # should fail because attempting to cast
        # two special floating point values
        # to integers (on both sides of ary),
        # `to_begin` is in the error message as the impl checks this first:
        (np.array([1., 3., 9.], dtype=np.int8),
         np.nan,
         np.nan,
         'to_begin'),
         ])
    def test_ediff1d_forbidden_type_casts(self, ary, prepend, append, expected):
        # verify resolution of gh-11490

        # specifically, raise an appropriate
        # Exception when attempting to append or
        # prepend with an incompatible type
        msg = f'dtype of `{expected}` must be compatible'
        with assert_raises_regex(TypeError, msg):
            ediff1d(ary=ary,
                    to_end=append,
                    to_begin=prepend)

    @pytest.mark.parametrize(
        "ary,prepend,append,expected",
        [
         (np.array([1, 2, 3], dtype=np.int16),
          2**16,  # will be cast to int16 under same kind rule.
          2**16 + 4,
          np.array([0, 1, 1, 4], dtype=np.int16)),
         (np.array([1, 2, 3], dtype=np.float32),
          np.array([5], dtype=np.float64),
          None,
          np.array([5, 1, 1], dtype=np.float32)),
         (np.array([1, 2, 3], dtype=np.int32),
          0,
          0,
          np.array([0, 1, 1, 0], dtype=np.int32)),
         (np.array([1, 2, 3], dtype=np.int64),
          3,
          -9,
          np.array([3, 1, 1, -9], dtype=np.int64)),
        ]
    )
    def test_ediff1d_scalar_handling(self,
                                     ary,
                                     prepend,
                                     append,
                                     expected):
        # maintain backwards-compatibility
        # of scalar prepend / append behavior
        # in ediff1d following fix for gh-11490
        actual = np.ediff1d(ary=ary,
                            to_end=append,
                            to_begin=prepend)
        assert_equal(actual, expected)
        assert actual.dtype == expected.dtype

    @pytest.mark.parametrize("kind", [None, "sort", "table"])
    def test_isin(self, kind):
        def _isin_slow(a, b):
            b = np.asarray(b).flatten().tolist()
            return a in b
        isin_slow = np.vectorize(_isin_slow, otypes=[bool], excluded={1})

        def assert_isin_equal(a, b):
            x = isin(a, b, kind=kind)
            y = isin_slow(a, b)
            assert_array_equal(x, y)

        # multidimensional arrays in both arguments
        a = np.arange(24).reshape([2, 3, 4])
        b = np.array([[10, 20, 30], [0, 1, 3], [11, 22, 33]])
        assert_isin_equal(a, b)

        # array-likes as both arguments
        c = [(9, 8), (7, 6)]
        d = (9, 7)
        assert_isin_equal(c, d)

        # zero-d array:
        f = np.array(3)
        assert_isin_equal(f, b)
        assert_isin_equal(a, f)
        assert_isin_equal(f, f)

        # scalar:
        assert_isin_equal(5, b)
        assert_isin_equal(a, 6)
        assert_isin_equal(5, 6)

        # empty array-like:
        if kind != "table":
            # An empty list will become float64,
            # which is invalid for kind="table"
            x = []
            assert_isin_equal(x, b)
            assert_isin_equal(a, x)
            assert_isin_equal(x, x)

        # empty array with various types:
        for dtype in [bool, np.int64, np.float64]:
            if kind == "table" and dtype == np.float64:
                continue

            if dtype in {np.int64, np.float64}:
                ar = np.array([10, 20, 30], dtype=dtype)
            elif dtype in {bool}:
                ar = np.array([True, False, False])

            empty_array = np.array([], dtype=dtype)

            assert_isin_equal(empty_array, ar)
            assert_isin_equal(ar, empty_array)
            assert_isin_equal(empty_array, empty_array)

    @pytest.mark.parametrize("kind", [None, "sort", "table"])
    def test_isin_additional(self, kind):
        # we use two different sizes for the b array here to test the
        # two different paths in isin().
        for mult in (1, 10):
            # One check without np.array to make sure lists are handled correct
            a = [5, 7, 1, 2]
            b = [2, 4, 3, 1, 5] * mult
            ec = np.array([True, False, True, True])
            c = isin(a, b, assume_unique=True, kind=kind)
            assert_array_equal(c, ec)

            a[0] = 8
            ec = np.array([False, False, True, True])
            c = isin(a, b, assume_unique=True, kind=kind)
            assert_array_equal(c, ec)

            a[0], a[3] = 4, 8
            ec = np.array([True, False, True, False])
            c = isin(a, b, assume_unique=True, kind=kind)
            assert_array_equal(c, ec)

            a = np.array([5, 4, 5, 3, 4, 4, 3, 4, 3, 5, 2, 1, 5, 5])
            b = [2, 3, 4] * mult
            ec = [False, True, False, True, True, True, True, True, True,
                  False, True, False, False, False]
            c = isin(a, b, kind=kind)
            assert_array_equal(c, ec)

            b = b + [5, 5, 4] * mult
            ec = [True, True, True, True, True, True, True, True, True, True,
                  True, False, True, True]
            c = isin(a, b, kind=kind)
            assert_array_equal(c, ec)

            a = np.array([5, 7, 1, 2])
            b = np.array([2, 4, 3, 1, 5] * mult)
            ec = np.array([True, False, True, True])
            c = isin(a, b, kind=kind)
            assert_array_equal(c, ec)

            a = np.array([5, 7, 1, 1, 2])
            b = np.array([2, 4, 3, 3, 1, 5] * mult)
            ec = np.array([True, False, True, True, True])
            c = isin(a, b, kind=kind)
            assert_array_equal(c, ec)

            a = np.array([5, 5])
            b = np.array([2, 2] * mult)
            ec = np.array([False, False])
            c = isin(a, b, kind=kind)
            assert_array_equal(c, ec)

        a = np.array([5])
        b = np.array([2])
        ec = np.array([False])
        c = isin(a, b, kind=kind)
        assert_array_equal(c, ec)

        if kind in {None, "sort"}:
            assert_array_equal(isin([], [], kind=kind), [])

    def test_isin_char_array(self):
        a = np.array(['a', 'b', 'c', 'd', 'e', 'c', 'e', 'b'])
        b = np.array(['a', 'c'])

        ec = np.array([True, False, True, False, False, True, False, False])
        c = isin(a, b)

        assert_array_equal(c, ec)

    @pytest.mark.parametrize("kind", [None, "sort", "table"])
    def test_isin_invert(self, kind):
        "Test isin's invert parameter"
        # We use two different sizes for the b array here to test the
        # two different paths in isin().
        for mult in (1, 10):
            a = np.array([5, 4, 5, 3, 4, 4, 3, 4, 3, 5, 2, 1, 5, 5])
            b = [2, 3, 4] * mult
            assert_array_equal(np.invert(isin(a, b, kind=kind)),
                               isin(a, b, invert=True, kind=kind))

        # float:
        if kind in {None, "sort"}:
            for mult in (1, 10):
                a = np.array([5, 4, 5, 3, 4, 4, 3, 4, 3, 5, 2, 1, 5, 5],
                            dtype=np.float32)
                b = [2, 3, 4] * mult
                b = np.array(b, dtype=np.float32)
                assert_array_equal(np.invert(isin(a, b, kind=kind)),
                                   isin(a, b, invert=True, kind=kind))

    def test_isin_hit_alternate_algorithm(self):
        """Hit the standard isin code with integers"""
        # Need extreme range to hit standard code
        # This hits it without the use of kind='table'
        a = np.array([5, 4, 5, 3, 4, 4, 1e9], dtype=np.int64)
        b = np.array([2, 3, 4, 1e9], dtype=np.int64)
        expected = np.array([0, 1, 0, 1, 1, 1, 1], dtype=bool)
        assert_array_equal(expected, isin(a, b))
        assert_array_equal(np.invert(expected), isin(a, b, invert=True))

        a = np.array([5, 7, 1, 2], dtype=np.int64)
        b = np.array([2, 4, 3, 1, 5, 1e9], dtype=np.int64)
        ec = np.array([True, False, True, True])
        c = isin(a, b, assume_unique=True)
        assert_array_equal(c, ec)

    @pytest.mark.parametrize("kind", [None, "sort", "table"])
    def test_isin_boolean(self, kind):
        """Test that isin works for boolean input"""
        a = np.array([True, False])
        b = np.array([False, False, False])
        expected = np.array([False, True])
        assert_array_equal(expected,
                           isin(a, b, kind=kind))
        assert_array_equal(np.invert(expected),
                           isin(a, b, invert=True, kind=kind))

    @pytest.mark.parametrize("kind", [None, "sort"])
    def test_isin_timedelta(self, kind):
        """Test that isin works for timedelta input"""
        rstate = np.random.RandomState(0)
        a = rstate.randint(0, 100, size=10)
        b = rstate.randint(0, 100, size=10)
        truth = isin(a, b)
        a_timedelta = a.astype("timedelta64[s]")
        b_timedelta = b.astype("timedelta64[s]")
        assert_array_equal(truth, isin(a_timedelta, b_timedelta, kind=kind))

    def test_isin_table_timedelta_fails(self):
        a = np.array([0, 1, 2], dtype="timedelta64[s]")
        b = a
        # Make sure it raises a value error:
        with pytest.raises(ValueError):
            isin(a, b, kind="table")

    @pytest.mark.parametrize(
        "dtype1,dtype2",
        [
            (np.int8, np.int16),
            (np.int16, np.int8),
            (np.uint8, np.uint16),
            (np.uint16, np.uint8),
            (np.uint8, np.int16),
            (np.int16, np.uint8),
            (np.uint64, np.int64),
        ]
    )
    @pytest.mark.parametrize("kind", [None, "sort", "table"])
    def test_isin_mixed_dtype(self, dtype1, dtype2, kind):
        """Test that isin works as expected for mixed dtype input."""
        is_dtype2_signed = np.issubdtype(dtype2, np.signedinteger)
        ar1 = np.array([0, 0, 1, 1], dtype=dtype1)

        if is_dtype2_signed:
            ar2 = np.array([-128, 0, 127], dtype=dtype2)
        else:
            ar2 = np.array([127, 0, 255], dtype=dtype2)

        expected = np.array([True, True, False, False])

        expect_failure = kind == "table" and (
            dtype1 == np.int16 and dtype2 == np.int8)

        if expect_failure:
            with pytest.raises(RuntimeError, match="exceed the maximum"):
                isin(ar1, ar2, kind=kind)
        else:
            assert_array_equal(isin(ar1, ar2, kind=kind), expected)

    @pytest.mark.parametrize("data", [
        np.array([2**63, 2**63 + 1], dtype=np.uint64),
        np.array([-2**62, -2**62 - 1], dtype=np.int64),
    ])
    @pytest.mark.parametrize("kind", [None, "sort", "table"])
    def test_isin_mixed_huge_vals(self, kind, data):
        """Test values outside intp range (negative ones if 32bit system)"""
        query = data[1]
        res = np.isin(data, query, kind=kind)
        assert_array_equal(res, [False, True])
        # Also check that nothing weird happens for values can't possibly
        # in range.
        data = data.astype(np.int32)  # clearly different values
        res = np.isin(data, query, kind=kind)
        assert_array_equal(res, [False, False])

    @pytest.mark.parametrize("kind", [None, "sort", "table"])
    def test_isin_mixed_boolean(self, kind):
        """Test that isin works as expected for bool/int input."""
        for dtype in np.typecodes["AllInteger"]:
            a = np.array([True, False, False], dtype=bool)
            b = np.array([0, 0, 0, 0], dtype=dtype)
            expected = np.array([False, True, True], dtype=bool)
            assert_array_equal(isin(a, b, kind=kind), expected)

            a, b = b, a
            expected = np.array([True, True, True, True], dtype=bool)
            assert_array_equal(isin(a, b, kind=kind), expected)

    def test_isin_first_array_is_object(self):
        ar1 = [None]
        ar2 = np.array([1] * 10)
        expected = np.array([False])
        result = np.isin(ar1, ar2)
        assert_array_equal(result, expected)

    def test_isin_second_array_is_object(self):
        ar1 = 1
        ar2 = np.array([None] * 10)
        expected = np.array([False])
        result = np.isin(ar1, ar2)
        assert_array_equal(result, expected)

    def test_isin_both_arrays_are_object(self):
        ar1 = [None]
        ar2 = np.array([None] * 10)
        expected = np.array([True])
        result = np.isin(ar1, ar2)
        assert_array_equal(result, expected)

    def test_isin_both_arrays_have_structured_dtype(self):
        # Test arrays of a structured data type containing an integer field
        # and a field of dtype `object` allowing for arbitrary Python objects
        dt = np.dtype([('field1', int), ('field2', object)])
        ar1 = np.array([(1, None)], dtype=dt)
        ar2 = np.array([(1, None)] * 10, dtype=dt)
        expected = np.array([True])
        result = np.isin(ar1, ar2)
        assert_array_equal(result, expected)

    def test_isin_with_arrays_containing_tuples(self):
        ar1 = np.array([(1,), 2], dtype=object)
        ar2 = np.array([(1,), 2], dtype=object)
        expected = np.array([True, True])
        result = np.isin(ar1, ar2)
        assert_array_equal(result, expected)
        result = np.isin(ar1, ar2, invert=True)
        assert_array_equal(result, np.invert(expected))

        # An integer is added at the end of the array to make sure
        # that the array builder will create the array with tuples
        # and after it's created the integer is removed.
        # There's a bug in the array constructor that doesn't handle
        # tuples properly and adding the integer fixes that.
        ar1 = np.array([(1,), (2, 1), 1], dtype=object)
        ar1 = ar1[:-1]
        ar2 = np.array([(1,), (2, 1), 1], dtype=object)
        ar2 = ar2[:-1]
        expected = np.array([True, True])
        result = np.isin(ar1, ar2)
        assert_array_equal(result, expected)
        result = np.isin(ar1, ar2, invert=True)
        assert_array_equal(result, np.invert(expected))

        ar1 = np.array([(1,), (2, 3), 1], dtype=object)
        ar1 = ar1[:-1]
        ar2 = np.array([(1,), 2], dtype=object)
        expected = np.array([True, False])
        result = np.isin(ar1, ar2)
        assert_array_equal(result, expected)
        result = np.isin(ar1, ar2, invert=True)
        assert_array_equal(result, np.invert(expected))

    def test_isin_errors(self):
        """Test that isin raises expected errors."""

        # Error 1: `kind` is not one of 'sort' 'table' or None.
        ar1 = np.array([1, 2, 3, 4, 5])
        ar2 = np.array([2, 4, 6, 8, 10])
        assert_raises(ValueError, isin, ar1, ar2, kind='quicksort')

        # Error 2: `kind="table"` does not work for non-integral arrays.
        obj_ar1 = np.array([1, 'a', 3, 'b', 5], dtype=object)
        obj_ar2 = np.array([1, 'a', 3, 'b', 5], dtype=object)
        assert_raises(ValueError, isin, obj_ar1, obj_ar2, kind='table')

        for dtype in [np.int32, np.int64]:
            ar1 = np.array([-1, 2, 3, 4, 5], dtype=dtype)
            # The range of this array will overflow:
            overflow_ar2 = np.array([-1, np.iinfo(dtype).max], dtype=dtype)

            # Error 3: `kind="table"` will trigger a runtime error
            #  if there is an integer overflow expected when computing the
            #  range of ar2
            assert_raises(
                RuntimeError,
                isin, ar1, overflow_ar2, kind='table'
            )

            # Non-error: `kind=None` will *not* trigger a runtime error
            #  if there is an integer overflow, it will switch to
            #  the `sort` algorithm.
            result = np.isin(ar1, overflow_ar2, kind=None)
            assert_array_equal(result, [True] + [False] * 4)
            result = np.isin(ar1, overflow_ar2, kind='sort')
            assert_array_equal(result, [True] + [False] * 4)

    def test_union1d(self):
        a = np.array([5, 4, 7, 1, 2])
        b = np.array([2, 4, 3, 3, 2, 1, 5])

        ec = np.array([1, 2, 3, 4, 5, 7])
        c = union1d(a, b)
        assert_array_equal(c, ec)

        # Tests gh-10340, arguments to union1d should be
        # flattened if they are not already 1D
        x = np.array([[0, 1, 2], [3, 4, 5]])
        y = np.array([0, 1, 2, 3, 4])
        ez = np.array([0, 1, 2, 3, 4, 5])
        z = union1d(x, y)
        assert_array_equal(z, ez)

        assert_array_equal([], union1d([], []))

    def test_setdiff1d(self):
        a = np.array([6, 5, 4, 7, 1, 2, 7, 4])
        b = np.array([2, 4, 3, 3, 2, 1, 5])

        ec = np.array([6, 7])
        c = setdiff1d(a, b)
        assert_array_equal(c, ec)

        a = np.arange(21)
        b = np.arange(19)
        ec = np.array([19, 20])
        c = setdiff1d(a, b)
        assert_array_equal(c, ec)

        assert_array_equal([], setdiff1d([], []))
        a = np.array((), np.uint32)
        assert_equal(setdiff1d(a, []).dtype, np.uint32)

    def test_setdiff1d_unique(self):
        a = np.array([3, 2, 1])
        b = np.array([7, 5, 2])
        expected = np.array([3, 1])
        actual = setdiff1d(a, b, assume_unique=True)
        assert_equal(actual, expected)

    def test_setdiff1d_char_array(self):
        a = np.array(['a', 'b', 'c'])
        b = np.array(['a', 'b', 's'])
        assert_array_equal(setdiff1d(a, b), np.array(['c']))

    def test_manyways(self):
        a = np.array([5, 7, 1, 2, 8])
        b = np.array([9, 8, 2, 4, 3, 1, 5])

        c1 = setxor1d(a, b)
        aux1 = intersect1d(a, b)
        aux2 = union1d(a, b)
        c2 = setdiff1d(aux2, aux1)
        assert_array_equal(c1, c2)


class TestUnique:

    def check_all(self, a, b, i1, i2, c, dt):
        base_msg = 'check {0} failed for type {1}'

        msg = base_msg.format('values', dt)
        v = unique(a)
        assert_array_equal(v, b, msg)
        assert type(v) == type(b)

        msg = base_msg.format('return_index', dt)
        v, j = unique(a, True, False, False)
        assert_array_equal(v, b, msg)
        assert_array_equal(j, i1, msg)
        assert type(v) == type(b)

        msg = base_msg.format('return_inverse', dt)
        v, j = unique(a, False, True, False)
        assert_array_equal(v, b, msg)
        assert_array_equal(j, i2, msg)
        assert type(v) == type(b)

        msg = base_msg.format('return_counts', dt)
        v, j = unique(a, False, False, True)
        assert_array_equal(v, b, msg)
        assert_array_equal(j, c, msg)
        assert type(v) == type(b)

        msg = base_msg.format('return_index and return_inverse', dt)
        v, j1, j2 = unique(a, True, True, False)
        assert_array_equal(v, b, msg)
        assert_array_equal(j1, i1, msg)
        assert_array_equal(j2, i2, msg)
        assert type(v) == type(b)

        msg = base_msg.format('return_index and return_counts', dt)
        v, j1, j2 = unique(a, True, False, True)
        assert_array_equal(v, b, msg)
        assert_array_equal(j1, i1, msg)
        assert_array_equal(j2, c, msg)
        assert type(v) == type(b)

        msg = base_msg.format('return_inverse and return_counts', dt)
        v, j1, j2 = unique(a, False, True, True)
        assert_array_equal(v, b, msg)
        assert_array_equal(j1, i2, msg)
        assert_array_equal(j2, c, msg)
        assert type(v) == type(b)

        msg = base_msg.format(('return_index, return_inverse '
                                'and return_counts'), dt)
        v, j1, j2, j3 = unique(a, True, True, True)
        assert_array_equal(v, b, msg)
        assert_array_equal(j1, i1, msg)
        assert_array_equal(j2, i2, msg)
        assert_array_equal(j3, c, msg)
        assert type(v) == type(b)

    def get_types(self):
        types = []
        types.extend(np.typecodes['AllInteger'])
        types.extend(np.typecodes['AllFloat'])
        types.append('datetime64[D]')
        types.append('timedelta64[D]')
        return types

    def test_unique_1d(self):

        a = [5, 7, 1, 2, 1, 5, 7] * 10
        b = [1, 2, 5, 7]
        i1 = [2, 3, 0, 1]
        i2 = [2, 3, 0, 1, 0, 2, 3] * 10
        c = np.multiply([2, 1, 2, 2], 10)

        # test for numeric arrays
        types = self.get_types()
        for dt in types:
            aa = np.array(a, dt)
            bb = np.array(b, dt)
            self.check_all(aa, bb, i1, i2, c, dt)

        # test for object arrays
        dt = 'O'
        aa = np.empty(len(a), dt)
        aa[:] = a
        bb = np.empty(len(b), dt)
        bb[:] = b
        self.check_all(aa, bb, i1, i2, c, dt)

        # test for structured arrays
        dt = [('', 'i'), ('', 'i')]
        aa = np.array(list(zip(a, a)), dt)
        bb = np.array(list(zip(b, b)), dt)
        self.check_all(aa, bb, i1, i2, c, dt)

        # test for ticket #2799
        aa = [1. + 0.j, 1 - 1.j, 1]
        assert_array_equal(np.unique(aa), [1. - 1.j, 1. + 0.j])

        # test for ticket #4785
        a = [(1, 2), (1, 2), (2, 3)]
        unq = [1, 2, 3]
        inv = [[0, 1], [0, 1], [1, 2]]
        a1 = unique(a)
        assert_array_equal(a1, unq)
        a2, a2_inv = unique(a, return_inverse=True)
        assert_array_equal(a2, unq)
        assert_array_equal(a2_inv, inv)

        # test for chararrays with return_inverse (gh-5099)
        a = np.char.chararray(5)
        a[...] = ''
        a2, a2_inv = np.unique(a, return_inverse=True)
        assert_array_equal(a2_inv, np.zeros(5))

        # test for ticket #9137
        a = []
        a1_idx = np.unique(a, return_index=True)[1]
        a2_inv = np.unique(a, return_inverse=True)[1]
        a3_idx, a3_inv = np.unique(a, return_index=True,
                                   return_inverse=True)[1:]
        assert_equal(a1_idx.dtype, np.intp)
        assert_equal(a2_inv.dtype, np.intp)
        assert_equal(a3_idx.dtype, np.intp)
        assert_equal(a3_inv.dtype, np.intp)

        # test for ticket 2111 - float
        a = [2.0, np.nan, 1.0, np.nan]
        ua = [1.0, 2.0, np.nan]
        ua_idx = [2, 0, 1]
        ua_inv = [1, 2, 0, 2]
        ua_cnt = [1, 1, 2]
        assert_equal(np.unique(a), ua)
        assert_equal(np.unique(a, return_index=True), (ua, ua_idx))
        assert_equal(np.unique(a, return_inverse=True), (ua, ua_inv))
        assert_equal(np.unique(a, return_counts=True), (ua, ua_cnt))

        # test for ticket 2111 - complex
        a = [2.0 - 1j, np.nan, 1.0 + 1j, complex(0.0, np.nan), complex(1.0, np.nan)]
        ua = [1.0 + 1j, 2.0 - 1j, complex(0.0, np.nan)]
        ua_idx = [2, 0, 3]
        ua_inv = [1, 2, 0, 2, 2]
        ua_cnt = [1, 1, 3]
        assert_equal(np.unique(a), ua)
        assert_equal(np.unique(a, return_index=True), (ua, ua_idx))
        assert_equal(np.unique(a, return_inverse=True), (ua, ua_inv))
        assert_equal(np.unique(a, return_counts=True), (ua, ua_cnt))

        # test for ticket 2111 - datetime64
        nat = np.datetime64('nat')
        a = [np.datetime64('2020-12-26'), nat, np.datetime64('2020-12-24'), nat]
        ua = [np.datetime64('2020-12-24'), np.datetime64('2020-12-26'), nat]
        ua_idx = [2, 0, 1]
        ua_inv = [1, 2, 0, 2]
        ua_cnt = [1, 1, 2]
        assert_equal(np.unique(a), ua)
        assert_equal(np.unique(a, return_index=True), (ua, ua_idx))
        assert_equal(np.unique(a, return_inverse=True), (ua, ua_inv))
        assert_equal(np.unique(a, return_counts=True), (ua, ua_cnt))

        # test for ticket 2111 - timedelta
        nat = np.timedelta64('nat')
        a = [np.timedelta64(1, 'D'), nat, np.timedelta64(1, 'h'), nat]
        ua = [np.timedelta64(1, 'h'), np.timedelta64(1, 'D'), nat]
        ua_idx = [2, 0, 1]
        ua_inv = [1, 2, 0, 2]
        ua_cnt = [1, 1, 2]
        assert_equal(np.unique(a), ua)
        assert_equal(np.unique(a, return_index=True), (ua, ua_idx))
        assert_equal(np.unique(a, return_inverse=True), (ua, ua_inv))
        assert_equal(np.unique(a, return_counts=True), (ua, ua_cnt))

        # test for gh-19300
        all_nans = [np.nan] * 4
        ua = [np.nan]
        ua_idx = [0]
        ua_inv = [0, 0, 0, 0]
        ua_cnt = [4]
        assert_equal(np.unique(all_nans), ua)
        assert_equal(np.unique(all_nans, return_index=True), (ua, ua_idx))
        assert_equal(np.unique(all_nans, return_inverse=True), (ua, ua_inv))
        assert_equal(np.unique(all_nans, return_counts=True), (ua, ua_cnt))

    def test_unique_zero_sized(self):
        # test for zero-sized arrays
        for dt in self.get_types():
            a = np.array([], dt)
            b = np.array([], dt)
            i1 = np.array([], np.int64)
            i2 = np.array([], np.int64)
            c = np.array([], np.int64)
            self.check_all(a, b, i1, i2, c, dt)

    def test_unique_subclass(self):
        class Subclass(np.ndarray):
            pass

        i1 = [2, 3, 0, 1]
        i2 = [2, 3, 0, 1, 0, 2, 3] * 10
        c = np.multiply([2, 1, 2, 2], 10)

        # test for numeric arrays
        types = self.get_types()
        for dt in types:
            a = np.array([5, 7, 1, 2, 1, 5, 7] * 10, dtype=dt)
            b = np.array([1, 2, 5, 7], dtype=dt)
            aa = Subclass(a.shape, dtype=dt, buffer=a)
            bb = Subclass(b.shape, dtype=dt, buffer=b)
            self.check_all(aa, bb, i1, i2, c, dt)

    @pytest.mark.parametrize("arg", ["return_index", "return_inverse", "return_counts"])
    def test_unsupported_hash_based(self, arg):
        """These currently never use the hash-based solution.  However,
        it seems easier to just allow it.

        When the hash-based solution is added, this test should fail and be
        replaced with something more comprehensive.
        """
        a = np.array([1, 5, 2, 3, 4, 8, 199, 1, 3, 5])

        res_not_sorted = np.unique([1, 1], sorted=False, **{arg: True})
        res_sorted = np.unique([1, 1], sorted=True, **{arg: True})
        # The following should fail without first sorting `res_not_sorted`.
        for arr, expected in zip(res_not_sorted, res_sorted):
            assert_array_equal(arr, expected)

    def test_unique_axis_errors(self):
        assert_raises(TypeError, self._run_axis_tests, object)
        assert_raises(TypeError, self._run_axis_tests,
                      [('a', int), ('b', object)])

        assert_raises(AxisError, unique, np.arange(10), axis=2)
        assert_raises(AxisError, unique, np.arange(10), axis=-2)

    def test_unique_axis_list(self):
        msg = "Unique failed on list of lists"
        inp = [[0, 1, 0], [0, 1, 0]]
        inp_arr = np.asarray(inp)
        assert_array_equal(unique(inp, axis=0), unique(inp_arr, axis=0), msg)
        assert_array_equal(unique(inp, axis=1), unique(inp_arr, axis=1), msg)

    def test_unique_axis(self):
        types = []
        types.extend(np.typecodes['AllInteger'])
        types.extend(np.typecodes['AllFloat'])
        types.append('datetime64[D]')
        types.append('timedelta64[D]')
        types.append([('a', int), ('b', int)])
        types.append([('a', int), ('b', float)])

        for dtype in types:
            self._run_axis_tests(dtype)

        msg = 'Non-bitwise-equal booleans test failed'
        data = np.arange(10, dtype=np.uint8).reshape(-1, 2).view(bool)
        result = np.array([[False, True], [True, True]], dtype=bool)
        assert_array_equal(unique(data, axis=0), result, msg)

        msg = 'Negative zero equality test failed'
        data = np.array([[-0.0, 0.0], [0.0, -0.0], [-0.0, 0.0], [0.0, -0.0]])
        result = np.array([[-0.0, 0.0]])
        assert_array_equal(unique(data, axis=0), result, msg)

    @pytest.mark.parametrize("axis", [0, -1])
    def test_unique_1d_with_axis(self, axis):
        x = np.array([4, 3, 2, 3, 2, 1, 2, 2])
        uniq = unique(x, axis=axis)
        assert_array_equal(uniq, [1, 2, 3, 4])

    @pytest.mark.parametrize("axis", [None, 0, -1])
    def test_unique_inverse_with_axis(self, axis):
        x = np.array([[4, 4, 3], [2, 2, 1], [2, 2, 1], [4, 4, 3]])
        uniq, inv = unique(x, return_inverse=True, axis=axis)
        assert_equal(inv.ndim, x.ndim if axis is None else 1)
        assert_array_equal(x, np.take(uniq, inv, axis=axis))

    def test_unique_axis_zeros(self):
        # issue 15559
        single_zero = np.empty(shape=(2, 0), dtype=np.int8)
        uniq, idx, inv, cnt = unique(single_zero, axis=0, return_index=True,
                                     return_inverse=True, return_counts=True)

        # there's 1 element of shape (0,) along axis 0
        assert_equal(uniq.dtype, single_zero.dtype)
        assert_array_equal(uniq, np.empty(shape=(1, 0)))
        assert_array_equal(idx, np.array([0]))
        assert_array_equal(inv, np.array([0, 0]))
        assert_array_equal(cnt, np.array([2]))

        # there's 0 elements of shape (2,) along axis 1
        uniq, idx, inv, cnt = unique(single_zero, axis=1, return_index=True,
                                     return_inverse=True, return_counts=True)

        assert_equal(uniq.dtype, single_zero.dtype)
        assert_array_equal(uniq, np.empty(shape=(2, 0)))
        assert_array_equal(idx, np.array([]))
        assert_array_equal(inv, np.array([]))
        assert_array_equal(cnt, np.array([]))

        # test a "complicated" shape
        shape = (0, 2, 0, 3, 0, 4, 0)
        multiple_zeros = np.empty(shape=shape)
        for axis in range(len(shape)):
            expected_shape = list(shape)
            if shape[axis] == 0:
                expected_shape[axis] = 0
            else:
                expected_shape[axis] = 1

            assert_array_equal(unique(multiple_zeros, axis=axis),
                               np.empty(shape=expected_shape))

    def test_unique_masked(self):
        # issue 8664
        x = np.array([64, 0, 1, 2, 3, 63, 63, 0, 0, 0, 1, 2, 0, 63, 0],
                     dtype='uint8')
        y = np.ma.masked_equal(x, 0)

        v = np.unique(y)
        v2, i, c = np.unique(y, return_index=True, return_counts=True)

        msg = 'Unique returned different results when asked for index'
        assert_array_equal(v.data, v2.data, msg)
        assert_array_equal(v.mask, v2.mask, msg)

    def test_unique_sort_order_with_axis(self):
        # These tests fail if sorting along axis is done by treating subarrays
        # as unsigned byte strings.  See gh-10495.
        fmt = "sort order incorrect for integer type '%s'"
        for dt in 'bhilq':
            a = np.array([[-1], [0]], dt)
            b = np.unique(a, axis=0)
            assert_array_equal(a, b, fmt % dt)

    def _run_axis_tests(self, dtype):
        data = np.array([[0, 1, 0, 0],
                         [1, 0, 0, 0],
                         [0, 1, 0, 0],
                         [1, 0, 0, 0]]).astype(dtype)

        msg = 'Unique with 1d array and axis=0 failed'
        result = np.array([0, 1])
        assert_array_equal(unique(data), result.astype(dtype), msg)

        msg = 'Unique with 2d array and axis=0 failed'
        result = np.array([[0, 1, 0, 0], [1, 0, 0, 0]])
        assert_array_equal(unique(data, axis=0), result.astype(dtype), msg)

        msg = 'Unique with 2d array and axis=1 failed'
        result = np.array([[0, 0, 1], [0, 1, 0], [0, 0, 1], [0, 1, 0]])
        assert_array_equal(unique(data, axis=1), result.astype(dtype), msg)

        msg = 'Unique with 3d array and axis=2 failed'
        data3d = np.array([[[1, 1],
                            [1, 0]],
                           [[0, 1],
                            [0, 0]]]).astype(dtype)
        result = np.take(data3d, [1, 0], axis=2)
        assert_array_equal(unique(data3d, axis=2), result, msg)

        uniq, idx, inv, cnt = unique(data, axis=0, return_index=True,
                                     return_inverse=True, return_counts=True)
        msg = "Unique's return_index=True failed with axis=0"
        assert_array_equal(data[idx], uniq, msg)
        msg = "Unique's return_inverse=True failed with axis=0"
        assert_array_equal(np.take(uniq, inv, axis=0), data)
        msg = "Unique's return_counts=True failed with axis=0"
        assert_array_equal(cnt, np.array([2, 2]), msg)

        uniq, idx, inv, cnt = unique(data, axis=1, return_index=True,
                                     return_inverse=True, return_counts=True)
        msg = "Unique's return_index=True failed with axis=1"
        assert_array_equal(data[:, idx], uniq)
        msg = "Unique's return_inverse=True failed with axis=1"
        assert_array_equal(np.take(uniq, inv, axis=1), data)
        msg = "Unique's return_counts=True failed with axis=1"
        assert_array_equal(cnt, np.array([2, 1, 1]), msg)

    def test_unique_nanequals(self):
        # issue 20326
        a = np.array([1, 1, np.nan, np.nan, np.nan])
        unq = np.unique(a)
        not_unq = np.unique(a, equal_nan=False)
        assert_array_equal(unq, np.array([1, np.nan]))
        assert_array_equal(not_unq, np.array([1, np.nan, np.nan, np.nan]))

    def test_unique_array_api_functions(self):
        arr = np.array([np.nan, 1, 4, 1, 3, 4, np.nan, 5, 1])

        for res_unique_array_api, res_unique in [
            (
                np.unique_values(arr),
                np.unique(arr, equal_nan=False)
            ),
            (
                np.unique_counts(arr),
                np.unique(arr, return_counts=True, equal_nan=False)
            ),
            (
                np.unique_inverse(arr),
                np.unique(arr, return_inverse=True, equal_nan=False)
            ),
            (
                np.unique_all(arr),
                np.unique(
                    arr,
                    return_index=True,
                    return_inverse=True,
                    return_counts=True,
                    equal_nan=False
                )
            )
        ]:
            assert len(res_unique_array_api) == len(res_unique)
            for actual, expected in zip(res_unique_array_api, res_unique):
                assert_array_equal(actual, expected)

    def test_unique_inverse_shape(self):
        # Regression test for https://github.com/numpy/numpy/issues/25552
        arr = np.array([[1, 2, 3], [2, 3, 1]])
        expected_values, expected_inverse = np.unique(arr, return_inverse=True)
        expected_inverse = expected_inverse.reshape(arr.shape)
        for func in np.unique_inverse, np.unique_all:
            result = func(arr)
            assert_array_equal(expected_values, result.values)
            assert_array_equal(expected_inverse, result.inverse_indices)
            assert_array_equal(arr, result.values[result.inverse_indices])

    @pytest.mark.parametrize(
        'data',
        [[[1, 1, 1],
          [1, 1, 1]],
         [1, 3, 2],
         1],
    )
    @pytest.mark.parametrize('transpose', [False, True])
    @pytest.mark.parametrize('dtype', [np.int32, np.float64])
    def test_unique_with_matrix(self, data, transpose, dtype):
        mat = np.matrix(data).astype(dtype)
        if transpose:
            mat = mat.T
        u = np.unique(mat)
        expected = np.unique(np.asarray(mat))
        assert_array_equal(u, expected, strict=True)

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\tests\test_arraysetops.py ===
"""Test functions for 1D array set operations.

"""
import pytest

import numpy as np
from numpy import ediff1d, intersect1d, isin, setdiff1d, setxor1d, union1d, unique
from numpy.exceptions import AxisError
from numpy.testing import (
    assert_array_equal,
    assert_equal,
    assert_raises,
    assert_raises_regex,
)


class TestSetOps:

    def test_intersect1d(self):
        # unique inputs
        a = np.array([5, 7, 1, 2])
        b = np.array([2, 4, 3, 1, 5])

        ec = np.array([1, 2, 5])
        c = intersect1d(a, b, assume_unique=True)
        assert_array_equal(c, ec)

        # non-unique inputs
        a = np.array([5, 5, 7, 1, 2])
        b = np.array([2, 1, 4, 3, 3, 1, 5])

        ed = np.array([1, 2, 5])
        c = intersect1d(a, b)
        assert_array_equal(c, ed)
        assert_array_equal([], intersect1d([], []))

    def test_intersect1d_array_like(self):
        # See gh-11772
        class Test:
            def __array__(self, dtype=None, copy=None):
                return np.arange(3)

        a = Test()
        res = intersect1d(a, a)
        assert_array_equal(res, a)
        res = intersect1d([1, 2, 3], [1, 2, 3])
        assert_array_equal(res, [1, 2, 3])

    def test_intersect1d_indices(self):
        # unique inputs
        a = np.array([1, 2, 3, 4])
        b = np.array([2, 1, 4, 6])
        c, i1, i2 = intersect1d(a, b, assume_unique=True, return_indices=True)
        ee = np.array([1, 2, 4])
        assert_array_equal(c, ee)
        assert_array_equal(a[i1], ee)
        assert_array_equal(b[i2], ee)

        # non-unique inputs
        a = np.array([1, 2, 2, 3, 4, 3, 2])
        b = np.array([1, 8, 4, 2, 2, 3, 2, 3])
        c, i1, i2 = intersect1d(a, b, return_indices=True)
        ef = np.array([1, 2, 3, 4])
        assert_array_equal(c, ef)
        assert_array_equal(a[i1], ef)
        assert_array_equal(b[i2], ef)

        # non1d, unique inputs
        a = np.array([[2, 4, 5, 6], [7, 8, 1, 15]])
        b = np.array([[3, 2, 7, 6], [10, 12, 8, 9]])
        c, i1, i2 = intersect1d(a, b, assume_unique=True, return_indices=True)
        ui1 = np.unravel_index(i1, a.shape)
        ui2 = np.unravel_index(i2, b.shape)
        ea = np.array([2, 6, 7, 8])
        assert_array_equal(ea, a[ui1])
        assert_array_equal(ea, b[ui2])

        # non1d, not assumed to be uniqueinputs
        a = np.array([[2, 4, 5, 6, 6], [4, 7, 8, 7, 2]])
        b = np.array([[3, 2, 7, 7], [10, 12, 8, 7]])
        c, i1, i2 = intersect1d(a, b, return_indices=True)
        ui1 = np.unravel_index(i1, a.shape)
        ui2 = np.unravel_index(i2, b.shape)
        ea = np.array([2, 7, 8])
        assert_array_equal(ea, a[ui1])
        assert_array_equal(ea, b[ui2])

    def test_setxor1d(self):
        a = np.array([5, 7, 1, 2])
        b = np.array([2, 4, 3, 1, 5])

        ec = np.array([3, 4, 7])
        c = setxor1d(a, b)
        assert_array_equal(c, ec)

        a = np.array([1, 2, 3])
        b = np.array([6, 5, 4])

        ec = np.array([1, 2, 3, 4, 5, 6])
        c = setxor1d(a, b)
        assert_array_equal(c, ec)

        a = np.array([1, 8, 2, 3])
        b = np.array([6, 5, 4, 8])

        ec = np.array([1, 2, 3, 4, 5, 6])
        c = setxor1d(a, b)
        assert_array_equal(c, ec)

        assert_array_equal([], setxor1d([], []))

    def test_setxor1d_unique(self):
        a = np.array([1, 8, 2, 3])
        b = np.array([6, 5, 4, 8])

        ec = np.array([1, 2, 3, 4, 5, 6])
        c = setxor1d(a, b, assume_unique=True)
        assert_array_equal(c, ec)

        a = np.array([[1], [8], [2], [3]])
        b = np.array([[6, 5], [4, 8]])

        ec = np.array([1, 2, 3, 4, 5, 6])
        c = setxor1d(a, b, assume_unique=True)
        assert_array_equal(c, ec)

    def test_ediff1d(self):
        zero_elem = np.array([])
        one_elem = np.array([1])
        two_elem = np.array([1, 2])

        assert_array_equal([], ediff1d(zero_elem))
        assert_array_equal([0], ediff1d(zero_elem, to_begin=0))
        assert_array_equal([0], ediff1d(zero_elem, to_end=0))
        assert_array_equal([-1, 0], ediff1d(zero_elem, to_begin=-1, to_end=0))
        assert_array_equal([], ediff1d(one_elem))
        assert_array_equal([1], ediff1d(two_elem))
        assert_array_equal([7, 1, 9], ediff1d(two_elem, to_begin=7, to_end=9))
        assert_array_equal([5, 6, 1, 7, 8],
                           ediff1d(two_elem, to_begin=[5, 6], to_end=[7, 8]))
        assert_array_equal([1, 9], ediff1d(two_elem, to_end=9))
        assert_array_equal([1, 7, 8], ediff1d(two_elem, to_end=[7, 8]))
        assert_array_equal([7, 1], ediff1d(two_elem, to_begin=7))
        assert_array_equal([5, 6, 1], ediff1d(two_elem, to_begin=[5, 6]))

    @pytest.mark.parametrize("ary, prepend, append, expected", [
        # should fail because trying to cast
        # np.nan standard floating point value
        # into an integer array:
        (np.array([1, 2, 3], dtype=np.int64),
         None,
         np.nan,
         'to_end'),
        # should fail because attempting
        # to downcast to int type:
        (np.array([1, 2, 3], dtype=np.int64),
         np.array([5, 7, 2], dtype=np.float32),
         None,
         'to_begin'),
        # should fail because attempting to cast
        # two special floating point values
        # to integers (on both sides of ary),
        # `to_begin` is in the error message as the impl checks this first:
        (np.array([1., 3., 9.], dtype=np.int8),
         np.nan,
         np.nan,
         'to_begin'),
         ])
    def test_ediff1d_forbidden_type_casts(self, ary, prepend, append, expected):
        # verify resolution of gh-11490

        # specifically, raise an appropriate
        # Exception when attempting to append or
        # prepend with an incompatible type
        msg = f'dtype of `{expected}` must be compatible'
        with assert_raises_regex(TypeError, msg):
            ediff1d(ary=ary,
                    to_end=append,
                    to_begin=prepend)

    @pytest.mark.parametrize(
        "ary,prepend,append,expected",
        [
         (np.array([1, 2, 3], dtype=np.int16),
          2**16,  # will be cast to int16 under same kind rule.
          2**16 + 4,
          np.array([0, 1, 1, 4], dtype=np.int16)),
         (np.array([1, 2, 3], dtype=np.float32),
          np.array([5], dtype=np.float64),
          None,
          np.array([5, 1, 1], dtype=np.float32)),
         (np.array([1, 2, 3], dtype=np.int32),
          0,
          0,
          np.array([0, 1, 1, 0], dtype=np.int32)),
         (np.array([1, 2, 3], dtype=np.int64),
          3,
          -9,
          np.array([3, 1, 1, -9], dtype=np.int64)),
        ]
    )
    def test_ediff1d_scalar_handling(self,
                                     ary,
                                     prepend,
                                     append,
                                     expected):
        # maintain backwards-compatibility
        # of scalar prepend / append behavior
        # in ediff1d following fix for gh-11490
        actual = np.ediff1d(ary=ary,
                            to_end=append,
                            to_begin=prepend)
        assert_equal(actual, expected)
        assert actual.dtype == expected.dtype

    @pytest.mark.parametrize("kind", [None, "sort", "table"])
    def test_isin(self, kind):
        def _isin_slow(a, b):
            b = np.asarray(b).flatten().tolist()
            return a in b
        isin_slow = np.vectorize(_isin_slow, otypes=[bool], excluded={1})

        def assert_isin_equal(a, b):
            x = isin(a, b, kind=kind)
            y = isin_slow(a, b)
            assert_array_equal(x, y)

        # multidimensional arrays in both arguments
        a = np.arange(24).reshape([2, 3, 4])
        b = np.array([[10, 20, 30], [0, 1, 3], [11, 22, 33]])
        assert_isin_equal(a, b)

        # array-likes as both arguments
        c = [(9, 8), (7, 6)]
        d = (9, 7)
        assert_isin_equal(c, d)

        # zero-d array:
        f = np.array(3)
        assert_isin_equal(f, b)
        assert_isin_equal(a, f)
        assert_isin_equal(f, f)

        # scalar:
        assert_isin_equal(5, b)
        assert_isin_equal(a, 6)
        assert_isin_equal(5, 6)

        # empty array-like:
        if kind != "table":
            # An empty list will become float64,
            # which is invalid for kind="table"
            x = []
            assert_isin_equal(x, b)
            assert_isin_equal(a, x)
            assert_isin_equal(x, x)

        # empty array with various types:
        for dtype in [bool, np.int64, np.float64]:
            if kind == "table" and dtype == np.float64:
                continue

            if dtype in {np.int64, np.float64}:
                ar = np.array([10, 20, 30], dtype=dtype)
            elif dtype in {bool}:
                ar = np.array([True, False, False])

            empty_array = np.array([], dtype=dtype)

            assert_isin_equal(empty_array, ar)
            assert_isin_equal(ar, empty_array)
            assert_isin_equal(empty_array, empty_array)

    @pytest.mark.parametrize("kind", [None, "sort", "table"])
    def test_isin_additional(self, kind):
        # we use two different sizes for the b array here to test the
        # two different paths in isin().
        for mult in (1, 10):
            # One check without np.array to make sure lists are handled correct
            a = [5, 7, 1, 2]
            b = [2, 4, 3, 1, 5] * mult
            ec = np.array([True, False, True, True])
            c = isin(a, b, assume_unique=True, kind=kind)
            assert_array_equal(c, ec)

            a[0] = 8
            ec = np.array([False, False, True, True])
            c = isin(a, b, assume_unique=True, kind=kind)
            assert_array_equal(c, ec)

            a[0], a[3] = 4, 8
            ec = np.array([True, False, True, False])
            c = isin(a, b, assume_unique=True, kind=kind)
            assert_array_equal(c, ec)

            a = np.array([5, 4, 5, 3, 4, 4, 3, 4, 3, 5, 2, 1, 5, 5])
            b = [2, 3, 4] * mult
            ec = [False, True, False, True, True, True, True, True, True,
                  False, True, False, False, False]
            c = isin(a, b, kind=kind)
            assert_array_equal(c, ec)

            b = b + [5, 5, 4] * mult
            ec = [True, True, True, True, True, True, True, True, True, True,
                  True, False, True, True]
            c = isin(a, b, kind=kind)
            assert_array_equal(c, ec)

            a = np.array([5, 7, 1, 2])
            b = np.array([2, 4, 3, 1, 5] * mult)
            ec = np.array([True, False, True, True])
            c = isin(a, b, kind=kind)
            assert_array_equal(c, ec)

            a = np.array([5, 7, 1, 1, 2])
            b = np.array([2, 4, 3, 3, 1, 5] * mult)
            ec = np.array([True, False, True, True, True])
            c = isin(a, b, kind=kind)
            assert_array_equal(c, ec)

            a = np.array([5, 5])
            b = np.array([2, 2] * mult)
            ec = np.array([False, False])
            c = isin(a, b, kind=kind)
            assert_array_equal(c, ec)

        a = np.array([5])
        b = np.array([2])
        ec = np.array([False])
        c = isin(a, b, kind=kind)
        assert_array_equal(c, ec)

        if kind in {None, "sort"}:
            assert_array_equal(isin([], [], kind=kind), [])

    def test_isin_char_array(self):
        a = np.array(['a', 'b', 'c', 'd', 'e', 'c', 'e', 'b'])
        b = np.array(['a', 'c'])

        ec = np.array([True, False, True, False, False, True, False, False])
        c = isin(a, b)

        assert_array_equal(c, ec)

    @pytest.mark.parametrize("kind", [None, "sort", "table"])
    def test_isin_invert(self, kind):
        "Test isin's invert parameter"
        # We use two different sizes for the b array here to test the
        # two different paths in isin().
        for mult in (1, 10):
            a = np.array([5, 4, 5, 3, 4, 4, 3, 4, 3, 5, 2, 1, 5, 5])
            b = [2, 3, 4] * mult
            assert_array_equal(np.invert(isin(a, b, kind=kind)),
                               isin(a, b, invert=True, kind=kind))

        # float:
        if kind in {None, "sort"}:
            for mult in (1, 10):
                a = np.array([5, 4, 5, 3, 4, 4, 3, 4, 3, 5, 2, 1, 5, 5],
                            dtype=np.float32)
                b = [2, 3, 4] * mult
                b = np.array(b, dtype=np.float32)
                assert_array_equal(np.invert(isin(a, b, kind=kind)),
                                   isin(a, b, invert=True, kind=kind))

    def test_isin_hit_alternate_algorithm(self):
        """Hit the standard isin code with integers"""
        # Need extreme range to hit standard code
        # This hits it without the use of kind='table'
        a = np.array([5, 4, 5, 3, 4, 4, 1e9], dtype=np.int64)
        b = np.array([2, 3, 4, 1e9], dtype=np.int64)
        expected = np.array([0, 1, 0, 1, 1, 1, 1], dtype=bool)
        assert_array_equal(expected, isin(a, b))
        assert_array_equal(np.invert(expected), isin(a, b, invert=True))

        a = np.array([5, 7, 1, 2], dtype=np.int64)
        b = np.array([2, 4, 3, 1, 5, 1e9], dtype=np.int64)
        ec = np.array([True, False, True, True])
        c = isin(a, b, assume_unique=True)
        assert_array_equal(c, ec)

    @pytest.mark.parametrize("kind", [None, "sort", "table"])
    def test_isin_boolean(self, kind):
        """Test that isin works for boolean input"""
        a = np.array([True, False])
        b = np.array([False, False, False])
        expected = np.array([False, True])
        assert_array_equal(expected,
                           isin(a, b, kind=kind))
        assert_array_equal(np.invert(expected),
                           isin(a, b, invert=True, kind=kind))

    @pytest.mark.parametrize("kind", [None, "sort"])
    def test_isin_timedelta(self, kind):
        """Test that isin works for timedelta input"""
        rstate = np.random.RandomState(0)
        a = rstate.randint(0, 100, size=10)
        b = rstate.randint(0, 100, size=10)
        truth = isin(a, b)
        a_timedelta = a.astype("timedelta64[s]")
        b_timedelta = b.astype("timedelta64[s]")
        assert_array_equal(truth, isin(a_timedelta, b_timedelta, kind=kind))

    def test_isin_table_timedelta_fails(self):
        a = np.array([0, 1, 2], dtype="timedelta64[s]")
        b = a
        # Make sure it raises a value error:
        with pytest.raises(ValueError):
            isin(a, b, kind="table")

    @pytest.mark.parametrize(
        "dtype1,dtype2",
        [
            (np.int8, np.int16),
            (np.int16, np.int8),
            (np.uint8, np.uint16),
            (np.uint16, np.uint8),
            (np.uint8, np.int16),
            (np.int16, np.uint8),
            (np.uint64, np.int64),
        ]
    )
    @pytest.mark.parametrize("kind", [None, "sort", "table"])
    def test_isin_mixed_dtype(self, dtype1, dtype2, kind):
        """Test that isin works as expected for mixed dtype input."""
        is_dtype2_signed = np.issubdtype(dtype2, np.signedinteger)
        ar1 = np.array([0, 0, 1, 1], dtype=dtype1)

        if is_dtype2_signed:
            ar2 = np.array([-128, 0, 127], dtype=dtype2)
        else:
            ar2 = np.array([127, 0, 255], dtype=dtype2)

        expected = np.array([True, True, False, False])

        expect_failure = kind == "table" and (
            dtype1 == np.int16 and dtype2 == np.int8)

        if expect_failure:
            with pytest.raises(RuntimeError, match="exceed the maximum"):
                isin(ar1, ar2, kind=kind)
        else:
            assert_array_equal(isin(ar1, ar2, kind=kind), expected)

    @pytest.mark.parametrize("data", [
        np.array([2**63, 2**63 + 1], dtype=np.uint64),
        np.array([-2**62, -2**62 - 1], dtype=np.int64),
    ])
    @pytest.mark.parametrize("kind", [None, "sort", "table"])
    def test_isin_mixed_huge_vals(self, kind, data):
        """Test values outside intp range (negative ones if 32bit system)"""
        query = data[1]
        res = np.isin(data, query, kind=kind)
        assert_array_equal(res, [False, True])
        # Also check that nothing weird happens for values can't possibly
        # in range.
        data = data.astype(np.int32)  # clearly different values
        res = np.isin(data, query, kind=kind)
        assert_array_equal(res, [False, False])

    @pytest.mark.parametrize("kind", [None, "sort", "table"])
    def test_isin_mixed_boolean(self, kind):
        """Test that isin works as expected for bool/int input."""
        for dtype in np.typecodes["AllInteger"]:
            a = np.array([True, False, False], dtype=bool)
            b = np.array([0, 0, 0, 0], dtype=dtype)
            expected = np.array([False, True, True], dtype=bool)
            assert_array_equal(isin(a, b, kind=kind), expected)

            a, b = b, a
            expected = np.array([True, True, True, True], dtype=bool)
            assert_array_equal(isin(a, b, kind=kind), expected)

    def test_isin_first_array_is_object(self):
        ar1 = [None]
        ar2 = np.array([1] * 10)
        expected = np.array([False])
        result = np.isin(ar1, ar2)
        assert_array_equal(result, expected)

    def test_isin_second_array_is_object(self):
        ar1 = 1
        ar2 = np.array([None] * 10)
        expected = np.array([False])
        result = np.isin(ar1, ar2)
        assert_array_equal(result, expected)

    def test_isin_both_arrays_are_object(self):
        ar1 = [None]
        ar2 = np.array([None] * 10)
        expected = np.array([True])
        result = np.isin(ar1, ar2)
        assert_array_equal(result, expected)

    def test_isin_both_arrays_have_structured_dtype(self):
        # Test arrays of a structured data type containing an integer field
        # and a field of dtype `object` allowing for arbitrary Python objects
        dt = np.dtype([('field1', int), ('field2', object)])
        ar1 = np.array([(1, None)], dtype=dt)
        ar2 = np.array([(1, None)] * 10, dtype=dt)
        expected = np.array([True])
        result = np.isin(ar1, ar2)
        assert_array_equal(result, expected)

    def test_isin_with_arrays_containing_tuples(self):
        ar1 = np.array([(1,), 2], dtype=object)
        ar2 = np.array([(1,), 2], dtype=object)
        expected = np.array([True, True])
        result = np.isin(ar1, ar2)
        assert_array_equal(result, expected)
        result = np.isin(ar1, ar2, invert=True)
        assert_array_equal(result, np.invert(expected))

        # An integer is added at the end of the array to make sure
        # that the array builder will create the array with tuples
        # and after it's created the integer is removed.
        # There's a bug in the array constructor that doesn't handle
        # tuples properly and adding the integer fixes that.
        ar1 = np.array([(1,), (2, 1), 1], dtype=object)
        ar1 = ar1[:-1]
        ar2 = np.array([(1,), (2, 1), 1], dtype=object)
        ar2 = ar2[:-1]
        expected = np.array([True, True])
        result = np.isin(ar1, ar2)
        assert_array_equal(result, expected)
        result = np.isin(ar1, ar2, invert=True)
        assert_array_equal(result, np.invert(expected))

        ar1 = np.array([(1,), (2, 3), 1], dtype=object)
        ar1 = ar1[:-1]
        ar2 = np.array([(1,), 2], dtype=object)
        expected = np.array([True, False])
        result = np.isin(ar1, ar2)
        assert_array_equal(result, expected)
        result = np.isin(ar1, ar2, invert=True)
        assert_array_equal(result, np.invert(expected))

    def test_isin_errors(self):
        """Test that isin raises expected errors."""

        # Error 1: `kind` is not one of 'sort' 'table' or None.
        ar1 = np.array([1, 2, 3, 4, 5])
        ar2 = np.array([2, 4, 6, 8, 10])
        assert_raises(ValueError, isin, ar1, ar2, kind='quicksort')

        # Error 2: `kind="table"` does not work for non-integral arrays.
        obj_ar1 = np.array([1, 'a', 3, 'b', 5], dtype=object)
        obj_ar2 = np.array([1, 'a', 3, 'b', 5], dtype=object)
        assert_raises(ValueError, isin, obj_ar1, obj_ar2, kind='table')

        for dtype in [np.int32, np.int64]:
            ar1 = np.array([-1, 2, 3, 4, 5], dtype=dtype)
            # The range of this array will overflow:
            overflow_ar2 = np.array([-1, np.iinfo(dtype).max], dtype=dtype)

            # Error 3: `kind="table"` will trigger a runtime error
            #  if there is an integer overflow expected when computing the
            #  range of ar2
            assert_raises(
                RuntimeError,
                isin, ar1, overflow_ar2, kind='table'
            )

            # Non-error: `kind=None` will *not* trigger a runtime error
            #  if there is an integer overflow, it will switch to
            #  the `sort` algorithm.
            result = np.isin(ar1, overflow_ar2, kind=None)
            assert_array_equal(result, [True] + [False] * 4)
            result = np.isin(ar1, overflow_ar2, kind='sort')
            assert_array_equal(result, [True] + [False] * 4)

    def test_union1d(self):
        a = np.array([5, 4, 7, 1, 2])
        b = np.array([2, 4, 3, 3, 2, 1, 5])

        ec = np.array([1, 2, 3, 4, 5, 7])
        c = union1d(a, b)
        assert_array_equal(c, ec)

        # Tests gh-10340, arguments to union1d should be
        # flattened if they are not already 1D
        x = np.array([[0, 1, 2], [3, 4, 5]])
        y = np.array([0, 1, 2, 3, 4])
        ez = np.array([0, 1, 2, 3, 4, 5])
        z = union1d(x, y)
        assert_array_equal(z, ez)

        assert_array_equal([], union1d([], []))

    def test_setdiff1d(self):
        a = np.array([6, 5, 4, 7, 1, 2, 7, 4])
        b = np.array([2, 4, 3, 3, 2, 1, 5])

        ec = np.array([6, 7])
        c = setdiff1d(a, b)
        assert_array_equal(c, ec)

        a = np.arange(21)
        b = np.arange(19)
        ec = np.array([19, 20])
        c = setdiff1d(a, b)
        assert_array_equal(c, ec)

        assert_array_equal([], setdiff1d([], []))
        a = np.array((), np.uint32)
        assert_equal(setdiff1d(a, []).dtype, np.uint32)

    def test_setdiff1d_unique(self):
        a = np.array([3, 2, 1])
        b = np.array([7, 5, 2])
        expected = np.array([3, 1])
        actual = setdiff1d(a, b, assume_unique=True)
        assert_equal(actual, expected)

    def test_setdiff1d_char_array(self):
        a = np.array(['a', 'b', 'c'])
        b = np.array(['a', 'b', 's'])
        assert_array_equal(setdiff1d(a, b), np.array(['c']))

    def test_manyways(self):
        a = np.array([5, 7, 1, 2, 8])
        b = np.array([9, 8, 2, 4, 3, 1, 5])

        c1 = setxor1d(a, b)
        aux1 = intersect1d(a, b)
        aux2 = union1d(a, b)
        c2 = setdiff1d(aux2, aux1)
        assert_array_equal(c1, c2)


class TestUnique:

    def check_all(self, a, b, i1, i2, c, dt):
        base_msg = 'check {0} failed for type {1}'

        msg = base_msg.format('values', dt)
        v = unique(a)
        assert_array_equal(v, b, msg)
        assert type(v) == type(b)

        msg = base_msg.format('return_index', dt)
        v, j = unique(a, True, False, False)
        assert_array_equal(v, b, msg)
        assert_array_equal(j, i1, msg)
        assert type(v) == type(b)

        msg = base_msg.format('return_inverse', dt)
        v, j = unique(a, False, True, False)
        assert_array_equal(v, b, msg)
        assert_array_equal(j, i2, msg)
        assert type(v) == type(b)

        msg = base_msg.format('return_counts', dt)
        v, j = unique(a, False, False, True)
        assert_array_equal(v, b, msg)
        assert_array_equal(j, c, msg)
        assert type(v) == type(b)

        msg = base_msg.format('return_index and return_inverse', dt)
        v, j1, j2 = unique(a, True, True, False)
        assert_array_equal(v, b, msg)
        assert_array_equal(j1, i1, msg)
        assert_array_equal(j2, i2, msg)
        assert type(v) == type(b)

        msg = base_msg.format('return_index and return_counts', dt)
        v, j1, j2 = unique(a, True, False, True)
        assert_array_equal(v, b, msg)
        assert_array_equal(j1, i1, msg)
        assert_array_equal(j2, c, msg)
        assert type(v) == type(b)

        msg = base_msg.format('return_inverse and return_counts', dt)
        v, j1, j2 = unique(a, False, True, True)
        assert_array_equal(v, b, msg)
        assert_array_equal(j1, i2, msg)
        assert_array_equal(j2, c, msg)
        assert type(v) == type(b)

        msg = base_msg.format(('return_index, return_inverse '
                                'and return_counts'), dt)
        v, j1, j2, j3 = unique(a, True, True, True)
        assert_array_equal(v, b, msg)
        assert_array_equal(j1, i1, msg)
        assert_array_equal(j2, i2, msg)
        assert_array_equal(j3, c, msg)
        assert type(v) == type(b)

    def get_types(self):
        types = []
        types.extend(np.typecodes['AllInteger'])
        types.extend(np.typecodes['AllFloat'])
        types.append('datetime64[D]')
        types.append('timedelta64[D]')
        return types

    def test_unique_1d(self):

        a = [5, 7, 1, 2, 1, 5, 7] * 10
        b = [1, 2, 5, 7]
        i1 = [2, 3, 0, 1]
        i2 = [2, 3, 0, 1, 0, 2, 3] * 10
        c = np.multiply([2, 1, 2, 2], 10)

        # test for numeric arrays
        types = self.get_types()
        for dt in types:
            aa = np.array(a, dt)
            bb = np.array(b, dt)
            self.check_all(aa, bb, i1, i2, c, dt)

        # test for object arrays
        dt = 'O'
        aa = np.empty(len(a), dt)
        aa[:] = a
        bb = np.empty(len(b), dt)
        bb[:] = b
        self.check_all(aa, bb, i1, i2, c, dt)

        # test for structured arrays
        dt = [('', 'i'), ('', 'i')]
        aa = np.array(list(zip(a, a)), dt)
        bb = np.array(list(zip(b, b)), dt)
        self.check_all(aa, bb, i1, i2, c, dt)

        # test for ticket #2799
        aa = [1. + 0.j, 1 - 1.j, 1]
        assert_array_equal(np.unique(aa), [1. - 1.j, 1. + 0.j])

        # test for ticket #4785
        a = [(1, 2), (1, 2), (2, 3)]
        unq = [1, 2, 3]
        inv = [[0, 1], [0, 1], [1, 2]]
        a1 = unique(a)
        assert_array_equal(a1, unq)
        a2, a2_inv = unique(a, return_inverse=True)
        assert_array_equal(a2, unq)
        assert_array_equal(a2_inv, inv)

        # test for chararrays with return_inverse (gh-5099)
        a = np.char.chararray(5)
        a[...] = ''
        a2, a2_inv = np.unique(a, return_inverse=True)
        assert_array_equal(a2_inv, np.zeros(5))

        # test for ticket #9137
        a = []
        a1_idx = np.unique(a, return_index=True)[1]
        a2_inv = np.unique(a, return_inverse=True)[1]
        a3_idx, a3_inv = np.unique(a, return_index=True,
                                   return_inverse=True)[1:]
        assert_equal(a1_idx.dtype, np.intp)
        assert_equal(a2_inv.dtype, np.intp)
        assert_equal(a3_idx.dtype, np.intp)
        assert_equal(a3_inv.dtype, np.intp)

        # test for ticket 2111 - float
        a = [2.0, np.nan, 1.0, np.nan]
        ua = [1.0, 2.0, np.nan]
        ua_idx = [2, 0, 1]
        ua_inv = [1, 2, 0, 2]
        ua_cnt = [1, 1, 2]
        assert_equal(np.unique(a), ua)
        assert_equal(np.unique(a, return_index=True), (ua, ua_idx))
        assert_equal(np.unique(a, return_inverse=True), (ua, ua_inv))
        assert_equal(np.unique(a, return_counts=True), (ua, ua_cnt))

        # test for ticket 2111 - complex
        a = [2.0 - 1j, np.nan, 1.0 + 1j, complex(0.0, np.nan), complex(1.0, np.nan)]
        ua = [1.0 + 1j, 2.0 - 1j, complex(0.0, np.nan)]
        ua_idx = [2, 0, 3]
        ua_inv = [1, 2, 0, 2, 2]
        ua_cnt = [1, 1, 3]
        assert_equal(np.unique(a), ua)
        assert_equal(np.unique(a, return_index=True), (ua, ua_idx))
        assert_equal(np.unique(a, return_inverse=True), (ua, ua_inv))
        assert_equal(np.unique(a, return_counts=True), (ua, ua_cnt))

        # test for ticket 2111 - datetime64
        nat = np.datetime64('nat')
        a = [np.datetime64('2020-12-26'), nat, np.datetime64('2020-12-24'), nat]
        ua = [np.datetime64('2020-12-24'), np.datetime64('2020-12-26'), nat]
        ua_idx = [2, 0, 1]
        ua_inv = [1, 2, 0, 2]
        ua_cnt = [1, 1, 2]
        assert_equal(np.unique(a), ua)
        assert_equal(np.unique(a, return_index=True), (ua, ua_idx))
        assert_equal(np.unique(a, return_inverse=True), (ua, ua_inv))
        assert_equal(np.unique(a, return_counts=True), (ua, ua_cnt))

        # test for ticket 2111 - timedelta
        nat = np.timedelta64('nat')
        a = [np.timedelta64(1, 'D'), nat, np.timedelta64(1, 'h'), nat]
        ua = [np.timedelta64(1, 'h'), np.timedelta64(1, 'D'), nat]
        ua_idx = [2, 0, 1]
        ua_inv = [1, 2, 0, 2]
        ua_cnt = [1, 1, 2]
        assert_equal(np.unique(a), ua)
        assert_equal(np.unique(a, return_index=True), (ua, ua_idx))
        assert_equal(np.unique(a, return_inverse=True), (ua, ua_inv))
        assert_equal(np.unique(a, return_counts=True), (ua, ua_cnt))

        # test for gh-19300
        all_nans = [np.nan] * 4
        ua = [np.nan]
        ua_idx = [0]
        ua_inv = [0, 0, 0, 0]
        ua_cnt = [4]
        assert_equal(np.unique(all_nans), ua)
        assert_equal(np.unique(all_nans, return_index=True), (ua, ua_idx))
        assert_equal(np.unique(all_nans, return_inverse=True), (ua, ua_inv))
        assert_equal(np.unique(all_nans, return_counts=True), (ua, ua_cnt))

    def test_unique_zero_sized(self):
        # test for zero-sized arrays
        for dt in self.get_types():
            a = np.array([], dt)
            b = np.array([], dt)
            i1 = np.array([], np.int64)
            i2 = np.array([], np.int64)
            c = np.array([], np.int64)
            self.check_all(a, b, i1, i2, c, dt)

    def test_unique_subclass(self):
        class Subclass(np.ndarray):
            pass

        i1 = [2, 3, 0, 1]
        i2 = [2, 3, 0, 1, 0, 2, 3] * 10
        c = np.multiply([2, 1, 2, 2], 10)

        # test for numeric arrays
        types = self.get_types()
        for dt in types:
            a = np.array([5, 7, 1, 2, 1, 5, 7] * 10, dtype=dt)
            b = np.array([1, 2, 5, 7], dtype=dt)
            aa = Subclass(a.shape, dtype=dt, buffer=a)
            bb = Subclass(b.shape, dtype=dt, buffer=b)
            self.check_all(aa, bb, i1, i2, c, dt)

    @pytest.mark.parametrize("arg", ["return_index", "return_inverse", "return_counts"])
    def test_unsupported_hash_based(self, arg):
        """These currently never use the hash-based solution.  However,
        it seems easier to just allow it.

        When the hash-based solution is added, this test should fail and be
        replaced with something more comprehensive.
        """
        a = np.array([1, 5, 2, 3, 4, 8, 199, 1, 3, 5])

        res_not_sorted = np.unique([1, 1], sorted=False, **{arg: True})
        res_sorted = np.unique([1, 1], sorted=True, **{arg: True})
        # The following should fail without first sorting `res_not_sorted`.
        for arr, expected in zip(res_not_sorted, res_sorted):
            assert_array_equal(arr, expected)

    def test_unique_axis_errors(self):
        assert_raises(TypeError, self._run_axis_tests, object)
        assert_raises(TypeError, self._run_axis_tests,
                      [('a', int), ('b', object)])

        assert_raises(AxisError, unique, np.arange(10), axis=2)
        assert_raises(AxisError, unique, np.arange(10), axis=-2)

    def test_unique_axis_list(self):
        msg = "Unique failed on list of lists"
        inp = [[0, 1, 0], [0, 1, 0]]
        inp_arr = np.asarray(inp)
        assert_array_equal(unique(inp, axis=0), unique(inp_arr, axis=0), msg)
        assert_array_equal(unique(inp, axis=1), unique(inp_arr, axis=1), msg)

    def test_unique_axis(self):
        types = []
        types.extend(np.typecodes['AllInteger'])
        types.extend(np.typecodes['AllFloat'])
        types.append('datetime64[D]')
        types.append('timedelta64[D]')
        types.append([('a', int), ('b', int)])
        types.append([('a', int), ('b', float)])

        for dtype in types:
            self._run_axis_tests(dtype)

        msg = 'Non-bitwise-equal booleans test failed'
        data = np.arange(10, dtype=np.uint8).reshape(-1, 2).view(bool)
        result = np.array([[False, True], [True, True]], dtype=bool)
        assert_array_equal(unique(data, axis=0), result, msg)

        msg = 'Negative zero equality test failed'
        data = np.array([[-0.0, 0.0], [0.0, -0.0], [-0.0, 0.0], [0.0, -0.0]])
        result = np.array([[-0.0, 0.0]])
        assert_array_equal(unique(data, axis=0), result, msg)

    @pytest.mark.parametrize("axis", [0, -1])
    def test_unique_1d_with_axis(self, axis):
        x = np.array([4, 3, 2, 3, 2, 1, 2, 2])
        uniq = unique(x, axis=axis)
        assert_array_equal(uniq, [1, 2, 3, 4])

    @pytest.mark.parametrize("axis", [None, 0, -1])
    def test_unique_inverse_with_axis(self, axis):
        x = np.array([[4, 4, 3], [2, 2, 1], [2, 2, 1], [4, 4, 3]])
        uniq, inv = unique(x, return_inverse=True, axis=axis)
        assert_equal(inv.ndim, x.ndim if axis is None else 1)
        assert_array_equal(x, np.take(uniq, inv, axis=axis))

    def test_unique_axis_zeros(self):
        # issue 15559
        single_zero = np.empty(shape=(2, 0), dtype=np.int8)
        uniq, idx, inv, cnt = unique(single_zero, axis=0, return_index=True,
                                     return_inverse=True, return_counts=True)

        # there's 1 element of shape (0,) along axis 0
        assert_equal(uniq.dtype, single_zero.dtype)
        assert_array_equal(uniq, np.empty(shape=(1, 0)))
        assert_array_equal(idx, np.array([0]))
        assert_array_equal(inv, np.array([0, 0]))
        assert_array_equal(cnt, np.array([2]))

        # there's 0 elements of shape (2,) along axis 1
        uniq, idx, inv, cnt = unique(single_zero, axis=1, return_index=True,
                                     return_inverse=True, return_counts=True)

        assert_equal(uniq.dtype, single_zero.dtype)
        assert_array_equal(uniq, np.empty(shape=(2, 0)))
        assert_array_equal(idx, np.array([]))
        assert_array_equal(inv, np.array([]))
        assert_array_equal(cnt, np.array([]))

        # test a "complicated" shape
        shape = (0, 2, 0, 3, 0, 4, 0)
        multiple_zeros = np.empty(shape=shape)
        for axis in range(len(shape)):
            expected_shape = list(shape)
            if shape[axis] == 0:
                expected_shape[axis] = 0
            else:
                expected_shape[axis] = 1

            assert_array_equal(unique(multiple_zeros, axis=axis),
                               np.empty(shape=expected_shape))

    def test_unique_masked(self):
        # issue 8664
        x = np.array([64, 0, 1, 2, 3, 63, 63, 0, 0, 0, 1, 2, 0, 63, 0],
                     dtype='uint8')
        y = np.ma.masked_equal(x, 0)

        v = np.unique(y)
        v2, i, c = np.unique(y, return_index=True, return_counts=True)

        msg = 'Unique returned different results when asked for index'
        assert_array_equal(v.data, v2.data, msg)
        assert_array_equal(v.mask, v2.mask, msg)

    def test_unique_sort_order_with_axis(self):
        # These tests fail if sorting along axis is done by treating subarrays
        # as unsigned byte strings.  See gh-10495.
        fmt = "sort order incorrect for integer type '%s'"
        for dt in 'bhilq':
            a = np.array([[-1], [0]], dt)
            b = np.unique(a, axis=0)
            assert_array_equal(a, b, fmt % dt)

    def _run_axis_tests(self, dtype):
        data = np.array([[0, 1, 0, 0],
                         [1, 0, 0, 0],
                         [0, 1, 0, 0],
                         [1, 0, 0, 0]]).astype(dtype)

        msg = 'Unique with 1d array and axis=0 failed'
        result = np.array([0, 1])
        assert_array_equal(unique(data), result.astype(dtype), msg)

        msg = 'Unique with 2d array and axis=0 failed'
        result = np.array([[0, 1, 0, 0], [1, 0, 0, 0]])
        assert_array_equal(unique(data, axis=0), result.astype(dtype), msg)

        msg = 'Unique with 2d array and axis=1 failed'
        result = np.array([[0, 0, 1], [0, 1, 0], [0, 0, 1], [0, 1, 0]])
        assert_array_equal(unique(data, axis=1), result.astype(dtype), msg)

        msg = 'Unique with 3d array and axis=2 failed'
        data3d = np.array([[[1, 1],
                            [1, 0]],
                           [[0, 1],
                            [0, 0]]]).astype(dtype)
        result = np.take(data3d, [1, 0], axis=2)
        assert_array_equal(unique(data3d, axis=2), result, msg)

        uniq, idx, inv, cnt = unique(data, axis=0, return_index=True,
                                     return_inverse=True, return_counts=True)
        msg = "Unique's return_index=True failed with axis=0"
        assert_array_equal(data[idx], uniq, msg)
        msg = "Unique's return_inverse=True failed with axis=0"
        assert_array_equal(np.take(uniq, inv, axis=0), data)
        msg = "Unique's return_counts=True failed with axis=0"
        assert_array_equal(cnt, np.array([2, 2]), msg)

        uniq, idx, inv, cnt = unique(data, axis=1, return_index=True,
                                     return_inverse=True, return_counts=True)
        msg = "Unique's return_index=True failed with axis=1"
        assert_array_equal(data[:, idx], uniq)
        msg = "Unique's return_inverse=True failed with axis=1"
        assert_array_equal(np.take(uniq, inv, axis=1), data)
        msg = "Unique's return_counts=True failed with axis=1"
        assert_array_equal(cnt, np.array([2, 1, 1]), msg)

    def test_unique_nanequals(self):
        # issue 20326
        a = np.array([1, 1, np.nan, np.nan, np.nan])
        unq = np.unique(a)
        not_unq = np.unique(a, equal_nan=False)
        assert_array_equal(unq, np.array([1, np.nan]))
        assert_array_equal(not_unq, np.array([1, np.nan, np.nan, np.nan]))

    def test_unique_array_api_functions(self):
        arr = np.array([np.nan, 1, 4, 1, 3, 4, np.nan, 5, 1])

        for res_unique_array_api, res_unique in [
            (
                np.unique_values(arr),
                np.unique(arr, equal_nan=False)
            ),
            (
                np.unique_counts(arr),
                np.unique(arr, return_counts=True, equal_nan=False)
            ),
            (
                np.unique_inverse(arr),
                np.unique(arr, return_inverse=True, equal_nan=False)
            ),
            (
                np.unique_all(arr),
                np.unique(
                    arr,
                    return_index=True,
                    return_inverse=True,
                    return_counts=True,
                    equal_nan=False
                )
            )
        ]:
            assert len(res_unique_array_api) == len(res_unique)
            for actual, expected in zip(res_unique_array_api, res_unique):
                assert_array_equal(actual, expected)

    def test_unique_inverse_shape(self):
        # Regression test for https://github.com/numpy/numpy/issues/25552
        arr = np.array([[1, 2, 3], [2, 3, 1]])
        expected_values, expected_inverse = np.unique(arr, return_inverse=True)
        expected_inverse = expected_inverse.reshape(arr.shape)
        for func in np.unique_inverse, np.unique_all:
            result = func(arr)
            assert_array_equal(expected_values, result.values)
            assert_array_equal(expected_inverse, result.inverse_indices)
            assert_array_equal(arr, result.values[result.inverse_indices])

    @pytest.mark.parametrize(
        'data',
        [[[1, 1, 1],
          [1, 1, 1]],
         [1, 3, 2],
         1],
    )
    @pytest.mark.parametrize('transpose', [False, True])
    @pytest.mark.parametrize('dtype', [np.int32, np.float64])
    def test_unique_with_matrix(self, data, transpose, dtype):
        mat = np.matrix(data).astype(dtype)
        if transpose:
            mat = mat.T
        u = np.unique(mat)
        expected = np.unique(np.asarray(mat))
        assert_array_equal(u, expected, strict=True)

# === NexusCore/openenv\Lib\site-packages\win32\lib\win32serviceutil.py ===
# General purpose service utilities, both for standard Python scripts,
# and for for Python programs which run as services...
#
# Note that most utility functions here will raise win32api.error's
# (which is win32service.error, pywintypes.error, etc)
# when things go wrong - eg, not enough permissions to hit the
# registry etc.

import importlib.machinery
import os
import sys
import warnings

import pywintypes
import win32api
import win32con
import win32service
import winerror

error = RuntimeError  # Re-exported alias


# Returns the full path to an executable for hosting a Python service - typically
# 'pythonservice.exe'
# * If you pass a param and it exists as a file, you'll get the abs path back
# * Otherwise we'll use the param instead of 'pythonservice.exe', and we will
#   look for it.
def LocatePythonServiceExe(exe=None):
    if not exe and hasattr(sys, "frozen"):
        # If py2exe etc calls this with no exe, default is current exe,
        # and all setup is their problem :)
        return sys.executable

    if exe and os.path.isfile(exe):
        return win32api.GetFullPathName(exe)

    suffix = "_d" if "_d.pyd" in importlib.machinery.EXTENSION_SUFFIXES else ""

    # We are confused if we aren't now looking for our default. But if that
    # exists as specified we assume it's good.
    exe = f"pythonservice{suffix}.exe"
    if os.path.isfile(exe):
        return win32api.GetFullPathName(exe)

    # Now we are searching for the .exe
    # We are going to want it here.
    correct = os.path.join(sys.exec_prefix, exe)
    # Even if that file already exists, we copy the one installed by pywin32
    # in-case it was upgraded.
    # pywin32 installed it next to win32service.pyd (but we can't run it from there)
    maybe = os.path.join(os.path.dirname(win32service.__file__), exe)
    if os.path.exists(maybe):
        print(f"moving host exe '{maybe}' -> '{correct}'")
        # Handle case where MoveFile() fails. Particularly if destination file
        # has a resource lock and can't be replaced by src file
        try:
            win32api.MoveFileEx(maybe, correct, win32con.MOVEFILE_REPLACE_EXISTING)
        except win32api.error as exc:
            print(f"Failed to move host exe '{exc}'")

    if not os.path.exists(correct):
        raise error(f"Can't find '{correct}'")

    # If pywintypes.dll isn't next to us, or at least next to pythonXX.dll,
    # there's a good chance the service will not run. That's usually copied by
    # `pywin32_postinstall`, but putting it next to the python DLL seems reasonable.
    # (Unlike the .exe above, we don't unconditionally copy this, and possibly
    # copy it to a different place. Doesn't seem a good reason for that!?)
    python_dll = win32api.GetModuleFileName(sys.dllhandle)
    pyw = f"pywintypes{sys.version_info.major}{sys.version_info.minor}{suffix}.dll"
    correct_pyw = os.path.join(os.path.dirname(python_dll), pyw)

    if not os.path.exists(correct_pyw):
        print(f"copying helper dll '{pywintypes.__file__}' -> '{correct_pyw}'")
        win32api.CopyFile(pywintypes.__file__, correct_pyw)

    return correct


def _GetServiceShortName(longName):
    # looks up a services name
    # from the display name
    # Thanks to Andy McKay for this code.
    access = (
        win32con.KEY_READ | win32con.KEY_ENUMERATE_SUB_KEYS | win32con.KEY_QUERY_VALUE
    )
    hkey = win32api.RegOpenKey(
        win32con.HKEY_LOCAL_MACHINE, "SYSTEM\\CurrentControlSet\\Services", 0, access
    )
    num = win32api.RegQueryInfoKey(hkey)[0]
    longName = longName.lower()
    # loop through number of subkeys
    for x in range(0, num):
        # find service name, open subkey
        svc = win32api.RegEnumKey(hkey, x)
        skey = win32api.RegOpenKey(hkey, svc, 0, access)
        try:
            # find display name
            thisName = str(win32api.RegQueryValueEx(skey, "DisplayName")[0])
            if thisName.lower() == longName:
                return svc
        except win32api.error:
            # in case there is no key called DisplayName
            pass
    return None


# Open a service given either it's long or short name.
def SmartOpenService(hscm, name, access):
    try:
        return win32service.OpenService(hscm, name, access)
    except win32api.error as details:
        if details.winerror not in [
            winerror.ERROR_SERVICE_DOES_NOT_EXIST,
            winerror.ERROR_INVALID_NAME,
        ]:
            raise
    name = win32service.GetServiceKeyName(hscm, name)
    return win32service.OpenService(hscm, name, access)


def LocateSpecificServiceExe(serviceName):
    # Return the .exe name of any service.
    hkey = win32api.RegOpenKey(
        win32con.HKEY_LOCAL_MACHINE,
        "SYSTEM\\CurrentControlSet\\Services\\%s" % (serviceName),
        0,
        win32con.KEY_QUERY_VALUE,
    )
    try:
        return win32api.RegQueryValueEx(hkey, "ImagePath")[0]
    finally:
        hkey.Close()


def InstallPerfmonForService(serviceName, iniName, dllName=None):
    # If no DLL name, look it up in the INI file name
    if not dllName:  # May be empty string!
        dllName = win32api.GetProfileVal("Python", "dll", "", iniName)
    # Still not found - look for the standard one in the same dir as win32service.pyd
    if not dllName:
        try:
            tryName = os.path.join(
                os.path.split(win32service.__file__)[0], "perfmondata.dll"
            )
            if os.path.isfile(tryName):
                dllName = tryName
        except AttributeError:
            # Frozen app? - anyway, can't find it!
            pass
    if not dllName:
        raise ValueError("The name of the performance DLL must be available")
    dllName = win32api.GetFullPathName(dllName)
    # Now setup all the required "Performance" entries.
    hkey = win32api.RegOpenKey(
        win32con.HKEY_LOCAL_MACHINE,
        "SYSTEM\\CurrentControlSet\\Services\\%s" % (serviceName),
        0,
        win32con.KEY_ALL_ACCESS,
    )
    try:
        subKey = win32api.RegCreateKey(hkey, "Performance")
        try:
            win32api.RegSetValueEx(subKey, "Library", 0, win32con.REG_SZ, dllName)
            win32api.RegSetValueEx(
                subKey, "Open", 0, win32con.REG_SZ, "OpenPerformanceData"
            )
            win32api.RegSetValueEx(
                subKey, "Close", 0, win32con.REG_SZ, "ClosePerformanceData"
            )
            win32api.RegSetValueEx(
                subKey, "Collect", 0, win32con.REG_SZ, "CollectPerformanceData"
            )
        finally:
            win32api.RegCloseKey(subKey)
    finally:
        win32api.RegCloseKey(hkey)
    # Now do the "Lodctr" thang...

    try:
        import perfmon

        path, fname = os.path.split(iniName)
        oldPath = os.getcwd()
        if path:
            os.chdir(path)
        try:
            perfmon.LoadPerfCounterTextStrings("python.exe " + fname)
        finally:
            os.chdir(oldPath)
    except win32api.error as details:
        print("The service was installed OK, but the performance monitor")
        print("data could not be loaded.", details)


def _GetCommandLine(exeName, exeArgs):
    if exeArgs is not None:
        return exeName + " " + exeArgs
    else:
        return exeName


def InstallService(
    pythonClassString,
    serviceName,
    displayName,
    startType=None,
    errorControl=None,
    bRunInteractive=0,
    serviceDeps=None,
    userName=None,
    password=None,
    exeName=None,
    perfMonIni=None,
    perfMonDll=None,
    exeArgs=None,
    description=None,
    delayedstart=None,
):
    # Handle the default arguments.
    if startType is None:
        startType = win32service.SERVICE_DEMAND_START
    serviceType = win32service.SERVICE_WIN32_OWN_PROCESS
    if bRunInteractive:
        serviceType |= win32service.SERVICE_INTERACTIVE_PROCESS
    if errorControl is None:
        errorControl = win32service.SERVICE_ERROR_NORMAL

    exeName = '"%s"' % LocatePythonServiceExe(exeName)
    commandLine = _GetCommandLine(exeName, exeArgs)
    hscm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ALL_ACCESS)
    try:
        hs = win32service.CreateService(
            hscm,
            serviceName,
            displayName,
            win32service.SERVICE_ALL_ACCESS,  # desired access
            serviceType,  # service type
            startType,
            errorControl,  # error control type
            commandLine,
            None,
            0,
            serviceDeps,
            userName,
            password,
        )
        if description is not None:
            try:
                win32service.ChangeServiceConfig2(
                    hs, win32service.SERVICE_CONFIG_DESCRIPTION, description
                )
            except NotImplementedError:
                pass  ## ChangeServiceConfig2 and description do not exist on NT
        if delayedstart is not None:
            try:
                win32service.ChangeServiceConfig2(
                    hs,
                    win32service.SERVICE_CONFIG_DELAYED_AUTO_START_INFO,
                    delayedstart,
                )
            except (win32service.error, NotImplementedError):
                ## delayed start only exists on Vista and later - warn only when trying to set delayed to True
                warnings.warn("Delayed Start not available on this system")
        win32service.CloseServiceHandle(hs)
    finally:
        win32service.CloseServiceHandle(hscm)
    InstallPythonClassString(pythonClassString, serviceName)
    # If I have performance monitor info to install, do that.
    if perfMonIni is not None:
        InstallPerfmonForService(serviceName, perfMonIni, perfMonDll)


def ChangeServiceConfig(
    pythonClassString,
    serviceName,
    startType=None,
    errorControl=None,
    bRunInteractive=0,
    serviceDeps=None,
    userName=None,
    password=None,
    exeName=None,
    displayName=None,
    perfMonIni=None,
    perfMonDll=None,
    exeArgs=None,
    description=None,
    delayedstart=None,
):
    # Before doing anything, remove any perfmon counters.
    try:
        import perfmon

        perfmon.UnloadPerfCounterTextStrings("python.exe " + serviceName)
    except (ImportError, win32api.error):
        pass

    # The EXE location may have changed
    exeName = '"%s"' % LocatePythonServiceExe(exeName)

    # Handle the default arguments.
    if startType is None:
        startType = win32service.SERVICE_NO_CHANGE
    if errorControl is None:
        errorControl = win32service.SERVICE_NO_CHANGE

    hscm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ALL_ACCESS)
    serviceType = win32service.SERVICE_WIN32_OWN_PROCESS
    if bRunInteractive:
        serviceType |= win32service.SERVICE_INTERACTIVE_PROCESS
    commandLine = _GetCommandLine(exeName, exeArgs)
    try:
        hs = SmartOpenService(hscm, serviceName, win32service.SERVICE_ALL_ACCESS)
        try:
            win32service.ChangeServiceConfig(
                hs,
                serviceType,  # service type
                startType,
                errorControl,  # error control type
                commandLine,
                None,
                0,
                serviceDeps,
                userName,
                password,
                displayName,
            )
            if description is not None:
                try:
                    win32service.ChangeServiceConfig2(
                        hs, win32service.SERVICE_CONFIG_DESCRIPTION, description
                    )
                except NotImplementedError:
                    pass  ## ChangeServiceConfig2 and description do not exist on NT
            if delayedstart is not None:
                try:
                    win32service.ChangeServiceConfig2(
                        hs,
                        win32service.SERVICE_CONFIG_DELAYED_AUTO_START_INFO,
                        delayedstart,
                    )
                except (win32service.error, NotImplementedError):
                    ## Delayed start only exists on Vista and later.  On Nt, will raise NotImplementedError since ChangeServiceConfig2
                    ## doensn't exist.  On Win2k and XP, will fail with ERROR_INVALID_LEVEL
                    ## Warn only if trying to set delayed to True
                    if delayedstart:
                        warnings.warn("Delayed Start not available on this system")
        finally:
            win32service.CloseServiceHandle(hs)
    finally:
        win32service.CloseServiceHandle(hscm)
    InstallPythonClassString(pythonClassString, serviceName)
    # If I have performance monitor info to install, do that.
    if perfMonIni is not None:
        InstallPerfmonForService(serviceName, perfMonIni, perfMonDll)


def InstallPythonClassString(pythonClassString, serviceName):
    # Now setup our Python specific entries.
    if pythonClassString:
        key = win32api.RegCreateKey(
            win32con.HKEY_LOCAL_MACHINE,
            "System\\CurrentControlSet\\Services\\%s\\PythonClass" % serviceName,
        )
        try:
            win32api.RegSetValue(key, None, win32con.REG_SZ, pythonClassString)
        finally:
            win32api.RegCloseKey(key)


# Utility functions for Services, to allow persistant properties.
def SetServiceCustomOption(serviceName, option, value):
    try:
        serviceName = serviceName._svc_name_
    except AttributeError:
        pass
    key = win32api.RegCreateKey(
        win32con.HKEY_LOCAL_MACHINE,
        "System\\CurrentControlSet\\Services\\%s\\Parameters" % serviceName,
    )
    try:
        if isinstance(value, int):
            win32api.RegSetValueEx(key, option, 0, win32con.REG_DWORD, value)
        else:
            win32api.RegSetValueEx(key, option, 0, win32con.REG_SZ, value)
    finally:
        win32api.RegCloseKey(key)


def GetServiceCustomOption(serviceName, option, defaultValue=None):
    # First param may also be a service class/instance.
    # This allows services to pass "self"
    try:
        serviceName = serviceName._svc_name_
    except AttributeError:
        pass
    key = win32api.RegCreateKey(
        win32con.HKEY_LOCAL_MACHINE,
        "System\\CurrentControlSet\\Services\\%s\\Parameters" % serviceName,
    )
    try:
        try:
            return win32api.RegQueryValueEx(key, option)[0]
        except win32api.error:  # No value.
            return defaultValue
    finally:
        win32api.RegCloseKey(key)


def RemoveService(serviceName):
    try:
        import perfmon

        perfmon.UnloadPerfCounterTextStrings("python.exe " + serviceName)
    except (ImportError, win32api.error):
        pass

    hscm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ALL_ACCESS)
    try:
        hs = SmartOpenService(hscm, serviceName, win32service.SERVICE_ALL_ACCESS)
        win32service.DeleteService(hs)
        win32service.CloseServiceHandle(hs)
    finally:
        win32service.CloseServiceHandle(hscm)

    import win32evtlogutil

    try:
        win32evtlogutil.RemoveSourceFromRegistry(serviceName)
    except win32api.error:
        pass


def ControlService(serviceName, code, machine=None):
    hscm = win32service.OpenSCManager(machine, None, win32service.SC_MANAGER_ALL_ACCESS)
    try:
        hs = SmartOpenService(hscm, serviceName, win32service.SERVICE_ALL_ACCESS)
        try:
            status = win32service.ControlService(hs, code)
        finally:
            win32service.CloseServiceHandle(hs)
    finally:
        win32service.CloseServiceHandle(hscm)
    return status


def __FindSvcDeps(findName):
    dict = {}
    k = win32api.RegOpenKey(
        win32con.HKEY_LOCAL_MACHINE, "SYSTEM\\CurrentControlSet\\Services"
    )
    num = 0
    while 1:
        try:
            svc = win32api.RegEnumKey(k, num)
        except win32api.error:
            break
        num += 1
        sk = win32api.RegOpenKey(k, svc)
        try:
            deps, typ = win32api.RegQueryValueEx(sk, "DependOnService")
        except win32api.error:
            deps = ()
        for dep in deps:
            dep = dep.lower()
            dep_on = dict.get(dep, [])
            dep_on.append(svc)
            dict[dep] = dep_on

    return __ResolveDeps(findName, dict)


def __ResolveDeps(findName, dict):
    items = dict.get(findName.lower(), [])
    retList = []
    for svc in items:
        retList.insert(0, svc)
        retList = __ResolveDeps(svc, dict) + retList
    return retList


def WaitForServiceStatus(serviceName, status, waitSecs, machine=None):
    """Waits for the service to return the specified status.  You
    should have already requested the service to enter that state"""
    for i in range(waitSecs * 4):
        now_status = QueryServiceStatus(serviceName, machine)[1]
        if now_status == status:
            break
        win32api.Sleep(250)
    else:
        raise pywintypes.error(
            winerror.ERROR_SERVICE_REQUEST_TIMEOUT,
            "QueryServiceStatus",
            win32api.FormatMessage(winerror.ERROR_SERVICE_REQUEST_TIMEOUT)[:-2],
        )


def __StopServiceWithTimeout(hs, waitSecs=30):
    try:
        status = win32service.ControlService(hs, win32service.SERVICE_CONTROL_STOP)
    except pywintypes.error as exc:
        if exc.winerror != winerror.ERROR_SERVICE_NOT_ACTIVE:
            raise
    for i in range(waitSecs):
        status = win32service.QueryServiceStatus(hs)
        if status[1] == win32service.SERVICE_STOPPED:
            break
        win32api.Sleep(1000)
    else:
        raise pywintypes.error(
            winerror.ERROR_SERVICE_REQUEST_TIMEOUT,
            "ControlService",
            win32api.FormatMessage(winerror.ERROR_SERVICE_REQUEST_TIMEOUT)[:-2],
        )


def StopServiceWithDeps(serviceName, machine=None, waitSecs=30):
    # Stop a service recursively looking for dependant services
    hscm = win32service.OpenSCManager(machine, None, win32service.SC_MANAGER_ALL_ACCESS)
    try:
        deps = __FindSvcDeps(serviceName)
        for dep in deps:
            hs = win32service.OpenService(hscm, dep, win32service.SERVICE_ALL_ACCESS)
            try:
                __StopServiceWithTimeout(hs, waitSecs)
            finally:
                win32service.CloseServiceHandle(hs)
        # Now my service!
        hs = win32service.OpenService(
            hscm, serviceName, win32service.SERVICE_ALL_ACCESS
        )
        try:
            __StopServiceWithTimeout(hs, waitSecs)
        finally:
            win32service.CloseServiceHandle(hs)

    finally:
        win32service.CloseServiceHandle(hscm)


def StopService(serviceName, machine=None):
    return ControlService(serviceName, win32service.SERVICE_CONTROL_STOP, machine)


def StartService(serviceName, args=None, machine=None):
    hscm = win32service.OpenSCManager(machine, None, win32service.SC_MANAGER_ALL_ACCESS)
    try:
        hs = SmartOpenService(hscm, serviceName, win32service.SERVICE_ALL_ACCESS)
        try:
            win32service.StartService(hs, args)
        finally:
            win32service.CloseServiceHandle(hs)
    finally:
        win32service.CloseServiceHandle(hscm)


def RestartService(serviceName, args=None, waitSeconds=30, machine=None):
    "Stop the service, and then start it again (with some tolerance for allowing it to stop.)"
    try:
        StopService(serviceName, machine)
    except pywintypes.error as exc:
        # Allow only "service not running" error
        if exc.winerror != winerror.ERROR_SERVICE_NOT_ACTIVE:
            raise
    # Give it a few goes, as the service may take time to stop
    for i in range(waitSeconds):
        try:
            StartService(serviceName, args, machine)
            break
        except pywintypes.error as exc:
            if exc.winerror != winerror.ERROR_SERVICE_ALREADY_RUNNING:
                raise
            win32api.Sleep(1000)
    else:
        print("Gave up waiting for the old service to stop!")


def _DebugCtrlHandler(evt):
    if evt in (win32con.CTRL_C_EVENT, win32con.CTRL_BREAK_EVENT):
        assert g_debugService
        print("Stopping debug service.")
        g_debugService.SvcStop()
        return True
    return False


def DebugService(cls, argv=[]):
    # Run a service in "debug" mode.  Re-implements what pythonservice.exe
    # does when it sees a "-debug" param.
    # Currently only used by "frozen" (ie, py2exe) programs (but later may
    # end up being used for all services should we ever remove
    # pythonservice.exe)
    import servicemanager

    global g_debugService

    print(f"Debugging service {cls._svc_name_} - press Ctrl+C to stop.")
    servicemanager.Debugging(True)
    servicemanager.PrepareToHostSingle(cls)
    g_debugService = cls(argv)
    # Setup a ctrl+c handler to simulate a "stop"
    win32api.SetConsoleCtrlHandler(_DebugCtrlHandler, True)
    try:
        g_debugService.SvcRun()
    finally:
        win32api.SetConsoleCtrlHandler(_DebugCtrlHandler, False)
        servicemanager.Debugging(False)
        g_debugService = None


def GetServiceClassString(cls, argv=None):
    if argv is None:
        argv = sys.argv
    import pickle

    modName = pickle.whichmodule(cls, cls.__name__)
    if modName == "__main__":
        try:
            fname = win32api.GetFullPathName(argv[0])
            path = os.path.split(fname)[0]
            # Eaaaahhhh - sometimes this will be a short filename, which causes
            # problems with 1.5.1 and the silly filename case rule.
            filelist = win32api.FindFiles(fname)
            # win32api.FindFiles will not detect files in a zip or exe. If list is empty,
            # skip the test and hope the file really exists.
            if len(filelist) != 0:
                # Get the long name
                fname = os.path.join(path, filelist[0][8])
        except win32api.error:
            raise error(
                "Could not resolve the path name '%s' to a full path" % (argv[0])
            )
        modName = os.path.splitext(fname)[0]
    return modName + "." + cls.__name__


def QueryServiceStatus(serviceName, machine=None):
    hscm = win32service.OpenSCManager(machine, None, win32service.SC_MANAGER_CONNECT)
    try:
        hs = SmartOpenService(hscm, serviceName, win32service.SERVICE_QUERY_STATUS)
        try:
            status = win32service.QueryServiceStatus(hs)
        finally:
            win32service.CloseServiceHandle(hs)
    finally:
        win32service.CloseServiceHandle(hscm)
    return status


def usage():
    try:
        fname = os.path.split(sys.argv[0])[1]
    except:
        fname = sys.argv[0]
    print(
        "Usage: '%s [options] install|update|remove|start [...]|stop|restart [...]|debug [...]'"
        % fname
    )
    print("Options for 'install' and 'update' commands only:")
    print(" --username domain\\username : The Username the service is to run under")
    print(" --password password : The password for the username")
    print(
        " --startup [manual|auto|disabled|delayed] : How the service starts, default = manual"
    )
    print(" --interactive : Allow the service to interact with the desktop.")
    print(
        " --perfmonini file: .ini file to use for registering performance monitor data"
    )
    print(" --perfmondll file: .dll file to use when querying the service for")
    print("   performance data, default = perfmondata.dll")
    print("Options for 'start' and 'stop' commands only:")
    print(" --wait seconds: Wait for the service to actually start or stop.")
    print("                 If you specify --wait with the 'stop' option, the service")
    print("                 and all dependent services will be stopped, each waiting")
    print("                 the specified period.")
    sys.exit(1)


def HandleCommandLine(
    cls,
    serviceClassString=None,
    argv=None,
    customInstallOptions="",
    customOptionHandler=None,
):
    """Utility function allowing services to process the command line.

    Allows standard commands such as 'start', 'stop', 'debug', 'install' etc.

    Install supports 'standard' command line options prefixed with '--', such as
    --username, --password, etc.  In addition,
    the function allows custom command line options to be handled by the calling function.
    """
    err = 0

    if argv is None:
        argv = sys.argv

    if len(argv) <= 1:
        usage()

    serviceName = cls._svc_name_
    serviceDisplayName = cls._svc_display_name_
    if serviceClassString is None:
        serviceClassString = GetServiceClassString(cls)

    # Pull apart the command line
    import getopt

    try:
        opts, args = getopt.getopt(
            argv[1:],
            customInstallOptions,
            [
                "password=",
                "username=",
                "startup=",
                "perfmonini=",
                "perfmondll=",
                "interactive",
                "wait=",
            ],
        )
    except getopt.error as details:
        print(details)
        usage()
    userName = None
    password = None
    perfMonIni = perfMonDll = None
    startup = None
    delayedstart = None
    interactive = None
    waitSecs = 0
    for opt, val in opts:
        if opt == "--username":
            userName = val
        elif opt == "--password":
            password = val
        elif opt == "--perfmonini":
            perfMonIni = val
        elif opt == "--perfmondll":
            perfMonDll = val
        elif opt == "--interactive":
            interactive = 1
        elif opt == "--startup":
            map = {
                "manual": win32service.SERVICE_DEMAND_START,
                "auto": win32service.SERVICE_AUTO_START,
                "delayed": win32service.SERVICE_AUTO_START,  ## ChangeServiceConfig2 called later
                "disabled": win32service.SERVICE_DISABLED,
            }
            startup = map.get(val.lower())
            if not startup:
                print(f"{val!r} is not a valid startup option")
            if val.lower() == "delayed":
                delayedstart = True
            elif val.lower() == "auto":
                delayedstart = False
            ## else no change
        elif opt == "--wait":
            try:
                waitSecs = int(val)
            except ValueError:
                print("--wait must specify an integer number of seconds.")
                usage()

    arg = args[0]
    knownArg = 0
    # First we process all arguments which pass additional args on
    if arg == "start":
        knownArg = 1
        print("Starting service %s" % (serviceName))
        try:
            StartService(serviceName, args[1:])
            if waitSecs:
                WaitForServiceStatus(
                    serviceName, win32service.SERVICE_RUNNING, waitSecs
                )
        except win32service.error as exc:
            print("Error starting service: %s" % exc.strerror)
            err = exc.winerror

    elif arg == "restart":
        knownArg = 1
        print("Restarting service %s" % (serviceName))
        RestartService(serviceName, args[1:])
        if waitSecs:
            WaitForServiceStatus(serviceName, win32service.SERVICE_RUNNING, waitSecs)

    elif arg == "debug":
        knownArg = 1
        if not hasattr(sys, "frozen"):
            # non-frozen services use pythonservice.exe which handles a
            # -debug option
            svcArgs = " ".join(args[1:])
            try:
                exeName = LocateSpecificServiceExe(serviceName)
            except win32api.error as exc:
                if exc.winerror == winerror.ERROR_FILE_NOT_FOUND:
                    print("The service does not appear to be installed.")
                    print("Please install the service before debugging it.")
                    sys.exit(1)
                raise
            try:
                os.system(f"{exeName} -debug {serviceName} {svcArgs}")
            # ^C is used to kill the debug service.  Sometimes Python also gets
            # interrupted - ignore it...
            except KeyboardInterrupt:
                pass
        else:
            # py2exe services don't use pythonservice - so we simulate
            # debugging here.
            DebugService(cls, args)

    if not knownArg and len(args) != 1:
        usage()  # the rest of the cmds don't take addn args

    if arg == "install":
        knownArg = 1
        try:
            serviceDeps = cls._svc_deps_
        except AttributeError:
            serviceDeps = None
        try:
            exeName = cls._exe_name_
        except AttributeError:
            exeName = None  # Default to PythonService.exe
        try:
            exeArgs = cls._exe_args_
        except AttributeError:
            exeArgs = None
        try:
            description = cls._svc_description_
        except AttributeError:
            description = None
        print(f"Installing service {serviceName}")
        # Note that we install the service before calling the custom option
        # handler, so if the custom handler fails, we have an installed service (from NT's POV)
        # but is unlikely to work, as the Python code controlling it failed.  Therefore
        # we remove the service if the first bit works, but the second doesn't!
        try:
            InstallService(
                serviceClassString,
                serviceName,
                serviceDisplayName,
                serviceDeps=serviceDeps,
                startType=startup,
                bRunInteractive=interactive,
                userName=userName,
                password=password,
                exeName=exeName,
                perfMonIni=perfMonIni,
                perfMonDll=perfMonDll,
                exeArgs=exeArgs,
                description=description,
                delayedstart=delayedstart,
            )
            if customOptionHandler:
                customOptionHandler(*(opts,))
            print("Service installed")
        except win32service.error as exc:
            if exc.winerror == winerror.ERROR_SERVICE_EXISTS:
                arg = "update"  # Fall through to the "update" param!
            else:
                print(
                    "Error installing service: %s (%d)" % (exc.strerror, exc.winerror)
                )
                err = exc.winerror
        except ValueError as msg:  # Can be raised by custom option handler.
            print("Error installing service: %s" % str(msg))
            err = -1
            # xxx - maybe I should remove after _any_ failed install - however,
            # xxx - it may be useful to help debug to leave the service as it failed.
            # xxx - We really _must_ remove as per the comments above...
            # As we failed here, remove the service, so the next installation
            # attempt works.
            try:
                RemoveService(serviceName)
            except win32api.error:
                print("Warning - could not remove the partially installed service.")

    if arg == "update":
        knownArg = 1
        try:
            serviceDeps = cls._svc_deps_
        except AttributeError:
            serviceDeps = None
        try:
            exeName = cls._exe_name_
        except AttributeError:
            exeName = None  # Default to PythonService.exe
        try:
            exeArgs = cls._exe_args_
        except AttributeError:
            exeArgs = None
        try:
            description = cls._svc_description_
        except AttributeError:
            description = None
        print("Changing service configuration")
        try:
            ChangeServiceConfig(
                serviceClassString,
                serviceName,
                serviceDeps=serviceDeps,
                startType=startup,
                bRunInteractive=interactive,
                userName=userName,
                password=password,
                exeName=exeName,
                displayName=serviceDisplayName,
                perfMonIni=perfMonIni,
                perfMonDll=perfMonDll,
                exeArgs=exeArgs,
                description=description,
                delayedstart=delayedstart,
            )
            if customOptionHandler:
                customOptionHandler(*(opts,))
            print("Service updated")
        except win32service.error as exc:
            print(
                "Error changing service configuration: %s (%d)"
                % (exc.strerror, exc.winerror)
            )
            err = exc.winerror

    elif arg == "remove":
        knownArg = 1
        print("Removing service %s" % (serviceName))
        try:
            RemoveService(serviceName)
            print("Service removed")
        except win32service.error as exc:
            print("Error removing service: %s (%d)" % (exc.strerror, exc.winerror))
            err = exc.winerror
    elif arg == "stop":
        knownArg = 1
        print("Stopping service %s" % (serviceName))
        try:
            if waitSecs:
                StopServiceWithDeps(serviceName, waitSecs=waitSecs)
            else:
                StopService(serviceName)
        except win32service.error as exc:
            print("Error stopping service: %s (%d)" % (exc.strerror, exc.winerror))
            err = exc.winerror
    if not knownArg:
        err = -1
        print("Unknown command - '%s'" % arg)
        usage()
    return err


#
# Useful base class to build services from.
#
class ServiceFramework:
    # Required Attributes:
    # _svc_name_ = The service name
    # _svc_display_name_ = The service display name

    # Optional Attributes:
    _svc_deps_ = None  # sequence of service names on which this depends
    _exe_name_ = None  # Default to PythonService.exe
    _exe_args_ = None  # Default to no arguments
    _svc_description_ = (
        None  # Only exists on Windows 2000 or later, ignored on windows NT
    )

    def __init__(self, args):
        import servicemanager

        self.ssh = servicemanager.RegisterServiceCtrlHandler(
            args[0], self.ServiceCtrlHandlerEx, True
        )
        servicemanager.SetEventSourceName(self._svc_name_)
        self.checkPoint = 0

    def GetAcceptedControls(self):
        # Setup the service controls we accept based on our attributes. Note
        # that if you need to handle controls via SvcOther[Ex](), you must
        # override this.
        accepted = 0
        if hasattr(self, "SvcStop"):
            accepted |= win32service.SERVICE_ACCEPT_STOP
        if hasattr(self, "SvcPause") and hasattr(self, "SvcContinue"):
            accepted |= win32service.SERVICE_ACCEPT_PAUSE_CONTINUE
        if hasattr(self, "SvcShutdown"):
            accepted |= win32service.SERVICE_ACCEPT_SHUTDOWN
        return accepted

    def ReportServiceStatus(
        self, serviceStatus, waitHint=5000, win32ExitCode=0, svcExitCode=0
    ):
        if self.ssh is None:  # Debugging!
            return
        if serviceStatus == win32service.SERVICE_START_PENDING:
            accepted = 0
        else:
            accepted = self.GetAcceptedControls()

        if serviceStatus in [
            win32service.SERVICE_RUNNING,
            win32service.SERVICE_STOPPED,
        ]:
            checkPoint = 0
        else:
            self.checkPoint += 1
            checkPoint = self.checkPoint

        # Now report the status to the control manager
        status = (
            win32service.SERVICE_WIN32_OWN_PROCESS,
            serviceStatus,
            accepted,  # dwControlsAccepted,
            win32ExitCode,  # dwWin32ExitCode;
            svcExitCode,  # dwServiceSpecificExitCode;
            checkPoint,  # dwCheckPoint;
            waitHint,
        )
        win32service.SetServiceStatus(self.ssh, status)

    def SvcInterrogate(self):
        # Assume we are running, and everyone is happy.
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)

    def SvcOther(self, control):
        try:
            print("Unknown control status - %d" % control)
        except OSError:
            # services may not have a valid stdout!
            pass

    def ServiceCtrlHandler(self, control):
        return self.ServiceCtrlHandlerEx(control, 0, None)

    # The 'Ex' functions, which take additional params
    def SvcOtherEx(self, control, event_type, data):
        # The default here is to call self.SvcOther as that is the old behaviour.
        # If you want to take advantage of the extra data, override this method
        return self.SvcOther(control)

    def ServiceCtrlHandlerEx(self, control, event_type, data):
        if control == win32service.SERVICE_CONTROL_STOP:
            return self.SvcStop()
        elif control == win32service.SERVICE_CONTROL_PAUSE:
            return self.SvcPause()
        elif control == win32service.SERVICE_CONTROL_CONTINUE:
            return self.SvcContinue()
        elif control == win32service.SERVICE_CONTROL_INTERROGATE:
            return self.SvcInterrogate()
        elif control == win32service.SERVICE_CONTROL_SHUTDOWN:
            return self.SvcShutdown()
        else:
            return self.SvcOtherEx(control, event_type, data)

    def SvcRun(self):
        # This is the entry point the C framework calls when the Service is
        # started. Your Service class should implement SvcDoRun().
        # Or you can override this method for more control over the Service
        # statuses reported to the SCM.

        # If this method raises an exception, the C framework will detect this
        # and report a SERVICE_STOPPED status with a non-zero error code.

        self.ReportServiceStatus(win32service.SERVICE_RUNNING)
        self.SvcDoRun()
        # Once SvcDoRun terminates, the service has stopped.
        # We tell the SCM the service is still stopping - the C framework
        # will automatically tell the SCM it has stopped when this returns.
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\win32\lib\win32serviceutil.py ===
# General purpose service utilities, both for standard Python scripts,
# and for for Python programs which run as services...
#
# Note that most utility functions here will raise win32api.error's
# (which is win32service.error, pywintypes.error, etc)
# when things go wrong - eg, not enough permissions to hit the
# registry etc.

import importlib.machinery
import os
import sys
import warnings

import pywintypes
import win32api
import win32con
import win32service
import winerror

error = RuntimeError  # Re-exported alias


# Returns the full path to an executable for hosting a Python service - typically
# 'pythonservice.exe'
# * If you pass a param and it exists as a file, you'll get the abs path back
# * Otherwise we'll use the param instead of 'pythonservice.exe', and we will
#   look for it.
def LocatePythonServiceExe(exe=None):
    if not exe and hasattr(sys, "frozen"):
        # If py2exe etc calls this with no exe, default is current exe,
        # and all setup is their problem :)
        return sys.executable

    if exe and os.path.isfile(exe):
        return win32api.GetFullPathName(exe)

    suffix = "_d" if "_d.pyd" in importlib.machinery.EXTENSION_SUFFIXES else ""

    # We are confused if we aren't now looking for our default. But if that
    # exists as specified we assume it's good.
    exe = f"pythonservice{suffix}.exe"
    if os.path.isfile(exe):
        return win32api.GetFullPathName(exe)

    # Now we are searching for the .exe
    # We are going to want it here.
    correct = os.path.join(sys.exec_prefix, exe)
    # Even if that file already exists, we copy the one installed by pywin32
    # in-case it was upgraded.
    # pywin32 installed it next to win32service.pyd (but we can't run it from there)
    maybe = os.path.join(os.path.dirname(win32service.__file__), exe)
    if os.path.exists(maybe):
        print(f"moving host exe '{maybe}' -> '{correct}'")
        # Handle case where MoveFile() fails. Particularly if destination file
        # has a resource lock and can't be replaced by src file
        try:
            win32api.MoveFileEx(maybe, correct, win32con.MOVEFILE_REPLACE_EXISTING)
        except win32api.error as exc:
            print(f"Failed to move host exe '{exc}'")

    if not os.path.exists(correct):
        raise error(f"Can't find '{correct}'")

    # If pywintypes.dll isn't next to us, or at least next to pythonXX.dll,
    # there's a good chance the service will not run. That's usually copied by
    # `pywin32_postinstall`, but putting it next to the python DLL seems reasonable.
    # (Unlike the .exe above, we don't unconditionally copy this, and possibly
    # copy it to a different place. Doesn't seem a good reason for that!?)
    python_dll = win32api.GetModuleFileName(sys.dllhandle)
    pyw = f"pywintypes{sys.version_info.major}{sys.version_info.minor}{suffix}.dll"
    correct_pyw = os.path.join(os.path.dirname(python_dll), pyw)

    if not os.path.exists(correct_pyw):
        print(f"copying helper dll '{pywintypes.__file__}' -> '{correct_pyw}'")
        win32api.CopyFile(pywintypes.__file__, correct_pyw)

    return correct


def _GetServiceShortName(longName):
    # looks up a services name
    # from the display name
    # Thanks to Andy McKay for this code.
    access = (
        win32con.KEY_READ | win32con.KEY_ENUMERATE_SUB_KEYS | win32con.KEY_QUERY_VALUE
    )
    hkey = win32api.RegOpenKey(
        win32con.HKEY_LOCAL_MACHINE, "SYSTEM\\CurrentControlSet\\Services", 0, access
    )
    num = win32api.RegQueryInfoKey(hkey)[0]
    longName = longName.lower()
    # loop through number of subkeys
    for x in range(0, num):
        # find service name, open subkey
        svc = win32api.RegEnumKey(hkey, x)
        skey = win32api.RegOpenKey(hkey, svc, 0, access)
        try:
            # find display name
            thisName = str(win32api.RegQueryValueEx(skey, "DisplayName")[0])
            if thisName.lower() == longName:
                return svc
        except win32api.error:
            # in case there is no key called DisplayName
            pass
    return None


# Open a service given either it's long or short name.
def SmartOpenService(hscm, name, access):
    try:
        return win32service.OpenService(hscm, name, access)
    except win32api.error as details:
        if details.winerror not in [
            winerror.ERROR_SERVICE_DOES_NOT_EXIST,
            winerror.ERROR_INVALID_NAME,
        ]:
            raise
    name = win32service.GetServiceKeyName(hscm, name)
    return win32service.OpenService(hscm, name, access)


def LocateSpecificServiceExe(serviceName):
    # Return the .exe name of any service.
    hkey = win32api.RegOpenKey(
        win32con.HKEY_LOCAL_MACHINE,
        "SYSTEM\\CurrentControlSet\\Services\\%s" % (serviceName),
        0,
        win32con.KEY_QUERY_VALUE,
    )
    try:
        return win32api.RegQueryValueEx(hkey, "ImagePath")[0]
    finally:
        hkey.Close()


def InstallPerfmonForService(serviceName, iniName, dllName=None):
    # If no DLL name, look it up in the INI file name
    if not dllName:  # May be empty string!
        dllName = win32api.GetProfileVal("Python", "dll", "", iniName)
    # Still not found - look for the standard one in the same dir as win32service.pyd
    if not dllName:
        try:
            tryName = os.path.join(
                os.path.split(win32service.__file__)[0], "perfmondata.dll"
            )
            if os.path.isfile(tryName):
                dllName = tryName
        except AttributeError:
            # Frozen app? - anyway, can't find it!
            pass
    if not dllName:
        raise ValueError("The name of the performance DLL must be available")
    dllName = win32api.GetFullPathName(dllName)
    # Now setup all the required "Performance" entries.
    hkey = win32api.RegOpenKey(
        win32con.HKEY_LOCAL_MACHINE,
        "SYSTEM\\CurrentControlSet\\Services\\%s" % (serviceName),
        0,
        win32con.KEY_ALL_ACCESS,
    )
    try:
        subKey = win32api.RegCreateKey(hkey, "Performance")
        try:
            win32api.RegSetValueEx(subKey, "Library", 0, win32con.REG_SZ, dllName)
            win32api.RegSetValueEx(
                subKey, "Open", 0, win32con.REG_SZ, "OpenPerformanceData"
            )
            win32api.RegSetValueEx(
                subKey, "Close", 0, win32con.REG_SZ, "ClosePerformanceData"
            )
            win32api.RegSetValueEx(
                subKey, "Collect", 0, win32con.REG_SZ, "CollectPerformanceData"
            )
        finally:
            win32api.RegCloseKey(subKey)
    finally:
        win32api.RegCloseKey(hkey)
    # Now do the "Lodctr" thang...

    try:
        import perfmon

        path, fname = os.path.split(iniName)
        oldPath = os.getcwd()
        if path:
            os.chdir(path)
        try:
            perfmon.LoadPerfCounterTextStrings("python.exe " + fname)
        finally:
            os.chdir(oldPath)
    except win32api.error as details:
        print("The service was installed OK, but the performance monitor")
        print("data could not be loaded.", details)


def _GetCommandLine(exeName, exeArgs):
    if exeArgs is not None:
        return exeName + " " + exeArgs
    else:
        return exeName


def InstallService(
    pythonClassString,
    serviceName,
    displayName,
    startType=None,
    errorControl=None,
    bRunInteractive=0,
    serviceDeps=None,
    userName=None,
    password=None,
    exeName=None,
    perfMonIni=None,
    perfMonDll=None,
    exeArgs=None,
    description=None,
    delayedstart=None,
):
    # Handle the default arguments.
    if startType is None:
        startType = win32service.SERVICE_DEMAND_START
    serviceType = win32service.SERVICE_WIN32_OWN_PROCESS
    if bRunInteractive:
        serviceType |= win32service.SERVICE_INTERACTIVE_PROCESS
    if errorControl is None:
        errorControl = win32service.SERVICE_ERROR_NORMAL

    exeName = '"%s"' % LocatePythonServiceExe(exeName)
    commandLine = _GetCommandLine(exeName, exeArgs)
    hscm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ALL_ACCESS)
    try:
        hs = win32service.CreateService(
            hscm,
            serviceName,
            displayName,
            win32service.SERVICE_ALL_ACCESS,  # desired access
            serviceType,  # service type
            startType,
            errorControl,  # error control type
            commandLine,
            None,
            0,
            serviceDeps,
            userName,
            password,
        )
        if description is not None:
            try:
                win32service.ChangeServiceConfig2(
                    hs, win32service.SERVICE_CONFIG_DESCRIPTION, description
                )
            except NotImplementedError:
                pass  ## ChangeServiceConfig2 and description do not exist on NT
        if delayedstart is not None:
            try:
                win32service.ChangeServiceConfig2(
                    hs,
                    win32service.SERVICE_CONFIG_DELAYED_AUTO_START_INFO,
                    delayedstart,
                )
            except (win32service.error, NotImplementedError):
                ## delayed start only exists on Vista and later - warn only when trying to set delayed to True
                warnings.warn("Delayed Start not available on this system")
        win32service.CloseServiceHandle(hs)
    finally:
        win32service.CloseServiceHandle(hscm)
    InstallPythonClassString(pythonClassString, serviceName)
    # If I have performance monitor info to install, do that.
    if perfMonIni is not None:
        InstallPerfmonForService(serviceName, perfMonIni, perfMonDll)


def ChangeServiceConfig(
    pythonClassString,
    serviceName,
    startType=None,
    errorControl=None,
    bRunInteractive=0,
    serviceDeps=None,
    userName=None,
    password=None,
    exeName=None,
    displayName=None,
    perfMonIni=None,
    perfMonDll=None,
    exeArgs=None,
    description=None,
    delayedstart=None,
):
    # Before doing anything, remove any perfmon counters.
    try:
        import perfmon

        perfmon.UnloadPerfCounterTextStrings("python.exe " + serviceName)
    except (ImportError, win32api.error):
        pass

    # The EXE location may have changed
    exeName = '"%s"' % LocatePythonServiceExe(exeName)

    # Handle the default arguments.
    if startType is None:
        startType = win32service.SERVICE_NO_CHANGE
    if errorControl is None:
        errorControl = win32service.SERVICE_NO_CHANGE

    hscm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ALL_ACCESS)
    serviceType = win32service.SERVICE_WIN32_OWN_PROCESS
    if bRunInteractive:
        serviceType |= win32service.SERVICE_INTERACTIVE_PROCESS
    commandLine = _GetCommandLine(exeName, exeArgs)
    try:
        hs = SmartOpenService(hscm, serviceName, win32service.SERVICE_ALL_ACCESS)
        try:
            win32service.ChangeServiceConfig(
                hs,
                serviceType,  # service type
                startType,
                errorControl,  # error control type
                commandLine,
                None,
                0,
                serviceDeps,
                userName,
                password,
                displayName,
            )
            if description is not None:
                try:
                    win32service.ChangeServiceConfig2(
                        hs, win32service.SERVICE_CONFIG_DESCRIPTION, description
                    )
                except NotImplementedError:
                    pass  ## ChangeServiceConfig2 and description do not exist on NT
            if delayedstart is not None:
                try:
                    win32service.ChangeServiceConfig2(
                        hs,
                        win32service.SERVICE_CONFIG_DELAYED_AUTO_START_INFO,
                        delayedstart,
                    )
                except (win32service.error, NotImplementedError):
                    ## Delayed start only exists on Vista and later.  On Nt, will raise NotImplementedError since ChangeServiceConfig2
                    ## doensn't exist.  On Win2k and XP, will fail with ERROR_INVALID_LEVEL
                    ## Warn only if trying to set delayed to True
                    if delayedstart:
                        warnings.warn("Delayed Start not available on this system")
        finally:
            win32service.CloseServiceHandle(hs)
    finally:
        win32service.CloseServiceHandle(hscm)
    InstallPythonClassString(pythonClassString, serviceName)
    # If I have performance monitor info to install, do that.
    if perfMonIni is not None:
        InstallPerfmonForService(serviceName, perfMonIni, perfMonDll)


def InstallPythonClassString(pythonClassString, serviceName):
    # Now setup our Python specific entries.
    if pythonClassString:
        key = win32api.RegCreateKey(
            win32con.HKEY_LOCAL_MACHINE,
            "System\\CurrentControlSet\\Services\\%s\\PythonClass" % serviceName,
        )
        try:
            win32api.RegSetValue(key, None, win32con.REG_SZ, pythonClassString)
        finally:
            win32api.RegCloseKey(key)


# Utility functions for Services, to allow persistant properties.
def SetServiceCustomOption(serviceName, option, value):
    try:
        serviceName = serviceName._svc_name_
    except AttributeError:
        pass
    key = win32api.RegCreateKey(
        win32con.HKEY_LOCAL_MACHINE,
        "System\\CurrentControlSet\\Services\\%s\\Parameters" % serviceName,
    )
    try:
        if isinstance(value, int):
            win32api.RegSetValueEx(key, option, 0, win32con.REG_DWORD, value)
        else:
            win32api.RegSetValueEx(key, option, 0, win32con.REG_SZ, value)
    finally:
        win32api.RegCloseKey(key)


def GetServiceCustomOption(serviceName, option, defaultValue=None):
    # First param may also be a service class/instance.
    # This allows services to pass "self"
    try:
        serviceName = serviceName._svc_name_
    except AttributeError:
        pass
    key = win32api.RegCreateKey(
        win32con.HKEY_LOCAL_MACHINE,
        "System\\CurrentControlSet\\Services\\%s\\Parameters" % serviceName,
    )
    try:
        try:
            return win32api.RegQueryValueEx(key, option)[0]
        except win32api.error:  # No value.
            return defaultValue
    finally:
        win32api.RegCloseKey(key)


def RemoveService(serviceName):
    try:
        import perfmon

        perfmon.UnloadPerfCounterTextStrings("python.exe " + serviceName)
    except (ImportError, win32api.error):
        pass

    hscm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ALL_ACCESS)
    try:
        hs = SmartOpenService(hscm, serviceName, win32service.SERVICE_ALL_ACCESS)
        win32service.DeleteService(hs)
        win32service.CloseServiceHandle(hs)
    finally:
        win32service.CloseServiceHandle(hscm)

    import win32evtlogutil

    try:
        win32evtlogutil.RemoveSourceFromRegistry(serviceName)
    except win32api.error:
        pass


def ControlService(serviceName, code, machine=None):
    hscm = win32service.OpenSCManager(machine, None, win32service.SC_MANAGER_ALL_ACCESS)
    try:
        hs = SmartOpenService(hscm, serviceName, win32service.SERVICE_ALL_ACCESS)
        try:
            status = win32service.ControlService(hs, code)
        finally:
            win32service.CloseServiceHandle(hs)
    finally:
        win32service.CloseServiceHandle(hscm)
    return status


def __FindSvcDeps(findName):
    dict = {}
    k = win32api.RegOpenKey(
        win32con.HKEY_LOCAL_MACHINE, "SYSTEM\\CurrentControlSet\\Services"
    )
    num = 0
    while 1:
        try:
            svc = win32api.RegEnumKey(k, num)
        except win32api.error:
            break
        num += 1
        sk = win32api.RegOpenKey(k, svc)
        try:
            deps, typ = win32api.RegQueryValueEx(sk, "DependOnService")
        except win32api.error:
            deps = ()
        for dep in deps:
            dep = dep.lower()
            dep_on = dict.get(dep, [])
            dep_on.append(svc)
            dict[dep] = dep_on

    return __ResolveDeps(findName, dict)


def __ResolveDeps(findName, dict):
    items = dict.get(findName.lower(), [])
    retList = []
    for svc in items:
        retList.insert(0, svc)
        retList = __ResolveDeps(svc, dict) + retList
    return retList


def WaitForServiceStatus(serviceName, status, waitSecs, machine=None):
    """Waits for the service to return the specified status.  You
    should have already requested the service to enter that state"""
    for i in range(waitSecs * 4):
        now_status = QueryServiceStatus(serviceName, machine)[1]
        if now_status == status:
            break
        win32api.Sleep(250)
    else:
        raise pywintypes.error(
            winerror.ERROR_SERVICE_REQUEST_TIMEOUT,
            "QueryServiceStatus",
            win32api.FormatMessage(winerror.ERROR_SERVICE_REQUEST_TIMEOUT)[:-2],
        )


def __StopServiceWithTimeout(hs, waitSecs=30):
    try:
        status = win32service.ControlService(hs, win32service.SERVICE_CONTROL_STOP)
    except pywintypes.error as exc:
        if exc.winerror != winerror.ERROR_SERVICE_NOT_ACTIVE:
            raise
    for i in range(waitSecs):
        status = win32service.QueryServiceStatus(hs)
        if status[1] == win32service.SERVICE_STOPPED:
            break
        win32api.Sleep(1000)
    else:
        raise pywintypes.error(
            winerror.ERROR_SERVICE_REQUEST_TIMEOUT,
            "ControlService",
            win32api.FormatMessage(winerror.ERROR_SERVICE_REQUEST_TIMEOUT)[:-2],
        )


def StopServiceWithDeps(serviceName, machine=None, waitSecs=30):
    # Stop a service recursively looking for dependant services
    hscm = win32service.OpenSCManager(machine, None, win32service.SC_MANAGER_ALL_ACCESS)
    try:
        deps = __FindSvcDeps(serviceName)
        for dep in deps:
            hs = win32service.OpenService(hscm, dep, win32service.SERVICE_ALL_ACCESS)
            try:
                __StopServiceWithTimeout(hs, waitSecs)
            finally:
                win32service.CloseServiceHandle(hs)
        # Now my service!
        hs = win32service.OpenService(
            hscm, serviceName, win32service.SERVICE_ALL_ACCESS
        )
        try:
            __StopServiceWithTimeout(hs, waitSecs)
        finally:
            win32service.CloseServiceHandle(hs)

    finally:
        win32service.CloseServiceHandle(hscm)


def StopService(serviceName, machine=None):
    return ControlService(serviceName, win32service.SERVICE_CONTROL_STOP, machine)


def StartService(serviceName, args=None, machine=None):
    hscm = win32service.OpenSCManager(machine, None, win32service.SC_MANAGER_ALL_ACCESS)
    try:
        hs = SmartOpenService(hscm, serviceName, win32service.SERVICE_ALL_ACCESS)
        try:
            win32service.StartService(hs, args)
        finally:
            win32service.CloseServiceHandle(hs)
    finally:
        win32service.CloseServiceHandle(hscm)


def RestartService(serviceName, args=None, waitSeconds=30, machine=None):
    "Stop the service, and then start it again (with some tolerance for allowing it to stop.)"
    try:
        StopService(serviceName, machine)
    except pywintypes.error as exc:
        # Allow only "service not running" error
        if exc.winerror != winerror.ERROR_SERVICE_NOT_ACTIVE:
            raise
    # Give it a few goes, as the service may take time to stop
    for i in range(waitSeconds):
        try:
            StartService(serviceName, args, machine)
            break
        except pywintypes.error as exc:
            if exc.winerror != winerror.ERROR_SERVICE_ALREADY_RUNNING:
                raise
            win32api.Sleep(1000)
    else:
        print("Gave up waiting for the old service to stop!")


def _DebugCtrlHandler(evt):
    if evt in (win32con.CTRL_C_EVENT, win32con.CTRL_BREAK_EVENT):
        assert g_debugService
        print("Stopping debug service.")
        g_debugService.SvcStop()
        return True
    return False


def DebugService(cls, argv=[]):
    # Run a service in "debug" mode.  Re-implements what pythonservice.exe
    # does when it sees a "-debug" param.
    # Currently only used by "frozen" (ie, py2exe) programs (but later may
    # end up being used for all services should we ever remove
    # pythonservice.exe)
    import servicemanager

    global g_debugService

    print(f"Debugging service {cls._svc_name_} - press Ctrl+C to stop.")
    servicemanager.Debugging(True)
    servicemanager.PrepareToHostSingle(cls)
    g_debugService = cls(argv)
    # Setup a ctrl+c handler to simulate a "stop"
    win32api.SetConsoleCtrlHandler(_DebugCtrlHandler, True)
    try:
        g_debugService.SvcRun()
    finally:
        win32api.SetConsoleCtrlHandler(_DebugCtrlHandler, False)
        servicemanager.Debugging(False)
        g_debugService = None


def GetServiceClassString(cls, argv=None):
    if argv is None:
        argv = sys.argv
    import pickle

    modName = pickle.whichmodule(cls, cls.__name__)
    if modName == "__main__":
        try:
            fname = win32api.GetFullPathName(argv[0])
            path = os.path.split(fname)[0]
            # Eaaaahhhh - sometimes this will be a short filename, which causes
            # problems with 1.5.1 and the silly filename case rule.
            filelist = win32api.FindFiles(fname)
            # win32api.FindFiles will not detect files in a zip or exe. If list is empty,
            # skip the test and hope the file really exists.
            if len(filelist) != 0:
                # Get the long name
                fname = os.path.join(path, filelist[0][8])
        except win32api.error:
            raise error(
                "Could not resolve the path name '%s' to a full path" % (argv[0])
            )
        modName = os.path.splitext(fname)[0]
    return modName + "." + cls.__name__


def QueryServiceStatus(serviceName, machine=None):
    hscm = win32service.OpenSCManager(machine, None, win32service.SC_MANAGER_CONNECT)
    try:
        hs = SmartOpenService(hscm, serviceName, win32service.SERVICE_QUERY_STATUS)
        try:
            status = win32service.QueryServiceStatus(hs)
        finally:
            win32service.CloseServiceHandle(hs)
    finally:
        win32service.CloseServiceHandle(hscm)
    return status


def usage():
    try:
        fname = os.path.split(sys.argv[0])[1]
    except:
        fname = sys.argv[0]
    print(
        "Usage: '%s [options] install|update|remove|start [...]|stop|restart [...]|debug [...]'"
        % fname
    )
    print("Options for 'install' and 'update' commands only:")
    print(" --username domain\\username : The Username the service is to run under")
    print(" --password password : The password for the username")
    print(
        " --startup [manual|auto|disabled|delayed] : How the service starts, default = manual"
    )
    print(" --interactive : Allow the service to interact with the desktop.")
    print(
        " --perfmonini file: .ini file to use for registering performance monitor data"
    )
    print(" --perfmondll file: .dll file to use when querying the service for")
    print("   performance data, default = perfmondata.dll")
    print("Options for 'start' and 'stop' commands only:")
    print(" --wait seconds: Wait for the service to actually start or stop.")
    print("                 If you specify --wait with the 'stop' option, the service")
    print("                 and all dependent services will be stopped, each waiting")
    print("                 the specified period.")
    sys.exit(1)


def HandleCommandLine(
    cls,
    serviceClassString=None,
    argv=None,
    customInstallOptions="",
    customOptionHandler=None,
):
    """Utility function allowing services to process the command line.

    Allows standard commands such as 'start', 'stop', 'debug', 'install' etc.

    Install supports 'standard' command line options prefixed with '--', such as
    --username, --password, etc.  In addition,
    the function allows custom command line options to be handled by the calling function.
    """
    err = 0

    if argv is None:
        argv = sys.argv

    if len(argv) <= 1:
        usage()

    serviceName = cls._svc_name_
    serviceDisplayName = cls._svc_display_name_
    if serviceClassString is None:
        serviceClassString = GetServiceClassString(cls)

    # Pull apart the command line
    import getopt

    try:
        opts, args = getopt.getopt(
            argv[1:],
            customInstallOptions,
            [
                "password=",
                "username=",
                "startup=",
                "perfmonini=",
                "perfmondll=",
                "interactive",
                "wait=",
            ],
        )
    except getopt.error as details:
        print(details)
        usage()
    userName = None
    password = None
    perfMonIni = perfMonDll = None
    startup = None
    delayedstart = None
    interactive = None
    waitSecs = 0
    for opt, val in opts:
        if opt == "--username":
            userName = val
        elif opt == "--password":
            password = val
        elif opt == "--perfmonini":
            perfMonIni = val
        elif opt == "--perfmondll":
            perfMonDll = val
        elif opt == "--interactive":
            interactive = 1
        elif opt == "--startup":
            map = {
                "manual": win32service.SERVICE_DEMAND_START,
                "auto": win32service.SERVICE_AUTO_START,
                "delayed": win32service.SERVICE_AUTO_START,  ## ChangeServiceConfig2 called later
                "disabled": win32service.SERVICE_DISABLED,
            }
            startup = map.get(val.lower())
            if not startup:
                print(f"{val!r} is not a valid startup option")
            if val.lower() == "delayed":
                delayedstart = True
            elif val.lower() == "auto":
                delayedstart = False
            ## else no change
        elif opt == "--wait":
            try:
                waitSecs = int(val)
            except ValueError:
                print("--wait must specify an integer number of seconds.")
                usage()

    arg = args[0]
    knownArg = 0
    # First we process all arguments which pass additional args on
    if arg == "start":
        knownArg = 1
        print("Starting service %s" % (serviceName))
        try:
            StartService(serviceName, args[1:])
            if waitSecs:
                WaitForServiceStatus(
                    serviceName, win32service.SERVICE_RUNNING, waitSecs
                )
        except win32service.error as exc:
            print("Error starting service: %s" % exc.strerror)
            err = exc.winerror

    elif arg == "restart":
        knownArg = 1
        print("Restarting service %s" % (serviceName))
        RestartService(serviceName, args[1:])
        if waitSecs:
            WaitForServiceStatus(serviceName, win32service.SERVICE_RUNNING, waitSecs)

    elif arg == "debug":
        knownArg = 1
        if not hasattr(sys, "frozen"):
            # non-frozen services use pythonservice.exe which handles a
            # -debug option
            svcArgs = " ".join(args[1:])
            try:
                exeName = LocateSpecificServiceExe(serviceName)
            except win32api.error as exc:
                if exc.winerror == winerror.ERROR_FILE_NOT_FOUND:
                    print("The service does not appear to be installed.")
                    print("Please install the service before debugging it.")
                    sys.exit(1)
                raise
            try:
                os.system(f"{exeName} -debug {serviceName} {svcArgs}")
            # ^C is used to kill the debug service.  Sometimes Python also gets
            # interrupted - ignore it...
            except KeyboardInterrupt:
                pass
        else:
            # py2exe services don't use pythonservice - so we simulate
            # debugging here.
            DebugService(cls, args)

    if not knownArg and len(args) != 1:
        usage()  # the rest of the cmds don't take addn args

    if arg == "install":
        knownArg = 1
        try:
            serviceDeps = cls._svc_deps_
        except AttributeError:
            serviceDeps = None
        try:
            exeName = cls._exe_name_
        except AttributeError:
            exeName = None  # Default to PythonService.exe
        try:
            exeArgs = cls._exe_args_
        except AttributeError:
            exeArgs = None
        try:
            description = cls._svc_description_
        except AttributeError:
            description = None
        print(f"Installing service {serviceName}")
        # Note that we install the service before calling the custom option
        # handler, so if the custom handler fails, we have an installed service (from NT's POV)
        # but is unlikely to work, as the Python code controlling it failed.  Therefore
        # we remove the service if the first bit works, but the second doesn't!
        try:
            InstallService(
                serviceClassString,
                serviceName,
                serviceDisplayName,
                serviceDeps=serviceDeps,
                startType=startup,
                bRunInteractive=interactive,
                userName=userName,
                password=password,
                exeName=exeName,
                perfMonIni=perfMonIni,
                perfMonDll=perfMonDll,
                exeArgs=exeArgs,
                description=description,
                delayedstart=delayedstart,
            )
            if customOptionHandler:
                customOptionHandler(*(opts,))
            print("Service installed")
        except win32service.error as exc:
            if exc.winerror == winerror.ERROR_SERVICE_EXISTS:
                arg = "update"  # Fall through to the "update" param!
            else:
                print(
                    "Error installing service: %s (%d)" % (exc.strerror, exc.winerror)
                )
                err = exc.winerror
        except ValueError as msg:  # Can be raised by custom option handler.
            print("Error installing service: %s" % str(msg))
            err = -1
            # xxx - maybe I should remove after _any_ failed install - however,
            # xxx - it may be useful to help debug to leave the service as it failed.
            # xxx - We really _must_ remove as per the comments above...
            # As we failed here, remove the service, so the next installation
            # attempt works.
            try:
                RemoveService(serviceName)
            except win32api.error:
                print("Warning - could not remove the partially installed service.")

    if arg == "update":
        knownArg = 1
        try:
            serviceDeps = cls._svc_deps_
        except AttributeError:
            serviceDeps = None
        try:
            exeName = cls._exe_name_
        except AttributeError:
            exeName = None  # Default to PythonService.exe
        try:
            exeArgs = cls._exe_args_
        except AttributeError:
            exeArgs = None
        try:
            description = cls._svc_description_
        except AttributeError:
            description = None
        print("Changing service configuration")
        try:
            ChangeServiceConfig(
                serviceClassString,
                serviceName,
                serviceDeps=serviceDeps,
                startType=startup,
                bRunInteractive=interactive,
                userName=userName,
                password=password,
                exeName=exeName,
                displayName=serviceDisplayName,
                perfMonIni=perfMonIni,
                perfMonDll=perfMonDll,
                exeArgs=exeArgs,
                description=description,
                delayedstart=delayedstart,
            )
            if customOptionHandler:
                customOptionHandler(*(opts,))
            print("Service updated")
        except win32service.error as exc:
            print(
                "Error changing service configuration: %s (%d)"
                % (exc.strerror, exc.winerror)
            )
            err = exc.winerror

    elif arg == "remove":
        knownArg = 1
        print("Removing service %s" % (serviceName))
        try:
            RemoveService(serviceName)
            print("Service removed")
        except win32service.error as exc:
            print("Error removing service: %s (%d)" % (exc.strerror, exc.winerror))
            err = exc.winerror
    elif arg == "stop":
        knownArg = 1
        print("Stopping service %s" % (serviceName))
        try:
            if waitSecs:
                StopServiceWithDeps(serviceName, waitSecs=waitSecs)
            else:
                StopService(serviceName)
        except win32service.error as exc:
            print("Error stopping service: %s (%d)" % (exc.strerror, exc.winerror))
            err = exc.winerror
    if not knownArg:
        err = -1
        print("Unknown command - '%s'" % arg)
        usage()
    return err


#
# Useful base class to build services from.
#
class ServiceFramework:
    # Required Attributes:
    # _svc_name_ = The service name
    # _svc_display_name_ = The service display name

    # Optional Attributes:
    _svc_deps_ = None  # sequence of service names on which this depends
    _exe_name_ = None  # Default to PythonService.exe
    _exe_args_ = None  # Default to no arguments
    _svc_description_ = (
        None  # Only exists on Windows 2000 or later, ignored on windows NT
    )

    def __init__(self, args):
        import servicemanager

        self.ssh = servicemanager.RegisterServiceCtrlHandler(
            args[0], self.ServiceCtrlHandlerEx, True
        )
        servicemanager.SetEventSourceName(self._svc_name_)
        self.checkPoint = 0

    def GetAcceptedControls(self):
        # Setup the service controls we accept based on our attributes. Note
        # that if you need to handle controls via SvcOther[Ex](), you must
        # override this.
        accepted = 0
        if hasattr(self, "SvcStop"):
            accepted |= win32service.SERVICE_ACCEPT_STOP
        if hasattr(self, "SvcPause") and hasattr(self, "SvcContinue"):
            accepted |= win32service.SERVICE_ACCEPT_PAUSE_CONTINUE
        if hasattr(self, "SvcShutdown"):
            accepted |= win32service.SERVICE_ACCEPT_SHUTDOWN
        return accepted

    def ReportServiceStatus(
        self, serviceStatus, waitHint=5000, win32ExitCode=0, svcExitCode=0
    ):
        if self.ssh is None:  # Debugging!
            return
        if serviceStatus == win32service.SERVICE_START_PENDING:
            accepted = 0
        else:
            accepted = self.GetAcceptedControls()

        if serviceStatus in [
            win32service.SERVICE_RUNNING,
            win32service.SERVICE_STOPPED,
        ]:
            checkPoint = 0
        else:
            self.checkPoint += 1
            checkPoint = self.checkPoint

        # Now report the status to the control manager
        status = (
            win32service.SERVICE_WIN32_OWN_PROCESS,
            serviceStatus,
            accepted,  # dwControlsAccepted,
            win32ExitCode,  # dwWin32ExitCode;
            svcExitCode,  # dwServiceSpecificExitCode;
            checkPoint,  # dwCheckPoint;
            waitHint,
        )
        win32service.SetServiceStatus(self.ssh, status)

    def SvcInterrogate(self):
        # Assume we are running, and everyone is happy.
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)

    def SvcOther(self, control):
        try:
            print("Unknown control status - %d" % control)
        except OSError:
            # services may not have a valid stdout!
            pass

    def ServiceCtrlHandler(self, control):
        return self.ServiceCtrlHandlerEx(control, 0, None)

    # The 'Ex' functions, which take additional params
    def SvcOtherEx(self, control, event_type, data):
        # The default here is to call self.SvcOther as that is the old behaviour.
        # If you want to take advantage of the extra data, override this method
        return self.SvcOther(control)

    def ServiceCtrlHandlerEx(self, control, event_type, data):
        if control == win32service.SERVICE_CONTROL_STOP:
            return self.SvcStop()
        elif control == win32service.SERVICE_CONTROL_PAUSE:
            return self.SvcPause()
        elif control == win32service.SERVICE_CONTROL_CONTINUE:
            return self.SvcContinue()
        elif control == win32service.SERVICE_CONTROL_INTERROGATE:
            return self.SvcInterrogate()
        elif control == win32service.SERVICE_CONTROL_SHUTDOWN:
            return self.SvcShutdown()
        else:
            return self.SvcOtherEx(control, event_type, data)

    def SvcRun(self):
        # This is the entry point the C framework calls when the Service is
        # started. Your Service class should implement SvcDoRun().
        # Or you can override this method for more control over the Service
        # statuses reported to the SCM.

        # If this method raises an exception, the C framework will detect this
        # and report a SERVICE_STOPPED status with a non-zero error code.

        self.ReportServiceStatus(win32service.SERVICE_RUNNING)
        self.SvcDoRun()
        # Once SvcDoRun terminates, the service has stopped.
        # We tell the SCM the service is still stopping - the C framework
        # will automatically tell the SCM it has stopped when this returns.
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\win32\lib\win32serviceutil.py ===
# General purpose service utilities, both for standard Python scripts,
# and for for Python programs which run as services...
#
# Note that most utility functions here will raise win32api.error's
# (which is win32service.error, pywintypes.error, etc)
# when things go wrong - eg, not enough permissions to hit the
# registry etc.

import importlib.machinery
import os
import sys
import warnings

import pywintypes
import win32api
import win32con
import win32service
import winerror

error = RuntimeError  # Re-exported alias


# Returns the full path to an executable for hosting a Python service - typically
# 'pythonservice.exe'
# * If you pass a param and it exists as a file, you'll get the abs path back
# * Otherwise we'll use the param instead of 'pythonservice.exe', and we will
#   look for it.
def LocatePythonServiceExe(exe=None):
    if not exe and hasattr(sys, "frozen"):
        # If py2exe etc calls this with no exe, default is current exe,
        # and all setup is their problem :)
        return sys.executable

    if exe and os.path.isfile(exe):
        return win32api.GetFullPathName(exe)

    suffix = "_d" if "_d.pyd" in importlib.machinery.EXTENSION_SUFFIXES else ""

    # We are confused if we aren't now looking for our default. But if that
    # exists as specified we assume it's good.
    exe = f"pythonservice{suffix}.exe"
    if os.path.isfile(exe):
        return win32api.GetFullPathName(exe)

    # Now we are searching for the .exe
    # We are going to want it here.
    correct = os.path.join(sys.exec_prefix, exe)
    # Even if that file already exists, we copy the one installed by pywin32
    # in-case it was upgraded.
    # pywin32 installed it next to win32service.pyd (but we can't run it from there)
    maybe = os.path.join(os.path.dirname(win32service.__file__), exe)
    if os.path.exists(maybe):
        print(f"moving host exe '{maybe}' -> '{correct}'")
        # Handle case where MoveFile() fails. Particularly if destination file
        # has a resource lock and can't be replaced by src file
        try:
            win32api.MoveFileEx(maybe, correct, win32con.MOVEFILE_REPLACE_EXISTING)
        except win32api.error as exc:
            print(f"Failed to move host exe '{exc}'")

    if not os.path.exists(correct):
        raise error(f"Can't find '{correct}'")

    # If pywintypes.dll isn't next to us, or at least next to pythonXX.dll,
    # there's a good chance the service will not run. That's usually copied by
    # `pywin32_postinstall`, but putting it next to the python DLL seems reasonable.
    # (Unlike the .exe above, we don't unconditionally copy this, and possibly
    # copy it to a different place. Doesn't seem a good reason for that!?)
    python_dll = win32api.GetModuleFileName(sys.dllhandle)
    pyw = f"pywintypes{sys.version_info.major}{sys.version_info.minor}{suffix}.dll"
    correct_pyw = os.path.join(os.path.dirname(python_dll), pyw)

    if not os.path.exists(correct_pyw):
        print(f"copying helper dll '{pywintypes.__file__}' -> '{correct_pyw}'")
        win32api.CopyFile(pywintypes.__file__, correct_pyw)

    return correct


def _GetServiceShortName(longName):
    # looks up a services name
    # from the display name
    # Thanks to Andy McKay for this code.
    access = (
        win32con.KEY_READ | win32con.KEY_ENUMERATE_SUB_KEYS | win32con.KEY_QUERY_VALUE
    )
    hkey = win32api.RegOpenKey(
        win32con.HKEY_LOCAL_MACHINE, "SYSTEM\\CurrentControlSet\\Services", 0, access
    )
    num = win32api.RegQueryInfoKey(hkey)[0]
    longName = longName.lower()
    # loop through number of subkeys
    for x in range(0, num):
        # find service name, open subkey
        svc = win32api.RegEnumKey(hkey, x)
        skey = win32api.RegOpenKey(hkey, svc, 0, access)
        try:
            # find display name
            thisName = str(win32api.RegQueryValueEx(skey, "DisplayName")[0])
            if thisName.lower() == longName:
                return svc
        except win32api.error:
            # in case there is no key called DisplayName
            pass
    return None


# Open a service given either it's long or short name.
def SmartOpenService(hscm, name, access):
    try:
        return win32service.OpenService(hscm, name, access)
    except win32api.error as details:
        if details.winerror not in [
            winerror.ERROR_SERVICE_DOES_NOT_EXIST,
            winerror.ERROR_INVALID_NAME,
        ]:
            raise
    name = win32service.GetServiceKeyName(hscm, name)
    return win32service.OpenService(hscm, name, access)


def LocateSpecificServiceExe(serviceName):
    # Return the .exe name of any service.
    hkey = win32api.RegOpenKey(
        win32con.HKEY_LOCAL_MACHINE,
        "SYSTEM\\CurrentControlSet\\Services\\%s" % (serviceName),
        0,
        win32con.KEY_QUERY_VALUE,
    )
    try:
        return win32api.RegQueryValueEx(hkey, "ImagePath")[0]
    finally:
        hkey.Close()


def InstallPerfmonForService(serviceName, iniName, dllName=None):
    # If no DLL name, look it up in the INI file name
    if not dllName:  # May be empty string!
        dllName = win32api.GetProfileVal("Python", "dll", "", iniName)
    # Still not found - look for the standard one in the same dir as win32service.pyd
    if not dllName:
        try:
            tryName = os.path.join(
                os.path.split(win32service.__file__)[0], "perfmondata.dll"
            )
            if os.path.isfile(tryName):
                dllName = tryName
        except AttributeError:
            # Frozen app? - anyway, can't find it!
            pass
    if not dllName:
        raise ValueError("The name of the performance DLL must be available")
    dllName = win32api.GetFullPathName(dllName)
    # Now setup all the required "Performance" entries.
    hkey = win32api.RegOpenKey(
        win32con.HKEY_LOCAL_MACHINE,
        "SYSTEM\\CurrentControlSet\\Services\\%s" % (serviceName),
        0,
        win32con.KEY_ALL_ACCESS,
    )
    try:
        subKey = win32api.RegCreateKey(hkey, "Performance")
        try:
            win32api.RegSetValueEx(subKey, "Library", 0, win32con.REG_SZ, dllName)
            win32api.RegSetValueEx(
                subKey, "Open", 0, win32con.REG_SZ, "OpenPerformanceData"
            )
            win32api.RegSetValueEx(
                subKey, "Close", 0, win32con.REG_SZ, "ClosePerformanceData"
            )
            win32api.RegSetValueEx(
                subKey, "Collect", 0, win32con.REG_SZ, "CollectPerformanceData"
            )
        finally:
            win32api.RegCloseKey(subKey)
    finally:
        win32api.RegCloseKey(hkey)
    # Now do the "Lodctr" thang...

    try:
        import perfmon

        path, fname = os.path.split(iniName)
        oldPath = os.getcwd()
        if path:
            os.chdir(path)
        try:
            perfmon.LoadPerfCounterTextStrings("python.exe " + fname)
        finally:
            os.chdir(oldPath)
    except win32api.error as details:
        print("The service was installed OK, but the performance monitor")
        print("data could not be loaded.", details)


def _GetCommandLine(exeName, exeArgs):
    if exeArgs is not None:
        return exeName + " " + exeArgs
    else:
        return exeName


def InstallService(
    pythonClassString,
    serviceName,
    displayName,
    startType=None,
    errorControl=None,
    bRunInteractive=0,
    serviceDeps=None,
    userName=None,
    password=None,
    exeName=None,
    perfMonIni=None,
    perfMonDll=None,
    exeArgs=None,
    description=None,
    delayedstart=None,
):
    # Handle the default arguments.
    if startType is None:
        startType = win32service.SERVICE_DEMAND_START
    serviceType = win32service.SERVICE_WIN32_OWN_PROCESS
    if bRunInteractive:
        serviceType |= win32service.SERVICE_INTERACTIVE_PROCESS
    if errorControl is None:
        errorControl = win32service.SERVICE_ERROR_NORMAL

    exeName = '"%s"' % LocatePythonServiceExe(exeName)
    commandLine = _GetCommandLine(exeName, exeArgs)
    hscm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ALL_ACCESS)
    try:
        hs = win32service.CreateService(
            hscm,
            serviceName,
            displayName,
            win32service.SERVICE_ALL_ACCESS,  # desired access
            serviceType,  # service type
            startType,
            errorControl,  # error control type
            commandLine,
            None,
            0,
            serviceDeps,
            userName,
            password,
        )
        if description is not None:
            try:
                win32service.ChangeServiceConfig2(
                    hs, win32service.SERVICE_CONFIG_DESCRIPTION, description
                )
            except NotImplementedError:
                pass  ## ChangeServiceConfig2 and description do not exist on NT
        if delayedstart is not None:
            try:
                win32service.ChangeServiceConfig2(
                    hs,
                    win32service.SERVICE_CONFIG_DELAYED_AUTO_START_INFO,
                    delayedstart,
                )
            except (win32service.error, NotImplementedError):
                ## delayed start only exists on Vista and later - warn only when trying to set delayed to True
                warnings.warn("Delayed Start not available on this system")
        win32service.CloseServiceHandle(hs)
    finally:
        win32service.CloseServiceHandle(hscm)
    InstallPythonClassString(pythonClassString, serviceName)
    # If I have performance monitor info to install, do that.
    if perfMonIni is not None:
        InstallPerfmonForService(serviceName, perfMonIni, perfMonDll)


def ChangeServiceConfig(
    pythonClassString,
    serviceName,
    startType=None,
    errorControl=None,
    bRunInteractive=0,
    serviceDeps=None,
    userName=None,
    password=None,
    exeName=None,
    displayName=None,
    perfMonIni=None,
    perfMonDll=None,
    exeArgs=None,
    description=None,
    delayedstart=None,
):
    # Before doing anything, remove any perfmon counters.
    try:
        import perfmon

        perfmon.UnloadPerfCounterTextStrings("python.exe " + serviceName)
    except (ImportError, win32api.error):
        pass

    # The EXE location may have changed
    exeName = '"%s"' % LocatePythonServiceExe(exeName)

    # Handle the default arguments.
    if startType is None:
        startType = win32service.SERVICE_NO_CHANGE
    if errorControl is None:
        errorControl = win32service.SERVICE_NO_CHANGE

    hscm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ALL_ACCESS)
    serviceType = win32service.SERVICE_WIN32_OWN_PROCESS
    if bRunInteractive:
        serviceType |= win32service.SERVICE_INTERACTIVE_PROCESS
    commandLine = _GetCommandLine(exeName, exeArgs)
    try:
        hs = SmartOpenService(hscm, serviceName, win32service.SERVICE_ALL_ACCESS)
        try:
            win32service.ChangeServiceConfig(
                hs,
                serviceType,  # service type
                startType,
                errorControl,  # error control type
                commandLine,
                None,
                0,
                serviceDeps,
                userName,
                password,
                displayName,
            )
            if description is not None:
                try:
                    win32service.ChangeServiceConfig2(
                        hs, win32service.SERVICE_CONFIG_DESCRIPTION, description
                    )
                except NotImplementedError:
                    pass  ## ChangeServiceConfig2 and description do not exist on NT
            if delayedstart is not None:
                try:
                    win32service.ChangeServiceConfig2(
                        hs,
                        win32service.SERVICE_CONFIG_DELAYED_AUTO_START_INFO,
                        delayedstart,
                    )
                except (win32service.error, NotImplementedError):
                    ## Delayed start only exists on Vista and later.  On Nt, will raise NotImplementedError since ChangeServiceConfig2
                    ## doensn't exist.  On Win2k and XP, will fail with ERROR_INVALID_LEVEL
                    ## Warn only if trying to set delayed to True
                    if delayedstart:
                        warnings.warn("Delayed Start not available on this system")
        finally:
            win32service.CloseServiceHandle(hs)
    finally:
        win32service.CloseServiceHandle(hscm)
    InstallPythonClassString(pythonClassString, serviceName)
    # If I have performance monitor info to install, do that.
    if perfMonIni is not None:
        InstallPerfmonForService(serviceName, perfMonIni, perfMonDll)


def InstallPythonClassString(pythonClassString, serviceName):
    # Now setup our Python specific entries.
    if pythonClassString:
        key = win32api.RegCreateKey(
            win32con.HKEY_LOCAL_MACHINE,
            "System\\CurrentControlSet\\Services\\%s\\PythonClass" % serviceName,
        )
        try:
            win32api.RegSetValue(key, None, win32con.REG_SZ, pythonClassString)
        finally:
            win32api.RegCloseKey(key)


# Utility functions for Services, to allow persistant properties.
def SetServiceCustomOption(serviceName, option, value):
    try:
        serviceName = serviceName._svc_name_
    except AttributeError:
        pass
    key = win32api.RegCreateKey(
        win32con.HKEY_LOCAL_MACHINE,
        "System\\CurrentControlSet\\Services\\%s\\Parameters" % serviceName,
    )
    try:
        if isinstance(value, int):
            win32api.RegSetValueEx(key, option, 0, win32con.REG_DWORD, value)
        else:
            win32api.RegSetValueEx(key, option, 0, win32con.REG_SZ, value)
    finally:
        win32api.RegCloseKey(key)


def GetServiceCustomOption(serviceName, option, defaultValue=None):
    # First param may also be a service class/instance.
    # This allows services to pass "self"
    try:
        serviceName = serviceName._svc_name_
    except AttributeError:
        pass
    key = win32api.RegCreateKey(
        win32con.HKEY_LOCAL_MACHINE,
        "System\\CurrentControlSet\\Services\\%s\\Parameters" % serviceName,
    )
    try:
        try:
            return win32api.RegQueryValueEx(key, option)[0]
        except win32api.error:  # No value.
            return defaultValue
    finally:
        win32api.RegCloseKey(key)


def RemoveService(serviceName):
    try:
        import perfmon

        perfmon.UnloadPerfCounterTextStrings("python.exe " + serviceName)
    except (ImportError, win32api.error):
        pass

    hscm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ALL_ACCESS)
    try:
        hs = SmartOpenService(hscm, serviceName, win32service.SERVICE_ALL_ACCESS)
        win32service.DeleteService(hs)
        win32service.CloseServiceHandle(hs)
    finally:
        win32service.CloseServiceHandle(hscm)

    import win32evtlogutil

    try:
        win32evtlogutil.RemoveSourceFromRegistry(serviceName)
    except win32api.error:
        pass


def ControlService(serviceName, code, machine=None):
    hscm = win32service.OpenSCManager(machine, None, win32service.SC_MANAGER_ALL_ACCESS)
    try:
        hs = SmartOpenService(hscm, serviceName, win32service.SERVICE_ALL_ACCESS)
        try:
            status = win32service.ControlService(hs, code)
        finally:
            win32service.CloseServiceHandle(hs)
    finally:
        win32service.CloseServiceHandle(hscm)
    return status


def __FindSvcDeps(findName):
    dict = {}
    k = win32api.RegOpenKey(
        win32con.HKEY_LOCAL_MACHINE, "SYSTEM\\CurrentControlSet\\Services"
    )
    num = 0
    while 1:
        try:
            svc = win32api.RegEnumKey(k, num)
        except win32api.error:
            break
        num += 1
        sk = win32api.RegOpenKey(k, svc)
        try:
            deps, typ = win32api.RegQueryValueEx(sk, "DependOnService")
        except win32api.error:
            deps = ()
        for dep in deps:
            dep = dep.lower()
            dep_on = dict.get(dep, [])
            dep_on.append(svc)
            dict[dep] = dep_on

    return __ResolveDeps(findName, dict)


def __ResolveDeps(findName, dict):
    items = dict.get(findName.lower(), [])
    retList = []
    for svc in items:
        retList.insert(0, svc)
        retList = __ResolveDeps(svc, dict) + retList
    return retList


def WaitForServiceStatus(serviceName, status, waitSecs, machine=None):
    """Waits for the service to return the specified status.  You
    should have already requested the service to enter that state"""
    for i in range(waitSecs * 4):
        now_status = QueryServiceStatus(serviceName, machine)[1]
        if now_status == status:
            break
        win32api.Sleep(250)
    else:
        raise pywintypes.error(
            winerror.ERROR_SERVICE_REQUEST_TIMEOUT,
            "QueryServiceStatus",
            win32api.FormatMessage(winerror.ERROR_SERVICE_REQUEST_TIMEOUT)[:-2],
        )


def __StopServiceWithTimeout(hs, waitSecs=30):
    try:
        status = win32service.ControlService(hs, win32service.SERVICE_CONTROL_STOP)
    except pywintypes.error as exc:
        if exc.winerror != winerror.ERROR_SERVICE_NOT_ACTIVE:
            raise
    for i in range(waitSecs):
        status = win32service.QueryServiceStatus(hs)
        if status[1] == win32service.SERVICE_STOPPED:
            break
        win32api.Sleep(1000)
    else:
        raise pywintypes.error(
            winerror.ERROR_SERVICE_REQUEST_TIMEOUT,
            "ControlService",
            win32api.FormatMessage(winerror.ERROR_SERVICE_REQUEST_TIMEOUT)[:-2],
        )


def StopServiceWithDeps(serviceName, machine=None, waitSecs=30):
    # Stop a service recursively looking for dependant services
    hscm = win32service.OpenSCManager(machine, None, win32service.SC_MANAGER_ALL_ACCESS)
    try:
        deps = __FindSvcDeps(serviceName)
        for dep in deps:
            hs = win32service.OpenService(hscm, dep, win32service.SERVICE_ALL_ACCESS)
            try:
                __StopServiceWithTimeout(hs, waitSecs)
            finally:
                win32service.CloseServiceHandle(hs)
        # Now my service!
        hs = win32service.OpenService(
            hscm, serviceName, win32service.SERVICE_ALL_ACCESS
        )
        try:
            __StopServiceWithTimeout(hs, waitSecs)
        finally:
            win32service.CloseServiceHandle(hs)

    finally:
        win32service.CloseServiceHandle(hscm)


def StopService(serviceName, machine=None):
    return ControlService(serviceName, win32service.SERVICE_CONTROL_STOP, machine)


def StartService(serviceName, args=None, machine=None):
    hscm = win32service.OpenSCManager(machine, None, win32service.SC_MANAGER_ALL_ACCESS)
    try:
        hs = SmartOpenService(hscm, serviceName, win32service.SERVICE_ALL_ACCESS)
        try:
            win32service.StartService(hs, args)
        finally:
            win32service.CloseServiceHandle(hs)
    finally:
        win32service.CloseServiceHandle(hscm)


def RestartService(serviceName, args=None, waitSeconds=30, machine=None):
    "Stop the service, and then start it again (with some tolerance for allowing it to stop.)"
    try:
        StopService(serviceName, machine)
    except pywintypes.error as exc:
        # Allow only "service not running" error
        if exc.winerror != winerror.ERROR_SERVICE_NOT_ACTIVE:
            raise
    # Give it a few goes, as the service may take time to stop
    for i in range(waitSeconds):
        try:
            StartService(serviceName, args, machine)
            break
        except pywintypes.error as exc:
            if exc.winerror != winerror.ERROR_SERVICE_ALREADY_RUNNING:
                raise
            win32api.Sleep(1000)
    else:
        print("Gave up waiting for the old service to stop!")


def _DebugCtrlHandler(evt):
    if evt in (win32con.CTRL_C_EVENT, win32con.CTRL_BREAK_EVENT):
        assert g_debugService
        print("Stopping debug service.")
        g_debugService.SvcStop()
        return True
    return False


def DebugService(cls, argv=[]):
    # Run a service in "debug" mode.  Re-implements what pythonservice.exe
    # does when it sees a "-debug" param.
    # Currently only used by "frozen" (ie, py2exe) programs (but later may
    # end up being used for all services should we ever remove
    # pythonservice.exe)
    import servicemanager

    global g_debugService

    print(f"Debugging service {cls._svc_name_} - press Ctrl+C to stop.")
    servicemanager.Debugging(True)
    servicemanager.PrepareToHostSingle(cls)
    g_debugService = cls(argv)
    # Setup a ctrl+c handler to simulate a "stop"
    win32api.SetConsoleCtrlHandler(_DebugCtrlHandler, True)
    try:
        g_debugService.SvcRun()
    finally:
        win32api.SetConsoleCtrlHandler(_DebugCtrlHandler, False)
        servicemanager.Debugging(False)
        g_debugService = None


def GetServiceClassString(cls, argv=None):
    if argv is None:
        argv = sys.argv
    import pickle

    modName = pickle.whichmodule(cls, cls.__name__)
    if modName == "__main__":
        try:
            fname = win32api.GetFullPathName(argv[0])
            path = os.path.split(fname)[0]
            # Eaaaahhhh - sometimes this will be a short filename, which causes
            # problems with 1.5.1 and the silly filename case rule.
            filelist = win32api.FindFiles(fname)
            # win32api.FindFiles will not detect files in a zip or exe. If list is empty,
            # skip the test and hope the file really exists.
            if len(filelist) != 0:
                # Get the long name
                fname = os.path.join(path, filelist[0][8])
        except win32api.error:
            raise error(
                "Could not resolve the path name '%s' to a full path" % (argv[0])
            )
        modName = os.path.splitext(fname)[0]
    return modName + "." + cls.__name__


def QueryServiceStatus(serviceName, machine=None):
    hscm = win32service.OpenSCManager(machine, None, win32service.SC_MANAGER_CONNECT)
    try:
        hs = SmartOpenService(hscm, serviceName, win32service.SERVICE_QUERY_STATUS)
        try:
            status = win32service.QueryServiceStatus(hs)
        finally:
            win32service.CloseServiceHandle(hs)
    finally:
        win32service.CloseServiceHandle(hscm)
    return status


def usage():
    try:
        fname = os.path.split(sys.argv[0])[1]
    except:
        fname = sys.argv[0]
    print(
        "Usage: '%s [options] install|update|remove|start [...]|stop|restart [...]|debug [...]'"
        % fname
    )
    print("Options for 'install' and 'update' commands only:")
    print(" --username domain\\username : The Username the service is to run under")
    print(" --password password : The password for the username")
    print(
        " --startup [manual|auto|disabled|delayed] : How the service starts, default = manual"
    )
    print(" --interactive : Allow the service to interact with the desktop.")
    print(
        " --perfmonini file: .ini file to use for registering performance monitor data"
    )
    print(" --perfmondll file: .dll file to use when querying the service for")
    print("   performance data, default = perfmondata.dll")
    print("Options for 'start' and 'stop' commands only:")
    print(" --wait seconds: Wait for the service to actually start or stop.")
    print("                 If you specify --wait with the 'stop' option, the service")
    print("                 and all dependent services will be stopped, each waiting")
    print("                 the specified period.")
    sys.exit(1)


def HandleCommandLine(
    cls,
    serviceClassString=None,
    argv=None,
    customInstallOptions="",
    customOptionHandler=None,
):
    """Utility function allowing services to process the command line.

    Allows standard commands such as 'start', 'stop', 'debug', 'install' etc.

    Install supports 'standard' command line options prefixed with '--', such as
    --username, --password, etc.  In addition,
    the function allows custom command line options to be handled by the calling function.
    """
    err = 0

    if argv is None:
        argv = sys.argv

    if len(argv) <= 1:
        usage()

    serviceName = cls._svc_name_
    serviceDisplayName = cls._svc_display_name_
    if serviceClassString is None:
        serviceClassString = GetServiceClassString(cls)

    # Pull apart the command line
    import getopt

    try:
        opts, args = getopt.getopt(
            argv[1:],
            customInstallOptions,
            [
                "password=",
                "username=",
                "startup=",
                "perfmonini=",
                "perfmondll=",
                "interactive",
                "wait=",
            ],
        )
    except getopt.error as details:
        print(details)
        usage()
    userName = None
    password = None
    perfMonIni = perfMonDll = None
    startup = None
    delayedstart = None
    interactive = None
    waitSecs = 0
    for opt, val in opts:
        if opt == "--username":
            userName = val
        elif opt == "--password":
            password = val
        elif opt == "--perfmonini":
            perfMonIni = val
        elif opt == "--perfmondll":
            perfMonDll = val
        elif opt == "--interactive":
            interactive = 1
        elif opt == "--startup":
            map = {
                "manual": win32service.SERVICE_DEMAND_START,
                "auto": win32service.SERVICE_AUTO_START,
                "delayed": win32service.SERVICE_AUTO_START,  ## ChangeServiceConfig2 called later
                "disabled": win32service.SERVICE_DISABLED,
            }
            startup = map.get(val.lower())
            if not startup:
                print(f"{val!r} is not a valid startup option")
            if val.lower() == "delayed":
                delayedstart = True
            elif val.lower() == "auto":
                delayedstart = False
            ## else no change
        elif opt == "--wait":
            try:
                waitSecs = int(val)
            except ValueError:
                print("--wait must specify an integer number of seconds.")
                usage()

    arg = args[0]
    knownArg = 0
    # First we process all arguments which pass additional args on
    if arg == "start":
        knownArg = 1
        print("Starting service %s" % (serviceName))
        try:
            StartService(serviceName, args[1:])
            if waitSecs:
                WaitForServiceStatus(
                    serviceName, win32service.SERVICE_RUNNING, waitSecs
                )
        except win32service.error as exc:
            print("Error starting service: %s" % exc.strerror)
            err = exc.winerror

    elif arg == "restart":
        knownArg = 1
        print("Restarting service %s" % (serviceName))
        RestartService(serviceName, args[1:])
        if waitSecs:
            WaitForServiceStatus(serviceName, win32service.SERVICE_RUNNING, waitSecs)

    elif arg == "debug":
        knownArg = 1
        if not hasattr(sys, "frozen"):
            # non-frozen services use pythonservice.exe which handles a
            # -debug option
            svcArgs = " ".join(args[1:])
            try:
                exeName = LocateSpecificServiceExe(serviceName)
            except win32api.error as exc:
                if exc.winerror == winerror.ERROR_FILE_NOT_FOUND:
                    print("The service does not appear to be installed.")
                    print("Please install the service before debugging it.")
                    sys.exit(1)
                raise
            try:
                os.system(f"{exeName} -debug {serviceName} {svcArgs}")
            # ^C is used to kill the debug service.  Sometimes Python also gets
            # interrupted - ignore it...
            except KeyboardInterrupt:
                pass
        else:
            # py2exe services don't use pythonservice - so we simulate
            # debugging here.
            DebugService(cls, args)

    if not knownArg and len(args) != 1:
        usage()  # the rest of the cmds don't take addn args

    if arg == "install":
        knownArg = 1
        try:
            serviceDeps = cls._svc_deps_
        except AttributeError:
            serviceDeps = None
        try:
            exeName = cls._exe_name_
        except AttributeError:
            exeName = None  # Default to PythonService.exe
        try:
            exeArgs = cls._exe_args_
        except AttributeError:
            exeArgs = None
        try:
            description = cls._svc_description_
        except AttributeError:
            description = None
        print(f"Installing service {serviceName}")
        # Note that we install the service before calling the custom option
        # handler, so if the custom handler fails, we have an installed service (from NT's POV)
        # but is unlikely to work, as the Python code controlling it failed.  Therefore
        # we remove the service if the first bit works, but the second doesn't!
        try:
            InstallService(
                serviceClassString,
                serviceName,
                serviceDisplayName,
                serviceDeps=serviceDeps,
                startType=startup,
                bRunInteractive=interactive,
                userName=userName,
                password=password,
                exeName=exeName,
                perfMonIni=perfMonIni,
                perfMonDll=perfMonDll,
                exeArgs=exeArgs,
                description=description,
                delayedstart=delayedstart,
            )
            if customOptionHandler:
                customOptionHandler(*(opts,))
            print("Service installed")
        except win32service.error as exc:
            if exc.winerror == winerror.ERROR_SERVICE_EXISTS:
                arg = "update"  # Fall through to the "update" param!
            else:
                print(
                    "Error installing service: %s (%d)" % (exc.strerror, exc.winerror)
                )
                err = exc.winerror
        except ValueError as msg:  # Can be raised by custom option handler.
            print("Error installing service: %s" % str(msg))
            err = -1
            # xxx - maybe I should remove after _any_ failed install - however,
            # xxx - it may be useful to help debug to leave the service as it failed.
            # xxx - We really _must_ remove as per the comments above...
            # As we failed here, remove the service, so the next installation
            # attempt works.
            try:
                RemoveService(serviceName)
            except win32api.error:
                print("Warning - could not remove the partially installed service.")

    if arg == "update":
        knownArg = 1
        try:
            serviceDeps = cls._svc_deps_
        except AttributeError:
            serviceDeps = None
        try:
            exeName = cls._exe_name_
        except AttributeError:
            exeName = None  # Default to PythonService.exe
        try:
            exeArgs = cls._exe_args_
        except AttributeError:
            exeArgs = None
        try:
            description = cls._svc_description_
        except AttributeError:
            description = None
        print("Changing service configuration")
        try:
            ChangeServiceConfig(
                serviceClassString,
                serviceName,
                serviceDeps=serviceDeps,
                startType=startup,
                bRunInteractive=interactive,
                userName=userName,
                password=password,
                exeName=exeName,
                displayName=serviceDisplayName,
                perfMonIni=perfMonIni,
                perfMonDll=perfMonDll,
                exeArgs=exeArgs,
                description=description,
                delayedstart=delayedstart,
            )
            if customOptionHandler:
                customOptionHandler(*(opts,))
            print("Service updated")
        except win32service.error as exc:
            print(
                "Error changing service configuration: %s (%d)"
                % (exc.strerror, exc.winerror)
            )
            err = exc.winerror

    elif arg == "remove":
        knownArg = 1
        print("Removing service %s" % (serviceName))
        try:
            RemoveService(serviceName)
            print("Service removed")
        except win32service.error as exc:
            print("Error removing service: %s (%d)" % (exc.strerror, exc.winerror))
            err = exc.winerror
    elif arg == "stop":
        knownArg = 1
        print("Stopping service %s" % (serviceName))
        try:
            if waitSecs:
                StopServiceWithDeps(serviceName, waitSecs=waitSecs)
            else:
                StopService(serviceName)
        except win32service.error as exc:
            print("Error stopping service: %s (%d)" % (exc.strerror, exc.winerror))
            err = exc.winerror
    if not knownArg:
        err = -1
        print("Unknown command - '%s'" % arg)
        usage()
    return err


#
# Useful base class to build services from.
#
class ServiceFramework:
    # Required Attributes:
    # _svc_name_ = The service name
    # _svc_display_name_ = The service display name

    # Optional Attributes:
    _svc_deps_ = None  # sequence of service names on which this depends
    _exe_name_ = None  # Default to PythonService.exe
    _exe_args_ = None  # Default to no arguments
    _svc_description_ = (
        None  # Only exists on Windows 2000 or later, ignored on windows NT
    )

    def __init__(self, args):
        import servicemanager

        self.ssh = servicemanager.RegisterServiceCtrlHandler(
            args[0], self.ServiceCtrlHandlerEx, True
        )
        servicemanager.SetEventSourceName(self._svc_name_)
        self.checkPoint = 0

    def GetAcceptedControls(self):
        # Setup the service controls we accept based on our attributes. Note
        # that if you need to handle controls via SvcOther[Ex](), you must
        # override this.
        accepted = 0
        if hasattr(self, "SvcStop"):
            accepted |= win32service.SERVICE_ACCEPT_STOP
        if hasattr(self, "SvcPause") and hasattr(self, "SvcContinue"):
            accepted |= win32service.SERVICE_ACCEPT_PAUSE_CONTINUE
        if hasattr(self, "SvcShutdown"):
            accepted |= win32service.SERVICE_ACCEPT_SHUTDOWN
        return accepted

    def ReportServiceStatus(
        self, serviceStatus, waitHint=5000, win32ExitCode=0, svcExitCode=0
    ):
        if self.ssh is None:  # Debugging!
            return
        if serviceStatus == win32service.SERVICE_START_PENDING:
            accepted = 0
        else:
            accepted = self.GetAcceptedControls()

        if serviceStatus in [
            win32service.SERVICE_RUNNING,
            win32service.SERVICE_STOPPED,
        ]:
            checkPoint = 0
        else:
            self.checkPoint += 1
            checkPoint = self.checkPoint

        # Now report the status to the control manager
        status = (
            win32service.SERVICE_WIN32_OWN_PROCESS,
            serviceStatus,
            accepted,  # dwControlsAccepted,
            win32ExitCode,  # dwWin32ExitCode;
            svcExitCode,  # dwServiceSpecificExitCode;
            checkPoint,  # dwCheckPoint;
            waitHint,
        )
        win32service.SetServiceStatus(self.ssh, status)

    def SvcInterrogate(self):
        # Assume we are running, and everyone is happy.
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)

    def SvcOther(self, control):
        try:
            print("Unknown control status - %d" % control)
        except OSError:
            # services may not have a valid stdout!
            pass

    def ServiceCtrlHandler(self, control):
        return self.ServiceCtrlHandlerEx(control, 0, None)

    # The 'Ex' functions, which take additional params
    def SvcOtherEx(self, control, event_type, data):
        # The default here is to call self.SvcOther as that is the old behaviour.
        # If you want to take advantage of the extra data, override this method
        return self.SvcOther(control)

    def ServiceCtrlHandlerEx(self, control, event_type, data):
        if control == win32service.SERVICE_CONTROL_STOP:
            return self.SvcStop()
        elif control == win32service.SERVICE_CONTROL_PAUSE:
            return self.SvcPause()
        elif control == win32service.SERVICE_CONTROL_CONTINUE:
            return self.SvcContinue()
        elif control == win32service.SERVICE_CONTROL_INTERROGATE:
            return self.SvcInterrogate()
        elif control == win32service.SERVICE_CONTROL_SHUTDOWN:
            return self.SvcShutdown()
        else:
            return self.SvcOtherEx(control, event_type, data)

    def SvcRun(self):
        # This is the entry point the C framework calls when the Service is
        # started. Your Service class should implement SvcDoRun().
        # Or you can override this method for more control over the Service
        # statuses reported to the SCM.

        # If this method raises an exception, the C framework will detect this
        # and report a SERVICE_STOPPED status with a non-zero error code.

        self.ReportServiceStatus(win32service.SERVICE_RUNNING)
        self.SvcDoRun()
        # Once SvcDoRun terminates, the service has stopped.
        # We tell the SCM the service is still stopping - the C framework
        # will automatically tell the SCM it has stopped when this returns.
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)

# === NexusCore/openenv\Lib\site-packages\numpy\lib\_index_tricks_impl.py ===
import functools
import math
import sys
import warnings

import numpy as np
import numpy._core.numeric as _nx
import numpy.matrixlib as matrixlib
from numpy._core import linspace, overrides
from numpy._core.multiarray import ravel_multi_index, unravel_index
from numpy._core.numeric import ScalarType, array
from numpy._core.numerictypes import issubdtype
from numpy._utils import set_module
from numpy.lib._function_base_impl import diff
from numpy.lib.stride_tricks import as_strided

array_function_dispatch = functools.partial(
    overrides.array_function_dispatch, module='numpy')


__all__ = [
    'ravel_multi_index', 'unravel_index', 'mgrid', 'ogrid', 'r_', 'c_',
    's_', 'index_exp', 'ix_', 'ndenumerate', 'ndindex', 'fill_diagonal',
    'diag_indices', 'diag_indices_from'
]


def _ix__dispatcher(*args):
    return args


@array_function_dispatch(_ix__dispatcher)
def ix_(*args):
    """
    Construct an open mesh from multiple sequences.

    This function takes N 1-D sequences and returns N outputs with N
    dimensions each, such that the shape is 1 in all but one dimension
    and the dimension with the non-unit shape value cycles through all
    N dimensions.

    Using `ix_` one can quickly construct index arrays that will index
    the cross product. ``a[np.ix_([1,3],[2,5])]`` returns the array
    ``[[a[1,2] a[1,5]], [a[3,2] a[3,5]]]``.

    Parameters
    ----------
    args : 1-D sequences
        Each sequence should be of integer or boolean type.
        Boolean sequences will be interpreted as boolean masks for the
        corresponding dimension (equivalent to passing in
        ``np.nonzero(boolean_sequence)``).

    Returns
    -------
    out : tuple of ndarrays
        N arrays with N dimensions each, with N the number of input
        sequences. Together these arrays form an open mesh.

    See Also
    --------
    ogrid, mgrid, meshgrid

    Examples
    --------
    >>> import numpy as np
    >>> a = np.arange(10).reshape(2, 5)
    >>> a
    array([[0, 1, 2, 3, 4],
           [5, 6, 7, 8, 9]])
    >>> ixgrid = np.ix_([0, 1], [2, 4])
    >>> ixgrid
    (array([[0],
           [1]]), array([[2, 4]]))
    >>> ixgrid[0].shape, ixgrid[1].shape
    ((2, 1), (1, 2))
    >>> a[ixgrid]
    array([[2, 4],
           [7, 9]])

    >>> ixgrid = np.ix_([True, True], [2, 4])
    >>> a[ixgrid]
    array([[2, 4],
           [7, 9]])
    >>> ixgrid = np.ix_([True, True], [False, False, True, False, True])
    >>> a[ixgrid]
    array([[2, 4],
           [7, 9]])

    """
    out = []
    nd = len(args)
    for k, new in enumerate(args):
        if not isinstance(new, _nx.ndarray):
            new = np.asarray(new)
            if new.size == 0:
                # Explicitly type empty arrays to avoid float default
                new = new.astype(_nx.intp)
        if new.ndim != 1:
            raise ValueError("Cross index must be 1 dimensional")
        if issubdtype(new.dtype, _nx.bool):
            new, = new.nonzero()
        new = new.reshape((1,) * k + (new.size,) + (1,) * (nd - k - 1))
        out.append(new)
    return tuple(out)


class nd_grid:
    """
    Construct a multi-dimensional "meshgrid".

    ``grid = nd_grid()`` creates an instance which will return a mesh-grid
    when indexed.  The dimension and number of the output arrays are equal
    to the number of indexing dimensions.  If the step length is not a
    complex number, then the stop is not inclusive.

    However, if the step length is a **complex number** (e.g. 5j), then the
    integer part of its magnitude is interpreted as specifying the
    number of points to create between the start and stop values, where
    the stop value **is inclusive**.

    If instantiated with an argument of ``sparse=True``, the mesh-grid is
    open (or not fleshed out) so that only one-dimension of each returned
    argument is greater than 1.

    Parameters
    ----------
    sparse : bool, optional
        Whether the grid is sparse or not. Default is False.

    Notes
    -----
    Two instances of `nd_grid` are made available in the NumPy namespace,
    `mgrid` and `ogrid`, approximately defined as::

        mgrid = nd_grid(sparse=False)
        ogrid = nd_grid(sparse=True)

    Users should use these pre-defined instances instead of using `nd_grid`
    directly.
    """
    __slots__ = ('sparse',)

    def __init__(self, sparse=False):
        self.sparse = sparse

    def __getitem__(self, key):
        try:
            size = []
            # Mimic the behavior of `np.arange` and use a data type
            # which is at least as large as `np.int_`
            num_list = [0]
            for k in range(len(key)):
                step = key[k].step
                start = key[k].start
                stop = key[k].stop
                if start is None:
                    start = 0
                if step is None:
                    step = 1
                if isinstance(step, (_nx.complexfloating, complex)):
                    step = abs(step)
                    size.append(int(step))
                else:
                    size.append(
                        math.ceil((stop - start) / step))
                num_list += [start, stop, step]
            typ = _nx.result_type(*num_list)
            if self.sparse:
                nn = [_nx.arange(_x, dtype=_t)
                      for _x, _t in zip(size, (typ,) * len(size))]
            else:
                nn = _nx.indices(size, typ)
            for k, kk in enumerate(key):
                step = kk.step
                start = kk.start
                if start is None:
                    start = 0
                if step is None:
                    step = 1
                if isinstance(step, (_nx.complexfloating, complex)):
                    step = int(abs(step))
                    if step != 1:
                        step = (kk.stop - start) / float(step - 1)
                nn[k] = (nn[k] * step + start)
            if self.sparse:
                slobj = [_nx.newaxis] * len(size)
                for k in range(len(size)):
                    slobj[k] = slice(None, None)
                    nn[k] = nn[k][tuple(slobj)]
                    slobj[k] = _nx.newaxis
                return tuple(nn)  # ogrid -> tuple of arrays
            return nn  # mgrid -> ndarray
        except (IndexError, TypeError):
            step = key.step
            stop = key.stop
            start = key.start
            if start is None:
                start = 0
            if isinstance(step, (_nx.complexfloating, complex)):
                # Prevent the (potential) creation of integer arrays
                step_float = abs(step)
                step = length = int(step_float)
                if step != 1:
                    step = (key.stop - start) / float(step - 1)
                typ = _nx.result_type(start, stop, step_float)
                return _nx.arange(0, length, 1, dtype=typ) * step + start
            else:
                return _nx.arange(start, stop, step)


class MGridClass(nd_grid):
    """
    An instance which returns a dense multi-dimensional "meshgrid".

    An instance which returns a dense (or fleshed out) mesh-grid
    when indexed, so that each returned argument has the same shape.
    The dimensions and number of the output arrays are equal to the
    number of indexing dimensions.  If the step length is not a complex
    number, then the stop is not inclusive.

    However, if the step length is a **complex number** (e.g. 5j), then
    the integer part of its magnitude is interpreted as specifying the
    number of points to create between the start and stop values, where
    the stop value **is inclusive**.

    Returns
    -------
    mesh-grid : ndarray
        A single array, containing a set of `ndarray`\\ s all of the same
        dimensions. stacked along the first axis.

    See Also
    --------
    ogrid : like `mgrid` but returns open (not fleshed out) mesh grids
    meshgrid: return coordinate matrices from coordinate vectors
    r_ : array concatenator
    :ref:`how-to-partition`

    Examples
    --------
    >>> import numpy as np
    >>> np.mgrid[0:5, 0:5]
    array([[[0, 0, 0, 0, 0],
            [1, 1, 1, 1, 1],
            [2, 2, 2, 2, 2],
            [3, 3, 3, 3, 3],
            [4, 4, 4, 4, 4]],
           [[0, 1, 2, 3, 4],
            [0, 1, 2, 3, 4],
            [0, 1, 2, 3, 4],
            [0, 1, 2, 3, 4],
            [0, 1, 2, 3, 4]]])
    >>> np.mgrid[-1:1:5j]
    array([-1. , -0.5,  0. ,  0.5,  1. ])

    >>> np.mgrid[0:4].shape
    (4,)
    >>> np.mgrid[0:4, 0:5].shape
    (2, 4, 5)
    >>> np.mgrid[0:4, 0:5, 0:6].shape
    (3, 4, 5, 6)

    """
    __slots__ = ()

    def __init__(self):
        super().__init__(sparse=False)


mgrid = MGridClass()


class OGridClass(nd_grid):
    """
    An instance which returns an open multi-dimensional "meshgrid".

    An instance which returns an open (i.e. not fleshed out) mesh-grid
    when indexed, so that only one dimension of each returned array is
    greater than 1.  The dimension and number of the output arrays are
    equal to the number of indexing dimensions.  If the step length is
    not a complex number, then the stop is not inclusive.

    However, if the step length is a **complex number** (e.g. 5j), then
    the integer part of its magnitude is interpreted as specifying the
    number of points to create between the start and stop values, where
    the stop value **is inclusive**.

    Returns
    -------
    mesh-grid : ndarray or tuple of ndarrays
        If the input is a single slice, returns an array.
        If the input is multiple slices, returns a tuple of arrays, with
        only one dimension not equal to 1.

    See Also
    --------
    mgrid : like `ogrid` but returns dense (or fleshed out) mesh grids
    meshgrid: return coordinate matrices from coordinate vectors
    r_ : array concatenator
    :ref:`how-to-partition`

    Examples
    --------
    >>> from numpy import ogrid
    >>> ogrid[-1:1:5j]
    array([-1. , -0.5,  0. ,  0.5,  1. ])
    >>> ogrid[0:5, 0:5]
    (array([[0],
            [1],
            [2],
            [3],
            [4]]),
     array([[0, 1, 2, 3, 4]]))

    """
    __slots__ = ()

    def __init__(self):
        super().__init__(sparse=True)


ogrid = OGridClass()


class AxisConcatenator:
    """
    Translates slice objects to concatenation along an axis.

    For detailed documentation on usage, see `r_`.
    """
    __slots__ = ('axis', 'matrix', 'ndmin', 'trans1d')

    # allow ma.mr_ to override this
    concatenate = staticmethod(_nx.concatenate)
    makemat = staticmethod(matrixlib.matrix)

    def __init__(self, axis=0, matrix=False, ndmin=1, trans1d=-1):
        self.axis = axis
        self.matrix = matrix
        self.trans1d = trans1d
        self.ndmin = ndmin

    def __getitem__(self, key):
        # handle matrix builder syntax
        if isinstance(key, str):
            frame = sys._getframe().f_back
            mymat = matrixlib.bmat(key, frame.f_globals, frame.f_locals)
            return mymat

        if not isinstance(key, tuple):
            key = (key,)

        # copy attributes, since they can be overridden in the first argument
        trans1d = self.trans1d
        ndmin = self.ndmin
        matrix = self.matrix
        axis = self.axis

        objs = []
        # dtypes or scalars for weak scalar handling in result_type
        result_type_objs = []

        for k, item in enumerate(key):
            scalar = False
            if isinstance(item, slice):
                step = item.step
                start = item.start
                stop = item.stop
                if start is None:
                    start = 0
                if step is None:
                    step = 1
                if isinstance(step, (_nx.complexfloating, complex)):
                    size = int(abs(step))
                    newobj = linspace(start, stop, num=size)
                else:
                    newobj = _nx.arange(start, stop, step)
                if ndmin > 1:
                    newobj = array(newobj, copy=None, ndmin=ndmin)
                    if trans1d != -1:
                        newobj = newobj.swapaxes(-1, trans1d)
            elif isinstance(item, str):
                if k != 0:
                    raise ValueError("special directives must be the "
                                     "first entry.")
                if item in ('r', 'c'):
                    matrix = True
                    col = (item == 'c')
                    continue
                if ',' in item:
                    vec = item.split(',')
                    try:
                        axis, ndmin = [int(x) for x in vec[:2]]
                        if len(vec) == 3:
                            trans1d = int(vec[2])
                        continue
                    except Exception as e:
                        raise ValueError(
                            f"unknown special directive {item!r}"
                        ) from e
                try:
                    axis = int(item)
                    continue
                except (ValueError, TypeError) as e:
                    raise ValueError("unknown special directive") from e
            elif type(item) in ScalarType:
                scalar = True
                newobj = item
            else:
                item_ndim = np.ndim(item)
                newobj = array(item, copy=None, subok=True, ndmin=ndmin)
                if trans1d != -1 and item_ndim < ndmin:
                    k2 = ndmin - item_ndim
                    k1 = trans1d
                    if k1 < 0:
                        k1 += k2 + 1
                    defaxes = list(range(ndmin))
                    axes = defaxes[:k1] + defaxes[k2:] + defaxes[k1:k2]
                    newobj = newobj.transpose(axes)

            objs.append(newobj)
            if scalar:
                result_type_objs.append(item)
            else:
                result_type_objs.append(newobj.dtype)

        # Ensure that scalars won't up-cast unless warranted, for 0, drops
        # through to error in concatenate.
        if len(result_type_objs) != 0:
            final_dtype = _nx.result_type(*result_type_objs)
            # concatenate could do cast, but that can be overridden:
            objs = [array(obj, copy=None, subok=True,
                          ndmin=ndmin, dtype=final_dtype) for obj in objs]

        res = self.concatenate(tuple(objs), axis=axis)

        if matrix:
            oldndim = res.ndim
            res = self.makemat(res)
            if oldndim == 1 and col:
                res = res.T
        return res

    def __len__(self):
        return 0

# separate classes are used here instead of just making r_ = concatenator(0),
# etc. because otherwise we couldn't get the doc string to come out right
# in help(r_)


class RClass(AxisConcatenator):
    """
    Translates slice objects to concatenation along the first axis.

    This is a simple way to build up arrays quickly. There are two use cases.

    1. If the index expression contains comma separated arrays, then stack
       them along their first axis.
    2. If the index expression contains slice notation or scalars then create
       a 1-D array with a range indicated by the slice notation.

    If slice notation is used, the syntax ``start:stop:step`` is equivalent
    to ``np.arange(start, stop, step)`` inside of the brackets. However, if
    ``step`` is an imaginary number (i.e. 100j) then its integer portion is
    interpreted as a number-of-points desired and the start and stop are
    inclusive. In other words ``start:stop:stepj`` is interpreted as
    ``np.linspace(start, stop, step, endpoint=1)`` inside of the brackets.
    After expansion of slice notation, all comma separated sequences are
    concatenated together.

    Optional character strings placed as the first element of the index
    expression can be used to change the output. The strings 'r' or 'c' result
    in matrix output. If the result is 1-D and 'r' is specified a 1 x N (row)
    matrix is produced. If the result is 1-D and 'c' is specified, then a N x 1
    (column) matrix is produced. If the result is 2-D then both provide the
    same matrix result.

    A string integer specifies which axis to stack multiple comma separated
    arrays along. A string of two comma-separated integers allows indication
    of the minimum number of dimensions to force each entry into as the
    second integer (the axis to concatenate along is still the first integer).

    A string with three comma-separated integers allows specification of the
    axis to concatenate along, the minimum number of dimensions to force the
    entries to, and which axis should contain the start of the arrays which
    are less than the specified number of dimensions. In other words the third
    integer allows you to specify where the 1's should be placed in the shape
    of the arrays that have their shapes upgraded. By default, they are placed
    in the front of the shape tuple. The third argument allows you to specify
    where the start of the array should be instead. Thus, a third argument of
    '0' would place the 1's at the end of the array shape. Negative integers
    specify where in the new shape tuple the last dimension of upgraded arrays
    should be placed, so the default is '-1'.

    Parameters
    ----------
    Not a function, so takes no parameters


    Returns
    -------
    A concatenated ndarray or matrix.

    See Also
    --------
    concatenate : Join a sequence of arrays along an existing axis.
    c_ : Translates slice objects to concatenation along the second axis.

    Examples
    --------
    >>> import numpy as np
    >>> np.r_[np.array([1,2,3]), 0, 0, np.array([4,5,6])]
    array([1, 2, 3, ..., 4, 5, 6])
    >>> np.r_[-1:1:6j, [0]*3, 5, 6]
    array([-1. , -0.6, -0.2,  0.2,  0.6,  1. ,  0. ,  0. ,  0. ,  5. ,  6. ])

    String integers specify the axis to concatenate along or the minimum
    number of dimensions to force entries into.

    >>> a = np.array([[0, 1, 2], [3, 4, 5]])
    >>> np.r_['-1', a, a] # concatenate along last axis
    array([[0, 1, 2, 0, 1, 2],
           [3, 4, 5, 3, 4, 5]])
    >>> np.r_['0,2', [1,2,3], [4,5,6]] # concatenate along first axis, dim>=2
    array([[1, 2, 3],
           [4, 5, 6]])

    >>> np.r_['0,2,0', [1,2,3], [4,5,6]]
    array([[1],
           [2],
           [3],
           [4],
           [5],
           [6]])
    >>> np.r_['1,2,0', [1,2,3], [4,5,6]]
    array([[1, 4],
           [2, 5],
           [3, 6]])

    Using 'r' or 'c' as a first string argument creates a matrix.

    >>> np.r_['r',[1,2,3], [4,5,6]]
    matrix([[1, 2, 3, 4, 5, 6]])

    """
    __slots__ = ()

    def __init__(self):
        AxisConcatenator.__init__(self, 0)


r_ = RClass()


class CClass(AxisConcatenator):
    """
    Translates slice objects to concatenation along the second axis.

    This is short-hand for ``np.r_['-1,2,0', index expression]``, which is
    useful because of its common occurrence. In particular, arrays will be
    stacked along their last axis after being upgraded to at least 2-D with
    1's post-pended to the shape (column vectors made out of 1-D arrays).

    See Also
    --------
    column_stack : Stack 1-D arrays as columns into a 2-D array.
    r_ : For more detailed documentation.

    Examples
    --------
    >>> import numpy as np
    >>> np.c_[np.array([1,2,3]), np.array([4,5,6])]
    array([[1, 4],
           [2, 5],
           [3, 6]])
    >>> np.c_[np.array([[1,2,3]]), 0, 0, np.array([[4,5,6]])]
    array([[1, 2, 3, ..., 4, 5, 6]])

    """
    __slots__ = ()

    def __init__(self):
        AxisConcatenator.__init__(self, -1, ndmin=2, trans1d=0)


c_ = CClass()


@set_module('numpy')
class ndenumerate:
    """
    Multidimensional index iterator.

    Return an iterator yielding pairs of array coordinates and values.

    Parameters
    ----------
    arr : ndarray
      Input array.

    See Also
    --------
    ndindex, flatiter

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[1, 2], [3, 4]])
    >>> for index, x in np.ndenumerate(a):
    ...     print(index, x)
    (0, 0) 1
    (0, 1) 2
    (1, 0) 3
    (1, 1) 4

    """

    def __init__(self, arr):
        self.iter = np.asarray(arr).flat

    def __next__(self):
        """
        Standard iterator method, returns the index tuple and array value.

        Returns
        -------
        coords : tuple of ints
            The indices of the current iteration.
        val : scalar
            The array element of the current iteration.

        """
        return self.iter.coords, next(self.iter)

    def __iter__(self):
        return self


@set_module('numpy')
class ndindex:
    """
    An N-dimensional iterator object to index arrays.

    Given the shape of an array, an `ndindex` instance iterates over
    the N-dimensional index of the array. At each iteration a tuple
    of indices is returned, the last dimension is iterated over first.

    Parameters
    ----------
    shape : ints, or a single tuple of ints
        The size of each dimension of the array can be passed as
        individual parameters or as the elements of a tuple.

    See Also
    --------
    ndenumerate, flatiter

    Examples
    --------
    >>> import numpy as np

    Dimensions as individual arguments

    >>> for index in np.ndindex(3, 2, 1):
    ...     print(index)
    (0, 0, 0)
    (0, 1, 0)
    (1, 0, 0)
    (1, 1, 0)
    (2, 0, 0)
    (2, 1, 0)

    Same dimensions - but in a tuple ``(3, 2, 1)``

    >>> for index in np.ndindex((3, 2, 1)):
    ...     print(index)
    (0, 0, 0)
    (0, 1, 0)
    (1, 0, 0)
    (1, 1, 0)
    (2, 0, 0)
    (2, 1, 0)

    """

    def __init__(self, *shape):
        if len(shape) == 1 and isinstance(shape[0], tuple):
            shape = shape[0]
        x = as_strided(_nx.zeros(1), shape=shape,
                       strides=_nx.zeros_like(shape))
        self._it = _nx.nditer(x, flags=['multi_index', 'zerosize_ok'],
                              order='C')

    def __iter__(self):
        return self

    def ndincr(self):
        """
        Increment the multi-dimensional index by one.

        This method is for backward compatibility only: do not use.

        .. deprecated:: 1.20.0
            This method has been advised against since numpy 1.8.0, but only
            started emitting DeprecationWarning as of this version.
        """
        # NumPy 1.20.0, 2020-09-08
        warnings.warn(
            "`ndindex.ndincr()` is deprecated, use `next(ndindex)` instead",
            DeprecationWarning, stacklevel=2)
        next(self)

    def __next__(self):
        """
        Standard iterator method, updates the index and returns the index
        tuple.

        Returns
        -------
        val : tuple of ints
            Returns a tuple containing the indices of the current
            iteration.

        """
        next(self._it)
        return self._it.multi_index


# You can do all this with slice() plus a few special objects,
# but there's a lot to remember. This version is simpler because
# it uses the standard array indexing syntax.
#
# Written by Konrad Hinsen <hinsen@cnrs-orleans.fr>
# last revision: 1999-7-23
#
# Cosmetic changes by T. Oliphant 2001
#
#

class IndexExpression:
    """
    A nicer way to build up index tuples for arrays.

    .. note::
       Use one of the two predefined instances ``index_exp`` or `s_`
       rather than directly using `IndexExpression`.

    For any index combination, including slicing and axis insertion,
    ``a[indices]`` is the same as ``a[np.index_exp[indices]]`` for any
    array `a`. However, ``np.index_exp[indices]`` can be used anywhere
    in Python code and returns a tuple of slice objects that can be
    used in the construction of complex index expressions.

    Parameters
    ----------
    maketuple : bool
        If True, always returns a tuple.

    See Also
    --------
    s_ : Predefined instance without tuple conversion:
       `s_ = IndexExpression(maketuple=False)`.
       The ``index_exp`` is another predefined instance that
       always returns a tuple:
       `index_exp = IndexExpression(maketuple=True)`.

    Notes
    -----
    You can do all this with :class:`slice` plus a few special objects,
    but there's a lot to remember and this version is simpler because
    it uses the standard array indexing syntax.

    Examples
    --------
    >>> import numpy as np
    >>> np.s_[2::2]
    slice(2, None, 2)
    >>> np.index_exp[2::2]
    (slice(2, None, 2),)

    >>> np.array([0, 1, 2, 3, 4])[np.s_[2::2]]
    array([2, 4])

    """
    __slots__ = ('maketuple',)

    def __init__(self, maketuple):
        self.maketuple = maketuple

    def __getitem__(self, item):
        if self.maketuple and not isinstance(item, tuple):
            return (item,)
        else:
            return item


index_exp = IndexExpression(maketuple=True)
s_ = IndexExpression(maketuple=False)

# End contribution from Konrad.


# The following functions complement those in twodim_base, but are
# applicable to N-dimensions.


def _fill_diagonal_dispatcher(a, val, wrap=None):
    return (a,)


@array_function_dispatch(_fill_diagonal_dispatcher)
def fill_diagonal(a, val, wrap=False):
    """Fill the main diagonal of the given array of any dimensionality.

    For an array `a` with ``a.ndim >= 2``, the diagonal is the list of
    values ``a[i, ..., i]`` with indices ``i`` all identical.  This function
    modifies the input array in-place without returning a value.

    Parameters
    ----------
    a : array, at least 2-D.
      Array whose diagonal is to be filled in-place.
    val : scalar or array_like
      Value(s) to write on the diagonal. If `val` is scalar, the value is
      written along the diagonal. If array-like, the flattened `val` is
      written along the diagonal, repeating if necessary to fill all
      diagonal entries.

    wrap : bool
      For tall matrices in NumPy version up to 1.6.2, the
      diagonal "wrapped" after N columns. You can have this behavior
      with this option. This affects only tall matrices.

    See also
    --------
    diag_indices, diag_indices_from

    Notes
    -----
    This functionality can be obtained via `diag_indices`, but internally
    this version uses a much faster implementation that never constructs the
    indices and uses simple slicing.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.zeros((3, 3), int)
    >>> np.fill_diagonal(a, 5)
    >>> a
    array([[5, 0, 0],
           [0, 5, 0],
           [0, 0, 5]])

    The same function can operate on a 4-D array:

    >>> a = np.zeros((3, 3, 3, 3), int)
    >>> np.fill_diagonal(a, 4)

    We only show a few blocks for clarity:

    >>> a[0, 0]
    array([[4, 0, 0],
           [0, 0, 0],
           [0, 0, 0]])
    >>> a[1, 1]
    array([[0, 0, 0],
           [0, 4, 0],
           [0, 0, 0]])
    >>> a[2, 2]
    array([[0, 0, 0],
           [0, 0, 0],
           [0, 0, 4]])

    The wrap option affects only tall matrices:

    >>> # tall matrices no wrap
    >>> a = np.zeros((5, 3), int)
    >>> np.fill_diagonal(a, 4)
    >>> a
    array([[4, 0, 0],
           [0, 4, 0],
           [0, 0, 4],
           [0, 0, 0],
           [0, 0, 0]])

    >>> # tall matrices wrap
    >>> a = np.zeros((5, 3), int)
    >>> np.fill_diagonal(a, 4, wrap=True)
    >>> a
    array([[4, 0, 0],
           [0, 4, 0],
           [0, 0, 4],
           [0, 0, 0],
           [4, 0, 0]])

    >>> # wide matrices
    >>> a = np.zeros((3, 5), int)
    >>> np.fill_diagonal(a, 4, wrap=True)
    >>> a
    array([[4, 0, 0, 0, 0],
           [0, 4, 0, 0, 0],
           [0, 0, 4, 0, 0]])

    The anti-diagonal can be filled by reversing the order of elements
    using either `numpy.flipud` or `numpy.fliplr`.

    >>> a = np.zeros((3, 3), int);
    >>> np.fill_diagonal(np.fliplr(a), [1,2,3])  # Horizontal flip
    >>> a
    array([[0, 0, 1],
           [0, 2, 0],
           [3, 0, 0]])
    >>> np.fill_diagonal(np.flipud(a), [1,2,3])  # Vertical flip
    >>> a
    array([[0, 0, 3],
           [0, 2, 0],
           [1, 0, 0]])

    Note that the order in which the diagonal is filled varies depending
    on the flip function.
    """
    if a.ndim < 2:
        raise ValueError("array must be at least 2-d")
    end = None
    if a.ndim == 2:
        # Explicit, fast formula for the common case.  For 2-d arrays, we
        # accept rectangular ones.
        step = a.shape[1] + 1
        # This is needed to don't have tall matrix have the diagonal wrap.
        if not wrap:
            end = a.shape[1] * a.shape[1]
    else:
        # For more than d=2, the strided formula is only valid for arrays with
        # all dimensions equal, so we check first.
        if not np.all(diff(a.shape) == 0):
            raise ValueError("All dimensions of input must be of equal length")
        step = 1 + (np.cumprod(a.shape[:-1])).sum()

    # Write the value out into the diagonal.
    a.flat[:end:step] = val


@set_module('numpy')
def diag_indices(n, ndim=2):
    """
    Return the indices to access the main diagonal of an array.

    This returns a tuple of indices that can be used to access the main
    diagonal of an array `a` with ``a.ndim >= 2`` dimensions and shape
    (n, n, ..., n). For ``a.ndim = 2`` this is the usual diagonal, for
    ``a.ndim > 2`` this is the set of indices to access ``a[i, i, ..., i]``
    for ``i = [0..n-1]``.

    Parameters
    ----------
    n : int
      The size, along each dimension, of the arrays for which the returned
      indices can be used.

    ndim : int, optional
      The number of dimensions.

    See Also
    --------
    diag_indices_from

    Examples
    --------
    >>> import numpy as np

    Create a set of indices to access the diagonal of a (4, 4) array:

    >>> di = np.diag_indices(4)
    >>> di
    (array([0, 1, 2, 3]), array([0, 1, 2, 3]))
    >>> a = np.arange(16).reshape(4, 4)
    >>> a
    array([[ 0,  1,  2,  3],
           [ 4,  5,  6,  7],
           [ 8,  9, 10, 11],
           [12, 13, 14, 15]])
    >>> a[di] = 100
    >>> a
    array([[100,   1,   2,   3],
           [  4, 100,   6,   7],
           [  8,   9, 100,  11],
           [ 12,  13,  14, 100]])

    Now, we create indices to manipulate a 3-D array:

    >>> d3 = np.diag_indices(2, 3)
    >>> d3
    (array([0, 1]), array([0, 1]), array([0, 1]))

    And use it to set the diagonal of an array of zeros to 1:

    >>> a = np.zeros((2, 2, 2), dtype=int)
    >>> a[d3] = 1
    >>> a
    array([[[1, 0],
            [0, 0]],
           [[0, 0],
            [0, 1]]])

    """
    idx = np.arange(n)
    return (idx,) * ndim


def _diag_indices_from(arr):
    return (arr,)


@array_function_dispatch(_diag_indices_from)
def diag_indices_from(arr):
    """
    Return the indices to access the main diagonal of an n-dimensional array.

    See `diag_indices` for full details.

    Parameters
    ----------
    arr : array, at least 2-D

    See Also
    --------
    diag_indices

    Examples
    --------
    >>> import numpy as np

    Create a 4 by 4 array.

    >>> a = np.arange(16).reshape(4, 4)
    >>> a
    array([[ 0,  1,  2,  3],
           [ 4,  5,  6,  7],
           [ 8,  9, 10, 11],
           [12, 13, 14, 15]])

    Get the indices of the diagonal elements.

    >>> di = np.diag_indices_from(a)
    >>> di
    (array([0, 1, 2, 3]), array([0, 1, 2, 3]))

    >>> a[di]
    array([ 0,  5, 10, 15])

    This is simply syntactic sugar for diag_indices.

    >>> np.diag_indices(a.shape[0])
    (array([0, 1, 2, 3]), array([0, 1, 2, 3]))

    """

    if not arr.ndim >= 2:
        raise ValueError("input array must be at least 2-d")
    # For more than d=2, the strided formula is only valid for arrays with
    # all dimensions equal, so we check first.
    if not np.all(diff(arr.shape) == 0):
        raise ValueError("All dimensions of input must be of equal length")

    return diag_indices(arr.shape[0], arr.ndim)

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\_index_tricks_impl.py ===
import functools
import math
import sys
import warnings

import numpy as np
import numpy._core.numeric as _nx
import numpy.matrixlib as matrixlib
from numpy._core import linspace, overrides
from numpy._core.multiarray import ravel_multi_index, unravel_index
from numpy._core.numeric import ScalarType, array
from numpy._core.numerictypes import issubdtype
from numpy._utils import set_module
from numpy.lib._function_base_impl import diff
from numpy.lib.stride_tricks import as_strided

array_function_dispatch = functools.partial(
    overrides.array_function_dispatch, module='numpy')


__all__ = [
    'ravel_multi_index', 'unravel_index', 'mgrid', 'ogrid', 'r_', 'c_',
    's_', 'index_exp', 'ix_', 'ndenumerate', 'ndindex', 'fill_diagonal',
    'diag_indices', 'diag_indices_from'
]


def _ix__dispatcher(*args):
    return args


@array_function_dispatch(_ix__dispatcher)
def ix_(*args):
    """
    Construct an open mesh from multiple sequences.

    This function takes N 1-D sequences and returns N outputs with N
    dimensions each, such that the shape is 1 in all but one dimension
    and the dimension with the non-unit shape value cycles through all
    N dimensions.

    Using `ix_` one can quickly construct index arrays that will index
    the cross product. ``a[np.ix_([1,3],[2,5])]`` returns the array
    ``[[a[1,2] a[1,5]], [a[3,2] a[3,5]]]``.

    Parameters
    ----------
    args : 1-D sequences
        Each sequence should be of integer or boolean type.
        Boolean sequences will be interpreted as boolean masks for the
        corresponding dimension (equivalent to passing in
        ``np.nonzero(boolean_sequence)``).

    Returns
    -------
    out : tuple of ndarrays
        N arrays with N dimensions each, with N the number of input
        sequences. Together these arrays form an open mesh.

    See Also
    --------
    ogrid, mgrid, meshgrid

    Examples
    --------
    >>> import numpy as np
    >>> a = np.arange(10).reshape(2, 5)
    >>> a
    array([[0, 1, 2, 3, 4],
           [5, 6, 7, 8, 9]])
    >>> ixgrid = np.ix_([0, 1], [2, 4])
    >>> ixgrid
    (array([[0],
           [1]]), array([[2, 4]]))
    >>> ixgrid[0].shape, ixgrid[1].shape
    ((2, 1), (1, 2))
    >>> a[ixgrid]
    array([[2, 4],
           [7, 9]])

    >>> ixgrid = np.ix_([True, True], [2, 4])
    >>> a[ixgrid]
    array([[2, 4],
           [7, 9]])
    >>> ixgrid = np.ix_([True, True], [False, False, True, False, True])
    >>> a[ixgrid]
    array([[2, 4],
           [7, 9]])

    """
    out = []
    nd = len(args)
    for k, new in enumerate(args):
        if not isinstance(new, _nx.ndarray):
            new = np.asarray(new)
            if new.size == 0:
                # Explicitly type empty arrays to avoid float default
                new = new.astype(_nx.intp)
        if new.ndim != 1:
            raise ValueError("Cross index must be 1 dimensional")
        if issubdtype(new.dtype, _nx.bool):
            new, = new.nonzero()
        new = new.reshape((1,) * k + (new.size,) + (1,) * (nd - k - 1))
        out.append(new)
    return tuple(out)


class nd_grid:
    """
    Construct a multi-dimensional "meshgrid".

    ``grid = nd_grid()`` creates an instance which will return a mesh-grid
    when indexed.  The dimension and number of the output arrays are equal
    to the number of indexing dimensions.  If the step length is not a
    complex number, then the stop is not inclusive.

    However, if the step length is a **complex number** (e.g. 5j), then the
    integer part of its magnitude is interpreted as specifying the
    number of points to create between the start and stop values, where
    the stop value **is inclusive**.

    If instantiated with an argument of ``sparse=True``, the mesh-grid is
    open (or not fleshed out) so that only one-dimension of each returned
    argument is greater than 1.

    Parameters
    ----------
    sparse : bool, optional
        Whether the grid is sparse or not. Default is False.

    Notes
    -----
    Two instances of `nd_grid` are made available in the NumPy namespace,
    `mgrid` and `ogrid`, approximately defined as::

        mgrid = nd_grid(sparse=False)
        ogrid = nd_grid(sparse=True)

    Users should use these pre-defined instances instead of using `nd_grid`
    directly.
    """
    __slots__ = ('sparse',)

    def __init__(self, sparse=False):
        self.sparse = sparse

    def __getitem__(self, key):
        try:
            size = []
            # Mimic the behavior of `np.arange` and use a data type
            # which is at least as large as `np.int_`
            num_list = [0]
            for k in range(len(key)):
                step = key[k].step
                start = key[k].start
                stop = key[k].stop
                if start is None:
                    start = 0
                if step is None:
                    step = 1
                if isinstance(step, (_nx.complexfloating, complex)):
                    step = abs(step)
                    size.append(int(step))
                else:
                    size.append(
                        math.ceil((stop - start) / step))
                num_list += [start, stop, step]
            typ = _nx.result_type(*num_list)
            if self.sparse:
                nn = [_nx.arange(_x, dtype=_t)
                      for _x, _t in zip(size, (typ,) * len(size))]
            else:
                nn = _nx.indices(size, typ)
            for k, kk in enumerate(key):
                step = kk.step
                start = kk.start
                if start is None:
                    start = 0
                if step is None:
                    step = 1
                if isinstance(step, (_nx.complexfloating, complex)):
                    step = int(abs(step))
                    if step != 1:
                        step = (kk.stop - start) / float(step - 1)
                nn[k] = (nn[k] * step + start)
            if self.sparse:
                slobj = [_nx.newaxis] * len(size)
                for k in range(len(size)):
                    slobj[k] = slice(None, None)
                    nn[k] = nn[k][tuple(slobj)]
                    slobj[k] = _nx.newaxis
                return tuple(nn)  # ogrid -> tuple of arrays
            return nn  # mgrid -> ndarray
        except (IndexError, TypeError):
            step = key.step
            stop = key.stop
            start = key.start
            if start is None:
                start = 0
            if isinstance(step, (_nx.complexfloating, complex)):
                # Prevent the (potential) creation of integer arrays
                step_float = abs(step)
                step = length = int(step_float)
                if step != 1:
                    step = (key.stop - start) / float(step - 1)
                typ = _nx.result_type(start, stop, step_float)
                return _nx.arange(0, length, 1, dtype=typ) * step + start
            else:
                return _nx.arange(start, stop, step)


class MGridClass(nd_grid):
    """
    An instance which returns a dense multi-dimensional "meshgrid".

    An instance which returns a dense (or fleshed out) mesh-grid
    when indexed, so that each returned argument has the same shape.
    The dimensions and number of the output arrays are equal to the
    number of indexing dimensions.  If the step length is not a complex
    number, then the stop is not inclusive.

    However, if the step length is a **complex number** (e.g. 5j), then
    the integer part of its magnitude is interpreted as specifying the
    number of points to create between the start and stop values, where
    the stop value **is inclusive**.

    Returns
    -------
    mesh-grid : ndarray
        A single array, containing a set of `ndarray`\\ s all of the same
        dimensions. stacked along the first axis.

    See Also
    --------
    ogrid : like `mgrid` but returns open (not fleshed out) mesh grids
    meshgrid: return coordinate matrices from coordinate vectors
    r_ : array concatenator
    :ref:`how-to-partition`

    Examples
    --------
    >>> import numpy as np
    >>> np.mgrid[0:5, 0:5]
    array([[[0, 0, 0, 0, 0],
            [1, 1, 1, 1, 1],
            [2, 2, 2, 2, 2],
            [3, 3, 3, 3, 3],
            [4, 4, 4, 4, 4]],
           [[0, 1, 2, 3, 4],
            [0, 1, 2, 3, 4],
            [0, 1, 2, 3, 4],
            [0, 1, 2, 3, 4],
            [0, 1, 2, 3, 4]]])
    >>> np.mgrid[-1:1:5j]
    array([-1. , -0.5,  0. ,  0.5,  1. ])

    >>> np.mgrid[0:4].shape
    (4,)
    >>> np.mgrid[0:4, 0:5].shape
    (2, 4, 5)
    >>> np.mgrid[0:4, 0:5, 0:6].shape
    (3, 4, 5, 6)

    """
    __slots__ = ()

    def __init__(self):
        super().__init__(sparse=False)


mgrid = MGridClass()


class OGridClass(nd_grid):
    """
    An instance which returns an open multi-dimensional "meshgrid".

    An instance which returns an open (i.e. not fleshed out) mesh-grid
    when indexed, so that only one dimension of each returned array is
    greater than 1.  The dimension and number of the output arrays are
    equal to the number of indexing dimensions.  If the step length is
    not a complex number, then the stop is not inclusive.

    However, if the step length is a **complex number** (e.g. 5j), then
    the integer part of its magnitude is interpreted as specifying the
    number of points to create between the start and stop values, where
    the stop value **is inclusive**.

    Returns
    -------
    mesh-grid : ndarray or tuple of ndarrays
        If the input is a single slice, returns an array.
        If the input is multiple slices, returns a tuple of arrays, with
        only one dimension not equal to 1.

    See Also
    --------
    mgrid : like `ogrid` but returns dense (or fleshed out) mesh grids
    meshgrid: return coordinate matrices from coordinate vectors
    r_ : array concatenator
    :ref:`how-to-partition`

    Examples
    --------
    >>> from numpy import ogrid
    >>> ogrid[-1:1:5j]
    array([-1. , -0.5,  0. ,  0.5,  1. ])
    >>> ogrid[0:5, 0:5]
    (array([[0],
            [1],
            [2],
            [3],
            [4]]),
     array([[0, 1, 2, 3, 4]]))

    """
    __slots__ = ()

    def __init__(self):
        super().__init__(sparse=True)


ogrid = OGridClass()


class AxisConcatenator:
    """
    Translates slice objects to concatenation along an axis.

    For detailed documentation on usage, see `r_`.
    """
    __slots__ = ('axis', 'matrix', 'ndmin', 'trans1d')

    # allow ma.mr_ to override this
    concatenate = staticmethod(_nx.concatenate)
    makemat = staticmethod(matrixlib.matrix)

    def __init__(self, axis=0, matrix=False, ndmin=1, trans1d=-1):
        self.axis = axis
        self.matrix = matrix
        self.trans1d = trans1d
        self.ndmin = ndmin

    def __getitem__(self, key):
        # handle matrix builder syntax
        if isinstance(key, str):
            frame = sys._getframe().f_back
            mymat = matrixlib.bmat(key, frame.f_globals, frame.f_locals)
            return mymat

        if not isinstance(key, tuple):
            key = (key,)

        # copy attributes, since they can be overridden in the first argument
        trans1d = self.trans1d
        ndmin = self.ndmin
        matrix = self.matrix
        axis = self.axis

        objs = []
        # dtypes or scalars for weak scalar handling in result_type
        result_type_objs = []

        for k, item in enumerate(key):
            scalar = False
            if isinstance(item, slice):
                step = item.step
                start = item.start
                stop = item.stop
                if start is None:
                    start = 0
                if step is None:
                    step = 1
                if isinstance(step, (_nx.complexfloating, complex)):
                    size = int(abs(step))
                    newobj = linspace(start, stop, num=size)
                else:
                    newobj = _nx.arange(start, stop, step)
                if ndmin > 1:
                    newobj = array(newobj, copy=None, ndmin=ndmin)
                    if trans1d != -1:
                        newobj = newobj.swapaxes(-1, trans1d)
            elif isinstance(item, str):
                if k != 0:
                    raise ValueError("special directives must be the "
                                     "first entry.")
                if item in ('r', 'c'):
                    matrix = True
                    col = (item == 'c')
                    continue
                if ',' in item:
                    vec = item.split(',')
                    try:
                        axis, ndmin = [int(x) for x in vec[:2]]
                        if len(vec) == 3:
                            trans1d = int(vec[2])
                        continue
                    except Exception as e:
                        raise ValueError(
                            f"unknown special directive {item!r}"
                        ) from e
                try:
                    axis = int(item)
                    continue
                except (ValueError, TypeError) as e:
                    raise ValueError("unknown special directive") from e
            elif type(item) in ScalarType:
                scalar = True
                newobj = item
            else:
                item_ndim = np.ndim(item)
                newobj = array(item, copy=None, subok=True, ndmin=ndmin)
                if trans1d != -1 and item_ndim < ndmin:
                    k2 = ndmin - item_ndim
                    k1 = trans1d
                    if k1 < 0:
                        k1 += k2 + 1
                    defaxes = list(range(ndmin))
                    axes = defaxes[:k1] + defaxes[k2:] + defaxes[k1:k2]
                    newobj = newobj.transpose(axes)

            objs.append(newobj)
            if scalar:
                result_type_objs.append(item)
            else:
                result_type_objs.append(newobj.dtype)

        # Ensure that scalars won't up-cast unless warranted, for 0, drops
        # through to error in concatenate.
        if len(result_type_objs) != 0:
            final_dtype = _nx.result_type(*result_type_objs)
            # concatenate could do cast, but that can be overridden:
            objs = [array(obj, copy=None, subok=True,
                          ndmin=ndmin, dtype=final_dtype) for obj in objs]

        res = self.concatenate(tuple(objs), axis=axis)

        if matrix:
            oldndim = res.ndim
            res = self.makemat(res)
            if oldndim == 1 and col:
                res = res.T
        return res

    def __len__(self):
        return 0

# separate classes are used here instead of just making r_ = concatenator(0),
# etc. because otherwise we couldn't get the doc string to come out right
# in help(r_)


class RClass(AxisConcatenator):
    """
    Translates slice objects to concatenation along the first axis.

    This is a simple way to build up arrays quickly. There are two use cases.

    1. If the index expression contains comma separated arrays, then stack
       them along their first axis.
    2. If the index expression contains slice notation or scalars then create
       a 1-D array with a range indicated by the slice notation.

    If slice notation is used, the syntax ``start:stop:step`` is equivalent
    to ``np.arange(start, stop, step)`` inside of the brackets. However, if
    ``step`` is an imaginary number (i.e. 100j) then its integer portion is
    interpreted as a number-of-points desired and the start and stop are
    inclusive. In other words ``start:stop:stepj`` is interpreted as
    ``np.linspace(start, stop, step, endpoint=1)`` inside of the brackets.
    After expansion of slice notation, all comma separated sequences are
    concatenated together.

    Optional character strings placed as the first element of the index
    expression can be used to change the output. The strings 'r' or 'c' result
    in matrix output. If the result is 1-D and 'r' is specified a 1 x N (row)
    matrix is produced. If the result is 1-D and 'c' is specified, then a N x 1
    (column) matrix is produced. If the result is 2-D then both provide the
    same matrix result.

    A string integer specifies which axis to stack multiple comma separated
    arrays along. A string of two comma-separated integers allows indication
    of the minimum number of dimensions to force each entry into as the
    second integer (the axis to concatenate along is still the first integer).

    A string with three comma-separated integers allows specification of the
    axis to concatenate along, the minimum number of dimensions to force the
    entries to, and which axis should contain the start of the arrays which
    are less than the specified number of dimensions. In other words the third
    integer allows you to specify where the 1's should be placed in the shape
    of the arrays that have their shapes upgraded. By default, they are placed
    in the front of the shape tuple. The third argument allows you to specify
    where the start of the array should be instead. Thus, a third argument of
    '0' would place the 1's at the end of the array shape. Negative integers
    specify where in the new shape tuple the last dimension of upgraded arrays
    should be placed, so the default is '-1'.

    Parameters
    ----------
    Not a function, so takes no parameters


    Returns
    -------
    A concatenated ndarray or matrix.

    See Also
    --------
    concatenate : Join a sequence of arrays along an existing axis.
    c_ : Translates slice objects to concatenation along the second axis.

    Examples
    --------
    >>> import numpy as np
    >>> np.r_[np.array([1,2,3]), 0, 0, np.array([4,5,6])]
    array([1, 2, 3, ..., 4, 5, 6])
    >>> np.r_[-1:1:6j, [0]*3, 5, 6]
    array([-1. , -0.6, -0.2,  0.2,  0.6,  1. ,  0. ,  0. ,  0. ,  5. ,  6. ])

    String integers specify the axis to concatenate along or the minimum
    number of dimensions to force entries into.

    >>> a = np.array([[0, 1, 2], [3, 4, 5]])
    >>> np.r_['-1', a, a] # concatenate along last axis
    array([[0, 1, 2, 0, 1, 2],
           [3, 4, 5, 3, 4, 5]])
    >>> np.r_['0,2', [1,2,3], [4,5,6]] # concatenate along first axis, dim>=2
    array([[1, 2, 3],
           [4, 5, 6]])

    >>> np.r_['0,2,0', [1,2,3], [4,5,6]]
    array([[1],
           [2],
           [3],
           [4],
           [5],
           [6]])
    >>> np.r_['1,2,0', [1,2,3], [4,5,6]]
    array([[1, 4],
           [2, 5],
           [3, 6]])

    Using 'r' or 'c' as a first string argument creates a matrix.

    >>> np.r_['r',[1,2,3], [4,5,6]]
    matrix([[1, 2, 3, 4, 5, 6]])

    """
    __slots__ = ()

    def __init__(self):
        AxisConcatenator.__init__(self, 0)


r_ = RClass()


class CClass(AxisConcatenator):
    """
    Translates slice objects to concatenation along the second axis.

    This is short-hand for ``np.r_['-1,2,0', index expression]``, which is
    useful because of its common occurrence. In particular, arrays will be
    stacked along their last axis after being upgraded to at least 2-D with
    1's post-pended to the shape (column vectors made out of 1-D arrays).

    See Also
    --------
    column_stack : Stack 1-D arrays as columns into a 2-D array.
    r_ : For more detailed documentation.

    Examples
    --------
    >>> import numpy as np
    >>> np.c_[np.array([1,2,3]), np.array([4,5,6])]
    array([[1, 4],
           [2, 5],
           [3, 6]])
    >>> np.c_[np.array([[1,2,3]]), 0, 0, np.array([[4,5,6]])]
    array([[1, 2, 3, ..., 4, 5, 6]])

    """
    __slots__ = ()

    def __init__(self):
        AxisConcatenator.__init__(self, -1, ndmin=2, trans1d=0)


c_ = CClass()


@set_module('numpy')
class ndenumerate:
    """
    Multidimensional index iterator.

    Return an iterator yielding pairs of array coordinates and values.

    Parameters
    ----------
    arr : ndarray
      Input array.

    See Also
    --------
    ndindex, flatiter

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[1, 2], [3, 4]])
    >>> for index, x in np.ndenumerate(a):
    ...     print(index, x)
    (0, 0) 1
    (0, 1) 2
    (1, 0) 3
    (1, 1) 4

    """

    def __init__(self, arr):
        self.iter = np.asarray(arr).flat

    def __next__(self):
        """
        Standard iterator method, returns the index tuple and array value.

        Returns
        -------
        coords : tuple of ints
            The indices of the current iteration.
        val : scalar
            The array element of the current iteration.

        """
        return self.iter.coords, next(self.iter)

    def __iter__(self):
        return self


@set_module('numpy')
class ndindex:
    """
    An N-dimensional iterator object to index arrays.

    Given the shape of an array, an `ndindex` instance iterates over
    the N-dimensional index of the array. At each iteration a tuple
    of indices is returned, the last dimension is iterated over first.

    Parameters
    ----------
    shape : ints, or a single tuple of ints
        The size of each dimension of the array can be passed as
        individual parameters or as the elements of a tuple.

    See Also
    --------
    ndenumerate, flatiter

    Examples
    --------
    >>> import numpy as np

    Dimensions as individual arguments

    >>> for index in np.ndindex(3, 2, 1):
    ...     print(index)
    (0, 0, 0)
    (0, 1, 0)
    (1, 0, 0)
    (1, 1, 0)
    (2, 0, 0)
    (2, 1, 0)

    Same dimensions - but in a tuple ``(3, 2, 1)``

    >>> for index in np.ndindex((3, 2, 1)):
    ...     print(index)
    (0, 0, 0)
    (0, 1, 0)
    (1, 0, 0)
    (1, 1, 0)
    (2, 0, 0)
    (2, 1, 0)

    """

    def __init__(self, *shape):
        if len(shape) == 1 and isinstance(shape[0], tuple):
            shape = shape[0]
        x = as_strided(_nx.zeros(1), shape=shape,
                       strides=_nx.zeros_like(shape))
        self._it = _nx.nditer(x, flags=['multi_index', 'zerosize_ok'],
                              order='C')

    def __iter__(self):
        return self

    def ndincr(self):
        """
        Increment the multi-dimensional index by one.

        This method is for backward compatibility only: do not use.

        .. deprecated:: 1.20.0
            This method has been advised against since numpy 1.8.0, but only
            started emitting DeprecationWarning as of this version.
        """
        # NumPy 1.20.0, 2020-09-08
        warnings.warn(
            "`ndindex.ndincr()` is deprecated, use `next(ndindex)` instead",
            DeprecationWarning, stacklevel=2)
        next(self)

    def __next__(self):
        """
        Standard iterator method, updates the index and returns the index
        tuple.

        Returns
        -------
        val : tuple of ints
            Returns a tuple containing the indices of the current
            iteration.

        """
        next(self._it)
        return self._it.multi_index


# You can do all this with slice() plus a few special objects,
# but there's a lot to remember. This version is simpler because
# it uses the standard array indexing syntax.
#
# Written by Konrad Hinsen <hinsen@cnrs-orleans.fr>
# last revision: 1999-7-23
#
# Cosmetic changes by T. Oliphant 2001
#
#

class IndexExpression:
    """
    A nicer way to build up index tuples for arrays.

    .. note::
       Use one of the two predefined instances ``index_exp`` or `s_`
       rather than directly using `IndexExpression`.

    For any index combination, including slicing and axis insertion,
    ``a[indices]`` is the same as ``a[np.index_exp[indices]]`` for any
    array `a`. However, ``np.index_exp[indices]`` can be used anywhere
    in Python code and returns a tuple of slice objects that can be
    used in the construction of complex index expressions.

    Parameters
    ----------
    maketuple : bool
        If True, always returns a tuple.

    See Also
    --------
    s_ : Predefined instance without tuple conversion:
       `s_ = IndexExpression(maketuple=False)`.
       The ``index_exp`` is another predefined instance that
       always returns a tuple:
       `index_exp = IndexExpression(maketuple=True)`.

    Notes
    -----
    You can do all this with :class:`slice` plus a few special objects,
    but there's a lot to remember and this version is simpler because
    it uses the standard array indexing syntax.

    Examples
    --------
    >>> import numpy as np
    >>> np.s_[2::2]
    slice(2, None, 2)
    >>> np.index_exp[2::2]
    (slice(2, None, 2),)

    >>> np.array([0, 1, 2, 3, 4])[np.s_[2::2]]
    array([2, 4])

    """
    __slots__ = ('maketuple',)

    def __init__(self, maketuple):
        self.maketuple = maketuple

    def __getitem__(self, item):
        if self.maketuple and not isinstance(item, tuple):
            return (item,)
        else:
            return item


index_exp = IndexExpression(maketuple=True)
s_ = IndexExpression(maketuple=False)

# End contribution from Konrad.


# The following functions complement those in twodim_base, but are
# applicable to N-dimensions.


def _fill_diagonal_dispatcher(a, val, wrap=None):
    return (a,)


@array_function_dispatch(_fill_diagonal_dispatcher)
def fill_diagonal(a, val, wrap=False):
    """Fill the main diagonal of the given array of any dimensionality.

    For an array `a` with ``a.ndim >= 2``, the diagonal is the list of
    values ``a[i, ..., i]`` with indices ``i`` all identical.  This function
    modifies the input array in-place without returning a value.

    Parameters
    ----------
    a : array, at least 2-D.
      Array whose diagonal is to be filled in-place.
    val : scalar or array_like
      Value(s) to write on the diagonal. If `val` is scalar, the value is
      written along the diagonal. If array-like, the flattened `val` is
      written along the diagonal, repeating if necessary to fill all
      diagonal entries.

    wrap : bool
      For tall matrices in NumPy version up to 1.6.2, the
      diagonal "wrapped" after N columns. You can have this behavior
      with this option. This affects only tall matrices.

    See also
    --------
    diag_indices, diag_indices_from

    Notes
    -----
    This functionality can be obtained via `diag_indices`, but internally
    this version uses a much faster implementation that never constructs the
    indices and uses simple slicing.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.zeros((3, 3), int)
    >>> np.fill_diagonal(a, 5)
    >>> a
    array([[5, 0, 0],
           [0, 5, 0],
           [0, 0, 5]])

    The same function can operate on a 4-D array:

    >>> a = np.zeros((3, 3, 3, 3), int)
    >>> np.fill_diagonal(a, 4)

    We only show a few blocks for clarity:

    >>> a[0, 0]
    array([[4, 0, 0],
           [0, 0, 0],
           [0, 0, 0]])
    >>> a[1, 1]
    array([[0, 0, 0],
           [0, 4, 0],
           [0, 0, 0]])
    >>> a[2, 2]
    array([[0, 0, 0],
           [0, 0, 0],
           [0, 0, 4]])

    The wrap option affects only tall matrices:

    >>> # tall matrices no wrap
    >>> a = np.zeros((5, 3), int)
    >>> np.fill_diagonal(a, 4)
    >>> a
    array([[4, 0, 0],
           [0, 4, 0],
           [0, 0, 4],
           [0, 0, 0],
           [0, 0, 0]])

    >>> # tall matrices wrap
    >>> a = np.zeros((5, 3), int)
    >>> np.fill_diagonal(a, 4, wrap=True)
    >>> a
    array([[4, 0, 0],
           [0, 4, 0],
           [0, 0, 4],
           [0, 0, 0],
           [4, 0, 0]])

    >>> # wide matrices
    >>> a = np.zeros((3, 5), int)
    >>> np.fill_diagonal(a, 4, wrap=True)
    >>> a
    array([[4, 0, 0, 0, 0],
           [0, 4, 0, 0, 0],
           [0, 0, 4, 0, 0]])

    The anti-diagonal can be filled by reversing the order of elements
    using either `numpy.flipud` or `numpy.fliplr`.

    >>> a = np.zeros((3, 3), int);
    >>> np.fill_diagonal(np.fliplr(a), [1,2,3])  # Horizontal flip
    >>> a
    array([[0, 0, 1],
           [0, 2, 0],
           [3, 0, 0]])
    >>> np.fill_diagonal(np.flipud(a), [1,2,3])  # Vertical flip
    >>> a
    array([[0, 0, 3],
           [0, 2, 0],
           [1, 0, 0]])

    Note that the order in which the diagonal is filled varies depending
    on the flip function.
    """
    if a.ndim < 2:
        raise ValueError("array must be at least 2-d")
    end = None
    if a.ndim == 2:
        # Explicit, fast formula for the common case.  For 2-d arrays, we
        # accept rectangular ones.
        step = a.shape[1] + 1
        # This is needed to don't have tall matrix have the diagonal wrap.
        if not wrap:
            end = a.shape[1] * a.shape[1]
    else:
        # For more than d=2, the strided formula is only valid for arrays with
        # all dimensions equal, so we check first.
        if not np.all(diff(a.shape) == 0):
            raise ValueError("All dimensions of input must be of equal length")
        step = 1 + (np.cumprod(a.shape[:-1])).sum()

    # Write the value out into the diagonal.
    a.flat[:end:step] = val


@set_module('numpy')
def diag_indices(n, ndim=2):
    """
    Return the indices to access the main diagonal of an array.

    This returns a tuple of indices that can be used to access the main
    diagonal of an array `a` with ``a.ndim >= 2`` dimensions and shape
    (n, n, ..., n). For ``a.ndim = 2`` this is the usual diagonal, for
    ``a.ndim > 2`` this is the set of indices to access ``a[i, i, ..., i]``
    for ``i = [0..n-1]``.

    Parameters
    ----------
    n : int
      The size, along each dimension, of the arrays for which the returned
      indices can be used.

    ndim : int, optional
      The number of dimensions.

    See Also
    --------
    diag_indices_from

    Examples
    --------
    >>> import numpy as np

    Create a set of indices to access the diagonal of a (4, 4) array:

    >>> di = np.diag_indices(4)
    >>> di
    (array([0, 1, 2, 3]), array([0, 1, 2, 3]))
    >>> a = np.arange(16).reshape(4, 4)
    >>> a
    array([[ 0,  1,  2,  3],
           [ 4,  5,  6,  7],
           [ 8,  9, 10, 11],
           [12, 13, 14, 15]])
    >>> a[di] = 100
    >>> a
    array([[100,   1,   2,   3],
           [  4, 100,   6,   7],
           [  8,   9, 100,  11],
           [ 12,  13,  14, 100]])

    Now, we create indices to manipulate a 3-D array:

    >>> d3 = np.diag_indices(2, 3)
    >>> d3
    (array([0, 1]), array([0, 1]), array([0, 1]))

    And use it to set the diagonal of an array of zeros to 1:

    >>> a = np.zeros((2, 2, 2), dtype=int)
    >>> a[d3] = 1
    >>> a
    array([[[1, 0],
            [0, 0]],
           [[0, 0],
            [0, 1]]])

    """
    idx = np.arange(n)
    return (idx,) * ndim


def _diag_indices_from(arr):
    return (arr,)


@array_function_dispatch(_diag_indices_from)
def diag_indices_from(arr):
    """
    Return the indices to access the main diagonal of an n-dimensional array.

    See `diag_indices` for full details.

    Parameters
    ----------
    arr : array, at least 2-D

    See Also
    --------
    diag_indices

    Examples
    --------
    >>> import numpy as np

    Create a 4 by 4 array.

    >>> a = np.arange(16).reshape(4, 4)
    >>> a
    array([[ 0,  1,  2,  3],
           [ 4,  5,  6,  7],
           [ 8,  9, 10, 11],
           [12, 13, 14, 15]])

    Get the indices of the diagonal elements.

    >>> di = np.diag_indices_from(a)
    >>> di
    (array([0, 1, 2, 3]), array([0, 1, 2, 3]))

    >>> a[di]
    array([ 0,  5, 10, 15])

    This is simply syntactic sugar for diag_indices.

    >>> np.diag_indices(a.shape[0])
    (array([0, 1, 2, 3]), array([0, 1, 2, 3]))

    """

    if not arr.ndim >= 2:
        raise ValueError("input array must be at least 2-d")
    # For more than d=2, the strided formula is only valid for arrays with
    # all dimensions equal, so we check first.
    if not np.all(diff(arr.shape) == 0):
        raise ValueError("All dimensions of input must be of equal length")

    return diag_indices(arr.shape[0], arr.ndim)

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\_index_tricks_impl.py ===
import functools
import math
import sys
import warnings

import numpy as np
import numpy._core.numeric as _nx
import numpy.matrixlib as matrixlib
from numpy._core import linspace, overrides
from numpy._core.multiarray import ravel_multi_index, unravel_index
from numpy._core.numeric import ScalarType, array
from numpy._core.numerictypes import issubdtype
from numpy._utils import set_module
from numpy.lib._function_base_impl import diff
from numpy.lib.stride_tricks import as_strided

array_function_dispatch = functools.partial(
    overrides.array_function_dispatch, module='numpy')


__all__ = [
    'ravel_multi_index', 'unravel_index', 'mgrid', 'ogrid', 'r_', 'c_',
    's_', 'index_exp', 'ix_', 'ndenumerate', 'ndindex', 'fill_diagonal',
    'diag_indices', 'diag_indices_from'
]


def _ix__dispatcher(*args):
    return args


@array_function_dispatch(_ix__dispatcher)
def ix_(*args):
    """
    Construct an open mesh from multiple sequences.

    This function takes N 1-D sequences and returns N outputs with N
    dimensions each, such that the shape is 1 in all but one dimension
    and the dimension with the non-unit shape value cycles through all
    N dimensions.

    Using `ix_` one can quickly construct index arrays that will index
    the cross product. ``a[np.ix_([1,3],[2,5])]`` returns the array
    ``[[a[1,2] a[1,5]], [a[3,2] a[3,5]]]``.

    Parameters
    ----------
    args : 1-D sequences
        Each sequence should be of integer or boolean type.
        Boolean sequences will be interpreted as boolean masks for the
        corresponding dimension (equivalent to passing in
        ``np.nonzero(boolean_sequence)``).

    Returns
    -------
    out : tuple of ndarrays
        N arrays with N dimensions each, with N the number of input
        sequences. Together these arrays form an open mesh.

    See Also
    --------
    ogrid, mgrid, meshgrid

    Examples
    --------
    >>> import numpy as np
    >>> a = np.arange(10).reshape(2, 5)
    >>> a
    array([[0, 1, 2, 3, 4],
           [5, 6, 7, 8, 9]])
    >>> ixgrid = np.ix_([0, 1], [2, 4])
    >>> ixgrid
    (array([[0],
           [1]]), array([[2, 4]]))
    >>> ixgrid[0].shape, ixgrid[1].shape
    ((2, 1), (1, 2))
    >>> a[ixgrid]
    array([[2, 4],
           [7, 9]])

    >>> ixgrid = np.ix_([True, True], [2, 4])
    >>> a[ixgrid]
    array([[2, 4],
           [7, 9]])
    >>> ixgrid = np.ix_([True, True], [False, False, True, False, True])
    >>> a[ixgrid]
    array([[2, 4],
           [7, 9]])

    """
    out = []
    nd = len(args)
    for k, new in enumerate(args):
        if not isinstance(new, _nx.ndarray):
            new = np.asarray(new)
            if new.size == 0:
                # Explicitly type empty arrays to avoid float default
                new = new.astype(_nx.intp)
        if new.ndim != 1:
            raise ValueError("Cross index must be 1 dimensional")
        if issubdtype(new.dtype, _nx.bool):
            new, = new.nonzero()
        new = new.reshape((1,) * k + (new.size,) + (1,) * (nd - k - 1))
        out.append(new)
    return tuple(out)


class nd_grid:
    """
    Construct a multi-dimensional "meshgrid".

    ``grid = nd_grid()`` creates an instance which will return a mesh-grid
    when indexed.  The dimension and number of the output arrays are equal
    to the number of indexing dimensions.  If the step length is not a
    complex number, then the stop is not inclusive.

    However, if the step length is a **complex number** (e.g. 5j), then the
    integer part of its magnitude is interpreted as specifying the
    number of points to create between the start and stop values, where
    the stop value **is inclusive**.

    If instantiated with an argument of ``sparse=True``, the mesh-grid is
    open (or not fleshed out) so that only one-dimension of each returned
    argument is greater than 1.

    Parameters
    ----------
    sparse : bool, optional
        Whether the grid is sparse or not. Default is False.

    Notes
    -----
    Two instances of `nd_grid` are made available in the NumPy namespace,
    `mgrid` and `ogrid`, approximately defined as::

        mgrid = nd_grid(sparse=False)
        ogrid = nd_grid(sparse=True)

    Users should use these pre-defined instances instead of using `nd_grid`
    directly.
    """
    __slots__ = ('sparse',)

    def __init__(self, sparse=False):
        self.sparse = sparse

    def __getitem__(self, key):
        try:
            size = []
            # Mimic the behavior of `np.arange` and use a data type
            # which is at least as large as `np.int_`
            num_list = [0]
            for k in range(len(key)):
                step = key[k].step
                start = key[k].start
                stop = key[k].stop
                if start is None:
                    start = 0
                if step is None:
                    step = 1
                if isinstance(step, (_nx.complexfloating, complex)):
                    step = abs(step)
                    size.append(int(step))
                else:
                    size.append(
                        math.ceil((stop - start) / step))
                num_list += [start, stop, step]
            typ = _nx.result_type(*num_list)
            if self.sparse:
                nn = [_nx.arange(_x, dtype=_t)
                      for _x, _t in zip(size, (typ,) * len(size))]
            else:
                nn = _nx.indices(size, typ)
            for k, kk in enumerate(key):
                step = kk.step
                start = kk.start
                if start is None:
                    start = 0
                if step is None:
                    step = 1
                if isinstance(step, (_nx.complexfloating, complex)):
                    step = int(abs(step))
                    if step != 1:
                        step = (kk.stop - start) / float(step - 1)
                nn[k] = (nn[k] * step + start)
            if self.sparse:
                slobj = [_nx.newaxis] * len(size)
                for k in range(len(size)):
                    slobj[k] = slice(None, None)
                    nn[k] = nn[k][tuple(slobj)]
                    slobj[k] = _nx.newaxis
                return tuple(nn)  # ogrid -> tuple of arrays
            return nn  # mgrid -> ndarray
        except (IndexError, TypeError):
            step = key.step
            stop = key.stop
            start = key.start
            if start is None:
                start = 0
            if isinstance(step, (_nx.complexfloating, complex)):
                # Prevent the (potential) creation of integer arrays
                step_float = abs(step)
                step = length = int(step_float)
                if step != 1:
                    step = (key.stop - start) / float(step - 1)
                typ = _nx.result_type(start, stop, step_float)
                return _nx.arange(0, length, 1, dtype=typ) * step + start
            else:
                return _nx.arange(start, stop, step)


class MGridClass(nd_grid):
    """
    An instance which returns a dense multi-dimensional "meshgrid".

    An instance which returns a dense (or fleshed out) mesh-grid
    when indexed, so that each returned argument has the same shape.
    The dimensions and number of the output arrays are equal to the
    number of indexing dimensions.  If the step length is not a complex
    number, then the stop is not inclusive.

    However, if the step length is a **complex number** (e.g. 5j), then
    the integer part of its magnitude is interpreted as specifying the
    number of points to create between the start and stop values, where
    the stop value **is inclusive**.

    Returns
    -------
    mesh-grid : ndarray
        A single array, containing a set of `ndarray`\\ s all of the same
        dimensions. stacked along the first axis.

    See Also
    --------
    ogrid : like `mgrid` but returns open (not fleshed out) mesh grids
    meshgrid: return coordinate matrices from coordinate vectors
    r_ : array concatenator
    :ref:`how-to-partition`

    Examples
    --------
    >>> import numpy as np
    >>> np.mgrid[0:5, 0:5]
    array([[[0, 0, 0, 0, 0],
            [1, 1, 1, 1, 1],
            [2, 2, 2, 2, 2],
            [3, 3, 3, 3, 3],
            [4, 4, 4, 4, 4]],
           [[0, 1, 2, 3, 4],
            [0, 1, 2, 3, 4],
            [0, 1, 2, 3, 4],
            [0, 1, 2, 3, 4],
            [0, 1, 2, 3, 4]]])
    >>> np.mgrid[-1:1:5j]
    array([-1. , -0.5,  0. ,  0.5,  1. ])

    >>> np.mgrid[0:4].shape
    (4,)
    >>> np.mgrid[0:4, 0:5].shape
    (2, 4, 5)
    >>> np.mgrid[0:4, 0:5, 0:6].shape
    (3, 4, 5, 6)

    """
    __slots__ = ()

    def __init__(self):
        super().__init__(sparse=False)


mgrid = MGridClass()


class OGridClass(nd_grid):
    """
    An instance which returns an open multi-dimensional "meshgrid".

    An instance which returns an open (i.e. not fleshed out) mesh-grid
    when indexed, so that only one dimension of each returned array is
    greater than 1.  The dimension and number of the output arrays are
    equal to the number of indexing dimensions.  If the step length is
    not a complex number, then the stop is not inclusive.

    However, if the step length is a **complex number** (e.g. 5j), then
    the integer part of its magnitude is interpreted as specifying the
    number of points to create between the start and stop values, where
    the stop value **is inclusive**.

    Returns
    -------
    mesh-grid : ndarray or tuple of ndarrays
        If the input is a single slice, returns an array.
        If the input is multiple slices, returns a tuple of arrays, with
        only one dimension not equal to 1.

    See Also
    --------
    mgrid : like `ogrid` but returns dense (or fleshed out) mesh grids
    meshgrid: return coordinate matrices from coordinate vectors
    r_ : array concatenator
    :ref:`how-to-partition`

    Examples
    --------
    >>> from numpy import ogrid
    >>> ogrid[-1:1:5j]
    array([-1. , -0.5,  0. ,  0.5,  1. ])
    >>> ogrid[0:5, 0:5]
    (array([[0],
            [1],
            [2],
            [3],
            [4]]),
     array([[0, 1, 2, 3, 4]]))

    """
    __slots__ = ()

    def __init__(self):
        super().__init__(sparse=True)


ogrid = OGridClass()


class AxisConcatenator:
    """
    Translates slice objects to concatenation along an axis.

    For detailed documentation on usage, see `r_`.
    """
    __slots__ = ('axis', 'matrix', 'ndmin', 'trans1d')

    # allow ma.mr_ to override this
    concatenate = staticmethod(_nx.concatenate)
    makemat = staticmethod(matrixlib.matrix)

    def __init__(self, axis=0, matrix=False, ndmin=1, trans1d=-1):
        self.axis = axis
        self.matrix = matrix
        self.trans1d = trans1d
        self.ndmin = ndmin

    def __getitem__(self, key):
        # handle matrix builder syntax
        if isinstance(key, str):
            frame = sys._getframe().f_back
            mymat = matrixlib.bmat(key, frame.f_globals, frame.f_locals)
            return mymat

        if not isinstance(key, tuple):
            key = (key,)

        # copy attributes, since they can be overridden in the first argument
        trans1d = self.trans1d
        ndmin = self.ndmin
        matrix = self.matrix
        axis = self.axis

        objs = []
        # dtypes or scalars for weak scalar handling in result_type
        result_type_objs = []

        for k, item in enumerate(key):
            scalar = False
            if isinstance(item, slice):
                step = item.step
                start = item.start
                stop = item.stop
                if start is None:
                    start = 0
                if step is None:
                    step = 1
                if isinstance(step, (_nx.complexfloating, complex)):
                    size = int(abs(step))
                    newobj = linspace(start, stop, num=size)
                else:
                    newobj = _nx.arange(start, stop, step)
                if ndmin > 1:
                    newobj = array(newobj, copy=None, ndmin=ndmin)
                    if trans1d != -1:
                        newobj = newobj.swapaxes(-1, trans1d)
            elif isinstance(item, str):
                if k != 0:
                    raise ValueError("special directives must be the "
                                     "first entry.")
                if item in ('r', 'c'):
                    matrix = True
                    col = (item == 'c')
                    continue
                if ',' in item:
                    vec = item.split(',')
                    try:
                        axis, ndmin = [int(x) for x in vec[:2]]
                        if len(vec) == 3:
                            trans1d = int(vec[2])
                        continue
                    except Exception as e:
                        raise ValueError(
                            f"unknown special directive {item!r}"
                        ) from e
                try:
                    axis = int(item)
                    continue
                except (ValueError, TypeError) as e:
                    raise ValueError("unknown special directive") from e
            elif type(item) in ScalarType:
                scalar = True
                newobj = item
            else:
                item_ndim = np.ndim(item)
                newobj = array(item, copy=None, subok=True, ndmin=ndmin)
                if trans1d != -1 and item_ndim < ndmin:
                    k2 = ndmin - item_ndim
                    k1 = trans1d
                    if k1 < 0:
                        k1 += k2 + 1
                    defaxes = list(range(ndmin))
                    axes = defaxes[:k1] + defaxes[k2:] + defaxes[k1:k2]
                    newobj = newobj.transpose(axes)

            objs.append(newobj)
            if scalar:
                result_type_objs.append(item)
            else:
                result_type_objs.append(newobj.dtype)

        # Ensure that scalars won't up-cast unless warranted, for 0, drops
        # through to error in concatenate.
        if len(result_type_objs) != 0:
            final_dtype = _nx.result_type(*result_type_objs)
            # concatenate could do cast, but that can be overridden:
            objs = [array(obj, copy=None, subok=True,
                          ndmin=ndmin, dtype=final_dtype) for obj in objs]

        res = self.concatenate(tuple(objs), axis=axis)

        if matrix:
            oldndim = res.ndim
            res = self.makemat(res)
            if oldndim == 1 and col:
                res = res.T
        return res

    def __len__(self):
        return 0

# separate classes are used here instead of just making r_ = concatenator(0),
# etc. because otherwise we couldn't get the doc string to come out right
# in help(r_)


class RClass(AxisConcatenator):
    """
    Translates slice objects to concatenation along the first axis.

    This is a simple way to build up arrays quickly. There are two use cases.

    1. If the index expression contains comma separated arrays, then stack
       them along their first axis.
    2. If the index expression contains slice notation or scalars then create
       a 1-D array with a range indicated by the slice notation.

    If slice notation is used, the syntax ``start:stop:step`` is equivalent
    to ``np.arange(start, stop, step)`` inside of the brackets. However, if
    ``step`` is an imaginary number (i.e. 100j) then its integer portion is
    interpreted as a number-of-points desired and the start and stop are
    inclusive. In other words ``start:stop:stepj`` is interpreted as
    ``np.linspace(start, stop, step, endpoint=1)`` inside of the brackets.
    After expansion of slice notation, all comma separated sequences are
    concatenated together.

    Optional character strings placed as the first element of the index
    expression can be used to change the output. The strings 'r' or 'c' result
    in matrix output. If the result is 1-D and 'r' is specified a 1 x N (row)
    matrix is produced. If the result is 1-D and 'c' is specified, then a N x 1
    (column) matrix is produced. If the result is 2-D then both provide the
    same matrix result.

    A string integer specifies which axis to stack multiple comma separated
    arrays along. A string of two comma-separated integers allows indication
    of the minimum number of dimensions to force each entry into as the
    second integer (the axis to concatenate along is still the first integer).

    A string with three comma-separated integers allows specification of the
    axis to concatenate along, the minimum number of dimensions to force the
    entries to, and which axis should contain the start of the arrays which
    are less than the specified number of dimensions. In other words the third
    integer allows you to specify where the 1's should be placed in the shape
    of the arrays that have their shapes upgraded. By default, they are placed
    in the front of the shape tuple. The third argument allows you to specify
    where the start of the array should be instead. Thus, a third argument of
    '0' would place the 1's at the end of the array shape. Negative integers
    specify where in the new shape tuple the last dimension of upgraded arrays
    should be placed, so the default is '-1'.

    Parameters
    ----------
    Not a function, so takes no parameters


    Returns
    -------
    A concatenated ndarray or matrix.

    See Also
    --------
    concatenate : Join a sequence of arrays along an existing axis.
    c_ : Translates slice objects to concatenation along the second axis.

    Examples
    --------
    >>> import numpy as np
    >>> np.r_[np.array([1,2,3]), 0, 0, np.array([4,5,6])]
    array([1, 2, 3, ..., 4, 5, 6])
    >>> np.r_[-1:1:6j, [0]*3, 5, 6]
    array([-1. , -0.6, -0.2,  0.2,  0.6,  1. ,  0. ,  0. ,  0. ,  5. ,  6. ])

    String integers specify the axis to concatenate along or the minimum
    number of dimensions to force entries into.

    >>> a = np.array([[0, 1, 2], [3, 4, 5]])
    >>> np.r_['-1', a, a] # concatenate along last axis
    array([[0, 1, 2, 0, 1, 2],
           [3, 4, 5, 3, 4, 5]])
    >>> np.r_['0,2', [1,2,3], [4,5,6]] # concatenate along first axis, dim>=2
    array([[1, 2, 3],
           [4, 5, 6]])

    >>> np.r_['0,2,0', [1,2,3], [4,5,6]]
    array([[1],
           [2],
           [3],
           [4],
           [5],
           [6]])
    >>> np.r_['1,2,0', [1,2,3], [4,5,6]]
    array([[1, 4],
           [2, 5],
           [3, 6]])

    Using 'r' or 'c' as a first string argument creates a matrix.

    >>> np.r_['r',[1,2,3], [4,5,6]]
    matrix([[1, 2, 3, 4, 5, 6]])

    """
    __slots__ = ()

    def __init__(self):
        AxisConcatenator.__init__(self, 0)


r_ = RClass()


class CClass(AxisConcatenator):
    """
    Translates slice objects to concatenation along the second axis.

    This is short-hand for ``np.r_['-1,2,0', index expression]``, which is
    useful because of its common occurrence. In particular, arrays will be
    stacked along their last axis after being upgraded to at least 2-D with
    1's post-pended to the shape (column vectors made out of 1-D arrays).

    See Also
    --------
    column_stack : Stack 1-D arrays as columns into a 2-D array.
    r_ : For more detailed documentation.

    Examples
    --------
    >>> import numpy as np
    >>> np.c_[np.array([1,2,3]), np.array([4,5,6])]
    array([[1, 4],
           [2, 5],
           [3, 6]])
    >>> np.c_[np.array([[1,2,3]]), 0, 0, np.array([[4,5,6]])]
    array([[1, 2, 3, ..., 4, 5, 6]])

    """
    __slots__ = ()

    def __init__(self):
        AxisConcatenator.__init__(self, -1, ndmin=2, trans1d=0)


c_ = CClass()


@set_module('numpy')
class ndenumerate:
    """
    Multidimensional index iterator.

    Return an iterator yielding pairs of array coordinates and values.

    Parameters
    ----------
    arr : ndarray
      Input array.

    See Also
    --------
    ndindex, flatiter

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[1, 2], [3, 4]])
    >>> for index, x in np.ndenumerate(a):
    ...     print(index, x)
    (0, 0) 1
    (0, 1) 2
    (1, 0) 3
    (1, 1) 4

    """

    def __init__(self, arr):
        self.iter = np.asarray(arr).flat

    def __next__(self):
        """
        Standard iterator method, returns the index tuple and array value.

        Returns
        -------
        coords : tuple of ints
            The indices of the current iteration.
        val : scalar
            The array element of the current iteration.

        """
        return self.iter.coords, next(self.iter)

    def __iter__(self):
        return self


@set_module('numpy')
class ndindex:
    """
    An N-dimensional iterator object to index arrays.

    Given the shape of an array, an `ndindex` instance iterates over
    the N-dimensional index of the array. At each iteration a tuple
    of indices is returned, the last dimension is iterated over first.

    Parameters
    ----------
    shape : ints, or a single tuple of ints
        The size of each dimension of the array can be passed as
        individual parameters or as the elements of a tuple.

    See Also
    --------
    ndenumerate, flatiter

    Examples
    --------
    >>> import numpy as np

    Dimensions as individual arguments

    >>> for index in np.ndindex(3, 2, 1):
    ...     print(index)
    (0, 0, 0)
    (0, 1, 0)
    (1, 0, 0)
    (1, 1, 0)
    (2, 0, 0)
    (2, 1, 0)

    Same dimensions - but in a tuple ``(3, 2, 1)``

    >>> for index in np.ndindex((3, 2, 1)):
    ...     print(index)
    (0, 0, 0)
    (0, 1, 0)
    (1, 0, 0)
    (1, 1, 0)
    (2, 0, 0)
    (2, 1, 0)

    """

    def __init__(self, *shape):
        if len(shape) == 1 and isinstance(shape[0], tuple):
            shape = shape[0]
        x = as_strided(_nx.zeros(1), shape=shape,
                       strides=_nx.zeros_like(shape))
        self._it = _nx.nditer(x, flags=['multi_index', 'zerosize_ok'],
                              order='C')

    def __iter__(self):
        return self

    def ndincr(self):
        """
        Increment the multi-dimensional index by one.

        This method is for backward compatibility only: do not use.

        .. deprecated:: 1.20.0
            This method has been advised against since numpy 1.8.0, but only
            started emitting DeprecationWarning as of this version.
        """
        # NumPy 1.20.0, 2020-09-08
        warnings.warn(
            "`ndindex.ndincr()` is deprecated, use `next(ndindex)` instead",
            DeprecationWarning, stacklevel=2)
        next(self)

    def __next__(self):
        """
        Standard iterator method, updates the index and returns the index
        tuple.

        Returns
        -------
        val : tuple of ints
            Returns a tuple containing the indices of the current
            iteration.

        """
        next(self._it)
        return self._it.multi_index


# You can do all this with slice() plus a few special objects,
# but there's a lot to remember. This version is simpler because
# it uses the standard array indexing syntax.
#
# Written by Konrad Hinsen <hinsen@cnrs-orleans.fr>
# last revision: 1999-7-23
#
# Cosmetic changes by T. Oliphant 2001
#
#

class IndexExpression:
    """
    A nicer way to build up index tuples for arrays.

    .. note::
       Use one of the two predefined instances ``index_exp`` or `s_`
       rather than directly using `IndexExpression`.

    For any index combination, including slicing and axis insertion,
    ``a[indices]`` is the same as ``a[np.index_exp[indices]]`` for any
    array `a`. However, ``np.index_exp[indices]`` can be used anywhere
    in Python code and returns a tuple of slice objects that can be
    used in the construction of complex index expressions.

    Parameters
    ----------
    maketuple : bool
        If True, always returns a tuple.

    See Also
    --------
    s_ : Predefined instance without tuple conversion:
       `s_ = IndexExpression(maketuple=False)`.
       The ``index_exp`` is another predefined instance that
       always returns a tuple:
       `index_exp = IndexExpression(maketuple=True)`.

    Notes
    -----
    You can do all this with :class:`slice` plus a few special objects,
    but there's a lot to remember and this version is simpler because
    it uses the standard array indexing syntax.

    Examples
    --------
    >>> import numpy as np
    >>> np.s_[2::2]
    slice(2, None, 2)
    >>> np.index_exp[2::2]
    (slice(2, None, 2),)

    >>> np.array([0, 1, 2, 3, 4])[np.s_[2::2]]
    array([2, 4])

    """
    __slots__ = ('maketuple',)

    def __init__(self, maketuple):
        self.maketuple = maketuple

    def __getitem__(self, item):
        if self.maketuple and not isinstance(item, tuple):
            return (item,)
        else:
            return item


index_exp = IndexExpression(maketuple=True)
s_ = IndexExpression(maketuple=False)

# End contribution from Konrad.


# The following functions complement those in twodim_base, but are
# applicable to N-dimensions.


def _fill_diagonal_dispatcher(a, val, wrap=None):
    return (a,)


@array_function_dispatch(_fill_diagonal_dispatcher)
def fill_diagonal(a, val, wrap=False):
    """Fill the main diagonal of the given array of any dimensionality.

    For an array `a` with ``a.ndim >= 2``, the diagonal is the list of
    values ``a[i, ..., i]`` with indices ``i`` all identical.  This function
    modifies the input array in-place without returning a value.

    Parameters
    ----------
    a : array, at least 2-D.
      Array whose diagonal is to be filled in-place.
    val : scalar or array_like
      Value(s) to write on the diagonal. If `val` is scalar, the value is
      written along the diagonal. If array-like, the flattened `val` is
      written along the diagonal, repeating if necessary to fill all
      diagonal entries.

    wrap : bool
      For tall matrices in NumPy version up to 1.6.2, the
      diagonal "wrapped" after N columns. You can have this behavior
      with this option. This affects only tall matrices.

    See also
    --------
    diag_indices, diag_indices_from

    Notes
    -----
    This functionality can be obtained via `diag_indices`, but internally
    this version uses a much faster implementation that never constructs the
    indices and uses simple slicing.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.zeros((3, 3), int)
    >>> np.fill_diagonal(a, 5)
    >>> a
    array([[5, 0, 0],
           [0, 5, 0],
           [0, 0, 5]])

    The same function can operate on a 4-D array:

    >>> a = np.zeros((3, 3, 3, 3), int)
    >>> np.fill_diagonal(a, 4)

    We only show a few blocks for clarity:

    >>> a[0, 0]
    array([[4, 0, 0],
           [0, 0, 0],
           [0, 0, 0]])
    >>> a[1, 1]
    array([[0, 0, 0],
           [0, 4, 0],
           [0, 0, 0]])
    >>> a[2, 2]
    array([[0, 0, 0],
           [0, 0, 0],
           [0, 0, 4]])

    The wrap option affects only tall matrices:

    >>> # tall matrices no wrap
    >>> a = np.zeros((5, 3), int)
    >>> np.fill_diagonal(a, 4)
    >>> a
    array([[4, 0, 0],
           [0, 4, 0],
           [0, 0, 4],
           [0, 0, 0],
           [0, 0, 0]])

    >>> # tall matrices wrap
    >>> a = np.zeros((5, 3), int)
    >>> np.fill_diagonal(a, 4, wrap=True)
    >>> a
    array([[4, 0, 0],
           [0, 4, 0],
           [0, 0, 4],
           [0, 0, 0],
           [4, 0, 0]])

    >>> # wide matrices
    >>> a = np.zeros((3, 5), int)
    >>> np.fill_diagonal(a, 4, wrap=True)
    >>> a
    array([[4, 0, 0, 0, 0],
           [0, 4, 0, 0, 0],
           [0, 0, 4, 0, 0]])

    The anti-diagonal can be filled by reversing the order of elements
    using either `numpy.flipud` or `numpy.fliplr`.

    >>> a = np.zeros((3, 3), int);
    >>> np.fill_diagonal(np.fliplr(a), [1,2,3])  # Horizontal flip
    >>> a
    array([[0, 0, 1],
           [0, 2, 0],
           [3, 0, 0]])
    >>> np.fill_diagonal(np.flipud(a), [1,2,3])  # Vertical flip
    >>> a
    array([[0, 0, 3],
           [0, 2, 0],
           [1, 0, 0]])

    Note that the order in which the diagonal is filled varies depending
    on the flip function.
    """
    if a.ndim < 2:
        raise ValueError("array must be at least 2-d")
    end = None
    if a.ndim == 2:
        # Explicit, fast formula for the common case.  For 2-d arrays, we
        # accept rectangular ones.
        step = a.shape[1] + 1
        # This is needed to don't have tall matrix have the diagonal wrap.
        if not wrap:
            end = a.shape[1] * a.shape[1]
    else:
        # For more than d=2, the strided formula is only valid for arrays with
        # all dimensions equal, so we check first.
        if not np.all(diff(a.shape) == 0):
            raise ValueError("All dimensions of input must be of equal length")
        step = 1 + (np.cumprod(a.shape[:-1])).sum()

    # Write the value out into the diagonal.
    a.flat[:end:step] = val


@set_module('numpy')
def diag_indices(n, ndim=2):
    """
    Return the indices to access the main diagonal of an array.

    This returns a tuple of indices that can be used to access the main
    diagonal of an array `a` with ``a.ndim >= 2`` dimensions and shape
    (n, n, ..., n). For ``a.ndim = 2`` this is the usual diagonal, for
    ``a.ndim > 2`` this is the set of indices to access ``a[i, i, ..., i]``
    for ``i = [0..n-1]``.

    Parameters
    ----------
    n : int
      The size, along each dimension, of the arrays for which the returned
      indices can be used.

    ndim : int, optional
      The number of dimensions.

    See Also
    --------
    diag_indices_from

    Examples
    --------
    >>> import numpy as np

    Create a set of indices to access the diagonal of a (4, 4) array:

    >>> di = np.diag_indices(4)
    >>> di
    (array([0, 1, 2, 3]), array([0, 1, 2, 3]))
    >>> a = np.arange(16).reshape(4, 4)
    >>> a
    array([[ 0,  1,  2,  3],
           [ 4,  5,  6,  7],
           [ 8,  9, 10, 11],
           [12, 13, 14, 15]])
    >>> a[di] = 100
    >>> a
    array([[100,   1,   2,   3],
           [  4, 100,   6,   7],
           [  8,   9, 100,  11],
           [ 12,  13,  14, 100]])

    Now, we create indices to manipulate a 3-D array:

    >>> d3 = np.diag_indices(2, 3)
    >>> d3
    (array([0, 1]), array([0, 1]), array([0, 1]))

    And use it to set the diagonal of an array of zeros to 1:

    >>> a = np.zeros((2, 2, 2), dtype=int)
    >>> a[d3] = 1
    >>> a
    array([[[1, 0],
            [0, 0]],
           [[0, 0],
            [0, 1]]])

    """
    idx = np.arange(n)
    return (idx,) * ndim


def _diag_indices_from(arr):
    return (arr,)


@array_function_dispatch(_diag_indices_from)
def diag_indices_from(arr):
    """
    Return the indices to access the main diagonal of an n-dimensional array.

    See `diag_indices` for full details.

    Parameters
    ----------
    arr : array, at least 2-D

    See Also
    --------
    diag_indices

    Examples
    --------
    >>> import numpy as np

    Create a 4 by 4 array.

    >>> a = np.arange(16).reshape(4, 4)
    >>> a
    array([[ 0,  1,  2,  3],
           [ 4,  5,  6,  7],
           [ 8,  9, 10, 11],
           [12, 13, 14, 15]])

    Get the indices of the diagonal elements.

    >>> di = np.diag_indices_from(a)
    >>> di
    (array([0, 1, 2, 3]), array([0, 1, 2, 3]))

    >>> a[di]
    array([ 0,  5, 10, 15])

    This is simply syntactic sugar for diag_indices.

    >>> np.diag_indices(a.shape[0])
    (array([0, 1, 2, 3]), array([0, 1, 2, 3]))

    """

    if not arr.ndim >= 2:
        raise ValueError("input array must be at least 2-d")
    # For more than d=2, the strided formula is only valid for arrays with
    # all dimensions equal, so we check first.
    if not np.all(diff(arr.shape) == 0):
        raise ValueError("All dimensions of input must be of equal length")

    return diag_indices(arr.shape[0], arr.ndim)

# === NexusCore/openenv\Lib\site-packages\numpy\lib\tests\test_format.py ===
# doctest
r''' Test the .npy file format.

Set up:

    >>> import sys
    >>> from io import BytesIO
    >>> from numpy.lib import format
    >>>
    >>> scalars = [
    ...     np.uint8,
    ...     np.int8,
    ...     np.uint16,
    ...     np.int16,
    ...     np.uint32,
    ...     np.int32,
    ...     np.uint64,
    ...     np.int64,
    ...     np.float32,
    ...     np.float64,
    ...     np.complex64,
    ...     np.complex128,
    ...     object,
    ... ]
    >>>
    >>> basic_arrays = []
    >>>
    >>> for scalar in scalars:
    ...     for endian in '<>':
    ...         dtype = np.dtype(scalar).newbyteorder(endian)
    ...         basic = np.arange(15).astype(dtype)
    ...         basic_arrays.extend([
    ...             np.array([], dtype=dtype),
    ...             np.array(10, dtype=dtype),
    ...             basic,
    ...             basic.reshape((3,5)),
    ...             basic.reshape((3,5)).T,
    ...             basic.reshape((3,5))[::-1,::2],
    ...         ])
    ...
    >>>
    >>> Pdescr = [
    ...     ('x', 'i4', (2,)),
    ...     ('y', 'f8', (2, 2)),
    ...     ('z', 'u1')]
    >>>
    >>>
    >>> PbufferT = [
    ...     ([3,2], [[6.,4.],[6.,4.]], 8),
    ...     ([4,3], [[7.,5.],[7.,5.]], 9),
    ...     ]
    >>>
    >>>
    >>> Ndescr = [
    ...     ('x', 'i4', (2,)),
    ...     ('Info', [
    ...         ('value', 'c16'),
    ...         ('y2', 'f8'),
    ...         ('Info2', [
    ...             ('name', 'S2'),
    ...             ('value', 'c16', (2,)),
    ...             ('y3', 'f8', (2,)),
    ...             ('z3', 'u4', (2,))]),
    ...         ('name', 'S2'),
    ...         ('z2', 'b1')]),
    ...     ('color', 'S2'),
    ...     ('info', [
    ...         ('Name', 'U8'),
    ...         ('Value', 'c16')]),
    ...     ('y', 'f8', (2, 2)),
    ...     ('z', 'u1')]
    >>>
    >>>
    >>> NbufferT = [
    ...     ([3,2], (6j, 6., ('nn', [6j,4j], [6.,4.], [1,2]), 'NN', True), 'cc', ('NN', 6j), [[6.,4.],[6.,4.]], 8),
    ...     ([4,3], (7j, 7., ('oo', [7j,5j], [7.,5.], [2,1]), 'OO', False), 'dd', ('OO', 7j), [[7.,5.],[7.,5.]], 9),
    ...     ]
    >>>
    >>>
    >>> record_arrays = [
    ...     np.array(PbufferT, dtype=np.dtype(Pdescr).newbyteorder('<')),
    ...     np.array(NbufferT, dtype=np.dtype(Ndescr).newbyteorder('<')),
    ...     np.array(PbufferT, dtype=np.dtype(Pdescr).newbyteorder('>')),
    ...     np.array(NbufferT, dtype=np.dtype(Ndescr).newbyteorder('>')),
    ... ]

Test the magic string writing.

    >>> format.magic(1, 0)
    '\x93NUMPY\x01\x00'
    >>> format.magic(0, 0)
    '\x93NUMPY\x00\x00'
    >>> format.magic(255, 255)
    '\x93NUMPY\xff\xff'
    >>> format.magic(2, 5)
    '\x93NUMPY\x02\x05'

Test the magic string reading.

    >>> format.read_magic(BytesIO(format.magic(1, 0)))
    (1, 0)
    >>> format.read_magic(BytesIO(format.magic(0, 0)))
    (0, 0)
    >>> format.read_magic(BytesIO(format.magic(255, 255)))
    (255, 255)
    >>> format.read_magic(BytesIO(format.magic(2, 5)))
    (2, 5)

Test the header writing.

    >>> for arr in basic_arrays + record_arrays:
    ...     f = BytesIO()
    ...     format.write_array_header_1_0(f, arr)   # XXX: arr is not a dict, items gets called on it
    ...     print(repr(f.getvalue()))
    ...
    "F\x00{'descr': '|u1', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '|u1', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '|u1', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '|u1', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '|u1', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '|u1', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '|u1', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '|u1', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '|u1', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '|u1', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '|u1', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '|u1', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '|i1', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '|i1', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '|i1', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '|i1', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '|i1', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '|i1', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '|i1', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '|i1', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '|i1', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '|i1', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '|i1', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '|i1', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '<u2', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '<u2', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '<u2', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '<u2', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '<u2', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '<u2', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '>u2', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '>u2', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '>u2', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '>u2', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '>u2', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '>u2', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '<i2', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '<i2', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '<i2', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '<i2', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '<i2', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '<i2', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '>i2', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '>i2', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '>i2', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '>i2', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '>i2', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '>i2', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '<u4', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '<u4', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '<u4', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '<u4', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '<u4', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '<u4', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '>u4', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '>u4', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '>u4', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '>u4', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '>u4', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '>u4', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '<i4', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '<i4', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '<i4', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '<i4', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '<i4', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '<i4', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '>i4', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '>i4', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '>i4', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '>i4', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '>i4', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '>i4', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '<u8', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '<u8', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '<u8', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '<u8', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '<u8', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '<u8', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '>u8', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '>u8', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '>u8', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '>u8', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '>u8', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '>u8', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '<i8', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '<i8', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '<i8', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '<i8', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '<i8', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '<i8', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '>i8', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '>i8', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '>i8', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '>i8', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '>i8', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '>i8', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '<f4', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '<f4', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '<f4', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '<f4', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '<f4', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '<f4', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '>f4', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '>f4', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '>f4', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '>f4', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '>f4', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '>f4', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '<f8', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '<f8', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '<f8', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '<f8', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '<f8', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '<f8', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '>f8', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '>f8', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '>f8', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '>f8', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '>f8', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '>f8', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '<c8', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '<c8', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '<c8', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '<c8', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '<c8', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '<c8', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '>c8', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': '>c8', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': '>c8', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': '>c8', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': '>c8', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': '>c8', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': '<c16', 'fortran_order': False, 'shape': (0,)}             \n"
    "F\x00{'descr': '<c16', 'fortran_order': False, 'shape': ()}               \n"
    "F\x00{'descr': '<c16', 'fortran_order': False, 'shape': (15,)}            \n"
    "F\x00{'descr': '<c16', 'fortran_order': False, 'shape': (3, 5)}           \n"
    "F\x00{'descr': '<c16', 'fortran_order': True, 'shape': (5, 3)}            \n"
    "F\x00{'descr': '<c16', 'fortran_order': False, 'shape': (3, 3)}           \n"
    "F\x00{'descr': '>c16', 'fortran_order': False, 'shape': (0,)}             \n"
    "F\x00{'descr': '>c16', 'fortran_order': False, 'shape': ()}               \n"
    "F\x00{'descr': '>c16', 'fortran_order': False, 'shape': (15,)}            \n"
    "F\x00{'descr': '>c16', 'fortran_order': False, 'shape': (3, 5)}           \n"
    "F\x00{'descr': '>c16', 'fortran_order': True, 'shape': (5, 3)}            \n"
    "F\x00{'descr': '>c16', 'fortran_order': False, 'shape': (3, 3)}           \n"
    "F\x00{'descr': 'O', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': 'O', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': 'O', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': 'O', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': 'O', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': 'O', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "F\x00{'descr': 'O', 'fortran_order': False, 'shape': (0,)}              \n"
    "F\x00{'descr': 'O', 'fortran_order': False, 'shape': ()}                \n"
    "F\x00{'descr': 'O', 'fortran_order': False, 'shape': (15,)}             \n"
    "F\x00{'descr': 'O', 'fortran_order': False, 'shape': (3, 5)}            \n"
    "F\x00{'descr': 'O', 'fortran_order': True, 'shape': (5, 3)}             \n"
    "F\x00{'descr': 'O', 'fortran_order': False, 'shape': (3, 3)}            \n"
    "v\x00{'descr': [('x', '<i4', (2,)), ('y', '<f8', (2, 2)), ('z', '|u1')],\n 'fortran_order': False,\n 'shape': (2,)}         \n"
    "\x16\x02{'descr': [('x', '<i4', (2,)),\n           ('Info',\n            [('value', '<c16'),\n             ('y2', '<f8'),\n             ('Info2',\n              [('name', '|S2'),\n               ('value', '<c16', (2,)),\n               ('y3', '<f8', (2,)),\n               ('z3', '<u4', (2,))]),\n             ('name', '|S2'),\n             ('z2', '|b1')]),\n           ('color', '|S2'),\n           ('info', [('Name', '<U8'), ('Value', '<c16')]),\n           ('y', '<f8', (2, 2)),\n           ('z', '|u1')],\n 'fortran_order': False,\n 'shape': (2,)}      \n"
    "v\x00{'descr': [('x', '>i4', (2,)), ('y', '>f8', (2, 2)), ('z', '|u1')],\n 'fortran_order': False,\n 'shape': (2,)}         \n"
    "\x16\x02{'descr': [('x', '>i4', (2,)),\n           ('Info',\n            [('value', '>c16'),\n             ('y2', '>f8'),\n             ('Info2',\n              [('name', '|S2'),\n               ('value', '>c16', (2,)),\n               ('y3', '>f8', (2,)),\n               ('z3', '>u4', (2,))]),\n             ('name', '|S2'),\n             ('z2', '|b1')]),\n           ('color', '|S2'),\n           ('info', [('Name', '>U8'), ('Value', '>c16')]),\n           ('y', '>f8', (2, 2)),\n           ('z', '|u1')],\n 'fortran_order': False,\n 'shape': (2,)}      \n"
'''
import os
import sys
import warnings
from io import BytesIO

import pytest

import numpy as np
from numpy.lib import format
from numpy.testing import (
    IS_64BIT,
    IS_PYPY,
    IS_WASM,
    assert_,
    assert_array_equal,
    assert_raises,
    assert_raises_regex,
    assert_warns,
)
from numpy.testing._private.utils import requires_memory

# Generate some basic arrays to test with.
scalars = [
    np.uint8,
    np.int8,
    np.uint16,
    np.int16,
    np.uint32,
    np.int32,
    np.uint64,
    np.int64,
    np.float32,
    np.float64,
    np.complex64,
    np.complex128,
    object,
]
basic_arrays = []
for scalar in scalars:
    for endian in '<>':
        dtype = np.dtype(scalar).newbyteorder(endian)
        basic = np.arange(1500).astype(dtype)
        basic_arrays.extend([
            # Empty
            np.array([], dtype=dtype),
            # Rank-0
            np.array(10, dtype=dtype),
            # 1-D
            basic,
            # 2-D C-contiguous
            basic.reshape((30, 50)),
            # 2-D F-contiguous
            basic.reshape((30, 50)).T,
            # 2-D non-contiguous
            basic.reshape((30, 50))[::-1, ::2],
        ])

# More complicated record arrays.
# This is the structure of the table used for plain objects:
#
# +-+-+-+
# |x|y|z|
# +-+-+-+

# Structure of a plain array description:
Pdescr = [
    ('x', 'i4', (2,)),
    ('y', 'f8', (2, 2)),
    ('z', 'u1')]

# A plain list of tuples with values for testing:
PbufferT = [
    # x     y                  z
    ([3, 2], [[6., 4.], [6., 4.]], 8),
    ([4, 3], [[7., 5.], [7., 5.]], 9),
    ]


# This is the structure of the table used for nested objects (DON'T PANIC!):
#
# +-+---------------------------------+-----+----------+-+-+
# |x|Info                             |color|info      |y|z|
# | +-----+--+----------------+----+--+     +----+-----+ | |
# | |value|y2|Info2           |name|z2|     |Name|Value| | |
# | |     |  +----+-----+--+--+    |  |     |    |     | | |
# | |     |  |name|value|y3|z3|    |  |     |    |     | | |
# +-+-----+--+----+-----+--+--+----+--+-----+----+-----+-+-+
#

# The corresponding nested array description:
Ndescr = [
    ('x', 'i4', (2,)),
    ('Info', [
        ('value', 'c16'),
        ('y2', 'f8'),
        ('Info2', [
            ('name', 'S2'),
            ('value', 'c16', (2,)),
            ('y3', 'f8', (2,)),
            ('z3', 'u4', (2,))]),
        ('name', 'S2'),
        ('z2', 'b1')]),
    ('color', 'S2'),
    ('info', [
        ('Name', 'U8'),
        ('Value', 'c16')]),
    ('y', 'f8', (2, 2)),
    ('z', 'u1')]

NbufferT = [
    # x     Info                                                color info        y                  z
    #       value y2 Info2                            name z2         Name Value
    #                name   value    y3       z3
    ([3, 2], (6j, 6., ('nn', [6j, 4j], [6., 4.], [1, 2]), 'NN', True),
     'cc', ('NN', 6j), [[6., 4.], [6., 4.]], 8),
    ([4, 3], (7j, 7., ('oo', [7j, 5j], [7., 5.], [2, 1]), 'OO', False),
     'dd', ('OO', 7j), [[7., 5.], [7., 5.]], 9),
    ]

record_arrays = [
    np.array(PbufferT, dtype=np.dtype(Pdescr).newbyteorder('<')),
    np.array(NbufferT, dtype=np.dtype(Ndescr).newbyteorder('<')),
    np.array(PbufferT, dtype=np.dtype(Pdescr).newbyteorder('>')),
    np.array(NbufferT, dtype=np.dtype(Ndescr).newbyteorder('>')),
    np.zeros(1, dtype=[('c', ('<f8', (5,)), (2,))])
]


# BytesIO that reads a random number of bytes at a time
class BytesIOSRandomSize(BytesIO):
    def read(self, size=None):
        import random
        size = random.randint(1, size)
        return super().read(size)


def roundtrip(arr):
    f = BytesIO()
    format.write_array(f, arr)
    f2 = BytesIO(f.getvalue())
    arr2 = format.read_array(f2, allow_pickle=True)
    return arr2


def roundtrip_randsize(arr):
    f = BytesIO()
    format.write_array(f, arr)
    f2 = BytesIOSRandomSize(f.getvalue())
    arr2 = format.read_array(f2)
    return arr2


def roundtrip_truncated(arr):
    f = BytesIO()
    format.write_array(f, arr)
    # BytesIO is one byte short
    f2 = BytesIO(f.getvalue()[0:-1])
    arr2 = format.read_array(f2)
    return arr2

def assert_equal_(o1, o2):
    assert_(o1 == o2)


def test_roundtrip():
    for arr in basic_arrays + record_arrays:
        arr2 = roundtrip(arr)
        assert_array_equal(arr, arr2)


def test_roundtrip_randsize():
    for arr in basic_arrays + record_arrays:
        if arr.dtype != object:
            arr2 = roundtrip_randsize(arr)
            assert_array_equal(arr, arr2)


def test_roundtrip_truncated():
    for arr in basic_arrays:
        if arr.dtype != object:
            assert_raises(ValueError, roundtrip_truncated, arr)

def test_file_truncated(tmp_path):
    path = tmp_path / "a.npy"
    for arr in basic_arrays:
        if arr.dtype != object:
            with open(path, 'wb') as f:
                format.write_array(f, arr)
            # truncate the file by one byte
            with open(path, 'rb+') as f:
                f.seek(-1, os.SEEK_END)
                f.truncate()
            with open(path, 'rb') as f:
                with pytest.raises(
                    ValueError,
                    match=(
                        r"EOF: reading array header, "
                        r"expected (\d+) bytes got (\d+)"
                    ) if arr.size == 0 else (
                        r"Failed to read all data for array\. "
                        r"Expected \(.*?\) = (\d+) elements, "
                        r"could only read (\d+) elements\. "
                        r"\(file seems not fully written\?\)"
                    )
                ):
                    _ = format.read_array(f)

def test_long_str():
    # check items larger than internal buffer size, gh-4027
    long_str_arr = np.ones(1, dtype=np.dtype((str, format.BUFFER_SIZE + 1)))
    long_str_arr2 = roundtrip(long_str_arr)
    assert_array_equal(long_str_arr, long_str_arr2)


@pytest.mark.skipif(IS_WASM, reason="memmap doesn't work correctly")
@pytest.mark.slow
def test_memmap_roundtrip(tmpdir):
    for i, arr in enumerate(basic_arrays + record_arrays):
        if arr.dtype.hasobject:
            # Skip these since they can't be mmap'ed.
            continue
        # Write it out normally and through mmap.
        nfn = os.path.join(tmpdir, f'normal{i}.npy')
        mfn = os.path.join(tmpdir, f'memmap{i}.npy')
        with open(nfn, 'wb') as fp:
            format.write_array(fp, arr)

        fortran_order = (
            arr.flags.f_contiguous and not arr.flags.c_contiguous)
        ma = format.open_memmap(mfn, mode='w+', dtype=arr.dtype,
                                shape=arr.shape, fortran_order=fortran_order)
        ma[...] = arr
        ma.flush()

        # Check that both of these files' contents are the same.
        with open(nfn, 'rb') as fp:
            normal_bytes = fp.read()
        with open(mfn, 'rb') as fp:
            memmap_bytes = fp.read()
        assert_equal_(normal_bytes, memmap_bytes)

        # Check that reading the file using memmap works.
        ma = format.open_memmap(nfn, mode='r')
        ma.flush()


def test_compressed_roundtrip(tmpdir):
    arr = np.random.rand(200, 200)
    npz_file = os.path.join(tmpdir, 'compressed.npz')
    np.savez_compressed(npz_file, arr=arr)
    with np.load(npz_file) as npz:
        arr1 = npz['arr']
    assert_array_equal(arr, arr1)


# aligned
dt1 = np.dtype('i1, i4, i1', align=True)
# non-aligned, explicit offsets
dt2 = np.dtype({'names': ['a', 'b'], 'formats': ['i4', 'i4'],
                'offsets': [1, 6]})
# nested struct-in-struct
dt3 = np.dtype({'names': ['c', 'd'], 'formats': ['i4', dt2]})
# field with '' name
dt4 = np.dtype({'names': ['a', '', 'b'], 'formats': ['i4'] * 3})
# titles
dt5 = np.dtype({'names': ['a', 'b'], 'formats': ['i4', 'i4'],
                'offsets': [1, 6], 'titles': ['aa', 'bb']})
# empty
dt6 = np.dtype({'names': [], 'formats': [], 'itemsize': 8})

@pytest.mark.parametrize("dt", [dt1, dt2, dt3, dt4, dt5, dt6])
def test_load_padded_dtype(tmpdir, dt):
    arr = np.zeros(3, dt)
    for i in range(3):
        arr[i] = i + 5
    npz_file = os.path.join(tmpdir, 'aligned.npz')
    np.savez(npz_file, arr=arr)
    with np.load(npz_file) as npz:
        arr1 = npz['arr']
    assert_array_equal(arr, arr1)


@pytest.mark.skipif(sys.version_info >= (3, 12), reason="see gh-23988")
@pytest.mark.xfail(IS_WASM, reason="Emscripten NODEFS has a buggy dup")
def test_python2_python3_interoperability():
    fname = 'win64python2.npy'
    path = os.path.join(os.path.dirname(__file__), 'data', fname)
    with pytest.warns(UserWarning, match="Reading.*this warning\\."):
        data = np.load(path)
    assert_array_equal(data, np.ones(2))


def test_pickle_python2_python3():
    # Test that loading object arrays saved on Python 2 works both on
    # Python 2 and Python 3 and vice versa
    data_dir = os.path.join(os.path.dirname(__file__), 'data')

    expected = np.array([None, range, '\u512a\u826f',
                         b'\xe4\xb8\x8d\xe8\x89\xaf'],
                        dtype=object)

    for fname in ['py2-np0-objarr.npy', 'py2-objarr.npy', 'py2-objarr.npz',
                  'py3-objarr.npy', 'py3-objarr.npz']:
        path = os.path.join(data_dir, fname)

        for encoding in ['bytes', 'latin1']:
            data_f = np.load(path, allow_pickle=True, encoding=encoding)
            if fname.endswith('.npz'):
                data = data_f['x']
                data_f.close()
            else:
                data = data_f

            if encoding == 'latin1' and fname.startswith('py2'):
                assert_(isinstance(data[3], str))
                assert_array_equal(data[:-1], expected[:-1])
                # mojibake occurs
                assert_array_equal(data[-1].encode(encoding), expected[-1])
            else:
                assert_(isinstance(data[3], bytes))
                assert_array_equal(data, expected)

        if fname.startswith('py2'):
            if fname.endswith('.npz'):
                data = np.load(path, allow_pickle=True)
                assert_raises(UnicodeError, data.__getitem__, 'x')
                data.close()
                data = np.load(path, allow_pickle=True, fix_imports=False,
                               encoding='latin1')
                assert_raises(ImportError, data.__getitem__, 'x')
                data.close()
            else:
                assert_raises(UnicodeError, np.load, path,
                              allow_pickle=True)
                assert_raises(ImportError, np.load, path,
                              allow_pickle=True, fix_imports=False,
                              encoding='latin1')


def test_pickle_disallow(tmpdir):
    data_dir = os.path.join(os.path.dirname(__file__), 'data')

    path = os.path.join(data_dir, 'py2-objarr.npy')
    assert_raises(ValueError, np.load, path,
                  allow_pickle=False, encoding='latin1')

    path = os.path.join(data_dir, 'py2-objarr.npz')
    with np.load(path, allow_pickle=False, encoding='latin1') as f:
        assert_raises(ValueError, f.__getitem__, 'x')

    path = os.path.join(tmpdir, 'pickle-disabled.npy')
    assert_raises(ValueError, np.save, path, np.array([None], dtype=object),
                  allow_pickle=False)

@pytest.mark.parametrize('dt', [
    np.dtype(np.dtype([('a', np.int8),
                       ('b', np.int16),
                       ('c', np.int32),
                      ], align=True),
             (3,)),
    np.dtype([('x', np.dtype({'names': ['a', 'b'],
                              'formats': ['i1', 'i1'],
                              'offsets': [0, 4],
                              'itemsize': 8,
                             },
                    (3,)),
               (4,),
             )]),
    np.dtype([('x',
                   ('<f8', (5,)),
                   (2,),
               )]),
    np.dtype([('x', np.dtype((
        np.dtype((
            np.dtype({'names': ['a', 'b'],
                      'formats': ['i1', 'i1'],
                      'offsets': [0, 4],
                      'itemsize': 8}),
            (3,)
            )),
        (4,)
        )))
        ]),
    np.dtype([
        ('a', np.dtype((
            np.dtype((
                np.dtype((
                    np.dtype([
                        ('a', int),
                        ('b', np.dtype({'names': ['a', 'b'],
                                        'formats': ['i1', 'i1'],
                                        'offsets': [0, 4],
                                        'itemsize': 8})),
                    ]),
                    (3,),
                )),
                (4,),
            )),
            (5,),
        )))
        ]),
    ])
def test_descr_to_dtype(dt):
    dt1 = format.descr_to_dtype(dt.descr)
    assert_equal_(dt1, dt)
    arr1 = np.zeros(3, dt)
    arr2 = roundtrip(arr1)
    assert_array_equal(arr1, arr2)

def test_version_2_0():
    f = BytesIO()
    # requires more than 2 byte for header
    dt = [(("%d" % i) * 100, float) for i in range(500)]
    d = np.ones(1000, dtype=dt)

    format.write_array(f, d, version=(2, 0))
    with warnings.catch_warnings(record=True) as w:
        warnings.filterwarnings('always', '', UserWarning)
        format.write_array(f, d)
        assert_(w[0].category is UserWarning)

    # check alignment of data portion
    f.seek(0)
    header = f.readline()
    assert_(len(header) % format.ARRAY_ALIGN == 0)

    f.seek(0)
    n = format.read_array(f, max_header_size=200000)
    assert_array_equal(d, n)

    # 1.0 requested but data cannot be saved this way
    assert_raises(ValueError, format.write_array, f, d, (1, 0))


@pytest.mark.skipif(IS_WASM, reason="memmap doesn't work correctly")
def test_version_2_0_memmap(tmpdir):
    # requires more than 2 byte for header
    dt = [(("%d" % i) * 100, float) for i in range(500)]
    d = np.ones(1000, dtype=dt)
    tf1 = os.path.join(tmpdir, 'version2_01.npy')
    tf2 = os.path.join(tmpdir, 'version2_02.npy')

    # 1.0 requested but data cannot be saved this way
    assert_raises(ValueError, format.open_memmap, tf1, mode='w+', dtype=d.dtype,
                            shape=d.shape, version=(1, 0))

    ma = format.open_memmap(tf1, mode='w+', dtype=d.dtype,
                            shape=d.shape, version=(2, 0))
    ma[...] = d
    ma.flush()
    ma = format.open_memmap(tf1, mode='r', max_header_size=200000)
    assert_array_equal(ma, d)

    with warnings.catch_warnings(record=True) as w:
        warnings.filterwarnings('always', '', UserWarning)
        ma = format.open_memmap(tf2, mode='w+', dtype=d.dtype,
                                shape=d.shape, version=None)
        assert_(w[0].category is UserWarning)
        ma[...] = d
        ma.flush()

    ma = format.open_memmap(tf2, mode='r', max_header_size=200000)

    assert_array_equal(ma, d)

@pytest.mark.parametrize("mmap_mode", ["r", None])
def test_huge_header(tmpdir, mmap_mode):
    f = os.path.join(tmpdir, 'large_header.npy')
    arr = np.array(1, dtype="i," * 10000 + "i")

    with pytest.warns(UserWarning, match=".*format 2.0"):
        np.save(f, arr)

    with pytest.raises(ValueError, match="Header.*large"):
        np.load(f, mmap_mode=mmap_mode)

    with pytest.raises(ValueError, match="Header.*large"):
        np.load(f, mmap_mode=mmap_mode, max_header_size=20000)

    res = np.load(f, mmap_mode=mmap_mode, allow_pickle=True)
    assert_array_equal(res, arr)

    res = np.load(f, mmap_mode=mmap_mode, max_header_size=180000)
    assert_array_equal(res, arr)

def test_huge_header_npz(tmpdir):
    f = os.path.join(tmpdir, 'large_header.npz')
    arr = np.array(1, dtype="i," * 10000 + "i")

    with pytest.warns(UserWarning, match=".*format 2.0"):
        np.savez(f, arr=arr)

    # Only getting the array from the file actually reads it
    with pytest.raises(ValueError, match="Header.*large"):
        np.load(f)["arr"]

    with pytest.raises(ValueError, match="Header.*large"):
        np.load(f, max_header_size=20000)["arr"]

    res = np.load(f, allow_pickle=True)["arr"]
    assert_array_equal(res, arr)

    res = np.load(f, max_header_size=180000)["arr"]
    assert_array_equal(res, arr)

def test_write_version():
    f = BytesIO()
    arr = np.arange(1)
    # These should pass.
    format.write_array(f, arr, version=(1, 0))
    format.write_array(f, arr)

    format.write_array(f, arr, version=None)
    format.write_array(f, arr)

    format.write_array(f, arr, version=(2, 0))
    format.write_array(f, arr)

    # These should all fail.
    bad_versions = [
        (1, 1),
        (0, 0),
        (0, 1),
        (2, 2),
        (255, 255),
    ]
    for version in bad_versions:
        with assert_raises_regex(ValueError,
                                 'we only support format version.*'):
            format.write_array(f, arr, version=version)


bad_version_magic = [
    b'\x93NUMPY\x01\x01',
    b'\x93NUMPY\x00\x00',
    b'\x93NUMPY\x00\x01',
    b'\x93NUMPY\x02\x00',
    b'\x93NUMPY\x02\x02',
    b'\x93NUMPY\xff\xff',
]
malformed_magic = [
    b'\x92NUMPY\x01\x00',
    b'\x00NUMPY\x01\x00',
    b'\x93numpy\x01\x00',
    b'\x93MATLB\x01\x00',
    b'\x93NUMPY\x01',
    b'\x93NUMPY',
    b'',
]

def test_read_magic():
    s1 = BytesIO()
    s2 = BytesIO()

    arr = np.ones((3, 6), dtype=float)

    format.write_array(s1, arr, version=(1, 0))
    format.write_array(s2, arr, version=(2, 0))

    s1.seek(0)
    s2.seek(0)

    version1 = format.read_magic(s1)
    version2 = format.read_magic(s2)

    assert_(version1 == (1, 0))
    assert_(version2 == (2, 0))

    assert_(s1.tell() == format.MAGIC_LEN)
    assert_(s2.tell() == format.MAGIC_LEN)

def test_read_magic_bad_magic():
    for magic in malformed_magic:
        f = BytesIO(magic)
        assert_raises(ValueError, format.read_array, f)


def test_read_version_1_0_bad_magic():
    for magic in bad_version_magic + malformed_magic:
        f = BytesIO(magic)
        assert_raises(ValueError, format.read_array, f)


def test_bad_magic_args():
    assert_raises(ValueError, format.magic, -1, 1)
    assert_raises(ValueError, format.magic, 256, 1)
    assert_raises(ValueError, format.magic, 1, -1)
    assert_raises(ValueError, format.magic, 1, 256)


def test_large_header():
    s = BytesIO()
    d = {'shape': (), 'fortran_order': False, 'descr': '<i8'}
    format.write_array_header_1_0(s, d)

    s = BytesIO()
    d['descr'] = [('x' * 256 * 256, '<i8')]
    assert_raises(ValueError, format.write_array_header_1_0, s, d)


def test_read_array_header_1_0():
    s = BytesIO()

    arr = np.ones((3, 6), dtype=float)
    format.write_array(s, arr, version=(1, 0))

    s.seek(format.MAGIC_LEN)
    shape, fortran, dtype = format.read_array_header_1_0(s)

    assert_(s.tell() % format.ARRAY_ALIGN == 0)
    assert_((shape, fortran, dtype) == ((3, 6), False, float))


def test_read_array_header_2_0():
    s = BytesIO()

    arr = np.ones((3, 6), dtype=float)
    format.write_array(s, arr, version=(2, 0))

    s.seek(format.MAGIC_LEN)
    shape, fortran, dtype = format.read_array_header_2_0(s)

    assert_(s.tell() % format.ARRAY_ALIGN == 0)
    assert_((shape, fortran, dtype) == ((3, 6), False, float))


def test_bad_header():
    # header of length less than 2 should fail
    s = BytesIO()
    assert_raises(ValueError, format.read_array_header_1_0, s)
    s = BytesIO(b'1')
    assert_raises(ValueError, format.read_array_header_1_0, s)

    # header shorter than indicated size should fail
    s = BytesIO(b'\x01\x00')
    assert_raises(ValueError, format.read_array_header_1_0, s)

    # headers without the exact keys required should fail
    # d = {"shape": (1, 2),
    #      "descr": "x"}
    s = BytesIO(
        b"\x93NUMPY\x01\x006\x00{'descr': 'x', 'shape': (1, 2), }"
        b"                    \n"
    )
    assert_raises(ValueError, format.read_array_header_1_0, s)

    d = {"shape": (1, 2),
         "fortran_order": False,
         "descr": "x",
         "extrakey": -1}
    s = BytesIO()
    format.write_array_header_1_0(s, d)
    assert_raises(ValueError, format.read_array_header_1_0, s)


def test_large_file_support(tmpdir):
    if (sys.platform == 'win32' or sys.platform == 'cygwin'):
        pytest.skip("Unknown if Windows has sparse filesystems")
    # try creating a large sparse file
    tf_name = os.path.join(tmpdir, 'sparse_file')
    try:
        # seek past end would work too, but linux truncate somewhat
        # increases the chances that we have a sparse filesystem and can
        # avoid actually writing 5GB
        import subprocess as sp
        sp.check_call(["truncate", "-s", "5368709120", tf_name])
    except Exception:
        pytest.skip("Could not create 5GB large file")
    # write a small array to the end
    with open(tf_name, "wb") as f:
        f.seek(5368709120)
        d = np.arange(5)
        np.save(f, d)
    # read it back
    with open(tf_name, "rb") as f:
        f.seek(5368709120)
        r = np.load(f)
    assert_array_equal(r, d)


@pytest.mark.skipif(IS_PYPY, reason="flaky on PyPy")
@pytest.mark.skipif(not IS_64BIT, reason="test requires 64-bit system")
@pytest.mark.slow
@requires_memory(free_bytes=2 * 2**30)
def test_large_archive(tmpdir):
    # Regression test for product of saving arrays with dimensions of array
    # having a product that doesn't fit in int32.  See gh-7598 for details.
    shape = (2**30, 2)
    try:
        a = np.empty(shape, dtype=np.uint8)
    except MemoryError:
        pytest.skip("Could not create large file")

    fname = os.path.join(tmpdir, "large_archive")

    with open(fname, "wb") as f:
        np.savez(f, arr=a)

    del a

    with open(fname, "rb") as f:
        new_a = np.load(f)["arr"]

    assert new_a.shape == shape


def test_empty_npz(tmpdir):
    # Test for gh-9989
    fname = os.path.join(tmpdir, "nothing.npz")
    np.savez(fname)
    with np.load(fname) as nps:
        pass


def test_unicode_field_names(tmpdir):
    # gh-7391
    arr = np.array([
        (1, 3),
        (1, 2),
        (1, 3),
        (1, 2)
    ], dtype=[
        ('int', int),
        ('\N{CJK UNIFIED IDEOGRAPH-6574}\N{CJK UNIFIED IDEOGRAPH-5F62}', int)
    ])
    fname = os.path.join(tmpdir, "unicode.npy")
    with open(fname, 'wb') as f:
        format.write_array(f, arr, version=(3, 0))
    with open(fname, 'rb') as f:
        arr2 = format.read_array(f)
    assert_array_equal(arr, arr2)

    # notifies the user that 3.0 is selected
    with open(fname, 'wb') as f:
        with assert_warns(UserWarning):
            format.write_array(f, arr, version=None)

def test_header_growth_axis():
    for is_fortran_array, dtype_space, expected_header_length in [
        [False, 22, 128], [False, 23, 192], [True, 23, 128], [True, 24, 192]
    ]:
        for size in [10**i for i in range(format.GROWTH_AXIS_MAX_DIGITS)]:
            fp = BytesIO()
            format.write_array_header_1_0(fp, {
                'shape': (2, size) if is_fortran_array else (size, 2),
                'fortran_order': is_fortran_array,
                'descr': np.dtype([(' ' * dtype_space, int)])
            })

            assert len(fp.getvalue()) == expected_header_length

@pytest.mark.parametrize('dt', [
    np.dtype({'names': ['a', 'b'], 'formats':  [float, np.dtype('S3',
                 metadata={'some': 'stuff'})]}),
    np.dtype(int, metadata={'some': 'stuff'}),
    np.dtype([('subarray', (int, (2,)))], metadata={'some': 'stuff'}),
    # recursive: metadata on the field of a dtype
    np.dtype({'names': ['a', 'b'], 'formats': [
        float, np.dtype({'names': ['c'], 'formats': [np.dtype(int, metadata={})]})
    ]}),
    ])
@pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
        reason="PyPy bug in error formatting")
def test_metadata_dtype(dt):
    # gh-14142
    arr = np.ones(10, dtype=dt)
    buf = BytesIO()
    with assert_warns(UserWarning):
        np.save(buf, arr)
    buf.seek(0)

    # Loading should work (metadata was stripped):
    arr2 = np.load(buf)
    # BUG: assert_array_equal does not check metadata
    from numpy.lib._utils_impl import drop_metadata
    assert_array_equal(arr, arr2)
    assert drop_metadata(arr.dtype) is not arr.dtype
    assert drop_metadata(arr2.dtype) is arr2.dtype