
# === NexusCore/openenv\Lib\site-packages\pip\_vendor\urllib3\packages\six.py ===
# Copyright (c) 2010-2020 Benjamin Peterson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Utilities for writing code that runs on Python 2 and 3"""

from __future__ import absolute_import

import functools
import itertools
import operator
import sys
import types

__author__ = "Benjamin Peterson <benjamin@python.org>"
__version__ = "1.16.0"


# Useful for very coarse version differentiation.
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3
PY34 = sys.version_info[0:2] >= (3, 4)

if PY3:
    string_types = (str,)
    integer_types = (int,)
    class_types = (type,)
    text_type = str
    binary_type = bytes

    MAXSIZE = sys.maxsize
else:
    string_types = (basestring,)
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str

    if sys.platform.startswith("java"):
        # Jython always uses 32 bits.
        MAXSIZE = int((1 << 31) - 1)
    else:
        # It's possible to have sizeof(long) != sizeof(Py_ssize_t).
        class X(object):
            def __len__(self):
                return 1 << 31

        try:
            len(X())
        except OverflowError:
            # 32-bit
            MAXSIZE = int((1 << 31) - 1)
        else:
            # 64-bit
            MAXSIZE = int((1 << 63) - 1)
        del X

if PY34:
    from importlib.util import spec_from_loader
else:
    spec_from_loader = None


def _add_doc(func, doc):
    """Add documentation to a function."""
    func.__doc__ = doc


def _import_module(name):
    """Import module, returning the module after the last dot."""
    __import__(name)
    return sys.modules[name]


class _LazyDescr(object):
    def __init__(self, name):
        self.name = name

    def __get__(self, obj, tp):
        result = self._resolve()
        setattr(obj, self.name, result)  # Invokes __set__.
        try:
            # This is a bit ugly, but it avoids running this again by
            # removing this descriptor.
            delattr(obj.__class__, self.name)
        except AttributeError:
            pass
        return result


class MovedModule(_LazyDescr):
    def __init__(self, name, old, new=None):
        super(MovedModule, self).__init__(name)
        if PY3:
            if new is None:
                new = name
            self.mod = new
        else:
            self.mod = old

    def _resolve(self):
        return _import_module(self.mod)

    def __getattr__(self, attr):
        _module = self._resolve()
        value = getattr(_module, attr)
        setattr(self, attr, value)
        return value


class _LazyModule(types.ModuleType):
    def __init__(self, name):
        super(_LazyModule, self).__init__(name)
        self.__doc__ = self.__class__.__doc__

    def __dir__(self):
        attrs = ["__doc__", "__name__"]
        attrs += [attr.name for attr in self._moved_attributes]
        return attrs

    # Subclasses should override this
    _moved_attributes = []


class MovedAttribute(_LazyDescr):
    def __init__(self, name, old_mod, new_mod, old_attr=None, new_attr=None):
        super(MovedAttribute, self).__init__(name)
        if PY3:
            if new_mod is None:
                new_mod = name
            self.mod = new_mod
            if new_attr is None:
                if old_attr is None:
                    new_attr = name
                else:
                    new_attr = old_attr
            self.attr = new_attr
        else:
            self.mod = old_mod
            if old_attr is None:
                old_attr = name
            self.attr = old_attr

    def _resolve(self):
        module = _import_module(self.mod)
        return getattr(module, self.attr)


class _SixMetaPathImporter(object):

    """
    A meta path importer to import six.moves and its submodules.

    This class implements a PEP302 finder and loader. It should be compatible
    with Python 2.5 and all existing versions of Python3
    """

    def __init__(self, six_module_name):
        self.name = six_module_name
        self.known_modules = {}

    def _add_module(self, mod, *fullnames):
        for fullname in fullnames:
            self.known_modules[self.name + "." + fullname] = mod

    def _get_module(self, fullname):
        return self.known_modules[self.name + "." + fullname]

    def find_module(self, fullname, path=None):
        if fullname in self.known_modules:
            return self
        return None

    def find_spec(self, fullname, path, target=None):
        if fullname in self.known_modules:
            return spec_from_loader(fullname, self)
        return None

    def __get_module(self, fullname):
        try:
            return self.known_modules[fullname]
        except KeyError:
            raise ImportError("This loader does not know module " + fullname)

    def load_module(self, fullname):
        try:
            # in case of a reload
            return sys.modules[fullname]
        except KeyError:
            pass
        mod = self.__get_module(fullname)
        if isinstance(mod, MovedModule):
            mod = mod._resolve()
        else:
            mod.__loader__ = self
        sys.modules[fullname] = mod
        return mod

    def is_package(self, fullname):
        """
        Return true, if the named module is a package.

        We need this method to get correct spec objects with
        Python 3.4 (see PEP451)
        """
        return hasattr(self.__get_module(fullname), "__path__")

    def get_code(self, fullname):
        """Return None

        Required, if is_package is implemented"""
        self.__get_module(fullname)  # eventually raises ImportError
        return None

    get_source = get_code  # same as get_code

    def create_module(self, spec):
        return self.load_module(spec.name)

    def exec_module(self, module):
        pass


_importer = _SixMetaPathImporter(__name__)


class _MovedItems(_LazyModule):

    """Lazy loading of moved objects"""

    __path__ = []  # mark as package


_moved_attributes = [
    MovedAttribute("cStringIO", "cStringIO", "io", "StringIO"),
    MovedAttribute("filter", "itertools", "builtins", "ifilter", "filter"),
    MovedAttribute(
        "filterfalse", "itertools", "itertools", "ifilterfalse", "filterfalse"
    ),
    MovedAttribute("input", "__builtin__", "builtins", "raw_input", "input"),
    MovedAttribute("intern", "__builtin__", "sys"),
    MovedAttribute("map", "itertools", "builtins", "imap", "map"),
    MovedAttribute("getcwd", "os", "os", "getcwdu", "getcwd"),
    MovedAttribute("getcwdb", "os", "os", "getcwd", "getcwdb"),
    MovedAttribute("getoutput", "commands", "subprocess"),
    MovedAttribute("range", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute(
        "reload_module", "__builtin__", "importlib" if PY34 else "imp", "reload"
    ),
    MovedAttribute("reduce", "__builtin__", "functools"),
    MovedAttribute("shlex_quote", "pipes", "shlex", "quote"),
    MovedAttribute("StringIO", "StringIO", "io"),
    MovedAttribute("UserDict", "UserDict", "collections"),
    MovedAttribute("UserList", "UserList", "collections"),
    MovedAttribute("UserString", "UserString", "collections"),
    MovedAttribute("xrange", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("zip", "itertools", "builtins", "izip", "zip"),
    MovedAttribute(
        "zip_longest", "itertools", "itertools", "izip_longest", "zip_longest"
    ),
    MovedModule("builtins", "__builtin__"),
    MovedModule("configparser", "ConfigParser"),
    MovedModule(
        "collections_abc",
        "collections",
        "collections.abc" if sys.version_info >= (3, 3) else "collections",
    ),
    MovedModule("copyreg", "copy_reg"),
    MovedModule("dbm_gnu", "gdbm", "dbm.gnu"),
    MovedModule("dbm_ndbm", "dbm", "dbm.ndbm"),
    MovedModule(
        "_dummy_thread",
        "dummy_thread",
        "_dummy_thread" if sys.version_info < (3, 9) else "_thread",
    ),
    MovedModule("http_cookiejar", "cookielib", "http.cookiejar"),
    MovedModule("http_cookies", "Cookie", "http.cookies"),
    MovedModule("html_entities", "htmlentitydefs", "html.entities"),
    MovedModule("html_parser", "HTMLParser", "html.parser"),
    MovedModule("http_client", "httplib", "http.client"),
    MovedModule("email_mime_base", "email.MIMEBase", "email.mime.base"),
    MovedModule("email_mime_image", "email.MIMEImage", "email.mime.image"),
    MovedModule("email_mime_multipart", "email.MIMEMultipart", "email.mime.multipart"),
    MovedModule(
        "email_mime_nonmultipart", "email.MIMENonMultipart", "email.mime.nonmultipart"
    ),
    MovedModule("email_mime_text", "email.MIMEText", "email.mime.text"),
    MovedModule("BaseHTTPServer", "BaseHTTPServer", "http.server"),
    MovedModule("CGIHTTPServer", "CGIHTTPServer", "http.server"),
    MovedModule("SimpleHTTPServer", "SimpleHTTPServer", "http.server"),
    MovedModule("cPickle", "cPickle", "pickle"),
    MovedModule("queue", "Queue"),
    MovedModule("reprlib", "repr"),
    MovedModule("socketserver", "SocketServer"),
    MovedModule("_thread", "thread", "_thread"),
    MovedModule("tkinter", "Tkinter"),
    MovedModule("tkinter_dialog", "Dialog", "tkinter.dialog"),
    MovedModule("tkinter_filedialog", "FileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_scrolledtext", "ScrolledText", "tkinter.scrolledtext"),
    MovedModule("tkinter_simpledialog", "SimpleDialog", "tkinter.simpledialog"),
    MovedModule("tkinter_tix", "Tix", "tkinter.tix"),
    MovedModule("tkinter_ttk", "ttk", "tkinter.ttk"),
    MovedModule("tkinter_constants", "Tkconstants", "tkinter.constants"),
    MovedModule("tkinter_dnd", "Tkdnd", "tkinter.dnd"),
    MovedModule("tkinter_colorchooser", "tkColorChooser", "tkinter.colorchooser"),
    MovedModule("tkinter_commondialog", "tkCommonDialog", "tkinter.commondialog"),
    MovedModule("tkinter_tkfiledialog", "tkFileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_font", "tkFont", "tkinter.font"),
    MovedModule("tkinter_messagebox", "tkMessageBox", "tkinter.messagebox"),
    MovedModule("tkinter_tksimpledialog", "tkSimpleDialog", "tkinter.simpledialog"),
    MovedModule("urllib_parse", __name__ + ".moves.urllib_parse", "urllib.parse"),
    MovedModule("urllib_error", __name__ + ".moves.urllib_error", "urllib.error"),
    MovedModule("urllib", __name__ + ".moves.urllib", __name__ + ".moves.urllib"),
    MovedModule("urllib_robotparser", "robotparser", "urllib.robotparser"),
    MovedModule("xmlrpc_client", "xmlrpclib", "xmlrpc.client"),
    MovedModule("xmlrpc_server", "SimpleXMLRPCServer", "xmlrpc.server"),
]
# Add windows specific modules.
if sys.platform == "win32":
    _moved_attributes += [
        MovedModule("winreg", "_winreg"),
    ]

for attr in _moved_attributes:
    setattr(_MovedItems, attr.name, attr)
    if isinstance(attr, MovedModule):
        _importer._add_module(attr, "moves." + attr.name)
del attr

_MovedItems._moved_attributes = _moved_attributes

moves = _MovedItems(__name__ + ".moves")
_importer._add_module(moves, "moves")


class Module_six_moves_urllib_parse(_LazyModule):

    """Lazy loading of moved objects in six.moves.urllib_parse"""


_urllib_parse_moved_attributes = [
    MovedAttribute("ParseResult", "urlparse", "urllib.parse"),
    MovedAttribute("SplitResult", "urlparse", "urllib.parse"),
    MovedAttribute("parse_qs", "urlparse", "urllib.parse"),
    MovedAttribute("parse_qsl", "urlparse", "urllib.parse"),
    MovedAttribute("urldefrag", "urlparse", "urllib.parse"),
    MovedAttribute("urljoin", "urlparse", "urllib.parse"),
    MovedAttribute("urlparse", "urlparse", "urllib.parse"),
    MovedAttribute("urlsplit", "urlparse", "urllib.parse"),
    MovedAttribute("urlunparse", "urlparse", "urllib.parse"),
    MovedAttribute("urlunsplit", "urlparse", "urllib.parse"),
    MovedAttribute("quote", "urllib", "urllib.parse"),
    MovedAttribute("quote_plus", "urllib", "urllib.parse"),
    MovedAttribute("unquote", "urllib", "urllib.parse"),
    MovedAttribute("unquote_plus", "urllib", "urllib.parse"),
    MovedAttribute(
        "unquote_to_bytes", "urllib", "urllib.parse", "unquote", "unquote_to_bytes"
    ),
    MovedAttribute("urlencode", "urllib", "urllib.parse"),
    MovedAttribute("splitquery", "urllib", "urllib.parse"),
    MovedAttribute("splittag", "urllib", "urllib.parse"),
    MovedAttribute("splituser", "urllib", "urllib.parse"),
    MovedAttribute("splitvalue", "urllib", "urllib.parse"),
    MovedAttribute("uses_fragment", "urlparse", "urllib.parse"),
    MovedAttribute("uses_netloc", "urlparse", "urllib.parse"),
    MovedAttribute("uses_params", "urlparse", "urllib.parse"),
    MovedAttribute("uses_query", "urlparse", "urllib.parse"),
    MovedAttribute("uses_relative", "urlparse", "urllib.parse"),
]
for attr in _urllib_parse_moved_attributes:
    setattr(Module_six_moves_urllib_parse, attr.name, attr)
del attr

Module_six_moves_urllib_parse._moved_attributes = _urllib_parse_moved_attributes

_importer._add_module(
    Module_six_moves_urllib_parse(__name__ + ".moves.urllib_parse"),
    "moves.urllib_parse",
    "moves.urllib.parse",
)


class Module_six_moves_urllib_error(_LazyModule):

    """Lazy loading of moved objects in six.moves.urllib_error"""


_urllib_error_moved_attributes = [
    MovedAttribute("URLError", "urllib2", "urllib.error"),
    MovedAttribute("HTTPError", "urllib2", "urllib.error"),
    MovedAttribute("ContentTooShortError", "urllib", "urllib.error"),
]
for attr in _urllib_error_moved_attributes:
    setattr(Module_six_moves_urllib_error, attr.name, attr)
del attr

Module_six_moves_urllib_error._moved_attributes = _urllib_error_moved_attributes

_importer._add_module(
    Module_six_moves_urllib_error(__name__ + ".moves.urllib.error"),
    "moves.urllib_error",
    "moves.urllib.error",
)


class Module_six_moves_urllib_request(_LazyModule):

    """Lazy loading of moved objects in six.moves.urllib_request"""


_urllib_request_moved_attributes = [
    MovedAttribute("urlopen", "urllib2", "urllib.request"),
    MovedAttribute("install_opener", "urllib2", "urllib.request"),
    MovedAttribute("build_opener", "urllib2", "urllib.request"),
    MovedAttribute("pathname2url", "urllib", "urllib.request"),
    MovedAttribute("url2pathname", "urllib", "urllib.request"),
    MovedAttribute("getproxies", "urllib", "urllib.request"),
    MovedAttribute("Request", "urllib2", "urllib.request"),
    MovedAttribute("OpenerDirector", "urllib2", "urllib.request"),
    MovedAttribute("HTTPDefaultErrorHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPRedirectHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPCookieProcessor", "urllib2", "urllib.request"),
    MovedAttribute("ProxyHandler", "urllib2", "urllib.request"),
    MovedAttribute("BaseHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPPasswordMgr", "urllib2", "urllib.request"),
    MovedAttribute("HTTPPasswordMgrWithDefaultRealm", "urllib2", "urllib.request"),
    MovedAttribute("AbstractBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("ProxyBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("AbstractDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("ProxyDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPSHandler", "urllib2", "urllib.request"),
    MovedAttribute("FileHandler", "urllib2", "urllib.request"),
    MovedAttribute("FTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("CacheFTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("UnknownHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPErrorProcessor", "urllib2", "urllib.request"),
    MovedAttribute("urlretrieve", "urllib", "urllib.request"),
    MovedAttribute("urlcleanup", "urllib", "urllib.request"),
    MovedAttribute("URLopener", "urllib", "urllib.request"),
    MovedAttribute("FancyURLopener", "urllib", "urllib.request"),
    MovedAttribute("proxy_bypass", "urllib", "urllib.request"),
    MovedAttribute("parse_http_list", "urllib2", "urllib.request"),
    MovedAttribute("parse_keqv_list", "urllib2", "urllib.request"),
]
for attr in _urllib_request_moved_attributes:
    setattr(Module_six_moves_urllib_request, attr.name, attr)
del attr

Module_six_moves_urllib_request._moved_attributes = _urllib_request_moved_attributes

_importer._add_module(
    Module_six_moves_urllib_request(__name__ + ".moves.urllib.request"),
    "moves.urllib_request",
    "moves.urllib.request",
)


class Module_six_moves_urllib_response(_LazyModule):

    """Lazy loading of moved objects in six.moves.urllib_response"""


_urllib_response_moved_attributes = [
    MovedAttribute("addbase", "urllib", "urllib.response"),
    MovedAttribute("addclosehook", "urllib", "urllib.response"),
    MovedAttribute("addinfo", "urllib", "urllib.response"),
    MovedAttribute("addinfourl", "urllib", "urllib.response"),
]
for attr in _urllib_response_moved_attributes:
    setattr(Module_six_moves_urllib_response, attr.name, attr)
del attr

Module_six_moves_urllib_response._moved_attributes = _urllib_response_moved_attributes

_importer._add_module(
    Module_six_moves_urllib_response(__name__ + ".moves.urllib.response"),
    "moves.urllib_response",
    "moves.urllib.response",
)


class Module_six_moves_urllib_robotparser(_LazyModule):

    """Lazy loading of moved objects in six.moves.urllib_robotparser"""


_urllib_robotparser_moved_attributes = [
    MovedAttribute("RobotFileParser", "robotparser", "urllib.robotparser"),
]
for attr in _urllib_robotparser_moved_attributes:
    setattr(Module_six_moves_urllib_robotparser, attr.name, attr)
del attr

Module_six_moves_urllib_robotparser._moved_attributes = (
    _urllib_robotparser_moved_attributes
)

_importer._add_module(
    Module_six_moves_urllib_robotparser(__name__ + ".moves.urllib.robotparser"),
    "moves.urllib_robotparser",
    "moves.urllib.robotparser",
)


class Module_six_moves_urllib(types.ModuleType):

    """Create a six.moves.urllib namespace that resembles the Python 3 namespace"""

    __path__ = []  # mark as package
    parse = _importer._get_module("moves.urllib_parse")
    error = _importer._get_module("moves.urllib_error")
    request = _importer._get_module("moves.urllib_request")
    response = _importer._get_module("moves.urllib_response")
    robotparser = _importer._get_module("moves.urllib_robotparser")

    def __dir__(self):
        return ["parse", "error", "request", "response", "robotparser"]


_importer._add_module(
    Module_six_moves_urllib(__name__ + ".moves.urllib"), "moves.urllib"
)


def add_move(move):
    """Add an item to six.moves."""
    setattr(_MovedItems, move.name, move)


def remove_move(name):
    """Remove item from six.moves."""
    try:
        delattr(_MovedItems, name)
    except AttributeError:
        try:
            del moves.__dict__[name]
        except KeyError:
            raise AttributeError("no such move, %r" % (name,))


if PY3:
    _meth_func = "__func__"
    _meth_self = "__self__"

    _func_closure = "__closure__"
    _func_code = "__code__"
    _func_defaults = "__defaults__"
    _func_globals = "__globals__"
else:
    _meth_func = "im_func"
    _meth_self = "im_self"

    _func_closure = "func_closure"
    _func_code = "func_code"
    _func_defaults = "func_defaults"
    _func_globals = "func_globals"


try:
    advance_iterator = next
except NameError:

    def advance_iterator(it):
        return it.next()


next = advance_iterator


try:
    callable = callable
except NameError:

    def callable(obj):
        return any("__call__" in klass.__dict__ for klass in type(obj).__mro__)


if PY3:

    def get_unbound_function(unbound):
        return unbound

    create_bound_method = types.MethodType

    def create_unbound_method(func, cls):
        return func

    Iterator = object
else:

    def get_unbound_function(unbound):
        return unbound.im_func

    def create_bound_method(func, obj):
        return types.MethodType(func, obj, obj.__class__)

    def create_unbound_method(func, cls):
        return types.MethodType(func, None, cls)

    class Iterator(object):
        def next(self):
            return type(self).__next__(self)

    callable = callable
_add_doc(
    get_unbound_function, """Get the function out of a possibly unbound function"""
)


get_method_function = operator.attrgetter(_meth_func)
get_method_self = operator.attrgetter(_meth_self)
get_function_closure = operator.attrgetter(_func_closure)
get_function_code = operator.attrgetter(_func_code)
get_function_defaults = operator.attrgetter(_func_defaults)
get_function_globals = operator.attrgetter(_func_globals)


if PY3:

    def iterkeys(d, **kw):
        return iter(d.keys(**kw))

    def itervalues(d, **kw):
        return iter(d.values(**kw))

    def iteritems(d, **kw):
        return iter(d.items(**kw))

    def iterlists(d, **kw):
        return iter(d.lists(**kw))

    viewkeys = operator.methodcaller("keys")

    viewvalues = operator.methodcaller("values")

    viewitems = operator.methodcaller("items")
else:

    def iterkeys(d, **kw):
        return d.iterkeys(**kw)

    def itervalues(d, **kw):
        return d.itervalues(**kw)

    def iteritems(d, **kw):
        return d.iteritems(**kw)

    def iterlists(d, **kw):
        return d.iterlists(**kw)

    viewkeys = operator.methodcaller("viewkeys")

    viewvalues = operator.methodcaller("viewvalues")

    viewitems = operator.methodcaller("viewitems")

_add_doc(iterkeys, "Return an iterator over the keys of a dictionary.")
_add_doc(itervalues, "Return an iterator over the values of a dictionary.")
_add_doc(iteritems, "Return an iterator over the (key, value) pairs of a dictionary.")
_add_doc(
    iterlists, "Return an iterator over the (key, [values]) pairs of a dictionary."
)


if PY3:

    def b(s):
        return s.encode("latin-1")

    def u(s):
        return s

    unichr = chr
    import struct

    int2byte = struct.Struct(">B").pack
    del struct
    byte2int = operator.itemgetter(0)
    indexbytes = operator.getitem
    iterbytes = iter
    import io

    StringIO = io.StringIO
    BytesIO = io.BytesIO
    del io
    _assertCountEqual = "assertCountEqual"
    if sys.version_info[1] <= 1:
        _assertRaisesRegex = "assertRaisesRegexp"
        _assertRegex = "assertRegexpMatches"
        _assertNotRegex = "assertNotRegexpMatches"
    else:
        _assertRaisesRegex = "assertRaisesRegex"
        _assertRegex = "assertRegex"
        _assertNotRegex = "assertNotRegex"
else:

    def b(s):
        return s

    # Workaround for standalone backslash

    def u(s):
        return unicode(s.replace(r"\\", r"\\\\"), "unicode_escape")

    unichr = unichr
    int2byte = chr

    def byte2int(bs):
        return ord(bs[0])

    def indexbytes(buf, i):
        return ord(buf[i])

    iterbytes = functools.partial(itertools.imap, ord)
    import StringIO

    StringIO = BytesIO = StringIO.StringIO
    _assertCountEqual = "assertItemsEqual"
    _assertRaisesRegex = "assertRaisesRegexp"
    _assertRegex = "assertRegexpMatches"
    _assertNotRegex = "assertNotRegexpMatches"
_add_doc(b, """Byte literal""")
_add_doc(u, """Text literal""")


def assertCountEqual(self, *args, **kwargs):
    return getattr(self, _assertCountEqual)(*args, **kwargs)


def assertRaisesRegex(self, *args, **kwargs):
    return getattr(self, _assertRaisesRegex)(*args, **kwargs)


def assertRegex(self, *args, **kwargs):
    return getattr(self, _assertRegex)(*args, **kwargs)


def assertNotRegex(self, *args, **kwargs):
    return getattr(self, _assertNotRegex)(*args, **kwargs)


if PY3:
    exec_ = getattr(moves.builtins, "exec")

    def reraise(tp, value, tb=None):
        try:
            if value is None:
                value = tp()
            if value.__traceback__ is not tb:
                raise value.with_traceback(tb)
            raise value
        finally:
            value = None
            tb = None

else:

    def exec_(_code_, _globs_=None, _locs_=None):
        """Execute code in a namespace."""
        if _globs_ is None:
            frame = sys._getframe(1)
            _globs_ = frame.f_globals
            if _locs_ is None:
                _locs_ = frame.f_locals
            del frame
        elif _locs_ is None:
            _locs_ = _globs_
        exec ("""exec _code_ in _globs_, _locs_""")

    exec_(
        """def reraise(tp, value, tb=None):
    try:
        raise tp, value, tb
    finally:
        tb = None
"""
    )


if sys.version_info[:2] > (3,):
    exec_(
        """def raise_from(value, from_value):
    try:
        raise value from from_value
    finally:
        value = None
"""
    )
else:

    def raise_from(value, from_value):
        raise value


print_ = getattr(moves.builtins, "print", None)
if print_ is None:

    def print_(*args, **kwargs):
        """The new-style print function for Python 2.4 and 2.5."""
        fp = kwargs.pop("file", sys.stdout)
        if fp is None:
            return

        def write(data):
            if not isinstance(data, basestring):
                data = str(data)
            # If the file has an encoding, encode unicode with it.
            if (
                isinstance(fp, file)
                and isinstance(data, unicode)
                and fp.encoding is not None
            ):
                errors = getattr(fp, "errors", None)
                if errors is None:
                    errors = "strict"
                data = data.encode(fp.encoding, errors)
            fp.write(data)

        want_unicode = False
        sep = kwargs.pop("sep", None)
        if sep is not None:
            if isinstance(sep, unicode):
                want_unicode = True
            elif not isinstance(sep, str):
                raise TypeError("sep must be None or a string")
        end = kwargs.pop("end", None)
        if end is not None:
            if isinstance(end, unicode):
                want_unicode = True
            elif not isinstance(end, str):
                raise TypeError("end must be None or a string")
        if kwargs:
            raise TypeError("invalid keyword arguments to print()")
        if not want_unicode:
            for arg in args:
                if isinstance(arg, unicode):
                    want_unicode = True
                    break
        if want_unicode:
            newline = unicode("\n")
            space = unicode(" ")
        else:
            newline = "\n"
            space = " "
        if sep is None:
            sep = space
        if end is None:
            end = newline
        for i, arg in enumerate(args):
            if i:
                write(sep)
            write(arg)
        write(end)


if sys.version_info[:2] < (3, 3):
    _print = print_

    def print_(*args, **kwargs):
        fp = kwargs.get("file", sys.stdout)
        flush = kwargs.pop("flush", False)
        _print(*args, **kwargs)
        if flush and fp is not None:
            fp.flush()


_add_doc(reraise, """Reraise an exception.""")

if sys.version_info[0:2] < (3, 4):
    # This does exactly the same what the :func:`py3:functools.update_wrapper`
    # function does on Python versions after 3.2. It sets the ``__wrapped__``
    # attribute on ``wrapper`` object and it doesn't raise an error if any of
    # the attributes mentioned in ``assigned`` and ``updated`` are missing on
    # ``wrapped`` object.
    def _update_wrapper(
        wrapper,
        wrapped,
        assigned=functools.WRAPPER_ASSIGNMENTS,
        updated=functools.WRAPPER_UPDATES,
    ):
        for attr in assigned:
            try:
                value = getattr(wrapped, attr)
            except AttributeError:
                continue
            else:
                setattr(wrapper, attr, value)
        for attr in updated:
            getattr(wrapper, attr).update(getattr(wrapped, attr, {}))
        wrapper.__wrapped__ = wrapped
        return wrapper

    _update_wrapper.__doc__ = functools.update_wrapper.__doc__

    def wraps(
        wrapped,
        assigned=functools.WRAPPER_ASSIGNMENTS,
        updated=functools.WRAPPER_UPDATES,
    ):
        return functools.partial(
            _update_wrapper, wrapped=wrapped, assigned=assigned, updated=updated
        )

    wraps.__doc__ = functools.wraps.__doc__

else:
    wraps = functools.wraps


def with_metaclass(meta, *bases):
    """Create a base class with a metaclass."""
    # This requires a bit of explanation: the basic idea is to make a dummy
    # metaclass for one level of class instantiation that replaces itself with
    # the actual metaclass.
    class metaclass(type):
        def __new__(cls, name, this_bases, d):
            if sys.version_info[:2] >= (3, 7):
                # This version introduced PEP 560 that requires a bit
                # of extra care (we mimic what is done by __build_class__).
                resolved_bases = types.resolve_bases(bases)
                if resolved_bases is not bases:
                    d["__orig_bases__"] = bases
            else:
                resolved_bases = bases
            return meta(name, resolved_bases, d)

        @classmethod
        def __prepare__(cls, name, this_bases):
            return meta.__prepare__(name, bases)

    return type.__new__(metaclass, "temporary_class", (), {})


def add_metaclass(metaclass):
    """Class decorator for creating a class with a metaclass."""

    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        slots = orig_vars.get("__slots__")
        if slots is not None:
            if isinstance(slots, str):
                slots = [slots]
            for slots_var in slots:
                orig_vars.pop(slots_var)
        orig_vars.pop("__dict__", None)
        orig_vars.pop("__weakref__", None)
        if hasattr(cls, "__qualname__"):
            orig_vars["__qualname__"] = cls.__qualname__
        return metaclass(cls.__name__, cls.__bases__, orig_vars)

    return wrapper


def ensure_binary(s, encoding="utf-8", errors="strict"):
    """Coerce **s** to six.binary_type.

    For Python 2:
      - `unicode` -> encoded to `str`
      - `str` -> `str`

    For Python 3:
      - `str` -> encoded to `bytes`
      - `bytes` -> `bytes`
    """
    if isinstance(s, binary_type):
        return s
    if isinstance(s, text_type):
        return s.encode(encoding, errors)
    raise TypeError("not expecting type '%s'" % type(s))


def ensure_str(s, encoding="utf-8", errors="strict"):
    """Coerce *s* to `str`.

    For Python 2:
      - `unicode` -> encoded to `str`
      - `str` -> `str`

    For Python 3:
      - `str` -> `str`
      - `bytes` -> decoded to `str`
    """
    # Optimization: Fast return for the common case.
    if type(s) is str:
        return s
    if PY2 and isinstance(s, text_type):
        return s.encode(encoding, errors)
    elif PY3 and isinstance(s, binary_type):
        return s.decode(encoding, errors)
    elif not isinstance(s, (text_type, binary_type)):
        raise TypeError("not expecting type '%s'" % type(s))
    return s


def ensure_text(s, encoding="utf-8", errors="strict"):
    """Coerce *s* to six.text_type.

    For Python 2:
      - `unicode` -> `unicode`
      - `str` -> `unicode`

    For Python 3:
      - `str` -> `str`
      - `bytes` -> decoded to `str`
    """
    if isinstance(s, binary_type):
        return s.decode(encoding, errors)
    elif isinstance(s, text_type):
        return s
    else:
        raise TypeError("not expecting type '%s'" % type(s))


def python_2_unicode_compatible(klass):
    """
    A class decorator that defines __unicode__ and __str__ methods under Python 2.
    Under Python 3 it does nothing.

    To support Python 2 and 3 with a single code base, define a __str__ method
    returning text and apply this decorator to the class.
    """
    if PY2:
        if "__str__" not in klass.__dict__:
            raise ValueError(
                "@python_2_unicode_compatible cannot be applied "
                "to %s because it doesn't define __str__()." % klass.__name__
            )
        klass.__unicode__ = klass.__str__
        klass.__str__ = lambda self: self.__unicode__().encode("utf-8")
    return klass


# Complete the moves implementation.
# This code is at the end of this module to speed up module loading.
# Turn this module into a package.
__path__ = []  # required for PEP 302 and PEP 451
__package__ = __name__  # see PEP 366 @ReservedAssignment
if globals().get("__spec__") is not None:
    __spec__.submodule_search_locations = []  # PEP 451 @UndefinedVariable
# Remove other six meta path importers, since they cause problems. This can
# happen if six is removed from sys.modules and then reloaded. (Setuptools does
# this for some reason.)
if sys.meta_path:
    for i, importer in enumerate(sys.meta_path):
        # Here's some real nastiness: Another "instance" of the six module might
        # be floating around. Therefore, we can't use isinstance() to check for
        # the six meta path importer, since the other six instance will have
        # inserted an importer with different class.
        if (
            type(importer).__name__ == "_SixMetaPathImporter"
            and importer.name == __name__
        ):
            del sys.meta_path[i]
            break
    del i, importer
# Finally, add the importer to the meta path import hook.
sys.meta_path.append(_importer)

# === NexusCore/myenv\Lib\site-packages\pip\_internal\cli\cmdoptions.py ===
"""
shared options and groups

The principle here is to define options once, but *not* instantiate them
globally. One reason being that options with action='append' can carry state
between parses. pip parses general options twice internally, and shouldn't
pass on state. To be consistent, all options will follow this design.
"""

# The following comment should be removed at some point in the future.
# mypy: strict-optional=False

import importlib.util
import logging
import os
import textwrap
from functools import partial
from optparse import SUPPRESS_HELP, Option, OptionGroup, OptionParser, Values
from textwrap import dedent
from typing import Any, Callable, Dict, Optional, Tuple

from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.cli.parser import ConfigOptionParser
from pip._internal.exceptions import CommandError
from pip._internal.locations import USER_CACHE_DIR, get_src_prefix
from pip._internal.models.format_control import FormatControl
from pip._internal.models.index import PyPI
from pip._internal.models.target_python import TargetPython
from pip._internal.utils.hashes import STRONG_HASHES
from pip._internal.utils.misc import strtobool

logger = logging.getLogger(__name__)


def raise_option_error(parser: OptionParser, option: Option, msg: str) -> None:
    """
    Raise an option parsing error using parser.error().

    Args:
      parser: an OptionParser instance.
      option: an Option instance.
      msg: the error text.
    """
    msg = f"{option} error: {msg}"
    msg = textwrap.fill(" ".join(msg.split()))
    parser.error(msg)


def make_option_group(group: Dict[str, Any], parser: ConfigOptionParser) -> OptionGroup:
    """
    Return an OptionGroup object
    group  -- assumed to be dict with 'name' and 'options' keys
    parser -- an optparse Parser
    """
    option_group = OptionGroup(parser, group["name"])
    for option in group["options"]:
        option_group.add_option(option())
    return option_group


def check_dist_restriction(options: Values, check_target: bool = False) -> None:
    """Function for determining if custom platform options are allowed.

    :param options: The OptionParser options.
    :param check_target: Whether or not to check if --target is being used.
    """
    dist_restriction_set = any(
        [
            options.python_version,
            options.platforms,
            options.abis,
            options.implementation,
        ]
    )

    binary_only = FormatControl(set(), {":all:"})
    sdist_dependencies_allowed = (
        options.format_control != binary_only and not options.ignore_dependencies
    )

    # Installations or downloads using dist restrictions must not combine
    # source distributions and dist-specific wheels, as they are not
    # guaranteed to be locally compatible.
    if dist_restriction_set and sdist_dependencies_allowed:
        raise CommandError(
            "When restricting platform and interpreter constraints using "
            "--python-version, --platform, --abi, or --implementation, "
            "either --no-deps must be set, or --only-binary=:all: must be "
            "set and --no-binary must not be set (or must be set to "
            ":none:)."
        )

    if check_target:
        if not options.dry_run and dist_restriction_set and not options.target_dir:
            raise CommandError(
                "Can not use any platform or abi specific options unless "
                "installing via '--target' or using '--dry-run'"
            )


def _path_option_check(option: Option, opt: str, value: str) -> str:
    return os.path.expanduser(value)


def _package_name_option_check(option: Option, opt: str, value: str) -> str:
    return canonicalize_name(value)


class PipOption(Option):
    TYPES = Option.TYPES + ("path", "package_name")
    TYPE_CHECKER = Option.TYPE_CHECKER.copy()
    TYPE_CHECKER["package_name"] = _package_name_option_check
    TYPE_CHECKER["path"] = _path_option_check


###########
# options #
###########

help_: Callable[..., Option] = partial(
    Option,
    "-h",
    "--help",
    dest="help",
    action="help",
    help="Show help.",
)

debug_mode: Callable[..., Option] = partial(
    Option,
    "--debug",
    dest="debug_mode",
    action="store_true",
    default=False,
    help=(
        "Let unhandled exceptions propagate outside the main subroutine, "
        "instead of logging them to stderr."
    ),
)

isolated_mode: Callable[..., Option] = partial(
    Option,
    "--isolated",
    dest="isolated_mode",
    action="store_true",
    default=False,
    help=(
        "Run pip in an isolated mode, ignoring environment variables and user "
        "configuration."
    ),
)

require_virtualenv: Callable[..., Option] = partial(
    Option,
    "--require-virtualenv",
    "--require-venv",
    dest="require_venv",
    action="store_true",
    default=False,
    help=(
        "Allow pip to only run in a virtual environment; "
        "exit with an error otherwise."
    ),
)

override_externally_managed: Callable[..., Option] = partial(
    Option,
    "--break-system-packages",
    dest="override_externally_managed",
    action="store_true",
    help="Allow pip to modify an EXTERNALLY-MANAGED Python installation",
)

python: Callable[..., Option] = partial(
    Option,
    "--python",
    dest="python",
    help="Run pip with the specified Python interpreter.",
)

verbose: Callable[..., Option] = partial(
    Option,
    "-v",
    "--verbose",
    dest="verbose",
    action="count",
    default=0,
    help="Give more output. Option is additive, and can be used up to 3 times.",
)

no_color: Callable[..., Option] = partial(
    Option,
    "--no-color",
    dest="no_color",
    action="store_true",
    default=False,
    help="Suppress colored output.",
)

version: Callable[..., Option] = partial(
    Option,
    "-V",
    "--version",
    dest="version",
    action="store_true",
    help="Show version and exit.",
)

quiet: Callable[..., Option] = partial(
    Option,
    "-q",
    "--quiet",
    dest="quiet",
    action="count",
    default=0,
    help=(
        "Give less output. Option is additive, and can be used up to 3"
        " times (corresponding to WARNING, ERROR, and CRITICAL logging"
        " levels)."
    ),
)

progress_bar: Callable[..., Option] = partial(
    Option,
    "--progress-bar",
    dest="progress_bar",
    type="choice",
    choices=["on", "off", "raw"],
    default="on",
    help="Specify whether the progress bar should be used [on, off, raw] (default: on)",
)

log: Callable[..., Option] = partial(
    PipOption,
    "--log",
    "--log-file",
    "--local-log",
    dest="log",
    metavar="path",
    type="path",
    help="Path to a verbose appending log.",
)

no_input: Callable[..., Option] = partial(
    Option,
    # Don't ask for input
    "--no-input",
    dest="no_input",
    action="store_true",
    default=False,
    help="Disable prompting for input.",
)

keyring_provider: Callable[..., Option] = partial(
    Option,
    "--keyring-provider",
    dest="keyring_provider",
    choices=["auto", "disabled", "import", "subprocess"],
    default="auto",
    help=(
        "Enable the credential lookup via the keyring library if user input is allowed."
        " Specify which mechanism to use [auto, disabled, import, subprocess]."
        " (default: %default)"
    ),
)

proxy: Callable[..., Option] = partial(
    Option,
    "--proxy",
    dest="proxy",
    type="str",
    default="",
    help="Specify a proxy in the form scheme://[user:passwd@]proxy.server:port.",
)

retries: Callable[..., Option] = partial(
    Option,
    "--retries",
    dest="retries",
    type="int",
    default=5,
    help="Maximum number of retries each connection should attempt "
    "(default %default times).",
)

timeout: Callable[..., Option] = partial(
    Option,
    "--timeout",
    "--default-timeout",
    metavar="sec",
    dest="timeout",
    type="float",
    default=15,
    help="Set the socket timeout (default %default seconds).",
)


def exists_action() -> Option:
    return Option(
        # Option when path already exist
        "--exists-action",
        dest="exists_action",
        type="choice",
        choices=["s", "i", "w", "b", "a"],
        default=[],
        action="append",
        metavar="action",
        help="Default action when a path already exists: "
        "(s)witch, (i)gnore, (w)ipe, (b)ackup, (a)bort.",
    )


cert: Callable[..., Option] = partial(
    PipOption,
    "--cert",
    dest="cert",
    type="path",
    metavar="path",
    help=(
        "Path to PEM-encoded CA certificate bundle. "
        "If provided, overrides the default. "
        "See 'SSL Certificate Verification' in pip documentation "
        "for more information."
    ),
)

client_cert: Callable[..., Option] = partial(
    PipOption,
    "--client-cert",
    dest="client_cert",
    type="path",
    default=None,
    metavar="path",
    help="Path to SSL client certificate, a single file containing the "
    "private key and the certificate in PEM format.",
)

index_url: Callable[..., Option] = partial(
    Option,
    "-i",
    "--index-url",
    "--pypi-url",
    dest="index_url",
    metavar="URL",
    default=PyPI.simple_url,
    help="Base URL of the Python Package Index (default %default). "
    "This should point to a repository compliant with PEP 503 "
    "(the simple repository API) or a local directory laid out "
    "in the same format.",
)


def extra_index_url() -> Option:
    return Option(
        "--extra-index-url",
        dest="extra_index_urls",
        metavar="URL",
        action="append",
        default=[],
        help="Extra URLs of package indexes to use in addition to "
        "--index-url. Should follow the same rules as "
        "--index-url.",
    )


no_index: Callable[..., Option] = partial(
    Option,
    "--no-index",
    dest="no_index",
    action="store_true",
    default=False,
    help="Ignore package index (only looking at --find-links URLs instead).",
)


def find_links() -> Option:
    return Option(
        "-f",
        "--find-links",
        dest="find_links",
        action="append",
        default=[],
        metavar="url",
        help="If a URL or path to an html file, then parse for links to "
        "archives such as sdist (.tar.gz) or wheel (.whl) files. "
        "If a local path or file:// URL that's a directory, "
        "then look for archives in the directory listing. "
        "Links to VCS project URLs are not supported.",
    )


def trusted_host() -> Option:
    return Option(
        "--trusted-host",
        dest="trusted_hosts",
        action="append",
        metavar="HOSTNAME",
        default=[],
        help="Mark this host or host:port pair as trusted, even though it "
        "does not have valid or any HTTPS.",
    )


def constraints() -> Option:
    return Option(
        "-c",
        "--constraint",
        dest="constraints",
        action="append",
        default=[],
        metavar="file",
        help="Constrain versions using the given constraints file. "
        "This option can be used multiple times.",
    )


def requirements() -> Option:
    return Option(
        "-r",
        "--requirement",
        dest="requirements",
        action="append",
        default=[],
        metavar="file",
        help="Install from the given requirements file. "
        "This option can be used multiple times.",
    )


def editable() -> Option:
    return Option(
        "-e",
        "--editable",
        dest="editables",
        action="append",
        default=[],
        metavar="path/url",
        help=(
            "Install a project in editable mode (i.e. setuptools "
            '"develop mode") from a local project path or a VCS url.'
        ),
    )


def _handle_src(option: Option, opt_str: str, value: str, parser: OptionParser) -> None:
    value = os.path.abspath(value)
    setattr(parser.values, option.dest, value)


src: Callable[..., Option] = partial(
    PipOption,
    "--src",
    "--source",
    "--source-dir",
    "--source-directory",
    dest="src_dir",
    type="path",
    metavar="dir",
    default=get_src_prefix(),
    action="callback",
    callback=_handle_src,
    help="Directory to check out editable projects into. "
    'The default in a virtualenv is "<venv path>/src". '
    'The default for global installs is "<current dir>/src".',
)


def _get_format_control(values: Values, option: Option) -> Any:
    """Get a format_control object."""
    return getattr(values, option.dest)


def _handle_no_binary(
    option: Option, opt_str: str, value: str, parser: OptionParser
) -> None:
    existing = _get_format_control(parser.values, option)
    FormatControl.handle_mutual_excludes(
        value,
        existing.no_binary,
        existing.only_binary,
    )


def _handle_only_binary(
    option: Option, opt_str: str, value: str, parser: OptionParser
) -> None:
    existing = _get_format_control(parser.values, option)
    FormatControl.handle_mutual_excludes(
        value,
        existing.only_binary,
        existing.no_binary,
    )


def no_binary() -> Option:
    format_control = FormatControl(set(), set())
    return Option(
        "--no-binary",
        dest="format_control",
        action="callback",
        callback=_handle_no_binary,
        type="str",
        default=format_control,
        help="Do not use binary packages. Can be supplied multiple times, and "
        'each time adds to the existing value. Accepts either ":all:" to '
        'disable all binary packages, ":none:" to empty the set (notice '
        "the colons), or one or more package names with commas between "
        "them (no colons). Note that some packages are tricky to compile "
        "and may fail to install when this option is used on them.",
    )


def only_binary() -> Option:
    format_control = FormatControl(set(), set())
    return Option(
        "--only-binary",
        dest="format_control",
        action="callback",
        callback=_handle_only_binary,
        type="str",
        default=format_control,
        help="Do not use source packages. Can be supplied multiple times, and "
        'each time adds to the existing value. Accepts either ":all:" to '
        'disable all source packages, ":none:" to empty the set, or one '
        "or more package names with commas between them. Packages "
        "without binary distributions will fail to install when this "
        "option is used on them.",
    )


platforms: Callable[..., Option] = partial(
    Option,
    "--platform",
    dest="platforms",
    metavar="platform",
    action="append",
    default=None,
    help=(
        "Only use wheels compatible with <platform>. Defaults to the "
        "platform of the running system. Use this option multiple times to "
        "specify multiple platforms supported by the target interpreter."
    ),
)


# This was made a separate function for unit-testing purposes.
def _convert_python_version(value: str) -> Tuple[Tuple[int, ...], Optional[str]]:
    """
    Convert a version string like "3", "37", or "3.7.3" into a tuple of ints.

    :return: A 2-tuple (version_info, error_msg), where `error_msg` is
        non-None if and only if there was a parsing error.
    """
    if not value:
        # The empty string is the same as not providing a value.
        return (None, None)

    parts = value.split(".")
    if len(parts) > 3:
        return ((), "at most three version parts are allowed")

    if len(parts) == 1:
        # Then we are in the case of "3" or "37".
        value = parts[0]
        if len(value) > 1:
            parts = [value[0], value[1:]]

    try:
        version_info = tuple(int(part) for part in parts)
    except ValueError:
        return ((), "each version part must be an integer")

    return (version_info, None)


def _handle_python_version(
    option: Option, opt_str: str, value: str, parser: OptionParser
) -> None:
    """
    Handle a provided --python-version value.
    """
    version_info, error_msg = _convert_python_version(value)
    if error_msg is not None:
        msg = f"invalid --python-version value: {value!r}: {error_msg}"
        raise_option_error(parser, option=option, msg=msg)

    parser.values.python_version = version_info


python_version: Callable[..., Option] = partial(
    Option,
    "--python-version",
    dest="python_version",
    metavar="python_version",
    action="callback",
    callback=_handle_python_version,
    type="str",
    default=None,
    help=dedent(
        """\
    The Python interpreter version to use for wheel and "Requires-Python"
    compatibility checks. Defaults to a version derived from the running
    interpreter. The version can be specified using up to three dot-separated
    integers (e.g. "3" for 3.0.0, "3.7" for 3.7.0, or "3.7.3"). A major-minor
    version can also be given as a string without dots (e.g. "37" for 3.7.0).
    """
    ),
)


implementation: Callable[..., Option] = partial(
    Option,
    "--implementation",
    dest="implementation",
    metavar="implementation",
    default=None,
    help=(
        "Only use wheels compatible with Python "
        "implementation <implementation>, e.g. 'pp', 'jy', 'cp', "
        " or 'ip'. If not specified, then the current "
        "interpreter implementation is used.  Use 'py' to force "
        "implementation-agnostic wheels."
    ),
)


abis: Callable[..., Option] = partial(
    Option,
    "--abi",
    dest="abis",
    metavar="abi",
    action="append",
    default=None,
    help=(
        "Only use wheels compatible with Python abi <abi>, e.g. 'pypy_41'. "
        "If not specified, then the current interpreter abi tag is used. "
        "Use this option multiple times to specify multiple abis supported "
        "by the target interpreter. Generally you will need to specify "
        "--implementation, --platform, and --python-version when using this "
        "option."
    ),
)


def add_target_python_options(cmd_opts: OptionGroup) -> None:
    cmd_opts.add_option(platforms())
    cmd_opts.add_option(python_version())
    cmd_opts.add_option(implementation())
    cmd_opts.add_option(abis())


def make_target_python(options: Values) -> TargetPython:
    target_python = TargetPython(
        platforms=options.platforms,
        py_version_info=options.python_version,
        abis=options.abis,
        implementation=options.implementation,
    )

    return target_python


def prefer_binary() -> Option:
    return Option(
        "--prefer-binary",
        dest="prefer_binary",
        action="store_true",
        default=False,
        help=(
            "Prefer binary packages over source packages, even if the "
            "source packages are newer."
        ),
    )


cache_dir: Callable[..., Option] = partial(
    PipOption,
    "--cache-dir",
    dest="cache_dir",
    default=USER_CACHE_DIR,
    metavar="dir",
    type="path",
    help="Store the cache data in <dir>.",
)


def _handle_no_cache_dir(
    option: Option, opt: str, value: str, parser: OptionParser
) -> None:
    """
    Process a value provided for the --no-cache-dir option.

    This is an optparse.Option callback for the --no-cache-dir option.
    """
    # The value argument will be None if --no-cache-dir is passed via the
    # command-line, since the option doesn't accept arguments.  However,
    # the value can be non-None if the option is triggered e.g. by an
    # environment variable, like PIP_NO_CACHE_DIR=true.
    if value is not None:
        # Then parse the string value to get argument error-checking.
        try:
            strtobool(value)
        except ValueError as exc:
            raise_option_error(parser, option=option, msg=str(exc))

    # Originally, setting PIP_NO_CACHE_DIR to a value that strtobool()
    # converted to 0 (like "false" or "no") caused cache_dir to be disabled
    # rather than enabled (logic would say the latter).  Thus, we disable
    # the cache directory not just on values that parse to True, but (for
    # backwards compatibility reasons) also on values that parse to False.
    # In other words, always set it to False if the option is provided in
    # some (valid) form.
    parser.values.cache_dir = False


no_cache: Callable[..., Option] = partial(
    Option,
    "--no-cache-dir",
    dest="cache_dir",
    action="callback",
    callback=_handle_no_cache_dir,
    help="Disable the cache.",
)

no_deps: Callable[..., Option] = partial(
    Option,
    "--no-deps",
    "--no-dependencies",
    dest="ignore_dependencies",
    action="store_true",
    default=False,
    help="Don't install package dependencies.",
)

ignore_requires_python: Callable[..., Option] = partial(
    Option,
    "--ignore-requires-python",
    dest="ignore_requires_python",
    action="store_true",
    help="Ignore the Requires-Python information.",
)

no_build_isolation: Callable[..., Option] = partial(
    Option,
    "--no-build-isolation",
    dest="build_isolation",
    action="store_false",
    default=True,
    help="Disable isolation when building a modern source distribution. "
    "Build dependencies specified by PEP 518 must be already installed "
    "if this option is used.",
)

check_build_deps: Callable[..., Option] = partial(
    Option,
    "--check-build-dependencies",
    dest="check_build_deps",
    action="store_true",
    default=False,
    help="Check the build dependencies when PEP517 is used.",
)


def _handle_no_use_pep517(
    option: Option, opt: str, value: str, parser: OptionParser
) -> None:
    """
    Process a value provided for the --no-use-pep517 option.

    This is an optparse.Option callback for the no_use_pep517 option.
    """
    # Since --no-use-pep517 doesn't accept arguments, the value argument
    # will be None if --no-use-pep517 is passed via the command-line.
    # However, the value can be non-None if the option is triggered e.g.
    # by an environment variable, for example "PIP_NO_USE_PEP517=true".
    if value is not None:
        msg = """A value was passed for --no-use-pep517,
        probably using either the PIP_NO_USE_PEP517 environment variable
        or the "no-use-pep517" config file option. Use an appropriate value
        of the PIP_USE_PEP517 environment variable or the "use-pep517"
        config file option instead.
        """
        raise_option_error(parser, option=option, msg=msg)

    # If user doesn't wish to use pep517, we check if setuptools and wheel are installed
    # and raise error if it is not.
    packages = ("setuptools", "wheel")
    if not all(importlib.util.find_spec(package) for package in packages):
        msg = (
            f"It is not possible to use --no-use-pep517 "
            f"without {' and '.join(packages)} installed."
        )
        raise_option_error(parser, option=option, msg=msg)

    # Otherwise, --no-use-pep517 was passed via the command-line.
    parser.values.use_pep517 = False


use_pep517: Any = partial(
    Option,
    "--use-pep517",
    dest="use_pep517",
    action="store_true",
    default=None,
    help="Use PEP 517 for building source distributions "
    "(use --no-use-pep517 to force legacy behaviour).",
)

no_use_pep517: Any = partial(
    Option,
    "--no-use-pep517",
    dest="use_pep517",
    action="callback",
    callback=_handle_no_use_pep517,
    default=None,
    help=SUPPRESS_HELP,
)


def _handle_config_settings(
    option: Option, opt_str: str, value: str, parser: OptionParser
) -> None:
    key, sep, val = value.partition("=")
    if sep != "=":
        parser.error(f"Arguments to {opt_str} must be of the form KEY=VAL")
    dest = getattr(parser.values, option.dest)
    if dest is None:
        dest = {}
        setattr(parser.values, option.dest, dest)
    if key in dest:
        if isinstance(dest[key], list):
            dest[key].append(val)
        else:
            dest[key] = [dest[key], val]
    else:
        dest[key] = val


config_settings: Callable[..., Option] = partial(
    Option,
    "-C",
    "--config-settings",
    dest="config_settings",
    type=str,
    action="callback",
    callback=_handle_config_settings,
    metavar="settings",
    help="Configuration settings to be passed to the PEP 517 build backend. "
    "Settings take the form KEY=VALUE. Use multiple --config-settings options "
    "to pass multiple keys to the backend.",
)

build_options: Callable[..., Option] = partial(
    Option,
    "--build-option",
    dest="build_options",
    metavar="options",
    action="append",
    help="Extra arguments to be supplied to 'setup.py bdist_wheel'.",
)

global_options: Callable[..., Option] = partial(
    Option,
    "--global-option",
    dest="global_options",
    action="append",
    metavar="options",
    help="Extra global options to be supplied to the setup.py "
    "call before the install or bdist_wheel command.",
)

no_clean: Callable[..., Option] = partial(
    Option,
    "--no-clean",
    action="store_true",
    default=False,
    help="Don't clean up build directories.",
)

pre: Callable[..., Option] = partial(
    Option,
    "--pre",
    action="store_true",
    default=False,
    help="Include pre-release and development versions. By default, "
    "pip only finds stable versions.",
)

disable_pip_version_check: Callable[..., Option] = partial(
    Option,
    "--disable-pip-version-check",
    dest="disable_pip_version_check",
    action="store_true",
    default=False,
    help="Don't periodically check PyPI to determine whether a new version "
    "of pip is available for download. Implied with --no-index.",
)

root_user_action: Callable[..., Option] = partial(
    Option,
    "--root-user-action",
    dest="root_user_action",
    default="warn",
    choices=["warn", "ignore"],
    help="Action if pip is run as a root user [warn, ignore] (default: warn)",
)


def _handle_merge_hash(
    option: Option, opt_str: str, value: str, parser: OptionParser
) -> None:
    """Given a value spelled "algo:digest", append the digest to a list
    pointed to in a dict by the algo name."""
    if not parser.values.hashes:
        parser.values.hashes = {}
    try:
        algo, digest = value.split(":", 1)
    except ValueError:
        parser.error(
            f"Arguments to {opt_str} must be a hash name "
            "followed by a value, like --hash=sha256:"
            "abcde..."
        )
    if algo not in STRONG_HASHES:
        parser.error(
            "Allowed hash algorithms for {} are {}.".format(
                opt_str, ", ".join(STRONG_HASHES)
            )
        )
    parser.values.hashes.setdefault(algo, []).append(digest)


hash: Callable[..., Option] = partial(
    Option,
    "--hash",
    # Hash values eventually end up in InstallRequirement.hashes due to
    # __dict__ copying in process_line().
    dest="hashes",
    action="callback",
    callback=_handle_merge_hash,
    type="string",
    help="Verify that the package's archive matches this "
    "hash before installing. Example: --hash=sha256:abcdef...",
)


require_hashes: Callable[..., Option] = partial(
    Option,
    "--require-hashes",
    dest="require_hashes",
    action="store_true",
    default=False,
    help="Require a hash to check each requirement against, for "
    "repeatable installs. This option is implied when any package in a "
    "requirements file has a --hash option.",
)


list_path: Callable[..., Option] = partial(
    PipOption,
    "--path",
    dest="path",
    type="path",
    action="append",
    help="Restrict to the specified installation path for listing "
    "packages (can be used multiple times).",
)


def check_list_path_option(options: Values) -> None:
    if options.path and (options.user or options.local):
        raise CommandError("Cannot combine '--path' with '--user' or '--local'")


list_exclude: Callable[..., Option] = partial(
    PipOption,
    "--exclude",
    dest="excludes",
    action="append",
    metavar="package",
    type="package_name",
    help="Exclude specified package from the output",
)


no_python_version_warning: Callable[..., Option] = partial(
    Option,
    "--no-python-version-warning",
    dest="no_python_version_warning",
    action="store_true",
    default=False,
    help="Silence deprecation warnings for upcoming unsupported Pythons.",
)


# Features that are now always on. A warning is printed if they are used.
ALWAYS_ENABLED_FEATURES = [
    "truststore",  # always on since 24.2
    "no-binary-enable-wheel-cache",  # always on since 23.1
]

use_new_feature: Callable[..., Option] = partial(
    Option,
    "--use-feature",
    dest="features_enabled",
    metavar="feature",
    action="append",
    default=[],
    choices=[
        "fast-deps",
    ]
    + ALWAYS_ENABLED_FEATURES,
    help="Enable new functionality, that may be backward incompatible.",
)

use_deprecated_feature: Callable[..., Option] = partial(
    Option,
    "--use-deprecated",
    dest="deprecated_features_enabled",
    metavar="feature",
    action="append",
    default=[],
    choices=[
        "legacy-resolver",
        "legacy-certs",
    ],
    help=("Enable deprecated functionality, that will be removed in the future."),
)


##########
# groups #
##########

general_group: Dict[str, Any] = {
    "name": "General Options",
    "options": [
        help_,
        debug_mode,
        isolated_mode,
        require_virtualenv,
        python,
        verbose,
        version,
        quiet,
        log,
        no_input,
        keyring_provider,
        proxy,
        retries,
        timeout,
        exists_action,
        trusted_host,
        cert,
        client_cert,
        cache_dir,
        no_cache,
        disable_pip_version_check,
        no_color,
        no_python_version_warning,
        use_new_feature,
        use_deprecated_feature,
    ],
}

index_group: Dict[str, Any] = {
    "name": "Package Index Options",
    "options": [
        index_url,
        extra_index_url,
        no_index,
        find_links,
    ],
}

# === NexusCore/openenv\Lib\site-packages\pip\_internal\cli\cmdoptions.py ===
"""
shared options and groups

The principle here is to define options once, but *not* instantiate them
globally. One reason being that options with action='append' can carry state
between parses. pip parses general options twice internally, and shouldn't
pass on state. To be consistent, all options will follow this design.
"""

# The following comment should be removed at some point in the future.
# mypy: strict-optional=False

import importlib.util
import logging
import os
import textwrap
from functools import partial
from optparse import SUPPRESS_HELP, Option, OptionGroup, OptionParser, Values
from textwrap import dedent
from typing import Any, Callable, Dict, Optional, Tuple

from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.cli.parser import ConfigOptionParser
from pip._internal.exceptions import CommandError
from pip._internal.locations import USER_CACHE_DIR, get_src_prefix
from pip._internal.models.format_control import FormatControl
from pip._internal.models.index import PyPI
from pip._internal.models.target_python import TargetPython
from pip._internal.utils.hashes import STRONG_HASHES
from pip._internal.utils.misc import strtobool

logger = logging.getLogger(__name__)


def raise_option_error(parser: OptionParser, option: Option, msg: str) -> None:
    """
    Raise an option parsing error using parser.error().

    Args:
      parser: an OptionParser instance.
      option: an Option instance.
      msg: the error text.
    """
    msg = f"{option} error: {msg}"
    msg = textwrap.fill(" ".join(msg.split()))
    parser.error(msg)


def make_option_group(group: Dict[str, Any], parser: ConfigOptionParser) -> OptionGroup:
    """
    Return an OptionGroup object
    group  -- assumed to be dict with 'name' and 'options' keys
    parser -- an optparse Parser
    """
    option_group = OptionGroup(parser, group["name"])
    for option in group["options"]:
        option_group.add_option(option())
    return option_group


def check_dist_restriction(options: Values, check_target: bool = False) -> None:
    """Function for determining if custom platform options are allowed.

    :param options: The OptionParser options.
    :param check_target: Whether or not to check if --target is being used.
    """
    dist_restriction_set = any(
        [
            options.python_version,
            options.platforms,
            options.abis,
            options.implementation,
        ]
    )

    binary_only = FormatControl(set(), {":all:"})
    sdist_dependencies_allowed = (
        options.format_control != binary_only and not options.ignore_dependencies
    )

    # Installations or downloads using dist restrictions must not combine
    # source distributions and dist-specific wheels, as they are not
    # guaranteed to be locally compatible.
    if dist_restriction_set and sdist_dependencies_allowed:
        raise CommandError(
            "When restricting platform and interpreter constraints using "
            "--python-version, --platform, --abi, or --implementation, "
            "either --no-deps must be set, or --only-binary=:all: must be "
            "set and --no-binary must not be set (or must be set to "
            ":none:)."
        )

    if check_target:
        if not options.dry_run and dist_restriction_set and not options.target_dir:
            raise CommandError(
                "Can not use any platform or abi specific options unless "
                "installing via '--target' or using '--dry-run'"
            )


def _path_option_check(option: Option, opt: str, value: str) -> str:
    return os.path.expanduser(value)


def _package_name_option_check(option: Option, opt: str, value: str) -> str:
    return canonicalize_name(value)


class PipOption(Option):
    TYPES = Option.TYPES + ("path", "package_name")
    TYPE_CHECKER = Option.TYPE_CHECKER.copy()
    TYPE_CHECKER["package_name"] = _package_name_option_check
    TYPE_CHECKER["path"] = _path_option_check


###########
# options #
###########

help_: Callable[..., Option] = partial(
    Option,
    "-h",
    "--help",
    dest="help",
    action="help",
    help="Show help.",
)

debug_mode: Callable[..., Option] = partial(
    Option,
    "--debug",
    dest="debug_mode",
    action="store_true",
    default=False,
    help=(
        "Let unhandled exceptions propagate outside the main subroutine, "
        "instead of logging them to stderr."
    ),
)

isolated_mode: Callable[..., Option] = partial(
    Option,
    "--isolated",
    dest="isolated_mode",
    action="store_true",
    default=False,
    help=(
        "Run pip in an isolated mode, ignoring environment variables and user "
        "configuration."
    ),
)

require_virtualenv: Callable[..., Option] = partial(
    Option,
    "--require-virtualenv",
    "--require-venv",
    dest="require_venv",
    action="store_true",
    default=False,
    help=(
        "Allow pip to only run in a virtual environment; "
        "exit with an error otherwise."
    ),
)

override_externally_managed: Callable[..., Option] = partial(
    Option,
    "--break-system-packages",
    dest="override_externally_managed",
    action="store_true",
    help="Allow pip to modify an EXTERNALLY-MANAGED Python installation",
)

python: Callable[..., Option] = partial(
    Option,
    "--python",
    dest="python",
    help="Run pip with the specified Python interpreter.",
)

verbose: Callable[..., Option] = partial(
    Option,
    "-v",
    "--verbose",
    dest="verbose",
    action="count",
    default=0,
    help="Give more output. Option is additive, and can be used up to 3 times.",
)

no_color: Callable[..., Option] = partial(
    Option,
    "--no-color",
    dest="no_color",
    action="store_true",
    default=False,
    help="Suppress colored output.",
)

version: Callable[..., Option] = partial(
    Option,
    "-V",
    "--version",
    dest="version",
    action="store_true",
    help="Show version and exit.",
)

quiet: Callable[..., Option] = partial(
    Option,
    "-q",
    "--quiet",
    dest="quiet",
    action="count",
    default=0,
    help=(
        "Give less output. Option is additive, and can be used up to 3"
        " times (corresponding to WARNING, ERROR, and CRITICAL logging"
        " levels)."
    ),
)

progress_bar: Callable[..., Option] = partial(
    Option,
    "--progress-bar",
    dest="progress_bar",
    type="choice",
    choices=["on", "off", "raw"],
    default="on",
    help="Specify whether the progress bar should be used [on, off, raw] (default: on)",
)

log: Callable[..., Option] = partial(
    PipOption,
    "--log",
    "--log-file",
    "--local-log",
    dest="log",
    metavar="path",
    type="path",
    help="Path to a verbose appending log.",
)

no_input: Callable[..., Option] = partial(
    Option,
    # Don't ask for input
    "--no-input",
    dest="no_input",
    action="store_true",
    default=False,
    help="Disable prompting for input.",
)

keyring_provider: Callable[..., Option] = partial(
    Option,
    "--keyring-provider",
    dest="keyring_provider",
    choices=["auto", "disabled", "import", "subprocess"],
    default="auto",
    help=(
        "Enable the credential lookup via the keyring library if user input is allowed."
        " Specify which mechanism to use [auto, disabled, import, subprocess]."
        " (default: %default)"
    ),
)

proxy: Callable[..., Option] = partial(
    Option,
    "--proxy",
    dest="proxy",
    type="str",
    default="",
    help="Specify a proxy in the form scheme://[user:passwd@]proxy.server:port.",
)

retries: Callable[..., Option] = partial(
    Option,
    "--retries",
    dest="retries",
    type="int",
    default=5,
    help="Maximum number of retries each connection should attempt "
    "(default %default times).",
)

timeout: Callable[..., Option] = partial(
    Option,
    "--timeout",
    "--default-timeout",
    metavar="sec",
    dest="timeout",
    type="float",
    default=15,
    help="Set the socket timeout (default %default seconds).",
)


def exists_action() -> Option:
    return Option(
        # Option when path already exist
        "--exists-action",
        dest="exists_action",
        type="choice",
        choices=["s", "i", "w", "b", "a"],
        default=[],
        action="append",
        metavar="action",
        help="Default action when a path already exists: "
        "(s)witch, (i)gnore, (w)ipe, (b)ackup, (a)bort.",
    )


cert: Callable[..., Option] = partial(
    PipOption,
    "--cert",
    dest="cert",
    type="path",
    metavar="path",
    help=(
        "Path to PEM-encoded CA certificate bundle. "
        "If provided, overrides the default. "
        "See 'SSL Certificate Verification' in pip documentation "
        "for more information."
    ),
)

client_cert: Callable[..., Option] = partial(
    PipOption,
    "--client-cert",
    dest="client_cert",
    type="path",
    default=None,
    metavar="path",
    help="Path to SSL client certificate, a single file containing the "
    "private key and the certificate in PEM format.",
)

index_url: Callable[..., Option] = partial(
    Option,
    "-i",
    "--index-url",
    "--pypi-url",
    dest="index_url",
    metavar="URL",
    default=PyPI.simple_url,
    help="Base URL of the Python Package Index (default %default). "
    "This should point to a repository compliant with PEP 503 "
    "(the simple repository API) or a local directory laid out "
    "in the same format.",
)


def extra_index_url() -> Option:
    return Option(
        "--extra-index-url",
        dest="extra_index_urls",
        metavar="URL",
        action="append",
        default=[],
        help="Extra URLs of package indexes to use in addition to "
        "--index-url. Should follow the same rules as "
        "--index-url.",
    )


no_index: Callable[..., Option] = partial(
    Option,
    "--no-index",
    dest="no_index",
    action="store_true",
    default=False,
    help="Ignore package index (only looking at --find-links URLs instead).",
)


def find_links() -> Option:
    return Option(
        "-f",
        "--find-links",
        dest="find_links",
        action="append",
        default=[],
        metavar="url",
        help="If a URL or path to an html file, then parse for links to "
        "archives such as sdist (.tar.gz) or wheel (.whl) files. "
        "If a local path or file:// URL that's a directory, "
        "then look for archives in the directory listing. "
        "Links to VCS project URLs are not supported.",
    )


def trusted_host() -> Option:
    return Option(
        "--trusted-host",
        dest="trusted_hosts",
        action="append",
        metavar="HOSTNAME",
        default=[],
        help="Mark this host or host:port pair as trusted, even though it "
        "does not have valid or any HTTPS.",
    )


def constraints() -> Option:
    return Option(
        "-c",
        "--constraint",
        dest="constraints",
        action="append",
        default=[],
        metavar="file",
        help="Constrain versions using the given constraints file. "
        "This option can be used multiple times.",
    )


def requirements() -> Option:
    return Option(
        "-r",
        "--requirement",
        dest="requirements",
        action="append",
        default=[],
        metavar="file",
        help="Install from the given requirements file. "
        "This option can be used multiple times.",
    )


def editable() -> Option:
    return Option(
        "-e",
        "--editable",
        dest="editables",
        action="append",
        default=[],
        metavar="path/url",
        help=(
            "Install a project in editable mode (i.e. setuptools "
            '"develop mode") from a local project path or a VCS url.'
        ),
    )


def _handle_src(option: Option, opt_str: str, value: str, parser: OptionParser) -> None:
    value = os.path.abspath(value)
    setattr(parser.values, option.dest, value)


src: Callable[..., Option] = partial(
    PipOption,
    "--src",
    "--source",
    "--source-dir",
    "--source-directory",
    dest="src_dir",
    type="path",
    metavar="dir",
    default=get_src_prefix(),
    action="callback",
    callback=_handle_src,
    help="Directory to check out editable projects into. "
    'The default in a virtualenv is "<venv path>/src". '
    'The default for global installs is "<current dir>/src".',
)


def _get_format_control(values: Values, option: Option) -> Any:
    """Get a format_control object."""
    return getattr(values, option.dest)


def _handle_no_binary(
    option: Option, opt_str: str, value: str, parser: OptionParser
) -> None:
    existing = _get_format_control(parser.values, option)
    FormatControl.handle_mutual_excludes(
        value,
        existing.no_binary,
        existing.only_binary,
    )


def _handle_only_binary(
    option: Option, opt_str: str, value: str, parser: OptionParser
) -> None:
    existing = _get_format_control(parser.values, option)
    FormatControl.handle_mutual_excludes(
        value,
        existing.only_binary,
        existing.no_binary,
    )


def no_binary() -> Option:
    format_control = FormatControl(set(), set())
    return Option(
        "--no-binary",
        dest="format_control",
        action="callback",
        callback=_handle_no_binary,
        type="str",
        default=format_control,
        help="Do not use binary packages. Can be supplied multiple times, and "
        'each time adds to the existing value. Accepts either ":all:" to '
        'disable all binary packages, ":none:" to empty the set (notice '
        "the colons), or one or more package names with commas between "
        "them (no colons). Note that some packages are tricky to compile "
        "and may fail to install when this option is used on them.",
    )


def only_binary() -> Option:
    format_control = FormatControl(set(), set())
    return Option(
        "--only-binary",
        dest="format_control",
        action="callback",
        callback=_handle_only_binary,
        type="str",
        default=format_control,
        help="Do not use source packages. Can be supplied multiple times, and "
        'each time adds to the existing value. Accepts either ":all:" to '
        'disable all source packages, ":none:" to empty the set, or one '
        "or more package names with commas between them. Packages "
        "without binary distributions will fail to install when this "
        "option is used on them.",
    )


platforms: Callable[..., Option] = partial(
    Option,
    "--platform",
    dest="platforms",
    metavar="platform",
    action="append",
    default=None,
    help=(
        "Only use wheels compatible with <platform>. Defaults to the "
        "platform of the running system. Use this option multiple times to "
        "specify multiple platforms supported by the target interpreter."
    ),
)


# This was made a separate function for unit-testing purposes.
def _convert_python_version(value: str) -> Tuple[Tuple[int, ...], Optional[str]]:
    """
    Convert a version string like "3", "37", or "3.7.3" into a tuple of ints.

    :return: A 2-tuple (version_info, error_msg), where `error_msg` is
        non-None if and only if there was a parsing error.
    """
    if not value:
        # The empty string is the same as not providing a value.
        return (None, None)

    parts = value.split(".")
    if len(parts) > 3:
        return ((), "at most three version parts are allowed")

    if len(parts) == 1:
        # Then we are in the case of "3" or "37".
        value = parts[0]
        if len(value) > 1:
            parts = [value[0], value[1:]]

    try:
        version_info = tuple(int(part) for part in parts)
    except ValueError:
        return ((), "each version part must be an integer")

    return (version_info, None)


def _handle_python_version(
    option: Option, opt_str: str, value: str, parser: OptionParser
) -> None:
    """
    Handle a provided --python-version value.
    """
    version_info, error_msg = _convert_python_version(value)
    if error_msg is not None:
        msg = f"invalid --python-version value: {value!r}: {error_msg}"
        raise_option_error(parser, option=option, msg=msg)

    parser.values.python_version = version_info


python_version: Callable[..., Option] = partial(
    Option,
    "--python-version",
    dest="python_version",
    metavar="python_version",
    action="callback",
    callback=_handle_python_version,
    type="str",
    default=None,
    help=dedent(
        """\
    The Python interpreter version to use for wheel and "Requires-Python"
    compatibility checks. Defaults to a version derived from the running
    interpreter. The version can be specified using up to three dot-separated
    integers (e.g. "3" for 3.0.0, "3.7" for 3.7.0, or "3.7.3"). A major-minor
    version can also be given as a string without dots (e.g. "37" for 3.7.0).
    """
    ),
)


implementation: Callable[..., Option] = partial(
    Option,
    "--implementation",
    dest="implementation",
    metavar="implementation",
    default=None,
    help=(
        "Only use wheels compatible with Python "
        "implementation <implementation>, e.g. 'pp', 'jy', 'cp', "
        " or 'ip'. If not specified, then the current "
        "interpreter implementation is used.  Use 'py' to force "
        "implementation-agnostic wheels."
    ),
)


abis: Callable[..., Option] = partial(
    Option,
    "--abi",
    dest="abis",
    metavar="abi",
    action="append",
    default=None,
    help=(
        "Only use wheels compatible with Python abi <abi>, e.g. 'pypy_41'. "
        "If not specified, then the current interpreter abi tag is used. "
        "Use this option multiple times to specify multiple abis supported "
        "by the target interpreter. Generally you will need to specify "
        "--implementation, --platform, and --python-version when using this "
        "option."
    ),
)


def add_target_python_options(cmd_opts: OptionGroup) -> None:
    cmd_opts.add_option(platforms())
    cmd_opts.add_option(python_version())
    cmd_opts.add_option(implementation())
    cmd_opts.add_option(abis())


def make_target_python(options: Values) -> TargetPython:
    target_python = TargetPython(
        platforms=options.platforms,
        py_version_info=options.python_version,
        abis=options.abis,
        implementation=options.implementation,
    )

    return target_python


def prefer_binary() -> Option:
    return Option(
        "--prefer-binary",
        dest="prefer_binary",
        action="store_true",
        default=False,
        help=(
            "Prefer binary packages over source packages, even if the "
            "source packages are newer."
        ),
    )


cache_dir: Callable[..., Option] = partial(
    PipOption,
    "--cache-dir",
    dest="cache_dir",
    default=USER_CACHE_DIR,
    metavar="dir",
    type="path",
    help="Store the cache data in <dir>.",
)


def _handle_no_cache_dir(
    option: Option, opt: str, value: str, parser: OptionParser
) -> None:
    """
    Process a value provided for the --no-cache-dir option.

    This is an optparse.Option callback for the --no-cache-dir option.
    """
    # The value argument will be None if --no-cache-dir is passed via the
    # command-line, since the option doesn't accept arguments.  However,
    # the value can be non-None if the option is triggered e.g. by an
    # environment variable, like PIP_NO_CACHE_DIR=true.
    if value is not None:
        # Then parse the string value to get argument error-checking.
        try:
            strtobool(value)
        except ValueError as exc:
            raise_option_error(parser, option=option, msg=str(exc))

    # Originally, setting PIP_NO_CACHE_DIR to a value that strtobool()
    # converted to 0 (like "false" or "no") caused cache_dir to be disabled
    # rather than enabled (logic would say the latter).  Thus, we disable
    # the cache directory not just on values that parse to True, but (for
    # backwards compatibility reasons) also on values that parse to False.
    # In other words, always set it to False if the option is provided in
    # some (valid) form.
    parser.values.cache_dir = False


no_cache: Callable[..., Option] = partial(
    Option,
    "--no-cache-dir",
    dest="cache_dir",
    action="callback",
    callback=_handle_no_cache_dir,
    help="Disable the cache.",
)

no_deps: Callable[..., Option] = partial(
    Option,
    "--no-deps",
    "--no-dependencies",
    dest="ignore_dependencies",
    action="store_true",
    default=False,
    help="Don't install package dependencies.",
)

ignore_requires_python: Callable[..., Option] = partial(
    Option,
    "--ignore-requires-python",
    dest="ignore_requires_python",
    action="store_true",
    help="Ignore the Requires-Python information.",
)

no_build_isolation: Callable[..., Option] = partial(
    Option,
    "--no-build-isolation",
    dest="build_isolation",
    action="store_false",
    default=True,
    help="Disable isolation when building a modern source distribution. "
    "Build dependencies specified by PEP 518 must be already installed "
    "if this option is used.",
)

check_build_deps: Callable[..., Option] = partial(
    Option,
    "--check-build-dependencies",
    dest="check_build_deps",
    action="store_true",
    default=False,
    help="Check the build dependencies when PEP517 is used.",
)


def _handle_no_use_pep517(
    option: Option, opt: str, value: str, parser: OptionParser
) -> None:
    """
    Process a value provided for the --no-use-pep517 option.

    This is an optparse.Option callback for the no_use_pep517 option.
    """
    # Since --no-use-pep517 doesn't accept arguments, the value argument
    # will be None if --no-use-pep517 is passed via the command-line.
    # However, the value can be non-None if the option is triggered e.g.
    # by an environment variable, for example "PIP_NO_USE_PEP517=true".
    if value is not None:
        msg = """A value was passed for --no-use-pep517,
        probably using either the PIP_NO_USE_PEP517 environment variable
        or the "no-use-pep517" config file option. Use an appropriate value
        of the PIP_USE_PEP517 environment variable or the "use-pep517"
        config file option instead.
        """
        raise_option_error(parser, option=option, msg=msg)

    # If user doesn't wish to use pep517, we check if setuptools and wheel are installed
    # and raise error if it is not.
    packages = ("setuptools", "wheel")
    if not all(importlib.util.find_spec(package) for package in packages):
        msg = (
            f"It is not possible to use --no-use-pep517 "
            f"without {' and '.join(packages)} installed."
        )
        raise_option_error(parser, option=option, msg=msg)

    # Otherwise, --no-use-pep517 was passed via the command-line.
    parser.values.use_pep517 = False


use_pep517: Any = partial(
    Option,
    "--use-pep517",
    dest="use_pep517",
    action="store_true",
    default=None,
    help="Use PEP 517 for building source distributions "
    "(use --no-use-pep517 to force legacy behaviour).",
)

no_use_pep517: Any = partial(
    Option,
    "--no-use-pep517",
    dest="use_pep517",
    action="callback",
    callback=_handle_no_use_pep517,
    default=None,
    help=SUPPRESS_HELP,
)


def _handle_config_settings(
    option: Option, opt_str: str, value: str, parser: OptionParser
) -> None:
    key, sep, val = value.partition("=")
    if sep != "=":
        parser.error(f"Arguments to {opt_str} must be of the form KEY=VAL")
    dest = getattr(parser.values, option.dest)
    if dest is None:
        dest = {}
        setattr(parser.values, option.dest, dest)
    if key in dest:
        if isinstance(dest[key], list):
            dest[key].append(val)
        else:
            dest[key] = [dest[key], val]
    else:
        dest[key] = val


config_settings: Callable[..., Option] = partial(
    Option,
    "-C",
    "--config-settings",
    dest="config_settings",
    type=str,
    action="callback",
    callback=_handle_config_settings,
    metavar="settings",
    help="Configuration settings to be passed to the PEP 517 build backend. "
    "Settings take the form KEY=VALUE. Use multiple --config-settings options "
    "to pass multiple keys to the backend.",
)

build_options: Callable[..., Option] = partial(
    Option,
    "--build-option",
    dest="build_options",
    metavar="options",
    action="append",
    help="Extra arguments to be supplied to 'setup.py bdist_wheel'.",
)

global_options: Callable[..., Option] = partial(
    Option,
    "--global-option",
    dest="global_options",
    action="append",
    metavar="options",
    help="Extra global options to be supplied to the setup.py "
    "call before the install or bdist_wheel command.",
)

no_clean: Callable[..., Option] = partial(
    Option,
    "--no-clean",
    action="store_true",
    default=False,
    help="Don't clean up build directories.",
)

pre: Callable[..., Option] = partial(
    Option,
    "--pre",
    action="store_true",
    default=False,
    help="Include pre-release and development versions. By default, "
    "pip only finds stable versions.",
)

disable_pip_version_check: Callable[..., Option] = partial(
    Option,
    "--disable-pip-version-check",
    dest="disable_pip_version_check",
    action="store_true",
    default=False,
    help="Don't periodically check PyPI to determine whether a new version "
    "of pip is available for download. Implied with --no-index.",
)

root_user_action: Callable[..., Option] = partial(
    Option,
    "--root-user-action",
    dest="root_user_action",
    default="warn",
    choices=["warn", "ignore"],
    help="Action if pip is run as a root user [warn, ignore] (default: warn)",
)


def _handle_merge_hash(
    option: Option, opt_str: str, value: str, parser: OptionParser
) -> None:
    """Given a value spelled "algo:digest", append the digest to a list
    pointed to in a dict by the algo name."""
    if not parser.values.hashes:
        parser.values.hashes = {}
    try:
        algo, digest = value.split(":", 1)
    except ValueError:
        parser.error(
            f"Arguments to {opt_str} must be a hash name "
            "followed by a value, like --hash=sha256:"
            "abcde..."
        )
    if algo not in STRONG_HASHES:
        parser.error(
            "Allowed hash algorithms for {} are {}.".format(
                opt_str, ", ".join(STRONG_HASHES)
            )
        )
    parser.values.hashes.setdefault(algo, []).append(digest)


hash: Callable[..., Option] = partial(
    Option,
    "--hash",
    # Hash values eventually end up in InstallRequirement.hashes due to
    # __dict__ copying in process_line().
    dest="hashes",
    action="callback",
    callback=_handle_merge_hash,
    type="string",
    help="Verify that the package's archive matches this "
    "hash before installing. Example: --hash=sha256:abcdef...",
)


require_hashes: Callable[..., Option] = partial(
    Option,
    "--require-hashes",
    dest="require_hashes",
    action="store_true",
    default=False,
    help="Require a hash to check each requirement against, for "
    "repeatable installs. This option is implied when any package in a "
    "requirements file has a --hash option.",
)


list_path: Callable[..., Option] = partial(
    PipOption,
    "--path",
    dest="path",
    type="path",
    action="append",
    help="Restrict to the specified installation path for listing "
    "packages (can be used multiple times).",
)


def check_list_path_option(options: Values) -> None:
    if options.path and (options.user or options.local):
        raise CommandError("Cannot combine '--path' with '--user' or '--local'")


list_exclude: Callable[..., Option] = partial(
    PipOption,
    "--exclude",
    dest="excludes",
    action="append",
    metavar="package",
    type="package_name",
    help="Exclude specified package from the output",
)


no_python_version_warning: Callable[..., Option] = partial(
    Option,
    "--no-python-version-warning",
    dest="no_python_version_warning",
    action="store_true",
    default=False,
    help="Silence deprecation warnings for upcoming unsupported Pythons.",
)


# Features that are now always on. A warning is printed if they are used.
ALWAYS_ENABLED_FEATURES = [
    "truststore",  # always on since 24.2
    "no-binary-enable-wheel-cache",  # always on since 23.1
]

use_new_feature: Callable[..., Option] = partial(
    Option,
    "--use-feature",
    dest="features_enabled",
    metavar="feature",
    action="append",
    default=[],
    choices=[
        "fast-deps",
    ]
    + ALWAYS_ENABLED_FEATURES,
    help="Enable new functionality, that may be backward incompatible.",
)

use_deprecated_feature: Callable[..., Option] = partial(
    Option,
    "--use-deprecated",
    dest="deprecated_features_enabled",
    metavar="feature",
    action="append",
    default=[],
    choices=[
        "legacy-resolver",
        "legacy-certs",
    ],
    help=("Enable deprecated functionality, that will be removed in the future."),
)


##########
# groups #
##########

general_group: Dict[str, Any] = {
    "name": "General Options",
    "options": [
        help_,
        debug_mode,
        isolated_mode,
        require_virtualenv,
        python,
        verbose,
        version,
        quiet,
        log,
        no_input,
        keyring_provider,
        proxy,
        retries,
        timeout,
        exists_action,
        trusted_host,
        cert,
        client_cert,
        cache_dir,
        no_cache,
        disable_pip_version_check,
        no_color,
        no_python_version_warning,
        use_new_feature,
        use_deprecated_feature,
    ],
}

index_group: Dict[str, Any] = {
    "name": "Package Index Options",
    "options": [
        index_url,
        extra_index_url,
        no_index,
        find_links,
    ],
}

# === NexusCore/openenv\Lib\site-packages\PIL\PdfParser.py ===
from __future__ import annotations

import calendar
import codecs
import collections
import mmap
import os
import re
import time
import zlib
from typing import IO, Any, NamedTuple, Union


# see 7.9.2.2 Text String Type on page 86 and D.3 PDFDocEncoding Character Set
# on page 656
def encode_text(s: str) -> bytes:
    return codecs.BOM_UTF16_BE + s.encode("utf_16_be")


PDFDocEncoding = {
    0x16: "\u0017",
    0x18: "\u02d8",
    0x19: "\u02c7",
    0x1A: "\u02c6",
    0x1B: "\u02d9",
    0x1C: "\u02dd",
    0x1D: "\u02db",
    0x1E: "\u02da",
    0x1F: "\u02dc",
    0x80: "\u2022",
    0x81: "\u2020",
    0x82: "\u2021",
    0x83: "\u2026",
    0x84: "\u2014",
    0x85: "\u2013",
    0x86: "\u0192",
    0x87: "\u2044",
    0x88: "\u2039",
    0x89: "\u203a",
    0x8A: "\u2212",
    0x8B: "\u2030",
    0x8C: "\u201e",
    0x8D: "\u201c",
    0x8E: "\u201d",
    0x8F: "\u2018",
    0x90: "\u2019",
    0x91: "\u201a",
    0x92: "\u2122",
    0x93: "\ufb01",
    0x94: "\ufb02",
    0x95: "\u0141",
    0x96: "\u0152",
    0x97: "\u0160",
    0x98: "\u0178",
    0x99: "\u017d",
    0x9A: "\u0131",
    0x9B: "\u0142",
    0x9C: "\u0153",
    0x9D: "\u0161",
    0x9E: "\u017e",
    0xA0: "\u20ac",
}


def decode_text(b: bytes) -> str:
    if b[: len(codecs.BOM_UTF16_BE)] == codecs.BOM_UTF16_BE:
        return b[len(codecs.BOM_UTF16_BE) :].decode("utf_16_be")
    else:
        return "".join(PDFDocEncoding.get(byte, chr(byte)) for byte in b)


class PdfFormatError(RuntimeError):
    """An error that probably indicates a syntactic or semantic error in the
    PDF file structure"""

    pass


def check_format_condition(condition: bool, error_message: str) -> None:
    if not condition:
        raise PdfFormatError(error_message)


class IndirectReferenceTuple(NamedTuple):
    object_id: int
    generation: int


class IndirectReference(IndirectReferenceTuple):
    def __str__(self) -> str:
        return f"{self.object_id} {self.generation} R"

    def __bytes__(self) -> bytes:
        return self.__str__().encode("us-ascii")

    def __eq__(self, other: object) -> bool:
        if self.__class__ is not other.__class__:
            return False
        assert isinstance(other, IndirectReference)
        return other.object_id == self.object_id and other.generation == self.generation

    def __ne__(self, other: object) -> bool:
        return not (self == other)

    def __hash__(self) -> int:
        return hash((self.object_id, self.generation))


class IndirectObjectDef(IndirectReference):
    def __str__(self) -> str:
        return f"{self.object_id} {self.generation} obj"


class XrefTable:
    def __init__(self) -> None:
        self.existing_entries: dict[int, tuple[int, int]] = (
            {}
        )  # object ID => (offset, generation)
        self.new_entries: dict[int, tuple[int, int]] = (
            {}
        )  # object ID => (offset, generation)
        self.deleted_entries = {0: 65536}  # object ID => generation
        self.reading_finished = False

    def __setitem__(self, key: int, value: tuple[int, int]) -> None:
        if self.reading_finished:
            self.new_entries[key] = value
        else:
            self.existing_entries[key] = value
        if key in self.deleted_entries:
            del self.deleted_entries[key]

    def __getitem__(self, key: int) -> tuple[int, int]:
        try:
            return self.new_entries[key]
        except KeyError:
            return self.existing_entries[key]

    def __delitem__(self, key: int) -> None:
        if key in self.new_entries:
            generation = self.new_entries[key][1] + 1
            del self.new_entries[key]
            self.deleted_entries[key] = generation
        elif key in self.existing_entries:
            generation = self.existing_entries[key][1] + 1
            self.deleted_entries[key] = generation
        elif key in self.deleted_entries:
            generation = self.deleted_entries[key]
        else:
            msg = f"object ID {key} cannot be deleted because it doesn't exist"
            raise IndexError(msg)

    def __contains__(self, key: int) -> bool:
        return key in self.existing_entries or key in self.new_entries

    def __len__(self) -> int:
        return len(
            set(self.existing_entries.keys())
            | set(self.new_entries.keys())
            | set(self.deleted_entries.keys())
        )

    def keys(self) -> set[int]:
        return (
            set(self.existing_entries.keys()) - set(self.deleted_entries.keys())
        ) | set(self.new_entries.keys())

    def write(self, f: IO[bytes]) -> int:
        keys = sorted(set(self.new_entries.keys()) | set(self.deleted_entries.keys()))
        deleted_keys = sorted(set(self.deleted_entries.keys()))
        startxref = f.tell()
        f.write(b"xref\n")
        while keys:
            # find a contiguous sequence of object IDs
            prev: int | None = None
            for index, key in enumerate(keys):
                if prev is None or prev + 1 == key:
                    prev = key
                else:
                    contiguous_keys = keys[:index]
                    keys = keys[index:]
                    break
            else:
                contiguous_keys = keys
                keys = []
            f.write(b"%d %d\n" % (contiguous_keys[0], len(contiguous_keys)))
            for object_id in contiguous_keys:
                if object_id in self.new_entries:
                    f.write(b"%010d %05d n \n" % self.new_entries[object_id])
                else:
                    this_deleted_object_id = deleted_keys.pop(0)
                    check_format_condition(
                        object_id == this_deleted_object_id,
                        f"expected the next deleted object ID to be {object_id}, "
                        f"instead found {this_deleted_object_id}",
                    )
                    try:
                        next_in_linked_list = deleted_keys[0]
                    except IndexError:
                        next_in_linked_list = 0
                    f.write(
                        b"%010d %05d f \n"
                        % (next_in_linked_list, self.deleted_entries[object_id])
                    )
        return startxref


class PdfName:
    name: bytes

    def __init__(self, name: PdfName | bytes | str) -> None:
        if isinstance(name, PdfName):
            self.name = name.name
        elif isinstance(name, bytes):
            self.name = name
        else:
            self.name = name.encode("us-ascii")

    def name_as_str(self) -> str:
        return self.name.decode("us-ascii")

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, PdfName) and other.name == self.name
        ) or other == self.name

    def __hash__(self) -> int:
        return hash(self.name)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({repr(self.name)})"

    @classmethod
    def from_pdf_stream(cls, data: bytes) -> PdfName:
        return cls(PdfParser.interpret_name(data))

    allowed_chars = set(range(33, 127)) - {ord(c) for c in "#%/()<>[]{}"}

    def __bytes__(self) -> bytes:
        result = bytearray(b"/")
        for b in self.name:
            if b in self.allowed_chars:
                result.append(b)
            else:
                result.extend(b"#%02X" % b)
        return bytes(result)


class PdfArray(list[Any]):
    def __bytes__(self) -> bytes:
        return b"[ " + b" ".join(pdf_repr(x) for x in self) + b" ]"


TYPE_CHECKING = False
if TYPE_CHECKING:
    _DictBase = collections.UserDict[Union[str, bytes], Any]
else:
    _DictBase = collections.UserDict


class PdfDict(_DictBase):
    def __setattr__(self, key: str, value: Any) -> None:
        if key == "data":
            collections.UserDict.__setattr__(self, key, value)
        else:
            self[key.encode("us-ascii")] = value

    def __getattr__(self, key: str) -> str | time.struct_time:
        try:
            value = self[key.encode("us-ascii")]
        except KeyError as e:
            raise AttributeError(key) from e
        if isinstance(value, bytes):
            value = decode_text(value)
        if key.endswith("Date"):
            if value.startswith("D:"):
                value = value[2:]

            relationship = "Z"
            if len(value) > 17:
                relationship = value[14]
                offset = int(value[15:17]) * 60
                if len(value) > 20:
                    offset += int(value[18:20])

            format = "%Y%m%d%H%M%S"[: len(value) - 2]
            value = time.strptime(value[: len(format) + 2], format)
            if relationship in ["+", "-"]:
                offset *= 60
                if relationship == "+":
                    offset *= -1
                value = time.gmtime(calendar.timegm(value) + offset)
        return value

    def __bytes__(self) -> bytes:
        out = bytearray(b"<<")
        for key, value in self.items():
            if value is None:
                continue
            value = pdf_repr(value)
            out.extend(b"\n")
            out.extend(bytes(PdfName(key)))
            out.extend(b" ")
            out.extend(value)
        out.extend(b"\n>>")
        return bytes(out)


class PdfBinary:
    def __init__(self, data: list[int] | bytes) -> None:
        self.data = data

    def __bytes__(self) -> bytes:
        return b"<%s>" % b"".join(b"%02X" % b for b in self.data)


class PdfStream:
    def __init__(self, dictionary: PdfDict, buf: bytes) -> None:
        self.dictionary = dictionary
        self.buf = buf

    def decode(self) -> bytes:
        try:
            filter = self.dictionary[b"Filter"]
        except KeyError:
            return self.buf
        if filter == b"FlateDecode":
            try:
                expected_length = self.dictionary[b"DL"]
            except KeyError:
                expected_length = self.dictionary[b"Length"]
            return zlib.decompress(self.buf, bufsize=int(expected_length))
        else:
            msg = f"stream filter {repr(filter)} unknown/unsupported"
            raise NotImplementedError(msg)


def pdf_repr(x: Any) -> bytes:
    if x is True:
        return b"true"
    elif x is False:
        return b"false"
    elif x is None:
        return b"null"
    elif isinstance(x, (PdfName, PdfDict, PdfArray, PdfBinary)):
        return bytes(x)
    elif isinstance(x, (int, float)):
        return str(x).encode("us-ascii")
    elif isinstance(x, time.struct_time):
        return b"(D:" + time.strftime("%Y%m%d%H%M%SZ", x).encode("us-ascii") + b")"
    elif isinstance(x, dict):
        return bytes(PdfDict(x))
    elif isinstance(x, list):
        return bytes(PdfArray(x))
    elif isinstance(x, str):
        return pdf_repr(encode_text(x))
    elif isinstance(x, bytes):
        # XXX escape more chars? handle binary garbage
        x = x.replace(b"\\", b"\\\\")
        x = x.replace(b"(", b"\\(")
        x = x.replace(b")", b"\\)")
        return b"(" + x + b")"
    else:
        return bytes(x)


class PdfParser:
    """Based on
    https://www.adobe.com/content/dam/acom/en/devnet/acrobat/pdfs/PDF32000_2008.pdf
    Supports PDF up to 1.4
    """

    def __init__(
        self,
        filename: str | None = None,
        f: IO[bytes] | None = None,
        buf: bytes | bytearray | None = None,
        start_offset: int = 0,
        mode: str = "rb",
    ) -> None:
        if buf and f:
            msg = "specify buf or f or filename, but not both buf and f"
            raise RuntimeError(msg)
        self.filename = filename
        self.buf: bytes | bytearray | mmap.mmap | None = buf
        self.f = f
        self.start_offset = start_offset
        self.should_close_buf = False
        self.should_close_file = False
        if filename is not None and f is None:
            self.f = f = open(filename, mode)
            self.should_close_file = True
        if f is not None:
            self.buf = self.get_buf_from_file(f)
            self.should_close_buf = True
            if not filename and hasattr(f, "name"):
                self.filename = f.name
        self.cached_objects: dict[IndirectReference, Any] = {}
        self.root_ref: IndirectReference | None
        self.info_ref: IndirectReference | None
        self.pages_ref: IndirectReference | None
        self.last_xref_section_offset: int | None
        if self.buf:
            self.read_pdf_info()
        else:
            self.file_size_total = self.file_size_this = 0
            self.root = PdfDict()
            self.root_ref = None
            self.info = PdfDict()
            self.info_ref = None
            self.page_tree_root = PdfDict()
            self.pages: list[IndirectReference] = []
            self.orig_pages: list[IndirectReference] = []
            self.pages_ref = None
            self.last_xref_section_offset = None
            self.trailer_dict: dict[bytes, Any] = {}
            self.xref_table = XrefTable()
        self.xref_table.reading_finished = True
        if f:
            self.seek_end()

    def __enter__(self) -> PdfParser:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def start_writing(self) -> None:
        self.close_buf()
        self.seek_end()

    def close_buf(self) -> None:
        if isinstance(self.buf, mmap.mmap):
            self.buf.close()
        self.buf = None

    def close(self) -> None:
        if self.should_close_buf:
            self.close_buf()
        if self.f is not None and self.should_close_file:
            self.f.close()
            self.f = None

    def seek_end(self) -> None:
        assert self.f is not None
        self.f.seek(0, os.SEEK_END)

    def write_header(self) -> None:
        assert self.f is not None
        self.f.write(b"%PDF-1.4\n")

    def write_comment(self, s: str) -> None:
        assert self.f is not None
        self.f.write(f"% {s}\n".encode())

    def write_catalog(self) -> IndirectReference:
        assert self.f is not None
        self.del_root()
        self.root_ref = self.next_object_id(self.f.tell())
        self.pages_ref = self.next_object_id(0)
        self.rewrite_pages()
        self.write_obj(self.root_ref, Type=PdfName(b"Catalog"), Pages=self.pages_ref)
        self.write_obj(
            self.pages_ref,
            Type=PdfName(b"Pages"),
            Count=len(self.pages),
            Kids=self.pages,
        )
        return self.root_ref

    def rewrite_pages(self) -> None:
        pages_tree_nodes_to_delete = []
        for i, page_ref in enumerate(self.orig_pages):
            page_info = self.cached_objects[page_ref]
            del self.xref_table[page_ref.object_id]
            pages_tree_nodes_to_delete.append(page_info[PdfName(b"Parent")])
            if page_ref not in self.pages:
                # the page has been deleted
                continue
            # make dict keys into strings for passing to write_page
            stringified_page_info = {}
            for key, value in page_info.items():
                # key should be a PdfName
                stringified_page_info[key.name_as_str()] = value
            stringified_page_info["Parent"] = self.pages_ref
            new_page_ref = self.write_page(None, **stringified_page_info)
            for j, cur_page_ref in enumerate(self.pages):
                if cur_page_ref == page_ref:
                    # replace the page reference with the new one
                    self.pages[j] = new_page_ref
        # delete redundant Pages tree nodes from xref table
        for pages_tree_node_ref in pages_tree_nodes_to_delete:
            while pages_tree_node_ref:
                pages_tree_node = self.cached_objects[pages_tree_node_ref]
                if pages_tree_node_ref.object_id in self.xref_table:
                    del self.xref_table[pages_tree_node_ref.object_id]
                pages_tree_node_ref = pages_tree_node.get(b"Parent", None)
        self.orig_pages = []

    def write_xref_and_trailer(
        self, new_root_ref: IndirectReference | None = None
    ) -> None:
        assert self.f is not None
        if new_root_ref:
            self.del_root()
            self.root_ref = new_root_ref
        if self.info:
            self.info_ref = self.write_obj(None, self.info)
        start_xref = self.xref_table.write(self.f)
        num_entries = len(self.xref_table)
        trailer_dict: dict[str | bytes, Any] = {
            b"Root": self.root_ref,
            b"Size": num_entries,
        }
        if self.last_xref_section_offset is not None:
            trailer_dict[b"Prev"] = self.last_xref_section_offset
        if self.info:
            trailer_dict[b"Info"] = self.info_ref
        self.last_xref_section_offset = start_xref
        self.f.write(
            b"trailer\n"
            + bytes(PdfDict(trailer_dict))
            + b"\nstartxref\n%d\n%%%%EOF" % start_xref
        )

    def write_page(
        self, ref: int | IndirectReference | None, *objs: Any, **dict_obj: Any
    ) -> IndirectReference:
        obj_ref = self.pages[ref] if isinstance(ref, int) else ref
        if "Type" not in dict_obj:
            dict_obj["Type"] = PdfName(b"Page")
        if "Parent" not in dict_obj:
            dict_obj["Parent"] = self.pages_ref
        return self.write_obj(obj_ref, *objs, **dict_obj)

    def write_obj(
        self, ref: IndirectReference | None, *objs: Any, **dict_obj: Any
    ) -> IndirectReference:
        assert self.f is not None
        f = self.f
        if ref is None:
            ref = self.next_object_id(f.tell())
        else:
            self.xref_table[ref.object_id] = (f.tell(), ref.generation)
        f.write(bytes(IndirectObjectDef(*ref)))
        stream = dict_obj.pop("stream", None)
        if stream is not None:
            dict_obj["Length"] = len(stream)
        if dict_obj:
            f.write(pdf_repr(dict_obj))
        for obj in objs:
            f.write(pdf_repr(obj))
        if stream is not None:
            f.write(b"stream\n")
            f.write(stream)
            f.write(b"\nendstream\n")
        f.write(b"endobj\n")
        return ref

    def del_root(self) -> None:
        if self.root_ref is None:
            return
        del self.xref_table[self.root_ref.object_id]
        del self.xref_table[self.root[b"Pages"].object_id]

    @staticmethod
    def get_buf_from_file(f: IO[bytes]) -> bytes | mmap.mmap:
        if hasattr(f, "getbuffer"):
            return f.getbuffer()
        elif hasattr(f, "getvalue"):
            return f.getvalue()
        else:
            try:
                return mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            except ValueError:  # cannot mmap an empty file
                return b""

    def read_pdf_info(self) -> None:
        assert self.buf is not None
        self.file_size_total = len(self.buf)
        self.file_size_this = self.file_size_total - self.start_offset
        self.read_trailer()
        check_format_condition(
            self.trailer_dict.get(b"Root") is not None, "Root is missing"
        )
        self.root_ref = self.trailer_dict[b"Root"]
        assert self.root_ref is not None
        self.info_ref = self.trailer_dict.get(b"Info", None)
        self.root = PdfDict(self.read_indirect(self.root_ref))
        if self.info_ref is None:
            self.info = PdfDict()
        else:
            self.info = PdfDict(self.read_indirect(self.info_ref))
        check_format_condition(b"Type" in self.root, "/Type missing in Root")
        check_format_condition(
            self.root[b"Type"] == b"Catalog", "/Type in Root is not /Catalog"
        )
        check_format_condition(
            self.root.get(b"Pages") is not None, "/Pages missing in Root"
        )
        check_format_condition(
            isinstance(self.root[b"Pages"], IndirectReference),
            "/Pages in Root is not an indirect reference",
        )
        self.pages_ref = self.root[b"Pages"]
        assert self.pages_ref is not None
        self.page_tree_root = self.read_indirect(self.pages_ref)
        self.pages = self.linearize_page_tree(self.page_tree_root)
        # save the original list of page references
        # in case the user modifies, adds or deletes some pages
        # and we need to rewrite the pages and their list
        self.orig_pages = self.pages[:]

    def next_object_id(self, offset: int | None = None) -> IndirectReference:
        try:
            # TODO: support reuse of deleted objects
            reference = IndirectReference(max(self.xref_table.keys()) + 1, 0)
        except ValueError:
            reference = IndirectReference(1, 0)
        if offset is not None:
            self.xref_table[reference.object_id] = (offset, 0)
        return reference

    delimiter = rb"[][()<>{}/%]"
    delimiter_or_ws = rb"[][()<>{}/%\000\011\012\014\015\040]"
    whitespace = rb"[\000\011\012\014\015\040]"
    whitespace_or_hex = rb"[\000\011\012\014\015\0400-9a-fA-F]"
    whitespace_optional = whitespace + b"*"
    whitespace_mandatory = whitespace + b"+"
    # No "\012" aka "\n" or "\015" aka "\r":
    whitespace_optional_no_nl = rb"[\000\011\014\040]*"
    newline_only = rb"[\r\n]+"
    newline = whitespace_optional_no_nl + newline_only + whitespace_optional_no_nl
    re_trailer_end = re.compile(
        whitespace_mandatory
        + rb"trailer"
        + whitespace_optional
        + rb"<<(.*>>)"
        + newline
        + rb"startxref"
        + newline
        + rb"([0-9]+)"
        + newline
        + rb"%%EOF"
        + whitespace_optional
        + rb"$",
        re.DOTALL,
    )
    re_trailer_prev = re.compile(
        whitespace_optional
        + rb"trailer"
        + whitespace_optional
        + rb"<<(.*?>>)"
        + newline
        + rb"startxref"
        + newline
        + rb"([0-9]+)"
        + newline
        + rb"%%EOF"
        + whitespace_optional,
        re.DOTALL,
    )

    def read_trailer(self) -> None:
        assert self.buf is not None
        search_start_offset = len(self.buf) - 16384
        if search_start_offset < self.start_offset:
            search_start_offset = self.start_offset
        m = self.re_trailer_end.search(self.buf, search_start_offset)
        check_format_condition(m is not None, "trailer end not found")
        # make sure we found the LAST trailer
        last_match = m
        while m:
            last_match = m
            m = self.re_trailer_end.search(self.buf, m.start() + 16)
        if not m:
            m = last_match
        assert m is not None
        trailer_data = m.group(1)
        self.last_xref_section_offset = int(m.group(2))
        self.trailer_dict = self.interpret_trailer(trailer_data)
        self.xref_table = XrefTable()
        self.read_xref_table(xref_section_offset=self.last_xref_section_offset)
        if b"Prev" in self.trailer_dict:
            self.read_prev_trailer(self.trailer_dict[b"Prev"])

    def read_prev_trailer(self, xref_section_offset: int) -> None:
        assert self.buf is not None
        trailer_offset = self.read_xref_table(xref_section_offset=xref_section_offset)
        m = self.re_trailer_prev.search(
            self.buf[trailer_offset : trailer_offset + 16384]
        )
        check_format_condition(m is not None, "previous trailer not found")
        assert m is not None
        trailer_data = m.group(1)
        check_format_condition(
            int(m.group(2)) == xref_section_offset,
            "xref section offset in previous trailer doesn't match what was expected",
        )
        trailer_dict = self.interpret_trailer(trailer_data)
        if b"Prev" in trailer_dict:
            self.read_prev_trailer(trailer_dict[b"Prev"])

    re_whitespace_optional = re.compile(whitespace_optional)
    re_name = re.compile(
        whitespace_optional
        + rb"/([!-$&'*-.0-;=?-Z\\^-z|~]+)(?="
        + delimiter_or_ws
        + rb")"
    )
    re_dict_start = re.compile(whitespace_optional + rb"<<")
    re_dict_end = re.compile(whitespace_optional + rb">>" + whitespace_optional)

    @classmethod
    def interpret_trailer(cls, trailer_data: bytes) -> dict[bytes, Any]:
        trailer = {}
        offset = 0
        while True:
            m = cls.re_name.match(trailer_data, offset)
            if not m:
                m = cls.re_dict_end.match(trailer_data, offset)
                check_format_condition(
                    m is not None and m.end() == len(trailer_data),
                    "name not found in trailer, remaining data: "
                    + repr(trailer_data[offset:]),
                )
                break
            key = cls.interpret_name(m.group(1))
            assert isinstance(key, bytes)
            value, value_offset = cls.get_value(trailer_data, m.end())
            trailer[key] = value
            if value_offset is None:
                break
            offset = value_offset
        check_format_condition(
            b"Size" in trailer and isinstance(trailer[b"Size"], int),
            "/Size not in trailer or not an integer",
        )
        check_format_condition(
            b"Root" in trailer and isinstance(trailer[b"Root"], IndirectReference),
            "/Root not in trailer or not an indirect reference",
        )
        return trailer

    re_hashes_in_name = re.compile(rb"([^#]*)(#([0-9a-fA-F]{2}))?")

    @classmethod
    def interpret_name(cls, raw: bytes, as_text: bool = False) -> str | bytes:
        name = b""
        for m in cls.re_hashes_in_name.finditer(raw):
            if m.group(3):
                name += m.group(1) + bytearray.fromhex(m.group(3).decode("us-ascii"))
            else:
                name += m.group(1)
        if as_text:
            return name.decode("utf-8")
        else:
            return bytes(name)

    re_null = re.compile(whitespace_optional + rb"null(?=" + delimiter_or_ws + rb")")
    re_true = re.compile(whitespace_optional + rb"true(?=" + delimiter_or_ws + rb")")
    re_false = re.compile(whitespace_optional + rb"false(?=" + delimiter_or_ws + rb")")
    re_int = re.compile(
        whitespace_optional + rb"([-+]?[0-9]+)(?=" + delimiter_or_ws + rb")"
    )
    re_real = re.compile(
        whitespace_optional
        + rb"([-+]?([0-9]+\.[0-9]*|[0-9]*\.[0-9]+))(?="
        + delimiter_or_ws
        + rb")"
    )
    re_array_start = re.compile(whitespace_optional + rb"\[")
    re_array_end = re.compile(whitespace_optional + rb"]")
    re_string_hex = re.compile(
        whitespace_optional + rb"<(" + whitespace_or_hex + rb"*)>"
    )
    re_string_lit = re.compile(whitespace_optional + rb"\(")
    re_indirect_reference = re.compile(
        whitespace_optional
        + rb"([-+]?[0-9]+)"
        + whitespace_mandatory
        + rb"([-+]?[0-9]+)"
        + whitespace_mandatory
        + rb"R(?="
        + delimiter_or_ws
        + rb")"
    )
    re_indirect_def_start = re.compile(
        whitespace_optional
        + rb"([-+]?[0-9]+)"
        + whitespace_mandatory
        + rb"([-+]?[0-9]+)"
        + whitespace_mandatory
        + rb"obj(?="
        + delimiter_or_ws
        + rb")"
    )
    re_indirect_def_end = re.compile(
        whitespace_optional + rb"endobj(?=" + delimiter_or_ws + rb")"
    )
    re_comment = re.compile(
        rb"(" + whitespace_optional + rb"%[^\r\n]*" + newline + rb")*"
    )
    re_stream_start = re.compile(whitespace_optional + rb"stream\r?\n")
    re_stream_end = re.compile(
        whitespace_optional + rb"endstream(?=" + delimiter_or_ws + rb")"
    )

    @classmethod
    def get_value(
        cls,
        data: bytes | bytearray | mmap.mmap,
        offset: int,
        expect_indirect: IndirectReference | None = None,
        max_nesting: int = -1,
    ) -> tuple[Any, int | None]:
        if max_nesting == 0:
            return None, None
        m = cls.re_comment.match(data, offset)
        if m:
            offset = m.end()
        m = cls.re_indirect_def_start.match(data, offset)
        if m:
            check_format_condition(
                int(m.group(1)) > 0,
                "indirect object definition: object ID must be greater than 0",
            )
            check_format_condition(
                int(m.group(2)) >= 0,
                "indirect object definition: generation must be non-negative",
            )
            check_format_condition(
                expect_indirect is None
                or expect_indirect
                == IndirectReference(int(m.group(1)), int(m.group(2))),
                "indirect object definition different than expected",
            )
            object, object_offset = cls.get_value(
                data, m.end(), max_nesting=max_nesting - 1
            )
            if object_offset is None:
                return object, None
            m = cls.re_indirect_def_end.match(data, object_offset)
            check_format_condition(
                m is not None, "indirect object definition end not found"
            )
            assert m is not None
            return object, m.end()
        check_format_condition(
            not expect_indirect, "indirect object definition not found"
        )
        m = cls.re_indirect_reference.match(data, offset)
        if m:
            check_format_condition(
                int(m.group(1)) > 0,
                "indirect object reference: object ID must be greater than 0",
            )
            check_format_condition(
                int(m.group(2)) >= 0,
                "indirect object reference: generation must be non-negative",
            )
            return IndirectReference(int(m.group(1)), int(m.group(2))), m.end()
        m = cls.re_dict_start.match(data, offset)
        if m:
            offset = m.end()
            result: dict[Any, Any] = {}
            m = cls.re_dict_end.match(data, offset)
            current_offset: int | None = offset
            while not m:
                assert current_offset is not None
                key, current_offset = cls.get_value(
                    data, current_offset, max_nesting=max_nesting - 1
                )
                if current_offset is None:
                    return result, None
                value, current_offset = cls.get_value(
                    data, current_offset, max_nesting=max_nesting - 1
                )
                result[key] = value
                if current_offset is None:
                    return result, None
                m = cls.re_dict_end.match(data, current_offset)
            current_offset = m.end()
            m = cls.re_stream_start.match(data, current_offset)
            if m:
                stream_len = result.get(b"Length")
                if stream_len is None or not isinstance(stream_len, int):
                    msg = f"bad or missing Length in stream dict ({stream_len})"
                    raise PdfFormatError(msg)
                stream_data = data[m.end() : m.end() + stream_len]
                m = cls.re_stream_end.match(data, m.end() + stream_len)
                check_format_condition(m is not None, "stream end not found")
                assert m is not None
                current_offset = m.end()
                return PdfStream(PdfDict(result), stream_data), current_offset
            return PdfDict(result), current_offset
        m = cls.re_array_start.match(data, offset)
        if m:
            offset = m.end()
            results = []
            m = cls.re_array_end.match(data, offset)
            current_offset = offset
            while not m:
                assert current_offset is not None
                value, current_offset = cls.get_value(
                    data, current_offset, max_nesting=max_nesting - 1
                )
                results.append(value)
                if current_offset is None:
                    return results, None
                m = cls.re_array_end.match(data, current_offset)
            return results, m.end()
        m = cls.re_null.match(data, offset)
        if m:
            return None, m.end()
        m = cls.re_true.match(data, offset)
        if m:
            return True, m.end()
        m = cls.re_false.match(data, offset)
        if m:
            return False, m.end()
        m = cls.re_name.match(data, offset)
        if m:
            return PdfName(cls.interpret_name(m.group(1))), m.end()
        m = cls.re_int.match(data, offset)
        if m:
            return int(m.group(1)), m.end()
        m = cls.re_real.match(data, offset)
        if m:
            # XXX Decimal instead of float???
            return float(m.group(1)), m.end()
        m = cls.re_string_hex.match(data, offset)
        if m:
            # filter out whitespace
            hex_string = bytearray(
                b for b in m.group(1) if b in b"0123456789abcdefABCDEF"
            )
            if len(hex_string) % 2 == 1:
                # append a 0 if the length is not even - yes, at the end
                hex_string.append(ord(b"0"))
            return bytearray.fromhex(hex_string.decode("us-ascii")), m.end()
        m = cls.re_string_lit.match(data, offset)
        if m:
            return cls.get_literal_string(data, m.end())
        # return None, offset  # fallback (only for debugging)
        msg = f"unrecognized object: {repr(data[offset : offset + 32])}"
        raise PdfFormatError(msg)

    re_lit_str_token = re.compile(
        rb"(\\[nrtbf()\\])|(\\[0-9]{1,3})|(\\(\r\n|\r|\n))|(\r\n|\r|\n)|(\()|(\))"
    )
    escaped_chars = {
        b"n": b"\n",
        b"r": b"\r",
        b"t": b"\t",
        b"b": b"\b",
        b"f": b"\f",
        b"(": b"(",
        b")": b")",
        b"\\": b"\\",
        ord(b"n"): b"\n",
        ord(b"r"): b"\r",
        ord(b"t"): b"\t",
        ord(b"b"): b"\b",
        ord(b"f"): b"\f",
        ord(b"("): b"(",
        ord(b")"): b")",
        ord(b"\\"): b"\\",
    }

    @classmethod
    def get_literal_string(
        cls, data: bytes | bytearray | mmap.mmap, offset: int
    ) -> tuple[bytes, int]:
        nesting_depth = 0
        result = bytearray()
        for m in cls.re_lit_str_token.finditer(data, offset):
            result.extend(data[offset : m.start()])
            if m.group(1):
                result.extend(cls.escaped_chars[m.group(1)[1]])
            elif m.group(2):
                result.append(int(m.group(2)[1:], 8))
            elif m.group(3):
                pass
            elif m.group(5):
                result.extend(b"\n")
            elif m.group(6):
                result.extend(b"(")
                nesting_depth += 1
            elif m.group(7):
                if nesting_depth == 0:
                    return bytes(result), m.end()
                result.extend(b")")
                nesting_depth -= 1
            offset = m.end()
        msg = "unfinished literal string"
        raise PdfFormatError(msg)

    re_xref_section_start = re.compile(whitespace_optional + rb"xref" + newline)
    re_xref_subsection_start = re.compile(
        whitespace_optional
        + rb"([0-9]+)"
        + whitespace_mandatory
        + rb"([0-9]+)"
        + whitespace_optional
        + newline_only
    )
    re_xref_entry = re.compile(rb"([0-9]{10}) ([0-9]{5}) ([fn])( \r| \n|\r\n)")

    def read_xref_table(self, xref_section_offset: int) -> int:
        assert self.buf is not None
        subsection_found = False
        m = self.re_xref_section_start.match(
            self.buf, xref_section_offset + self.start_offset
        )
        check_format_condition(m is not None, "xref section start not found")
        assert m is not None
        offset = m.end()
        while True:
            m = self.re_xref_subsection_start.match(self.buf, offset)
            if not m:
                check_format_condition(
                    subsection_found, "xref subsection start not found"
                )
                break
            subsection_found = True
            offset = m.end()
            first_object = int(m.group(1))
            num_objects = int(m.group(2))
            for i in range(first_object, first_object + num_objects):
                m = self.re_xref_entry.match(self.buf, offset)
                check_format_condition(m is not None, "xref entry not found")
                assert m is not None
                offset = m.end()
                is_free = m.group(3) == b"f"
                if not is_free:
                    generation = int(m.group(2))
                    new_entry = (int(m.group(1)), generation)
                    if i not in self.xref_table:
                        self.xref_table[i] = new_entry
        return offset

    def read_indirect(self, ref: IndirectReference, max_nesting: int = -1) -> Any:
        offset, generation = self.xref_table[ref[0]]
        check_format_condition(
            generation == ref[1],
            f"expected to find generation {ref[1]} for object ID {ref[0]} in xref "
            f"table, instead found generation {generation} at offset {offset}",
        )
        assert self.buf is not None
        value = self.get_value(
            self.buf,
            offset + self.start_offset,
            expect_indirect=IndirectReference(*ref),
            max_nesting=max_nesting,
        )[0]
        self.cached_objects[ref] = value
        return value

    def linearize_page_tree(
        self, node: PdfDict | None = None
    ) -> list[IndirectReference]:
        page_node = node if node is not None else self.page_tree_root
        check_format_condition(
            page_node[b"Type"] == b"Pages", "/Type of page tree node is not /Pages"
        )
        pages = []
        for kid in page_node[b"Kids"]:
            kid_object = self.read_indirect(kid)
            if kid_object[b"Type"] == b"Page":
                pages.append(kid)
            else:
                pages.extend(self.linearize_page_tree(node=kid_object))
        return pages

# === NexusCore/openenv\Lib\site-packages\matplotlib\backends\backend_qt.py ===
import functools
import os
import sys
import traceback

import matplotlib as mpl
from matplotlib import _api, backend_tools, cbook
from matplotlib._pylab_helpers import Gcf
from matplotlib.backend_bases import (
    _Backend, FigureCanvasBase, FigureManagerBase, NavigationToolbar2,
    TimerBase, cursors, ToolContainerBase, MouseButton,
    CloseEvent, KeyEvent, LocationEvent, MouseEvent, ResizeEvent,
    _allow_interrupt)
import matplotlib.backends.qt_editor.figureoptions as figureoptions
from . import qt_compat
from .qt_compat import (
    QtCore, QtGui, QtWidgets, __version__, QT_API, _to_int, _isdeleted)


# SPECIAL_KEYS are Qt::Key that do *not* return their Unicode name
# instead they have manually specified names.
SPECIAL_KEYS = {
    _to_int(getattr(QtCore.Qt.Key, k)): v for k, v in [
        ("Key_Escape", "escape"),
        ("Key_Tab", "tab"),
        ("Key_Backspace", "backspace"),
        ("Key_Return", "enter"),
        ("Key_Enter", "enter"),
        ("Key_Insert", "insert"),
        ("Key_Delete", "delete"),
        ("Key_Pause", "pause"),
        ("Key_SysReq", "sysreq"),
        ("Key_Clear", "clear"),
        ("Key_Home", "home"),
        ("Key_End", "end"),
        ("Key_Left", "left"),
        ("Key_Up", "up"),
        ("Key_Right", "right"),
        ("Key_Down", "down"),
        ("Key_PageUp", "pageup"),
        ("Key_PageDown", "pagedown"),
        ("Key_Shift", "shift"),
        # In macOS, the control and super (aka cmd/apple) keys are switched.
        ("Key_Control", "control" if sys.platform != "darwin" else "cmd"),
        ("Key_Meta", "meta" if sys.platform != "darwin" else "control"),
        ("Key_Alt", "alt"),
        ("Key_CapsLock", "caps_lock"),
        ("Key_F1", "f1"),
        ("Key_F2", "f2"),
        ("Key_F3", "f3"),
        ("Key_F4", "f4"),
        ("Key_F5", "f5"),
        ("Key_F6", "f6"),
        ("Key_F7", "f7"),
        ("Key_F8", "f8"),
        ("Key_F9", "f9"),
        ("Key_F10", "f10"),
        ("Key_F10", "f11"),
        ("Key_F12", "f12"),
        ("Key_Super_L", "super"),
        ("Key_Super_R", "super"),
    ]
}
# Define which modifier keys are collected on keyboard events.
# Elements are (Qt::KeyboardModifiers, Qt::Key) tuples.
# Order determines the modifier order (ctrl+alt+...) reported by Matplotlib.
_MODIFIER_KEYS = [
    (_to_int(getattr(QtCore.Qt.KeyboardModifier, mod)),
     _to_int(getattr(QtCore.Qt.Key, key)))
    for mod, key in [
        ("ControlModifier", "Key_Control"),
        ("AltModifier", "Key_Alt"),
        ("ShiftModifier", "Key_Shift"),
        ("MetaModifier", "Key_Meta"),
    ]
]
cursord = {
    k: getattr(QtCore.Qt.CursorShape, v) for k, v in [
        (cursors.MOVE, "SizeAllCursor"),
        (cursors.HAND, "PointingHandCursor"),
        (cursors.POINTER, "ArrowCursor"),
        (cursors.SELECT_REGION, "CrossCursor"),
        (cursors.WAIT, "WaitCursor"),
        (cursors.RESIZE_HORIZONTAL, "SizeHorCursor"),
        (cursors.RESIZE_VERTICAL, "SizeVerCursor"),
    ]
}


# lru_cache keeps a reference to the QApplication instance, keeping it from
# being GC'd.
@functools.lru_cache(1)
def _create_qApp():
    app = QtWidgets.QApplication.instance()

    # Create a new QApplication and configure it if none exists yet, as only
    # one QApplication can exist at a time.
    if app is None:
        # display_is_valid returns False only if on Linux and neither X11
        # nor Wayland display can be opened.
        if not mpl._c_internal_utils.display_is_valid():
            raise RuntimeError('Invalid DISPLAY variable')

        # Check to make sure a QApplication from a different major version
        # of Qt is not instantiated in the process
        if QT_API in {'PyQt6', 'PySide6'}:
            other_bindings = ('PyQt5', 'PySide2')
            qt_version = 6
        elif QT_API in {'PyQt5', 'PySide2'}:
            other_bindings = ('PyQt6', 'PySide6')
            qt_version = 5
        else:
            raise RuntimeError("Should never be here")

        for binding in other_bindings:
            mod = sys.modules.get(f'{binding}.QtWidgets')
            if mod is not None and mod.QApplication.instance() is not None:
                other_core = sys.modules.get(f'{binding}.QtCore')
                _api.warn_external(
                    f'Matplotlib is using {QT_API} which wraps '
                    f'{QtCore.qVersion()} however an instantiated '
                    f'QApplication from {binding} which wraps '
                    f'{other_core.qVersion()} exists.  Mixing Qt major '
                    'versions may not work as expected.'
                )
                break
        if qt_version == 5:
            try:
                QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
            except AttributeError:  # Only for Qt>=5.6, <6.
                pass
        try:
            QtWidgets.QApplication.setHighDpiScaleFactorRoundingPolicy(
                QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
        except AttributeError:  # Only for Qt>=5.14.
            pass
        app = QtWidgets.QApplication(["matplotlib"])
        if sys.platform == "darwin":
            image = str(cbook._get_data_path('images/matplotlib.svg'))
            icon = QtGui.QIcon(image)
            app.setWindowIcon(icon)
        app.setQuitOnLastWindowClosed(True)
        cbook._setup_new_guiapp()
        if qt_version == 5:
            app.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)

    return app


def _allow_interrupt_qt(qapp_or_eventloop):
    """A context manager that allows terminating a plot by sending a SIGINT."""

    # Use QSocketNotifier to read the socketpair while the Qt event loop runs.

    def prepare_notifier(rsock):
        sn = QtCore.QSocketNotifier(rsock.fileno(), QtCore.QSocketNotifier.Type.Read)

        @sn.activated.connect
        def _may_clear_sock():
            # Running a Python function on socket activation gives the interpreter a
            # chance to handle the signal in Python land.  We also need to drain the
            # socket with recv() to re-arm it, because it will be written to as part of
            # the wakeup.  (We need this in case set_wakeup_fd catches a signal other
            # than SIGINT and we shall continue waiting.)
            try:
                rsock.recv(1)
            except BlockingIOError:
                # This may occasionally fire too soon or more than once on Windows, so
                # be forgiving about reading an empty socket.
                pass

        return sn  # Actually keep the notifier alive.

    def handle_sigint():
        if hasattr(qapp_or_eventloop, 'closeAllWindows'):
            qapp_or_eventloop.closeAllWindows()
        qapp_or_eventloop.quit()

    return _allow_interrupt(prepare_notifier, handle_sigint)


class TimerQT(TimerBase):
    """Subclass of `.TimerBase` using QTimer events."""

    def __init__(self, *args, **kwargs):
        # Create a new timer and connect the timeout() signal to the
        # _on_timer method.
        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(self._on_timer)
        super().__init__(*args, **kwargs)

    def __del__(self):
        # The check for deletedness is needed to avoid an error at animation
        # shutdown with PySide2.
        if not _isdeleted(self._timer):
            self._timer_stop()

    def _timer_set_single_shot(self):
        self._timer.setSingleShot(self._single)

    def _timer_set_interval(self):
        self._timer.setInterval(self._interval)

    def _timer_start(self):
        self._timer.start()

    def _timer_stop(self):
        self._timer.stop()


class FigureCanvasQT(FigureCanvasBase, QtWidgets.QWidget):
    required_interactive_framework = "qt"
    _timer_cls = TimerQT
    manager_class = _api.classproperty(lambda cls: FigureManagerQT)

    buttond = {
        getattr(QtCore.Qt.MouseButton, k): v for k, v in [
            ("LeftButton", MouseButton.LEFT),
            ("RightButton", MouseButton.RIGHT),
            ("MiddleButton", MouseButton.MIDDLE),
            ("XButton1", MouseButton.BACK),
            ("XButton2", MouseButton.FORWARD),
        ]
    }

    def __init__(self, figure=None):
        _create_qApp()
        super().__init__(figure=figure)

        self._draw_pending = False
        self._is_drawing = False
        self._draw_rect_callback = lambda painter: None
        self._in_resize_event = False

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setMouseTracking(True)
        self.resize(*self.get_width_height())

        palette = QtGui.QPalette(QtGui.QColor("white"))
        self.setPalette(palette)

    @QtCore.Slot()
    def _update_pixel_ratio(self):
        if self._set_device_pixel_ratio(
                self.devicePixelRatioF() or 1):  # rarely, devicePixelRatioF=0
            # The easiest way to resize the canvas is to emit a resizeEvent
            # since we implement all the logic for resizing the canvas for
            # that event.
            event = QtGui.QResizeEvent(self.size(), self.size())
            self.resizeEvent(event)

    @QtCore.Slot(QtGui.QScreen)
    def _update_screen(self, screen):
        # Handler for changes to a window's attached screen.
        self._update_pixel_ratio()
        if screen is not None:
            screen.physicalDotsPerInchChanged.connect(self._update_pixel_ratio)
            screen.logicalDotsPerInchChanged.connect(self._update_pixel_ratio)

    def showEvent(self, event):
        # Set up correct pixel ratio, and connect to any signal changes for it,
        # once the window is shown (and thus has these attributes).
        window = self.window().windowHandle()
        window.screenChanged.connect(self._update_screen)
        self._update_screen(window.screen())

    def set_cursor(self, cursor):
        # docstring inherited
        self.setCursor(_api.check_getitem(cursord, cursor=cursor))

    def mouseEventCoords(self, pos=None):
        """
        Calculate mouse coordinates in physical pixels.

        Qt uses logical pixels, but the figure is scaled to physical
        pixels for rendering.  Transform to physical pixels so that
        all of the down-stream transforms work as expected.

        Also, the origin is different and needs to be corrected.
        """
        if pos is None:
            pos = self.mapFromGlobal(QtGui.QCursor.pos())
        elif hasattr(pos, "position"):  # qt6 QtGui.QEvent
            pos = pos.position()
        elif hasattr(pos, "pos"):  # qt5 QtCore.QEvent
            pos = pos.pos()
        # (otherwise, it's already a QPoint)
        x = pos.x()
        # flip y so y=0 is bottom of canvas
        y = self.figure.bbox.height / self.device_pixel_ratio - pos.y()
        return x * self.device_pixel_ratio, y * self.device_pixel_ratio

    def enterEvent(self, event):
        # Force querying of the modifiers, as the cached modifier state can
        # have been invalidated while the window was out of focus.
        mods = QtWidgets.QApplication.instance().queryKeyboardModifiers()
        if self.figure is None:
            return
        LocationEvent("figure_enter_event", self,
                      *self.mouseEventCoords(event),
                      modifiers=self._mpl_modifiers(mods),
                      guiEvent=event)._process()

    def leaveEvent(self, event):
        QtWidgets.QApplication.restoreOverrideCursor()
        if self.figure is None:
            return
        LocationEvent("figure_leave_event", self,
                      *self.mouseEventCoords(),
                      modifiers=self._mpl_modifiers(),
                      guiEvent=event)._process()

    def mousePressEvent(self, event):
        button = self.buttond.get(event.button())
        if button is not None and self.figure is not None:
            MouseEvent("button_press_event", self,
                       *self.mouseEventCoords(event), button,
                       modifiers=self._mpl_modifiers(),
                       guiEvent=event)._process()

    def mouseDoubleClickEvent(self, event):
        button = self.buttond.get(event.button())
        if button is not None and self.figure is not None:
            MouseEvent("button_press_event", self,
                       *self.mouseEventCoords(event), button, dblclick=True,
                       modifiers=self._mpl_modifiers(),
                       guiEvent=event)._process()

    def mouseMoveEvent(self, event):
        if self.figure is None:
            return
        MouseEvent("motion_notify_event", self,
                   *self.mouseEventCoords(event),
                   buttons=self._mpl_buttons(event.buttons()),
                   modifiers=self._mpl_modifiers(),
                   guiEvent=event)._process()

    def mouseReleaseEvent(self, event):
        button = self.buttond.get(event.button())
        if button is not None and self.figure is not None:
            MouseEvent("button_release_event", self,
                       *self.mouseEventCoords(event), button,
                       modifiers=self._mpl_modifiers(),
                       guiEvent=event)._process()

    def wheelEvent(self, event):
        # from QWheelEvent::pixelDelta doc: pixelDelta is sometimes not
        # provided (`isNull()`) and is unreliable on X11 ("xcb").
        if (event.pixelDelta().isNull()
                or QtWidgets.QApplication.instance().platformName() == "xcb"):
            steps = event.angleDelta().y() / 120
        else:
            steps = event.pixelDelta().y()
        if steps and self.figure is not None:
            MouseEvent("scroll_event", self,
                       *self.mouseEventCoords(event), step=steps,
                       modifiers=self._mpl_modifiers(),
                       guiEvent=event)._process()

    def keyPressEvent(self, event):
        key = self._get_key(event)
        if key is not None and self.figure is not None:
            KeyEvent("key_press_event", self,
                     key, *self.mouseEventCoords(),
                     guiEvent=event)._process()

    def keyReleaseEvent(self, event):
        key = self._get_key(event)
        if key is not None and self.figure is not None:
            KeyEvent("key_release_event", self,
                     key, *self.mouseEventCoords(),
                     guiEvent=event)._process()

    def resizeEvent(self, event):
        if self._in_resize_event:  # Prevent PyQt6 recursion
            return
        if self.figure is None:
            return
        self._in_resize_event = True
        try:
            w = event.size().width() * self.device_pixel_ratio
            h = event.size().height() * self.device_pixel_ratio
            dpival = self.figure.dpi
            winch = w / dpival
            hinch = h / dpival
            self.figure.set_size_inches(winch, hinch, forward=False)
            # pass back into Qt to let it finish
            QtWidgets.QWidget.resizeEvent(self, event)
            # emit our resize events
            ResizeEvent("resize_event", self)._process()
            self.draw_idle()
        finally:
            self._in_resize_event = False

    def sizeHint(self):
        w, h = self.get_width_height()
        return QtCore.QSize(w, h)

    def minimumSizeHint(self):
        return QtCore.QSize(10, 10)

    @staticmethod
    def _mpl_buttons(buttons):
        buttons = _to_int(buttons)
        # State *after* press/release.
        return {button for mask, button in FigureCanvasQT.buttond.items()
                if _to_int(mask) & buttons}

    @staticmethod
    def _mpl_modifiers(modifiers=None, *, exclude=None):
        if modifiers is None:
            modifiers = QtWidgets.QApplication.instance().keyboardModifiers()
        modifiers = _to_int(modifiers)
        # get names of the pressed modifier keys
        # 'control' is named 'control' when a standalone key, but 'ctrl' when a
        # modifier
        # bit twiddling to pick out modifier keys from modifiers bitmask,
        # if exclude is a MODIFIER, it should not be duplicated in mods
        return [SPECIAL_KEYS[key].replace('control', 'ctrl')
                for mask, key in _MODIFIER_KEYS
                if exclude != key and modifiers & mask]

    def _get_key(self, event):
        event_key = event.key()
        mods = self._mpl_modifiers(exclude=event_key)
        try:
            # for certain keys (enter, left, backspace, etc) use a word for the
            # key, rather than Unicode
            key = SPECIAL_KEYS[event_key]
        except KeyError:
            # Unicode defines code points up to 0x10ffff (sys.maxunicode)
            # QT will use Key_Codes larger than that for keyboard keys that are
            # not Unicode characters (like multimedia keys)
            # skip these
            # if you really want them, you should add them to SPECIAL_KEYS
            if event_key > sys.maxunicode:
                return None

            key = chr(event_key)
            # qt delivers capitalized letters.  fix capitalization
            # note that capslock is ignored
            if 'shift' in mods:
                mods.remove('shift')
            else:
                key = key.lower()

        return '+'.join(mods + [key])

    def flush_events(self):
        # docstring inherited
        QtWidgets.QApplication.instance().processEvents()

    def start_event_loop(self, timeout=0):
        # docstring inherited
        if hasattr(self, "_event_loop") and self._event_loop.isRunning():
            raise RuntimeError("Event loop already running")
        self._event_loop = event_loop = QtCore.QEventLoop()
        if timeout > 0:
            _ = QtCore.QTimer.singleShot(int(timeout * 1000), event_loop.quit)

        with _allow_interrupt_qt(event_loop):
            qt_compat._exec(event_loop)

    def stop_event_loop(self, event=None):
        # docstring inherited
        if hasattr(self, "_event_loop"):
            self._event_loop.quit()

    def draw(self):
        """Render the figure, and queue a request for a Qt draw."""
        # The renderer draw is done here; delaying causes problems with code
        # that uses the result of the draw() to update plot elements.
        if self._is_drawing:
            return
        with cbook._setattr_cm(self, _is_drawing=True):
            super().draw()
        self.update()

    def draw_idle(self):
        """Queue redraw of the Agg buffer and request Qt paintEvent."""
        # The Agg draw needs to be handled by the same thread Matplotlib
        # modifies the scene graph from. Post Agg draw request to the
        # current event loop in order to ensure thread affinity and to
        # accumulate multiple draw requests from event handling.
        # TODO: queued signal connection might be safer than singleShot
        if not (getattr(self, '_draw_pending', False) or
                getattr(self, '_is_drawing', False)):
            self._draw_pending = True
            QtCore.QTimer.singleShot(0, self._draw_idle)

    def blit(self, bbox=None):
        # docstring inherited
        if bbox is None and self.figure:
            bbox = self.figure.bbox  # Blit the entire canvas if bbox is None.
        # repaint uses logical pixels, not physical pixels like the renderer.
        l, b, w, h = (int(pt / self.device_pixel_ratio) for pt in bbox.bounds)
        t = b + h
        self.repaint(l, self.rect().height() - t, w, h)

    def _draw_idle(self):
        with self._idle_draw_cntx():
            if not self._draw_pending:
                return
            self._draw_pending = False
            if self.height() <= 0 or self.width() <= 0:
                return
            try:
                self.draw()
            except Exception:
                # Uncaught exceptions are fatal for PyQt5, so catch them.
                traceback.print_exc()

    def drawRectangle(self, rect):
        # Draw the zoom rectangle to the QPainter.  _draw_rect_callback needs
        # to be called at the end of paintEvent.
        if rect is not None:
            x0, y0, w, h = (int(pt / self.device_pixel_ratio) for pt in rect)
            x1 = x0 + w
            y1 = y0 + h
            def _draw_rect_callback(painter):
                pen = QtGui.QPen(
                    QtGui.QColor("black"),
                    1 / self.device_pixel_ratio
                )

                pen.setDashPattern([3, 3])
                for color, offset in [
                        (QtGui.QColor("black"), 0),
                        (QtGui.QColor("white"), 3),
                ]:
                    pen.setDashOffset(offset)
                    pen.setColor(color)
                    painter.setPen(pen)
                    # Draw the lines from x0, y0 towards x1, y1 so that the
                    # dashes don't "jump" when moving the zoom box.
                    painter.drawLine(x0, y0, x0, y1)
                    painter.drawLine(x0, y0, x1, y0)
                    painter.drawLine(x0, y1, x1, y1)
                    painter.drawLine(x1, y0, x1, y1)
        else:
            def _draw_rect_callback(painter):
                return
        self._draw_rect_callback = _draw_rect_callback
        self.update()


class MainWindow(QtWidgets.QMainWindow):
    closing = QtCore.Signal()

    def closeEvent(self, event):
        self.closing.emit()
        super().closeEvent(event)


class FigureManagerQT(FigureManagerBase):
    """
    Attributes
    ----------
    canvas : `FigureCanvas`
        The FigureCanvas instance
    num : int or str
        The Figure number
    toolbar : qt.QToolBar
        The qt.QToolBar
    window : qt.QMainWindow
        The qt.QMainWindow
    """

    def __init__(self, canvas, num):
        self.window = MainWindow()
        super().__init__(canvas, num)
        self.window.closing.connect(self._widgetclosed)

        if sys.platform != "darwin":
            image = str(cbook._get_data_path('images/matplotlib.svg'))
            icon = QtGui.QIcon(image)
            self.window.setWindowIcon(icon)

        self.window._destroying = False

        if self.toolbar:
            self.window.addToolBar(self.toolbar)
            tbs_height = self.toolbar.sizeHint().height()
        else:
            tbs_height = 0

        # resize the main window so it will display the canvas with the
        # requested size:
        cs = canvas.sizeHint()
        cs_height = cs.height()
        height = cs_height + tbs_height
        self.window.resize(cs.width(), height)

        self.window.setCentralWidget(self.canvas)

        if mpl.is_interactive():
            self.window.show()
            self.canvas.draw_idle()

        # Give the keyboard focus to the figure instead of the manager:
        # StrongFocus accepts both tab and click to focus and will enable the
        # canvas to process event without clicking.
        # https://doc.qt.io/qt-5/qt.html#FocusPolicy-enum
        self.canvas.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.canvas.setFocus()

        self.window.raise_()

    def full_screen_toggle(self):
        if self.window.isFullScreen():
            self.window.showNormal()
        else:
            self.window.showFullScreen()

    def _widgetclosed(self):
        CloseEvent("close_event", self.canvas)._process()
        if self.window._destroying:
            return
        self.window._destroying = True
        try:
            Gcf.destroy(self)
        except AttributeError:
            pass
            # It seems that when the python session is killed,
            # Gcf can get destroyed before the Gcf.destroy
            # line is run, leading to a useless AttributeError.

    def resize(self, width, height):
        # The Qt methods return sizes in 'virtual' pixels so we do need to
        # rescale from physical to logical pixels.
        width = int(width / self.canvas.device_pixel_ratio)
        height = int(height / self.canvas.device_pixel_ratio)
        extra_width = self.window.width() - self.canvas.width()
        extra_height = self.window.height() - self.canvas.height()
        self.canvas.resize(width, height)
        self.window.resize(width + extra_width, height + extra_height)

    @classmethod
    def start_main_loop(cls):
        qapp = QtWidgets.QApplication.instance()
        if qapp:
            with _allow_interrupt_qt(qapp):
                qt_compat._exec(qapp)

    def show(self):
        self.window._destroying = False
        self.window.show()
        if mpl.rcParams['figure.raise_window']:
            self.window.activateWindow()
            self.window.raise_()

    def destroy(self, *args):
        # check for qApp first, as PySide deletes it in its atexit handler
        if QtWidgets.QApplication.instance() is None:
            return
        if self.window._destroying:
            return
        self.window._destroying = True
        if self.toolbar:
            self.toolbar.destroy()
        self.window.close()

    def get_window_title(self):
        return self.window.windowTitle()

    def set_window_title(self, title):
        self.window.setWindowTitle(title)


class NavigationToolbar2QT(NavigationToolbar2, QtWidgets.QToolBar):
    toolitems = [*NavigationToolbar2.toolitems]
    toolitems.insert(
        # Add 'customize' action after 'subplots'
        [name for name, *_ in toolitems].index("Subplots") + 1,
        ("Customize", "Edit axis, curve and image parameters",
         "qt4_editor_options", "edit_parameters"))

    def __init__(self, canvas, parent=None, coordinates=True):
        """coordinates: should we show the coordinates on the right?"""
        QtWidgets.QToolBar.__init__(self, parent)
        self.setAllowedAreas(QtCore.Qt.ToolBarArea(
            _to_int(QtCore.Qt.ToolBarArea.TopToolBarArea) |
            _to_int(QtCore.Qt.ToolBarArea.BottomToolBarArea)))
        self.coordinates = coordinates
        self._actions = {}  # mapping of toolitem method names to QActions.
        self._subplot_dialog = None

        for text, tooltip_text, image_file, callback in self.toolitems:
            if text is None:
                self.addSeparator()
            else:
                slot = getattr(self, callback)
                # https://bugreports.qt.io/browse/PYSIDE-2512
                slot = functools.wraps(slot)(functools.partial(slot))
                slot = QtCore.Slot()(slot)

                a = self.addAction(self._icon(image_file + '.png'),
                                   text, slot)
                self._actions[callback] = a
                if callback in ['zoom', 'pan']:
                    a.setCheckable(True)
                if tooltip_text is not None:
                    a.setToolTip(tooltip_text)

        # Add the (x, y) location widget at the right side of the toolbar
        # The stretch factor is 1 which means any resizing of the toolbar
        # will resize this label instead of the buttons.
        if self.coordinates:
            self.locLabel = QtWidgets.QLabel("", self)
            self.locLabel.setAlignment(QtCore.Qt.AlignmentFlag(
                _to_int(QtCore.Qt.AlignmentFlag.AlignRight) |
                _to_int(QtCore.Qt.AlignmentFlag.AlignVCenter)))

            self.locLabel.setSizePolicy(QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Ignored,
            ))
            labelAction = self.addWidget(self.locLabel)
            labelAction.setVisible(True)

        NavigationToolbar2.__init__(self, canvas)

    def _icon(self, name):
        """
        Construct a `.QIcon` from an image file *name*, including the extension
        and relative to Matplotlib's "images" data directory.
        """
        # use a high-resolution icon with suffix '_large' if available
        # note: user-provided icons may not have '_large' versions
        path_regular = cbook._get_data_path('images', name)
        path_large = path_regular.with_name(
            path_regular.name.replace('.png', '_large.png'))
        filename = str(path_large if path_large.exists() else path_regular)

        pm = QtGui.QPixmap(filename)
        pm.setDevicePixelRatio(
            self.devicePixelRatioF() or 1)  # rarely, devicePixelRatioF=0
        if self.palette().color(self.backgroundRole()).value() < 128:
            icon_color = self.palette().color(self.foregroundRole())
            mask = pm.createMaskFromColor(
                QtGui.QColor('black'),
                QtCore.Qt.MaskMode.MaskOutColor)
            pm.fill(icon_color)
            pm.setMask(mask)
        return QtGui.QIcon(pm)

    def edit_parameters(self):
        axes = self.canvas.figure.get_axes()
        if not axes:
            QtWidgets.QMessageBox.warning(
                self.canvas.parent(), "Error", "There are no Axes to edit.")
            return
        elif len(axes) == 1:
            ax, = axes
        else:
            titles = [
                ax.get_label() or
                ax.get_title() or
                ax.get_title("left") or
                ax.get_title("right") or
                " - ".join(filter(None, [ax.get_xlabel(), ax.get_ylabel()])) or
                f"<anonymous {type(ax).__name__}>"
                for ax in axes]
            duplicate_titles = [
                title for title in titles if titles.count(title) > 1]
            for i, ax in enumerate(axes):
                if titles[i] in duplicate_titles:
                    titles[i] += f" (id: {id(ax):#x})"  # Deduplicate titles.
            item, ok = QtWidgets.QInputDialog.getItem(
                self.canvas.parent(),
                'Customize', 'Select Axes:', titles, 0, False)
            if not ok:
                return
            ax = axes[titles.index(item)]
        figureoptions.figure_edit(ax, self)

    def _update_buttons_checked(self):
        # sync button checkstates to match active mode
        if 'pan' in self._actions:
            self._actions['pan'].setChecked(self.mode.name == 'PAN')
        if 'zoom' in self._actions:
            self._actions['zoom'].setChecked(self.mode.name == 'ZOOM')

    def pan(self, *args):
        super().pan(*args)
        self._update_buttons_checked()

    def zoom(self, *args):
        super().zoom(*args)
        self._update_buttons_checked()

    def set_message(self, s):
        if self.coordinates:
            self.locLabel.setText(s)

    def draw_rubberband(self, event, x0, y0, x1, y1):
        height = self.canvas.figure.bbox.height
        y1 = height - y1
        y0 = height - y0
        rect = [int(val) for val in (x0, y0, x1 - x0, y1 - y0)]
        self.canvas.drawRectangle(rect)

    def remove_rubberband(self):
        self.canvas.drawRectangle(None)

    def configure_subplots(self):
        if self._subplot_dialog is None:
            self._subplot_dialog = SubplotToolQt(
                self.canvas.figure, self.canvas.parent())
            self.canvas.mpl_connect(
                "close_event", lambda e: self._subplot_dialog.reject())
        self._subplot_dialog.update_from_current_subplotpars()
        self._subplot_dialog.setModal(True)
        self._subplot_dialog.show()
        return self._subplot_dialog

    def save_figure(self, *args):
        filetypes = self.canvas.get_supported_filetypes_grouped()
        sorted_filetypes = sorted(filetypes.items())
        default_filetype = self.canvas.get_default_filetype()

        startpath = os.path.expanduser(mpl.rcParams['savefig.directory'])
        start = os.path.join(startpath, self.canvas.get_default_filename())
        filters = []
        selectedFilter = None
        for name, exts in sorted_filetypes:
            exts_list = " ".join(['*.%s' % ext for ext in exts])
            filter = f'{name} ({exts_list})'
            if default_filetype in exts:
                selectedFilter = filter
            filters.append(filter)
        filters = ';;'.join(filters)

        fname, filter = QtWidgets.QFileDialog.getSaveFileName(
            self.canvas.parent(), "Choose a filename to save to", start,
            filters, selectedFilter)
        if fname:
            # Save dir for next time, unless empty str (i.e., use cwd).
            if startpath != "":
                mpl.rcParams['savefig.directory'] = os.path.dirname(fname)
            try:
                self.canvas.figure.savefig(fname)
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self, "Error saving file", str(e),
                    QtWidgets.QMessageBox.StandardButton.Ok,
                    QtWidgets.QMessageBox.StandardButton.NoButton)
        return fname

    def set_history_buttons(self):
        can_backward = self._nav_stack._pos > 0
        can_forward = self._nav_stack._pos < len(self._nav_stack) - 1
        if 'back' in self._actions:
            self._actions['back'].setEnabled(can_backward)
        if 'forward' in self._actions:
            self._actions['forward'].setEnabled(can_forward)


class SubplotToolQt(QtWidgets.QDialog):
    def __init__(self, targetfig, parent):
        super().__init__(parent)
        self.setWindowIcon(QtGui.QIcon(
            str(cbook._get_data_path("images/matplotlib.png"))))
        self.setObjectName("SubplotTool")
        self._spinboxes = {}
        main_layout = QtWidgets.QHBoxLayout()
        self.setLayout(main_layout)
        for group, spinboxes, buttons in [
                ("Borders",
                 ["top", "bottom", "left", "right"],
                 [("Export values", self._export_values)]),
                ("Spacings",
                 ["hspace", "wspace"],
                 [("Tight layout", self._tight_layout),
                  ("Reset", self._reset),
                  ("Close", self.close)])]:
            layout = QtWidgets.QVBoxLayout()
            main_layout.addLayout(layout)
            box = QtWidgets.QGroupBox(group)
            layout.addWidget(box)
            inner = QtWidgets.QFormLayout(box)
            for name in spinboxes:
                self._spinboxes[name] = spinbox = QtWidgets.QDoubleSpinBox()
                spinbox.setRange(0, 1)
                spinbox.setDecimals(3)
                spinbox.setSingleStep(0.005)
                spinbox.setKeyboardTracking(False)
                spinbox.valueChanged.connect(self._on_value_changed)
                inner.addRow(name, spinbox)
            layout.addStretch(1)
            for name, method in buttons:
                button = QtWidgets.QPushButton(name)
                # Don't trigger on <enter>, which is used to input values.
                button.setAutoDefault(False)
                button.clicked.connect(method)
                layout.addWidget(button)
                if name == "Close":
                    button.setFocus()
        self._figure = targetfig
        self._defaults = {}
        self._export_values_dialog = None
        self.update_from_current_subplotpars()

    def update_from_current_subplotpars(self):
        self._defaults = {spinbox: getattr(self._figure.subplotpars, name)
                          for name, spinbox in self._spinboxes.items()}
        self._reset()  # Set spinbox current values without triggering signals.

    def _export_values(self):
        # Explicitly round to 3 decimals (which is also the spinbox precision)
        # to avoid numbers of the form 0.100...001.
        self._export_values_dialog = QtWidgets.QDialog()
        layout = QtWidgets.QVBoxLayout()
        self._export_values_dialog.setLayout(layout)
        text = QtWidgets.QPlainTextEdit()
        text.setReadOnly(True)
        layout.addWidget(text)
        text.setPlainText(
            ",\n".join(f"{attr}={spinbox.value():.3}"
                       for attr, spinbox in self._spinboxes.items()))
        # Adjust the height of the text widget to fit the whole text, plus
        # some padding.
        size = text.maximumSize()
        size.setHeight(
            QtGui.QFontMetrics(text.document().defaultFont())
            .size(0, text.toPlainText()).height() + 20)
        text.setMaximumSize(size)
        self._export_values_dialog.show()

    def _on_value_changed(self):
        spinboxes = self._spinboxes
        # Set all mins and maxes, so that this can also be used in _reset().
        for lower, higher in [("bottom", "top"), ("left", "right")]:
            spinboxes[higher].setMinimum(spinboxes[lower].value() + .001)
            spinboxes[lower].setMaximum(spinboxes[higher].value() - .001)
        self._figure.subplots_adjust(
            **{attr: spinbox.value() for attr, spinbox in spinboxes.items()})
        self._figure.canvas.draw_idle()

    def _tight_layout(self):
        self._figure.tight_layout()
        for attr, spinbox in self._spinboxes.items():
            spinbox.blockSignals(True)
            spinbox.setValue(getattr(self._figure.subplotpars, attr))
            spinbox.blockSignals(False)
        self._figure.canvas.draw_idle()

    def _reset(self):
        for spinbox, value in self._defaults.items():
            spinbox.setRange(0, 1)
            spinbox.blockSignals(True)
            spinbox.setValue(value)
            spinbox.blockSignals(False)
        self._on_value_changed()


class ToolbarQt(ToolContainerBase, QtWidgets.QToolBar):
    def __init__(self, toolmanager, parent=None):
        ToolContainerBase.__init__(self, toolmanager)
        QtWidgets.QToolBar.__init__(self, parent)
        self.setAllowedAreas(QtCore.Qt.ToolBarArea(
            _to_int(QtCore.Qt.ToolBarArea.TopToolBarArea) |
            _to_int(QtCore.Qt.ToolBarArea.BottomToolBarArea)))
        message_label = QtWidgets.QLabel("")
        message_label.setAlignment(QtCore.Qt.AlignmentFlag(
            _to_int(QtCore.Qt.AlignmentFlag.AlignRight) |
            _to_int(QtCore.Qt.AlignmentFlag.AlignVCenter)))
        message_label.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Ignored,
        ))
        self._message_action = self.addWidget(message_label)
        self._toolitems = {}
        self._groups = {}

    def add_toolitem(
            self, name, group, position, image_file, description, toggle):

        button = QtWidgets.QToolButton(self)
        if image_file:
            button.setIcon(NavigationToolbar2QT._icon(self, image_file))
        button.setText(name)
        if description:
            button.setToolTip(description)

        def handler():
            self.trigger_tool(name)
        if toggle:
            button.setCheckable(True)
            button.toggled.connect(handler)
        else:
            button.clicked.connect(handler)

        self._toolitems.setdefault(name, [])
        self._add_to_group(group, name, button, position)
        self._toolitems[name].append((button, handler))

    def _add_to_group(self, group, name, button, position):
        gr = self._groups.get(group, [])
        if not gr:
            sep = self.insertSeparator(self._message_action)
            gr.append(sep)
        before = gr[position]
        widget = self.insertWidget(before, button)
        gr.insert(position, widget)
        self._groups[group] = gr

    def toggle_toolitem(self, name, toggled):
        if name not in self._toolitems:
            return
        for button, handler in self._toolitems[name]:
            button.toggled.disconnect(handler)
            button.setChecked(toggled)
            button.toggled.connect(handler)

    def remove_toolitem(self, name):
        for button, handler in self._toolitems.pop(name, []):
            button.setParent(None)

    def set_message(self, s):
        self.widgetForAction(self._message_action).setText(s)


@backend_tools._register_tool_class(FigureCanvasQT)
class ConfigureSubplotsQt(backend_tools.ConfigureSubplotsBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._subplot_dialog = None

    def trigger(self, *args):
        NavigationToolbar2QT.configure_subplots(self)


@backend_tools._register_tool_class(FigureCanvasQT)
class SaveFigureQt(backend_tools.SaveFigureBase):
    def trigger(self, *args):
        NavigationToolbar2QT.save_figure(
            self._make_classic_style_pseudo_toolbar())


@backend_tools._register_tool_class(FigureCanvasQT)
class RubberbandQt(backend_tools.RubberbandBase):
    def draw_rubberband(self, x0, y0, x1, y1):
        NavigationToolbar2QT.draw_rubberband(
            self._make_classic_style_pseudo_toolbar(), None, x0, y0, x1, y1)

    def remove_rubberband(self):
        NavigationToolbar2QT.remove_rubberband(
            self._make_classic_style_pseudo_toolbar())


@backend_tools._register_tool_class(FigureCanvasQT)
class HelpQt(backend_tools.ToolHelpBase):
    def trigger(self, *args):
        QtWidgets.QMessageBox.information(None, "Help", self._get_help_html())


@backend_tools._register_tool_class(FigureCanvasQT)
class ToolCopyToClipboardQT(backend_tools.ToolCopyToClipboardBase):
    def trigger(self, *args, **kwargs):
        pixmap = self.canvas.grab()
        QtWidgets.QApplication.instance().clipboard().setPixmap(pixmap)


FigureManagerQT._toolbar2_class = NavigationToolbar2QT
FigureManagerQT._toolmanager_toolbar_class = ToolbarQt


@_Backend.export
class _BackendQT(_Backend):
    backend_version = __version__
    FigureCanvas = FigureCanvasQT
    FigureManager = FigureManagerQT
    mainloop = FigureManagerQT.start_main_loop

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\model_service\transports\rest.py ===
# -*- coding: utf-8 -*-
# Copyright 2024 Google LLC
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
#

import dataclasses
import json  # type: ignore
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union
import warnings

from google.api_core import (
    gapic_v1,
    operations_v1,
    path_template,
    rest_helpers,
    rest_streaming,
)
from google.api_core import exceptions as core_exceptions
from google.api_core import retry as retries
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.auth.transport.requests import AuthorizedSession  # type: ignore
from google.protobuf import json_format
import grpc  # type: ignore
from requests import __version__ as requests_version

try:
    OptionalRetry = Union[retries.Retry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.Retry, object, None]  # type: ignore


from google.longrunning import operations_pb2  # type: ignore
from google.protobuf import empty_pb2  # type: ignore

from google.ai.generativelanguage_v1beta.types import tuned_model as gag_tuned_model
from google.ai.generativelanguage_v1beta.types import model, model_service
from google.ai.generativelanguage_v1beta.types import tuned_model

from .base import DEFAULT_CLIENT_INFO as BASE_DEFAULT_CLIENT_INFO
from .base import ModelServiceTransport

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=BASE_DEFAULT_CLIENT_INFO.gapic_version,
    grpc_version=None,
    rest_version=requests_version,
)


class ModelServiceRestInterceptor:
    """Interceptor for ModelService.

    Interceptors are used to manipulate requests, request metadata, and responses
    in arbitrary ways.
    Example use cases include:
    * Logging
    * Verifying requests according to service or custom semantics
    * Stripping extraneous information from responses

    These use cases and more can be enabled by injecting an
    instance of a custom subclass when constructing the ModelServiceRestTransport.

    .. code-block:: python
        class MyCustomModelServiceInterceptor(ModelServiceRestInterceptor):
            def pre_create_tuned_model(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_create_tuned_model(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_delete_tuned_model(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def pre_get_model(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_get_model(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_get_tuned_model(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_get_tuned_model(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_list_models(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_list_models(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_list_tuned_models(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_list_tuned_models(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_update_tuned_model(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_update_tuned_model(self, response):
                logging.log(f"Received response: {response}")
                return response

        transport = ModelServiceRestTransport(interceptor=MyCustomModelServiceInterceptor())
        client = ModelServiceClient(transport=transport)


    """

    def pre_create_tuned_model(
        self,
        request: model_service.CreateTunedModelRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[model_service.CreateTunedModelRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for create_tuned_model

        Override in a subclass to manipulate the request or metadata
        before they are sent to the ModelService server.
        """
        return request, metadata

    def post_create_tuned_model(
        self, response: operations_pb2.Operation
    ) -> operations_pb2.Operation:
        """Post-rpc interceptor for create_tuned_model

        Override in a subclass to manipulate the response
        after it is returned by the ModelService server but before
        it is returned to user code.
        """
        return response

    def pre_delete_tuned_model(
        self,
        request: model_service.DeleteTunedModelRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[model_service.DeleteTunedModelRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for delete_tuned_model

        Override in a subclass to manipulate the request or metadata
        before they are sent to the ModelService server.
        """
        return request, metadata

    def pre_get_model(
        self,
        request: model_service.GetModelRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[model_service.GetModelRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for get_model

        Override in a subclass to manipulate the request or metadata
        before they are sent to the ModelService server.
        """
        return request, metadata

    def post_get_model(self, response: model.Model) -> model.Model:
        """Post-rpc interceptor for get_model

        Override in a subclass to manipulate the response
        after it is returned by the ModelService server but before
        it is returned to user code.
        """
        return response

    def pre_get_tuned_model(
        self,
        request: model_service.GetTunedModelRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[model_service.GetTunedModelRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for get_tuned_model

        Override in a subclass to manipulate the request or metadata
        before they are sent to the ModelService server.
        """
        return request, metadata

    def post_get_tuned_model(
        self, response: tuned_model.TunedModel
    ) -> tuned_model.TunedModel:
        """Post-rpc interceptor for get_tuned_model

        Override in a subclass to manipulate the response
        after it is returned by the ModelService server but before
        it is returned to user code.
        """
        return response

    def pre_list_models(
        self,
        request: model_service.ListModelsRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[model_service.ListModelsRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for list_models

        Override in a subclass to manipulate the request or metadata
        before they are sent to the ModelService server.
        """
        return request, metadata

    def post_list_models(
        self, response: model_service.ListModelsResponse
    ) -> model_service.ListModelsResponse:
        """Post-rpc interceptor for list_models

        Override in a subclass to manipulate the response
        after it is returned by the ModelService server but before
        it is returned to user code.
        """
        return response

    def pre_list_tuned_models(
        self,
        request: model_service.ListTunedModelsRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[model_service.ListTunedModelsRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for list_tuned_models

        Override in a subclass to manipulate the request or metadata
        before they are sent to the ModelService server.
        """
        return request, metadata

    def post_list_tuned_models(
        self, response: model_service.ListTunedModelsResponse
    ) -> model_service.ListTunedModelsResponse:
        """Post-rpc interceptor for list_tuned_models

        Override in a subclass to manipulate the response
        after it is returned by the ModelService server but before
        it is returned to user code.
        """
        return response

    def pre_update_tuned_model(
        self,
        request: model_service.UpdateTunedModelRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[model_service.UpdateTunedModelRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for update_tuned_model

        Override in a subclass to manipulate the request or metadata
        before they are sent to the ModelService server.
        """
        return request, metadata

    def post_update_tuned_model(
        self, response: gag_tuned_model.TunedModel
    ) -> gag_tuned_model.TunedModel:
        """Post-rpc interceptor for update_tuned_model

        Override in a subclass to manipulate the response
        after it is returned by the ModelService server but before
        it is returned to user code.
        """
        return response


@dataclasses.dataclass
class ModelServiceRestStub:
    _session: AuthorizedSession
    _host: str
    _interceptor: ModelServiceRestInterceptor


class ModelServiceRestTransport(ModelServiceTransport):
    """REST backend transport for ModelService.

    Provides methods for getting metadata information about
    Generative Models.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends JSON representations of protocol buffers over HTTP/1.1

    """

    def __init__(
        self,
        *,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        client_cert_source_for_mtls: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
        url_scheme: str = "https",
        interceptor: Optional[ModelServiceRestInterceptor] = None,
        api_audience: Optional[str] = None,
    ) -> None:
        """Instantiate the transport.

        Args:
            host (Optional[str]):
                 The hostname to connect to (default: 'generativelanguage.googleapis.com').
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.

            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is ignored if ``channel`` is provided.
            scopes (Optional(Sequence[str])): A list of scopes. This argument is
                ignored if ``channel`` is provided.
            client_cert_source_for_mtls (Callable[[], Tuple[bytes, bytes]]): Client
                certificate to configure mutual TLS HTTP channel. It is ignored
                if ``channel`` is provided.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you are developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.
            url_scheme: the protocol scheme for the API endpoint.  Normally
                "https", but for testing or local servers,
                "http" can be specified.
        """
        # Run the base constructor
        # TODO(yon-mg): resolve other ctor params i.e. scopes, quota, etc.
        # TODO: When custom host (api_endpoint) is set, `scopes` must *also* be set on the
        # credentials object
        maybe_url_match = re.match("^(?P<scheme>http(?:s)?://)?(?P<host>.*)$", host)
        if maybe_url_match is None:
            raise ValueError(
                f"Unexpected hostname structure: {host}"
            )  # pragma: NO COVER

        url_match_items = maybe_url_match.groupdict()

        host = f"{url_scheme}://{host}" if not url_match_items["scheme"] else host

        super().__init__(
            host=host,
            credentials=credentials,
            client_info=client_info,
            always_use_jwt_access=always_use_jwt_access,
            api_audience=api_audience,
        )
        self._session = AuthorizedSession(
            self._credentials, default_host=self.DEFAULT_HOST
        )
        self._operations_client: Optional[operations_v1.AbstractOperationsClient] = None
        if client_cert_source_for_mtls:
            self._session.configure_mtls_channel(client_cert_source_for_mtls)
        self._interceptor = interceptor or ModelServiceRestInterceptor()
        self._prep_wrapped_messages(client_info)

    @property
    def operations_client(self) -> operations_v1.AbstractOperationsClient:
        """Create the client designed to process long-running operations.

        This property caches on the instance; repeated calls return the same
        client.
        """
        # Only create a new client if we do not already have one.
        if self._operations_client is None:
            http_options: Dict[str, List[Dict[str, str]]] = {}

            rest_transport = operations_v1.OperationsRestTransport(
                host=self._host,
                # use the credentials which are saved
                credentials=self._credentials,
                scopes=self._scopes,
                http_options=http_options,
                path_prefix="v1beta",
            )

            self._operations_client = operations_v1.AbstractOperationsClient(
                transport=rest_transport
            )

        # Return the client from cache.
        return self._operations_client

    class _CreateTunedModel(ModelServiceRestStub):
        def __hash__(self):
            return hash("CreateTunedModel")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: model_service.CreateTunedModelRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> operations_pb2.Operation:
            r"""Call the create tuned model method over HTTP.

            Args:
                request (~.model_service.CreateTunedModelRequest):
                    The request object. Request to create a TunedModel.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.operations_pb2.Operation:
                    This resource represents a
                long-running operation that is the
                result of a network API call.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1beta/tunedModels",
                    "body": "tuned_model",
                },
            ]
            request, metadata = self._interceptor.pre_create_tuned_model(
                request, metadata
            )
            pb_request = model_service.CreateTunedModelRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request["body"], use_integers_for_enums=True
            )
            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = operations_pb2.Operation()
            json_format.Parse(response.content, resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_create_tuned_model(resp)
            return resp

    class _DeleteTunedModel(ModelServiceRestStub):
        def __hash__(self):
            return hash("DeleteTunedModel")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: model_service.DeleteTunedModelRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ):
            r"""Call the delete tuned model method over HTTP.

            Args:
                request (~.model_service.DeleteTunedModelRequest):
                    The request object. Request to delete a TunedModel.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.
            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "delete",
                    "uri": "/v1beta/{name=tunedModels/*}",
                },
            ]
            request, metadata = self._interceptor.pre_delete_tuned_model(
                request, metadata
            )
            pb_request = model_service.DeleteTunedModelRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

    class _GetModel(ModelServiceRestStub):
        def __hash__(self):
            return hash("GetModel")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: model_service.GetModelRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> model.Model:
            r"""Call the get model method over HTTP.

            Args:
                request (~.model_service.GetModelRequest):
                    The request object. Request for getting information about
                a specific Model.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.model.Model:
                    Information about a Generative
                Language Model.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "get",
                    "uri": "/v1beta/{name=models/*}",
                },
            ]
            request, metadata = self._interceptor.pre_get_model(request, metadata)
            pb_request = model_service.GetModelRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = model.Model()
            pb_resp = model.Model.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_get_model(resp)
            return resp

    class _GetTunedModel(ModelServiceRestStub):
        def __hash__(self):
            return hash("GetTunedModel")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: model_service.GetTunedModelRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> tuned_model.TunedModel:
            r"""Call the get tuned model method over HTTP.

            Args:
                request (~.model_service.GetTunedModelRequest):
                    The request object. Request for getting information about
                a specific Model.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.tuned_model.TunedModel:
                    A fine-tuned model created using
                ModelService.CreateTunedModel.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "get",
                    "uri": "/v1beta/{name=tunedModels/*}",
                },
            ]
            request, metadata = self._interceptor.pre_get_tuned_model(request, metadata)
            pb_request = model_service.GetTunedModelRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = tuned_model.TunedModel()
            pb_resp = tuned_model.TunedModel.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_get_tuned_model(resp)
            return resp

    class _ListModels(ModelServiceRestStub):
        def __hash__(self):
            return hash("ListModels")

        def __call__(
            self,
            request: model_service.ListModelsRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> model_service.ListModelsResponse:
            r"""Call the list models method over HTTP.

            Args:
                request (~.model_service.ListModelsRequest):
                    The request object. Request for listing all Models.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.model_service.ListModelsResponse:
                    Response from ``ListModel`` containing a paginated list
                of Models.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "get",
                    "uri": "/v1beta/models",
                },
            ]
            request, metadata = self._interceptor.pre_list_models(request, metadata)
            pb_request = model_service.ListModelsRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = model_service.ListModelsResponse()
            pb_resp = model_service.ListModelsResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_list_models(resp)
            return resp

    class _ListTunedModels(ModelServiceRestStub):
        def __hash__(self):
            return hash("ListTunedModels")

        def __call__(
            self,
            request: model_service.ListTunedModelsRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> model_service.ListTunedModelsResponse:
            r"""Call the list tuned models method over HTTP.

            Args:
                request (~.model_service.ListTunedModelsRequest):
                    The request object. Request for listing TunedModels.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.model_service.ListTunedModelsResponse:
                    Response from ``ListTunedModels`` containing a paginated
                list of Models.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "get",
                    "uri": "/v1beta/tunedModels",
                },
            ]
            request, metadata = self._interceptor.pre_list_tuned_models(
                request, metadata
            )
            pb_request = model_service.ListTunedModelsRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = model_service.ListTunedModelsResponse()
            pb_resp = model_service.ListTunedModelsResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_list_tuned_models(resp)
            return resp

    class _UpdateTunedModel(ModelServiceRestStub):
        def __hash__(self):
            return hash("UpdateTunedModel")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {
            "updateMask": {},
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: model_service.UpdateTunedModelRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> gag_tuned_model.TunedModel:
            r"""Call the update tuned model method over HTTP.

            Args:
                request (~.model_service.UpdateTunedModelRequest):
                    The request object. Request to update a TunedModel.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.gag_tuned_model.TunedModel:
                    A fine-tuned model created using
                ModelService.CreateTunedModel.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "patch",
                    "uri": "/v1beta/{tuned_model.name=tunedModels/*}",
                    "body": "tuned_model",
                },
            ]
            request, metadata = self._interceptor.pre_update_tuned_model(
                request, metadata
            )
            pb_request = model_service.UpdateTunedModelRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request["body"], use_integers_for_enums=True
            )
            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = gag_tuned_model.TunedModel()
            pb_resp = gag_tuned_model.TunedModel.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_update_tuned_model(resp)
            return resp

    @property
    def create_tuned_model(
        self,
    ) -> Callable[[model_service.CreateTunedModelRequest], operations_pb2.Operation]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._CreateTunedModel(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def delete_tuned_model(
        self,
    ) -> Callable[[model_service.DeleteTunedModelRequest], empty_pb2.Empty]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._DeleteTunedModel(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def get_model(self) -> Callable[[model_service.GetModelRequest], model.Model]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._GetModel(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def get_tuned_model(
        self,
    ) -> Callable[[model_service.GetTunedModelRequest], tuned_model.TunedModel]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._GetTunedModel(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def list_models(
        self,
    ) -> Callable[[model_service.ListModelsRequest], model_service.ListModelsResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._ListModels(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def list_tuned_models(
        self,
    ) -> Callable[
        [model_service.ListTunedModelsRequest], model_service.ListTunedModelsResponse
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._ListTunedModels(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def update_tuned_model(
        self,
    ) -> Callable[[model_service.UpdateTunedModelRequest], gag_tuned_model.TunedModel]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._UpdateTunedModel(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def kind(self) -> str:
        return "rest"

    def close(self):
        self._session.close()


__all__ = ("ModelServiceRestTransport",)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\services\model_service\transports\rest.py ===
# -*- coding: utf-8 -*-
# Copyright 2024 Google LLC
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
#

import dataclasses
import json  # type: ignore
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union
import warnings

from google.api_core import (
    gapic_v1,
    operations_v1,
    path_template,
    rest_helpers,
    rest_streaming,
)
from google.api_core import exceptions as core_exceptions
from google.api_core import retry as retries
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.auth.transport.requests import AuthorizedSession  # type: ignore
from google.protobuf import json_format
import grpc  # type: ignore
from requests import __version__ as requests_version

try:
    OptionalRetry = Union[retries.Retry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.Retry, object, None]  # type: ignore


from google.longrunning import operations_pb2  # type: ignore
from google.protobuf import empty_pb2  # type: ignore

from google.ai.generativelanguage_v1beta3.types import tuned_model as gag_tuned_model
from google.ai.generativelanguage_v1beta3.types import model, model_service
from google.ai.generativelanguage_v1beta3.types import tuned_model

from .base import DEFAULT_CLIENT_INFO as BASE_DEFAULT_CLIENT_INFO
from .base import ModelServiceTransport

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=BASE_DEFAULT_CLIENT_INFO.gapic_version,
    grpc_version=None,
    rest_version=requests_version,
)


class ModelServiceRestInterceptor:
    """Interceptor for ModelService.

    Interceptors are used to manipulate requests, request metadata, and responses
    in arbitrary ways.
    Example use cases include:
    * Logging
    * Verifying requests according to service or custom semantics
    * Stripping extraneous information from responses

    These use cases and more can be enabled by injecting an
    instance of a custom subclass when constructing the ModelServiceRestTransport.

    .. code-block:: python
        class MyCustomModelServiceInterceptor(ModelServiceRestInterceptor):
            def pre_create_tuned_model(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_create_tuned_model(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_delete_tuned_model(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def pre_get_model(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_get_model(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_get_tuned_model(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_get_tuned_model(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_list_models(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_list_models(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_list_tuned_models(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_list_tuned_models(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_update_tuned_model(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_update_tuned_model(self, response):
                logging.log(f"Received response: {response}")
                return response

        transport = ModelServiceRestTransport(interceptor=MyCustomModelServiceInterceptor())
        client = ModelServiceClient(transport=transport)


    """

    def pre_create_tuned_model(
        self,
        request: model_service.CreateTunedModelRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[model_service.CreateTunedModelRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for create_tuned_model

        Override in a subclass to manipulate the request or metadata
        before they are sent to the ModelService server.
        """
        return request, metadata

    def post_create_tuned_model(
        self, response: operations_pb2.Operation
    ) -> operations_pb2.Operation:
        """Post-rpc interceptor for create_tuned_model

        Override in a subclass to manipulate the response
        after it is returned by the ModelService server but before
        it is returned to user code.
        """
        return response

    def pre_delete_tuned_model(
        self,
        request: model_service.DeleteTunedModelRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[model_service.DeleteTunedModelRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for delete_tuned_model

        Override in a subclass to manipulate the request or metadata
        before they are sent to the ModelService server.
        """
        return request, metadata

    def pre_get_model(
        self,
        request: model_service.GetModelRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[model_service.GetModelRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for get_model

        Override in a subclass to manipulate the request or metadata
        before they are sent to the ModelService server.
        """
        return request, metadata

    def post_get_model(self, response: model.Model) -> model.Model:
        """Post-rpc interceptor for get_model

        Override in a subclass to manipulate the response
        after it is returned by the ModelService server but before
        it is returned to user code.
        """
        return response

    def pre_get_tuned_model(
        self,
        request: model_service.GetTunedModelRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[model_service.GetTunedModelRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for get_tuned_model

        Override in a subclass to manipulate the request or metadata
        before they are sent to the ModelService server.
        """
        return request, metadata

    def post_get_tuned_model(
        self, response: tuned_model.TunedModel
    ) -> tuned_model.TunedModel:
        """Post-rpc interceptor for get_tuned_model

        Override in a subclass to manipulate the response
        after it is returned by the ModelService server but before
        it is returned to user code.
        """
        return response

    def pre_list_models(
        self,
        request: model_service.ListModelsRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[model_service.ListModelsRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for list_models

        Override in a subclass to manipulate the request or metadata
        before they are sent to the ModelService server.
        """
        return request, metadata

    def post_list_models(
        self, response: model_service.ListModelsResponse
    ) -> model_service.ListModelsResponse:
        """Post-rpc interceptor for list_models

        Override in a subclass to manipulate the response
        after it is returned by the ModelService server but before
        it is returned to user code.
        """
        return response

    def pre_list_tuned_models(
        self,
        request: model_service.ListTunedModelsRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[model_service.ListTunedModelsRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for list_tuned_models

        Override in a subclass to manipulate the request or metadata
        before they are sent to the ModelService server.
        """
        return request, metadata

    def post_list_tuned_models(
        self, response: model_service.ListTunedModelsResponse
    ) -> model_service.ListTunedModelsResponse:
        """Post-rpc interceptor for list_tuned_models

        Override in a subclass to manipulate the response
        after it is returned by the ModelService server but before
        it is returned to user code.
        """
        return response

    def pre_update_tuned_model(
        self,
        request: model_service.UpdateTunedModelRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[model_service.UpdateTunedModelRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for update_tuned_model

        Override in a subclass to manipulate the request or metadata
        before they are sent to the ModelService server.
        """
        return request, metadata

    def post_update_tuned_model(
        self, response: gag_tuned_model.TunedModel
    ) -> gag_tuned_model.TunedModel:
        """Post-rpc interceptor for update_tuned_model

        Override in a subclass to manipulate the response
        after it is returned by the ModelService server but before
        it is returned to user code.
        """
        return response


@dataclasses.dataclass
class ModelServiceRestStub:
    _session: AuthorizedSession
    _host: str
    _interceptor: ModelServiceRestInterceptor


class ModelServiceRestTransport(ModelServiceTransport):
    """REST backend transport for ModelService.

    Provides methods for getting metadata information about
    Generative Models.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends JSON representations of protocol buffers over HTTP/1.1

    """

    def __init__(
        self,
        *,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        client_cert_source_for_mtls: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
        url_scheme: str = "https",
        interceptor: Optional[ModelServiceRestInterceptor] = None,
        api_audience: Optional[str] = None,
    ) -> None:
        """Instantiate the transport.

        Args:
            host (Optional[str]):
                 The hostname to connect to (default: 'generativelanguage.googleapis.com').
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.

            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is ignored if ``channel`` is provided.
            scopes (Optional(Sequence[str])): A list of scopes. This argument is
                ignored if ``channel`` is provided.
            client_cert_source_for_mtls (Callable[[], Tuple[bytes, bytes]]): Client
                certificate to configure mutual TLS HTTP channel. It is ignored
                if ``channel`` is provided.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you are developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.
            url_scheme: the protocol scheme for the API endpoint.  Normally
                "https", but for testing or local servers,
                "http" can be specified.
        """
        # Run the base constructor
        # TODO(yon-mg): resolve other ctor params i.e. scopes, quota, etc.
        # TODO: When custom host (api_endpoint) is set, `scopes` must *also* be set on the
        # credentials object
        maybe_url_match = re.match("^(?P<scheme>http(?:s)?://)?(?P<host>.*)$", host)
        if maybe_url_match is None:
            raise ValueError(
                f"Unexpected hostname structure: {host}"
            )  # pragma: NO COVER

        url_match_items = maybe_url_match.groupdict()

        host = f"{url_scheme}://{host}" if not url_match_items["scheme"] else host

        super().__init__(
            host=host,
            credentials=credentials,
            client_info=client_info,
            always_use_jwt_access=always_use_jwt_access,
            api_audience=api_audience,
        )
        self._session = AuthorizedSession(
            self._credentials, default_host=self.DEFAULT_HOST
        )
        self._operations_client: Optional[operations_v1.AbstractOperationsClient] = None
        if client_cert_source_for_mtls:
            self._session.configure_mtls_channel(client_cert_source_for_mtls)
        self._interceptor = interceptor or ModelServiceRestInterceptor()
        self._prep_wrapped_messages(client_info)

    @property
    def operations_client(self) -> operations_v1.AbstractOperationsClient:
        """Create the client designed to process long-running operations.

        This property caches on the instance; repeated calls return the same
        client.
        """
        # Only create a new client if we do not already have one.
        if self._operations_client is None:
            http_options: Dict[str, List[Dict[str, str]]] = {}

            rest_transport = operations_v1.OperationsRestTransport(
                host=self._host,
                # use the credentials which are saved
                credentials=self._credentials,
                scopes=self._scopes,
                http_options=http_options,
                path_prefix="v1beta3",
            )

            self._operations_client = operations_v1.AbstractOperationsClient(
                transport=rest_transport
            )

        # Return the client from cache.
        return self._operations_client

    class _CreateTunedModel(ModelServiceRestStub):
        def __hash__(self):
            return hash("CreateTunedModel")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: model_service.CreateTunedModelRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> operations_pb2.Operation:
            r"""Call the create tuned model method over HTTP.

            Args:
                request (~.model_service.CreateTunedModelRequest):
                    The request object. Request to create a TunedModel.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.operations_pb2.Operation:
                    This resource represents a
                long-running operation that is the
                result of a network API call.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1beta3/tunedModels",
                    "body": "tuned_model",
                },
            ]
            request, metadata = self._interceptor.pre_create_tuned_model(
                request, metadata
            )
            pb_request = model_service.CreateTunedModelRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request["body"], use_integers_for_enums=True
            )
            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = operations_pb2.Operation()
            json_format.Parse(response.content, resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_create_tuned_model(resp)
            return resp

    class _DeleteTunedModel(ModelServiceRestStub):
        def __hash__(self):
            return hash("DeleteTunedModel")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: model_service.DeleteTunedModelRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ):
            r"""Call the delete tuned model method over HTTP.

            Args:
                request (~.model_service.DeleteTunedModelRequest):
                    The request object. Request to delete a TunedModel.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.
            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "delete",
                    "uri": "/v1beta3/{name=tunedModels/*}",
                },
            ]
            request, metadata = self._interceptor.pre_delete_tuned_model(
                request, metadata
            )
            pb_request = model_service.DeleteTunedModelRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

    class _GetModel(ModelServiceRestStub):
        def __hash__(self):
            return hash("GetModel")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: model_service.GetModelRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> model.Model:
            r"""Call the get model method over HTTP.

            Args:
                request (~.model_service.GetModelRequest):
                    The request object. Request for getting information about
                a specific Model.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.model.Model:
                    Information about a Generative
                Language Model.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "get",
                    "uri": "/v1beta3/{name=models/*}",
                },
            ]
            request, metadata = self._interceptor.pre_get_model(request, metadata)
            pb_request = model_service.GetModelRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = model.Model()
            pb_resp = model.Model.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_get_model(resp)
            return resp

    class _GetTunedModel(ModelServiceRestStub):
        def __hash__(self):
            return hash("GetTunedModel")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: model_service.GetTunedModelRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> tuned_model.TunedModel:
            r"""Call the get tuned model method over HTTP.

            Args:
                request (~.model_service.GetTunedModelRequest):
                    The request object. Request for getting information about
                a specific Model.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.tuned_model.TunedModel:
                    A fine-tuned model created using
                ModelService.CreateTunedModel.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "get",
                    "uri": "/v1beta3/{name=tunedModels/*}",
                },
            ]
            request, metadata = self._interceptor.pre_get_tuned_model(request, metadata)
            pb_request = model_service.GetTunedModelRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = tuned_model.TunedModel()
            pb_resp = tuned_model.TunedModel.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_get_tuned_model(resp)
            return resp

    class _ListModels(ModelServiceRestStub):
        def __hash__(self):
            return hash("ListModels")

        def __call__(
            self,
            request: model_service.ListModelsRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> model_service.ListModelsResponse:
            r"""Call the list models method over HTTP.

            Args:
                request (~.model_service.ListModelsRequest):
                    The request object. Request for listing all Models.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.model_service.ListModelsResponse:
                    Response from ``ListModel`` containing a paginated list
                of Models.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "get",
                    "uri": "/v1beta3/models",
                },
            ]
            request, metadata = self._interceptor.pre_list_models(request, metadata)
            pb_request = model_service.ListModelsRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = model_service.ListModelsResponse()
            pb_resp = model_service.ListModelsResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_list_models(resp)
            return resp

    class _ListTunedModels(ModelServiceRestStub):
        def __hash__(self):
            return hash("ListTunedModels")

        def __call__(
            self,
            request: model_service.ListTunedModelsRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> model_service.ListTunedModelsResponse:
            r"""Call the list tuned models method over HTTP.

            Args:
                request (~.model_service.ListTunedModelsRequest):
                    The request object. Request for listing TunedModels.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.model_service.ListTunedModelsResponse:
                    Response from ``ListTunedModels`` containing a paginated
                list of Models.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "get",
                    "uri": "/v1beta3/tunedModels",
                },
            ]
            request, metadata = self._interceptor.pre_list_tuned_models(
                request, metadata
            )
            pb_request = model_service.ListTunedModelsRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = model_service.ListTunedModelsResponse()
            pb_resp = model_service.ListTunedModelsResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_list_tuned_models(resp)
            return resp

    class _UpdateTunedModel(ModelServiceRestStub):
        def __hash__(self):
            return hash("UpdateTunedModel")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {
            "updateMask": {},
        }

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: model_service.UpdateTunedModelRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> gag_tuned_model.TunedModel:
            r"""Call the update tuned model method over HTTP.

            Args:
                request (~.model_service.UpdateTunedModelRequest):
                    The request object. Request to update a TunedModel.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.gag_tuned_model.TunedModel:
                    A fine-tuned model created using
                ModelService.CreateTunedModel.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "patch",
                    "uri": "/v1beta3/{tuned_model.name=tunedModels/*}",
                    "body": "tuned_model",
                },
            ]
            request, metadata = self._interceptor.pre_update_tuned_model(
                request, metadata
            )
            pb_request = model_service.UpdateTunedModelRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request["body"], use_integers_for_enums=True
            )
            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = gag_tuned_model.TunedModel()
            pb_resp = gag_tuned_model.TunedModel.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_update_tuned_model(resp)
            return resp

    @property
    def create_tuned_model(
        self,
    ) -> Callable[[model_service.CreateTunedModelRequest], operations_pb2.Operation]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._CreateTunedModel(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def delete_tuned_model(
        self,
    ) -> Callable[[model_service.DeleteTunedModelRequest], empty_pb2.Empty]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._DeleteTunedModel(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def get_model(self) -> Callable[[model_service.GetModelRequest], model.Model]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._GetModel(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def get_tuned_model(
        self,
    ) -> Callable[[model_service.GetTunedModelRequest], tuned_model.TunedModel]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._GetTunedModel(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def list_models(
        self,
    ) -> Callable[[model_service.ListModelsRequest], model_service.ListModelsResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._ListModels(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def list_tuned_models(
        self,
    ) -> Callable[
        [model_service.ListTunedModelsRequest], model_service.ListTunedModelsResponse
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._ListTunedModels(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def update_tuned_model(
        self,
    ) -> Callable[[model_service.UpdateTunedModelRequest], gag_tuned_model.TunedModel]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._UpdateTunedModel(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def kind(self) -> str:
        return "rest"

    def close(self):
        self._session.close()


__all__ = ("ModelServiceRestTransport",)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\anthropic\chat\transformation.py ===
import json
import re
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union, cast

import httpx

import litellm
from litellm.constants import (
    ANTHROPIC_WEB_SEARCH_TOOL_MAX_USES,
    DEFAULT_ANTHROPIC_CHAT_MAX_TOKENS,
    DEFAULT_REASONING_EFFORT_HIGH_THINKING_BUDGET,
    DEFAULT_REASONING_EFFORT_LOW_THINKING_BUDGET,
    DEFAULT_REASONING_EFFORT_MEDIUM_THINKING_BUDGET,
    RESPONSE_FORMAT_TOOL_NAME,
)
from litellm.litellm_core_utils.core_helpers import map_finish_reason
from litellm.llms.base_llm.base_utils import type_to_response_format_param
from litellm.llms.base_llm.chat.transformation import BaseConfig, BaseLLMException
from litellm.types.llms.anthropic import (
    AllAnthropicMessageValues,
    AllAnthropicToolsValues,
    AnthropicCodeExecutionTool,
    AnthropicComputerTool,
    AnthropicHostedTools,
    AnthropicInputSchema,
    AnthropicMcpServerTool,
    AnthropicMessagesTool,
    AnthropicMessagesToolChoice,
    AnthropicSystemMessageContent,
    AnthropicThinkingParam,
    AnthropicWebSearchTool,
    AnthropicWebSearchUserLocation,
)
from litellm.types.llms.openai import (
    REASONING_EFFORT,
    AllMessageValues,
    ChatCompletionCachedContent,
    ChatCompletionRedactedThinkingBlock,
    ChatCompletionSystemMessage,
    ChatCompletionThinkingBlock,
    ChatCompletionToolCallChunk,
    ChatCompletionToolCallFunctionChunk,
    ChatCompletionToolParam,
    OpenAIMcpServerTool,
    OpenAIWebSearchOptions,
)
from litellm.types.utils import CompletionTokensDetailsWrapper
from litellm.types.utils import Message as LitellmMessage
from litellm.types.utils import PromptTokensDetailsWrapper, ServerToolUse
from litellm.utils import (
    ModelResponse,
    Usage,
    add_dummy_tool,
    has_tool_call_blocks,
    supports_reasoning,
    token_counter,
)

from ..common_utils import AnthropicError, AnthropicModelInfo, process_anthropic_headers

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj

    LoggingClass = LiteLLMLoggingObj
else:
    LoggingClass = Any


ANTHROPIC_HOSTED_TOOLS = ["web_search", "bash", "text_editor", "code_execution"]


class AnthropicConfig(AnthropicModelInfo, BaseConfig):
    """
    Reference: https://docs.anthropic.com/claude/reference/messages_post

    to pass metadata to anthropic, it's {"user_id": "any-relevant-information"}
    """

    max_tokens: Optional[int] = (
        DEFAULT_ANTHROPIC_CHAT_MAX_TOKENS  # anthropic requires a default value (Opus, Sonnet, and Haiku have the same default)
    )
    stop_sequences: Optional[list] = None
    temperature: Optional[int] = None
    top_p: Optional[int] = None
    top_k: Optional[int] = None
    metadata: Optional[dict] = None
    system: Optional[str] = None

    def __init__(
        self,
        max_tokens: Optional[
            int
        ] = DEFAULT_ANTHROPIC_CHAT_MAX_TOKENS,  # You can pass in a value yourself or use the default value 4096
        stop_sequences: Optional[list] = None,
        temperature: Optional[int] = None,
        top_p: Optional[int] = None,
        top_k: Optional[int] = None,
        metadata: Optional[dict] = None,
        system: Optional[str] = None,
    ) -> None:
        locals_ = locals().copy()
        for key, value in locals_.items():
            if key != "self" and value is not None:
                setattr(self.__class__, key, value)

    @property
    def custom_llm_provider(self) -> Optional[str]:
        return "anthropic"

    @classmethod
    def get_config(cls):
        return super().get_config()

    def get_supported_openai_params(self, model: str):

        params = [
            "stream",
            "stop",
            "temperature",
            "top_p",
            "max_tokens",
            "max_completion_tokens",
            "tools",
            "tool_choice",
            "extra_headers",
            "parallel_tool_calls",
            "response_format",
            "user",
            "reasoning_effort",
            "web_search_options",
        ]

        if "claude-3-7-sonnet" in model or supports_reasoning(
            model=model,
            custom_llm_provider=self.custom_llm_provider,
        ):
            params.append("thinking")

        return params

    def get_json_schema_from_pydantic_object(
        self, response_format: Union[Any, Dict, None]
    ) -> Optional[dict]:
        return type_to_response_format_param(
            response_format, ref_template="/$defs/{model}"
        )  # Relevant issue: https://github.com/BerriAI/litellm/issues/7755

    def get_cache_control_headers(self) -> dict:
        return {
            "anthropic-version": "2023-06-01",
            "anthropic-beta": "prompt-caching-2024-07-31",
        }

    def _map_tool_choice(
        self, tool_choice: Optional[str], parallel_tool_use: Optional[bool]
    ) -> Optional[AnthropicMessagesToolChoice]:
        _tool_choice: Optional[AnthropicMessagesToolChoice] = None
        if tool_choice == "auto":
            _tool_choice = AnthropicMessagesToolChoice(
                type="auto",
            )
        elif tool_choice == "required":
            _tool_choice = AnthropicMessagesToolChoice(type="any")
        elif tool_choice == "none":
            _tool_choice = AnthropicMessagesToolChoice(type="none")
        elif isinstance(tool_choice, dict):
            _tool_name = tool_choice.get("function", {}).get("name")
            _tool_choice = AnthropicMessagesToolChoice(type="tool")
            if _tool_name is not None:
                _tool_choice["name"] = _tool_name

        if parallel_tool_use is not None:
            # Anthropic uses 'disable_parallel_tool_use' flag to determine if parallel tool use is allowed
            # this is the inverse of the openai flag.
            if tool_choice == "none":
                pass
            elif _tool_choice is not None:
                _tool_choice["disable_parallel_tool_use"] = not parallel_tool_use
            else:  # use anthropic defaults and make sure to send the disable_parallel_tool_use flag
                _tool_choice = AnthropicMessagesToolChoice(
                    type="auto",
                    disable_parallel_tool_use=not parallel_tool_use,
                )
        return _tool_choice

    def _map_tool_helper(
        self, tool: ChatCompletionToolParam
    ) -> Tuple[Optional[AllAnthropicToolsValues], Optional[AnthropicMcpServerTool]]:
        returned_tool: Optional[AllAnthropicToolsValues] = None
        mcp_server: Optional[AnthropicMcpServerTool] = None

        if tool["type"] == "function" or tool["type"] == "custom":
            _input_schema: dict = tool["function"].get(
                "parameters",
                {
                    "type": "object",
                    "properties": {},
                },
            )
            input_schema: AnthropicInputSchema = AnthropicInputSchema(**_input_schema)
            _tool = AnthropicMessagesTool(
                name=tool["function"]["name"],
                input_schema=input_schema,
            )

            _description = tool["function"].get("description")
            if _description is not None:
                _tool["description"] = _description

            returned_tool = _tool

        elif tool["type"].startswith("computer_"):
            ## check if all required 'display_' params are given
            if "parameters" not in tool["function"]:
                raise ValueError("Missing required parameter: parameters")

            _display_width_px: Optional[int] = tool["function"]["parameters"].get(
                "display_width_px"
            )
            _display_height_px: Optional[int] = tool["function"]["parameters"].get(
                "display_height_px"
            )
            if _display_width_px is None or _display_height_px is None:
                raise ValueError(
                    "Missing required parameter: display_width_px or display_height_px"
                )

            _computer_tool = AnthropicComputerTool(
                type=tool["type"],
                name=tool["function"].get("name", "computer"),
                display_width_px=_display_width_px,
                display_height_px=_display_height_px,
            )

            _display_number = tool["function"]["parameters"].get("display_number")
            if _display_number is not None:
                _computer_tool["display_number"] = _display_number

            returned_tool = _computer_tool
        elif any(tool["type"].startswith(t) for t in ANTHROPIC_HOSTED_TOOLS):
            function_name = tool.get("name", tool.get("function", {}).get("name"))
            if function_name is None or not isinstance(function_name, str):
                raise ValueError("Missing required parameter: name")

            additional_tool_params = {}
            for k, v in tool.items():
                if k != "type" and k != "name":
                    additional_tool_params[k] = v

            returned_tool = AnthropicHostedTools(
                type=tool["type"], name=function_name, **additional_tool_params  # type: ignore
            )
        elif tool["type"] == "url":  # mcp server tool
            mcp_server = AnthropicMcpServerTool(**tool)  # type: ignore
        elif tool["type"] == "mcp":
            mcp_server = self._map_openai_mcp_server_tool(
                cast(OpenAIMcpServerTool, tool)
            )
        if returned_tool is None and mcp_server is None:
            raise ValueError(f"Unsupported tool type: {tool['type']}")

        ## check if cache_control is set in the tool
        _cache_control = tool.get("cache_control", None)
        _cache_control_function = tool.get("function", {}).get("cache_control", None)
        if returned_tool is not None:
            if _cache_control is not None:
                returned_tool["cache_control"] = _cache_control
            elif _cache_control_function is not None and isinstance(
                _cache_control_function, dict
            ):
                returned_tool["cache_control"] = ChatCompletionCachedContent(
                    **_cache_control_function  # type: ignore
                )

        return returned_tool, mcp_server

    def _map_openai_mcp_server_tool(
        self, tool: OpenAIMcpServerTool
    ) -> AnthropicMcpServerTool:
        from litellm.types.llms.anthropic import AnthropicMcpServerToolConfiguration

        allowed_tools = tool.get("allowed_tools", None)
        tool_configuration: Optional[AnthropicMcpServerToolConfiguration] = None
        if allowed_tools is not None:
            tool_configuration = AnthropicMcpServerToolConfiguration(
                allowed_tools=tool.get("allowed_tools", None),
            )

        headers = tool.get("headers", {})
        authorization_token: Optional[str] = None
        if headers is not None:
            bearer_token = headers.get("Authorization", None)
            if bearer_token is not None:
                authorization_token = bearer_token.replace("Bearer ", "")

        initial_tool = AnthropicMcpServerTool(
            type="url",
            url=tool["server_url"],
            name=tool["server_label"],
        )

        if tool_configuration is not None:
            initial_tool["tool_configuration"] = tool_configuration
        if authorization_token is not None:
            initial_tool["authorization_token"] = authorization_token
        return initial_tool

    def _map_tools(
        self, tools: List
    ) -> Tuple[List[AllAnthropicToolsValues], List[AnthropicMcpServerTool]]:
        anthropic_tools = []
        mcp_servers = []
        for tool in tools:
            if "input_schema" in tool:  # assume in anthropic format
                anthropic_tools.append(tool)
            else:  # assume openai tool call
                new_tool, mcp_server_tool = self._map_tool_helper(tool)

                if new_tool is not None:
                    anthropic_tools.append(new_tool)
                if mcp_server_tool is not None:
                    mcp_servers.append(mcp_server_tool)
        return anthropic_tools, mcp_servers

    def _map_stop_sequences(
        self, stop: Optional[Union[str, List[str]]]
    ) -> Optional[List[str]]:
        new_stop: Optional[List[str]] = None
        if isinstance(stop, str):
            if (
                stop.isspace() and litellm.drop_params is True
            ):  # anthropic doesn't allow whitespace characters as stop-sequences
                return new_stop
            new_stop = [stop]
        elif isinstance(stop, list):
            new_v = []
            for v in stop:
                if (
                    v.isspace() and litellm.drop_params is True
                ):  # anthropic doesn't allow whitespace characters as stop-sequences
                    continue
                new_v.append(v)
            if len(new_v) > 0:
                new_stop = new_v
        return new_stop

    @staticmethod
    def _map_reasoning_effort(
        reasoning_effort: Optional[Union[REASONING_EFFORT, str]],
    ) -> Optional[AnthropicThinkingParam]:
        if reasoning_effort is None:
            return None
        elif reasoning_effort == "low":
            return AnthropicThinkingParam(
                type="enabled",
                budget_tokens=DEFAULT_REASONING_EFFORT_LOW_THINKING_BUDGET,
            )
        elif reasoning_effort == "medium":
            return AnthropicThinkingParam(
                type="enabled",
                budget_tokens=DEFAULT_REASONING_EFFORT_MEDIUM_THINKING_BUDGET,
            )
        elif reasoning_effort == "high":
            return AnthropicThinkingParam(
                type="enabled",
                budget_tokens=DEFAULT_REASONING_EFFORT_HIGH_THINKING_BUDGET,
            )
        else:
            raise ValueError(f"Unmapped reasoning effort: {reasoning_effort}")

    def map_response_format_to_anthropic_tool(
        self, value: Optional[dict], optional_params: dict, is_thinking_enabled: bool
    ) -> Optional[AnthropicMessagesTool]:
        ignore_response_format_types = ["text"]
        if (
            value is None or value["type"] in ignore_response_format_types
        ):  # value is a no-op
            return None

        json_schema: Optional[dict] = None
        if "response_schema" in value:
            json_schema = value["response_schema"]
        elif "json_schema" in value:
            json_schema = value["json_schema"]["schema"]
        """
        When using tools in this way: - https://docs.anthropic.com/en/docs/build-with-claude/tool-use#json-mode
        - You usually want to provide a single tool
        - You should set tool_choice (see Forcing tool use) to instruct the model to explicitly use that tool
        - Remember that the model will pass the input to the tool, so the name of the tool and description should be from the model’s perspective.
        """

        _tool = self._create_json_tool_call_for_response_format(
            json_schema=json_schema,
        )

        return _tool

    def map_web_search_tool(
        self,
        value: OpenAIWebSearchOptions,
    ) -> AnthropicWebSearchTool:
        value_typed = cast(OpenAIWebSearchOptions, value)
        hosted_web_search_tool = AnthropicWebSearchTool(
            type="web_search_20250305",
            name="web_search",
        )
        user_location = value_typed.get("user_location")
        if user_location is not None:
            anthropic_user_location = AnthropicWebSearchUserLocation(type="approximate")
            anthropic_user_location_keys = (
                AnthropicWebSearchUserLocation.__annotations__.keys()
            )
            user_location_approximate = user_location.get("approximate")
            if user_location_approximate is not None:
                for key, user_location_value in user_location_approximate.items():
                    if key in anthropic_user_location_keys and key != "type":
                        anthropic_user_location[key] = user_location_value  # type: ignore
                hosted_web_search_tool["user_location"] = anthropic_user_location

        ## MAP SEARCH CONTEXT SIZE
        search_context_size = value_typed.get("search_context_size")
        if search_context_size is not None:
            hosted_web_search_tool["max_uses"] = ANTHROPIC_WEB_SEARCH_TOOL_MAX_USES[
                search_context_size
            ]

        return hosted_web_search_tool

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ) -> dict:
        is_thinking_enabled = self.is_thinking_enabled(
            non_default_params=non_default_params
        )

        for param, value in non_default_params.items():
            if param == "max_tokens":
                optional_params["max_tokens"] = value
            if param == "max_completion_tokens":
                optional_params["max_tokens"] = value
            if param == "tools":
                # check if optional params already has tools
                anthropic_tools, mcp_servers = self._map_tools(value)
                optional_params = self._add_tools_to_optional_params(
                    optional_params=optional_params, tools=anthropic_tools
                )
                if mcp_servers:
                    optional_params["mcp_servers"] = mcp_servers
            if param == "tool_choice" or param == "parallel_tool_calls":
                _tool_choice: Optional[AnthropicMessagesToolChoice] = (
                    self._map_tool_choice(
                        tool_choice=non_default_params.get("tool_choice"),
                        parallel_tool_use=non_default_params.get("parallel_tool_calls"),
                    )
                )

                if _tool_choice is not None:
                    optional_params["tool_choice"] = _tool_choice
            if param == "stream" and value is True:
                optional_params["stream"] = value
            if param == "stop" and (isinstance(value, str) or isinstance(value, list)):
                _value = self._map_stop_sequences(value)
                if _value is not None:
                    optional_params["stop_sequences"] = _value
            if param == "temperature":
                optional_params["temperature"] = value
            if param == "top_p":
                optional_params["top_p"] = value
            if param == "response_format" and isinstance(value, dict):
                _tool = self.map_response_format_to_anthropic_tool(
                    value, optional_params, is_thinking_enabled
                )
                if _tool is None:
                    continue
                if not is_thinking_enabled:
                    _tool_choice = {"name": RESPONSE_FORMAT_TOOL_NAME, "type": "tool"}
                    optional_params["tool_choice"] = _tool_choice
                optional_params["json_mode"] = True
                optional_params = self._add_tools_to_optional_params(
                    optional_params=optional_params, tools=[_tool]
                )
            if (
                param == "user"
                and value is not None
                and isinstance(value, str)
                and _valid_user_id(value)  # anthropic fails on emails
            ):
                optional_params["metadata"] = {"user_id": value}
            if param == "thinking":
                optional_params["thinking"] = value
            elif param == "reasoning_effort" and isinstance(value, str):
                optional_params["thinking"] = AnthropicConfig._map_reasoning_effort(
                    value
                )
            elif param == "web_search_options" and isinstance(value, dict):
                hosted_web_search_tool = self.map_web_search_tool(
                    cast(OpenAIWebSearchOptions, value)
                )
                self._add_tools_to_optional_params(
                    optional_params=optional_params, tools=[hosted_web_search_tool]
                )

        ## handle thinking tokens
        self.update_optional_params_with_thinking_tokens(
            non_default_params=non_default_params, optional_params=optional_params
        )

        return optional_params

    def _create_json_tool_call_for_response_format(
        self,
        json_schema: Optional[dict] = None,
    ) -> AnthropicMessagesTool:
        """
        Handles creating a tool call for getting responses in JSON format.

        Args:
            json_schema (Optional[dict]): The JSON schema the response should be in

        Returns:
            AnthropicMessagesTool: The tool call to send to Anthropic API to get responses in JSON format
        """
        _input_schema: AnthropicInputSchema = AnthropicInputSchema(
            type="object",
        )

        if json_schema is None:
            # Anthropic raises a 400 BadRequest error if properties is passed as None
            # see usage with additionalProperties (Example 5) https://github.com/anthropics/anthropic-cookbook/blob/main/tool_use/extracting_structured_json.ipynb
            _input_schema["additionalProperties"] = True
            _input_schema["properties"] = {}
        else:
            _input_schema.update(cast(AnthropicInputSchema, json_schema))

        _tool = AnthropicMessagesTool(
            name=RESPONSE_FORMAT_TOOL_NAME, input_schema=_input_schema
        )
        return _tool

    def translate_system_message(
        self, messages: List[AllMessageValues]
    ) -> List[AnthropicSystemMessageContent]:
        """
        Translate system message to anthropic format.

        Removes system message from the original list and returns a new list of anthropic system message content.
        """
        system_prompt_indices = []
        anthropic_system_message_list: List[AnthropicSystemMessageContent] = []
        for idx, message in enumerate(messages):
            if message["role"] == "system":
                valid_content: bool = False
                system_message_block = ChatCompletionSystemMessage(**message)
                if isinstance(system_message_block["content"], str):
                    anthropic_system_message_content = AnthropicSystemMessageContent(
                        type="text",
                        text=system_message_block["content"],
                    )
                    if "cache_control" in system_message_block:
                        anthropic_system_message_content["cache_control"] = (
                            system_message_block["cache_control"]
                        )
                    anthropic_system_message_list.append(
                        anthropic_system_message_content
                    )
                    valid_content = True
                elif isinstance(message["content"], list):
                    for _content in message["content"]:
                        anthropic_system_message_content = (
                            AnthropicSystemMessageContent(
                                type=_content.get("type"),
                                text=_content.get("text"),
                            )
                        )
                        if "cache_control" in _content:
                            anthropic_system_message_content["cache_control"] = (
                                _content["cache_control"]
                            )

                        anthropic_system_message_list.append(
                            anthropic_system_message_content
                        )
                    valid_content = True

                if valid_content:
                    system_prompt_indices.append(idx)
        if len(system_prompt_indices) > 0:
            for idx in reversed(system_prompt_indices):
                messages.pop(idx)

        return anthropic_system_message_list

    def add_code_execution_tool(
        self,
        messages: List[AllAnthropicMessageValues],
        tools: List[Union[AllAnthropicToolsValues, Dict]],
    ) -> List[Union[AllAnthropicToolsValues, Dict]]:
        """if 'container_upload' in messages, add code_execution tool"""
        add_code_execution_tool = False
        for message in messages:
            message_content = message.get("content", None)
            if message_content and isinstance(message_content, list):
                for content in message_content:
                    content_type = content.get("type", None)
                    if content_type == "container_upload":
                        add_code_execution_tool = True
                        break

        if add_code_execution_tool:
            ## check if code_execution tool is already in tools
            for tool in tools:
                tool_type = tool.get("type", None)
                if (
                    tool_type
                    and isinstance(tool_type, str)
                    and tool_type.startswith("code_execution")
                ):
                    return tools
            tools.append(
                AnthropicCodeExecutionTool(
                    name="code_execution",
                    type="code_execution_20250522",
                )
            )
        return tools

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        """
        Translate messages to anthropic format.
        """
        ## VALIDATE REQUEST
        """
        Anthropic doesn't support tool calling without `tools=` param specified.
        """
        from litellm.litellm_core_utils.prompt_templates.factory import (
            anthropic_messages_pt,
        )

        if (
            "tools" not in optional_params
            and messages is not None
            and has_tool_call_blocks(messages)
        ):
            if litellm.modify_params:
                optional_params["tools"], _ = self._map_tools(
                    add_dummy_tool(custom_llm_provider="anthropic")
                )
            else:
                raise litellm.UnsupportedParamsError(
                    message="Anthropic doesn't support tool calling without `tools=` param specified. Pass `tools=` param OR set `litellm.modify_params = True` // `litellm_settings::modify_params: True` to add dummy tool to the request.",
                    model="",
                    llm_provider="anthropic",
                )

        # Separate system prompt from rest of message
        anthropic_system_message_list = self.translate_system_message(messages=messages)
        # Handling anthropic API Prompt Caching
        if len(anthropic_system_message_list) > 0:
            optional_params["system"] = anthropic_system_message_list
        # Format rest of message according to anthropic guidelines
        try:
            anthropic_messages = anthropic_messages_pt(
                model=model,
                messages=messages,
                llm_provider="anthropic",
            )
        except Exception as e:
            raise AnthropicError(
                status_code=400,
                message="{}\nReceived Messages={}".format(str(e), messages),
            )  # don't use verbose_logger.exception, if exception is raised

        ## Add code_execution tool if container_upload is in messages
        _tools = (
            cast(
                Optional[List[Union[AllAnthropicToolsValues, Dict]]],
                optional_params.get("tools"),
            )
            or []
        )
        tools = self.add_code_execution_tool(messages=anthropic_messages, tools=_tools)
        if len(tools) > 1:
            optional_params["tools"] = tools

        ## Load Config
        config = litellm.AnthropicConfig.get_config()
        for k, v in config.items():
            if (
                k not in optional_params
            ):  # completion(top_k=3) > anthropic_config(top_k=3) <- allows for dynamic variables to be passed in
                optional_params[k] = v

        ## Handle user_id in metadata
        _litellm_metadata = litellm_params.get("metadata", None)
        if (
            _litellm_metadata
            and isinstance(_litellm_metadata, dict)
            and "user_id" in _litellm_metadata
            and not _valid_user_id(_litellm_metadata.get("user_id", None))
        ):
            optional_params["metadata"] = {"user_id": _litellm_metadata["user_id"]}

        data = {
            "model": model,
            "messages": anthropic_messages,
            **optional_params,
        }

        return data

    def _transform_response_for_json_mode(
        self,
        json_mode: Optional[bool],
        tool_calls: List[ChatCompletionToolCallChunk],
    ) -> Optional[LitellmMessage]:
        _message: Optional[LitellmMessage] = None
        if json_mode is True and len(tool_calls) == 1:
            # check if tool name is the default tool name
            json_mode_content_str: Optional[str] = None
            if (
                "name" in tool_calls[0]["function"]
                and tool_calls[0]["function"]["name"] == RESPONSE_FORMAT_TOOL_NAME
            ):
                json_mode_content_str = tool_calls[0]["function"].get("arguments")
            if json_mode_content_str is not None:
                _message = AnthropicConfig._convert_tool_response_to_message(
                    tool_calls=tool_calls,
                )
        return _message

    def extract_response_content(self, completion_response: dict) -> Tuple[
        str,
        Optional[List[Any]],
        Optional[
            List[
                Union[ChatCompletionThinkingBlock, ChatCompletionRedactedThinkingBlock]
            ]
        ],
        Optional[str],
        List[ChatCompletionToolCallChunk],
    ]:
        text_content = ""
        citations: Optional[List[Any]] = None
        thinking_blocks: Optional[
            List[
                Union[ChatCompletionThinkingBlock, ChatCompletionRedactedThinkingBlock]
            ]
        ] = None
        reasoning_content: Optional[str] = None
        tool_calls: List[ChatCompletionToolCallChunk] = []
        for idx, content in enumerate(completion_response["content"]):
            if content["type"] == "text":
                text_content += content["text"]
            ## TOOL CALLING
            elif content["type"] == "tool_use":
                tool_calls.append(
                    ChatCompletionToolCallChunk(
                        id=content["id"],
                        type="function",
                        function=ChatCompletionToolCallFunctionChunk(
                            name=content["name"],
                            arguments=json.dumps(content["input"]),
                        ),
                        index=idx,
                    )
                )

            elif content.get("thinking", None) is not None:
                if thinking_blocks is None:
                    thinking_blocks = []
                thinking_blocks.append(cast(ChatCompletionThinkingBlock, content))
            elif content["type"] == "redacted_thinking":
                if thinking_blocks is None:
                    thinking_blocks = []
                thinking_blocks.append(
                    cast(ChatCompletionRedactedThinkingBlock, content)
                )

            ## CITATIONS
            if content.get("citations") is not None:
                if citations is None:
                    citations = []
                citations.append(content["citations"])
        if thinking_blocks is not None:
            reasoning_content = ""
            for block in thinking_blocks:
                thinking_content = cast(Optional[str], block.get("thinking"))
                if thinking_content is not None:
                    reasoning_content += thinking_content

        return text_content, citations, thinking_blocks, reasoning_content, tool_calls

    def calculate_usage(
        self, usage_object: dict, reasoning_content: Optional[str]
    ) -> Usage:
        prompt_tokens = usage_object.get("input_tokens", 0)
        completion_tokens = usage_object.get("output_tokens", 0)
        _usage = usage_object
        cache_creation_input_tokens: int = 0
        cache_read_input_tokens: int = 0
        web_search_requests: Optional[int] = None
        if "cache_creation_input_tokens" in _usage:
            cache_creation_input_tokens = _usage["cache_creation_input_tokens"]
        if "cache_read_input_tokens" in _usage:
            cache_read_input_tokens = _usage["cache_read_input_tokens"]
            prompt_tokens += cache_read_input_tokens
        if "server_tool_use" in _usage:
            if "web_search_requests" in _usage["server_tool_use"]:
                web_search_requests = cast(
                    int, _usage["server_tool_use"]["web_search_requests"]
                )

        prompt_tokens_details = PromptTokensDetailsWrapper(
            cached_tokens=cache_read_input_tokens,
        )
        completion_token_details = (
            CompletionTokensDetailsWrapper(
                reasoning_tokens=token_counter(
                    text=reasoning_content, count_response_tokens=True
                )
            )
            if reasoning_content
            else None
        )
        total_tokens = prompt_tokens + completion_tokens

        usage = Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            prompt_tokens_details=prompt_tokens_details,
            cache_creation_input_tokens=cache_creation_input_tokens,
            cache_read_input_tokens=cache_read_input_tokens,
            completion_tokens_details=completion_token_details,
            server_tool_use=(
                ServerToolUse(web_search_requests=web_search_requests)
                if web_search_requests is not None
                else None
            ),
        )
        return usage

    def transform_parsed_response(
        self,
        completion_response: dict,
        raw_response: httpx.Response,
        model_response: ModelResponse,
        json_mode: Optional[bool] = None,
        prefix_prompt: Optional[str] = None,
    ):
        _hidden_params: Dict = {}
        _hidden_params["additional_headers"] = process_anthropic_headers(
            dict(raw_response.headers)
        )
        if "error" in completion_response:
            response_headers = getattr(raw_response, "headers", None)
            raise AnthropicError(
                message=str(completion_response["error"]),
                status_code=raw_response.status_code,
                headers=response_headers,
            )
        else:
            text_content = ""
            citations: Optional[List[Any]] = None
            thinking_blocks: Optional[
                List[
                    Union[
                        ChatCompletionThinkingBlock, ChatCompletionRedactedThinkingBlock
                    ]
                ]
            ] = None
            reasoning_content: Optional[str] = None
            tool_calls: List[ChatCompletionToolCallChunk] = []

            (
                text_content,
                citations,
                thinking_blocks,
                reasoning_content,
                tool_calls,
            ) = self.extract_response_content(completion_response=completion_response)

            if (
                prefix_prompt is not None
                and not text_content.startswith(prefix_prompt)
                and not litellm.disable_add_prefix_to_prompt
            ):
                text_content = prefix_prompt + text_content

            _message = litellm.Message(
                tool_calls=tool_calls,
                content=text_content or None,
                provider_specific_fields={
                    "citations": citations,
                    "thinking_blocks": thinking_blocks,
                },
                thinking_blocks=thinking_blocks,
                reasoning_content=reasoning_content,
            )

            ## HANDLE JSON MODE - anthropic returns single function call
            json_mode_message = self._transform_response_for_json_mode(
                json_mode=json_mode,
                tool_calls=tool_calls,
            )
            if json_mode_message is not None:
                completion_response["stop_reason"] = "stop"
                _message = json_mode_message

            model_response.choices[0].message = _message  # type: ignore
            model_response._hidden_params["original_response"] = completion_response[
                "content"
            ]  # allow user to access raw anthropic tool calling response

            model_response.choices[0].finish_reason = map_finish_reason(
                completion_response["stop_reason"]
            )

        ## CALCULATING USAGE
        usage = self.calculate_usage(
            usage_object=completion_response["usage"],
            reasoning_content=reasoning_content,
        )
        setattr(model_response, "usage", usage)  # type: ignore

        model_response.created = int(time.time())
        model_response.model = completion_response["model"]

        model_response._hidden_params = _hidden_params

        return model_response

    def get_prefix_prompt(self, messages: List[AllMessageValues]) -> Optional[str]:
        """
        Get the prefix prompt from the messages.

        Check last message
        - if it's assistant message, with 'prefix': true, return the content

        E.g. :    {"role": "assistant", "content": "Argentina", "prefix": True}
        """
        if len(messages) == 0:
            return None

        message = messages[-1]
        message_content = message.get("content")
        if (
            message["role"] == "assistant"
            and message.get("prefix", False)
            and isinstance(message_content, str)
        ):
            return message_content

        return None

    def transform_response(
        self,
        model: str,
        raw_response: httpx.Response,
        model_response: ModelResponse,
        logging_obj: LoggingClass,
        request_data: Dict,
        messages: List[AllMessageValues],
        optional_params: Dict,
        litellm_params: dict,
        encoding: Any,
        api_key: Optional[str] = None,
        json_mode: Optional[bool] = None,
    ) -> ModelResponse:
        ## LOGGING
        logging_obj.post_call(
            input=messages,
            api_key=api_key,
            original_response=raw_response.text,
            additional_args={"complete_input_dict": request_data},
        )

        ## RESPONSE OBJECT
        try:
            completion_response = raw_response.json()
        except Exception as e:
            response_headers = getattr(raw_response, "headers", None)
            raise AnthropicError(
                message="Unable to get json response - {}, Original Response: {}".format(
                    str(e), raw_response.text
                ),
                status_code=raw_response.status_code,
                headers=response_headers,
            )

        prefix_prompt = self.get_prefix_prompt(messages=messages)

        model_response = self.transform_parsed_response(
            completion_response=completion_response,
            raw_response=raw_response,
            model_response=model_response,
            json_mode=json_mode,
            prefix_prompt=prefix_prompt,
        )
        return model_response

    @staticmethod
    def _convert_tool_response_to_message(
        tool_calls: List[ChatCompletionToolCallChunk],
    ) -> Optional[LitellmMessage]:
        """
        In JSON mode, Anthropic API returns JSON schema as a tool call, we need to convert it to a message to follow the OpenAI format

        """
        ## HANDLE JSON MODE - anthropic returns single function call
        json_mode_content_str: Optional[str] = tool_calls[0]["function"].get(
            "arguments"
        )
        try:
            if json_mode_content_str is not None:
                args = json.loads(json_mode_content_str)
                if (
                    isinstance(args, dict)
                    and (values := args.get("values")) is not None
                ):
                    _message = litellm.Message(content=json.dumps(values))
                    return _message
                else:
                    # a lot of the times the `values` key is not present in the tool response
                    # relevant issue: https://github.com/BerriAI/litellm/issues/6741
                    _message = litellm.Message(content=json.dumps(args))
                    return _message
        except json.JSONDecodeError:
            # json decode error does occur, return the original tool response str
            return litellm.Message(content=json_mode_content_str)
        return None

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[Dict, httpx.Headers]
    ) -> BaseLLMException:
        return AnthropicError(
            status_code=status_code,
            message=error_message,
            headers=cast(httpx.Headers, headers),
        )


def _valid_user_id(user_id: str) -> bool:
    """
    Validate that user_id is not an email or phone number.
    Returns: bool: True if valid (not email or phone), False otherwise
    """
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    phone_pattern = r"^\+?[\d\s\(\)-]{7,}$"

    if re.match(email_pattern, user_id):
        return False
    if re.match(phone_pattern, user_id):
        return False

    return True

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\auth\handle_jwt.py ===
"""
Supports using JWT's for authenticating into the proxy.

Currently only supports admin.

JWT token must have 'litellm_proxy_admin' in scope.
"""

import json
import os
from typing import Any, List, Literal, Optional, Set, Tuple, cast

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from fastapi import HTTPException

from litellm._logging import verbose_proxy_logger
from litellm.caching.caching import DualCache
from litellm.litellm_core_utils.dot_notation_indexing import get_nested_value
from litellm.llms.custom_httpx.httpx_handler import HTTPHandler
from litellm.proxy._types import (
    RBAC_ROLES,
    JWKKeyValue,
    JWTAuthBuilderResult,
    JWTKeyItem,
    LiteLLM_EndUserTable,
    LiteLLM_JWTAuth,
    LiteLLM_OrganizationTable,
    LiteLLM_TeamTable,
    LiteLLM_UserTable,
    LitellmUserRoles,
    Member,
    ProxyErrorTypes,
    ProxyException,
    ScopeMapping,
    Span,
    TeamMemberAddRequest,
    UserAPIKeyAuth,
)
from litellm.proxy.auth.auth_checks import can_team_access_model
from litellm.proxy.utils import PrismaClient, ProxyLogging

from .auth_checks import (
    _allowed_routes_check,
    allowed_routes_check,
    get_actual_routes,
    get_end_user_object,
    get_org_object,
    get_role_based_models,
    get_role_based_routes,
    get_team_object,
    get_user_object,
)


class JWTHandler:
    """
    - treat the sub id passed in as the user id
    - return an error if id making request doesn't exist in proxy user table
    - track spend against the user id
    - if role="litellm_proxy_user" -> allow making calls + info. Can not edit budgets
    """

    prisma_client: Optional[PrismaClient]
    user_api_key_cache: DualCache

    def __init__(
        self,
    ) -> None:
        self.http_handler = HTTPHandler()
        self.leeway = 0

    def update_environment(
        self,
        prisma_client: Optional[PrismaClient],
        user_api_key_cache: DualCache,
        litellm_jwtauth: LiteLLM_JWTAuth,
        leeway: int = 0,
    ) -> None:
        self.prisma_client = prisma_client
        self.user_api_key_cache = user_api_key_cache
        self.litellm_jwtauth = litellm_jwtauth
        self.leeway = leeway

    def is_jwt(self, token: str):
        parts = token.split(".")
        return len(parts) == 3

    def _rbac_role_from_role_mapping(self, token: dict) -> Optional[RBAC_ROLES]:
        """
        Returns the RBAC role the token 'belongs' to based on role mappings.

        Args:
            token (dict): The JWT token containing role information

        Returns:
            Optional[RBAC_ROLES]: The mapped internal RBAC role if a mapping exists,
                                None otherwise

        Note:
            The function handles both single string roles and lists of roles from the JWT.
            If multiple mappings match the JWT roles, the first matching mapping is returned.
        """
        if self.litellm_jwtauth.role_mappings is None:
            return None

        jwt_role = self.get_jwt_role(token=token, default_value=None)
        if not jwt_role:
            return None

        jwt_role_set = set(jwt_role)

        for role_mapping in self.litellm_jwtauth.role_mappings:
            # Check if the mapping role matches any of the JWT roles
            if role_mapping.role in jwt_role_set:
                return role_mapping.internal_role

        return None

    def get_rbac_role(self, token: dict) -> Optional[RBAC_ROLES]:
        """
        Returns the RBAC role the token 'belongs' to.

        RBAC roles allowed to make requests:
        - PROXY_ADMIN: can make requests to all routes
        - TEAM: can make requests to routes associated with a team
        - INTERNAL_USER: can make requests to routes associated with a user

        Resolves: https://github.com/BerriAI/litellm/issues/6793

        Returns:
        - PROXY_ADMIN: if token is admin
        - TEAM: if token is associated with a team
        - INTERNAL_USER: if token is associated with a user
        - None: if token is not associated with a team or user
        """
        scopes = self.get_scopes(token=token)
        is_admin = self.is_admin(scopes=scopes)
        user_roles = self.get_user_roles(token=token, default_value=None)

        if is_admin:
            return LitellmUserRoles.PROXY_ADMIN
        elif self.get_team_id(token=token, default_value=None) is not None:
            return LitellmUserRoles.TEAM
        elif self.get_user_id(token=token, default_value=None) is not None:
            return LitellmUserRoles.INTERNAL_USER
        elif user_roles is not None and self.is_allowed_user_role(
            user_roles=user_roles
        ):
            return LitellmUserRoles.INTERNAL_USER
        elif rbac_role := self._rbac_role_from_role_mapping(token=token):
            return rbac_role

        return None

    def is_admin(self, scopes: list) -> bool:
        if self.litellm_jwtauth.admin_jwt_scope in scopes:
            return True
        return False

    def get_team_ids_from_jwt(self, token: dict) -> List[str]:
        if (
            self.litellm_jwtauth.team_ids_jwt_field is not None
            and token.get(self.litellm_jwtauth.team_ids_jwt_field) is not None
        ):
            return token[self.litellm_jwtauth.team_ids_jwt_field]
        return []

    def get_end_user_id(
        self, token: dict, default_value: Optional[str]
    ) -> Optional[str]:
        try:
            if self.litellm_jwtauth.end_user_id_jwt_field is not None:
                user_id = token[self.litellm_jwtauth.end_user_id_jwt_field]
            else:
                user_id = None
        except KeyError:
            user_id = default_value

        return user_id

    def is_required_team_id(self) -> bool:
        """
        Returns:
        - True: if 'team_id_jwt_field' is set
        - False: if not
        """
        if self.litellm_jwtauth.team_id_jwt_field is None:
            return False
        return True

    def is_enforced_email_domain(self) -> bool:
        """
        Returns:
        - True: if 'user_allowed_email_domain' is set
        - False: if 'user_allowed_email_domain' is None
        """

        if self.litellm_jwtauth.user_allowed_email_domain is not None and isinstance(
            self.litellm_jwtauth.user_allowed_email_domain, str
        ):
            return True
        return False

    def get_team_id(self, token: dict, default_value: Optional[str]) -> Optional[str]:
        try:
            if self.litellm_jwtauth.team_id_jwt_field is not None:
                team_id = token[self.litellm_jwtauth.team_id_jwt_field]
            elif self.litellm_jwtauth.team_id_default is not None:
                team_id = self.litellm_jwtauth.team_id_default
            else:
                team_id = None
        except KeyError:
            team_id = default_value
        return team_id

    def is_upsert_user_id(self, valid_user_email: Optional[bool] = None) -> bool:
        """
        Returns:
        - True: if 'user_id_upsert' is set AND valid_user_email is not False
        - False: if not
        """
        if valid_user_email is False:
            return False
        return self.litellm_jwtauth.user_id_upsert

    def get_user_id(self, token: dict, default_value: Optional[str]) -> Optional[str]:
        try:
            if self.litellm_jwtauth.user_id_jwt_field is not None:
                user_id = token[self.litellm_jwtauth.user_id_jwt_field]
            else:
                user_id = default_value
        except KeyError:
            user_id = default_value
        return user_id

    def get_user_roles(
        self, token: dict, default_value: Optional[List[str]]
    ) -> Optional[List[str]]:
        """
        Returns the user role from the token.

        Set via 'user_roles_jwt_field' in the config.
        """
        try:
            if self.litellm_jwtauth.user_roles_jwt_field is not None:
                user_roles = get_nested_value(
                    data=token,
                    key_path=self.litellm_jwtauth.user_roles_jwt_field,
                    default=default_value,
                )
            else:
                user_roles = default_value
        except KeyError:
            user_roles = default_value
        return user_roles

    def get_jwt_role(
        self, token: dict, default_value: Optional[List[str]]
    ) -> Optional[List[str]]:
        """
        Generic implementation of `get_user_roles` that can be used for both user and team roles.

        Returns the jwt role from the token.

        Set via 'roles_jwt_field' in the config.
        """
        try:
            if self.litellm_jwtauth.roles_jwt_field is not None:
                user_roles = get_nested_value(
                    data=token,
                    key_path=self.litellm_jwtauth.roles_jwt_field,
                    default=default_value,
                )
            else:
                user_roles = default_value
        except KeyError:
            user_roles = default_value
        return user_roles

    def is_allowed_user_role(self, user_roles: Optional[List[str]]) -> bool:
        """
        Returns the user role from the token.

        Set via 'user_allowed_roles' in the config.
        """
        if (
            user_roles is not None
            and self.litellm_jwtauth.user_allowed_roles is not None
            and any(
                role in self.litellm_jwtauth.user_allowed_roles for role in user_roles
            )
        ):
            return True
        return False

    def get_user_email(
        self, token: dict, default_value: Optional[str]
    ) -> Optional[str]:
        try:
            if self.litellm_jwtauth.user_email_jwt_field is not None:
                user_email = token[self.litellm_jwtauth.user_email_jwt_field]
            else:
                user_email = None
        except KeyError:
            user_email = default_value
        return user_email

    def get_object_id(self, token: dict, default_value: Optional[str]) -> Optional[str]:
        try:
            if self.litellm_jwtauth.object_id_jwt_field is not None:
                object_id = token[self.litellm_jwtauth.object_id_jwt_field]
            else:
                object_id = default_value
        except KeyError:
            object_id = default_value
        return object_id

    def get_org_id(self, token: dict, default_value: Optional[str]) -> Optional[str]:
        try:
            if self.litellm_jwtauth.org_id_jwt_field is not None:
                org_id = token[self.litellm_jwtauth.org_id_jwt_field]
            else:
                org_id = None
        except KeyError:
            org_id = default_value
        return org_id

    def get_scopes(self, token: dict) -> List[str]:
        try:
            if isinstance(token["scope"], str):
                # Assuming the scopes are stored in 'scope' claim and are space-separated
                scopes = token["scope"].split()
            elif isinstance(token["scope"], list):
                scopes = token["scope"]
            else:
                raise Exception(
                    f"Unmapped scope type - {type(token['scope'])}. Supported types - list, str."
                )
        except KeyError:
            scopes = []
        return scopes

    async def get_public_key(self, kid: Optional[str]) -> dict:
        keys_url = os.getenv("JWT_PUBLIC_KEY_URL")

        if keys_url is None:
            raise Exception("Missing JWT Public Key URL from environment.")

        keys_url_list = [url.strip() for url in keys_url.split(",")]

        for key_url in keys_url_list:
            cache_key = f"litellm_jwt_auth_keys_{key_url}"

            cached_keys = await self.user_api_key_cache.async_get_cache(cache_key)

            if cached_keys is None:
                response = await self.http_handler.get(key_url)

                response_json = response.json()
                if "keys" in response_json:
                    keys: JWKKeyValue = response.json()["keys"]
                else:
                    keys = response_json

                await self.user_api_key_cache.async_set_cache(
                    key=cache_key,
                    value=keys,
                    ttl=self.litellm_jwtauth.public_key_ttl,  # cache for 10 mins
                )
            else:
                keys = cached_keys

            public_key = self.parse_keys(keys=keys, kid=kid)
            if public_key is not None:
                return cast(dict, public_key)

        raise Exception(
            f"No matching public key found. keys={keys_url_list}, kid={kid}"
        )

    def parse_keys(self, keys: JWKKeyValue, kid: Optional[str]) -> Optional[JWTKeyItem]:
        public_key: Optional[JWTKeyItem] = None
        if len(keys) == 1:
            if isinstance(keys, dict) and (keys.get("kid", None) == kid or kid is None):
                public_key = keys
            elif isinstance(keys, list) and (
                keys[0].get("kid", None) == kid or kid is None
            ):
                public_key = keys[0]
        elif len(keys) > 1:
            for key in keys:
                if isinstance(key, dict):
                    key_kid = key.get("kid", None)
                else:
                    key_kid = None
                if (
                    kid is not None
                    and isinstance(key, dict)
                    and key_kid is not None
                    and key_kid == kid
                ):
                    public_key = key

        return public_key

    def is_allowed_domain(self, user_email: str) -> bool:
        if self.litellm_jwtauth.user_allowed_email_domain is None:
            return True

        email_domain = user_email.split("@")[-1]  # Extract domain from email
        if email_domain == self.litellm_jwtauth.user_allowed_email_domain:
            return True
        else:
            return False

    async def auth_jwt(self, token: str) -> dict:
        # Supported algos: https://pyjwt.readthedocs.io/en/stable/algorithms.html
        # "Warning: Make sure not to mix symmetric and asymmetric algorithms that interpret
        #   the key in different ways (e.g. HS* and RS*)."
        algorithms = ["RS256", "RS384", "RS512", "PS256", "PS384", "PS512"]

        audience = os.getenv("JWT_AUDIENCE")
        decode_options = None
        if audience is None:
            decode_options = {"verify_aud": False}

        import jwt
        from jwt.algorithms import RSAAlgorithm

        header = jwt.get_unverified_header(token)

        verbose_proxy_logger.debug("header: %s", header)

        kid = header.get("kid", None)

        public_key = await self.get_public_key(kid=kid)

        if public_key is not None and isinstance(public_key, dict):
            jwk = {}
            if "kty" in public_key:
                jwk["kty"] = public_key["kty"]
            if "kid" in public_key:
                jwk["kid"] = public_key["kid"]
            if "n" in public_key:
                jwk["n"] = public_key["n"]
            if "e" in public_key:
                jwk["e"] = public_key["e"]

            public_key_rsa = RSAAlgorithm.from_jwk(json.dumps(jwk))

            try:
                # decode the token using the public key
                payload = jwt.decode(
                    token,
                    public_key_rsa,  # type: ignore
                    algorithms=algorithms,
                    options=decode_options,
                    audience=audience,
                    leeway=self.leeway,  # allow testing of expired tokens
                )
                return payload

            except jwt.ExpiredSignatureError:
                # the token is expired, do something to refresh it
                raise Exception("Token Expired")
            except Exception as e:
                raise Exception(f"Validation fails: {str(e)}")
        elif public_key is not None and isinstance(public_key, str):
            try:
                cert = x509.load_pem_x509_certificate(
                    public_key.encode(), default_backend()
                )

                # Extract public key
                key = cert.public_key().public_bytes(
                    serialization.Encoding.PEM,
                    serialization.PublicFormat.SubjectPublicKeyInfo,
                )

                # decode the token using the public key
                payload = jwt.decode(
                    token,
                    key,
                    algorithms=algorithms,
                    audience=audience,
                    options=decode_options,
                )
                return payload

            except jwt.ExpiredSignatureError:
                # the token is expired, do something to refresh it
                raise Exception("Token Expired")
            except Exception as e:
                raise Exception(f"Validation fails: {str(e)}")

        raise Exception("Invalid JWT Submitted")

    async def close(self):
        await self.http_handler.close()


class JWTAuthManager:
    """Manages JWT authentication and authorization operations"""

    @staticmethod
    def can_rbac_role_call_route(
        rbac_role: RBAC_ROLES,
        general_settings: dict,
        route: str,
    ) -> Literal[True]:
        """
        Checks if user is allowed to access the route, based on their role.
        """
        role_based_routes = get_role_based_routes(
            rbac_role=rbac_role, general_settings=general_settings
        )

        if role_based_routes is None or route is None:
            return True

        is_allowed = _allowed_routes_check(
            user_route=route,
            allowed_routes=role_based_routes,
        )

        if not is_allowed:
            raise HTTPException(
                status_code=403,
                detail=f"Role={rbac_role} not allowed to call route={route}. Allowed routes={role_based_routes}",
            )

        return True

    @staticmethod
    def can_rbac_role_call_model(
        rbac_role: RBAC_ROLES,
        general_settings: dict,
        model: Optional[str],
    ) -> Literal[True]:
        """
        Checks if user is allowed to access the model, based on their role.
        """
        role_based_models = get_role_based_models(
            rbac_role=rbac_role, general_settings=general_settings
        )
        if role_based_models is None or model is None:
            return True

        if model not in role_based_models:
            raise HTTPException(
                status_code=403,
                detail=f"Role={rbac_role} not allowed to call model={model}. Allowed models={role_based_models}",
            )

        return True

    @staticmethod
    def check_scope_based_access(
        scope_mappings: List[ScopeMapping],
        scopes: List[str],
        request_data: dict,
        general_settings: dict,
    ) -> None:
        """
        Check if scope allows access to the requested model
        """
        if not scope_mappings:
            return None

        allowed_models = []
        for sm in scope_mappings:
            if sm.scope in scopes and sm.models:
                allowed_models.extend(sm.models)

        requested_model = request_data.get("model")

        if not requested_model:
            return None

        if requested_model not in allowed_models:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "model={} not allowed. Allowed_models={}".format(
                        requested_model, allowed_models
                    )
                },
            )
        return None

    @staticmethod
    async def check_rbac_role(
        jwt_handler: JWTHandler,
        jwt_valid_token: dict,
        general_settings: dict,
        request_data: dict,
        route: str,
        rbac_role: Optional[RBAC_ROLES],
    ) -> None:
        """Validate RBAC role and model access permissions"""
        if jwt_handler.litellm_jwtauth.enforce_rbac is True:
            if rbac_role is None:
                raise HTTPException(
                    status_code=403,
                    detail="Unmatched token passed in. enforce_rbac is set to True. Token must belong to a proxy admin, team, or user.",
                )
            JWTAuthManager.can_rbac_role_call_model(
                rbac_role=rbac_role,
                general_settings=general_settings,
                model=request_data.get("model"),
            )
            JWTAuthManager.can_rbac_role_call_route(
                rbac_role=rbac_role,
                general_settings=general_settings,
                route=route,
            )

    @staticmethod
    async def check_admin_access(
        jwt_handler: JWTHandler,
        scopes: list,
        route: str,
        user_id: Optional[str],
        org_id: Optional[str],
        api_key: str,
    ) -> Optional[JWTAuthBuilderResult]:
        """Check admin status and route access permissions"""
        if not jwt_handler.is_admin(scopes=scopes):
            return None

        is_allowed = allowed_routes_check(
            user_role=LitellmUserRoles.PROXY_ADMIN,
            user_route=route,
            litellm_proxy_roles=jwt_handler.litellm_jwtauth,
        )
        if not is_allowed:
            allowed_routes: List[Any] = jwt_handler.litellm_jwtauth.admin_allowed_routes
            actual_routes = get_actual_routes(allowed_routes=allowed_routes)
            raise Exception(
                f"Admin not allowed to access this route. Route={route}, Allowed Routes={actual_routes}"
            )

        return JWTAuthBuilderResult(
            is_proxy_admin=True,
            team_object=None,
            user_object=None,
            end_user_object=None,
            org_object=None,
            token=api_key,
            team_id=None,
            user_id=user_id,
            end_user_id=None,
            org_id=org_id,
        )

    @staticmethod
    async def find_and_validate_specific_team_id(
        jwt_handler: JWTHandler,
        jwt_valid_token: dict,
        prisma_client: Optional[PrismaClient],
        user_api_key_cache: DualCache,
        parent_otel_span: Optional[Span],
        proxy_logging_obj: ProxyLogging,
    ) -> Tuple[Optional[str], Optional[LiteLLM_TeamTable]]:
        """Find and validate specific team ID"""
        individual_team_id = jwt_handler.get_team_id(
            token=jwt_valid_token, default_value=None
        )

        if not individual_team_id and jwt_handler.is_required_team_id() is True:
            raise Exception(
                f"No team id found in token. Checked team_id field '{jwt_handler.litellm_jwtauth.team_id_jwt_field}'"
            )

        ## VALIDATE TEAM OBJECT ###
        team_object: Optional[LiteLLM_TeamTable] = None
        if individual_team_id:
            team_object = await get_team_object(
                team_id=individual_team_id,
                prisma_client=prisma_client,
                user_api_key_cache=user_api_key_cache,
                parent_otel_span=parent_otel_span,
                proxy_logging_obj=proxy_logging_obj,
                team_id_upsert=jwt_handler.litellm_jwtauth.team_id_upsert,
            )

        return individual_team_id, team_object

    @staticmethod
    def get_all_team_ids(jwt_handler: JWTHandler, jwt_valid_token: dict) -> Set[str]:
        """Get combined team IDs from groups and individual team_id"""
        team_ids_from_groups = jwt_handler.get_team_ids_from_jwt(token=jwt_valid_token)

        all_team_ids = set(team_ids_from_groups)

        return all_team_ids

    @staticmethod
    async def find_team_with_model_access(
        team_ids: Set[str],
        requested_model: Optional[str],
        route: str,
        jwt_handler: JWTHandler,
        prisma_client: Optional[PrismaClient],
        user_api_key_cache: DualCache,
        parent_otel_span: Optional[Span],
        proxy_logging_obj: ProxyLogging,
    ) -> Tuple[Optional[str], Optional[LiteLLM_TeamTable]]:
        """Find first team with access to the requested model"""

        if not team_ids:
            if jwt_handler.litellm_jwtauth.enforce_team_based_model_access:
                raise HTTPException(
                    status_code=403,
                    detail="No teams found in token. `enforce_team_based_model_access` is set to True. Token must belong to a team.",
                )
            return None, None

        for team_id in team_ids:
            try:
                team_object = await get_team_object(
                    team_id=team_id,
                    prisma_client=prisma_client,
                    user_api_key_cache=user_api_key_cache,
                    parent_otel_span=parent_otel_span,
                    proxy_logging_obj=proxy_logging_obj,
                )

                if team_object and team_object.models is not None:
                    team_models = team_object.models
                    if isinstance(team_models, list) and (
                        not requested_model
                        or can_team_access_model(
                            model=requested_model,
                            team_object=team_object,
                            llm_router=None,
                            team_model_aliases=None,
                        )
                    ):
                        is_allowed = allowed_routes_check(
                            user_role=LitellmUserRoles.TEAM,
                            user_route=route,
                            litellm_proxy_roles=jwt_handler.litellm_jwtauth,
                        )
                        if is_allowed:
                            return team_id, team_object
            except Exception:
                continue

        if requested_model:
            raise HTTPException(
                status_code=403,
                detail=f"No team has access to the requested model: {requested_model}. Checked teams={team_ids}. Check `/models` to see all available models.",
            )

        return None, None

    @staticmethod
    async def get_user_info(
        jwt_handler: JWTHandler,
        jwt_valid_token: dict,
    ) -> Tuple[Optional[str], Optional[str], Optional[bool]]:
        """Get user email and validation status"""
        user_email = jwt_handler.get_user_email(
            token=jwt_valid_token, default_value=None
        )
        valid_user_email = None
        if jwt_handler.is_enforced_email_domain():
            valid_user_email = (
                False
                if user_email is None
                else jwt_handler.is_allowed_domain(user_email=user_email)
            )
        user_id = jwt_handler.get_user_id(
            token=jwt_valid_token, default_value=user_email
        )
        return user_id, user_email, valid_user_email

    @staticmethod
    async def get_objects(
        user_id: Optional[str],
        user_email: Optional[str],
        org_id: Optional[str],
        end_user_id: Optional[str],
        valid_user_email: Optional[bool],
        jwt_handler: JWTHandler,
        prisma_client: Optional[PrismaClient],
        user_api_key_cache: DualCache,
        parent_otel_span: Optional[Span],
        proxy_logging_obj: ProxyLogging,
    ) -> Tuple[
        Optional[LiteLLM_UserTable],
        Optional[LiteLLM_OrganizationTable],
        Optional[LiteLLM_EndUserTable],
    ]:
        """Get user, org, and end user objects"""
        org_object: Optional[LiteLLM_OrganizationTable] = None
        if org_id:
            org_object = (
                await get_org_object(
                    org_id=org_id,
                    prisma_client=prisma_client,
                    user_api_key_cache=user_api_key_cache,
                    parent_otel_span=parent_otel_span,
                    proxy_logging_obj=proxy_logging_obj,
                )
                if org_id
                else None
            )

        user_object: Optional[LiteLLM_UserTable] = None
        if user_id:
            user_object = (
                await get_user_object(
                    user_id=user_id,
                    prisma_client=prisma_client,
                    user_api_key_cache=user_api_key_cache,
                    user_id_upsert=jwt_handler.is_upsert_user_id(
                        valid_user_email=valid_user_email
                    ),
                    parent_otel_span=parent_otel_span,
                    proxy_logging_obj=proxy_logging_obj,
                    user_email=user_email,
                    sso_user_id=user_id,
                )
                if user_id
                else None
            )

        end_user_object: Optional[LiteLLM_EndUserTable] = None
        if end_user_id:
            end_user_object = (
                await get_end_user_object(
                    end_user_id=end_user_id,
                    prisma_client=prisma_client,
                    user_api_key_cache=user_api_key_cache,
                    parent_otel_span=parent_otel_span,
                    proxy_logging_obj=proxy_logging_obj,
                )
                if end_user_id
                else None
            )

        return user_object, org_object, end_user_object

    @staticmethod
    def validate_object_id(
        user_id: Optional[str],
        team_id: Optional[str],
        enforce_rbac: bool,
        is_proxy_admin: bool,
    ) -> Literal[True]:
        """If enforce_rbac is true, validate that a valid rbac id is returned for spend tracking"""
        if enforce_rbac and not is_proxy_admin and not user_id and not team_id:
            raise HTTPException(
                status_code=403,
                detail="No user or team id found in token. enforce_rbac is set to True. Token must belong to a proxy admin, team, or user.",
            )
        return True

    @staticmethod
    async def map_user_to_teams(
        user_object: Optional[LiteLLM_UserTable],
        team_object: Optional[LiteLLM_TeamTable],
    ):
        """
        Map user to teams.
        - If user is not in team, add them to the team
        - If user is in team, do nothing
        """
        from litellm.proxy.management_endpoints.team_endpoints import team_member_add

        if not user_object:
            return None

        if not team_object:
            return None

        # check if user is in team
        for member in team_object.members_with_roles:
            if member.user_id and member.user_id == user_object.user_id:
                return None

        data = TeamMemberAddRequest(
            member=Member(
                user_id=user_object.user_id,
                role="user",  # [TODO]: allow controlling role within team based on jwt token
            ),
            team_id=team_object.team_id,
        )
        # add user to team - make this non-blocking to avoid authentication failures
        try:
            await team_member_add(
                data=data,
                user_api_key_dict=UserAPIKeyAuth(
                    user_role=LitellmUserRoles.PROXY_ADMIN
                ),  # [TODO]: expose an internal service role, for better tracking
            )
            verbose_proxy_logger.debug(
                f"Successfully added user {user_object.user_id} to team {team_object.team_id}"
            )
        except ProxyException as e:
            if e.type == ProxyErrorTypes.team_member_already_in_team:
                verbose_proxy_logger.debug(
                    f"User {user_object.user_id} is already a member of team {team_object.team_id}"
                )
                return None
            else:
                raise e
        return None

    @staticmethod
    async def auth_builder(
        api_key: str,
        jwt_handler: JWTHandler,
        request_data: dict,
        general_settings: dict,
        route: str,
        prisma_client: Optional[PrismaClient],
        user_api_key_cache: DualCache,
        parent_otel_span: Optional[Span],
        proxy_logging_obj: ProxyLogging,
    ) -> JWTAuthBuilderResult:
        """Main authentication and authorization builder"""
        jwt_valid_token: dict = await jwt_handler.auth_jwt(token=api_key)

        # Check custom validate
        if jwt_handler.litellm_jwtauth.custom_validate:
            if not jwt_handler.litellm_jwtauth.custom_validate(jwt_valid_token):
                raise HTTPException(
                    status_code=403,
                    detail="Invalid JWT token",
                )

        # Check RBAC
        rbac_role = jwt_handler.get_rbac_role(token=jwt_valid_token)
        await JWTAuthManager.check_rbac_role(
            jwt_handler,
            jwt_valid_token,
            general_settings,
            request_data,
            route,
            rbac_role,
        )

        # Check Scope Based Access
        scopes = jwt_handler.get_scopes(token=jwt_valid_token)
        if (
            jwt_handler.litellm_jwtauth.enforce_scope_based_access
            and jwt_handler.litellm_jwtauth.scope_mappings
        ):
            JWTAuthManager.check_scope_based_access(
                scope_mappings=jwt_handler.litellm_jwtauth.scope_mappings,
                scopes=scopes,
                request_data=request_data,
                general_settings=general_settings,
            )

        object_id = jwt_handler.get_object_id(token=jwt_valid_token, default_value=None)

        # Get basic user info
        scopes = jwt_handler.get_scopes(token=jwt_valid_token)
        user_id, user_email, valid_user_email = await JWTAuthManager.get_user_info(
            jwt_handler, jwt_valid_token
        )

        # Get IDs
        org_id = jwt_handler.get_org_id(token=jwt_valid_token, default_value=None)
        end_user_id = jwt_handler.get_end_user_id(
            token=jwt_valid_token, default_value=None
        )
        team_id: Optional[str] = None
        team_object: Optional[LiteLLM_TeamTable] = None
        object_id = jwt_handler.get_object_id(token=jwt_valid_token, default_value=None)

        if rbac_role and object_id:
            if rbac_role == LitellmUserRoles.TEAM:
                team_id = object_id
            elif rbac_role == LitellmUserRoles.INTERNAL_USER:
                user_id = object_id

        # Check admin access
        admin_result = await JWTAuthManager.check_admin_access(
            jwt_handler, scopes, route, user_id, org_id, api_key
        )
        if admin_result:
            return admin_result

        # Get team with model access
        ## SPECIFIC TEAM ID

        if not team_id:
            (
                team_id,
                team_object,
            ) = await JWTAuthManager.find_and_validate_specific_team_id(
                jwt_handler,
                jwt_valid_token,
                prisma_client,
                user_api_key_cache,
                parent_otel_span,
                proxy_logging_obj,
            )

        if not team_object and not team_id:
            ## CHECK USER GROUP ACCESS
            all_team_ids = JWTAuthManager.get_all_team_ids(jwt_handler, jwt_valid_token)
            team_id, team_object = await JWTAuthManager.find_team_with_model_access(
                team_ids=all_team_ids,
                requested_model=request_data.get("model"),
                route=route,
                jwt_handler=jwt_handler,
                prisma_client=prisma_client,
                user_api_key_cache=user_api_key_cache,
                parent_otel_span=parent_otel_span,
                proxy_logging_obj=proxy_logging_obj,
            )

        # Get other objects
        user_object, org_object, end_user_object = await JWTAuthManager.get_objects(
            user_id=user_id,
            user_email=user_email,
            org_id=org_id,
            end_user_id=end_user_id,
            valid_user_email=valid_user_email,
            jwt_handler=jwt_handler,
            prisma_client=prisma_client,
            user_api_key_cache=user_api_key_cache,
            parent_otel_span=parent_otel_span,
            proxy_logging_obj=proxy_logging_obj,
        )

        ## MAP USER TO TEAMS
        await JWTAuthManager.map_user_to_teams(
            user_object=user_object,
            team_object=team_object,
        )

        # Validate that a valid rbac id is returned for spend tracking
        JWTAuthManager.validate_object_id(
            user_id=user_id,
            team_id=team_id,
            enforce_rbac=general_settings.get("enforce_rbac", False),
            is_proxy_admin=False,
        )

        # check if user is proxy admin
        if user_object and user_object.user_role == LitellmUserRoles.PROXY_ADMIN:
            is_proxy_admin = True
        else:
            is_proxy_admin = False

        return JWTAuthBuilderResult(
            is_proxy_admin=is_proxy_admin,
            team_id=team_id,
            team_object=team_object,
            user_id=user_id,
            user_object=user_object,
            org_id=org_id,
            org_object=org_object,
            end_user_id=end_user_id,
            end_user_object=end_user_object,
            token=api_key,
        )

# === NexusCore/openenv\Lib\site-packages\jinja2\runtime.py ===
"""The runtime functions and state used by compiled templates."""

import functools
import sys
import typing as t
from collections import abc
from itertools import chain

from markupsafe import escape  # noqa: F401
from markupsafe import Markup
from markupsafe import soft_str

from .async_utils import auto_aiter
from .async_utils import auto_await  # noqa: F401
from .exceptions import TemplateNotFound  # noqa: F401
from .exceptions import TemplateRuntimeError  # noqa: F401
from .exceptions import UndefinedError
from .nodes import EvalContext
from .utils import _PassArg
from .utils import concat
from .utils import internalcode
from .utils import missing
from .utils import Namespace  # noqa: F401
from .utils import object_type_repr
from .utils import pass_eval_context

V = t.TypeVar("V")
F = t.TypeVar("F", bound=t.Callable[..., t.Any])

if t.TYPE_CHECKING:
    import logging

    import typing_extensions as te

    from .environment import Environment

    class LoopRenderFunc(te.Protocol):
        def __call__(
            self,
            reciter: t.Iterable[V],
            loop_render_func: "LoopRenderFunc",
            depth: int = 0,
        ) -> str: ...


# these variables are exported to the template runtime
exported = [
    "LoopContext",
    "TemplateReference",
    "Macro",
    "Markup",
    "TemplateRuntimeError",
    "missing",
    "escape",
    "markup_join",
    "str_join",
    "identity",
    "TemplateNotFound",
    "Namespace",
    "Undefined",
    "internalcode",
]
async_exported = [
    "AsyncLoopContext",
    "auto_aiter",
    "auto_await",
]


def identity(x: V) -> V:
    """Returns its argument. Useful for certain things in the
    environment.
    """
    return x


def markup_join(seq: t.Iterable[t.Any]) -> str:
    """Concatenation that escapes if necessary and converts to string."""
    buf = []
    iterator = map(soft_str, seq)
    for arg in iterator:
        buf.append(arg)
        if hasattr(arg, "__html__"):
            return Markup("").join(chain(buf, iterator))
    return concat(buf)


def str_join(seq: t.Iterable[t.Any]) -> str:
    """Simple args to string conversion and concatenation."""
    return concat(map(str, seq))


def new_context(
    environment: "Environment",
    template_name: t.Optional[str],
    blocks: t.Dict[str, t.Callable[["Context"], t.Iterator[str]]],
    vars: t.Optional[t.Dict[str, t.Any]] = None,
    shared: bool = False,
    globals: t.Optional[t.MutableMapping[str, t.Any]] = None,
    locals: t.Optional[t.Mapping[str, t.Any]] = None,
) -> "Context":
    """Internal helper for context creation."""
    if vars is None:
        vars = {}
    if shared:
        parent = vars
    else:
        parent = dict(globals or (), **vars)
    if locals:
        # if the parent is shared a copy should be created because
        # we don't want to modify the dict passed
        if shared:
            parent = dict(parent)
        for key, value in locals.items():
            if value is not missing:
                parent[key] = value
    return environment.context_class(
        environment, parent, template_name, blocks, globals=globals
    )


class TemplateReference:
    """The `self` in templates."""

    def __init__(self, context: "Context") -> None:
        self.__context = context

    def __getitem__(self, name: str) -> t.Any:
        blocks = self.__context.blocks[name]
        return BlockReference(name, self.__context, blocks, 0)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.__context.name!r}>"


def _dict_method_all(dict_method: F) -> F:
    @functools.wraps(dict_method)
    def f_all(self: "Context") -> t.Any:
        return dict_method(self.get_all())

    return t.cast(F, f_all)


@abc.Mapping.register
class Context:
    """The template context holds the variables of a template.  It stores the
    values passed to the template and also the names the template exports.
    Creating instances is neither supported nor useful as it's created
    automatically at various stages of the template evaluation and should not
    be created by hand.

    The context is immutable.  Modifications on :attr:`parent` **must not**
    happen and modifications on :attr:`vars` are allowed from generated
    template code only.  Template filters and global functions marked as
    :func:`pass_context` get the active context passed as first argument
    and are allowed to access the context read-only.

    The template context supports read only dict operations (`get`,
    `keys`, `values`, `items`, `iterkeys`, `itervalues`, `iteritems`,
    `__getitem__`, `__contains__`).  Additionally there is a :meth:`resolve`
    method that doesn't fail with a `KeyError` but returns an
    :class:`Undefined` object for missing variables.
    """

    def __init__(
        self,
        environment: "Environment",
        parent: t.Dict[str, t.Any],
        name: t.Optional[str],
        blocks: t.Dict[str, t.Callable[["Context"], t.Iterator[str]]],
        globals: t.Optional[t.MutableMapping[str, t.Any]] = None,
    ):
        self.parent = parent
        self.vars: t.Dict[str, t.Any] = {}
        self.environment: Environment = environment
        self.eval_ctx = EvalContext(self.environment, name)
        self.exported_vars: t.Set[str] = set()
        self.name = name
        self.globals_keys = set() if globals is None else set(globals)

        # create the initial mapping of blocks.  Whenever template inheritance
        # takes place the runtime will update this mapping with the new blocks
        # from the template.
        self.blocks = {k: [v] for k, v in blocks.items()}

    def super(
        self, name: str, current: t.Callable[["Context"], t.Iterator[str]]
    ) -> t.Union["BlockReference", "Undefined"]:
        """Render a parent block."""
        try:
            blocks = self.blocks[name]
            index = blocks.index(current) + 1
            blocks[index]
        except LookupError:
            return self.environment.undefined(
                f"there is no parent block called {name!r}.", name="super"
            )
        return BlockReference(name, self, blocks, index)

    def get(self, key: str, default: t.Any = None) -> t.Any:
        """Look up a variable by name, or return a default if the key is
        not found.

        :param key: The variable name to look up.
        :param default: The value to return if the key is not found.
        """
        try:
            return self[key]
        except KeyError:
            return default

    def resolve(self, key: str) -> t.Union[t.Any, "Undefined"]:
        """Look up a variable by name, or return an :class:`Undefined`
        object if the key is not found.

        If you need to add custom behavior, override
        :meth:`resolve_or_missing`, not this method. The various lookup
        functions use that method, not this one.

        :param key: The variable name to look up.
        """
        rv = self.resolve_or_missing(key)

        if rv is missing:
            return self.environment.undefined(name=key)

        return rv

    def resolve_or_missing(self, key: str) -> t.Any:
        """Look up a variable by name, or return a ``missing`` sentinel
        if the key is not found.

        Override this method to add custom lookup behavior.
        :meth:`resolve`, :meth:`get`, and :meth:`__getitem__` use this
        method. Don't call this method directly.

        :param key: The variable name to look up.
        """
        if key in self.vars:
            return self.vars[key]

        if key in self.parent:
            return self.parent[key]

        return missing

    def get_exported(self) -> t.Dict[str, t.Any]:
        """Get a new dict with the exported variables."""
        return {k: self.vars[k] for k in self.exported_vars}

    def get_all(self) -> t.Dict[str, t.Any]:
        """Return the complete context as dict including the exported
        variables.  For optimizations reasons this might not return an
        actual copy so be careful with using it.
        """
        if not self.vars:
            return self.parent
        if not self.parent:
            return self.vars
        return dict(self.parent, **self.vars)

    @internalcode
    def call(
        __self,
        __obj: t.Callable[..., t.Any],
        *args: t.Any,
        **kwargs: t.Any,  # noqa: B902
    ) -> t.Union[t.Any, "Undefined"]:
        """Call the callable with the arguments and keyword arguments
        provided but inject the active context or environment as first
        argument if the callable has :func:`pass_context` or
        :func:`pass_environment`.
        """
        if __debug__:
            __traceback_hide__ = True  # noqa

        # Allow callable classes to take a context
        if (
            hasattr(__obj, "__call__")  # noqa: B004
            and _PassArg.from_obj(__obj.__call__) is not None
        ):
            __obj = __obj.__call__

        pass_arg = _PassArg.from_obj(__obj)

        if pass_arg is _PassArg.context:
            # the active context should have access to variables set in
            # loops and blocks without mutating the context itself
            if kwargs.get("_loop_vars"):
                __self = __self.derived(kwargs["_loop_vars"])
            if kwargs.get("_block_vars"):
                __self = __self.derived(kwargs["_block_vars"])
            args = (__self,) + args
        elif pass_arg is _PassArg.eval_context:
            args = (__self.eval_ctx,) + args
        elif pass_arg is _PassArg.environment:
            args = (__self.environment,) + args

        kwargs.pop("_block_vars", None)
        kwargs.pop("_loop_vars", None)

        try:
            return __obj(*args, **kwargs)
        except StopIteration:
            return __self.environment.undefined(
                "value was undefined because a callable raised a"
                " StopIteration exception"
            )

    def derived(self, locals: t.Optional[t.Dict[str, t.Any]] = None) -> "Context":
        """Internal helper function to create a derived context.  This is
        used in situations where the system needs a new context in the same
        template that is independent.
        """
        context = new_context(
            self.environment, self.name, {}, self.get_all(), True, None, locals
        )
        context.eval_ctx = self.eval_ctx
        context.blocks.update((k, list(v)) for k, v in self.blocks.items())
        return context

    keys = _dict_method_all(dict.keys)
    values = _dict_method_all(dict.values)
    items = _dict_method_all(dict.items)

    def __contains__(self, name: str) -> bool:
        return name in self.vars or name in self.parent

    def __getitem__(self, key: str) -> t.Any:
        """Look up a variable by name with ``[]`` syntax, or raise a
        ``KeyError`` if the key is not found.
        """
        item = self.resolve_or_missing(key)

        if item is missing:
            raise KeyError(key)

        return item

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.get_all()!r} of {self.name!r}>"


class BlockReference:
    """One block on a template reference."""

    def __init__(
        self,
        name: str,
        context: "Context",
        stack: t.List[t.Callable[["Context"], t.Iterator[str]]],
        depth: int,
    ) -> None:
        self.name = name
        self._context = context
        self._stack = stack
        self._depth = depth

    @property
    def super(self) -> t.Union["BlockReference", "Undefined"]:
        """Super the block."""
        if self._depth + 1 >= len(self._stack):
            return self._context.environment.undefined(
                f"there is no parent block called {self.name!r}.", name="super"
            )
        return BlockReference(self.name, self._context, self._stack, self._depth + 1)

    @internalcode
    async def _async_call(self) -> str:
        rv = self._context.environment.concat(  # type: ignore
            [x async for x in self._stack[self._depth](self._context)]  # type: ignore
        )

        if self._context.eval_ctx.autoescape:
            return Markup(rv)

        return rv

    @internalcode
    def __call__(self) -> str:
        if self._context.environment.is_async:
            return self._async_call()  # type: ignore

        rv = self._context.environment.concat(  # type: ignore
            self._stack[self._depth](self._context)
        )

        if self._context.eval_ctx.autoescape:
            return Markup(rv)

        return rv


class LoopContext:
    """A wrapper iterable for dynamic ``for`` loops, with information
    about the loop and iteration.
    """

    #: Current iteration of the loop, starting at 0.
    index0 = -1

    _length: t.Optional[int] = None
    _after: t.Any = missing
    _current: t.Any = missing
    _before: t.Any = missing
    _last_changed_value: t.Any = missing

    def __init__(
        self,
        iterable: t.Iterable[V],
        undefined: t.Type["Undefined"],
        recurse: t.Optional["LoopRenderFunc"] = None,
        depth0: int = 0,
    ) -> None:
        """
        :param iterable: Iterable to wrap.
        :param undefined: :class:`Undefined` class to use for next and
            previous items.
        :param recurse: The function to render the loop body when the
            loop is marked recursive.
        :param depth0: Incremented when looping recursively.
        """
        self._iterable = iterable
        self._iterator = self._to_iterator(iterable)
        self._undefined = undefined
        self._recurse = recurse
        #: How many levels deep a recursive loop currently is, starting at 0.
        self.depth0 = depth0

    @staticmethod
    def _to_iterator(iterable: t.Iterable[V]) -> t.Iterator[V]:
        return iter(iterable)

    @property
    def length(self) -> int:
        """Length of the iterable.

        If the iterable is a generator or otherwise does not have a
        size, it is eagerly evaluated to get a size.
        """
        if self._length is not None:
            return self._length

        try:
            self._length = len(self._iterable)  # type: ignore
        except TypeError:
            iterable = list(self._iterator)
            self._iterator = self._to_iterator(iterable)
            self._length = len(iterable) + self.index + (self._after is not missing)

        return self._length

    def __len__(self) -> int:
        return self.length

    @property
    def depth(self) -> int:
        """How many levels deep a recursive loop currently is, starting at 1."""
        return self.depth0 + 1

    @property
    def index(self) -> int:
        """Current iteration of the loop, starting at 1."""
        return self.index0 + 1

    @property
    def revindex0(self) -> int:
        """Number of iterations from the end of the loop, ending at 0.

        Requires calculating :attr:`length`.
        """
        return self.length - self.index

    @property
    def revindex(self) -> int:
        """Number of iterations from the end of the loop, ending at 1.

        Requires calculating :attr:`length`.
        """
        return self.length - self.index0

    @property
    def first(self) -> bool:
        """Whether this is the first iteration of the loop."""
        return self.index0 == 0

    def _peek_next(self) -> t.Any:
        """Return the next element in the iterable, or :data:`missing`
        if the iterable is exhausted. Only peeks one item ahead, caching
        the result in :attr:`_last` for use in subsequent checks. The
        cache is reset when :meth:`__next__` is called.
        """
        if self._after is not missing:
            return self._after

        self._after = next(self._iterator, missing)
        return self._after

    @property
    def last(self) -> bool:
        """Whether this is the last iteration of the loop.

        Causes the iterable to advance early. See
        :func:`itertools.groupby` for issues this can cause.
        The :func:`groupby` filter avoids that issue.
        """
        return self._peek_next() is missing

    @property
    def previtem(self) -> t.Union[t.Any, "Undefined"]:
        """The item in the previous iteration. Undefined during the
        first iteration.
        """
        if self.first:
            return self._undefined("there is no previous item")

        return self._before

    @property
    def nextitem(self) -> t.Union[t.Any, "Undefined"]:
        """The item in the next iteration. Undefined during the last
        iteration.

        Causes the iterable to advance early. See
        :func:`itertools.groupby` for issues this can cause.
        The :func:`jinja-filters.groupby` filter avoids that issue.
        """
        rv = self._peek_next()

        if rv is missing:
            return self._undefined("there is no next item")

        return rv

    def cycle(self, *args: V) -> V:
        """Return a value from the given args, cycling through based on
        the current :attr:`index0`.

        :param args: One or more values to cycle through.
        """
        if not args:
            raise TypeError("no items for cycling given")

        return args[self.index0 % len(args)]

    def changed(self, *value: t.Any) -> bool:
        """Return ``True`` if previously called with a different value
        (including when called for the first time).

        :param value: One or more values to compare to the last call.
        """
        if self._last_changed_value != value:
            self._last_changed_value = value
            return True

        return False

    def __iter__(self) -> "LoopContext":
        return self

    def __next__(self) -> t.Tuple[t.Any, "LoopContext"]:
        if self._after is not missing:
            rv = self._after
            self._after = missing
        else:
            rv = next(self._iterator)

        self.index0 += 1
        self._before = self._current
        self._current = rv
        return rv, self

    @internalcode
    def __call__(self, iterable: t.Iterable[V]) -> str:
        """When iterating over nested data, render the body of the loop
        recursively with the given inner iterable data.

        The loop must have the ``recursive`` marker for this to work.
        """
        if self._recurse is None:
            raise TypeError(
                "The loop must have the 'recursive' marker to be called recursively."
            )

        return self._recurse(iterable, self._recurse, depth=self.depth)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.index}/{self.length}>"


class AsyncLoopContext(LoopContext):
    _iterator: t.AsyncIterator[t.Any]  # type: ignore

    @staticmethod
    def _to_iterator(  # type: ignore
        iterable: t.Union[t.Iterable[V], t.AsyncIterable[V]],
    ) -> t.AsyncIterator[V]:
        return auto_aiter(iterable)

    @property
    async def length(self) -> int:  # type: ignore
        if self._length is not None:
            return self._length

        try:
            self._length = len(self._iterable)  # type: ignore
        except TypeError:
            iterable = [x async for x in self._iterator]
            self._iterator = self._to_iterator(iterable)
            self._length = len(iterable) + self.index + (self._after is not missing)

        return self._length

    @property
    async def revindex0(self) -> int:  # type: ignore
        return await self.length - self.index

    @property
    async def revindex(self) -> int:  # type: ignore
        return await self.length - self.index0

    async def _peek_next(self) -> t.Any:
        if self._after is not missing:
            return self._after

        try:
            self._after = await self._iterator.__anext__()
        except StopAsyncIteration:
            self._after = missing

        return self._after

    @property
    async def last(self) -> bool:  # type: ignore
        return await self._peek_next() is missing

    @property
    async def nextitem(self) -> t.Union[t.Any, "Undefined"]:
        rv = await self._peek_next()

        if rv is missing:
            return self._undefined("there is no next item")

        return rv

    def __aiter__(self) -> "AsyncLoopContext":
        return self

    async def __anext__(self) -> t.Tuple[t.Any, "AsyncLoopContext"]:
        if self._after is not missing:
            rv = self._after
            self._after = missing
        else:
            rv = await self._iterator.__anext__()

        self.index0 += 1
        self._before = self._current
        self._current = rv
        return rv, self


class Macro:
    """Wraps a macro function."""

    def __init__(
        self,
        environment: "Environment",
        func: t.Callable[..., str],
        name: str,
        arguments: t.List[str],
        catch_kwargs: bool,
        catch_varargs: bool,
        caller: bool,
        default_autoescape: t.Optional[bool] = None,
    ):
        self._environment = environment
        self._func = func
        self._argument_count = len(arguments)
        self.name = name
        self.arguments = arguments
        self.catch_kwargs = catch_kwargs
        self.catch_varargs = catch_varargs
        self.caller = caller
        self.explicit_caller = "caller" in arguments

        if default_autoescape is None:
            if callable(environment.autoescape):
                default_autoescape = environment.autoescape(None)
            else:
                default_autoescape = environment.autoescape

        self._default_autoescape = default_autoescape

    @internalcode
    @pass_eval_context
    def __call__(self, *args: t.Any, **kwargs: t.Any) -> str:
        # This requires a bit of explanation,  In the past we used to
        # decide largely based on compile-time information if a macro is
        # safe or unsafe.  While there was a volatile mode it was largely
        # unused for deciding on escaping.  This turns out to be
        # problematic for macros because whether a macro is safe depends not
        # on the escape mode when it was defined, but rather when it was used.
        #
        # Because however we export macros from the module system and
        # there are historic callers that do not pass an eval context (and
        # will continue to not pass one), we need to perform an instance
        # check here.
        #
        # This is considered safe because an eval context is not a valid
        # argument to callables otherwise anyway.  Worst case here is
        # that if no eval context is passed we fall back to the compile
        # time autoescape flag.
        if args and isinstance(args[0], EvalContext):
            autoescape = args[0].autoescape
            args = args[1:]
        else:
            autoescape = self._default_autoescape

        # try to consume the positional arguments
        arguments = list(args[: self._argument_count])
        off = len(arguments)

        # For information why this is necessary refer to the handling
        # of caller in the `macro_body` handler in the compiler.
        found_caller = False

        # if the number of arguments consumed is not the number of
        # arguments expected we start filling in keyword arguments
        # and defaults.
        if off != self._argument_count:
            for name in self.arguments[len(arguments) :]:
                try:
                    value = kwargs.pop(name)
                except KeyError:
                    value = missing
                if name == "caller":
                    found_caller = True
                arguments.append(value)
        else:
            found_caller = self.explicit_caller

        # it's important that the order of these arguments does not change
        # if not also changed in the compiler's `function_scoping` method.
        # the order is caller, keyword arguments, positional arguments!
        if self.caller and not found_caller:
            caller = kwargs.pop("caller", None)
            if caller is None:
                caller = self._environment.undefined("No caller defined", name="caller")
            arguments.append(caller)

        if self.catch_kwargs:
            arguments.append(kwargs)
        elif kwargs:
            if "caller" in kwargs:
                raise TypeError(
                    f"macro {self.name!r} was invoked with two values for the special"
                    " caller argument. This is most likely a bug."
                )
            raise TypeError(
                f"macro {self.name!r} takes no keyword argument {next(iter(kwargs))!r}"
            )
        if self.catch_varargs:
            arguments.append(args[self._argument_count :])
        elif len(args) > self._argument_count:
            raise TypeError(
                f"macro {self.name!r} takes not more than"
                f" {len(self.arguments)} argument(s)"
            )

        return self._invoke(arguments, autoescape)

    async def _async_invoke(self, arguments: t.List[t.Any], autoescape: bool) -> str:
        rv = await self._func(*arguments)  # type: ignore

        if autoescape:
            return Markup(rv)

        return rv  # type: ignore

    def _invoke(self, arguments: t.List[t.Any], autoescape: bool) -> str:
        if self._environment.is_async:
            return self._async_invoke(arguments, autoescape)  # type: ignore

        rv = self._func(*arguments)

        if autoescape:
            rv = Markup(rv)

        return rv

    def __repr__(self) -> str:
        name = "anonymous" if self.name is None else repr(self.name)
        return f"<{type(self).__name__} {name}>"


class Undefined:
    """The default undefined type. This can be printed, iterated, and treated as
    a boolean. Any other operation will raise an :exc:`UndefinedError`.

    >>> foo = Undefined(name='foo')
    >>> str(foo)
    ''
    >>> not foo
    True
    >>> foo + 42
    Traceback (most recent call last):
      ...
    jinja2.exceptions.UndefinedError: 'foo' is undefined
    """

    __slots__ = (
        "_undefined_hint",
        "_undefined_obj",
        "_undefined_name",
        "_undefined_exception",
    )

    def __init__(
        self,
        hint: t.Optional[str] = None,
        obj: t.Any = missing,
        name: t.Optional[str] = None,
        exc: t.Type[TemplateRuntimeError] = UndefinedError,
    ) -> None:
        self._undefined_hint = hint
        self._undefined_obj = obj
        self._undefined_name = name
        self._undefined_exception = exc

    @property
    def _undefined_message(self) -> str:
        """Build a message about the undefined value based on how it was
        accessed.
        """
        if self._undefined_hint:
            return self._undefined_hint

        if self._undefined_obj is missing:
            return f"{self._undefined_name!r} is undefined"

        if not isinstance(self._undefined_name, str):
            return (
                f"{object_type_repr(self._undefined_obj)} has no"
                f" element {self._undefined_name!r}"
            )

        return (
            f"{object_type_repr(self._undefined_obj)!r} has no"
            f" attribute {self._undefined_name!r}"
        )

    @internalcode
    def _fail_with_undefined_error(
        self, *args: t.Any, **kwargs: t.Any
    ) -> "te.NoReturn":
        """Raise an :exc:`UndefinedError` when operations are performed
        on the undefined value.
        """
        raise self._undefined_exception(self._undefined_message)

    @internalcode
    def __getattr__(self, name: str) -> t.Any:
        # Raise AttributeError on requests for names that appear to be unimplemented
        # dunder methods to keep Python's internal protocol probing behaviors working
        # properly in cases where another exception type could cause unexpected or
        # difficult-to-diagnose failures.
        if name[:2] == "__" and name[-2:] == "__":
            raise AttributeError(name)

        return self._fail_with_undefined_error()

    __add__ = __radd__ = __sub__ = __rsub__ = _fail_with_undefined_error
    __mul__ = __rmul__ = __div__ = __rdiv__ = _fail_with_undefined_error
    __truediv__ = __rtruediv__ = _fail_with_undefined_error
    __floordiv__ = __rfloordiv__ = _fail_with_undefined_error
    __mod__ = __rmod__ = _fail_with_undefined_error
    __pos__ = __neg__ = _fail_with_undefined_error
    __call__ = __getitem__ = _fail_with_undefined_error
    __lt__ = __le__ = __gt__ = __ge__ = _fail_with_undefined_error
    __int__ = __float__ = __complex__ = _fail_with_undefined_error
    __pow__ = __rpow__ = _fail_with_undefined_error

    def __eq__(self, other: t.Any) -> bool:
        return type(self) is type(other)

    def __ne__(self, other: t.Any) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return id(type(self))

    def __str__(self) -> str:
        return ""

    def __len__(self) -> int:
        return 0

    def __iter__(self) -> t.Iterator[t.Any]:
        yield from ()

    async def __aiter__(self) -> t.AsyncIterator[t.Any]:
        for _ in ():
            yield

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "Undefined"


def make_logging_undefined(
    logger: t.Optional["logging.Logger"] = None, base: t.Type[Undefined] = Undefined
) -> t.Type[Undefined]:
    """Given a logger object this returns a new undefined class that will
    log certain failures.  It will log iterations and printing.  If no
    logger is given a default logger is created.

    Example::

        logger = logging.getLogger(__name__)
        LoggingUndefined = make_logging_undefined(
            logger=logger,
            base=Undefined
        )

    .. versionadded:: 2.8

    :param logger: the logger to use.  If not provided, a default logger
                   is created.
    :param base: the base class to add logging functionality to.  This
                 defaults to :class:`Undefined`.
    """
    if logger is None:
        import logging

        logger = logging.getLogger(__name__)
        logger.addHandler(logging.StreamHandler(sys.stderr))

    def _log_message(undef: Undefined) -> None:
        logger.warning("Template variable warning: %s", undef._undefined_message)

    class LoggingUndefined(base):  # type: ignore
        __slots__ = ()

        def _fail_with_undefined_error(  # type: ignore
            self, *args: t.Any, **kwargs: t.Any
        ) -> "te.NoReturn":
            try:
                super()._fail_with_undefined_error(*args, **kwargs)
            except self._undefined_exception as e:
                logger.error("Template variable error: %s", e)  # type: ignore
                raise e

        def __str__(self) -> str:
            _log_message(self)
            return super().__str__()  # type: ignore

        def __iter__(self) -> t.Iterator[t.Any]:
            _log_message(self)
            return super().__iter__()  # type: ignore

        def __bool__(self) -> bool:
            _log_message(self)
            return super().__bool__()  # type: ignore

    return LoggingUndefined


class ChainableUndefined(Undefined):
    """An undefined that is chainable, where both ``__getattr__`` and
    ``__getitem__`` return itself rather than raising an
    :exc:`UndefinedError`.

    >>> foo = ChainableUndefined(name='foo')
    >>> str(foo.bar['baz'])
    ''
    >>> foo.bar['baz'] + 42
    Traceback (most recent call last):
      ...
    jinja2.exceptions.UndefinedError: 'foo' is undefined

    .. versionadded:: 2.11.0
    """

    __slots__ = ()

    def __html__(self) -> str:
        return str(self)

    def __getattr__(self, name: str) -> "ChainableUndefined":
        # Raise AttributeError on requests for names that appear to be unimplemented
        # dunder methods to avoid confusing Python with truthy non-method objects that
        # do not implement the protocol being probed for. e.g., copy.copy(Undefined())
        # fails spectacularly if getattr(Undefined(), '__setstate__') returns an
        # Undefined object instead of raising AttributeError to signal that it does not
        # support that style of object initialization.
        if name[:2] == "__" and name[-2:] == "__":
            raise AttributeError(name)

        return self

    def __getitem__(self, _name: str) -> "ChainableUndefined":  # type: ignore[override]
        return self


class DebugUndefined(Undefined):
    """An undefined that returns the debug info when printed.

    >>> foo = DebugUndefined(name='foo')
    >>> str(foo)
    '{{ foo }}'
    >>> not foo
    True
    >>> foo + 42
    Traceback (most recent call last):
      ...
    jinja2.exceptions.UndefinedError: 'foo' is undefined
    """

    __slots__ = ()

    def __str__(self) -> str:
        if self._undefined_hint:
            message = f"undefined value printed: {self._undefined_hint}"

        elif self._undefined_obj is missing:
            message = self._undefined_name  # type: ignore

        else:
            message = (
                f"no such element: {object_type_repr(self._undefined_obj)}"
                f"[{self._undefined_name!r}]"
            )

        return f"{{{{ {message} }}}}"


class StrictUndefined(Undefined):
    """An undefined that barks on print and iteration as well as boolean
    tests and all kinds of comparisons.  In other words: you can do nothing
    with it except checking if it's defined using the `defined` test.

    >>> foo = StrictUndefined(name='foo')
    >>> str(foo)
    Traceback (most recent call last):
      ...
    jinja2.exceptions.UndefinedError: 'foo' is undefined
    >>> not foo
    Traceback (most recent call last):
      ...
    jinja2.exceptions.UndefinedError: 'foo' is undefined
    >>> foo + 42
    Traceback (most recent call last):
      ...
    jinja2.exceptions.UndefinedError: 'foo' is undefined
    """

    __slots__ = ()
    __iter__ = __str__ = __len__ = Undefined._fail_with_undefined_error
    __eq__ = __ne__ = __bool__ = __hash__ = Undefined._fail_with_undefined_error
    __contains__ = Undefined._fail_with_undefined_error