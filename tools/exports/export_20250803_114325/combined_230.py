
# === NexusCore/openenv\Lib\site-packages\win32comext\axscript\test\leakTest.py ===
import sys

import pythoncom
from win32com.axscript import axscript
from win32com.axscript.server import axsite
from win32com.server import connect, util


class MySite(axsite.AXSite):
    def OnScriptError(self, error):
        exc = error.GetExceptionInfo()
        context, line, char = error.GetSourcePosition()
        print(" >Exception:", exc[1])
        try:
            st = error.GetSourceLineText()
        except pythoncom.com_error:
            st = None
        if st is None:
            st = ""
        text = st + "\n" + (" " * (char - 1)) + "^" + "\n" + exc[2]
        for line in text.splitlines():
            print("  >" + line)


class MyCollection(util.Collection):
    def _NewEnum(self):
        print("Making new Enumerator")
        return util.Collection._NewEnum(self)


class Test:
    _public_methods_ = ["echo"]
    _public_attrs_ = ["collection", "verbose"]

    def __init__(self):
        self.verbose = 0
        self.collection = util.wrap(MyCollection([1, "Two", 3]))
        self.last = ""

    #    self._connect_server_ = TestConnectServer(self)

    def echo(self, *args):
        self.last = "".join(map(str, args))
        if self.verbose:
            for arg in args:
                print(arg, end=" ")
            print()


#    self._connect_server_.Broadcast(last)


#### Connections currently won't work, as there is no way for the engine to
#### know what events we support.  We need typeinfo support.

IID_ITestEvents = pythoncom.MakeIID("{8EB72F90-0D44-11d1-9C4B-00AA00125A98}")


class TestConnectServer(connect.ConnectableServer):
    _connect_interfaces_ = [IID_ITestEvents]

    # The single public method that the client can call on us
    # (ie, as a normal COM server, this exposes just this single method.
    def __init__(self, object):
        self.object = object

    def Broadcast(self, arg):
        # Simply broadcast a notification.
        self._BroadcastNotify(self.NotifyDoneIt, (arg,))

    def NotifyDoneIt(self, interface, arg):
        interface.Invoke(1000, 0, pythoncom.DISPATCH_METHOD, 1, arg)


VBScript = """\
prop = "Property Value"

sub hello(arg1)
   test.echo arg1
end sub

sub testcollection
   test.verbose = 1
   for each item in test.collection
     test.echo "Collection item is", item
   next
end sub
"""

PyScript = """\
print("PyScript is being parsed...")\n

prop = "Property Value"
def hello(arg1):
   test.echo(arg1)
   pass

def testcollection():
   test.verbose = 1
#   test.collection[1] = "New one"
   for item in test.collection:
     test.echo("Collection item is", item)
   pass
"""

ErrScript = """\
bad code for everyone!
"""


def TestEngine(engineName, code, bShouldWork=1):
    echoer = Test()
    model = {
        "test": util.wrap(echoer),
    }

    site = MySite(model)
    engine = site._AddEngine(engineName)
    engine.AddCode(code, axscript.SCRIPTTEXT_ISPERSISTENT)
    try:
        engine.Start()
    finally:
        if not bShouldWork:
            engine.Close()
            return
    doTestEngine(engine, echoer)
    # re-transition the engine back to the UNINITIALIZED state, a-la ASP.
    engine.eScript.SetScriptState(axscript.SCRIPTSTATE_UNINITIALIZED)
    engine.eScript.SetScriptSite(util.wrap(site))
    print("restarting")
    engine.Start()
    # all done!
    engine.Close()


def doTestEngine(engine, echoer):
    # Now call into the scripts IDispatch
    from win32com.client.dynamic import Dispatch

    ob = Dispatch(engine.GetScriptDispatch())
    try:
        ob.hello("Goober")
    except pythoncom.com_error as exc:
        print("***** Calling 'hello' failed", exc)
        return
    if echoer.last != "Goober":
        print(f"***** Function call didnt set value correctly {echoer.last!r}")

    if str(ob.prop) != "Property Value":
        print(f"***** Property Value not correct - {ob.prop!r}")

    ob.testcollection()

    # Now make sure my engines can evaluate stuff.
    result = engine.eParse.ParseScriptText(
        "1+1", None, None, None, 0, 0, axscript.SCRIPTTEXT_ISEXPRESSION
    )
    if result != 2:
        print("Engine could not evaluate '1+1' - said the result was", result)


def dotestall():
    for i in range(10):
        TestEngine("Python", PyScript)
        print(sys.gettotalrefcount())


# print("Testing Exceptions")
# try:
#     TestEngine("Python", ErrScript, 0)
# except pythoncom.com_error:
#     pass


def testall():
    dotestall()
    pythoncom.CoUninitialize()
    print(
        "AXScript Host worked correctly - %d/%d COM objects left alive."
        % (pythoncom._GetInterfaceCount(), pythoncom._GetGatewayCount())
    )


if __name__ == "__main__":
    testall()

# === NexusCore/tools\gradio_project_export_ui.py ===
# ファイル名: gradio_project_export_ui.py
# メモ:
# - 出力フォルダは「exported_projects」配下にまとめて管理
# - サブフォルダ名は「プロジェクト名_YYYYMMDD_HHMMSS」で分かりやすく自動生成
# - ダウンロードボタンは常に有効化、出力完了時に明確な通知
# - 出力ボタンはvariant="primary"で青色に強調
# - 古いエクスポートフォルダは自動クリーンアップ（1時間）
# - ファイルコピーは自動削除されるのでHDD圧迫を防止

import gradio as gr
import os
import json
import zipfile
import tempfile
import shutil
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

EXPORT_PARENT_DIR = "exported_projects"
os.makedirs(EXPORT_PARENT_DIR, exist_ok=True)
CLEANUP_SECONDS = 60 * 60  # 1時間

def cleanup_exported_projects():
    now = time.time()
    for folder in os.listdir(EXPORT_PARENT_DIR):
        folder_path = os.path.join(EXPORT_PARENT_DIR, folder)
        if os.path.isdir(folder_path):
            try:
                mtime = os.path.getmtime(folder_path)
                if now - mtime > CLEANUP_SECONDS:
                    shutil.rmtree(folder_path)
                    logging.info(f"Cleaned up old export folder: {folder_path}")
            except Exception as e:
                logging.warning(f"Failed to cleanup {folder_path}: {e}")

def export_structure_and_code(uploaded_file, extensions, prefix, suffix):
    cleanup_exported_projects()

    # ファイル名取得
    if hasattr(uploaded_file, "name") and isinstance(uploaded_file.name, str):
        filename = os.path.basename(uploaded_file.name)
        input_path = uploaded_file.name
    elif isinstance(uploaded_file, str):
        filename = os.path.basename(uploaded_file)
        input_path = uploaded_file
    else:
        filename = "uploaded_file"
        input_path = os.path.join(EXPORT_PARENT_DIR, filename)
        with open(input_path, "wb") as f:
            f.write(uploaded_file.read())

    # プロジェクト名・時刻でサブフォルダ名生成
    base_name = os.path.splitext(filename)[0]
    nowstr = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_dir = os.path.join(EXPORT_PARENT_DIR, f"{base_name}_{nowstr}")
    os.makedirs(export_dir, exist_ok=True)

    _, ext = os.path.splitext(filename)
    ext = ext.lower()

    if ext == ".zip":
        try:
            with zipfile.ZipFile(input_path, 'r') as zip_ref:
                zip_ref.extractall(export_dir)
            logging.info(f"Extracted zip to {export_dir}")
        except Exception as e:
            shutil.rmtree(export_dir)
            logging.error(f"ZIP extraction failed: {e}")
            raise gr.Error(f"ZIPファイルの解凍に失敗しました: {e}")
        extracted_items = os.listdir(export_dir)
        if len(extracted_items) == 1 and os.path.isdir(os.path.join(export_dir, extracted_items[0])):
            project_root = os.path.join(export_dir, extracted_items[0])
            folder_name = os.path.basename(project_root)
        else:
            project_root = export_dir
            folder_name = base_name
    else:
        try:
            project_root = os.path.join(export_dir, "single_file_project")
            os.makedirs(project_root, exist_ok=True)
            dest_path = os.path.join(project_root, filename)
            shutil.copy(input_path, dest_path)
            folder_name = base_name
            logging.info(f"Copied file to {dest_path}")
        except Exception as e:
            shutil.rmtree(export_dir)
            logging.error(f"File copy failed: {e}")
            raise gr.Error(f"ファイルのコピーに失敗しました: {e}")

    def create_folder_structure_json(path):
        result = {'name': os.path.basename(path), 'type': 'folder', 'children': []}
        if not os.path.isdir(path):
            return result
        try:
            entries = sorted(os.listdir(path))
        except Exception as e:
            logging.error(f"Failed to listdir {path}: {e}")
            return {'name': os.path.basename(path), 'type': 'folder', 'children': [], 'error': str(e)}
        for entry in entries:
            full_path = os.path.join(path, entry)
            if os.path.isdir(full_path):
                result['children'].append(create_folder_structure_json(full_path))
            else:
                result['children'].append({'name': entry, 'type': 'file'})
        return result

    structure = create_folder_structure_json(project_root)
    structure_json = os.path.join(export_dir, f"{prefix}{folder_name}{suffix}_structure_{nowstr}.json")
    combined_code = os.path.join(export_dir, f"{prefix}{folder_name}{suffix}_combined_code_{nowstr}.txt")

    try:
        with open(structure_json, "w", encoding="utf-8") as f:
            json.dump(structure, f, indent=4, ensure_ascii=False)
        logging.info(f"Saved structure JSON: {structure_json}")
    except Exception as e:
        logging.error(f"Failed to save structure JSON: {e}")
        raise gr.Error(f"構造JSONの保存に失敗: {e}")

    exts = [e.strip() for e in extensions.split(",") if e.strip()]
    files_found = 0
    try:
        with open(combined_code, "w", encoding="utf-8") as outfile:
            for dirpath, _, filenames in os.walk(project_root):
                for filename in sorted(filenames):
                    if any(filename.endswith(ext) for ext in exts):
                        file_path = os.path.join(dirpath, filename)
                        rel_path = os.path.relpath(file_path, project_root)
                        outfile.write(f"\n\n# === File: {rel_path} ===\n\n")
                        try:
                            with open(file_path, "r", encoding="utf-8") as infile:
                                outfile.write(infile.read())
                            files_found += 1
                        except Exception as e:
                            outfile.write(f"[読み込みエラー: {e}]\n")
                            logging.warning(f"Failed to read file {file_path}: {e}")
        logging.info(f"Saved combined code: {combined_code} (files found: {files_found})")
    except Exception as e:
        logging.error(f"Failed to save combined code: {e}")
        raise gr.Error(f"統合コードファイルの保存に失敗: {e}")

    if files_found == 0:
        logging.warning("No files found for the specified extensions.")
        raise gr.Warning("指定した拡張子のファイルが見つかりませんでした。")

    notify_msg = f"出力が完了しました！\n{os.path.basename(export_dir)}\n構造JSON: {os.path.basename(structure_json)}\n統合コード: {os.path.basename(combined_code)}"
    return structure_json, combined_code, notify_msg

with gr.Blocks() as demo:
    gr.Markdown("""
    # プロジェクト構造＆コード統合ファイル 出力ツール
    1. プロジェクトフォルダ(zip)または個別ファイル（.py, .txt, .md, .jsonなど）をアップロード
    2. 統合したい拡張子をカンマ区切りで入力（例: .py,.txt,.md）
    3. 出力ファイル名のプレフィックス・サフィックスを指定（任意）
    4. 「出力」ボタンを押すと、ダウンロードボタンと通知が表示されます
    """)

    file_input = gr.File(
        label="プロジェクトフォルダ（zip）または個別ファイルをアップロード",
        file_types=[".zip", ".py", ".txt", ".md", ".json"]
    )
    ext_input = gr.Textbox(label="統合する拡張子（カンマ区切り）", value=".py,.txt,.md", placeholder=".py,.txt,.md など")
    prefix_input = gr.Textbox(label="出力ファイル名のプレフィックス", value="", placeholder="例: my_")
    suffix_input = gr.Textbox(label="出力ファイル名のサフィックス", value="", placeholder="例: _v1")
    out1 = gr.DownloadButton(label="Download 構造JSON", visible=True)
    out2 = gr.DownloadButton(label="Download 統合コード", visible=True)
    notify = gr.Textbox(label="通知", visible=True)
    btn = gr.Button("出力", interactive=True, variant="primary")  # ここで青色ボタンに

    def enable_btn(file):
        return gr.update(interactive=True)

    file_input.change(enable_btn, inputs=file_input, outputs=btn)

    def on_click(uploaded_file, extensions, prefix, suffix):
        if uploaded_file is None:
            raise gr.Error("zipまたはファイルをアップロードしてください。")
        return export_structure_and_code(uploaded_file, extensions, prefix, suffix)

    btn.click(on_click, inputs=[file_input, ext_input, prefix_input, suffix_input], outputs=[out1, out2, notify])

demo.launch(inbrowser=True)

# === NexusCore/openenv\Lib\site-packages\requests\__init__.py ===
#   __
#  /__)  _  _     _   _ _/   _
# / (   (- (/ (/ (- _)  /  _)
#          /

"""
Requests HTTP Library
~~~~~~~~~~~~~~~~~~~~~

Requests is an HTTP library, written in Python, for human beings.
Basic GET usage:

   >>> import requests
   >>> r = requests.get('https://www.python.org')
   >>> r.status_code
   200
   >>> b'Python is a programming language' in r.content
   True

... or POST:

   >>> payload = dict(key1='value1', key2='value2')
   >>> r = requests.post('https://httpbin.org/post', data=payload)
   >>> print(r.text)
   {
     ...
     "form": {
       "key1": "value1",
       "key2": "value2"
     },
     ...
   }

The other HTTP methods are supported - see `requests.api`. Full documentation
is at <https://requests.readthedocs.io>.

:copyright: (c) 2017 by Kenneth Reitz.
:license: Apache 2.0, see LICENSE for more details.
"""

import warnings

import urllib3

from .exceptions import RequestsDependencyWarning

try:
    from charset_normalizer import __version__ as charset_normalizer_version
except ImportError:
    charset_normalizer_version = None

try:
    from chardet import __version__ as chardet_version
except ImportError:
    chardet_version = None


def check_compatibility(urllib3_version, chardet_version, charset_normalizer_version):
    urllib3_version = urllib3_version.split(".")
    assert urllib3_version != ["dev"]  # Verify urllib3 isn't installed from git.

    # Sometimes, urllib3 only reports its version as 16.1.
    if len(urllib3_version) == 2:
        urllib3_version.append("0")

    # Check urllib3 for compatibility.
    major, minor, patch = urllib3_version  # noqa: F811
    major, minor, patch = int(major), int(minor), int(patch)
    # urllib3 >= 1.21.1
    assert major >= 1
    if major == 1:
        assert minor >= 21

    # Check charset_normalizer for compatibility.
    if chardet_version:
        major, minor, patch = chardet_version.split(".")[:3]
        major, minor, patch = int(major), int(minor), int(patch)
        # chardet_version >= 3.0.2, < 6.0.0
        assert (3, 0, 2) <= (major, minor, patch) < (6, 0, 0)
    elif charset_normalizer_version:
        major, minor, patch = charset_normalizer_version.split(".")[:3]
        major, minor, patch = int(major), int(minor), int(patch)
        # charset_normalizer >= 2.0.0 < 4.0.0
        assert (2, 0, 0) <= (major, minor, patch) < (4, 0, 0)
    else:
        warnings.warn(
            "Unable to find acceptable character detection dependency "
            "(chardet or charset_normalizer).",
            RequestsDependencyWarning,
        )


def _check_cryptography(cryptography_version):
    # cryptography < 1.3.4
    try:
        cryptography_version = list(map(int, cryptography_version.split(".")))
    except ValueError:
        return

    if cryptography_version < [1, 3, 4]:
        warning = "Old version of cryptography ({}) may cause slowdown.".format(
            cryptography_version
        )
        warnings.warn(warning, RequestsDependencyWarning)


# Check imported dependencies for compatibility.
try:
    check_compatibility(
        urllib3.__version__, chardet_version, charset_normalizer_version
    )
except (AssertionError, ValueError):
    warnings.warn(
        "urllib3 ({}) or chardet ({})/charset_normalizer ({}) doesn't match a supported "
        "version!".format(
            urllib3.__version__, chardet_version, charset_normalizer_version
        ),
        RequestsDependencyWarning,
    )

# Attempt to enable urllib3's fallback for SNI support
# if the standard library doesn't support SNI or the
# 'ssl' library isn't available.
try:
    try:
        import ssl
    except ImportError:
        ssl = None

    if not getattr(ssl, "HAS_SNI", False):
        from urllib3.contrib import pyopenssl

        pyopenssl.inject_into_urllib3()

        # Check cryptography version
        from cryptography import __version__ as cryptography_version

        _check_cryptography(cryptography_version)
except ImportError:
    pass

# urllib3's DependencyWarnings should be silenced.
from urllib3.exceptions import DependencyWarning

warnings.simplefilter("ignore", DependencyWarning)

# Set default logging handler to avoid "No handler found" warnings.
import logging
from logging import NullHandler

from . import packages, utils
from .__version__ import (
    __author__,
    __author_email__,
    __build__,
    __cake__,
    __copyright__,
    __description__,
    __license__,
    __title__,
    __url__,
    __version__,
)
from .api import delete, get, head, options, patch, post, put, request
from .exceptions import (
    ConnectionError,
    ConnectTimeout,
    FileModeWarning,
    HTTPError,
    JSONDecodeError,
    ReadTimeout,
    RequestException,
    Timeout,
    TooManyRedirects,
    URLRequired,
)
from .models import PreparedRequest, Request, Response
from .sessions import Session, session
from .status_codes import codes

logging.getLogger(__name__).addHandler(NullHandler())

# FileModeWarnings go off per the default.
warnings.simplefilter("default", FileModeWarning, append=True)

# === NexusCore/openenv\Lib\site-packages\rsa\common.py ===
#  Copyright 2011 Sybren A. Stüvel <sybren@stuvel.eu>
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""Common functionality shared by several modules."""

import typing


class NotRelativePrimeError(ValueError):
    def __init__(self, a: int, b: int, d: int, msg: str = "") -> None:
        super().__init__(msg or "%d and %d are not relatively prime, divider=%i" % (a, b, d))
        self.a = a
        self.b = b
        self.d = d


def bit_size(num: int) -> int:
    """
    Number of bits needed to represent a integer excluding any prefix
    0 bits.

    Usage::

        >>> bit_size(1023)
        10
        >>> bit_size(1024)
        11
        >>> bit_size(1025)
        11

    :param num:
        Integer value. If num is 0, returns 0. Only the absolute value of the
        number is considered. Therefore, signed integers will be abs(num)
        before the number's bit length is determined.
    :returns:
        Returns the number of bits in the integer.
    """

    try:
        return num.bit_length()
    except AttributeError as ex:
        raise TypeError("bit_size(num) only supports integers, not %r" % type(num)) from ex


def byte_size(number: int) -> int:
    """
    Returns the number of bytes required to hold a specific long number.

    The number of bytes is rounded up.

    Usage::

        >>> byte_size(1 << 1023)
        128
        >>> byte_size((1 << 1024) - 1)
        128
        >>> byte_size(1 << 1024)
        129

    :param number:
        An unsigned integer
    :returns:
        The number of bytes required to hold a specific long number.
    """
    if number == 0:
        return 1
    return ceil_div(bit_size(number), 8)


def ceil_div(num: int, div: int) -> int:
    """
    Returns the ceiling function of a division between `num` and `div`.

    Usage::

        >>> ceil_div(100, 7)
        15
        >>> ceil_div(100, 10)
        10
        >>> ceil_div(1, 4)
        1

    :param num: Division's numerator, a number
    :param div: Division's divisor, a number

    :return: Rounded up result of the division between the parameters.
    """
    quanta, mod = divmod(num, div)
    if mod:
        quanta += 1
    return quanta


def extended_gcd(a: int, b: int) -> typing.Tuple[int, int, int]:
    """Returns a tuple (r, i, j) such that r = gcd(a, b) = ia + jb"""
    # r = gcd(a,b) i = multiplicitive inverse of a mod b
    #      or      j = multiplicitive inverse of b mod a
    # Neg return values for i or j are made positive mod b or a respectively
    # Iterateive Version is faster and uses much less stack space
    x = 0
    y = 1
    lx = 1
    ly = 0
    oa = a  # Remember original a/b to remove
    ob = b  # negative values from return results
    while b != 0:
        q = a // b
        (a, b) = (b, a % b)
        (x, lx) = ((lx - (q * x)), x)
        (y, ly) = ((ly - (q * y)), y)
    if lx < 0:
        lx += ob  # If neg wrap modulo original b
    if ly < 0:
        ly += oa  # If neg wrap modulo original a
    return a, lx, ly  # Return only positive values


def inverse(x: int, n: int) -> int:
    """Returns the inverse of x % n under multiplication, a.k.a x^-1 (mod n)

    >>> inverse(7, 4)
    3
    >>> (inverse(143, 4) * 143) % 4
    1
    """

    (divider, inv, _) = extended_gcd(x, n)

    if divider != 1:
        raise NotRelativePrimeError(x, n, divider)

    return inv


def crt(a_values: typing.Iterable[int], modulo_values: typing.Iterable[int]) -> int:
    """Chinese Remainder Theorem.

    Calculates x such that x = a[i] (mod m[i]) for each i.

    :param a_values: the a-values of the above equation
    :param modulo_values: the m-values of the above equation
    :returns: x such that x = a[i] (mod m[i]) for each i


    >>> crt([2, 3], [3, 5])
    8

    >>> crt([2, 3, 2], [3, 5, 7])
    23

    >>> crt([2, 3, 0], [7, 11, 15])
    135
    """

    m = 1
    x = 0

    for modulo in modulo_values:
        m *= modulo

    for (m_i, a_i) in zip(modulo_values, a_values):
        M_i = m // m_i
        inv = inverse(M_i, m_i)

        x = (x + a_i * M_i * inv) % m

    return x


if __name__ == "__main__":
    import doctest

    doctest.testmod()

# === NexusCore/openenv\Lib\site-packages\adodbapi\test\adodbapitestconfig.py ===
# Configure this to _YOUR_ environment in order to run the testcases.
"testADOdbapiConfig.py v 2.6.2.B00"

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# #
# #  TESTERS:
# #
# #  You will need to make numerous modifications to this file
# #  to adapt it to your own testing environment.
# #
# #  Skip down to the next "# #" line --
# #  -- the things you need to change are below it.
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
import platform
import random
import sys

import is64bit
import setuptestframework
import tryconnection

print("\nPython", sys.version)
node = platform.node()
try:
    print(
        "node=%s, is64bit.os()= %s, is64bit.Python()= %s"
        % (node, is64bit.os(), is64bit.Python())
    )
except:
    pass

if "--help" in sys.argv:
    print(
        """Valid command-line switches are:
    --package - create a temporary test package
    --all - run all possible tests
    --time - do time format test
    --nojet - do not test against an ACCESS database file
    --mssql - test against Microsoft SQL server
    --pg - test against PostgreSQL
    --mysql - test against MariaDB
    """
    )
    exit()
try:
    onWindows = bool(sys.getwindowsversion())  # seems to work on all versions of Python
except:
    onWindows = False

# create a random name for temporary table names
_alphabet = (
    "PYFGCRLAOEUIDHTNSQJKXBMWVZ"  # why, yes, I do happen to use a dvorak keyboard
)
tmp = "".join([random.choice(_alphabet) for x in range(9)])
mdb_name = "xx_" + tmp + ".mdb"  # generate a non-colliding name for the temporary .mdb
testfolder = setuptestframework.maketemp()

if "--package" in sys.argv:
    #  create a new adodbapi module
    pth = setuptestframework.makeadopackage(testfolder)
else:
    #  use the adodbapi module in which this file appears
    pth = setuptestframework.find_ado_path()
if pth not in sys.path:
    #  look here _first_ to find modules
    sys.path.insert(1, pth)

# function to clean up the temporary folder -- calling program must run this function before exit.
cleanup = setuptestframework.getcleanupfunction()

import adodbapi  # will (hopefully) be imported using the "pth" discovered above

print(adodbapi.version)  # show version
print(__doc__)

verbose = False
for a in sys.argv:
    if a.startswith("--verbose"):
        arg = True
        try:
            arg = int(a.split("=")[1])
        except IndexError:
            pass
        adodbapi.adodbapi.verbose = arg
        verbose = arg

doAllTests = "--all" in sys.argv
doAccessTest = not ("--nojet" in sys.argv)
doSqlServerTest = "--mssql" in sys.argv or doAllTests
doMySqlTest = "--mysql" in sys.argv or doAllTests
doPostgresTest = "--pg" in sys.argv or doAllTests
doTimeTest = ("--time" in sys.argv or doAllTests) and onWindows

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # start your environment setup here v v v
SQL_HOST_NODE = "testsql.2txt.us,1430"

if doAccessTest:
    c = {
        "mdb": setuptestframework.makemdb(testfolder, mdb_name),
        # macro definition for keyword "provider"  using macro "is64bit" -- see documentation
        # is64bit will return true for 64 bit versions of Python, so the macro will select the ACE provider
        "macro_is64bit": [
            "provider",
            "Microsoft.ACE.OLEDB.12.0",  # 64 bit provider
            "Microsoft.Jet.OLEDB.4.0",  # 32 bit provider
        ],
    }

    # ;Mode=ReadWrite;Persist Security Info=False;Jet OLEDB:Bypass UserInfo Validation=True"
    connStrAccess = "Provider=%(provider)s;Data Source=%(mdb)s"
    print("    ...Testing ACCESS connection to {} file...".format(c["mdb"]))
    doAccessTest, connStrAccess, dbAccessconnect = tryconnection.try_connection(
        verbose, connStrAccess, 10, **c
    )

if doSqlServerTest:
    c = {
        "host": SQL_HOST_NODE,  # name of computer with SQL Server
        "database": "adotest",
        "user": "adotestuser",  # None implies Windows security
        "password": "Sq1234567",
        # macro definition for keyword "security" using macro "auto_security"
        "macro_auto_security": "security",
        "provider": "MSOLEDBSQL; MARS Connection=True",
    }
    connStr = "Provider=%(provider)s; Initial Catalog=%(database)s; Data Source=%(host)s; %(security)s;"
    print("    ...Testing MS-SQL login to {}...".format(c["host"]))
    (
        doSqlServerTest,
        connStrSQLServer,
        dbSqlServerconnect,
    ) = tryconnection.try_connection(verbose, connStr, 30, **c)

if doMySqlTest:
    c = {
        "host": "testmysql.2txt.us",
        "database": "adodbapitest",
        "user": "adotest",
        "password": "12345678",
        "port": "3330",  # note the nonstandard port for obfuscation
        "driver": "MySQL ODBC 5.1 Driver",
    }  # or _driver="MySQL ODBC 3.51 Driver
    c["macro_is64bit"] = [
        "provider",
        "Provider=MSDASQL;",
    ]  # turn on the 64 bit ODBC adapter only if needed
    cs = (
        "%(provider)sDriver={%(driver)s};Server=%(host)s;Port=3330;"
        + "Database=%(database)s;user=%(user)s;password=%(password)s;Option=3;"
    )
    print("    ...Testing MySql login to {}...".format(c["host"]))
    doMySqlTest, connStrMySql, dbMySqlconnect = tryconnection.try_connection(
        verbose, cs, 5, **c
    )


if doPostgresTest:
    _computername = "testpg.2txt.us"
    _databasename = "adotest"
    _username = "adotestuser"
    _password = "12345678"
    kws = {"timeout": 4}
    kws["macro_is64bit"] = [
        "prov_drv",
        "Provider=MSDASQL;Driver={PostgreSQL Unicode(x64)}",
        "Driver=PostgreSQL Unicode",
    ]
    # get driver from https://www.postgresql.org/ftp/odbc/releases/
    # test using positional and keyword arguments (bad example for real code)
    print("    ...Testing PostgreSQL login to {}...".format(_computername))
    doPostgresTest, connStrPostgres, dbPostgresConnect = tryconnection.try_connection(
        verbose,
        "%(prov_drv)s;Server=%(host)s;Database=%(database)s;uid=%(user)s;pwd=%(password)s;port=5430;",  # note nonstandard port
        _username,
        _password,
        _computername,
        _databasename,
        **kws,
    )

assert (
    doAccessTest or doSqlServerTest or doMySqlTest or doPostgresTest
), "No database engine found for testing"

# === NexusCore/openenv\Lib\site-packages\fontTools\subset\cff.py ===
from fontTools.misc import psCharStrings
from fontTools import ttLib
from fontTools.pens.basePen import NullPen
from fontTools.misc.roundTools import otRound
from fontTools.misc.loggingTools import deprecateFunction
from fontTools.subset.util import _add_method, _uniq_sort


class _ClosureGlyphsT2Decompiler(psCharStrings.SimpleT2Decompiler):
    def __init__(self, components, localSubrs, globalSubrs):
        psCharStrings.SimpleT2Decompiler.__init__(self, localSubrs, globalSubrs)
        self.components = components

    def op_endchar(self, index):
        args = self.popall()
        if len(args) >= 4:
            from fontTools.encodings.StandardEncoding import StandardEncoding

            # endchar can do seac accent bulding; The T2 spec says it's deprecated,
            # but recent software that shall remain nameless does output it.
            adx, ady, bchar, achar = args[-4:]
            baseGlyph = StandardEncoding[bchar]
            accentGlyph = StandardEncoding[achar]
            self.components.add(baseGlyph)
            self.components.add(accentGlyph)


@_add_method(ttLib.getTableClass("CFF "))
def closure_glyphs(self, s):
    cff = self.cff
    assert len(cff) == 1
    font = cff[cff.keys()[0]]
    glyphSet = font.CharStrings

    decompose = s.glyphs
    while decompose:
        components = set()
        for g in decompose:
            if g not in glyphSet:
                continue
            gl = glyphSet[g]

            subrs = getattr(gl.private, "Subrs", [])
            decompiler = _ClosureGlyphsT2Decompiler(components, subrs, gl.globalSubrs)
            decompiler.execute(gl)
        components -= s.glyphs
        s.glyphs.update(components)
        decompose = components


def _empty_charstring(font, glyphName, isCFF2, ignoreWidth=False):
    c, fdSelectIndex = font.CharStrings.getItemAndSelector(glyphName)
    if isCFF2 or ignoreWidth:
        # CFF2 charstrings have no widths nor 'endchar' operators
        c.setProgram([] if isCFF2 else ["endchar"])
    else:
        if hasattr(font, "FDArray") and font.FDArray is not None:
            private = font.FDArray[fdSelectIndex].Private
        else:
            private = font.Private
        dfltWdX = private.defaultWidthX
        nmnlWdX = private.nominalWidthX
        pen = NullPen()
        c.draw(pen)  # this will set the charstring's width
        if c.width != dfltWdX:
            c.program = [c.width - nmnlWdX, "endchar"]
        else:
            c.program = ["endchar"]


@_add_method(ttLib.getTableClass("CFF "))
def prune_pre_subset(self, font, options):
    cff = self.cff
    # CFF table must have one font only
    cff.fontNames = cff.fontNames[:1]

    if options.notdef_glyph and not options.notdef_outline:
        isCFF2 = cff.major > 1
        for fontname in cff.keys():
            font = cff[fontname]
            _empty_charstring(font, ".notdef", isCFF2=isCFF2)

    # Clear useless Encoding
    for fontname in cff.keys():
        font = cff[fontname]
        # https://github.com/fonttools/fonttools/issues/620
        font.Encoding = "StandardEncoding"

    return True  # bool(cff.fontNames)


@_add_method(ttLib.getTableClass("CFF "))
def subset_glyphs(self, s):
    cff = self.cff
    for fontname in cff.keys():
        font = cff[fontname]
        cs = font.CharStrings

        glyphs = s.glyphs.union(s.glyphs_emptied)

        # Load all glyphs
        for g in font.charset:
            if g not in glyphs:
                continue
            c, _ = cs.getItemAndSelector(g)

        if cs.charStringsAreIndexed:
            indices = [i for i, g in enumerate(font.charset) if g in glyphs]
            csi = cs.charStringsIndex
            csi.items = [csi.items[i] for i in indices]
            del csi.file, csi.offsets
            if hasattr(font, "FDSelect"):
                sel = font.FDSelect
                sel.format = None
                sel.gidArray = [sel.gidArray[i] for i in indices]
            newCharStrings = {}
            for indicesIdx, charsetIdx in enumerate(indices):
                g = font.charset[charsetIdx]
                if g in cs.charStrings:
                    newCharStrings[g] = indicesIdx
            cs.charStrings = newCharStrings
        else:
            cs.charStrings = {g: v for g, v in cs.charStrings.items() if g in glyphs}
        font.charset = [g for g in font.charset if g in glyphs]
        font.numGlyphs = len(font.charset)

        if s.options.retain_gids:
            isCFF2 = cff.major > 1
            for g in s.glyphs_emptied:
                _empty_charstring(font, g, isCFF2=isCFF2, ignoreWidth=True)

    return True  # any(cff[fontname].numGlyphs for fontname in cff.keys())


@_add_method(ttLib.getTableClass("CFF "))
def prune_post_subset(self, ttfFont, options):
    cff = self.cff
    for fontname in cff.keys():
        font = cff[fontname]
        cs = font.CharStrings

        # Drop unused FontDictionaries
        if hasattr(font, "FDSelect"):
            sel = font.FDSelect
            indices = _uniq_sort(sel.gidArray)
            sel.gidArray = [indices.index(ss) for ss in sel.gidArray]
            arr = font.FDArray
            arr.items = [arr[i] for i in indices]
            del arr.file, arr.offsets

    # Desubroutinize if asked for
    if options.desubroutinize:
        cff.desubroutinize()

    # Drop hints if not needed
    if not options.hinting:
        self.remove_hints()
    elif not options.desubroutinize:
        self.remove_unused_subroutines()
    return True


@deprecateFunction(
    "use 'CFFFontSet.desubroutinize()' instead", category=DeprecationWarning
)
@_add_method(ttLib.getTableClass("CFF "))
def desubroutinize(self):
    self.cff.desubroutinize()


@deprecateFunction(
    "use 'CFFFontSet.remove_hints()' instead", category=DeprecationWarning
)
@_add_method(ttLib.getTableClass("CFF "))
def remove_hints(self):
    self.cff.remove_hints()


@deprecateFunction(
    "use 'CFFFontSet.remove_unused_subroutines' instead", category=DeprecationWarning
)
@_add_method(ttLib.getTableClass("CFF "))
def remove_unused_subroutines(self):
    self.cff.remove_unused_subroutines()

# === NexusCore/openenv\Lib\site-packages\litellm\llms\anthropic\experimental_pass_through\adapters\streaming_iterator.py ===
# What is this?
## Translates OpenAI call to Anthropic `/v1/messages` format
import json
import traceback
from typing import Any, AsyncIterator, Iterator, Optional

from litellm import verbose_logger
from litellm.types.llms.anthropic import UsageDelta
from litellm.types.utils import AdapterCompletionStreamWrapper


class AnthropicStreamWrapper(AdapterCompletionStreamWrapper):
    """
    - first chunk return 'message_start'
    - content block must be started and stopped
    - finish_reason must map exactly to anthropic reason, else anthropic client won't be able to parse it.
    """

    sent_first_chunk: bool = False
    sent_content_block_start: bool = False
    sent_content_block_finish: bool = False
    sent_last_message: bool = False
    holding_chunk: Optional[Any] = None

    def __next__(self):
        from .transformation import LiteLLMAnthropicMessagesAdapter

        try:
            if self.sent_first_chunk is False:
                self.sent_first_chunk = True
                return {
                    "type": "message_start",
                    "message": {
                        "id": "msg_1nZdL29xx5MUA1yADyHTEsnR8uuvGzszyY",
                        "type": "message",
                        "role": "assistant",
                        "content": [],
                        "model": "claude-3-5-sonnet-20240620",
                        "stop_reason": None,
                        "stop_sequence": None,
                        "usage": UsageDelta(input_tokens=0, output_tokens=0),
                    },
                }
            if self.sent_content_block_start is False:
                self.sent_content_block_start = True
                return {
                    "type": "content_block_start",
                    "index": 0,
                    "content_block": {"type": "text", "text": ""},
                }

            for chunk in self.completion_stream:
                if chunk == "None" or chunk is None:
                    raise Exception

                processed_chunk = LiteLLMAnthropicMessagesAdapter().translate_streaming_openai_response_to_anthropic(
                    response=chunk
                )
                if (
                    processed_chunk["type"] == "message_delta"
                    and self.sent_content_block_finish is False
                ):
                    self.holding_chunk = processed_chunk
                    self.sent_content_block_finish = True
                    return {
                        "type": "content_block_stop",
                        "index": 0,
                    }
                elif self.holding_chunk is not None:
                    return_chunk = self.holding_chunk
                    self.holding_chunk = processed_chunk
                    return return_chunk
                else:
                    return processed_chunk
            if self.holding_chunk is not None:
                return_chunk = self.holding_chunk
                self.holding_chunk = None
                return return_chunk
            if self.sent_last_message is False:
                self.sent_last_message = True
                return {"type": "message_stop"}
            raise StopIteration
        except StopIteration:
            if self.sent_last_message is False:
                self.sent_last_message = True
                return {"type": "message_stop"}
            raise StopIteration
        except Exception as e:
            verbose_logger.error(
                "Anthropic Adapter - {}\n{}".format(e, traceback.format_exc())
            )
            raise StopAsyncIteration

    async def __anext__(self):
        from .transformation import LiteLLMAnthropicMessagesAdapter

        try:
            if self.sent_first_chunk is False:
                self.sent_first_chunk = True
                return {
                    "type": "message_start",
                    "message": {
                        "id": "msg_1nZdL29xx5MUA1yADyHTEsnR8uuvGzszyY",
                        "type": "message",
                        "role": "assistant",
                        "content": [],
                        "model": "claude-3-5-sonnet-20240620",
                        "stop_reason": None,
                        "stop_sequence": None,
                        "usage": UsageDelta(input_tokens=0, output_tokens=0),
                    },
                }
            if self.sent_content_block_start is False:
                self.sent_content_block_start = True
                return {
                    "type": "content_block_start",
                    "index": 0,
                    "content_block": {"type": "text", "text": ""},
                }
            async for chunk in self.completion_stream:
                if chunk == "None" or chunk is None:
                    raise Exception
                processed_chunk = LiteLLMAnthropicMessagesAdapter().translate_streaming_openai_response_to_anthropic(
                    response=chunk
                )
                if (
                    processed_chunk["type"] == "message_delta"
                    and self.sent_content_block_finish is False
                ):
                    self.holding_chunk = processed_chunk
                    self.sent_content_block_finish = True
                    return {
                        "type": "content_block_stop",
                        "index": 0,
                    }
                elif self.holding_chunk is not None:
                    return_chunk = self.holding_chunk
                    self.holding_chunk = processed_chunk
                    return return_chunk
                else:
                    return processed_chunk
            if self.holding_chunk is not None:
                return_chunk = self.holding_chunk
                self.holding_chunk = None
                return return_chunk
            if self.sent_last_message is False:
                self.sent_last_message = True
                return {"type": "message_stop"}
            raise StopIteration
        except StopIteration:
            if self.sent_last_message is False:
                self.sent_last_message = True
                return {"type": "message_stop"}
            raise StopAsyncIteration

    def anthropic_sse_wrapper(self) -> Iterator[bytes]:
        """
        Convert AnthropicStreamWrapper dict chunks to Server-Sent Events format.
        Similar to the Bedrock bedrock_sse_wrapper implementation.

        This wrapper ensures dict chunks are SSE formatted with both event and data lines.
        """
        for chunk in self:
            if isinstance(chunk, dict):
                event_type: str = str(chunk.get("type", "message"))
                payload = f"event: {event_type}\ndata: {json.dumps(chunk)}\n\n"
                yield payload.encode()
            else:
                # For non-dict chunks, forward the original value unchanged
                yield chunk

    async def async_anthropic_sse_wrapper(self) -> AsyncIterator[bytes]:
        """
        Async version of anthropic_sse_wrapper.
        Convert AnthropicStreamWrapper dict chunks to Server-Sent Events format.
        """
        async for chunk in self:
            if isinstance(chunk, dict):
                event_type: str = str(chunk.get("type", "message"))
                payload = f"event: {event_type}\ndata: {json.dumps(chunk)}\n\n"
                yield payload.encode()
            else:
                # For non-dict chunks, forward the original value unchanged
                yield chunk

# === NexusCore/openenv\Lib\site-packages\nltk\classify\megam.py ===
# Natural Language Toolkit: Interface to Megam Classifier
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A set of functions used to interface with the external megam_ maxent
optimization package. Before megam can be used, you should tell NLTK where it
can find the megam binary, using the ``config_megam()`` function. Typical
usage:

    >>> from nltk.classify import megam
    >>> megam.config_megam() # pass path to megam if not found in PATH # doctest: +SKIP
    [Found megam: ...]

Use with MaxentClassifier. Example below, see MaxentClassifier documentation
for details.

    nltk.classify.MaxentClassifier.train(corpus, 'megam')

.. _megam: https://www.umiacs.umd.edu/~hal/megam/index.html
"""
import subprocess

from nltk.internals import find_binary

try:
    import numpy
except ImportError:
    numpy = None

######################################################################
# { Configuration
######################################################################

_megam_bin = None


def config_megam(bin=None):
    """
    Configure NLTK's interface to the ``megam`` maxent optimization
    package.

    :param bin: The full path to the ``megam`` binary.  If not specified,
        then nltk will search the system for a ``megam`` binary; and if
        one is not found, it will raise a ``LookupError`` exception.
    :type bin: str
    """
    global _megam_bin
    _megam_bin = find_binary(
        "megam",
        bin,
        env_vars=["MEGAM"],
        binary_names=["megam.opt", "megam", "megam_686", "megam_i686.opt"],
        url="https://www.umiacs.umd.edu/~hal/megam/index.html",
    )


######################################################################
# { Megam Interface Functions
######################################################################


def write_megam_file(train_toks, encoding, stream, bernoulli=True, explicit=True):
    """
    Generate an input file for ``megam`` based on the given corpus of
    classified tokens.

    :type train_toks: list(tuple(dict, str))
    :param train_toks: Training data, represented as a list of
        pairs, the first member of which is a feature dictionary,
        and the second of which is a classification label.

    :type encoding: MaxentFeatureEncodingI
    :param encoding: A feature encoding, used to convert featuresets
        into feature vectors. May optionally implement a cost() method
        in order to assign different costs to different class predictions.

    :type stream: stream
    :param stream: The stream to which the megam input file should be
        written.

    :param bernoulli: If true, then use the 'bernoulli' format.  I.e.,
        all joint features have binary values, and are listed iff they
        are true.  Otherwise, list feature values explicitly.  If
        ``bernoulli=False``, then you must call ``megam`` with the
        ``-fvals`` option.

    :param explicit: If true, then use the 'explicit' format.  I.e.,
        list the features that would fire for any of the possible
        labels, for each token.  If ``explicit=True``, then you must
        call ``megam`` with the ``-explicit`` option.
    """
    # Look up the set of labels.
    labels = encoding.labels()
    labelnum = {label: i for (i, label) in enumerate(labels)}

    # Write the file, which contains one line per instance.
    for featureset, label in train_toks:
        # First, the instance number (or, in the weighted multiclass case, the cost of each label).
        if hasattr(encoding, "cost"):
            stream.write(
                ":".join(str(encoding.cost(featureset, label, l)) for l in labels)
            )
        else:
            stream.write("%d" % labelnum[label])

        # For implicit file formats, just list the features that fire
        # for this instance's actual label.
        if not explicit:
            _write_megam_features(encoding.encode(featureset, label), stream, bernoulli)

        # For explicit formats, list the features that would fire for
        # any of the possible labels.
        else:
            for l in labels:
                stream.write(" #")
                _write_megam_features(encoding.encode(featureset, l), stream, bernoulli)

        # End of the instance.
        stream.write("\n")


def parse_megam_weights(s, features_count, explicit=True):
    """
    Given the stdout output generated by ``megam`` when training a
    model, return a ``numpy`` array containing the corresponding weight
    vector.  This function does not currently handle bias features.
    """
    if numpy is None:
        raise ValueError("This function requires that numpy be installed")
    assert explicit, "non-explicit not supported yet"
    lines = s.strip().split("\n")
    weights = numpy.zeros(features_count, "d")
    for line in lines:
        if line.strip():
            fid, weight = line.split()
            weights[int(fid)] = float(weight)
    return weights


def _write_megam_features(vector, stream, bernoulli):
    if not vector:
        raise ValueError(
            "MEGAM classifier requires the use of an " "always-on feature."
        )
    for fid, fval in vector:
        if bernoulli:
            if fval == 1:
                stream.write(" %s" % fid)
            elif fval != 0:
                raise ValueError(
                    "If bernoulli=True, then all" "features must be binary."
                )
        else:
            stream.write(f" {fid} {fval}")


def call_megam(args):
    """
    Call the ``megam`` binary with the given arguments.
    """
    if isinstance(args, str):
        raise TypeError("args should be a list of strings")
    if _megam_bin is None:
        config_megam()

    # Call megam via a subprocess
    cmd = [_megam_bin] + args
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    (stdout, stderr) = p.communicate()

    # Check the return code.
    if p.returncode != 0:
        print()
        print(stderr)
        raise OSError("megam command failed!")

    if isinstance(stdout, str):
        return stdout
    else:
        return stdout.decode("utf-8")

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\styles\base.py ===
"""
The base classes for the styling.
"""

from __future__ import annotations

from abc import ABCMeta, abstractmethod, abstractproperty
from typing import Callable, Hashable, NamedTuple

__all__ = [
    "Attrs",
    "DEFAULT_ATTRS",
    "ANSI_COLOR_NAMES",
    "ANSI_COLOR_NAMES_ALIASES",
    "BaseStyle",
    "DummyStyle",
    "DynamicStyle",
]


#: Style attributes.
class Attrs(NamedTuple):
    color: str | None
    bgcolor: str | None
    bold: bool | None
    underline: bool | None
    strike: bool | None
    italic: bool | None
    blink: bool | None
    reverse: bool | None
    hidden: bool | None


"""
:param color: Hexadecimal string. E.g. '000000' or Ansi color name: e.g. 'ansiblue'
:param bgcolor: Hexadecimal string. E.g. 'ffffff' or Ansi color name: e.g. 'ansired'
:param bold: Boolean
:param underline: Boolean
:param strike: Boolean
:param italic: Boolean
:param blink: Boolean
:param reverse: Boolean
:param hidden: Boolean
"""

#: The default `Attrs`.
DEFAULT_ATTRS = Attrs(
    color="",
    bgcolor="",
    bold=False,
    underline=False,
    strike=False,
    italic=False,
    blink=False,
    reverse=False,
    hidden=False,
)


#: ``Attrs.bgcolor/fgcolor`` can be in either 'ffffff' format, or can be any of
#: the following in case we want to take colors from the 8/16 color palette.
#: Usually, in that case, the terminal application allows to configure the RGB
#: values for these names.
#: ISO 6429 colors
ANSI_COLOR_NAMES = [
    "ansidefault",
    # Low intensity, dark.  (One or two components 0x80, the other 0x00.)
    "ansiblack",
    "ansired",
    "ansigreen",
    "ansiyellow",
    "ansiblue",
    "ansimagenta",
    "ansicyan",
    "ansigray",
    # High intensity, bright. (One or two components 0xff, the other 0x00. Not supported everywhere.)
    "ansibrightblack",
    "ansibrightred",
    "ansibrightgreen",
    "ansibrightyellow",
    "ansibrightblue",
    "ansibrightmagenta",
    "ansibrightcyan",
    "ansiwhite",
]


# People don't use the same ANSI color names everywhere. In prompt_toolkit 1.0
# we used some unconventional names (which were contributed like that to
# Pygments). This is fixed now, but we still support the old names.

# The table below maps the old aliases to the current names.
ANSI_COLOR_NAMES_ALIASES: dict[str, str] = {
    "ansidarkgray": "ansibrightblack",
    "ansiteal": "ansicyan",
    "ansiturquoise": "ansibrightcyan",
    "ansibrown": "ansiyellow",
    "ansipurple": "ansimagenta",
    "ansifuchsia": "ansibrightmagenta",
    "ansilightgray": "ansigray",
    "ansidarkred": "ansired",
    "ansidarkgreen": "ansigreen",
    "ansidarkblue": "ansiblue",
}
assert set(ANSI_COLOR_NAMES_ALIASES.values()).issubset(set(ANSI_COLOR_NAMES))
assert not (set(ANSI_COLOR_NAMES_ALIASES.keys()) & set(ANSI_COLOR_NAMES))


class BaseStyle(metaclass=ABCMeta):
    """
    Abstract base class for prompt_toolkit styles.
    """

    @abstractmethod
    def get_attrs_for_style_str(
        self, style_str: str, default: Attrs = DEFAULT_ATTRS
    ) -> Attrs:
        """
        Return :class:`.Attrs` for the given style string.

        :param style_str: The style string. This can contain inline styling as
            well as classnames (e.g. "class:title").
        :param default: `Attrs` to be used if no styling was defined.
        """

    @abstractproperty
    def style_rules(self) -> list[tuple[str, str]]:
        """
        The list of style rules, used to create this style.
        (Required for `DynamicStyle` and `_MergedStyle` to work.)
        """
        return []

    @abstractmethod
    def invalidation_hash(self) -> Hashable:
        """
        Invalidation hash for the style. When this changes over time, the
        renderer knows that something in the style changed, and that everything
        has to be redrawn.
        """


class DummyStyle(BaseStyle):
    """
    A style that doesn't style anything.
    """

    def get_attrs_for_style_str(
        self, style_str: str, default: Attrs = DEFAULT_ATTRS
    ) -> Attrs:
        return default

    def invalidation_hash(self) -> Hashable:
        return 1  # Always the same value.

    @property
    def style_rules(self) -> list[tuple[str, str]]:
        return []


class DynamicStyle(BaseStyle):
    """
    Style class that can dynamically returns an other Style.

    :param get_style: Callable that returns a :class:`.Style` instance.
    """

    def __init__(self, get_style: Callable[[], BaseStyle | None]):
        self.get_style = get_style
        self._dummy = DummyStyle()

    def get_attrs_for_style_str(
        self, style_str: str, default: Attrs = DEFAULT_ATTRS
    ) -> Attrs:
        style = self.get_style() or self._dummy

        return style.get_attrs_for_style_str(style_str, default)

    def invalidation_hash(self) -> Hashable:
        return (self.get_style() or self._dummy).invalidation_hash()

    @property
    def style_rules(self) -> list[tuple[str, str]]:
        return (self.get_style() or self._dummy).style_rules

# === NexusCore/openenv\Lib\site-packages\win32com\test\testMSOffice.py ===
# Test MSOffice
#
# Main purpose of test is to ensure that Dynamic COM objects
# work as expected.

# Assumes Word and Excel installed on your machine.

import traceback

import pythoncom
import win32api
import win32com
import win32com.client.dynamic
from win32com.client import gencache
from win32com.test.util import CheckClean


# Test a few of the MSOffice components.
def TestWord():
    try:
        # Office 97 - _totally_ different object model!
        word7 = win32com.client.Dispatch("Word.Basic")
        # Check if any property needed by TestWord7 is not None
        if word7.FileNew:
            print("Starting Word 7 for dynamic test")
            TestWord7(word7)
        else:
            # NOTE - using "client.Dispatch" would return an msword8.py instance!
            print("Starting Word 8 for dynamic test")
            word = win32com.client.dynamic.Dispatch("Word.Application")
            TestWord8(word)

            word = None
            # Now we will test Dispatch without the new "lazy" capabilities
            print("Starting Word 8 for non-lazy dynamic test")
            dispatch = win32com.client.dynamic._GetGoodDispatch("Word.Application")
            typeinfo = dispatch.GetTypeInfo()
            attr = typeinfo.GetTypeAttr()
            olerepr = win32com.client.build.DispatchItem(typeinfo, attr, None, 0)
            word = win32com.client.dynamic.CDispatch(dispatch, olerepr)
            dispatch = typeinfo = attr = olerepr = None
            TestWord8(word)
    except Exception as e:
        print("Word dynamic tests failed", e)
        traceback.print_exc()

    print("Starting MSWord for generated test")
    try:
        from win32com.client import gencache

        word = gencache.EnsureDispatch("Word.Application.8")
        TestWord8(word)
    except Exception as e:
        print("Word generated tests failed", e)
        traceback.print_exc()


def TestWord7(word):
    word.FileNew()
    # If not shown, show the app.
    if not word.AppShow():
        word._proc_("AppShow")

    for i in range(12):
        word.FormatFont(Color=i + 1, Points=i + 12)
        word.Insert("Hello from Python %d\n" % i)

    word.FileClose(2)


def TestWord8(word):
    word.Visible = 1
    doc = word.Documents.Add()
    wrange = doc.Range()
    for i in range(10):
        wrange.InsertAfter(f"Hello from Python {i + 1}\n")
    paras = doc.Paragraphs
    if int(word.Version.split(".")[0]) >= 16:
        # With Word 16 / Word 2019
        for i, p in enumerate(paras):
            p.Range.Font.ColorIndex = i + 1
            p.Range.Font.Size = 12 + (4 * i)
    else:
        # NOTE: Iterating on paras doesn't seem to work - no error, just doesn't work
        # for para in paras:
        #     para().Font...
        for i in range(len(paras)):
            p = paras(i + 1)
            p.Font.ColorIndex = i + 1
            p.Font.Size = 12 + (4 * i)
    doc.Close(SaveChanges=False)
    word.Quit()
    win32api.Sleep(1000)  # Wait for word to close, else we may get OA error.


def TestWord8OldStyle():
    try:
        import win32com.test.Generated4Test.msword8
    except ImportError:
        print("Can not do old style test")


def TextExcel(xl):
    xl.Visible = 0
    assert not xl.Visible, "Visible property is true."
    xl.Visible = 1
    assert xl.Visible, "Visible property not true."

    xl.Workbooks.Add()

    xl.Range("A1:C1").Value = (1, 2, 3)
    xl.Range("A2:C2").Value = ("x", "y", "z")
    xl.Range("A3:C3").Value = ("3", "2", "1")

    for i in range(20):
        xl.Cells(i + 1, i + 1).Value = "Hi %d" % i

    assert xl.Range("A1").Value == "Hi 0", "Single cell range failed"
    assert xl.Range("A1:B1").Value == (
        ("Hi 0", 2),
    ), "flat-horizontal cell range failed"
    assert xl.Range("A1:A2").Value == (
        ("Hi 0",),
        ("x",),
    ), "flat-vertical cell range failed"
    assert xl.Range("A1:C3").Value == (
        ("Hi 0", 2, 3),
        ("x", "Hi 1", "z"),
        (3, 2, "Hi 2"),
    ), "square cell range failed"

    xl.Range("A1:C3").Value = ((3, 2, 1), ("x", "y", "z"), (1, 2, 3))

    assert xl.Range("A1:C3").Value == (
        (3, 2, 1),
        ("x", "y", "z"),
        (1, 2, 3),
    ), "Range was not what I set it to!"

    # test dates out with Excel
    xl.Cells(5, 1).Value = "Excel time"
    xl.Cells(5, 2).Formula = "=Now()"

    import time

    xl.Cells(6, 1).Value = "Python time"
    xl.Cells(6, 2).Value = pythoncom.MakeTime(time.time())
    xl.Cells(6, 2).NumberFormat = "d/mm/yy h:mm"
    xl.Columns("A:B").EntireColumn.AutoFit()

    xl.Workbooks(1).Close(0)
    xl.Quit()


def TestAll():
    TestWord()

    try:
        print("Starting Excel for Dynamic test...")
        xl = win32com.client.dynamic.Dispatch("Excel.Application")
        TextExcel(xl)
    except Exception as e:
        worked = False
        print("Excel tests failed", e)
        traceback.print_exc()

    try:
        print("Starting Excel 8 for generated excel8.py test...")
        mod = gencache.EnsureModule(
            "{00020813-0000-0000-C000-000000000046}", 0, 1, 2, bForDemand=True
        )
        xl = win32com.client.Dispatch("Excel.Application")
        TextExcel(xl)
    except ImportError:
        print("Could not import the generated Excel 97 wrapper")
    except Exception as e:
        print("Generated Excel tests failed", e)
        traceback.print_exc()


if __name__ == "__main__":
    TestAll()
    CheckClean()
    pythoncom.CoUninitialize()

# === NexusCore/openenv\Lib\site-packages\googleapiclient\mimeparse.py ===
# Copyright 2014 Joe Gregorio
#
# Licensed under the MIT License

"""MIME-Type Parser

This module provides basic functions for handling mime-types. It can handle
matching mime-types against a list of media-ranges. See section 14.1 of the
HTTP specification [RFC 2616] for a complete explanation.

   http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.1

Contents:
 - parse_mime_type():   Parses a mime-type into its component parts.
 - parse_media_range(): Media-ranges are mime-types with wild-cards and a 'q'
                          quality parameter.
 - quality():           Determines the quality ('q') of a mime-type when
                          compared against a list of media-ranges.
 - quality_parsed():    Just like quality() except the second parameter must be
                          pre-parsed.
 - best_match():        Choose the mime-type with the highest quality ('q')
                          from a list of candidates.
"""
from __future__ import absolute_import

from functools import reduce

__version__ = "0.1.3"
__author__ = "Joe Gregorio"
__email__ = "joe@bitworking.org"
__license__ = "MIT License"
__credits__ = ""


def parse_mime_type(mime_type):
    """Parses a mime-type into its component parts.

    Carves up a mime-type and returns a tuple of the (type, subtype, params)
    where 'params' is a dictionary of all the parameters for the media range.
    For example, the media range 'application/xhtml;q=0.5' would get parsed
    into:

       ('application', 'xhtml', {'q', '0.5'})
    """
    parts = mime_type.split(";")
    params = dict(
        [tuple([s.strip() for s in param.split("=", 1)]) for param in parts[1:]]
    )
    full_type = parts[0].strip()
    # Java URLConnection class sends an Accept header that includes a
    # single '*'. Turn it into a legal wildcard.
    if full_type == "*":
        full_type = "*/*"
    (type, subtype) = full_type.split("/")

    return (type.strip(), subtype.strip(), params)


def parse_media_range(range):
    """Parse a media-range into its component parts.

    Carves up a media range and returns a tuple of the (type, subtype,
    params) where 'params' is a dictionary of all the parameters for the media
    range.  For example, the media range 'application/*;q=0.5' would get parsed
    into:

       ('application', '*', {'q', '0.5'})

    In addition this function also guarantees that there is a value for 'q'
    in the params dictionary, filling it in with a proper default if
    necessary.
    """
    (type, subtype, params) = parse_mime_type(range)
    if (
        "q" not in params
        or not params["q"]
        or not float(params["q"])
        or float(params["q"]) > 1
        or float(params["q"]) < 0
    ):
        params["q"] = "1"

    return (type, subtype, params)


def fitness_and_quality_parsed(mime_type, parsed_ranges):
    """Find the best match for a mime-type amongst parsed media-ranges.

    Find the best match for a given mime-type against a list of media_ranges
    that have already been parsed by parse_media_range(). Returns a tuple of
    the fitness value and the value of the 'q' quality parameter of the best
    match, or (-1, 0) if no match was found. Just as for quality_parsed(),
    'parsed_ranges' must be a list of parsed media ranges.
    """
    best_fitness = -1
    best_fit_q = 0
    (target_type, target_subtype, target_params) = parse_media_range(mime_type)
    for (type, subtype, params) in parsed_ranges:
        type_match = type == target_type or type == "*" or target_type == "*"
        subtype_match = (
            subtype == target_subtype or subtype == "*" or target_subtype == "*"
        )
        if type_match and subtype_match:
            param_matches = reduce(
                lambda x, y: x + y,
                [
                    1
                    for (key, value) in target_params.items()
                    if key != "q" and key in params and value == params[key]
                ],
                0,
            )
            fitness = (type == target_type) and 100 or 0
            fitness += (subtype == target_subtype) and 10 or 0
            fitness += param_matches
            if fitness > best_fitness:
                best_fitness = fitness
                best_fit_q = params["q"]

    return best_fitness, float(best_fit_q)


def quality_parsed(mime_type, parsed_ranges):
    """Find the best match for a mime-type amongst parsed media-ranges.

    Find the best match for a given mime-type against a list of media_ranges
    that have already been parsed by parse_media_range(). Returns the 'q'
    quality parameter of the best match, 0 if no match was found. This function
    bahaves the same as quality() except that 'parsed_ranges' must be a list of
    parsed media ranges.
    """

    return fitness_and_quality_parsed(mime_type, parsed_ranges)[1]


def quality(mime_type, ranges):
    """Return the quality ('q') of a mime-type against a list of media-ranges.

    Returns the quality 'q' of a mime-type when compared against the
    media-ranges in ranges. For example:

    >>> quality('text/html','text/*;q=0.3, text/html;q=0.7,
                  text/html;level=1, text/html;level=2;q=0.4, */*;q=0.5')
    0.7

    """
    parsed_ranges = [parse_media_range(r) for r in ranges.split(",")]

    return quality_parsed(mime_type, parsed_ranges)


def best_match(supported, header):
    """Return mime-type with the highest quality ('q') from list of candidates.

    Takes a list of supported mime-types and finds the best match for all the
    media-ranges listed in header. The value of header must be a string that
    conforms to the format of the HTTP Accept: header. The value of 'supported'
    is a list of mime-types. The list of supported mime-types should be sorted
    in order of increasing desirability, in case of a situation where there is
    a tie.

    >>> best_match(['application/xbel+xml', 'text/xml'],
                   'text/*;q=0.5,*/*; q=0.1')
    'text/xml'
    """
    split_header = _filter_blank(header.split(","))
    parsed_header = [parse_media_range(r) for r in split_header]
    weighted_matches = []
    pos = 0
    for mime_type in supported:
        weighted_matches.append(
            (fitness_and_quality_parsed(mime_type, parsed_header), pos, mime_type)
        )
        pos += 1
    weighted_matches.sort()

    return weighted_matches[-1][0][1] and weighted_matches[-1][2] or ""


def _filter_blank(i):
    for s in i:
        if s.strip():
            yield s

# === NexusCore/openenv\Lib\site-packages\grpc\_common.py ===
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
"""Shared implementation."""

import logging
import time
from typing import Any, AnyStr, Callable, Optional, Union

import grpc
from grpc._cython import cygrpc
from grpc._typing import DeserializingFunction
from grpc._typing import SerializingFunction

_LOGGER = logging.getLogger(__name__)

CYGRPC_CONNECTIVITY_STATE_TO_CHANNEL_CONNECTIVITY = {
    cygrpc.ConnectivityState.idle: grpc.ChannelConnectivity.IDLE,
    cygrpc.ConnectivityState.connecting: grpc.ChannelConnectivity.CONNECTING,
    cygrpc.ConnectivityState.ready: grpc.ChannelConnectivity.READY,
    cygrpc.ConnectivityState.transient_failure: grpc.ChannelConnectivity.TRANSIENT_FAILURE,
    cygrpc.ConnectivityState.shutdown: grpc.ChannelConnectivity.SHUTDOWN,
}

CYGRPC_STATUS_CODE_TO_STATUS_CODE = {
    cygrpc.StatusCode.ok: grpc.StatusCode.OK,
    cygrpc.StatusCode.cancelled: grpc.StatusCode.CANCELLED,
    cygrpc.StatusCode.unknown: grpc.StatusCode.UNKNOWN,
    cygrpc.StatusCode.invalid_argument: grpc.StatusCode.INVALID_ARGUMENT,
    cygrpc.StatusCode.deadline_exceeded: grpc.StatusCode.DEADLINE_EXCEEDED,
    cygrpc.StatusCode.not_found: grpc.StatusCode.NOT_FOUND,
    cygrpc.StatusCode.already_exists: grpc.StatusCode.ALREADY_EXISTS,
    cygrpc.StatusCode.permission_denied: grpc.StatusCode.PERMISSION_DENIED,
    cygrpc.StatusCode.unauthenticated: grpc.StatusCode.UNAUTHENTICATED,
    cygrpc.StatusCode.resource_exhausted: grpc.StatusCode.RESOURCE_EXHAUSTED,
    cygrpc.StatusCode.failed_precondition: grpc.StatusCode.FAILED_PRECONDITION,
    cygrpc.StatusCode.aborted: grpc.StatusCode.ABORTED,
    cygrpc.StatusCode.out_of_range: grpc.StatusCode.OUT_OF_RANGE,
    cygrpc.StatusCode.unimplemented: grpc.StatusCode.UNIMPLEMENTED,
    cygrpc.StatusCode.internal: grpc.StatusCode.INTERNAL,
    cygrpc.StatusCode.unavailable: grpc.StatusCode.UNAVAILABLE,
    cygrpc.StatusCode.data_loss: grpc.StatusCode.DATA_LOSS,
}
STATUS_CODE_TO_CYGRPC_STATUS_CODE = {
    grpc_code: cygrpc_code
    for cygrpc_code, grpc_code in CYGRPC_STATUS_CODE_TO_STATUS_CODE.items()
}

MAXIMUM_WAIT_TIMEOUT = 0.1

_ERROR_MESSAGE_PORT_BINDING_FAILED = (
    "Failed to bind to address %s; set "
    "GRPC_VERBOSITY=debug environment variable to see detailed error message."
)


def encode(s: AnyStr) -> bytes:
    if isinstance(s, bytes):
        return s
    else:
        return s.encode("utf8")


def decode(b: AnyStr) -> str:
    if isinstance(b, bytes):
        return b.decode("utf-8", "replace")
    return b


def _transform(
    message: Any,
    transformer: Union[SerializingFunction, DeserializingFunction, None],
    exception_message: str,
) -> Any:
    if transformer is None:
        return message
    else:
        try:
            return transformer(message)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception(exception_message)
            return None


def serialize(message: Any, serializer: Optional[SerializingFunction]) -> bytes:
    return _transform(message, serializer, "Exception serializing message!")


def deserialize(
    serialized_message: bytes, deserializer: Optional[DeserializingFunction]
) -> Any:
    return _transform(
        serialized_message, deserializer, "Exception deserializing message!"
    )


def fully_qualified_method(group: str, method: str) -> str:
    return "/{}/{}".format(group, method)


def _wait_once(
    wait_fn: Callable[..., bool],
    timeout: float,
    spin_cb: Optional[Callable[[], None]],
):
    wait_fn(timeout=timeout)
    if spin_cb is not None:
        spin_cb()


def wait(
    wait_fn: Callable[..., bool],
    wait_complete_fn: Callable[[], bool],
    timeout: Optional[float] = None,
    spin_cb: Optional[Callable[[], None]] = None,
) -> bool:
    """Blocks waiting for an event without blocking the thread indefinitely.

    See https://github.com/grpc/grpc/issues/19464 for full context. CPython's
    `threading.Event.wait` and `threading.Condition.wait` methods, if invoked
    without a timeout kwarg, may block the calling thread indefinitely. If the
    call is made from the main thread, this means that signal handlers may not
    run for an arbitrarily long period of time.

    This wrapper calls the supplied wait function with an arbitrary short
    timeout to ensure that no signal handler has to wait longer than
    MAXIMUM_WAIT_TIMEOUT before executing.

    Args:
      wait_fn: A callable acceptable a single float-valued kwarg named
        `timeout`. This function is expected to be one of `threading.Event.wait`
        or `threading.Condition.wait`.
      wait_complete_fn: A callable taking no arguments and returning a bool.
        When this function returns true, it indicates that waiting should cease.
      timeout: An optional float-valued number of seconds after which the wait
        should cease.
      spin_cb: An optional Callable taking no arguments and returning nothing.
        This callback will be called on each iteration of the spin. This may be
        used for, e.g. work related to forking.

    Returns:
      True if a timeout was supplied and it was reached. False otherwise.
    """
    if timeout is None:
        while not wait_complete_fn():
            _wait_once(wait_fn, MAXIMUM_WAIT_TIMEOUT, spin_cb)
    else:
        end = time.time() + timeout
        while not wait_complete_fn():
            remaining = min(end - time.time(), MAXIMUM_WAIT_TIMEOUT)
            if remaining < 0:
                return True
            _wait_once(wait_fn, remaining, spin_cb)
    return False


def validate_port_binding_result(address: str, port: int) -> int:
    """Validates if the port binding succeed.

    If the port returned by Core is 0, the binding is failed. However, in that
    case, the Core API doesn't return a detailed failing reason. The best we
    can do is raising an exception to prevent further confusion.

    Args:
        address: The address string to be bound.
        port: An int returned by core
    """
    if port == 0:
        # The Core API doesn't return a failure message. The best we can do
        # is raising an exception to prevent further confusion.
        raise RuntimeError(_ERROR_MESSAGE_PORT_BINDING_FAILED % address)
    else:
        return port

# === NexusCore/openenv\Lib\site-packages\debugpy\adapter\components.py ===
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root
# for license information.

import functools

from debugpy.common import json, log, messaging, util


ACCEPT_CONNECTIONS_TIMEOUT = 60


class ComponentNotAvailable(Exception):
    def __init__(self, type):
        super().__init__(f"{type.__name__} is not available")


class Component(util.Observable):
    """A component managed by a debug adapter: client, launcher, or debug server.

    Every component belongs to a Session, which is used for synchronization and
    shared data.

    Every component has its own message channel, and provides message handlers for
    that channel. All handlers should be decorated with @Component.message_handler,
    which ensures that Session is locked for the duration of the handler. Thus, only
    one handler is running at any given time across all components, unless the lock
    is released explicitly or via Session.wait_for().

    Components report changes to their attributes to Session, allowing one component
    to wait_for() a change caused by another component.
    """

    def __init__(self, session, stream=None, channel=None):
        assert (stream is None) ^ (channel is None)

        try:
            lock_held = session.lock.acquire(blocking=False)
            assert lock_held, "__init__ of a Component subclass must lock its Session"
        finally:
            session.lock.release()

        super().__init__()

        self.session = session

        if channel is None:
            stream.name = str(self)
            channel = messaging.JsonMessageChannel(stream, self)
            channel.start()
        else:
            channel.name = channel.stream.name = str(self)
            channel.handlers = self
        self.channel = channel
        self.is_connected = True

        # Do this last to avoid triggering useless notifications for assignments above.
        self.observers += [lambda *_: self.session.notify_changed()]

    def __str__(self):
        return f"{type(self).__name__}[{self.session.id}]"

    @property
    def client(self):
        return self.session.client

    @property
    def launcher(self):
        return self.session.launcher

    @property
    def server(self):
        return self.session.server

    def wait_for(self, *args, **kwargs):
        return self.session.wait_for(*args, **kwargs)

    @staticmethod
    def message_handler(f):
        """Applied to a message handler to automatically lock and unlock the session
        for its duration, and to validate the session state.

        If the handler raises ComponentNotAvailable or JsonIOError, converts it to
        Message.cant_handle().
        """

        @functools.wraps(f)
        def lock_and_handle(self, message):
            try:
                with self.session:
                    return f(self, message)
            except ComponentNotAvailable as exc:
                raise message.cant_handle("{0}", exc, silent=True)
            except messaging.MessageHandlingError as exc:
                if exc.cause is message:
                    raise
                else:
                    exc.propagate(message)
            except messaging.JsonIOError as exc:
                raise message.cant_handle(
                    "{0} disconnected unexpectedly", exc.stream.name, silent=True
                )

        return lock_and_handle

    def disconnect(self):
        with self.session:
            self.is_connected = False
            self.session.finalize("{0} has disconnected".format(self))


def missing(session, type):
    class Missing(object):
        """A dummy component that raises ComponentNotAvailable whenever some
        attribute is accessed on it.
        """

        __getattr__ = __setattr__ = lambda self, *_: report()
        __bool__ = __nonzero__ = lambda self: False

    def report():
        try:
            raise ComponentNotAvailable(type)
        except Exception as exc:
            log.reraise_exception("{0} in {1}", exc, session)

    return Missing()


class Capabilities(dict):
    """A collection of feature flags for a component. Corresponds to JSON properties
    in the DAP "initialize" request or response, other than those that identify the
    party.
    """

    PROPERTIES = {}
    """JSON property names and default values for the the capabilities represented
    by instances of this class. Keys are names, and values are either default values
    or validators.

    If the value is callable, it must be a JSON validator; see debugpy.common.json for
    details. If the value is not callable, it is as if json.default(value) validator
    was used instead.
    """

    def __init__(self, component, message):
        """Parses an "initialize" request or response and extracts the feature flags.

        For every "X" in self.PROPERTIES, sets self["X"] to the corresponding value
        from message.payload if it's present there, or to the default value otherwise.
        """

        assert message.is_request("initialize") or message.is_response("initialize")

        self.component = component

        payload = message.payload
        for name, validate in self.PROPERTIES.items():
            value = payload.get(name, ())
            if not callable(validate):
                validate = json.default(validate)

            try:
                value = validate(value)
            except Exception as exc:
                raise message.isnt_valid("{0} {1}", json.repr(name), exc)

            assert (
                value != ()
            ), f"{validate} must provide a default value for missing properties."
            self[name] = value

        log.debug("{0}", self)

    def __repr__(self):
        return f"{type(self).__name__}: {json.repr(dict(self))}"

    def require(self, *keys):
        for key in keys:
            if not self[key]:
                raise messaging.MessageHandlingError(
                    f"{self.component} does not have capability {json.repr(key)}",
                )

# === NexusCore/openenv\Lib\site-packages\fontTools\svgLib\path\shapes.py ===
import re


def _prefer_non_zero(*args):
    for arg in args:
        if arg != 0:
            return arg
    return 0.0


def _ntos(n):
    # %f likes to add unnecessary 0's, %g isn't consistent about # decimals
    return ("%.3f" % n).rstrip("0").rstrip(".")


def _strip_xml_ns(tag):
    # ElementTree API doesn't provide a way to ignore XML namespaces in tags
    # so we here strip them ourselves: cf. https://bugs.python.org/issue18304
    return tag.split("}", 1)[1] if "}" in tag else tag


def _transform(raw_value):
    # TODO assumes a 'matrix' transform.
    # No other transform functions are supported at the moment.
    # https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/transform
    # start simple: if you aren't exactly matrix(...) then no love
    match = re.match(r"matrix\((.*)\)", raw_value)
    if not match:
        raise NotImplementedError
    matrix = tuple(float(p) for p in re.split(r"\s+|,", match.group(1)))
    if len(matrix) != 6:
        raise ValueError("wrong # of terms in %s" % raw_value)
    return matrix


class PathBuilder(object):
    def __init__(self):
        self.paths = []
        self.transforms = []

    def _start_path(self, initial_path=""):
        self.paths.append(initial_path)
        self.transforms.append(None)

    def _end_path(self):
        self._add("z")

    def _add(self, path_snippet):
        path = self.paths[-1]
        if path:
            path += " " + path_snippet
        else:
            path = path_snippet
        self.paths[-1] = path

    def _move(self, c, x, y):
        self._add("%s%s,%s" % (c, _ntos(x), _ntos(y)))

    def M(self, x, y):
        self._move("M", x, y)

    def m(self, x, y):
        self._move("m", x, y)

    def _arc(self, c, rx, ry, x, y, large_arc):
        self._add(
            "%s%s,%s 0 %d 1 %s,%s"
            % (c, _ntos(rx), _ntos(ry), large_arc, _ntos(x), _ntos(y))
        )

    def A(self, rx, ry, x, y, large_arc=0):
        self._arc("A", rx, ry, x, y, large_arc)

    def a(self, rx, ry, x, y, large_arc=0):
        self._arc("a", rx, ry, x, y, large_arc)

    def _vhline(self, c, x):
        self._add("%s%s" % (c, _ntos(x)))

    def H(self, x):
        self._vhline("H", x)

    def h(self, x):
        self._vhline("h", x)

    def V(self, y):
        self._vhline("V", y)

    def v(self, y):
        self._vhline("v", y)

    def _line(self, c, x, y):
        self._add("%s%s,%s" % (c, _ntos(x), _ntos(y)))

    def L(self, x, y):
        self._line("L", x, y)

    def l(self, x, y):
        self._line("l", x, y)

    def _parse_line(self, line):
        x1 = float(line.attrib.get("x1", 0))
        y1 = float(line.attrib.get("y1", 0))
        x2 = float(line.attrib.get("x2", 0))
        y2 = float(line.attrib.get("y2", 0))

        self._start_path()
        self.M(x1, y1)
        self.L(x2, y2)

    def _parse_rect(self, rect):
        x = float(rect.attrib.get("x", 0))
        y = float(rect.attrib.get("y", 0))
        w = float(rect.attrib.get("width"))
        h = float(rect.attrib.get("height"))
        rx = float(rect.attrib.get("rx", 0))
        ry = float(rect.attrib.get("ry", 0))

        rx = _prefer_non_zero(rx, ry)
        ry = _prefer_non_zero(ry, rx)
        # TODO there are more rules for adjusting rx, ry

        self._start_path()
        self.M(x + rx, y)
        self.H(x + w - rx)
        if rx > 0:
            self.A(rx, ry, x + w, y + ry)
        self.V(y + h - ry)
        if rx > 0:
            self.A(rx, ry, x + w - rx, y + h)
        self.H(x + rx)
        if rx > 0:
            self.A(rx, ry, x, y + h - ry)
        self.V(y + ry)
        if rx > 0:
            self.A(rx, ry, x + rx, y)
        self._end_path()

    def _parse_path(self, path):
        if "d" in path.attrib:
            self._start_path(initial_path=path.attrib["d"])

    def _parse_polygon(self, poly):
        if "points" in poly.attrib:
            self._start_path("M" + poly.attrib["points"])
            self._end_path()

    def _parse_polyline(self, poly):
        if "points" in poly.attrib:
            self._start_path("M" + poly.attrib["points"])

    def _parse_circle(self, circle):
        cx = float(circle.attrib.get("cx", 0))
        cy = float(circle.attrib.get("cy", 0))
        r = float(circle.attrib.get("r"))

        # arc doesn't seem to like being a complete shape, draw two halves
        self._start_path()
        self.M(cx - r, cy)
        self.A(r, r, cx + r, cy, large_arc=1)
        self.A(r, r, cx - r, cy, large_arc=1)

    def _parse_ellipse(self, ellipse):
        cx = float(ellipse.attrib.get("cx", 0))
        cy = float(ellipse.attrib.get("cy", 0))
        rx = float(ellipse.attrib.get("rx"))
        ry = float(ellipse.attrib.get("ry"))

        # arc doesn't seem to like being a complete shape, draw two halves
        self._start_path()
        self.M(cx - rx, cy)
        self.A(rx, ry, cx + rx, cy, large_arc=1)
        self.A(rx, ry, cx - rx, cy, large_arc=1)

    def add_path_from_element(self, el):
        tag = _strip_xml_ns(el.tag)
        parse_fn = getattr(self, "_parse_%s" % tag.lower(), None)
        if not callable(parse_fn):
            return False
        parse_fn(el)
        if "transform" in el.attrib:
            self.transforms[-1] = _transform(el.attrib["transform"])
        return True

# === NexusCore/openenv\Lib\site-packages\IPython\core\displaypub.py ===
"""An interface for publishing rich data to frontends.

There are two components of the display system:

* Display formatters, which take a Python object and compute the
  representation of the object in various formats (text, HTML, SVG, etc.).
* The display publisher that is used to send the representation data to the
  various frontends.

This module defines the logic display publishing. The display publisher uses
the ``display_data`` message type that is defined in the IPython messaging
spec.
"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

import sys

from traitlets.config.configurable import Configurable
from traitlets import List

# This used to be defined here - it is imported for backwards compatibility
from .display_functions import publish_display_data
from .history import HistoryOutput

import typing as t

# -----------------------------------------------------------------------------
# Main payload class
# -----------------------------------------------------------------------------

_sentinel = object()


class DisplayPublisher(Configurable):
    """A traited class that publishes display data to frontends.

    Instances of this class are created by the main IPython object and should
    be accessed there.
    """

    def __init__(self, shell=None, *args, **kwargs):
        self.shell = shell
        self._is_publishing = False
        super().__init__(*args, **kwargs)

    def _validate_data(self, data, metadata=None):
        """Validate the display data.

        Parameters
        ----------
        data : dict
            The formata data dictionary.
        metadata : dict
            Any metadata for the data.
        """

        if not isinstance(data, dict):
            raise TypeError("data must be a dict, got: %r" % data)
        if metadata is not None:
            if not isinstance(metadata, dict):
                raise TypeError("metadata must be a dict, got: %r" % data)

    # use * to indicate transient, update are keyword-only
    def publish(
        self,
        data,
        metadata=None,
        source=_sentinel,
        *,
        transient=None,
        update=False,
        **kwargs,
    ) -> None:
        """Publish data and metadata to all frontends.

        See the ``display_data`` message in the messaging documentation for
        more details about this message type.

        The following MIME types are currently implemented:

        * text/plain
        * text/html
        * text/markdown
        * text/latex
        * application/json
        * application/javascript
        * image/png
        * image/jpeg
        * image/svg+xml

        Parameters
        ----------
        data : dict
            A dictionary having keys that are valid MIME types (like
            'text/plain' or 'image/svg+xml') and values that are the data for
            that MIME type. The data itself must be a JSON'able data
            structure. Minimally all data should have the 'text/plain' data,
            which can be displayed by all frontends. If more than the plain
            text is given, it is up to the frontend to decide which
            representation to use.
        metadata : dict
            A dictionary for metadata related to the data. This can contain
            arbitrary key, value pairs that frontends can use to interpret
            the data.  Metadata specific to each mime-type can be specified
            in the metadata dict with the same mime-type keys as
            the data itself.
        source : str, deprecated
            Unused.
        transient : dict, keyword-only
            A dictionary for transient data.
            Data in this dictionary should not be persisted as part of saving this output.
            Examples include 'display_id'.
        update : bool, keyword-only, default: False
            If True, only update existing outputs with the same display_id,
            rather than creating a new output.
        """

        if source is not _sentinel:
            import warnings

            warnings.warn(
                "The 'source' parameter is deprecated since IPython 3.0 and will be ignored "
                "(this warning is present since 9.0). `source` parameter will be removed in the future.",
                DeprecationWarning,
                stacklevel=2,
            )

        handlers: t.Dict = {}
        if self.shell is not None:
            handlers = getattr(self.shell, "mime_renderers", {})

        outputs = self.shell.history_manager.outputs

        outputs[self.shell.execution_count].append(
            HistoryOutput(output_type="display_data", bundle=data)
        )

        for mime, handler in handlers.items():
            if mime in data:
                handler(data[mime], metadata.get(mime, None))
                return

        self._is_publishing = True
        if "text/plain" in data:
            print(data["text/plain"])
        self._is_publishing = False

    @property
    def is_publishing(self):
        return self._is_publishing

    def clear_output(self, wait=False):
        """Clear the output of the cell receiving output."""
        print("\033[2K\r", end="")
        sys.stdout.flush()
        print("\033[2K\r", end="")
        sys.stderr.flush()


class CapturingDisplayPublisher(DisplayPublisher):
    """A DisplayPublisher that stores"""

    outputs: List = List()

    def publish(
        self, data, metadata=None, source=None, *, transient=None, update=False
    ):
        self.outputs.append(
            {
                "data": data,
                "metadata": metadata,
                "transient": transient,
                "update": update,
            }
        )

    def clear_output(self, wait=False):
        super(CapturingDisplayPublisher, self).clear_output(wait)

        # empty the list, *do not* reassign a new list
        self.outputs.clear()

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\health_check.py ===
# This file runs a health check for the LLM, used on litellm/proxy

import asyncio
import logging
import random
from typing import List, Optional

import litellm

logger = logging.getLogger(__name__)
from litellm.constants import HEALTH_CHECK_TIMEOUT_SECONDS

ILLEGAL_DISPLAY_PARAMS = [
    "messages",
    "api_key",
    "prompt",
    "input",
    "vertex_credentials",
    "aws_access_key_id",
    "aws_secret_access_key",
]

MINIMAL_DISPLAY_PARAMS = ["model", "mode_error"]


def _get_random_llm_message():
    """
    Get a random message from the LLM.
    """
    messages = ["Hey how's it going?", "What's 1 + 1?"]

    return [{"role": "user", "content": random.choice(messages)}]


def _clean_endpoint_data(endpoint_data: dict, details: Optional[bool] = True):
    """
    Clean the endpoint data for display to users.
    """
    endpoint_data.pop("litellm_logging_obj", None)
    return (
        {k: v for k, v in endpoint_data.items() if k not in ILLEGAL_DISPLAY_PARAMS}
        if details is not False
        else {k: v for k, v in endpoint_data.items() if k in MINIMAL_DISPLAY_PARAMS}
    )


def filter_deployments_by_id(
    model_list: List,
) -> List:
    seen_ids = set()
    filtered_deployments = []

    for deployment in model_list:
        _model_info = deployment.get("model_info") or {}
        _id = _model_info.get("id") or None
        if _id is None:
            continue

        if _id not in seen_ids:
            seen_ids.add(_id)
            filtered_deployments.append(deployment)

    return filtered_deployments


async def run_with_timeout(task, timeout):
    try:
        return await asyncio.wait_for(task, timeout)
    except asyncio.TimeoutError:
        task.cancel()
        # Only cancel child tasks of the current task
        current_task = asyncio.current_task()
        for t in asyncio.all_tasks():
            if t != current_task:
                t.cancel()
        try:
            await asyncio.wait_for(task, 0.1)  # Give 100ms for cleanup
        except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
            pass
        return {"error": "Timeout exceeded"}


async def _perform_health_check(model_list: list, details: Optional[bool] = True):
    """
    Perform a health check for each model in the list.
    """

    tasks = []
    for model in model_list:
        litellm_params = model["litellm_params"]
        model_info = model.get("model_info", {})
        mode = model_info.get("mode", None)
        litellm_params = _update_litellm_params_for_health_check(
            model_info, litellm_params
        )
        timeout = model_info.get("health_check_timeout") or HEALTH_CHECK_TIMEOUT_SECONDS

        task = run_with_timeout(
            litellm.ahealth_check(
                model["litellm_params"],
                mode=mode,
                prompt="test from litellm",
                input=["test from litellm"],
            ),
            timeout,
        )

        tasks.append(task)

    results = await asyncio.gather(*tasks, return_exceptions=True)

    healthy_endpoints = []
    unhealthy_endpoints = []

    for is_healthy, model in zip(results, model_list):
        litellm_params = model["litellm_params"]

        if isinstance(is_healthy, dict) and "error" not in is_healthy:
            healthy_endpoints.append(
                _clean_endpoint_data({**litellm_params, **is_healthy}, details)
            )
        elif isinstance(is_healthy, dict):
            unhealthy_endpoints.append(
                _clean_endpoint_data({**litellm_params, **is_healthy}, details)
            )
        else:
            unhealthy_endpoints.append(_clean_endpoint_data(litellm_params, details))

    return healthy_endpoints, unhealthy_endpoints


def _update_litellm_params_for_health_check(
    model_info: dict, litellm_params: dict
) -> dict:
    """
    Update the litellm params for health check.

    - gets a short `messages` param for health check
    - updates the `model` param with the `health_check_model` if it exists Doc: https://docs.litellm.ai/docs/proxy/health#wildcard-routes
    """
    litellm_params["messages"] = _get_random_llm_message()
    _health_check_model = model_info.get("health_check_model", None)
    if _health_check_model is not None:
        litellm_params["model"] = _health_check_model
    return litellm_params


async def perform_health_check(
    model_list: list,
    model: Optional[str] = None,
    cli_model: Optional[str] = None,
    details: Optional[bool] = True,
):
    """
    Perform a health check on the system.

    Returns:
        (bool): True if the health check passes, False otherwise.
    """
    if not model_list:
        if cli_model:
            model_list = [
                {"model_name": cli_model, "litellm_params": {"model": cli_model}}
            ]
        else:
            return [], []

    if model is not None:
        _new_model_list = [
            x for x in model_list if x["litellm_params"]["model"] == model
        ]
        if _new_model_list == []:
            _new_model_list = [x for x in model_list if x["model_name"] == model]
        model_list = _new_model_list

    model_list = filter_deployments_by_id(
        model_list=model_list
    )  # filter duplicate deployments (e.g. when model alias'es are used)
    healthy_endpoints, unhealthy_endpoints = await _perform_health_check(
        model_list, details
    )

    return healthy_endpoints, unhealthy_endpoints

# === NexusCore/openenv\Lib\site-packages\litellm\realtime_api\main.py ===
"""Abstraction function for OpenAI's realtime API"""

from typing import Any, Optional, cast

import litellm
from litellm import get_llm_provider
from litellm.llms.base_llm.realtime.transformation import BaseRealtimeConfig
from litellm.llms.custom_httpx.llm_http_handler import BaseLLMHTTPHandler
from litellm.secret_managers.main import get_secret_str
from litellm.types.router import GenericLiteLLMParams
from litellm.types.utils import LlmProviders
from litellm.utils import ProviderConfigManager

from ..litellm_core_utils.get_litellm_params import get_litellm_params
from ..litellm_core_utils.litellm_logging import Logging as LiteLLMLogging
from ..llms.azure.realtime.handler import AzureOpenAIRealtime
from ..llms.openai.realtime.handler import OpenAIRealtime
from ..utils import client as wrapper_client

azure_realtime = AzureOpenAIRealtime()
openai_realtime = OpenAIRealtime()
base_llm_http_handler = BaseLLMHTTPHandler()


@wrapper_client
async def _arealtime(
    model: str,
    websocket: Any,  # fastapi websocket
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
    api_version: Optional[str] = None,
    azure_ad_token: Optional[str] = None,
    client: Optional[Any] = None,
    timeout: Optional[float] = None,
    **kwargs,
):
    """
    Private function to handle the realtime API call.

    For PROXY use only.
    """
    headers = cast(Optional[dict], kwargs.get("headers"))
    extra_headers = cast(Optional[dict], kwargs.get("extra_headers"))
    if headers is None:
        headers = {}
    if extra_headers is not None:
        headers.update(extra_headers)
    litellm_logging_obj: LiteLLMLogging = kwargs.get("litellm_logging_obj")  # type: ignore
    user = kwargs.get("user", None)
    litellm_params = GenericLiteLLMParams(**kwargs)

    litellm_params_dict = get_litellm_params(**kwargs)

    model, _custom_llm_provider, dynamic_api_key, dynamic_api_base = get_llm_provider(
        model=model,
        api_base=api_base,
        api_key=api_key,
    )

    litellm_logging_obj.update_environment_variables(
        model=model,
        user=user,
        optional_params={},
        litellm_params=litellm_params_dict,
        custom_llm_provider=_custom_llm_provider,
    )

    provider_config: Optional[BaseRealtimeConfig] = None
    if _custom_llm_provider in LlmProviders._member_map_.values():
        provider_config = ProviderConfigManager.get_provider_realtime_config(
            model=model,
            provider=LlmProviders(_custom_llm_provider),
        )
    if provider_config is not None:
        await base_llm_http_handler.async_realtime(
            model=model,
            websocket=websocket,
            logging_obj=litellm_logging_obj,
            provider_config=provider_config,
            api_base=api_base,
            api_key=api_key,
            client=client,
            timeout=timeout,
            headers=headers,
        )
    elif _custom_llm_provider == "azure":
        api_base = (
            dynamic_api_base
            or litellm_params.api_base
            or litellm.api_base
            or get_secret_str("AZURE_API_BASE")
        )
        # set API KEY
        api_key = (
            dynamic_api_key
            or litellm.api_key
            or litellm.openai_key
            or get_secret_str("AZURE_API_KEY")
        )

        await azure_realtime.async_realtime(
            model=model,
            websocket=websocket,
            api_base=api_base,
            api_key=api_key,
            api_version="2024-10-01-preview",
            azure_ad_token=None,
            client=None,
            timeout=timeout,
            logging_obj=litellm_logging_obj,
        )
    elif _custom_llm_provider == "openai":
        api_base = (
            dynamic_api_base
            or litellm_params.api_base
            or litellm.api_base
            or "https://api.openai.com/"
        )
        # set API KEY
        api_key = (
            dynamic_api_key
            or litellm.api_key
            or litellm.openai_key
            or get_secret_str("OPENAI_API_KEY")
        )

        await openai_realtime.async_realtime(
            model=model,
            websocket=websocket,
            logging_obj=litellm_logging_obj,
            api_base=api_base,
            api_key=api_key,
            client=None,
            timeout=timeout,
        )
    else:
        raise ValueError(f"Unsupported model: {model}")


async def _realtime_health_check(
    model: str,
    custom_llm_provider: str,
    api_key: Optional[str],
    api_base: Optional[str] = None,
    api_version: Optional[str] = None,
):
    """
    Health check for realtime API - tries connection to the realtime API websocket

    Args:
        model: str - model name
        api_base: str - api base
        api_version: Optional[str] - api version
        api_key: str - api key
        custom_llm_provider: str - custom llm provider

    Returns:
        bool - True if connection is successful, False otherwise
    Raises:
        Exception - if the connection is not successful
    """
    import websockets

    url: Optional[str] = None
    if custom_llm_provider == "azure":
        url = azure_realtime._construct_url(
            api_base=api_base or "",
            model=model,
            api_version=api_version or "2024-10-01-preview",
        )
    elif custom_llm_provider == "openai":
        url = openai_realtime._construct_url(
            api_base=api_base or "https://api.openai.com/", model=model
        )
    else:
        raise ValueError(f"Unsupported model: {model}")
    async with websockets.connect(  # type: ignore
        url,
        extra_headers={
            "api-key": api_key,  # type: ignore
        },
    ):
        return True

# === NexusCore/openenv\Lib\site-packages\nltk\classify\rte_classify.py ===
# Natural Language Toolkit: RTE Classifier
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Simple classifier for RTE corpus.

It calculates the overlap in words and named entities between text and
hypothesis, and also whether there are words / named entities in the
hypothesis which fail to occur in the text, since this is an indicator that
the hypothesis is more informative than (i.e not entailed by) the text.

TO DO: better Named Entity classification
TO DO: add lemmatization
"""

from nltk.classify.maxent import MaxentClassifier
from nltk.classify.util import accuracy
from nltk.tokenize import RegexpTokenizer


class RTEFeatureExtractor:
    """
    This builds a bag of words for both the text and the hypothesis after
    throwing away some stopwords, then calculates overlap and difference.
    """

    def __init__(self, rtepair, stop=True, use_lemmatize=False):
        """
        :param rtepair: a ``RTEPair`` from which features should be extracted
        :param stop: if ``True``, stopwords are thrown away.
        :type stop: bool
        """
        self.stop = stop
        self.stopwords = {
            "a",
            "the",
            "it",
            "they",
            "of",
            "in",
            "to",
            "is",
            "have",
            "are",
            "were",
            "and",
            "very",
            ".",
            ",",
        }

        self.negwords = {"no", "not", "never", "failed", "rejected", "denied"}
        # Try to tokenize so that abbreviations, monetary amounts, email
        # addresses, URLs are single tokens.
        tokenizer = RegexpTokenizer(r"[\w.@:/]+|\w+|\$[\d.]+")

        # Get the set of word types for text and hypothesis
        self.text_tokens = tokenizer.tokenize(rtepair.text)
        self.hyp_tokens = tokenizer.tokenize(rtepair.hyp)
        self.text_words = set(self.text_tokens)
        self.hyp_words = set(self.hyp_tokens)

        if use_lemmatize:
            self.text_words = {self._lemmatize(token) for token in self.text_tokens}
            self.hyp_words = {self._lemmatize(token) for token in self.hyp_tokens}

        if self.stop:
            self.text_words = self.text_words - self.stopwords
            self.hyp_words = self.hyp_words - self.stopwords

        self._overlap = self.hyp_words & self.text_words
        self._hyp_extra = self.hyp_words - self.text_words
        self._txt_extra = self.text_words - self.hyp_words

    def overlap(self, toktype, debug=False):
        """
        Compute the overlap between text and hypothesis.

        :param toktype: distinguish Named Entities from ordinary words
        :type toktype: 'ne' or 'word'
        """
        ne_overlap = {token for token in self._overlap if self._ne(token)}
        if toktype == "ne":
            if debug:
                print("ne overlap", ne_overlap)
            return ne_overlap
        elif toktype == "word":
            if debug:
                print("word overlap", self._overlap - ne_overlap)
            return self._overlap - ne_overlap
        else:
            raise ValueError("Type not recognized:'%s'" % toktype)

    def hyp_extra(self, toktype, debug=True):
        """
        Compute the extraneous material in the hypothesis.

        :param toktype: distinguish Named Entities from ordinary words
        :type toktype: 'ne' or 'word'
        """
        ne_extra = {token for token in self._hyp_extra if self._ne(token)}
        if toktype == "ne":
            return ne_extra
        elif toktype == "word":
            return self._hyp_extra - ne_extra
        else:
            raise ValueError("Type not recognized: '%s'" % toktype)

    @staticmethod
    def _ne(token):
        """
        This just assumes that words in all caps or titles are
        named entities.

        :type token: str
        """
        if token.istitle() or token.isupper():
            return True
        return False

    @staticmethod
    def _lemmatize(word):
        """
        Use morphy from WordNet to find the base form of verbs.
        """
        from nltk.corpus import wordnet as wn

        lemma = wn.morphy(word, pos=wn.VERB)
        if lemma is not None:
            return lemma
        return word


def rte_features(rtepair):
    extractor = RTEFeatureExtractor(rtepair)
    features = {}
    features["alwayson"] = True
    features["word_overlap"] = len(extractor.overlap("word"))
    features["word_hyp_extra"] = len(extractor.hyp_extra("word"))
    features["ne_overlap"] = len(extractor.overlap("ne"))
    features["ne_hyp_extra"] = len(extractor.hyp_extra("ne"))
    features["neg_txt"] = len(extractor.negwords & extractor.text_words)
    features["neg_hyp"] = len(extractor.negwords & extractor.hyp_words)
    return features


def rte_featurize(rte_pairs):
    return [(rte_features(pair), pair.value) for pair in rte_pairs]


def rte_classifier(algorithm, sample_N=None):
    from nltk.corpus import rte as rte_corpus

    train_set = rte_corpus.pairs(["rte1_dev.xml", "rte2_dev.xml", "rte3_dev.xml"])
    test_set = rte_corpus.pairs(["rte1_test.xml", "rte2_test.xml", "rte3_test.xml"])

    if sample_N is not None:
        train_set = train_set[:sample_N]
        test_set = test_set[:sample_N]

    featurized_train_set = rte_featurize(train_set)
    featurized_test_set = rte_featurize(test_set)

    # Train the classifier
    print("Training classifier...")
    if algorithm in ["megam"]:  # MEGAM based algorithms.
        clf = MaxentClassifier.train(featurized_train_set, algorithm)
    elif algorithm in ["GIS", "IIS"]:  # Use default GIS/IIS MaxEnt algorithm
        clf = MaxentClassifier.train(featurized_train_set, algorithm)
    else:
        err_msg = str(
            "RTEClassifier only supports these algorithms:\n "
            "'megam', 'GIS', 'IIS'.\n"
        )
        raise Exception(err_msg)
    print("Testing classifier...")
    acc = accuracy(clf, featurized_test_set)
    print("Accuracy: %6.4f" % acc)
    return clf

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\lin.py ===
# Natural Language Toolkit: Lin's Thesaurus
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Dan Blanchard <dblanchard@ets.org>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.txt

import re
from collections import defaultdict
from functools import reduce

from nltk.corpus.reader import CorpusReader


class LinThesaurusCorpusReader(CorpusReader):
    """Wrapper for the LISP-formatted thesauruses distributed by Dekang Lin."""

    # Compiled regular expression for extracting the key from the first line of each
    # thesaurus entry
    _key_re = re.compile(r'\("?([^"]+)"? \(desc [0-9.]+\).+')

    @staticmethod
    def __defaultdict_factory():
        """Factory for creating defaultdict of defaultdict(dict)s"""
        return defaultdict(dict)

    def __init__(self, root, badscore=0.0):
        """
        Initialize the thesaurus.

        :param root: root directory containing thesaurus LISP files
        :type root: C{string}
        :param badscore: the score to give to words which do not appear in each other's sets of synonyms
        :type badscore: C{float}
        """

        super().__init__(root, r"sim[A-Z]\.lsp")
        self._thesaurus = defaultdict(LinThesaurusCorpusReader.__defaultdict_factory)
        self._badscore = badscore
        for path, encoding, fileid in self.abspaths(
            include_encoding=True, include_fileid=True
        ):
            with open(path) as lin_file:
                first = True
                for line in lin_file:
                    line = line.strip()
                    # Start of entry
                    if first:
                        key = LinThesaurusCorpusReader._key_re.sub(r"\1", line)
                        first = False
                    # End of entry
                    elif line == "))":
                        first = True
                    # Lines with pairs of ngrams and scores
                    else:
                        split_line = line.split("\t")
                        if len(split_line) == 2:
                            ngram, score = split_line
                            self._thesaurus[fileid][key][ngram.strip('"')] = float(
                                score
                            )

    def similarity(self, ngram1, ngram2, fileid=None):
        """
        Returns the similarity score for two ngrams.

        :param ngram1: first ngram to compare
        :type ngram1: C{string}
        :param ngram2: second ngram to compare
        :type ngram2: C{string}
        :param fileid: thesaurus fileid to search in. If None, search all fileids.
        :type fileid: C{string}
        :return: If fileid is specified, just the score for the two ngrams; otherwise,
                 list of tuples of fileids and scores.
        """
        # Entries don't contain themselves, so make sure similarity between item and itself is 1.0
        if ngram1 == ngram2:
            if fileid:
                return 1.0
            else:
                return [(fid, 1.0) for fid in self._fileids]
        else:
            if fileid:
                return (
                    self._thesaurus[fileid][ngram1][ngram2]
                    if ngram2 in self._thesaurus[fileid][ngram1]
                    else self._badscore
                )
            else:
                return [
                    (
                        fid,
                        (
                            self._thesaurus[fid][ngram1][ngram2]
                            if ngram2 in self._thesaurus[fid][ngram1]
                            else self._badscore
                        ),
                    )
                    for fid in self._fileids
                ]

    def scored_synonyms(self, ngram, fileid=None):
        """
        Returns a list of scored synonyms (tuples of synonyms and scores) for the current ngram

        :param ngram: ngram to lookup
        :type ngram: C{string}
        :param fileid: thesaurus fileid to search in. If None, search all fileids.
        :type fileid: C{string}
        :return: If fileid is specified, list of tuples of scores and synonyms; otherwise,
                 list of tuples of fileids and lists, where inner lists consist of tuples of
                 scores and synonyms.
        """
        if fileid:
            return self._thesaurus[fileid][ngram].items()
        else:
            return [
                (fileid, self._thesaurus[fileid][ngram].items())
                for fileid in self._fileids
            ]

    def synonyms(self, ngram, fileid=None):
        """
        Returns a list of synonyms for the current ngram.

        :param ngram: ngram to lookup
        :type ngram: C{string}
        :param fileid: thesaurus fileid to search in. If None, search all fileids.
        :type fileid: C{string}
        :return: If fileid is specified, list of synonyms; otherwise, list of tuples of fileids and
                 lists, where inner lists contain synonyms.
        """
        if fileid:
            return self._thesaurus[fileid][ngram].keys()
        else:
            return [
                (fileid, self._thesaurus[fileid][ngram].keys())
                for fileid in self._fileids
            ]

    def __contains__(self, ngram):
        """
        Determines whether or not the given ngram is in the thesaurus.

        :param ngram: ngram to lookup
        :type ngram: C{string}
        :return: whether the given ngram is in the thesaurus.
        """
        return reduce(
            lambda accum, fileid: accum or (ngram in self._thesaurus[fileid]),
            self._fileids,
            False,
        )


######################################################################
# Demo
######################################################################


def demo():
    from nltk.corpus import lin_thesaurus as thes

    word1 = "business"
    word2 = "enterprise"
    print("Getting synonyms for " + word1)
    print(thes.synonyms(word1))

    print("Getting scored synonyms for " + word1)
    print(thes.scored_synonyms(word1))

    print("Getting synonyms from simN.lsp (noun subsection) for " + word1)
    print(thes.synonyms(word1, fileid="simN.lsp"))

    print("Getting synonyms from simN.lsp (noun subsection) for " + word1)
    print(thes.synonyms(word1, fileid="simN.lsp"))

    print(f"Similarity score for {word1} and {word2}:")
    print(thes.similarity(word1, word2))


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\numpy\_core\overrides.py ===
"""Implementation of __array_function__ overrides from NEP-18."""
import collections
import functools

from numpy._core._multiarray_umath import (
    _ArrayFunctionDispatcher,
    _get_implementing_args,
    add_docstring,
)
from numpy._utils import set_module  # noqa: F401
from numpy._utils._inspect import getargspec

ARRAY_FUNCTIONS = set()

array_function_like_doc = (
    """like : array_like, optional
        Reference object to allow the creation of arrays which are not
        NumPy arrays. If an array-like passed in as ``like`` supports
        the ``__array_function__`` protocol, the result will be defined
        by it. In this case, it ensures the creation of an array object
        compatible with that passed in via this argument."""
)

def get_array_function_like_doc(public_api, docstring_template=""):
    ARRAY_FUNCTIONS.add(public_api)
    docstring = public_api.__doc__ or docstring_template
    return docstring.replace("${ARRAY_FUNCTION_LIKE}", array_function_like_doc)

def finalize_array_function_like(public_api):
    public_api.__doc__ = get_array_function_like_doc(public_api)
    return public_api


add_docstring(
    _ArrayFunctionDispatcher,
    """
    Class to wrap functions with checks for __array_function__ overrides.

    All arguments are required, and can only be passed by position.

    Parameters
    ----------
    dispatcher : function or None
        The dispatcher function that returns a single sequence-like object
        of all arguments relevant.  It must have the same signature (except
        the default values) as the actual implementation.
        If ``None``, this is a ``like=`` dispatcher and the
        ``_ArrayFunctionDispatcher`` must be called with ``like`` as the
        first (additional and positional) argument.
    implementation : function
        Function that implements the operation on NumPy arrays without
        overrides.  Arguments passed calling the ``_ArrayFunctionDispatcher``
        will be forwarded to this (and the ``dispatcher``) as if using
        ``*args, **kwargs``.

    Attributes
    ----------
    _implementation : function
        The original implementation passed in.
    """)


# exposed for testing purposes; used internally by _ArrayFunctionDispatcher
add_docstring(
    _get_implementing_args,
    """
    Collect arguments on which to call __array_function__.

    Parameters
    ----------
    relevant_args : iterable of array-like
        Iterable of possibly array-like arguments to check for
        __array_function__ methods.

    Returns
    -------
    Sequence of arguments with __array_function__ methods, in the order in
    which they should be called.
    """)


ArgSpec = collections.namedtuple('ArgSpec', 'args varargs keywords defaults')


def verify_matching_signatures(implementation, dispatcher):
    """Verify that a dispatcher function has the right signature."""
    implementation_spec = ArgSpec(*getargspec(implementation))
    dispatcher_spec = ArgSpec(*getargspec(dispatcher))

    if (implementation_spec.args != dispatcher_spec.args or
            implementation_spec.varargs != dispatcher_spec.varargs or
            implementation_spec.keywords != dispatcher_spec.keywords or
            (bool(implementation_spec.defaults) !=
             bool(dispatcher_spec.defaults)) or
            (implementation_spec.defaults is not None and
             len(implementation_spec.defaults) !=
             len(dispatcher_spec.defaults))):
        raise RuntimeError('implementation and dispatcher for %s have '
                           'different function signatures' % implementation)

    if implementation_spec.defaults is not None:
        if dispatcher_spec.defaults != (None,) * len(dispatcher_spec.defaults):
            raise RuntimeError('dispatcher functions can only use None for '
                               'default argument values')


def array_function_dispatch(dispatcher=None, module=None, verify=True,
                            docs_from_dispatcher=False):
    """Decorator for adding dispatch with the __array_function__ protocol.

    See NEP-18 for example usage.

    Parameters
    ----------
    dispatcher : callable or None
        Function that when called like ``dispatcher(*args, **kwargs)`` with
        arguments from the NumPy function call returns an iterable of
        array-like arguments to check for ``__array_function__``.

        If `None`, the first argument is used as the single `like=` argument
        and not passed on.  A function implementing `like=` must call its
        dispatcher with `like` as the first non-keyword argument.
    module : str, optional
        __module__ attribute to set on new function, e.g., ``module='numpy'``.
        By default, module is copied from the decorated function.
    verify : bool, optional
        If True, verify the that the signature of the dispatcher and decorated
        function signatures match exactly: all required and optional arguments
        should appear in order with the same names, but the default values for
        all optional arguments should be ``None``. Only disable verification
        if the dispatcher's signature needs to deviate for some particular
        reason, e.g., because the function has a signature like
        ``func(*args, **kwargs)``.
    docs_from_dispatcher : bool, optional
        If True, copy docs from the dispatcher function onto the dispatched
        function, rather than from the implementation. This is useful for
        functions defined in C, which otherwise don't have docstrings.

    Returns
    -------
    Function suitable for decorating the implementation of a NumPy function.

    """
    def decorator(implementation):
        if verify:
            if dispatcher is not None:
                verify_matching_signatures(implementation, dispatcher)
            else:
                # Using __code__ directly similar to verify_matching_signature
                co = implementation.__code__
                last_arg = co.co_argcount + co.co_kwonlyargcount - 1
                last_arg = co.co_varnames[last_arg]
                if last_arg != "like" or co.co_kwonlyargcount == 0:
                    raise RuntimeError(
                        "__array_function__ expects `like=` to be the last "
                        "argument and a keyword-only argument. "
                        f"{implementation} does not seem to comply.")

        if docs_from_dispatcher:
            add_docstring(implementation, dispatcher.__doc__)

        public_api = _ArrayFunctionDispatcher(dispatcher, implementation)
        public_api = functools.wraps(implementation)(public_api)

        if module is not None:
            public_api.__module__ = module

        ARRAY_FUNCTIONS.add(public_api)

        return public_api

    return decorator


def array_function_from_dispatcher(
        implementation, module=None, verify=True, docs_from_dispatcher=True):
    """Like array_function_dispatcher, but with function arguments flipped."""

    def decorator(dispatcher):
        return array_function_dispatch(
            dispatcher, module, verify=verify,
            docs_from_dispatcher=docs_from_dispatcher)(implementation)
    return decorator

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\slash.py ===
"""
    pygments.lexers.slash
    ~~~~~~~~~~~~~~~~~~~~~

    Lexer for the Slash programming language.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import ExtendedRegexLexer, bygroups, DelegatingLexer
from pygments.token import Name, Number, String, Comment, Punctuation, \
    Other, Keyword, Operator, Whitespace

__all__ = ['SlashLexer']


class SlashLanguageLexer(ExtendedRegexLexer):
    _nkw = r'(?=[^a-zA-Z_0-9])'

    def move_state(new_state):
        return ("#pop", new_state)

    def right_angle_bracket(lexer, match, ctx):
        if len(ctx.stack) > 1 and ctx.stack[-2] == "string":
            ctx.stack.pop()
        yield match.start(), String.Interpol, '}'
        ctx.pos = match.end()
        pass

    tokens = {
        "root": [
            (r"<%=",        Comment.Preproc,    move_state("slash")),
            (r"<%!!",       Comment.Preproc,    move_state("slash")),
            (r"<%#.*?%>",   Comment.Multiline),
            (r"<%",         Comment.Preproc,    move_state("slash")),
            (r".|\n",       Other),
        ],
        "string": [
            (r"\\",         String.Escape,      move_state("string_e")),
            (r"\"",         String,             move_state("slash")),
            (r"#\{",        String.Interpol,    "slash"),
            (r'.|\n',       String),
        ],
        "string_e": [
            (r'n',                  String.Escape,      move_state("string")),
            (r't',                  String.Escape,      move_state("string")),
            (r'r',                  String.Escape,      move_state("string")),
            (r'e',                  String.Escape,      move_state("string")),
            (r'x[a-fA-F0-9]{2}',    String.Escape,      move_state("string")),
            (r'.',                  String.Escape,      move_state("string")),
        ],
        "regexp": [
            (r'}[a-z]*',            String.Regex,       move_state("slash")),
            (r'\\(.|\n)',           String.Regex),
            (r'{',                  String.Regex,       "regexp_r"),
            (r'.|\n',               String.Regex),
        ],
        "regexp_r": [
            (r'}[a-z]*',            String.Regex,       "#pop"),
            (r'\\(.|\n)',           String.Regex),
            (r'{',                  String.Regex,       "regexp_r"),
        ],
        "slash": [
            (r"%>",                     Comment.Preproc,    move_state("root")),
            (r"\"",                     String,             move_state("string")),
            (r"'[a-zA-Z0-9_]+",         String),
            (r'%r{',                    String.Regex,       move_state("regexp")),
            (r'/\*.*?\*/',              Comment.Multiline),
            (r"(#|//).*?\n",            Comment.Single),
            (r'-?[0-9]+e[+-]?[0-9]+',   Number.Float),
            (r'-?[0-9]+\.[0-9]+(e[+-]?[0-9]+)?', Number.Float),
            (r'-?[0-9]+',               Number.Integer),
            (r'nil'+_nkw,               Name.Builtin),
            (r'true'+_nkw,              Name.Builtin),
            (r'false'+_nkw,             Name.Builtin),
            (r'self'+_nkw,              Name.Builtin),
            (r'(class)(\s+)([A-Z][a-zA-Z0-9_\']*)',
                bygroups(Keyword, Whitespace, Name.Class)),
            (r'class'+_nkw,             Keyword),
            (r'extends'+_nkw,           Keyword),
            (r'(def)(\s+)(self)(\s*)(\.)(\s*)([a-z_][a-zA-Z0-9_\']*=?|<<|>>|==|<=>|<=|<|>=|>|\+|-(self)?|~(self)?|\*|/|%|^|&&|&|\||\[\]=?)',
                bygroups(Keyword, Whitespace, Name.Builtin, Whitespace, Punctuation, Whitespace, Name.Function)),
            (r'(def)(\s+)([a-z_][a-zA-Z0-9_\']*=?|<<|>>|==|<=>|<=|<|>=|>|\+|-(self)?|~(self)?|\*|/|%|^|&&|&|\||\[\]=?)',
                bygroups(Keyword, Whitespace, Name.Function)),
            (r'def'+_nkw,               Keyword),
            (r'if'+_nkw,                Keyword),
            (r'elsif'+_nkw,             Keyword),
            (r'else'+_nkw,              Keyword),
            (r'unless'+_nkw,            Keyword),
            (r'for'+_nkw,               Keyword),
            (r'in'+_nkw,                Keyword),
            (r'while'+_nkw,             Keyword),
            (r'until'+_nkw,             Keyword),
            (r'and'+_nkw,               Keyword),
            (r'or'+_nkw,                Keyword),
            (r'not'+_nkw,               Keyword),
            (r'lambda'+_nkw,            Keyword),
            (r'try'+_nkw,               Keyword),
            (r'catch'+_nkw,             Keyword),
            (r'return'+_nkw,            Keyword),
            (r'next'+_nkw,              Keyword),
            (r'last'+_nkw,              Keyword),
            (r'throw'+_nkw,             Keyword),
            (r'use'+_nkw,               Keyword),
            (r'switch'+_nkw,            Keyword),
            (r'\\',                     Keyword),
            (r'λ',                      Keyword),
            (r'__FILE__'+_nkw,          Name.Builtin.Pseudo),
            (r'__LINE__'+_nkw,          Name.Builtin.Pseudo),
            (r'[A-Z][a-zA-Z0-9_\']*'+_nkw, Name.Constant),
            (r'[a-z_][a-zA-Z0-9_\']*'+_nkw, Name),
            (r'@[a-z_][a-zA-Z0-9_\']*'+_nkw, Name.Variable.Instance),
            (r'@@[a-z_][a-zA-Z0-9_\']*'+_nkw, Name.Variable.Class),
            (r'\(',                     Punctuation),
            (r'\)',                     Punctuation),
            (r'\[',                     Punctuation),
            (r'\]',                     Punctuation),
            (r'\{',                     Punctuation),
            (r'\}',                     right_angle_bracket),
            (r';',                      Punctuation),
            (r',',                      Punctuation),
            (r'<<=',                    Operator),
            (r'>>=',                    Operator),
            (r'<<',                     Operator),
            (r'>>',                     Operator),
            (r'==',                     Operator),
            (r'!=',                     Operator),
            (r'=>',                     Operator),
            (r'=',                      Operator),
            (r'<=>',                    Operator),
            (r'<=',                     Operator),
            (r'>=',                     Operator),
            (r'<',                      Operator),
            (r'>',                      Operator),
            (r'\+\+',                   Operator),
            (r'\+=',                    Operator),
            (r'-=',                     Operator),
            (r'\*\*=',                  Operator),
            (r'\*=',                    Operator),
            (r'\*\*',                   Operator),
            (r'\*',                     Operator),
            (r'/=',                     Operator),
            (r'\+',                     Operator),
            (r'-',                      Operator),
            (r'/',                      Operator),
            (r'%=',                     Operator),
            (r'%',                      Operator),
            (r'^=',                     Operator),
            (r'&&=',                    Operator),
            (r'&=',                     Operator),
            (r'&&',                     Operator),
            (r'&',                      Operator),
            (r'\|\|=',                  Operator),
            (r'\|=',                    Operator),
            (r'\|\|',                   Operator),
            (r'\|',                     Operator),
            (r'!',                      Operator),
            (r'\.\.\.',                 Operator),
            (r'\.\.',                   Operator),
            (r'\.',                     Operator),
            (r'::',                     Operator),
            (r':',                      Operator),
            (r'(\s|\n)+',               Whitespace),
            (r'[a-z_][a-zA-Z0-9_\']*',  Name.Variable),
        ],
    }


class SlashLexer(DelegatingLexer):
    """
    Lexer for the Slash programming language.
    """

    name = 'Slash'
    aliases = ['slash']
    filenames = ['*.sla']
    url = 'https://github.com/arturadib/Slash-A'
    version_added = '2.4'

    def __init__(self, **options):
        from pygments.lexers.web import HtmlLexer
        super().__init__(HtmlLexer, SlashLanguageLexer, **options)

# === NexusCore/openenv\Lib\site-packages\send2trash\win\legacy.py ===
# Copyright 2017 Virgil Dupras

# This software is licensed under the "BSD" License as described in the "LICENSE" file,
# which should be included with this package. The terms are also available at
# http://www.hardcoded.net/licenses/bsd_license

from __future__ import unicode_literals
import os.path as op

from send2trash.compat import text_type
from send2trash.util import preprocess_paths

from ctypes import (
    windll,
    Structure,
    byref,
    c_uint,
    create_unicode_buffer,
    addressof,
    GetLastError,
    FormatError,
)
from ctypes.wintypes import HWND, UINT, LPCWSTR, BOOL

kernel32 = windll.kernel32
GetShortPathNameW = kernel32.GetShortPathNameW

shell32 = windll.shell32
SHFileOperationW = shell32.SHFileOperationW


class SHFILEOPSTRUCTW(Structure):
    _fields_ = [
        ("hwnd", HWND),
        ("wFunc", UINT),
        ("pFrom", LPCWSTR),
        ("pTo", LPCWSTR),
        ("fFlags", c_uint),
        ("fAnyOperationsAborted", BOOL),
        ("hNameMappings", c_uint),
        ("lpszProgressTitle", LPCWSTR),
    ]


FO_MOVE = 1
FO_COPY = 2
FO_DELETE = 3
FO_RENAME = 4

FOF_MULTIDESTFILES = 1
FOF_SILENT = 4
FOF_NOCONFIRMATION = 16
FOF_ALLOWUNDO = 64
FOF_NOERRORUI = 1024


def convert_sh_file_opt_result(result):
    # map overlapping values from SHFileOpterationW to approximate standard windows errors
    # ref https://docs.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-shfileoperationw#return-value
    # ref https://docs.microsoft.com/en-us/windows/win32/debug/system-error-codes--0-499-
    results = {
        0x71: 0x50,  # DE_SAMEFILE -> ERROR_FILE_EXISTS
        0x72: 0x57,  # DE_MANYSRC1DEST -> ERROR_INVALID_PARAMETER
        0x73: 0x57,  # DE_DIFFDIR -> ERROR_INVALID_PARAMETER
        0x74: 0x57,  # DE_ROOTDIR -> ERROR_INVALID_PARAMETER
        0x75: 0x4C7,  # DE_OPCANCELLED -> ERROR_CANCELLED
        0x76: 0x57,  # DE_DESTSUBTREE -> ERROR_INVALID_PARAMETER
        0x78: 0x05,  # DE_ACCESSDENIEDSRC -> ERROR_ACCESS_DENIED
        0x79: 0x6F,  # DE_PATHTOODEEP -> ERROR_BUFFER_OVERFLOW
        0x7A: 0x57,  # DE_MANYDEST -> ERROR_INVALID_PARAMETER
        0x7C: 0xA1,  # DE_INVALIDFILES -> ERROR_BAD_PATHNAME
        0x7D: 0x57,  # DE_DESTSAMETREE -> ERROR_INVALID_PARAMETER
        0x7E: 0xB7,  # DE_FLDDESTISFILE -> ERROR_ALREADY_EXISTS
        0x80: 0xB7,  # DE_FILEDESTISFLD -> ERROR_ALREADY_EXISTS
        0x81: 0x6F,  # DE_FILENAMETOOLONG -> ERROR_BUFFER_OVERFLOW
        0x82: 0x13,  # DE_DEST_IS_CDROM -> ERROR_WRITE_PROTECT
        0x83: 0x13,  # DE_DEST_IS_DVD -> ERROR_WRITE_PROTECT
        0x84: 0x6F9,  # DE_DEST_IS_CDRECORD -> ERROR_UNRECOGNIZED_MEDIA
        0x85: 0xDF,  # DE_FILE_TOO_LARGE -> ERROR_FILE_TOO_LARGE
        0x86: 0x13,  # DE_SRC_IS_CDROM -> ERROR_WRITE_PROTECT
        0x87: 0x13,  # DE_SRC_IS_DVD -> ERROR_WRITE_PROTECT
        0x88: 0x6F9,  # DE_SRC_IS_CDRECORD -> ERROR_UNRECOGNIZED_MEDIA
        0xB7: 0x6F,  # DE_ERROR_MAX -> ERROR_BUFFER_OVERFLOW
        0x402: 0xA1,  # UNKNOWN -> ERROR_BAD_PATHNAME
        0x10000: 0x1D,  # ERRORONDEST -> ERROR_WRITE_FAULT
        0x10074: 0x57,  # DE_ROOTDIR | ERRORONDEST -> ERROR_INVALID_PARAMETER
    }

    return results.get(result, result)


def prefix_and_path(path):
    r"""Guess the long-path prefix based on the kind of *path*.
    Local paths (C:\folder\file.ext) and UNC names (\\server\folder\file.ext)
    are handled.

    Return a tuple of the long-path prefix and the prefixed path.
    """
    prefix, long_path = "\\\\?\\", path

    if not path.startswith(prefix):
        if path.startswith("\\\\"):
            # Likely a UNC name
            prefix = "\\\\?\\UNC"
            long_path = prefix + path[1:]
        else:
            # Likely a local path
            long_path = prefix + path
    elif path.startswith(prefix + "UNC\\"):
        # UNC name with long-path prefix
        prefix = "\\\\?\\UNC"

    return prefix, long_path


def get_awaited_path_from_prefix(prefix, path):
    """Guess the correct path to pass to the SHFileOperationW() call.
    The long-path prefix must be removed, so we should take care of
    different long-path prefixes.
    """
    if prefix == "\\\\?\\UNC":
        # We need to prepend a backslash for UNC names, as it was removed
        # in prefix_and_path().
        return "\\" + path[len(prefix) :]
    return path[len(prefix) :]


def get_short_path_name(long_name):
    prefix, long_path = prefix_and_path(long_name)
    buf_size = GetShortPathNameW(long_path, None, 0)
    # FIX: https://github.com/hsoft/send2trash/issues/31
    # If buffer size is zero, an error has occurred.
    if not buf_size:
        err_no = GetLastError()
        raise WindowsError(err_no, FormatError(err_no), long_path)
    output = create_unicode_buffer(buf_size)
    GetShortPathNameW(long_path, output, buf_size)
    return get_awaited_path_from_prefix(prefix, output.value)


def send2trash(paths):
    paths = preprocess_paths(paths)
    if not paths:
        return
    # convert data type
    paths = [text_type(path, "mbcs") if not isinstance(path, text_type) else path for path in paths]
    # convert to full paths
    paths = [op.abspath(path) if not op.isabs(path) else path for path in paths]
    # get short path to handle path length issues
    paths = [get_short_path_name(path) for path in paths]
    fileop = SHFILEOPSTRUCTW()
    fileop.hwnd = 0
    fileop.wFunc = FO_DELETE
    # FIX: https://github.com/hsoft/send2trash/issues/17
    # Starting in python 3.6.3 it is no longer possible to use:
    # LPCWSTR(path + '\0') directly as embedded null characters are no longer
    # allowed in strings
    # Workaround
    #  - create buffer of c_wchar[] (LPCWSTR is based on this type)
    #  - buffer is two c_wchar characters longer (double null terminator)
    #  - cast the address of the buffer to a LPCWSTR
    # NOTE: based on how python allocates memory for these types they should
    # always be zero, if this is ever not true we can go back to explicitly
    # setting the last two characters to null using buffer[index] = '\0'.
    # Additional note on another issue here, unicode_buffer expects length in
    # bytes essentially, so having multi-byte characters causes issues if just
    # passing pythons string length.  Instead of dealing with this difference we
    # just create a buffer then a new one with an extra null.  Since the non-length
    # specified version apparently stops after the first null, join with a space first.
    buffer = create_unicode_buffer(" ".join(paths))
    # convert to a single string of null terminated paths
    path_string = "\0".join(paths)
    buffer = create_unicode_buffer(path_string, len(buffer) + 1)
    fileop.pFrom = LPCWSTR(addressof(buffer))
    fileop.pTo = None
    fileop.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_NOERRORUI | FOF_SILENT
    fileop.fAnyOperationsAborted = 0
    fileop.hNameMappings = 0
    fileop.lpszProgressTitle = None
    result = SHFileOperationW(byref(fileop))
    if result:
        error = convert_sh_file_opt_result(result)
        raise WindowsError(None, FormatError(error), paths, error)

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\wheel\metadata.py ===
"""
Tools for converting old- to new-style metadata.
"""

from __future__ import annotations

import functools
import itertools
import os.path
import re
import textwrap
from email.message import Message
from email.parser import Parser
from typing import Generator, Iterable, Iterator, Literal

from .vendored.packaging.requirements import Requirement


def _nonblank(str: str) -> bool | Literal[""]:
    return str and not str.startswith("#")


@functools.singledispatch
def yield_lines(iterable: Iterable[str]) -> Iterator[str]:
    r"""
    Yield valid lines of a string or iterable.
    >>> list(yield_lines(''))
    []
    >>> list(yield_lines(['foo', 'bar']))
    ['foo', 'bar']
    >>> list(yield_lines('foo\nbar'))
    ['foo', 'bar']
    >>> list(yield_lines('\nfoo\n#bar\nbaz #comment'))
    ['foo', 'baz #comment']
    >>> list(yield_lines(['foo\nbar', 'baz', 'bing\n\n\n']))
    ['foo', 'bar', 'baz', 'bing']
    """
    return itertools.chain.from_iterable(map(yield_lines, iterable))


@yield_lines.register(str)
def _(text: str) -> Iterator[str]:
    return filter(_nonblank, map(str.strip, text.splitlines()))


def split_sections(
    s: str | Iterator[str],
) -> Generator[tuple[str | None, list[str]], None, None]:
    """Split a string or iterable thereof into (section, content) pairs
    Each ``section`` is a stripped version of the section header ("[section]")
    and each ``content`` is a list of stripped lines excluding blank lines and
    comment-only lines.  If there are any such lines before the first section
    header, they're returned in a first ``section`` of ``None``.
    """
    section = None
    content: list[str] = []
    for line in yield_lines(s):
        if line.startswith("["):
            if line.endswith("]"):
                if section or content:
                    yield section, content
                section = line[1:-1].strip()
                content = []
            else:
                raise ValueError("Invalid section heading", line)
        else:
            content.append(line)

    # wrap up last segment
    yield section, content


def safe_extra(extra: str) -> str:
    """Convert an arbitrary string to a standard 'extra' name
    Any runs of non-alphanumeric characters are replaced with a single '_',
    and the result is always lowercased.
    """
    return re.sub("[^A-Za-z0-9.-]+", "_", extra).lower()


def safe_name(name: str) -> str:
    """Convert an arbitrary string to a standard distribution name
    Any runs of non-alphanumeric/. characters are replaced with a single '-'.
    """
    return re.sub("[^A-Za-z0-9.]+", "-", name)


def requires_to_requires_dist(requirement: Requirement) -> str:
    """Return the version specifier for a requirement in PEP 345/566 fashion."""
    if requirement.url:
        return " @ " + requirement.url

    requires_dist: list[str] = []
    for spec in requirement.specifier:
        requires_dist.append(spec.operator + spec.version)

    if requires_dist:
        return " " + ",".join(sorted(requires_dist))
    else:
        return ""


def convert_requirements(requirements: list[str]) -> Iterator[str]:
    """Yield Requires-Dist: strings for parsed requirements strings."""
    for req in requirements:
        parsed_requirement = Requirement(req)
        spec = requires_to_requires_dist(parsed_requirement)
        extras = ",".join(sorted(safe_extra(e) for e in parsed_requirement.extras))
        if extras:
            extras = f"[{extras}]"

        yield safe_name(parsed_requirement.name) + extras + spec


def generate_requirements(
    extras_require: dict[str | None, list[str]],
) -> Iterator[tuple[str, str]]:
    """
    Convert requirements from a setup()-style dictionary to
    ('Requires-Dist', 'requirement') and ('Provides-Extra', 'extra') tuples.

    extras_require is a dictionary of {extra: [requirements]} as passed to setup(),
    using the empty extra {'': [requirements]} to hold install_requires.
    """
    for extra, depends in extras_require.items():
        condition = ""
        extra = extra or ""
        if ":" in extra:  # setuptools extra:condition syntax
            extra, condition = extra.split(":", 1)

        extra = safe_extra(extra)
        if extra:
            yield "Provides-Extra", extra
            if condition:
                condition = "(" + condition + ") and "
            condition += f"extra == '{extra}'"

        if condition:
            condition = " ; " + condition

        for new_req in convert_requirements(depends):
            canonical_req = str(Requirement(new_req + condition))
            yield "Requires-Dist", canonical_req


def pkginfo_to_metadata(egg_info_path: str, pkginfo_path: str) -> Message:
    """
    Convert .egg-info directory with PKG-INFO to the Metadata 2.1 format
    """
    with open(pkginfo_path, encoding="utf-8") as headers:
        pkg_info = Parser().parse(headers)

    pkg_info.replace_header("Metadata-Version", "2.1")
    # Those will be regenerated from `requires.txt`.
    del pkg_info["Provides-Extra"]
    del pkg_info["Requires-Dist"]
    requires_path = os.path.join(egg_info_path, "requires.txt")
    if os.path.exists(requires_path):
        with open(requires_path, encoding="utf-8") as requires_file:
            requires = requires_file.read()

        parsed_requirements = sorted(split_sections(requires), key=lambda x: x[0] or "")
        for extra, reqs in parsed_requirements:
            for key, value in generate_requirements({extra: reqs}):
                if (key, value) not in pkg_info.items():
                    pkg_info[key] = value

    description = pkg_info["Description"]
    if description:
        description_lines = pkg_info["Description"].splitlines()
        dedented_description = "\n".join(
            # if the first line of long_description is blank,
            # the first line here will be indented.
            (
                description_lines[0].lstrip(),
                textwrap.dedent("\n".join(description_lines[1:])),
                "\n",
            )
        )
        pkg_info.set_payload(dedented_description)
        del pkg_info["Description"]

    return pkg_info

# === NexusCore/openenv\Lib\site-packages\numpy\ma\tests\test_core.py ===
"""Tests suite for MaskedArray & subclassing.

:author: Pierre Gerard-Marchant
:contact: pierregm_at_uga_dot_edu
"""
__author__ = "Pierre GF Gerard-Marchant"

import copy
import itertools
import operator
import pickle
import sys
import textwrap
import warnings
from functools import reduce

import pytest

import numpy as np
import numpy._core.fromnumeric as fromnumeric
import numpy._core.umath as umath
import numpy.ma.core
from numpy import ndarray
from numpy._utils import asbytes
from numpy.exceptions import AxisError
from numpy.ma.core import (
    MAError,
    MaskedArray,
    MaskError,
    MaskType,
    abs,
    absolute,
    add,
    all,
    allclose,
    allequal,
    alltrue,
    angle,
    anom,
    arange,
    arccos,
    arccosh,
    arcsin,
    arctan,
    arctan2,
    argsort,
    array,
    asarray,
    choose,
    concatenate,
    conjugate,
    cos,
    cosh,
    count,
    default_fill_value,
    diag,
    divide,
    empty,
    empty_like,
    equal,
    exp,
    filled,
    fix_invalid,
    flatten_mask,
    flatten_structured_array,
    fromflex,
    getmask,
    getmaskarray,
    greater,
    greater_equal,
    identity,
    inner,
    isMaskedArray,
    less,
    less_equal,
    log,
    log10,
    make_mask,
    make_mask_descr,
    mask_or,
    masked,
    masked_array,
    masked_equal,
    masked_greater,
    masked_greater_equal,
    masked_inside,
    masked_less,
    masked_less_equal,
    masked_not_equal,
    masked_outside,
    masked_print_option,
    masked_values,
    masked_where,
    max,
    maximum,
    maximum_fill_value,
    min,
    minimum,
    minimum_fill_value,
    mod,
    multiply,
    mvoid,
    nomask,
    not_equal,
    ones,
    ones_like,
    outer,
    power,
    product,
    put,
    putmask,
    ravel,
    repeat,
    reshape,
    resize,
    shape,
    sin,
    sinh,
    sometrue,
    sort,
    sqrt,
    subtract,
    sum,
    take,
    tan,
    tanh,
    transpose,
    where,
    zeros,
    zeros_like,
)
from numpy.ma.testutils import (
    assert_,
    assert_almost_equal,
    assert_array_equal,
    assert_equal,
    assert_equal_records,
    assert_mask_equal,
    assert_not_equal,
    fail_if_equal,
)
from numpy.testing import (
    IS_WASM,
    assert_raises,
    assert_warns,
    suppress_warnings,
    temppath,
)
from numpy.testing._private.utils import requires_memory

pi = np.pi


suppress_copy_mask_on_assignment = suppress_warnings()
suppress_copy_mask_on_assignment.filter(
    numpy.ma.core.MaskedArrayFutureWarning,
    "setting an item on a masked array which has a shared mask will not copy")


# For parametrized numeric testing
num_dts = [np.dtype(dt_) for dt_ in '?bhilqBHILQefdgFD']
num_ids = [dt_.char for dt_ in num_dts]


class TestMaskedArray:
    # Base test class for MaskedArrays.

    def setup_method(self):
        # Base data definition.
        x = np.array([1., 1., 1., -2., pi / 2.0, 4., 5., -10., 10., 1., 2., 3.])
        y = np.array([5., 0., 3., 2., -1., -4., 0., -10., 10., 1., 0., 3.])
        a10 = 10.
        m1 = [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0]
        m2 = [0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1]
        xm = masked_array(x, mask=m1)
        ym = masked_array(y, mask=m2)
        z = np.array([-.5, 0., .5, .8])
        zm = masked_array(z, mask=[0, 1, 0, 0])
        xf = np.where(m1, 1e+20, x)
        xm.set_fill_value(1e+20)
        self.d = (x, y, a10, m1, m2, xm, ym, z, zm, xf)

    def test_basicattributes(self):
        # Tests some basic array attributes.
        a = array([1, 3, 2])
        b = array([1, 3, 2], mask=[1, 0, 1])
        assert_equal(a.ndim, 1)
        assert_equal(b.ndim, 1)
        assert_equal(a.size, 3)
        assert_equal(b.size, 3)
        assert_equal(a.shape, (3,))
        assert_equal(b.shape, (3,))

    def test_basic0d(self):
        # Checks masking a scalar
        x = masked_array(0)
        assert_equal(str(x), '0')
        x = masked_array(0, mask=True)
        assert_equal(str(x), str(masked_print_option))
        x = masked_array(0, mask=False)
        assert_equal(str(x), '0')
        x = array(0, mask=1)
        assert_(x.filled().dtype is x._data.dtype)

    def test_basic1d(self):
        # Test of basic array creation and properties in 1 dimension.
        (x, y, a10, m1, m2, xm, ym, z, zm, xf) = self.d
        assert_(not isMaskedArray(x))
        assert_(isMaskedArray(xm))
        assert_((xm - ym).filled(0).any())
        fail_if_equal(xm.mask.astype(int), ym.mask.astype(int))
        s = x.shape
        assert_equal(np.shape(xm), s)
        assert_equal(xm.shape, s)
        assert_equal(xm.dtype, x.dtype)
        assert_equal(zm.dtype, z.dtype)
        assert_equal(xm.size, reduce(lambda x, y: x * y, s))
        assert_equal(count(xm), len(m1) - reduce(lambda x, y: x + y, m1))
        assert_array_equal(xm, xf)
        assert_array_equal(filled(xm, 1.e20), xf)
        assert_array_equal(x, xm)

    def test_basic2d(self):
        # Test of basic array creation and properties in 2 dimensions.
        (x, y, a10, m1, m2, xm, ym, z, zm, xf) = self.d
        for s in [(4, 3), (6, 2)]:
            x.shape = s
            y.shape = s
            xm.shape = s
            ym.shape = s
            xf.shape = s

            assert_(not isMaskedArray(x))
            assert_(isMaskedArray(xm))
            assert_equal(shape(xm), s)
            assert_equal(xm.shape, s)
            assert_equal(xm.size, reduce(lambda x, y: x * y, s))
            assert_equal(count(xm), len(m1) - reduce(lambda x, y: x + y, m1))
            assert_equal(xm, xf)
            assert_equal(filled(xm, 1.e20), xf)
            assert_equal(x, xm)

    def test_concatenate_basic(self):
        # Tests concatenations.
        (x, y, a10, m1, m2, xm, ym, z, zm, xf) = self.d
        # basic concatenation
        assert_equal(np.concatenate((x, y)), concatenate((xm, ym)))
        assert_equal(np.concatenate((x, y)), concatenate((x, y)))
        assert_equal(np.concatenate((x, y)), concatenate((xm, y)))
        assert_equal(np.concatenate((x, y, x)), concatenate((x, ym, x)))

    def test_concatenate_alongaxis(self):
        # Tests concatenations.
        (x, y, a10, m1, m2, xm, ym, z, zm, xf) = self.d
        # Concatenation along an axis
        s = (3, 4)
        x.shape = y.shape = xm.shape = ym.shape = s
        assert_equal(xm.mask, np.reshape(m1, s))
        assert_equal(ym.mask, np.reshape(m2, s))
        xmym = concatenate((xm, ym), 1)
        assert_equal(np.concatenate((x, y), 1), xmym)
        assert_equal(np.concatenate((xm.mask, ym.mask), 1), xmym._mask)

        x = zeros(2)
        y = array(ones(2), mask=[False, True])
        z = concatenate((x, y))
        assert_array_equal(z, [0, 0, 1, 1])
        assert_array_equal(z.mask, [False, False, False, True])
        z = concatenate((y, x))
        assert_array_equal(z, [1, 1, 0, 0])
        assert_array_equal(z.mask, [False, True, False, False])

    def test_concatenate_flexible(self):
        # Tests the concatenation on flexible arrays.
        data = masked_array(list(zip(np.random.rand(10),
                                     np.arange(10))),
                            dtype=[('a', float), ('b', int)])

        test = concatenate([data[:5], data[5:]])
        assert_equal_records(test, data)

    def test_creation_ndmin(self):
        # Check the use of ndmin
        x = array([1, 2, 3], mask=[1, 0, 0], ndmin=2)
        assert_equal(x.shape, (1, 3))
        assert_equal(x._data, [[1, 2, 3]])
        assert_equal(x._mask, [[1, 0, 0]])

    def test_creation_ndmin_from_maskedarray(self):
        # Make sure we're not losing the original mask w/ ndmin
        x = array([1, 2, 3])
        x[-1] = masked
        xx = array(x, ndmin=2, dtype=float)
        assert_equal(x.shape, x._mask.shape)
        assert_equal(xx.shape, xx._mask.shape)

    def test_creation_maskcreation(self):
        # Tests how masks are initialized at the creation of Maskedarrays.
        data = arange(24, dtype=float)
        data[[3, 6, 15]] = masked
        dma_1 = MaskedArray(data)
        assert_equal(dma_1.mask, data.mask)
        dma_2 = MaskedArray(dma_1)
        assert_equal(dma_2.mask, dma_1.mask)
        dma_3 = MaskedArray(dma_1, mask=[1, 0, 0, 0] * 6)
        fail_if_equal(dma_3.mask, dma_1.mask)

        x = array([1, 2, 3], mask=True)
        assert_equal(x._mask, [True, True, True])
        x = array([1, 2, 3], mask=False)
        assert_equal(x._mask, [False, False, False])
        y = array([1, 2, 3], mask=x._mask, copy=False)
        assert_(np.may_share_memory(x.mask, y.mask))
        y = array([1, 2, 3], mask=x._mask, copy=True)
        assert_(not np.may_share_memory(x.mask, y.mask))
        x = array([1, 2, 3], mask=None)
        assert_equal(x._mask, [False, False, False])

    def test_masked_singleton_array_creation_warns(self):
        # The first works, but should not (ideally), there may be no way
        # to solve this, however, as long as `np.ma.masked` is an ndarray.
        np.array(np.ma.masked)
        with pytest.warns(UserWarning):
            # Tries to create a float array, using `float(np.ma.masked)`.
            # We may want to define this is invalid behaviour in the future!
            # (requiring np.ma.masked to be a known NumPy scalar probably
            # with a DType.)
            np.array([3., np.ma.masked])

    def test_creation_with_list_of_maskedarrays(self):
        # Tests creating a masked array from a list of masked arrays.
        x = array(np.arange(5), mask=[1, 0, 0, 0, 0])
        data = array((x, x[::-1]))
        assert_equal(data, [[0, 1, 2, 3, 4], [4, 3, 2, 1, 0]])
        assert_equal(data._mask, [[1, 0, 0, 0, 0], [0, 0, 0, 0, 1]])

        x.mask = nomask
        data = array((x, x[::-1]))
        assert_equal(data, [[0, 1, 2, 3, 4], [4, 3, 2, 1, 0]])
        assert_(data.mask is nomask)

    def test_creation_with_list_of_maskedarrays_no_bool_cast(self):
        # Tests the regression in gh-18551
        masked_str = np.ma.masked_array(['a', 'b'], mask=[True, False])
        normal_int = np.arange(2)
        res = np.ma.asarray([masked_str, normal_int], dtype="U21")
        assert_array_equal(res.mask, [[True, False], [False, False]])

        # The above only failed due a long chain of oddity, try also with
        # an object array that cannot be converted to bool always:
        class NotBool:
            def __bool__(self):
                raise ValueError("not a bool!")
        masked_obj = np.ma.masked_array([NotBool(), 'b'], mask=[True, False])
        # Check that the NotBool actually fails like we would expect:
        with pytest.raises(ValueError, match="not a bool!"):
            np.asarray([masked_obj], dtype=bool)

        res = np.ma.asarray([masked_obj, normal_int])
        assert_array_equal(res.mask, [[True, False], [False, False]])

    def test_creation_from_ndarray_with_padding(self):
        x = np.array([('A', 0)], dtype={'names': ['f0', 'f1'],
                                        'formats': ['S4', 'i8'],
                                        'offsets': [0, 8]})
        array(x)  # used to fail due to 'V' padding field in x.dtype.descr

    def test_unknown_keyword_parameter(self):
        with pytest.raises(TypeError, match="unexpected keyword argument"):
            MaskedArray([1, 2, 3], maks=[0, 1, 0])  # `mask` is misspelled.

    def test_asarray(self):
        (x, y, a10, m1, m2, xm, ym, z, zm, xf) = self.d
        xm.fill_value = -9999
        xm._hardmask = True
        xmm = asarray(xm)
        assert_equal(xmm._data, xm._data)
        assert_equal(xmm._mask, xm._mask)
        assert_equal(xmm.fill_value, xm.fill_value)
        assert_equal(xmm._hardmask, xm._hardmask)

    def test_asarray_default_order(self):
        # See Issue #6646
        m = np.eye(3).T
        assert_(not m.flags.c_contiguous)

        new_m = asarray(m)
        assert_(new_m.flags.c_contiguous)

    def test_asarray_enforce_order(self):
        # See Issue #6646
        m = np.eye(3).T
        assert_(not m.flags.c_contiguous)

        new_m = asarray(m, order='C')
        assert_(new_m.flags.c_contiguous)

    def test_fix_invalid(self):
        # Checks fix_invalid.
        with np.errstate(invalid='ignore'):
            data = masked_array([np.nan, 0., 1.], mask=[0, 0, 1])
            data_fixed = fix_invalid(data)
            assert_equal(data_fixed._data, [data.fill_value, 0., 1.])
            assert_equal(data_fixed._mask, [1., 0., 1.])

    def test_maskedelement(self):
        # Test of masked element
        x = arange(6)
        x[1] = masked
        assert_(str(masked) == '--')
        assert_(x[1] is masked)
        assert_equal(filled(x[1], 0), 0)

    def test_set_element_as_object(self):
        # Tests setting elements with object
        a = empty(1, dtype=object)
        x = (1, 2, 3, 4, 5)
        a[0] = x
        assert_equal(a[0], x)
        assert_(a[0] is x)

        import datetime
        dt = datetime.datetime.now()
        a[0] = dt
        assert_(a[0] is dt)

    def test_indexing(self):
        # Tests conversions and indexing
        x1 = np.array([1, 2, 4, 3])
        x2 = array(x1, mask=[1, 0, 0, 0])
        x3 = array(x1, mask=[0, 1, 0, 1])
        x4 = array(x1)
        # test conversion to strings
        str(x2)  # raises?
        repr(x2)  # raises?
        assert_equal(np.sort(x1), sort(x2, endwith=False))
        # tests of indexing
        assert_(type(x2[1]) is type(x1[1]))
        assert_(x1[1] == x2[1])
        assert_(x2[0] is masked)
        assert_equal(x1[2], x2[2])
        assert_equal(x1[2:5], x2[2:5])
        assert_equal(x1[:], x2[:])
        assert_equal(x1[1:], x3[1:])
        x1[2] = 9
        x2[2] = 9
        assert_equal(x1, x2)
        x1[1:3] = 99
        x2[1:3] = 99
        assert_equal(x1, x2)
        x2[1] = masked
        assert_equal(x1, x2)
        x2[1:3] = masked
        assert_equal(x1, x2)
        x2[:] = x1
        x2[1] = masked
        assert_(allequal(getmask(x2), array([0, 1, 0, 0])))
        x3[:] = masked_array([1, 2, 3, 4], [0, 1, 1, 0])
        assert_(allequal(getmask(x3), array([0, 1, 1, 0])))
        x4[:] = masked_array([1, 2, 3, 4], [0, 1, 1, 0])
        assert_(allequal(getmask(x4), array([0, 1, 1, 0])))
        assert_(allequal(x4, array([1, 2, 3, 4])))
        x1 = np.arange(5) * 1.0
        x2 = masked_values(x1, 3.0)
        assert_equal(x1, x2)
        assert_(allequal(array([0, 0, 0, 1, 0], MaskType), x2.mask))
        assert_equal(3.0, x2.fill_value)
        x1 = array([1, 'hello', 2, 3], object)
        x2 = np.array([1, 'hello', 2, 3], object)
        s1 = x1[1]
        s2 = x2[1]
        assert_equal(type(s2), str)
        assert_equal(type(s1), str)
        assert_equal(s1, s2)
        assert_(x1[1:1].shape == (0,))

    def test_setitem_no_warning(self):
        # Setitem shouldn't warn, because the assignment might be masked
        # and warning for a masked assignment is weird (see gh-23000)
        # (When the value is masked, otherwise a warning would be acceptable
        # but is not given currently.)
        x = np.ma.arange(60).reshape((6, 10))
        index = (slice(1, 5, 2), [7, 5])
        value = np.ma.masked_all((2, 2))
        value._data[...] = np.inf  # not a valid integer...
        x[index] = value
        # The masked scalar is special cased, but test anyway (it's NaN):
        x[...] = np.ma.masked
        # Finally, a large value that cannot be cast to the float32 `x`
        x = np.ma.arange(3., dtype=np.float32)
        value = np.ma.array([2e234, 1, 1], mask=[True, False, False])
        x[...] = value
        x[[0, 1, 2]] = value

    @suppress_copy_mask_on_assignment
    def test_copy(self):
        # Tests of some subtle points of copying and sizing.
        n = [0, 0, 1, 0, 0]
        m = make_mask(n)
        m2 = make_mask(m)
        assert_(m is m2)
        m3 = make_mask(m, copy=True)
        assert_(m is not m3)

        x1 = np.arange(5)
        y1 = array(x1, mask=m)
        assert_equal(y1._data.__array_interface__, x1.__array_interface__)
        assert_(allequal(x1, y1.data))
        assert_equal(y1._mask.__array_interface__, m.__array_interface__)

        y1a = array(y1)
        # Default for masked array is not to copy; see gh-10318.
        assert_(y1a._data.__array_interface__ ==
                        y1._data.__array_interface__)
        assert_(y1a._mask.__array_interface__ ==
                        y1._mask.__array_interface__)

        y2 = array(x1, mask=m3)
        assert_(y2._data.__array_interface__ == x1.__array_interface__)
        assert_(y2._mask.__array_interface__ == m3.__array_interface__)
        assert_(y2[2] is masked)
        y2[2] = 9
        assert_(y2[2] is not masked)
        assert_(y2._mask.__array_interface__ == m3.__array_interface__)
        assert_(allequal(y2.mask, 0))

        y2a = array(x1, mask=m, copy=1)
        assert_(y2a._data.__array_interface__ != x1.__array_interface__)
        #assert_( y2a._mask is not m)
        assert_(y2a._mask.__array_interface__ != m.__array_interface__)
        assert_(y2a[2] is masked)
        y2a[2] = 9
        assert_(y2a[2] is not masked)
        #assert_( y2a._mask is not m)
        assert_(y2a._mask.__array_interface__ != m.__array_interface__)
        assert_(allequal(y2a.mask, 0))

        y3 = array(x1 * 1.0, mask=m)
        assert_(filled(y3).dtype is (x1 * 1.0).dtype)

        x4 = arange(4)
        x4[2] = masked
        y4 = resize(x4, (8,))
        assert_equal(concatenate([x4, x4]), y4)
        assert_equal(getmask(y4), [0, 0, 1, 0, 0, 0, 1, 0])
        y5 = repeat(x4, (2, 2, 2, 2), axis=0)
        assert_equal(y5, [0, 0, 1, 1, 2, 2, 3, 3])
        y6 = repeat(x4, 2, axis=0)
        assert_equal(y5, y6)
        y7 = x4.repeat((2, 2, 2, 2), axis=0)
        assert_equal(y5, y7)
        y8 = x4.repeat(2, 0)
        assert_equal(y5, y8)

        y9 = x4.copy()
        assert_equal(y9._data, x4._data)
        assert_equal(y9._mask, x4._mask)

        x = masked_array([1, 2, 3], mask=[0, 1, 0])
        # Copy is False by default
        y = masked_array(x)
        assert_equal(y._data.ctypes.data, x._data.ctypes.data)
        assert_equal(y._mask.ctypes.data, x._mask.ctypes.data)
        y = masked_array(x, copy=True)
        assert_not_equal(y._data.ctypes.data, x._data.ctypes.data)
        assert_not_equal(y._mask.ctypes.data, x._mask.ctypes.data)

    def test_copy_0d(self):
        # gh-9430
        x = np.ma.array(43, mask=True)
        xc = x.copy()
        assert_equal(xc.mask, True)

    def test_copy_on_python_builtins(self):
        # Tests copy works on python builtins (issue#8019)
        assert_(isMaskedArray(np.ma.copy([1, 2, 3])))
        assert_(isMaskedArray(np.ma.copy((1, 2, 3))))

    def test_copy_immutable(self):
        # Tests that the copy method is immutable, GitHub issue #5247
        a = np.ma.array([1, 2, 3])
        b = np.ma.array([4, 5, 6])
        a_copy_method = a.copy
        b.copy
        assert_equal(a_copy_method(), [1, 2, 3])

    def test_deepcopy(self):
        from copy import deepcopy
        a = array([0, 1, 2], mask=[False, True, False])
        copied = deepcopy(a)
        assert_equal(copied.mask, a.mask)
        assert_not_equal(id(a._mask), id(copied._mask))

        copied[1] = 1
        assert_equal(copied.mask, [0, 0, 0])
        assert_equal(a.mask, [0, 1, 0])

        copied = deepcopy(a)
        assert_equal(copied.mask, a.mask)
        copied.mask[1] = False
        assert_equal(copied.mask, [0, 0, 0])
        assert_equal(a.mask, [0, 1, 0])

    def test_format(self):
        a = array([0, 1, 2], mask=[False, True, False])
        assert_equal(format(a), "[0 -- 2]")
        assert_equal(format(masked), "--")
        assert_equal(format(masked, ""), "--")

        # Postponed from PR #15410, perhaps address in the future.
        # assert_equal(format(masked, " >5"), "   --")
        # assert_equal(format(masked, " <5"), "--   ")

        # Expect a FutureWarning for using format_spec with MaskedElement
        with assert_warns(FutureWarning):
            with_format_string = format(masked, " >5")
        assert_equal(with_format_string, "--")

    def test_str_repr(self):
        a = array([0, 1, 2], mask=[False, True, False])
        assert_equal(str(a), '[0 -- 2]')
        assert_equal(
            repr(a),
            textwrap.dedent('''\
            masked_array(data=[0, --, 2],
                         mask=[False,  True, False],
                   fill_value=999999)''')
        )

        # arrays with a continuation
        a = np.ma.arange(2000)
        a[1:50] = np.ma.masked
        assert_equal(
            repr(a),
            textwrap.dedent('''\
            masked_array(data=[0, --, --, ..., 1997, 1998, 1999],
                         mask=[False,  True,  True, ..., False, False, False],
                   fill_value=999999)''')
        )

        # line-wrapped 1d arrays are correctly aligned
        a = np.ma.arange(20)
        assert_equal(
            repr(a),
            textwrap.dedent('''\
            masked_array(data=[ 0,  1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12, 13,
                               14, 15, 16, 17, 18, 19],
                         mask=False,
                   fill_value=999999)''')
        )

        # 2d arrays cause wrapping
        a = array([[1, 2, 3], [4, 5, 6]], dtype=np.int8)
        a[1, 1] = np.ma.masked
        assert_equal(
            repr(a),
            textwrap.dedent(f'''\
            masked_array(
              data=[[1, 2, 3],
                    [4, --, 6]],
              mask=[[False, False, False],
                    [False,  True, False]],
              fill_value={np.array(999999)[()]!r},
              dtype=int8)''')
        )

        # but not it they're a row vector
        assert_equal(
            repr(a[:1]),
            textwrap.dedent(f'''\
            masked_array(data=[[1, 2, 3]],
                         mask=[[False, False, False]],
                   fill_value={np.array(999999)[()]!r},
                        dtype=int8)''')
        )

        # dtype=int is implied, so not shown
        assert_equal(
            repr(a.astype(int)),
            textwrap.dedent('''\
            masked_array(
              data=[[1, 2, 3],
                    [4, --, 6]],
              mask=[[False, False, False],
                    [False,  True, False]],
              fill_value=999999)''')
        )

    def test_str_repr_legacy(self):
        oldopts = np.get_printoptions()
        np.set_printoptions(legacy='1.13')
        try:
            a = array([0, 1, 2], mask=[False, True, False])
            assert_equal(str(a), '[0 -- 2]')
            assert_equal(repr(a), 'masked_array(data = [0 -- 2],\n'
                                  '             mask = [False  True False],\n'
                                  '       fill_value = 999999)\n')

            a = np.ma.arange(2000)
            a[1:50] = np.ma.masked
            assert_equal(
                repr(a),
                'masked_array(data = [0 -- -- ..., 1997 1998 1999],\n'
                '             mask = [False  True  True ..., False False False],\n'
                '       fill_value = 999999)\n'
            )
        finally:
            np.set_printoptions(**oldopts)

    def test_0d_unicode(self):
        u = 'caf\xe9'
        utype = type(u)

        arr_nomask = np.ma.array(u)
        arr_masked = np.ma.array(u, mask=True)

        assert_equal(utype(arr_nomask), u)
        assert_equal(utype(arr_masked), '--')

    def test_pickling(self):
        # Tests pickling
        for dtype in (int, float, str, object):
            a = arange(10).astype(dtype)
            a.fill_value = 999

            masks = ([0, 0, 0, 1, 0, 1, 0, 1, 0, 1],  # partially masked
                     True,                            # Fully masked
                     False)                           # Fully unmasked

            for proto in range(2, pickle.HIGHEST_PROTOCOL + 1):
                for mask in masks:
                    a.mask = mask
                    a_pickled = pickle.loads(pickle.dumps(a, protocol=proto))
                    assert_equal(a_pickled._mask, a._mask)
                    assert_equal(a_pickled._data, a._data)
                    if dtype in (object, int):
                        assert_equal(a_pickled.fill_value, 999)
                    else:
                        assert_equal(a_pickled.fill_value, dtype(999))
                    assert_array_equal(a_pickled.mask, mask)

    def test_pickling_subbaseclass(self):
        # Test pickling w/ a subclass of ndarray
        x = np.array([(1.0, 2), (3.0, 4)],
                     dtype=[('x', float), ('y', int)]).view(np.recarray)
        a = masked_array(x, mask=[(True, False), (False, True)])
        for proto in range(2, pickle.HIGHEST_PROTOCOL + 1):
            a_pickled = pickle.loads(pickle.dumps(a, protocol=proto))
            assert_equal(a_pickled._mask, a._mask)
            assert_equal(a_pickled, a)
            assert_(isinstance(a_pickled._data, np.recarray))

    def test_pickling_maskedconstant(self):
        # Test pickling MaskedConstant
        mc = np.ma.masked
        for proto in range(2, pickle.HIGHEST_PROTOCOL + 1):
            mc_pickled = pickle.loads(pickle.dumps(mc, protocol=proto))
            assert_equal(mc_pickled._baseclass, mc._baseclass)
            assert_equal(mc_pickled._mask, mc._mask)
            assert_equal(mc_pickled._data, mc._data)

    def test_pickling_wstructured(self):
        # Tests pickling w/ structured array
        a = array([(1, 1.), (2, 2.)], mask=[(0, 0), (0, 1)],
                  dtype=[('a', int), ('b', float)])
        for proto in range(2, pickle.HIGHEST_PROTOCOL + 1):
            a_pickled = pickle.loads(pickle.dumps(a, protocol=proto))
            assert_equal(a_pickled._mask, a._mask)
            assert_equal(a_pickled, a)

    def test_pickling_keepalignment(self):
        # Tests pickling w/ F_CONTIGUOUS arrays
        a = arange(10)
        a.shape = (-1, 2)
        b = a.T
        for proto in range(2, pickle.HIGHEST_PROTOCOL + 1):
            test = pickle.loads(pickle.dumps(b, protocol=proto))
            assert_equal(test, b)

    def test_single_element_subscript(self):
        # Tests single element subscripts of Maskedarrays.
        a = array([1, 3, 2])
        b = array([1, 3, 2], mask=[1, 0, 1])
        assert_equal(a[0].shape, ())
        assert_equal(b[0].shape, ())
        assert_equal(b[1].shape, ())

    def test_topython(self):
        # Tests some communication issues with Python.
        assert_equal(1, int(array(1)))
        assert_equal(1.0, float(array(1)))
        assert_equal(1, int(array([[[1]]])))
        assert_equal(1.0, float(array([[1]])))
        assert_raises(TypeError, float, array([1, 1]))

        with suppress_warnings() as sup:
            sup.filter(UserWarning, 'Warning: converting a masked element')
            assert_(np.isnan(float(array([1], mask=[1]))))

            a = array([1, 2, 3], mask=[1, 0, 0])
            assert_raises(TypeError, lambda: float(a))
            assert_equal(float(a[-1]), 3.)
            assert_(np.isnan(float(a[0])))
        assert_raises(TypeError, int, a)
        assert_equal(int(a[-1]), 3)
        assert_raises(MAError, lambda: int(a[0]))

    def test_oddfeatures_1(self):
        # Test of other odd features
        x = arange(20)
        x = x.reshape(4, 5)
        x.flat[5] = 12
        assert_(x[1, 0] == 12)
        z = x + 10j * x
        assert_equal(z.real, x)
        assert_equal(z.imag, 10 * x)
        assert_equal((z * conjugate(z)).real, 101 * x * x)
        z.imag[...] = 0.0

        x = arange(10)
        x[3] = masked
        assert_(str(x[3]) == str(masked))
        c = x >= 8
        assert_(count(where(c, masked, masked)) == 0)
        assert_(shape(where(c, masked, masked)) == c.shape)

        z = masked_where(c, x)
        assert_(z.dtype is x.dtype)
        assert_(z[3] is masked)
        assert_(z[4] is not masked)
        assert_(z[7] is not masked)
        assert_(z[8] is masked)
        assert_(z[9] is masked)
        assert_equal(x, z)

    def test_oddfeatures_2(self):
        # Tests some more features.
        x = array([1., 2., 3., 4., 5.])
        c = array([1, 1, 1, 0, 0])
        x[2] = masked
        z = where(c, x, -x)
        assert_equal(z, [1., 2., 0., -4., -5])
        c[0] = masked
        z = where(c, x, -x)
        assert_equal(z, [1., 2., 0., -4., -5])
        assert_(z[0] is masked)
        assert_(z[1] is not masked)
        assert_(z[2] is masked)

    @suppress_copy_mask_on_assignment
    def test_oddfeatures_3(self):
        # Tests some generic features
        atest = array([10], mask=True)
        btest = array([20])
        idx = atest.mask
        atest[idx] = btest[idx]
        assert_equal(atest, [20])

    def test_filled_with_object_dtype(self):
        a = np.ma.masked_all(1, dtype='O')
        assert_equal(a.filled('x')[0], 'x')

    def test_filled_with_flexible_dtype(self):
        # Test filled w/ flexible dtype
        flexi = array([(1, 1, 1)],
                      dtype=[('i', int), ('s', '|S8'), ('f', float)])
        flexi[0] = masked
        assert_equal(flexi.filled(),
                     np.array([(default_fill_value(0),
                                default_fill_value('0'),
                                default_fill_value(0.),)], dtype=flexi.dtype))
        flexi[0] = masked
        assert_equal(flexi.filled(1),
                     np.array([(1, '1', 1.)], dtype=flexi.dtype))

    def test_filled_with_mvoid(self):
        # Test filled w/ mvoid
        ndtype = [('a', int), ('b', float)]
        a = mvoid((1, 2.), mask=[(0, 1)], dtype=ndtype)
        # Filled using default
        test = a.filled()
        assert_equal(tuple(test), (1, default_fill_value(1.)))
        # Explicit fill_value
        test = a.filled((-1, -1))
        assert_equal(tuple(test), (1, -1))
        # Using predefined filling values
        a.fill_value = (-999, -999)
        assert_equal(tuple(a.filled()), (1, -999))

    def test_filled_with_nested_dtype(self):
        # Test filled w/ nested dtype
        ndtype = [('A', int), ('B', [('BA', int), ('BB', int)])]
        a = array([(1, (1, 1)), (2, (2, 2))],
                  mask=[(0, (1, 0)), (0, (0, 1))], dtype=ndtype)
        test = a.filled(0)
        control = np.array([(1, (0, 1)), (2, (2, 0))], dtype=ndtype)
        assert_equal(test, control)

        test = a['B'].filled(0)
        control = np.array([(0, 1), (2, 0)], dtype=a['B'].dtype)
        assert_equal(test, control)

        # test if mask gets set correctly (see #6760)
        Z = numpy.ma.zeros(2, numpy.dtype([("A", "(2,2)i1,(2,2)i1", (2, 2))]))
        assert_equal(Z.data.dtype, numpy.dtype([('A', [('f0', 'i1', (2, 2)),
                                          ('f1', 'i1', (2, 2))], (2, 2))]))
        assert_equal(Z.mask.dtype, numpy.dtype([('A', [('f0', '?', (2, 2)),
                                          ('f1', '?', (2, 2))], (2, 2))]))

    def test_filled_with_f_order(self):
        # Test filled w/ F-contiguous array
        a = array(np.array([(0, 1, 2), (4, 5, 6)], order='F'),
                  mask=np.array([(0, 0, 1), (1, 0, 0)], order='F'),
                  order='F')  # this is currently ignored
        assert_(a.flags['F_CONTIGUOUS'])
        assert_(a.filled(0).flags['F_CONTIGUOUS'])

    def test_optinfo_propagation(self):
        # Checks that _optinfo dictionary isn't back-propagated
        x = array([1, 2, 3, ], dtype=float)
        x._optinfo['info'] = '???'
        y = x.copy()
        assert_equal(y._optinfo['info'], '???')
        y._optinfo['info'] = '!!!'
        assert_equal(x._optinfo['info'], '???')

    def test_optinfo_forward_propagation(self):
        a = array([1, 2, 2, 4])
        a._optinfo["key"] = "value"
        assert_equal(a._optinfo["key"], (a == 2)._optinfo["key"])
        assert_equal(a._optinfo["key"], (a != 2)._optinfo["key"])
        assert_equal(a._optinfo["key"], (a > 2)._optinfo["key"])
        assert_equal(a._optinfo["key"], (a >= 2)._optinfo["key"])
        assert_equal(a._optinfo["key"], (a <= 2)._optinfo["key"])
        assert_equal(a._optinfo["key"], (a + 2)._optinfo["key"])
        assert_equal(a._optinfo["key"], (a - 2)._optinfo["key"])
        assert_equal(a._optinfo["key"], (a * 2)._optinfo["key"])
        assert_equal(a._optinfo["key"], (a / 2)._optinfo["key"])
        assert_equal(a._optinfo["key"], a[:2]._optinfo["key"])
        assert_equal(a._optinfo["key"], a[[0, 0, 2]]._optinfo["key"])
        assert_equal(a._optinfo["key"], np.exp(a)._optinfo["key"])
        assert_equal(a._optinfo["key"], np.abs(a)._optinfo["key"])
        assert_equal(a._optinfo["key"], array(a, copy=True)._optinfo["key"])
        assert_equal(a._optinfo["key"], np.zeros_like(a)._optinfo["key"])

    def test_fancy_printoptions(self):
        # Test printing a masked array w/ fancy dtype.
        fancydtype = np.dtype([('x', int), ('y', [('t', int), ('s', float)])])
        test = array([(1, (2, 3.0)), (4, (5, 6.0))],
                     mask=[(1, (0, 1)), (0, (1, 0))],
                     dtype=fancydtype)
        control = "[(--, (2, --)) (4, (--, 6.0))]"
        assert_equal(str(test), control)

        # Test 0-d array with multi-dimensional dtype
        t_2d0 = masked_array(data=(0, [[0.0, 0.0, 0.0],
                                       [0.0, 0.0, 0.0]],
                                   0.0),
                             mask=(False, [[True, False, True],
                                           [False, False, True]],
                                   False),
                             dtype="int, (2,3)float, float")
        control = "(0, [[--, 0.0, --], [0.0, 0.0, --]], 0.0)"
        assert_equal(str(t_2d0), control)

    def test_flatten_structured_array(self):
        # Test flatten_structured_array on arrays
        # On ndarray
        ndtype = [('a', int), ('b', float)]
        a = np.array([(1, 1), (2, 2)], dtype=ndtype)
        test = flatten_structured_array(a)
        control = np.array([[1., 1.], [2., 2.]], dtype=float)
        assert_equal(test, control)
        assert_equal(test.dtype, control.dtype)
        # On masked_array
        a = array([(1, 1), (2, 2)], mask=[(0, 1), (1, 0)], dtype=ndtype)
        test = flatten_structured_array(a)
        control = array([[1., 1.], [2., 2.]],
                        mask=[[0, 1], [1, 0]], dtype=float)
        assert_equal(test, control)
        assert_equal(test.dtype, control.dtype)
        assert_equal(test.mask, control.mask)
        # On masked array with nested structure
        ndtype = [('a', int), ('b', [('ba', int), ('bb', float)])]
        a = array([(1, (1, 1.1)), (2, (2, 2.2))],
                  mask=[(0, (1, 0)), (1, (0, 1))], dtype=ndtype)
        test = flatten_structured_array(a)
        control = array([[1., 1., 1.1], [2., 2., 2.2]],
                        mask=[[0, 1, 0], [1, 0, 1]], dtype=float)
        assert_equal(test, control)
        assert_equal(test.dtype, control.dtype)
        assert_equal(test.mask, control.mask)
        # Keeping the initial shape
        ndtype = [('a', int), ('b', float)]
        a = np.array([[(1, 1), ], [(2, 2), ]], dtype=ndtype)
        test = flatten_structured_array(a)
        control = np.array([[[1., 1.], ], [[2., 2.], ]], dtype=float)
        assert_equal(test, control)
        assert_equal(test.dtype, control.dtype)

    def test_void0d(self):
        # Test creating a mvoid object
        ndtype = [('a', int), ('b', int)]
        a = np.array([(1, 2,)], dtype=ndtype)[0]
        f = mvoid(a)
        assert_(isinstance(f, mvoid))

        a = masked_array([(1, 2)], mask=[(1, 0)], dtype=ndtype)[0]
        assert_(isinstance(a, mvoid))

        a = masked_array([(1, 2), (1, 2)], mask=[(1, 0), (0, 0)], dtype=ndtype)
        f = mvoid(a._data[0], a._mask[0])
        assert_(isinstance(f, mvoid))

    def test_mvoid_getitem(self):
        # Test mvoid.__getitem__
        ndtype = [('a', int), ('b', int)]
        a = masked_array([(1, 2,), (3, 4)], mask=[(0, 0), (1, 0)],
                         dtype=ndtype)
        # w/o mask
        f = a[0]
        assert_(isinstance(f, mvoid))
        assert_equal((f[0], f['a']), (1, 1))
        assert_equal(f['b'], 2)
        # w/ mask
        f = a[1]
        assert_(isinstance(f, mvoid))
        assert_(f[0] is masked)
        assert_(f['a'] is masked)
        assert_equal(f[1], 4)

        # exotic dtype
        A = masked_array(data=[([0, 1],)],
                         mask=[([True, False],)],
                         dtype=[("A", ">i2", (2,))])
        assert_equal(A[0]["A"], A["A"][0])
        assert_equal(A[0]["A"], masked_array(data=[0, 1],
                         mask=[True, False], dtype=">i2"))

    def test_mvoid_iter(self):
        # Test iteration on __getitem__
        ndtype = [('a', int), ('b', int)]
        a = masked_array([(1, 2,), (3, 4)], mask=[(0, 0), (1, 0)],
                         dtype=ndtype)
        # w/o mask
        assert_equal(list(a[0]), [1, 2])
        # w/ mask
        assert_equal(list(a[1]), [masked, 4])

    def test_mvoid_print(self):
        # Test printing a mvoid
        mx = array([(1, 1), (2, 2)], dtype=[('a', int), ('b', int)])
        assert_equal(str(mx[0]), "(1, 1)")
        mx['b'][0] = masked
        ini_display = masked_print_option._display
        masked_print_option.set_display("-X-")
        try:
            assert_equal(str(mx[0]), "(1, -X-)")
            assert_equal(repr(mx[0]), "(1, -X-)")
        finally:
            masked_print_option.set_display(ini_display)

        # also check if there are object datatypes (see gh-7493)
        mx = array([(1,), (2,)], dtype=[('a', 'O')])
        assert_equal(str(mx[0]), "(1,)")

    def test_mvoid_multidim_print(self):

        # regression test for gh-6019
        t_ma = masked_array(data=[([1, 2, 3],)],
                            mask=[([False, True, False],)],
                            fill_value=([999999, 999999, 999999],),
                            dtype=[('a', '<i4', (3,))])
        assert_(str(t_ma[0]) == "([1, --, 3],)")
        assert_(repr(t_ma[0]) == "([1, --, 3],)")

        # additional tests with structured arrays

        t_2d = masked_array(data=[([[1, 2], [3, 4]],)],
                            mask=[([[False, True], [True, False]],)],
                            dtype=[('a', '<i4', (2, 2))])
        assert_(str(t_2d[0]) == "([[1, --], [--, 4]],)")
        assert_(repr(t_2d[0]) == "([[1, --], [--, 4]],)")

        t_0d = masked_array(data=[(1, 2)],
                            mask=[(True, False)],
                            dtype=[('a', '<i4'), ('b', '<i4')])
        assert_(str(t_0d[0]) == "(--, 2)")
        assert_(repr(t_0d[0]) == "(--, 2)")

        t_2d = masked_array(data=[([[1, 2], [3, 4]], 1)],
                            mask=[([[False, True], [True, False]], False)],
                            dtype=[('a', '<i4', (2, 2)), ('b', float)])
        assert_(str(t_2d[0]) == "([[1, --], [--, 4]], 1.0)")
        assert_(repr(t_2d[0]) == "([[1, --], [--, 4]], 1.0)")

        t_ne = masked_array(data=[(1, (1, 1))],
                            mask=[(True, (True, False))],
                            dtype=[('a', '<i4'), ('b', 'i4,i4')])
        assert_(str(t_ne[0]) == "(--, (--, 1))")
        assert_(repr(t_ne[0]) == "(--, (--, 1))")

    def test_object_with_array(self):
        mx1 = masked_array([1.], mask=[True])
        mx2 = masked_array([1., 2.])
        mx = masked_array([mx1, mx2], mask=[False, True], dtype=object)
        assert_(mx[0] is mx1)
        assert_(mx[1] is not mx2)
        assert_(np.all(mx[1].data == mx2.data))
        assert_(np.all(mx[1].mask))
        # check that we return a view.
        mx[1].data[0] = 0.
        assert_(mx2[0] == 0.)

    def test_maskedarray_tofile_raises_notimplementederror(self):
        xm = masked_array([1, 2, 3], mask=[False, True, False])
        # Test case to check the NotImplementedError.
        # It is not implemented at this point of time. We can change this in future
        with temppath(suffix='.npy') as path:
            with pytest.raises(NotImplementedError):
                np.save(path, xm)


class TestMaskedArrayArithmetic:
    # Base test class for MaskedArrays.

    def setup_method(self):
        # Base data definition.
        x = np.array([1., 1., 1., -2., pi / 2.0, 4., 5., -10., 10., 1., 2., 3.])
        y = np.array([5., 0., 3., 2., -1., -4., 0., -10., 10., 1., 0., 3.])
        a10 = 10.
        m1 = [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0]
        m2 = [0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1]
        xm = masked_array(x, mask=m1)
        ym = masked_array(y, mask=m2)
        z = np.array([-.5, 0., .5, .8])
        zm = masked_array(z, mask=[0, 1, 0, 0])
        xf = np.where(m1, 1e+20, x)
        xm.set_fill_value(1e+20)
        self.d = (x, y, a10, m1, m2, xm, ym, z, zm, xf)
        self.err_status = np.geterr()
        np.seterr(divide='ignore', invalid='ignore')

    def teardown_method(self):
        np.seterr(**self.err_status)

    def test_basic_arithmetic(self):
        # Test of basic arithmetic.
        (x, y, a10, m1, m2, xm, ym, z, zm, xf) = self.d
        a2d = array([[1, 2], [0, 4]])
        a2dm = masked_array(a2d, [[0, 0], [1, 0]])
        assert_equal(a2d * a2d, a2d * a2dm)
        assert_equal(a2d + a2d, a2d + a2dm)
        assert_equal(a2d - a2d, a2d - a2dm)
        for s in [(12,), (4, 3), (2, 6)]:
            x = x.reshape(s)
            y = y.reshape(s)
            xm = xm.reshape(s)
            ym = ym.reshape(s)
            xf = xf.reshape(s)
            assert_equal(-x, -xm)
            assert_equal(x + y, xm + ym)
            assert_equal(x - y, xm - ym)
            assert_equal(x * y, xm * ym)
            assert_equal(x / y, xm / ym)
            assert_equal(a10 + y, a10 + ym)
            assert_equal(a10 - y, a10 - ym)
            assert_equal(a10 * y, a10 * ym)
            assert_equal(a10 / y, a10 / ym)
            assert_equal(x + a10, xm + a10)
            assert_equal(x - a10, xm - a10)
            assert_equal(x * a10, xm * a10)
            assert_equal(x / a10, xm / a10)
            assert_equal(x ** 2, xm ** 2)
            assert_equal(abs(x) ** 2.5, abs(xm) ** 2.5)
            assert_equal(x ** y, xm ** ym)
            assert_equal(np.add(x, y), add(xm, ym))
            assert_equal(np.subtract(x, y), subtract(xm, ym))
            assert_equal(np.multiply(x, y), multiply(xm, ym))
            assert_equal(np.divide(x, y), divide(xm, ym))

    def test_divide_on_different_shapes(self):
        x = arange(6, dtype=float)
        x.shape = (2, 3)
        y = arange(3, dtype=float)

        z = x / y
        assert_equal(z, [[-1., 1., 1.], [-1., 4., 2.5]])
        assert_equal(z.mask, [[1, 0, 0], [1, 0, 0]])

        z = x / y[None, :]
        assert_equal(z, [[-1., 1., 1.], [-1., 4., 2.5]])
        assert_equal(z.mask, [[1, 0, 0], [1, 0, 0]])

        y = arange(2, dtype=float)
        z = x / y[:, None]
        assert_equal(z, [[-1., -1., -1.], [3., 4., 5.]])
        assert_equal(z.mask, [[1, 1, 1], [0, 0, 0]])

    def test_mixed_arithmetic(self):
        # Tests mixed arithmetic.
        na = np.array([1])
        ma = array([1])
        assert_(isinstance(na + ma, MaskedArray))
        assert_(isinstance(ma + na, MaskedArray))

    def test_limits_arithmetic(self):
        tiny = np.finfo(float).tiny
        a = array([tiny, 1. / tiny, 0.])
        assert_equal(getmaskarray(a / 2), [0, 0, 0])
        assert_equal(getmaskarray(2 / a), [1, 0, 1])

    def test_masked_singleton_arithmetic(self):
        # Tests some scalar arithmetic on MaskedArrays.
        # Masked singleton should remain masked no matter what
        xm = array(0, mask=1)
        assert_((1 / array(0)).mask)
        assert_((1 + xm).mask)
        assert_((-xm).mask)
        assert_(maximum(xm, xm).mask)
        assert_(minimum(xm, xm).mask)

    def test_masked_singleton_equality(self):
        # Tests (in)equality on masked singleton
        a = array([1, 2, 3], mask=[1, 1, 0])
        assert_((a[0] == 0) is masked)
        assert_((a[0] != 0) is masked)
        assert_equal((a[-1] == 0), False)
        assert_equal((a[-1] != 0), True)

    def test_arithmetic_with_masked_singleton(self):
        # Checks that there's no collapsing to masked
        x = masked_array([1, 2])
        y = x * masked
        assert_equal(y.shape, x.shape)
        assert_equal(y._mask, [True, True])
        y = x[0] * masked
        assert_(y is masked)
        y = x + masked
        assert_equal(y.shape, x.shape)
        assert_equal(y._mask, [True, True])

    def test_arithmetic_with_masked_singleton_on_1d_singleton(self):
        # Check that we're not losing the shape of a singleton
        x = masked_array([1, ])
        y = x + masked
        assert_equal(y.shape, x.shape)
        assert_equal(y.mask, [True, ])

    def test_scalar_arithmetic(self):
        x = array(0, mask=0)
        assert_equal(x.filled().ctypes.data, x.ctypes.data)
        # Make sure we don't lose the shape in some circumstances
        xm = array((0, 0)) / 0.
        assert_equal(xm.shape, (2,))
        assert_equal(xm.mask, [1, 1])

    def test_basic_ufuncs(self):
        # Test various functions such as sin, cos.
        (x, y, a10, m1, m2, xm, ym, z, zm, xf) = self.d
        assert_equal(np.cos(x), cos(xm))
        assert_equal(np.cosh(x), cosh(xm))
        assert_equal(np.sin(x), sin(xm))
        assert_equal(np.sinh(x), sinh(xm))
        assert_equal(np.tan(x), tan(xm))
        assert_equal(np.tanh(x), tanh(xm))
        assert_equal(np.sqrt(abs(x)), sqrt(xm))
        assert_equal(np.log(abs(x)), log(xm))
        assert_equal(np.log10(abs(x)), log10(xm))
        assert_equal(np.exp(x), exp(xm))
        assert_equal(np.arcsin(z), arcsin(zm))
        assert_equal(np.arccos(z), arccos(zm))
        assert_equal(np.arctan(z), arctan(zm))
        assert_equal(np.arctan2(x, y), arctan2(xm, ym))
        assert_equal(np.absolute(x), absolute(xm))
        assert_equal(np.angle(x + 1j * y), angle(xm + 1j * ym))
        assert_equal(np.angle(x + 1j * y, deg=True), angle(xm + 1j * ym, deg=True))
        assert_equal(np.equal(x, y), equal(xm, ym))
        assert_equal(np.not_equal(x, y), not_equal(xm, ym))
        assert_equal(np.less(x, y), less(xm, ym))
        assert_equal(np.greater(x, y), greater(xm, ym))
        assert_equal(np.less_equal(x, y), less_equal(xm, ym))
        assert_equal(np.greater_equal(x, y), greater_equal(xm, ym))
        assert_equal(np.conjugate(x), conjugate(xm))

    def test_basic_ufuncs_masked(self):
        # Mostly regression test for gh-25635
        assert np.sqrt(np.ma.masked) is np.ma.masked

    def test_count_func(self):
        # Tests count
        assert_equal(1, count(1))
        assert_equal(0, array(1, mask=[1]))

        ott = array([0., 1., 2., 3.], mask=[1, 0, 0, 0])
        res = count(ott)
        assert_(res.dtype.type is np.intp)
        assert_equal(3, res)

        ott = ott.reshape((2, 2))
        res = count(ott)
        assert_(res.dtype.type is np.intp)
        assert_equal(3, res)
        res = count(ott, 0)
        assert_(isinstance(res, ndarray))
        assert_equal([1, 2], res)
        assert_(getmask(res) is nomask)

        ott = array([0., 1., 2., 3.])
        res = count(ott, 0)
        assert_(isinstance(res, ndarray))
        assert_(res.dtype.type is np.intp)
        assert_raises(AxisError, ott.count, axis=1)

    def test_count_on_python_builtins(self):
        # Tests count works on python builtins (issue#8019)
        assert_equal(3, count([1, 2, 3]))
        assert_equal(2, count((1, 2)))

    def test_minmax_func(self):
        # Tests minimum and maximum.
        (x, y, a10, m1, m2, xm, ym, z, zm, xf) = self.d
        # max doesn't work if shaped
        xr = np.ravel(x)
        xmr = ravel(xm)
        # following are true because of careful selection of data
        assert_equal(max(xr), maximum.reduce(xmr))
        assert_equal(min(xr), minimum.reduce(xmr))

        assert_equal(minimum([1, 2, 3], [4, 0, 9]), [1, 0, 3])
        assert_equal(maximum([1, 2, 3], [4, 0, 9]), [4, 2, 9])
        x = arange(5)
        y = arange(5) - 2
        x[3] = masked
        y[0] = masked
        assert_equal(minimum(x, y), where(less(x, y), x, y))
        assert_equal(maximum(x, y), where(greater(x, y), x, y))
        assert_(minimum.reduce(x) == 0)
        assert_(maximum.reduce(x) == 4)

        x = arange(4).reshape(2, 2)
        x[-1, -1] = masked
        assert_equal(maximum.reduce(x, axis=None), 2)

    def test_minimummaximum_func(self):
        a = np.ones((2, 2))
        aminimum = minimum(a, a)
        assert_(isinstance(aminimum, MaskedArray))
        assert_equal(aminimum, np.minimum(a, a))

        aminimum = minimum.outer(a, a)
        assert_(isinstance(aminimum, MaskedArray))
        assert_equal(aminimum, np.minimum.outer(a, a))

        amaximum = maximum(a, a)
        assert_(isinstance(amaximum, MaskedArray))
        assert_equal(amaximum, np.maximum(a, a))

        amaximum = maximum.outer(a, a)
        assert_(isinstance(amaximum, MaskedArray))
        assert_equal(amaximum, np.maximum.outer(a, a))

    def test_minmax_reduce(self):
        # Test np.min/maximum.reduce on array w/ full False mask
        a = array([1, 2, 3], mask=[False, False, False])
        b = np.maximum.reduce(a)
        assert_equal(b, 3)

    def test_minmax_funcs_with_output(self):
        # Tests the min/max functions with explicit outputs
        mask = np.random.rand(12).round()
        xm = array(np.random.uniform(0, 10, 12), mask=mask)
        xm.shape = (3, 4)
        for funcname in ('min', 'max'):
            # Initialize
            npfunc = getattr(np, funcname)
            mafunc = getattr(numpy.ma.core, funcname)
            # Use the np version
            nout = np.empty((4,), dtype=int)
            try:
                result = npfunc(xm, axis=0, out=nout)
            except MaskError:
                pass
            nout = np.empty((4,), dtype=float)
            result = npfunc(xm, axis=0, out=nout)
            assert_(result is nout)
            # Use the ma version
            nout.fill(-999)
            result = mafunc(xm, axis=0, out=nout)
            assert_(result is nout)

    def test_minmax_methods(self):
        # Additional tests on max/min
        (_, _, _, _, _, xm, _, _, _, _) = self.d
        xm.shape = (xm.size,)
        assert_equal(xm.max(), 10)
        assert_(xm[0].max() is masked)
        assert_(xm[0].max(0) is masked)
        assert_(xm[0].max(-1) is masked)
        assert_equal(xm.min(), -10.)
        assert_(xm[0].min() is masked)
        assert_(xm[0].min(0) is masked)
        assert_(xm[0].min(-1) is masked)
        assert_equal(xm.ptp(), 20.)
        assert_(xm[0].ptp() is masked)
        assert_(xm[0].ptp(0) is masked)
        assert_(xm[0].ptp(-1) is masked)

        x = array([1, 2, 3], mask=True)
        assert_(x.min() is masked)
        assert_(x.max() is masked)
        assert_(x.ptp() is masked)

    def test_minmax_dtypes(self):
        # Additional tests on max/min for non-standard float and complex dtypes
        x = np.array([1., 1., 1., -2., pi / 2.0, 4., 5., -10., 10., 1., 2., 3.])
        a10 = 10.
        an10 = -10.0
        m1 = [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0]
        xm = masked_array(x, mask=m1)
        xm.set_fill_value(1e+20)
        float_dtypes = [np.float16, np.float32, np.float64, np.longdouble,
                        np.complex64, np.complex128, np.clongdouble]
        for float_dtype in float_dtypes:
            assert_equal(masked_array(x, mask=m1, dtype=float_dtype).max(),
                         float_dtype(a10))
            assert_equal(masked_array(x, mask=m1, dtype=float_dtype).min(),
                         float_dtype(an10))

        assert_equal(xm.min(), an10)
        assert_equal(xm.max(), a10)

        # Non-complex type only test
        for float_dtype in float_dtypes[:4]:
            assert_equal(masked_array(x, mask=m1, dtype=float_dtype).max(),
                         float_dtype(a10))
            assert_equal(masked_array(x, mask=m1, dtype=float_dtype).min(),
                         float_dtype(an10))

        # Complex types only test
        for float_dtype in float_dtypes[-3:]:
            ym = masked_array([1e20 + 1j, 1e20 - 2j, 1e20 - 1j], mask=[0, 1, 0],
                          dtype=float_dtype)
            assert_equal(ym.min(), float_dtype(1e20 - 1j))
            assert_equal(ym.max(), float_dtype(1e20 + 1j))

            zm = masked_array([np.inf + 2j, np.inf + 3j, -np.inf - 1j], mask=[0, 1, 0],
                              dtype=float_dtype)
            assert_equal(zm.min(), float_dtype(-np.inf - 1j))
            assert_equal(zm.max(), float_dtype(np.inf + 2j))

            cmax = np.inf - 1j * np.finfo(np.float64).max
            assert masked_array([-cmax, 0], mask=[0, 1]).max() == -cmax
            assert masked_array([cmax, 0], mask=[0, 1]).min() == cmax

    @pytest.mark.parametrize("dtype", "bBiIqQ")
    @pytest.mark.parametrize("mask", [
        [False, False, False, True, True],  # masked min/max
        [False, False, False, True, False],  # masked max only
        [False, False, False, False, True],  # masked min only
    ])
    @pytest.mark.parametrize("axis", [None, -1])
    def test_minmax_ints(self, dtype, mask, axis):
        iinfo = np.iinfo(dtype)
        # two dimensional to hit certain filling paths
        a = np.array([[0, 10, -10, iinfo.min, iinfo.max]] * 2).astype(dtype)
        mask = np.asarray([mask] * 2)

        masked_a = masked_array(a, mask=mask)
        assert_array_equal(masked_a.min(axis), a[~mask].min(axis))
        assert_array_equal(masked_a.max(axis), a[~mask].max(axis))

    @pytest.mark.parametrize("time_type", ["M8[s]", "m8[s]"])
    def test_minmax_time_dtypes(self, time_type):
        def minmax_with_mask(arr, mask):
            masked_arr = masked_array(arr, mask=mask)
            expected_min = arr[~np.array(mask, dtype=bool)].min()
            expected_max = arr[~np.array(mask, dtype=bool)].max()

            assert_array_equal(masked_arr.min(), expected_min)
            assert_array_equal(masked_arr.max(), expected_max)

        # Additional tests on max/min for time dtypes
        x1 = np.array([1, 1, -2, 4, 5, -10, 10, 1, 2, -2**63 + 1], dtype=time_type)
        x2 = np.array(['NaT', 1, -2, 4, 5, -10, 10, 1, 2, 3], dtype=time_type)
        x3 = np.array(['NaT', 'NaT', -2, 4, 5, -10, 10, 1, 2, 3], dtype=time_type)
        x_test = [x1, x2, x3]
        m = [1, 0, 0, 0, 0, 0, 1, 0, 0, 0]

        for x in x_test:
            minmax_with_mask(x, m)

    def test_addsumprod(self):
        # Tests add, sum, product.
        (x, y, a10, m1, m2, xm, ym, z, zm, xf) = self.d
        assert_equal(np.add.reduce(x), add.reduce(x))
        assert_equal(np.add.accumulate(x), add.accumulate(x))
        assert_equal(4, sum(array(4), axis=0))
        assert_equal(4, sum(array(4), axis=0))
        assert_equal(np.sum(x, axis=0), sum(x, axis=0))
        assert_equal(np.sum(filled(xm, 0), axis=0), sum(xm, axis=0))
        assert_equal(np.sum(x, 0), sum(x, 0))
        assert_equal(np.prod(x, axis=0), product(x, axis=0))
        assert_equal(np.prod(x, 0), product(x, 0))
        assert_equal(np.prod(filled(xm, 1), axis=0), product(xm, axis=0))
        s = (3, 4)
        x.shape = y.shape = xm.shape = ym.shape = s
        if len(s) > 1:
            assert_equal(np.concatenate((x, y), 1), concatenate((xm, ym), 1))
            assert_equal(np.add.reduce(x, 1), add.reduce(x, 1))
            assert_equal(np.sum(x, 1), sum(x, 1))
            assert_equal(np.prod(x, 1), product(x, 1))

    def test_binops_d2D(self):
        # Test binary operations on 2D data
        a = array([[1.], [2.], [3.]], mask=[[False], [True], [True]])
        b = array([[2., 3.], [4., 5.], [6., 7.]])

        test = a * b
        control = array([[2., 3.], [2., 2.], [3., 3.]],
                        mask=[[0, 0], [1, 1], [1, 1]])
        assert_equal(test, control)
        assert_equal(test.data, control.data)
        assert_equal(test.mask, control.mask)

        test = b * a
        control = array([[2., 3.], [4., 5.], [6., 7.]],
                        mask=[[0, 0], [1, 1], [1, 1]])
        assert_equal(test, control)
        assert_equal(test.data, control.data)
        assert_equal(test.mask, control.mask)

        a = array([[1.], [2.], [3.]])
        b = array([[2., 3.], [4., 5.], [6., 7.]],
                  mask=[[0, 0], [0, 0], [0, 1]])
        test = a * b
        control = array([[2, 3], [8, 10], [18, 3]],
                        mask=[[0, 0], [0, 0], [0, 1]])
        assert_equal(test, control)
        assert_equal(test.data, control.data)
        assert_equal(test.mask, control.mask)

        test = b * a
        control = array([[2, 3], [8, 10], [18, 7]],
                        mask=[[0, 0], [0, 0], [0, 1]])
        assert_equal(test, control)
        assert_equal(test.data, control.data)
        assert_equal(test.mask, control.mask)

    def test_domained_binops_d2D(self):
        # Test domained binary operations on 2D data
        a = array([[1.], [2.], [3.]], mask=[[False], [True], [True]])
        b = array([[2., 3.], [4., 5.], [6., 7.]])

        test = a / b
        control = array([[1. / 2., 1. / 3.], [2., 2.], [3., 3.]],
                        mask=[[0, 0], [1, 1], [1, 1]])
        assert_equal(test, control)
        assert_equal(test.data, control.data)
        assert_equal(test.mask, control.mask)

        test = b / a
        control = array([[2. / 1., 3. / 1.], [4., 5.], [6., 7.]],
                        mask=[[0, 0], [1, 1], [1, 1]])
        assert_equal(test, control)
        assert_equal(test.data, control.data)
        assert_equal(test.mask, control.mask)

        a = array([[1.], [2.], [3.]])
        b = array([[2., 3.], [4., 5.], [6., 7.]],
                  mask=[[0, 0], [0, 0], [0, 1]])
        test = a / b
        control = array([[1. / 2, 1. / 3], [2. / 4, 2. / 5], [3. / 6, 3]],
                        mask=[[0, 0], [0, 0], [0, 1]])
        assert_equal(test, control)
        assert_equal(test.data, control.data)
        assert_equal(test.mask, control.mask)

        test = b / a
        control = array([[2 / 1., 3 / 1.], [4 / 2., 5 / 2.], [6 / 3., 7]],
                        mask=[[0, 0], [0, 0], [0, 1]])
        assert_equal(test, control)
        assert_equal(test.data, control.data)
        assert_equal(test.mask, control.mask)

    def test_noshrinking(self):
        # Check that we don't shrink a mask when not wanted
        # Binary operations
        a = masked_array([1., 2., 3.], mask=[False, False, False],
                         shrink=False)
        b = a + 1
        assert_equal(b.mask, [0, 0, 0])
        # In place binary operation
        a += 1
        assert_equal(a.mask, [0, 0, 0])
        # Domained binary operation
        b = a / 1.
        assert_equal(b.mask, [0, 0, 0])
        # In place binary operation
        a /= 1.
        assert_equal(a.mask, [0, 0, 0])

    def test_ufunc_nomask(self):
        # check the case ufuncs should set the mask to false
        m = np.ma.array([1])
        # check we don't get array([False], dtype=bool)
        assert_equal(np.true_divide(m, 5).mask.shape, ())

    def test_noshink_on_creation(self):
        # Check that the mask is not shrunk on array creation when not wanted
        a = np.ma.masked_values([1., 2.5, 3.1], 1.5, shrink=False)
        assert_equal(a.mask, [0, 0, 0])

    def test_mod(self):
        # Tests mod
        (x, y, a10, m1, m2, xm, ym, z, zm, xf) = self.d
        assert_equal(mod(x, y), mod(xm, ym))
        test = mod(ym, xm)
        assert_equal(test, np.mod(ym, xm))
        assert_equal(test.mask, mask_or(xm.mask, ym.mask))
        test = mod(xm, ym)
        assert_equal(test, np.mod(xm, ym))
        assert_equal(test.mask, mask_or(mask_or(xm.mask, ym.mask), (ym == 0)))

    def test_TakeTransposeInnerOuter(self):
        # Test of take, transpose, inner, outer products
        x = arange(24)
        y = np.arange(24)
        x[5:6] = masked
        x = x.reshape(2, 3, 4)
        y = y.reshape(2, 3, 4)
        assert_equal(np.transpose(y, (2, 0, 1)), transpose(x, (2, 0, 1)))
        assert_equal(np.take(y, (2, 0, 1), 1), take(x, (2, 0, 1), 1))
        assert_equal(np.inner(filled(x, 0), filled(y, 0)),
                     inner(x, y))
        assert_equal(np.outer(filled(x, 0), filled(y, 0)),
                     outer(x, y))
        y = array(['abc', 1, 'def', 2, 3], object)
        y[2] = masked
        t = take(y, [0, 3, 4])
        assert_(t[0] == 'abc')
        assert_(t[1] == 2)
        assert_(t[2] == 3)

    def test_imag_real(self):
        # Check complex
        xx = array([1 + 10j, 20 + 2j], mask=[1, 0])
        assert_equal(xx.imag, [10, 2])
        assert_equal(xx.imag.filled(), [1e+20, 2])
        assert_equal(xx.imag.dtype, xx._data.imag.dtype)
        assert_equal(xx.real, [1, 20])
        assert_equal(xx.real.filled(), [1e+20, 20])
        assert_equal(xx.real.dtype, xx._data.real.dtype)

    def test_methods_with_output(self):
        xm = array(np.random.uniform(0, 10, 12)).reshape(3, 4)
        xm[:, 0] = xm[0] = xm[-1, -1] = masked

        funclist = ('sum', 'prod', 'var', 'std', 'max', 'min', 'ptp', 'mean',)

        for funcname in funclist:
            npfunc = getattr(np, funcname)
            xmmeth = getattr(xm, funcname)
            # A ndarray as explicit input
            output = np.empty(4, dtype=float)
            output.fill(-9999)
            result = npfunc(xm, axis=0, out=output)
            # ... the result should be the given output
            assert_(result is output)
            assert_equal(result, xmmeth(axis=0, out=output))

            output = empty(4, dtype=int)
            result = xmmeth(axis=0, out=output)
            assert_(result is output)
            assert_(output[0] is masked)

    def test_eq_on_structured(self):
        # Test the equality of structured arrays
        ndtype = [('A', int), ('B', int)]
        a = array([(1, 1), (2, 2)], mask=[(0, 1), (0, 0)], dtype=ndtype)

        test = (a == a)
        assert_equal(test.data, [True, True])
        assert_equal(test.mask, [False, False])
        assert_(test.fill_value == True)

        test = (a == a[0])
        assert_equal(test.data, [True, False])
        assert_equal(test.mask, [False, False])
        assert_(test.fill_value == True)

        b = array([(1, 1), (2, 2)], mask=[(1, 0), (0, 0)], dtype=ndtype)
        test = (a == b)
        assert_equal(test.data, [False, True])
        assert_equal(test.mask, [True, False])
        assert_(test.fill_value == True)

        test = (a[0] == b)
        assert_equal(test.data, [False, False])
        assert_equal(test.mask, [True, False])
        assert_(test.fill_value == True)

        b = array([(1, 1), (2, 2)], mask=[(0, 1), (1, 0)], dtype=ndtype)
        test = (a == b)
        assert_equal(test.data, [True, True])
        assert_equal(test.mask, [False, False])
        assert_(test.fill_value == True)

        # complicated dtype, 2-dimensional array.
        ndtype = [('A', int), ('B', [('BA', int), ('BB', int)])]
        a = array([[(1, (1, 1)), (2, (2, 2))],
                   [(3, (3, 3)), (4, (4, 4))]],
                  mask=[[(0, (1, 0)), (0, (0, 1))],
                        [(1, (0, 0)), (1, (1, 1))]], dtype=ndtype)
        test = (a[0, 0] == a)
        assert_equal(test.data, [[True, False], [False, False]])
        assert_equal(test.mask, [[False, False], [False, True]])
        assert_(test.fill_value == True)

    def test_ne_on_structured(self):
        # Test the equality of structured arrays
        ndtype = [('A', int), ('B', int)]
        a = array([(1, 1), (2, 2)], mask=[(0, 1), (0, 0)], dtype=ndtype)

        test = (a != a)
        assert_equal(test.data, [False, False])
        assert_equal(test.mask, [False, False])
        assert_(test.fill_value == True)

        test = (a != a[0])
        assert_equal(test.data, [False, True])
        assert_equal(test.mask, [False, False])
        assert_(test.fill_value == True)

        b = array([(1, 1), (2, 2)], mask=[(1, 0), (0, 0)], dtype=ndtype)
        test = (a != b)
        assert_equal(test.data, [True, False])
        assert_equal(test.mask, [True, False])
        assert_(test.fill_value == True)

        test = (a[0] != b)
        assert_equal(test.data, [True, True])
        assert_equal(test.mask, [True, False])
        assert_(test.fill_value == True)

        b = array([(1, 1), (2, 2)], mask=[(0, 1), (1, 0)], dtype=ndtype)
        test = (a != b)
        assert_equal(test.data, [False, False])
        assert_equal(test.mask, [False, False])
        assert_(test.fill_value == True)

        # complicated dtype, 2-dimensional array.
        ndtype = [('A', int), ('B', [('BA', int), ('BB', int)])]
        a = array([[(1, (1, 1)), (2, (2, 2))],
                   [(3, (3, 3)), (4, (4, 4))]],
                  mask=[[(0, (1, 0)), (0, (0, 1))],
                        [(1, (0, 0)), (1, (1, 1))]], dtype=ndtype)
        test = (a[0, 0] != a)
        assert_equal(test.data, [[False, True], [True, True]])
        assert_equal(test.mask, [[False, False], [False, True]])
        assert_(test.fill_value == True)

    def test_eq_ne_structured_with_non_masked(self):
        a = array([(1, 1), (2, 2), (3, 4)],
                  mask=[(0, 1), (0, 0), (1, 1)], dtype='i4,i4')
        eq = a == a.data
        ne = a.data != a
        # Test the obvious.
        assert_(np.all(eq))
        assert_(not np.any(ne))
        # Expect the mask set only for items with all fields masked.
        expected_mask = a.mask == np.ones((), a.mask.dtype)
        assert_array_equal(eq.mask, expected_mask)
        assert_array_equal(ne.mask, expected_mask)
        # The masked element will indicated not equal, because the
        # masks did not match.
        assert_equal(eq.data, [True, True, False])
        assert_array_equal(eq.data, ~ne.data)

    def test_eq_ne_structured_extra(self):
        # ensure simple examples are symmetric and make sense.
        # from https://github.com/numpy/numpy/pull/8590#discussion_r101126465
        dt = np.dtype('i4,i4')
        for m1 in (mvoid((1, 2), mask=(0, 0), dtype=dt),
                   mvoid((1, 2), mask=(0, 1), dtype=dt),
                   mvoid((1, 2), mask=(1, 0), dtype=dt),
                   mvoid((1, 2), mask=(1, 1), dtype=dt)):
            ma1 = m1.view(MaskedArray)
            r1 = ma1.view('2i4')
            for m2 in (np.array((1, 1), dtype=dt),
                       mvoid((1, 1), dtype=dt),
                       mvoid((1, 0), mask=(0, 1), dtype=dt),
                       mvoid((3, 2), mask=(0, 1), dtype=dt)):
                ma2 = m2.view(MaskedArray)
                r2 = ma2.view('2i4')
                eq_expected = (r1 == r2).all()
                assert_equal(m1 == m2, eq_expected)
                assert_equal(m2 == m1, eq_expected)
                assert_equal(ma1 == m2, eq_expected)
                assert_equal(m1 == ma2, eq_expected)
                assert_equal(ma1 == ma2, eq_expected)
                # Also check it is the same if we do it element by element.
                el_by_el = [m1[name] == m2[name] for name in dt.names]
                assert_equal(array(el_by_el, dtype=bool).all(), eq_expected)
                ne_expected = (r1 != r2).any()
                assert_equal(m1 != m2, ne_expected)
                assert_equal(m2 != m1, ne_expected)
                assert_equal(ma1 != m2, ne_expected)
                assert_equal(m1 != ma2, ne_expected)
                assert_equal(ma1 != ma2, ne_expected)
                el_by_el = [m1[name] != m2[name] for name in dt.names]
                assert_equal(array(el_by_el, dtype=bool).any(), ne_expected)

    @pytest.mark.parametrize('dt', ['S', 'U'])
    @pytest.mark.parametrize('fill', [None, 'A'])
    def test_eq_for_strings(self, dt, fill):
        # Test the equality of structured arrays
        a = array(['a', 'b'], dtype=dt, mask=[0, 1], fill_value=fill)

        test = (a == a)
        assert_equal(test.data, [True, True])
        assert_equal(test.mask, [False, True])
        assert_(test.fill_value == True)

        test = (a == a[0])
        assert_equal(test.data, [True, False])
        assert_equal(test.mask, [False, True])
        assert_(test.fill_value == True)

        b = array(['a', 'b'], dtype=dt, mask=[1, 0], fill_value=fill)
        test = (a == b)
        assert_equal(test.data, [False, False])
        assert_equal(test.mask, [True, True])
        assert_(test.fill_value == True)

        test = (a[0] == b)
        assert_equal(test.data, [False, False])
        assert_equal(test.mask, [True, False])
        assert_(test.fill_value == True)

        test = (b == a[0])
        assert_equal(test.data, [False, False])
        assert_equal(test.mask, [True, False])
        assert_(test.fill_value == True)

    @pytest.mark.parametrize('dt', ['S', 'U'])
    @pytest.mark.parametrize('fill', [None, 'A'])
    def test_ne_for_strings(self, dt, fill):
        # Test the equality of structured arrays
        a = array(['a', 'b'], dtype=dt, mask=[0, 1], fill_value=fill)

        test = (a != a)
        assert_equal(test.data, [False, False])
        assert_equal(test.mask, [False, True])
        assert_(test.fill_value == True)

        test = (a != a[0])
        assert_equal(test.data, [False, True])
        assert_equal(test.mask, [False, True])
        assert_(test.fill_value == True)

        b = array(['a', 'b'], dtype=dt, mask=[1, 0], fill_value=fill)
        test = (a != b)
        assert_equal(test.data, [True, True])
        assert_equal(test.mask, [True, True])
        assert_(test.fill_value == True)

        test = (a[0] != b)
        assert_equal(test.data, [True, True])
        assert_equal(test.mask, [True, False])
        assert_(test.fill_value == True)

        test = (b != a[0])
        assert_equal(test.data, [True, True])
        assert_equal(test.mask, [True, False])
        assert_(test.fill_value == True)

    @pytest.mark.parametrize('dt1', num_dts, ids=num_ids)
    @pytest.mark.parametrize('dt2', num_dts, ids=num_ids)
    @pytest.mark.parametrize('fill', [None, 1])
    def test_eq_for_numeric(self, dt1, dt2, fill):
        # Test the equality of structured arrays
        a = array([0, 1], dtype=dt1, mask=[0, 1], fill_value=fill)

        test = (a == a)
        assert_equal(test.data, [True, True])
        assert_equal(test.mask, [False, True])
        assert_(test.fill_value == True)

        test = (a == a[0])
        assert_equal(test.data, [True, False])
        assert_equal(test.mask, [False, True])
        assert_(test.fill_value == True)

        b = array([0, 1], dtype=dt2, mask=[1, 0], fill_value=fill)
        test = (a == b)
        assert_equal(test.data, [False, False])
        assert_equal(test.mask, [True, True])
        assert_(test.fill_value == True)

        test = (a[0] == b)
        assert_equal(test.data, [False, False])
        assert_equal(test.mask, [True, False])
        assert_(test.fill_value == True)

        test = (b == a[0])
        assert_equal(test.data, [False, False])
        assert_equal(test.mask, [True, False])
        assert_(test.fill_value == True)

    @pytest.mark.parametrize("op", [operator.eq, operator.lt])
    def test_eq_broadcast_with_unmasked(self, op):
        a = array([0, 1], mask=[0, 1])
        b = np.arange(10).reshape(5, 2)
        result = op(a, b)
        assert_(result.mask.shape == b.shape)
        assert_equal(result.mask, np.zeros(b.shape, bool) | a.mask)

    @pytest.mark.parametrize("op", [operator.eq, operator.gt])
    def test_comp_no_mask_not_broadcast(self, op):
        # Regression test for failing doctest in MaskedArray.nonzero
        # after gh-24556.
        a = array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
        result = op(a, 3)
        assert_(not result.mask.shape)
        assert_(result.mask is nomask)

    @pytest.mark.parametrize('dt1', num_dts, ids=num_ids)
    @pytest.mark.parametrize('dt2', num_dts, ids=num_ids)
    @pytest.mark.parametrize('fill', [None, 1])
    def test_ne_for_numeric(self, dt1, dt2, fill):
        # Test the equality of structured arrays
        a = array([0, 1], dtype=dt1, mask=[0, 1], fill_value=fill)

        test = (a != a)
        assert_equal(test.data, [False, False])
        assert_equal(test.mask, [False, True])
        assert_(test.fill_value == True)

        test = (a != a[0])
        assert_equal(test.data, [False, True])
        assert_equal(test.mask, [False, True])
        assert_(test.fill_value == True)

        b = array([0, 1], dtype=dt2, mask=[1, 0], fill_value=fill)
        test = (a != b)
        assert_equal(test.data, [True, True])
        assert_equal(test.mask, [True, True])
        assert_(test.fill_value == True)

        test = (a[0] != b)
        assert_equal(test.data, [True, True])
        assert_equal(test.mask, [True, False])
        assert_(test.fill_value == True)

        test = (b != a[0])
        assert_equal(test.data, [True, True])
        assert_equal(test.mask, [True, False])
        assert_(test.fill_value == True)

    @pytest.mark.parametrize('dt1', num_dts, ids=num_ids)
    @pytest.mark.parametrize('dt2', num_dts, ids=num_ids)
    @pytest.mark.parametrize('fill', [None, 1])
    @pytest.mark.parametrize('op',
            [operator.le, operator.lt, operator.ge, operator.gt])
    def test_comparisons_for_numeric(self, op, dt1, dt2, fill):
        # Test the equality of structured arrays
        a = array([0, 1], dtype=dt1, mask=[0, 1], fill_value=fill)

        test = op(a, a)
        assert_equal(test.data, op(a._data, a._data))
        assert_equal(test.mask, [False, True])
        assert_(test.fill_value == True)

        test = op(a, a[0])
        assert_equal(test.data, op(a._data, a._data[0]))
        assert_equal(test.mask, [False, True])
        assert_(test.fill_value == True)

        b = array([0, 1], dtype=dt2, mask=[1, 0], fill_value=fill)
        test = op(a, b)
        assert_equal(test.data, op(a._data, b._data))
        assert_equal(test.mask, [True, True])
        assert_(test.fill_value == True)

        test = op(a[0], b)
        assert_equal(test.data, op(a._data[0], b._data))
        assert_equal(test.mask, [True, False])
        assert_(test.fill_value == True)

        test = op(b, a[0])
        assert_equal(test.data, op(b._data, a._data[0]))
        assert_equal(test.mask, [True, False])
        assert_(test.fill_value == True)

    @pytest.mark.parametrize('op',
            [operator.le, operator.lt, operator.ge, operator.gt])
    @pytest.mark.parametrize('fill', [None, "N/A"])
    def test_comparisons_strings(self, op, fill):
        # See gh-21770, mask propagation is broken for strings (and some other
        # cases) so we explicitly test strings here.
        # In principle only == and != may need special handling...
        ma1 = masked_array(["a", "b", "cde"], mask=[0, 1, 0], fill_value=fill)
        ma2 = masked_array(["cde", "b", "a"], mask=[0, 1, 0], fill_value=fill)
        assert_equal(op(ma1, ma2)._data, op(ma1._data, ma2._data))

    def test_eq_with_None(self):
        # Really, comparisons with None should not be done, but check them
        # anyway. Note that pep8 will flag these tests.
        # Deprecation is in place for arrays, and when it happens this
        # test will fail (and have to be changed accordingly).

        # With partial mask
        with suppress_warnings() as sup:
            sup.filter(FutureWarning, "Comparison to `None`")
            a = array([None, 1], mask=[0, 1])
            assert_equal(a == None, array([True, False], mask=[0, 1]))  # noqa: E711
            assert_equal(a.data == None, [True, False])  # noqa: E711
            assert_equal(a != None, array([False, True], mask=[0, 1]))  # noqa: E711
            # With nomask
            a = array([None, 1], mask=False)
            assert_equal(a == None, [True, False])  # noqa: E711
            assert_equal(a != None, [False, True])  # noqa: E711
            # With complete mask
            a = array([None, 2], mask=True)
            assert_equal(a == None, array([False, True], mask=True))  # noqa: E711
            assert_equal(a != None, array([True, False], mask=True))  # noqa: E711
            # Fully masked, even comparison to None should return "masked"
            a = masked
            assert_equal(a == None, masked)  # noqa: E711

    def test_eq_with_scalar(self):
        a = array(1)
        assert_equal(a == 1, True)
        assert_equal(a == 0, False)
        assert_equal(a != 1, False)
        assert_equal(a != 0, True)
        b = array(1, mask=True)
        assert_equal(b == 0, masked)
        assert_equal(b == 1, masked)
        assert_equal(b != 0, masked)
        assert_equal(b != 1, masked)

    def test_eq_different_dimensions(self):
        m1 = array([1, 1], mask=[0, 1])
        # test comparison with both masked and regular arrays.
        for m2 in (array([[0, 1], [1, 2]]),
                   np.array([[0, 1], [1, 2]])):
            test = (m1 == m2)
            assert_equal(test.data, [[False, False],
                                     [True, False]])
            assert_equal(test.mask, [[False, True],
                                     [False, True]])

    def test_numpyarithmetic(self):
        # Check that the mask is not back-propagated when using numpy functions
        a = masked_array([-1, 0, 1, 2, 3], mask=[0, 0, 0, 0, 1])
        control = masked_array([np.nan, np.nan, 0, np.log(2), -1],
                               mask=[1, 1, 0, 0, 1])

        test = log(a)
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)
        assert_equal(a.mask, [0, 0, 0, 0, 1])

        test = np.log(a)
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)
        assert_equal(a.mask, [0, 0, 0, 0, 1])


class TestMaskedArrayAttributes:

    def test_keepmask(self):
        # Tests the keep mask flag
        x = masked_array([1, 2, 3], mask=[1, 0, 0])
        mx = masked_array(x)
        assert_equal(mx.mask, x.mask)
        mx = masked_array(x, mask=[0, 1, 0], keep_mask=False)
        assert_equal(mx.mask, [0, 1, 0])
        mx = masked_array(x, mask=[0, 1, 0], keep_mask=True)
        assert_equal(mx.mask, [1, 1, 0])
        # We default to true
        mx = masked_array(x, mask=[0, 1, 0])
        assert_equal(mx.mask, [1, 1, 0])

    def test_hardmask(self):
        # Test hard_mask
        d = arange(5)
        n = [0, 0, 0, 1, 1]
        m = make_mask(n)
        xh = array(d, mask=m, hard_mask=True)
        # We need to copy, to avoid updating d in xh !
        xs = array(d, mask=m, hard_mask=False, copy=True)
        xh[[1, 4]] = [10, 40]
        xs[[1, 4]] = [10, 40]
        assert_equal(xh._data, [0, 10, 2, 3, 4])
        assert_equal(xs._data, [0, 10, 2, 3, 40])
        assert_equal(xs.mask, [0, 0, 0, 1, 0])
        assert_(xh._hardmask)
        assert_(not xs._hardmask)
        xh[1:4] = [10, 20, 30]
        xs[1:4] = [10, 20, 30]
        assert_equal(xh._data, [0, 10, 20, 3, 4])
        assert_equal(xs._data, [0, 10, 20, 30, 40])
        assert_equal(xs.mask, nomask)
        xh[0] = masked
        xs[0] = masked
        assert_equal(xh.mask, [1, 0, 0, 1, 1])
        assert_equal(xs.mask, [1, 0, 0, 0, 0])
        xh[:] = 1
        xs[:] = 1
        assert_equal(xh._data, [0, 1, 1, 3, 4])
        assert_equal(xs._data, [1, 1, 1, 1, 1])
        assert_equal(xh.mask, [1, 0, 0, 1, 1])
        assert_equal(xs.mask, nomask)
        # Switch to soft mask
        xh.soften_mask()
        xh[:] = arange(5)
        assert_equal(xh._data, [0, 1, 2, 3, 4])
        assert_equal(xh.mask, nomask)
        # Switch back to hard mask
        xh.harden_mask()
        xh[xh < 3] = masked
        assert_equal(xh._data, [0, 1, 2, 3, 4])
        assert_equal(xh._mask, [1, 1, 1, 0, 0])
        xh[filled(xh > 1, False)] = 5
        assert_equal(xh._data, [0, 1, 2, 5, 5])
        assert_equal(xh._mask, [1, 1, 1, 0, 0])

        xh = array([[1, 2], [3, 4]], mask=[[1, 0], [0, 0]], hard_mask=True)
        xh[0] = 0
        assert_equal(xh._data, [[1, 0], [3, 4]])
        assert_equal(xh._mask, [[1, 0], [0, 0]])
        xh[-1, -1] = 5
        assert_equal(xh._data, [[1, 0], [3, 5]])
        assert_equal(xh._mask, [[1, 0], [0, 0]])
        xh[filled(xh < 5, False)] = 2
        assert_equal(xh._data, [[1, 2], [2, 5]])
        assert_equal(xh._mask, [[1, 0], [0, 0]])

    def test_hardmask_again(self):
        # Another test of hardmask
        d = arange(5)
        n = [0, 0, 0, 1, 1]
        m = make_mask(n)
        xh = array(d, mask=m, hard_mask=True)
        xh[4:5] = 999
        xh[0:1] = 999
        assert_equal(xh._data, [999, 1, 2, 3, 4])

    def test_hardmask_oncemore_yay(self):
        # OK, yet another test of hardmask
        # Make sure that harden_mask/soften_mask//unshare_mask returns self
        a = array([1, 2, 3], mask=[1, 0, 0])
        b = a.harden_mask()
        assert_equal(a, b)
        b[0] = 0
        assert_equal(a, b)
        assert_equal(b, array([1, 2, 3], mask=[1, 0, 0]))
        a = b.soften_mask()
        a[0] = 0
        assert_equal(a, b)
        assert_equal(b, array([0, 2, 3], mask=[0, 0, 0]))

    def test_smallmask(self):
        # Checks the behaviour of _smallmask
        a = arange(10)
        a[1] = masked
        a[1] = 1
        assert_equal(a._mask, nomask)
        a = arange(10)
        a._smallmask = False
        a[1] = masked
        a[1] = 1
        assert_equal(a._mask, zeros(10))

    def test_shrink_mask(self):
        # Tests .shrink_mask()
        a = array([1, 2, 3], mask=[0, 0, 0])
        b = a.shrink_mask()
        assert_equal(a, b)
        assert_equal(a.mask, nomask)

        # Mask cannot be shrunk on structured types, so is a no-op
        a = np.ma.array([(1, 2.0)], [('a', int), ('b', float)])
        b = a.copy()
        a.shrink_mask()
        assert_equal(a.mask, b.mask)

    def test_flat(self):
        # Test that flat can return all types of items [#4585, #4615]
        # test 2-D record array
        # ... on structured array w/ masked records
        x = array([[(1, 1.1, 'one'), (2, 2.2, 'two'), (3, 3.3, 'thr')],
                   [(4, 4.4, 'fou'), (5, 5.5, 'fiv'), (6, 6.6, 'six')]],
                  dtype=[('a', int), ('b', float), ('c', '|S8')])
        x['a'][0, 1] = masked
        x['b'][1, 0] = masked
        x['c'][0, 2] = masked
        x[-1, -1] = masked
        xflat = x.flat
        assert_equal(xflat[0], x[0, 0])
        assert_equal(xflat[1], x[0, 1])
        assert_equal(xflat[2], x[0, 2])
        assert_equal(xflat[:3], x[0])
        assert_equal(xflat[3], x[1, 0])
        assert_equal(xflat[4], x[1, 1])
        assert_equal(xflat[5], x[1, 2])
        assert_equal(xflat[3:], x[1])
        assert_equal(xflat[-1], x[-1, -1])
        i = 0
        j = 0
        for xf in xflat:
            assert_equal(xf, x[j, i])
            i += 1
            if i >= x.shape[-1]:
                i = 0
                j += 1

    def test_assign_dtype(self):
        # check that the mask's dtype is updated when dtype is changed
        a = np.zeros(4, dtype='f4,i4')

        m = np.ma.array(a)
        m.dtype = np.dtype('f4')
        repr(m)  # raises?
        assert_equal(m.dtype, np.dtype('f4'))

        # check that dtype changes that change shape of mask too much
        # are not allowed
        def assign():
            m = np.ma.array(a)
            m.dtype = np.dtype('f8')
        assert_raises(ValueError, assign)

        b = a.view(dtype='f4', type=np.ma.MaskedArray)  # raises?
        assert_equal(b.dtype, np.dtype('f4'))

        # check that nomask is preserved
        a = np.zeros(4, dtype='f4')
        m = np.ma.array(a)
        m.dtype = np.dtype('f4,i4')
        assert_equal(m.dtype, np.dtype('f4,i4'))
        assert_equal(m._mask, np.ma.nomask)


class TestFillingValues:

    def test_check_on_scalar(self):
        # Test _check_fill_value set to valid and invalid values
        _check_fill_value = np.ma.core._check_fill_value

        fval = _check_fill_value(0, int)
        assert_equal(fval, 0)
        fval = _check_fill_value(None, int)
        assert_equal(fval, default_fill_value(0))

        fval = _check_fill_value(0, "|S3")
        assert_equal(fval, b"0")
        fval = _check_fill_value(None, "|S3")
        assert_equal(fval, default_fill_value(b"camelot!"))
        assert_raises(TypeError, _check_fill_value, 1e+20, int)
        assert_raises(TypeError, _check_fill_value, 'stuff', int)

    def test_check_on_fields(self):
        # Tests _check_fill_value with records
        _check_fill_value = np.ma.core._check_fill_value
        ndtype = [('a', int), ('b', float), ('c', "|S3")]
        # A check on a list should return a single record
        fval = _check_fill_value([-999, -12345678.9, "???"], ndtype)
        assert_(isinstance(fval, ndarray))
        assert_equal(fval.item(), [-999, -12345678.9, b"???"])
        # A check on None should output the defaults
        fval = _check_fill_value(None, ndtype)
        assert_(isinstance(fval, ndarray))
        assert_equal(fval.item(), [default_fill_value(0),
                                   default_fill_value(0.),
                                   asbytes(default_fill_value("0"))])
        #.....Using a structured type as fill_value should work
        fill_val = np.array((-999, -12345678.9, "???"), dtype=ndtype)
        fval = _check_fill_value(fill_val, ndtype)
        assert_(isinstance(fval, ndarray))
        assert_equal(fval.item(), [-999, -12345678.9, b"???"])

        #.....Using a flexible type w/ a different type shouldn't matter
        # BEHAVIOR in 1.5 and earlier, and 1.13 and later: match structured
        # types by position
        fill_val = np.array((-999, -12345678.9, "???"),
                            dtype=[("A", int), ("B", float), ("C", "|S3")])
        fval = _check_fill_value(fill_val, ndtype)
        assert_(isinstance(fval, ndarray))
        assert_equal(fval.item(), [-999, -12345678.9, b"???"])

        #.....Using an object-array shouldn't matter either
        fill_val = np.ndarray(shape=(1,), dtype=object)
        fill_val[0] = (-999, -12345678.9, b"???")
        fval = _check_fill_value(fill_val, object)
        assert_(isinstance(fval, ndarray))
        assert_equal(fval.item(), [-999, -12345678.9, b"???"])
        # NOTE: This test was never run properly as "fill_value" rather than
        # "fill_val" was assigned.  Written properly, it fails.
        #fill_val = np.array((-999, -12345678.9, "???"))
        #fval = _check_fill_value(fill_val, ndtype)
        #assert_(isinstance(fval, ndarray))
        #assert_equal(fval.item(), [-999, -12345678.9, b"???"])
        #.....One-field-only flexible type should work as well
        ndtype = [("a", int)]
        fval = _check_fill_value(-999999999, ndtype)
        assert_(isinstance(fval, ndarray))
        assert_equal(fval.item(), (-999999999,))

    def test_fillvalue_conversion(self):
        # Tests the behavior of fill_value during conversion
        # We had a tailored comment to make sure special attributes are
        # properly dealt with
        a = array([b'3', b'4', b'5'])
        a._optinfo.update({'comment': "updated!"})

        b = array(a, dtype=int)
        assert_equal(b._data, [3, 4, 5])
        assert_equal(b.fill_value, default_fill_value(0))

        b = array(a, dtype=float)
        assert_equal(b._data, [3, 4, 5])
        assert_equal(b.fill_value, default_fill_value(0.))

        b = a.astype(int)
        assert_equal(b._data, [3, 4, 5])
        assert_equal(b.fill_value, default_fill_value(0))
        assert_equal(b._optinfo['comment'], "updated!")

        b = a.astype([('a', '|S3')])
        assert_equal(b['a']._data, a._data)
        assert_equal(b['a'].fill_value, a.fill_value)

    def test_default_fill_value(self):
        # check all calling conventions
        f1 = default_fill_value(1.)
        f2 = default_fill_value(np.array(1.))
        f3 = default_fill_value(np.array(1.).dtype)
        assert_equal(f1, f2)
        assert_equal(f1, f3)

    def test_default_fill_value_structured(self):
        fields = array([(1, 1, 1)],
                      dtype=[('i', int), ('s', '|S8'), ('f', float)])

        f1 = default_fill_value(fields)
        f2 = default_fill_value(fields.dtype)
        expected = np.array((default_fill_value(0),
                             default_fill_value('0'),
                             default_fill_value(0.)), dtype=fields.dtype)
        assert_equal(f1, expected)
        assert_equal(f2, expected)

    def test_default_fill_value_void(self):
        dt = np.dtype([('v', 'V7')])
        f = default_fill_value(dt)
        assert_equal(f['v'], np.array(default_fill_value(dt['v']), dt['v']))

    def test_fillvalue(self):
        # Yet more fun with the fill_value
        data = masked_array([1, 2, 3], fill_value=-999)
        series = data[[0, 2, 1]]
        assert_equal(series._fill_value, data._fill_value)

        mtype = [('f', float), ('s', '|S3')]
        x = array([(1, 'a'), (2, 'b'), (pi, 'pi')], dtype=mtype)
        x.fill_value = 999
        assert_equal(x.fill_value.item(), [999., b'999'])
        assert_equal(x['f'].fill_value, 999)
        assert_equal(x['s'].fill_value, b'999')

        x.fill_value = (9, '???')
        assert_equal(x.fill_value.item(), (9, b'???'))
        assert_equal(x['f'].fill_value, 9)
        assert_equal(x['s'].fill_value, b'???')

        x = array([1, 2, 3.1])
        x.fill_value = 999
        assert_equal(np.asarray(x.fill_value).dtype, float)
        assert_equal(x.fill_value, 999.)
        assert_equal(x._fill_value, np.array(999.))

    def test_subarray_fillvalue(self):
        # gh-10483   test multi-field index fill value
        fields = array([(1, 1, 1)],
                      dtype=[('i', int), ('s', '|S8'), ('f', float)])
        with suppress_warnings() as sup:
            sup.filter(FutureWarning, "Numpy has detected")
            subfields = fields[['i', 'f']]
            assert_equal(tuple(subfields.fill_value), (999999, 1.e+20))
            # test comparison does not raise:
            subfields[1:] == subfields[:-1]

    def test_fillvalue_exotic_dtype(self):
        # Tests yet more exotic flexible dtypes
        _check_fill_value = np.ma.core._check_fill_value
        ndtype = [('i', int), ('s', '|S8'), ('f', float)]
        control = np.array((default_fill_value(0),
                            default_fill_value('0'),
                            default_fill_value(0.),),
                           dtype=ndtype)
        assert_equal(_check_fill_value(None, ndtype), control)
        # The shape shouldn't matter
        ndtype = [('f0', float, (2, 2))]
        control = np.array((default_fill_value(0.),),
                           dtype=[('f0', float)]).astype(ndtype)
        assert_equal(_check_fill_value(None, ndtype), control)
        control = np.array((0,), dtype=[('f0', float)]).astype(ndtype)
        assert_equal(_check_fill_value(0, ndtype), control)

        ndtype = np.dtype("int, (2,3)float, float")
        control = np.array((default_fill_value(0),
                            default_fill_value(0.),
                            default_fill_value(0.),),
                           dtype="int, float, float").astype(ndtype)
        test = _check_fill_value(None, ndtype)
        assert_equal(test, control)
        control = np.array((0, 0, 0), dtype="int, float, float").astype(ndtype)
        assert_equal(_check_fill_value(0, ndtype), control)
        # but when indexing, fill value should become scalar not tuple
        # See issue #6723
        M = masked_array(control)
        assert_equal(M["f1"].fill_value.ndim, 0)

    def test_fillvalue_datetime_timedelta(self):
        # Test default fillvalue for datetime64 and timedelta64 types.
        # See issue #4476, this would return '?' which would cause errors
        # elsewhere

        for timecode in ("as", "fs", "ps", "ns", "us", "ms", "s", "m",
                         "h", "D", "W", "M", "Y"):
            control = numpy.datetime64("NaT", timecode)
            test = default_fill_value(numpy.dtype("<M8[" + timecode + "]"))
            np.testing.assert_equal(test, control)

            control = numpy.timedelta64("NaT", timecode)
            test = default_fill_value(numpy.dtype("<m8[" + timecode + "]"))
            np.testing.assert_equal(test, control)

    def test_extremum_fill_value(self):
        # Tests extremum fill values for flexible type.
        a = array([(1, (2, 3)), (4, (5, 6))],
                  dtype=[('A', int), ('B', [('BA', int), ('BB', int)])])
        test = a.fill_value
        assert_equal(test.dtype, a.dtype)
        assert_equal(test['A'], default_fill_value(a['A']))
        assert_equal(test['B']['BA'], default_fill_value(a['B']['BA']))
        assert_equal(test['B']['BB'], default_fill_value(a['B']['BB']))

        test = minimum_fill_value(a)
        assert_equal(test.dtype, a.dtype)
        assert_equal(test[0], minimum_fill_value(a['A']))
        assert_equal(test[1][0], minimum_fill_value(a['B']['BA']))
        assert_equal(test[1][1], minimum_fill_value(a['B']['BB']))
        assert_equal(test[1], minimum_fill_value(a['B']))

        test = maximum_fill_value(a)
        assert_equal(test.dtype, a.dtype)
        assert_equal(test[0], maximum_fill_value(a['A']))
        assert_equal(test[1][0], maximum_fill_value(a['B']['BA']))
        assert_equal(test[1][1], maximum_fill_value(a['B']['BB']))
        assert_equal(test[1], maximum_fill_value(a['B']))

    def test_extremum_fill_value_subdtype(self):
        a = array(([2, 3, 4],), dtype=[('value', np.int8, 3)])

        test = minimum_fill_value(a)
        assert_equal(test.dtype, a.dtype)
        assert_equal(test[0], np.full(3, minimum_fill_value(a['value'])))

        test = maximum_fill_value(a)
        assert_equal(test.dtype, a.dtype)
        assert_equal(test[0], np.full(3, maximum_fill_value(a['value'])))

    def test_fillvalue_individual_fields(self):
        # Test setting fill_value on individual fields
        ndtype = [('a', int), ('b', int)]
        # Explicit fill_value
        a = array(list(zip([1, 2, 3], [4, 5, 6])),
                  fill_value=(-999, -999), dtype=ndtype)
        aa = a['a']
        aa.set_fill_value(10)
        assert_equal(aa._fill_value, np.array(10))
        assert_equal(tuple(a.fill_value), (10, -999))
        a.fill_value['b'] = -10
        assert_equal(tuple(a.fill_value), (10, -10))
        # Implicit fill_value
        t = array(list(zip([1, 2, 3], [4, 5, 6])), dtype=ndtype)
        tt = t['a']
        tt.set_fill_value(10)
        assert_equal(tt._fill_value, np.array(10))
        assert_equal(tuple(t.fill_value), (10, default_fill_value(0)))

    def test_fillvalue_implicit_structured_array(self):
        # Check that fill_value is always defined for structured arrays
        ndtype = ('b', float)
        adtype = ('a', float)
        a = array([(1.,), (2.,)], mask=[(False,), (False,)],
                  fill_value=(np.nan,), dtype=np.dtype([adtype]))
        b = empty(a.shape, dtype=[adtype, ndtype])
        b['a'] = a['a']
        b['a'].set_fill_value(a['a'].fill_value)
        f = b._fill_value[()]
        assert_(np.isnan(f[0]))
        assert_equal(f[-1], default_fill_value(1.))

    def test_fillvalue_as_arguments(self):
        # Test adding a fill_value parameter to empty/ones/zeros
        a = empty(3, fill_value=999.)
        assert_equal(a.fill_value, 999.)

        a = ones(3, fill_value=999., dtype=float)
        assert_equal(a.fill_value, 999.)

        a = zeros(3, fill_value=0., dtype=complex)
        assert_equal(a.fill_value, 0.)

        a = identity(3, fill_value=0., dtype=complex)
        assert_equal(a.fill_value, 0.)

    def test_shape_argument(self):
        # Test that shape can be provides as an argument
        # GH issue 6106
        a = empty(shape=(3, ))
        assert_equal(a.shape, (3, ))

        a = ones(shape=(3, ), dtype=float)
        assert_equal(a.shape, (3, ))

        a = zeros(shape=(3, ), dtype=complex)
        assert_equal(a.shape, (3, ))

    def test_fillvalue_in_view(self):
        # Test the behavior of fill_value in view

        # Create initial masked array
        x = array([1, 2, 3], fill_value=1, dtype=np.int64)

        # Check that fill_value is preserved by default
        y = x.view()
        assert_(y.fill_value == 1)

        # Check that fill_value is preserved if dtype is specified and the
        # dtype is an ndarray sub-class and has a _fill_value attribute
        y = x.view(MaskedArray)
        assert_(y.fill_value == 1)

        # Check that fill_value is preserved if type is specified and the
        # dtype is an ndarray sub-class and has a _fill_value attribute (by
        # default, the first argument is dtype, not type)
        y = x.view(type=MaskedArray)
        assert_(y.fill_value == 1)

        # Check that code does not crash if passed an ndarray sub-class that
        # does not have a _fill_value attribute
        y = x.view(np.ndarray)
        y = x.view(type=np.ndarray)

        # Check that fill_value can be overridden with view
        y = x.view(MaskedArray, fill_value=2)
        assert_(y.fill_value == 2)

        # Check that fill_value can be overridden with view (using type=)
        y = x.view(type=MaskedArray, fill_value=2)
        assert_(y.fill_value == 2)

        # Check that fill_value gets reset if passed a dtype but not a
        # fill_value. This is because even though in some cases one can safely
        # cast the fill_value, e.g. if taking an int64 view of an int32 array,
        # in other cases, this cannot be done (e.g. int32 view of an int64
        # array with a large fill_value).
        y = x.view(dtype=np.int32)
        assert_(y.fill_value == 999999)

    def test_fillvalue_bytes_or_str(self):
        # Test whether fill values work as expected for structured dtypes
        # containing bytes or str.  See issue #7259.
        a = empty(shape=(3, ), dtype="(2,)3S,(2,)3U")
        assert_equal(a["f0"].fill_value, default_fill_value(b"spam"))
        assert_equal(a["f1"].fill_value, default_fill_value("eggs"))


class TestUfuncs:
    # Test class for the application of ufuncs on MaskedArrays.

    def setup_method(self):
        # Base data definition.
        self.d = (array([1.0, 0, -1, pi / 2] * 2, mask=[0, 1] + [0] * 6),
                  array([1.0, 0, -1, pi / 2] * 2, mask=[1, 0] + [0] * 6),)
        self.err_status = np.geterr()
        np.seterr(divide='ignore', invalid='ignore')

    def teardown_method(self):
        np.seterr(**self.err_status)

    def test_testUfuncRegression(self):
        # Tests new ufuncs on MaskedArrays.
        for f in ['sqrt', 'log', 'log10', 'exp', 'conjugate',
                  'sin', 'cos', 'tan',
                  'arcsin', 'arccos', 'arctan',
                  'sinh', 'cosh', 'tanh',
                  'arcsinh',
                  'arccosh',
                  'arctanh',
                  'absolute', 'fabs', 'negative',
                  'floor', 'ceil',
                  'logical_not',
                  'add', 'subtract', 'multiply',
                  'divide', 'true_divide', 'floor_divide',
                  'remainder', 'fmod', 'hypot', 'arctan2',
                  'equal', 'not_equal', 'less_equal', 'greater_equal',
                  'less', 'greater',
                  'logical_and', 'logical_or', 'logical_xor',
                  ]:
            try:
                uf = getattr(umath, f)
            except AttributeError:
                uf = getattr(fromnumeric, f)
            mf = getattr(numpy.ma.core, f)
            args = self.d[:uf.nin]
            ur = uf(*args)
            mr = mf(*args)
            assert_equal(ur.filled(0), mr.filled(0), f)
            assert_mask_equal(ur.mask, mr.mask, err_msg=f)

    def test_reduce(self):
        # Tests reduce on MaskedArrays.
        a = self.d[0]
        assert_(not alltrue(a, axis=0))
        assert_(sometrue(a, axis=0))
        assert_equal(sum(a[:3], axis=0), 0)
        assert_equal(product(a, axis=0), 0)
        assert_equal(add.reduce(a), pi)

    def test_minmax(self):
        # Tests extrema on MaskedArrays.
        a = arange(1, 13).reshape(3, 4)
        amask = masked_where(a < 5, a)
        assert_equal(amask.max(), a.max())
        assert_equal(amask.min(), 5)
        assert_equal(amask.max(0), a.max(0))
        assert_equal(amask.min(0), [5, 6, 7, 8])
        assert_(amask.max(1)[0].mask)
        assert_(amask.min(1)[0].mask)

    def test_ndarray_mask(self):
        # Check that the mask of the result is a ndarray (not a MaskedArray...)
        a = masked_array([-1, 0, 1, 2, 3], mask=[0, 0, 0, 0, 1])
        test = np.sqrt(a)
        control = masked_array([-1, 0, 1, np.sqrt(2), -1],
                               mask=[1, 0, 0, 0, 1])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)
        assert_(not isinstance(test.mask, MaskedArray))

    def test_treatment_of_NotImplemented(self):
        # Check that NotImplemented is returned at appropriate places

        a = masked_array([1., 2.], mask=[1, 0])
        assert_raises(TypeError, operator.mul, a, "abc")
        assert_raises(TypeError, operator.truediv, a, "abc")

        class MyClass:
            __array_priority__ = a.__array_priority__ + 1

            def __mul__(self, other):
                return "My mul"

            def __rmul__(self, other):
                return "My rmul"

        me = MyClass()
        assert_(me * a == "My mul")
        assert_(a * me == "My rmul")

        # and that __array_priority__ is respected
        class MyClass2:
            __array_priority__ = 100

            def __mul__(self, other):
                return "Me2mul"

            def __rmul__(self, other):
                return "Me2rmul"

            def __rtruediv__(self, other):
                return "Me2rdiv"

        me_too = MyClass2()
        assert_(a.__mul__(me_too) is NotImplemented)
        assert_(all(multiply.outer(a, me_too) == "Me2rmul"))
        assert_(a.__truediv__(me_too) is NotImplemented)
        assert_(me_too * a == "Me2mul")
        assert_(a * me_too == "Me2rmul")
        assert_(a / me_too == "Me2rdiv")

    def test_no_masked_nan_warnings(self):
        # check that a nan in masked position does not
        # cause ufunc warnings

        m = np.ma.array([0.5, np.nan], mask=[0, 1])

        with warnings.catch_warnings():
            warnings.filterwarnings("error")

            # test unary and binary ufuncs
            exp(m)
            add(m, 1)
            m > 0

            # test different unary domains
            sqrt(m)
            log(m)
            tan(m)
            arcsin(m)
            arccos(m)
            arccosh(m)

            # test binary domains
            divide(m, 2)

            # also check that allclose uses ma ufuncs, to avoid warning
            allclose(m, 0.5)

    def test_masked_array_underflow(self):
        x = np.arange(0, 3, 0.1)
        X = np.ma.array(x)
        with np.errstate(under="raise"):
            X2 = X / 2.0
            np.testing.assert_array_equal(X2, x / 2)

class TestMaskedArrayInPlaceArithmetic:
    # Test MaskedArray Arithmetic

    def setup_method(self):
        x = arange(10)
        y = arange(10)
        xm = arange(10)
        xm[2] = masked
        self.intdata = (x, y, xm)
        self.floatdata = (x.astype(float), y.astype(float), xm.astype(float))
        self.othertypes = np.typecodes['AllInteger'] + np.typecodes['AllFloat']
        self.othertypes = [np.dtype(_).type for _ in self.othertypes]
        self.uint8data = (
            x.astype(np.uint8),
            y.astype(np.uint8),
            xm.astype(np.uint8)
        )

    def test_inplace_addition_scalar(self):
        # Test of inplace additions
        (x, y, xm) = self.intdata
        xm[2] = masked
        x += 1
        assert_equal(x, y + 1)
        xm += 1
        assert_equal(xm, y + 1)

        (x, _, xm) = self.floatdata
        id1 = x.data.ctypes.data
        x += 1.
        assert_(id1 == x.data.ctypes.data)
        assert_equal(x, y + 1.)

    def test_inplace_addition_array(self):
        # Test of inplace additions
        (x, y, xm) = self.intdata
        m = xm.mask
        a = arange(10, dtype=np.int16)
        a[-1] = masked
        x += a
        xm += a
        assert_equal(x, y + a)
        assert_equal(xm, y + a)
        assert_equal(xm.mask, mask_or(m, a.mask))

    def test_inplace_subtraction_scalar(self):
        # Test of inplace subtractions
        (x, y, xm) = self.intdata
        x -= 1
        assert_equal(x, y - 1)
        xm -= 1
        assert_equal(xm, y - 1)

    def test_inplace_subtraction_array(self):
        # Test of inplace subtractions
        (x, y, xm) = self.floatdata
        m = xm.mask
        a = arange(10, dtype=float)
        a[-1] = masked
        x -= a
        xm -= a
        assert_equal(x, y - a)
        assert_equal(xm, y - a)
        assert_equal(xm.mask, mask_or(m, a.mask))

    def test_inplace_multiplication_scalar(self):
        # Test of inplace multiplication
        (x, y, xm) = self.floatdata
        x *= 2.0
        assert_equal(x, y * 2)
        xm *= 2.0
        assert_equal(xm, y * 2)

    def test_inplace_multiplication_array(self):
        # Test of inplace multiplication
        (x, y, xm) = self.floatdata
        m = xm.mask
        a = arange(10, dtype=float)
        a[-1] = masked
        x *= a
        xm *= a
        assert_equal(x, y * a)
        assert_equal(xm, y * a)
        assert_equal(xm.mask, mask_or(m, a.mask))

    def test_inplace_division_scalar_int(self):
        # Test of inplace division
        (x, y, xm) = self.intdata
        x = arange(10) * 2
        xm = arange(10) * 2
        xm[2] = masked
        x //= 2
        assert_equal(x, y)
        xm //= 2
        assert_equal(xm, y)

    def test_inplace_division_scalar_float(self):
        # Test of inplace division
        (x, y, xm) = self.floatdata
        x /= 2.0
        assert_equal(x, y / 2.0)
        xm /= arange(10)
        assert_equal(xm, ones((10,)))

    def test_inplace_division_array_float(self):
        # Test of inplace division
        (x, y, xm) = self.floatdata
        m = xm.mask
        a = arange(10, dtype=float)
        a[-1] = masked
        x /= a
        xm /= a
        assert_equal(x, y / a)
        assert_equal(xm, y / a)
        assert_equal(xm.mask, mask_or(mask_or(m, a.mask), (a == 0)))

    def test_inplace_division_misc(self):

        x = [1., 1., 1., -2., pi / 2., 4., 5., -10., 10., 1., 2., 3.]
        y = [5., 0., 3., 2., -1., -4., 0., -10., 10., 1., 0., 3.]
        m1 = [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0]
        m2 = [0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1]
        xm = masked_array(x, mask=m1)
        ym = masked_array(y, mask=m2)

        z = xm / ym
        assert_equal(z._mask, [1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1])
        assert_equal(z._data,
                     [1., 1., 1., -1., -pi / 2., 4., 5., 1., 1., 1., 2., 3.])

        xm = xm.copy()
        xm /= ym
        assert_equal(xm._mask, [1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1])
        assert_equal(z._data,
                     [1., 1., 1., -1., -pi / 2., 4., 5., 1., 1., 1., 2., 3.])

    def test_datafriendly_add(self):
        # Test keeping data w/ (inplace) addition
        x = array([1, 2, 3], mask=[0, 0, 1])
        # Test add w/ scalar
        xx = x + 1
        assert_equal(xx.data, [2, 3, 3])
        assert_equal(xx.mask, [0, 0, 1])
        # Test iadd w/ scalar
        x += 1
        assert_equal(x.data, [2, 3, 3])
        assert_equal(x.mask, [0, 0, 1])
        # Test add w/ array
        x = array([1, 2, 3], mask=[0, 0, 1])
        xx = x + array([1, 2, 3], mask=[1, 0, 0])
        assert_equal(xx.data, [1, 4, 3])
        assert_equal(xx.mask, [1, 0, 1])
        # Test iadd w/ array
        x = array([1, 2, 3], mask=[0, 0, 1])
        x += array([1, 2, 3], mask=[1, 0, 0])
        assert_equal(x.data, [1, 4, 3])
        assert_equal(x.mask, [1, 0, 1])

    def test_datafriendly_sub(self):
        # Test keeping data w/ (inplace) subtraction
        # Test sub w/ scalar
        x = array([1, 2, 3], mask=[0, 0, 1])
        xx = x - 1
        assert_equal(xx.data, [0, 1, 3])
        assert_equal(xx.mask, [0, 0, 1])
        # Test isub w/ scalar
        x = array([1, 2, 3], mask=[0, 0, 1])
        x -= 1
        assert_equal(x.data, [0, 1, 3])
        assert_equal(x.mask, [0, 0, 1])
        # Test sub w/ array
        x = array([1, 2, 3], mask=[0, 0, 1])
        xx = x - array([1, 2, 3], mask=[1, 0, 0])
        assert_equal(xx.data, [1, 0, 3])
        assert_equal(xx.mask, [1, 0, 1])
        # Test isub w/ array
        x = array([1, 2, 3], mask=[0, 0, 1])
        x -= array([1, 2, 3], mask=[1, 0, 0])
        assert_equal(x.data, [1, 0, 3])
        assert_equal(x.mask, [1, 0, 1])

    def test_datafriendly_mul(self):
        # Test keeping data w/ (inplace) multiplication
        # Test mul w/ scalar
        x = array([1, 2, 3], mask=[0, 0, 1])
        xx = x * 2
        assert_equal(xx.data, [2, 4, 3])
        assert_equal(xx.mask, [0, 0, 1])
        # Test imul w/ scalar
        x = array([1, 2, 3], mask=[0, 0, 1])
        x *= 2
        assert_equal(x.data, [2, 4, 3])
        assert_equal(x.mask, [0, 0, 1])
        # Test mul w/ array
        x = array([1, 2, 3], mask=[0, 0, 1])
        xx = x * array([10, 20, 30], mask=[1, 0, 0])
        assert_equal(xx.data, [1, 40, 3])
        assert_equal(xx.mask, [1, 0, 1])
        # Test imul w/ array
        x = array([1, 2, 3], mask=[0, 0, 1])
        x *= array([10, 20, 30], mask=[1, 0, 0])
        assert_equal(x.data, [1, 40, 3])
        assert_equal(x.mask, [1, 0, 1])

    def test_datafriendly_div(self):
        # Test keeping data w/ (inplace) division
        # Test div on scalar
        x = array([1, 2, 3], mask=[0, 0, 1])
        xx = x / 2.
        assert_equal(xx.data, [1 / 2., 2 / 2., 3])
        assert_equal(xx.mask, [0, 0, 1])
        # Test idiv on scalar
        x = array([1., 2., 3.], mask=[0, 0, 1])
        x /= 2.
        assert_equal(x.data, [1 / 2., 2 / 2., 3])
        assert_equal(x.mask, [0, 0, 1])
        # Test div on array
        x = array([1., 2., 3.], mask=[0, 0, 1])
        xx = x / array([10., 20., 30.], mask=[1, 0, 0])
        assert_equal(xx.data, [1., 2. / 20., 3.])
        assert_equal(xx.mask, [1, 0, 1])
        # Test idiv on array
        x = array([1., 2., 3.], mask=[0, 0, 1])
        x /= array([10., 20., 30.], mask=[1, 0, 0])
        assert_equal(x.data, [1., 2 / 20., 3.])
        assert_equal(x.mask, [1, 0, 1])

    def test_datafriendly_pow(self):
        # Test keeping data w/ (inplace) power
        # Test pow on scalar
        x = array([1., 2., 3.], mask=[0, 0, 1])
        xx = x ** 2.5
        assert_equal(xx.data, [1., 2. ** 2.5, 3.])
        assert_equal(xx.mask, [0, 0, 1])
        # Test ipow on scalar
        x **= 2.5
        assert_equal(x.data, [1., 2. ** 2.5, 3])
        assert_equal(x.mask, [0, 0, 1])

    def test_datafriendly_add_arrays(self):
        a = array([[1, 1], [3, 3]])
        b = array([1, 1], mask=[0, 0])
        a += b
        assert_equal(a, [[2, 2], [4, 4]])
        if a.mask is not nomask:
            assert_equal(a.mask, [[0, 0], [0, 0]])

        a = array([[1, 1], [3, 3]])
        b = array([1, 1], mask=[0, 1])
        a += b
        assert_equal(a, [[2, 2], [4, 4]])
        assert_equal(a.mask, [[0, 1], [0, 1]])

    def test_datafriendly_sub_arrays(self):
        a = array([[1, 1], [3, 3]])
        b = array([1, 1], mask=[0, 0])
        a -= b
        assert_equal(a, [[0, 0], [2, 2]])
        if a.mask is not nomask:
            assert_equal(a.mask, [[0, 0], [0, 0]])

        a = array([[1, 1], [3, 3]])
        b = array([1, 1], mask=[0, 1])
        a -= b
        assert_equal(a, [[0, 0], [2, 2]])
        assert_equal(a.mask, [[0, 1], [0, 1]])

    def test_datafriendly_mul_arrays(self):
        a = array([[1, 1], [3, 3]])
        b = array([1, 1], mask=[0, 0])
        a *= b
        assert_equal(a, [[1, 1], [3, 3]])
        if a.mask is not nomask:
            assert_equal(a.mask, [[0, 0], [0, 0]])

        a = array([[1, 1], [3, 3]])
        b = array([1, 1], mask=[0, 1])
        a *= b
        assert_equal(a, [[1, 1], [3, 3]])
        assert_equal(a.mask, [[0, 1], [0, 1]])

    def test_inplace_addition_scalar_type(self):
        # Test of inplace additions
        for t in self.othertypes:
            with warnings.catch_warnings():
                warnings.filterwarnings("error")
                (x, y, xm) = (_.astype(t) for _ in self.uint8data)
                xm[2] = masked
                x += t(1)
                assert_equal(x, y + t(1))
                xm += t(1)
                assert_equal(xm, y + t(1))

    def test_inplace_addition_array_type(self):
        # Test of inplace additions
        for t in self.othertypes:
            with warnings.catch_warnings():
                warnings.filterwarnings("error")
                (x, y, xm) = (_.astype(t) for _ in self.uint8data)
                m = xm.mask
                a = arange(10, dtype=t)
                a[-1] = masked
                x += a
                xm += a
                assert_equal(x, y + a)
                assert_equal(xm, y + a)
                assert_equal(xm.mask, mask_or(m, a.mask))

    def test_inplace_subtraction_scalar_type(self):
        # Test of inplace subtractions
        for t in self.othertypes:
            with warnings.catch_warnings():
                warnings.filterwarnings("error")
                (x, y, xm) = (_.astype(t) for _ in self.uint8data)
                x -= t(1)
                assert_equal(x, y - t(1))
                xm -= t(1)
                assert_equal(xm, y - t(1))

    def test_inplace_subtraction_array_type(self):
        # Test of inplace subtractions
        for t in self.othertypes:
            with warnings.catch_warnings():
                warnings.filterwarnings("error")
                (x, y, xm) = (_.astype(t) for _ in self.uint8data)
                m = xm.mask
                a = arange(10, dtype=t)
                a[-1] = masked
                x -= a
                xm -= a
                assert_equal(x, y - a)
                assert_equal(xm, y - a)
                assert_equal(xm.mask, mask_or(m, a.mask))

    def test_inplace_multiplication_scalar_type(self):
        # Test of inplace multiplication
        for t in self.othertypes:
            with warnings.catch_warnings():
                warnings.filterwarnings("error")
                (x, y, xm) = (_.astype(t) for _ in self.uint8data)
                x *= t(2)
                assert_equal(x, y * t(2))
                xm *= t(2)
                assert_equal(xm, y * t(2))

    def test_inplace_multiplication_array_type(self):
        # Test of inplace multiplication
        for t in self.othertypes:
            with warnings.catch_warnings():
                warnings.filterwarnings("error")
                (x, y, xm) = (_.astype(t) for _ in self.uint8data)
                m = xm.mask
                a = arange(10, dtype=t)
                a[-1] = masked
                x *= a
                xm *= a
                assert_equal(x, y * a)
                assert_equal(xm, y * a)
                assert_equal(xm.mask, mask_or(m, a.mask))

    def test_inplace_floor_division_scalar_type(self):
        # Test of inplace division
        # Check for TypeError in case of unsupported types
        unsupported = {np.dtype(t).type for t in np.typecodes["Complex"]}
        for t in self.othertypes:
            with warnings.catch_warnings():
                warnings.filterwarnings("error")
                (x, y, xm) = (_.astype(t) for _ in self.uint8data)
                x = arange(10, dtype=t) * t(2)
                xm = arange(10, dtype=t) * t(2)
                xm[2] = masked
                try:
                    x //= t(2)
                    xm //= t(2)
                    assert_equal(x, y)
                    assert_equal(xm, y)
                except TypeError:
                    msg = f"Supported type {t} throwing TypeError"
                    assert t in unsupported, msg

    def test_inplace_floor_division_array_type(self):
        # Test of inplace division
        # Check for TypeError in case of unsupported types
        unsupported = {np.dtype(t).type for t in np.typecodes["Complex"]}
        for t in self.othertypes:
            with warnings.catch_warnings():
                warnings.filterwarnings("error")
                (x, y, xm) = (_.astype(t) for _ in self.uint8data)
                m = xm.mask
                a = arange(10, dtype=t)
                a[-1] = masked
                try:
                    x //= a
                    xm //= a
                    assert_equal(x, y // a)
                    assert_equal(xm, y // a)
                    assert_equal(
                        xm.mask,
                        mask_or(mask_or(m, a.mask), (a == t(0)))
                    )
                except TypeError:
                    msg = f"Supported type {t} throwing TypeError"
                    assert t in unsupported, msg

    def test_inplace_division_scalar_type(self):
        # Test of inplace division
        for t in self.othertypes:
            with suppress_warnings() as sup:
                sup.record(UserWarning)

                (x, y, xm) = (_.astype(t) for _ in self.uint8data)
                x = arange(10, dtype=t) * t(2)
                xm = arange(10, dtype=t) * t(2)
                xm[2] = masked

                # May get a DeprecationWarning or a TypeError.
                #
                # This is a consequence of the fact that this is true divide
                # and will require casting to float for calculation and
                # casting back to the original type. This will only be raised
                # with integers. Whether it is an error or warning is only
                # dependent on how stringent the casting rules are.
                #
                # Will handle the same way.
                try:
                    x /= t(2)
                    assert_equal(x, y)
                except (DeprecationWarning, TypeError) as e:
                    warnings.warn(str(e), stacklevel=1)
                try:
                    xm /= t(2)
                    assert_equal(xm, y)
                except (DeprecationWarning, TypeError) as e:
                    warnings.warn(str(e), stacklevel=1)

                if issubclass(t, np.integer):
                    assert_equal(len(sup.log), 2, f'Failed on type={t}.')
                else:
                    assert_equal(len(sup.log), 0, f'Failed on type={t}.')

    def test_inplace_division_array_type(self):
        # Test of inplace division
        for t in self.othertypes:
            with suppress_warnings() as sup:
                sup.record(UserWarning)
                (x, y, xm) = (_.astype(t) for _ in self.uint8data)
                m = xm.mask
                a = arange(10, dtype=t)
                a[-1] = masked

                # May get a DeprecationWarning or a TypeError.
                #
                # This is a consequence of the fact that this is true divide
                # and will require casting to float for calculation and
                # casting back to the original type. This will only be raised
                # with integers. Whether it is an error or warning is only
                # dependent on how stringent the casting rules are.
                #
                # Will handle the same way.
                try:
                    x /= a
                    assert_equal(x, y / a)
                except (DeprecationWarning, TypeError) as e:
                    warnings.warn(str(e), stacklevel=1)
                try:
                    xm /= a
                    assert_equal(xm, y / a)
                    assert_equal(
                        xm.mask,
                        mask_or(mask_or(m, a.mask), (a == t(0)))
                    )
                except (DeprecationWarning, TypeError) as e:
                    warnings.warn(str(e), stacklevel=1)

                if issubclass(t, np.integer):
                    assert_equal(len(sup.log), 2, f'Failed on type={t}.')
                else:
                    assert_equal(len(sup.log), 0, f'Failed on type={t}.')

    def test_inplace_pow_type(self):
        # Test keeping data w/ (inplace) power
        for t in self.othertypes:
            with warnings.catch_warnings():
                warnings.filterwarnings("error")
                # Test pow on scalar
                x = array([1, 2, 3], mask=[0, 0, 1], dtype=t)
                xx = x ** t(2)
                xx_r = array([1, 2 ** 2, 3], mask=[0, 0, 1], dtype=t)
                assert_equal(xx.data, xx_r.data)
                assert_equal(xx.mask, xx_r.mask)
                # Test ipow on scalar
                x **= t(2)
                assert_equal(x.data, xx_r.data)
                assert_equal(x.mask, xx_r.mask)


class TestMaskedArrayMethods:
    # Test class for miscellaneous MaskedArrays methods.
    def setup_method(self):
        # Base data definition.
        x = np.array([8.375, 7.545, 8.828, 8.5, 1.757, 5.928,
                      8.43, 7.78, 9.865, 5.878, 8.979, 4.732,
                      3.012, 6.022, 5.095, 3.116, 5.238, 3.957,
                      6.04, 9.63, 7.712, 3.382, 4.489, 6.479,
                      7.189, 9.645, 5.395, 4.961, 9.894, 2.893,
                      7.357, 9.828, 6.272, 3.758, 6.693, 0.993])
        X = x.reshape(6, 6)
        XX = x.reshape(3, 2, 2, 3)

        m = np.array([0, 1, 0, 1, 0, 0,
                     1, 0, 1, 1, 0, 1,
                     0, 0, 0, 1, 0, 1,
                     0, 0, 0, 1, 1, 1,
                     1, 0, 0, 1, 0, 0,
                     0, 0, 1, 0, 1, 0])
        mx = array(data=x, mask=m)
        mX = array(data=X, mask=m.reshape(X.shape))
        mXX = array(data=XX, mask=m.reshape(XX.shape))

        m2 = np.array([1, 1, 0, 1, 0, 0,
                      1, 1, 1, 1, 0, 1,
                      0, 0, 1, 1, 0, 1,
                      0, 0, 0, 1, 1, 1,
                      1, 0, 0, 1, 1, 0,
                      0, 0, 1, 0, 1, 1])
        m2x = array(data=x, mask=m2)
        m2X = array(data=X, mask=m2.reshape(X.shape))
        m2XX = array(data=XX, mask=m2.reshape(XX.shape))
        self.d = (x, X, XX, m, mx, mX, mXX, m2x, m2X, m2XX)

    def test_generic_methods(self):
        # Tests some MaskedArray methods.
        a = array([1, 3, 2])
        assert_equal(a.any(), a._data.any())
        assert_equal(a.all(), a._data.all())
        assert_equal(a.argmax(), a._data.argmax())
        assert_equal(a.argmin(), a._data.argmin())
        assert_equal(a.choose(0, 1, 2, 3, 4), a._data.choose(0, 1, 2, 3, 4))
        assert_equal(a.compress([1, 0, 1]), a._data.compress([1, 0, 1]))
        assert_equal(a.conj(), a._data.conj())
        assert_equal(a.conjugate(), a._data.conjugate())

        m = array([[1, 2], [3, 4]])
        assert_equal(m.diagonal(), m._data.diagonal())
        assert_equal(a.sum(), a._data.sum())
        assert_equal(a.take([1, 2]), a._data.take([1, 2]))
        assert_equal(m.transpose(), m._data.transpose())

    def test_allclose(self):
        # Tests allclose on arrays
        a = np.random.rand(10)
        b = a + np.random.rand(10) * 1e-8
        assert_(allclose(a, b))
        # Test allclose w/ infs
        a[0] = np.inf
        assert_(not allclose(a, b))
        b[0] = np.inf
        assert_(allclose(a, b))
        # Test allclose w/ masked
        a = masked_array(a)
        a[-1] = masked
        assert_(allclose(a, b, masked_equal=True))
        assert_(not allclose(a, b, masked_equal=False))
        # Test comparison w/ scalar
        a *= 1e-8
        a[0] = 0
        assert_(allclose(a, 0, masked_equal=True))

        # Test that the function works for MIN_INT integer typed arrays
        a = masked_array([np.iinfo(np.int_).min], dtype=np.int_)
        assert_(allclose(a, a))

    def test_allclose_timedelta(self):
        # Allclose currently works for timedelta64 as long as `atol` is
        # an integer or also a timedelta64
        a = np.array([[1, 2, 3, 4]], dtype="m8[ns]")
        assert allclose(a, a, atol=0)
        assert allclose(a, a, atol=np.timedelta64(1, "ns"))

    def test_allany(self):
        # Checks the any/all methods/functions.
        x = np.array([[0.13, 0.26, 0.90],
                      [0.28, 0.33, 0.63],
                      [0.31, 0.87, 0.70]])
        m = np.array([[True, False, False],
                      [False, False, False],
                      [True, True, False]], dtype=np.bool)
        mx = masked_array(x, mask=m)
        mxbig = (mx > 0.5)
        mxsmall = (mx < 0.5)

        assert_(not mxbig.all())
        assert_(mxbig.any())
        assert_equal(mxbig.all(0), [False, False, True])
        assert_equal(mxbig.all(1), [False, False, True])
        assert_equal(mxbig.any(0), [False, False, True])
        assert_equal(mxbig.any(1), [True, True, True])

        assert_(not mxsmall.all())
        assert_(mxsmall.any())
        assert_equal(mxsmall.all(0), [True, True, False])
        assert_equal(mxsmall.all(1), [False, False, False])
        assert_equal(mxsmall.any(0), [True, True, False])
        assert_equal(mxsmall.any(1), [True, True, False])

    def test_allany_oddities(self):
        # Some fun with all and any
        store = empty((), dtype=bool)
        full = array([1, 2, 3], mask=True)

        assert_(full.all() is masked)
        full.all(out=store)
        assert_(store)
        assert_(store._mask, True)
        assert_(store is not masked)

        store = empty((), dtype=bool)
        assert_(full.any() is masked)
        full.any(out=store)
        assert_(not store)
        assert_(store._mask, True)
        assert_(store is not masked)

    def test_argmax_argmin(self):
        # Tests argmin & argmax on MaskedArrays.
        (x, X, XX, m, mx, mX, mXX, m2x, m2X, m2XX) = self.d

        assert_equal(mx.argmin(), 35)
        assert_equal(mX.argmin(), 35)
        assert_equal(m2x.argmin(), 4)
        assert_equal(m2X.argmin(), 4)
        assert_equal(mx.argmax(), 28)
        assert_equal(mX.argmax(), 28)
        assert_equal(m2x.argmax(), 31)
        assert_equal(m2X.argmax(), 31)

        assert_equal(mX.argmin(0), [2, 2, 2, 5, 0, 5])
        assert_equal(m2X.argmin(0), [2, 2, 4, 5, 0, 4])
        assert_equal(mX.argmax(0), [0, 5, 0, 5, 4, 0])
        assert_equal(m2X.argmax(0), [5, 5, 0, 5, 1, 0])

        assert_equal(mX.argmin(1), [4, 1, 0, 0, 5, 5, ])
        assert_equal(m2X.argmin(1), [4, 4, 0, 0, 5, 3])
        assert_equal(mX.argmax(1), [2, 4, 1, 1, 4, 1])
        assert_equal(m2X.argmax(1), [2, 4, 1, 1, 1, 1])

    def test_clip(self):
        # Tests clip on MaskedArrays.
        x = np.array([8.375, 7.545, 8.828, 8.5, 1.757, 5.928,
                      8.43, 7.78, 9.865, 5.878, 8.979, 4.732,
                      3.012, 6.022, 5.095, 3.116, 5.238, 3.957,
                      6.04, 9.63, 7.712, 3.382, 4.489, 6.479,
                      7.189, 9.645, 5.395, 4.961, 9.894, 2.893,
                      7.357, 9.828, 6.272, 3.758, 6.693, 0.993])
        m = np.array([0, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1,
                      0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 1, 1,
                      1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0])
        mx = array(x, mask=m)
        clipped = mx.clip(2, 8)
        assert_equal(clipped.mask, mx.mask)
        assert_equal(clipped._data, x.clip(2, 8))
        assert_equal(clipped._data, mx._data.clip(2, 8))

    def test_clip_out(self):
        # gh-14140
        a = np.arange(10)
        m = np.ma.MaskedArray(a, mask=[0, 1] * 5)
        m.clip(0, 5, out=m)
        assert_equal(m.mask, [0, 1] * 5)

    def test_compress(self):
        # test compress
        a = masked_array([1., 2., 3., 4., 5.], fill_value=9999)
        condition = (a > 1.5) & (a < 3.5)
        assert_equal(a.compress(condition), [2., 3.])

        a[[2, 3]] = masked
        b = a.compress(condition)
        assert_equal(b._data, [2., 3.])
        assert_equal(b._mask, [0, 1])
        assert_equal(b.fill_value, 9999)
        assert_equal(b, a[condition])

        condition = (a < 4.)
        b = a.compress(condition)
        assert_equal(b._data, [1., 2., 3.])
        assert_equal(b._mask, [0, 0, 1])
        assert_equal(b.fill_value, 9999)
        assert_equal(b, a[condition])

        a = masked_array([[10, 20, 30], [40, 50, 60]],
                         mask=[[0, 0, 1], [1, 0, 0]])
        b = a.compress(a.ravel() >= 22)
        assert_equal(b._data, [30, 40, 50, 60])
        assert_equal(b._mask, [1, 1, 0, 0])

        x = np.array([3, 1, 2])
        b = a.compress(x >= 2, axis=1)
        assert_equal(b._data, [[10, 30], [40, 60]])
        assert_equal(b._mask, [[0, 1], [1, 0]])

    def test_compressed(self):
        # Tests compressed
        a = array([1, 2, 3, 4], mask=[0, 0, 0, 0])
        b = a.compressed()
        assert_equal(b, a)
        a[0] = masked
        b = a.compressed()
        assert_equal(b, [2, 3, 4])

    def test_empty(self):
        # Tests empty/like
        datatype = [('a', int), ('b', float), ('c', '|S8')]
        a = masked_array([(1, 1.1, '1.1'), (2, 2.2, '2.2'), (3, 3.3, '3.3')],
                         dtype=datatype)
        assert_equal(len(a.fill_value.item()), len(datatype))

        b = empty_like(a)
        assert_equal(b.shape, a.shape)
        assert_equal(b.fill_value, a.fill_value)

        b = empty(len(a), dtype=datatype)
        assert_equal(b.shape, a.shape)
        assert_equal(b.fill_value, a.fill_value)

        # check empty_like mask handling
        a = masked_array([1, 2, 3], mask=[False, True, False])
        b = empty_like(a)
        assert_(not np.may_share_memory(a.mask, b.mask))
        b = a.view(masked_array)
        assert_(np.may_share_memory(a.mask, b.mask))

    def test_zeros(self):
        # Tests zeros/like
        datatype = [('a', int), ('b', float), ('c', '|S8')]
        a = masked_array([(1, 1.1, '1.1'), (2, 2.2, '2.2'), (3, 3.3, '3.3')],
                         dtype=datatype)
        assert_equal(len(a.fill_value.item()), len(datatype))

        b = zeros(len(a), dtype=datatype)
        assert_equal(b.shape, a.shape)
        assert_equal(b.fill_value, a.fill_value)

        b = zeros_like(a)
        assert_equal(b.shape, a.shape)
        assert_equal(b.fill_value, a.fill_value)

        # check zeros_like mask handling
        a = masked_array([1, 2, 3], mask=[False, True, False])
        b = zeros_like(a)
        assert_(not np.may_share_memory(a.mask, b.mask))
        b = a.view()
        assert_(np.may_share_memory(a.mask, b.mask))

    def test_ones(self):
        # Tests ones/like
        datatype = [('a', int), ('b', float), ('c', '|S8')]
        a = masked_array([(1, 1.1, '1.1'), (2, 2.2, '2.2'), (3, 3.3, '3.3')],
                         dtype=datatype)
        assert_equal(len(a.fill_value.item()), len(datatype))

        b = ones(len(a), dtype=datatype)
        assert_equal(b.shape, a.shape)
        assert_equal(b.fill_value, a.fill_value)

        b = ones_like(a)
        assert_equal(b.shape, a.shape)
        assert_equal(b.fill_value, a.fill_value)

        # check ones_like mask handling
        a = masked_array([1, 2, 3], mask=[False, True, False])
        b = ones_like(a)
        assert_(not np.may_share_memory(a.mask, b.mask))
        b = a.view()
        assert_(np.may_share_memory(a.mask, b.mask))

    @suppress_copy_mask_on_assignment
    def test_put(self):
        # Tests put.
        d = arange(5)
        n = [0, 0, 0, 1, 1]
        m = make_mask(n)
        x = array(d, mask=m)
        assert_(x[3] is masked)
        assert_(x[4] is masked)
        x[[1, 4]] = [10, 40]
        assert_(x[3] is masked)
        assert_(x[4] is not masked)
        assert_equal(x, [0, 10, 2, -1, 40])

        x = masked_array(arange(10), mask=[1, 0, 0, 0, 0] * 2)
        i = [0, 2, 4, 6]
        x.put(i, [6, 4, 2, 0])
        assert_equal(x, asarray([6, 1, 4, 3, 2, 5, 0, 7, 8, 9, ]))
        assert_equal(x.mask, [0, 0, 0, 0, 0, 1, 0, 0, 0, 0])
        x.put(i, masked_array([0, 2, 4, 6], [1, 0, 1, 0]))
        assert_array_equal(x, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, ])
        assert_equal(x.mask, [1, 0, 0, 0, 1, 1, 0, 0, 0, 0])

        x = masked_array(arange(10), mask=[1, 0, 0, 0, 0] * 2)
        put(x, i, [6, 4, 2, 0])
        assert_equal(x, asarray([6, 1, 4, 3, 2, 5, 0, 7, 8, 9, ]))
        assert_equal(x.mask, [0, 0, 0, 0, 0, 1, 0, 0, 0, 0])
        put(x, i, masked_array([0, 2, 4, 6], [1, 0, 1, 0]))
        assert_array_equal(x, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, ])
        assert_equal(x.mask, [1, 0, 0, 0, 1, 1, 0, 0, 0, 0])

    def test_put_nomask(self):
        # GitHub issue 6425
        x = zeros(10)
        z = array([3., -1.], mask=[False, True])

        x.put([1, 2], z)
        assert_(x[0] is not masked)
        assert_equal(x[0], 0)
        assert_(x[1] is not masked)
        assert_equal(x[1], 3)
        assert_(x[2] is masked)
        assert_(x[3] is not masked)
        assert_equal(x[3], 0)

    def test_put_hardmask(self):
        # Tests put on hardmask
        d = arange(5)
        n = [0, 0, 0, 1, 1]
        m = make_mask(n)
        xh = array(d + 1, mask=m, hard_mask=True, copy=True)
        xh.put([4, 2, 0, 1, 3], [1, 2, 3, 4, 5])
        assert_equal(xh._data, [3, 4, 2, 4, 5])

    def test_putmask(self):
        x = arange(6) + 1
        mx = array(x, mask=[0, 0, 0, 1, 1, 1])
        mask = [0, 0, 1, 0, 0, 1]
        # w/o mask, w/o masked values
        xx = x.copy()
        putmask(xx, mask, 99)
        assert_equal(xx, [1, 2, 99, 4, 5, 99])
        # w/ mask, w/o masked values
        mxx = mx.copy()
        putmask(mxx, mask, 99)
        assert_equal(mxx._data, [1, 2, 99, 4, 5, 99])
        assert_equal(mxx._mask, [0, 0, 0, 1, 1, 0])
        # w/o mask, w/ masked values
        values = array([10, 20, 30, 40, 50, 60], mask=[1, 1, 1, 0, 0, 0])
        xx = x.copy()
        putmask(xx, mask, values)
        assert_equal(xx._data, [1, 2, 30, 4, 5, 60])
        assert_equal(xx._mask, [0, 0, 1, 0, 0, 0])
        # w/ mask, w/ masked values
        mxx = mx.copy()
        putmask(mxx, mask, values)
        assert_equal(mxx._data, [1, 2, 30, 4, 5, 60])
        assert_equal(mxx._mask, [0, 0, 1, 1, 1, 0])
        # w/ mask, w/ masked values + hardmask
        mxx = mx.copy()
        mxx.harden_mask()
        putmask(mxx, mask, values)
        assert_equal(mxx, [1, 2, 30, 4, 5, 60])

    def test_ravel(self):
        # Tests ravel
        a = array([[1, 2, 3, 4, 5]], mask=[[0, 1, 0, 0, 0]])
        aravel = a.ravel()
        assert_equal(aravel._mask.shape, aravel.shape)
        a = array([0, 0], mask=[1, 1])
        aravel = a.ravel()
        assert_equal(aravel._mask.shape, a.shape)
        # Checks that small_mask is preserved
        a = array([1, 2, 3, 4], mask=[0, 0, 0, 0], shrink=False)
        assert_equal(a.ravel()._mask, [0, 0, 0, 0])
        # Test that the fill_value is preserved
        a.fill_value = -99
        a.shape = (2, 2)
        ar = a.ravel()
        assert_equal(ar._mask, [0, 0, 0, 0])
        assert_equal(ar._data, [1, 2, 3, 4])
        assert_equal(ar.fill_value, -99)
        # Test index ordering
        assert_equal(a.ravel(order='C'), [1, 2, 3, 4])
        assert_equal(a.ravel(order='F'), [1, 3, 2, 4])

    @pytest.mark.parametrize("order", "AKCF")
    @pytest.mark.parametrize("data_order", "CF")
    def test_ravel_order(self, order, data_order):
        # Ravelling must ravel mask and data in the same order always to avoid
        # misaligning the two in the ravel result.
        arr = np.ones((5, 10), order=data_order)
        arr[0, :] = 0
        mask = np.ones((10, 5), dtype=bool, order=data_order).T
        mask[0, :] = False
        x = array(arr, mask=mask)
        assert x._data.flags.fnc != x._mask.flags.fnc
        assert (x.filled(0) == 0).all()
        raveled = x.ravel(order)
        assert (raveled.filled(0) == 0).all()

        # NOTE: Can be wrong if arr order is neither C nor F and `order="K"`
        assert_array_equal(arr.ravel(order), x.ravel(order)._data)

    def test_reshape(self):
        # Tests reshape
        x = arange(4)
        x[0] = masked
        y = x.reshape(2, 2)
        assert_equal(y.shape, (2, 2,))
        assert_equal(y._mask.shape, (2, 2,))
        assert_equal(x.shape, (4,))
        assert_equal(x._mask.shape, (4,))

    def test_sort(self):
        # Test sort
        x = array([1, 4, 2, 3], mask=[0, 1, 0, 0], dtype=np.uint8)

        sortedx = sort(x)
        assert_equal(sortedx._data, [1, 2, 3, 4])
        assert_equal(sortedx._mask, [0, 0, 0, 1])

        sortedx = sort(x, endwith=False)
        assert_equal(sortedx._data, [4, 1, 2, 3])
        assert_equal(sortedx._mask, [1, 0, 0, 0])

        x.sort()
        assert_equal(x._data, [1, 2, 3, 4])
        assert_equal(x._mask, [0, 0, 0, 1])

        x = array([1, 4, 2, 3], mask=[0, 1, 0, 0], dtype=np.uint8)
        x.sort(endwith=False)
        assert_equal(x._data, [4, 1, 2, 3])
        assert_equal(x._mask, [1, 0, 0, 0])

        x = [1, 4, 2, 3]
        sortedx = sort(x)
        assert_(not isinstance(sorted, MaskedArray))

        x = array([0, 1, -1, -2, 2], mask=nomask, dtype=np.int8)
        sortedx = sort(x, endwith=False)
        assert_equal(sortedx._data, [-2, -1, 0, 1, 2])
        x = array([0, 1, -1, -2, 2], mask=[0, 1, 0, 0, 1], dtype=np.int8)
        sortedx = sort(x, endwith=False)
        assert_equal(sortedx._data, [1, 2, -2, -1, 0])
        assert_equal(sortedx._mask, [1, 1, 0, 0, 0])

        x = array([0, -1], dtype=np.int8)
        sortedx = sort(x, kind="stable")
        assert_equal(sortedx, array([-1, 0], dtype=np.int8))

    def test_stable_sort(self):
        x = array([1, 2, 3, 1, 2, 3], dtype=np.uint8)
        expected = array([0, 3, 1, 4, 2, 5])
        computed = argsort(x, kind='stable')
        assert_equal(computed, expected)

    def test_argsort_matches_sort(self):
        x = array([1, 4, 2, 3], mask=[0, 1, 0, 0], dtype=np.uint8)

        for kwargs in [{},
                       {"endwith": True},
                       {"endwith": False},
                       {"fill_value": 2},
                       {"fill_value": 2, "endwith": True},
                       {"fill_value": 2, "endwith": False}]:
            sortedx = sort(x, **kwargs)
            argsortedx = x[argsort(x, **kwargs)]
            assert_equal(sortedx._data, argsortedx._data)
            assert_equal(sortedx._mask, argsortedx._mask)

    def test_sort_2d(self):
        # Check sort of 2D array.
        # 2D array w/o mask
        a = masked_array([[8, 4, 1], [2, 0, 9]])
        a.sort(0)
        assert_equal(a, [[2, 0, 1], [8, 4, 9]])
        a = masked_array([[8, 4, 1], [2, 0, 9]])
        a.sort(1)
        assert_equal(a, [[1, 4, 8], [0, 2, 9]])
        # 2D array w/mask
        a = masked_array([[8, 4, 1], [2, 0, 9]], mask=[[1, 0, 0], [0, 0, 1]])
        a.sort(0)
        assert_equal(a, [[2, 0, 1], [8, 4, 9]])
        assert_equal(a._mask, [[0, 0, 0], [1, 0, 1]])
        a = masked_array([[8, 4, 1], [2, 0, 9]], mask=[[1, 0, 0], [0, 0, 1]])
        a.sort(1)
        assert_equal(a, [[1, 4, 8], [0, 2, 9]])
        assert_equal(a._mask, [[0, 0, 1], [0, 0, 1]])
        # 3D
        a = masked_array([[[7, 8, 9], [4, 5, 6], [1, 2, 3]],
                          [[1, 2, 3], [7, 8, 9], [4, 5, 6]],
                          [[7, 8, 9], [1, 2, 3], [4, 5, 6]],
                          [[4, 5, 6], [1, 2, 3], [7, 8, 9]]])
        a[a % 4 == 0] = masked
        am = a.copy()
        an = a.filled(99)
        am.sort(0)
        an.sort(0)
        assert_equal(am, an)
        am = a.copy()
        an = a.filled(99)
        am.sort(1)
        an.sort(1)
        assert_equal(am, an)
        am = a.copy()
        an = a.filled(99)
        am.sort(2)
        an.sort(2)
        assert_equal(am, an)

    def test_sort_flexible(self):
        # Test sort on structured dtype.
        a = array(
            data=[(3, 3), (3, 2), (2, 2), (2, 1), (1, 0), (1, 1), (1, 2)],
            mask=[(0, 0), (0, 1), (0, 0), (0, 0), (1, 0), (0, 0), (0, 0)],
            dtype=[('A', int), ('B', int)])
        mask_last = array(
            data=[(1, 1), (1, 2), (2, 1), (2, 2), (3, 3), (3, 2), (1, 0)],
            mask=[(0, 0), (0, 0), (0, 0), (0, 0), (0, 0), (0, 1), (1, 0)],
            dtype=[('A', int), ('B', int)])
        mask_first = array(
            data=[(1, 0), (1, 1), (1, 2), (2, 1), (2, 2), (3, 2), (3, 3)],
            mask=[(1, 0), (0, 0), (0, 0), (0, 0), (0, 0), (0, 1), (0, 0)],
            dtype=[('A', int), ('B', int)])

        test = sort(a)
        assert_equal(test, mask_last)
        assert_equal(test.mask, mask_last.mask)

        test = sort(a, endwith=False)
        assert_equal(test, mask_first)
        assert_equal(test.mask, mask_first.mask)

        # Test sort on dtype with subarray (gh-8069)
        # Just check that the sort does not error, structured array subarrays
        # are treated as byte strings and that leads to differing behavior
        # depending on endianness and `endwith`.
        dt = np.dtype([('v', int, 2)])
        a = a.view(dt)
        test = sort(a)
        test = sort(a, endwith=False)

    def test_argsort(self):
        # Test argsort
        a = array([1, 5, 2, 4, 3], mask=[1, 0, 0, 1, 0])
        assert_equal(np.argsort(a), argsort(a))

    def test_squeeze(self):
        # Check squeeze
        data = masked_array([[1, 2, 3]])
        assert_equal(data.squeeze(), [1, 2, 3])
        data = masked_array([[1, 2, 3]], mask=[[1, 1, 1]])
        assert_equal(data.squeeze(), [1, 2, 3])
        assert_equal(data.squeeze()._mask, [1, 1, 1])

        # normal ndarrays return a view
        arr = np.array([[1]])
        arr_sq = arr.squeeze()
        assert_equal(arr_sq, 1)
        arr_sq[...] = 2
        assert_equal(arr[0, 0], 2)

        # so maskedarrays should too
        m_arr = masked_array([[1]], mask=True)
        m_arr_sq = m_arr.squeeze()
        assert_(m_arr_sq is not np.ma.masked)
        assert_equal(m_arr_sq.mask, True)
        m_arr_sq[...] = 2
        assert_equal(m_arr[0, 0], 2)

    def test_swapaxes(self):
        # Tests swapaxes on MaskedArrays.
        x = np.array([8.375, 7.545, 8.828, 8.5, 1.757, 5.928,
                      8.43, 7.78, 9.865, 5.878, 8.979, 4.732,
                      3.012, 6.022, 5.095, 3.116, 5.238, 3.957,
                      6.04, 9.63, 7.712, 3.382, 4.489, 6.479,
                      7.189, 9.645, 5.395, 4.961, 9.894, 2.893,
                      7.357, 9.828, 6.272, 3.758, 6.693, 0.993])
        m = np.array([0, 1, 0, 1, 0, 0,
                      1, 0, 1, 1, 0, 1,
                      0, 0, 0, 1, 0, 1,
                      0, 0, 0, 1, 1, 1,
                      1, 0, 0, 1, 0, 0,
                      0, 0, 1, 0, 1, 0])
        mX = array(x, mask=m).reshape(6, 6)
        mXX = mX.reshape(3, 2, 2, 3)

        mXswapped = mX.swapaxes(0, 1)
        assert_equal(mXswapped[-1], mX[:, -1])

        mXXswapped = mXX.swapaxes(0, 2)
        assert_equal(mXXswapped.shape, (2, 2, 3, 3))

    def test_take(self):
        # Tests take
        x = masked_array([10, 20, 30, 40], [0, 1, 0, 1])
        assert_equal(x.take([0, 0, 3]), masked_array([10, 10, 40], [0, 0, 1]))
        assert_equal(x.take([0, 0, 3]), x[[0, 0, 3]])
        assert_equal(x.take([[0, 1], [0, 1]]),
                     masked_array([[10, 20], [10, 20]], [[0, 1], [0, 1]]))

        # assert_equal crashes when passed np.ma.mask
        assert_(x[1] is np.ma.masked)
        assert_(x.take(1) is np.ma.masked)

        x = array([[10, 20, 30], [40, 50, 60]], mask=[[0, 0, 1], [1, 0, 0, ]])
        assert_equal(x.take([0, 2], axis=1),
                     array([[10, 30], [40, 60]], mask=[[0, 1], [1, 0]]))
        assert_equal(take(x, [0, 2], axis=1),
                     array([[10, 30], [40, 60]], mask=[[0, 1], [1, 0]]))

    def test_take_masked_indices(self):
        # Test take w/ masked indices
        a = np.array((40, 18, 37, 9, 22))
        indices = np.arange(3)[None, :] + np.arange(5)[:, None]
        mindices = array(indices, mask=(indices >= len(a)))
        # No mask
        test = take(a, mindices, mode='clip')
        ctrl = array([[40, 18, 37],
                      [18, 37, 9],
                      [37, 9, 22],
                      [9, 22, 22],
                      [22, 22, 22]])
        assert_equal(test, ctrl)
        # Masked indices
        test = take(a, mindices)
        ctrl = array([[40, 18, 37],
                      [18, 37, 9],
                      [37, 9, 22],
                      [9, 22, 40],
                      [22, 40, 40]])
        ctrl[3, 2] = ctrl[4, 1] = ctrl[4, 2] = masked
        assert_equal(test, ctrl)
        assert_equal(test.mask, ctrl.mask)
        # Masked input + masked indices
        a = array((40, 18, 37, 9, 22), mask=(0, 1, 0, 0, 0))
        test = take(a, mindices)
        ctrl[0, 1] = ctrl[1, 0] = masked
        assert_equal(test, ctrl)
        assert_equal(test.mask, ctrl.mask)

    def test_tolist(self):
        # Tests to list
        # ... on 1D
        x = array(np.arange(12))
        x[[1, -2]] = masked
        xlist = x.tolist()
        assert_(xlist[1] is None)
        assert_(xlist[-2] is None)
        # ... on 2D
        x.shape = (3, 4)
        xlist = x.tolist()
        ctrl = [[0, None, 2, 3], [4, 5, 6, 7], [8, 9, None, 11]]
        assert_equal(xlist[0], [0, None, 2, 3])
        assert_equal(xlist[1], [4, 5, 6, 7])
        assert_equal(xlist[2], [8, 9, None, 11])
        assert_equal(xlist, ctrl)
        # ... on structured array w/ masked records
        x = array(list(zip([1, 2, 3],
                           [1.1, 2.2, 3.3],
                           ['one', 'two', 'thr'])),
                  dtype=[('a', int), ('b', float), ('c', '|S8')])
        x[-1] = masked
        assert_equal(x.tolist(),
                     [(1, 1.1, b'one'),
                      (2, 2.2, b'two'),
                      (None, None, None)])
        # ... on structured array w/ masked fields
        a = array([(1, 2,), (3, 4)], mask=[(0, 1), (0, 0)],
                  dtype=[('a', int), ('b', int)])
        test = a.tolist()
        assert_equal(test, [[1, None], [3, 4]])
        # ... on mvoid
        a = a[0]
        test = a.tolist()
        assert_equal(test, [1, None])

    def test_tolist_specialcase(self):
        # Test mvoid.tolist: make sure we return a standard Python object
        a = array([(0, 1), (2, 3)], dtype=[('a', int), ('b', int)])
        # w/o mask: each entry is a np.void whose elements are standard Python
        for entry in a:
            for item in entry.tolist():
                assert_(not isinstance(item, np.generic))
        # w/ mask: each entry is a ma.void whose elements should be
        # standard Python
        a.mask[0] = (0, 1)
        for entry in a:
            for item in entry.tolist():
                assert_(not isinstance(item, np.generic))

    def test_toflex(self):
        # Test the conversion to records
        data = arange(10)
        record = data.toflex()
        assert_equal(record['_data'], data._data)
        assert_equal(record['_mask'], data._mask)

        data[[0, 1, 2, -1]] = masked
        record = data.toflex()
        assert_equal(record['_data'], data._data)
        assert_equal(record['_mask'], data._mask)

        ndtype = [('i', int), ('s', '|S3'), ('f', float)]
        data = array(list(zip(np.arange(10),
                              'ABCDEFGHIJKLM',
                              np.random.rand(10))),
                     dtype=ndtype)
        data[[0, 1, 2, -1]] = masked
        record = data.toflex()
        assert_equal(record['_data'], data._data)
        assert_equal(record['_mask'], data._mask)

        ndtype = np.dtype("int, (2,3)float, float")
        data = array(list(zip(np.arange(10),
                              np.random.rand(10),
                              np.random.rand(10))),
                     dtype=ndtype)
        data[[0, 1, 2, -1]] = masked
        record = data.toflex()
        assert_equal_records(record['_data'], data._data)
        assert_equal_records(record['_mask'], data._mask)

    def test_fromflex(self):
        # Test the reconstruction of a masked_array from a record
        a = array([1, 2, 3])
        test = fromflex(a.toflex())
        assert_equal(test, a)
        assert_equal(test.mask, a.mask)

        a = array([1, 2, 3], mask=[0, 0, 1])
        test = fromflex(a.toflex())
        assert_equal(test, a)
        assert_equal(test.mask, a.mask)

        a = array([(1, 1.), (2, 2.), (3, 3.)], mask=[(1, 0), (0, 0), (0, 1)],
                  dtype=[('A', int), ('B', float)])
        test = fromflex(a.toflex())
        assert_equal(test, a)
        assert_equal(test.data, a.data)

    def test_arraymethod(self):
        # Test a _arraymethod w/ n argument
        marray = masked_array([[1, 2, 3, 4, 5]], mask=[0, 0, 1, 0, 0])
        control = masked_array([[1], [2], [3], [4], [5]],
                               mask=[0, 0, 1, 0, 0])
        assert_equal(marray.T, control)
        assert_equal(marray.transpose(), control)

        assert_equal(MaskedArray.cumsum(marray.T, 0), control.cumsum(0))

    def test_arraymethod_0d(self):
        # gh-9430
        x = np.ma.array(42, mask=True)
        assert_equal(x.T.mask, x.mask)
        assert_equal(x.T.data, x.data)

    def test_transpose_view(self):
        x = np.ma.array([[1, 2, 3], [4, 5, 6]])
        x[0, 1] = np.ma.masked
        xt = x.T

        xt[1, 0] = 10
        xt[0, 1] = np.ma.masked

        assert_equal(x.data, xt.T.data)
        assert_equal(x.mask, xt.T.mask)

    def test_diagonal_view(self):
        x = np.ma.zeros((3, 3))
        x[0, 0] = 10
        x[1, 1] = np.ma.masked
        x[2, 2] = 20
        xd = x.diagonal()
        x[1, 1] = 15
        assert_equal(xd.mask, x.diagonal().mask)
        assert_equal(xd.data, x.diagonal().data)


class TestMaskedArrayMathMethods:

    def setup_method(self):
        # Base data definition.
        x = np.array([8.375, 7.545, 8.828, 8.5, 1.757, 5.928,
                      8.43, 7.78, 9.865, 5.878, 8.979, 4.732,
                      3.012, 6.022, 5.095, 3.116, 5.238, 3.957,
                      6.04, 9.63, 7.712, 3.382, 4.489, 6.479,
                      7.189, 9.645, 5.395, 4.961, 9.894, 2.893,
                      7.357, 9.828, 6.272, 3.758, 6.693, 0.993])
        X = x.reshape(6, 6)
        XX = x.reshape(3, 2, 2, 3)

        m = np.array([0, 1, 0, 1, 0, 0,
                     1, 0, 1, 1, 0, 1,
                     0, 0, 0, 1, 0, 1,
                     0, 0, 0, 1, 1, 1,
                     1, 0, 0, 1, 0, 0,
                     0, 0, 1, 0, 1, 0])
        mx = array(data=x, mask=m)
        mX = array(data=X, mask=m.reshape(X.shape))
        mXX = array(data=XX, mask=m.reshape(XX.shape))

        m2 = np.array([1, 1, 0, 1, 0, 0,
                      1, 1, 1, 1, 0, 1,
                      0, 0, 1, 1, 0, 1,
                      0, 0, 0, 1, 1, 1,
                      1, 0, 0, 1, 1, 0,
                      0, 0, 1, 0, 1, 1])
        m2x = array(data=x, mask=m2)
        m2X = array(data=X, mask=m2.reshape(X.shape))
        m2XX = array(data=XX, mask=m2.reshape(XX.shape))
        self.d = (x, X, XX, m, mx, mX, mXX, m2x, m2X, m2XX)

    def test_cumsumprod(self):
        # Tests cumsum & cumprod on MaskedArrays.
        (x, X, XX, m, mx, mX, mXX, m2x, m2X, m2XX) = self.d
        mXcp = mX.cumsum(0)
        assert_equal(mXcp._data, mX.filled(0).cumsum(0))
        mXcp = mX.cumsum(1)
        assert_equal(mXcp._data, mX.filled(0).cumsum(1))

        mXcp = mX.cumprod(0)
        assert_equal(mXcp._data, mX.filled(1).cumprod(0))
        mXcp = mX.cumprod(1)
        assert_equal(mXcp._data, mX.filled(1).cumprod(1))

    def test_cumsumprod_with_output(self):
        # Tests cumsum/cumprod w/ output
        xm = array(np.random.uniform(0, 10, 12)).reshape(3, 4)
        xm[:, 0] = xm[0] = xm[-1, -1] = masked

        for funcname in ('cumsum', 'cumprod'):
            npfunc = getattr(np, funcname)
            xmmeth = getattr(xm, funcname)

            # A ndarray as explicit input
            output = np.empty((3, 4), dtype=float)
            output.fill(-9999)
            result = npfunc(xm, axis=0, out=output)
            # ... the result should be the given output
            assert_(result is output)
            assert_equal(result, xmmeth(axis=0, out=output))

            output = empty((3, 4), dtype=int)
            result = xmmeth(axis=0, out=output)
            assert_(result is output)

    def test_ptp(self):
        # Tests ptp on MaskedArrays.
        (x, X, XX, m, mx, mX, mXX, m2x, m2X, m2XX) = self.d
        (n, m) = X.shape
        assert_equal(mx.ptp(), np.ptp(mx.compressed()))
        rows = np.zeros(n, float)
        cols = np.zeros(m, float)
        for k in range(m):
            cols[k] = np.ptp(mX[:, k].compressed())
        for k in range(n):
            rows[k] = np.ptp(mX[k].compressed())
        assert_equal(mX.ptp(0), cols)
        assert_equal(mX.ptp(1), rows)

    def test_add_object(self):
        x = masked_array(['a', 'b'], mask=[1, 0], dtype=object)
        y = x + 'x'
        assert_equal(y[1], 'bx')
        assert_(y.mask[0])

    def test_sum_object(self):
        # Test sum on object dtype
        a = masked_array([1, 2, 3], mask=[1, 0, 0], dtype=object)
        assert_equal(a.sum(), 5)
        a = masked_array([[1, 2, 3], [4, 5, 6]], dtype=object)
        assert_equal(a.sum(axis=0), [5, 7, 9])

    def test_prod_object(self):
        # Test prod on object dtype
        a = masked_array([1, 2, 3], mask=[1, 0, 0], dtype=object)
        assert_equal(a.prod(), 2 * 3)
        a = masked_array([[1, 2, 3], [4, 5, 6]], dtype=object)
        assert_equal(a.prod(axis=0), [4, 10, 18])

    def test_meananom_object(self):
        # Test mean/anom on object dtype
        a = masked_array([1, 2, 3], dtype=object)
        assert_equal(a.mean(), 2)
        assert_equal(a.anom(), [-1, 0, 1])

    def test_anom_shape(self):
        a = masked_array([1, 2, 3])
        assert_equal(a.anom().shape, a.shape)
        a.mask = True
        assert_equal(a.anom().shape, a.shape)
        assert_(np.ma.is_masked(a.anom()))

    def test_anom(self):
        a = masked_array(np.arange(1, 7).reshape(2, 3))
        assert_almost_equal(a.anom(),
                            [[-2.5, -1.5, -0.5], [0.5, 1.5, 2.5]])
        assert_almost_equal(a.anom(axis=0),
                            [[-1.5, -1.5, -1.5], [1.5, 1.5, 1.5]])
        assert_almost_equal(a.anom(axis=1),
                            [[-1., 0., 1.], [-1., 0., 1.]])
        a.mask = [[0, 0, 1], [0, 1, 0]]
        mval = -99
        assert_almost_equal(a.anom().filled(mval),
                            [[-2.25, -1.25, mval], [0.75, mval, 2.75]])
        assert_almost_equal(a.anom(axis=0).filled(mval),
                            [[-1.5, 0.0, mval], [1.5, mval, 0.0]])
        assert_almost_equal(a.anom(axis=1).filled(mval),
                            [[-0.5, 0.5, mval], [-1.0, mval, 1.0]])

    def test_trace(self):
        # Tests trace on MaskedArrays.
        (x, X, XX, m, mx, mX, mXX, m2x, m2X, m2XX) = self.d
        mXdiag = mX.diagonal()
        assert_equal(mX.trace(), mX.diagonal().compressed().sum())
        assert_almost_equal(mX.trace(),
                            X.trace() - sum(mXdiag.mask * X.diagonal(),
                                            axis=0))
        assert_equal(np.trace(mX), mX.trace())

        # gh-5560
        arr = np.arange(2 * 4 * 4).reshape(2, 4, 4)
        m_arr = np.ma.masked_array(arr, False)
        assert_equal(arr.trace(axis1=1, axis2=2), m_arr.trace(axis1=1, axis2=2))

    def test_dot(self):
        # Tests dot on MaskedArrays.
        (x, X, XX, m, mx, mX, mXX, m2x, m2X, m2XX) = self.d
        fx = mx.filled(0)
        r = mx.dot(mx)
        assert_almost_equal(r.filled(0), fx.dot(fx))
        assert_(r.mask is nomask)

        fX = mX.filled(0)
        r = mX.dot(mX)
        assert_almost_equal(r.filled(0), fX.dot(fX))
        assert_(r.mask[1, 3])
        r1 = empty_like(r)
        mX.dot(mX, out=r1)
        assert_almost_equal(r, r1)

        mYY = mXX.swapaxes(-1, -2)
        fXX, fYY = mXX.filled(0), mYY.filled(0)
        r = mXX.dot(mYY)
        assert_almost_equal(r.filled(0), fXX.dot(fYY))
        r1 = empty_like(r)
        mXX.dot(mYY, out=r1)
        assert_almost_equal(r, r1)

    def test_dot_shape_mismatch(self):
        # regression test
        x = masked_array([[1, 2], [3, 4]], mask=[[0, 1], [0, 0]])
        y = masked_array([[1, 2], [3, 4]], mask=[[0, 1], [0, 0]])
        z = masked_array([[0, 1], [3, 3]])
        x.dot(y, out=z)
        assert_almost_equal(z.filled(0), [[1, 0], [15, 16]])
        assert_almost_equal(z.mask, [[0, 1], [0, 0]])

    def test_varmean_nomask(self):
        # gh-5769
        foo = array([1, 2, 3, 4], dtype='f8')
        bar = array([1, 2, 3, 4], dtype='f8')
        assert_equal(type(foo.mean()), np.float64)
        assert_equal(type(foo.var()), np.float64)
        assert (foo.mean() == bar.mean()) is np.bool(True)

        # check array type is preserved and out works
        foo = array(np.arange(16).reshape((4, 4)), dtype='f8')
        bar = empty(4, dtype='f4')
        assert_equal(type(foo.mean(axis=1)), MaskedArray)
        assert_equal(type(foo.var(axis=1)), MaskedArray)
        assert_(foo.mean(axis=1, out=bar) is bar)
        assert_(foo.var(axis=1, out=bar) is bar)

    def test_varstd(self):
        # Tests var & std on MaskedArrays.
        (x, X, XX, m, mx, mX, mXX, m2x, m2X, m2XX) = self.d
        assert_almost_equal(mX.var(axis=None), mX.compressed().var())
        assert_almost_equal(mX.std(axis=None), mX.compressed().std())
        assert_almost_equal(mX.std(axis=None, ddof=1),
                            mX.compressed().std(ddof=1))
        assert_almost_equal(mX.var(axis=None, ddof=1),
                            mX.compressed().var(ddof=1))
        assert_equal(mXX.var(axis=3).shape, XX.var(axis=3).shape)
        assert_equal(mX.var().shape, X.var().shape)
        (mXvar0, mXvar1) = (mX.var(axis=0), mX.var(axis=1))
        assert_almost_equal(mX.var(axis=None, ddof=2),
                            mX.compressed().var(ddof=2))
        assert_almost_equal(mX.std(axis=None, ddof=2),
                            mX.compressed().std(ddof=2))
        for k in range(6):
            assert_almost_equal(mXvar1[k], mX[k].compressed().var())
            assert_almost_equal(mXvar0[k], mX[:, k].compressed().var())
            assert_almost_equal(np.sqrt(mXvar0[k]),
                                mX[:, k].compressed().std())

    @suppress_copy_mask_on_assignment
    def test_varstd_specialcases(self):
        # Test a special case for var
        nout = np.array(-1, dtype=float)
        mout = array(-1, dtype=float)

        x = array(arange(10), mask=True)
        for methodname in ('var', 'std'):
            method = getattr(x, methodname)
            assert_(method() is masked)
            assert_(method(0) is masked)
            assert_(method(-1) is masked)
            # Using a masked array as explicit output
            method(out=mout)
            assert_(mout is not masked)
            assert_equal(mout.mask, True)
            # Using a ndarray as explicit output
            method(out=nout)
            assert_(np.isnan(nout))

        x = array(arange(10), mask=True)
        x[-1] = 9
        for methodname in ('var', 'std'):
            method = getattr(x, methodname)
            assert_(method(ddof=1) is masked)
            assert_(method(0, ddof=1) is masked)
            assert_(method(-1, ddof=1) is masked)
            # Using a masked array as explicit output
            method(out=mout, ddof=1)
            assert_(mout is not masked)
            assert_equal(mout.mask, True)
            # Using a ndarray as explicit output
            method(out=nout, ddof=1)
            assert_(np.isnan(nout))

    def test_varstd_ddof(self):
        a = array([[1, 1, 0], [1, 1, 0]], mask=[[0, 0, 1], [0, 0, 1]])
        test = a.std(axis=0, ddof=0)
        assert_equal(test.filled(0), [0, 0, 0])
        assert_equal(test.mask, [0, 0, 1])
        test = a.std(axis=0, ddof=1)
        assert_equal(test.filled(0), [0, 0, 0])
        assert_equal(test.mask, [0, 0, 1])
        test = a.std(axis=0, ddof=2)
        assert_equal(test.filled(0), [0, 0, 0])
        assert_equal(test.mask, [1, 1, 1])

    def test_diag(self):
        # Test diag
        x = arange(9).reshape((3, 3))
        x[1, 1] = masked
        out = np.diag(x)
        assert_equal(out, [0, 4, 8])
        out = diag(x)
        assert_equal(out, [0, 4, 8])
        assert_equal(out.mask, [0, 1, 0])
        out = diag(out)
        control = array([[0, 0, 0], [0, 4, 0], [0, 0, 8]],
                        mask=[[0, 0, 0], [0, 1, 0], [0, 0, 0]])
        assert_equal(out, control)

    def test_axis_methods_nomask(self):
        # Test the combination nomask & methods w/ axis
        a = array([[1, 2, 3], [4, 5, 6]])

        assert_equal(a.sum(0), [5, 7, 9])
        assert_equal(a.sum(-1), [6, 15])
        assert_equal(a.sum(1), [6, 15])

        assert_equal(a.prod(0), [4, 10, 18])
        assert_equal(a.prod(-1), [6, 120])
        assert_equal(a.prod(1), [6, 120])

        assert_equal(a.min(0), [1, 2, 3])
        assert_equal(a.min(-1), [1, 4])
        assert_equal(a.min(1), [1, 4])

        assert_equal(a.max(0), [4, 5, 6])
        assert_equal(a.max(-1), [3, 6])
        assert_equal(a.max(1), [3, 6])

    @requires_memory(free_bytes=2 * 10000 * 1000 * 2)
    def test_mean_overflow(self):
        # Test overflow in masked arrays
        # gh-20272
        a = masked_array(np.full((10000, 10000), 65535, dtype=np.uint16),
                         mask=np.zeros((10000, 10000)))
        assert_equal(a.mean(), 65535.0)

    def test_diff_with_prepend(self):
        # GH 22465
        x = np.array([1, 2, 2, 3, 4, 2, 1, 1])

        a = np.ma.masked_equal(x[3:], value=2)
        a_prep = np.ma.masked_equal(x[:3], value=2)
        diff1 = np.ma.diff(a, prepend=a_prep, axis=0)

        b = np.ma.masked_equal(x, value=2)
        diff2 = np.ma.diff(b, axis=0)

        assert_(np.ma.allequal(diff1, diff2))

    def test_diff_with_append(self):
        # GH 22465
        x = np.array([1, 2, 2, 3, 4, 2, 1, 1])

        a = np.ma.masked_equal(x[:3], value=2)
        a_app = np.ma.masked_equal(x[3:], value=2)
        diff1 = np.ma.diff(a, append=a_app, axis=0)

        b = np.ma.masked_equal(x, value=2)
        diff2 = np.ma.diff(b, axis=0)

        assert_(np.ma.allequal(diff1, diff2))

    def test_diff_with_dim_0(self):
        with pytest.raises(
            ValueError,
            match="diff requires input that is at least one dimensional"
            ):
            np.ma.diff(np.array(1))

    def test_diff_with_n_0(self):
        a = np.ma.masked_equal([1, 2, 2, 3, 4, 2, 1, 1], value=2)
        diff = np.ma.diff(a, n=0, axis=0)

        assert_(np.ma.allequal(a, diff))


class TestMaskedArrayMathMethodsComplex:
    # Test class for miscellaneous MaskedArrays methods.
    def setup_method(self):
        # Base data definition.
        x = np.array([8.375j, 7.545j, 8.828j, 8.5j, 1.757j, 5.928,
                      8.43, 7.78, 9.865, 5.878, 8.979, 4.732,
                      3.012, 6.022, 5.095, 3.116, 5.238, 3.957,
                      6.04, 9.63, 7.712, 3.382, 4.489, 6.479j,
                      7.189j, 9.645, 5.395, 4.961, 9.894, 2.893,
                      7.357, 9.828, 6.272, 3.758, 6.693, 0.993j])
        X = x.reshape(6, 6)
        XX = x.reshape(3, 2, 2, 3)

        m = np.array([0, 1, 0, 1, 0, 0,
                     1, 0, 1, 1, 0, 1,
                     0, 0, 0, 1, 0, 1,
                     0, 0, 0, 1, 1, 1,
                     1, 0, 0, 1, 0, 0,
                     0, 0, 1, 0, 1, 0])
        mx = array(data=x, mask=m)
        mX = array(data=X, mask=m.reshape(X.shape))
        mXX = array(data=XX, mask=m.reshape(XX.shape))

        m2 = np.array([1, 1, 0, 1, 0, 0,
                      1, 1, 1, 1, 0, 1,
                      0, 0, 1, 1, 0, 1,
                      0, 0, 0, 1, 1, 1,
                      1, 0, 0, 1, 1, 0,
                      0, 0, 1, 0, 1, 1])
        m2x = array(data=x, mask=m2)
        m2X = array(data=X, mask=m2.reshape(X.shape))
        m2XX = array(data=XX, mask=m2.reshape(XX.shape))
        self.d = (x, X, XX, m, mx, mX, mXX, m2x, m2X, m2XX)

    def test_varstd(self):
        # Tests var & std on MaskedArrays.
        (x, X, XX, m, mx, mX, mXX, m2x, m2X, m2XX) = self.d
        assert_almost_equal(mX.var(axis=None), mX.compressed().var())
        assert_almost_equal(mX.std(axis=None), mX.compressed().std())
        assert_equal(mXX.var(axis=3).shape, XX.var(axis=3).shape)
        assert_equal(mX.var().shape, X.var().shape)
        (mXvar0, mXvar1) = (mX.var(axis=0), mX.var(axis=1))
        assert_almost_equal(mX.var(axis=None, ddof=2),
                            mX.compressed().var(ddof=2))
        assert_almost_equal(mX.std(axis=None, ddof=2),
                            mX.compressed().std(ddof=2))
        for k in range(6):
            assert_almost_equal(mXvar1[k], mX[k].compressed().var())
            assert_almost_equal(mXvar0[k], mX[:, k].compressed().var())
            assert_almost_equal(np.sqrt(mXvar0[k]),
                                mX[:, k].compressed().std())


class TestMaskedArrayFunctions:
    # Test class for miscellaneous functions.

    def setup_method(self):
        x = np.array([1., 1., 1., -2., pi / 2.0, 4., 5., -10., 10., 1., 2., 3.])
        y = np.array([5., 0., 3., 2., -1., -4., 0., -10., 10., 1., 0., 3.])
        m1 = [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0]
        m2 = [0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1]
        xm = masked_array(x, mask=m1)
        ym = masked_array(y, mask=m2)
        xm.set_fill_value(1e+20)
        self.info = (xm, ym)

    def test_masked_where_bool(self):
        x = [1, 2]
        y = masked_where(False, x)
        assert_equal(y, [1, 2])
        assert_equal(y[1], 2)

    def test_masked_equal_wlist(self):
        x = [1, 2, 3]
        mx = masked_equal(x, 3)
        assert_equal(mx, x)
        assert_equal(mx._mask, [0, 0, 1])
        mx = masked_not_equal(x, 3)
        assert_equal(mx, x)
        assert_equal(mx._mask, [1, 1, 0])

    def test_masked_equal_fill_value(self):
        x = [1, 2, 3]
        mx = masked_equal(x, 3)
        assert_equal(mx._mask, [0, 0, 1])
        assert_equal(mx.fill_value, 3)

    def test_masked_where_condition(self):
        # Tests masking functions.
        x = array([1., 2., 3., 4., 5.])
        x[2] = masked
        assert_equal(masked_where(greater(x, 2), x), masked_greater(x, 2))
        assert_equal(masked_where(greater_equal(x, 2), x),
                     masked_greater_equal(x, 2))
        assert_equal(masked_where(less(x, 2), x), masked_less(x, 2))
        assert_equal(masked_where(less_equal(x, 2), x),
                     masked_less_equal(x, 2))
        assert_equal(masked_where(not_equal(x, 2), x), masked_not_equal(x, 2))
        assert_equal(masked_where(equal(x, 2), x), masked_equal(x, 2))
        assert_equal(masked_where(not_equal(x, 2), x), masked_not_equal(x, 2))
        assert_equal(masked_where([1, 1, 0, 0, 0], [1, 2, 3, 4, 5]),
                     [99, 99, 3, 4, 5])

    def test_masked_where_oddities(self):
        # Tests some generic features.
        atest = ones((10, 10, 10), dtype=float)
        btest = zeros(atest.shape, MaskType)
        ctest = masked_where(btest, atest)
        assert_equal(atest, ctest)

    def test_masked_where_shape_constraint(self):
        a = arange(10)
        with assert_raises(IndexError):
            masked_equal(1, a)
        test = masked_equal(a, 1)
        assert_equal(test.mask, [0, 1, 0, 0, 0, 0, 0, 0, 0, 0])

    def test_masked_where_structured(self):
        # test that masked_where on a structured array sets a structured
        # mask (see issue #2972)
        a = np.zeros(10, dtype=[("A", "<f2"), ("B", "<f4")])
        with np.errstate(over="ignore"):
            # NOTE: The float16 "uses" 1e20 as mask, which overflows to inf
            #       and warns.  Unrelated to this test, but probably undesired.
            #       But NumPy previously did not warn for this overflow.
            am = np.ma.masked_where(a["A"] < 5, a)
        assert_equal(am.mask.dtype.names, am.dtype.names)
        assert_equal(am["A"],
                    np.ma.masked_array(np.zeros(10), np.ones(10)))

    def test_masked_where_mismatch(self):
        # gh-4520
        x = np.arange(10)
        y = np.arange(5)
        assert_raises(IndexError, np.ma.masked_where, y > 6, x)

    def test_masked_otherfunctions(self):
        assert_equal(masked_inside(list(range(5)), 1, 3),
                     [0, 199, 199, 199, 4])
        assert_equal(masked_outside(list(range(5)), 1, 3), [199, 1, 2, 3, 199])
        assert_equal(masked_inside(array(list(range(5)),
                                         mask=[1, 0, 0, 0, 0]), 1, 3).mask,
                     [1, 1, 1, 1, 0])
        assert_equal(masked_outside(array(list(range(5)),
                                          mask=[0, 1, 0, 0, 0]), 1, 3).mask,
                     [1, 1, 0, 0, 1])
        assert_equal(masked_equal(array(list(range(5)),
                                        mask=[1, 0, 0, 0, 0]), 2).mask,
                     [1, 0, 1, 0, 0])
        assert_equal(masked_not_equal(array([2, 2, 1, 2, 1],
                                            mask=[1, 0, 0, 0, 0]), 2).mask,
                     [1, 0, 1, 0, 1])

    def test_round(self):
        a = array([1.23456, 2.34567, 3.45678, 4.56789, 5.67890],
                  mask=[0, 1, 0, 0, 0])
        assert_equal(a.round(), [1., 2., 3., 5., 6.])
        assert_equal(a.round(1), [1.2, 2.3, 3.5, 4.6, 5.7])
        assert_equal(a.round(3), [1.235, 2.346, 3.457, 4.568, 5.679])
        b = empty_like(a)
        a.round(out=b)
        assert_equal(b, [1., 2., 3., 5., 6.])

        x = array([1., 2., 3., 4., 5.])
        c = array([1, 1, 1, 0, 0])
        x[2] = masked
        z = where(c, x, -x)
        assert_equal(z, [1., 2., 0., -4., -5])
        c[0] = masked
        z = where(c, x, -x)
        assert_equal(z, [1., 2., 0., -4., -5])
        assert_(z[0] is masked)
        assert_(z[1] is not masked)
        assert_(z[2] is masked)

    def test_round_with_output(self):
        # Testing round with an explicit output

        xm = array(np.random.uniform(0, 10, 12)).reshape(3, 4)
        xm[:, 0] = xm[0] = xm[-1, -1] = masked

        # A ndarray as explicit input
        output = np.empty((3, 4), dtype=float)
        output.fill(-9999)
        result = np.round(xm, decimals=2, out=output)
        # ... the result should be the given output
        assert_(result is output)
        assert_equal(result, xm.round(decimals=2, out=output))

        output = empty((3, 4), dtype=float)
        result = xm.round(decimals=2, out=output)
        assert_(result is output)

    def test_round_with_scalar(self):
        # Testing round with scalar/zero dimension input
        # GH issue 2244
        a = array(1.1, mask=[False])
        assert_equal(a.round(), 1)

        a = array(1.1, mask=[True])
        assert_(a.round() is masked)

        a = array(1.1, mask=[False])
        output = np.empty(1, dtype=float)
        output.fill(-9999)
        a.round(out=output)
        assert_equal(output, 1)

        a = array(1.1, mask=[False])
        output = array(-9999., mask=[True])
        a.round(out=output)
        assert_equal(output[()], 1)

        a = array(1.1, mask=[True])
        output = array(-9999., mask=[False])
        a.round(out=output)
        assert_(output[()] is masked)

    def test_identity(self):
        a = identity(5)
        assert_(isinstance(a, MaskedArray))
        assert_equal(a, np.identity(5))

    def test_power(self):
        x = -1.1
        assert_almost_equal(power(x, 2.), 1.21)
        assert_(power(x, masked) is masked)
        x = array([-1.1, -1.1, 1.1, 1.1, 0.])
        b = array([0.5, 2., 0.5, 2., -1.], mask=[0, 0, 0, 0, 1])
        y = power(x, b)
        assert_almost_equal(y, [0, 1.21, 1.04880884817, 1.21, 0.])
        assert_equal(y._mask, [1, 0, 0, 0, 1])
        b.mask = nomask
        y = power(x, b)
        assert_equal(y._mask, [1, 0, 0, 0, 1])
        z = x ** b
        assert_equal(z._mask, y._mask)
        assert_almost_equal(z, y)
        assert_almost_equal(z._data, y._data)
        x **= b
        assert_equal(x._mask, y._mask)
        assert_almost_equal(x, y)
        assert_almost_equal(x._data, y._data)

    def test_power_with_broadcasting(self):
        # Test power w/ broadcasting
        a2 = np.array([[1., 2., 3.], [4., 5., 6.]])
        a2m = array(a2, mask=[[1, 0, 0], [0, 0, 1]])
        b1 = np.array([2, 4, 3])
        b2 = np.array([b1, b1])
        b2m = array(b2, mask=[[0, 1, 0], [0, 1, 0]])

        ctrl = array([[1 ** 2, 2 ** 4, 3 ** 3], [4 ** 2, 5 ** 4, 6 ** 3]],
                     mask=[[1, 1, 0], [0, 1, 1]])
        # No broadcasting, base & exp w/ mask
        test = a2m ** b2m
        assert_equal(test, ctrl)
        assert_equal(test.mask, ctrl.mask)
        # No broadcasting, base w/ mask, exp w/o mask
        test = a2m ** b2
        assert_equal(test, ctrl)
        assert_equal(test.mask, a2m.mask)
        # No broadcasting, base w/o mask, exp w/ mask
        test = a2 ** b2m
        assert_equal(test, ctrl)
        assert_equal(test.mask, b2m.mask)

        ctrl = array([[2 ** 2, 4 ** 4, 3 ** 3], [2 ** 2, 4 ** 4, 3 ** 3]],
                     mask=[[0, 1, 0], [0, 1, 0]])
        test = b1 ** b2m
        assert_equal(test, ctrl)
        assert_equal(test.mask, ctrl.mask)
        test = b2m ** b1
        assert_equal(test, ctrl)
        assert_equal(test.mask, ctrl.mask)

    @pytest.mark.skipif(IS_WASM, reason="fp errors don't work in wasm")
    def test_where(self):
        # Test the where function
        x = np.array([1., 1., 1., -2., pi / 2.0, 4., 5., -10., 10., 1., 2., 3.])
        y = np.array([5., 0., 3., 2., -1., -4., 0., -10., 10., 1., 0., 3.])
        m1 = [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0]
        m2 = [0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1]
        xm = masked_array(x, mask=m1)
        ym = masked_array(y, mask=m2)
        xm.set_fill_value(1e+20)

        d = where(xm > 2, xm, -9)
        assert_equal(d, [-9., -9., -9., -9., -9., 4.,
                         -9., -9., 10., -9., -9., 3.])
        assert_equal(d._mask, xm._mask)
        d = where(xm > 2, -9, ym)
        assert_equal(d, [5., 0., 3., 2., -1., -9.,
                         -9., -10., -9., 1., 0., -9.])
        assert_equal(d._mask, [1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0])
        d = where(xm > 2, xm, masked)
        assert_equal(d, [-9., -9., -9., -9., -9., 4.,
                         -9., -9., 10., -9., -9., 3.])
        tmp = xm._mask.copy()
        tmp[(xm <= 2).filled(True)] = True
        assert_equal(d._mask, tmp)

        with np.errstate(invalid="warn"):
            # The fill value is 1e20, it cannot be converted to `int`:
            with pytest.warns(RuntimeWarning, match="invalid value"):
                ixm = xm.astype(int)
        d = where(ixm > 2, ixm, masked)
        assert_equal(d, [-9, -9, -9, -9, -9, 4, -9, -9, 10, -9, -9, 3])
        assert_equal(d.dtype, ixm.dtype)

    def test_where_object(self):
        a = np.array(None)
        b = masked_array(None)
        r = b.copy()
        assert_equal(np.ma.where(True, a, a), r)
        assert_equal(np.ma.where(True, b, b), r)

    def test_where_with_masked_choice(self):
        x = arange(10)
        x[3] = masked
        c = x >= 8
        # Set False to masked
        z = where(c, x, masked)
        assert_(z.dtype is x.dtype)
        assert_(z[3] is masked)
        assert_(z[4] is masked)
        assert_(z[7] is masked)
        assert_(z[8] is not masked)
        assert_(z[9] is not masked)
        assert_equal(x, z)
        # Set True to masked
        z = where(c, masked, x)
        assert_(z.dtype is x.dtype)
        assert_(z[3] is masked)
        assert_(z[4] is not masked)
        assert_(z[7] is not masked)
        assert_(z[8] is masked)
        assert_(z[9] is masked)

    def test_where_with_masked_condition(self):
        x = array([1., 2., 3., 4., 5.])
        c = array([1, 1, 1, 0, 0])
        x[2] = masked
        z = where(c, x, -x)
        assert_equal(z, [1., 2., 0., -4., -5])
        c[0] = masked
        z = where(c, x, -x)
        assert_equal(z, [1., 2., 0., -4., -5])
        assert_(z[0] is masked)
        assert_(z[1] is not masked)
        assert_(z[2] is masked)

        x = arange(1, 6)
        x[-1] = masked
        y = arange(1, 6) * 10
        y[2] = masked
        c = array([1, 1, 1, 0, 0], mask=[1, 0, 0, 0, 0])
        cm = c.filled(1)
        z = where(c, x, y)
        zm = where(cm, x, y)
        assert_equal(z, zm)
        assert_(getmask(zm) is nomask)
        assert_equal(zm, [1, 2, 3, 40, 50])
        z = where(c, masked, 1)
        assert_equal(z, [99, 99, 99, 1, 1])
        z = where(c, 1, masked)
        assert_equal(z, [99, 1, 1, 99, 99])

    def test_where_type(self):
        # Test the type conservation with where
        x = np.arange(4, dtype=np.int32)
        y = np.arange(4, dtype=np.float32) * 2.2
        test = where(x > 1.5, y, x).dtype
        control = np.result_type(np.int32, np.float32)
        assert_equal(test, control)

    def test_where_broadcast(self):
        # Issue 8599
        x = np.arange(9).reshape(3, 3)
        y = np.zeros(3)
        core = np.where([1, 0, 1], x, y)
        ma = where([1, 0, 1], x, y)

        assert_equal(core, ma)
        assert_equal(core.dtype, ma.dtype)

    def test_where_structured(self):
        # Issue 8600
        dt = np.dtype([('a', int), ('b', int)])
        x = np.array([(1, 2), (3, 4), (5, 6)], dtype=dt)
        y = np.array((10, 20), dtype=dt)
        core = np.where([0, 1, 1], x, y)
        ma = np.where([0, 1, 1], x, y)

        assert_equal(core, ma)
        assert_equal(core.dtype, ma.dtype)

    def test_where_structured_masked(self):
        dt = np.dtype([('a', int), ('b', int)])
        x = np.array([(1, 2), (3, 4), (5, 6)], dtype=dt)

        ma = where([0, 1, 1], x, masked)
        expected = masked_where([1, 0, 0], x)

        assert_equal(ma.dtype, expected.dtype)
        assert_equal(ma, expected)
        assert_equal(ma.mask, expected.mask)

    def test_masked_invalid_error(self):
        a = np.arange(5, dtype=object)
        a[3] = np.inf
        a[2] = np.nan
        with pytest.raises(TypeError,
                           match="not supported for the input types"):
            np.ma.masked_invalid(a)

    def test_masked_invalid_pandas(self):
        # getdata() used to be bad for pandas series due to its _data
        # attribute.  This test is a regression test mainly and may be
        # removed if getdata() is adjusted.
        class Series:
            _data = "nonsense"

            def __array__(self, dtype=None, copy=None):
                return np.array([5, np.nan, np.inf])

        arr = np.ma.masked_invalid(Series())
        assert_array_equal(arr._data, np.array(Series()))
        assert_array_equal(arr._mask, [False, True, True])

    @pytest.mark.parametrize("copy", [True, False])
    def test_masked_invalid_full_mask(self, copy):
        # Matplotlib relied on masked_invalid always returning a full mask
        # (Also astropy projects, but were ok with it gh-22720 and gh-22842)
        a = np.ma.array([1, 2, 3, 4])
        assert a._mask is nomask
        res = np.ma.masked_invalid(a, copy=copy)
        assert res.mask is not nomask
        # mask of a should not be mutated
        assert a.mask is nomask
        assert np.may_share_memory(a._data, res._data) != copy

    def test_choose(self):
        # Test choose
        choices = [[0, 1, 2, 3], [10, 11, 12, 13],
                   [20, 21, 22, 23], [30, 31, 32, 33]]
        chosen = choose([2, 3, 1, 0], choices)
        assert_equal(chosen, array([20, 31, 12, 3]))
        chosen = choose([2, 4, 1, 0], choices, mode='clip')
        assert_equal(chosen, array([20, 31, 12, 3]))
        chosen = choose([2, 4, 1, 0], choices, mode='wrap')
        assert_equal(chosen, array([20, 1, 12, 3]))
        # Check with some masked indices
        indices_ = array([2, 4, 1, 0], mask=[1, 0, 0, 1])
        chosen = choose(indices_, choices, mode='wrap')
        assert_equal(chosen, array([99, 1, 12, 99]))
        assert_equal(chosen.mask, [1, 0, 0, 1])
        # Check with some masked choices
        choices = array(choices, mask=[[0, 0, 0, 1], [1, 1, 0, 1],
                                       [1, 0, 0, 0], [0, 0, 0, 0]])
        indices_ = [2, 3, 1, 0]
        chosen = choose(indices_, choices, mode='wrap')
        assert_equal(chosen, array([20, 31, 12, 3]))
        assert_equal(chosen.mask, [1, 0, 0, 1])

    def test_choose_with_out(self):
        # Test choose with an explicit out keyword
        choices = [[0, 1, 2, 3], [10, 11, 12, 13],
                   [20, 21, 22, 23], [30, 31, 32, 33]]
        store = empty(4, dtype=int)
        chosen = choose([2, 3, 1, 0], choices, out=store)
        assert_equal(store, array([20, 31, 12, 3]))
        assert_(store is chosen)
        # Check with some masked indices + out
        store = empty(4, dtype=int)
        indices_ = array([2, 3, 1, 0], mask=[1, 0, 0, 1])
        chosen = choose(indices_, choices, mode='wrap', out=store)
        assert_equal(store, array([99, 31, 12, 99]))
        assert_equal(store.mask, [1, 0, 0, 1])
        # Check with some masked choices + out ina ndarray !
        choices = array(choices, mask=[[0, 0, 0, 1], [1, 1, 0, 1],
                                       [1, 0, 0, 0], [0, 0, 0, 0]])
        indices_ = [2, 3, 1, 0]
        store = empty(4, dtype=int).view(ndarray)
        chosen = choose(indices_, choices, mode='wrap', out=store)
        assert_equal(store, array([999999, 31, 12, 999999]))

    def test_reshape(self):
        a = arange(10)
        a[0] = masked
        # Try the default
        b = a.reshape((5, 2))
        assert_equal(b.shape, (5, 2))
        assert_(b.flags['C'])
        # Try w/ arguments as list instead of tuple
        b = a.reshape(5, 2)
        assert_equal(b.shape, (5, 2))
        assert_(b.flags['C'])
        # Try w/ order
        b = a.reshape((5, 2), order='F')
        assert_equal(b.shape, (5, 2))
        assert_(b.flags['F'])
        # Try w/ order
        b = a.reshape(5, 2, order='F')
        assert_equal(b.shape, (5, 2))
        assert_(b.flags['F'])

        c = np.reshape(a, (2, 5))
        assert_(isinstance(c, MaskedArray))
        assert_equal(c.shape, (2, 5))
        assert_(c[0, 0] is masked)
        assert_(c.flags['C'])

    def test_make_mask_descr(self):
        # Flexible
        ntype = [('a', float), ('b', float)]
        test = make_mask_descr(ntype)
        assert_equal(test, [('a', bool), ('b', bool)])
        assert_(test is make_mask_descr(test))

        # Standard w/ shape
        ntype = (float, 2)
        test = make_mask_descr(ntype)
        assert_equal(test, (bool, 2))
        assert_(test is make_mask_descr(test))

        # Standard standard
        ntype = float
        test = make_mask_descr(ntype)
        assert_equal(test, np.dtype(bool))
        assert_(test is make_mask_descr(test))

        # Nested
        ntype = [('a', float), ('b', [('ba', float), ('bb', float)])]
        test = make_mask_descr(ntype)
        control = np.dtype([('a', 'b1'), ('b', [('ba', 'b1'), ('bb', 'b1')])])
        assert_equal(test, control)
        assert_(test is make_mask_descr(test))

        # Named+ shape
        ntype = [('a', (float, 2))]
        test = make_mask_descr(ntype)
        assert_equal(test, np.dtype([('a', (bool, 2))]))
        assert_(test is make_mask_descr(test))

        # 2 names
        ntype = [(('A', 'a'), float)]
        test = make_mask_descr(ntype)
        assert_equal(test, np.dtype([(('A', 'a'), bool)]))
        assert_(test is make_mask_descr(test))

        # nested boolean types should preserve identity
        base_type = np.dtype([('a', int, 3)])
        base_mtype = make_mask_descr(base_type)
        sub_type = np.dtype([('a', int), ('b', base_mtype)])
        test = make_mask_descr(sub_type)
        assert_equal(test, np.dtype([('a', bool), ('b', [('a', bool, 3)])]))
        assert_(test.fields['b'][0] is base_mtype)

    def test_make_mask(self):
        # Test make_mask
        # w/ a list as an input
        mask = [0, 1]
        test = make_mask(mask)
        assert_equal(test.dtype, MaskType)
        assert_equal(test, [0, 1])
        # w/ a ndarray as an input
        mask = np.array([0, 1], dtype=bool)
        test = make_mask(mask)
        assert_equal(test.dtype, MaskType)
        assert_equal(test, [0, 1])
        # w/ a flexible-type ndarray as an input - use default
        mdtype = [('a', bool), ('b', bool)]
        mask = np.array([(0, 0), (0, 1)], dtype=mdtype)
        test = make_mask(mask)
        assert_equal(test.dtype, MaskType)
        assert_equal(test, [1, 1])
        # w/ a flexible-type ndarray as an input - use input dtype
        mdtype = [('a', bool), ('b', bool)]
        mask = np.array([(0, 0), (0, 1)], dtype=mdtype)
        test = make_mask(mask, dtype=mask.dtype)
        assert_equal(test.dtype, mdtype)
        assert_equal(test, mask)
        # w/ a flexible-type ndarray as an input - use input dtype
        mdtype = [('a', float), ('b', float)]
        bdtype = [('a', bool), ('b', bool)]
        mask = np.array([(0, 0), (0, 1)], dtype=mdtype)
        test = make_mask(mask, dtype=mask.dtype)
        assert_equal(test.dtype, bdtype)
        assert_equal(test, np.array([(0, 0), (0, 1)], dtype=bdtype))
        # Ensure this also works for void
        mask = np.array((False, True), dtype='?,?')[()]
        assert_(isinstance(mask, np.void))
        test = make_mask(mask, dtype=mask.dtype)
        assert_equal(test, mask)
        assert_(test is not mask)
        mask = np.array((0, 1), dtype='i4,i4')[()]
        test2 = make_mask(mask, dtype=mask.dtype)
        assert_equal(test2, test)
        # test that nomask is returned when m is nomask.
        bools = [True, False]
        dtypes = [MaskType, float]
        msgformat = 'copy=%s, shrink=%s, dtype=%s'
        for cpy, shr, dt in itertools.product(bools, bools, dtypes):
            res = make_mask(nomask, copy=cpy, shrink=shr, dtype=dt)
            assert_(res is nomask, msgformat % (cpy, shr, dt))

    def test_mask_or(self):
        # Initialize
        mtype = [('a', bool), ('b', bool)]
        mask = np.array([(0, 0), (0, 1), (1, 0), (0, 0)], dtype=mtype)
        # Test using nomask as input
        test = mask_or(mask, nomask)
        assert_equal(test, mask)
        test = mask_or(nomask, mask)
        assert_equal(test, mask)
        # Using False as input
        test = mask_or(mask, False)
        assert_equal(test, mask)
        # Using another array w / the same dtype
        other = np.array([(0, 1), (0, 1), (0, 1), (0, 1)], dtype=mtype)
        test = mask_or(mask, other)
        control = np.array([(0, 1), (0, 1), (1, 1), (0, 1)], dtype=mtype)
        assert_equal(test, control)
        # Using another array w / a different dtype
        othertype = [('A', bool), ('B', bool)]
        other = np.array([(0, 1), (0, 1), (0, 1), (0, 1)], dtype=othertype)
        try:
            test = mask_or(mask, other)
        except ValueError:
            pass
        # Using nested arrays
        dtype = [('a', bool), ('b', [('ba', bool), ('bb', bool)])]
        amask = np.array([(0, (1, 0)), (0, (1, 0))], dtype=dtype)
        bmask = np.array([(1, (0, 1)), (0, (0, 0))], dtype=dtype)
        cntrl = np.array([(1, (1, 1)), (0, (1, 0))], dtype=dtype)
        assert_equal(mask_or(amask, bmask), cntrl)

        a = np.array([False, False])
        assert mask_or(a, a) is nomask  # gh-27360

    def test_allequal(self):
        x = array([1, 2, 3], mask=[0, 0, 0])
        y = array([1, 2, 3], mask=[1, 0, 0])
        z = array([[1, 2, 3], [4, 5, 6]], mask=[[0, 0, 0], [1, 1, 1]])

        assert allequal(x, y)
        assert not allequal(x, y, fill_value=False)
        assert allequal(x, z)

        # test allequal for the same input, with mask=nomask, this test is for
        # the scenario raised in https://github.com/numpy/numpy/issues/27201
        assert allequal(x, x)
        assert allequal(x, x, fill_value=False)

        assert allequal(y, y)
        assert not allequal(y, y, fill_value=False)

    def test_flatten_mask(self):
        # Tests flatten mask
        # Standard dtype
        mask = np.array([0, 0, 1], dtype=bool)
        assert_equal(flatten_mask(mask), mask)
        # Flexible dtype
        mask = np.array([(0, 0), (0, 1)], dtype=[('a', bool), ('b', bool)])
        test = flatten_mask(mask)
        control = np.array([0, 0, 0, 1], dtype=bool)
        assert_equal(test, control)

        mdtype = [('a', bool), ('b', [('ba', bool), ('bb', bool)])]
        data = [(0, (0, 0)), (0, (0, 1))]
        mask = np.array(data, dtype=mdtype)
        test = flatten_mask(mask)
        control = np.array([0, 0, 0, 0, 0, 1], dtype=bool)
        assert_equal(test, control)

    def test_on_ndarray(self):
        # Test functions on ndarrays
        a = np.array([1, 2, 3, 4])
        m = array(a, mask=False)
        test = anom(a)
        assert_equal(test, m.anom())
        test = reshape(a, (2, 2))
        assert_equal(test, m.reshape(2, 2))

    def test_compress(self):
        # Test compress function on ndarray and masked array
        # Address Github #2495.
        arr = np.arange(8)
        arr.shape = 4, 2
        cond = np.array([True, False, True, True])
        control = arr[[0, 2, 3]]
        test = np.ma.compress(cond, arr, axis=0)
        assert_equal(test, control)
        marr = np.ma.array(arr)
        test = np.ma.compress(cond, marr, axis=0)
        assert_equal(test, control)

    def test_compressed(self):
        # Test ma.compressed function.
        # Address gh-4026
        a = np.ma.array([1, 2])
        test = np.ma.compressed(a)
        assert_(type(test) is np.ndarray)

        # Test case when input data is ndarray subclass
        class A(np.ndarray):
            pass

        a = np.ma.array(A(shape=0))
        test = np.ma.compressed(a)
        assert_(type(test) is A)

        # Test that compress flattens
        test = np.ma.compressed([[1], [2]])
        assert_equal(test.ndim, 1)
        test = np.ma.compressed([[[[[1]]]]])
        assert_equal(test.ndim, 1)

        # Test case when input is MaskedArray subclass
        class M(MaskedArray):
            pass

        test = np.ma.compressed(M([[[]], [[]]]))
        assert_equal(test.ndim, 1)

        # with .compressed() overridden
        class M(MaskedArray):
            def compressed(self):
                return 42

        test = np.ma.compressed(M([[[]], [[]]]))
        assert_equal(test, 42)

    def test_convolve(self):
        a = masked_equal(np.arange(5), 2)
        b = np.array([1, 1])

        result = masked_equal([0, 1, -1, -1, 7, 4], -1)
        test = np.ma.convolve(a, b, mode='full')
        assert_equal(test, result)

        test = np.ma.convolve(a, b, mode='same')
        assert_equal(test, result[:-1])

        test = np.ma.convolve(a, b, mode='valid')
        assert_equal(test, result[1:-1])

        result = masked_equal([0, 1, 1, 3, 7, 4], -1)
        test = np.ma.convolve(a, b, mode='full', propagate_mask=False)
        assert_equal(test, result)

        test = np.ma.convolve(a, b, mode='same', propagate_mask=False)
        assert_equal(test, result[:-1])

        test = np.ma.convolve(a, b, mode='valid', propagate_mask=False)
        assert_equal(test, result[1:-1])

        test = np.ma.convolve([1, 1], [1, 1, 1])
        assert_equal(test, masked_equal([1, 2, 2, 1], -1))

        a = [1, 1]
        b = masked_equal([1, -1, -1, 1], -1)
        test = np.ma.convolve(a, b, propagate_mask=False)
        assert_equal(test, masked_equal([1, 1, -1, 1, 1], -1))
        test = np.ma.convolve(a, b, propagate_mask=True)
        assert_equal(test, masked_equal([-1, -1, -1, -1, -1], -1))


class TestMaskedFields:

    def setup_method(self):
        ilist = [1, 2, 3, 4, 5]
        flist = [1.1, 2.2, 3.3, 4.4, 5.5]
        slist = ['one', 'two', 'three', 'four', 'five']
        ddtype = [('a', int), ('b', float), ('c', '|S8')]
        mdtype = [('a', bool), ('b', bool), ('c', bool)]
        mask = [0, 1, 0, 0, 1]
        base = array(list(zip(ilist, flist, slist)), mask=mask, dtype=ddtype)
        self.data = {"base": base, "mask": mask, "ddtype": ddtype, "mdtype": mdtype}

    def test_set_records_masks(self):
        base = self.data['base']
        mdtype = self.data['mdtype']
        # Set w/ nomask or masked
        base.mask = nomask
        assert_equal_records(base._mask, np.zeros(base.shape, dtype=mdtype))
        base.mask = masked
        assert_equal_records(base._mask, np.ones(base.shape, dtype=mdtype))
        # Set w/ simple boolean
        base.mask = False
        assert_equal_records(base._mask, np.zeros(base.shape, dtype=mdtype))
        base.mask = True
        assert_equal_records(base._mask, np.ones(base.shape, dtype=mdtype))
        # Set w/ list
        base.mask = [0, 0, 0, 1, 1]
        assert_equal_records(base._mask,
                             np.array([(x, x, x) for x in [0, 0, 0, 1, 1]],
                                      dtype=mdtype))

    def test_set_record_element(self):
        # Check setting an element of a record)
        base = self.data['base']
        (base_a, base_b, base_c) = (base['a'], base['b'], base['c'])
        base[0] = (pi, pi, 'pi')

        assert_equal(base_a.dtype, int)
        assert_equal(base_a._data, [3, 2, 3, 4, 5])

        assert_equal(base_b.dtype, float)
        assert_equal(base_b._data, [pi, 2.2, 3.3, 4.4, 5.5])

        assert_equal(base_c.dtype, '|S8')
        assert_equal(base_c._data,
                     [b'pi', b'two', b'three', b'four', b'five'])

    def test_set_record_slice(self):
        base = self.data['base']
        (base_a, base_b, base_c) = (base['a'], base['b'], base['c'])
        base[:3] = (pi, pi, 'pi')

        assert_equal(base_a.dtype, int)
        assert_equal(base_a._data, [3, 3, 3, 4, 5])

        assert_equal(base_b.dtype, float)
        assert_equal(base_b._data, [pi, pi, pi, 4.4, 5.5])

        assert_equal(base_c.dtype, '|S8')
        assert_equal(base_c._data,
                     [b'pi', b'pi', b'pi', b'four', b'five'])

    def test_mask_element(self):
        "Check record access"
        base = self.data['base']
        base[0] = masked

        for n in ('a', 'b', 'c'):
            assert_equal(base[n].mask, [1, 1, 0, 0, 1])
            assert_equal(base[n]._data, base._data[n])

    def test_getmaskarray(self):
        # Test getmaskarray on flexible dtype
        ndtype = [('a', int), ('b', float)]
        test = empty(3, dtype=ndtype)
        assert_equal(getmaskarray(test),
                     np.array([(0, 0), (0, 0), (0, 0)],
                              dtype=[('a', '|b1'), ('b', '|b1')]))
        test[:] = masked
        assert_equal(getmaskarray(test),
                     np.array([(1, 1), (1, 1), (1, 1)],
                              dtype=[('a', '|b1'), ('b', '|b1')]))

    def test_view(self):
        # Test view w/ flexible dtype
        iterator = list(zip(np.arange(10), np.random.rand(10)))
        data = np.array(iterator)
        a = array(iterator, dtype=[('a', float), ('b', float)])
        a.mask[0] = (1, 0)
        controlmask = np.array([1] + 19 * [0], dtype=bool)
        # Transform globally to simple dtype
        test = a.view(float)
        assert_equal(test, data.ravel())
        assert_equal(test.mask, controlmask)
        # Transform globally to dty
        test = a.view((float, 2))
        assert_equal(test, data)
        assert_equal(test.mask, controlmask.reshape(-1, 2))

    def test_getitem(self):
        ndtype = [('a', float), ('b', float)]
        a = array(list(zip(np.random.rand(10), np.arange(10))), dtype=ndtype)
        a.mask = np.array(list(zip([0, 0, 0, 0, 0, 0, 0, 0, 1, 1],
                                   [1, 0, 0, 0, 0, 0, 0, 0, 1, 0])),
                          dtype=[('a', bool), ('b', bool)])

        def _test_index(i):
            assert_equal(type(a[i]), mvoid)
            assert_equal_records(a[i]._data, a._data[i])
            assert_equal_records(a[i]._mask, a._mask[i])

            assert_equal(type(a[i, ...]), MaskedArray)
            assert_equal_records(a[i, ...]._data, a._data[i, ...])
            assert_equal_records(a[i, ...]._mask, a._mask[i, ...])

        _test_index(1)   # No mask
        _test_index(0)   # One element masked
        _test_index(-2)  # All element masked

    def test_setitem(self):
        # Issue 4866: check that one can set individual items in [record][col]
        # and [col][record] order
        ndtype = np.dtype([('a', float), ('b', int)])
        ma = np.ma.MaskedArray([(1.0, 1), (2.0, 2)], dtype=ndtype)
        ma['a'][1] = 3.0
        assert_equal(ma['a'], np.array([1.0, 3.0]))
        ma[1]['a'] = 4.0
        assert_equal(ma['a'], np.array([1.0, 4.0]))
        # Issue 2403
        mdtype = np.dtype([('a', bool), ('b', bool)])
        # soft mask
        control = np.array([(False, True), (True, True)], dtype=mdtype)
        a = np.ma.masked_all((2,), dtype=ndtype)
        a['a'][0] = 2
        assert_equal(a.mask, control)
        a = np.ma.masked_all((2,), dtype=ndtype)
        a[0]['a'] = 2
        assert_equal(a.mask, control)
        # hard mask
        control = np.array([(True, True), (True, True)], dtype=mdtype)
        a = np.ma.masked_all((2,), dtype=ndtype)
        a.harden_mask()
        a['a'][0] = 2
        assert_equal(a.mask, control)
        a = np.ma.masked_all((2,), dtype=ndtype)
        a.harden_mask()
        a[0]['a'] = 2
        assert_equal(a.mask, control)

    def test_setitem_scalar(self):
        # 8510
        mask_0d = np.ma.masked_array(1, mask=True)
        arr = np.ma.arange(3)
        arr[0] = mask_0d
        assert_array_equal(arr.mask, [True, False, False])

    def test_element_len(self):
        # check that len() works for mvoid (Github issue #576)
        for rec in self.data['base']:
            assert_equal(len(rec), len(self.data['ddtype']))


class TestMaskedObjectArray:

    def test_getitem(self):
        arr = np.ma.array([None, None])
        for dt in [float, object]:
            a0 = np.eye(2).astype(dt)
            a1 = np.eye(3).astype(dt)
            arr[0] = a0
            arr[1] = a1

            assert_(arr[0] is a0)
            assert_(arr[1] is a1)
            assert_(isinstance(arr[0, ...], MaskedArray))
            assert_(isinstance(arr[1, ...], MaskedArray))
            assert_(arr[0, ...][()] is a0)
            assert_(arr[1, ...][()] is a1)

            arr[0] = np.ma.masked

            assert_(arr[1] is a1)
            assert_(isinstance(arr[0, ...], MaskedArray))
            assert_(isinstance(arr[1, ...], MaskedArray))
            assert_equal(arr[0, ...].mask, True)
            assert_(arr[1, ...][()] is a1)

            # gh-5962 - object arrays of arrays do something special
            assert_equal(arr[0].data, a0)
            assert_equal(arr[0].mask, True)
            assert_equal(arr[0, ...][()].data, a0)
            assert_equal(arr[0, ...][()].mask, True)

    def test_nested_ma(self):

        arr = np.ma.array([None, None])
        # set the first object to be an unmasked masked constant. A little fiddly
        arr[0, ...] = np.array([np.ma.masked], object)[0, ...]

        # check the above line did what we were aiming for
        assert_(arr.data[0] is np.ma.masked)

        # test that getitem returned the value by identity
        assert_(arr[0] is np.ma.masked)

        # now mask the masked value!
        arr[0] = np.ma.masked
        assert_(arr[0] is np.ma.masked)


class TestMaskedView:

    def setup_method(self):
        iterator = list(zip(np.arange(10), np.random.rand(10)))
        data = np.array(iterator)
        a = array(iterator, dtype=[('a', float), ('b', float)])
        a.mask[0] = (1, 0)
        controlmask = np.array([1] + 19 * [0], dtype=bool)
        self.data = (data, a, controlmask)

    def test_view_to_nothing(self):
        (data, a, controlmask) = self.data
        test = a.view()
        assert_(isinstance(test, MaskedArray))
        assert_equal(test._data, a._data)
        assert_equal(test._mask, a._mask)

    def test_view_to_type(self):
        (data, a, controlmask) = self.data
        test = a.view(np.ndarray)
        assert_(not isinstance(test, MaskedArray))
        assert_equal(test, a._data)
        assert_equal_records(test, data.view(a.dtype).squeeze())

    def test_view_to_simple_dtype(self):
        (data, a, controlmask) = self.data
        # View globally
        test = a.view(float)
        assert_(isinstance(test, MaskedArray))
        assert_equal(test, data.ravel())
        assert_equal(test.mask, controlmask)

    def test_view_to_flexible_dtype(self):
        (data, a, controlmask) = self.data

        test = a.view([('A', float), ('B', float)])
        assert_equal(test.mask.dtype.names, ('A', 'B'))
        assert_equal(test['A'], a['a'])
        assert_equal(test['B'], a['b'])

        test = a[0].view([('A', float), ('B', float)])
        assert_(isinstance(test, MaskedArray))
        assert_equal(test.mask.dtype.names, ('A', 'B'))
        assert_equal(test['A'], a['a'][0])
        assert_equal(test['B'], a['b'][0])

        test = a[-1].view([('A', float), ('B', float)])
        assert_(isinstance(test, MaskedArray))
        assert_equal(test.dtype.names, ('A', 'B'))
        assert_equal(test['A'], a['a'][-1])
        assert_equal(test['B'], a['b'][-1])

    def test_view_to_subdtype(self):
        (data, a, controlmask) = self.data
        # View globally
        test = a.view((float, 2))
        assert_(isinstance(test, MaskedArray))
        assert_equal(test, data)
        assert_equal(test.mask, controlmask.reshape(-1, 2))
        # View on 1 masked element
        test = a[0].view((float, 2))
        assert_(isinstance(test, MaskedArray))
        assert_equal(test, data[0])
        assert_equal(test.mask, (1, 0))
        # View on 1 unmasked element
        test = a[-1].view((float, 2))
        assert_(isinstance(test, MaskedArray))
        assert_equal(test, data[-1])

    def test_view_to_dtype_and_type(self):
        (data, a, controlmask) = self.data

        test = a.view((float, 2), np.recarray)
        assert_equal(test, data)
        assert_(isinstance(test, np.recarray))
        assert_(not isinstance(test, MaskedArray))


class TestOptionalArgs:
    def test_ndarrayfuncs(self):
        # test axis arg behaves the same as ndarray (including multiple axes)

        d = np.arange(24.0).reshape((2, 3, 4))
        m = np.zeros(24, dtype=bool).reshape((2, 3, 4))
        # mask out last element of last dimension
        m[:, :, -1] = True
        a = np.ma.array(d, mask=m)

        def testaxis(f, a, d):
            numpy_f = numpy.__getattribute__(f)
            ma_f = np.ma.__getattribute__(f)

            # test axis arg
            assert_equal(ma_f(a, axis=1)[..., :-1], numpy_f(d[..., :-1], axis=1))
            assert_equal(ma_f(a, axis=(0, 1))[..., :-1],
                         numpy_f(d[..., :-1], axis=(0, 1)))

        def testkeepdims(f, a, d):
            numpy_f = numpy.__getattribute__(f)
            ma_f = np.ma.__getattribute__(f)

            # test keepdims arg
            assert_equal(ma_f(a, keepdims=True).shape,
                         numpy_f(d, keepdims=True).shape)
            assert_equal(ma_f(a, keepdims=False).shape,
                         numpy_f(d, keepdims=False).shape)

            # test both at once
            assert_equal(ma_f(a, axis=1, keepdims=True)[..., :-1],
                         numpy_f(d[..., :-1], axis=1, keepdims=True))
            assert_equal(ma_f(a, axis=(0, 1), keepdims=True)[..., :-1],
                         numpy_f(d[..., :-1], axis=(0, 1), keepdims=True))

        for f in ['sum', 'prod', 'mean', 'var', 'std']:
            testaxis(f, a, d)
            testkeepdims(f, a, d)

        for f in ['min', 'max']:
            testaxis(f, a, d)

        d = (np.arange(24).reshape((2, 3, 4)) % 2 == 0)
        a = np.ma.array(d, mask=m)
        for f in ['all', 'any']:
            testaxis(f, a, d)
            testkeepdims(f, a, d)

    def test_count(self):
        # test np.ma.count specially

        d = np.arange(24.0).reshape((2, 3, 4))
        m = np.zeros(24, dtype=bool).reshape((2, 3, 4))
        m[:, 0, :] = True
        a = np.ma.array(d, mask=m)

        assert_equal(count(a), 16)
        assert_equal(count(a, axis=1), 2 * ones((2, 4)))
        assert_equal(count(a, axis=(0, 1)), 4 * ones((4,)))
        assert_equal(count(a, keepdims=True), 16 * ones((1, 1, 1)))
        assert_equal(count(a, axis=1, keepdims=True), 2 * ones((2, 1, 4)))
        assert_equal(count(a, axis=(0, 1), keepdims=True), 4 * ones((1, 1, 4)))
        assert_equal(count(a, axis=-2), 2 * ones((2, 4)))
        assert_raises(ValueError, count, a, axis=(1, 1))
        assert_raises(AxisError, count, a, axis=3)

        # check the 'nomask' path
        a = np.ma.array(d, mask=nomask)

        assert_equal(count(a), 24)
        assert_equal(count(a, axis=1), 3 * ones((2, 4)))
        assert_equal(count(a, axis=(0, 1)), 6 * ones((4,)))
        assert_equal(count(a, keepdims=True), 24 * ones((1, 1, 1)))
        assert_equal(np.ndim(count(a, keepdims=True)), 3)
        assert_equal(count(a, axis=1, keepdims=True), 3 * ones((2, 1, 4)))
        assert_equal(count(a, axis=(0, 1), keepdims=True), 6 * ones((1, 1, 4)))
        assert_equal(count(a, axis=-2), 3 * ones((2, 4)))
        assert_raises(ValueError, count, a, axis=(1, 1))
        assert_raises(AxisError, count, a, axis=3)

        # check the 'masked' singleton
        assert_equal(count(np.ma.masked), 0)

        # check 0-d arrays do not allow axis > 0
        assert_raises(AxisError, count, np.ma.array(1), axis=1)


class TestMaskedConstant:
    def _do_add_test(self, add):
        # sanity check
        assert_(add(np.ma.masked, 1) is np.ma.masked)

        # now try with a vector
        vector = np.array([1, 2, 3])
        result = add(np.ma.masked, vector)

        # lots of things could go wrong here
        assert_(result is not np.ma.masked)
        assert_(not isinstance(result, np.ma.core.MaskedConstant))
        assert_equal(result.shape, vector.shape)
        assert_equal(np.ma.getmask(result), np.ones(vector.shape, dtype=bool))

    def test_ufunc(self):
        self._do_add_test(np.add)

    def test_operator(self):
        self._do_add_test(lambda a, b: a + b)

    def test_ctor(self):
        m = np.ma.array(np.ma.masked)

        # most importantly, we do not want to create a new MaskedConstant
        # instance
        assert_(not isinstance(m, np.ma.core.MaskedConstant))
        assert_(m is not np.ma.masked)

    def test_repr(self):
        # copies should not exist, but if they do, it should be obvious that
        # something is wrong
        assert_equal(repr(np.ma.masked), 'masked')

        # create a new instance in a weird way
        masked2 = np.ma.MaskedArray.__new__(np.ma.core.MaskedConstant)
        assert_not_equal(repr(masked2), 'masked')

    def test_pickle(self):
        from io import BytesIO

        for proto in range(2, pickle.HIGHEST_PROTOCOL + 1):
            with BytesIO() as f:
                pickle.dump(np.ma.masked, f, protocol=proto)
                f.seek(0)
                res = pickle.load(f)
            assert_(res is np.ma.masked)

    def test_copy(self):
        # gh-9328
        # copy is a no-op, like it is with np.True_
        assert_equal(
            np.ma.masked.copy() is np.ma.masked,
            np.True_.copy() is np.True_)

    def test__copy(self):
        import copy
        assert_(
            copy.copy(np.ma.masked) is np.ma.masked)

    def test_deepcopy(self):
        import copy
        assert_(
            copy.deepcopy(np.ma.masked) is np.ma.masked)

    def test_immutable(self):
        orig = np.ma.masked
        assert_raises(np.ma.core.MaskError, operator.setitem, orig, (), 1)
        assert_raises(ValueError, operator.setitem, orig.data, (), 1)
        assert_raises(ValueError, operator.setitem, orig.mask, (), False)

        view = np.ma.masked.view(np.ma.MaskedArray)
        assert_raises(ValueError, operator.setitem, view, (), 1)
        assert_raises(ValueError, operator.setitem, view.data, (), 1)
        assert_raises(ValueError, operator.setitem, view.mask, (), False)

    def test_coercion_int(self):
        a_i = np.zeros((), int)
        assert_raises(MaskError, operator.setitem, a_i, (), np.ma.masked)
        assert_raises(MaskError, int, np.ma.masked)

    def test_coercion_float(self):
        a_f = np.zeros((), float)
        assert_warns(UserWarning, operator.setitem, a_f, (), np.ma.masked)
        assert_(np.isnan(a_f[()]))

    @pytest.mark.xfail(reason="See gh-9750")
    def test_coercion_unicode(self):
        a_u = np.zeros((), 'U10')
        a_u[()] = np.ma.masked
        assert_equal(a_u[()], '--')

    @pytest.mark.xfail(reason="See gh-9750")
    def test_coercion_bytes(self):
        a_b = np.zeros((), 'S10')
        a_b[()] = np.ma.masked
        assert_equal(a_b[()], b'--')

    def test_subclass(self):
        # https://github.com/astropy/astropy/issues/6645
        class Sub(type(np.ma.masked)):
            pass

        a = Sub()
        assert_(a is Sub())
        assert_(a is not np.ma.masked)
        assert_not_equal(repr(a), 'masked')

    def test_attributes_readonly(self):
        assert_raises(AttributeError, setattr, np.ma.masked, 'shape', (1,))
        assert_raises(AttributeError, setattr, np.ma.masked, 'dtype', np.int64)


class TestMaskedWhereAliases:

    # TODO: Test masked_object, masked_equal, ...

    def test_masked_values(self):
        res = masked_values(np.array([-32768.0]), np.int16(-32768))
        assert_equal(res.mask, [True])

        res = masked_values(np.inf, np.inf)
        assert_equal(res.mask, True)

        res = np.ma.masked_values(np.inf, -np.inf)
        assert_equal(res.mask, False)

        res = np.ma.masked_values([1, 2, 3, 4], 5, shrink=True)
        assert_(res.mask is np.ma.nomask)

        res = np.ma.masked_values([1, 2, 3, 4], 5, shrink=False)
        assert_equal(res.mask, [False] * 4)


def test_masked_array():
    a = np.ma.array([0, 1, 2, 3], mask=[0, 0, 1, 0])
    assert_equal(np.argwhere(a), [[1], [3]])

def test_masked_array_no_copy():
    # check nomask array is updated in place
    a = np.ma.array([1, 2, 3, 4])
    _ = np.ma.masked_where(a == 3, a, copy=False)
    assert_array_equal(a.mask, [False, False, True, False])
    # check masked array is updated in place
    a = np.ma.array([1, 2, 3, 4], mask=[1, 0, 0, 0])
    _ = np.ma.masked_where(a == 3, a, copy=False)
    assert_array_equal(a.mask, [True, False, True, False])
    # check masked array with masked_invalid is updated in place
    a = np.ma.array([np.inf, 1, 2, 3, 4])
    _ = np.ma.masked_invalid(a, copy=False)
    assert_array_equal(a.mask, [True, False, False, False, False])

def test_append_masked_array():
    a = np.ma.masked_equal([1, 2, 3], value=2)
    b = np.ma.masked_equal([4, 3, 2], value=2)

    result = np.ma.append(a, b)
    expected_data = [1, 2, 3, 4, 3, 2]
    expected_mask = [False, True, False, False, False, True]
    assert_array_equal(result.data, expected_data)
    assert_array_equal(result.mask, expected_mask)

    a = np.ma.masked_all((2, 2))
    b = np.ma.ones((3, 1))

    result = np.ma.append(a, b)
    expected_data = [1] * 3
    expected_mask = [True] * 4 + [False] * 3
    assert_array_equal(result.data[-3], expected_data)
    assert_array_equal(result.mask, expected_mask)

    result = np.ma.append(a, b, axis=None)
    assert_array_equal(result.data[-3], expected_data)
    assert_array_equal(result.mask, expected_mask)


def test_append_masked_array_along_axis():
    a = np.ma.masked_equal([1, 2, 3], value=2)
    b = np.ma.masked_values([[4, 5, 6], [7, 8, 9]], 7)

    # When `axis` is specified, `values` must have the correct shape.
    assert_raises(ValueError, np.ma.append, a, b, axis=0)

    result = np.ma.append(a[np.newaxis, :], b, axis=0)
    expected = np.ma.arange(1, 10)
    expected[[1, 6]] = np.ma.masked
    expected = expected.reshape((3, 3))
    assert_array_equal(result.data, expected.data)
    assert_array_equal(result.mask, expected.mask)

def test_default_fill_value_complex():
    # regression test for Python 3, where 'unicode' was not defined
    assert_(default_fill_value(1 + 1j) == 1.e20 + 0.0j)


def test_ufunc_with_output():
    # check that giving an output argument always returns that output.
    # Regression test for gh-8416.
    x = array([1., 2., 3.], mask=[0, 0, 1])
    y = np.add(x, 1., out=x)
    assert_(y is x)


def test_ufunc_with_out_varied():
    """ Test that masked arrays are immune to gh-10459 """
    # the mask of the output should not affect the result, however it is passed
    a = array([ 1,  2,  3], mask=[1, 0, 0])
    b = array([10, 20, 30], mask=[1, 0, 0])
    out = array([ 0,  0,  0], mask=[0, 0, 1])
    expected = array([11, 22, 33], mask=[1, 0, 0])

    out_pos = out.copy()
    res_pos = np.add(a, b, out_pos)

    out_kw = out.copy()
    res_kw = np.add(a, b, out=out_kw)

    out_tup = out.copy()
    res_tup = np.add(a, b, out=(out_tup,))

    assert_equal(res_kw.mask,  expected.mask)
    assert_equal(res_kw.data,  expected.data)
    assert_equal(res_tup.mask, expected.mask)
    assert_equal(res_tup.data, expected.data)
    assert_equal(res_pos.mask, expected.mask)
    assert_equal(res_pos.data, expected.data)


def test_astype_mask_ordering():
    descr = np.dtype([('v', int, 3), ('x', [('y', float)])])
    x = array([
        [([1, 2, 3], (1.0,)),  ([1, 2, 3], (2.0,))],
        [([1, 2, 3], (3.0,)),  ([1, 2, 3], (4.0,))]], dtype=descr)
    x[0]['v'][0] = np.ma.masked

    x_a = x.astype(descr)
    assert x_a.dtype.names == np.dtype(descr).names
    assert x_a.mask.dtype.names == np.dtype(descr).names
    assert_equal(x, x_a)

    assert_(x is x.astype(x.dtype, copy=False))
    assert_equal(type(x.astype(x.dtype, subok=False)), np.ndarray)

    x_f = x.astype(x.dtype, order='F')
    assert_(x_f.flags.f_contiguous)
    assert_(x_f.mask.flags.f_contiguous)

    # Also test the same indirectly, via np.array
    x_a2 = np.array(x, dtype=descr, subok=True)
    assert x_a2.dtype.names == np.dtype(descr).names
    assert x_a2.mask.dtype.names == np.dtype(descr).names
    assert_equal(x, x_a2)

    assert_(x is np.array(x, dtype=descr, copy=None, subok=True))

    x_f2 = np.array(x, dtype=x.dtype, order='F', subok=True)
    assert_(x_f2.flags.f_contiguous)
    assert_(x_f2.mask.flags.f_contiguous)


@pytest.mark.parametrize('dt1', num_dts, ids=num_ids)
@pytest.mark.parametrize('dt2', num_dts, ids=num_ids)
@pytest.mark.filterwarnings('ignore::numpy.exceptions.ComplexWarning')
def test_astype_basic(dt1, dt2):
    # See gh-12070
    src = np.ma.array(ones(3, dt1), fill_value=1)
    dst = src.astype(dt2)

    assert_(src.fill_value == 1)
    assert_(src.dtype == dt1)
    assert_(src.fill_value.dtype == dt1)

    assert_(dst.fill_value == 1)
    assert_(dst.dtype == dt2)
    assert_(dst.fill_value.dtype == dt2)

    assert_equal(src, dst)


def test_fieldless_void():
    dt = np.dtype([])  # a void dtype with no fields
    x = np.empty(4, dt)

    # these arrays contain no values, so there's little to test - but this
    # shouldn't crash
    mx = np.ma.array(x)
    assert_equal(mx.dtype, x.dtype)
    assert_equal(mx.shape, x.shape)

    mx = np.ma.array(x, mask=x)
    assert_equal(mx.dtype, x.dtype)
    assert_equal(mx.shape, x.shape)


def test_mask_shape_assignment_does_not_break_masked():
    a = np.ma.masked
    b = np.ma.array(1, mask=a.mask)
    b.shape = (1,)
    assert_equal(a.mask.shape, ())

@pytest.mark.skipif(sys.flags.optimize > 1,
                    reason="no docstrings present to inspect when PYTHONOPTIMIZE/Py_OptimizeFlag > 1")  # noqa: E501
def test_doc_note():
    def method(self):
        """This docstring

        Has multiple lines

        And notes

        Notes
        -----
        original note
        """
        pass

    expected_doc = """This docstring

Has multiple lines

And notes

Notes
-----
note

original note"""

    assert_equal(np.ma.core.doc_note(method.__doc__, "note"), expected_doc)


def test_gh_22556():
    source = np.ma.array([0, [0, 1, 2]], dtype=object)
    deepcopy = copy.deepcopy(source)
    deepcopy[1].append('this should not appear in source')
    assert len(source[1]) == 3


def test_gh_21022():
    # testing for absence of reported error
    source = np.ma.masked_array(data=[-1, -1], mask=True, dtype=np.float64)
    axis = np.array(0)
    result = np.prod(source, axis=axis, keepdims=False)
    result = np.ma.masked_array(result,
                                mask=np.ones(result.shape, dtype=np.bool))
    array = np.ma.masked_array(data=-1, mask=True, dtype=np.float64)
    copy.deepcopy(array)
    copy.deepcopy(result)


def test_deepcopy_2d_obj():
    source = np.ma.array([[0, "dog"],
                          [1, 1],
                          [[1, 2], "cat"]],
                        mask=[[0, 1],
                              [0, 0],
                              [0, 0]],
                        dtype=object)
    deepcopy = copy.deepcopy(source)
    deepcopy[2, 0].extend(['this should not appear in source', 3])
    assert len(source[2, 0]) == 2
    assert len(deepcopy[2, 0]) == 4
    assert_equal(deepcopy._mask, source._mask)
    deepcopy._mask[0, 0] = 1
    assert source._mask[0, 0] == 0


def test_deepcopy_0d_obj():
    source = np.ma.array(0, mask=[0], dtype=object)
    deepcopy = copy.deepcopy(source)
    deepcopy[...] = 17
    assert_equal(source, 0)
    assert_equal(deepcopy, 17)


def test_uint_fill_value_and_filled():
    # See also gh-27269
    a = np.ma.MaskedArray([1, 1], [True, False], dtype="uint16")
    # the fill value should likely not be 99999, but for now guarantee it:
    assert a.fill_value == 999999
    # However, it's type is uint:
    assert a.fill_value.dtype.kind == "u"
    # And this ensures things like filled work:
    np.testing.assert_array_equal(
        a.filled(), np.array([999999, 1]).astype("uint16"), strict=True)