
# === NexusCore/openenv\Lib\site-packages\six.py ===
# Copyright (c) 2010-2024 Benjamin Peterson
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
__version__ = "1.17.0"


# Useful for very coarse version differentiation.
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3
PY34 = sys.version_info[0:2] >= (3, 4)

if PY3:
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes

    MAXSIZE = sys.maxsize
else:
    string_types = basestring,
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
    MovedAttribute("filterfalse", "itertools", "itertools", "ifilterfalse", "filterfalse"),
    MovedAttribute("input", "__builtin__", "builtins", "raw_input", "input"),
    MovedAttribute("intern", "__builtin__", "sys"),
    MovedAttribute("map", "itertools", "builtins", "imap", "map"),
    MovedAttribute("getcwd", "os", "os", "getcwdu", "getcwd"),
    MovedAttribute("getcwdb", "os", "os", "getcwd", "getcwdb"),
    MovedAttribute("getoutput", "commands", "subprocess"),
    MovedAttribute("range", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("reload_module", "__builtin__", "importlib" if PY34 else "imp", "reload"),
    MovedAttribute("reduce", "__builtin__", "functools"),
    MovedAttribute("shlex_quote", "pipes", "shlex", "quote"),
    MovedAttribute("StringIO", "StringIO", "io"),
    MovedAttribute("UserDict", "UserDict", "collections", "IterableUserDict", "UserDict"),
    MovedAttribute("UserList", "UserList", "collections"),
    MovedAttribute("UserString", "UserString", "collections"),
    MovedAttribute("xrange", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("zip", "itertools", "builtins", "izip", "zip"),
    MovedAttribute("zip_longest", "itertools", "itertools", "izip_longest", "zip_longest"),
    MovedModule("builtins", "__builtin__"),
    MovedModule("configparser", "ConfigParser"),
    MovedModule("collections_abc", "collections", "collections.abc" if sys.version_info >= (3, 3) else "collections"),
    MovedModule("copyreg", "copy_reg"),
    MovedModule("dbm_gnu", "gdbm", "dbm.gnu"),
    MovedModule("dbm_ndbm", "dbm", "dbm.ndbm"),
    MovedModule("_dummy_thread", "dummy_thread", "_dummy_thread" if sys.version_info < (3, 9) else "_thread"),
    MovedModule("http_cookiejar", "cookielib", "http.cookiejar"),
    MovedModule("http_cookies", "Cookie", "http.cookies"),
    MovedModule("html_entities", "htmlentitydefs", "html.entities"),
    MovedModule("html_parser", "HTMLParser", "html.parser"),
    MovedModule("http_client", "httplib", "http.client"),
    MovedModule("email_mime_base", "email.MIMEBase", "email.mime.base"),
    MovedModule("email_mime_image", "email.MIMEImage", "email.mime.image"),
    MovedModule("email_mime_multipart", "email.MIMEMultipart", "email.mime.multipart"),
    MovedModule("email_mime_nonmultipart", "email.MIMENonMultipart", "email.mime.nonmultipart"),
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
    MovedModule("tkinter_colorchooser", "tkColorChooser",
                "tkinter.colorchooser"),
    MovedModule("tkinter_commondialog", "tkCommonDialog",
                "tkinter.commondialog"),
    MovedModule("tkinter_tkfiledialog", "tkFileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_font", "tkFont", "tkinter.font"),
    MovedModule("tkinter_messagebox", "tkMessageBox", "tkinter.messagebox"),
    MovedModule("tkinter_tksimpledialog", "tkSimpleDialog",
                "tkinter.simpledialog"),
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
    MovedAttribute("unquote_to_bytes", "urllib", "urllib.parse", "unquote", "unquote_to_bytes"),
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

_importer._add_module(Module_six_moves_urllib_parse(__name__ + ".moves.urllib_parse"),
                      "moves.urllib_parse", "moves.urllib.parse")


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

_importer._add_module(Module_six_moves_urllib_error(__name__ + ".moves.urllib.error"),
                      "moves.urllib_error", "moves.urllib.error")


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
    MovedAttribute("proxy_bypass", "urllib", "urllib.request"),
    MovedAttribute("parse_http_list", "urllib2", "urllib.request"),
    MovedAttribute("parse_keqv_list", "urllib2", "urllib.request"),
]
if sys.version_info[:2] < (3, 14):
    _urllib_request_moved_attributes.extend(
        [
            MovedAttribute("URLopener", "urllib", "urllib.request"),
            MovedAttribute("FancyURLopener", "urllib", "urllib.request"),
        ]
    )
for attr in _urllib_request_moved_attributes:
    setattr(Module_six_moves_urllib_request, attr.name, attr)
del attr

Module_six_moves_urllib_request._moved_attributes = _urllib_request_moved_attributes

_importer._add_module(Module_six_moves_urllib_request(__name__ + ".moves.urllib.request"),
                      "moves.urllib_request", "moves.urllib.request")


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

_importer._add_module(Module_six_moves_urllib_response(__name__ + ".moves.urllib.response"),
                      "moves.urllib_response", "moves.urllib.response")


class Module_six_moves_urllib_robotparser(_LazyModule):

    """Lazy loading of moved objects in six.moves.urllib_robotparser"""


_urllib_robotparser_moved_attributes = [
    MovedAttribute("RobotFileParser", "robotparser", "urllib.robotparser"),
]
for attr in _urllib_robotparser_moved_attributes:
    setattr(Module_six_moves_urllib_robotparser, attr.name, attr)
del attr

Module_six_moves_urllib_robotparser._moved_attributes = _urllib_robotparser_moved_attributes

_importer._add_module(Module_six_moves_urllib_robotparser(__name__ + ".moves.urllib.robotparser"),
                      "moves.urllib_robotparser", "moves.urllib.robotparser")


class Module_six_moves_urllib(types.ModuleType):

    """Create a six.moves.urllib namespace that resembles the Python 3 namespace"""
    __path__ = []  # mark as package
    parse = _importer._get_module("moves.urllib_parse")
    error = _importer._get_module("moves.urllib_error")
    request = _importer._get_module("moves.urllib_request")
    response = _importer._get_module("moves.urllib_response")
    robotparser = _importer._get_module("moves.urllib_robotparser")

    def __dir__(self):
        return ['parse', 'error', 'request', 'response', 'robotparser']

_importer._add_module(Module_six_moves_urllib(__name__ + ".moves.urllib"),
                      "moves.urllib")


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
_add_doc(get_unbound_function,
         """Get the function out of a possibly unbound function""")


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
_add_doc(iteritems,
         "Return an iterator over the (key, value) pairs of a dictionary.")
_add_doc(iterlists,
         "Return an iterator over the (key, [values]) pairs of a dictionary.")


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
        return unicode(s.replace(r'\\', r'\\\\'), "unicode_escape")
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
        exec("""exec _code_ in _globs_, _locs_""")

    exec_("""def reraise(tp, value, tb=None):
    try:
        raise tp, value, tb
    finally:
        tb = None
""")


if sys.version_info[:2] > (3,):
    exec_("""def raise_from(value, from_value):
    try:
        raise value from from_value
    finally:
        value = None
""")
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
            if (isinstance(fp, file) and
                    isinstance(data, unicode) and
                    fp.encoding is not None):
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
    def _update_wrapper(wrapper, wrapped,
                        assigned=functools.WRAPPER_ASSIGNMENTS,
                        updated=functools.WRAPPER_UPDATES):
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

    def wraps(wrapped, assigned=functools.WRAPPER_ASSIGNMENTS,
              updated=functools.WRAPPER_UPDATES):
        return functools.partial(_update_wrapper, wrapped=wrapped,
                                 assigned=assigned, updated=updated)
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
                    d['__orig_bases__'] = bases
            else:
                resolved_bases = bases
            return meta(name, resolved_bases, d)

        @classmethod
        def __prepare__(cls, name, this_bases):
            return meta.__prepare__(name, bases)
    return type.__new__(metaclass, 'temporary_class', (), {})


def add_metaclass(metaclass):
    """Class decorator for creating a class with a metaclass."""
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        slots = orig_vars.get('__slots__')
        if slots is not None:
            if isinstance(slots, str):
                slots = [slots]
            for slots_var in slots:
                orig_vars.pop(slots_var)
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        if hasattr(cls, '__qualname__'):
            orig_vars['__qualname__'] = cls.__qualname__
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper


def ensure_binary(s, encoding='utf-8', errors='strict'):
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


def ensure_str(s, encoding='utf-8', errors='strict'):
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


def ensure_text(s, encoding='utf-8', errors='strict'):
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
        if '__str__' not in klass.__dict__:
            raise ValueError("@python_2_unicode_compatible cannot be applied "
                             "to %s because it doesn't define __str__()." %
                             klass.__name__)
        klass.__unicode__ = klass.__str__
        klass.__str__ = lambda self: self.__unicode__().encode('utf-8')
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
        if (type(importer).__name__ == "_SixMetaPathImporter" and
                importer.name == __name__):
            del sys.meta_path[i]
            break
    del i, importer
# Finally, add the importer to the meta path import hook.
sys.meta_path.append(_importer)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\_tsql_builtins.py ===
"""
    pygments.lexers._tsql_builtins
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    These are manually translated lists from https://msdn.microsoft.com.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

# See https://msdn.microsoft.com/en-us/library/ms174986.aspx.
OPERATORS = (
    '!<',
    '!=',
    '!>',
    '<',
    '<=',
    '<>',
    '=',
    '>',
    '>=',
    '+',
    '+=',
    '-',
    '-=',
    '*',
    '*=',
    '/',
    '/=',
    '%',
    '%=',
    '&',
    '&=',
    '|',
    '|=',
    '^',
    '^=',
    '~',
    '::',
)

OPERATOR_WORDS = (
    'all',
    'and',
    'any',
    'between',
    'except',
    'exists',
    'in',
    'intersect',
    'like',
    'not',
    'or',
    'some',
    'union',
)

_KEYWORDS_SERVER = (
    'add',
    'all',
    'alter',
    'and',
    'any',
    'as',
    'asc',
    'authorization',
    'backup',
    'begin',
    'between',
    'break',
    'browse',
    'bulk',
    'by',
    'cascade',
    'case',
    'catch',
    'check',
    'checkpoint',
    'close',
    'clustered',
    'coalesce',
    'collate',
    'column',
    'commit',
    'compute',
    'constraint',
    'contains',
    'containstable',
    'continue',
    'convert',
    'create',
    'cross',
    'current',
    'current_date',
    'current_time',
    'current_timestamp',
    'current_user',
    'cursor',
    'database',
    'dbcc',
    'deallocate',
    'declare',
    'default',
    'delete',
    'deny',
    'desc',
    'disk',
    'distinct',
    'distributed',
    'double',
    'drop',
    'dump',
    'else',
    'end',
    'errlvl',
    'escape',
    'except',
    'exec',
    'execute',
    'exists',
    'exit',
    'external',
    'fetch',
    'file',
    'fillfactor',
    'for',
    'foreign',
    'freetext',
    'freetexttable',
    'from',
    'full',
    'function',
    'goto',
    'grant',
    'group',
    'having',
    'holdlock',
    'identity',
    'identity_insert',
    'identitycol',
    'if',
    'in',
    'index',
    'inner',
    'insert',
    'intersect',
    'into',
    'is',
    'join',
    'key',
    'kill',
    'left',
    'like',
    'lineno',
    'load',
    'merge',
    'national',
    'nocheck',
    'nonclustered',
    'not',
    'null',
    'nullif',
    'of',
    'off',
    'offsets',
    'on',
    'open',
    'opendatasource',
    'openquery',
    'openrowset',
    'openxml',
    'option',
    'or',
    'order',
    'outer',
    'over',
    'percent',
    'pivot',
    'plan',
    'precision',
    'primary',
    'print',
    'proc',
    'procedure',
    'public',
    'raiserror',
    'read',
    'readtext',
    'reconfigure',
    'references',
    'replication',
    'restore',
    'restrict',
    'return',
    'revert',
    'revoke',
    'right',
    'rollback',
    'rowcount',
    'rowguidcol',
    'rule',
    'save',
    'schema',
    'securityaudit',
    'select',
    'semantickeyphrasetable',
    'semanticsimilaritydetailstable',
    'semanticsimilaritytable',
    'session_user',
    'set',
    'setuser',
    'shutdown',
    'some',
    'statistics',
    'system_user',
    'table',
    'tablesample',
    'textsize',
    'then',
    'throw',
    'to',
    'top',
    'tran',
    'transaction',
    'trigger',
    'truncate',
    'try',
    'try_convert',
    'tsequal',
    'union',
    'unique',
    'unpivot',
    'update',
    'updatetext',
    'use',
    'user',
    'values',
    'varying',
    'view',
    'waitfor',
    'when',
    'where',
    'while',
    'with',
    'within',
    'writetext',
)

_KEYWORDS_FUTURE = (
    'absolute',
    'action',
    'admin',
    'after',
    'aggregate',
    'alias',
    'allocate',
    'are',
    'array',
    'asensitive',
    'assertion',
    'asymmetric',
    'at',
    'atomic',
    'before',
    'binary',
    'bit',
    'blob',
    'boolean',
    'both',
    'breadth',
    'call',
    'called',
    'cardinality',
    'cascaded',
    'cast',
    'catalog',
    'char',
    'character',
    'class',
    'clob',
    'collation',
    'collect',
    'completion',
    'condition',
    'connect',
    'connection',
    'constraints',
    'constructor',
    'corr',
    'corresponding',
    'covar_pop',
    'covar_samp',
    'cube',
    'cume_dist',
    'current_catalog',
    'current_default_transform_group',
    'current_path',
    'current_role',
    'current_schema',
    'current_transform_group_for_type',
    'cycle',
    'data',
    'date',
    'day',
    'dec',
    'decimal',
    'deferrable',
    'deferred',
    'depth',
    'deref',
    'describe',
    'descriptor',
    'destroy',
    'destructor',
    'deterministic',
    'diagnostics',
    'dictionary',
    'disconnect',
    'domain',
    'dynamic',
    'each',
    'element',
    'end-exec',
    'equals',
    'every',
    'exception',
    'false',
    'filter',
    'first',
    'float',
    'found',
    'free',
    'fulltexttable',
    'fusion',
    'general',
    'get',
    'global',
    'go',
    'grouping',
    'hold',
    'host',
    'hour',
    'ignore',
    'immediate',
    'indicator',
    'initialize',
    'initially',
    'inout',
    'input',
    'int',
    'integer',
    'intersection',
    'interval',
    'isolation',
    'iterate',
    'language',
    'large',
    'last',
    'lateral',
    'leading',
    'less',
    'level',
    'like_regex',
    'limit',
    'ln',
    'local',
    'localtime',
    'localtimestamp',
    'locator',
    'map',
    'match',
    'member',
    'method',
    'minute',
    'mod',
    'modifies',
    'modify',
    'module',
    'month',
    'multiset',
    'names',
    'natural',
    'nchar',
    'nclob',
    'new',
    'next',
    'no',
    'none',
    'normalize',
    'numeric',
    'object',
    'occurrences_regex',
    'old',
    'only',
    'operation',
    'ordinality',
    'out',
    'output',
    'overlay',
    'pad',
    'parameter',
    'parameters',
    'partial',
    'partition',
    'path',
    'percent_rank',
    'percentile_cont',
    'percentile_disc',
    'position_regex',
    'postfix',
    'prefix',
    'preorder',
    'prepare',
    'preserve',
    'prior',
    'privileges',
    'range',
    'reads',
    'real',
    'recursive',
    'ref',
    'referencing',
    'regr_avgx',
    'regr_avgy',
    'regr_count',
    'regr_intercept',
    'regr_r2',
    'regr_slope',
    'regr_sxx',
    'regr_sxy',
    'regr_syy',
    'relative',
    'release',
    'result',
    'returns',
    'role',
    'rollup',
    'routine',
    'row',
    'rows',
    'savepoint',
    'scope',
    'scroll',
    'search',
    'second',
    'section',
    'sensitive',
    'sequence',
    'session',
    'sets',
    'similar',
    'size',
    'smallint',
    'space',
    'specific',
    'specifictype',
    'sql',
    'sqlexception',
    'sqlstate',
    'sqlwarning',
    'start',
    'state',
    'statement',
    'static',
    'stddev_pop',
    'stddev_samp',
    'structure',
    'submultiset',
    'substring_regex',
    'symmetric',
    'system',
    'temporary',
    'terminate',
    'than',
    'time',
    'timestamp',
    'timezone_hour',
    'timezone_minute',
    'trailing',
    'translate_regex',
    'translation',
    'treat',
    'true',
    'uescape',
    'under',
    'unknown',
    'unnest',
    'usage',
    'using',
    'value',
    'var_pop',
    'var_samp',
    'varchar',
    'variable',
    'whenever',
    'width_bucket',
    'window',
    'within',
    'without',
    'work',
    'write',
    'xmlagg',
    'xmlattributes',
    'xmlbinary',
    'xmlcast',
    'xmlcomment',
    'xmlconcat',
    'xmldocument',
    'xmlelement',
    'xmlexists',
    'xmlforest',
    'xmliterate',
    'xmlnamespaces',
    'xmlparse',
    'xmlpi',
    'xmlquery',
    'xmlserialize',
    'xmltable',
    'xmltext',
    'xmlvalidate',
    'year',
    'zone',
)

_KEYWORDS_ODBC = (
    'absolute',
    'action',
    'ada',
    'add',
    'all',
    'allocate',
    'alter',
    'and',
    'any',
    'are',
    'as',
    'asc',
    'assertion',
    'at',
    'authorization',
    'avg',
    'begin',
    'between',
    'bit',
    'bit_length',
    'both',
    'by',
    'cascade',
    'cascaded',
    'case',
    'cast',
    'catalog',
    'char',
    'char_length',
    'character',
    'character_length',
    'check',
    'close',
    'coalesce',
    'collate',
    'collation',
    'column',
    'commit',
    'connect',
    'connection',
    'constraint',
    'constraints',
    'continue',
    'convert',
    'corresponding',
    'count',
    'create',
    'cross',
    'current',
    'current_date',
    'current_time',
    'current_timestamp',
    'current_user',
    'cursor',
    'date',
    'day',
    'deallocate',
    'dec',
    'decimal',
    'declare',
    'default',
    'deferrable',
    'deferred',
    'delete',
    'desc',
    'describe',
    'descriptor',
    'diagnostics',
    'disconnect',
    'distinct',
    'domain',
    'double',
    'drop',
    'else',
    'end',
    'end-exec',
    'escape',
    'except',
    'exception',
    'exec',
    'execute',
    'exists',
    'external',
    'extract',
    'false',
    'fetch',
    'first',
    'float',
    'for',
    'foreign',
    'fortran',
    'found',
    'from',
    'full',
    'get',
    'global',
    'go',
    'goto',
    'grant',
    'group',
    'having',
    'hour',
    'identity',
    'immediate',
    'in',
    'include',
    'index',
    'indicator',
    'initially',
    'inner',
    'input',
    'insensitive',
    'insert',
    'int',
    'integer',
    'intersect',
    'interval',
    'into',
    'is',
    'isolation',
    'join',
    'key',
    'language',
    'last',
    'leading',
    'left',
    'level',
    'like',
    'local',
    'lower',
    'match',
    'max',
    'min',
    'minute',
    'module',
    'month',
    'names',
    'national',
    'natural',
    'nchar',
    'next',
    'no',
    'none',
    'not',
    'null',
    'nullif',
    'numeric',
    'octet_length',
    'of',
    'on',
    'only',
    'open',
    'option',
    'or',
    'order',
    'outer',
    'output',
    'overlaps',
    'pad',
    'partial',
    'pascal',
    'position',
    'precision',
    'prepare',
    'preserve',
    'primary',
    'prior',
    'privileges',
    'procedure',
    'public',
    'read',
    'real',
    'references',
    'relative',
    'restrict',
    'revoke',
    'right',
    'rollback',
    'rows',
    'schema',
    'scroll',
    'second',
    'section',
    'select',
    'session',
    'session_user',
    'set',
    'size',
    'smallint',
    'some',
    'space',
    'sql',
    'sqlca',
    'sqlcode',
    'sqlerror',
    'sqlstate',
    'sqlwarning',
    'substring',
    'sum',
    'system_user',
    'table',
    'temporary',
    'then',
    'time',
    'timestamp',
    'timezone_hour',
    'timezone_minute',
    'to',
    'trailing',
    'transaction',
    'translate',
    'translation',
    'trim',
    'true',
    'union',
    'unique',
    'unknown',
    'update',
    'upper',
    'usage',
    'user',
    'using',
    'value',
    'values',
    'varchar',
    'varying',
    'view',
    'when',
    'whenever',
    'where',
    'with',
    'work',
    'write',
    'year',
    'zone',
)

# See https://msdn.microsoft.com/en-us/library/ms189822.aspx.
KEYWORDS = sorted(set(_KEYWORDS_FUTURE + _KEYWORDS_ODBC + _KEYWORDS_SERVER))

# See https://msdn.microsoft.com/en-us/library/ms187752.aspx.
TYPES = (
    'bigint',
    'binary',
    'bit',
    'char',
    'cursor',
    'date',
    'datetime',
    'datetime2',
    'datetimeoffset',
    'decimal',
    'float',
    'hierarchyid',
    'image',
    'int',
    'money',
    'nchar',
    'ntext',
    'numeric',
    'nvarchar',
    'real',
    'smalldatetime',
    'smallint',
    'smallmoney',
    'sql_variant',
    'table',
    'text',
    'time',
    'timestamp',
    'tinyint',
    'uniqueidentifier',
    'varbinary',
    'varchar',
    'xml',
)

# See https://msdn.microsoft.com/en-us/library/ms174318.aspx.
FUNCTIONS = (
    '$partition',
    'abs',
    'acos',
    'app_name',
    'applock_mode',
    'applock_test',
    'ascii',
    'asin',
    'assemblyproperty',
    'atan',
    'atn2',
    'avg',
    'binary_checksum',
    'cast',
    'ceiling',
    'certencoded',
    'certprivatekey',
    'char',
    'charindex',
    'checksum',
    'checksum_agg',
    'choose',
    'col_length',
    'col_name',
    'columnproperty',
    'compress',
    'concat',
    'connectionproperty',
    'context_info',
    'convert',
    'cos',
    'cot',
    'count',
    'count_big',
    'current_request_id',
    'current_timestamp',
    'current_transaction_id',
    'current_user',
    'cursor_status',
    'database_principal_id',
    'databasepropertyex',
    'dateadd',
    'datediff',
    'datediff_big',
    'datefromparts',
    'datename',
    'datepart',
    'datetime2fromparts',
    'datetimefromparts',
    'datetimeoffsetfromparts',
    'day',
    'db_id',
    'db_name',
    'decompress',
    'degrees',
    'dense_rank',
    'difference',
    'eomonth',
    'error_line',
    'error_message',
    'error_number',
    'error_procedure',
    'error_severity',
    'error_state',
    'exp',
    'file_id',
    'file_idex',
    'file_name',
    'filegroup_id',
    'filegroup_name',
    'filegroupproperty',
    'fileproperty',
    'floor',
    'format',
    'formatmessage',
    'fulltextcatalogproperty',
    'fulltextserviceproperty',
    'get_filestream_transaction_context',
    'getansinull',
    'getdate',
    'getutcdate',
    'grouping',
    'grouping_id',
    'has_perms_by_name',
    'host_id',
    'host_name',
    'iif',
    'index_col',
    'indexkey_property',
    'indexproperty',
    'is_member',
    'is_rolemember',
    'is_srvrolemember',
    'isdate',
    'isjson',
    'isnull',
    'isnumeric',
    'json_modify',
    'json_query',
    'json_value',
    'left',
    'len',
    'log',
    'log10',
    'lower',
    'ltrim',
    'max',
    'min',
    'min_active_rowversion',
    'month',
    'nchar',
    'newid',
    'newsequentialid',
    'ntile',
    'object_definition',
    'object_id',
    'object_name',
    'object_schema_name',
    'objectproperty',
    'objectpropertyex',
    'opendatasource',
    'openjson',
    'openquery',
    'openrowset',
    'openxml',
    'original_db_name',
    'original_login',
    'parse',
    'parsename',
    'patindex',
    'permissions',
    'pi',
    'power',
    'pwdcompare',
    'pwdencrypt',
    'quotename',
    'radians',
    'rand',
    'rank',
    'replace',
    'replicate',
    'reverse',
    'right',
    'round',
    'row_number',
    'rowcount_big',
    'rtrim',
    'schema_id',
    'schema_name',
    'scope_identity',
    'serverproperty',
    'session_context',
    'session_user',
    'sign',
    'sin',
    'smalldatetimefromparts',
    'soundex',
    'sp_helplanguage',
    'space',
    'sqrt',
    'square',
    'stats_date',
    'stdev',
    'stdevp',
    'str',
    'string_escape',
    'string_split',
    'stuff',
    'substring',
    'sum',
    'suser_id',
    'suser_name',
    'suser_sid',
    'suser_sname',
    'switchoffset',
    'sysdatetime',
    'sysdatetimeoffset',
    'system_user',
    'sysutcdatetime',
    'tan',
    'textptr',
    'textvalid',
    'timefromparts',
    'todatetimeoffset',
    'try_cast',
    'try_convert',
    'try_parse',
    'type_id',
    'type_name',
    'typeproperty',
    'unicode',
    'upper',
    'user_id',
    'user_name',
    'var',
    'varp',
    'xact_state',
    'year',
)

# === NexusCore/openenv\Lib\site-packages\matplotlib\backend_tools.py ===
"""
Abstract base classes define the primitives for Tools.
These tools are used by `matplotlib.backend_managers.ToolManager`

:class:`ToolBase`
    Simple stateless tool

:class:`ToolToggleBase`
    Tool that has two states, only one Toggle tool can be
    active at any given time for the same
    `matplotlib.backend_managers.ToolManager`
"""

import enum
import functools
import re
import time
from types import SimpleNamespace
import uuid
from weakref import WeakKeyDictionary

import numpy as np

import matplotlib as mpl
from matplotlib._pylab_helpers import Gcf
from matplotlib import _api, cbook


class Cursors(enum.IntEnum):  # Must subclass int for the macOS backend.
    """Backend-independent cursor types."""
    POINTER = enum.auto()
    HAND = enum.auto()
    SELECT_REGION = enum.auto()
    MOVE = enum.auto()
    WAIT = enum.auto()
    RESIZE_HORIZONTAL = enum.auto()
    RESIZE_VERTICAL = enum.auto()
cursors = Cursors  # Backcompat.


# _tool_registry, _register_tool_class, and _find_tool_class implement a
# mechanism through which ToolManager.add_tool can determine whether a subclass
# of the requested tool class has been registered (either for the current
# canvas class or for a parent class), in which case that tool subclass will be
# instantiated instead.  This is the mechanism used e.g. to allow different
# GUI backends to implement different specializations for ConfigureSubplots.


_tool_registry = set()


def _register_tool_class(canvas_cls, tool_cls=None):
    """Decorator registering *tool_cls* as a tool class for *canvas_cls*."""
    if tool_cls is None:
        return functools.partial(_register_tool_class, canvas_cls)
    _tool_registry.add((canvas_cls, tool_cls))
    return tool_cls


def _find_tool_class(canvas_cls, tool_cls):
    """Find a subclass of *tool_cls* registered for *canvas_cls*."""
    for canvas_parent in canvas_cls.__mro__:
        for tool_child in _api.recursive_subclasses(tool_cls):
            if (canvas_parent, tool_child) in _tool_registry:
                return tool_child
    return tool_cls


# Views positions tool
_views_positions = 'viewpos'


class ToolBase:
    """
    Base tool class.

    A base tool, only implements `trigger` method or no method at all.
    The tool is instantiated by `matplotlib.backend_managers.ToolManager`.
    """

    default_keymap = None
    """
    Keymap to associate with this tool.

    ``list[str]``: List of keys that will trigger this tool when a keypress
    event is emitted on ``self.figure.canvas``.  Note that this attribute is
    looked up on the instance, and can therefore be a property (this is used
    e.g. by the built-in tools to load the rcParams at instantiation time).
    """

    description = None
    """
    Description of the Tool.

    `str`: Tooltip used if the Tool is included in a Toolbar.
    """

    image = None
    """
    Icon filename.

    ``str | None``: Filename of the Toolbar icon; either absolute, or relative to the
    directory containing the Python source file where the ``Tool.image`` class attribute
    is defined (in the latter case, this cannot be defined as an instance attribute).
    In either case, the extension is optional; leaving it off lets individual backends
    select the icon format they prefer.  If None, the *name* is used as a label in the
    toolbar button.
    """

    def __init__(self, toolmanager, name):
        self._name = name
        self._toolmanager = toolmanager
        self._figure = None

    name = property(
        lambda self: self._name,
        doc="The tool id (str, must be unique among tools of a tool manager).")
    toolmanager = property(
        lambda self: self._toolmanager,
        doc="The `.ToolManager` that controls this tool.")
    canvas = property(
        lambda self: self._figure.canvas if self._figure is not None else None,
        doc="The canvas of the figure affected by this tool, or None.")

    def set_figure(self, figure):
        self._figure = figure

    figure = property(
        lambda self: self._figure,
        # The setter must explicitly call self.set_figure so that subclasses can
        # meaningfully override it.
        lambda self, figure: self.set_figure(figure),
        doc="The Figure affected by this tool, or None.")

    def _make_classic_style_pseudo_toolbar(self):
        """
        Return a placeholder object with a single `canvas` attribute.

        This is useful to reuse the implementations of tools already provided
        by the classic Toolbars.
        """
        return SimpleNamespace(canvas=self.canvas)

    def trigger(self, sender, event, data=None):
        """
        Called when this tool gets used.

        This method is called by `.ToolManager.trigger_tool`.

        Parameters
        ----------
        event : `.Event`
            The canvas event that caused this tool to be called.
        sender : object
            Object that requested the tool to be triggered.
        data : object
            Extra data.
        """
        pass


class ToolToggleBase(ToolBase):
    """
    Toggleable tool.

    Every time it is triggered, it switches between enable and disable.

    Parameters
    ----------
    ``*args``
        Variable length argument to be used by the Tool.
    ``**kwargs``
        `toggled` if present and True, sets the initial state of the Tool
        Arbitrary keyword arguments to be consumed by the Tool
    """

    radio_group = None
    """
    Attribute to group 'radio' like tools (mutually exclusive).

    `str` that identifies the group or **None** if not belonging to a group.
    """

    cursor = None
    """Cursor to use when the tool is active."""

    default_toggled = False
    """Default of toggled state."""

    def __init__(self, *args, **kwargs):
        self._toggled = kwargs.pop('toggled', self.default_toggled)
        super().__init__(*args, **kwargs)

    def trigger(self, sender, event, data=None):
        """Calls `enable` or `disable` based on `toggled` value."""
        if self._toggled:
            self.disable(event)
        else:
            self.enable(event)
        self._toggled = not self._toggled

    def enable(self, event=None):
        """
        Enable the toggle tool.

        `trigger` calls this method when `toggled` is False.
        """
        pass

    def disable(self, event=None):
        """
        Disable the toggle tool.

        `trigger` call this method when `toggled` is True.

        This can happen in different circumstances.

        * Click on the toolbar tool button.
        * Call to `matplotlib.backend_managers.ToolManager.trigger_tool`.
        * Another `ToolToggleBase` derived tool is triggered
          (from the same `.ToolManager`).
        """
        pass

    @property
    def toggled(self):
        """State of the toggled tool."""
        return self._toggled

    def set_figure(self, figure):
        toggled = self.toggled
        if toggled:
            if self.figure:
                self.trigger(self, None)
            else:
                # if no figure the internal state is not changed
                # we change it here so next call to trigger will change it back
                self._toggled = False
        super().set_figure(figure)
        if toggled:
            if figure:
                self.trigger(self, None)
            else:
                # if there is no figure, trigger won't change the internal
                # state we change it back
                self._toggled = True


class ToolSetCursor(ToolBase):
    """
    Change to the current cursor while inaxes.

    This tool, keeps track of all `ToolToggleBase` derived tools, and updates
    the cursor when a tool gets triggered.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._id_drag = None
        self._current_tool = None
        self._default_cursor = cursors.POINTER
        self._last_cursor = self._default_cursor
        self.toolmanager.toolmanager_connect('tool_added_event',
                                             self._add_tool_cbk)
        for tool in self.toolmanager.tools.values():  # process current tools
            self._add_tool_cbk(mpl.backend_managers.ToolEvent(
                'tool_added_event', self.toolmanager, tool))

    def set_figure(self, figure):
        if self._id_drag:
            self.canvas.mpl_disconnect(self._id_drag)
        super().set_figure(figure)
        if figure:
            self._id_drag = self.canvas.mpl_connect(
                'motion_notify_event', self._set_cursor_cbk)

    def _add_tool_cbk(self, event):
        """Process every newly added tool."""
        if getattr(event.tool, 'cursor', None) is not None:
            self.toolmanager.toolmanager_connect(
                f'tool_trigger_{event.tool.name}', self._tool_trigger_cbk)

    def _tool_trigger_cbk(self, event):
        self._current_tool = event.tool if event.tool.toggled else None
        self._set_cursor_cbk(event.canvasevent)

    def _set_cursor_cbk(self, event):
        if not event or not self.canvas:
            return
        if (self._current_tool and getattr(event, "inaxes", None)
                and event.inaxes.get_navigate()):
            if self._last_cursor != self._current_tool.cursor:
                self.canvas.set_cursor(self._current_tool.cursor)
                self._last_cursor = self._current_tool.cursor
        elif self._last_cursor != self._default_cursor:
            self.canvas.set_cursor(self._default_cursor)
            self._last_cursor = self._default_cursor


class ToolCursorPosition(ToolBase):
    """
    Send message with the current pointer position.

    This tool runs in the background reporting the position of the cursor.
    """
    def __init__(self, *args, **kwargs):
        self._id_drag = None
        super().__init__(*args, **kwargs)

    def set_figure(self, figure):
        if self._id_drag:
            self.canvas.mpl_disconnect(self._id_drag)
        super().set_figure(figure)
        if figure:
            self._id_drag = self.canvas.mpl_connect(
                'motion_notify_event', self.send_message)

    def send_message(self, event):
        """Call `matplotlib.backend_managers.ToolManager.message_event`."""
        if self.toolmanager.messagelock.locked():
            return

        from matplotlib.backend_bases import NavigationToolbar2
        message = NavigationToolbar2._mouse_event_to_message(event)
        self.toolmanager.message_event(message, self)


class RubberbandBase(ToolBase):
    """Draw and remove a rubberband."""
    def trigger(self, sender, event, data=None):
        """Call `draw_rubberband` or `remove_rubberband` based on data."""
        if not self.figure.canvas.widgetlock.available(sender):
            return
        if data is not None:
            self.draw_rubberband(*data)
        else:
            self.remove_rubberband()

    def draw_rubberband(self, *data):
        """
        Draw rubberband.

        This method must get implemented per backend.
        """
        raise NotImplementedError

    def remove_rubberband(self):
        """
        Remove rubberband.

        This method should get implemented per backend.
        """
        pass


class ToolQuit(ToolBase):
    """Tool to call the figure manager destroy method."""

    description = 'Quit the figure'
    default_keymap = property(lambda self: mpl.rcParams['keymap.quit'])

    def trigger(self, sender, event, data=None):
        Gcf.destroy_fig(self.figure)


class ToolQuitAll(ToolBase):
    """Tool to call the figure manager destroy method."""

    description = 'Quit all figures'
    default_keymap = property(lambda self: mpl.rcParams['keymap.quit_all'])

    def trigger(self, sender, event, data=None):
        Gcf.destroy_all()


class ToolGrid(ToolBase):
    """Tool to toggle the major grids of the figure."""

    description = 'Toggle major grids'
    default_keymap = property(lambda self: mpl.rcParams['keymap.grid'])

    def trigger(self, sender, event, data=None):
        sentinel = str(uuid.uuid4())
        # Trigger grid switching by temporarily setting :rc:`keymap.grid`
        # to a unique key and sending an appropriate event.
        with (cbook._setattr_cm(event, key=sentinel),
              mpl.rc_context({'keymap.grid': sentinel})):
            mpl.backend_bases.key_press_handler(event, self.figure.canvas)


class ToolMinorGrid(ToolBase):
    """Tool to toggle the major and minor grids of the figure."""

    description = 'Toggle major and minor grids'
    default_keymap = property(lambda self: mpl.rcParams['keymap.grid_minor'])

    def trigger(self, sender, event, data=None):
        sentinel = str(uuid.uuid4())
        # Trigger grid switching by temporarily setting :rc:`keymap.grid_minor`
        # to a unique key and sending an appropriate event.
        with (cbook._setattr_cm(event, key=sentinel),
              mpl.rc_context({'keymap.grid_minor': sentinel})):
            mpl.backend_bases.key_press_handler(event, self.figure.canvas)


class ToolFullScreen(ToolBase):
    """Tool to toggle full screen."""

    description = 'Toggle fullscreen mode'
    default_keymap = property(lambda self: mpl.rcParams['keymap.fullscreen'])

    def trigger(self, sender, event, data=None):
        self.figure.canvas.manager.full_screen_toggle()


class AxisScaleBase(ToolToggleBase):
    """Base Tool to toggle between linear and logarithmic."""

    def trigger(self, sender, event, data=None):
        if event.inaxes is None:
            return
        super().trigger(sender, event, data)

    def enable(self, event=None):
        self.set_scale(event.inaxes, 'log')
        self.figure.canvas.draw_idle()

    def disable(self, event=None):
        self.set_scale(event.inaxes, 'linear')
        self.figure.canvas.draw_idle()


class ToolYScale(AxisScaleBase):
    """Tool to toggle between linear and logarithmic scales on the Y axis."""

    description = 'Toggle scale Y axis'
    default_keymap = property(lambda self: mpl.rcParams['keymap.yscale'])

    def set_scale(self, ax, scale):
        ax.set_yscale(scale)


class ToolXScale(AxisScaleBase):
    """Tool to toggle between linear and logarithmic scales on the X axis."""

    description = 'Toggle scale X axis'
    default_keymap = property(lambda self: mpl.rcParams['keymap.xscale'])

    def set_scale(self, ax, scale):
        ax.set_xscale(scale)


class ToolViewsPositions(ToolBase):
    """
    Auxiliary Tool to handle changes in views and positions.

    Runs in the background and should get used by all the tools that
    need to access the figure's history of views and positions, e.g.

    * `ToolZoom`
    * `ToolPan`
    * `ToolHome`
    * `ToolBack`
    * `ToolForward`
    """

    def __init__(self, *args, **kwargs):
        self.views = WeakKeyDictionary()
        self.positions = WeakKeyDictionary()
        self.home_views = WeakKeyDictionary()
        super().__init__(*args, **kwargs)

    def add_figure(self, figure):
        """Add the current figure to the stack of views and positions."""

        if figure not in self.views:
            self.views[figure] = cbook._Stack()
            self.positions[figure] = cbook._Stack()
            self.home_views[figure] = WeakKeyDictionary()
            # Define Home
            self.push_current(figure)
            # Make sure we add a home view for new Axes as they're added
            figure.add_axobserver(lambda fig: self.update_home_views(fig))

    def clear(self, figure):
        """Reset the Axes stack."""
        if figure in self.views:
            self.views[figure].clear()
            self.positions[figure].clear()
            self.home_views[figure].clear()
            self.update_home_views()

    def update_view(self):
        """
        Update the view limits and position for each Axes from the current
        stack position. If any Axes are present in the figure that aren't in
        the current stack position, use the home view limits for those Axes and
        don't update *any* positions.
        """

        views = self.views[self.figure]()
        if views is None:
            return
        pos = self.positions[self.figure]()
        if pos is None:
            return
        home_views = self.home_views[self.figure]
        all_axes = self.figure.get_axes()
        for a in all_axes:
            if a in views:
                cur_view = views[a]
            else:
                cur_view = home_views[a]
            a._set_view(cur_view)

        if set(all_axes).issubset(pos):
            for a in all_axes:
                # Restore both the original and modified positions
                a._set_position(pos[a][0], 'original')
                a._set_position(pos[a][1], 'active')

        self.figure.canvas.draw_idle()

    def push_current(self, figure=None):
        """
        Push the current view limits and position onto their respective stacks.
        """
        if not figure:
            figure = self.figure
        views = WeakKeyDictionary()
        pos = WeakKeyDictionary()
        for a in figure.get_axes():
            views[a] = a._get_view()
            pos[a] = self._axes_pos(a)
        self.views[figure].push(views)
        self.positions[figure].push(pos)

    def _axes_pos(self, ax):
        """
        Return the original and modified positions for the specified Axes.

        Parameters
        ----------
        ax : matplotlib.axes.Axes
            The `.Axes` to get the positions for.

        Returns
        -------
        original_position, modified_position
            A tuple of the original and modified positions.
        """

        return (ax.get_position(True).frozen(),
                ax.get_position().frozen())

    def update_home_views(self, figure=None):
        """
        Make sure that ``self.home_views`` has an entry for all Axes present
        in the figure.
        """

        if not figure:
            figure = self.figure
        for a in figure.get_axes():
            if a not in self.home_views[figure]:
                self.home_views[figure][a] = a._get_view()

    def home(self):
        """Recall the first view and position from the stack."""
        self.views[self.figure].home()
        self.positions[self.figure].home()

    def back(self):
        """Back one step in the stack of views and positions."""
        self.views[self.figure].back()
        self.positions[self.figure].back()

    def forward(self):
        """Forward one step in the stack of views and positions."""
        self.views[self.figure].forward()
        self.positions[self.figure].forward()


class ViewsPositionsBase(ToolBase):
    """Base class for `ToolHome`, `ToolBack` and `ToolForward`."""

    _on_trigger = None

    def trigger(self, sender, event, data=None):
        self.toolmanager.get_tool(_views_positions).add_figure(self.figure)
        getattr(self.toolmanager.get_tool(_views_positions),
                self._on_trigger)()
        self.toolmanager.get_tool(_views_positions).update_view()


class ToolHome(ViewsPositionsBase):
    """Restore the original view limits."""

    description = 'Reset original view'
    image = 'mpl-data/images/home'
    default_keymap = property(lambda self: mpl.rcParams['keymap.home'])
    _on_trigger = 'home'


class ToolBack(ViewsPositionsBase):
    """Move back up the view limits stack."""

    description = 'Back to previous view'
    image = 'mpl-data/images/back'
    default_keymap = property(lambda self: mpl.rcParams['keymap.back'])
    _on_trigger = 'back'


class ToolForward(ViewsPositionsBase):
    """Move forward in the view lim stack."""

    description = 'Forward to next view'
    image = 'mpl-data/images/forward'
    default_keymap = property(lambda self: mpl.rcParams['keymap.forward'])
    _on_trigger = 'forward'


class ConfigureSubplotsBase(ToolBase):
    """Base tool for the configuration of subplots."""

    description = 'Configure subplots'
    image = 'mpl-data/images/subplots'


class SaveFigureBase(ToolBase):
    """Base tool for figure saving."""

    description = 'Save the figure'
    image = 'mpl-data/images/filesave'
    default_keymap = property(lambda self: mpl.rcParams['keymap.save'])


class ZoomPanBase(ToolToggleBase):
    """Base class for `ToolZoom` and `ToolPan`."""
    def __init__(self, *args):
        super().__init__(*args)
        self._button_pressed = None
        self._xypress = None
        self._idPress = None
        self._idRelease = None
        self._idScroll = None
        self.base_scale = 2.
        self.scrollthresh = .5  # .5 second scroll threshold
        self.lastscroll = time.time()-self.scrollthresh

    def enable(self, event=None):
        """Connect press/release events and lock the canvas."""
        self.figure.canvas.widgetlock(self)
        self._idPress = self.figure.canvas.mpl_connect(
            'button_press_event', self._press)
        self._idRelease = self.figure.canvas.mpl_connect(
            'button_release_event', self._release)
        self._idScroll = self.figure.canvas.mpl_connect(
            'scroll_event', self.scroll_zoom)

    def disable(self, event=None):
        """Release the canvas and disconnect press/release events."""
        self._cancel_action()
        self.figure.canvas.widgetlock.release(self)
        self.figure.canvas.mpl_disconnect(self._idPress)
        self.figure.canvas.mpl_disconnect(self._idRelease)
        self.figure.canvas.mpl_disconnect(self._idScroll)

    def trigger(self, sender, event, data=None):
        self.toolmanager.get_tool(_views_positions).add_figure(self.figure)
        super().trigger(sender, event, data)
        new_navigate_mode = self.name.upper() if self.toggled else None
        for ax in self.figure.axes:
            ax.set_navigate_mode(new_navigate_mode)

    def scroll_zoom(self, event):
        # https://gist.github.com/tacaswell/3144287
        if event.inaxes is None:
            return

        if event.button == 'up':
            # deal with zoom in
            scl = self.base_scale
        elif event.button == 'down':
            # deal with zoom out
            scl = 1/self.base_scale
        else:
            # deal with something that should never happen
            scl = 1

        ax = event.inaxes
        ax._set_view_from_bbox([event.x, event.y, scl])

        # If last scroll was done within the timing threshold, delete the
        # previous view
        if (time.time()-self.lastscroll) < self.scrollthresh:
            self.toolmanager.get_tool(_views_positions).back()

        self.figure.canvas.draw_idle()  # force re-draw

        self.lastscroll = time.time()
        self.toolmanager.get_tool(_views_positions).push_current()


class ToolZoom(ZoomPanBase):
    """A Tool for zooming using a rectangle selector."""

    description = 'Zoom to rectangle'
    image = 'mpl-data/images/zoom_to_rect'
    default_keymap = property(lambda self: mpl.rcParams['keymap.zoom'])
    cursor = cursors.SELECT_REGION
    radio_group = 'default'

    def __init__(self, *args):
        super().__init__(*args)
        self._ids_zoom = []

    def _cancel_action(self):
        for zoom_id in self._ids_zoom:
            self.figure.canvas.mpl_disconnect(zoom_id)
        self.toolmanager.trigger_tool('rubberband', self)
        self.figure.canvas.draw_idle()
        self._xypress = None
        self._button_pressed = None
        self._ids_zoom = []
        return

    def _press(self, event):
        """Callback for mouse button presses in zoom-to-rectangle mode."""

        # If we're already in the middle of a zoom, pressing another
        # button works to "cancel"
        if self._ids_zoom:
            self._cancel_action()

        if event.button == 1:
            self._button_pressed = 1
        elif event.button == 3:
            self._button_pressed = 3
        else:
            self._cancel_action()
            return

        x, y = event.x, event.y

        self._xypress = []
        for i, a in enumerate(self.figure.get_axes()):
            if (x is not None and y is not None and a.in_axes(event) and
                    a.get_navigate() and a.can_zoom()):
                self._xypress.append((x, y, a, i, a._get_view()))

        id1 = self.figure.canvas.mpl_connect(
            'motion_notify_event', self._mouse_move)
        id2 = self.figure.canvas.mpl_connect(
            'key_press_event', self._switch_on_zoom_mode)
        id3 = self.figure.canvas.mpl_connect(
            'key_release_event', self._switch_off_zoom_mode)

        self._ids_zoom = id1, id2, id3
        self._zoom_mode = event.key

    def _switch_on_zoom_mode(self, event):
        self._zoom_mode = event.key
        self._mouse_move(event)

    def _switch_off_zoom_mode(self, event):
        self._zoom_mode = None
        self._mouse_move(event)

    def _mouse_move(self, event):
        """Callback for mouse moves in zoom-to-rectangle mode."""

        if self._xypress:
            x, y = event.x, event.y
            lastx, lasty, a, ind, view = self._xypress[0]
            (x1, y1), (x2, y2) = np.clip(
                [[lastx, lasty], [x, y]], a.bbox.min, a.bbox.max)
            if self._zoom_mode == "x":
                y1, y2 = a.bbox.intervaly
            elif self._zoom_mode == "y":
                x1, x2 = a.bbox.intervalx
            self.toolmanager.trigger_tool(
                'rubberband', self, data=(x1, y1, x2, y2))

    def _release(self, event):
        """Callback for mouse button releases in zoom-to-rectangle mode."""

        for zoom_id in self._ids_zoom:
            self.figure.canvas.mpl_disconnect(zoom_id)
        self._ids_zoom = []

        if not self._xypress:
            self._cancel_action()
            return

        done_ax = []

        for cur_xypress in self._xypress:
            x, y = event.x, event.y
            lastx, lasty, a, _ind, view = cur_xypress
            # ignore singular clicks - 5 pixels is a threshold
            if abs(x - lastx) < 5 or abs(y - lasty) < 5:
                self._cancel_action()
                return

            # detect twinx, twiny Axes and avoid double zooming
            twinx = any(a.get_shared_x_axes().joined(a, a1) for a1 in done_ax)
            twiny = any(a.get_shared_y_axes().joined(a, a1) for a1 in done_ax)
            done_ax.append(a)

            if self._button_pressed == 1:
                direction = 'in'
            elif self._button_pressed == 3:
                direction = 'out'
            else:
                continue

            a._set_view_from_bbox((lastx, lasty, x, y), direction,
                                  self._zoom_mode, twinx, twiny)

        self._zoom_mode = None
        self.toolmanager.get_tool(_views_positions).push_current()
        self._cancel_action()


class ToolPan(ZoomPanBase):
    """Pan Axes with left mouse, zoom with right."""

    default_keymap = property(lambda self: mpl.rcParams['keymap.pan'])
    description = 'Pan axes with left mouse, zoom with right'
    image = 'mpl-data/images/move'
    cursor = cursors.MOVE
    radio_group = 'default'

    def __init__(self, *args):
        super().__init__(*args)
        self._id_drag = None

    def _cancel_action(self):
        self._button_pressed = None
        self._xypress = []
        self.figure.canvas.mpl_disconnect(self._id_drag)
        self.toolmanager.messagelock.release(self)
        self.figure.canvas.draw_idle()

    def _press(self, event):
        if event.button == 1:
            self._button_pressed = 1
        elif event.button == 3:
            self._button_pressed = 3
        else:
            self._cancel_action()
            return

        x, y = event.x, event.y

        self._xypress = []
        for i, a in enumerate(self.figure.get_axes()):
            if (x is not None and y is not None and a.in_axes(event) and
                    a.get_navigate() and a.can_pan()):
                a.start_pan(x, y, event.button)
                self._xypress.append((a, i))
                self.toolmanager.messagelock(self)
                self._id_drag = self.figure.canvas.mpl_connect(
                    'motion_notify_event', self._mouse_move)

    def _release(self, event):
        if self._button_pressed is None:
            self._cancel_action()
            return

        self.figure.canvas.mpl_disconnect(self._id_drag)
        self.toolmanager.messagelock.release(self)

        for a, _ind in self._xypress:
            a.end_pan()
        if not self._xypress:
            self._cancel_action()
            return

        self.toolmanager.get_tool(_views_positions).push_current()
        self._cancel_action()

    def _mouse_move(self, event):
        for a, _ind in self._xypress:
            # safer to use the recorded button at the _press than current
            # button: # multiple button can get pressed during motion...
            a.drag_pan(self._button_pressed, event.key, event.x, event.y)
        self.toolmanager.canvas.draw_idle()


class ToolHelpBase(ToolBase):
    description = 'Print tool list, shortcuts and description'
    default_keymap = property(lambda self: mpl.rcParams['keymap.help'])
    image = 'mpl-data/images/help'

    @staticmethod
    def format_shortcut(key_sequence):
        """
        Convert a shortcut string from the notation used in rc config to the
        standard notation for displaying shortcuts, e.g. 'ctrl+a' -> 'Ctrl+A'.
        """
        return (key_sequence if len(key_sequence) == 1 else
                re.sub(r"\+[A-Z]", r"+Shift\g<0>", key_sequence).title())

    def _format_tool_keymap(self, name):
        keymaps = self.toolmanager.get_tool_keymap(name)
        return ", ".join(self.format_shortcut(keymap) for keymap in keymaps)

    def _get_help_entries(self):
        return [(name, self._format_tool_keymap(name), tool.description)
                for name, tool in sorted(self.toolmanager.tools.items())
                if tool.description]

    def _get_help_text(self):
        entries = self._get_help_entries()
        entries = ["{}: {}\n\t{}".format(*entry) for entry in entries]
        return "\n".join(entries)

    def _get_help_html(self):
        fmt = "<tr><td>{}</td><td>{}</td><td>{}</td></tr>"
        rows = [fmt.format(
            "<b>Action</b>", "<b>Shortcuts</b>", "<b>Description</b>")]
        rows += [fmt.format(*row) for row in self._get_help_entries()]
        return ("<style>td {padding: 0px 4px}</style>"
                "<table><thead>" + rows[0] + "</thead>"
                "<tbody>".join(rows[1:]) + "</tbody></table>")


class ToolCopyToClipboardBase(ToolBase):
    """Tool to copy the figure to the clipboard."""

    description = 'Copy the canvas figure to clipboard'
    default_keymap = property(lambda self: mpl.rcParams['keymap.copy'])

    def trigger(self, *args, **kwargs):
        message = "Copy tool is not available"
        self.toolmanager.message_event(message, self)


default_tools = {'home': ToolHome, 'back': ToolBack, 'forward': ToolForward,
                 'zoom': ToolZoom, 'pan': ToolPan,
                 'subplots': ConfigureSubplotsBase,
                 'save': SaveFigureBase,
                 'grid': ToolGrid,
                 'grid_minor': ToolMinorGrid,
                 'fullscreen': ToolFullScreen,
                 'quit': ToolQuit,
                 'quit_all': ToolQuitAll,
                 'xscale': ToolXScale,
                 'yscale': ToolYScale,
                 'position': ToolCursorPosition,
                 _views_positions: ToolViewsPositions,
                 'cursor': ToolSetCursor,
                 'rubberband': RubberbandBase,
                 'help': ToolHelpBase,
                 'copy': ToolCopyToClipboardBase,
                 }

default_toolbar_tools = [['navigation', ['home', 'back', 'forward']],
                         ['zoompan', ['pan', 'zoom', 'subplots']],
                         ['io', ['save', 'help']]]


def add_tools_to_manager(toolmanager, tools=default_tools):
    """
    Add multiple tools to a `.ToolManager`.

    Parameters
    ----------
    toolmanager : `.backend_managers.ToolManager`
        Manager to which the tools are added.
    tools : {str: class_like}, optional
        The tools to add in a {name: tool} dict, see
        `.backend_managers.ToolManager.add_tool` for more info.
    """

    for name, tool in tools.items():
        toolmanager.add_tool(name, tool)


def add_tools_to_container(container, tools=default_toolbar_tools):
    """
    Add multiple tools to the container.

    Parameters
    ----------
    container : Container
        `.backend_bases.ToolContainerBase` object that will get the tools
        added.
    tools : list, optional
        List in the form ``[[group1, [tool1, tool2 ...]], [group2, [...]]]``
        where the tools ``[tool1, tool2, ...]`` will display in group1.
        See `.backend_bases.ToolContainerBase.add_tool` for details.
    """

    for group, grouptools in tools:
        for position, tool in enumerate(grouptools):
            container.add_tool(tool, group, position)

# === NexusCore/openenv\Lib\site-packages\numpy\_core\shape_base.py ===
__all__ = ['atleast_1d', 'atleast_2d', 'atleast_3d', 'block', 'hstack',
           'stack', 'unstack', 'vstack']

import functools
import itertools
import operator

from . import fromnumeric as _from_nx
from . import numeric as _nx
from . import overrides
from .multiarray import array, asanyarray, normalize_axis_index

array_function_dispatch = functools.partial(
    overrides.array_function_dispatch, module='numpy')


def _atleast_1d_dispatcher(*arys):
    return arys


@array_function_dispatch(_atleast_1d_dispatcher)
def atleast_1d(*arys):
    """
    Convert inputs to arrays with at least one dimension.

    Scalar inputs are converted to 1-dimensional arrays, whilst
    higher-dimensional inputs are preserved.

    Parameters
    ----------
    arys1, arys2, ... : array_like
        One or more input arrays.

    Returns
    -------
    ret : ndarray
        An array, or tuple of arrays, each with ``a.ndim >= 1``.
        Copies are made only if necessary.

    See Also
    --------
    atleast_2d, atleast_3d

    Examples
    --------
    >>> import numpy as np
    >>> np.atleast_1d(1.0)
    array([1.])

    >>> x = np.arange(9.0).reshape(3,3)
    >>> np.atleast_1d(x)
    array([[0., 1., 2.],
           [3., 4., 5.],
           [6., 7., 8.]])
    >>> np.atleast_1d(x) is x
    True

    >>> np.atleast_1d(1, [3, 4])
    (array([1]), array([3, 4]))

    """
    if len(arys) == 1:
        result = asanyarray(arys[0])
        if result.ndim == 0:
            result = result.reshape(1)
        return result
    res = []
    for ary in arys:
        result = asanyarray(ary)
        if result.ndim == 0:
            result = result.reshape(1)
        res.append(result)
    return tuple(res)


def _atleast_2d_dispatcher(*arys):
    return arys


@array_function_dispatch(_atleast_2d_dispatcher)
def atleast_2d(*arys):
    """
    View inputs as arrays with at least two dimensions.

    Parameters
    ----------
    arys1, arys2, ... : array_like
        One or more array-like sequences.  Non-array inputs are converted
        to arrays.  Arrays that already have two or more dimensions are
        preserved.

    Returns
    -------
    res, res2, ... : ndarray
        An array, or tuple of arrays, each with ``a.ndim >= 2``.
        Copies are avoided where possible, and views with two or more
        dimensions are returned.

    See Also
    --------
    atleast_1d, atleast_3d

    Examples
    --------
    >>> import numpy as np
    >>> np.atleast_2d(3.0)
    array([[3.]])

    >>> x = np.arange(3.0)
    >>> np.atleast_2d(x)
    array([[0., 1., 2.]])
    >>> np.atleast_2d(x).base is x
    True

    >>> np.atleast_2d(1, [1, 2], [[1, 2]])
    (array([[1]]), array([[1, 2]]), array([[1, 2]]))

    """
    res = []
    for ary in arys:
        ary = asanyarray(ary)
        if ary.ndim == 0:
            result = ary.reshape(1, 1)
        elif ary.ndim == 1:
            result = ary[_nx.newaxis, :]
        else:
            result = ary
        res.append(result)
    if len(res) == 1:
        return res[0]
    else:
        return tuple(res)


def _atleast_3d_dispatcher(*arys):
    return arys


@array_function_dispatch(_atleast_3d_dispatcher)
def atleast_3d(*arys):
    """
    View inputs as arrays with at least three dimensions.

    Parameters
    ----------
    arys1, arys2, ... : array_like
        One or more array-like sequences.  Non-array inputs are converted to
        arrays.  Arrays that already have three or more dimensions are
        preserved.

    Returns
    -------
    res1, res2, ... : ndarray
        An array, or tuple of arrays, each with ``a.ndim >= 3``.  Copies are
        avoided where possible, and views with three or more dimensions are
        returned.  For example, a 1-D array of shape ``(N,)`` becomes a view
        of shape ``(1, N, 1)``, and a 2-D array of shape ``(M, N)`` becomes a
        view of shape ``(M, N, 1)``.

    See Also
    --------
    atleast_1d, atleast_2d

    Examples
    --------
    >>> import numpy as np
    >>> np.atleast_3d(3.0)
    array([[[3.]]])

    >>> x = np.arange(3.0)
    >>> np.atleast_3d(x).shape
    (1, 3, 1)

    >>> x = np.arange(12.0).reshape(4,3)
    >>> np.atleast_3d(x).shape
    (4, 3, 1)
    >>> np.atleast_3d(x).base is x.base  # x is a reshape, so not base itself
    True

    >>> for arr in np.atleast_3d([1, 2], [[1, 2]], [[[1, 2]]]):
    ...     print(arr, arr.shape) # doctest: +SKIP
    ...
    [[[1]
      [2]]] (1, 2, 1)
    [[[1]
      [2]]] (1, 2, 1)
    [[[1 2]]] (1, 1, 2)

    """
    res = []
    for ary in arys:
        ary = asanyarray(ary)
        if ary.ndim == 0:
            result = ary.reshape(1, 1, 1)
        elif ary.ndim == 1:
            result = ary[_nx.newaxis, :, _nx.newaxis]
        elif ary.ndim == 2:
            result = ary[:, :, _nx.newaxis]
        else:
            result = ary
        res.append(result)
    if len(res) == 1:
        return res[0]
    else:
        return tuple(res)


def _arrays_for_stack_dispatcher(arrays):
    if not hasattr(arrays, "__getitem__"):
        raise TypeError('arrays to stack must be passed as a "sequence" type '
                        'such as list or tuple.')

    return tuple(arrays)


def _vhstack_dispatcher(tup, *, dtype=None, casting=None):
    return _arrays_for_stack_dispatcher(tup)


@array_function_dispatch(_vhstack_dispatcher)
def vstack(tup, *, dtype=None, casting="same_kind"):
    """
    Stack arrays in sequence vertically (row wise).

    This is equivalent to concatenation along the first axis after 1-D arrays
    of shape `(N,)` have been reshaped to `(1,N)`. Rebuilds arrays divided by
    `vsplit`.

    This function makes most sense for arrays with up to 3 dimensions. For
    instance, for pixel-data with a height (first axis), width (second axis),
    and r/g/b channels (third axis). The functions `concatenate`, `stack` and
    `block` provide more general stacking and concatenation operations.

    Parameters
    ----------
    tup : sequence of ndarrays
        The arrays must have the same shape along all but the first axis.
        1-D arrays must have the same length. In the case of a single
        array_like input, it will be treated as a sequence of arrays; i.e.,
        each element along the zeroth axis is treated as a separate array.

    dtype : str or dtype
        If provided, the destination array will have this dtype. Cannot be
        provided together with `out`.

        .. versionadded:: 1.24

    casting : {'no', 'equiv', 'safe', 'same_kind', 'unsafe'}, optional
        Controls what kind of data casting may occur. Defaults to 'same_kind'.

        .. versionadded:: 1.24

    Returns
    -------
    stacked : ndarray
        The array formed by stacking the given arrays, will be at least 2-D.

    See Also
    --------
    concatenate : Join a sequence of arrays along an existing axis.
    stack : Join a sequence of arrays along a new axis.
    block : Assemble an nd-array from nested lists of blocks.
    hstack : Stack arrays in sequence horizontally (column wise).
    dstack : Stack arrays in sequence depth wise (along third axis).
    column_stack : Stack 1-D arrays as columns into a 2-D array.
    vsplit : Split an array into multiple sub-arrays vertically (row-wise).
    unstack : Split an array into a tuple of sub-arrays along an axis.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([1, 2, 3])
    >>> b = np.array([4, 5, 6])
    >>> np.vstack((a,b))
    array([[1, 2, 3],
           [4, 5, 6]])

    >>> a = np.array([[1], [2], [3]])
    >>> b = np.array([[4], [5], [6]])
    >>> np.vstack((a,b))
    array([[1],
           [2],
           [3],
           [4],
           [5],
           [6]])

    """
    arrs = atleast_2d(*tup)
    if not isinstance(arrs, tuple):
        arrs = (arrs,)
    return _nx.concatenate(arrs, 0, dtype=dtype, casting=casting)


@array_function_dispatch(_vhstack_dispatcher)
def hstack(tup, *, dtype=None, casting="same_kind"):
    """
    Stack arrays in sequence horizontally (column wise).

    This is equivalent to concatenation along the second axis, except for 1-D
    arrays where it concatenates along the first axis. Rebuilds arrays divided
    by `hsplit`.

    This function makes most sense for arrays with up to 3 dimensions. For
    instance, for pixel-data with a height (first axis), width (second axis),
    and r/g/b channels (third axis). The functions `concatenate`, `stack` and
    `block` provide more general stacking and concatenation operations.

    Parameters
    ----------
    tup : sequence of ndarrays
        The arrays must have the same shape along all but the second axis,
        except 1-D arrays which can be any length. In the case of a single
        array_like input, it will be treated as a sequence of arrays; i.e.,
        each element along the zeroth axis is treated as a separate array.

    dtype : str or dtype
        If provided, the destination array will have this dtype. Cannot be
        provided together with `out`.

        .. versionadded:: 1.24

    casting : {'no', 'equiv', 'safe', 'same_kind', 'unsafe'}, optional
        Controls what kind of data casting may occur. Defaults to 'same_kind'.

        .. versionadded:: 1.24

    Returns
    -------
    stacked : ndarray
        The array formed by stacking the given arrays.

    See Also
    --------
    concatenate : Join a sequence of arrays along an existing axis.
    stack : Join a sequence of arrays along a new axis.
    block : Assemble an nd-array from nested lists of blocks.
    vstack : Stack arrays in sequence vertically (row wise).
    dstack : Stack arrays in sequence depth wise (along third axis).
    column_stack : Stack 1-D arrays as columns into a 2-D array.
    hsplit : Split an array into multiple sub-arrays
             horizontally (column-wise).
    unstack : Split an array into a tuple of sub-arrays along an axis.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array((1,2,3))
    >>> b = np.array((4,5,6))
    >>> np.hstack((a,b))
    array([1, 2, 3, 4, 5, 6])
    >>> a = np.array([[1],[2],[3]])
    >>> b = np.array([[4],[5],[6]])
    >>> np.hstack((a,b))
    array([[1, 4],
           [2, 5],
           [3, 6]])

    """
    arrs = atleast_1d(*tup)
    if not isinstance(arrs, tuple):
        arrs = (arrs,)
    # As a special case, dimension 0 of 1-dimensional arrays is "horizontal"
    if arrs and arrs[0].ndim == 1:
        return _nx.concatenate(arrs, 0, dtype=dtype, casting=casting)
    else:
        return _nx.concatenate(arrs, 1, dtype=dtype, casting=casting)


def _stack_dispatcher(arrays, axis=None, out=None, *,
                      dtype=None, casting=None):
    arrays = _arrays_for_stack_dispatcher(arrays)
    if out is not None:
        # optimize for the typical case where only arrays is provided
        arrays = list(arrays)
        arrays.append(out)
    return arrays


@array_function_dispatch(_stack_dispatcher)
def stack(arrays, axis=0, out=None, *, dtype=None, casting="same_kind"):
    """
    Join a sequence of arrays along a new axis.

    The ``axis`` parameter specifies the index of the new axis in the
    dimensions of the result. For example, if ``axis=0`` it will be the first
    dimension and if ``axis=-1`` it will be the last dimension.

    Parameters
    ----------
    arrays : sequence of ndarrays
        Each array must have the same shape. In the case of a single ndarray
        array_like input, it will be treated as a sequence of arrays; i.e.,
        each element along the zeroth axis is treated as a separate array.

    axis : int, optional
        The axis in the result array along which the input arrays are stacked.

    out : ndarray, optional
        If provided, the destination to place the result. The shape must be
        correct, matching that of what stack would have returned if no
        out argument were specified.

    dtype : str or dtype
        If provided, the destination array will have this dtype. Cannot be
        provided together with `out`.

        .. versionadded:: 1.24

    casting : {'no', 'equiv', 'safe', 'same_kind', 'unsafe'}, optional
        Controls what kind of data casting may occur. Defaults to 'same_kind'.

        .. versionadded:: 1.24


    Returns
    -------
    stacked : ndarray
        The stacked array has one more dimension than the input arrays.

    See Also
    --------
    concatenate : Join a sequence of arrays along an existing axis.
    block : Assemble an nd-array from nested lists of blocks.
    split : Split array into a list of multiple sub-arrays of equal size.
    unstack : Split an array into a tuple of sub-arrays along an axis.

    Examples
    --------
    >>> import numpy as np
    >>> rng = np.random.default_rng()
    >>> arrays = [rng.normal(size=(3,4)) for _ in range(10)]
    >>> np.stack(arrays, axis=0).shape
    (10, 3, 4)

    >>> np.stack(arrays, axis=1).shape
    (3, 10, 4)

    >>> np.stack(arrays, axis=2).shape
    (3, 4, 10)

    >>> a = np.array([1, 2, 3])
    >>> b = np.array([4, 5, 6])
    >>> np.stack((a, b))
    array([[1, 2, 3],
           [4, 5, 6]])

    >>> np.stack((a, b), axis=-1)
    array([[1, 4],
           [2, 5],
           [3, 6]])

    """
    arrays = [asanyarray(arr) for arr in arrays]
    if not arrays:
        raise ValueError('need at least one array to stack')

    shapes = {arr.shape for arr in arrays}
    if len(shapes) != 1:
        raise ValueError('all input arrays must have the same shape')

    result_ndim = arrays[0].ndim + 1
    axis = normalize_axis_index(axis, result_ndim)

    sl = (slice(None),) * axis + (_nx.newaxis,)
    expanded_arrays = [arr[sl] for arr in arrays]
    return _nx.concatenate(expanded_arrays, axis=axis, out=out,
                           dtype=dtype, casting=casting)

def _unstack_dispatcher(x, /, *, axis=None):
    return (x,)

@array_function_dispatch(_unstack_dispatcher)
def unstack(x, /, *, axis=0):
    """
    Split an array into a sequence of arrays along the given axis.

    The ``axis`` parameter specifies the dimension along which the array will
    be split. For example, if ``axis=0`` (the default) it will be the first
    dimension and if ``axis=-1`` it will be the last dimension.

    The result is a tuple of arrays split along ``axis``.

    .. versionadded:: 2.1.0

    Parameters
    ----------
    x : ndarray
        The array to be unstacked.
    axis : int, optional
        Axis along which the array will be split. Default: ``0``.

    Returns
    -------
    unstacked : tuple of ndarrays
        The unstacked arrays.

    See Also
    --------
    stack : Join a sequence of arrays along a new axis.
    concatenate : Join a sequence of arrays along an existing axis.
    block : Assemble an nd-array from nested lists of blocks.
    split : Split array into a list of multiple sub-arrays of equal size.

    Notes
    -----
    ``unstack`` serves as the reverse operation of :py:func:`stack`, i.e.,
    ``stack(unstack(x, axis=axis), axis=axis) == x``.

    This function is equivalent to ``tuple(np.moveaxis(x, axis, 0))``, since
    iterating on an array iterates along the first axis.

    Examples
    --------
    >>> arr = np.arange(24).reshape((2, 3, 4))
    >>> np.unstack(arr)
    (array([[ 0,  1,  2,  3],
            [ 4,  5,  6,  7],
            [ 8,  9, 10, 11]]),
     array([[12, 13, 14, 15],
            [16, 17, 18, 19],
            [20, 21, 22, 23]]))
    >>> np.unstack(arr, axis=1)
    (array([[ 0,  1,  2,  3],
            [12, 13, 14, 15]]),
     array([[ 4,  5,  6,  7],
            [16, 17, 18, 19]]),
     array([[ 8,  9, 10, 11],
            [20, 21, 22, 23]]))
    >>> arr2 = np.stack(np.unstack(arr, axis=1), axis=1)
    >>> arr2.shape
    (2, 3, 4)
    >>> np.all(arr == arr2)
    np.True_

    """
    if x.ndim == 0:
        raise ValueError("Input array must be at least 1-d.")
    return tuple(_nx.moveaxis(x, axis, 0))


# Internal functions to eliminate the overhead of repeated dispatch in one of
# the two possible paths inside np.block.
# Use getattr to protect against __array_function__ being disabled.
_size = getattr(_from_nx.size, '__wrapped__', _from_nx.size)
_ndim = getattr(_from_nx.ndim, '__wrapped__', _from_nx.ndim)
_concatenate = getattr(_from_nx.concatenate,
                       '__wrapped__', _from_nx.concatenate)


def _block_format_index(index):
    """
    Convert a list of indices ``[0, 1, 2]`` into ``"arrays[0][1][2]"``.
    """
    idx_str = ''.join(f'[{i}]' for i in index if i is not None)
    return 'arrays' + idx_str


def _block_check_depths_match(arrays, parent_index=[]):
    """
    Recursive function checking that the depths of nested lists in `arrays`
    all match. Mismatch raises a ValueError as described in the block
    docstring below.

    The entire index (rather than just the depth) needs to be calculated
    for each innermost list, in case an error needs to be raised, so that
    the index of the offending list can be printed as part of the error.

    Parameters
    ----------
    arrays : nested list of arrays
        The arrays to check
    parent_index : list of int
        The full index of `arrays` within the nested lists passed to
        `_block_check_depths_match` at the top of the recursion.

    Returns
    -------
    first_index : list of int
        The full index of an element from the bottom of the nesting in
        `arrays`. If any element at the bottom is an empty list, this will
        refer to it, and the last index along the empty axis will be None.
    max_arr_ndim : int
        The maximum of the ndims of the arrays nested in `arrays`.
    final_size: int
        The number of elements in the final array. This is used the motivate
        the choice of algorithm used using benchmarking wisdom.

    """
    if isinstance(arrays, tuple):
        # not strictly necessary, but saves us from:
        #  - more than one way to do things - no point treating tuples like
        #    lists
        #  - horribly confusing behaviour that results when tuples are
        #    treated like ndarray
        raise TypeError(
            f'{_block_format_index(parent_index)} is a tuple. '
            'Only lists can be used to arrange blocks, and np.block does '
            'not allow implicit conversion from tuple to ndarray.'
        )
    elif isinstance(arrays, list) and len(arrays) > 0:
        idxs_ndims = (_block_check_depths_match(arr, parent_index + [i])
                      for i, arr in enumerate(arrays))

        first_index, max_arr_ndim, final_size = next(idxs_ndims)
        for index, ndim, size in idxs_ndims:
            final_size += size
            if ndim > max_arr_ndim:
                max_arr_ndim = ndim
            if len(index) != len(first_index):
                raise ValueError(
                    "List depths are mismatched. First element was at "
                    f"depth {len(first_index)}, but there is an element at "
                    f"depth {len(index)} ({_block_format_index(index)})"
                )
            # propagate our flag that indicates an empty list at the bottom
            if index[-1] is None:
                first_index = index

        return first_index, max_arr_ndim, final_size
    elif isinstance(arrays, list) and len(arrays) == 0:
        # We've 'bottomed out' on an empty list
        return parent_index + [None], 0, 0
    else:
        # We've 'bottomed out' - arrays is either a scalar or an array
        size = _size(arrays)
        return parent_index, _ndim(arrays), size


def _atleast_nd(a, ndim):
    # Ensures `a` has at least `ndim` dimensions by prepending
    # ones to `a.shape` as necessary
    return array(a, ndmin=ndim, copy=None, subok=True)


def _accumulate(values):
    return list(itertools.accumulate(values))


def _concatenate_shapes(shapes, axis):
    """Given array shapes, return the resulting shape and slices prefixes.

    These help in nested concatenation.

    Returns
    -------
    shape: tuple of int
        This tuple satisfies::

            shape, _ = _concatenate_shapes([arr.shape for shape in arrs], axis)
            shape == concatenate(arrs, axis).shape

    slice_prefixes: tuple of (slice(start, end), )
        For a list of arrays being concatenated, this returns the slice
        in the larger array at axis that needs to be sliced into.

        For example, the following holds::

            ret = concatenate([a, b, c], axis)
            _, (sl_a, sl_b, sl_c) = concatenate_slices([a, b, c], axis)

            ret[(slice(None),) * axis + sl_a] == a
            ret[(slice(None),) * axis + sl_b] == b
            ret[(slice(None),) * axis + sl_c] == c

        These are called slice prefixes since they are used in the recursive
        blocking algorithm to compute the left-most slices during the
        recursion. Therefore, they must be prepended to rest of the slice
        that was computed deeper in the recursion.

        These are returned as tuples to ensure that they can quickly be added
        to existing slice tuple without creating a new tuple every time.

    """
    # Cache a result that will be reused.
    shape_at_axis = [shape[axis] for shape in shapes]

    # Take a shape, any shape
    first_shape = shapes[0]
    first_shape_pre = first_shape[:axis]
    first_shape_post = first_shape[axis + 1:]

    if any(shape[:axis] != first_shape_pre or
           shape[axis + 1:] != first_shape_post for shape in shapes):
        raise ValueError(
            f'Mismatched array shapes in block along axis {axis}.')

    shape = (first_shape_pre + (sum(shape_at_axis),) + first_shape[axis + 1:])

    offsets_at_axis = _accumulate(shape_at_axis)
    slice_prefixes = [(slice(start, end),)
                      for start, end in zip([0] + offsets_at_axis,
                                            offsets_at_axis)]
    return shape, slice_prefixes


def _block_info_recursion(arrays, max_depth, result_ndim, depth=0):
    """
    Returns the shape of the final array, along with a list
    of slices and a list of arrays that can be used for assignment inside the
    new array

    Parameters
    ----------
    arrays : nested list of arrays
        The arrays to check
    max_depth : list of int
        The number of nested lists
    result_ndim : int
        The number of dimensions in thefinal array.

    Returns
    -------
    shape : tuple of int
        The shape that the final array will take on.
    slices: list of tuple of slices
        The slices into the full array required for assignment. These are
        required to be prepended with ``(Ellipsis, )`` to obtain to correct
        final index.
    arrays: list of ndarray
        The data to assign to each slice of the full array

    """
    if depth < max_depth:
        shapes, slices, arrays = zip(
            *[_block_info_recursion(arr, max_depth, result_ndim, depth + 1)
              for arr in arrays])

        axis = result_ndim - max_depth + depth
        shape, slice_prefixes = _concatenate_shapes(shapes, axis)

        # Prepend the slice prefix and flatten the slices
        slices = [slice_prefix + the_slice
                  for slice_prefix, inner_slices in zip(slice_prefixes, slices)
                  for the_slice in inner_slices]

        # Flatten the array list
        arrays = functools.reduce(operator.add, arrays)

        return shape, slices, arrays
    else:
        # We've 'bottomed out' - arrays is either a scalar or an array
        # type(arrays) is not list
        # Return the slice and the array inside a list to be consistent with
        # the recursive case.
        arr = _atleast_nd(arrays, result_ndim)
        return arr.shape, [()], [arr]


def _block(arrays, max_depth, result_ndim, depth=0):
    """
    Internal implementation of block based on repeated concatenation.
    `arrays` is the argument passed to
    block. `max_depth` is the depth of nested lists within `arrays` and
    `result_ndim` is the greatest of the dimensions of the arrays in
    `arrays` and the depth of the lists in `arrays` (see block docstring
    for details).
    """
    if depth < max_depth:
        arrs = [_block(arr, max_depth, result_ndim, depth + 1)
                for arr in arrays]
        return _concatenate(arrs, axis=-(max_depth - depth))
    else:
        # We've 'bottomed out' - arrays is either a scalar or an array
        # type(arrays) is not list
        return _atleast_nd(arrays, result_ndim)


def _block_dispatcher(arrays):
    # Use type(...) is list to match the behavior of np.block(), which special
    # cases list specifically rather than allowing for generic iterables or
    # tuple. Also, we know that list.__array_function__ will never exist.
    if isinstance(arrays, list):
        for subarrays in arrays:
            yield from _block_dispatcher(subarrays)
    else:
        yield arrays


@array_function_dispatch(_block_dispatcher)
def block(arrays):
    """
    Assemble an nd-array from nested lists of blocks.

    Blocks in the innermost lists are concatenated (see `concatenate`) along
    the last dimension (-1), then these are concatenated along the
    second-last dimension (-2), and so on until the outermost list is reached.

    Blocks can be of any dimension, but will not be broadcasted using
    the normal rules. Instead, leading axes of size 1 are inserted,
    to make ``block.ndim`` the same for all blocks. This is primarily useful
    for working with scalars, and means that code like ``np.block([v, 1])``
    is valid, where ``v.ndim == 1``.

    When the nested list is two levels deep, this allows block matrices to be
    constructed from their components.

    Parameters
    ----------
    arrays : nested list of array_like or scalars (but not tuples)
        If passed a single ndarray or scalar (a nested list of depth 0), this
        is returned unmodified (and not copied).

        Elements shapes must match along the appropriate axes (without
        broadcasting), but leading 1s will be prepended to the shape as
        necessary to make the dimensions match.

    Returns
    -------
    block_array : ndarray
        The array assembled from the given blocks.

        The dimensionality of the output is equal to the greatest of:

        * the dimensionality of all the inputs
        * the depth to which the input list is nested

    Raises
    ------
    ValueError
        * If list depths are mismatched - for instance, ``[[a, b], c]`` is
          illegal, and should be spelt ``[[a, b], [c]]``
        * If lists are empty - for instance, ``[[a, b], []]``

    See Also
    --------
    concatenate : Join a sequence of arrays along an existing axis.
    stack : Join a sequence of arrays along a new axis.
    vstack : Stack arrays in sequence vertically (row wise).
    hstack : Stack arrays in sequence horizontally (column wise).
    dstack : Stack arrays in sequence depth wise (along third axis).
    column_stack : Stack 1-D arrays as columns into a 2-D array.
    vsplit : Split an array into multiple sub-arrays vertically (row-wise).
    unstack : Split an array into a tuple of sub-arrays along an axis.

    Notes
    -----
    When called with only scalars, ``np.block`` is equivalent to an ndarray
    call. So ``np.block([[1, 2], [3, 4]])`` is equivalent to
    ``np.array([[1, 2], [3, 4]])``.

    This function does not enforce that the blocks lie on a fixed grid.
    ``np.block([[a, b], [c, d]])`` is not restricted to arrays of the form::

        AAAbb
        AAAbb
        cccDD

    But is also allowed to produce, for some ``a, b, c, d``::

        AAAbb
        AAAbb
        cDDDD

    Since concatenation happens along the last axis first, `block` is *not*
    capable of producing the following directly::

        AAAbb
        cccbb
        cccDD

    Matlab's "square bracket stacking", ``[A, B, ...; p, q, ...]``, is
    equivalent to ``np.block([[A, B, ...], [p, q, ...]])``.

    Examples
    --------
    The most common use of this function is to build a block matrix:

    >>> import numpy as np
    >>> A = np.eye(2) * 2
    >>> B = np.eye(3) * 3
    >>> np.block([
    ...     [A,               np.zeros((2, 3))],
    ...     [np.ones((3, 2)), B               ]
    ... ])
    array([[2., 0., 0., 0., 0.],
           [0., 2., 0., 0., 0.],
           [1., 1., 3., 0., 0.],
           [1., 1., 0., 3., 0.],
           [1., 1., 0., 0., 3.]])

    With a list of depth 1, `block` can be used as `hstack`:

    >>> np.block([1, 2, 3])              # hstack([1, 2, 3])
    array([1, 2, 3])

    >>> a = np.array([1, 2, 3])
    >>> b = np.array([4, 5, 6])
    >>> np.block([a, b, 10])             # hstack([a, b, 10])
    array([ 1,  2,  3,  4,  5,  6, 10])

    >>> A = np.ones((2, 2), int)
    >>> B = 2 * A
    >>> np.block([A, B])                 # hstack([A, B])
    array([[1, 1, 2, 2],
           [1, 1, 2, 2]])

    With a list of depth 2, `block` can be used in place of `vstack`:

    >>> a = np.array([1, 2, 3])
    >>> b = np.array([4, 5, 6])
    >>> np.block([[a], [b]])             # vstack([a, b])
    array([[1, 2, 3],
           [4, 5, 6]])

    >>> A = np.ones((2, 2), int)
    >>> B = 2 * A
    >>> np.block([[A], [B]])             # vstack([A, B])
    array([[1, 1],
           [1, 1],
           [2, 2],
           [2, 2]])

    It can also be used in place of `atleast_1d` and `atleast_2d`:

    >>> a = np.array(0)
    >>> b = np.array([1])
    >>> np.block([a])                    # atleast_1d(a)
    array([0])
    >>> np.block([b])                    # atleast_1d(b)
    array([1])

    >>> np.block([[a]])                  # atleast_2d(a)
    array([[0]])
    >>> np.block([[b]])                  # atleast_2d(b)
    array([[1]])


    """
    arrays, list_ndim, result_ndim, final_size = _block_setup(arrays)

    # It was found through benchmarking that making an array of final size
    # around 256x256 was faster by straight concatenation on a
    # i7-7700HQ processor and dual channel ram 2400MHz.
    # It didn't seem to matter heavily on the dtype used.
    #
    # A 2D array using repeated concatenation requires 2 copies of the array.
    #
    # The fastest algorithm will depend on the ratio of CPU power to memory
    # speed.
    # One can monitor the results of the benchmark
    # https://pv.github.io/numpy-bench/#bench_shape_base.Block2D.time_block2d
    # to tune this parameter until a C version of the `_block_info_recursion`
    # algorithm is implemented which would likely be faster than the python
    # version.
    if list_ndim * final_size > (2 * 512 * 512):
        return _block_slicing(arrays, list_ndim, result_ndim)
    else:
        return _block_concatenate(arrays, list_ndim, result_ndim)


# These helper functions are mostly used for testing.
# They allow us to write tests that directly call `_block_slicing`
# or `_block_concatenate` without blocking large arrays to force the wisdom
# to trigger the desired path.
def _block_setup(arrays):
    """
    Returns
    (`arrays`, list_ndim, result_ndim, final_size)
    """
    bottom_index, arr_ndim, final_size = _block_check_depths_match(arrays)
    list_ndim = len(bottom_index)
    if bottom_index and bottom_index[-1] is None:
        raise ValueError(
            f'List at {_block_format_index(bottom_index)} cannot be empty'
        )
    result_ndim = max(arr_ndim, list_ndim)
    return arrays, list_ndim, result_ndim, final_size


def _block_slicing(arrays, list_ndim, result_ndim):
    shape, slices, arrays = _block_info_recursion(
        arrays, list_ndim, result_ndim)
    dtype = _nx.result_type(*[arr.dtype for arr in arrays])

    # Test preferring F only in the case that all input arrays are F
    F_order = all(arr.flags['F_CONTIGUOUS'] for arr in arrays)
    C_order = all(arr.flags['C_CONTIGUOUS'] for arr in arrays)
    order = 'F' if F_order and not C_order else 'C'
    result = _nx.empty(shape=shape, dtype=dtype, order=order)
    # Note: In a c implementation, the function
    # PyArray_CreateMultiSortedStridePerm could be used for more advanced
    # guessing of the desired order.

    for the_slice, arr in zip(slices, arrays):
        result[(Ellipsis,) + the_slice] = arr
    return result


def _block_concatenate(arrays, list_ndim, result_ndim):
    result = _block(arrays, list_ndim, result_ndim)
    if list_ndim == 0:
        # Catch an edge case where _block returns a view because
        # `arrays` is a single numpy array and not a list of numpy arrays.
        # This might copy scalars or lists twice, but this isn't a likely
        # usecase for those interested in performance
        result = result.copy()
    return result

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\permission_service\async_client.py ===
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
from collections import OrderedDict
import functools
import re
from typing import (
    Callable,
    Dict,
    Mapping,
    MutableMapping,
    MutableSequence,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
)

from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1
from google.api_core import retry_async as retries
from google.api_core.client_options import ClientOptions
from google.auth import credentials as ga_credentials  # type: ignore
from google.oauth2 import service_account  # type: ignore

from google.ai.generativelanguage_v1beta import gapic_version as package_version

try:
    OptionalRetry = Union[retries.AsyncRetry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.AsyncRetry, object, None]  # type: ignore

from google.longrunning import operations_pb2  # type: ignore
from google.protobuf import field_mask_pb2  # type: ignore

from google.ai.generativelanguage_v1beta.services.permission_service import pagers
from google.ai.generativelanguage_v1beta.types import permission as gag_permission
from google.ai.generativelanguage_v1beta.types import permission
from google.ai.generativelanguage_v1beta.types import permission_service

from .client import PermissionServiceClient
from .transports.base import DEFAULT_CLIENT_INFO, PermissionServiceTransport
from .transports.grpc_asyncio import PermissionServiceGrpcAsyncIOTransport


class PermissionServiceAsyncClient:
    """Provides methods for managing permissions to PaLM API
    resources.
    """

    _client: PermissionServiceClient

    # Copy defaults from the synchronous client for use here.
    # Note: DEFAULT_ENDPOINT is deprecated. Use _DEFAULT_ENDPOINT_TEMPLATE instead.
    DEFAULT_ENDPOINT = PermissionServiceClient.DEFAULT_ENDPOINT
    DEFAULT_MTLS_ENDPOINT = PermissionServiceClient.DEFAULT_MTLS_ENDPOINT
    _DEFAULT_ENDPOINT_TEMPLATE = PermissionServiceClient._DEFAULT_ENDPOINT_TEMPLATE
    _DEFAULT_UNIVERSE = PermissionServiceClient._DEFAULT_UNIVERSE

    permission_path = staticmethod(PermissionServiceClient.permission_path)
    parse_permission_path = staticmethod(PermissionServiceClient.parse_permission_path)
    common_billing_account_path = staticmethod(
        PermissionServiceClient.common_billing_account_path
    )
    parse_common_billing_account_path = staticmethod(
        PermissionServiceClient.parse_common_billing_account_path
    )
    common_folder_path = staticmethod(PermissionServiceClient.common_folder_path)
    parse_common_folder_path = staticmethod(
        PermissionServiceClient.parse_common_folder_path
    )
    common_organization_path = staticmethod(
        PermissionServiceClient.common_organization_path
    )
    parse_common_organization_path = staticmethod(
        PermissionServiceClient.parse_common_organization_path
    )
    common_project_path = staticmethod(PermissionServiceClient.common_project_path)
    parse_common_project_path = staticmethod(
        PermissionServiceClient.parse_common_project_path
    )
    common_location_path = staticmethod(PermissionServiceClient.common_location_path)
    parse_common_location_path = staticmethod(
        PermissionServiceClient.parse_common_location_path
    )

    @classmethod
    def from_service_account_info(cls, info: dict, *args, **kwargs):
        """Creates an instance of this client using the provided credentials
            info.

        Args:
            info (dict): The service account private key info.
            args: Additional arguments to pass to the constructor.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            PermissionServiceAsyncClient: The constructed client.
        """
        return PermissionServiceClient.from_service_account_info.__func__(PermissionServiceAsyncClient, info, *args, **kwargs)  # type: ignore

    @classmethod
    def from_service_account_file(cls, filename: str, *args, **kwargs):
        """Creates an instance of this client using the provided credentials
            file.

        Args:
            filename (str): The path to the service account private key json
                file.
            args: Additional arguments to pass to the constructor.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            PermissionServiceAsyncClient: The constructed client.
        """
        return PermissionServiceClient.from_service_account_file.__func__(PermissionServiceAsyncClient, filename, *args, **kwargs)  # type: ignore

    from_service_account_json = from_service_account_file

    @classmethod
    def get_mtls_endpoint_and_cert_source(
        cls, client_options: Optional[ClientOptions] = None
    ):
        """Return the API endpoint and client cert source for mutual TLS.

        The client cert source is determined in the following order:
        (1) if `GOOGLE_API_USE_CLIENT_CERTIFICATE` environment variable is not "true", the
        client cert source is None.
        (2) if `client_options.client_cert_source` is provided, use the provided one; if the
        default client cert source exists, use the default one; otherwise the client cert
        source is None.

        The API endpoint is determined in the following order:
        (1) if `client_options.api_endpoint` if provided, use the provided one.
        (2) if `GOOGLE_API_USE_CLIENT_CERTIFICATE` environment variable is "always", use the
        default mTLS endpoint; if the environment variable is "never", use the default API
        endpoint; otherwise if client cert source exists, use the default mTLS endpoint, otherwise
        use the default API endpoint.

        More details can be found at https://google.aip.dev/auth/4114.

        Args:
            client_options (google.api_core.client_options.ClientOptions): Custom options for the
                client. Only the `api_endpoint` and `client_cert_source` properties may be used
                in this method.

        Returns:
            Tuple[str, Callable[[], Tuple[bytes, bytes]]]: returns the API endpoint and the
                client cert source to use.

        Raises:
            google.auth.exceptions.MutualTLSChannelError: If any errors happen.
        """
        return PermissionServiceClient.get_mtls_endpoint_and_cert_source(client_options)  # type: ignore

    @property
    def transport(self) -> PermissionServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            PermissionServiceTransport: The transport used by the client instance.
        """
        return self._client.transport

    @property
    def api_endpoint(self):
        """Return the API endpoint used by the client instance.

        Returns:
            str: The API endpoint used by the client instance.
        """
        return self._client._api_endpoint

    @property
    def universe_domain(self) -> str:
        """Return the universe domain used by the client instance.

        Returns:
            str: The universe domain used
                by the client instance.
        """
        return self._client._universe_domain

    get_transport_class = functools.partial(
        type(PermissionServiceClient).get_transport_class, type(PermissionServiceClient)
    )

    def __init__(
        self,
        *,
        credentials: Optional[ga_credentials.Credentials] = None,
        transport: Optional[
            Union[
                str,
                PermissionServiceTransport,
                Callable[..., PermissionServiceTransport],
            ]
        ] = "grpc_asyncio",
        client_options: Optional[ClientOptions] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the permission service async client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,PermissionServiceTransport,Callable[..., PermissionServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport to use.
                If a Callable is given, it will be called with the same set of initialization
                arguments as used in the PermissionServiceTransport constructor.
                If set to None, a transport is chosen automatically.
            client_options (Optional[Union[google.api_core.client_options.ClientOptions, dict]]):
                Custom options for the client.

                1. The ``api_endpoint`` property can be used to override the
                default endpoint provided by the client when ``transport`` is
                not explicitly provided. Only if this property is not set and
                ``transport`` was not explicitly provided, the endpoint is
                determined by the GOOGLE_API_USE_MTLS_ENDPOINT environment
                variable, which have one of the following values:
                "always" (always use the default mTLS endpoint), "never" (always
                use the default regular endpoint) and "auto" (auto-switch to the
                default mTLS endpoint if client certificate is present; this is
                the default value).

                2. If the GOOGLE_API_USE_CLIENT_CERTIFICATE environment variable
                is "true", then the ``client_cert_source`` property can be used
                to provide a client certificate for mTLS transport. If
                not provided, the default SSL client certificate will be used if
                present. If GOOGLE_API_USE_CLIENT_CERTIFICATE is "false" or not
                set, no client certificate will be used.

                3. The ``universe_domain`` property can be used to override the
                default "googleapis.com" universe. Note that ``api_endpoint``
                property still takes precedence; and ``universe_domain`` is
                currently not supported for mTLS.

            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.

        Raises:
            google.auth.exceptions.MutualTlsChannelError: If mutual TLS transport
                creation failed for any reason.
        """
        self._client = PermissionServiceClient(
            credentials=credentials,
            transport=transport,
            client_options=client_options,
            client_info=client_info,
        )

    async def create_permission(
        self,
        request: Optional[
            Union[permission_service.CreatePermissionRequest, dict]
        ] = None,
        *,
        parent: Optional[str] = None,
        permission: Optional[gag_permission.Permission] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> gag_permission.Permission:
        r"""Create a permission to a specific resource.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_create_permission():
                # Create a client
                client = generativelanguage_v1beta.PermissionServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.CreatePermissionRequest(
                    parent="parent_value",
                )

                # Make the request
                response = await client.create_permission(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.CreatePermissionRequest, dict]]):
                The request object. Request to create a ``Permission``.
            parent (:class:`str`):
                Required. The parent resource of the ``Permission``.
                Formats: ``tunedModels/{tuned_model}``
                ``corpora/{corpus}``

                This corresponds to the ``parent`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            permission (:class:`google.ai.generativelanguage_v1beta.types.Permission`):
                Required. The permission to create.
                This corresponds to the ``permission`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.Permission:
                Permission resource grants user,
                group or the rest of the world access to
                the PaLM API resource (e.g. a tuned
                model, corpus).

                A role is a collection of permitted
                operations that allows users to perform
                specific actions on PaLM API resources.
                To make them available to users, groups,
                or service accounts, you assign roles.
                When you assign a role, you grant
                permissions that the role contains.

                There are three concentric roles. Each
                role is a superset of the previous
                role's permitted operations:

                - reader can use the resource (e.g.
                  tuned model, corpus) for inference
                - writer has reader's permissions and
                  additionally can edit and share
                - owner has writer's permissions and
                  additionally can delete

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([parent, permission])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, permission_service.CreatePermissionRequest):
            request = permission_service.CreatePermissionRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if parent is not None:
            request.parent = parent
        if permission is not None:
            request.permission = permission

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.create_permission
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("parent", request.parent),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def get_permission(
        self,
        request: Optional[Union[permission_service.GetPermissionRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> permission.Permission:
        r"""Gets information about a specific Permission.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_get_permission():
                # Create a client
                client = generativelanguage_v1beta.PermissionServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.GetPermissionRequest(
                    name="name_value",
                )

                # Make the request
                response = await client.get_permission(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.GetPermissionRequest, dict]]):
                The request object. Request for getting information about a specific
                ``Permission``.
            name (:class:`str`):
                Required. The resource name of the permission.

                Formats:
                ``tunedModels/{tuned_model}/permissions/{permission}``
                ``corpora/{corpus}/permissions/{permission}``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.Permission:
                Permission resource grants user,
                group or the rest of the world access to
                the PaLM API resource (e.g. a tuned
                model, corpus).

                A role is a collection of permitted
                operations that allows users to perform
                specific actions on PaLM API resources.
                To make them available to users, groups,
                or service accounts, you assign roles.
                When you assign a role, you grant
                permissions that the role contains.

                There are three concentric roles. Each
                role is a superset of the previous
                role's permitted operations:

                - reader can use the resource (e.g.
                  tuned model, corpus) for inference
                - writer has reader's permissions and
                  additionally can edit and share
                - owner has writer's permissions and
                  additionally can delete

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([name])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, permission_service.GetPermissionRequest):
            request = permission_service.GetPermissionRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if name is not None:
            request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.get_permission
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def list_permissions(
        self,
        request: Optional[
            Union[permission_service.ListPermissionsRequest, dict]
        ] = None,
        *,
        parent: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> pagers.ListPermissionsAsyncPager:
        r"""Lists permissions for the specific resource.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_list_permissions():
                # Create a client
                client = generativelanguage_v1beta.PermissionServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.ListPermissionsRequest(
                    parent="parent_value",
                )

                # Make the request
                page_result = client.list_permissions(request=request)

                # Handle the response
                async for response in page_result:
                    print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.ListPermissionsRequest, dict]]):
                The request object. Request for listing permissions.
            parent (:class:`str`):
                Required. The parent resource of the permissions.
                Formats: ``tunedModels/{tuned_model}``
                ``corpora/{corpus}``

                This corresponds to the ``parent`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.services.permission_service.pagers.ListPermissionsAsyncPager:
                Response from ListPermissions containing a paginated list of
                   permissions.

                Iterating over this object will yield results and
                resolve additional pages automatically.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([parent])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, permission_service.ListPermissionsRequest):
            request = permission_service.ListPermissionsRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if parent is not None:
            request.parent = parent

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.list_permissions
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("parent", request.parent),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # This method is paged; wrap the response in a pager, which provides
        # an `__aiter__` convenience method.
        response = pagers.ListPermissionsAsyncPager(
            method=rpc,
            request=request,
            response=response,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def update_permission(
        self,
        request: Optional[
            Union[permission_service.UpdatePermissionRequest, dict]
        ] = None,
        *,
        permission: Optional[gag_permission.Permission] = None,
        update_mask: Optional[field_mask_pb2.FieldMask] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> gag_permission.Permission:
        r"""Updates the permission.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_update_permission():
                # Create a client
                client = generativelanguage_v1beta.PermissionServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.UpdatePermissionRequest(
                )

                # Make the request
                response = await client.update_permission(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.UpdatePermissionRequest, dict]]):
                The request object. Request to update the ``Permission``.
            permission (:class:`google.ai.generativelanguage_v1beta.types.Permission`):
                Required. The permission to update.

                The permission's ``name`` field is used to identify the
                permission to update.

                This corresponds to the ``permission`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            update_mask (:class:`google.protobuf.field_mask_pb2.FieldMask`):
                Required. The list of fields to update. Accepted ones:

                -  role (``Permission.role`` field)

                This corresponds to the ``update_mask`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.Permission:
                Permission resource grants user,
                group or the rest of the world access to
                the PaLM API resource (e.g. a tuned
                model, corpus).

                A role is a collection of permitted
                operations that allows users to perform
                specific actions on PaLM API resources.
                To make them available to users, groups,
                or service accounts, you assign roles.
                When you assign a role, you grant
                permissions that the role contains.

                There are three concentric roles. Each
                role is a superset of the previous
                role's permitted operations:

                - reader can use the resource (e.g.
                  tuned model, corpus) for inference
                - writer has reader's permissions and
                  additionally can edit and share
                - owner has writer's permissions and
                  additionally can delete

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([permission, update_mask])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, permission_service.UpdatePermissionRequest):
            request = permission_service.UpdatePermissionRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if permission is not None:
            request.permission = permission
        if update_mask is not None:
            request.update_mask = update_mask

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.update_permission
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata(
                (("permission.name", request.permission.name),)
            ),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def delete_permission(
        self,
        request: Optional[
            Union[permission_service.DeletePermissionRequest, dict]
        ] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> None:
        r"""Deletes the permission.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_delete_permission():
                # Create a client
                client = generativelanguage_v1beta.PermissionServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.DeletePermissionRequest(
                    name="name_value",
                )

                # Make the request
                await client.delete_permission(request=request)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.DeletePermissionRequest, dict]]):
                The request object. Request to delete the ``Permission``.
            name (:class:`str`):
                Required. The resource name of the permission. Formats:
                ``tunedModels/{tuned_model}/permissions/{permission}``
                ``corpora/{corpus}/permissions/{permission}``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([name])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, permission_service.DeletePermissionRequest):
            request = permission_service.DeletePermissionRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if name is not None:
            request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.delete_permission
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

    async def transfer_ownership(
        self,
        request: Optional[
            Union[permission_service.TransferOwnershipRequest, dict]
        ] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> permission_service.TransferOwnershipResponse:
        r"""Transfers ownership of the tuned model.
        This is the only way to change ownership of the tuned
        model. The current owner will be downgraded to writer
        role.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_transfer_ownership():
                # Create a client
                client = generativelanguage_v1beta.PermissionServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.TransferOwnershipRequest(
                    name="name_value",
                    email_address="email_address_value",
                )

                # Make the request
                response = await client.transfer_ownership(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.TransferOwnershipRequest, dict]]):
                The request object. Request to transfer the ownership of
                the tuned model.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.TransferOwnershipResponse:
                Response from TransferOwnership.
        """
        # Create or coerce a protobuf request object.
        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, permission_service.TransferOwnershipRequest):
            request = permission_service.TransferOwnershipRequest(request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.transfer_ownership
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def __aenter__(self) -> "PermissionServiceAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.transport.close()


DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


__all__ = ("PermissionServiceAsyncClient",)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\services\permission_service\async_client.py ===
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
from collections import OrderedDict
import functools
import re
from typing import (
    Callable,
    Dict,
    Mapping,
    MutableMapping,
    MutableSequence,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
)

from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1
from google.api_core import retry_async as retries
from google.api_core.client_options import ClientOptions
from google.auth import credentials as ga_credentials  # type: ignore
from google.oauth2 import service_account  # type: ignore

from google.ai.generativelanguage_v1beta3 import gapic_version as package_version

try:
    OptionalRetry = Union[retries.AsyncRetry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.AsyncRetry, object, None]  # type: ignore

from google.longrunning import operations_pb2  # type: ignore
from google.protobuf import field_mask_pb2  # type: ignore

from google.ai.generativelanguage_v1beta3.services.permission_service import pagers
from google.ai.generativelanguage_v1beta3.types import permission as gag_permission
from google.ai.generativelanguage_v1beta3.types import permission
from google.ai.generativelanguage_v1beta3.types import permission_service

from .client import PermissionServiceClient
from .transports.base import DEFAULT_CLIENT_INFO, PermissionServiceTransport
from .transports.grpc_asyncio import PermissionServiceGrpcAsyncIOTransport


class PermissionServiceAsyncClient:
    """Provides methods for managing permissions to PaLM API
    resources.
    """

    _client: PermissionServiceClient

    # Copy defaults from the synchronous client for use here.
    # Note: DEFAULT_ENDPOINT is deprecated. Use _DEFAULT_ENDPOINT_TEMPLATE instead.
    DEFAULT_ENDPOINT = PermissionServiceClient.DEFAULT_ENDPOINT
    DEFAULT_MTLS_ENDPOINT = PermissionServiceClient.DEFAULT_MTLS_ENDPOINT
    _DEFAULT_ENDPOINT_TEMPLATE = PermissionServiceClient._DEFAULT_ENDPOINT_TEMPLATE
    _DEFAULT_UNIVERSE = PermissionServiceClient._DEFAULT_UNIVERSE

    permission_path = staticmethod(PermissionServiceClient.permission_path)
    parse_permission_path = staticmethod(PermissionServiceClient.parse_permission_path)
    tuned_model_path = staticmethod(PermissionServiceClient.tuned_model_path)
    parse_tuned_model_path = staticmethod(
        PermissionServiceClient.parse_tuned_model_path
    )
    common_billing_account_path = staticmethod(
        PermissionServiceClient.common_billing_account_path
    )
    parse_common_billing_account_path = staticmethod(
        PermissionServiceClient.parse_common_billing_account_path
    )
    common_folder_path = staticmethod(PermissionServiceClient.common_folder_path)
    parse_common_folder_path = staticmethod(
        PermissionServiceClient.parse_common_folder_path
    )
    common_organization_path = staticmethod(
        PermissionServiceClient.common_organization_path
    )
    parse_common_organization_path = staticmethod(
        PermissionServiceClient.parse_common_organization_path
    )
    common_project_path = staticmethod(PermissionServiceClient.common_project_path)
    parse_common_project_path = staticmethod(
        PermissionServiceClient.parse_common_project_path
    )
    common_location_path = staticmethod(PermissionServiceClient.common_location_path)
    parse_common_location_path = staticmethod(
        PermissionServiceClient.parse_common_location_path
    )

    @classmethod
    def from_service_account_info(cls, info: dict, *args, **kwargs):
        """Creates an instance of this client using the provided credentials
            info.

        Args:
            info (dict): The service account private key info.
            args: Additional arguments to pass to the constructor.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            PermissionServiceAsyncClient: The constructed client.
        """
        return PermissionServiceClient.from_service_account_info.__func__(PermissionServiceAsyncClient, info, *args, **kwargs)  # type: ignore

    @classmethod
    def from_service_account_file(cls, filename: str, *args, **kwargs):
        """Creates an instance of this client using the provided credentials
            file.

        Args:
            filename (str): The path to the service account private key json
                file.
            args: Additional arguments to pass to the constructor.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            PermissionServiceAsyncClient: The constructed client.
        """
        return PermissionServiceClient.from_service_account_file.__func__(PermissionServiceAsyncClient, filename, *args, **kwargs)  # type: ignore

    from_service_account_json = from_service_account_file

    @classmethod
    def get_mtls_endpoint_and_cert_source(
        cls, client_options: Optional[ClientOptions] = None
    ):
        """Return the API endpoint and client cert source for mutual TLS.

        The client cert source is determined in the following order:
        (1) if `GOOGLE_API_USE_CLIENT_CERTIFICATE` environment variable is not "true", the
        client cert source is None.
        (2) if `client_options.client_cert_source` is provided, use the provided one; if the
        default client cert source exists, use the default one; otherwise the client cert
        source is None.

        The API endpoint is determined in the following order:
        (1) if `client_options.api_endpoint` if provided, use the provided one.
        (2) if `GOOGLE_API_USE_CLIENT_CERTIFICATE` environment variable is "always", use the
        default mTLS endpoint; if the environment variable is "never", use the default API
        endpoint; otherwise if client cert source exists, use the default mTLS endpoint, otherwise
        use the default API endpoint.

        More details can be found at https://google.aip.dev/auth/4114.

        Args:
            client_options (google.api_core.client_options.ClientOptions): Custom options for the
                client. Only the `api_endpoint` and `client_cert_source` properties may be used
                in this method.

        Returns:
            Tuple[str, Callable[[], Tuple[bytes, bytes]]]: returns the API endpoint and the
                client cert source to use.

        Raises:
            google.auth.exceptions.MutualTLSChannelError: If any errors happen.
        """
        return PermissionServiceClient.get_mtls_endpoint_and_cert_source(client_options)  # type: ignore

    @property
    def transport(self) -> PermissionServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            PermissionServiceTransport: The transport used by the client instance.
        """
        return self._client.transport

    @property
    def api_endpoint(self):
        """Return the API endpoint used by the client instance.

        Returns:
            str: The API endpoint used by the client instance.
        """
        return self._client._api_endpoint

    @property
    def universe_domain(self) -> str:
        """Return the universe domain used by the client instance.

        Returns:
            str: The universe domain used
                by the client instance.
        """
        return self._client._universe_domain

    get_transport_class = functools.partial(
        type(PermissionServiceClient).get_transport_class, type(PermissionServiceClient)
    )

    def __init__(
        self,
        *,
        credentials: Optional[ga_credentials.Credentials] = None,
        transport: Optional[
            Union[
                str,
                PermissionServiceTransport,
                Callable[..., PermissionServiceTransport],
            ]
        ] = "grpc_asyncio",
        client_options: Optional[ClientOptions] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the permission service async client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,PermissionServiceTransport,Callable[..., PermissionServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport to use.
                If a Callable is given, it will be called with the same set of initialization
                arguments as used in the PermissionServiceTransport constructor.
                If set to None, a transport is chosen automatically.
            client_options (Optional[Union[google.api_core.client_options.ClientOptions, dict]]):
                Custom options for the client.

                1. The ``api_endpoint`` property can be used to override the
                default endpoint provided by the client when ``transport`` is
                not explicitly provided. Only if this property is not set and
                ``transport`` was not explicitly provided, the endpoint is
                determined by the GOOGLE_API_USE_MTLS_ENDPOINT environment
                variable, which have one of the following values:
                "always" (always use the default mTLS endpoint), "never" (always
                use the default regular endpoint) and "auto" (auto-switch to the
                default mTLS endpoint if client certificate is present; this is
                the default value).

                2. If the GOOGLE_API_USE_CLIENT_CERTIFICATE environment variable
                is "true", then the ``client_cert_source`` property can be used
                to provide a client certificate for mTLS transport. If
                not provided, the default SSL client certificate will be used if
                present. If GOOGLE_API_USE_CLIENT_CERTIFICATE is "false" or not
                set, no client certificate will be used.

                3. The ``universe_domain`` property can be used to override the
                default "googleapis.com" universe. Note that ``api_endpoint``
                property still takes precedence; and ``universe_domain`` is
                currently not supported for mTLS.

            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.

        Raises:
            google.auth.exceptions.MutualTlsChannelError: If mutual TLS transport
                creation failed for any reason.
        """
        self._client = PermissionServiceClient(
            credentials=credentials,
            transport=transport,
            client_options=client_options,
            client_info=client_info,
        )

    async def create_permission(
        self,
        request: Optional[
            Union[permission_service.CreatePermissionRequest, dict]
        ] = None,
        *,
        parent: Optional[str] = None,
        permission: Optional[gag_permission.Permission] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> gag_permission.Permission:
        r"""Create a permission to a specific resource.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            async def sample_create_permission():
                # Create a client
                client = generativelanguage_v1beta3.PermissionServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta3.CreatePermissionRequest(
                    parent="parent_value",
                )

                # Make the request
                response = await client.create_permission(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta3.types.CreatePermissionRequest, dict]]):
                The request object. Request to create a ``Permission``.
            parent (:class:`str`):
                Required. The parent resource of the ``Permission``.
                Format: tunedModels/{tuned_model}

                This corresponds to the ``parent`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            permission (:class:`google.ai.generativelanguage_v1beta3.types.Permission`):
                Required. The permission to create.
                This corresponds to the ``permission`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.types.Permission:
                Permission resource grants user,
                group or the rest of the world access to
                the PaLM API resource (e.g. a tuned
                model, file).

                A role is a collection of permitted
                operations that allows users to perform
                specific actions on PaLM API resources.
                To make them available to users, groups,
                or service accounts, you assign roles.
                When you assign a role, you grant
                permissions that the role contains.

                There are three concentric roles. Each
                role is a superset of the previous
                role's permitted operations:

                - reader can use the resource (e.g.
                  tuned model) for inference
                - writer has reader's permissions and
                  additionally can edit and share
                - owner has writer's permissions and
                  additionally can delete

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([parent, permission])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, permission_service.CreatePermissionRequest):
            request = permission_service.CreatePermissionRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if parent is not None:
            request.parent = parent
        if permission is not None:
            request.permission = permission

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.create_permission
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("parent", request.parent),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def get_permission(
        self,
        request: Optional[Union[permission_service.GetPermissionRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> permission.Permission:
        r"""Gets information about a specific Permission.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            async def sample_get_permission():
                # Create a client
                client = generativelanguage_v1beta3.PermissionServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta3.GetPermissionRequest(
                    name="name_value",
                )

                # Make the request
                response = await client.get_permission(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta3.types.GetPermissionRequest, dict]]):
                The request object. Request for getting information about a specific
                ``Permission``.
            name (:class:`str`):
                Required. The resource name of the permission.

                Format:
                ``tunedModels/{tuned_model}permissions/{permission}``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.types.Permission:
                Permission resource grants user,
                group or the rest of the world access to
                the PaLM API resource (e.g. a tuned
                model, file).

                A role is a collection of permitted
                operations that allows users to perform
                specific actions on PaLM API resources.
                To make them available to users, groups,
                or service accounts, you assign roles.
                When you assign a role, you grant
                permissions that the role contains.

                There are three concentric roles. Each
                role is a superset of the previous
                role's permitted operations:

                - reader can use the resource (e.g.
                  tuned model) for inference
                - writer has reader's permissions and
                  additionally can edit and share
                - owner has writer's permissions and
                  additionally can delete

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([name])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, permission_service.GetPermissionRequest):
            request = permission_service.GetPermissionRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if name is not None:
            request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.get_permission
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def list_permissions(
        self,
        request: Optional[
            Union[permission_service.ListPermissionsRequest, dict]
        ] = None,
        *,
        parent: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> pagers.ListPermissionsAsyncPager:
        r"""Lists permissions for the specific resource.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            async def sample_list_permissions():
                # Create a client
                client = generativelanguage_v1beta3.PermissionServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta3.ListPermissionsRequest(
                    parent="parent_value",
                )

                # Make the request
                page_result = client.list_permissions(request=request)

                # Handle the response
                async for response in page_result:
                    print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta3.types.ListPermissionsRequest, dict]]):
                The request object. Request for listing permissions.
            parent (:class:`str`):
                Required. The parent resource of the permissions.
                Format: tunedModels/{tuned_model}

                This corresponds to the ``parent`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.services.permission_service.pagers.ListPermissionsAsyncPager:
                Response from ListPermissions containing a paginated list of
                   permissions.

                Iterating over this object will yield results and
                resolve additional pages automatically.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([parent])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, permission_service.ListPermissionsRequest):
            request = permission_service.ListPermissionsRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if parent is not None:
            request.parent = parent

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.list_permissions
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("parent", request.parent),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # This method is paged; wrap the response in a pager, which provides
        # an `__aiter__` convenience method.
        response = pagers.ListPermissionsAsyncPager(
            method=rpc,
            request=request,
            response=response,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def update_permission(
        self,
        request: Optional[
            Union[permission_service.UpdatePermissionRequest, dict]
        ] = None,
        *,
        permission: Optional[gag_permission.Permission] = None,
        update_mask: Optional[field_mask_pb2.FieldMask] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> gag_permission.Permission:
        r"""Updates the permission.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            async def sample_update_permission():
                # Create a client
                client = generativelanguage_v1beta3.PermissionServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta3.UpdatePermissionRequest(
                )

                # Make the request
                response = await client.update_permission(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta3.types.UpdatePermissionRequest, dict]]):
                The request object. Request to update the ``Permission``.
            permission (:class:`google.ai.generativelanguage_v1beta3.types.Permission`):
                Required. The permission to update.

                The permission's ``name`` field is used to identify the
                permission to update.

                This corresponds to the ``permission`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            update_mask (:class:`google.protobuf.field_mask_pb2.FieldMask`):
                Required. The list of fields to update. Accepted ones:

                -  role (``Permission.role`` field)

                This corresponds to the ``update_mask`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.types.Permission:
                Permission resource grants user,
                group or the rest of the world access to
                the PaLM API resource (e.g. a tuned
                model, file).

                A role is a collection of permitted
                operations that allows users to perform
                specific actions on PaLM API resources.
                To make them available to users, groups,
                or service accounts, you assign roles.
                When you assign a role, you grant
                permissions that the role contains.

                There are three concentric roles. Each
                role is a superset of the previous
                role's permitted operations:

                - reader can use the resource (e.g.
                  tuned model) for inference
                - writer has reader's permissions and
                  additionally can edit and share
                - owner has writer's permissions and
                  additionally can delete

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([permission, update_mask])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, permission_service.UpdatePermissionRequest):
            request = permission_service.UpdatePermissionRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if permission is not None:
            request.permission = permission
        if update_mask is not None:
            request.update_mask = update_mask

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.update_permission
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata(
                (("permission.name", request.permission.name),)
            ),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def delete_permission(
        self,
        request: Optional[
            Union[permission_service.DeletePermissionRequest, dict]
        ] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> None:
        r"""Deletes the permission.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            async def sample_delete_permission():
                # Create a client
                client = generativelanguage_v1beta3.PermissionServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta3.DeletePermissionRequest(
                    name="name_value",
                )

                # Make the request
                await client.delete_permission(request=request)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta3.types.DeletePermissionRequest, dict]]):
                The request object. Request to delete the ``Permission``.
            name (:class:`str`):
                Required. The resource name of the permission. Format:
                ``tunedModels/{tuned_model}/permissions/{permission}``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([name])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, permission_service.DeletePermissionRequest):
            request = permission_service.DeletePermissionRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if name is not None:
            request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.delete_permission
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

    async def transfer_ownership(
        self,
        request: Optional[
            Union[permission_service.TransferOwnershipRequest, dict]
        ] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> permission_service.TransferOwnershipResponse:
        r"""Transfers ownership of the tuned model.
        This is the only way to change ownership of the tuned
        model. The current owner will be downgraded to writer
        role.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            async def sample_transfer_ownership():
                # Create a client
                client = generativelanguage_v1beta3.PermissionServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta3.TransferOwnershipRequest(
                    name="name_value",
                    email_address="email_address_value",
                )

                # Make the request
                response = await client.transfer_ownership(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta3.types.TransferOwnershipRequest, dict]]):
                The request object. Request to transfer the ownership of
                the tuned model.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.types.TransferOwnershipResponse:
                Response from TransferOwnership.
        """
        # Create or coerce a protobuf request object.
        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, permission_service.TransferOwnershipRequest):
            request = permission_service.TransferOwnershipRequest(request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.transfer_ownership
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def __aenter__(self) -> "PermissionServiceAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.transport.close()


DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


__all__ = ("PermissionServiceAsyncClient",)

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\widgets\base.py ===
"""
Collection of reusable components for building full screen applications.

All of these widgets implement the ``__pt_container__`` method, which makes
them usable in any situation where we are expecting a `prompt_toolkit`
container object.

.. warning::

    At this point, the API for these widgets is considered unstable, and can
    potentially change between minor releases (we try not too, but no
    guarantees are made yet). The public API in
    `prompt_toolkit.shortcuts.dialogs` on the other hand is considered stable.
"""

from __future__ import annotations

from functools import partial
from typing import Callable, Generic, Sequence, TypeVar

from prompt_toolkit.application.current import get_app
from prompt_toolkit.auto_suggest import AutoSuggest, DynamicAutoSuggest
from prompt_toolkit.buffer import Buffer, BufferAcceptHandler
from prompt_toolkit.completion import Completer, DynamicCompleter
from prompt_toolkit.document import Document
from prompt_toolkit.filters import (
    Condition,
    FilterOrBool,
    has_focus,
    is_done,
    is_true,
    to_filter,
)
from prompt_toolkit.formatted_text import (
    AnyFormattedText,
    StyleAndTextTuples,
    Template,
    to_formatted_text,
)
from prompt_toolkit.formatted_text.utils import fragment_list_to_text
from prompt_toolkit.history import History
from prompt_toolkit.key_binding.key_bindings import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout.containers import (
    AnyContainer,
    ConditionalContainer,
    Container,
    DynamicContainer,
    Float,
    FloatContainer,
    HSplit,
    VSplit,
    Window,
    WindowAlign,
)
from prompt_toolkit.layout.controls import (
    BufferControl,
    FormattedTextControl,
    GetLinePrefixCallable,
)
from prompt_toolkit.layout.dimension import AnyDimension
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.layout.margins import (
    ConditionalMargin,
    NumberedMargin,
    ScrollbarMargin,
)
from prompt_toolkit.layout.processors import (
    AppendAutoSuggestion,
    BeforeInput,
    ConditionalProcessor,
    PasswordProcessor,
    Processor,
)
from prompt_toolkit.lexers import DynamicLexer, Lexer
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.utils import get_cwidth
from prompt_toolkit.validation import DynamicValidator, Validator

from .toolbars import SearchToolbar

__all__ = [
    "TextArea",
    "Label",
    "Button",
    "Frame",
    "Shadow",
    "Box",
    "VerticalLine",
    "HorizontalLine",
    "RadioList",
    "CheckboxList",
    "Checkbox",  # backward compatibility
    "ProgressBar",
]

E = KeyPressEvent


class Border:
    "Box drawing characters. (Thin)"

    HORIZONTAL = "\u2500"
    VERTICAL = "\u2502"
    TOP_LEFT = "\u250c"
    TOP_RIGHT = "\u2510"
    BOTTOM_LEFT = "\u2514"
    BOTTOM_RIGHT = "\u2518"


class TextArea:
    """
    A simple input field.

    This is a higher level abstraction on top of several other classes with
    sane defaults.

    This widget does have the most common options, but it does not intend to
    cover every single use case. For more configurations options, you can
    always build a text area manually, using a
    :class:`~prompt_toolkit.buffer.Buffer`,
    :class:`~prompt_toolkit.layout.BufferControl` and
    :class:`~prompt_toolkit.layout.Window`.

    Buffer attributes:

    :param text: The initial text.
    :param multiline: If True, allow multiline input.
    :param completer: :class:`~prompt_toolkit.completion.Completer` instance
        for auto completion.
    :param complete_while_typing: Boolean.
    :param accept_handler: Called when `Enter` is pressed (This should be a
        callable that takes a buffer as input).
    :param history: :class:`~prompt_toolkit.history.History` instance.
    :param auto_suggest: :class:`~prompt_toolkit.auto_suggest.AutoSuggest`
        instance for input suggestions.

    BufferControl attributes:

    :param password: When `True`, display using asterisks.
    :param focusable: When `True`, allow this widget to receive the focus.
    :param focus_on_click: When `True`, focus after mouse click.
    :param input_processors: `None` or a list of
        :class:`~prompt_toolkit.layout.Processor` objects.
    :param validator: `None` or a :class:`~prompt_toolkit.validation.Validator`
        object.

    Window attributes:

    :param lexer: :class:`~prompt_toolkit.lexers.Lexer` instance for syntax
        highlighting.
    :param wrap_lines: When `True`, don't scroll horizontally, but wrap lines.
    :param width: Window width. (:class:`~prompt_toolkit.layout.Dimension` object.)
    :param height: Window height. (:class:`~prompt_toolkit.layout.Dimension` object.)
    :param scrollbar: When `True`, display a scroll bar.
    :param style: A style string.
    :param dont_extend_width: When `True`, don't take up more width then the
                              preferred width reported by the control.
    :param dont_extend_height: When `True`, don't take up more width then the
                               preferred height reported by the control.
    :param get_line_prefix: None or a callable that returns formatted text to
        be inserted before a line. It takes a line number (int) and a
        wrap_count and returns formatted text. This can be used for
        implementation of line continuations, things like Vim "breakindent" and
        so on.

    Other attributes:

    :param search_field: An optional `SearchToolbar` object.
    """

    def __init__(
        self,
        text: str = "",
        multiline: FilterOrBool = True,
        password: FilterOrBool = False,
        lexer: Lexer | None = None,
        auto_suggest: AutoSuggest | None = None,
        completer: Completer | None = None,
        complete_while_typing: FilterOrBool = True,
        validator: Validator | None = None,
        accept_handler: BufferAcceptHandler | None = None,
        history: History | None = None,
        focusable: FilterOrBool = True,
        focus_on_click: FilterOrBool = False,
        wrap_lines: FilterOrBool = True,
        read_only: FilterOrBool = False,
        width: AnyDimension = None,
        height: AnyDimension = None,
        dont_extend_height: FilterOrBool = False,
        dont_extend_width: FilterOrBool = False,
        line_numbers: bool = False,
        get_line_prefix: GetLinePrefixCallable | None = None,
        scrollbar: bool = False,
        style: str = "",
        search_field: SearchToolbar | None = None,
        preview_search: FilterOrBool = True,
        prompt: AnyFormattedText = "",
        input_processors: list[Processor] | None = None,
        name: str = "",
    ) -> None:
        if search_field is None:
            search_control = None
        elif isinstance(search_field, SearchToolbar):
            search_control = search_field.control

        if input_processors is None:
            input_processors = []

        # Writeable attributes.
        self.completer = completer
        self.complete_while_typing = complete_while_typing
        self.lexer = lexer
        self.auto_suggest = auto_suggest
        self.read_only = read_only
        self.wrap_lines = wrap_lines
        self.validator = validator

        self.buffer = Buffer(
            document=Document(text, 0),
            multiline=multiline,
            read_only=Condition(lambda: is_true(self.read_only)),
            completer=DynamicCompleter(lambda: self.completer),
            complete_while_typing=Condition(
                lambda: is_true(self.complete_while_typing)
            ),
            validator=DynamicValidator(lambda: self.validator),
            auto_suggest=DynamicAutoSuggest(lambda: self.auto_suggest),
            accept_handler=accept_handler,
            history=history,
            name=name,
        )

        self.control = BufferControl(
            buffer=self.buffer,
            lexer=DynamicLexer(lambda: self.lexer),
            input_processors=[
                ConditionalProcessor(
                    AppendAutoSuggestion(), has_focus(self.buffer) & ~is_done
                ),
                ConditionalProcessor(
                    processor=PasswordProcessor(), filter=to_filter(password)
                ),
                BeforeInput(prompt, style="class:text-area.prompt"),
            ]
            + input_processors,
            search_buffer_control=search_control,
            preview_search=preview_search,
            focusable=focusable,
            focus_on_click=focus_on_click,
        )

        if multiline:
            if scrollbar:
                right_margins = [ScrollbarMargin(display_arrows=True)]
            else:
                right_margins = []
            if line_numbers:
                left_margins = [NumberedMargin()]
            else:
                left_margins = []
        else:
            height = D.exact(1)
            left_margins = []
            right_margins = []

        style = "class:text-area " + style

        # If no height was given, guarantee height of at least 1.
        if height is None:
            height = D(min=1)

        self.window = Window(
            height=height,
            width=width,
            dont_extend_height=dont_extend_height,
            dont_extend_width=dont_extend_width,
            content=self.control,
            style=style,
            wrap_lines=Condition(lambda: is_true(self.wrap_lines)),
            left_margins=left_margins,
            right_margins=right_margins,
            get_line_prefix=get_line_prefix,
        )

    @property
    def text(self) -> str:
        """
        The `Buffer` text.
        """
        return self.buffer.text

    @text.setter
    def text(self, value: str) -> None:
        self.document = Document(value, 0)

    @property
    def document(self) -> Document:
        """
        The `Buffer` document (text + cursor position).
        """
        return self.buffer.document

    @document.setter
    def document(self, value: Document) -> None:
        self.buffer.set_document(value, bypass_readonly=True)

    @property
    def accept_handler(self) -> BufferAcceptHandler | None:
        """
        The accept handler. Called when the user accepts the input.
        """
        return self.buffer.accept_handler

    @accept_handler.setter
    def accept_handler(self, value: BufferAcceptHandler) -> None:
        self.buffer.accept_handler = value

    def __pt_container__(self) -> Container:
        return self.window


class Label:
    """
    Widget that displays the given text. It is not editable or focusable.

    :param text: Text to display. Can be multiline. All value types accepted by
        :class:`prompt_toolkit.layout.FormattedTextControl` are allowed,
        including a callable.
    :param style: A style string.
    :param width: When given, use this width, rather than calculating it from
        the text size.
    :param dont_extend_width: When `True`, don't take up more width than
                              preferred, i.e. the length of the longest line of
                              the text, or value of `width` parameter, if
                              given. `True` by default
    :param dont_extend_height: When `True`, don't take up more width than the
                               preferred height, i.e. the number of lines of
                               the text. `False` by default.
    """

    def __init__(
        self,
        text: AnyFormattedText,
        style: str = "",
        width: AnyDimension = None,
        dont_extend_height: bool = True,
        dont_extend_width: bool = False,
        align: WindowAlign | Callable[[], WindowAlign] = WindowAlign.LEFT,
        # There is no cursor navigation in a label, so it makes sense to always
        # wrap lines by default.
        wrap_lines: FilterOrBool = True,
    ) -> None:
        self.text = text

        def get_width() -> AnyDimension:
            if width is None:
                text_fragments = to_formatted_text(self.text)
                text = fragment_list_to_text(text_fragments)
                if text:
                    longest_line = max(get_cwidth(line) for line in text.splitlines())
                else:
                    return D(preferred=0)
                return D(preferred=longest_line)
            else:
                return width

        self.formatted_text_control = FormattedTextControl(text=lambda: self.text)

        self.window = Window(
            content=self.formatted_text_control,
            width=get_width,
            height=D(min=1),
            style="class:label " + style,
            dont_extend_height=dont_extend_height,
            dont_extend_width=dont_extend_width,
            align=align,
            wrap_lines=wrap_lines,
        )

    def __pt_container__(self) -> Container:
        return self.window


class Button:
    """
    Clickable button.

    :param text: The caption for the button.
    :param handler: `None` or callable. Called when the button is clicked. No
        parameters are passed to this callable. Use for instance Python's
        `functools.partial` to pass parameters to this callable if needed.
    :param width: Width of the button.
    """

    def __init__(
        self,
        text: str,
        handler: Callable[[], None] | None = None,
        width: int = 12,
        left_symbol: str = "<",
        right_symbol: str = ">",
    ) -> None:
        self.text = text
        self.left_symbol = left_symbol
        self.right_symbol = right_symbol
        self.handler = handler
        self.width = width
        self.control = FormattedTextControl(
            self._get_text_fragments,
            key_bindings=self._get_key_bindings(),
            focusable=True,
        )

        def get_style() -> str:
            if get_app().layout.has_focus(self):
                return "class:button.focused"
            else:
                return "class:button"

        # Note: `dont_extend_width` is False, because we want to allow buttons
        #       to take more space if the parent container provides more space.
        #       Otherwise, we will also truncate the text.
        #       Probably we need a better way here to adjust to width of the
        #       button to the text.

        self.window = Window(
            self.control,
            align=WindowAlign.CENTER,
            height=1,
            width=width,
            style=get_style,
            dont_extend_width=False,
            dont_extend_height=True,
        )

    def _get_text_fragments(self) -> StyleAndTextTuples:
        width = self.width - (
            get_cwidth(self.left_symbol) + get_cwidth(self.right_symbol)
        )
        text = (f"{{:^{width}}}").format(self.text)

        def handler(mouse_event: MouseEvent) -> None:
            if (
                self.handler is not None
                and mouse_event.event_type == MouseEventType.MOUSE_UP
            ):
                self.handler()

        return [
            ("class:button.arrow", self.left_symbol, handler),
            ("[SetCursorPosition]", ""),
            ("class:button.text", text, handler),
            ("class:button.arrow", self.right_symbol, handler),
        ]

    def _get_key_bindings(self) -> KeyBindings:
        "Key bindings for the Button."
        kb = KeyBindings()

        @kb.add(" ")
        @kb.add("enter")
        def _(event: E) -> None:
            if self.handler is not None:
                self.handler()

        return kb

    def __pt_container__(self) -> Container:
        return self.window


class Frame:
    """
    Draw a border around any container, optionally with a title text.

    Changing the title and body of the frame is possible at runtime by
    assigning to the `body` and `title` attributes of this class.

    :param body: Another container object.
    :param title: Text to be displayed in the top of the frame (can be formatted text).
    :param style: Style string to be applied to this widget.
    """

    def __init__(
        self,
        body: AnyContainer,
        title: AnyFormattedText = "",
        style: str = "",
        width: AnyDimension = None,
        height: AnyDimension = None,
        key_bindings: KeyBindings | None = None,
        modal: bool = False,
    ) -> None:
        self.title = title
        self.body = body

        fill = partial(Window, style="class:frame.border")
        style = "class:frame " + style

        top_row_with_title = VSplit(
            [
                fill(width=1, height=1, char=Border.TOP_LEFT),
                fill(char=Border.HORIZONTAL),
                fill(width=1, height=1, char="|"),
                # Notice: we use `Template` here, because `self.title` can be an
                # `HTML` object for instance.
                Label(
                    lambda: Template(" {} ").format(self.title),
                    style="class:frame.label",
                    dont_extend_width=True,
                ),
                fill(width=1, height=1, char="|"),
                fill(char=Border.HORIZONTAL),
                fill(width=1, height=1, char=Border.TOP_RIGHT),
            ],
            height=1,
        )

        top_row_without_title = VSplit(
            [
                fill(width=1, height=1, char=Border.TOP_LEFT),
                fill(char=Border.HORIZONTAL),
                fill(width=1, height=1, char=Border.TOP_RIGHT),
            ],
            height=1,
        )

        @Condition
        def has_title() -> bool:
            return bool(self.title)

        self.container = HSplit(
            [
                ConditionalContainer(content=top_row_with_title, filter=has_title),
                ConditionalContainer(content=top_row_without_title, filter=~has_title),
                VSplit(
                    [
                        fill(width=1, char=Border.VERTICAL),
                        DynamicContainer(lambda: self.body),
                        fill(width=1, char=Border.VERTICAL),
                        # Padding is required to make sure that if the content is
                        # too small, the right frame border is still aligned.
                    ],
                    padding=0,
                ),
                VSplit(
                    [
                        fill(width=1, height=1, char=Border.BOTTOM_LEFT),
                        fill(char=Border.HORIZONTAL),
                        fill(width=1, height=1, char=Border.BOTTOM_RIGHT),
                    ],
                    # specifying height here will increase the rendering speed.
                    height=1,
                ),
            ],
            width=width,
            height=height,
            style=style,
            key_bindings=key_bindings,
            modal=modal,
        )

    def __pt_container__(self) -> Container:
        return self.container


class Shadow:
    """
    Draw a shadow underneath/behind this container.
    (This applies `class:shadow` the the cells under the shadow. The Style
    should define the colors for the shadow.)

    :param body: Another container object.
    """

    def __init__(self, body: AnyContainer) -> None:
        self.container = FloatContainer(
            content=body,
            floats=[
                Float(
                    bottom=-1,
                    height=1,
                    left=1,
                    right=-1,
                    transparent=True,
                    content=Window(style="class:shadow"),
                ),
                Float(
                    bottom=-1,
                    top=1,
                    width=1,
                    right=-1,
                    transparent=True,
                    content=Window(style="class:shadow"),
                ),
            ],
        )

    def __pt_container__(self) -> Container:
        return self.container


class Box:
    """
    Add padding around a container.

    This also makes sure that the parent can provide more space than required by
    the child. This is very useful when wrapping a small element with a fixed
    size into a ``VSplit`` or ``HSplit`` object. The ``HSplit`` and ``VSplit``
    try to make sure to adapt respectively the width and height, possibly
    shrinking other elements. Wrapping something in a ``Box`` makes it flexible.

    :param body: Another container object.
    :param padding: The margin to be used around the body. This can be
        overridden by `padding_left`, padding_right`, `padding_top` and
        `padding_bottom`.
    :param style: A style string.
    :param char: Character to be used for filling the space around the body.
        (This is supposed to be a character with a terminal width of 1.)
    """

    def __init__(
        self,
        body: AnyContainer,
        padding: AnyDimension = None,
        padding_left: AnyDimension = None,
        padding_right: AnyDimension = None,
        padding_top: AnyDimension = None,
        padding_bottom: AnyDimension = None,
        width: AnyDimension = None,
        height: AnyDimension = None,
        style: str = "",
        char: None | str | Callable[[], str] = None,
        modal: bool = False,
        key_bindings: KeyBindings | None = None,
    ) -> None:
        self.padding = padding
        self.padding_left = padding_left
        self.padding_right = padding_right
        self.padding_top = padding_top
        self.padding_bottom = padding_bottom
        self.body = body

        def left() -> AnyDimension:
            if self.padding_left is None:
                return self.padding
            return self.padding_left

        def right() -> AnyDimension:
            if self.padding_right is None:
                return self.padding
            return self.padding_right

        def top() -> AnyDimension:
            if self.padding_top is None:
                return self.padding
            return self.padding_top

        def bottom() -> AnyDimension:
            if self.padding_bottom is None:
                return self.padding
            return self.padding_bottom

        self.container = HSplit(
            [
                Window(height=top, char=char),
                VSplit(
                    [
                        Window(width=left, char=char),
                        body,
                        Window(width=right, char=char),
                    ]
                ),
                Window(height=bottom, char=char),
            ],
            width=width,
            height=height,
            style=style,
            modal=modal,
            key_bindings=None,
        )

    def __pt_container__(self) -> Container:
        return self.container


_T = TypeVar("_T")


class _DialogList(Generic[_T]):
    """
    Common code for `RadioList` and `CheckboxList`.
    """

    open_character: str = ""
    close_character: str = ""
    container_style: str = ""
    default_style: str = ""
    selected_style: str = ""
    checked_style: str = ""
    multiple_selection: bool = False
    show_scrollbar: bool = True

    def __init__(
        self,
        values: Sequence[tuple[_T, AnyFormattedText]],
        default_values: Sequence[_T] | None = None,
    ) -> None:
        assert len(values) > 0
        default_values = default_values or []

        self.values = values
        # current_values will be used in multiple_selection,
        # current_value will be used otherwise.
        keys: list[_T] = [value for (value, _) in values]
        self.current_values: list[_T] = [
            value for value in default_values if value in keys
        ]
        self.current_value: _T = (
            default_values[0]
            if len(default_values) and default_values[0] in keys
            else values[0][0]
        )

        # Cursor index: take first selected item or first item otherwise.
        if len(self.current_values) > 0:
            self._selected_index = keys.index(self.current_values[0])
        else:
            self._selected_index = 0

        # Key bindings.
        kb = KeyBindings()

        @kb.add("up")
        def _up(event: E) -> None:
            self._selected_index = max(0, self._selected_index - 1)

        @kb.add("down")
        def _down(event: E) -> None:
            self._selected_index = min(len(self.values) - 1, self._selected_index + 1)

        @kb.add("pageup")
        def _pageup(event: E) -> None:
            w = event.app.layout.current_window
            if w.render_info:
                self._selected_index = max(
                    0, self._selected_index - len(w.render_info.displayed_lines)
                )

        @kb.add("pagedown")
        def _pagedown(event: E) -> None:
            w = event.app.layout.current_window
            if w.render_info:
                self._selected_index = min(
                    len(self.values) - 1,
                    self._selected_index + len(w.render_info.displayed_lines),
                )

        @kb.add("enter")
        @kb.add(" ")
        def _click(event: E) -> None:
            self._handle_enter()

        @kb.add(Keys.Any)
        def _find(event: E) -> None:
            # We first check values after the selected value, then all values.
            values = list(self.values)
            for value in values[self._selected_index + 1 :] + values:
                text = fragment_list_to_text(to_formatted_text(value[1])).lower()

                if text.startswith(event.data.lower()):
                    self._selected_index = self.values.index(value)
                    return

        # Control and window.
        self.control = FormattedTextControl(
            self._get_text_fragments, key_bindings=kb, focusable=True
        )

        self.window = Window(
            content=self.control,
            style=self.container_style,
            right_margins=[
                ConditionalMargin(
                    margin=ScrollbarMargin(display_arrows=True),
                    filter=Condition(lambda: self.show_scrollbar),
                ),
            ],
            dont_extend_height=True,
        )

    def _handle_enter(self) -> None:
        if self.multiple_selection:
            val = self.values[self._selected_index][0]
            if val in self.current_values:
                self.current_values.remove(val)
            else:
                self.current_values.append(val)
        else:
            self.current_value = self.values[self._selected_index][0]

    def _get_text_fragments(self) -> StyleAndTextTuples:
        def mouse_handler(mouse_event: MouseEvent) -> None:
            """
            Set `_selected_index` and `current_value` according to the y
            position of the mouse click event.
            """
            if mouse_event.event_type == MouseEventType.MOUSE_UP:
                self._selected_index = mouse_event.position.y
                self._handle_enter()

        result: StyleAndTextTuples = []
        for i, value in enumerate(self.values):
            if self.multiple_selection:
                checked = value[0] in self.current_values
            else:
                checked = value[0] == self.current_value
            selected = i == self._selected_index

            style = ""
            if checked:
                style += " " + self.checked_style
            if selected:
                style += " " + self.selected_style

            result.append((style, self.open_character))

            if selected:
                result.append(("[SetCursorPosition]", ""))

            if checked:
                result.append((style, "*"))
            else:
                result.append((style, " "))

            result.append((style, self.close_character))
            result.append((self.default_style, " "))
            result.extend(to_formatted_text(value[1], style=self.default_style))
            result.append(("", "\n"))

        # Add mouse handler to all fragments.
        for i in range(len(result)):
            result[i] = (result[i][0], result[i][1], mouse_handler)

        result.pop()  # Remove last newline.
        return result

    def __pt_container__(self) -> Container:
        return self.window


class RadioList(_DialogList[_T]):
    """
    List of radio buttons. Only one can be checked at the same time.

    :param values: List of (value, label) tuples.
    """

    open_character = "("
    close_character = ")"
    container_style = "class:radio-list"
    default_style = "class:radio"
    selected_style = "class:radio-selected"
    checked_style = "class:radio-checked"
    multiple_selection = False

    def __init__(
        self,
        values: Sequence[tuple[_T, AnyFormattedText]],
        default: _T | None = None,
    ) -> None:
        if default is None:
            default_values = None
        else:
            default_values = [default]

        super().__init__(values, default_values=default_values)


class CheckboxList(_DialogList[_T]):
    """
    List of checkbox buttons. Several can be checked at the same time.

    :param values: List of (value, label) tuples.
    """

    open_character = "["
    close_character = "]"
    container_style = "class:checkbox-list"
    default_style = "class:checkbox"
    selected_style = "class:checkbox-selected"
    checked_style = "class:checkbox-checked"
    multiple_selection = True


class Checkbox(CheckboxList[str]):
    """Backward compatibility util: creates a 1-sized CheckboxList

    :param text: the text
    """

    show_scrollbar = False

    def __init__(self, text: AnyFormattedText = "", checked: bool = False) -> None:
        values = [("value", text)]
        super().__init__(values=values)
        self.checked = checked

    @property
    def checked(self) -> bool:
        return "value" in self.current_values

    @checked.setter
    def checked(self, value: bool) -> None:
        if value:
            self.current_values = ["value"]
        else:
            self.current_values = []


class VerticalLine:
    """
    A simple vertical line with a width of 1.
    """

    def __init__(self) -> None:
        self.window = Window(
            char=Border.VERTICAL, style="class:line,vertical-line", width=1
        )

    def __pt_container__(self) -> Container:
        return self.window


class HorizontalLine:
    """
    A simple horizontal line with a height of 1.
    """

    def __init__(self) -> None:
        self.window = Window(
            char=Border.HORIZONTAL, style="class:line,horizontal-line", height=1
        )

    def __pt_container__(self) -> Container:
        return self.window


class ProgressBar:
    def __init__(self) -> None:
        self._percentage = 60

        self.label = Label("60%")
        self.container = FloatContainer(
            content=Window(height=1),
            floats=[
                # We first draw the label, then the actual progress bar.  Right
                # now, this is the only way to have the colors of the progress
                # bar appear on top of the label. The problem is that our label
                # can't be part of any `Window` below.
                Float(content=self.label, top=0, bottom=0),
                Float(
                    left=0,
                    top=0,
                    right=0,
                    bottom=0,
                    content=VSplit(
                        [
                            Window(
                                style="class:progress-bar.used",
                                width=lambda: D(weight=int(self._percentage)),
                            ),
                            Window(
                                style="class:progress-bar",
                                width=lambda: D(weight=int(100 - self._percentage)),
                            ),
                        ]
                    ),
                ),
            ],
        )

    @property
    def percentage(self) -> int:
        return self._percentage

    @percentage.setter
    def percentage(self, value: int) -> None:
        self._percentage = value
        self.label.text = f"{value}%"

    def __pt_container__(self) -> Container:
        return self.container

# === NexusCore/openenv\Lib\site-packages\pygments\formatters\html.py ===
"""
    pygments.formatters.html
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Formatter for HTML output.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import functools
import os
import sys
import os.path
from io import StringIO

from pygments.formatter import Formatter
from pygments.token import Token, Text, STANDARD_TYPES
from pygments.util import get_bool_opt, get_int_opt, get_list_opt

try:
    import ctags
except ImportError:
    ctags = None

__all__ = ['HtmlFormatter']


_escape_html_table = {
    ord('&'): '&amp;',
    ord('<'): '&lt;',
    ord('>'): '&gt;',
    ord('"'): '&quot;',
    ord("'"): '&#39;',
}


def escape_html(text, table=_escape_html_table):
    """Escape &, <, > as well as single and double quotes for HTML."""
    return text.translate(table)


def webify(color):
    if color.startswith('calc') or color.startswith('var'):
        return color
    else:
        # Check if the color can be shortened from 6 to 3 characters
        color = color.upper()
        if (len(color) == 6 and
            (    color[0] == color[1]
             and color[2] == color[3]
             and color[4] == color[5])):
            return f'#{color[0]}{color[2]}{color[4]}'
        else:
            return f'#{color}'


def _get_ttype_class(ttype):
    fname = STANDARD_TYPES.get(ttype)
    if fname:
        return fname
    aname = ''
    while fname is None:
        aname = '-' + ttype[-1] + aname
        ttype = ttype.parent
        fname = STANDARD_TYPES.get(ttype)
    return fname + aname


CSSFILE_TEMPLATE = '''\
/*
generated by Pygments <https://pygments.org/>
Copyright 2006-2025 by the Pygments team.
Licensed under the BSD license, see LICENSE for details.
*/
%(styledefs)s
'''

DOC_HEADER = '''\
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN"
   "http://www.w3.org/TR/html4/strict.dtd">
<!--
generated by Pygments <https://pygments.org/>
Copyright 2006-2025 by the Pygments team.
Licensed under the BSD license, see LICENSE for details.
-->
<html>
<head>
  <title>%(title)s</title>
  <meta http-equiv="content-type" content="text/html; charset=%(encoding)s">
  <style type="text/css">
''' + CSSFILE_TEMPLATE + '''
  </style>
</head>
<body>
<h2>%(title)s</h2>

'''

DOC_HEADER_EXTERNALCSS = '''\
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN"
   "http://www.w3.org/TR/html4/strict.dtd">

<html>
<head>
  <title>%(title)s</title>
  <meta http-equiv="content-type" content="text/html; charset=%(encoding)s">
  <link rel="stylesheet" href="%(cssfile)s" type="text/css">
</head>
<body>
<h2>%(title)s</h2>

'''

DOC_FOOTER = '''\
</body>
</html>
'''


class HtmlFormatter(Formatter):
    r"""
    Format tokens as HTML 4 ``<span>`` tags. By default, the content is enclosed
    in a ``<pre>`` tag, itself wrapped in a ``<div>`` tag (but see the `nowrap` option).
    The ``<div>``'s CSS class can be set by the `cssclass` option.

    If the `linenos` option is set to ``"table"``, the ``<pre>`` is
    additionally wrapped inside a ``<table>`` which has one row and two
    cells: one containing the line numbers and one containing the code.
    Example:

    .. sourcecode:: html

        <div class="highlight" >
        <table><tr>
          <td class="linenos" title="click to toggle"
            onclick="with (this.firstChild.style)
                     { display = (display == '') ? 'none' : '' }">
            <pre>1
            2</pre>
          </td>
          <td class="code">
            <pre><span class="Ke">def </span><span class="NaFu">foo</span>(bar):
              <span class="Ke">pass</span>
            </pre>
          </td>
        </tr></table></div>

    (whitespace added to improve clarity).

    A list of lines can be specified using the `hl_lines` option to make these
    lines highlighted (as of Pygments 0.11).

    With the `full` option, a complete HTML 4 document is output, including
    the style definitions inside a ``<style>`` tag, or in a separate file if
    the `cssfile` option is given.

    When `tagsfile` is set to the path of a ctags index file, it is used to
    generate hyperlinks from names to their definition.  You must enable
    `lineanchors` and run ctags with the `-n` option for this to work.  The
    `python-ctags` module from PyPI must be installed to use this feature;
    otherwise a `RuntimeError` will be raised.

    The `get_style_defs(arg='')` method of a `HtmlFormatter` returns a string
    containing CSS rules for the CSS classes used by the formatter. The
    argument `arg` can be used to specify additional CSS selectors that
    are prepended to the classes. A call `fmter.get_style_defs('td .code')`
    would result in the following CSS classes:

    .. sourcecode:: css

        td .code .kw { font-weight: bold; color: #00FF00 }
        td .code .cm { color: #999999 }
        ...

    If you have Pygments 0.6 or higher, you can also pass a list or tuple to the
    `get_style_defs()` method to request multiple prefixes for the tokens:

    .. sourcecode:: python

        formatter.get_style_defs(['div.syntax pre', 'pre.syntax'])

    The output would then look like this:

    .. sourcecode:: css

        div.syntax pre .kw,
        pre.syntax .kw { font-weight: bold; color: #00FF00 }
        div.syntax pre .cm,
        pre.syntax .cm { color: #999999 }
        ...

    Additional options accepted:

    `nowrap`
        If set to ``True``, don't add a ``<pre>`` and a ``<div>`` tag
        around the tokens. This disables most other options (default: ``False``).

    `full`
        Tells the formatter to output a "full" document, i.e. a complete
        self-contained document (default: ``False``).

    `title`
        If `full` is true, the title that should be used to caption the
        document (default: ``''``).

    `style`
        The style to use, can be a string or a Style subclass (default:
        ``'default'``). This option has no effect if the `cssfile`
        and `noclobber_cssfile` option are given and the file specified in
        `cssfile` exists.

    `noclasses`
        If set to true, token ``<span>`` tags (as well as line number elements)
        will not use CSS classes, but inline styles. This is not recommended
        for larger pieces of code since it increases output size by quite a bit
        (default: ``False``).

    `classprefix`
        Since the token types use relatively short class names, they may clash
        with some of your own class names. In this case you can use the
        `classprefix` option to give a string to prepend to all Pygments-generated
        CSS class names for token types.
        Note that this option also affects the output of `get_style_defs()`.

    `cssclass`
        CSS class for the wrapping ``<div>`` tag (default: ``'highlight'``).
        If you set this option, the default selector for `get_style_defs()`
        will be this class.

        .. versionadded:: 0.9
           If you select the ``'table'`` line numbers, the wrapping table will
           have a CSS class of this string plus ``'table'``, the default is
           accordingly ``'highlighttable'``.

    `cssstyles`
        Inline CSS styles for the wrapping ``<div>`` tag (default: ``''``).

    `prestyles`
        Inline CSS styles for the ``<pre>`` tag (default: ``''``).

        .. versionadded:: 0.11

    `cssfile`
        If the `full` option is true and this option is given, it must be the
        name of an external file. If the filename does not include an absolute
        path, the file's path will be assumed to be relative to the main output
        file's path, if the latter can be found. The stylesheet is then written
        to this file instead of the HTML file.

        .. versionadded:: 0.6

    `noclobber_cssfile`
        If `cssfile` is given and the specified file exists, the css file will
        not be overwritten. This allows the use of the `full` option in
        combination with a user specified css file. Default is ``False``.

        .. versionadded:: 1.1

    `linenos`
        If set to ``'table'``, output line numbers as a table with two cells,
        one containing the line numbers, the other the whole code.  This is
        copy-and-paste-friendly, but may cause alignment problems with some
        browsers or fonts.  If set to ``'inline'``, the line numbers will be
        integrated in the ``<pre>`` tag that contains the code (that setting
        is *new in Pygments 0.8*).

        For compatibility with Pygments 0.7 and earlier, every true value
        except ``'inline'`` means the same as ``'table'`` (in particular, that
        means also ``True``).

        The default value is ``False``, which means no line numbers at all.

        **Note:** with the default ("table") line number mechanism, the line
        numbers and code can have different line heights in Internet Explorer
        unless you give the enclosing ``<pre>`` tags an explicit ``line-height``
        CSS property (you get the default line spacing with ``line-height:
        125%``).

    `hl_lines`
        Specify a list of lines to be highlighted. The line numbers are always
        relative to the input (i.e. the first line is line 1) and are
        independent of `linenostart`.

        .. versionadded:: 0.11

    `linenostart`
        The line number for the first line (default: ``1``).

    `linenostep`
        If set to a number n > 1, only every nth line number is printed.

    `linenospecial`
        If set to a number n > 0, every nth line number is given the CSS
        class ``"special"`` (default: ``0``).

    `nobackground`
        If set to ``True``, the formatter won't output the background color
        for the wrapping element (this automatically defaults to ``False``
        when there is no wrapping element [eg: no argument for the
        `get_syntax_defs` method given]) (default: ``False``).

        .. versionadded:: 0.6

    `lineseparator`
        This string is output between lines of code. It defaults to ``"\n"``,
        which is enough to break a line inside ``<pre>`` tags, but you can
        e.g. set it to ``"<br>"`` to get HTML line breaks.

        .. versionadded:: 0.7

    `lineanchors`
        If set to a nonempty string, e.g. ``foo``, the formatter will wrap each
        output line in an anchor tag with an ``id`` (and `name`) of ``foo-linenumber``.
        This allows easy linking to certain lines.

        .. versionadded:: 0.9

    `linespans`
        If set to a nonempty string, e.g. ``foo``, the formatter will wrap each
        output line in a span tag with an ``id`` of ``foo-linenumber``.
        This allows easy access to lines via javascript.

        .. versionadded:: 1.6

    `anchorlinenos`
        If set to `True`, will wrap line numbers in <a> tags. Used in
        combination with `linenos` and `lineanchors`.

    `tagsfile`
        If set to the path of a ctags file, wrap names in anchor tags that
        link to their definitions. `lineanchors` should be used, and the
        tags file should specify line numbers (see the `-n` option to ctags).
        The tags file is assumed to be encoded in UTF-8.

        .. versionadded:: 1.6

    `tagurlformat`
        A string formatting pattern used to generate links to ctags definitions.
        Available variables are `%(path)s`, `%(fname)s` and `%(fext)s`.
        Defaults to an empty string, resulting in just `#prefix-number` links.

        .. versionadded:: 1.6

    `filename`
        A string used to generate a filename when rendering ``<pre>`` blocks,
        for example if displaying source code. If `linenos` is set to
        ``'table'`` then the filename will be rendered in an initial row
        containing a single `<th>` which spans both columns.

        .. versionadded:: 2.1

    `wrapcode`
        Wrap the code inside ``<pre>`` blocks using ``<code>``, as recommended
        by the HTML5 specification.

        .. versionadded:: 2.4

    `debug_token_types`
        Add ``title`` attributes to all token ``<span>`` tags that show the
        name of the token.

        .. versionadded:: 2.10


    **Subclassing the HTML formatter**

    .. versionadded:: 0.7

    The HTML formatter is now built in a way that allows easy subclassing, thus
    customizing the output HTML code. The `format()` method calls
    `self._format_lines()` which returns a generator that yields tuples of ``(1,
    line)``, where the ``1`` indicates that the ``line`` is a line of the
    formatted source code.

    If the `nowrap` option is set, the generator is the iterated over and the
    resulting HTML is output.

    Otherwise, `format()` calls `self.wrap()`, which wraps the generator with
    other generators. These may add some HTML code to the one generated by
    `_format_lines()`, either by modifying the lines generated by the latter,
    then yielding them again with ``(1, line)``, and/or by yielding other HTML
    code before or after the lines, with ``(0, html)``. The distinction between
    source lines and other code makes it possible to wrap the generator multiple
    times.

    The default `wrap()` implementation adds a ``<div>`` and a ``<pre>`` tag.

    A custom `HtmlFormatter` subclass could look like this:

    .. sourcecode:: python

        class CodeHtmlFormatter(HtmlFormatter):

            def wrap(self, source, *, include_div):
                return self._wrap_code(source)

            def _wrap_code(self, source):
                yield 0, '<code>'
                for i, t in source:
                    if i == 1:
                        # it's a line of formatted code
                        t += '<br>'
                    yield i, t
                yield 0, '</code>'

    This results in wrapping the formatted lines with a ``<code>`` tag, where the
    source lines are broken using ``<br>`` tags.

    After calling `wrap()`, the `format()` method also adds the "line numbers"
    and/or "full document" wrappers if the respective options are set. Then, all
    HTML yielded by the wrapped generator is output.
    """

    name = 'HTML'
    aliases = ['html']
    filenames = ['*.html', '*.htm']

    def __init__(self, **options):
        Formatter.__init__(self, **options)
        self.title = self._decodeifneeded(self.title)
        self.nowrap = get_bool_opt(options, 'nowrap', False)
        self.noclasses = get_bool_opt(options, 'noclasses', False)
        self.classprefix = options.get('classprefix', '')
        self.cssclass = self._decodeifneeded(options.get('cssclass', 'highlight'))
        self.cssstyles = self._decodeifneeded(options.get('cssstyles', ''))
        self.prestyles = self._decodeifneeded(options.get('prestyles', ''))
        self.cssfile = self._decodeifneeded(options.get('cssfile', ''))
        self.noclobber_cssfile = get_bool_opt(options, 'noclobber_cssfile', False)
        self.tagsfile = self._decodeifneeded(options.get('tagsfile', ''))
        self.tagurlformat = self._decodeifneeded(options.get('tagurlformat', ''))
        self.filename = self._decodeifneeded(options.get('filename', ''))
        self.wrapcode = get_bool_opt(options, 'wrapcode', False)
        self.span_element_openers = {}
        self.debug_token_types = get_bool_opt(options, 'debug_token_types', False)

        if self.tagsfile:
            if not ctags:
                raise RuntimeError('The "ctags" package must to be installed '
                                   'to be able to use the "tagsfile" feature.')
            self._ctags = ctags.CTags(self.tagsfile)

        linenos = options.get('linenos', False)
        if linenos == 'inline':
            self.linenos = 2
        elif linenos:
            # compatibility with <= 0.7
            self.linenos = 1
        else:
            self.linenos = 0
        self.linenostart = abs(get_int_opt(options, 'linenostart', 1))
        self.linenostep = abs(get_int_opt(options, 'linenostep', 1))
        self.linenospecial = abs(get_int_opt(options, 'linenospecial', 0))
        self.nobackground = get_bool_opt(options, 'nobackground', False)
        self.lineseparator = options.get('lineseparator', '\n')
        self.lineanchors = options.get('lineanchors', '')
        self.linespans = options.get('linespans', '')
        self.anchorlinenos = get_bool_opt(options, 'anchorlinenos', False)
        self.hl_lines = set()
        for lineno in get_list_opt(options, 'hl_lines', []):
            try:
                self.hl_lines.add(int(lineno))
            except ValueError:
                pass

        self._create_stylesheet()

    def _get_css_class(self, ttype):
        """Return the css class of this token type prefixed with
        the classprefix option."""
        ttypeclass = _get_ttype_class(ttype)
        if ttypeclass:
            return self.classprefix + ttypeclass
        return ''

    def _get_css_classes(self, ttype):
        """Return the CSS classes of this token type prefixed with the classprefix option."""
        cls = self._get_css_class(ttype)
        while ttype not in STANDARD_TYPES:
            ttype = ttype.parent
            cls = self._get_css_class(ttype) + ' ' + cls
        return cls or ''

    def _get_css_inline_styles(self, ttype):
        """Return the inline CSS styles for this token type."""
        cclass = self.ttype2class.get(ttype)
        while cclass is None:
            ttype = ttype.parent
            cclass = self.ttype2class.get(ttype)
        return cclass or ''

    def _create_stylesheet(self):
        t2c = self.ttype2class = {Token: ''}
        c2s = self.class2style = {}
        for ttype, ndef in self.style:
            name = self._get_css_class(ttype)
            style = ''
            if ndef['color']:
                style += 'color: {}; '.format(webify(ndef['color']))
            if ndef['bold']:
                style += 'font-weight: bold; '
            if ndef['italic']:
                style += 'font-style: italic; '
            if ndef['underline']:
                style += 'text-decoration: underline; '
            if ndef['bgcolor']:
                style += 'background-color: {}; '.format(webify(ndef['bgcolor']))
            if ndef['border']:
                style += 'border: 1px solid {}; '.format(webify(ndef['border']))
            if style:
                t2c[ttype] = name
                # save len(ttype) to enable ordering the styles by
                # hierarchy (necessary for CSS cascading rules!)
                c2s[name] = (style[:-2], ttype, len(ttype))

    def get_style_defs(self, arg=None):
        """
        Return CSS style definitions for the classes produced by the current
        highlighting style. ``arg`` can be a string or list of selectors to
        insert before the token type classes.
        """
        style_lines = []

        style_lines.extend(self.get_linenos_style_defs())
        style_lines.extend(self.get_background_style_defs(arg))
        style_lines.extend(self.get_token_style_defs(arg))

        return '\n'.join(style_lines)

    def get_token_style_defs(self, arg=None):
        prefix = self.get_css_prefix(arg)

        styles = [
            (level, ttype, cls, style)
            for cls, (style, ttype, level) in self.class2style.items()
            if cls and style
        ]
        styles.sort()

        lines = [
            f'{prefix(cls)} {{ {style} }} /* {repr(ttype)[6:]} */'
            for (level, ttype, cls, style) in styles
        ]

        return lines

    def get_background_style_defs(self, arg=None):
        prefix = self.get_css_prefix(arg)
        bg_color = self.style.background_color
        hl_color = self.style.highlight_color

        lines = []

        if arg and not self.nobackground and bg_color is not None:
            text_style = ''
            if Text in self.ttype2class:
                text_style = ' ' + self.class2style[self.ttype2class[Text]][0]
            lines.insert(
                0, '{}{{ background: {};{} }}'.format(
                    prefix(''), bg_color, text_style
                )
            )
        if hl_color is not None:
            lines.insert(
                0, '{} {{ background-color: {} }}'.format(prefix('hll'), hl_color)
            )

        return lines

    def get_linenos_style_defs(self):
        lines = [
            f'pre {{ {self._pre_style} }}',
            f'td.linenos .normal {{ {self._linenos_style} }}',
            f'span.linenos {{ {self._linenos_style} }}',
            f'td.linenos .special {{ {self._linenos_special_style} }}',
            f'span.linenos.special {{ {self._linenos_special_style} }}',
        ]

        return lines

    def get_css_prefix(self, arg):
        if arg is None:
            arg = ('cssclass' in self.options and '.'+self.cssclass or '')
        if isinstance(arg, str):
            args = [arg]
        else:
            args = list(arg)

        def prefix(cls):
            if cls:
                cls = '.' + cls
            tmp = []
            for arg in args:
                tmp.append((arg and arg + ' ' or '') + cls)
            return ', '.join(tmp)

        return prefix

    @property
    def _pre_style(self):
        return 'line-height: 125%;'

    @property
    def _linenos_style(self):
        color = self.style.line_number_color
        background_color = self.style.line_number_background_color
        return f'color: {color}; background-color: {background_color}; padding-left: 5px; padding-right: 5px;'

    @property
    def _linenos_special_style(self):
        color = self.style.line_number_special_color
        background_color = self.style.line_number_special_background_color
        return f'color: {color}; background-color: {background_color}; padding-left: 5px; padding-right: 5px;'

    def _decodeifneeded(self, value):
        if isinstance(value, bytes):
            if self.encoding:
                return value.decode(self.encoding)
            return value.decode()
        return value

    def _wrap_full(self, inner, outfile):
        if self.cssfile:
            if os.path.isabs(self.cssfile):
                # it's an absolute filename
                cssfilename = self.cssfile
            else:
                try:
                    filename = outfile.name
                    if not filename or filename[0] == '<':
                        # pseudo files, e.g. name == '<fdopen>'
                        raise AttributeError
                    cssfilename = os.path.join(os.path.dirname(filename),
                                               self.cssfile)
                except AttributeError:
                    print('Note: Cannot determine output file name, '
                          'using current directory as base for the CSS file name',
                          file=sys.stderr)
                    cssfilename = self.cssfile
            # write CSS file only if noclobber_cssfile isn't given as an option.
            try:
                if not os.path.exists(cssfilename) or not self.noclobber_cssfile:
                    with open(cssfilename, "w", encoding="utf-8") as cf:
                        cf.write(CSSFILE_TEMPLATE %
                                 {'styledefs': self.get_style_defs('body')})
            except OSError as err:
                err.strerror = 'Error writing CSS file: ' + err.strerror
                raise

            yield 0, (DOC_HEADER_EXTERNALCSS %
                      dict(title=self.title,
                           cssfile=self.cssfile,
                           encoding=self.encoding))
        else:
            yield 0, (DOC_HEADER %
                      dict(title=self.title,
                           styledefs=self.get_style_defs('body'),
                           encoding=self.encoding))

        yield from inner
        yield 0, DOC_FOOTER

    def _wrap_tablelinenos(self, inner):
        dummyoutfile = StringIO()
        lncount = 0
        for t, line in inner:
            if t:
                lncount += 1
            dummyoutfile.write(line)

        fl = self.linenostart
        mw = len(str(lncount + fl - 1))
        sp = self.linenospecial
        st = self.linenostep
        anchor_name = self.lineanchors or self.linespans
        aln = self.anchorlinenos
        nocls = self.noclasses

        lines = []

        for i in range(fl, fl+lncount):
            print_line = i % st == 0
            special_line = sp and i % sp == 0

            if print_line:
                line = '%*d' % (mw, i)
                if aln:
                    line = '<a href="#%s-%d">%s</a>' % (anchor_name, i, line)
            else:
                line = ' ' * mw

            if nocls:
                if special_line:
                    style = f' style="{self._linenos_special_style}"'
                else:
                    style = f' style="{self._linenos_style}"'
            else:
                if special_line:
                    style = ' class="special"'
                else:
                    style = ' class="normal"'

            if style:
                line = f'<span{style}>{line}</span>'

            lines.append(line)

        ls = '\n'.join(lines)

        # If a filename was specified, we can't put it into the code table as it
        # would misalign the line numbers. Hence we emit a separate row for it.
        filename_tr = ""
        if self.filename:
            filename_tr = (
                '<tr><th colspan="2" class="filename">'
                '<span class="filename">' + self.filename + '</span>'
                '</th></tr>')

        # in case you wonder about the seemingly redundant <div> here: since the
        # content in the other cell also is wrapped in a div, some browsers in
        # some configurations seem to mess up the formatting...
        yield 0, (f'<table class="{self.cssclass}table">' + filename_tr +
            '<tr><td class="linenos"><div class="linenodiv"><pre>' +
            ls + '</pre></div></td><td class="code">')
        yield 0, '<div>'
        yield 0, dummyoutfile.getvalue()
        yield 0, '</div>'
        yield 0, '</td></tr></table>'


    def _wrap_inlinelinenos(self, inner):
        # need a list of lines since we need the width of a single number :(
        inner_lines = list(inner)
        sp = self.linenospecial
        st = self.linenostep
        num = self.linenostart
        mw = len(str(len(inner_lines) + num - 1))
        anchor_name = self.lineanchors or self.linespans
        aln = self.anchorlinenos
        nocls = self.noclasses

        for _, inner_line in inner_lines:
            print_line = num % st == 0
            special_line = sp and num % sp == 0

            if print_line:
                line = '%*d' % (mw, num)
            else:
                line = ' ' * mw

            if nocls:
                if special_line:
                    style = f' style="{self._linenos_special_style}"'
                else:
                    style = f' style="{self._linenos_style}"'
            else:
                if special_line:
                    style = ' class="linenos special"'
                else:
                    style = ' class="linenos"'

            if style:
                linenos = f'<span{style}>{line}</span>'
            else:
                linenos = line

            if aln:
                yield 1, ('<a href="#%s-%d">%s</a>' % (anchor_name, num, linenos) +
                          inner_line)
            else:
                yield 1, linenos + inner_line
            num += 1

    def _wrap_lineanchors(self, inner):
        s = self.lineanchors
        # subtract 1 since we have to increment i *before* yielding
        i = self.linenostart - 1
        for t, line in inner:
            if t:
                i += 1
                href = "" if self.linenos else ' href="#%s-%d"' % (s, i)
                yield 1, '<a id="%s-%d" name="%s-%d"%s></a>' % (s, i, s, i, href) + line
            else:
                yield 0, line

    def _wrap_linespans(self, inner):
        s = self.linespans
        i = self.linenostart - 1
        for t, line in inner:
            if t:
                i += 1
                yield 1, '<span id="%s-%d">%s</span>' % (s, i, line)
            else:
                yield 0, line

    def _wrap_div(self, inner):
        style = []
        if (self.noclasses and not self.nobackground and
                self.style.background_color is not None):
            style.append(f'background: {self.style.background_color}')
        if self.cssstyles:
            style.append(self.cssstyles)
        style = '; '.join(style)

        yield 0, ('<div' + (self.cssclass and f' class="{self.cssclass}"') +
                  (style and (f' style="{style}"')) + '>')
        yield from inner
        yield 0, '</div>\n'

    def _wrap_pre(self, inner):
        style = []
        if self.prestyles:
            style.append(self.prestyles)
        if self.noclasses:
            style.append(self._pre_style)
        style = '; '.join(style)

        if self.filename and self.linenos != 1:
            yield 0, ('<span class="filename">' + self.filename + '</span>')

        # the empty span here is to keep leading empty lines from being
        # ignored by HTML parsers
        yield 0, ('<pre' + (style and f' style="{style}"') + '><span></span>')
        yield from inner
        yield 0, '</pre>'

    def _wrap_code(self, inner):
        yield 0, '<code>'
        yield from inner
        yield 0, '</code>'

    @functools.lru_cache(maxsize=100)
    def _translate_parts(self, value):
        """HTML-escape a value and split it by newlines."""
        return value.translate(_escape_html_table).split('\n')

    def _format_lines(self, tokensource):
        """
        Just format the tokens, without any wrapping tags.
        Yield individual lines.
        """
        nocls = self.noclasses
        lsep = self.lineseparator
        tagsfile = self.tagsfile

        lspan = ''
        line = []
        for ttype, value in tokensource:
            try:
                cspan = self.span_element_openers[ttype]
            except KeyError:
                title = ' title="{}"'.format('.'.join(ttype)) if self.debug_token_types else ''
                if nocls:
                    css_style = self._get_css_inline_styles(ttype)
                    if css_style:
                        css_style = self.class2style[css_style][0]
                        cspan = f'<span style="{css_style}"{title}>'
                    else:
                        cspan = ''
                else:
                    css_class = self._get_css_classes(ttype)
                    if css_class:
                        cspan = f'<span class="{css_class}"{title}>'
                    else:
                        cspan = ''
                self.span_element_openers[ttype] = cspan

            parts = self._translate_parts(value)

            if tagsfile and ttype in Token.Name:
                filename, linenumber = self._lookup_ctag(value)
                if linenumber:
                    base, filename = os.path.split(filename)
                    if base:
                        base += '/'
                    filename, extension = os.path.splitext(filename)
                    url = self.tagurlformat % {'path': base, 'fname': filename,
                                               'fext': extension}
                    parts[0] = "<a href=\"%s#%s-%d\">%s" % \
                        (url, self.lineanchors, linenumber, parts[0])
                    parts[-1] = parts[-1] + "</a>"

            # for all but the last line
            for part in parts[:-1]:
                if line:
                    # Also check for part being non-empty, so we avoid creating
                    # empty <span> tags
                    if lspan != cspan and part:
                        line.extend(((lspan and '</span>'), cspan, part,
                                     (cspan and '</span>'), lsep))
                    else:  # both are the same, or the current part was empty
                        line.extend((part, (lspan and '</span>'), lsep))
                    yield 1, ''.join(line)
                    line = []
                elif part:
                    yield 1, ''.join((cspan, part, (cspan and '</span>'), lsep))
                else:
                    yield 1, lsep
            # for the last line
            if line and parts[-1]:
                if lspan != cspan:
                    line.extend(((lspan and '</span>'), cspan, parts[-1]))
                    lspan = cspan
                else:
                    line.append(parts[-1])
            elif parts[-1]:
                line = [cspan, parts[-1]]
                lspan = cspan
            # else we neither have to open a new span nor set lspan

        if line:
            line.extend(((lspan and '</span>'), lsep))
            yield 1, ''.join(line)

    def _lookup_ctag(self, token):
        entry = ctags.TagEntry()
        if self._ctags.find(entry, token.encode(), 0):
            return entry['file'].decode(), entry['lineNumber']
        else:
            return None, None

    def _highlight_lines(self, tokensource):
        """
        Highlighted the lines specified in the `hl_lines` option by
        post-processing the token stream coming from `_format_lines`.
        """
        hls = self.hl_lines

        for i, (t, value) in enumerate(tokensource):
            if t != 1:
                yield t, value
            if i + 1 in hls:  # i + 1 because Python indexes start at 0
                if self.noclasses:
                    style = ''
                    if self.style.highlight_color is not None:
                        style = (f' style="background-color: {self.style.highlight_color}"')
                    yield 1, f'<span{style}>{value}</span>'
                else:
                    yield 1, f'<span class="hll">{value}</span>'
            else:
                yield 1, value

    def wrap(self, source):
        """
        Wrap the ``source``, which is a generator yielding
        individual lines, in custom generators. See docstring
        for `format`. Can be overridden.
        """

        output = source
        if self.wrapcode:
            output = self._wrap_code(output)

        output = self._wrap_pre(output)

        return output

    def format_unencoded(self, tokensource, outfile):
        """
        The formatting process uses several nested generators; which of
        them are used is determined by the user's options.

        Each generator should take at least one argument, ``inner``,
        and wrap the pieces of text generated by this.

        Always yield 2-tuples: (code, text). If "code" is 1, the text
        is part of the original tokensource being highlighted, if it's
        0, the text is some piece of wrapping. This makes it possible to
        use several different wrappers that process the original source
        linewise, e.g. line number generators.
        """
        source = self._format_lines(tokensource)

        # As a special case, we wrap line numbers before line highlighting
        # so the line numbers get wrapped in the highlighting tag.
        if not self.nowrap and self.linenos == 2:
            source = self._wrap_inlinelinenos(source)

        if self.hl_lines:
            source = self._highlight_lines(source)

        if not self.nowrap:
            if self.lineanchors:
                source = self._wrap_lineanchors(source)
            if self.linespans:
                source = self._wrap_linespans(source)
            source = self.wrap(source)
            if self.linenos == 1:
                source = self._wrap_tablelinenos(source)
            source = self._wrap_div(source)
            if self.full:
                source = self._wrap_full(source, outfile)

        for t, piece in source:
            outfile.write(piece)

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\framework\interact.py ===
##################################################################
##
## Interactive Shell Window
##

import array
import code
import os
import string
import sys
import traceback

import __main__
import pywin.framework.app
import pywin.scintilla.control
import pywin.scintilla.formatter
import pywin.scintilla.IDLEenvironment  # nopycln: import # Injects fast_readline into the IDLE auto-indent extension
import win32api
import win32clipboard
import win32con
import win32ui
from pywin.mfc import afxres

## sequential after ID_GOTO_LINE defined in editor.py
ID_EDIT_COPY_CODE = 0xE2002
ID_EDIT_EXEC_CLIPBOARD = 0x2003

trace = pywin.scintilla.formatter.trace

import re

from . import winout

# from IDLE.
_is_block_opener = re.compile(r":\s*(#.*)?$").search
_is_block_closer = re.compile(
    r"""
    \s*
    ( return
    | break
    | continue
    | raise
    | pass
    )
    \b
""",
    re.VERBOSE,
).match

tracebackHeader = b"Traceback ("

sectionProfile = "Interactive Window"
valueFormatTitle = "FormatTitle"
valueFormatInput = "FormatInput"
valueFormatOutput = "FormatOutput"
valueFormatOutputError = "FormatOutputError"

# These are defaults only.  Values are read from the registry.
formatTitle = (-536870897, 0, 220, 0, 16711680, 184, 34, "Arial")
formatInput = (-402653169, 0, 200, 0, 0, 0, 49, "Courier New")
formatOutput = (-402653169, 0, 200, 0, 8421376, 0, 49, "Courier New")
formatOutputError = (-402653169, 0, 200, 0, 255, 0, 49, "Courier New")

try:
    sys.ps1
except AttributeError:
    sys.ps1 = ">>> "
    sys.ps2 = "... "


def LoadPreference(preference, default=""):
    return win32ui.GetProfileVal(sectionProfile, preference, default)


def SavePreference(prefName, prefValue):
    win32ui.WriteProfileVal(sectionProfile, prefName, prefValue)


def SaveFontPreferences():
    win32ui.WriteProfileVal(sectionProfile, valueFormatTitle, str(formatTitle))
    win32ui.WriteProfileVal(sectionProfile, valueFormatInput, str(formatInput))
    win32ui.WriteProfileVal(sectionProfile, valueFormatOutput, str(formatOutput))
    win32ui.WriteProfileVal(
        sectionProfile, valueFormatOutputError, str(formatOutputError)
    )


def GetPromptPrefix(line):
    ps1 = sys.ps1
    if line[: len(ps1)] == ps1:
        return ps1
    ps2 = sys.ps2
    if line[: len(ps2)] == ps2:
        return ps2


#############################################################
#
# Colorizer related code.
#
#############################################################
STYLE_INTERACTIVE_EOL = "Interactive EOL"
STYLE_INTERACTIVE_OUTPUT = "Interactive Output"
STYLE_INTERACTIVE_PROMPT = "Interactive Prompt"
STYLE_INTERACTIVE_BANNER = "Interactive Banner"
STYLE_INTERACTIVE_ERROR = "Interactive Error"
STYLE_INTERACTIVE_ERROR_FINALLINE = "Interactive Error (final line)"

INTERACTIVE_STYLES = [
    STYLE_INTERACTIVE_EOL,
    STYLE_INTERACTIVE_OUTPUT,
    STYLE_INTERACTIVE_PROMPT,
    STYLE_INTERACTIVE_BANNER,
    STYLE_INTERACTIVE_ERROR,
    STYLE_INTERACTIVE_ERROR_FINALLINE,
]

FormatterParent = pywin.scintilla.formatter.PythonSourceFormatter


class InteractiveFormatter(FormatterParent):
    def __init__(self, scintilla):
        FormatterParent.__init__(self, scintilla)
        self.bannerDisplayed = False

    def SetStyles(self):
        FormatterParent.SetStyles(self)
        Style = pywin.scintilla.formatter.Style
        self.RegisterStyle(Style(STYLE_INTERACTIVE_EOL, STYLE_INTERACTIVE_PROMPT))
        self.RegisterStyle(Style(STYLE_INTERACTIVE_PROMPT, formatInput))
        self.RegisterStyle(Style(STYLE_INTERACTIVE_OUTPUT, formatOutput))
        self.RegisterStyle(Style(STYLE_INTERACTIVE_BANNER, formatTitle))
        self.RegisterStyle(Style(STYLE_INTERACTIVE_ERROR, formatOutputError))
        self.RegisterStyle(
            Style(STYLE_INTERACTIVE_ERROR_FINALLINE, STYLE_INTERACTIVE_ERROR)
        )

    def LoadPreference(self, name, default):
        rc = win32ui.GetProfileVal("Format", name, default)
        if rc == default:
            rc = win32ui.GetProfileVal(sectionProfile, name, default)
        return rc

    def ColorizeInteractiveCode(self, cdoc, styleStart, stylePyStart):
        lengthDoc = len(cdoc)
        if lengthDoc == 0:
            return
        state = styleStart
        # As per comments in Colorize(), we work with the raw utf8
        # bytes. To avoid too much pain, we treat each utf8 byte
        # as a latin-1 unicode character - we only use it to compare
        # against ascii chars anyway...
        chNext = cdoc[0:1].decode("latin-1")
        startSeg = 0
        i = 0
        lastState = state  # debug only
        while i < lengthDoc:
            ch = chNext
            chNext = cdoc[i + 1 : i + 2].decode("latin-1")

            # 			trace("ch=%r, i=%d, next=%r, state=%s" % (ch, i, chNext, state))
            if state == STYLE_INTERACTIVE_EOL:
                if ch not in "\r\n":
                    self.ColorSeg(startSeg, i - 1, state)
                    startSeg = i
                    if ch in (str(sys.ps1)[0], str(sys.ps2)[0]):
                        state = STYLE_INTERACTIVE_PROMPT
                    elif cdoc[i : i + len(tracebackHeader)] == tracebackHeader:
                        state = STYLE_INTERACTIVE_ERROR
                    else:
                        state = STYLE_INTERACTIVE_OUTPUT
            elif state == STYLE_INTERACTIVE_PROMPT:
                if ch not in sys.ps1 + sys.ps2 + " ":
                    self.ColorSeg(startSeg, i - 1, state)
                    startSeg = i
                    if ch in "\r\n":
                        state = STYLE_INTERACTIVE_EOL
                    else:
                        state = stylePyStart  # Start coloring Python code.
            elif state in (STYLE_INTERACTIVE_OUTPUT,):
                if ch in "\r\n":
                    self.ColorSeg(startSeg, i - 1, state)
                    startSeg = i
                    state = STYLE_INTERACTIVE_EOL
            elif state == STYLE_INTERACTIVE_ERROR:
                if ch in "\r\n" and chNext and chNext not in string.whitespace:
                    # Everything including me
                    self.ColorSeg(startSeg, i, state)
                    startSeg = i + 1
                    state = STYLE_INTERACTIVE_ERROR_FINALLINE
                elif i == 0 and ch not in string.whitespace:
                    # If we are coloring from the start of a line,
                    # we need this better check for the last line
                    # Color up to not including me
                    self.ColorSeg(startSeg, i - 1, state)
                    startSeg = i
                    state = STYLE_INTERACTIVE_ERROR_FINALLINE
            elif state == STYLE_INTERACTIVE_ERROR_FINALLINE:
                if ch in "\r\n":
                    self.ColorSeg(startSeg, i - 1, state)
                    startSeg = i
                    state = STYLE_INTERACTIVE_EOL
            elif state == STYLE_INTERACTIVE_BANNER:
                if ch in "\r\n" and (chNext == "" or chNext in ">["):
                    # Everything including me
                    self.ColorSeg(startSeg, i - 1, state)
                    startSeg = i
                    state = STYLE_INTERACTIVE_EOL
            else:
                # It is a PythonColorizer state - seek past the end of the line
                # and ask the Python colorizer to color that.
                end = startSeg
                while end < lengthDoc and cdoc[end] not in b"\r\n":
                    end += 1
                self.ColorizePythonCode(cdoc[:end], startSeg, state)
                stylePyStart = self.GetStringStyle(end - 1)
                if stylePyStart is None:
                    stylePyStart = pywin.scintilla.formatter.STYLE_DEFAULT
                else:
                    stylePyStart = stylePyStart.name
                startSeg = end
                i = end - 1  # ready for increment.
                chNext = cdoc[end : end + 1].decode("latin-1")
                state = STYLE_INTERACTIVE_EOL
            if lastState != state:
                lastState = state
            i += 1
        # and the rest
        if startSeg < i:
            self.ColorSeg(startSeg, i - 1, state)

    def Colorize(self, start=0, end=-1):
        # scintilla's formatting is all done in terms of utf, so
        # we work with utf8 bytes instead of unicode.  This magically
        # works as any extended chars found in the utf8 don't change
        # the semantics.
        stringVal = self.scintilla.GetTextRange(start, end, decode=False)
        styleStart = None
        stylePyStart = None
        if start > 1:
            # Likely we are being asked to color from the start of the line.
            # We find the last formatted character on the previous line.
            # If TQString, we continue it.  Otherwise, we reset.
            look = start - 1
            while look and self.scintilla.SCIGetCharAt(look) in "\n\r":
                look -= 1
            if look and look < start - 1:  # Did we find a char before the \n\r sets?
                strstyle = self.GetStringStyle(look)
                quote_char = None
                if strstyle is not None:
                    if strstyle.name == pywin.scintilla.formatter.STYLE_TQSSTRING:
                        quote_char = "'"
                    elif strstyle.name == pywin.scintilla.formatter.STYLE_TQDSTRING:
                        quote_char = '"'
                    if quote_char is not None:
                        # It is a TQS.  If the TQS is not terminated, we
                        # carry the style through.
                        if look > 2:
                            look_str = (
                                self.scintilla.SCIGetCharAt(look - 2)
                                + self.scintilla.SCIGetCharAt(look - 1)
                                + self.scintilla.SCIGetCharAt(look)
                            )
                            if look_str != quote_char * 3:
                                stylePyStart = strstyle.name
        if stylePyStart is None:
            stylePyStart = pywin.scintilla.formatter.STYLE_DEFAULT

        if start > 0:
            stylenum = self.scintilla.SCIGetStyleAt(start - 1)
            styleStart = self.GetStyleByNum(stylenum).name
        elif self.bannerDisplayed:
            styleStart = STYLE_INTERACTIVE_EOL
        else:
            styleStart = STYLE_INTERACTIVE_BANNER
            self.bannerDisplayed = True
        self.scintilla.SCIStartStyling(start, 31)
        self.style_buffer = array.array("b", (0,) * len(stringVal))
        self.ColorizeInteractiveCode(stringVal, styleStart, stylePyStart)
        self.scintilla.SCISetStylingEx(self.style_buffer)
        self.style_buffer = None


###############################################################
#
# This class handles the Python interactive interpreter.
#
# It uses a basic EditWindow, and does all the magic.
# This is triggered by the enter key hander attached by the
# start-up code.  It determines if a command is to be executed
# or continued (ie, emit "... ") by snooping around the current
# line, looking for the prompts
#
class PythonwinInteractiveInterpreter(code.InteractiveInterpreter):
    def __init__(self, locals=None, globals=None):
        if locals is None:
            locals = __main__.__dict__
        if globals is None:
            globals = locals
        self.globals = globals
        code.InteractiveInterpreter.__init__(self, locals)

    def showsyntaxerror(self, filename=None, **kwargs):
        sys.stderr.write(
            tracebackHeader.decode("ascii")
        )  # So the color syntaxer recognises it.
        code.InteractiveInterpreter.showsyntaxerror(self, filename)

    def runcode(self, code):
        try:
            exec(code, self.globals, self.locals)
        except SystemExit:
            raise
        except:
            self.showtraceback()


class InteractiveCore:
    def __init__(self, banner=None):
        self.banner = banner

    # 		LoadFontPreferences()
    def Init(self):
        self.oldStdOut = self.oldStdErr = None

        # 		self.SetWordWrap(win32ui.CRichEditView_WrapNone)
        self.interp = PythonwinInteractiveInterpreter()

        self.OutputGrab()  # Release at cleanup.

        if self.GetTextLength() == 0:
            if self.banner is None:
                suffix = ""
                if win32ui.debug:
                    suffix = ", debug build"
                sys.stderr.write(
                    f"PythonWin {sys.version} on {sys.platform}{suffix}.\n"
                )
                sys.stderr.write(
                    "Portions {} - see 'Help/About PythonWin' for further copyright information.\n".format(
                        win32ui.copyright
                    )
                )
            else:
                sys.stderr.write(self.banner)
        rcfile = os.environ.get("PYTHONSTARTUP")
        if rcfile:
            import __main__

            try:
                exec(
                    compile(
                        open(rcfile, "rb").read(), rcfile, "exec", dont_inherit=True
                    ),
                    __main__.__dict__,
                    __main__.__dict__,
                )
            except:
                sys.stderr.write(
                    ">>> \nError executing PYTHONSTARTUP script %r\n" % (rcfile)
                )
                traceback.print_exc(file=sys.stderr)
        self.AppendToPrompt([])

    def SetContext(self, globals, locals, name="Dbg"):
        oldPrompt = sys.ps1
        if globals is None:
            # Reset
            sys.ps1 = ">>> "
            sys.ps2 = "... "
            locals = globals = __main__.__dict__
        else:
            sys.ps1 = "[%s]>>> " % name
            sys.ps2 = "[%s]... " % name
        self.interp.locals = locals
        self.interp.globals = globals
        self.AppendToPrompt([], oldPrompt)

    def GetContext(self):
        return self.interp.globals, self.interp.locals

    def DoGetLine(self, line=-1):
        if line == -1:
            line = self.LineFromChar()
        line = self.GetLine(line)
        while line and line[-1] in ("\r", "\n"):
            line = line[:-1]
        return line

    def AppendToPrompt(self, bufLines, oldPrompt=None):
        "Take a command and stick it at the end of the buffer (with python prompts inserted if required)."
        self.flush()
        lastLineNo = self.GetLineCount() - 1
        line = self.DoGetLine(lastLineNo)
        if oldPrompt and line == oldPrompt:
            self.SetSel(self.GetTextLength() - len(oldPrompt), self.GetTextLength())
            self.ReplaceSel(sys.ps1)
        elif line != str(sys.ps1):
            if len(line) != 0:
                self.write("\n")
            self.write(sys.ps1)
        self.flush()
        self.idle.text.mark_set("iomark", "end-1c")
        if not bufLines:
            return
        terms = (["\n" + sys.ps2] * (len(bufLines) - 1)) + [""]
        for bufLine, term in zip(bufLines, terms):
            if bufLine.strip():
                self.write(bufLine + term)
        self.flush()

    def EnsureNoPrompt(self):
        # Get ready to write some text NOT at a Python prompt.
        self.flush()
        lastLineNo = self.GetLineCount() - 1
        line = self.DoGetLine(lastLineNo)
        if not line or line in (sys.ps1, sys.ps2):
            self.SetSel(self.GetTextLength() - len(line), self.GetTextLength())
            self.ReplaceSel("")
        else:
            # Just add a new line.
            self.write("\n")

    def _GetSubConfigNames(self):
        return ["interactive"]  # Allow [Keys:Interactive] sections to be specific

    def HookHandlers(self):
        # Hook menu command (executed when a menu item with that ID is selected from a menu/toolbar
        self.HookCommand(self.OnSelectBlock, win32ui.ID_EDIT_SELECT_BLOCK)
        self.HookCommand(self.OnEditCopyCode, ID_EDIT_COPY_CODE)
        self.HookCommand(self.OnEditExecClipboard, ID_EDIT_EXEC_CLIPBOARD)
        mod = pywin.scintilla.IDLEenvironment.GetIDLEModule("IdleHistory")
        if mod is not None:
            self.history = mod.History(self.idle.text, "\n" + sys.ps2)
        else:
            self.history = None
        # hack for now for event handling.

    # GetBlockBoundary takes a line number, and will return the
    # start and and line numbers of the block, and a flag indicating if the
    # block is a Python code block.
    # If the line specified has a Python prompt, then the lines are parsed
    # backwards and forwards, and the flag is true.
    # If the line does not start with a prompt, the block is searched forward
    # and backward until a prompt _is_ found, and all lines in between without
    # prompts are returned, and the flag is false.
    def GetBlockBoundary(self, lineNo):
        line = self.DoGetLine(lineNo)
        maxLineNo = self.GetLineCount() - 1
        prefix = GetPromptPrefix(line)
        if prefix is None:  # Non code block
            flag = 0
            startLineNo = lineNo
            while startLineNo > 0:
                if GetPromptPrefix(self.DoGetLine(startLineNo - 1)) is not None:
                    break  # there _is_ a prompt
                startLineNo -= 1
            endLineNo = lineNo
            while endLineNo < maxLineNo:
                if GetPromptPrefix(self.DoGetLine(endLineNo + 1)) is not None:
                    break  # there _is_ a prompt
                endLineNo += 1
        else:  # Code block
            flag = 1
            startLineNo = lineNo
            while startLineNo > 0 and prefix != str(sys.ps1):
                prefix = GetPromptPrefix(self.DoGetLine(startLineNo - 1))
                if prefix is None:
                    break
                    # there is no prompt.
                startLineNo -= 1
            endLineNo = lineNo
            while endLineNo < maxLineNo:
                prefix = GetPromptPrefix(self.DoGetLine(endLineNo + 1))
                if prefix is None:
                    break  # there is no prompt
                if prefix == str(sys.ps1):
                    break  # this is another command
                endLineNo += 1
                # continue until end of buffer, or no prompt
        return (startLineNo, endLineNo, flag)

    def ExtractCommand(self, lines):
        start, end = lines
        retList = []
        while end >= start:
            thisLine = self.DoGetLine(end)
            promptLen = len(GetPromptPrefix(thisLine))
            retList = [thisLine[promptLen:]] + retList
            end -= 1
        return retList

    def OutputGrab(self):
        # 		import win32traceutil; return
        self.oldStdOut = sys.stdout
        self.oldStdErr = sys.stderr
        sys.stdout = self
        sys.stderr = self
        self.flush()

    def OutputRelease(self):
        # a command may have overwritten these - only restore if not.
        if self.oldStdOut is not None:
            if sys.stdout == self:
                sys.stdout = self.oldStdOut
        if self.oldStdErr is not None:
            if sys.stderr == self:
                sys.stderr = self.oldStdErr
        self.oldStdOut = None
        self.oldStdErr = None
        self.flush()

    ###################################
    #
    # Message/Command/Key Hooks.
    #
    # Enter key handler
    #
    def ProcessEnterEvent(self, event):
        # If autocompletion has been triggered, complete and do not process event
        if self.SCIAutoCActive():
            self.SCIAutoCComplete()
            self.SCICancel()
            return

        self.SCICancel()
        # First, check for an error message
        haveGrabbedOutput = 0
        if self.HandleSpecialLine():
            return 0

        lineNo = self.LineFromChar()
        start, end, isCode = self.GetBlockBoundary(lineNo)
        # If we are not in a code block just go to the prompt (or create a new one)
        if not isCode:
            self.AppendToPrompt([])
            win32ui.SetStatusText(win32ui.LoadString(afxres.AFX_IDS_IDLEMESSAGE))
            return

        lines = self.ExtractCommand((start, end))

        # If we are in a code-block, but it isn't at the end of the buffer
        # then copy it to the end ready for editing and subsequent execution
        if end != self.GetLineCount() - 1:
            win32ui.SetStatusText("Press ENTER to execute command")
            self.AppendToPrompt(lines)
            self.SetSel(-2)
            return

        # If SHIFT held down, we want new code here and now!
        bNeedIndent = (
            win32api.GetKeyState(win32con.VK_SHIFT) < 0
            or win32api.GetKeyState(win32con.VK_CONTROL) < 0
        )
        if bNeedIndent:
            self.ReplaceSel("\n")
        else:
            self.SetSel(-2)
            self.ReplaceSel("\n")
            source = "\n".join(lines)
            while source and source[-1] in "\t ":
                source = source[:-1]
            self.OutputGrab()  # grab the output for the command exec.
            try:
                if self.interp.runsource(
                    source, "<interactive input>"
                ):  # Need more input!
                    bNeedIndent = 1
                else:
                    # If the last line isn't empty, append a newline
                    if self.history is not None:
                        self.history.history_store(source)
                    self.AppendToPrompt([])
                    win32ui.SetStatusText(
                        win32ui.LoadString(afxres.AFX_IDS_IDLEMESSAGE)
                    )
            # 					win32ui.SetStatusText('Successfully executed statement')
            finally:
                self.OutputRelease()
        if bNeedIndent:
            win32ui.SetStatusText("Ready to continue the command")
            # Now attempt correct indentation (should use IDLE?)
            curLine = self.DoGetLine(lineNo)[len(sys.ps2) :]
            pos = 0
            indent = ""
            while len(curLine) > pos and curLine[pos] in string.whitespace:
                indent += curLine[pos]
                pos += 1
            if _is_block_opener(curLine):
                indent += "\t"
            elif _is_block_closer(curLine):
                indent = indent[:-1]
            # use ReplaceSel to ensure it goes at the cursor rather than end of buffer.
            self.ReplaceSel(sys.ps2 + indent)
        return 0

    # ESC key handler
    def ProcessEscEvent(self, event):
        # Implement a cancel.
        if self.SCIAutoCActive() or self.SCICallTipActive():
            self.SCICancel()
        else:
            win32ui.SetStatusText("Cancelled.")
            self.AppendToPrompt(("",))
        return 0

    def OnSelectBlock(self, command, code):
        lineNo = self.LineFromChar()
        start, end, isCode = self.GetBlockBoundary(lineNo)
        startIndex = self.LineIndex(start)
        endIndex = self.LineIndex(end + 1) - 2  # skip \r + \n
        if endIndex < 0:  # must be beyond end of buffer
            endIndex = -2  # self.Length()
        self.SetSel(startIndex, endIndex)

    def OnEditCopyCode(self, command, code):
        """Sanitizes code from interactive window, removing prompts and output,
        and inserts it in the clipboard."""
        code = self.GetSelText()
        lines = code.splitlines()
        out_lines = []
        for line in lines:
            if line.startswith(sys.ps1):
                line = line[len(sys.ps1) :]
                out_lines.append(line)
            elif line.startswith(sys.ps2):
                line = line[len(sys.ps2) :]
                out_lines.append(line)
        out_code = os.linesep.join(out_lines)
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.SetClipboardData(
                win32clipboard.CF_UNICODETEXT, str(out_code)
            )
        finally:
            win32clipboard.CloseClipboard()

    def OnEditExecClipboard(self, command, code):
        """Executes python code directly from the clipboard."""
        win32clipboard.OpenClipboard()
        try:
            code = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
        finally:
            win32clipboard.CloseClipboard()

        code = code.replace("\r\n", "\n") + "\n"
        try:
            o = compile(code, "<clipboard>", "exec")
            exec(o, __main__.__dict__)
        except:
            traceback.print_exc()

    def GetRightMenuItems(self):
        # Just override parents
        ret = []
        flags = 0
        ret.append((flags, win32ui.ID_EDIT_UNDO, "&Undo"))
        ret.append(win32con.MF_SEPARATOR)
        ret.append((flags, win32ui.ID_EDIT_CUT, "Cu&t"))
        ret.append((flags, win32ui.ID_EDIT_COPY, "&Copy"))

        start, end = self.GetSel()
        if start != end:
            ret.append((flags, ID_EDIT_COPY_CODE, "Copy code without prompts"))
        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
            ret.append(
                (flags, ID_EDIT_EXEC_CLIPBOARD, "Execute python code from clipboard")
            )

        ret.append((flags, win32ui.ID_EDIT_PASTE, "&Paste"))
        ret.append(win32con.MF_SEPARATOR)
        ret.append((flags, win32ui.ID_EDIT_SELECT_ALL, "&Select all"))
        ret.append((flags, win32ui.ID_EDIT_SELECT_BLOCK, "Select &block"))
        ret.append((flags, win32ui.ID_VIEW_WHITESPACE, "View &Whitespace"))
        return ret

    def MDINextEvent(self, event):
        win32ui.GetMainFrame().MDINext(0)

    def MDIPrevEvent(self, event):
        win32ui.GetMainFrame().MDINext(0)

    def WindowBackEvent(self, event):
        parent = self.GetParentFrame()
        if parent == win32ui.GetMainFrame():
            # It is docked.
            try:
                wnd, isactive = parent.MDIGetActive()
                wnd.SetFocus()
            except win32ui.error:
                # No MDI window active!
                pass
        else:
            # Normal Window
            try:
                lastActive = self.GetParentFrame().lastActive
                # If the window is invalid, reset it.
                if lastActive is not None and (
                    lastActive._obj_ is None or lastActive.GetSafeHwnd() == 0
                ):
                    lastActive = self.GetParentFrame().lastActive = None
                    win32ui.SetStatusText("The last active Window has been closed.")
            except AttributeError:
                print("Can't find the last active window!")
                lastActive = None
            if lastActive is not None:
                lastActive.MDIActivate()


class InteractiveView(InteractiveCore, winout.WindowOutputView):
    def __init__(self, doc):
        InteractiveCore.__init__(self)
        winout.WindowOutputView.__init__(self, doc)
        self.encoding = pywin.default_scintilla_encoding

    def _MakeColorizer(self):
        return InteractiveFormatter(self)

    def OnInitialUpdate(self):
        winout.WindowOutputView.OnInitialUpdate(self)
        self.SetWordWrap()
        self.Init()

    def HookHandlers(self):
        winout.WindowOutputView.HookHandlers(self)
        InteractiveCore.HookHandlers(self)


class CInteractivePython(winout.WindowOutput):
    def __init__(self, makeDoc=None, makeFrame=None):
        self.IsFinalDestroy = 0
        winout.WindowOutput.__init__(
            self,
            sectionProfile,
            sectionProfile,
            winout.flags.WQ_LINE,
            1,
            None,
            makeDoc,
            makeFrame,
            InteractiveView,
        )
        self.Create()

    def OnViewDestroy(self, view):
        if self.IsFinalDestroy:
            view.OutputRelease()
        winout.WindowOutput.OnViewDestroy(self, view)

    def Close(self):
        self.IsFinalDestroy = 1
        winout.WindowOutput.Close(self)


class InteractiveFrame(winout.WindowOutputFrame):
    def __init__(self):
        self.lastActive = None
        winout.WindowOutputFrame.__init__(self)

    def OnMDIActivate(self, bActive, wndActive, wndDeactive):
        if bActive:
            self.lastActive = wndDeactive


######################################################################
##
## Dockable Window Support
##
######################################################################
ID_DOCKED_INTERACTIVE_CONTROLBAR = 0xE802

DockedInteractiveViewParent = InteractiveView


class DockedInteractiveView(DockedInteractiveViewParent):
    def HookHandlers(self):
        DockedInteractiveViewParent.HookHandlers(self)
        self.HookMessage(self.OnSetFocus, win32con.WM_SETFOCUS)
        self.HookMessage(self.OnKillFocus, win32con.WM_KILLFOCUS)

    def OnSetFocus(self, msg):
        self.GetParentFrame().SetActiveView(self)
        return 1

    def OnKillFocus(self, msg):
        # If we are losing focus to another in this app, reset the main frame's active view.
        hwnd = wparam = msg[2]
        try:
            wnd = win32ui.CreateWindowFromHandle(hwnd)
            reset = wnd.GetTopLevelFrame() == self.GetTopLevelFrame()
        except win32ui.error:
            reset = 0  # Not my window
        if reset:
            self.GetParentFrame().SetActiveView(None)
        return 1

    def OnDestroy(self, msg):
        newSize = self.GetWindowPlacement()[4]
        pywin.framework.app.SaveWindowSize("Interactive Window", newSize, "docked")
        try:
            if self.GetParentFrame().GetActiveView == self:
                self.GetParentFrame().SetActiveView(None)
        except win32ui.error:
            pass
        try:
            if win32ui.GetMainFrame().GetActiveView() == self:
                win32ui.GetMainFrame().SetActiveView(None)
        except win32ui.error:
            pass
        return DockedInteractiveViewParent.OnDestroy(self, msg)


class CDockedInteractivePython(CInteractivePython):
    def __init__(self, dockbar):
        self.bFirstCreated = 0
        self.dockbar = dockbar
        CInteractivePython.__init__(self)

    def NeedRecreateWindow(self):
        if self.bCreating:
            return 0
        try:
            frame = win32ui.GetMainFrame()
            if frame.closing:
                return 0  # Dieing!
        except (win32ui.error, AttributeError):
            return 0  # The app is dieing!
        try:
            cb = frame.GetControlBar(ID_DOCKED_INTERACTIVE_CONTROLBAR)
            return not cb.IsWindowVisible()
        except win32ui.error:
            return 1  # Control bar does not exist!

    def RecreateWindow(self):
        try:
            dockbar = win32ui.GetMainFrame().GetControlBar(
                ID_DOCKED_INTERACTIVE_CONTROLBAR
            )
            win32ui.GetMainFrame().ShowControlBar(dockbar, 1, 1)
        except win32ui.error:
            CreateDockedInteractiveWindow()

    def Create(self):
        self.bCreating = 1
        doc = InteractiveDocument(None, self.DoCreateDoc())
        view = DockedInteractiveView(doc)
        defRect = pywin.framework.app.LoadWindowSize("Interactive Window", "docked")
        if defRect[2] - defRect[0] == 0:
            defRect = 0, 0, 500, 200
        style = win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.WS_BORDER
        id = 1050  # win32ui.AFX_IDW_PANE_FIRST
        view.CreateWindow(self.dockbar, id, style, defRect)
        view.OnInitialUpdate()
        self.bFirstCreated = 1

        self.currentView = doc.GetFirstView()
        self.bCreating = 0
        if self.title:
            doc.SetTitle(self.title)


# The factory we pass to the dockable window support.
def InteractiveViewCreator(parent):
    global edit
    edit = CDockedInteractivePython(parent)
    return edit.currentView


def CreateDockedInteractiveWindow():
    # Later, the DockingBar should be capable of hosting multiple
    # children.
    from pywin.docking.DockingBar import DockingBar

    bar = DockingBar()
    creator = InteractiveViewCreator
    bar.CreateWindow(
        win32ui.GetMainFrame(),
        creator,
        "Interactive Window",
        ID_DOCKED_INTERACTIVE_CONTROLBAR,
    )
    bar.SetBarStyle(
        bar.GetBarStyle()
        | afxres.CBRS_TOOLTIPS
        | afxres.CBRS_FLYBY
        | afxres.CBRS_SIZE_DYNAMIC
    )
    bar.EnableDocking(afxres.CBRS_ALIGN_ANY)
    win32ui.GetMainFrame().DockControlBar(bar, afxres.AFX_IDW_DOCKBAR_BOTTOM)


######################################################################
#
# The public interface to this module.
#
######################################################################
# No extra functionality now, but maybe later, so
# publicize these names.
InteractiveDocument = winout.WindowOutputDocument

# We remember our one and only interactive window in the "edit" variable.
edit = None


def CreateInteractiveWindowUserPreference(makeDoc=None, makeFrame=None):
    """Create some sort of interactive window if the user's preference say we should."""
    bCreate = LoadPreference("Show at startup", 1)
    if bCreate:
        CreateInteractiveWindow(makeDoc, makeFrame)


def CreateInteractiveWindow(makeDoc=None, makeFrame=None):
    """Create a standard or docked interactive window unconditionally"""
    assert edit is None, "Creating second interactive window!"
    bDocking = LoadPreference("Docking", 0)
    if bDocking:
        CreateDockedInteractiveWindow()
    else:
        CreateMDIInteractiveWindow(makeDoc, makeFrame)
    assert edit is not None, "Created interactive window, but did not set the global!"
    edit.currentView.SetFocus()


def CreateMDIInteractiveWindow(makeDoc=None, makeFrame=None):
    """Create a standard (non-docked) interactive window unconditionally"""
    global edit
    if makeDoc is None:
        makeDoc = InteractiveDocument
    if makeFrame is None:
        makeFrame = InteractiveFrame
    edit = CInteractivePython(makeDoc=makeDoc, makeFrame=makeFrame)


def DestroyInteractiveWindow():
    """Destroy the interactive window.
    This is different to Closing the window,
    which may automatically re-appear.  Once destroyed, it can never be recreated,
    and a complete new instance must be created (which the various other helper
    functions will then do after making this call
    """
    global edit
    if edit is not None and edit.currentView is not None:
        if edit.currentView.GetParentFrame() == win32ui.GetMainFrame():
            # It is docked - do nothing now (this is only called at shutdown!)
            pass
        else:
            # It is a standard window - call Close on the container.
            edit.Close()
            edit = None


def CloseInteractiveWindow():
    """Close the interactive window, allowing it to be re-created on demand."""
    global edit
    if edit is not None and edit.currentView is not None:
        if edit.currentView.GetParentFrame() == win32ui.GetMainFrame():
            # It is docked, just hide the dock bar.
            frame = win32ui.GetMainFrame()
            cb = frame.GetControlBar(ID_DOCKED_INTERACTIVE_CONTROLBAR)
            frame.ShowControlBar(cb, 0, 1)
        else:
            # It is a standard window - destroy the frame/view, allowing the object itself to remain.
            edit.currentView.GetParentFrame().DestroyWindow()


def ToggleInteractiveWindow():
    """If the interactive window is visible, hide it, otherwise show it."""
    if edit is None:
        CreateInteractiveWindow()
    else:
        if edit.NeedRecreateWindow():
            edit.RecreateWindow()
        else:
            # Close it, allowing a reopen.
            CloseInteractiveWindow()


def ShowInteractiveWindow():
    """Shows (or creates if necessary) an interactive window"""
    if edit is None:
        CreateInteractiveWindow()
    else:
        if edit.NeedRecreateWindow():
            edit.RecreateWindow()
        else:
            parent = edit.currentView.GetParentFrame()
            if parent == win32ui.GetMainFrame():  # It is docked.
                edit.currentView.SetFocus()
            else:  # It is a "normal" window
                edit.currentView.GetParentFrame().AutoRestore()
                win32ui.GetMainFrame().MDIActivate(edit.currentView.GetParentFrame())


def IsInteractiveWindowVisible():
    return edit is not None and not edit.NeedRecreateWindow()

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\typeguard\_checkers.py ===
from __future__ import annotations

import collections.abc
import inspect
import sys
import types
import typing
import warnings
from enum import Enum
from inspect import Parameter, isclass, isfunction
from io import BufferedIOBase, IOBase, RawIOBase, TextIOBase
from textwrap import indent
from typing import (
    IO,
    AbstractSet,
    Any,
    BinaryIO,
    Callable,
    Dict,
    ForwardRef,
    List,
    Mapping,
    MutableMapping,
    NewType,
    Optional,
    Sequence,
    Set,
    TextIO,
    Tuple,
    Type,
    TypeVar,
    Union,
)
from unittest.mock import Mock
from weakref import WeakKeyDictionary

try:
    import typing_extensions
except ImportError:
    typing_extensions = None  # type: ignore[assignment]

# Must use this because typing.is_typeddict does not recognize
# TypedDict from typing_extensions, and as of version 4.12.0
# typing_extensions.TypedDict is different from typing.TypedDict
# on all versions.
from typing_extensions import is_typeddict

from ._config import ForwardRefPolicy
from ._exceptions import TypeCheckError, TypeHintWarning
from ._memo import TypeCheckMemo
from ._utils import evaluate_forwardref, get_stacklevel, get_type_name, qualified_name

if sys.version_info >= (3, 11):
    from typing import (
        Annotated,
        NotRequired,
        TypeAlias,
        get_args,
        get_origin,
    )

    SubclassableAny = Any
else:
    from typing_extensions import (
        Annotated,
        NotRequired,
        TypeAlias,
        get_args,
        get_origin,
    )
    from typing_extensions import Any as SubclassableAny

if sys.version_info >= (3, 10):
    from importlib.metadata import entry_points
    from typing import ParamSpec
else:
    from importlib_metadata import entry_points
    from typing_extensions import ParamSpec

TypeCheckerCallable: TypeAlias = Callable[
    [Any, Any, Tuple[Any, ...], TypeCheckMemo], Any
]
TypeCheckLookupCallback: TypeAlias = Callable[
    [Any, Tuple[Any, ...], Tuple[Any, ...]], Optional[TypeCheckerCallable]
]

checker_lookup_functions: list[TypeCheckLookupCallback] = []
generic_alias_types: tuple[type, ...] = (type(List), type(List[Any]))
if sys.version_info >= (3, 9):
    generic_alias_types += (types.GenericAlias,)

protocol_check_cache: WeakKeyDictionary[
    type[Any], dict[type[Any], TypeCheckError | None]
] = WeakKeyDictionary()

# Sentinel
_missing = object()

# Lifted from mypy.sharedparse
BINARY_MAGIC_METHODS = {
    "__add__",
    "__and__",
    "__cmp__",
    "__divmod__",
    "__div__",
    "__eq__",
    "__floordiv__",
    "__ge__",
    "__gt__",
    "__iadd__",
    "__iand__",
    "__idiv__",
    "__ifloordiv__",
    "__ilshift__",
    "__imatmul__",
    "__imod__",
    "__imul__",
    "__ior__",
    "__ipow__",
    "__irshift__",
    "__isub__",
    "__itruediv__",
    "__ixor__",
    "__le__",
    "__lshift__",
    "__lt__",
    "__matmul__",
    "__mod__",
    "__mul__",
    "__ne__",
    "__or__",
    "__pow__",
    "__radd__",
    "__rand__",
    "__rdiv__",
    "__rfloordiv__",
    "__rlshift__",
    "__rmatmul__",
    "__rmod__",
    "__rmul__",
    "__ror__",
    "__rpow__",
    "__rrshift__",
    "__rshift__",
    "__rsub__",
    "__rtruediv__",
    "__rxor__",
    "__sub__",
    "__truediv__",
    "__xor__",
}


def check_callable(
    value: Any,
    origin_type: Any,
    args: tuple[Any, ...],
    memo: TypeCheckMemo,
) -> None:
    if not callable(value):
        raise TypeCheckError("is not callable")

    if args:
        try:
            signature = inspect.signature(value)
        except (TypeError, ValueError):
            return

        argument_types = args[0]
        if isinstance(argument_types, list) and not any(
            type(item) is ParamSpec for item in argument_types
        ):
            # The callable must not have keyword-only arguments without defaults
            unfulfilled_kwonlyargs = [
                param.name
                for param in signature.parameters.values()
                if param.kind == Parameter.KEYWORD_ONLY
                and param.default == Parameter.empty
            ]
            if unfulfilled_kwonlyargs:
                raise TypeCheckError(
                    f"has mandatory keyword-only arguments in its declaration: "
                    f'{", ".join(unfulfilled_kwonlyargs)}'
                )

            num_positional_args = num_mandatory_pos_args = 0
            has_varargs = False
            for param in signature.parameters.values():
                if param.kind in (
                    Parameter.POSITIONAL_ONLY,
                    Parameter.POSITIONAL_OR_KEYWORD,
                ):
                    num_positional_args += 1
                    if param.default is Parameter.empty:
                        num_mandatory_pos_args += 1
                elif param.kind == Parameter.VAR_POSITIONAL:
                    has_varargs = True

            if num_mandatory_pos_args > len(argument_types):
                raise TypeCheckError(
                    f"has too many mandatory positional arguments in its declaration; "
                    f"expected {len(argument_types)} but {num_mandatory_pos_args} "
                    f"mandatory positional argument(s) declared"
                )
            elif not has_varargs and num_positional_args < len(argument_types):
                raise TypeCheckError(
                    f"has too few arguments in its declaration; expected "
                    f"{len(argument_types)} but {num_positional_args} argument(s) "
                    f"declared"
                )


def check_mapping(
    value: Any,
    origin_type: Any,
    args: tuple[Any, ...],
    memo: TypeCheckMemo,
) -> None:
    if origin_type is Dict or origin_type is dict:
        if not isinstance(value, dict):
            raise TypeCheckError("is not a dict")
    if origin_type is MutableMapping or origin_type is collections.abc.MutableMapping:
        if not isinstance(value, collections.abc.MutableMapping):
            raise TypeCheckError("is not a mutable mapping")
    elif not isinstance(value, collections.abc.Mapping):
        raise TypeCheckError("is not a mapping")

    if args:
        key_type, value_type = args
        if key_type is not Any or value_type is not Any:
            samples = memo.config.collection_check_strategy.iterate_samples(
                value.items()
            )
            for k, v in samples:
                try:
                    check_type_internal(k, key_type, memo)
                except TypeCheckError as exc:
                    exc.append_path_element(f"key {k!r}")
                    raise

                try:
                    check_type_internal(v, value_type, memo)
                except TypeCheckError as exc:
                    exc.append_path_element(f"value of key {k!r}")
                    raise


def check_typed_dict(
    value: Any,
    origin_type: Any,
    args: tuple[Any, ...],
    memo: TypeCheckMemo,
) -> None:
    if not isinstance(value, dict):
        raise TypeCheckError("is not a dict")

    declared_keys = frozenset(origin_type.__annotations__)
    if hasattr(origin_type, "__required_keys__"):
        required_keys = set(origin_type.__required_keys__)
    else:  # py3.8 and lower
        required_keys = set(declared_keys) if origin_type.__total__ else set()

    existing_keys = set(value)
    extra_keys = existing_keys - declared_keys
    if extra_keys:
        keys_formatted = ", ".join(f'"{key}"' for key in sorted(extra_keys, key=repr))
        raise TypeCheckError(f"has unexpected extra key(s): {keys_formatted}")

    # Detect NotRequired fields which are hidden by get_type_hints()
    type_hints: dict[str, type] = {}
    for key, annotation in origin_type.__annotations__.items():
        if isinstance(annotation, ForwardRef):
            annotation = evaluate_forwardref(annotation, memo)
            if get_origin(annotation) is NotRequired:
                required_keys.discard(key)
                annotation = get_args(annotation)[0]

        type_hints[key] = annotation

    missing_keys = required_keys - existing_keys
    if missing_keys:
        keys_formatted = ", ".join(f'"{key}"' for key in sorted(missing_keys, key=repr))
        raise TypeCheckError(f"is missing required key(s): {keys_formatted}")

    for key, argtype in type_hints.items():
        argvalue = value.get(key, _missing)
        if argvalue is not _missing:
            try:
                check_type_internal(argvalue, argtype, memo)
            except TypeCheckError as exc:
                exc.append_path_element(f"value of key {key!r}")
                raise


def check_list(
    value: Any,
    origin_type: Any,
    args: tuple[Any, ...],
    memo: TypeCheckMemo,
) -> None:
    if not isinstance(value, list):
        raise TypeCheckError("is not a list")

    if args and args != (Any,):
        samples = memo.config.collection_check_strategy.iterate_samples(value)
        for i, v in enumerate(samples):
            try:
                check_type_internal(v, args[0], memo)
            except TypeCheckError as exc:
                exc.append_path_element(f"item {i}")
                raise


def check_sequence(
    value: Any,
    origin_type: Any,
    args: tuple[Any, ...],
    memo: TypeCheckMemo,
) -> None:
    if not isinstance(value, collections.abc.Sequence):
        raise TypeCheckError("is not a sequence")

    if args and args != (Any,):
        samples = memo.config.collection_check_strategy.iterate_samples(value)
        for i, v in enumerate(samples):
            try:
                check_type_internal(v, args[0], memo)
            except TypeCheckError as exc:
                exc.append_path_element(f"item {i}")
                raise


def check_set(
    value: Any,
    origin_type: Any,
    args: tuple[Any, ...],
    memo: TypeCheckMemo,
) -> None:
    if origin_type is frozenset:
        if not isinstance(value, frozenset):
            raise TypeCheckError("is not a frozenset")
    elif not isinstance(value, AbstractSet):
        raise TypeCheckError("is not a set")

    if args and args != (Any,):
        samples = memo.config.collection_check_strategy.iterate_samples(value)
        for v in samples:
            try:
                check_type_internal(v, args[0], memo)
            except TypeCheckError as exc:
                exc.append_path_element(f"[{v}]")
                raise


def check_tuple(
    value: Any,
    origin_type: Any,
    args: tuple[Any, ...],
    memo: TypeCheckMemo,
) -> None:
    # Specialized check for NamedTuples
    if field_types := getattr(origin_type, "__annotations__", None):
        if not isinstance(value, origin_type):
            raise TypeCheckError(
                f"is not a named tuple of type {qualified_name(origin_type)}"
            )

        for name, field_type in field_types.items():
            try:
                check_type_internal(getattr(value, name), field_type, memo)
            except TypeCheckError as exc:
                exc.append_path_element(f"attribute {name!r}")
                raise

        return
    elif not isinstance(value, tuple):
        raise TypeCheckError("is not a tuple")

    if args:
        use_ellipsis = args[-1] is Ellipsis
        tuple_params = args[: -1 if use_ellipsis else None]
    else:
        # Unparametrized Tuple or plain tuple
        return

    if use_ellipsis:
        element_type = tuple_params[0]
        samples = memo.config.collection_check_strategy.iterate_samples(value)
        for i, element in enumerate(samples):
            try:
                check_type_internal(element, element_type, memo)
            except TypeCheckError as exc:
                exc.append_path_element(f"item {i}")
                raise
    elif tuple_params == ((),):
        if value != ():
            raise TypeCheckError("is not an empty tuple")
    else:
        if len(value) != len(tuple_params):
            raise TypeCheckError(
                f"has wrong number of elements (expected {len(tuple_params)}, got "
                f"{len(value)} instead)"
            )

        for i, (element, element_type) in enumerate(zip(value, tuple_params)):
            try:
                check_type_internal(element, element_type, memo)
            except TypeCheckError as exc:
                exc.append_path_element(f"item {i}")
                raise


def check_union(
    value: Any,
    origin_type: Any,
    args: tuple[Any, ...],
    memo: TypeCheckMemo,
) -> None:
    errors: dict[str, TypeCheckError] = {}
    try:
        for type_ in args:
            try:
                check_type_internal(value, type_, memo)
                return
            except TypeCheckError as exc:
                errors[get_type_name(type_)] = exc

        formatted_errors = indent(
            "\n".join(f"{key}: {error}" for key, error in errors.items()), "  "
        )
    finally:
        del errors  # avoid creating ref cycle
    raise TypeCheckError(f"did not match any element in the union:\n{formatted_errors}")


def check_uniontype(
    value: Any,
    origin_type: Any,
    args: tuple[Any, ...],
    memo: TypeCheckMemo,
) -> None:
    errors: dict[str, TypeCheckError] = {}
    for type_ in args:
        try:
            check_type_internal(value, type_, memo)
            return
        except TypeCheckError as exc:
            errors[get_type_name(type_)] = exc

    formatted_errors = indent(
        "\n".join(f"{key}: {error}" for key, error in errors.items()), "  "
    )
    raise TypeCheckError(f"did not match any element in the union:\n{formatted_errors}")


def check_class(
    value: Any,
    origin_type: Any,
    args: tuple[Any, ...],
    memo: TypeCheckMemo,
) -> None:
    if not isclass(value) and not isinstance(value, generic_alias_types):
        raise TypeCheckError("is not a class")

    if not args:
        return

    if isinstance(args[0], ForwardRef):
        expected_class = evaluate_forwardref(args[0], memo)
    else:
        expected_class = args[0]

    if expected_class is Any:
        return
    elif getattr(expected_class, "_is_protocol", False):
        check_protocol(value, expected_class, (), memo)
    elif isinstance(expected_class, TypeVar):
        check_typevar(value, expected_class, (), memo, subclass_check=True)
    elif get_origin(expected_class) is Union:
        errors: dict[str, TypeCheckError] = {}
        for arg in get_args(expected_class):
            if arg is Any:
                return

            try:
                check_class(value, type, (arg,), memo)
                return
            except TypeCheckError as exc:
                errors[get_type_name(arg)] = exc
        else:
            formatted_errors = indent(
                "\n".join(f"{key}: {error}" for key, error in errors.items()), "  "
            )
            raise TypeCheckError(
                f"did not match any element in the union:\n{formatted_errors}"
            )
    elif not issubclass(value, expected_class):  # type: ignore[arg-type]
        raise TypeCheckError(f"is not a subclass of {qualified_name(expected_class)}")


def check_newtype(
    value: Any,
    origin_type: Any,
    args: tuple[Any, ...],
    memo: TypeCheckMemo,
) -> None:
    check_type_internal(value, origin_type.__supertype__, memo)


def check_instance(
    value: Any,
    origin_type: Any,
    args: tuple[Any, ...],
    memo: TypeCheckMemo,
) -> None:
    if not isinstance(value, origin_type):
        raise TypeCheckError(f"is not an instance of {qualified_name(origin_type)}")


def check_typevar(
    value: Any,
    origin_type: TypeVar,
    args: tuple[Any, ...],
    memo: TypeCheckMemo,
    *,
    subclass_check: bool = False,
) -> None:
    if origin_type.__bound__ is not None:
        annotation = (
            Type[origin_type.__bound__] if subclass_check else origin_type.__bound__
        )
        check_type_internal(value, annotation, memo)
    elif origin_type.__constraints__:
        for constraint in origin_type.__constraints__:
            annotation = Type[constraint] if subclass_check else constraint
            try:
                check_type_internal(value, annotation, memo)
            except TypeCheckError:
                pass
            else:
                break
        else:
            formatted_constraints = ", ".join(
                get_type_name(constraint) for constraint in origin_type.__constraints__
            )
            raise TypeCheckError(
                f"does not match any of the constraints " f"({formatted_constraints})"
            )


if typing_extensions is None:

    def _is_literal_type(typ: object) -> bool:
        return typ is typing.Literal

else:

    def _is_literal_type(typ: object) -> bool:
        return typ is typing.Literal or typ is typing_extensions.Literal


def check_literal(
    value: Any,
    origin_type: Any,
    args: tuple[Any, ...],
    memo: TypeCheckMemo,
) -> None:
    def get_literal_args(literal_args: tuple[Any, ...]) -> tuple[Any, ...]:
        retval: list[Any] = []
        for arg in literal_args:
            if _is_literal_type(get_origin(arg)):
                retval.extend(get_literal_args(arg.__args__))
            elif arg is None or isinstance(arg, (int, str, bytes, bool, Enum)):
                retval.append(arg)
            else:
                raise TypeError(
                    f"Illegal literal value: {arg}"
                )  # TypeError here is deliberate

        return tuple(retval)

    final_args = tuple(get_literal_args(args))
    try:
        index = final_args.index(value)
    except ValueError:
        pass
    else:
        if type(final_args[index]) is type(value):
            return

    formatted_args = ", ".join(repr(arg) for arg in final_args)
    raise TypeCheckError(f"is not any of ({formatted_args})") from None


def check_literal_string(
    value: Any,
    origin_type: Any,
    args: tuple[Any, ...],
    memo: TypeCheckMemo,
) -> None:
    check_type_internal(value, str, memo)


def check_typeguard(
    value: Any,
    origin_type: Any,
    args: tuple[Any, ...],
    memo: TypeCheckMemo,
) -> None:
    check_type_internal(value, bool, memo)


def check_none(
    value: Any,
    origin_type: Any,
    args: tuple[Any, ...],
    memo: TypeCheckMemo,
) -> None:
    if value is not None:
        raise TypeCheckError("is not None")


def check_number(
    value: Any,
    origin_type: Any,
    args: tuple[Any, ...],
    memo: TypeCheckMemo,
) -> None:
    if origin_type is complex and not isinstance(value, (complex, float, int)):
        raise TypeCheckError("is neither complex, float or int")
    elif origin_type is float and not isinstance(value, (float, int)):
        raise TypeCheckError("is neither float or int")


def check_io(
    value: Any,
    origin_type: Any,
    args: tuple[Any, ...],
    memo: TypeCheckMemo,
) -> None:
    if origin_type is TextIO or (origin_type is IO and args == (str,)):
        if not isinstance(value, TextIOBase):
            raise TypeCheckError("is not a text based I/O object")
    elif origin_type is BinaryIO or (origin_type is IO and args == (bytes,)):
        if not isinstance(value, (RawIOBase, BufferedIOBase)):
            raise TypeCheckError("is not a binary I/O object")
    elif not isinstance(value, IOBase):
        raise TypeCheckError("is not an I/O object")


def check_protocol(
    value: Any,
    origin_type: Any,
    args: tuple[Any, ...],
    memo: TypeCheckMemo,
) -> None:
    subject: type[Any] = value if isclass(value) else type(value)

    if subject in protocol_check_cache:
        result_map = protocol_check_cache[subject]
        if origin_type in result_map:
            if exc := result_map[origin_type]:
                raise exc
            else:
                return

    # Collect a set of methods and non-method attributes present in the protocol
    ignored_attrs = set(dir(typing.Protocol)) | {
        "__annotations__",
        "__non_callable_proto_members__",
    }
    expected_methods: dict[str, tuple[Any, Any]] = {}
    expected_noncallable_members: dict[str, Any] = {}
    for attrname in dir(origin_type):
        # Skip attributes present in typing.Protocol
        if attrname in ignored_attrs:
            continue

        member = getattr(origin_type, attrname)
        if callable(member):
            signature = inspect.signature(member)
            argtypes = [
                (p.annotation if p.annotation is not Parameter.empty else Any)
                for p in signature.parameters.values()
                if p.kind is not Parameter.KEYWORD_ONLY
            ] or Ellipsis
            return_annotation = (
                signature.return_annotation
                if signature.return_annotation is not Parameter.empty
                else Any
            )
            expected_methods[attrname] = argtypes, return_annotation
        else:
            expected_noncallable_members[attrname] = member

    for attrname, annotation in typing.get_type_hints(origin_type).items():
        expected_noncallable_members[attrname] = annotation

    subject_annotations = typing.get_type_hints(subject)

    # Check that all required methods are present and their signatures are compatible
    result_map = protocol_check_cache.setdefault(subject, {})
    try:
        for attrname, callable_args in expected_methods.items():
            try:
                method = getattr(subject, attrname)
            except AttributeError:
                if attrname in subject_annotations:
                    raise TypeCheckError(
                        f"is not compatible with the {origin_type.__qualname__} protocol "
                        f"because its {attrname!r} attribute is not a method"
                    ) from None
                else:
                    raise TypeCheckError(
                        f"is not compatible with the {origin_type.__qualname__} protocol "
                        f"because it has no method named {attrname!r}"
                    ) from None

            if not callable(method):
                raise TypeCheckError(
                    f"is not compatible with the {origin_type.__qualname__} protocol "
                    f"because its {attrname!r} attribute is not a callable"
                )

            # TODO: raise exception on added keyword-only arguments without defaults
            try:
                check_callable(method, Callable, callable_args, memo)
            except TypeCheckError as exc:
                raise TypeCheckError(
                    f"is not compatible with the {origin_type.__qualname__} protocol "
                    f"because its {attrname!r} method {exc}"
                ) from None

        # Check that all required non-callable members are present
        for attrname in expected_noncallable_members:
            # TODO: implement assignability checks for non-callable members
            if attrname not in subject_annotations and not hasattr(subject, attrname):
                raise TypeCheckError(
                    f"is not compatible with the {origin_type.__qualname__} protocol "
                    f"because it has no attribute named {attrname!r}"
                )
    except TypeCheckError as exc:
        result_map[origin_type] = exc
        raise
    else:
        result_map[origin_type] = None


def check_byteslike(
    value: Any,
    origin_type: Any,
    args: tuple[Any, ...],
    memo: TypeCheckMemo,
) -> None:
    if not isinstance(value, (bytearray, bytes, memoryview)):
        raise TypeCheckError("is not bytes-like")


def check_self(
    value: Any,
    origin_type: Any,
    args: tuple[Any, ...],
    memo: TypeCheckMemo,
) -> None:
    if memo.self_type is None:
        raise TypeCheckError("cannot be checked against Self outside of a method call")

    if isclass(value):
        if not issubclass(value, memo.self_type):
            raise TypeCheckError(
                f"is not an instance of the self type "
                f"({qualified_name(memo.self_type)})"
            )
    elif not isinstance(value, memo.self_type):
        raise TypeCheckError(
            f"is not an instance of the self type ({qualified_name(memo.self_type)})"
        )


def check_paramspec(
    value: Any,
    origin_type: Any,
    args: tuple[Any, ...],
    memo: TypeCheckMemo,
) -> None:
    pass  # No-op for now


def check_instanceof(
    value: Any,
    origin_type: Any,
    args: tuple[Any, ...],
    memo: TypeCheckMemo,
) -> None:
    if not isinstance(value, origin_type):
        raise TypeCheckError(f"is not an instance of {qualified_name(origin_type)}")


def check_type_internal(
    value: Any,
    annotation: Any,
    memo: TypeCheckMemo,
) -> None:
    """
    Check that the given object is compatible with the given type annotation.

    This function should only be used by type checker callables. Applications should use
    :func:`~.check_type` instead.

    :param value: the value to check
    :param annotation: the type annotation to check against
    :param memo: a memo object containing configuration and information necessary for
        looking up forward references
    """

    if isinstance(annotation, ForwardRef):
        try:
            annotation = evaluate_forwardref(annotation, memo)
        except NameError:
            if memo.config.forward_ref_policy is ForwardRefPolicy.ERROR:
                raise
            elif memo.config.forward_ref_policy is ForwardRefPolicy.WARN:
                warnings.warn(
                    f"Cannot resolve forward reference {annotation.__forward_arg__!r}",
                    TypeHintWarning,
                    stacklevel=get_stacklevel(),
                )

            return

    if annotation is Any or annotation is SubclassableAny or isinstance(value, Mock):
        return

    # Skip type checks if value is an instance of a class that inherits from Any
    if not isclass(value) and SubclassableAny in type(value).__bases__:
        return

    extras: tuple[Any, ...]
    origin_type = get_origin(annotation)
    if origin_type is Annotated:
        annotation, *extras_ = get_args(annotation)
        extras = tuple(extras_)
        origin_type = get_origin(annotation)
    else:
        extras = ()

    if origin_type is not None:
        args = get_args(annotation)

        # Compatibility hack to distinguish between unparametrized and empty tuple
        # (tuple[()]), necessary due to https://github.com/python/cpython/issues/91137
        if origin_type in (tuple, Tuple) and annotation is not Tuple and not args:
            args = ((),)
    else:
        origin_type = annotation
        args = ()

    for lookup_func in checker_lookup_functions:
        checker = lookup_func(origin_type, args, extras)
        if checker:
            checker(value, origin_type, args, memo)
            return

    if isclass(origin_type):
        if not isinstance(value, origin_type):
            raise TypeCheckError(f"is not an instance of {qualified_name(origin_type)}")
    elif type(origin_type) is str:  # noqa: E721
        warnings.warn(
            f"Skipping type check against {origin_type!r}; this looks like a "
            f"string-form forward reference imported from another module",
            TypeHintWarning,
            stacklevel=get_stacklevel(),
        )


# Equality checks are applied to these
origin_type_checkers = {
    bytes: check_byteslike,
    AbstractSet: check_set,
    BinaryIO: check_io,
    Callable: check_callable,
    collections.abc.Callable: check_callable,
    complex: check_number,
    dict: check_mapping,
    Dict: check_mapping,
    float: check_number,
    frozenset: check_set,
    IO: check_io,
    list: check_list,
    List: check_list,
    typing.Literal: check_literal,
    Mapping: check_mapping,
    MutableMapping: check_mapping,
    None: check_none,
    collections.abc.Mapping: check_mapping,
    collections.abc.MutableMapping: check_mapping,
    Sequence: check_sequence,
    collections.abc.Sequence: check_sequence,
    collections.abc.Set: check_set,
    set: check_set,
    Set: check_set,
    TextIO: check_io,
    tuple: check_tuple,
    Tuple: check_tuple,
    type: check_class,
    Type: check_class,
    Union: check_union,
}
if sys.version_info >= (3, 10):
    origin_type_checkers[types.UnionType] = check_uniontype
    origin_type_checkers[typing.TypeGuard] = check_typeguard
if sys.version_info >= (3, 11):
    origin_type_checkers.update(
        {typing.LiteralString: check_literal_string, typing.Self: check_self}
    )
if typing_extensions is not None:
    # On some Python versions, these may simply be re-exports from typing,
    # but exactly which Python versions is subject to change,
    # so it's best to err on the safe side
    # and update the dictionary on all Python versions
    # if typing_extensions is installed
    origin_type_checkers[typing_extensions.Literal] = check_literal
    origin_type_checkers[typing_extensions.LiteralString] = check_literal_string
    origin_type_checkers[typing_extensions.Self] = check_self
    origin_type_checkers[typing_extensions.TypeGuard] = check_typeguard


def builtin_checker_lookup(
    origin_type: Any, args: tuple[Any, ...], extras: tuple[Any, ...]
) -> TypeCheckerCallable | None:
    checker = origin_type_checkers.get(origin_type)
    if checker is not None:
        return checker
    elif is_typeddict(origin_type):
        return check_typed_dict
    elif isclass(origin_type) and issubclass(
        origin_type,
        Tuple,  # type: ignore[arg-type]
    ):
        # NamedTuple
        return check_tuple
    elif getattr(origin_type, "_is_protocol", False):
        return check_protocol
    elif isinstance(origin_type, ParamSpec):
        return check_paramspec
    elif isinstance(origin_type, TypeVar):
        return check_typevar
    elif origin_type.__class__ is NewType:
        # typing.NewType on Python 3.10+
        return check_newtype
    elif (
        isfunction(origin_type)
        and getattr(origin_type, "__module__", None) == "typing"
        and getattr(origin_type, "__qualname__", "").startswith("NewType.")
        and hasattr(origin_type, "__supertype__")
    ):
        # typing.NewType on Python 3.9 and below
        return check_newtype

    return None


checker_lookup_functions.append(builtin_checker_lookup)


def load_plugins() -> None:
    """
    Load all type checker lookup functions from entry points.

    All entry points from the ``typeguard.checker_lookup`` group are loaded, and the
    returned lookup functions are added to :data:`typeguard.checker_lookup_functions`.

    .. note:: This function is called implicitly on import, unless the
        ``TYPEGUARD_DISABLE_PLUGIN_AUTOLOAD`` environment variable is present.
    """

    for ep in entry_points(group="typeguard.checker_lookup"):
        try:
            plugin = ep.load()
        except Exception as exc:
            warnings.warn(
                f"Failed to load plugin {ep.name!r}: " f"{qualified_name(exc)}: {exc}",
                stacklevel=2,
            )
            continue

        if not callable(plugin):
            warnings.warn(
                f"Plugin {ep} returned a non-callable object: {plugin!r}", stacklevel=2
            )
            continue

        checker_lookup_functions.insert(0, plugin)

# === NexusCore/openenv\Lib\site-packages\executing\_position_node_finder.py ===
import ast
import sys
import dis
from types import CodeType, FrameType
from typing import Any, Callable, Iterator, Optional, Sequence, Set, Tuple, Type, Union, cast
from .executing import EnhancedAST, NotOneValueFound, Source, only, function_node_types, assert_
from ._exceptions import KnownIssue, VerifierFailure

from functools import lru_cache

# the code in this module can use all python>=3.11 features


def parents(node: EnhancedAST) -> Iterator[EnhancedAST]:
    while True:
        if hasattr(node, "parent"):
            node = node.parent
            yield node
        else:
            break  # pragma: no mutate


def node_and_parents(node: EnhancedAST) -> Iterator[EnhancedAST]:
    yield node
    yield from parents(node)


def mangled_name(node: EnhancedAST) -> str:
    """

    Parameters:
        node: the node which should be mangled
        name: the name of the node

    Returns:
        The mangled name of `node`
    """
    if isinstance(node, ast.Attribute):
        name = node.attr
    elif isinstance(node, ast.Name):
        name = node.id
    elif isinstance(node, (ast.alias)):
        name = node.asname or node.name.split(".")[0]
    elif isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
        name = node.name
    elif isinstance(node, ast.ExceptHandler):
        assert node.name
        name = node.name
    elif sys.version_info >= (3,12) and isinstance(node,ast.TypeVar):
        name=node.name
    else:
        raise TypeError("no node to mangle for type "+repr(type(node)))

    if name.startswith("__") and not name.endswith("__"):

        parent,child=node.parent,node

        while not (isinstance(parent,ast.ClassDef) and child not in parent.bases):
            if not hasattr(parent,"parent"):
                break # pragma: no mutate

            parent,child=parent.parent,parent
        else:
            class_name=parent.name.lstrip("_")
            if class_name!="":
                return "_" + class_name + name

            

    return name


@lru_cache(128) # pragma: no mutate
def get_instructions(code: CodeType) -> list[dis.Instruction]:
    return list(dis.get_instructions(code))


types_cmp_issue_fix = (
    ast.IfExp,
    ast.If,
    ast.Assert,
    ast.While,
)

types_cmp_issue = types_cmp_issue_fix + (
    ast.ListComp,
    ast.SetComp,
    ast.DictComp,
    ast.GeneratorExp,
)

op_type_map = {
    "**": ast.Pow,
    "*": ast.Mult,
    "@": ast.MatMult,
    "//": ast.FloorDiv,
    "/": ast.Div,
    "%": ast.Mod,
    "+": ast.Add,
    "-": ast.Sub,
    "<<": ast.LShift,
    ">>": ast.RShift,
    "&": ast.BitAnd,
    "^": ast.BitXor,
    "|": ast.BitOr,
}


class PositionNodeFinder(object):
    """
    Mapping bytecode to ast-node based on the source positions, which where introduced in pyhon 3.11.
    In general every ast-node can be exactly referenced by its begin/end line/col_offset, which is stored in the bytecode.
    There are only some exceptions for methods and attributes.
    """

    def __init__(self, frame: FrameType, stmts: Set[EnhancedAST], tree: ast.Module, lasti: int, source: Source):
        self.bc_dict={bc.offset:bc for bc in get_instructions(frame.f_code) }

        self.source = source
        self.decorator: Optional[EnhancedAST] = None

        # work around for https://github.com/python/cpython/issues/96970
        while self.opname(lasti) == "CACHE":
            lasti -= 2

        try:
            # try to map with all match_positions
            self.result = self.find_node(lasti)
        except NotOneValueFound:
            typ: tuple[Type]
            # LOAD_METHOD could load "".join for long "..."%(...) BinOps
            # this can only be associated by using all positions
            if self.opname(lasti) in (
                "LOAD_METHOD",
                "LOAD_ATTR",
                "STORE_ATTR",
                "DELETE_ATTR",
            ):
                # lineno and col_offset of LOAD_METHOD and *_ATTR instructions get set to the beginning of
                # the attribute by the python compiler to improved error messages (PEP-657)
                # we ignore here the start position and try to find the ast-node just by end position and expected node type
                # This is save, because there can only be one attribute ending at a specific point in the source code.
                typ = (ast.Attribute,)
            elif self.opname(lasti) in ("CALL", "CALL_KW"):
                # A CALL instruction can be a method call, in which case the lineno and col_offset gets changed by the compiler.
                # Therefore we ignoring here this attributes and searchnig for a Call-node only by end_col_offset and end_lineno.
                # This is save, because there can only be one method ending at a specific point in the source code.
                # One closing ) only belongs to one method.
                typ = (ast.Call,)
            else:
                raise

            self.result = self.find_node(
                lasti,
                match_positions=("end_col_offset", "end_lineno"),
                typ=typ,
            )

        instruction = self.instruction(lasti)
        assert instruction is not None

        self.result = self.fix_result(self.result, instruction)

        self.known_issues(self.result, instruction)

        self.test_for_decorator(self.result, lasti)

        # verify
        if self.decorator is None:
            self.verify(self.result, instruction)
        else: 
            assert_(self.decorator in self.result.decorator_list)

    def test_for_decorator(self, node: EnhancedAST, index: int) -> None:
        if (
            isinstance(node.parent, (ast.ClassDef, function_node_types))
            and node in node.parent.decorator_list # type: ignore[attr-defined]
        ):
            node_func = node.parent

            while True:
                # the generated bytecode looks like follow:

                # index    opname
                # ------------------
                # index-4  PRECALL     (only in 3.11)
                # index-2  CACHE
                # index    CALL        <- the call instruction
                # ...      CACHE       some CACHE instructions

                # maybe multiple other bytecode blocks for other decorators
                # index-4  PRECALL     (only in 3.11)
                # index-2  CACHE
                # index    CALL        <- index of the next loop
                # ...      CACHE       some CACHE instructions

                # index+x  STORE_*     the ast-node of this instruction points to the decorated thing

                if not (
                    (self.opname(index - 4) == "PRECALL" or sys.version_info >= (3, 12))
                    and self.opname(index) == "CALL"
                ):  # pragma: no mutate
                    break  # pragma: no mutate

                index += 2

                while self.opname(index) in ("CACHE", "EXTENDED_ARG"):
                    index += 2

                if (
                    self.opname(index).startswith("STORE_")
                    and self.find_node(index) == node_func
                ):
                    self.result = node_func
                    self.decorator = node
                    return

                if sys.version_info < (3, 12):
                    index += 4

    def fix_result(
        self, node: EnhancedAST, instruction: dis.Instruction
    ) -> EnhancedAST:
        if (
            sys.version_info >= (3, 12, 5)
            and instruction.opname in ("GET_ITER", "FOR_ITER")
            and isinstance(node.parent, ast.For)
            and node is node.parent.iter
        ):
            # node positions have changed in 3.12.5
            # https://github.com/python/cpython/issues/93691
            # `for` calls __iter__ and __next__ during execution, the calling
            # expression of these calls was the ast.For node since cpython 3.11 (see test_iter).
            # cpython 3.12.5 changed this to the `iter` node of the loop, to make tracebacks easier to read.
            # This keeps backward compatibility with older executing versions.

            # there are also cases like:
            #
            # for a in iter(l): pass
            #
            # where `iter(l)` would be otherwise the resulting node for the `iter()` call and the __iter__ call of the for implementation.
            # keeping the old behaviour makes it possible to distinguish both cases.

            return node.parent

        if (
            sys.version_info >= (3, 12, 6)
            and instruction.opname in ("GET_ITER", "FOR_ITER")
            and isinstance(
                node.parent.parent,
                (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp),
            )
            and isinstance(node.parent,ast.comprehension)
            and node is node.parent.iter
        ):
            # same as above but only for comprehensions, see:
            # https://github.com/python/cpython/issues/123142

            return node.parent.parent

        if sys.version_info >= (3, 12,6) and instruction.opname == "CALL":
            before = self.instruction_before(instruction)
            if (
                before is not None
                and before.opname == "LOAD_CONST"
                and before.positions == instruction.positions
                and isinstance(node.parent, ast.withitem)
                and node is node.parent.context_expr
            ):
                # node positions for with-statements have change
                # and is now equal to the expression which created the context-manager
                # https://github.com/python/cpython/pull/120763

                # with context_manager:
                #     ...

                # but there is one problem to distinguish call-expressions from __exit__()

                # with context_manager():
                #     ...

                # the call for __exit__

                # 20  1:5    1:22  LOAD_CONST(None)
                # 22  1:5    1:22  LOAD_CONST(None)
                # 24  1:5    1:22  LOAD_CONST(None)
                # 26  1:5    1:22  CALL()         # <-- same source range as context_manager()

                # but we can use the fact that the previous load for None
                # has the same source range as the call, wich can not happen for normal calls

                # we return the same ast.With statement at the and to preserve backward compatibility

                return node.parent.parent

        if (
            sys.version_info >= (3, 12,6)
            and instruction.opname == "BEFORE_WITH"
            and isinstance(node.parent, ast.withitem)
            and node is node.parent.context_expr
        ):
            # handle positions changes for __enter__
            return node.parent.parent

        return node

    def known_issues(self, node: EnhancedAST, instruction: dis.Instruction) -> None:
        if instruction.opname in ("COMPARE_OP", "IS_OP", "CONTAINS_OP") and isinstance(
            node, types_cmp_issue
        ):
            if isinstance(node, types_cmp_issue_fix):
                # this is a workaround for https://github.com/python/cpython/issues/95921
                # we can fix cases with only on comparison inside the test condition
                #
                # we can not fix cases like:
                # if a<b<c and d<e<f: pass
                # if (a<b<c)!=d!=e: pass
                # because we don't know which comparison caused the problem

                comparisons = [
                    n
                    for n in ast.walk(node.test) # type: ignore[attr-defined]
                    if isinstance(n, ast.Compare) and len(n.ops) > 1
                ]

                assert_(comparisons, "expected at least one comparison")

                if len(comparisons) == 1:
                    node = self.result = cast(EnhancedAST, comparisons[0])
                else:
                    raise KnownIssue(
                        "multiple chain comparison inside %s can not be fixed" % (node)
                    )

            else:
                # Comprehension and generators get not fixed for now.
                raise KnownIssue("chain comparison inside %s can not be fixed" % (node))

        if (
            sys.version_info[:3] == (3, 11, 1)
            and isinstance(node, ast.Compare)
            and instruction.opname == "CALL"
            and any(isinstance(n, ast.Assert) for n in node_and_parents(node))
        ):
            raise KnownIssue(
                "known bug in 3.11.1 https://github.com/python/cpython/issues/95921"
            )

        if isinstance(node, ast.Assert):
            # pytest assigns the position of the assertion to all expressions of the rewritten assertion.
            # All the rewritten expressions get mapped to ast.Assert, which is the wrong ast-node.
            # We don't report this wrong result.
            raise KnownIssue("assert")

        if any(isinstance(n, ast.pattern) for n in node_and_parents(node)):
            # TODO: investigate
            raise KnownIssue("pattern matching ranges seems to be wrong")

        if (
            sys.version_info >= (3, 12)
            and isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "super"
        ):
            # super is optimized to some instructions which do not map nicely to a Call

            # find the enclosing function
            func = node.parent
            while hasattr(func, "parent") and not isinstance(
                func, (ast.AsyncFunctionDef, ast.FunctionDef)
            ):

                func = func.parent

            # get the first function argument (self/cls)
            first_arg = None

            if hasattr(func, "args"):
                args = [*func.args.posonlyargs, *func.args.args]
                if args:
                    first_arg = args[0].arg

            if (instruction.opname, instruction.argval) in [
                ("LOAD_DEREF", "__class__"),
                ("LOAD_FAST", first_arg),
                ("LOAD_DEREF", first_arg),
            ]:
                raise KnownIssue("super optimization")

        if self.is_except_cleanup(instruction, node):
            raise KnownIssue("exeption cleanup does not belong to the last node in a except block")

        if instruction.opname == "STORE_NAME" and instruction.argval == "__classcell__":
            # handle stores to __classcell__ as KnownIssue,
            # because they get complicated if they are used in `if` or `for` loops
            # example:
            #
            # class X:
            #     # ... something
            #     if some_condition:
            #         def method(self):
            #             super()
            #
            # The `STORE_NAME` instruction gets mapped to the `ast.If` node,
            # because it is the last element in the class.
            # This last element could be anything and gets dificult to verify.

            raise KnownIssue("store __classcell__")

        if (
            instruction.opname == "CALL"
            and not isinstance(node,ast.Call)
            and any(isinstance(p, ast.Assert) for p in parents(node))
            and sys.version_info >= (3, 11, 2)
        ):
            raise KnownIssue("exception generation maps to condition")

        if sys.version_info >= (3, 13):
            if instruction.opname in (
                "STORE_FAST_STORE_FAST",
                "STORE_FAST_LOAD_FAST",
                "LOAD_FAST_LOAD_FAST",
            ):
                raise KnownIssue(f"can not map {instruction.opname} to two ast nodes")

            if instruction.opname == "LOAD_FAST" and instruction.argval == "__class__":
                # example:
                #   class T:
                #       def a():
                #           super()
                #       some_node  # <- there is a LOAD_FAST for this node because we use super()

                raise KnownIssue(
                    f"loading of __class__ is accociated with a random node at the end of a class if you use super()"
                )

            if (
                instruction.opname == "COMPARE_OP"
                and isinstance(node, ast.UnaryOp)
                and isinstance(node.operand,ast.Compare)
                and isinstance(node.op, ast.Not)
            ):
                # work around for 
                # https://github.com/python/cpython/issues/114671
                self.result = node.operand

    @staticmethod
    def is_except_cleanup(inst: dis.Instruction, node: EnhancedAST) -> bool:
        if inst.opname not in (
            "STORE_NAME",
            "STORE_FAST",
            "STORE_DEREF",
            "STORE_GLOBAL",
            "DELETE_NAME",
            "DELETE_FAST",
            "DELETE_DEREF",
            "DELETE_GLOBAL",
        ):
            return False

        # This bytecode does something exception cleanup related.
        # The position of the instruciton seems to be something in the last ast-node of the ExceptHandler
        # this could be a bug, but it might not be observable in normal python code.

        # example:
        # except Exception as exc:
        #     enum_member._value_ = value

        # other example:
        # STORE_FAST of e was mapped to Constant(value=False)
        # except OSError as e:
        #     if not _ignore_error(e):
        #         raise
        #     return False

        # STORE_FAST of msg was mapped to print(...)
        #  except TypeError as msg:
        #      print("Sorry:", msg, file=file)

        if (
            isinstance(node, ast.Name)
            and isinstance(node.ctx,ast.Store)
            and inst.opname.startswith("STORE_")
            and mangled_name(node) == inst.argval
        ):
            # Storing the variable is valid and no exception cleanup, if the name is correct
            return False

        if (
            isinstance(node, ast.Name)
            and isinstance(node.ctx,ast.Del)
            and inst.opname.startswith("DELETE_")
            and mangled_name(node) == inst.argval
        ):
            # Deleting the variable is valid and no exception cleanup, if the name is correct
            return False

        return any(
            isinstance(n, ast.ExceptHandler) and n.name and mangled_name(n) == inst.argval
            for n in parents(node)
        )

    def verify(self, node: EnhancedAST, instruction: dis.Instruction) -> None:
        """
        checks if this node could gererate this instruction
        """

        op_name = instruction.opname
        extra_filter: Callable[[EnhancedAST], bool] = lambda e: True
        ctx: Type = type(None)

        def inst_match(opnames: Union[str, Sequence[str]], **kwargs: Any) -> bool:
            """
            match instruction

            Parameters:
                opnames: (str|Seq[str]): inst.opname has to be equal to or in `opname`
                **kwargs: every arg has to match inst.arg

            Returns:
                True if all conditions match the instruction

            """

            if isinstance(opnames, str):
                opnames = [opnames]
            return instruction.opname in opnames and kwargs == {
                k: getattr(instruction, k) for k in kwargs
            }

        def node_match(node_type: Union[Type, Tuple[Type, ...]], **kwargs: Any) -> bool:
            """
            match the ast-node

            Parameters:
                node_type: type of the node
                **kwargs: every `arg` has to be equal `node.arg`
                        or `node.arg` has to be an instance of `arg` if it is a type.
            """
            return isinstance(node, node_type) and all(
                isinstance(getattr(node, k), v)
                if isinstance(v, type)
                else getattr(node, k) == v
                for k, v in kwargs.items()
            )

        if op_name == "CACHE":
            return

        if inst_match("CALL") and node_match((ast.With, ast.AsyncWith)):
            # call to context.__exit__
            return

        if inst_match(("CALL", "LOAD_FAST")) and node_match(
            (ast.ListComp, ast.GeneratorExp, ast.SetComp, ast.DictComp)
        ):
            # call to the generator function
            return

        if (
            sys.version_info >= (3, 12)
            and inst_match(("LOAD_FAST_AND_CLEAR", "STORE_FAST"))
            and node_match((ast.ListComp, ast.SetComp, ast.DictComp))
        ):
            return

        if inst_match(("CALL", "CALL_FUNCTION_EX")) and node_match(
            (ast.ClassDef, ast.Call)
        ):
            return

        if inst_match(("COMPARE_OP", "IS_OP", "CONTAINS_OP")) and node_match(
            ast.Compare
        ):
            return

        if inst_match("LOAD_NAME", argval="__annotations__") and node_match(
            ast.AnnAssign
        ):
            return

        if (
            (
                inst_match("LOAD_METHOD", argval="join")
                or inst_match("LOAD_ATTR", argval="join")  # 3.12
                or inst_match(("CALL", "BUILD_STRING"))
            )
            and node_match(ast.BinOp, left=ast.Constant, op=ast.Mod)
            and isinstance(cast(ast.Constant, cast(ast.BinOp, node).left).value, str)
        ):
            # "..."%(...) uses "".join
            return

        if inst_match("STORE_SUBSCR") and node_match(ast.AnnAssign):
            # data: int
            return


        if inst_match(("DELETE_NAME", "DELETE_FAST")) and node_match(
            ast.Name, id=instruction.argval, ctx=ast.Del
        ):
            return

        if inst_match("BUILD_STRING") and (
            node_match(ast.JoinedStr) or node_match(ast.BinOp, op=ast.Mod)
        ):
            return

        if inst_match(("BEFORE_WITH","WITH_EXCEPT_START")) and node_match(ast.With):
            return

        if inst_match(("STORE_NAME", "STORE_GLOBAL"), argval="__doc__") and node_match(
            ast.Constant
        ):
            # store docstrings
            return

        if (
            inst_match(("STORE_NAME", "STORE_FAST", "STORE_GLOBAL", "STORE_DEREF"))
            and node_match(ast.ExceptHandler)
            and instruction.argval == mangled_name(node)
        ):
            # store exception in variable
            return

        if (
            inst_match(("STORE_NAME", "STORE_FAST", "STORE_DEREF", "STORE_GLOBAL"))
            and node_match((ast.Import, ast.ImportFrom))
            and any(mangled_name(cast(EnhancedAST, alias)) == instruction.argval for alias in cast(ast.Import, node).names)
        ):
            # store imported module in variable
            return

        if (
            inst_match(("STORE_FAST", "STORE_DEREF", "STORE_NAME", "STORE_GLOBAL"))
            and (
                node_match((ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef))
                or node_match(
                    ast.Name,
                    ctx=ast.Store,
                )
            )
            and instruction.argval == mangled_name(node)
        ):
            return

        if False:
            # TODO: match expressions are not supported for now
            if inst_match(("STORE_FAST", "STORE_NAME")) and node_match(
                ast.MatchAs, name=instruction.argval
            ):
                return

            if inst_match("COMPARE_OP", argval="==") and node_match(ast.MatchSequence):
                return

            if inst_match("COMPARE_OP", argval="==") and node_match(ast.MatchValue):
                return

        if inst_match("BINARY_OP") and node_match(
            ast.AugAssign, op=op_type_map[instruction.argrepr.removesuffix("=")]
        ):
            # a+=5
            return

        if node_match(ast.Attribute, ctx=ast.Del) and inst_match(
            "DELETE_ATTR", argval=mangled_name(node)
        ):
            return

        if inst_match(
            (
                "JUMP_IF_TRUE_OR_POP",
                "JUMP_IF_FALSE_OR_POP",
                "POP_JUMP_IF_TRUE",
                "POP_JUMP_IF_FALSE",
            )
        ) and node_match(ast.BoolOp):
            # and/or short circuit
            return

        if inst_match("DELETE_SUBSCR") and node_match(ast.Subscript, ctx=ast.Del):
            return

        if (
            node_match(ast.Name, ctx=ast.Load)
            or (
                node_match(ast.Name, ctx=ast.Store)
                and isinstance(node.parent, ast.AugAssign)
            )
        ) and inst_match(
            (
                "LOAD_NAME",
                "LOAD_FAST",
                "LOAD_FAST_CHECK",
                "LOAD_GLOBAL",
                "LOAD_DEREF",
                "LOAD_FROM_DICT_OR_DEREF",
            ),
            argval=mangled_name(node),
        ):
            return

        if node_match(ast.Name, ctx=ast.Del) and inst_match(
            ("DELETE_NAME", "DELETE_GLOBAL", "DELETE_DEREF"), argval=mangled_name(node)
        ):
            return

        if node_match(ast.Constant) and inst_match(
            "LOAD_CONST", argval=cast(ast.Constant, node).value
        ):
            return

        if node_match(
            (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp, ast.For)
        ) and inst_match(("GET_ITER", "FOR_ITER")):
            return

        if sys.version_info >= (3, 12):
            if node_match(ast.UnaryOp, op=ast.UAdd) and inst_match(
                "CALL_INTRINSIC_1", argrepr="INTRINSIC_UNARY_POSITIVE"
            ):
                return

            if node_match(ast.Subscript) and inst_match("BINARY_SLICE"):
                return

            if node_match(ast.ImportFrom) and inst_match(
                "CALL_INTRINSIC_1", argrepr="INTRINSIC_IMPORT_STAR"
            ):
                return

            if (
                node_match(ast.Yield) or isinstance(node.parent, ast.GeneratorExp)
            ) and inst_match("CALL_INTRINSIC_1", argrepr="INTRINSIC_ASYNC_GEN_WRAP"):
                return

            if node_match(ast.Name) and inst_match("LOAD_DEREF",argval="__classdict__"):
                return

            if node_match(ast.TypeVar) and (
                inst_match("CALL_INTRINSIC_1", argrepr="INTRINSIC_TYPEVAR")
                or inst_match(
                    "CALL_INTRINSIC_2", argrepr="INTRINSIC_TYPEVAR_WITH_BOUND"
                )
                or inst_match(
                    "CALL_INTRINSIC_2", argrepr="INTRINSIC_TYPEVAR_WITH_CONSTRAINTS"
                )
                or inst_match(("STORE_FAST", "STORE_DEREF"), argrepr=mangled_name(node))
            ):
                return

            if node_match(ast.TypeVarTuple) and (
                inst_match("CALL_INTRINSIC_1", argrepr="INTRINSIC_TYPEVARTUPLE")
                or inst_match(("STORE_FAST", "STORE_DEREF"), argrepr=node.name)
            ):
                return

            if node_match(ast.ParamSpec) and (
                inst_match("CALL_INTRINSIC_1", argrepr="INTRINSIC_PARAMSPEC")

                or inst_match(("STORE_FAST", "STORE_DEREF"), argrepr=node.name)):
                return


            if node_match(ast.TypeAlias):
                if(
                    inst_match("CALL_INTRINSIC_1", argrepr="INTRINSIC_TYPEALIAS")
                    or inst_match(
                        ("STORE_NAME", "STORE_FAST", "STORE_DEREF"), argrepr=node.name.id
                    )
                    or inst_match("CALL")
                ):
                    return


            if node_match(ast.ClassDef) and node.type_params:
                if inst_match(
                    ("STORE_DEREF", "LOAD_DEREF", "LOAD_FROM_DICT_OR_DEREF"),
                    argrepr=".type_params",
                ):
                    return

                if inst_match(("STORE_FAST", "LOAD_FAST"), argrepr=".generic_base"):
                    return

                if inst_match(
                    "CALL_INTRINSIC_1", argrepr="INTRINSIC_SUBSCRIPT_GENERIC"
                ):
                    return

                if inst_match("LOAD_DEREF",argval="__classdict__"):
                    return

            if node_match((ast.FunctionDef,ast.AsyncFunctionDef)) and node.type_params:
                if inst_match("CALL"):
                    return

                if inst_match(
                    "CALL_INTRINSIC_2", argrepr="INTRINSIC_SET_FUNCTION_TYPE_PARAMS"
                ):
                    return

                if inst_match("LOAD_FAST",argval=".defaults"):
                    return

                if inst_match("LOAD_FAST",argval=".kwdefaults"):
                    return

            if inst_match("STORE_NAME", argval="__classdictcell__"):
                # this is a general thing
                return


            # f-strings

            if node_match(ast.JoinedStr) and (
                inst_match("LOAD_ATTR", argval="join")
                or inst_match(("LIST_APPEND", "CALL"))
            ):
                return

            if node_match(ast.FormattedValue) and inst_match("FORMAT_VALUE"):
                return

        if sys.version_info >= (3, 13):

            if inst_match("NOP"):
                return

            if inst_match("TO_BOOL") and node_match(ast.BoolOp):
                return

            if inst_match("CALL_KW") and node_match((ast.Call, ast.ClassDef)):
                return

            if inst_match("LOAD_FAST", argval=".type_params"):
                return

            if inst_match("LOAD_FAST", argval="__classdict__"):
                return

            if inst_match("LOAD_FAST") and node_match(
                (
                    ast.FunctionDef,
                    ast.ClassDef,
                    ast.TypeAlias,
                    ast.TypeVar,
                    ast.Lambda,
                    ast.AsyncFunctionDef,
                )
            ):
                # These are loads for closure variables.
                # It is difficult to check that this is actually closure variable, see:
                # https://github.com/alexmojaki/executing/pull/80#discussion_r1716027317
                return

            if (
                inst_match("LOAD_FAST")
                and node_match(ast.TypeAlias)
                and node.name.id == instruction.argval
            ):
                return

            if inst_match("STORE_NAME",argval="__static_attributes__"):
                # the node is the first node in the body
                return

            if inst_match("LOAD_FAST") and isinstance(node.parent,ast.TypeVar):
                return


        # old verifier

        typ: Type = type(None)
        op_type: Type = type(None)

        if op_name.startswith(("BINARY_SUBSCR", "SLICE+")):
            typ = ast.Subscript
            ctx = ast.Load
        elif op_name.startswith("BINARY_"):
            typ = ast.BinOp
            op_type = op_type_map[instruction.argrepr]
            extra_filter = lambda e: isinstance(cast(ast.BinOp, e).op, op_type)
        elif op_name.startswith("UNARY_"):
            typ = ast.UnaryOp
            op_type = dict(
                UNARY_POSITIVE=ast.UAdd,
                UNARY_NEGATIVE=ast.USub,
                UNARY_NOT=ast.Not,
                UNARY_INVERT=ast.Invert,
            )[op_name]
            extra_filter = lambda e: isinstance(cast(ast.UnaryOp, e).op, op_type)
        elif op_name in ("LOAD_ATTR", "LOAD_METHOD", "LOOKUP_METHOD","LOAD_SUPER_ATTR"):
            typ = ast.Attribute
            ctx = ast.Load
            extra_filter = lambda e: mangled_name(e) == instruction.argval
        elif op_name in (
            "LOAD_NAME",
            "LOAD_GLOBAL",
            "LOAD_FAST",
            "LOAD_DEREF",
            "LOAD_CLASSDEREF",
        ):
            typ = ast.Name
            ctx = ast.Load
            extra_filter = lambda e: cast(ast.Name, e).id == instruction.argval
        elif op_name in ("COMPARE_OP", "IS_OP", "CONTAINS_OP"):
            typ = ast.Compare
            extra_filter = lambda e: len(cast(ast.Compare, e).ops) == 1
        elif op_name.startswith(("STORE_SLICE", "STORE_SUBSCR")):
            ctx = ast.Store
            typ = ast.Subscript
        elif op_name.startswith("STORE_ATTR"):
            ctx = ast.Store
            typ = ast.Attribute
            extra_filter = lambda e: mangled_name(e) == instruction.argval

        node_ctx = getattr(node, "ctx", None)

        ctx_match = (
            ctx is not type(None)
            or not hasattr(node, "ctx")
            or isinstance(node_ctx, ctx)
        )

        # check for old verifier
        if isinstance(node, typ) and ctx_match and extra_filter(node):
            return

        # generate error

        title = "ast.%s is not created from %s" % (
            type(node).__name__,
            instruction.opname,
        )

        raise VerifierFailure(title, node, instruction)

    def instruction(self, index: int) -> Optional[dis.Instruction]:
        return self.bc_dict.get(index,None)

    def instruction_before(
        self, instruction: dis.Instruction
    ) -> Optional[dis.Instruction]:
        return self.bc_dict.get(instruction.offset - 2, None)

    def opname(self, index: int) -> str:
        i=self.instruction(index)
        if i is None:
            return "CACHE"
        return i.opname

    extra_node_types=()
    if sys.version_info >= (3,12):
        extra_node_types = (ast.type_param,)

    def find_node(
        self,
        index: int,
        match_positions: Sequence[str] = (
            "lineno",
            "end_lineno",
            "col_offset",
            "end_col_offset",
        ),
        typ: tuple[Type, ...] = (
            ast.expr,
            ast.stmt,
            ast.excepthandler,
            ast.pattern,
            *extra_node_types,
        ),
    ) -> EnhancedAST:
        instruction = self.instruction(index)
        assert instruction is not None

        position = instruction.positions
        assert position is not None and position.lineno is not None

        return only(
            cast(EnhancedAST, node)
            for node in self.source._nodes_by_line[position.lineno]
            if isinstance(node, typ)
            if not isinstance(node, ast.Expr)
            # matchvalue.value has the same positions as matchvalue themself, so we exclude ast.MatchValue
            if not isinstance(node, ast.MatchValue)
            if all(
                getattr(position, attr) == getattr(node, attr)
                for attr in match_positions
            )
        )