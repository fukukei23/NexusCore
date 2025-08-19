
# === NexusCore/openenv\Lib\site-packages\IPython\core\formatters.py ===
# -*- coding: utf-8 -*-
"""Display formatters.

This module defines the base instances in order to implement custom
formatters/mimetypes
got objects:

As we want to see internal IPython working we are going to use the following
function to diaply objects instead of the normal print or display method:

    >>> ip = get_ipython()
    >>> ip.display_formatter.format(...)
    ({'text/plain': 'Ellipsis'}, {})

This return a tuple with the mimebumdle for the current object, and the
associated metadata.


We can now define our own formatter and register it:


    >>> from IPython.core.formatters import BaseFormatter, FormatterABC


    >>> class LLMFormatter(BaseFormatter):
    ...
    ...     format_type = 'x-vendor/llm'
    ...     print_method = '_repr_llm_'
    ...     _return_type = (dict, str)

    >>> llm_formatter = LLMFormatter(parent=ip.display_formatter)

    >>> ip.display_formatter.formatters[LLMFormatter.format_type] = llm_formatter

Now any class that define `_repr_llm_` will return a x-vendor/llm as part of
it's display data:

    >>> class A:
    ...
    ...     def _repr_llm_(self, *kwargs):
    ...         return 'This a A'
    ...

    >>> ip.display_formatter.format(A())
    ({'text/plain': '<IPython.core.formatters.A at ...>', 'x-vendor/llm': 'This a A'}, {})

As usual, you can register methods for third party types (see
:ref:`third_party_formatting`)

    >>> def llm_int(obj):
    ...      return 'This is the integer %s, in between %s and %s'%(obj, obj-1, obj+1)

    >>> llm_formatter.for_type(int, llm_int)

    >>> ip.display_formatter.format(42)
    ({'text/plain': '42', 'x-vendor/llm': 'This is the integer 42, in between 41 and 43'}, {})


Inheritance diagram:

.. inheritance-diagram:: IPython.core.formatters
   :parts: 3
"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

import abc
import sys
import traceback
import warnings
from io import StringIO

from decorator import decorator

from traitlets.config.configurable import Configurable
from .getipython import get_ipython
from ..utils.sentinel import Sentinel
from ..utils.dir2 import get_real_method
from ..lib import pretty
from traitlets import (
    Bool, Dict, Integer, Unicode, CUnicode, ObjectName, List,
    ForwardDeclaredInstance,
    default, observe,
)

from typing import Any


class DisplayFormatter(Configurable):

    active_types = List(Unicode(),
        help="""List of currently active mime-types to display.
        You can use this to set a white-list for formats to display.

        Most users will not need to change this value.
        """,
    ).tag(config=True)

    @default('active_types')
    def _active_types_default(self):
        return self.format_types

    @observe('active_types')
    def _active_types_changed(self, change):
        for key, formatter in self.formatters.items():
            if key in change['new']:
                formatter.enabled = True
            else:
                formatter.enabled = False

    ipython_display_formatter = ForwardDeclaredInstance("FormatterABC")  # type: ignore

    @default("ipython_display_formatter")
    def _default_formatter(self):
        return IPythonDisplayFormatter(parent=self)

    mimebundle_formatter = ForwardDeclaredInstance("FormatterABC")  # type: ignore

    @default("mimebundle_formatter")
    def _default_mime_formatter(self):
        return MimeBundleFormatter(parent=self)

    # A dict of formatter whose keys are format types (MIME types) and whose
    # values are subclasses of BaseFormatter.
    formatters = Dict()

    @default("formatters")
    def _formatters_default(self):
        """Activate the default formatters."""
        formatter_classes = [
            PlainTextFormatter,
            HTMLFormatter,
            MarkdownFormatter,
            SVGFormatter,
            PNGFormatter,
            PDFFormatter,
            JPEGFormatter,
            LatexFormatter,
            JSONFormatter,
            JavascriptFormatter
        ]
        d = {}
        for cls in formatter_classes:
            f = cls(parent=self)
            d[f.format_type] = f
        return d

    def format(self, obj, include=None, exclude=None):
        """Return a format data dict for an object.

        By default all format types will be computed.

        The following MIME types are usually implemented:

        * text/plain
        * text/html
        * text/markdown
        * text/latex
        * application/json
        * application/javascript
        * application/pdf
        * image/png
        * image/jpeg
        * image/svg+xml

        Parameters
        ----------
        obj : object
            The Python object whose format data will be computed.
        include : list, tuple or set; optional
            A list of format type strings (MIME types) to include in the
            format data dict. If this is set *only* the format types included
            in this list will be computed.
        exclude : list, tuple or set; optional
            A list of format type string (MIME types) to exclude in the format
            data dict. If this is set all format types will be computed,
            except for those included in this argument.
            Mimetypes present in exclude will take precedence over the ones in include

        Returns
        -------
        (format_dict, metadata_dict) : tuple of two dicts
            format_dict is a dictionary of key/value pairs, one of each format that was
            generated for the object. The keys are the format types, which
            will usually be MIME type strings and the values and JSON'able
            data structure containing the raw data for the representation in
            that format.

            metadata_dict is a dictionary of metadata about each mime-type output.
            Its keys will be a strict subset of the keys in format_dict.

        Notes
        -----
            If an object implement `_repr_mimebundle_` as well as various
            `_repr_*_`, the data returned by `_repr_mimebundle_` will take
            precedence and the corresponding `_repr_*_` for this mimetype will
            not be called.

        """
        format_dict = {}
        md_dict = {}

        if self.ipython_display_formatter(obj):
            # object handled itself, don't proceed
            return {}, {}

        format_dict, md_dict = self.mimebundle_formatter(obj, include=include, exclude=exclude)

        if format_dict or md_dict:
            if include:
                format_dict = {k:v for k,v in format_dict.items() if k in include}
                md_dict = {k:v for k,v in md_dict.items() if k in include}
            if exclude:
                format_dict = {k:v for k,v in format_dict.items() if k not in exclude}
                md_dict = {k:v for k,v in md_dict.items() if k not in exclude}

        for format_type, formatter in self.formatters.items():
            if format_type in format_dict:
                # already got it from mimebundle, maybe don't render again.
                # exception: manually registered per-mime renderer
                # check priority:
                # 1. user-registered per-mime formatter
                # 2. mime-bundle (user-registered or repr method)
                # 3. default per-mime formatter (e.g. repr method)
                try:
                    formatter.lookup(obj)
                except KeyError:
                    # no special formatter, use mime-bundle-provided value
                    continue
            if include and format_type not in include:
                continue
            if exclude and format_type in exclude:
                continue

            md = None
            try:
                data = formatter(obj)
            except:
                # FIXME: log the exception
                raise

            # formatters can return raw data or (data, metadata)
            if isinstance(data, tuple) and len(data) == 2:
                data, md = data

            if data is not None:
                format_dict[format_type] = data
            if md is not None:
                md_dict[format_type] = md
        return format_dict, md_dict

    @property
    def format_types(self):
        """Return the format types (MIME types) of the active formatters."""
        return list(self.formatters.keys())


#-----------------------------------------------------------------------------
# Formatters for specific format types (text, html, svg, etc.)
#-----------------------------------------------------------------------------


def _safe_repr(obj):
    """Try to return a repr of an object

    always returns a string, at least.
    """
    try:
        return repr(obj)
    except Exception as e:
        return "un-repr-able object (%r)" % e


class FormatterWarning(UserWarning):
    """Warning class for errors in formatters"""

@decorator
def catch_format_error(method, self, *args, **kwargs):
    """show traceback on failed format call"""
    try:
        r = method(self, *args, **kwargs)
    except NotImplementedError:
        # don't warn on NotImplementedErrors
        return self._check_return(None, args[0])
    except Exception:
        exc_info = sys.exc_info()
        ip = get_ipython()
        if ip is not None:
            ip.showtraceback(exc_info)
        else:
            traceback.print_exception(*exc_info)
        return self._check_return(None, args[0])
    return self._check_return(r, args[0])


class FormatterABC(metaclass=abc.ABCMeta):
    """ Abstract base class for Formatters.

    A formatter is a callable class that is responsible for computing the
    raw format data for a particular format type (MIME type). For example,
    an HTML formatter would have a format type of `text/html` and would return
    the HTML representation of the object when called.
    """

    # The format type of the data returned, usually a MIME type.
    format_type = 'text/plain'

    # Is the formatter enabled...
    enabled = True

    @abc.abstractmethod
    def __call__(self, obj):
        """Return a JSON'able representation of the object.

        If the object cannot be formatted by this formatter,
        warn and return None.
        """
        return repr(obj)


def _mod_name_key(typ):
    """Return a (__module__, __name__) tuple for a type.

    Used as key in Formatter.deferred_printers.
    """
    module = getattr(typ, '__module__', None)
    name = getattr(typ, '__name__', None)
    return (module, name)


def _get_type(obj):
    """Return the type of an instance (old and new-style)"""
    return getattr(obj, '__class__', None) or type(obj)


_raise_key_error = Sentinel(
    "_raise_key_error",
    __name__,
    """
Special value to raise a KeyError

Raise KeyError in `BaseFormatter.pop` if passed as the default value to `pop`
""",
)


class BaseFormatter(Configurable):
    """A base formatter class that is configurable.

    This formatter should usually be used as the base class of all formatters.
    It is a traited :class:`Configurable` class and includes an extensible
    API for users to determine how their objects are formatted. The following
    logic is used to find a function to format an given object.

    1. The object is introspected to see if it has a method with the name
       :attr:`print_method`. If is does, that object is passed to that method
       for formatting.
    2. If no print method is found, three internal dictionaries are consulted
       to find print method: :attr:`singleton_printers`, :attr:`type_printers`
       and :attr:`deferred_printers`.

    Users should use these dictionaries to register functions that will be
    used to compute the format data for their objects (if those objects don't
    have the special print methods). The easiest way of using these
    dictionaries is through the :meth:`for_type` and :meth:`for_type_by_name`
    methods.

    If no function/callable is found to compute the format data, ``None`` is
    returned and this format type is not used.
    """

    format_type = Unicode("text/plain")
    _return_type: Any = str

    enabled = Bool(True).tag(config=True)

    print_method = ObjectName('__repr__')

    # The singleton printers.
    # Maps the IDs of the builtin singleton objects to the format functions.
    singleton_printers = Dict().tag(config=True)

    # The type-specific printers.
    # Map type objects to the format functions.
    type_printers = Dict().tag(config=True)

    # The deferred-import type-specific printers.
    # Map (modulename, classname) pairs to the format functions.
    deferred_printers = Dict().tag(config=True)

    @catch_format_error
    def __call__(self, obj):
        """Compute the format for an object."""
        if self.enabled:
            # lookup registered printer
            try:
                printer = self.lookup(obj)
            except KeyError:
                pass
            else:
                return printer(obj)
            # Finally look for special method names
            method = get_real_method(obj, self.print_method)
            if method is not None:
                return method()
            return None
        else:
            return None

    def __contains__(self, typ):
        """map in to lookup_by_type"""
        try:
            self.lookup_by_type(typ)
        except KeyError:
            return False
        else:
            return True

    def _check_return(self, r, obj):
        """Check that a return value is appropriate

        Return the value if so, None otherwise, warning if invalid.
        """
        if r is None or isinstance(r, self._return_type) or \
            (isinstance(r, tuple) and r and isinstance(r[0], self._return_type)):
            return r
        else:
            warnings.warn(
                "%s formatter returned invalid type %s (expected %s) for object: %s" % \
                (self.format_type, type(r), self._return_type, _safe_repr(obj)),
                FormatterWarning
            )

    def lookup(self, obj):
        """Look up the formatter for a given instance.

        Parameters
        ----------
        obj : object instance

        Returns
        -------
        f : callable
            The registered formatting callable for the type.

        Raises
        ------
        KeyError if the type has not been registered.
        """
        # look for singleton first
        obj_id = id(obj)
        if obj_id in self.singleton_printers:
            return self.singleton_printers[obj_id]
        # then lookup by type
        return self.lookup_by_type(_get_type(obj))

    def lookup_by_type(self, typ):
        """Look up the registered formatter for a type.

        Parameters
        ----------
        typ : type or '__module__.__name__' string for a type

        Returns
        -------
        f : callable
            The registered formatting callable for the type.

        Raises
        ------
        KeyError if the type has not been registered.
        """
        if isinstance(typ, str):
            typ_key = tuple(typ.rsplit('.',1))
            if typ_key not in self.deferred_printers:
                # We may have it cached in the type map. We will have to
                # iterate over all of the types to check.
                for cls in self.type_printers:
                    if _mod_name_key(cls) == typ_key:
                        return self.type_printers[cls]
            else:
                return self.deferred_printers[typ_key]
        else:
            for cls in pretty._get_mro(typ):
                if cls in self.type_printers or self._in_deferred_types(cls):
                    return self.type_printers[cls]

        # If we have reached here, the lookup failed.
        raise KeyError("No registered printer for {0!r}".format(typ))

    def for_type(self, typ, func=None):
        """Add a format function for a given type.

        Parameters
        ----------
        typ : type or '__module__.__name__' string for a type
            The class of the object that will be formatted using `func`.

        func : callable
            A callable for computing the format data.
            `func` will be called with the object to be formatted,
            and will return the raw data in this formatter's format.
            Subclasses may use a different call signature for the
            `func` argument.

            If `func` is None or not specified, there will be no change,
            only returning the current value.

        Returns
        -------
        oldfunc : callable
            The currently registered callable.
            If you are registering a new formatter,
            this will be the previous value (to enable restoring later).
        """
        # if string given, interpret as 'pkg.module.class_name'
        if isinstance(typ, str):
            type_module, type_name = typ.rsplit('.', 1)
            return self.for_type_by_name(type_module, type_name, func)

        try:
            oldfunc = self.lookup_by_type(typ)
        except KeyError:
            oldfunc = None

        if func is not None:
            self.type_printers[typ] = func

        return oldfunc

    def for_type_by_name(self, type_module, type_name, func=None):
        """Add a format function for a type specified by the full dotted
        module and name of the type, rather than the type of the object.

        Parameters
        ----------
        type_module : str
            The full dotted name of the module the type is defined in, like
            ``numpy``.

        type_name : str
            The name of the type (the class name), like ``dtype``

        func : callable
            A callable for computing the format data.
            `func` will be called with the object to be formatted,
            and will return the raw data in this formatter's format.
            Subclasses may use a different call signature for the
            `func` argument.

            If `func` is None or unspecified, there will be no change,
            only returning the current value.

        Returns
        -------
        oldfunc : callable
            The currently registered callable.
            If you are registering a new formatter,
            this will be the previous value (to enable restoring later).
        """
        key = (type_module, type_name)

        try:
            oldfunc = self.lookup_by_type("%s.%s" % key)
        except KeyError:
            oldfunc = None

        if func is not None:
            self.deferred_printers[key] = func
        return oldfunc

    def pop(self, typ, default=_raise_key_error):
        """Pop a formatter for the given type.

        Parameters
        ----------
        typ : type or '__module__.__name__' string for a type
        default : object
            value to be returned if no formatter is registered for typ.

        Returns
        -------
        obj : object
            The last registered object for the type.

        Raises
        ------
        KeyError if the type is not registered and default is not specified.
        """

        if isinstance(typ, str):
            typ_key = tuple(typ.rsplit('.',1))
            if typ_key not in self.deferred_printers:
                # We may have it cached in the type map. We will have to
                # iterate over all of the types to check.
                for cls in self.type_printers:
                    if _mod_name_key(cls) == typ_key:
                        old = self.type_printers.pop(cls)
                        break
                else:
                    old = default
            else:
                old = self.deferred_printers.pop(typ_key)
        else:
            if typ in self.type_printers:
                old = self.type_printers.pop(typ)
            else:
                old = self.deferred_printers.pop(_mod_name_key(typ), default)
        if old is _raise_key_error:
            raise KeyError("No registered value for {0!r}".format(typ))
        return old

    def _in_deferred_types(self, cls):
        """
        Check if the given class is specified in the deferred type registry.

        Successful matches will be moved to the regular type registry for future use.
        """
        mod = getattr(cls, '__module__', None)
        name = getattr(cls, '__name__', None)
        key = (mod, name)
        if key in self.deferred_printers:
            # Move the printer over to the regular registry.
            printer = self.deferred_printers.pop(key)
            self.type_printers[cls] = printer
            return True
        return False


class PlainTextFormatter(BaseFormatter):
    """The default pretty-printer.

    This uses :mod:`IPython.lib.pretty` to compute the format data of
    the object. If the object cannot be pretty printed, :func:`repr` is used.
    See the documentation of :mod:`IPython.lib.pretty` for details on
    how to write pretty printers.  Here is a simple example::

        def dtype_pprinter(obj, p, cycle):
            if cycle:
                return p.text('dtype(...)')
            if hasattr(obj, 'fields'):
                if obj.fields is None:
                    p.text(repr(obj))
                else:
                    p.begin_group(7, 'dtype([')
                    for i, field in enumerate(obj.descr):
                        if i > 0:
                            p.text(',')
                            p.breakable()
                        p.pretty(field)
                    p.end_group(7, '])')
    """

    # The format type of data returned.
    format_type = Unicode('text/plain')

    # This subclass ignores this attribute as it always need to return
    # something.
    enabled = Bool(True).tag(config=False)

    max_seq_length = Integer(pretty.MAX_SEQ_LENGTH,
        help="""Truncate large collections (lists, dicts, tuples, sets) to this size.

        Set to 0 to disable truncation.
        """,
    ).tag(config=True)

    # Look for a _repr_pretty_ methods to use for pretty printing.
    print_method = ObjectName('_repr_pretty_')

    # Whether to pretty-print or not.
    pprint = Bool(True).tag(config=True)

    # Whether to be verbose or not.
    verbose = Bool(False).tag(config=True)

    # The maximum width.
    max_width = Integer(79).tag(config=True)

    # The newline character.
    newline = Unicode('\n').tag(config=True)

    # format-string for pprinting floats
    float_format = Unicode('%r')
    # setter for float precision, either int or direct format-string
    float_precision = CUnicode('').tag(config=True)

    @observe('float_precision')
    def _float_precision_changed(self, change):
        """float_precision changed, set float_format accordingly.

        float_precision can be set by int or str.
        This will set float_format, after interpreting input.
        If numpy has been imported, numpy print precision will also be set.

        integer `n` sets format to '%.nf', otherwise, format set directly.

        An empty string returns to defaults (repr for float, 8 for numpy).

        This parameter can be set via the '%precision' magic.
        """
        new = change['new']
        if '%' in new:
            # got explicit format string
            fmt = new
            try:
                fmt%3.14159
            except Exception as e:
                raise ValueError("Precision must be int or format string, not %r"%new) from e
        elif new:
            # otherwise, should be an int
            try:
                i = int(new)
                assert i >= 0
            except ValueError as e:
                raise ValueError("Precision must be int or format string, not %r"%new) from e
            except AssertionError as e:
                raise ValueError("int precision must be non-negative, not %r"%i) from e

            fmt = '%%.%if'%i
            if 'numpy' in sys.modules:
                # set numpy precision if it has been imported
                import numpy
                numpy.set_printoptions(precision=i)
        else:
            # default back to repr
            fmt = '%r'
            if 'numpy' in sys.modules:
                import numpy
                # numpy default is 8
                numpy.set_printoptions(precision=8)
        self.float_format = fmt

    # Use the default pretty printers from IPython.lib.pretty.
    @default('singleton_printers')
    def _singleton_printers_default(self):
        return pretty._singleton_pprinters.copy()

    @default('type_printers')
    def _type_printers_default(self):
        d = pretty._type_pprinters.copy()
        d[float] = lambda obj,p,cycle: p.text(self.float_format%obj)
        # if NumPy is used, set precision for its float64 type
        if "numpy" in sys.modules:
            import numpy

            d[numpy.float64] = lambda obj, p, cycle: p.text(self.float_format % obj)
        return d

    @default('deferred_printers')
    def _deferred_printers_default(self):
        return pretty._deferred_type_pprinters.copy()

    #### FormatterABC interface ####

    @catch_format_error
    def __call__(self, obj):
        """Compute the pretty representation of the object."""
        if not self.pprint:
            return repr(obj)
        else:
            stream = StringIO()
            printer = pretty.RepresentationPrinter(stream, self.verbose,
                self.max_width, self.newline,
                max_seq_length=self.max_seq_length,
                singleton_pprinters=self.singleton_printers,
                type_pprinters=self.type_printers,
                deferred_pprinters=self.deferred_printers)
            printer.pretty(obj)
            printer.flush()
            return stream.getvalue()


class HTMLFormatter(BaseFormatter):
    """An HTML formatter.

    To define the callables that compute the HTML representation of your
    objects, define a :meth:`_repr_html_` method or use the :meth:`for_type`
    or :meth:`for_type_by_name` methods to register functions that handle
    this.

    The return value of this formatter should be a valid HTML snippet that
    could be injected into an existing DOM. It should *not* include the
    ```<html>`` or ```<body>`` tags.
    """
    format_type = Unicode('text/html')

    print_method = ObjectName('_repr_html_')


class MarkdownFormatter(BaseFormatter):
    """A Markdown formatter.

    To define the callables that compute the Markdown representation of your
    objects, define a :meth:`_repr_markdown_` method or use the :meth:`for_type`
    or :meth:`for_type_by_name` methods to register functions that handle
    this.

    The return value of this formatter should be a valid Markdown.
    """
    format_type = Unicode('text/markdown')

    print_method = ObjectName('_repr_markdown_')

class SVGFormatter(BaseFormatter):
    """An SVG formatter.

    To define the callables that compute the SVG representation of your
    objects, define a :meth:`_repr_svg_` method or use the :meth:`for_type`
    or :meth:`for_type_by_name` methods to register functions that handle
    this.

    The return value of this formatter should be valid SVG enclosed in
    ```<svg>``` tags, that could be injected into an existing DOM. It should
    *not* include the ```<html>`` or ```<body>`` tags.
    """
    format_type = Unicode('image/svg+xml')

    print_method = ObjectName('_repr_svg_')


class PNGFormatter(BaseFormatter):
    """A PNG formatter.

    To define the callables that compute the PNG representation of your
    objects, define a :meth:`_repr_png_` method or use the :meth:`for_type`
    or :meth:`for_type_by_name` methods to register functions that handle
    this.

    The return value of this formatter should be raw PNG data, *not*
    base64 encoded.
    """
    format_type = Unicode('image/png')

    print_method = ObjectName('_repr_png_')

    _return_type = (bytes, str)


class JPEGFormatter(BaseFormatter):
    """A JPEG formatter.

    To define the callables that compute the JPEG representation of your
    objects, define a :meth:`_repr_jpeg_` method or use the :meth:`for_type`
    or :meth:`for_type_by_name` methods to register functions that handle
    this.

    The return value of this formatter should be raw JPEG data, *not*
    base64 encoded.
    """
    format_type = Unicode('image/jpeg')

    print_method = ObjectName('_repr_jpeg_')

    _return_type = (bytes, str)


class LatexFormatter(BaseFormatter):
    """A LaTeX formatter.

    To define the callables that compute the LaTeX representation of your
    objects, define a :meth:`_repr_latex_` method or use the :meth:`for_type`
    or :meth:`for_type_by_name` methods to register functions that handle
    this.

    The return value of this formatter should be a valid LaTeX equation,
    enclosed in either ```$```, ```$$``` or another LaTeX equation
    environment.
    """
    format_type = Unicode('text/latex')

    print_method = ObjectName('_repr_latex_')


class JSONFormatter(BaseFormatter):
    """A JSON string formatter.

    To define the callables that compute the JSONable representation of
    your objects, define a :meth:`_repr_json_` method or use the :meth:`for_type`
    or :meth:`for_type_by_name` methods to register functions that handle
    this.

    The return value of this formatter should be a JSONable list or dict.
    JSON scalars (None, number, string) are not allowed, only dict or list containers.
    """
    format_type = Unicode('application/json')
    _return_type = (list, dict)

    print_method = ObjectName('_repr_json_')

    def _check_return(self, r, obj):
        """Check that a return value is appropriate

        Return the value if so, None otherwise, warning if invalid.
        """
        if r is None:
            return
        md = None
        if isinstance(r, tuple):
            # unpack data, metadata tuple for type checking on first element
            r, md = r

        assert not isinstance(
            r, str
        ), "JSON-as-string has been deprecated since IPython < 3"

        if md is not None:
            # put the tuple back together
            r = (r, md)
        return super(JSONFormatter, self)._check_return(r, obj)


class JavascriptFormatter(BaseFormatter):
    """A Javascript formatter.

    To define the callables that compute the Javascript representation of
    your objects, define a :meth:`_repr_javascript_` method or use the
    :meth:`for_type` or :meth:`for_type_by_name` methods to register functions
    that handle this.

    The return value of this formatter should be valid Javascript code and
    should *not* be enclosed in ```<script>``` tags.
    """
    format_type = Unicode('application/javascript')

    print_method = ObjectName('_repr_javascript_')


class PDFFormatter(BaseFormatter):
    """A PDF formatter.

    To define the callables that compute the PDF representation of your
    objects, define a :meth:`_repr_pdf_` method or use the :meth:`for_type`
    or :meth:`for_type_by_name` methods to register functions that handle
    this.

    The return value of this formatter should be raw PDF data, *not*
    base64 encoded.
    """
    format_type = Unicode('application/pdf')

    print_method = ObjectName('_repr_pdf_')

    _return_type = (bytes, str)

class IPythonDisplayFormatter(BaseFormatter):
    """An escape-hatch Formatter for objects that know how to display themselves.

    To define the callables that compute the representation of your
    objects, define a :meth:`_ipython_display_` method or use the :meth:`for_type`
    or :meth:`for_type_by_name` methods to register functions that handle
    this. Unlike mime-type displays, this method should not return anything,
    instead calling any appropriate display methods itself.

    This display formatter has highest priority.
    If it fires, no other display formatter will be called.

    Prior to IPython 6.1, `_ipython_display_` was the only way to display custom mime-types
    without registering a new Formatter.

    IPython 6.1 introduces `_repr_mimebundle_` for displaying custom mime-types,
    so `_ipython_display_` should only be used for objects that require unusual
    display patterns, such as multiple display calls.
    """
    print_method = ObjectName('_ipython_display_')
    _return_type = (type(None), bool)

    @catch_format_error
    def __call__(self, obj):
        """Compute the format for an object."""
        if self.enabled:
            # lookup registered printer
            try:
                printer = self.lookup(obj)
            except KeyError:
                pass
            else:
                printer(obj)
                return True
            # Finally look for special method names
            method = get_real_method(obj, self.print_method)
            if method is not None:
                method()
                return True


class MimeBundleFormatter(BaseFormatter):
    """A Formatter for arbitrary mime-types.

    Unlike other `_repr_<mimetype>_` methods,
    `_repr_mimebundle_` should return mime-bundle data,
    either the mime-keyed `data` dictionary or the tuple `(data, metadata)`.
    Any mime-type is valid.

    To define the callables that compute the mime-bundle representation of your
    objects, define a :meth:`_repr_mimebundle_` method or use the :meth:`for_type`
    or :meth:`for_type_by_name` methods to register functions that handle
    this.

    .. versionadded:: 6.1
    """
    print_method = ObjectName('_repr_mimebundle_')
    _return_type = dict

    def _check_return(self, r, obj):
        r = super(MimeBundleFormatter, self)._check_return(r, obj)
        # always return (data, metadata):
        if r is None:
            return {}, {}
        if not isinstance(r, tuple):
            return r, {}
        return r

    @catch_format_error
    def __call__(self, obj, include=None, exclude=None):
        """Compute the format for an object.

        Identical to parent's method but we pass extra parameters to the method.

        Unlike other _repr_*_ `_repr_mimebundle_` should allow extra kwargs, in
        particular `include` and `exclude`.
        """
        if self.enabled:
            # lookup registered printer
            try:
                printer = self.lookup(obj)
            except KeyError:
                pass
            else:
                return printer(obj)
            # Finally look for special method names
            method = get_real_method(obj, self.print_method)

            if method is not None:
                return method(include=include, exclude=exclude)
            return None
        else:
            return None


FormatterABC.register(BaseFormatter)
FormatterABC.register(PlainTextFormatter)
FormatterABC.register(HTMLFormatter)
FormatterABC.register(MarkdownFormatter)
FormatterABC.register(SVGFormatter)
FormatterABC.register(PNGFormatter)
FormatterABC.register(PDFFormatter)
FormatterABC.register(JPEGFormatter)
FormatterABC.register(LatexFormatter)
FormatterABC.register(JSONFormatter)
FormatterABC.register(JavascriptFormatter)
FormatterABC.register(IPythonDisplayFormatter)
FormatterABC.register(MimeBundleFormatter)


def format_display_data(obj, include=None, exclude=None):
    """Return a format data dict for an object.

    By default all format types will be computed.

    Parameters
    ----------
    obj : object
        The Python object whose format data will be computed.

    Returns
    -------
    format_dict : dict
        A dictionary of key/value pairs, one or each format that was
        generated for the object. The keys are the format types, which
        will usually be MIME type strings and the values and JSON'able
        data structure containing the raw data for the representation in
        that format.
    include : list or tuple, optional
        A list of format type strings (MIME types) to include in the
        format data dict. If this is set *only* the format types included
        in this list will be computed.
    exclude : list or tuple, optional
        A list of format type string (MIME types) to exclude in the format
        data dict. If this is set all format types will be computed,
        except for those included in this argument.
    """
    from .interactiveshell import InteractiveShell

    return InteractiveShell.instance().display_formatter.format(
        obj,
        include,
        exclude
    )

# === NexusCore/openenv\Lib\site-packages\numpy\_core\records.py ===
"""
This module contains a set of functions for record arrays.
"""
import os
import warnings
from collections import Counter
from contextlib import nullcontext

from numpy._utils import set_module

from . import numeric as sb
from . import numerictypes as nt
from .arrayprint import _get_legacy_print_mode

# All of the functions allow formats to be a dtype
__all__ = [
    'record', 'recarray', 'format_parser', 'fromarrays', 'fromrecords',
    'fromstring', 'fromfile', 'array', 'find_duplicate',
]


ndarray = sb.ndarray

_byteorderconv = {'b': '>',
                  'l': '<',
                  'n': '=',
                  'B': '>',
                  'L': '<',
                  'N': '=',
                  'S': 's',
                  's': 's',
                  '>': '>',
                  '<': '<',
                  '=': '=',
                  '|': '|',
                  'I': '|',
                  'i': '|'}

# formats regular expression
# allows multidimensional spec with a tuple syntax in front
# of the letter code '(2,3)f4' and ' (  2 ,  3  )  f4  '
# are equally allowed

numfmt = nt.sctypeDict


@set_module('numpy.rec')
def find_duplicate(list):
    """Find duplication in a list, return a list of duplicated elements"""
    return [
        item
        for item, counts in Counter(list).items()
        if counts > 1
    ]


@set_module('numpy.rec')
class format_parser:
    """
    Class to convert formats, names, titles description to a dtype.

    After constructing the format_parser object, the dtype attribute is
    the converted data-type:
    ``dtype = format_parser(formats, names, titles).dtype``

    Attributes
    ----------
    dtype : dtype
        The converted data-type.

    Parameters
    ----------
    formats : str or list of str
        The format description, either specified as a string with
        comma-separated format descriptions in the form ``'f8, i4, S5'``, or
        a list of format description strings  in the form
        ``['f8', 'i4', 'S5']``.
    names : str or list/tuple of str
        The field names, either specified as a comma-separated string in the
        form ``'col1, col2, col3'``, or as a list or tuple of strings in the
        form ``['col1', 'col2', 'col3']``.
        An empty list can be used, in that case default field names
        ('f0', 'f1', ...) are used.
    titles : sequence
        Sequence of title strings. An empty list can be used to leave titles
        out.
    aligned : bool, optional
        If True, align the fields by padding as the C-compiler would.
        Default is False.
    byteorder : str, optional
        If specified, all the fields will be changed to the
        provided byte-order.  Otherwise, the default byte-order is
        used. For all available string specifiers, see `dtype.newbyteorder`.

    See Also
    --------
    numpy.dtype, numpy.typename

    Examples
    --------
    >>> import numpy as np
    >>> np.rec.format_parser(['<f8', '<i4'], ['col1', 'col2'],
    ...                      ['T1', 'T2']).dtype
    dtype([(('T1', 'col1'), '<f8'), (('T2', 'col2'), '<i4')])

    `names` and/or `titles` can be empty lists. If `titles` is an empty list,
    titles will simply not appear. If `names` is empty, default field names
    will be used.

    >>> np.rec.format_parser(['f8', 'i4', 'a5'], ['col1', 'col2', 'col3'],
    ...                      []).dtype
    dtype([('col1', '<f8'), ('col2', '<i4'), ('col3', '<S5')])
    >>> np.rec.format_parser(['<f8', '<i4', '<a5'], [], []).dtype
    dtype([('f0', '<f8'), ('f1', '<i4'), ('f2', 'S5')])

    """

    def __init__(self, formats, names, titles, aligned=False, byteorder=None):
        self._parseFormats(formats, aligned)
        self._setfieldnames(names, titles)
        self._createdtype(byteorder)

    def _parseFormats(self, formats, aligned=False):
        """ Parse the field formats """

        if formats is None:
            raise ValueError("Need formats argument")
        if isinstance(formats, list):
            dtype = sb.dtype(
                [
                    (f'f{i}', format_)
                    for i, format_ in enumerate(formats)
                ],
                aligned,
            )
        else:
            dtype = sb.dtype(formats, aligned)
        fields = dtype.fields
        if fields is None:
            dtype = sb.dtype([('f1', dtype)], aligned)
            fields = dtype.fields
        keys = dtype.names
        self._f_formats = [fields[key][0] for key in keys]
        self._offsets = [fields[key][1] for key in keys]
        self._nfields = len(keys)

    def _setfieldnames(self, names, titles):
        """convert input field names into a list and assign to the _names
        attribute """

        if names:
            if type(names) in [list, tuple]:
                pass
            elif isinstance(names, str):
                names = names.split(',')
            else:
                raise NameError(f"illegal input names {repr(names)}")

            self._names = [n.strip() for n in names[:self._nfields]]
        else:
            self._names = []

        # if the names are not specified, they will be assigned as
        #  "f0, f1, f2,..."
        # if not enough names are specified, they will be assigned as "f[n],
        # f[n+1],..." etc. where n is the number of specified names..."
        self._names += ['f%d' % i for i in range(len(self._names),
                                                 self._nfields)]
        # check for redundant names
        _dup = find_duplicate(self._names)
        if _dup:
            raise ValueError(f"Duplicate field names: {_dup}")

        if titles:
            self._titles = [n.strip() for n in titles[:self._nfields]]
        else:
            self._titles = []
            titles = []

        if self._nfields > len(titles):
            self._titles += [None] * (self._nfields - len(titles))

    def _createdtype(self, byteorder):
        dtype = sb.dtype({
            'names': self._names,
            'formats': self._f_formats,
            'offsets': self._offsets,
            'titles': self._titles,
        })
        if byteorder is not None:
            byteorder = _byteorderconv[byteorder[0]]
            dtype = dtype.newbyteorder(byteorder)

        self.dtype = dtype


class record(nt.void):
    """A data-type scalar that allows field access as attribute lookup.
    """

    # manually set name and module so that this class's type shows up
    # as numpy.record when printed
    __name__ = 'record'
    __module__ = 'numpy'

    def __repr__(self):
        if _get_legacy_print_mode() <= 113:
            return self.__str__()
        return super().__repr__()

    def __str__(self):
        if _get_legacy_print_mode() <= 113:
            return str(self.item())
        return super().__str__()

    def __getattribute__(self, attr):
        if attr in ('setfield', 'getfield', 'dtype'):
            return nt.void.__getattribute__(self, attr)
        try:
            return nt.void.__getattribute__(self, attr)
        except AttributeError:
            pass
        fielddict = nt.void.__getattribute__(self, 'dtype').fields
        res = fielddict.get(attr, None)
        if res:
            obj = self.getfield(*res[:2])
            # if it has fields return a record,
            # otherwise return the object
            try:
                dt = obj.dtype
            except AttributeError:
                # happens if field is Object type
                return obj
            if dt.names is not None:
                return obj.view((self.__class__, obj.dtype))
            return obj
        else:
            raise AttributeError(f"'record' object has no attribute '{attr}'")

    def __setattr__(self, attr, val):
        if attr in ('setfield', 'getfield', 'dtype'):
            raise AttributeError(f"Cannot set '{attr}' attribute")
        fielddict = nt.void.__getattribute__(self, 'dtype').fields
        res = fielddict.get(attr, None)
        if res:
            return self.setfield(val, *res[:2])
        elif getattr(self, attr, None):
            return nt.void.__setattr__(self, attr, val)
        else:
            raise AttributeError(f"'record' object has no attribute '{attr}'")

    def __getitem__(self, indx):
        obj = nt.void.__getitem__(self, indx)

        # copy behavior of record.__getattribute__,
        if isinstance(obj, nt.void) and obj.dtype.names is not None:
            return obj.view((self.__class__, obj.dtype))
        else:
            # return a single element
            return obj

    def pprint(self):
        """Pretty-print all fields."""
        # pretty-print all fields
        names = self.dtype.names
        maxlen = max(len(name) for name in names)
        fmt = '%% %ds: %%s' % maxlen
        rows = [fmt % (name, getattr(self, name)) for name in names]
        return "\n".join(rows)

# The recarray is almost identical to a standard array (which supports
#   named fields already)  The biggest difference is that it can use
#   attribute-lookup to find the fields and it is constructed using
#   a record.

# If byteorder is given it forces a particular byteorder on all
#  the fields (and any subfields)


@set_module("numpy.rec")
class recarray(ndarray):
    """Construct an ndarray that allows field access using attributes.

    Arrays may have a data-types containing fields, analogous
    to columns in a spread sheet.  An example is ``[(x, int), (y, float)]``,
    where each entry in the array is a pair of ``(int, float)``.  Normally,
    these attributes are accessed using dictionary lookups such as ``arr['x']``
    and ``arr['y']``.  Record arrays allow the fields to be accessed as members
    of the array, using ``arr.x`` and ``arr.y``.

    Parameters
    ----------
    shape : tuple
        Shape of output array.
    dtype : data-type, optional
        The desired data-type.  By default, the data-type is determined
        from `formats`, `names`, `titles`, `aligned` and `byteorder`.
    formats : list of data-types, optional
        A list containing the data-types for the different columns, e.g.
        ``['i4', 'f8', 'i4']``.  `formats` does *not* support the new
        convention of using types directly, i.e. ``(int, float, int)``.
        Note that `formats` must be a list, not a tuple.
        Given that `formats` is somewhat limited, we recommend specifying
        `dtype` instead.
    names : tuple of str, optional
        The name of each column, e.g. ``('x', 'y', 'z')``.
    buf : buffer, optional
        By default, a new array is created of the given shape and data-type.
        If `buf` is specified and is an object exposing the buffer interface,
        the array will use the memory from the existing buffer.  In this case,
        the `offset` and `strides` keywords are available.

    Other Parameters
    ----------------
    titles : tuple of str, optional
        Aliases for column names.  For example, if `names` were
        ``('x', 'y', 'z')`` and `titles` is
        ``('x_coordinate', 'y_coordinate', 'z_coordinate')``, then
        ``arr['x']`` is equivalent to both ``arr.x`` and ``arr.x_coordinate``.
    byteorder : {'<', '>', '='}, optional
        Byte-order for all fields.
    aligned : bool, optional
        Align the fields in memory as the C-compiler would.
    strides : tuple of ints, optional
        Buffer (`buf`) is interpreted according to these strides (strides
        define how many bytes each array element, row, column, etc.
        occupy in memory).
    offset : int, optional
        Start reading buffer (`buf`) from this offset onwards.
    order : {'C', 'F'}, optional
        Row-major (C-style) or column-major (Fortran-style) order.

    Returns
    -------
    rec : recarray
        Empty array of the given shape and type.

    See Also
    --------
    numpy.rec.fromrecords : Construct a record array from data.
    numpy.record : fundamental data-type for `recarray`.
    numpy.rec.format_parser : determine data-type from formats, names, titles.

    Notes
    -----
    This constructor can be compared to ``empty``: it creates a new record
    array but does not fill it with data.  To create a record array from data,
    use one of the following methods:

    1. Create a standard ndarray and convert it to a record array,
       using ``arr.view(np.recarray)``
    2. Use the `buf` keyword.
    3. Use `np.rec.fromrecords`.

    Examples
    --------
    Create an array with two fields, ``x`` and ``y``:

    >>> import numpy as np
    >>> x = np.array([(1.0, 2), (3.0, 4)], dtype=[('x', '<f8'), ('y', '<i8')])
    >>> x
    array([(1., 2), (3., 4)], dtype=[('x', '<f8'), ('y', '<i8')])

    >>> x['x']
    array([1., 3.])

    View the array as a record array:

    >>> x = x.view(np.recarray)

    >>> x.x
    array([1., 3.])

    >>> x.y
    array([2, 4])

    Create a new, empty record array:

    >>> np.recarray((2,),
    ... dtype=[('x', int), ('y', float), ('z', int)]) #doctest: +SKIP
    rec.array([(-1073741821, 1.2249118382103472e-301, 24547520),
           (3471280, 1.2134086255804012e-316, 0)],
          dtype=[('x', '<i4'), ('y', '<f8'), ('z', '<i4')])

    """

    def __new__(subtype, shape, dtype=None, buf=None, offset=0, strides=None,
                formats=None, names=None, titles=None,
                byteorder=None, aligned=False, order='C'):

        if dtype is not None:
            descr = sb.dtype(dtype)
        else:
            descr = format_parser(
                formats, names, titles, aligned, byteorder
            ).dtype

        if buf is None:
            self = ndarray.__new__(
                subtype, shape, (record, descr), order=order
            )
        else:
            self = ndarray.__new__(
                subtype, shape, (record, descr), buffer=buf,
                offset=offset, strides=strides, order=order
            )
        return self

    def __array_finalize__(self, obj):
        if self.dtype.type is not record and self.dtype.names is not None:
            # if self.dtype is not np.record, invoke __setattr__ which will
            # convert it to a record if it is a void dtype.
            self.dtype = self.dtype

    def __getattribute__(self, attr):
        # See if ndarray has this attr, and return it if so. (note that this
        # means a field with the same name as an ndarray attr cannot be
        # accessed by attribute).
        try:
            return object.__getattribute__(self, attr)
        except AttributeError:  # attr must be a fieldname
            pass

        # look for a field with this name
        fielddict = ndarray.__getattribute__(self, 'dtype').fields
        try:
            res = fielddict[attr][:2]
        except (TypeError, KeyError) as e:
            raise AttributeError(f"recarray has no attribute {attr}") from e
        obj = self.getfield(*res)

        # At this point obj will always be a recarray, since (see
        # PyArray_GetField) the type of obj is inherited. Next, if obj.dtype is
        # non-structured, convert it to an ndarray. Then if obj is structured
        # with void type convert it to the same dtype.type (eg to preserve
        # numpy.record type if present), since nested structured fields do not
        # inherit type. Don't do this for non-void structures though.
        if obj.dtype.names is not None:
            if issubclass(obj.dtype.type, nt.void):
                return obj.view(dtype=(self.dtype.type, obj.dtype))
            return obj
        else:
            return obj.view(ndarray)

    # Save the dictionary.
    # If the attr is a field name and not in the saved dictionary
    # Undo any "setting" of the attribute and do a setfield
    # Thus, you can't create attributes on-the-fly that are field names.
    def __setattr__(self, attr, val):

        # Automatically convert (void) structured types to records
        # (but not non-void structures, subarrays, or non-structured voids)
        if (
            attr == 'dtype' and
            issubclass(val.type, nt.void) and
            val.names is not None
        ):
            val = sb.dtype((record, val))

        newattr = attr not in self.__dict__
        try:
            ret = object.__setattr__(self, attr, val)
        except Exception:
            fielddict = ndarray.__getattribute__(self, 'dtype').fields or {}
            if attr not in fielddict:
                raise
        else:
            fielddict = ndarray.__getattribute__(self, 'dtype').fields or {}
            if attr not in fielddict:
                return ret
            if newattr:
                # We just added this one or this setattr worked on an
                # internal attribute.
                try:
                    object.__delattr__(self, attr)
                except Exception:
                    return ret
        try:
            res = fielddict[attr][:2]
        except (TypeError, KeyError) as e:
            raise AttributeError(
                f"record array has no attribute {attr}"
            ) from e
        return self.setfield(val, *res)

    def __getitem__(self, indx):
        obj = super().__getitem__(indx)

        # copy behavior of getattr, except that here
        # we might also be returning a single element
        if isinstance(obj, ndarray):
            if obj.dtype.names is not None:
                obj = obj.view(type(self))
                if issubclass(obj.dtype.type, nt.void):
                    return obj.view(dtype=(self.dtype.type, obj.dtype))
                return obj
            else:
                return obj.view(type=ndarray)
        else:
            # return a single element
            return obj

    def __repr__(self):

        repr_dtype = self.dtype
        if (
            self.dtype.type is record or
            not issubclass(self.dtype.type, nt.void)
        ):
            # If this is a full record array (has numpy.record dtype),
            # or if it has a scalar (non-void) dtype with no records,
            # represent it using the rec.array function. Since rec.array
            # converts dtype to a numpy.record for us, convert back
            # to non-record before printing
            if repr_dtype.type is record:
                repr_dtype = sb.dtype((nt.void, repr_dtype))
            prefix = "rec.array("
            fmt = 'rec.array(%s,%sdtype=%s)'
        else:
            # otherwise represent it using np.array plus a view
            # This should only happen if the user is playing
            # strange games with dtypes.
            prefix = "array("
            fmt = 'array(%s,%sdtype=%s).view(numpy.recarray)'

        # get data/shape string. logic taken from numeric.array_repr
        if self.size > 0 or self.shape == (0,):
            lst = sb.array2string(
                self, separator=', ', prefix=prefix, suffix=',')
        else:
            # show zero-length shape unless it is (0,)
            lst = f"[], shape={repr(self.shape)}"

        lf = '\n' + ' ' * len(prefix)
        if _get_legacy_print_mode() <= 113:
            lf = ' ' + lf  # trailing space
        return fmt % (lst, lf, repr_dtype)

    def field(self, attr, val=None):
        if isinstance(attr, int):
            names = ndarray.__getattribute__(self, 'dtype').names
            attr = names[attr]

        fielddict = ndarray.__getattribute__(self, 'dtype').fields

        res = fielddict[attr][:2]

        if val is None:
            obj = self.getfield(*res)
            if obj.dtype.names is not None:
                return obj
            return obj.view(ndarray)
        else:
            return self.setfield(val, *res)


def _deprecate_shape_0_as_None(shape):
    if shape == 0:
        warnings.warn(
            "Passing `shape=0` to have the shape be inferred is deprecated, "
            "and in future will be equivalent to `shape=(0,)`. To infer "
            "the shape and suppress this warning, pass `shape=None` instead.",
            FutureWarning, stacklevel=3)
        return None
    else:
        return shape


@set_module("numpy.rec")
def fromarrays(arrayList, dtype=None, shape=None, formats=None,
               names=None, titles=None, aligned=False, byteorder=None):
    """Create a record array from a (flat) list of arrays

    Parameters
    ----------
    arrayList : list or tuple
        List of array-like objects (such as lists, tuples,
        and ndarrays).
    dtype : data-type, optional
        valid dtype for all arrays
    shape : int or tuple of ints, optional
        Shape of the resulting array. If not provided, inferred from
        ``arrayList[0]``.
    formats, names, titles, aligned, byteorder :
        If `dtype` is ``None``, these arguments are passed to
        `numpy.rec.format_parser` to construct a dtype. See that function for
        detailed documentation.

    Returns
    -------
    np.recarray
        Record array consisting of given arrayList columns.

    Examples
    --------
    >>> x1=np.array([1,2,3,4])
    >>> x2=np.array(['a','dd','xyz','12'])
    >>> x3=np.array([1.1,2,3,4])
    >>> r = np.rec.fromarrays([x1,x2,x3],names='a,b,c')
    >>> print(r[1])
    (2, 'dd', 2.0) # may vary
    >>> x1[1]=34
    >>> r.a
    array([1, 2, 3, 4])

    >>> x1 = np.array([1, 2, 3, 4])
    >>> x2 = np.array(['a', 'dd', 'xyz', '12'])
    >>> x3 = np.array([1.1, 2, 3,4])
    >>> r = np.rec.fromarrays(
    ...     [x1, x2, x3],
    ...     dtype=np.dtype([('a', np.int32), ('b', 'S3'), ('c', np.float32)]))
    >>> r
    rec.array([(1, b'a', 1.1), (2, b'dd', 2. ), (3, b'xyz', 3. ),
               (4, b'12', 4. )],
              dtype=[('a', '<i4'), ('b', 'S3'), ('c', '<f4')])
    """

    arrayList = [sb.asarray(x) for x in arrayList]

    # NumPy 1.19.0, 2020-01-01
    shape = _deprecate_shape_0_as_None(shape)

    if shape is None:
        shape = arrayList[0].shape
    elif isinstance(shape, int):
        shape = (shape,)

    if formats is None and dtype is None:
        # go through each object in the list to see if it is an ndarray
        # and determine the formats.
        formats = [obj.dtype for obj in arrayList]

    if dtype is not None:
        descr = sb.dtype(dtype)
    else:
        descr = format_parser(formats, names, titles, aligned, byteorder).dtype
    _names = descr.names

    # Determine shape from data-type.
    if len(descr) != len(arrayList):
        raise ValueError("mismatch between the number of fields "
                "and the number of arrays")

    d0 = descr[0].shape
    nn = len(d0)
    if nn > 0:
        shape = shape[:-nn]

    _array = recarray(shape, descr)

    # populate the record array (makes a copy)
    for k, obj in enumerate(arrayList):
        nn = descr[k].ndim
        testshape = obj.shape[:obj.ndim - nn]
        name = _names[k]
        if testshape != shape:
            raise ValueError(f'array-shape mismatch in array {k} ("{name}")')

        _array[name] = obj

    return _array


@set_module("numpy.rec")
def fromrecords(recList, dtype=None, shape=None, formats=None, names=None,
                titles=None, aligned=False, byteorder=None):
    """Create a recarray from a list of records in text form.

    Parameters
    ----------
    recList : sequence
        data in the same field may be heterogeneous - they will be promoted
        to the highest data type.
    dtype : data-type, optional
        valid dtype for all arrays
    shape : int or tuple of ints, optional
        shape of each array.
    formats, names, titles, aligned, byteorder :
        If `dtype` is ``None``, these arguments are passed to
        `numpy.format_parser` to construct a dtype. See that function for
        detailed documentation.

        If both `formats` and `dtype` are None, then this will auto-detect
        formats. Use list of tuples rather than list of lists for faster
        processing.

    Returns
    -------
    np.recarray
        record array consisting of given recList rows.

    Examples
    --------
    >>> r=np.rec.fromrecords([(456,'dbe',1.2),(2,'de',1.3)],
    ... names='col1,col2,col3')
    >>> print(r[0])
    (456, 'dbe', 1.2)
    >>> r.col1
    array([456,   2])
    >>> r.col2
    array(['dbe', 'de'], dtype='<U3')
    >>> import pickle
    >>> pickle.loads(pickle.dumps(r))
    rec.array([(456, 'dbe', 1.2), (  2, 'de', 1.3)],
              dtype=[('col1', '<i8'), ('col2', '<U3'), ('col3', '<f8')])
    """

    if formats is None and dtype is None:  # slower
        obj = sb.array(recList, dtype=object)
        arrlist = [
            sb.array(obj[..., i].tolist()) for i in range(obj.shape[-1])
        ]
        return fromarrays(arrlist, formats=formats, shape=shape, names=names,
                          titles=titles, aligned=aligned, byteorder=byteorder)

    if dtype is not None:
        descr = sb.dtype((record, dtype))
    else:
        descr = format_parser(
            formats, names, titles, aligned, byteorder
        ).dtype

    try:
        retval = sb.array(recList, dtype=descr)
    except (TypeError, ValueError):
        # NumPy 1.19.0, 2020-01-01
        shape = _deprecate_shape_0_as_None(shape)
        if shape is None:
            shape = len(recList)
        if isinstance(shape, int):
            shape = (shape,)
        if len(shape) > 1:
            raise ValueError("Can only deal with 1-d array.")
        _array = recarray(shape, descr)
        for k in range(_array.size):
            _array[k] = tuple(recList[k])
        # list of lists instead of list of tuples ?
        # 2018-02-07, 1.14.1
        warnings.warn(
            "fromrecords expected a list of tuples, may have received a list "
            "of lists instead. In the future that will raise an error",
            FutureWarning, stacklevel=2)
        return _array
    else:
        if shape is not None and retval.shape != shape:
            retval.shape = shape

    res = retval.view(recarray)

    return res


@set_module("numpy.rec")
def fromstring(datastring, dtype=None, shape=None, offset=0, formats=None,
               names=None, titles=None, aligned=False, byteorder=None):
    r"""Create a record array from binary data

    Note that despite the name of this function it does not accept `str`
    instances.

    Parameters
    ----------
    datastring : bytes-like
        Buffer of binary data
    dtype : data-type, optional
        Valid dtype for all arrays
    shape : int or tuple of ints, optional
        Shape of each array.
    offset : int, optional
        Position in the buffer to start reading from.
    formats, names, titles, aligned, byteorder :
        If `dtype` is ``None``, these arguments are passed to
        `numpy.format_parser` to construct a dtype. See that function for
        detailed documentation.


    Returns
    -------
    np.recarray
        Record array view into the data in datastring. This will be readonly
        if `datastring` is readonly.

    See Also
    --------
    numpy.frombuffer

    Examples
    --------
    >>> a = b'\x01\x02\x03abc'
    >>> np.rec.fromstring(a, dtype='u1,u1,u1,S3')
    rec.array([(1, 2, 3, b'abc')],
            dtype=[('f0', 'u1'), ('f1', 'u1'), ('f2', 'u1'), ('f3', 'S3')])

    >>> grades_dtype = [('Name', (np.str_, 10)), ('Marks', np.float64),
    ...                 ('GradeLevel', np.int32)]
    >>> grades_array = np.array([('Sam', 33.3, 3), ('Mike', 44.4, 5),
    ...                         ('Aadi', 66.6, 6)], dtype=grades_dtype)
    >>> np.rec.fromstring(grades_array.tobytes(), dtype=grades_dtype)
    rec.array([('Sam', 33.3, 3), ('Mike', 44.4, 5), ('Aadi', 66.6, 6)],
            dtype=[('Name', '<U10'), ('Marks', '<f8'), ('GradeLevel', '<i4')])

    >>> s = '\x01\x02\x03abc'
    >>> np.rec.fromstring(s, dtype='u1,u1,u1,S3')
    Traceback (most recent call last):
       ...
    TypeError: a bytes-like object is required, not 'str'
    """

    if dtype is None and formats is None:
        raise TypeError("fromstring() needs a 'dtype' or 'formats' argument")

    if dtype is not None:
        descr = sb.dtype(dtype)
    else:
        descr = format_parser(formats, names, titles, aligned, byteorder).dtype

    itemsize = descr.itemsize

    # NumPy 1.19.0, 2020-01-01
    shape = _deprecate_shape_0_as_None(shape)

    if shape in (None, -1):
        shape = (len(datastring) - offset) // itemsize

    _array = recarray(shape, descr, buf=datastring, offset=offset)
    return _array

def get_remaining_size(fd):
    pos = fd.tell()
    try:
        fd.seek(0, 2)
        return fd.tell() - pos
    finally:
        fd.seek(pos, 0)


@set_module("numpy.rec")
def fromfile(fd, dtype=None, shape=None, offset=0, formats=None,
             names=None, titles=None, aligned=False, byteorder=None):
    """Create an array from binary file data

    Parameters
    ----------
    fd : str or file type
        If file is a string or a path-like object then that file is opened,
        else it is assumed to be a file object. The file object must
        support random access (i.e. it must have tell and seek methods).
    dtype : data-type, optional
        valid dtype for all arrays
    shape : int or tuple of ints, optional
        shape of each array.
    offset : int, optional
        Position in the file to start reading from.
    formats, names, titles, aligned, byteorder :
        If `dtype` is ``None``, these arguments are passed to
        `numpy.format_parser` to construct a dtype. See that function for
        detailed documentation

    Returns
    -------
    np.recarray
        record array consisting of data enclosed in file.

    Examples
    --------
    >>> from tempfile import TemporaryFile
    >>> a = np.empty(10,dtype='f8,i4,a5')
    >>> a[5] = (0.5,10,'abcde')
    >>>
    >>> fd=TemporaryFile()
    >>> a = a.view(a.dtype.newbyteorder('<'))
    >>> a.tofile(fd)
    >>>
    >>> _ = fd.seek(0)
    >>> r=np.rec.fromfile(fd, formats='f8,i4,a5', shape=10,
    ... byteorder='<')
    >>> print(r[5])
    (0.5, 10, b'abcde')
    >>> r.shape
    (10,)
    """

    if dtype is None and formats is None:
        raise TypeError("fromfile() needs a 'dtype' or 'formats' argument")

    # NumPy 1.19.0, 2020-01-01
    shape = _deprecate_shape_0_as_None(shape)

    if shape is None:
        shape = (-1,)
    elif isinstance(shape, int):
        shape = (shape,)

    if hasattr(fd, 'readinto'):
        # GH issue 2504. fd supports io.RawIOBase or io.BufferedIOBase
        # interface. Example of fd: gzip, BytesIO, BufferedReader
        # file already opened
        ctx = nullcontext(fd)
    else:
        # open file
        ctx = open(os.fspath(fd), 'rb')

    with ctx as fd:
        if offset > 0:
            fd.seek(offset, 1)
        size = get_remaining_size(fd)

        if dtype is not None:
            descr = sb.dtype(dtype)
        else:
            descr = format_parser(
                formats, names, titles, aligned, byteorder
            ).dtype

        itemsize = descr.itemsize

        shapeprod = sb.array(shape).prod(dtype=nt.intp)
        shapesize = shapeprod * itemsize
        if shapesize < 0:
            shape = list(shape)
            shape[shape.index(-1)] = size // -shapesize
            shape = tuple(shape)
            shapeprod = sb.array(shape).prod(dtype=nt.intp)

        nbytes = shapeprod * itemsize

        if nbytes > size:
            raise ValueError(
                    "Not enough bytes left in file for specified "
                    "shape and type."
                )

        # create the array
        _array = recarray(shape, descr)
        nbytesread = fd.readinto(_array.data)
        if nbytesread != nbytes:
            raise OSError("Didn't read as many bytes as expected")

    return _array


@set_module("numpy.rec")
def array(obj, dtype=None, shape=None, offset=0, strides=None, formats=None,
          names=None, titles=None, aligned=False, byteorder=None, copy=True):
    """
    Construct a record array from a wide-variety of objects.

    A general-purpose record array constructor that dispatches to the
    appropriate `recarray` creation function based on the inputs (see Notes).

    Parameters
    ----------
    obj : any
        Input object. See Notes for details on how various input types are
        treated.
    dtype : data-type, optional
        Valid dtype for array.
    shape : int or tuple of ints, optional
        Shape of each array.
    offset : int, optional
        Position in the file or buffer to start reading from.
    strides : tuple of ints, optional
        Buffer (`buf`) is interpreted according to these strides (strides
        define how many bytes each array element, row, column, etc.
        occupy in memory).
    formats, names, titles, aligned, byteorder :
        If `dtype` is ``None``, these arguments are passed to
        `numpy.format_parser` to construct a dtype. See that function for
        detailed documentation.
    copy : bool, optional
        Whether to copy the input object (True), or to use a reference instead.
        This option only applies when the input is an ndarray or recarray.
        Defaults to True.

    Returns
    -------
    np.recarray
        Record array created from the specified object.

    Notes
    -----
    If `obj` is ``None``, then call the `~numpy.recarray` constructor. If
    `obj` is a string, then call the `fromstring` constructor. If `obj` is a
    list or a tuple, then if the first object is an `~numpy.ndarray`, call
    `fromarrays`, otherwise call `fromrecords`. If `obj` is a
    `~numpy.recarray`, then make a copy of the data in the recarray
    (if ``copy=True``) and use the new formats, names, and titles. If `obj`
    is a file, then call `fromfile`. Finally, if obj is an `ndarray`, then
    return ``obj.view(recarray)``, making a copy of the data if ``copy=True``.

    Examples
    --------
    >>> a = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
    >>> a
    array([[1, 2, 3],
           [4, 5, 6],
           [7, 8, 9]])

    >>> np.rec.array(a)
    rec.array([[1, 2, 3],
               [4, 5, 6],
               [7, 8, 9]],
              dtype=int64)

    >>> b = [(1, 1), (2, 4), (3, 9)]
    >>> c = np.rec.array(b, formats = ['i2', 'f2'], names = ('x', 'y'))
    >>> c
    rec.array([(1, 1.), (2, 4.), (3, 9.)],
              dtype=[('x', '<i2'), ('y', '<f2')])

    >>> c.x
    array([1, 2, 3], dtype=int16)

    >>> c.y
    array([1.,  4.,  9.], dtype=float16)

    >>> r = np.rec.array(['abc','def'], names=['col1','col2'])
    >>> print(r.col1)
    abc

    >>> r.col1
    array('abc', dtype='<U3')

    >>> r.col2
    array('def', dtype='<U3')
    """

    if ((isinstance(obj, (type(None), str)) or hasattr(obj, 'readinto')) and
           formats is None and dtype is None):
        raise ValueError("Must define formats (or dtype) if object is "
                         "None, string, or an open file")

    kwds = {}
    if dtype is not None:
        dtype = sb.dtype(dtype)
    elif formats is not None:
        dtype = format_parser(formats, names, titles,
                              aligned, byteorder).dtype
    else:
        kwds = {'formats': formats,
                'names': names,
                'titles': titles,
                'aligned': aligned,
                'byteorder': byteorder
                }

    if obj is None:
        if shape is None:
            raise ValueError("Must define a shape if obj is None")
        return recarray(shape, dtype, buf=obj, offset=offset, strides=strides)

    elif isinstance(obj, bytes):
        return fromstring(obj, dtype, shape=shape, offset=offset, **kwds)

    elif isinstance(obj, (list, tuple)):
        if isinstance(obj[0], (tuple, list)):
            return fromrecords(obj, dtype=dtype, shape=shape, **kwds)
        else:
            return fromarrays(obj, dtype=dtype, shape=shape, **kwds)

    elif isinstance(obj, recarray):
        if dtype is not None and (obj.dtype != dtype):
            new = obj.view(dtype)
        else:
            new = obj
        if copy:
            new = new.copy()
        return new

    elif hasattr(obj, 'readinto'):
        return fromfile(obj, dtype=dtype, shape=shape, offset=offset)

    elif isinstance(obj, ndarray):
        if dtype is not None and (obj.dtype != dtype):
            new = obj.view(dtype)
        else:
            new = obj
        if copy:
            new = new.copy()
        return new.view(recarray)

    else:
        interface = getattr(obj, "__array_interface__", None)
        if interface is None or not isinstance(interface, dict):
            raise ValueError("Unknown input type")
        obj = sb.array(obj)
        if dtype is not None and (obj.dtype != dtype):
            obj = obj.view(dtype)
        return obj.view(recarray)

# === NexusCore/openenv\Lib\site-packages\requests\utils.py ===
"""
requests.utils
~~~~~~~~~~~~~~

This module provides utility functions that are used within Requests
that are also useful for external consumption.
"""

import codecs
import contextlib
import io
import os
import re
import socket
import struct
import sys
import tempfile
import warnings
import zipfile
from collections import OrderedDict

from urllib3.util import make_headers, parse_url

from . import certs
from .__version__ import __version__

# to_native_string is unused here, but imported here for backwards compatibility
from ._internal_utils import (  # noqa: F401
    _HEADER_VALIDATORS_BYTE,
    _HEADER_VALIDATORS_STR,
    HEADER_VALIDATORS,
    to_native_string,
)
from .compat import (
    Mapping,
    basestring,
    bytes,
    getproxies,
    getproxies_environment,
    integer_types,
    is_urllib3_1,
)
from .compat import parse_http_list as _parse_list_header
from .compat import (
    proxy_bypass,
    proxy_bypass_environment,
    quote,
    str,
    unquote,
    urlparse,
    urlunparse,
)
from .cookies import cookiejar_from_dict
from .exceptions import (
    FileModeWarning,
    InvalidHeader,
    InvalidURL,
    UnrewindableBodyError,
)
from .structures import CaseInsensitiveDict

NETRC_FILES = (".netrc", "_netrc")

DEFAULT_CA_BUNDLE_PATH = certs.where()

DEFAULT_PORTS = {"http": 80, "https": 443}

# Ensure that ', ' is used to preserve previous delimiter behavior.
DEFAULT_ACCEPT_ENCODING = ", ".join(
    re.split(r",\s*", make_headers(accept_encoding=True)["accept-encoding"])
)


if sys.platform == "win32":
    # provide a proxy_bypass version on Windows without DNS lookups

    def proxy_bypass_registry(host):
        try:
            import winreg
        except ImportError:
            return False

        try:
            internetSettings = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
            )
            # ProxyEnable could be REG_SZ or REG_DWORD, normalizing it
            proxyEnable = int(winreg.QueryValueEx(internetSettings, "ProxyEnable")[0])
            # ProxyOverride is almost always a string
            proxyOverride = winreg.QueryValueEx(internetSettings, "ProxyOverride")[0]
        except (OSError, ValueError):
            return False
        if not proxyEnable or not proxyOverride:
            return False

        # make a check value list from the registry entry: replace the
        # '<local>' string by the localhost entry and the corresponding
        # canonical entry.
        proxyOverride = proxyOverride.split(";")
        # filter out empty strings to avoid re.match return true in the following code.
        proxyOverride = filter(None, proxyOverride)
        # now check if we match one of the registry values.
        for test in proxyOverride:
            if test == "<local>":
                if "." not in host:
                    return True
            test = test.replace(".", r"\.")  # mask dots
            test = test.replace("*", r".*")  # change glob sequence
            test = test.replace("?", r".")  # change glob char
            if re.match(test, host, re.I):
                return True
        return False

    def proxy_bypass(host):  # noqa
        """Return True, if the host should be bypassed.

        Checks proxy settings gathered from the environment, if specified,
        or the registry.
        """
        if getproxies_environment():
            return proxy_bypass_environment(host)
        else:
            return proxy_bypass_registry(host)


def dict_to_sequence(d):
    """Returns an internal sequence dictionary update."""

    if hasattr(d, "items"):
        d = d.items()

    return d


def super_len(o):
    total_length = None
    current_position = 0

    if not is_urllib3_1 and isinstance(o, str):
        # urllib3 2.x+ treats all strings as utf-8 instead
        # of latin-1 (iso-8859-1) like http.client.
        o = o.encode("utf-8")

    if hasattr(o, "__len__"):
        total_length = len(o)

    elif hasattr(o, "len"):
        total_length = o.len

    elif hasattr(o, "fileno"):
        try:
            fileno = o.fileno()
        except (io.UnsupportedOperation, AttributeError):
            # AttributeError is a surprising exception, seeing as how we've just checked
            # that `hasattr(o, 'fileno')`.  It happens for objects obtained via
            # `Tarfile.extractfile()`, per issue 5229.
            pass
        else:
            total_length = os.fstat(fileno).st_size

            # Having used fstat to determine the file length, we need to
            # confirm that this file was opened up in binary mode.
            if "b" not in o.mode:
                warnings.warn(
                    (
                        "Requests has determined the content-length for this "
                        "request using the binary size of the file: however, the "
                        "file has been opened in text mode (i.e. without the 'b' "
                        "flag in the mode). This may lead to an incorrect "
                        "content-length. In Requests 3.0, support will be removed "
                        "for files in text mode."
                    ),
                    FileModeWarning,
                )

    if hasattr(o, "tell"):
        try:
            current_position = o.tell()
        except OSError:
            # This can happen in some weird situations, such as when the file
            # is actually a special file descriptor like stdin. In this
            # instance, we don't know what the length is, so set it to zero and
            # let requests chunk it instead.
            if total_length is not None:
                current_position = total_length
        else:
            if hasattr(o, "seek") and total_length is None:
                # StringIO and BytesIO have seek but no usable fileno
                try:
                    # seek to end of file
                    o.seek(0, 2)
                    total_length = o.tell()

                    # seek back to current position to support
                    # partially read file-like objects
                    o.seek(current_position or 0)
                except OSError:
                    total_length = 0

    if total_length is None:
        total_length = 0

    return max(0, total_length - current_position)


def get_netrc_auth(url, raise_errors=False):
    """Returns the Requests tuple auth for a given url from netrc."""

    netrc_file = os.environ.get("NETRC")
    if netrc_file is not None:
        netrc_locations = (netrc_file,)
    else:
        netrc_locations = (f"~/{f}" for f in NETRC_FILES)

    try:
        from netrc import NetrcParseError, netrc

        netrc_path = None

        for f in netrc_locations:
            loc = os.path.expanduser(f)
            if os.path.exists(loc):
                netrc_path = loc
                break

        # Abort early if there isn't one.
        if netrc_path is None:
            return

        ri = urlparse(url)
        host = ri.hostname

        try:
            _netrc = netrc(netrc_path).authenticators(host)
            if _netrc:
                # Return with login / password
                login_i = 0 if _netrc[0] else 1
                return (_netrc[login_i], _netrc[2])
        except (NetrcParseError, OSError):
            # If there was a parsing error or a permissions issue reading the file,
            # we'll just skip netrc auth unless explicitly asked to raise errors.
            if raise_errors:
                raise

    # App Engine hackiness.
    except (ImportError, AttributeError):
        pass


def guess_filename(obj):
    """Tries to guess the filename of the given object."""
    name = getattr(obj, "name", None)
    if name and isinstance(name, basestring) and name[0] != "<" and name[-1] != ">":
        return os.path.basename(name)


def extract_zipped_paths(path):
    """Replace nonexistent paths that look like they refer to a member of a zip
    archive with the location of an extracted copy of the target, or else
    just return the provided path unchanged.
    """
    if os.path.exists(path):
        # this is already a valid path, no need to do anything further
        return path

    # find the first valid part of the provided path and treat that as a zip archive
    # assume the rest of the path is the name of a member in the archive
    archive, member = os.path.split(path)
    while archive and not os.path.exists(archive):
        archive, prefix = os.path.split(archive)
        if not prefix:
            # If we don't check for an empty prefix after the split (in other words, archive remains unchanged after the split),
            # we _can_ end up in an infinite loop on a rare corner case affecting a small number of users
            break
        member = "/".join([prefix, member])

    if not zipfile.is_zipfile(archive):
        return path

    zip_file = zipfile.ZipFile(archive)
    if member not in zip_file.namelist():
        return path

    # we have a valid zip archive and a valid member of that archive
    tmp = tempfile.gettempdir()
    extracted_path = os.path.join(tmp, member.split("/")[-1])
    if not os.path.exists(extracted_path):
        # use read + write to avoid the creating nested folders, we only want the file, avoids mkdir racing condition
        with atomic_open(extracted_path) as file_handler:
            file_handler.write(zip_file.read(member))
    return extracted_path


@contextlib.contextmanager
def atomic_open(filename):
    """Write a file to the disk in an atomic fashion"""
    tmp_descriptor, tmp_name = tempfile.mkstemp(dir=os.path.dirname(filename))
    try:
        with os.fdopen(tmp_descriptor, "wb") as tmp_handler:
            yield tmp_handler
        os.replace(tmp_name, filename)
    except BaseException:
        os.remove(tmp_name)
        raise


def from_key_val_list(value):
    """Take an object and test to see if it can be represented as a
    dictionary. Unless it can not be represented as such, return an
    OrderedDict, e.g.,

    ::

        >>> from_key_val_list([('key', 'val')])
        OrderedDict([('key', 'val')])
        >>> from_key_val_list('string')
        Traceback (most recent call last):
        ...
        ValueError: cannot encode objects that are not 2-tuples
        >>> from_key_val_list({'key': 'val'})
        OrderedDict([('key', 'val')])

    :rtype: OrderedDict
    """
    if value is None:
        return None

    if isinstance(value, (str, bytes, bool, int)):
        raise ValueError("cannot encode objects that are not 2-tuples")

    return OrderedDict(value)


def to_key_val_list(value):
    """Take an object and test to see if it can be represented as a
    dictionary. If it can be, return a list of tuples, e.g.,

    ::

        >>> to_key_val_list([('key', 'val')])
        [('key', 'val')]
        >>> to_key_val_list({'key': 'val'})
        [('key', 'val')]
        >>> to_key_val_list('string')
        Traceback (most recent call last):
        ...
        ValueError: cannot encode objects that are not 2-tuples

    :rtype: list
    """
    if value is None:
        return None

    if isinstance(value, (str, bytes, bool, int)):
        raise ValueError("cannot encode objects that are not 2-tuples")

    if isinstance(value, Mapping):
        value = value.items()

    return list(value)


# From mitsuhiko/werkzeug (used with permission).
def parse_list_header(value):
    """Parse lists as described by RFC 2068 Section 2.

    In particular, parse comma-separated lists where the elements of
    the list may include quoted-strings.  A quoted-string could
    contain a comma.  A non-quoted string could have quotes in the
    middle.  Quotes are removed automatically after parsing.

    It basically works like :func:`parse_set_header` just that items
    may appear multiple times and case sensitivity is preserved.

    The return value is a standard :class:`list`:

    >>> parse_list_header('token, "quoted value"')
    ['token', 'quoted value']

    To create a header from the :class:`list` again, use the
    :func:`dump_header` function.

    :param value: a string with a list header.
    :return: :class:`list`
    :rtype: list
    """
    result = []
    for item in _parse_list_header(value):
        if item[:1] == item[-1:] == '"':
            item = unquote_header_value(item[1:-1])
        result.append(item)
    return result


# From mitsuhiko/werkzeug (used with permission).
def parse_dict_header(value):
    """Parse lists of key, value pairs as described by RFC 2068 Section 2 and
    convert them into a python dict:

    >>> d = parse_dict_header('foo="is a fish", bar="as well"')
    >>> type(d) is dict
    True
    >>> sorted(d.items())
    [('bar', 'as well'), ('foo', 'is a fish')]

    If there is no value for a key it will be `None`:

    >>> parse_dict_header('key_without_value')
    {'key_without_value': None}

    To create a header from the :class:`dict` again, use the
    :func:`dump_header` function.

    :param value: a string with a dict header.
    :return: :class:`dict`
    :rtype: dict
    """
    result = {}
    for item in _parse_list_header(value):
        if "=" not in item:
            result[item] = None
            continue
        name, value = item.split("=", 1)
        if value[:1] == value[-1:] == '"':
            value = unquote_header_value(value[1:-1])
        result[name] = value
    return result


# From mitsuhiko/werkzeug (used with permission).
def unquote_header_value(value, is_filename=False):
    r"""Unquotes a header value.  (Reversal of :func:`quote_header_value`).
    This does not use the real unquoting but what browsers are actually
    using for quoting.

    :param value: the header value to unquote.
    :rtype: str
    """
    if value and value[0] == value[-1] == '"':
        # this is not the real unquoting, but fixing this so that the
        # RFC is met will result in bugs with internet explorer and
        # probably some other browsers as well.  IE for example is
        # uploading files with "C:\foo\bar.txt" as filename
        value = value[1:-1]

        # if this is a filename and the starting characters look like
        # a UNC path, then just return the value without quotes.  Using the
        # replace sequence below on a UNC path has the effect of turning
        # the leading double slash into a single slash and then
        # _fix_ie_filename() doesn't work correctly.  See #458.
        if not is_filename or value[:2] != "\\\\":
            return value.replace("\\\\", "\\").replace('\\"', '"')
    return value


def dict_from_cookiejar(cj):
    """Returns a key/value dictionary from a CookieJar.

    :param cj: CookieJar object to extract cookies from.
    :rtype: dict
    """

    cookie_dict = {cookie.name: cookie.value for cookie in cj}
    return cookie_dict


def add_dict_to_cookiejar(cj, cookie_dict):
    """Returns a CookieJar from a key/value dictionary.

    :param cj: CookieJar to insert cookies into.
    :param cookie_dict: Dict of key/values to insert into CookieJar.
    :rtype: CookieJar
    """

    return cookiejar_from_dict(cookie_dict, cj)


def get_encodings_from_content(content):
    """Returns encodings from given content string.

    :param content: bytestring to extract encodings from.
    """
    warnings.warn(
        (
            "In requests 3.0, get_encodings_from_content will be removed. For "
            "more information, please see the discussion on issue #2266. (This"
            " warning should only appear once.)"
        ),
        DeprecationWarning,
    )

    charset_re = re.compile(r'<meta.*?charset=["\']*(.+?)["\'>]', flags=re.I)
    pragma_re = re.compile(r'<meta.*?content=["\']*;?charset=(.+?)["\'>]', flags=re.I)
    xml_re = re.compile(r'^<\?xml.*?encoding=["\']*(.+?)["\'>]')

    return (
        charset_re.findall(content)
        + pragma_re.findall(content)
        + xml_re.findall(content)
    )


def _parse_content_type_header(header):
    """Returns content type and parameters from given header

    :param header: string
    :return: tuple containing content type and dictionary of
         parameters
    """

    tokens = header.split(";")
    content_type, params = tokens[0].strip(), tokens[1:]
    params_dict = {}
    items_to_strip = "\"' "

    for param in params:
        param = param.strip()
        if param:
            key, value = param, True
            index_of_equals = param.find("=")
            if index_of_equals != -1:
                key = param[:index_of_equals].strip(items_to_strip)
                value = param[index_of_equals + 1 :].strip(items_to_strip)
            params_dict[key.lower()] = value
    return content_type, params_dict


def get_encoding_from_headers(headers):
    """Returns encodings from given HTTP Header Dict.

    :param headers: dictionary to extract encoding from.
    :rtype: str
    """

    content_type = headers.get("content-type")

    if not content_type:
        return None

    content_type, params = _parse_content_type_header(content_type)

    if "charset" in params:
        return params["charset"].strip("'\"")

    if "text" in content_type:
        return "ISO-8859-1"

    if "application/json" in content_type:
        # Assume UTF-8 based on RFC 4627: https://www.ietf.org/rfc/rfc4627.txt since the charset was unset
        return "utf-8"


def stream_decode_response_unicode(iterator, r):
    """Stream decodes an iterator."""

    if r.encoding is None:
        yield from iterator
        return

    decoder = codecs.getincrementaldecoder(r.encoding)(errors="replace")
    for chunk in iterator:
        rv = decoder.decode(chunk)
        if rv:
            yield rv
    rv = decoder.decode(b"", final=True)
    if rv:
        yield rv


def iter_slices(string, slice_length):
    """Iterate over slices of a string."""
    pos = 0
    if slice_length is None or slice_length <= 0:
        slice_length = len(string)
    while pos < len(string):
        yield string[pos : pos + slice_length]
        pos += slice_length


def get_unicode_from_response(r):
    """Returns the requested content back in unicode.

    :param r: Response object to get unicode content from.

    Tried:

    1. charset from content-type
    2. fall back and replace all unicode characters

    :rtype: str
    """
    warnings.warn(
        (
            "In requests 3.0, get_unicode_from_response will be removed. For "
            "more information, please see the discussion on issue #2266. (This"
            " warning should only appear once.)"
        ),
        DeprecationWarning,
    )

    tried_encodings = []

    # Try charset from content-type
    encoding = get_encoding_from_headers(r.headers)

    if encoding:
        try:
            return str(r.content, encoding)
        except UnicodeError:
            tried_encodings.append(encoding)

    # Fall back:
    try:
        return str(r.content, encoding, errors="replace")
    except TypeError:
        return r.content


# The unreserved URI characters (RFC 3986)
UNRESERVED_SET = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz" + "0123456789-._~"
)


def unquote_unreserved(uri):
    """Un-escape any percent-escape sequences in a URI that are unreserved
    characters. This leaves all reserved, illegal and non-ASCII bytes encoded.

    :rtype: str
    """
    parts = uri.split("%")
    for i in range(1, len(parts)):
        h = parts[i][0:2]
        if len(h) == 2 and h.isalnum():
            try:
                c = chr(int(h, 16))
            except ValueError:
                raise InvalidURL(f"Invalid percent-escape sequence: '{h}'")

            if c in UNRESERVED_SET:
                parts[i] = c + parts[i][2:]
            else:
                parts[i] = f"%{parts[i]}"
        else:
            parts[i] = f"%{parts[i]}"
    return "".join(parts)


def requote_uri(uri):
    """Re-quote the given URI.

    This function passes the given URI through an unquote/quote cycle to
    ensure that it is fully and consistently quoted.

    :rtype: str
    """
    safe_with_percent = "!#$%&'()*+,/:;=?@[]~"
    safe_without_percent = "!#$&'()*+,/:;=?@[]~"
    try:
        # Unquote only the unreserved characters
        # Then quote only illegal characters (do not quote reserved,
        # unreserved, or '%')
        return quote(unquote_unreserved(uri), safe=safe_with_percent)
    except InvalidURL:
        # We couldn't unquote the given URI, so let's try quoting it, but
        # there may be unquoted '%'s in the URI. We need to make sure they're
        # properly quoted so they do not cause issues elsewhere.
        return quote(uri, safe=safe_without_percent)


def address_in_network(ip, net):
    """This function allows you to check if an IP belongs to a network subnet

    Example: returns True if ip = 192.168.1.1 and net = 192.168.1.0/24
             returns False if ip = 192.168.1.1 and net = 192.168.100.0/24

    :rtype: bool
    """
    ipaddr = struct.unpack("=L", socket.inet_aton(ip))[0]
    netaddr, bits = net.split("/")
    netmask = struct.unpack("=L", socket.inet_aton(dotted_netmask(int(bits))))[0]
    network = struct.unpack("=L", socket.inet_aton(netaddr))[0] & netmask
    return (ipaddr & netmask) == (network & netmask)


def dotted_netmask(mask):
    """Converts mask from /xx format to xxx.xxx.xxx.xxx

    Example: if mask is 24 function returns 255.255.255.0

    :rtype: str
    """
    bits = 0xFFFFFFFF ^ (1 << 32 - mask) - 1
    return socket.inet_ntoa(struct.pack(">I", bits))


def is_ipv4_address(string_ip):
    """
    :rtype: bool
    """
    try:
        socket.inet_aton(string_ip)
    except OSError:
        return False
    return True


def is_valid_cidr(string_network):
    """
    Very simple check of the cidr format in no_proxy variable.

    :rtype: bool
    """
    if string_network.count("/") == 1:
        try:
            mask = int(string_network.split("/")[1])
        except ValueError:
            return False

        if mask < 1 or mask > 32:
            return False

        try:
            socket.inet_aton(string_network.split("/")[0])
        except OSError:
            return False
    else:
        return False
    return True


@contextlib.contextmanager
def set_environ(env_name, value):
    """Set the environment variable 'env_name' to 'value'

    Save previous value, yield, and then restore the previous value stored in
    the environment variable 'env_name'.

    If 'value' is None, do nothing"""
    value_changed = value is not None
    if value_changed:
        old_value = os.environ.get(env_name)
        os.environ[env_name] = value
    try:
        yield
    finally:
        if value_changed:
            if old_value is None:
                del os.environ[env_name]
            else:
                os.environ[env_name] = old_value


def should_bypass_proxies(url, no_proxy):
    """
    Returns whether we should bypass proxies or not.

    :rtype: bool
    """

    # Prioritize lowercase environment variables over uppercase
    # to keep a consistent behaviour with other http projects (curl, wget).
    def get_proxy(key):
        return os.environ.get(key) or os.environ.get(key.upper())

    # First check whether no_proxy is defined. If it is, check that the URL
    # we're getting isn't in the no_proxy list.
    no_proxy_arg = no_proxy
    if no_proxy is None:
        no_proxy = get_proxy("no_proxy")
    parsed = urlparse(url)

    if parsed.hostname is None:
        # URLs don't always have hostnames, e.g. file:/// urls.
        return True

    if no_proxy:
        # We need to check whether we match here. We need to see if we match
        # the end of the hostname, both with and without the port.
        no_proxy = (host for host in no_proxy.replace(" ", "").split(",") if host)

        if is_ipv4_address(parsed.hostname):
            for proxy_ip in no_proxy:
                if is_valid_cidr(proxy_ip):
                    if address_in_network(parsed.hostname, proxy_ip):
                        return True
                elif parsed.hostname == proxy_ip:
                    # If no_proxy ip was defined in plain IP notation instead of cidr notation &
                    # matches the IP of the index
                    return True
        else:
            host_with_port = parsed.hostname
            if parsed.port:
                host_with_port += f":{parsed.port}"

            for host in no_proxy:
                if parsed.hostname.endswith(host) or host_with_port.endswith(host):
                    # The URL does match something in no_proxy, so we don't want
                    # to apply the proxies on this URL.
                    return True

    with set_environ("no_proxy", no_proxy_arg):
        # parsed.hostname can be `None` in cases such as a file URI.
        try:
            bypass = proxy_bypass(parsed.hostname)
        except (TypeError, socket.gaierror):
            bypass = False

    if bypass:
        return True

    return False


def get_environ_proxies(url, no_proxy=None):
    """
    Return a dict of environment proxies.

    :rtype: dict
    """
    if should_bypass_proxies(url, no_proxy=no_proxy):
        return {}
    else:
        return getproxies()


def select_proxy(url, proxies):
    """Select a proxy for the url, if applicable.

    :param url: The url being for the request
    :param proxies: A dictionary of schemes or schemes and hosts to proxy URLs
    """
    proxies = proxies or {}
    urlparts = urlparse(url)
    if urlparts.hostname is None:
        return proxies.get(urlparts.scheme, proxies.get("all"))

    proxy_keys = [
        urlparts.scheme + "://" + urlparts.hostname,
        urlparts.scheme,
        "all://" + urlparts.hostname,
        "all",
    ]
    proxy = None
    for proxy_key in proxy_keys:
        if proxy_key in proxies:
            proxy = proxies[proxy_key]
            break

    return proxy


def resolve_proxies(request, proxies, trust_env=True):
    """This method takes proxy information from a request and configuration
    input to resolve a mapping of target proxies. This will consider settings
    such as NO_PROXY to strip proxy configurations.

    :param request: Request or PreparedRequest
    :param proxies: A dictionary of schemes or schemes and hosts to proxy URLs
    :param trust_env: Boolean declaring whether to trust environment configs

    :rtype: dict
    """
    proxies = proxies if proxies is not None else {}
    url = request.url
    scheme = urlparse(url).scheme
    no_proxy = proxies.get("no_proxy")
    new_proxies = proxies.copy()

    if trust_env and not should_bypass_proxies(url, no_proxy=no_proxy):
        environ_proxies = get_environ_proxies(url, no_proxy=no_proxy)

        proxy = environ_proxies.get(scheme, environ_proxies.get("all"))

        if proxy:
            new_proxies.setdefault(scheme, proxy)
    return new_proxies


def default_user_agent(name="python-requests"):
    """
    Return a string representing the default user agent.

    :rtype: str
    """
    return f"{name}/{__version__}"


def default_headers():
    """
    :rtype: requests.structures.CaseInsensitiveDict
    """
    return CaseInsensitiveDict(
        {
            "User-Agent": default_user_agent(),
            "Accept-Encoding": DEFAULT_ACCEPT_ENCODING,
            "Accept": "*/*",
            "Connection": "keep-alive",
        }
    )


def parse_header_links(value):
    """Return a list of parsed link headers proxies.

    i.e. Link: <http:/.../front.jpeg>; rel=front; type="image/jpeg",<http://.../back.jpeg>; rel=back;type="image/jpeg"

    :rtype: list
    """

    links = []

    replace_chars = " '\""

    value = value.strip(replace_chars)
    if not value:
        return links

    for val in re.split(", *<", value):
        try:
            url, params = val.split(";", 1)
        except ValueError:
            url, params = val, ""

        link = {"url": url.strip("<> '\"")}

        for param in params.split(";"):
            try:
                key, value = param.split("=")
            except ValueError:
                break

            link[key.strip(replace_chars)] = value.strip(replace_chars)

        links.append(link)

    return links


# Null bytes; no need to recreate these on each call to guess_json_utf
_null = "\x00".encode("ascii")  # encoding to ASCII for Python 3
_null2 = _null * 2
_null3 = _null * 3


def guess_json_utf(data):
    """
    :rtype: str
    """
    # JSON always starts with two ASCII characters, so detection is as
    # easy as counting the nulls and from their location and count
    # determine the encoding. Also detect a BOM, if present.
    sample = data[:4]
    if sample in (codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE):
        return "utf-32"  # BOM included
    if sample[:3] == codecs.BOM_UTF8:
        return "utf-8-sig"  # BOM included, MS style (discouraged)
    if sample[:2] in (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE):
        return "utf-16"  # BOM included
    nullcount = sample.count(_null)
    if nullcount == 0:
        return "utf-8"
    if nullcount == 2:
        if sample[::2] == _null2:  # 1st and 3rd are null
            return "utf-16-be"
        if sample[1::2] == _null2:  # 2nd and 4th are null
            return "utf-16-le"
        # Did not detect 2 valid UTF-16 ascii-range characters
    if nullcount == 3:
        if sample[:3] == _null3:
            return "utf-32-be"
        if sample[1:] == _null3:
            return "utf-32-le"
        # Did not detect a valid UTF-32 ascii-range character
    return None


def prepend_scheme_if_needed(url, new_scheme):
    """Given a URL that may or may not have a scheme, prepend the given scheme.
    Does not replace a present scheme with the one provided as an argument.

    :rtype: str
    """
    parsed = parse_url(url)
    scheme, auth, host, port, path, query, fragment = parsed

    # A defect in urlparse determines that there isn't a netloc present in some
    # urls. We previously assumed parsing was overly cautious, and swapped the
    # netloc and path. Due to a lack of tests on the original defect, this is
    # maintained with parse_url for backwards compatibility.
    netloc = parsed.netloc
    if not netloc:
        netloc, path = path, netloc

    if auth:
        # parse_url doesn't provide the netloc with auth
        # so we'll add it ourselves.
        netloc = "@".join([auth, netloc])
    if scheme is None:
        scheme = new_scheme
    if path is None:
        path = ""

    return urlunparse((scheme, netloc, path, "", query, fragment))


def get_auth_from_url(url):
    """Given a url with authentication components, extract them into a tuple of
    username,password.

    :rtype: (str,str)
    """
    parsed = urlparse(url)

    try:
        auth = (unquote(parsed.username), unquote(parsed.password))
    except (AttributeError, TypeError):
        auth = ("", "")

    return auth


def check_header_validity(header):
    """Verifies that header parts don't contain leading whitespace
    reserved characters, or return characters.

    :param header: tuple, in the format (name, value).
    """
    name, value = header
    _validate_header_part(header, name, 0)
    _validate_header_part(header, value, 1)


def _validate_header_part(header, header_part, header_validator_index):
    if isinstance(header_part, str):
        validator = _HEADER_VALIDATORS_STR[header_validator_index]
    elif isinstance(header_part, bytes):
        validator = _HEADER_VALIDATORS_BYTE[header_validator_index]
    else:
        raise InvalidHeader(
            f"Header part ({header_part!r}) from {header} "
            f"must be of type str or bytes, not {type(header_part)}"
        )

    if not validator.match(header_part):
        header_kind = "name" if header_validator_index == 0 else "value"
        raise InvalidHeader(
            f"Invalid leading whitespace, reserved character(s), or return "
            f"character(s) in header {header_kind}: {header_part!r}"
        )


def urldefragauth(url):
    """
    Given a url remove the fragment and the authentication part.

    :rtype: str
    """
    scheme, netloc, path, params, query, fragment = urlparse(url)

    # see func:`prepend_scheme_if_needed`
    if not netloc:
        netloc, path = path, netloc

    netloc = netloc.rsplit("@", 1)[-1]

    return urlunparse((scheme, netloc, path, params, query, ""))


def rewind_body(prepared_request):
    """Move file pointer back to its recorded starting position
    so it can be read again on redirect.
    """
    body_seek = getattr(prepared_request.body, "seek", None)
    if body_seek is not None and isinstance(
        prepared_request._body_position, integer_types
    ):
        try:
            body_seek(prepared_request._body_position)
        except OSError:
            raise UnrewindableBodyError(
                "An error occurred when rewinding request body for redirect."
            )
    else:
        raise UnrewindableBodyError("Unable to rewind request body for redirect.")

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_attach_to_process\winappdbg\win32\version.py ===
#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
Detect the current architecture and operating system.

Some functions here are really from kernel32.dll, others from version.dll.
"""

__revision__ = "$Id$"

from winappdbg.win32.defines import *

# ==============================================================================
# This is used later on to calculate the list of exported symbols.
_all = None
_all = set(vars().keys())
# ==============================================================================

# --- NTDDI version ------------------------------------------------------------

NTDDI_WIN8 = 0x06020000
NTDDI_WIN7SP1 = 0x06010100
NTDDI_WIN7 = 0x06010000
NTDDI_WS08 = 0x06000100
NTDDI_VISTASP1 = 0x06000100
NTDDI_VISTA = 0x06000000
NTDDI_LONGHORN = NTDDI_VISTA
NTDDI_WS03SP2 = 0x05020200
NTDDI_WS03SP1 = 0x05020100
NTDDI_WS03 = 0x05020000
NTDDI_WINXPSP3 = 0x05010300
NTDDI_WINXPSP2 = 0x05010200
NTDDI_WINXPSP1 = 0x05010100
NTDDI_WINXP = 0x05010000
NTDDI_WIN2KSP4 = 0x05000400
NTDDI_WIN2KSP3 = 0x05000300
NTDDI_WIN2KSP2 = 0x05000200
NTDDI_WIN2KSP1 = 0x05000100
NTDDI_WIN2K = 0x05000000
NTDDI_WINNT4 = 0x04000000

OSVERSION_MASK = 0xFFFF0000
SPVERSION_MASK = 0x0000FF00
SUBVERSION_MASK = 0x000000FF

# --- OSVERSIONINFO and OSVERSIONINFOEX structures and constants ---------------

VER_PLATFORM_WIN32s = 0
VER_PLATFORM_WIN32_WINDOWS = 1
VER_PLATFORM_WIN32_NT = 2

VER_SUITE_BACKOFFICE = 0x00000004
VER_SUITE_BLADE = 0x00000400
VER_SUITE_COMPUTE_SERVER = 0x00004000
VER_SUITE_DATACENTER = 0x00000080
VER_SUITE_ENTERPRISE = 0x00000002
VER_SUITE_EMBEDDEDNT = 0x00000040
VER_SUITE_PERSONAL = 0x00000200
VER_SUITE_SINGLEUSERTS = 0x00000100
VER_SUITE_SMALLBUSINESS = 0x00000001
VER_SUITE_SMALLBUSINESS_RESTRICTED = 0x00000020
VER_SUITE_STORAGE_SERVER = 0x00002000
VER_SUITE_TERMINAL = 0x00000010
VER_SUITE_WH_SERVER = 0x00008000

VER_NT_DOMAIN_CONTROLLER = 0x0000002
VER_NT_SERVER = 0x0000003
VER_NT_WORKSTATION = 0x0000001

VER_BUILDNUMBER = 0x0000004
VER_MAJORVERSION = 0x0000002
VER_MINORVERSION = 0x0000001
VER_PLATFORMID = 0x0000008
VER_PRODUCT_TYPE = 0x0000080
VER_SERVICEPACKMAJOR = 0x0000020
VER_SERVICEPACKMINOR = 0x0000010
VER_SUITENAME = 0x0000040

VER_EQUAL = 1
VER_GREATER = 2
VER_GREATER_EQUAL = 3
VER_LESS = 4
VER_LESS_EQUAL = 5
VER_AND = 6
VER_OR = 7


# typedef struct _OSVERSIONINFO {
#   DWORD dwOSVersionInfoSize;
#   DWORD dwMajorVersion;
#   DWORD dwMinorVersion;
#   DWORD dwBuildNumber;
#   DWORD dwPlatformId;
#   TCHAR szCSDVersion[128];
# }OSVERSIONINFO;
class OSVERSIONINFOA(Structure):
    _fields_ = [
        ("dwOSVersionInfoSize", DWORD),
        ("dwMajorVersion", DWORD),
        ("dwMinorVersion", DWORD),
        ("dwBuildNumber", DWORD),
        ("dwPlatformId", DWORD),
        ("szCSDVersion", CHAR * 128),
    ]


class OSVERSIONINFOW(Structure):
    _fields_ = [
        ("dwOSVersionInfoSize", DWORD),
        ("dwMajorVersion", DWORD),
        ("dwMinorVersion", DWORD),
        ("dwBuildNumber", DWORD),
        ("dwPlatformId", DWORD),
        ("szCSDVersion", WCHAR * 128),
    ]


# typedef struct _OSVERSIONINFOEX {
#   DWORD dwOSVersionInfoSize;
#   DWORD dwMajorVersion;
#   DWORD dwMinorVersion;
#   DWORD dwBuildNumber;
#   DWORD dwPlatformId;
#   TCHAR szCSDVersion[128];
#   WORD  wServicePackMajor;
#   WORD  wServicePackMinor;
#   WORD  wSuiteMask;
#   BYTE  wProductType;
#   BYTE  wReserved;
# }OSVERSIONINFOEX, *POSVERSIONINFOEX, *LPOSVERSIONINFOEX;
class OSVERSIONINFOEXA(Structure):
    _fields_ = [
        ("dwOSVersionInfoSize", DWORD),
        ("dwMajorVersion", DWORD),
        ("dwMinorVersion", DWORD),
        ("dwBuildNumber", DWORD),
        ("dwPlatformId", DWORD),
        ("szCSDVersion", CHAR * 128),
        ("wServicePackMajor", WORD),
        ("wServicePackMinor", WORD),
        ("wSuiteMask", WORD),
        ("wProductType", BYTE),
        ("wReserved", BYTE),
    ]


class OSVERSIONINFOEXW(Structure):
    _fields_ = [
        ("dwOSVersionInfoSize", DWORD),
        ("dwMajorVersion", DWORD),
        ("dwMinorVersion", DWORD),
        ("dwBuildNumber", DWORD),
        ("dwPlatformId", DWORD),
        ("szCSDVersion", WCHAR * 128),
        ("wServicePackMajor", WORD),
        ("wServicePackMinor", WORD),
        ("wSuiteMask", WORD),
        ("wProductType", BYTE),
        ("wReserved", BYTE),
    ]


LPOSVERSIONINFOA = POINTER(OSVERSIONINFOA)
LPOSVERSIONINFOW = POINTER(OSVERSIONINFOW)
LPOSVERSIONINFOEXA = POINTER(OSVERSIONINFOEXA)
LPOSVERSIONINFOEXW = POINTER(OSVERSIONINFOEXW)
POSVERSIONINFOA = LPOSVERSIONINFOA
POSVERSIONINFOW = LPOSVERSIONINFOW
POSVERSIONINFOEXA = LPOSVERSIONINFOEXA
POSVERSIONINFOEXW = LPOSVERSIONINFOA

# --- GetSystemMetrics constants -----------------------------------------------

SM_CXSCREEN = 0
SM_CYSCREEN = 1
SM_CXVSCROLL = 2
SM_CYHSCROLL = 3
SM_CYCAPTION = 4
SM_CXBORDER = 5
SM_CYBORDER = 6
SM_CXDLGFRAME = 7
SM_CYDLGFRAME = 8
SM_CYVTHUMB = 9
SM_CXHTHUMB = 10
SM_CXICON = 11
SM_CYICON = 12
SM_CXCURSOR = 13
SM_CYCURSOR = 14
SM_CYMENU = 15
SM_CXFULLSCREEN = 16
SM_CYFULLSCREEN = 17
SM_CYKANJIWINDOW = 18
SM_MOUSEPRESENT = 19
SM_CYVSCROLL = 20
SM_CXHSCROLL = 21
SM_DEBUG = 22
SM_SWAPBUTTON = 23
SM_RESERVED1 = 24
SM_RESERVED2 = 25
SM_RESERVED3 = 26
SM_RESERVED4 = 27
SM_CXMIN = 28
SM_CYMIN = 29
SM_CXSIZE = 30
SM_CYSIZE = 31
SM_CXFRAME = 32
SM_CYFRAME = 33
SM_CXMINTRACK = 34
SM_CYMINTRACK = 35
SM_CXDOUBLECLK = 36
SM_CYDOUBLECLK = 37
SM_CXICONSPACING = 38
SM_CYICONSPACING = 39
SM_MENUDROPALIGNMENT = 40
SM_PENWINDOWS = 41
SM_DBCSENABLED = 42
SM_CMOUSEBUTTONS = 43

SM_CXFIXEDFRAME = SM_CXDLGFRAME  # ;win40 name change
SM_CYFIXEDFRAME = SM_CYDLGFRAME  # ;win40 name change
SM_CXSIZEFRAME = SM_CXFRAME  # ;win40 name change
SM_CYSIZEFRAME = SM_CYFRAME  # ;win40 name change

SM_SECURE = 44
SM_CXEDGE = 45
SM_CYEDGE = 46
SM_CXMINSPACING = 47
SM_CYMINSPACING = 48
SM_CXSMICON = 49
SM_CYSMICON = 50
SM_CYSMCAPTION = 51
SM_CXSMSIZE = 52
SM_CYSMSIZE = 53
SM_CXMENUSIZE = 54
SM_CYMENUSIZE = 55
SM_ARRANGE = 56
SM_CXMINIMIZED = 57
SM_CYMINIMIZED = 58
SM_CXMAXTRACK = 59
SM_CYMAXTRACK = 60
SM_CXMAXIMIZED = 61
SM_CYMAXIMIZED = 62
SM_NETWORK = 63
SM_CLEANBOOT = 67
SM_CXDRAG = 68
SM_CYDRAG = 69
SM_SHOWSOUNDS = 70
SM_CXMENUCHECK = 71  # Use instead of GetMenuCheckMarkDimensions()!
SM_CYMENUCHECK = 72
SM_SLOWMACHINE = 73
SM_MIDEASTENABLED = 74
SM_MOUSEWHEELPRESENT = 75
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79
SM_CMONITORS = 80
SM_SAMEDISPLAYFORMAT = 81
SM_IMMENABLED = 82
SM_CXFOCUSBORDER = 83
SM_CYFOCUSBORDER = 84
SM_TABLETPC = 86
SM_MEDIACENTER = 87
SM_STARTER = 88
SM_SERVERR2 = 89
SM_MOUSEHORIZONTALWHEELPRESENT = 91
SM_CXPADDEDBORDER = 92

SM_CMETRICS = 93

SM_REMOTESESSION = 0x1000
SM_SHUTTINGDOWN = 0x2000
SM_REMOTECONTROL = 0x2001
SM_CARETBLINKINGENABLED = 0x2002

# --- SYSTEM_INFO structure, GetSystemInfo() and GetNativeSystemInfo() ---------

# Values used by Wine
# Documented values at MSDN are marked with an asterisk
PROCESSOR_ARCHITECTURE_UNKNOWN = 0xFFFF  # Unknown architecture.
PROCESSOR_ARCHITECTURE_INTEL = 0  # x86 (AMD or Intel) *
PROCESSOR_ARCHITECTURE_MIPS = 1  # MIPS
PROCESSOR_ARCHITECTURE_ALPHA = 2  # Alpha
PROCESSOR_ARCHITECTURE_PPC = 3  # Power PC
PROCESSOR_ARCHITECTURE_SHX = 4  # SHX
PROCESSOR_ARCHITECTURE_ARM = 5  # ARM
PROCESSOR_ARCHITECTURE_IA64 = 6  # Intel Itanium *
PROCESSOR_ARCHITECTURE_ALPHA64 = 7  # Alpha64
PROCESSOR_ARCHITECTURE_MSIL = 8  # MSIL
PROCESSOR_ARCHITECTURE_AMD64 = 9  # x64 (AMD or Intel) *
PROCESSOR_ARCHITECTURE_IA32_ON_WIN64 = 10  # IA32 on Win64
PROCESSOR_ARCHITECTURE_SPARC = 20  # Sparc (Wine)

# Values used by Wine
# PROCESSOR_OPTIL value found at http://code.google.com/p/ddab-lib/
# Documented values at MSDN are marked with an asterisk
PROCESSOR_INTEL_386 = 386  # Intel i386 *
PROCESSOR_INTEL_486 = 486  # Intel i486 *
PROCESSOR_INTEL_PENTIUM = 586  # Intel Pentium *
PROCESSOR_INTEL_IA64 = 2200  # Intel IA64 (Itanium) *
PROCESSOR_AMD_X8664 = 8664  # AMD X86 64 *
PROCESSOR_MIPS_R4000 = 4000  # MIPS R4000, R4101, R3910
PROCESSOR_ALPHA_21064 = 21064  # Alpha 210 64
PROCESSOR_PPC_601 = 601  # PPC 601
PROCESSOR_PPC_603 = 603  # PPC 603
PROCESSOR_PPC_604 = 604  # PPC 604
PROCESSOR_PPC_620 = 620  # PPC 620
PROCESSOR_HITACHI_SH3 = 10003  # Hitachi SH3 (Windows CE)
PROCESSOR_HITACHI_SH3E = 10004  # Hitachi SH3E (Windows CE)
PROCESSOR_HITACHI_SH4 = 10005  # Hitachi SH4 (Windows CE)
PROCESSOR_MOTOROLA_821 = 821  # Motorola 821 (Windows CE)
PROCESSOR_SHx_SH3 = 103  # SHx SH3 (Windows CE)
PROCESSOR_SHx_SH4 = 104  # SHx SH4 (Windows CE)
PROCESSOR_STRONGARM = 2577  # StrongARM (Windows CE)
PROCESSOR_ARM720 = 1824  # ARM 720 (Windows CE)
PROCESSOR_ARM820 = 2080  # ARM 820 (Windows CE)
PROCESSOR_ARM920 = 2336  # ARM 920 (Windows CE)
PROCESSOR_ARM_7TDMI = 70001  # ARM 7TDMI (Windows CE)
PROCESSOR_OPTIL = 0x494F  # MSIL

# typedef struct _SYSTEM_INFO {
#   union {
#     DWORD dwOemId;
#     struct {
#       WORD wProcessorArchitecture;
#       WORD wReserved;
#     } ;
#   }     ;
#   DWORD     dwPageSize;
#   LPVOID    lpMinimumApplicationAddress;
#   LPVOID    lpMaximumApplicationAddress;
#   DWORD_PTR dwActiveProcessorMask;
#   DWORD     dwNumberOfProcessors;
#   DWORD     dwProcessorType;
#   DWORD     dwAllocationGranularity;
#   WORD      wProcessorLevel;
#   WORD      wProcessorRevision;
# } SYSTEM_INFO;


class _SYSTEM_INFO_OEM_ID_STRUCT(Structure):
    _fields_ = [
        ("wProcessorArchitecture", WORD),
        ("wReserved", WORD),
    ]


class _SYSTEM_INFO_OEM_ID(Union):
    _fields_ = [
        ("dwOemId", DWORD),
        ("w", _SYSTEM_INFO_OEM_ID_STRUCT),
    ]


class SYSTEM_INFO(Structure):
    _fields_ = [
        ("id", _SYSTEM_INFO_OEM_ID),
        ("dwPageSize", DWORD),
        ("lpMinimumApplicationAddress", LPVOID),
        ("lpMaximumApplicationAddress", LPVOID),
        ("dwActiveProcessorMask", DWORD_PTR),
        ("dwNumberOfProcessors", DWORD),
        ("dwProcessorType", DWORD),
        ("dwAllocationGranularity", DWORD),
        ("wProcessorLevel", WORD),
        ("wProcessorRevision", WORD),
    ]

    def __get_dwOemId(self):
        return self.id.dwOemId

    def __set_dwOemId(self, value):
        self.id.dwOemId = value

    dwOemId = property(__get_dwOemId, __set_dwOemId)

    def __get_wProcessorArchitecture(self):
        return self.id.w.wProcessorArchitecture

    def __set_wProcessorArchitecture(self, value):
        self.id.w.wProcessorArchitecture = value

    wProcessorArchitecture = property(__get_wProcessorArchitecture, __set_wProcessorArchitecture)


LPSYSTEM_INFO = ctypes.POINTER(SYSTEM_INFO)


# void WINAPI GetSystemInfo(
#   __out  LPSYSTEM_INFO lpSystemInfo
# );
def GetSystemInfo():
    _GetSystemInfo = windll.kernel32.GetSystemInfo
    _GetSystemInfo.argtypes = [LPSYSTEM_INFO]
    _GetSystemInfo.restype = None

    sysinfo = SYSTEM_INFO()
    _GetSystemInfo(byref(sysinfo))
    return sysinfo


# void WINAPI GetNativeSystemInfo(
#   __out  LPSYSTEM_INFO lpSystemInfo
# );
def GetNativeSystemInfo():
    _GetNativeSystemInfo = windll.kernel32.GetNativeSystemInfo
    _GetNativeSystemInfo.argtypes = [LPSYSTEM_INFO]
    _GetNativeSystemInfo.restype = None

    sysinfo = SYSTEM_INFO()
    _GetNativeSystemInfo(byref(sysinfo))
    return sysinfo


# int WINAPI GetSystemMetrics(
#   __in  int nIndex
# );
def GetSystemMetrics(nIndex):
    _GetSystemMetrics = windll.user32.GetSystemMetrics
    _GetSystemMetrics.argtypes = [ctypes.c_int]
    _GetSystemMetrics.restype = ctypes.c_int
    return _GetSystemMetrics(nIndex)


# SIZE_T WINAPI GetLargePageMinimum(void);
def GetLargePageMinimum():
    _GetLargePageMinimum = windll.user32.GetLargePageMinimum
    _GetLargePageMinimum.argtypes = []
    _GetLargePageMinimum.restype = SIZE_T
    return _GetLargePageMinimum()


# HANDLE WINAPI GetCurrentProcess(void);
def GetCurrentProcess():
    ##    return 0xFFFFFFFFFFFFFFFFL
    _GetCurrentProcess = windll.kernel32.GetCurrentProcess
    _GetCurrentProcess.argtypes = []
    _GetCurrentProcess.restype = HANDLE
    return _GetCurrentProcess()


# HANDLE WINAPI GetCurrentThread(void);
def GetCurrentThread():
    ##    return 0xFFFFFFFFFFFFFFFEL
    _GetCurrentThread = windll.kernel32.GetCurrentThread
    _GetCurrentThread.argtypes = []
    _GetCurrentThread.restype = HANDLE
    return _GetCurrentThread()


# BOOL WINAPI IsWow64Process(
#   __in   HANDLE hProcess,
#   __out  PBOOL Wow64Process
# );
def IsWow64Process(hProcess):
    _IsWow64Process = windll.kernel32.IsWow64Process
    _IsWow64Process.argtypes = [HANDLE, PBOOL]
    _IsWow64Process.restype = bool
    _IsWow64Process.errcheck = RaiseIfZero

    Wow64Process = BOOL(FALSE)
    _IsWow64Process(hProcess, byref(Wow64Process))
    return bool(Wow64Process)


# DWORD WINAPI GetVersion(void);
def GetVersion():
    _GetVersion = windll.kernel32.GetVersion
    _GetVersion.argtypes = []
    _GetVersion.restype = DWORD
    _GetVersion.errcheck = RaiseIfZero

    # See the example code here:
    # http://msdn.microsoft.com/en-us/library/ms724439(VS.85).aspx

    dwVersion = _GetVersion()
    dwMajorVersion = dwVersion & 0x000000FF
    dwMinorVersion = (dwVersion & 0x0000FF00) >> 8
    if (dwVersion & 0x80000000) == 0:
        dwBuild = (dwVersion & 0x7FFF0000) >> 16
    else:
        dwBuild = None
    return int(dwMajorVersion), int(dwMinorVersion), int(dwBuild)


# BOOL WINAPI GetVersionEx(
#   __inout  LPOSVERSIONINFO lpVersionInfo
# );
def GetVersionExA():
    _GetVersionExA = windll.kernel32.GetVersionExA
    _GetVersionExA.argtypes = [POINTER(OSVERSIONINFOEXA)]
    _GetVersionExA.restype = bool
    _GetVersionExA.errcheck = RaiseIfZero

    osi = OSVERSIONINFOEXA()
    osi.dwOSVersionInfoSize = sizeof(osi)
    try:
        _GetVersionExA(byref(osi))
    except WindowsError:
        osi = OSVERSIONINFOA()
        osi.dwOSVersionInfoSize = sizeof(osi)
        _GetVersionExA.argtypes = [POINTER(OSVERSIONINFOA)]
        _GetVersionExA(byref(osi))
    return osi


def GetVersionExW():
    _GetVersionExW = windll.kernel32.GetVersionExW
    _GetVersionExW.argtypes = [POINTER(OSVERSIONINFOEXW)]
    _GetVersionExW.restype = bool
    _GetVersionExW.errcheck = RaiseIfZero

    osi = OSVERSIONINFOEXW()
    osi.dwOSVersionInfoSize = sizeof(osi)
    try:
        _GetVersionExW(byref(osi))
    except WindowsError:
        osi = OSVERSIONINFOW()
        osi.dwOSVersionInfoSize = sizeof(osi)
        _GetVersionExW.argtypes = [POINTER(OSVERSIONINFOW)]
        _GetVersionExW(byref(osi))
    return osi


GetVersionEx = GuessStringType(GetVersionExA, GetVersionExW)


# BOOL WINAPI GetProductInfo(
#   __in   DWORD dwOSMajorVersion,
#   __in   DWORD dwOSMinorVersion,
#   __in   DWORD dwSpMajorVersion,
#   __in   DWORD dwSpMinorVersion,
#   __out  PDWORD pdwReturnedProductType
# );
def GetProductInfo(dwOSMajorVersion, dwOSMinorVersion, dwSpMajorVersion, dwSpMinorVersion):
    _GetProductInfo = windll.kernel32.GetProductInfo
    _GetProductInfo.argtypes = [DWORD, DWORD, DWORD, DWORD, PDWORD]
    _GetProductInfo.restype = BOOL
    _GetProductInfo.errcheck = RaiseIfZero

    dwReturnedProductType = DWORD(0)
    _GetProductInfo(dwOSMajorVersion, dwOSMinorVersion, dwSpMajorVersion, dwSpMinorVersion, byref(dwReturnedProductType))
    return dwReturnedProductType.value


# BOOL WINAPI VerifyVersionInfo(
#   __in  LPOSVERSIONINFOEX lpVersionInfo,
#   __in  DWORD dwTypeMask,
#   __in  DWORDLONG dwlConditionMask
# );
def VerifyVersionInfo(lpVersionInfo, dwTypeMask, dwlConditionMask):
    if isinstance(lpVersionInfo, OSVERSIONINFOEXA):
        return VerifyVersionInfoA(lpVersionInfo, dwTypeMask, dwlConditionMask)
    if isinstance(lpVersionInfo, OSVERSIONINFOEXW):
        return VerifyVersionInfoW(lpVersionInfo, dwTypeMask, dwlConditionMask)
    raise TypeError("Bad OSVERSIONINFOEX structure")


def VerifyVersionInfoA(lpVersionInfo, dwTypeMask, dwlConditionMask):
    _VerifyVersionInfoA = windll.kernel32.VerifyVersionInfoA
    _VerifyVersionInfoA.argtypes = [LPOSVERSIONINFOEXA, DWORD, DWORDLONG]
    _VerifyVersionInfoA.restype = bool
    return _VerifyVersionInfoA(byref(lpVersionInfo), dwTypeMask, dwlConditionMask)


def VerifyVersionInfoW(lpVersionInfo, dwTypeMask, dwlConditionMask):
    _VerifyVersionInfoW = windll.kernel32.VerifyVersionInfoW
    _VerifyVersionInfoW.argtypes = [LPOSVERSIONINFOEXW, DWORD, DWORDLONG]
    _VerifyVersionInfoW.restype = bool
    return _VerifyVersionInfoW(byref(lpVersionInfo), dwTypeMask, dwlConditionMask)


# ULONGLONG WINAPI VerSetConditionMask(
#   __in  ULONGLONG dwlConditionMask,
#   __in  DWORD dwTypeBitMask,
#   __in  BYTE dwConditionMask
# );
def VerSetConditionMask(dwlConditionMask, dwTypeBitMask, dwConditionMask):
    _VerSetConditionMask = windll.kernel32.VerSetConditionMask
    _VerSetConditionMask.argtypes = [ULONGLONG, DWORD, BYTE]
    _VerSetConditionMask.restype = ULONGLONG
    return _VerSetConditionMask(dwlConditionMask, dwTypeBitMask, dwConditionMask)


# --- get_bits, get_arch and get_os --------------------------------------------

ARCH_UNKNOWN = "unknown"
ARCH_I386 = "i386"
ARCH_MIPS = "mips"
ARCH_ALPHA = "alpha"
ARCH_PPC = "ppc"
ARCH_SHX = "shx"
ARCH_ARM = "arm"
ARCH_ARM64 = "arm64"
ARCH_THUMB = "thumb"
ARCH_IA64 = "ia64"
ARCH_ALPHA64 = "alpha64"
ARCH_MSIL = "msil"
ARCH_AMD64 = "amd64"
ARCH_SPARC = "sparc"

# aliases
ARCH_IA32 = ARCH_I386
ARCH_X86 = ARCH_I386
ARCH_X64 = ARCH_AMD64
ARCH_ARM7 = ARCH_ARM
ARCH_ARM8 = ARCH_ARM64
ARCH_T32 = ARCH_THUMB
ARCH_AARCH32 = ARCH_ARM7
ARCH_AARCH64 = ARCH_ARM8
ARCH_POWERPC = ARCH_PPC
ARCH_HITACHI = ARCH_SHX
ARCH_ITANIUM = ARCH_IA64

# win32 constants -> our constants
_arch_map = {
    PROCESSOR_ARCHITECTURE_INTEL: ARCH_I386,
    PROCESSOR_ARCHITECTURE_MIPS: ARCH_MIPS,
    PROCESSOR_ARCHITECTURE_ALPHA: ARCH_ALPHA,
    PROCESSOR_ARCHITECTURE_PPC: ARCH_PPC,
    PROCESSOR_ARCHITECTURE_SHX: ARCH_SHX,
    PROCESSOR_ARCHITECTURE_ARM: ARCH_ARM,
    PROCESSOR_ARCHITECTURE_IA64: ARCH_IA64,
    PROCESSOR_ARCHITECTURE_ALPHA64: ARCH_ALPHA64,
    PROCESSOR_ARCHITECTURE_MSIL: ARCH_MSIL,
    PROCESSOR_ARCHITECTURE_AMD64: ARCH_AMD64,
    PROCESSOR_ARCHITECTURE_SPARC: ARCH_SPARC,
}

OS_UNKNOWN = "Unknown"
OS_NT = "Windows NT"
OS_W2K = "Windows 2000"
OS_XP = "Windows XP"
OS_XP_64 = "Windows XP (64 bits)"
OS_W2K3 = "Windows 2003"
OS_W2K3_64 = "Windows 2003 (64 bits)"
OS_W2K3R2 = "Windows 2003 R2"
OS_W2K3R2_64 = "Windows 2003 R2 (64 bits)"
OS_W2K8 = "Windows 2008"
OS_W2K8_64 = "Windows 2008 (64 bits)"
OS_W2K8R2 = "Windows 2008 R2"
OS_W2K8R2_64 = "Windows 2008 R2 (64 bits)"
OS_VISTA = "Windows Vista"
OS_VISTA_64 = "Windows Vista (64 bits)"
OS_W7 = "Windows 7"
OS_W7_64 = "Windows 7 (64 bits)"

OS_SEVEN = OS_W7
OS_SEVEN_64 = OS_W7_64

OS_WINDOWS_NT = OS_NT
OS_WINDOWS_2000 = OS_W2K
OS_WINDOWS_XP = OS_XP
OS_WINDOWS_XP_64 = OS_XP_64
OS_WINDOWS_2003 = OS_W2K3
OS_WINDOWS_2003_64 = OS_W2K3_64
OS_WINDOWS_2003_R2 = OS_W2K3R2
OS_WINDOWS_2003_R2_64 = OS_W2K3R2_64
OS_WINDOWS_2008 = OS_W2K8
OS_WINDOWS_2008_64 = OS_W2K8_64
OS_WINDOWS_2008_R2 = OS_W2K8R2
OS_WINDOWS_2008_R2_64 = OS_W2K8R2_64
OS_WINDOWS_VISTA = OS_VISTA
OS_WINDOWS_VISTA_64 = OS_VISTA_64
OS_WINDOWS_SEVEN = OS_W7
OS_WINDOWS_SEVEN_64 = OS_W7_64


def _get_bits():
    """
    Determines the current integer size in bits.

    This is useful to know if we're running in a 32 bits or a 64 bits machine.

    @rtype: int
    @return: Returns the size of L{SIZE_T} in bits.
    """
    return sizeof(SIZE_T) * 8


def _get_arch():
    """
    Determines the current processor architecture.

    @rtype: str
    @return:
        On error, returns:

         - L{ARCH_UNKNOWN} (C{"unknown"}) meaning the architecture could not be detected or is not known to WinAppDbg.

        On success, returns one of the following values:

         - L{ARCH_I386} (C{"i386"}) for Intel 32-bit x86 processor or compatible.
         - L{ARCH_AMD64} (C{"amd64"}) for Intel 64-bit x86_64 processor or compatible.

        May also return one of the following values if you get both Python and
        WinAppDbg to work in such machines... let me know if you do! :)

         - L{ARCH_MIPS} (C{"mips"}) for MIPS compatible processors.
         - L{ARCH_ALPHA} (C{"alpha"}) for Alpha processors.
         - L{ARCH_PPC} (C{"ppc"}) for PowerPC compatible processors.
         - L{ARCH_SHX} (C{"shx"}) for Hitachi SH processors.
         - L{ARCH_ARM} (C{"arm"}) for ARM compatible processors.
         - L{ARCH_IA64} (C{"ia64"}) for Intel Itanium processor or compatible.
         - L{ARCH_ALPHA64} (C{"alpha64"}) for Alpha64 processors.
         - L{ARCH_MSIL} (C{"msil"}) for the .NET virtual machine.
         - L{ARCH_SPARC} (C{"sparc"}) for Sun Sparc processors.

        Probably IronPython returns C{ARCH_MSIL} but I haven't tried it. Python
        on Windows CE and Windows Mobile should return C{ARCH_ARM}. Python on
        Solaris using Wine would return C{ARCH_SPARC}. Python in an Itanium
        machine should return C{ARCH_IA64} both on Wine and proper Windows.
        All other values should only be returned on Linux using Wine.
    """
    try:
        si = GetNativeSystemInfo()
    except Exception:
        si = GetSystemInfo()
    try:
        return _arch_map[si.id.w.wProcessorArchitecture]
    except KeyError:
        return ARCH_UNKNOWN


def _get_wow64():
    """
    Determines if the current process is running in Windows-On-Windows 64 bits.

    @rtype:  bool
    @return: C{True} of the current process is a 32 bit program running in a
        64 bit version of Windows, C{False} if it's either a 32 bit program
        in a 32 bit Windows or a 64 bit program in a 64 bit Windows.
    """
    # Try to determine if the debugger itself is running on WOW64.
    # On error assume False.
    if bits == 64:
        wow64 = False
    else:
        try:
            wow64 = IsWow64Process(GetCurrentProcess())
        except Exception:
            wow64 = False
    return wow64


def _get_os(osvi=None):
    """
    Determines the current operating system.

    This function allows you to quickly tell apart major OS differences.
    For more detailed information call L{GetVersionEx} instead.

    @note:
        Wine reports itself as Windows XP 32 bits
        (even if the Linux host is 64 bits).
        ReactOS may report itself as Windows 2000 or Windows XP,
        depending on the version of ReactOS.

    @type  osvi: L{OSVERSIONINFOEXA}
    @param osvi: Optional. The return value from L{GetVersionEx}.

    @rtype: str
    @return:
        One of the following values:
         - L{OS_UNKNOWN} (C{"Unknown"})
         - L{OS_NT} (C{"Windows NT"})
         - L{OS_W2K} (C{"Windows 2000"})
         - L{OS_XP} (C{"Windows XP"})
         - L{OS_XP_64} (C{"Windows XP (64 bits)"})
         - L{OS_W2K3} (C{"Windows 2003"})
         - L{OS_W2K3_64} (C{"Windows 2003 (64 bits)"})
         - L{OS_W2K3R2} (C{"Windows 2003 R2"})
         - L{OS_W2K3R2_64} (C{"Windows 2003 R2 (64 bits)"})
         - L{OS_W2K8} (C{"Windows 2008"})
         - L{OS_W2K8_64} (C{"Windows 2008 (64 bits)"})
         - L{OS_W2K8R2} (C{"Windows 2008 R2"})
         - L{OS_W2K8R2_64} (C{"Windows 2008 R2 (64 bits)"})
         - L{OS_VISTA} (C{"Windows Vista"})
         - L{OS_VISTA_64} (C{"Windows Vista (64 bits)"})
         - L{OS_W7} (C{"Windows 7"})
         - L{OS_W7_64} (C{"Windows 7 (64 bits)"})
    """
    # rough port of http://msdn.microsoft.com/en-us/library/ms724429%28VS.85%29.aspx
    if not osvi:
        osvi = GetVersionEx()
    if osvi.dwPlatformId == VER_PLATFORM_WIN32_NT and osvi.dwMajorVersion > 4:
        if osvi.dwMajorVersion == 6:
            if osvi.dwMinorVersion == 0:
                if osvi.wProductType == VER_NT_WORKSTATION:
                    if bits == 64 or wow64:
                        return "Windows Vista (64 bits)"
                    return "Windows Vista"
                else:
                    if bits == 64 or wow64:
                        return "Windows 2008 (64 bits)"
                    return "Windows 2008"
            if osvi.dwMinorVersion == 1:
                if osvi.wProductType == VER_NT_WORKSTATION:
                    if bits == 64 or wow64:
                        return "Windows 7 (64 bits)"
                    return "Windows 7"
                else:
                    if bits == 64 or wow64:
                        return "Windows 2008 R2 (64 bits)"
                    return "Windows 2008 R2"
        if osvi.dwMajorVersion == 5:
            if osvi.dwMinorVersion == 2:
                if GetSystemMetrics(SM_SERVERR2):
                    if bits == 64 or wow64:
                        return "Windows 2003 R2 (64 bits)"
                    return "Windows 2003 R2"
                if osvi.wSuiteMask in (VER_SUITE_STORAGE_SERVER, VER_SUITE_WH_SERVER):
                    if bits == 64 or wow64:
                        return "Windows 2003 (64 bits)"
                    return "Windows 2003"
                if osvi.wProductType == VER_NT_WORKSTATION and arch == ARCH_AMD64:
                    return "Windows XP (64 bits)"
                else:
                    if bits == 64 or wow64:
                        return "Windows 2003 (64 bits)"
                    return "Windows 2003"
            if osvi.dwMinorVersion == 1:
                return "Windows XP"
            if osvi.dwMinorVersion == 0:
                return "Windows 2000"
        if osvi.dwMajorVersion == 4:
            return "Windows NT"
    return "Unknown"


def _get_ntddi(osvi):
    """
    Determines the current operating system.

    This function allows you to quickly tell apart major OS differences.
    For more detailed information call L{kernel32.GetVersionEx} instead.

    @note:
        Wine reports itself as Windows XP 32 bits
        (even if the Linux host is 64 bits).
        ReactOS may report itself as Windows 2000 or Windows XP,
        depending on the version of ReactOS.

    @type  osvi: L{OSVERSIONINFOEXA}
    @param osvi: Optional. The return value from L{kernel32.GetVersionEx}.

    @rtype:  int
    @return: NTDDI version number.
    """
    if not osvi:
        osvi = GetVersionEx()
    ntddi = 0
    ntddi += (osvi.dwMajorVersion & 0xFF) << 24
    ntddi += (osvi.dwMinorVersion & 0xFF) << 16
    ntddi += (osvi.wServicePackMajor & 0xFF) << 8
    ntddi += osvi.wServicePackMinor & 0xFF
    return ntddi


# The order of the following definitions DOES matter!

# Current integer size in bits. See L{_get_bits} for more details.
bits = _get_bits()

# Current processor architecture. See L{_get_arch} for more details.
arch = _get_arch()

# Set to C{True} if the current process is running in WOW64. See L{_get_wow64} for more details.
wow64 = _get_wow64()

_osvi = GetVersionEx()

# Current operating system. See L{_get_os} for more details.
os = _get_os(_osvi)

# Current operating system as an NTDDI constant. See L{_get_ntddi} for more details.
NTDDI_VERSION = _get_ntddi(_osvi)

# Upper word of L{NTDDI_VERSION}, contains the OS major and minor version number.
WINVER = NTDDI_VERSION >> 16

# --- version.dll --------------------------------------------------------------

VS_FF_DEBUG = 0x00000001
VS_FF_PRERELEASE = 0x00000002
VS_FF_PATCHED = 0x00000004
VS_FF_PRIVATEBUILD = 0x00000008
VS_FF_INFOINFERRED = 0x00000010
VS_FF_SPECIALBUILD = 0x00000020

VOS_UNKNOWN = 0x00000000
VOS__WINDOWS16 = 0x00000001
VOS__PM16 = 0x00000002
VOS__PM32 = 0x00000003
VOS__WINDOWS32 = 0x00000004
VOS_DOS = 0x00010000
VOS_OS216 = 0x00020000
VOS_OS232 = 0x00030000
VOS_NT = 0x00040000

VOS_DOS_WINDOWS16 = 0x00010001
VOS_DOS_WINDOWS32 = 0x00010004
VOS_NT_WINDOWS32 = 0x00040004
VOS_OS216_PM16 = 0x00020002
VOS_OS232_PM32 = 0x00030003

VFT_UNKNOWN = 0x00000000
VFT_APP = 0x00000001
VFT_DLL = 0x00000002
VFT_DRV = 0x00000003
VFT_FONT = 0x00000004
VFT_VXD = 0x00000005
VFT_RESERVED = 0x00000006  # undocumented
VFT_STATIC_LIB = 0x00000007

VFT2_UNKNOWN = 0x00000000

VFT2_DRV_PRINTER = 0x00000001
VFT2_DRV_KEYBOARD = 0x00000002
VFT2_DRV_LANGUAGE = 0x00000003
VFT2_DRV_DISPLAY = 0x00000004
VFT2_DRV_MOUSE = 0x00000005
VFT2_DRV_NETWORK = 0x00000006
VFT2_DRV_SYSTEM = 0x00000007
VFT2_DRV_INSTALLABLE = 0x00000008
VFT2_DRV_SOUND = 0x00000009
VFT2_DRV_COMM = 0x0000000A
VFT2_DRV_RESERVED = 0x0000000B  # undocumented
VFT2_DRV_VERSIONED_PRINTER = 0x0000000C

VFT2_FONT_RASTER = 0x00000001
VFT2_FONT_VECTOR = 0x00000002
VFT2_FONT_TRUETYPE = 0x00000003


# typedef struct tagVS_FIXEDFILEINFO {
#   DWORD dwSignature;
#   DWORD dwStrucVersion;
#   DWORD dwFileVersionMS;
#   DWORD dwFileVersionLS;
#   DWORD dwProductVersionMS;
#   DWORD dwProductVersionLS;
#   DWORD dwFileFlagsMask;
#   DWORD dwFileFlags;
#   DWORD dwFileOS;
#   DWORD dwFileType;
#   DWORD dwFileSubtype;
#   DWORD dwFileDateMS;
#   DWORD dwFileDateLS;
# } VS_FIXEDFILEINFO;
class VS_FIXEDFILEINFO(Structure):
    _fields_ = [
        ("dwSignature", DWORD),
        ("dwStrucVersion", DWORD),
        ("dwFileVersionMS", DWORD),
        ("dwFileVersionLS", DWORD),
        ("dwProductVersionMS", DWORD),
        ("dwProductVersionLS", DWORD),
        ("dwFileFlagsMask", DWORD),
        ("dwFileFlags", DWORD),
        ("dwFileOS", DWORD),
        ("dwFileType", DWORD),
        ("dwFileSubtype", DWORD),
        ("dwFileDateMS", DWORD),
        ("dwFileDateLS", DWORD),
    ]


PVS_FIXEDFILEINFO = POINTER(VS_FIXEDFILEINFO)
LPVS_FIXEDFILEINFO = PVS_FIXEDFILEINFO


# BOOL WINAPI GetFileVersionInfo(
#   _In_        LPCTSTR lptstrFilename,
#   _Reserved_  DWORD dwHandle,
#   _In_        DWORD dwLen,
#   _Out_       LPVOID lpData
# );
# DWORD WINAPI GetFileVersionInfoSize(
#   _In_       LPCTSTR lptstrFilename,
#   _Out_opt_  LPDWORD lpdwHandle
# );
def GetFileVersionInfoA(lptstrFilename):
    _GetFileVersionInfoA = windll.version.GetFileVersionInfoA
    _GetFileVersionInfoA.argtypes = [LPSTR, DWORD, DWORD, LPVOID]
    _GetFileVersionInfoA.restype = bool
    _GetFileVersionInfoA.errcheck = RaiseIfZero

    _GetFileVersionInfoSizeA = windll.version.GetFileVersionInfoSizeA
    _GetFileVersionInfoSizeA.argtypes = [LPSTR, LPVOID]
    _GetFileVersionInfoSizeA.restype = DWORD
    _GetFileVersionInfoSizeA.errcheck = RaiseIfZero

    dwLen = _GetFileVersionInfoSizeA(lptstrFilename, None)
    lpData = ctypes.create_string_buffer(dwLen)
    _GetFileVersionInfoA(lptstrFilename, 0, dwLen, byref(lpData))
    return lpData


def GetFileVersionInfoW(lptstrFilename):
    _GetFileVersionInfoW = windll.version.GetFileVersionInfoW
    _GetFileVersionInfoW.argtypes = [LPWSTR, DWORD, DWORD, LPVOID]
    _GetFileVersionInfoW.restype = bool
    _GetFileVersionInfoW.errcheck = RaiseIfZero

    _GetFileVersionInfoSizeW = windll.version.GetFileVersionInfoSizeW
    _GetFileVersionInfoSizeW.argtypes = [LPWSTR, LPVOID]
    _GetFileVersionInfoSizeW.restype = DWORD
    _GetFileVersionInfoSizeW.errcheck = RaiseIfZero

    dwLen = _GetFileVersionInfoSizeW(lptstrFilename, None)
    lpData = ctypes.create_string_buffer(dwLen)  # not a string!
    _GetFileVersionInfoW(lptstrFilename, 0, dwLen, byref(lpData))
    return lpData


GetFileVersionInfo = GuessStringType(GetFileVersionInfoA, GetFileVersionInfoW)


# BOOL WINAPI VerQueryValue(
#   _In_   LPCVOID pBlock,
#   _In_   LPCTSTR lpSubBlock,
#   _Out_  LPVOID *lplpBuffer,
#   _Out_  PUINT puLen
# );
def VerQueryValueA(pBlock, lpSubBlock):
    _VerQueryValueA = windll.version.VerQueryValueA
    _VerQueryValueA.argtypes = [LPVOID, LPSTR, LPVOID, POINTER(UINT)]
    _VerQueryValueA.restype = bool
    _VerQueryValueA.errcheck = RaiseIfZero

    lpBuffer = LPVOID(0)
    uLen = UINT(0)
    _VerQueryValueA(pBlock, lpSubBlock, byref(lpBuffer), byref(uLen))
    return lpBuffer, uLen.value


def VerQueryValueW(pBlock, lpSubBlock):
    _VerQueryValueW = windll.version.VerQueryValueW
    _VerQueryValueW.argtypes = [LPVOID, LPWSTR, LPVOID, POINTER(UINT)]
    _VerQueryValueW.restype = bool
    _VerQueryValueW.errcheck = RaiseIfZero

    lpBuffer = LPVOID(0)
    uLen = UINT(0)
    _VerQueryValueW(pBlock, lpSubBlock, byref(lpBuffer), byref(uLen))
    return lpBuffer, uLen.value


VerQueryValue = GuessStringType(VerQueryValueA, VerQueryValueW)

# ==============================================================================
# This calculates the list of exported symbols.
_all = set(vars().keys()).difference(_all)
__all__ = [_x for _x in _all if not _x.startswith("_")]
__all__.sort()
# ==============================================================================

# === NexusCore/openenv\Lib\site-packages\cffi\vengine_cpy.py ===
#
# DEPRECATED: implementation for ffi.verify()
#
import sys
from . import model
from .error import VerificationError
from . import _imp_emulation as imp


class VCPythonEngine(object):
    _class_key = 'x'
    _gen_python_module = True

    def __init__(self, verifier):
        self.verifier = verifier
        self.ffi = verifier.ffi
        self._struct_pending_verification = {}
        self._types_of_builtin_functions = {}

    def patch_extension_kwds(self, kwds):
        pass

    def find_module(self, module_name, path, so_suffixes):
        try:
            f, filename, descr = imp.find_module(module_name, path)
        except ImportError:
            return None
        if f is not None:
            f.close()
        # Note that after a setuptools installation, there are both .py
        # and .so files with the same basename.  The code here relies on
        # imp.find_module() locating the .so in priority.
        if descr[0] not in so_suffixes:
            return None
        return filename

    def collect_types(self):
        self._typesdict = {}
        self._generate("collecttype")

    def _prnt(self, what=''):
        self._f.write(what + '\n')

    def _gettypenum(self, type):
        # a KeyError here is a bug.  please report it! :-)
        return self._typesdict[type]

    def _do_collect_type(self, tp):
        if ((not isinstance(tp, model.PrimitiveType)
             or tp.name == 'long double')
                and tp not in self._typesdict):
            num = len(self._typesdict)
            self._typesdict[tp] = num

    def write_source_to_f(self):
        self.collect_types()
        #
        # The new module will have a _cffi_setup() function that receives
        # objects from the ffi world, and that calls some setup code in
        # the module.  This setup code is split in several independent
        # functions, e.g. one per constant.  The functions are "chained"
        # by ending in a tail call to each other.
        #
        # This is further split in two chained lists, depending on if we
        # can do it at import-time or if we must wait for _cffi_setup() to
        # provide us with the <ctype> objects.  This is needed because we
        # need the values of the enum constants in order to build the
        # <ctype 'enum'> that we may have to pass to _cffi_setup().
        #
        # The following two 'chained_list_constants' items contains
        # the head of these two chained lists, as a string that gives the
        # call to do, if any.
        self._chained_list_constants = ['((void)lib,0)', '((void)lib,0)']
        #
        prnt = self._prnt
        # first paste some standard set of lines that are mostly '#define'
        prnt(cffimod_header)
        prnt()
        # then paste the C source given by the user, verbatim.
        prnt(self.verifier.preamble)
        prnt()
        #
        # call generate_cpy_xxx_decl(), for every xxx found from
        # ffi._parser._declarations.  This generates all the functions.
        self._generate("decl")
        #
        # implement the function _cffi_setup_custom() as calling the
        # head of the chained list.
        self._generate_setup_custom()
        prnt()
        #
        # produce the method table, including the entries for the
        # generated Python->C function wrappers, which are done
        # by generate_cpy_function_method().
        prnt('static PyMethodDef _cffi_methods[] = {')
        self._generate("method")
        prnt('  {"_cffi_setup", _cffi_setup, METH_VARARGS, NULL},')
        prnt('  {NULL, NULL, 0, NULL}    /* Sentinel */')
        prnt('};')
        prnt()
        #
        # standard init.
        modname = self.verifier.get_module_name()
        constants = self._chained_list_constants[False]
        prnt('#if PY_MAJOR_VERSION >= 3')
        prnt()
        prnt('static struct PyModuleDef _cffi_module_def = {')
        prnt('  PyModuleDef_HEAD_INIT,')
        prnt('  "%s",' % modname)
        prnt('  NULL,')
        prnt('  -1,')
        prnt('  _cffi_methods,')
        prnt('  NULL, NULL, NULL, NULL')
        prnt('};')
        prnt()
        prnt('PyMODINIT_FUNC')
        prnt('PyInit_%s(void)' % modname)
        prnt('{')
        prnt('  PyObject *lib;')
        prnt('  lib = PyModule_Create(&_cffi_module_def);')
        prnt('  if (lib == NULL)')
        prnt('    return NULL;')
        prnt('  if (%s < 0 || _cffi_init() < 0) {' % (constants,))
        prnt('    Py_DECREF(lib);')
        prnt('    return NULL;')
        prnt('  }')
        prnt('  return lib;')
        prnt('}')
        prnt()
        prnt('#else')
        prnt()
        prnt('PyMODINIT_FUNC')
        prnt('init%s(void)' % modname)
        prnt('{')
        prnt('  PyObject *lib;')
        prnt('  lib = Py_InitModule("%s", _cffi_methods);' % modname)
        prnt('  if (lib == NULL)')
        prnt('    return;')
        prnt('  if (%s < 0 || _cffi_init() < 0)' % (constants,))
        prnt('    return;')
        prnt('  return;')
        prnt('}')
        prnt()
        prnt('#endif')

    def load_library(self, flags=None):
        # XXX review all usages of 'self' here!
        # import it as a new extension module
        imp.acquire_lock()
        try:
            if hasattr(sys, "getdlopenflags"):
                previous_flags = sys.getdlopenflags()
            try:
                if hasattr(sys, "setdlopenflags") and flags is not None:
                    sys.setdlopenflags(flags)
                module = imp.load_dynamic(self.verifier.get_module_name(),
                                          self.verifier.modulefilename)
            except ImportError as e:
                error = "importing %r: %s" % (self.verifier.modulefilename, e)
                raise VerificationError(error)
            finally:
                if hasattr(sys, "setdlopenflags"):
                    sys.setdlopenflags(previous_flags)
        finally:
            imp.release_lock()
        #
        # call loading_cpy_struct() to get the struct layout inferred by
        # the C compiler
        self._load(module, 'loading')
        #
        # the C code will need the <ctype> objects.  Collect them in
        # order in a list.
        revmapping = dict([(value, key)
                           for (key, value) in self._typesdict.items()])
        lst = [revmapping[i] for i in range(len(revmapping))]
        lst = list(map(self.ffi._get_cached_btype, lst))
        #
        # build the FFILibrary class and instance and call _cffi_setup().
        # this will set up some fields like '_cffi_types', and only then
        # it will invoke the chained list of functions that will really
        # build (notably) the constant objects, as <cdata> if they are
        # pointers, and store them as attributes on the 'library' object.
        class FFILibrary(object):
            _cffi_python_module = module
            _cffi_ffi = self.ffi
            _cffi_dir = []
            def __dir__(self):
                return FFILibrary._cffi_dir + list(self.__dict__)
        library = FFILibrary()
        if module._cffi_setup(lst, VerificationError, library):
            import warnings
            warnings.warn("reimporting %r might overwrite older definitions"
                          % (self.verifier.get_module_name()))
        #
        # finally, call the loaded_cpy_xxx() functions.  This will perform
        # the final adjustments, like copying the Python->C wrapper
        # functions from the module to the 'library' object, and setting
        # up the FFILibrary class with properties for the global C variables.
        self._load(module, 'loaded', library=library)
        module._cffi_original_ffi = self.ffi
        module._cffi_types_of_builtin_funcs = self._types_of_builtin_functions
        return library

    def _get_declarations(self):
        lst = [(key, tp) for (key, (tp, qual)) in
                                self.ffi._parser._declarations.items()]
        lst.sort()
        return lst

    def _generate(self, step_name):
        for name, tp in self._get_declarations():
            kind, realname = name.split(' ', 1)
            try:
                method = getattr(self, '_generate_cpy_%s_%s' % (kind,
                                                                step_name))
            except AttributeError:
                raise VerificationError(
                    "not implemented in verify(): %r" % name)
            try:
                method(tp, realname)
            except Exception as e:
                model.attach_exception_info(e, name)
                raise

    def _load(self, module, step_name, **kwds):
        for name, tp in self._get_declarations():
            kind, realname = name.split(' ', 1)
            method = getattr(self, '_%s_cpy_%s' % (step_name, kind))
            try:
                method(tp, realname, module, **kwds)
            except Exception as e:
                model.attach_exception_info(e, name)
                raise

    def _generate_nothing(self, tp, name):
        pass

    def _loaded_noop(self, tp, name, module, **kwds):
        pass

    # ----------

    def _convert_funcarg_to_c(self, tp, fromvar, tovar, errcode):
        extraarg = ''
        if isinstance(tp, model.PrimitiveType):
            if tp.is_integer_type() and tp.name != '_Bool':
                converter = '_cffi_to_c_int'
                extraarg = ', %s' % tp.name
            elif tp.is_complex_type():
                raise VerificationError(
                    "not implemented in verify(): complex types")
            else:
                converter = '(%s)_cffi_to_c_%s' % (tp.get_c_name(''),
                                                   tp.name.replace(' ', '_'))
            errvalue = '-1'
        #
        elif isinstance(tp, model.PointerType):
            self._convert_funcarg_to_c_ptr_or_array(tp, fromvar,
                                                    tovar, errcode)
            return
        #
        elif isinstance(tp, (model.StructOrUnion, model.EnumType)):
            # a struct (not a struct pointer) as a function argument
            self._prnt('  if (_cffi_to_c((char *)&%s, _cffi_type(%d), %s) < 0)'
                      % (tovar, self._gettypenum(tp), fromvar))
            self._prnt('    %s;' % errcode)
            return
        #
        elif isinstance(tp, model.FunctionPtrType):
            converter = '(%s)_cffi_to_c_pointer' % tp.get_c_name('')
            extraarg = ', _cffi_type(%d)' % self._gettypenum(tp)
            errvalue = 'NULL'
        #
        else:
            raise NotImplementedError(tp)
        #
        self._prnt('  %s = %s(%s%s);' % (tovar, converter, fromvar, extraarg))
        self._prnt('  if (%s == (%s)%s && PyErr_Occurred())' % (
            tovar, tp.get_c_name(''), errvalue))
        self._prnt('    %s;' % errcode)

    def _extra_local_variables(self, tp, localvars, freelines):
        if isinstance(tp, model.PointerType):
            localvars.add('Py_ssize_t datasize')
            localvars.add('struct _cffi_freeme_s *large_args_free = NULL')
            freelines.add('if (large_args_free != NULL)'
                          ' _cffi_free_array_arguments(large_args_free);')

    def _convert_funcarg_to_c_ptr_or_array(self, tp, fromvar, tovar, errcode):
        self._prnt('  datasize = _cffi_prepare_pointer_call_argument(')
        self._prnt('      _cffi_type(%d), %s, (char **)&%s);' % (
            self._gettypenum(tp), fromvar, tovar))
        self._prnt('  if (datasize != 0) {')
        self._prnt('    %s = ((size_t)datasize) <= 640 ? '
                   'alloca((size_t)datasize) : NULL;' % (tovar,))
        self._prnt('    if (_cffi_convert_array_argument(_cffi_type(%d), %s, '
                   '(char **)&%s,' % (self._gettypenum(tp), fromvar, tovar))
        self._prnt('            datasize, &large_args_free) < 0)')
        self._prnt('      %s;' % errcode)
        self._prnt('  }')

    def _convert_expr_from_c(self, tp, var, context):
        if isinstance(tp, model.PrimitiveType):
            if tp.is_integer_type() and tp.name != '_Bool':
                return '_cffi_from_c_int(%s, %s)' % (var, tp.name)
            elif tp.name != 'long double':
                return '_cffi_from_c_%s(%s)' % (tp.name.replace(' ', '_'), var)
            else:
                return '_cffi_from_c_deref((char *)&%s, _cffi_type(%d))' % (
                    var, self._gettypenum(tp))
        elif isinstance(tp, (model.PointerType, model.FunctionPtrType)):
            return '_cffi_from_c_pointer((char *)%s, _cffi_type(%d))' % (
                var, self._gettypenum(tp))
        elif isinstance(tp, model.ArrayType):
            return '_cffi_from_c_pointer((char *)%s, _cffi_type(%d))' % (
                var, self._gettypenum(model.PointerType(tp.item)))
        elif isinstance(tp, model.StructOrUnion):
            if tp.fldnames is None:
                raise TypeError("'%s' is used as %s, but is opaque" % (
                    tp._get_c_name(), context))
            return '_cffi_from_c_struct((char *)&%s, _cffi_type(%d))' % (
                var, self._gettypenum(tp))
        elif isinstance(tp, model.EnumType):
            return '_cffi_from_c_deref((char *)&%s, _cffi_type(%d))' % (
                var, self._gettypenum(tp))
        else:
            raise NotImplementedError(tp)

    # ----------
    # typedefs: generates no code so far

    _generate_cpy_typedef_collecttype = _generate_nothing
    _generate_cpy_typedef_decl   = _generate_nothing
    _generate_cpy_typedef_method = _generate_nothing
    _loading_cpy_typedef         = _loaded_noop
    _loaded_cpy_typedef          = _loaded_noop

    # ----------
    # function declarations

    def _generate_cpy_function_collecttype(self, tp, name):
        assert isinstance(tp, model.FunctionPtrType)
        if tp.ellipsis:
            self._do_collect_type(tp)
        else:
            # don't call _do_collect_type(tp) in this common case,
            # otherwise test_autofilled_struct_as_argument fails
            for type in tp.args:
                self._do_collect_type(type)
            self._do_collect_type(tp.result)

    def _generate_cpy_function_decl(self, tp, name):
        assert isinstance(tp, model.FunctionPtrType)
        if tp.ellipsis:
            # cannot support vararg functions better than this: check for its
            # exact type (including the fixed arguments), and build it as a
            # constant function pointer (no CPython wrapper)
            self._generate_cpy_const(False, name, tp)
            return
        prnt = self._prnt
        numargs = len(tp.args)
        if numargs == 0:
            argname = 'noarg'
        elif numargs == 1:
            argname = 'arg0'
        else:
            argname = 'args'
        prnt('static PyObject *')
        prnt('_cffi_f_%s(PyObject *self, PyObject *%s)' % (name, argname))
        prnt('{')
        #
        context = 'argument of %s' % name
        for i, type in enumerate(tp.args):
            prnt('  %s;' % type.get_c_name(' x%d' % i, context))
        #
        localvars = set()
        freelines = set()
        for type in tp.args:
            self._extra_local_variables(type, localvars, freelines)
        for decl in sorted(localvars):
            prnt('  %s;' % (decl,))
        #
        if not isinstance(tp.result, model.VoidType):
            result_code = 'result = '
            context = 'result of %s' % name
            prnt('  %s;' % tp.result.get_c_name(' result', context))
            prnt('  PyObject *pyresult;')
        else:
            result_code = ''
        #
        if len(tp.args) > 1:
            rng = range(len(tp.args))
            for i in rng:
                prnt('  PyObject *arg%d;' % i)
            prnt()
            prnt('  if (!PyArg_ParseTuple(args, "%s:%s", %s))' % (
                'O' * numargs, name, ', '.join(['&arg%d' % i for i in rng])))
            prnt('    return NULL;')
        prnt()
        #
        for i, type in enumerate(tp.args):
            self._convert_funcarg_to_c(type, 'arg%d' % i, 'x%d' % i,
                                       'return NULL')
            prnt()
        #
        prnt('  Py_BEGIN_ALLOW_THREADS')
        prnt('  _cffi_restore_errno();')
        prnt('  { %s%s(%s); }' % (
            result_code, name,
            ', '.join(['x%d' % i for i in range(len(tp.args))])))
        prnt('  _cffi_save_errno();')
        prnt('  Py_END_ALLOW_THREADS')
        prnt()
        #
        prnt('  (void)self; /* unused */')
        if numargs == 0:
            prnt('  (void)noarg; /* unused */')
        if result_code:
            prnt('  pyresult = %s;' %
                 self._convert_expr_from_c(tp.result, 'result', 'result type'))
            for freeline in freelines:
                prnt('  ' + freeline)
            prnt('  return pyresult;')
        else:
            for freeline in freelines:
                prnt('  ' + freeline)
            prnt('  Py_INCREF(Py_None);')
            prnt('  return Py_None;')
        prnt('}')
        prnt()

    def _generate_cpy_function_method(self, tp, name):
        if tp.ellipsis:
            return
        numargs = len(tp.args)
        if numargs == 0:
            meth = 'METH_NOARGS'
        elif numargs == 1:
            meth = 'METH_O'
        else:
            meth = 'METH_VARARGS'
        self._prnt('  {"%s", _cffi_f_%s, %s, NULL},' % (name, name, meth))

    _loading_cpy_function = _loaded_noop

    def _loaded_cpy_function(self, tp, name, module, library):
        if tp.ellipsis:
            return
        func = getattr(module, name)
        setattr(library, name, func)
        self._types_of_builtin_functions[func] = tp

    # ----------
    # named structs

    _generate_cpy_struct_collecttype = _generate_nothing
    def _generate_cpy_struct_decl(self, tp, name):
        assert name == tp.name
        self._generate_struct_or_union_decl(tp, 'struct', name)
    def _generate_cpy_struct_method(self, tp, name):
        self._generate_struct_or_union_method(tp, 'struct', name)
    def _loading_cpy_struct(self, tp, name, module):
        self._loading_struct_or_union(tp, 'struct', name, module)
    def _loaded_cpy_struct(self, tp, name, module, **kwds):
        self._loaded_struct_or_union(tp)

    _generate_cpy_union_collecttype = _generate_nothing
    def _generate_cpy_union_decl(self, tp, name):
        assert name == tp.name
        self._generate_struct_or_union_decl(tp, 'union', name)
    def _generate_cpy_union_method(self, tp, name):
        self._generate_struct_or_union_method(tp, 'union', name)
    def _loading_cpy_union(self, tp, name, module):
        self._loading_struct_or_union(tp, 'union', name, module)
    def _loaded_cpy_union(self, tp, name, module, **kwds):
        self._loaded_struct_or_union(tp)

    def _generate_struct_or_union_decl(self, tp, prefix, name):
        if tp.fldnames is None:
            return     # nothing to do with opaque structs
        checkfuncname = '_cffi_check_%s_%s' % (prefix, name)
        layoutfuncname = '_cffi_layout_%s_%s' % (prefix, name)
        cname = ('%s %s' % (prefix, name)).strip()
        #
        prnt = self._prnt
        prnt('static void %s(%s *p)' % (checkfuncname, cname))
        prnt('{')
        prnt('  /* only to generate compile-time warnings or errors */')
        prnt('  (void)p;')
        for fname, ftype, fbitsize, fqual in tp.enumfields():
            if (isinstance(ftype, model.PrimitiveType)
                and ftype.is_integer_type()) or fbitsize >= 0:
                # accept all integers, but complain on float or double
                prnt('  (void)((p->%s) << 1);' % fname)
            else:
                # only accept exactly the type declared.
                try:
                    prnt('  { %s = &p->%s; (void)tmp; }' % (
                        ftype.get_c_name('*tmp', 'field %r'%fname, quals=fqual),
                        fname))
                except VerificationError as e:
                    prnt('  /* %s */' % str(e))   # cannot verify it, ignore
        prnt('}')
        prnt('static PyObject *')
        prnt('%s(PyObject *self, PyObject *noarg)' % (layoutfuncname,))
        prnt('{')
        prnt('  struct _cffi_aligncheck { char x; %s y; };' % cname)
        prnt('  static Py_ssize_t nums[] = {')
        prnt('    sizeof(%s),' % cname)
        prnt('    offsetof(struct _cffi_aligncheck, y),')
        for fname, ftype, fbitsize, fqual in tp.enumfields():
            if fbitsize >= 0:
                continue      # xxx ignore fbitsize for now
            prnt('    offsetof(%s, %s),' % (cname, fname))
            if isinstance(ftype, model.ArrayType) and ftype.length is None:
                prnt('    0,  /* %s */' % ftype._get_c_name())
            else:
                prnt('    sizeof(((%s *)0)->%s),' % (cname, fname))
        prnt('    -1')
        prnt('  };')
        prnt('  (void)self; /* unused */')
        prnt('  (void)noarg; /* unused */')
        prnt('  return _cffi_get_struct_layout(nums);')
        prnt('  /* the next line is not executed, but compiled */')
        prnt('  %s(0);' % (checkfuncname,))
        prnt('}')
        prnt()

    def _generate_struct_or_union_method(self, tp, prefix, name):
        if tp.fldnames is None:
            return     # nothing to do with opaque structs
        layoutfuncname = '_cffi_layout_%s_%s' % (prefix, name)
        self._prnt('  {"%s", %s, METH_NOARGS, NULL},' % (layoutfuncname,
                                                         layoutfuncname))

    def _loading_struct_or_union(self, tp, prefix, name, module):
        if tp.fldnames is None:
            return     # nothing to do with opaque structs
        layoutfuncname = '_cffi_layout_%s_%s' % (prefix, name)
        #
        function = getattr(module, layoutfuncname)
        layout = function()
        if isinstance(tp, model.StructOrUnion) and tp.partial:
            # use the function()'s sizes and offsets to guide the
            # layout of the struct
            totalsize = layout[0]
            totalalignment = layout[1]
            fieldofs = layout[2::2]
            fieldsize = layout[3::2]
            tp.force_flatten()
            assert len(fieldofs) == len(fieldsize) == len(tp.fldnames)
            tp.fixedlayout = fieldofs, fieldsize, totalsize, totalalignment
        else:
            cname = ('%s %s' % (prefix, name)).strip()
            self._struct_pending_verification[tp] = layout, cname

    def _loaded_struct_or_union(self, tp):
        if tp.fldnames is None:
            return     # nothing to do with opaque structs
        self.ffi._get_cached_btype(tp)   # force 'fixedlayout' to be considered

        if tp in self._struct_pending_verification:
            # check that the layout sizes and offsets match the real ones
            def check(realvalue, expectedvalue, msg):
                if realvalue != expectedvalue:
                    raise VerificationError(
                        "%s (we have %d, but C compiler says %d)"
                        % (msg, expectedvalue, realvalue))
            ffi = self.ffi
            BStruct = ffi._get_cached_btype(tp)
            layout, cname = self._struct_pending_verification.pop(tp)
            check(layout[0], ffi.sizeof(BStruct), "wrong total size")
            check(layout[1], ffi.alignof(BStruct), "wrong total alignment")
            i = 2
            for fname, ftype, fbitsize, fqual in tp.enumfields():
                if fbitsize >= 0:
                    continue        # xxx ignore fbitsize for now
                check(layout[i], ffi.offsetof(BStruct, fname),
                      "wrong offset for field %r" % (fname,))
                if layout[i+1] != 0:
                    BField = ffi._get_cached_btype(ftype)
                    check(layout[i+1], ffi.sizeof(BField),
                          "wrong size for field %r" % (fname,))
                i += 2
            assert i == len(layout)

    # ----------
    # 'anonymous' declarations.  These are produced for anonymous structs
    # or unions; the 'name' is obtained by a typedef.

    _generate_cpy_anonymous_collecttype = _generate_nothing

    def _generate_cpy_anonymous_decl(self, tp, name):
        if isinstance(tp, model.EnumType):
            self._generate_cpy_enum_decl(tp, name, '')
        else:
            self._generate_struct_or_union_decl(tp, '', name)

    def _generate_cpy_anonymous_method(self, tp, name):
        if not isinstance(tp, model.EnumType):
            self._generate_struct_or_union_method(tp, '', name)

    def _loading_cpy_anonymous(self, tp, name, module):
        if isinstance(tp, model.EnumType):
            self._loading_cpy_enum(tp, name, module)
        else:
            self._loading_struct_or_union(tp, '', name, module)

    def _loaded_cpy_anonymous(self, tp, name, module, **kwds):
        if isinstance(tp, model.EnumType):
            self._loaded_cpy_enum(tp, name, module, **kwds)
        else:
            self._loaded_struct_or_union(tp)

    # ----------
    # constants, likely declared with '#define'

    def _generate_cpy_const(self, is_int, name, tp=None, category='const',
                            vartp=None, delayed=True, size_too=False,
                            check_value=None):
        prnt = self._prnt
        funcname = '_cffi_%s_%s' % (category, name)
        prnt('static int %s(PyObject *lib)' % funcname)
        prnt('{')
        prnt('  PyObject *o;')
        prnt('  int res;')
        if not is_int:
            prnt('  %s;' % (vartp or tp).get_c_name(' i', name))
        else:
            assert category == 'const'
        #
        if check_value is not None:
            self._check_int_constant_value(name, check_value)
        #
        if not is_int:
            if category == 'var':
                realexpr = '&' + name
            else:
                realexpr = name
            prnt('  i = (%s);' % (realexpr,))
            prnt('  o = %s;' % (self._convert_expr_from_c(tp, 'i',
                                                          'variable type'),))
            assert delayed
        else:
            prnt('  o = _cffi_from_c_int_const(%s);' % name)
        prnt('  if (o == NULL)')
        prnt('    return -1;')
        if size_too:
            prnt('  {')
            prnt('    PyObject *o1 = o;')
            prnt('    o = Py_BuildValue("On", o1, (Py_ssize_t)sizeof(%s));'
                 % (name,))
            prnt('    Py_DECREF(o1);')
            prnt('    if (o == NULL)')
            prnt('      return -1;')
            prnt('  }')
        prnt('  res = PyObject_SetAttrString(lib, "%s", o);' % name)
        prnt('  Py_DECREF(o);')
        prnt('  if (res < 0)')
        prnt('    return -1;')
        prnt('  return %s;' % self._chained_list_constants[delayed])
        self._chained_list_constants[delayed] = funcname + '(lib)'
        prnt('}')
        prnt()

    def _generate_cpy_constant_collecttype(self, tp, name):
        is_int = isinstance(tp, model.PrimitiveType) and tp.is_integer_type()
        if not is_int:
            self._do_collect_type(tp)

    def _generate_cpy_constant_decl(self, tp, name):
        is_int = isinstance(tp, model.PrimitiveType) and tp.is_integer_type()
        self._generate_cpy_const(is_int, name, tp)

    _generate_cpy_constant_method = _generate_nothing
    _loading_cpy_constant = _loaded_noop
    _loaded_cpy_constant  = _loaded_noop

    # ----------
    # enums

    def _check_int_constant_value(self, name, value, err_prefix=''):
        prnt = self._prnt
        if value <= 0:
            prnt('  if ((%s) > 0 || (long)(%s) != %dL) {' % (
                name, name, value))
        else:
            prnt('  if ((%s) <= 0 || (unsigned long)(%s) != %dUL) {' % (
                name, name, value))
        prnt('    char buf[64];')
        prnt('    if ((%s) <= 0)' % name)
        prnt('        snprintf(buf, 63, "%%ld", (long)(%s));' % name)
        prnt('    else')
        prnt('        snprintf(buf, 63, "%%lu", (unsigned long)(%s));' %
             name)
        prnt('    PyErr_Format(_cffi_VerificationError,')
        prnt('                 "%s%s has the real value %s, not %s",')
        prnt('                 "%s", "%s", buf, "%d");' % (
            err_prefix, name, value))
        prnt('    return -1;')
        prnt('  }')

    def _enum_funcname(self, prefix, name):
        # "$enum_$1" => "___D_enum____D_1"
        name = name.replace('$', '___D_')
        return '_cffi_e_%s_%s' % (prefix, name)

    def _generate_cpy_enum_decl(self, tp, name, prefix='enum'):
        if tp.partial:
            for enumerator in tp.enumerators:
                self._generate_cpy_const(True, enumerator, delayed=False)
            return
        #
        funcname = self._enum_funcname(prefix, name)
        prnt = self._prnt
        prnt('static int %s(PyObject *lib)' % funcname)
        prnt('{')
        for enumerator, enumvalue in zip(tp.enumerators, tp.enumvalues):
            self._check_int_constant_value(enumerator, enumvalue,
                                           "enum %s: " % name)
        prnt('  return %s;' % self._chained_list_constants[True])
        self._chained_list_constants[True] = funcname + '(lib)'
        prnt('}')
        prnt()

    _generate_cpy_enum_collecttype = _generate_nothing
    _generate_cpy_enum_method = _generate_nothing

    def _loading_cpy_enum(self, tp, name, module):
        if tp.partial:
            enumvalues = [getattr(module, enumerator)
                          for enumerator in tp.enumerators]
            tp.enumvalues = tuple(enumvalues)
            tp.partial_resolved = True

    def _loaded_cpy_enum(self, tp, name, module, library):
        for enumerator, enumvalue in zip(tp.enumerators, tp.enumvalues):
            setattr(library, enumerator, enumvalue)

    # ----------
    # macros: for now only for integers

    def _generate_cpy_macro_decl(self, tp, name):
        if tp == '...':
            check_value = None
        else:
            check_value = tp     # an integer
        self._generate_cpy_const(True, name, check_value=check_value)

    _generate_cpy_macro_collecttype = _generate_nothing
    _generate_cpy_macro_method = _generate_nothing
    _loading_cpy_macro = _loaded_noop
    _loaded_cpy_macro  = _loaded_noop

    # ----------
    # global variables

    def _generate_cpy_variable_collecttype(self, tp, name):
        if isinstance(tp, model.ArrayType):
            tp_ptr = model.PointerType(tp.item)
        else:
            tp_ptr = model.PointerType(tp)
        self._do_collect_type(tp_ptr)

    def _generate_cpy_variable_decl(self, tp, name):
        if isinstance(tp, model.ArrayType):
            tp_ptr = model.PointerType(tp.item)
            self._generate_cpy_const(False, name, tp, vartp=tp_ptr,
                                     size_too = tp.length_is_unknown())
        else:
            tp_ptr = model.PointerType(tp)
            self._generate_cpy_const(False, name, tp_ptr, category='var')

    _generate_cpy_variable_method = _generate_nothing
    _loading_cpy_variable = _loaded_noop

    def _loaded_cpy_variable(self, tp, name, module, library):
        value = getattr(library, name)
        if isinstance(tp, model.ArrayType):   # int a[5] is "constant" in the
                                              # sense that "a=..." is forbidden
            if tp.length_is_unknown():
                assert isinstance(value, tuple)
                (value, size) = value
                BItemType = self.ffi._get_cached_btype(tp.item)
                length, rest = divmod(size, self.ffi.sizeof(BItemType))
                if rest != 0:
                    raise VerificationError(
                        "bad size: %r does not seem to be an array of %s" %
                        (name, tp.item))
                tp = tp.resolve_length(length)
            # 'value' is a <cdata 'type *'> which we have to replace with
            # a <cdata 'type[N]'> if the N is actually known
            if tp.length is not None:
                BArray = self.ffi._get_cached_btype(tp)
                value = self.ffi.cast(BArray, value)
                setattr(library, name, value)
            return
        # remove ptr=<cdata 'int *'> from the library instance, and replace
        # it by a property on the class, which reads/writes into ptr[0].
        ptr = value
        delattr(library, name)
        def getter(library):
            return ptr[0]
        def setter(library, value):
            ptr[0] = value
        setattr(type(library), name, property(getter, setter))
        type(library)._cffi_dir.append(name)

    # ----------

    def _generate_setup_custom(self):
        prnt = self._prnt
        prnt('static int _cffi_setup_custom(PyObject *lib)')
        prnt('{')
        prnt('  return %s;' % self._chained_list_constants[True])
        prnt('}')

cffimod_header = r'''
#include <Python.h>
#include <stddef.h>

/* this block of #ifs should be kept exactly identical between
   c/_cffi_backend.c, cffi/vengine_cpy.py, cffi/vengine_gen.py
   and cffi/_cffi_include.h */
#if defined(_MSC_VER)
# include <malloc.h>   /* for alloca() */
# if _MSC_VER < 1600   /* MSVC < 2010 */
   typedef __int8 int8_t;
   typedef __int16 int16_t;
   typedef __int32 int32_t;
   typedef __int64 int64_t;
   typedef unsigned __int8 uint8_t;
   typedef unsigned __int16 uint16_t;
   typedef unsigned __int32 uint32_t;
   typedef unsigned __int64 uint64_t;
   typedef __int8 int_least8_t;
   typedef __int16 int_least16_t;
   typedef __int32 int_least32_t;
   typedef __int64 int_least64_t;
   typedef unsigned __int8 uint_least8_t;
   typedef unsigned __int16 uint_least16_t;
   typedef unsigned __int32 uint_least32_t;
   typedef unsigned __int64 uint_least64_t;
   typedef __int8 int_fast8_t;
   typedef __int16 int_fast16_t;
   typedef __int32 int_fast32_t;
   typedef __int64 int_fast64_t;
   typedef unsigned __int8 uint_fast8_t;
   typedef unsigned __int16 uint_fast16_t;
   typedef unsigned __int32 uint_fast32_t;
   typedef unsigned __int64 uint_fast64_t;
   typedef __int64 intmax_t;
   typedef unsigned __int64 uintmax_t;
# else
#  include <stdint.h>
# endif
# if _MSC_VER < 1800   /* MSVC < 2013 */
#  ifndef __cplusplus
    typedef unsigned char _Bool;
#  endif
# endif
# define _cffi_float_complex_t   _Fcomplex    /* include <complex.h> for it */
# define _cffi_double_complex_t  _Dcomplex    /* include <complex.h> for it */
#else
# include <stdint.h>
# if (defined (__SVR4) && defined (__sun)) || defined(_AIX) || defined(__hpux)
#  include <alloca.h>
# endif
# define _cffi_float_complex_t   float _Complex
# define _cffi_double_complex_t  double _Complex
#endif

#if PY_MAJOR_VERSION < 3
# undef PyCapsule_CheckExact
# undef PyCapsule_GetPointer
# define PyCapsule_CheckExact(capsule) (PyCObject_Check(capsule))
# define PyCapsule_GetPointer(capsule, name) \
    (PyCObject_AsVoidPtr(capsule))
#endif

#if PY_MAJOR_VERSION >= 3
# define PyInt_FromLong PyLong_FromLong
#endif

#define _cffi_from_c_double PyFloat_FromDouble
#define _cffi_from_c_float PyFloat_FromDouble
#define _cffi_from_c_long PyInt_FromLong
#define _cffi_from_c_ulong PyLong_FromUnsignedLong
#define _cffi_from_c_longlong PyLong_FromLongLong
#define _cffi_from_c_ulonglong PyLong_FromUnsignedLongLong
#define _cffi_from_c__Bool PyBool_FromLong

#define _cffi_to_c_double PyFloat_AsDouble
#define _cffi_to_c_float PyFloat_AsDouble

#define _cffi_from_c_int_const(x)                                        \
    (((x) > 0) ?                                                         \
        ((unsigned long long)(x) <= (unsigned long long)LONG_MAX) ?      \
            PyInt_FromLong((long)(x)) :                                  \
            PyLong_FromUnsignedLongLong((unsigned long long)(x)) :       \
        ((long long)(x) >= (long long)LONG_MIN) ?                        \
            PyInt_FromLong((long)(x)) :                                  \
            PyLong_FromLongLong((long long)(x)))

#define _cffi_from_c_int(x, type)                                        \
    (((type)-1) > 0 ? /* unsigned */                                     \
        (sizeof(type) < sizeof(long) ?                                   \
            PyInt_FromLong((long)x) :                                    \
         sizeof(type) == sizeof(long) ?                                  \
            PyLong_FromUnsignedLong((unsigned long)x) :                  \
            PyLong_FromUnsignedLongLong((unsigned long long)x)) :        \
        (sizeof(type) <= sizeof(long) ?                                  \
            PyInt_FromLong((long)x) :                                    \
            PyLong_FromLongLong((long long)x)))

#define _cffi_to_c_int(o, type)                                          \
    ((type)(                                                             \
     sizeof(type) == 1 ? (((type)-1) > 0 ? (type)_cffi_to_c_u8(o)        \
                                         : (type)_cffi_to_c_i8(o)) :     \
     sizeof(type) == 2 ? (((type)-1) > 0 ? (type)_cffi_to_c_u16(o)       \
                                         : (type)_cffi_to_c_i16(o)) :    \
     sizeof(type) == 4 ? (((type)-1) > 0 ? (type)_cffi_to_c_u32(o)       \
                                         : (type)_cffi_to_c_i32(o)) :    \
     sizeof(type) == 8 ? (((type)-1) > 0 ? (type)_cffi_to_c_u64(o)       \
                                         : (type)_cffi_to_c_i64(o)) :    \
     (Py_FatalError("unsupported size for type " #type), (type)0)))

#define _cffi_to_c_i8                                                    \
                 ((int(*)(PyObject *))_cffi_exports[1])
#define _cffi_to_c_u8                                                    \
                 ((int(*)(PyObject *))_cffi_exports[2])
#define _cffi_to_c_i16                                                   \
                 ((int(*)(PyObject *))_cffi_exports[3])
#define _cffi_to_c_u16                                                   \
                 ((int(*)(PyObject *))_cffi_exports[4])
#define _cffi_to_c_i32                                                   \
                 ((int(*)(PyObject *))_cffi_exports[5])
#define _cffi_to_c_u32                                                   \
                 ((unsigned int(*)(PyObject *))_cffi_exports[6])
#define _cffi_to_c_i64                                                   \
                 ((long long(*)(PyObject *))_cffi_exports[7])
#define _cffi_to_c_u64                                                   \
                 ((unsigned long long(*)(PyObject *))_cffi_exports[8])
#define _cffi_to_c_char                                                  \
                 ((int(*)(PyObject *))_cffi_exports[9])
#define _cffi_from_c_pointer                                             \
    ((PyObject *(*)(char *, CTypeDescrObject *))_cffi_exports[10])
#define _cffi_to_c_pointer                                               \
    ((char *(*)(PyObject *, CTypeDescrObject *))_cffi_exports[11])
#define _cffi_get_struct_layout                                          \
    ((PyObject *(*)(Py_ssize_t[]))_cffi_exports[12])
#define _cffi_restore_errno                                              \
    ((void(*)(void))_cffi_exports[13])
#define _cffi_save_errno                                                 \
    ((void(*)(void))_cffi_exports[14])
#define _cffi_from_c_char                                                \
    ((PyObject *(*)(char))_cffi_exports[15])
#define _cffi_from_c_deref                                               \
    ((PyObject *(*)(char *, CTypeDescrObject *))_cffi_exports[16])
#define _cffi_to_c                                                       \
    ((int(*)(char *, CTypeDescrObject *, PyObject *))_cffi_exports[17])
#define _cffi_from_c_struct                                              \
    ((PyObject *(*)(char *, CTypeDescrObject *))_cffi_exports[18])
#define _cffi_to_c_wchar_t                                               \
    ((wchar_t(*)(PyObject *))_cffi_exports[19])
#define _cffi_from_c_wchar_t                                             \
    ((PyObject *(*)(wchar_t))_cffi_exports[20])
#define _cffi_to_c_long_double                                           \
    ((long double(*)(PyObject *))_cffi_exports[21])
#define _cffi_to_c__Bool                                                 \
    ((_Bool(*)(PyObject *))_cffi_exports[22])
#define _cffi_prepare_pointer_call_argument                              \
    ((Py_ssize_t(*)(CTypeDescrObject *, PyObject *, char **))_cffi_exports[23])
#define _cffi_convert_array_from_object                                  \
    ((int(*)(char *, CTypeDescrObject *, PyObject *))_cffi_exports[24])
#define _CFFI_NUM_EXPORTS 25

typedef struct _ctypedescr CTypeDescrObject;

static void *_cffi_exports[_CFFI_NUM_EXPORTS];
static PyObject *_cffi_types, *_cffi_VerificationError;

static int _cffi_setup_custom(PyObject *lib);   /* forward */

static PyObject *_cffi_setup(PyObject *self, PyObject *args)
{
    PyObject *library;
    int was_alive = (_cffi_types != NULL);
    (void)self; /* unused */
    if (!PyArg_ParseTuple(args, "OOO", &_cffi_types, &_cffi_VerificationError,
                                       &library))
        return NULL;
    Py_INCREF(_cffi_types);
    Py_INCREF(_cffi_VerificationError);
    if (_cffi_setup_custom(library) < 0)
        return NULL;
    return PyBool_FromLong(was_alive);
}

union _cffi_union_alignment_u {
    unsigned char m_char;
    unsigned short m_short;
    unsigned int m_int;
    unsigned long m_long;
    unsigned long long m_longlong;
    float m_float;
    double m_double;
    long double m_longdouble;
};

struct _cffi_freeme_s {
    struct _cffi_freeme_s *next;
    union _cffi_union_alignment_u alignment;
};

#ifdef __GNUC__
  __attribute__((unused))
#endif
static int _cffi_convert_array_argument(CTypeDescrObject *ctptr, PyObject *arg,
                                        char **output_data, Py_ssize_t datasize,
                                        struct _cffi_freeme_s **freeme)
{
    char *p;
    if (datasize < 0)
        return -1;

    p = *output_data;
    if (p == NULL) {
        struct _cffi_freeme_s *fp = (struct _cffi_freeme_s *)PyObject_Malloc(
            offsetof(struct _cffi_freeme_s, alignment) + (size_t)datasize);
        if (fp == NULL)
            return -1;
        fp->next = *freeme;
        *freeme = fp;
        p = *output_data = (char *)&fp->alignment;
    }
    memset((void *)p, 0, (size_t)datasize);
    return _cffi_convert_array_from_object(p, ctptr, arg);
}

#ifdef __GNUC__
  __attribute__((unused))
#endif
static void _cffi_free_array_arguments(struct _cffi_freeme_s *freeme)
{
    do {
        void *p = (void *)freeme;
        freeme = freeme->next;
        PyObject_Free(p);
    } while (freeme != NULL);
}

static int _cffi_init(void)
{
    PyObject *module, *c_api_object = NULL;

    module = PyImport_ImportModule("_cffi_backend");
    if (module == NULL)
        goto failure;

    c_api_object = PyObject_GetAttrString(module, "_C_API");
    if (c_api_object == NULL)
        goto failure;
    if (!PyCapsule_CheckExact(c_api_object)) {
        PyErr_SetNone(PyExc_ImportError);
        goto failure;
    }
    memcpy(_cffi_exports, PyCapsule_GetPointer(c_api_object, "cffi"),
           _CFFI_NUM_EXPORTS * sizeof(void *));

    Py_DECREF(module);
    Py_DECREF(c_api_object);
    return 0;

  failure:
    Py_XDECREF(module);
    Py_XDECREF(c_api_object);
    return -1;
}

#define _cffi_type(num) ((CTypeDescrObject *)PyList_GET_ITEM(_cffi_types, num))

/**********/
'''

# === NexusCore/openenv\Lib\site-packages\grpc\framework\interfaces\face\face.py ===
# Copyright 2015 gRPC authors.
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
"""Interfaces defining the Face layer of RPC Framework."""

import abc
import collections
import enum

# cardinality, style, abandonment, future, and stream are
# referenced from specification in this module.
from grpc.framework.common import cardinality  # pylint: disable=unused-import
from grpc.framework.common import style  # pylint: disable=unused-import
from grpc.framework.foundation import future  # pylint: disable=unused-import
from grpc.framework.foundation import stream  # pylint: disable=unused-import

# pylint: disable=too-many-arguments


class NoSuchMethodError(Exception):
    """Raised by customer code to indicate an unrecognized method.

    Attributes:
      group: The group of the unrecognized method.
      name: The name of the unrecognized method.
    """

    def __init__(self, group, method):
        """Constructor.

        Args:
          group: The group identifier of the unrecognized RPC name.
          method: The method identifier of the unrecognized RPC name.
        """
        super(NoSuchMethodError, self).__init__()
        self.group = group
        self.method = method

    def __repr__(self):
        return "face.NoSuchMethodError(%s, %s)" % (
            self.group,
            self.method,
        )


class Abortion(
    collections.namedtuple(
        "Abortion",
        (
            "kind",
            "initial_metadata",
            "terminal_metadata",
            "code",
            "details",
        ),
    )
):
    """A value describing RPC abortion.

    Attributes:
      kind: A Kind value identifying how the RPC failed.
      initial_metadata: The initial metadata from the other side of the RPC or
        None if no initial metadata value was received.
      terminal_metadata: The terminal metadata from the other side of the RPC or
        None if no terminal metadata value was received.
      code: The code value from the other side of the RPC or None if no code value
        was received.
      details: The details value from the other side of the RPC or None if no
        details value was received.
    """

    @enum.unique
    class Kind(enum.Enum):
        """Types of RPC abortion."""

        CANCELLED = "cancelled"
        EXPIRED = "expired"
        LOCAL_SHUTDOWN = "local shutdown"
        REMOTE_SHUTDOWN = "remote shutdown"
        NETWORK_FAILURE = "network failure"
        LOCAL_FAILURE = "local failure"
        REMOTE_FAILURE = "remote failure"


class AbortionError(Exception, metaclass=abc.ABCMeta):
    """Common super type for exceptions indicating RPC abortion.

    initial_metadata: The initial metadata from the other side of the RPC or
      None if no initial metadata value was received.
    terminal_metadata: The terminal metadata from the other side of the RPC or
      None if no terminal metadata value was received.
    code: The code value from the other side of the RPC or None if no code value
      was received.
    details: The details value from the other side of the RPC or None if no
      details value was received.
    """

    def __init__(self, initial_metadata, terminal_metadata, code, details):
        super(AbortionError, self).__init__()
        self.initial_metadata = initial_metadata
        self.terminal_metadata = terminal_metadata
        self.code = code
        self.details = details

    def __str__(self):
        return '%s(code=%s, details="%s")' % (
            self.__class__.__name__,
            self.code,
            self.details,
        )


class CancellationError(AbortionError):
    """Indicates that an RPC has been cancelled."""


class ExpirationError(AbortionError):
    """Indicates that an RPC has expired ("timed out")."""


class LocalShutdownError(AbortionError):
    """Indicates that an RPC has terminated due to local shutdown of RPCs."""


class RemoteShutdownError(AbortionError):
    """Indicates that an RPC has terminated due to remote shutdown of RPCs."""


class NetworkError(AbortionError):
    """Indicates that some error occurred on the network."""


class LocalError(AbortionError):
    """Indicates that an RPC has terminated due to a local defect."""


class RemoteError(AbortionError):
    """Indicates that an RPC has terminated due to a remote defect."""


class RpcContext(abc.ABC):
    """Provides RPC-related information and action."""

    @abc.abstractmethod
    def is_active(self):
        """Describes whether the RPC is active or has terminated."""
        raise NotImplementedError()

    @abc.abstractmethod
    def time_remaining(self):
        """Describes the length of allowed time remaining for the RPC.

        Returns:
          A nonnegative float indicating the length of allowed time in seconds
          remaining for the RPC to complete before it is considered to have timed
          out.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def add_abortion_callback(self, abortion_callback):
        """Registers a callback to be called if the RPC is aborted.

        Args:
          abortion_callback: A callable to be called and passed an Abortion value
            in the event of RPC abortion.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def cancel(self):
        """Cancels the RPC.

        Idempotent and has no effect if the RPC has already terminated.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def protocol_context(self):
        """Accesses a custom object specified by an implementation provider.

        Returns:
          A value specified by the provider of a Face interface implementation
            affording custom state and behavior.
        """
        raise NotImplementedError()


class Call(RpcContext, metaclass=abc.ABCMeta):
    """Invocation-side utility object for an RPC."""

    @abc.abstractmethod
    def initial_metadata(self):
        """Accesses the initial metadata from the service-side of the RPC.

        This method blocks until the value is available or is known not to have been
        emitted from the service-side of the RPC.

        Returns:
          The initial metadata object emitted by the service-side of the RPC, or
            None if there was no such value.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def terminal_metadata(self):
        """Accesses the terminal metadata from the service-side of the RPC.

        This method blocks until the value is available or is known not to have been
        emitted from the service-side of the RPC.

        Returns:
          The terminal metadata object emitted by the service-side of the RPC, or
            None if there was no such value.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def code(self):
        """Accesses the code emitted by the service-side of the RPC.

        This method blocks until the value is available or is known not to have been
        emitted from the service-side of the RPC.

        Returns:
          The code object emitted by the service-side of the RPC, or None if there
            was no such value.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def details(self):
        """Accesses the details value emitted by the service-side of the RPC.

        This method blocks until the value is available or is known not to have been
        emitted from the service-side of the RPC.

        Returns:
          The details value emitted by the service-side of the RPC, or None if there
            was no such value.
        """
        raise NotImplementedError()


class ServicerContext(RpcContext, metaclass=abc.ABCMeta):
    """A context object passed to method implementations."""

    @abc.abstractmethod
    def invocation_metadata(self):
        """Accesses the metadata from the invocation-side of the RPC.

        This method blocks until the value is available or is known not to have been
        emitted from the invocation-side of the RPC.

        Returns:
          The metadata object emitted by the invocation-side of the RPC, or None if
            there was no such value.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def initial_metadata(self, initial_metadata):
        """Accepts the service-side initial metadata value of the RPC.

        This method need not be called by method implementations if they have no
        service-side initial metadata to transmit.

        Args:
          initial_metadata: The service-side initial metadata value of the RPC to
            be transmitted to the invocation side of the RPC.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def terminal_metadata(self, terminal_metadata):
        """Accepts the service-side terminal metadata value of the RPC.

        This method need not be called by method implementations if they have no
        service-side terminal metadata to transmit.

        Args:
          terminal_metadata: The service-side terminal metadata value of the RPC to
            be transmitted to the invocation side of the RPC.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def code(self, code):
        """Accepts the service-side code of the RPC.

        This method need not be called by method implementations if they have no
        code to transmit.

        Args:
          code: The code of the RPC to be transmitted to the invocation side of the
            RPC.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def details(self, details):
        """Accepts the service-side details of the RPC.

        This method need not be called by method implementations if they have no
        service-side details to transmit.

        Args:
          details: The service-side details value of the RPC to be transmitted to
            the invocation side of the RPC.
        """
        raise NotImplementedError()


class ResponseReceiver(abc.ABC):
    """Invocation-side object used to accept the output of an RPC."""

    @abc.abstractmethod
    def initial_metadata(self, initial_metadata):
        """Receives the initial metadata from the service-side of the RPC.

        Args:
          initial_metadata: The initial metadata object emitted from the
            service-side of the RPC.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def response(self, response):
        """Receives a response from the service-side of the RPC.

        Args:
          response: A response object emitted from the service-side of the RPC.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def complete(self, terminal_metadata, code, details):
        """Receives the completion values emitted from the service-side of the RPC.

        Args:
          terminal_metadata: The terminal metadata object emitted from the
            service-side of the RPC.
          code: The code object emitted from the service-side of the RPC.
          details: The details object emitted from the service-side of the RPC.
        """
        raise NotImplementedError()


class UnaryUnaryMultiCallable(abc.ABC):
    """Affords invoking a unary-unary RPC in any call style."""

    @abc.abstractmethod
    def __call__(
        self,
        request,
        timeout,
        metadata=None,
        with_call=False,
        protocol_options=None,
    ):
        """Synchronously invokes the underlying RPC.

        Args:
          request: The request value for the RPC.
          timeout: A duration of time in seconds to allow for the RPC.
          metadata: A metadata value to be passed to the service-side of
            the RPC.
          with_call: Whether or not to include return a Call for the RPC in addition
            to the response.
          protocol_options: A value specified by the provider of a Face interface
            implementation affording custom state and behavior.

        Returns:
          The response value for the RPC, and a Call for the RPC if with_call was
            set to True at invocation.

        Raises:
          AbortionError: Indicating that the RPC was aborted.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def future(self, request, timeout, metadata=None, protocol_options=None):
        """Asynchronously invokes the underlying RPC.

        Args:
          request: The request value for the RPC.
          timeout: A duration of time in seconds to allow for the RPC.
          metadata: A metadata value to be passed to the service-side of
            the RPC.
          protocol_options: A value specified by the provider of a Face interface
            implementation affording custom state and behavior.

        Returns:
          An object that is both a Call for the RPC and a future.Future. In the
            event of RPC completion, the return Future's result value will be the
            response value of the RPC. In the event of RPC abortion, the returned
            Future's exception value will be an AbortionError.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def event(
        self,
        request,
        receiver,
        abortion_callback,
        timeout,
        metadata=None,
        protocol_options=None,
    ):
        """Asynchronously invokes the underlying RPC.

        Args:
          request: The request value for the RPC.
          receiver: A ResponseReceiver to be passed the response data of the RPC.
          abortion_callback: A callback to be called and passed an Abortion value
            in the event of RPC abortion.
          timeout: A duration of time in seconds to allow for the RPC.
          metadata: A metadata value to be passed to the service-side of
            the RPC.
          protocol_options: A value specified by the provider of a Face interface
            implementation affording custom state and behavior.

        Returns:
          A Call for the RPC.
        """
        raise NotImplementedError()


class UnaryStreamMultiCallable(abc.ABC):
    """Affords invoking a unary-stream RPC in any call style."""

    @abc.abstractmethod
    def __call__(self, request, timeout, metadata=None, protocol_options=None):
        """Invokes the underlying RPC.

        Args:
          request: The request value for the RPC.
          timeout: A duration of time in seconds to allow for the RPC.
          metadata: A metadata value to be passed to the service-side of
            the RPC.
          protocol_options: A value specified by the provider of a Face interface
            implementation affording custom state and behavior.

        Returns:
          An object that is both a Call for the RPC and an iterator of response
            values. Drawing response values from the returned iterator may raise
            AbortionError indicating abortion of the RPC.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def event(
        self,
        request,
        receiver,
        abortion_callback,
        timeout,
        metadata=None,
        protocol_options=None,
    ):
        """Asynchronously invokes the underlying RPC.

        Args:
          request: The request value for the RPC.
          receiver: A ResponseReceiver to be passed the response data of the RPC.
          abortion_callback: A callback to be called and passed an Abortion value
            in the event of RPC abortion.
          timeout: A duration of time in seconds to allow for the RPC.
          metadata: A metadata value to be passed to the service-side of
            the RPC.
          protocol_options: A value specified by the provider of a Face interface
            implementation affording custom state and behavior.

        Returns:
          A Call object for the RPC.
        """
        raise NotImplementedError()


class StreamUnaryMultiCallable(abc.ABC):
    """Affords invoking a stream-unary RPC in any call style."""

    @abc.abstractmethod
    def __call__(
        self,
        request_iterator,
        timeout,
        metadata=None,
        with_call=False,
        protocol_options=None,
    ):
        """Synchronously invokes the underlying RPC.

        Args:
          request_iterator: An iterator that yields request values for the RPC.
          timeout: A duration of time in seconds to allow for the RPC.
          metadata: A metadata value to be passed to the service-side of
            the RPC.
          with_call: Whether or not to include return a Call for the RPC in addition
            to the response.
          protocol_options: A value specified by the provider of a Face interface
            implementation affording custom state and behavior.

        Returns:
          The response value for the RPC, and a Call for the RPC if with_call was
            set to True at invocation.

        Raises:
          AbortionError: Indicating that the RPC was aborted.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def future(
        self, request_iterator, timeout, metadata=None, protocol_options=None
    ):
        """Asynchronously invokes the underlying RPC.

        Args:
          request_iterator: An iterator that yields request values for the RPC.
          timeout: A duration of time in seconds to allow for the RPC.
          metadata: A metadata value to be passed to the service-side of
            the RPC.
          protocol_options: A value specified by the provider of a Face interface
            implementation affording custom state and behavior.

        Returns:
          An object that is both a Call for the RPC and a future.Future. In the
            event of RPC completion, the return Future's result value will be the
            response value of the RPC. In the event of RPC abortion, the returned
            Future's exception value will be an AbortionError.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def event(
        self,
        receiver,
        abortion_callback,
        timeout,
        metadata=None,
        protocol_options=None,
    ):
        """Asynchronously invokes the underlying RPC.

        Args:
          receiver: A ResponseReceiver to be passed the response data of the RPC.
          abortion_callback: A callback to be called and passed an Abortion value
            in the event of RPC abortion.
          timeout: A duration of time in seconds to allow for the RPC.
          metadata: A metadata value to be passed to the service-side of
            the RPC.
          protocol_options: A value specified by the provider of a Face interface
            implementation affording custom state and behavior.

        Returns:
          A single object that is both a Call object for the RPC and a
            stream.Consumer to which the request values of the RPC should be passed.
        """
        raise NotImplementedError()


class StreamStreamMultiCallable(abc.ABC):
    """Affords invoking a stream-stream RPC in any call style."""

    @abc.abstractmethod
    def __call__(
        self, request_iterator, timeout, metadata=None, protocol_options=None
    ):
        """Invokes the underlying RPC.

        Args:
          request_iterator: An iterator that yields request values for the RPC.
          timeout: A duration of time in seconds to allow for the RPC.
          metadata: A metadata value to be passed to the service-side of
            the RPC.
          protocol_options: A value specified by the provider of a Face interface
            implementation affording custom state and behavior.

        Returns:
          An object that is both a Call for the RPC and an iterator of response
            values. Drawing response values from the returned iterator may raise
            AbortionError indicating abortion of the RPC.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def event(
        self,
        receiver,
        abortion_callback,
        timeout,
        metadata=None,
        protocol_options=None,
    ):
        """Asynchronously invokes the underlying RPC.

        Args:
          receiver: A ResponseReceiver to be passed the response data of the RPC.
          abortion_callback: A callback to be called and passed an Abortion value
            in the event of RPC abortion.
          timeout: A duration of time in seconds to allow for the RPC.
          metadata: A metadata value to be passed to the service-side of
            the RPC.
          protocol_options: A value specified by the provider of a Face interface
            implementation affording custom state and behavior.

        Returns:
          A single object that is both a Call object for the RPC and a
            stream.Consumer to which the request values of the RPC should be passed.
        """
        raise NotImplementedError()


class MethodImplementation(abc.ABC):
    """A sum type that describes a method implementation.

    Attributes:
      cardinality: A cardinality.Cardinality value.
      style: A style.Service value.
      unary_unary_inline: The implementation of the method as a callable value
        that takes a request value and a ServicerContext object and returns a
        response value. Only non-None if cardinality is
        cardinality.Cardinality.UNARY_UNARY and style is style.Service.INLINE.
      unary_stream_inline: The implementation of the method as a callable value
        that takes a request value and a ServicerContext object and returns an
        iterator of response values. Only non-None if cardinality is
        cardinality.Cardinality.UNARY_STREAM and style is style.Service.INLINE.
      stream_unary_inline: The implementation of the method as a callable value
        that takes an iterator of request values and a ServicerContext object and
        returns a response value. Only non-None if cardinality is
        cardinality.Cardinality.STREAM_UNARY and style is style.Service.INLINE.
      stream_stream_inline: The implementation of the method as a callable value
        that takes an iterator of request values and a ServicerContext object and
        returns an iterator of response values. Only non-None if cardinality is
        cardinality.Cardinality.STREAM_STREAM and style is style.Service.INLINE.
      unary_unary_event: The implementation of the method as a callable value that
        takes a request value, a response callback to which to pass the response
        value of the RPC, and a ServicerContext. Only non-None if cardinality is
        cardinality.Cardinality.UNARY_UNARY and style is style.Service.EVENT.
      unary_stream_event: The implementation of the method as a callable value
        that takes a request value, a stream.Consumer to which to pass the
        response values of the RPC, and a ServicerContext. Only non-None if
        cardinality is cardinality.Cardinality.UNARY_STREAM and style is
        style.Service.EVENT.
      stream_unary_event: The implementation of the method as a callable value
        that takes a response callback to which to pass the response value of the
        RPC and a ServicerContext and returns a stream.Consumer to which the
        request values of the RPC should be passed. Only non-None if cardinality
        is cardinality.Cardinality.STREAM_UNARY and style is style.Service.EVENT.
      stream_stream_event: The implementation of the method as a callable value
        that takes a stream.Consumer to which to pass the response values of the
        RPC and a ServicerContext and returns a stream.Consumer to which the
        request values of the RPC should be passed. Only non-None if cardinality
        is cardinality.Cardinality.STREAM_STREAM and style is
        style.Service.EVENT.
    """


class MultiMethodImplementation(abc.ABC):
    """A general type able to service many methods."""

    @abc.abstractmethod
    def service(self, group, method, response_consumer, context):
        """Services an RPC.

        Args:
          group: The group identifier of the RPC.
          method: The method identifier of the RPC.
          response_consumer: A stream.Consumer to be called to accept the response
            values of the RPC.
          context: a ServicerContext object.

        Returns:
          A stream.Consumer with which to accept the request values of the RPC. The
            consumer returned from this method may or may not be invoked to
            completion: in the case of RPC abortion, RPC Framework will simply stop
            passing values to this object. Implementations must not assume that this
            object will be called to completion of the request stream or even called
            at all.

        Raises:
          abandonment.Abandoned: May or may not be raised when the RPC has been
            aborted.
          NoSuchMethodError: If this MultiMethod does not recognize the given group
            and name for the RPC and is not able to service the RPC.
        """
        raise NotImplementedError()


class GenericStub(abc.ABC):
    """Affords RPC invocation via generic methods."""

    @abc.abstractmethod
    def blocking_unary_unary(
        self,
        group,
        method,
        request,
        timeout,
        metadata=None,
        with_call=False,
        protocol_options=None,
    ):
        """Invokes a unary-request-unary-response method.

        This method blocks until either returning the response value of the RPC
        (in the event of RPC completion) or raising an exception (in the event of
        RPC abortion).

        Args:
          group: The group identifier of the RPC.
          method: The method identifier of the RPC.
          request: The request value for the RPC.
          timeout: A duration of time in seconds to allow for the RPC.
          metadata: A metadata value to be passed to the service-side of the RPC.
          with_call: Whether or not to include return a Call for the RPC in addition
            to the response.
          protocol_options: A value specified by the provider of a Face interface
            implementation affording custom state and behavior.

        Returns:
          The response value for the RPC, and a Call for the RPC if with_call was
            set to True at invocation.

        Raises:
          AbortionError: Indicating that the RPC was aborted.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def future_unary_unary(
        self,
        group,
        method,
        request,
        timeout,
        metadata=None,
        protocol_options=None,
    ):
        """Invokes a unary-request-unary-response method.

        Args:
          group: The group identifier of the RPC.
          method: The method identifier of the RPC.
          request: The request value for the RPC.
          timeout: A duration of time in seconds to allow for the RPC.
          metadata: A metadata value to be passed to the service-side of the RPC.
          protocol_options: A value specified by the provider of a Face interface
            implementation affording custom state and behavior.

        Returns:
          An object that is both a Call for the RPC and a future.Future. In the
            event of RPC completion, the return Future's result value will be the
            response value of the RPC. In the event of RPC abortion, the returned
            Future's exception value will be an AbortionError.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def inline_unary_stream(
        self,
        group,
        method,
        request,
        timeout,
        metadata=None,
        protocol_options=None,
    ):
        """Invokes a unary-request-stream-response method.

        Args:
          group: The group identifier of the RPC.
          method: The method identifier of the RPC.
          request: The request value for the RPC.
          timeout: A duration of time in seconds to allow for the RPC.
          metadata: A metadata value to be passed to the service-side of the RPC.
          protocol_options: A value specified by the provider of a Face interface
            implementation affording custom state and behavior.

        Returns:
          An object that is both a Call for the RPC and an iterator of response
            values. Drawing response values from the returned iterator may raise
            AbortionError indicating abortion of the RPC.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def blocking_stream_unary(
        self,
        group,
        method,
        request_iterator,
        timeout,
        metadata=None,
        with_call=False,
        protocol_options=None,
    ):
        """Invokes a stream-request-unary-response method.

        This method blocks until either returning the response value of the RPC
        (in the event of RPC completion) or raising an exception (in the event of
        RPC abortion).

        Args:
          group: The group identifier of the RPC.
          method: The method identifier of the RPC.
          request_iterator: An iterator that yields request values for the RPC.
          timeout: A duration of time in seconds to allow for the RPC.
          metadata: A metadata value to be passed to the service-side of the RPC.
          with_call: Whether or not to include return a Call for the RPC in addition
            to the response.
          protocol_options: A value specified by the provider of a Face interface
            implementation affording custom state and behavior.

        Returns:
          The response value for the RPC, and a Call for the RPC if with_call was
            set to True at invocation.

        Raises:
          AbortionError: Indicating that the RPC was aborted.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def future_stream_unary(
        self,
        group,
        method,
        request_iterator,
        timeout,
        metadata=None,
        protocol_options=None,
    ):
        """Invokes a stream-request-unary-response method.

        Args:
          group: The group identifier of the RPC.
          method: The method identifier of the RPC.
          request_iterator: An iterator that yields request values for the RPC.
          timeout: A duration of time in seconds to allow for the RPC.
          metadata: A metadata value to be passed to the service-side of the RPC.
          protocol_options: A value specified by the provider of a Face interface
            implementation affording custom state and behavior.

        Returns:
          An object that is both a Call for the RPC and a future.Future. In the
            event of RPC completion, the return Future's result value will be the
            response value of the RPC. In the event of RPC abortion, the returned
            Future's exception value will be an AbortionError.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def inline_stream_stream(
        self,
        group,
        method,
        request_iterator,
        timeout,
        metadata=None,
        protocol_options=None,
    ):
        """Invokes a stream-request-stream-response method.

        Args:
          group: The group identifier of the RPC.
          method: The method identifier of the RPC.
          request_iterator: An iterator that yields request values for the RPC.
          timeout: A duration of time in seconds to allow for the RPC.
          metadata: A metadata value to be passed to the service-side of the RPC.
          protocol_options: A value specified by the provider of a Face interface
            implementation affording custom state and behavior.

        Returns:
          An object that is both a Call for the RPC and an iterator of response
            values. Drawing response values from the returned iterator may raise
            AbortionError indicating abortion of the RPC.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def event_unary_unary(
        self,
        group,
        method,
        request,
        receiver,
        abortion_callback,
        timeout,
        metadata=None,
        protocol_options=None,
    ):
        """Event-driven invocation of a unary-request-unary-response method.

        Args:
          group: The group identifier of the RPC.
          method: The method identifier of the RPC.
          request: The request value for the RPC.
          receiver: A ResponseReceiver to be passed the response data of the RPC.
          abortion_callback: A callback to be called and passed an Abortion value
            in the event of RPC abortion.
          timeout: A duration of time in seconds to allow for the RPC.
          metadata: A metadata value to be passed to the service-side of the RPC.
          protocol_options: A value specified by the provider of a Face interface
            implementation affording custom state and behavior.

        Returns:
          A Call for the RPC.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def event_unary_stream(
        self,
        group,
        method,
        request,
        receiver,
        abortion_callback,
        timeout,
        metadata=None,
        protocol_options=None,
    ):
        """Event-driven invocation of a unary-request-stream-response method.

        Args:
          group: The group identifier of the RPC.
          method: The method identifier of the RPC.
          request: The request value for the RPC.
          receiver: A ResponseReceiver to be passed the response data of the RPC.
          abortion_callback: A callback to be called and passed an Abortion value
            in the event of RPC abortion.
          timeout: A duration of time in seconds to allow for the RPC.
          metadata: A metadata value to be passed to the service-side of the RPC.
          protocol_options: A value specified by the provider of a Face interface
            implementation affording custom state and behavior.

        Returns:
          A Call for the RPC.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def event_stream_unary(
        self,
        group,
        method,
        receiver,
        abortion_callback,
        timeout,
        metadata=None,
        protocol_options=None,
    ):
        """Event-driven invocation of a unary-request-unary-response method.

        Args:
          group: The group identifier of the RPC.
          method: The method identifier of the RPC.
          receiver: A ResponseReceiver to be passed the response data of the RPC.
          abortion_callback: A callback to be called and passed an Abortion value
            in the event of RPC abortion.
          timeout: A duration of time in seconds to allow for the RPC.
          metadata: A metadata value to be passed to the service-side of the RPC.
          protocol_options: A value specified by the provider of a Face interface
            implementation affording custom state and behavior.

        Returns:
          A pair of a Call object for the RPC and a stream.Consumer to which the
            request values of the RPC should be passed.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def event_stream_stream(
        self,
        group,
        method,
        receiver,
        abortion_callback,
        timeout,
        metadata=None,
        protocol_options=None,
    ):
        """Event-driven invocation of a unary-request-stream-response method.

        Args:
          group: The group identifier of the RPC.
          method: The method identifier of the RPC.
          receiver: A ResponseReceiver to be passed the response data of the RPC.
          abortion_callback: A callback to be called and passed an Abortion value
            in the event of RPC abortion.
          timeout: A duration of time in seconds to allow for the RPC.
          metadata: A metadata value to be passed to the service-side of the RPC.
          protocol_options: A value specified by the provider of a Face interface
            implementation affording custom state and behavior.

        Returns:
          A pair of a Call object for the RPC and a stream.Consumer to which the
            request values of the RPC should be passed.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def unary_unary(self, group, method):
        """Creates a UnaryUnaryMultiCallable for a unary-unary method.

        Args:
          group: The group identifier of the RPC.
          method: The method identifier of the RPC.

        Returns:
          A UnaryUnaryMultiCallable value for the named unary-unary method.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def unary_stream(self, group, method):
        """Creates a UnaryStreamMultiCallable for a unary-stream method.

        Args:
          group: The group identifier of the RPC.
          method: The method identifier of the RPC.

        Returns:
          A UnaryStreamMultiCallable value for the name unary-stream method.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def stream_unary(self, group, method):
        """Creates a StreamUnaryMultiCallable for a stream-unary method.

        Args:
          group: The group identifier of the RPC.
          method: The method identifier of the RPC.

        Returns:
          A StreamUnaryMultiCallable value for the named stream-unary method.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def stream_stream(self, group, method):
        """Creates a StreamStreamMultiCallable for a stream-stream method.

        Args:
          group: The group identifier of the RPC.
          method: The method identifier of the RPC.

        Returns:
          A StreamStreamMultiCallable value for the named stream-stream method.
        """
        raise NotImplementedError()


class DynamicStub(abc.ABC):
    """Affords RPC invocation via attributes corresponding to afforded methods.

    Instances of this type may be scoped to a single group so that attribute
    access is unambiguous.

    Instances of this type respond to attribute access as follows: if the
    requested attribute is the name of a unary-unary method, the value of the
    attribute will be a UnaryUnaryMultiCallable with which to invoke an RPC; if
    the requested attribute is the name of a unary-stream method, the value of the
    attribute will be a UnaryStreamMultiCallable with which to invoke an RPC; if
    the requested attribute is the name of a stream-unary method, the value of the
    attribute will be a StreamUnaryMultiCallable with which to invoke an RPC; and
    if the requested attribute is the name of a stream-stream method, the value of
    the attribute will be a StreamStreamMultiCallable with which to invoke an RPC.
    """

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\importlib_metadata\__init__.py ===
from __future__ import annotations

import os
import re
import abc
import sys
import json
import zipp
import email
import types
import inspect
import pathlib
import operator
import textwrap
import functools
import itertools
import posixpath
import collections

from . import _meta
from .compat import py39, py311
from ._collections import FreezableDefaultDict, Pair
from ._compat import (
    NullFinder,
    install,
)
from ._functools import method_cache, pass_none
from ._itertools import always_iterable, unique_everseen
from ._meta import PackageMetadata, SimplePath

from contextlib import suppress
from importlib import import_module
from importlib.abc import MetaPathFinder
from itertools import starmap
from typing import Any, Iterable, List, Mapping, Match, Optional, Set, cast

__all__ = [
    'Distribution',
    'DistributionFinder',
    'PackageMetadata',
    'PackageNotFoundError',
    'distribution',
    'distributions',
    'entry_points',
    'files',
    'metadata',
    'packages_distributions',
    'requires',
    'version',
]


class PackageNotFoundError(ModuleNotFoundError):
    """The package was not found."""

    def __str__(self) -> str:
        return f"No package metadata was found for {self.name}"

    @property
    def name(self) -> str:  # type: ignore[override]
        (name,) = self.args
        return name


class Sectioned:
    """
    A simple entry point config parser for performance

    >>> for item in Sectioned.read(Sectioned._sample):
    ...     print(item)
    Pair(name='sec1', value='# comments ignored')
    Pair(name='sec1', value='a = 1')
    Pair(name='sec1', value='b = 2')
    Pair(name='sec2', value='a = 2')

    >>> res = Sectioned.section_pairs(Sectioned._sample)
    >>> item = next(res)
    >>> item.name
    'sec1'
    >>> item.value
    Pair(name='a', value='1')
    >>> item = next(res)
    >>> item.value
    Pair(name='b', value='2')
    >>> item = next(res)
    >>> item.name
    'sec2'
    >>> item.value
    Pair(name='a', value='2')
    >>> list(res)
    []
    """

    _sample = textwrap.dedent(
        """
        [sec1]
        # comments ignored
        a = 1
        b = 2

        [sec2]
        a = 2
        """
    ).lstrip()

    @classmethod
    def section_pairs(cls, text):
        return (
            section._replace(value=Pair.parse(section.value))
            for section in cls.read(text, filter_=cls.valid)
            if section.name is not None
        )

    @staticmethod
    def read(text, filter_=None):
        lines = filter(filter_, map(str.strip, text.splitlines()))
        name = None
        for value in lines:
            section_match = value.startswith('[') and value.endswith(']')
            if section_match:
                name = value.strip('[]')
                continue
            yield Pair(name, value)

    @staticmethod
    def valid(line: str):
        return line and not line.startswith('#')


class EntryPoint:
    """An entry point as defined by Python packaging conventions.

    See `the packaging docs on entry points
    <https://packaging.python.org/specifications/entry-points/>`_
    for more information.

    >>> ep = EntryPoint(
    ...     name=None, group=None, value='package.module:attr [extra1, extra2]')
    >>> ep.module
    'package.module'
    >>> ep.attr
    'attr'
    >>> ep.extras
    ['extra1', 'extra2']
    """

    pattern = re.compile(
        r'(?P<module>[\w.]+)\s*'
        r'(:\s*(?P<attr>[\w.]+)\s*)?'
        r'((?P<extras>\[.*\])\s*)?$'
    )
    """
    A regular expression describing the syntax for an entry point,
    which might look like:

        - module
        - package.module
        - package.module:attribute
        - package.module:object.attribute
        - package.module:attr [extra1, extra2]

    Other combinations are possible as well.

    The expression is lenient about whitespace around the ':',
    following the attr, and following any extras.
    """

    name: str
    value: str
    group: str

    dist: Optional[Distribution] = None

    def __init__(self, name: str, value: str, group: str) -> None:
        vars(self).update(name=name, value=value, group=group)

    def load(self) -> Any:
        """Load the entry point from its definition. If only a module
        is indicated by the value, return that module. Otherwise,
        return the named object.
        """
        match = cast(Match, self.pattern.match(self.value))
        module = import_module(match.group('module'))
        attrs = filter(None, (match.group('attr') or '').split('.'))
        return functools.reduce(getattr, attrs, module)

    @property
    def module(self) -> str:
        match = self.pattern.match(self.value)
        assert match is not None
        return match.group('module')

    @property
    def attr(self) -> str:
        match = self.pattern.match(self.value)
        assert match is not None
        return match.group('attr')

    @property
    def extras(self) -> List[str]:
        match = self.pattern.match(self.value)
        assert match is not None
        return re.findall(r'\w+', match.group('extras') or '')

    def _for(self, dist):
        vars(self).update(dist=dist)
        return self

    def matches(self, **params):
        """
        EntryPoint matches the given parameters.

        >>> ep = EntryPoint(group='foo', name='bar', value='bing:bong [extra1, extra2]')
        >>> ep.matches(group='foo')
        True
        >>> ep.matches(name='bar', value='bing:bong [extra1, extra2]')
        True
        >>> ep.matches(group='foo', name='other')
        False
        >>> ep.matches()
        True
        >>> ep.matches(extras=['extra1', 'extra2'])
        True
        >>> ep.matches(module='bing')
        True
        >>> ep.matches(attr='bong')
        True
        """
        attrs = (getattr(self, param) for param in params)
        return all(map(operator.eq, params.values(), attrs))

    def _key(self):
        return self.name, self.value, self.group

    def __lt__(self, other):
        return self._key() < other._key()

    def __eq__(self, other):
        return self._key() == other._key()

    def __setattr__(self, name, value):
        raise AttributeError("EntryPoint objects are immutable.")

    def __repr__(self):
        return (
            f'EntryPoint(name={self.name!r}, value={self.value!r}, '
            f'group={self.group!r})'
        )

    def __hash__(self) -> int:
        return hash(self._key())


class EntryPoints(tuple):
    """
    An immutable collection of selectable EntryPoint objects.
    """

    __slots__ = ()

    def __getitem__(self, name: str) -> EntryPoint:  # type: ignore[override]
        """
        Get the EntryPoint in self matching name.
        """
        try:
            return next(iter(self.select(name=name)))
        except StopIteration:
            raise KeyError(name)

    def __repr__(self):
        """
        Repr with classname and tuple constructor to
        signal that we deviate from regular tuple behavior.
        """
        return '%s(%r)' % (self.__class__.__name__, tuple(self))

    def select(self, **params) -> EntryPoints:
        """
        Select entry points from self that match the
        given parameters (typically group and/or name).
        """
        return EntryPoints(ep for ep in self if py39.ep_matches(ep, **params))

    @property
    def names(self) -> Set[str]:
        """
        Return the set of all names of all entry points.
        """
        return {ep.name for ep in self}

    @property
    def groups(self) -> Set[str]:
        """
        Return the set of all groups of all entry points.
        """
        return {ep.group for ep in self}

    @classmethod
    def _from_text_for(cls, text, dist):
        return cls(ep._for(dist) for ep in cls._from_text(text))

    @staticmethod
    def _from_text(text):
        return (
            EntryPoint(name=item.value.name, value=item.value.value, group=item.name)
            for item in Sectioned.section_pairs(text or '')
        )


class PackagePath(pathlib.PurePosixPath):
    """A reference to a path in a package"""

    hash: Optional[FileHash]
    size: int
    dist: Distribution

    def read_text(self, encoding: str = 'utf-8') -> str:  # type: ignore[override]
        return self.locate().read_text(encoding=encoding)

    def read_binary(self) -> bytes:
        return self.locate().read_bytes()

    def locate(self) -> SimplePath:
        """Return a path-like object for this path"""
        return self.dist.locate_file(self)


class FileHash:
    def __init__(self, spec: str) -> None:
        self.mode, _, self.value = spec.partition('=')

    def __repr__(self) -> str:
        return f'<FileHash mode: {self.mode} value: {self.value}>'


class Distribution(metaclass=abc.ABCMeta):
    """
    An abstract Python distribution package.

    Custom providers may derive from this class and define
    the abstract methods to provide a concrete implementation
    for their environment. Some providers may opt to override
    the default implementation of some properties to bypass
    the file-reading mechanism.
    """

    @abc.abstractmethod
    def read_text(self, filename) -> Optional[str]:
        """Attempt to load metadata file given by the name.

        Python distribution metadata is organized by blobs of text
        typically represented as "files" in the metadata directory
        (e.g. package-1.0.dist-info). These files include things
        like:

        - METADATA: The distribution metadata including fields
          like Name and Version and Description.
        - entry_points.txt: A series of entry points as defined in
          `the entry points spec <https://packaging.python.org/en/latest/specifications/entry-points/#file-format>`_.
        - RECORD: A record of files according to
          `this recording spec <https://packaging.python.org/en/latest/specifications/recording-installed-packages/#the-record-file>`_.

        A package may provide any set of files, including those
        not listed here or none at all.

        :param filename: The name of the file in the distribution info.
        :return: The text if found, otherwise None.
        """

    @abc.abstractmethod
    def locate_file(self, path: str | os.PathLike[str]) -> SimplePath:
        """
        Given a path to a file in this distribution, return a SimplePath
        to it.
        """

    @classmethod
    def from_name(cls, name: str) -> Distribution:
        """Return the Distribution for the given package name.

        :param name: The name of the distribution package to search for.
        :return: The Distribution instance (or subclass thereof) for the named
            package, if found.
        :raises PackageNotFoundError: When the named package's distribution
            metadata cannot be found.
        :raises ValueError: When an invalid value is supplied for name.
        """
        if not name:
            raise ValueError("A distribution name is required.")
        try:
            return next(iter(cls.discover(name=name)))
        except StopIteration:
            raise PackageNotFoundError(name)

    @classmethod
    def discover(
        cls, *, context: Optional[DistributionFinder.Context] = None, **kwargs
    ) -> Iterable[Distribution]:
        """Return an iterable of Distribution objects for all packages.

        Pass a ``context`` or pass keyword arguments for constructing
        a context.

        :context: A ``DistributionFinder.Context`` object.
        :return: Iterable of Distribution objects for packages matching
          the context.
        """
        if context and kwargs:
            raise ValueError("cannot accept context and kwargs")
        context = context or DistributionFinder.Context(**kwargs)
        return itertools.chain.from_iterable(
            resolver(context) for resolver in cls._discover_resolvers()
        )

    @staticmethod
    def at(path: str | os.PathLike[str]) -> Distribution:
        """Return a Distribution for the indicated metadata path.

        :param path: a string or path-like object
        :return: a concrete Distribution instance for the path
        """
        return PathDistribution(pathlib.Path(path))

    @staticmethod
    def _discover_resolvers():
        """Search the meta_path for resolvers (MetadataPathFinders)."""
        declared = (
            getattr(finder, 'find_distributions', None) for finder in sys.meta_path
        )
        return filter(None, declared)

    @property
    def metadata(self) -> _meta.PackageMetadata:
        """Return the parsed metadata for this Distribution.

        The returned object will have keys that name the various bits of
        metadata per the
        `Core metadata specifications <https://packaging.python.org/en/latest/specifications/core-metadata/#core-metadata>`_.

        Custom providers may provide the METADATA file or override this
        property.
        """
        # deferred for performance (python/cpython#109829)
        from . import _adapters

        opt_text = (
            self.read_text('METADATA')
            or self.read_text('PKG-INFO')
            # This last clause is here to support old egg-info files.  Its
            # effect is to just end up using the PathDistribution's self._path
            # (which points to the egg-info file) attribute unchanged.
            or self.read_text('')
        )
        text = cast(str, opt_text)
        return _adapters.Message(email.message_from_string(text))

    @property
    def name(self) -> str:
        """Return the 'Name' metadata for the distribution package."""
        return self.metadata['Name']

    @property
    def _normalized_name(self):
        """Return a normalized version of the name."""
        return Prepared.normalize(self.name)

    @property
    def version(self) -> str:
        """Return the 'Version' metadata for the distribution package."""
        return self.metadata['Version']

    @property
    def entry_points(self) -> EntryPoints:
        """
        Return EntryPoints for this distribution.

        Custom providers may provide the ``entry_points.txt`` file
        or override this property.
        """
        return EntryPoints._from_text_for(self.read_text('entry_points.txt'), self)

    @property
    def files(self) -> Optional[List[PackagePath]]:
        """Files in this distribution.

        :return: List of PackagePath for this distribution or None

        Result is `None` if the metadata file that enumerates files
        (i.e. RECORD for dist-info, or installed-files.txt or
        SOURCES.txt for egg-info) is missing.
        Result may be empty if the metadata exists but is empty.

        Custom providers are recommended to provide a "RECORD" file (in
        ``read_text``) or override this property to allow for callers to be
        able to resolve filenames provided by the package.
        """

        def make_file(name, hash=None, size_str=None):
            result = PackagePath(name)
            result.hash = FileHash(hash) if hash else None
            result.size = int(size_str) if size_str else None
            result.dist = self
            return result

        @pass_none
        def make_files(lines):
            # Delay csv import, since Distribution.files is not as widely used
            # as other parts of importlib.metadata
            import csv

            return starmap(make_file, csv.reader(lines))

        @pass_none
        def skip_missing_files(package_paths):
            return list(filter(lambda path: path.locate().exists(), package_paths))

        return skip_missing_files(
            make_files(
                self._read_files_distinfo()
                or self._read_files_egginfo_installed()
                or self._read_files_egginfo_sources()
            )
        )

    def _read_files_distinfo(self):
        """
        Read the lines of RECORD.
        """
        text = self.read_text('RECORD')
        return text and text.splitlines()

    def _read_files_egginfo_installed(self):
        """
        Read installed-files.txt and return lines in a similar
        CSV-parsable format as RECORD: each file must be placed
        relative to the site-packages directory and must also be
        quoted (since file names can contain literal commas).

        This file is written when the package is installed by pip,
        but it might not be written for other installation methods.
        Assume the file is accurate if it exists.
        """
        text = self.read_text('installed-files.txt')
        # Prepend the .egg-info/ subdir to the lines in this file.
        # But this subdir is only available from PathDistribution's
        # self._path.
        subdir = getattr(self, '_path', None)
        if not text or not subdir:
            return

        paths = (
            py311.relative_fix((subdir / name).resolve())
            .relative_to(self.locate_file('').resolve(), walk_up=True)
            .as_posix()
            for name in text.splitlines()
        )
        return map('"{}"'.format, paths)

    def _read_files_egginfo_sources(self):
        """
        Read SOURCES.txt and return lines in a similar CSV-parsable
        format as RECORD: each file name must be quoted (since it
        might contain literal commas).

        Note that SOURCES.txt is not a reliable source for what
        files are installed by a package. This file is generated
        for a source archive, and the files that are present
        there (e.g. setup.py) may not correctly reflect the files
        that are present after the package has been installed.
        """
        text = self.read_text('SOURCES.txt')
        return text and map('"{}"'.format, text.splitlines())

    @property
    def requires(self) -> Optional[List[str]]:
        """Generated requirements specified for this Distribution"""
        reqs = self._read_dist_info_reqs() or self._read_egg_info_reqs()
        return reqs and list(reqs)

    def _read_dist_info_reqs(self):
        return self.metadata.get_all('Requires-Dist')

    def _read_egg_info_reqs(self):
        source = self.read_text('requires.txt')
        return pass_none(self._deps_from_requires_text)(source)

    @classmethod
    def _deps_from_requires_text(cls, source):
        return cls._convert_egg_info_reqs_to_simple_reqs(Sectioned.read(source))

    @staticmethod
    def _convert_egg_info_reqs_to_simple_reqs(sections):
        """
        Historically, setuptools would solicit and store 'extra'
        requirements, including those with environment markers,
        in separate sections. More modern tools expect each
        dependency to be defined separately, with any relevant
        extras and environment markers attached directly to that
        requirement. This method converts the former to the
        latter. See _test_deps_from_requires_text for an example.
        """

        def make_condition(name):
            return name and f'extra == "{name}"'

        def quoted_marker(section):
            section = section or ''
            extra, sep, markers = section.partition(':')
            if extra and markers:
                markers = f'({markers})'
            conditions = list(filter(None, [markers, make_condition(extra)]))
            return '; ' + ' and '.join(conditions) if conditions else ''

        def url_req_space(req):
            """
            PEP 508 requires a space between the url_spec and the quoted_marker.
            Ref python/importlib_metadata#357.
            """
            # '@' is uniquely indicative of a url_req.
            return ' ' * ('@' in req)

        for section in sections:
            space = url_req_space(section.value)
            yield section.value + space + quoted_marker(section.name)

    @property
    def origin(self):
        return self._load_json('direct_url.json')

    def _load_json(self, filename):
        return pass_none(json.loads)(
            self.read_text(filename),
            object_hook=lambda data: types.SimpleNamespace(**data),
        )


class DistributionFinder(MetaPathFinder):
    """
    A MetaPathFinder capable of discovering installed distributions.

    Custom providers should implement this interface in order to
    supply metadata.
    """

    class Context:
        """
        Keyword arguments presented by the caller to
        ``distributions()`` or ``Distribution.discover()``
        to narrow the scope of a search for distributions
        in all DistributionFinders.

        Each DistributionFinder may expect any parameters
        and should attempt to honor the canonical
        parameters defined below when appropriate.

        This mechanism gives a custom provider a means to
        solicit additional details from the caller beyond
        "name" and "path" when searching distributions.
        For example, imagine a provider that exposes suites
        of packages in either a "public" or "private" ``realm``.
        A caller may wish to query only for distributions in
        a particular realm and could call
        ``distributions(realm="private")`` to signal to the
        custom provider to only include distributions from that
        realm.
        """

        name = None
        """
        Specific name for which a distribution finder should match.
        A name of ``None`` matches all distributions.
        """

        def __init__(self, **kwargs):
            vars(self).update(kwargs)

        @property
        def path(self) -> List[str]:
            """
            The sequence of directory path that a distribution finder
            should search.

            Typically refers to Python installed package paths such as
            "site-packages" directories and defaults to ``sys.path``.
            """
            return vars(self).get('path', sys.path)

    @abc.abstractmethod
    def find_distributions(self, context=Context()) -> Iterable[Distribution]:
        """
        Find distributions.

        Return an iterable of all Distribution instances capable of
        loading the metadata for packages matching the ``context``,
        a DistributionFinder.Context instance.
        """


class FastPath:
    """
    Micro-optimized class for searching a root for children.

    Root is a path on the file system that may contain metadata
    directories either as natural directories or within a zip file.

    >>> FastPath('').children()
    ['...']

    FastPath objects are cached and recycled for any given root.

    >>> FastPath('foobar') is FastPath('foobar')
    True
    """

    @functools.lru_cache()  # type: ignore
    def __new__(cls, root):
        return super().__new__(cls)

    def __init__(self, root):
        self.root = root

    def joinpath(self, child):
        return pathlib.Path(self.root, child)

    def children(self):
        with suppress(Exception):
            return os.listdir(self.root or '.')
        with suppress(Exception):
            return self.zip_children()
        return []

    def zip_children(self):
        zip_path = zipp.Path(self.root)
        names = zip_path.root.namelist()
        self.joinpath = zip_path.joinpath

        return dict.fromkeys(child.split(posixpath.sep, 1)[0] for child in names)

    def search(self, name):
        return self.lookup(self.mtime).search(name)

    @property
    def mtime(self):
        with suppress(OSError):
            return os.stat(self.root).st_mtime
        self.lookup.cache_clear()

    @method_cache
    def lookup(self, mtime):
        return Lookup(self)


class Lookup:
    """
    A micro-optimized class for searching a (fast) path for metadata.
    """

    def __init__(self, path: FastPath):
        """
        Calculate all of the children representing metadata.

        From the children in the path, calculate early all of the
        children that appear to represent metadata (infos) or legacy
        metadata (eggs).
        """

        base = os.path.basename(path.root).lower()
        base_is_egg = base.endswith(".egg")
        self.infos = FreezableDefaultDict(list)
        self.eggs = FreezableDefaultDict(list)

        for child in path.children():
            low = child.lower()
            if low.endswith((".dist-info", ".egg-info")):
                # rpartition is faster than splitext and suitable for this purpose.
                name = low.rpartition(".")[0].partition("-")[0]
                normalized = Prepared.normalize(name)
                self.infos[normalized].append(path.joinpath(child))
            elif base_is_egg and low == "egg-info":
                name = base.rpartition(".")[0].partition("-")[0]
                legacy_normalized = Prepared.legacy_normalize(name)
                self.eggs[legacy_normalized].append(path.joinpath(child))

        self.infos.freeze()
        self.eggs.freeze()

    def search(self, prepared: Prepared):
        """
        Yield all infos and eggs matching the Prepared query.
        """
        infos = (
            self.infos[prepared.normalized]
            if prepared
            else itertools.chain.from_iterable(self.infos.values())
        )
        eggs = (
            self.eggs[prepared.legacy_normalized]
            if prepared
            else itertools.chain.from_iterable(self.eggs.values())
        )
        return itertools.chain(infos, eggs)


class Prepared:
    """
    A prepared search query for metadata on a possibly-named package.

    Pre-calculates the normalization to prevent repeated operations.

    >>> none = Prepared(None)
    >>> none.normalized
    >>> none.legacy_normalized
    >>> bool(none)
    False
    >>> sample = Prepared('Sample__Pkg-name.foo')
    >>> sample.normalized
    'sample_pkg_name_foo'
    >>> sample.legacy_normalized
    'sample__pkg_name.foo'
    >>> bool(sample)
    True
    """

    normalized = None
    legacy_normalized = None

    def __init__(self, name: Optional[str]):
        self.name = name
        if name is None:
            return
        self.normalized = self.normalize(name)
        self.legacy_normalized = self.legacy_normalize(name)

    @staticmethod
    def normalize(name):
        """
        PEP 503 normalization plus dashes as underscores.
        """
        return re.sub(r"[-_.]+", "-", name).lower().replace('-', '_')

    @staticmethod
    def legacy_normalize(name):
        """
        Normalize the package name as found in the convention in
        older packaging tools versions and specs.
        """
        return name.lower().replace('-', '_')

    def __bool__(self):
        return bool(self.name)


@install
class MetadataPathFinder(NullFinder, DistributionFinder):
    """A degenerate finder for distribution packages on the file system.

    This finder supplies only a find_distributions() method for versions
    of Python that do not have a PathFinder find_distributions().
    """

    @classmethod
    def find_distributions(
        cls, context=DistributionFinder.Context()
    ) -> Iterable[PathDistribution]:
        """
        Find distributions.

        Return an iterable of all Distribution instances capable of
        loading the metadata for packages matching ``context.name``
        (or all names if ``None`` indicated) along the paths in the list
        of directories ``context.path``.
        """
        found = cls._search_paths(context.name, context.path)
        return map(PathDistribution, found)

    @classmethod
    def _search_paths(cls, name, paths):
        """Find metadata directories in paths heuristically."""
        prepared = Prepared(name)
        return itertools.chain.from_iterable(
            path.search(prepared) for path in map(FastPath, paths)
        )

    @classmethod
    def invalidate_caches(cls) -> None:
        FastPath.__new__.cache_clear()


class PathDistribution(Distribution):
    def __init__(self, path: SimplePath) -> None:
        """Construct a distribution.

        :param path: SimplePath indicating the metadata directory.
        """
        self._path = path

    def read_text(self, filename: str | os.PathLike[str]) -> Optional[str]:
        with suppress(
            FileNotFoundError,
            IsADirectoryError,
            KeyError,
            NotADirectoryError,
            PermissionError,
        ):
            return self._path.joinpath(filename).read_text(encoding='utf-8')

        return None

    read_text.__doc__ = Distribution.read_text.__doc__

    def locate_file(self, path: str | os.PathLike[str]) -> SimplePath:
        return self._path.parent / path

    @property
    def _normalized_name(self):
        """
        Performance optimization: where possible, resolve the
        normalized name from the file system path.
        """
        stem = os.path.basename(str(self._path))
        return (
            pass_none(Prepared.normalize)(self._name_from_stem(stem))
            or super()._normalized_name
        )

    @staticmethod
    def _name_from_stem(stem):
        """
        >>> PathDistribution._name_from_stem('foo-3.0.egg-info')
        'foo'
        >>> PathDistribution._name_from_stem('CherryPy-3.0.dist-info')
        'CherryPy'
        >>> PathDistribution._name_from_stem('face.egg-info')
        'face'
        >>> PathDistribution._name_from_stem('foo.bar')
        """
        filename, ext = os.path.splitext(stem)
        if ext not in ('.dist-info', '.egg-info'):
            return
        name, sep, rest = filename.partition('-')
        return name


def distribution(distribution_name: str) -> Distribution:
    """Get the ``Distribution`` instance for the named package.

    :param distribution_name: The name of the distribution package as a string.
    :return: A ``Distribution`` instance (or subclass thereof).
    """
    return Distribution.from_name(distribution_name)


def distributions(**kwargs) -> Iterable[Distribution]:
    """Get all ``Distribution`` instances in the current environment.

    :return: An iterable of ``Distribution`` instances.
    """
    return Distribution.discover(**kwargs)


def metadata(distribution_name: str) -> _meta.PackageMetadata:
    """Get the metadata for the named package.

    :param distribution_name: The name of the distribution package to query.
    :return: A PackageMetadata containing the parsed metadata.
    """
    return Distribution.from_name(distribution_name).metadata


def version(distribution_name: str) -> str:
    """Get the version string for the named package.

    :param distribution_name: The name of the distribution package to query.
    :return: The version string for the package as defined in the package's
        "Version" metadata key.
    """
    return distribution(distribution_name).version


_unique = functools.partial(
    unique_everseen,
    key=py39.normalized_name,
)
"""
Wrapper for ``distributions`` to return unique distributions by name.
"""


def entry_points(**params) -> EntryPoints:
    """Return EntryPoint objects for all installed packages.

    Pass selection parameters (group or name) to filter the
    result to entry points matching those properties (see
    EntryPoints.select()).

    :return: EntryPoints for all installed packages.
    """
    eps = itertools.chain.from_iterable(
        dist.entry_points for dist in _unique(distributions())
    )
    return EntryPoints(eps).select(**params)


def files(distribution_name: str) -> Optional[List[PackagePath]]:
    """Return a list of files for the named package.

    :param distribution_name: The name of the distribution package to query.
    :return: List of files composing the distribution.
    """
    return distribution(distribution_name).files


def requires(distribution_name: str) -> Optional[List[str]]:
    """
    Return a list of requirements for the named package.

    :return: An iterable of requirements, suitable for
        packaging.requirement.Requirement.
    """
    return distribution(distribution_name).requires


def packages_distributions() -> Mapping[str, List[str]]:
    """
    Return a mapping of top-level packages to their
    distributions.

    >>> import collections.abc
    >>> pkgs = packages_distributions()
    >>> all(isinstance(dist, collections.abc.Sequence) for dist in pkgs.values())
    True
    """
    pkg_to_dist = collections.defaultdict(list)
    for dist in distributions():
        for pkg in _top_level_declared(dist) or _top_level_inferred(dist):
            pkg_to_dist[pkg].append(dist.metadata['Name'])
    return dict(pkg_to_dist)


def _top_level_declared(dist):
    return (dist.read_text('top_level.txt') or '').split()


def _topmost(name: PackagePath) -> Optional[str]:
    """
    Return the top-most parent as long as there is a parent.
    """
    top, *rest = name.parts
    return top if rest else None


def _get_toplevel_name(name: PackagePath) -> str:
    """
    Infer a possibly importable module name from a name presumed on
    sys.path.

    >>> _get_toplevel_name(PackagePath('foo.py'))
    'foo'
    >>> _get_toplevel_name(PackagePath('foo'))
    'foo'
    >>> _get_toplevel_name(PackagePath('foo.pyc'))
    'foo'
    >>> _get_toplevel_name(PackagePath('foo/__init__.py'))
    'foo'
    >>> _get_toplevel_name(PackagePath('foo.pth'))
    'foo.pth'
    >>> _get_toplevel_name(PackagePath('foo.dist-info'))
    'foo.dist-info'
    """
    return _topmost(name) or (
        # python/typeshed#10328
        inspect.getmodulename(name)  # type: ignore
        or str(name)
    )


def _top_level_inferred(dist):
    opt_names = set(map(_get_toplevel_name, always_iterable(dist.files)))

    def importable_name(name):
        return '.' not in name

    return filter(importable_name, opt_names)

# === NexusCore/openenv\Lib\site-packages\typer\main.py ===
import inspect
import os
import sys
import traceback
from datetime import datetime
from enum import Enum
from functools import update_wrapper
from pathlib import Path
from traceback import FrameSummary, StackSummary
from types import TracebackType
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Type, Union
from uuid import UUID

import click

from ._typing import get_args, get_origin, is_union
from .completion import get_completion_inspect_parameters
from .core import (
    DEFAULT_MARKUP_MODE,
    MarkupMode,
    TyperArgument,
    TyperCommand,
    TyperGroup,
    TyperOption,
)
from .models import (
    AnyType,
    ArgumentInfo,
    CommandFunctionType,
    CommandInfo,
    Default,
    DefaultPlaceholder,
    DeveloperExceptionConfig,
    FileBinaryRead,
    FileBinaryWrite,
    FileText,
    FileTextWrite,
    NoneType,
    OptionInfo,
    ParameterInfo,
    ParamMeta,
    Required,
    TyperInfo,
)
from .utils import get_params_from_function

try:
    import rich
    from rich.traceback import Traceback

    from . import rich_utils

    console_stderr = rich_utils._get_rich_console(stderr=True)

except ImportError:  # pragma: no cover
    rich = None  # type: ignore

_original_except_hook = sys.excepthook
_typer_developer_exception_attr_name = "__typer_developer_exception__"


def except_hook(
    exc_type: Type[BaseException], exc_value: BaseException, tb: Optional[TracebackType]
) -> None:
    exception_config: Union[DeveloperExceptionConfig, None] = getattr(
        exc_value, _typer_developer_exception_attr_name, None
    )
    standard_traceback = os.getenv("_TYPER_STANDARD_TRACEBACK")
    if (
        standard_traceback
        or not exception_config
        or not exception_config.pretty_exceptions_enable
    ):
        _original_except_hook(exc_type, exc_value, tb)
        return
    typer_path = os.path.dirname(__file__)
    click_path = os.path.dirname(click.__file__)
    supress_internal_dir_names = [typer_path, click_path]
    exc = exc_value
    if rich:
        from .rich_utils import MAX_WIDTH

        rich_tb = Traceback.from_exception(
            type(exc),
            exc,
            exc.__traceback__,
            show_locals=exception_config.pretty_exceptions_show_locals,
            suppress=supress_internal_dir_names,
            width=MAX_WIDTH,
        )
        console_stderr.print(rich_tb)
        return
    tb_exc = traceback.TracebackException.from_exception(exc)
    stack: List[FrameSummary] = []
    for frame in tb_exc.stack:
        if any(frame.filename.startswith(path) for path in supress_internal_dir_names):
            if not exception_config.pretty_exceptions_short:
                # Hide the line for internal libraries, Typer and Click
                stack.append(
                    traceback.FrameSummary(
                        filename=frame.filename,
                        lineno=frame.lineno,
                        name=frame.name,
                        line="",
                    )
                )
        else:
            stack.append(frame)
    # Type ignore ref: https://github.com/python/typeshed/pull/8244
    final_stack_summary = StackSummary.from_list(stack)
    tb_exc.stack = final_stack_summary
    for line in tb_exc.format():
        print(line, file=sys.stderr)
    return


def get_install_completion_arguments() -> Tuple[click.Parameter, click.Parameter]:
    install_param, show_param = get_completion_inspect_parameters()
    click_install_param, _ = get_click_param(install_param)
    click_show_param, _ = get_click_param(show_param)
    return click_install_param, click_show_param


class Typer:
    def __init__(
        self,
        *,
        name: Optional[str] = Default(None),
        cls: Optional[Type[TyperGroup]] = Default(None),
        invoke_without_command: bool = Default(False),
        no_args_is_help: bool = Default(False),
        subcommand_metavar: Optional[str] = Default(None),
        chain: bool = Default(False),
        result_callback: Optional[Callable[..., Any]] = Default(None),
        # Command
        context_settings: Optional[Dict[Any, Any]] = Default(None),
        callback: Optional[Callable[..., Any]] = Default(None),
        help: Optional[str] = Default(None),
        epilog: Optional[str] = Default(None),
        short_help: Optional[str] = Default(None),
        options_metavar: str = Default("[OPTIONS]"),
        add_help_option: bool = Default(True),
        hidden: bool = Default(False),
        deprecated: bool = Default(False),
        add_completion: bool = True,
        # Rich settings
        rich_markup_mode: MarkupMode = Default(DEFAULT_MARKUP_MODE),
        rich_help_panel: Union[str, None] = Default(None),
        pretty_exceptions_enable: bool = True,
        pretty_exceptions_show_locals: bool = True,
        pretty_exceptions_short: bool = True,
    ):
        self._add_completion = add_completion
        self.rich_markup_mode: MarkupMode = rich_markup_mode
        self.rich_help_panel = rich_help_panel
        self.pretty_exceptions_enable = pretty_exceptions_enable
        self.pretty_exceptions_show_locals = pretty_exceptions_show_locals
        self.pretty_exceptions_short = pretty_exceptions_short
        self.info = TyperInfo(
            name=name,
            cls=cls,
            invoke_without_command=invoke_without_command,
            no_args_is_help=no_args_is_help,
            subcommand_metavar=subcommand_metavar,
            chain=chain,
            result_callback=result_callback,
            context_settings=context_settings,
            callback=callback,
            help=help,
            epilog=epilog,
            short_help=short_help,
            options_metavar=options_metavar,
            add_help_option=add_help_option,
            hidden=hidden,
            deprecated=deprecated,
        )
        self.registered_groups: List[TyperInfo] = []
        self.registered_commands: List[CommandInfo] = []
        self.registered_callback: Optional[TyperInfo] = None

    def callback(
        self,
        name: Optional[str] = Default(None),
        *,
        cls: Optional[Type[TyperGroup]] = Default(None),
        invoke_without_command: bool = Default(False),
        no_args_is_help: bool = Default(False),
        subcommand_metavar: Optional[str] = Default(None),
        chain: bool = Default(False),
        result_callback: Optional[Callable[..., Any]] = Default(None),
        # Command
        context_settings: Optional[Dict[Any, Any]] = Default(None),
        help: Optional[str] = Default(None),
        epilog: Optional[str] = Default(None),
        short_help: Optional[str] = Default(None),
        options_metavar: str = Default("[OPTIONS]"),
        add_help_option: bool = Default(True),
        hidden: bool = Default(False),
        deprecated: bool = Default(False),
        # Rich settings
        rich_help_panel: Union[str, None] = Default(None),
    ) -> Callable[[CommandFunctionType], CommandFunctionType]:
        def decorator(f: CommandFunctionType) -> CommandFunctionType:
            self.registered_callback = TyperInfo(
                name=name,
                cls=cls,
                invoke_without_command=invoke_without_command,
                no_args_is_help=no_args_is_help,
                subcommand_metavar=subcommand_metavar,
                chain=chain,
                result_callback=result_callback,
                context_settings=context_settings,
                callback=f,
                help=help,
                epilog=epilog,
                short_help=short_help,
                options_metavar=options_metavar,
                add_help_option=add_help_option,
                hidden=hidden,
                deprecated=deprecated,
                rich_help_panel=rich_help_panel,
            )
            return f

        return decorator

    def command(
        self,
        name: Optional[str] = None,
        *,
        cls: Optional[Type[TyperCommand]] = None,
        context_settings: Optional[Dict[Any, Any]] = None,
        help: Optional[str] = None,
        epilog: Optional[str] = None,
        short_help: Optional[str] = None,
        options_metavar: str = "[OPTIONS]",
        add_help_option: bool = True,
        no_args_is_help: bool = False,
        hidden: bool = False,
        deprecated: bool = False,
        # Rich settings
        rich_help_panel: Union[str, None] = Default(None),
    ) -> Callable[[CommandFunctionType], CommandFunctionType]:
        if cls is None:
            cls = TyperCommand

        def decorator(f: CommandFunctionType) -> CommandFunctionType:
            self.registered_commands.append(
                CommandInfo(
                    name=name,
                    cls=cls,
                    context_settings=context_settings,
                    callback=f,
                    help=help,
                    epilog=epilog,
                    short_help=short_help,
                    options_metavar=options_metavar,
                    add_help_option=add_help_option,
                    no_args_is_help=no_args_is_help,
                    hidden=hidden,
                    deprecated=deprecated,
                    # Rich settings
                    rich_help_panel=rich_help_panel,
                )
            )
            return f

        return decorator

    def add_typer(
        self,
        typer_instance: "Typer",
        *,
        name: Optional[str] = Default(None),
        cls: Optional[Type[TyperGroup]] = Default(None),
        invoke_without_command: bool = Default(False),
        no_args_is_help: bool = Default(False),
        subcommand_metavar: Optional[str] = Default(None),
        chain: bool = Default(False),
        result_callback: Optional[Callable[..., Any]] = Default(None),
        # Command
        context_settings: Optional[Dict[Any, Any]] = Default(None),
        callback: Optional[Callable[..., Any]] = Default(None),
        help: Optional[str] = Default(None),
        epilog: Optional[str] = Default(None),
        short_help: Optional[str] = Default(None),
        options_metavar: str = Default("[OPTIONS]"),
        add_help_option: bool = Default(True),
        hidden: bool = Default(False),
        deprecated: bool = Default(False),
        # Rich settings
        rich_help_panel: Union[str, None] = Default(None),
    ) -> None:
        self.registered_groups.append(
            TyperInfo(
                typer_instance,
                name=name,
                cls=cls,
                invoke_without_command=invoke_without_command,
                no_args_is_help=no_args_is_help,
                subcommand_metavar=subcommand_metavar,
                chain=chain,
                result_callback=result_callback,
                context_settings=context_settings,
                callback=callback,
                help=help,
                epilog=epilog,
                short_help=short_help,
                options_metavar=options_metavar,
                add_help_option=add_help_option,
                hidden=hidden,
                deprecated=deprecated,
                rich_help_panel=rich_help_panel,
            )
        )

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if sys.excepthook != except_hook:
            sys.excepthook = except_hook
        try:
            return get_command(self)(*args, **kwargs)
        except Exception as e:
            # Set a custom attribute to tell the hook to show nice exceptions for user
            # code. An alternative/first implementation was a custom exception with
            # raise custom_exc from e
            # but that means the last error shown is the custom exception, not the
            # actual error. This trick improves developer experience by showing the
            # actual error last.
            setattr(
                e,
                _typer_developer_exception_attr_name,
                DeveloperExceptionConfig(
                    pretty_exceptions_enable=self.pretty_exceptions_enable,
                    pretty_exceptions_show_locals=self.pretty_exceptions_show_locals,
                    pretty_exceptions_short=self.pretty_exceptions_short,
                ),
            )
            raise e


def get_group(typer_instance: Typer) -> TyperGroup:
    group = get_group_from_info(
        TyperInfo(typer_instance),
        pretty_exceptions_short=typer_instance.pretty_exceptions_short,
        rich_markup_mode=typer_instance.rich_markup_mode,
    )
    return group


def get_command(typer_instance: Typer) -> click.Command:
    if typer_instance._add_completion:
        click_install_param, click_show_param = get_install_completion_arguments()
    if (
        typer_instance.registered_callback
        or typer_instance.info.callback
        or typer_instance.registered_groups
        or len(typer_instance.registered_commands) > 1
    ):
        # Create a Group
        click_command: click.Command = get_group(typer_instance)
        if typer_instance._add_completion:
            click_command.params.append(click_install_param)
            click_command.params.append(click_show_param)
        return click_command
    elif len(typer_instance.registered_commands) == 1:
        # Create a single Command
        single_command = typer_instance.registered_commands[0]

        if not single_command.context_settings and not isinstance(
            typer_instance.info.context_settings, DefaultPlaceholder
        ):
            single_command.context_settings = typer_instance.info.context_settings

        click_command = get_command_from_info(
            single_command,
            pretty_exceptions_short=typer_instance.pretty_exceptions_short,
            rich_markup_mode=typer_instance.rich_markup_mode,
        )
        if typer_instance._add_completion:
            click_command.params.append(click_install_param)
            click_command.params.append(click_show_param)
        return click_command
    raise RuntimeError(
        "Could not get a command for this Typer instance"
    )  # pragma: no cover


def get_group_name(typer_info: TyperInfo) -> Optional[str]:
    if typer_info.callback:
        # Priority 1: Callback passed in app.add_typer()
        return get_command_name(typer_info.callback.__name__)
    if typer_info.typer_instance:
        registered_callback = typer_info.typer_instance.registered_callback
        if registered_callback:
            if registered_callback.callback:
                # Priority 2: Callback passed in @subapp.callback()
                return get_command_name(registered_callback.callback.__name__)
        if typer_info.typer_instance.info.callback:
            return get_command_name(typer_info.typer_instance.info.callback.__name__)
    return None


def solve_typer_info_help(typer_info: TyperInfo) -> str:
    # Priority 1: Explicit value was set in app.add_typer()
    if not isinstance(typer_info.help, DefaultPlaceholder):
        return inspect.cleandoc(typer_info.help or "")
    # Priority 2: Explicit value was set in sub_app.callback()
    try:
        callback_help = typer_info.typer_instance.registered_callback.help
        if not isinstance(callback_help, DefaultPlaceholder):
            return inspect.cleandoc(callback_help or "")
    except AttributeError:
        pass
    # Priority 3: Explicit value was set in sub_app = typer.Typer()
    try:
        instance_help = typer_info.typer_instance.info.help
        if not isinstance(instance_help, DefaultPlaceholder):
            return inspect.cleandoc(instance_help or "")
    except AttributeError:
        pass
    # Priority 4: Implicit inference from callback docstring in app.add_typer()
    if typer_info.callback:
        doc = inspect.getdoc(typer_info.callback)
        if doc:
            return doc
    # Priority 5: Implicit inference from callback docstring in @app.callback()
    try:
        callback = typer_info.typer_instance.registered_callback.callback
        if not isinstance(callback, DefaultPlaceholder):
            doc = inspect.getdoc(callback or "")
            if doc:
                return doc
    except AttributeError:
        pass
    # Priority 6: Implicit inference from callback docstring in typer.Typer()
    try:
        instance_callback = typer_info.typer_instance.info.callback
        if not isinstance(instance_callback, DefaultPlaceholder):
            doc = inspect.getdoc(instance_callback)
            if doc:
                return doc
    except AttributeError:
        pass
    # Value not set, use the default
    return typer_info.help.value


def solve_typer_info_defaults(typer_info: TyperInfo) -> TyperInfo:
    values: Dict[str, Any] = {}
    for name, value in typer_info.__dict__.items():
        # Priority 1: Value was set in app.add_typer()
        if not isinstance(value, DefaultPlaceholder):
            values[name] = value
            continue
        # Priority 2: Value was set in @subapp.callback()
        try:
            callback_value = getattr(
                typer_info.typer_instance.registered_callback,  # type: ignore
                name,
            )
            if not isinstance(callback_value, DefaultPlaceholder):
                values[name] = callback_value
                continue
        except AttributeError:
            pass
        # Priority 3: Value set in subapp = typer.Typer()
        try:
            instance_value = getattr(
                typer_info.typer_instance.info,  # type: ignore
                name,
            )
            if not isinstance(instance_value, DefaultPlaceholder):
                values[name] = instance_value
                continue
        except AttributeError:
            pass
        # Value not set, use the default
        values[name] = value.value
    if values["name"] is None:
        values["name"] = get_group_name(typer_info)
    values["help"] = solve_typer_info_help(typer_info)
    return TyperInfo(**values)


def get_group_from_info(
    group_info: TyperInfo,
    *,
    pretty_exceptions_short: bool,
    rich_markup_mode: MarkupMode,
) -> TyperGroup:
    assert (
        group_info.typer_instance
    ), "A Typer instance is needed to generate a Click Group"
    commands: Dict[str, click.Command] = {}
    for command_info in group_info.typer_instance.registered_commands:
        command = get_command_from_info(
            command_info=command_info,
            pretty_exceptions_short=pretty_exceptions_short,
            rich_markup_mode=rich_markup_mode,
        )
        if command.name:
            commands[command.name] = command
    for sub_group_info in group_info.typer_instance.registered_groups:
        sub_group = get_group_from_info(
            sub_group_info,
            pretty_exceptions_short=pretty_exceptions_short,
            rich_markup_mode=rich_markup_mode,
        )
        if sub_group.name:
            commands[sub_group.name] = sub_group
    solved_info = solve_typer_info_defaults(group_info)
    (
        params,
        convertors,
        context_param_name,
    ) = get_params_convertors_ctx_param_name_from_function(solved_info.callback)
    cls = solved_info.cls or TyperGroup
    assert issubclass(cls, TyperGroup), f"{cls} should be a subclass of {TyperGroup}"
    group = cls(
        name=solved_info.name or "",
        commands=commands,
        invoke_without_command=solved_info.invoke_without_command,
        no_args_is_help=solved_info.no_args_is_help,
        subcommand_metavar=solved_info.subcommand_metavar,
        chain=solved_info.chain,
        result_callback=solved_info.result_callback,
        context_settings=solved_info.context_settings,
        callback=get_callback(
            callback=solved_info.callback,
            params=params,
            convertors=convertors,
            context_param_name=context_param_name,
            pretty_exceptions_short=pretty_exceptions_short,
        ),
        params=params,
        help=solved_info.help,
        epilog=solved_info.epilog,
        short_help=solved_info.short_help,
        options_metavar=solved_info.options_metavar,
        add_help_option=solved_info.add_help_option,
        hidden=solved_info.hidden,
        deprecated=solved_info.deprecated,
        rich_markup_mode=rich_markup_mode,
        # Rich settings
        rich_help_panel=solved_info.rich_help_panel,
    )
    return group


def get_command_name(name: str) -> str:
    return name.lower().replace("_", "-")


def get_params_convertors_ctx_param_name_from_function(
    callback: Optional[Callable[..., Any]],
) -> Tuple[List[Union[click.Argument, click.Option]], Dict[str, Any], Optional[str]]:
    params = []
    convertors = {}
    context_param_name = None
    if callback:
        parameters = get_params_from_function(callback)
        for param_name, param in parameters.items():
            if lenient_issubclass(param.annotation, click.Context):
                context_param_name = param_name
                continue
            click_param, convertor = get_click_param(param)
            if convertor:
                convertors[param_name] = convertor
            params.append(click_param)
    return params, convertors, context_param_name


def get_command_from_info(
    command_info: CommandInfo,
    *,
    pretty_exceptions_short: bool,
    rich_markup_mode: MarkupMode,
) -> click.Command:
    assert command_info.callback, "A command must have a callback function"
    name = command_info.name or get_command_name(command_info.callback.__name__)
    use_help = command_info.help
    if use_help is None:
        use_help = inspect.getdoc(command_info.callback)
    else:
        use_help = inspect.cleandoc(use_help)
    (
        params,
        convertors,
        context_param_name,
    ) = get_params_convertors_ctx_param_name_from_function(command_info.callback)
    cls = command_info.cls or TyperCommand
    command = cls(
        name=name,
        context_settings=command_info.context_settings,
        callback=get_callback(
            callback=command_info.callback,
            params=params,
            convertors=convertors,
            context_param_name=context_param_name,
            pretty_exceptions_short=pretty_exceptions_short,
        ),
        params=params,  # type: ignore
        help=use_help,
        epilog=command_info.epilog,
        short_help=command_info.short_help,
        options_metavar=command_info.options_metavar,
        add_help_option=command_info.add_help_option,
        no_args_is_help=command_info.no_args_is_help,
        hidden=command_info.hidden,
        deprecated=command_info.deprecated,
        rich_markup_mode=rich_markup_mode,
        # Rich settings
        rich_help_panel=command_info.rich_help_panel,
    )
    return command


def determine_type_convertor(type_: Any) -> Optional[Callable[[Any], Any]]:
    convertor: Optional[Callable[[Any], Any]] = None
    if lenient_issubclass(type_, Path):
        convertor = param_path_convertor
    if lenient_issubclass(type_, Enum):
        convertor = generate_enum_convertor(type_)
    return convertor


def param_path_convertor(value: Optional[str] = None) -> Optional[Path]:
    if value is not None:
        return Path(value)
    return None


def generate_enum_convertor(enum: Type[Enum]) -> Callable[[Any], Any]:
    val_map = {str(val.value): val for val in enum}

    def convertor(value: Any) -> Any:
        if value is not None:
            val = str(value)
            if val in val_map:
                key = val_map[val]
                return enum(key)

    return convertor


def generate_list_convertor(
    convertor: Optional[Callable[[Any], Any]], default_value: Optional[Any]
) -> Callable[[Sequence[Any]], Optional[List[Any]]]:
    def internal_convertor(value: Sequence[Any]) -> Optional[List[Any]]:
        if default_value is None and len(value) == 0:
            return None
        return [convertor(v) if convertor else v for v in value]

    return internal_convertor


def generate_tuple_convertor(
    types: Sequence[Any],
) -> Callable[[Optional[Tuple[Any, ...]]], Optional[Tuple[Any, ...]]]:
    convertors = [determine_type_convertor(type_) for type_ in types]

    def internal_convertor(
        param_args: Optional[Tuple[Any, ...]],
    ) -> Optional[Tuple[Any, ...]]:
        if param_args is None:
            return None
        return tuple(
            convertor(arg) if convertor else arg
            for (convertor, arg) in zip(convertors, param_args)
        )

    return internal_convertor


def get_callback(
    *,
    callback: Optional[Callable[..., Any]] = None,
    params: Sequence[click.Parameter] = [],
    convertors: Optional[Dict[str, Callable[[str], Any]]] = None,
    context_param_name: Optional[str] = None,
    pretty_exceptions_short: bool,
) -> Optional[Callable[..., Any]]:
    use_convertors = convertors or {}
    if not callback:
        return None
    parameters = get_params_from_function(callback)
    use_params: Dict[str, Any] = {}
    for param_name in parameters:
        use_params[param_name] = None
    for param in params:
        if param.name:
            use_params[param.name] = param.default

    def wrapper(**kwargs: Any) -> Any:
        _rich_traceback_guard = pretty_exceptions_short  # noqa: F841
        for k, v in kwargs.items():
            if k in use_convertors:
                use_params[k] = use_convertors[k](v)
            else:
                use_params[k] = v
        if context_param_name:
            use_params[context_param_name] = click.get_current_context()
        return callback(**use_params)

    update_wrapper(wrapper, callback)
    return wrapper


def get_click_type(
    *, annotation: Any, parameter_info: ParameterInfo
) -> click.ParamType:
    if parameter_info.click_type is not None:
        return parameter_info.click_type

    elif parameter_info.parser is not None:
        return click.types.FuncParamType(parameter_info.parser)

    elif annotation == str:
        return click.STRING
    elif annotation == int:
        if parameter_info.min is not None or parameter_info.max is not None:
            min_ = None
            max_ = None
            if parameter_info.min is not None:
                min_ = int(parameter_info.min)
            if parameter_info.max is not None:
                max_ = int(parameter_info.max)
            return click.IntRange(min=min_, max=max_, clamp=parameter_info.clamp)
        else:
            return click.INT
    elif annotation == float:
        if parameter_info.min is not None or parameter_info.max is not None:
            return click.FloatRange(
                min=parameter_info.min,
                max=parameter_info.max,
                clamp=parameter_info.clamp,
            )
        else:
            return click.FLOAT
    elif annotation == bool:
        return click.BOOL
    elif annotation == UUID:
        return click.UUID
    elif annotation == datetime:
        return click.DateTime(formats=parameter_info.formats)
    elif (
        annotation == Path
        or parameter_info.allow_dash
        or parameter_info.path_type
        or parameter_info.resolve_path
    ):
        return click.Path(
            exists=parameter_info.exists,
            file_okay=parameter_info.file_okay,
            dir_okay=parameter_info.dir_okay,
            writable=parameter_info.writable,
            readable=parameter_info.readable,
            resolve_path=parameter_info.resolve_path,
            allow_dash=parameter_info.allow_dash,
            path_type=parameter_info.path_type,
        )
    elif lenient_issubclass(annotation, FileTextWrite):
        return click.File(
            mode=parameter_info.mode or "w",
            encoding=parameter_info.encoding,
            errors=parameter_info.errors,
            lazy=parameter_info.lazy,
            atomic=parameter_info.atomic,
        )
    elif lenient_issubclass(annotation, FileText):
        return click.File(
            mode=parameter_info.mode or "r",
            encoding=parameter_info.encoding,
            errors=parameter_info.errors,
            lazy=parameter_info.lazy,
            atomic=parameter_info.atomic,
        )
    elif lenient_issubclass(annotation, FileBinaryRead):
        return click.File(
            mode=parameter_info.mode or "rb",
            encoding=parameter_info.encoding,
            errors=parameter_info.errors,
            lazy=parameter_info.lazy,
            atomic=parameter_info.atomic,
        )
    elif lenient_issubclass(annotation, FileBinaryWrite):
        return click.File(
            mode=parameter_info.mode or "wb",
            encoding=parameter_info.encoding,
            errors=parameter_info.errors,
            lazy=parameter_info.lazy,
            atomic=parameter_info.atomic,
        )
    elif lenient_issubclass(annotation, Enum):
        return click.Choice(
            [item.value for item in annotation],
            case_sensitive=parameter_info.case_sensitive,
        )
    raise RuntimeError(f"Type not yet supported: {annotation}")  # pragma: no cover


def lenient_issubclass(
    cls: Any, class_or_tuple: Union[AnyType, Tuple[AnyType, ...]]
) -> bool:
    return isinstance(cls, type) and issubclass(cls, class_or_tuple)


def get_click_param(
    param: ParamMeta,
) -> Tuple[Union[click.Argument, click.Option], Any]:
    # First, find out what will be:
    # * ParamInfo (ArgumentInfo or OptionInfo)
    # * default_value
    # * required
    default_value = None
    required = False
    if isinstance(param.default, ParameterInfo):
        parameter_info = param.default
        if parameter_info.default == Required:
            required = True
        else:
            default_value = parameter_info.default
    elif param.default == Required or param.default == param.empty:
        required = True
        parameter_info = ArgumentInfo()
    else:
        default_value = param.default
        parameter_info = OptionInfo()
    annotation: Any
    if not param.annotation == param.empty:
        annotation = param.annotation
    else:
        annotation = str
    main_type = annotation
    is_list = False
    is_tuple = False
    parameter_type: Any = None
    is_flag = None
    origin = get_origin(main_type)

    if origin is not None:
        # Handle SomeType | None and Optional[SomeType]
        if is_union(origin):
            types = []
            for type_ in get_args(main_type):
                if type_ is NoneType:
                    continue
                types.append(type_)
            assert len(types) == 1, "Typer Currently doesn't support Union types"
            main_type = types[0]
            origin = get_origin(main_type)
        # Handle Tuples and Lists
        if lenient_issubclass(origin, List):
            main_type = get_args(main_type)[0]
            assert not get_origin(
                main_type
            ), "List types with complex sub-types are not currently supported"
            is_list = True
        elif lenient_issubclass(origin, Tuple):  # type: ignore
            types = []
            for type_ in get_args(main_type):
                assert not get_origin(
                    type_
                ), "Tuple types with complex sub-types are not currently supported"
                types.append(
                    get_click_type(annotation=type_, parameter_info=parameter_info)
                )
            parameter_type = tuple(types)
            is_tuple = True
    if parameter_type is None:
        parameter_type = get_click_type(
            annotation=main_type, parameter_info=parameter_info
        )
    convertor = determine_type_convertor(main_type)
    if is_list:
        convertor = generate_list_convertor(
            convertor=convertor, default_value=default_value
        )
    if is_tuple:
        convertor = generate_tuple_convertor(get_args(main_type))
    if isinstance(parameter_info, OptionInfo):
        if main_type is bool and parameter_info.is_flag is not False:
            is_flag = True
            # Click doesn't accept a flag of type bool, only None, and then it sets it
            # to bool internally
            parameter_type = None
        default_option_name = get_command_name(param.name)
        if is_flag:
            default_option_declaration = (
                f"--{default_option_name}/--no-{default_option_name}"
            )
        else:
            default_option_declaration = f"--{default_option_name}"
        param_decls = [param.name]
        if parameter_info.param_decls:
            param_decls.extend(parameter_info.param_decls)
        else:
            param_decls.append(default_option_declaration)
        return (
            TyperOption(
                # Option
                param_decls=param_decls,
                show_default=parameter_info.show_default,
                prompt=parameter_info.prompt,
                confirmation_prompt=parameter_info.confirmation_prompt,
                prompt_required=parameter_info.prompt_required,
                hide_input=parameter_info.hide_input,
                is_flag=is_flag,
                flag_value=parameter_info.flag_value,
                multiple=is_list,
                count=parameter_info.count,
                allow_from_autoenv=parameter_info.allow_from_autoenv,
                type=parameter_type,
                help=parameter_info.help,
                hidden=parameter_info.hidden,
                show_choices=parameter_info.show_choices,
                show_envvar=parameter_info.show_envvar,
                # Parameter
                required=required,
                default=default_value,
                callback=get_param_callback(
                    callback=parameter_info.callback, convertor=convertor
                ),
                metavar=parameter_info.metavar,
                expose_value=parameter_info.expose_value,
                is_eager=parameter_info.is_eager,
                envvar=parameter_info.envvar,
                shell_complete=parameter_info.shell_complete,
                autocompletion=get_param_completion(parameter_info.autocompletion),
                # Rich settings
                rich_help_panel=parameter_info.rich_help_panel,
            ),
            convertor,
        )
    elif isinstance(parameter_info, ArgumentInfo):
        param_decls = [param.name]
        nargs = None
        if is_list:
            nargs = -1
        return (
            TyperArgument(
                # Argument
                param_decls=param_decls,
                type=parameter_type,
                required=required,
                nargs=nargs,
                # TyperArgument
                show_default=parameter_info.show_default,
                show_choices=parameter_info.show_choices,
                show_envvar=parameter_info.show_envvar,
                help=parameter_info.help,
                hidden=parameter_info.hidden,
                # Parameter
                default=default_value,
                callback=get_param_callback(
                    callback=parameter_info.callback, convertor=convertor
                ),
                metavar=parameter_info.metavar,
                expose_value=parameter_info.expose_value,
                is_eager=parameter_info.is_eager,
                envvar=parameter_info.envvar,
                shell_complete=parameter_info.shell_complete,
                autocompletion=get_param_completion(parameter_info.autocompletion),
                # Rich settings
                rich_help_panel=parameter_info.rich_help_panel,
            ),
            convertor,
        )
    raise AssertionError("A click.Parameter should be returned")  # pragma: no cover


def get_param_callback(
    *,
    callback: Optional[Callable[..., Any]] = None,
    convertor: Optional[Callable[..., Any]] = None,
) -> Optional[Callable[..., Any]]:
    if not callback:
        return None
    parameters = get_params_from_function(callback)
    ctx_name = None
    click_param_name = None
    value_name = None
    untyped_names: List[str] = []
    for param_name, param_sig in parameters.items():
        if lenient_issubclass(param_sig.annotation, click.Context):
            ctx_name = param_name
        elif lenient_issubclass(param_sig.annotation, click.Parameter):
            click_param_name = param_name
        else:
            untyped_names.append(param_name)
    # Extract value param name first
    if untyped_names:
        value_name = untyped_names.pop()
    # If context and Click param were not typed (old/Click callback style) extract them
    if untyped_names:
        if ctx_name is None:
            ctx_name = untyped_names.pop(0)
        if click_param_name is None:
            if untyped_names:
                click_param_name = untyped_names.pop(0)
        if untyped_names:
            raise click.ClickException(
                "Too many CLI parameter callback function parameters"
            )

    def wrapper(ctx: click.Context, param: click.Parameter, value: Any) -> Any:
        use_params: Dict[str, Any] = {}
        if ctx_name:
            use_params[ctx_name] = ctx
        if click_param_name:
            use_params[click_param_name] = param
        if value_name:
            if convertor:
                use_value = convertor(value)
            else:
                use_value = value
            use_params[value_name] = use_value
        return callback(**use_params)

    update_wrapper(wrapper, callback)
    return wrapper


def get_param_completion(
    callback: Optional[Callable[..., Any]] = None,
) -> Optional[Callable[..., Any]]:
    if not callback:
        return None
    parameters = get_params_from_function(callback)
    ctx_name = None
    args_name = None
    incomplete_name = None
    unassigned_params = list(parameters.values())
    for param_sig in unassigned_params[:]:
        origin = get_origin(param_sig.annotation)
        if lenient_issubclass(param_sig.annotation, click.Context):
            ctx_name = param_sig.name
            unassigned_params.remove(param_sig)
        elif lenient_issubclass(origin, List):
            args_name = param_sig.name
            unassigned_params.remove(param_sig)
        elif lenient_issubclass(param_sig.annotation, str):
            incomplete_name = param_sig.name
            unassigned_params.remove(param_sig)
    # If there are still unassigned parameters (not typed), extract by name
    for param_sig in unassigned_params[:]:
        if ctx_name is None and param_sig.name == "ctx":
            ctx_name = param_sig.name
            unassigned_params.remove(param_sig)
        elif args_name is None and param_sig.name == "args":
            args_name = param_sig.name
            unassigned_params.remove(param_sig)
        elif incomplete_name is None and param_sig.name == "incomplete":
            incomplete_name = param_sig.name
            unassigned_params.remove(param_sig)
    # Extract value param name first
    if unassigned_params:
        show_params = " ".join([param.name for param in unassigned_params])
        raise click.ClickException(
            f"Invalid autocompletion callback parameters: {show_params}"
        )

    def wrapper(ctx: click.Context, args: List[str], incomplete: Optional[str]) -> Any:
        use_params: Dict[str, Any] = {}
        if ctx_name:
            use_params[ctx_name] = ctx
        if args_name:
            use_params[args_name] = args
        if incomplete_name:
            use_params[incomplete_name] = incomplete
        return callback(**use_params)

    update_wrapper(wrapper, callback)
    return wrapper


def run(function: Callable[..., Any]) -> None:
    app = Typer(add_completion=False)
    app.command()(function)
    app()

# === NexusCore/openenv\Lib\site-packages\matplotlib\backends\_backend_tk.py ===
import uuid
import weakref
from contextlib import contextmanager
import logging
import math
import os.path
import pathlib
import sys
import tkinter as tk
import tkinter.filedialog
import tkinter.font
import tkinter.messagebox
from tkinter.simpledialog import SimpleDialog

import numpy as np
from PIL import Image, ImageTk

import matplotlib as mpl
from matplotlib import _api, backend_tools, cbook, _c_internal_utils
from matplotlib.backend_bases import (
    _Backend, FigureCanvasBase, FigureManagerBase, NavigationToolbar2,
    TimerBase, ToolContainerBase, cursors, _Mode, MouseButton,
    CloseEvent, KeyEvent, LocationEvent, MouseEvent, ResizeEvent)
from matplotlib._pylab_helpers import Gcf
from . import _tkagg
from ._tkagg import TK_PHOTO_COMPOSITE_OVERLAY, TK_PHOTO_COMPOSITE_SET


_log = logging.getLogger(__name__)
cursord = {
    cursors.MOVE: "fleur",
    cursors.HAND: "hand2",
    cursors.POINTER: "arrow",
    cursors.SELECT_REGION: "crosshair",
    cursors.WAIT: "watch",
    cursors.RESIZE_HORIZONTAL: "sb_h_double_arrow",
    cursors.RESIZE_VERTICAL: "sb_v_double_arrow",
}


@contextmanager
def _restore_foreground_window_at_end():
    foreground = _c_internal_utils.Win32_GetForegroundWindow()
    try:
        yield
    finally:
        if foreground and mpl.rcParams['tk.window_focus']:
            _c_internal_utils.Win32_SetForegroundWindow(foreground)


_blit_args = {}
# Initialize to a non-empty string that is not a Tcl command
_blit_tcl_name = "mpl_blit_" + uuid.uuid4().hex


def _blit(argsid):
    """
    Thin wrapper to blit called via tkapp.call.

    *argsid* is a unique string identifier to fetch the correct arguments from
    the ``_blit_args`` dict, since arguments cannot be passed directly.
    """
    photoimage, data, offsets, bbox, comp_rule = _blit_args.pop(argsid)
    if not photoimage.tk.call("info", "commands", photoimage):
        return
    _tkagg.blit(photoimage.tk.interpaddr(), str(photoimage), data, comp_rule, offsets,
                bbox)


def blit(photoimage, aggimage, offsets, bbox=None):
    """
    Blit *aggimage* to *photoimage*.

    *offsets* is a tuple describing how to fill the ``offset`` field of the
    ``Tk_PhotoImageBlock`` struct: it should be (0, 1, 2, 3) for RGBA8888 data,
    (2, 1, 0, 3) for little-endian ARBG32 (i.e. GBRA8888) data and (1, 2, 3, 0)
    for big-endian ARGB32 (i.e. ARGB8888) data.

    If *bbox* is passed, it defines the region that gets blitted. That region
    will be composed with the previous data according to the alpha channel.
    Blitting will be clipped to pixels inside the canvas, including silently
    doing nothing if the *bbox* region is entirely outside the canvas.

    Tcl events must be dispatched to trigger a blit from a non-Tcl thread.
    """
    data = np.asarray(aggimage)
    height, width = data.shape[:2]
    if bbox is not None:
        (x1, y1), (x2, y2) = bbox.__array__()
        x1 = max(math.floor(x1), 0)
        x2 = min(math.ceil(x2), width)
        y1 = max(math.floor(y1), 0)
        y2 = min(math.ceil(y2), height)
        if (x1 > x2) or (y1 > y2):
            return
        bboxptr = (x1, x2, y1, y2)
        comp_rule = TK_PHOTO_COMPOSITE_OVERLAY
    else:
        bboxptr = (0, width, 0, height)
        comp_rule = TK_PHOTO_COMPOSITE_SET

    # NOTE: _tkagg.blit is thread unsafe and will crash the process if called
    # from a thread (GH#13293). Instead of blanking and blitting here,
    # use tkapp.call to post a cross-thread event if this function is called
    # from a non-Tcl thread.

    # tkapp.call coerces all arguments to strings, so to avoid string parsing
    # within _blit, pack up the arguments into a global data structure.
    args = photoimage, data, offsets, bboxptr, comp_rule
    # Need a unique key to avoid thread races.
    # Again, make the key a string to avoid string parsing in _blit.
    argsid = str(id(args))
    _blit_args[argsid] = args

    try:
        photoimage.tk.call(_blit_tcl_name, argsid)
    except tk.TclError as e:
        if "invalid command name" not in str(e):
            raise
        photoimage.tk.createcommand(_blit_tcl_name, _blit)
        photoimage.tk.call(_blit_tcl_name, argsid)


class TimerTk(TimerBase):
    """Subclass of `backend_bases.TimerBase` using Tk timer events."""

    def __init__(self, parent, *args, **kwargs):
        self._timer = None
        super().__init__(*args, **kwargs)
        self.parent = parent

    def _timer_start(self):
        self._timer_stop()
        self._timer = self.parent.after(self._interval, self._on_timer)

    def _timer_stop(self):
        if self._timer is not None:
            self.parent.after_cancel(self._timer)
        self._timer = None

    def _on_timer(self):
        super()._on_timer()
        # Tk after() is only a single shot, so we need to add code here to
        # reset the timer if we're not operating in single shot mode.  However,
        # if _timer is None, this means that _timer_stop has been called; so
        # don't recreate the timer in that case.
        if not self._single and self._timer:
            if self._interval > 0:
                self._timer = self.parent.after(self._interval, self._on_timer)
            else:
                # Edge case: Tcl after 0 *prepends* events to the queue
                # so a 0 interval does not allow any other events to run.
                # This incantation is cancellable and runs as fast as possible
                # while also allowing events and drawing every frame. GH#18236
                self._timer = self.parent.after_idle(
                    lambda: self.parent.after(self._interval, self._on_timer)
                )
        else:
            self._timer = None


class FigureCanvasTk(FigureCanvasBase):
    required_interactive_framework = "tk"
    manager_class = _api.classproperty(lambda cls: FigureManagerTk)

    def __init__(self, figure=None, master=None):
        super().__init__(figure)
        self._idle_draw_id = None
        self._event_loop_id = None
        w, h = self.get_width_height(physical=True)
        self._tkcanvas = tk.Canvas(
            master=master, background="white",
            width=w, height=h, borderwidth=0, highlightthickness=0)
        self._tkphoto = tk.PhotoImage(
            master=self._tkcanvas, width=w, height=h)
        self._tkcanvas_image_region = self._tkcanvas.create_image(
            w//2, h//2, image=self._tkphoto)
        self._tkcanvas.bind("<Configure>", self.resize)
        self._tkcanvas.bind("<Map>", self._update_device_pixel_ratio)
        self._tkcanvas.bind("<Key>", self.key_press)
        self._tkcanvas.bind("<Motion>", self.motion_notify_event)
        self._tkcanvas.bind("<Enter>", self.enter_notify_event)
        self._tkcanvas.bind("<Leave>", self.leave_notify_event)
        self._tkcanvas.bind("<KeyRelease>", self.key_release)
        for name in ["<Button-1>", "<Button-2>", "<Button-3>"]:
            self._tkcanvas.bind(name, self.button_press_event)
        for name in [
                "<Double-Button-1>", "<Double-Button-2>", "<Double-Button-3>"]:
            self._tkcanvas.bind(name, self.button_dblclick_event)
        for name in [
                "<ButtonRelease-1>", "<ButtonRelease-2>", "<ButtonRelease-3>"]:
            self._tkcanvas.bind(name, self.button_release_event)

        # Mouse wheel on Linux generates button 4/5 events
        for name in "<Button-4>", "<Button-5>":
            self._tkcanvas.bind(name, self.scroll_event)
        # Mouse wheel for windows goes to the window with the focus.
        # Since the canvas won't usually have the focus, bind the
        # event to the window containing the canvas instead.
        # See https://wiki.tcl-lang.org/3893 (mousewheel) for details
        root = self._tkcanvas.winfo_toplevel()

        # Prevent long-lived references via tkinter callback structure GH-24820
        weakself = weakref.ref(self)
        weakroot = weakref.ref(root)

        def scroll_event_windows(event):
            self = weakself()
            if self is None:
                root = weakroot()
                if root is not None:
                    root.unbind("<MouseWheel>", scroll_event_windows_id)
                return
            return self.scroll_event_windows(event)
        scroll_event_windows_id = root.bind("<MouseWheel>", scroll_event_windows, "+")

        # Can't get destroy events by binding to _tkcanvas. Therefore, bind
        # to the window and filter.
        def filter_destroy(event):
            self = weakself()
            if self is None:
                root = weakroot()
                if root is not None:
                    root.unbind("<Destroy>", filter_destroy_id)
                return
            if event.widget is self._tkcanvas:
                CloseEvent("close_event", self)._process()
        filter_destroy_id = root.bind("<Destroy>", filter_destroy, "+")

        self._tkcanvas.focus_set()

        self._rubberband_rect_black = None
        self._rubberband_rect_white = None

    def _update_device_pixel_ratio(self, event=None):
        ratio = None
        if sys.platform == 'win32':
            # Tk gives scaling with respect to 72 DPI, but Windows screens are
            # scaled vs 96 dpi, and pixel ratio settings are given in whole
            # percentages, so round to 2 digits.
            ratio = round(self._tkcanvas.tk.call('tk', 'scaling') / (96 / 72), 2)
        elif sys.platform == "linux":
            ratio = self._tkcanvas.winfo_fpixels('1i') / 96
        if ratio is not None and self._set_device_pixel_ratio(ratio):
            # The easiest way to resize the canvas is to resize the canvas
            # widget itself, since we implement all the logic for resizing the
            # canvas backing store on that event.
            w, h = self.get_width_height(physical=True)
            self._tkcanvas.configure(width=w, height=h)

    def resize(self, event):
        width, height = event.width, event.height

        # compute desired figure size in inches
        dpival = self.figure.dpi
        winch = width / dpival
        hinch = height / dpival
        self.figure.set_size_inches(winch, hinch, forward=False)

        self._tkcanvas.delete(self._tkcanvas_image_region)
        self._tkphoto.configure(width=int(width), height=int(height))
        self._tkcanvas_image_region = self._tkcanvas.create_image(
            int(width / 2), int(height / 2), image=self._tkphoto)
        ResizeEvent("resize_event", self)._process()
        self.draw_idle()

    def draw_idle(self):
        # docstring inherited
        if self._idle_draw_id:
            return

        def idle_draw(*args):
            try:
                self.draw()
            finally:
                self._idle_draw_id = None

        self._idle_draw_id = self._tkcanvas.after_idle(idle_draw)

    def get_tk_widget(self):
        """
        Return the Tk widget used to implement FigureCanvasTkAgg.

        Although the initial implementation uses a Tk canvas,  this routine
        is intended to hide that fact.
        """
        return self._tkcanvas

    def _event_mpl_coords(self, event):
        # calling canvasx/canvasy allows taking scrollbars into account (i.e.
        # the top of the widget may have been scrolled out of view).
        return (self._tkcanvas.canvasx(event.x),
                # flipy so y=0 is bottom of canvas
                self.figure.bbox.height - self._tkcanvas.canvasy(event.y))

    def motion_notify_event(self, event):
        MouseEvent("motion_notify_event", self,
                   *self._event_mpl_coords(event),
                   buttons=self._mpl_buttons(event),
                   modifiers=self._mpl_modifiers(event),
                   guiEvent=event)._process()

    def enter_notify_event(self, event):
        LocationEvent("figure_enter_event", self,
                      *self._event_mpl_coords(event),
                      modifiers=self._mpl_modifiers(event),
                      guiEvent=event)._process()

    def leave_notify_event(self, event):
        LocationEvent("figure_leave_event", self,
                      *self._event_mpl_coords(event),
                      modifiers=self._mpl_modifiers(event),
                      guiEvent=event)._process()

    def button_press_event(self, event, dblclick=False):
        # set focus to the canvas so that it can receive keyboard events
        self._tkcanvas.focus_set()

        num = getattr(event, 'num', None)
        if sys.platform == 'darwin':  # 2 and 3 are reversed.
            num = {2: 3, 3: 2}.get(num, num)
        MouseEvent("button_press_event", self,
                   *self._event_mpl_coords(event), num, dblclick=dblclick,
                   modifiers=self._mpl_modifiers(event),
                   guiEvent=event)._process()

    def button_dblclick_event(self, event):
        self.button_press_event(event, dblclick=True)

    def button_release_event(self, event):
        num = getattr(event, 'num', None)
        if sys.platform == 'darwin':  # 2 and 3 are reversed.
            num = {2: 3, 3: 2}.get(num, num)
        MouseEvent("button_release_event", self,
                   *self._event_mpl_coords(event), num,
                   modifiers=self._mpl_modifiers(event),
                   guiEvent=event)._process()

    def scroll_event(self, event):
        num = getattr(event, 'num', None)
        step = 1 if num == 4 else -1 if num == 5 else 0
        MouseEvent("scroll_event", self,
                   *self._event_mpl_coords(event), step=step,
                   modifiers=self._mpl_modifiers(event),
                   guiEvent=event)._process()

    def scroll_event_windows(self, event):
        """MouseWheel event processor"""
        # need to find the window that contains the mouse
        w = event.widget.winfo_containing(event.x_root, event.y_root)
        if w != self._tkcanvas:
            return
        x = self._tkcanvas.canvasx(event.x_root - w.winfo_rootx())
        y = (self.figure.bbox.height
             - self._tkcanvas.canvasy(event.y_root - w.winfo_rooty()))
        step = event.delta / 120
        MouseEvent("scroll_event", self,
                   x, y, step=step, modifiers=self._mpl_modifiers(event),
                   guiEvent=event)._process()

    @staticmethod
    def _mpl_buttons(event):  # See _mpl_modifiers.
        # NOTE: This fails to report multiclicks on macOS; only one button is
        # reported (multiclicks work correctly on Linux & Windows).
        modifiers = [
            # macOS appears to swap right and middle (look for "Swap buttons
            # 2/3" in tk/macosx/tkMacOSXMouseEvent.c).
            (MouseButton.LEFT, 1 << 8),
            (MouseButton.RIGHT, 1 << 9),
            (MouseButton.MIDDLE, 1 << 10),
            (MouseButton.BACK, 1 << 11),
            (MouseButton.FORWARD, 1 << 12),
        ] if sys.platform == "darwin" else [
            (MouseButton.LEFT, 1 << 8),
            (MouseButton.MIDDLE, 1 << 9),
            (MouseButton.RIGHT, 1 << 10),
            (MouseButton.BACK, 1 << 11),
            (MouseButton.FORWARD, 1 << 12),
        ]
        # State *before* press/release.
        return [name for name, mask in modifiers if event.state & mask]

    @staticmethod
    def _mpl_modifiers(event, *, exclude=None):
        # Add modifier keys to the key string. Bit values are inferred from
        # the implementation of tkinter.Event.__repr__ (1, 2, 4, 8, ... =
        # Shift, Lock, Control, Mod1, ..., Mod5, Button1, ..., Button5)
        # In general, the modifier key is excluded from the modifier flag,
        # however this is not the case on "darwin", so double check that
        # we aren't adding repeat modifier flags to a modifier key.
        modifiers = [
            ("ctrl", 1 << 2, "control"),
            ("alt", 1 << 17, "alt"),
            ("shift", 1 << 0, "shift"),
        ] if sys.platform == "win32" else [
            ("ctrl", 1 << 2, "control"),
            ("alt", 1 << 4, "alt"),
            ("shift", 1 << 0, "shift"),
            ("cmd", 1 << 3, "cmd"),
        ] if sys.platform == "darwin" else [
            ("ctrl", 1 << 2, "control"),
            ("alt", 1 << 3, "alt"),
            ("shift", 1 << 0, "shift"),
            ("super", 1 << 6, "super"),
        ]
        return [name for name, mask, key in modifiers
                if event.state & mask and exclude != key]

    def _get_key(self, event):
        unikey = event.char
        key = cbook._unikey_or_keysym_to_mplkey(unikey, event.keysym)
        if key is not None:
            mods = self._mpl_modifiers(event, exclude=key)
            # shift is not added to the keys as this is already accounted for.
            if "shift" in mods and unikey:
                mods.remove("shift")
            return "+".join([*mods, key])

    def key_press(self, event):
        KeyEvent("key_press_event", self,
                 self._get_key(event), *self._event_mpl_coords(event),
                 guiEvent=event)._process()

    def key_release(self, event):
        KeyEvent("key_release_event", self,
                 self._get_key(event), *self._event_mpl_coords(event),
                 guiEvent=event)._process()

    def new_timer(self, *args, **kwargs):
        # docstring inherited
        return TimerTk(self._tkcanvas, *args, **kwargs)

    def flush_events(self):
        # docstring inherited
        self._tkcanvas.update()

    def start_event_loop(self, timeout=0):
        # docstring inherited
        if timeout > 0:
            milliseconds = int(1000 * timeout)
            if milliseconds > 0:
                self._event_loop_id = self._tkcanvas.after(
                    milliseconds, self.stop_event_loop)
            else:
                self._event_loop_id = self._tkcanvas.after_idle(
                    self.stop_event_loop)
        self._tkcanvas.mainloop()

    def stop_event_loop(self):
        # docstring inherited
        if self._event_loop_id:
            self._tkcanvas.after_cancel(self._event_loop_id)
            self._event_loop_id = None
        self._tkcanvas.quit()

    def set_cursor(self, cursor):
        try:
            self._tkcanvas.configure(cursor=cursord[cursor])
        except tkinter.TclError:
            pass


class FigureManagerTk(FigureManagerBase):
    """
    Attributes
    ----------
    canvas : `FigureCanvas`
        The FigureCanvas instance
    num : int or str
        The Figure number
    toolbar : tk.Toolbar
        The tk.Toolbar
    window : tk.Window
        The tk.Window
    """

    _owns_mainloop = False

    def __init__(self, canvas, num, window):
        self.window = window
        super().__init__(canvas, num)
        self.window.withdraw()
        # packing toolbar first, because if space is getting low, last packed
        # widget is getting shrunk first (-> the canvas)
        self.canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        # If the window has per-monitor DPI awareness, then setup a Tk variable
        # to store the DPI, which will be updated by the C code, and the trace
        # will handle it on the Python side.
        window_frame = int(window.wm_frame(), 16)
        self._window_dpi = tk.IntVar(master=window, value=96,
                                     name=f'window_dpi{window_frame}')
        self._window_dpi_cbname = ''
        if _tkagg.enable_dpi_awareness(window_frame, window.tk.interpaddr()):
            self._window_dpi_cbname = self._window_dpi.trace_add(
                'write', self._update_window_dpi)

        self._shown = False

    @classmethod
    def create_with_canvas(cls, canvas_class, figure, num):
        # docstring inherited
        with _restore_foreground_window_at_end():
            if cbook._get_running_interactive_framework() is None:
                cbook._setup_new_guiapp()
                _c_internal_utils.Win32_SetProcessDpiAwareness_max()
            window = tk.Tk(className="matplotlib")
            window.withdraw()

            # Put a Matplotlib icon on the window rather than the default tk
            # icon. See https://www.tcl.tk/man/tcl/TkCmd/wm.html#M50
            #
            # `ImageTk` can be replaced with `tk` whenever the minimum
            # supported Tk version is increased to 8.6, as Tk 8.6+ natively
            # supports PNG images.
            icon_fname = str(cbook._get_data_path(
                'images/matplotlib.png'))
            icon_img = ImageTk.PhotoImage(file=icon_fname, master=window)

            icon_fname_large = str(cbook._get_data_path(
                'images/matplotlib_large.png'))
            icon_img_large = ImageTk.PhotoImage(
                file=icon_fname_large, master=window)

            window.iconphoto(False, icon_img_large, icon_img)

            canvas = canvas_class(figure, master=window)
            manager = cls(canvas, num, window)
            if mpl.is_interactive():
                manager.show()
                canvas.draw_idle()
            return manager

    @classmethod
    def start_main_loop(cls):
        managers = Gcf.get_all_fig_managers()
        if managers:
            first_manager = managers[0]
            manager_class = type(first_manager)
            if manager_class._owns_mainloop:
                return
            manager_class._owns_mainloop = True
            try:
                first_manager.window.mainloop()
            finally:
                manager_class._owns_mainloop = False

    def _update_window_dpi(self, *args):
        newdpi = self._window_dpi.get()
        self.window.call('tk', 'scaling', newdpi / 72)
        if self.toolbar and hasattr(self.toolbar, '_rescale'):
            self.toolbar._rescale()
        self.canvas._update_device_pixel_ratio()

    def resize(self, width, height):
        max_size = 1_400_000  # the measured max on xorg 1.20.8 was 1_409_023

        if (width > max_size or height > max_size) and sys.platform == 'linux':
            raise ValueError(
                'You have requested to resize the '
                f'Tk window to ({width}, {height}), one of which '
                f'is bigger than {max_size}.  At larger sizes xorg will '
                'either exit with an error on newer versions (~1.20) or '
                'cause corruption on older version (~1.19).  We '
                'do not expect a window over a million pixel wide or tall '
                'to be intended behavior.')
        self.canvas._tkcanvas.configure(width=width, height=height)

    def show(self):
        with _restore_foreground_window_at_end():
            if not self._shown:
                def destroy(*args):
                    Gcf.destroy(self)
                self.window.protocol("WM_DELETE_WINDOW", destroy)
                self.window.deiconify()
                self.canvas._tkcanvas.focus_set()
            else:
                self.canvas.draw_idle()
            if mpl.rcParams['figure.raise_window']:
                self.canvas.manager.window.attributes('-topmost', 1)
                self.canvas.manager.window.attributes('-topmost', 0)
            self._shown = True

    def destroy(self, *args):
        if self.canvas._idle_draw_id:
            self.canvas._tkcanvas.after_cancel(self.canvas._idle_draw_id)
        if self.canvas._event_loop_id:
            self.canvas._tkcanvas.after_cancel(self.canvas._event_loop_id)
        if self._window_dpi_cbname:
            self._window_dpi.trace_remove('write', self._window_dpi_cbname)

        # NOTE: events need to be flushed before issuing destroy (GH #9956),
        # however, self.window.update() can break user code. An async callback
        # is the safest way to achieve a complete draining of the event queue,
        # but it leaks if no tk event loop is running. Therefore we explicitly
        # check for an event loop and choose our best guess.
        def delayed_destroy():
            self.window.destroy()

            if self._owns_mainloop and not Gcf.get_num_fig_managers():
                self.window.quit()

        if cbook._get_running_interactive_framework() == "tk":
            # "after idle after 0" avoids Tcl error/race (GH #19940)
            self.window.after_idle(self.window.after, 0, delayed_destroy)
        else:
            self.window.update()
            delayed_destroy()

    def get_window_title(self):
        return self.window.wm_title()

    def set_window_title(self, title):
        self.window.wm_title(title)

    def full_screen_toggle(self):
        is_fullscreen = bool(self.window.attributes('-fullscreen'))
        self.window.attributes('-fullscreen', not is_fullscreen)


class NavigationToolbar2Tk(NavigationToolbar2, tk.Frame):
    def __init__(self, canvas, window=None, *, pack_toolbar=True):
        """
        Parameters
        ----------
        canvas : `FigureCanvas`
            The figure canvas on which to operate.
        window : tk.Window
            The tk.Window which owns this toolbar.
        pack_toolbar : bool, default: True
            If True, add the toolbar to the parent's pack manager's packing
            list during initialization with ``side="bottom"`` and ``fill="x"``.
            If you want to use the toolbar with a different layout manager, use
            ``pack_toolbar=False``.
        """

        if window is None:
            window = canvas.get_tk_widget().master
        tk.Frame.__init__(self, master=window, borderwidth=2,
                          width=int(canvas.figure.bbox.width), height=50)

        self._buttons = {}
        for text, tooltip_text, image_file, callback in self.toolitems:
            if text is None:
                # Add a spacer; return value is unused.
                self._Spacer()
            else:
                self._buttons[text] = button = self._Button(
                    text,
                    str(cbook._get_data_path(f"images/{image_file}.png")),
                    toggle=callback in ["zoom", "pan"],
                    command=getattr(self, callback),
                )
                if tooltip_text is not None:
                    add_tooltip(button, tooltip_text)

        self._label_font = tkinter.font.Font(root=window, size=10)

        # This filler item ensures the toolbar is always at least two text
        # lines high. Otherwise the canvas gets redrawn as the mouse hovers
        # over images because those use two-line messages which resize the
        # toolbar.
        label = tk.Label(master=self, font=self._label_font,
                         text='\N{NO-BREAK SPACE}\n\N{NO-BREAK SPACE}')
        label.pack(side=tk.RIGHT)

        self.message = tk.StringVar(master=self)
        self._message_label = tk.Label(master=self, font=self._label_font,
                                       textvariable=self.message,
                                       justify=tk.RIGHT)
        self._message_label.pack(side=tk.RIGHT)

        NavigationToolbar2.__init__(self, canvas)
        if pack_toolbar:
            self.pack(side=tk.BOTTOM, fill=tk.X)

    def _rescale(self):
        """
        Scale all children of the toolbar to current DPI setting.

        Before this is called, the Tk scaling setting will have been updated to
        match the new DPI. Tk widgets do not update for changes to scaling, but
        all measurements made after the change will match the new scaling. Thus
        this function re-applies all the same sizes in points, which Tk will
        scale correctly to pixels.
        """
        for widget in self.winfo_children():
            if isinstance(widget, (tk.Button, tk.Checkbutton)):
                if hasattr(widget, '_image_file'):
                    # Explicit class because ToolbarTk calls _rescale.
                    NavigationToolbar2Tk._set_image_for_button(self, widget)
                else:
                    # Text-only button is handled by the font setting instead.
                    pass
            elif isinstance(widget, tk.Frame):
                widget.configure(height='18p')
                widget.pack_configure(padx='3p')
            elif isinstance(widget, tk.Label):
                pass  # Text is handled by the font setting instead.
            else:
                _log.warning('Unknown child class %s', widget.winfo_class)
        self._label_font.configure(size=10)

    def _update_buttons_checked(self):
        # sync button checkstates to match active mode
        for text, mode in [('Zoom', _Mode.ZOOM), ('Pan', _Mode.PAN)]:
            if text in self._buttons:
                if self.mode == mode:
                    self._buttons[text].select()  # NOT .invoke()
                else:
                    self._buttons[text].deselect()

    def pan(self, *args):
        super().pan(*args)
        self._update_buttons_checked()

    def zoom(self, *args):
        super().zoom(*args)
        self._update_buttons_checked()

    def set_message(self, s):
        self.message.set(s)

    def draw_rubberband(self, event, x0, y0, x1, y1):
        # Block copied from remove_rubberband for backend_tools convenience.
        if self.canvas._rubberband_rect_white:
            self.canvas._tkcanvas.delete(self.canvas._rubberband_rect_white)
        if self.canvas._rubberband_rect_black:
            self.canvas._tkcanvas.delete(self.canvas._rubberband_rect_black)
        height = self.canvas.figure.bbox.height
        y0 = height - y0
        y1 = height - y1
        self.canvas._rubberband_rect_black = (
            self.canvas._tkcanvas.create_rectangle(
                x0, y0, x1, y1))
        self.canvas._rubberband_rect_white = (
            self.canvas._tkcanvas.create_rectangle(
                x0, y0, x1, y1, outline='white', dash=(3, 3)))

    def remove_rubberband(self):
        if self.canvas._rubberband_rect_white:
            self.canvas._tkcanvas.delete(self.canvas._rubberband_rect_white)
            self.canvas._rubberband_rect_white = None
        if self.canvas._rubberband_rect_black:
            self.canvas._tkcanvas.delete(self.canvas._rubberband_rect_black)
            self.canvas._rubberband_rect_black = None

    def _set_image_for_button(self, button):
        """
        Set the image for a button based on its pixel size.

        The pixel size is determined by the DPI scaling of the window.
        """
        if button._image_file is None:
            return

        # Allow _image_file to be relative to Matplotlib's "images" data
        # directory.
        path_regular = cbook._get_data_path('images', button._image_file)
        path_large = path_regular.with_name(
            path_regular.name.replace('.png', '_large.png'))
        size = button.winfo_pixels('18p')

        # Nested functions because ToolbarTk calls  _Button.
        def _get_color(color_name):
            # `winfo_rgb` returns an (r, g, b) tuple in the range 0-65535
            return button.winfo_rgb(button.cget(color_name))

        def _is_dark(color):
            if isinstance(color, str):
                color = _get_color(color)
            return max(color) < 65535 / 2

        def _recolor_icon(image, color):
            image_data = np.asarray(image).copy()
            black_mask = (image_data[..., :3] == 0).all(axis=-1)
            image_data[black_mask, :3] = color
            return Image.fromarray(image_data, mode="RGBA")

        # Use the high-resolution (48x48 px) icon if it exists and is needed
        with Image.open(path_large if (size > 24 and path_large.exists())
                        else path_regular) as im:
            # assure a RGBA image as foreground color is RGB
            im = im.convert("RGBA")
            image = ImageTk.PhotoImage(im.resize((size, size)), master=self)
            button._ntimage = image

            # create a version of the icon with the button's text color
            foreground = (255 / 65535) * np.array(
                button.winfo_rgb(button.cget("foreground")))
            im_alt = _recolor_icon(im, foreground)
            image_alt = ImageTk.PhotoImage(
                im_alt.resize((size, size)), master=self)
            button._ntimage_alt = image_alt

        if _is_dark("background"):
            # For Checkbuttons, we need to set `image` and `selectimage` at
            # the same time. Otherwise, when updating the `image` option
            # (such as when changing DPI), if the old `selectimage` has
            # just been overwritten, Tk will throw an error.
            image_kwargs = {"image": image_alt}
        else:
            image_kwargs = {"image": image}
        # Checkbuttons may switch the background to `selectcolor` in the
        # checked state, so check separately which image it needs to use in
        # that state to still ensure enough contrast with the background.
        if (
            isinstance(button, tk.Checkbutton)
            and button.cget("selectcolor") != ""
        ):
            if self._windowingsystem != "x11":
                selectcolor = "selectcolor"
            else:
                # On X11, selectcolor isn't used directly for indicator-less
                # buttons. See `::tk::CheckEnter` in the Tk button.tcl source
                # code for details.
                r1, g1, b1 = _get_color("selectcolor")
                r2, g2, b2 = _get_color("activebackground")
                selectcolor = ((r1+r2)/2, (g1+g2)/2, (b1+b2)/2)
            if _is_dark(selectcolor):
                image_kwargs["selectimage"] = image_alt
            else:
                image_kwargs["selectimage"] = image

        button.configure(**image_kwargs, height='18p', width='18p')

    def _Button(self, text, image_file, toggle, command):
        if not toggle:
            b = tk.Button(
                master=self, text=text, command=command,
                relief="flat", overrelief="groove", borderwidth=1,
            )
        else:
            # There is a bug in tkinter included in some python 3.6 versions
            # that without this variable, produces a "visual" toggling of
            # other near checkbuttons
            # https://bugs.python.org/issue29402
            # https://bugs.python.org/issue25684
            var = tk.IntVar(master=self)
            b = tk.Checkbutton(
                master=self, text=text, command=command, indicatoron=False,
                variable=var, offrelief="flat", overrelief="groove",
                borderwidth=1
            )
            b.var = var
        b._image_file = image_file
        if image_file is not None:
            # Explicit class because ToolbarTk calls _Button.
            NavigationToolbar2Tk._set_image_for_button(self, b)
        else:
            b.configure(font=self._label_font)
        b.pack(side=tk.LEFT)
        return b

    def _Spacer(self):
        # Buttons are also 18pt high.
        s = tk.Frame(master=self, height='18p', relief=tk.RIDGE, bg='DarkGray')
        s.pack(side=tk.LEFT, padx='3p')
        return s

    def save_figure(self, *args):
        filetypes = self.canvas.get_supported_filetypes_grouped()
        tk_filetypes = [
            (name, " ".join(f"*.{ext}" for ext in exts))
            for name, exts in sorted(filetypes.items())
        ]

        default_extension = self.canvas.get_default_filetype()
        default_filetype = self.canvas.get_supported_filetypes()[default_extension]
        filetype_variable = tk.StringVar(self.canvas.get_tk_widget(), default_filetype)

        # adding a default extension seems to break the
        # asksaveasfilename dialog when you choose various save types
        # from the dropdown.  Passing in the empty string seems to
        # work - JDH!
        # defaultextension = self.canvas.get_default_filetype()
        defaultextension = ''
        initialdir = os.path.expanduser(mpl.rcParams['savefig.directory'])
        # get_default_filename() contains the default extension. On some platforms,
        # choosing a different extension from the dropdown does not overwrite it,
        # so we need to remove it to make the dropdown functional.
        initialfile = pathlib.Path(self.canvas.get_default_filename()).stem
        fname = tkinter.filedialog.asksaveasfilename(
            master=self.canvas.get_tk_widget().master,
            title='Save the figure',
            filetypes=tk_filetypes,
            defaultextension=defaultextension,
            initialdir=initialdir,
            initialfile=initialfile,
            typevariable=filetype_variable
            )

        if fname in ["", ()]:
            return None
        # Save dir for next time, unless empty str (i.e., use cwd).
        if initialdir != "":
            mpl.rcParams['savefig.directory'] = (
                os.path.dirname(str(fname)))

        # If the filename contains an extension, let savefig() infer the file
        # format from that. If it does not, use the selected dropdown option.
        if pathlib.Path(fname).suffix[1:] != "":
            extension = None
        else:
            extension = filetypes[filetype_variable.get()][0]

        try:
            self.canvas.figure.savefig(fname, format=extension)
            return fname
        except Exception as e:
            tkinter.messagebox.showerror("Error saving file", str(e))

    def set_history_buttons(self):
        state_map = {True: tk.NORMAL, False: tk.DISABLED}
        can_back = self._nav_stack._pos > 0
        can_forward = self._nav_stack._pos < len(self._nav_stack) - 1
        if "Back" in self._buttons:
            self._buttons['Back']['state'] = state_map[can_back]
        if "Forward" in self._buttons:
            self._buttons['Forward']['state'] = state_map[can_forward]


def add_tooltip(widget, text):
    tipwindow = None

    def showtip(event):
        """Display text in tooltip window."""
        nonlocal tipwindow
        if tipwindow or not text:
            return
        x, y, _, _ = widget.bbox("insert")
        x = x + widget.winfo_rootx() + widget.winfo_width()
        y = y + widget.winfo_rooty()
        tipwindow = tk.Toplevel(widget)
        tipwindow.overrideredirect(1)
        tipwindow.geometry(f"+{x}+{y}")
        try:  # For Mac OS
            tipwindow.tk.call("::tk::unsupported::MacWindowStyle",
                              "style", tipwindow._w,
                              "help", "noActivates")
        except tk.TclError:
            pass
        label = tk.Label(tipwindow, text=text, justify=tk.LEFT,
                         relief=tk.SOLID, borderwidth=1)
        label.pack(ipadx=1)

    def hidetip(event):
        nonlocal tipwindow
        if tipwindow:
            tipwindow.destroy()
        tipwindow = None

    widget.bind("<Enter>", showtip)
    widget.bind("<Leave>", hidetip)


@backend_tools._register_tool_class(FigureCanvasTk)
class RubberbandTk(backend_tools.RubberbandBase):
    def draw_rubberband(self, x0, y0, x1, y1):
        NavigationToolbar2Tk.draw_rubberband(
            self._make_classic_style_pseudo_toolbar(), None, x0, y0, x1, y1)

    def remove_rubberband(self):
        NavigationToolbar2Tk.remove_rubberband(
            self._make_classic_style_pseudo_toolbar())


class ToolbarTk(ToolContainerBase, tk.Frame):
    def __init__(self, toolmanager, window=None):
        ToolContainerBase.__init__(self, toolmanager)
        if window is None:
            window = self.toolmanager.canvas.get_tk_widget().master
        xmin, xmax = self.toolmanager.canvas.figure.bbox.intervalx
        height, width = 50, xmax - xmin
        tk.Frame.__init__(self, master=window,
                          width=int(width), height=int(height),
                          borderwidth=2)
        self._label_font = tkinter.font.Font(size=10)
        # This filler item ensures the toolbar is always at least two text
        # lines high. Otherwise the canvas gets redrawn as the mouse hovers
        # over images because those use two-line messages which resize the
        # toolbar.
        label = tk.Label(master=self, font=self._label_font,
                         text='\N{NO-BREAK SPACE}\n\N{NO-BREAK SPACE}')
        label.pack(side=tk.RIGHT)
        self._message = tk.StringVar(master=self)
        self._message_label = tk.Label(master=self, font=self._label_font,
                                       textvariable=self._message)
        self._message_label.pack(side=tk.RIGHT)
        self._toolitems = {}
        self.pack(side=tk.TOP, fill=tk.X)
        self._groups = {}

    def _rescale(self):
        return NavigationToolbar2Tk._rescale(self)

    def add_toolitem(
            self, name, group, position, image_file, description, toggle):
        frame = self._get_groupframe(group)
        buttons = frame.pack_slaves()
        if position >= len(buttons) or position < 0:
            before = None
        else:
            before = buttons[position]
        button = NavigationToolbar2Tk._Button(frame, name, image_file, toggle,
                                              lambda: self._button_click(name))
        button.pack_configure(before=before)
        if description is not None:
            add_tooltip(button, description)
        self._toolitems.setdefault(name, [])
        self._toolitems[name].append(button)

    def _get_groupframe(self, group):
        if group not in self._groups:
            if self._groups:
                self._add_separator()
            frame = tk.Frame(master=self, borderwidth=0)
            frame.pack(side=tk.LEFT, fill=tk.Y)
            frame._label_font = self._label_font
            self._groups[group] = frame
        return self._groups[group]

    def _add_separator(self):
        return NavigationToolbar2Tk._Spacer(self)

    def _button_click(self, name):
        self.trigger_tool(name)

    def toggle_toolitem(self, name, toggled):
        if name not in self._toolitems:
            return
        for toolitem in self._toolitems[name]:
            if toggled:
                toolitem.select()
            else:
                toolitem.deselect()

    def remove_toolitem(self, name):
        for toolitem in self._toolitems.pop(name, []):
            toolitem.pack_forget()

    def set_message(self, s):
        self._message.set(s)


@backend_tools._register_tool_class(FigureCanvasTk)
class SaveFigureTk(backend_tools.SaveFigureBase):
    def trigger(self, *args):
        NavigationToolbar2Tk.save_figure(
            self._make_classic_style_pseudo_toolbar())


@backend_tools._register_tool_class(FigureCanvasTk)
class ConfigureSubplotsTk(backend_tools.ConfigureSubplotsBase):
    def trigger(self, *args):
        NavigationToolbar2Tk.configure_subplots(self)


@backend_tools._register_tool_class(FigureCanvasTk)
class HelpTk(backend_tools.ToolHelpBase):
    def trigger(self, *args):
        dialog = SimpleDialog(
            self.figure.canvas._tkcanvas, self._get_help_text(), ["OK"])
        dialog.done = lambda num: dialog.frame.master.withdraw()


Toolbar = ToolbarTk
FigureManagerTk._toolbar2_class = NavigationToolbar2Tk
FigureManagerTk._toolmanager_toolbar_class = ToolbarTk


@_Backend.export
class _BackendTk(_Backend):
    backend_version = tk.TkVersion
    FigureCanvas = FigureCanvasTk
    FigureManager = FigureManagerTk
    mainloop = FigureManagerTk.start_main_loop

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\urllib3\packages\six.py ===
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