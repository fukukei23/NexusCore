
# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\tests\test_io.py ===
import gc
import gzip
import locale
import os
import re
import sys
import threading
import time
import warnings
from ctypes import c_bool
from datetime import datetime
from io import BytesIO, StringIO
from multiprocessing import Value, get_context
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

import numpy as np
import numpy.ma as ma
from numpy._utils import asbytes
from numpy.exceptions import VisibleDeprecationWarning
from numpy.lib import _npyio_impl
from numpy.lib._iotools import ConversionWarning, ConverterError
from numpy.lib._npyio_impl import recfromcsv, recfromtxt
from numpy.ma.testutils import assert_equal
from numpy.testing import (
    HAS_REFCOUNT,
    IS_PYPY,
    IS_WASM,
    assert_,
    assert_allclose,
    assert_array_equal,
    assert_no_gc_cycles,
    assert_no_warnings,
    assert_raises,
    assert_raises_regex,
    assert_warns,
    break_cycles,
    suppress_warnings,
    tempdir,
    temppath,
)
from numpy.testing._private.utils import requires_memory


class TextIO(BytesIO):
    """Helper IO class.

    Writes encode strings to bytes if needed, reads return bytes.
    This makes it easier to emulate files opened in binary mode
    without needing to explicitly convert strings to bytes in
    setting up the test data.

    """
    def __init__(self, s=""):
        BytesIO.__init__(self, asbytes(s))

    def write(self, s):
        BytesIO.write(self, asbytes(s))

    def writelines(self, lines):
        BytesIO.writelines(self, [asbytes(s) for s in lines])


IS_64BIT = sys.maxsize > 2**32
try:
    import bz2
    HAS_BZ2 = True
except ImportError:
    HAS_BZ2 = False
try:
    import lzma
    HAS_LZMA = True
except ImportError:
    HAS_LZMA = False


def strptime(s, fmt=None):
    """
    This function is available in the datetime module only from Python >=
    2.5.

    """
    if isinstance(s, bytes):
        s = s.decode("latin1")
    return datetime(*time.strptime(s, fmt)[:3])


class RoundtripTest:
    def roundtrip(self, save_func, *args, **kwargs):
        """
        save_func : callable
            Function used to save arrays to file.
        file_on_disk : bool
            If true, store the file on disk, instead of in a
            string buffer.
        save_kwds : dict
            Parameters passed to `save_func`.
        load_kwds : dict
            Parameters passed to `numpy.load`.
        args : tuple of arrays
            Arrays stored to file.

        """
        save_kwds = kwargs.get('save_kwds', {})
        load_kwds = kwargs.get('load_kwds', {"allow_pickle": True})
        file_on_disk = kwargs.get('file_on_disk', False)

        if file_on_disk:
            target_file = NamedTemporaryFile(delete=False)
            load_file = target_file.name
        else:
            target_file = BytesIO()
            load_file = target_file

        try:
            arr = args

            save_func(target_file, *arr, **save_kwds)
            target_file.flush()
            target_file.seek(0)

            if sys.platform == 'win32' and not isinstance(target_file, BytesIO):
                target_file.close()

            arr_reloaded = np.load(load_file, **load_kwds)

            self.arr = arr
            self.arr_reloaded = arr_reloaded
        finally:
            if not isinstance(target_file, BytesIO):
                target_file.close()
                # holds an open file descriptor so it can't be deleted on win
                if 'arr_reloaded' in locals():
                    if not isinstance(arr_reloaded, np.lib.npyio.NpzFile):
                        os.remove(target_file.name)

    def check_roundtrips(self, a):
        self.roundtrip(a)
        self.roundtrip(a, file_on_disk=True)
        self.roundtrip(np.asfortranarray(a))
        self.roundtrip(np.asfortranarray(a), file_on_disk=True)
        if a.shape[0] > 1:
            # neither C nor Fortran contiguous for 2D arrays or more
            self.roundtrip(np.asfortranarray(a)[1:])
            self.roundtrip(np.asfortranarray(a)[1:], file_on_disk=True)

    def test_array(self):
        a = np.array([], float)
        self.check_roundtrips(a)

        a = np.array([[1, 2], [3, 4]], float)
        self.check_roundtrips(a)

        a = np.array([[1, 2], [3, 4]], int)
        self.check_roundtrips(a)

        a = np.array([[1 + 5j, 2 + 6j], [3 + 7j, 4 + 8j]], dtype=np.csingle)
        self.check_roundtrips(a)

        a = np.array([[1 + 5j, 2 + 6j], [3 + 7j, 4 + 8j]], dtype=np.cdouble)
        self.check_roundtrips(a)

    def test_array_object(self):
        a = np.array([], object)
        self.check_roundtrips(a)

        a = np.array([[1, 2], [3, 4]], object)
        self.check_roundtrips(a)

    def test_1D(self):
        a = np.array([1, 2, 3, 4], int)
        self.roundtrip(a)

    @pytest.mark.skipif(sys.platform == 'win32', reason="Fails on Win32")
    def test_mmap(self):
        a = np.array([[1, 2.5], [4, 7.3]])
        self.roundtrip(a, file_on_disk=True, load_kwds={'mmap_mode': 'r'})

        a = np.asfortranarray([[1, 2.5], [4, 7.3]])
        self.roundtrip(a, file_on_disk=True, load_kwds={'mmap_mode': 'r'})

    def test_record(self):
        a = np.array([(1, 2), (3, 4)], dtype=[('x', 'i4'), ('y', 'i4')])
        self.check_roundtrips(a)

    @pytest.mark.slow
    def test_format_2_0(self):
        dt = [(("%d" % i) * 100, float) for i in range(500)]
        a = np.ones(1000, dtype=dt)
        with warnings.catch_warnings(record=True):
            warnings.filterwarnings('always', '', UserWarning)
            self.check_roundtrips(a)


class TestSaveLoad(RoundtripTest):
    def roundtrip(self, *args, **kwargs):
        RoundtripTest.roundtrip(self, np.save, *args, **kwargs)
        assert_equal(self.arr[0], self.arr_reloaded)
        assert_equal(self.arr[0].dtype, self.arr_reloaded.dtype)
        assert_equal(self.arr[0].flags.fnc, self.arr_reloaded.flags.fnc)


class TestSavezLoad(RoundtripTest):
    def roundtrip(self, *args, **kwargs):
        RoundtripTest.roundtrip(self, np.savez, *args, **kwargs)
        try:
            for n, arr in enumerate(self.arr):
                reloaded = self.arr_reloaded['arr_%d' % n]
                assert_equal(arr, reloaded)
                assert_equal(arr.dtype, reloaded.dtype)
                assert_equal(arr.flags.fnc, reloaded.flags.fnc)
        finally:
            # delete tempfile, must be done here on windows
            if self.arr_reloaded.fid:
                self.arr_reloaded.fid.close()
                os.remove(self.arr_reloaded.fid.name)

    @pytest.mark.skipif(IS_PYPY, reason="Hangs on PyPy")
    @pytest.mark.skipif(not IS_64BIT, reason="Needs 64bit platform")
    @pytest.mark.slow
    def test_big_arrays(self):
        L = (1 << 31) + 100000
        a = np.empty(L, dtype=np.uint8)
        with temppath(prefix="numpy_test_big_arrays_", suffix=".npz") as tmp:
            np.savez(tmp, a=a)
            del a
            npfile = np.load(tmp)
            a = npfile['a']  # Should succeed
            npfile.close()

    def test_multiple_arrays(self):
        a = np.array([[1, 2], [3, 4]], float)
        b = np.array([[1 + 2j, 2 + 7j], [3 - 6j, 4 + 12j]], complex)
        self.roundtrip(a, b)

    def test_named_arrays(self):
        a = np.array([[1, 2], [3, 4]], float)
        b = np.array([[1 + 2j, 2 + 7j], [3 - 6j, 4 + 12j]], complex)
        c = BytesIO()
        np.savez(c, file_a=a, file_b=b)
        c.seek(0)
        l = np.load(c)
        assert_equal(a, l['file_a'])
        assert_equal(b, l['file_b'])

    def test_tuple_getitem_raises(self):
        # gh-23748
        a = np.array([1, 2, 3])
        f = BytesIO()
        np.savez(f, a=a)
        f.seek(0)
        l = np.load(f)
        with pytest.raises(KeyError, match="(1, 2)"):
            l[1, 2]

    def test_BagObj(self):
        a = np.array([[1, 2], [3, 4]], float)
        b = np.array([[1 + 2j, 2 + 7j], [3 - 6j, 4 + 12j]], complex)
        c = BytesIO()
        np.savez(c, file_a=a, file_b=b)
        c.seek(0)
        l = np.load(c)
        assert_equal(sorted(dir(l.f)), ['file_a', 'file_b'])
        assert_equal(a, l.f.file_a)
        assert_equal(b, l.f.file_b)

    @pytest.mark.skipif(IS_WASM, reason="Cannot start thread")
    def test_savez_filename_clashes(self):
        # Test that issue #852 is fixed
        # and savez functions in multithreaded environment

        def writer(error_list):
            with temppath(suffix='.npz') as tmp:
                arr = np.random.randn(500, 500)
                try:
                    np.savez(tmp, arr=arr)
                except OSError as err:
                    error_list.append(err)

        errors = []
        threads = [threading.Thread(target=writer, args=(errors,))
                   for j in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        if errors:
            raise AssertionError(errors)

    def test_not_closing_opened_fid(self):
        # Test that issue #2178 is fixed:
        # verify could seek on 'loaded' file
        with temppath(suffix='.npz') as tmp:
            with open(tmp, 'wb') as fp:
                np.savez(fp, data='LOVELY LOAD')
            with open(tmp, 'rb', 10000) as fp:
                fp.seek(0)
                assert_(not fp.closed)
                np.load(fp)['data']
                # fp must not get closed by .load
                assert_(not fp.closed)
                fp.seek(0)
                assert_(not fp.closed)

    @pytest.mark.slow_pypy
    def test_closing_fid(self):
        # Test that issue #1517 (too many opened files) remains closed
        # It might be a "weak" test since failed to get triggered on
        # e.g. Debian sid of 2012 Jul 05 but was reported to
        # trigger the failure on Ubuntu 10.04:
        # http://projects.scipy.org/numpy/ticket/1517#comment:2
        with temppath(suffix='.npz') as tmp:
            np.savez(tmp, data='LOVELY LOAD')
            # We need to check if the garbage collector can properly close
            # numpy npz file returned by np.load when their reference count
            # goes to zero.  Python running in debug mode raises a
            # ResourceWarning when file closing is left to the garbage
            # collector, so we catch the warnings.
            with suppress_warnings() as sup:
                sup.filter(ResourceWarning)  # TODO: specify exact message
                for i in range(1, 1025):
                    try:
                        np.load(tmp)["data"]
                    except Exception as e:
                        msg = f"Failed to load data from a file: {e}"
                        raise AssertionError(msg)
                    finally:
                        if IS_PYPY:
                            gc.collect()

    def test_closing_zipfile_after_load(self):
        # Check that zipfile owns file and can close it.  This needs to
        # pass a file name to load for the test. On windows failure will
        # cause a second error will be raised when the attempt to remove
        # the open file is made.
        prefix = 'numpy_test_closing_zipfile_after_load_'
        with temppath(suffix='.npz', prefix=prefix) as tmp:
            np.savez(tmp, lab='place holder')
            data = np.load(tmp)
            fp = data.zip.fp
            data.close()
            assert_(fp.closed)

    @pytest.mark.parametrize("count, expected_repr", [
        (1, "NpzFile {fname!r} with keys: arr_0"),
        (5, "NpzFile {fname!r} with keys: arr_0, arr_1, arr_2, arr_3, arr_4"),
        # _MAX_REPR_ARRAY_COUNT is 5, so files with more than 5 keys are
        # expected to end in '...'
        (6, "NpzFile {fname!r} with keys: arr_0, arr_1, arr_2, arr_3, arr_4..."),
    ])
    def test_repr_lists_keys(self, count, expected_repr):
        a = np.array([[1, 2], [3, 4]], float)
        with temppath(suffix='.npz') as tmp:
            np.savez(tmp, *[a] * count)
            l = np.load(tmp)
            assert repr(l) == expected_repr.format(fname=tmp)
            l.close()


class TestSaveTxt:
    def test_array(self):
        a = np.array([[1, 2], [3, 4]], float)
        fmt = "%.18e"
        c = BytesIO()
        np.savetxt(c, a, fmt=fmt)
        c.seek(0)
        assert_equal(c.readlines(),
                     [asbytes((fmt + ' ' + fmt + '\n') % (1, 2)),
                      asbytes((fmt + ' ' + fmt + '\n') % (3, 4))])

        a = np.array([[1, 2], [3, 4]], int)
        c = BytesIO()
        np.savetxt(c, a, fmt='%d')
        c.seek(0)
        assert_equal(c.readlines(), [b'1 2\n', b'3 4\n'])

    def test_1D(self):
        a = np.array([1, 2, 3, 4], int)
        c = BytesIO()
        np.savetxt(c, a, fmt='%d')
        c.seek(0)
        lines = c.readlines()
        assert_equal(lines, [b'1\n', b'2\n', b'3\n', b'4\n'])

    def test_0D_3D(self):
        c = BytesIO()
        assert_raises(ValueError, np.savetxt, c, np.array(1))
        assert_raises(ValueError, np.savetxt, c, np.array([[[1], [2]]]))

    def test_structured(self):
        a = np.array([(1, 2), (3, 4)], dtype=[('x', 'i4'), ('y', 'i4')])
        c = BytesIO()
        np.savetxt(c, a, fmt='%d')
        c.seek(0)
        assert_equal(c.readlines(), [b'1 2\n', b'3 4\n'])

    def test_structured_padded(self):
        # gh-13297
        a = np.array([(1, 2, 3), (4, 5, 6)], dtype=[
            ('foo', 'i4'), ('bar', 'i4'), ('baz', 'i4')
        ])
        c = BytesIO()
        np.savetxt(c, a[['foo', 'baz']], fmt='%d')
        c.seek(0)
        assert_equal(c.readlines(), [b'1 3\n', b'4 6\n'])

    def test_multifield_view(self):
        a = np.ones(1, dtype=[('x', 'i4'), ('y', 'i4'), ('z', 'f4')])
        v = a[['x', 'z']]
        with temppath(suffix='.npy') as path:
            path = Path(path)
            np.save(path, v)
            data = np.load(path)
            assert_array_equal(data, v)

    def test_delimiter(self):
        a = np.array([[1., 2.], [3., 4.]])
        c = BytesIO()
        np.savetxt(c, a, delimiter=',', fmt='%d')
        c.seek(0)
        assert_equal(c.readlines(), [b'1,2\n', b'3,4\n'])

    def test_format(self):
        a = np.array([(1, 2), (3, 4)])
        c = BytesIO()
        # Sequence of formats
        np.savetxt(c, a, fmt=['%02d', '%3.1f'])
        c.seek(0)
        assert_equal(c.readlines(), [b'01 2.0\n', b'03 4.0\n'])

        # A single multiformat string
        c = BytesIO()
        np.savetxt(c, a, fmt='%02d : %3.1f')
        c.seek(0)
        lines = c.readlines()
        assert_equal(lines, [b'01 : 2.0\n', b'03 : 4.0\n'])

        # Specify delimiter, should be overridden
        c = BytesIO()
        np.savetxt(c, a, fmt='%02d : %3.1f', delimiter=',')
        c.seek(0)
        lines = c.readlines()
        assert_equal(lines, [b'01 : 2.0\n', b'03 : 4.0\n'])

        # Bad fmt, should raise a ValueError
        c = BytesIO()
        assert_raises(ValueError, np.savetxt, c, a, fmt=99)

    def test_header_footer(self):
        # Test the functionality of the header and footer keyword argument.

        c = BytesIO()
        a = np.array([(1, 2), (3, 4)], dtype=int)
        test_header_footer = 'Test header / footer'
        # Test the header keyword argument
        np.savetxt(c, a, fmt='%1d', header=test_header_footer)
        c.seek(0)
        assert_equal(c.read(),
                     asbytes('# ' + test_header_footer + '\n1 2\n3 4\n'))
        # Test the footer keyword argument
        c = BytesIO()
        np.savetxt(c, a, fmt='%1d', footer=test_header_footer)
        c.seek(0)
        assert_equal(c.read(),
                     asbytes('1 2\n3 4\n# ' + test_header_footer + '\n'))
        # Test the commentstr keyword argument used on the header
        c = BytesIO()
        commentstr = '% '
        np.savetxt(c, a, fmt='%1d',
                   header=test_header_footer, comments=commentstr)
        c.seek(0)
        assert_equal(c.read(),
                     asbytes(commentstr + test_header_footer + '\n' + '1 2\n3 4\n'))
        # Test the commentstr keyword argument used on the footer
        c = BytesIO()
        commentstr = '% '
        np.savetxt(c, a, fmt='%1d',
                   footer=test_header_footer, comments=commentstr)
        c.seek(0)
        assert_equal(c.read(),
                     asbytes('1 2\n3 4\n' + commentstr + test_header_footer + '\n'))

    @pytest.mark.parametrize("filename_type", [Path, str])
    def test_file_roundtrip(self, filename_type):
        with temppath() as name:
            a = np.array([(1, 2), (3, 4)])
            np.savetxt(filename_type(name), a)
            b = np.loadtxt(filename_type(name))
            assert_array_equal(a, b)

    def test_complex_arrays(self):
        ncols = 2
        nrows = 2
        a = np.zeros((ncols, nrows), dtype=np.complex128)
        re = np.pi
        im = np.e
        a[:] = re + 1.0j * im

        # One format only
        c = BytesIO()
        np.savetxt(c, a, fmt=' %+.3e')
        c.seek(0)
        lines = c.readlines()
        assert_equal(
            lines,
            [b' ( +3.142e+00+ +2.718e+00j)  ( +3.142e+00+ +2.718e+00j)\n',
             b' ( +3.142e+00+ +2.718e+00j)  ( +3.142e+00+ +2.718e+00j)\n'])

        # One format for each real and imaginary part
        c = BytesIO()
        np.savetxt(c, a, fmt='  %+.3e' * 2 * ncols)
        c.seek(0)
        lines = c.readlines()
        assert_equal(
            lines,
            [b'  +3.142e+00  +2.718e+00  +3.142e+00  +2.718e+00\n',
             b'  +3.142e+00  +2.718e+00  +3.142e+00  +2.718e+00\n'])

        # One format for each complex number
        c = BytesIO()
        np.savetxt(c, a, fmt=['(%.3e%+.3ej)'] * ncols)
        c.seek(0)
        lines = c.readlines()
        assert_equal(
            lines,
            [b'(3.142e+00+2.718e+00j) (3.142e+00+2.718e+00j)\n',
             b'(3.142e+00+2.718e+00j) (3.142e+00+2.718e+00j)\n'])

    def test_complex_negative_exponent(self):
        # Previous to 1.15, some formats generated x+-yj, gh 7895
        ncols = 2
        nrows = 2
        a = np.zeros((ncols, nrows), dtype=np.complex128)
        re = np.pi
        im = np.e
        a[:] = re - 1.0j * im
        c = BytesIO()
        np.savetxt(c, a, fmt='%.3e')
        c.seek(0)
        lines = c.readlines()
        assert_equal(
            lines,
            [b' (3.142e+00-2.718e+00j)  (3.142e+00-2.718e+00j)\n',
             b' (3.142e+00-2.718e+00j)  (3.142e+00-2.718e+00j)\n'])

    def test_custom_writer(self):

        class CustomWriter(list):
            def write(self, text):
                self.extend(text.split(b'\n'))

        w = CustomWriter()
        a = np.array([(1, 2), (3, 4)])
        np.savetxt(w, a)
        b = np.loadtxt(w)
        assert_array_equal(a, b)

    def test_unicode(self):
        utf8 = b'\xcf\x96'.decode('UTF-8')
        a = np.array([utf8], dtype=np.str_)
        with tempdir() as tmpdir:
            # set encoding as on windows it may not be unicode even on py3
            np.savetxt(os.path.join(tmpdir, 'test.csv'), a, fmt=['%s'],
                       encoding='UTF-8')

    def test_unicode_roundtrip(self):
        utf8 = b'\xcf\x96'.decode('UTF-8')
        a = np.array([utf8], dtype=np.str_)
        # our gz wrapper support encoding
        suffixes = ['', '.gz']
        if HAS_BZ2:
            suffixes.append('.bz2')
        if HAS_LZMA:
            suffixes.extend(['.xz', '.lzma'])
        with tempdir() as tmpdir:
            for suffix in suffixes:
                np.savetxt(os.path.join(tmpdir, 'test.csv' + suffix), a,
                           fmt=['%s'], encoding='UTF-16-LE')
                b = np.loadtxt(os.path.join(tmpdir, 'test.csv' + suffix),
                               encoding='UTF-16-LE', dtype=np.str_)
                assert_array_equal(a, b)

    def test_unicode_bytestream(self):
        utf8 = b'\xcf\x96'.decode('UTF-8')
        a = np.array([utf8], dtype=np.str_)
        s = BytesIO()
        np.savetxt(s, a, fmt=['%s'], encoding='UTF-8')
        s.seek(0)
        assert_equal(s.read().decode('UTF-8'), utf8 + '\n')

    def test_unicode_stringstream(self):
        utf8 = b'\xcf\x96'.decode('UTF-8')
        a = np.array([utf8], dtype=np.str_)
        s = StringIO()
        np.savetxt(s, a, fmt=['%s'], encoding='UTF-8')
        s.seek(0)
        assert_equal(s.read(), utf8 + '\n')

    @pytest.mark.parametrize("iotype", [StringIO, BytesIO])
    def test_unicode_and_bytes_fmt(self, iotype):
        # string type of fmt should not matter, see also gh-4053
        a = np.array([1.])
        s = iotype()
        np.savetxt(s, a, fmt="%f")
        s.seek(0)
        if iotype is StringIO:
            assert_equal(s.read(), "%f\n" % 1.)
        else:
            assert_equal(s.read(), b"%f\n" % 1.)

    @pytest.mark.skipif(sys.platform == 'win32', reason="files>4GB may not work")
    @pytest.mark.slow
    @requires_memory(free_bytes=7e9)
    def test_large_zip(self):
        def check_large_zip(memoryerror_raised):
            memoryerror_raised.value = False
            try:
                # The test takes at least 6GB of memory, writes a file larger
                # than 4GB. This tests the ``allowZip64`` kwarg to ``zipfile``
                test_data = np.asarray([np.random.rand(
                                        np.random.randint(50, 100), 4)
                                        for i in range(800000)], dtype=object)
                with tempdir() as tmpdir:
                    np.savez(os.path.join(tmpdir, 'test.npz'),
                             test_data=test_data)
            except MemoryError:
                memoryerror_raised.value = True
                raise
        # run in a subprocess to ensure memory is released on PyPy, see gh-15775
        # Use an object in shared memory to re-raise the MemoryError exception
        # in our process if needed, see gh-16889
        memoryerror_raised = Value(c_bool)

        # Since Python 3.8, the default start method for multiprocessing has
        # been changed from 'fork' to 'spawn' on macOS, causing inconsistency
        # on memory sharing model, leading to failed test for check_large_zip
        ctx = get_context('fork')
        p = ctx.Process(target=check_large_zip, args=(memoryerror_raised,))
        p.start()
        p.join()
        if memoryerror_raised.value:
            raise MemoryError("Child process raised a MemoryError exception")
        # -9 indicates a SIGKILL, probably an OOM.
        if p.exitcode == -9:
            pytest.xfail("subprocess got a SIGKILL, apparently free memory was not sufficient")
        assert p.exitcode == 0

class LoadTxtBase:
    def check_compressed(self, fopen, suffixes):
        # Test that we can load data from a compressed file
        wanted = np.arange(6).reshape((2, 3))
        linesep = ('\n', '\r\n', '\r')
        for sep in linesep:
            data = '0 1 2' + sep + '3 4 5'
            for suffix in suffixes:
                with temppath(suffix=suffix) as name:
                    with fopen(name, mode='wt', encoding='UTF-32-LE') as f:
                        f.write(data)
                    res = self.loadfunc(name, encoding='UTF-32-LE')
                    assert_array_equal(res, wanted)
                    with fopen(name, "rt",  encoding='UTF-32-LE') as f:
                        res = self.loadfunc(f)
                    assert_array_equal(res, wanted)

    def test_compressed_gzip(self):
        self.check_compressed(gzip.open, ('.gz',))

    @pytest.mark.skipif(not HAS_BZ2, reason="Needs bz2")
    def test_compressed_bz2(self):
        self.check_compressed(bz2.open, ('.bz2',))

    @pytest.mark.skipif(not HAS_LZMA, reason="Needs lzma")
    def test_compressed_lzma(self):
        self.check_compressed(lzma.open, ('.xz', '.lzma'))

    def test_encoding(self):
        with temppath() as path:
            with open(path, "wb") as f:
                f.write('0.\n1.\n2.'.encode("UTF-16"))
            x = self.loadfunc(path, encoding="UTF-16")
            assert_array_equal(x, [0., 1., 2.])

    def test_stringload(self):
        # umlaute
        nonascii = b'\xc3\xb6\xc3\xbc\xc3\xb6'.decode("UTF-8")
        with temppath() as path:
            with open(path, "wb") as f:
                f.write(nonascii.encode("UTF-16"))
            x = self.loadfunc(path, encoding="UTF-16", dtype=np.str_)
            assert_array_equal(x, nonascii)

    def test_binary_decode(self):
        utf16 = b'\xff\xfeh\x04 \x00i\x04 \x00j\x04'
        v = self.loadfunc(BytesIO(utf16), dtype=np.str_, encoding='UTF-16')
        assert_array_equal(v, np.array(utf16.decode('UTF-16').split()))

    def test_converters_decode(self):
        # test converters that decode strings
        c = TextIO()
        c.write(b'\xcf\x96')
        c.seek(0)
        x = self.loadfunc(c, dtype=np.str_, encoding="bytes",
                          converters={0: lambda x: x.decode('UTF-8')})
        a = np.array([b'\xcf\x96'.decode('UTF-8')])
        assert_array_equal(x, a)

    def test_converters_nodecode(self):
        # test native string converters enabled by setting an encoding
        utf8 = b'\xcf\x96'.decode('UTF-8')
        with temppath() as path:
            with open(path, 'wt', encoding='UTF-8') as f:
                f.write(utf8)
            x = self.loadfunc(path, dtype=np.str_,
                              converters={0: lambda x: x + 't'},
                              encoding='UTF-8')
            a = np.array([utf8 + 't'])
            assert_array_equal(x, a)


class TestLoadTxt(LoadTxtBase):
    loadfunc = staticmethod(np.loadtxt)

    def setup_method(self):
        # lower chunksize for testing
        self.orig_chunk = _npyio_impl._loadtxt_chunksize
        _npyio_impl._loadtxt_chunksize = 1

    def teardown_method(self):
        _npyio_impl._loadtxt_chunksize = self.orig_chunk

    def test_record(self):
        c = TextIO()
        c.write('1 2\n3 4')
        c.seek(0)
        x = np.loadtxt(c, dtype=[('x', np.int32), ('y', np.int32)])
        a = np.array([(1, 2), (3, 4)], dtype=[('x', 'i4'), ('y', 'i4')])
        assert_array_equal(x, a)

        d = TextIO()
        d.write('M 64 75.0\nF 25 60.0')
        d.seek(0)
        mydescriptor = {'names': ('gender', 'age', 'weight'),
                        'formats': ('S1', 'i4', 'f4')}
        b = np.array([('M', 64.0, 75.0),
                      ('F', 25.0, 60.0)], dtype=mydescriptor)
        y = np.loadtxt(d, dtype=mydescriptor)
        assert_array_equal(y, b)

    def test_array(self):
        c = TextIO()
        c.write('1 2\n3 4')

        c.seek(0)
        x = np.loadtxt(c, dtype=int)
        a = np.array([[1, 2], [3, 4]], int)
        assert_array_equal(x, a)

        c.seek(0)
        x = np.loadtxt(c, dtype=float)
        a = np.array([[1, 2], [3, 4]], float)
        assert_array_equal(x, a)

    def test_1D(self):
        c = TextIO()
        c.write('1\n2\n3\n4\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int)
        a = np.array([1, 2, 3, 4], int)
        assert_array_equal(x, a)

        c = TextIO()
        c.write('1,2,3,4\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',')
        a = np.array([1, 2, 3, 4], int)
        assert_array_equal(x, a)

    def test_missing(self):
        c = TextIO()
        c.write('1,2,3,,5\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       converters={3: lambda s: int(s or - 999)})
        a = np.array([1, 2, 3, -999, 5], int)
        assert_array_equal(x, a)

    def test_converters_with_usecols(self):
        c = TextIO()
        c.write('1,2,3,,5\n6,7,8,9,10\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       converters={3: lambda s: int(s or - 999)},
                       usecols=(1, 3,))
        a = np.array([[2, -999], [7, 9]], int)
        assert_array_equal(x, a)

    def test_comments_unicode(self):
        c = TextIO()
        c.write('# comment\n1,2,3,5\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       comments='#')
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

    def test_comments_byte(self):
        c = TextIO()
        c.write('# comment\n1,2,3,5\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       comments=b'#')
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

    def test_comments_multiple(self):
        c = TextIO()
        c.write('# comment\n1,2,3\n@ comment2\n4,5,6 // comment3')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       comments=['#', '@', '//'])
        a = np.array([[1, 2, 3], [4, 5, 6]], int)
        assert_array_equal(x, a)

    @pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                        reason="PyPy bug in error formatting")
    def test_comments_multi_chars(self):
        c = TextIO()
        c.write('/* comment\n1,2,3,5\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       comments='/*')
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

        # Check that '/*' is not transformed to ['/', '*']
        c = TextIO()
        c.write('*/ comment\n1,2,3,5\n')
        c.seek(0)
        assert_raises(ValueError, np.loadtxt, c, dtype=int, delimiter=',',
                      comments='/*')

    def test_skiprows(self):
        c = TextIO()
        c.write('comment\n1,2,3,5\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       skiprows=1)
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

        c = TextIO()
        c.write('# comment\n1,2,3,5\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       skiprows=1)
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

    def test_usecols(self):
        a = np.array([[1, 2], [3, 4]], float)
        c = BytesIO()
        np.savetxt(c, a)
        c.seek(0)
        x = np.loadtxt(c, dtype=float, usecols=(1,))
        assert_array_equal(x, a[:, 1])

        a = np.array([[1, 2, 3], [3, 4, 5]], float)
        c = BytesIO()
        np.savetxt(c, a)
        c.seek(0)
        x = np.loadtxt(c, dtype=float, usecols=(1, 2))
        assert_array_equal(x, a[:, 1:])

        # Testing with arrays instead of tuples.
        c.seek(0)
        x = np.loadtxt(c, dtype=float, usecols=np.array([1, 2]))
        assert_array_equal(x, a[:, 1:])

        # Testing with an integer instead of a sequence
        for int_type in [int, np.int8, np.int16,
                         np.int32, np.int64, np.uint8, np.uint16,
                         np.uint32, np.uint64]:
            to_read = int_type(1)
            c.seek(0)
            x = np.loadtxt(c, dtype=float, usecols=to_read)
            assert_array_equal(x, a[:, 1])

        # Testing with some crazy custom integer type
        class CrazyInt:
            def __index__(self):
                return 1

        crazy_int = CrazyInt()
        c.seek(0)
        x = np.loadtxt(c, dtype=float, usecols=crazy_int)
        assert_array_equal(x, a[:, 1])

        c.seek(0)
        x = np.loadtxt(c, dtype=float, usecols=(crazy_int,))
        assert_array_equal(x, a[:, 1])

        # Checking with dtypes defined converters.
        data = '''JOE 70.1 25.3
                BOB 60.5 27.9
                '''
        c = TextIO(data)
        names = ['stid', 'temp']
        dtypes = ['S4', 'f8']
        arr = np.loadtxt(c, usecols=(0, 2), dtype=list(zip(names, dtypes)))
        assert_equal(arr['stid'], [b"JOE", b"BOB"])
        assert_equal(arr['temp'], [25.3, 27.9])

        # Testing non-ints in usecols
        c.seek(0)
        bogus_idx = 1.5
        assert_raises_regex(
            TypeError,
            f'^usecols must be.*{type(bogus_idx).__name__}',
            np.loadtxt, c, usecols=bogus_idx
            )

        assert_raises_regex(
            TypeError,
            f'^usecols must be.*{type(bogus_idx).__name__}',
            np.loadtxt, c, usecols=[0, bogus_idx, 0]
            )

    def test_bad_usecols(self):
        with pytest.raises(OverflowError):
            np.loadtxt(["1\n"], usecols=[2**64], delimiter=",")
        with pytest.raises((ValueError, OverflowError)):
            # Overflow error on 32bit platforms
            np.loadtxt(["1\n"], usecols=[2**62], delimiter=",")
        with pytest.raises(TypeError,
                match="If a structured dtype .*. But 1 usecols were given and "
                      "the number of fields is 3."):
            np.loadtxt(["1,1\n"], dtype="i,2i", usecols=[0], delimiter=",")

    def test_fancy_dtype(self):
        c = TextIO()
        c.write('1,2,3.0\n4,5,6.0\n')
        c.seek(0)
        dt = np.dtype([('x', int), ('y', [('t', int), ('s', float)])])
        x = np.loadtxt(c, dtype=dt, delimiter=',')
        a = np.array([(1, (2, 3.0)), (4, (5, 6.0))], dt)
        assert_array_equal(x, a)

    def test_shaped_dtype(self):
        c = TextIO("aaaa  1.0  8.0  1 2 3 4 5 6")
        dt = np.dtype([('name', 'S4'), ('x', float), ('y', float),
                       ('block', int, (2, 3))])
        x = np.loadtxt(c, dtype=dt)
        a = np.array([('aaaa', 1.0, 8.0, [[1, 2, 3], [4, 5, 6]])],
                     dtype=dt)
        assert_array_equal(x, a)

    def test_3d_shaped_dtype(self):
        c = TextIO("aaaa  1.0  8.0  1 2 3 4 5 6 7 8 9 10 11 12")
        dt = np.dtype([('name', 'S4'), ('x', float), ('y', float),
                       ('block', int, (2, 2, 3))])
        x = np.loadtxt(c, dtype=dt)
        a = np.array([('aaaa', 1.0, 8.0,
                       [[[1, 2, 3], [4, 5, 6]], [[7, 8, 9], [10, 11, 12]]])],
                     dtype=dt)
        assert_array_equal(x, a)

    def test_str_dtype(self):
        # see gh-8033
        c = ["str1", "str2"]

        for dt in (str, np.bytes_):
            a = np.array(["str1", "str2"], dtype=dt)
            x = np.loadtxt(c, dtype=dt)
            assert_array_equal(x, a)

    def test_empty_file(self):
        with pytest.warns(UserWarning, match="input contained no data"):
            c = TextIO()
            x = np.loadtxt(c)
            assert_equal(x.shape, (0,))
            x = np.loadtxt(c, dtype=np.int64)
            assert_equal(x.shape, (0,))
            assert_(x.dtype == np.int64)

    def test_unused_converter(self):
        c = TextIO()
        c.writelines(['1 21\n', '3 42\n'])
        c.seek(0)
        data = np.loadtxt(c, usecols=(1,),
                          converters={0: lambda s: int(s, 16)})
        assert_array_equal(data, [21, 42])

        c.seek(0)
        data = np.loadtxt(c, usecols=(1,),
                          converters={1: lambda s: int(s, 16)})
        assert_array_equal(data, [33, 66])

    def test_dtype_with_object(self):
        # Test using an explicit dtype with an object
        data = """ 1; 2001-01-01
                   2; 2002-01-31 """
        ndtype = [('idx', int), ('code', object)]
        func = lambda s: strptime(s.strip(), "%Y-%m-%d")
        converters = {1: func}
        test = np.loadtxt(TextIO(data), delimiter=";", dtype=ndtype,
                          converters=converters)
        control = np.array(
            [(1, datetime(2001, 1, 1)), (2, datetime(2002, 1, 31))],
            dtype=ndtype)
        assert_equal(test, control)

    def test_uint64_type(self):
        tgt = (9223372043271415339, 9223372043271415853)
        c = TextIO()
        c.write("%s %s" % tgt)
        c.seek(0)
        res = np.loadtxt(c, dtype=np.uint64)
        assert_equal(res, tgt)

    def test_int64_type(self):
        tgt = (-9223372036854775807, 9223372036854775807)
        c = TextIO()
        c.write("%s %s" % tgt)
        c.seek(0)
        res = np.loadtxt(c, dtype=np.int64)
        assert_equal(res, tgt)

    def test_from_float_hex(self):
        # IEEE doubles and floats only, otherwise the float32
        # conversion may fail.
        tgt = np.logspace(-10, 10, 5).astype(np.float32)
        tgt = np.hstack((tgt, -tgt)).astype(float)
        inp = '\n'.join(map(float.hex, tgt))
        c = TextIO()
        c.write(inp)
        for dt in [float, np.float32]:
            c.seek(0)
            res = np.loadtxt(
                c, dtype=dt, converters=float.fromhex, encoding="latin1")
            assert_equal(res, tgt, err_msg=f"{dt}")

    @pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                        reason="PyPy bug in error formatting")
    def test_default_float_converter_no_default_hex_conversion(self):
        """
        Ensure that fromhex is only used for values with the correct prefix and
        is not called by default. Regression test related to gh-19598.
        """
        c = TextIO("a b c")
        with pytest.raises(ValueError,
                match=".*convert string 'a' to float64 at row 0, column 1"):
            np.loadtxt(c)

    @pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                        reason="PyPy bug in error formatting")
    def test_default_float_converter_exception(self):
        """
        Ensure that the exception message raised during failed floating point
        conversion is correct. Regression test related to gh-19598.
        """
        c = TextIO("qrs tuv")  # Invalid values for default float converter
        with pytest.raises(ValueError,
                match="could not convert string 'qrs' to float64"):
            np.loadtxt(c)

    def test_from_complex(self):
        tgt = (complex(1, 1), complex(1, -1))
        c = TextIO()
        c.write("%s %s" % tgt)
        c.seek(0)
        res = np.loadtxt(c, dtype=complex)
        assert_equal(res, tgt)

    def test_complex_misformatted(self):
        # test for backward compatibility
        # some complex formats used to generate x+-yj
        a = np.zeros((2, 2), dtype=np.complex128)
        re = np.pi
        im = np.e
        a[:] = re - 1.0j * im
        c = BytesIO()
        np.savetxt(c, a, fmt='%.16e')
        c.seek(0)
        txt = c.read()
        c.seek(0)
        # misformat the sign on the imaginary part, gh 7895
        txt_bad = txt.replace(b'e+00-', b'e00+-')
        assert_(txt_bad != txt)
        c.write(txt_bad)
        c.seek(0)
        res = np.loadtxt(c, dtype=complex)
        assert_equal(res, a)

    def test_universal_newline(self):
        with temppath() as name:
            with open(name, 'w') as f:
                f.write('1 21\r3 42\r')
            data = np.loadtxt(name)
        assert_array_equal(data, [[1, 21], [3, 42]])

    def test_empty_field_after_tab(self):
        c = TextIO()
        c.write('1 \t2 \t3\tstart \n4\t5\t6\t  \n7\t8\t9.5\t')
        c.seek(0)
        dt = {'names': ('x', 'y', 'z', 'comment'),
              'formats': ('<i4', '<i4', '<f4', '|S8')}
        x = np.loadtxt(c, dtype=dt, delimiter='\t')
        a = np.array([b'start ', b'  ', b''])
        assert_array_equal(x['comment'], a)

    def test_unpack_structured(self):
        txt = TextIO("M 21 72\nF 35 58")
        dt = {'names': ('a', 'b', 'c'), 'formats': ('|S1', '<i4', '<f4')}
        a, b, c = np.loadtxt(txt, dtype=dt, unpack=True)
        assert_(a.dtype.str == '|S1')
        assert_(b.dtype.str == '<i4')
        assert_(c.dtype.str == '<f4')
        assert_array_equal(a, np.array([b'M', b'F']))
        assert_array_equal(b, np.array([21, 35]))
        assert_array_equal(c, np.array([72.,  58.]))

    def test_ndmin_keyword(self):
        c = TextIO()
        c.write('1,2,3\n4,5,6')
        c.seek(0)
        assert_raises(ValueError, np.loadtxt, c, ndmin=3)
        c.seek(0)
        assert_raises(ValueError, np.loadtxt, c, ndmin=1.5)
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',', ndmin=1)
        a = np.array([[1, 2, 3], [4, 5, 6]])
        assert_array_equal(x, a)

        d = TextIO()
        d.write('0,1,2')
        d.seek(0)
        x = np.loadtxt(d, dtype=int, delimiter=',', ndmin=2)
        assert_(x.shape == (1, 3))
        d.seek(0)
        x = np.loadtxt(d, dtype=int, delimiter=',', ndmin=1)
        assert_(x.shape == (3,))
        d.seek(0)
        x = np.loadtxt(d, dtype=int, delimiter=',', ndmin=0)
        assert_(x.shape == (3,))

        e = TextIO()
        e.write('0\n1\n2')
        e.seek(0)
        x = np.loadtxt(e, dtype=int, delimiter=',', ndmin=2)
        assert_(x.shape == (3, 1))
        e.seek(0)
        x = np.loadtxt(e, dtype=int, delimiter=',', ndmin=1)
        assert_(x.shape == (3,))
        e.seek(0)
        x = np.loadtxt(e, dtype=int, delimiter=',', ndmin=0)
        assert_(x.shape == (3,))

        # Test ndmin kw with empty file.
        with pytest.warns(UserWarning, match="input contained no data"):
            f = TextIO()
            assert_(np.loadtxt(f, ndmin=2).shape == (0, 1,))
            assert_(np.loadtxt(f, ndmin=1).shape == (0,))

    def test_generator_source(self):
        def count():
            for i in range(10):
                yield "%d" % i

        res = np.loadtxt(count())
        assert_array_equal(res, np.arange(10))

    def test_bad_line(self):
        c = TextIO()
        c.write('1 2 3\n4 5 6\n2 3')
        c.seek(0)

        # Check for exception and that exception contains line number
        assert_raises_regex(ValueError, "3", np.loadtxt, c)

    def test_none_as_string(self):
        # gh-5155, None should work as string when format demands it
        c = TextIO()
        c.write('100,foo,200\n300,None,400')
        c.seek(0)
        dt = np.dtype([('x', int), ('a', 'S10'), ('y', int)])
        np.loadtxt(c, delimiter=',', dtype=dt, comments=None)  # Should succeed

    @pytest.mark.skipif(locale.getpreferredencoding() == 'ANSI_X3.4-1968',
                        reason="Wrong preferred encoding")
    def test_binary_load(self):
        butf8 = b"5,6,7,\xc3\x95scarscar\r\n15,2,3,hello\r\n"\
                b"20,2,3,\xc3\x95scar\r\n"
        sutf8 = butf8.decode("UTF-8").replace("\r", "").splitlines()
        with temppath() as path:
            with open(path, "wb") as f:
                f.write(butf8)
            with open(path, "rb") as f:
                x = np.loadtxt(f, encoding="UTF-8", dtype=np.str_)
            assert_array_equal(x, sutf8)
            # test broken latin1 conversion people now rely on
            with open(path, "rb") as f:
                x = np.loadtxt(f, encoding="UTF-8", dtype="S")
            x = [b'5,6,7,\xc3\x95scarscar', b'15,2,3,hello', b'20,2,3,\xc3\x95scar']
            assert_array_equal(x, np.array(x, dtype="S"))

    def test_max_rows(self):
        c = TextIO()
        c.write('1,2,3,5\n4,5,7,8\n2,1,4,5')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       max_rows=1)
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

    def test_max_rows_with_skiprows(self):
        c = TextIO()
        c.write('comments\n1,2,3,5\n4,5,7,8\n2,1,4,5')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       skiprows=1, max_rows=1)
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

        c = TextIO()
        c.write('comment\n1,2,3,5\n4,5,7,8\n2,1,4,5')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       skiprows=1, max_rows=2)
        a = np.array([[1, 2, 3, 5], [4, 5, 7, 8]], int)
        assert_array_equal(x, a)

    def test_max_rows_with_read_continuation(self):
        c = TextIO()
        c.write('1,2,3,5\n4,5,7,8\n2,1,4,5')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       max_rows=2)
        a = np.array([[1, 2, 3, 5], [4, 5, 7, 8]], int)
        assert_array_equal(x, a)
        # test continuation
        x = np.loadtxt(c, dtype=int, delimiter=',')
        a = np.array([2, 1, 4, 5], int)
        assert_array_equal(x, a)

    def test_max_rows_larger(self):
        #test max_rows > num rows
        c = TextIO()
        c.write('comment\n1,2,3,5\n4,5,7,8\n2,1,4,5')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       skiprows=1, max_rows=6)
        a = np.array([[1, 2, 3, 5], [4, 5, 7, 8], [2, 1, 4, 5]], int)
        assert_array_equal(x, a)

    @pytest.mark.parametrize(["skip", "data"], [
            (1, ["ignored\n", "1,2\n", "\n", "3,4\n"]),
            # "Bad" lines that do not end in newlines:
            (1, ["ignored", "1,2", "", "3,4"]),
            (1, StringIO("ignored\n1,2\n\n3,4")),
            # Same as above, but do not skip any lines:
            (0, ["-1,0\n", "1,2\n", "\n", "3,4\n"]),
            (0, ["-1,0", "1,2", "", "3,4"]),
            (0, StringIO("-1,0\n1,2\n\n3,4"))])
    def test_max_rows_empty_lines(self, skip, data):
        with pytest.warns(UserWarning,
                    match=f"Input line 3.*max_rows={3 - skip}"):
            res = np.loadtxt(data, dtype=int, skiprows=skip, delimiter=",",
                             max_rows=3 - skip)
            assert_array_equal(res, [[-1, 0], [1, 2], [3, 4]][skip:])

        if isinstance(data, StringIO):
            data.seek(0)

        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            with pytest.raises(UserWarning):
                np.loadtxt(data, dtype=int, skiprows=skip, delimiter=",",
                           max_rows=3 - skip)

class Testfromregex:
    def test_record(self):
        c = TextIO()
        c.write('1.312 foo\n1.534 bar\n4.444 qux')
        c.seek(0)

        dt = [('num', np.float64), ('val', 'S3')]
        x = np.fromregex(c, r"([0-9.]+)\s+(...)", dt)
        a = np.array([(1.312, 'foo'), (1.534, 'bar'), (4.444, 'qux')],
                     dtype=dt)
        assert_array_equal(x, a)

    def test_record_2(self):
        c = TextIO()
        c.write('1312 foo\n1534 bar\n4444 qux')
        c.seek(0)

        dt = [('num', np.int32), ('val', 'S3')]
        x = np.fromregex(c, r"(\d+)\s+(...)", dt)
        a = np.array([(1312, 'foo'), (1534, 'bar'), (4444, 'qux')],
                     dtype=dt)
        assert_array_equal(x, a)

    def test_record_3(self):
        c = TextIO()
        c.write('1312 foo\n1534 bar\n4444 qux')
        c.seek(0)

        dt = [('num', np.float64)]
        x = np.fromregex(c, r"(\d+)\s+...", dt)
        a = np.array([(1312,), (1534,), (4444,)], dtype=dt)
        assert_array_equal(x, a)

    @pytest.mark.parametrize("path_type", [str, Path])
    def test_record_unicode(self, path_type):
        utf8 = b'\xcf\x96'
        with temppath() as str_path:
            path = path_type(str_path)
            with open(path, 'wb') as f:
                f.write(b'1.312 foo' + utf8 + b' \n1.534 bar\n4.444 qux')

            dt = [('num', np.float64), ('val', 'U4')]
            x = np.fromregex(path, r"(?u)([0-9.]+)\s+(\w+)", dt, encoding='UTF-8')
            a = np.array([(1.312, 'foo' + utf8.decode('UTF-8')), (1.534, 'bar'),
                           (4.444, 'qux')], dtype=dt)
            assert_array_equal(x, a)

            regexp = re.compile(r"([0-9.]+)\s+(\w+)", re.UNICODE)
            x = np.fromregex(path, regexp, dt, encoding='UTF-8')
            assert_array_equal(x, a)

    def test_compiled_bytes(self):
        regexp = re.compile(br'(\d)')
        c = BytesIO(b'123')
        dt = [('num', np.float64)]
        a = np.array([1, 2, 3], dtype=dt)
        x = np.fromregex(c, regexp, dt)
        assert_array_equal(x, a)

    def test_bad_dtype_not_structured(self):
        regexp = re.compile(br'(\d)')
        c = BytesIO(b'123')
        with pytest.raises(TypeError, match='structured datatype'):
            np.fromregex(c, regexp, dtype=np.float64)


#####--------------------------------------------------------------------------


class TestFromTxt(LoadTxtBase):
    loadfunc = staticmethod(np.genfromtxt)

    def test_record(self):
        # Test w/ explicit dtype
        data = TextIO('1 2\n3 4')
        test = np.genfromtxt(data, dtype=[('x', np.int32), ('y', np.int32)])
        control = np.array([(1, 2), (3, 4)], dtype=[('x', 'i4'), ('y', 'i4')])
        assert_equal(test, control)
        #
        data = TextIO('M 64.0 75.0\nF 25.0 60.0')
        descriptor = {'names': ('gender', 'age', 'weight'),
                      'formats': ('S1', 'i4', 'f4')}
        control = np.array([('M', 64.0, 75.0), ('F', 25.0, 60.0)],
                           dtype=descriptor)
        test = np.genfromtxt(data, dtype=descriptor)
        assert_equal(test, control)

    def test_array(self):
        # Test outputting a standard ndarray
        data = TextIO('1 2\n3 4')
        control = np.array([[1, 2], [3, 4]], dtype=int)
        test = np.genfromtxt(data, dtype=int)
        assert_array_equal(test, control)
        #
        data.seek(0)
        control = np.array([[1, 2], [3, 4]], dtype=float)
        test = np.loadtxt(data, dtype=float)
        assert_array_equal(test, control)

    def test_1D(self):
        # Test squeezing to 1D
        control = np.array([1, 2, 3, 4], int)
        #
        data = TextIO('1\n2\n3\n4\n')
        test = np.genfromtxt(data, dtype=int)
        assert_array_equal(test, control)
        #
        data = TextIO('1,2,3,4\n')
        test = np.genfromtxt(data, dtype=int, delimiter=',')
        assert_array_equal(test, control)

    def test_comments(self):
        # Test the stripping of comments
        control = np.array([1, 2, 3, 5], int)
        # Comment on its own line
        data = TextIO('# comment\n1,2,3,5\n')
        test = np.genfromtxt(data, dtype=int, delimiter=',', comments='#')
        assert_equal(test, control)
        # Comment at the end of a line
        data = TextIO('1,2,3,5# comment\n')
        test = np.genfromtxt(data, dtype=int, delimiter=',', comments='#')
        assert_equal(test, control)

    def test_skiprows(self):
        # Test row skipping
        control = np.array([1, 2, 3, 5], int)
        kwargs = {"dtype": int, "delimiter": ','}
        #
        data = TextIO('comment\n1,2,3,5\n')
        test = np.genfromtxt(data, skip_header=1, **kwargs)
        assert_equal(test, control)
        #
        data = TextIO('# comment\n1,2,3,5\n')
        test = np.loadtxt(data, skiprows=1, **kwargs)
        assert_equal(test, control)

    def test_skip_footer(self):
        data = [f"# {i}" for i in range(1, 6)]
        data.append("A, B, C")
        data.extend([f"{i},{i:3.1f},{i:03d}" for i in range(51)])
        data[-1] = "99,99"
        kwargs = {"delimiter": ",", "names": True, "skip_header": 5, "skip_footer": 10}
        test = np.genfromtxt(TextIO("\n".join(data)), **kwargs)
        ctrl = np.array([(f"{i:f}", f"{i:f}", f"{i:f}") for i in range(41)],
                        dtype=[(_, float) for _ in "ABC"])
        assert_equal(test, ctrl)

    def test_skip_footer_with_invalid(self):
        with suppress_warnings() as sup:
            sup.filter(ConversionWarning)
            basestr = '1 1\n2 2\n3 3\n4 4\n5  \n6  \n7  \n'
            # Footer too small to get rid of all invalid values
            assert_raises(ValueError, np.genfromtxt,
                          TextIO(basestr), skip_footer=1)
    #        except ValueError:
    #            pass
            a = np.genfromtxt(
                TextIO(basestr), skip_footer=1, invalid_raise=False)
            assert_equal(a, np.array([[1., 1.], [2., 2.], [3., 3.], [4., 4.]]))
            #
            a = np.genfromtxt(TextIO(basestr), skip_footer=3)
            assert_equal(a, np.array([[1., 1.], [2., 2.], [3., 3.], [4., 4.]]))
            #
            basestr = '1 1\n2  \n3 3\n4 4\n5  \n6 6\n7 7\n'
            a = np.genfromtxt(
                TextIO(basestr), skip_footer=1, invalid_raise=False)
            assert_equal(a, np.array([[1., 1.], [3., 3.], [4., 4.], [6., 6.]]))
            a = np.genfromtxt(
                TextIO(basestr), skip_footer=3, invalid_raise=False)
            assert_equal(a, np.array([[1., 1.], [3., 3.], [4., 4.]]))

    def test_header(self):
        # Test retrieving a header
        data = TextIO('gender age weight\nM 64.0 75.0\nF 25.0 60.0')
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(data, dtype=None, names=True,
                                 encoding='bytes')
            assert_(w[0].category is VisibleDeprecationWarning)
        control = {'gender': np.array([b'M', b'F']),
                   'age': np.array([64.0, 25.0]),
                   'weight': np.array([75.0, 60.0])}
        assert_equal(test['gender'], control['gender'])
        assert_equal(test['age'], control['age'])
        assert_equal(test['weight'], control['weight'])

    def test_auto_dtype(self):
        # Test the automatic definition of the output dtype
        data = TextIO('A 64 75.0 3+4j True\nBCD 25 60.0 5+6j False')
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(data, dtype=None, encoding='bytes')
            assert_(w[0].category is VisibleDeprecationWarning)
        control = [np.array([b'A', b'BCD']),
                   np.array([64, 25]),
                   np.array([75.0, 60.0]),
                   np.array([3 + 4j, 5 + 6j]),
                   np.array([True, False]), ]
        assert_equal(test.dtype.names, ['f0', 'f1', 'f2', 'f3', 'f4'])
        for (i, ctrl) in enumerate(control):
            assert_equal(test[f'f{i}'], ctrl)

    def test_auto_dtype_uniform(self):
        # Tests whether the output dtype can be uniformized
        data = TextIO('1 2 3 4\n5 6 7 8\n')
        test = np.genfromtxt(data, dtype=None)
        control = np.array([[1, 2, 3, 4], [5, 6, 7, 8]])
        assert_equal(test, control)

    def test_fancy_dtype(self):
        # Check that a nested dtype isn't MIA
        data = TextIO('1,2,3.0\n4,5,6.0\n')
        fancydtype = np.dtype([('x', int), ('y', [('t', int), ('s', float)])])
        test = np.genfromtxt(data, dtype=fancydtype, delimiter=',')
        control = np.array([(1, (2, 3.0)), (4, (5, 6.0))], dtype=fancydtype)
        assert_equal(test, control)

    def test_names_overwrite(self):
        # Test overwriting the names of the dtype
        descriptor = {'names': ('g', 'a', 'w'),
                      'formats': ('S1', 'i4', 'f4')}
        data = TextIO(b'M 64.0 75.0\nF 25.0 60.0')
        names = ('gender', 'age', 'weight')
        test = np.genfromtxt(data, dtype=descriptor, names=names)
        descriptor['names'] = names
        control = np.array([('M', 64.0, 75.0),
                            ('F', 25.0, 60.0)], dtype=descriptor)
        assert_equal(test, control)

    def test_bad_fname(self):
        with pytest.raises(TypeError, match='fname must be a string,'):
            np.genfromtxt(123)

    def test_commented_header(self):
        # Check that names can be retrieved even if the line is commented out.
        data = TextIO("""
#gender age weight
M   21  72.100000
F   35  58.330000
M   33  21.99
        """)
        # The # is part of the first name and should be deleted automatically.
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(data, names=True, dtype=None,
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        ctrl = np.array([('M', 21, 72.1), ('F', 35, 58.33), ('M', 33, 21.99)],
                        dtype=[('gender', '|S1'), ('age', int), ('weight', float)])
        assert_equal(test, ctrl)
        # Ditto, but we should get rid of the first element
        data = TextIO(b"""
# gender age weight
M   21  72.100000
F   35  58.330000
M   33  21.99
        """)
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(data, names=True, dtype=None,
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        assert_equal(test, ctrl)

    def test_names_and_comments_none(self):
        # Tests case when names is true but comments is None (gh-10780)
        data = TextIO('col1 col2\n 1 2\n 3 4')
        test = np.genfromtxt(data, dtype=(int, int), comments=None, names=True)
        control = np.array([(1, 2), (3, 4)], dtype=[('col1', int), ('col2', int)])
        assert_equal(test, control)

    def test_file_is_closed_on_error(self):
        # gh-13200
        with tempdir() as tmpdir:
            fpath = os.path.join(tmpdir, "test.csv")
            with open(fpath, "wb") as f:
                f.write('\N{GREEK PI SYMBOL}'.encode())

            # ResourceWarnings are emitted from a destructor, so won't be
            # detected by regular propagation to errors.
            with assert_no_warnings():
                with pytest.raises(UnicodeDecodeError):
                    np.genfromtxt(fpath, encoding="ascii")

    def test_autonames_and_usecols(self):
        # Tests names and usecols
        data = TextIO('A B C D\n aaaa 121 45 9.1')
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(data, usecols=('A', 'C', 'D'),
                                names=True, dtype=None, encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        control = np.array(('aaaa', 45, 9.1),
                           dtype=[('A', '|S4'), ('C', int), ('D', float)])
        assert_equal(test, control)

    def test_converters_with_usecols(self):
        # Test the combination user-defined converters and usecol
        data = TextIO('1,2,3,,5\n6,7,8,9,10\n')
        test = np.genfromtxt(data, dtype=int, delimiter=',',
                            converters={3: lambda s: int(s or - 999)},
                            usecols=(1, 3,))
        control = np.array([[2, -999], [7, 9]], int)
        assert_equal(test, control)

    def test_converters_with_usecols_and_names(self):
        # Tests names and usecols
        data = TextIO('A B C D\n aaaa 121 45 9.1')
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(data, usecols=('A', 'C', 'D'), names=True,
                                dtype=None, encoding="bytes",
                                converters={'C': lambda s: 2 * int(s)})
            assert_(w[0].category is VisibleDeprecationWarning)
        control = np.array(('aaaa', 90, 9.1),
                           dtype=[('A', '|S4'), ('C', int), ('D', float)])
        assert_equal(test, control)

    def test_converters_cornercases(self):
        # Test the conversion to datetime.
        converter = {
            'date': lambda s: strptime(s, '%Y-%m-%d %H:%M:%SZ')}
        data = TextIO('2009-02-03 12:00:00Z, 72214.0')
        test = np.genfromtxt(data, delimiter=',', dtype=None,
                            names=['date', 'stid'], converters=converter)
        control = np.array((datetime(2009, 2, 3), 72214.),
                           dtype=[('date', np.object_), ('stid', float)])
        assert_equal(test, control)

    def test_converters_cornercases2(self):
        # Test the conversion to datetime64.
        converter = {
            'date': lambda s: np.datetime64(strptime(s, '%Y-%m-%d %H:%M:%SZ'))}
        data = TextIO('2009-02-03 12:00:00Z, 72214.0')
        test = np.genfromtxt(data, delimiter=',', dtype=None,
                            names=['date', 'stid'], converters=converter)
        control = np.array((datetime(2009, 2, 3), 72214.),
                           dtype=[('date', 'datetime64[us]'), ('stid', float)])
        assert_equal(test, control)

    def test_unused_converter(self):
        # Test whether unused converters are forgotten
        data = TextIO("1 21\n  3 42\n")
        test = np.genfromtxt(data, usecols=(1,),
                            converters={0: lambda s: int(s, 16)})
        assert_equal(test, [21, 42])
        #
        data.seek(0)
        test = np.genfromtxt(data, usecols=(1,),
                            converters={1: lambda s: int(s, 16)})
        assert_equal(test, [33, 66])

    def test_invalid_converter(self):
        strip_rand = lambda x: float((b'r' in x.lower() and x.split()[-1]) or
                                     ((b'r' not in x.lower() and x.strip()) or 0.0))
        strip_per = lambda x: float((b'%' in x.lower() and x.split()[0]) or
                                    ((b'%' not in x.lower() and x.strip()) or 0.0))
        s = TextIO("D01N01,10/1/2003 ,1 %,R 75,400,600\r\n"
                   "L24U05,12/5/2003, 2 %,1,300, 150.5\r\n"
                   "D02N03,10/10/2004,R 1,,7,145.55")
        kwargs = {
            "converters": {2: strip_per, 3: strip_rand}, "delimiter": ",",
            "dtype": None, "encoding": "bytes"}
        assert_raises(ConverterError, np.genfromtxt, s, **kwargs)

    def test_tricky_converter_bug1666(self):
        # Test some corner cases
        s = TextIO('q1,2\nq3,4')
        cnv = lambda s: float(s[1:])
        test = np.genfromtxt(s, delimiter=',', converters={0: cnv})
        control = np.array([[1., 2.], [3., 4.]])
        assert_equal(test, control)

    def test_dtype_with_converters(self):
        dstr = "2009; 23; 46"
        test = np.genfromtxt(TextIO(dstr,),
                            delimiter=";", dtype=float, converters={0: bytes})
        control = np.array([('2009', 23., 46)],
                           dtype=[('f0', '|S4'), ('f1', float), ('f2', float)])
        assert_equal(test, control)
        test = np.genfromtxt(TextIO(dstr,),
                            delimiter=";", dtype=float, converters={0: float})
        control = np.array([2009., 23., 46],)
        assert_equal(test, control)

    @pytest.mark.filterwarnings("ignore:.*recfromcsv.*:DeprecationWarning")
    def test_dtype_with_converters_and_usecols(self):
        dstr = "1,5,-1,1:1\n2,8,-1,1:n\n3,3,-2,m:n\n"
        dmap = {'1:1': 0, '1:n': 1, 'm:1': 2, 'm:n': 3}
        dtyp = [('e1', 'i4'), ('e2', 'i4'), ('e3', 'i2'), ('n', 'i1')]
        conv = {0: int, 1: int, 2: int, 3: lambda r: dmap[r.decode()]}
        test = recfromcsv(TextIO(dstr,), dtype=dtyp, delimiter=',',
                          names=None, converters=conv, encoding="bytes")
        control = np.rec.array([(1, 5, -1, 0), (2, 8, -1, 1), (3, 3, -2, 3)], dtype=dtyp)
        assert_equal(test, control)
        dtyp = [('e1', 'i4'), ('e2', 'i4'), ('n', 'i1')]
        test = recfromcsv(TextIO(dstr,), dtype=dtyp, delimiter=',',
                          usecols=(0, 1, 3), names=None, converters=conv,
                          encoding="bytes")
        control = np.rec.array([(1, 5, 0), (2, 8, 1), (3, 3, 3)], dtype=dtyp)
        assert_equal(test, control)

    def test_dtype_with_object(self):
        # Test using an explicit dtype with an object
        data = """ 1; 2001-01-01
                   2; 2002-01-31 """
        ndtype = [('idx', int), ('code', object)]
        func = lambda s: strptime(s.strip(), "%Y-%m-%d")
        converters = {1: func}
        test = np.genfromtxt(TextIO(data), delimiter=";", dtype=ndtype,
                             converters=converters)
        control = np.array(
            [(1, datetime(2001, 1, 1)), (2, datetime(2002, 1, 31))],
            dtype=ndtype)
        assert_equal(test, control)

        ndtype = [('nest', [('idx', int), ('code', object)])]
        with assert_raises_regex(NotImplementedError,
                                 'Nested fields.* not supported.*'):
            test = np.genfromtxt(TextIO(data), delimiter=";",
                                 dtype=ndtype, converters=converters)

        # nested but empty fields also aren't supported
        ndtype = [('idx', int), ('code', object), ('nest', [])]
        with assert_raises_regex(NotImplementedError,
                                 'Nested fields.* not supported.*'):
            test = np.genfromtxt(TextIO(data), delimiter=";",
                                 dtype=ndtype, converters=converters)

    def test_dtype_with_object_no_converter(self):
        # Object without a converter uses bytes:
        parsed = np.genfromtxt(TextIO("1"), dtype=object)
        assert parsed[()] == b"1"
        parsed = np.genfromtxt(TextIO("string"), dtype=object)
        assert parsed[()] == b"string"

    def test_userconverters_with_explicit_dtype(self):
        # Test user_converters w/ explicit (standard) dtype
        data = TextIO('skip,skip,2001-01-01,1.0,skip')
        test = np.genfromtxt(data, delimiter=",", names=None, dtype=float,
                             usecols=(2, 3), converters={2: bytes})
        control = np.array([('2001-01-01', 1.)],
                           dtype=[('', '|S10'), ('', float)])
        assert_equal(test, control)

    def test_utf8_userconverters_with_explicit_dtype(self):
        utf8 = b'\xcf\x96'
        with temppath() as path:
            with open(path, 'wb') as f:
                f.write(b'skip,skip,2001-01-01' + utf8 + b',1.0,skip')
            test = np.genfromtxt(path, delimiter=",", names=None, dtype=float,
                                 usecols=(2, 3), converters={2: str},
                                 encoding='UTF-8')
        control = np.array([('2001-01-01' + utf8.decode('UTF-8'), 1.)],
                           dtype=[('', '|U11'), ('', float)])
        assert_equal(test, control)

    def test_spacedelimiter(self):
        # Test space delimiter
        data = TextIO("1  2  3  4   5\n6  7  8  9  10")
        test = np.genfromtxt(data)
        control = np.array([[1., 2., 3., 4., 5.],
                            [6., 7., 8., 9., 10.]])
        assert_equal(test, control)

    def test_integer_delimiter(self):
        # Test using an integer for delimiter
        data = "  1  2  3\n  4  5 67\n890123  4"
        test = np.genfromtxt(TextIO(data), delimiter=3)
        control = np.array([[1, 2, 3], [4, 5, 67], [890, 123, 4]])
        assert_equal(test, control)

    def test_missing(self):
        data = TextIO('1,2,3,,5\n')
        test = np.genfromtxt(data, dtype=int, delimiter=',',
                            converters={3: lambda s: int(s or - 999)})
        control = np.array([1, 2, 3, -999, 5], int)
        assert_equal(test, control)

    def test_missing_with_tabs(self):
        # Test w/ a delimiter tab
        txt = "1\t2\t3\n\t2\t\n1\t\t3"
        test = np.genfromtxt(TextIO(txt), delimiter="\t",
                             usemask=True,)
        ctrl_d = np.array([(1, 2, 3), (np.nan, 2, np.nan), (1, np.nan, 3)],)
        ctrl_m = np.array([(0, 0, 0), (1, 0, 1), (0, 1, 0)], dtype=bool)
        assert_equal(test.data, ctrl_d)
        assert_equal(test.mask, ctrl_m)

    def test_usecols(self):
        # Test the selection of columns
        # Select 1 column
        control = np.array([[1, 2], [3, 4]], float)
        data = TextIO()
        np.savetxt(data, control)
        data.seek(0)
        test = np.genfromtxt(data, dtype=float, usecols=(1,))
        assert_equal(test, control[:, 1])
        #
        control = np.array([[1, 2, 3], [3, 4, 5]], float)
        data = TextIO()
        np.savetxt(data, control)
        data.seek(0)
        test = np.genfromtxt(data, dtype=float, usecols=(1, 2))
        assert_equal(test, control[:, 1:])
        # Testing with arrays instead of tuples.
        data.seek(0)
        test = np.genfromtxt(data, dtype=float, usecols=np.array([1, 2]))
        assert_equal(test, control[:, 1:])

    def test_usecols_as_css(self):
        # Test giving usecols with a comma-separated string
        data = "1 2 3\n4 5 6"
        test = np.genfromtxt(TextIO(data),
                             names="a, b, c", usecols="a, c")
        ctrl = np.array([(1, 3), (4, 6)], dtype=[(_, float) for _ in "ac"])
        assert_equal(test, ctrl)

    def test_usecols_with_structured_dtype(self):
        # Test usecols with an explicit structured dtype
        data = TextIO("JOE 70.1 25.3\nBOB 60.5 27.9")
        names = ['stid', 'temp']
        dtypes = ['S4', 'f8']
        test = np.genfromtxt(
            data, usecols=(0, 2), dtype=list(zip(names, dtypes)))
        assert_equal(test['stid'], [b"JOE", b"BOB"])
        assert_equal(test['temp'], [25.3, 27.9])

    def test_usecols_with_integer(self):
        # Test usecols with an integer
        test = np.genfromtxt(TextIO(b"1 2 3\n4 5 6"), usecols=0)
        assert_equal(test, np.array([1., 4.]))

    def test_usecols_with_named_columns(self):
        # Test usecols with named columns
        ctrl = np.array([(1, 3), (4, 6)], dtype=[('a', float), ('c', float)])
        data = "1 2 3\n4 5 6"
        kwargs = {"names": "a, b, c"}
        test = np.genfromtxt(TextIO(data), usecols=(0, -1), **kwargs)
        assert_equal(test, ctrl)
        test = np.genfromtxt(TextIO(data),
                             usecols=('a', 'c'), **kwargs)
        assert_equal(test, ctrl)

    def test_empty_file(self):
        # Test that an empty file raises the proper warning.
        with suppress_warnings() as sup:
            sup.filter(message="genfromtxt: Empty input file:")
            data = TextIO()
            test = np.genfromtxt(data)
            assert_equal(test, np.array([]))

            # when skip_header > 0
            test = np.genfromtxt(data, skip_header=1)
            assert_equal(test, np.array([]))

    def test_fancy_dtype_alt(self):
        # Check that a nested dtype isn't MIA
        data = TextIO('1,2,3.0\n4,5,6.0\n')
        fancydtype = np.dtype([('x', int), ('y', [('t', int), ('s', float)])])
        test = np.genfromtxt(data, dtype=fancydtype, delimiter=',', usemask=True)
        control = ma.array([(1, (2, 3.0)), (4, (5, 6.0))], dtype=fancydtype)
        assert_equal(test, control)

    def test_shaped_dtype(self):
        c = TextIO("aaaa  1.0  8.0  1 2 3 4 5 6")
        dt = np.dtype([('name', 'S4'), ('x', float), ('y', float),
                       ('block', int, (2, 3))])
        x = np.genfromtxt(c, dtype=dt)
        a = np.array([('aaaa', 1.0, 8.0, [[1, 2, 3], [4, 5, 6]])],
                     dtype=dt)
        assert_array_equal(x, a)

    def test_withmissing(self):
        data = TextIO('A,B\n0,1\n2,N/A')
        kwargs = {"delimiter": ",", "missing_values": "N/A", "names": True}
        test = np.genfromtxt(data, dtype=None, usemask=True, **kwargs)
        control = ma.array([(0, 1), (2, -1)],
                           mask=[(False, False), (False, True)],
                           dtype=[('A', int), ('B', int)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)
        #
        data.seek(0)
        test = np.genfromtxt(data, usemask=True, **kwargs)
        control = ma.array([(0, 1), (2, -1)],
                           mask=[(False, False), (False, True)],
                           dtype=[('A', float), ('B', float)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)

    def test_user_missing_values(self):
        data = "A, B, C\n0, 0., 0j\n1, N/A, 1j\n-9, 2.2, N/A\n3, -99, 3j"
        basekwargs = {"dtype": None, "delimiter": ",", "names": True}
        mdtype = [('A', int), ('B', float), ('C', complex)]
        #
        test = np.genfromtxt(TextIO(data), missing_values="N/A",
                            **basekwargs)
        control = ma.array([(0, 0.0, 0j), (1, -999, 1j),
                            (-9, 2.2, -999j), (3, -99, 3j)],
                           mask=[(0, 0, 0), (0, 1, 0), (0, 0, 1), (0, 0, 0)],
                           dtype=mdtype)
        assert_equal(test, control)
        #
        basekwargs['dtype'] = mdtype
        test = np.genfromtxt(TextIO(data),
                            missing_values={0: -9, 1: -99, 2: -999j}, usemask=True, **basekwargs)
        control = ma.array([(0, 0.0, 0j), (1, -999, 1j),
                            (-9, 2.2, -999j), (3, -99, 3j)],
                           mask=[(0, 0, 0), (0, 1, 0), (1, 0, 1), (0, 1, 0)],
                           dtype=mdtype)
        assert_equal(test, control)
        #
        test = np.genfromtxt(TextIO(data),
                            missing_values={0: -9, 'B': -99, 'C': -999j},
                            usemask=True,
                            **basekwargs)
        control = ma.array([(0, 0.0, 0j), (1, -999, 1j),
                            (-9, 2.2, -999j), (3, -99, 3j)],
                           mask=[(0, 0, 0), (0, 1, 0), (1, 0, 1), (0, 1, 0)],
                           dtype=mdtype)
        assert_equal(test, control)

    def test_user_filling_values(self):
        # Test with missing and filling values
        ctrl = np.array([(0, 3), (4, -999)], dtype=[('a', int), ('b', int)])
        data = "N/A, 2, 3\n4, ,???"
        kwargs = {"delimiter": ",",
                      "dtype": int,
                      "names": "a,b,c",
                      "missing_values": {0: "N/A", 'b': " ", 2: "???"},
                      "filling_values": {0: 0, 'b': 0, 2: -999}}
        test = np.genfromtxt(TextIO(data), **kwargs)
        ctrl = np.array([(0, 2, 3), (4, 0, -999)],
                        dtype=[(_, int) for _ in "abc"])
        assert_equal(test, ctrl)
        #
        test = np.genfromtxt(TextIO(data), usecols=(0, -1), **kwargs)
        ctrl = np.array([(0, 3), (4, -999)], dtype=[(_, int) for _ in "ac"])
        assert_equal(test, ctrl)

        data2 = "1,2,*,4\n5,*,7,8\n"
        test = np.genfromtxt(TextIO(data2), delimiter=',', dtype=int,
                             missing_values="*", filling_values=0)
        ctrl = np.array([[1, 2, 0, 4], [5, 0, 7, 8]])
        assert_equal(test, ctrl)
        test = np.genfromtxt(TextIO(data2), delimiter=',', dtype=int,
                             missing_values="*", filling_values=-1)
        ctrl = np.array([[1, 2, -1, 4], [5, -1, 7, 8]])
        assert_equal(test, ctrl)

    def test_withmissing_float(self):
        data = TextIO('A,B\n0,1.5\n2,-999.00')
        test = np.genfromtxt(data, dtype=None, delimiter=',',
                            missing_values='-999.0', names=True, usemask=True)
        control = ma.array([(0, 1.5), (2, -1.)],
                           mask=[(False, False), (False, True)],
                           dtype=[('A', int), ('B', float)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)

    def test_with_masked_column_uniform(self):
        # Test masked column
        data = TextIO('1 2 3\n4 5 6\n')
        test = np.genfromtxt(data, dtype=None,
                             missing_values='2,5', usemask=True)
        control = ma.array([[1, 2, 3], [4, 5, 6]], mask=[[0, 1, 0], [0, 1, 0]])
        assert_equal(test, control)

    def test_with_masked_column_various(self):
        # Test masked column
        data = TextIO('True 2 3\nFalse 5 6\n')
        test = np.genfromtxt(data, dtype=None,
                             missing_values='2,5', usemask=True)
        control = ma.array([(1, 2, 3), (0, 5, 6)],
                           mask=[(0, 1, 0), (0, 1, 0)],
                           dtype=[('f0', bool), ('f1', bool), ('f2', int)])
        assert_equal(test, control)

    def test_invalid_raise(self):
        # Test invalid raise
        data = ["1, 1, 1, 1, 1"] * 50
        for i in range(5):
            data[10 * i] = "2, 2, 2, 2 2"
        data.insert(0, "a, b, c, d, e")
        mdata = TextIO("\n".join(data))

        kwargs = {"delimiter": ",", "dtype": None, "names": True}

        def f():
            return np.genfromtxt(mdata, invalid_raise=False, **kwargs)
        mtest = assert_warns(ConversionWarning, f)
        assert_equal(len(mtest), 45)
        assert_equal(mtest, np.ones(45, dtype=[(_, int) for _ in 'abcde']))
        #
        mdata.seek(0)
        assert_raises(ValueError, np.genfromtxt, mdata,
                      delimiter=",", names=True)

    def test_invalid_raise_with_usecols(self):
        # Test invalid_raise with usecols
        data = ["1, 1, 1, 1, 1"] * 50
        for i in range(5):
            data[10 * i] = "2, 2, 2, 2 2"
        data.insert(0, "a, b, c, d, e")
        mdata = TextIO("\n".join(data))

        kwargs = {"delimiter": ",", "dtype": None, "names": True,
                      "invalid_raise": False}

        def f():
            return np.genfromtxt(mdata, usecols=(0, 4), **kwargs)
        mtest = assert_warns(ConversionWarning, f)
        assert_equal(len(mtest), 45)
        assert_equal(mtest, np.ones(45, dtype=[(_, int) for _ in 'ae']))
        #
        mdata.seek(0)
        mtest = np.genfromtxt(mdata, usecols=(0, 1), **kwargs)
        assert_equal(len(mtest), 50)
        control = np.ones(50, dtype=[(_, int) for _ in 'ab'])
        control[[10 * _ for _ in range(5)]] = (2, 2)
        assert_equal(mtest, control)

    def test_inconsistent_dtype(self):
        # Test inconsistent dtype
        data = ["1, 1, 1, 1, -1.1"] * 50
        mdata = TextIO("\n".join(data))

        converters = {4: lambda x: f"({x.decode()})"}
        kwargs = {"delimiter": ",", "converters": converters,
                      "dtype": [(_, int) for _ in 'abcde'], "encoding": "bytes"}
        assert_raises(ValueError, np.genfromtxt, mdata, **kwargs)

    def test_default_field_format(self):
        # Test default format
        data = "0, 1, 2.3\n4, 5, 6.7"
        mtest = np.genfromtxt(TextIO(data),
                             delimiter=",", dtype=None, defaultfmt="f%02i")
        ctrl = np.array([(0, 1, 2.3), (4, 5, 6.7)],
                        dtype=[("f00", int), ("f01", int), ("f02", float)])
        assert_equal(mtest, ctrl)

    def test_single_dtype_wo_names(self):
        # Test single dtype w/o names
        data = "0, 1, 2.3\n4, 5, 6.7"
        mtest = np.genfromtxt(TextIO(data),
                             delimiter=",", dtype=float, defaultfmt="f%02i")
        ctrl = np.array([[0., 1., 2.3], [4., 5., 6.7]], dtype=float)
        assert_equal(mtest, ctrl)

    def test_single_dtype_w_explicit_names(self):
        # Test single dtype w explicit names
        data = "0, 1, 2.3\n4, 5, 6.7"
        mtest = np.genfromtxt(TextIO(data),
                             delimiter=",", dtype=float, names="a, b, c")
        ctrl = np.array([(0., 1., 2.3), (4., 5., 6.7)],
                        dtype=[(_, float) for _ in "abc"])
        assert_equal(mtest, ctrl)

    def test_single_dtype_w_implicit_names(self):
        # Test single dtype w implicit names
        data = "a, b, c\n0, 1, 2.3\n4, 5, 6.7"
        mtest = np.genfromtxt(TextIO(data),
                             delimiter=",", dtype=float, names=True)
        ctrl = np.array([(0., 1., 2.3), (4., 5., 6.7)],
                        dtype=[(_, float) for _ in "abc"])
        assert_equal(mtest, ctrl)

    def test_easy_structured_dtype(self):
        # Test easy structured dtype
        data = "0, 1, 2.3\n4, 5, 6.7"
        mtest = np.genfromtxt(TextIO(data), delimiter=",",
                             dtype=(int, float, float), defaultfmt="f_%02i")
        ctrl = np.array([(0, 1., 2.3), (4, 5., 6.7)],
                        dtype=[("f_00", int), ("f_01", float), ("f_02", float)])
        assert_equal(mtest, ctrl)

    def test_autostrip(self):
        # Test autostrip
        data = "01/01/2003  , 1.3,   abcde"
        kwargs = {"delimiter": ",", "dtype": None, "encoding": "bytes"}
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            mtest = np.genfromtxt(TextIO(data), **kwargs)
            assert_(w[0].category is VisibleDeprecationWarning)
        ctrl = np.array([('01/01/2003  ', 1.3, '   abcde')],
                        dtype=[('f0', '|S12'), ('f1', float), ('f2', '|S8')])
        assert_equal(mtest, ctrl)
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            mtest = np.genfromtxt(TextIO(data), autostrip=True, **kwargs)
            assert_(w[0].category is VisibleDeprecationWarning)
        ctrl = np.array([('01/01/2003', 1.3, 'abcde')],
                        dtype=[('f0', '|S10'), ('f1', float), ('f2', '|S5')])
        assert_equal(mtest, ctrl)

    def test_replace_space(self):
        # Test the 'replace_space' option
        txt = "A.A, B (B), C:C\n1, 2, 3.14"
        # Test default: replace ' ' by '_' and delete non-alphanum chars
        test = np.genfromtxt(TextIO(txt),
                             delimiter=",", names=True, dtype=None)
        ctrl_dtype = [("AA", int), ("B_B", int), ("CC", float)]
        ctrl = np.array((1, 2, 3.14), dtype=ctrl_dtype)
        assert_equal(test, ctrl)
        # Test: no replace, no delete
        test = np.genfromtxt(TextIO(txt),
                             delimiter=",", names=True, dtype=None,
                             replace_space='', deletechars='')
        ctrl_dtype = [("A.A", int), ("B (B)", int), ("C:C", float)]
        ctrl = np.array((1, 2, 3.14), dtype=ctrl_dtype)
        assert_equal(test, ctrl)
        # Test: no delete (spaces are replaced by _)
        test = np.genfromtxt(TextIO(txt),
                             delimiter=",", names=True, dtype=None,
                             deletechars='')
        ctrl_dtype = [("A.A", int), ("B_(B)", int), ("C:C", float)]
        ctrl = np.array((1, 2, 3.14), dtype=ctrl_dtype)
        assert_equal(test, ctrl)

    def test_replace_space_known_dtype(self):
        # Test the 'replace_space' (and related) options when dtype != None
        txt = "A.A, B (B), C:C\n1, 2, 3"
        # Test default: replace ' ' by '_' and delete non-alphanum chars
        test = np.genfromtxt(TextIO(txt),
                             delimiter=",", names=True, dtype=int)
        ctrl_dtype = [("AA", int), ("B_B", int), ("CC", int)]
        ctrl = np.array((1, 2, 3), dtype=ctrl_dtype)
        assert_equal(test, ctrl)
        # Test: no replace, no delete
        test = np.genfromtxt(TextIO(txt),
                             delimiter=",", names=True, dtype=int,
                             replace_space='', deletechars='')
        ctrl_dtype = [("A.A", int), ("B (B)", int), ("C:C", int)]
        ctrl = np.array((1, 2, 3), dtype=ctrl_dtype)
        assert_equal(test, ctrl)
        # Test: no delete (spaces are replaced by _)
        test = np.genfromtxt(TextIO(txt),
                             delimiter=",", names=True, dtype=int,
                             deletechars='')
        ctrl_dtype = [("A.A", int), ("B_(B)", int), ("C:C", int)]
        ctrl = np.array((1, 2, 3), dtype=ctrl_dtype)
        assert_equal(test, ctrl)

    def test_incomplete_names(self):
        # Test w/ incomplete names
        data = "A,,C\n0,1,2\n3,4,5"
        kwargs = {"delimiter": ",", "names": True}
        # w/ dtype=None
        ctrl = np.array([(0, 1, 2), (3, 4, 5)],
                        dtype=[(_, int) for _ in ('A', 'f0', 'C')])
        test = np.genfromtxt(TextIO(data), dtype=None, **kwargs)
        assert_equal(test, ctrl)
        # w/ default dtype
        ctrl = np.array([(0, 1, 2), (3, 4, 5)],
                        dtype=[(_, float) for _ in ('A', 'f0', 'C')])
        test = np.genfromtxt(TextIO(data), **kwargs)

    def test_names_auto_completion(self):
        # Make sure that names are properly completed
        data = "1 2 3\n 4 5 6"
        test = np.genfromtxt(TextIO(data),
                             dtype=(int, float, int), names="a")
        ctrl = np.array([(1, 2, 3), (4, 5, 6)],
                        dtype=[('a', int), ('f0', float), ('f1', int)])
        assert_equal(test, ctrl)

    def test_names_with_usecols_bug1636(self):
        # Make sure we pick up the right names w/ usecols
        data = "A,B,C,D,E\n0,1,2,3,4\n0,1,2,3,4\n0,1,2,3,4"
        ctrl_names = ("A", "C", "E")
        test = np.genfromtxt(TextIO(data),
                             dtype=(int, int, int), delimiter=",",
                             usecols=(0, 2, 4), names=True)
        assert_equal(test.dtype.names, ctrl_names)
        #
        test = np.genfromtxt(TextIO(data),
                             dtype=(int, int, int), delimiter=",",
                             usecols=("A", "C", "E"), names=True)
        assert_equal(test.dtype.names, ctrl_names)
        #
        test = np.genfromtxt(TextIO(data),
                             dtype=int, delimiter=",",
                             usecols=("A", "C", "E"), names=True)
        assert_equal(test.dtype.names, ctrl_names)

    def test_fixed_width_names(self):
        # Test fix-width w/ names
        data = "    A    B   C\n    0    1 2.3\n   45   67   9."
        kwargs = {"delimiter": (5, 5, 4), "names": True, "dtype": None}
        ctrl = np.array([(0, 1, 2.3), (45, 67, 9.)],
                        dtype=[('A', int), ('B', int), ('C', float)])
        test = np.genfromtxt(TextIO(data), **kwargs)
        assert_equal(test, ctrl)
        #
        kwargs = {"delimiter": 5, "names": True, "dtype": None}
        ctrl = np.array([(0, 1, 2.3), (45, 67, 9.)],
                        dtype=[('A', int), ('B', int), ('C', float)])
        test = np.genfromtxt(TextIO(data), **kwargs)
        assert_equal(test, ctrl)

    def test_filling_values(self):
        # Test missing values
        data = b"1, 2, 3\n1, , 5\n0, 6, \n"
        kwargs = {"delimiter": ",", "dtype": None, "filling_values": -999}
        ctrl = np.array([[1, 2, 3], [1, -999, 5], [0, 6, -999]], dtype=int)
        test = np.genfromtxt(TextIO(data), **kwargs)
        assert_equal(test, ctrl)

    def test_comments_is_none(self):
        # Github issue 329 (None was previously being converted to 'None').
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(TextIO("test1,testNonetherestofthedata"),
                                 dtype=None, comments=None, delimiter=',',
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        assert_equal(test[1], b'testNonetherestofthedata')
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(TextIO("test1, testNonetherestofthedata"),
                                 dtype=None, comments=None, delimiter=',',
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        assert_equal(test[1], b' testNonetherestofthedata')

    def test_latin1(self):
        latin1 = b'\xf6\xfc\xf6'
        norm = b"norm1,norm2,norm3\n"
        enc = b"test1,testNonethe" + latin1 + b",test3\n"
        s = norm + enc + norm
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(TextIO(s),
                                 dtype=None, comments=None, delimiter=',',
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        assert_equal(test[1, 0], b"test1")
        assert_equal(test[1, 1], b"testNonethe" + latin1)
        assert_equal(test[1, 2], b"test3")
        test = np.genfromtxt(TextIO(s),
                             dtype=None, comments=None, delimiter=',',
                             encoding='latin1')
        assert_equal(test[1, 0], "test1")
        assert_equal(test[1, 1], "testNonethe" + latin1.decode('latin1'))
        assert_equal(test[1, 2], "test3")

        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(TextIO(b"0,testNonethe" + latin1),
                                 dtype=None, comments=None, delimiter=',',
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        assert_equal(test['f0'], 0)
        assert_equal(test['f1'], b"testNonethe" + latin1)

    def test_binary_decode_autodtype(self):
        utf16 = b'\xff\xfeh\x04 \x00i\x04 \x00j\x04'
        v = self.loadfunc(BytesIO(utf16), dtype=None, encoding='UTF-16')
        assert_array_equal(v, np.array(utf16.decode('UTF-16').split()))

    def test_utf8_byte_encoding(self):
        utf8 = b"\xcf\x96"
        norm = b"norm1,norm2,norm3\n"
        enc = b"test1,testNonethe" + utf8 + b",test3\n"
        s = norm + enc + norm
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(TextIO(s),
                                 dtype=None, comments=None, delimiter=',',
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        ctl = np.array([
                 [b'norm1', b'norm2', b'norm3'],
                 [b'test1', b'testNonethe' + utf8, b'test3'],
                 [b'norm1', b'norm2', b'norm3']])
        assert_array_equal(test, ctl)

    def test_utf8_file(self):
        utf8 = b"\xcf\x96"
        with temppath() as path:
            with open(path, "wb") as f:
                f.write((b"test1,testNonethe" + utf8 + b",test3\n") * 2)
            test = np.genfromtxt(path, dtype=None, comments=None,
                                 delimiter=',', encoding="UTF-8")
            ctl = np.array([
                     ["test1", "testNonethe" + utf8.decode("UTF-8"), "test3"],
                     ["test1", "testNonethe" + utf8.decode("UTF-8"), "test3"]],
                     dtype=np.str_)
            assert_array_equal(test, ctl)

            # test a mixed dtype
            with open(path, "wb") as f:
                f.write(b"0,testNonethe" + utf8)
            test = np.genfromtxt(path, dtype=None, comments=None,
                                 delimiter=',', encoding="UTF-8")
            assert_equal(test['f0'], 0)
            assert_equal(test['f1'], "testNonethe" + utf8.decode("UTF-8"))

    def test_utf8_file_nodtype_unicode(self):
        # bytes encoding with non-latin1 -> unicode upcast
        utf8 = '\u03d6'
        latin1 = '\xf6\xfc\xf6'

        # skip test if cannot encode utf8 test string with preferred
        # encoding. The preferred encoding is assumed to be the default
        # encoding of open. Will need to change this for PyTest, maybe
        # using pytest.mark.xfail(raises=***).
        try:
            encoding = locale.getpreferredencoding()
            utf8.encode(encoding)
        except (UnicodeError, ImportError):
            pytest.skip('Skipping test_utf8_file_nodtype_unicode, '
                        'unable to encode utf8 in preferred encoding')

        with temppath() as path:
            with open(path, "wt") as f:
                f.write("norm1,norm2,norm3\n")
                f.write("norm1," + latin1 + ",norm3\n")
                f.write("test1,testNonethe" + utf8 + ",test3\n")
            with warnings.catch_warnings(record=True) as w:
                warnings.filterwarnings('always', '',
                                        VisibleDeprecationWarning)
                test = np.genfromtxt(path, dtype=None, comments=None,
                                     delimiter=',', encoding="bytes")
                # Check for warning when encoding not specified.
                assert_(w[0].category is VisibleDeprecationWarning)
            ctl = np.array([
                     ["norm1", "norm2", "norm3"],
                     ["norm1", latin1, "norm3"],
                     ["test1", "testNonethe" + utf8, "test3"]],
                     dtype=np.str_)
            assert_array_equal(test, ctl)

    @pytest.mark.filterwarnings("ignore:.*recfromtxt.*:DeprecationWarning")
    def test_recfromtxt(self):
        #
        data = TextIO('A,B\n0,1\n2,3')
        kwargs = {"delimiter": ",", "missing_values": "N/A", "names": True}
        test = recfromtxt(data, **kwargs)
        control = np.array([(0, 1), (2, 3)],
                           dtype=[('A', int), ('B', int)])
        assert_(isinstance(test, np.recarray))
        assert_equal(test, control)
        #
        data = TextIO('A,B\n0,1\n2,N/A')
        test = recfromtxt(data, dtype=None, usemask=True, **kwargs)
        control = ma.array([(0, 1), (2, -1)],
                           mask=[(False, False), (False, True)],
                           dtype=[('A', int), ('B', int)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)
        assert_equal(test.A, [0, 2])

    @pytest.mark.filterwarnings("ignore:.*recfromcsv.*:DeprecationWarning")
    def test_recfromcsv(self):
        #
        data = TextIO('A,B\n0,1\n2,3')
        kwargs = {"missing_values": "N/A", "names": True, "case_sensitive": True,
                      "encoding": "bytes"}
        test = recfromcsv(data, dtype=None, **kwargs)
        control = np.array([(0, 1), (2, 3)],
                           dtype=[('A', int), ('B', int)])
        assert_(isinstance(test, np.recarray))
        assert_equal(test, control)
        #
        data = TextIO('A,B\n0,1\n2,N/A')
        test = recfromcsv(data, dtype=None, usemask=True, **kwargs)
        control = ma.array([(0, 1), (2, -1)],
                           mask=[(False, False), (False, True)],
                           dtype=[('A', int), ('B', int)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)
        assert_equal(test.A, [0, 2])
        #
        data = TextIO('A,B\n0,1\n2,3')
        test = recfromcsv(data, missing_values='N/A',)
        control = np.array([(0, 1), (2, 3)],
                           dtype=[('a', int), ('b', int)])
        assert_(isinstance(test, np.recarray))
        assert_equal(test, control)
        #
        data = TextIO('A,B\n0,1\n2,3')
        dtype = [('a', int), ('b', float)]
        test = recfromcsv(data, missing_values='N/A', dtype=dtype)
        control = np.array([(0, 1), (2, 3)],
                           dtype=dtype)
        assert_(isinstance(test, np.recarray))
        assert_equal(test, control)

        # gh-10394
        data = TextIO('color\n"red"\n"blue"')
        test = recfromcsv(data, converters={0: lambda x: x.strip('\"')})
        control = np.array([('red',), ('blue',)], dtype=[('color', (str, 4))])
        assert_equal(test.dtype, control.dtype)
        assert_equal(test, control)

    def test_max_rows(self):
        # Test the `max_rows` keyword argument.
        data = '1 2\n3 4\n5 6\n7 8\n9 10\n'
        txt = TextIO(data)
        a1 = np.genfromtxt(txt, max_rows=3)
        a2 = np.genfromtxt(txt)
        assert_equal(a1, [[1, 2], [3, 4], [5, 6]])
        assert_equal(a2, [[7, 8], [9, 10]])

        # max_rows must be at least 1.
        assert_raises(ValueError, np.genfromtxt, TextIO(data), max_rows=0)

        # An input with several invalid rows.
        data = '1 1\n2 2\n0 \n3 3\n4 4\n5  \n6  \n7  \n'

        test = np.genfromtxt(TextIO(data), max_rows=2)
        control = np.array([[1., 1.], [2., 2.]])
        assert_equal(test, control)

        # Test keywords conflict
        assert_raises(ValueError, np.genfromtxt, TextIO(data), skip_footer=1,
                      max_rows=4)

        # Test with invalid value
        assert_raises(ValueError, np.genfromtxt, TextIO(data), max_rows=4)

        # Test with invalid not raise
        with suppress_warnings() as sup:
            sup.filter(ConversionWarning)

            test = np.genfromtxt(TextIO(data), max_rows=4, invalid_raise=False)
            control = np.array([[1., 1.], [2., 2.], [3., 3.], [4., 4.]])
            assert_equal(test, control)

            test = np.genfromtxt(TextIO(data), max_rows=5, invalid_raise=False)
            control = np.array([[1., 1.], [2., 2.], [3., 3.], [4., 4.]])
            assert_equal(test, control)

        # Structured array with field names.
        data = 'a b\n#c d\n1 1\n2 2\n#0 \n3 3\n4 4\n5  5\n'

        # Test with header, names and comments
        txt = TextIO(data)
        test = np.genfromtxt(txt, skip_header=1, max_rows=3, names=True)
        control = np.array([(1.0, 1.0), (2.0, 2.0), (3.0, 3.0)],
                      dtype=[('c', '<f8'), ('d', '<f8')])
        assert_equal(test, control)
        # To continue reading the same "file", don't use skip_header or
        # names, and use the previously determined dtype.
        test = np.genfromtxt(txt, max_rows=None, dtype=test.dtype)
        control = np.array([(4.0, 4.0), (5.0, 5.0)],
                      dtype=[('c', '<f8'), ('d', '<f8')])
        assert_equal(test, control)

    def test_gft_using_filename(self):
        # Test that we can load data from a filename as well as a file
        # object
        tgt = np.arange(6).reshape((2, 3))
        linesep = ('\n', '\r\n', '\r')

        for sep in linesep:
            data = '0 1 2' + sep + '3 4 5'
            with temppath() as name:
                with open(name, 'w') as f:
                    f.write(data)
                res = np.genfromtxt(name)
            assert_array_equal(res, tgt)

    def test_gft_from_gzip(self):
        # Test that we can load data from a gzipped file
        wanted = np.arange(6).reshape((2, 3))
        linesep = ('\n', '\r\n', '\r')

        for sep in linesep:
            data = '0 1 2' + sep + '3 4 5'
            s = BytesIO()
            with gzip.GzipFile(fileobj=s, mode='w') as g:
                g.write(asbytes(data))

            with temppath(suffix='.gz2') as name:
                with open(name, 'w') as f:
                    f.write(data)
                assert_array_equal(np.genfromtxt(name), wanted)

    def test_gft_using_generator(self):
        # gft doesn't work with unicode.
        def count():
            for i in range(10):
                yield asbytes("%d" % i)

        res = np.genfromtxt(count())
        assert_array_equal(res, np.arange(10))

    def test_auto_dtype_largeint(self):
        # Regression test for numpy/numpy#5635 whereby large integers could
        # cause OverflowErrors.

        # Test the automatic definition of the output dtype
        #
        # 2**66 = 73786976294838206464 => should convert to float
        # 2**34 = 17179869184 => should convert to int64
        # 2**10 = 1024 => should convert to int (int32 on 32-bit systems,
        #                 int64 on 64-bit systems)

        data = TextIO('73786976294838206464 17179869184 1024')

        test = np.genfromtxt(data, dtype=None)

        assert_equal(test.dtype.names, ['f0', 'f1', 'f2'])

        assert_(test.dtype['f0'] == float)
        assert_(test.dtype['f1'] == np.int64)
        assert_(test.dtype['f2'] == np.int_)

        assert_allclose(test['f0'], 73786976294838206464.)
        assert_equal(test['f1'], 17179869184)
        assert_equal(test['f2'], 1024)

    def test_unpack_float_data(self):
        txt = TextIO("1,2,3\n4,5,6\n7,8,9\n0.0,1.0,2.0")
        a, b, c = np.loadtxt(txt, delimiter=",", unpack=True)
        assert_array_equal(a, np.array([1.0, 4.0, 7.0, 0.0]))
        assert_array_equal(b, np.array([2.0, 5.0, 8.0, 1.0]))
        assert_array_equal(c, np.array([3.0, 6.0, 9.0, 2.0]))

    def test_unpack_structured(self):
        # Regression test for gh-4341
        # Unpacking should work on structured arrays
        txt = TextIO("M 21 72\nF 35 58")
        dt = {'names': ('a', 'b', 'c'), 'formats': ('S1', 'i4', 'f4')}
        a, b, c = np.genfromtxt(txt, dtype=dt, unpack=True)
        assert_equal(a.dtype, np.dtype('S1'))
        assert_equal(b.dtype, np.dtype('i4'))
        assert_equal(c.dtype, np.dtype('f4'))
        assert_array_equal(a, np.array([b'M', b'F']))
        assert_array_equal(b, np.array([21, 35]))
        assert_array_equal(c, np.array([72.,  58.]))

    def test_unpack_auto_dtype(self):
        # Regression test for gh-4341
        # Unpacking should work when dtype=None
        txt = TextIO("M 21 72.\nF 35 58.")
        expected = (np.array(["M", "F"]), np.array([21, 35]), np.array([72., 58.]))
        test = np.genfromtxt(txt, dtype=None, unpack=True, encoding="utf-8")
        for arr, result in zip(expected, test):
            assert_array_equal(arr, result)
            assert_equal(arr.dtype, result.dtype)

    def test_unpack_single_name(self):
        # Regression test for gh-4341
        # Unpacking should work when structured dtype has only one field
        txt = TextIO("21\n35")
        dt = {'names': ('a',), 'formats': ('i4',)}
        expected = np.array([21, 35], dtype=np.int32)
        test = np.genfromtxt(txt, dtype=dt, unpack=True)
        assert_array_equal(expected, test)
        assert_equal(expected.dtype, test.dtype)

    def test_squeeze_scalar(self):
        # Regression test for gh-4341
        # Unpacking a scalar should give zero-dim output,
        # even if dtype is structured
        txt = TextIO("1")
        dt = {'names': ('a',), 'formats': ('i4',)}
        expected = np.array((1,), dtype=np.int32)
        test = np.genfromtxt(txt, dtype=dt, unpack=True)
        assert_array_equal(expected, test)
        assert_equal((), test.shape)
        assert_equal(expected.dtype, test.dtype)

    @pytest.mark.parametrize("ndim", [0, 1, 2])
    def test_ndmin_keyword(self, ndim: int):
        # lets have the same behaviour of ndmin as loadtxt
        # as they should be the same for non-missing values
        txt = "42"

        a = np.loadtxt(StringIO(txt), ndmin=ndim)
        b = np.genfromtxt(StringIO(txt), ndmin=ndim)

        assert_array_equal(a, b)


class TestPathUsage:
    # Test that pathlib.Path can be used
    def test_loadtxt(self):
        with temppath(suffix='.txt') as path:
            path = Path(path)
            a = np.array([[1.1, 2], [3, 4]])
            np.savetxt(path, a)
            x = np.loadtxt(path)
            assert_array_equal(x, a)

    def test_save_load(self):
        # Test that pathlib.Path instances can be used with save.
        with temppath(suffix='.npy') as path:
            path = Path(path)
            a = np.array([[1, 2], [3, 4]], int)
            np.save(path, a)
            data = np.load(path)
            assert_array_equal(data, a)

    def test_save_load_memmap(self):
        # Test that pathlib.Path instances can be loaded mem-mapped.
        with temppath(suffix='.npy') as path:
            path = Path(path)
            a = np.array([[1, 2], [3, 4]], int)
            np.save(path, a)
            data = np.load(path, mmap_mode='r')
            assert_array_equal(data, a)
            # close the mem-mapped file
            del data
            if IS_PYPY:
                break_cycles()
                break_cycles()

    @pytest.mark.xfail(IS_WASM, reason="memmap doesn't work correctly")
    @pytest.mark.parametrize("filename_type", [Path, str])
    def test_save_load_memmap_readwrite(self, filename_type):
        with temppath(suffix='.npy') as path:
            path = filename_type(path)
            a = np.array([[1, 2], [3, 4]], int)
            np.save(path, a)
            b = np.load(path, mmap_mode='r+')
            a[0][0] = 5
            b[0][0] = 5
            del b  # closes the file
            if IS_PYPY:
                break_cycles()
                break_cycles()
            data = np.load(path)
            assert_array_equal(data, a)

    @pytest.mark.parametrize("filename_type", [Path, str])
    def test_savez_load(self, filename_type):
        with temppath(suffix='.npz') as path:
            path = filename_type(path)
            np.savez(path, lab='place holder')
            with np.load(path) as data:
                assert_array_equal(data['lab'], 'place holder')

    @pytest.mark.parametrize("filename_type", [Path, str])
    def test_savez_compressed_load(self, filename_type):
        with temppath(suffix='.npz') as path:
            path = filename_type(path)
            np.savez_compressed(path, lab='place holder')
            data = np.load(path)
            assert_array_equal(data['lab'], 'place holder')
            data.close()

    @pytest.mark.parametrize("filename_type", [Path, str])
    def test_genfromtxt(self, filename_type):
        with temppath(suffix='.txt') as path:
            path = filename_type(path)
            a = np.array([(1, 2), (3, 4)])
            np.savetxt(path, a)
            data = np.genfromtxt(path)
            assert_array_equal(a, data)

    @pytest.mark.parametrize("filename_type", [Path, str])
    @pytest.mark.filterwarnings("ignore:.*recfromtxt.*:DeprecationWarning")
    def test_recfromtxt(self, filename_type):
        with temppath(suffix='.txt') as path:
            path = filename_type(path)
            with open(path, 'w') as f:
                f.write('A,B\n0,1\n2,3')

            kwargs = {"delimiter": ",", "missing_values": "N/A", "names": True}
            test = recfromtxt(path, **kwargs)
            control = np.array([(0, 1), (2, 3)],
                               dtype=[('A', int), ('B', int)])
            assert_(isinstance(test, np.recarray))
            assert_equal(test, control)

    @pytest.mark.parametrize("filename_type", [Path, str])
    @pytest.mark.filterwarnings("ignore:.*recfromcsv.*:DeprecationWarning")
    def test_recfromcsv(self, filename_type):
        with temppath(suffix='.txt') as path:
            path = filename_type(path)
            with open(path, 'w') as f:
                f.write('A,B\n0,1\n2,3')

            kwargs = {
                "missing_values": "N/A", "names": True, "case_sensitive": True
            }
            test = recfromcsv(path, dtype=None, **kwargs)
            control = np.array([(0, 1), (2, 3)],
                               dtype=[('A', int), ('B', int)])
            assert_(isinstance(test, np.recarray))
            assert_equal(test, control)


def test_gzip_load():
    a = np.random.random((5, 5))

    s = BytesIO()
    f = gzip.GzipFile(fileobj=s, mode="w")

    np.save(f, a)
    f.close()
    s.seek(0)

    f = gzip.GzipFile(fileobj=s, mode="r")
    assert_array_equal(np.load(f), a)


# These next two classes encode the minimal API needed to save()/load() arrays.
# The `test_ducktyping` ensures they work correctly
class JustWriter:
    def __init__(self, base):
        self.base = base

    def write(self, s):
        return self.base.write(s)

    def flush(self):
        return self.base.flush()

class JustReader:
    def __init__(self, base):
        self.base = base

    def read(self, n):
        return self.base.read(n)

    def seek(self, off, whence=0):
        return self.base.seek(off, whence)


def test_ducktyping():
    a = np.random.random((5, 5))

    s = BytesIO()
    f = JustWriter(s)

    np.save(f, a)
    f.flush()
    s.seek(0)

    f = JustReader(s)
    assert_array_equal(np.load(f), a)


def test_gzip_loadtxt():
    # Thanks to another windows brokenness, we can't use
    # NamedTemporaryFile: a file created from this function cannot be
    # reopened by another open call. So we first put the gzipped string
    # of the test reference array, write it to a securely opened file,
    # which is then read from by the loadtxt function
    s = BytesIO()
    g = gzip.GzipFile(fileobj=s, mode='w')
    g.write(b'1 2 3\n')
    g.close()

    s.seek(0)
    with temppath(suffix='.gz') as name:
        with open(name, 'wb') as f:
            f.write(s.read())
        res = np.loadtxt(name)
    s.close()

    assert_array_equal(res, [1, 2, 3])


def test_gzip_loadtxt_from_string():
    s = BytesIO()
    f = gzip.GzipFile(fileobj=s, mode="w")
    f.write(b'1 2 3\n')
    f.close()
    s.seek(0)

    f = gzip.GzipFile(fileobj=s, mode="r")
    assert_array_equal(np.loadtxt(f), [1, 2, 3])


def test_npzfile_dict():
    s = BytesIO()
    x = np.zeros((3, 3))
    y = np.zeros((3, 3))

    np.savez(s, x=x, y=y)
    s.seek(0)

    z = np.load(s)

    assert_('x' in z)
    assert_('y' in z)
    assert_('x' in z.keys())
    assert_('y' in z.keys())

    for f, a in z.items():
        assert_(f in ['x', 'y'])
        assert_equal(a.shape, (3, 3))

    for a in z.values():
        assert_equal(a.shape, (3, 3))

    assert_(len(z.items()) == 2)

    for f in z:
        assert_(f in ['x', 'y'])

    assert_('x' in z.keys())
    assert (z.get('x') == z['x']).all()


@pytest.mark.skipif(not HAS_REFCOUNT, reason="Python lacks refcounts")
def test_load_refcount():
    # Check that objects returned by np.load are directly freed based on
    # their refcount, rather than needing the gc to collect them.

    f = BytesIO()
    np.savez(f, [1, 2, 3])
    f.seek(0)

    with assert_no_gc_cycles():
        np.load(f)

    f.seek(0)
    dt = [("a", 'u1', 2), ("b", 'u1', 2)]
    with assert_no_gc_cycles():
        x = np.loadtxt(TextIO("0 1 2 3"), dtype=dt)
        assert_equal(x, np.array([((0, 1), (2, 3))], dtype=dt))


def test_load_multiple_arrays_until_eof():
    f = BytesIO()
    np.save(f, 1)
    np.save(f, 2)
    f.seek(0)
    out1 = np.load(f)
    assert out1 == 1
    out2 = np.load(f)
    assert out2 == 2
    with pytest.raises(EOFError):
        np.load(f)


def test_savez_nopickle():
    obj_array = np.array([1, 'hello'], dtype=object)
    with temppath(suffix='.npz') as tmp:
        np.savez(tmp, obj_array)

    with temppath(suffix='.npz') as tmp:
        with pytest.raises(ValueError, match="Object arrays cannot be saved when.*"):
            np.savez(tmp, obj_array, allow_pickle=False)

    with temppath(suffix='.npz') as tmp:
        np.savez_compressed(tmp, obj_array)

    with temppath(suffix='.npz') as tmp:
        with pytest.raises(ValueError, match="Object arrays cannot be saved when.*"):
            np.savez_compressed(tmp, obj_array, allow_pickle=False)

# === NexusCore/src\code_interpreter\JupyterClient.py ===
from jupyter_client import KernelManager
import threading
import re
from utils.const import *


class JupyterNotebook:
    def __init__(self):
        self.km = KernelManager()
        self.km.start_kernel()
        self.kc = self.km.client()
        _ = self.add_and_run(TOOLS_CODE)

    def clean_output(self, outputs):
        outputs_only_str = list()
        for i in outputs:
            if type(i) == dict:
                if "text/plain" in list(i.keys()):
                    outputs_only_str.append(i["text/plain"])
            elif type(i) == str:
                outputs_only_str.append(i)
            elif type(i) == list:
                error_msg = "\n".join(i)
                error_msg = re.sub(r"\x1b\[.*?m", "", error_msg)
                outputs_only_str.append(error_msg)

        return "\n".join(outputs_only_str).strip()

    def add_and_run(self, code_string):
        # This inner function will be executed in a separate thread
        def run_code_in_thread():
            nonlocal outputs, error_flag

            # Execute the code and get the execution count
            msg_id = self.kc.execute(code_string)

            while True:
                try:
                    msg = self.kc.get_iopub_msg(timeout=20)

                    msg_type = msg["header"]["msg_type"]
                    content = msg["content"]

                    if msg_type == "execute_result":
                        outputs.append(content["data"])
                    elif msg_type == "stream":
                        outputs.append(content["text"])
                    elif msg_type == "error":
                        error_flag = True
                        outputs.append(content["traceback"])

                    # If the execution state of the kernel is idle, it means the cell finished executing
                    if msg_type == "status" and content["execution_state"] == "idle":
                        break
                except:
                    break

        outputs = []
        error_flag = False

        # Start the thread to run the code
        thread = threading.Thread(target=run_code_in_thread)
        thread.start()

        # Wait for 20 seconds for the thread to finish
        thread.join(timeout=20)

        # If the thread is still alive after 20 seconds, it's a timeout
        if thread.is_alive():
            outputs = ["Execution timed out."]
            # outputs = ["Error"]
            error_flag = "Timeout"

        return self.clean_output(outputs), error_flag

    def close(self):
        """Shutdown the kernel."""
        self.km.shutdown_kernel()
    
    def __deepcopy__(self, memo):
        if id(self) in memo:
            return memo[id(self)]
        new_copy = type(self)()
        memo[id(self)] = new_copy
        return new_copy

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\code_interpreter\JupyterClient.py ===
from jupyter_client import KernelManager
import threading
import re
from utils.const import *


class JupyterNotebook:
    def __init__(self):
        self.km = KernelManager()
        self.km.start_kernel()
        self.kc = self.km.client()
        _ = self.add_and_run(TOOLS_CODE)

    def clean_output(self, outputs):
        outputs_only_str = list()
        for i in outputs:
            if type(i) == dict:
                if "text/plain" in list(i.keys()):
                    outputs_only_str.append(i["text/plain"])
            elif type(i) == str:
                outputs_only_str.append(i)
            elif type(i) == list:
                error_msg = "\n".join(i)
                error_msg = re.sub(r"\x1b\[.*?m", "", error_msg)
                outputs_only_str.append(error_msg)

        return "\n".join(outputs_only_str).strip()

    def add_and_run(self, code_string):
        # This inner function will be executed in a separate thread
        def run_code_in_thread():
            nonlocal outputs, error_flag

            # Execute the code and get the execution count
            msg_id = self.kc.execute(code_string)

            while True:
                try:
                    msg = self.kc.get_iopub_msg(timeout=20)

                    msg_type = msg["header"]["msg_type"]
                    content = msg["content"]

                    if msg_type == "execute_result":
                        outputs.append(content["data"])
                    elif msg_type == "stream":
                        outputs.append(content["text"])
                    elif msg_type == "error":
                        error_flag = True
                        outputs.append(content["traceback"])

                    # If the execution state of the kernel is idle, it means the cell finished executing
                    if msg_type == "status" and content["execution_state"] == "idle":
                        break
                except:
                    break

        outputs = []
        error_flag = False

        # Start the thread to run the code
        thread = threading.Thread(target=run_code_in_thread)
        thread.start()

        # Wait for 20 seconds for the thread to finish
        thread.join(timeout=20)

        # If the thread is still alive after 20 seconds, it's a timeout
        if thread.is_alive():
            outputs = ["Execution timed out."]
            # outputs = ["Error"]
            error_flag = "Timeout"

        return self.clean_output(outputs), error_flag

    def close(self):
        """Shutdown the kernel."""
        self.km.shutdown_kernel()
    
    def __deepcopy__(self, memo):
        if id(self) in memo:
            return memo[id(self)]
        new_copy = type(self)()
        memo[id(self)] = new_copy
        return new_copy

# === NexusCore/openenv\Lib\site-packages\numpy\lib\_npyio_impl.py ===
"""
IO related functions.
"""
import contextlib
import functools
import itertools
import operator
import os
import pickle
import re
import warnings
import weakref
from collections.abc import Mapping
from operator import itemgetter

import numpy as np
from numpy._core import overrides
from numpy._core._multiarray_umath import _load_from_filelike
from numpy._core.multiarray import packbits, unpackbits
from numpy._core.overrides import finalize_array_function_like, set_module
from numpy._utils import asbytes, asunicode

from . import format
from ._datasource import DataSource  # noqa: F401
from ._format_impl import _MAX_HEADER_SIZE
from ._iotools import (
    ConversionWarning,
    ConverterError,
    ConverterLockError,
    LineSplitter,
    NameValidator,
    StringConverter,
    _decode_line,
    _is_string_like,
    easy_dtype,
    flatten_dtype,
    has_nested_fields,
)

__all__ = [
    'savetxt', 'loadtxt', 'genfromtxt', 'load', 'save', 'savez',
    'savez_compressed', 'packbits', 'unpackbits', 'fromregex'
    ]


array_function_dispatch = functools.partial(
    overrides.array_function_dispatch, module='numpy')


class BagObj:
    """
    BagObj(obj)

    Convert attribute look-ups to getitems on the object passed in.

    Parameters
    ----------
    obj : class instance
        Object on which attribute look-up is performed.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.lib._npyio_impl import BagObj as BO
    >>> class BagDemo:
    ...     def __getitem__(self, key): # An instance of BagObj(BagDemo)
    ...                                 # will call this method when any
    ...                                 # attribute look-up is required
    ...         result = "Doesn't matter what you want, "
    ...         return result + "you're gonna get this"
    ...
    >>> demo_obj = BagDemo()
    >>> bagobj = BO(demo_obj)
    >>> bagobj.hello_there
    "Doesn't matter what you want, you're gonna get this"
    >>> bagobj.I_can_be_anything
    "Doesn't matter what you want, you're gonna get this"

    """

    def __init__(self, obj):
        # Use weakref to make NpzFile objects collectable by refcount
        self._obj = weakref.proxy(obj)

    def __getattribute__(self, key):
        try:
            return object.__getattribute__(self, '_obj')[key]
        except KeyError:
            raise AttributeError(key) from None

    def __dir__(self):
        """
        Enables dir(bagobj) to list the files in an NpzFile.

        This also enables tab-completion in an interpreter or IPython.
        """
        return list(object.__getattribute__(self, '_obj').keys())


def zipfile_factory(file, *args, **kwargs):
    """
    Create a ZipFile.

    Allows for Zip64, and the `file` argument can accept file, str, or
    pathlib.Path objects. `args` and `kwargs` are passed to the zipfile.ZipFile
    constructor.
    """
    if not hasattr(file, 'read'):
        file = os.fspath(file)
    import zipfile
    kwargs['allowZip64'] = True
    return zipfile.ZipFile(file, *args, **kwargs)


@set_module('numpy.lib.npyio')
class NpzFile(Mapping):
    """
    NpzFile(fid)

    A dictionary-like object with lazy-loading of files in the zipped
    archive provided on construction.

    `NpzFile` is used to load files in the NumPy ``.npz`` data archive
    format. It assumes that files in the archive have a ``.npy`` extension,
    other files are ignored.

    The arrays and file strings are lazily loaded on either
    getitem access using ``obj['key']`` or attribute lookup using
    ``obj.f.key``. A list of all files (without ``.npy`` extensions) can
    be obtained with ``obj.files`` and the ZipFile object itself using
    ``obj.zip``.

    Attributes
    ----------
    files : list of str
        List of all files in the archive with a ``.npy`` extension.
    zip : ZipFile instance
        The ZipFile object initialized with the zipped archive.
    f : BagObj instance
        An object on which attribute can be performed as an alternative
        to getitem access on the `NpzFile` instance itself.
    allow_pickle : bool, optional
        Allow loading pickled data. Default: False
    pickle_kwargs : dict, optional
        Additional keyword arguments to pass on to pickle.load.
        These are only useful when loading object arrays saved on
        Python 2.
    max_header_size : int, optional
        Maximum allowed size of the header.  Large headers may not be safe
        to load securely and thus require explicitly passing a larger value.
        See :py:func:`ast.literal_eval()` for details.
        This option is ignored when `allow_pickle` is passed.  In that case
        the file is by definition trusted and the limit is unnecessary.

    Parameters
    ----------
    fid : file, str, or pathlib.Path
        The zipped archive to open. This is either a file-like object
        or a string containing the path to the archive.
    own_fid : bool, optional
        Whether NpzFile should close the file handle.
        Requires that `fid` is a file-like object.

    Examples
    --------
    >>> import numpy as np
    >>> from tempfile import TemporaryFile
    >>> outfile = TemporaryFile()
    >>> x = np.arange(10)
    >>> y = np.sin(x)
    >>> np.savez(outfile, x=x, y=y)
    >>> _ = outfile.seek(0)

    >>> npz = np.load(outfile)
    >>> isinstance(npz, np.lib.npyio.NpzFile)
    True
    >>> npz
    NpzFile 'object' with keys: x, y
    >>> sorted(npz.files)
    ['x', 'y']
    >>> npz['x']  # getitem access
    array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    >>> npz.f.x  # attribute lookup
    array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])

    """
    # Make __exit__ safe if zipfile_factory raises an exception
    zip = None
    fid = None
    _MAX_REPR_ARRAY_COUNT = 5

    def __init__(self, fid, own_fid=False, allow_pickle=False,
                 pickle_kwargs=None, *,
                 max_header_size=_MAX_HEADER_SIZE):
        # Import is postponed to here since zipfile depends on gzip, an
        # optional component of the so-called standard library.
        _zip = zipfile_factory(fid)
        _files = _zip.namelist()
        self.files = [name.removesuffix(".npy") for name in _files]
        self._files = dict(zip(self.files, _files))
        self._files.update(zip(_files, _files))
        self.allow_pickle = allow_pickle
        self.max_header_size = max_header_size
        self.pickle_kwargs = pickle_kwargs
        self.zip = _zip
        self.f = BagObj(self)
        if own_fid:
            self.fid = fid

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        """
        Close the file.

        """
        if self.zip is not None:
            self.zip.close()
            self.zip = None
        if self.fid is not None:
            self.fid.close()
            self.fid = None
        self.f = None  # break reference cycle

    def __del__(self):
        self.close()

    # Implement the Mapping ABC
    def __iter__(self):
        return iter(self.files)

    def __len__(self):
        return len(self.files)

    def __getitem__(self, key):
        try:
            key = self._files[key]
        except KeyError:
            raise KeyError(f"{key} is not a file in the archive") from None
        else:
            with self.zip.open(key) as bytes:
                magic = bytes.read(len(format.MAGIC_PREFIX))
                bytes.seek(0)
                if magic == format.MAGIC_PREFIX:
                    # FIXME: This seems like it will copy strings around
                    #   more than is strictly necessary.  The zipfile
                    #   will read the string and then
                    #   the format.read_array will copy the string
                    #   to another place in memory.
                    #   It would be better if the zipfile could read
                    #   (or at least uncompress) the data
                    #   directly into the array memory.
                    return format.read_array(
                        bytes,
                        allow_pickle=self.allow_pickle,
                        pickle_kwargs=self.pickle_kwargs,
                        max_header_size=self.max_header_size
                    )
                else:
                    return bytes.read(key)

    def __contains__(self, key):
        return (key in self._files)

    def __repr__(self):
        # Get filename or default to `object`
        if isinstance(self.fid, str):
            filename = self.fid
        else:
            filename = getattr(self.fid, "name", "object")

        # Get the name of arrays
        array_names = ', '.join(self.files[:self._MAX_REPR_ARRAY_COUNT])
        if len(self.files) > self._MAX_REPR_ARRAY_COUNT:
            array_names += "..."
        return f"NpzFile {filename!r} with keys: {array_names}"

    # Work around problems with the docstrings in the Mapping methods
    # They contain a `->`, which confuses the type annotation interpretations
    # of sphinx-docs. See gh-25964

    def get(self, key, default=None, /):
        """
        D.get(k,[,d]) returns D[k] if k in D, else d.  d defaults to None.
        """
        return Mapping.get(self, key, default)

    def items(self):
        """
        D.items() returns a set-like object providing a view on the items
        """
        return Mapping.items(self)

    def keys(self):
        """
        D.keys() returns a set-like object providing a view on the keys
        """
        return Mapping.keys(self)

    def values(self):
        """
        D.values() returns a set-like object providing a view on the values
        """
        return Mapping.values(self)


@set_module('numpy')
def load(file, mmap_mode=None, allow_pickle=False, fix_imports=True,
         encoding='ASCII', *, max_header_size=_MAX_HEADER_SIZE):
    """
    Load arrays or pickled objects from ``.npy``, ``.npz`` or pickled files.

    .. warning:: Loading files that contain object arrays uses the ``pickle``
                 module, which is not secure against erroneous or maliciously
                 constructed data. Consider passing ``allow_pickle=False`` to
                 load data that is known not to contain object arrays for the
                 safer handling of untrusted sources.

    Parameters
    ----------
    file : file-like object, string, or pathlib.Path
        The file to read. File-like objects must support the
        ``seek()`` and ``read()`` methods and must always
        be opened in binary mode.  Pickled files require that the
        file-like object support the ``readline()`` method as well.
    mmap_mode : {None, 'r+', 'r', 'w+', 'c'}, optional
        If not None, then memory-map the file, using the given mode (see
        `numpy.memmap` for a detailed description of the modes).  A
        memory-mapped array is kept on disk. However, it can be accessed
        and sliced like any ndarray.  Memory mapping is especially useful
        for accessing small fragments of large files without reading the
        entire file into memory.
    allow_pickle : bool, optional
        Allow loading pickled object arrays stored in npy files. Reasons for
        disallowing pickles include security, as loading pickled data can
        execute arbitrary code. If pickles are disallowed, loading object
        arrays will fail. Default: False
    fix_imports : bool, optional
        Only useful when loading Python 2 generated pickled files,
        which includes npy/npz files containing object arrays. If `fix_imports`
        is True, pickle will try to map the old Python 2 names to the new names
        used in Python 3.
    encoding : str, optional
        What encoding to use when reading Python 2 strings. Only useful when
        loading Python 2 generated pickled files, which includes
        npy/npz files containing object arrays. Values other than 'latin1',
        'ASCII', and 'bytes' are not allowed, as they can corrupt numerical
        data. Default: 'ASCII'
    max_header_size : int, optional
        Maximum allowed size of the header.  Large headers may not be safe
        to load securely and thus require explicitly passing a larger value.
        See :py:func:`ast.literal_eval()` for details.
        This option is ignored when `allow_pickle` is passed.  In that case
        the file is by definition trusted and the limit is unnecessary.

    Returns
    -------
    result : array, tuple, dict, etc.
        Data stored in the file. For ``.npz`` files, the returned instance
        of NpzFile class must be closed to avoid leaking file descriptors.

    Raises
    ------
    OSError
        If the input file does not exist or cannot be read.
    UnpicklingError
        If ``allow_pickle=True``, but the file cannot be loaded as a pickle.
    ValueError
        The file contains an object array, but ``allow_pickle=False`` given.
    EOFError
        When calling ``np.load`` multiple times on the same file handle,
        if all data has already been read

    See Also
    --------
    save, savez, savez_compressed, loadtxt
    memmap : Create a memory-map to an array stored in a file on disk.
    lib.format.open_memmap : Create or load a memory-mapped ``.npy`` file.

    Notes
    -----
    - If the file contains pickle data, then whatever object is stored
      in the pickle is returned.
    - If the file is a ``.npy`` file, then a single array is returned.
    - If the file is a ``.npz`` file, then a dictionary-like object is
      returned, containing ``{filename: array}`` key-value pairs, one for
      each file in the archive.
    - If the file is a ``.npz`` file, the returned value supports the
      context manager protocol in a similar fashion to the open function::

        with load('foo.npz') as data:
            a = data['a']

      The underlying file descriptor is closed when exiting the 'with'
      block.

    Examples
    --------
    >>> import numpy as np

    Store data to disk, and load it again:

    >>> np.save('/tmp/123', np.array([[1, 2, 3], [4, 5, 6]]))
    >>> np.load('/tmp/123.npy')
    array([[1, 2, 3],
           [4, 5, 6]])

    Store compressed data to disk, and load it again:

    >>> a=np.array([[1, 2, 3], [4, 5, 6]])
    >>> b=np.array([1, 2])
    >>> np.savez('/tmp/123.npz', a=a, b=b)
    >>> data = np.load('/tmp/123.npz')
    >>> data['a']
    array([[1, 2, 3],
           [4, 5, 6]])
    >>> data['b']
    array([1, 2])
    >>> data.close()

    Mem-map the stored array, and then access the second row
    directly from disk:

    >>> X = np.load('/tmp/123.npy', mmap_mode='r')
    >>> X[1, :]
    memmap([4, 5, 6])

    """
    if encoding not in ('ASCII', 'latin1', 'bytes'):
        # The 'encoding' value for pickle also affects what encoding
        # the serialized binary data of NumPy arrays is loaded
        # in. Pickle does not pass on the encoding information to
        # NumPy. The unpickling code in numpy._core.multiarray is
        # written to assume that unicode data appearing where binary
        # should be is in 'latin1'. 'bytes' is also safe, as is 'ASCII'.
        #
        # Other encoding values can corrupt binary data, and we
        # purposefully disallow them. For the same reason, the errors=
        # argument is not exposed, as values other than 'strict'
        # result can similarly silently corrupt numerical data.
        raise ValueError("encoding must be 'ASCII', 'latin1', or 'bytes'")

    pickle_kwargs = {'encoding': encoding, 'fix_imports': fix_imports}

    with contextlib.ExitStack() as stack:
        if hasattr(file, 'read'):
            fid = file
            own_fid = False
        else:
            fid = stack.enter_context(open(os.fspath(file), "rb"))
            own_fid = True

        # Code to distinguish from NumPy binary files and pickles.
        _ZIP_PREFIX = b'PK\x03\x04'
        _ZIP_SUFFIX = b'PK\x05\x06'  # empty zip files start with this
        N = len(format.MAGIC_PREFIX)
        magic = fid.read(N)
        if not magic:
            raise EOFError("No data left in file")
        # If the file size is less than N, we need to make sure not
        # to seek past the beginning of the file
        fid.seek(-min(N, len(magic)), 1)  # back-up
        if magic.startswith((_ZIP_PREFIX, _ZIP_SUFFIX)):
            # zip-file (assume .npz)
            # Potentially transfer file ownership to NpzFile
            stack.pop_all()
            ret = NpzFile(fid, own_fid=own_fid, allow_pickle=allow_pickle,
                          pickle_kwargs=pickle_kwargs,
                          max_header_size=max_header_size)
            return ret
        elif magic == format.MAGIC_PREFIX:
            # .npy file
            if mmap_mode:
                if allow_pickle:
                    max_header_size = 2**64
                return format.open_memmap(file, mode=mmap_mode,
                                          max_header_size=max_header_size)
            else:
                return format.read_array(fid, allow_pickle=allow_pickle,
                                         pickle_kwargs=pickle_kwargs,
                                         max_header_size=max_header_size)
        else:
            # Try a pickle
            if not allow_pickle:
                raise ValueError(
                    "This file contains pickled (object) data. If you trust "
                    "the file you can load it unsafely using the "
                    "`allow_pickle=` keyword argument or `pickle.load()`.")
            try:
                return pickle.load(fid, **pickle_kwargs)
            except Exception as e:
                raise pickle.UnpicklingError(
                    f"Failed to interpret file {file!r} as a pickle") from e


def _save_dispatcher(file, arr, allow_pickle=None, fix_imports=None):
    return (arr,)


@array_function_dispatch(_save_dispatcher)
def save(file, arr, allow_pickle=True, fix_imports=np._NoValue):
    """
    Save an array to a binary file in NumPy ``.npy`` format.

    Parameters
    ----------
    file : file, str, or pathlib.Path
        File or filename to which the data is saved. If file is a file-object,
        then the filename is unchanged.  If file is a string or Path,
        a ``.npy`` extension will be appended to the filename if it does not
        already have one.
    arr : array_like
        Array data to be saved.
    allow_pickle : bool, optional
        Allow saving object arrays using Python pickles. Reasons for
        disallowing pickles include security (loading pickled data can execute
        arbitrary code) and portability (pickled objects may not be loadable
        on different Python installations, for example if the stored objects
        require libraries that are not available, and not all pickled data is
        compatible between different versions of Python).
        Default: True
    fix_imports : bool, optional
        The `fix_imports` flag is deprecated and has no effect.

        .. deprecated:: 2.1
            This flag is ignored since NumPy 1.17 and was only needed to
            support loading in Python 2 some files written in Python 3.

    See Also
    --------
    savez : Save several arrays into a ``.npz`` archive
    savetxt, load

    Notes
    -----
    For a description of the ``.npy`` format, see :py:mod:`numpy.lib.format`.

    Any data saved to the file is appended to the end of the file.

    Examples
    --------
    >>> import numpy as np

    >>> from tempfile import TemporaryFile
    >>> outfile = TemporaryFile()

    >>> x = np.arange(10)
    >>> np.save(outfile, x)

    >>> _ = outfile.seek(0) # Only needed to simulate closing & reopening file
    >>> np.load(outfile)
    array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])


    >>> with open('test.npy', 'wb') as f:
    ...     np.save(f, np.array([1, 2]))
    ...     np.save(f, np.array([1, 3]))
    >>> with open('test.npy', 'rb') as f:
    ...     a = np.load(f)
    ...     b = np.load(f)
    >>> print(a, b)
    # [1 2] [1 3]
    """
    if fix_imports is not np._NoValue:
        # Deprecated 2024-05-16, NumPy 2.1
        warnings.warn(
            "The 'fix_imports' flag is deprecated and has no effect. "
            "(Deprecated in NumPy 2.1)",
            DeprecationWarning, stacklevel=2)
    if hasattr(file, 'write'):
        file_ctx = contextlib.nullcontext(file)
    else:
        file = os.fspath(file)
        if not file.endswith('.npy'):
            file = file + '.npy'
        file_ctx = open(file, "wb")

    with file_ctx as fid:
        arr = np.asanyarray(arr)
        format.write_array(fid, arr, allow_pickle=allow_pickle,
                           pickle_kwargs={'fix_imports': fix_imports})


def _savez_dispatcher(file, *args, allow_pickle=True, **kwds):
    yield from args
    yield from kwds.values()


@array_function_dispatch(_savez_dispatcher)
def savez(file, *args, allow_pickle=True, **kwds):
    """Save several arrays into a single file in uncompressed ``.npz`` format.

    Provide arrays as keyword arguments to store them under the
    corresponding name in the output file: ``savez(fn, x=x, y=y)``.

    If arrays are specified as positional arguments, i.e., ``savez(fn,
    x, y)``, their names will be `arr_0`, `arr_1`, etc.

    Parameters
    ----------
    file : file, str, or pathlib.Path
        Either the filename (string) or an open file (file-like object)
        where the data will be saved. If file is a string or a Path, the
        ``.npz`` extension will be appended to the filename if it is not
        already there.
    args : Arguments, optional
        Arrays to save to the file. Please use keyword arguments (see
        `kwds` below) to assign names to arrays.  Arrays specified as
        args will be named "arr_0", "arr_1", and so on.
    allow_pickle : bool, optional
        Allow saving object arrays using Python pickles. Reasons for
        disallowing pickles include security (loading pickled data can execute
        arbitrary code) and portability (pickled objects may not be loadable
        on different Python installations, for example if the stored objects
        require libraries that are not available, and not all pickled data is
        compatible between different versions of Python).
        Default: True
    kwds : Keyword arguments, optional
        Arrays to save to the file. Each array will be saved to the
        output file with its corresponding keyword name.

    Returns
    -------
    None

    See Also
    --------
    save : Save a single array to a binary file in NumPy format.
    savetxt : Save an array to a file as plain text.
    savez_compressed : Save several arrays into a compressed ``.npz`` archive

    Notes
    -----
    The ``.npz`` file format is a zipped archive of files named after the
    variables they contain.  The archive is not compressed and each file
    in the archive contains one variable in ``.npy`` format. For a
    description of the ``.npy`` format, see :py:mod:`numpy.lib.format`.

    When opening the saved ``.npz`` file with `load` a `~lib.npyio.NpzFile`
    object is returned. This is a dictionary-like object which can be queried
    for its list of arrays (with the ``.files`` attribute), and for the arrays
    themselves.

    Keys passed in `kwds` are used as filenames inside the ZIP archive.
    Therefore, keys should be valid filenames; e.g., avoid keys that begin with
    ``/`` or contain ``.``.

    When naming variables with keyword arguments, it is not possible to name a
    variable ``file``, as this would cause the ``file`` argument to be defined
    twice in the call to ``savez``.

    Examples
    --------
    >>> import numpy as np
    >>> from tempfile import TemporaryFile
    >>> outfile = TemporaryFile()
    >>> x = np.arange(10)
    >>> y = np.sin(x)

    Using `savez` with \\*args, the arrays are saved with default names.

    >>> np.savez(outfile, x, y)
    >>> _ = outfile.seek(0) # Only needed to simulate closing & reopening file
    >>> npzfile = np.load(outfile)
    >>> npzfile.files
    ['arr_0', 'arr_1']
    >>> npzfile['arr_0']
    array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])

    Using `savez` with \\**kwds, the arrays are saved with the keyword names.

    >>> outfile = TemporaryFile()
    >>> np.savez(outfile, x=x, y=y)
    >>> _ = outfile.seek(0)
    >>> npzfile = np.load(outfile)
    >>> sorted(npzfile.files)
    ['x', 'y']
    >>> npzfile['x']
    array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])

    """
    _savez(file, args, kwds, False, allow_pickle=allow_pickle)


def _savez_compressed_dispatcher(file, *args, allow_pickle=True, **kwds):
    yield from args
    yield from kwds.values()


@array_function_dispatch(_savez_compressed_dispatcher)
def savez_compressed(file, *args, allow_pickle=True, **kwds):
    """
    Save several arrays into a single file in compressed ``.npz`` format.

    Provide arrays as keyword arguments to store them under the
    corresponding name in the output file: ``savez_compressed(fn, x=x, y=y)``.

    If arrays are specified as positional arguments, i.e.,
    ``savez_compressed(fn, x, y)``, their names will be `arr_0`, `arr_1`, etc.

    Parameters
    ----------
    file : file, str, or pathlib.Path
        Either the filename (string) or an open file (file-like object)
        where the data will be saved. If file is a string or a Path, the
        ``.npz`` extension will be appended to the filename if it is not
        already there.
    args : Arguments, optional
        Arrays to save to the file. Please use keyword arguments (see
        `kwds` below) to assign names to arrays.  Arrays specified as
        args will be named "arr_0", "arr_1", and so on.
    allow_pickle : bool, optional
        Allow saving object arrays using Python pickles. Reasons for
        disallowing pickles include security (loading pickled data can execute
        arbitrary code) and portability (pickled objects may not be loadable
        on different Python installations, for example if the stored objects
        require libraries that are not available, and not all pickled data is
        compatible between different versions of Python).
        Default: True
    kwds : Keyword arguments, optional
        Arrays to save to the file. Each array will be saved to the
        output file with its corresponding keyword name.

    Returns
    -------
    None

    See Also
    --------
    numpy.save : Save a single array to a binary file in NumPy format.
    numpy.savetxt : Save an array to a file as plain text.
    numpy.savez : Save several arrays into an uncompressed ``.npz`` file format
    numpy.load : Load the files created by savez_compressed.

    Notes
    -----
    The ``.npz`` file format is a zipped archive of files named after the
    variables they contain.  The archive is compressed with
    ``zipfile.ZIP_DEFLATED`` and each file in the archive contains one variable
    in ``.npy`` format. For a description of the ``.npy`` format, see
    :py:mod:`numpy.lib.format`.


    When opening the saved ``.npz`` file with `load` a `~lib.npyio.NpzFile`
    object is returned. This is a dictionary-like object which can be queried
    for its list of arrays (with the ``.files`` attribute), and for the arrays
    themselves.

    Examples
    --------
    >>> import numpy as np
    >>> test_array = np.random.rand(3, 2)
    >>> test_vector = np.random.rand(4)
    >>> np.savez_compressed('/tmp/123', a=test_array, b=test_vector)
    >>> loaded = np.load('/tmp/123.npz')
    >>> print(np.array_equal(test_array, loaded['a']))
    True
    >>> print(np.array_equal(test_vector, loaded['b']))
    True

    """
    _savez(file, args, kwds, True, allow_pickle=allow_pickle)


def _savez(file, args, kwds, compress, allow_pickle=True, pickle_kwargs=None):
    # Import is postponed to here since zipfile depends on gzip, an optional
    # component of the so-called standard library.
    import zipfile

    if not hasattr(file, 'write'):
        file = os.fspath(file)
        if not file.endswith('.npz'):
            file = file + '.npz'

    namedict = kwds
    for i, val in enumerate(args):
        key = 'arr_%d' % i
        if key in namedict.keys():
            raise ValueError(
                f"Cannot use un-named variables and keyword {key}")
        namedict[key] = val

    if compress:
        compression = zipfile.ZIP_DEFLATED
    else:
        compression = zipfile.ZIP_STORED

    zipf = zipfile_factory(file, mode="w", compression=compression)
    try:
        for key, val in namedict.items():
            fname = key + '.npy'
            val = np.asanyarray(val)
            # always force zip64, gh-10776
            with zipf.open(fname, 'w', force_zip64=True) as fid:
                format.write_array(fid, val,
                                   allow_pickle=allow_pickle,
                                   pickle_kwargs=pickle_kwargs)
    finally:
        zipf.close()


def _ensure_ndmin_ndarray_check_param(ndmin):
    """Just checks if the param ndmin is supported on
        _ensure_ndmin_ndarray. It is intended to be used as
        verification before running anything expensive.
        e.g. loadtxt, genfromtxt
    """
    # Check correctness of the values of `ndmin`
    if ndmin not in [0, 1, 2]:
        raise ValueError(f"Illegal value of ndmin keyword: {ndmin}")

def _ensure_ndmin_ndarray(a, *, ndmin: int):
    """This is a helper function of loadtxt and genfromtxt to ensure
        proper minimum dimension as requested

        ndim : int. Supported values 1, 2, 3
                    ^^ whenever this changes, keep in sync with
                       _ensure_ndmin_ndarray_check_param
    """
    # Verify that the array has at least dimensions `ndmin`.
    # Tweak the size and shape of the arrays - remove extraneous dimensions
    if a.ndim > ndmin:
        a = np.squeeze(a)
    # and ensure we have the minimum number of dimensions asked for
    # - has to be in this order for the odd case ndmin=1, a.squeeze().ndim=0
    if a.ndim < ndmin:
        if ndmin == 1:
            a = np.atleast_1d(a)
        elif ndmin == 2:
            a = np.atleast_2d(a).T

    return a


# amount of lines loadtxt reads in one chunk, can be overridden for testing
_loadtxt_chunksize = 50000


def _check_nonneg_int(value, name="argument"):
    try:
        operator.index(value)
    except TypeError:
        raise TypeError(f"{name} must be an integer") from None
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")


def _preprocess_comments(iterable, comments, encoding):
    """
    Generator that consumes a line iterated iterable and strips out the
    multiple (or multi-character) comments from lines.
    This is a pre-processing step to achieve feature parity with loadtxt
    (we assume that this feature is a nieche feature).
    """
    for line in iterable:
        if isinstance(line, bytes):
            # Need to handle conversion here, or the splitting would fail
            line = line.decode(encoding)

        for c in comments:
            line = line.split(c, 1)[0]

        yield line


# The number of rows we read in one go if confronted with a parametric dtype
_loadtxt_chunksize = 50000


def _read(fname, *, delimiter=',', comment='#', quote='"',
          imaginary_unit='j', usecols=None, skiplines=0,
          max_rows=None, converters=None, ndmin=None, unpack=False,
          dtype=np.float64, encoding=None):
    r"""
    Read a NumPy array from a text file.
    This is a helper function for loadtxt.

    Parameters
    ----------
    fname : file, str, or pathlib.Path
        The filename or the file to be read.
    delimiter : str, optional
        Field delimiter of the fields in line of the file.
        Default is a comma, ','.  If None any sequence of whitespace is
        considered a delimiter.
    comment : str or sequence of str or None, optional
        Character that begins a comment.  All text from the comment
        character to the end of the line is ignored.
        Multiple comments or multiple-character comment strings are supported,
        but may be slower and `quote` must be empty if used.
        Use None to disable all use of comments.
    quote : str or None, optional
        Character that is used to quote string fields. Default is '"'
        (a double quote). Use None to disable quote support.
    imaginary_unit : str, optional
        Character that represent the imaginary unit `sqrt(-1)`.
        Default is 'j'.
    usecols : array_like, optional
        A one-dimensional array of integer column numbers.  These are the
        columns from the file to be included in the array.  If this value
        is not given, all the columns are used.
    skiplines : int, optional
        Number of lines to skip before interpreting the data in the file.
    max_rows : int, optional
        Maximum number of rows of data to read.  Default is to read the
        entire file.
    converters : dict or callable, optional
        A function to parse all columns strings into the desired value, or
        a dictionary mapping column number to a parser function.
        E.g. if column 0 is a date string: ``converters = {0: datestr2num}``.
        Converters can also be used to provide a default value for missing
        data, e.g. ``converters = lambda s: float(s.strip() or 0)`` will
        convert empty fields to 0.
        Default: None
    ndmin : int, optional
        Minimum dimension of the array returned.
        Allowed values are 0, 1 or 2.  Default is 0.
    unpack : bool, optional
        If True, the returned array is transposed, so that arguments may be
        unpacked using ``x, y, z = read(...)``.  When used with a structured
        data-type, arrays are returned for each field.  Default is False.
    dtype : numpy data type
        A NumPy dtype instance, can be a structured dtype to map to the
        columns of the file.
    encoding : str, optional
        Encoding used to decode the inputfile. The special value 'bytes'
        (the default) enables backwards-compatible behavior for `converters`,
        ensuring that inputs to the converter functions are encoded
        bytes objects. The special value 'bytes' has no additional effect if
        ``converters=None``. If encoding is ``'bytes'`` or ``None``, the
        default system encoding is used.

    Returns
    -------
    ndarray
        NumPy array.
    """
    # Handle special 'bytes' keyword for encoding
    byte_converters = False
    if encoding == 'bytes':
        encoding = None
        byte_converters = True

    if dtype is None:
        raise TypeError("a dtype must be provided.")
    dtype = np.dtype(dtype)

    read_dtype_via_object_chunks = None
    if dtype.kind in 'SUM' and dtype in {
            np.dtype("S0"), np.dtype("U0"), np.dtype("M8"), np.dtype("m8")}:
        # This is a legacy "flexible" dtype.  We do not truly support
        # parametric dtypes currently (no dtype discovery step in the core),
        # but have to support these for backward compatibility.
        read_dtype_via_object_chunks = dtype
        dtype = np.dtype(object)

    if usecols is not None:
        # Allow usecols to be a single int or a sequence of ints, the C-code
        # handles the rest
        try:
            usecols = list(usecols)
        except TypeError:
            usecols = [usecols]

    _ensure_ndmin_ndarray_check_param(ndmin)

    if comment is None:
        comments = None
    else:
        # assume comments are a sequence of strings
        if "" in comment:
            raise ValueError(
                "comments cannot be an empty string. Use comments=None to "
                "disable comments."
            )
        comments = tuple(comment)
        comment = None
        if len(comments) == 0:
            comments = None  # No comments at all
        elif len(comments) == 1:
            # If there is only one comment, and that comment has one character,
            # the normal parsing can deal with it just fine.
            if isinstance(comments[0], str) and len(comments[0]) == 1:
                comment = comments[0]
                comments = None
        # Input validation if there are multiple comment characters
        elif delimiter in comments:
            raise TypeError(
                f"Comment characters '{comments}' cannot include the "
                f"delimiter '{delimiter}'"
            )

    # comment is now either a 1 or 0 character string or a tuple:
    if comments is not None:
        # Note: An earlier version support two character comments (and could
        #       have been extended to multiple characters, we assume this is
        #       rare enough to not optimize for.
        if quote is not None:
            raise ValueError(
                "when multiple comments or a multi-character comment is "
                "given, quotes are not supported.  In this case quotechar "
                "must be set to None.")

    if len(imaginary_unit) != 1:
        raise ValueError('len(imaginary_unit) must be 1.')

    _check_nonneg_int(skiplines)
    if max_rows is not None:
        _check_nonneg_int(max_rows)
    else:
        # Passing -1 to the C code means "read the entire file".
        max_rows = -1

    fh_closing_ctx = contextlib.nullcontext()
    filelike = False
    try:
        if isinstance(fname, os.PathLike):
            fname = os.fspath(fname)
        if isinstance(fname, str):
            fh = np.lib._datasource.open(fname, 'rt', encoding=encoding)
            if encoding is None:
                encoding = getattr(fh, 'encoding', 'latin1')

            fh_closing_ctx = contextlib.closing(fh)
            data = fh
            filelike = True
        else:
            if encoding is None:
                encoding = getattr(fname, 'encoding', 'latin1')
            data = iter(fname)
    except TypeError as e:
        raise ValueError(
            f"fname must be a string, filehandle, list of strings,\n"
            f"or generator. Got {type(fname)} instead.") from e

    with fh_closing_ctx:
        if comments is not None:
            if filelike:
                data = iter(data)
                filelike = False
            data = _preprocess_comments(data, comments, encoding)

        if read_dtype_via_object_chunks is None:
            arr = _load_from_filelike(
                data, delimiter=delimiter, comment=comment, quote=quote,
                imaginary_unit=imaginary_unit,
                usecols=usecols, skiplines=skiplines, max_rows=max_rows,
                converters=converters, dtype=dtype,
                encoding=encoding, filelike=filelike,
                byte_converters=byte_converters)

        else:
            # This branch reads the file into chunks of object arrays and then
            # casts them to the desired actual dtype.  This ensures correct
            # string-length and datetime-unit discovery (like `arr.astype()`).
            # Due to chunking, certain error reports are less clear, currently.
            if filelike:
                data = iter(data)  # cannot chunk when reading from file
                filelike = False

            c_byte_converters = False
            if read_dtype_via_object_chunks == "S":
                c_byte_converters = True  # Use latin1 rather than ascii

            chunks = []
            while max_rows != 0:
                if max_rows < 0:
                    chunk_size = _loadtxt_chunksize
                else:
                    chunk_size = min(_loadtxt_chunksize, max_rows)

                next_arr = _load_from_filelike(
                    data, delimiter=delimiter, comment=comment, quote=quote,
                    imaginary_unit=imaginary_unit,
                    usecols=usecols, skiplines=skiplines, max_rows=chunk_size,
                    converters=converters, dtype=dtype,
                    encoding=encoding, filelike=filelike,
                    byte_converters=byte_converters,
                    c_byte_converters=c_byte_converters)
                # Cast here already.  We hope that this is better even for
                # large files because the storage is more compact.  It could
                # be adapted (in principle the concatenate could cast).
                chunks.append(next_arr.astype(read_dtype_via_object_chunks))

                skiplines = 0  # Only have to skip for first chunk
                if max_rows >= 0:
                    max_rows -= chunk_size
                if len(next_arr) < chunk_size:
                    # There was less data than requested, so we are done.
                    break

            # Need at least one chunk, but if empty, the last one may have
            # the wrong shape.
            if len(chunks) > 1 and len(chunks[-1]) == 0:
                del chunks[-1]
            if len(chunks) == 1:
                arr = chunks[0]
            else:
                arr = np.concatenate(chunks, axis=0)

    # NOTE: ndmin works as advertised for structured dtypes, but normally
    #       these would return a 1D result plus the structured dimension,
    #       so ndmin=2 adds a third dimension even when no squeezing occurs.
    #       A `squeeze=False` could be a better solution (pandas uses squeeze).
    arr = _ensure_ndmin_ndarray(arr, ndmin=ndmin)

    if arr.shape:
        if arr.shape[0] == 0:
            warnings.warn(
                f'loadtxt: input contained no data: "{fname}"',
                category=UserWarning,
                stacklevel=3
            )

    if unpack:
        # Unpack structured dtypes if requested:
        dt = arr.dtype
        if dt.names is not None:
            # For structured arrays, return an array for each field.
            return [arr[field] for field in dt.names]
        else:
            return arr.T
    else:
        return arr


@finalize_array_function_like
@set_module('numpy')
def loadtxt(fname, dtype=float, comments='#', delimiter=None,
            converters=None, skiprows=0, usecols=None, unpack=False,
            ndmin=0, encoding=None, max_rows=None, *, quotechar=None,
            like=None):
    r"""
    Load data from a text file.

    Parameters
    ----------
    fname : file, str, pathlib.Path, list of str, generator
        File, filename, list, or generator to read.  If the filename
        extension is ``.gz`` or ``.bz2``, the file is first decompressed. Note
        that generators must return bytes or strings. The strings
        in a list or produced by a generator are treated as lines.
    dtype : data-type, optional
        Data-type of the resulting array; default: float.  If this is a
        structured data-type, the resulting array will be 1-dimensional, and
        each row will be interpreted as an element of the array.  In this
        case, the number of columns used must match the number of fields in
        the data-type.
    comments : str or sequence of str or None, optional
        The characters or list of characters used to indicate the start of a
        comment. None implies no comments. For backwards compatibility, byte
        strings will be decoded as 'latin1'. The default is '#'.
    delimiter : str, optional
        The character used to separate the values. For backwards compatibility,
        byte strings will be decoded as 'latin1'. The default is whitespace.

        .. versionchanged:: 1.23.0
           Only single character delimiters are supported. Newline characters
           cannot be used as the delimiter.

    converters : dict or callable, optional
        Converter functions to customize value parsing. If `converters` is
        callable, the function is applied to all columns, else it must be a
        dict that maps column number to a parser function.
        See examples for further details.
        Default: None.

        .. versionchanged:: 1.23.0
           The ability to pass a single callable to be applied to all columns
           was added.

    skiprows : int, optional
        Skip the first `skiprows` lines, including comments; default: 0.
    usecols : int or sequence, optional
        Which columns to read, with 0 being the first. For example,
        ``usecols = (1,4,5)`` will extract the 2nd, 5th and 6th columns.
        The default, None, results in all columns being read.
    unpack : bool, optional
        If True, the returned array is transposed, so that arguments may be
        unpacked using ``x, y, z = loadtxt(...)``.  When used with a
        structured data-type, arrays are returned for each field.
        Default is False.
    ndmin : int, optional
        The returned array will have at least `ndmin` dimensions.
        Otherwise mono-dimensional axes will be squeezed.
        Legal values: 0 (default), 1 or 2.
    encoding : str, optional
        Encoding used to decode the inputfile. Does not apply to input streams.
        The special value 'bytes' enables backward compatibility workarounds
        that ensures you receive byte arrays as results if possible and passes
        'latin1' encoded strings to converters. Override this value to receive
        unicode arrays and pass strings as input to converters.  If set to None
        the system default is used. The default value is None.

        .. versionchanged:: 2.0
            Before NumPy 2, the default was ``'bytes'`` for Python 2
            compatibility. The default is now ``None``.

    max_rows : int, optional
        Read `max_rows` rows of content after `skiprows` lines. The default is
        to read all the rows. Note that empty rows containing no data such as
        empty lines and comment lines are not counted towards `max_rows`,
        while such lines are counted in `skiprows`.

        .. versionchanged:: 1.23.0
            Lines containing no data, including comment lines (e.g., lines
            starting with '#' or as specified via `comments`) are not counted
            towards `max_rows`.
    quotechar : unicode character or None, optional
        The character used to denote the start and end of a quoted item.
        Occurrences of the delimiter or comment characters are ignored within
        a quoted item. The default value is ``quotechar=None``, which means
        quoting support is disabled.

        If two consecutive instances of `quotechar` are found within a quoted
        field, the first is treated as an escape character. See examples.

        .. versionadded:: 1.23.0
    ${ARRAY_FUNCTION_LIKE}

        .. versionadded:: 1.20.0

    Returns
    -------
    out : ndarray
        Data read from the text file.

    See Also
    --------
    load, fromstring, fromregex
    genfromtxt : Load data with missing values handled as specified.
    scipy.io.loadmat : reads MATLAB data files

    Notes
    -----
    This function aims to be a fast reader for simply formatted files.  The
    `genfromtxt` function provides more sophisticated handling of, e.g.,
    lines with missing values.

    Each row in the input text file must have the same number of values to be
    able to read all values. If all rows do not have same number of values, a
    subset of up to n columns (where n is the least number of values present
    in all rows) can be read by specifying the columns via `usecols`.

    The strings produced by the Python float.hex method can be used as
    input for floats.

    Examples
    --------
    >>> import numpy as np
    >>> from io import StringIO   # StringIO behaves like a file object
    >>> c = StringIO("0 1\n2 3")
    >>> np.loadtxt(c)
    array([[0., 1.],
           [2., 3.]])

    >>> d = StringIO("M 21 72\nF 35 58")
    >>> np.loadtxt(d, dtype={'names': ('gender', 'age', 'weight'),
    ...                      'formats': ('S1', 'i4', 'f4')})
    array([(b'M', 21, 72.), (b'F', 35, 58.)],
          dtype=[('gender', 'S1'), ('age', '<i4'), ('weight', '<f4')])

    >>> c = StringIO("1,0,2\n3,0,4")
    >>> x, y = np.loadtxt(c, delimiter=',', usecols=(0, 2), unpack=True)
    >>> x
    array([1., 3.])
    >>> y
    array([2., 4.])

    The `converters` argument is used to specify functions to preprocess the
    text prior to parsing. `converters` can be a dictionary that maps
    preprocessing functions to each column:

    >>> s = StringIO("1.618, 2.296\n3.141, 4.669\n")
    >>> conv = {
    ...     0: lambda x: np.floor(float(x)),  # conversion fn for column 0
    ...     1: lambda x: np.ceil(float(x)),  # conversion fn for column 1
    ... }
    >>> np.loadtxt(s, delimiter=",", converters=conv)
    array([[1., 3.],
           [3., 5.]])

    `converters` can be a callable instead of a dictionary, in which case it
    is applied to all columns:

    >>> s = StringIO("0xDE 0xAD\n0xC0 0xDE")
    >>> import functools
    >>> conv = functools.partial(int, base=16)
    >>> np.loadtxt(s, converters=conv)
    array([[222., 173.],
           [192., 222.]])

    This example shows how `converters` can be used to convert a field
    with a trailing minus sign into a negative number.

    >>> s = StringIO("10.01 31.25-\n19.22 64.31\n17.57- 63.94")
    >>> def conv(fld):
    ...     return -float(fld[:-1]) if fld.endswith("-") else float(fld)
    ...
    >>> np.loadtxt(s, converters=conv)
    array([[ 10.01, -31.25],
           [ 19.22,  64.31],
           [-17.57,  63.94]])

    Using a callable as the converter can be particularly useful for handling
    values with different formatting, e.g. floats with underscores:

    >>> s = StringIO("1 2.7 100_000")
    >>> np.loadtxt(s, converters=float)
    array([1.e+00, 2.7e+00, 1.e+05])

    This idea can be extended to automatically handle values specified in
    many different formats, such as hex values:

    >>> def conv(val):
    ...     try:
    ...         return float(val)
    ...     except ValueError:
    ...         return float.fromhex(val)
    >>> s = StringIO("1, 2.5, 3_000, 0b4, 0x1.4000000000000p+2")
    >>> np.loadtxt(s, delimiter=",", converters=conv)
    array([1.0e+00, 2.5e+00, 3.0e+03, 1.8e+02, 5.0e+00])

    Or a format where the ``-`` sign comes after the number:

    >>> s = StringIO("10.01 31.25-\n19.22 64.31\n17.57- 63.94")
    >>> conv = lambda x: -float(x[:-1]) if x.endswith("-") else float(x)
    >>> np.loadtxt(s, converters=conv)
    array([[ 10.01, -31.25],
           [ 19.22,  64.31],
           [-17.57,  63.94]])

    Support for quoted fields is enabled with the `quotechar` parameter.
    Comment and delimiter characters are ignored when they appear within a
    quoted item delineated by `quotechar`:

    >>> s = StringIO('"alpha, #42", 10.0\n"beta, #64", 2.0\n')
    >>> dtype = np.dtype([("label", "U12"), ("value", float)])
    >>> np.loadtxt(s, dtype=dtype, delimiter=",", quotechar='"')
    array([('alpha, #42', 10.), ('beta, #64',  2.)],
          dtype=[('label', '<U12'), ('value', '<f8')])

    Quoted fields can be separated by multiple whitespace characters:

    >>> s = StringIO('"alpha, #42"       10.0\n"beta, #64" 2.0\n')
    >>> dtype = np.dtype([("label", "U12"), ("value", float)])
    >>> np.loadtxt(s, dtype=dtype, delimiter=None, quotechar='"')
    array([('alpha, #42', 10.), ('beta, #64',  2.)],
          dtype=[('label', '<U12'), ('value', '<f8')])

    Two consecutive quote characters within a quoted field are treated as a
    single escaped character:

    >>> s = StringIO('"Hello, my name is ""Monty""!"')
    >>> np.loadtxt(s, dtype="U", delimiter=",", quotechar='"')
    array('Hello, my name is "Monty"!', dtype='<U26')

    Read subset of columns when all rows do not contain equal number of values:

    >>> d = StringIO("1 2\n2 4\n3 9 12\n4 16 20")
    >>> np.loadtxt(d, usecols=(0, 1))
    array([[ 1.,  2.],
           [ 2.,  4.],
           [ 3.,  9.],
           [ 4., 16.]])

    """

    if like is not None:
        return _loadtxt_with_like(
            like, fname, dtype=dtype, comments=comments, delimiter=delimiter,
            converters=converters, skiprows=skiprows, usecols=usecols,
            unpack=unpack, ndmin=ndmin, encoding=encoding,
            max_rows=max_rows
        )

    if isinstance(delimiter, bytes):
        delimiter.decode("latin1")

    if dtype is None:
        dtype = np.float64

    comment = comments
    # Control character type conversions for Py3 convenience
    if comment is not None:
        if isinstance(comment, (str, bytes)):
            comment = [comment]
        comment = [
            x.decode('latin1') if isinstance(x, bytes) else x for x in comment]
    if isinstance(delimiter, bytes):
        delimiter = delimiter.decode('latin1')

    arr = _read(fname, dtype=dtype, comment=comment, delimiter=delimiter,
                converters=converters, skiplines=skiprows, usecols=usecols,
                unpack=unpack, ndmin=ndmin, encoding=encoding,
                max_rows=max_rows, quote=quotechar)

    return arr


_loadtxt_with_like = array_function_dispatch()(loadtxt)


def _savetxt_dispatcher(fname, X, fmt=None, delimiter=None, newline=None,
                        header=None, footer=None, comments=None,
                        encoding=None):
    return (X,)


@array_function_dispatch(_savetxt_dispatcher)
def savetxt(fname, X, fmt='%.18e', delimiter=' ', newline='\n', header='',
            footer='', comments='# ', encoding=None):
    """
    Save an array to a text file.

    Parameters
    ----------
    fname : filename, file handle or pathlib.Path
        If the filename ends in ``.gz``, the file is automatically saved in
        compressed gzip format.  `loadtxt` understands gzipped files
        transparently.
    X : 1D or 2D array_like
        Data to be saved to a text file.
    fmt : str or sequence of strs, optional
        A single format (%10.5f), a sequence of formats, or a
        multi-format string, e.g. 'Iteration %d -- %10.5f', in which
        case `delimiter` is ignored. For complex `X`, the legal options
        for `fmt` are:

        * a single specifier, ``fmt='%.4e'``, resulting in numbers formatted
          like ``' (%s+%sj)' % (fmt, fmt)``
        * a full string specifying every real and imaginary part, e.g.
          ``' %.4e %+.4ej %.4e %+.4ej %.4e %+.4ej'`` for 3 columns
        * a list of specifiers, one per column - in this case, the real
          and imaginary part must have separate specifiers,
          e.g. ``['%.3e + %.3ej', '(%.15e%+.15ej)']`` for 2 columns
    delimiter : str, optional
        String or character separating columns.
    newline : str, optional
        String or character separating lines.
    header : str, optional
        String that will be written at the beginning of the file.
    footer : str, optional
        String that will be written at the end of the file.
    comments : str, optional
        String that will be prepended to the ``header`` and ``footer`` strings,
        to mark them as comments. Default: '# ',  as expected by e.g.
        ``numpy.loadtxt``.
    encoding : {None, str}, optional
        Encoding used to encode the outputfile. Does not apply to output
        streams. If the encoding is something other than 'bytes' or 'latin1'
        you will not be able to load the file in NumPy versions < 1.14. Default
        is 'latin1'.

    See Also
    --------
    save : Save an array to a binary file in NumPy ``.npy`` format
    savez : Save several arrays into an uncompressed ``.npz`` archive
    savez_compressed : Save several arrays into a compressed ``.npz`` archive

    Notes
    -----
    Further explanation of the `fmt` parameter
    (``%[flag]width[.precision]specifier``):

    flags:
        ``-`` : left justify

        ``+`` : Forces to precede result with + or -.

        ``0`` : Left pad the number with zeros instead of space (see width).

    width:
        Minimum number of characters to be printed. The value is not truncated
        if it has more characters.

    precision:
        - For integer specifiers (eg. ``d,i,o,x``), the minimum number of
          digits.
        - For ``e, E`` and ``f`` specifiers, the number of digits to print
          after the decimal point.
        - For ``g`` and ``G``, the maximum number of significant digits.
        - For ``s``, the maximum number of characters.

    specifiers:
        ``c`` : character

        ``d`` or ``i`` : signed decimal integer

        ``e`` or ``E`` : scientific notation with ``e`` or ``E``.

        ``f`` : decimal floating point

        ``g,G`` : use the shorter of ``e,E`` or ``f``

        ``o`` : signed octal

        ``s`` : string of characters

        ``u`` : unsigned decimal integer

        ``x,X`` : unsigned hexadecimal integer

    This explanation of ``fmt`` is not complete, for an exhaustive
    specification see [1]_.

    References
    ----------
    .. [1] `Format Specification Mini-Language
           <https://docs.python.org/library/string.html#format-specification-mini-language>`_,
           Python Documentation.

    Examples
    --------
    >>> import numpy as np
    >>> x = y = z = np.arange(0.0,5.0,1.0)
    >>> np.savetxt('test.out', x, delimiter=',')   # X is an array
    >>> np.savetxt('test.out', (x,y,z))   # x,y,z equal sized 1D arrays
    >>> np.savetxt('test.out', x, fmt='%1.4e')   # use exponential notation

    """

    class WriteWrap:
        """Convert to bytes on bytestream inputs.

        """
        def __init__(self, fh, encoding):
            self.fh = fh
            self.encoding = encoding
            self.do_write = self.first_write

        def close(self):
            self.fh.close()

        def write(self, v):
            self.do_write(v)

        def write_bytes(self, v):
            if isinstance(v, bytes):
                self.fh.write(v)
            else:
                self.fh.write(v.encode(self.encoding))

        def write_normal(self, v):
            self.fh.write(asunicode(v))

        def first_write(self, v):
            try:
                self.write_normal(v)
                self.write = self.write_normal
            except TypeError:
                # input is probably a bytestream
                self.write_bytes(v)
                self.write = self.write_bytes

    own_fh = False
    if isinstance(fname, os.PathLike):
        fname = os.fspath(fname)
    if _is_string_like(fname):
        # datasource doesn't support creating a new file ...
        open(fname, 'wt').close()
        fh = np.lib._datasource.open(fname, 'wt', encoding=encoding)
        own_fh = True
    elif hasattr(fname, 'write'):
        # wrap to handle byte output streams
        fh = WriteWrap(fname, encoding or 'latin1')
    else:
        raise ValueError('fname must be a string or file handle')

    try:
        X = np.asarray(X)

        # Handle 1-dimensional arrays
        if X.ndim == 0 or X.ndim > 2:
            raise ValueError(
                "Expected 1D or 2D array, got %dD array instead" % X.ndim)
        elif X.ndim == 1:
            # Common case -- 1d array of numbers
            if X.dtype.names is None:
                X = np.atleast_2d(X).T
                ncol = 1

            # Complex dtype -- each field indicates a separate column
            else:
                ncol = len(X.dtype.names)
        else:
            ncol = X.shape[1]

        iscomplex_X = np.iscomplexobj(X)
        # `fmt` can be a string with multiple insertion points or a
        # list of formats.  E.g. '%10.5f\t%10d' or ('%10.5f', '$10d')
        if type(fmt) in (list, tuple):
            if len(fmt) != ncol:
                raise AttributeError(f'fmt has wrong shape.  {str(fmt)}')
            format = delimiter.join(fmt)
        elif isinstance(fmt, str):
            n_fmt_chars = fmt.count('%')
            error = ValueError(f'fmt has wrong number of % formats:  {fmt}')
            if n_fmt_chars == 1:
                if iscomplex_X:
                    fmt = [f' ({fmt}+{fmt}j)', ] * ncol
                else:
                    fmt = [fmt, ] * ncol
                format = delimiter.join(fmt)
            elif iscomplex_X and n_fmt_chars != (2 * ncol):
                raise error
            elif ((not iscomplex_X) and n_fmt_chars != ncol):
                raise error
            else:
                format = fmt
        else:
            raise ValueError(f'invalid fmt: {fmt!r}')

        if len(header) > 0:
            header = header.replace('\n', '\n' + comments)
            fh.write(comments + header + newline)
        if iscomplex_X:
            for row in X:
                row2 = []
                for number in row:
                    row2.extend((number.real, number.imag))
                s = format % tuple(row2) + newline
                fh.write(s.replace('+-', '-'))
        else:
            for row in X:
                try:
                    v = format % tuple(row) + newline
                except TypeError as e:
                    raise TypeError("Mismatch between array dtype ('%s') and "
                                    "format specifier ('%s')"
                                    % (str(X.dtype), format)) from e
                fh.write(v)

        if len(footer) > 0:
            footer = footer.replace('\n', '\n' + comments)
            fh.write(comments + footer + newline)
    finally:
        if own_fh:
            fh.close()


@set_module('numpy')
def fromregex(file, regexp, dtype, encoding=None):
    r"""
    Construct an array from a text file, using regular expression parsing.

    The returned array is always a structured array, and is constructed from
    all matches of the regular expression in the file. Groups in the regular
    expression are converted to fields of the structured array.

    Parameters
    ----------
    file : file, str, or pathlib.Path
        Filename or file object to read.

        .. versionchanged:: 1.22.0
            Now accepts `os.PathLike` implementations.

    regexp : str or regexp
        Regular expression used to parse the file.
        Groups in the regular expression correspond to fields in the dtype.
    dtype : dtype or list of dtypes
        Dtype for the structured array; must be a structured datatype.
    encoding : str, optional
        Encoding used to decode the inputfile. Does not apply to input streams.

    Returns
    -------
    output : ndarray
        The output array, containing the part of the content of `file` that
        was matched by `regexp`. `output` is always a structured array.

    Raises
    ------
    TypeError
        When `dtype` is not a valid dtype for a structured array.

    See Also
    --------
    fromstring, loadtxt

    Notes
    -----
    Dtypes for structured arrays can be specified in several forms, but all
    forms specify at least the data type and field name. For details see
    `basics.rec`.

    Examples
    --------
    >>> import numpy as np
    >>> from io import StringIO
    >>> text = StringIO("1312 foo\n1534  bar\n444   qux")

    >>> regexp = r"(\d+)\s+(...)"  # match [digits, whitespace, anything]
    >>> output = np.fromregex(text, regexp,
    ...                       [('num', np.int64), ('key', 'S3')])
    >>> output
    array([(1312, b'foo'), (1534, b'bar'), ( 444, b'qux')],
          dtype=[('num', '<i8'), ('key', 'S3')])
    >>> output['num']
    array([1312, 1534,  444])

    """
    own_fh = False
    if not hasattr(file, "read"):
        file = os.fspath(file)
        file = np.lib._datasource.open(file, 'rt', encoding=encoding)
        own_fh = True

    try:
        if not isinstance(dtype, np.dtype):
            dtype = np.dtype(dtype)
        if dtype.names is None:
            raise TypeError('dtype must be a structured datatype.')

        content = file.read()
        if isinstance(content, bytes) and isinstance(regexp, str):
            regexp = asbytes(regexp)

        if not hasattr(regexp, 'match'):
            regexp = re.compile(regexp)
        seq = regexp.findall(content)
        if seq and not isinstance(seq[0], tuple):
            # Only one group is in the regexp.
            # Create the new array as a single data-type and then
            #   re-interpret as a single-field structured array.
            newdtype = np.dtype(dtype[dtype.names[0]])
            output = np.array(seq, dtype=newdtype)
            output.dtype = dtype
        else:
            output = np.array(seq, dtype=dtype)

        return output
    finally:
        if own_fh:
            file.close()


#####--------------------------------------------------------------------------
#---- --- ASCII functions ---
#####--------------------------------------------------------------------------


@finalize_array_function_like
@set_module('numpy')
def genfromtxt(fname, dtype=float, comments='#', delimiter=None,
               skip_header=0, skip_footer=0, converters=None,
               missing_values=None, filling_values=None, usecols=None,
               names=None, excludelist=None,
               deletechars=''.join(sorted(NameValidator.defaultdeletechars)),  # noqa: B008
               replace_space='_', autostrip=False, case_sensitive=True,
               defaultfmt="f%i", unpack=None, usemask=False, loose=True,
               invalid_raise=True, max_rows=None, encoding=None,
               *, ndmin=0, like=None):
    """
    Load data from a text file, with missing values handled as specified.

    Each line past the first `skip_header` lines is split at the `delimiter`
    character, and characters following the `comments` character are discarded.

    Parameters
    ----------
    fname : file, str, pathlib.Path, list of str, generator
        File, filename, list, or generator to read.  If the filename
        extension is ``.gz`` or ``.bz2``, the file is first decompressed. Note
        that generators must return bytes or strings. The strings
        in a list or produced by a generator are treated as lines.
    dtype : dtype, optional
        Data type of the resulting array.
        If None, the dtypes will be determined by the contents of each
        column, individually.
    comments : str, optional
        The character used to indicate the start of a comment.
        All the characters occurring on a line after a comment are discarded.
    delimiter : str, int, or sequence, optional
        The string used to separate values.  By default, any consecutive
        whitespaces act as delimiter.  An integer or sequence of integers
        can also be provided as width(s) of each field.
    skiprows : int, optional
        `skiprows` was removed in numpy 1.10. Please use `skip_header` instead.
    skip_header : int, optional
        The number of lines to skip at the beginning of the file.
    skip_footer : int, optional
        The number of lines to skip at the end of the file.
    converters : variable, optional
        The set of functions that convert the data of a column to a value.
        The converters can also be used to provide a default value
        for missing data: ``converters = {3: lambda s: float(s or 0)}``.
    missing : variable, optional
        `missing` was removed in numpy 1.10. Please use `missing_values`
        instead.
    missing_values : variable, optional
        The set of strings corresponding to missing data.
    filling_values : variable, optional
        The set of values to be used as default when the data are missing.
    usecols : sequence, optional
        Which columns to read, with 0 being the first.  For example,
        ``usecols = (1, 4, 5)`` will extract the 2nd, 5th and 6th columns.
    names : {None, True, str, sequence}, optional
        If `names` is True, the field names are read from the first line after
        the first `skip_header` lines. This line can optionally be preceded
        by a comment delimiter. Any content before the comment delimiter is
        discarded. If `names` is a sequence or a single-string of
        comma-separated names, the names will be used to define the field
        names in a structured dtype. If `names` is None, the names of the
        dtype fields will be used, if any.
    excludelist : sequence, optional
        A list of names to exclude. This list is appended to the default list
        ['return','file','print']. Excluded names are appended with an
        underscore: for example, `file` would become `file_`.
    deletechars : str, optional
        A string combining invalid characters that must be deleted from the
        names.
    defaultfmt : str, optional
        A format used to define default field names, such as "f%i" or "f_%02i".
    autostrip : bool, optional
        Whether to automatically strip white spaces from the variables.
    replace_space : char, optional
        Character(s) used in replacement of white spaces in the variable
        names. By default, use a '_'.
    case_sensitive : {True, False, 'upper', 'lower'}, optional
        If True, field names are case sensitive.
        If False or 'upper', field names are converted to upper case.
        If 'lower', field names are converted to lower case.
    unpack : bool, optional
        If True, the returned array is transposed, so that arguments may be
        unpacked using ``x, y, z = genfromtxt(...)``.  When used with a
        structured data-type, arrays are returned for each field.
        Default is False.
    usemask : bool, optional
        If True, return a masked array.
        If False, return a regular array.
    loose : bool, optional
        If True, do not raise errors for invalid values.
    invalid_raise : bool, optional
        If True, an exception is raised if an inconsistency is detected in the
        number of columns.
        If False, a warning is emitted and the offending lines are skipped.
    max_rows : int,  optional
        The maximum number of rows to read. Must not be used with skip_footer
        at the same time.  If given, the value must be at least 1. Default is
        to read the entire file.
    encoding : str, optional
        Encoding used to decode the inputfile. Does not apply when `fname`
        is a file object. The special value 'bytes' enables backward
        compatibility workarounds that ensure that you receive byte arrays
        when possible and passes latin1 encoded strings to converters.
        Override this value to receive unicode arrays and pass strings
        as input to converters.  If set to None the system default is used.
        The default value is 'bytes'.

        .. versionchanged:: 2.0
            Before NumPy 2, the default was ``'bytes'`` for Python 2
            compatibility. The default is now ``None``.

    ndmin : int, optional
        Same parameter as `loadtxt`

        .. versionadded:: 1.23.0
    ${ARRAY_FUNCTION_LIKE}

        .. versionadded:: 1.20.0

    Returns
    -------
    out : ndarray
        Data read from the text file. If `usemask` is True, this is a
        masked array.

    See Also
    --------
    numpy.loadtxt : equivalent function when no data is missing.

    Notes
    -----
    * When spaces are used as delimiters, or when no delimiter has been given
      as input, there should not be any missing data between two fields.
    * When variables are named (either by a flexible dtype or with a `names`
      sequence), there must not be any header in the file (else a ValueError
      exception is raised).
    * Individual values are not stripped of spaces by default.
      When using a custom converter, make sure the function does remove spaces.
    * Custom converters may receive unexpected values due to dtype
      discovery.

    References
    ----------
    .. [1] NumPy User Guide, section `I/O with NumPy
           <https://docs.scipy.org/doc/numpy/user/basics.io.genfromtxt.html>`_.

    Examples
    --------
    >>> from io import StringIO
    >>> import numpy as np

    Comma delimited file with mixed dtype

    >>> s = StringIO("1,1.3,abcde")
    >>> data = np.genfromtxt(s, dtype=[('myint','i8'),('myfloat','f8'),
    ... ('mystring','S5')], delimiter=",")
    >>> data
    array((1, 1.3, b'abcde'),
          dtype=[('myint', '<i8'), ('myfloat', '<f8'), ('mystring', 'S5')])

    Using dtype = None

    >>> _ = s.seek(0) # needed for StringIO example only
    >>> data = np.genfromtxt(s, dtype=None,
    ... names = ['myint','myfloat','mystring'], delimiter=",")
    >>> data
    array((1, 1.3, 'abcde'),
          dtype=[('myint', '<i8'), ('myfloat', '<f8'), ('mystring', '<U5')])

    Specifying dtype and names

    >>> _ = s.seek(0)
    >>> data = np.genfromtxt(s, dtype="i8,f8,S5",
    ... names=['myint','myfloat','mystring'], delimiter=",")
    >>> data
    array((1, 1.3, b'abcde'),
          dtype=[('myint', '<i8'), ('myfloat', '<f8'), ('mystring', 'S5')])

    An example with fixed-width columns

    >>> s = StringIO("11.3abcde")
    >>> data = np.genfromtxt(s, dtype=None, names=['intvar','fltvar','strvar'],
    ...     delimiter=[1,3,5])
    >>> data
    array((1, 1.3, 'abcde'),
          dtype=[('intvar', '<i8'), ('fltvar', '<f8'), ('strvar', '<U5')])

    An example to show comments

    >>> f = StringIO('''
    ... text,# of chars
    ... hello world,11
    ... numpy,5''')
    >>> np.genfromtxt(f, dtype='S12,S12', delimiter=',')
    array([(b'text', b''), (b'hello world', b'11'), (b'numpy', b'5')],
      dtype=[('f0', 'S12'), ('f1', 'S12')])

    """

    if like is not None:
        return _genfromtxt_with_like(
            like, fname, dtype=dtype, comments=comments, delimiter=delimiter,
            skip_header=skip_header, skip_footer=skip_footer,
            converters=converters, missing_values=missing_values,
            filling_values=filling_values, usecols=usecols, names=names,
            excludelist=excludelist, deletechars=deletechars,
            replace_space=replace_space, autostrip=autostrip,
            case_sensitive=case_sensitive, defaultfmt=defaultfmt,
            unpack=unpack, usemask=usemask, loose=loose,
            invalid_raise=invalid_raise, max_rows=max_rows, encoding=encoding,
            ndmin=ndmin,
        )

    _ensure_ndmin_ndarray_check_param(ndmin)

    if max_rows is not None:
        if skip_footer:
            raise ValueError(
                    "The keywords 'skip_footer' and 'max_rows' can not be "
                    "specified at the same time.")
        if max_rows < 1:
            raise ValueError("'max_rows' must be at least 1.")

    if usemask:
        from numpy.ma import MaskedArray, make_mask_descr
    # Check the input dictionary of converters
    user_converters = converters or {}
    if not isinstance(user_converters, dict):
        raise TypeError(
            "The input argument 'converter' should be a valid dictionary "
            "(got '%s' instead)" % type(user_converters))

    if encoding == 'bytes':
        encoding = None
        byte_converters = True
    else:
        byte_converters = False

    # Initialize the filehandle, the LineSplitter and the NameValidator
    if isinstance(fname, os.PathLike):
        fname = os.fspath(fname)
    if isinstance(fname, str):
        fid = np.lib._datasource.open(fname, 'rt', encoding=encoding)
        fid_ctx = contextlib.closing(fid)
    else:
        fid = fname
        fid_ctx = contextlib.nullcontext(fid)
    try:
        fhd = iter(fid)
    except TypeError as e:
        raise TypeError(
            "fname must be a string, a filehandle, a sequence of strings,\n"
            f"or an iterator of strings. Got {type(fname)} instead."
        ) from e
    with fid_ctx:
        split_line = LineSplitter(delimiter=delimiter, comments=comments,
                                  autostrip=autostrip, encoding=encoding)
        validate_names = NameValidator(excludelist=excludelist,
                                       deletechars=deletechars,
                                       case_sensitive=case_sensitive,
                                       replace_space=replace_space)

        # Skip the first `skip_header` rows
        try:
            for i in range(skip_header):
                next(fhd)

            # Keep on until we find the first valid values
            first_values = None

            while not first_values:
                first_line = _decode_line(next(fhd), encoding)
                if (names is True) and (comments is not None):
                    if comments in first_line:
                        first_line = (
                            ''.join(first_line.split(comments)[1:]))
                first_values = split_line(first_line)
        except StopIteration:
            # return an empty array if the datafile is empty
            first_line = ''
            first_values = []
            warnings.warn(
                f'genfromtxt: Empty input file: "{fname}"', stacklevel=2
            )

        # Should we take the first values as names ?
        if names is True:
            fval = first_values[0].strip()
            if comments is not None:
                if fval in comments:
                    del first_values[0]

        # Check the columns to use: make sure `usecols` is a list
        if usecols is not None:
            try:
                usecols = [_.strip() for _ in usecols.split(",")]
            except AttributeError:
                try:
                    usecols = list(usecols)
                except TypeError:
                    usecols = [usecols, ]
        nbcols = len(usecols or first_values)

        # Check the names and overwrite the dtype.names if needed
        if names is True:
            names = validate_names([str(_.strip()) for _ in first_values])
            first_line = ''
        elif _is_string_like(names):
            names = validate_names([_.strip() for _ in names.split(',')])
        elif names:
            names = validate_names(names)
        # Get the dtype
        if dtype is not None:
            dtype = easy_dtype(dtype, defaultfmt=defaultfmt, names=names,
                               excludelist=excludelist,
                               deletechars=deletechars,
                               case_sensitive=case_sensitive,
                               replace_space=replace_space)
        # Make sure the names is a list (for 2.5)
        if names is not None:
            names = list(names)

        if usecols:
            for (i, current) in enumerate(usecols):
                # if usecols is a list of names, convert to a list of indices
                if _is_string_like(current):
                    usecols[i] = names.index(current)
                elif current < 0:
                    usecols[i] = current + len(first_values)
            # If the dtype is not None, make sure we update it
            if (dtype is not None) and (len(dtype) > nbcols):
                descr = dtype.descr
                dtype = np.dtype([descr[_] for _ in usecols])
                names = list(dtype.names)
            # If `names` is not None, update the names
            elif (names is not None) and (len(names) > nbcols):
                names = [names[_] for _ in usecols]
        elif (names is not None) and (dtype is not None):
            names = list(dtype.names)

        # Process the missing values ...............................
        # Rename missing_values for convenience
        user_missing_values = missing_values or ()
        if isinstance(user_missing_values, bytes):
            user_missing_values = user_missing_values.decode('latin1')

        # Define the list of missing_values (one column: one list)
        missing_values = [[''] for _ in range(nbcols)]

        # We have a dictionary: process it field by field
        if isinstance(user_missing_values, dict):
            # Loop on the items
            for (key, val) in user_missing_values.items():
                # Is the key a string ?
                if _is_string_like(key):
                    try:
                        # Transform it into an integer
                        key = names.index(key)
                    except ValueError:
                        # We couldn't find it: the name must have been dropped
                        continue
                # Redefine the key as needed if it's a column number
                if usecols:
                    try:
                        key = usecols.index(key)
                    except ValueError:
                        pass
                # Transform the value as a list of string
                if isinstance(val, (list, tuple)):
                    val = [str(_) for _ in val]
                else:
                    val = [str(val), ]
                # Add the value(s) to the current list of missing
                if key is None:
                    # None acts as default
                    for miss in missing_values:
                        miss.extend(val)
                else:
                    missing_values[key].extend(val)
        # We have a sequence : each item matches a column
        elif isinstance(user_missing_values, (list, tuple)):
            for (value, entry) in zip(user_missing_values, missing_values):
                value = str(value)
                if value not in entry:
                    entry.append(value)
        # We have a string : apply it to all entries
        elif isinstance(user_missing_values, str):
            user_value = user_missing_values.split(",")
            for entry in missing_values:
                entry.extend(user_value)
        # We have something else: apply it to all entries
        else:
            for entry in missing_values:
                entry.extend([str(user_missing_values)])

        # Process the filling_values ...............................
        # Rename the input for convenience
        user_filling_values = filling_values
        if user_filling_values is None:
            user_filling_values = []
        # Define the default
        filling_values = [None] * nbcols
        # We have a dictionary : update each entry individually
        if isinstance(user_filling_values, dict):
            for (key, val) in user_filling_values.items():
                if _is_string_like(key):
                    try:
                        # Transform it into an integer
                        key = names.index(key)
                    except ValueError:
                        # We couldn't find it: the name must have been dropped
                        continue
                # Redefine the key if it's a column number
                # and usecols is defined
                if usecols:
                    try:
                        key = usecols.index(key)
                    except ValueError:
                        pass
                # Add the value to the list
                filling_values[key] = val
        # We have a sequence : update on a one-to-one basis
        elif isinstance(user_filling_values, (list, tuple)):
            n = len(user_filling_values)
            if (n <= nbcols):
                filling_values[:n] = user_filling_values
            else:
                filling_values = user_filling_values[:nbcols]
        # We have something else : use it for all entries
        else:
            filling_values = [user_filling_values] * nbcols

        # Initialize the converters ................................
        if dtype is None:
            # Note: we can't use a [...]*nbcols, as we would have 3 times
            # the same converter, instead of 3 different converters.
            converters = [
                StringConverter(None, missing_values=miss, default=fill)
                for (miss, fill) in zip(missing_values, filling_values)
            ]
        else:
            dtype_flat = flatten_dtype(dtype, flatten_base=True)
            # Initialize the converters
            if len(dtype_flat) > 1:
                # Flexible type : get a converter from each dtype
                zipit = zip(dtype_flat, missing_values, filling_values)
                converters = [StringConverter(dt,
                                              locked=True,
                                              missing_values=miss,
                                              default=fill)
                              for (dt, miss, fill) in zipit]
            else:
                # Set to a default converter (but w/ different missing values)
                zipit = zip(missing_values, filling_values)
                converters = [StringConverter(dtype,
                                              locked=True,
                                              missing_values=miss,
                                              default=fill)
                              for (miss, fill) in zipit]
        # Update the converters to use the user-defined ones
        uc_update = []
        for (j, conv) in user_converters.items():
            # If the converter is specified by column names,
            # use the index instead
            if _is_string_like(j):
                try:
                    j = names.index(j)
                    i = j
                except ValueError:
                    continue
            elif usecols:
                try:
                    i = usecols.index(j)
                except ValueError:
                    # Unused converter specified
                    continue
            else:
                i = j
            # Find the value to test - first_line is not filtered by usecols:
            if len(first_line):
                testing_value = first_values[j]
            else:
                testing_value = None
            if conv is bytes:
                user_conv = asbytes
            elif byte_converters:
                # Converters may use decode to workaround numpy's old
                # behavior, so encode the string again before passing
                # to the user converter.
                def tobytes_first(x, conv):
                    if type(x) is bytes:
                        return conv(x)
                    return conv(x.encode("latin1"))
                user_conv = functools.partial(tobytes_first, conv=conv)
            else:
                user_conv = conv
            converters[i].update(user_conv, locked=True,
                                 testing_value=testing_value,
                                 default=filling_values[i],
                                 missing_values=missing_values[i],)
            uc_update.append((i, user_conv))
        # Make sure we have the corrected keys in user_converters...
        user_converters.update(uc_update)

        # Fixme: possible error as following variable never used.
        # miss_chars = [_.missing_values for _ in converters]

        # Initialize the output lists ...
        # ... rows
        rows = []
        append_to_rows = rows.append
        # ... masks
        if usemask:
            masks = []
            append_to_masks = masks.append
        # ... invalid
        invalid = []
        append_to_invalid = invalid.append

        # Parse each line
        for (i, line) in enumerate(itertools.chain([first_line, ], fhd)):
            values = split_line(line)
            nbvalues = len(values)
            # Skip an empty line
            if nbvalues == 0:
                continue
            if usecols:
                # Select only the columns we need
                try:
                    values = [values[_] for _ in usecols]
                except IndexError:
                    append_to_invalid((i + skip_header + 1, nbvalues))
                    continue
            elif nbvalues != nbcols:
                append_to_invalid((i + skip_header + 1, nbvalues))
                continue
            # Store the values
            append_to_rows(tuple(values))
            if usemask:
                append_to_masks(tuple(v.strip() in m
                                       for (v, m) in zip(values,
                                                         missing_values)))
            if len(rows) == max_rows:
                break

    # Upgrade the converters (if needed)
    if dtype is None:
        for (i, converter) in enumerate(converters):
            current_column = [itemgetter(i)(_m) for _m in rows]
            try:
                converter.iterupgrade(current_column)
            except ConverterLockError:
                errmsg = f"Converter #{i} is locked and cannot be upgraded: "
                current_column = map(itemgetter(i), rows)
                for (j, value) in enumerate(current_column):
                    try:
                        converter.upgrade(value)
                    except (ConverterError, ValueError):
                        line_number = j + 1 + skip_header
                        errmsg += f"(occurred line #{line_number} for value '{value}')"
                        raise ConverterError(errmsg)

    # Check that we don't have invalid values
    nbinvalid = len(invalid)
    if nbinvalid > 0:
        nbrows = len(rows) + nbinvalid - skip_footer
        # Construct the error message
        template = f"    Line #%i (got %i columns instead of {nbcols})"
        if skip_footer > 0:
            nbinvalid_skipped = len([_ for _ in invalid
                                     if _[0] > nbrows + skip_header])
            invalid = invalid[:nbinvalid - nbinvalid_skipped]
            skip_footer -= nbinvalid_skipped
#
#            nbrows -= skip_footer
#            errmsg = [template % (i, nb)
#                      for (i, nb) in invalid if i < nbrows]
#        else:
        errmsg = [template % (i, nb)
                  for (i, nb) in invalid]
        if len(errmsg):
            errmsg.insert(0, "Some errors were detected !")
            errmsg = "\n".join(errmsg)
            # Raise an exception ?
            if invalid_raise:
                raise ValueError(errmsg)
            # Issue a warning ?
            else:
                warnings.warn(errmsg, ConversionWarning, stacklevel=2)

    # Strip the last skip_footer data
    if skip_footer > 0:
        rows = rows[:-skip_footer]
        if usemask:
            masks = masks[:-skip_footer]

    # Convert each value according to the converter:
    # We want to modify the list in place to avoid creating a new one...
    if loose:
        rows = list(
            zip(*[[conv._loose_call(_r) for _r in map(itemgetter(i), rows)]
                  for (i, conv) in enumerate(converters)]))
    else:
        rows = list(
            zip(*[[conv._strict_call(_r) for _r in map(itemgetter(i), rows)]
                  for (i, conv) in enumerate(converters)]))

    # Reset the dtype
    data = rows
    if dtype is None:
        # Get the dtypes from the types of the converters
        column_types = [conv.type for conv in converters]
        # Find the columns with strings...
        strcolidx = [i for (i, v) in enumerate(column_types)
                     if v == np.str_]

        if byte_converters and strcolidx:
            # convert strings back to bytes for backward compatibility
            warnings.warn(
                "Reading unicode strings without specifying the encoding "
                "argument is deprecated. Set the encoding, use None for the "
                "system default.",
                np.exceptions.VisibleDeprecationWarning, stacklevel=2)

            def encode_unicode_cols(row_tup):
                row = list(row_tup)
                for i in strcolidx:
                    row[i] = row[i].encode('latin1')
                return tuple(row)

            try:
                data = [encode_unicode_cols(r) for r in data]
            except UnicodeEncodeError:
                pass
            else:
                for i in strcolidx:
                    column_types[i] = np.bytes_

        # Update string types to be the right length
        sized_column_types = column_types.copy()
        for i, col_type in enumerate(column_types):
            if np.issubdtype(col_type, np.character):
                n_chars = max(len(row[i]) for row in data)
                sized_column_types[i] = (col_type, n_chars)

        if names is None:
            # If the dtype is uniform (before sizing strings)
            base = {
                c_type
                for c, c_type in zip(converters, column_types)
                if c._checked}
            if len(base) == 1:
                uniform_type, = base
                (ddtype, mdtype) = (uniform_type, bool)
            else:
                ddtype = [(defaultfmt % i, dt)
                          for (i, dt) in enumerate(sized_column_types)]
                if usemask:
                    mdtype = [(defaultfmt % i, bool)
                              for (i, dt) in enumerate(sized_column_types)]
        else:
            ddtype = list(zip(names, sized_column_types))
            mdtype = list(zip(names, [bool] * len(sized_column_types)))
        output = np.array(data, dtype=ddtype)
        if usemask:
            outputmask = np.array(masks, dtype=mdtype)
    else:
        # Overwrite the initial dtype names if needed
        if names and dtype.names is not None:
            dtype.names = names
        # Case 1. We have a structured type
        if len(dtype_flat) > 1:
            # Nested dtype, eg [('a', int), ('b', [('b0', int), ('b1', 'f4')])]
            # First, create the array using a flattened dtype:
            # [('a', int), ('b1', int), ('b2', float)]
            # Then, view the array using the specified dtype.
            if 'O' in (_.char for _ in dtype_flat):
                if has_nested_fields(dtype):
                    raise NotImplementedError(
                        "Nested fields involving objects are not supported...")
                else:
                    output = np.array(data, dtype=dtype)
            else:
                rows = np.array(data, dtype=[('', _) for _ in dtype_flat])
                output = rows.view(dtype)
            # Now, process the rowmasks the same way
            if usemask:
                rowmasks = np.array(
                    masks, dtype=np.dtype([('', bool) for t in dtype_flat]))
                # Construct the new dtype
                mdtype = make_mask_descr(dtype)
                outputmask = rowmasks.view(mdtype)
        # Case #2. We have a basic dtype
        else:
            # We used some user-defined converters
            if user_converters:
                ishomogeneous = True
                descr = []
                for i, ttype in enumerate([conv.type for conv in converters]):
                    # Keep the dtype of the current converter
                    if i in user_converters:
                        ishomogeneous &= (ttype == dtype.type)
                        if np.issubdtype(ttype, np.character):
                            ttype = (ttype, max(len(row[i]) for row in data))
                        descr.append(('', ttype))
                    else:
                        descr.append(('', dtype))
                # So we changed the dtype ?
                if not ishomogeneous:
                    # We have more than one field
                    if len(descr) > 1:
                        dtype = np.dtype(descr)
                    # We have only one field: drop the name if not needed.
                    else:
                        dtype = np.dtype(ttype)
            #
            output = np.array(data, dtype)
            if usemask:
                if dtype.names is not None:
                    mdtype = [(_, bool) for _ in dtype.names]
                else:
                    mdtype = bool
                outputmask = np.array(masks, dtype=mdtype)
    # Try to take care of the missing data we missed
    names = output.dtype.names
    if usemask and names:
        for (name, conv) in zip(names, converters):
            missing_values = [conv(_) for _ in conv.missing_values
                              if _ != '']
            for mval in missing_values:
                outputmask[name] |= (output[name] == mval)
    # Construct the final array
    if usemask:
        output = output.view(MaskedArray)
        output._mask = outputmask

    output = _ensure_ndmin_ndarray(output, ndmin=ndmin)

    if unpack:
        if names is None:
            return output.T
        elif len(names) == 1:
            # squeeze single-name dtypes too
            return output[names[0]]
        else:
            # For structured arrays with multiple fields,
            # return an array for each field.
            return [output[field] for field in names]
    return output


_genfromtxt_with_like = array_function_dispatch()(genfromtxt)


def recfromtxt(fname, **kwargs):
    """
    Load ASCII data from a file and return it in a record array.

    If ``usemask=False`` a standard `recarray` is returned,
    if ``usemask=True`` a MaskedRecords array is returned.

    .. deprecated:: 2.0
        Use `numpy.genfromtxt` instead.

    Parameters
    ----------
    fname, kwargs : For a description of input parameters, see `genfromtxt`.

    See Also
    --------
    numpy.genfromtxt : generic function

    Notes
    -----
    By default, `dtype` is None, which means that the data-type of the output
    array will be determined from the data.

    """

    # Deprecated in NumPy 2.0, 2023-07-11
    warnings.warn(
        "`recfromtxt` is deprecated, "
        "use `numpy.genfromtxt` instead."
        "(deprecated in NumPy 2.0)",
        DeprecationWarning,
        stacklevel=2
    )

    kwargs.setdefault("dtype", None)
    usemask = kwargs.get('usemask', False)
    output = genfromtxt(fname, **kwargs)
    if usemask:
        from numpy.ma.mrecords import MaskedRecords
        output = output.view(MaskedRecords)
    else:
        output = output.view(np.recarray)
    return output


def recfromcsv(fname, **kwargs):
    """
    Load ASCII data stored in a comma-separated file.

    The returned array is a record array (if ``usemask=False``, see
    `recarray`) or a masked record array (if ``usemask=True``,
    see `ma.mrecords.MaskedRecords`).

    .. deprecated:: 2.0
        Use `numpy.genfromtxt` with comma as `delimiter` instead.

    Parameters
    ----------
    fname, kwargs : For a description of input parameters, see `genfromtxt`.

    See Also
    --------
    numpy.genfromtxt : generic function to load ASCII data.

    Notes
    -----
    By default, `dtype` is None, which means that the data-type of the output
    array will be determined from the data.

    """

    # Deprecated in NumPy 2.0, 2023-07-11
    warnings.warn(
        "`recfromcsv` is deprecated, "
        "use `numpy.genfromtxt` with comma as `delimiter` instead. "
        "(deprecated in NumPy 2.0)",
        DeprecationWarning,
        stacklevel=2
    )

    # Set default kwargs for genfromtxt as relevant to csv import.
    kwargs.setdefault("case_sensitive", "lower")
    kwargs.setdefault("names", True)
    kwargs.setdefault("delimiter", ",")
    kwargs.setdefault("dtype", None)
    output = genfromtxt(fname, **kwargs)

    usemask = kwargs.get("usemask", False)
    if usemask:
        from numpy.ma.mrecords import MaskedRecords
        output = output.view(MaskedRecords)
    else:
        output = output.view(np.recarray)
    return output

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\_npyio_impl.py ===
"""
IO related functions.
"""
import contextlib
import functools
import itertools
import operator
import os
import pickle
import re
import warnings
import weakref
from collections.abc import Mapping
from operator import itemgetter

import numpy as np
from numpy._core import overrides
from numpy._core._multiarray_umath import _load_from_filelike
from numpy._core.multiarray import packbits, unpackbits
from numpy._core.overrides import finalize_array_function_like, set_module
from numpy._utils import asbytes, asunicode

from . import format
from ._datasource import DataSource  # noqa: F401
from ._format_impl import _MAX_HEADER_SIZE
from ._iotools import (
    ConversionWarning,
    ConverterError,
    ConverterLockError,
    LineSplitter,
    NameValidator,
    StringConverter,
    _decode_line,
    _is_string_like,
    easy_dtype,
    flatten_dtype,
    has_nested_fields,
)

__all__ = [
    'savetxt', 'loadtxt', 'genfromtxt', 'load', 'save', 'savez',
    'savez_compressed', 'packbits', 'unpackbits', 'fromregex'
    ]


array_function_dispatch = functools.partial(
    overrides.array_function_dispatch, module='numpy')


class BagObj:
    """
    BagObj(obj)

    Convert attribute look-ups to getitems on the object passed in.

    Parameters
    ----------
    obj : class instance
        Object on which attribute look-up is performed.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.lib._npyio_impl import BagObj as BO
    >>> class BagDemo:
    ...     def __getitem__(self, key): # An instance of BagObj(BagDemo)
    ...                                 # will call this method when any
    ...                                 # attribute look-up is required
    ...         result = "Doesn't matter what you want, "
    ...         return result + "you're gonna get this"
    ...
    >>> demo_obj = BagDemo()
    >>> bagobj = BO(demo_obj)
    >>> bagobj.hello_there
    "Doesn't matter what you want, you're gonna get this"
    >>> bagobj.I_can_be_anything
    "Doesn't matter what you want, you're gonna get this"

    """

    def __init__(self, obj):
        # Use weakref to make NpzFile objects collectable by refcount
        self._obj = weakref.proxy(obj)

    def __getattribute__(self, key):
        try:
            return object.__getattribute__(self, '_obj')[key]
        except KeyError:
            raise AttributeError(key) from None

    def __dir__(self):
        """
        Enables dir(bagobj) to list the files in an NpzFile.

        This also enables tab-completion in an interpreter or IPython.
        """
        return list(object.__getattribute__(self, '_obj').keys())


def zipfile_factory(file, *args, **kwargs):
    """
    Create a ZipFile.

    Allows for Zip64, and the `file` argument can accept file, str, or
    pathlib.Path objects. `args` and `kwargs` are passed to the zipfile.ZipFile
    constructor.
    """
    if not hasattr(file, 'read'):
        file = os.fspath(file)
    import zipfile
    kwargs['allowZip64'] = True
    return zipfile.ZipFile(file, *args, **kwargs)


@set_module('numpy.lib.npyio')
class NpzFile(Mapping):
    """
    NpzFile(fid)

    A dictionary-like object with lazy-loading of files in the zipped
    archive provided on construction.

    `NpzFile` is used to load files in the NumPy ``.npz`` data archive
    format. It assumes that files in the archive have a ``.npy`` extension,
    other files are ignored.

    The arrays and file strings are lazily loaded on either
    getitem access using ``obj['key']`` or attribute lookup using
    ``obj.f.key``. A list of all files (without ``.npy`` extensions) can
    be obtained with ``obj.files`` and the ZipFile object itself using
    ``obj.zip``.

    Attributes
    ----------
    files : list of str
        List of all files in the archive with a ``.npy`` extension.
    zip : ZipFile instance
        The ZipFile object initialized with the zipped archive.
    f : BagObj instance
        An object on which attribute can be performed as an alternative
        to getitem access on the `NpzFile` instance itself.
    allow_pickle : bool, optional
        Allow loading pickled data. Default: False
    pickle_kwargs : dict, optional
        Additional keyword arguments to pass on to pickle.load.
        These are only useful when loading object arrays saved on
        Python 2.
    max_header_size : int, optional
        Maximum allowed size of the header.  Large headers may not be safe
        to load securely and thus require explicitly passing a larger value.
        See :py:func:`ast.literal_eval()` for details.
        This option is ignored when `allow_pickle` is passed.  In that case
        the file is by definition trusted and the limit is unnecessary.

    Parameters
    ----------
    fid : file, str, or pathlib.Path
        The zipped archive to open. This is either a file-like object
        or a string containing the path to the archive.
    own_fid : bool, optional
        Whether NpzFile should close the file handle.
        Requires that `fid` is a file-like object.

    Examples
    --------
    >>> import numpy as np
    >>> from tempfile import TemporaryFile
    >>> outfile = TemporaryFile()
    >>> x = np.arange(10)
    >>> y = np.sin(x)
    >>> np.savez(outfile, x=x, y=y)
    >>> _ = outfile.seek(0)

    >>> npz = np.load(outfile)
    >>> isinstance(npz, np.lib.npyio.NpzFile)
    True
    >>> npz
    NpzFile 'object' with keys: x, y
    >>> sorted(npz.files)
    ['x', 'y']
    >>> npz['x']  # getitem access
    array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    >>> npz.f.x  # attribute lookup
    array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])

    """
    # Make __exit__ safe if zipfile_factory raises an exception
    zip = None
    fid = None
    _MAX_REPR_ARRAY_COUNT = 5

    def __init__(self, fid, own_fid=False, allow_pickle=False,
                 pickle_kwargs=None, *,
                 max_header_size=_MAX_HEADER_SIZE):
        # Import is postponed to here since zipfile depends on gzip, an
        # optional component of the so-called standard library.
        _zip = zipfile_factory(fid)
        _files = _zip.namelist()
        self.files = [name.removesuffix(".npy") for name in _files]
        self._files = dict(zip(self.files, _files))
        self._files.update(zip(_files, _files))
        self.allow_pickle = allow_pickle
        self.max_header_size = max_header_size
        self.pickle_kwargs = pickle_kwargs
        self.zip = _zip
        self.f = BagObj(self)
        if own_fid:
            self.fid = fid

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        """
        Close the file.

        """
        if self.zip is not None:
            self.zip.close()
            self.zip = None
        if self.fid is not None:
            self.fid.close()
            self.fid = None
        self.f = None  # break reference cycle

    def __del__(self):
        self.close()

    # Implement the Mapping ABC
    def __iter__(self):
        return iter(self.files)

    def __len__(self):
        return len(self.files)

    def __getitem__(self, key):
        try:
            key = self._files[key]
        except KeyError:
            raise KeyError(f"{key} is not a file in the archive") from None
        else:
            with self.zip.open(key) as bytes:
                magic = bytes.read(len(format.MAGIC_PREFIX))
                bytes.seek(0)
                if magic == format.MAGIC_PREFIX:
                    # FIXME: This seems like it will copy strings around
                    #   more than is strictly necessary.  The zipfile
                    #   will read the string and then
                    #   the format.read_array will copy the string
                    #   to another place in memory.
                    #   It would be better if the zipfile could read
                    #   (or at least uncompress) the data
                    #   directly into the array memory.
                    return format.read_array(
                        bytes,
                        allow_pickle=self.allow_pickle,
                        pickle_kwargs=self.pickle_kwargs,
                        max_header_size=self.max_header_size
                    )
                else:
                    return bytes.read(key)

    def __contains__(self, key):
        return (key in self._files)

    def __repr__(self):
        # Get filename or default to `object`
        if isinstance(self.fid, str):
            filename = self.fid
        else:
            filename = getattr(self.fid, "name", "object")

        # Get the name of arrays
        array_names = ', '.join(self.files[:self._MAX_REPR_ARRAY_COUNT])
        if len(self.files) > self._MAX_REPR_ARRAY_COUNT:
            array_names += "..."
        return f"NpzFile {filename!r} with keys: {array_names}"

    # Work around problems with the docstrings in the Mapping methods
    # They contain a `->`, which confuses the type annotation interpretations
    # of sphinx-docs. See gh-25964

    def get(self, key, default=None, /):
        """
        D.get(k,[,d]) returns D[k] if k in D, else d.  d defaults to None.
        """
        return Mapping.get(self, key, default)

    def items(self):
        """
        D.items() returns a set-like object providing a view on the items
        """
        return Mapping.items(self)

    def keys(self):
        """
        D.keys() returns a set-like object providing a view on the keys
        """
        return Mapping.keys(self)

    def values(self):
        """
        D.values() returns a set-like object providing a view on the values
        """
        return Mapping.values(self)


@set_module('numpy')
def load(file, mmap_mode=None, allow_pickle=False, fix_imports=True,
         encoding='ASCII', *, max_header_size=_MAX_HEADER_SIZE):
    """
    Load arrays or pickled objects from ``.npy``, ``.npz`` or pickled files.

    .. warning:: Loading files that contain object arrays uses the ``pickle``
                 module, which is not secure against erroneous or maliciously
                 constructed data. Consider passing ``allow_pickle=False`` to
                 load data that is known not to contain object arrays for the
                 safer handling of untrusted sources.

    Parameters
    ----------
    file : file-like object, string, or pathlib.Path
        The file to read. File-like objects must support the
        ``seek()`` and ``read()`` methods and must always
        be opened in binary mode.  Pickled files require that the
        file-like object support the ``readline()`` method as well.
    mmap_mode : {None, 'r+', 'r', 'w+', 'c'}, optional
        If not None, then memory-map the file, using the given mode (see
        `numpy.memmap` for a detailed description of the modes).  A
        memory-mapped array is kept on disk. However, it can be accessed
        and sliced like any ndarray.  Memory mapping is especially useful
        for accessing small fragments of large files without reading the
        entire file into memory.
    allow_pickle : bool, optional
        Allow loading pickled object arrays stored in npy files. Reasons for
        disallowing pickles include security, as loading pickled data can
        execute arbitrary code. If pickles are disallowed, loading object
        arrays will fail. Default: False
    fix_imports : bool, optional
        Only useful when loading Python 2 generated pickled files,
        which includes npy/npz files containing object arrays. If `fix_imports`
        is True, pickle will try to map the old Python 2 names to the new names
        used in Python 3.
    encoding : str, optional
        What encoding to use when reading Python 2 strings. Only useful when
        loading Python 2 generated pickled files, which includes
        npy/npz files containing object arrays. Values other than 'latin1',
        'ASCII', and 'bytes' are not allowed, as they can corrupt numerical
        data. Default: 'ASCII'
    max_header_size : int, optional
        Maximum allowed size of the header.  Large headers may not be safe
        to load securely and thus require explicitly passing a larger value.
        See :py:func:`ast.literal_eval()` for details.
        This option is ignored when `allow_pickle` is passed.  In that case
        the file is by definition trusted and the limit is unnecessary.

    Returns
    -------
    result : array, tuple, dict, etc.
        Data stored in the file. For ``.npz`` files, the returned instance
        of NpzFile class must be closed to avoid leaking file descriptors.

    Raises
    ------
    OSError
        If the input file does not exist or cannot be read.
    UnpicklingError
        If ``allow_pickle=True``, but the file cannot be loaded as a pickle.
    ValueError
        The file contains an object array, but ``allow_pickle=False`` given.
    EOFError
        When calling ``np.load`` multiple times on the same file handle,
        if all data has already been read

    See Also
    --------
    save, savez, savez_compressed, loadtxt
    memmap : Create a memory-map to an array stored in a file on disk.
    lib.format.open_memmap : Create or load a memory-mapped ``.npy`` file.

    Notes
    -----
    - If the file contains pickle data, then whatever object is stored
      in the pickle is returned.
    - If the file is a ``.npy`` file, then a single array is returned.
    - If the file is a ``.npz`` file, then a dictionary-like object is
      returned, containing ``{filename: array}`` key-value pairs, one for
      each file in the archive.
    - If the file is a ``.npz`` file, the returned value supports the
      context manager protocol in a similar fashion to the open function::

        with load('foo.npz') as data:
            a = data['a']

      The underlying file descriptor is closed when exiting the 'with'
      block.

    Examples
    --------
    >>> import numpy as np

    Store data to disk, and load it again:

    >>> np.save('/tmp/123', np.array([[1, 2, 3], [4, 5, 6]]))
    >>> np.load('/tmp/123.npy')
    array([[1, 2, 3],
           [4, 5, 6]])

    Store compressed data to disk, and load it again:

    >>> a=np.array([[1, 2, 3], [4, 5, 6]])
    >>> b=np.array([1, 2])
    >>> np.savez('/tmp/123.npz', a=a, b=b)
    >>> data = np.load('/tmp/123.npz')
    >>> data['a']
    array([[1, 2, 3],
           [4, 5, 6]])
    >>> data['b']
    array([1, 2])
    >>> data.close()

    Mem-map the stored array, and then access the second row
    directly from disk:

    >>> X = np.load('/tmp/123.npy', mmap_mode='r')
    >>> X[1, :]
    memmap([4, 5, 6])

    """
    if encoding not in ('ASCII', 'latin1', 'bytes'):
        # The 'encoding' value for pickle also affects what encoding
        # the serialized binary data of NumPy arrays is loaded
        # in. Pickle does not pass on the encoding information to
        # NumPy. The unpickling code in numpy._core.multiarray is
        # written to assume that unicode data appearing where binary
        # should be is in 'latin1'. 'bytes' is also safe, as is 'ASCII'.
        #
        # Other encoding values can corrupt binary data, and we
        # purposefully disallow them. For the same reason, the errors=
        # argument is not exposed, as values other than 'strict'
        # result can similarly silently corrupt numerical data.
        raise ValueError("encoding must be 'ASCII', 'latin1', or 'bytes'")

    pickle_kwargs = {'encoding': encoding, 'fix_imports': fix_imports}

    with contextlib.ExitStack() as stack:
        if hasattr(file, 'read'):
            fid = file
            own_fid = False
        else:
            fid = stack.enter_context(open(os.fspath(file), "rb"))
            own_fid = True

        # Code to distinguish from NumPy binary files and pickles.
        _ZIP_PREFIX = b'PK\x03\x04'
        _ZIP_SUFFIX = b'PK\x05\x06'  # empty zip files start with this
        N = len(format.MAGIC_PREFIX)
        magic = fid.read(N)
        if not magic:
            raise EOFError("No data left in file")
        # If the file size is less than N, we need to make sure not
        # to seek past the beginning of the file
        fid.seek(-min(N, len(magic)), 1)  # back-up
        if magic.startswith((_ZIP_PREFIX, _ZIP_SUFFIX)):
            # zip-file (assume .npz)
            # Potentially transfer file ownership to NpzFile
            stack.pop_all()
            ret = NpzFile(fid, own_fid=own_fid, allow_pickle=allow_pickle,
                          pickle_kwargs=pickle_kwargs,
                          max_header_size=max_header_size)
            return ret
        elif magic == format.MAGIC_PREFIX:
            # .npy file
            if mmap_mode:
                if allow_pickle:
                    max_header_size = 2**64
                return format.open_memmap(file, mode=mmap_mode,
                                          max_header_size=max_header_size)
            else:
                return format.read_array(fid, allow_pickle=allow_pickle,
                                         pickle_kwargs=pickle_kwargs,
                                         max_header_size=max_header_size)
        else:
            # Try a pickle
            if not allow_pickle:
                raise ValueError(
                    "This file contains pickled (object) data. If you trust "
                    "the file you can load it unsafely using the "
                    "`allow_pickle=` keyword argument or `pickle.load()`.")
            try:
                return pickle.load(fid, **pickle_kwargs)
            except Exception as e:
                raise pickle.UnpicklingError(
                    f"Failed to interpret file {file!r} as a pickle") from e


def _save_dispatcher(file, arr, allow_pickle=None, fix_imports=None):
    return (arr,)


@array_function_dispatch(_save_dispatcher)
def save(file, arr, allow_pickle=True, fix_imports=np._NoValue):
    """
    Save an array to a binary file in NumPy ``.npy`` format.

    Parameters
    ----------
    file : file, str, or pathlib.Path
        File or filename to which the data is saved. If file is a file-object,
        then the filename is unchanged.  If file is a string or Path,
        a ``.npy`` extension will be appended to the filename if it does not
        already have one.
    arr : array_like
        Array data to be saved.
    allow_pickle : bool, optional
        Allow saving object arrays using Python pickles. Reasons for
        disallowing pickles include security (loading pickled data can execute
        arbitrary code) and portability (pickled objects may not be loadable
        on different Python installations, for example if the stored objects
        require libraries that are not available, and not all pickled data is
        compatible between different versions of Python).
        Default: True
    fix_imports : bool, optional
        The `fix_imports` flag is deprecated and has no effect.

        .. deprecated:: 2.1
            This flag is ignored since NumPy 1.17 and was only needed to
            support loading in Python 2 some files written in Python 3.

    See Also
    --------
    savez : Save several arrays into a ``.npz`` archive
    savetxt, load

    Notes
    -----
    For a description of the ``.npy`` format, see :py:mod:`numpy.lib.format`.

    Any data saved to the file is appended to the end of the file.

    Examples
    --------
    >>> import numpy as np

    >>> from tempfile import TemporaryFile
    >>> outfile = TemporaryFile()

    >>> x = np.arange(10)
    >>> np.save(outfile, x)

    >>> _ = outfile.seek(0) # Only needed to simulate closing & reopening file
    >>> np.load(outfile)
    array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])


    >>> with open('test.npy', 'wb') as f:
    ...     np.save(f, np.array([1, 2]))
    ...     np.save(f, np.array([1, 3]))
    >>> with open('test.npy', 'rb') as f:
    ...     a = np.load(f)
    ...     b = np.load(f)
    >>> print(a, b)
    # [1 2] [1 3]
    """
    if fix_imports is not np._NoValue:
        # Deprecated 2024-05-16, NumPy 2.1
        warnings.warn(
            "The 'fix_imports' flag is deprecated and has no effect. "
            "(Deprecated in NumPy 2.1)",
            DeprecationWarning, stacklevel=2)
    if hasattr(file, 'write'):
        file_ctx = contextlib.nullcontext(file)
    else:
        file = os.fspath(file)
        if not file.endswith('.npy'):
            file = file + '.npy'
        file_ctx = open(file, "wb")

    with file_ctx as fid:
        arr = np.asanyarray(arr)
        format.write_array(fid, arr, allow_pickle=allow_pickle,
                           pickle_kwargs={'fix_imports': fix_imports})


def _savez_dispatcher(file, *args, allow_pickle=True, **kwds):
    yield from args
    yield from kwds.values()


@array_function_dispatch(_savez_dispatcher)
def savez(file, *args, allow_pickle=True, **kwds):
    """Save several arrays into a single file in uncompressed ``.npz`` format.

    Provide arrays as keyword arguments to store them under the
    corresponding name in the output file: ``savez(fn, x=x, y=y)``.

    If arrays are specified as positional arguments, i.e., ``savez(fn,
    x, y)``, their names will be `arr_0`, `arr_1`, etc.

    Parameters
    ----------
    file : file, str, or pathlib.Path
        Either the filename (string) or an open file (file-like object)
        where the data will be saved. If file is a string or a Path, the
        ``.npz`` extension will be appended to the filename if it is not
        already there.
    args : Arguments, optional
        Arrays to save to the file. Please use keyword arguments (see
        `kwds` below) to assign names to arrays.  Arrays specified as
        args will be named "arr_0", "arr_1", and so on.
    allow_pickle : bool, optional
        Allow saving object arrays using Python pickles. Reasons for
        disallowing pickles include security (loading pickled data can execute
        arbitrary code) and portability (pickled objects may not be loadable
        on different Python installations, for example if the stored objects
        require libraries that are not available, and not all pickled data is
        compatible between different versions of Python).
        Default: True
    kwds : Keyword arguments, optional
        Arrays to save to the file. Each array will be saved to the
        output file with its corresponding keyword name.

    Returns
    -------
    None

    See Also
    --------
    save : Save a single array to a binary file in NumPy format.
    savetxt : Save an array to a file as plain text.
    savez_compressed : Save several arrays into a compressed ``.npz`` archive

    Notes
    -----
    The ``.npz`` file format is a zipped archive of files named after the
    variables they contain.  The archive is not compressed and each file
    in the archive contains one variable in ``.npy`` format. For a
    description of the ``.npy`` format, see :py:mod:`numpy.lib.format`.

    When opening the saved ``.npz`` file with `load` a `~lib.npyio.NpzFile`
    object is returned. This is a dictionary-like object which can be queried
    for its list of arrays (with the ``.files`` attribute), and for the arrays
    themselves.

    Keys passed in `kwds` are used as filenames inside the ZIP archive.
    Therefore, keys should be valid filenames; e.g., avoid keys that begin with
    ``/`` or contain ``.``.

    When naming variables with keyword arguments, it is not possible to name a
    variable ``file``, as this would cause the ``file`` argument to be defined
    twice in the call to ``savez``.

    Examples
    --------
    >>> import numpy as np
    >>> from tempfile import TemporaryFile
    >>> outfile = TemporaryFile()
    >>> x = np.arange(10)
    >>> y = np.sin(x)

    Using `savez` with \\*args, the arrays are saved with default names.

    >>> np.savez(outfile, x, y)
    >>> _ = outfile.seek(0) # Only needed to simulate closing & reopening file
    >>> npzfile = np.load(outfile)
    >>> npzfile.files
    ['arr_0', 'arr_1']
    >>> npzfile['arr_0']
    array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])

    Using `savez` with \\**kwds, the arrays are saved with the keyword names.

    >>> outfile = TemporaryFile()
    >>> np.savez(outfile, x=x, y=y)
    >>> _ = outfile.seek(0)
    >>> npzfile = np.load(outfile)
    >>> sorted(npzfile.files)
    ['x', 'y']
    >>> npzfile['x']
    array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])

    """
    _savez(file, args, kwds, False, allow_pickle=allow_pickle)


def _savez_compressed_dispatcher(file, *args, allow_pickle=True, **kwds):
    yield from args
    yield from kwds.values()


@array_function_dispatch(_savez_compressed_dispatcher)
def savez_compressed(file, *args, allow_pickle=True, **kwds):
    """
    Save several arrays into a single file in compressed ``.npz`` format.

    Provide arrays as keyword arguments to store them under the
    corresponding name in the output file: ``savez_compressed(fn, x=x, y=y)``.

    If arrays are specified as positional arguments, i.e.,
    ``savez_compressed(fn, x, y)``, their names will be `arr_0`, `arr_1`, etc.

    Parameters
    ----------
    file : file, str, or pathlib.Path
        Either the filename (string) or an open file (file-like object)
        where the data will be saved. If file is a string or a Path, the
        ``.npz`` extension will be appended to the filename if it is not
        already there.
    args : Arguments, optional
        Arrays to save to the file. Please use keyword arguments (see
        `kwds` below) to assign names to arrays.  Arrays specified as
        args will be named "arr_0", "arr_1", and so on.
    allow_pickle : bool, optional
        Allow saving object arrays using Python pickles. Reasons for
        disallowing pickles include security (loading pickled data can execute
        arbitrary code) and portability (pickled objects may not be loadable
        on different Python installations, for example if the stored objects
        require libraries that are not available, and not all pickled data is
        compatible between different versions of Python).
        Default: True
    kwds : Keyword arguments, optional
        Arrays to save to the file. Each array will be saved to the
        output file with its corresponding keyword name.

    Returns
    -------
    None

    See Also
    --------
    numpy.save : Save a single array to a binary file in NumPy format.
    numpy.savetxt : Save an array to a file as plain text.
    numpy.savez : Save several arrays into an uncompressed ``.npz`` file format
    numpy.load : Load the files created by savez_compressed.

    Notes
    -----
    The ``.npz`` file format is a zipped archive of files named after the
    variables they contain.  The archive is compressed with
    ``zipfile.ZIP_DEFLATED`` and each file in the archive contains one variable
    in ``.npy`` format. For a description of the ``.npy`` format, see
    :py:mod:`numpy.lib.format`.


    When opening the saved ``.npz`` file with `load` a `~lib.npyio.NpzFile`
    object is returned. This is a dictionary-like object which can be queried
    for its list of arrays (with the ``.files`` attribute), and for the arrays
    themselves.

    Examples
    --------
    >>> import numpy as np
    >>> test_array = np.random.rand(3, 2)
    >>> test_vector = np.random.rand(4)
    >>> np.savez_compressed('/tmp/123', a=test_array, b=test_vector)
    >>> loaded = np.load('/tmp/123.npz')
    >>> print(np.array_equal(test_array, loaded['a']))
    True
    >>> print(np.array_equal(test_vector, loaded['b']))
    True

    """
    _savez(file, args, kwds, True, allow_pickle=allow_pickle)


def _savez(file, args, kwds, compress, allow_pickle=True, pickle_kwargs=None):
    # Import is postponed to here since zipfile depends on gzip, an optional
    # component of the so-called standard library.
    import zipfile

    if not hasattr(file, 'write'):
        file = os.fspath(file)
        if not file.endswith('.npz'):
            file = file + '.npz'

    namedict = kwds
    for i, val in enumerate(args):
        key = 'arr_%d' % i
        if key in namedict.keys():
            raise ValueError(
                f"Cannot use un-named variables and keyword {key}")
        namedict[key] = val

    if compress:
        compression = zipfile.ZIP_DEFLATED
    else:
        compression = zipfile.ZIP_STORED

    zipf = zipfile_factory(file, mode="w", compression=compression)
    try:
        for key, val in namedict.items():
            fname = key + '.npy'
            val = np.asanyarray(val)
            # always force zip64, gh-10776
            with zipf.open(fname, 'w', force_zip64=True) as fid:
                format.write_array(fid, val,
                                   allow_pickle=allow_pickle,
                                   pickle_kwargs=pickle_kwargs)
    finally:
        zipf.close()


def _ensure_ndmin_ndarray_check_param(ndmin):
    """Just checks if the param ndmin is supported on
        _ensure_ndmin_ndarray. It is intended to be used as
        verification before running anything expensive.
        e.g. loadtxt, genfromtxt
    """
    # Check correctness of the values of `ndmin`
    if ndmin not in [0, 1, 2]:
        raise ValueError(f"Illegal value of ndmin keyword: {ndmin}")

def _ensure_ndmin_ndarray(a, *, ndmin: int):
    """This is a helper function of loadtxt and genfromtxt to ensure
        proper minimum dimension as requested

        ndim : int. Supported values 1, 2, 3
                    ^^ whenever this changes, keep in sync with
                       _ensure_ndmin_ndarray_check_param
    """
    # Verify that the array has at least dimensions `ndmin`.
    # Tweak the size and shape of the arrays - remove extraneous dimensions
    if a.ndim > ndmin:
        a = np.squeeze(a)
    # and ensure we have the minimum number of dimensions asked for
    # - has to be in this order for the odd case ndmin=1, a.squeeze().ndim=0
    if a.ndim < ndmin:
        if ndmin == 1:
            a = np.atleast_1d(a)
        elif ndmin == 2:
            a = np.atleast_2d(a).T

    return a


# amount of lines loadtxt reads in one chunk, can be overridden for testing
_loadtxt_chunksize = 50000


def _check_nonneg_int(value, name="argument"):
    try:
        operator.index(value)
    except TypeError:
        raise TypeError(f"{name} must be an integer") from None
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")


def _preprocess_comments(iterable, comments, encoding):
    """
    Generator that consumes a line iterated iterable and strips out the
    multiple (or multi-character) comments from lines.
    This is a pre-processing step to achieve feature parity with loadtxt
    (we assume that this feature is a nieche feature).
    """
    for line in iterable:
        if isinstance(line, bytes):
            # Need to handle conversion here, or the splitting would fail
            line = line.decode(encoding)

        for c in comments:
            line = line.split(c, 1)[0]

        yield line


# The number of rows we read in one go if confronted with a parametric dtype
_loadtxt_chunksize = 50000


def _read(fname, *, delimiter=',', comment='#', quote='"',
          imaginary_unit='j', usecols=None, skiplines=0,
          max_rows=None, converters=None, ndmin=None, unpack=False,
          dtype=np.float64, encoding=None):
    r"""
    Read a NumPy array from a text file.
    This is a helper function for loadtxt.

    Parameters
    ----------
    fname : file, str, or pathlib.Path
        The filename or the file to be read.
    delimiter : str, optional
        Field delimiter of the fields in line of the file.
        Default is a comma, ','.  If None any sequence of whitespace is
        considered a delimiter.
    comment : str or sequence of str or None, optional
        Character that begins a comment.  All text from the comment
        character to the end of the line is ignored.
        Multiple comments or multiple-character comment strings are supported,
        but may be slower and `quote` must be empty if used.
        Use None to disable all use of comments.
    quote : str or None, optional
        Character that is used to quote string fields. Default is '"'
        (a double quote). Use None to disable quote support.
    imaginary_unit : str, optional
        Character that represent the imaginary unit `sqrt(-1)`.
        Default is 'j'.
    usecols : array_like, optional
        A one-dimensional array of integer column numbers.  These are the
        columns from the file to be included in the array.  If this value
        is not given, all the columns are used.
    skiplines : int, optional
        Number of lines to skip before interpreting the data in the file.
    max_rows : int, optional
        Maximum number of rows of data to read.  Default is to read the
        entire file.
    converters : dict or callable, optional
        A function to parse all columns strings into the desired value, or
        a dictionary mapping column number to a parser function.
        E.g. if column 0 is a date string: ``converters = {0: datestr2num}``.
        Converters can also be used to provide a default value for missing
        data, e.g. ``converters = lambda s: float(s.strip() or 0)`` will
        convert empty fields to 0.
        Default: None
    ndmin : int, optional
        Minimum dimension of the array returned.
        Allowed values are 0, 1 or 2.  Default is 0.
    unpack : bool, optional
        If True, the returned array is transposed, so that arguments may be
        unpacked using ``x, y, z = read(...)``.  When used with a structured
        data-type, arrays are returned for each field.  Default is False.
    dtype : numpy data type
        A NumPy dtype instance, can be a structured dtype to map to the
        columns of the file.
    encoding : str, optional
        Encoding used to decode the inputfile. The special value 'bytes'
        (the default) enables backwards-compatible behavior for `converters`,
        ensuring that inputs to the converter functions are encoded
        bytes objects. The special value 'bytes' has no additional effect if
        ``converters=None``. If encoding is ``'bytes'`` or ``None``, the
        default system encoding is used.

    Returns
    -------
    ndarray
        NumPy array.
    """
    # Handle special 'bytes' keyword for encoding
    byte_converters = False
    if encoding == 'bytes':
        encoding = None
        byte_converters = True

    if dtype is None:
        raise TypeError("a dtype must be provided.")
    dtype = np.dtype(dtype)

    read_dtype_via_object_chunks = None
    if dtype.kind in 'SUM' and dtype in {
            np.dtype("S0"), np.dtype("U0"), np.dtype("M8"), np.dtype("m8")}:
        # This is a legacy "flexible" dtype.  We do not truly support
        # parametric dtypes currently (no dtype discovery step in the core),
        # but have to support these for backward compatibility.
        read_dtype_via_object_chunks = dtype
        dtype = np.dtype(object)

    if usecols is not None:
        # Allow usecols to be a single int or a sequence of ints, the C-code
        # handles the rest
        try:
            usecols = list(usecols)
        except TypeError:
            usecols = [usecols]

    _ensure_ndmin_ndarray_check_param(ndmin)

    if comment is None:
        comments = None
    else:
        # assume comments are a sequence of strings
        if "" in comment:
            raise ValueError(
                "comments cannot be an empty string. Use comments=None to "
                "disable comments."
            )
        comments = tuple(comment)
        comment = None
        if len(comments) == 0:
            comments = None  # No comments at all
        elif len(comments) == 1:
            # If there is only one comment, and that comment has one character,
            # the normal parsing can deal with it just fine.
            if isinstance(comments[0], str) and len(comments[0]) == 1:
                comment = comments[0]
                comments = None
        # Input validation if there are multiple comment characters
        elif delimiter in comments:
            raise TypeError(
                f"Comment characters '{comments}' cannot include the "
                f"delimiter '{delimiter}'"
            )

    # comment is now either a 1 or 0 character string or a tuple:
    if comments is not None:
        # Note: An earlier version support two character comments (and could
        #       have been extended to multiple characters, we assume this is
        #       rare enough to not optimize for.
        if quote is not None:
            raise ValueError(
                "when multiple comments or a multi-character comment is "
                "given, quotes are not supported.  In this case quotechar "
                "must be set to None.")

    if len(imaginary_unit) != 1:
        raise ValueError('len(imaginary_unit) must be 1.')

    _check_nonneg_int(skiplines)
    if max_rows is not None:
        _check_nonneg_int(max_rows)
    else:
        # Passing -1 to the C code means "read the entire file".
        max_rows = -1

    fh_closing_ctx = contextlib.nullcontext()
    filelike = False
    try:
        if isinstance(fname, os.PathLike):
            fname = os.fspath(fname)
        if isinstance(fname, str):
            fh = np.lib._datasource.open(fname, 'rt', encoding=encoding)
            if encoding is None:
                encoding = getattr(fh, 'encoding', 'latin1')

            fh_closing_ctx = contextlib.closing(fh)
            data = fh
            filelike = True
        else:
            if encoding is None:
                encoding = getattr(fname, 'encoding', 'latin1')
            data = iter(fname)
    except TypeError as e:
        raise ValueError(
            f"fname must be a string, filehandle, list of strings,\n"
            f"or generator. Got {type(fname)} instead.") from e

    with fh_closing_ctx:
        if comments is not None:
            if filelike:
                data = iter(data)
                filelike = False
            data = _preprocess_comments(data, comments, encoding)

        if read_dtype_via_object_chunks is None:
            arr = _load_from_filelike(
                data, delimiter=delimiter, comment=comment, quote=quote,
                imaginary_unit=imaginary_unit,
                usecols=usecols, skiplines=skiplines, max_rows=max_rows,
                converters=converters, dtype=dtype,
                encoding=encoding, filelike=filelike,
                byte_converters=byte_converters)

        else:
            # This branch reads the file into chunks of object arrays and then
            # casts them to the desired actual dtype.  This ensures correct
            # string-length and datetime-unit discovery (like `arr.astype()`).
            # Due to chunking, certain error reports are less clear, currently.
            if filelike:
                data = iter(data)  # cannot chunk when reading from file
                filelike = False

            c_byte_converters = False
            if read_dtype_via_object_chunks == "S":
                c_byte_converters = True  # Use latin1 rather than ascii

            chunks = []
            while max_rows != 0:
                if max_rows < 0:
                    chunk_size = _loadtxt_chunksize
                else:
                    chunk_size = min(_loadtxt_chunksize, max_rows)

                next_arr = _load_from_filelike(
                    data, delimiter=delimiter, comment=comment, quote=quote,
                    imaginary_unit=imaginary_unit,
                    usecols=usecols, skiplines=skiplines, max_rows=chunk_size,
                    converters=converters, dtype=dtype,
                    encoding=encoding, filelike=filelike,
                    byte_converters=byte_converters,
                    c_byte_converters=c_byte_converters)
                # Cast here already.  We hope that this is better even for
                # large files because the storage is more compact.  It could
                # be adapted (in principle the concatenate could cast).
                chunks.append(next_arr.astype(read_dtype_via_object_chunks))

                skiplines = 0  # Only have to skip for first chunk
                if max_rows >= 0:
                    max_rows -= chunk_size
                if len(next_arr) < chunk_size:
                    # There was less data than requested, so we are done.
                    break

            # Need at least one chunk, but if empty, the last one may have
            # the wrong shape.
            if len(chunks) > 1 and len(chunks[-1]) == 0:
                del chunks[-1]
            if len(chunks) == 1:
                arr = chunks[0]
            else:
                arr = np.concatenate(chunks, axis=0)

    # NOTE: ndmin works as advertised for structured dtypes, but normally
    #       these would return a 1D result plus the structured dimension,
    #       so ndmin=2 adds a third dimension even when no squeezing occurs.
    #       A `squeeze=False` could be a better solution (pandas uses squeeze).
    arr = _ensure_ndmin_ndarray(arr, ndmin=ndmin)

    if arr.shape:
        if arr.shape[0] == 0:
            warnings.warn(
                f'loadtxt: input contained no data: "{fname}"',
                category=UserWarning,
                stacklevel=3
            )

    if unpack:
        # Unpack structured dtypes if requested:
        dt = arr.dtype
        if dt.names is not None:
            # For structured arrays, return an array for each field.
            return [arr[field] for field in dt.names]
        else:
            return arr.T
    else:
        return arr


@finalize_array_function_like
@set_module('numpy')
def loadtxt(fname, dtype=float, comments='#', delimiter=None,
            converters=None, skiprows=0, usecols=None, unpack=False,
            ndmin=0, encoding=None, max_rows=None, *, quotechar=None,
            like=None):
    r"""
    Load data from a text file.

    Parameters
    ----------
    fname : file, str, pathlib.Path, list of str, generator
        File, filename, list, or generator to read.  If the filename
        extension is ``.gz`` or ``.bz2``, the file is first decompressed. Note
        that generators must return bytes or strings. The strings
        in a list or produced by a generator are treated as lines.
    dtype : data-type, optional
        Data-type of the resulting array; default: float.  If this is a
        structured data-type, the resulting array will be 1-dimensional, and
        each row will be interpreted as an element of the array.  In this
        case, the number of columns used must match the number of fields in
        the data-type.
    comments : str or sequence of str or None, optional
        The characters or list of characters used to indicate the start of a
        comment. None implies no comments. For backwards compatibility, byte
        strings will be decoded as 'latin1'. The default is '#'.
    delimiter : str, optional
        The character used to separate the values. For backwards compatibility,
        byte strings will be decoded as 'latin1'. The default is whitespace.

        .. versionchanged:: 1.23.0
           Only single character delimiters are supported. Newline characters
           cannot be used as the delimiter.

    converters : dict or callable, optional
        Converter functions to customize value parsing. If `converters` is
        callable, the function is applied to all columns, else it must be a
        dict that maps column number to a parser function.
        See examples for further details.
        Default: None.

        .. versionchanged:: 1.23.0
           The ability to pass a single callable to be applied to all columns
           was added.

    skiprows : int, optional
        Skip the first `skiprows` lines, including comments; default: 0.
    usecols : int or sequence, optional
        Which columns to read, with 0 being the first. For example,
        ``usecols = (1,4,5)`` will extract the 2nd, 5th and 6th columns.
        The default, None, results in all columns being read.
    unpack : bool, optional
        If True, the returned array is transposed, so that arguments may be
        unpacked using ``x, y, z = loadtxt(...)``.  When used with a
        structured data-type, arrays are returned for each field.
        Default is False.
    ndmin : int, optional
        The returned array will have at least `ndmin` dimensions.
        Otherwise mono-dimensional axes will be squeezed.
        Legal values: 0 (default), 1 or 2.
    encoding : str, optional
        Encoding used to decode the inputfile. Does not apply to input streams.
        The special value 'bytes' enables backward compatibility workarounds
        that ensures you receive byte arrays as results if possible and passes
        'latin1' encoded strings to converters. Override this value to receive
        unicode arrays and pass strings as input to converters.  If set to None
        the system default is used. The default value is None.

        .. versionchanged:: 2.0
            Before NumPy 2, the default was ``'bytes'`` for Python 2
            compatibility. The default is now ``None``.

    max_rows : int, optional
        Read `max_rows` rows of content after `skiprows` lines. The default is
        to read all the rows. Note that empty rows containing no data such as
        empty lines and comment lines are not counted towards `max_rows`,
        while such lines are counted in `skiprows`.

        .. versionchanged:: 1.23.0
            Lines containing no data, including comment lines (e.g., lines
            starting with '#' or as specified via `comments`) are not counted
            towards `max_rows`.
    quotechar : unicode character or None, optional
        The character used to denote the start and end of a quoted item.
        Occurrences of the delimiter or comment characters are ignored within
        a quoted item. The default value is ``quotechar=None``, which means
        quoting support is disabled.

        If two consecutive instances of `quotechar` are found within a quoted
        field, the first is treated as an escape character. See examples.

        .. versionadded:: 1.23.0
    ${ARRAY_FUNCTION_LIKE}

        .. versionadded:: 1.20.0

    Returns
    -------
    out : ndarray
        Data read from the text file.

    See Also
    --------
    load, fromstring, fromregex
    genfromtxt : Load data with missing values handled as specified.
    scipy.io.loadmat : reads MATLAB data files

    Notes
    -----
    This function aims to be a fast reader for simply formatted files.  The
    `genfromtxt` function provides more sophisticated handling of, e.g.,
    lines with missing values.

    Each row in the input text file must have the same number of values to be
    able to read all values. If all rows do not have same number of values, a
    subset of up to n columns (where n is the least number of values present
    in all rows) can be read by specifying the columns via `usecols`.

    The strings produced by the Python float.hex method can be used as
    input for floats.

    Examples
    --------
    >>> import numpy as np
    >>> from io import StringIO   # StringIO behaves like a file object
    >>> c = StringIO("0 1\n2 3")
    >>> np.loadtxt(c)
    array([[0., 1.],
           [2., 3.]])

    >>> d = StringIO("M 21 72\nF 35 58")
    >>> np.loadtxt(d, dtype={'names': ('gender', 'age', 'weight'),
    ...                      'formats': ('S1', 'i4', 'f4')})
    array([(b'M', 21, 72.), (b'F', 35, 58.)],
          dtype=[('gender', 'S1'), ('age', '<i4'), ('weight', '<f4')])

    >>> c = StringIO("1,0,2\n3,0,4")
    >>> x, y = np.loadtxt(c, delimiter=',', usecols=(0, 2), unpack=True)
    >>> x
    array([1., 3.])
    >>> y
    array([2., 4.])

    The `converters` argument is used to specify functions to preprocess the
    text prior to parsing. `converters` can be a dictionary that maps
    preprocessing functions to each column:

    >>> s = StringIO("1.618, 2.296\n3.141, 4.669\n")
    >>> conv = {
    ...     0: lambda x: np.floor(float(x)),  # conversion fn for column 0
    ...     1: lambda x: np.ceil(float(x)),  # conversion fn for column 1
    ... }
    >>> np.loadtxt(s, delimiter=",", converters=conv)
    array([[1., 3.],
           [3., 5.]])

    `converters` can be a callable instead of a dictionary, in which case it
    is applied to all columns:

    >>> s = StringIO("0xDE 0xAD\n0xC0 0xDE")
    >>> import functools
    >>> conv = functools.partial(int, base=16)
    >>> np.loadtxt(s, converters=conv)
    array([[222., 173.],
           [192., 222.]])

    This example shows how `converters` can be used to convert a field
    with a trailing minus sign into a negative number.

    >>> s = StringIO("10.01 31.25-\n19.22 64.31\n17.57- 63.94")
    >>> def conv(fld):
    ...     return -float(fld[:-1]) if fld.endswith("-") else float(fld)
    ...
    >>> np.loadtxt(s, converters=conv)
    array([[ 10.01, -31.25],
           [ 19.22,  64.31],
           [-17.57,  63.94]])

    Using a callable as the converter can be particularly useful for handling
    values with different formatting, e.g. floats with underscores:

    >>> s = StringIO("1 2.7 100_000")
    >>> np.loadtxt(s, converters=float)
    array([1.e+00, 2.7e+00, 1.e+05])

    This idea can be extended to automatically handle values specified in
    many different formats, such as hex values:

    >>> def conv(val):
    ...     try:
    ...         return float(val)
    ...     except ValueError:
    ...         return float.fromhex(val)
    >>> s = StringIO("1, 2.5, 3_000, 0b4, 0x1.4000000000000p+2")
    >>> np.loadtxt(s, delimiter=",", converters=conv)
    array([1.0e+00, 2.5e+00, 3.0e+03, 1.8e+02, 5.0e+00])

    Or a format where the ``-`` sign comes after the number:

    >>> s = StringIO("10.01 31.25-\n19.22 64.31\n17.57- 63.94")
    >>> conv = lambda x: -float(x[:-1]) if x.endswith("-") else float(x)
    >>> np.loadtxt(s, converters=conv)
    array([[ 10.01, -31.25],
           [ 19.22,  64.31],
           [-17.57,  63.94]])

    Support for quoted fields is enabled with the `quotechar` parameter.
    Comment and delimiter characters are ignored when they appear within a
    quoted item delineated by `quotechar`:

    >>> s = StringIO('"alpha, #42", 10.0\n"beta, #64", 2.0\n')
    >>> dtype = np.dtype([("label", "U12"), ("value", float)])
    >>> np.loadtxt(s, dtype=dtype, delimiter=",", quotechar='"')
    array([('alpha, #42', 10.), ('beta, #64',  2.)],
          dtype=[('label', '<U12'), ('value', '<f8')])

    Quoted fields can be separated by multiple whitespace characters:

    >>> s = StringIO('"alpha, #42"       10.0\n"beta, #64" 2.0\n')
    >>> dtype = np.dtype([("label", "U12"), ("value", float)])
    >>> np.loadtxt(s, dtype=dtype, delimiter=None, quotechar='"')
    array([('alpha, #42', 10.), ('beta, #64',  2.)],
          dtype=[('label', '<U12'), ('value', '<f8')])

    Two consecutive quote characters within a quoted field are treated as a
    single escaped character:

    >>> s = StringIO('"Hello, my name is ""Monty""!"')
    >>> np.loadtxt(s, dtype="U", delimiter=",", quotechar='"')
    array('Hello, my name is "Monty"!', dtype='<U26')

    Read subset of columns when all rows do not contain equal number of values:

    >>> d = StringIO("1 2\n2 4\n3 9 12\n4 16 20")
    >>> np.loadtxt(d, usecols=(0, 1))
    array([[ 1.,  2.],
           [ 2.,  4.],
           [ 3.,  9.],
           [ 4., 16.]])

    """

    if like is not None:
        return _loadtxt_with_like(
            like, fname, dtype=dtype, comments=comments, delimiter=delimiter,
            converters=converters, skiprows=skiprows, usecols=usecols,
            unpack=unpack, ndmin=ndmin, encoding=encoding,
            max_rows=max_rows
        )

    if isinstance(delimiter, bytes):
        delimiter.decode("latin1")

    if dtype is None:
        dtype = np.float64

    comment = comments
    # Control character type conversions for Py3 convenience
    if comment is not None:
        if isinstance(comment, (str, bytes)):
            comment = [comment]
        comment = [
            x.decode('latin1') if isinstance(x, bytes) else x for x in comment]
    if isinstance(delimiter, bytes):
        delimiter = delimiter.decode('latin1')

    arr = _read(fname, dtype=dtype, comment=comment, delimiter=delimiter,
                converters=converters, skiplines=skiprows, usecols=usecols,
                unpack=unpack, ndmin=ndmin, encoding=encoding,
                max_rows=max_rows, quote=quotechar)

    return arr


_loadtxt_with_like = array_function_dispatch()(loadtxt)


def _savetxt_dispatcher(fname, X, fmt=None, delimiter=None, newline=None,
                        header=None, footer=None, comments=None,
                        encoding=None):
    return (X,)


@array_function_dispatch(_savetxt_dispatcher)
def savetxt(fname, X, fmt='%.18e', delimiter=' ', newline='\n', header='',
            footer='', comments='# ', encoding=None):
    """
    Save an array to a text file.

    Parameters
    ----------
    fname : filename, file handle or pathlib.Path
        If the filename ends in ``.gz``, the file is automatically saved in
        compressed gzip format.  `loadtxt` understands gzipped files
        transparently.
    X : 1D or 2D array_like
        Data to be saved to a text file.
    fmt : str or sequence of strs, optional
        A single format (%10.5f), a sequence of formats, or a
        multi-format string, e.g. 'Iteration %d -- %10.5f', in which
        case `delimiter` is ignored. For complex `X`, the legal options
        for `fmt` are:

        * a single specifier, ``fmt='%.4e'``, resulting in numbers formatted
          like ``' (%s+%sj)' % (fmt, fmt)``
        * a full string specifying every real and imaginary part, e.g.
          ``' %.4e %+.4ej %.4e %+.4ej %.4e %+.4ej'`` for 3 columns
        * a list of specifiers, one per column - in this case, the real
          and imaginary part must have separate specifiers,
          e.g. ``['%.3e + %.3ej', '(%.15e%+.15ej)']`` for 2 columns
    delimiter : str, optional
        String or character separating columns.
    newline : str, optional
        String or character separating lines.
    header : str, optional
        String that will be written at the beginning of the file.
    footer : str, optional
        String that will be written at the end of the file.
    comments : str, optional
        String that will be prepended to the ``header`` and ``footer`` strings,
        to mark them as comments. Default: '# ',  as expected by e.g.
        ``numpy.loadtxt``.
    encoding : {None, str}, optional
        Encoding used to encode the outputfile. Does not apply to output
        streams. If the encoding is something other than 'bytes' or 'latin1'
        you will not be able to load the file in NumPy versions < 1.14. Default
        is 'latin1'.

    See Also
    --------
    save : Save an array to a binary file in NumPy ``.npy`` format
    savez : Save several arrays into an uncompressed ``.npz`` archive
    savez_compressed : Save several arrays into a compressed ``.npz`` archive

    Notes
    -----
    Further explanation of the `fmt` parameter
    (``%[flag]width[.precision]specifier``):

    flags:
        ``-`` : left justify

        ``+`` : Forces to precede result with + or -.

        ``0`` : Left pad the number with zeros instead of space (see width).

    width:
        Minimum number of characters to be printed. The value is not truncated
        if it has more characters.

    precision:
        - For integer specifiers (eg. ``d,i,o,x``), the minimum number of
          digits.
        - For ``e, E`` and ``f`` specifiers, the number of digits to print
          after the decimal point.
        - For ``g`` and ``G``, the maximum number of significant digits.
        - For ``s``, the maximum number of characters.

    specifiers:
        ``c`` : character

        ``d`` or ``i`` : signed decimal integer

        ``e`` or ``E`` : scientific notation with ``e`` or ``E``.

        ``f`` : decimal floating point

        ``g,G`` : use the shorter of ``e,E`` or ``f``

        ``o`` : signed octal

        ``s`` : string of characters

        ``u`` : unsigned decimal integer

        ``x,X`` : unsigned hexadecimal integer

    This explanation of ``fmt`` is not complete, for an exhaustive
    specification see [1]_.

    References
    ----------
    .. [1] `Format Specification Mini-Language
           <https://docs.python.org/library/string.html#format-specification-mini-language>`_,
           Python Documentation.

    Examples
    --------
    >>> import numpy as np
    >>> x = y = z = np.arange(0.0,5.0,1.0)
    >>> np.savetxt('test.out', x, delimiter=',')   # X is an array
    >>> np.savetxt('test.out', (x,y,z))   # x,y,z equal sized 1D arrays
    >>> np.savetxt('test.out', x, fmt='%1.4e')   # use exponential notation

    """

    class WriteWrap:
        """Convert to bytes on bytestream inputs.

        """
        def __init__(self, fh, encoding):
            self.fh = fh
            self.encoding = encoding
            self.do_write = self.first_write

        def close(self):
            self.fh.close()

        def write(self, v):
            self.do_write(v)

        def write_bytes(self, v):
            if isinstance(v, bytes):
                self.fh.write(v)
            else:
                self.fh.write(v.encode(self.encoding))

        def write_normal(self, v):
            self.fh.write(asunicode(v))

        def first_write(self, v):
            try:
                self.write_normal(v)
                self.write = self.write_normal
            except TypeError:
                # input is probably a bytestream
                self.write_bytes(v)
                self.write = self.write_bytes

    own_fh = False
    if isinstance(fname, os.PathLike):
        fname = os.fspath(fname)
    if _is_string_like(fname):
        # datasource doesn't support creating a new file ...
        open(fname, 'wt').close()
        fh = np.lib._datasource.open(fname, 'wt', encoding=encoding)
        own_fh = True
    elif hasattr(fname, 'write'):
        # wrap to handle byte output streams
        fh = WriteWrap(fname, encoding or 'latin1')
    else:
        raise ValueError('fname must be a string or file handle')

    try:
        X = np.asarray(X)

        # Handle 1-dimensional arrays
        if X.ndim == 0 or X.ndim > 2:
            raise ValueError(
                "Expected 1D or 2D array, got %dD array instead" % X.ndim)
        elif X.ndim == 1:
            # Common case -- 1d array of numbers
            if X.dtype.names is None:
                X = np.atleast_2d(X).T
                ncol = 1

            # Complex dtype -- each field indicates a separate column
            else:
                ncol = len(X.dtype.names)
        else:
            ncol = X.shape[1]

        iscomplex_X = np.iscomplexobj(X)
        # `fmt` can be a string with multiple insertion points or a
        # list of formats.  E.g. '%10.5f\t%10d' or ('%10.5f', '$10d')
        if type(fmt) in (list, tuple):
            if len(fmt) != ncol:
                raise AttributeError(f'fmt has wrong shape.  {str(fmt)}')
            format = delimiter.join(fmt)
        elif isinstance(fmt, str):
            n_fmt_chars = fmt.count('%')
            error = ValueError(f'fmt has wrong number of % formats:  {fmt}')
            if n_fmt_chars == 1:
                if iscomplex_X:
                    fmt = [f' ({fmt}+{fmt}j)', ] * ncol
                else:
                    fmt = [fmt, ] * ncol
                format = delimiter.join(fmt)
            elif iscomplex_X and n_fmt_chars != (2 * ncol):
                raise error
            elif ((not iscomplex_X) and n_fmt_chars != ncol):
                raise error
            else:
                format = fmt
        else:
            raise ValueError(f'invalid fmt: {fmt!r}')

        if len(header) > 0:
            header = header.replace('\n', '\n' + comments)
            fh.write(comments + header + newline)
        if iscomplex_X:
            for row in X:
                row2 = []
                for number in row:
                    row2.extend((number.real, number.imag))
                s = format % tuple(row2) + newline
                fh.write(s.replace('+-', '-'))
        else:
            for row in X:
                try:
                    v = format % tuple(row) + newline
                except TypeError as e:
                    raise TypeError("Mismatch between array dtype ('%s') and "
                                    "format specifier ('%s')"
                                    % (str(X.dtype), format)) from e
                fh.write(v)

        if len(footer) > 0:
            footer = footer.replace('\n', '\n' + comments)
            fh.write(comments + footer + newline)
    finally:
        if own_fh:
            fh.close()


@set_module('numpy')
def fromregex(file, regexp, dtype, encoding=None):
    r"""
    Construct an array from a text file, using regular expression parsing.

    The returned array is always a structured array, and is constructed from
    all matches of the regular expression in the file. Groups in the regular
    expression are converted to fields of the structured array.

    Parameters
    ----------
    file : file, str, or pathlib.Path
        Filename or file object to read.

        .. versionchanged:: 1.22.0
            Now accepts `os.PathLike` implementations.

    regexp : str or regexp
        Regular expression used to parse the file.
        Groups in the regular expression correspond to fields in the dtype.
    dtype : dtype or list of dtypes
        Dtype for the structured array; must be a structured datatype.
    encoding : str, optional
        Encoding used to decode the inputfile. Does not apply to input streams.

    Returns
    -------
    output : ndarray
        The output array, containing the part of the content of `file` that
        was matched by `regexp`. `output` is always a structured array.

    Raises
    ------
    TypeError
        When `dtype` is not a valid dtype for a structured array.

    See Also
    --------
    fromstring, loadtxt

    Notes
    -----
    Dtypes for structured arrays can be specified in several forms, but all
    forms specify at least the data type and field name. For details see
    `basics.rec`.

    Examples
    --------
    >>> import numpy as np
    >>> from io import StringIO
    >>> text = StringIO("1312 foo\n1534  bar\n444   qux")

    >>> regexp = r"(\d+)\s+(...)"  # match [digits, whitespace, anything]
    >>> output = np.fromregex(text, regexp,
    ...                       [('num', np.int64), ('key', 'S3')])
    >>> output
    array([(1312, b'foo'), (1534, b'bar'), ( 444, b'qux')],
          dtype=[('num', '<i8'), ('key', 'S3')])
    >>> output['num']
    array([1312, 1534,  444])

    """
    own_fh = False
    if not hasattr(file, "read"):
        file = os.fspath(file)
        file = np.lib._datasource.open(file, 'rt', encoding=encoding)
        own_fh = True

    try:
        if not isinstance(dtype, np.dtype):
            dtype = np.dtype(dtype)
        if dtype.names is None:
            raise TypeError('dtype must be a structured datatype.')

        content = file.read()
        if isinstance(content, bytes) and isinstance(regexp, str):
            regexp = asbytes(regexp)

        if not hasattr(regexp, 'match'):
            regexp = re.compile(regexp)
        seq = regexp.findall(content)
        if seq and not isinstance(seq[0], tuple):
            # Only one group is in the regexp.
            # Create the new array as a single data-type and then
            #   re-interpret as a single-field structured array.
            newdtype = np.dtype(dtype[dtype.names[0]])
            output = np.array(seq, dtype=newdtype)
            output.dtype = dtype
        else:
            output = np.array(seq, dtype=dtype)

        return output
    finally:
        if own_fh:
            file.close()


#####--------------------------------------------------------------------------
#---- --- ASCII functions ---
#####--------------------------------------------------------------------------


@finalize_array_function_like
@set_module('numpy')
def genfromtxt(fname, dtype=float, comments='#', delimiter=None,
               skip_header=0, skip_footer=0, converters=None,
               missing_values=None, filling_values=None, usecols=None,
               names=None, excludelist=None,
               deletechars=''.join(sorted(NameValidator.defaultdeletechars)),  # noqa: B008
               replace_space='_', autostrip=False, case_sensitive=True,
               defaultfmt="f%i", unpack=None, usemask=False, loose=True,
               invalid_raise=True, max_rows=None, encoding=None,
               *, ndmin=0, like=None):
    """
    Load data from a text file, with missing values handled as specified.

    Each line past the first `skip_header` lines is split at the `delimiter`
    character, and characters following the `comments` character are discarded.

    Parameters
    ----------
    fname : file, str, pathlib.Path, list of str, generator
        File, filename, list, or generator to read.  If the filename
        extension is ``.gz`` or ``.bz2``, the file is first decompressed. Note
        that generators must return bytes or strings. The strings
        in a list or produced by a generator are treated as lines.
    dtype : dtype, optional
        Data type of the resulting array.
        If None, the dtypes will be determined by the contents of each
        column, individually.
    comments : str, optional
        The character used to indicate the start of a comment.
        All the characters occurring on a line after a comment are discarded.
    delimiter : str, int, or sequence, optional
        The string used to separate values.  By default, any consecutive
        whitespaces act as delimiter.  An integer or sequence of integers
        can also be provided as width(s) of each field.
    skiprows : int, optional
        `skiprows` was removed in numpy 1.10. Please use `skip_header` instead.
    skip_header : int, optional
        The number of lines to skip at the beginning of the file.
    skip_footer : int, optional
        The number of lines to skip at the end of the file.
    converters : variable, optional
        The set of functions that convert the data of a column to a value.
        The converters can also be used to provide a default value
        for missing data: ``converters = {3: lambda s: float(s or 0)}``.
    missing : variable, optional
        `missing` was removed in numpy 1.10. Please use `missing_values`
        instead.
    missing_values : variable, optional
        The set of strings corresponding to missing data.
    filling_values : variable, optional
        The set of values to be used as default when the data are missing.
    usecols : sequence, optional
        Which columns to read, with 0 being the first.  For example,
        ``usecols = (1, 4, 5)`` will extract the 2nd, 5th and 6th columns.
    names : {None, True, str, sequence}, optional
        If `names` is True, the field names are read from the first line after
        the first `skip_header` lines. This line can optionally be preceded
        by a comment delimiter. Any content before the comment delimiter is
        discarded. If `names` is a sequence or a single-string of
        comma-separated names, the names will be used to define the field
        names in a structured dtype. If `names` is None, the names of the
        dtype fields will be used, if any.
    excludelist : sequence, optional
        A list of names to exclude. This list is appended to the default list
        ['return','file','print']. Excluded names are appended with an
        underscore: for example, `file` would become `file_`.
    deletechars : str, optional
        A string combining invalid characters that must be deleted from the
        names.
    defaultfmt : str, optional
        A format used to define default field names, such as "f%i" or "f_%02i".
    autostrip : bool, optional
        Whether to automatically strip white spaces from the variables.
    replace_space : char, optional
        Character(s) used in replacement of white spaces in the variable
        names. By default, use a '_'.
    case_sensitive : {True, False, 'upper', 'lower'}, optional
        If True, field names are case sensitive.
        If False or 'upper', field names are converted to upper case.
        If 'lower', field names are converted to lower case.
    unpack : bool, optional
        If True, the returned array is transposed, so that arguments may be
        unpacked using ``x, y, z = genfromtxt(...)``.  When used with a
        structured data-type, arrays are returned for each field.
        Default is False.
    usemask : bool, optional
        If True, return a masked array.
        If False, return a regular array.
    loose : bool, optional
        If True, do not raise errors for invalid values.
    invalid_raise : bool, optional
        If True, an exception is raised if an inconsistency is detected in the
        number of columns.
        If False, a warning is emitted and the offending lines are skipped.
    max_rows : int,  optional
        The maximum number of rows to read. Must not be used with skip_footer
        at the same time.  If given, the value must be at least 1. Default is
        to read the entire file.
    encoding : str, optional
        Encoding used to decode the inputfile. Does not apply when `fname`
        is a file object. The special value 'bytes' enables backward
        compatibility workarounds that ensure that you receive byte arrays
        when possible and passes latin1 encoded strings to converters.
        Override this value to receive unicode arrays and pass strings
        as input to converters.  If set to None the system default is used.
        The default value is 'bytes'.

        .. versionchanged:: 2.0
            Before NumPy 2, the default was ``'bytes'`` for Python 2
            compatibility. The default is now ``None``.

    ndmin : int, optional
        Same parameter as `loadtxt`

        .. versionadded:: 1.23.0
    ${ARRAY_FUNCTION_LIKE}

        .. versionadded:: 1.20.0

    Returns
    -------
    out : ndarray
        Data read from the text file. If `usemask` is True, this is a
        masked array.

    See Also
    --------
    numpy.loadtxt : equivalent function when no data is missing.

    Notes
    -----
    * When spaces are used as delimiters, or when no delimiter has been given
      as input, there should not be any missing data between two fields.
    * When variables are named (either by a flexible dtype or with a `names`
      sequence), there must not be any header in the file (else a ValueError
      exception is raised).
    * Individual values are not stripped of spaces by default.
      When using a custom converter, make sure the function does remove spaces.
    * Custom converters may receive unexpected values due to dtype
      discovery.

    References
    ----------
    .. [1] NumPy User Guide, section `I/O with NumPy
           <https://docs.scipy.org/doc/numpy/user/basics.io.genfromtxt.html>`_.

    Examples
    --------
    >>> from io import StringIO
    >>> import numpy as np

    Comma delimited file with mixed dtype

    >>> s = StringIO("1,1.3,abcde")
    >>> data = np.genfromtxt(s, dtype=[('myint','i8'),('myfloat','f8'),
    ... ('mystring','S5')], delimiter=",")
    >>> data
    array((1, 1.3, b'abcde'),
          dtype=[('myint', '<i8'), ('myfloat', '<f8'), ('mystring', 'S5')])

    Using dtype = None

    >>> _ = s.seek(0) # needed for StringIO example only
    >>> data = np.genfromtxt(s, dtype=None,
    ... names = ['myint','myfloat','mystring'], delimiter=",")
    >>> data
    array((1, 1.3, 'abcde'),
          dtype=[('myint', '<i8'), ('myfloat', '<f8'), ('mystring', '<U5')])

    Specifying dtype and names

    >>> _ = s.seek(0)
    >>> data = np.genfromtxt(s, dtype="i8,f8,S5",
    ... names=['myint','myfloat','mystring'], delimiter=",")
    >>> data
    array((1, 1.3, b'abcde'),
          dtype=[('myint', '<i8'), ('myfloat', '<f8'), ('mystring', 'S5')])

    An example with fixed-width columns

    >>> s = StringIO("11.3abcde")
    >>> data = np.genfromtxt(s, dtype=None, names=['intvar','fltvar','strvar'],
    ...     delimiter=[1,3,5])
    >>> data
    array((1, 1.3, 'abcde'),
          dtype=[('intvar', '<i8'), ('fltvar', '<f8'), ('strvar', '<U5')])

    An example to show comments

    >>> f = StringIO('''
    ... text,# of chars
    ... hello world,11
    ... numpy,5''')
    >>> np.genfromtxt(f, dtype='S12,S12', delimiter=',')
    array([(b'text', b''), (b'hello world', b'11'), (b'numpy', b'5')],
      dtype=[('f0', 'S12'), ('f1', 'S12')])

    """

    if like is not None:
        return _genfromtxt_with_like(
            like, fname, dtype=dtype, comments=comments, delimiter=delimiter,
            skip_header=skip_header, skip_footer=skip_footer,
            converters=converters, missing_values=missing_values,
            filling_values=filling_values, usecols=usecols, names=names,
            excludelist=excludelist, deletechars=deletechars,
            replace_space=replace_space, autostrip=autostrip,
            case_sensitive=case_sensitive, defaultfmt=defaultfmt,
            unpack=unpack, usemask=usemask, loose=loose,
            invalid_raise=invalid_raise, max_rows=max_rows, encoding=encoding,
            ndmin=ndmin,
        )

    _ensure_ndmin_ndarray_check_param(ndmin)

    if max_rows is not None:
        if skip_footer:
            raise ValueError(
                    "The keywords 'skip_footer' and 'max_rows' can not be "
                    "specified at the same time.")
        if max_rows < 1:
            raise ValueError("'max_rows' must be at least 1.")

    if usemask:
        from numpy.ma import MaskedArray, make_mask_descr
    # Check the input dictionary of converters
    user_converters = converters or {}
    if not isinstance(user_converters, dict):
        raise TypeError(
            "The input argument 'converter' should be a valid dictionary "
            "(got '%s' instead)" % type(user_converters))

    if encoding == 'bytes':
        encoding = None
        byte_converters = True
    else:
        byte_converters = False

    # Initialize the filehandle, the LineSplitter and the NameValidator
    if isinstance(fname, os.PathLike):
        fname = os.fspath(fname)
    if isinstance(fname, str):
        fid = np.lib._datasource.open(fname, 'rt', encoding=encoding)
        fid_ctx = contextlib.closing(fid)
    else:
        fid = fname
        fid_ctx = contextlib.nullcontext(fid)
    try:
        fhd = iter(fid)
    except TypeError as e:
        raise TypeError(
            "fname must be a string, a filehandle, a sequence of strings,\n"
            f"or an iterator of strings. Got {type(fname)} instead."
        ) from e
    with fid_ctx:
        split_line = LineSplitter(delimiter=delimiter, comments=comments,
                                  autostrip=autostrip, encoding=encoding)
        validate_names = NameValidator(excludelist=excludelist,
                                       deletechars=deletechars,
                                       case_sensitive=case_sensitive,
                                       replace_space=replace_space)

        # Skip the first `skip_header` rows
        try:
            for i in range(skip_header):
                next(fhd)

            # Keep on until we find the first valid values
            first_values = None

            while not first_values:
                first_line = _decode_line(next(fhd), encoding)
                if (names is True) and (comments is not None):
                    if comments in first_line:
                        first_line = (
                            ''.join(first_line.split(comments)[1:]))
                first_values = split_line(first_line)
        except StopIteration:
            # return an empty array if the datafile is empty
            first_line = ''
            first_values = []
            warnings.warn(
                f'genfromtxt: Empty input file: "{fname}"', stacklevel=2
            )

        # Should we take the first values as names ?
        if names is True:
            fval = first_values[0].strip()
            if comments is not None:
                if fval in comments:
                    del first_values[0]

        # Check the columns to use: make sure `usecols` is a list
        if usecols is not None:
            try:
                usecols = [_.strip() for _ in usecols.split(",")]
            except AttributeError:
                try:
                    usecols = list(usecols)
                except TypeError:
                    usecols = [usecols, ]
        nbcols = len(usecols or first_values)

        # Check the names and overwrite the dtype.names if needed
        if names is True:
            names = validate_names([str(_.strip()) for _ in first_values])
            first_line = ''
        elif _is_string_like(names):
            names = validate_names([_.strip() for _ in names.split(',')])
        elif names:
            names = validate_names(names)
        # Get the dtype
        if dtype is not None:
            dtype = easy_dtype(dtype, defaultfmt=defaultfmt, names=names,
                               excludelist=excludelist,
                               deletechars=deletechars,
                               case_sensitive=case_sensitive,
                               replace_space=replace_space)
        # Make sure the names is a list (for 2.5)
        if names is not None:
            names = list(names)

        if usecols:
            for (i, current) in enumerate(usecols):
                # if usecols is a list of names, convert to a list of indices
                if _is_string_like(current):
                    usecols[i] = names.index(current)
                elif current < 0:
                    usecols[i] = current + len(first_values)
            # If the dtype is not None, make sure we update it
            if (dtype is not None) and (len(dtype) > nbcols):
                descr = dtype.descr
                dtype = np.dtype([descr[_] for _ in usecols])
                names = list(dtype.names)
            # If `names` is not None, update the names
            elif (names is not None) and (len(names) > nbcols):
                names = [names[_] for _ in usecols]
        elif (names is not None) and (dtype is not None):
            names = list(dtype.names)

        # Process the missing values ...............................
        # Rename missing_values for convenience
        user_missing_values = missing_values or ()
        if isinstance(user_missing_values, bytes):
            user_missing_values = user_missing_values.decode('latin1')

        # Define the list of missing_values (one column: one list)
        missing_values = [[''] for _ in range(nbcols)]

        # We have a dictionary: process it field by field
        if isinstance(user_missing_values, dict):
            # Loop on the items
            for (key, val) in user_missing_values.items():
                # Is the key a string ?
                if _is_string_like(key):
                    try:
                        # Transform it into an integer
                        key = names.index(key)
                    except ValueError:
                        # We couldn't find it: the name must have been dropped
                        continue
                # Redefine the key as needed if it's a column number
                if usecols:
                    try:
                        key = usecols.index(key)
                    except ValueError:
                        pass
                # Transform the value as a list of string
                if isinstance(val, (list, tuple)):
                    val = [str(_) for _ in val]
                else:
                    val = [str(val), ]
                # Add the value(s) to the current list of missing
                if key is None:
                    # None acts as default
                    for miss in missing_values:
                        miss.extend(val)
                else:
                    missing_values[key].extend(val)
        # We have a sequence : each item matches a column
        elif isinstance(user_missing_values, (list, tuple)):
            for (value, entry) in zip(user_missing_values, missing_values):
                value = str(value)
                if value not in entry:
                    entry.append(value)
        # We have a string : apply it to all entries
        elif isinstance(user_missing_values, str):
            user_value = user_missing_values.split(",")
            for entry in missing_values:
                entry.extend(user_value)
        # We have something else: apply it to all entries
        else:
            for entry in missing_values:
                entry.extend([str(user_missing_values)])

        # Process the filling_values ...............................
        # Rename the input for convenience
        user_filling_values = filling_values
        if user_filling_values is None:
            user_filling_values = []
        # Define the default
        filling_values = [None] * nbcols
        # We have a dictionary : update each entry individually
        if isinstance(user_filling_values, dict):
            for (key, val) in user_filling_values.items():
                if _is_string_like(key):
                    try:
                        # Transform it into an integer
                        key = names.index(key)
                    except ValueError:
                        # We couldn't find it: the name must have been dropped
                        continue
                # Redefine the key if it's a column number
                # and usecols is defined
                if usecols:
                    try:
                        key = usecols.index(key)
                    except ValueError:
                        pass
                # Add the value to the list
                filling_values[key] = val
        # We have a sequence : update on a one-to-one basis
        elif isinstance(user_filling_values, (list, tuple)):
            n = len(user_filling_values)
            if (n <= nbcols):
                filling_values[:n] = user_filling_values
            else:
                filling_values = user_filling_values[:nbcols]
        # We have something else : use it for all entries
        else:
            filling_values = [user_filling_values] * nbcols

        # Initialize the converters ................................
        if dtype is None:
            # Note: we can't use a [...]*nbcols, as we would have 3 times
            # the same converter, instead of 3 different converters.
            converters = [
                StringConverter(None, missing_values=miss, default=fill)
                for (miss, fill) in zip(missing_values, filling_values)
            ]
        else:
            dtype_flat = flatten_dtype(dtype, flatten_base=True)
            # Initialize the converters
            if len(dtype_flat) > 1:
                # Flexible type : get a converter from each dtype
                zipit = zip(dtype_flat, missing_values, filling_values)
                converters = [StringConverter(dt,
                                              locked=True,
                                              missing_values=miss,
                                              default=fill)
                              for (dt, miss, fill) in zipit]
            else:
                # Set to a default converter (but w/ different missing values)
                zipit = zip(missing_values, filling_values)
                converters = [StringConverter(dtype,
                                              locked=True,
                                              missing_values=miss,
                                              default=fill)
                              for (miss, fill) in zipit]
        # Update the converters to use the user-defined ones
        uc_update = []
        for (j, conv) in user_converters.items():
            # If the converter is specified by column names,
            # use the index instead
            if _is_string_like(j):
                try:
                    j = names.index(j)
                    i = j
                except ValueError:
                    continue
            elif usecols:
                try:
                    i = usecols.index(j)
                except ValueError:
                    # Unused converter specified
                    continue
            else:
                i = j
            # Find the value to test - first_line is not filtered by usecols:
            if len(first_line):
                testing_value = first_values[j]
            else:
                testing_value = None
            if conv is bytes:
                user_conv = asbytes
            elif byte_converters:
                # Converters may use decode to workaround numpy's old
                # behavior, so encode the string again before passing
                # to the user converter.
                def tobytes_first(x, conv):
                    if type(x) is bytes:
                        return conv(x)
                    return conv(x.encode("latin1"))
                user_conv = functools.partial(tobytes_first, conv=conv)
            else:
                user_conv = conv
            converters[i].update(user_conv, locked=True,
                                 testing_value=testing_value,
                                 default=filling_values[i],
                                 missing_values=missing_values[i],)
            uc_update.append((i, user_conv))
        # Make sure we have the corrected keys in user_converters...
        user_converters.update(uc_update)

        # Fixme: possible error as following variable never used.
        # miss_chars = [_.missing_values for _ in converters]

        # Initialize the output lists ...
        # ... rows
        rows = []
        append_to_rows = rows.append
        # ... masks
        if usemask:
            masks = []
            append_to_masks = masks.append
        # ... invalid
        invalid = []
        append_to_invalid = invalid.append

        # Parse each line
        for (i, line) in enumerate(itertools.chain([first_line, ], fhd)):
            values = split_line(line)
            nbvalues = len(values)
            # Skip an empty line
            if nbvalues == 0:
                continue
            if usecols:
                # Select only the columns we need
                try:
                    values = [values[_] for _ in usecols]
                except IndexError:
                    append_to_invalid((i + skip_header + 1, nbvalues))
                    continue
            elif nbvalues != nbcols:
                append_to_invalid((i + skip_header + 1, nbvalues))
                continue
            # Store the values
            append_to_rows(tuple(values))
            if usemask:
                append_to_masks(tuple(v.strip() in m
                                       for (v, m) in zip(values,
                                                         missing_values)))
            if len(rows) == max_rows:
                break

    # Upgrade the converters (if needed)
    if dtype is None:
        for (i, converter) in enumerate(converters):
            current_column = [itemgetter(i)(_m) for _m in rows]
            try:
                converter.iterupgrade(current_column)
            except ConverterLockError:
                errmsg = f"Converter #{i} is locked and cannot be upgraded: "
                current_column = map(itemgetter(i), rows)
                for (j, value) in enumerate(current_column):
                    try:
                        converter.upgrade(value)
                    except (ConverterError, ValueError):
                        line_number = j + 1 + skip_header
                        errmsg += f"(occurred line #{line_number} for value '{value}')"
                        raise ConverterError(errmsg)

    # Check that we don't have invalid values
    nbinvalid = len(invalid)
    if nbinvalid > 0:
        nbrows = len(rows) + nbinvalid - skip_footer
        # Construct the error message
        template = f"    Line #%i (got %i columns instead of {nbcols})"
        if skip_footer > 0:
            nbinvalid_skipped = len([_ for _ in invalid
                                     if _[0] > nbrows + skip_header])
            invalid = invalid[:nbinvalid - nbinvalid_skipped]
            skip_footer -= nbinvalid_skipped
#
#            nbrows -= skip_footer
#            errmsg = [template % (i, nb)
#                      for (i, nb) in invalid if i < nbrows]
#        else:
        errmsg = [template % (i, nb)
                  for (i, nb) in invalid]
        if len(errmsg):
            errmsg.insert(0, "Some errors were detected !")
            errmsg = "\n".join(errmsg)
            # Raise an exception ?
            if invalid_raise:
                raise ValueError(errmsg)
            # Issue a warning ?
            else:
                warnings.warn(errmsg, ConversionWarning, stacklevel=2)

    # Strip the last skip_footer data
    if skip_footer > 0:
        rows = rows[:-skip_footer]
        if usemask:
            masks = masks[:-skip_footer]

    # Convert each value according to the converter:
    # We want to modify the list in place to avoid creating a new one...
    if loose:
        rows = list(
            zip(*[[conv._loose_call(_r) for _r in map(itemgetter(i), rows)]
                  for (i, conv) in enumerate(converters)]))
    else:
        rows = list(
            zip(*[[conv._strict_call(_r) for _r in map(itemgetter(i), rows)]
                  for (i, conv) in enumerate(converters)]))

    # Reset the dtype
    data = rows
    if dtype is None:
        # Get the dtypes from the types of the converters
        column_types = [conv.type for conv in converters]
        # Find the columns with strings...
        strcolidx = [i for (i, v) in enumerate(column_types)
                     if v == np.str_]

        if byte_converters and strcolidx:
            # convert strings back to bytes for backward compatibility
            warnings.warn(
                "Reading unicode strings without specifying the encoding "
                "argument is deprecated. Set the encoding, use None for the "
                "system default.",
                np.exceptions.VisibleDeprecationWarning, stacklevel=2)

            def encode_unicode_cols(row_tup):
                row = list(row_tup)
                for i in strcolidx:
                    row[i] = row[i].encode('latin1')
                return tuple(row)

            try:
                data = [encode_unicode_cols(r) for r in data]
            except UnicodeEncodeError:
                pass
            else:
                for i in strcolidx:
                    column_types[i] = np.bytes_

        # Update string types to be the right length
        sized_column_types = column_types.copy()
        for i, col_type in enumerate(column_types):
            if np.issubdtype(col_type, np.character):
                n_chars = max(len(row[i]) for row in data)
                sized_column_types[i] = (col_type, n_chars)

        if names is None:
            # If the dtype is uniform (before sizing strings)
            base = {
                c_type
                for c, c_type in zip(converters, column_types)
                if c._checked}
            if len(base) == 1:
                uniform_type, = base
                (ddtype, mdtype) = (uniform_type, bool)
            else:
                ddtype = [(defaultfmt % i, dt)
                          for (i, dt) in enumerate(sized_column_types)]
                if usemask:
                    mdtype = [(defaultfmt % i, bool)
                              for (i, dt) in enumerate(sized_column_types)]
        else:
            ddtype = list(zip(names, sized_column_types))
            mdtype = list(zip(names, [bool] * len(sized_column_types)))
        output = np.array(data, dtype=ddtype)
        if usemask:
            outputmask = np.array(masks, dtype=mdtype)
    else:
        # Overwrite the initial dtype names if needed
        if names and dtype.names is not None:
            dtype.names = names
        # Case 1. We have a structured type
        if len(dtype_flat) > 1:
            # Nested dtype, eg [('a', int), ('b', [('b0', int), ('b1', 'f4')])]
            # First, create the array using a flattened dtype:
            # [('a', int), ('b1', int), ('b2', float)]
            # Then, view the array using the specified dtype.
            if 'O' in (_.char for _ in dtype_flat):
                if has_nested_fields(dtype):
                    raise NotImplementedError(
                        "Nested fields involving objects are not supported...")
                else:
                    output = np.array(data, dtype=dtype)
            else:
                rows = np.array(data, dtype=[('', _) for _ in dtype_flat])
                output = rows.view(dtype)
            # Now, process the rowmasks the same way
            if usemask:
                rowmasks = np.array(
                    masks, dtype=np.dtype([('', bool) for t in dtype_flat]))
                # Construct the new dtype
                mdtype = make_mask_descr(dtype)
                outputmask = rowmasks.view(mdtype)
        # Case #2. We have a basic dtype
        else:
            # We used some user-defined converters
            if user_converters:
                ishomogeneous = True
                descr = []
                for i, ttype in enumerate([conv.type for conv in converters]):
                    # Keep the dtype of the current converter
                    if i in user_converters:
                        ishomogeneous &= (ttype == dtype.type)
                        if np.issubdtype(ttype, np.character):
                            ttype = (ttype, max(len(row[i]) for row in data))
                        descr.append(('', ttype))
                    else:
                        descr.append(('', dtype))
                # So we changed the dtype ?
                if not ishomogeneous:
                    # We have more than one field
                    if len(descr) > 1:
                        dtype = np.dtype(descr)
                    # We have only one field: drop the name if not needed.
                    else:
                        dtype = np.dtype(ttype)
            #
            output = np.array(data, dtype)
            if usemask:
                if dtype.names is not None:
                    mdtype = [(_, bool) for _ in dtype.names]
                else:
                    mdtype = bool
                outputmask = np.array(masks, dtype=mdtype)
    # Try to take care of the missing data we missed
    names = output.dtype.names
    if usemask and names:
        for (name, conv) in zip(names, converters):
            missing_values = [conv(_) for _ in conv.missing_values
                              if _ != '']
            for mval in missing_values:
                outputmask[name] |= (output[name] == mval)
    # Construct the final array
    if usemask:
        output = output.view(MaskedArray)
        output._mask = outputmask

    output = _ensure_ndmin_ndarray(output, ndmin=ndmin)

    if unpack:
        if names is None:
            return output.T
        elif len(names) == 1:
            # squeeze single-name dtypes too
            return output[names[0]]
        else:
            # For structured arrays with multiple fields,
            # return an array for each field.
            return [output[field] for field in names]
    return output


_genfromtxt_with_like = array_function_dispatch()(genfromtxt)


def recfromtxt(fname, **kwargs):
    """
    Load ASCII data from a file and return it in a record array.

    If ``usemask=False`` a standard `recarray` is returned,
    if ``usemask=True`` a MaskedRecords array is returned.

    .. deprecated:: 2.0
        Use `numpy.genfromtxt` instead.

    Parameters
    ----------
    fname, kwargs : For a description of input parameters, see `genfromtxt`.

    See Also
    --------
    numpy.genfromtxt : generic function

    Notes
    -----
    By default, `dtype` is None, which means that the data-type of the output
    array will be determined from the data.

    """

    # Deprecated in NumPy 2.0, 2023-07-11
    warnings.warn(
        "`recfromtxt` is deprecated, "
        "use `numpy.genfromtxt` instead."
        "(deprecated in NumPy 2.0)",
        DeprecationWarning,
        stacklevel=2
    )

    kwargs.setdefault("dtype", None)
    usemask = kwargs.get('usemask', False)
    output = genfromtxt(fname, **kwargs)
    if usemask:
        from numpy.ma.mrecords import MaskedRecords
        output = output.view(MaskedRecords)
    else:
        output = output.view(np.recarray)
    return output


def recfromcsv(fname, **kwargs):
    """
    Load ASCII data stored in a comma-separated file.

    The returned array is a record array (if ``usemask=False``, see
    `recarray`) or a masked record array (if ``usemask=True``,
    see `ma.mrecords.MaskedRecords`).

    .. deprecated:: 2.0
        Use `numpy.genfromtxt` with comma as `delimiter` instead.

    Parameters
    ----------
    fname, kwargs : For a description of input parameters, see `genfromtxt`.

    See Also
    --------
    numpy.genfromtxt : generic function to load ASCII data.

    Notes
    -----
    By default, `dtype` is None, which means that the data-type of the output
    array will be determined from the data.

    """

    # Deprecated in NumPy 2.0, 2023-07-11
    warnings.warn(
        "`recfromcsv` is deprecated, "
        "use `numpy.genfromtxt` with comma as `delimiter` instead. "
        "(deprecated in NumPy 2.0)",
        DeprecationWarning,
        stacklevel=2
    )

    # Set default kwargs for genfromtxt as relevant to csv import.
    kwargs.setdefault("case_sensitive", "lower")
    kwargs.setdefault("names", True)
    kwargs.setdefault("delimiter", ",")
    kwargs.setdefault("dtype", None)
    output = genfromtxt(fname, **kwargs)

    usemask = kwargs.get("usemask", False)
    if usemask:
        from numpy.ma.mrecords import MaskedRecords
        output = output.view(MaskedRecords)
    else:
        output = output.view(np.recarray)
    return output

# === NexusCore/src\code_interpreter\OpenCodeInterpreter.py ===
import sys
import os

prj_root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(prj_root_path)

from code_interpreter.BaseCodeInterpreter import BaseCodeInterpreter
from utils.const import *

from typing import List, Tuple, Dict
import re

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="transformers")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"


class OpenCodeInterpreter(BaseCodeInterpreter):
    def __init__(
        self,
        model_path: str,
        load_in_8bit: bool = False,
        load_in_4bit: bool = False,
    ):
        # build tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            padding_side="right",
            trust_remote_code=True
        )

        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            device_map="auto",
            load_in_4bit=load_in_4bit,
            load_in_8bit=load_in_8bit,
            torch_dtype=torch.float16,
            trust_remote_code=True
        )

        self.model.resize_token_embeddings(len(self.tokenizer))

        self.model = self.model.eval()

        self.dialog = []
        self.MAX_CODE_OUTPUT_LENGTH = 1000
        

    def dialog_to_prompt(self, dialog: List[Dict]) -> str:
        full_str = self.tokenizer.apply_chat_template(dialog, tokenize=False)

        return full_str

    def extract_code_blocks(self, prompt: str) -> Tuple[bool, str]:
        pattern = re.escape("```python") + r"(.*?)" + re.escape("```")
        matches = re.findall(pattern, prompt, re.DOTALL)

        if matches:
            # Return the last matched code block
            return True, matches[-1].strip()
        else:
            return False, ""

    def clean_code_output(self, output: str) -> str:
        if self.MAX_CODE_OUTPUT_LENGTH < len(output):
            return (
                output[: self.MAX_CODE_OUTPUT_LENGTH // 5]
                + "\n...(truncated due to length)...\n"
                + output[-self.MAX_CODE_OUTPUT_LENGTH // 5 :]
            )

        return output

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\code_interpreter\OpenCodeInterpreter.py ===
import sys
import os

prj_root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(prj_root_path)

from code_interpreter.BaseCodeInterpreter import BaseCodeInterpreter
from utils.const import *

from typing import List, Tuple, Dict
import re

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="transformers")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"


class OpenCodeInterpreter(BaseCodeInterpreter):
    def __init__(
        self,
        model_path: str,
        load_in_8bit: bool = False,
        load_in_4bit: bool = False,
    ):
        # build tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            padding_side="right",
            trust_remote_code=True
        )

        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            device_map="auto",
            load_in_4bit=load_in_4bit,
            load_in_8bit=load_in_8bit,
            torch_dtype=torch.float16,
            trust_remote_code=True
        )

        self.model.resize_token_embeddings(len(self.tokenizer))

        self.model = self.model.eval()

        self.dialog = []
        self.MAX_CODE_OUTPUT_LENGTH = 1000
        

    def dialog_to_prompt(self, dialog: List[Dict]) -> str:
        full_str = self.tokenizer.apply_chat_template(dialog, tokenize=False)

        return full_str

    def extract_code_blocks(self, prompt: str) -> Tuple[bool, str]:
        pattern = re.escape("```python") + r"(.*?)" + re.escape("```")
        matches = re.findall(pattern, prompt, re.DOTALL)

        if matches:
            # Return the last matched code block
            return True, matches[-1].strip()
        else:
            return False, ""

    def clean_code_output(self, output: str) -> str:
        if self.MAX_CODE_OUTPUT_LENGTH < len(output):
            return (
                output[: self.MAX_CODE_OUTPUT_LENGTH // 5]
                + "\n...(truncated due to length)...\n"
                + output[-self.MAX_CODE_OUTPUT_LENGTH // 5 :]
            )

        return output

# === NexusCore/exported_projects\app_20250703_223016\app\utils\image_crawler.py ===
# image_crawler.py ─ DeepLab v3 (MobileNetV3-ONNX 版)
# 依存: torch torchvision onnx opencv-python numpy icrawler requests
# ------------------------------------------------------------
from __future__ import annotations
import cv2, numpy as np, requests
from icrawler.builtin import BingImageCrawler, GoogleImageCrawler
from pathlib import Path
from typing import List

# 1. モデルファイル
MODEL_DIR  = Path(__file__).parent / "models"
ONNX_FILE  = MODEL_DIR / "deeplabv3_mnv3.onnx"

# 2. ダウンロード処理は廃止（ローカルに無ければ明示エラー）
def ensure_model() -> None:
    if ONNX_FILE.exists():
        print("✓ DeepLab ONNX モデルは既に存在します")
        return
    raise FileNotFoundError(
        f"{ONNX_FILE.name} がありません。\n"
        "1) app/utils/models で make_deeplab_onnx.py を実行して生成する\n"
        "2) 生成した deeplabv3_mnv3.onnx を models フォルダに置いて再実行してください"
    )

# 3. 深度学習セグメンテーション
class DeepLabSeg:
    def __init__(self, onnx: Path, use_cuda=False):
        self.net = cv2.dnn.readNetFromONNX(str(onnx))
        backend = cv2.dnn.DNN_BACKEND_CUDA if use_cuda else cv2.dnn.DNN_BACKEND_OPENCV
        target  = cv2.dnn.DNN_TARGET_CUDA  if use_cuda else cv2.dnn.DNN_TARGET_CPU
        self.net.setPreferableBackend(backend)
        self.net.setPreferableTarget(target)

    def remove_bg(self, img: np.ndarray, blur=5) -> np.ndarray:
        h, w = img.shape[:2]
        blob = cv2.dnn.blobFromImage(img, 1/127.5, (513, 513), (127.5,)*3, swapRB=True)
        self.net.setInput(blob)
        mask = self.net.forward()[0].argmax(0).astype(np.uint8)
        mask = cv2.resize(mask, (w, h), cv2.INTER_NEAREST)
        fg_mask = cv2.medianBlur(mask*255, blur) if blur else mask*255
        fg = cv2.bitwise_and(img, img, mask=fg_mask)
        return np.where(fg_mask[..., None] == 255, fg, 255)

# 4. 画像検索＋背景除去
def crawl_and_remove_bg(keyword: str, max_num=30,
                        engines: List[str] | None = None,
                        use_cuda=False) -> Path:
    engines = engines or ["bing", "google"]
    out_dir = Path(__file__).parent / "images" / keyword.replace(" ", "_")
    out_dir.mkdir(parents=True, exist_ok=True)

    if "bing" in engines:
        BingImageCrawler(storage={"root_dir": str(out_dir)}).crawl(keyword, max_num)
    if "google" in engines:
        GoogleImageCrawler(storage={"root_dir": str(out_dir)}).crawl(keyword, max_num)

    ensure_model()
    seg = DeepLabSeg(ONNX_FILE, use_cuda)

    for p in out_dir.glob("*.jpg"):
        try:
            img = cv2.imread(str(p))
            out_path = p.with_stem(p.stem + "_bg").with_suffix(".png")
            cv2.imwrite(str(out_path), seg.remove_bg(img))
            print("✓", p.name)
        except Exception as e:
            print("×", p.name, e)
    return out_dir

def crawl_images(keyword, max_num=50, engines=None):
    return crawl_and_remove_bg(keyword, max_num, engines or ["bing", "google"])

# 5. CLI
if __name__ == "__main__":
    kw = input("検索キーワードを入力してください：")
    print("完了→", crawl_and_remove_bg(kw, 50, ["bing"]).resolve())

# === NexusCore/exported_projects\project_export_m73owrzi\app\utils\image_crawler.py ===
# image_crawler.py ─ DeepLab v3 (MobileNetV3-ONNX 版)
# 依存: torch torchvision onnx opencv-python numpy icrawler requests
# ------------------------------------------------------------
from __future__ import annotations
import cv2, numpy as np, requests
from icrawler.builtin import BingImageCrawler, GoogleImageCrawler
from pathlib import Path
from typing import List

# 1. モデルファイル
MODEL_DIR  = Path(__file__).parent / "models"
ONNX_FILE  = MODEL_DIR / "deeplabv3_mnv3.onnx"

# 2. ダウンロード処理は廃止（ローカルに無ければ明示エラー）
def ensure_model() -> None:
    if ONNX_FILE.exists():
        print("✓ DeepLab ONNX モデルは既に存在します")
        return
    raise FileNotFoundError(
        f"{ONNX_FILE.name} がありません。\n"
        "1) app/utils/models で make_deeplab_onnx.py を実行して生成する\n"
        "2) 生成した deeplabv3_mnv3.onnx を models フォルダに置いて再実行してください"
    )

# 3. 深度学習セグメンテーション
class DeepLabSeg:
    def __init__(self, onnx: Path, use_cuda=False):
        self.net = cv2.dnn.readNetFromONNX(str(onnx))
        backend = cv2.dnn.DNN_BACKEND_CUDA if use_cuda else cv2.dnn.DNN_BACKEND_OPENCV
        target  = cv2.dnn.DNN_TARGET_CUDA  if use_cuda else cv2.dnn.DNN_TARGET_CPU
        self.net.setPreferableBackend(backend)
        self.net.setPreferableTarget(target)

    def remove_bg(self, img: np.ndarray, blur=5) -> np.ndarray:
        h, w = img.shape[:2]
        blob = cv2.dnn.blobFromImage(img, 1/127.5, (513, 513), (127.5,)*3, swapRB=True)
        self.net.setInput(blob)
        mask = self.net.forward()[0].argmax(0).astype(np.uint8)
        mask = cv2.resize(mask, (w, h), cv2.INTER_NEAREST)
        fg_mask = cv2.medianBlur(mask*255, blur) if blur else mask*255
        fg = cv2.bitwise_and(img, img, mask=fg_mask)
        return np.where(fg_mask[..., None] == 255, fg, 255)

# 4. 画像検索＋背景除去
def crawl_and_remove_bg(keyword: str, max_num=30,
                        engines: List[str] | None = None,
                        use_cuda=False) -> Path:
    engines = engines or ["bing", "google"]
    out_dir = Path(__file__).parent / "images" / keyword.replace(" ", "_")
    out_dir.mkdir(parents=True, exist_ok=True)

    if "bing" in engines:
        BingImageCrawler(storage={"root_dir": str(out_dir)}).crawl(keyword, max_num)
    if "google" in engines:
        GoogleImageCrawler(storage={"root_dir": str(out_dir)}).crawl(keyword, max_num)

    ensure_model()
    seg = DeepLabSeg(ONNX_FILE, use_cuda)

    for p in out_dir.glob("*.jpg"):
        try:
            img = cv2.imread(str(p))
            out_path = p.with_stem(p.stem + "_bg").with_suffix(".png")
            cv2.imwrite(str(out_path), seg.remove_bg(img))
            print("✓", p.name)
        except Exception as e:
            print("×", p.name, e)
    return out_dir

def crawl_images(keyword, max_num=50, engines=None):
    return crawl_and_remove_bg(keyword, max_num, engines or ["bing", "google"])

# 5. CLI
if __name__ == "__main__":
    kw = input("検索キーワードを入力してください：")
    print("完了→", crawl_and_remove_bg(kw, 50, ["bing"]).resolve())

# === NexusCore/exported_projects\project_export_xb_l70t8\app\utils\image_crawler.py ===
# image_crawler.py ─ DeepLab v3 (MobileNetV3-ONNX 版)
# 依存: torch torchvision onnx opencv-python numpy icrawler requests
# ------------------------------------------------------------
from __future__ import annotations
import cv2, numpy as np, requests
from icrawler.builtin import BingImageCrawler, GoogleImageCrawler
from pathlib import Path
from typing import List

# 1. モデルファイル
MODEL_DIR  = Path(__file__).parent / "models"
ONNX_FILE  = MODEL_DIR / "deeplabv3_mnv3.onnx"

# 2. ダウンロード処理は廃止（ローカルに無ければ明示エラー）
def ensure_model() -> None:
    if ONNX_FILE.exists():
        print("✓ DeepLab ONNX モデルは既に存在します")
        return
    raise FileNotFoundError(
        f"{ONNX_FILE.name} がありません。\n"
        "1) app/utils/models で make_deeplab_onnx.py を実行して生成する\n"
        "2) 生成した deeplabv3_mnv3.onnx を models フォルダに置いて再実行してください"
    )

# 3. 深度学習セグメンテーション
class DeepLabSeg:
    def __init__(self, onnx: Path, use_cuda=False):
        self.net = cv2.dnn.readNetFromONNX(str(onnx))
        backend = cv2.dnn.DNN_BACKEND_CUDA if use_cuda else cv2.dnn.DNN_BACKEND_OPENCV
        target  = cv2.dnn.DNN_TARGET_CUDA  if use_cuda else cv2.dnn.DNN_TARGET_CPU
        self.net.setPreferableBackend(backend)
        self.net.setPreferableTarget(target)

    def remove_bg(self, img: np.ndarray, blur=5) -> np.ndarray:
        h, w = img.shape[:2]
        blob = cv2.dnn.blobFromImage(img, 1/127.5, (513, 513), (127.5,)*3, swapRB=True)
        self.net.setInput(blob)
        mask = self.net.forward()[0].argmax(0).astype(np.uint8)
        mask = cv2.resize(mask, (w, h), cv2.INTER_NEAREST)
        fg_mask = cv2.medianBlur(mask*255, blur) if blur else mask*255
        fg = cv2.bitwise_and(img, img, mask=fg_mask)
        return np.where(fg_mask[..., None] == 255, fg, 255)

# 4. 画像検索＋背景除去
def crawl_and_remove_bg(keyword: str, max_num=30,
                        engines: List[str] | None = None,
                        use_cuda=False) -> Path:
    engines = engines or ["bing", "google"]
    out_dir = Path(__file__).parent / "images" / keyword.replace(" ", "_")
    out_dir.mkdir(parents=True, exist_ok=True)

    if "bing" in engines:
        BingImageCrawler(storage={"root_dir": str(out_dir)}).crawl(keyword, max_num)
    if "google" in engines:
        GoogleImageCrawler(storage={"root_dir": str(out_dir)}).crawl(keyword, max_num)

    ensure_model()
    seg = DeepLabSeg(ONNX_FILE, use_cuda)

    for p in out_dir.glob("*.jpg"):
        try:
            img = cv2.imread(str(p))
            out_path = p.with_stem(p.stem + "_bg").with_suffix(".png")
            cv2.imwrite(str(out_path), seg.remove_bg(img))
            print("✓", p.name)
        except Exception as e:
            print("×", p.name, e)
    return out_dir

def crawl_images(keyword, max_num=50, engines=None):
    return crawl_and_remove_bg(keyword, max_num, engines or ["bing", "google"])

# 5. CLI
if __name__ == "__main__":
    kw = input("検索キーワードを入力してください：")
    print("完了→", crawl_and_remove_bg(kw, 50, ["bing"]).resolve())

# === NexusCore/exported_projects\project_export_y7xxp1v8\app\utils\image_crawler.py ===
# image_crawler.py ─ DeepLab v3 (MobileNetV3-ONNX 版)
# 依存: torch torchvision onnx opencv-python numpy icrawler requests
# ------------------------------------------------------------
from __future__ import annotations
import cv2, numpy as np, requests
from icrawler.builtin import BingImageCrawler, GoogleImageCrawler
from pathlib import Path
from typing import List

# 1. モデルファイル
MODEL_DIR  = Path(__file__).parent / "models"
ONNX_FILE  = MODEL_DIR / "deeplabv3_mnv3.onnx"

# 2. ダウンロード処理は廃止（ローカルに無ければ明示エラー）
def ensure_model() -> None:
    if ONNX_FILE.exists():
        print("✓ DeepLab ONNX モデルは既に存在します")
        return
    raise FileNotFoundError(
        f"{ONNX_FILE.name} がありません。\n"
        "1) app/utils/models で make_deeplab_onnx.py を実行して生成する\n"
        "2) 生成した deeplabv3_mnv3.onnx を models フォルダに置いて再実行してください"
    )

# 3. 深度学習セグメンテーション
class DeepLabSeg:
    def __init__(self, onnx: Path, use_cuda=False):
        self.net = cv2.dnn.readNetFromONNX(str(onnx))
        backend = cv2.dnn.DNN_BACKEND_CUDA if use_cuda else cv2.dnn.DNN_BACKEND_OPENCV
        target  = cv2.dnn.DNN_TARGET_CUDA  if use_cuda else cv2.dnn.DNN_TARGET_CPU
        self.net.setPreferableBackend(backend)
        self.net.setPreferableTarget(target)

    def remove_bg(self, img: np.ndarray, blur=5) -> np.ndarray:
        h, w = img.shape[:2]
        blob = cv2.dnn.blobFromImage(img, 1/127.5, (513, 513), (127.5,)*3, swapRB=True)
        self.net.setInput(blob)
        mask = self.net.forward()[0].argmax(0).astype(np.uint8)
        mask = cv2.resize(mask, (w, h), cv2.INTER_NEAREST)
        fg_mask = cv2.medianBlur(mask*255, blur) if blur else mask*255
        fg = cv2.bitwise_and(img, img, mask=fg_mask)
        return np.where(fg_mask[..., None] == 255, fg, 255)

# 4. 画像検索＋背景除去
def crawl_and_remove_bg(keyword: str, max_num=30,
                        engines: List[str] | None = None,
                        use_cuda=False) -> Path:
    engines = engines or ["bing", "google"]
    out_dir = Path(__file__).parent / "images" / keyword.replace(" ", "_")
    out_dir.mkdir(parents=True, exist_ok=True)

    if "bing" in engines:
        BingImageCrawler(storage={"root_dir": str(out_dir)}).crawl(keyword, max_num)
    if "google" in engines:
        GoogleImageCrawler(storage={"root_dir": str(out_dir)}).crawl(keyword, max_num)

    ensure_model()
    seg = DeepLabSeg(ONNX_FILE, use_cuda)

    for p in out_dir.glob("*.jpg"):
        try:
            img = cv2.imread(str(p))
            out_path = p.with_stem(p.stem + "_bg").with_suffix(".png")
            cv2.imwrite(str(out_path), seg.remove_bg(img))
            print("✓", p.name)
        except Exception as e:
            print("×", p.name, e)
    return out_dir

def crawl_images(keyword, max_num=50, engines=None):
    return crawl_and_remove_bg(keyword, max_num, engines or ["bing", "google"])

# 5. CLI
if __name__ == "__main__":
    kw = input("検索キーワードを入力してください：")
    print("完了→", crawl_and_remove_bg(kw, 50, ["bing"]).resolve())

# === NexusCore/src\audio\voice_to_text.py ===
import os
from dotenv import load_dotenv
import openai
import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np
import threading
import time
import tempfile

# .envファイルから環境変数を読み込む
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def record_until_keypress(max_duration=60, sample_rate=16000):
    """
    エンターキーが押されるか、最大max_duration秒まで録音
    """
    print(f"録音中... 最大{max_duration}秒、エンターキーで終了します")
    recording = []
    event = threading.Event()
    start_time = time.time()

    def callback(indata, frames, t, status):
        # 最大時間を超えたら録音停止
        if time.time() - start_time > max_duration:
            event.set()
            raise sd.CallbackAbort
        recording.append(indata.copy())

    def record_thread():
        with sd.InputStream(samplerate=sample_rate, channels=1, callback=callback):
            event.wait()

    def key_thread():
        input()  # エンターキー待ち
        event.set()

    t1 = threading.Thread(target=record_thread)
    t2 = threading.Thread(target=key_thread)
    t1.start()
    t2.start()
    t2.join(timeout=max_duration)
    t1.join(timeout=1)

    if recording:
        return np.concatenate(recording, axis=0), sample_rate
    return None, sample_rate

def transcribe_with_whisper(audio_path):
    """Whisper APIで音声ファイルを文字起こし"""
    with open(audio_path, "rb") as f:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="ja",
            response_format="text"
        )
    return transcript

if __name__ == "__main__":
    audio_data, fs = record_until_keypress(max_duration=60)
    if audio_data is not None:
        print(f"録音終了: {len(audio_data)/fs:.2f}秒の音声を録音しました")
        # 一時ファイルに保存
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        write(temp_file.name, fs, audio_data)
        try:
            # Whisper APIで文字起こし
            text = transcribe_with_whisper(temp_file.name)
            print("\nWhisper認識結果:")
            print(text)
        finally:
            os.unlink(temp_file.name)
    else:
        print("録音データがありません")

# === NexusCore/src\code_interpreter\sandbox_runner.py ===
import os
import tempfile
import subprocess
import shutil
import difflib

from utils.test_generator import generate_unit_tests
from utils.repair_module import gpt_repair_code

# 非ASCIIコメントを除去する関数
def remove_non_ascii_comments(code: str) -> str:
    lines = code.splitlines()
    cleaned = []
    for line in lines:
        if "#" in line:
            code_part, comment = line.split("#", 1)
            comment = ''.join(c for c in comment if ord(c) < 128)
            cleaned.append(f"{code_part}# {comment}".rstrip())
        else:
            cleaned.append(line)
    return "\n".join(cleaned)

# 有意な変更かを判定（厳格ではなく緩やかな差分検出）
def is_meaningful_change(before: str, after: str) -> bool:
    ratio = difflib.SequenceMatcher(None, before.strip(), after.strip()).ratio()
    return ratio < 0.98

# 修正＋ユニットテスト実行
def run_test_and_repair(user_code: str, max_retries: int = 3):
    current_code = remove_non_ascii_comments(user_code)
    test_code = generate_unit_tests(current_code)
    
    os.makedirs("sandbox_output", exist_ok=True)
    
    for attempt in range(max_retries):
        print(f"\n🔁 修正サイクル {attempt + 1}")
        
        # 書き出し
        with tempfile.TemporaryDirectory() as tempdir:
            code_path = os.path.join(tempdir, "target_code.py")
            test_path = os.path.join(tempdir, "test_main.py")

            with open(code_path, "w", encoding="utf-8") as f:
                f.write(current_code)

            with open(test_path, "w", encoding="utf-8") as f:
                f.write(test_code)

            try:
                result = subprocess.run(
                    ["pytest", test_path, "-q", "--tb=short"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=tempdir
                )
                print(result.stdout)
                print(result.stderr)

                if result.returncode == 0:
                    print("✅ テスト成功")
                    shutil.copy(code_path, "sandbox_output/final_code.py")
                    shutil.copy(test_path, "sandbox_output/test_main.py")
                    return current_code, test_code, True, result.stdout + result.stderr

            except subprocess.TimeoutExpired:
                print("⏰ テストタイムアウト")

        # 修正処理
        fixed = gpt_repair_code(current_code, test_code)
        if not is_meaningful_change(current_code, fixed):
            print("⚠️ 意味的な変化なし：強制継続")
        current_code = fixed

    print("❌ テスト失敗（最大試行回数）")
    return current_code, test_code, False, "最大試行回数を超えました"

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\app_20250703_223016\app\utils\image_crawler.py ===
# image_crawler.py ─ DeepLab v3 (MobileNetV3-ONNX 版)
# 依存: torch torchvision onnx opencv-python numpy icrawler requests
# ------------------------------------------------------------
from __future__ import annotations
import cv2, numpy as np, requests
from icrawler.builtin import BingImageCrawler, GoogleImageCrawler
from pathlib import Path
from typing import List

# 1. モデルファイル
MODEL_DIR  = Path(__file__).parent / "models"
ONNX_FILE  = MODEL_DIR / "deeplabv3_mnv3.onnx"

# 2. ダウンロード処理は廃止（ローカルに無ければ明示エラー）
def ensure_model() -> None:
    if ONNX_FILE.exists():
        print("✓ DeepLab ONNX モデルは既に存在します")
        return
    raise FileNotFoundError(
        f"{ONNX_FILE.name} がありません。\n"
        "1) app/utils/models で make_deeplab_onnx.py を実行して生成する\n"
        "2) 生成した deeplabv3_mnv3.onnx を models フォルダに置いて再実行してください"
    )

# 3. 深度学習セグメンテーション
class DeepLabSeg:
    def __init__(self, onnx: Path, use_cuda=False):
        self.net = cv2.dnn.readNetFromONNX(str(onnx))
        backend = cv2.dnn.DNN_BACKEND_CUDA if use_cuda else cv2.dnn.DNN_BACKEND_OPENCV
        target  = cv2.dnn.DNN_TARGET_CUDA  if use_cuda else cv2.dnn.DNN_TARGET_CPU
        self.net.setPreferableBackend(backend)
        self.net.setPreferableTarget(target)

    def remove_bg(self, img: np.ndarray, blur=5) -> np.ndarray:
        h, w = img.shape[:2]
        blob = cv2.dnn.blobFromImage(img, 1/127.5, (513, 513), (127.5,)*3, swapRB=True)
        self.net.setInput(blob)
        mask = self.net.forward()[0].argmax(0).astype(np.uint8)
        mask = cv2.resize(mask, (w, h), cv2.INTER_NEAREST)
        fg_mask = cv2.medianBlur(mask*255, blur) if blur else mask*255
        fg = cv2.bitwise_and(img, img, mask=fg_mask)
        return np.where(fg_mask[..., None] == 255, fg, 255)

# 4. 画像検索＋背景除去
def crawl_and_remove_bg(keyword: str, max_num=30,
                        engines: List[str] | None = None,
                        use_cuda=False) -> Path:
    engines = engines or ["bing", "google"]
    out_dir = Path(__file__).parent / "images" / keyword.replace(" ", "_")
    out_dir.mkdir(parents=True, exist_ok=True)

    if "bing" in engines:
        BingImageCrawler(storage={"root_dir": str(out_dir)}).crawl(keyword, max_num)
    if "google" in engines:
        GoogleImageCrawler(storage={"root_dir": str(out_dir)}).crawl(keyword, max_num)

    ensure_model()
    seg = DeepLabSeg(ONNX_FILE, use_cuda)

    for p in out_dir.glob("*.jpg"):
        try:
            img = cv2.imread(str(p))
            out_path = p.with_stem(p.stem + "_bg").with_suffix(".png")
            cv2.imwrite(str(out_path), seg.remove_bg(img))
            print("✓", p.name)
        except Exception as e:
            print("×", p.name, e)
    return out_dir

def crawl_images(keyword, max_num=50, engines=None):
    return crawl_and_remove_bg(keyword, max_num, engines or ["bing", "google"])

# 5. CLI
if __name__ == "__main__":
    kw = input("検索キーワードを入力してください：")
    print("完了→", crawl_and_remove_bg(kw, 50, ["bing"]).resolve())

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\project_export_m73owrzi\app\utils\image_crawler.py ===
# image_crawler.py ─ DeepLab v3 (MobileNetV3-ONNX 版)
# 依存: torch torchvision onnx opencv-python numpy icrawler requests
# ------------------------------------------------------------
from __future__ import annotations
import cv2, numpy as np, requests
from icrawler.builtin import BingImageCrawler, GoogleImageCrawler
from pathlib import Path
from typing import List

# 1. モデルファイル
MODEL_DIR  = Path(__file__).parent / "models"
ONNX_FILE  = MODEL_DIR / "deeplabv3_mnv3.onnx"

# 2. ダウンロード処理は廃止（ローカルに無ければ明示エラー）
def ensure_model() -> None:
    if ONNX_FILE.exists():
        print("✓ DeepLab ONNX モデルは既に存在します")
        return
    raise FileNotFoundError(
        f"{ONNX_FILE.name} がありません。\n"
        "1) app/utils/models で make_deeplab_onnx.py を実行して生成する\n"
        "2) 生成した deeplabv3_mnv3.onnx を models フォルダに置いて再実行してください"
    )

# 3. 深度学習セグメンテーション
class DeepLabSeg:
    def __init__(self, onnx: Path, use_cuda=False):
        self.net = cv2.dnn.readNetFromONNX(str(onnx))
        backend = cv2.dnn.DNN_BACKEND_CUDA if use_cuda else cv2.dnn.DNN_BACKEND_OPENCV
        target  = cv2.dnn.DNN_TARGET_CUDA  if use_cuda else cv2.dnn.DNN_TARGET_CPU
        self.net.setPreferableBackend(backend)
        self.net.setPreferableTarget(target)

    def remove_bg(self, img: np.ndarray, blur=5) -> np.ndarray:
        h, w = img.shape[:2]
        blob = cv2.dnn.blobFromImage(img, 1/127.5, (513, 513), (127.5,)*3, swapRB=True)
        self.net.setInput(blob)
        mask = self.net.forward()[0].argmax(0).astype(np.uint8)
        mask = cv2.resize(mask, (w, h), cv2.INTER_NEAREST)
        fg_mask = cv2.medianBlur(mask*255, blur) if blur else mask*255
        fg = cv2.bitwise_and(img, img, mask=fg_mask)
        return np.where(fg_mask[..., None] == 255, fg, 255)

# 4. 画像検索＋背景除去
def crawl_and_remove_bg(keyword: str, max_num=30,
                        engines: List[str] | None = None,
                        use_cuda=False) -> Path:
    engines = engines or ["bing", "google"]
    out_dir = Path(__file__).parent / "images" / keyword.replace(" ", "_")
    out_dir.mkdir(parents=True, exist_ok=True)

    if "bing" in engines:
        BingImageCrawler(storage={"root_dir": str(out_dir)}).crawl(keyword, max_num)
    if "google" in engines:
        GoogleImageCrawler(storage={"root_dir": str(out_dir)}).crawl(keyword, max_num)

    ensure_model()
    seg = DeepLabSeg(ONNX_FILE, use_cuda)

    for p in out_dir.glob("*.jpg"):
        try:
            img = cv2.imread(str(p))
            out_path = p.with_stem(p.stem + "_bg").with_suffix(".png")
            cv2.imwrite(str(out_path), seg.remove_bg(img))
            print("✓", p.name)
        except Exception as e:
            print("×", p.name, e)
    return out_dir

def crawl_images(keyword, max_num=50, engines=None):
    return crawl_and_remove_bg(keyword, max_num, engines or ["bing", "google"])

# 5. CLI
if __name__ == "__main__":
    kw = input("検索キーワードを入力してください：")
    print("完了→", crawl_and_remove_bg(kw, 50, ["bing"]).resolve())

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\project_export_xb_l70t8\app\utils\image_crawler.py ===
# image_crawler.py ─ DeepLab v3 (MobileNetV3-ONNX 版)
# 依存: torch torchvision onnx opencv-python numpy icrawler requests
# ------------------------------------------------------------
from __future__ import annotations
import cv2, numpy as np, requests
from icrawler.builtin import BingImageCrawler, GoogleImageCrawler
from pathlib import Path
from typing import List

# 1. モデルファイル
MODEL_DIR  = Path(__file__).parent / "models"
ONNX_FILE  = MODEL_DIR / "deeplabv3_mnv3.onnx"

# 2. ダウンロード処理は廃止（ローカルに無ければ明示エラー）
def ensure_model() -> None:
    if ONNX_FILE.exists():
        print("✓ DeepLab ONNX モデルは既に存在します")
        return
    raise FileNotFoundError(
        f"{ONNX_FILE.name} がありません。\n"
        "1) app/utils/models で make_deeplab_onnx.py を実行して生成する\n"
        "2) 生成した deeplabv3_mnv3.onnx を models フォルダに置いて再実行してください"
    )

# 3. 深度学習セグメンテーション
class DeepLabSeg:
    def __init__(self, onnx: Path, use_cuda=False):
        self.net = cv2.dnn.readNetFromONNX(str(onnx))
        backend = cv2.dnn.DNN_BACKEND_CUDA if use_cuda else cv2.dnn.DNN_BACKEND_OPENCV
        target  = cv2.dnn.DNN_TARGET_CUDA  if use_cuda else cv2.dnn.DNN_TARGET_CPU
        self.net.setPreferableBackend(backend)
        self.net.setPreferableTarget(target)

    def remove_bg(self, img: np.ndarray, blur=5) -> np.ndarray:
        h, w = img.shape[:2]
        blob = cv2.dnn.blobFromImage(img, 1/127.5, (513, 513), (127.5,)*3, swapRB=True)
        self.net.setInput(blob)
        mask = self.net.forward()[0].argmax(0).astype(np.uint8)
        mask = cv2.resize(mask, (w, h), cv2.INTER_NEAREST)
        fg_mask = cv2.medianBlur(mask*255, blur) if blur else mask*255
        fg = cv2.bitwise_and(img, img, mask=fg_mask)
        return np.where(fg_mask[..., None] == 255, fg, 255)

# 4. 画像検索＋背景除去
def crawl_and_remove_bg(keyword: str, max_num=30,
                        engines: List[str] | None = None,
                        use_cuda=False) -> Path:
    engines = engines or ["bing", "google"]
    out_dir = Path(__file__).parent / "images" / keyword.replace(" ", "_")
    out_dir.mkdir(parents=True, exist_ok=True)

    if "bing" in engines:
        BingImageCrawler(storage={"root_dir": str(out_dir)}).crawl(keyword, max_num)
    if "google" in engines:
        GoogleImageCrawler(storage={"root_dir": str(out_dir)}).crawl(keyword, max_num)

    ensure_model()
    seg = DeepLabSeg(ONNX_FILE, use_cuda)

    for p in out_dir.glob("*.jpg"):
        try:
            img = cv2.imread(str(p))
            out_path = p.with_stem(p.stem + "_bg").with_suffix(".png")
            cv2.imwrite(str(out_path), seg.remove_bg(img))
            print("✓", p.name)
        except Exception as e:
            print("×", p.name, e)
    return out_dir

def crawl_images(keyword, max_num=50, engines=None):
    return crawl_and_remove_bg(keyword, max_num, engines or ["bing", "google"])

# 5. CLI
if __name__ == "__main__":
    kw = input("検索キーワードを入力してください：")
    print("完了→", crawl_and_remove_bg(kw, 50, ["bing"]).resolve())

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\project_export_y7xxp1v8\app\utils\image_crawler.py ===
# image_crawler.py ─ DeepLab v3 (MobileNetV3-ONNX 版)
# 依存: torch torchvision onnx opencv-python numpy icrawler requests
# ------------------------------------------------------------
from __future__ import annotations
import cv2, numpy as np, requests
from icrawler.builtin import BingImageCrawler, GoogleImageCrawler
from pathlib import Path
from typing import List

# 1. モデルファイル
MODEL_DIR  = Path(__file__).parent / "models"
ONNX_FILE  = MODEL_DIR / "deeplabv3_mnv3.onnx"

# 2. ダウンロード処理は廃止（ローカルに無ければ明示エラー）
def ensure_model() -> None:
    if ONNX_FILE.exists():
        print("✓ DeepLab ONNX モデルは既に存在します")
        return
    raise FileNotFoundError(
        f"{ONNX_FILE.name} がありません。\n"
        "1) app/utils/models で make_deeplab_onnx.py を実行して生成する\n"
        "2) 生成した deeplabv3_mnv3.onnx を models フォルダに置いて再実行してください"
    )

# 3. 深度学習セグメンテーション
class DeepLabSeg:
    def __init__(self, onnx: Path, use_cuda=False):
        self.net = cv2.dnn.readNetFromONNX(str(onnx))
        backend = cv2.dnn.DNN_BACKEND_CUDA if use_cuda else cv2.dnn.DNN_BACKEND_OPENCV
        target  = cv2.dnn.DNN_TARGET_CUDA  if use_cuda else cv2.dnn.DNN_TARGET_CPU
        self.net.setPreferableBackend(backend)
        self.net.setPreferableTarget(target)

    def remove_bg(self, img: np.ndarray, blur=5) -> np.ndarray:
        h, w = img.shape[:2]
        blob = cv2.dnn.blobFromImage(img, 1/127.5, (513, 513), (127.5,)*3, swapRB=True)
        self.net.setInput(blob)
        mask = self.net.forward()[0].argmax(0).astype(np.uint8)
        mask = cv2.resize(mask, (w, h), cv2.INTER_NEAREST)
        fg_mask = cv2.medianBlur(mask*255, blur) if blur else mask*255
        fg = cv2.bitwise_and(img, img, mask=fg_mask)
        return np.where(fg_mask[..., None] == 255, fg, 255)

# 4. 画像検索＋背景除去
def crawl_and_remove_bg(keyword: str, max_num=30,
                        engines: List[str] | None = None,
                        use_cuda=False) -> Path:
    engines = engines or ["bing", "google"]
    out_dir = Path(__file__).parent / "images" / keyword.replace(" ", "_")
    out_dir.mkdir(parents=True, exist_ok=True)

    if "bing" in engines:
        BingImageCrawler(storage={"root_dir": str(out_dir)}).crawl(keyword, max_num)
    if "google" in engines:
        GoogleImageCrawler(storage={"root_dir": str(out_dir)}).crawl(keyword, max_num)

    ensure_model()
    seg = DeepLabSeg(ONNX_FILE, use_cuda)

    for p in out_dir.glob("*.jpg"):
        try:
            img = cv2.imread(str(p))
            out_path = p.with_stem(p.stem + "_bg").with_suffix(".png")
            cv2.imwrite(str(out_path), seg.remove_bg(img))
            print("✓", p.name)
        except Exception as e:
            print("×", p.name, e)
    return out_dir

def crawl_images(keyword, max_num=50, engines=None):
    return crawl_and_remove_bg(keyword, max_num, engines or ["bing", "google"])

# 5. CLI
if __name__ == "__main__":
    kw = input("検索キーワードを入力してください：")
    print("完了→", crawl_and_remove_bg(kw, 50, ["bing"]).resolve())

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\audio\voice_to_text.py ===
import os
from dotenv import load_dotenv
import openai
import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np
import threading
import time
import tempfile

# .envファイルから環境変数を読み込む
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def record_until_keypress(max_duration=60, sample_rate=16000):
    """
    エンターキーが押されるか、最大max_duration秒まで録音
    """
    print(f"録音中... 最大{max_duration}秒、エンターキーで終了します")
    recording = []
    event = threading.Event()
    start_time = time.time()

    def callback(indata, frames, t, status):
        # 最大時間を超えたら録音停止
        if time.time() - start_time > max_duration:
            event.set()
            raise sd.CallbackAbort
        recording.append(indata.copy())

    def record_thread():
        with sd.InputStream(samplerate=sample_rate, channels=1, callback=callback):
            event.wait()

    def key_thread():
        input()  # エンターキー待ち
        event.set()

    t1 = threading.Thread(target=record_thread)
    t2 = threading.Thread(target=key_thread)
    t1.start()
    t2.start()
    t2.join(timeout=max_duration)
    t1.join(timeout=1)

    if recording:
        return np.concatenate(recording, axis=0), sample_rate
    return None, sample_rate

def transcribe_with_whisper(audio_path):
    """Whisper APIで音声ファイルを文字起こし"""
    with open(audio_path, "rb") as f:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="ja",
            response_format="text"
        )
    return transcript

if __name__ == "__main__":
    audio_data, fs = record_until_keypress(max_duration=60)
    if audio_data is not None:
        print(f"録音終了: {len(audio_data)/fs:.2f}秒の音声を録音しました")
        # 一時ファイルに保存
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        write(temp_file.name, fs, audio_data)
        try:
            # Whisper APIで文字起こし
            text = transcribe_with_whisper(temp_file.name)
            print("\nWhisper認識結果:")
            print(text)
        finally:
            os.unlink(temp_file.name)
    else:
        print("録音データがありません")

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\code_interpreter\sandbox_runner.py ===
import os
import tempfile
import subprocess
import shutil
import difflib

from utils.test_generator import generate_unit_tests
from utils.repair_module import gpt_repair_code

# 非ASCIIコメントを除去する関数
def remove_non_ascii_comments(code: str) -> str:
    lines = code.splitlines()
    cleaned = []
    for line in lines:
        if "#" in line:
            code_part, comment = line.split("#", 1)
            comment = ''.join(c for c in comment if ord(c) < 128)
            cleaned.append(f"{code_part}# {comment}".rstrip())
        else:
            cleaned.append(line)
    return "\n".join(cleaned)

# 有意な変更かを判定（厳格ではなく緩やかな差分検出）
def is_meaningful_change(before: str, after: str) -> bool:
    ratio = difflib.SequenceMatcher(None, before.strip(), after.strip()).ratio()
    return ratio < 0.98

# 修正＋ユニットテスト実行
def run_test_and_repair(user_code: str, max_retries: int = 3):
    current_code = remove_non_ascii_comments(user_code)
    test_code = generate_unit_tests(current_code)
    
    os.makedirs("sandbox_output", exist_ok=True)
    
    for attempt in range(max_retries):
        print(f"\n🔁 修正サイクル {attempt + 1}")
        
        # 書き出し
        with tempfile.TemporaryDirectory() as tempdir:
            code_path = os.path.join(tempdir, "target_code.py")
            test_path = os.path.join(tempdir, "test_main.py")

            with open(code_path, "w", encoding="utf-8") as f:
                f.write(current_code)

            with open(test_path, "w", encoding="utf-8") as f:
                f.write(test_code)

            try:
                result = subprocess.run(
                    ["pytest", test_path, "-q", "--tb=short"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=tempdir
                )
                print(result.stdout)
                print(result.stderr)

                if result.returncode == 0:
                    print("✅ テスト成功")
                    shutil.copy(code_path, "sandbox_output/final_code.py")
                    shutil.copy(test_path, "sandbox_output/test_main.py")
                    return current_code, test_code, True, result.stdout + result.stderr

            except subprocess.TimeoutExpired:
                print("⏰ テストタイムアウト")

        # 修正処理
        fixed = gpt_repair_code(current_code, test_code)
        if not is_meaningful_change(current_code, fixed):
            print("⚠️ 意味的な変化なし：強制継続")
        current_code = fixed

    print("❌ テスト失敗（最大試行回数）")
    return current_code, test_code, False, "最大試行回数を超えました"

# === NexusCore/data_collection\Local-Code-Interpreter\src\notebook_serializer.py ===
import nbformat
from nbformat import v4 as nbf
import ansi2html
import os
import argparse

# main code
parser = argparse.ArgumentParser()
parser.add_argument("-n", "--notebook", help="Path to the output notebook", default=None, type=str)
args = parser.parse_args()
if args.notebook:
    notebook_path = os.path.join(os.getcwd(), args.notebook)
    base, ext = os.path.splitext(notebook_path)
    if ext.lower() != '.ipynb':
        notebook_path += '.ipynb'
    if os.path.exists(notebook_path):
        print(f'File at {notebook_path} already exists. Please choose a different file name.')
        exit()

# Global variable for code cells
nb = nbf.new_notebook()


def ansi_to_html(ansi_text):
    converter = ansi2html.Ansi2HTMLConverter()
    html_text = converter.convert(ansi_text)
    return html_text


def write_to_notebook():
    if args.notebook:
        with open(notebook_path, 'w', encoding='utf-8') as f:
            nbformat.write(nb, f)


def add_code_cell_to_notebook(code):
    code_cell = nbf.new_code_cell(source=code)
    nb['cells'].append(code_cell)
    write_to_notebook()


def add_code_cell_output_to_notebook(output):
    html_content = ansi_to_html(output)
    cell_output = nbf.new_output(output_type='display_data', data={'text/html': html_content})
    nb['cells'][-1]['outputs'].append(cell_output)
    write_to_notebook()


def add_code_cell_error_to_notebook(error):
    nbf_error_output = nbf.new_output(
        output_type='error',
        ename='Error',
        evalue='Error message',
        traceback=[error]
    )
    nb['cells'][-1]['outputs'].append(nbf_error_output)
    write_to_notebook()


def add_image_to_notebook(image, mime_type):
    image_output = nbf.new_output(output_type='display_data', data={mime_type: image})
    nb['cells'][-1]['outputs'].append(image_output)
    write_to_notebook()


def add_markdown_to_notebook(content, title=None):
    if title:
        content = "##### " + title + ":\n" + content
    markdown_cell = nbf.new_markdown_cell(content)
    nb['cells'].append(markdown_cell)
    write_to_notebook()

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\Demos\app\dojobapp.py ===
# dojobapp - do a job, show the result in a dialog, and exit.
#
# Very simple - faily minimal dialog based app.
#
# This should be run using the command line:
# pythonwin /app demos\dojobapp.py


import win32con
import win32ui
from pywin.framework import dlgappcore


class DoJobAppDialog(dlgappcore.AppDialog):
    softspace = 1

    def __init__(self, appName=""):
        self.appName = appName
        dlgappcore.AppDialog.__init__(self, win32ui.IDD_GENERAL_STATUS)

    def PreDoModal(self):
        pass

    def ProcessArgs(self, args):
        pass

    def OnInitDialog(self):
        self.SetWindowText(self.appName)
        butCancel = self.GetDlgItem(win32con.IDCANCEL)
        butCancel.ShowWindow(win32con.SW_HIDE)
        p1 = self.GetDlgItem(win32ui.IDC_PROMPT1)
        p2 = self.GetDlgItem(win32ui.IDC_PROMPT2)

        # Do something here!

        p1.SetWindowText("Hello there")
        p2.SetWindowText("from the demo")

    def OnDestroy(self, msg):
        pass


# 	def OnOK(self):
# 		pass
# 	def OnCancel(self): default behaviour - cancel == close.
# 		return


class DoJobDialogApp(dlgappcore.DialogApp):
    def CreateDialog(self):
        return DoJobAppDialog("Do Something")


class CopyToDialogApp(DoJobDialogApp):
    def __init__(self):
        DoJobDialogApp.__init__(self)


app = DoJobDialogApp()


def t():
    t = DoJobAppDialog("Copy To")
    t.DoModal()
    return t


if __name__ == "__main__":
    import demoutils

    demoutils.NeedApp()

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\data_collection\Local-Code-Interpreter\src\notebook_serializer.py ===
import nbformat
from nbformat import v4 as nbf
import ansi2html
import os
import argparse

# main code
parser = argparse.ArgumentParser()
parser.add_argument("-n", "--notebook", help="Path to the output notebook", default=None, type=str)
args = parser.parse_args()
if args.notebook:
    notebook_path = os.path.join(os.getcwd(), args.notebook)
    base, ext = os.path.splitext(notebook_path)
    if ext.lower() != '.ipynb':
        notebook_path += '.ipynb'
    if os.path.exists(notebook_path):
        print(f'File at {notebook_path} already exists. Please choose a different file name.')
        exit()

# Global variable for code cells
nb = nbf.new_notebook()


def ansi_to_html(ansi_text):
    converter = ansi2html.Ansi2HTMLConverter()
    html_text = converter.convert(ansi_text)
    return html_text


def write_to_notebook():
    if args.notebook:
        with open(notebook_path, 'w', encoding='utf-8') as f:
            nbformat.write(nb, f)


def add_code_cell_to_notebook(code):
    code_cell = nbf.new_code_cell(source=code)
    nb['cells'].append(code_cell)
    write_to_notebook()


def add_code_cell_output_to_notebook(output):
    html_content = ansi_to_html(output)
    cell_output = nbf.new_output(output_type='display_data', data={'text/html': html_content})
    nb['cells'][-1]['outputs'].append(cell_output)
    write_to_notebook()


def add_code_cell_error_to_notebook(error):
    nbf_error_output = nbf.new_output(
        output_type='error',
        ename='Error',
        evalue='Error message',
        traceback=[error]
    )
    nb['cells'][-1]['outputs'].append(nbf_error_output)
    write_to_notebook()


def add_image_to_notebook(image, mime_type):
    image_output = nbf.new_output(output_type='display_data', data={mime_type: image})
    nb['cells'][-1]['outputs'].append(image_output)
    write_to_notebook()


def add_markdown_to_notebook(content, title=None):
    if title:
        content = "##### " + title + ":\n" + content
    markdown_cell = nbf.new_markdown_cell(content)
    nb['cells'].append(markdown_cell)
    write_to_notebook()

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pythonwin\pywin\Demos\app\dojobapp.py ===
# dojobapp - do a job, show the result in a dialog, and exit.
#
# Very simple - faily minimal dialog based app.
#
# This should be run using the command line:
# pythonwin /app demos\dojobapp.py


import win32con
import win32ui
from pywin.framework import dlgappcore


class DoJobAppDialog(dlgappcore.AppDialog):
    softspace = 1

    def __init__(self, appName=""):
        self.appName = appName
        dlgappcore.AppDialog.__init__(self, win32ui.IDD_GENERAL_STATUS)

    def PreDoModal(self):
        pass

    def ProcessArgs(self, args):
        pass

    def OnInitDialog(self):
        self.SetWindowText(self.appName)
        butCancel = self.GetDlgItem(win32con.IDCANCEL)
        butCancel.ShowWindow(win32con.SW_HIDE)
        p1 = self.GetDlgItem(win32ui.IDC_PROMPT1)
        p2 = self.GetDlgItem(win32ui.IDC_PROMPT2)

        # Do something here!

        p1.SetWindowText("Hello there")
        p2.SetWindowText("from the demo")

    def OnDestroy(self, msg):
        pass


# 	def OnOK(self):
# 		pass
# 	def OnCancel(self): default behaviour - cancel == close.
# 		return


class DoJobDialogApp(dlgappcore.DialogApp):
    def CreateDialog(self):
        return DoJobAppDialog("Do Something")


class CopyToDialogApp(DoJobDialogApp):
    def __init__(self):
        DoJobDialogApp.__init__(self)


app = DoJobDialogApp()


def t():
    t = DoJobAppDialog("Copy To")
    t.DoModal()
    return t


if __name__ == "__main__":
    import demoutils

    demoutils.NeedApp()

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\workspace\test_crm_app\app\main.py ===
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

# === NexusCore/workspace\test_crm_app\app\main.py ===
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

# === NexusCore/healing_sandbox\app\main.py ===
# my-crm-app/app/main.py
"""
Main application module for the CRM.

This module contains the core business logic.
"""

def hello_world(username: str) -> str:
    """
    Greets the user by their name.

    This function provides a personalized greeting message.

    Args:
        username (str): The name of the user to greet.

    Returns:
        str: The complete greeting message.
    """
    if not isinstance(username, str) or not username:
        return "Hello, anonymous!"
    return f"Hello, {username}!"

def simple_greeting() -> str:
    """
    Returns a simple greeting message.

    This function provides a basic greeting.

    Returns:
        str: A string in the format 'Hello!'.
    """
    return "Hello!"

def greet_user(username: str) -> str:
    """
    Returns a greeting message for the given username.

    This function provides a personalized greeting message.

    Args:
        username (str): The name of the user to greet.

    Returns:
        str: A greeting message in the format 'Hello, [username]!'
    """
    return f"Hello, {username}!"

def greet(username: str = None) -> str:
    """
    Greets the user with a personalized message or a default message if the username is empty or null.
    Handles special characters and long usernames gracefully.

    Args:
        username (str): The name of the user to greet. Can be empty, null, or contain special characters.

    Returns:
        str: A greeting string. 'Hello, [username]!' if the username is provided, 
             and a suitable default message if the username is empty or null.
    """
    if username is None or not username:
        return "Hello, stranger!"
    else:
        return f"Hello, {username}!"

# === NexusCore/my-crm-app\app\main.py ===
# my-crm-app/app/main.py
"""
Main application module for the CRM.

This module contains the core business logic.
"""

def hello_world(username: str) -> str:
    """
    Greets the user by their name.

    This function provides a personalized greeting message.

    Args:
        username (str): The name of the user to greet.

    Returns:
        str: The complete greeting message.
    """
    if not isinstance(username, str) or not username:
        return "Hello, anonymous!"
    return f"Hello, {username}!"

def simple_greeting() -> str:
    """
    Returns a simple greeting message.

    This function provides a basic greeting.

    Returns:
        str: A string in the format 'Hello!'.
    """
    return "Hello!"

def greet_user(username: str) -> str:
    """
    Returns a greeting message for the given username.

    This function provides a personalized greeting message.

    Args:
        username (str): The name of the user to greet.

    Returns:
        str: A greeting message in the format 'Hello, [username]!'
    """
    return f"Hello, {username}!"

def greet(username: str = None) -> str:
    """
    Greets the user with a personalized message or a default message if the username is empty or null.
    Handles special characters and long usernames gracefully.

    Args:
        username (str): The name of the user to greet. Can be empty, null, or contain special characters.

    Returns:
        str: A greeting string. 'Hello, [username]!' if the username is provided, 
             and a suitable default message if the username is empty or null.
    """
    if username is None or not username:
        return "Hello, there!"
    else:
        return f"Hello, {username}!"

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\healing_sandbox\app\main.py ===
# my-crm-app/app/main.py
"""
Main application module for the CRM.

This module contains the core business logic.
"""

def hello_world(username: str) -> str:
    """
    Greets the user by their name.

    This function provides a personalized greeting message.

    Args:
        username (str): The name of the user to greet.

    Returns:
        str: The complete greeting message.
    """
    if not isinstance(username, str) or not username:
        return "Hello, anonymous!"
    return f"Hello, {username}!"

def simple_greeting() -> str:
    """
    Returns a simple greeting message.

    This function provides a basic greeting.

    Returns:
        str: A string in the format 'Hello!'.
    """
    return "Hello!"

def greet_user(username: str) -> str:
    """
    Returns a greeting message for the given username.

    This function provides a personalized greeting message.

    Args:
        username (str): The name of the user to greet.

    Returns:
        str: A greeting message in the format 'Hello, [username]!'
    """
    return f"Hello, {username}!"

def greet(username: str = None) -> str:
    """
    Greets the user with a personalized message or a default message if the username is empty or null.
    Handles special characters and long usernames gracefully.

    Args:
        username (str): The name of the user to greet. Can be empty, null, or contain special characters.

    Returns:
        str: A greeting string. 'Hello, [username]!' if the username is provided, 
             and a suitable default message if the username is empty or null.
    """
    if username is None or not username:
        return "Hello, stranger!"
    else:
        return f"Hello, {username}!"

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\my-crm-app\app\main.py ===
# my-crm-app/app/main.py
"""
Main application module for the CRM.

This module contains the core business logic.
"""

def hello_world(username: str) -> str:
    """
    Greets the user by their name.

    This function provides a personalized greeting message.

    Args:
        username (str): The name of the user to greet.

    Returns:
        str: The complete greeting message.
    """
    if not isinstance(username, str) or not username:
        return "Hello, anonymous!"
    return f"Hello, {username}!"

def simple_greeting() -> str:
    """
    Returns a simple greeting message.

    This function provides a basic greeting.

    Returns:
        str: A string in the format 'Hello!'.
    """
    return "Hello!"

def greet_user(username: str) -> str:
    """
    Returns a greeting message for the given username.

    This function provides a personalized greeting message.

    Args:
        username (str): The name of the user to greet.

    Returns:
        str: A greeting message in the format 'Hello, [username]!'
    """
    return f"Hello, {username}!"

def greet(username: str = None) -> str:
    """
    Greets the user with a personalized message or a default message if the username is empty or null.
    Handles special characters and long usernames gracefully.

    Args:
        username (str): The name of the user to greet. Can be empty, null, or contain special characters.

    Returns:
        str: A greeting string. 'Hello, [username]!' if the username is provided, 
             and a suitable default message if the username is empty or null.
    """
    if username is None or not username:
        return "Hello, there!"
    else:
        return f"Hello, {username}!"

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\Demos\app\demoutils.py ===
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