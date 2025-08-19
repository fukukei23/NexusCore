
# === NexusCore/src\sandbox_logs\repair_20250713_114552_fixed.py ===
ここでのエラーはPythonのコード自体に問題があるわけではなく、テストモジュールのインポートに失敗していることが原因となっています。したがって、Pythonのコードを修正することで解決する問題ではありません。

エラーメッセージを見ると、'C:\\Users\\USER\\AppData\\Local\\Temp\\tmpjgrmw9nh\\test_main'というモジュールが見つからないという内容です。これは、テストを実行する際に必要なモジュールが適切な場所に存在しない、または適切な名前で存在しない可能性があります。

解決策としては、以下のことを確認してみてください。

1. テストモジュールが正しい場所に存在しているか確認する。
2. テストモジュールの名前が正しいか確認する。
3. Pythonのパス設定が正しいか確認する。

これらを確認・修正した上で再度テストを実行してみてください。

# === NexusCore/src\sandbox_logs\repair_20250713_124402_fixed.py ===
元のコードには二つの問題があります。一つは、関数`add`が実際には引数を減算していること、もう一つは、エラーメッセージから見て、Pythonのコードが日本語のコメントで始まっていることです。PythonはデフォルトでASCII文字しか受け付けないため、日本語のコメントが原因でエラーが発生しています。

以下に修正したコードを示します：

```python
# 以下は、指定されたPythonコードに対するpytest形式のユニットテストです。
def add(a, b):
    return a + b  # 修正：return a - bからreturn a + bへ
```

この修正により、関数`add`は引数を正しく加算し、日本語のコメントもASCII文字に変換されてエラーが解消されます。

# === NexusCore/src\sandbox_logs\repair_20250713_124414_original.py ===
元のコードには二つの問題があります。一つは、関数`add`が実際には引数を減算していること、もう一つは、エラーメッセージから見て、Pythonのコードが日本語のコメントで始まっていることです。PythonはデフォルトでASCII文字しか受け付けないため、日本語のコメントが原因でエラーが発生しています。

以下に修正したコードを示します：

```python
# 以下は、指定されたPythonコードに対するpytest形式のユニットテストです。
def add(a, b):
    return a + b  # 修正：return a - bからreturn a + bへ
```

この修正により、関数`add`は引数を正しく加算し、日本語のコメントもASCII文字に変換されてエラーが解消されます。

# === NexusCore/src\sandbox_logs\repair_20250713_213319_fixed.py ===
申し訳ありませんが、テスト対象のPythonコードが具体的に提供されていないため、具体的な修正コードを生成することができません。ただし、エラーメッセージから推測するに、テストコードの先頭に非ASCII文字（この場合は日本語）が含まれていることが問題のようです。

Pythonのソースコードに非ASCII文字を使用する場合、ファイルの先頭に文字エンコーディングを指定することが一般的です。以下のように、ファイルの先頭に文字エンコーディングを指定します：

```python
# -*- coding: utf-8 -*-
```

この行を追加すると、PythonはファイルがUTF-8でエンコードされていることを認識し、非ASCII文字を正しく処理できます。

ただし、この修正が問題を解決するかどうかは、テストコードの他の部分にどのような内容が含まれているかによります。

# === NexusCore/src\sandbox_logs\repair_20250713_213331_original.py ===
申し訳ありませんが、テスト対象のPythonコードが具体的に提供されていないため、具体的な修正コードを生成することができません。ただし、エラーメッセージから推測するに、テストコードの先頭に非ASCII文字（この場合は日本語）が含まれていることが問題のようです。

Pythonのソースコードに非ASCII文字を使用する場合、ファイルの先頭に文字エンコーディングを指定することが一般的です。以下のように、ファイルの先頭に文字エンコーディングを指定します：

```python
# -*- coding: utf-8 -*-
```

この行を追加すると、PythonはファイルがUTF-8でエンコードされていることを認識し、非ASCII文字を正しく処理できます。

ただし、この修正が問題を解決するかどうかは、テストコードの他の部分にどのような内容が含まれているかによります。

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_114552_fixed.py ===
ここでのエラーはPythonのコード自体に問題があるわけではなく、テストモジュールのインポートに失敗していることが原因となっています。したがって、Pythonのコードを修正することで解決する問題ではありません。

エラーメッセージを見ると、'C:\\Users\\USER\\AppData\\Local\\Temp\\tmpjgrmw9nh\\test_main'というモジュールが見つからないという内容です。これは、テストを実行する際に必要なモジュールが適切な場所に存在しない、または適切な名前で存在しない可能性があります。

解決策としては、以下のことを確認してみてください。

1. テストモジュールが正しい場所に存在しているか確認する。
2. テストモジュールの名前が正しいか確認する。
3. Pythonのパス設定が正しいか確認する。

これらを確認・修正した上で再度テストを実行してみてください。

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_124402_fixed.py ===
元のコードには二つの問題があります。一つは、関数`add`が実際には引数を減算していること、もう一つは、エラーメッセージから見て、Pythonのコードが日本語のコメントで始まっていることです。PythonはデフォルトでASCII文字しか受け付けないため、日本語のコメントが原因でエラーが発生しています。

以下に修正したコードを示します：

```python
# 以下は、指定されたPythonコードに対するpytest形式のユニットテストです。
def add(a, b):
    return a + b  # 修正：return a - bからreturn a + bへ
```

この修正により、関数`add`は引数を正しく加算し、日本語のコメントもASCII文字に変換されてエラーが解消されます。

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_124414_original.py ===
元のコードには二つの問題があります。一つは、関数`add`が実際には引数を減算していること、もう一つは、エラーメッセージから見て、Pythonのコードが日本語のコメントで始まっていることです。PythonはデフォルトでASCII文字しか受け付けないため、日本語のコメントが原因でエラーが発生しています。

以下に修正したコードを示します：

```python
# 以下は、指定されたPythonコードに対するpytest形式のユニットテストです。
def add(a, b):
    return a + b  # 修正：return a - bからreturn a + bへ
```

この修正により、関数`add`は引数を正しく加算し、日本語のコメントもASCII文字に変換されてエラーが解消されます。

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_213319_fixed.py ===
申し訳ありませんが、テスト対象のPythonコードが具体的に提供されていないため、具体的な修正コードを生成することができません。ただし、エラーメッセージから推測するに、テストコードの先頭に非ASCII文字（この場合は日本語）が含まれていることが問題のようです。

Pythonのソースコードに非ASCII文字を使用する場合、ファイルの先頭に文字エンコーディングを指定することが一般的です。以下のように、ファイルの先頭に文字エンコーディングを指定します：

```python
# -*- coding: utf-8 -*-
```

この行を追加すると、PythonはファイルがUTF-8でエンコードされていることを認識し、非ASCII文字を正しく処理できます。

ただし、この修正が問題を解決するかどうかは、テストコードの他の部分にどのような内容が含まれているかによります。

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_213331_original.py ===
申し訳ありませんが、テスト対象のPythonコードが具体的に提供されていないため、具体的な修正コードを生成することができません。ただし、エラーメッセージから推測するに、テストコードの先頭に非ASCII文字（この場合は日本語）が含まれていることが問題のようです。

Pythonのソースコードに非ASCII文字を使用する場合、ファイルの先頭に文字エンコーディングを指定することが一般的です。以下のように、ファイルの先頭に文字エンコーディングを指定します：

```python
# -*- coding: utf-8 -*-
```

この行を追加すると、PythonはファイルがUTF-8でエンコードされていることを認識し、非ASCII文字を正しく処理できます。

ただし、この修正が問題を解決するかどうかは、テストコードの他の部分にどのような内容が含まれているかによります。

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\sandbox_logs\repair_20250713_114552_fixed.py ===
ここでのエラーはPythonのコード自体に問題があるわけではなく、テストモジュールのインポートに失敗していることが原因となっています。したがって、Pythonのコードを修正することで解決する問題ではありません。

エラーメッセージを見ると、'C:\\Users\\USER\\AppData\\Local\\Temp\\tmpjgrmw9nh\\test_main'というモジュールが見つからないという内容です。これは、テストを実行する際に必要なモジュールが適切な場所に存在しない、または適切な名前で存在しない可能性があります。

解決策としては、以下のことを確認してみてください。

1. テストモジュールが正しい場所に存在しているか確認する。
2. テストモジュールの名前が正しいか確認する。
3. Pythonのパス設定が正しいか確認する。

これらを確認・修正した上で再度テストを実行してみてください。

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\sandbox_logs\repair_20250713_124402_fixed.py ===
元のコードには二つの問題があります。一つは、関数`add`が実際には引数を減算していること、もう一つは、エラーメッセージから見て、Pythonのコードが日本語のコメントで始まっていることです。PythonはデフォルトでASCII文字しか受け付けないため、日本語のコメントが原因でエラーが発生しています。

以下に修正したコードを示します：

```python
# 以下は、指定されたPythonコードに対するpytest形式のユニットテストです。
def add(a, b):
    return a + b  # 修正：return a - bからreturn a + bへ
```

この修正により、関数`add`は引数を正しく加算し、日本語のコメントもASCII文字に変換されてエラーが解消されます。

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\sandbox_logs\repair_20250713_124414_original.py ===
元のコードには二つの問題があります。一つは、関数`add`が実際には引数を減算していること、もう一つは、エラーメッセージから見て、Pythonのコードが日本語のコメントで始まっていることです。PythonはデフォルトでASCII文字しか受け付けないため、日本語のコメントが原因でエラーが発生しています。

以下に修正したコードを示します：

```python
# 以下は、指定されたPythonコードに対するpytest形式のユニットテストです。
def add(a, b):
    return a + b  # 修正：return a - bからreturn a + bへ
```

この修正により、関数`add`は引数を正しく加算し、日本語のコメントもASCII文字に変換されてエラーが解消されます。

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\sandbox_logs\repair_20250713_213319_fixed.py ===
申し訳ありませんが、テスト対象のPythonコードが具体的に提供されていないため、具体的な修正コードを生成することができません。ただし、エラーメッセージから推測するに、テストコードの先頭に非ASCII文字（この場合は日本語）が含まれていることが問題のようです。

Pythonのソースコードに非ASCII文字を使用する場合、ファイルの先頭に文字エンコーディングを指定することが一般的です。以下のように、ファイルの先頭に文字エンコーディングを指定します：

```python
# -*- coding: utf-8 -*-
```

この行を追加すると、PythonはファイルがUTF-8でエンコードされていることを認識し、非ASCII文字を正しく処理できます。

ただし、この修正が問題を解決するかどうかは、テストコードの他の部分にどのような内容が含まれているかによります。

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\sandbox_logs\repair_20250713_213331_original.py ===
申し訳ありませんが、テスト対象のPythonコードが具体的に提供されていないため、具体的な修正コードを生成することができません。ただし、エラーメッセージから推測するに、テストコードの先頭に非ASCII文字（この場合は日本語）が含まれていることが問題のようです。

Pythonのソースコードに非ASCII文字を使用する場合、ファイルの先頭に文字エンコーディングを指定することが一般的です。以下のように、ファイルの先頭に文字エンコーディングを指定します：

```python
# -*- coding: utf-8 -*-
```

この行を追加すると、PythonはファイルがUTF-8でエンコードされていることを認識し、非ASCII文字を正しく処理できます。

ただし、この修正が問題を解決するかどうかは、テストコードの他の部分にどのような内容が含まれているかによります。

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\combined_53.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\lib\tests\test__iotools.py ===
import time
from datetime import date

import numpy as np
from numpy.lib._iotools import (
    LineSplitter,
    NameValidator,
    StringConverter,
    easy_dtype,
    flatten_dtype,
    has_nested_fields,
)
from numpy.testing import (
    assert_,
    assert_allclose,
    assert_equal,
    assert_raises,
)


class TestLineSplitter:
    "Tests the LineSplitter class."

    def test_no_delimiter(self):
        "Test LineSplitter w/o delimiter"
        strg = " 1 2 3 4  5 # test"
        test = LineSplitter()(strg)
        assert_equal(test, ['1', '2', '3', '4', '5'])
        test = LineSplitter('')(strg)
        assert_equal(test, ['1', '2', '3', '4', '5'])

    def test_space_delimiter(self):
        "Test space delimiter"
        strg = " 1 2 3 4  5 # test"
        test = LineSplitter(' ')(strg)
        assert_equal(test, ['1', '2', '3', '4', '', '5'])
        test = LineSplitter('  ')(strg)
        assert_equal(test, ['1 2 3 4', '5'])

    def test_tab_delimiter(self):
        "Test tab delimiter"
        strg = " 1\t 2\t 3\t 4\t 5  6"
        test = LineSplitter('\t')(strg)
        assert_equal(test, ['1', '2', '3', '4', '5  6'])
        strg = " 1  2\t 3  4\t 5  6"
        test = LineSplitter('\t')(strg)
        assert_equal(test, ['1  2', '3  4', '5  6'])

    def test_other_delimiter(self):
        "Test LineSplitter on delimiter"
        strg = "1,2,3,4,,5"
        test = LineSplitter(',')(strg)
        assert_equal(test, ['1', '2', '3', '4', '', '5'])
        #
        strg = " 1,2,3,4,,5 # test"
        test = LineSplitter(',')(strg)
        assert_equal(test, ['1', '2', '3', '4', '', '5'])

        # gh-11028 bytes comment/delimiters should get encoded
        strg = b" 1,2,3,4,,5 % test"
        test = LineSplitter(delimiter=b',', comments=b'%')(strg)
        assert_equal(test, ['1', '2', '3', '4', '', '5'])

    def test_constant_fixed_width(self):
        "Test LineSplitter w/ fixed-width fields"
        strg = "  1  2  3  4     5   # test"
        test = LineSplitter(3)(strg)
        assert_equal(test, ['1', '2', '3', '4', '', '5', ''])
        #
        strg = "  1     3  4  5  6# test"
        test = LineSplitter(20)(strg)
        assert_equal(test, ['1     3  4  5  6'])
        #
        strg = "  1     3  4  5  6# test"
        test = LineSplitter(30)(strg)
        assert_equal(test, ['1     3  4  5  6'])

    def test_variable_fixed_width(self):
        strg = "  1     3  4  5  6# test"
        test = LineSplitter((3, 6, 6, 3))(strg)
        assert_equal(test, ['1', '3', '4  5', '6'])
        #
        strg = "  1     3  4  5  6# test"
        test = LineSplitter((6, 6, 9))(strg)
        assert_equal(test, ['1', '3  4', '5  6'])

# -----------------------------------------------------------------------------


class TestNameValidator:

    def test_case_sensitivity(self):
        "Test case sensitivity"
        names = ['A', 'a', 'b', 'c']
        test = NameValidator().validate(names)
        assert_equal(test, ['A', 'a', 'b', 'c'])
        test = NameValidator(case_sensitive=False).validate(names)
        assert_equal(test, ['A', 'A_1', 'B', 'C'])
        test = NameValidator(case_sensitive='upper').validate(names)
        assert_equal(test, ['A', 'A_1', 'B', 'C'])
        test = NameValidator(case_sensitive='lower').validate(names)
        assert_equal(test, ['a', 'a_1', 'b', 'c'])

        # check exceptions
        assert_raises(ValueError, NameValidator, case_sensitive='foobar')

    def test_excludelist(self):
        "Test excludelist"
        names = ['dates', 'data', 'Other Data', 'mask']
        validator = NameValidator(excludelist=['dates', 'data', 'mask'])
        test = validator.validate(names)
        assert_equal(test, ['dates_', 'data_', 'Other_Data', 'mask_'])

    def test_missing_names(self):
        "Test validate missing names"
        namelist = ('a', 'b', 'c')
        validator = NameValidator()
        assert_equal(validator(namelist), ['a', 'b', 'c'])
        namelist = ('', 'b', 'c')
        assert_equal(validator(namelist), ['f0', 'b', 'c'])
        namelist = ('a', 'b', '')
        assert_equal(validator(namelist), ['a', 'b', 'f0'])
        namelist = ('', 'f0', '')
        assert_equal(validator(namelist), ['f1', 'f0', 'f2'])

    def test_validate_nb_names(self):
        "Test validate nb names"
        namelist = ('a', 'b', 'c')
        validator = NameValidator()
        assert_equal(validator(namelist, nbfields=1), ('a',))
        assert_equal(validator(namelist, nbfields=5, defaultfmt="g%i"),
                     ['a', 'b', 'c', 'g0', 'g1'])

    def test_validate_wo_names(self):
        "Test validate no names"
        namelist = None
        validator = NameValidator()
        assert_(validator(namelist) is None)
        assert_equal(validator(namelist, nbfields=3), ['f0', 'f1', 'f2'])

# -----------------------------------------------------------------------------


def _bytes_to_date(s):
    return date(*time.strptime(s, "%Y-%m-%d")[:3])


class TestStringConverter:
    "Test StringConverter"

    def test_creation(self):
        "Test creation of a StringConverter"
        converter = StringConverter(int, -99999)
        assert_equal(converter._status, 1)
        assert_equal(converter.default, -99999)

    def test_upgrade(self):
        "Tests the upgrade method."

        converter = StringConverter()
        assert_equal(converter._status, 0)

        # test int
        assert_equal(converter.upgrade('0'), 0)
        assert_equal(converter._status, 1)

        # On systems where long defaults to 32-bit, the statuses will be
        # offset by one, so we check for this here.
        import numpy._core.numeric as nx
        status_offset = int(nx.dtype(nx.int_).itemsize < nx.dtype(nx.int64).itemsize)

        # test int > 2**32
        assert_equal(converter.upgrade('17179869184'), 17179869184)
        assert_equal(converter._status, 1 + status_offset)

        # test float
        assert_allclose(converter.upgrade('0.'), 0.0)
        assert_equal(converter._status, 2 + status_offset)

        # test complex
        assert_equal(converter.upgrade('0j'), complex('0j'))
        assert_equal(converter._status, 3 + status_offset)

        # test str
        # note that the longdouble type has been skipped, so the
        # _status increases by 2. Everything should succeed with
        # unicode conversion (8).
        for s in ['a', b'a']:
            res = converter.upgrade(s)
            assert_(type(res) is str)
            assert_equal(res, 'a')
            assert_equal(converter._status, 8 + status_offset)

    def test_missing(self):
        "Tests the use of missing values."
        converter = StringConverter(missing_values=('missing',
                                                    'missed'))
        converter.upgrade('0')
        assert_equal(converter('0'), 0)
        assert_equal(converter(''), converter.default)
        assert_equal(converter('missing'), converter.default)
        assert_equal(converter('missed'), converter.default)
        try:
            converter('miss')
        except ValueError:
            pass

    def test_upgrademapper(self):
        "Tests updatemapper"
        dateparser = _bytes_to_date
        _original_mapper = StringConverter._mapper[:]
        try:
            StringConverter.upgrade_mapper(dateparser, date(2000, 1, 1))
            convert = StringConverter(dateparser, date(2000, 1, 1))
            test = convert('2001-01-01')
            assert_equal(test, date(2001, 1, 1))
            test = convert('2009-01-01')
            assert_equal(test, date(2009, 1, 1))
            test = convert('')
            assert_equal(test, date(2000, 1, 1))
        finally:
            StringConverter._mapper = _original_mapper

    def test_string_to_object(self):
        "Make sure that string-to-object functions are properly recognized"
        old_mapper = StringConverter._mapper[:]  # copy of list
        conv = StringConverter(_bytes_to_date)
        assert_equal(conv._mapper, old_mapper)
        assert_(hasattr(conv, 'default'))

    def test_keep_default(self):
        "Make sure we don't lose an explicit default"
        converter = StringConverter(None, missing_values='',
                                    default=-999)
        converter.upgrade('3.14159265')
        assert_equal(converter.default, -999)
        assert_equal(converter.type, np.dtype(float))
        #
        converter = StringConverter(
            None, missing_values='', default=0)
        converter.upgrade('3.14159265')
        assert_equal(converter.default, 0)
        assert_equal(converter.type, np.dtype(float))

    def test_keep_default_zero(self):
        "Check that we don't lose a default of 0"
        converter = StringConverter(int, default=0,
                                    missing_values="N/A")
        assert_equal(converter.default, 0)

    def test_keep_missing_values(self):
        "Check that we're not losing missing values"
        converter = StringConverter(int, default=0,
                                    missing_values="N/A")
        assert_equal(
            converter.missing_values, {'', 'N/A'})

    def test_int64_dtype(self):
        "Check that int64 integer types can be specified"
        converter = StringConverter(np.int64, default=0)
        val = "-9223372036854775807"
        assert_(converter(val) == -9223372036854775807)
        val = "9223372036854775807"
        assert_(converter(val) == 9223372036854775807)

    def test_uint64_dtype(self):
        "Check that uint64 integer types can be specified"
        converter = StringConverter(np.uint64, default=0)
        val = "9223372043271415339"
        assert_(converter(val) == 9223372043271415339)


class TestMiscFunctions:

    def test_has_nested_dtype(self):
        "Test has_nested_dtype"
        ndtype = np.dtype(float)
        assert_equal(has_nested_fields(ndtype), False)
        ndtype = np.dtype([('A', '|S3'), ('B', float)])
        assert_equal(has_nested_fields(ndtype), False)
        ndtype = np.dtype([('A', int), ('B', [('BA', float), ('BB', '|S1')])])
        assert_equal(has_nested_fields(ndtype), True)

    def test_easy_dtype(self):
        "Test ndtype on dtypes"
        # Simple case
        ndtype = float
        assert_equal(easy_dtype(ndtype), np.dtype(float))
        # As string w/o names
        ndtype = "i4, f8"
        assert_equal(easy_dtype(ndtype),
                     np.dtype([('f0', "i4"), ('f1', "f8")]))
        # As string w/o names but different default format
        assert_equal(easy_dtype(ndtype, defaultfmt="field_%03i"),
                     np.dtype([('field_000', "i4"), ('field_001', "f8")]))
        # As string w/ names
        ndtype = "i4, f8"
        assert_equal(easy_dtype(ndtype, names="a, b"),
                     np.dtype([('a', "i4"), ('b', "f8")]))
        # As string w/ names (too many)
        ndtype = "i4, f8"
        assert_equal(easy_dtype(ndtype, names="a, b, c"),
                     np.dtype([('a', "i4"), ('b', "f8")]))
        # As string w/ names (not enough)
        ndtype = "i4, f8"
        assert_equal(easy_dtype(ndtype, names=", b"),
                     np.dtype([('f0', "i4"), ('b', "f8")]))
        # ... (with different default format)
        assert_equal(easy_dtype(ndtype, names="a", defaultfmt="f%02i"),
                     np.dtype([('a', "i4"), ('f00', "f8")]))
        # As list of tuples w/o names
        ndtype = [('A', int), ('B', float)]
        assert_equal(easy_dtype(ndtype), np.dtype([('A', int), ('B', float)]))
        # As list of tuples w/ names
        assert_equal(easy_dtype(ndtype, names="a,b"),
                     np.dtype([('a', int), ('b', float)]))
        # As list of tuples w/ not enough names
        assert_equal(easy_dtype(ndtype, names="a"),
                     np.dtype([('a', int), ('f0', float)]))
        # As list of tuples w/ too many names
        assert_equal(easy_dtype(ndtype, names="a,b,c"),
                     np.dtype([('a', int), ('b', float)]))
        # As list of types w/o names
        ndtype = (int, float, float)
        assert_equal(easy_dtype(ndtype),
                     np.dtype([('f0', int), ('f1', float), ('f2', float)]))
        # As list of types w names
        ndtype = (int, float, float)
        assert_equal(easy_dtype(ndtype, names="a, b, c"),
                     np.dtype([('a', int), ('b', float), ('c', float)]))
        # As simple dtype w/ names
        ndtype = np.dtype(float)
        assert_equal(easy_dtype(ndtype, names="a, b, c"),
                     np.dtype([(_, float) for _ in ('a', 'b', 'c')]))
        # As simple dtype w/o names (but multiple fields)
        ndtype = np.dtype(float)
        assert_equal(
            easy_dtype(ndtype, names=['', '', ''], defaultfmt="f%02i"),
            np.dtype([(_, float) for _ in ('f00', 'f01', 'f02')]))

    def test_flatten_dtype(self):
        "Testing flatten_dtype"
        # Standard dtype
        dt = np.dtype([("a", "f8"), ("b", "f8")])
        dt_flat = flatten_dtype(dt)
        assert_equal(dt_flat, [float, float])
        # Recursive dtype
        dt = np.dtype([("a", [("aa", '|S1'), ("ab", '|S2')]), ("b", int)])
        dt_flat = flatten_dtype(dt)
        assert_equal(dt_flat, [np.dtype('|S1'), np.dtype('|S2'), int])
        # dtype with shaped fields
        dt = np.dtype([("a", (float, 2)), ("b", (int, 3))])
        dt_flat = flatten_dtype(dt)
        assert_equal(dt_flat, [float, int])
        dt_flat = flatten_dtype(dt, True)
        assert_equal(dt_flat, [float] * 2 + [int] * 3)
        # dtype w/ titles
        dt = np.dtype([(("a", "A"), "f8"), (("b", "B"), "f8")])
        dt_flat = flatten_dtype(dt)
        assert_equal(dt_flat, [float, float])

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\tests\test__iotools.py ===
import time
from datetime import date

import numpy as np
from numpy.lib._iotools import (
    LineSplitter,
    NameValidator,
    StringConverter,
    easy_dtype,
    flatten_dtype,
    has_nested_fields,
)
from numpy.testing import (
    assert_,
    assert_allclose,
    assert_equal,
    assert_raises,
)


class TestLineSplitter:
    "Tests the LineSplitter class."

    def test_no_delimiter(self):
        "Test LineSplitter w/o delimiter"
        strg = " 1 2 3 4  5 # test"
        test = LineSplitter()(strg)
        assert_equal(test, ['1', '2', '3', '4', '5'])
        test = LineSplitter('')(strg)
        assert_equal(test, ['1', '2', '3', '4', '5'])

    def test_space_delimiter(self):
        "Test space delimiter"
        strg = " 1 2 3 4  5 # test"
        test = LineSplitter(' ')(strg)
        assert_equal(test, ['1', '2', '3', '4', '', '5'])
        test = LineSplitter('  ')(strg)
        assert_equal(test, ['1 2 3 4', '5'])

    def test_tab_delimiter(self):
        "Test tab delimiter"
        strg = " 1\t 2\t 3\t 4\t 5  6"
        test = LineSplitter('\t')(strg)
        assert_equal(test, ['1', '2', '3', '4', '5  6'])
        strg = " 1  2\t 3  4\t 5  6"
        test = LineSplitter('\t')(strg)
        assert_equal(test, ['1  2', '3  4', '5  6'])

    def test_other_delimiter(self):
        "Test LineSplitter on delimiter"
        strg = "1,2,3,4,,5"
        test = LineSplitter(',')(strg)
        assert_equal(test, ['1', '2', '3', '4', '', '5'])
        #
        strg = " 1,2,3,4,,5 # test"
        test = LineSplitter(',')(strg)
        assert_equal(test, ['1', '2', '3', '4', '', '5'])

        # gh-11028 bytes comment/delimiters should get encoded
        strg = b" 1,2,3,4,,5 % test"
        test = LineSplitter(delimiter=b',', comments=b'%')(strg)
        assert_equal(test, ['1', '2', '3', '4', '', '5'])

    def test_constant_fixed_width(self):
        "Test LineSplitter w/ fixed-width fields"
        strg = "  1  2  3  4     5   # test"
        test = LineSplitter(3)(strg)
        assert_equal(test, ['1', '2', '3', '4', '', '5', ''])
        #
        strg = "  1     3  4  5  6# test"
        test = LineSplitter(20)(strg)
        assert_equal(test, ['1     3  4  5  6'])
        #
        strg = "  1     3  4  5  6# test"
        test = LineSplitter(30)(strg)
        assert_equal(test, ['1     3  4  5  6'])

    def test_variable_fixed_width(self):
        strg = "  1     3  4  5  6# test"
        test = LineSplitter((3, 6, 6, 3))(strg)
        assert_equal(test, ['1', '3', '4  5', '6'])
        #
        strg = "  1     3  4  5  6# test"
        test = LineSplitter((6, 6, 9))(strg)
        assert_equal(test, ['1', '3  4', '5  6'])

# -----------------------------------------------------------------------------


class TestNameValidator:

    def test_case_sensitivity(self):
        "Test case sensitivity"
        names = ['A', 'a', 'b', 'c']
        test = NameValidator().validate(names)
        assert_equal(test, ['A', 'a', 'b', 'c'])
        test = NameValidator(case_sensitive=False).validate(names)
        assert_equal(test, ['A', 'A_1', 'B', 'C'])
        test = NameValidator(case_sensitive='upper').validate(names)
        assert_equal(test, ['A', 'A_1', 'B', 'C'])
        test = NameValidator(case_sensitive='lower').validate(names)
        assert_equal(test, ['a', 'a_1', 'b', 'c'])

        # check exceptions
        assert_raises(ValueError, NameValidator, case_sensitive='foobar')

    def test_excludelist(self):
        "Test excludelist"
        names = ['dates', 'data', 'Other Data', 'mask']
        validator = NameValidator(excludelist=['dates', 'data', 'mask'])
        test = validator.validate(names)
        assert_equal(test, ['dates_', 'data_', 'Other_Data', 'mask_'])

    def test_missing_names(self):
        "Test validate missing names"
        namelist = ('a', 'b', 'c')
        validator = NameValidator()
        assert_equal(validator(namelist), ['a', 'b', 'c'])
        namelist = ('', 'b', 'c')
        assert_equal(validator(namelist), ['f0', 'b', 'c'])
        namelist = ('a', 'b', '')
        assert_equal(validator(namelist), ['a', 'b', 'f0'])
        namelist = ('', 'f0', '')
        assert_equal(validator(namelist), ['f1', 'f0', 'f2'])

    def test_validate_nb_names(self):
        "Test validate nb names"
        namelist = ('a', 'b', 'c')
        validator = NameValidator()
        assert_equal(validator(namelist, nbfields=1), ('a',))
        assert_equal(validator(namelist, nbfields=5, defaultfmt="g%i"),
                     ['a', 'b', 'c', 'g0', 'g1'])

    def test_validate_wo_names(self):
        "Test validate no names"
        namelist = None
        validator = NameValidator()
        assert_(validator(namelist) is None)
        assert_equal(validator(namelist, nbfields=3), ['f0', 'f1', 'f2'])

# -----------------------------------------------------------------------------


def _bytes_to_date(s):
    return date(*time.strptime(s, "%Y-%m-%d")[:3])


class TestStringConverter:
    "Test StringConverter"

    def test_creation(self):
        "Test creation of a StringConverter"
        converter = StringConverter(int, -99999)
        assert_equal(converter._status, 1)
        assert_equal(converter.default, -99999)

    def test_upgrade(self):
        "Tests the upgrade method."

        converter = StringConverter()
        assert_equal(converter._status, 0)

        # test int
        assert_equal(converter.upgrade('0'), 0)
        assert_equal(converter._status, 1)

        # On systems where long defaults to 32-bit, the statuses will be
        # offset by one, so we check for this here.
        import numpy._core.numeric as nx
        status_offset = int(nx.dtype(nx.int_).itemsize < nx.dtype(nx.int64).itemsize)

        # test int > 2**32
        assert_equal(converter.upgrade('17179869184'), 17179869184)
        assert_equal(converter._status, 1 + status_offset)

        # test float
        assert_allclose(converter.upgrade('0.'), 0.0)
        assert_equal(converter._status, 2 + status_offset)

        # test complex
        assert_equal(converter.upgrade('0j'), complex('0j'))
        assert_equal(converter._status, 3 + status_offset)

        # test str
        # note that the longdouble type has been skipped, so the
        # _status increases by 2. Everything should succeed with
        # unicode conversion (8).
        for s in ['a', b'a']:
            res = converter.upgrade(s)
            assert_(type(res) is str)
            assert_equal(res, 'a')
            assert_equal(converter._status, 8 + status_offset)

    def test_missing(self):
        "Tests the use of missing values."
        converter = StringConverter(missing_values=('missing',
                                                    'missed'))
        converter.upgrade('0')
        assert_equal(converter('0'), 0)
        assert_equal(converter(''), converter.default)
        assert_equal(converter('missing'), converter.default)
        assert_equal(converter('missed'), converter.default)
        try:
            converter('miss')
        except ValueError:
            pass

    def test_upgrademapper(self):
        "Tests updatemapper"
        dateparser = _bytes_to_date
        _original_mapper = StringConverter._mapper[:]
        try:
            StringConverter.upgrade_mapper(dateparser, date(2000, 1, 1))
            convert = StringConverter(dateparser, date(2000, 1, 1))
            test = convert('2001-01-01')
            assert_equal(test, date(2001, 1, 1))
            test = convert('2009-01-01')
            assert_equal(test, date(2009, 1, 1))
            test = convert('')
            assert_equal(test, date(2000, 1, 1))
        finally:
            StringConverter._mapper = _original_mapper

    def test_string_to_object(self):
        "Make sure that string-to-object functions are properly recognized"
        old_mapper = StringConverter._mapper[:]  # copy of list
        conv = StringConverter(_bytes_to_date)
        assert_equal(conv._mapper, old_mapper)
        assert_(hasattr(conv, 'default'))

    def test_keep_default(self):
        "Make sure we don't lose an explicit default"
        converter = StringConverter(None, missing_values='',
                                    default=-999)
        converter.upgrade('3.14159265')
        assert_equal(converter.default, -999)
        assert_equal(converter.type, np.dtype(float))
        #
        converter = StringConverter(
            None, missing_values='', default=0)
        converter.upgrade('3.14159265')
        assert_equal(converter.default, 0)
        assert_equal(converter.type, np.dtype(float))

    def test_keep_default_zero(self):
        "Check that we don't lose a default of 0"
        converter = StringConverter(int, default=0,
                                    missing_values="N/A")
        assert_equal(converter.default, 0)

    def test_keep_missing_values(self):
        "Check that we're not losing missing values"
        converter = StringConverter(int, default=0,
                                    missing_values="N/A")
        assert_equal(
            converter.missing_values, {'', 'N/A'})

    def test_int64_dtype(self):
        "Check that int64 integer types can be specified"
        converter = StringConverter(np.int64, default=0)
        val = "-9223372036854775807"
        assert_(converter(val) == -9223372036854775807)
        val = "9223372036854775807"
        assert_(converter(val) == 9223372036854775807)

    def test_uint64_dtype(self):
        "Check that uint64 integer types can be specified"
        converter = StringConverter(np.uint64, default=0)
        val = "9223372043271415339"
        assert_(converter(val) == 9223372043271415339)


class TestMiscFunctions:

    def test_has_nested_dtype(self):
        "Test has_nested_dtype"
        ndtype = np.dtype(float)
        assert_equal(has_nested_fields(ndtype), False)
        ndtype = np.dtype([('A', '|S3'), ('B', float)])
        assert_equal(has_nested_fields(ndtype), False)
        ndtype = np.dtype([('A', int), ('B', [('BA', float), ('BB', '|S1')])])
        assert_equal(has_nested_fields(ndtype), True)

    def test_easy_dtype(self):
        "Test ndtype on dtypes"
        # Simple case
        ndtype = float
        assert_equal(easy_dtype(ndtype), np.dtype(float))
        # As string w/o names
        ndtype = "i4, f8"
        assert_equal(easy_dtype(ndtype),
                     np.dtype([('f0', "i4"), ('f1', "f8")]))
        # As string w/o names but different default format
        assert_equal(easy_dtype(ndtype, defaultfmt="field_%03i"),
                     np.dtype([('field_000', "i4"), ('field_001', "f8")]))
        # As string w/ names
        ndtype = "i4, f8"
        assert_equal(easy_dtype(ndtype, names="a, b"),
                     np.dtype([('a', "i4"), ('b', "f8")]))
        # As string w/ names (too many)
        ndtype = "i4, f8"
        assert_equal(easy_dtype(ndtype, names="a, b, c"),
                     np.dtype([('a', "i4"), ('b', "f8")]))
        # As string w/ names (not enough)
        ndtype = "i4, f8"
        assert_equal(easy_dtype(ndtype, names=", b"),
                     np.dtype([('f0', "i4"), ('b', "f8")]))
        # ... (with different default format)
        assert_equal(easy_dtype(ndtype, names="a", defaultfmt="f%02i"),
                     np.dtype([('a', "i4"), ('f00', "f8")]))
        # As list of tuples w/o names
        ndtype = [('A', int), ('B', float)]
        assert_equal(easy_dtype(ndtype), np.dtype([('A', int), ('B', float)]))
        # As list of tuples w/ names
        assert_equal(easy_dtype(ndtype, names="a,b"),
                     np.dtype([('a', int), ('b', float)]))
        # As list of tuples w/ not enough names
        assert_equal(easy_dtype(ndtype, names="a"),
                     np.dtype([('a', int), ('f0', float)]))
        # As list of tuples w/ too many names
        assert_equal(easy_dtype(ndtype, names="a,b,c"),
                     np.dtype([('a', int), ('b', float)]))
        # As list of types w/o names
        ndtype = (int, float, float)
        assert_equal(easy_dtype(ndtype),
                     np.dtype([('f0', int), ('f1', float), ('f2', float)]))
        # As list of types w names
        ndtype = (int, float, float)
        assert_equal(easy_dtype(ndtype, names="a, b, c"),
                     np.dtype([('a', int), ('b', float), ('c', float)]))
        # As simple dtype w/ names
        ndtype = np.dtype(float)
        assert_equal(easy_dtype(ndtype, names="a, b, c"),
                     np.dtype([(_, float) for _ in ('a', 'b', 'c')]))
        # As simple dtype w/o names (but multiple fields)
        ndtype = np.dtype(float)
        assert_equal(
            easy_dtype(ndtype, names=['', '', ''], defaultfmt="f%02i"),
            np.dtype([(_, float) for _ in ('f00', 'f01', 'f02')]))

    def test_flatten_dtype(self):
        "Testing flatten_dtype"
        # Standard dtype
        dt = np.dtype([("a", "f8"), ("b", "f8")])
        dt_flat = flatten_dtype(dt)
        assert_equal(dt_flat, [float, float])
        # Recursive dtype
        dt = np.dtype([("a", [("aa", '|S1'), ("ab", '|S2')]), ("b", int)])
        dt_flat = flatten_dtype(dt)
        assert_equal(dt_flat, [np.dtype('|S1'), np.dtype('|S2'), int])
        # dtype with shaped fields
        dt = np.dtype([("a", (float, 2)), ("b", (int, 3))])
        dt_flat = flatten_dtype(dt)
        assert_equal(dt_flat, [float, int])
        dt_flat = flatten_dtype(dt, True)
        assert_equal(dt_flat, [float] * 2 + [int] * 3)
        # dtype w/ titles
        dt = np.dtype([(("a", "A"), "f8"), (("b", "B"), "f8")])
        dt_flat = flatten_dtype(dt)
        assert_equal(dt_flat, [float, float])

# === NexusCore/tools\exports\export_20250803_114325\combined_58.py ===

# === NexusCore/openenv\Lib\site-packages\anthropic\lib\bedrock\_auth.py ===
from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from ..._utils import lru_cache

if TYPE_CHECKING:
    import boto3


@lru_cache(maxsize=512)
def _get_session(
    *,
    aws_access_key: str | None,
    aws_secret_key: str | None,
    aws_session_token: str | None,
    region: str | None,
    profile: str | None,
) -> boto3.Session:
    import boto3

    return boto3.Session(
        profile_name=profile,
        region_name=region,
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        aws_session_token=aws_session_token,
    )


def get_auth_headers(
    *,
    method: str,
    url: str,
    headers: httpx.Headers,
    aws_access_key: str | None,
    aws_secret_key: str | None,
    aws_session_token: str | None,
    region: str | None,
    profile: str | None,
    data: str | None,
) -> dict[str, str]:
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest

    session = _get_session(
        profile=profile,
        region=region,
        aws_access_key=aws_access_key,
        aws_secret_key=aws_secret_key,
        aws_session_token=aws_session_token,
    )

    # The connection header may be stripped by a proxy somewhere, so the receiver
    # of this message may not see this header, so we remove it from the set of headers
    # that are signed.
    headers = headers.copy()
    del headers["connection"]

    request = AWSRequest(method=method.upper(), url=url, headers=headers, data=data)
    credentials = session.get_credentials()

    signer = SigV4Auth(credentials, "bedrock", session.region_name)
    signer.add_auth(request)

    prepped = request.prepare()

    return {key: value for key, value in dict(prepped.headers).items() if value is not None}

# === NexusCore/openenv\Lib\site-packages\fsspec\spec.py ===
from __future__ import annotations

import io
import json
import logging
import os
import threading
import warnings
import weakref
from errno import ESPIPE
from glob import has_magic
from hashlib import sha256
from typing import Any, ClassVar

from .callbacks import DEFAULT_CALLBACK
from .config import apply_config, conf
from .dircache import DirCache
from .transaction import Transaction
from .utils import (
    _unstrip_protocol,
    glob_translate,
    isfilelike,
    other_paths,
    read_block,
    stringify_path,
    tokenize,
)

logger = logging.getLogger("fsspec")


def make_instance(cls, args, kwargs):
    return cls(*args, **kwargs)


class _Cached(type):
    """
    Metaclass for caching file system instances.

    Notes
    -----
    Instances are cached according to

    * The values of the class attributes listed in `_extra_tokenize_attributes`
    * The arguments passed to ``__init__``.

    This creates an additional reference to the filesystem, which prevents the
    filesystem from being garbage collected when all *user* references go away.
    A call to the :meth:`AbstractFileSystem.clear_instance_cache` must *also*
    be made for a filesystem instance to be garbage collected.
    """

    def __init__(cls, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Note: we intentionally create a reference here, to avoid garbage
        # collecting instances when all other references are gone. To really
        # delete a FileSystem, the cache must be cleared.
        if conf.get("weakref_instance_cache"):  # pragma: no cover
            # debug option for analysing fork/spawn conditions
            cls._cache = weakref.WeakValueDictionary()
        else:
            cls._cache = {}
        cls._pid = os.getpid()

    def __call__(cls, *args, **kwargs):
        kwargs = apply_config(cls, kwargs)
        extra_tokens = tuple(
            getattr(cls, attr, None) for attr in cls._extra_tokenize_attributes
        )
        token = tokenize(
            cls, cls._pid, threading.get_ident(), *args, *extra_tokens, **kwargs
        )
        skip = kwargs.pop("skip_instance_cache", False)
        if os.getpid() != cls._pid:
            cls._cache.clear()
            cls._pid = os.getpid()
        if not skip and cls.cachable and token in cls._cache:
            cls._latest = token
            return cls._cache[token]
        else:
            obj = super().__call__(*args, **kwargs)
            # Setting _fs_token here causes some static linters to complain.
            obj._fs_token_ = token
            obj.storage_args = args
            obj.storage_options = kwargs
            if obj.async_impl and obj.mirror_sync_methods:
                from .asyn import mirror_sync_methods

                mirror_sync_methods(obj)

            if cls.cachable and not skip:
                cls._latest = token
                cls._cache[token] = obj
            return obj


class AbstractFileSystem(metaclass=_Cached):
    """
    An abstract super-class for pythonic file-systems

    Implementations are expected to be compatible with or, better, subclass
    from here.
    """

    cachable = True  # this class can be cached, instances reused
    _cached = False
    blocksize = 2**22
    sep = "/"
    protocol: ClassVar[str | tuple[str, ...]] = "abstract"
    _latest = None
    async_impl = False
    mirror_sync_methods = False
    root_marker = ""  # For some FSs, may require leading '/' or other character
    transaction_type = Transaction

    #: Extra *class attributes* that should be considered when hashing.
    _extra_tokenize_attributes = ()

    # Set by _Cached metaclass
    storage_args: tuple[Any, ...]
    storage_options: dict[str, Any]

    def __init__(self, *args, **storage_options):
        """Create and configure file-system instance

        Instances may be cachable, so if similar enough arguments are seen
        a new instance is not required. The token attribute exists to allow
        implementations to cache instances if they wish.

        A reasonable default should be provided if there are no arguments.

        Subclasses should call this method.

        Parameters
        ----------
        use_listings_cache, listings_expiry_time, max_paths:
            passed to ``DirCache``, if the implementation supports
            directory listing caching. Pass use_listings_cache=False
            to disable such caching.
        skip_instance_cache: bool
            If this is a cachable implementation, pass True here to force
            creating a new instance even if a matching instance exists, and prevent
            storing this instance.
        asynchronous: bool
        loop: asyncio-compatible IOLoop or None
        """
        if self._cached:
            # reusing instance, don't change
            return
        self._cached = True
        self._intrans = False
        self._transaction = None
        self._invalidated_caches_in_transaction = []
        self.dircache = DirCache(**storage_options)

        if storage_options.pop("add_docs", None):
            warnings.warn("add_docs is no longer supported.", FutureWarning)

        if storage_options.pop("add_aliases", None):
            warnings.warn("add_aliases has been removed.", FutureWarning)
        # This is set in _Cached
        self._fs_token_ = None

    @property
    def fsid(self):
        """Persistent filesystem id that can be used to compare filesystems
        across sessions.
        """
        raise NotImplementedError

    @property
    def _fs_token(self):
        return self._fs_token_

    def __dask_tokenize__(self):
        return self._fs_token

    def __hash__(self):
        return int(self._fs_token, 16)

    def __eq__(self, other):
        return isinstance(other, type(self)) and self._fs_token == other._fs_token

    def __reduce__(self):
        return make_instance, (type(self), self.storage_args, self.storage_options)

    @classmethod
    def _strip_protocol(cls, path):
        """Turn path from fully-qualified to file-system-specific

        May require FS-specific handling, e.g., for relative paths or links.
        """
        if isinstance(path, list):
            return [cls._strip_protocol(p) for p in path]
        path = stringify_path(path)
        protos = (cls.protocol,) if isinstance(cls.protocol, str) else cls.protocol
        for protocol in protos:
            if path.startswith(protocol + "://"):
                path = path[len(protocol) + 3 :]
            elif path.startswith(protocol + "::"):
                path = path[len(protocol) + 2 :]
        path = path.rstrip("/")
        # use of root_marker to make minimum required path, e.g., "/"
        return path or cls.root_marker

    def unstrip_protocol(self, name: str) -> str:
        """Format FS-specific path to generic, including protocol"""
        protos = (self.protocol,) if isinstance(self.protocol, str) else self.protocol
        for protocol in protos:
            if name.startswith(f"{protocol}://"):
                return name
        return f"{protos[0]}://{name}"

    @staticmethod
    def _get_kwargs_from_urls(path):
        """If kwargs can be encoded in the paths, extract them here

        This should happen before instantiation of the class; incoming paths
        then should be amended to strip the options in methods.

        Examples may look like an sftp path "sftp://user@host:/my/path", where
        the user and host should become kwargs and later get stripped.
        """
        # by default, nothing happens
        return {}

    @classmethod
    def current(cls):
        """Return the most recently instantiated FileSystem

        If no instance has been created, then create one with defaults
        """
        if cls._latest in cls._cache:
            return cls._cache[cls._latest]
        return cls()

    @property
    def transaction(self):
        """A context within which files are committed together upon exit

        Requires the file class to implement `.commit()` and `.discard()`
        for the normal and exception cases.
        """
        if self._transaction is None:
            self._transaction = self.transaction_type(self)
        return self._transaction

    def start_transaction(self):
        """Begin write transaction for deferring files, non-context version"""
        self._intrans = True
        self._transaction = self.transaction_type(self)
        return self.transaction

    def end_transaction(self):
        """Finish write transaction, non-context version"""
        self.transaction.complete()
        self._transaction = None
        # The invalid cache must be cleared after the transaction is completed.
        for path in self._invalidated_caches_in_transaction:
            self.invalidate_cache(path)
        self._invalidated_caches_in_transaction.clear()

    def invalidate_cache(self, path=None):
        """
        Discard any cached directory information

        Parameters
        ----------
        path: string or None
            If None, clear all listings cached else listings at or under given
            path.
        """
        # Not necessary to implement invalidation mechanism, may have no cache.
        # But if have, you should call this method of parent class from your
        # subclass to ensure expiring caches after transacations correctly.
        # See the implementation of FTPFileSystem in ftp.py
        if self._intrans:
            self._invalidated_caches_in_transaction.append(path)

    def mkdir(self, path, create_parents=True, **kwargs):
        """
        Create directory entry at path

        For systems that don't have true directories, may create an for
        this instance only and not touch the real filesystem

        Parameters
        ----------
        path: str
            location
        create_parents: bool
            if True, this is equivalent to ``makedirs``
        kwargs:
            may be permissions, etc.
        """
        pass  # not necessary to implement, may not have directories

    def makedirs(self, path, exist_ok=False):
        """Recursively make directories

        Creates directory at path and any intervening required directories.
        Raises exception if, for instance, the path already exists but is a
        file.

        Parameters
        ----------
        path: str
            leaf directory name
        exist_ok: bool (False)
            If False, will error if the target already exists
        """
        pass  # not necessary to implement, may not have directories

    def rmdir(self, path):
        """Remove a directory, if empty"""
        pass  # not necessary to implement, may not have directories

    def ls(self, path, detail=True, **kwargs):
        """List objects at path.

        This should include subdirectories and files at that location. The
        difference between a file and a directory must be clear when details
        are requested.

        The specific keys, or perhaps a FileInfo class, or similar, is TBD,
        but must be consistent across implementations.
        Must include:

        - full path to the entry (without protocol)
        - size of the entry, in bytes. If the value cannot be determined, will
          be ``None``.
        - type of entry, "file", "directory" or other

        Additional information
        may be present, appropriate to the file-system, e.g., generation,
        checksum, etc.

        May use refresh=True|False to allow use of self._ls_from_cache to
        check for a saved listing and avoid calling the backend. This would be
        common where listing may be expensive.

        Parameters
        ----------
        path: str
        detail: bool
            if True, gives a list of dictionaries, where each is the same as
            the result of ``info(path)``. If False, gives a list of paths
            (str).
        kwargs: may have additional backend-specific options, such as version
            information

        Returns
        -------
        List of strings if detail is False, or list of directory information
        dicts if detail is True.
        """
        raise NotImplementedError

    def _ls_from_cache(self, path):
        """Check cache for listing

        Returns listing, if found (may be empty list for a directly that exists
        but contains nothing), None if not in cache.
        """
        parent = self._parent(path)
        try:
            return self.dircache[path.rstrip("/")]
        except KeyError:
            pass
        try:
            files = [
                f
                for f in self.dircache[parent]
                if f["name"] == path
                or (f["name"] == path.rstrip("/") and f["type"] == "directory")
            ]
            if len(files) == 0:
                # parent dir was listed but did not contain this file
                raise FileNotFoundError(path)
            return files
        except KeyError:
            pass

    def walk(self, path, maxdepth=None, topdown=True, on_error="omit", **kwargs):
        """Return all files under the given path.

        List all files, recursing into subdirectories; output is iterator-style,
        like ``os.walk()``. For a simple list of files, ``find()`` is available.

        When topdown is True, the caller can modify the dirnames list in-place (perhaps
        using del or slice assignment), and walk() will
        only recurse into the subdirectories whose names remain in dirnames;
        this can be used to prune the search, impose a specific order of visiting,
        or even to inform walk() about directories the caller creates or renames before
        it resumes walk() again.
        Modifying dirnames when topdown is False has no effect. (see os.walk)

        Note that the "files" outputted will include anything that is not
        a directory, such as links.

        Parameters
        ----------
        path: str
            Root to recurse into
        maxdepth: int
            Maximum recursion depth. None means limitless, but not recommended
            on link-based file-systems.
        topdown: bool (True)
            Whether to walk the directory tree from the top downwards or from
            the bottom upwards.
        on_error: "omit", "raise", a callable
            if omit (default), path with exception will simply be empty;
            If raise, an underlying exception will be raised;
            if callable, it will be called with a single OSError instance as argument
        kwargs: passed to ``ls``
        """
        if maxdepth is not None and maxdepth < 1:
            raise ValueError("maxdepth must be at least 1")

        path = self._strip_protocol(path)
        full_dirs = {}
        dirs = {}
        files = {}

        detail = kwargs.pop("detail", False)
        try:
            listing = self.ls(path, detail=True, **kwargs)
        except (FileNotFoundError, OSError) as e:
            if on_error == "raise":
                raise
            if callable(on_error):
                on_error(e)
            return

        for info in listing:
            # each info name must be at least [path]/part , but here
            # we check also for names like [path]/part/
            pathname = info["name"].rstrip("/")
            name = pathname.rsplit("/", 1)[-1]
            if info["type"] == "directory" and pathname != path:
                # do not include "self" path
                full_dirs[name] = pathname
                dirs[name] = info
            elif pathname == path:
                # file-like with same name as give path
                files[""] = info
            else:
                files[name] = info

        if not detail:
            dirs = list(dirs)
            files = list(files)

        if topdown:
            # Yield before recursion if walking top down
            yield path, dirs, files

        if maxdepth is not None:
            maxdepth -= 1
            if maxdepth < 1:
                if not topdown:
                    yield path, dirs, files
                return

        for d in dirs:
            yield from self.walk(
                full_dirs[d],
                maxdepth=maxdepth,
                detail=detail,
                topdown=topdown,
                **kwargs,
            )

        if not topdown:
            # Yield after recursion if walking bottom up
            yield path, dirs, files

    def find(self, path, maxdepth=None, withdirs=False, detail=False, **kwargs):
        """List all files below path.

        Like posix ``find`` command without conditions

        Parameters
        ----------
        path : str
        maxdepth: int or None
            If not None, the maximum number of levels to descend
        withdirs: bool
            Whether to include directory paths in the output. This is True
            when used by glob, but users usually only want files.
        kwargs are passed to ``ls``.
        """
        # TODO: allow equivalent of -name parameter
        path = self._strip_protocol(path)
        out = {}

        # Add the root directory if withdirs is requested
        # This is needed for posix glob compliance
        if withdirs and path != "" and self.isdir(path):
            out[path] = self.info(path)

        for _, dirs, files in self.walk(path, maxdepth, detail=True, **kwargs):
            if withdirs:
                files.update(dirs)
            out.update({info["name"]: info for name, info in files.items()})
        if not out and self.isfile(path):
            # walk works on directories, but find should also return [path]
            # when path happens to be a file
            out[path] = {}
        names = sorted(out)
        if not detail:
            return names
        else:
            return {name: out[name] for name in names}

    def du(self, path, total=True, maxdepth=None, withdirs=False, **kwargs):
        """Space used by files and optionally directories within a path

        Directory size does not include the size of its contents.

        Parameters
        ----------
        path: str
        total: bool
            Whether to sum all the file sizes
        maxdepth: int or None
            Maximum number of directory levels to descend, None for unlimited.
        withdirs: bool
            Whether to include directory paths in the output.
        kwargs: passed to ``find``

        Returns
        -------
        Dict of {path: size} if total=False, or int otherwise, where numbers
        refer to bytes used.
        """
        sizes = {}
        if withdirs and self.isdir(path):
            # Include top-level directory in output
            info = self.info(path)
            sizes[info["name"]] = info["size"]
        for f in self.find(path, maxdepth=maxdepth, withdirs=withdirs, **kwargs):
            info = self.info(f)
            sizes[info["name"]] = info["size"]
        if total:
            return sum(sizes.values())
        else:
            return sizes

    def glob(self, path, maxdepth=None, **kwargs):
        """Find files by glob-matching.

        Pattern matching capabilities for finding files that match the given pattern.

        Parameters
        ----------
        path: str
            The glob pattern to match against
        maxdepth: int or None
            Maximum depth for ``'**'`` patterns. Applied on the first ``'**'`` found.
            Must be at least 1 if provided.
        kwargs:
            Additional arguments passed to ``find`` (e.g., detail=True)

        Returns
        -------
        List of matched paths, or dict of paths and their info if detail=True

        Notes
        -----
        Supported patterns:
        - '*': Matches any sequence of characters within a single directory level
        - ``'**'``: Matches any number of directory levels (must be an entire path component)
        - '?': Matches exactly one character
        - '[abc]': Matches any character in the set
        - '[a-z]': Matches any character in the range
        - '[!abc]': Matches any character NOT in the set

        Special behaviors:
        - If the path ends with '/', only folders are returned
        - Consecutive '*' characters are compressed into a single '*'
        - Empty brackets '[]' never match anything
        - Negated empty brackets '[!]' match any single character
        - Special characters in character classes are escaped properly

        Limitations:
        - ``'**'`` must be a complete path component (e.g., ``'a/**/b'``, not ``'a**b'``)
        - No brace expansion ('{a,b}.txt')
        - No extended glob patterns ('+(pattern)', '!(pattern)')
        """
        if maxdepth is not None and maxdepth < 1:
            raise ValueError("maxdepth must be at least 1")

        import re

        seps = (os.path.sep, os.path.altsep) if os.path.altsep else (os.path.sep,)
        ends_with_sep = path.endswith(seps)  # _strip_protocol strips trailing slash
        path = self._strip_protocol(path)
        append_slash_to_dirname = ends_with_sep or path.endswith(
            tuple(sep + "**" for sep in seps)
        )
        idx_star = path.find("*") if path.find("*") >= 0 else len(path)
        idx_qmark = path.find("?") if path.find("?") >= 0 else len(path)
        idx_brace = path.find("[") if path.find("[") >= 0 else len(path)

        min_idx = min(idx_star, idx_qmark, idx_brace)

        detail = kwargs.pop("detail", False)

        if not has_magic(path):
            if self.exists(path, **kwargs):
                if not detail:
                    return [path]
                else:
                    return {path: self.info(path, **kwargs)}
            else:
                if not detail:
                    return []  # glob of non-existent returns empty
                else:
                    return {}
        elif "/" in path[:min_idx]:
            min_idx = path[:min_idx].rindex("/")
            root = path[: min_idx + 1]
            depth = path[min_idx + 1 :].count("/") + 1
        else:
            root = ""
            depth = path[min_idx + 1 :].count("/") + 1

        if "**" in path:
            if maxdepth is not None:
                idx_double_stars = path.find("**")
                depth_double_stars = path[idx_double_stars:].count("/") + 1
                depth = depth - depth_double_stars + maxdepth
            else:
                depth = None

        allpaths = self.find(root, maxdepth=depth, withdirs=True, detail=True, **kwargs)

        pattern = glob_translate(path + ("/" if ends_with_sep else ""))
        pattern = re.compile(pattern)

        out = {
            p: info
            for p, info in sorted(allpaths.items())
            if pattern.match(
                p + "/"
                if append_slash_to_dirname and info["type"] == "directory"
                else p
            )
        }

        if detail:
            return out
        else:
            return list(out)

    def exists(self, path, **kwargs):
        """Is there a file at the given path"""
        try:
            self.info(path, **kwargs)
            return True
        except:  # noqa: E722
            # any exception allowed bar FileNotFoundError?
            return False

    def lexists(self, path, **kwargs):
        """If there is a file at the given path (including
        broken links)"""
        return self.exists(path)

    def info(self, path, **kwargs):
        """Give details of entry at path

        Returns a single dictionary, with exactly the same information as ``ls``
        would with ``detail=True``.

        The default implementation calls ls and could be overridden by a
        shortcut. kwargs are passed on to ```ls()``.

        Some file systems might not be able to measure the file's size, in
        which case, the returned dict will include ``'size': None``.

        Returns
        -------
        dict with keys: name (full path in the FS), size (in bytes), type (file,
        directory, or something else) and other FS-specific keys.
        """
        path = self._strip_protocol(path)
        out = self.ls(self._parent(path), detail=True, **kwargs)
        out = [o for o in out if o["name"].rstrip("/") == path]
        if out:
            return out[0]
        out = self.ls(path, detail=True, **kwargs)
        path = path.rstrip("/")
        out1 = [o for o in out if o["name"].rstrip("/") == path]
        if len(out1) == 1:
            if "size" not in out1[0]:
                out1[0]["size"] = None
            return out1[0]
        elif len(out1) > 1 or out:
            return {"name": path, "size": 0, "type": "directory"}
        else:
            raise FileNotFoundError(path)

    def checksum(self, path):
        """Unique value for current version of file

        If the checksum is the same from one moment to another, the contents
        are guaranteed to be the same. If the checksum changes, the contents
        *might* have changed.

        This should normally be overridden; default will probably capture
        creation/modification timestamp (which would be good) or maybe
        access timestamp (which would be bad)
        """
        return int(tokenize(self.info(path)), 16)

    def size(self, path):
        """Size in bytes of file"""
        return self.info(path).get("size", None)

    def sizes(self, paths):
        """Size in bytes of each file in a list of paths"""
        return [self.size(p) for p in paths]

    def isdir(self, path):
        """Is this entry directory-like?"""
        try:
            return self.info(path)["type"] == "directory"
        except OSError:
            return False

    def isfile(self, path):
        """Is this entry file-like?"""
        try:
            return self.info(path)["type"] == "file"
        except:  # noqa: E722
            return False

    def read_text(self, path, encoding=None, errors=None, newline=None, **kwargs):
        """Get the contents of the file as a string.

        Parameters
        ----------
        path: str
            URL of file on this filesystems
        encoding, errors, newline: same as `open`.
        """
        with self.open(
            path,
            mode="r",
            encoding=encoding,
            errors=errors,
            newline=newline,
            **kwargs,
        ) as f:
            return f.read()

    def write_text(
        self, path, value, encoding=None, errors=None, newline=None, **kwargs
    ):
        """Write the text to the given file.

        An existing file will be overwritten.

        Parameters
        ----------
        path: str
            URL of file on this filesystems
        value: str
            Text to write.
        encoding, errors, newline: same as `open`.
        """
        with self.open(
            path,
            mode="w",
            encoding=encoding,
            errors=errors,
            newline=newline,
            **kwargs,
        ) as f:
            return f.write(value)

    def cat_file(self, path, start=None, end=None, **kwargs):
        """Get the content of a file

        Parameters
        ----------
        path: URL of file on this filesystems
        start, end: int
            Bytes limits of the read. If negative, backwards from end,
            like usual python slices. Either can be None for start or
            end of file, respectively
        kwargs: passed to ``open()``.
        """
        # explicitly set buffering off?
        with self.open(path, "rb", **kwargs) as f:
            if start is not None:
                if start >= 0:
                    f.seek(start)
                else:
                    f.seek(max(0, f.size + start))
            if end is not None:
                if end < 0:
                    end = f.size + end
                return f.read(end - f.tell())
            return f.read()

    def pipe_file(self, path, value, mode="overwrite", **kwargs):
        """Set the bytes of given file"""
        if mode == "create" and self.exists(path):
            # non-atomic but simple way; or could use "xb" in open(), which is likely
            # not as well supported
            raise FileExistsError
        with self.open(path, "wb", **kwargs) as f:
            f.write(value)

    def pipe(self, path, value=None, **kwargs):
        """Put value into path

        (counterpart to ``cat``)

        Parameters
        ----------
        path: string or dict(str, bytes)
            If a string, a single remote location to put ``value`` bytes; if a dict,
            a mapping of {path: bytesvalue}.
        value: bytes, optional
            If using a single path, these are the bytes to put there. Ignored if
            ``path`` is a dict
        """
        if isinstance(path, str):
            self.pipe_file(self._strip_protocol(path), value, **kwargs)
        elif isinstance(path, dict):
            for k, v in path.items():
                self.pipe_file(self._strip_protocol(k), v, **kwargs)
        else:
            raise ValueError("path must be str or dict")

    def cat_ranges(
        self, paths, starts, ends, max_gap=None, on_error="return", **kwargs
    ):
        """Get the contents of byte ranges from one or more files

        Parameters
        ----------
        paths: list
            A list of of filepaths on this filesystems
        starts, ends: int or list
            Bytes limits of the read. If using a single int, the same value will be
            used to read all the specified files.
        """
        if max_gap is not None:
            raise NotImplementedError
        if not isinstance(paths, list):
            raise TypeError
        if not isinstance(starts, list):
            starts = [starts] * len(paths)
        if not isinstance(ends, list):
            ends = [ends] * len(paths)
        if len(starts) != len(paths) or len(ends) != len(paths):
            raise ValueError
        out = []
        for p, s, e in zip(paths, starts, ends):
            try:
                out.append(self.cat_file(p, s, e))
            except Exception as e:
                if on_error == "return":
                    out.append(e)
                else:
                    raise
        return out

    def cat(self, path, recursive=False, on_error="raise", **kwargs):
        """Fetch (potentially multiple) paths' contents

        Parameters
        ----------
        recursive: bool
            If True, assume the path(s) are directories, and get all the
            contained files
        on_error : "raise", "omit", "return"
            If raise, an underlying exception will be raised (converted to KeyError
            if the type is in self.missing_exceptions); if omit, keys with exception
            will simply not be included in the output; if "return", all keys are
            included in the output, but the value will be bytes or an exception
            instance.
        kwargs: passed to cat_file

        Returns
        -------
        dict of {path: contents} if there are multiple paths
        or the path has been otherwise expanded
        """
        paths = self.expand_path(path, recursive=recursive)
        if (
            len(paths) > 1
            or isinstance(path, list)
            or paths[0] != self._strip_protocol(path)
        ):
            out = {}
            for path in paths:
                try:
                    out[path] = self.cat_file(path, **kwargs)
                except Exception as e:
                    if on_error == "raise":
                        raise
                    if on_error == "return":
                        out[path] = e
            return out
        else:
            return self.cat_file(paths[0], **kwargs)

    def get_file(self, rpath, lpath, callback=DEFAULT_CALLBACK, outfile=None, **kwargs):
        """Copy single remote file to local"""
        from .implementations.local import LocalFileSystem

        if isfilelike(lpath):
            outfile = lpath
        elif self.isdir(rpath):
            os.makedirs(lpath, exist_ok=True)
            return None

        fs = LocalFileSystem(auto_mkdir=True)
        fs.makedirs(fs._parent(lpath), exist_ok=True)

        with self.open(rpath, "rb", **kwargs) as f1:
            if outfile is None:
                outfile = open(lpath, "wb")

            try:
                callback.set_size(getattr(f1, "size", None))
                data = True
                while data:
                    data = f1.read(self.blocksize)
                    segment_len = outfile.write(data)
                    if segment_len is None:
                        segment_len = len(data)
                    callback.relative_update(segment_len)
            finally:
                if not isfilelike(lpath):
                    outfile.close()

    def get(
        self,
        rpath,
        lpath,
        recursive=False,
        callback=DEFAULT_CALLBACK,
        maxdepth=None,
        **kwargs,
    ):
        """Copy file(s) to local.

        Copies a specific file or tree of files (if recursive=True). If lpath
        ends with a "/", it will be assumed to be a directory, and target files
        will go within. Can submit a list of paths, which may be glob-patterns
        and will be expanded.

        Calls get_file for each source.
        """
        if isinstance(lpath, list) and isinstance(rpath, list):
            # No need to expand paths when both source and destination
            # are provided as lists
            rpaths = rpath
            lpaths = lpath
        else:
            from .implementations.local import (
                LocalFileSystem,
                make_path_posix,
                trailing_sep,
            )

            source_is_str = isinstance(rpath, str)
            rpaths = self.expand_path(rpath, recursive=recursive, maxdepth=maxdepth)
            if source_is_str and (not recursive or maxdepth is not None):
                # Non-recursive glob does not copy directories
                rpaths = [p for p in rpaths if not (trailing_sep(p) or self.isdir(p))]
                if not rpaths:
                    return

            if isinstance(lpath, str):
                lpath = make_path_posix(lpath)

            source_is_file = len(rpaths) == 1
            dest_is_dir = isinstance(lpath, str) and (
                trailing_sep(lpath) or LocalFileSystem().isdir(lpath)
            )

            exists = source_is_str and (
                (has_magic(rpath) and source_is_file)
                or (not has_magic(rpath) and dest_is_dir and not trailing_sep(rpath))
            )
            lpaths = other_paths(
                rpaths,
                lpath,
                exists=exists,
                flatten=not source_is_str,
            )

        callback.set_size(len(lpaths))
        for lpath, rpath in callback.wrap(zip(lpaths, rpaths)):
            with callback.branched(rpath, lpath) as child:
                self.get_file(rpath, lpath, callback=child, **kwargs)

    def put_file(
        self, lpath, rpath, callback=DEFAULT_CALLBACK, mode="overwrite", **kwargs
    ):
        """Copy single file to remote"""
        if mode == "create" and self.exists(rpath):
            raise FileExistsError
        if os.path.isdir(lpath):
            self.makedirs(rpath, exist_ok=True)
            return None

        with open(lpath, "rb") as f1:
            size = f1.seek(0, 2)
            callback.set_size(size)
            f1.seek(0)

            self.mkdirs(self._parent(os.fspath(rpath)), exist_ok=True)
            with self.open(rpath, "wb", **kwargs) as f2:
                while f1.tell() < size:
                    data = f1.read(self.blocksize)
                    segment_len = f2.write(data)
                    if segment_len is None:
                        segment_len = len(data)
                    callback.relative_update(segment_len)

    def put(
        self,
        lpath,
        rpath,
        recursive=False,
        callback=DEFAULT_CALLBACK,
        maxdepth=None,
        **kwargs,
    ):
        """Copy file(s) from local.

        Copies a specific file or tree of files (if recursive=True). If rpath
        ends with a "/", it will be assumed to be a directory, and target files
        will go within.

        Calls put_file for each source.
        """
        if isinstance(lpath, list) and isinstance(rpath, list):
            # No need to expand paths when both source and destination
            # are provided as lists
            rpaths = rpath
            lpaths = lpath
        else:
            from .implementations.local import (
                LocalFileSystem,
                make_path_posix,
                trailing_sep,
            )

            source_is_str = isinstance(lpath, str)
            if source_is_str:
                lpath = make_path_posix(lpath)
            fs = LocalFileSystem()
            lpaths = fs.expand_path(lpath, recursive=recursive, maxdepth=maxdepth)
            if source_is_str and (not recursive or maxdepth is not None):
                # Non-recursive glob does not copy directories
                lpaths = [p for p in lpaths if not (trailing_sep(p) or fs.isdir(p))]
                if not lpaths:
                    return

            source_is_file = len(lpaths) == 1
            dest_is_dir = isinstance(rpath, str) and (
                trailing_sep(rpath) or self.isdir(rpath)
            )

            rpath = (
                self._strip_protocol(rpath)
                if isinstance(rpath, str)
                else [self._strip_protocol(p) for p in rpath]
            )
            exists = source_is_str and (
                (has_magic(lpath) and source_is_file)
                or (not has_magic(lpath) and dest_is_dir and not trailing_sep(lpath))
            )
            rpaths = other_paths(
                lpaths,
                rpath,
                exists=exists,
                flatten=not source_is_str,
            )

        callback.set_size(len(rpaths))
        for lpath, rpath in callback.wrap(zip(lpaths, rpaths)):
            with callback.branched(lpath, rpath) as child:
                self.put_file(lpath, rpath, callback=child, **kwargs)

    def head(self, path, size=1024):
        """Get the first ``size`` bytes from file"""
        with self.open(path, "rb") as f:
            return f.read(size)

    def tail(self, path, size=1024):
        """Get the last ``size`` bytes from file"""
        with self.open(path, "rb") as f:
            f.seek(max(-size, -f.size), 2)
            return f.read()

    def cp_file(self, path1, path2, **kwargs):
        raise NotImplementedError

    def copy(
        self, path1, path2, recursive=False, maxdepth=None, on_error=None, **kwargs
    ):
        """Copy within two locations in the filesystem

        on_error : "raise", "ignore"
            If raise, any not-found exceptions will be raised; if ignore any
            not-found exceptions will cause the path to be skipped; defaults to
            raise unless recursive is true, where the default is ignore
        """
        if on_error is None and recursive:
            on_error = "ignore"
        elif on_error is None:
            on_error = "raise"

        if isinstance(path1, list) and isinstance(path2, list):
            # No need to expand paths when both source and destination
            # are provided as lists
            paths1 = path1
            paths2 = path2
        else:
            from .implementations.local import trailing_sep

            source_is_str = isinstance(path1, str)
            paths1 = self.expand_path(path1, recursive=recursive, maxdepth=maxdepth)
            if source_is_str and (not recursive or maxdepth is not None):
                # Non-recursive glob does not copy directories
                paths1 = [p for p in paths1 if not (trailing_sep(p) or self.isdir(p))]
                if not paths1:
                    return

            source_is_file = len(paths1) == 1
            dest_is_dir = isinstance(path2, str) and (
                trailing_sep(path2) or self.isdir(path2)
            )

            exists = source_is_str and (
                (has_magic(path1) and source_is_file)
                or (not has_magic(path1) and dest_is_dir and not trailing_sep(path1))
            )
            paths2 = other_paths(
                paths1,
                path2,
                exists=exists,
                flatten=not source_is_str,
            )

        for p1, p2 in zip(paths1, paths2):
            try:
                self.cp_file(p1, p2, **kwargs)
            except FileNotFoundError:
                if on_error == "raise":
                    raise

    def expand_path(self, path, recursive=False, maxdepth=None, **kwargs):
        """Turn one or more globs or directories into a list of all matching paths
        to files or directories.

        kwargs are passed to ``glob`` or ``find``, which may in turn call ``ls``
        """

        if maxdepth is not None and maxdepth < 1:
            raise ValueError("maxdepth must be at least 1")

        if isinstance(path, (str, os.PathLike)):
            out = self.expand_path([path], recursive, maxdepth)
        else:
            out = set()
            path = [self._strip_protocol(p) for p in path]
            for p in path:
                if has_magic(p):
                    bit = set(self.glob(p, maxdepth=maxdepth, **kwargs))
                    out |= bit
                    if recursive:
                        # glob call above expanded one depth so if maxdepth is defined
                        # then decrement it in expand_path call below. If it is zero
                        # after decrementing then avoid expand_path call.
                        if maxdepth is not None and maxdepth <= 1:
                            continue
                        out |= set(
                            self.expand_path(
                                list(bit),
                                recursive=recursive,
                                maxdepth=maxdepth - 1 if maxdepth is not None else None,
                                **kwargs,
                            )
                        )
                    continue
                elif recursive:
                    rec = set(
                        self.find(
                            p, maxdepth=maxdepth, withdirs=True, detail=False, **kwargs
                        )
                    )
                    out |= rec
                if p not in out and (recursive is False or self.exists(p)):
                    # should only check once, for the root
                    out.add(p)
        if not out:
            raise FileNotFoundError(path)
        return sorted(out)

    def mv(self, path1, path2, recursive=False, maxdepth=None, **kwargs):
        """Move file(s) from one location to another"""
        if path1 == path2:
            logger.debug("%s mv: The paths are the same, so no files were moved.", self)
        else:
            # explicitly raise exception to prevent data corruption
            self.copy(
                path1, path2, recursive=recursive, maxdepth=maxdepth, onerror="raise"
            )
            self.rm(path1, recursive=recursive)

    def rm_file(self, path):
        """Delete a file"""
        self._rm(path)

    def _rm(self, path):
        """Delete one file"""
        # this is the old name for the method, prefer rm_file
        raise NotImplementedError

    def rm(self, path, recursive=False, maxdepth=None):
        """Delete files.

        Parameters
        ----------
        path: str or list of str
            File(s) to delete.
        recursive: bool
            If file(s) are directories, recursively delete contents and then
            also remove the directory
        maxdepth: int or None
            Depth to pass to walk for finding files to delete, if recursive.
            If None, there will be no limit and infinite recursion may be
            possible.
        """
        path = self.expand_path(path, recursive=recursive, maxdepth=maxdepth)
        for p in reversed(path):
            self.rm_file(p)

    @classmethod
    def _parent(cls, path):
        path = cls._strip_protocol(path)
        if "/" in path:
            parent = path.rsplit("/", 1)[0].lstrip(cls.root_marker)
            return cls.root_marker + parent
        else:
            return cls.root_marker

    def _open(
        self,
        path,
        mode="rb",
        block_size=None,
        autocommit=True,
        cache_options=None,
        **kwargs,
    ):
        """Return raw bytes-mode file-like from the file-system"""
        return AbstractBufferedFile(
            self,
            path,
            mode,
            block_size,
            autocommit,
            cache_options=cache_options,
            **kwargs,
        )

    def open(
        self,
        path,
        mode="rb",
        block_size=None,
        cache_options=None,
        compression=None,
        **kwargs,
    ):
        """
        Return a file-like object from the filesystem

        The resultant instance must function correctly in a context ``with``
        block.

        Parameters
        ----------
        path: str
            Target file
        mode: str like 'rb', 'w'
            See builtin ``open()``
            Mode "x" (exclusive write) may be implemented by the backend. Even if
            it is, whether  it is checked up front or on commit, and whether it is
            atomic is implementation-dependent.
        block_size: int
            Some indication of buffering - this is a value in bytes
        cache_options : dict, optional
            Extra arguments to pass through to the cache.
        compression: string or None
            If given, open file using compression codec. Can either be a compression
            name (a key in ``fsspec.compression.compr``) or "infer" to guess the
            compression from the filename suffix.
        encoding, errors, newline: passed on to TextIOWrapper for text mode
        """
        import io

        path = self._strip_protocol(path)
        if "b" not in mode:
            mode = mode.replace("t", "") + "b"

            text_kwargs = {
                k: kwargs.pop(k)
                for k in ["encoding", "errors", "newline"]
                if k in kwargs
            }
            return io.TextIOWrapper(
                self.open(
                    path,
                    mode,
                    block_size=block_size,
                    cache_options=cache_options,
                    compression=compression,
                    **kwargs,
                ),
                **text_kwargs,
            )
        else:
            ac = kwargs.pop("autocommit", not self._intrans)
            f = self._open(
                path,
                mode=mode,
                block_size=block_size,
                autocommit=ac,
                cache_options=cache_options,
                **kwargs,
            )
            if compression is not None:
                from fsspec.compression import compr
                from fsspec.core import get_compression

                compression = get_compression(path, compression)
                compress = compr[compression]
                f = compress(f, mode=mode[0])

            if not ac and "r" not in mode:
                self.transaction.files.append(f)
            return f

    def touch(self, path, truncate=True, **kwargs):
        """Create empty file, or update timestamp

        Parameters
        ----------
        path: str
            file location
        truncate: bool
            If True, always set file size to 0; if False, update timestamp and
            leave file unchanged, if backend allows this
        """
        if truncate or not self.exists(path):
            with self.open(path, "wb", **kwargs):
                pass
        else:
            raise NotImplementedError  # update timestamp, if possible

    def ukey(self, path):
        """Hash of file properties, to tell if it has changed"""
        return sha256(str(self.info(path)).encode()).hexdigest()

    def read_block(self, fn, offset, length, delimiter=None):
        """Read a block of bytes from

        Starting at ``offset`` of the file, read ``length`` bytes.  If
        ``delimiter`` is set then we ensure that the read starts and stops at
        delimiter boundaries that follow the locations ``offset`` and ``offset
        + length``.  If ``offset`` is zero then we start at zero.  The
        bytestring returned WILL include the end delimiter string.

        If offset+length is beyond the eof, reads to eof.

        Parameters
        ----------
        fn: string
            Path to filename
        offset: int
            Byte offset to start read
        length: int
            Number of bytes to read. If None, read to end.
        delimiter: bytes (optional)
            Ensure reading starts and stops at delimiter bytestring

        Examples
        --------
        >>> fs.read_block('data/file.csv', 0, 13)  # doctest: +SKIP
        b'Alice, 100\\nBo'
        >>> fs.read_block('data/file.csv', 0, 13, delimiter=b'\\n')  # doctest: +SKIP
        b'Alice, 100\\nBob, 200\\n'

        Use ``length=None`` to read to the end of the file.
        >>> fs.read_block('data/file.csv', 0, None, delimiter=b'\\n')  # doctest: +SKIP
        b'Alice, 100\\nBob, 200\\nCharlie, 300'

        See Also
        --------
        :func:`fsspec.utils.read_block`
        """
        with self.open(fn, "rb") as f:
            size = f.size
            if length is None:
                length = size
            if size is not None and offset + length > size:
                length = size - offset
            return read_block(f, offset, length, delimiter)

    def to_json(self, *, include_password: bool = True) -> str:
        """
        JSON representation of this filesystem instance.

        Parameters
        ----------
        include_password: bool, default True
            Whether to include the password (if any) in the output.

        Returns
        -------
        JSON string with keys ``cls`` (the python location of this class),
        protocol (text name of this class's protocol, first one in case of
        multiple), ``args`` (positional args, usually empty), and all other
        keyword arguments as their own keys.

        Warnings
        --------
        Serialized filesystems may contain sensitive information which have been
        passed to the constructor, such as passwords and tokens. Make sure you
        store and send them in a secure environment!
        """
        from .json import FilesystemJSONEncoder

        return json.dumps(
            self,
            cls=type(
                "_FilesystemJSONEncoder",
                (FilesystemJSONEncoder,),
                {"include_password": include_password},
            ),
        )

    @staticmethod
    def from_json(blob: str) -> AbstractFileSystem:
        """
        Recreate a filesystem instance from JSON representation.

        See ``.to_json()`` for the expected structure of the input.

        Parameters
        ----------
        blob: str

        Returns
        -------
        file system instance, not necessarily of this particular class.

        Warnings
        --------
        This can import arbitrary modules (as determined by the ``cls`` key).
        Make sure you haven't installed any modules that may execute malicious code
        at import time.
        """
        from .json import FilesystemJSONDecoder

        return json.loads(blob, cls=FilesystemJSONDecoder)

    def to_dict(self, *, include_password: bool = True) -> dict[str, Any]:
        """
        JSON-serializable dictionary representation of this filesystem instance.

        Parameters
        ----------
        include_password: bool, default True
            Whether to include the password (if any) in the output.

        Returns
        -------
        Dictionary with keys ``cls`` (the python location of this class),
        protocol (text name of this class's protocol, first one in case of
        multiple), ``args`` (positional args, usually empty), and all other
        keyword arguments as their own keys.

        Warnings
        --------
        Serialized filesystems may contain sensitive information which have been
        passed to the constructor, such as passwords and tokens. Make sure you
        store and send them in a secure environment!
        """
        from .json import FilesystemJSONEncoder

        json_encoder = FilesystemJSONEncoder()

        cls = type(self)
        proto = self.protocol

        storage_options = dict(self.storage_options)
        if not include_password:
            storage_options.pop("password", None)

        return dict(
            cls=f"{cls.__module__}:{cls.__name__}",
            protocol=proto[0] if isinstance(proto, (tuple, list)) else proto,
            args=json_encoder.make_serializable(self.storage_args),
            **json_encoder.make_serializable(storage_options),
        )

    @staticmethod
    def from_dict(dct: dict[str, Any]) -> AbstractFileSystem:
        """
        Recreate a filesystem instance from dictionary representation.

        See ``.to_dict()`` for the expected structure of the input.

        Parameters
        ----------
        dct: Dict[str, Any]

        Returns
        -------
        file system instance, not necessarily of this particular class.

        Warnings
        --------
        This can import arbitrary modules (as determined by the ``cls`` key).
        Make sure you haven't installed any modules that may execute malicious code
        at import time.
        """
        from .json import FilesystemJSONDecoder

        json_decoder = FilesystemJSONDecoder()

        dct = dict(dct)  # Defensive copy

        cls = FilesystemJSONDecoder.try_resolve_fs_cls(dct)
        if cls is None:
            raise ValueError("Not a serialized AbstractFileSystem")

        dct.pop("cls", None)
        dct.pop("protocol", None)

        return cls(
            *json_decoder.unmake_serializable(dct.pop("args", ())),
            **json_decoder.unmake_serializable(dct),
        )

    def _get_pyarrow_filesystem(self):
        """
        Make a version of the FS instance which will be acceptable to pyarrow
        """
        # all instances already also derive from pyarrow
        return self

    def get_mapper(self, root="", check=False, create=False, missing_exceptions=None):
        """Create key/value store based on this file-system

        Makes a MutableMapping interface to the FS at the given root path.
        See ``fsspec.mapping.FSMap`` for further details.
        """
        from .mapping import FSMap

        return FSMap(
            root,
            self,
            check=check,
            create=create,
            missing_exceptions=missing_exceptions,
        )

    @classmethod
    def clear_instance_cache(cls):
        """
        Clear the cache of filesystem instances.

        Notes
        -----
        Unless overridden by setting the ``cachable`` class attribute to False,
        the filesystem class stores a reference to newly created instances. This
        prevents Python's normal rules around garbage collection from working,
        since the instances refcount will not drop to zero until
        ``clear_instance_cache`` is called.
        """
        cls._cache.clear()

    def created(self, path):
        """Return the created timestamp of a file as a datetime.datetime"""
        raise NotImplementedError

    def modified(self, path):
        """Return the modified timestamp of a file as a datetime.datetime"""
        raise NotImplementedError

    def tree(
        self,
        path: str = "/",
        recursion_limit: int = 2,
        max_display: int = 25,
        display_size: bool = False,
        prefix: str = "",
        is_last: bool = True,
        first: bool = True,
        indent_size: int = 4,
    ) -> str:
        """
        Return a tree-like structure of the filesystem starting from the given path as a string.

        Parameters
        ----------
            path: Root path to start traversal from
            recursion_limit: Maximum depth of directory traversal
            max_display: Maximum number of items to display per directory
            display_size: Whether to display file sizes
            prefix: Current line prefix for visual tree structure
            is_last: Whether current item is last in its level
            first: Whether this is the first call (displays root path)
            indent_size: Number of spaces by indent

        Returns
        -------
            str: A string representing the tree structure.

        Example
        -------
            >>> from fsspec import filesystem

            >>> fs = filesystem('ftp', host='test.rebex.net', user='demo', password='password')
            >>> tree = fs.tree(display_size=True, recursion_limit=3, indent_size=8, max_display=10)
            >>> print(tree)
        """

        def format_bytes(n: int) -> str:
            """Format bytes as text."""
            for prefix, k in (
                ("P", 2**50),
                ("T", 2**40),
                ("G", 2**30),
                ("M", 2**20),
                ("k", 2**10),
            ):
                if n >= 0.9 * k:
                    return f"{n / k:.2f} {prefix}b"
            return f"{n}B"

        result = []

        if first:
            result.append(path)

        if recursion_limit:
            indent = " " * indent_size
            contents = self.ls(path, detail=True)
            contents.sort(
                key=lambda x: (x.get("type") != "directory", x.get("name", ""))
            )

            if max_display is not None and len(contents) > max_display:
                displayed_contents = contents[:max_display]
                remaining_count = len(contents) - max_display
            else:
                displayed_contents = contents
                remaining_count = 0

            for i, item in enumerate(displayed_contents):
                is_last_item = (i == len(displayed_contents) - 1) and (
                    remaining_count == 0
                )

                branch = (
                    "└" + ("─" * (indent_size - 2))
                    if is_last_item
                    else "├" + ("─" * (indent_size - 2))
                )
                branch += " "
                new_prefix = prefix + (
                    indent if is_last_item else "│" + " " * (indent_size - 1)
                )

                name = os.path.basename(item.get("name", ""))

                if display_size and item.get("type") == "directory":
                    sub_contents = self.ls(item.get("name", ""), detail=True)
                    num_files = sum(
                        1 for sub_item in sub_contents if sub_item.get("type") == "file"
                    )
                    num_folders = sum(
                        1
                        for sub_item in sub_contents
                        if sub_item.get("type") == "directory"
                    )

                    if num_files == 0 and num_folders == 0:
                        size = " (empty folder)"
                    elif num_files == 0:
                        size = f" ({num_folders} subfolder{'s' if num_folders > 1 else ''})"
                    elif num_folders == 0:
                        size = f" ({num_files} file{'s' if num_files > 1 else ''})"
                    else:
                        size = f" ({num_files} file{'s' if num_files > 1 else ''}, {num_folders} subfolder{'s' if num_folders > 1 else ''})"
                elif display_size and item.get("type") == "file":
                    size = f" ({format_bytes(item.get('size', 0))})"
                else:
                    size = ""

                result.append(f"{prefix}{branch}{name}{size}")

                if item.get("type") == "directory" and recursion_limit > 0:
                    result.append(
                        self.tree(
                            path=item.get("name", ""),
                            recursion_limit=recursion_limit - 1,
                            max_display=max_display,
                            display_size=display_size,
                            prefix=new_prefix,
                            is_last=is_last_item,
                            first=False,
                            indent_size=indent_size,
                        )
                    )

            if remaining_count > 0:
                more_message = f"{remaining_count} more item(s) not displayed."
                result.append(
                    f"{prefix}{'└' + ('─' * (indent_size - 2))} {more_message}"
                )

        return "\n".join(_ for _ in result if _)

    # ------------------------------------------------------------------------
    # Aliases

    def read_bytes(self, path, start=None, end=None, **kwargs):
        """Alias of `AbstractFileSystem.cat_file`."""
        return self.cat_file(path, start=start, end=end, **kwargs)

    def write_bytes(self, path, value, **kwargs):
        """Alias of `AbstractFileSystem.pipe_file`."""
        self.pipe_file(path, value, **kwargs)

    def makedir(self, path, create_parents=True, **kwargs):
        """Alias of `AbstractFileSystem.mkdir`."""
        return self.mkdir(path, create_parents=create_parents, **kwargs)

    def mkdirs(self, path, exist_ok=False):
        """Alias of `AbstractFileSystem.makedirs`."""
        return self.makedirs(path, exist_ok=exist_ok)

    def listdir(self, path, detail=True, **kwargs):
        """Alias of `AbstractFileSystem.ls`."""
        return self.ls(path, detail=detail, **kwargs)

    def cp(self, path1, path2, **kwargs):
        """Alias of `AbstractFileSystem.copy`."""
        return self.copy(path1, path2, **kwargs)

    def move(self, path1, path2, **kwargs):
        """Alias of `AbstractFileSystem.mv`."""
        return self.mv(path1, path2, **kwargs)

    def stat(self, path, **kwargs):
        """Alias of `AbstractFileSystem.info`."""
        return self.info(path, **kwargs)

    def disk_usage(self, path, total=True, maxdepth=None, **kwargs):
        """Alias of `AbstractFileSystem.du`."""
        return self.du(path, total=total, maxdepth=maxdepth, **kwargs)

    def rename(self, path1, path2, **kwargs):
        """Alias of `AbstractFileSystem.mv`."""
        return self.mv(path1, path2, **kwargs)

    def delete(self, path, recursive=False, maxdepth=None):
        """Alias of `AbstractFileSystem.rm`."""
        return self.rm(path, recursive=recursive, maxdepth=maxdepth)

    def upload(self, lpath, rpath, recursive=False, **kwargs):
        """Alias of `AbstractFileSystem.put`."""
        return self.put(lpath, rpath, recursive=recursive, **kwargs)

    def download(self, rpath, lpath, recursive=False, **kwargs):
        """Alias of `AbstractFileSystem.get`."""
        return self.get(rpath, lpath, recursive=recursive, **kwargs)

    def sign(self, path, expiration=100, **kwargs):
        """Create a signed URL representing the given path

        Some implementations allow temporary URLs to be generated, as a
        way of delegating credentials.

        Parameters
        ----------
        path : str
             The path on the filesystem
        expiration : int
            Number of seconds to enable the URL for (if supported)

        Returns
        -------
        URL : str
            The signed URL

        Raises
        ------
        NotImplementedError : if method is not implemented for a filesystem
        """
        raise NotImplementedError("Sign is not implemented for this filesystem")

    def _isfilestore(self):
        # Originally inherited from pyarrow DaskFileSystem. Keeping this
        # here for backwards compatibility as long as pyarrow uses its
        # legacy fsspec-compatible filesystems and thus accepts fsspec
        # filesystems as well
        return False


class AbstractBufferedFile(io.IOBase):
    """Convenient class to derive from to provide buffering

    In the case that the backend does not provide a pythonic file-like object
    already, this class contains much of the logic to build one. The only
    methods that need to be overridden are ``_upload_chunk``,
    ``_initiate_upload`` and ``_fetch_range``.
    """

    DEFAULT_BLOCK_SIZE = 5 * 2**20
    _details = None

    def __init__(
        self,
        fs,
        path,
        mode="rb",
        block_size="default",
        autocommit=True,
        cache_type="readahead",
        cache_options=None,
        size=None,
        **kwargs,
    ):
        """
        Template for files with buffered reading and writing

        Parameters
        ----------
        fs: instance of FileSystem
        path: str
            location in file-system
        mode: str
            Normal file modes. Currently only 'wb', 'ab' or 'rb'. Some file
            systems may be read-only, and some may not support append.
        block_size: int
            Buffer size for reading or writing, 'default' for class default
        autocommit: bool
            Whether to write to final destination; may only impact what
            happens when file is being closed.
        cache_type: {"readahead", "none", "mmap", "bytes"}, default "readahead"
            Caching policy in read mode. See the definitions in ``core``.
        cache_options : dict
            Additional options passed to the constructor for the cache specified
            by `cache_type`.
        size: int
            If given and in read mode, suppressed having to look up the file size
        kwargs:
            Gets stored as self.kwargs
        """
        from .core import caches

        self.path = path
        self.fs = fs
        self.mode = mode
        self.blocksize = (
            self.DEFAULT_BLOCK_SIZE if block_size in ["default", None] else block_size
        )
        self.loc = 0
        self.autocommit = autocommit
        self.end = None
        self.start = None
        self.closed = False

        if cache_options is None:
            cache_options = {}

        if "trim" in kwargs:
            warnings.warn(
                "Passing 'trim' to control the cache behavior has been deprecated. "
                "Specify it within the 'cache_options' argument instead.",
                FutureWarning,
            )
            cache_options["trim"] = kwargs.pop("trim")

        self.kwargs = kwargs

        if mode not in {"ab", "rb", "wb", "xb"}:
            raise NotImplementedError("File mode not supported")
        if mode == "rb":
            if size is not None:
                self.size = size
            else:
                self.size = self.details["size"]
            self.cache = caches[cache_type](
                self.blocksize, self._fetch_range, self.size, **cache_options
            )
        else:
            self.buffer = io.BytesIO()
            self.offset = None
            self.forced = False
            self.location = None

    @property
    def details(self):
        if self._details is None:
            self._details = self.fs.info(self.path)
        return self._details

    @details.setter
    def details(self, value):
        self._details = value
        self.size = value["size"]

    @property
    def full_name(self):
        return _unstrip_protocol(self.path, self.fs)

    @property
    def closed(self):
        # get around this attr being read-only in IOBase
        # use getattr here, since this can be called during del
        return getattr(self, "_closed", True)

    @closed.setter
    def closed(self, c):
        self._closed = c

    def __hash__(self):
        if "w" in self.mode:
            return id(self)
        else:
            return int(tokenize(self.details), 16)

    def __eq__(self, other):
        """Files are equal if they have the same checksum, only in read mode"""
        if self is other:
            return True
        return (
            isinstance(other, type(self))
            and self.mode == "rb"
            and other.mode == "rb"
            and hash(self) == hash(other)
        )

    def commit(self):
        """Move from temp to final destination"""

    def discard(self):
        """Throw away temporary file"""

    def info(self):
        """File information about this path"""
        if self.readable():
            return self.details
        else:
            raise ValueError("Info not available while writing")

    def tell(self):
        """Current file location"""
        return self.loc

    def seek(self, loc, whence=0):
        """Set current file location

        Parameters
        ----------
        loc: int
            byte location
        whence: {0, 1, 2}
            from start of file, current location or end of file, resp.
        """
        loc = int(loc)
        if not self.mode == "rb":
            raise OSError(ESPIPE, "Seek only available in read mode")
        if whence == 0:
            nloc = loc
        elif whence == 1:
            nloc = self.loc + loc
        elif whence == 2:
            nloc = self.size + loc
        else:
            raise ValueError(f"invalid whence ({whence}, should be 0, 1 or 2)")
        if nloc < 0:
            raise ValueError("Seek before start of file")
        self.loc = nloc
        return self.loc

    def write(self, data):
        """
        Write data to buffer.

        Buffer only sent on flush() or if buffer is greater than
        or equal to blocksize.

        Parameters
        ----------
        data: bytes
            Set of bytes to be written.
        """
        if not self.writable():
            raise ValueError("File not in write mode")
        if self.closed:
            raise ValueError("I/O operation on closed file.")
        if self.forced:
            raise ValueError("This file has been force-flushed, can only close")
        out = self.buffer.write(data)
        self.loc += out
        if self.buffer.tell() >= self.blocksize:
            self.flush()
        return out

    def flush(self, force=False):
        """
        Write buffered data to backend store.

        Writes the current buffer, if it is larger than the block-size, or if
        the file is being closed.

        Parameters
        ----------
        force: bool
            When closing, write the last block even if it is smaller than
            blocks are allowed to be. Disallows further writing to this file.
        """

        if self.closed:
            raise ValueError("Flush on closed file")
        if force and self.forced:
            raise ValueError("Force flush cannot be called more than once")
        if force:
            self.forced = True

        if self.readable():
            # no-op to flush on read-mode
            return

        if not force and self.buffer.tell() < self.blocksize:
            # Defer write on small block
            return

        if self.offset is None:
            # Initialize a multipart upload
            self.offset = 0
            try:
                self._initiate_upload()
            except:
                self.closed = True
                raise

        if self._upload_chunk(final=force) is not False:
            self.offset += self.buffer.seek(0, 2)
            self.buffer = io.BytesIO()

    def _upload_chunk(self, final=False):
        """Write one part of a multi-block file upload

        Parameters
        ==========
        final: bool
            This is the last block, so should complete file, if
            self.autocommit is True.
        """
        # may not yet have been initialized, may need to call _initialize_upload

    def _initiate_upload(self):
        """Create remote file/upload"""
        pass

    def _fetch_range(self, start, end):
        """Get the specified set of bytes from remote"""
        return self.fs.cat_file(self.path, start=start, end=end)

    def read(self, length=-1):
        """
        Return data from cache, or fetch pieces as necessary

        Parameters
        ----------
        length: int (-1)
            Number of bytes to read; if <0, all remaining bytes.
        """
        length = -1 if length is None else int(length)
        if self.mode != "rb":
            raise ValueError("File not in read mode")
        if length < 0:
            length = self.size - self.loc
        if self.closed:
            raise ValueError("I/O operation on closed file.")
        if length == 0:
            # don't even bother calling fetch
            return b""
        out = self.cache._fetch(self.loc, self.loc + length)

        logger.debug(
            "%s read: %i - %i %s",
            self,
            self.loc,
            self.loc + length,
            self.cache._log_stats(),
        )
        self.loc += len(out)
        return out

    def readinto(self, b):
        """mirrors builtin file's readinto method

        https://docs.python.org/3/library/io.html#io.RawIOBase.readinto
        """
        out = memoryview(b).cast("B")
        data = self.read(out.nbytes)
        out[: len(data)] = data
        return len(data)

    def readuntil(self, char=b"\n", blocks=None):
        """Return data between current position and first occurrence of char

        char is included in the output, except if the end of the tile is
        encountered first.

        Parameters
        ----------
        char: bytes
            Thing to find
        blocks: None or int
            How much to read in each go. Defaults to file blocksize - which may
            mean a new read on every call.
        """
        out = []
        while True:
            start = self.tell()
            part = self.read(blocks or self.blocksize)
            if len(part) == 0:
                break
            found = part.find(char)
            if found > -1:
                out.append(part[: found + len(char)])
                self.seek(start + found + len(char))
                break
            out.append(part)
        return b"".join(out)

    def readline(self):
        """Read until and including the first occurrence of newline character

        Note that, because of character encoding, this is not necessarily a
        true line ending.
        """
        return self.readuntil(b"\n")

    def __next__(self):
        out = self.readline()
        if out:
            return out
        raise StopIteration

    def __iter__(self):
        return self

    def readlines(self):
        """Return all data, split by the newline character, including the newline character"""
        data = self.read()
        lines = data.split(b"\n")
        out = [l + b"\n" for l in lines[:-1]]
        if data.endswith(b"\n"):
            return out
        else:
            return out + [lines[-1]]
        # return list(self)  ???

    def readinto1(self, b):
        return self.readinto(b)

    def close(self):
        """Close file

        Finalizes writes, discards cache
        """
        if getattr(self, "_unclosable", False):
            return
        if self.closed:
            return
        try:
            if self.mode == "rb":
                self.cache = None
            else:
                if not self.forced:
                    self.flush(force=True)

                if self.fs is not None:
                    self.fs.invalidate_cache(self.path)
                    self.fs.invalidate_cache(self.fs._parent(self.path))
        finally:
            self.closed = True

    def readable(self):
        """Whether opened for reading"""
        return "r" in self.mode and not self.closed

    def seekable(self):
        """Whether is seekable (only in read mode)"""
        return self.readable()

    def writable(self):
        """Whether opened for writing"""
        return self.mode in {"wb", "ab", "xb"} and not self.closed

    def __reduce__(self):
        if self.mode != "rb":
            raise RuntimeError("Pickling a writeable file is not supported")

        return reopen, (
            self.fs,
            self.path,
            self.mode,
            self.blocksize,
            self.loc,
            self.size,
            self.autocommit,
            self.cache.name if self.cache else "none",
            self.kwargs,
        )

    def __del__(self):
        if not self.closed:
            self.close()

    def __str__(self):
        return f"<File-like object {type(self.fs).__name__}, {self.path}>"

    __repr__ = __str__

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def reopen(fs, path, mode, blocksize, loc, size, autocommit, cache_type, kwargs):
    file = fs.open(
        path,
        mode=mode,
        block_size=blocksize,
        autocommit=autocommit,
        cache_type=cache_type,
        size=size,
        **kwargs,
    )
    if loc > 0:
        file.seek(loc)
    return file

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_attach_to_process\winappdbg\interactive.py ===
#!~/.wine/drive_c/Python25/python.exe
# -*- coding: utf-8 -*-

# Acknowledgements:
#  Nicolas Economou, for his command line debugger on which this is inspired.
#  http://tinyurl.com/nicolaseconomou

# Copyright (c) 2009-2014, Mario Vilas
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice,this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
Interactive debugging console.

@group Debugging:
    ConsoleDebugger

@group Exceptions:
    CmdError
"""

from __future__ import with_statement

__revision__ = "$Id$"

__all__ = ["ConsoleDebugger", "CmdError"]

# TODO document this module with docstrings.
# TODO command to set a last error breakpoint.
# TODO command to show available plugins.

from winappdbg import win32
from winappdbg import compat
from winappdbg.system import System
from winappdbg.util import PathOperations
from winappdbg.event import EventHandler, NoEvent
from winappdbg.textio import HexInput, HexOutput, HexDump, CrashDump, DebugLog

import os
import sys
import code
import time
import warnings
import traceback

# too many variables named "cmd" to have a module by the same name :P
from cmd import Cmd

# lazy imports
readline = None

# ==============================================================================


class DummyEvent(NoEvent):
    "Dummy event object used internally by L{ConsoleDebugger}."

    def get_pid(self):
        return self._pid

    def get_tid(self):
        return self._tid

    def get_process(self):
        return self._process

    def get_thread(self):
        return self._thread


# ==============================================================================


class CmdError(Exception):
    """
    Exception raised when a command parsing error occurs.
    Used internally by L{ConsoleDebugger}.
    """


# ==============================================================================


class ConsoleDebugger(Cmd, EventHandler):
    """
    Interactive console debugger.

    @see: L{Debug.interactive}
    """

    # ------------------------------------------------------------------------------
    # Class variables

    # Exception to raise when an error occurs executing a command.
    command_error_exception = CmdError

    # Milliseconds to wait for debug events in the main loop.
    dwMilliseconds = 100

    # History file name.
    history_file = ".winappdbg_history"

    # Confirm before quitting?
    confirm_quit = True

    # Valid plugin name characters.
    valid_plugin_name_chars = "ABCDEFGHIJKLMNOPQRSTUVWXY" "abcdefghijklmnopqrstuvwxy" "012345678" "_"

    # Names of the registers.
    segment_names = ("cs", "ds", "es", "fs", "gs")

    register_alias_64_to_32 = {
        "eax": "Rax",
        "ebx": "Rbx",
        "ecx": "Rcx",
        "edx": "Rdx",
        "eip": "Rip",
        "ebp": "Rbp",
        "esp": "Rsp",
        "esi": "Rsi",
        "edi": "Rdi",
    }
    register_alias_64_to_16 = {"ax": "Rax", "bx": "Rbx", "cx": "Rcx", "dx": "Rdx"}
    register_alias_64_to_8_low = {"al": "Rax", "bl": "Rbx", "cl": "Rcx", "dl": "Rdx"}
    register_alias_64_to_8_high = {"ah": "Rax", "bh": "Rbx", "ch": "Rcx", "dh": "Rdx"}
    register_alias_32_to_16 = {"ax": "Eax", "bx": "Ebx", "cx": "Ecx", "dx": "Edx"}
    register_alias_32_to_8_low = {"al": "Eax", "bl": "Ebx", "cl": "Ecx", "dl": "Edx"}
    register_alias_32_to_8_high = {"ah": "Eax", "bh": "Ebx", "ch": "Ecx", "dh": "Edx"}

    register_aliases_full_32 = list(segment_names)
    register_aliases_full_32.extend(compat.iterkeys(register_alias_32_to_16))
    register_aliases_full_32.extend(compat.iterkeys(register_alias_32_to_8_low))
    register_aliases_full_32.extend(compat.iterkeys(register_alias_32_to_8_high))
    register_aliases_full_32 = tuple(register_aliases_full_32)

    register_aliases_full_64 = list(segment_names)
    register_aliases_full_64.extend(compat.iterkeys(register_alias_64_to_32))
    register_aliases_full_64.extend(compat.iterkeys(register_alias_64_to_16))
    register_aliases_full_64.extend(compat.iterkeys(register_alias_64_to_8_low))
    register_aliases_full_64.extend(compat.iterkeys(register_alias_64_to_8_high))
    register_aliases_full_64 = tuple(register_aliases_full_64)

    # Names of the control flow instructions.
    jump_instructions = (
        "jmp",
        "jecxz",
        "jcxz",
        "ja",
        "jnbe",
        "jae",
        "jnb",
        "jb",
        "jnae",
        "jbe",
        "jna",
        "jc",
        "je",
        "jz",
        "jnc",
        "jne",
        "jnz",
        "jnp",
        "jpo",
        "jp",
        "jpe",
        "jg",
        "jnle",
        "jge",
        "jnl",
        "jl",
        "jnge",
        "jle",
        "jng",
        "jno",
        "jns",
        "jo",
        "js",
    )
    call_instructions = ("call", "ret", "retn")
    loop_instructions = ("loop", "loopz", "loopnz", "loope", "loopne")
    control_flow_instructions = call_instructions + loop_instructions + jump_instructions

    # ------------------------------------------------------------------------------
    # Instance variables

    def __init__(self):
        """
        Interactive console debugger.

        @see: L{Debug.interactive}
        """
        Cmd.__init__(self)
        EventHandler.__init__(self)

        # Quit the debugger when True.
        self.debuggerExit = False

        # Full path to the history file.
        self.history_file_full_path = None

        # Last executed command.
        self.__lastcmd = ""

    # ------------------------------------------------------------------------------
    # Debugger

    # Use this Debug object.
    def start_using_debugger(self, debug):
        # Clear the previous Debug object.
        self.stop_using_debugger()

        # Keep the Debug object.
        self.debug = debug

        # Set ourselves as the event handler for the debugger.
        self.prevHandler = debug.set_event_handler(self)

    # Stop using the Debug object given by start_using_debugger().
    # Circular references must be removed, or the destructors never get called.
    def stop_using_debugger(self):
        if hasattr(self, "debug"):
            debug = self.debug
            debug.set_event_handler(self.prevHandler)
            del self.prevHandler
            del self.debug
            return debug
        return None

    # Destroy the Debug object.
    def destroy_debugger(self, autodetach=True):
        debug = self.stop_using_debugger()
        if debug is not None:
            if not autodetach:
                debug.kill_all(bIgnoreExceptions=True)
                debug.lastEvent = None
            debug.stop()
        del debug

    @property
    def lastEvent(self):
        return self.debug.lastEvent

    def set_fake_last_event(self, process):
        if self.lastEvent is None:
            self.debug.lastEvent = DummyEvent(self.debug)
            self.debug.lastEvent._process = process
            self.debug.lastEvent._thread = process.get_thread(process.get_thread_ids()[0])
            self.debug.lastEvent._pid = process.get_pid()
            self.debug.lastEvent._tid = self.lastEvent._thread.get_tid()

    # ------------------------------------------------------------------------------
    # Input

    # TODO
    # * try to guess breakpoints when insufficient data is given
    # * child Cmd instances will have to be used for other prompts, for example
    #   when assembling or editing memory - it may also be a good idea to think
    #   if it's possible to make the main Cmd instance also a child, instead of
    #   the debugger itself - probably the same goes for the EventHandler, maybe
    #   it can be used as a contained object rather than a parent class.

    # Join a token list into an argument string.
    def join_tokens(self, token_list):
        return self.debug.system.argv_to_cmdline(token_list)

    # Split an argument string into a token list.
    def split_tokens(self, arg, min_count=0, max_count=None):
        token_list = self.debug.system.cmdline_to_argv(arg)
        if len(token_list) < min_count:
            raise CmdError("missing parameters.")
        if max_count and len(token_list) > max_count:
            raise CmdError("too many parameters.")
        return token_list

    # Token is a thread ID or name.
    def input_thread(self, token):
        targets = self.input_thread_list([token])
        if len(targets) == 0:
            raise CmdError("missing thread name or ID")
        if len(targets) > 1:
            msg = "more than one thread with that name:\n"
            for tid in targets:
                msg += "\t%d\n" % tid
            msg = msg[: -len("\n")]
            raise CmdError(msg)
        return targets[0]

    # Token list is a list of thread IDs or names.
    def input_thread_list(self, token_list):
        targets = set()
        system = self.debug.system
        for token in token_list:
            try:
                tid = self.input_integer(token)
                if not system.has_thread(tid):
                    raise CmdError("thread not found (%d)" % tid)
                targets.add(tid)
            except ValueError:
                found = set()
                for process in system.iter_processes():
                    found.update(system.find_threads_by_name(token))
                if not found:
                    raise CmdError("thread not found (%s)" % token)
                for thread in found:
                    targets.add(thread.get_tid())
        targets = list(targets)
        targets.sort()
        return targets

    # Token is a process ID or name.
    def input_process(self, token):
        targets = self.input_process_list([token])
        if len(targets) == 0:
            raise CmdError("missing process name or ID")
        if len(targets) > 1:
            msg = "more than one process with that name:\n"
            for pid in targets:
                msg += "\t%d\n" % pid
            msg = msg[: -len("\n")]
            raise CmdError(msg)
        return targets[0]

    # Token list is a list of process IDs or names.
    def input_process_list(self, token_list):
        targets = set()
        system = self.debug.system
        for token in token_list:
            try:
                pid = self.input_integer(token)
                if not system.has_process(pid):
                    raise CmdError("process not found (%d)" % pid)
                targets.add(pid)
            except ValueError:
                found = system.find_processes_by_filename(token)
                if not found:
                    raise CmdError("process not found (%s)" % token)
                for process, _ in found:
                    targets.add(process.get_pid())
        targets = list(targets)
        targets.sort()
        return targets

    # Token is a command line to execute.
    def input_command_line(self, command_line):
        argv = self.debug.system.cmdline_to_argv(command_line)
        if not argv:
            raise CmdError("missing command line to execute")
        fname = argv[0]
        if not os.path.exists(fname):
            try:
                fname, _ = win32.SearchPath(None, fname, ".exe")
            except WindowsError:
                raise CmdError("file not found: %s" % fname)
            argv[0] = fname
            command_line = self.debug.system.argv_to_cmdline(argv)
        return command_line

    # Token is an integer.
    # Only hexadecimal format is supported.
    def input_hexadecimal_integer(self, token):
        return int(token, 0x10)

    # Token is an integer.
    # It can be in any supported format.
    def input_integer(self, token):
        return HexInput.integer(token)

    # #    input_integer = input_hexadecimal_integer

    # Token is an address.
    # The address can be a integer, a label or a register.
    def input_address(self, token, pid=None, tid=None):
        address = None
        if self.is_register(token):
            if tid is None:
                if self.lastEvent is None or pid != self.lastEvent.get_pid():
                    msg = "can't resolve register (%s) for unknown thread"
                    raise CmdError(msg % token)
                tid = self.lastEvent.get_tid()
            address = self.input_register(token, tid)
        if address is None:
            try:
                address = self.input_hexadecimal_integer(token)
            except ValueError:
                if pid is None:
                    if self.lastEvent is None:
                        raise CmdError("no current process set")
                    process = self.lastEvent.get_process()
                elif self.lastEvent is not None and pid == self.lastEvent.get_pid():
                    process = self.lastEvent.get_process()
                else:
                    try:
                        process = self.debug.system.get_process(pid)
                    except KeyError:
                        raise CmdError("process not found (%d)" % pid)
                try:
                    address = process.resolve_label(token)
                except Exception:
                    raise CmdError("unknown address (%s)" % token)
        return address

    # Token is an address range, or a single address.
    # The addresses can be integers, labels or registers.
    def input_address_range(self, token_list, pid=None, tid=None):
        if len(token_list) == 2:
            token_1, token_2 = token_list
            address = self.input_address(token_1, pid, tid)
            try:
                size = self.input_integer(token_2)
            except ValueError:
                raise CmdError("bad address range: %s %s" % (token_1, token_2))
        elif len(token_list) == 1:
            token = token_list[0]
            if "-" in token:
                try:
                    token_1, token_2 = token.split("-")
                except Exception:
                    raise CmdError("bad address range: %s" % token)
                address = self.input_address(token_1, pid, tid)
                size = self.input_address(token_2, pid, tid) - address
            else:
                address = self.input_address(token, pid, tid)
                size = None
        return address, size

    # XXX TODO
    # Support non-integer registers here.
    def is_register(self, token):
        if win32.arch == "i386":
            if token in self.register_aliases_full_32:
                return True
            token = token.title()
            for name, typ in win32.CONTEXT._fields_:
                if name == token:
                    return win32.sizeof(typ) == win32.sizeof(win32.DWORD)
        elif win32.arch == "amd64":
            if token in self.register_aliases_full_64:
                return True
            token = token.title()
            for name, typ in win32.CONTEXT._fields_:
                if name == token:
                    return win32.sizeof(typ) == win32.sizeof(win32.DWORD64)
        return False

    # The token is a register name.
    # Returns None if no register name is matched.
    def input_register(self, token, tid=None):
        if tid is None:
            if self.lastEvent is None:
                raise CmdError("no current process set")
            thread = self.lastEvent.get_thread()
        else:
            thread = self.debug.system.get_thread(tid)
        ctx = thread.get_context()

        token = token.lower()
        title = token.title()

        if title in ctx:
            return ctx.get(title)  # eax -> Eax

        if ctx.arch == "i386":
            if token in self.segment_names:
                return ctx.get("Seg%s" % title)  # cs -> SegCs

            if token in self.register_alias_32_to_16:
                return ctx.get(self.register_alias_32_to_16[token]) & 0xFFFF

            if token in self.register_alias_32_to_8_low:
                return ctx.get(self.register_alias_32_to_8_low[token]) & 0xFF

            if token in self.register_alias_32_to_8_high:
                return (ctx.get(self.register_alias_32_to_8_high[token]) & 0xFF00) >> 8

        elif ctx.arch == "amd64":
            if token in self.segment_names:
                return ctx.get("Seg%s" % title)  # cs -> SegCs

            if token in self.register_alias_64_to_32:
                return ctx.get(self.register_alias_64_to_32[token]) & 0xFFFFFFFF

            if token in self.register_alias_64_to_16:
                return ctx.get(self.register_alias_64_to_16[token]) & 0xFFFF

            if token in self.register_alias_64_to_8_low:
                return ctx.get(self.register_alias_64_to_8_low[token]) & 0xFF

            if token in self.register_alias_64_to_8_high:
                return (ctx.get(self.register_alias_64_to_8_high[token]) & 0xFF00) >> 8

        return None

    # Token list contains an address or address range.
    # The prefix is also parsed looking for process and thread IDs.
    def input_full_address_range(self, token_list):
        pid, tid = self.get_process_and_thread_ids_from_prefix()
        address, size = self.input_address_range(token_list, pid, tid)
        return pid, tid, address, size

    # Token list contains a breakpoint.
    def input_breakpoint(self, token_list):
        pid, tid, address, size = self.input_full_address_range(token_list)
        if not self.debug.is_debugee(pid):
            raise CmdError("target process is not being debugged")
        return pid, tid, address, size

    # Token list contains a memory address, and optional size and process.
    # Sets the results as the default for the next display command.
    def input_display(self, token_list, default_size=64):
        pid, tid, address, size = self.input_full_address_range(token_list)
        if not size:
            size = default_size
        next_address = HexOutput.integer(address + size)
        self.default_display_target = next_address
        return pid, tid, address, size

    # ------------------------------------------------------------------------------
    # Output

    # Tell the user a module was loaded.
    def print_module_load(self, event):
        mod = event.get_module()
        base = mod.get_base()
        name = mod.get_filename()
        if not name:
            name = ""
        msg = "Loaded module (%s) %s"
        msg = msg % (HexDump.address(base), name)
        print(msg)

    # Tell the user a module was unloaded.
    def print_module_unload(self, event):
        mod = event.get_module()
        base = mod.get_base()
        name = mod.get_filename()
        if not name:
            name = ""
        msg = "Unloaded module (%s) %s"
        msg = msg % (HexDump.address(base), name)
        print(msg)

    # Tell the user a process was started.
    def print_process_start(self, event):
        pid = event.get_pid()
        start = event.get_start_address()
        if start:
            start = HexOutput.address(start)
            print("Started process %d at %s" % (pid, start))
        else:
            print("Attached to process %d" % pid)

    # Tell the user a thread was started.
    def print_thread_start(self, event):
        tid = event.get_tid()
        start = event.get_start_address()
        if start:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                start = event.get_process().get_label_at_address(start)
            print("Started thread %d at %s" % (tid, start))
        else:
            print("Attached to thread %d" % tid)

    # Tell the user a process has finished.
    def print_process_end(self, event):
        pid = event.get_pid()
        code = event.get_exit_code()
        print("Process %d terminated, exit code %d" % (pid, code))

    # Tell the user a thread has finished.
    def print_thread_end(self, event):
        tid = event.get_tid()
        code = event.get_exit_code()
        print("Thread %d terminated, exit code %d" % (tid, code))

    # Print(debug strings.
    def print_debug_string(self, event):
        tid = event.get_tid()
        string = event.get_debug_string()
        print("Thread %d says: %r" % (tid, string))

    # Inform the user of any other debugging event.
    def print_event(self, event):
        code = HexDump.integer(event.get_event_code())
        name = event.get_event_name()
        desc = event.get_event_description()
        if code in desc:
            print("")
            print("%s: %s" % (name, desc))
        else:
            print("")
            print("%s (%s): %s" % (name, code, desc))
        self.print_event_location(event)

    # Stop on exceptions and prompt for commands.
    def print_exception(self, event):
        address = HexDump.address(event.get_exception_address())
        code = HexDump.integer(event.get_exception_code())
        desc = event.get_exception_description()
        if event.is_first_chance():
            chance = "first"
        else:
            chance = "second"
        if code in desc:
            msg = "%s at address %s (%s chance)" % (desc, address, chance)
        else:
            msg = "%s (%s) at address %s (%s chance)" % (desc, code, address, chance)
        print("")
        print(msg)
        self.print_event_location(event)

    # Show the current location in the code.
    def print_event_location(self, event):
        process = event.get_process()
        thread = event.get_thread()
        self.print_current_location(process, thread)

    # Show the current location in the code.
    def print_breakpoint_location(self, event):
        process = event.get_process()
        thread = event.get_thread()
        pc = event.get_exception_address()
        self.print_current_location(process, thread, pc)

    # Show the current location in any process and thread.
    def print_current_location(self, process=None, thread=None, pc=None):
        if not process:
            if self.lastEvent is None:
                raise CmdError("no current process set")
            process = self.lastEvent.get_process()
        if not thread:
            if self.lastEvent is None:
                raise CmdError("no current process set")
            thread = self.lastEvent.get_thread()
        thread.suspend()
        try:
            if pc is None:
                pc = thread.get_pc()
            ctx = thread.get_context()
        finally:
            thread.resume()
        label = process.get_label_at_address(pc)
        try:
            disasm = process.disassemble(pc, 15)
        except WindowsError:
            disasm = None
        except NotImplementedError:
            disasm = None
        print("")
        print(
            CrashDump.dump_registers(ctx),
        )
        print("%s:" % label)
        if disasm:
            print(CrashDump.dump_code_line(disasm[0], pc, bShowDump=True))
        else:
            try:
                data = process.peek(pc, 15)
            except Exception:
                data = None
            if data:
                print("%s: %s" % (HexDump.address(pc), HexDump.hexblock_byte(data)))
            else:
                print("%s: ???" % HexDump.address(pc))

    # Display memory contents using a given method.
    def print_memory_display(self, arg, method):
        if not arg:
            arg = self.default_display_target
        token_list = self.split_tokens(arg, 1, 2)
        pid, tid, address, size = self.input_display(token_list)
        label = self.get_process(pid).get_label_at_address(address)
        data = self.read_memory(address, size, pid)
        if data:
            print("%s:" % label)
            print(
                method(data, address),
            )

    # ------------------------------------------------------------------------------
    # Debugging

    # Get the process ID from the prefix or the last event.
    def get_process_id_from_prefix(self):
        if self.cmdprefix:
            pid = self.input_process(self.cmdprefix)
        else:
            if self.lastEvent is None:
                raise CmdError("no current process set")
            pid = self.lastEvent.get_pid()
        return pid

    # Get the thread ID from the prefix or the last event.
    def get_thread_id_from_prefix(self):
        if self.cmdprefix:
            tid = self.input_thread(self.cmdprefix)
        else:
            if self.lastEvent is None:
                raise CmdError("no current process set")
            tid = self.lastEvent.get_tid()
        return tid

    # Get the process from the prefix or the last event.
    def get_process_from_prefix(self):
        pid = self.get_process_id_from_prefix()
        return self.get_process(pid)

    # Get the thread from the prefix or the last event.
    def get_thread_from_prefix(self):
        tid = self.get_thread_id_from_prefix()
        return self.get_thread(tid)

    # Get the process and thread IDs from the prefix or the last event.
    def get_process_and_thread_ids_from_prefix(self):
        if self.cmdprefix:
            try:
                pid = self.input_process(self.cmdprefix)
                tid = None
            except CmdError:
                try:
                    tid = self.input_thread(self.cmdprefix)
                    pid = self.debug.system.get_thread(tid).get_pid()
                except CmdError:
                    msg = "unknown process or thread (%s)" % self.cmdprefix
                    raise CmdError(msg)
        else:
            if self.lastEvent is None:
                raise CmdError("no current process set")
            pid = self.lastEvent.get_pid()
            tid = self.lastEvent.get_tid()
        return pid, tid

    # Get the process and thread from the prefix or the last event.
    def get_process_and_thread_from_prefix(self):
        pid, tid = self.get_process_and_thread_ids_from_prefix()
        process = self.get_process(pid)
        thread = self.get_thread(tid)
        return process, thread

    # Get the process object.
    def get_process(self, pid=None):
        if pid is None:
            if self.lastEvent is None:
                raise CmdError("no current process set")
            process = self.lastEvent.get_process()
        elif self.lastEvent is not None and pid == self.lastEvent.get_pid():
            process = self.lastEvent.get_process()
        else:
            try:
                process = self.debug.system.get_process(pid)
            except KeyError:
                raise CmdError("process not found (%d)" % pid)
        return process

    # Get the thread object.
    def get_thread(self, tid=None):
        if tid is None:
            if self.lastEvent is None:
                raise CmdError("no current process set")
            thread = self.lastEvent.get_thread()
        elif self.lastEvent is not None and tid == self.lastEvent.get_tid():
            thread = self.lastEvent.get_thread()
        else:
            try:
                thread = self.debug.system.get_thread(tid)
            except KeyError:
                raise CmdError("thread not found (%d)" % tid)
        return thread

    # Read the process memory.
    def read_memory(self, address, size, pid=None):
        process = self.get_process(pid)
        try:
            data = process.peek(address, size)
        except WindowsError:
            orig_address = HexOutput.integer(address)
            next_address = HexOutput.integer(address + size)
            msg = "error reading process %d, from %s to %s (%d bytes)"
            msg = msg % (pid, orig_address, next_address, size)
            raise CmdError(msg)
        return data

    # Write the process memory.
    def write_memory(self, address, data, pid=None):
        process = self.get_process(pid)
        try:
            process.write(address, data)
        except WindowsError:
            size = len(data)
            orig_address = HexOutput.integer(address)
            next_address = HexOutput.integer(address + size)
            msg = "error reading process %d, from %s to %s (%d bytes)"
            msg = msg % (pid, orig_address, next_address, size)
            raise CmdError(msg)

    # Change a register value.
    def change_register(self, register, value, tid=None):
        # Get the thread.
        if tid is None:
            if self.lastEvent is None:
                raise CmdError("no current process set")
            thread = self.lastEvent.get_thread()
        else:
            try:
                thread = self.debug.system.get_thread(tid)
            except KeyError:
                raise CmdError("thread not found (%d)" % tid)

        # Convert the value to integer type.
        try:
            value = self.input_integer(value)
        except ValueError:
            pid = thread.get_pid()
            value = self.input_address(value, pid, tid)

        # Suspend the thread.
        # The finally clause ensures the thread is resumed before returning.
        thread.suspend()
        try:
            # Get the current context.
            ctx = thread.get_context()

            # Register name matching is case insensitive.
            register = register.lower()

            # Integer 32 bits registers.
            if register in self.register_names:
                register = register.title()  # eax -> Eax

            # Segment (16 bit) registers.
            if register in self.segment_names:
                register = "Seg%s" % register.title()  # cs -> SegCs
                value = value & 0x0000FFFF

            # Integer 16 bits registers.
            if register in self.register_alias_16:
                register = self.register_alias_16[register]
                previous = ctx.get(register) & 0xFFFF0000
                value = (value & 0x0000FFFF) | previous

            # Integer 8 bits registers (low part).
            if register in self.register_alias_8_low:
                register = self.register_alias_8_low[register]
                previous = ctx.get(register) % 0xFFFFFF00
                value = (value & 0x000000FF) | previous

            # Integer 8 bits registers (high part).
            if register in self.register_alias_8_high:
                register = self.register_alias_8_high[register]
                previous = ctx.get(register) % 0xFFFF00FF
                value = ((value & 0x000000FF) << 8) | previous

            # Set the new context.
            ctx.__setitem__(register, value)
            thread.set_context(ctx)

        # Resume the thread.
        finally:
            thread.resume()

    # Very crude way to find data within the process memory.
    # TODO: Perhaps pfind.py can be integrated here instead.
    def find_in_memory(self, query, process):
        for mbi in process.get_memory_map():
            if mbi.State != win32.MEM_COMMIT or mbi.Protect & win32.PAGE_GUARD:
                continue
            address = mbi.BaseAddress
            size = mbi.RegionSize
            try:
                data = process.read(address, size)
            except WindowsError:
                msg = "*** Warning: read error at address %s"
                msg = msg % HexDump.address(address)
                print(msg)
            width = min(len(query), 16)
            p = data.find(query)
            while p >= 0:
                q = p + len(query)
                d = data[p : min(q, p + width)]
                h = HexDump.hexline(d, width=width)
                a = HexDump.address(address + p)
                print("%s: %s" % (a, h))
                p = data.find(query, q)

    # Kill a process.
    def kill_process(self, pid):
        process = self.debug.system.get_process(pid)
        try:
            process.kill()
            if self.debug.is_debugee(pid):
                self.debug.detach(pid)
            print("Killed process (%d)" % pid)
        except Exception:
            print("Error trying to kill process (%d)" % pid)

    # Kill a thread.
    def kill_thread(self, tid):
        thread = self.debug.system.get_thread(tid)
        try:
            thread.kill()
            process = thread.get_process()
            pid = process.get_pid()
            if self.debug.is_debugee(pid) and not process.is_alive():
                self.debug.detach(pid)
            print("Killed thread (%d)" % tid)
        except Exception:
            print("Error trying to kill thread (%d)" % tid)

    # ------------------------------------------------------------------------------
    # Command prompt input

    # Prompt the user for commands.
    def prompt_user(self):
        while not self.debuggerExit:
            try:
                self.cmdloop()
                break
            except CmdError:
                e = sys.exc_info()[1]
                print("*** Error: %s" % str(e))
            except Exception:
                traceback.print_exc()

    # #                self.debuggerExit = True

    # Prompt the user for a YES/NO kind of question.
    def ask_user(self, msg, prompt="Are you sure? (y/N): "):
        print(msg)
        answer = raw_input(prompt)
        answer = answer.strip()[:1].lower()
        return answer == "y"

    # Autocomplete the given command when not ambiguous.
    # Convert it to lowercase (so commands are seen as case insensitive).
    def autocomplete(self, cmd):
        cmd = cmd.lower()
        completed = self.completenames(cmd)
        if len(completed) == 1:
            cmd = completed[0]
        return cmd

    # Get the help text for the given list of command methods.
    # Note it's NOT a list of commands, but a list of actual method names.
    # Each line of text is stripped and all lines are sorted.
    # Repeated text lines are removed.
    # Returns a single, possibly multiline, string.
    def get_help(self, commands):
        msg = set()
        for name in commands:
            if name != "do_help":
                try:
                    doc = getattr(self, name).__doc__.split("\n")
                except Exception:
                    return "No help available when Python" " is run with the -OO switch."
                for x in doc:
                    x = x.strip()
                    if x:
                        msg.add("  %s" % x)
        msg = list(msg)
        msg.sort()
        msg = "\n".join(msg)
        return msg

    # Parse the prefix and remove it from the command line.
    def split_prefix(self, line):
        prefix = None
        if line.startswith("~"):
            pos = line.find(" ")
            if pos == 1:
                pos = line.find(" ", pos + 1)
            if not pos < 0:
                prefix = line[1:pos].strip()
                line = line[pos:].strip()
        return prefix, line

    # ------------------------------------------------------------------------------
    # Cmd() hacks

    # Header for help page.
    doc_header = "Available commands (type help * or help <command>)"

    # #    # Read and write directly to stdin and stdout.
    # #    # This prevents the use of raw_input and print.
    # #    use_rawinput = False

    @property
    def prompt(self):
        if self.lastEvent:
            pid = self.lastEvent.get_pid()
            tid = self.lastEvent.get_tid()
            if self.debug.is_debugee(pid):
                # #                return '~%d(%d)> ' % (tid, pid)
                return "%d:%d> " % (pid, tid)
        return "> "

    # Return a sorted list of method names.
    # Only returns the methods that implement commands.
    def get_names(self):
        names = Cmd.get_names(self)
        names = [x for x in set(names) if x.startswith("do_")]
        names.sort()
        return names

    # Automatically autocomplete commands, even if Tab wasn't pressed.
    # The prefix is removed from the line and stored in self.cmdprefix.
    # Also implement the commands that consist of a symbol character.
    def parseline(self, line):
        self.cmdprefix, line = self.split_prefix(line)
        line = line.strip()
        if line:
            if line[0] == ".":
                line = "plugin " + line[1:]
            elif line[0] == "#":
                line = "python " + line[1:]
        cmd, arg, line = Cmd.parseline(self, line)
        if cmd:
            cmd = self.autocomplete(cmd)
        return cmd, arg, line

    # #    # Don't repeat the last executed command.
    # #    def emptyline(self):
    # #        pass

    # Reset the defaults for some commands.
    def preloop(self):
        self.default_disasm_target = "eip"
        self.default_display_target = "eip"
        self.last_display_command = self.do_db

    # Put the prefix back in the command line.
    def get_lastcmd(self):
        return self.__lastcmd

    def set_lastcmd(self, lastcmd):
        if self.cmdprefix:
            lastcmd = "~%s %s" % (self.cmdprefix, lastcmd)
        self.__lastcmd = lastcmd

    lastcmd = property(get_lastcmd, set_lastcmd)

    # Quit the command prompt if the debuggerExit flag is on.
    def postcmd(self, stop, line):
        return stop or self.debuggerExit

    # ------------------------------------------------------------------------------
    # Commands

    # Each command contains a docstring with it's help text.
    # The help text consist of independent text lines,
    # where each line shows a command and it's parameters.
    # Each command method has the help message for itself and all it's aliases.
    # Only the docstring for the "help" command is shown as-is.

    # NOTE: Command methods MUST be all lowercase!

    # Extended help command.
    def do_help(self, arg):
        """
        ? - show the list of available commands
        ? * - show help for all commands
        ? <command> [command...] - show help for the given command(s)
        help - show the list of available commands
        help * - show help for all commands
        help <command> [command...] - show help for the given command(s)
        """
        if not arg:
            Cmd.do_help(self, arg)
        elif arg in ("?", "help"):
            # An easter egg :)
            print("  Help! I need somebody...")
            print("  Help! Not just anybody...")
            print("  Help! You know, I need someone...")
            print("  Heeelp!")
        else:
            if arg == "*":
                commands = self.get_names()
                commands = [x for x in commands if x.startswith("do_")]
            else:
                commands = set()
                for x in arg.split(" "):
                    x = x.strip()
                    if x:
                        for n in self.completenames(x):
                            commands.add("do_%s" % n)
                commands = list(commands)
                commands.sort()
            print(self.get_help(commands))

    def do_shell(self, arg):
        """
        ! - spawn a system shell
        shell - spawn a system shell
        ! <command> [arguments...] - execute a single shell command
        shell <command> [arguments...] - execute a single shell command
        """
        if self.cmdprefix:
            raise CmdError("prefix not allowed")

        # Try to use the environment to locate cmd.exe.
        # If not found, it's usually OK to just use the filename,
        # since cmd.exe is one of those "magic" programs that
        # can be automatically found by CreateProcess.
        shell = os.getenv("ComSpec", "cmd.exe")

        # When given a command, run it and return.
        # When no command is given, spawn a shell.
        if arg:
            arg = "%s /c %s" % (shell, arg)
        else:
            arg = shell
        process = self.debug.system.start_process(arg, bConsole=True)
        process.wait()

    # This hack fixes a bug in Python, the interpreter console is closing the
    # stdin pipe when calling the exit() function (Ctrl+Z seems to work fine).
    class _PythonExit(object):
        def __repr__(self):
            return "Use exit() or Ctrl-Z plus Return to exit"

        def __call__(self):
            raise SystemExit()

    _python_exit = _PythonExit()

    # Spawns a Python shell with some handy local variables and the winappdbg
    # module already imported. Also the console banner is improved.
    def _spawn_python_shell(self, arg):
        import winappdbg

        banner = 'Python %s on %s\nType "help", "copyright", ' '"credits" or "license" for more information.\n'
        platform = winappdbg.version.lower()
        platform = "WinAppDbg %s" % platform
        banner = banner % (sys.version, platform)
        local = {}
        local.update(__builtins__)
        local.update(
            {
                "__name__": "__console__",
                "__doc__": None,
                "exit": self._python_exit,
                "self": self,
                "arg": arg,
                "winappdbg": winappdbg,
            }
        )
        try:
            code.interact(banner=banner, local=local)
        except SystemExit:
            # We need to catch it so it doesn't kill our program.
            pass

    def do_python(self, arg):
        """
        # - spawn a python interpreter
        python - spawn a python interpreter
        # <statement> - execute a single python statement
        python <statement> - execute a single python statement
        """
        if self.cmdprefix:
            raise CmdError("prefix not allowed")

        # When given a Python statement, execute it directly.
        if arg:
            try:
                compat.exec_(arg, globals(), locals())
            except Exception:
                traceback.print_exc()

        # When no statement is given, spawn a Python interpreter.
        else:
            try:
                self._spawn_python_shell(arg)
            except Exception:
                e = sys.exc_info()[1]
                raise CmdError("unhandled exception when running Python console: %s" % e)

    def do_quit(self, arg):
        """
        quit - close the debugging session
        q - close the debugging session
        """
        if self.cmdprefix:
            raise CmdError("prefix not allowed")
        if arg:
            raise CmdError("too many arguments")
        if self.confirm_quit:
            count = self.debug.get_debugee_count()
            if count > 0:
                if count == 1:
                    msg = "There's a program still running."
                else:
                    msg = "There are %s programs still running." % count
                if not self.ask_user(msg):
                    return False
        self.debuggerExit = True
        return True

    do_q = do_quit

    def do_attach(self, arg):
        """
        attach <target> [target...] - attach to the given process(es)
        """
        if self.cmdprefix:
            raise CmdError("prefix not allowed")
        targets = self.input_process_list(self.split_tokens(arg, 1))
        if not targets:
            print("Error: missing parameters")
        else:
            debug = self.debug
            for pid in targets:
                try:
                    debug.attach(pid)
                    print("Attached to process (%d)" % pid)
                except Exception:
                    print("Error: can't attach to process (%d)" % pid)

    def do_detach(self, arg):
        """
        [~process] detach - detach from the current process
        detach - detach from the current process
        detach <target> [target...] - detach from the given process(es)
        """
        debug = self.debug
        token_list = self.split_tokens(arg)
        if self.cmdprefix:
            token_list.insert(0, self.cmdprefix)
        targets = self.input_process_list(token_list)
        if not targets:
            if self.lastEvent is None:
                raise CmdError("no current process set")
            targets = [self.lastEvent.get_pid()]
        for pid in targets:
            try:
                debug.detach(pid)
                print("Detached from process (%d)" % pid)
            except Exception:
                print("Error: can't detach from process (%d)" % pid)

    def do_windowed(self, arg):
        """
        windowed <target> [arguments...] - run a windowed program for debugging
        """
        if self.cmdprefix:
            raise CmdError("prefix not allowed")
        cmdline = self.input_command_line(arg)
        try:
            process = self.debug.execl(arg, bConsole=False, bFollow=self.options.follow)
            print("Spawned process (%d)" % process.get_pid())
        except Exception:
            raise CmdError("can't execute")
        self.set_fake_last_event(process)

    def do_console(self, arg):
        """
        console <target> [arguments...] - run a console program for debugging
        """
        if self.cmdprefix:
            raise CmdError("prefix not allowed")
        cmdline = self.input_command_line(arg)
        try:
            process = self.debug.execl(arg, bConsole=True, bFollow=self.options.follow)
            print("Spawned process (%d)" % process.get_pid())
        except Exception:
            raise CmdError("can't execute")
        self.set_fake_last_event(process)

    def do_continue(self, arg):
        """
        continue - continue execution
        g - continue execution
        go - continue execution
        """
        if self.cmdprefix:
            raise CmdError("prefix not allowed")
        if arg:
            raise CmdError("too many arguments")
        if self.debug.get_debugee_count() > 0:
            return True

    do_g = do_continue
    do_go = do_continue

    def do_gh(self, arg):
        """
        gh - go with exception handled
        """
        if self.cmdprefix:
            raise CmdError("prefix not allowed")
        if arg:
            raise CmdError("too many arguments")
        if self.lastEvent:
            self.lastEvent.continueStatus = win32.DBG_EXCEPTION_HANDLED
        return self.do_go(arg)

    def do_gn(self, arg):
        """
        gn - go with exception not handled
        """
        if self.cmdprefix:
            raise CmdError("prefix not allowed")
        if arg:
            raise CmdError("too many arguments")
        if self.lastEvent:
            self.lastEvent.continueStatus = win32.DBG_EXCEPTION_NOT_HANDLED
        return self.do_go(arg)

    def do_refresh(self, arg):
        """
        refresh - refresh the list of running processes and threads
        [~process] refresh - refresh the list of running threads
        """
        if arg:
            raise CmdError("too many arguments")
        if self.cmdprefix:
            process = self.get_process_from_prefix()
            process.scan()
        else:
            self.debug.system.scan()

    def do_processlist(self, arg):
        """
        pl - show the processes being debugged
        processlist - show the processes being debugged
        """
        if self.cmdprefix:
            raise CmdError("prefix not allowed")
        if arg:
            raise CmdError("too many arguments")
        system = self.debug.system
        pid_list = self.debug.get_debugee_pids()
        if pid_list:
            print("Process ID   File name")
            for pid in pid_list:
                if pid == 0:
                    filename = "System Idle Process"
                elif pid == 4:
                    filename = "System"
                else:
                    filename = system.get_process(pid).get_filename()
                    filename = PathOperations.pathname_to_filename(filename)
                print("%-12d %s" % (pid, filename))

    do_pl = do_processlist

    def do_threadlist(self, arg):
        """
        tl - show the threads being debugged
        threadlist - show the threads being debugged
        """
        if arg:
            raise CmdError("too many arguments")
        if self.cmdprefix:
            process = self.get_process_from_prefix()
            for thread in process.iter_threads():
                tid = thread.get_tid()
                name = thread.get_name()
                print("%-12d %s" % (tid, name))
        else:
            system = self.debug.system
            pid_list = self.debug.get_debugee_pids()
            if pid_list:
                print("Thread ID    Thread name")
                for pid in pid_list:
                    process = system.get_process(pid)
                    for thread in process.iter_threads():
                        tid = thread.get_tid()
                        name = thread.get_name()
                        print("%-12d %s" % (tid, name))

    do_tl = do_threadlist

    def do_kill(self, arg):
        """
        [~process] kill - kill a process
        [~thread] kill - kill a thread
        kill - kill the current process
        kill * - kill all debugged processes
        kill <processes and/or threads...> - kill the given processes and threads
        """
        if arg:
            if arg == "*":
                target_pids = self.debug.get_debugee_pids()
                target_tids = list()
            else:
                target_pids = set()
                target_tids = set()
                if self.cmdprefix:
                    pid, tid = self.get_process_and_thread_ids_from_prefix()
                    if tid is None:
                        target_tids.add(tid)
                    else:
                        target_pids.add(pid)
                for token in self.split_tokens(arg):
                    try:
                        pid = self.input_process(token)
                        target_pids.add(pid)
                    except CmdError:
                        try:
                            tid = self.input_process(token)
                            target_pids.add(pid)
                        except CmdError:
                            msg = "unknown process or thread (%s)" % token
                            raise CmdError(msg)
                target_pids = list(target_pids)
                target_tids = list(target_tids)
                target_pids.sort()
                target_tids.sort()
            msg = "You are about to kill %d processes and %d threads."
            msg = msg % (len(target_pids), len(target_tids))
            if self.ask_user(msg):
                for pid in target_pids:
                    self.kill_process(pid)
                for tid in target_tids:
                    self.kill_thread(tid)
        else:
            if self.cmdprefix:
                pid, tid = self.get_process_and_thread_ids_from_prefix()
                if tid is None:
                    if self.lastEvent is not None and pid == self.lastEvent.get_pid():
                        msg = "You are about to kill the current process."
                    else:
                        msg = "You are about to kill process %d." % pid
                    if self.ask_user(msg):
                        self.kill_process(pid)
                else:
                    if self.lastEvent is not None and tid == self.lastEvent.get_tid():
                        msg = "You are about to kill the current thread."
                    else:
                        msg = "You are about to kill thread %d." % tid
                    if self.ask_user(msg):
                        self.kill_thread(tid)
            else:
                if self.lastEvent is None:
                    raise CmdError("no current process set")
                pid = self.lastEvent.get_pid()
                if self.ask_user("You are about to kill the current process."):
                    self.kill_process(pid)

    # TODO: create hidden threads using undocumented API calls.
    def do_modload(self, arg):
        """
        [~process] modload <filename.dll> - load a DLL module
        """
        filename = self.split_tokens(arg, 1, 1)[0]
        process = self.get_process_from_prefix()
        try:
            process.inject_dll(filename, bWait=False)
        except RuntimeError:
            print("Can't inject module: %r" % filename)

    # TODO: modunload

    def do_stack(self, arg):
        """
        [~thread] k - show the stack trace
        [~thread] stack - show the stack trace
        """
        if arg:  # XXX TODO add depth parameter
            raise CmdError("too many arguments")
        pid, tid = self.get_process_and_thread_ids_from_prefix()
        process = self.get_process(pid)
        thread = process.get_thread(tid)
        try:
            stack_trace = thread.get_stack_trace_with_labels()
            if stack_trace:
                print(
                    CrashDump.dump_stack_trace_with_labels(stack_trace),
                )
            else:
                print("No stack trace available for thread (%d)" % tid)
        except WindowsError:
            print("Can't get stack trace for thread (%d)" % tid)

    do_k = do_stack

    def do_break(self, arg):
        """
        break - force a debug break in all debugees
        break <process> [process...] - force a debug break
        """
        debug = self.debug
        system = debug.system
        targets = self.input_process_list(self.split_tokens(arg))
        if not targets:
            targets = debug.get_debugee_pids()
            targets.sort()
        if self.lastEvent:
            current = self.lastEvent.get_pid()
        else:
            current = None
        for pid in targets:
            if pid != current and debug.is_debugee(pid):
                process = system.get_process(pid)
                try:
                    process.debug_break()
                except WindowsError:
                    print("Can't force a debug break on process (%d)")

    def do_step(self, arg):
        """
        p - step on the current assembly instruction
        next - step on the current assembly instruction
        step - step on the current assembly instruction
        """
        if self.cmdprefix:
            raise CmdError("prefix not allowed")
        if self.lastEvent is None:
            raise CmdError("no current process set")
        if arg:  # XXX this check is to be removed
            raise CmdError("too many arguments")
        pid = self.lastEvent.get_pid()
        thread = self.lastEvent.get_thread()
        pc = thread.get_pc()
        code = thread.disassemble(pc, 16)[0]
        size = code[1]
        opcode = code[2].lower()
        if " " in opcode:
            opcode = opcode[: opcode.find(" ")]
        if opcode in self.jump_instructions or opcode in ("int", "ret", "retn"):
            return self.do_trace(arg)
        address = pc + size
        # #        print(hex(pc), hex(address), size   # XXX DEBUG
        self.debug.stalk_at(pid, address)
        return True

    do_p = do_step
    do_next = do_step

    def do_trace(self, arg):
        """
        t - trace at the current assembly instruction
        trace - trace at the current assembly instruction
        """
        if arg:  # XXX this check is to be removed
            raise CmdError("too many arguments")
        if self.lastEvent is None:
            raise CmdError("no current thread set")
        self.lastEvent.get_thread().set_tf()
        return True

    do_t = do_trace

    def do_bp(self, arg):
        """
        [~process] bp <address> - set a code breakpoint
        """
        pid = self.get_process_id_from_prefix()
        if not self.debug.is_debugee(pid):
            raise CmdError("target process is not being debugged")
        process = self.get_process(pid)
        token_list = self.split_tokens(arg, 1, 1)
        try:
            address = self.input_address(token_list[0], pid)
            deferred = False
        except Exception:
            address = token_list[0]
            deferred = True
        if not address:
            address = token_list[0]
            deferred = True
        self.debug.break_at(pid, address)
        if deferred:
            print("Deferred breakpoint set at %s" % address)
        else:
            print("Breakpoint set at %s" % address)

    def do_ba(self, arg):
        """
        [~thread] ba <a|w|e> <1|2|4|8> <address> - set hardware breakpoint
        """
        debug = self.debug
        thread = self.get_thread_from_prefix()
        pid = thread.get_pid()
        tid = thread.get_tid()
        if not debug.is_debugee(pid):
            raise CmdError("target thread is not being debugged")
        token_list = self.split_tokens(arg, 3, 3)
        access = token_list[0].lower()
        size = token_list[1]
        address = token_list[2]
        if access == "a":
            access = debug.BP_BREAK_ON_ACCESS
        elif access == "w":
            access = debug.BP_BREAK_ON_WRITE
        elif access == "e":
            access = debug.BP_BREAK_ON_EXECUTION
        else:
            raise CmdError("bad access type: %s" % token_list[0])
        if size == "1":
            size = debug.BP_WATCH_BYTE
        elif size == "2":
            size = debug.BP_WATCH_WORD
        elif size == "4":
            size = debug.BP_WATCH_DWORD
        elif size == "8":
            size = debug.BP_WATCH_QWORD
        else:
            raise CmdError("bad breakpoint size: %s" % size)
        thread = self.get_thread_from_prefix()
        tid = thread.get_tid()
        pid = thread.get_pid()
        if not debug.is_debugee(pid):
            raise CmdError("target process is not being debugged")
        address = self.input_address(address, pid)
        if debug.has_hardware_breakpoint(tid, address):
            debug.erase_hardware_breakpoint(tid, address)
        debug.define_hardware_breakpoint(tid, address, access, size)
        debug.enable_hardware_breakpoint(tid, address)

    def do_bm(self, arg):
        """
        [~process] bm <address-address> - set memory breakpoint
        """
        pid = self.get_process_id_from_prefix()
        if not self.debug.is_debugee(pid):
            raise CmdError("target process is not being debugged")
        process = self.get_process(pid)
        token_list = self.split_tokens(arg, 1, 2)
        address, size = self.input_address_range(token_list[0], pid)
        self.debug.watch_buffer(pid, address, size)

    def do_bl(self, arg):
        """
        bl - list the breakpoints for the current process
        bl * - list the breakpoints for all processes
        [~process] bl - list the breakpoints for the given process
        bl <process> [process...] - list the breakpoints for each given process
        """
        debug = self.debug
        if arg == "*":
            if self.cmdprefix:
                raise CmdError("prefix not supported")
            breakpoints = debug.get_debugee_pids()
        else:
            targets = self.input_process_list(self.split_tokens(arg))
            if self.cmdprefix:
                targets.insert(0, self.input_process(self.cmdprefix))
            if not targets:
                if self.lastEvent is None:
                    raise CmdError("no current process is set")
                targets = [self.lastEvent.get_pid()]
        for pid in targets:
            bplist = debug.get_process_code_breakpoints(pid)
            printed_process_banner = False
            if bplist:
                if not printed_process_banner:
                    print("Process %d:" % pid)
                    printed_process_banner = True
                for bp in bplist:
                    address = repr(bp)[1:-1].replace("remote address ", "")
                    print("  %s" % address)
            dbplist = debug.get_process_deferred_code_breakpoints(pid)
            if dbplist:
                if not printed_process_banner:
                    print("Process %d:" % pid)
                    printed_process_banner = True
                for label, action, oneshot in dbplist:
                    if oneshot:
                        address = "  Deferred unconditional one-shot" " code breakpoint at %s"
                    else:
                        address = "  Deferred unconditional" " code breakpoint at %s"
                    address = address % label
                    print("  %s" % address)
            bplist = debug.get_process_page_breakpoints(pid)
            if bplist:
                if not printed_process_banner:
                    print("Process %d:" % pid)
                    printed_process_banner = True
                for bp in bplist:
                    address = repr(bp)[1:-1].replace("remote address ", "")
                    print("  %s" % address)
            for tid in debug.system.get_process(pid).iter_thread_ids():
                bplist = debug.get_thread_hardware_breakpoints(tid)
                if bplist:
                    print("Thread %d:" % tid)
                    for bp in bplist:
                        address = repr(bp)[1:-1].replace("remote address ", "")
                        print("  %s" % address)

    def do_bo(self, arg):
        """
        [~process] bo <address> - make a code breakpoint one-shot
        [~thread] bo <address> - make a hardware breakpoint one-shot
        [~process] bo <address-address> - make a memory breakpoint one-shot
        [~process] bo <address> <size> - make a memory breakpoint one-shot
        """
        token_list = self.split_tokens(arg, 1, 2)
        pid, tid, address, size = self.input_breakpoint(token_list)
        debug = self.debug
        found = False
        if size is None:
            if tid is not None:
                if debug.has_hardware_breakpoint(tid, address):
                    debug.enable_one_shot_hardware_breakpoint(tid, address)
                    found = True
            if pid is not None:
                if debug.has_code_breakpoint(pid, address):
                    debug.enable_one_shot_code_breakpoint(pid, address)
                    found = True
        else:
            if debug.has_page_breakpoint(pid, address):
                debug.enable_one_shot_page_breakpoint(pid, address)
                found = True
        if not found:
            print("Error: breakpoint not found.")

    def do_be(self, arg):
        """
        [~process] be <address> - enable a code breakpoint
        [~thread] be <address> - enable a hardware breakpoint
        [~process] be <address-address> - enable a memory breakpoint
        [~process] be <address> <size> - enable a memory breakpoint
        """
        token_list = self.split_tokens(arg, 1, 2)
        pid, tid, address, size = self.input_breakpoint(token_list)
        debug = self.debug
        found = False
        if size is None:
            if tid is not None:
                if debug.has_hardware_breakpoint(tid, address):
                    debug.enable_hardware_breakpoint(tid, address)
                    found = True
            if pid is not None:
                if debug.has_code_breakpoint(pid, address):
                    debug.enable_code_breakpoint(pid, address)
                    found = True
        else:
            if debug.has_page_breakpoint(pid, address):
                debug.enable_page_breakpoint(pid, address)
                found = True
        if not found:
            print("Error: breakpoint not found.")

    def do_bd(self, arg):
        """
        [~process] bd <address> - disable a code breakpoint
        [~thread] bd <address> - disable a hardware breakpoint
        [~process] bd <address-address> - disable a memory breakpoint
        [~process] bd <address> <size> - disable a memory breakpoint
        """
        token_list = self.split_tokens(arg, 1, 2)
        pid, tid, address, size = self.input_breakpoint(token_list)
        debug = self.debug
        found = False
        if size is None:
            if tid is not None:
                if debug.has_hardware_breakpoint(tid, address):
                    debug.disable_hardware_breakpoint(tid, address)
                    found = True
            if pid is not None:
                if debug.has_code_breakpoint(pid, address):
                    debug.disable_code_breakpoint(pid, address)
                    found = True
        else:
            if debug.has_page_breakpoint(pid, address):
                debug.disable_page_breakpoint(pid, address)
                found = True
        if not found:
            print("Error: breakpoint not found.")

    def do_bc(self, arg):
        """
        [~process] bc <address> - clear a code breakpoint
        [~thread] bc <address> - clear a hardware breakpoint
        [~process] bc <address-address> - clear a memory breakpoint
        [~process] bc <address> <size> - clear a memory breakpoint
        """
        token_list = self.split_tokens(arg, 1, 2)
        pid, tid, address, size = self.input_breakpoint(token_list)
        debug = self.debug
        found = False
        if size is None:
            if tid is not None:
                if debug.has_hardware_breakpoint(tid, address):
                    debug.dont_watch_variable(tid, address)
                    found = True
            if pid is not None:
                if debug.has_code_breakpoint(pid, address):
                    debug.dont_break_at(pid, address)
                    found = True
        else:
            if debug.has_page_breakpoint(pid, address):
                debug.dont_watch_buffer(pid, address, size)
                found = True
        if not found:
            print("Error: breakpoint not found.")

    def do_disassemble(self, arg):
        """
        [~thread] u [register] - show code disassembly
        [~process] u [address] - show code disassembly
        [~thread] disassemble [register] - show code disassembly
        [~process] disassemble [address] - show code disassembly
        """
        if not arg:
            arg = self.default_disasm_target
        token_list = self.split_tokens(arg, 1, 1)
        pid, tid = self.get_process_and_thread_ids_from_prefix()
        process = self.get_process(pid)
        address = self.input_address(token_list[0], pid, tid)
        try:
            code = process.disassemble(address, 15 * 8)[:8]
        except Exception:
            msg = "can't disassemble address %s"
            msg = msg % HexDump.address(address)
            raise CmdError(msg)
        if code:
            label = process.get_label_at_address(address)
            last_code = code[-1]
            next_address = last_code[0] + last_code[1]
            next_address = HexOutput.integer(next_address)
            self.default_disasm_target = next_address
            print("%s:" % label)
            # #            print(CrashDump.dump_code(code))
            for line in code:
                print(CrashDump.dump_code_line(line, bShowDump=False))

    do_u = do_disassemble

    def do_search(self, arg):
        """
        [~process] s [address-address] <search string>
        [~process] search [address-address] <search string>
        """
        token_list = self.split_tokens(arg, 1, 3)
        pid, tid = self.get_process_and_thread_ids_from_prefix()
        process = self.get_process(pid)
        if len(token_list) == 1:
            pattern = token_list[0]
            minAddr = None
            maxAddr = None
        else:
            pattern = token_list[-1]
            addr, size = self.input_address_range(token_list[:-1], pid, tid)
            minAddr = addr
            maxAddr = addr + size
        iter = process.search_bytes(pattern)
        if process.get_bits() == 32:
            addr_width = 8
        else:
            addr_width = 16
        # TODO: need a prettier output here!
        for addr in iter:
            print(HexDump.address(addr, addr_width))

    do_s = do_search

    def do_searchhex(self, arg):
        """
        [~process] sh [address-address] <hexadecimal pattern>
        [~process] searchhex [address-address] <hexadecimal pattern>
        """
        token_list = self.split_tokens(arg, 1, 3)
        pid, tid = self.get_process_and_thread_ids_from_prefix()
        process = self.get_process(pid)
        if len(token_list) == 1:
            pattern = token_list[0]
            minAddr = None
            maxAddr = None
        else:
            pattern = token_list[-1]
            addr, size = self.input_address_range(token_list[:-1], pid, tid)
            minAddr = addr
            maxAddr = addr + size
        iter = process.search_hexa(pattern)
        if process.get_bits() == 32:
            addr_width = 8
        else:
            addr_width = 16
        for addr, bytes in iter:
            print(
                HexDump.hexblock(bytes, addr, addr_width),
            )

    do_sh = do_searchhex

    # #    def do_strings(self, arg):
    # #        """
    # #        [~process] strings - extract ASCII strings from memory
    # #        """
    # #        if arg:
    # #            raise CmdError("too many arguments")
    # #        pid, tid   = self.get_process_and_thread_ids_from_prefix()
    # #        process    = self.get_process(pid)
    # #        for addr, size, data in process.strings():
    # #            print("%s: %r" % (HexDump.address(addr), data)

    def do_d(self, arg):
        """
        [~thread] d <register> - show memory contents
        [~thread] d <register-register> - show memory contents
        [~thread] d <register> <size> - show memory contents
        [~process] d <address> - show memory contents
        [~process] d <address-address> - show memory contents
        [~process] d <address> <size> - show memory contents
        """
        return self.last_display_command(arg)

    def do_db(self, arg):
        """
        [~thread] db <register> - show memory contents as bytes
        [~thread] db <register-register> - show memory contents as bytes
        [~thread] db <register> <size> - show memory contents as bytes
        [~process] db <address> - show memory contents as bytes
        [~process] db <address-address> - show memory contents as bytes
        [~process] db <address> <size> - show memory contents as bytes
        """
        self.print_memory_display(arg, HexDump.hexblock)
        self.last_display_command = self.do_db

    def do_dw(self, arg):
        """
        [~thread] dw <register> - show memory contents as words
        [~thread] dw <register-register> - show memory contents as words
        [~thread] dw <register> <size> - show memory contents as words
        [~process] dw <address> - show memory contents as words
        [~process] dw <address-address> - show memory contents as words
        [~process] dw <address> <size> - show memory contents as words
        """
        self.print_memory_display(arg, HexDump.hexblock_word)
        self.last_display_command = self.do_dw

    def do_dd(self, arg):
        """
        [~thread] dd <register> - show memory contents as dwords
        [~thread] dd <register-register> - show memory contents as dwords
        [~thread] dd <register> <size> - show memory contents as dwords
        [~process] dd <address> - show memory contents as dwords
        [~process] dd <address-address> - show memory contents as dwords
        [~process] dd <address> <size> - show memory contents as dwords
        """
        self.print_memory_display(arg, HexDump.hexblock_dword)
        self.last_display_command = self.do_dd

    def do_dq(self, arg):
        """
        [~thread] dq <register> - show memory contents as qwords
        [~thread] dq <register-register> - show memory contents as qwords
        [~thread] dq <register> <size> - show memory contents as qwords
        [~process] dq <address> - show memory contents as qwords
        [~process] dq <address-address> - show memory contents as qwords
        [~process] dq <address> <size> - show memory contents as qwords
        """
        self.print_memory_display(arg, HexDump.hexblock_qword)
        self.last_display_command = self.do_dq

    # XXX TODO
    # Change the way the default is used with ds and du

    def do_ds(self, arg):
        """
        [~thread] ds <register> - show memory contents as ANSI string
        [~process] ds <address> - show memory contents as ANSI string
        """
        if not arg:
            arg = self.default_display_target
        token_list = self.split_tokens(arg, 1, 1)
        pid, tid, address, size = self.input_display(token_list, 256)
        process = self.get_process(pid)
        data = process.peek_string(address, False, size)
        if data:
            print(repr(data))
        self.last_display_command = self.do_ds

    def do_du(self, arg):
        """
        [~thread] du <register> - show memory contents as Unicode string
        [~process] du <address> - show memory contents as Unicode string
        """
        if not arg:
            arg = self.default_display_target
        token_list = self.split_tokens(arg, 1, 2)
        pid, tid, address, size = self.input_display(token_list, 256)
        process = self.get_process(pid)
        data = process.peek_string(address, True, size)
        if data:
            print(repr(data))
        self.last_display_command = self.do_du

    def do_register(self, arg):
        """
        [~thread] r - print(the value of all registers
        [~thread] r <register> - print(the value of a register
        [~thread] r <register>=<value> - change the value of a register
        [~thread] register - print(the value of all registers
        [~thread] register <register> - print(the value of a register
        [~thread] register <register>=<value> - change the value of a register
        """
        arg = arg.strip()
        if not arg:
            self.print_current_location()
        else:
            equ = arg.find("=")
            if equ >= 0:
                register = arg[:equ].strip()
                value = arg[equ + 1 :].strip()
                if not value:
                    value = "0"
                self.change_register(register, value)
            else:
                value = self.input_register(arg)
                if value is None:
                    raise CmdError("unknown register: %s" % arg)
                try:
                    label = None
                    thread = self.get_thread_from_prefix()
                    process = thread.get_process()
                    module = process.get_module_at_address(value)
                    if module:
                        label = module.get_label_at_address(value)
                except RuntimeError:
                    label = None
                reg = arg.upper()
                val = HexDump.address(value)
                if label:
                    print("%s: %s (%s)" % (reg, val, label))
                else:
                    print("%s: %s" % (reg, val))

    do_r = do_register

    def do_eb(self, arg):
        """
        [~process] eb <address> <data> - write the data to the specified address
        """
        # TODO
        # data parameter should be optional, use a child Cmd here
        pid = self.get_process_id_from_prefix()
        token_list = self.split_tokens(arg, 2)
        address = self.input_address(token_list[0], pid)
        data = HexInput.hexadecimal(" ".join(token_list[1:]))
        self.write_memory(address, data, pid)

    # XXX TODO
    # add ew, ed and eq here

    def do_find(self, arg):
        """
        [~process] f <string> - find the string in the process memory
        [~process] find <string> - find the string in the process memory
        """
        if not arg:
            raise CmdError("missing parameter: string")
        process = self.get_process_from_prefix()
        self.find_in_memory(arg, process)

    do_f = do_find

    def do_memory(self, arg):
        """
        [~process] m - show the process memory map
        [~process] memory - show the process memory map
        """
        if arg:  # TODO: take min and max addresses
            raise CmdError("too many arguments")
        process = self.get_process_from_prefix()
        try:
            memoryMap = process.get_memory_map()
            mappedFilenames = process.get_mapped_filenames()
            print("")
            print(CrashDump.dump_memory_map(memoryMap, mappedFilenames))
        except WindowsError:
            msg = "can't get memory information for process (%d)"
            raise CmdError(msg % process.get_pid())

    do_m = do_memory

    # ------------------------------------------------------------------------------
    # Event handling

    # TODO
    # * add configurable stop/don't stop behavior on events and exceptions

    # Stop for all events, unless stated otherwise.
    def event(self, event):
        self.print_event(event)
        self.prompt_user()

    # Stop for all exceptions, unless stated otherwise.
    def exception(self, event):
        self.print_exception(event)
        self.prompt_user()

    # Stop for breakpoint exceptions.
    def breakpoint(self, event):
        if hasattr(event, "breakpoint") and event.breakpoint:
            self.print_breakpoint_location(event)
        else:
            self.print_exception(event)
        self.prompt_user()

    # Stop for WOW64 breakpoint exceptions.
    def wow64_breakpoint(self, event):
        self.print_exception(event)
        self.prompt_user()

    # Stop for single step exceptions.
    def single_step(self, event):
        if event.debug.is_tracing(event.get_tid()):
            self.print_breakpoint_location(event)
        else:
            self.print_exception(event)
        self.prompt_user()

    # Don't stop for C++ exceptions.
    def ms_vc_exception(self, event):
        self.print_exception(event)
        event.continueStatus = win32.DBG_CONTINUE

    # Don't stop for process start.
    def create_process(self, event):
        self.print_process_start(event)
        self.print_thread_start(event)
        self.print_module_load(event)

    # Don't stop for process exit.
    def exit_process(self, event):
        self.print_process_end(event)

    # Don't stop for thread creation.
    def create_thread(self, event):
        self.print_thread_start(event)

    # Don't stop for thread exit.
    def exit_thread(self, event):
        self.print_thread_end(event)

    # Don't stop for DLL load.
    def load_dll(self, event):
        self.print_module_load(event)

    # Don't stop for DLL unload.
    def unload_dll(self, event):
        self.print_module_unload(event)

    # Don't stop for debug strings.
    def output_string(self, event):
        self.print_debug_string(event)

    # ------------------------------------------------------------------------------
    # History file

    def load_history(self):
        global readline
        if readline is None:
            try:
                import readline
            except ImportError:
                return
        if self.history_file_full_path is None:
            folder = os.environ.get("USERPROFILE", "")
            if not folder:
                folder = os.environ.get("HOME", "")
            if not folder:
                folder = os.path.split(sys.argv[0])[1]
            if not folder:
                folder = os.path.curdir
            self.history_file_full_path = os.path.join(folder, self.history_file)
        try:
            if os.path.exists(self.history_file_full_path):
                readline.read_history_file(self.history_file_full_path)
        except IOError:
            e = sys.exc_info()[1]
            warnings.warn("Cannot load history file, reason: %s" % str(e))

    def save_history(self):
        if self.history_file_full_path is not None:
            global readline
            if readline is None:
                try:
                    import readline
                except ImportError:
                    return
            try:
                readline.write_history_file(self.history_file_full_path)
            except IOError:
                e = sys.exc_info()[1]
                warnings.warn("Cannot save history file, reason: %s" % str(e))

    # ------------------------------------------------------------------------------
    # Main loop

    # Debugging loop.
    def loop(self):
        self.debuggerExit = False
        debug = self.debug

        # Stop on the initial event, if any.
        if self.lastEvent is not None:
            self.cmdqueue.append("r")
            self.prompt_user()

        # Loop until the debugger is told to quit.
        while not self.debuggerExit:
            try:
                # If for some reason the last event wasn't continued,
                # continue it here. This won't be done more than once
                # for a given Event instance, though.
                try:
                    debug.cont()
                # On error, show the command prompt.
                except Exception:
                    traceback.print_exc()
                    self.prompt_user()

                # While debugees are attached, handle debug events.
                # Some debug events may cause the command prompt to be shown.
                if self.debug.get_debugee_count() > 0:
                    try:
                        # Get the next debug event.
                        debug.wait()

                        # Dispatch the debug event.
                        try:
                            debug.dispatch()

                        # Continue the debug event.
                        finally:
                            debug.cont()

                    # On error, show the command prompt.
                    except Exception:
                        traceback.print_exc()
                        self.prompt_user()

                # While no debugees are attached, show the command prompt.
                else:
                    self.prompt_user()

            # When the user presses Ctrl-C send a debug break to all debugees.
            except KeyboardInterrupt:
                success = False
                try:
                    print("*** User requested debug break")
                    system = debug.system
                    for pid in debug.get_debugee_pids():
                        try:
                            system.get_process(pid).debug_break()
                            success = True
                        except:
                            traceback.print_exc()
                except:
                    traceback.print_exc()
                if not success:
                    raise  # This should never happen!

# === NexusCore/openenv\Lib\site-packages\grpc\_channel.py ===
# Copyright 2016 gRPC authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Invocation-side implementation of gRPC Python."""

import copy
import functools
import logging
import os
import sys
import threading
import time
import types
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

import grpc  # pytype: disable=pyi-error
from grpc import _common  # pytype: disable=pyi-error
from grpc import _compression  # pytype: disable=pyi-error
from grpc import _grpcio_metadata  # pytype: disable=pyi-error
from grpc import _observability  # pytype: disable=pyi-error
from grpc._cython import cygrpc
from grpc._typing import ChannelArgumentType
from grpc._typing import DeserializingFunction
from grpc._typing import IntegratedCallFactory
from grpc._typing import MetadataType
from grpc._typing import NullaryCallbackType
from grpc._typing import ResponseType
from grpc._typing import SerializingFunction
from grpc._typing import UserTag
import grpc.experimental  # pytype: disable=pyi-error

_LOGGER = logging.getLogger(__name__)

_USER_AGENT = "grpc-python/{}".format(_grpcio_metadata.__version__)

_EMPTY_FLAGS = 0

# NOTE(rbellevi): No guarantees are given about the maintenance of this
# environment variable.
_DEFAULT_SINGLE_THREADED_UNARY_STREAM = (
    os.getenv("GRPC_SINGLE_THREADED_UNARY_STREAM") is not None
)

_UNARY_UNARY_INITIAL_DUE = (
    cygrpc.OperationType.send_initial_metadata,
    cygrpc.OperationType.send_message,
    cygrpc.OperationType.send_close_from_client,
    cygrpc.OperationType.receive_initial_metadata,
    cygrpc.OperationType.receive_message,
    cygrpc.OperationType.receive_status_on_client,
)
_UNARY_STREAM_INITIAL_DUE = (
    cygrpc.OperationType.send_initial_metadata,
    cygrpc.OperationType.send_message,
    cygrpc.OperationType.send_close_from_client,
    cygrpc.OperationType.receive_initial_metadata,
    cygrpc.OperationType.receive_status_on_client,
)
_STREAM_UNARY_INITIAL_DUE = (
    cygrpc.OperationType.send_initial_metadata,
    cygrpc.OperationType.receive_initial_metadata,
    cygrpc.OperationType.receive_message,
    cygrpc.OperationType.receive_status_on_client,
)
_STREAM_STREAM_INITIAL_DUE = (
    cygrpc.OperationType.send_initial_metadata,
    cygrpc.OperationType.receive_initial_metadata,
    cygrpc.OperationType.receive_status_on_client,
)

_CHANNEL_SUBSCRIPTION_CALLBACK_ERROR_LOG_MESSAGE = (
    "Exception calling channel subscription callback!"
)

_OK_RENDEZVOUS_REPR_FORMAT = (
    '<{} of RPC that terminated with:\n\tstatus = {}\n\tdetails = "{}"\n>'
)

_NON_OK_RENDEZVOUS_REPR_FORMAT = (
    "<{} of RPC that terminated with:\n"
    "\tstatus = {}\n"
    '\tdetails = "{}"\n'
    '\tdebug_error_string = "{}"\n'
    ">"
)


def _deadline(timeout: Optional[float]) -> Optional[float]:
    return None if timeout is None else time.time() + timeout


def _unknown_code_details(
    unknown_cygrpc_code: Optional[grpc.StatusCode], details: Optional[str]
) -> str:
    return 'Server sent unknown code {} and details "{}"'.format(
        unknown_cygrpc_code, details
    )


class _RPCState(object):
    condition: threading.Condition
    due: Set[cygrpc.OperationType]
    initial_metadata: Optional[MetadataType]
    response: Any
    trailing_metadata: Optional[MetadataType]
    code: Optional[grpc.StatusCode]
    details: Optional[str]
    debug_error_string: Optional[str]
    cancelled: bool
    callbacks: List[NullaryCallbackType]
    fork_epoch: Optional[int]
    rpc_start_time: Optional[float]  # In relative seconds
    rpc_end_time: Optional[float]  # In relative seconds
    method: Optional[str]
    target: Optional[str]

    def __init__(
        self,
        due: Sequence[cygrpc.OperationType],
        initial_metadata: Optional[MetadataType],
        trailing_metadata: Optional[MetadataType],
        code: Optional[grpc.StatusCode],
        details: Optional[str],
    ):
        # `condition` guards all members of _RPCState. `notify_all` is called on
        # `condition` when the state of the RPC has changed.
        self.condition = threading.Condition()

        # The cygrpc.OperationType objects representing events due from the RPC's
        # completion queue. If an operation is in `due`, it is guaranteed that
        # `operate()` has been called on a corresponding operation. But the
        # converse is not true. That is, in the case of failed `operate()`
        # calls, there may briefly be events in `due` that do not correspond to
        # operations submitted to Core.
        self.due = set(due)
        self.initial_metadata = initial_metadata
        self.response = None
        self.trailing_metadata = trailing_metadata
        self.code = code
        self.details = details
        self.debug_error_string = None
        # The following three fields are used for observability.
        # Updates to those fields do not trigger self.condition.
        self.rpc_start_time = None
        self.rpc_end_time = None
        self.method = None
        self.target = None

        # The semantics of grpc.Future.cancel and grpc.Future.cancelled are
        # slightly wonky, so they have to be tracked separately from the rest of the
        # result of the RPC. This field tracks whether cancellation was requested
        # prior to termination of the RPC.
        self.cancelled = False
        self.callbacks = []
        self.fork_epoch = cygrpc.get_fork_epoch()

    def reset_postfork_child(self):
        self.condition = threading.Condition()


def _abort(state: _RPCState, code: grpc.StatusCode, details: str) -> None:
    if state.code is None:
        state.code = code
        state.details = details
        if state.initial_metadata is None:
            state.initial_metadata = ()
        state.trailing_metadata = ()


def _handle_event(
    event: cygrpc.BaseEvent,
    state: _RPCState,
    response_deserializer: Optional[DeserializingFunction],
) -> List[NullaryCallbackType]:
    callbacks = []
    for batch_operation in event.batch_operations:
        operation_type = batch_operation.type()
        state.due.remove(operation_type)
        if operation_type == cygrpc.OperationType.receive_initial_metadata:
            state.initial_metadata = batch_operation.initial_metadata()
        elif operation_type == cygrpc.OperationType.receive_message:
            serialized_response = batch_operation.message()
            if serialized_response is not None:
                response = _common.deserialize(
                    serialized_response, response_deserializer
                )
                if response is None:
                    details = "Exception deserializing response!"
                    _abort(state, grpc.StatusCode.INTERNAL, details)
                else:
                    state.response = response
        elif operation_type == cygrpc.OperationType.receive_status_on_client:
            state.trailing_metadata = batch_operation.trailing_metadata()
            if state.code is None:
                code = _common.CYGRPC_STATUS_CODE_TO_STATUS_CODE.get(
                    batch_operation.code()
                )
                if code is None:
                    state.code = grpc.StatusCode.UNKNOWN
                    state.details = _unknown_code_details(
                        code, batch_operation.details()
                    )
                else:
                    state.code = code
                    state.details = batch_operation.details()
                    state.debug_error_string = batch_operation.error_string()
            state.rpc_end_time = time.perf_counter()
            _observability.maybe_record_rpc_latency(state)
            callbacks.extend(state.callbacks)
            state.callbacks = None
    return callbacks


def _event_handler(
    state: _RPCState, response_deserializer: Optional[DeserializingFunction]
) -> UserTag:
    def handle_event(event):
        with state.condition:
            callbacks = _handle_event(event, state, response_deserializer)
            state.condition.notify_all()
            done = not state.due
        for callback in callbacks:
            try:
                callback()
            except Exception as e:  # pylint: disable=broad-except
                # NOTE(rbellevi): We suppress but log errors here so as not to
                # kill the channel spin thread.
                logging.error(
                    "Exception in callback %s: %s", repr(callback.func), repr(e)
                )
        return done and state.fork_epoch >= cygrpc.get_fork_epoch()

    return handle_event


# TODO(xuanwn): Create a base class for IntegratedCall and SegregatedCall.
# pylint: disable=too-many-statements
def _consume_request_iterator(
    request_iterator: Iterator,
    state: _RPCState,
    call: Union[cygrpc.IntegratedCall, cygrpc.SegregatedCall],
    request_serializer: SerializingFunction,
    event_handler: Optional[UserTag],
) -> None:
    """Consume a request supplied by the user."""

    def consume_request_iterator():  # pylint: disable=too-many-branches
        # Iterate over the request iterator until it is exhausted or an error
        # condition is encountered.
        while True:
            return_from_user_request_generator_invoked = False
            try:
                # The thread may die in user-code. Do not block fork for this.
                cygrpc.enter_user_request_generator()
                request = next(request_iterator)
            except StopIteration:
                break
            except Exception:  # pylint: disable=broad-except
                cygrpc.return_from_user_request_generator()
                return_from_user_request_generator_invoked = True
                code = grpc.StatusCode.UNKNOWN
                details = "Exception iterating requests!"
                _LOGGER.exception(details)
                call.cancel(
                    _common.STATUS_CODE_TO_CYGRPC_STATUS_CODE[code], details
                )
                _abort(state, code, details)
                return
            finally:
                if not return_from_user_request_generator_invoked:
                    cygrpc.return_from_user_request_generator()
            serialized_request = _common.serialize(request, request_serializer)
            with state.condition:
                if state.code is None and not state.cancelled:
                    if serialized_request is None:
                        code = grpc.StatusCode.INTERNAL
                        details = "Exception serializing request!"
                        call.cancel(
                            _common.STATUS_CODE_TO_CYGRPC_STATUS_CODE[code],
                            details,
                        )
                        _abort(state, code, details)
                        return
                    else:
                        state.due.add(cygrpc.OperationType.send_message)
                        operations = (
                            cygrpc.SendMessageOperation(
                                serialized_request, _EMPTY_FLAGS
                            ),
                        )
                        operating = call.operate(operations, event_handler)
                        if not operating:
                            state.due.remove(cygrpc.OperationType.send_message)
                            return

                        def _done():
                            return (
                                state.code is not None
                                or cygrpc.OperationType.send_message
                                not in state.due
                            )

                        _common.wait(
                            state.condition.wait,
                            _done,
                            spin_cb=functools.partial(
                                cygrpc.block_if_fork_in_progress, state
                            ),
                        )
                        if state.code is not None:
                            return
                else:
                    return
        with state.condition:
            if state.code is None:
                state.due.add(cygrpc.OperationType.send_close_from_client)
                operations = (
                    cygrpc.SendCloseFromClientOperation(_EMPTY_FLAGS),
                )
                operating = call.operate(operations, event_handler)
                if not operating:
                    state.due.remove(
                        cygrpc.OperationType.send_close_from_client
                    )

    consumption_thread = cygrpc.ForkManagedThread(
        target=consume_request_iterator
    )
    consumption_thread.setDaemon(True)
    consumption_thread.start()


def _rpc_state_string(class_name: str, rpc_state: _RPCState) -> str:
    """Calculates error string for RPC."""
    with rpc_state.condition:
        if rpc_state.code is None:
            return "<{} object>".format(class_name)
        elif rpc_state.code is grpc.StatusCode.OK:
            return _OK_RENDEZVOUS_REPR_FORMAT.format(
                class_name, rpc_state.code, rpc_state.details
            )
        else:
            return _NON_OK_RENDEZVOUS_REPR_FORMAT.format(
                class_name,
                rpc_state.code,
                rpc_state.details,
                rpc_state.debug_error_string,
            )


class _InactiveRpcError(grpc.RpcError, grpc.Call, grpc.Future):
    """An RPC error not tied to the execution of a particular RPC.

    The RPC represented by the state object must not be in-progress or
    cancelled.

    Attributes:
      _state: An instance of _RPCState.
    """

    _state: _RPCState

    def __init__(self, state: _RPCState):
        with state.condition:
            self._state = _RPCState(
                (),
                copy.deepcopy(state.initial_metadata),
                copy.deepcopy(state.trailing_metadata),
                state.code,
                copy.deepcopy(state.details),
            )
            self._state.response = copy.copy(state.response)
            self._state.debug_error_string = copy.copy(state.debug_error_string)

    def initial_metadata(self) -> Optional[MetadataType]:
        return self._state.initial_metadata

    def trailing_metadata(self) -> Optional[MetadataType]:
        return self._state.trailing_metadata

    def code(self) -> Optional[grpc.StatusCode]:
        return self._state.code

    def details(self) -> Optional[str]:
        return _common.decode(self._state.details)

    def debug_error_string(self) -> Optional[str]:
        return _common.decode(self._state.debug_error_string)

    def _repr(self) -> str:
        return _rpc_state_string(self.__class__.__name__, self._state)

    def __repr__(self) -> str:
        return self._repr()

    def __str__(self) -> str:
        return self._repr()

    def cancel(self) -> bool:
        """See grpc.Future.cancel."""
        return False

    def cancelled(self) -> bool:
        """See grpc.Future.cancelled."""
        return False

    def running(self) -> bool:
        """See grpc.Future.running."""
        return False

    def done(self) -> bool:
        """See grpc.Future.done."""
        return True

    def result(
        self, timeout: Optional[float] = None
    ) -> Any:  # pylint: disable=unused-argument
        """See grpc.Future.result."""
        raise self

    def exception(
        self, timeout: Optional[float] = None  # pylint: disable=unused-argument
    ) -> Optional[Exception]:
        """See grpc.Future.exception."""
        return self

    def traceback(
        self, timeout: Optional[float] = None  # pylint: disable=unused-argument
    ) -> Optional[types.TracebackType]:
        """See grpc.Future.traceback."""
        try:
            raise self
        except grpc.RpcError:
            return sys.exc_info()[2]

    def add_done_callback(
        self,
        fn: Callable[[grpc.Future], None],
        timeout: Optional[float] = None,  # pylint: disable=unused-argument
    ) -> None:
        """See grpc.Future.add_done_callback."""
        fn(self)


class _Rendezvous(grpc.RpcError, grpc.RpcContext):
    """An RPC iterator.

    Attributes:
      _state: An instance of _RPCState.
      _call: An instance of SegregatedCall or IntegratedCall.
        In either case, the _call object is expected to have operate, cancel,
        and next_event methods.
      _response_deserializer: A callable taking bytes and return a Python
        object.
      _deadline: A float representing the deadline of the RPC in seconds. Or
        possibly None, to represent an RPC with no deadline at all.
    """

    _state: _RPCState
    _call: Union[cygrpc.SegregatedCall, cygrpc.IntegratedCall]
    _response_deserializer: Optional[DeserializingFunction]
    _deadline: Optional[float]

    def __init__(
        self,
        state: _RPCState,
        call: Union[cygrpc.SegregatedCall, cygrpc.IntegratedCall],
        response_deserializer: Optional[DeserializingFunction],
        deadline: Optional[float],
    ):
        super(_Rendezvous, self).__init__()
        self._state = state
        self._call = call
        self._response_deserializer = response_deserializer
        self._deadline = deadline

    def is_active(self) -> bool:
        """See grpc.RpcContext.is_active"""
        with self._state.condition:
            return self._state.code is None

    def time_remaining(self) -> Optional[float]:
        """See grpc.RpcContext.time_remaining"""
        with self._state.condition:
            if self._deadline is None:
                return None
            else:
                return max(self._deadline - time.time(), 0)

    def cancel(self) -> bool:
        """See grpc.RpcContext.cancel"""
        with self._state.condition:
            if self._state.code is None:
                code = grpc.StatusCode.CANCELLED
                details = "Locally cancelled by application!"
                self._call.cancel(
                    _common.STATUS_CODE_TO_CYGRPC_STATUS_CODE[code], details
                )
                self._state.cancelled = True
                _abort(self._state, code, details)
                self._state.condition.notify_all()
                return True
            else:
                return False

    def add_callback(self, callback: NullaryCallbackType) -> bool:
        """See grpc.RpcContext.add_callback"""
        with self._state.condition:
            if self._state.callbacks is None:
                return False
            else:
                self._state.callbacks.append(callback)
                return True

    def __iter__(self):
        return self

    def next(self):
        return self._next()

    def __next__(self):
        return self._next()

    def _next(self):
        raise NotImplementedError()

    def debug_error_string(self) -> Optional[str]:
        raise NotImplementedError()

    def _repr(self) -> str:
        return _rpc_state_string(self.__class__.__name__, self._state)

    def __repr__(self) -> str:
        return self._repr()

    def __str__(self) -> str:
        return self._repr()

    def __del__(self) -> None:
        with self._state.condition:
            if self._state.code is None:
                self._state.code = grpc.StatusCode.CANCELLED
                self._state.details = "Cancelled upon garbage collection!"
                self._state.cancelled = True
                self._call.cancel(
                    _common.STATUS_CODE_TO_CYGRPC_STATUS_CODE[self._state.code],
                    self._state.details,
                )
                self._state.condition.notify_all()


class _SingleThreadedRendezvous(
    _Rendezvous, grpc.Call, grpc.Future
):  # pylint: disable=too-many-ancestors
    """An RPC iterator operating entirely on a single thread.

    The __next__ method of _SingleThreadedRendezvous does not depend on the
    existence of any other thread, including the "channel spin thread".
    However, this means that its interface is entirely synchronous. So this
    class cannot completely fulfill the grpc.Future interface. The result,
    exception, and traceback methods will never block and will instead raise
    an exception if calling the method would result in blocking.

    This means that these methods are safe to call from add_done_callback
    handlers.
    """

    _state: _RPCState

    def _is_complete(self) -> bool:
        return self._state.code is not None

    def cancelled(self) -> bool:
        with self._state.condition:
            return self._state.cancelled

    def running(self) -> bool:
        with self._state.condition:
            return self._state.code is None

    def done(self) -> bool:
        with self._state.condition:
            return self._state.code is not None

    def result(self, timeout: Optional[float] = None) -> Any:
        """Returns the result of the computation or raises its exception.

        This method will never block. Instead, it will raise an exception
        if calling this method would otherwise result in blocking.

        Since this method will never block, any `timeout` argument passed will
        be ignored.
        """
        del timeout
        with self._state.condition:
            if not self._is_complete():
                raise grpc.experimental.UsageError(
                    "_SingleThreadedRendezvous only supports result() when the"
                    " RPC is complete."
                )
            if self._state.code is grpc.StatusCode.OK:
                return self._state.response
            elif self._state.cancelled:
                raise grpc.FutureCancelledError()
            else:
                raise self

    def exception(self, timeout: Optional[float] = None) -> Optional[Exception]:
        """Return the exception raised by the computation.

        This method will never block. Instead, it will raise an exception
        if calling this method would otherwise result in blocking.

        Since this method will never block, any `timeout` argument passed will
        be ignored.
        """
        del timeout
        with self._state.condition:
            if not self._is_complete():
                raise grpc.experimental.UsageError(
                    "_SingleThreadedRendezvous only supports exception() when"
                    " the RPC is complete."
                )
            if self._state.code is grpc.StatusCode.OK:
                return None
            elif self._state.cancelled:
                raise grpc.FutureCancelledError()
            else:
                return self

    def traceback(
        self, timeout: Optional[float] = None
    ) -> Optional[types.TracebackType]:
        """Access the traceback of the exception raised by the computation.

        This method will never block. Instead, it will raise an exception
        if calling this method would otherwise result in blocking.

        Since this method will never block, any `timeout` argument passed will
        be ignored.
        """
        del timeout
        with self._state.condition:
            if not self._is_complete():
                raise grpc.experimental.UsageError(
                    "_SingleThreadedRendezvous only supports traceback() when"
                    " the RPC is complete."
                )
            if self._state.code is grpc.StatusCode.OK:
                return None
            elif self._state.cancelled:
                raise grpc.FutureCancelledError()
            else:
                try:
                    raise self
                except grpc.RpcError:
                    return sys.exc_info()[2]

    def add_done_callback(self, fn: Callable[[grpc.Future], None]) -> None:
        with self._state.condition:
            if self._state.code is None:
                self._state.callbacks.append(functools.partial(fn, self))
                return

        fn(self)

    def initial_metadata(self) -> Optional[MetadataType]:
        """See grpc.Call.initial_metadata"""
        with self._state.condition:
            # NOTE(gnossen): Based on our initial call batch, we are guaranteed
            # to receive initial metadata before any messages.
            while self._state.initial_metadata is None:
                self._consume_next_event()
            return self._state.initial_metadata

    def trailing_metadata(self) -> Optional[MetadataType]:
        """See grpc.Call.trailing_metadata"""
        with self._state.condition:
            if self._state.trailing_metadata is None:
                raise grpc.experimental.UsageError(
                    "Cannot get trailing metadata until RPC is completed."
                )
            return self._state.trailing_metadata

    def code(self) -> Optional[grpc.StatusCode]:
        """See grpc.Call.code"""
        with self._state.condition:
            if self._state.code is None:
                raise grpc.experimental.UsageError(
                    "Cannot get code until RPC is completed."
                )
            return self._state.code

    def details(self) -> Optional[str]:
        """See grpc.Call.details"""
        with self._state.condition:
            if self._state.details is None:
                raise grpc.experimental.UsageError(
                    "Cannot get details until RPC is completed."
                )
            return _common.decode(self._state.details)

    def _consume_next_event(self) -> Optional[cygrpc.BaseEvent]:
        event = self._call.next_event()
        with self._state.condition:
            callbacks = _handle_event(
                event, self._state, self._response_deserializer
            )
            for callback in callbacks:
                # NOTE(gnossen): We intentionally allow exceptions to bubble up
                # to the user when running on a single thread.
                callback()
        return event

    def _next_response(self) -> Any:
        while True:
            self._consume_next_event()
            with self._state.condition:
                if self._state.response is not None:
                    response = self._state.response
                    self._state.response = None
                    return response
                elif (
                    cygrpc.OperationType.receive_message not in self._state.due
                ):
                    if self._state.code is grpc.StatusCode.OK:
                        raise StopIteration()
                    elif self._state.code is not None:
                        raise self

    def _next(self) -> Any:
        with self._state.condition:
            if self._state.code is None:
                # We tentatively add the operation as expected and remove
                # it if the enqueue operation fails. This allows us to guarantee that
                # if an event has been submitted to the core completion queue,
                # it is in `due`. If we waited until after a successful
                # enqueue operation then a signal could interrupt this
                # thread between the enqueue operation and the addition of the
                # operation to `due`. This would cause an exception on the
                # channel spin thread when the operation completes and no
                # corresponding operation would be present in state.due.
                # Note that, since `condition` is held through this block, there is
                # no data race on `due`.
                self._state.due.add(cygrpc.OperationType.receive_message)
                operating = self._call.operate(
                    (cygrpc.ReceiveMessageOperation(_EMPTY_FLAGS),), None
                )
                if not operating:
                    self._state.due.remove(cygrpc.OperationType.receive_message)
            elif self._state.code is grpc.StatusCode.OK:
                raise StopIteration()
            else:
                raise self
        return self._next_response()

    def debug_error_string(self) -> Optional[str]:
        with self._state.condition:
            if self._state.debug_error_string is None:
                raise grpc.experimental.UsageError(
                    "Cannot get debug error string until RPC is completed."
                )
            return _common.decode(self._state.debug_error_string)


class _MultiThreadedRendezvous(
    _Rendezvous, grpc.Call, grpc.Future
):  # pylint: disable=too-many-ancestors
    """An RPC iterator that depends on a channel spin thread.

    This iterator relies upon a per-channel thread running in the background,
    dequeueing events from the completion queue, and notifying threads waiting
    on the threading.Condition object in the _RPCState object.

    This extra thread allows _MultiThreadedRendezvous to fulfill the grpc.Future interface
    and to mediate a bidirection streaming RPC.
    """

    _state: _RPCState

    def initial_metadata(self) -> Optional[MetadataType]:
        """See grpc.Call.initial_metadata"""
        with self._state.condition:

            def _done():
                return self._state.initial_metadata is not None

            _common.wait(self._state.condition.wait, _done)
            return self._state.initial_metadata

    def trailing_metadata(self) -> Optional[MetadataType]:
        """See grpc.Call.trailing_metadata"""
        with self._state.condition:

            def _done():
                return self._state.trailing_metadata is not None

            _common.wait(self._state.condition.wait, _done)
            return self._state.trailing_metadata

    def code(self) -> Optional[grpc.StatusCode]:
        """See grpc.Call.code"""
        with self._state.condition:

            def _done():
                return self._state.code is not None

            _common.wait(self._state.condition.wait, _done)
            return self._state.code

    def details(self) -> Optional[str]:
        """See grpc.Call.details"""
        with self._state.condition:

            def _done():
                return self._state.details is not None

            _common.wait(self._state.condition.wait, _done)
            return _common.decode(self._state.details)

    def debug_error_string(self) -> Optional[str]:
        with self._state.condition:

            def _done():
                return self._state.debug_error_string is not None

            _common.wait(self._state.condition.wait, _done)
            return _common.decode(self._state.debug_error_string)

    def cancelled(self) -> bool:
        with self._state.condition:
            return self._state.cancelled

    def running(self) -> bool:
        with self._state.condition:
            return self._state.code is None

    def done(self) -> bool:
        with self._state.condition:
            return self._state.code is not None

    def _is_complete(self) -> bool:
        return self._state.code is not None

    def result(self, timeout: Optional[float] = None) -> Any:
        """Returns the result of the computation or raises its exception.

        See grpc.Future.result for the full API contract.
        """
        with self._state.condition:
            timed_out = _common.wait(
                self._state.condition.wait, self._is_complete, timeout=timeout
            )
            if timed_out:
                raise grpc.FutureTimeoutError()
            else:
                if self._state.code is grpc.StatusCode.OK:
                    return self._state.response
                elif self._state.cancelled:
                    raise grpc.FutureCancelledError()
                else:
                    raise self

    def exception(self, timeout: Optional[float] = None) -> Optional[Exception]:
        """Return the exception raised by the computation.

        See grpc.Future.exception for the full API contract.
        """
        with self._state.condition:
            timed_out = _common.wait(
                self._state.condition.wait, self._is_complete, timeout=timeout
            )
            if timed_out:
                raise grpc.FutureTimeoutError()
            else:
                if self._state.code is grpc.StatusCode.OK:
                    return None
                elif self._state.cancelled:
                    raise grpc.FutureCancelledError()
                else:
                    return self

    def traceback(
        self, timeout: Optional[float] = None
    ) -> Optional[types.TracebackType]:
        """Access the traceback of the exception raised by the computation.

        See grpc.future.traceback for the full API contract.
        """
        with self._state.condition:
            timed_out = _common.wait(
                self._state.condition.wait, self._is_complete, timeout=timeout
            )
            if timed_out:
                raise grpc.FutureTimeoutError()
            else:
                if self._state.code is grpc.StatusCode.OK:
                    return None
                elif self._state.cancelled:
                    raise grpc.FutureCancelledError()
                else:
                    try:
                        raise self
                    except grpc.RpcError:
                        return sys.exc_info()[2]

    def add_done_callback(self, fn: Callable[[grpc.Future], None]) -> None:
        with self._state.condition:
            if self._state.code is None:
                self._state.callbacks.append(functools.partial(fn, self))
                return

        fn(self)

    def _next(self) -> Any:
        with self._state.condition:
            if self._state.code is None:
                event_handler = _event_handler(
                    self._state, self._response_deserializer
                )
                self._state.due.add(cygrpc.OperationType.receive_message)
                operating = self._call.operate(
                    (cygrpc.ReceiveMessageOperation(_EMPTY_FLAGS),),
                    event_handler,
                )
                if not operating:
                    self._state.due.remove(cygrpc.OperationType.receive_message)
            elif self._state.code is grpc.StatusCode.OK:
                raise StopIteration()
            else:
                raise self

            def _response_ready():
                return self._state.response is not None or (
                    cygrpc.OperationType.receive_message not in self._state.due
                    and self._state.code is not None
                )

            _common.wait(self._state.condition.wait, _response_ready)
            if self._state.response is not None:
                response = self._state.response
                self._state.response = None
                return response
            elif cygrpc.OperationType.receive_message not in self._state.due:
                if self._state.code is grpc.StatusCode.OK:
                    raise StopIteration()
                elif self._state.code is not None:
                    raise self


def _start_unary_request(
    request: Any,
    timeout: Optional[float],
    request_serializer: SerializingFunction,
) -> Tuple[Optional[float], Optional[bytes], Optional[grpc.RpcError]]:
    deadline = _deadline(timeout)
    serialized_request = _common.serialize(request, request_serializer)
    if serialized_request is None:
        state = _RPCState(
            (),
            (),
            (),
            grpc.StatusCode.INTERNAL,
            "Exception serializing request!",
        )
        error = _InactiveRpcError(state)
        return deadline, None, error
    else:
        return deadline, serialized_request, None


def _end_unary_response_blocking(
    state: _RPCState,
    call: cygrpc.SegregatedCall,
    with_call: bool,
    deadline: Optional[float],
) -> Union[ResponseType, Tuple[ResponseType, grpc.Call]]:
    if state.code is grpc.StatusCode.OK:
        if with_call:
            rendezvous = _MultiThreadedRendezvous(state, call, None, deadline)
            return state.response, rendezvous
        else:
            return state.response
    else:
        raise _InactiveRpcError(state)  # pytype: disable=not-instantiable


def _stream_unary_invocation_operations(
    metadata: Optional[MetadataType], initial_metadata_flags: int
) -> Sequence[Sequence[cygrpc.Operation]]:
    return (
        (
            cygrpc.SendInitialMetadataOperation(
                metadata, initial_metadata_flags
            ),
            cygrpc.ReceiveMessageOperation(_EMPTY_FLAGS),
            cygrpc.ReceiveStatusOnClientOperation(_EMPTY_FLAGS),
        ),
        (cygrpc.ReceiveInitialMetadataOperation(_EMPTY_FLAGS),),
    )


def _stream_unary_invocation_operations_and_tags(
    metadata: Optional[MetadataType], initial_metadata_flags: int
) -> Sequence[Tuple[Sequence[cygrpc.Operation], Optional[UserTag]]]:
    return tuple(
        (
            operations,
            None,
        )
        for operations in _stream_unary_invocation_operations(
            metadata, initial_metadata_flags
        )
    )


def _determine_deadline(user_deadline: Optional[float]) -> Optional[float]:
    parent_deadline = cygrpc.get_deadline_from_context()
    if parent_deadline is None and user_deadline is None:
        return None
    elif parent_deadline is not None and user_deadline is None:
        return parent_deadline
    elif user_deadline is not None and parent_deadline is None:
        return user_deadline
    else:
        return min(parent_deadline, user_deadline)


class _UnaryUnaryMultiCallable(grpc.UnaryUnaryMultiCallable):
    _channel: cygrpc.Channel
    _managed_call: IntegratedCallFactory
    _method: bytes
    _target: bytes
    _request_serializer: Optional[SerializingFunction]
    _response_deserializer: Optional[DeserializingFunction]
    _context: Any
    _registered_call_handle: Optional[int]

    __slots__ = [
        "_channel",
        "_managed_call",
        "_method",
        "_target",
        "_request_serializer",
        "_response_deserializer",
        "_context",
    ]

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        channel: cygrpc.Channel,
        managed_call: IntegratedCallFactory,
        method: bytes,
        target: bytes,
        request_serializer: Optional[SerializingFunction],
        response_deserializer: Optional[DeserializingFunction],
        _registered_call_handle: Optional[int],
    ):
        self._channel = channel
        self._managed_call = managed_call
        self._method = method
        self._target = target
        self._request_serializer = request_serializer
        self._response_deserializer = response_deserializer
        self._context = cygrpc.build_census_context()
        self._registered_call_handle = _registered_call_handle

    def _prepare(
        self,
        request: Any,
        timeout: Optional[float],
        metadata: Optional[MetadataType],
        wait_for_ready: Optional[bool],
        compression: Optional[grpc.Compression],
    ) -> Tuple[
        Optional[_RPCState],
        Optional[Sequence[cygrpc.Operation]],
        Optional[float],
        Optional[grpc.RpcError],
    ]:
        deadline, serialized_request, rendezvous = _start_unary_request(
            request, timeout, self._request_serializer
        )
        initial_metadata_flags = _InitialMetadataFlags().with_wait_for_ready(
            wait_for_ready
        )
        augmented_metadata = _compression.augment_metadata(
            metadata, compression
        )
        if serialized_request is None:
            return None, None, None, rendezvous
        else:
            state = _RPCState(_UNARY_UNARY_INITIAL_DUE, None, None, None, None)
            operations = (
                cygrpc.SendInitialMetadataOperation(
                    augmented_metadata, initial_metadata_flags
                ),
                cygrpc.SendMessageOperation(serialized_request, _EMPTY_FLAGS),
                cygrpc.SendCloseFromClientOperation(_EMPTY_FLAGS),
                cygrpc.ReceiveInitialMetadataOperation(_EMPTY_FLAGS),
                cygrpc.ReceiveMessageOperation(_EMPTY_FLAGS),
                cygrpc.ReceiveStatusOnClientOperation(_EMPTY_FLAGS),
            )
            return state, operations, deadline, None

    def _blocking(
        self,
        request: Any,
        timeout: Optional[float] = None,
        metadata: Optional[MetadataType] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None,
    ) -> Tuple[_RPCState, cygrpc.SegregatedCall]:
        state, operations, deadline, rendezvous = self._prepare(
            request, timeout, metadata, wait_for_ready, compression
        )
        if state is None:
            raise rendezvous  # pylint: disable-msg=raising-bad-type
        else:
            state.rpc_start_time = time.perf_counter()
            state.method = _common.decode(self._method)
            state.target = _common.decode(self._target)
            call = self._channel.segregated_call(
                cygrpc.PropagationConstants.GRPC_PROPAGATE_DEFAULTS,
                self._method,
                None,
                _determine_deadline(deadline),
                metadata,
                None if credentials is None else credentials._credentials,
                (
                    (
                        operations,
                        None,
                    ),
                ),
                self._context,
                self._registered_call_handle,
            )
            event = call.next_event()
            _handle_event(event, state, self._response_deserializer)
            return state, call

    def __call__(
        self,
        request: Any,
        timeout: Optional[float] = None,
        metadata: Optional[MetadataType] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None,
    ) -> Any:
        (
            state,
            call,
        ) = self._blocking(
            request, timeout, metadata, credentials, wait_for_ready, compression
        )
        return _end_unary_response_blocking(state, call, False, None)

    def with_call(
        self,
        request: Any,
        timeout: Optional[float] = None,
        metadata: Optional[MetadataType] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None,
    ) -> Tuple[Any, grpc.Call]:
        (
            state,
            call,
        ) = self._blocking(
            request, timeout, metadata, credentials, wait_for_ready, compression
        )
        return _end_unary_response_blocking(state, call, True, None)

    def future(
        self,
        request: Any,
        timeout: Optional[float] = None,
        metadata: Optional[MetadataType] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None,
    ) -> _MultiThreadedRendezvous:
        state, operations, deadline, rendezvous = self._prepare(
            request, timeout, metadata, wait_for_ready, compression
        )
        if state is None:
            raise rendezvous  # pylint: disable-msg=raising-bad-type
        else:
            event_handler = _event_handler(state, self._response_deserializer)
            state.rpc_start_time = time.perf_counter()
            state.method = _common.decode(self._method)
            state.target = _common.decode(self._target)
            call = self._managed_call(
                cygrpc.PropagationConstants.GRPC_PROPAGATE_DEFAULTS,
                self._method,
                None,
                deadline,
                metadata,
                None if credentials is None else credentials._credentials,
                (operations,),
                event_handler,
                self._context,
                self._registered_call_handle,
            )
            return _MultiThreadedRendezvous(
                state, call, self._response_deserializer, deadline
            )


class _SingleThreadedUnaryStreamMultiCallable(grpc.UnaryStreamMultiCallable):
    _channel: cygrpc.Channel
    _method: bytes
    _target: bytes
    _request_serializer: Optional[SerializingFunction]
    _response_deserializer: Optional[DeserializingFunction]
    _context: Any
    _registered_call_handle: Optional[int]

    __slots__ = [
        "_channel",
        "_method",
        "_target",
        "_request_serializer",
        "_response_deserializer",
        "_context",
    ]

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        channel: cygrpc.Channel,
        method: bytes,
        target: bytes,
        request_serializer: SerializingFunction,
        response_deserializer: DeserializingFunction,
        _registered_call_handle: Optional[int],
    ):
        self._channel = channel
        self._method = method
        self._target = target
        self._request_serializer = request_serializer
        self._response_deserializer = response_deserializer
        self._context = cygrpc.build_census_context()
        self._registered_call_handle = _registered_call_handle

    def __call__(  # pylint: disable=too-many-locals
        self,
        request: Any,
        timeout: Optional[float] = None,
        metadata: Optional[MetadataType] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None,
    ) -> _SingleThreadedRendezvous:
        deadline = _deadline(timeout)
        serialized_request = _common.serialize(
            request, self._request_serializer
        )
        if serialized_request is None:
            state = _RPCState(
                (),
                (),
                (),
                grpc.StatusCode.INTERNAL,
                "Exception serializing request!",
            )
            raise _InactiveRpcError(state)

        state = _RPCState(_UNARY_STREAM_INITIAL_DUE, None, None, None, None)
        call_credentials = (
            None if credentials is None else credentials._credentials
        )
        initial_metadata_flags = _InitialMetadataFlags().with_wait_for_ready(
            wait_for_ready
        )
        augmented_metadata = _compression.augment_metadata(
            metadata, compression
        )
        operations = (
            (
                cygrpc.SendInitialMetadataOperation(
                    augmented_metadata, initial_metadata_flags
                ),
                cygrpc.SendMessageOperation(serialized_request, _EMPTY_FLAGS),
                cygrpc.SendCloseFromClientOperation(_EMPTY_FLAGS),
            ),
            (cygrpc.ReceiveStatusOnClientOperation(_EMPTY_FLAGS),),
            (cygrpc.ReceiveInitialMetadataOperation(_EMPTY_FLAGS),),
        )
        operations_and_tags = tuple((ops, None) for ops in operations)
        state.rpc_start_time = time.perf_counter()
        state.method = _common.decode(self._method)
        state.target = _common.decode(self._target)
        call = self._channel.segregated_call(
            cygrpc.PropagationConstants.GRPC_PROPAGATE_DEFAULTS,
            self._method,
            None,
            _determine_deadline(deadline),
            metadata,
            call_credentials,
            operations_and_tags,
            self._context,
            self._registered_call_handle,
        )
        return _SingleThreadedRendezvous(
            state, call, self._response_deserializer, deadline
        )


class _UnaryStreamMultiCallable(grpc.UnaryStreamMultiCallable):
    _channel: cygrpc.Channel
    _managed_call: IntegratedCallFactory
    _method: bytes
    _target: bytes
    _request_serializer: Optional[SerializingFunction]
    _response_deserializer: Optional[DeserializingFunction]
    _context: Any
    _registered_call_handle: Optional[int]

    __slots__ = [
        "_channel",
        "_managed_call",
        "_method",
        "_target",
        "_request_serializer",
        "_response_deserializer",
        "_context",
    ]

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        channel: cygrpc.Channel,
        managed_call: IntegratedCallFactory,
        method: bytes,
        target: bytes,
        request_serializer: SerializingFunction,
        response_deserializer: DeserializingFunction,
        _registered_call_handle: Optional[int],
    ):
        self._channel = channel
        self._managed_call = managed_call
        self._method = method
        self._target = target
        self._request_serializer = request_serializer
        self._response_deserializer = response_deserializer
        self._context = cygrpc.build_census_context()
        self._registered_call_handle = _registered_call_handle

    def __call__(  # pylint: disable=too-many-locals
        self,
        request: Any,
        timeout: Optional[float] = None,
        metadata: Optional[MetadataType] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None,
    ) -> _MultiThreadedRendezvous:
        deadline, serialized_request, rendezvous = _start_unary_request(
            request, timeout, self._request_serializer
        )
        initial_metadata_flags = _InitialMetadataFlags().with_wait_for_ready(
            wait_for_ready
        )
        if serialized_request is None:
            raise rendezvous  # pylint: disable-msg=raising-bad-type
        else:
            augmented_metadata = _compression.augment_metadata(
                metadata, compression
            )
            state = _RPCState(_UNARY_STREAM_INITIAL_DUE, None, None, None, None)
            operations = (
                (
                    cygrpc.SendInitialMetadataOperation(
                        augmented_metadata, initial_metadata_flags
                    ),
                    cygrpc.SendMessageOperation(
                        serialized_request, _EMPTY_FLAGS
                    ),
                    cygrpc.SendCloseFromClientOperation(_EMPTY_FLAGS),
                    cygrpc.ReceiveStatusOnClientOperation(_EMPTY_FLAGS),
                ),
                (cygrpc.ReceiveInitialMetadataOperation(_EMPTY_FLAGS),),
            )
            state.rpc_start_time = time.perf_counter()
            state.method = _common.decode(self._method)
            state.target = _common.decode(self._target)
            call = self._managed_call(
                cygrpc.PropagationConstants.GRPC_PROPAGATE_DEFAULTS,
                self._method,
                None,
                _determine_deadline(deadline),
                metadata,
                None if credentials is None else credentials._credentials,
                operations,
                _event_handler(state, self._response_deserializer),
                self._context,
                self._registered_call_handle,
            )
            return _MultiThreadedRendezvous(
                state, call, self._response_deserializer, deadline
            )


class _StreamUnaryMultiCallable(grpc.StreamUnaryMultiCallable):
    _channel: cygrpc.Channel
    _managed_call: IntegratedCallFactory
    _method: bytes
    _target: bytes
    _request_serializer: Optional[SerializingFunction]
    _response_deserializer: Optional[DeserializingFunction]
    _context: Any
    _registered_call_handle: Optional[int]

    __slots__ = [
        "_channel",
        "_managed_call",
        "_method",
        "_target",
        "_request_serializer",
        "_response_deserializer",
        "_context",
    ]

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        channel: cygrpc.Channel,
        managed_call: IntegratedCallFactory,
        method: bytes,
        target: bytes,
        request_serializer: Optional[SerializingFunction],
        response_deserializer: Optional[DeserializingFunction],
        _registered_call_handle: Optional[int],
    ):
        self._channel = channel
        self._managed_call = managed_call
        self._method = method
        self._target = target
        self._request_serializer = request_serializer
        self._response_deserializer = response_deserializer
        self._context = cygrpc.build_census_context()
        self._registered_call_handle = _registered_call_handle

    def _blocking(
        self,
        request_iterator: Iterator,
        timeout: Optional[float],
        metadata: Optional[MetadataType],
        credentials: Optional[grpc.CallCredentials],
        wait_for_ready: Optional[bool],
        compression: Optional[grpc.Compression],
    ) -> Tuple[_RPCState, cygrpc.SegregatedCall]:
        deadline = _deadline(timeout)
        state = _RPCState(_STREAM_UNARY_INITIAL_DUE, None, None, None, None)
        initial_metadata_flags = _InitialMetadataFlags().with_wait_for_ready(
            wait_for_ready
        )
        augmented_metadata = _compression.augment_metadata(
            metadata, compression
        )
        state.rpc_start_time = time.perf_counter()
        state.method = _common.decode(self._method)
        state.target = _common.decode(self._target)
        call = self._channel.segregated_call(
            cygrpc.PropagationConstants.GRPC_PROPAGATE_DEFAULTS,
            self._method,
            None,
            _determine_deadline(deadline),
            augmented_metadata,
            None if credentials is None else credentials._credentials,
            _stream_unary_invocation_operations_and_tags(
                augmented_metadata, initial_metadata_flags
            ),
            self._context,
            self._registered_call_handle,
        )
        _consume_request_iterator(
            request_iterator, state, call, self._request_serializer, None
        )
        while True:
            event = call.next_event()
            with state.condition:
                _handle_event(event, state, self._response_deserializer)
                state.condition.notify_all()
                if not state.due:
                    break
        return state, call

    def __call__(
        self,
        request_iterator: Iterator,
        timeout: Optional[float] = None,
        metadata: Optional[MetadataType] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None,
    ) -> Any:
        (
            state,
            call,
        ) = self._blocking(
            request_iterator,
            timeout,
            metadata,
            credentials,
            wait_for_ready,
            compression,
        )
        return _end_unary_response_blocking(state, call, False, None)

    def with_call(
        self,
        request_iterator: Iterator,
        timeout: Optional[float] = None,
        metadata: Optional[MetadataType] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None,
    ) -> Tuple[Any, grpc.Call]:
        (
            state,
            call,
        ) = self._blocking(
            request_iterator,
            timeout,
            metadata,
            credentials,
            wait_for_ready,
            compression,
        )
        return _end_unary_response_blocking(state, call, True, None)

    def future(
        self,
        request_iterator: Iterator,
        timeout: Optional[float] = None,
        metadata: Optional[MetadataType] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None,
    ) -> _MultiThreadedRendezvous:
        deadline = _deadline(timeout)
        state = _RPCState(_STREAM_UNARY_INITIAL_DUE, None, None, None, None)
        event_handler = _event_handler(state, self._response_deserializer)
        initial_metadata_flags = _InitialMetadataFlags().with_wait_for_ready(
            wait_for_ready
        )
        augmented_metadata = _compression.augment_metadata(
            metadata, compression
        )
        state.rpc_start_time = time.perf_counter()
        state.method = _common.decode(self._method)
        state.target = _common.decode(self._target)
        call = self._managed_call(
            cygrpc.PropagationConstants.GRPC_PROPAGATE_DEFAULTS,
            self._method,
            None,
            deadline,
            augmented_metadata,
            None if credentials is None else credentials._credentials,
            _stream_unary_invocation_operations(
                metadata, initial_metadata_flags
            ),
            event_handler,
            self._context,
            self._registered_call_handle,
        )
        _consume_request_iterator(
            request_iterator,
            state,
            call,
            self._request_serializer,
            event_handler,
        )
        return _MultiThreadedRendezvous(
            state, call, self._response_deserializer, deadline
        )


class _StreamStreamMultiCallable(grpc.StreamStreamMultiCallable):
    _channel: cygrpc.Channel
    _managed_call: IntegratedCallFactory
    _method: bytes
    _target: bytes
    _request_serializer: Optional[SerializingFunction]
    _response_deserializer: Optional[DeserializingFunction]
    _context: Any
    _registered_call_handle: Optional[int]

    __slots__ = [
        "_channel",
        "_managed_call",
        "_method",
        "_target",
        "_request_serializer",
        "_response_deserializer",
        "_context",
    ]

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        channel: cygrpc.Channel,
        managed_call: IntegratedCallFactory,
        method: bytes,
        target: bytes,
        request_serializer: Optional[SerializingFunction],
        response_deserializer: Optional[DeserializingFunction],
        _registered_call_handle: Optional[int],
    ):
        self._channel = channel
        self._managed_call = managed_call
        self._method = method
        self._target = target
        self._request_serializer = request_serializer
        self._response_deserializer = response_deserializer
        self._context = cygrpc.build_census_context()
        self._registered_call_handle = _registered_call_handle

    def __call__(
        self,
        request_iterator: Iterator,
        timeout: Optional[float] = None,
        metadata: Optional[MetadataType] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None,
    ) -> _MultiThreadedRendezvous:
        deadline = _deadline(timeout)
        state = _RPCState(_STREAM_STREAM_INITIAL_DUE, None, None, None, None)
        initial_metadata_flags = _InitialMetadataFlags().with_wait_for_ready(
            wait_for_ready
        )
        augmented_metadata = _compression.augment_metadata(
            metadata, compression
        )
        operations = (
            (
                cygrpc.SendInitialMetadataOperation(
                    augmented_metadata, initial_metadata_flags
                ),
                cygrpc.ReceiveStatusOnClientOperation(_EMPTY_FLAGS),
            ),
            (cygrpc.ReceiveInitialMetadataOperation(_EMPTY_FLAGS),),
        )
        event_handler = _event_handler(state, self._response_deserializer)
        state.rpc_start_time = time.perf_counter()
        state.method = _common.decode(self._method)
        state.target = _common.decode(self._target)
        call = self._managed_call(
            cygrpc.PropagationConstants.GRPC_PROPAGATE_DEFAULTS,
            self._method,
            None,
            _determine_deadline(deadline),
            augmented_metadata,
            None if credentials is None else credentials._credentials,
            operations,
            event_handler,
            self._context,
            self._registered_call_handle,
        )
        _consume_request_iterator(
            request_iterator,
            state,
            call,
            self._request_serializer,
            event_handler,
        )
        return _MultiThreadedRendezvous(
            state, call, self._response_deserializer, deadline
        )


class _InitialMetadataFlags(int):
    """Stores immutable initial metadata flags"""

    def __new__(cls, value: int = _EMPTY_FLAGS):
        value &= cygrpc.InitialMetadataFlags.used_mask
        return super(_InitialMetadataFlags, cls).__new__(cls, value)

    def with_wait_for_ready(self, wait_for_ready: Optional[bool]) -> int:
        if wait_for_ready is not None:
            if wait_for_ready:
                return self.__class__(
                    self
                    | cygrpc.InitialMetadataFlags.wait_for_ready
                    | cygrpc.InitialMetadataFlags.wait_for_ready_explicitly_set
                )
            elif not wait_for_ready:
                return self.__class__(
                    self & ~cygrpc.InitialMetadataFlags.wait_for_ready
                    | cygrpc.InitialMetadataFlags.wait_for_ready_explicitly_set
                )
        return self


class _ChannelCallState(object):
    channel: cygrpc.Channel
    managed_calls: int
    threading: bool

    def __init__(self, channel: cygrpc.Channel):
        self.lock = threading.Lock()
        self.channel = channel
        self.managed_calls = 0
        self.threading = False

    def reset_postfork_child(self) -> None:
        self.managed_calls = 0

    def __del__(self):
        try:
            self.channel.close(
                cygrpc.StatusCode.cancelled, "Channel deallocated!"
            )
        except (TypeError, AttributeError):
            pass


def _run_channel_spin_thread(state: _ChannelCallState) -> None:
    def channel_spin():
        while True:
            cygrpc.block_if_fork_in_progress(state)
            event = state.channel.next_call_event()
            if event.completion_type == cygrpc.CompletionType.queue_timeout:
                continue
            call_completed = event.tag(event)
            if call_completed:
                with state.lock:
                    state.managed_calls -= 1
                    if state.managed_calls == 0:
                        return

    channel_spin_thread = cygrpc.ForkManagedThread(target=channel_spin)
    channel_spin_thread.setDaemon(True)
    channel_spin_thread.start()


def _channel_managed_call_management(state: _ChannelCallState):
    # pylint: disable=too-many-arguments
    def create(
        flags: int,
        method: bytes,
        host: Optional[str],
        deadline: Optional[float],
        metadata: Optional[MetadataType],
        credentials: Optional[cygrpc.CallCredentials],
        operations: Sequence[Sequence[cygrpc.Operation]],
        event_handler: UserTag,
        context: Any,
        _registered_call_handle: Optional[int],
    ) -> cygrpc.IntegratedCall:
        """Creates a cygrpc.IntegratedCall.

        Args:
          flags: An integer bitfield of call flags.
          method: The RPC method.
          host: A host string for the created call.
          deadline: A float to be the deadline of the created call or None if
            the call is to have an infinite deadline.
          metadata: The metadata for the call or None.
          credentials: A cygrpc.CallCredentials or None.
          operations: A sequence of sequences of cygrpc.Operations to be
            started on the call.
          event_handler: A behavior to call to handle the events resultant from
            the operations on the call.
          context: Context object for distributed tracing.
          _registered_call_handle: An int representing the call handle of the
            method, or None if the method is not registered.
        Returns:
          A cygrpc.IntegratedCall with which to conduct an RPC.
        """
        operations_and_tags = tuple(
            (
                operation,
                event_handler,
            )
            for operation in operations
        )
        with state.lock:
            call = state.channel.integrated_call(
                flags,
                method,
                host,
                deadline,
                metadata,
                credentials,
                operations_and_tags,
                context,
                _registered_call_handle,
            )
            if state.managed_calls == 0:
                state.managed_calls = 1
                _run_channel_spin_thread(state)
            else:
                state.managed_calls += 1
            return call

    return create


class _ChannelConnectivityState(object):
    lock: threading.RLock
    channel: grpc.Channel
    polling: bool
    connectivity: grpc.ChannelConnectivity
    try_to_connect: bool
    # TODO(xuanwn): Refactor this: https://github.com/grpc/grpc/issues/31704
    callbacks_and_connectivities: List[
        Sequence[
            Union[
                Callable[[grpc.ChannelConnectivity], None],
                Optional[grpc.ChannelConnectivity],
            ]
        ]
    ]
    delivering: bool

    def __init__(self, channel: grpc.Channel):
        self.lock = threading.RLock()
        self.channel = channel
        self.polling = False
        self.connectivity = None
        self.try_to_connect = False
        self.callbacks_and_connectivities = []
        self.delivering = False

    def reset_postfork_child(self) -> None:
        self.polling = False
        self.connectivity = None
        self.try_to_connect = False
        self.callbacks_and_connectivities = []
        self.delivering = False


def _deliveries(
    state: _ChannelConnectivityState,
) -> List[Callable[[grpc.ChannelConnectivity], None]]:
    callbacks_needing_update = []
    for callback_and_connectivity in state.callbacks_and_connectivities:
        (
            callback,
            callback_connectivity,
        ) = callback_and_connectivity
        if callback_connectivity is not state.connectivity:
            callbacks_needing_update.append(callback)
            callback_and_connectivity[1] = state.connectivity
    return callbacks_needing_update


def _deliver(
    state: _ChannelConnectivityState,
    initial_connectivity: grpc.ChannelConnectivity,
    initial_callbacks: Sequence[Callable[[grpc.ChannelConnectivity], None]],
) -> None:
    connectivity = initial_connectivity
    callbacks = initial_callbacks
    while True:
        for callback in callbacks:
            cygrpc.block_if_fork_in_progress(state)
            try:
                callback(connectivity)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception(
                    _CHANNEL_SUBSCRIPTION_CALLBACK_ERROR_LOG_MESSAGE
                )
        with state.lock:
            callbacks = _deliveries(state)
            if callbacks:
                connectivity = state.connectivity
            else:
                state.delivering = False
                return


def _spawn_delivery(
    state: _ChannelConnectivityState,
    callbacks: Sequence[Callable[[grpc.ChannelConnectivity], None]],
) -> None:
    delivering_thread = cygrpc.ForkManagedThread(
        target=_deliver,
        args=(
            state,
            state.connectivity,
            callbacks,
        ),
    )
    delivering_thread.setDaemon(True)
    delivering_thread.start()
    state.delivering = True


# NOTE(https://github.com/grpc/grpc/issues/3064): We'd rather not poll.
def _poll_connectivity(
    state: _ChannelConnectivityState,
    channel: grpc.Channel,
    initial_try_to_connect: bool,
) -> None:
    try_to_connect = initial_try_to_connect
    connectivity = channel.check_connectivity_state(try_to_connect)
    with state.lock:
        state.connectivity = (
            _common.CYGRPC_CONNECTIVITY_STATE_TO_CHANNEL_CONNECTIVITY[
                connectivity
            ]
        )
        callbacks = tuple(
            callback for callback, _ in state.callbacks_and_connectivities
        )
        for callback_and_connectivity in state.callbacks_and_connectivities:
            callback_and_connectivity[1] = state.connectivity
        if callbacks:
            _spawn_delivery(state, callbacks)
    while True:
        event = channel.watch_connectivity_state(
            connectivity, time.time() + 0.2
        )
        cygrpc.block_if_fork_in_progress(state)
        with state.lock:
            if (
                not state.callbacks_and_connectivities
                and not state.try_to_connect
            ):
                state.polling = False
                state.connectivity = None
                break
            try_to_connect = state.try_to_connect
            state.try_to_connect = False
        if event.success or try_to_connect:
            connectivity = channel.check_connectivity_state(try_to_connect)
            with state.lock:
                state.connectivity = (
                    _common.CYGRPC_CONNECTIVITY_STATE_TO_CHANNEL_CONNECTIVITY[
                        connectivity
                    ]
                )
                if not state.delivering:
                    callbacks = _deliveries(state)
                    if callbacks:
                        _spawn_delivery(state, callbacks)


def _subscribe(
    state: _ChannelConnectivityState,
    callback: Callable[[grpc.ChannelConnectivity], None],
    try_to_connect: bool,
) -> None:
    with state.lock:
        if not state.callbacks_and_connectivities and not state.polling:
            polling_thread = cygrpc.ForkManagedThread(
                target=_poll_connectivity,
                args=(state, state.channel, bool(try_to_connect)),
            )
            polling_thread.setDaemon(True)
            polling_thread.start()
            state.polling = True
            state.callbacks_and_connectivities.append([callback, None])
        elif not state.delivering and state.connectivity is not None:
            _spawn_delivery(state, (callback,))
            state.try_to_connect |= bool(try_to_connect)
            state.callbacks_and_connectivities.append(
                [callback, state.connectivity]
            )
        else:
            state.try_to_connect |= bool(try_to_connect)
            state.callbacks_and_connectivities.append([callback, None])


def _unsubscribe(
    state: _ChannelConnectivityState,
    callback: Callable[[grpc.ChannelConnectivity], None],
) -> None:
    with state.lock:
        for index, (subscribed_callback, unused_connectivity) in enumerate(
            state.callbacks_and_connectivities
        ):
            if callback == subscribed_callback:
                state.callbacks_and_connectivities.pop(index)
                break


def _augment_options(
    base_options: Sequence[ChannelArgumentType],
    compression: Optional[grpc.Compression],
) -> Sequence[ChannelArgumentType]:
    compression_option = _compression.create_channel_option(compression)
    return (
        tuple(base_options)
        + compression_option
        + (
            (
                cygrpc.ChannelArgKey.primary_user_agent_string,
                _USER_AGENT,
            ),
        )
    )


def _separate_channel_options(
    options: Sequence[ChannelArgumentType],
) -> Tuple[Sequence[ChannelArgumentType], Sequence[ChannelArgumentType]]:
    """Separates core channel options from Python channel options."""
    core_options = []
    python_options = []
    for pair in options:
        if (
            pair[0]
            == grpc.experimental.ChannelOptions.SingleThreadedUnaryStream
        ):
            python_options.append(pair)
        else:
            core_options.append(pair)
    return python_options, core_options


class Channel(grpc.Channel):
    """A cygrpc.Channel-backed implementation of grpc.Channel."""

    _single_threaded_unary_stream: bool
    _channel: cygrpc.Channel
    _call_state: _ChannelCallState
    _connectivity_state: _ChannelConnectivityState
    _target: str
    _registered_call_handles: Dict[str, int]

    def __init__(
        self,
        target: str,
        options: Sequence[ChannelArgumentType],
        credentials: Optional[grpc.ChannelCredentials],
        compression: Optional[grpc.Compression],
    ):
        """Constructor.

        Args:
          target: The target to which to connect.
          options: Configuration options for the channel.
          credentials: A cygrpc.ChannelCredentials or None.
          compression: An optional value indicating the compression method to be
            used over the lifetime of the channel.
        """
        python_options, core_options = _separate_channel_options(options)
        self._single_threaded_unary_stream = (
            _DEFAULT_SINGLE_THREADED_UNARY_STREAM
        )
        self._process_python_options(python_options)
        self._channel = cygrpc.Channel(
            _common.encode(target),
            _augment_options(core_options, compression),
            credentials,
        )
        self._target = target
        self._call_state = _ChannelCallState(self._channel)
        self._connectivity_state = _ChannelConnectivityState(self._channel)
        cygrpc.fork_register_channel(self)
        if cygrpc.g_gevent_activated:
            cygrpc.gevent_increment_channel_count()

    def _get_registered_call_handle(self, method: str) -> int:
        """
        Get the registered call handle for a method.

        This is a semi-private method. It is intended for use only by gRPC generated code.

        This method is not thread-safe.

        Args:
          method: Required, the method name for the RPC.

        Returns:
          The registered call handle pointer in the form of a Python Long.
        """
        return self._channel.get_registered_call_handle(_common.encode(method))

    def _process_python_options(
        self, python_options: Sequence[ChannelArgumentType]
    ) -> None:
        """Sets channel attributes according to python-only channel options."""
        for pair in python_options:
            if (
                pair[0]
                == grpc.experimental.ChannelOptions.SingleThreadedUnaryStream
            ):
                self._single_threaded_unary_stream = True

    def subscribe(
        self,
        callback: Callable[[grpc.ChannelConnectivity], None],
        try_to_connect: Optional[bool] = None,
    ) -> None:
        _subscribe(self._connectivity_state, callback, try_to_connect)

    def unsubscribe(
        self, callback: Callable[[grpc.ChannelConnectivity], None]
    ) -> None:
        _unsubscribe(self._connectivity_state, callback)

    # pylint: disable=arguments-differ
    def unary_unary(
        self,
        method: str,
        request_serializer: Optional[SerializingFunction] = None,
        response_deserializer: Optional[DeserializingFunction] = None,
        _registered_method: Optional[bool] = False,
    ) -> grpc.UnaryUnaryMultiCallable:
        _registered_call_handle = None
        if _registered_method:
            _registered_call_handle = self._get_registered_call_handle(method)
        return _UnaryUnaryMultiCallable(
            self._channel,
            _channel_managed_call_management(self._call_state),
            _common.encode(method),
            _common.encode(self._target),
            request_serializer,
            response_deserializer,
            _registered_call_handle,
        )

    # pylint: disable=arguments-differ
    def unary_stream(
        self,
        method: str,
        request_serializer: Optional[SerializingFunction] = None,
        response_deserializer: Optional[DeserializingFunction] = None,
        _registered_method: Optional[bool] = False,
    ) -> grpc.UnaryStreamMultiCallable:
        _registered_call_handle = None
        if _registered_method:
            _registered_call_handle = self._get_registered_call_handle(method)
        # NOTE(rbellevi): Benchmarks have shown that running a unary-stream RPC
        # on a single Python thread results in an appreciable speed-up. However,
        # due to slight differences in capability, the multi-threaded variant
        # remains the default.
        if self._single_threaded_unary_stream:
            return _SingleThreadedUnaryStreamMultiCallable(
                self._channel,
                _common.encode(method),
                _common.encode(self._target),
                request_serializer,
                response_deserializer,
                _registered_call_handle,
            )
        else:
            return _UnaryStreamMultiCallable(
                self._channel,
                _channel_managed_call_management(self._call_state),
                _common.encode(method),
                _common.encode(self._target),
                request_serializer,
                response_deserializer,
                _registered_call_handle,
            )

    # pylint: disable=arguments-differ
    def stream_unary(
        self,
        method: str,
        request_serializer: Optional[SerializingFunction] = None,
        response_deserializer: Optional[DeserializingFunction] = None,
        _registered_method: Optional[bool] = False,
    ) -> grpc.StreamUnaryMultiCallable:
        _registered_call_handle = None
        if _registered_method:
            _registered_call_handle = self._get_registered_call_handle(method)
        return _StreamUnaryMultiCallable(
            self._channel,
            _channel_managed_call_management(self._call_state),
            _common.encode(method),
            _common.encode(self._target),
            request_serializer,
            response_deserializer,
            _registered_call_handle,
        )

    # pylint: disable=arguments-differ
    def stream_stream(
        self,
        method: str,
        request_serializer: Optional[SerializingFunction] = None,
        response_deserializer: Optional[DeserializingFunction] = None,
        _registered_method: Optional[bool] = False,
    ) -> grpc.StreamStreamMultiCallable:
        _registered_call_handle = None
        if _registered_method:
            _registered_call_handle = self._get_registered_call_handle(method)
        return _StreamStreamMultiCallable(
            self._channel,
            _channel_managed_call_management(self._call_state),
            _common.encode(method),
            _common.encode(self._target),
            request_serializer,
            response_deserializer,
            _registered_call_handle,
        )

    def _unsubscribe_all(self) -> None:
        state = self._connectivity_state
        if state:
            with state.lock:
                del state.callbacks_and_connectivities[:]

    def _close(self) -> None:
        self._unsubscribe_all()
        self._channel.close(cygrpc.StatusCode.cancelled, "Channel closed!")
        cygrpc.fork_unregister_channel(self)
        if cygrpc.g_gevent_activated:
            cygrpc.gevent_decrement_channel_count()

    def _close_on_fork(self) -> None:
        self._unsubscribe_all()
        self._channel.close_on_fork(
            cygrpc.StatusCode.cancelled, "Channel closed due to fork"
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._close()
        return False

    def close(self) -> None:
        self._close()

    def __del__(self):
        # TODO(https://github.com/grpc/grpc/issues/12531): Several releases
        # after 1.12 (1.16 or thereabouts?) add a "self._channel.close" call
        # here (or more likely, call self._close() here). We don't do this today
        # because many valid use cases today allow the channel to be deleted
        # immediately after stubs are created. After a sufficient period of time
        # has passed for all users to be trusted to freeze out to their channels
        # for as long as they are in use and to close them after using them,
        # then deletion of this grpc._channel.Channel instance can be made to
        # effect closure of the underlying cygrpc.Channel instance.
        try:
            self._unsubscribe_all()
        except:  # pylint: disable=bare-except
            # Exceptions in __del__ are ignored by Python anyway, but they can
            # keep spamming logs.  Just silence them.
            pass

# === NexusCore/openenv\Lib\site-packages\joblib\test\test_parallel.py ===
"""
Test the parallel module.
"""

# Author: Gael Varoquaux <gael dot varoquaux at normalesup dot org>
# Copyright (c) 2010-2011 Gael Varoquaux
# License: BSD Style, 3 clauses.

import mmap
import os
import re
import sys
import threading
import time
import warnings
import weakref
from contextlib import nullcontext
from math import sqrt
from multiprocessing import TimeoutError
from pickle import PicklingError
from time import sleep
from traceback import format_exception

import pytest

import joblib
from joblib import dump, load, parallel
from joblib._multiprocessing_helpers import mp
from joblib.test.common import (
    IS_GIL_DISABLED,
    np,
    with_multiprocessing,
    with_numpy,
)
from joblib.testing import check_subprocess_call, parametrize, raises, skipif, warns

if mp is not None:
    # Loky is not available if multiprocessing is not
    from joblib.externals.loky import get_reusable_executor

from queue import Queue

try:
    import posix
except ImportError:
    posix = None

try:
    from ._openmp_test_helper.parallel_sum import parallel_sum
except ImportError:
    parallel_sum = None

try:
    import distributed
except ImportError:
    distributed = None

from joblib._parallel_backends import (
    LokyBackend,
    MultiprocessingBackend,
    ParallelBackendBase,
    SequentialBackend,
    ThreadingBackend,
)
from joblib.parallel import (
    BACKENDS,
    Parallel,
    cpu_count,
    delayed,
    effective_n_jobs,
    mp,
    parallel_backend,
    parallel_config,
    register_parallel_backend,
)

RETURN_GENERATOR_BACKENDS = BACKENDS.copy()
RETURN_GENERATOR_BACKENDS.pop("multiprocessing", None)

ALL_VALID_BACKENDS = [None] + sorted(BACKENDS.keys())
# Add instances of backend classes deriving from ParallelBackendBase
ALL_VALID_BACKENDS += [BACKENDS[backend_str]() for backend_str in BACKENDS]
if mp is None:
    PROCESS_BACKENDS = []
else:
    PROCESS_BACKENDS = ["multiprocessing", "loky"]
PARALLEL_BACKENDS = PROCESS_BACKENDS + ["threading"]

if hasattr(mp, "get_context"):
    # Custom multiprocessing context in Python 3.4+
    ALL_VALID_BACKENDS.append(mp.get_context("spawn"))


def get_default_backend_instance():
    # The default backend can be changed before running the tests through
    # JOBLIB_DEFAULT_PARALLEL_BACKEND environment variable so we need to use
    # parallel.DEFAULT_BACKEND here and not
    # from joblib.parallel import DEFAULT_BACKEND
    return BACKENDS[parallel.DEFAULT_BACKEND]


def get_workers(backend):
    return getattr(backend, "_pool", getattr(backend, "_workers", None))


def division(x, y):
    return x / y


def square(x):
    return x**2


class MyExceptionWithFinickyInit(Exception):
    """An exception class with non trivial __init__"""

    def __init__(self, a, b, c, d):
        pass


def exception_raiser(x, custom_exception=False):
    if x == 7:
        raise (
            MyExceptionWithFinickyInit("a", "b", "c", "d")
            if custom_exception
            else ValueError
        )
    return x


def interrupt_raiser(x):
    time.sleep(0.05)
    raise KeyboardInterrupt


def f(x, y=0, z=0):
    """A module-level function so that it can be spawn with
    multiprocessing.
    """
    return x**2 + y + z


def _active_backend_type():
    return type(parallel.get_active_backend()[0])


def parallel_func(inner_n_jobs, backend):
    return Parallel(n_jobs=inner_n_jobs, backend=backend)(
        delayed(square)(i) for i in range(3)
    )


###############################################################################
def test_cpu_count():
    assert cpu_count() > 0


def test_effective_n_jobs():
    assert effective_n_jobs() > 0


@parametrize("context", [parallel_config, parallel_backend])
@pytest.mark.parametrize(
    "backend_n_jobs, expected_n_jobs",
    [(3, 3), (-1, effective_n_jobs(n_jobs=-1)), (None, 1)],
    ids=["positive-int", "negative-int", "None"],
)
@with_multiprocessing
def test_effective_n_jobs_None(context, backend_n_jobs, expected_n_jobs):
    # check the number of effective jobs when `n_jobs=None`
    # non-regression test for https://github.com/joblib/joblib/issues/984
    with context("threading", n_jobs=backend_n_jobs):
        # when using a backend, the default of number jobs will be the one set
        # in the backend
        assert effective_n_jobs(n_jobs=None) == expected_n_jobs
    # without any backend, None will default to a single job
    assert effective_n_jobs(n_jobs=None) == 1


###############################################################################
# Test parallel


@parametrize("backend", ALL_VALID_BACKENDS)
@parametrize("n_jobs", [1, 2, -1, -2])
@parametrize("verbose", [2, 11, 100])
def test_simple_parallel(backend, n_jobs, verbose):
    assert [square(x) for x in range(5)] == Parallel(
        n_jobs=n_jobs, backend=backend, verbose=verbose
    )(delayed(square)(x) for x in range(5))


@parametrize("backend", ALL_VALID_BACKENDS)
@parametrize("n_jobs", [1, 2])
def test_parallel_pretty_print(backend, n_jobs):
    n_tasks = 100
    pattern = re.compile(r"(Done\s+\d+ out of \d+ \|)")

    class ParallelLog(Parallel):
        messages = []

        def _print(self, msg):
            self.messages.append(msg)

    executor = ParallelLog(n_jobs=n_jobs, backend=backend, verbose=10000)
    executor([delayed(f)(i) for i in range(n_tasks)])
    lens = set()
    for message in executor.messages:
        if s := pattern.search(message):
            a, b = s.span()
            lens.add(b - a)
    assert len(lens) == 1


@parametrize("backend", ALL_VALID_BACKENDS)
def test_main_thread_renamed_no_warning(backend, monkeypatch):
    # Check that no default backend relies on the name of the main thread:
    # https://github.com/joblib/joblib/issues/180#issuecomment-253266247
    # Some programs use a different name for the main thread. This is the case
    # for uWSGI apps for instance.
    monkeypatch.setattr(
        target=threading.current_thread(),
        name="name",
        value="some_new_name_for_the_main_thread",
    )

    with warnings.catch_warnings(record=True) as warninfo:
        results = Parallel(n_jobs=2, backend=backend)(
            delayed(square)(x) for x in range(3)
        )
        assert results == [0, 1, 4]

    # Due to the default parameters of LokyBackend, there is a chance that
    # warninfo catches Warnings from worker timeouts. We remove it if it exists
    # We also remove DeprecationWarnings which could lead to false negatives.
    warninfo = [
        w
        for w in warninfo
        if "worker timeout" not in str(w.message)
        and not isinstance(w.message, DeprecationWarning)
    ]

    # Under Python 3.13 if backend='multiprocessing', you will get a
    # warning saying that forking a multi-threaded process is not a good idea,
    # we ignore them in this test
    if backend in [None, "multiprocessing"] or isinstance(
        backend, MultiprocessingBackend
    ):
        message_part = "multi-threaded, use of fork() may lead to deadlocks"
        warninfo = [w for w in warninfo if message_part not in str(w.message)]

    # The multiprocessing backend will raise a warning when detecting that is
    # started from the non-main thread. Let's check that there is no false
    # positive because of the name change.
    assert len(warninfo) == 0


def _assert_warning_nested(backend, inner_n_jobs, expected):
    with warnings.catch_warnings(record=True) as warninfo:
        warnings.simplefilter("always")
        parallel_func(backend=backend, inner_n_jobs=inner_n_jobs)

    warninfo = [w.message for w in warninfo]
    if expected:
        if warninfo:
            warnings_are_correct = all(
                "backed parallel loops cannot" in each.args[0] for each in warninfo
            )
            # With free-threaded Python, when the outer backend is threading,
            # we might see more that one warning
            warnings_have_the_right_length = (
                len(warninfo) >= 1 if IS_GIL_DISABLED else len(warninfo) == 1
            )
            return warnings_are_correct and warnings_have_the_right_length

        return False
    else:
        assert not warninfo
        return True


@with_multiprocessing
@parametrize(
    "parent_backend,child_backend,expected",
    [
        ("loky", "multiprocessing", True),
        ("loky", "loky", False),
        ("multiprocessing", "multiprocessing", True),
        ("multiprocessing", "loky", True),
        ("threading", "multiprocessing", True),
        ("threading", "loky", True),
    ],
)
def test_nested_parallel_warnings(parent_backend, child_backend, expected):
    # no warnings if inner_n_jobs=1
    Parallel(n_jobs=2, backend=parent_backend)(
        delayed(_assert_warning_nested)(
            backend=child_backend, inner_n_jobs=1, expected=False
        )
        for _ in range(5)
    )

    #  warnings if inner_n_jobs != 1 and expected
    res = Parallel(n_jobs=2, backend=parent_backend)(
        delayed(_assert_warning_nested)(
            backend=child_backend, inner_n_jobs=2, expected=expected
        )
        for _ in range(5)
    )

    # warning handling is not thread safe. One thread might see multiple
    # warning or no warning at all.
    if parent_backend == "threading":
        assert any(res)
    else:
        assert all(res)


@with_multiprocessing
@parametrize("backend", ["loky", "multiprocessing", "threading"])
def test_background_thread_parallelism(backend):
    is_run_parallel = [False]

    def background_thread(is_run_parallel):
        with warnings.catch_warnings(record=True) as warninfo:
            Parallel(n_jobs=2)(delayed(sleep)(0.1) for _ in range(4))
        print(len(warninfo))
        is_run_parallel[0] = len(warninfo) == 0

    t = threading.Thread(target=background_thread, args=(is_run_parallel,))
    t.start()
    t.join()
    assert is_run_parallel[0]


def nested_loop(backend):
    Parallel(n_jobs=2, backend=backend)(delayed(square)(0.01) for _ in range(2))


@parametrize("child_backend", BACKENDS)
@parametrize("parent_backend", BACKENDS)
def test_nested_loop(parent_backend, child_backend):
    Parallel(n_jobs=2, backend=parent_backend)(
        delayed(nested_loop)(child_backend) for _ in range(2)
    )


def raise_exception(backend):
    raise ValueError


@with_multiprocessing
def test_nested_loop_with_exception_with_loky():
    with raises(ValueError):
        with Parallel(n_jobs=2, backend="loky") as parallel:
            parallel([delayed(nested_loop)("loky"), delayed(raise_exception)("loky")])


def test_mutate_input_with_threads():
    """Input is mutable when using the threading backend"""
    q = Queue(maxsize=5)
    Parallel(n_jobs=2, backend="threading")(delayed(q.put)(1) for _ in range(5))
    assert q.full()


@parametrize("n_jobs", [1, 2, 3])
def test_parallel_kwargs(n_jobs):
    """Check the keyword argument processing of pmap."""
    lst = range(10)
    assert [f(x, y=1) for x in lst] == Parallel(n_jobs=n_jobs)(
        delayed(f)(x, y=1) for x in lst
    )


@parametrize("backend", PARALLEL_BACKENDS)
def test_parallel_as_context_manager(backend):
    lst = range(10)
    expected = [f(x, y=1) for x in lst]

    with Parallel(n_jobs=4, backend=backend) as p:
        # Internally a pool instance has been eagerly created and is managed
        # via the context manager protocol
        managed_backend = p._backend

        # We make call with the managed parallel object several times inside
        # the managed block:
        assert expected == p(delayed(f)(x, y=1) for x in lst)
        assert expected == p(delayed(f)(x, y=1) for x in lst)

        # Those calls have all used the same pool instance:
        if mp is not None:
            assert get_workers(managed_backend) is get_workers(p._backend)

    # As soon as we exit the context manager block, the pool is terminated and
    # no longer referenced from the parallel object:
    if mp is not None:
        assert get_workers(p._backend) is None

    # It's still possible to use the parallel instance in non-managed mode:
    assert expected == p(delayed(f)(x, y=1) for x in lst)
    if mp is not None:
        assert get_workers(p._backend) is None


@with_multiprocessing
def test_parallel_pickling():
    """Check that pmap captures the errors when it is passed an object
    that cannot be pickled.
    """

    class UnpicklableObject(object):
        def __reduce__(self):
            raise RuntimeError("123")

    with raises(PicklingError, match=r"the task to send"):
        Parallel(n_jobs=2, backend="loky")(
            delayed(id)(UnpicklableObject()) for _ in range(10)
        )


@with_numpy
@with_multiprocessing
@parametrize("byteorder", ["<", ">", "="])
@parametrize("max_nbytes", [1, "1M"])
def test_parallel_byteorder_corruption(byteorder, max_nbytes):
    def inspect_byteorder(x):
        return x, x.dtype.byteorder

    x = np.arange(6).reshape((2, 3)).view(f"{byteorder}i4")

    initial_np_byteorder = x.dtype.byteorder

    result = Parallel(n_jobs=2, backend="loky", max_nbytes=max_nbytes)(
        delayed(inspect_byteorder)(x) for _ in range(3)
    )

    for x_returned, byteorder_in_worker in result:
        assert byteorder_in_worker == initial_np_byteorder
        assert byteorder_in_worker == x_returned.dtype.byteorder
        np.testing.assert_array_equal(x, x_returned)


@parametrize("backend", PARALLEL_BACKENDS)
def test_parallel_timeout_success(backend):
    # Check that timeout isn't thrown when function is fast enough
    assert (
        len(
            Parallel(n_jobs=2, backend=backend, timeout=30)(
                delayed(sleep)(0.001) for x in range(10)
            )
        )
        == 10
    )


@with_multiprocessing
@parametrize("backend", PARALLEL_BACKENDS)
def test_parallel_timeout_fail(backend):
    # Check that timeout properly fails when function is too slow
    with raises(TimeoutError):
        Parallel(n_jobs=2, backend=backend, timeout=0.01)(
            delayed(sleep)(10) for x in range(10)
        )


@with_multiprocessing
@parametrize("backend", set(RETURN_GENERATOR_BACKENDS) - {"sequential"})
@parametrize("return_as", ["generator", "generator_unordered"])
def test_parallel_timeout_fail_with_generator(backend, return_as):
    # Check that timeout properly fails when function is too slow with
    # return_as=generator
    with raises(TimeoutError):
        list(
            Parallel(n_jobs=2, backend=backend, return_as=return_as, timeout=0.1)(
                delayed(sleep)(10) for x in range(10)
            )
        )

    # Fast tasks and high timeout should not raise
    list(
        Parallel(n_jobs=2, backend=backend, return_as=return_as, timeout=10)(
            delayed(sleep)(0.01) for x in range(10)
        )
    )


@with_multiprocessing
@parametrize("backend", PROCESS_BACKENDS)
def test_error_capture(backend):
    # Check that error are captured, and that correct exceptions
    # are raised.
    if mp is not None:
        with raises(ZeroDivisionError):
            Parallel(n_jobs=2, backend=backend)(
                [delayed(division)(x, y) for x, y in zip((0, 1), (1, 0))]
            )

        with raises(KeyboardInterrupt):
            Parallel(n_jobs=2, backend=backend)(
                [delayed(interrupt_raiser)(x) for x in (1, 0)]
            )

        # Try again with the context manager API
        with Parallel(n_jobs=2, backend=backend) as parallel:
            assert get_workers(parallel._backend) is not None
            original_workers = get_workers(parallel._backend)

            with raises(ZeroDivisionError):
                parallel([delayed(division)(x, y) for x, y in zip((0, 1), (1, 0))])

            # The managed pool should still be available and be in a working
            # state despite the previously raised (and caught) exception
            assert get_workers(parallel._backend) is not None

            # The pool should have been interrupted and restarted:
            assert get_workers(parallel._backend) is not original_workers

            assert [f(x, y=1) for x in range(10)] == parallel(
                delayed(f)(x, y=1) for x in range(10)
            )

            original_workers = get_workers(parallel._backend)
            with raises(KeyboardInterrupt):
                parallel([delayed(interrupt_raiser)(x) for x in (1, 0)])

            # The pool should still be available despite the exception
            assert get_workers(parallel._backend) is not None

            # The pool should have been interrupted and restarted:
            assert get_workers(parallel._backend) is not original_workers

            assert [f(x, y=1) for x in range(10)] == parallel(
                delayed(f)(x, y=1) for x in range(10)
            ), (
                parallel._iterating,
                parallel.n_completed_tasks,
                parallel.n_dispatched_tasks,
                parallel._aborting,
            )

        # Check that the inner pool has been terminated when exiting the
        # context manager
        assert get_workers(parallel._backend) is None
    else:
        with raises(KeyboardInterrupt):
            Parallel(n_jobs=2)([delayed(interrupt_raiser)(x) for x in (1, 0)])

    # wrapped exceptions should inherit from the class of the original
    # exception to make it easy to catch them
    with raises(ZeroDivisionError):
        Parallel(n_jobs=2)([delayed(division)(x, y) for x, y in zip((0, 1), (1, 0))])

    with raises(MyExceptionWithFinickyInit):
        Parallel(n_jobs=2, verbose=0)(
            (delayed(exception_raiser)(i, custom_exception=True) for i in range(30))
        )


@with_multiprocessing
@parametrize("backend", BACKENDS)
def test_error_in_task_iterator(backend):
    def my_generator(raise_at=0):
        for i in range(20):
            if i == raise_at:
                raise ValueError("Iterator Raising Error")
            yield i

    with Parallel(n_jobs=2, backend=backend) as p:
        # The error is raised in the pre-dispatch phase
        with raises(ValueError, match="Iterator Raising Error"):
            p(delayed(square)(i) for i in my_generator(raise_at=0))

        # The error is raised when dispatching a new task after the
        # pre-dispatch (likely to happen in a different thread)
        with raises(ValueError, match="Iterator Raising Error"):
            p(delayed(square)(i) for i in my_generator(raise_at=5))

        # Same, but raises long after the pre-dispatch phase
        with raises(ValueError, match="Iterator Raising Error"):
            p(delayed(square)(i) for i in my_generator(raise_at=19))


def consumer(queue, item):
    queue.append("Consumed %s" % item)


@parametrize("backend", BACKENDS)
@parametrize(
    "batch_size, expected_queue",
    [
        (
            1,
            [
                "Produced 0",
                "Consumed 0",
                "Produced 1",
                "Consumed 1",
                "Produced 2",
                "Consumed 2",
                "Produced 3",
                "Consumed 3",
                "Produced 4",
                "Consumed 4",
                "Produced 5",
                "Consumed 5",
            ],
        ),
        (
            4,
            [  # First Batch
                "Produced 0",
                "Produced 1",
                "Produced 2",
                "Produced 3",
                "Consumed 0",
                "Consumed 1",
                "Consumed 2",
                "Consumed 3",
                # Second batch
                "Produced 4",
                "Produced 5",
                "Consumed 4",
                "Consumed 5",
            ],
        ),
    ],
)
def test_dispatch_one_job(backend, batch_size, expected_queue):
    """Test that with only one job, Parallel does act as a iterator."""
    queue = list()

    def producer():
        for i in range(6):
            queue.append("Produced %i" % i)
            yield i

    Parallel(n_jobs=1, batch_size=batch_size, backend=backend)(
        delayed(consumer)(queue, x) for x in producer()
    )
    assert queue == expected_queue
    assert len(queue) == 12


@with_multiprocessing
@parametrize("backend", PARALLEL_BACKENDS)
def test_dispatch_multiprocessing(backend):
    """Check that using pre_dispatch Parallel does indeed dispatch items
    lazily.
    """
    manager = mp.Manager()
    queue = manager.list()

    def producer():
        for i in range(6):
            queue.append("Produced %i" % i)
            yield i

    Parallel(n_jobs=2, batch_size=1, pre_dispatch=3, backend=backend)(
        delayed(consumer)(queue, "any") for _ in producer()
    )

    queue_contents = list(queue)
    assert queue_contents[0] == "Produced 0"

    # Only 3 tasks are pre-dispatched out of 6. The 4th task is dispatched only
    # after any of the first 3 jobs have completed.
    first_consumption_index = queue_contents[:4].index("Consumed any")
    assert first_consumption_index > -1

    produced_3_index = queue_contents.index("Produced 3")  # 4th task produced
    assert produced_3_index > first_consumption_index

    assert len(queue) == 12


def test_batching_auto_threading():
    # batching='auto' with the threading backend leaves the effective batch
    # size to 1 (no batching) as it has been found to never be beneficial with
    # this low-overhead backend.

    with Parallel(n_jobs=2, batch_size="auto", backend="threading") as p:
        p(delayed(id)(i) for i in range(5000))  # many very fast tasks
        assert p._backend.compute_batch_size() == 1


@with_multiprocessing
@parametrize("backend", PROCESS_BACKENDS)
def test_batching_auto_subprocesses(backend):
    with Parallel(n_jobs=2, batch_size="auto", backend=backend) as p:
        p(delayed(id)(i) for i in range(5000))  # many very fast tasks

        # It should be strictly larger than 1 but as we don't want heisen
        # failures on clogged CI worker environment be safe and only check that
        # it's a strictly positive number.
        assert p._backend.compute_batch_size() > 0


def test_exception_dispatch():
    """Make sure that exception raised during dispatch are indeed captured"""
    with raises(ValueError):
        Parallel(n_jobs=2, pre_dispatch=16, verbose=0)(
            delayed(exception_raiser)(i) for i in range(30)
        )


def nested_function_inner(i):
    Parallel(n_jobs=2)(delayed(exception_raiser)(j) for j in range(30))


def nested_function_outer(i):
    Parallel(n_jobs=2)(delayed(nested_function_inner)(j) for j in range(30))


@with_multiprocessing
@parametrize("backend", PARALLEL_BACKENDS)
@pytest.mark.xfail(reason="https://github.com/joblib/loky/pull/255")
def test_nested_exception_dispatch(backend):
    """Ensure errors for nested joblib cases gets propagated

    We rely on the Python 3 built-in __cause__ system that already
    report this kind of information to the user.
    """
    with raises(ValueError) as excinfo:
        Parallel(n_jobs=2, backend=backend)(
            delayed(nested_function_outer)(i) for i in range(30)
        )

    # Check that important information such as function names are visible
    # in the final error message reported to the user
    report_lines = format_exception(excinfo.type, excinfo.value, excinfo.tb)
    report = "".join(report_lines)
    assert "nested_function_outer" in report
    assert "nested_function_inner" in report
    assert "exception_raiser" in report

    assert type(excinfo.value) is ValueError


class FakeParallelBackend(SequentialBackend):
    """Pretends to run concurrently while running sequentially."""

    def configure(self, n_jobs=1, parallel=None, **backend_args):
        self.n_jobs = self.effective_n_jobs(n_jobs)
        self.parallel = parallel
        return n_jobs

    def effective_n_jobs(self, n_jobs=1):
        if n_jobs < 0:
            n_jobs = max(mp.cpu_count() + 1 + n_jobs, 1)
        return n_jobs


def test_invalid_backend():
    with raises(ValueError, match="Invalid backend:"):
        Parallel(backend="unit-testing")

    with raises(ValueError, match="Invalid backend:"):
        with parallel_config(backend="unit-testing"):
            pass

    with raises(ValueError, match="Invalid backend:"):
        with parallel_config(backend="unit-testing"):
            pass


@parametrize("backend", ALL_VALID_BACKENDS)
def test_invalid_njobs(backend):
    with raises(ValueError) as excinfo:
        Parallel(n_jobs=0, backend=backend)._initialize_backend()
    assert "n_jobs == 0 in Parallel has no meaning" in str(excinfo.value)

    with raises(ValueError) as excinfo:
        Parallel(n_jobs=0.5, backend=backend)._initialize_backend()
    assert "n_jobs == 0 in Parallel has no meaning" in str(excinfo.value)

    with raises(ValueError) as excinfo:
        Parallel(n_jobs="2.3", backend=backend)._initialize_backend()
    assert "n_jobs could not be converted to int" in str(excinfo.value)

    with raises(ValueError) as excinfo:
        Parallel(n_jobs="invalid_str", backend=backend)._initialize_backend()
    assert "n_jobs could not be converted to int" in str(excinfo.value)


@with_multiprocessing
@parametrize("backend", PARALLEL_BACKENDS)
@parametrize("n_jobs", ["2", 2.3, 2])
def test_njobs_converted_to_int(backend, n_jobs):
    p = Parallel(n_jobs=n_jobs, backend=backend)
    assert p._effective_n_jobs() == 2

    res = p(delayed(square)(i) for i in range(10))
    assert all(r == square(i) for i, r in enumerate(res))


def test_register_parallel_backend():
    try:
        register_parallel_backend("test_backend", FakeParallelBackend)
        assert "test_backend" in BACKENDS
        assert BACKENDS["test_backend"] == FakeParallelBackend
    finally:
        del BACKENDS["test_backend"]


def test_overwrite_default_backend():
    default_backend_orig = parallel.DEFAULT_BACKEND
    assert _active_backend_type() == get_default_backend_instance()
    try:
        register_parallel_backend("threading", BACKENDS["threading"], make_default=True)
        assert _active_backend_type() == ThreadingBackend
    finally:
        # Restore the global default manually
        parallel.DEFAULT_BACKEND = default_backend_orig
    assert _active_backend_type() == get_default_backend_instance()


@skipif(mp is not None, reason="Only without multiprocessing")
def test_backend_no_multiprocessing():
    with warns(UserWarning, match="joblib backend '.*' is not available on.*"):
        Parallel(backend="loky")(delayed(square)(i) for i in range(3))

    # The below should now work without problems
    with parallel_config(backend="loky"):
        Parallel()(delayed(square)(i) for i in range(3))


def check_backend_context_manager(context, backend_name):
    with context(backend_name, n_jobs=3):
        active_backend, active_n_jobs = parallel.get_active_backend()
        assert active_n_jobs == 3
        assert effective_n_jobs(3) == 3
        p = Parallel()
        assert p.n_jobs == 3
        if backend_name == "multiprocessing":
            assert type(active_backend) is MultiprocessingBackend
            assert type(p._backend) is MultiprocessingBackend
        elif backend_name == "loky":
            assert type(active_backend) is LokyBackend
            assert type(p._backend) is LokyBackend
        elif backend_name == "threading":
            assert type(active_backend) is ThreadingBackend
            assert type(p._backend) is ThreadingBackend
        elif backend_name.startswith("test_"):
            assert type(active_backend) is FakeParallelBackend
            assert type(p._backend) is FakeParallelBackend


all_backends_for_context_manager = PARALLEL_BACKENDS[:]
all_backends_for_context_manager.extend(["test_backend_%d" % i for i in range(3)])


@with_multiprocessing
@parametrize("backend", all_backends_for_context_manager)
@parametrize("context", [parallel_backend, parallel_config])
def test_backend_context_manager(monkeypatch, backend, context):
    if backend not in BACKENDS:
        monkeypatch.setitem(BACKENDS, backend, FakeParallelBackend)

    assert _active_backend_type() == get_default_backend_instance()
    # check that this possible to switch parallel backends sequentially
    check_backend_context_manager(context, backend)

    # The default backend is restored
    assert _active_backend_type() == get_default_backend_instance()

    # Check that context manager switching is thread safe:
    Parallel(n_jobs=2, backend="threading")(
        delayed(check_backend_context_manager)(context, b)
        for b in all_backends_for_context_manager
        if not b
    )

    # The default backend is again restored
    assert _active_backend_type() == get_default_backend_instance()


class ParameterizedParallelBackend(SequentialBackend):
    """Pretends to run conncurrently while running sequentially."""

    def __init__(self, param=None):
        if param is None:
            raise ValueError("param should not be None")
        self.param = param


@parametrize("context", [parallel_config, parallel_backend])
def test_parameterized_backend_context_manager(monkeypatch, context):
    monkeypatch.setitem(BACKENDS, "param_backend", ParameterizedParallelBackend)
    assert _active_backend_type() == get_default_backend_instance()

    with context("param_backend", param=42, n_jobs=3):
        active_backend, active_n_jobs = parallel.get_active_backend()
        assert type(active_backend) is ParameterizedParallelBackend
        assert active_backend.param == 42
        assert active_n_jobs == 3
        p = Parallel()
        assert p.n_jobs == 3
        assert p._backend is active_backend
        results = p(delayed(sqrt)(i) for i in range(5))
    assert results == [sqrt(i) for i in range(5)]

    # The default backend is again restored
    assert _active_backend_type() == get_default_backend_instance()


@parametrize("context", [parallel_config, parallel_backend])
def test_directly_parameterized_backend_context_manager(context):
    assert _active_backend_type() == get_default_backend_instance()

    # Check that it's possible to pass a backend instance directly,
    # without registration
    with context(ParameterizedParallelBackend(param=43), n_jobs=5):
        active_backend, active_n_jobs = parallel.get_active_backend()
        assert type(active_backend) is ParameterizedParallelBackend
        assert active_backend.param == 43
        assert active_n_jobs == 5
        p = Parallel()
        assert p.n_jobs == 5
        assert p._backend is active_backend
        results = p(delayed(sqrt)(i) for i in range(5))
    assert results == [sqrt(i) for i in range(5)]

    # The default backend is again restored
    assert _active_backend_type() == get_default_backend_instance()


def sleep_and_return_pid():
    sleep(0.1)
    return os.getpid()


def get_nested_pids():
    assert _active_backend_type() == ThreadingBackend
    # Assert that the nested backend does not change the default number of
    # jobs used in Parallel
    assert Parallel()._effective_n_jobs() == 1

    # Assert that the tasks are running only on one process
    return Parallel(n_jobs=2)(delayed(sleep_and_return_pid)() for _ in range(2))


class MyBackend(joblib._parallel_backends.LokyBackend):
    """Backend to test backward compatibility with older backends"""

    def get_nested_backend(
        self,
    ):
        # Older backends only return a backend, without n_jobs indications.
        return super(MyBackend, self).get_nested_backend()[0]


register_parallel_backend("back_compat_backend", MyBackend)


@with_multiprocessing
@parametrize("backend", ["threading", "loky", "multiprocessing", "back_compat_backend"])
@parametrize("context", [parallel_config, parallel_backend])
def test_nested_backend_context_manager(context, backend):
    # Check that by default, nested parallel calls will always use the
    # ThreadingBackend

    with context(backend):
        pid_groups = Parallel(n_jobs=2)(delayed(get_nested_pids)() for _ in range(10))
        for pid_group in pid_groups:
            assert len(set(pid_group)) == 1


@with_multiprocessing
@parametrize("n_jobs", [2, -1, None])
@parametrize("backend", PARALLEL_BACKENDS)
@parametrize("context", [parallel_config, parallel_backend])
def test_nested_backend_in_sequential(backend, n_jobs, context):
    # Check that by default, nested parallel calls will always use the
    # ThreadingBackend

    def check_nested_backend(expected_backend_type, expected_n_job):
        # Assert that the sequential backend at top level, does not change the
        # backend for nested calls.
        assert _active_backend_type() == BACKENDS[expected_backend_type]

        # Assert that the nested backend in SequentialBackend does not change
        # the default number of jobs used in Parallel
        expected_n_job = effective_n_jobs(expected_n_job)
        assert Parallel()._effective_n_jobs() == expected_n_job

    Parallel(n_jobs=1)(
        delayed(check_nested_backend)(parallel.DEFAULT_BACKEND, 1) for _ in range(10)
    )

    with context(backend, n_jobs=n_jobs):
        Parallel(n_jobs=1)(
            delayed(check_nested_backend)(backend, n_jobs) for _ in range(10)
        )


def check_nesting_level(context, inner_backend, expected_level):
    with context(inner_backend) as ctx:
        if context is parallel_config:
            backend = ctx["backend"]
        if context is parallel_backend:
            backend = ctx[0]
        assert backend.nesting_level == expected_level


@with_multiprocessing
@parametrize("outer_backend", PARALLEL_BACKENDS)
@parametrize("inner_backend", PARALLEL_BACKENDS)
@parametrize("context", [parallel_config, parallel_backend])
def test_backend_nesting_level(context, outer_backend, inner_backend):
    # Check that the nesting level for the backend is correctly set
    check_nesting_level(context, outer_backend, 0)

    Parallel(n_jobs=2, backend=outer_backend)(
        delayed(check_nesting_level)(context, inner_backend, 1) for _ in range(10)
    )

    with context(inner_backend, n_jobs=2):
        Parallel()(
            delayed(check_nesting_level)(context, inner_backend, 1) for _ in range(10)
        )


@with_multiprocessing
@parametrize("context", [parallel_config, parallel_backend])
@parametrize("with_retrieve_callback", [True, False])
def test_retrieval_context(context, with_retrieve_callback):
    import contextlib

    class MyBackend(ThreadingBackend):
        i = 0
        supports_retrieve_callback = with_retrieve_callback

        @contextlib.contextmanager
        def retrieval_context(self):
            self.i += 1
            yield

    register_parallel_backend("retrieval", MyBackend)

    def nested_call(n):
        return Parallel(n_jobs=2)(delayed(id)(i) for i in range(n))

    with context("retrieval") as ctx:
        Parallel(n_jobs=2)(delayed(nested_call)(i) for i in range(5))
        if context is parallel_config:
            assert ctx["backend"].i == 1
        if context is parallel_backend:
            assert ctx[0].i == 1


###############################################################################
# Test helpers


@parametrize("batch_size", [0, -1, 1.42])
def test_invalid_batch_size(batch_size):
    with raises(ValueError):
        Parallel(batch_size=batch_size)


@parametrize(
    "n_tasks, n_jobs, pre_dispatch, batch_size",
    [
        (2, 2, "all", "auto"),
        (2, 2, "n_jobs", "auto"),
        (10, 2, "n_jobs", "auto"),
        (517, 2, "n_jobs", "auto"),
        (10, 2, "n_jobs", "auto"),
        (10, 4, "n_jobs", "auto"),
        (200, 12, "n_jobs", "auto"),
        (25, 12, "2 * n_jobs", 1),
        (250, 12, "all", 1),
        (250, 12, "2 * n_jobs", 7),
        (200, 12, "2 * n_jobs", "auto"),
    ],
)
def test_dispatch_race_condition(n_tasks, n_jobs, pre_dispatch, batch_size):
    # Check that using (async-)dispatch does not yield a race condition on the
    # iterable generator that is not thread-safe natively.
    # This is a non-regression test for the "Pool seems closed" class of error
    params = {"n_jobs": n_jobs, "pre_dispatch": pre_dispatch, "batch_size": batch_size}
    expected = [square(i) for i in range(n_tasks)]
    results = Parallel(**params)(delayed(square)(i) for i in range(n_tasks))
    assert results == expected


@with_multiprocessing
def test_default_mp_context():
    mp_start_method = mp.get_start_method()
    p = Parallel(n_jobs=2, backend="multiprocessing")
    context = p._backend_kwargs.get("context")
    start_method = context.get_start_method()
    assert start_method == mp_start_method


@with_numpy
@with_multiprocessing
@parametrize("backend", PROCESS_BACKENDS)
def test_no_blas_crash_or_freeze_with_subprocesses(backend):
    if backend == "multiprocessing":
        # Use the spawn backend that is both robust and available on all
        # platforms
        backend = mp.get_context("spawn")

    # Check that on recent Python version, the 'spawn' start method can make
    # it possible to use multiprocessing in conjunction of any BLAS
    # implementation that happens to be used by numpy with causing a freeze or
    # a crash
    rng = np.random.RandomState(42)

    # call BLAS DGEMM to force the initialization of the internal thread-pool
    # in the main process
    a = rng.randn(1000, 1000)
    np.dot(a, a.T)

    # check that the internal BLAS thread-pool is not in an inconsistent state
    # in the worker processes managed by multiprocessing
    Parallel(n_jobs=2, backend=backend)(delayed(np.dot)(a, a.T) for i in range(2))


UNPICKLABLE_CALLABLE_SCRIPT_TEMPLATE_NO_MAIN = """\
from joblib import Parallel, delayed

def square(x):
    return x ** 2

backend = "{}"
if backend == "spawn":
    from multiprocessing import get_context
    backend = get_context(backend)

print(Parallel(n_jobs=2, backend=backend)(
      delayed(square)(i) for i in range(5)))
"""


@with_multiprocessing
@parametrize("backend", PROCESS_BACKENDS)
def test_parallel_with_interactively_defined_functions(backend):
    # When using the "-c" flag, interactive functions defined in __main__
    # should work with any backend.
    if backend == "multiprocessing" and mp.get_start_method() != "fork":
        pytest.skip(
            "Require fork start method to use interactively defined "
            "functions with multiprocessing."
        )
    code = UNPICKLABLE_CALLABLE_SCRIPT_TEMPLATE_NO_MAIN.format(backend)
    check_subprocess_call(
        [sys.executable, "-c", code], timeout=10, stdout_regex=r"\[0, 1, 4, 9, 16\]"
    )


UNPICKLABLE_CALLABLE_SCRIPT_TEMPLATE_MAIN = """\
import sys
# Make sure that joblib is importable in the subprocess launching this
# script. This is needed in case we run the tests from the joblib root
# folder without having installed joblib
sys.path.insert(0, {joblib_root_folder!r})

from joblib import Parallel, delayed

def run(f, x):
    return f(x)

{define_func}

if __name__ == "__main__":
    backend = "{backend}"
    if backend == "spawn":
        from multiprocessing import get_context
        backend = get_context(backend)

    callable_position = "{callable_position}"
    if callable_position == "delayed":
        print(Parallel(n_jobs=2, backend=backend)(
                delayed(square)(i) for i in range(5)))
    elif callable_position == "args":
        print(Parallel(n_jobs=2, backend=backend)(
                delayed(run)(square, i) for i in range(5)))
    else:
        print(Parallel(n_jobs=2, backend=backend)(
                delayed(run)(f=square, x=i) for i in range(5)))
"""

SQUARE_MAIN = """\
def square(x):
    return x ** 2
"""
SQUARE_LOCAL = """\
def gen_square():
    def square(x):
        return x ** 2
    return square
square = gen_square()
"""
SQUARE_LAMBDA = """\
square = lambda x: x ** 2
"""


@with_multiprocessing
@parametrize("backend", PROCESS_BACKENDS + ([] if mp is None else ["spawn"]))
@parametrize("define_func", [SQUARE_MAIN, SQUARE_LOCAL, SQUARE_LAMBDA])
@parametrize("callable_position", ["delayed", "args", "kwargs"])
def test_parallel_with_unpicklable_functions_in_args(
    backend, define_func, callable_position, tmpdir
):
    if backend in ["multiprocessing", "spawn"] and (
        define_func != SQUARE_MAIN or sys.platform == "win32"
    ):
        pytest.skip("Not picklable with pickle")
    code = UNPICKLABLE_CALLABLE_SCRIPT_TEMPLATE_MAIN.format(
        define_func=define_func,
        backend=backend,
        callable_position=callable_position,
        joblib_root_folder=os.path.dirname(os.path.dirname(joblib.__file__)),
    )
    code_file = tmpdir.join("unpicklable_func_script.py")
    code_file.write(code)
    check_subprocess_call(
        [sys.executable, code_file.strpath],
        timeout=10,
        stdout_regex=r"\[0, 1, 4, 9, 16\]",
    )


INTERACTIVE_DEFINED_FUNCTION_AND_CLASS_SCRIPT_CONTENT = """\
import sys
import faulthandler
# Make sure that joblib is importable in the subprocess launching this
# script. This is needed in case we run the tests from the joblib root
# folder without having installed joblib
sys.path.insert(0, {joblib_root_folder!r})

from joblib import Parallel, delayed
from functools import partial

class MyClass:
    '''Class defined in the __main__ namespace'''
    def __init__(self, value):
        self.value = value


def square(x, ignored=None, ignored2=None):
    '''Function defined in the __main__ namespace'''
    return x.value ** 2


square2 = partial(square, ignored2='something')

# Here, we do not need the `if __name__ == "__main__":` safeguard when
# using the default `loky` backend (even on Windows).

# To make debugging easier
faulthandler.dump_traceback_later(30, exit=True)

# The following baroque function call is meant to check that joblib
# introspection rightfully uses cloudpickle instead of the (faster) pickle
# module of the standard library when necessary. In particular cloudpickle is
# necessary for functions and instances of classes interactively defined in the
# __main__ module.

print(Parallel(backend="loky", n_jobs=2)(
    delayed(square2)(MyClass(i), ignored=[dict(a=MyClass(1))])
    for i in range(5)
))
""".format(joblib_root_folder=os.path.dirname(os.path.dirname(joblib.__file__)))


@with_multiprocessing
def test_parallel_with_interactively_defined_functions_loky(tmpdir):
    # loky accepts interactive functions defined in __main__ and does not
    # require if __name__ == '__main__' even when the __main__ module is
    # defined by the result of the execution of a filesystem script.
    script = tmpdir.join("joblib_interactively_defined_function.py")
    script.write(INTERACTIVE_DEFINED_FUNCTION_AND_CLASS_SCRIPT_CONTENT)
    check_subprocess_call(
        [sys.executable, script.strpath],
        stdout_regex=r"\[0, 1, 4, 9, 16\]",
        timeout=None,  # rely on faulthandler to kill the process
    )


INTERACTIVELY_DEFINED_SUBCLASS_WITH_METHOD_SCRIPT_CONTENT = """\
import sys
# Make sure that joblib is importable in the subprocess launching this
# script. This is needed in case we run the tests from the joblib root
# folder without having installed joblib
sys.path.insert(0, {joblib_root_folder!r})

from joblib import Parallel, delayed, hash
import multiprocessing as mp
mp.util.log_to_stderr(5)

class MyList(list):
    '''MyList is interactively defined by MyList.append is a built-in'''
    def __hash__(self):
        # XXX: workaround limitation in cloudpickle
        return hash(self).__hash__()

l = MyList()

print(Parallel(backend="loky", n_jobs=2)(
    delayed(l.append)(i) for i in range(3)
))
""".format(joblib_root_folder=os.path.dirname(os.path.dirname(joblib.__file__)))


@with_multiprocessing
def test_parallel_with_interactively_defined_bound_method_loky(tmpdir):
    script = tmpdir.join("joblib_interactive_bound_method_script.py")
    script.write(INTERACTIVELY_DEFINED_SUBCLASS_WITH_METHOD_SCRIPT_CONTENT)
    check_subprocess_call(
        [sys.executable, script.strpath],
        stdout_regex=r"\[None, None, None\]",
        stderr_regex=r"LokyProcess",
        timeout=15,
    )


def test_parallel_with_exhausted_iterator():
    exhausted_iterator = iter([])
    assert Parallel(n_jobs=2)(exhausted_iterator) == []


def check_memmap(a):
    if not isinstance(a, np.memmap):
        raise TypeError("Expected np.memmap instance, got %r", type(a))
    return a.copy()  # return a regular array instead of a memmap


@with_numpy
@with_multiprocessing
@parametrize("backend", PROCESS_BACKENDS)
def test_auto_memmap_on_arrays_from_generator(backend):
    # Non-regression test for a problem with a bad interaction between the
    # GC collecting arrays recently created during iteration inside the
    # parallel dispatch loop and the auto-memmap feature of Parallel.
    # See: https://github.com/joblib/joblib/pull/294
    def generate_arrays(n):
        for i in range(n):
            yield np.ones(10, dtype=np.float32) * i

    # Use max_nbytes=1 to force the use of memory-mapping even for small
    # arrays
    results = Parallel(n_jobs=2, max_nbytes=1, backend=backend)(
        delayed(check_memmap)(a) for a in generate_arrays(100)
    )
    for result, expected in zip(results, generate_arrays(len(results))):
        np.testing.assert_array_equal(expected, result)

    # Second call to force loky to adapt the executor by growing the number
    # of worker processes. This is a non-regression test for:
    # https://github.com/joblib/joblib/issues/629.
    results = Parallel(n_jobs=4, max_nbytes=1, backend=backend)(
        delayed(check_memmap)(a) for a in generate_arrays(100)
    )
    for result, expected in zip(results, generate_arrays(len(results))):
        np.testing.assert_array_equal(expected, result)


def identity(arg):
    return arg


@with_numpy
@with_multiprocessing
def test_memmap_with_big_offset(tmpdir):
    fname = tmpdir.join("test.mmap").strpath
    size = mmap.ALLOCATIONGRANULARITY
    obj = [np.zeros(size, dtype="uint8"), np.ones(size, dtype="uint8")]
    dump(obj, fname)
    memmap = load(fname, mmap_mode="r")
    (result,) = Parallel(n_jobs=2)(delayed(identity)(memmap) for _ in [0])
    assert isinstance(memmap[1], np.memmap)
    assert memmap[1].offset > size
    np.testing.assert_array_equal(obj, result)


def test_warning_about_timeout_not_supported_by_backend():
    with warnings.catch_warnings(record=True) as warninfo:
        Parallel(n_jobs=1, timeout=1)(delayed(square)(i) for i in range(50))
    assert len(warninfo) == 1
    w = warninfo[0]
    assert isinstance(w.message, UserWarning)
    assert str(w.message) == (
        "The backend class 'SequentialBackend' does not support timeout. "
        "You have set 'timeout=1' in Parallel but the 'timeout' parameter "
        "will not be used."
    )


def set_list_value(input_list, index, value):
    input_list[index] = value
    return value


@pytest.mark.parametrize("n_jobs", [1, 2, 4])
def test_parallel_return_order_with_return_as_generator_parameter(n_jobs):
    # This test inserts values in a list in some expected order
    # in sequential computing, and then checks that this order has been
    # respected by Parallel output generator.
    input_list = [0] * 5
    result = Parallel(n_jobs=n_jobs, return_as="generator", backend="threading")(
        delayed(set_list_value)(input_list, i, i) for i in range(5)
    )

    # Ensure that all the tasks are completed before checking the result
    result = list(result)

    assert all(v == r for v, r in zip(input_list, result))


def _sqrt_with_delay(e, delay):
    if delay:
        sleep(30)
    return sqrt(e)


# Use a private function so it can also be called for the dask backend in
# test_dask.py without triggering the test twice.
# We isolate the test with the dask backend to simplify optional deps
# management and leaking environment variables.
def _test_parallel_unordered_generator_returns_fastest_first(backend, n_jobs):
    # This test submits 10 tasks, but the second task is super slow. This test
    # checks that the 9 other tasks return before the slow task is done, when
    # `return_as` parameter is set to `'generator_unordered'`
    result = Parallel(n_jobs=n_jobs, return_as="generator_unordered", backend=backend)(
        delayed(_sqrt_with_delay)(i**2, (i == 1)) for i in range(10)
    )

    quickly_returned = sorted(next(result) for _ in range(9))

    expected_quickly_returned = [0] + list(range(2, 10))

    assert all(v == r for v, r in zip(expected_quickly_returned, quickly_returned))

    del result


@pytest.mark.parametrize("n_jobs", [2, 4])
# NB: for this test to work, the backend must be allowed to process tasks
# concurrently, so at least two jobs with a non-sequential backend are
# mandatory.
@with_multiprocessing
@parametrize("backend", set(RETURN_GENERATOR_BACKENDS) - {"sequential"})
def test_parallel_unordered_generator_returns_fastest_first(backend, n_jobs):
    _test_parallel_unordered_generator_returns_fastest_first(backend, n_jobs)


@parametrize("backend", ALL_VALID_BACKENDS)
@parametrize("n_jobs", [1, 2, -2, -1])
def test_abort_backend(n_jobs, backend):
    delays = ["a"] + [10] * 100
    with raises(TypeError):
        t_start = time.time()
        Parallel(n_jobs=n_jobs, backend=backend)(delayed(time.sleep)(i) for i in delays)
    dt = time.time() - t_start
    assert dt < 20


def get_large_object(arg):
    result = np.ones(int(5 * 1e5), dtype=bool)
    result[0] = False
    return result


# Use a private function so it can also be called for the dask backend in
# test_dask.py without triggering the test twice.
# We isolate the test with the dask backend to simplify optional deps
# management and leaking environment variables.
def _test_deadlock_with_generator(backend, return_as, n_jobs):
    # Non-regression test for a race condition in the backends when the pickler
    # is delayed by a large object.
    with Parallel(n_jobs=n_jobs, backend=backend, return_as=return_as) as parallel:
        result = parallel(delayed(get_large_object)(i) for i in range(10))
        next(result)
        next(result)
        del result


@with_numpy
@parametrize("backend", RETURN_GENERATOR_BACKENDS)
@parametrize("return_as", ["generator", "generator_unordered"])
@parametrize("n_jobs", [1, 2, -2, -1])
def test_deadlock_with_generator(backend, return_as, n_jobs):
    _test_deadlock_with_generator(backend, return_as, n_jobs)


@parametrize("backend", RETURN_GENERATOR_BACKENDS)
@parametrize("return_as", ["generator", "generator_unordered"])
@parametrize("n_jobs", [1, 2, -2, -1])
def test_multiple_generator_call(backend, return_as, n_jobs):
    # Non-regression test that ensures the dispatch of the tasks starts
    # immediately when Parallel.__call__ is called. This test relies on the
    # assumption that only one generator can be submitted at a time.
    with raises(RuntimeError, match="This Parallel instance is already running"):
        parallel = Parallel(n_jobs, backend=backend, return_as=return_as)
        g = parallel(delayed(sleep)(1) for _ in range(10))  # noqa: F841
        t_start = time.time()
        gen2 = parallel(delayed(id)(i) for i in range(100))  # noqa: F841

    # Make sure that the error is raised quickly
    assert time.time() - t_start < 2, (
        "The error should be raised immediately when submitting a new task "
        "but it took more than 2s."
    )

    del g


@parametrize("backend", RETURN_GENERATOR_BACKENDS)
@parametrize("return_as", ["generator", "generator_unordered"])
@parametrize("n_jobs", [1, 2, -2, -1])
def test_multiple_generator_call_managed(backend, return_as, n_jobs):
    # Non-regression test that ensures the dispatch of the tasks starts
    # immediately when Parallel.__call__ is called. This test relies on the
    # assumption that only one generator can be submitted at a time.
    with Parallel(n_jobs, backend=backend, return_as=return_as) as parallel:
        g = parallel(delayed(sleep)(10) for _ in range(10))  # noqa: F841
        t_start = time.time()
        with raises(RuntimeError, match="This Parallel instance is already running"):
            g2 = parallel(delayed(id)(i) for i in range(100))  # noqa: F841

        # Make sure that the error is raised quickly
        assert time.time() - t_start < 2, (
            "The error should be raised immediately when submitting a new task "
            "but it took more than 2s."
        )

    del g


@parametrize("backend", RETURN_GENERATOR_BACKENDS)
@parametrize("return_as_1", ["generator", "generator_unordered"])
@parametrize("return_as_2", ["generator", "generator_unordered"])
@parametrize("n_jobs", [1, 2, -2, -1])
def test_multiple_generator_call_separated(backend, return_as_1, return_as_2, n_jobs):
    # Check that for separated Parallel, both tasks are correctly returned.
    g = Parallel(n_jobs, backend=backend, return_as=return_as_1)(
        delayed(sqrt)(i**2) for i in range(10)
    )
    g2 = Parallel(n_jobs, backend=backend, return_as=return_as_2)(
        delayed(sqrt)(i**2) for i in range(10, 20)
    )

    if return_as_1 == "generator_unordered":
        g = sorted(g)

    if return_as_2 == "generator_unordered":
        g2 = sorted(g2)

    assert all(res == i for res, i in zip(g, range(10)))
    assert all(res == i for res, i in zip(g2, range(10, 20)))


@parametrize(
    "backend, error",
    [
        ("loky", True),
        ("threading", False),
        ("sequential", False),
    ],
)
@parametrize("return_as_1", ["generator", "generator_unordered"])
@parametrize("return_as_2", ["generator", "generator_unordered"])
def test_multiple_generator_call_separated_gc(backend, return_as_1, return_as_2, error):
    if (backend == "loky") and (mp is None):
        pytest.skip("Requires multiprocessing")

    # Check that in loky, only one call can be run at a time with
    # a single executor.
    parallel = Parallel(2, backend=backend, return_as=return_as_1)
    g = parallel(delayed(sleep)(10) for i in range(10))
    g_wr = weakref.finalize(g, lambda: print("Generator collected"))
    ctx = (
        raises(RuntimeError, match="The executor underlying Parallel")
        if error
        else nullcontext()
    )
    with ctx:
        # For loky, this call will raise an error as the gc of the previous
        # generator will shutdown the shared executor.
        # For the other backends, as the worker pools are not shared between
        # the two calls, this should proceed correctly.
        t_start = time.time()
        g = Parallel(2, backend=backend, return_as=return_as_2)(
            delayed(sqrt)(i**2) for i in range(10, 20)
        )

        if return_as_2 == "generator_unordered":
            g = sorted(g)

        assert all(res == i for res, i in zip(g, range(10, 20)))

    assert time.time() - t_start < 5

    # Make sure that the computation are stopped for the gc'ed generator
    retry = 0
    while g_wr.alive and retry < 3:
        retry += 1
        time.sleep(0.5)
    assert time.time() - t_start < 5

    if parallel._effective_n_jobs() != 1:
        # check that the first parallel object is aborting (the final _aborted
        # state might be delayed).
        assert parallel._aborting


@with_numpy
@with_multiprocessing
@parametrize("backend", PROCESS_BACKENDS)
def test_memmapping_leaks(backend, tmpdir):
    # Non-regression test for memmapping backends. Ensure that the data
    # does not stay too long in memory
    tmpdir = tmpdir.strpath

    # Use max_nbytes=1 to force the use of memory-mapping even for small
    # arrays
    with Parallel(n_jobs=2, max_nbytes=1, backend=backend, temp_folder=tmpdir) as p:
        p(delayed(check_memmap)(a) for a in [np.random.random(10)] * 2)

        # The memmap folder should not be clean in the context scope
        assert len(os.listdir(tmpdir)) > 0

    # Make sure that the shared memory is cleaned at the end when we exit
    # the context
    for _ in range(100):
        if not os.listdir(tmpdir):
            break
        sleep(0.1)
    else:
        raise AssertionError("temporary directory of Parallel was not removed")

    # Make sure that the shared memory is cleaned at the end of a call
    p = Parallel(n_jobs=2, max_nbytes=1, backend=backend)
    p(delayed(check_memmap)(a) for a in [np.random.random(10)] * 2)

    for _ in range(100):
        if not os.listdir(tmpdir):
            break
        sleep(0.1)
    else:
        raise AssertionError("temporary directory of Parallel was not removed")


@parametrize(
    "backend", ([None, "threading"] if mp is None else [None, "loky", "threading"])
)
def test_lambda_expression(backend):
    # cloudpickle is used to pickle delayed callables
    results = Parallel(n_jobs=2, backend=backend)(
        delayed(lambda x: x**2)(i) for i in range(10)
    )
    assert results == [i**2 for i in range(10)]


@with_multiprocessing
@parametrize("backend", PROCESS_BACKENDS)
def test_backend_batch_statistics_reset(backend):
    """Test that a parallel backend correctly resets its batch statistics."""
    n_jobs = 2
    n_inputs = 500
    task_time = 2.0 / n_inputs

    p = Parallel(verbose=10, n_jobs=n_jobs, backend=backend)
    p(delayed(time.sleep)(task_time) for i in range(n_inputs))
    assert p._backend._effective_batch_size == p._backend._DEFAULT_EFFECTIVE_BATCH_SIZE
    assert (
        p._backend._smoothed_batch_duration
        == p._backend._DEFAULT_SMOOTHED_BATCH_DURATION
    )

    p(delayed(time.sleep)(task_time) for i in range(n_inputs))
    assert p._backend._effective_batch_size == p._backend._DEFAULT_EFFECTIVE_BATCH_SIZE
    assert (
        p._backend._smoothed_batch_duration
        == p._backend._DEFAULT_SMOOTHED_BATCH_DURATION
    )


@with_multiprocessing
@parametrize("context", [parallel_config, parallel_backend])
def test_backend_hinting_and_constraints(context):
    for n_jobs in [1, 2, -1]:
        assert type(Parallel(n_jobs=n_jobs)._backend) is get_default_backend_instance()

        p = Parallel(n_jobs=n_jobs, prefer="threads")
        assert type(p._backend) is ThreadingBackend

        p = Parallel(n_jobs=n_jobs, prefer="processes")
        assert type(p._backend) is LokyBackend

        p = Parallel(n_jobs=n_jobs, require="sharedmem")
        assert type(p._backend) is ThreadingBackend

    # Explicit backend selection can override backend hinting although it
    # is useless to pass a hint when selecting a backend.
    p = Parallel(n_jobs=2, backend="loky", prefer="threads")
    assert type(p._backend) is LokyBackend

    with context("loky", n_jobs=2):
        # Explicit backend selection by the user with the context manager
        # should be respected when combined with backend hints only.
        p = Parallel(prefer="threads")
        assert type(p._backend) is LokyBackend
        assert p.n_jobs == 2

    with context("loky", n_jobs=2):
        # Locally hard-coded n_jobs value is respected.
        p = Parallel(n_jobs=3, prefer="threads")
        assert type(p._backend) is LokyBackend
        assert p.n_jobs == 3

    with context("loky", n_jobs=2):
        # Explicit backend selection by the user with the context manager
        # should be ignored when the Parallel call has hard constraints.
        # In this case, the default backend that supports shared mem is
        # used an the default number of processes is used.
        p = Parallel(require="sharedmem")
        assert type(p._backend) is ThreadingBackend
        assert p.n_jobs == 1

    with context("loky", n_jobs=2):
        p = Parallel(n_jobs=3, require="sharedmem")
        assert type(p._backend) is ThreadingBackend
        assert p.n_jobs == 3


@parametrize("n_jobs", [1, 2])
@parametrize("prefer", [None, "processes", "threads"])
def test_backend_hinting_always_running(n_jobs, prefer):
    # Check that the backend hinting never results in an error
    # Non-regression test for https://github.com/joblib/joblib/issues/1720
    expected_results = [i**2 for i in range(10)]

    results = Parallel(n_jobs=n_jobs, prefer=prefer)(
        delayed(square)(i) for i in range(10)
    )
    assert results == expected_results

    with parallel_config(prefer=prefer, n_jobs=n_jobs):
        results = Parallel()(delayed(square)(i) for i in range(10))
    assert results == expected_results


@parametrize("context", [parallel_config, parallel_backend])
def test_backend_hinting_and_constraints_with_custom_backends(capsys, context):
    # Custom backends can declare that they use threads and have shared memory
    # semantics:
    class MyCustomThreadingBackend(ParallelBackendBase):
        supports_sharedmem = True
        use_threads = True

        def apply_async(self):
            pass

        def effective_n_jobs(self, n_jobs):
            return n_jobs

    with context(MyCustomThreadingBackend()):
        p = Parallel(n_jobs=2, prefer="processes")  # ignored
        assert type(p._backend) is MyCustomThreadingBackend

        p = Parallel(n_jobs=2, require="sharedmem")
        assert type(p._backend) is MyCustomThreadingBackend

    class MyCustomProcessingBackend(ParallelBackendBase):
        supports_sharedmem = False
        use_threads = False

        def apply_async(self):
            pass

        def effective_n_jobs(self, n_jobs):
            return n_jobs

    with context(MyCustomProcessingBackend()):
        p = Parallel(n_jobs=2, prefer="processes")
        assert type(p._backend) is MyCustomProcessingBackend

        out, err = capsys.readouterr()
        assert out == ""
        assert err == ""

        p = Parallel(n_jobs=2, require="sharedmem", verbose=10)
        assert type(p._backend) is ThreadingBackend

        out, err = capsys.readouterr()
        expected = (
            "Using ThreadingBackend as joblib backend "
            "instead of MyCustomProcessingBackend as the latter "
            "does not provide shared memory semantics."
        )
        assert out.strip() == expected
        assert err == ""

    with raises(ValueError):
        Parallel(backend=MyCustomProcessingBackend(), require="sharedmem")


def test_invalid_backend_hinting_and_constraints():
    with raises(ValueError):
        Parallel(prefer="invalid")

    with raises(ValueError):
        Parallel(require="invalid")

    with raises(ValueError):
        # It is inconsistent to prefer process-based parallelism while
        # requiring shared memory semantics.
        Parallel(prefer="processes", require="sharedmem")

    if mp is not None:
        # It is inconsistent to ask explicitly for a process-based
        # parallelism while requiring shared memory semantics.
        with raises(ValueError):
            Parallel(backend="loky", require="sharedmem")
        with raises(ValueError):
            Parallel(backend="multiprocessing", require="sharedmem")


def _recursive_backend_info(limit=3, **kwargs):
    """Perform nested parallel calls and introspect the backend on the way"""

    with Parallel(n_jobs=2) as p:
        this_level = [(type(p._backend).__name__, p._backend.nesting_level)]
        if limit == 0:
            return this_level
        results = p(
            delayed(_recursive_backend_info)(limit=limit - 1, **kwargs)
            for i in range(1)
        )
        return this_level + results[0]


@with_multiprocessing
@parametrize("backend", ["loky", "threading"])
@parametrize("context", [parallel_config, parallel_backend])
def test_nested_parallelism_limit(context, backend):
    with context(backend, n_jobs=2):
        backend_types_and_levels = _recursive_backend_info()

    top_level_backend_type = backend.title() + "Backend"
    expected_types_and_levels = [
        (top_level_backend_type, 0),
        ("ThreadingBackend", 1),
        ("SequentialBackend", 2),
        ("SequentialBackend", 2),
    ]
    assert backend_types_and_levels == expected_types_and_levels


def _recursive_parallel(nesting_limit=None):
    """A horrible function that does recursive parallel calls"""
    return Parallel()(delayed(_recursive_parallel)() for i in range(2))


@pytest.mark.no_cover
@parametrize("context", [parallel_config, parallel_backend])
@parametrize("backend", (["threading"] if mp is None else ["loky", "threading"]))
def test_thread_bomb_mitigation(context, backend):
    # Test that recursive parallelism raises a recursion rather than
    # saturating the operating system resources by creating a unbounded number
    # of threads.
    with context(backend, n_jobs=2):
        with raises(BaseException) as excinfo:
            _recursive_parallel()
    exc = excinfo.value
    if backend == "loky":
        # Local import because loky may not be importable for lack of
        # multiprocessing
        from joblib.externals.loky.process_executor import TerminatedWorkerError  # noqa

        if isinstance(exc, (TerminatedWorkerError, PicklingError)):
            # The recursion exception can itself cause an error when
            # pickling it to be send back to the parent process. In this
            # case the worker crashes but the original traceback is still
            # printed on stderr. This could be improved but does not seem
            # simple to do and this is not critical for users (as long
            # as there is no process or thread bomb happening).
            pytest.xfail("Loky worker crash when serializing RecursionError")

    assert isinstance(exc, RecursionError)


def _run_parallel_sum():
    env_vars = {}
    for var in [
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "NUMBA_NUM_THREADS",
        "ENABLE_IPC",
    ]:
        env_vars[var] = os.environ.get(var)
    return env_vars, parallel_sum(100)


@parametrize("backend", ([None, "loky"] if mp is not None else [None]))
@skipif(parallel_sum is None, reason="Need OpenMP helper compiled")
def test_parallel_thread_limit(backend):
    results = Parallel(n_jobs=2, backend=backend)(
        delayed(_run_parallel_sum)() for _ in range(2)
    )
    expected_num_threads = max(cpu_count() // 2, 1)
    for worker_env_vars, omp_num_threads in results:
        assert omp_num_threads == expected_num_threads
        for name, value in worker_env_vars.items():
            if name.endswith("_THREADS"):
                assert value == str(expected_num_threads)
            else:
                assert name == "ENABLE_IPC"
                assert value == "1"


@parametrize("context", [parallel_config, parallel_backend])
@skipif(distributed is not None, reason="This test requires dask")
def test_dask_backend_when_dask_not_installed(context):
    with raises(ValueError, match="Please install dask"):
        context("dask")


@parametrize("context", [parallel_config, parallel_backend])
def test_zero_worker_backend(context):
    # joblib.Parallel should reject with an explicit error message parallel
    # backends that have no worker.
    class ZeroWorkerBackend(ThreadingBackend):
        def configure(self, *args, **kwargs):
            return 0

        def apply_async(self, func, callback=None):  # pragma: no cover
            raise TimeoutError("No worker available")

        def effective_n_jobs(self, n_jobs):  # pragma: no cover
            return 0

    expected_msg = "ZeroWorkerBackend has no active worker"
    with context(ZeroWorkerBackend()):
        with pytest.raises(RuntimeError, match=expected_msg):
            Parallel(n_jobs=2)(delayed(id)(i) for i in range(2))


def test_globals_update_at_each_parallel_call():
    # This is a non-regression test related to joblib issues #836 and #833.
    # Cloudpickle versions between 0.5.4 and 0.7 introduced a bug where global
    # variables changes in a parent process between two calls to
    # joblib.Parallel would not be propagated into the workers.
    global MY_GLOBAL_VARIABLE
    MY_GLOBAL_VARIABLE = "original value"

    def check_globals():
        global MY_GLOBAL_VARIABLE
        return MY_GLOBAL_VARIABLE

    assert check_globals() == "original value"

    workers_global_variable = Parallel(n_jobs=2)(
        delayed(check_globals)() for i in range(2)
    )
    assert set(workers_global_variable) == {"original value"}

    # Change the value of MY_GLOBAL_VARIABLE, and make sure this change gets
    # propagated into the workers environment
    MY_GLOBAL_VARIABLE = "changed value"
    assert check_globals() == "changed value"

    workers_global_variable = Parallel(n_jobs=2)(
        delayed(check_globals)() for i in range(2)
    )
    assert set(workers_global_variable) == {"changed value"}


##############################################################################
# Test environment variable in child env, in particular for limiting
# the maximal number of threads in C-library threadpools.
#


def _check_numpy_threadpool_limits():
    import numpy as np

    # Let's call BLAS on a Matrix Matrix multiplication with dimensions large
    # enough to ensure that the threadpool managed by the underlying BLAS
    # implementation is actually used so as to force its initialization.
    a = np.random.randn(100, 100)
    np.dot(a, a)
    threadpoolctl = pytest.importorskip("threadpoolctl")
    return threadpoolctl.threadpool_info()


def _parent_max_num_threads_for(child_module, parent_info):
    for parent_module in parent_info:
        if parent_module["filepath"] == child_module["filepath"]:
            return parent_module["num_threads"]
    raise ValueError(
        "An unexpected module was loaded in child:\n{}".format(child_module)
    )


def check_child_num_threads(workers_info, parent_info, num_threads):
    # Check that the number of threads reported in workers_info is consistent
    # with the expectation. We need to be careful to handle the cases where
    # the requested number of threads is below max_num_thread for the library.
    for child_threadpool_info in workers_info:
        for child_module in child_threadpool_info:
            parent_max_num_threads = _parent_max_num_threads_for(
                child_module, parent_info
            )
            expected = {min(num_threads, parent_max_num_threads), num_threads}
            assert child_module["num_threads"] in expected


@with_numpy
@with_multiprocessing
@parametrize("n_jobs", [2, 4, -2, -1])
def test_threadpool_limitation_in_child_loky(n_jobs):
    # Check that the protection against oversubscription in workers is working
    # using threadpoolctl functionalities.

    # Skip this test if numpy is not linked to a BLAS library
    parent_info = _check_numpy_threadpool_limits()
    if len(parent_info) == 0:
        pytest.skip(reason="Need a version of numpy linked to BLAS")

    workers_threadpool_infos = Parallel(backend="loky", n_jobs=n_jobs)(
        delayed(_check_numpy_threadpool_limits)() for i in range(2)
    )

    n_jobs = effective_n_jobs(n_jobs)
    if n_jobs == 1:
        expected_child_num_threads = parent_info[0]["num_threads"]
    else:
        expected_child_num_threads = max(cpu_count() // n_jobs, 1)

    check_child_num_threads(
        workers_threadpool_infos, parent_info, expected_child_num_threads
    )


@with_numpy
@with_multiprocessing
@parametrize("inner_max_num_threads", [1, 2, 4, None])
@parametrize("n_jobs", [2, -1])
@parametrize("context", [parallel_config, parallel_backend])
def test_threadpool_limitation_in_child_context(context, n_jobs, inner_max_num_threads):
    # Check that the protection against oversubscription in workers is working
    # using threadpoolctl functionalities.

    # Skip this test if numpy is not linked to a BLAS library
    parent_info = _check_numpy_threadpool_limits()
    if len(parent_info) == 0:
        pytest.skip(reason="Need a version of numpy linked to BLAS")

    with context("loky", inner_max_num_threads=inner_max_num_threads):
        workers_threadpool_infos = Parallel(n_jobs=n_jobs)(
            delayed(_check_numpy_threadpool_limits)() for i in range(2)
        )

    n_jobs = effective_n_jobs(n_jobs)
    if n_jobs == 1:
        expected_child_num_threads = parent_info[0]["num_threads"]
    elif inner_max_num_threads is None:
        expected_child_num_threads = max(cpu_count() // n_jobs, 1)
    else:
        expected_child_num_threads = inner_max_num_threads

    check_child_num_threads(
        workers_threadpool_infos, parent_info, expected_child_num_threads
    )


@with_multiprocessing
@parametrize("n_jobs", [2, -1])
@parametrize("var_name", ["OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"])
@parametrize("context", [parallel_config, parallel_backend])
def test_threadpool_limitation_in_child_override(context, n_jobs, var_name):
    # Check that environment variables set by the user on the main process
    # always have the priority.

    # Skip this test if the process is run sequetially
    if effective_n_jobs(n_jobs) == 1:
        pytest.skip("Skip test when n_jobs == 1")

    # Clean up the existing executor because we change the environment of the
    # parent at runtime and it is not detected in loky intentionally.
    get_reusable_executor(reuse=True).shutdown()

    def _get_env(var_name):
        return os.environ.get(var_name)

    original_var_value = os.environ.get(var_name)
    try:
        os.environ[var_name] = "4"
        # Skip this test if numpy is not linked to a BLAS library
        results = Parallel(n_jobs=n_jobs)(delayed(_get_env)(var_name) for i in range(2))
        assert results == ["4", "4"]

        with context("loky", inner_max_num_threads=1):
            results = Parallel(n_jobs=n_jobs)(
                delayed(_get_env)(var_name) for i in range(2)
            )
        assert results == ["1", "1"]

    finally:
        if original_var_value is None:
            del os.environ[var_name]
        else:
            os.environ[var_name] = original_var_value


@with_multiprocessing
@parametrize("n_jobs", [2, 4, -1])
def test_loky_reuse_workers(n_jobs):
    # Non-regression test for issue #967 where the workers are not reused when
    # calling multiple Parallel loops.

    def parallel_call(n_jobs):
        x = range(10)
        Parallel(n_jobs=n_jobs)(delayed(sum)(x) for i in range(10))

    # Run a parallel loop and get the workers used for computations
    parallel_call(n_jobs)
    first_executor = get_reusable_executor(reuse=True)

    # Ensure that the workers are reused for the next calls, as the executor is
    # not restarted.
    for _ in range(10):
        parallel_call(n_jobs)
        executor = get_reusable_executor(reuse=True)
        assert executor == first_executor


def _set_initialized(status):
    status[os.getpid()] = "initialized"


def _check_status(status, n_jobs, wait_workers=False):
    pid = os.getpid()
    state = status.get(pid, None)
    assert state in ("initialized", "started"), (
        f"worker should have been in initialized state, got {state}"
    )
    if not wait_workers:
        return

    status[pid] = "started"
    # wait up to 30 seconds for the workers to be initialized
    deadline = time.time() + 30
    n_started = len([pid for pid, v in status.items() if v == "started"])
    while time.time() < deadline and n_started < n_jobs:
        time.sleep(0.1)
        n_started = len([pid for pid, v in status.items() if v == "started"])

    if time.time() >= deadline:
        raise TimeoutError("Waited more than 30s to start all the workers")

    return pid


@with_multiprocessing
@parametrize("n_jobs", [2, 4])
@parametrize("backend", PROCESS_BACKENDS)
@parametrize("context", [parallel_config, parallel_backend])
def test_initializer_context(n_jobs, backend, context):
    manager = mp.Manager()
    status = manager.dict()

    # pass the initializer to the backend context
    with context(
        backend=backend,
        n_jobs=n_jobs,
        initializer=_set_initialized,
        initargs=(status,),
    ):
        # check_status checks that the initializer is correctly call
        Parallel()(delayed(_check_status)(status, n_jobs) for i in range(100))


@with_multiprocessing
@parametrize("n_jobs", [2, 4])
@parametrize("backend", PROCESS_BACKENDS)
def test_initializer_parallel(n_jobs, backend):
    manager = mp.Manager()
    status = manager.dict()

    # pass the initializer directly to the Parallel call
    # check_status checks that the initializer is called in all tasks
    Parallel(
        backend=backend,
        n_jobs=n_jobs,
        initializer=_set_initialized,
        initargs=(status,),
    )(delayed(_check_status)(status, n_jobs) for i in range(100))


@with_multiprocessing
@pytest.mark.parametrize("n_jobs", [2, 4])
def test_initializer_reused(n_jobs):
    # Check that it is possible to pass initializer config via the `Parallel`
    # call directly and the worker are reused when the arguments are the same.
    n_repetitions = 3
    manager = mp.Manager()
    status = manager.dict()

    pids = set()
    for i in range(n_repetitions):
        results = Parallel(
            backend="loky",
            n_jobs=n_jobs,
            initializer=_set_initialized,
            initargs=(status,),
        )(
            delayed(_check_status)(status, n_jobs, wait_workers=True)
            for i in range(n_jobs)
        )
        pids = pids.union(set(results))
    assert len(pids) == n_jobs, (
        "The workers should be reused when the initializer is the same"
    )


@with_multiprocessing
@pytest.mark.parametrize("n_jobs", [2, 4])
def test_initializer_not_reused(n_jobs):
    # Check that when changing the initializer arguments, each parallel call uses its
    # own initializer args, independently of the previous calls, hence the loky workers
    # are not reused.
    n_repetitions = 3
    manager = mp.Manager()

    pids = set()
    for i in range(n_repetitions):
        status = manager.dict()
        results = Parallel(
            backend="loky",
            n_jobs=n_jobs,
            initializer=_set_initialized,
            initargs=(status,),
        )(
            delayed(_check_status)(status, n_jobs, wait_workers=True)
            for i in range(n_jobs)
        )
        pids = pids.union(set(results))
    assert len(pids) == n_repetitions * n_jobs, (
        "The workers should not be reused when the initializer arguments change"
    )

# === NexusCore/openenv\Lib\site-packages\google\generativeai\notebook\lib\llmfn_inputs_source.py ===
# -*- coding: utf-8 -*-
# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""LLMFnInputsSource."""
from __future__ import annotations

import abc
from typing import Callable, Mapping, Sequence


NormalizedInputsList = Sequence[Mapping[str, str]]


class LLMFnInputsSource(abc.ABC):
    """Abstract class representing a source of inputs for LLMFunction.

    This class could be extended with concrete implementations that read data
    from external sources, such as Google Sheets.
    """

    def __init__(self):
        self._cached_inputs: NormalizedInputsList | None = None
        self._display_status_fn: Callable[[], None] = lambda: None

    def to_normalized_inputs(self, suppress_status_msgs: bool = False) -> NormalizedInputsList:
        """Returns a sequence of normalized inputs.

        The return value is a sequence of dictionaries of (placeholder, value)
        pairs, e.g. [{"word": "hot"}, {"word: "cold"}, ....]

        These are used for keyword-substitution for prompts in LLMFunctions.

        Args:
          suppress_status_msgs: If True, suppress status messages regarding the
            input being read.

        Returns:
          A sequence of normalized inputs.
        """
        if self._cached_inputs is None:
            (
                self._cached_inputs,
                self._display_status_fn,
            ) = self._to_normalized_inputs_impl()
        if not suppress_status_msgs:
            self._display_status_fn()
        return self._cached_inputs

    @abc.abstractmethod
    def _to_normalized_inputs_impl(
        self,
    ) -> tuple[NormalizedInputsList, Callable[[], None]]:
        """Returns a tuple of NormalizedInputsList and a display function.

        The display function displays some status about the input (e.g. where
        it is read from). This way the status continues to be displayed
        even though the results are cached.
        """

# === NexusCore/openenv\Lib\site-packages\google\generativeai\notebook\lib\model.py ===
# -*- coding: utf-8 -*-
# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Abstract interface for models."""
from __future__ import annotations

import abc
import dataclasses
from typing import Sequence


@dataclasses.dataclass(frozen=True)
class ModelArguments:
    """Common arguments for models.

    Attributes:
      model: The model string to use. If None a default model will be selected.
      temperature: The temperature. Must be greater-than-or-equal-to zero.
      candidate_count: Number of candidates to return.
    """

    model: str | None = None
    temperature: float | None = None
    candidate_count: int | None = None


@dataclasses.dataclass
class ModelResults:
    """Results from calling AbstractModel.call_model()."""

    model_input: str
    text_results: Sequence[str]


class AbstractModel(abc.ABC):
    @abc.abstractmethod
    def call_model(
        self, model_input: str, model_args: ModelArguments | None = None
    ) -> ModelResults:
        """Executes the model."""


class EchoModel(AbstractModel):
    """Model that returns the original input.

    This is primarily used for testing.
    """

    def call_model(
        self, model_input: str, model_args: ModelArguments | None = None
    ) -> ModelResults:
        candidate_count = model_args.candidate_count if model_args else None
        if candidate_count is None:
            candidate_count = 1
        return ModelResults(
            model_input=model_input,
            text_results=[model_input] * candidate_count,
        )

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\key_binding\bindings\vi.py ===
# pylint: disable=function-redefined
from __future__ import annotations

import codecs
import string
from enum import Enum
from itertools import accumulate
from typing import Callable, Iterable, Tuple, TypeVar

from prompt_toolkit.application.current import get_app
from prompt_toolkit.buffer import Buffer, indent, reshape_text, unindent
from prompt_toolkit.clipboard import ClipboardData
from prompt_toolkit.document import Document
from prompt_toolkit.filters import (
    Always,
    Condition,
    Filter,
    has_arg,
    is_read_only,
    is_searching,
)
from prompt_toolkit.filters.app import (
    in_paste_mode,
    is_multiline,
    vi_digraph_mode,
    vi_insert_mode,
    vi_insert_multiple_mode,
    vi_mode,
    vi_navigation_mode,
    vi_recording_macro,
    vi_replace_mode,
    vi_replace_single_mode,
    vi_search_direction_reversed,
    vi_selection_mode,
    vi_waiting_for_text_object_mode,
)
from prompt_toolkit.input.vt100_parser import Vt100Parser
from prompt_toolkit.key_binding.digraphs import DIGRAPHS
from prompt_toolkit.key_binding.key_processor import KeyPress, KeyPressEvent
from prompt_toolkit.key_binding.vi_state import CharacterFind, InputMode
from prompt_toolkit.keys import Keys
from prompt_toolkit.search import SearchDirection
from prompt_toolkit.selection import PasteMode, SelectionState, SelectionType

from ..key_bindings import ConditionalKeyBindings, KeyBindings, KeyBindingsBase
from .named_commands import get_by_name

__all__ = [
    "load_vi_bindings",
    "load_vi_search_bindings",
]

E = KeyPressEvent

ascii_lowercase = string.ascii_lowercase

vi_register_names = ascii_lowercase + "0123456789"


class TextObjectType(Enum):
    EXCLUSIVE = "EXCLUSIVE"
    INCLUSIVE = "INCLUSIVE"
    LINEWISE = "LINEWISE"
    BLOCK = "BLOCK"


class TextObject:
    """
    Return struct for functions wrapped in ``text_object``.
    Both `start` and `end` are relative to the current cursor position.
    """

    def __init__(
        self, start: int, end: int = 0, type: TextObjectType = TextObjectType.EXCLUSIVE
    ):
        self.start = start
        self.end = end
        self.type = type

    @property
    def selection_type(self) -> SelectionType:
        if self.type == TextObjectType.LINEWISE:
            return SelectionType.LINES
        if self.type == TextObjectType.BLOCK:
            return SelectionType.BLOCK
        else:
            return SelectionType.CHARACTERS

    def sorted(self) -> tuple[int, int]:
        """
        Return a (start, end) tuple where start <= end.
        """
        if self.start < self.end:
            return self.start, self.end
        else:
            return self.end, self.start

    def operator_range(self, document: Document) -> tuple[int, int]:
        """
        Return a (start, end) tuple with start <= end that indicates the range
        operators should operate on.
        `buffer` is used to get start and end of line positions.

        This should return something that can be used in a slice, so the `end`
        position is *not* included.
        """
        start, end = self.sorted()
        doc = document

        if (
            self.type == TextObjectType.EXCLUSIVE
            and doc.translate_index_to_position(end + doc.cursor_position)[1] == 0
        ):
            # If the motion is exclusive and the end of motion is on the first
            # column, the end position becomes end of previous line.
            end -= 1
        if self.type == TextObjectType.INCLUSIVE:
            end += 1
        if self.type == TextObjectType.LINEWISE:
            # Select whole lines
            row, col = doc.translate_index_to_position(start + doc.cursor_position)
            start = doc.translate_row_col_to_index(row, 0) - doc.cursor_position
            row, col = doc.translate_index_to_position(end + doc.cursor_position)
            end = (
                doc.translate_row_col_to_index(row, len(doc.lines[row]))
                - doc.cursor_position
            )
        return start, end

    def get_line_numbers(self, buffer: Buffer) -> tuple[int, int]:
        """
        Return a (start_line, end_line) pair.
        """
        # Get absolute cursor positions from the text object.
        from_, to = self.operator_range(buffer.document)
        from_ += buffer.cursor_position
        to += buffer.cursor_position

        # Take the start of the lines.
        from_, _ = buffer.document.translate_index_to_position(from_)
        to, _ = buffer.document.translate_index_to_position(to)

        return from_, to

    def cut(self, buffer: Buffer) -> tuple[Document, ClipboardData]:
        """
        Turn text object into `ClipboardData` instance.
        """
        from_, to = self.operator_range(buffer.document)

        from_ += buffer.cursor_position
        to += buffer.cursor_position

        # For Vi mode, the SelectionState does include the upper position,
        # while `self.operator_range` does not. So, go one to the left, unless
        # we're in the line mode, then we don't want to risk going to the
        # previous line, and missing one line in the selection.
        if self.type != TextObjectType.LINEWISE:
            to -= 1

        document = Document(
            buffer.text,
            to,
            SelectionState(original_cursor_position=from_, type=self.selection_type),
        )

        new_document, clipboard_data = document.cut_selection()
        return new_document, clipboard_data


# Typevar for any text object function:
TextObjectFunction = Callable[[E], TextObject]
_TOF = TypeVar("_TOF", bound=TextObjectFunction)


def create_text_object_decorator(
    key_bindings: KeyBindings,
) -> Callable[..., Callable[[_TOF], _TOF]]:
    """
    Create a decorator that can be used to register Vi text object implementations.
    """

    def text_object_decorator(
        *keys: Keys | str,
        filter: Filter = Always(),
        no_move_handler: bool = False,
        no_selection_handler: bool = False,
        eager: bool = False,
    ) -> Callable[[_TOF], _TOF]:
        """
        Register a text object function.

        Usage::

            @text_object('w', filter=..., no_move_handler=False)
            def handler(event):
                # Return a text object for this key.
                return TextObject(...)

        :param no_move_handler: Disable the move handler in navigation mode.
            (It's still active in selection mode.)
        """

        def decorator(text_object_func: _TOF) -> _TOF:
            @key_bindings.add(
                *keys, filter=vi_waiting_for_text_object_mode & filter, eager=eager
            )
            def _apply_operator_to_text_object(event: E) -> None:
                # Arguments are multiplied.
                vi_state = event.app.vi_state
                event._arg = str((vi_state.operator_arg or 1) * (event.arg or 1))

                # Call the text object handler.
                text_obj = text_object_func(event)

                # Get the operator function.
                # (Should never be None here, given the
                # `vi_waiting_for_text_object_mode` filter state.)
                operator_func = vi_state.operator_func

                if text_obj is not None and operator_func is not None:
                    # Call the operator function with the text object.
                    operator_func(event, text_obj)

                # Clear operator.
                event.app.vi_state.operator_func = None
                event.app.vi_state.operator_arg = None

            # Register a move operation. (Doesn't need an operator.)
            if not no_move_handler:

                @key_bindings.add(
                    *keys,
                    filter=~vi_waiting_for_text_object_mode
                    & filter
                    & vi_navigation_mode,
                    eager=eager,
                )
                def _move_in_navigation_mode(event: E) -> None:
                    """
                    Move handler for navigation mode.
                    """
                    text_object = text_object_func(event)
                    event.current_buffer.cursor_position += text_object.start

            # Register a move selection operation.
            if not no_selection_handler:

                @key_bindings.add(
                    *keys,
                    filter=~vi_waiting_for_text_object_mode
                    & filter
                    & vi_selection_mode,
                    eager=eager,
                )
                def _move_in_selection_mode(event: E) -> None:
                    """
                    Move handler for selection mode.
                    """
                    text_object = text_object_func(event)
                    buff = event.current_buffer
                    selection_state = buff.selection_state

                    if selection_state is None:
                        return  # Should not happen, because of the `vi_selection_mode` filter.

                    # When the text object has both a start and end position, like 'i(' or 'iw',
                    # Turn this into a selection, otherwise the cursor.
                    if text_object.end:
                        # Take selection positions from text object.
                        start, end = text_object.operator_range(buff.document)
                        start += buff.cursor_position
                        end += buff.cursor_position

                        selection_state.original_cursor_position = start
                        buff.cursor_position = end

                        # Take selection type from text object.
                        if text_object.type == TextObjectType.LINEWISE:
                            selection_state.type = SelectionType.LINES
                        else:
                            selection_state.type = SelectionType.CHARACTERS
                    else:
                        event.current_buffer.cursor_position += text_object.start

            # Make it possible to chain @text_object decorators.
            return text_object_func

        return decorator

    return text_object_decorator


# Typevar for any operator function:
OperatorFunction = Callable[[E, TextObject], None]
_OF = TypeVar("_OF", bound=OperatorFunction)


def create_operator_decorator(
    key_bindings: KeyBindings,
) -> Callable[..., Callable[[_OF], _OF]]:
    """
    Create a decorator that can be used for registering Vi operators.
    """

    def operator_decorator(
        *keys: Keys | str, filter: Filter = Always(), eager: bool = False
    ) -> Callable[[_OF], _OF]:
        """
        Register a Vi operator.

        Usage::

            @operator('d', filter=...)
            def handler(event, text_object):
                # Do something with the text object here.
        """

        def decorator(operator_func: _OF) -> _OF:
            @key_bindings.add(
                *keys,
                filter=~vi_waiting_for_text_object_mode & filter & vi_navigation_mode,
                eager=eager,
            )
            def _operator_in_navigation(event: E) -> None:
                """
                Handle operator in navigation mode.
                """
                # When this key binding is matched, only set the operator
                # function in the ViState. We should execute it after a text
                # object has been received.
                event.app.vi_state.operator_func = operator_func
                event.app.vi_state.operator_arg = event.arg

            @key_bindings.add(
                *keys,
                filter=~vi_waiting_for_text_object_mode & filter & vi_selection_mode,
                eager=eager,
            )
            def _operator_in_selection(event: E) -> None:
                """
                Handle operator in selection mode.
                """
                buff = event.current_buffer
                selection_state = buff.selection_state

                if selection_state is not None:
                    # Create text object from selection.
                    if selection_state.type == SelectionType.LINES:
                        text_obj_type = TextObjectType.LINEWISE
                    elif selection_state.type == SelectionType.BLOCK:
                        text_obj_type = TextObjectType.BLOCK
                    else:
                        text_obj_type = TextObjectType.INCLUSIVE

                    text_object = TextObject(
                        selection_state.original_cursor_position - buff.cursor_position,
                        type=text_obj_type,
                    )

                    # Execute operator.
                    operator_func(event, text_object)

                    # Quit selection mode.
                    buff.selection_state = None

            return operator_func

        return decorator

    return operator_decorator


@Condition
def is_returnable() -> bool:
    return get_app().current_buffer.is_returnable


@Condition
def in_block_selection() -> bool:
    buff = get_app().current_buffer
    return bool(
        buff.selection_state and buff.selection_state.type == SelectionType.BLOCK
    )


@Condition
def digraph_symbol_1_given() -> bool:
    return get_app().vi_state.digraph_symbol1 is not None


@Condition
def search_buffer_is_empty() -> bool:
    "Returns True when the search buffer is empty."
    return get_app().current_buffer.text == ""


@Condition
def tilde_operator() -> bool:
    return get_app().vi_state.tilde_operator


def load_vi_bindings() -> KeyBindingsBase:
    """
    Vi extensions.

    # Overview of Readline Vi commands:
    # http://www.catonmat.net/download/bash-vi-editing-mode-cheat-sheet.pdf
    """
    # Note: Some key bindings have the "~IsReadOnly()" filter added. This
    #       prevents the handler to be executed when the focus is on a
    #       read-only buffer.
    #       This is however only required for those that change the ViState to
    #       INSERT mode. The `Buffer` class itself throws the
    #       `EditReadOnlyBuffer` exception for any text operations which is
    #       handled correctly. There is no need to add "~IsReadOnly" to all key
    #       bindings that do text manipulation.

    key_bindings = KeyBindings()
    handle = key_bindings.add

    # (Note: Always take the navigation bindings in read-only mode, even when
    #  ViState says different.)

    TransformFunction = Tuple[Tuple[str, ...], Filter, Callable[[str], str]]

    vi_transform_functions: list[TransformFunction] = [
        # Rot 13 transformation
        (
            ("g", "?"),
            Always(),
            lambda string: codecs.encode(string, "rot_13"),
        ),
        # To lowercase
        (("g", "u"), Always(), lambda string: string.lower()),
        # To uppercase.
        (("g", "U"), Always(), lambda string: string.upper()),
        # Swap case.
        (("g", "~"), Always(), lambda string: string.swapcase()),
        (
            ("~",),
            tilde_operator,
            lambda string: string.swapcase(),
        ),
    ]

    # Insert a character literally (quoted insert).
    handle("c-v", filter=vi_insert_mode)(get_by_name("quoted-insert"))

    @handle("escape")
    def _back_to_navigation(event: E) -> None:
        """
        Escape goes to vi navigation mode.
        """
        buffer = event.current_buffer
        vi_state = event.app.vi_state

        if vi_state.input_mode in (InputMode.INSERT, InputMode.REPLACE):
            buffer.cursor_position += buffer.document.get_cursor_left_position()

        vi_state.input_mode = InputMode.NAVIGATION

        if bool(buffer.selection_state):
            buffer.exit_selection()

    @handle("k", filter=vi_selection_mode)
    def _up_in_selection(event: E) -> None:
        """
        Arrow up in selection mode.
        """
        event.current_buffer.cursor_up(count=event.arg)

    @handle("j", filter=vi_selection_mode)
    def _down_in_selection(event: E) -> None:
        """
        Arrow down in selection mode.
        """
        event.current_buffer.cursor_down(count=event.arg)

    @handle("up", filter=vi_navigation_mode)
    @handle("c-p", filter=vi_navigation_mode)
    def _up_in_navigation(event: E) -> None:
        """
        Arrow up and ControlP in navigation mode go up.
        """
        event.current_buffer.auto_up(count=event.arg)

    @handle("k", filter=vi_navigation_mode)
    def _go_up(event: E) -> None:
        """
        Go up, but if we enter a new history entry, move to the start of the
        line.
        """
        event.current_buffer.auto_up(
            count=event.arg, go_to_start_of_line_if_history_changes=True
        )

    @handle("down", filter=vi_navigation_mode)
    @handle("c-n", filter=vi_navigation_mode)
    def _go_down(event: E) -> None:
        """
        Arrow down and Control-N in navigation mode.
        """
        event.current_buffer.auto_down(count=event.arg)

    @handle("j", filter=vi_navigation_mode)
    def _go_down2(event: E) -> None:
        """
        Go down, but if we enter a new history entry, go to the start of the line.
        """
        event.current_buffer.auto_down(
            count=event.arg, go_to_start_of_line_if_history_changes=True
        )

    @handle("backspace", filter=vi_navigation_mode)
    def _go_left(event: E) -> None:
        """
        In navigation-mode, move cursor.
        """
        event.current_buffer.cursor_position += (
            event.current_buffer.document.get_cursor_left_position(count=event.arg)
        )

    @handle("c-n", filter=vi_insert_mode)
    def _complete_next(event: E) -> None:
        b = event.current_buffer

        if b.complete_state:
            b.complete_next()
        else:
            b.start_completion(select_first=True)

    @handle("c-p", filter=vi_insert_mode)
    def _complete_prev(event: E) -> None:
        """
        Control-P: To previous completion.
        """
        b = event.current_buffer

        if b.complete_state:
            b.complete_previous()
        else:
            b.start_completion(select_last=True)

    @handle("c-g", filter=vi_insert_mode)
    @handle("c-y", filter=vi_insert_mode)
    def _accept_completion(event: E) -> None:
        """
        Accept current completion.
        """
        event.current_buffer.complete_state = None

    @handle("c-e", filter=vi_insert_mode)
    def _cancel_completion(event: E) -> None:
        """
        Cancel completion. Go back to originally typed text.
        """
        event.current_buffer.cancel_completion()

    # In navigation mode, pressing enter will always return the input.
    handle("enter", filter=vi_navigation_mode & is_returnable)(
        get_by_name("accept-line")
    )

    # In insert mode, also accept input when enter is pressed, and the buffer
    # has been marked as single line.
    handle("enter", filter=is_returnable & ~is_multiline)(get_by_name("accept-line"))

    @handle("enter", filter=~is_returnable & vi_navigation_mode)
    def _start_of_next_line(event: E) -> None:
        """
        Go to the beginning of next line.
        """
        b = event.current_buffer
        b.cursor_down(count=event.arg)
        b.cursor_position += b.document.get_start_of_line_position(
            after_whitespace=True
        )

    # ** In navigation mode **

    # List of navigation commands: http://hea-www.harvard.edu/~fine/Tech/vi.html

    @handle("insert", filter=vi_navigation_mode)
    def _insert_mode(event: E) -> None:
        """
        Pressing the Insert key.
        """
        event.app.vi_state.input_mode = InputMode.INSERT

    @handle("insert", filter=vi_insert_mode)
    def _navigation_mode(event: E) -> None:
        """
        Pressing the Insert key.
        """
        event.app.vi_state.input_mode = InputMode.NAVIGATION

    @handle("a", filter=vi_navigation_mode & ~is_read_only)
    # ~IsReadOnly, because we want to stay in navigation mode for
    # read-only buffers.
    def _a(event: E) -> None:
        event.current_buffer.cursor_position += (
            event.current_buffer.document.get_cursor_right_position()
        )
        event.app.vi_state.input_mode = InputMode.INSERT

    @handle("A", filter=vi_navigation_mode & ~is_read_only)
    def _A(event: E) -> None:
        event.current_buffer.cursor_position += (
            event.current_buffer.document.get_end_of_line_position()
        )
        event.app.vi_state.input_mode = InputMode.INSERT

    @handle("C", filter=vi_navigation_mode & ~is_read_only)
    def _change_until_end_of_line(event: E) -> None:
        """
        Change to end of line.
        Same as 'c$' (which is implemented elsewhere.)
        """
        buffer = event.current_buffer

        deleted = buffer.delete(count=buffer.document.get_end_of_line_position())
        event.app.clipboard.set_text(deleted)
        event.app.vi_state.input_mode = InputMode.INSERT

    @handle("c", "c", filter=vi_navigation_mode & ~is_read_only)
    @handle("S", filter=vi_navigation_mode & ~is_read_only)
    def _change_current_line(event: E) -> None:  # TODO: implement 'arg'
        """
        Change current line
        """
        buffer = event.current_buffer

        # We copy the whole line.
        data = ClipboardData(buffer.document.current_line, SelectionType.LINES)
        event.app.clipboard.set_data(data)

        # But we delete after the whitespace
        buffer.cursor_position += buffer.document.get_start_of_line_position(
            after_whitespace=True
        )
        buffer.delete(count=buffer.document.get_end_of_line_position())
        event.app.vi_state.input_mode = InputMode.INSERT

    @handle("D", filter=vi_navigation_mode)
    def _delete_until_end_of_line(event: E) -> None:
        """
        Delete from cursor position until the end of the line.
        """
        buffer = event.current_buffer
        deleted = buffer.delete(count=buffer.document.get_end_of_line_position())
        event.app.clipboard.set_text(deleted)

    @handle("d", "d", filter=vi_navigation_mode)
    def _delete_line(event: E) -> None:
        """
        Delete line. (Or the following 'n' lines.)
        """
        buffer = event.current_buffer

        # Split string in before/deleted/after text.
        lines = buffer.document.lines

        before = "\n".join(lines[: buffer.document.cursor_position_row])
        deleted = "\n".join(
            lines[
                buffer.document.cursor_position_row : buffer.document.cursor_position_row
                + event.arg
            ]
        )
        after = "\n".join(lines[buffer.document.cursor_position_row + event.arg :])

        # Set new text.
        if before and after:
            before = before + "\n"

        # Set text and cursor position.
        buffer.document = Document(
            text=before + after,
            # Cursor At the start of the first 'after' line, after the leading whitespace.
            cursor_position=len(before) + len(after) - len(after.lstrip(" ")),
        )

        # Set clipboard data
        event.app.clipboard.set_data(ClipboardData(deleted, SelectionType.LINES))

    @handle("x", filter=vi_selection_mode)
    def _cut(event: E) -> None:
        """
        Cut selection.
        ('x' is not an operator.)
        """
        clipboard_data = event.current_buffer.cut_selection()
        event.app.clipboard.set_data(clipboard_data)

    @handle("i", filter=vi_navigation_mode & ~is_read_only)
    def _i(event: E) -> None:
        event.app.vi_state.input_mode = InputMode.INSERT

    @handle("I", filter=vi_navigation_mode & ~is_read_only)
    def _I(event: E) -> None:
        event.app.vi_state.input_mode = InputMode.INSERT
        event.current_buffer.cursor_position += (
            event.current_buffer.document.get_start_of_line_position(
                after_whitespace=True
            )
        )

    @handle("I", filter=in_block_selection & ~is_read_only)
    def insert_in_block_selection(event: E, after: bool = False) -> None:
        """
        Insert in block selection mode.
        """
        buff = event.current_buffer

        # Store all cursor positions.
        positions = []

        if after:

            def get_pos(from_to: tuple[int, int]) -> int:
                return from_to[1]

        else:

            def get_pos(from_to: tuple[int, int]) -> int:
                return from_to[0]

        for i, from_to in enumerate(buff.document.selection_ranges()):
            positions.append(get_pos(from_to))
            if i == 0:
                buff.cursor_position = get_pos(from_to)

        buff.multiple_cursor_positions = positions

        # Go to 'INSERT_MULTIPLE' mode.
        event.app.vi_state.input_mode = InputMode.INSERT_MULTIPLE
        buff.exit_selection()

    @handle("A", filter=in_block_selection & ~is_read_only)
    def _append_after_block(event: E) -> None:
        insert_in_block_selection(event, after=True)

    @handle("J", filter=vi_navigation_mode & ~is_read_only)
    def _join(event: E) -> None:
        """
        Join lines.
        """
        for i in range(event.arg):
            event.current_buffer.join_next_line()

    @handle("g", "J", filter=vi_navigation_mode & ~is_read_only)
    def _join_nospace(event: E) -> None:
        """
        Join lines without space.
        """
        for i in range(event.arg):
            event.current_buffer.join_next_line(separator="")

    @handle("J", filter=vi_selection_mode & ~is_read_only)
    def _join_selection(event: E) -> None:
        """
        Join selected lines.
        """
        event.current_buffer.join_selected_lines()

    @handle("g", "J", filter=vi_selection_mode & ~is_read_only)
    def _join_selection_nospace(event: E) -> None:
        """
        Join selected lines without space.
        """
        event.current_buffer.join_selected_lines(separator="")

    @handle("p", filter=vi_navigation_mode)
    def _paste(event: E) -> None:
        """
        Paste after
        """
        event.current_buffer.paste_clipboard_data(
            event.app.clipboard.get_data(),
            count=event.arg,
            paste_mode=PasteMode.VI_AFTER,
        )

    @handle("P", filter=vi_navigation_mode)
    def _paste_before(event: E) -> None:
        """
        Paste before
        """
        event.current_buffer.paste_clipboard_data(
            event.app.clipboard.get_data(),
            count=event.arg,
            paste_mode=PasteMode.VI_BEFORE,
        )

    @handle('"', Keys.Any, "p", filter=vi_navigation_mode)
    def _paste_register(event: E) -> None:
        """
        Paste from named register.
        """
        c = event.key_sequence[1].data
        if c in vi_register_names:
            data = event.app.vi_state.named_registers.get(c)
            if data:
                event.current_buffer.paste_clipboard_data(
                    data, count=event.arg, paste_mode=PasteMode.VI_AFTER
                )

    @handle('"', Keys.Any, "P", filter=vi_navigation_mode)
    def _paste_register_before(event: E) -> None:
        """
        Paste (before) from named register.
        """
        c = event.key_sequence[1].data
        if c in vi_register_names:
            data = event.app.vi_state.named_registers.get(c)
            if data:
                event.current_buffer.paste_clipboard_data(
                    data, count=event.arg, paste_mode=PasteMode.VI_BEFORE
                )

    @handle("r", filter=vi_navigation_mode)
    def _replace(event: E) -> None:
        """
        Go to 'replace-single'-mode.
        """
        event.app.vi_state.input_mode = InputMode.REPLACE_SINGLE

    @handle("R", filter=vi_navigation_mode)
    def _replace_mode(event: E) -> None:
        """
        Go to 'replace'-mode.
        """
        event.app.vi_state.input_mode = InputMode.REPLACE

    @handle("s", filter=vi_navigation_mode & ~is_read_only)
    def _substitute(event: E) -> None:
        """
        Substitute with new text
        (Delete character(s) and go to insert mode.)
        """
        text = event.current_buffer.delete(count=event.arg)
        event.app.clipboard.set_text(text)
        event.app.vi_state.input_mode = InputMode.INSERT

    @handle("u", filter=vi_navigation_mode, save_before=(lambda e: False))
    def _undo(event: E) -> None:
        for i in range(event.arg):
            event.current_buffer.undo()

    @handle("V", filter=vi_navigation_mode)
    def _visual_line(event: E) -> None:
        """
        Start lines selection.
        """
        event.current_buffer.start_selection(selection_type=SelectionType.LINES)

    @handle("c-v", filter=vi_navigation_mode)
    def _visual_block(event: E) -> None:
        """
        Enter block selection mode.
        """
        event.current_buffer.start_selection(selection_type=SelectionType.BLOCK)

    @handle("V", filter=vi_selection_mode)
    def _visual_line2(event: E) -> None:
        """
        Exit line selection mode, or go from non line selection mode to line
        selection mode.
        """
        selection_state = event.current_buffer.selection_state

        if selection_state is not None:
            if selection_state.type != SelectionType.LINES:
                selection_state.type = SelectionType.LINES
            else:
                event.current_buffer.exit_selection()

    @handle("v", filter=vi_navigation_mode)
    def _visual(event: E) -> None:
        """
        Enter character selection mode.
        """
        event.current_buffer.start_selection(selection_type=SelectionType.CHARACTERS)

    @handle("v", filter=vi_selection_mode)
    def _visual2(event: E) -> None:
        """
        Exit character selection mode, or go from non-character-selection mode
        to character selection mode.
        """
        selection_state = event.current_buffer.selection_state

        if selection_state is not None:
            if selection_state.type != SelectionType.CHARACTERS:
                selection_state.type = SelectionType.CHARACTERS
            else:
                event.current_buffer.exit_selection()

    @handle("c-v", filter=vi_selection_mode)
    def _visual_block2(event: E) -> None:
        """
        Exit block selection mode, or go from non block selection mode to block
        selection mode.
        """
        selection_state = event.current_buffer.selection_state

        if selection_state is not None:
            if selection_state.type != SelectionType.BLOCK:
                selection_state.type = SelectionType.BLOCK
            else:
                event.current_buffer.exit_selection()

    @handle("a", "w", filter=vi_selection_mode)
    @handle("a", "W", filter=vi_selection_mode)
    def _visual_auto_word(event: E) -> None:
        """
        Switch from visual linewise mode to visual characterwise mode.
        """
        buffer = event.current_buffer

        if (
            buffer.selection_state
            and buffer.selection_state.type == SelectionType.LINES
        ):
            buffer.selection_state.type = SelectionType.CHARACTERS

    @handle("x", filter=vi_navigation_mode)
    def _delete(event: E) -> None:
        """
        Delete character.
        """
        buff = event.current_buffer
        count = min(event.arg, len(buff.document.current_line_after_cursor))
        if count:
            text = event.current_buffer.delete(count=count)
            event.app.clipboard.set_text(text)

    @handle("X", filter=vi_navigation_mode)
    def _delete_before_cursor(event: E) -> None:
        buff = event.current_buffer
        count = min(event.arg, len(buff.document.current_line_before_cursor))
        if count:
            text = event.current_buffer.delete_before_cursor(count=count)
            event.app.clipboard.set_text(text)

    @handle("y", "y", filter=vi_navigation_mode)
    @handle("Y", filter=vi_navigation_mode)
    def _yank_line(event: E) -> None:
        """
        Yank the whole line.
        """
        text = "\n".join(event.current_buffer.document.lines_from_current[: event.arg])
        event.app.clipboard.set_data(ClipboardData(text, SelectionType.LINES))

    @handle("+", filter=vi_navigation_mode)
    def _next_line(event: E) -> None:
        """
        Move to first non whitespace of next line
        """
        buffer = event.current_buffer
        buffer.cursor_position += buffer.document.get_cursor_down_position(
            count=event.arg
        )
        buffer.cursor_position += buffer.document.get_start_of_line_position(
            after_whitespace=True
        )

    @handle("-", filter=vi_navigation_mode)
    def _prev_line(event: E) -> None:
        """
        Move to first non whitespace of previous line
        """
        buffer = event.current_buffer
        buffer.cursor_position += buffer.document.get_cursor_up_position(
            count=event.arg
        )
        buffer.cursor_position += buffer.document.get_start_of_line_position(
            after_whitespace=True
        )

    @handle(">", ">", filter=vi_navigation_mode)
    @handle("c-t", filter=vi_insert_mode)
    def _indent(event: E) -> None:
        """
        Indent lines.
        """
        buffer = event.current_buffer
        current_row = buffer.document.cursor_position_row
        indent(buffer, current_row, current_row + event.arg)

    @handle("<", "<", filter=vi_navigation_mode)
    @handle("c-d", filter=vi_insert_mode)
    def _unindent(event: E) -> None:
        """
        Unindent lines.
        """
        current_row = event.current_buffer.document.cursor_position_row
        unindent(event.current_buffer, current_row, current_row + event.arg)

    @handle("O", filter=vi_navigation_mode & ~is_read_only)
    def _open_above(event: E) -> None:
        """
        Open line above and enter insertion mode
        """
        event.current_buffer.insert_line_above(copy_margin=not in_paste_mode())
        event.app.vi_state.input_mode = InputMode.INSERT

    @handle("o", filter=vi_navigation_mode & ~is_read_only)
    def _open_below(event: E) -> None:
        """
        Open line below and enter insertion mode
        """
        event.current_buffer.insert_line_below(copy_margin=not in_paste_mode())
        event.app.vi_state.input_mode = InputMode.INSERT

    @handle("~", filter=vi_navigation_mode)
    def _reverse_case(event: E) -> None:
        """
        Reverse case of current character and move cursor forward.
        """
        buffer = event.current_buffer
        c = buffer.document.current_char

        if c is not None and c != "\n":
            buffer.insert_text(c.swapcase(), overwrite=True)

    @handle("g", "u", "u", filter=vi_navigation_mode & ~is_read_only)
    def _lowercase_line(event: E) -> None:
        """
        Lowercase current line.
        """
        buff = event.current_buffer
        buff.transform_current_line(lambda s: s.lower())

    @handle("g", "U", "U", filter=vi_navigation_mode & ~is_read_only)
    def _uppercase_line(event: E) -> None:
        """
        Uppercase current line.
        """
        buff = event.current_buffer
        buff.transform_current_line(lambda s: s.upper())

    @handle("g", "~", "~", filter=vi_navigation_mode & ~is_read_only)
    def _swapcase_line(event: E) -> None:
        """
        Swap case of the current line.
        """
        buff = event.current_buffer
        buff.transform_current_line(lambda s: s.swapcase())

    @handle("#", filter=vi_navigation_mode)
    def _prev_occurrence(event: E) -> None:
        """
        Go to previous occurrence of this word.
        """
        b = event.current_buffer
        search_state = event.app.current_search_state

        search_state.text = b.document.get_word_under_cursor()
        search_state.direction = SearchDirection.BACKWARD

        b.apply_search(search_state, count=event.arg, include_current_position=False)

    @handle("*", filter=vi_navigation_mode)
    def _next_occurrence(event: E) -> None:
        """
        Go to next occurrence of this word.
        """
        b = event.current_buffer
        search_state = event.app.current_search_state

        search_state.text = b.document.get_word_under_cursor()
        search_state.direction = SearchDirection.FORWARD

        b.apply_search(search_state, count=event.arg, include_current_position=False)

    @handle("(", filter=vi_navigation_mode)
    def _begin_of_sentence(event: E) -> None:
        # TODO: go to begin of sentence.
        # XXX: should become text_object.
        pass

    @handle(")", filter=vi_navigation_mode)
    def _end_of_sentence(event: E) -> None:
        # TODO: go to end of sentence.
        # XXX: should become text_object.
        pass

    operator = create_operator_decorator(key_bindings)
    text_object = create_text_object_decorator(key_bindings)

    @handle(Keys.Any, filter=vi_waiting_for_text_object_mode)
    def _unknown_text_object(event: E) -> None:
        """
        Unknown key binding while waiting for a text object.
        """
        event.app.output.bell()

    #
    # *** Operators ***
    #

    def create_delete_and_change_operators(
        delete_only: bool, with_register: bool = False
    ) -> None:
        """
        Delete and change operators.

        :param delete_only: Create an operator that deletes, but doesn't go to insert mode.
        :param with_register: Copy the deleted text to this named register instead of the clipboard.
        """
        handler_keys: Iterable[str]
        if with_register:
            handler_keys = ('"', Keys.Any, "cd"[delete_only])
        else:
            handler_keys = "cd"[delete_only]

        @operator(*handler_keys, filter=~is_read_only)
        def delete_or_change_operator(event: E, text_object: TextObject) -> None:
            clipboard_data = None
            buff = event.current_buffer

            if text_object:
                new_document, clipboard_data = text_object.cut(buff)
                buff.document = new_document

            # Set deleted/changed text to clipboard or named register.
            if clipboard_data and clipboard_data.text:
                if with_register:
                    reg_name = event.key_sequence[1].data
                    if reg_name in vi_register_names:
                        event.app.vi_state.named_registers[reg_name] = clipboard_data
                else:
                    event.app.clipboard.set_data(clipboard_data)

            # Only go back to insert mode in case of 'change'.
            if not delete_only:
                event.app.vi_state.input_mode = InputMode.INSERT

    create_delete_and_change_operators(False, False)
    create_delete_and_change_operators(False, True)
    create_delete_and_change_operators(True, False)
    create_delete_and_change_operators(True, True)

    def create_transform_handler(
        filter: Filter, transform_func: Callable[[str], str], *a: str
    ) -> None:
        @operator(*a, filter=filter & ~is_read_only)
        def _(event: E, text_object: TextObject) -> None:
            """
            Apply transformation (uppercase, lowercase, rot13, swap case).
            """
            buff = event.current_buffer
            start, end = text_object.operator_range(buff.document)

            if start < end:
                # Transform.
                buff.transform_region(
                    buff.cursor_position + start,
                    buff.cursor_position + end,
                    transform_func,
                )

                # Move cursor
                buff.cursor_position += text_object.end or text_object.start

    for k, f, func in vi_transform_functions:
        create_transform_handler(f, func, *k)

    @operator("y")
    def _yank(event: E, text_object: TextObject) -> None:
        """
        Yank operator. (Copy text.)
        """
        _, clipboard_data = text_object.cut(event.current_buffer)
        if clipboard_data.text:
            event.app.clipboard.set_data(clipboard_data)

    @operator('"', Keys.Any, "y")
    def _yank_to_register(event: E, text_object: TextObject) -> None:
        """
        Yank selection to named register.
        """
        c = event.key_sequence[1].data
        if c in vi_register_names:
            _, clipboard_data = text_object.cut(event.current_buffer)
            event.app.vi_state.named_registers[c] = clipboard_data

    @operator(">")
    def _indent_text_object(event: E, text_object: TextObject) -> None:
        """
        Indent.
        """
        buff = event.current_buffer
        from_, to = text_object.get_line_numbers(buff)
        indent(buff, from_, to + 1, count=event.arg)

    @operator("<")
    def _unindent_text_object(event: E, text_object: TextObject) -> None:
        """
        Unindent.
        """
        buff = event.current_buffer
        from_, to = text_object.get_line_numbers(buff)
        unindent(buff, from_, to + 1, count=event.arg)

    @operator("g", "q")
    def _reshape(event: E, text_object: TextObject) -> None:
        """
        Reshape text.
        """
        buff = event.current_buffer
        from_, to = text_object.get_line_numbers(buff)
        reshape_text(buff, from_, to)

    #
    # *** Text objects ***
    #

    @text_object("b")
    def _b(event: E) -> TextObject:
        """
        Move one word or token left.
        """
        return TextObject(
            event.current_buffer.document.find_start_of_previous_word(count=event.arg)
            or 0
        )

    @text_object("B")
    def _B(event: E) -> TextObject:
        """
        Move one non-blank word left
        """
        return TextObject(
            event.current_buffer.document.find_start_of_previous_word(
                count=event.arg, WORD=True
            )
            or 0
        )

    @text_object("$")
    def _dollar(event: E) -> TextObject:
        """
        'c$', 'd$' and '$':  Delete/change/move until end of line.
        """
        return TextObject(event.current_buffer.document.get_end_of_line_position())

    @text_object("w")
    def _word_forward(event: E) -> TextObject:
        """
        'word' forward. 'cw', 'dw', 'w': Delete/change/move one word.
        """
        return TextObject(
            event.current_buffer.document.find_next_word_beginning(count=event.arg)
            or event.current_buffer.document.get_end_of_document_position()
        )

    @text_object("W")
    def _WORD_forward(event: E) -> TextObject:
        """
        'WORD' forward. 'cW', 'dW', 'W': Delete/change/move one WORD.
        """
        return TextObject(
            event.current_buffer.document.find_next_word_beginning(
                count=event.arg, WORD=True
            )
            or event.current_buffer.document.get_end_of_document_position()
        )

    @text_object("e")
    def _end_of_word(event: E) -> TextObject:
        """
        End of 'word': 'ce', 'de', 'e'
        """
        end = event.current_buffer.document.find_next_word_ending(count=event.arg)
        return TextObject(end - 1 if end else 0, type=TextObjectType.INCLUSIVE)

    @text_object("E")
    def _end_of_WORD(event: E) -> TextObject:
        """
        End of 'WORD': 'cE', 'dE', 'E'
        """
        end = event.current_buffer.document.find_next_word_ending(
            count=event.arg, WORD=True
        )
        return TextObject(end - 1 if end else 0, type=TextObjectType.INCLUSIVE)

    @text_object("i", "w", no_move_handler=True)
    def _inner_word(event: E) -> TextObject:
        """
        Inner 'word': ciw and diw
        """
        start, end = event.current_buffer.document.find_boundaries_of_current_word()
        return TextObject(start, end)

    @text_object("a", "w", no_move_handler=True)
    def _a_word(event: E) -> TextObject:
        """
        A 'word': caw and daw
        """
        start, end = event.current_buffer.document.find_boundaries_of_current_word(
            include_trailing_whitespace=True
        )
        return TextObject(start, end)

    @text_object("i", "W", no_move_handler=True)
    def _inner_WORD(event: E) -> TextObject:
        """
        Inner 'WORD': ciW and diW
        """
        start, end = event.current_buffer.document.find_boundaries_of_current_word(
            WORD=True
        )
        return TextObject(start, end)

    @text_object("a", "W", no_move_handler=True)
    def _a_WORD(event: E) -> TextObject:
        """
        A 'WORD': caw and daw
        """
        start, end = event.current_buffer.document.find_boundaries_of_current_word(
            WORD=True, include_trailing_whitespace=True
        )
        return TextObject(start, end)

    @text_object("a", "p", no_move_handler=True)
    def _paragraph(event: E) -> TextObject:
        """
        Auto paragraph.
        """
        start = event.current_buffer.document.start_of_paragraph()
        end = event.current_buffer.document.end_of_paragraph(count=event.arg)
        return TextObject(start, end)

    @text_object("^")
    def _start_of_line(event: E) -> TextObject:
        """'c^', 'd^' and '^': Soft start of line, after whitespace."""
        return TextObject(
            event.current_buffer.document.get_start_of_line_position(
                after_whitespace=True
            )
        )

    @text_object("0")
    def _hard_start_of_line(event: E) -> TextObject:
        """
        'c0', 'd0': Hard start of line, before whitespace.
        (The move '0' key is implemented elsewhere, because a '0' could also change the `arg`.)
        """
        return TextObject(
            event.current_buffer.document.get_start_of_line_position(
                after_whitespace=False
            )
        )

    def create_ci_ca_handles(
        ci_start: str, ci_end: str, inner: bool, key: str | None = None
    ) -> None:
        # TODO: 'dat', 'dit', (tags (like xml)
        """
        Delete/Change string between this start and stop character. But keep these characters.
        This implements all the ci", ci<, ci{, ci(, di", di<, ca", ca<, ... combinations.
        """

        def handler(event: E) -> TextObject:
            if ci_start == ci_end:
                # Quotes
                start = event.current_buffer.document.find_backwards(
                    ci_start, in_current_line=False
                )
                end = event.current_buffer.document.find(ci_end, in_current_line=False)
            else:
                # Brackets
                start = event.current_buffer.document.find_enclosing_bracket_left(
                    ci_start, ci_end
                )
                end = event.current_buffer.document.find_enclosing_bracket_right(
                    ci_start, ci_end
                )

            if start is not None and end is not None:
                offset = 0 if inner else 1
                return TextObject(start + 1 - offset, end + offset)
            else:
                # Nothing found.
                return TextObject(0)

        if key is None:
            text_object("ai"[inner], ci_start, no_move_handler=True)(handler)
            text_object("ai"[inner], ci_end, no_move_handler=True)(handler)
        else:
            text_object("ai"[inner], key, no_move_handler=True)(handler)

    for inner in (False, True):
        for ci_start, ci_end in [
            ('"', '"'),
            ("'", "'"),
            ("`", "`"),
            ("[", "]"),
            ("<", ">"),
            ("{", "}"),
            ("(", ")"),
        ]:
            create_ci_ca_handles(ci_start, ci_end, inner)

        create_ci_ca_handles("(", ")", inner, "b")  # 'dab', 'dib'
        create_ci_ca_handles("{", "}", inner, "B")  # 'daB', 'diB'

    @text_object("{")
    def _previous_section(event: E) -> TextObject:
        """
        Move to previous blank-line separated section.
        Implements '{', 'c{', 'd{', 'y{'
        """
        index = event.current_buffer.document.start_of_paragraph(
            count=event.arg, before=True
        )
        return TextObject(index)

    @text_object("}")
    def _next_section(event: E) -> TextObject:
        """
        Move to next blank-line separated section.
        Implements '}', 'c}', 'd}', 'y}'
        """
        index = event.current_buffer.document.end_of_paragraph(
            count=event.arg, after=True
        )
        return TextObject(index)

    @text_object("f", Keys.Any)
    def _find_next_occurrence(event: E) -> TextObject:
        """
        Go to next occurrence of character. Typing 'fx' will move the
        cursor to the next occurrence of character. 'x'.
        """
        event.app.vi_state.last_character_find = CharacterFind(event.data, False)
        match = event.current_buffer.document.find(
            event.data, in_current_line=True, count=event.arg
        )
        if match:
            return TextObject(match, type=TextObjectType.INCLUSIVE)
        else:
            return TextObject(0)

    @text_object("F", Keys.Any)
    def _find_previous_occurrence(event: E) -> TextObject:
        """
        Go to previous occurrence of character. Typing 'Fx' will move the
        cursor to the previous occurrence of character. 'x'.
        """
        event.app.vi_state.last_character_find = CharacterFind(event.data, True)
        return TextObject(
            event.current_buffer.document.find_backwards(
                event.data, in_current_line=True, count=event.arg
            )
            or 0
        )

    @text_object("t", Keys.Any)
    def _t(event: E) -> TextObject:
        """
        Move right to the next occurrence of c, then one char backward.
        """
        event.app.vi_state.last_character_find = CharacterFind(event.data, False)
        match = event.current_buffer.document.find(
            event.data, in_current_line=True, count=event.arg
        )
        if match:
            return TextObject(match - 1, type=TextObjectType.INCLUSIVE)
        else:
            return TextObject(0)

    @text_object("T", Keys.Any)
    def _T(event: E) -> TextObject:
        """
        Move left to the previous occurrence of c, then one char forward.
        """
        event.app.vi_state.last_character_find = CharacterFind(event.data, True)
        match = event.current_buffer.document.find_backwards(
            event.data, in_current_line=True, count=event.arg
        )
        return TextObject(match + 1 if match else 0)

    def repeat(reverse: bool) -> None:
        """
        Create ',' and ';' commands.
        """

        @text_object("," if reverse else ";")
        def _(event: E) -> TextObject:
            """
            Repeat the last 'f'/'F'/'t'/'T' command.
            """
            pos: int | None = 0
            vi_state = event.app.vi_state

            type = TextObjectType.EXCLUSIVE

            if vi_state.last_character_find:
                char = vi_state.last_character_find.character
                backwards = vi_state.last_character_find.backwards

                if reverse:
                    backwards = not backwards

                if backwards:
                    pos = event.current_buffer.document.find_backwards(
                        char, in_current_line=True, count=event.arg
                    )
                else:
                    pos = event.current_buffer.document.find(
                        char, in_current_line=True, count=event.arg
                    )
                    type = TextObjectType.INCLUSIVE
            if pos:
                return TextObject(pos, type=type)
            else:
                return TextObject(0)

    repeat(True)
    repeat(False)

    @text_object("h")
    @text_object("left")
    def _left(event: E) -> TextObject:
        """
        Implements 'ch', 'dh', 'h': Cursor left.
        """
        return TextObject(
            event.current_buffer.document.get_cursor_left_position(count=event.arg)
        )

    @text_object("j", no_move_handler=True, no_selection_handler=True)
    # Note: We also need `no_selection_handler`, because we in
    #       selection mode, we prefer the other 'j' binding that keeps
    #       `buffer.preferred_column`.
    def _down(event: E) -> TextObject:
        """
        Implements 'cj', 'dj', 'j', ... Cursor up.
        """
        return TextObject(
            event.current_buffer.document.get_cursor_down_position(count=event.arg),
            type=TextObjectType.LINEWISE,
        )

    @text_object("k", no_move_handler=True, no_selection_handler=True)
    def _up(event: E) -> TextObject:
        """
        Implements 'ck', 'dk', 'k', ... Cursor up.
        """
        return TextObject(
            event.current_buffer.document.get_cursor_up_position(count=event.arg),
            type=TextObjectType.LINEWISE,
        )

    @text_object("l")
    @text_object(" ")
    @text_object("right")
    def _right(event: E) -> TextObject:
        """
        Implements 'cl', 'dl', 'l', 'c ', 'd ', ' '. Cursor right.
        """
        return TextObject(
            event.current_buffer.document.get_cursor_right_position(count=event.arg)
        )

    @text_object("H")
    def _top_of_screen(event: E) -> TextObject:
        """
        Moves to the start of the visible region. (Below the scroll offset.)
        Implements 'cH', 'dH', 'H'.
        """
        w = event.app.layout.current_window
        b = event.current_buffer

        if w and w.render_info:
            # When we find a Window that has BufferControl showing this window,
            # move to the start of the visible area.
            pos = (
                b.document.translate_row_col_to_index(
                    w.render_info.first_visible_line(after_scroll_offset=True), 0
                )
                - b.cursor_position
            )

        else:
            # Otherwise, move to the start of the input.
            pos = -len(b.document.text_before_cursor)
        return TextObject(pos, type=TextObjectType.LINEWISE)

    @text_object("M")
    def _middle_of_screen(event: E) -> TextObject:
        """
        Moves cursor to the vertical center of the visible region.
        Implements 'cM', 'dM', 'M'.
        """
        w = event.app.layout.current_window
        b = event.current_buffer

        if w and w.render_info:
            # When we find a Window that has BufferControl showing this window,
            # move to the center of the visible area.
            pos = (
                b.document.translate_row_col_to_index(
                    w.render_info.center_visible_line(), 0
                )
                - b.cursor_position
            )

        else:
            # Otherwise, move to the start of the input.
            pos = -len(b.document.text_before_cursor)
        return TextObject(pos, type=TextObjectType.LINEWISE)

    @text_object("L")
    def _end_of_screen(event: E) -> TextObject:
        """
        Moves to the end of the visible region. (Above the scroll offset.)
        """
        w = event.app.layout.current_window
        b = event.current_buffer

        if w and w.render_info:
            # When we find a Window that has BufferControl showing this window,
            # move to the end of the visible area.
            pos = (
                b.document.translate_row_col_to_index(
                    w.render_info.last_visible_line(before_scroll_offset=True), 0
                )
                - b.cursor_position
            )

        else:
            # Otherwise, move to the end of the input.
            pos = len(b.document.text_after_cursor)
        return TextObject(pos, type=TextObjectType.LINEWISE)

    @text_object("n", no_move_handler=True)
    def _search_next(event: E) -> TextObject:
        """
        Search next.
        """
        buff = event.current_buffer
        search_state = event.app.current_search_state

        cursor_position = buff.get_search_position(
            search_state, include_current_position=False, count=event.arg
        )
        return TextObject(cursor_position - buff.cursor_position)

    @handle("n", filter=vi_navigation_mode)
    def _search_next2(event: E) -> None:
        """
        Search next in navigation mode. (This goes through the history.)
        """
        search_state = event.app.current_search_state

        event.current_buffer.apply_search(
            search_state, include_current_position=False, count=event.arg
        )

    @text_object("N", no_move_handler=True)
    def _search_previous(event: E) -> TextObject:
        """
        Search previous.
        """
        buff = event.current_buffer
        search_state = event.app.current_search_state

        cursor_position = buff.get_search_position(
            ~search_state, include_current_position=False, count=event.arg
        )
        return TextObject(cursor_position - buff.cursor_position)

    @handle("N", filter=vi_navigation_mode)
    def _search_previous2(event: E) -> None:
        """
        Search previous in navigation mode. (This goes through the history.)
        """
        search_state = event.app.current_search_state

        event.current_buffer.apply_search(
            ~search_state, include_current_position=False, count=event.arg
        )

    @handle("z", "+", filter=vi_navigation_mode | vi_selection_mode)
    @handle("z", "t", filter=vi_navigation_mode | vi_selection_mode)
    @handle("z", "enter", filter=vi_navigation_mode | vi_selection_mode)
    def _scroll_top(event: E) -> None:
        """
        Scrolls the window to makes the current line the first line in the visible region.
        """
        b = event.current_buffer
        event.app.layout.current_window.vertical_scroll = b.document.cursor_position_row

    @handle("z", "-", filter=vi_navigation_mode | vi_selection_mode)
    @handle("z", "b", filter=vi_navigation_mode | vi_selection_mode)
    def _scroll_bottom(event: E) -> None:
        """
        Scrolls the window to makes the current line the last line in the visible region.
        """
        # We can safely set the scroll offset to zero; the Window will make
        # sure that it scrolls at least enough to make the cursor visible
        # again.
        event.app.layout.current_window.vertical_scroll = 0

    @handle("z", "z", filter=vi_navigation_mode | vi_selection_mode)
    def _scroll_center(event: E) -> None:
        """
        Center Window vertically around cursor.
        """
        w = event.app.layout.current_window
        b = event.current_buffer

        if w and w.render_info:
            info = w.render_info

            # Calculate the offset that we need in order to position the row
            # containing the cursor in the center.
            scroll_height = info.window_height // 2

            y = max(0, b.document.cursor_position_row - 1)
            height = 0
            while y > 0:
                line_height = info.get_height_for_line(y)

                if height + line_height < scroll_height:
                    height += line_height
                    y -= 1
                else:
                    break

            w.vertical_scroll = y

    @text_object("%")
    def _goto_corresponding_bracket(event: E) -> TextObject:
        """
        Implements 'c%', 'd%', '%, 'y%' (Move to corresponding bracket.)
        If an 'arg' has been given, go this this % position in the file.
        """
        buffer = event.current_buffer

        if event._arg:
            # If 'arg' has been given, the meaning of % is to go to the 'x%'
            # row in the file.
            if 0 < event.arg <= 100:
                absolute_index = buffer.document.translate_row_col_to_index(
                    int((event.arg * buffer.document.line_count - 1) / 100), 0
                )
                return TextObject(
                    absolute_index - buffer.document.cursor_position,
                    type=TextObjectType.LINEWISE,
                )
            else:
                return TextObject(0)  # Do nothing.

        else:
            # Move to the corresponding opening/closing bracket (()'s, []'s and {}'s).
            match = buffer.document.find_matching_bracket_position()
            if match:
                return TextObject(match, type=TextObjectType.INCLUSIVE)
            else:
                return TextObject(0)

    @text_object("|")
    def _to_column(event: E) -> TextObject:
        """
        Move to the n-th column (you may specify the argument n by typing it on
        number keys, for example, 20|).
        """
        return TextObject(
            event.current_buffer.document.get_column_cursor_position(event.arg - 1)
        )

    @text_object("g", "g")
    def _goto_first_line(event: E) -> TextObject:
        """
        Go to the start of the very first line.
        Implements 'gg', 'cgg', 'ygg'
        """
        d = event.current_buffer.document

        if event._arg:
            # Move to the given line.
            return TextObject(
                d.translate_row_col_to_index(event.arg - 1, 0) - d.cursor_position,
                type=TextObjectType.LINEWISE,
            )
        else:
            # Move to the top of the input.
            return TextObject(
                d.get_start_of_document_position(), type=TextObjectType.LINEWISE
            )

    @text_object("g", "_")
    def _goto_last_line(event: E) -> TextObject:
        """
        Go to last non-blank of line.
        'g_', 'cg_', 'yg_', etc..
        """
        return TextObject(
            event.current_buffer.document.last_non_blank_of_current_line_position(),
            type=TextObjectType.INCLUSIVE,
        )

    @text_object("g", "e")
    def _ge(event: E) -> TextObject:
        """
        Go to last character of previous word.
        'ge', 'cge', 'yge', etc..
        """
        prev_end = event.current_buffer.document.find_previous_word_ending(
            count=event.arg
        )
        return TextObject(
            prev_end - 1 if prev_end is not None else 0, type=TextObjectType.INCLUSIVE
        )

    @text_object("g", "E")
    def _gE(event: E) -> TextObject:
        """
        Go to last character of previous WORD.
        'gE', 'cgE', 'ygE', etc..
        """
        prev_end = event.current_buffer.document.find_previous_word_ending(
            count=event.arg, WORD=True
        )
        return TextObject(
            prev_end - 1 if prev_end is not None else 0, type=TextObjectType.INCLUSIVE
        )

    @text_object("g", "m")
    def _gm(event: E) -> TextObject:
        """
        Like g0, but half a screenwidth to the right. (Or as much as possible.)
        """
        w = event.app.layout.current_window
        buff = event.current_buffer

        if w and w.render_info:
            width = w.render_info.window_width
            start = buff.document.get_start_of_line_position(after_whitespace=False)
            start += int(min(width / 2, len(buff.document.current_line)))

            return TextObject(start, type=TextObjectType.INCLUSIVE)
        return TextObject(0)

    @text_object("G")
    def _last_line(event: E) -> TextObject:
        """
        Go to the end of the document. (If no arg has been given.)
        """
        buf = event.current_buffer
        return TextObject(
            buf.document.translate_row_col_to_index(buf.document.line_count - 1, 0)
            - buf.cursor_position,
            type=TextObjectType.LINEWISE,
        )

    #
    # *** Other ***
    #

    @handle("G", filter=has_arg)
    def _to_nth_history_line(event: E) -> None:
        """
        If an argument is given, move to this line in the  history. (for
        example, 15G)
        """
        event.current_buffer.go_to_history(event.arg - 1)

    for n in "123456789":

        @handle(
            n,
            filter=vi_navigation_mode
            | vi_selection_mode
            | vi_waiting_for_text_object_mode,
        )
        def _arg(event: E) -> None:
            """
            Always handle numerics in navigation mode as arg.
            """
            event.append_to_arg_count(event.data)

    @handle(
        "0",
        filter=(
            vi_navigation_mode | vi_selection_mode | vi_waiting_for_text_object_mode
        )
        & has_arg,
    )
    def _0_arg(event: E) -> None:
        """
        Zero when an argument was already give.
        """
        event.append_to_arg_count(event.data)

    @handle(Keys.Any, filter=vi_replace_mode)
    def _insert_text(event: E) -> None:
        """
        Insert data at cursor position.
        """
        event.current_buffer.insert_text(event.data, overwrite=True)

    @handle(Keys.Any, filter=vi_replace_single_mode)
    def _replace_single(event: E) -> None:
        """
        Replace single character at cursor position.
        """
        event.current_buffer.insert_text(event.data, overwrite=True)
        event.current_buffer.cursor_position -= 1
        event.app.vi_state.input_mode = InputMode.NAVIGATION

    @handle(
        Keys.Any,
        filter=vi_insert_multiple_mode,
        save_before=(lambda e: not e.is_repeat),
    )
    def _insert_text_multiple_cursors(event: E) -> None:
        """
        Insert data at multiple cursor positions at once.
        (Usually a result of pressing 'I' or 'A' in block-selection mode.)
        """
        buff = event.current_buffer
        original_text = buff.text

        # Construct new text.
        text = []
        p = 0

        for p2 in buff.multiple_cursor_positions:
            text.append(original_text[p:p2])
            text.append(event.data)
            p = p2

        text.append(original_text[p:])

        # Shift all cursor positions.
        new_cursor_positions = [
            pos + i + 1 for i, pos in enumerate(buff.multiple_cursor_positions)
        ]

        # Set result.
        buff.text = "".join(text)
        buff.multiple_cursor_positions = new_cursor_positions
        buff.cursor_position += 1

    @handle("backspace", filter=vi_insert_multiple_mode)
    def _delete_before_multiple_cursors(event: E) -> None:
        """
        Backspace, using multiple cursors.
        """
        buff = event.current_buffer
        original_text = buff.text

        # Construct new text.
        deleted_something = False
        text = []
        p = 0

        for p2 in buff.multiple_cursor_positions:
            if p2 > 0 and original_text[p2 - 1] != "\n":  # Don't delete across lines.
                text.append(original_text[p : p2 - 1])
                deleted_something = True
            else:
                text.append(original_text[p:p2])
            p = p2

        text.append(original_text[p:])

        if deleted_something:
            # Shift all cursor positions.
            lengths = [len(part) for part in text[:-1]]
            new_cursor_positions = list(accumulate(lengths))

            # Set result.
            buff.text = "".join(text)
            buff.multiple_cursor_positions = new_cursor_positions
            buff.cursor_position -= 1
        else:
            event.app.output.bell()

    @handle("delete", filter=vi_insert_multiple_mode)
    def _delete_after_multiple_cursors(event: E) -> None:
        """
        Delete, using multiple cursors.
        """
        buff = event.current_buffer
        original_text = buff.text

        # Construct new text.
        deleted_something = False
        text = []
        new_cursor_positions = []
        p = 0

        for p2 in buff.multiple_cursor_positions:
            text.append(original_text[p:p2])
            if p2 >= len(original_text) or original_text[p2] == "\n":
                # Don't delete across lines.
                p = p2
            else:
                p = p2 + 1
                deleted_something = True

        text.append(original_text[p:])

        if deleted_something:
            # Shift all cursor positions.
            lengths = [len(part) for part in text[:-1]]
            new_cursor_positions = list(accumulate(lengths))

            # Set result.
            buff.text = "".join(text)
            buff.multiple_cursor_positions = new_cursor_positions
        else:
            event.app.output.bell()

    @handle("left", filter=vi_insert_multiple_mode)
    def _left_multiple(event: E) -> None:
        """
        Move all cursors to the left.
        (But keep all cursors on the same line.)
        """
        buff = event.current_buffer
        new_positions = []

        for p in buff.multiple_cursor_positions:
            if buff.document.translate_index_to_position(p)[1] > 0:
                p -= 1
            new_positions.append(p)

        buff.multiple_cursor_positions = new_positions

        if buff.document.cursor_position_col > 0:
            buff.cursor_position -= 1

    @handle("right", filter=vi_insert_multiple_mode)
    def _right_multiple(event: E) -> None:
        """
        Move all cursors to the right.
        (But keep all cursors on the same line.)
        """
        buff = event.current_buffer
        new_positions = []

        for p in buff.multiple_cursor_positions:
            row, column = buff.document.translate_index_to_position(p)
            if column < len(buff.document.lines[row]):
                p += 1
            new_positions.append(p)

        buff.multiple_cursor_positions = new_positions

        if not buff.document.is_cursor_at_the_end_of_line:
            buff.cursor_position += 1

    @handle("up", filter=vi_insert_multiple_mode)
    @handle("down", filter=vi_insert_multiple_mode)
    def _updown_multiple(event: E) -> None:
        """
        Ignore all up/down key presses when in multiple cursor mode.
        """

    @handle("c-x", "c-l", filter=vi_insert_mode)
    def _complete_line(event: E) -> None:
        """
        Pressing the ControlX - ControlL sequence in Vi mode does line
        completion based on the other lines in the document and the history.
        """
        event.current_buffer.start_history_lines_completion()

    @handle("c-x", "c-f", filter=vi_insert_mode)
    def _complete_filename(event: E) -> None:
        """
        Complete file names.
        """
        # TODO
        pass

    @handle("c-k", filter=vi_insert_mode | vi_replace_mode)
    def _digraph(event: E) -> None:
        """
        Go into digraph mode.
        """
        event.app.vi_state.waiting_for_digraph = True

    @handle(Keys.Any, filter=vi_digraph_mode & ~digraph_symbol_1_given)
    def _digraph1(event: E) -> None:
        """
        First digraph symbol.
        """
        event.app.vi_state.digraph_symbol1 = event.data

    @handle(Keys.Any, filter=vi_digraph_mode & digraph_symbol_1_given)
    def _create_digraph(event: E) -> None:
        """
        Insert digraph.
        """
        try:
            # Lookup.
            code: tuple[str, str] = (
                event.app.vi_state.digraph_symbol1 or "",
                event.data,
            )
            if code not in DIGRAPHS:
                code = code[::-1]  # Try reversing.
            symbol = DIGRAPHS[code]
        except KeyError:
            # Unknown digraph.
            event.app.output.bell()
        else:
            # Insert digraph.
            overwrite = event.app.vi_state.input_mode == InputMode.REPLACE
            event.current_buffer.insert_text(chr(symbol), overwrite=overwrite)
            event.app.vi_state.waiting_for_digraph = False
        finally:
            event.app.vi_state.waiting_for_digraph = False
            event.app.vi_state.digraph_symbol1 = None

    @handle("c-o", filter=vi_insert_mode | vi_replace_mode)
    def _quick_normal_mode(event: E) -> None:
        """
        Go into normal mode for one single action.
        """
        event.app.vi_state.temporary_navigation_mode = True

    @handle("q", Keys.Any, filter=vi_navigation_mode & ~vi_recording_macro)
    def _start_macro(event: E) -> None:
        """
        Start recording macro.
        """
        c = event.key_sequence[1].data
        if c in vi_register_names:
            vi_state = event.app.vi_state

            vi_state.recording_register = c
            vi_state.current_recording = ""

    @handle("q", filter=vi_navigation_mode & vi_recording_macro)
    def _stop_macro(event: E) -> None:
        """
        Stop recording macro.
        """
        vi_state = event.app.vi_state

        # Store and stop recording.
        if vi_state.recording_register:
            vi_state.named_registers[vi_state.recording_register] = ClipboardData(
                vi_state.current_recording
            )
            vi_state.recording_register = None
            vi_state.current_recording = ""

    @handle("@", Keys.Any, filter=vi_navigation_mode, record_in_macro=False)
    def _execute_macro(event: E) -> None:
        """
        Execute macro.

        Notice that we pass `record_in_macro=False`. This ensures that the `@x`
        keys don't appear in the recording itself. This function inserts the
        body of the called macro back into the KeyProcessor, so these keys will
        be added later on to the macro of their handlers have
        `record_in_macro=True`.
        """
        # Retrieve macro.
        c = event.key_sequence[1].data
        try:
            macro = event.app.vi_state.named_registers[c]
        except KeyError:
            return

        # Expand macro (which is a string in the register), in individual keys.
        # Use vt100 parser for this.
        keys: list[KeyPress] = []

        parser = Vt100Parser(keys.append)
        parser.feed(macro.text)
        parser.flush()

        # Now feed keys back to the input processor.
        for _ in range(event.arg):
            event.app.key_processor.feed_multiple(keys, first=True)

    return ConditionalKeyBindings(key_bindings, vi_mode)


def load_vi_search_bindings() -> KeyBindingsBase:
    key_bindings = KeyBindings()
    handle = key_bindings.add
    from . import search

    # Vi-style forward search.
    handle(
        "/",
        filter=(vi_navigation_mode | vi_selection_mode) & ~vi_search_direction_reversed,
    )(search.start_forward_incremental_search)
    handle(
        "?",
        filter=(vi_navigation_mode | vi_selection_mode) & vi_search_direction_reversed,
    )(search.start_forward_incremental_search)
    handle("c-s")(search.start_forward_incremental_search)

    # Vi-style backward search.
    handle(
        "?",
        filter=(vi_navigation_mode | vi_selection_mode) & ~vi_search_direction_reversed,
    )(search.start_reverse_incremental_search)
    handle(
        "/",
        filter=(vi_navigation_mode | vi_selection_mode) & vi_search_direction_reversed,
    )(search.start_reverse_incremental_search)
    handle("c-r")(search.start_reverse_incremental_search)

    # Apply the search. (At the / or ? prompt.)
    handle("enter", filter=is_searching)(search.accept_search)

    handle("c-r", filter=is_searching)(search.reverse_incremental_search)
    handle("c-s", filter=is_searching)(search.forward_incremental_search)

    handle("c-c")(search.abort_search)
    handle("c-g")(search.abort_search)
    handle("backspace", filter=search_buffer_is_empty)(search.abort_search)

    # Handle escape. This should accept the search, just like readline.
    # `abort_search` would be a meaningful alternative.
    handle("escape")(search.accept_search)

    return ConditionalKeyBindings(key_bindings, vi_mode)