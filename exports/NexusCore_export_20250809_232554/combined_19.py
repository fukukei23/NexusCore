
# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\tests\test_loadtxt.py ===
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

# === NexusCore/src\nexuscore\npe\budget.py ===
# npe/budget.py
import time
from collections import defaultdict

class BudgetManager:
    """
    プロジェクトやユーザーごとのAI利用予算を管理する。
    本番ではRedisやDBで永続化することを想定。
    """
    def __init__(self):
        self.budgets = defaultdict(lambda: 10.0)  # デフォルト予算を$10とする
        self.costs = defaultdict(float)

    def check_budget(self, project_id: str, estimated_cost: float) -> bool:
        """予算が十分か確認する"""
        remaining = self.budgets[project_id] - self.costs[project_id]
        print(f"[BudgetManager] Project '{project_id}': Remaining Budget ${remaining:.4f}. Estimated Cost ${estimated_cost:.4f}.")
        if remaining >= estimated_cost:
            return True
        print(f"[BudgetManager] WARN: Budget exceeded for project '{project_id}'.")
        return False

    def record_cost(self, project_id: str, actual_cost: float):
        """実績コストを記録する"""
        self.costs[project_id] += actual_cost
        print(f"[BudgetManager] Recorded cost ${actual_cost:.4f} for project '{project_id}'.")

    def get_remaining_budget(self, project_id: str) -> float:
        """残予算を返す"""
        return self.budgets[project_id] - self.costs[project_id]

# シングルトンインスタンスとして利用
budget_manager = BudgetManager()

# === NexusCore/openenv\Lib\site-packages\win32\lib\win32inetcon.py ===
# Generated by h2py from \mssdk\include\WinInet.h

INTERNET_INVALID_PORT_NUMBER = 0
INTERNET_DEFAULT_PORT = 0
INTERNET_DEFAULT_FTP_PORT = 21
INTERNET_DEFAULT_GOPHER_PORT = 70
INTERNET_DEFAULT_HTTP_PORT = 80
INTERNET_DEFAULT_HTTPS_PORT = 443
INTERNET_DEFAULT_SOCKS_PORT = 1080
INTERNET_MAX_HOST_NAME_LENGTH = 256
INTERNET_MAX_USER_NAME_LENGTH = 128
INTERNET_MAX_PASSWORD_LENGTH = 128
INTERNET_MAX_PORT_NUMBER_LENGTH = 5
INTERNET_MAX_PORT_NUMBER_VALUE = 65535
INTERNET_MAX_PATH_LENGTH = 2048
INTERNET_MAX_SCHEME_LENGTH = 32
INTERNET_KEEP_ALIVE_ENABLED = 1
INTERNET_KEEP_ALIVE_DISABLED = 0
INTERNET_REQFLAG_FROM_CACHE = 0x00000001
INTERNET_REQFLAG_ASYNC = 0x00000002
INTERNET_REQFLAG_VIA_PROXY = 0x00000004
INTERNET_REQFLAG_NO_HEADERS = 0x00000008
INTERNET_REQFLAG_PASSIVE = 0x00000010
INTERNET_REQFLAG_CACHE_WRITE_DISABLED = 0x00000040
INTERNET_REQFLAG_NET_TIMEOUT = 0x00000080
INTERNET_FLAG_RELOAD = -2147483648
INTERNET_FLAG_RAW_DATA = 0x40000000
INTERNET_FLAG_EXISTING_CONNECT = 0x20000000
INTERNET_FLAG_ASYNC = 0x10000000
INTERNET_FLAG_PASSIVE = 0x08000000
INTERNET_FLAG_NO_CACHE_WRITE = 0x04000000
INTERNET_FLAG_DONT_CACHE = INTERNET_FLAG_NO_CACHE_WRITE
INTERNET_FLAG_MAKE_PERSISTENT = 0x02000000
INTERNET_FLAG_FROM_CACHE = 0x01000000
INTERNET_FLAG_OFFLINE = INTERNET_FLAG_FROM_CACHE
INTERNET_FLAG_SECURE = 0x00800000
INTERNET_FLAG_KEEP_CONNECTION = 0x00400000
INTERNET_FLAG_NO_AUTO_REDIRECT = 0x00200000
INTERNET_FLAG_READ_PREFETCH = 0x00100000
INTERNET_FLAG_NO_COOKIES = 0x00080000
INTERNET_FLAG_NO_AUTH = 0x00040000
INTERNET_FLAG_RESTRICTED_ZONE = 0x00020000
INTERNET_FLAG_CACHE_IF_NET_FAIL = 0x00010000
INTERNET_FLAG_IGNORE_REDIRECT_TO_HTTP = 0x00008000
INTERNET_FLAG_IGNORE_REDIRECT_TO_HTTPS = 0x00004000
INTERNET_FLAG_IGNORE_CERT_DATE_INVALID = 0x00002000
INTERNET_FLAG_IGNORE_CERT_CN_INVALID = 0x00001000
INTERNET_FLAG_RESYNCHRONIZE = 0x00000800
INTERNET_FLAG_HYPERLINK = 0x00000400
INTERNET_FLAG_NO_UI = 0x00000200
INTERNET_FLAG_PRAGMA_NOCACHE = 0x00000100
INTERNET_FLAG_CACHE_ASYNC = 0x00000080
INTERNET_FLAG_FORMS_SUBMIT = 0x00000040
INTERNET_FLAG_FWD_BACK = 0x00000020
INTERNET_FLAG_NEED_FILE = 0x00000010
INTERNET_FLAG_MUST_CACHE_REQUEST = INTERNET_FLAG_NEED_FILE
SECURITY_INTERNET_MASK = (
    INTERNET_FLAG_IGNORE_CERT_CN_INVALID
    | INTERNET_FLAG_IGNORE_CERT_DATE_INVALID
    | INTERNET_FLAG_IGNORE_REDIRECT_TO_HTTPS
    | INTERNET_FLAG_IGNORE_REDIRECT_TO_HTTP
)
INTERNET_ERROR_MASK_INSERT_CDROM = 0x1
INTERNET_ERROR_MASK_COMBINED_SEC_CERT = 0x2
INTERNET_ERROR_MASK_NEED_MSN_SSPI_PKG = 0x4
INTERNET_ERROR_MASK_LOGIN_FAILURE_DISPLAY_ENTITY_BODY = 0x8
WININET_API_FLAG_ASYNC = 0x00000001
WININET_API_FLAG_SYNC = 0x00000004
WININET_API_FLAG_USE_CONTEXT = 0x00000008
INTERNET_NO_CALLBACK = 0
IDSI_FLAG_KEEP_ALIVE = 0x00000001
IDSI_FLAG_SECURE = 0x00000002
IDSI_FLAG_PROXY = 0x00000004
IDSI_FLAG_TUNNEL = 0x00000008
INTERNET_PER_CONN_FLAGS = 1
INTERNET_PER_CONN_PROXY_SERVER = 2
INTERNET_PER_CONN_PROXY_BYPASS = 3
INTERNET_PER_CONN_AUTOCONFIG_URL = 4
INTERNET_PER_CONN_AUTODISCOVERY_FLAGS = 5
INTERNET_PER_CONN_AUTOCONFIG_SECONDARY_URL = 6
INTERNET_PER_CONN_AUTOCONFIG_RELOAD_DELAY_MINS = 7
INTERNET_PER_CONN_AUTOCONFIG_LAST_DETECT_TIME = 8
INTERNET_PER_CONN_AUTOCONFIG_LAST_DETECT_URL = 9
PROXY_TYPE_DIRECT = 0x00000001
PROXY_TYPE_PROXY = 0x00000002
PROXY_TYPE_AUTO_PROXY_URL = 0x00000004
PROXY_TYPE_AUTO_DETECT = 0x00000008
AUTO_PROXY_FLAG_USER_SET = 0x00000001
AUTO_PROXY_FLAG_ALWAYS_DETECT = 0x00000002
AUTO_PROXY_FLAG_DETECTION_RUN = 0x00000004
AUTO_PROXY_FLAG_MIGRATED = 0x00000008
AUTO_PROXY_FLAG_DONT_CACHE_PROXY_RESULT = 0x00000010
AUTO_PROXY_FLAG_CACHE_INIT_RUN = 0x00000020
AUTO_PROXY_FLAG_DETECTION_SUSPECT = 0x00000040
ISO_FORCE_DISCONNECTED = 0x00000001
INTERNET_RFC1123_FORMAT = 0
INTERNET_RFC1123_BUFSIZE = 30
ICU_ESCAPE = -2147483648
ICU_ESCAPE_AUTHORITY = 0x00002000
ICU_REJECT_USERPWD = 0x00004000
ICU_USERNAME = 0x40000000
ICU_NO_ENCODE = 0x20000000
ICU_DECODE = 0x10000000
ICU_NO_META = 0x08000000
ICU_ENCODE_SPACES_ONLY = 0x04000000
ICU_BROWSER_MODE = 0x02000000
ICU_ENCODE_PERCENT = 0x00001000
INTERNET_OPEN_TYPE_PRECONFIG = 0
INTERNET_OPEN_TYPE_DIRECT = 1
INTERNET_OPEN_TYPE_PROXY = 3
INTERNET_OPEN_TYPE_PRECONFIG_WITH_NO_AUTOPROXY = 4
PRE_CONFIG_INTERNET_ACCESS = INTERNET_OPEN_TYPE_PRECONFIG
LOCAL_INTERNET_ACCESS = INTERNET_OPEN_TYPE_DIRECT
CERN_PROXY_INTERNET_ACCESS = INTERNET_OPEN_TYPE_PROXY
INTERNET_SERVICE_FTP = 1
INTERNET_SERVICE_GOPHER = 2
INTERNET_SERVICE_HTTP = 3
IRF_ASYNC = WININET_API_FLAG_ASYNC
IRF_SYNC = WININET_API_FLAG_SYNC
IRF_USE_CONTEXT = WININET_API_FLAG_USE_CONTEXT
IRF_NO_WAIT = 0x00000008
ISO_GLOBAL = 0x00000001
ISO_REGISTRY = 0x00000002
ISO_VALID_FLAGS = ISO_GLOBAL | ISO_REGISTRY
INTERNET_OPTION_CALLBACK = 1
INTERNET_OPTION_CONNECT_TIMEOUT = 2
INTERNET_OPTION_CONNECT_RETRIES = 3
INTERNET_OPTION_CONNECT_BACKOFF = 4
INTERNET_OPTION_SEND_TIMEOUT = 5
INTERNET_OPTION_CONTROL_SEND_TIMEOUT = INTERNET_OPTION_SEND_TIMEOUT
INTERNET_OPTION_RECEIVE_TIMEOUT = 6
INTERNET_OPTION_CONTROL_RECEIVE_TIMEOUT = INTERNET_OPTION_RECEIVE_TIMEOUT
INTERNET_OPTION_DATA_SEND_TIMEOUT = 7
INTERNET_OPTION_DATA_RECEIVE_TIMEOUT = 8
INTERNET_OPTION_HANDLE_TYPE = 9
INTERNET_OPTION_LISTEN_TIMEOUT = 11
INTERNET_OPTION_READ_BUFFER_SIZE = 12
INTERNET_OPTION_WRITE_BUFFER_SIZE = 13
INTERNET_OPTION_ASYNC_ID = 15
INTERNET_OPTION_ASYNC_PRIORITY = 16
INTERNET_OPTION_PARENT_HANDLE = 21
INTERNET_OPTION_KEEP_CONNECTION = 22
INTERNET_OPTION_REQUEST_FLAGS = 23
INTERNET_OPTION_EXTENDED_ERROR = 24
INTERNET_OPTION_OFFLINE_MODE = 26
INTERNET_OPTION_CACHE_STREAM_HANDLE = 27
INTERNET_OPTION_USERNAME = 28
INTERNET_OPTION_PASSWORD = 29
INTERNET_OPTION_ASYNC = 30
INTERNET_OPTION_SECURITY_FLAGS = 31
INTERNET_OPTION_SECURITY_CERTIFICATE_STRUCT = 32
INTERNET_OPTION_DATAFILE_NAME = 33
INTERNET_OPTION_URL = 34
INTERNET_OPTION_SECURITY_CERTIFICATE = 35
INTERNET_OPTION_SECURITY_KEY_BITNESS = 36
INTERNET_OPTION_REFRESH = 37
INTERNET_OPTION_PROXY = 38
INTERNET_OPTION_SETTINGS_CHANGED = 39
INTERNET_OPTION_VERSION = 40
INTERNET_OPTION_USER_AGENT = 41
INTERNET_OPTION_END_BROWSER_SESSION = 42
INTERNET_OPTION_PROXY_USERNAME = 43
INTERNET_OPTION_PROXY_PASSWORD = 44
INTERNET_OPTION_CONTEXT_VALUE = 45
INTERNET_OPTION_CONNECT_LIMIT = 46
INTERNET_OPTION_SECURITY_SELECT_CLIENT_CERT = 47
INTERNET_OPTION_POLICY = 48
INTERNET_OPTION_DISCONNECTED_TIMEOUT = 49
INTERNET_OPTION_CONNECTED_STATE = 50
INTERNET_OPTION_IDLE_STATE = 51
INTERNET_OPTION_OFFLINE_SEMANTICS = 52
INTERNET_OPTION_SECONDARY_CACHE_KEY = 53
INTERNET_OPTION_CALLBACK_FILTER = 54
INTERNET_OPTION_CONNECT_TIME = 55
INTERNET_OPTION_SEND_THROUGHPUT = 56
INTERNET_OPTION_RECEIVE_THROUGHPUT = 57
INTERNET_OPTION_REQUEST_PRIORITY = 58
INTERNET_OPTION_HTTP_VERSION = 59
INTERNET_OPTION_RESET_URLCACHE_SESSION = 60
INTERNET_OPTION_ERROR_MASK = 62
INTERNET_OPTION_FROM_CACHE_TIMEOUT = 63
INTERNET_OPTION_BYPASS_EDITED_ENTRY = 64
INTERNET_OPTION_DIAGNOSTIC_SOCKET_INFO = 67
INTERNET_OPTION_CODEPAGE = 68
INTERNET_OPTION_CACHE_TIMESTAMPS = 69
INTERNET_OPTION_DISABLE_AUTODIAL = 70
INTERNET_OPTION_MAX_CONNS_PER_SERVER = 73
INTERNET_OPTION_MAX_CONNS_PER_1_0_SERVER = 74
INTERNET_OPTION_PER_CONNECTION_OPTION = 75
INTERNET_OPTION_DIGEST_AUTH_UNLOAD = 76
INTERNET_OPTION_IGNORE_OFFLINE = 77
INTERNET_OPTION_IDENTITY = 78
INTERNET_OPTION_REMOVE_IDENTITY = 79
INTERNET_OPTION_ALTER_IDENTITY = 80
INTERNET_OPTION_SUPPRESS_BEHAVIOR = 81
INTERNET_OPTION_AUTODIAL_MODE = 82
INTERNET_OPTION_AUTODIAL_CONNECTION = 83
INTERNET_OPTION_CLIENT_CERT_CONTEXT = 84
INTERNET_OPTION_AUTH_FLAGS = 85
INTERNET_OPTION_COOKIES_3RD_PARTY = 86
INTERNET_OPTION_DISABLE_PASSPORT_AUTH = 87
INTERNET_OPTION_SEND_UTF8_SERVERNAME_TO_PROXY = 88
INTERNET_OPTION_EXEMPT_CONNECTION_LIMIT = 89
INTERNET_OPTION_ENABLE_PASSPORT_AUTH = 90
INTERNET_OPTION_HIBERNATE_INACTIVE_WORKER_THREADS = 91
INTERNET_OPTION_ACTIVATE_WORKER_THREADS = 92
INTERNET_OPTION_RESTORE_WORKER_THREAD_DEFAULTS = 93
INTERNET_OPTION_SOCKET_SEND_BUFFER_LENGTH = 94
INTERNET_OPTION_PROXY_SETTINGS_CHANGED = 95
INTERNET_FIRST_OPTION = INTERNET_OPTION_CALLBACK
INTERNET_LAST_OPTION = INTERNET_OPTION_PROXY_SETTINGS_CHANGED
INTERNET_PRIORITY_FOREGROUND = 1000
INTERNET_HANDLE_TYPE_INTERNET = 1
INTERNET_HANDLE_TYPE_CONNECT_FTP = 2
INTERNET_HANDLE_TYPE_CONNECT_GOPHER = 3
INTERNET_HANDLE_TYPE_CONNECT_HTTP = 4
INTERNET_HANDLE_TYPE_FTP_FIND = 5
INTERNET_HANDLE_TYPE_FTP_FIND_HTML = 6
INTERNET_HANDLE_TYPE_FTP_FILE = 7
INTERNET_HANDLE_TYPE_FTP_FILE_HTML = 8
INTERNET_HANDLE_TYPE_GOPHER_FIND = 9
INTERNET_HANDLE_TYPE_GOPHER_FIND_HTML = 10
INTERNET_HANDLE_TYPE_GOPHER_FILE = 11
INTERNET_HANDLE_TYPE_GOPHER_FILE_HTML = 12
INTERNET_HANDLE_TYPE_HTTP_REQUEST = 13
INTERNET_HANDLE_TYPE_FILE_REQUEST = 14
AUTH_FLAG_DISABLE_NEGOTIATE = 0x00000001
AUTH_FLAG_ENABLE_NEGOTIATE = 0x00000002
SECURITY_FLAG_SECURE = 0x00000001
SECURITY_FLAG_STRENGTH_WEAK = 0x10000000
SECURITY_FLAG_STRENGTH_MEDIUM = 0x40000000
SECURITY_FLAG_STRENGTH_STRONG = 0x20000000
SECURITY_FLAG_UNKNOWNBIT = -2147483648
SECURITY_FLAG_FORTEZZA = 0x08000000
SECURITY_FLAG_NORMALBITNESS = SECURITY_FLAG_STRENGTH_WEAK
SECURITY_FLAG_SSL = 0x00000002
SECURITY_FLAG_SSL3 = 0x00000004
SECURITY_FLAG_PCT = 0x00000008
SECURITY_FLAG_PCT4 = 0x00000010
SECURITY_FLAG_IETFSSL4 = 0x00000020
SECURITY_FLAG_40BIT = SECURITY_FLAG_STRENGTH_WEAK
SECURITY_FLAG_128BIT = SECURITY_FLAG_STRENGTH_STRONG
SECURITY_FLAG_56BIT = SECURITY_FLAG_STRENGTH_MEDIUM
SECURITY_FLAG_IGNORE_REVOCATION = 0x00000080
SECURITY_FLAG_IGNORE_UNKNOWN_CA = 0x00000100
SECURITY_FLAG_IGNORE_WRONG_USAGE = 0x00000200
SECURITY_FLAG_IGNORE_CERT_CN_INVALID = INTERNET_FLAG_IGNORE_CERT_CN_INVALID
SECURITY_FLAG_IGNORE_CERT_DATE_INVALID = INTERNET_FLAG_IGNORE_CERT_DATE_INVALID
SECURITY_FLAG_IGNORE_CERT_WRONG_USAGE = 0x00000200
SECURITY_FLAG_IGNORE_REDIRECT_TO_HTTPS = INTERNET_FLAG_IGNORE_REDIRECT_TO_HTTPS
SECURITY_FLAG_IGNORE_REDIRECT_TO_HTTP = INTERNET_FLAG_IGNORE_REDIRECT_TO_HTTP
SECURITY_SET_MASK = (
    SECURITY_FLAG_IGNORE_REVOCATION
    | SECURITY_FLAG_IGNORE_UNKNOWN_CA
    | SECURITY_FLAG_IGNORE_CERT_CN_INVALID
    | SECURITY_FLAG_IGNORE_CERT_DATE_INVALID
    | SECURITY_FLAG_IGNORE_WRONG_USAGE
)
AUTODIAL_MODE_NEVER = 1
AUTODIAL_MODE_ALWAYS = 2
AUTODIAL_MODE_NO_NETWORK_PRESENT = 4
INTERNET_STATUS_RESOLVING_NAME = 10
INTERNET_STATUS_NAME_RESOLVED = 11
INTERNET_STATUS_CONNECTING_TO_SERVER = 20
INTERNET_STATUS_CONNECTED_TO_SERVER = 21
INTERNET_STATUS_SENDING_REQUEST = 30
INTERNET_STATUS_REQUEST_SENT = 31
INTERNET_STATUS_RECEIVING_RESPONSE = 40
INTERNET_STATUS_RESPONSE_RECEIVED = 41
INTERNET_STATUS_CTL_RESPONSE_RECEIVED = 42
INTERNET_STATUS_PREFETCH = 43
INTERNET_STATUS_CLOSING_CONNECTION = 50
INTERNET_STATUS_CONNECTION_CLOSED = 51
INTERNET_STATUS_HANDLE_CREATED = 60
INTERNET_STATUS_HANDLE_CLOSING = 70
INTERNET_STATUS_DETECTING_PROXY = 80
INTERNET_STATUS_REQUEST_COMPLETE = 100
INTERNET_STATUS_REDIRECT = 110
INTERNET_STATUS_INTERMEDIATE_RESPONSE = 120
INTERNET_STATUS_USER_INPUT_REQUIRED = 140
INTERNET_STATUS_STATE_CHANGE = 200
INTERNET_STATUS_COOKIE_SENT = 320
INTERNET_STATUS_COOKIE_RECEIVED = 321
INTERNET_STATUS_PRIVACY_IMPACTED = 324
INTERNET_STATUS_P3P_HEADER = 325
INTERNET_STATUS_P3P_POLICYREF = 326
INTERNET_STATUS_COOKIE_HISTORY = 327
INTERNET_STATE_CONNECTED = 0x00000001
INTERNET_STATE_DISCONNECTED = 0x00000002
INTERNET_STATE_DISCONNECTED_BY_USER = 0x00000010
INTERNET_STATE_IDLE = 0x00000100
INTERNET_STATE_BUSY = 0x00000200
FTP_TRANSFER_TYPE_UNKNOWN = 0x00000000
FTP_TRANSFER_TYPE_ASCII = 0x00000001
FTP_TRANSFER_TYPE_BINARY = 0x00000002
FTP_TRANSFER_TYPE_MASK = FTP_TRANSFER_TYPE_ASCII | FTP_TRANSFER_TYPE_BINARY
MAX_GOPHER_DISPLAY_TEXT = 128
MAX_GOPHER_SELECTOR_TEXT = 256
MAX_GOPHER_HOST_NAME = INTERNET_MAX_HOST_NAME_LENGTH
MAX_GOPHER_LOCATOR_LENGTH = (
    1
    + MAX_GOPHER_DISPLAY_TEXT
    + 1
    + MAX_GOPHER_SELECTOR_TEXT
    + 1
    + MAX_GOPHER_HOST_NAME
    + 1
    + INTERNET_MAX_PORT_NUMBER_LENGTH
    + 1
    + 1
    + 2
)
GOPHER_TYPE_TEXT_FILE = 0x00000001
GOPHER_TYPE_DIRECTORY = 0x00000002
GOPHER_TYPE_CSO = 0x00000004
GOPHER_TYPE_ERROR = 0x00000008
GOPHER_TYPE_MAC_BINHEX = 0x00000010
GOPHER_TYPE_DOS_ARCHIVE = 0x00000020
GOPHER_TYPE_UNIX_UUENCODED = 0x00000040
GOPHER_TYPE_INDEX_SERVER = 0x00000080
GOPHER_TYPE_TELNET = 0x00000100
GOPHER_TYPE_BINARY = 0x00000200
GOPHER_TYPE_REDUNDANT = 0x00000400
GOPHER_TYPE_TN3270 = 0x00000800
GOPHER_TYPE_GIF = 0x00001000
GOPHER_TYPE_IMAGE = 0x00002000
GOPHER_TYPE_BITMAP = 0x00004000
GOPHER_TYPE_MOVIE = 0x00008000
GOPHER_TYPE_SOUND = 0x00010000
GOPHER_TYPE_HTML = 0x00020000
GOPHER_TYPE_PDF = 0x00040000
GOPHER_TYPE_CALENDAR = 0x00080000
GOPHER_TYPE_INLINE = 0x00100000
GOPHER_TYPE_UNKNOWN = 0x20000000
GOPHER_TYPE_ASK = 0x40000000
GOPHER_TYPE_GOPHER_PLUS = -2147483648
GOPHER_TYPE_FILE_MASK = (
    GOPHER_TYPE_TEXT_FILE
    | GOPHER_TYPE_MAC_BINHEX
    | GOPHER_TYPE_DOS_ARCHIVE
    | GOPHER_TYPE_UNIX_UUENCODED
    | GOPHER_TYPE_BINARY
    | GOPHER_TYPE_GIF
    | GOPHER_TYPE_IMAGE
    | GOPHER_TYPE_BITMAP
    | GOPHER_TYPE_MOVIE
    | GOPHER_TYPE_SOUND
    | GOPHER_TYPE_HTML
    | GOPHER_TYPE_PDF
    | GOPHER_TYPE_CALENDAR
    | GOPHER_TYPE_INLINE
)
MAX_GOPHER_CATEGORY_NAME = 128
MAX_GOPHER_ATTRIBUTE_NAME = 128
MIN_GOPHER_ATTRIBUTE_LENGTH = 256
GOPHER_ATTRIBUTE_ID_BASE = -1412641792
GOPHER_CATEGORY_ID_ALL = GOPHER_ATTRIBUTE_ID_BASE + 1
GOPHER_CATEGORY_ID_INFO = GOPHER_ATTRIBUTE_ID_BASE + 2
GOPHER_CATEGORY_ID_ADMIN = GOPHER_ATTRIBUTE_ID_BASE + 3
GOPHER_CATEGORY_ID_VIEWS = GOPHER_ATTRIBUTE_ID_BASE + 4
GOPHER_CATEGORY_ID_ABSTRACT = GOPHER_ATTRIBUTE_ID_BASE + 5
GOPHER_CATEGORY_ID_VERONICA = GOPHER_ATTRIBUTE_ID_BASE + 6
GOPHER_CATEGORY_ID_ASK = GOPHER_ATTRIBUTE_ID_BASE + 7
GOPHER_CATEGORY_ID_UNKNOWN = GOPHER_ATTRIBUTE_ID_BASE + 8
GOPHER_ATTRIBUTE_ID_ALL = GOPHER_ATTRIBUTE_ID_BASE + 9
GOPHER_ATTRIBUTE_ID_ADMIN = GOPHER_ATTRIBUTE_ID_BASE + 10
GOPHER_ATTRIBUTE_ID_MOD_DATE = GOPHER_ATTRIBUTE_ID_BASE + 11
GOPHER_ATTRIBUTE_ID_TTL = GOPHER_ATTRIBUTE_ID_BASE + 12
GOPHER_ATTRIBUTE_ID_SCORE = GOPHER_ATTRIBUTE_ID_BASE + 13
GOPHER_ATTRIBUTE_ID_RANGE = GOPHER_ATTRIBUTE_ID_BASE + 14
GOPHER_ATTRIBUTE_ID_SITE = GOPHER_ATTRIBUTE_ID_BASE + 15
GOPHER_ATTRIBUTE_ID_ORG = GOPHER_ATTRIBUTE_ID_BASE + 16
GOPHER_ATTRIBUTE_ID_LOCATION = GOPHER_ATTRIBUTE_ID_BASE + 17
GOPHER_ATTRIBUTE_ID_GEOG = GOPHER_ATTRIBUTE_ID_BASE + 18
GOPHER_ATTRIBUTE_ID_TIMEZONE = GOPHER_ATTRIBUTE_ID_BASE + 19
GOPHER_ATTRIBUTE_ID_PROVIDER = GOPHER_ATTRIBUTE_ID_BASE + 20
GOPHER_ATTRIBUTE_ID_VERSION = GOPHER_ATTRIBUTE_ID_BASE + 21
GOPHER_ATTRIBUTE_ID_ABSTRACT = GOPHER_ATTRIBUTE_ID_BASE + 22
GOPHER_ATTRIBUTE_ID_VIEW = GOPHER_ATTRIBUTE_ID_BASE + 23
GOPHER_ATTRIBUTE_ID_TREEWALK = GOPHER_ATTRIBUTE_ID_BASE + 24
GOPHER_ATTRIBUTE_ID_UNKNOWN = GOPHER_ATTRIBUTE_ID_BASE + 25
HTTP_MAJOR_VERSION = 1
HTTP_MINOR_VERSION = 0
HTTP_VERSIONA = "HTTP/1.0"
HTTP_VERSION = HTTP_VERSIONA
HTTP_QUERY_MIME_VERSION = 0
HTTP_QUERY_CONTENT_TYPE = 1
HTTP_QUERY_CONTENT_TRANSFER_ENCODING = 2
HTTP_QUERY_CONTENT_ID = 3
HTTP_QUERY_CONTENT_DESCRIPTION = 4
HTTP_QUERY_CONTENT_LENGTH = 5
HTTP_QUERY_CONTENT_LANGUAGE = 6
HTTP_QUERY_ALLOW = 7
HTTP_QUERY_PUBLIC = 8
HTTP_QUERY_DATE = 9
HTTP_QUERY_EXPIRES = 10
HTTP_QUERY_LAST_MODIFIED = 11
HTTP_QUERY_MESSAGE_ID = 12
HTTP_QUERY_URI = 13
HTTP_QUERY_DERIVED_FROM = 14
HTTP_QUERY_COST = 15
HTTP_QUERY_LINK = 16
HTTP_QUERY_PRAGMA = 17
HTTP_QUERY_VERSION = 18
HTTP_QUERY_STATUS_CODE = 19
HTTP_QUERY_STATUS_TEXT = 20
HTTP_QUERY_RAW_HEADERS = 21
HTTP_QUERY_RAW_HEADERS_CRLF = 22
HTTP_QUERY_CONNECTION = 23
HTTP_QUERY_ACCEPT = 24
HTTP_QUERY_ACCEPT_CHARSET = 25
HTTP_QUERY_ACCEPT_ENCODING = 26
HTTP_QUERY_ACCEPT_LANGUAGE = 27
HTTP_QUERY_AUTHORIZATION = 28
HTTP_QUERY_CONTENT_ENCODING = 29
HTTP_QUERY_FORWARDED = 30
HTTP_QUERY_FROM = 31
HTTP_QUERY_IF_MODIFIED_SINCE = 32
HTTP_QUERY_LOCATION = 33
HTTP_QUERY_ORIG_URI = 34
HTTP_QUERY_REFERER = 35
HTTP_QUERY_RETRY_AFTER = 36
HTTP_QUERY_SERVER = 37
HTTP_QUERY_TITLE = 38
HTTP_QUERY_USER_AGENT = 39
HTTP_QUERY_WWW_AUTHENTICATE = 40
HTTP_QUERY_PROXY_AUTHENTICATE = 41
HTTP_QUERY_ACCEPT_RANGES = 42
HTTP_QUERY_SET_COOKIE = 43
HTTP_QUERY_COOKIE = 44
HTTP_QUERY_REQUEST_METHOD = 45
HTTP_QUERY_REFRESH = 46
HTTP_QUERY_CONTENT_DISPOSITION = 47
HTTP_QUERY_AGE = 48
HTTP_QUERY_CACHE_CONTROL = 49
HTTP_QUERY_CONTENT_BASE = 50
HTTP_QUERY_CONTENT_LOCATION = 51
HTTP_QUERY_CONTENT_MD5 = 52
HTTP_QUERY_CONTENT_RANGE = 53
HTTP_QUERY_ETAG = 54
HTTP_QUERY_HOST = 55
HTTP_QUERY_IF_MATCH = 56
HTTP_QUERY_IF_NONE_MATCH = 57
HTTP_QUERY_IF_RANGE = 58
HTTP_QUERY_IF_UNMODIFIED_SINCE = 59
HTTP_QUERY_MAX_FORWARDS = 60
HTTP_QUERY_PROXY_AUTHORIZATION = 61
HTTP_QUERY_RANGE = 62
HTTP_QUERY_TRANSFER_ENCODING = 63
HTTP_QUERY_UPGRADE = 64
HTTP_QUERY_VARY = 65
HTTP_QUERY_VIA = 66
HTTP_QUERY_WARNING = 67
HTTP_QUERY_EXPECT = 68
HTTP_QUERY_PROXY_CONNECTION = 69
HTTP_QUERY_UNLESS_MODIFIED_SINCE = 70
HTTP_QUERY_ECHO_REQUEST = 71
HTTP_QUERY_ECHO_REPLY = 72
HTTP_QUERY_ECHO_HEADERS = 73
HTTP_QUERY_ECHO_HEADERS_CRLF = 74
HTTP_QUERY_PROXY_SUPPORT = 75
HTTP_QUERY_AUTHENTICATION_INFO = 76
HTTP_QUERY_PASSPORT_URLS = 77
HTTP_QUERY_PASSPORT_CONFIG = 78
HTTP_QUERY_MAX = 78
HTTP_QUERY_CUSTOM = 65535
HTTP_QUERY_FLAG_REQUEST_HEADERS = -2147483648
HTTP_QUERY_FLAG_SYSTEMTIME = 0x40000000
HTTP_QUERY_FLAG_NUMBER = 0x20000000
HTTP_QUERY_FLAG_COALESCE = 0x10000000
HTTP_QUERY_MODIFIER_FLAGS_MASK = (
    HTTP_QUERY_FLAG_REQUEST_HEADERS
    | HTTP_QUERY_FLAG_SYSTEMTIME
    | HTTP_QUERY_FLAG_NUMBER
    | HTTP_QUERY_FLAG_COALESCE
)
HTTP_QUERY_HEADER_MASK = ~HTTP_QUERY_MODIFIER_FLAGS_MASK
HTTP_STATUS_CONTINUE = 100
HTTP_STATUS_SWITCH_PROTOCOLS = 101
HTTP_STATUS_OK = 200
HTTP_STATUS_CREATED = 201
HTTP_STATUS_ACCEPTED = 202
HTTP_STATUS_PARTIAL = 203
HTTP_STATUS_NO_CONTENT = 204
HTTP_STATUS_RESET_CONTENT = 205
HTTP_STATUS_PARTIAL_CONTENT = 206
HTTP_STATUS_WEBDAV_MULTI_STATUS = 207
HTTP_STATUS_AMBIGUOUS = 300
HTTP_STATUS_MOVED = 301
HTTP_STATUS_REDIRECT = 302
HTTP_STATUS_REDIRECT_METHOD = 303
HTTP_STATUS_NOT_MODIFIED = 304
HTTP_STATUS_USE_PROXY = 305
HTTP_STATUS_REDIRECT_KEEP_VERB = 307
HTTP_STATUS_BAD_REQUEST = 400
HTTP_STATUS_DENIED = 401
HTTP_STATUS_PAYMENT_REQ = 402
HTTP_STATUS_FORBIDDEN = 403
HTTP_STATUS_NOT_FOUND = 404
HTTP_STATUS_BAD_METHOD = 405
HTTP_STATUS_NONE_ACCEPTABLE = 406
HTTP_STATUS_PROXY_AUTH_REQ = 407
HTTP_STATUS_REQUEST_TIMEOUT = 408
HTTP_STATUS_CONFLICT = 409
HTTP_STATUS_GONE = 410
HTTP_STATUS_LENGTH_REQUIRED = 411
HTTP_STATUS_PRECOND_FAILED = 412
HTTP_STATUS_REQUEST_TOO_LARGE = 413
HTTP_STATUS_URI_TOO_LONG = 414
HTTP_STATUS_UNSUPPORTED_MEDIA = 415
HTTP_STATUS_RETRY_WITH = 449
HTTP_STATUS_SERVER_ERROR = 500
HTTP_STATUS_NOT_SUPPORTED = 501
HTTP_STATUS_BAD_GATEWAY = 502
HTTP_STATUS_SERVICE_UNAVAIL = 503
HTTP_STATUS_GATEWAY_TIMEOUT = 504
HTTP_STATUS_VERSION_NOT_SUP = 505
HTTP_STATUS_FIRST = HTTP_STATUS_CONTINUE
HTTP_STATUS_LAST = HTTP_STATUS_VERSION_NOT_SUP
HTTP_ADDREQ_INDEX_MASK = 0x0000FFFF
HTTP_ADDREQ_FLAGS_MASK = -65536
HTTP_ADDREQ_FLAG_ADD_IF_NEW = 0x10000000
HTTP_ADDREQ_FLAG_ADD = 0x20000000
HTTP_ADDREQ_FLAG_COALESCE_WITH_COMMA = 0x40000000
HTTP_ADDREQ_FLAG_COALESCE_WITH_SEMICOLON = 0x01000000
HTTP_ADDREQ_FLAG_COALESCE = HTTP_ADDREQ_FLAG_COALESCE_WITH_COMMA
HTTP_ADDREQ_FLAG_REPLACE = -2147483648
HSR_ASYNC = WININET_API_FLAG_ASYNC
HSR_SYNC = WININET_API_FLAG_SYNC
HSR_USE_CONTEXT = WININET_API_FLAG_USE_CONTEXT
HSR_INITIATE = 0x00000008
HSR_DOWNLOAD = 0x00000010
HSR_CHUNKED = 0x00000020
INTERNET_COOKIE_IS_SECURE = 0x01
INTERNET_COOKIE_IS_SESSION = 0x02
INTERNET_COOKIE_THIRD_PARTY = 0x10
INTERNET_COOKIE_PROMPT_REQUIRED = 0x20
INTERNET_COOKIE_EVALUATE_P3P = 0x40
INTERNET_COOKIE_APPLY_P3P = 0x80
INTERNET_COOKIE_P3P_ENABLED = 0x100
INTERNET_COOKIE_IS_RESTRICTED = 0x200
INTERNET_COOKIE_IE6 = 0x400
INTERNET_COOKIE_IS_LEGACY = 0x800
FLAG_ICC_FORCE_CONNECTION = 0x00000001
FLAGS_ERROR_UI_FILTER_FOR_ERRORS = 0x01
FLAGS_ERROR_UI_FLAGS_CHANGE_OPTIONS = 0x02
FLAGS_ERROR_UI_FLAGS_GENERATE_DATA = 0x04
FLAGS_ERROR_UI_FLAGS_NO_UI = 0x08
FLAGS_ERROR_UI_SERIALIZE_DIALOGS = 0x10
INTERNET_ERROR_BASE = 12000
ERROR_INTERNET_OUT_OF_HANDLES = INTERNET_ERROR_BASE + 1
ERROR_INTERNET_TIMEOUT = INTERNET_ERROR_BASE + 2
ERROR_INTERNET_EXTENDED_ERROR = INTERNET_ERROR_BASE + 3
ERROR_INTERNET_INTERNAL_ERROR = INTERNET_ERROR_BASE + 4
ERROR_INTERNET_INVALID_URL = INTERNET_ERROR_BASE + 5
ERROR_INTERNET_UNRECOGNIZED_SCHEME = INTERNET_ERROR_BASE + 6
ERROR_INTERNET_NAME_NOT_RESOLVED = INTERNET_ERROR_BASE + 7
ERROR_INTERNET_PROTOCOL_NOT_FOUND = INTERNET_ERROR_BASE + 8
ERROR_INTERNET_INVALID_OPTION = INTERNET_ERROR_BASE + 9
ERROR_INTERNET_BAD_OPTION_LENGTH = INTERNET_ERROR_BASE + 10
ERROR_INTERNET_OPTION_NOT_SETTABLE = INTERNET_ERROR_BASE + 11
ERROR_INTERNET_SHUTDOWN = INTERNET_ERROR_BASE + 12
ERROR_INTERNET_INCORRECT_USER_NAME = INTERNET_ERROR_BASE + 13
ERROR_INTERNET_INCORRECT_PASSWORD = INTERNET_ERROR_BASE + 14
ERROR_INTERNET_LOGIN_FAILURE = INTERNET_ERROR_BASE + 15
ERROR_INTERNET_INVALID_OPERATION = INTERNET_ERROR_BASE + 16
ERROR_INTERNET_OPERATION_CANCELLED = INTERNET_ERROR_BASE + 17
ERROR_INTERNET_INCORRECT_HANDLE_TYPE = INTERNET_ERROR_BASE + 18
ERROR_INTERNET_INCORRECT_HANDLE_STATE = INTERNET_ERROR_BASE + 19
ERROR_INTERNET_NOT_PROXY_REQUEST = INTERNET_ERROR_BASE + 20
ERROR_INTERNET_REGISTRY_VALUE_NOT_FOUND = INTERNET_ERROR_BASE + 21
ERROR_INTERNET_BAD_REGISTRY_PARAMETER = INTERNET_ERROR_BASE + 22
ERROR_INTERNET_NO_DIRECT_ACCESS = INTERNET_ERROR_BASE + 23
ERROR_INTERNET_NO_CONTEXT = INTERNET_ERROR_BASE + 24
ERROR_INTERNET_NO_CALLBACK = INTERNET_ERROR_BASE + 25
ERROR_INTERNET_REQUEST_PENDING = INTERNET_ERROR_BASE + 26
ERROR_INTERNET_INCORRECT_FORMAT = INTERNET_ERROR_BASE + 27
ERROR_INTERNET_ITEM_NOT_FOUND = INTERNET_ERROR_BASE + 28
ERROR_INTERNET_CANNOT_CONNECT = INTERNET_ERROR_BASE + 29
ERROR_INTERNET_CONNECTION_ABORTED = INTERNET_ERROR_BASE + 30
ERROR_INTERNET_CONNECTION_RESET = INTERNET_ERROR_BASE + 31
ERROR_INTERNET_FORCE_RETRY = INTERNET_ERROR_BASE + 32
ERROR_INTERNET_INVALID_PROXY_REQUEST = INTERNET_ERROR_BASE + 33
ERROR_INTERNET_NEED_UI = INTERNET_ERROR_BASE + 34
ERROR_INTERNET_HANDLE_EXISTS = INTERNET_ERROR_BASE + 36
ERROR_INTERNET_SEC_CERT_DATE_INVALID = INTERNET_ERROR_BASE + 37
ERROR_INTERNET_SEC_CERT_CN_INVALID = INTERNET_ERROR_BASE + 38
ERROR_INTERNET_HTTP_TO_HTTPS_ON_REDIR = INTERNET_ERROR_BASE + 39
ERROR_INTERNET_HTTPS_TO_HTTP_ON_REDIR = INTERNET_ERROR_BASE + 40
ERROR_INTERNET_MIXED_SECURITY = INTERNET_ERROR_BASE + 41
ERROR_INTERNET_CHG_POST_IS_NON_SECURE = INTERNET_ERROR_BASE + 42
ERROR_INTERNET_POST_IS_NON_SECURE = INTERNET_ERROR_BASE + 43
ERROR_INTERNET_CLIENT_AUTH_CERT_NEEDED = INTERNET_ERROR_BASE + 44
ERROR_INTERNET_INVALID_CA = INTERNET_ERROR_BASE + 45
ERROR_INTERNET_CLIENT_AUTH_NOT_SETUP = INTERNET_ERROR_BASE + 46
ERROR_INTERNET_ASYNC_THREAD_FAILED = INTERNET_ERROR_BASE + 47
ERROR_INTERNET_REDIRECT_SCHEME_CHANGE = INTERNET_ERROR_BASE + 48
ERROR_INTERNET_DIALOG_PENDING = INTERNET_ERROR_BASE + 49
ERROR_INTERNET_RETRY_DIALOG = INTERNET_ERROR_BASE + 50
ERROR_INTERNET_HTTPS_HTTP_SUBMIT_REDIR = INTERNET_ERROR_BASE + 52
ERROR_INTERNET_INSERT_CDROM = INTERNET_ERROR_BASE + 53
ERROR_INTERNET_FORTEZZA_LOGIN_NEEDED = INTERNET_ERROR_BASE + 54
ERROR_INTERNET_SEC_CERT_ERRORS = INTERNET_ERROR_BASE + 55
ERROR_INTERNET_SEC_CERT_NO_REV = INTERNET_ERROR_BASE + 56
ERROR_INTERNET_SEC_CERT_REV_FAILED = INTERNET_ERROR_BASE + 57
ERROR_FTP_TRANSFER_IN_PROGRESS = INTERNET_ERROR_BASE + 110
ERROR_FTP_DROPPED = INTERNET_ERROR_BASE + 111
ERROR_FTP_NO_PASSIVE_MODE = INTERNET_ERROR_BASE + 112
ERROR_GOPHER_PROTOCOL_ERROR = INTERNET_ERROR_BASE + 130
ERROR_GOPHER_NOT_FILE = INTERNET_ERROR_BASE + 131
ERROR_GOPHER_DATA_ERROR = INTERNET_ERROR_BASE + 132
ERROR_GOPHER_END_OF_DATA = INTERNET_ERROR_BASE + 133
ERROR_GOPHER_INVALID_LOCATOR = INTERNET_ERROR_BASE + 134
ERROR_GOPHER_INCORRECT_LOCATOR_TYPE = INTERNET_ERROR_BASE + 135
ERROR_GOPHER_NOT_GOPHER_PLUS = INTERNET_ERROR_BASE + 136
ERROR_GOPHER_ATTRIBUTE_NOT_FOUND = INTERNET_ERROR_BASE + 137
ERROR_GOPHER_UNKNOWN_LOCATOR = INTERNET_ERROR_BASE + 138
ERROR_HTTP_HEADER_NOT_FOUND = INTERNET_ERROR_BASE + 150
ERROR_HTTP_DOWNLEVEL_SERVER = INTERNET_ERROR_BASE + 151
ERROR_HTTP_INVALID_SERVER_RESPONSE = INTERNET_ERROR_BASE + 152
ERROR_HTTP_INVALID_HEADER = INTERNET_ERROR_BASE + 153
ERROR_HTTP_INVALID_QUERY_REQUEST = INTERNET_ERROR_BASE + 154
ERROR_HTTP_HEADER_ALREADY_EXISTS = INTERNET_ERROR_BASE + 155
ERROR_HTTP_REDIRECT_FAILED = INTERNET_ERROR_BASE + 156
ERROR_HTTP_NOT_REDIRECTED = INTERNET_ERROR_BASE + 160
ERROR_HTTP_COOKIE_NEEDS_CONFIRMATION = INTERNET_ERROR_BASE + 161
ERROR_HTTP_COOKIE_DECLINED = INTERNET_ERROR_BASE + 162
ERROR_HTTP_REDIRECT_NEEDS_CONFIRMATION = INTERNET_ERROR_BASE + 168
ERROR_INTERNET_SECURITY_CHANNEL_ERROR = INTERNET_ERROR_BASE + 157
ERROR_INTERNET_UNABLE_TO_CACHE_FILE = INTERNET_ERROR_BASE + 158
ERROR_INTERNET_TCPIP_NOT_INSTALLED = INTERNET_ERROR_BASE + 159
ERROR_INTERNET_DISCONNECTED = INTERNET_ERROR_BASE + 163
ERROR_INTERNET_SERVER_UNREACHABLE = INTERNET_ERROR_BASE + 164
ERROR_INTERNET_PROXY_SERVER_UNREACHABLE = INTERNET_ERROR_BASE + 165
ERROR_INTERNET_BAD_AUTO_PROXY_SCRIPT = INTERNET_ERROR_BASE + 166
ERROR_INTERNET_UNABLE_TO_DOWNLOAD_SCRIPT = INTERNET_ERROR_BASE + 167
ERROR_INTERNET_SEC_INVALID_CERT = INTERNET_ERROR_BASE + 169
ERROR_INTERNET_SEC_CERT_REVOKED = INTERNET_ERROR_BASE + 170
ERROR_INTERNET_FAILED_DUETOSECURITYCHECK = INTERNET_ERROR_BASE + 171
ERROR_INTERNET_NOT_INITIALIZED = INTERNET_ERROR_BASE + 172
ERROR_INTERNET_NEED_MSN_SSPI_PKG = INTERNET_ERROR_BASE + 173
ERROR_INTERNET_LOGIN_FAILURE_DISPLAY_ENTITY_BODY = INTERNET_ERROR_BASE + 174
INTERNET_ERROR_LAST = ERROR_INTERNET_LOGIN_FAILURE_DISPLAY_ENTITY_BODY
NORMAL_CACHE_ENTRY = 0x00000001
STICKY_CACHE_ENTRY = 0x00000004
EDITED_CACHE_ENTRY = 0x00000008
TRACK_OFFLINE_CACHE_ENTRY = 0x00000010
TRACK_ONLINE_CACHE_ENTRY = 0x00000020
SPARSE_CACHE_ENTRY = 0x00010000
COOKIE_CACHE_ENTRY = 0x00100000
URLHISTORY_CACHE_ENTRY = 0x00200000
URLCACHE_FIND_DEFAULT_FILTER = (
    NORMAL_CACHE_ENTRY
    | COOKIE_CACHE_ENTRY
    | URLHISTORY_CACHE_ENTRY
    | TRACK_OFFLINE_CACHE_ENTRY
    | TRACK_ONLINE_CACHE_ENTRY
    | STICKY_CACHE_ENTRY
)
CACHEGROUP_ATTRIBUTE_GET_ALL = -1
CACHEGROUP_ATTRIBUTE_BASIC = 0x00000001
CACHEGROUP_ATTRIBUTE_FLAG = 0x00000002
CACHEGROUP_ATTRIBUTE_TYPE = 0x00000004
CACHEGROUP_ATTRIBUTE_QUOTA = 0x00000008
CACHEGROUP_ATTRIBUTE_GROUPNAME = 0x00000010
CACHEGROUP_ATTRIBUTE_STORAGE = 0x00000020
CACHEGROUP_FLAG_NONPURGEABLE = 0x00000001
CACHEGROUP_FLAG_GIDONLY = 0x00000004
CACHEGROUP_FLAG_FLUSHURL_ONDELETE = 0x00000002
CACHEGROUP_SEARCH_ALL = 0x00000000
CACHEGROUP_SEARCH_BYURL = 0x00000001
CACHEGROUP_TYPE_INVALID = 0x00000001
CACHEGROUP_READWRITE_MASK = (
    CACHEGROUP_ATTRIBUTE_TYPE
    | CACHEGROUP_ATTRIBUTE_QUOTA
    | CACHEGROUP_ATTRIBUTE_GROUPNAME
    | CACHEGROUP_ATTRIBUTE_STORAGE
)
GROUPNAME_MAX_LENGTH = 120
GROUP_OWNER_STORAGE_SIZE = 4
CACHE_ENTRY_ATTRIBUTE_FC = 0x00000004
CACHE_ENTRY_HITRATE_FC = 0x00000010
CACHE_ENTRY_MODTIME_FC = 0x00000040
CACHE_ENTRY_EXPTIME_FC = 0x00000080
CACHE_ENTRY_ACCTIME_FC = 0x00000100
CACHE_ENTRY_SYNCTIME_FC = 0x00000200
CACHE_ENTRY_HEADERINFO_FC = 0x00000400
CACHE_ENTRY_EXEMPT_DELTA_FC = 0x00000800
INTERNET_CACHE_GROUP_ADD = 0
INTERNET_CACHE_GROUP_REMOVE = 1
INTERNET_DIAL_FORCE_PROMPT = 0x2000
INTERNET_DIAL_SHOW_OFFLINE = 0x4000
INTERNET_DIAL_UNATTENDED = 0x8000
INTERENT_GOONLINE_REFRESH = 0x00000001
INTERENT_GOONLINE_MASK = 0x00000001
INTERNET_AUTODIAL_FORCE_ONLINE = 1
INTERNET_AUTODIAL_FORCE_UNATTENDED = 2
INTERNET_AUTODIAL_FAILIFSECURITYCHECK = 4
INTERNET_AUTODIAL_OVERRIDE_NET_PRESENT = 8
INTERNET_AUTODIAL_FLAGS_MASK = (
    INTERNET_AUTODIAL_FORCE_ONLINE
    | INTERNET_AUTODIAL_FORCE_UNATTENDED
    | INTERNET_AUTODIAL_FAILIFSECURITYCHECK
    | INTERNET_AUTODIAL_OVERRIDE_NET_PRESENT
)
PROXY_AUTO_DETECT_TYPE_DHCP = 1
PROXY_AUTO_DETECT_TYPE_DNS_A = 2
INTERNET_CONNECTION_MODEM = 0x01
INTERNET_CONNECTION_LAN = 0x02
INTERNET_CONNECTION_PROXY = 0x04
INTERNET_CONNECTION_MODEM_BUSY = 0x08
INTERNET_RAS_INSTALLED = 0x10
INTERNET_CONNECTION_OFFLINE = 0x20
INTERNET_CONNECTION_CONFIGURED = 0x40
INTERNET_CUSTOMDIAL_CONNECT = 0
INTERNET_CUSTOMDIAL_UNATTENDED = 1
INTERNET_CUSTOMDIAL_DISCONNECT = 2
INTERNET_CUSTOMDIAL_SHOWOFFLINE = 4
INTERNET_CUSTOMDIAL_SAFE_FOR_UNATTENDED = 1
INTERNET_CUSTOMDIAL_WILL_SUPPLY_STATE = 2
INTERNET_CUSTOMDIAL_CAN_HANGUP = 4
INTERNET_DIALSTATE_DISCONNECTED = 1
INTERNET_IDENTITY_FLAG_PRIVATE_CACHE = 0x01
INTERNET_IDENTITY_FLAG_SHARED_CACHE = 0x02
INTERNET_IDENTITY_FLAG_CLEAR_DATA = 0x04
INTERNET_IDENTITY_FLAG_CLEAR_COOKIES = 0x08
INTERNET_IDENTITY_FLAG_CLEAR_HISTORY = 0x10
INTERNET_IDENTITY_FLAG_CLEAR_CONTENT = 0x20
INTERNET_SUPPRESS_RESET_ALL = 0x00
INTERNET_SUPPRESS_COOKIE_POLICY = 0x01
INTERNET_SUPPRESS_COOKIE_POLICY_RESET = 0x02
PRIVACY_TEMPLATE_NO_COOKIES = 0
PRIVACY_TEMPLATE_HIGH = 1
PRIVACY_TEMPLATE_MEDIUM_HIGH = 2
PRIVACY_TEMPLATE_MEDIUM = 3
PRIVACY_TEMPLATE_MEDIUM_LOW = 4
PRIVACY_TEMPLATE_LOW = 5
PRIVACY_TEMPLATE_CUSTOM = 100
PRIVACY_TEMPLATE_ADVANCED = 101
PRIVACY_TEMPLATE_MAX = PRIVACY_TEMPLATE_LOW
PRIVACY_TYPE_FIRST_PARTY = 0
PRIVACY_TYPE_THIRD_PARTY = 1

# Generated by h2py from winhttp.h
WINHTTP_FLAG_ASYNC = 0x10000000
WINHTTP_FLAG_SECURE = 0x00800000
WINHTTP_FLAG_ESCAPE_PERCENT = 0x00000004
WINHTTP_FLAG_NULL_CODEPAGE = 0x00000008
WINHTTP_FLAG_BYPASS_PROXY_CACHE = 0x00000100
WINHTTP_FLAG_REFRESH = WINHTTP_FLAG_BYPASS_PROXY_CACHE
WINHTTP_FLAG_ESCAPE_DISABLE = 0x00000040
WINHTTP_FLAG_ESCAPE_DISABLE_QUERY = 0x00000080
INTERNET_SCHEME_HTTP = 1
INTERNET_SCHEME_HTTPS = 2
WINHTTP_AUTOPROXY_AUTO_DETECT = 0x00000001
WINHTTP_AUTOPROXY_CONFIG_URL = 0x00000002
WINHTTP_AUTOPROXY_RUN_INPROCESS = 0x00010000
WINHTTP_AUTOPROXY_RUN_OUTPROCESS_ONLY = 0x00020000
WINHTTP_AUTO_DETECT_TYPE_DHCP = 0x00000001
WINHTTP_AUTO_DETECT_TYPE_DNS_A = 0x00000002
WINHTTP_TIME_FORMAT_BUFSIZE = 62
WINHTTP_ACCESS_TYPE_DEFAULT_PROXY = 0
WINHTTP_ACCESS_TYPE_NO_PROXY = 1
WINHTTP_ACCESS_TYPE_NAMED_PROXY = 3
WINHTTP_OPTION_CALLBACK = 1
WINHTTP_OPTION_RESOLVE_TIMEOUT = 2
WINHTTP_OPTION_CONNECT_TIMEOUT = 3
WINHTTP_OPTION_CONNECT_RETRIES = 4
WINHTTP_OPTION_SEND_TIMEOUT = 5
WINHTTP_OPTION_RECEIVE_TIMEOUT = 6
WINHTTP_OPTION_RECEIVE_RESPONSE_TIMEOUT = 7
WINHTTP_OPTION_HANDLE_TYPE = 9
WINHTTP_OPTION_READ_BUFFER_SIZE = 12
WINHTTP_OPTION_WRITE_BUFFER_SIZE = 13
WINHTTP_OPTION_PARENT_HANDLE = 21
WINHTTP_OPTION_EXTENDED_ERROR = 24
WINHTTP_OPTION_SECURITY_FLAGS = 31
WINHTTP_OPTION_SECURITY_CERTIFICATE_STRUCT = 32
WINHTTP_OPTION_URL = 34
WINHTTP_OPTION_SECURITY_KEY_BITNESS = 36
WINHTTP_OPTION_PROXY = 38
WINHTTP_OPTION_USER_AGENT = 41
WINHTTP_OPTION_CONTEXT_VALUE = 45
WINHTTP_OPTION_CLIENT_CERT_CONTEXT = 47
WINHTTP_OPTION_REQUEST_PRIORITY = 58
WINHTTP_OPTION_HTTP_VERSION = 59
WINHTTP_OPTION_DISABLE_FEATURE = 63
WINHTTP_OPTION_CODEPAGE = 68
WINHTTP_OPTION_MAX_CONNS_PER_SERVER = 73
WINHTTP_OPTION_MAX_CONNS_PER_1_0_SERVER = 74
WINHTTP_OPTION_AUTOLOGON_POLICY = 77
WINHTTP_OPTION_SERVER_CERT_CONTEXT = 78
WINHTTP_OPTION_ENABLE_FEATURE = 79
WINHTTP_OPTION_WORKER_THREAD_COUNT = 80
WINHTTP_OPTION_PASSPORT_COBRANDING_TEXT = 81
WINHTTP_OPTION_PASSPORT_COBRANDING_URL = 82
WINHTTP_OPTION_CONFIGURE_PASSPORT_AUTH = 83
WINHTTP_OPTION_SECURE_PROTOCOLS = 84
WINHTTP_OPTION_ENABLETRACING = 85
WINHTTP_OPTION_PASSPORT_SIGN_OUT = 86
WINHTTP_OPTION_PASSPORT_RETURN_URL = 87
WINHTTP_OPTION_REDIRECT_POLICY = 88
WINHTTP_OPTION_MAX_HTTP_AUTOMATIC_REDIRECTS = 89
WINHTTP_OPTION_MAX_HTTP_STATUS_CONTINUE = 90
WINHTTP_OPTION_MAX_RESPONSE_HEADER_SIZE = 91
WINHTTP_OPTION_MAX_RESPONSE_DRAIN_SIZE = 92
WINHTTP_OPTION_CONNECTION_INFO = 93
WINHTTP_OPTION_CLIENT_CERT_ISSUER_LIST = 94
WINHTTP_OPTION_SPN = 96
WINHTTP_OPTION_GLOBAL_PROXY_CREDS = 97
WINHTTP_OPTION_GLOBAL_SERVER_CREDS = 98
WINHTTP_OPTION_UNLOAD_NOTIFY_EVENT = 99
WINHTTP_OPTION_REJECT_USERPWD_IN_URL = 100
WINHTTP_OPTION_USE_GLOBAL_SERVER_CREDENTIALS = 101
WINHTTP_LAST_OPTION = WINHTTP_OPTION_USE_GLOBAL_SERVER_CREDENTIALS
WINHTTP_OPTION_USERNAME = 0x1000
WINHTTP_OPTION_PASSWORD = 0x1001
WINHTTP_OPTION_PROXY_USERNAME = 0x1002
WINHTTP_OPTION_PROXY_PASSWORD = 0x1003
WINHTTP_CONNS_PER_SERVER_UNLIMITED = -1
WINHTTP_AUTOLOGON_SECURITY_LEVEL_MEDIUM = 0
WINHTTP_AUTOLOGON_SECURITY_LEVEL_LOW = 1
WINHTTP_AUTOLOGON_SECURITY_LEVEL_HIGH = 2
WINHTTP_AUTOLOGON_SECURITY_LEVEL_DEFAULT = WINHTTP_AUTOLOGON_SECURITY_LEVEL_MEDIUM
WINHTTP_OPTION_REDIRECT_POLICY_NEVER = 0
WINHTTP_OPTION_REDIRECT_POLICY_DISALLOW_HTTPS_TO_HTTP = 1
WINHTTP_OPTION_REDIRECT_POLICY_ALWAYS = 2
WINHTTP_OPTION_REDIRECT_POLICY_LAST = WINHTTP_OPTION_REDIRECT_POLICY_ALWAYS
WINHTTP_OPTION_REDIRECT_POLICY_DEFAULT = (
    WINHTTP_OPTION_REDIRECT_POLICY_DISALLOW_HTTPS_TO_HTTP
)
WINHTTP_DISABLE_PASSPORT_AUTH = 0x00000000
WINHTTP_ENABLE_PASSPORT_AUTH = 0x10000000
WINHTTP_DISABLE_PASSPORT_KEYRING = 0x20000000
WINHTTP_ENABLE_PASSPORT_KEYRING = 0x40000000
WINHTTP_DISABLE_COOKIES = 0x00000001
WINHTTP_DISABLE_REDIRECTS = 0x00000002
WINHTTP_DISABLE_AUTHENTICATION = 0x00000004
WINHTTP_DISABLE_KEEP_ALIVE = 0x00000008
WINHTTP_ENABLE_SSL_REVOCATION = 0x00000001
WINHTTP_ENABLE_SSL_REVERT_IMPERSONATION = 0x00000002
WINHTTP_DISABLE_SPN_SERVER_PORT = 0x00000000
WINHTTP_ENABLE_SPN_SERVER_PORT = 0x00000001
WINHTTP_OPTION_SPN_MASK = WINHTTP_ENABLE_SPN_SERVER_PORT
WINHTTP_HANDLE_TYPE_SESSION = 1
WINHTTP_HANDLE_TYPE_CONNECT = 2
WINHTTP_HANDLE_TYPE_REQUEST = 3
WINHTTP_AUTH_SCHEME_BASIC = 0x00000001
WINHTTP_AUTH_SCHEME_NTLM = 0x00000002
WINHTTP_AUTH_SCHEME_PASSPORT = 0x00000004
WINHTTP_AUTH_SCHEME_DIGEST = 0x00000008
WINHTTP_AUTH_SCHEME_NEGOTIATE = 0x00000010
WINHTTP_AUTH_TARGET_SERVER = 0x00000000
WINHTTP_AUTH_TARGET_PROXY = 0x00000001
WINHTTP_CALLBACK_STATUS_FLAG_CERT_REV_FAILED = 0x00000001
WINHTTP_CALLBACK_STATUS_FLAG_INVALID_CERT = 0x00000002
WINHTTP_CALLBACK_STATUS_FLAG_CERT_REVOKED = 0x00000004
WINHTTP_CALLBACK_STATUS_FLAG_INVALID_CA = 0x00000008
WINHTTP_CALLBACK_STATUS_FLAG_CERT_CN_INVALID = 0x00000010
WINHTTP_CALLBACK_STATUS_FLAG_CERT_DATE_INVALID = 0x00000020
WINHTTP_CALLBACK_STATUS_FLAG_CERT_WRONG_USAGE = 0x00000040
WINHTTP_CALLBACK_STATUS_FLAG_SECURITY_CHANNEL_ERROR = -2147483648
WINHTTP_FLAG_SECURE_PROTOCOL_SSL2 = 0x00000008
WINHTTP_FLAG_SECURE_PROTOCOL_SSL3 = 0x00000020
WINHTTP_FLAG_SECURE_PROTOCOL_TLS1 = 0x00000080
WINHTTP_FLAG_SECURE_PROTOCOL_ALL = (
    WINHTTP_FLAG_SECURE_PROTOCOL_SSL2
    | WINHTTP_FLAG_SECURE_PROTOCOL_SSL3
    | WINHTTP_FLAG_SECURE_PROTOCOL_TLS1
)
WINHTTP_CALLBACK_STATUS_RESOLVING_NAME = 0x00000001
WINHTTP_CALLBACK_STATUS_NAME_RESOLVED = 0x00000002
WINHTTP_CALLBACK_STATUS_CONNECTING_TO_SERVER = 0x00000004
WINHTTP_CALLBACK_STATUS_CONNECTED_TO_SERVER = 0x00000008
WINHTTP_CALLBACK_STATUS_SENDING_REQUEST = 0x00000010
WINHTTP_CALLBACK_STATUS_REQUEST_SENT = 0x00000020
WINHTTP_CALLBACK_STATUS_RECEIVING_RESPONSE = 0x00000040
WINHTTP_CALLBACK_STATUS_RESPONSE_RECEIVED = 0x00000080
WINHTTP_CALLBACK_STATUS_CLOSING_CONNECTION = 0x00000100
WINHTTP_CALLBACK_STATUS_CONNECTION_CLOSED = 0x00000200
WINHTTP_CALLBACK_STATUS_HANDLE_CREATED = 0x00000400
WINHTTP_CALLBACK_STATUS_HANDLE_CLOSING = 0x00000800
WINHTTP_CALLBACK_STATUS_DETECTING_PROXY = 0x00001000
WINHTTP_CALLBACK_STATUS_REDIRECT = 0x00004000
WINHTTP_CALLBACK_STATUS_INTERMEDIATE_RESPONSE = 0x00008000
WINHTTP_CALLBACK_STATUS_SECURE_FAILURE = 0x00010000
WINHTTP_CALLBACK_STATUS_HEADERS_AVAILABLE = 0x00020000
WINHTTP_CALLBACK_STATUS_DATA_AVAILABLE = 0x00040000
WINHTTP_CALLBACK_STATUS_READ_COMPLETE = 0x00080000
WINHTTP_CALLBACK_STATUS_WRITE_COMPLETE = 0x00100000
WINHTTP_CALLBACK_STATUS_REQUEST_ERROR = 0x00200000
WINHTTP_CALLBACK_STATUS_SENDREQUEST_COMPLETE = 0x00400000
API_RECEIVE_RESPONSE = 1
API_QUERY_DATA_AVAILABLE = 2
API_READ_DATA = 3
API_WRITE_DATA = 4
API_SEND_REQUEST = 5
WINHTTP_CALLBACK_FLAG_RESOLVE_NAME = (
    WINHTTP_CALLBACK_STATUS_RESOLVING_NAME | WINHTTP_CALLBACK_STATUS_NAME_RESOLVED
)
WINHTTP_CALLBACK_FLAG_CONNECT_TO_SERVER = (
    WINHTTP_CALLBACK_STATUS_CONNECTING_TO_SERVER
    | WINHTTP_CALLBACK_STATUS_CONNECTED_TO_SERVER
)
WINHTTP_CALLBACK_FLAG_SEND_REQUEST = (
    WINHTTP_CALLBACK_STATUS_SENDING_REQUEST | WINHTTP_CALLBACK_STATUS_REQUEST_SENT
)
WINHTTP_CALLBACK_FLAG_RECEIVE_RESPONSE = (
    WINHTTP_CALLBACK_STATUS_RECEIVING_RESPONSE
    | WINHTTP_CALLBACK_STATUS_RESPONSE_RECEIVED
)
WINHTTP_CALLBACK_FLAG_CLOSE_CONNECTION = (
    WINHTTP_CALLBACK_STATUS_CLOSING_CONNECTION
    | WINHTTP_CALLBACK_STATUS_CONNECTION_CLOSED
)
WINHTTP_CALLBACK_FLAG_HANDLES = (
    WINHTTP_CALLBACK_STATUS_HANDLE_CREATED | WINHTTP_CALLBACK_STATUS_HANDLE_CLOSING
)
WINHTTP_CALLBACK_FLAG_DETECTING_PROXY = WINHTTP_CALLBACK_STATUS_DETECTING_PROXY
WINHTTP_CALLBACK_FLAG_REDIRECT = WINHTTP_CALLBACK_STATUS_REDIRECT
WINHTTP_CALLBACK_FLAG_INTERMEDIATE_RESPONSE = (
    WINHTTP_CALLBACK_STATUS_INTERMEDIATE_RESPONSE
)
WINHTTP_CALLBACK_FLAG_SECURE_FAILURE = WINHTTP_CALLBACK_STATUS_SECURE_FAILURE
WINHTTP_CALLBACK_FLAG_SENDREQUEST_COMPLETE = (
    WINHTTP_CALLBACK_STATUS_SENDREQUEST_COMPLETE
)
WINHTTP_CALLBACK_FLAG_HEADERS_AVAILABLE = WINHTTP_CALLBACK_STATUS_HEADERS_AVAILABLE
WINHTTP_CALLBACK_FLAG_DATA_AVAILABLE = WINHTTP_CALLBACK_STATUS_DATA_AVAILABLE
WINHTTP_CALLBACK_FLAG_READ_COMPLETE = WINHTTP_CALLBACK_STATUS_READ_COMPLETE
WINHTTP_CALLBACK_FLAG_WRITE_COMPLETE = WINHTTP_CALLBACK_STATUS_WRITE_COMPLETE
WINHTTP_CALLBACK_FLAG_REQUEST_ERROR = WINHTTP_CALLBACK_STATUS_REQUEST_ERROR
WINHTTP_CALLBACK_FLAG_ALL_COMPLETIONS = (
    WINHTTP_CALLBACK_STATUS_SENDREQUEST_COMPLETE
    | WINHTTP_CALLBACK_STATUS_HEADERS_AVAILABLE
    | WINHTTP_CALLBACK_STATUS_DATA_AVAILABLE
    | WINHTTP_CALLBACK_STATUS_READ_COMPLETE
    | WINHTTP_CALLBACK_STATUS_WRITE_COMPLETE
    | WINHTTP_CALLBACK_STATUS_REQUEST_ERROR
)
WINHTTP_CALLBACK_FLAG_ALL_NOTIFICATIONS = -1
WINHTTP_QUERY_MIME_VERSION = 0
WINHTTP_QUERY_CONTENT_TYPE = 1
WINHTTP_QUERY_CONTENT_TRANSFER_ENCODING = 2
WINHTTP_QUERY_CONTENT_ID = 3
WINHTTP_QUERY_CONTENT_DESCRIPTION = 4
WINHTTP_QUERY_CONTENT_LENGTH = 5
WINHTTP_QUERY_CONTENT_LANGUAGE = 6
WINHTTP_QUERY_ALLOW = 7
WINHTTP_QUERY_PUBLIC = 8
WINHTTP_QUERY_DATE = 9
WINHTTP_QUERY_EXPIRES = 10
WINHTTP_QUERY_LAST_MODIFIED = 11
WINHTTP_QUERY_MESSAGE_ID = 12
WINHTTP_QUERY_URI = 13
WINHTTP_QUERY_DERIVED_FROM = 14
WINHTTP_QUERY_COST = 15
WINHTTP_QUERY_LINK = 16
WINHTTP_QUERY_PRAGMA = 17
WINHTTP_QUERY_VERSION = 18
WINHTTP_QUERY_STATUS_CODE = 19
WINHTTP_QUERY_STATUS_TEXT = 20
WINHTTP_QUERY_RAW_HEADERS = 21
WINHTTP_QUERY_RAW_HEADERS_CRLF = 22
WINHTTP_QUERY_CONNECTION = 23
WINHTTP_QUERY_ACCEPT = 24
WINHTTP_QUERY_ACCEPT_CHARSET = 25
WINHTTP_QUERY_ACCEPT_ENCODING = 26
WINHTTP_QUERY_ACCEPT_LANGUAGE = 27
WINHTTP_QUERY_AUTHORIZATION = 28
WINHTTP_QUERY_CONTENT_ENCODING = 29
WINHTTP_QUERY_FORWARDED = 30
WINHTTP_QUERY_FROM = 31
WINHTTP_QUERY_IF_MODIFIED_SINCE = 32
WINHTTP_QUERY_LOCATION = 33
WINHTTP_QUERY_ORIG_URI = 34
WINHTTP_QUERY_REFERER = 35
WINHTTP_QUERY_RETRY_AFTER = 36
WINHTTP_QUERY_SERVER = 37
WINHTTP_QUERY_TITLE = 38
WINHTTP_QUERY_USER_AGENT = 39
WINHTTP_QUERY_WWW_AUTHENTICATE = 40
WINHTTP_QUERY_PROXY_AUTHENTICATE = 41
WINHTTP_QUERY_ACCEPT_RANGES = 42
WINHTTP_QUERY_SET_COOKIE = 43
WINHTTP_QUERY_COOKIE = 44
WINHTTP_QUERY_REQUEST_METHOD = 45
WINHTTP_QUERY_REFRESH = 46
WINHTTP_QUERY_CONTENT_DISPOSITION = 47
WINHTTP_QUERY_AGE = 48
WINHTTP_QUERY_CACHE_CONTROL = 49
WINHTTP_QUERY_CONTENT_BASE = 50
WINHTTP_QUERY_CONTENT_LOCATION = 51
WINHTTP_QUERY_CONTENT_MD5 = 52
WINHTTP_QUERY_CONTENT_RANGE = 53
WINHTTP_QUERY_ETAG = 54
WINHTTP_QUERY_HOST = 55
WINHTTP_QUERY_IF_MATCH = 56
WINHTTP_QUERY_IF_NONE_MATCH = 57
WINHTTP_QUERY_IF_RANGE = 58
WINHTTP_QUERY_IF_UNMODIFIED_SINCE = 59
WINHTTP_QUERY_MAX_FORWARDS = 60
WINHTTP_QUERY_PROXY_AUTHORIZATION = 61
WINHTTP_QUERY_RANGE = 62
WINHTTP_QUERY_TRANSFER_ENCODING = 63
WINHTTP_QUERY_UPGRADE = 64
WINHTTP_QUERY_VARY = 65
WINHTTP_QUERY_VIA = 66
WINHTTP_QUERY_WARNING = 67
WINHTTP_QUERY_EXPECT = 68
WINHTTP_QUERY_PROXY_CONNECTION = 69
WINHTTP_QUERY_UNLESS_MODIFIED_SINCE = 70
WINHTTP_QUERY_PROXY_SUPPORT = 75
WINHTTP_QUERY_AUTHENTICATION_INFO = 76
WINHTTP_QUERY_PASSPORT_URLS = 77
WINHTTP_QUERY_PASSPORT_CONFIG = 78
WINHTTP_QUERY_MAX = 78
WINHTTP_QUERY_CUSTOM = 65535
WINHTTP_QUERY_FLAG_REQUEST_HEADERS = -2147483648
WINHTTP_QUERY_FLAG_SYSTEMTIME = 0x40000000
WINHTTP_QUERY_FLAG_NUMBER = 0x20000000
WINHTTP_ADDREQ_INDEX_MASK = 0x0000FFFF
WINHTTP_ADDREQ_FLAGS_MASK = -65536
WINHTTP_ADDREQ_FLAG_ADD_IF_NEW = 0x10000000
WINHTTP_ADDREQ_FLAG_ADD = 0x20000000
WINHTTP_ADDREQ_FLAG_COALESCE_WITH_COMMA = 0x40000000
WINHTTP_ADDREQ_FLAG_COALESCE_WITH_SEMICOLON = 0x01000000
WINHTTP_ADDREQ_FLAG_COALESCE = WINHTTP_ADDREQ_FLAG_COALESCE_WITH_COMMA
WINHTTP_ADDREQ_FLAG_REPLACE = -2147483648
WINHTTP_IGNORE_REQUEST_TOTAL_LENGTH = 0
WINHTTP_ERROR_BASE = 12000
ERROR_WINHTTP_OUT_OF_HANDLES = WINHTTP_ERROR_BASE + 1
ERROR_WINHTTP_TIMEOUT = WINHTTP_ERROR_BASE + 2
ERROR_WINHTTP_INTERNAL_ERROR = WINHTTP_ERROR_BASE + 4
ERROR_WINHTTP_INVALID_URL = WINHTTP_ERROR_BASE + 5
ERROR_WINHTTP_UNRECOGNIZED_SCHEME = WINHTTP_ERROR_BASE + 6
ERROR_WINHTTP_NAME_NOT_RESOLVED = WINHTTP_ERROR_BASE + 7
ERROR_WINHTTP_INVALID_OPTION = WINHTTP_ERROR_BASE + 9
ERROR_WINHTTP_OPTION_NOT_SETTABLE = WINHTTP_ERROR_BASE + 11
ERROR_WINHTTP_SHUTDOWN = WINHTTP_ERROR_BASE + 12
ERROR_WINHTTP_LOGIN_FAILURE = WINHTTP_ERROR_BASE + 15
ERROR_WINHTTP_OPERATION_CANCELLED = WINHTTP_ERROR_BASE + 17
ERROR_WINHTTP_INCORRECT_HANDLE_TYPE = WINHTTP_ERROR_BASE + 18
ERROR_WINHTTP_INCORRECT_HANDLE_STATE = WINHTTP_ERROR_BASE + 19
ERROR_WINHTTP_CANNOT_CONNECT = WINHTTP_ERROR_BASE + 29
ERROR_WINHTTP_CONNECTION_ERROR = WINHTTP_ERROR_BASE + 30
ERROR_WINHTTP_RESEND_REQUEST = WINHTTP_ERROR_BASE + 32
ERROR_WINHTTP_CLIENT_AUTH_CERT_NEEDED = WINHTTP_ERROR_BASE + 44
ERROR_WINHTTP_CANNOT_CALL_BEFORE_OPEN = WINHTTP_ERROR_BASE + 100
ERROR_WINHTTP_CANNOT_CALL_BEFORE_SEND = WINHTTP_ERROR_BASE + 101
ERROR_WINHTTP_CANNOT_CALL_AFTER_SEND = WINHTTP_ERROR_BASE + 102
ERROR_WINHTTP_CANNOT_CALL_AFTER_OPEN = WINHTTP_ERROR_BASE + 103
ERROR_WINHTTP_HEADER_NOT_FOUND = WINHTTP_ERROR_BASE + 150
ERROR_WINHTTP_INVALID_SERVER_RESPONSE = WINHTTP_ERROR_BASE + 152
ERROR_WINHTTP_INVALID_HEADER = WINHTTP_ERROR_BASE + 153
ERROR_WINHTTP_INVALID_QUERY_REQUEST = WINHTTP_ERROR_BASE + 154
ERROR_WINHTTP_HEADER_ALREADY_EXISTS = WINHTTP_ERROR_BASE + 155
ERROR_WINHTTP_REDIRECT_FAILED = WINHTTP_ERROR_BASE + 156
ERROR_WINHTTP_AUTO_PROXY_SERVICE_ERROR = WINHTTP_ERROR_BASE + 178
ERROR_WINHTTP_BAD_AUTO_PROXY_SCRIPT = WINHTTP_ERROR_BASE + 166
ERROR_WINHTTP_UNABLE_TO_DOWNLOAD_SCRIPT = WINHTTP_ERROR_BASE + 167
ERROR_WINHTTP_NOT_INITIALIZED = WINHTTP_ERROR_BASE + 172
ERROR_WINHTTP_SECURE_FAILURE = WINHTTP_ERROR_BASE + 175
ERROR_WINHTTP_SECURE_CERT_DATE_INVALID = WINHTTP_ERROR_BASE + 37
ERROR_WINHTTP_SECURE_CERT_CN_INVALID = WINHTTP_ERROR_BASE + 38
ERROR_WINHTTP_SECURE_INVALID_CA = WINHTTP_ERROR_BASE + 45
ERROR_WINHTTP_SECURE_CERT_REV_FAILED = WINHTTP_ERROR_BASE + 57
ERROR_WINHTTP_SECURE_CHANNEL_ERROR = WINHTTP_ERROR_BASE + 157
ERROR_WINHTTP_SECURE_INVALID_CERT = WINHTTP_ERROR_BASE + 169
ERROR_WINHTTP_SECURE_CERT_REVOKED = WINHTTP_ERROR_BASE + 170
ERROR_WINHTTP_SECURE_CERT_WRONG_USAGE = WINHTTP_ERROR_BASE + 179
ERROR_WINHTTP_AUTODETECTION_FAILED = WINHTTP_ERROR_BASE + 180
ERROR_WINHTTP_HEADER_COUNT_EXCEEDED = WINHTTP_ERROR_BASE + 181
ERROR_WINHTTP_HEADER_SIZE_OVERFLOW = WINHTTP_ERROR_BASE + 182
ERROR_WINHTTP_CHUNKED_ENCODING_HEADER_SIZE_OVERFLOW = WINHTTP_ERROR_BASE + 183
ERROR_WINHTTP_RESPONSE_DRAIN_OVERFLOW = WINHTTP_ERROR_BASE + 184
ERROR_WINHTTP_CLIENT_CERT_NO_PRIVATE_KEY = WINHTTP_ERROR_BASE + 185
ERROR_WINHTTP_CLIENT_CERT_NO_ACCESS_PRIVATE_KEY = WINHTTP_ERROR_BASE + 186
WINHTTP_ERROR_LAST = WINHTTP_ERROR_BASE + 186

WINHTTP_NO_PROXY_NAME = None
WINHTTP_NO_PROXY_BYPASS = None
WINHTTP_NO_REFERER = None
WINHTTP_DEFAULT_ACCEPT_TYPES = None
WINHTTP_NO_ADDITIONAL_HEADERS = None
WINHTTP_NO_REQUEST_DATA = None

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\win32\lib\win32inetcon.py ===
# Generated by h2py from \mssdk\include\WinInet.h

INTERNET_INVALID_PORT_NUMBER = 0
INTERNET_DEFAULT_PORT = 0
INTERNET_DEFAULT_FTP_PORT = 21
INTERNET_DEFAULT_GOPHER_PORT = 70
INTERNET_DEFAULT_HTTP_PORT = 80
INTERNET_DEFAULT_HTTPS_PORT = 443
INTERNET_DEFAULT_SOCKS_PORT = 1080
INTERNET_MAX_HOST_NAME_LENGTH = 256
INTERNET_MAX_USER_NAME_LENGTH = 128
INTERNET_MAX_PASSWORD_LENGTH = 128
INTERNET_MAX_PORT_NUMBER_LENGTH = 5
INTERNET_MAX_PORT_NUMBER_VALUE = 65535
INTERNET_MAX_PATH_LENGTH = 2048
INTERNET_MAX_SCHEME_LENGTH = 32
INTERNET_KEEP_ALIVE_ENABLED = 1
INTERNET_KEEP_ALIVE_DISABLED = 0
INTERNET_REQFLAG_FROM_CACHE = 0x00000001
INTERNET_REQFLAG_ASYNC = 0x00000002
INTERNET_REQFLAG_VIA_PROXY = 0x00000004
INTERNET_REQFLAG_NO_HEADERS = 0x00000008
INTERNET_REQFLAG_PASSIVE = 0x00000010
INTERNET_REQFLAG_CACHE_WRITE_DISABLED = 0x00000040
INTERNET_REQFLAG_NET_TIMEOUT = 0x00000080
INTERNET_FLAG_RELOAD = -2147483648
INTERNET_FLAG_RAW_DATA = 0x40000000
INTERNET_FLAG_EXISTING_CONNECT = 0x20000000
INTERNET_FLAG_ASYNC = 0x10000000
INTERNET_FLAG_PASSIVE = 0x08000000
INTERNET_FLAG_NO_CACHE_WRITE = 0x04000000
INTERNET_FLAG_DONT_CACHE = INTERNET_FLAG_NO_CACHE_WRITE
INTERNET_FLAG_MAKE_PERSISTENT = 0x02000000
INTERNET_FLAG_FROM_CACHE = 0x01000000
INTERNET_FLAG_OFFLINE = INTERNET_FLAG_FROM_CACHE
INTERNET_FLAG_SECURE = 0x00800000
INTERNET_FLAG_KEEP_CONNECTION = 0x00400000
INTERNET_FLAG_NO_AUTO_REDIRECT = 0x00200000
INTERNET_FLAG_READ_PREFETCH = 0x00100000
INTERNET_FLAG_NO_COOKIES = 0x00080000
INTERNET_FLAG_NO_AUTH = 0x00040000
INTERNET_FLAG_RESTRICTED_ZONE = 0x00020000
INTERNET_FLAG_CACHE_IF_NET_FAIL = 0x00010000
INTERNET_FLAG_IGNORE_REDIRECT_TO_HTTP = 0x00008000
INTERNET_FLAG_IGNORE_REDIRECT_TO_HTTPS = 0x00004000
INTERNET_FLAG_IGNORE_CERT_DATE_INVALID = 0x00002000
INTERNET_FLAG_IGNORE_CERT_CN_INVALID = 0x00001000
INTERNET_FLAG_RESYNCHRONIZE = 0x00000800
INTERNET_FLAG_HYPERLINK = 0x00000400
INTERNET_FLAG_NO_UI = 0x00000200
INTERNET_FLAG_PRAGMA_NOCACHE = 0x00000100
INTERNET_FLAG_CACHE_ASYNC = 0x00000080
INTERNET_FLAG_FORMS_SUBMIT = 0x00000040
INTERNET_FLAG_FWD_BACK = 0x00000020
INTERNET_FLAG_NEED_FILE = 0x00000010
INTERNET_FLAG_MUST_CACHE_REQUEST = INTERNET_FLAG_NEED_FILE
SECURITY_INTERNET_MASK = (
    INTERNET_FLAG_IGNORE_CERT_CN_INVALID
    | INTERNET_FLAG_IGNORE_CERT_DATE_INVALID
    | INTERNET_FLAG_IGNORE_REDIRECT_TO_HTTPS
    | INTERNET_FLAG_IGNORE_REDIRECT_TO_HTTP
)
INTERNET_ERROR_MASK_INSERT_CDROM = 0x1
INTERNET_ERROR_MASK_COMBINED_SEC_CERT = 0x2
INTERNET_ERROR_MASK_NEED_MSN_SSPI_PKG = 0x4
INTERNET_ERROR_MASK_LOGIN_FAILURE_DISPLAY_ENTITY_BODY = 0x8
WININET_API_FLAG_ASYNC = 0x00000001
WININET_API_FLAG_SYNC = 0x00000004
WININET_API_FLAG_USE_CONTEXT = 0x00000008
INTERNET_NO_CALLBACK = 0
IDSI_FLAG_KEEP_ALIVE = 0x00000001
IDSI_FLAG_SECURE = 0x00000002
IDSI_FLAG_PROXY = 0x00000004
IDSI_FLAG_TUNNEL = 0x00000008
INTERNET_PER_CONN_FLAGS = 1
INTERNET_PER_CONN_PROXY_SERVER = 2
INTERNET_PER_CONN_PROXY_BYPASS = 3
INTERNET_PER_CONN_AUTOCONFIG_URL = 4
INTERNET_PER_CONN_AUTODISCOVERY_FLAGS = 5
INTERNET_PER_CONN_AUTOCONFIG_SECONDARY_URL = 6
INTERNET_PER_CONN_AUTOCONFIG_RELOAD_DELAY_MINS = 7
INTERNET_PER_CONN_AUTOCONFIG_LAST_DETECT_TIME = 8
INTERNET_PER_CONN_AUTOCONFIG_LAST_DETECT_URL = 9
PROXY_TYPE_DIRECT = 0x00000001
PROXY_TYPE_PROXY = 0x00000002
PROXY_TYPE_AUTO_PROXY_URL = 0x00000004
PROXY_TYPE_AUTO_DETECT = 0x00000008
AUTO_PROXY_FLAG_USER_SET = 0x00000001
AUTO_PROXY_FLAG_ALWAYS_DETECT = 0x00000002
AUTO_PROXY_FLAG_DETECTION_RUN = 0x00000004
AUTO_PROXY_FLAG_MIGRATED = 0x00000008
AUTO_PROXY_FLAG_DONT_CACHE_PROXY_RESULT = 0x00000010
AUTO_PROXY_FLAG_CACHE_INIT_RUN = 0x00000020
AUTO_PROXY_FLAG_DETECTION_SUSPECT = 0x00000040
ISO_FORCE_DISCONNECTED = 0x00000001
INTERNET_RFC1123_FORMAT = 0
INTERNET_RFC1123_BUFSIZE = 30
ICU_ESCAPE = -2147483648
ICU_ESCAPE_AUTHORITY = 0x00002000
ICU_REJECT_USERPWD = 0x00004000
ICU_USERNAME = 0x40000000
ICU_NO_ENCODE = 0x20000000
ICU_DECODE = 0x10000000
ICU_NO_META = 0x08000000
ICU_ENCODE_SPACES_ONLY = 0x04000000
ICU_BROWSER_MODE = 0x02000000
ICU_ENCODE_PERCENT = 0x00001000
INTERNET_OPEN_TYPE_PRECONFIG = 0
INTERNET_OPEN_TYPE_DIRECT = 1
INTERNET_OPEN_TYPE_PROXY = 3
INTERNET_OPEN_TYPE_PRECONFIG_WITH_NO_AUTOPROXY = 4
PRE_CONFIG_INTERNET_ACCESS = INTERNET_OPEN_TYPE_PRECONFIG
LOCAL_INTERNET_ACCESS = INTERNET_OPEN_TYPE_DIRECT
CERN_PROXY_INTERNET_ACCESS = INTERNET_OPEN_TYPE_PROXY
INTERNET_SERVICE_FTP = 1
INTERNET_SERVICE_GOPHER = 2
INTERNET_SERVICE_HTTP = 3
IRF_ASYNC = WININET_API_FLAG_ASYNC
IRF_SYNC = WININET_API_FLAG_SYNC
IRF_USE_CONTEXT = WININET_API_FLAG_USE_CONTEXT
IRF_NO_WAIT = 0x00000008
ISO_GLOBAL = 0x00000001
ISO_REGISTRY = 0x00000002
ISO_VALID_FLAGS = ISO_GLOBAL | ISO_REGISTRY
INTERNET_OPTION_CALLBACK = 1
INTERNET_OPTION_CONNECT_TIMEOUT = 2
INTERNET_OPTION_CONNECT_RETRIES = 3
INTERNET_OPTION_CONNECT_BACKOFF = 4
INTERNET_OPTION_SEND_TIMEOUT = 5
INTERNET_OPTION_CONTROL_SEND_TIMEOUT = INTERNET_OPTION_SEND_TIMEOUT
INTERNET_OPTION_RECEIVE_TIMEOUT = 6
INTERNET_OPTION_CONTROL_RECEIVE_TIMEOUT = INTERNET_OPTION_RECEIVE_TIMEOUT
INTERNET_OPTION_DATA_SEND_TIMEOUT = 7
INTERNET_OPTION_DATA_RECEIVE_TIMEOUT = 8
INTERNET_OPTION_HANDLE_TYPE = 9
INTERNET_OPTION_LISTEN_TIMEOUT = 11
INTERNET_OPTION_READ_BUFFER_SIZE = 12
INTERNET_OPTION_WRITE_BUFFER_SIZE = 13
INTERNET_OPTION_ASYNC_ID = 15
INTERNET_OPTION_ASYNC_PRIORITY = 16
INTERNET_OPTION_PARENT_HANDLE = 21
INTERNET_OPTION_KEEP_CONNECTION = 22
INTERNET_OPTION_REQUEST_FLAGS = 23
INTERNET_OPTION_EXTENDED_ERROR = 24
INTERNET_OPTION_OFFLINE_MODE = 26
INTERNET_OPTION_CACHE_STREAM_HANDLE = 27
INTERNET_OPTION_USERNAME = 28
INTERNET_OPTION_PASSWORD = 29
INTERNET_OPTION_ASYNC = 30
INTERNET_OPTION_SECURITY_FLAGS = 31
INTERNET_OPTION_SECURITY_CERTIFICATE_STRUCT = 32
INTERNET_OPTION_DATAFILE_NAME = 33
INTERNET_OPTION_URL = 34
INTERNET_OPTION_SECURITY_CERTIFICATE = 35
INTERNET_OPTION_SECURITY_KEY_BITNESS = 36
INTERNET_OPTION_REFRESH = 37
INTERNET_OPTION_PROXY = 38
INTERNET_OPTION_SETTINGS_CHANGED = 39
INTERNET_OPTION_VERSION = 40
INTERNET_OPTION_USER_AGENT = 41
INTERNET_OPTION_END_BROWSER_SESSION = 42
INTERNET_OPTION_PROXY_USERNAME = 43
INTERNET_OPTION_PROXY_PASSWORD = 44
INTERNET_OPTION_CONTEXT_VALUE = 45
INTERNET_OPTION_CONNECT_LIMIT = 46
INTERNET_OPTION_SECURITY_SELECT_CLIENT_CERT = 47
INTERNET_OPTION_POLICY = 48
INTERNET_OPTION_DISCONNECTED_TIMEOUT = 49
INTERNET_OPTION_CONNECTED_STATE = 50
INTERNET_OPTION_IDLE_STATE = 51
INTERNET_OPTION_OFFLINE_SEMANTICS = 52
INTERNET_OPTION_SECONDARY_CACHE_KEY = 53
INTERNET_OPTION_CALLBACK_FILTER = 54
INTERNET_OPTION_CONNECT_TIME = 55
INTERNET_OPTION_SEND_THROUGHPUT = 56
INTERNET_OPTION_RECEIVE_THROUGHPUT = 57
INTERNET_OPTION_REQUEST_PRIORITY = 58
INTERNET_OPTION_HTTP_VERSION = 59
INTERNET_OPTION_RESET_URLCACHE_SESSION = 60
INTERNET_OPTION_ERROR_MASK = 62
INTERNET_OPTION_FROM_CACHE_TIMEOUT = 63
INTERNET_OPTION_BYPASS_EDITED_ENTRY = 64
INTERNET_OPTION_DIAGNOSTIC_SOCKET_INFO = 67
INTERNET_OPTION_CODEPAGE = 68
INTERNET_OPTION_CACHE_TIMESTAMPS = 69
INTERNET_OPTION_DISABLE_AUTODIAL = 70
INTERNET_OPTION_MAX_CONNS_PER_SERVER = 73
INTERNET_OPTION_MAX_CONNS_PER_1_0_SERVER = 74
INTERNET_OPTION_PER_CONNECTION_OPTION = 75
INTERNET_OPTION_DIGEST_AUTH_UNLOAD = 76
INTERNET_OPTION_IGNORE_OFFLINE = 77
INTERNET_OPTION_IDENTITY = 78
INTERNET_OPTION_REMOVE_IDENTITY = 79
INTERNET_OPTION_ALTER_IDENTITY = 80
INTERNET_OPTION_SUPPRESS_BEHAVIOR = 81
INTERNET_OPTION_AUTODIAL_MODE = 82
INTERNET_OPTION_AUTODIAL_CONNECTION = 83
INTERNET_OPTION_CLIENT_CERT_CONTEXT = 84
INTERNET_OPTION_AUTH_FLAGS = 85
INTERNET_OPTION_COOKIES_3RD_PARTY = 86
INTERNET_OPTION_DISABLE_PASSPORT_AUTH = 87
INTERNET_OPTION_SEND_UTF8_SERVERNAME_TO_PROXY = 88
INTERNET_OPTION_EXEMPT_CONNECTION_LIMIT = 89
INTERNET_OPTION_ENABLE_PASSPORT_AUTH = 90
INTERNET_OPTION_HIBERNATE_INACTIVE_WORKER_THREADS = 91
INTERNET_OPTION_ACTIVATE_WORKER_THREADS = 92
INTERNET_OPTION_RESTORE_WORKER_THREAD_DEFAULTS = 93
INTERNET_OPTION_SOCKET_SEND_BUFFER_LENGTH = 94
INTERNET_OPTION_PROXY_SETTINGS_CHANGED = 95
INTERNET_FIRST_OPTION = INTERNET_OPTION_CALLBACK
INTERNET_LAST_OPTION = INTERNET_OPTION_PROXY_SETTINGS_CHANGED
INTERNET_PRIORITY_FOREGROUND = 1000
INTERNET_HANDLE_TYPE_INTERNET = 1
INTERNET_HANDLE_TYPE_CONNECT_FTP = 2
INTERNET_HANDLE_TYPE_CONNECT_GOPHER = 3
INTERNET_HANDLE_TYPE_CONNECT_HTTP = 4
INTERNET_HANDLE_TYPE_FTP_FIND = 5
INTERNET_HANDLE_TYPE_FTP_FIND_HTML = 6
INTERNET_HANDLE_TYPE_FTP_FILE = 7
INTERNET_HANDLE_TYPE_FTP_FILE_HTML = 8
INTERNET_HANDLE_TYPE_GOPHER_FIND = 9
INTERNET_HANDLE_TYPE_GOPHER_FIND_HTML = 10
INTERNET_HANDLE_TYPE_GOPHER_FILE = 11
INTERNET_HANDLE_TYPE_GOPHER_FILE_HTML = 12
INTERNET_HANDLE_TYPE_HTTP_REQUEST = 13
INTERNET_HANDLE_TYPE_FILE_REQUEST = 14
AUTH_FLAG_DISABLE_NEGOTIATE = 0x00000001
AUTH_FLAG_ENABLE_NEGOTIATE = 0x00000002
SECURITY_FLAG_SECURE = 0x00000001
SECURITY_FLAG_STRENGTH_WEAK = 0x10000000
SECURITY_FLAG_STRENGTH_MEDIUM = 0x40000000
SECURITY_FLAG_STRENGTH_STRONG = 0x20000000
SECURITY_FLAG_UNKNOWNBIT = -2147483648
SECURITY_FLAG_FORTEZZA = 0x08000000
SECURITY_FLAG_NORMALBITNESS = SECURITY_FLAG_STRENGTH_WEAK
SECURITY_FLAG_SSL = 0x00000002
SECURITY_FLAG_SSL3 = 0x00000004
SECURITY_FLAG_PCT = 0x00000008
SECURITY_FLAG_PCT4 = 0x00000010
SECURITY_FLAG_IETFSSL4 = 0x00000020
SECURITY_FLAG_40BIT = SECURITY_FLAG_STRENGTH_WEAK
SECURITY_FLAG_128BIT = SECURITY_FLAG_STRENGTH_STRONG
SECURITY_FLAG_56BIT = SECURITY_FLAG_STRENGTH_MEDIUM
SECURITY_FLAG_IGNORE_REVOCATION = 0x00000080
SECURITY_FLAG_IGNORE_UNKNOWN_CA = 0x00000100
SECURITY_FLAG_IGNORE_WRONG_USAGE = 0x00000200
SECURITY_FLAG_IGNORE_CERT_CN_INVALID = INTERNET_FLAG_IGNORE_CERT_CN_INVALID
SECURITY_FLAG_IGNORE_CERT_DATE_INVALID = INTERNET_FLAG_IGNORE_CERT_DATE_INVALID
SECURITY_FLAG_IGNORE_CERT_WRONG_USAGE = 0x00000200
SECURITY_FLAG_IGNORE_REDIRECT_TO_HTTPS = INTERNET_FLAG_IGNORE_REDIRECT_TO_HTTPS
SECURITY_FLAG_IGNORE_REDIRECT_TO_HTTP = INTERNET_FLAG_IGNORE_REDIRECT_TO_HTTP
SECURITY_SET_MASK = (
    SECURITY_FLAG_IGNORE_REVOCATION
    | SECURITY_FLAG_IGNORE_UNKNOWN_CA
    | SECURITY_FLAG_IGNORE_CERT_CN_INVALID
    | SECURITY_FLAG_IGNORE_CERT_DATE_INVALID
    | SECURITY_FLAG_IGNORE_WRONG_USAGE
)
AUTODIAL_MODE_NEVER = 1
AUTODIAL_MODE_ALWAYS = 2
AUTODIAL_MODE_NO_NETWORK_PRESENT = 4
INTERNET_STATUS_RESOLVING_NAME = 10
INTERNET_STATUS_NAME_RESOLVED = 11
INTERNET_STATUS_CONNECTING_TO_SERVER = 20
INTERNET_STATUS_CONNECTED_TO_SERVER = 21
INTERNET_STATUS_SENDING_REQUEST = 30
INTERNET_STATUS_REQUEST_SENT = 31
INTERNET_STATUS_RECEIVING_RESPONSE = 40
INTERNET_STATUS_RESPONSE_RECEIVED = 41
INTERNET_STATUS_CTL_RESPONSE_RECEIVED = 42
INTERNET_STATUS_PREFETCH = 43
INTERNET_STATUS_CLOSING_CONNECTION = 50
INTERNET_STATUS_CONNECTION_CLOSED = 51
INTERNET_STATUS_HANDLE_CREATED = 60
INTERNET_STATUS_HANDLE_CLOSING = 70
INTERNET_STATUS_DETECTING_PROXY = 80
INTERNET_STATUS_REQUEST_COMPLETE = 100
INTERNET_STATUS_REDIRECT = 110
INTERNET_STATUS_INTERMEDIATE_RESPONSE = 120
INTERNET_STATUS_USER_INPUT_REQUIRED = 140
INTERNET_STATUS_STATE_CHANGE = 200
INTERNET_STATUS_COOKIE_SENT = 320
INTERNET_STATUS_COOKIE_RECEIVED = 321
INTERNET_STATUS_PRIVACY_IMPACTED = 324
INTERNET_STATUS_P3P_HEADER = 325
INTERNET_STATUS_P3P_POLICYREF = 326
INTERNET_STATUS_COOKIE_HISTORY = 327
INTERNET_STATE_CONNECTED = 0x00000001
INTERNET_STATE_DISCONNECTED = 0x00000002
INTERNET_STATE_DISCONNECTED_BY_USER = 0x00000010
INTERNET_STATE_IDLE = 0x00000100
INTERNET_STATE_BUSY = 0x00000200
FTP_TRANSFER_TYPE_UNKNOWN = 0x00000000
FTP_TRANSFER_TYPE_ASCII = 0x00000001
FTP_TRANSFER_TYPE_BINARY = 0x00000002
FTP_TRANSFER_TYPE_MASK = FTP_TRANSFER_TYPE_ASCII | FTP_TRANSFER_TYPE_BINARY
MAX_GOPHER_DISPLAY_TEXT = 128
MAX_GOPHER_SELECTOR_TEXT = 256
MAX_GOPHER_HOST_NAME = INTERNET_MAX_HOST_NAME_LENGTH
MAX_GOPHER_LOCATOR_LENGTH = (
    1
    + MAX_GOPHER_DISPLAY_TEXT
    + 1
    + MAX_GOPHER_SELECTOR_TEXT
    + 1
    + MAX_GOPHER_HOST_NAME
    + 1
    + INTERNET_MAX_PORT_NUMBER_LENGTH
    + 1
    + 1
    + 2
)
GOPHER_TYPE_TEXT_FILE = 0x00000001
GOPHER_TYPE_DIRECTORY = 0x00000002
GOPHER_TYPE_CSO = 0x00000004
GOPHER_TYPE_ERROR = 0x00000008
GOPHER_TYPE_MAC_BINHEX = 0x00000010
GOPHER_TYPE_DOS_ARCHIVE = 0x00000020
GOPHER_TYPE_UNIX_UUENCODED = 0x00000040
GOPHER_TYPE_INDEX_SERVER = 0x00000080
GOPHER_TYPE_TELNET = 0x00000100
GOPHER_TYPE_BINARY = 0x00000200
GOPHER_TYPE_REDUNDANT = 0x00000400
GOPHER_TYPE_TN3270 = 0x00000800
GOPHER_TYPE_GIF = 0x00001000
GOPHER_TYPE_IMAGE = 0x00002000
GOPHER_TYPE_BITMAP = 0x00004000
GOPHER_TYPE_MOVIE = 0x00008000
GOPHER_TYPE_SOUND = 0x00010000
GOPHER_TYPE_HTML = 0x00020000
GOPHER_TYPE_PDF = 0x00040000
GOPHER_TYPE_CALENDAR = 0x00080000
GOPHER_TYPE_INLINE = 0x00100000
GOPHER_TYPE_UNKNOWN = 0x20000000
GOPHER_TYPE_ASK = 0x40000000
GOPHER_TYPE_GOPHER_PLUS = -2147483648
GOPHER_TYPE_FILE_MASK = (
    GOPHER_TYPE_TEXT_FILE
    | GOPHER_TYPE_MAC_BINHEX
    | GOPHER_TYPE_DOS_ARCHIVE
    | GOPHER_TYPE_UNIX_UUENCODED
    | GOPHER_TYPE_BINARY
    | GOPHER_TYPE_GIF
    | GOPHER_TYPE_IMAGE
    | GOPHER_TYPE_BITMAP
    | GOPHER_TYPE_MOVIE
    | GOPHER_TYPE_SOUND
    | GOPHER_TYPE_HTML
    | GOPHER_TYPE_PDF
    | GOPHER_TYPE_CALENDAR
    | GOPHER_TYPE_INLINE
)
MAX_GOPHER_CATEGORY_NAME = 128
MAX_GOPHER_ATTRIBUTE_NAME = 128
MIN_GOPHER_ATTRIBUTE_LENGTH = 256
GOPHER_ATTRIBUTE_ID_BASE = -1412641792
GOPHER_CATEGORY_ID_ALL = GOPHER_ATTRIBUTE_ID_BASE + 1
GOPHER_CATEGORY_ID_INFO = GOPHER_ATTRIBUTE_ID_BASE + 2
GOPHER_CATEGORY_ID_ADMIN = GOPHER_ATTRIBUTE_ID_BASE + 3
GOPHER_CATEGORY_ID_VIEWS = GOPHER_ATTRIBUTE_ID_BASE + 4
GOPHER_CATEGORY_ID_ABSTRACT = GOPHER_ATTRIBUTE_ID_BASE + 5
GOPHER_CATEGORY_ID_VERONICA = GOPHER_ATTRIBUTE_ID_BASE + 6
GOPHER_CATEGORY_ID_ASK = GOPHER_ATTRIBUTE_ID_BASE + 7
GOPHER_CATEGORY_ID_UNKNOWN = GOPHER_ATTRIBUTE_ID_BASE + 8
GOPHER_ATTRIBUTE_ID_ALL = GOPHER_ATTRIBUTE_ID_BASE + 9
GOPHER_ATTRIBUTE_ID_ADMIN = GOPHER_ATTRIBUTE_ID_BASE + 10
GOPHER_ATTRIBUTE_ID_MOD_DATE = GOPHER_ATTRIBUTE_ID_BASE + 11
GOPHER_ATTRIBUTE_ID_TTL = GOPHER_ATTRIBUTE_ID_BASE + 12
GOPHER_ATTRIBUTE_ID_SCORE = GOPHER_ATTRIBUTE_ID_BASE + 13
GOPHER_ATTRIBUTE_ID_RANGE = GOPHER_ATTRIBUTE_ID_BASE + 14
GOPHER_ATTRIBUTE_ID_SITE = GOPHER_ATTRIBUTE_ID_BASE + 15
GOPHER_ATTRIBUTE_ID_ORG = GOPHER_ATTRIBUTE_ID_BASE + 16
GOPHER_ATTRIBUTE_ID_LOCATION = GOPHER_ATTRIBUTE_ID_BASE + 17
GOPHER_ATTRIBUTE_ID_GEOG = GOPHER_ATTRIBUTE_ID_BASE + 18
GOPHER_ATTRIBUTE_ID_TIMEZONE = GOPHER_ATTRIBUTE_ID_BASE + 19
GOPHER_ATTRIBUTE_ID_PROVIDER = GOPHER_ATTRIBUTE_ID_BASE + 20
GOPHER_ATTRIBUTE_ID_VERSION = GOPHER_ATTRIBUTE_ID_BASE + 21
GOPHER_ATTRIBUTE_ID_ABSTRACT = GOPHER_ATTRIBUTE_ID_BASE + 22
GOPHER_ATTRIBUTE_ID_VIEW = GOPHER_ATTRIBUTE_ID_BASE + 23
GOPHER_ATTRIBUTE_ID_TREEWALK = GOPHER_ATTRIBUTE_ID_BASE + 24
GOPHER_ATTRIBUTE_ID_UNKNOWN = GOPHER_ATTRIBUTE_ID_BASE + 25
HTTP_MAJOR_VERSION = 1
HTTP_MINOR_VERSION = 0
HTTP_VERSIONA = "HTTP/1.0"
HTTP_VERSION = HTTP_VERSIONA
HTTP_QUERY_MIME_VERSION = 0
HTTP_QUERY_CONTENT_TYPE = 1
HTTP_QUERY_CONTENT_TRANSFER_ENCODING = 2
HTTP_QUERY_CONTENT_ID = 3
HTTP_QUERY_CONTENT_DESCRIPTION = 4
HTTP_QUERY_CONTENT_LENGTH = 5
HTTP_QUERY_CONTENT_LANGUAGE = 6
HTTP_QUERY_ALLOW = 7
HTTP_QUERY_PUBLIC = 8
HTTP_QUERY_DATE = 9
HTTP_QUERY_EXPIRES = 10
HTTP_QUERY_LAST_MODIFIED = 11
HTTP_QUERY_MESSAGE_ID = 12
HTTP_QUERY_URI = 13
HTTP_QUERY_DERIVED_FROM = 14
HTTP_QUERY_COST = 15
HTTP_QUERY_LINK = 16
HTTP_QUERY_PRAGMA = 17
HTTP_QUERY_VERSION = 18
HTTP_QUERY_STATUS_CODE = 19
HTTP_QUERY_STATUS_TEXT = 20
HTTP_QUERY_RAW_HEADERS = 21
HTTP_QUERY_RAW_HEADERS_CRLF = 22
HTTP_QUERY_CONNECTION = 23
HTTP_QUERY_ACCEPT = 24
HTTP_QUERY_ACCEPT_CHARSET = 25
HTTP_QUERY_ACCEPT_ENCODING = 26
HTTP_QUERY_ACCEPT_LANGUAGE = 27
HTTP_QUERY_AUTHORIZATION = 28
HTTP_QUERY_CONTENT_ENCODING = 29
HTTP_QUERY_FORWARDED = 30
HTTP_QUERY_FROM = 31
HTTP_QUERY_IF_MODIFIED_SINCE = 32
HTTP_QUERY_LOCATION = 33
HTTP_QUERY_ORIG_URI = 34
HTTP_QUERY_REFERER = 35
HTTP_QUERY_RETRY_AFTER = 36
HTTP_QUERY_SERVER = 37
HTTP_QUERY_TITLE = 38
HTTP_QUERY_USER_AGENT = 39
HTTP_QUERY_WWW_AUTHENTICATE = 40
HTTP_QUERY_PROXY_AUTHENTICATE = 41
HTTP_QUERY_ACCEPT_RANGES = 42
HTTP_QUERY_SET_COOKIE = 43
HTTP_QUERY_COOKIE = 44
HTTP_QUERY_REQUEST_METHOD = 45
HTTP_QUERY_REFRESH = 46
HTTP_QUERY_CONTENT_DISPOSITION = 47
HTTP_QUERY_AGE = 48
HTTP_QUERY_CACHE_CONTROL = 49
HTTP_QUERY_CONTENT_BASE = 50
HTTP_QUERY_CONTENT_LOCATION = 51
HTTP_QUERY_CONTENT_MD5 = 52
HTTP_QUERY_CONTENT_RANGE = 53
HTTP_QUERY_ETAG = 54
HTTP_QUERY_HOST = 55
HTTP_QUERY_IF_MATCH = 56
HTTP_QUERY_IF_NONE_MATCH = 57
HTTP_QUERY_IF_RANGE = 58
HTTP_QUERY_IF_UNMODIFIED_SINCE = 59
HTTP_QUERY_MAX_FORWARDS = 60
HTTP_QUERY_PROXY_AUTHORIZATION = 61
HTTP_QUERY_RANGE = 62
HTTP_QUERY_TRANSFER_ENCODING = 63
HTTP_QUERY_UPGRADE = 64
HTTP_QUERY_VARY = 65
HTTP_QUERY_VIA = 66
HTTP_QUERY_WARNING = 67
HTTP_QUERY_EXPECT = 68
HTTP_QUERY_PROXY_CONNECTION = 69
HTTP_QUERY_UNLESS_MODIFIED_SINCE = 70
HTTP_QUERY_ECHO_REQUEST = 71
HTTP_QUERY_ECHO_REPLY = 72
HTTP_QUERY_ECHO_HEADERS = 73
HTTP_QUERY_ECHO_HEADERS_CRLF = 74
HTTP_QUERY_PROXY_SUPPORT = 75
HTTP_QUERY_AUTHENTICATION_INFO = 76
HTTP_QUERY_PASSPORT_URLS = 77
HTTP_QUERY_PASSPORT_CONFIG = 78
HTTP_QUERY_MAX = 78
HTTP_QUERY_CUSTOM = 65535
HTTP_QUERY_FLAG_REQUEST_HEADERS = -2147483648
HTTP_QUERY_FLAG_SYSTEMTIME = 0x40000000
HTTP_QUERY_FLAG_NUMBER = 0x20000000
HTTP_QUERY_FLAG_COALESCE = 0x10000000
HTTP_QUERY_MODIFIER_FLAGS_MASK = (
    HTTP_QUERY_FLAG_REQUEST_HEADERS
    | HTTP_QUERY_FLAG_SYSTEMTIME
    | HTTP_QUERY_FLAG_NUMBER
    | HTTP_QUERY_FLAG_COALESCE
)
HTTP_QUERY_HEADER_MASK = ~HTTP_QUERY_MODIFIER_FLAGS_MASK
HTTP_STATUS_CONTINUE = 100
HTTP_STATUS_SWITCH_PROTOCOLS = 101
HTTP_STATUS_OK = 200
HTTP_STATUS_CREATED = 201
HTTP_STATUS_ACCEPTED = 202
HTTP_STATUS_PARTIAL = 203
HTTP_STATUS_NO_CONTENT = 204
HTTP_STATUS_RESET_CONTENT = 205
HTTP_STATUS_PARTIAL_CONTENT = 206
HTTP_STATUS_WEBDAV_MULTI_STATUS = 207
HTTP_STATUS_AMBIGUOUS = 300
HTTP_STATUS_MOVED = 301
HTTP_STATUS_REDIRECT = 302
HTTP_STATUS_REDIRECT_METHOD = 303
HTTP_STATUS_NOT_MODIFIED = 304
HTTP_STATUS_USE_PROXY = 305
HTTP_STATUS_REDIRECT_KEEP_VERB = 307
HTTP_STATUS_BAD_REQUEST = 400
HTTP_STATUS_DENIED = 401
HTTP_STATUS_PAYMENT_REQ = 402
HTTP_STATUS_FORBIDDEN = 403
HTTP_STATUS_NOT_FOUND = 404
HTTP_STATUS_BAD_METHOD = 405
HTTP_STATUS_NONE_ACCEPTABLE = 406
HTTP_STATUS_PROXY_AUTH_REQ = 407
HTTP_STATUS_REQUEST_TIMEOUT = 408
HTTP_STATUS_CONFLICT = 409
HTTP_STATUS_GONE = 410
HTTP_STATUS_LENGTH_REQUIRED = 411
HTTP_STATUS_PRECOND_FAILED = 412
HTTP_STATUS_REQUEST_TOO_LARGE = 413
HTTP_STATUS_URI_TOO_LONG = 414
HTTP_STATUS_UNSUPPORTED_MEDIA = 415
HTTP_STATUS_RETRY_WITH = 449
HTTP_STATUS_SERVER_ERROR = 500
HTTP_STATUS_NOT_SUPPORTED = 501
HTTP_STATUS_BAD_GATEWAY = 502
HTTP_STATUS_SERVICE_UNAVAIL = 503
HTTP_STATUS_GATEWAY_TIMEOUT = 504
HTTP_STATUS_VERSION_NOT_SUP = 505
HTTP_STATUS_FIRST = HTTP_STATUS_CONTINUE
HTTP_STATUS_LAST = HTTP_STATUS_VERSION_NOT_SUP
HTTP_ADDREQ_INDEX_MASK = 0x0000FFFF
HTTP_ADDREQ_FLAGS_MASK = -65536
HTTP_ADDREQ_FLAG_ADD_IF_NEW = 0x10000000
HTTP_ADDREQ_FLAG_ADD = 0x20000000
HTTP_ADDREQ_FLAG_COALESCE_WITH_COMMA = 0x40000000
HTTP_ADDREQ_FLAG_COALESCE_WITH_SEMICOLON = 0x01000000
HTTP_ADDREQ_FLAG_COALESCE = HTTP_ADDREQ_FLAG_COALESCE_WITH_COMMA
HTTP_ADDREQ_FLAG_REPLACE = -2147483648
HSR_ASYNC = WININET_API_FLAG_ASYNC
HSR_SYNC = WININET_API_FLAG_SYNC
HSR_USE_CONTEXT = WININET_API_FLAG_USE_CONTEXT
HSR_INITIATE = 0x00000008
HSR_DOWNLOAD = 0x00000010
HSR_CHUNKED = 0x00000020
INTERNET_COOKIE_IS_SECURE = 0x01
INTERNET_COOKIE_IS_SESSION = 0x02
INTERNET_COOKIE_THIRD_PARTY = 0x10
INTERNET_COOKIE_PROMPT_REQUIRED = 0x20
INTERNET_COOKIE_EVALUATE_P3P = 0x40
INTERNET_COOKIE_APPLY_P3P = 0x80
INTERNET_COOKIE_P3P_ENABLED = 0x100
INTERNET_COOKIE_IS_RESTRICTED = 0x200
INTERNET_COOKIE_IE6 = 0x400
INTERNET_COOKIE_IS_LEGACY = 0x800
FLAG_ICC_FORCE_CONNECTION = 0x00000001
FLAGS_ERROR_UI_FILTER_FOR_ERRORS = 0x01
FLAGS_ERROR_UI_FLAGS_CHANGE_OPTIONS = 0x02
FLAGS_ERROR_UI_FLAGS_GENERATE_DATA = 0x04
FLAGS_ERROR_UI_FLAGS_NO_UI = 0x08
FLAGS_ERROR_UI_SERIALIZE_DIALOGS = 0x10
INTERNET_ERROR_BASE = 12000
ERROR_INTERNET_OUT_OF_HANDLES = INTERNET_ERROR_BASE + 1
ERROR_INTERNET_TIMEOUT = INTERNET_ERROR_BASE + 2
ERROR_INTERNET_EXTENDED_ERROR = INTERNET_ERROR_BASE + 3
ERROR_INTERNET_INTERNAL_ERROR = INTERNET_ERROR_BASE + 4
ERROR_INTERNET_INVALID_URL = INTERNET_ERROR_BASE + 5
ERROR_INTERNET_UNRECOGNIZED_SCHEME = INTERNET_ERROR_BASE + 6
ERROR_INTERNET_NAME_NOT_RESOLVED = INTERNET_ERROR_BASE + 7
ERROR_INTERNET_PROTOCOL_NOT_FOUND = INTERNET_ERROR_BASE + 8
ERROR_INTERNET_INVALID_OPTION = INTERNET_ERROR_BASE + 9
ERROR_INTERNET_BAD_OPTION_LENGTH = INTERNET_ERROR_BASE + 10
ERROR_INTERNET_OPTION_NOT_SETTABLE = INTERNET_ERROR_BASE + 11
ERROR_INTERNET_SHUTDOWN = INTERNET_ERROR_BASE + 12
ERROR_INTERNET_INCORRECT_USER_NAME = INTERNET_ERROR_BASE + 13
ERROR_INTERNET_INCORRECT_PASSWORD = INTERNET_ERROR_BASE + 14
ERROR_INTERNET_LOGIN_FAILURE = INTERNET_ERROR_BASE + 15
ERROR_INTERNET_INVALID_OPERATION = INTERNET_ERROR_BASE + 16
ERROR_INTERNET_OPERATION_CANCELLED = INTERNET_ERROR_BASE + 17
ERROR_INTERNET_INCORRECT_HANDLE_TYPE = INTERNET_ERROR_BASE + 18
ERROR_INTERNET_INCORRECT_HANDLE_STATE = INTERNET_ERROR_BASE + 19
ERROR_INTERNET_NOT_PROXY_REQUEST = INTERNET_ERROR_BASE + 20
ERROR_INTERNET_REGISTRY_VALUE_NOT_FOUND = INTERNET_ERROR_BASE + 21
ERROR_INTERNET_BAD_REGISTRY_PARAMETER = INTERNET_ERROR_BASE + 22
ERROR_INTERNET_NO_DIRECT_ACCESS = INTERNET_ERROR_BASE + 23
ERROR_INTERNET_NO_CONTEXT = INTERNET_ERROR_BASE + 24
ERROR_INTERNET_NO_CALLBACK = INTERNET_ERROR_BASE + 25
ERROR_INTERNET_REQUEST_PENDING = INTERNET_ERROR_BASE + 26
ERROR_INTERNET_INCORRECT_FORMAT = INTERNET_ERROR_BASE + 27
ERROR_INTERNET_ITEM_NOT_FOUND = INTERNET_ERROR_BASE + 28
ERROR_INTERNET_CANNOT_CONNECT = INTERNET_ERROR_BASE + 29
ERROR_INTERNET_CONNECTION_ABORTED = INTERNET_ERROR_BASE + 30
ERROR_INTERNET_CONNECTION_RESET = INTERNET_ERROR_BASE + 31
ERROR_INTERNET_FORCE_RETRY = INTERNET_ERROR_BASE + 32
ERROR_INTERNET_INVALID_PROXY_REQUEST = INTERNET_ERROR_BASE + 33
ERROR_INTERNET_NEED_UI = INTERNET_ERROR_BASE + 34
ERROR_INTERNET_HANDLE_EXISTS = INTERNET_ERROR_BASE + 36
ERROR_INTERNET_SEC_CERT_DATE_INVALID = INTERNET_ERROR_BASE + 37
ERROR_INTERNET_SEC_CERT_CN_INVALID = INTERNET_ERROR_BASE + 38
ERROR_INTERNET_HTTP_TO_HTTPS_ON_REDIR = INTERNET_ERROR_BASE + 39
ERROR_INTERNET_HTTPS_TO_HTTP_ON_REDIR = INTERNET_ERROR_BASE + 40
ERROR_INTERNET_MIXED_SECURITY = INTERNET_ERROR_BASE + 41
ERROR_INTERNET_CHG_POST_IS_NON_SECURE = INTERNET_ERROR_BASE + 42
ERROR_INTERNET_POST_IS_NON_SECURE = INTERNET_ERROR_BASE + 43
ERROR_INTERNET_CLIENT_AUTH_CERT_NEEDED = INTERNET_ERROR_BASE + 44
ERROR_INTERNET_INVALID_CA = INTERNET_ERROR_BASE + 45
ERROR_INTERNET_CLIENT_AUTH_NOT_SETUP = INTERNET_ERROR_BASE + 46
ERROR_INTERNET_ASYNC_THREAD_FAILED = INTERNET_ERROR_BASE + 47
ERROR_INTERNET_REDIRECT_SCHEME_CHANGE = INTERNET_ERROR_BASE + 48
ERROR_INTERNET_DIALOG_PENDING = INTERNET_ERROR_BASE + 49
ERROR_INTERNET_RETRY_DIALOG = INTERNET_ERROR_BASE + 50
ERROR_INTERNET_HTTPS_HTTP_SUBMIT_REDIR = INTERNET_ERROR_BASE + 52
ERROR_INTERNET_INSERT_CDROM = INTERNET_ERROR_BASE + 53
ERROR_INTERNET_FORTEZZA_LOGIN_NEEDED = INTERNET_ERROR_BASE + 54
ERROR_INTERNET_SEC_CERT_ERRORS = INTERNET_ERROR_BASE + 55
ERROR_INTERNET_SEC_CERT_NO_REV = INTERNET_ERROR_BASE + 56
ERROR_INTERNET_SEC_CERT_REV_FAILED = INTERNET_ERROR_BASE + 57
ERROR_FTP_TRANSFER_IN_PROGRESS = INTERNET_ERROR_BASE + 110
ERROR_FTP_DROPPED = INTERNET_ERROR_BASE + 111
ERROR_FTP_NO_PASSIVE_MODE = INTERNET_ERROR_BASE + 112
ERROR_GOPHER_PROTOCOL_ERROR = INTERNET_ERROR_BASE + 130
ERROR_GOPHER_NOT_FILE = INTERNET_ERROR_BASE + 131
ERROR_GOPHER_DATA_ERROR = INTERNET_ERROR_BASE + 132
ERROR_GOPHER_END_OF_DATA = INTERNET_ERROR_BASE + 133
ERROR_GOPHER_INVALID_LOCATOR = INTERNET_ERROR_BASE + 134
ERROR_GOPHER_INCORRECT_LOCATOR_TYPE = INTERNET_ERROR_BASE + 135
ERROR_GOPHER_NOT_GOPHER_PLUS = INTERNET_ERROR_BASE + 136
ERROR_GOPHER_ATTRIBUTE_NOT_FOUND = INTERNET_ERROR_BASE + 137
ERROR_GOPHER_UNKNOWN_LOCATOR = INTERNET_ERROR_BASE + 138
ERROR_HTTP_HEADER_NOT_FOUND = INTERNET_ERROR_BASE + 150
ERROR_HTTP_DOWNLEVEL_SERVER = INTERNET_ERROR_BASE + 151
ERROR_HTTP_INVALID_SERVER_RESPONSE = INTERNET_ERROR_BASE + 152
ERROR_HTTP_INVALID_HEADER = INTERNET_ERROR_BASE + 153
ERROR_HTTP_INVALID_QUERY_REQUEST = INTERNET_ERROR_BASE + 154
ERROR_HTTP_HEADER_ALREADY_EXISTS = INTERNET_ERROR_BASE + 155
ERROR_HTTP_REDIRECT_FAILED = INTERNET_ERROR_BASE + 156
ERROR_HTTP_NOT_REDIRECTED = INTERNET_ERROR_BASE + 160
ERROR_HTTP_COOKIE_NEEDS_CONFIRMATION = INTERNET_ERROR_BASE + 161
ERROR_HTTP_COOKIE_DECLINED = INTERNET_ERROR_BASE + 162
ERROR_HTTP_REDIRECT_NEEDS_CONFIRMATION = INTERNET_ERROR_BASE + 168
ERROR_INTERNET_SECURITY_CHANNEL_ERROR = INTERNET_ERROR_BASE + 157
ERROR_INTERNET_UNABLE_TO_CACHE_FILE = INTERNET_ERROR_BASE + 158
ERROR_INTERNET_TCPIP_NOT_INSTALLED = INTERNET_ERROR_BASE + 159
ERROR_INTERNET_DISCONNECTED = INTERNET_ERROR_BASE + 163
ERROR_INTERNET_SERVER_UNREACHABLE = INTERNET_ERROR_BASE + 164
ERROR_INTERNET_PROXY_SERVER_UNREACHABLE = INTERNET_ERROR_BASE + 165
ERROR_INTERNET_BAD_AUTO_PROXY_SCRIPT = INTERNET_ERROR_BASE + 166
ERROR_INTERNET_UNABLE_TO_DOWNLOAD_SCRIPT = INTERNET_ERROR_BASE + 167
ERROR_INTERNET_SEC_INVALID_CERT = INTERNET_ERROR_BASE + 169
ERROR_INTERNET_SEC_CERT_REVOKED = INTERNET_ERROR_BASE + 170
ERROR_INTERNET_FAILED_DUETOSECURITYCHECK = INTERNET_ERROR_BASE + 171
ERROR_INTERNET_NOT_INITIALIZED = INTERNET_ERROR_BASE + 172
ERROR_INTERNET_NEED_MSN_SSPI_PKG = INTERNET_ERROR_BASE + 173
ERROR_INTERNET_LOGIN_FAILURE_DISPLAY_ENTITY_BODY = INTERNET_ERROR_BASE + 174
INTERNET_ERROR_LAST = ERROR_INTERNET_LOGIN_FAILURE_DISPLAY_ENTITY_BODY
NORMAL_CACHE_ENTRY = 0x00000001
STICKY_CACHE_ENTRY = 0x00000004
EDITED_CACHE_ENTRY = 0x00000008
TRACK_OFFLINE_CACHE_ENTRY = 0x00000010
TRACK_ONLINE_CACHE_ENTRY = 0x00000020
SPARSE_CACHE_ENTRY = 0x00010000
COOKIE_CACHE_ENTRY = 0x00100000
URLHISTORY_CACHE_ENTRY = 0x00200000
URLCACHE_FIND_DEFAULT_FILTER = (
    NORMAL_CACHE_ENTRY
    | COOKIE_CACHE_ENTRY
    | URLHISTORY_CACHE_ENTRY
    | TRACK_OFFLINE_CACHE_ENTRY
    | TRACK_ONLINE_CACHE_ENTRY
    | STICKY_CACHE_ENTRY
)
CACHEGROUP_ATTRIBUTE_GET_ALL = -1
CACHEGROUP_ATTRIBUTE_BASIC = 0x00000001
CACHEGROUP_ATTRIBUTE_FLAG = 0x00000002
CACHEGROUP_ATTRIBUTE_TYPE = 0x00000004
CACHEGROUP_ATTRIBUTE_QUOTA = 0x00000008
CACHEGROUP_ATTRIBUTE_GROUPNAME = 0x00000010
CACHEGROUP_ATTRIBUTE_STORAGE = 0x00000020
CACHEGROUP_FLAG_NONPURGEABLE = 0x00000001
CACHEGROUP_FLAG_GIDONLY = 0x00000004
CACHEGROUP_FLAG_FLUSHURL_ONDELETE = 0x00000002
CACHEGROUP_SEARCH_ALL = 0x00000000
CACHEGROUP_SEARCH_BYURL = 0x00000001
CACHEGROUP_TYPE_INVALID = 0x00000001
CACHEGROUP_READWRITE_MASK = (
    CACHEGROUP_ATTRIBUTE_TYPE
    | CACHEGROUP_ATTRIBUTE_QUOTA
    | CACHEGROUP_ATTRIBUTE_GROUPNAME
    | CACHEGROUP_ATTRIBUTE_STORAGE
)
GROUPNAME_MAX_LENGTH = 120
GROUP_OWNER_STORAGE_SIZE = 4
CACHE_ENTRY_ATTRIBUTE_FC = 0x00000004
CACHE_ENTRY_HITRATE_FC = 0x00000010
CACHE_ENTRY_MODTIME_FC = 0x00000040
CACHE_ENTRY_EXPTIME_FC = 0x00000080
CACHE_ENTRY_ACCTIME_FC = 0x00000100
CACHE_ENTRY_SYNCTIME_FC = 0x00000200
CACHE_ENTRY_HEADERINFO_FC = 0x00000400
CACHE_ENTRY_EXEMPT_DELTA_FC = 0x00000800
INTERNET_CACHE_GROUP_ADD = 0
INTERNET_CACHE_GROUP_REMOVE = 1
INTERNET_DIAL_FORCE_PROMPT = 0x2000
INTERNET_DIAL_SHOW_OFFLINE = 0x4000
INTERNET_DIAL_UNATTENDED = 0x8000
INTERENT_GOONLINE_REFRESH = 0x00000001
INTERENT_GOONLINE_MASK = 0x00000001
INTERNET_AUTODIAL_FORCE_ONLINE = 1
INTERNET_AUTODIAL_FORCE_UNATTENDED = 2
INTERNET_AUTODIAL_FAILIFSECURITYCHECK = 4
INTERNET_AUTODIAL_OVERRIDE_NET_PRESENT = 8
INTERNET_AUTODIAL_FLAGS_MASK = (
    INTERNET_AUTODIAL_FORCE_ONLINE
    | INTERNET_AUTODIAL_FORCE_UNATTENDED
    | INTERNET_AUTODIAL_FAILIFSECURITYCHECK
    | INTERNET_AUTODIAL_OVERRIDE_NET_PRESENT
)
PROXY_AUTO_DETECT_TYPE_DHCP = 1
PROXY_AUTO_DETECT_TYPE_DNS_A = 2
INTERNET_CONNECTION_MODEM = 0x01
INTERNET_CONNECTION_LAN = 0x02
INTERNET_CONNECTION_PROXY = 0x04
INTERNET_CONNECTION_MODEM_BUSY = 0x08
INTERNET_RAS_INSTALLED = 0x10
INTERNET_CONNECTION_OFFLINE = 0x20
INTERNET_CONNECTION_CONFIGURED = 0x40
INTERNET_CUSTOMDIAL_CONNECT = 0
INTERNET_CUSTOMDIAL_UNATTENDED = 1
INTERNET_CUSTOMDIAL_DISCONNECT = 2
INTERNET_CUSTOMDIAL_SHOWOFFLINE = 4
INTERNET_CUSTOMDIAL_SAFE_FOR_UNATTENDED = 1
INTERNET_CUSTOMDIAL_WILL_SUPPLY_STATE = 2
INTERNET_CUSTOMDIAL_CAN_HANGUP = 4
INTERNET_DIALSTATE_DISCONNECTED = 1
INTERNET_IDENTITY_FLAG_PRIVATE_CACHE = 0x01
INTERNET_IDENTITY_FLAG_SHARED_CACHE = 0x02
INTERNET_IDENTITY_FLAG_CLEAR_DATA = 0x04
INTERNET_IDENTITY_FLAG_CLEAR_COOKIES = 0x08
INTERNET_IDENTITY_FLAG_CLEAR_HISTORY = 0x10
INTERNET_IDENTITY_FLAG_CLEAR_CONTENT = 0x20
INTERNET_SUPPRESS_RESET_ALL = 0x00
INTERNET_SUPPRESS_COOKIE_POLICY = 0x01
INTERNET_SUPPRESS_COOKIE_POLICY_RESET = 0x02
PRIVACY_TEMPLATE_NO_COOKIES = 0
PRIVACY_TEMPLATE_HIGH = 1
PRIVACY_TEMPLATE_MEDIUM_HIGH = 2
PRIVACY_TEMPLATE_MEDIUM = 3
PRIVACY_TEMPLATE_MEDIUM_LOW = 4
PRIVACY_TEMPLATE_LOW = 5
PRIVACY_TEMPLATE_CUSTOM = 100
PRIVACY_TEMPLATE_ADVANCED = 101
PRIVACY_TEMPLATE_MAX = PRIVACY_TEMPLATE_LOW
PRIVACY_TYPE_FIRST_PARTY = 0
PRIVACY_TYPE_THIRD_PARTY = 1

# Generated by h2py from winhttp.h
WINHTTP_FLAG_ASYNC = 0x10000000
WINHTTP_FLAG_SECURE = 0x00800000
WINHTTP_FLAG_ESCAPE_PERCENT = 0x00000004
WINHTTP_FLAG_NULL_CODEPAGE = 0x00000008
WINHTTP_FLAG_BYPASS_PROXY_CACHE = 0x00000100
WINHTTP_FLAG_REFRESH = WINHTTP_FLAG_BYPASS_PROXY_CACHE
WINHTTP_FLAG_ESCAPE_DISABLE = 0x00000040
WINHTTP_FLAG_ESCAPE_DISABLE_QUERY = 0x00000080
INTERNET_SCHEME_HTTP = 1
INTERNET_SCHEME_HTTPS = 2
WINHTTP_AUTOPROXY_AUTO_DETECT = 0x00000001
WINHTTP_AUTOPROXY_CONFIG_URL = 0x00000002
WINHTTP_AUTOPROXY_RUN_INPROCESS = 0x00010000
WINHTTP_AUTOPROXY_RUN_OUTPROCESS_ONLY = 0x00020000
WINHTTP_AUTO_DETECT_TYPE_DHCP = 0x00000001
WINHTTP_AUTO_DETECT_TYPE_DNS_A = 0x00000002
WINHTTP_TIME_FORMAT_BUFSIZE = 62
WINHTTP_ACCESS_TYPE_DEFAULT_PROXY = 0
WINHTTP_ACCESS_TYPE_NO_PROXY = 1
WINHTTP_ACCESS_TYPE_NAMED_PROXY = 3
WINHTTP_OPTION_CALLBACK = 1
WINHTTP_OPTION_RESOLVE_TIMEOUT = 2
WINHTTP_OPTION_CONNECT_TIMEOUT = 3
WINHTTP_OPTION_CONNECT_RETRIES = 4
WINHTTP_OPTION_SEND_TIMEOUT = 5
WINHTTP_OPTION_RECEIVE_TIMEOUT = 6
WINHTTP_OPTION_RECEIVE_RESPONSE_TIMEOUT = 7
WINHTTP_OPTION_HANDLE_TYPE = 9
WINHTTP_OPTION_READ_BUFFER_SIZE = 12
WINHTTP_OPTION_WRITE_BUFFER_SIZE = 13
WINHTTP_OPTION_PARENT_HANDLE = 21
WINHTTP_OPTION_EXTENDED_ERROR = 24
WINHTTP_OPTION_SECURITY_FLAGS = 31
WINHTTP_OPTION_SECURITY_CERTIFICATE_STRUCT = 32
WINHTTP_OPTION_URL = 34
WINHTTP_OPTION_SECURITY_KEY_BITNESS = 36
WINHTTP_OPTION_PROXY = 38
WINHTTP_OPTION_USER_AGENT = 41
WINHTTP_OPTION_CONTEXT_VALUE = 45
WINHTTP_OPTION_CLIENT_CERT_CONTEXT = 47
WINHTTP_OPTION_REQUEST_PRIORITY = 58
WINHTTP_OPTION_HTTP_VERSION = 59
WINHTTP_OPTION_DISABLE_FEATURE = 63
WINHTTP_OPTION_CODEPAGE = 68
WINHTTP_OPTION_MAX_CONNS_PER_SERVER = 73
WINHTTP_OPTION_MAX_CONNS_PER_1_0_SERVER = 74
WINHTTP_OPTION_AUTOLOGON_POLICY = 77
WINHTTP_OPTION_SERVER_CERT_CONTEXT = 78
WINHTTP_OPTION_ENABLE_FEATURE = 79
WINHTTP_OPTION_WORKER_THREAD_COUNT = 80
WINHTTP_OPTION_PASSPORT_COBRANDING_TEXT = 81
WINHTTP_OPTION_PASSPORT_COBRANDING_URL = 82
WINHTTP_OPTION_CONFIGURE_PASSPORT_AUTH = 83
WINHTTP_OPTION_SECURE_PROTOCOLS = 84
WINHTTP_OPTION_ENABLETRACING = 85
WINHTTP_OPTION_PASSPORT_SIGN_OUT = 86
WINHTTP_OPTION_PASSPORT_RETURN_URL = 87
WINHTTP_OPTION_REDIRECT_POLICY = 88
WINHTTP_OPTION_MAX_HTTP_AUTOMATIC_REDIRECTS = 89
WINHTTP_OPTION_MAX_HTTP_STATUS_CONTINUE = 90
WINHTTP_OPTION_MAX_RESPONSE_HEADER_SIZE = 91
WINHTTP_OPTION_MAX_RESPONSE_DRAIN_SIZE = 92
WINHTTP_OPTION_CONNECTION_INFO = 93
WINHTTP_OPTION_CLIENT_CERT_ISSUER_LIST = 94
WINHTTP_OPTION_SPN = 96
WINHTTP_OPTION_GLOBAL_PROXY_CREDS = 97
WINHTTP_OPTION_GLOBAL_SERVER_CREDS = 98
WINHTTP_OPTION_UNLOAD_NOTIFY_EVENT = 99
WINHTTP_OPTION_REJECT_USERPWD_IN_URL = 100
WINHTTP_OPTION_USE_GLOBAL_SERVER_CREDENTIALS = 101
WINHTTP_LAST_OPTION = WINHTTP_OPTION_USE_GLOBAL_SERVER_CREDENTIALS
WINHTTP_OPTION_USERNAME = 0x1000
WINHTTP_OPTION_PASSWORD = 0x1001
WINHTTP_OPTION_PROXY_USERNAME = 0x1002
WINHTTP_OPTION_PROXY_PASSWORD = 0x1003
WINHTTP_CONNS_PER_SERVER_UNLIMITED = -1
WINHTTP_AUTOLOGON_SECURITY_LEVEL_MEDIUM = 0
WINHTTP_AUTOLOGON_SECURITY_LEVEL_LOW = 1
WINHTTP_AUTOLOGON_SECURITY_LEVEL_HIGH = 2
WINHTTP_AUTOLOGON_SECURITY_LEVEL_DEFAULT = WINHTTP_AUTOLOGON_SECURITY_LEVEL_MEDIUM
WINHTTP_OPTION_REDIRECT_POLICY_NEVER = 0
WINHTTP_OPTION_REDIRECT_POLICY_DISALLOW_HTTPS_TO_HTTP = 1
WINHTTP_OPTION_REDIRECT_POLICY_ALWAYS = 2
WINHTTP_OPTION_REDIRECT_POLICY_LAST = WINHTTP_OPTION_REDIRECT_POLICY_ALWAYS
WINHTTP_OPTION_REDIRECT_POLICY_DEFAULT = (
    WINHTTP_OPTION_REDIRECT_POLICY_DISALLOW_HTTPS_TO_HTTP
)
WINHTTP_DISABLE_PASSPORT_AUTH = 0x00000000
WINHTTP_ENABLE_PASSPORT_AUTH = 0x10000000
WINHTTP_DISABLE_PASSPORT_KEYRING = 0x20000000
WINHTTP_ENABLE_PASSPORT_KEYRING = 0x40000000
WINHTTP_DISABLE_COOKIES = 0x00000001
WINHTTP_DISABLE_REDIRECTS = 0x00000002
WINHTTP_DISABLE_AUTHENTICATION = 0x00000004
WINHTTP_DISABLE_KEEP_ALIVE = 0x00000008
WINHTTP_ENABLE_SSL_REVOCATION = 0x00000001
WINHTTP_ENABLE_SSL_REVERT_IMPERSONATION = 0x00000002
WINHTTP_DISABLE_SPN_SERVER_PORT = 0x00000000
WINHTTP_ENABLE_SPN_SERVER_PORT = 0x00000001
WINHTTP_OPTION_SPN_MASK = WINHTTP_ENABLE_SPN_SERVER_PORT
WINHTTP_HANDLE_TYPE_SESSION = 1
WINHTTP_HANDLE_TYPE_CONNECT = 2
WINHTTP_HANDLE_TYPE_REQUEST = 3
WINHTTP_AUTH_SCHEME_BASIC = 0x00000001
WINHTTP_AUTH_SCHEME_NTLM = 0x00000002
WINHTTP_AUTH_SCHEME_PASSPORT = 0x00000004
WINHTTP_AUTH_SCHEME_DIGEST = 0x00000008
WINHTTP_AUTH_SCHEME_NEGOTIATE = 0x00000010
WINHTTP_AUTH_TARGET_SERVER = 0x00000000
WINHTTP_AUTH_TARGET_PROXY = 0x00000001
WINHTTP_CALLBACK_STATUS_FLAG_CERT_REV_FAILED = 0x00000001
WINHTTP_CALLBACK_STATUS_FLAG_INVALID_CERT = 0x00000002
WINHTTP_CALLBACK_STATUS_FLAG_CERT_REVOKED = 0x00000004
WINHTTP_CALLBACK_STATUS_FLAG_INVALID_CA = 0x00000008
WINHTTP_CALLBACK_STATUS_FLAG_CERT_CN_INVALID = 0x00000010
WINHTTP_CALLBACK_STATUS_FLAG_CERT_DATE_INVALID = 0x00000020
WINHTTP_CALLBACK_STATUS_FLAG_CERT_WRONG_USAGE = 0x00000040
WINHTTP_CALLBACK_STATUS_FLAG_SECURITY_CHANNEL_ERROR = -2147483648
WINHTTP_FLAG_SECURE_PROTOCOL_SSL2 = 0x00000008
WINHTTP_FLAG_SECURE_PROTOCOL_SSL3 = 0x00000020
WINHTTP_FLAG_SECURE_PROTOCOL_TLS1 = 0x00000080
WINHTTP_FLAG_SECURE_PROTOCOL_ALL = (
    WINHTTP_FLAG_SECURE_PROTOCOL_SSL2
    | WINHTTP_FLAG_SECURE_PROTOCOL_SSL3
    | WINHTTP_FLAG_SECURE_PROTOCOL_TLS1
)
WINHTTP_CALLBACK_STATUS_RESOLVING_NAME = 0x00000001
WINHTTP_CALLBACK_STATUS_NAME_RESOLVED = 0x00000002
WINHTTP_CALLBACK_STATUS_CONNECTING_TO_SERVER = 0x00000004
WINHTTP_CALLBACK_STATUS_CONNECTED_TO_SERVER = 0x00000008
WINHTTP_CALLBACK_STATUS_SENDING_REQUEST = 0x00000010
WINHTTP_CALLBACK_STATUS_REQUEST_SENT = 0x00000020
WINHTTP_CALLBACK_STATUS_RECEIVING_RESPONSE = 0x00000040
WINHTTP_CALLBACK_STATUS_RESPONSE_RECEIVED = 0x00000080
WINHTTP_CALLBACK_STATUS_CLOSING_CONNECTION = 0x00000100
WINHTTP_CALLBACK_STATUS_CONNECTION_CLOSED = 0x00000200
WINHTTP_CALLBACK_STATUS_HANDLE_CREATED = 0x00000400
WINHTTP_CALLBACK_STATUS_HANDLE_CLOSING = 0x00000800
WINHTTP_CALLBACK_STATUS_DETECTING_PROXY = 0x00001000
WINHTTP_CALLBACK_STATUS_REDIRECT = 0x00004000
WINHTTP_CALLBACK_STATUS_INTERMEDIATE_RESPONSE = 0x00008000
WINHTTP_CALLBACK_STATUS_SECURE_FAILURE = 0x00010000
WINHTTP_CALLBACK_STATUS_HEADERS_AVAILABLE = 0x00020000
WINHTTP_CALLBACK_STATUS_DATA_AVAILABLE = 0x00040000
WINHTTP_CALLBACK_STATUS_READ_COMPLETE = 0x00080000
WINHTTP_CALLBACK_STATUS_WRITE_COMPLETE = 0x00100000
WINHTTP_CALLBACK_STATUS_REQUEST_ERROR = 0x00200000
WINHTTP_CALLBACK_STATUS_SENDREQUEST_COMPLETE = 0x00400000
API_RECEIVE_RESPONSE = 1
API_QUERY_DATA_AVAILABLE = 2
API_READ_DATA = 3
API_WRITE_DATA = 4
API_SEND_REQUEST = 5
WINHTTP_CALLBACK_FLAG_RESOLVE_NAME = (
    WINHTTP_CALLBACK_STATUS_RESOLVING_NAME | WINHTTP_CALLBACK_STATUS_NAME_RESOLVED
)
WINHTTP_CALLBACK_FLAG_CONNECT_TO_SERVER = (
    WINHTTP_CALLBACK_STATUS_CONNECTING_TO_SERVER
    | WINHTTP_CALLBACK_STATUS_CONNECTED_TO_SERVER
)
WINHTTP_CALLBACK_FLAG_SEND_REQUEST = (
    WINHTTP_CALLBACK_STATUS_SENDING_REQUEST | WINHTTP_CALLBACK_STATUS_REQUEST_SENT
)
WINHTTP_CALLBACK_FLAG_RECEIVE_RESPONSE = (
    WINHTTP_CALLBACK_STATUS_RECEIVING_RESPONSE
    | WINHTTP_CALLBACK_STATUS_RESPONSE_RECEIVED
)
WINHTTP_CALLBACK_FLAG_CLOSE_CONNECTION = (
    WINHTTP_CALLBACK_STATUS_CLOSING_CONNECTION
    | WINHTTP_CALLBACK_STATUS_CONNECTION_CLOSED
)
WINHTTP_CALLBACK_FLAG_HANDLES = (
    WINHTTP_CALLBACK_STATUS_HANDLE_CREATED | WINHTTP_CALLBACK_STATUS_HANDLE_CLOSING
)
WINHTTP_CALLBACK_FLAG_DETECTING_PROXY = WINHTTP_CALLBACK_STATUS_DETECTING_PROXY
WINHTTP_CALLBACK_FLAG_REDIRECT = WINHTTP_CALLBACK_STATUS_REDIRECT
WINHTTP_CALLBACK_FLAG_INTERMEDIATE_RESPONSE = (
    WINHTTP_CALLBACK_STATUS_INTERMEDIATE_RESPONSE
)
WINHTTP_CALLBACK_FLAG_SECURE_FAILURE = WINHTTP_CALLBACK_STATUS_SECURE_FAILURE
WINHTTP_CALLBACK_FLAG_SENDREQUEST_COMPLETE = (
    WINHTTP_CALLBACK_STATUS_SENDREQUEST_COMPLETE
)
WINHTTP_CALLBACK_FLAG_HEADERS_AVAILABLE = WINHTTP_CALLBACK_STATUS_HEADERS_AVAILABLE
WINHTTP_CALLBACK_FLAG_DATA_AVAILABLE = WINHTTP_CALLBACK_STATUS_DATA_AVAILABLE
WINHTTP_CALLBACK_FLAG_READ_COMPLETE = WINHTTP_CALLBACK_STATUS_READ_COMPLETE
WINHTTP_CALLBACK_FLAG_WRITE_COMPLETE = WINHTTP_CALLBACK_STATUS_WRITE_COMPLETE
WINHTTP_CALLBACK_FLAG_REQUEST_ERROR = WINHTTP_CALLBACK_STATUS_REQUEST_ERROR
WINHTTP_CALLBACK_FLAG_ALL_COMPLETIONS = (
    WINHTTP_CALLBACK_STATUS_SENDREQUEST_COMPLETE
    | WINHTTP_CALLBACK_STATUS_HEADERS_AVAILABLE
    | WINHTTP_CALLBACK_STATUS_DATA_AVAILABLE
    | WINHTTP_CALLBACK_STATUS_READ_COMPLETE
    | WINHTTP_CALLBACK_STATUS_WRITE_COMPLETE
    | WINHTTP_CALLBACK_STATUS_REQUEST_ERROR
)
WINHTTP_CALLBACK_FLAG_ALL_NOTIFICATIONS = -1
WINHTTP_QUERY_MIME_VERSION = 0
WINHTTP_QUERY_CONTENT_TYPE = 1
WINHTTP_QUERY_CONTENT_TRANSFER_ENCODING = 2
WINHTTP_QUERY_CONTENT_ID = 3
WINHTTP_QUERY_CONTENT_DESCRIPTION = 4
WINHTTP_QUERY_CONTENT_LENGTH = 5
WINHTTP_QUERY_CONTENT_LANGUAGE = 6
WINHTTP_QUERY_ALLOW = 7
WINHTTP_QUERY_PUBLIC = 8
WINHTTP_QUERY_DATE = 9
WINHTTP_QUERY_EXPIRES = 10
WINHTTP_QUERY_LAST_MODIFIED = 11
WINHTTP_QUERY_MESSAGE_ID = 12
WINHTTP_QUERY_URI = 13
WINHTTP_QUERY_DERIVED_FROM = 14
WINHTTP_QUERY_COST = 15
WINHTTP_QUERY_LINK = 16
WINHTTP_QUERY_PRAGMA = 17
WINHTTP_QUERY_VERSION = 18
WINHTTP_QUERY_STATUS_CODE = 19
WINHTTP_QUERY_STATUS_TEXT = 20
WINHTTP_QUERY_RAW_HEADERS = 21
WINHTTP_QUERY_RAW_HEADERS_CRLF = 22
WINHTTP_QUERY_CONNECTION = 23
WINHTTP_QUERY_ACCEPT = 24
WINHTTP_QUERY_ACCEPT_CHARSET = 25
WINHTTP_QUERY_ACCEPT_ENCODING = 26
WINHTTP_QUERY_ACCEPT_LANGUAGE = 27
WINHTTP_QUERY_AUTHORIZATION = 28
WINHTTP_QUERY_CONTENT_ENCODING = 29
WINHTTP_QUERY_FORWARDED = 30
WINHTTP_QUERY_FROM = 31
WINHTTP_QUERY_IF_MODIFIED_SINCE = 32
WINHTTP_QUERY_LOCATION = 33
WINHTTP_QUERY_ORIG_URI = 34
WINHTTP_QUERY_REFERER = 35
WINHTTP_QUERY_RETRY_AFTER = 36
WINHTTP_QUERY_SERVER = 37
WINHTTP_QUERY_TITLE = 38
WINHTTP_QUERY_USER_AGENT = 39
WINHTTP_QUERY_WWW_AUTHENTICATE = 40
WINHTTP_QUERY_PROXY_AUTHENTICATE = 41
WINHTTP_QUERY_ACCEPT_RANGES = 42
WINHTTP_QUERY_SET_COOKIE = 43
WINHTTP_QUERY_COOKIE = 44
WINHTTP_QUERY_REQUEST_METHOD = 45
WINHTTP_QUERY_REFRESH = 46
WINHTTP_QUERY_CONTENT_DISPOSITION = 47
WINHTTP_QUERY_AGE = 48
WINHTTP_QUERY_CACHE_CONTROL = 49
WINHTTP_QUERY_CONTENT_BASE = 50
WINHTTP_QUERY_CONTENT_LOCATION = 51
WINHTTP_QUERY_CONTENT_MD5 = 52
WINHTTP_QUERY_CONTENT_RANGE = 53
WINHTTP_QUERY_ETAG = 54
WINHTTP_QUERY_HOST = 55
WINHTTP_QUERY_IF_MATCH = 56
WINHTTP_QUERY_IF_NONE_MATCH = 57
WINHTTP_QUERY_IF_RANGE = 58
WINHTTP_QUERY_IF_UNMODIFIED_SINCE = 59
WINHTTP_QUERY_MAX_FORWARDS = 60
WINHTTP_QUERY_PROXY_AUTHORIZATION = 61
WINHTTP_QUERY_RANGE = 62
WINHTTP_QUERY_TRANSFER_ENCODING = 63
WINHTTP_QUERY_UPGRADE = 64
WINHTTP_QUERY_VARY = 65
WINHTTP_QUERY_VIA = 66
WINHTTP_QUERY_WARNING = 67
WINHTTP_QUERY_EXPECT = 68
WINHTTP_QUERY_PROXY_CONNECTION = 69
WINHTTP_QUERY_UNLESS_MODIFIED_SINCE = 70
WINHTTP_QUERY_PROXY_SUPPORT = 75
WINHTTP_QUERY_AUTHENTICATION_INFO = 76
WINHTTP_QUERY_PASSPORT_URLS = 77
WINHTTP_QUERY_PASSPORT_CONFIG = 78
WINHTTP_QUERY_MAX = 78
WINHTTP_QUERY_CUSTOM = 65535
WINHTTP_QUERY_FLAG_REQUEST_HEADERS = -2147483648
WINHTTP_QUERY_FLAG_SYSTEMTIME = 0x40000000
WINHTTP_QUERY_FLAG_NUMBER = 0x20000000
WINHTTP_ADDREQ_INDEX_MASK = 0x0000FFFF
WINHTTP_ADDREQ_FLAGS_MASK = -65536
WINHTTP_ADDREQ_FLAG_ADD_IF_NEW = 0x10000000
WINHTTP_ADDREQ_FLAG_ADD = 0x20000000
WINHTTP_ADDREQ_FLAG_COALESCE_WITH_COMMA = 0x40000000
WINHTTP_ADDREQ_FLAG_COALESCE_WITH_SEMICOLON = 0x01000000
WINHTTP_ADDREQ_FLAG_COALESCE = WINHTTP_ADDREQ_FLAG_COALESCE_WITH_COMMA
WINHTTP_ADDREQ_FLAG_REPLACE = -2147483648
WINHTTP_IGNORE_REQUEST_TOTAL_LENGTH = 0
WINHTTP_ERROR_BASE = 12000
ERROR_WINHTTP_OUT_OF_HANDLES = WINHTTP_ERROR_BASE + 1
ERROR_WINHTTP_TIMEOUT = WINHTTP_ERROR_BASE + 2
ERROR_WINHTTP_INTERNAL_ERROR = WINHTTP_ERROR_BASE + 4
ERROR_WINHTTP_INVALID_URL = WINHTTP_ERROR_BASE + 5
ERROR_WINHTTP_UNRECOGNIZED_SCHEME = WINHTTP_ERROR_BASE + 6
ERROR_WINHTTP_NAME_NOT_RESOLVED = WINHTTP_ERROR_BASE + 7
ERROR_WINHTTP_INVALID_OPTION = WINHTTP_ERROR_BASE + 9
ERROR_WINHTTP_OPTION_NOT_SETTABLE = WINHTTP_ERROR_BASE + 11
ERROR_WINHTTP_SHUTDOWN = WINHTTP_ERROR_BASE + 12
ERROR_WINHTTP_LOGIN_FAILURE = WINHTTP_ERROR_BASE + 15
ERROR_WINHTTP_OPERATION_CANCELLED = WINHTTP_ERROR_BASE + 17
ERROR_WINHTTP_INCORRECT_HANDLE_TYPE = WINHTTP_ERROR_BASE + 18
ERROR_WINHTTP_INCORRECT_HANDLE_STATE = WINHTTP_ERROR_BASE + 19
ERROR_WINHTTP_CANNOT_CONNECT = WINHTTP_ERROR_BASE + 29
ERROR_WINHTTP_CONNECTION_ERROR = WINHTTP_ERROR_BASE + 30
ERROR_WINHTTP_RESEND_REQUEST = WINHTTP_ERROR_BASE + 32
ERROR_WINHTTP_CLIENT_AUTH_CERT_NEEDED = WINHTTP_ERROR_BASE + 44
ERROR_WINHTTP_CANNOT_CALL_BEFORE_OPEN = WINHTTP_ERROR_BASE + 100
ERROR_WINHTTP_CANNOT_CALL_BEFORE_SEND = WINHTTP_ERROR_BASE + 101
ERROR_WINHTTP_CANNOT_CALL_AFTER_SEND = WINHTTP_ERROR_BASE + 102
ERROR_WINHTTP_CANNOT_CALL_AFTER_OPEN = WINHTTP_ERROR_BASE + 103
ERROR_WINHTTP_HEADER_NOT_FOUND = WINHTTP_ERROR_BASE + 150
ERROR_WINHTTP_INVALID_SERVER_RESPONSE = WINHTTP_ERROR_BASE + 152
ERROR_WINHTTP_INVALID_HEADER = WINHTTP_ERROR_BASE + 153
ERROR_WINHTTP_INVALID_QUERY_REQUEST = WINHTTP_ERROR_BASE + 154
ERROR_WINHTTP_HEADER_ALREADY_EXISTS = WINHTTP_ERROR_BASE + 155
ERROR_WINHTTP_REDIRECT_FAILED = WINHTTP_ERROR_BASE + 156
ERROR_WINHTTP_AUTO_PROXY_SERVICE_ERROR = WINHTTP_ERROR_BASE + 178
ERROR_WINHTTP_BAD_AUTO_PROXY_SCRIPT = WINHTTP_ERROR_BASE + 166
ERROR_WINHTTP_UNABLE_TO_DOWNLOAD_SCRIPT = WINHTTP_ERROR_BASE + 167
ERROR_WINHTTP_NOT_INITIALIZED = WINHTTP_ERROR_BASE + 172
ERROR_WINHTTP_SECURE_FAILURE = WINHTTP_ERROR_BASE + 175
ERROR_WINHTTP_SECURE_CERT_DATE_INVALID = WINHTTP_ERROR_BASE + 37
ERROR_WINHTTP_SECURE_CERT_CN_INVALID = WINHTTP_ERROR_BASE + 38
ERROR_WINHTTP_SECURE_INVALID_CA = WINHTTP_ERROR_BASE + 45
ERROR_WINHTTP_SECURE_CERT_REV_FAILED = WINHTTP_ERROR_BASE + 57
ERROR_WINHTTP_SECURE_CHANNEL_ERROR = WINHTTP_ERROR_BASE + 157
ERROR_WINHTTP_SECURE_INVALID_CERT = WINHTTP_ERROR_BASE + 169
ERROR_WINHTTP_SECURE_CERT_REVOKED = WINHTTP_ERROR_BASE + 170
ERROR_WINHTTP_SECURE_CERT_WRONG_USAGE = WINHTTP_ERROR_BASE + 179
ERROR_WINHTTP_AUTODETECTION_FAILED = WINHTTP_ERROR_BASE + 180
ERROR_WINHTTP_HEADER_COUNT_EXCEEDED = WINHTTP_ERROR_BASE + 181
ERROR_WINHTTP_HEADER_SIZE_OVERFLOW = WINHTTP_ERROR_BASE + 182
ERROR_WINHTTP_CHUNKED_ENCODING_HEADER_SIZE_OVERFLOW = WINHTTP_ERROR_BASE + 183
ERROR_WINHTTP_RESPONSE_DRAIN_OVERFLOW = WINHTTP_ERROR_BASE + 184
ERROR_WINHTTP_CLIENT_CERT_NO_PRIVATE_KEY = WINHTTP_ERROR_BASE + 185
ERROR_WINHTTP_CLIENT_CERT_NO_ACCESS_PRIVATE_KEY = WINHTTP_ERROR_BASE + 186
WINHTTP_ERROR_LAST = WINHTTP_ERROR_BASE + 186

WINHTTP_NO_PROXY_NAME = None
WINHTTP_NO_PROXY_BYPASS = None
WINHTTP_NO_REFERER = None
WINHTTP_DEFAULT_ACCEPT_TYPES = None
WINHTTP_NO_ADDITIONAL_HEADERS = None
WINHTTP_NO_REQUEST_DATA = None

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\win32\lib\win32inetcon.py ===
# Generated by h2py from \mssdk\include\WinInet.h

INTERNET_INVALID_PORT_NUMBER = 0
INTERNET_DEFAULT_PORT = 0
INTERNET_DEFAULT_FTP_PORT = 21
INTERNET_DEFAULT_GOPHER_PORT = 70
INTERNET_DEFAULT_HTTP_PORT = 80
INTERNET_DEFAULT_HTTPS_PORT = 443
INTERNET_DEFAULT_SOCKS_PORT = 1080
INTERNET_MAX_HOST_NAME_LENGTH = 256
INTERNET_MAX_USER_NAME_LENGTH = 128
INTERNET_MAX_PASSWORD_LENGTH = 128
INTERNET_MAX_PORT_NUMBER_LENGTH = 5
INTERNET_MAX_PORT_NUMBER_VALUE = 65535
INTERNET_MAX_PATH_LENGTH = 2048
INTERNET_MAX_SCHEME_LENGTH = 32
INTERNET_KEEP_ALIVE_ENABLED = 1
INTERNET_KEEP_ALIVE_DISABLED = 0
INTERNET_REQFLAG_FROM_CACHE = 0x00000001
INTERNET_REQFLAG_ASYNC = 0x00000002
INTERNET_REQFLAG_VIA_PROXY = 0x00000004
INTERNET_REQFLAG_NO_HEADERS = 0x00000008
INTERNET_REQFLAG_PASSIVE = 0x00000010
INTERNET_REQFLAG_CACHE_WRITE_DISABLED = 0x00000040
INTERNET_REQFLAG_NET_TIMEOUT = 0x00000080
INTERNET_FLAG_RELOAD = -2147483648
INTERNET_FLAG_RAW_DATA = 0x40000000
INTERNET_FLAG_EXISTING_CONNECT = 0x20000000
INTERNET_FLAG_ASYNC = 0x10000000
INTERNET_FLAG_PASSIVE = 0x08000000
INTERNET_FLAG_NO_CACHE_WRITE = 0x04000000
INTERNET_FLAG_DONT_CACHE = INTERNET_FLAG_NO_CACHE_WRITE
INTERNET_FLAG_MAKE_PERSISTENT = 0x02000000
INTERNET_FLAG_FROM_CACHE = 0x01000000
INTERNET_FLAG_OFFLINE = INTERNET_FLAG_FROM_CACHE
INTERNET_FLAG_SECURE = 0x00800000
INTERNET_FLAG_KEEP_CONNECTION = 0x00400000
INTERNET_FLAG_NO_AUTO_REDIRECT = 0x00200000
INTERNET_FLAG_READ_PREFETCH = 0x00100000
INTERNET_FLAG_NO_COOKIES = 0x00080000
INTERNET_FLAG_NO_AUTH = 0x00040000
INTERNET_FLAG_RESTRICTED_ZONE = 0x00020000
INTERNET_FLAG_CACHE_IF_NET_FAIL = 0x00010000
INTERNET_FLAG_IGNORE_REDIRECT_TO_HTTP = 0x00008000
INTERNET_FLAG_IGNORE_REDIRECT_TO_HTTPS = 0x00004000
INTERNET_FLAG_IGNORE_CERT_DATE_INVALID = 0x00002000
INTERNET_FLAG_IGNORE_CERT_CN_INVALID = 0x00001000
INTERNET_FLAG_RESYNCHRONIZE = 0x00000800
INTERNET_FLAG_HYPERLINK = 0x00000400
INTERNET_FLAG_NO_UI = 0x00000200
INTERNET_FLAG_PRAGMA_NOCACHE = 0x00000100
INTERNET_FLAG_CACHE_ASYNC = 0x00000080
INTERNET_FLAG_FORMS_SUBMIT = 0x00000040
INTERNET_FLAG_FWD_BACK = 0x00000020
INTERNET_FLAG_NEED_FILE = 0x00000010
INTERNET_FLAG_MUST_CACHE_REQUEST = INTERNET_FLAG_NEED_FILE
SECURITY_INTERNET_MASK = (
    INTERNET_FLAG_IGNORE_CERT_CN_INVALID
    | INTERNET_FLAG_IGNORE_CERT_DATE_INVALID
    | INTERNET_FLAG_IGNORE_REDIRECT_TO_HTTPS
    | INTERNET_FLAG_IGNORE_REDIRECT_TO_HTTP
)
INTERNET_ERROR_MASK_INSERT_CDROM = 0x1
INTERNET_ERROR_MASK_COMBINED_SEC_CERT = 0x2
INTERNET_ERROR_MASK_NEED_MSN_SSPI_PKG = 0x4
INTERNET_ERROR_MASK_LOGIN_FAILURE_DISPLAY_ENTITY_BODY = 0x8
WININET_API_FLAG_ASYNC = 0x00000001
WININET_API_FLAG_SYNC = 0x00000004
WININET_API_FLAG_USE_CONTEXT = 0x00000008
INTERNET_NO_CALLBACK = 0
IDSI_FLAG_KEEP_ALIVE = 0x00000001
IDSI_FLAG_SECURE = 0x00000002
IDSI_FLAG_PROXY = 0x00000004
IDSI_FLAG_TUNNEL = 0x00000008
INTERNET_PER_CONN_FLAGS = 1
INTERNET_PER_CONN_PROXY_SERVER = 2
INTERNET_PER_CONN_PROXY_BYPASS = 3
INTERNET_PER_CONN_AUTOCONFIG_URL = 4
INTERNET_PER_CONN_AUTODISCOVERY_FLAGS = 5
INTERNET_PER_CONN_AUTOCONFIG_SECONDARY_URL = 6
INTERNET_PER_CONN_AUTOCONFIG_RELOAD_DELAY_MINS = 7
INTERNET_PER_CONN_AUTOCONFIG_LAST_DETECT_TIME = 8
INTERNET_PER_CONN_AUTOCONFIG_LAST_DETECT_URL = 9
PROXY_TYPE_DIRECT = 0x00000001
PROXY_TYPE_PROXY = 0x00000002
PROXY_TYPE_AUTO_PROXY_URL = 0x00000004
PROXY_TYPE_AUTO_DETECT = 0x00000008
AUTO_PROXY_FLAG_USER_SET = 0x00000001
AUTO_PROXY_FLAG_ALWAYS_DETECT = 0x00000002
AUTO_PROXY_FLAG_DETECTION_RUN = 0x00000004
AUTO_PROXY_FLAG_MIGRATED = 0x00000008
AUTO_PROXY_FLAG_DONT_CACHE_PROXY_RESULT = 0x00000010
AUTO_PROXY_FLAG_CACHE_INIT_RUN = 0x00000020
AUTO_PROXY_FLAG_DETECTION_SUSPECT = 0x00000040
ISO_FORCE_DISCONNECTED = 0x00000001
INTERNET_RFC1123_FORMAT = 0
INTERNET_RFC1123_BUFSIZE = 30
ICU_ESCAPE = -2147483648
ICU_ESCAPE_AUTHORITY = 0x00002000
ICU_REJECT_USERPWD = 0x00004000
ICU_USERNAME = 0x40000000
ICU_NO_ENCODE = 0x20000000
ICU_DECODE = 0x10000000
ICU_NO_META = 0x08000000
ICU_ENCODE_SPACES_ONLY = 0x04000000
ICU_BROWSER_MODE = 0x02000000
ICU_ENCODE_PERCENT = 0x00001000
INTERNET_OPEN_TYPE_PRECONFIG = 0
INTERNET_OPEN_TYPE_DIRECT = 1
INTERNET_OPEN_TYPE_PROXY = 3
INTERNET_OPEN_TYPE_PRECONFIG_WITH_NO_AUTOPROXY = 4
PRE_CONFIG_INTERNET_ACCESS = INTERNET_OPEN_TYPE_PRECONFIG
LOCAL_INTERNET_ACCESS = INTERNET_OPEN_TYPE_DIRECT
CERN_PROXY_INTERNET_ACCESS = INTERNET_OPEN_TYPE_PROXY
INTERNET_SERVICE_FTP = 1
INTERNET_SERVICE_GOPHER = 2
INTERNET_SERVICE_HTTP = 3
IRF_ASYNC = WININET_API_FLAG_ASYNC
IRF_SYNC = WININET_API_FLAG_SYNC
IRF_USE_CONTEXT = WININET_API_FLAG_USE_CONTEXT
IRF_NO_WAIT = 0x00000008
ISO_GLOBAL = 0x00000001
ISO_REGISTRY = 0x00000002
ISO_VALID_FLAGS = ISO_GLOBAL | ISO_REGISTRY
INTERNET_OPTION_CALLBACK = 1
INTERNET_OPTION_CONNECT_TIMEOUT = 2
INTERNET_OPTION_CONNECT_RETRIES = 3
INTERNET_OPTION_CONNECT_BACKOFF = 4
INTERNET_OPTION_SEND_TIMEOUT = 5
INTERNET_OPTION_CONTROL_SEND_TIMEOUT = INTERNET_OPTION_SEND_TIMEOUT
INTERNET_OPTION_RECEIVE_TIMEOUT = 6
INTERNET_OPTION_CONTROL_RECEIVE_TIMEOUT = INTERNET_OPTION_RECEIVE_TIMEOUT
INTERNET_OPTION_DATA_SEND_TIMEOUT = 7
INTERNET_OPTION_DATA_RECEIVE_TIMEOUT = 8
INTERNET_OPTION_HANDLE_TYPE = 9
INTERNET_OPTION_LISTEN_TIMEOUT = 11
INTERNET_OPTION_READ_BUFFER_SIZE = 12
INTERNET_OPTION_WRITE_BUFFER_SIZE = 13
INTERNET_OPTION_ASYNC_ID = 15
INTERNET_OPTION_ASYNC_PRIORITY = 16
INTERNET_OPTION_PARENT_HANDLE = 21
INTERNET_OPTION_KEEP_CONNECTION = 22
INTERNET_OPTION_REQUEST_FLAGS = 23
INTERNET_OPTION_EXTENDED_ERROR = 24
INTERNET_OPTION_OFFLINE_MODE = 26
INTERNET_OPTION_CACHE_STREAM_HANDLE = 27
INTERNET_OPTION_USERNAME = 28
INTERNET_OPTION_PASSWORD = 29
INTERNET_OPTION_ASYNC = 30
INTERNET_OPTION_SECURITY_FLAGS = 31
INTERNET_OPTION_SECURITY_CERTIFICATE_STRUCT = 32
INTERNET_OPTION_DATAFILE_NAME = 33
INTERNET_OPTION_URL = 34
INTERNET_OPTION_SECURITY_CERTIFICATE = 35
INTERNET_OPTION_SECURITY_KEY_BITNESS = 36
INTERNET_OPTION_REFRESH = 37
INTERNET_OPTION_PROXY = 38
INTERNET_OPTION_SETTINGS_CHANGED = 39
INTERNET_OPTION_VERSION = 40
INTERNET_OPTION_USER_AGENT = 41
INTERNET_OPTION_END_BROWSER_SESSION = 42
INTERNET_OPTION_PROXY_USERNAME = 43
INTERNET_OPTION_PROXY_PASSWORD = 44
INTERNET_OPTION_CONTEXT_VALUE = 45
INTERNET_OPTION_CONNECT_LIMIT = 46
INTERNET_OPTION_SECURITY_SELECT_CLIENT_CERT = 47
INTERNET_OPTION_POLICY = 48
INTERNET_OPTION_DISCONNECTED_TIMEOUT = 49
INTERNET_OPTION_CONNECTED_STATE = 50
INTERNET_OPTION_IDLE_STATE = 51
INTERNET_OPTION_OFFLINE_SEMANTICS = 52
INTERNET_OPTION_SECONDARY_CACHE_KEY = 53
INTERNET_OPTION_CALLBACK_FILTER = 54
INTERNET_OPTION_CONNECT_TIME = 55
INTERNET_OPTION_SEND_THROUGHPUT = 56
INTERNET_OPTION_RECEIVE_THROUGHPUT = 57
INTERNET_OPTION_REQUEST_PRIORITY = 58
INTERNET_OPTION_HTTP_VERSION = 59
INTERNET_OPTION_RESET_URLCACHE_SESSION = 60
INTERNET_OPTION_ERROR_MASK = 62
INTERNET_OPTION_FROM_CACHE_TIMEOUT = 63
INTERNET_OPTION_BYPASS_EDITED_ENTRY = 64
INTERNET_OPTION_DIAGNOSTIC_SOCKET_INFO = 67
INTERNET_OPTION_CODEPAGE = 68
INTERNET_OPTION_CACHE_TIMESTAMPS = 69
INTERNET_OPTION_DISABLE_AUTODIAL = 70
INTERNET_OPTION_MAX_CONNS_PER_SERVER = 73
INTERNET_OPTION_MAX_CONNS_PER_1_0_SERVER = 74
INTERNET_OPTION_PER_CONNECTION_OPTION = 75
INTERNET_OPTION_DIGEST_AUTH_UNLOAD = 76
INTERNET_OPTION_IGNORE_OFFLINE = 77
INTERNET_OPTION_IDENTITY = 78
INTERNET_OPTION_REMOVE_IDENTITY = 79
INTERNET_OPTION_ALTER_IDENTITY = 80
INTERNET_OPTION_SUPPRESS_BEHAVIOR = 81
INTERNET_OPTION_AUTODIAL_MODE = 82
INTERNET_OPTION_AUTODIAL_CONNECTION = 83
INTERNET_OPTION_CLIENT_CERT_CONTEXT = 84
INTERNET_OPTION_AUTH_FLAGS = 85
INTERNET_OPTION_COOKIES_3RD_PARTY = 86
INTERNET_OPTION_DISABLE_PASSPORT_AUTH = 87
INTERNET_OPTION_SEND_UTF8_SERVERNAME_TO_PROXY = 88
INTERNET_OPTION_EXEMPT_CONNECTION_LIMIT = 89
INTERNET_OPTION_ENABLE_PASSPORT_AUTH = 90
INTERNET_OPTION_HIBERNATE_INACTIVE_WORKER_THREADS = 91
INTERNET_OPTION_ACTIVATE_WORKER_THREADS = 92
INTERNET_OPTION_RESTORE_WORKER_THREAD_DEFAULTS = 93
INTERNET_OPTION_SOCKET_SEND_BUFFER_LENGTH = 94
INTERNET_OPTION_PROXY_SETTINGS_CHANGED = 95
INTERNET_FIRST_OPTION = INTERNET_OPTION_CALLBACK
INTERNET_LAST_OPTION = INTERNET_OPTION_PROXY_SETTINGS_CHANGED
INTERNET_PRIORITY_FOREGROUND = 1000
INTERNET_HANDLE_TYPE_INTERNET = 1
INTERNET_HANDLE_TYPE_CONNECT_FTP = 2
INTERNET_HANDLE_TYPE_CONNECT_GOPHER = 3
INTERNET_HANDLE_TYPE_CONNECT_HTTP = 4
INTERNET_HANDLE_TYPE_FTP_FIND = 5
INTERNET_HANDLE_TYPE_FTP_FIND_HTML = 6
INTERNET_HANDLE_TYPE_FTP_FILE = 7
INTERNET_HANDLE_TYPE_FTP_FILE_HTML = 8
INTERNET_HANDLE_TYPE_GOPHER_FIND = 9
INTERNET_HANDLE_TYPE_GOPHER_FIND_HTML = 10
INTERNET_HANDLE_TYPE_GOPHER_FILE = 11
INTERNET_HANDLE_TYPE_GOPHER_FILE_HTML = 12
INTERNET_HANDLE_TYPE_HTTP_REQUEST = 13
INTERNET_HANDLE_TYPE_FILE_REQUEST = 14
AUTH_FLAG_DISABLE_NEGOTIATE = 0x00000001
AUTH_FLAG_ENABLE_NEGOTIATE = 0x00000002
SECURITY_FLAG_SECURE = 0x00000001
SECURITY_FLAG_STRENGTH_WEAK = 0x10000000
SECURITY_FLAG_STRENGTH_MEDIUM = 0x40000000
SECURITY_FLAG_STRENGTH_STRONG = 0x20000000
SECURITY_FLAG_UNKNOWNBIT = -2147483648
SECURITY_FLAG_FORTEZZA = 0x08000000
SECURITY_FLAG_NORMALBITNESS = SECURITY_FLAG_STRENGTH_WEAK
SECURITY_FLAG_SSL = 0x00000002
SECURITY_FLAG_SSL3 = 0x00000004
SECURITY_FLAG_PCT = 0x00000008
SECURITY_FLAG_PCT4 = 0x00000010
SECURITY_FLAG_IETFSSL4 = 0x00000020
SECURITY_FLAG_40BIT = SECURITY_FLAG_STRENGTH_WEAK
SECURITY_FLAG_128BIT = SECURITY_FLAG_STRENGTH_STRONG
SECURITY_FLAG_56BIT = SECURITY_FLAG_STRENGTH_MEDIUM
SECURITY_FLAG_IGNORE_REVOCATION = 0x00000080
SECURITY_FLAG_IGNORE_UNKNOWN_CA = 0x00000100
SECURITY_FLAG_IGNORE_WRONG_USAGE = 0x00000200
SECURITY_FLAG_IGNORE_CERT_CN_INVALID = INTERNET_FLAG_IGNORE_CERT_CN_INVALID
SECURITY_FLAG_IGNORE_CERT_DATE_INVALID = INTERNET_FLAG_IGNORE_CERT_DATE_INVALID
SECURITY_FLAG_IGNORE_CERT_WRONG_USAGE = 0x00000200
SECURITY_FLAG_IGNORE_REDIRECT_TO_HTTPS = INTERNET_FLAG_IGNORE_REDIRECT_TO_HTTPS
SECURITY_FLAG_IGNORE_REDIRECT_TO_HTTP = INTERNET_FLAG_IGNORE_REDIRECT_TO_HTTP
SECURITY_SET_MASK = (
    SECURITY_FLAG_IGNORE_REVOCATION
    | SECURITY_FLAG_IGNORE_UNKNOWN_CA
    | SECURITY_FLAG_IGNORE_CERT_CN_INVALID
    | SECURITY_FLAG_IGNORE_CERT_DATE_INVALID
    | SECURITY_FLAG_IGNORE_WRONG_USAGE
)
AUTODIAL_MODE_NEVER = 1
AUTODIAL_MODE_ALWAYS = 2
AUTODIAL_MODE_NO_NETWORK_PRESENT = 4
INTERNET_STATUS_RESOLVING_NAME = 10
INTERNET_STATUS_NAME_RESOLVED = 11
INTERNET_STATUS_CONNECTING_TO_SERVER = 20
INTERNET_STATUS_CONNECTED_TO_SERVER = 21
INTERNET_STATUS_SENDING_REQUEST = 30
INTERNET_STATUS_REQUEST_SENT = 31
INTERNET_STATUS_RECEIVING_RESPONSE = 40
INTERNET_STATUS_RESPONSE_RECEIVED = 41
INTERNET_STATUS_CTL_RESPONSE_RECEIVED = 42
INTERNET_STATUS_PREFETCH = 43
INTERNET_STATUS_CLOSING_CONNECTION = 50
INTERNET_STATUS_CONNECTION_CLOSED = 51
INTERNET_STATUS_HANDLE_CREATED = 60
INTERNET_STATUS_HANDLE_CLOSING = 70
INTERNET_STATUS_DETECTING_PROXY = 80
INTERNET_STATUS_REQUEST_COMPLETE = 100
INTERNET_STATUS_REDIRECT = 110
INTERNET_STATUS_INTERMEDIATE_RESPONSE = 120
INTERNET_STATUS_USER_INPUT_REQUIRED = 140
INTERNET_STATUS_STATE_CHANGE = 200
INTERNET_STATUS_COOKIE_SENT = 320
INTERNET_STATUS_COOKIE_RECEIVED = 321
INTERNET_STATUS_PRIVACY_IMPACTED = 324
INTERNET_STATUS_P3P_HEADER = 325
INTERNET_STATUS_P3P_POLICYREF = 326
INTERNET_STATUS_COOKIE_HISTORY = 327
INTERNET_STATE_CONNECTED = 0x00000001
INTERNET_STATE_DISCONNECTED = 0x00000002
INTERNET_STATE_DISCONNECTED_BY_USER = 0x00000010
INTERNET_STATE_IDLE = 0x00000100
INTERNET_STATE_BUSY = 0x00000200
FTP_TRANSFER_TYPE_UNKNOWN = 0x00000000
FTP_TRANSFER_TYPE_ASCII = 0x00000001
FTP_TRANSFER_TYPE_BINARY = 0x00000002
FTP_TRANSFER_TYPE_MASK = FTP_TRANSFER_TYPE_ASCII | FTP_TRANSFER_TYPE_BINARY
MAX_GOPHER_DISPLAY_TEXT = 128
MAX_GOPHER_SELECTOR_TEXT = 256
MAX_GOPHER_HOST_NAME = INTERNET_MAX_HOST_NAME_LENGTH
MAX_GOPHER_LOCATOR_LENGTH = (
    1
    + MAX_GOPHER_DISPLAY_TEXT
    + 1
    + MAX_GOPHER_SELECTOR_TEXT
    + 1
    + MAX_GOPHER_HOST_NAME
    + 1
    + INTERNET_MAX_PORT_NUMBER_LENGTH
    + 1
    + 1
    + 2
)
GOPHER_TYPE_TEXT_FILE = 0x00000001
GOPHER_TYPE_DIRECTORY = 0x00000002
GOPHER_TYPE_CSO = 0x00000004
GOPHER_TYPE_ERROR = 0x00000008
GOPHER_TYPE_MAC_BINHEX = 0x00000010
GOPHER_TYPE_DOS_ARCHIVE = 0x00000020
GOPHER_TYPE_UNIX_UUENCODED = 0x00000040
GOPHER_TYPE_INDEX_SERVER = 0x00000080
GOPHER_TYPE_TELNET = 0x00000100
GOPHER_TYPE_BINARY = 0x00000200
GOPHER_TYPE_REDUNDANT = 0x00000400
GOPHER_TYPE_TN3270 = 0x00000800
GOPHER_TYPE_GIF = 0x00001000
GOPHER_TYPE_IMAGE = 0x00002000
GOPHER_TYPE_BITMAP = 0x00004000
GOPHER_TYPE_MOVIE = 0x00008000
GOPHER_TYPE_SOUND = 0x00010000
GOPHER_TYPE_HTML = 0x00020000
GOPHER_TYPE_PDF = 0x00040000
GOPHER_TYPE_CALENDAR = 0x00080000
GOPHER_TYPE_INLINE = 0x00100000
GOPHER_TYPE_UNKNOWN = 0x20000000
GOPHER_TYPE_ASK = 0x40000000
GOPHER_TYPE_GOPHER_PLUS = -2147483648
GOPHER_TYPE_FILE_MASK = (
    GOPHER_TYPE_TEXT_FILE
    | GOPHER_TYPE_MAC_BINHEX
    | GOPHER_TYPE_DOS_ARCHIVE
    | GOPHER_TYPE_UNIX_UUENCODED
    | GOPHER_TYPE_BINARY
    | GOPHER_TYPE_GIF
    | GOPHER_TYPE_IMAGE
    | GOPHER_TYPE_BITMAP
    | GOPHER_TYPE_MOVIE
    | GOPHER_TYPE_SOUND
    | GOPHER_TYPE_HTML
    | GOPHER_TYPE_PDF
    | GOPHER_TYPE_CALENDAR
    | GOPHER_TYPE_INLINE
)
MAX_GOPHER_CATEGORY_NAME = 128
MAX_GOPHER_ATTRIBUTE_NAME = 128
MIN_GOPHER_ATTRIBUTE_LENGTH = 256
GOPHER_ATTRIBUTE_ID_BASE = -1412641792
GOPHER_CATEGORY_ID_ALL = GOPHER_ATTRIBUTE_ID_BASE + 1
GOPHER_CATEGORY_ID_INFO = GOPHER_ATTRIBUTE_ID_BASE + 2
GOPHER_CATEGORY_ID_ADMIN = GOPHER_ATTRIBUTE_ID_BASE + 3
GOPHER_CATEGORY_ID_VIEWS = GOPHER_ATTRIBUTE_ID_BASE + 4
GOPHER_CATEGORY_ID_ABSTRACT = GOPHER_ATTRIBUTE_ID_BASE + 5
GOPHER_CATEGORY_ID_VERONICA = GOPHER_ATTRIBUTE_ID_BASE + 6
GOPHER_CATEGORY_ID_ASK = GOPHER_ATTRIBUTE_ID_BASE + 7
GOPHER_CATEGORY_ID_UNKNOWN = GOPHER_ATTRIBUTE_ID_BASE + 8
GOPHER_ATTRIBUTE_ID_ALL = GOPHER_ATTRIBUTE_ID_BASE + 9
GOPHER_ATTRIBUTE_ID_ADMIN = GOPHER_ATTRIBUTE_ID_BASE + 10
GOPHER_ATTRIBUTE_ID_MOD_DATE = GOPHER_ATTRIBUTE_ID_BASE + 11
GOPHER_ATTRIBUTE_ID_TTL = GOPHER_ATTRIBUTE_ID_BASE + 12
GOPHER_ATTRIBUTE_ID_SCORE = GOPHER_ATTRIBUTE_ID_BASE + 13
GOPHER_ATTRIBUTE_ID_RANGE = GOPHER_ATTRIBUTE_ID_BASE + 14
GOPHER_ATTRIBUTE_ID_SITE = GOPHER_ATTRIBUTE_ID_BASE + 15
GOPHER_ATTRIBUTE_ID_ORG = GOPHER_ATTRIBUTE_ID_BASE + 16
GOPHER_ATTRIBUTE_ID_LOCATION = GOPHER_ATTRIBUTE_ID_BASE + 17
GOPHER_ATTRIBUTE_ID_GEOG = GOPHER_ATTRIBUTE_ID_BASE + 18
GOPHER_ATTRIBUTE_ID_TIMEZONE = GOPHER_ATTRIBUTE_ID_BASE + 19
GOPHER_ATTRIBUTE_ID_PROVIDER = GOPHER_ATTRIBUTE_ID_BASE + 20
GOPHER_ATTRIBUTE_ID_VERSION = GOPHER_ATTRIBUTE_ID_BASE + 21
GOPHER_ATTRIBUTE_ID_ABSTRACT = GOPHER_ATTRIBUTE_ID_BASE + 22
GOPHER_ATTRIBUTE_ID_VIEW = GOPHER_ATTRIBUTE_ID_BASE + 23
GOPHER_ATTRIBUTE_ID_TREEWALK = GOPHER_ATTRIBUTE_ID_BASE + 24
GOPHER_ATTRIBUTE_ID_UNKNOWN = GOPHER_ATTRIBUTE_ID_BASE + 25
HTTP_MAJOR_VERSION = 1
HTTP_MINOR_VERSION = 0
HTTP_VERSIONA = "HTTP/1.0"
HTTP_VERSION = HTTP_VERSIONA
HTTP_QUERY_MIME_VERSION = 0
HTTP_QUERY_CONTENT_TYPE = 1
HTTP_QUERY_CONTENT_TRANSFER_ENCODING = 2
HTTP_QUERY_CONTENT_ID = 3
HTTP_QUERY_CONTENT_DESCRIPTION = 4
HTTP_QUERY_CONTENT_LENGTH = 5
HTTP_QUERY_CONTENT_LANGUAGE = 6
HTTP_QUERY_ALLOW = 7
HTTP_QUERY_PUBLIC = 8
HTTP_QUERY_DATE = 9
HTTP_QUERY_EXPIRES = 10
HTTP_QUERY_LAST_MODIFIED = 11
HTTP_QUERY_MESSAGE_ID = 12
HTTP_QUERY_URI = 13
HTTP_QUERY_DERIVED_FROM = 14
HTTP_QUERY_COST = 15
HTTP_QUERY_LINK = 16
HTTP_QUERY_PRAGMA = 17
HTTP_QUERY_VERSION = 18
HTTP_QUERY_STATUS_CODE = 19
HTTP_QUERY_STATUS_TEXT = 20
HTTP_QUERY_RAW_HEADERS = 21
HTTP_QUERY_RAW_HEADERS_CRLF = 22
HTTP_QUERY_CONNECTION = 23
HTTP_QUERY_ACCEPT = 24
HTTP_QUERY_ACCEPT_CHARSET = 25
HTTP_QUERY_ACCEPT_ENCODING = 26
HTTP_QUERY_ACCEPT_LANGUAGE = 27
HTTP_QUERY_AUTHORIZATION = 28
HTTP_QUERY_CONTENT_ENCODING = 29
HTTP_QUERY_FORWARDED = 30
HTTP_QUERY_FROM = 31
HTTP_QUERY_IF_MODIFIED_SINCE = 32
HTTP_QUERY_LOCATION = 33
HTTP_QUERY_ORIG_URI = 34
HTTP_QUERY_REFERER = 35
HTTP_QUERY_RETRY_AFTER = 36
HTTP_QUERY_SERVER = 37
HTTP_QUERY_TITLE = 38
HTTP_QUERY_USER_AGENT = 39
HTTP_QUERY_WWW_AUTHENTICATE = 40
HTTP_QUERY_PROXY_AUTHENTICATE = 41
HTTP_QUERY_ACCEPT_RANGES = 42
HTTP_QUERY_SET_COOKIE = 43
HTTP_QUERY_COOKIE = 44
HTTP_QUERY_REQUEST_METHOD = 45
HTTP_QUERY_REFRESH = 46
HTTP_QUERY_CONTENT_DISPOSITION = 47
HTTP_QUERY_AGE = 48
HTTP_QUERY_CACHE_CONTROL = 49
HTTP_QUERY_CONTENT_BASE = 50
HTTP_QUERY_CONTENT_LOCATION = 51
HTTP_QUERY_CONTENT_MD5 = 52
HTTP_QUERY_CONTENT_RANGE = 53
HTTP_QUERY_ETAG = 54
HTTP_QUERY_HOST = 55
HTTP_QUERY_IF_MATCH = 56
HTTP_QUERY_IF_NONE_MATCH = 57
HTTP_QUERY_IF_RANGE = 58
HTTP_QUERY_IF_UNMODIFIED_SINCE = 59
HTTP_QUERY_MAX_FORWARDS = 60
HTTP_QUERY_PROXY_AUTHORIZATION = 61
HTTP_QUERY_RANGE = 62
HTTP_QUERY_TRANSFER_ENCODING = 63
HTTP_QUERY_UPGRADE = 64
HTTP_QUERY_VARY = 65
HTTP_QUERY_VIA = 66
HTTP_QUERY_WARNING = 67
HTTP_QUERY_EXPECT = 68
HTTP_QUERY_PROXY_CONNECTION = 69
HTTP_QUERY_UNLESS_MODIFIED_SINCE = 70
HTTP_QUERY_ECHO_REQUEST = 71
HTTP_QUERY_ECHO_REPLY = 72
HTTP_QUERY_ECHO_HEADERS = 73
HTTP_QUERY_ECHO_HEADERS_CRLF = 74
HTTP_QUERY_PROXY_SUPPORT = 75
HTTP_QUERY_AUTHENTICATION_INFO = 76
HTTP_QUERY_PASSPORT_URLS = 77
HTTP_QUERY_PASSPORT_CONFIG = 78
HTTP_QUERY_MAX = 78
HTTP_QUERY_CUSTOM = 65535
HTTP_QUERY_FLAG_REQUEST_HEADERS = -2147483648
HTTP_QUERY_FLAG_SYSTEMTIME = 0x40000000
HTTP_QUERY_FLAG_NUMBER = 0x20000000
HTTP_QUERY_FLAG_COALESCE = 0x10000000
HTTP_QUERY_MODIFIER_FLAGS_MASK = (
    HTTP_QUERY_FLAG_REQUEST_HEADERS
    | HTTP_QUERY_FLAG_SYSTEMTIME
    | HTTP_QUERY_FLAG_NUMBER
    | HTTP_QUERY_FLAG_COALESCE
)
HTTP_QUERY_HEADER_MASK = ~HTTP_QUERY_MODIFIER_FLAGS_MASK
HTTP_STATUS_CONTINUE = 100
HTTP_STATUS_SWITCH_PROTOCOLS = 101
HTTP_STATUS_OK = 200
HTTP_STATUS_CREATED = 201
HTTP_STATUS_ACCEPTED = 202
HTTP_STATUS_PARTIAL = 203
HTTP_STATUS_NO_CONTENT = 204
HTTP_STATUS_RESET_CONTENT = 205
HTTP_STATUS_PARTIAL_CONTENT = 206
HTTP_STATUS_WEBDAV_MULTI_STATUS = 207
HTTP_STATUS_AMBIGUOUS = 300
HTTP_STATUS_MOVED = 301
HTTP_STATUS_REDIRECT = 302
HTTP_STATUS_REDIRECT_METHOD = 303
HTTP_STATUS_NOT_MODIFIED = 304
HTTP_STATUS_USE_PROXY = 305
HTTP_STATUS_REDIRECT_KEEP_VERB = 307
HTTP_STATUS_BAD_REQUEST = 400
HTTP_STATUS_DENIED = 401
HTTP_STATUS_PAYMENT_REQ = 402
HTTP_STATUS_FORBIDDEN = 403
HTTP_STATUS_NOT_FOUND = 404
HTTP_STATUS_BAD_METHOD = 405
HTTP_STATUS_NONE_ACCEPTABLE = 406
HTTP_STATUS_PROXY_AUTH_REQ = 407
HTTP_STATUS_REQUEST_TIMEOUT = 408
HTTP_STATUS_CONFLICT = 409
HTTP_STATUS_GONE = 410
HTTP_STATUS_LENGTH_REQUIRED = 411
HTTP_STATUS_PRECOND_FAILED = 412
HTTP_STATUS_REQUEST_TOO_LARGE = 413
HTTP_STATUS_URI_TOO_LONG = 414
HTTP_STATUS_UNSUPPORTED_MEDIA = 415
HTTP_STATUS_RETRY_WITH = 449
HTTP_STATUS_SERVER_ERROR = 500
HTTP_STATUS_NOT_SUPPORTED = 501
HTTP_STATUS_BAD_GATEWAY = 502
HTTP_STATUS_SERVICE_UNAVAIL = 503
HTTP_STATUS_GATEWAY_TIMEOUT = 504
HTTP_STATUS_VERSION_NOT_SUP = 505
HTTP_STATUS_FIRST = HTTP_STATUS_CONTINUE
HTTP_STATUS_LAST = HTTP_STATUS_VERSION_NOT_SUP
HTTP_ADDREQ_INDEX_MASK = 0x0000FFFF
HTTP_ADDREQ_FLAGS_MASK = -65536
HTTP_ADDREQ_FLAG_ADD_IF_NEW = 0x10000000
HTTP_ADDREQ_FLAG_ADD = 0x20000000
HTTP_ADDREQ_FLAG_COALESCE_WITH_COMMA = 0x40000000
HTTP_ADDREQ_FLAG_COALESCE_WITH_SEMICOLON = 0x01000000
HTTP_ADDREQ_FLAG_COALESCE = HTTP_ADDREQ_FLAG_COALESCE_WITH_COMMA
HTTP_ADDREQ_FLAG_REPLACE = -2147483648
HSR_ASYNC = WININET_API_FLAG_ASYNC
HSR_SYNC = WININET_API_FLAG_SYNC
HSR_USE_CONTEXT = WININET_API_FLAG_USE_CONTEXT
HSR_INITIATE = 0x00000008
HSR_DOWNLOAD = 0x00000010
HSR_CHUNKED = 0x00000020
INTERNET_COOKIE_IS_SECURE = 0x01
INTERNET_COOKIE_IS_SESSION = 0x02
INTERNET_COOKIE_THIRD_PARTY = 0x10
INTERNET_COOKIE_PROMPT_REQUIRED = 0x20
INTERNET_COOKIE_EVALUATE_P3P = 0x40
INTERNET_COOKIE_APPLY_P3P = 0x80
INTERNET_COOKIE_P3P_ENABLED = 0x100
INTERNET_COOKIE_IS_RESTRICTED = 0x200
INTERNET_COOKIE_IE6 = 0x400
INTERNET_COOKIE_IS_LEGACY = 0x800
FLAG_ICC_FORCE_CONNECTION = 0x00000001
FLAGS_ERROR_UI_FILTER_FOR_ERRORS = 0x01
FLAGS_ERROR_UI_FLAGS_CHANGE_OPTIONS = 0x02
FLAGS_ERROR_UI_FLAGS_GENERATE_DATA = 0x04
FLAGS_ERROR_UI_FLAGS_NO_UI = 0x08
FLAGS_ERROR_UI_SERIALIZE_DIALOGS = 0x10
INTERNET_ERROR_BASE = 12000
ERROR_INTERNET_OUT_OF_HANDLES = INTERNET_ERROR_BASE + 1
ERROR_INTERNET_TIMEOUT = INTERNET_ERROR_BASE + 2
ERROR_INTERNET_EXTENDED_ERROR = INTERNET_ERROR_BASE + 3
ERROR_INTERNET_INTERNAL_ERROR = INTERNET_ERROR_BASE + 4
ERROR_INTERNET_INVALID_URL = INTERNET_ERROR_BASE + 5
ERROR_INTERNET_UNRECOGNIZED_SCHEME = INTERNET_ERROR_BASE + 6
ERROR_INTERNET_NAME_NOT_RESOLVED = INTERNET_ERROR_BASE + 7
ERROR_INTERNET_PROTOCOL_NOT_FOUND = INTERNET_ERROR_BASE + 8
ERROR_INTERNET_INVALID_OPTION = INTERNET_ERROR_BASE + 9
ERROR_INTERNET_BAD_OPTION_LENGTH = INTERNET_ERROR_BASE + 10
ERROR_INTERNET_OPTION_NOT_SETTABLE = INTERNET_ERROR_BASE + 11
ERROR_INTERNET_SHUTDOWN = INTERNET_ERROR_BASE + 12
ERROR_INTERNET_INCORRECT_USER_NAME = INTERNET_ERROR_BASE + 13
ERROR_INTERNET_INCORRECT_PASSWORD = INTERNET_ERROR_BASE + 14
ERROR_INTERNET_LOGIN_FAILURE = INTERNET_ERROR_BASE + 15
ERROR_INTERNET_INVALID_OPERATION = INTERNET_ERROR_BASE + 16
ERROR_INTERNET_OPERATION_CANCELLED = INTERNET_ERROR_BASE + 17
ERROR_INTERNET_INCORRECT_HANDLE_TYPE = INTERNET_ERROR_BASE + 18
ERROR_INTERNET_INCORRECT_HANDLE_STATE = INTERNET_ERROR_BASE + 19
ERROR_INTERNET_NOT_PROXY_REQUEST = INTERNET_ERROR_BASE + 20
ERROR_INTERNET_REGISTRY_VALUE_NOT_FOUND = INTERNET_ERROR_BASE + 21
ERROR_INTERNET_BAD_REGISTRY_PARAMETER = INTERNET_ERROR_BASE + 22
ERROR_INTERNET_NO_DIRECT_ACCESS = INTERNET_ERROR_BASE + 23
ERROR_INTERNET_NO_CONTEXT = INTERNET_ERROR_BASE + 24
ERROR_INTERNET_NO_CALLBACK = INTERNET_ERROR_BASE + 25
ERROR_INTERNET_REQUEST_PENDING = INTERNET_ERROR_BASE + 26
ERROR_INTERNET_INCORRECT_FORMAT = INTERNET_ERROR_BASE + 27
ERROR_INTERNET_ITEM_NOT_FOUND = INTERNET_ERROR_BASE + 28
ERROR_INTERNET_CANNOT_CONNECT = INTERNET_ERROR_BASE + 29
ERROR_INTERNET_CONNECTION_ABORTED = INTERNET_ERROR_BASE + 30
ERROR_INTERNET_CONNECTION_RESET = INTERNET_ERROR_BASE + 31
ERROR_INTERNET_FORCE_RETRY = INTERNET_ERROR_BASE + 32
ERROR_INTERNET_INVALID_PROXY_REQUEST = INTERNET_ERROR_BASE + 33
ERROR_INTERNET_NEED_UI = INTERNET_ERROR_BASE + 34
ERROR_INTERNET_HANDLE_EXISTS = INTERNET_ERROR_BASE + 36
ERROR_INTERNET_SEC_CERT_DATE_INVALID = INTERNET_ERROR_BASE + 37
ERROR_INTERNET_SEC_CERT_CN_INVALID = INTERNET_ERROR_BASE + 38
ERROR_INTERNET_HTTP_TO_HTTPS_ON_REDIR = INTERNET_ERROR_BASE + 39
ERROR_INTERNET_HTTPS_TO_HTTP_ON_REDIR = INTERNET_ERROR_BASE + 40
ERROR_INTERNET_MIXED_SECURITY = INTERNET_ERROR_BASE + 41
ERROR_INTERNET_CHG_POST_IS_NON_SECURE = INTERNET_ERROR_BASE + 42
ERROR_INTERNET_POST_IS_NON_SECURE = INTERNET_ERROR_BASE + 43
ERROR_INTERNET_CLIENT_AUTH_CERT_NEEDED = INTERNET_ERROR_BASE + 44
ERROR_INTERNET_INVALID_CA = INTERNET_ERROR_BASE + 45
ERROR_INTERNET_CLIENT_AUTH_NOT_SETUP = INTERNET_ERROR_BASE + 46
ERROR_INTERNET_ASYNC_THREAD_FAILED = INTERNET_ERROR_BASE + 47
ERROR_INTERNET_REDIRECT_SCHEME_CHANGE = INTERNET_ERROR_BASE + 48
ERROR_INTERNET_DIALOG_PENDING = INTERNET_ERROR_BASE + 49
ERROR_INTERNET_RETRY_DIALOG = INTERNET_ERROR_BASE + 50
ERROR_INTERNET_HTTPS_HTTP_SUBMIT_REDIR = INTERNET_ERROR_BASE + 52
ERROR_INTERNET_INSERT_CDROM = INTERNET_ERROR_BASE + 53
ERROR_INTERNET_FORTEZZA_LOGIN_NEEDED = INTERNET_ERROR_BASE + 54
ERROR_INTERNET_SEC_CERT_ERRORS = INTERNET_ERROR_BASE + 55
ERROR_INTERNET_SEC_CERT_NO_REV = INTERNET_ERROR_BASE + 56
ERROR_INTERNET_SEC_CERT_REV_FAILED = INTERNET_ERROR_BASE + 57
ERROR_FTP_TRANSFER_IN_PROGRESS = INTERNET_ERROR_BASE + 110
ERROR_FTP_DROPPED = INTERNET_ERROR_BASE + 111
ERROR_FTP_NO_PASSIVE_MODE = INTERNET_ERROR_BASE + 112
ERROR_GOPHER_PROTOCOL_ERROR = INTERNET_ERROR_BASE + 130
ERROR_GOPHER_NOT_FILE = INTERNET_ERROR_BASE + 131
ERROR_GOPHER_DATA_ERROR = INTERNET_ERROR_BASE + 132
ERROR_GOPHER_END_OF_DATA = INTERNET_ERROR_BASE + 133
ERROR_GOPHER_INVALID_LOCATOR = INTERNET_ERROR_BASE + 134
ERROR_GOPHER_INCORRECT_LOCATOR_TYPE = INTERNET_ERROR_BASE + 135
ERROR_GOPHER_NOT_GOPHER_PLUS = INTERNET_ERROR_BASE + 136
ERROR_GOPHER_ATTRIBUTE_NOT_FOUND = INTERNET_ERROR_BASE + 137
ERROR_GOPHER_UNKNOWN_LOCATOR = INTERNET_ERROR_BASE + 138
ERROR_HTTP_HEADER_NOT_FOUND = INTERNET_ERROR_BASE + 150
ERROR_HTTP_DOWNLEVEL_SERVER = INTERNET_ERROR_BASE + 151
ERROR_HTTP_INVALID_SERVER_RESPONSE = INTERNET_ERROR_BASE + 152
ERROR_HTTP_INVALID_HEADER = INTERNET_ERROR_BASE + 153
ERROR_HTTP_INVALID_QUERY_REQUEST = INTERNET_ERROR_BASE + 154
ERROR_HTTP_HEADER_ALREADY_EXISTS = INTERNET_ERROR_BASE + 155
ERROR_HTTP_REDIRECT_FAILED = INTERNET_ERROR_BASE + 156
ERROR_HTTP_NOT_REDIRECTED = INTERNET_ERROR_BASE + 160
ERROR_HTTP_COOKIE_NEEDS_CONFIRMATION = INTERNET_ERROR_BASE + 161
ERROR_HTTP_COOKIE_DECLINED = INTERNET_ERROR_BASE + 162
ERROR_HTTP_REDIRECT_NEEDS_CONFIRMATION = INTERNET_ERROR_BASE + 168
ERROR_INTERNET_SECURITY_CHANNEL_ERROR = INTERNET_ERROR_BASE + 157
ERROR_INTERNET_UNABLE_TO_CACHE_FILE = INTERNET_ERROR_BASE + 158
ERROR_INTERNET_TCPIP_NOT_INSTALLED = INTERNET_ERROR_BASE + 159
ERROR_INTERNET_DISCONNECTED = INTERNET_ERROR_BASE + 163
ERROR_INTERNET_SERVER_UNREACHABLE = INTERNET_ERROR_BASE + 164
ERROR_INTERNET_PROXY_SERVER_UNREACHABLE = INTERNET_ERROR_BASE + 165
ERROR_INTERNET_BAD_AUTO_PROXY_SCRIPT = INTERNET_ERROR_BASE + 166
ERROR_INTERNET_UNABLE_TO_DOWNLOAD_SCRIPT = INTERNET_ERROR_BASE + 167
ERROR_INTERNET_SEC_INVALID_CERT = INTERNET_ERROR_BASE + 169
ERROR_INTERNET_SEC_CERT_REVOKED = INTERNET_ERROR_BASE + 170
ERROR_INTERNET_FAILED_DUETOSECURITYCHECK = INTERNET_ERROR_BASE + 171
ERROR_INTERNET_NOT_INITIALIZED = INTERNET_ERROR_BASE + 172
ERROR_INTERNET_NEED_MSN_SSPI_PKG = INTERNET_ERROR_BASE + 173
ERROR_INTERNET_LOGIN_FAILURE_DISPLAY_ENTITY_BODY = INTERNET_ERROR_BASE + 174
INTERNET_ERROR_LAST = ERROR_INTERNET_LOGIN_FAILURE_DISPLAY_ENTITY_BODY
NORMAL_CACHE_ENTRY = 0x00000001
STICKY_CACHE_ENTRY = 0x00000004
EDITED_CACHE_ENTRY = 0x00000008
TRACK_OFFLINE_CACHE_ENTRY = 0x00000010
TRACK_ONLINE_CACHE_ENTRY = 0x00000020
SPARSE_CACHE_ENTRY = 0x00010000
COOKIE_CACHE_ENTRY = 0x00100000
URLHISTORY_CACHE_ENTRY = 0x00200000
URLCACHE_FIND_DEFAULT_FILTER = (
    NORMAL_CACHE_ENTRY
    | COOKIE_CACHE_ENTRY
    | URLHISTORY_CACHE_ENTRY
    | TRACK_OFFLINE_CACHE_ENTRY
    | TRACK_ONLINE_CACHE_ENTRY
    | STICKY_CACHE_ENTRY
)
CACHEGROUP_ATTRIBUTE_GET_ALL = -1
CACHEGROUP_ATTRIBUTE_BASIC = 0x00000001
CACHEGROUP_ATTRIBUTE_FLAG = 0x00000002
CACHEGROUP_ATTRIBUTE_TYPE = 0x00000004
CACHEGROUP_ATTRIBUTE_QUOTA = 0x00000008
CACHEGROUP_ATTRIBUTE_GROUPNAME = 0x00000010
CACHEGROUP_ATTRIBUTE_STORAGE = 0x00000020
CACHEGROUP_FLAG_NONPURGEABLE = 0x00000001
CACHEGROUP_FLAG_GIDONLY = 0x00000004
CACHEGROUP_FLAG_FLUSHURL_ONDELETE = 0x00000002
CACHEGROUP_SEARCH_ALL = 0x00000000
CACHEGROUP_SEARCH_BYURL = 0x00000001
CACHEGROUP_TYPE_INVALID = 0x00000001
CACHEGROUP_READWRITE_MASK = (
    CACHEGROUP_ATTRIBUTE_TYPE
    | CACHEGROUP_ATTRIBUTE_QUOTA
    | CACHEGROUP_ATTRIBUTE_GROUPNAME
    | CACHEGROUP_ATTRIBUTE_STORAGE
)
GROUPNAME_MAX_LENGTH = 120
GROUP_OWNER_STORAGE_SIZE = 4
CACHE_ENTRY_ATTRIBUTE_FC = 0x00000004
CACHE_ENTRY_HITRATE_FC = 0x00000010
CACHE_ENTRY_MODTIME_FC = 0x00000040
CACHE_ENTRY_EXPTIME_FC = 0x00000080
CACHE_ENTRY_ACCTIME_FC = 0x00000100
CACHE_ENTRY_SYNCTIME_FC = 0x00000200
CACHE_ENTRY_HEADERINFO_FC = 0x00000400
CACHE_ENTRY_EXEMPT_DELTA_FC = 0x00000800
INTERNET_CACHE_GROUP_ADD = 0
INTERNET_CACHE_GROUP_REMOVE = 1
INTERNET_DIAL_FORCE_PROMPT = 0x2000
INTERNET_DIAL_SHOW_OFFLINE = 0x4000
INTERNET_DIAL_UNATTENDED = 0x8000
INTERENT_GOONLINE_REFRESH = 0x00000001
INTERENT_GOONLINE_MASK = 0x00000001
INTERNET_AUTODIAL_FORCE_ONLINE = 1
INTERNET_AUTODIAL_FORCE_UNATTENDED = 2
INTERNET_AUTODIAL_FAILIFSECURITYCHECK = 4
INTERNET_AUTODIAL_OVERRIDE_NET_PRESENT = 8
INTERNET_AUTODIAL_FLAGS_MASK = (
    INTERNET_AUTODIAL_FORCE_ONLINE
    | INTERNET_AUTODIAL_FORCE_UNATTENDED
    | INTERNET_AUTODIAL_FAILIFSECURITYCHECK
    | INTERNET_AUTODIAL_OVERRIDE_NET_PRESENT
)
PROXY_AUTO_DETECT_TYPE_DHCP = 1
PROXY_AUTO_DETECT_TYPE_DNS_A = 2
INTERNET_CONNECTION_MODEM = 0x01
INTERNET_CONNECTION_LAN = 0x02
INTERNET_CONNECTION_PROXY = 0x04
INTERNET_CONNECTION_MODEM_BUSY = 0x08
INTERNET_RAS_INSTALLED = 0x10
INTERNET_CONNECTION_OFFLINE = 0x20
INTERNET_CONNECTION_CONFIGURED = 0x40
INTERNET_CUSTOMDIAL_CONNECT = 0
INTERNET_CUSTOMDIAL_UNATTENDED = 1
INTERNET_CUSTOMDIAL_DISCONNECT = 2
INTERNET_CUSTOMDIAL_SHOWOFFLINE = 4
INTERNET_CUSTOMDIAL_SAFE_FOR_UNATTENDED = 1
INTERNET_CUSTOMDIAL_WILL_SUPPLY_STATE = 2
INTERNET_CUSTOMDIAL_CAN_HANGUP = 4
INTERNET_DIALSTATE_DISCONNECTED = 1
INTERNET_IDENTITY_FLAG_PRIVATE_CACHE = 0x01
INTERNET_IDENTITY_FLAG_SHARED_CACHE = 0x02
INTERNET_IDENTITY_FLAG_CLEAR_DATA = 0x04
INTERNET_IDENTITY_FLAG_CLEAR_COOKIES = 0x08
INTERNET_IDENTITY_FLAG_CLEAR_HISTORY = 0x10
INTERNET_IDENTITY_FLAG_CLEAR_CONTENT = 0x20
INTERNET_SUPPRESS_RESET_ALL = 0x00
INTERNET_SUPPRESS_COOKIE_POLICY = 0x01
INTERNET_SUPPRESS_COOKIE_POLICY_RESET = 0x02
PRIVACY_TEMPLATE_NO_COOKIES = 0
PRIVACY_TEMPLATE_HIGH = 1
PRIVACY_TEMPLATE_MEDIUM_HIGH = 2
PRIVACY_TEMPLATE_MEDIUM = 3
PRIVACY_TEMPLATE_MEDIUM_LOW = 4
PRIVACY_TEMPLATE_LOW = 5
PRIVACY_TEMPLATE_CUSTOM = 100
PRIVACY_TEMPLATE_ADVANCED = 101
PRIVACY_TEMPLATE_MAX = PRIVACY_TEMPLATE_LOW
PRIVACY_TYPE_FIRST_PARTY = 0
PRIVACY_TYPE_THIRD_PARTY = 1

# Generated by h2py from winhttp.h
WINHTTP_FLAG_ASYNC = 0x10000000
WINHTTP_FLAG_SECURE = 0x00800000
WINHTTP_FLAG_ESCAPE_PERCENT = 0x00000004
WINHTTP_FLAG_NULL_CODEPAGE = 0x00000008
WINHTTP_FLAG_BYPASS_PROXY_CACHE = 0x00000100
WINHTTP_FLAG_REFRESH = WINHTTP_FLAG_BYPASS_PROXY_CACHE
WINHTTP_FLAG_ESCAPE_DISABLE = 0x00000040
WINHTTP_FLAG_ESCAPE_DISABLE_QUERY = 0x00000080
INTERNET_SCHEME_HTTP = 1
INTERNET_SCHEME_HTTPS = 2
WINHTTP_AUTOPROXY_AUTO_DETECT = 0x00000001
WINHTTP_AUTOPROXY_CONFIG_URL = 0x00000002
WINHTTP_AUTOPROXY_RUN_INPROCESS = 0x00010000
WINHTTP_AUTOPROXY_RUN_OUTPROCESS_ONLY = 0x00020000
WINHTTP_AUTO_DETECT_TYPE_DHCP = 0x00000001
WINHTTP_AUTO_DETECT_TYPE_DNS_A = 0x00000002
WINHTTP_TIME_FORMAT_BUFSIZE = 62
WINHTTP_ACCESS_TYPE_DEFAULT_PROXY = 0
WINHTTP_ACCESS_TYPE_NO_PROXY = 1
WINHTTP_ACCESS_TYPE_NAMED_PROXY = 3
WINHTTP_OPTION_CALLBACK = 1
WINHTTP_OPTION_RESOLVE_TIMEOUT = 2
WINHTTP_OPTION_CONNECT_TIMEOUT = 3
WINHTTP_OPTION_CONNECT_RETRIES = 4
WINHTTP_OPTION_SEND_TIMEOUT = 5
WINHTTP_OPTION_RECEIVE_TIMEOUT = 6
WINHTTP_OPTION_RECEIVE_RESPONSE_TIMEOUT = 7
WINHTTP_OPTION_HANDLE_TYPE = 9
WINHTTP_OPTION_READ_BUFFER_SIZE = 12
WINHTTP_OPTION_WRITE_BUFFER_SIZE = 13
WINHTTP_OPTION_PARENT_HANDLE = 21
WINHTTP_OPTION_EXTENDED_ERROR = 24
WINHTTP_OPTION_SECURITY_FLAGS = 31
WINHTTP_OPTION_SECURITY_CERTIFICATE_STRUCT = 32
WINHTTP_OPTION_URL = 34
WINHTTP_OPTION_SECURITY_KEY_BITNESS = 36
WINHTTP_OPTION_PROXY = 38
WINHTTP_OPTION_USER_AGENT = 41
WINHTTP_OPTION_CONTEXT_VALUE = 45
WINHTTP_OPTION_CLIENT_CERT_CONTEXT = 47
WINHTTP_OPTION_REQUEST_PRIORITY = 58
WINHTTP_OPTION_HTTP_VERSION = 59
WINHTTP_OPTION_DISABLE_FEATURE = 63
WINHTTP_OPTION_CODEPAGE = 68
WINHTTP_OPTION_MAX_CONNS_PER_SERVER = 73
WINHTTP_OPTION_MAX_CONNS_PER_1_0_SERVER = 74
WINHTTP_OPTION_AUTOLOGON_POLICY = 77
WINHTTP_OPTION_SERVER_CERT_CONTEXT = 78
WINHTTP_OPTION_ENABLE_FEATURE = 79
WINHTTP_OPTION_WORKER_THREAD_COUNT = 80
WINHTTP_OPTION_PASSPORT_COBRANDING_TEXT = 81
WINHTTP_OPTION_PASSPORT_COBRANDING_URL = 82
WINHTTP_OPTION_CONFIGURE_PASSPORT_AUTH = 83
WINHTTP_OPTION_SECURE_PROTOCOLS = 84
WINHTTP_OPTION_ENABLETRACING = 85
WINHTTP_OPTION_PASSPORT_SIGN_OUT = 86
WINHTTP_OPTION_PASSPORT_RETURN_URL = 87
WINHTTP_OPTION_REDIRECT_POLICY = 88
WINHTTP_OPTION_MAX_HTTP_AUTOMATIC_REDIRECTS = 89
WINHTTP_OPTION_MAX_HTTP_STATUS_CONTINUE = 90
WINHTTP_OPTION_MAX_RESPONSE_HEADER_SIZE = 91
WINHTTP_OPTION_MAX_RESPONSE_DRAIN_SIZE = 92
WINHTTP_OPTION_CONNECTION_INFO = 93
WINHTTP_OPTION_CLIENT_CERT_ISSUER_LIST = 94
WINHTTP_OPTION_SPN = 96
WINHTTP_OPTION_GLOBAL_PROXY_CREDS = 97
WINHTTP_OPTION_GLOBAL_SERVER_CREDS = 98
WINHTTP_OPTION_UNLOAD_NOTIFY_EVENT = 99
WINHTTP_OPTION_REJECT_USERPWD_IN_URL = 100
WINHTTP_OPTION_USE_GLOBAL_SERVER_CREDENTIALS = 101
WINHTTP_LAST_OPTION = WINHTTP_OPTION_USE_GLOBAL_SERVER_CREDENTIALS
WINHTTP_OPTION_USERNAME = 0x1000
WINHTTP_OPTION_PASSWORD = 0x1001
WINHTTP_OPTION_PROXY_USERNAME = 0x1002
WINHTTP_OPTION_PROXY_PASSWORD = 0x1003
WINHTTP_CONNS_PER_SERVER_UNLIMITED = -1
WINHTTP_AUTOLOGON_SECURITY_LEVEL_MEDIUM = 0
WINHTTP_AUTOLOGON_SECURITY_LEVEL_LOW = 1
WINHTTP_AUTOLOGON_SECURITY_LEVEL_HIGH = 2
WINHTTP_AUTOLOGON_SECURITY_LEVEL_DEFAULT = WINHTTP_AUTOLOGON_SECURITY_LEVEL_MEDIUM
WINHTTP_OPTION_REDIRECT_POLICY_NEVER = 0
WINHTTP_OPTION_REDIRECT_POLICY_DISALLOW_HTTPS_TO_HTTP = 1
WINHTTP_OPTION_REDIRECT_POLICY_ALWAYS = 2
WINHTTP_OPTION_REDIRECT_POLICY_LAST = WINHTTP_OPTION_REDIRECT_POLICY_ALWAYS
WINHTTP_OPTION_REDIRECT_POLICY_DEFAULT = (
    WINHTTP_OPTION_REDIRECT_POLICY_DISALLOW_HTTPS_TO_HTTP
)
WINHTTP_DISABLE_PASSPORT_AUTH = 0x00000000
WINHTTP_ENABLE_PASSPORT_AUTH = 0x10000000
WINHTTP_DISABLE_PASSPORT_KEYRING = 0x20000000
WINHTTP_ENABLE_PASSPORT_KEYRING = 0x40000000
WINHTTP_DISABLE_COOKIES = 0x00000001
WINHTTP_DISABLE_REDIRECTS = 0x00000002
WINHTTP_DISABLE_AUTHENTICATION = 0x00000004
WINHTTP_DISABLE_KEEP_ALIVE = 0x00000008
WINHTTP_ENABLE_SSL_REVOCATION = 0x00000001
WINHTTP_ENABLE_SSL_REVERT_IMPERSONATION = 0x00000002
WINHTTP_DISABLE_SPN_SERVER_PORT = 0x00000000
WINHTTP_ENABLE_SPN_SERVER_PORT = 0x00000001
WINHTTP_OPTION_SPN_MASK = WINHTTP_ENABLE_SPN_SERVER_PORT
WINHTTP_HANDLE_TYPE_SESSION = 1
WINHTTP_HANDLE_TYPE_CONNECT = 2
WINHTTP_HANDLE_TYPE_REQUEST = 3
WINHTTP_AUTH_SCHEME_BASIC = 0x00000001
WINHTTP_AUTH_SCHEME_NTLM = 0x00000002
WINHTTP_AUTH_SCHEME_PASSPORT = 0x00000004
WINHTTP_AUTH_SCHEME_DIGEST = 0x00000008
WINHTTP_AUTH_SCHEME_NEGOTIATE = 0x00000010
WINHTTP_AUTH_TARGET_SERVER = 0x00000000
WINHTTP_AUTH_TARGET_PROXY = 0x00000001
WINHTTP_CALLBACK_STATUS_FLAG_CERT_REV_FAILED = 0x00000001
WINHTTP_CALLBACK_STATUS_FLAG_INVALID_CERT = 0x00000002
WINHTTP_CALLBACK_STATUS_FLAG_CERT_REVOKED = 0x00000004
WINHTTP_CALLBACK_STATUS_FLAG_INVALID_CA = 0x00000008
WINHTTP_CALLBACK_STATUS_FLAG_CERT_CN_INVALID = 0x00000010
WINHTTP_CALLBACK_STATUS_FLAG_CERT_DATE_INVALID = 0x00000020
WINHTTP_CALLBACK_STATUS_FLAG_CERT_WRONG_USAGE = 0x00000040
WINHTTP_CALLBACK_STATUS_FLAG_SECURITY_CHANNEL_ERROR = -2147483648
WINHTTP_FLAG_SECURE_PROTOCOL_SSL2 = 0x00000008
WINHTTP_FLAG_SECURE_PROTOCOL_SSL3 = 0x00000020
WINHTTP_FLAG_SECURE_PROTOCOL_TLS1 = 0x00000080
WINHTTP_FLAG_SECURE_PROTOCOL_ALL = (
    WINHTTP_FLAG_SECURE_PROTOCOL_SSL2
    | WINHTTP_FLAG_SECURE_PROTOCOL_SSL3
    | WINHTTP_FLAG_SECURE_PROTOCOL_TLS1
)
WINHTTP_CALLBACK_STATUS_RESOLVING_NAME = 0x00000001
WINHTTP_CALLBACK_STATUS_NAME_RESOLVED = 0x00000002
WINHTTP_CALLBACK_STATUS_CONNECTING_TO_SERVER = 0x00000004
WINHTTP_CALLBACK_STATUS_CONNECTED_TO_SERVER = 0x00000008
WINHTTP_CALLBACK_STATUS_SENDING_REQUEST = 0x00000010
WINHTTP_CALLBACK_STATUS_REQUEST_SENT = 0x00000020
WINHTTP_CALLBACK_STATUS_RECEIVING_RESPONSE = 0x00000040
WINHTTP_CALLBACK_STATUS_RESPONSE_RECEIVED = 0x00000080
WINHTTP_CALLBACK_STATUS_CLOSING_CONNECTION = 0x00000100
WINHTTP_CALLBACK_STATUS_CONNECTION_CLOSED = 0x00000200
WINHTTP_CALLBACK_STATUS_HANDLE_CREATED = 0x00000400
WINHTTP_CALLBACK_STATUS_HANDLE_CLOSING = 0x00000800
WINHTTP_CALLBACK_STATUS_DETECTING_PROXY = 0x00001000
WINHTTP_CALLBACK_STATUS_REDIRECT = 0x00004000
WINHTTP_CALLBACK_STATUS_INTERMEDIATE_RESPONSE = 0x00008000
WINHTTP_CALLBACK_STATUS_SECURE_FAILURE = 0x00010000
WINHTTP_CALLBACK_STATUS_HEADERS_AVAILABLE = 0x00020000
WINHTTP_CALLBACK_STATUS_DATA_AVAILABLE = 0x00040000
WINHTTP_CALLBACK_STATUS_READ_COMPLETE = 0x00080000
WINHTTP_CALLBACK_STATUS_WRITE_COMPLETE = 0x00100000
WINHTTP_CALLBACK_STATUS_REQUEST_ERROR = 0x00200000
WINHTTP_CALLBACK_STATUS_SENDREQUEST_COMPLETE = 0x00400000
API_RECEIVE_RESPONSE = 1
API_QUERY_DATA_AVAILABLE = 2
API_READ_DATA = 3
API_WRITE_DATA = 4
API_SEND_REQUEST = 5
WINHTTP_CALLBACK_FLAG_RESOLVE_NAME = (
    WINHTTP_CALLBACK_STATUS_RESOLVING_NAME | WINHTTP_CALLBACK_STATUS_NAME_RESOLVED
)
WINHTTP_CALLBACK_FLAG_CONNECT_TO_SERVER = (
    WINHTTP_CALLBACK_STATUS_CONNECTING_TO_SERVER
    | WINHTTP_CALLBACK_STATUS_CONNECTED_TO_SERVER
)
WINHTTP_CALLBACK_FLAG_SEND_REQUEST = (
    WINHTTP_CALLBACK_STATUS_SENDING_REQUEST | WINHTTP_CALLBACK_STATUS_REQUEST_SENT
)
WINHTTP_CALLBACK_FLAG_RECEIVE_RESPONSE = (
    WINHTTP_CALLBACK_STATUS_RECEIVING_RESPONSE
    | WINHTTP_CALLBACK_STATUS_RESPONSE_RECEIVED
)
WINHTTP_CALLBACK_FLAG_CLOSE_CONNECTION = (
    WINHTTP_CALLBACK_STATUS_CLOSING_CONNECTION
    | WINHTTP_CALLBACK_STATUS_CONNECTION_CLOSED
)
WINHTTP_CALLBACK_FLAG_HANDLES = (
    WINHTTP_CALLBACK_STATUS_HANDLE_CREATED | WINHTTP_CALLBACK_STATUS_HANDLE_CLOSING
)
WINHTTP_CALLBACK_FLAG_DETECTING_PROXY = WINHTTP_CALLBACK_STATUS_DETECTING_PROXY
WINHTTP_CALLBACK_FLAG_REDIRECT = WINHTTP_CALLBACK_STATUS_REDIRECT
WINHTTP_CALLBACK_FLAG_INTERMEDIATE_RESPONSE = (
    WINHTTP_CALLBACK_STATUS_INTERMEDIATE_RESPONSE
)
WINHTTP_CALLBACK_FLAG_SECURE_FAILURE = WINHTTP_CALLBACK_STATUS_SECURE_FAILURE
WINHTTP_CALLBACK_FLAG_SENDREQUEST_COMPLETE = (
    WINHTTP_CALLBACK_STATUS_SENDREQUEST_COMPLETE
)
WINHTTP_CALLBACK_FLAG_HEADERS_AVAILABLE = WINHTTP_CALLBACK_STATUS_HEADERS_AVAILABLE
WINHTTP_CALLBACK_FLAG_DATA_AVAILABLE = WINHTTP_CALLBACK_STATUS_DATA_AVAILABLE
WINHTTP_CALLBACK_FLAG_READ_COMPLETE = WINHTTP_CALLBACK_STATUS_READ_COMPLETE
WINHTTP_CALLBACK_FLAG_WRITE_COMPLETE = WINHTTP_CALLBACK_STATUS_WRITE_COMPLETE
WINHTTP_CALLBACK_FLAG_REQUEST_ERROR = WINHTTP_CALLBACK_STATUS_REQUEST_ERROR
WINHTTP_CALLBACK_FLAG_ALL_COMPLETIONS = (
    WINHTTP_CALLBACK_STATUS_SENDREQUEST_COMPLETE
    | WINHTTP_CALLBACK_STATUS_HEADERS_AVAILABLE
    | WINHTTP_CALLBACK_STATUS_DATA_AVAILABLE
    | WINHTTP_CALLBACK_STATUS_READ_COMPLETE
    | WINHTTP_CALLBACK_STATUS_WRITE_COMPLETE
    | WINHTTP_CALLBACK_STATUS_REQUEST_ERROR
)
WINHTTP_CALLBACK_FLAG_ALL_NOTIFICATIONS = -1
WINHTTP_QUERY_MIME_VERSION = 0
WINHTTP_QUERY_CONTENT_TYPE = 1
WINHTTP_QUERY_CONTENT_TRANSFER_ENCODING = 2
WINHTTP_QUERY_CONTENT_ID = 3
WINHTTP_QUERY_CONTENT_DESCRIPTION = 4
WINHTTP_QUERY_CONTENT_LENGTH = 5
WINHTTP_QUERY_CONTENT_LANGUAGE = 6
WINHTTP_QUERY_ALLOW = 7
WINHTTP_QUERY_PUBLIC = 8
WINHTTP_QUERY_DATE = 9
WINHTTP_QUERY_EXPIRES = 10
WINHTTP_QUERY_LAST_MODIFIED = 11
WINHTTP_QUERY_MESSAGE_ID = 12
WINHTTP_QUERY_URI = 13
WINHTTP_QUERY_DERIVED_FROM = 14
WINHTTP_QUERY_COST = 15
WINHTTP_QUERY_LINK = 16
WINHTTP_QUERY_PRAGMA = 17
WINHTTP_QUERY_VERSION = 18
WINHTTP_QUERY_STATUS_CODE = 19
WINHTTP_QUERY_STATUS_TEXT = 20
WINHTTP_QUERY_RAW_HEADERS = 21
WINHTTP_QUERY_RAW_HEADERS_CRLF = 22
WINHTTP_QUERY_CONNECTION = 23
WINHTTP_QUERY_ACCEPT = 24
WINHTTP_QUERY_ACCEPT_CHARSET = 25
WINHTTP_QUERY_ACCEPT_ENCODING = 26
WINHTTP_QUERY_ACCEPT_LANGUAGE = 27
WINHTTP_QUERY_AUTHORIZATION = 28
WINHTTP_QUERY_CONTENT_ENCODING = 29
WINHTTP_QUERY_FORWARDED = 30
WINHTTP_QUERY_FROM = 31
WINHTTP_QUERY_IF_MODIFIED_SINCE = 32
WINHTTP_QUERY_LOCATION = 33
WINHTTP_QUERY_ORIG_URI = 34
WINHTTP_QUERY_REFERER = 35
WINHTTP_QUERY_RETRY_AFTER = 36
WINHTTP_QUERY_SERVER = 37
WINHTTP_QUERY_TITLE = 38
WINHTTP_QUERY_USER_AGENT = 39
WINHTTP_QUERY_WWW_AUTHENTICATE = 40
WINHTTP_QUERY_PROXY_AUTHENTICATE = 41
WINHTTP_QUERY_ACCEPT_RANGES = 42
WINHTTP_QUERY_SET_COOKIE = 43
WINHTTP_QUERY_COOKIE = 44
WINHTTP_QUERY_REQUEST_METHOD = 45
WINHTTP_QUERY_REFRESH = 46
WINHTTP_QUERY_CONTENT_DISPOSITION = 47
WINHTTP_QUERY_AGE = 48
WINHTTP_QUERY_CACHE_CONTROL = 49
WINHTTP_QUERY_CONTENT_BASE = 50
WINHTTP_QUERY_CONTENT_LOCATION = 51
WINHTTP_QUERY_CONTENT_MD5 = 52
WINHTTP_QUERY_CONTENT_RANGE = 53
WINHTTP_QUERY_ETAG = 54
WINHTTP_QUERY_HOST = 55
WINHTTP_QUERY_IF_MATCH = 56
WINHTTP_QUERY_IF_NONE_MATCH = 57
WINHTTP_QUERY_IF_RANGE = 58
WINHTTP_QUERY_IF_UNMODIFIED_SINCE = 59
WINHTTP_QUERY_MAX_FORWARDS = 60
WINHTTP_QUERY_PROXY_AUTHORIZATION = 61
WINHTTP_QUERY_RANGE = 62
WINHTTP_QUERY_TRANSFER_ENCODING = 63
WINHTTP_QUERY_UPGRADE = 64
WINHTTP_QUERY_VARY = 65
WINHTTP_QUERY_VIA = 66
WINHTTP_QUERY_WARNING = 67
WINHTTP_QUERY_EXPECT = 68
WINHTTP_QUERY_PROXY_CONNECTION = 69
WINHTTP_QUERY_UNLESS_MODIFIED_SINCE = 70
WINHTTP_QUERY_PROXY_SUPPORT = 75
WINHTTP_QUERY_AUTHENTICATION_INFO = 76
WINHTTP_QUERY_PASSPORT_URLS = 77
WINHTTP_QUERY_PASSPORT_CONFIG = 78
WINHTTP_QUERY_MAX = 78
WINHTTP_QUERY_CUSTOM = 65535
WINHTTP_QUERY_FLAG_REQUEST_HEADERS = -2147483648
WINHTTP_QUERY_FLAG_SYSTEMTIME = 0x40000000
WINHTTP_QUERY_FLAG_NUMBER = 0x20000000
WINHTTP_ADDREQ_INDEX_MASK = 0x0000FFFF
WINHTTP_ADDREQ_FLAGS_MASK = -65536
WINHTTP_ADDREQ_FLAG_ADD_IF_NEW = 0x10000000
WINHTTP_ADDREQ_FLAG_ADD = 0x20000000
WINHTTP_ADDREQ_FLAG_COALESCE_WITH_COMMA = 0x40000000
WINHTTP_ADDREQ_FLAG_COALESCE_WITH_SEMICOLON = 0x01000000
WINHTTP_ADDREQ_FLAG_COALESCE = WINHTTP_ADDREQ_FLAG_COALESCE_WITH_COMMA
WINHTTP_ADDREQ_FLAG_REPLACE = -2147483648
WINHTTP_IGNORE_REQUEST_TOTAL_LENGTH = 0
WINHTTP_ERROR_BASE = 12000
ERROR_WINHTTP_OUT_OF_HANDLES = WINHTTP_ERROR_BASE + 1
ERROR_WINHTTP_TIMEOUT = WINHTTP_ERROR_BASE + 2
ERROR_WINHTTP_INTERNAL_ERROR = WINHTTP_ERROR_BASE + 4
ERROR_WINHTTP_INVALID_URL = WINHTTP_ERROR_BASE + 5
ERROR_WINHTTP_UNRECOGNIZED_SCHEME = WINHTTP_ERROR_BASE + 6
ERROR_WINHTTP_NAME_NOT_RESOLVED = WINHTTP_ERROR_BASE + 7
ERROR_WINHTTP_INVALID_OPTION = WINHTTP_ERROR_BASE + 9
ERROR_WINHTTP_OPTION_NOT_SETTABLE = WINHTTP_ERROR_BASE + 11
ERROR_WINHTTP_SHUTDOWN = WINHTTP_ERROR_BASE + 12
ERROR_WINHTTP_LOGIN_FAILURE = WINHTTP_ERROR_BASE + 15
ERROR_WINHTTP_OPERATION_CANCELLED = WINHTTP_ERROR_BASE + 17
ERROR_WINHTTP_INCORRECT_HANDLE_TYPE = WINHTTP_ERROR_BASE + 18
ERROR_WINHTTP_INCORRECT_HANDLE_STATE = WINHTTP_ERROR_BASE + 19
ERROR_WINHTTP_CANNOT_CONNECT = WINHTTP_ERROR_BASE + 29
ERROR_WINHTTP_CONNECTION_ERROR = WINHTTP_ERROR_BASE + 30
ERROR_WINHTTP_RESEND_REQUEST = WINHTTP_ERROR_BASE + 32
ERROR_WINHTTP_CLIENT_AUTH_CERT_NEEDED = WINHTTP_ERROR_BASE + 44
ERROR_WINHTTP_CANNOT_CALL_BEFORE_OPEN = WINHTTP_ERROR_BASE + 100
ERROR_WINHTTP_CANNOT_CALL_BEFORE_SEND = WINHTTP_ERROR_BASE + 101
ERROR_WINHTTP_CANNOT_CALL_AFTER_SEND = WINHTTP_ERROR_BASE + 102
ERROR_WINHTTP_CANNOT_CALL_AFTER_OPEN = WINHTTP_ERROR_BASE + 103
ERROR_WINHTTP_HEADER_NOT_FOUND = WINHTTP_ERROR_BASE + 150
ERROR_WINHTTP_INVALID_SERVER_RESPONSE = WINHTTP_ERROR_BASE + 152
ERROR_WINHTTP_INVALID_HEADER = WINHTTP_ERROR_BASE + 153
ERROR_WINHTTP_INVALID_QUERY_REQUEST = WINHTTP_ERROR_BASE + 154
ERROR_WINHTTP_HEADER_ALREADY_EXISTS = WINHTTP_ERROR_BASE + 155
ERROR_WINHTTP_REDIRECT_FAILED = WINHTTP_ERROR_BASE + 156
ERROR_WINHTTP_AUTO_PROXY_SERVICE_ERROR = WINHTTP_ERROR_BASE + 178
ERROR_WINHTTP_BAD_AUTO_PROXY_SCRIPT = WINHTTP_ERROR_BASE + 166
ERROR_WINHTTP_UNABLE_TO_DOWNLOAD_SCRIPT = WINHTTP_ERROR_BASE + 167
ERROR_WINHTTP_NOT_INITIALIZED = WINHTTP_ERROR_BASE + 172
ERROR_WINHTTP_SECURE_FAILURE = WINHTTP_ERROR_BASE + 175
ERROR_WINHTTP_SECURE_CERT_DATE_INVALID = WINHTTP_ERROR_BASE + 37
ERROR_WINHTTP_SECURE_CERT_CN_INVALID = WINHTTP_ERROR_BASE + 38
ERROR_WINHTTP_SECURE_INVALID_CA = WINHTTP_ERROR_BASE + 45
ERROR_WINHTTP_SECURE_CERT_REV_FAILED = WINHTTP_ERROR_BASE + 57
ERROR_WINHTTP_SECURE_CHANNEL_ERROR = WINHTTP_ERROR_BASE + 157
ERROR_WINHTTP_SECURE_INVALID_CERT = WINHTTP_ERROR_BASE + 169
ERROR_WINHTTP_SECURE_CERT_REVOKED = WINHTTP_ERROR_BASE + 170
ERROR_WINHTTP_SECURE_CERT_WRONG_USAGE = WINHTTP_ERROR_BASE + 179
ERROR_WINHTTP_AUTODETECTION_FAILED = WINHTTP_ERROR_BASE + 180
ERROR_WINHTTP_HEADER_COUNT_EXCEEDED = WINHTTP_ERROR_BASE + 181
ERROR_WINHTTP_HEADER_SIZE_OVERFLOW = WINHTTP_ERROR_BASE + 182
ERROR_WINHTTP_CHUNKED_ENCODING_HEADER_SIZE_OVERFLOW = WINHTTP_ERROR_BASE + 183
ERROR_WINHTTP_RESPONSE_DRAIN_OVERFLOW = WINHTTP_ERROR_BASE + 184
ERROR_WINHTTP_CLIENT_CERT_NO_PRIVATE_KEY = WINHTTP_ERROR_BASE + 185
ERROR_WINHTTP_CLIENT_CERT_NO_ACCESS_PRIVATE_KEY = WINHTTP_ERROR_BASE + 186
WINHTTP_ERROR_LAST = WINHTTP_ERROR_BASE + 186

WINHTTP_NO_PROXY_NAME = None
WINHTTP_NO_PROXY_BYPASS = None
WINHTTP_NO_REFERER = None
WINHTTP_DEFAULT_ACCEPT_TYPES = None
WINHTTP_NO_ADDITIONAL_HEADERS = None
WINHTTP_NO_REQUEST_DATA = None

# === NexusCore/openenv\Lib\site-packages\numpy\lib\_histograms_impl.py ===
"""
Histogram-related functions
"""
import contextlib
import functools
import operator
import warnings

import numpy as np
from numpy._core import overrides

__all__ = ['histogram', 'histogramdd', 'histogram_bin_edges']

array_function_dispatch = functools.partial(
    overrides.array_function_dispatch, module='numpy')

# range is a keyword argument to many functions, so save the builtin so they can
# use it.
_range = range


def _ptp(x):
    """Peak-to-peak value of x.

    This implementation avoids the problem of signed integer arrays having a
    peak-to-peak value that cannot be represented with the array's data type.
    This function returns an unsigned value for signed integer arrays.
    """
    return _unsigned_subtract(x.max(), x.min())


def _hist_bin_sqrt(x, range):
    """
    Square root histogram bin estimator.

    Bin width is inversely proportional to the data size. Used by many
    programs for its simplicity.

    Parameters
    ----------
    x : array_like
        Input data that is to be histogrammed, trimmed to range. May not
        be empty.

    Returns
    -------
    h : An estimate of the optimal bin width for the given data.
    """
    del range  # unused
    return _ptp(x) / np.sqrt(x.size)


def _hist_bin_sturges(x, range):
    """
    Sturges histogram bin estimator.

    A very simplistic estimator based on the assumption of normality of
    the data. This estimator has poor performance for non-normal data,
    which becomes especially obvious for large data sets. The estimate
    depends only on size of the data.

    Parameters
    ----------
    x : array_like
        Input data that is to be histogrammed, trimmed to range. May not
        be empty.

    Returns
    -------
    h : An estimate of the optimal bin width for the given data.
    """
    del range  # unused
    return _ptp(x) / (np.log2(x.size) + 1.0)


def _hist_bin_rice(x, range):
    """
    Rice histogram bin estimator.

    Another simple estimator with no normality assumption. It has better
    performance for large data than Sturges, but tends to overestimate
    the number of bins. The number of bins is proportional to the cube
    root of data size (asymptotically optimal). The estimate depends
    only on size of the data.

    Parameters
    ----------
    x : array_like
        Input data that is to be histogrammed, trimmed to range. May not
        be empty.

    Returns
    -------
    h : An estimate of the optimal bin width for the given data.
    """
    del range  # unused
    return _ptp(x) / (2.0 * x.size ** (1.0 / 3))


def _hist_bin_scott(x, range):
    """
    Scott histogram bin estimator.

    The binwidth is proportional to the standard deviation of the data
    and inversely proportional to the cube root of data size
    (asymptotically optimal).

    Parameters
    ----------
    x : array_like
        Input data that is to be histogrammed, trimmed to range. May not
        be empty.

    Returns
    -------
    h : An estimate of the optimal bin width for the given data.
    """
    del range  # unused
    return (24.0 * np.pi**0.5 / x.size)**(1.0 / 3.0) * np.std(x)


def _hist_bin_stone(x, range):
    """
    Histogram bin estimator based on minimizing the estimated integrated squared error (ISE).

    The number of bins is chosen by minimizing the estimated ISE against the unknown
    true distribution. The ISE is estimated using cross-validation and can be regarded
    as a generalization of Scott's rule.
    https://en.wikipedia.org/wiki/Histogram#Scott.27s_normal_reference_rule

    This paper by Stone appears to be the origination of this rule.
    https://digitalassets.lib.berkeley.edu/sdtr/ucb/text/34.pdf

    Parameters
    ----------
    x : array_like
        Input data that is to be histogrammed, trimmed to range. May not
        be empty.
    range : (float, float)
        The lower and upper range of the bins.

    Returns
    -------
    h : An estimate of the optimal bin width for the given data.
    """  # noqa: E501

    n = x.size
    ptp_x = _ptp(x)
    if n <= 1 or ptp_x == 0:
        return 0

    def jhat(nbins):
        hh = ptp_x / nbins
        p_k = np.histogram(x, bins=nbins, range=range)[0] / n
        return (2 - (n + 1) * p_k.dot(p_k)) / hh

    nbins_upper_bound = max(100, int(np.sqrt(n)))
    nbins = min(_range(1, nbins_upper_bound + 1), key=jhat)
    if nbins == nbins_upper_bound:
        warnings.warn("The number of bins estimated may be suboptimal.",
                      RuntimeWarning, stacklevel=3)
    return ptp_x / nbins


def _hist_bin_doane(x, range):
    """
    Doane's histogram bin estimator.

    Improved version of Sturges' formula which works better for
    non-normal data. See
    stats.stackexchange.com/questions/55134/doanes-formula-for-histogram-binning

    Parameters
    ----------
    x : array_like
        Input data that is to be histogrammed, trimmed to range. May not
        be empty.

    Returns
    -------
    h : An estimate of the optimal bin width for the given data.
    """
    del range  # unused
    if x.size > 2:
        sg1 = np.sqrt(6.0 * (x.size - 2) / ((x.size + 1.0) * (x.size + 3)))
        sigma = np.std(x)
        if sigma > 0.0:
            # These three operations add up to
            # g1 = np.mean(((x - np.mean(x)) / sigma)**3)
            # but use only one temp array instead of three
            temp = x - np.mean(x)
            np.true_divide(temp, sigma, temp)
            np.power(temp, 3, temp)
            g1 = np.mean(temp)
            return _ptp(x) / (1.0 + np.log2(x.size) +
                                    np.log2(1.0 + np.absolute(g1) / sg1))
    return 0.0


def _hist_bin_fd(x, range):
    """
    The Freedman-Diaconis histogram bin estimator.

    The Freedman-Diaconis rule uses interquartile range (IQR) to
    estimate binwidth. It is considered a variation of the Scott rule
    with more robustness as the IQR is less affected by outliers than
    the standard deviation. However, the IQR depends on fewer points
    than the standard deviation, so it is less accurate, especially for
    long tailed distributions.

    If the IQR is 0, this function returns 0 for the bin width.
    Binwidth is inversely proportional to the cube root of data size
    (asymptotically optimal).

    Parameters
    ----------
    x : array_like
        Input data that is to be histogrammed, trimmed to range. May not
        be empty.

    Returns
    -------
    h : An estimate of the optimal bin width for the given data.
    """
    del range  # unused
    iqr = np.subtract(*np.percentile(x, [75, 25]))
    return 2.0 * iqr * x.size ** (-1.0 / 3.0)


def _hist_bin_auto(x, range):
    """
    Histogram bin estimator that uses the minimum width of a relaxed
    Freedman-Diaconis and Sturges estimators if the FD bin width does
    not result in a large number of bins. The relaxed Freedman-Diaconis estimator
    limits the bin width to half the sqrt estimated to avoid small bins.

    The FD estimator is usually the most robust method, but its width
    estimate tends to be too large for small `x` and bad for data with limited
    variance. The Sturges estimator is quite good for small (<1000) datasets
    and is the default in the R language. This method gives good off-the-shelf
    behaviour.


    Parameters
    ----------
    x : array_like
        Input data that is to be histogrammed, trimmed to range. May not
        be empty.
    range : Tuple with range for the histogram

    Returns
    -------
    h : An estimate of the optimal bin width for the given data.

    See Also
    --------
    _hist_bin_fd, _hist_bin_sturges
    """
    fd_bw = _hist_bin_fd(x, range)
    sturges_bw = _hist_bin_sturges(x, range)
    sqrt_bw = _hist_bin_sqrt(x, range)
    # heuristic to limit the maximal number of bins
    fd_bw_corrected = max(fd_bw, sqrt_bw / 2)
    return min(fd_bw_corrected, sturges_bw)


# Private dict initialized at module load time
_hist_bin_selectors = {'stone': _hist_bin_stone,
                       'auto': _hist_bin_auto,
                       'doane': _hist_bin_doane,
                       'fd': _hist_bin_fd,
                       'rice': _hist_bin_rice,
                       'scott': _hist_bin_scott,
                       'sqrt': _hist_bin_sqrt,
                       'sturges': _hist_bin_sturges}


def _ravel_and_check_weights(a, weights):
    """ Check a and weights have matching shapes, and ravel both """
    a = np.asarray(a)

    # Ensure that the array is a "subtractable" dtype
    if a.dtype == np.bool:
        msg = f"Converting input from {a.dtype} to {np.uint8} for compatibility."
        warnings.warn(msg, RuntimeWarning, stacklevel=3)
        a = a.astype(np.uint8)

    if weights is not None:
        weights = np.asarray(weights)
        if weights.shape != a.shape:
            raise ValueError(
                'weights should have the same shape as a.')
        weights = weights.ravel()
    a = a.ravel()
    return a, weights


def _get_outer_edges(a, range):
    """
    Determine the outer bin edges to use, from either the data or the range
    argument
    """
    if range is not None:
        first_edge, last_edge = range
        if first_edge > last_edge:
            raise ValueError(
                'max must be larger than min in range parameter.')
        if not (np.isfinite(first_edge) and np.isfinite(last_edge)):
            raise ValueError(
                f"supplied range of [{first_edge}, {last_edge}] is not finite")
    elif a.size == 0:
        # handle empty arrays. Can't determine range, so use 0-1.
        first_edge, last_edge = 0, 1
    else:
        first_edge, last_edge = a.min(), a.max()
        if not (np.isfinite(first_edge) and np.isfinite(last_edge)):
            raise ValueError(
                f"autodetected range of [{first_edge}, {last_edge}] is not finite")

    # expand empty range to avoid divide by zero
    if first_edge == last_edge:
        first_edge = first_edge - 0.5
        last_edge = last_edge + 0.5

    return first_edge, last_edge


def _unsigned_subtract(a, b):
    """
    Subtract two values where a >= b, and produce an unsigned result

    This is needed when finding the difference between the upper and lower
    bound of an int16 histogram
    """
    # coerce to a single type
    signed_to_unsigned = {
        np.byte: np.ubyte,
        np.short: np.ushort,
        np.intc: np.uintc,
        np.int_: np.uint,
        np.longlong: np.ulonglong
    }
    dt = np.result_type(a, b)
    try:
        unsigned_dt = signed_to_unsigned[dt.type]
    except KeyError:
        return np.subtract(a, b, dtype=dt)
    else:
        # we know the inputs are integers, and we are deliberately casting
        # signed to unsigned.  The input may be negative python integers so
        # ensure we pass in arrays with the initial dtype (related to NEP 50).
        return np.subtract(np.asarray(a, dtype=dt), np.asarray(b, dtype=dt),
                           casting='unsafe', dtype=unsigned_dt)


def _get_bin_edges(a, bins, range, weights):
    """
    Computes the bins used internally by `histogram`.

    Parameters
    ==========
    a : ndarray
        Ravelled data array
    bins, range
        Forwarded arguments from `histogram`.
    weights : ndarray, optional
        Ravelled weights array, or None

    Returns
    =======
    bin_edges : ndarray
        Array of bin edges
    uniform_bins : (Number, Number, int):
        The upper bound, lowerbound, and number of bins, used in the optimized
        implementation of `histogram` that works on uniform bins.
    """
    # parse the overloaded bins argument
    n_equal_bins = None
    bin_edges = None

    if isinstance(bins, str):
        bin_name = bins
        # if `bins` is a string for an automatic method,
        # this will replace it with the number of bins calculated
        if bin_name not in _hist_bin_selectors:
            raise ValueError(
                f"{bin_name!r} is not a valid estimator for `bins`")
        if weights is not None:
            raise TypeError("Automated estimation of the number of "
                            "bins is not supported for weighted data")

        first_edge, last_edge = _get_outer_edges(a, range)

        # truncate the range if needed
        if range is not None:
            keep = (a >= first_edge)
            keep &= (a <= last_edge)
            if not np.logical_and.reduce(keep):
                a = a[keep]

        if a.size == 0:
            n_equal_bins = 1
        else:
            # Do not call selectors on empty arrays
            width = _hist_bin_selectors[bin_name](a, (first_edge, last_edge))
            if width:
                if np.issubdtype(a.dtype, np.integer) and width < 1:
                    width = 1
                delta = _unsigned_subtract(last_edge, first_edge)
                n_equal_bins = int(np.ceil(delta / width))
            else:
                # Width can be zero for some estimators, e.g. FD when
                # the IQR of the data is zero.
                n_equal_bins = 1

    elif np.ndim(bins) == 0:
        try:
            n_equal_bins = operator.index(bins)
        except TypeError as e:
            raise TypeError(
                '`bins` must be an integer, a string, or an array') from e
        if n_equal_bins < 1:
            raise ValueError('`bins` must be positive, when an integer')

        first_edge, last_edge = _get_outer_edges(a, range)

    elif np.ndim(bins) == 1:
        bin_edges = np.asarray(bins)
        if np.any(bin_edges[:-1] > bin_edges[1:]):
            raise ValueError(
                '`bins` must increase monotonically, when an array')

    else:
        raise ValueError('`bins` must be 1d, when an array')

    if n_equal_bins is not None:
        # gh-10322 means that type resolution rules are dependent on array
        # shapes. To avoid this causing problems, we pick a type now and stick
        # with it throughout.
        bin_type = np.result_type(first_edge, last_edge, a)
        if np.issubdtype(bin_type, np.integer):
            bin_type = np.result_type(bin_type, float)

        # bin edges must be computed
        bin_edges = np.linspace(
            first_edge, last_edge, n_equal_bins + 1,
            endpoint=True, dtype=bin_type)
        if np.any(bin_edges[:-1] >= bin_edges[1:]):
            raise ValueError(
                f'Too many bins for data range. Cannot create {n_equal_bins} '
                f'finite-sized bins.')
        return bin_edges, (first_edge, last_edge, n_equal_bins)
    else:
        return bin_edges, None


def _search_sorted_inclusive(a, v):
    """
    Like `searchsorted`, but where the last item in `v` is placed on the right.

    In the context of a histogram, this makes the last bin edge inclusive
    """
    return np.concatenate((
        a.searchsorted(v[:-1], 'left'),
        a.searchsorted(v[-1:], 'right')
    ))


def _histogram_bin_edges_dispatcher(a, bins=None, range=None, weights=None):
    return (a, bins, weights)


@array_function_dispatch(_histogram_bin_edges_dispatcher)
def histogram_bin_edges(a, bins=10, range=None, weights=None):
    r"""
    Function to calculate only the edges of the bins used by the `histogram`
    function.

    Parameters
    ----------
    a : array_like
        Input data. The histogram is computed over the flattened array.
    bins : int or sequence of scalars or str, optional
        If `bins` is an int, it defines the number of equal-width
        bins in the given range (10, by default). If `bins` is a
        sequence, it defines the bin edges, including the rightmost
        edge, allowing for non-uniform bin widths.

        If `bins` is a string from the list below, `histogram_bin_edges` will
        use the method chosen to calculate the optimal bin width and
        consequently the number of bins (see the Notes section for more detail
        on the estimators) from the data that falls within the requested range.
        While the bin width will be optimal for the actual data
        in the range, the number of bins will be computed to fill the
        entire range, including the empty portions. For visualisation,
        using the 'auto' option is suggested. Weighted data is not
        supported for automated bin size selection.

        'auto'
            Minimum bin width between the 'sturges' and 'fd' estimators.
            Provides good all-around performance.

        'fd' (Freedman Diaconis Estimator)
            Robust (resilient to outliers) estimator that takes into
            account data variability and data size.

        'doane'
            An improved version of Sturges' estimator that works better
            with non-normal datasets.

        'scott'
            Less robust estimator that takes into account data variability
            and data size.

        'stone'
            Estimator based on leave-one-out cross-validation estimate of
            the integrated squared error. Can be regarded as a generalization
            of Scott's rule.

        'rice'
            Estimator does not take variability into account, only data
            size. Commonly overestimates number of bins required.

        'sturges'
            R's default method, only accounts for data size. Only
            optimal for gaussian data and underestimates number of bins
            for large non-gaussian datasets.

        'sqrt'
            Square root (of data size) estimator, used by Excel and
            other programs for its speed and simplicity.

    range : (float, float), optional
        The lower and upper range of the bins.  If not provided, range
        is simply ``(a.min(), a.max())``.  Values outside the range are
        ignored. The first element of the range must be less than or
        equal to the second. `range` affects the automatic bin
        computation as well. While bin width is computed to be optimal
        based on the actual data within `range`, the bin count will fill
        the entire range including portions containing no data.

    weights : array_like, optional
        An array of weights, of the same shape as `a`.  Each value in
        `a` only contributes its associated weight towards the bin count
        (instead of 1). This is currently not used by any of the bin estimators,
        but may be in the future.

    Returns
    -------
    bin_edges : array of dtype float
        The edges to pass into `histogram`

    See Also
    --------
    histogram

    Notes
    -----
    The methods to estimate the optimal number of bins are well founded
    in literature, and are inspired by the choices R provides for
    histogram visualisation. Note that having the number of bins
    proportional to :math:`n^{1/3}` is asymptotically optimal, which is
    why it appears in most estimators. These are simply plug-in methods
    that give good starting points for number of bins. In the equations
    below, :math:`h` is the binwidth and :math:`n_h` is the number of
    bins. All estimators that compute bin counts are recast to bin width
    using the `ptp` of the data. The final bin count is obtained from
    ``np.round(np.ceil(range / h))``. The final bin width is often less
    than what is returned by the estimators below.

    'auto' (minimum bin width of the 'sturges' and 'fd' estimators)
        A compromise to get a good value. For small datasets the Sturges
        value will usually be chosen, while larger datasets will usually
        default to FD.  Avoids the overly conservative behaviour of FD
        and Sturges for small and large datasets respectively.
        Switchover point is usually :math:`a.size \approx 1000`.

    'fd' (Freedman Diaconis Estimator)
        .. math:: h = 2 \frac{IQR}{n^{1/3}}

        The binwidth is proportional to the interquartile range (IQR)
        and inversely proportional to cube root of a.size. Can be too
        conservative for small datasets, but is quite good for large
        datasets. The IQR is very robust to outliers.

    'scott'
        .. math:: h = \sigma \sqrt[3]{\frac{24 \sqrt{\pi}}{n}}

        The binwidth is proportional to the standard deviation of the
        data and inversely proportional to cube root of ``x.size``. Can
        be too conservative for small datasets, but is quite good for
        large datasets. The standard deviation is not very robust to
        outliers. Values are very similar to the Freedman-Diaconis
        estimator in the absence of outliers.

    'rice'
        .. math:: n_h = 2n^{1/3}

        The number of bins is only proportional to cube root of
        ``a.size``. It tends to overestimate the number of bins and it
        does not take into account data variability.

    'sturges'
        .. math:: n_h = \log _{2}(n) + 1

        The number of bins is the base 2 log of ``a.size``.  This
        estimator assumes normality of data and is too conservative for
        larger, non-normal datasets. This is the default method in R's
        ``hist`` method.

    'doane'
        .. math:: n_h = 1 + \log_{2}(n) +
                        \log_{2}\left(1 + \frac{|g_1|}{\sigma_{g_1}}\right)

            g_1 = mean\left[\left(\frac{x - \mu}{\sigma}\right)^3\right]

            \sigma_{g_1} = \sqrt{\frac{6(n - 2)}{(n + 1)(n + 3)}}

        An improved version of Sturges' formula that produces better
        estimates for non-normal datasets. This estimator attempts to
        account for the skew of the data.

    'sqrt'
        .. math:: n_h = \sqrt n

        The simplest and fastest estimator. Only takes into account the
        data size.

    Additionally, if the data is of integer dtype, then the binwidth will never
    be less than 1.

    Examples
    --------
    >>> import numpy as np
    >>> arr = np.array([0, 0, 0, 1, 2, 3, 3, 4, 5])
    >>> np.histogram_bin_edges(arr, bins='auto', range=(0, 1))
    array([0.  , 0.25, 0.5 , 0.75, 1.  ])
    >>> np.histogram_bin_edges(arr, bins=2)
    array([0. , 2.5, 5. ])

    For consistency with histogram, an array of pre-computed bins is
    passed through unmodified:

    >>> np.histogram_bin_edges(arr, [1, 2])
    array([1, 2])

    This function allows one set of bins to be computed, and reused across
    multiple histograms:

    >>> shared_bins = np.histogram_bin_edges(arr, bins='auto')
    >>> shared_bins
    array([0., 1., 2., 3., 4., 5.])

    >>> group_id = np.array([0, 1, 1, 0, 1, 1, 0, 1, 1])
    >>> hist_0, _ = np.histogram(arr[group_id == 0], bins=shared_bins)
    >>> hist_1, _ = np.histogram(arr[group_id == 1], bins=shared_bins)

    >>> hist_0; hist_1
    array([1, 1, 0, 1, 0])
    array([2, 0, 1, 1, 2])

    Which gives more easily comparable results than using separate bins for
    each histogram:

    >>> hist_0, bins_0 = np.histogram(arr[group_id == 0], bins='auto')
    >>> hist_1, bins_1 = np.histogram(arr[group_id == 1], bins='auto')
    >>> hist_0; hist_1
    array([1, 1, 1])
    array([2, 1, 1, 2])
    >>> bins_0; bins_1
    array([0., 1., 2., 3.])
    array([0.  , 1.25, 2.5 , 3.75, 5.  ])

    """
    a, weights = _ravel_and_check_weights(a, weights)
    bin_edges, _ = _get_bin_edges(a, bins, range, weights)
    return bin_edges


def _histogram_dispatcher(
        a, bins=None, range=None, density=None, weights=None):
    return (a, bins, weights)


@array_function_dispatch(_histogram_dispatcher)
def histogram(a, bins=10, range=None, density=None, weights=None):
    r"""
    Compute the histogram of a dataset.

    Parameters
    ----------
    a : array_like
        Input data. The histogram is computed over the flattened array.
    bins : int or sequence of scalars or str, optional
        If `bins` is an int, it defines the number of equal-width
        bins in the given range (10, by default). If `bins` is a
        sequence, it defines a monotonically increasing array of bin edges,
        including the rightmost edge, allowing for non-uniform bin widths.

        If `bins` is a string, it defines the method used to calculate the
        optimal bin width, as defined by `histogram_bin_edges`.

    range : (float, float), optional
        The lower and upper range of the bins.  If not provided, range
        is simply ``(a.min(), a.max())``.  Values outside the range are
        ignored. The first element of the range must be less than or
        equal to the second. `range` affects the automatic bin
        computation as well. While bin width is computed to be optimal
        based on the actual data within `range`, the bin count will fill
        the entire range including portions containing no data.
    weights : array_like, optional
        An array of weights, of the same shape as `a`.  Each value in
        `a` only contributes its associated weight towards the bin count
        (instead of 1). If `density` is True, the weights are
        normalized, so that the integral of the density over the range
        remains 1.
        Please note that the ``dtype`` of `weights` will also become the
        ``dtype`` of the returned accumulator (`hist`), so it must be
        large enough to hold accumulated values as well.
    density : bool, optional
        If ``False``, the result will contain the number of samples in
        each bin. If ``True``, the result is the value of the
        probability *density* function at the bin, normalized such that
        the *integral* over the range is 1. Note that the sum of the
        histogram values will not be equal to 1 unless bins of unity
        width are chosen; it is not a probability *mass* function.

    Returns
    -------
    hist : array
        The values of the histogram. See `density` and `weights` for a
        description of the possible semantics.  If `weights` are given,
        ``hist.dtype`` will be taken from `weights`.
    bin_edges : array of dtype float
        Return the bin edges ``(length(hist)+1)``.


    See Also
    --------
    histogramdd, bincount, searchsorted, digitize, histogram_bin_edges

    Notes
    -----
    All but the last (righthand-most) bin is half-open.  In other words,
    if `bins` is::

      [1, 2, 3, 4]

    then the first bin is ``[1, 2)`` (including 1, but excluding 2) and
    the second ``[2, 3)``.  The last bin, however, is ``[3, 4]``, which
    *includes* 4.


    Examples
    --------
    >>> import numpy as np
    >>> np.histogram([1, 2, 1], bins=[0, 1, 2, 3])
    (array([0, 2, 1]), array([0, 1, 2, 3]))
    >>> np.histogram(np.arange(4), bins=np.arange(5), density=True)
    (array([0.25, 0.25, 0.25, 0.25]), array([0, 1, 2, 3, 4]))
    >>> np.histogram([[1, 2, 1], [1, 0, 1]], bins=[0,1,2,3])
    (array([1, 4, 1]), array([0, 1, 2, 3]))

    >>> a = np.arange(5)
    >>> hist, bin_edges = np.histogram(a, density=True)
    >>> hist
    array([0.5, 0. , 0.5, 0. , 0. , 0.5, 0. , 0.5, 0. , 0.5])
    >>> hist.sum()
    2.4999999999999996
    >>> np.sum(hist * np.diff(bin_edges))
    1.0

    Automated Bin Selection Methods example, using 2 peak random data
    with 2000 points.

    .. plot::
        :include-source:

        import matplotlib.pyplot as plt
        import numpy as np

        rng = np.random.RandomState(10)  # deterministic random data
        a = np.hstack((rng.normal(size=1000),
                       rng.normal(loc=5, scale=2, size=1000)))
        plt.hist(a, bins='auto')  # arguments are passed to np.histogram
        plt.title("Histogram with 'auto' bins")
        plt.show()

    """
    a, weights = _ravel_and_check_weights(a, weights)

    bin_edges, uniform_bins = _get_bin_edges(a, bins, range, weights)

    # Histogram is an integer or a float array depending on the weights.
    if weights is None:
        ntype = np.dtype(np.intp)
    else:
        ntype = weights.dtype

    # We set a block size, as this allows us to iterate over chunks when
    # computing histograms, to minimize memory usage.
    BLOCK = 65536

    # The fast path uses bincount, but that only works for certain types
    # of weight
    simple_weights = (
        weights is None or
        np.can_cast(weights.dtype, np.double) or
        np.can_cast(weights.dtype, complex)
    )

    if uniform_bins is not None and simple_weights:
        # Fast algorithm for equal bins
        # We now convert values of a to bin indices, under the assumption of
        # equal bin widths (which is valid here).
        first_edge, last_edge, n_equal_bins = uniform_bins

        # Initialize empty histogram
        n = np.zeros(n_equal_bins, ntype)

        # Pre-compute histogram scaling factor
        norm_numerator = n_equal_bins
        norm_denom = _unsigned_subtract(last_edge, first_edge)

        # We iterate over blocks here for two reasons: the first is that for
        # large arrays, it is actually faster (for example for a 10^8 array it
        # is 2x as fast) and it results in a memory footprint 3x lower in the
        # limit of large arrays.
        for i in _range(0, len(a), BLOCK):
            tmp_a = a[i:i + BLOCK]
            if weights is None:
                tmp_w = None
            else:
                tmp_w = weights[i:i + BLOCK]

            # Only include values in the right range
            keep = (tmp_a >= first_edge)
            keep &= (tmp_a <= last_edge)
            if not np.logical_and.reduce(keep):
                tmp_a = tmp_a[keep]
                if tmp_w is not None:
                    tmp_w = tmp_w[keep]

            # This cast ensures no type promotions occur below, which gh-10322
            # make unpredictable. Getting it wrong leads to precision errors
            # like gh-8123.
            tmp_a = tmp_a.astype(bin_edges.dtype, copy=False)

            # Compute the bin indices, and for values that lie exactly on
            # last_edge we need to subtract one
            f_indices = ((_unsigned_subtract(tmp_a, first_edge) / norm_denom)
                         * norm_numerator)
            indices = f_indices.astype(np.intp)
            indices[indices == n_equal_bins] -= 1

            # The index computation is not guaranteed to give exactly
            # consistent results within ~1 ULP of the bin edges.
            decrement = tmp_a < bin_edges[indices]
            indices[decrement] -= 1
            # The last bin includes the right edge. The other bins do not.
            increment = ((tmp_a >= bin_edges[indices + 1])
                         & (indices != n_equal_bins - 1))
            indices[increment] += 1

            # We now compute the histogram using bincount
            if ntype.kind == 'c':
                n.real += np.bincount(indices, weights=tmp_w.real,
                                      minlength=n_equal_bins)
                n.imag += np.bincount(indices, weights=tmp_w.imag,
                                      minlength=n_equal_bins)
            else:
                n += np.bincount(indices, weights=tmp_w,
                                 minlength=n_equal_bins).astype(ntype)
    else:
        # Compute via cumulative histogram
        cum_n = np.zeros(bin_edges.shape, ntype)
        if weights is None:
            for i in _range(0, len(a), BLOCK):
                sa = np.sort(a[i:i + BLOCK])
                cum_n += _search_sorted_inclusive(sa, bin_edges)
        else:
            zero = np.zeros(1, dtype=ntype)
            for i in _range(0, len(a), BLOCK):
                tmp_a = a[i:i + BLOCK]
                tmp_w = weights[i:i + BLOCK]
                sorting_index = np.argsort(tmp_a)
                sa = tmp_a[sorting_index]
                sw = tmp_w[sorting_index]
                cw = np.concatenate((zero, sw.cumsum()))
                bin_index = _search_sorted_inclusive(sa, bin_edges)
                cum_n += cw[bin_index]

        n = np.diff(cum_n)

    if density:
        db = np.array(np.diff(bin_edges), float)
        return n / db / n.sum(), bin_edges

    return n, bin_edges


def _histogramdd_dispatcher(sample, bins=None, range=None, density=None,
                            weights=None):
    if hasattr(sample, 'shape'):  # same condition as used in histogramdd
        yield sample
    else:
        yield from sample
    with contextlib.suppress(TypeError):
        yield from bins
    yield weights


@array_function_dispatch(_histogramdd_dispatcher)
def histogramdd(sample, bins=10, range=None, density=None, weights=None):
    """
    Compute the multidimensional histogram of some data.

    Parameters
    ----------
    sample : (N, D) array, or (N, D) array_like
        The data to be histogrammed.

        Note the unusual interpretation of sample when an array_like:

        * When an array, each row is a coordinate in a D-dimensional space -
          such as ``histogramdd(np.array([p1, p2, p3]))``.
        * When an array_like, each element is the list of values for single
          coordinate - such as ``histogramdd((X, Y, Z))``.

        The first form should be preferred.

    bins : sequence or int, optional
        The bin specification:

        * A sequence of arrays describing the monotonically increasing bin
          edges along each dimension.
        * The number of bins for each dimension (nx, ny, ... =bins)
        * The number of bins for all dimensions (nx=ny=...=bins).

    range : sequence, optional
        A sequence of length D, each an optional (lower, upper) tuple giving
        the outer bin edges to be used if the edges are not given explicitly in
        `bins`.
        An entry of None in the sequence results in the minimum and maximum
        values being used for the corresponding dimension.
        The default, None, is equivalent to passing a tuple of D None values.
    density : bool, optional
        If False, the default, returns the number of samples in each bin.
        If True, returns the probability *density* function at the bin,
        ``bin_count / sample_count / bin_volume``.
    weights : (N,) array_like, optional
        An array of values `w_i` weighing each sample `(x_i, y_i, z_i, ...)`.
        Weights are normalized to 1 if density is True. If density is False,
        the values of the returned histogram are equal to the sum of the
        weights belonging to the samples falling into each bin.

    Returns
    -------
    H : ndarray
        The multidimensional histogram of sample x. See density and weights
        for the different possible semantics.
    edges : tuple of ndarrays
        A tuple of D arrays describing the bin edges for each dimension.

    See Also
    --------
    histogram: 1-D histogram
    histogram2d: 2-D histogram

    Examples
    --------
    >>> import numpy as np
    >>> rng = np.random.default_rng()
    >>> r = rng.normal(size=(100,3))
    >>> H, edges = np.histogramdd(r, bins = (5, 8, 4))
    >>> H.shape, edges[0].size, edges[1].size, edges[2].size
    ((5, 8, 4), 6, 9, 5)

    """

    try:
        # Sample is an ND-array.
        N, D = sample.shape
    except (AttributeError, ValueError):
        # Sample is a sequence of 1D arrays.
        sample = np.atleast_2d(sample).T
        N, D = sample.shape

    nbin = np.empty(D, np.intp)
    edges = D * [None]
    dedges = D * [None]
    if weights is not None:
        weights = np.asarray(weights)

    try:
        M = len(bins)
        if M != D:
            raise ValueError(
                'The dimension of bins must be equal to the dimension of the '
                'sample x.')
    except TypeError:
        # bins is an integer
        bins = D * [bins]

    # normalize the range argument
    if range is None:
        range = (None,) * D
    elif len(range) != D:
        raise ValueError('range argument must have one entry per dimension')

    # Create edge arrays
    for i in _range(D):
        if np.ndim(bins[i]) == 0:
            if bins[i] < 1:
                raise ValueError(
                    f'`bins[{i}]` must be positive, when an integer')
            smin, smax = _get_outer_edges(sample[:, i], range[i])
            try:
                n = operator.index(bins[i])

            except TypeError as e:
                raise TypeError(
                    f"`bins[{i}]` must be an integer, when a scalar"
                ) from e

            edges[i] = np.linspace(smin, smax, n + 1)
        elif np.ndim(bins[i]) == 1:
            edges[i] = np.asarray(bins[i])
            if np.any(edges[i][:-1] > edges[i][1:]):
                raise ValueError(
                    f'`bins[{i}]` must be monotonically increasing, when an array')
        else:
            raise ValueError(
                f'`bins[{i}]` must be a scalar or 1d array')

        nbin[i] = len(edges[i]) + 1  # includes an outlier on each end
        dedges[i] = np.diff(edges[i])

    # Compute the bin number each sample falls into.
    Ncount = tuple(
        # avoid np.digitize to work around gh-11022
        np.searchsorted(edges[i], sample[:, i], side='right')
        for i in _range(D)
    )

    # Using digitize, values that fall on an edge are put in the right bin.
    # For the rightmost bin, we want values equal to the right edge to be
    # counted in the last bin, and not as an outlier.
    for i in _range(D):
        # Find which points are on the rightmost edge.
        on_edge = (sample[:, i] == edges[i][-1])
        # Shift these points one bin to the left.
        Ncount[i][on_edge] -= 1

    # Compute the sample indices in the flattened histogram matrix.
    # This raises an error if the array is too large.
    xy = np.ravel_multi_index(Ncount, nbin)

    # Compute the number of repetitions in xy and assign it to the
    # flattened histmat.
    hist = np.bincount(xy, weights, minlength=nbin.prod())

    # Shape into a proper matrix
    hist = hist.reshape(nbin)

    # This preserves the (bad) behavior observed in gh-7845, for now.
    hist = hist.astype(float, casting='safe')

    # Remove outliers (indices 0 and -1 for each dimension).
    core = D * (slice(1, -1),)
    hist = hist[core]

    if density:
        # calculate the probability density function
        s = hist.sum()
        for i in _range(D):
            shape = np.ones(D, int)
            shape[i] = nbin[i] - 2
            hist = hist / dedges[i].reshape(shape)
        hist /= s

    if (hist.shape != nbin - 2).any():
        raise RuntimeError(
            "Internal Shape Error")
    return hist, edges

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\_histograms_impl.py ===
"""
Histogram-related functions
"""
import contextlib
import functools
import operator
import warnings

import numpy as np
from numpy._core import overrides

__all__ = ['histogram', 'histogramdd', 'histogram_bin_edges']

array_function_dispatch = functools.partial(
    overrides.array_function_dispatch, module='numpy')

# range is a keyword argument to many functions, so save the builtin so they can
# use it.
_range = range


def _ptp(x):
    """Peak-to-peak value of x.

    This implementation avoids the problem of signed integer arrays having a
    peak-to-peak value that cannot be represented with the array's data type.
    This function returns an unsigned value for signed integer arrays.
    """
    return _unsigned_subtract(x.max(), x.min())


def _hist_bin_sqrt(x, range):
    """
    Square root histogram bin estimator.

    Bin width is inversely proportional to the data size. Used by many
    programs for its simplicity.

    Parameters
    ----------
    x : array_like
        Input data that is to be histogrammed, trimmed to range. May not
        be empty.

    Returns
    -------
    h : An estimate of the optimal bin width for the given data.
    """
    del range  # unused
    return _ptp(x) / np.sqrt(x.size)


def _hist_bin_sturges(x, range):
    """
    Sturges histogram bin estimator.

    A very simplistic estimator based on the assumption of normality of
    the data. This estimator has poor performance for non-normal data,
    which becomes especially obvious for large data sets. The estimate
    depends only on size of the data.

    Parameters
    ----------
    x : array_like
        Input data that is to be histogrammed, trimmed to range. May not
        be empty.

    Returns
    -------
    h : An estimate of the optimal bin width for the given data.
    """
    del range  # unused
    return _ptp(x) / (np.log2(x.size) + 1.0)


def _hist_bin_rice(x, range):
    """
    Rice histogram bin estimator.

    Another simple estimator with no normality assumption. It has better
    performance for large data than Sturges, but tends to overestimate
    the number of bins. The number of bins is proportional to the cube
    root of data size (asymptotically optimal). The estimate depends
    only on size of the data.

    Parameters
    ----------
    x : array_like
        Input data that is to be histogrammed, trimmed to range. May not
        be empty.

    Returns
    -------
    h : An estimate of the optimal bin width for the given data.
    """
    del range  # unused
    return _ptp(x) / (2.0 * x.size ** (1.0 / 3))


def _hist_bin_scott(x, range):
    """
    Scott histogram bin estimator.

    The binwidth is proportional to the standard deviation of the data
    and inversely proportional to the cube root of data size
    (asymptotically optimal).

    Parameters
    ----------
    x : array_like
        Input data that is to be histogrammed, trimmed to range. May not
        be empty.

    Returns
    -------
    h : An estimate of the optimal bin width for the given data.
    """
    del range  # unused
    return (24.0 * np.pi**0.5 / x.size)**(1.0 / 3.0) * np.std(x)


def _hist_bin_stone(x, range):
    """
    Histogram bin estimator based on minimizing the estimated integrated squared error (ISE).

    The number of bins is chosen by minimizing the estimated ISE against the unknown
    true distribution. The ISE is estimated using cross-validation and can be regarded
    as a generalization of Scott's rule.
    https://en.wikipedia.org/wiki/Histogram#Scott.27s_normal_reference_rule

    This paper by Stone appears to be the origination of this rule.
    https://digitalassets.lib.berkeley.edu/sdtr/ucb/text/34.pdf

    Parameters
    ----------
    x : array_like
        Input data that is to be histogrammed, trimmed to range. May not
        be empty.
    range : (float, float)
        The lower and upper range of the bins.

    Returns
    -------
    h : An estimate of the optimal bin width for the given data.
    """  # noqa: E501

    n = x.size
    ptp_x = _ptp(x)
    if n <= 1 or ptp_x == 0:
        return 0

    def jhat(nbins):
        hh = ptp_x / nbins
        p_k = np.histogram(x, bins=nbins, range=range)[0] / n
        return (2 - (n + 1) * p_k.dot(p_k)) / hh

    nbins_upper_bound = max(100, int(np.sqrt(n)))
    nbins = min(_range(1, nbins_upper_bound + 1), key=jhat)
    if nbins == nbins_upper_bound:
        warnings.warn("The number of bins estimated may be suboptimal.",
                      RuntimeWarning, stacklevel=3)
    return ptp_x / nbins


def _hist_bin_doane(x, range):
    """
    Doane's histogram bin estimator.

    Improved version of Sturges' formula which works better for
    non-normal data. See
    stats.stackexchange.com/questions/55134/doanes-formula-for-histogram-binning

    Parameters
    ----------
    x : array_like
        Input data that is to be histogrammed, trimmed to range. May not
        be empty.

    Returns
    -------
    h : An estimate of the optimal bin width for the given data.
    """
    del range  # unused
    if x.size > 2:
        sg1 = np.sqrt(6.0 * (x.size - 2) / ((x.size + 1.0) * (x.size + 3)))
        sigma = np.std(x)
        if sigma > 0.0:
            # These three operations add up to
            # g1 = np.mean(((x - np.mean(x)) / sigma)**3)
            # but use only one temp array instead of three
            temp = x - np.mean(x)
            np.true_divide(temp, sigma, temp)
            np.power(temp, 3, temp)
            g1 = np.mean(temp)
            return _ptp(x) / (1.0 + np.log2(x.size) +
                                    np.log2(1.0 + np.absolute(g1) / sg1))
    return 0.0


def _hist_bin_fd(x, range):
    """
    The Freedman-Diaconis histogram bin estimator.

    The Freedman-Diaconis rule uses interquartile range (IQR) to
    estimate binwidth. It is considered a variation of the Scott rule
    with more robustness as the IQR is less affected by outliers than
    the standard deviation. However, the IQR depends on fewer points
    than the standard deviation, so it is less accurate, especially for
    long tailed distributions.

    If the IQR is 0, this function returns 0 for the bin width.
    Binwidth is inversely proportional to the cube root of data size
    (asymptotically optimal).

    Parameters
    ----------
    x : array_like
        Input data that is to be histogrammed, trimmed to range. May not
        be empty.

    Returns
    -------
    h : An estimate of the optimal bin width for the given data.
    """
    del range  # unused
    iqr = np.subtract(*np.percentile(x, [75, 25]))
    return 2.0 * iqr * x.size ** (-1.0 / 3.0)


def _hist_bin_auto(x, range):
    """
    Histogram bin estimator that uses the minimum width of a relaxed
    Freedman-Diaconis and Sturges estimators if the FD bin width does
    not result in a large number of bins. The relaxed Freedman-Diaconis estimator
    limits the bin width to half the sqrt estimated to avoid small bins.

    The FD estimator is usually the most robust method, but its width
    estimate tends to be too large for small `x` and bad for data with limited
    variance. The Sturges estimator is quite good for small (<1000) datasets
    and is the default in the R language. This method gives good off-the-shelf
    behaviour.


    Parameters
    ----------
    x : array_like
        Input data that is to be histogrammed, trimmed to range. May not
        be empty.
    range : Tuple with range for the histogram

    Returns
    -------
    h : An estimate of the optimal bin width for the given data.

    See Also
    --------
    _hist_bin_fd, _hist_bin_sturges
    """
    fd_bw = _hist_bin_fd(x, range)
    sturges_bw = _hist_bin_sturges(x, range)
    sqrt_bw = _hist_bin_sqrt(x, range)
    # heuristic to limit the maximal number of bins
    fd_bw_corrected = max(fd_bw, sqrt_bw / 2)
    return min(fd_bw_corrected, sturges_bw)


# Private dict initialized at module load time
_hist_bin_selectors = {'stone': _hist_bin_stone,
                       'auto': _hist_bin_auto,
                       'doane': _hist_bin_doane,
                       'fd': _hist_bin_fd,
                       'rice': _hist_bin_rice,
                       'scott': _hist_bin_scott,
                       'sqrt': _hist_bin_sqrt,
                       'sturges': _hist_bin_sturges}


def _ravel_and_check_weights(a, weights):
    """ Check a and weights have matching shapes, and ravel both """
    a = np.asarray(a)

    # Ensure that the array is a "subtractable" dtype
    if a.dtype == np.bool:
        msg = f"Converting input from {a.dtype} to {np.uint8} for compatibility."
        warnings.warn(msg, RuntimeWarning, stacklevel=3)
        a = a.astype(np.uint8)

    if weights is not None:
        weights = np.asarray(weights)
        if weights.shape != a.shape:
            raise ValueError(
                'weights should have the same shape as a.')
        weights = weights.ravel()
    a = a.ravel()
    return a, weights


def _get_outer_edges(a, range):
    """
    Determine the outer bin edges to use, from either the data or the range
    argument
    """
    if range is not None:
        first_edge, last_edge = range
        if first_edge > last_edge:
            raise ValueError(
                'max must be larger than min in range parameter.')
        if not (np.isfinite(first_edge) and np.isfinite(last_edge)):
            raise ValueError(
                f"supplied range of [{first_edge}, {last_edge}] is not finite")
    elif a.size == 0:
        # handle empty arrays. Can't determine range, so use 0-1.
        first_edge, last_edge = 0, 1
    else:
        first_edge, last_edge = a.min(), a.max()
        if not (np.isfinite(first_edge) and np.isfinite(last_edge)):
            raise ValueError(
                f"autodetected range of [{first_edge}, {last_edge}] is not finite")

    # expand empty range to avoid divide by zero
    if first_edge == last_edge:
        first_edge = first_edge - 0.5
        last_edge = last_edge + 0.5

    return first_edge, last_edge


def _unsigned_subtract(a, b):
    """
    Subtract two values where a >= b, and produce an unsigned result

    This is needed when finding the difference between the upper and lower
    bound of an int16 histogram
    """
    # coerce to a single type
    signed_to_unsigned = {
        np.byte: np.ubyte,
        np.short: np.ushort,
        np.intc: np.uintc,
        np.int_: np.uint,
        np.longlong: np.ulonglong
    }
    dt = np.result_type(a, b)
    try:
        unsigned_dt = signed_to_unsigned[dt.type]
    except KeyError:
        return np.subtract(a, b, dtype=dt)
    else:
        # we know the inputs are integers, and we are deliberately casting
        # signed to unsigned.  The input may be negative python integers so
        # ensure we pass in arrays with the initial dtype (related to NEP 50).
        return np.subtract(np.asarray(a, dtype=dt), np.asarray(b, dtype=dt),
                           casting='unsafe', dtype=unsigned_dt)


def _get_bin_edges(a, bins, range, weights):
    """
    Computes the bins used internally by `histogram`.

    Parameters
    ==========
    a : ndarray
        Ravelled data array
    bins, range
        Forwarded arguments from `histogram`.
    weights : ndarray, optional
        Ravelled weights array, or None

    Returns
    =======
    bin_edges : ndarray
        Array of bin edges
    uniform_bins : (Number, Number, int):
        The upper bound, lowerbound, and number of bins, used in the optimized
        implementation of `histogram` that works on uniform bins.
    """
    # parse the overloaded bins argument
    n_equal_bins = None
    bin_edges = None

    if isinstance(bins, str):
        bin_name = bins
        # if `bins` is a string for an automatic method,
        # this will replace it with the number of bins calculated
        if bin_name not in _hist_bin_selectors:
            raise ValueError(
                f"{bin_name!r} is not a valid estimator for `bins`")
        if weights is not None:
            raise TypeError("Automated estimation of the number of "
                            "bins is not supported for weighted data")

        first_edge, last_edge = _get_outer_edges(a, range)

        # truncate the range if needed
        if range is not None:
            keep = (a >= first_edge)
            keep &= (a <= last_edge)
            if not np.logical_and.reduce(keep):
                a = a[keep]

        if a.size == 0:
            n_equal_bins = 1
        else:
            # Do not call selectors on empty arrays
            width = _hist_bin_selectors[bin_name](a, (first_edge, last_edge))
            if width:
                if np.issubdtype(a.dtype, np.integer) and width < 1:
                    width = 1
                delta = _unsigned_subtract(last_edge, first_edge)
                n_equal_bins = int(np.ceil(delta / width))
            else:
                # Width can be zero for some estimators, e.g. FD when
                # the IQR of the data is zero.
                n_equal_bins = 1

    elif np.ndim(bins) == 0:
        try:
            n_equal_bins = operator.index(bins)
        except TypeError as e:
            raise TypeError(
                '`bins` must be an integer, a string, or an array') from e
        if n_equal_bins < 1:
            raise ValueError('`bins` must be positive, when an integer')

        first_edge, last_edge = _get_outer_edges(a, range)

    elif np.ndim(bins) == 1:
        bin_edges = np.asarray(bins)
        if np.any(bin_edges[:-1] > bin_edges[1:]):
            raise ValueError(
                '`bins` must increase monotonically, when an array')

    else:
        raise ValueError('`bins` must be 1d, when an array')

    if n_equal_bins is not None:
        # gh-10322 means that type resolution rules are dependent on array
        # shapes. To avoid this causing problems, we pick a type now and stick
        # with it throughout.
        bin_type = np.result_type(first_edge, last_edge, a)
        if np.issubdtype(bin_type, np.integer):
            bin_type = np.result_type(bin_type, float)

        # bin edges must be computed
        bin_edges = np.linspace(
            first_edge, last_edge, n_equal_bins + 1,
            endpoint=True, dtype=bin_type)
        if np.any(bin_edges[:-1] >= bin_edges[1:]):
            raise ValueError(
                f'Too many bins for data range. Cannot create {n_equal_bins} '
                f'finite-sized bins.')
        return bin_edges, (first_edge, last_edge, n_equal_bins)
    else:
        return bin_edges, None


def _search_sorted_inclusive(a, v):
    """
    Like `searchsorted`, but where the last item in `v` is placed on the right.

    In the context of a histogram, this makes the last bin edge inclusive
    """
    return np.concatenate((
        a.searchsorted(v[:-1], 'left'),
        a.searchsorted(v[-1:], 'right')
    ))


def _histogram_bin_edges_dispatcher(a, bins=None, range=None, weights=None):
    return (a, bins, weights)


@array_function_dispatch(_histogram_bin_edges_dispatcher)
def histogram_bin_edges(a, bins=10, range=None, weights=None):
    r"""
    Function to calculate only the edges of the bins used by the `histogram`
    function.

    Parameters
    ----------
    a : array_like
        Input data. The histogram is computed over the flattened array.
    bins : int or sequence of scalars or str, optional
        If `bins` is an int, it defines the number of equal-width
        bins in the given range (10, by default). If `bins` is a
        sequence, it defines the bin edges, including the rightmost
        edge, allowing for non-uniform bin widths.

        If `bins` is a string from the list below, `histogram_bin_edges` will
        use the method chosen to calculate the optimal bin width and
        consequently the number of bins (see the Notes section for more detail
        on the estimators) from the data that falls within the requested range.
        While the bin width will be optimal for the actual data
        in the range, the number of bins will be computed to fill the
        entire range, including the empty portions. For visualisation,
        using the 'auto' option is suggested. Weighted data is not
        supported for automated bin size selection.

        'auto'
            Minimum bin width between the 'sturges' and 'fd' estimators.
            Provides good all-around performance.

        'fd' (Freedman Diaconis Estimator)
            Robust (resilient to outliers) estimator that takes into
            account data variability and data size.

        'doane'
            An improved version of Sturges' estimator that works better
            with non-normal datasets.

        'scott'
            Less robust estimator that takes into account data variability
            and data size.

        'stone'
            Estimator based on leave-one-out cross-validation estimate of
            the integrated squared error. Can be regarded as a generalization
            of Scott's rule.

        'rice'
            Estimator does not take variability into account, only data
            size. Commonly overestimates number of bins required.

        'sturges'
            R's default method, only accounts for data size. Only
            optimal for gaussian data and underestimates number of bins
            for large non-gaussian datasets.

        'sqrt'
            Square root (of data size) estimator, used by Excel and
            other programs for its speed and simplicity.

    range : (float, float), optional
        The lower and upper range of the bins.  If not provided, range
        is simply ``(a.min(), a.max())``.  Values outside the range are
        ignored. The first element of the range must be less than or
        equal to the second. `range` affects the automatic bin
        computation as well. While bin width is computed to be optimal
        based on the actual data within `range`, the bin count will fill
        the entire range including portions containing no data.

    weights : array_like, optional
        An array of weights, of the same shape as `a`.  Each value in
        `a` only contributes its associated weight towards the bin count
        (instead of 1). This is currently not used by any of the bin estimators,
        but may be in the future.

    Returns
    -------
    bin_edges : array of dtype float
        The edges to pass into `histogram`

    See Also
    --------
    histogram

    Notes
    -----
    The methods to estimate the optimal number of bins are well founded
    in literature, and are inspired by the choices R provides for
    histogram visualisation. Note that having the number of bins
    proportional to :math:`n^{1/3}` is asymptotically optimal, which is
    why it appears in most estimators. These are simply plug-in methods
    that give good starting points for number of bins. In the equations
    below, :math:`h` is the binwidth and :math:`n_h` is the number of
    bins. All estimators that compute bin counts are recast to bin width
    using the `ptp` of the data. The final bin count is obtained from
    ``np.round(np.ceil(range / h))``. The final bin width is often less
    than what is returned by the estimators below.

    'auto' (minimum bin width of the 'sturges' and 'fd' estimators)
        A compromise to get a good value. For small datasets the Sturges
        value will usually be chosen, while larger datasets will usually
        default to FD.  Avoids the overly conservative behaviour of FD
        and Sturges for small and large datasets respectively.
        Switchover point is usually :math:`a.size \approx 1000`.

    'fd' (Freedman Diaconis Estimator)
        .. math:: h = 2 \frac{IQR}{n^{1/3}}

        The binwidth is proportional to the interquartile range (IQR)
        and inversely proportional to cube root of a.size. Can be too
        conservative for small datasets, but is quite good for large
        datasets. The IQR is very robust to outliers.

    'scott'
        .. math:: h = \sigma \sqrt[3]{\frac{24 \sqrt{\pi}}{n}}

        The binwidth is proportional to the standard deviation of the
        data and inversely proportional to cube root of ``x.size``. Can
        be too conservative for small datasets, but is quite good for
        large datasets. The standard deviation is not very robust to
        outliers. Values are very similar to the Freedman-Diaconis
        estimator in the absence of outliers.

    'rice'
        .. math:: n_h = 2n^{1/3}

        The number of bins is only proportional to cube root of
        ``a.size``. It tends to overestimate the number of bins and it
        does not take into account data variability.

    'sturges'
        .. math:: n_h = \log _{2}(n) + 1

        The number of bins is the base 2 log of ``a.size``.  This
        estimator assumes normality of data and is too conservative for
        larger, non-normal datasets. This is the default method in R's
        ``hist`` method.

    'doane'
        .. math:: n_h = 1 + \log_{2}(n) +
                        \log_{2}\left(1 + \frac{|g_1|}{\sigma_{g_1}}\right)

            g_1 = mean\left[\left(\frac{x - \mu}{\sigma}\right)^3\right]

            \sigma_{g_1} = \sqrt{\frac{6(n - 2)}{(n + 1)(n + 3)}}

        An improved version of Sturges' formula that produces better
        estimates for non-normal datasets. This estimator attempts to
        account for the skew of the data.

    'sqrt'
        .. math:: n_h = \sqrt n

        The simplest and fastest estimator. Only takes into account the
        data size.

    Additionally, if the data is of integer dtype, then the binwidth will never
    be less than 1.

    Examples
    --------
    >>> import numpy as np
    >>> arr = np.array([0, 0, 0, 1, 2, 3, 3, 4, 5])
    >>> np.histogram_bin_edges(arr, bins='auto', range=(0, 1))
    array([0.  , 0.25, 0.5 , 0.75, 1.  ])
    >>> np.histogram_bin_edges(arr, bins=2)
    array([0. , 2.5, 5. ])

    For consistency with histogram, an array of pre-computed bins is
    passed through unmodified:

    >>> np.histogram_bin_edges(arr, [1, 2])
    array([1, 2])

    This function allows one set of bins to be computed, and reused across
    multiple histograms:

    >>> shared_bins = np.histogram_bin_edges(arr, bins='auto')
    >>> shared_bins
    array([0., 1., 2., 3., 4., 5.])

    >>> group_id = np.array([0, 1, 1, 0, 1, 1, 0, 1, 1])
    >>> hist_0, _ = np.histogram(arr[group_id == 0], bins=shared_bins)
    >>> hist_1, _ = np.histogram(arr[group_id == 1], bins=shared_bins)

    >>> hist_0; hist_1
    array([1, 1, 0, 1, 0])
    array([2, 0, 1, 1, 2])

    Which gives more easily comparable results than using separate bins for
    each histogram:

    >>> hist_0, bins_0 = np.histogram(arr[group_id == 0], bins='auto')
    >>> hist_1, bins_1 = np.histogram(arr[group_id == 1], bins='auto')
    >>> hist_0; hist_1
    array([1, 1, 1])
    array([2, 1, 1, 2])
    >>> bins_0; bins_1
    array([0., 1., 2., 3.])
    array([0.  , 1.25, 2.5 , 3.75, 5.  ])

    """
    a, weights = _ravel_and_check_weights(a, weights)
    bin_edges, _ = _get_bin_edges(a, bins, range, weights)
    return bin_edges


def _histogram_dispatcher(
        a, bins=None, range=None, density=None, weights=None):
    return (a, bins, weights)


@array_function_dispatch(_histogram_dispatcher)
def histogram(a, bins=10, range=None, density=None, weights=None):
    r"""
    Compute the histogram of a dataset.

    Parameters
    ----------
    a : array_like
        Input data. The histogram is computed over the flattened array.
    bins : int or sequence of scalars or str, optional
        If `bins` is an int, it defines the number of equal-width
        bins in the given range (10, by default). If `bins` is a
        sequence, it defines a monotonically increasing array of bin edges,
        including the rightmost edge, allowing for non-uniform bin widths.

        If `bins` is a string, it defines the method used to calculate the
        optimal bin width, as defined by `histogram_bin_edges`.

    range : (float, float), optional
        The lower and upper range of the bins.  If not provided, range
        is simply ``(a.min(), a.max())``.  Values outside the range are
        ignored. The first element of the range must be less than or
        equal to the second. `range` affects the automatic bin
        computation as well. While bin width is computed to be optimal
        based on the actual data within `range`, the bin count will fill
        the entire range including portions containing no data.
    weights : array_like, optional
        An array of weights, of the same shape as `a`.  Each value in
        `a` only contributes its associated weight towards the bin count
        (instead of 1). If `density` is True, the weights are
        normalized, so that the integral of the density over the range
        remains 1.
        Please note that the ``dtype`` of `weights` will also become the
        ``dtype`` of the returned accumulator (`hist`), so it must be
        large enough to hold accumulated values as well.
    density : bool, optional
        If ``False``, the result will contain the number of samples in
        each bin. If ``True``, the result is the value of the
        probability *density* function at the bin, normalized such that
        the *integral* over the range is 1. Note that the sum of the
        histogram values will not be equal to 1 unless bins of unity
        width are chosen; it is not a probability *mass* function.

    Returns
    -------
    hist : array
        The values of the histogram. See `density` and `weights` for a
        description of the possible semantics.  If `weights` are given,
        ``hist.dtype`` will be taken from `weights`.
    bin_edges : array of dtype float
        Return the bin edges ``(length(hist)+1)``.


    See Also
    --------
    histogramdd, bincount, searchsorted, digitize, histogram_bin_edges

    Notes
    -----
    All but the last (righthand-most) bin is half-open.  In other words,
    if `bins` is::

      [1, 2, 3, 4]

    then the first bin is ``[1, 2)`` (including 1, but excluding 2) and
    the second ``[2, 3)``.  The last bin, however, is ``[3, 4]``, which
    *includes* 4.


    Examples
    --------
    >>> import numpy as np
    >>> np.histogram([1, 2, 1], bins=[0, 1, 2, 3])
    (array([0, 2, 1]), array([0, 1, 2, 3]))
    >>> np.histogram(np.arange(4), bins=np.arange(5), density=True)
    (array([0.25, 0.25, 0.25, 0.25]), array([0, 1, 2, 3, 4]))
    >>> np.histogram([[1, 2, 1], [1, 0, 1]], bins=[0,1,2,3])
    (array([1, 4, 1]), array([0, 1, 2, 3]))

    >>> a = np.arange(5)
    >>> hist, bin_edges = np.histogram(a, density=True)
    >>> hist
    array([0.5, 0. , 0.5, 0. , 0. , 0.5, 0. , 0.5, 0. , 0.5])
    >>> hist.sum()
    2.4999999999999996
    >>> np.sum(hist * np.diff(bin_edges))
    1.0

    Automated Bin Selection Methods example, using 2 peak random data
    with 2000 points.

    .. plot::
        :include-source:

        import matplotlib.pyplot as plt
        import numpy as np

        rng = np.random.RandomState(10)  # deterministic random data
        a = np.hstack((rng.normal(size=1000),
                       rng.normal(loc=5, scale=2, size=1000)))
        plt.hist(a, bins='auto')  # arguments are passed to np.histogram
        plt.title("Histogram with 'auto' bins")
        plt.show()

    """
    a, weights = _ravel_and_check_weights(a, weights)

    bin_edges, uniform_bins = _get_bin_edges(a, bins, range, weights)

    # Histogram is an integer or a float array depending on the weights.
    if weights is None:
        ntype = np.dtype(np.intp)
    else:
        ntype = weights.dtype

    # We set a block size, as this allows us to iterate over chunks when
    # computing histograms, to minimize memory usage.
    BLOCK = 65536

    # The fast path uses bincount, but that only works for certain types
    # of weight
    simple_weights = (
        weights is None or
        np.can_cast(weights.dtype, np.double) or
        np.can_cast(weights.dtype, complex)
    )

    if uniform_bins is not None and simple_weights:
        # Fast algorithm for equal bins
        # We now convert values of a to bin indices, under the assumption of
        # equal bin widths (which is valid here).
        first_edge, last_edge, n_equal_bins = uniform_bins

        # Initialize empty histogram
        n = np.zeros(n_equal_bins, ntype)

        # Pre-compute histogram scaling factor
        norm_numerator = n_equal_bins
        norm_denom = _unsigned_subtract(last_edge, first_edge)

        # We iterate over blocks here for two reasons: the first is that for
        # large arrays, it is actually faster (for example for a 10^8 array it
        # is 2x as fast) and it results in a memory footprint 3x lower in the
        # limit of large arrays.
        for i in _range(0, len(a), BLOCK):
            tmp_a = a[i:i + BLOCK]
            if weights is None:
                tmp_w = None
            else:
                tmp_w = weights[i:i + BLOCK]

            # Only include values in the right range
            keep = (tmp_a >= first_edge)
            keep &= (tmp_a <= last_edge)
            if not np.logical_and.reduce(keep):
                tmp_a = tmp_a[keep]
                if tmp_w is not None:
                    tmp_w = tmp_w[keep]

            # This cast ensures no type promotions occur below, which gh-10322
            # make unpredictable. Getting it wrong leads to precision errors
            # like gh-8123.
            tmp_a = tmp_a.astype(bin_edges.dtype, copy=False)

            # Compute the bin indices, and for values that lie exactly on
            # last_edge we need to subtract one
            f_indices = ((_unsigned_subtract(tmp_a, first_edge) / norm_denom)
                         * norm_numerator)
            indices = f_indices.astype(np.intp)
            indices[indices == n_equal_bins] -= 1

            # The index computation is not guaranteed to give exactly
            # consistent results within ~1 ULP of the bin edges.
            decrement = tmp_a < bin_edges[indices]
            indices[decrement] -= 1
            # The last bin includes the right edge. The other bins do not.
            increment = ((tmp_a >= bin_edges[indices + 1])
                         & (indices != n_equal_bins - 1))
            indices[increment] += 1

            # We now compute the histogram using bincount
            if ntype.kind == 'c':
                n.real += np.bincount(indices, weights=tmp_w.real,
                                      minlength=n_equal_bins)
                n.imag += np.bincount(indices, weights=tmp_w.imag,
                                      minlength=n_equal_bins)
            else:
                n += np.bincount(indices, weights=tmp_w,
                                 minlength=n_equal_bins).astype(ntype)
    else:
        # Compute via cumulative histogram
        cum_n = np.zeros(bin_edges.shape, ntype)
        if weights is None:
            for i in _range(0, len(a), BLOCK):
                sa = np.sort(a[i:i + BLOCK])
                cum_n += _search_sorted_inclusive(sa, bin_edges)
        else:
            zero = np.zeros(1, dtype=ntype)
            for i in _range(0, len(a), BLOCK):
                tmp_a = a[i:i + BLOCK]
                tmp_w = weights[i:i + BLOCK]
                sorting_index = np.argsort(tmp_a)
                sa = tmp_a[sorting_index]
                sw = tmp_w[sorting_index]
                cw = np.concatenate((zero, sw.cumsum()))
                bin_index = _search_sorted_inclusive(sa, bin_edges)
                cum_n += cw[bin_index]

        n = np.diff(cum_n)

    if density:
        db = np.array(np.diff(bin_edges), float)
        return n / db / n.sum(), bin_edges

    return n, bin_edges


def _histogramdd_dispatcher(sample, bins=None, range=None, density=None,
                            weights=None):
    if hasattr(sample, 'shape'):  # same condition as used in histogramdd
        yield sample
    else:
        yield from sample
    with contextlib.suppress(TypeError):
        yield from bins
    yield weights


@array_function_dispatch(_histogramdd_dispatcher)
def histogramdd(sample, bins=10, range=None, density=None, weights=None):
    """
    Compute the multidimensional histogram of some data.

    Parameters
    ----------
    sample : (N, D) array, or (N, D) array_like
        The data to be histogrammed.

        Note the unusual interpretation of sample when an array_like:

        * When an array, each row is a coordinate in a D-dimensional space -
          such as ``histogramdd(np.array([p1, p2, p3]))``.
        * When an array_like, each element is the list of values for single
          coordinate - such as ``histogramdd((X, Y, Z))``.

        The first form should be preferred.

    bins : sequence or int, optional
        The bin specification:

        * A sequence of arrays describing the monotonically increasing bin
          edges along each dimension.
        * The number of bins for each dimension (nx, ny, ... =bins)
        * The number of bins for all dimensions (nx=ny=...=bins).

    range : sequence, optional
        A sequence of length D, each an optional (lower, upper) tuple giving
        the outer bin edges to be used if the edges are not given explicitly in
        `bins`.
        An entry of None in the sequence results in the minimum and maximum
        values being used for the corresponding dimension.
        The default, None, is equivalent to passing a tuple of D None values.
    density : bool, optional
        If False, the default, returns the number of samples in each bin.
        If True, returns the probability *density* function at the bin,
        ``bin_count / sample_count / bin_volume``.
    weights : (N,) array_like, optional
        An array of values `w_i` weighing each sample `(x_i, y_i, z_i, ...)`.
        Weights are normalized to 1 if density is True. If density is False,
        the values of the returned histogram are equal to the sum of the
        weights belonging to the samples falling into each bin.

    Returns
    -------
    H : ndarray
        The multidimensional histogram of sample x. See density and weights
        for the different possible semantics.
    edges : tuple of ndarrays
        A tuple of D arrays describing the bin edges for each dimension.

    See Also
    --------
    histogram: 1-D histogram
    histogram2d: 2-D histogram

    Examples
    --------
    >>> import numpy as np
    >>> rng = np.random.default_rng()
    >>> r = rng.normal(size=(100,3))
    >>> H, edges = np.histogramdd(r, bins = (5, 8, 4))
    >>> H.shape, edges[0].size, edges[1].size, edges[2].size
    ((5, 8, 4), 6, 9, 5)

    """

    try:
        # Sample is an ND-array.
        N, D = sample.shape
    except (AttributeError, ValueError):
        # Sample is a sequence of 1D arrays.
        sample = np.atleast_2d(sample).T
        N, D = sample.shape

    nbin = np.empty(D, np.intp)
    edges = D * [None]
    dedges = D * [None]
    if weights is not None:
        weights = np.asarray(weights)

    try:
        M = len(bins)
        if M != D:
            raise ValueError(
                'The dimension of bins must be equal to the dimension of the '
                'sample x.')
    except TypeError:
        # bins is an integer
        bins = D * [bins]

    # normalize the range argument
    if range is None:
        range = (None,) * D
    elif len(range) != D:
        raise ValueError('range argument must have one entry per dimension')

    # Create edge arrays
    for i in _range(D):
        if np.ndim(bins[i]) == 0:
            if bins[i] < 1:
                raise ValueError(
                    f'`bins[{i}]` must be positive, when an integer')
            smin, smax = _get_outer_edges(sample[:, i], range[i])
            try:
                n = operator.index(bins[i])

            except TypeError as e:
                raise TypeError(
                    f"`bins[{i}]` must be an integer, when a scalar"
                ) from e

            edges[i] = np.linspace(smin, smax, n + 1)
        elif np.ndim(bins[i]) == 1:
            edges[i] = np.asarray(bins[i])
            if np.any(edges[i][:-1] > edges[i][1:]):
                raise ValueError(
                    f'`bins[{i}]` must be monotonically increasing, when an array')
        else:
            raise ValueError(
                f'`bins[{i}]` must be a scalar or 1d array')

        nbin[i] = len(edges[i]) + 1  # includes an outlier on each end
        dedges[i] = np.diff(edges[i])

    # Compute the bin number each sample falls into.
    Ncount = tuple(
        # avoid np.digitize to work around gh-11022
        np.searchsorted(edges[i], sample[:, i], side='right')
        for i in _range(D)
    )

    # Using digitize, values that fall on an edge are put in the right bin.
    # For the rightmost bin, we want values equal to the right edge to be
    # counted in the last bin, and not as an outlier.
    for i in _range(D):
        # Find which points are on the rightmost edge.
        on_edge = (sample[:, i] == edges[i][-1])
        # Shift these points one bin to the left.
        Ncount[i][on_edge] -= 1

    # Compute the sample indices in the flattened histogram matrix.
    # This raises an error if the array is too large.
    xy = np.ravel_multi_index(Ncount, nbin)

    # Compute the number of repetitions in xy and assign it to the
    # flattened histmat.
    hist = np.bincount(xy, weights, minlength=nbin.prod())

    # Shape into a proper matrix
    hist = hist.reshape(nbin)

    # This preserves the (bad) behavior observed in gh-7845, for now.
    hist = hist.astype(float, casting='safe')

    # Remove outliers (indices 0 and -1 for each dimension).
    core = D * (slice(1, -1),)
    hist = hist[core]

    if density:
        # calculate the probability density function
        s = hist.sum()
        for i in _range(D):
            shape = np.ones(D, int)
            shape[i] = nbin[i] - 2
            hist = hist / dedges[i].reshape(shape)
        hist /= s

    if (hist.shape != nbin - 2).any():
        raise RuntimeError(
            "Internal Shape Error")
    return hist, edges

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\_histograms_impl.py ===
"""
Histogram-related functions
"""
import contextlib
import functools
import operator
import warnings

import numpy as np
from numpy._core import overrides

__all__ = ['histogram', 'histogramdd', 'histogram_bin_edges']

array_function_dispatch = functools.partial(
    overrides.array_function_dispatch, module='numpy')

# range is a keyword argument to many functions, so save the builtin so they can
# use it.
_range = range


def _ptp(x):
    """Peak-to-peak value of x.

    This implementation avoids the problem of signed integer arrays having a
    peak-to-peak value that cannot be represented with the array's data type.
    This function returns an unsigned value for signed integer arrays.
    """
    return _unsigned_subtract(x.max(), x.min())


def _hist_bin_sqrt(x, range):
    """
    Square root histogram bin estimator.

    Bin width is inversely proportional to the data size. Used by many
    programs for its simplicity.

    Parameters
    ----------
    x : array_like
        Input data that is to be histogrammed, trimmed to range. May not
        be empty.

    Returns
    -------
    h : An estimate of the optimal bin width for the given data.
    """
    del range  # unused
    return _ptp(x) / np.sqrt(x.size)


def _hist_bin_sturges(x, range):
    """
    Sturges histogram bin estimator.

    A very simplistic estimator based on the assumption of normality of
    the data. This estimator has poor performance for non-normal data,
    which becomes especially obvious for large data sets. The estimate
    depends only on size of the data.

    Parameters
    ----------
    x : array_like
        Input data that is to be histogrammed, trimmed to range. May not
        be empty.

    Returns
    -------
    h : An estimate of the optimal bin width for the given data.
    """
    del range  # unused
    return _ptp(x) / (np.log2(x.size) + 1.0)


def _hist_bin_rice(x, range):
    """
    Rice histogram bin estimator.

    Another simple estimator with no normality assumption. It has better
    performance for large data than Sturges, but tends to overestimate
    the number of bins. The number of bins is proportional to the cube
    root of data size (asymptotically optimal). The estimate depends
    only on size of the data.

    Parameters
    ----------
    x : array_like
        Input data that is to be histogrammed, trimmed to range. May not
        be empty.

    Returns
    -------
    h : An estimate of the optimal bin width for the given data.
    """
    del range  # unused
    return _ptp(x) / (2.0 * x.size ** (1.0 / 3))


def _hist_bin_scott(x, range):
    """
    Scott histogram bin estimator.

    The binwidth is proportional to the standard deviation of the data
    and inversely proportional to the cube root of data size
    (asymptotically optimal).

    Parameters
    ----------
    x : array_like
        Input data that is to be histogrammed, trimmed to range. May not
        be empty.

    Returns
    -------
    h : An estimate of the optimal bin width for the given data.
    """
    del range  # unused
    return (24.0 * np.pi**0.5 / x.size)**(1.0 / 3.0) * np.std(x)


def _hist_bin_stone(x, range):
    """
    Histogram bin estimator based on minimizing the estimated integrated squared error (ISE).

    The number of bins is chosen by minimizing the estimated ISE against the unknown
    true distribution. The ISE is estimated using cross-validation and can be regarded
    as a generalization of Scott's rule.
    https://en.wikipedia.org/wiki/Histogram#Scott.27s_normal_reference_rule

    This paper by Stone appears to be the origination of this rule.
    https://digitalassets.lib.berkeley.edu/sdtr/ucb/text/34.pdf

    Parameters
    ----------
    x : array_like
        Input data that is to be histogrammed, trimmed to range. May not
        be empty.
    range : (float, float)
        The lower and upper range of the bins.

    Returns
    -------
    h : An estimate of the optimal bin width for the given data.
    """  # noqa: E501

    n = x.size
    ptp_x = _ptp(x)
    if n <= 1 or ptp_x == 0:
        return 0

    def jhat(nbins):
        hh = ptp_x / nbins
        p_k = np.histogram(x, bins=nbins, range=range)[0] / n
        return (2 - (n + 1) * p_k.dot(p_k)) / hh

    nbins_upper_bound = max(100, int(np.sqrt(n)))
    nbins = min(_range(1, nbins_upper_bound + 1), key=jhat)
    if nbins == nbins_upper_bound:
        warnings.warn("The number of bins estimated may be suboptimal.",
                      RuntimeWarning, stacklevel=3)
    return ptp_x / nbins


def _hist_bin_doane(x, range):
    """
    Doane's histogram bin estimator.

    Improved version of Sturges' formula which works better for
    non-normal data. See
    stats.stackexchange.com/questions/55134/doanes-formula-for-histogram-binning

    Parameters
    ----------
    x : array_like
        Input data that is to be histogrammed, trimmed to range. May not
        be empty.

    Returns
    -------
    h : An estimate of the optimal bin width for the given data.
    """
    del range  # unused
    if x.size > 2:
        sg1 = np.sqrt(6.0 * (x.size - 2) / ((x.size + 1.0) * (x.size + 3)))
        sigma = np.std(x)
        if sigma > 0.0:
            # These three operations add up to
            # g1 = np.mean(((x - np.mean(x)) / sigma)**3)
            # but use only one temp array instead of three
            temp = x - np.mean(x)
            np.true_divide(temp, sigma, temp)
            np.power(temp, 3, temp)
            g1 = np.mean(temp)
            return _ptp(x) / (1.0 + np.log2(x.size) +
                                    np.log2(1.0 + np.absolute(g1) / sg1))
    return 0.0


def _hist_bin_fd(x, range):
    """
    The Freedman-Diaconis histogram bin estimator.

    The Freedman-Diaconis rule uses interquartile range (IQR) to
    estimate binwidth. It is considered a variation of the Scott rule
    with more robustness as the IQR is less affected by outliers than
    the standard deviation. However, the IQR depends on fewer points
    than the standard deviation, so it is less accurate, especially for
    long tailed distributions.

    If the IQR is 0, this function returns 0 for the bin width.
    Binwidth is inversely proportional to the cube root of data size
    (asymptotically optimal).

    Parameters
    ----------
    x : array_like
        Input data that is to be histogrammed, trimmed to range. May not
        be empty.

    Returns
    -------
    h : An estimate of the optimal bin width for the given data.
    """
    del range  # unused
    iqr = np.subtract(*np.percentile(x, [75, 25]))
    return 2.0 * iqr * x.size ** (-1.0 / 3.0)


def _hist_bin_auto(x, range):
    """
    Histogram bin estimator that uses the minimum width of a relaxed
    Freedman-Diaconis and Sturges estimators if the FD bin width does
    not result in a large number of bins. The relaxed Freedman-Diaconis estimator
    limits the bin width to half the sqrt estimated to avoid small bins.

    The FD estimator is usually the most robust method, but its width
    estimate tends to be too large for small `x` and bad for data with limited
    variance. The Sturges estimator is quite good for small (<1000) datasets
    and is the default in the R language. This method gives good off-the-shelf
    behaviour.


    Parameters
    ----------
    x : array_like
        Input data that is to be histogrammed, trimmed to range. May not
        be empty.
    range : Tuple with range for the histogram

    Returns
    -------
    h : An estimate of the optimal bin width for the given data.

    See Also
    --------
    _hist_bin_fd, _hist_bin_sturges
    """
    fd_bw = _hist_bin_fd(x, range)
    sturges_bw = _hist_bin_sturges(x, range)
    sqrt_bw = _hist_bin_sqrt(x, range)
    # heuristic to limit the maximal number of bins
    fd_bw_corrected = max(fd_bw, sqrt_bw / 2)
    return min(fd_bw_corrected, sturges_bw)


# Private dict initialized at module load time
_hist_bin_selectors = {'stone': _hist_bin_stone,
                       'auto': _hist_bin_auto,
                       'doane': _hist_bin_doane,
                       'fd': _hist_bin_fd,
                       'rice': _hist_bin_rice,
                       'scott': _hist_bin_scott,
                       'sqrt': _hist_bin_sqrt,
                       'sturges': _hist_bin_sturges}


def _ravel_and_check_weights(a, weights):
    """ Check a and weights have matching shapes, and ravel both """
    a = np.asarray(a)

    # Ensure that the array is a "subtractable" dtype
    if a.dtype == np.bool:
        msg = f"Converting input from {a.dtype} to {np.uint8} for compatibility."
        warnings.warn(msg, RuntimeWarning, stacklevel=3)
        a = a.astype(np.uint8)

    if weights is not None:
        weights = np.asarray(weights)
        if weights.shape != a.shape:
            raise ValueError(
                'weights should have the same shape as a.')
        weights = weights.ravel()
    a = a.ravel()
    return a, weights


def _get_outer_edges(a, range):
    """
    Determine the outer bin edges to use, from either the data or the range
    argument
    """
    if range is not None:
        first_edge, last_edge = range
        if first_edge > last_edge:
            raise ValueError(
                'max must be larger than min in range parameter.')
        if not (np.isfinite(first_edge) and np.isfinite(last_edge)):
            raise ValueError(
                f"supplied range of [{first_edge}, {last_edge}] is not finite")
    elif a.size == 0:
        # handle empty arrays. Can't determine range, so use 0-1.
        first_edge, last_edge = 0, 1
    else:
        first_edge, last_edge = a.min(), a.max()
        if not (np.isfinite(first_edge) and np.isfinite(last_edge)):
            raise ValueError(
                f"autodetected range of [{first_edge}, {last_edge}] is not finite")

    # expand empty range to avoid divide by zero
    if first_edge == last_edge:
        first_edge = first_edge - 0.5
        last_edge = last_edge + 0.5

    return first_edge, last_edge


def _unsigned_subtract(a, b):
    """
    Subtract two values where a >= b, and produce an unsigned result

    This is needed when finding the difference between the upper and lower
    bound of an int16 histogram
    """
    # coerce to a single type
    signed_to_unsigned = {
        np.byte: np.ubyte,
        np.short: np.ushort,
        np.intc: np.uintc,
        np.int_: np.uint,
        np.longlong: np.ulonglong
    }
    dt = np.result_type(a, b)
    try:
        unsigned_dt = signed_to_unsigned[dt.type]
    except KeyError:
        return np.subtract(a, b, dtype=dt)
    else:
        # we know the inputs are integers, and we are deliberately casting
        # signed to unsigned.  The input may be negative python integers so
        # ensure we pass in arrays with the initial dtype (related to NEP 50).
        return np.subtract(np.asarray(a, dtype=dt), np.asarray(b, dtype=dt),
                           casting='unsafe', dtype=unsigned_dt)


def _get_bin_edges(a, bins, range, weights):
    """
    Computes the bins used internally by `histogram`.

    Parameters
    ==========
    a : ndarray
        Ravelled data array
    bins, range
        Forwarded arguments from `histogram`.
    weights : ndarray, optional
        Ravelled weights array, or None

    Returns
    =======
    bin_edges : ndarray
        Array of bin edges
    uniform_bins : (Number, Number, int):
        The upper bound, lowerbound, and number of bins, used in the optimized
        implementation of `histogram` that works on uniform bins.
    """
    # parse the overloaded bins argument
    n_equal_bins = None
    bin_edges = None

    if isinstance(bins, str):
        bin_name = bins
        # if `bins` is a string for an automatic method,
        # this will replace it with the number of bins calculated
        if bin_name not in _hist_bin_selectors:
            raise ValueError(
                f"{bin_name!r} is not a valid estimator for `bins`")
        if weights is not None:
            raise TypeError("Automated estimation of the number of "
                            "bins is not supported for weighted data")

        first_edge, last_edge = _get_outer_edges(a, range)

        # truncate the range if needed
        if range is not None:
            keep = (a >= first_edge)
            keep &= (a <= last_edge)
            if not np.logical_and.reduce(keep):
                a = a[keep]

        if a.size == 0:
            n_equal_bins = 1
        else:
            # Do not call selectors on empty arrays
            width = _hist_bin_selectors[bin_name](a, (first_edge, last_edge))
            if width:
                if np.issubdtype(a.dtype, np.integer) and width < 1:
                    width = 1
                delta = _unsigned_subtract(last_edge, first_edge)
                n_equal_bins = int(np.ceil(delta / width))
            else:
                # Width can be zero for some estimators, e.g. FD when
                # the IQR of the data is zero.
                n_equal_bins = 1

    elif np.ndim(bins) == 0:
        try:
            n_equal_bins = operator.index(bins)
        except TypeError as e:
            raise TypeError(
                '`bins` must be an integer, a string, or an array') from e
        if n_equal_bins < 1:
            raise ValueError('`bins` must be positive, when an integer')

        first_edge, last_edge = _get_outer_edges(a, range)

    elif np.ndim(bins) == 1:
        bin_edges = np.asarray(bins)
        if np.any(bin_edges[:-1] > bin_edges[1:]):
            raise ValueError(
                '`bins` must increase monotonically, when an array')

    else:
        raise ValueError('`bins` must be 1d, when an array')

    if n_equal_bins is not None:
        # gh-10322 means that type resolution rules are dependent on array
        # shapes. To avoid this causing problems, we pick a type now and stick
        # with it throughout.
        bin_type = np.result_type(first_edge, last_edge, a)
        if np.issubdtype(bin_type, np.integer):
            bin_type = np.result_type(bin_type, float)

        # bin edges must be computed
        bin_edges = np.linspace(
            first_edge, last_edge, n_equal_bins + 1,
            endpoint=True, dtype=bin_type)
        if np.any(bin_edges[:-1] >= bin_edges[1:]):
            raise ValueError(
                f'Too many bins for data range. Cannot create {n_equal_bins} '
                f'finite-sized bins.')
        return bin_edges, (first_edge, last_edge, n_equal_bins)
    else:
        return bin_edges, None


def _search_sorted_inclusive(a, v):
    """
    Like `searchsorted`, but where the last item in `v` is placed on the right.

    In the context of a histogram, this makes the last bin edge inclusive
    """
    return np.concatenate((
        a.searchsorted(v[:-1], 'left'),
        a.searchsorted(v[-1:], 'right')
    ))


def _histogram_bin_edges_dispatcher(a, bins=None, range=None, weights=None):
    return (a, bins, weights)


@array_function_dispatch(_histogram_bin_edges_dispatcher)
def histogram_bin_edges(a, bins=10, range=None, weights=None):
    r"""
    Function to calculate only the edges of the bins used by the `histogram`
    function.

    Parameters
    ----------
    a : array_like
        Input data. The histogram is computed over the flattened array.
    bins : int or sequence of scalars or str, optional
        If `bins` is an int, it defines the number of equal-width
        bins in the given range (10, by default). If `bins` is a
        sequence, it defines the bin edges, including the rightmost
        edge, allowing for non-uniform bin widths.

        If `bins` is a string from the list below, `histogram_bin_edges` will
        use the method chosen to calculate the optimal bin width and
        consequently the number of bins (see the Notes section for more detail
        on the estimators) from the data that falls within the requested range.
        While the bin width will be optimal for the actual data
        in the range, the number of bins will be computed to fill the
        entire range, including the empty portions. For visualisation,
        using the 'auto' option is suggested. Weighted data is not
        supported for automated bin size selection.

        'auto'
            Minimum bin width between the 'sturges' and 'fd' estimators.
            Provides good all-around performance.

        'fd' (Freedman Diaconis Estimator)
            Robust (resilient to outliers) estimator that takes into
            account data variability and data size.

        'doane'
            An improved version of Sturges' estimator that works better
            with non-normal datasets.

        'scott'
            Less robust estimator that takes into account data variability
            and data size.

        'stone'
            Estimator based on leave-one-out cross-validation estimate of
            the integrated squared error. Can be regarded as a generalization
            of Scott's rule.

        'rice'
            Estimator does not take variability into account, only data
            size. Commonly overestimates number of bins required.

        'sturges'
            R's default method, only accounts for data size. Only
            optimal for gaussian data and underestimates number of bins
            for large non-gaussian datasets.

        'sqrt'
            Square root (of data size) estimator, used by Excel and
            other programs for its speed and simplicity.

    range : (float, float), optional
        The lower and upper range of the bins.  If not provided, range
        is simply ``(a.min(), a.max())``.  Values outside the range are
        ignored. The first element of the range must be less than or
        equal to the second. `range` affects the automatic bin
        computation as well. While bin width is computed to be optimal
        based on the actual data within `range`, the bin count will fill
        the entire range including portions containing no data.

    weights : array_like, optional
        An array of weights, of the same shape as `a`.  Each value in
        `a` only contributes its associated weight towards the bin count
        (instead of 1). This is currently not used by any of the bin estimators,
        but may be in the future.

    Returns
    -------
    bin_edges : array of dtype float
        The edges to pass into `histogram`

    See Also
    --------
    histogram

    Notes
    -----
    The methods to estimate the optimal number of bins are well founded
    in literature, and are inspired by the choices R provides for
    histogram visualisation. Note that having the number of bins
    proportional to :math:`n^{1/3}` is asymptotically optimal, which is
    why it appears in most estimators. These are simply plug-in methods
    that give good starting points for number of bins. In the equations
    below, :math:`h` is the binwidth and :math:`n_h` is the number of
    bins. All estimators that compute bin counts are recast to bin width
    using the `ptp` of the data. The final bin count is obtained from
    ``np.round(np.ceil(range / h))``. The final bin width is often less
    than what is returned by the estimators below.

    'auto' (minimum bin width of the 'sturges' and 'fd' estimators)
        A compromise to get a good value. For small datasets the Sturges
        value will usually be chosen, while larger datasets will usually
        default to FD.  Avoids the overly conservative behaviour of FD
        and Sturges for small and large datasets respectively.
        Switchover point is usually :math:`a.size \approx 1000`.

    'fd' (Freedman Diaconis Estimator)
        .. math:: h = 2 \frac{IQR}{n^{1/3}}

        The binwidth is proportional to the interquartile range (IQR)
        and inversely proportional to cube root of a.size. Can be too
        conservative for small datasets, but is quite good for large
        datasets. The IQR is very robust to outliers.

    'scott'
        .. math:: h = \sigma \sqrt[3]{\frac{24 \sqrt{\pi}}{n}}

        The binwidth is proportional to the standard deviation of the
        data and inversely proportional to cube root of ``x.size``. Can
        be too conservative for small datasets, but is quite good for
        large datasets. The standard deviation is not very robust to
        outliers. Values are very similar to the Freedman-Diaconis
        estimator in the absence of outliers.

    'rice'
        .. math:: n_h = 2n^{1/3}

        The number of bins is only proportional to cube root of
        ``a.size``. It tends to overestimate the number of bins and it
        does not take into account data variability.

    'sturges'
        .. math:: n_h = \log _{2}(n) + 1

        The number of bins is the base 2 log of ``a.size``.  This
        estimator assumes normality of data and is too conservative for
        larger, non-normal datasets. This is the default method in R's
        ``hist`` method.

    'doane'
        .. math:: n_h = 1 + \log_{2}(n) +
                        \log_{2}\left(1 + \frac{|g_1|}{\sigma_{g_1}}\right)

            g_1 = mean\left[\left(\frac{x - \mu}{\sigma}\right)^3\right]

            \sigma_{g_1} = \sqrt{\frac{6(n - 2)}{(n + 1)(n + 3)}}

        An improved version of Sturges' formula that produces better
        estimates for non-normal datasets. This estimator attempts to
        account for the skew of the data.

    'sqrt'
        .. math:: n_h = \sqrt n

        The simplest and fastest estimator. Only takes into account the
        data size.

    Additionally, if the data is of integer dtype, then the binwidth will never
    be less than 1.

    Examples
    --------
    >>> import numpy as np
    >>> arr = np.array([0, 0, 0, 1, 2, 3, 3, 4, 5])
    >>> np.histogram_bin_edges(arr, bins='auto', range=(0, 1))
    array([0.  , 0.25, 0.5 , 0.75, 1.  ])
    >>> np.histogram_bin_edges(arr, bins=2)
    array([0. , 2.5, 5. ])

    For consistency with histogram, an array of pre-computed bins is
    passed through unmodified:

    >>> np.histogram_bin_edges(arr, [1, 2])
    array([1, 2])

    This function allows one set of bins to be computed, and reused across
    multiple histograms:

    >>> shared_bins = np.histogram_bin_edges(arr, bins='auto')
    >>> shared_bins
    array([0., 1., 2., 3., 4., 5.])

    >>> group_id = np.array([0, 1, 1, 0, 1, 1, 0, 1, 1])
    >>> hist_0, _ = np.histogram(arr[group_id == 0], bins=shared_bins)
    >>> hist_1, _ = np.histogram(arr[group_id == 1], bins=shared_bins)

    >>> hist_0; hist_1
    array([1, 1, 0, 1, 0])
    array([2, 0, 1, 1, 2])

    Which gives more easily comparable results than using separate bins for
    each histogram:

    >>> hist_0, bins_0 = np.histogram(arr[group_id == 0], bins='auto')
    >>> hist_1, bins_1 = np.histogram(arr[group_id == 1], bins='auto')
    >>> hist_0; hist_1
    array([1, 1, 1])
    array([2, 1, 1, 2])
    >>> bins_0; bins_1
    array([0., 1., 2., 3.])
    array([0.  , 1.25, 2.5 , 3.75, 5.  ])

    """
    a, weights = _ravel_and_check_weights(a, weights)
    bin_edges, _ = _get_bin_edges(a, bins, range, weights)
    return bin_edges


def _histogram_dispatcher(
        a, bins=None, range=None, density=None, weights=None):
    return (a, bins, weights)


@array_function_dispatch(_histogram_dispatcher)
def histogram(a, bins=10, range=None, density=None, weights=None):
    r"""
    Compute the histogram of a dataset.

    Parameters
    ----------
    a : array_like
        Input data. The histogram is computed over the flattened array.
    bins : int or sequence of scalars or str, optional
        If `bins` is an int, it defines the number of equal-width
        bins in the given range (10, by default). If `bins` is a
        sequence, it defines a monotonically increasing array of bin edges,
        including the rightmost edge, allowing for non-uniform bin widths.

        If `bins` is a string, it defines the method used to calculate the
        optimal bin width, as defined by `histogram_bin_edges`.

    range : (float, float), optional
        The lower and upper range of the bins.  If not provided, range
        is simply ``(a.min(), a.max())``.  Values outside the range are
        ignored. The first element of the range must be less than or
        equal to the second. `range` affects the automatic bin
        computation as well. While bin width is computed to be optimal
        based on the actual data within `range`, the bin count will fill
        the entire range including portions containing no data.
    weights : array_like, optional
        An array of weights, of the same shape as `a`.  Each value in
        `a` only contributes its associated weight towards the bin count
        (instead of 1). If `density` is True, the weights are
        normalized, so that the integral of the density over the range
        remains 1.
        Please note that the ``dtype`` of `weights` will also become the
        ``dtype`` of the returned accumulator (`hist`), so it must be
        large enough to hold accumulated values as well.
    density : bool, optional
        If ``False``, the result will contain the number of samples in
        each bin. If ``True``, the result is the value of the
        probability *density* function at the bin, normalized such that
        the *integral* over the range is 1. Note that the sum of the
        histogram values will not be equal to 1 unless bins of unity
        width are chosen; it is not a probability *mass* function.

    Returns
    -------
    hist : array
        The values of the histogram. See `density` and `weights` for a
        description of the possible semantics.  If `weights` are given,
        ``hist.dtype`` will be taken from `weights`.
    bin_edges : array of dtype float
        Return the bin edges ``(length(hist)+1)``.


    See Also
    --------
    histogramdd, bincount, searchsorted, digitize, histogram_bin_edges

    Notes
    -----
    All but the last (righthand-most) bin is half-open.  In other words,
    if `bins` is::

      [1, 2, 3, 4]

    then the first bin is ``[1, 2)`` (including 1, but excluding 2) and
    the second ``[2, 3)``.  The last bin, however, is ``[3, 4]``, which
    *includes* 4.


    Examples
    --------
    >>> import numpy as np
    >>> np.histogram([1, 2, 1], bins=[0, 1, 2, 3])
    (array([0, 2, 1]), array([0, 1, 2, 3]))
    >>> np.histogram(np.arange(4), bins=np.arange(5), density=True)
    (array([0.25, 0.25, 0.25, 0.25]), array([0, 1, 2, 3, 4]))
    >>> np.histogram([[1, 2, 1], [1, 0, 1]], bins=[0,1,2,3])
    (array([1, 4, 1]), array([0, 1, 2, 3]))

    >>> a = np.arange(5)
    >>> hist, bin_edges = np.histogram(a, density=True)
    >>> hist
    array([0.5, 0. , 0.5, 0. , 0. , 0.5, 0. , 0.5, 0. , 0.5])
    >>> hist.sum()
    2.4999999999999996
    >>> np.sum(hist * np.diff(bin_edges))
    1.0

    Automated Bin Selection Methods example, using 2 peak random data
    with 2000 points.

    .. plot::
        :include-source:

        import matplotlib.pyplot as plt
        import numpy as np

        rng = np.random.RandomState(10)  # deterministic random data
        a = np.hstack((rng.normal(size=1000),
                       rng.normal(loc=5, scale=2, size=1000)))
        plt.hist(a, bins='auto')  # arguments are passed to np.histogram
        plt.title("Histogram with 'auto' bins")
        plt.show()

    """
    a, weights = _ravel_and_check_weights(a, weights)

    bin_edges, uniform_bins = _get_bin_edges(a, bins, range, weights)

    # Histogram is an integer or a float array depending on the weights.
    if weights is None:
        ntype = np.dtype(np.intp)
    else:
        ntype = weights.dtype

    # We set a block size, as this allows us to iterate over chunks when
    # computing histograms, to minimize memory usage.
    BLOCK = 65536

    # The fast path uses bincount, but that only works for certain types
    # of weight
    simple_weights = (
        weights is None or
        np.can_cast(weights.dtype, np.double) or
        np.can_cast(weights.dtype, complex)
    )

    if uniform_bins is not None and simple_weights:
        # Fast algorithm for equal bins
        # We now convert values of a to bin indices, under the assumption of
        # equal bin widths (which is valid here).
        first_edge, last_edge, n_equal_bins = uniform_bins

        # Initialize empty histogram
        n = np.zeros(n_equal_bins, ntype)

        # Pre-compute histogram scaling factor
        norm_numerator = n_equal_bins
        norm_denom = _unsigned_subtract(last_edge, first_edge)

        # We iterate over blocks here for two reasons: the first is that for
        # large arrays, it is actually faster (for example for a 10^8 array it
        # is 2x as fast) and it results in a memory footprint 3x lower in the
        # limit of large arrays.
        for i in _range(0, len(a), BLOCK):
            tmp_a = a[i:i + BLOCK]
            if weights is None:
                tmp_w = None
            else:
                tmp_w = weights[i:i + BLOCK]

            # Only include values in the right range
            keep = (tmp_a >= first_edge)
            keep &= (tmp_a <= last_edge)
            if not np.logical_and.reduce(keep):
                tmp_a = tmp_a[keep]
                if tmp_w is not None:
                    tmp_w = tmp_w[keep]

            # This cast ensures no type promotions occur below, which gh-10322
            # make unpredictable. Getting it wrong leads to precision errors
            # like gh-8123.
            tmp_a = tmp_a.astype(bin_edges.dtype, copy=False)

            # Compute the bin indices, and for values that lie exactly on
            # last_edge we need to subtract one
            f_indices = ((_unsigned_subtract(tmp_a, first_edge) / norm_denom)
                         * norm_numerator)
            indices = f_indices.astype(np.intp)
            indices[indices == n_equal_bins] -= 1

            # The index computation is not guaranteed to give exactly
            # consistent results within ~1 ULP of the bin edges.
            decrement = tmp_a < bin_edges[indices]
            indices[decrement] -= 1
            # The last bin includes the right edge. The other bins do not.
            increment = ((tmp_a >= bin_edges[indices + 1])
                         & (indices != n_equal_bins - 1))
            indices[increment] += 1

            # We now compute the histogram using bincount
            if ntype.kind == 'c':
                n.real += np.bincount(indices, weights=tmp_w.real,
                                      minlength=n_equal_bins)
                n.imag += np.bincount(indices, weights=tmp_w.imag,
                                      minlength=n_equal_bins)
            else:
                n += np.bincount(indices, weights=tmp_w,
                                 minlength=n_equal_bins).astype(ntype)
    else:
        # Compute via cumulative histogram
        cum_n = np.zeros(bin_edges.shape, ntype)
        if weights is None:
            for i in _range(0, len(a), BLOCK):
                sa = np.sort(a[i:i + BLOCK])
                cum_n += _search_sorted_inclusive(sa, bin_edges)
        else:
            zero = np.zeros(1, dtype=ntype)
            for i in _range(0, len(a), BLOCK):
                tmp_a = a[i:i + BLOCK]
                tmp_w = weights[i:i + BLOCK]
                sorting_index = np.argsort(tmp_a)
                sa = tmp_a[sorting_index]
                sw = tmp_w[sorting_index]
                cw = np.concatenate((zero, sw.cumsum()))
                bin_index = _search_sorted_inclusive(sa, bin_edges)
                cum_n += cw[bin_index]

        n = np.diff(cum_n)

    if density:
        db = np.array(np.diff(bin_edges), float)
        return n / db / n.sum(), bin_edges

    return n, bin_edges


def _histogramdd_dispatcher(sample, bins=None, range=None, density=None,
                            weights=None):
    if hasattr(sample, 'shape'):  # same condition as used in histogramdd
        yield sample
    else:
        yield from sample
    with contextlib.suppress(TypeError):
        yield from bins
    yield weights


@array_function_dispatch(_histogramdd_dispatcher)
def histogramdd(sample, bins=10, range=None, density=None, weights=None):
    """
    Compute the multidimensional histogram of some data.

    Parameters
    ----------
    sample : (N, D) array, or (N, D) array_like
        The data to be histogrammed.

        Note the unusual interpretation of sample when an array_like:

        * When an array, each row is a coordinate in a D-dimensional space -
          such as ``histogramdd(np.array([p1, p2, p3]))``.
        * When an array_like, each element is the list of values for single
          coordinate - such as ``histogramdd((X, Y, Z))``.

        The first form should be preferred.

    bins : sequence or int, optional
        The bin specification:

        * A sequence of arrays describing the monotonically increasing bin
          edges along each dimension.
        * The number of bins for each dimension (nx, ny, ... =bins)
        * The number of bins for all dimensions (nx=ny=...=bins).

    range : sequence, optional
        A sequence of length D, each an optional (lower, upper) tuple giving
        the outer bin edges to be used if the edges are not given explicitly in
        `bins`.
        An entry of None in the sequence results in the minimum and maximum
        values being used for the corresponding dimension.
        The default, None, is equivalent to passing a tuple of D None values.
    density : bool, optional
        If False, the default, returns the number of samples in each bin.
        If True, returns the probability *density* function at the bin,
        ``bin_count / sample_count / bin_volume``.
    weights : (N,) array_like, optional
        An array of values `w_i` weighing each sample `(x_i, y_i, z_i, ...)`.
        Weights are normalized to 1 if density is True. If density is False,
        the values of the returned histogram are equal to the sum of the
        weights belonging to the samples falling into each bin.

    Returns
    -------
    H : ndarray
        The multidimensional histogram of sample x. See density and weights
        for the different possible semantics.
    edges : tuple of ndarrays
        A tuple of D arrays describing the bin edges for each dimension.

    See Also
    --------
    histogram: 1-D histogram
    histogram2d: 2-D histogram

    Examples
    --------
    >>> import numpy as np
    >>> rng = np.random.default_rng()
    >>> r = rng.normal(size=(100,3))
    >>> H, edges = np.histogramdd(r, bins = (5, 8, 4))
    >>> H.shape, edges[0].size, edges[1].size, edges[2].size
    ((5, 8, 4), 6, 9, 5)

    """

    try:
        # Sample is an ND-array.
        N, D = sample.shape
    except (AttributeError, ValueError):
        # Sample is a sequence of 1D arrays.
        sample = np.atleast_2d(sample).T
        N, D = sample.shape

    nbin = np.empty(D, np.intp)
    edges = D * [None]
    dedges = D * [None]
    if weights is not None:
        weights = np.asarray(weights)

    try:
        M = len(bins)
        if M != D:
            raise ValueError(
                'The dimension of bins must be equal to the dimension of the '
                'sample x.')
    except TypeError:
        # bins is an integer
        bins = D * [bins]

    # normalize the range argument
    if range is None:
        range = (None,) * D
    elif len(range) != D:
        raise ValueError('range argument must have one entry per dimension')

    # Create edge arrays
    for i in _range(D):
        if np.ndim(bins[i]) == 0:
            if bins[i] < 1:
                raise ValueError(
                    f'`bins[{i}]` must be positive, when an integer')
            smin, smax = _get_outer_edges(sample[:, i], range[i])
            try:
                n = operator.index(bins[i])

            except TypeError as e:
                raise TypeError(
                    f"`bins[{i}]` must be an integer, when a scalar"
                ) from e

            edges[i] = np.linspace(smin, smax, n + 1)
        elif np.ndim(bins[i]) == 1:
            edges[i] = np.asarray(bins[i])
            if np.any(edges[i][:-1] > edges[i][1:]):
                raise ValueError(
                    f'`bins[{i}]` must be monotonically increasing, when an array')
        else:
            raise ValueError(
                f'`bins[{i}]` must be a scalar or 1d array')

        nbin[i] = len(edges[i]) + 1  # includes an outlier on each end
        dedges[i] = np.diff(edges[i])

    # Compute the bin number each sample falls into.
    Ncount = tuple(
        # avoid np.digitize to work around gh-11022
        np.searchsorted(edges[i], sample[:, i], side='right')
        for i in _range(D)
    )

    # Using digitize, values that fall on an edge are put in the right bin.
    # For the rightmost bin, we want values equal to the right edge to be
    # counted in the last bin, and not as an outlier.
    for i in _range(D):
        # Find which points are on the rightmost edge.
        on_edge = (sample[:, i] == edges[i][-1])
        # Shift these points one bin to the left.
        Ncount[i][on_edge] -= 1

    # Compute the sample indices in the flattened histogram matrix.
    # This raises an error if the array is too large.
    xy = np.ravel_multi_index(Ncount, nbin)

    # Compute the number of repetitions in xy and assign it to the
    # flattened histmat.
    hist = np.bincount(xy, weights, minlength=nbin.prod())

    # Shape into a proper matrix
    hist = hist.reshape(nbin)

    # This preserves the (bad) behavior observed in gh-7845, for now.
    hist = hist.astype(float, casting='safe')

    # Remove outliers (indices 0 and -1 for each dimension).
    core = D * (slice(1, -1),)
    hist = hist[core]

    if density:
        # calculate the probability density function
        s = hist.sum()
        for i in _range(D):
            shape = np.ones(D, int)
            shape[i] = nbin[i] - 2
            hist = hist / dedges[i].reshape(shape)
        hist /= s

    if (hist.shape != nbin - 2).any():
        raise RuntimeError(
            "Internal Shape Error")
    return hist, edges

# === NexusCore/openenv\Lib\site-packages\win32\lib\winioctlcon.py ===
## flags, enums, guids used with DeviceIoControl from WinIoCtl.h

import pywintypes
from ntsecuritycon import FILE_READ_DATA, FILE_WRITE_DATA


def CTL_CODE(DeviceType, Function, Method, Access):
    return (DeviceType << 16) | (Access << 14) | (Function << 2) | Method


def DEVICE_TYPE_FROM_CTL_CODE(ctrlCode):
    return (ctrlCode & 0xFFFF0000) >> 16


FILE_DEVICE_BEEP = 0x00000001
FILE_DEVICE_CD_ROM = 0x00000002
FILE_DEVICE_CD_ROM_FILE_SYSTEM = 0x00000003
FILE_DEVICE_CONTROLLER = 0x00000004
FILE_DEVICE_DATALINK = 0x00000005
FILE_DEVICE_DFS = 0x00000006
FILE_DEVICE_DISK = 0x00000007
FILE_DEVICE_DISK_FILE_SYSTEM = 0x00000008
FILE_DEVICE_FILE_SYSTEM = 0x00000009
FILE_DEVICE_INPORT_PORT = 0x0000000A
FILE_DEVICE_KEYBOARD = 0x0000000B
FILE_DEVICE_MAILSLOT = 0x0000000C
FILE_DEVICE_MIDI_IN = 0x0000000D
FILE_DEVICE_MIDI_OUT = 0x0000000E
FILE_DEVICE_MOUSE = 0x0000000F
FILE_DEVICE_MULTI_UNC_PROVIDER = 0x00000010
FILE_DEVICE_NAMED_PIPE = 0x00000011
FILE_DEVICE_NETWORK = 0x00000012
FILE_DEVICE_NETWORK_BROWSER = 0x00000013
FILE_DEVICE_NETWORK_FILE_SYSTEM = 0x00000014
FILE_DEVICE_NULL = 0x00000015
FILE_DEVICE_PARALLEL_PORT = 0x00000016
FILE_DEVICE_PHYSICAL_NETCARD = 0x00000017
FILE_DEVICE_PRINTER = 0x00000018
FILE_DEVICE_SCANNER = 0x00000019
FILE_DEVICE_SERIAL_MOUSE_PORT = 0x0000001A
FILE_DEVICE_SERIAL_PORT = 0x0000001B
FILE_DEVICE_SCREEN = 0x0000001C
FILE_DEVICE_SOUND = 0x0000001D
FILE_DEVICE_STREAMS = 0x0000001E
FILE_DEVICE_TAPE = 0x0000001F
FILE_DEVICE_TAPE_FILE_SYSTEM = 0x00000020
FILE_DEVICE_TRANSPORT = 0x00000021
FILE_DEVICE_UNKNOWN = 0x00000022
FILE_DEVICE_VIDEO = 0x00000023
FILE_DEVICE_VIRTUAL_DISK = 0x00000024
FILE_DEVICE_WAVE_IN = 0x00000025
FILE_DEVICE_WAVE_OUT = 0x00000026
FILE_DEVICE_8042_PORT = 0x00000027
FILE_DEVICE_NETWORK_REDIRECTOR = 0x00000028
FILE_DEVICE_BATTERY = 0x00000029
FILE_DEVICE_BUS_EXTENDER = 0x0000002A
FILE_DEVICE_MODEM = 0x0000002B
FILE_DEVICE_VDM = 0x0000002C
FILE_DEVICE_MASS_STORAGE = 0x0000002D
FILE_DEVICE_SMB = 0x0000002E
FILE_DEVICE_KS = 0x0000002F
FILE_DEVICE_CHANGER = 0x00000030
FILE_DEVICE_SMARTCARD = 0x00000031
FILE_DEVICE_ACPI = 0x00000032
FILE_DEVICE_DVD = 0x00000033
FILE_DEVICE_FULLSCREEN_VIDEO = 0x00000034
FILE_DEVICE_DFS_FILE_SYSTEM = 0x00000035
FILE_DEVICE_DFS_VOLUME = 0x00000036
FILE_DEVICE_SERENUM = 0x00000037
FILE_DEVICE_TERMSRV = 0x00000038
FILE_DEVICE_KSEC = 0x00000039
FILE_DEVICE_FIPS = 0x0000003A
FILE_DEVICE_INFINIBAND = 0x0000003B

METHOD_BUFFERED = 0
METHOD_IN_DIRECT = 1
METHOD_OUT_DIRECT = 2
METHOD_NEITHER = 3
METHOD_DIRECT_TO_HARDWARE = METHOD_IN_DIRECT
METHOD_DIRECT_FROM_HARDWARE = METHOD_OUT_DIRECT
FILE_ANY_ACCESS = 0
FILE_SPECIAL_ACCESS = FILE_ANY_ACCESS
FILE_READ_ACCESS = 0x0001
FILE_WRITE_ACCESS = 0x0002
IOCTL_STORAGE_BASE = FILE_DEVICE_MASS_STORAGE
RECOVERED_WRITES_VALID = 0x00000001
UNRECOVERED_WRITES_VALID = 0x00000002
RECOVERED_READS_VALID = 0x00000004
UNRECOVERED_READS_VALID = 0x00000008
WRITE_COMPRESSION_INFO_VALID = 0x00000010
READ_COMPRESSION_INFO_VALID = 0x00000020
TAPE_RETURN_STATISTICS = 0
TAPE_RETURN_ENV_INFO = 1
TAPE_RESET_STATISTICS = 2
MEDIA_ERASEABLE = 0x00000001
MEDIA_WRITE_ONCE = 0x00000002
MEDIA_READ_ONLY = 0x00000004
MEDIA_READ_WRITE = 0x00000008
MEDIA_WRITE_PROTECTED = 0x00000100
MEDIA_CURRENTLY_MOUNTED = 0x80000000
IOCTL_DISK_BASE = FILE_DEVICE_DISK
PARTITION_ENTRY_UNUSED = 0x00
PARTITION_FAT_12 = 0x01
PARTITION_XENIX_1 = 0x02
PARTITION_XENIX_2 = 0x03
PARTITION_FAT_16 = 0x04
PARTITION_EXTENDED = 0x05
PARTITION_HUGE = 0x06
PARTITION_IFS = 0x07
PARTITION_OS2BOOTMGR = 0x0A
PARTITION_FAT32 = 0x0B
PARTITION_FAT32_XINT13 = 0x0C
PARTITION_XINT13 = 0x0E
PARTITION_XINT13_EXTENDED = 0x0F
PARTITION_PREP = 0x41
PARTITION_LDM = 0x42
PARTITION_UNIX = 0x63
VALID_NTFT = 0xC0
PARTITION_NTFT = 0x80

GPT_ATTRIBUTE_PLATFORM_REQUIRED = 0x0000000000000001
GPT_BASIC_DATA_ATTRIBUTE_NO_DRIVE_LETTER = 0x8000000000000000
GPT_BASIC_DATA_ATTRIBUTE_HIDDEN = 0x4000000000000000
GPT_BASIC_DATA_ATTRIBUTE_SHADOW_COPY = 0x2000000000000000
GPT_BASIC_DATA_ATTRIBUTE_READ_ONLY = 0x1000000000000000

HIST_NO_OF_BUCKETS = 24
DISK_LOGGING_START = 0
DISK_LOGGING_STOP = 1
DISK_LOGGING_DUMP = 2
DISK_BINNING = 3
CAP_ATA_ID_CMD = 1
CAP_ATAPI_ID_CMD = 2
CAP_SMART_CMD = 4
ATAPI_ID_CMD = 0xA1
ID_CMD = 0xEC
SMART_CMD = 0xB0
SMART_CYL_LOW = 0x4F
SMART_CYL_HI = 0xC2
SMART_NO_ERROR = 0
SMART_IDE_ERROR = 1
SMART_INVALID_FLAG = 2
SMART_INVALID_COMMAND = 3
SMART_INVALID_BUFFER = 4
SMART_INVALID_DRIVE = 5
SMART_INVALID_IOCTL = 6
SMART_ERROR_NO_MEM = 7
SMART_INVALID_REGISTER = 8
SMART_NOT_SUPPORTED = 9
SMART_NO_IDE_DEVICE = 10
SMART_OFFLINE_ROUTINE_OFFLINE = 0
SMART_SHORT_SELFTEST_OFFLINE = 1
SMART_EXTENDED_SELFTEST_OFFLINE = 2
SMART_ABORT_OFFLINE_SELFTEST = 127
SMART_SHORT_SELFTEST_CAPTIVE = 129
SMART_EXTENDED_SELFTEST_CAPTIVE = 130
READ_ATTRIBUTE_BUFFER_SIZE = 512
IDENTIFY_BUFFER_SIZE = 512
READ_THRESHOLD_BUFFER_SIZE = 512
SMART_LOG_SECTOR_SIZE = 512
READ_ATTRIBUTES = 0xD0
READ_THRESHOLDS = 0xD1
ENABLE_DISABLE_AUTOSAVE = 0xD2
SAVE_ATTRIBUTE_VALUES = 0xD3
EXECUTE_OFFLINE_DIAGS = 0xD4
SMART_READ_LOG = 0xD5
SMART_WRITE_LOG = 0xD6
ENABLE_SMART = 0xD8
DISABLE_SMART = 0xD9
RETURN_SMART_STATUS = 0xDA
ENABLE_DISABLE_AUTO_OFFLINE = 0xDB
IOCTL_CHANGER_BASE = FILE_DEVICE_CHANGER
MAX_VOLUME_ID_SIZE = 36
MAX_VOLUME_TEMPLATE_SIZE = 40
VENDOR_ID_LENGTH = 8
PRODUCT_ID_LENGTH = 16
REVISION_LENGTH = 4
SERIAL_NUMBER_LENGTH = 32
CHANGER_BAR_CODE_SCANNER_INSTALLED = 0x00000001
CHANGER_INIT_ELEM_STAT_WITH_RANGE = 0x00000002
CHANGER_CLOSE_IEPORT = 0x00000004
CHANGER_OPEN_IEPORT = 0x00000008
CHANGER_STATUS_NON_VOLATILE = 0x00000010
CHANGER_EXCHANGE_MEDIA = 0x00000020
CHANGER_CLEANER_SLOT = 0x00000040
CHANGER_LOCK_UNLOCK = 0x00000080
CHANGER_CARTRIDGE_MAGAZINE = 0x00000100
CHANGER_MEDIUM_FLIP = 0x00000200
CHANGER_POSITION_TO_ELEMENT = 0x00000400
CHANGER_REPORT_IEPORT_STATE = 0x00000800
CHANGER_STORAGE_DRIVE = 0x00001000
CHANGER_STORAGE_IEPORT = 0x00002000
CHANGER_STORAGE_SLOT = 0x00004000
CHANGER_STORAGE_TRANSPORT = 0x00008000
CHANGER_DRIVE_CLEANING_REQUIRED = 0x00010000
CHANGER_PREDISMOUNT_EJECT_REQUIRED = 0x00020000
CHANGER_CLEANER_ACCESS_NOT_VALID = 0x00040000
CHANGER_PREMOUNT_EJECT_REQUIRED = 0x00080000
CHANGER_VOLUME_IDENTIFICATION = 0x00100000
CHANGER_VOLUME_SEARCH = 0x00200000
CHANGER_VOLUME_ASSERT = 0x00400000
CHANGER_VOLUME_REPLACE = 0x00800000
CHANGER_VOLUME_UNDEFINE = 0x01000000
CHANGER_SERIAL_NUMBER_VALID = 0x04000000
CHANGER_DEVICE_REINITIALIZE_CAPABLE = 0x08000000
CHANGER_KEYPAD_ENABLE_DISABLE = 0x10000000
CHANGER_DRIVE_EMPTY_ON_DOOR_ACCESS = 0x20000000

CHANGER_RESERVED_BIT = 0x80000000
CHANGER_PREDISMOUNT_ALIGN_TO_SLOT = 0x80000001
CHANGER_PREDISMOUNT_ALIGN_TO_DRIVE = 0x80000002
CHANGER_CLEANER_AUTODISMOUNT = 0x80000004
CHANGER_TRUE_EXCHANGE_CAPABLE = 0x80000008
CHANGER_SLOTS_USE_TRAYS = 0x80000010
CHANGER_RTN_MEDIA_TO_ORIGINAL_ADDR = 0x80000020
CHANGER_CLEANER_OPS_NOT_SUPPORTED = 0x80000040
CHANGER_IEPORT_USER_CONTROL_OPEN = 0x80000080
CHANGER_IEPORT_USER_CONTROL_CLOSE = 0x80000100
CHANGER_MOVE_EXTENDS_IEPORT = 0x80000200
CHANGER_MOVE_RETRACTS_IEPORT = 0x80000400


CHANGER_TO_TRANSPORT = 0x01
CHANGER_TO_SLOT = 0x02
CHANGER_TO_IEPORT = 0x04
CHANGER_TO_DRIVE = 0x08
LOCK_UNLOCK_IEPORT = 0x01
LOCK_UNLOCK_DOOR = 0x02
LOCK_UNLOCK_KEYPAD = 0x04
LOCK_ELEMENT = 0
UNLOCK_ELEMENT = 1
EXTEND_IEPORT = 2
RETRACT_IEPORT = 3
ELEMENT_STATUS_FULL = 0x00000001
ELEMENT_STATUS_IMPEXP = 0x00000002
ELEMENT_STATUS_EXCEPT = 0x00000004
ELEMENT_STATUS_ACCESS = 0x00000008
ELEMENT_STATUS_EXENAB = 0x00000010
ELEMENT_STATUS_INENAB = 0x00000020
ELEMENT_STATUS_PRODUCT_DATA = 0x00000040
ELEMENT_STATUS_LUN_VALID = 0x00001000
ELEMENT_STATUS_ID_VALID = 0x00002000
ELEMENT_STATUS_NOT_BUS = 0x00008000
ELEMENT_STATUS_INVERT = 0x00400000
ELEMENT_STATUS_SVALID = 0x00800000
ELEMENT_STATUS_PVOLTAG = 0x10000000
ELEMENT_STATUS_AVOLTAG = 0x20000000
ERROR_LABEL_UNREADABLE = 0x00000001
ERROR_LABEL_QUESTIONABLE = 0x00000002
ERROR_SLOT_NOT_PRESENT = 0x00000004
ERROR_DRIVE_NOT_INSTALLED = 0x00000008
ERROR_TRAY_MALFUNCTION = 0x00000010
ERROR_INIT_STATUS_NEEDED = 0x00000011
ERROR_UNHANDLED_ERROR = 0xFFFFFFFF
SEARCH_ALL = 0x0
SEARCH_PRIMARY = 0x1
SEARCH_ALTERNATE = 0x2
SEARCH_ALL_NO_SEQ = 0x4
SEARCH_PRI_NO_SEQ = 0x5
SEARCH_ALT_NO_SEQ = 0x6
ASSERT_PRIMARY = 0x8
ASSERT_ALTERNATE = 0x9
REPLACE_PRIMARY = 0xA
REPLACE_ALTERNATE = 0xB
UNDEFINE_PRIMARY = 0xC
UNDEFINE_ALTERNATE = 0xD
USN_PAGE_SIZE = 0x1000
USN_REASON_DATA_OVERWRITE = 0x00000001
USN_REASON_DATA_EXTEND = 0x00000002
USN_REASON_DATA_TRUNCATION = 0x00000004
USN_REASON_NAMED_DATA_OVERWRITE = 0x00000010
USN_REASON_NAMED_DATA_EXTEND = 0x00000020
USN_REASON_NAMED_DATA_TRUNCATION = 0x00000040
USN_REASON_FILE_CREATE = 0x00000100
USN_REASON_FILE_DELETE = 0x00000200
USN_REASON_EA_CHANGE = 0x00000400
USN_REASON_SECURITY_CHANGE = 0x00000800
USN_REASON_RENAME_OLD_NAME = 0x00001000
USN_REASON_RENAME_NEW_NAME = 0x00002000
USN_REASON_INDEXABLE_CHANGE = 0x00004000
USN_REASON_BASIC_INFO_CHANGE = 0x00008000
USN_REASON_HARD_LINK_CHANGE = 0x00010000
USN_REASON_COMPRESSION_CHANGE = 0x00020000
USN_REASON_ENCRYPTION_CHANGE = 0x00040000
USN_REASON_OBJECT_ID_CHANGE = 0x00080000
USN_REASON_REPARSE_POINT_CHANGE = 0x00100000
USN_REASON_STREAM_CHANGE = 0x00200000
USN_REASON_TRANSACTED_CHANGE = 0x00400000
USN_REASON_CLOSE = 0x80000000
USN_DELETE_FLAG_DELETE = 0x00000001
USN_DELETE_FLAG_NOTIFY = 0x00000002
USN_DELETE_VALID_FLAGS = 0x00000003
USN_SOURCE_DATA_MANAGEMENT = 0x00000001
USN_SOURCE_AUXILIARY_DATA = 0x00000002
USN_SOURCE_REPLICATION_MANAGEMENT = 0x00000004

MARK_HANDLE_PROTECT_CLUSTERS = 1
MARK_HANDLE_TXF_SYSTEM_LOG = 4
MARK_HANDLE_NOT_TXF_SYSTEM_LOG = 8

VOLUME_IS_DIRTY = 0x00000001
VOLUME_UPGRADE_SCHEDULED = 0x00000002
VOLUME_SESSION_OPEN = 4

FILE_PREFETCH_TYPE_FOR_CREATE = 1
FILE_PREFETCH_TYPE_FOR_DIRENUM = 2
FILE_PREFETCH_TYPE_FOR_CREATE_EX = 3
FILE_PREFETCH_TYPE_FOR_DIRENUM_EX = 4
FILE_PREFETCH_TYPE_MAX = 4

FILESYSTEM_STATISTICS_TYPE_NTFS = 1
FILESYSTEM_STATISTICS_TYPE_FAT = 2
FILE_SET_ENCRYPTION = 0x00000001
FILE_CLEAR_ENCRYPTION = 0x00000002
STREAM_SET_ENCRYPTION = 0x00000003
STREAM_CLEAR_ENCRYPTION = 0x00000004
MAXIMUM_ENCRYPTION_VALUE = 0x00000004
ENCRYPTION_FORMAT_DEFAULT = 0x01
COMPRESSION_FORMAT_SPARSE = 0x4000
COPYFILE_SIS_LINK = 0x0001
COPYFILE_SIS_REPLACE = 0x0002
COPYFILE_SIS_FLAGS = 0x0003

WMI_DISK_GEOMETRY_GUID = pywintypes.IID("{25007F51-57C2-11D1-A528-00A0C9062910}")
GUID_DEVINTERFACE_CDROM = pywintypes.IID("{53F56308-B6BF-11D0-94F2-00A0C91EFB8B}")
GUID_DEVINTERFACE_FLOPPY = pywintypes.IID("{53F56311-B6BF-11D0-94F2-00A0C91EFB8B}")
GUID_DEVINTERFACE_SERENUM_BUS_ENUMERATOR = pywintypes.IID(
    "{4D36E978-E325-11CE-BFC1-08002BE10318}"
)
GUID_DEVINTERFACE_COMPORT = pywintypes.IID("{86E0D1E0-8089-11D0-9CE4-08003E301F73}")
GUID_DEVINTERFACE_DISK = pywintypes.IID("{53F56307-B6BF-11D0-94F2-00A0C91EFB8B}")
GUID_DEVINTERFACE_STORAGEPORT = pywintypes.IID("{2ACCFE60-C130-11D2-B082-00A0C91EFB8B}")
GUID_DEVINTERFACE_CDCHANGER = pywintypes.IID("{53F56312-B6BF-11D0-94F2-00A0C91EFB8B}")
GUID_DEVINTERFACE_PARTITION = pywintypes.IID("{53F5630A-B6BF-11D0-94F2-00A0C91EFB8B}")
GUID_DEVINTERFACE_VOLUME = pywintypes.IID("{53F5630D-B6BF-11D0-94F2-00A0C91EFB8B}")
GUID_DEVINTERFACE_WRITEONCEDISK = pywintypes.IID(
    "{53F5630C-B6BF-11D0-94F2-00A0C91EFB8B}"
)
GUID_DEVINTERFACE_TAPE = pywintypes.IID("{53F5630B-B6BF-11D0-94F2-00A0C91EFB8B}")
GUID_DEVINTERFACE_MEDIUMCHANGER = pywintypes.IID(
    "{53F56310-B6BF-11D0-94F2-00A0C91EFB8B}"
)
GUID_SERENUM_BUS_ENUMERATOR = GUID_DEVINTERFACE_SERENUM_BUS_ENUMERATOR
GUID_CLASS_COMPORT = GUID_DEVINTERFACE_COMPORT

DiskClassGuid = GUID_DEVINTERFACE_DISK
CdRomClassGuid = GUID_DEVINTERFACE_CDROM
PartitionClassGuid = GUID_DEVINTERFACE_PARTITION
TapeClassGuid = GUID_DEVINTERFACE_TAPE
WriteOnceDiskClassGuid = GUID_DEVINTERFACE_WRITEONCEDISK
VolumeClassGuid = GUID_DEVINTERFACE_VOLUME
MediumChangerClassGuid = GUID_DEVINTERFACE_MEDIUMCHANGER
FloppyClassGuid = GUID_DEVINTERFACE_FLOPPY
CdChangerClassGuid = GUID_DEVINTERFACE_CDCHANGER
StoragePortClassGuid = GUID_DEVINTERFACE_STORAGEPORT


IOCTL_STORAGE_CHECK_VERIFY = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0200, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_STORAGE_CHECK_VERIFY2 = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0200, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_STORAGE_MEDIA_REMOVAL = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0201, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_STORAGE_EJECT_MEDIA = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0202, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_STORAGE_LOAD_MEDIA = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0203, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_STORAGE_LOAD_MEDIA2 = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0203, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_STORAGE_RESERVE = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0204, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_STORAGE_RELEASE = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0205, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_STORAGE_FIND_NEW_DEVICES = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0206, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_STORAGE_EJECTION_CONTROL = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0250, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_STORAGE_MCN_CONTROL = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0251, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_STORAGE_GET_MEDIA_TYPES = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0300, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_STORAGE_GET_MEDIA_TYPES_EX = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0301, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_STORAGE_GET_MEDIA_SERIAL_NUMBER = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0304, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_STORAGE_GET_HOTPLUG_INFO = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0305, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_STORAGE_SET_HOTPLUG_INFO = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0306, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_STORAGE_RESET_BUS = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0400, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_STORAGE_RESET_DEVICE = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0401, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_STORAGE_BREAK_RESERVATION = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0405, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_STORAGE_GET_DEVICE_NUMBER = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0420, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_STORAGE_PREDICT_FAILURE = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0440, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_GET_DRIVE_GEOMETRY = CTL_CODE(
    IOCTL_DISK_BASE, 0x0000, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_GET_PARTITION_INFO = CTL_CODE(
    IOCTL_DISK_BASE, 0x0001, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_SET_PARTITION_INFO = CTL_CODE(
    IOCTL_DISK_BASE, 0x0002, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_GET_DRIVE_LAYOUT = CTL_CODE(
    IOCTL_DISK_BASE, 0x0003, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_SET_DRIVE_LAYOUT = CTL_CODE(
    IOCTL_DISK_BASE, 0x0004, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_VERIFY = CTL_CODE(IOCTL_DISK_BASE, 0x0005, METHOD_BUFFERED, FILE_ANY_ACCESS)
IOCTL_DISK_FORMAT_TRACKS = CTL_CODE(
    IOCTL_DISK_BASE, 0x0006, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_REASSIGN_BLOCKS = CTL_CODE(
    IOCTL_DISK_BASE, 0x0007, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_PERFORMANCE = CTL_CODE(
    IOCTL_DISK_BASE, 0x0008, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_IS_WRITABLE = CTL_CODE(
    IOCTL_DISK_BASE, 0x0009, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_LOGGING = CTL_CODE(IOCTL_DISK_BASE, 0x000A, METHOD_BUFFERED, FILE_ANY_ACCESS)
IOCTL_DISK_FORMAT_TRACKS_EX = CTL_CODE(
    IOCTL_DISK_BASE, 0x000B, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_HISTOGRAM_STRUCTURE = CTL_CODE(
    IOCTL_DISK_BASE, 0x000C, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_HISTOGRAM_DATA = CTL_CODE(
    IOCTL_DISK_BASE, 0x000D, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_HISTOGRAM_RESET = CTL_CODE(
    IOCTL_DISK_BASE, 0x000E, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_REQUEST_STRUCTURE = CTL_CODE(
    IOCTL_DISK_BASE, 0x000F, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_REQUEST_DATA = CTL_CODE(
    IOCTL_DISK_BASE, 0x0010, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_PERFORMANCE_OFF = CTL_CODE(
    IOCTL_DISK_BASE, 0x0018, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_CONTROLLER_NUMBER = CTL_CODE(
    IOCTL_DISK_BASE, 0x0011, METHOD_BUFFERED, FILE_ANY_ACCESS
)
SMART_GET_VERSION = CTL_CODE(IOCTL_DISK_BASE, 0x0020, METHOD_BUFFERED, FILE_READ_ACCESS)
SMART_SEND_DRIVE_COMMAND = CTL_CODE(
    IOCTL_DISK_BASE, 0x0021, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
SMART_RCV_DRIVE_DATA = CTL_CODE(
    IOCTL_DISK_BASE, 0x0022, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_GET_PARTITION_INFO_EX = CTL_CODE(
    IOCTL_DISK_BASE, 0x0012, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_SET_PARTITION_INFO_EX = CTL_CODE(
    IOCTL_DISK_BASE, 0x0013, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_GET_DRIVE_LAYOUT_EX = CTL_CODE(
    IOCTL_DISK_BASE, 0x0014, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_SET_DRIVE_LAYOUT_EX = CTL_CODE(
    IOCTL_DISK_BASE, 0x0015, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_CREATE_DISK = CTL_CODE(
    IOCTL_DISK_BASE, 0x0016, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_GET_LENGTH_INFO = CTL_CODE(
    IOCTL_DISK_BASE, 0x0017, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_GET_DRIVE_GEOMETRY_EX = CTL_CODE(
    IOCTL_DISK_BASE, 0x0028, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_REASSIGN_BLOCKS_EX = CTL_CODE(
    IOCTL_DISK_BASE, 0x0029, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)

IOCTL_DISK_UPDATE_DRIVE_SIZE = CTL_CODE(
    IOCTL_DISK_BASE, 0x0032, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_GROW_PARTITION = CTL_CODE(
    IOCTL_DISK_BASE, 0x0034, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_GET_CACHE_INFORMATION = CTL_CODE(
    IOCTL_DISK_BASE, 0x0035, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_SET_CACHE_INFORMATION = CTL_CODE(
    IOCTL_DISK_BASE, 0x0036, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)

OBSOLETE_IOCTL_STORAGE_RESET_BUS = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0400, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
OBSOLETE_IOCTL_STORAGE_RESET_DEVICE = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0401, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
## the original define no longer exists in winioctl.h
OBSOLETE_DISK_GET_WRITE_CACHE_STATE = CTL_CODE(
    IOCTL_DISK_BASE, 0x0037, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_GET_WRITE_CACHE_STATE = OBSOLETE_DISK_GET_WRITE_CACHE_STATE


IOCTL_DISK_DELETE_DRIVE_LAYOUT = CTL_CODE(
    IOCTL_DISK_BASE, 0x0040, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_UPDATE_PROPERTIES = CTL_CODE(
    IOCTL_DISK_BASE, 0x0050, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_FORMAT_DRIVE = CTL_CODE(
    IOCTL_DISK_BASE, 0x00F3, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_SENSE_DEVICE = CTL_CODE(
    IOCTL_DISK_BASE, 0x00F8, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_CHECK_VERIFY = CTL_CODE(
    IOCTL_DISK_BASE, 0x0200, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_MEDIA_REMOVAL = CTL_CODE(
    IOCTL_DISK_BASE, 0x0201, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_EJECT_MEDIA = CTL_CODE(
    IOCTL_DISK_BASE, 0x0202, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_LOAD_MEDIA = CTL_CODE(
    IOCTL_DISK_BASE, 0x0203, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_RESERVE = CTL_CODE(
    IOCTL_DISK_BASE, 0x0204, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_RELEASE = CTL_CODE(
    IOCTL_DISK_BASE, 0x0205, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_FIND_NEW_DEVICES = CTL_CODE(
    IOCTL_DISK_BASE, 0x0206, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_GET_MEDIA_TYPES = CTL_CODE(
    IOCTL_DISK_BASE, 0x0300, METHOD_BUFFERED, FILE_ANY_ACCESS
)

DISK_HISTOGRAM_SIZE = 72
HISTOGRAM_BUCKET_SIZE = 8

IOCTL_CHANGER_GET_PARAMETERS = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x0000, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_CHANGER_GET_STATUS = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x0001, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_CHANGER_GET_PRODUCT_DATA = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x0002, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_CHANGER_SET_ACCESS = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x0004, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_CHANGER_GET_ELEMENT_STATUS = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x0005, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_CHANGER_INITIALIZE_ELEMENT_STATUS = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x0006, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_CHANGER_SET_POSITION = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x0007, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_CHANGER_EXCHANGE_MEDIUM = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x0008, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_CHANGER_MOVE_MEDIUM = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x0009, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_CHANGER_REINITIALIZE_TRANSPORT = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x000A, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_CHANGER_QUERY_VOLUME_TAGS = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x000B, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_SERIAL_LSRMST_INSERT = CTL_CODE(
    FILE_DEVICE_SERIAL_PORT, 31, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_SERENUM_EXPOSE_HARDWARE = CTL_CODE(
    FILE_DEVICE_SERENUM, 128, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_SERENUM_REMOVE_HARDWARE = CTL_CODE(
    FILE_DEVICE_SERENUM, 129, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_SERENUM_PORT_DESC = CTL_CODE(
    FILE_DEVICE_SERENUM, 130, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_SERENUM_GET_PORT_NAME = CTL_CODE(
    FILE_DEVICE_SERENUM, 131, METHOD_BUFFERED, FILE_ANY_ACCESS
)

## ??? can't find where FILE_DEVICE_AVIO is defined ???
## IOCTL_AVIO_ALLOCATE_STREAM = CTL_CODE(FILE_DEVICE_AVIO, 1, METHOD_BUFFERED, FILE_SPECIAL_ACCESS)
## IOCTL_AVIO_FREE_STREAM = CTL_CODE(FILE_DEVICE_AVIO, 2, METHOD_BUFFERED, FILE_SPECIAL_ACCESS)
## IOCTL_AVIO_MODIFY_STREAM = CTL_CODE(FILE_DEVICE_AVIO, 3, METHOD_BUFFERED, FILE_SPECIAL_ACCESS)

SERIAL_LSRMST_ESCAPE = 0x00
SERIAL_LSRMST_LSR_DATA = 0x01
SERIAL_LSRMST_LSR_NODATA = 0x02
SERIAL_LSRMST_MST = 0x03
SERIAL_IOC_FCR_FIFO_ENABLE = 0x00000001
SERIAL_IOC_FCR_RCVR_RESET = 0x00000002
SERIAL_IOC_FCR_XMIT_RESET = 0x00000004
SERIAL_IOC_FCR_DMA_MODE = 0x00000008
SERIAL_IOC_FCR_RES1 = 0x00000010
SERIAL_IOC_FCR_RES2 = 0x00000020
SERIAL_IOC_FCR_RCVR_TRIGGER_LSB = 0x00000040
SERIAL_IOC_FCR_RCVR_TRIGGER_MSB = 0x00000080
SERIAL_IOC_MCR_DTR = 0x00000001
SERIAL_IOC_MCR_RTS = 0x00000002
SERIAL_IOC_MCR_OUT1 = 0x00000004
SERIAL_IOC_MCR_OUT2 = 0x00000008
SERIAL_IOC_MCR_LOOP = 0x00000010
FSCTL_REQUEST_OPLOCK_LEVEL_1 = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 0, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_REQUEST_OPLOCK_LEVEL_2 = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 1, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_REQUEST_BATCH_OPLOCK = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 2, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_OPLOCK_BREAK_ACKNOWLEDGE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 3, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_OPBATCH_ACK_CLOSE_PENDING = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 4, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_OPLOCK_BREAK_NOTIFY = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 5, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_LOCK_VOLUME = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 6, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_UNLOCK_VOLUME = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 7, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_DISMOUNT_VOLUME = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 8, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_IS_VOLUME_MOUNTED = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 10, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_IS_PATHNAME_VALID = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 11, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_MARK_VOLUME_DIRTY = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 12, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_QUERY_RETRIEVAL_POINTERS = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 14, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_GET_COMPRESSION = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 15, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_SET_COMPRESSION = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 16, METHOD_BUFFERED, FILE_READ_DATA | FILE_WRITE_DATA
)
FSCTL_MARK_AS_SYSTEM_HIVE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 19, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_OPLOCK_BREAK_ACK_NO_2 = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 20, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_INVALIDATE_VOLUMES = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 21, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_QUERY_FAT_BPB = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 22, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_REQUEST_FILTER_OPLOCK = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 23, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_FILESYSTEM_GET_STATISTICS = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 24, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_GET_NTFS_VOLUME_DATA = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 25, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_GET_NTFS_FILE_RECORD = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 26, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_GET_VOLUME_BITMAP = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 27, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_GET_RETRIEVAL_POINTERS = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 28, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_MOVE_FILE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 29, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_IS_VOLUME_DIRTY = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 30, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_ALLOW_EXTENDED_DASD_IO = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 32, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_FIND_FILES_BY_SID = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 35, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_SET_OBJECT_ID = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 38, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_GET_OBJECT_ID = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 39, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_DELETE_OBJECT_ID = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 40, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_SET_REPARSE_POINT = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 41, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_GET_REPARSE_POINT = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 42, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_DELETE_REPARSE_POINT = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 43, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_ENUM_USN_DATA = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 44, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_SECURITY_ID_CHECK = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 45, METHOD_NEITHER, FILE_READ_DATA
)
FSCTL_READ_USN_JOURNAL = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 46, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_SET_OBJECT_ID_EXTENDED = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 47, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_CREATE_OR_GET_OBJECT_ID = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 48, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_SET_SPARSE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 49, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_SET_ZERO_DATA = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 50, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_QUERY_ALLOCATED_RANGES = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 51, METHOD_NEITHER, FILE_READ_DATA
)
FSCTL_SET_ENCRYPTION = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 53, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_ENCRYPTION_FSCTL_IO = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 54, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_WRITE_RAW_ENCRYPTED = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 55, METHOD_NEITHER, FILE_SPECIAL_ACCESS
)
FSCTL_READ_RAW_ENCRYPTED = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 56, METHOD_NEITHER, FILE_SPECIAL_ACCESS
)
FSCTL_CREATE_USN_JOURNAL = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 57, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_READ_FILE_USN_DATA = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 58, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_WRITE_USN_CLOSE_RECORD = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 59, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_EXTEND_VOLUME = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 60, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_QUERY_USN_JOURNAL = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 61, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_DELETE_USN_JOURNAL = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 62, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_MARK_HANDLE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 63, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_SIS_COPYFILE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 64, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_SIS_LINK_FILES = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 65, METHOD_BUFFERED, FILE_READ_DATA | FILE_WRITE_DATA
)
FSCTL_HSM_MSG = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 66, METHOD_BUFFERED, FILE_READ_DATA | FILE_WRITE_DATA
)
FSCTL_HSM_DATA = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 68, METHOD_NEITHER, FILE_READ_DATA | FILE_WRITE_DATA
)
FSCTL_RECALL_FILE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 69, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_READ_FROM_PLEX = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 71, METHOD_OUT_DIRECT, FILE_READ_DATA
)
FSCTL_FILE_PREFETCH = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 72, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_MAKE_MEDIA_COMPATIBLE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 76, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_SET_DEFECT_MANAGEMENT = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 77, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_QUERY_SPARING_INFO = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 78, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_QUERY_ON_DISK_VOLUME_INFO = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 79, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_SET_VOLUME_COMPRESSION_STATE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 80, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_TXFS_MODIFY_RM = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 81, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_TXFS_QUERY_RM_INFORMATION = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 82, METHOD_BUFFERED, FILE_READ_DATA
)
FSCTL_TXFS_ROLLFORWARD_REDO = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 84, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_TXFS_ROLLFORWARD_UNDO = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 85, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_TXFS_START_RM = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 86, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_TXFS_SHUTDOWN_RM = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 87, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_TXFS_READ_BACKUP_INFORMATION = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 88, METHOD_BUFFERED, FILE_READ_DATA
)
FSCTL_TXFS_WRITE_BACKUP_INFORMATION = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 89, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_TXFS_CREATE_SECONDARY_RM = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 90, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_TXFS_GET_METADATA_INFO = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 91, METHOD_BUFFERED, FILE_READ_DATA
)
FSCTL_TXFS_GET_TRANSACTED_VERSION = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 92, METHOD_BUFFERED, FILE_READ_DATA
)
FSCTL_TXFS_CREATE_MINIVERSION = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 95, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_TXFS_TRANSACTION_ACTIVE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 99, METHOD_BUFFERED, FILE_READ_DATA
)
FSCTL_SET_ZERO_ON_DEALLOCATION = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 101, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_SET_REPAIR = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 102, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_GET_REPAIR = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 103, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_WAIT_FOR_REPAIR = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 104, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_INITIATE_REPAIR = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 106, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_CSC_INTERNAL = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 107, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_SHRINK_VOLUME = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 108, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_SET_SHORT_NAME_BEHAVIOR = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 109, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_DFSR_SET_GHOST_HANDLE_STATE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 110, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_TXFS_LIST_TRANSACTION_LOCKED_FILES = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 120, METHOD_BUFFERED, FILE_READ_DATA
)
FSCTL_TXFS_LIST_TRANSACTIONS = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 121, METHOD_BUFFERED, FILE_READ_DATA
)
FSCTL_QUERY_PAGEFILE_ENCRYPTION = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 122, METHOD_BUFFERED, FILE_ANY_ACCESS
)

IOCTL_VOLUME_BASE = ord("V")
IOCTL_VOLUME_GET_VOLUME_DISK_EXTENTS = CTL_CODE(
    IOCTL_VOLUME_BASE, 0, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_VOLUME_ONLINE = CTL_CODE(
    IOCTL_VOLUME_BASE, 2, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_VOLUME_OFFLINE = CTL_CODE(
    IOCTL_VOLUME_BASE, 3, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_VOLUME_IS_CLUSTERED = CTL_CODE(
    IOCTL_VOLUME_BASE, 12, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_VOLUME_GET_GPT_ATTRIBUTES = CTL_CODE(
    IOCTL_VOLUME_BASE, 14, METHOD_BUFFERED, FILE_ANY_ACCESS
)

## enums
## STORAGE_MEDIA_TYPE
DDS_4mm = 32
MiniQic = 33
Travan = 34
QIC = 35
MP_8mm = 36
AME_8mm = 37
AIT1_8mm = 38
DLT = 39
NCTP = 40
IBM_3480 = 41
IBM_3490E = 42
IBM_Magstar_3590 = 43
IBM_Magstar_MP = 44
STK_DATA_D3 = 45
SONY_DTF = 46
DV_6mm = 47
DMI = 48
SONY_D2 = 49
CLEANER_CARTRIDGE = 50
CD_ROM = 51
CD_R = 52
CD_RW = 53
DVD_ROM = 54
DVD_R = 55
DVD_RW = 56
MO_3_RW = 57
MO_5_WO = 58
MO_5_RW = 59
MO_5_LIMDOW = 60
PC_5_WO = 61
PC_5_RW = 62
PD_5_RW = 63
ABL_5_WO = 64
PINNACLE_APEX_5_RW = 65
SONY_12_WO = 66
PHILIPS_12_WO = 67
HITACHI_12_WO = 68
CYGNET_12_WO = 69
KODAK_14_WO = 70
MO_NFR_525 = 71
NIKON_12_RW = 72
IOMEGA_ZIP = 73
IOMEGA_JAZ = 74
SYQUEST_EZ135 = 75
SYQUEST_EZFLYER = 76
SYQUEST_SYJET = 77
AVATAR_F2 = 78
MP2_8mm = 79
DST_S = 80
DST_M = 81
DST_L = 82
VXATape_1 = 83
VXATape_2 = 84
STK_9840 = 85
LTO_Ultrium = 86
LTO_Accelis = 87
DVD_RAM = 88
AIT_8mm = 89
ADR_1 = 90
ADR_2 = 91
STK_9940 = 92

## STORAGE_BUS_TYPE
BusTypeUnknown = 0
BusTypeScsi = 1
BusTypeAtapi = 2
BusTypeAta = 3
BusType1394 = 4
BusTypeSsa = 5
BusTypeFibre = 6
BusTypeUsb = 7
BusTypeRAID = 8
BusTypeiScsi = 9
BusTypeSas = 10
BusTypeSata = 11
BusTypeMaxReserved = 127

## MEDIA_TYPE
Unknown = 0
F5_1Pt2_512 = 1
F3_1Pt44_512 = 2
F3_2Pt88_512 = 3
F3_20Pt8_512 = 4
F3_720_512 = 5
F5_360_512 = 6
F5_320_512 = 7
F5_320_1024 = 8
F5_180_512 = 9
F5_160_512 = 10
RemovableMedia = 11
FixedMedia = 12
F3_120M_512 = 13
F3_640_512 = 14
F5_640_512 = 15
F5_720_512 = 16
F3_1Pt2_512 = 17
F3_1Pt23_1024 = 18
F5_1Pt23_1024 = 19
F3_128Mb_512 = 20
F3_230Mb_512 = 21
F8_256_128 = 22
F3_200Mb_512 = 23
F3_240M_512 = 24
F3_32M_512 = 25

## PARTITION_STYLE
PARTITION_STYLE_MBR = 0
PARTITION_STYLE_GPT = 1
PARTITION_STYLE_RAW = 2

## DETECTION_TYPE
DetectNone = 0
DetectInt13 = 1
DetectExInt13 = 2

## DISK_CACHE_RETENTION_PRIORITY
EqualPriority = 0
KeepPrefetchedData = 1
KeepReadData = 2

## DISK_WRITE_CACHE_STATE - ?????? this enum has disappeared from winioctl.h in windows 2003 SP1 sdk ??????
DiskWriteCacheNormal = 0
DiskWriteCacheForceDisable = 1
DiskWriteCacheDisableNotSupported = 2

## BIN_TYPES
RequestSize = 0
RequestLocation = 1

## CHANGER_DEVICE_PROBLEM_TYPE
DeviceProblemNone = 0
DeviceProblemHardware = 1
DeviceProblemCHMError = 2
DeviceProblemDoorOpen = 3
DeviceProblemCalibrationError = 4
DeviceProblemTargetFailure = 5
DeviceProblemCHMMoveError = 6
DeviceProblemCHMZeroError = 7
DeviceProblemCartridgeInsertError = 8
DeviceProblemPositionError = 9
DeviceProblemSensorError = 10
DeviceProblemCartridgeEjectError = 11
DeviceProblemGripperError = 12
DeviceProblemDriveError = 13

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\win32\lib\winioctlcon.py ===
## flags, enums, guids used with DeviceIoControl from WinIoCtl.h

import pywintypes
from ntsecuritycon import FILE_READ_DATA, FILE_WRITE_DATA


def CTL_CODE(DeviceType, Function, Method, Access):
    return (DeviceType << 16) | (Access << 14) | (Function << 2) | Method


def DEVICE_TYPE_FROM_CTL_CODE(ctrlCode):
    return (ctrlCode & 0xFFFF0000) >> 16


FILE_DEVICE_BEEP = 0x00000001
FILE_DEVICE_CD_ROM = 0x00000002
FILE_DEVICE_CD_ROM_FILE_SYSTEM = 0x00000003
FILE_DEVICE_CONTROLLER = 0x00000004
FILE_DEVICE_DATALINK = 0x00000005
FILE_DEVICE_DFS = 0x00000006
FILE_DEVICE_DISK = 0x00000007
FILE_DEVICE_DISK_FILE_SYSTEM = 0x00000008
FILE_DEVICE_FILE_SYSTEM = 0x00000009
FILE_DEVICE_INPORT_PORT = 0x0000000A
FILE_DEVICE_KEYBOARD = 0x0000000B
FILE_DEVICE_MAILSLOT = 0x0000000C
FILE_DEVICE_MIDI_IN = 0x0000000D
FILE_DEVICE_MIDI_OUT = 0x0000000E
FILE_DEVICE_MOUSE = 0x0000000F
FILE_DEVICE_MULTI_UNC_PROVIDER = 0x00000010
FILE_DEVICE_NAMED_PIPE = 0x00000011
FILE_DEVICE_NETWORK = 0x00000012
FILE_DEVICE_NETWORK_BROWSER = 0x00000013
FILE_DEVICE_NETWORK_FILE_SYSTEM = 0x00000014
FILE_DEVICE_NULL = 0x00000015
FILE_DEVICE_PARALLEL_PORT = 0x00000016
FILE_DEVICE_PHYSICAL_NETCARD = 0x00000017
FILE_DEVICE_PRINTER = 0x00000018
FILE_DEVICE_SCANNER = 0x00000019
FILE_DEVICE_SERIAL_MOUSE_PORT = 0x0000001A
FILE_DEVICE_SERIAL_PORT = 0x0000001B
FILE_DEVICE_SCREEN = 0x0000001C
FILE_DEVICE_SOUND = 0x0000001D
FILE_DEVICE_STREAMS = 0x0000001E
FILE_DEVICE_TAPE = 0x0000001F
FILE_DEVICE_TAPE_FILE_SYSTEM = 0x00000020
FILE_DEVICE_TRANSPORT = 0x00000021
FILE_DEVICE_UNKNOWN = 0x00000022
FILE_DEVICE_VIDEO = 0x00000023
FILE_DEVICE_VIRTUAL_DISK = 0x00000024
FILE_DEVICE_WAVE_IN = 0x00000025
FILE_DEVICE_WAVE_OUT = 0x00000026
FILE_DEVICE_8042_PORT = 0x00000027
FILE_DEVICE_NETWORK_REDIRECTOR = 0x00000028
FILE_DEVICE_BATTERY = 0x00000029
FILE_DEVICE_BUS_EXTENDER = 0x0000002A
FILE_DEVICE_MODEM = 0x0000002B
FILE_DEVICE_VDM = 0x0000002C
FILE_DEVICE_MASS_STORAGE = 0x0000002D
FILE_DEVICE_SMB = 0x0000002E
FILE_DEVICE_KS = 0x0000002F
FILE_DEVICE_CHANGER = 0x00000030
FILE_DEVICE_SMARTCARD = 0x00000031
FILE_DEVICE_ACPI = 0x00000032
FILE_DEVICE_DVD = 0x00000033
FILE_DEVICE_FULLSCREEN_VIDEO = 0x00000034
FILE_DEVICE_DFS_FILE_SYSTEM = 0x00000035
FILE_DEVICE_DFS_VOLUME = 0x00000036
FILE_DEVICE_SERENUM = 0x00000037
FILE_DEVICE_TERMSRV = 0x00000038
FILE_DEVICE_KSEC = 0x00000039
FILE_DEVICE_FIPS = 0x0000003A
FILE_DEVICE_INFINIBAND = 0x0000003B

METHOD_BUFFERED = 0
METHOD_IN_DIRECT = 1
METHOD_OUT_DIRECT = 2
METHOD_NEITHER = 3
METHOD_DIRECT_TO_HARDWARE = METHOD_IN_DIRECT
METHOD_DIRECT_FROM_HARDWARE = METHOD_OUT_DIRECT
FILE_ANY_ACCESS = 0
FILE_SPECIAL_ACCESS = FILE_ANY_ACCESS
FILE_READ_ACCESS = 0x0001
FILE_WRITE_ACCESS = 0x0002
IOCTL_STORAGE_BASE = FILE_DEVICE_MASS_STORAGE
RECOVERED_WRITES_VALID = 0x00000001
UNRECOVERED_WRITES_VALID = 0x00000002
RECOVERED_READS_VALID = 0x00000004
UNRECOVERED_READS_VALID = 0x00000008
WRITE_COMPRESSION_INFO_VALID = 0x00000010
READ_COMPRESSION_INFO_VALID = 0x00000020
TAPE_RETURN_STATISTICS = 0
TAPE_RETURN_ENV_INFO = 1
TAPE_RESET_STATISTICS = 2
MEDIA_ERASEABLE = 0x00000001
MEDIA_WRITE_ONCE = 0x00000002
MEDIA_READ_ONLY = 0x00000004
MEDIA_READ_WRITE = 0x00000008
MEDIA_WRITE_PROTECTED = 0x00000100
MEDIA_CURRENTLY_MOUNTED = 0x80000000
IOCTL_DISK_BASE = FILE_DEVICE_DISK
PARTITION_ENTRY_UNUSED = 0x00
PARTITION_FAT_12 = 0x01
PARTITION_XENIX_1 = 0x02
PARTITION_XENIX_2 = 0x03
PARTITION_FAT_16 = 0x04
PARTITION_EXTENDED = 0x05
PARTITION_HUGE = 0x06
PARTITION_IFS = 0x07
PARTITION_OS2BOOTMGR = 0x0A
PARTITION_FAT32 = 0x0B
PARTITION_FAT32_XINT13 = 0x0C
PARTITION_XINT13 = 0x0E
PARTITION_XINT13_EXTENDED = 0x0F
PARTITION_PREP = 0x41
PARTITION_LDM = 0x42
PARTITION_UNIX = 0x63
VALID_NTFT = 0xC0
PARTITION_NTFT = 0x80

GPT_ATTRIBUTE_PLATFORM_REQUIRED = 0x0000000000000001
GPT_BASIC_DATA_ATTRIBUTE_NO_DRIVE_LETTER = 0x8000000000000000
GPT_BASIC_DATA_ATTRIBUTE_HIDDEN = 0x4000000000000000
GPT_BASIC_DATA_ATTRIBUTE_SHADOW_COPY = 0x2000000000000000
GPT_BASIC_DATA_ATTRIBUTE_READ_ONLY = 0x1000000000000000

HIST_NO_OF_BUCKETS = 24
DISK_LOGGING_START = 0
DISK_LOGGING_STOP = 1
DISK_LOGGING_DUMP = 2
DISK_BINNING = 3
CAP_ATA_ID_CMD = 1
CAP_ATAPI_ID_CMD = 2
CAP_SMART_CMD = 4
ATAPI_ID_CMD = 0xA1
ID_CMD = 0xEC
SMART_CMD = 0xB0
SMART_CYL_LOW = 0x4F
SMART_CYL_HI = 0xC2
SMART_NO_ERROR = 0
SMART_IDE_ERROR = 1
SMART_INVALID_FLAG = 2
SMART_INVALID_COMMAND = 3
SMART_INVALID_BUFFER = 4
SMART_INVALID_DRIVE = 5
SMART_INVALID_IOCTL = 6
SMART_ERROR_NO_MEM = 7
SMART_INVALID_REGISTER = 8
SMART_NOT_SUPPORTED = 9
SMART_NO_IDE_DEVICE = 10
SMART_OFFLINE_ROUTINE_OFFLINE = 0
SMART_SHORT_SELFTEST_OFFLINE = 1
SMART_EXTENDED_SELFTEST_OFFLINE = 2
SMART_ABORT_OFFLINE_SELFTEST = 127
SMART_SHORT_SELFTEST_CAPTIVE = 129
SMART_EXTENDED_SELFTEST_CAPTIVE = 130
READ_ATTRIBUTE_BUFFER_SIZE = 512
IDENTIFY_BUFFER_SIZE = 512
READ_THRESHOLD_BUFFER_SIZE = 512
SMART_LOG_SECTOR_SIZE = 512
READ_ATTRIBUTES = 0xD0
READ_THRESHOLDS = 0xD1
ENABLE_DISABLE_AUTOSAVE = 0xD2
SAVE_ATTRIBUTE_VALUES = 0xD3
EXECUTE_OFFLINE_DIAGS = 0xD4
SMART_READ_LOG = 0xD5
SMART_WRITE_LOG = 0xD6
ENABLE_SMART = 0xD8
DISABLE_SMART = 0xD9
RETURN_SMART_STATUS = 0xDA
ENABLE_DISABLE_AUTO_OFFLINE = 0xDB
IOCTL_CHANGER_BASE = FILE_DEVICE_CHANGER
MAX_VOLUME_ID_SIZE = 36
MAX_VOLUME_TEMPLATE_SIZE = 40
VENDOR_ID_LENGTH = 8
PRODUCT_ID_LENGTH = 16
REVISION_LENGTH = 4
SERIAL_NUMBER_LENGTH = 32
CHANGER_BAR_CODE_SCANNER_INSTALLED = 0x00000001
CHANGER_INIT_ELEM_STAT_WITH_RANGE = 0x00000002
CHANGER_CLOSE_IEPORT = 0x00000004
CHANGER_OPEN_IEPORT = 0x00000008
CHANGER_STATUS_NON_VOLATILE = 0x00000010
CHANGER_EXCHANGE_MEDIA = 0x00000020
CHANGER_CLEANER_SLOT = 0x00000040
CHANGER_LOCK_UNLOCK = 0x00000080
CHANGER_CARTRIDGE_MAGAZINE = 0x00000100
CHANGER_MEDIUM_FLIP = 0x00000200
CHANGER_POSITION_TO_ELEMENT = 0x00000400
CHANGER_REPORT_IEPORT_STATE = 0x00000800
CHANGER_STORAGE_DRIVE = 0x00001000
CHANGER_STORAGE_IEPORT = 0x00002000
CHANGER_STORAGE_SLOT = 0x00004000
CHANGER_STORAGE_TRANSPORT = 0x00008000
CHANGER_DRIVE_CLEANING_REQUIRED = 0x00010000
CHANGER_PREDISMOUNT_EJECT_REQUIRED = 0x00020000
CHANGER_CLEANER_ACCESS_NOT_VALID = 0x00040000
CHANGER_PREMOUNT_EJECT_REQUIRED = 0x00080000
CHANGER_VOLUME_IDENTIFICATION = 0x00100000
CHANGER_VOLUME_SEARCH = 0x00200000
CHANGER_VOLUME_ASSERT = 0x00400000
CHANGER_VOLUME_REPLACE = 0x00800000
CHANGER_VOLUME_UNDEFINE = 0x01000000
CHANGER_SERIAL_NUMBER_VALID = 0x04000000
CHANGER_DEVICE_REINITIALIZE_CAPABLE = 0x08000000
CHANGER_KEYPAD_ENABLE_DISABLE = 0x10000000
CHANGER_DRIVE_EMPTY_ON_DOOR_ACCESS = 0x20000000

CHANGER_RESERVED_BIT = 0x80000000
CHANGER_PREDISMOUNT_ALIGN_TO_SLOT = 0x80000001
CHANGER_PREDISMOUNT_ALIGN_TO_DRIVE = 0x80000002
CHANGER_CLEANER_AUTODISMOUNT = 0x80000004
CHANGER_TRUE_EXCHANGE_CAPABLE = 0x80000008
CHANGER_SLOTS_USE_TRAYS = 0x80000010
CHANGER_RTN_MEDIA_TO_ORIGINAL_ADDR = 0x80000020
CHANGER_CLEANER_OPS_NOT_SUPPORTED = 0x80000040
CHANGER_IEPORT_USER_CONTROL_OPEN = 0x80000080
CHANGER_IEPORT_USER_CONTROL_CLOSE = 0x80000100
CHANGER_MOVE_EXTENDS_IEPORT = 0x80000200
CHANGER_MOVE_RETRACTS_IEPORT = 0x80000400


CHANGER_TO_TRANSPORT = 0x01
CHANGER_TO_SLOT = 0x02
CHANGER_TO_IEPORT = 0x04
CHANGER_TO_DRIVE = 0x08
LOCK_UNLOCK_IEPORT = 0x01
LOCK_UNLOCK_DOOR = 0x02
LOCK_UNLOCK_KEYPAD = 0x04
LOCK_ELEMENT = 0
UNLOCK_ELEMENT = 1
EXTEND_IEPORT = 2
RETRACT_IEPORT = 3
ELEMENT_STATUS_FULL = 0x00000001
ELEMENT_STATUS_IMPEXP = 0x00000002
ELEMENT_STATUS_EXCEPT = 0x00000004
ELEMENT_STATUS_ACCESS = 0x00000008
ELEMENT_STATUS_EXENAB = 0x00000010
ELEMENT_STATUS_INENAB = 0x00000020
ELEMENT_STATUS_PRODUCT_DATA = 0x00000040
ELEMENT_STATUS_LUN_VALID = 0x00001000
ELEMENT_STATUS_ID_VALID = 0x00002000
ELEMENT_STATUS_NOT_BUS = 0x00008000
ELEMENT_STATUS_INVERT = 0x00400000
ELEMENT_STATUS_SVALID = 0x00800000
ELEMENT_STATUS_PVOLTAG = 0x10000000
ELEMENT_STATUS_AVOLTAG = 0x20000000
ERROR_LABEL_UNREADABLE = 0x00000001
ERROR_LABEL_QUESTIONABLE = 0x00000002
ERROR_SLOT_NOT_PRESENT = 0x00000004
ERROR_DRIVE_NOT_INSTALLED = 0x00000008
ERROR_TRAY_MALFUNCTION = 0x00000010
ERROR_INIT_STATUS_NEEDED = 0x00000011
ERROR_UNHANDLED_ERROR = 0xFFFFFFFF
SEARCH_ALL = 0x0
SEARCH_PRIMARY = 0x1
SEARCH_ALTERNATE = 0x2
SEARCH_ALL_NO_SEQ = 0x4
SEARCH_PRI_NO_SEQ = 0x5
SEARCH_ALT_NO_SEQ = 0x6
ASSERT_PRIMARY = 0x8
ASSERT_ALTERNATE = 0x9
REPLACE_PRIMARY = 0xA
REPLACE_ALTERNATE = 0xB
UNDEFINE_PRIMARY = 0xC
UNDEFINE_ALTERNATE = 0xD
USN_PAGE_SIZE = 0x1000
USN_REASON_DATA_OVERWRITE = 0x00000001
USN_REASON_DATA_EXTEND = 0x00000002
USN_REASON_DATA_TRUNCATION = 0x00000004
USN_REASON_NAMED_DATA_OVERWRITE = 0x00000010
USN_REASON_NAMED_DATA_EXTEND = 0x00000020
USN_REASON_NAMED_DATA_TRUNCATION = 0x00000040
USN_REASON_FILE_CREATE = 0x00000100
USN_REASON_FILE_DELETE = 0x00000200
USN_REASON_EA_CHANGE = 0x00000400
USN_REASON_SECURITY_CHANGE = 0x00000800
USN_REASON_RENAME_OLD_NAME = 0x00001000
USN_REASON_RENAME_NEW_NAME = 0x00002000
USN_REASON_INDEXABLE_CHANGE = 0x00004000
USN_REASON_BASIC_INFO_CHANGE = 0x00008000
USN_REASON_HARD_LINK_CHANGE = 0x00010000
USN_REASON_COMPRESSION_CHANGE = 0x00020000
USN_REASON_ENCRYPTION_CHANGE = 0x00040000
USN_REASON_OBJECT_ID_CHANGE = 0x00080000
USN_REASON_REPARSE_POINT_CHANGE = 0x00100000
USN_REASON_STREAM_CHANGE = 0x00200000
USN_REASON_TRANSACTED_CHANGE = 0x00400000
USN_REASON_CLOSE = 0x80000000
USN_DELETE_FLAG_DELETE = 0x00000001
USN_DELETE_FLAG_NOTIFY = 0x00000002
USN_DELETE_VALID_FLAGS = 0x00000003
USN_SOURCE_DATA_MANAGEMENT = 0x00000001
USN_SOURCE_AUXILIARY_DATA = 0x00000002
USN_SOURCE_REPLICATION_MANAGEMENT = 0x00000004

MARK_HANDLE_PROTECT_CLUSTERS = 1
MARK_HANDLE_TXF_SYSTEM_LOG = 4
MARK_HANDLE_NOT_TXF_SYSTEM_LOG = 8

VOLUME_IS_DIRTY = 0x00000001
VOLUME_UPGRADE_SCHEDULED = 0x00000002
VOLUME_SESSION_OPEN = 4

FILE_PREFETCH_TYPE_FOR_CREATE = 1
FILE_PREFETCH_TYPE_FOR_DIRENUM = 2
FILE_PREFETCH_TYPE_FOR_CREATE_EX = 3
FILE_PREFETCH_TYPE_FOR_DIRENUM_EX = 4
FILE_PREFETCH_TYPE_MAX = 4

FILESYSTEM_STATISTICS_TYPE_NTFS = 1
FILESYSTEM_STATISTICS_TYPE_FAT = 2
FILE_SET_ENCRYPTION = 0x00000001
FILE_CLEAR_ENCRYPTION = 0x00000002
STREAM_SET_ENCRYPTION = 0x00000003
STREAM_CLEAR_ENCRYPTION = 0x00000004
MAXIMUM_ENCRYPTION_VALUE = 0x00000004
ENCRYPTION_FORMAT_DEFAULT = 0x01
COMPRESSION_FORMAT_SPARSE = 0x4000
COPYFILE_SIS_LINK = 0x0001
COPYFILE_SIS_REPLACE = 0x0002
COPYFILE_SIS_FLAGS = 0x0003

WMI_DISK_GEOMETRY_GUID = pywintypes.IID("{25007F51-57C2-11D1-A528-00A0C9062910}")
GUID_DEVINTERFACE_CDROM = pywintypes.IID("{53F56308-B6BF-11D0-94F2-00A0C91EFB8B}")
GUID_DEVINTERFACE_FLOPPY = pywintypes.IID("{53F56311-B6BF-11D0-94F2-00A0C91EFB8B}")
GUID_DEVINTERFACE_SERENUM_BUS_ENUMERATOR = pywintypes.IID(
    "{4D36E978-E325-11CE-BFC1-08002BE10318}"
)
GUID_DEVINTERFACE_COMPORT = pywintypes.IID("{86E0D1E0-8089-11D0-9CE4-08003E301F73}")
GUID_DEVINTERFACE_DISK = pywintypes.IID("{53F56307-B6BF-11D0-94F2-00A0C91EFB8B}")
GUID_DEVINTERFACE_STORAGEPORT = pywintypes.IID("{2ACCFE60-C130-11D2-B082-00A0C91EFB8B}")
GUID_DEVINTERFACE_CDCHANGER = pywintypes.IID("{53F56312-B6BF-11D0-94F2-00A0C91EFB8B}")
GUID_DEVINTERFACE_PARTITION = pywintypes.IID("{53F5630A-B6BF-11D0-94F2-00A0C91EFB8B}")
GUID_DEVINTERFACE_VOLUME = pywintypes.IID("{53F5630D-B6BF-11D0-94F2-00A0C91EFB8B}")
GUID_DEVINTERFACE_WRITEONCEDISK = pywintypes.IID(
    "{53F5630C-B6BF-11D0-94F2-00A0C91EFB8B}"
)
GUID_DEVINTERFACE_TAPE = pywintypes.IID("{53F5630B-B6BF-11D0-94F2-00A0C91EFB8B}")
GUID_DEVINTERFACE_MEDIUMCHANGER = pywintypes.IID(
    "{53F56310-B6BF-11D0-94F2-00A0C91EFB8B}"
)
GUID_SERENUM_BUS_ENUMERATOR = GUID_DEVINTERFACE_SERENUM_BUS_ENUMERATOR
GUID_CLASS_COMPORT = GUID_DEVINTERFACE_COMPORT

DiskClassGuid = GUID_DEVINTERFACE_DISK
CdRomClassGuid = GUID_DEVINTERFACE_CDROM
PartitionClassGuid = GUID_DEVINTERFACE_PARTITION
TapeClassGuid = GUID_DEVINTERFACE_TAPE
WriteOnceDiskClassGuid = GUID_DEVINTERFACE_WRITEONCEDISK
VolumeClassGuid = GUID_DEVINTERFACE_VOLUME
MediumChangerClassGuid = GUID_DEVINTERFACE_MEDIUMCHANGER
FloppyClassGuid = GUID_DEVINTERFACE_FLOPPY
CdChangerClassGuid = GUID_DEVINTERFACE_CDCHANGER
StoragePortClassGuid = GUID_DEVINTERFACE_STORAGEPORT


IOCTL_STORAGE_CHECK_VERIFY = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0200, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_STORAGE_CHECK_VERIFY2 = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0200, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_STORAGE_MEDIA_REMOVAL = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0201, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_STORAGE_EJECT_MEDIA = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0202, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_STORAGE_LOAD_MEDIA = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0203, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_STORAGE_LOAD_MEDIA2 = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0203, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_STORAGE_RESERVE = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0204, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_STORAGE_RELEASE = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0205, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_STORAGE_FIND_NEW_DEVICES = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0206, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_STORAGE_EJECTION_CONTROL = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0250, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_STORAGE_MCN_CONTROL = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0251, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_STORAGE_GET_MEDIA_TYPES = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0300, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_STORAGE_GET_MEDIA_TYPES_EX = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0301, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_STORAGE_GET_MEDIA_SERIAL_NUMBER = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0304, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_STORAGE_GET_HOTPLUG_INFO = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0305, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_STORAGE_SET_HOTPLUG_INFO = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0306, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_STORAGE_RESET_BUS = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0400, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_STORAGE_RESET_DEVICE = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0401, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_STORAGE_BREAK_RESERVATION = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0405, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_STORAGE_GET_DEVICE_NUMBER = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0420, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_STORAGE_PREDICT_FAILURE = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0440, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_GET_DRIVE_GEOMETRY = CTL_CODE(
    IOCTL_DISK_BASE, 0x0000, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_GET_PARTITION_INFO = CTL_CODE(
    IOCTL_DISK_BASE, 0x0001, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_SET_PARTITION_INFO = CTL_CODE(
    IOCTL_DISK_BASE, 0x0002, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_GET_DRIVE_LAYOUT = CTL_CODE(
    IOCTL_DISK_BASE, 0x0003, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_SET_DRIVE_LAYOUT = CTL_CODE(
    IOCTL_DISK_BASE, 0x0004, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_VERIFY = CTL_CODE(IOCTL_DISK_BASE, 0x0005, METHOD_BUFFERED, FILE_ANY_ACCESS)
IOCTL_DISK_FORMAT_TRACKS = CTL_CODE(
    IOCTL_DISK_BASE, 0x0006, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_REASSIGN_BLOCKS = CTL_CODE(
    IOCTL_DISK_BASE, 0x0007, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_PERFORMANCE = CTL_CODE(
    IOCTL_DISK_BASE, 0x0008, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_IS_WRITABLE = CTL_CODE(
    IOCTL_DISK_BASE, 0x0009, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_LOGGING = CTL_CODE(IOCTL_DISK_BASE, 0x000A, METHOD_BUFFERED, FILE_ANY_ACCESS)
IOCTL_DISK_FORMAT_TRACKS_EX = CTL_CODE(
    IOCTL_DISK_BASE, 0x000B, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_HISTOGRAM_STRUCTURE = CTL_CODE(
    IOCTL_DISK_BASE, 0x000C, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_HISTOGRAM_DATA = CTL_CODE(
    IOCTL_DISK_BASE, 0x000D, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_HISTOGRAM_RESET = CTL_CODE(
    IOCTL_DISK_BASE, 0x000E, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_REQUEST_STRUCTURE = CTL_CODE(
    IOCTL_DISK_BASE, 0x000F, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_REQUEST_DATA = CTL_CODE(
    IOCTL_DISK_BASE, 0x0010, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_PERFORMANCE_OFF = CTL_CODE(
    IOCTL_DISK_BASE, 0x0018, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_CONTROLLER_NUMBER = CTL_CODE(
    IOCTL_DISK_BASE, 0x0011, METHOD_BUFFERED, FILE_ANY_ACCESS
)
SMART_GET_VERSION = CTL_CODE(IOCTL_DISK_BASE, 0x0020, METHOD_BUFFERED, FILE_READ_ACCESS)
SMART_SEND_DRIVE_COMMAND = CTL_CODE(
    IOCTL_DISK_BASE, 0x0021, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
SMART_RCV_DRIVE_DATA = CTL_CODE(
    IOCTL_DISK_BASE, 0x0022, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_GET_PARTITION_INFO_EX = CTL_CODE(
    IOCTL_DISK_BASE, 0x0012, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_SET_PARTITION_INFO_EX = CTL_CODE(
    IOCTL_DISK_BASE, 0x0013, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_GET_DRIVE_LAYOUT_EX = CTL_CODE(
    IOCTL_DISK_BASE, 0x0014, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_SET_DRIVE_LAYOUT_EX = CTL_CODE(
    IOCTL_DISK_BASE, 0x0015, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_CREATE_DISK = CTL_CODE(
    IOCTL_DISK_BASE, 0x0016, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_GET_LENGTH_INFO = CTL_CODE(
    IOCTL_DISK_BASE, 0x0017, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_GET_DRIVE_GEOMETRY_EX = CTL_CODE(
    IOCTL_DISK_BASE, 0x0028, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_REASSIGN_BLOCKS_EX = CTL_CODE(
    IOCTL_DISK_BASE, 0x0029, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)

IOCTL_DISK_UPDATE_DRIVE_SIZE = CTL_CODE(
    IOCTL_DISK_BASE, 0x0032, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_GROW_PARTITION = CTL_CODE(
    IOCTL_DISK_BASE, 0x0034, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_GET_CACHE_INFORMATION = CTL_CODE(
    IOCTL_DISK_BASE, 0x0035, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_SET_CACHE_INFORMATION = CTL_CODE(
    IOCTL_DISK_BASE, 0x0036, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)

OBSOLETE_IOCTL_STORAGE_RESET_BUS = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0400, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
OBSOLETE_IOCTL_STORAGE_RESET_DEVICE = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0401, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
## the original define no longer exists in winioctl.h
OBSOLETE_DISK_GET_WRITE_CACHE_STATE = CTL_CODE(
    IOCTL_DISK_BASE, 0x0037, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_GET_WRITE_CACHE_STATE = OBSOLETE_DISK_GET_WRITE_CACHE_STATE


IOCTL_DISK_DELETE_DRIVE_LAYOUT = CTL_CODE(
    IOCTL_DISK_BASE, 0x0040, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_UPDATE_PROPERTIES = CTL_CODE(
    IOCTL_DISK_BASE, 0x0050, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_FORMAT_DRIVE = CTL_CODE(
    IOCTL_DISK_BASE, 0x00F3, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_SENSE_DEVICE = CTL_CODE(
    IOCTL_DISK_BASE, 0x00F8, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_CHECK_VERIFY = CTL_CODE(
    IOCTL_DISK_BASE, 0x0200, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_MEDIA_REMOVAL = CTL_CODE(
    IOCTL_DISK_BASE, 0x0201, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_EJECT_MEDIA = CTL_CODE(
    IOCTL_DISK_BASE, 0x0202, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_LOAD_MEDIA = CTL_CODE(
    IOCTL_DISK_BASE, 0x0203, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_RESERVE = CTL_CODE(
    IOCTL_DISK_BASE, 0x0204, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_RELEASE = CTL_CODE(
    IOCTL_DISK_BASE, 0x0205, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_FIND_NEW_DEVICES = CTL_CODE(
    IOCTL_DISK_BASE, 0x0206, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_GET_MEDIA_TYPES = CTL_CODE(
    IOCTL_DISK_BASE, 0x0300, METHOD_BUFFERED, FILE_ANY_ACCESS
)

DISK_HISTOGRAM_SIZE = 72
HISTOGRAM_BUCKET_SIZE = 8

IOCTL_CHANGER_GET_PARAMETERS = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x0000, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_CHANGER_GET_STATUS = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x0001, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_CHANGER_GET_PRODUCT_DATA = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x0002, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_CHANGER_SET_ACCESS = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x0004, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_CHANGER_GET_ELEMENT_STATUS = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x0005, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_CHANGER_INITIALIZE_ELEMENT_STATUS = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x0006, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_CHANGER_SET_POSITION = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x0007, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_CHANGER_EXCHANGE_MEDIUM = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x0008, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_CHANGER_MOVE_MEDIUM = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x0009, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_CHANGER_REINITIALIZE_TRANSPORT = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x000A, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_CHANGER_QUERY_VOLUME_TAGS = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x000B, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_SERIAL_LSRMST_INSERT = CTL_CODE(
    FILE_DEVICE_SERIAL_PORT, 31, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_SERENUM_EXPOSE_HARDWARE = CTL_CODE(
    FILE_DEVICE_SERENUM, 128, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_SERENUM_REMOVE_HARDWARE = CTL_CODE(
    FILE_DEVICE_SERENUM, 129, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_SERENUM_PORT_DESC = CTL_CODE(
    FILE_DEVICE_SERENUM, 130, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_SERENUM_GET_PORT_NAME = CTL_CODE(
    FILE_DEVICE_SERENUM, 131, METHOD_BUFFERED, FILE_ANY_ACCESS
)

## ??? can't find where FILE_DEVICE_AVIO is defined ???
## IOCTL_AVIO_ALLOCATE_STREAM = CTL_CODE(FILE_DEVICE_AVIO, 1, METHOD_BUFFERED, FILE_SPECIAL_ACCESS)
## IOCTL_AVIO_FREE_STREAM = CTL_CODE(FILE_DEVICE_AVIO, 2, METHOD_BUFFERED, FILE_SPECIAL_ACCESS)
## IOCTL_AVIO_MODIFY_STREAM = CTL_CODE(FILE_DEVICE_AVIO, 3, METHOD_BUFFERED, FILE_SPECIAL_ACCESS)

SERIAL_LSRMST_ESCAPE = 0x00
SERIAL_LSRMST_LSR_DATA = 0x01
SERIAL_LSRMST_LSR_NODATA = 0x02
SERIAL_LSRMST_MST = 0x03
SERIAL_IOC_FCR_FIFO_ENABLE = 0x00000001
SERIAL_IOC_FCR_RCVR_RESET = 0x00000002
SERIAL_IOC_FCR_XMIT_RESET = 0x00000004
SERIAL_IOC_FCR_DMA_MODE = 0x00000008
SERIAL_IOC_FCR_RES1 = 0x00000010
SERIAL_IOC_FCR_RES2 = 0x00000020
SERIAL_IOC_FCR_RCVR_TRIGGER_LSB = 0x00000040
SERIAL_IOC_FCR_RCVR_TRIGGER_MSB = 0x00000080
SERIAL_IOC_MCR_DTR = 0x00000001
SERIAL_IOC_MCR_RTS = 0x00000002
SERIAL_IOC_MCR_OUT1 = 0x00000004
SERIAL_IOC_MCR_OUT2 = 0x00000008
SERIAL_IOC_MCR_LOOP = 0x00000010
FSCTL_REQUEST_OPLOCK_LEVEL_1 = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 0, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_REQUEST_OPLOCK_LEVEL_2 = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 1, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_REQUEST_BATCH_OPLOCK = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 2, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_OPLOCK_BREAK_ACKNOWLEDGE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 3, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_OPBATCH_ACK_CLOSE_PENDING = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 4, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_OPLOCK_BREAK_NOTIFY = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 5, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_LOCK_VOLUME = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 6, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_UNLOCK_VOLUME = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 7, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_DISMOUNT_VOLUME = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 8, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_IS_VOLUME_MOUNTED = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 10, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_IS_PATHNAME_VALID = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 11, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_MARK_VOLUME_DIRTY = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 12, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_QUERY_RETRIEVAL_POINTERS = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 14, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_GET_COMPRESSION = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 15, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_SET_COMPRESSION = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 16, METHOD_BUFFERED, FILE_READ_DATA | FILE_WRITE_DATA
)
FSCTL_MARK_AS_SYSTEM_HIVE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 19, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_OPLOCK_BREAK_ACK_NO_2 = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 20, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_INVALIDATE_VOLUMES = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 21, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_QUERY_FAT_BPB = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 22, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_REQUEST_FILTER_OPLOCK = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 23, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_FILESYSTEM_GET_STATISTICS = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 24, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_GET_NTFS_VOLUME_DATA = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 25, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_GET_NTFS_FILE_RECORD = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 26, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_GET_VOLUME_BITMAP = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 27, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_GET_RETRIEVAL_POINTERS = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 28, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_MOVE_FILE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 29, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_IS_VOLUME_DIRTY = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 30, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_ALLOW_EXTENDED_DASD_IO = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 32, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_FIND_FILES_BY_SID = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 35, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_SET_OBJECT_ID = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 38, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_GET_OBJECT_ID = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 39, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_DELETE_OBJECT_ID = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 40, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_SET_REPARSE_POINT = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 41, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_GET_REPARSE_POINT = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 42, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_DELETE_REPARSE_POINT = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 43, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_ENUM_USN_DATA = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 44, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_SECURITY_ID_CHECK = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 45, METHOD_NEITHER, FILE_READ_DATA
)
FSCTL_READ_USN_JOURNAL = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 46, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_SET_OBJECT_ID_EXTENDED = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 47, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_CREATE_OR_GET_OBJECT_ID = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 48, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_SET_SPARSE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 49, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_SET_ZERO_DATA = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 50, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_QUERY_ALLOCATED_RANGES = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 51, METHOD_NEITHER, FILE_READ_DATA
)
FSCTL_SET_ENCRYPTION = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 53, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_ENCRYPTION_FSCTL_IO = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 54, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_WRITE_RAW_ENCRYPTED = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 55, METHOD_NEITHER, FILE_SPECIAL_ACCESS
)
FSCTL_READ_RAW_ENCRYPTED = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 56, METHOD_NEITHER, FILE_SPECIAL_ACCESS
)
FSCTL_CREATE_USN_JOURNAL = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 57, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_READ_FILE_USN_DATA = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 58, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_WRITE_USN_CLOSE_RECORD = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 59, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_EXTEND_VOLUME = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 60, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_QUERY_USN_JOURNAL = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 61, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_DELETE_USN_JOURNAL = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 62, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_MARK_HANDLE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 63, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_SIS_COPYFILE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 64, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_SIS_LINK_FILES = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 65, METHOD_BUFFERED, FILE_READ_DATA | FILE_WRITE_DATA
)
FSCTL_HSM_MSG = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 66, METHOD_BUFFERED, FILE_READ_DATA | FILE_WRITE_DATA
)
FSCTL_HSM_DATA = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 68, METHOD_NEITHER, FILE_READ_DATA | FILE_WRITE_DATA
)
FSCTL_RECALL_FILE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 69, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_READ_FROM_PLEX = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 71, METHOD_OUT_DIRECT, FILE_READ_DATA
)
FSCTL_FILE_PREFETCH = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 72, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_MAKE_MEDIA_COMPATIBLE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 76, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_SET_DEFECT_MANAGEMENT = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 77, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_QUERY_SPARING_INFO = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 78, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_QUERY_ON_DISK_VOLUME_INFO = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 79, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_SET_VOLUME_COMPRESSION_STATE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 80, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_TXFS_MODIFY_RM = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 81, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_TXFS_QUERY_RM_INFORMATION = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 82, METHOD_BUFFERED, FILE_READ_DATA
)
FSCTL_TXFS_ROLLFORWARD_REDO = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 84, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_TXFS_ROLLFORWARD_UNDO = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 85, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_TXFS_START_RM = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 86, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_TXFS_SHUTDOWN_RM = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 87, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_TXFS_READ_BACKUP_INFORMATION = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 88, METHOD_BUFFERED, FILE_READ_DATA
)
FSCTL_TXFS_WRITE_BACKUP_INFORMATION = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 89, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_TXFS_CREATE_SECONDARY_RM = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 90, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_TXFS_GET_METADATA_INFO = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 91, METHOD_BUFFERED, FILE_READ_DATA
)
FSCTL_TXFS_GET_TRANSACTED_VERSION = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 92, METHOD_BUFFERED, FILE_READ_DATA
)
FSCTL_TXFS_CREATE_MINIVERSION = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 95, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_TXFS_TRANSACTION_ACTIVE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 99, METHOD_BUFFERED, FILE_READ_DATA
)
FSCTL_SET_ZERO_ON_DEALLOCATION = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 101, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_SET_REPAIR = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 102, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_GET_REPAIR = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 103, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_WAIT_FOR_REPAIR = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 104, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_INITIATE_REPAIR = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 106, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_CSC_INTERNAL = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 107, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_SHRINK_VOLUME = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 108, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_SET_SHORT_NAME_BEHAVIOR = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 109, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_DFSR_SET_GHOST_HANDLE_STATE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 110, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_TXFS_LIST_TRANSACTION_LOCKED_FILES = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 120, METHOD_BUFFERED, FILE_READ_DATA
)
FSCTL_TXFS_LIST_TRANSACTIONS = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 121, METHOD_BUFFERED, FILE_READ_DATA
)
FSCTL_QUERY_PAGEFILE_ENCRYPTION = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 122, METHOD_BUFFERED, FILE_ANY_ACCESS
)

IOCTL_VOLUME_BASE = ord("V")
IOCTL_VOLUME_GET_VOLUME_DISK_EXTENTS = CTL_CODE(
    IOCTL_VOLUME_BASE, 0, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_VOLUME_ONLINE = CTL_CODE(
    IOCTL_VOLUME_BASE, 2, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_VOLUME_OFFLINE = CTL_CODE(
    IOCTL_VOLUME_BASE, 3, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_VOLUME_IS_CLUSTERED = CTL_CODE(
    IOCTL_VOLUME_BASE, 12, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_VOLUME_GET_GPT_ATTRIBUTES = CTL_CODE(
    IOCTL_VOLUME_BASE, 14, METHOD_BUFFERED, FILE_ANY_ACCESS
)

## enums
## STORAGE_MEDIA_TYPE
DDS_4mm = 32
MiniQic = 33
Travan = 34
QIC = 35
MP_8mm = 36
AME_8mm = 37
AIT1_8mm = 38
DLT = 39
NCTP = 40
IBM_3480 = 41
IBM_3490E = 42
IBM_Magstar_3590 = 43
IBM_Magstar_MP = 44
STK_DATA_D3 = 45
SONY_DTF = 46
DV_6mm = 47
DMI = 48
SONY_D2 = 49
CLEANER_CARTRIDGE = 50
CD_ROM = 51
CD_R = 52
CD_RW = 53
DVD_ROM = 54
DVD_R = 55
DVD_RW = 56
MO_3_RW = 57
MO_5_WO = 58
MO_5_RW = 59
MO_5_LIMDOW = 60
PC_5_WO = 61
PC_5_RW = 62
PD_5_RW = 63
ABL_5_WO = 64
PINNACLE_APEX_5_RW = 65
SONY_12_WO = 66
PHILIPS_12_WO = 67
HITACHI_12_WO = 68
CYGNET_12_WO = 69
KODAK_14_WO = 70
MO_NFR_525 = 71
NIKON_12_RW = 72
IOMEGA_ZIP = 73
IOMEGA_JAZ = 74
SYQUEST_EZ135 = 75
SYQUEST_EZFLYER = 76
SYQUEST_SYJET = 77
AVATAR_F2 = 78
MP2_8mm = 79
DST_S = 80
DST_M = 81
DST_L = 82
VXATape_1 = 83
VXATape_2 = 84
STK_9840 = 85
LTO_Ultrium = 86
LTO_Accelis = 87
DVD_RAM = 88
AIT_8mm = 89
ADR_1 = 90
ADR_2 = 91
STK_9940 = 92

## STORAGE_BUS_TYPE
BusTypeUnknown = 0
BusTypeScsi = 1
BusTypeAtapi = 2
BusTypeAta = 3
BusType1394 = 4
BusTypeSsa = 5
BusTypeFibre = 6
BusTypeUsb = 7
BusTypeRAID = 8
BusTypeiScsi = 9
BusTypeSas = 10
BusTypeSata = 11
BusTypeMaxReserved = 127

## MEDIA_TYPE
Unknown = 0
F5_1Pt2_512 = 1
F3_1Pt44_512 = 2
F3_2Pt88_512 = 3
F3_20Pt8_512 = 4
F3_720_512 = 5
F5_360_512 = 6
F5_320_512 = 7
F5_320_1024 = 8
F5_180_512 = 9
F5_160_512 = 10
RemovableMedia = 11
FixedMedia = 12
F3_120M_512 = 13
F3_640_512 = 14
F5_640_512 = 15
F5_720_512 = 16
F3_1Pt2_512 = 17
F3_1Pt23_1024 = 18
F5_1Pt23_1024 = 19
F3_128Mb_512 = 20
F3_230Mb_512 = 21
F8_256_128 = 22
F3_200Mb_512 = 23
F3_240M_512 = 24
F3_32M_512 = 25

## PARTITION_STYLE
PARTITION_STYLE_MBR = 0
PARTITION_STYLE_GPT = 1
PARTITION_STYLE_RAW = 2

## DETECTION_TYPE
DetectNone = 0
DetectInt13 = 1
DetectExInt13 = 2

## DISK_CACHE_RETENTION_PRIORITY
EqualPriority = 0
KeepPrefetchedData = 1
KeepReadData = 2

## DISK_WRITE_CACHE_STATE - ?????? this enum has disappeared from winioctl.h in windows 2003 SP1 sdk ??????
DiskWriteCacheNormal = 0
DiskWriteCacheForceDisable = 1
DiskWriteCacheDisableNotSupported = 2

## BIN_TYPES
RequestSize = 0
RequestLocation = 1

## CHANGER_DEVICE_PROBLEM_TYPE
DeviceProblemNone = 0
DeviceProblemHardware = 1
DeviceProblemCHMError = 2
DeviceProblemDoorOpen = 3
DeviceProblemCalibrationError = 4
DeviceProblemTargetFailure = 5
DeviceProblemCHMMoveError = 6
DeviceProblemCHMZeroError = 7
DeviceProblemCartridgeInsertError = 8
DeviceProblemPositionError = 9
DeviceProblemSensorError = 10
DeviceProblemCartridgeEjectError = 11
DeviceProblemGripperError = 12
DeviceProblemDriveError = 13

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\win32\lib\winioctlcon.py ===
## flags, enums, guids used with DeviceIoControl from WinIoCtl.h

import pywintypes
from ntsecuritycon import FILE_READ_DATA, FILE_WRITE_DATA


def CTL_CODE(DeviceType, Function, Method, Access):
    return (DeviceType << 16) | (Access << 14) | (Function << 2) | Method


def DEVICE_TYPE_FROM_CTL_CODE(ctrlCode):
    return (ctrlCode & 0xFFFF0000) >> 16


FILE_DEVICE_BEEP = 0x00000001
FILE_DEVICE_CD_ROM = 0x00000002
FILE_DEVICE_CD_ROM_FILE_SYSTEM = 0x00000003
FILE_DEVICE_CONTROLLER = 0x00000004
FILE_DEVICE_DATALINK = 0x00000005
FILE_DEVICE_DFS = 0x00000006
FILE_DEVICE_DISK = 0x00000007
FILE_DEVICE_DISK_FILE_SYSTEM = 0x00000008
FILE_DEVICE_FILE_SYSTEM = 0x00000009
FILE_DEVICE_INPORT_PORT = 0x0000000A
FILE_DEVICE_KEYBOARD = 0x0000000B
FILE_DEVICE_MAILSLOT = 0x0000000C
FILE_DEVICE_MIDI_IN = 0x0000000D
FILE_DEVICE_MIDI_OUT = 0x0000000E
FILE_DEVICE_MOUSE = 0x0000000F
FILE_DEVICE_MULTI_UNC_PROVIDER = 0x00000010
FILE_DEVICE_NAMED_PIPE = 0x00000011
FILE_DEVICE_NETWORK = 0x00000012
FILE_DEVICE_NETWORK_BROWSER = 0x00000013
FILE_DEVICE_NETWORK_FILE_SYSTEM = 0x00000014
FILE_DEVICE_NULL = 0x00000015
FILE_DEVICE_PARALLEL_PORT = 0x00000016
FILE_DEVICE_PHYSICAL_NETCARD = 0x00000017
FILE_DEVICE_PRINTER = 0x00000018
FILE_DEVICE_SCANNER = 0x00000019
FILE_DEVICE_SERIAL_MOUSE_PORT = 0x0000001A
FILE_DEVICE_SERIAL_PORT = 0x0000001B
FILE_DEVICE_SCREEN = 0x0000001C
FILE_DEVICE_SOUND = 0x0000001D
FILE_DEVICE_STREAMS = 0x0000001E
FILE_DEVICE_TAPE = 0x0000001F
FILE_DEVICE_TAPE_FILE_SYSTEM = 0x00000020
FILE_DEVICE_TRANSPORT = 0x00000021
FILE_DEVICE_UNKNOWN = 0x00000022
FILE_DEVICE_VIDEO = 0x00000023
FILE_DEVICE_VIRTUAL_DISK = 0x00000024
FILE_DEVICE_WAVE_IN = 0x00000025
FILE_DEVICE_WAVE_OUT = 0x00000026
FILE_DEVICE_8042_PORT = 0x00000027
FILE_DEVICE_NETWORK_REDIRECTOR = 0x00000028
FILE_DEVICE_BATTERY = 0x00000029
FILE_DEVICE_BUS_EXTENDER = 0x0000002A
FILE_DEVICE_MODEM = 0x0000002B
FILE_DEVICE_VDM = 0x0000002C
FILE_DEVICE_MASS_STORAGE = 0x0000002D
FILE_DEVICE_SMB = 0x0000002E
FILE_DEVICE_KS = 0x0000002F
FILE_DEVICE_CHANGER = 0x00000030
FILE_DEVICE_SMARTCARD = 0x00000031
FILE_DEVICE_ACPI = 0x00000032
FILE_DEVICE_DVD = 0x00000033
FILE_DEVICE_FULLSCREEN_VIDEO = 0x00000034
FILE_DEVICE_DFS_FILE_SYSTEM = 0x00000035
FILE_DEVICE_DFS_VOLUME = 0x00000036
FILE_DEVICE_SERENUM = 0x00000037
FILE_DEVICE_TERMSRV = 0x00000038
FILE_DEVICE_KSEC = 0x00000039
FILE_DEVICE_FIPS = 0x0000003A
FILE_DEVICE_INFINIBAND = 0x0000003B

METHOD_BUFFERED = 0
METHOD_IN_DIRECT = 1
METHOD_OUT_DIRECT = 2
METHOD_NEITHER = 3
METHOD_DIRECT_TO_HARDWARE = METHOD_IN_DIRECT
METHOD_DIRECT_FROM_HARDWARE = METHOD_OUT_DIRECT
FILE_ANY_ACCESS = 0
FILE_SPECIAL_ACCESS = FILE_ANY_ACCESS
FILE_READ_ACCESS = 0x0001
FILE_WRITE_ACCESS = 0x0002
IOCTL_STORAGE_BASE = FILE_DEVICE_MASS_STORAGE
RECOVERED_WRITES_VALID = 0x00000001
UNRECOVERED_WRITES_VALID = 0x00000002
RECOVERED_READS_VALID = 0x00000004
UNRECOVERED_READS_VALID = 0x00000008
WRITE_COMPRESSION_INFO_VALID = 0x00000010
READ_COMPRESSION_INFO_VALID = 0x00000020
TAPE_RETURN_STATISTICS = 0
TAPE_RETURN_ENV_INFO = 1
TAPE_RESET_STATISTICS = 2
MEDIA_ERASEABLE = 0x00000001
MEDIA_WRITE_ONCE = 0x00000002
MEDIA_READ_ONLY = 0x00000004
MEDIA_READ_WRITE = 0x00000008
MEDIA_WRITE_PROTECTED = 0x00000100
MEDIA_CURRENTLY_MOUNTED = 0x80000000
IOCTL_DISK_BASE = FILE_DEVICE_DISK
PARTITION_ENTRY_UNUSED = 0x00
PARTITION_FAT_12 = 0x01
PARTITION_XENIX_1 = 0x02
PARTITION_XENIX_2 = 0x03
PARTITION_FAT_16 = 0x04
PARTITION_EXTENDED = 0x05
PARTITION_HUGE = 0x06
PARTITION_IFS = 0x07
PARTITION_OS2BOOTMGR = 0x0A
PARTITION_FAT32 = 0x0B
PARTITION_FAT32_XINT13 = 0x0C
PARTITION_XINT13 = 0x0E
PARTITION_XINT13_EXTENDED = 0x0F
PARTITION_PREP = 0x41
PARTITION_LDM = 0x42
PARTITION_UNIX = 0x63
VALID_NTFT = 0xC0
PARTITION_NTFT = 0x80

GPT_ATTRIBUTE_PLATFORM_REQUIRED = 0x0000000000000001
GPT_BASIC_DATA_ATTRIBUTE_NO_DRIVE_LETTER = 0x8000000000000000
GPT_BASIC_DATA_ATTRIBUTE_HIDDEN = 0x4000000000000000
GPT_BASIC_DATA_ATTRIBUTE_SHADOW_COPY = 0x2000000000000000
GPT_BASIC_DATA_ATTRIBUTE_READ_ONLY = 0x1000000000000000

HIST_NO_OF_BUCKETS = 24
DISK_LOGGING_START = 0
DISK_LOGGING_STOP = 1
DISK_LOGGING_DUMP = 2
DISK_BINNING = 3
CAP_ATA_ID_CMD = 1
CAP_ATAPI_ID_CMD = 2
CAP_SMART_CMD = 4
ATAPI_ID_CMD = 0xA1
ID_CMD = 0xEC
SMART_CMD = 0xB0
SMART_CYL_LOW = 0x4F
SMART_CYL_HI = 0xC2
SMART_NO_ERROR = 0
SMART_IDE_ERROR = 1
SMART_INVALID_FLAG = 2
SMART_INVALID_COMMAND = 3
SMART_INVALID_BUFFER = 4
SMART_INVALID_DRIVE = 5
SMART_INVALID_IOCTL = 6
SMART_ERROR_NO_MEM = 7
SMART_INVALID_REGISTER = 8
SMART_NOT_SUPPORTED = 9
SMART_NO_IDE_DEVICE = 10
SMART_OFFLINE_ROUTINE_OFFLINE = 0
SMART_SHORT_SELFTEST_OFFLINE = 1
SMART_EXTENDED_SELFTEST_OFFLINE = 2
SMART_ABORT_OFFLINE_SELFTEST = 127
SMART_SHORT_SELFTEST_CAPTIVE = 129
SMART_EXTENDED_SELFTEST_CAPTIVE = 130
READ_ATTRIBUTE_BUFFER_SIZE = 512
IDENTIFY_BUFFER_SIZE = 512
READ_THRESHOLD_BUFFER_SIZE = 512
SMART_LOG_SECTOR_SIZE = 512
READ_ATTRIBUTES = 0xD0
READ_THRESHOLDS = 0xD1
ENABLE_DISABLE_AUTOSAVE = 0xD2
SAVE_ATTRIBUTE_VALUES = 0xD3
EXECUTE_OFFLINE_DIAGS = 0xD4
SMART_READ_LOG = 0xD5
SMART_WRITE_LOG = 0xD6
ENABLE_SMART = 0xD8
DISABLE_SMART = 0xD9
RETURN_SMART_STATUS = 0xDA
ENABLE_DISABLE_AUTO_OFFLINE = 0xDB
IOCTL_CHANGER_BASE = FILE_DEVICE_CHANGER
MAX_VOLUME_ID_SIZE = 36
MAX_VOLUME_TEMPLATE_SIZE = 40
VENDOR_ID_LENGTH = 8
PRODUCT_ID_LENGTH = 16
REVISION_LENGTH = 4
SERIAL_NUMBER_LENGTH = 32
CHANGER_BAR_CODE_SCANNER_INSTALLED = 0x00000001
CHANGER_INIT_ELEM_STAT_WITH_RANGE = 0x00000002
CHANGER_CLOSE_IEPORT = 0x00000004
CHANGER_OPEN_IEPORT = 0x00000008
CHANGER_STATUS_NON_VOLATILE = 0x00000010
CHANGER_EXCHANGE_MEDIA = 0x00000020
CHANGER_CLEANER_SLOT = 0x00000040
CHANGER_LOCK_UNLOCK = 0x00000080
CHANGER_CARTRIDGE_MAGAZINE = 0x00000100
CHANGER_MEDIUM_FLIP = 0x00000200
CHANGER_POSITION_TO_ELEMENT = 0x00000400
CHANGER_REPORT_IEPORT_STATE = 0x00000800
CHANGER_STORAGE_DRIVE = 0x00001000
CHANGER_STORAGE_IEPORT = 0x00002000
CHANGER_STORAGE_SLOT = 0x00004000
CHANGER_STORAGE_TRANSPORT = 0x00008000
CHANGER_DRIVE_CLEANING_REQUIRED = 0x00010000
CHANGER_PREDISMOUNT_EJECT_REQUIRED = 0x00020000
CHANGER_CLEANER_ACCESS_NOT_VALID = 0x00040000
CHANGER_PREMOUNT_EJECT_REQUIRED = 0x00080000
CHANGER_VOLUME_IDENTIFICATION = 0x00100000
CHANGER_VOLUME_SEARCH = 0x00200000
CHANGER_VOLUME_ASSERT = 0x00400000
CHANGER_VOLUME_REPLACE = 0x00800000
CHANGER_VOLUME_UNDEFINE = 0x01000000
CHANGER_SERIAL_NUMBER_VALID = 0x04000000
CHANGER_DEVICE_REINITIALIZE_CAPABLE = 0x08000000
CHANGER_KEYPAD_ENABLE_DISABLE = 0x10000000
CHANGER_DRIVE_EMPTY_ON_DOOR_ACCESS = 0x20000000

CHANGER_RESERVED_BIT = 0x80000000
CHANGER_PREDISMOUNT_ALIGN_TO_SLOT = 0x80000001
CHANGER_PREDISMOUNT_ALIGN_TO_DRIVE = 0x80000002
CHANGER_CLEANER_AUTODISMOUNT = 0x80000004
CHANGER_TRUE_EXCHANGE_CAPABLE = 0x80000008
CHANGER_SLOTS_USE_TRAYS = 0x80000010
CHANGER_RTN_MEDIA_TO_ORIGINAL_ADDR = 0x80000020
CHANGER_CLEANER_OPS_NOT_SUPPORTED = 0x80000040
CHANGER_IEPORT_USER_CONTROL_OPEN = 0x80000080
CHANGER_IEPORT_USER_CONTROL_CLOSE = 0x80000100
CHANGER_MOVE_EXTENDS_IEPORT = 0x80000200
CHANGER_MOVE_RETRACTS_IEPORT = 0x80000400


CHANGER_TO_TRANSPORT = 0x01
CHANGER_TO_SLOT = 0x02
CHANGER_TO_IEPORT = 0x04
CHANGER_TO_DRIVE = 0x08
LOCK_UNLOCK_IEPORT = 0x01
LOCK_UNLOCK_DOOR = 0x02
LOCK_UNLOCK_KEYPAD = 0x04
LOCK_ELEMENT = 0
UNLOCK_ELEMENT = 1
EXTEND_IEPORT = 2
RETRACT_IEPORT = 3
ELEMENT_STATUS_FULL = 0x00000001
ELEMENT_STATUS_IMPEXP = 0x00000002
ELEMENT_STATUS_EXCEPT = 0x00000004
ELEMENT_STATUS_ACCESS = 0x00000008
ELEMENT_STATUS_EXENAB = 0x00000010
ELEMENT_STATUS_INENAB = 0x00000020
ELEMENT_STATUS_PRODUCT_DATA = 0x00000040
ELEMENT_STATUS_LUN_VALID = 0x00001000
ELEMENT_STATUS_ID_VALID = 0x00002000
ELEMENT_STATUS_NOT_BUS = 0x00008000
ELEMENT_STATUS_INVERT = 0x00400000
ELEMENT_STATUS_SVALID = 0x00800000
ELEMENT_STATUS_PVOLTAG = 0x10000000
ELEMENT_STATUS_AVOLTAG = 0x20000000
ERROR_LABEL_UNREADABLE = 0x00000001
ERROR_LABEL_QUESTIONABLE = 0x00000002
ERROR_SLOT_NOT_PRESENT = 0x00000004
ERROR_DRIVE_NOT_INSTALLED = 0x00000008
ERROR_TRAY_MALFUNCTION = 0x00000010
ERROR_INIT_STATUS_NEEDED = 0x00000011
ERROR_UNHANDLED_ERROR = 0xFFFFFFFF
SEARCH_ALL = 0x0
SEARCH_PRIMARY = 0x1
SEARCH_ALTERNATE = 0x2
SEARCH_ALL_NO_SEQ = 0x4
SEARCH_PRI_NO_SEQ = 0x5
SEARCH_ALT_NO_SEQ = 0x6
ASSERT_PRIMARY = 0x8
ASSERT_ALTERNATE = 0x9
REPLACE_PRIMARY = 0xA
REPLACE_ALTERNATE = 0xB
UNDEFINE_PRIMARY = 0xC
UNDEFINE_ALTERNATE = 0xD
USN_PAGE_SIZE = 0x1000
USN_REASON_DATA_OVERWRITE = 0x00000001
USN_REASON_DATA_EXTEND = 0x00000002
USN_REASON_DATA_TRUNCATION = 0x00000004
USN_REASON_NAMED_DATA_OVERWRITE = 0x00000010
USN_REASON_NAMED_DATA_EXTEND = 0x00000020
USN_REASON_NAMED_DATA_TRUNCATION = 0x00000040
USN_REASON_FILE_CREATE = 0x00000100
USN_REASON_FILE_DELETE = 0x00000200
USN_REASON_EA_CHANGE = 0x00000400
USN_REASON_SECURITY_CHANGE = 0x00000800
USN_REASON_RENAME_OLD_NAME = 0x00001000
USN_REASON_RENAME_NEW_NAME = 0x00002000
USN_REASON_INDEXABLE_CHANGE = 0x00004000
USN_REASON_BASIC_INFO_CHANGE = 0x00008000
USN_REASON_HARD_LINK_CHANGE = 0x00010000
USN_REASON_COMPRESSION_CHANGE = 0x00020000
USN_REASON_ENCRYPTION_CHANGE = 0x00040000
USN_REASON_OBJECT_ID_CHANGE = 0x00080000
USN_REASON_REPARSE_POINT_CHANGE = 0x00100000
USN_REASON_STREAM_CHANGE = 0x00200000
USN_REASON_TRANSACTED_CHANGE = 0x00400000
USN_REASON_CLOSE = 0x80000000
USN_DELETE_FLAG_DELETE = 0x00000001
USN_DELETE_FLAG_NOTIFY = 0x00000002
USN_DELETE_VALID_FLAGS = 0x00000003
USN_SOURCE_DATA_MANAGEMENT = 0x00000001
USN_SOURCE_AUXILIARY_DATA = 0x00000002
USN_SOURCE_REPLICATION_MANAGEMENT = 0x00000004

MARK_HANDLE_PROTECT_CLUSTERS = 1
MARK_HANDLE_TXF_SYSTEM_LOG = 4
MARK_HANDLE_NOT_TXF_SYSTEM_LOG = 8

VOLUME_IS_DIRTY = 0x00000001
VOLUME_UPGRADE_SCHEDULED = 0x00000002
VOLUME_SESSION_OPEN = 4

FILE_PREFETCH_TYPE_FOR_CREATE = 1
FILE_PREFETCH_TYPE_FOR_DIRENUM = 2
FILE_PREFETCH_TYPE_FOR_CREATE_EX = 3
FILE_PREFETCH_TYPE_FOR_DIRENUM_EX = 4
FILE_PREFETCH_TYPE_MAX = 4

FILESYSTEM_STATISTICS_TYPE_NTFS = 1
FILESYSTEM_STATISTICS_TYPE_FAT = 2
FILE_SET_ENCRYPTION = 0x00000001
FILE_CLEAR_ENCRYPTION = 0x00000002
STREAM_SET_ENCRYPTION = 0x00000003
STREAM_CLEAR_ENCRYPTION = 0x00000004
MAXIMUM_ENCRYPTION_VALUE = 0x00000004
ENCRYPTION_FORMAT_DEFAULT = 0x01
COMPRESSION_FORMAT_SPARSE = 0x4000
COPYFILE_SIS_LINK = 0x0001
COPYFILE_SIS_REPLACE = 0x0002
COPYFILE_SIS_FLAGS = 0x0003

WMI_DISK_GEOMETRY_GUID = pywintypes.IID("{25007F51-57C2-11D1-A528-00A0C9062910}")
GUID_DEVINTERFACE_CDROM = pywintypes.IID("{53F56308-B6BF-11D0-94F2-00A0C91EFB8B}")
GUID_DEVINTERFACE_FLOPPY = pywintypes.IID("{53F56311-B6BF-11D0-94F2-00A0C91EFB8B}")
GUID_DEVINTERFACE_SERENUM_BUS_ENUMERATOR = pywintypes.IID(
    "{4D36E978-E325-11CE-BFC1-08002BE10318}"
)
GUID_DEVINTERFACE_COMPORT = pywintypes.IID("{86E0D1E0-8089-11D0-9CE4-08003E301F73}")
GUID_DEVINTERFACE_DISK = pywintypes.IID("{53F56307-B6BF-11D0-94F2-00A0C91EFB8B}")
GUID_DEVINTERFACE_STORAGEPORT = pywintypes.IID("{2ACCFE60-C130-11D2-B082-00A0C91EFB8B}")
GUID_DEVINTERFACE_CDCHANGER = pywintypes.IID("{53F56312-B6BF-11D0-94F2-00A0C91EFB8B}")
GUID_DEVINTERFACE_PARTITION = pywintypes.IID("{53F5630A-B6BF-11D0-94F2-00A0C91EFB8B}")
GUID_DEVINTERFACE_VOLUME = pywintypes.IID("{53F5630D-B6BF-11D0-94F2-00A0C91EFB8B}")
GUID_DEVINTERFACE_WRITEONCEDISK = pywintypes.IID(
    "{53F5630C-B6BF-11D0-94F2-00A0C91EFB8B}"
)
GUID_DEVINTERFACE_TAPE = pywintypes.IID("{53F5630B-B6BF-11D0-94F2-00A0C91EFB8B}")
GUID_DEVINTERFACE_MEDIUMCHANGER = pywintypes.IID(
    "{53F56310-B6BF-11D0-94F2-00A0C91EFB8B}"
)
GUID_SERENUM_BUS_ENUMERATOR = GUID_DEVINTERFACE_SERENUM_BUS_ENUMERATOR
GUID_CLASS_COMPORT = GUID_DEVINTERFACE_COMPORT

DiskClassGuid = GUID_DEVINTERFACE_DISK
CdRomClassGuid = GUID_DEVINTERFACE_CDROM
PartitionClassGuid = GUID_DEVINTERFACE_PARTITION
TapeClassGuid = GUID_DEVINTERFACE_TAPE
WriteOnceDiskClassGuid = GUID_DEVINTERFACE_WRITEONCEDISK
VolumeClassGuid = GUID_DEVINTERFACE_VOLUME
MediumChangerClassGuid = GUID_DEVINTERFACE_MEDIUMCHANGER
FloppyClassGuid = GUID_DEVINTERFACE_FLOPPY
CdChangerClassGuid = GUID_DEVINTERFACE_CDCHANGER
StoragePortClassGuid = GUID_DEVINTERFACE_STORAGEPORT


IOCTL_STORAGE_CHECK_VERIFY = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0200, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_STORAGE_CHECK_VERIFY2 = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0200, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_STORAGE_MEDIA_REMOVAL = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0201, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_STORAGE_EJECT_MEDIA = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0202, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_STORAGE_LOAD_MEDIA = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0203, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_STORAGE_LOAD_MEDIA2 = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0203, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_STORAGE_RESERVE = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0204, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_STORAGE_RELEASE = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0205, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_STORAGE_FIND_NEW_DEVICES = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0206, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_STORAGE_EJECTION_CONTROL = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0250, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_STORAGE_MCN_CONTROL = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0251, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_STORAGE_GET_MEDIA_TYPES = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0300, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_STORAGE_GET_MEDIA_TYPES_EX = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0301, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_STORAGE_GET_MEDIA_SERIAL_NUMBER = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0304, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_STORAGE_GET_HOTPLUG_INFO = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0305, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_STORAGE_SET_HOTPLUG_INFO = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0306, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_STORAGE_RESET_BUS = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0400, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_STORAGE_RESET_DEVICE = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0401, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_STORAGE_BREAK_RESERVATION = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0405, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_STORAGE_GET_DEVICE_NUMBER = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0420, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_STORAGE_PREDICT_FAILURE = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0440, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_GET_DRIVE_GEOMETRY = CTL_CODE(
    IOCTL_DISK_BASE, 0x0000, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_GET_PARTITION_INFO = CTL_CODE(
    IOCTL_DISK_BASE, 0x0001, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_SET_PARTITION_INFO = CTL_CODE(
    IOCTL_DISK_BASE, 0x0002, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_GET_DRIVE_LAYOUT = CTL_CODE(
    IOCTL_DISK_BASE, 0x0003, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_SET_DRIVE_LAYOUT = CTL_CODE(
    IOCTL_DISK_BASE, 0x0004, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_VERIFY = CTL_CODE(IOCTL_DISK_BASE, 0x0005, METHOD_BUFFERED, FILE_ANY_ACCESS)
IOCTL_DISK_FORMAT_TRACKS = CTL_CODE(
    IOCTL_DISK_BASE, 0x0006, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_REASSIGN_BLOCKS = CTL_CODE(
    IOCTL_DISK_BASE, 0x0007, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_PERFORMANCE = CTL_CODE(
    IOCTL_DISK_BASE, 0x0008, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_IS_WRITABLE = CTL_CODE(
    IOCTL_DISK_BASE, 0x0009, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_LOGGING = CTL_CODE(IOCTL_DISK_BASE, 0x000A, METHOD_BUFFERED, FILE_ANY_ACCESS)
IOCTL_DISK_FORMAT_TRACKS_EX = CTL_CODE(
    IOCTL_DISK_BASE, 0x000B, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_HISTOGRAM_STRUCTURE = CTL_CODE(
    IOCTL_DISK_BASE, 0x000C, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_HISTOGRAM_DATA = CTL_CODE(
    IOCTL_DISK_BASE, 0x000D, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_HISTOGRAM_RESET = CTL_CODE(
    IOCTL_DISK_BASE, 0x000E, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_REQUEST_STRUCTURE = CTL_CODE(
    IOCTL_DISK_BASE, 0x000F, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_REQUEST_DATA = CTL_CODE(
    IOCTL_DISK_BASE, 0x0010, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_PERFORMANCE_OFF = CTL_CODE(
    IOCTL_DISK_BASE, 0x0018, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_CONTROLLER_NUMBER = CTL_CODE(
    IOCTL_DISK_BASE, 0x0011, METHOD_BUFFERED, FILE_ANY_ACCESS
)
SMART_GET_VERSION = CTL_CODE(IOCTL_DISK_BASE, 0x0020, METHOD_BUFFERED, FILE_READ_ACCESS)
SMART_SEND_DRIVE_COMMAND = CTL_CODE(
    IOCTL_DISK_BASE, 0x0021, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
SMART_RCV_DRIVE_DATA = CTL_CODE(
    IOCTL_DISK_BASE, 0x0022, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_GET_PARTITION_INFO_EX = CTL_CODE(
    IOCTL_DISK_BASE, 0x0012, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_SET_PARTITION_INFO_EX = CTL_CODE(
    IOCTL_DISK_BASE, 0x0013, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_GET_DRIVE_LAYOUT_EX = CTL_CODE(
    IOCTL_DISK_BASE, 0x0014, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_SET_DRIVE_LAYOUT_EX = CTL_CODE(
    IOCTL_DISK_BASE, 0x0015, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_CREATE_DISK = CTL_CODE(
    IOCTL_DISK_BASE, 0x0016, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_GET_LENGTH_INFO = CTL_CODE(
    IOCTL_DISK_BASE, 0x0017, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_GET_DRIVE_GEOMETRY_EX = CTL_CODE(
    IOCTL_DISK_BASE, 0x0028, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_REASSIGN_BLOCKS_EX = CTL_CODE(
    IOCTL_DISK_BASE, 0x0029, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)

IOCTL_DISK_UPDATE_DRIVE_SIZE = CTL_CODE(
    IOCTL_DISK_BASE, 0x0032, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_GROW_PARTITION = CTL_CODE(
    IOCTL_DISK_BASE, 0x0034, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_GET_CACHE_INFORMATION = CTL_CODE(
    IOCTL_DISK_BASE, 0x0035, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_SET_CACHE_INFORMATION = CTL_CODE(
    IOCTL_DISK_BASE, 0x0036, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)

OBSOLETE_IOCTL_STORAGE_RESET_BUS = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0400, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
OBSOLETE_IOCTL_STORAGE_RESET_DEVICE = CTL_CODE(
    IOCTL_STORAGE_BASE, 0x0401, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
## the original define no longer exists in winioctl.h
OBSOLETE_DISK_GET_WRITE_CACHE_STATE = CTL_CODE(
    IOCTL_DISK_BASE, 0x0037, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_GET_WRITE_CACHE_STATE = OBSOLETE_DISK_GET_WRITE_CACHE_STATE


IOCTL_DISK_DELETE_DRIVE_LAYOUT = CTL_CODE(
    IOCTL_DISK_BASE, 0x0040, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_UPDATE_PROPERTIES = CTL_CODE(
    IOCTL_DISK_BASE, 0x0050, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_FORMAT_DRIVE = CTL_CODE(
    IOCTL_DISK_BASE, 0x00F3, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_DISK_SENSE_DEVICE = CTL_CODE(
    IOCTL_DISK_BASE, 0x00F8, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_DISK_CHECK_VERIFY = CTL_CODE(
    IOCTL_DISK_BASE, 0x0200, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_MEDIA_REMOVAL = CTL_CODE(
    IOCTL_DISK_BASE, 0x0201, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_EJECT_MEDIA = CTL_CODE(
    IOCTL_DISK_BASE, 0x0202, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_LOAD_MEDIA = CTL_CODE(
    IOCTL_DISK_BASE, 0x0203, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_RESERVE = CTL_CODE(
    IOCTL_DISK_BASE, 0x0204, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_RELEASE = CTL_CODE(
    IOCTL_DISK_BASE, 0x0205, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_FIND_NEW_DEVICES = CTL_CODE(
    IOCTL_DISK_BASE, 0x0206, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_DISK_GET_MEDIA_TYPES = CTL_CODE(
    IOCTL_DISK_BASE, 0x0300, METHOD_BUFFERED, FILE_ANY_ACCESS
)

DISK_HISTOGRAM_SIZE = 72
HISTOGRAM_BUCKET_SIZE = 8

IOCTL_CHANGER_GET_PARAMETERS = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x0000, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_CHANGER_GET_STATUS = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x0001, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_CHANGER_GET_PRODUCT_DATA = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x0002, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_CHANGER_SET_ACCESS = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x0004, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_CHANGER_GET_ELEMENT_STATUS = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x0005, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_CHANGER_INITIALIZE_ELEMENT_STATUS = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x0006, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_CHANGER_SET_POSITION = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x0007, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_CHANGER_EXCHANGE_MEDIUM = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x0008, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_CHANGER_MOVE_MEDIUM = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x0009, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_CHANGER_REINITIALIZE_TRANSPORT = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x000A, METHOD_BUFFERED, FILE_READ_ACCESS
)
IOCTL_CHANGER_QUERY_VOLUME_TAGS = CTL_CODE(
    IOCTL_CHANGER_BASE, 0x000B, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_SERIAL_LSRMST_INSERT = CTL_CODE(
    FILE_DEVICE_SERIAL_PORT, 31, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_SERENUM_EXPOSE_HARDWARE = CTL_CODE(
    FILE_DEVICE_SERENUM, 128, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_SERENUM_REMOVE_HARDWARE = CTL_CODE(
    FILE_DEVICE_SERENUM, 129, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_SERENUM_PORT_DESC = CTL_CODE(
    FILE_DEVICE_SERENUM, 130, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_SERENUM_GET_PORT_NAME = CTL_CODE(
    FILE_DEVICE_SERENUM, 131, METHOD_BUFFERED, FILE_ANY_ACCESS
)

## ??? can't find where FILE_DEVICE_AVIO is defined ???
## IOCTL_AVIO_ALLOCATE_STREAM = CTL_CODE(FILE_DEVICE_AVIO, 1, METHOD_BUFFERED, FILE_SPECIAL_ACCESS)
## IOCTL_AVIO_FREE_STREAM = CTL_CODE(FILE_DEVICE_AVIO, 2, METHOD_BUFFERED, FILE_SPECIAL_ACCESS)
## IOCTL_AVIO_MODIFY_STREAM = CTL_CODE(FILE_DEVICE_AVIO, 3, METHOD_BUFFERED, FILE_SPECIAL_ACCESS)

SERIAL_LSRMST_ESCAPE = 0x00
SERIAL_LSRMST_LSR_DATA = 0x01
SERIAL_LSRMST_LSR_NODATA = 0x02
SERIAL_LSRMST_MST = 0x03
SERIAL_IOC_FCR_FIFO_ENABLE = 0x00000001
SERIAL_IOC_FCR_RCVR_RESET = 0x00000002
SERIAL_IOC_FCR_XMIT_RESET = 0x00000004
SERIAL_IOC_FCR_DMA_MODE = 0x00000008
SERIAL_IOC_FCR_RES1 = 0x00000010
SERIAL_IOC_FCR_RES2 = 0x00000020
SERIAL_IOC_FCR_RCVR_TRIGGER_LSB = 0x00000040
SERIAL_IOC_FCR_RCVR_TRIGGER_MSB = 0x00000080
SERIAL_IOC_MCR_DTR = 0x00000001
SERIAL_IOC_MCR_RTS = 0x00000002
SERIAL_IOC_MCR_OUT1 = 0x00000004
SERIAL_IOC_MCR_OUT2 = 0x00000008
SERIAL_IOC_MCR_LOOP = 0x00000010
FSCTL_REQUEST_OPLOCK_LEVEL_1 = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 0, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_REQUEST_OPLOCK_LEVEL_2 = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 1, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_REQUEST_BATCH_OPLOCK = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 2, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_OPLOCK_BREAK_ACKNOWLEDGE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 3, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_OPBATCH_ACK_CLOSE_PENDING = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 4, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_OPLOCK_BREAK_NOTIFY = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 5, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_LOCK_VOLUME = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 6, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_UNLOCK_VOLUME = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 7, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_DISMOUNT_VOLUME = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 8, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_IS_VOLUME_MOUNTED = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 10, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_IS_PATHNAME_VALID = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 11, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_MARK_VOLUME_DIRTY = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 12, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_QUERY_RETRIEVAL_POINTERS = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 14, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_GET_COMPRESSION = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 15, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_SET_COMPRESSION = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 16, METHOD_BUFFERED, FILE_READ_DATA | FILE_WRITE_DATA
)
FSCTL_MARK_AS_SYSTEM_HIVE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 19, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_OPLOCK_BREAK_ACK_NO_2 = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 20, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_INVALIDATE_VOLUMES = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 21, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_QUERY_FAT_BPB = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 22, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_REQUEST_FILTER_OPLOCK = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 23, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_FILESYSTEM_GET_STATISTICS = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 24, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_GET_NTFS_VOLUME_DATA = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 25, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_GET_NTFS_FILE_RECORD = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 26, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_GET_VOLUME_BITMAP = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 27, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_GET_RETRIEVAL_POINTERS = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 28, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_MOVE_FILE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 29, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_IS_VOLUME_DIRTY = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 30, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_ALLOW_EXTENDED_DASD_IO = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 32, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_FIND_FILES_BY_SID = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 35, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_SET_OBJECT_ID = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 38, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_GET_OBJECT_ID = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 39, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_DELETE_OBJECT_ID = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 40, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_SET_REPARSE_POINT = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 41, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_GET_REPARSE_POINT = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 42, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_DELETE_REPARSE_POINT = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 43, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_ENUM_USN_DATA = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 44, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_SECURITY_ID_CHECK = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 45, METHOD_NEITHER, FILE_READ_DATA
)
FSCTL_READ_USN_JOURNAL = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 46, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_SET_OBJECT_ID_EXTENDED = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 47, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_CREATE_OR_GET_OBJECT_ID = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 48, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_SET_SPARSE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 49, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_SET_ZERO_DATA = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 50, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_QUERY_ALLOCATED_RANGES = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 51, METHOD_NEITHER, FILE_READ_DATA
)
FSCTL_SET_ENCRYPTION = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 53, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_ENCRYPTION_FSCTL_IO = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 54, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_WRITE_RAW_ENCRYPTED = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 55, METHOD_NEITHER, FILE_SPECIAL_ACCESS
)
FSCTL_READ_RAW_ENCRYPTED = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 56, METHOD_NEITHER, FILE_SPECIAL_ACCESS
)
FSCTL_CREATE_USN_JOURNAL = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 57, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_READ_FILE_USN_DATA = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 58, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_WRITE_USN_CLOSE_RECORD = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 59, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_EXTEND_VOLUME = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 60, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_QUERY_USN_JOURNAL = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 61, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_DELETE_USN_JOURNAL = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 62, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_MARK_HANDLE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 63, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_SIS_COPYFILE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 64, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_SIS_LINK_FILES = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 65, METHOD_BUFFERED, FILE_READ_DATA | FILE_WRITE_DATA
)
FSCTL_HSM_MSG = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 66, METHOD_BUFFERED, FILE_READ_DATA | FILE_WRITE_DATA
)
FSCTL_HSM_DATA = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 68, METHOD_NEITHER, FILE_READ_DATA | FILE_WRITE_DATA
)
FSCTL_RECALL_FILE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 69, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_READ_FROM_PLEX = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 71, METHOD_OUT_DIRECT, FILE_READ_DATA
)
FSCTL_FILE_PREFETCH = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 72, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_MAKE_MEDIA_COMPATIBLE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 76, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_SET_DEFECT_MANAGEMENT = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 77, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_QUERY_SPARING_INFO = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 78, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_QUERY_ON_DISK_VOLUME_INFO = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 79, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_SET_VOLUME_COMPRESSION_STATE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 80, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_TXFS_MODIFY_RM = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 81, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_TXFS_QUERY_RM_INFORMATION = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 82, METHOD_BUFFERED, FILE_READ_DATA
)
FSCTL_TXFS_ROLLFORWARD_REDO = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 84, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_TXFS_ROLLFORWARD_UNDO = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 85, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_TXFS_START_RM = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 86, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_TXFS_SHUTDOWN_RM = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 87, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_TXFS_READ_BACKUP_INFORMATION = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 88, METHOD_BUFFERED, FILE_READ_DATA
)
FSCTL_TXFS_WRITE_BACKUP_INFORMATION = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 89, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_TXFS_CREATE_SECONDARY_RM = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 90, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_TXFS_GET_METADATA_INFO = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 91, METHOD_BUFFERED, FILE_READ_DATA
)
FSCTL_TXFS_GET_TRANSACTED_VERSION = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 92, METHOD_BUFFERED, FILE_READ_DATA
)
FSCTL_TXFS_CREATE_MINIVERSION = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 95, METHOD_BUFFERED, FILE_WRITE_DATA
)
FSCTL_TXFS_TRANSACTION_ACTIVE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 99, METHOD_BUFFERED, FILE_READ_DATA
)
FSCTL_SET_ZERO_ON_DEALLOCATION = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 101, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_SET_REPAIR = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 102, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_GET_REPAIR = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 103, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_WAIT_FOR_REPAIR = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 104, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_INITIATE_REPAIR = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 106, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_CSC_INTERNAL = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 107, METHOD_NEITHER, FILE_ANY_ACCESS
)
FSCTL_SHRINK_VOLUME = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 108, METHOD_BUFFERED, FILE_SPECIAL_ACCESS
)
FSCTL_SET_SHORT_NAME_BEHAVIOR = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 109, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_DFSR_SET_GHOST_HANDLE_STATE = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 110, METHOD_BUFFERED, FILE_ANY_ACCESS
)
FSCTL_TXFS_LIST_TRANSACTION_LOCKED_FILES = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 120, METHOD_BUFFERED, FILE_READ_DATA
)
FSCTL_TXFS_LIST_TRANSACTIONS = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 121, METHOD_BUFFERED, FILE_READ_DATA
)
FSCTL_QUERY_PAGEFILE_ENCRYPTION = CTL_CODE(
    FILE_DEVICE_FILE_SYSTEM, 122, METHOD_BUFFERED, FILE_ANY_ACCESS
)

IOCTL_VOLUME_BASE = ord("V")
IOCTL_VOLUME_GET_VOLUME_DISK_EXTENTS = CTL_CODE(
    IOCTL_VOLUME_BASE, 0, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_VOLUME_ONLINE = CTL_CODE(
    IOCTL_VOLUME_BASE, 2, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_VOLUME_OFFLINE = CTL_CODE(
    IOCTL_VOLUME_BASE, 3, METHOD_BUFFERED, FILE_READ_ACCESS | FILE_WRITE_ACCESS
)
IOCTL_VOLUME_IS_CLUSTERED = CTL_CODE(
    IOCTL_VOLUME_BASE, 12, METHOD_BUFFERED, FILE_ANY_ACCESS
)
IOCTL_VOLUME_GET_GPT_ATTRIBUTES = CTL_CODE(
    IOCTL_VOLUME_BASE, 14, METHOD_BUFFERED, FILE_ANY_ACCESS
)

## enums
## STORAGE_MEDIA_TYPE
DDS_4mm = 32
MiniQic = 33
Travan = 34
QIC = 35
MP_8mm = 36
AME_8mm = 37
AIT1_8mm = 38
DLT = 39
NCTP = 40
IBM_3480 = 41
IBM_3490E = 42
IBM_Magstar_3590 = 43
IBM_Magstar_MP = 44
STK_DATA_D3 = 45
SONY_DTF = 46
DV_6mm = 47
DMI = 48
SONY_D2 = 49
CLEANER_CARTRIDGE = 50
CD_ROM = 51
CD_R = 52
CD_RW = 53
DVD_ROM = 54
DVD_R = 55
DVD_RW = 56
MO_3_RW = 57
MO_5_WO = 58
MO_5_RW = 59
MO_5_LIMDOW = 60
PC_5_WO = 61
PC_5_RW = 62
PD_5_RW = 63
ABL_5_WO = 64
PINNACLE_APEX_5_RW = 65
SONY_12_WO = 66
PHILIPS_12_WO = 67
HITACHI_12_WO = 68
CYGNET_12_WO = 69
KODAK_14_WO = 70
MO_NFR_525 = 71
NIKON_12_RW = 72
IOMEGA_ZIP = 73
IOMEGA_JAZ = 74
SYQUEST_EZ135 = 75
SYQUEST_EZFLYER = 76
SYQUEST_SYJET = 77
AVATAR_F2 = 78
MP2_8mm = 79
DST_S = 80
DST_M = 81
DST_L = 82
VXATape_1 = 83
VXATape_2 = 84
STK_9840 = 85
LTO_Ultrium = 86
LTO_Accelis = 87
DVD_RAM = 88
AIT_8mm = 89
ADR_1 = 90
ADR_2 = 91
STK_9940 = 92

## STORAGE_BUS_TYPE
BusTypeUnknown = 0
BusTypeScsi = 1
BusTypeAtapi = 2
BusTypeAta = 3
BusType1394 = 4
BusTypeSsa = 5
BusTypeFibre = 6
BusTypeUsb = 7
BusTypeRAID = 8
BusTypeiScsi = 9
BusTypeSas = 10
BusTypeSata = 11
BusTypeMaxReserved = 127

## MEDIA_TYPE
Unknown = 0
F5_1Pt2_512 = 1
F3_1Pt44_512 = 2
F3_2Pt88_512 = 3
F3_20Pt8_512 = 4
F3_720_512 = 5
F5_360_512 = 6
F5_320_512 = 7
F5_320_1024 = 8
F5_180_512 = 9
F5_160_512 = 10
RemovableMedia = 11
FixedMedia = 12
F3_120M_512 = 13
F3_640_512 = 14
F5_640_512 = 15
F5_720_512 = 16
F3_1Pt2_512 = 17
F3_1Pt23_1024 = 18
F5_1Pt23_1024 = 19
F3_128Mb_512 = 20
F3_230Mb_512 = 21
F8_256_128 = 22
F3_200Mb_512 = 23
F3_240M_512 = 24
F3_32M_512 = 25

## PARTITION_STYLE
PARTITION_STYLE_MBR = 0
PARTITION_STYLE_GPT = 1
PARTITION_STYLE_RAW = 2

## DETECTION_TYPE
DetectNone = 0
DetectInt13 = 1
DetectExInt13 = 2

## DISK_CACHE_RETENTION_PRIORITY
EqualPriority = 0
KeepPrefetchedData = 1
KeepReadData = 2

## DISK_WRITE_CACHE_STATE - ?????? this enum has disappeared from winioctl.h in windows 2003 SP1 sdk ??????
DiskWriteCacheNormal = 0
DiskWriteCacheForceDisable = 1
DiskWriteCacheDisableNotSupported = 2

## BIN_TYPES
RequestSize = 0
RequestLocation = 1

## CHANGER_DEVICE_PROBLEM_TYPE
DeviceProblemNone = 0
DeviceProblemHardware = 1
DeviceProblemCHMError = 2
DeviceProblemDoorOpen = 3
DeviceProblemCalibrationError = 4
DeviceProblemTargetFailure = 5
DeviceProblemCHMMoveError = 6
DeviceProblemCHMZeroError = 7
DeviceProblemCartridgeInsertError = 8
DeviceProblemPositionError = 9
DeviceProblemSensorError = 10
DeviceProblemCartridgeEjectError = 11
DeviceProblemGripperError = 12
DeviceProblemDriveError = 13