
# === NexusCore/openenv\Lib\site-packages\jedi\api\classes.py ===
"""
There are a couple of classes documented in here:

- :class:`.BaseName` as an abstact base class for almost everything.
- :class:`.Name` used in a lot of places
- :class:`.Completion` for completions
- :class:`.BaseSignature` as a base class for signatures
- :class:`.Signature` for :meth:`.Script.get_signatures` only
- :class:`.ParamName` used for parameters of signatures
- :class:`.Refactoring` for refactorings
- :class:`.SyntaxError` for :meth:`.Script.get_syntax_errors` only

These classes are the much biggest part of the API, because they contain
the interesting information about all operations.
"""
import re
from pathlib import Path
from typing import Optional

from parso.tree import search_ancestor

from jedi import settings
from jedi import debug
from jedi.inference.utils import unite
from jedi.cache import memoize_method
from jedi.inference.compiled.mixed import MixedName
from jedi.inference.names import ImportName, SubModuleName
from jedi.inference.gradual.stub_value import StubModuleValue
from jedi.inference.gradual.conversion import convert_names, convert_values
from jedi.inference.base_value import ValueSet, HasNoContext
from jedi.api.keywords import KeywordName
from jedi.api import completion_cache
from jedi.api.helpers import filter_follow_imports


def _sort_names_by_start_pos(names):
    return sorted(names, key=lambda s: s.start_pos or (0, 0))


def defined_names(inference_state, value):
    """
    List sub-definitions (e.g., methods in class).

    :type scope: Scope
    :rtype: list of Name
    """
    try:
        context = value.as_context()
    except HasNoContext:
        return []
    filter = next(context.get_filters())
    names = [name for name in filter.values()]
    return [Name(inference_state, n) for n in _sort_names_by_start_pos(names)]


def _values_to_definitions(values):
    return [Name(c.inference_state, c.name) for c in values]


class BaseName:
    """
    The base class for all definitions, completions and signatures.
    """
    _mapping = {
        'posixpath': 'os.path',
        'riscospath': 'os.path',
        'ntpath': 'os.path',
        'os2emxpath': 'os.path',
        'macpath': 'os.path',
        'genericpath': 'os.path',
        'posix': 'os',
        '_io': 'io',
        '_functools': 'functools',
        '_collections': 'collections',
        '_socket': 'socket',
        '_sqlite3': 'sqlite3',
    }

    _tuple_mapping = dict((tuple(k.split('.')), v) for (k, v) in {
        'argparse._ActionsContainer': 'argparse.ArgumentParser',
    }.items())

    def __init__(self, inference_state, name):
        self._inference_state = inference_state
        self._name = name
        """
        An instance of :class:`parso.python.tree.Name` subclass.
        """
        self.is_keyword = isinstance(self._name, KeywordName)

    @memoize_method
    def _get_module_context(self):
        # This can take a while to complete, because in the worst case of
        # imports (consider `import a` completions), we need to load all
        # modules starting with a first.
        return self._name.get_root_context()

    @property
    def module_path(self) -> Optional[Path]:
        """
        Shows the file path of a module. e.g. ``/usr/lib/python3.9/os.py``
        """
        module = self._get_module_context()
        if module.is_stub() or not module.is_compiled():
            # Compiled modules should not return a module path even if they
            # have one.
            path: Optional[Path] = self._get_module_context().py__file__()
            return path

        return None

    @property
    def name(self):
        """
        Name of variable/function/class/module.

        For example, for ``x = None`` it returns ``'x'``.

        :rtype: str or None
        """
        return self._name.get_public_name()

    @property
    def type(self):
        """
        The type of the definition.

        Here is an example of the value of this attribute.  Let's consider
        the following source.  As what is in ``variable`` is unambiguous
        to Jedi, :meth:`jedi.Script.infer` should return a list of
        definition for ``sys``, ``f``, ``C`` and ``x``.

        >>> from jedi import Script
        >>> source = '''
        ... import keyword
        ...
        ... class C:
        ...     pass
        ...
        ... class D:
        ...     pass
        ...
        ... x = D()
        ...
        ... def f():
        ...     pass
        ...
        ... for variable in [keyword, f, C, x]:
        ...     variable'''

        >>> script = Script(source)
        >>> defs = script.infer()

        Before showing what is in ``defs``, let's sort it by :attr:`line`
        so that it is easy to relate the result to the source code.

        >>> defs = sorted(defs, key=lambda d: d.line)
        >>> print(defs)  # doctest: +NORMALIZE_WHITESPACE
        [<Name full_name='keyword', description='module keyword'>,
         <Name full_name='__main__.C', description='class C'>,
         <Name full_name='__main__.D', description='instance D'>,
         <Name full_name='__main__.f', description='def f'>]

        Finally, here is what you can get from :attr:`type`:

        >>> defs = [d.type for d in defs]
        >>> defs[0]
        'module'
        >>> defs[1]
        'class'
        >>> defs[2]
        'instance'
        >>> defs[3]
        'function'

        Valid values for type are ``module``, ``class``, ``instance``, ``function``,
        ``param``, ``path``, ``keyword``, ``property`` and ``statement``.

        """
        tree_name = self._name.tree_name
        resolve = False
        if tree_name is not None:
            # TODO move this to their respective names.
            definition = tree_name.get_definition()
            if definition is not None and definition.type == 'import_from' and \
                    tree_name.is_definition():
                resolve = True

        if isinstance(self._name, SubModuleName) or resolve:
            for value in self._name.infer():
                return value.api_type
        return self._name.api_type

    @property
    def module_name(self):
        """
        The module name, a bit similar to what ``__name__`` is in a random
        Python module.

        >>> from jedi import Script
        >>> source = 'import json'
        >>> script = Script(source, path='example.py')
        >>> d = script.infer()[0]
        >>> print(d.module_name)  # doctest: +ELLIPSIS
        json
        """
        return self._get_module_context().py__name__()

    def in_builtin_module(self):
        """
        Returns True, if this is a builtin module.
        """
        value = self._get_module_context().get_value()
        if isinstance(value, StubModuleValue):
            return any(v.is_compiled() for v in value.non_stub_value_set)
        return value.is_compiled()

    @property
    def line(self):
        """The line where the definition occurs (starting with 1)."""
        start_pos = self._name.start_pos
        if start_pos is None:
            return None
        return start_pos[0]

    @property
    def column(self):
        """The column where the definition occurs (starting with 0)."""
        start_pos = self._name.start_pos
        if start_pos is None:
            return None
        return start_pos[1]

    def get_definition_start_position(self):
        """
        The (row, column) of the start of the definition range. Rows start with
        1, columns start with 0.

        :rtype: Optional[Tuple[int, int]]
        """
        if self._name.tree_name is None:
            return None
        definition = self._name.tree_name.get_definition()
        if definition is None:
            return self._name.start_pos
        return definition.start_pos

    def get_definition_end_position(self):
        """
        The (row, column) of the end of the definition range. Rows start with
        1, columns start with 0.

        :rtype: Optional[Tuple[int, int]]
        """
        if self._name.tree_name is None:
            return None
        definition = self._name.tree_name.get_definition()
        if definition is None:
            return self._name.tree_name.end_pos
        if self.type in ("function", "class"):
            last_leaf = definition.get_last_leaf()
            if last_leaf.type == "newline":
                return last_leaf.get_previous_leaf().end_pos
            return last_leaf.end_pos
        return definition.end_pos

    def docstring(self, raw=False, fast=True):
        r"""
        Return a document string for this completion object.

        Example:

        >>> from jedi import Script
        >>> source = '''\
        ... def f(a, b=1):
        ...     "Document for function f."
        ... '''
        >>> script = Script(source, path='example.py')
        >>> doc = script.infer(1, len('def f'))[0].docstring()
        >>> print(doc)
        f(a, b=1)
        <BLANKLINE>
        Document for function f.

        Notice that useful extra information is added to the actual
        docstring, e.g. function signatures are prepended to their docstrings.
        If you need the actual docstring, use ``raw=True`` instead.

        >>> print(script.infer(1, len('def f'))[0].docstring(raw=True))
        Document for function f.

        :param fast: Don't follow imports that are only one level deep like
            ``import foo``, but follow ``from foo import bar``. This makes
            sense for speed reasons. Completing `import a` is slow if you use
            the ``foo.docstring(fast=False)`` on every object, because it
            parses all libraries starting with ``a``.
        """
        if isinstance(self._name, ImportName) and fast:
            return ''
        doc = self._get_docstring()
        if raw:
            return doc

        signature_text = self._get_docstring_signature()
        if signature_text and doc:
            return signature_text + '\n\n' + doc
        else:
            return signature_text + doc

    def _get_docstring(self):
        return self._name.py__doc__()

    def _get_docstring_signature(self):
        return '\n'.join(
            signature.to_string()
            for signature in self._get_signatures(for_docstring=True)
        )

    @property
    def description(self):
        """
        A description of the :class:`.Name` object, which is heavily used
        in testing. e.g. for ``isinstance`` it returns ``def isinstance``.

        Example:

        >>> from jedi import Script
        >>> source = '''
        ... def f():
        ...     pass
        ...
        ... class C:
        ...     pass
        ...
        ... variable = f if random.choice([0,1]) else C'''
        >>> script = Script(source)  # line is maximum by default
        >>> defs = script.infer(column=3)
        >>> defs = sorted(defs, key=lambda d: d.line)
        >>> print(defs)  # doctest: +NORMALIZE_WHITESPACE
        [<Name full_name='__main__.f', description='def f'>,
         <Name full_name='__main__.C', description='class C'>]
        >>> str(defs[0].description)
        'def f'
        >>> str(defs[1].description)
        'class C'

        """
        typ = self.type
        tree_name = self._name.tree_name
        if typ == 'param':
            return typ + ' ' + self._name.to_string()
        if typ in ('function', 'class', 'module', 'instance') or tree_name is None:
            if typ == 'function':
                # For the description we want a short and a pythonic way.
                typ = 'def'
            return typ + ' ' + self._name.get_public_name()

        definition = tree_name.get_definition(include_setitem=True) or tree_name
        # Remove the prefix, because that's not what we want for get_code
        # here.
        txt = definition.get_code(include_prefix=False)
        # Delete comments:
        txt = re.sub(r'#[^\n]+\n', ' ', txt)
        # Delete multi spaces/newlines
        txt = re.sub(r'\s+', ' ', txt).strip()
        return txt

    @property
    def full_name(self):
        """
        Dot-separated path of this object.

        It is in the form of ``<module>[.<submodule>[...]][.<object>]``.
        It is useful when you want to look up Python manual of the
        object at hand.

        Example:

        >>> from jedi import Script
        >>> source = '''
        ... import os
        ... os.path.join'''
        >>> script = Script(source, path='example.py')
        >>> print(script.infer(3, len('os.path.join'))[0].full_name)
        os.path.join

        Notice that it returns ``'os.path.join'`` instead of (for example)
        ``'posixpath.join'``. This is not correct, since the modules name would
        be ``<module 'posixpath' ...>```. However most users find the latter
        more practical.
        """
        if not self._name.is_value_name:
            return None

        names = self._name.get_qualified_names(include_module_names=True)
        if names is None:
            return None

        names = list(names)
        try:
            names[0] = self._mapping[names[0]]
        except KeyError:
            pass

        return '.'.join(names)

    def is_stub(self):
        """
        Returns True if the current name is defined in a stub file.
        """
        if not self._name.is_value_name:
            return False

        return self._name.get_root_context().is_stub()

    def is_side_effect(self):
        """
        Checks if a name is defined as ``self.foo = 3``. In case of self, this
        function would return False, for foo it would return True.
        """
        tree_name = self._name.tree_name
        if tree_name is None:
            return False
        return tree_name.is_definition() and tree_name.parent.type == 'trailer'

    @debug.increase_indent_cm('goto on name')
    def goto(self, *, follow_imports=False, follow_builtin_imports=False,
             only_stubs=False, prefer_stubs=False):

        """
        Like :meth:`.Script.goto` (also supports the same params), but does it
        for the current name. This is typically useful if you are using
        something like :meth:`.Script.get_names()`.

        :param follow_imports: The goto call will follow imports.
        :param follow_builtin_imports: If follow_imports is True will try to
            look up names in builtins (i.e. compiled or extension modules).
        :param only_stubs: Only return stubs for this goto call.
        :param prefer_stubs: Prefer stubs to Python objects for this goto call.
        :rtype: list of :class:`Name`
        """
        if not self._name.is_value_name:
            return []

        names = self._name.goto()
        if follow_imports:
            names = filter_follow_imports(names, follow_builtin_imports)
        names = convert_names(
            names,
            only_stubs=only_stubs,
            prefer_stubs=prefer_stubs,
        )
        return [self if n == self._name else Name(self._inference_state, n)
                for n in names]

    @debug.increase_indent_cm('infer on name')
    def infer(self, *, only_stubs=False, prefer_stubs=False):
        """
        Like :meth:`.Script.infer`, it can be useful to understand which type
        the current name has.

        Return the actual definitions. I strongly recommend not using it for
        your completions, because it might slow down |jedi|. If you want to
        read only a few objects (<=20), it might be useful, especially to get
        the original docstrings. The basic problem of this function is that it
        follows all results. This means with 1000 completions (e.g.  numpy),
        it's just very, very slow.

        :param only_stubs: Only return stubs for this goto call.
        :param prefer_stubs: Prefer stubs to Python objects for this type
            inference call.
        :rtype: list of :class:`Name`
        """
        assert not (only_stubs and prefer_stubs)

        if not self._name.is_value_name:
            return []

        # First we need to make sure that we have stub names (if possible) that
        # we can follow. If we don't do that, we can end up with the inferred
        # results of Python objects instead of stubs.
        names = convert_names([self._name], prefer_stubs=True)
        values = convert_values(
            ValueSet.from_sets(n.infer() for n in names),
            only_stubs=only_stubs,
            prefer_stubs=prefer_stubs,
        )
        resulting_names = [c.name for c in values]
        return [self if n == self._name else Name(self._inference_state, n)
                for n in resulting_names]

    def parent(self):
        """
        Returns the parent scope of this identifier.

        :rtype: Name
        """
        if not self._name.is_value_name:
            return None

        if self.type in ('function', 'class', 'param') and self._name.tree_name is not None:
            # Since the parent_context doesn't really match what the user
            # thinks of that the parent is here, we do these cases separately.
            # The reason for this is the following:
            # - class: Nested classes parent_context is always the
            #   parent_context of the most outer one.
            # - function: Functions in classes have the module as
            #   parent_context.
            # - param: The parent_context of a param is not its function but
            #   e.g. the outer class or module.
            cls_or_func_node = self._name.tree_name.get_definition()
            parent = search_ancestor(cls_or_func_node, 'funcdef', 'classdef', 'file_input')
            context = self._get_module_context().create_value(parent).as_context()
        else:
            context = self._name.parent_context

        if context is None:
            return None
        while context.name is None:
            # Happens for comprehension contexts
            context = context.parent_context

        return Name(self._inference_state, context.name)

    def __repr__(self):
        return "<%s %sname=%r, description=%r>" % (
            self.__class__.__name__,
            'full_' if self.full_name else '',
            self.full_name or self.name,
            self.description,
        )

    def get_line_code(self, before=0, after=0):
        """
        Returns the line of code where this object was defined.

        :param before: Add n lines before the current line to the output.
        :param after: Add n lines after the current line to the output.

        :return str: Returns the line(s) of code or an empty string if it's a
                     builtin.
        """
        if not self._name.is_value_name:
            return ''

        lines = self._name.get_root_context().code_lines
        if lines is None:
            # Probably a builtin module, just ignore in that case.
            return ''

        index = self._name.start_pos[0] - 1
        start_index = max(index - before, 0)
        return ''.join(lines[start_index:index + after + 1])

    def _get_signatures(self, for_docstring=False):
        if self._name.api_type == 'property':
            return []
        if for_docstring and self._name.api_type == 'statement' and not self.is_stub():
            # For docstrings we don't resolve signatures if they are simple
            # statements and not stubs. This is a speed optimization.
            return []

        if isinstance(self._name, MixedName):
            # While this would eventually happen anyway, it's basically just a
            # shortcut to not infer anything tree related, because it's really
            # not necessary.
            return self._name.infer_compiled_value().get_signatures()

        names = convert_names([self._name], prefer_stubs=True)
        return [sig for name in names for sig in name.infer().get_signatures()]

    def get_signatures(self):
        """
        Returns all potential signatures for a function or a class. Multiple
        signatures are typical if you use Python stubs with ``@overload``.

        :rtype: list of :class:`BaseSignature`
        """
        return [
            BaseSignature(self._inference_state, s)
            for s in self._get_signatures()
        ]

    def execute(self):
        """
        Uses type inference to "execute" this identifier and returns the
        executed objects.

        :rtype: list of :class:`Name`
        """
        return _values_to_definitions(self._name.infer().execute_with_values())

    def get_type_hint(self):
        """
        Returns type hints like ``Iterable[int]`` or ``Union[int, str]``.

        This method might be quite slow, especially for functions. The problem
        is finding executions for those functions to return something like
        ``Callable[[int, str], str]``.

        :rtype: str
        """
        return self._name.infer().get_type_hint()


class Completion(BaseName):
    """
    ``Completion`` objects are returned from :meth:`.Script.complete`. They
    provide additional information about a completion.
    """
    def __init__(self, inference_state, name, stack, like_name_length,
                 is_fuzzy, cached_name=None):
        super().__init__(inference_state, name)

        self._like_name_length = like_name_length
        self._stack = stack
        self._is_fuzzy = is_fuzzy
        self._cached_name = cached_name

        # Completion objects with the same Completion name (which means
        # duplicate items in the completion)
        self._same_name_completions = []

    def _complete(self, like_name):
        append = ''
        if settings.add_bracket_after_function \
                and self.type == 'function':
            append = '('

        name = self._name.get_public_name()
        if like_name:
            name = name[self._like_name_length:]
        return name + append

    @property
    def complete(self):
        """
        Only works with non-fuzzy completions. Returns None if fuzzy
        completions are used.

        Return the rest of the word, e.g. completing ``isinstance``::

            isinstan# <-- Cursor is here

        would return the string 'ce'. It also adds additional stuff, depending
        on your ``settings.py``.

        Assuming the following function definition::

            def foo(param=0):
                pass

        completing ``foo(par`` would give a ``Completion`` which ``complete``
        would be ``am=``.
        """
        if self._is_fuzzy:
            return None
        return self._complete(True)

    @property
    def name_with_symbols(self):
        """
        Similar to :attr:`.name`, but like :attr:`.name` returns also the
        symbols, for example assuming the following function definition::

            def foo(param=0):
                pass

        completing ``foo(`` would give a ``Completion`` which
        ``name_with_symbols`` would be "param=".

        """
        return self._complete(False)

    def docstring(self, raw=False, fast=True):
        """
        Documented under :meth:`BaseName.docstring`.
        """
        if self._like_name_length >= 3:
            # In this case we can just resolve the like name, because we
            # wouldn't load like > 100 Python modules anymore.
            fast = False

        return super().docstring(raw=raw, fast=fast)

    def _get_docstring(self):
        if self._cached_name is not None:
            return completion_cache.get_docstring(
                self._cached_name,
                self._name.get_public_name(),
                lambda: self._get_cache()
            )
        return super()._get_docstring()

    def _get_docstring_signature(self):
        if self._cached_name is not None:
            return completion_cache.get_docstring_signature(
                self._cached_name,
                self._name.get_public_name(),
                lambda: self._get_cache()
            )
        return super()._get_docstring_signature()

    def _get_cache(self):
        return (
            super().type,
            super()._get_docstring_signature(),
            super()._get_docstring(),
        )

    @property
    def type(self):
        """
        Documented under :meth:`BaseName.type`.
        """
        # Purely a speed optimization.
        if self._cached_name is not None:
            return completion_cache.get_type(
                self._cached_name,
                self._name.get_public_name(),
                lambda: self._get_cache()
            )

        return super().type

    def get_completion_prefix_length(self):
        """
        Returns the length of the prefix being completed.
        For example, completing ``isinstance``::

            isinstan# <-- Cursor is here

        would return 8, because len('isinstan') == 8.

        Assuming the following function definition::

            def foo(param=0):
                pass

        completing ``foo(par`` would return 3.
        """
        return self._like_name_length

    def __repr__(self):
        return '<%s: %s>' % (type(self).__name__, self._name.get_public_name())


class Name(BaseName):
    """
    *Name* objects are returned from many different APIs including
    :meth:`.Script.goto` or :meth:`.Script.infer`.
    """
    def __init__(self, inference_state, definition):
        super().__init__(inference_state, definition)

    @memoize_method
    def defined_names(self):
        """
        List sub-definitions (e.g., methods in class).

        :rtype: list of :class:`Name`
        """
        defs = self._name.infer()
        return sorted(
            unite(defined_names(self._inference_state, d) for d in defs),
            key=lambda s: s._name.start_pos or (0, 0)
        )

    def is_definition(self):
        """
        Returns True, if defined as a name in a statement, function or class.
        Returns False, if it's a reference to such a definition.
        """
        if self._name.tree_name is None:
            return True
        else:
            return self._name.tree_name.is_definition()

    def __eq__(self, other):
        return self._name.start_pos == other._name.start_pos \
            and self.module_path == other.module_path \
            and self.name == other.name \
            and self._inference_state == other._inference_state

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self._name.start_pos, self.module_path, self.name, self._inference_state))


class BaseSignature(Name):
    """
    These signatures are returned by :meth:`BaseName.get_signatures`
    calls.
    """
    def __init__(self, inference_state, signature):
        super().__init__(inference_state, signature.name)
        self._signature = signature

    @property
    def params(self):
        """
        Returns definitions for all parameters that a signature defines.
        This includes stuff like ``*args`` and ``**kwargs``.

        :rtype: list of :class:`.ParamName`
        """
        return [ParamName(self._inference_state, n)
                for n in self._signature.get_param_names(resolve_stars=True)]

    def to_string(self):
        """
        Returns a text representation of the signature. This could for example
        look like ``foo(bar, baz: int, **kwargs)``.

        :rtype: str
        """
        return self._signature.to_string()


class Signature(BaseSignature):
    """
    A full signature object is the return value of
    :meth:`.Script.get_signatures`.
    """
    def __init__(self, inference_state, signature, call_details):
        super().__init__(inference_state, signature)
        self._call_details = call_details
        self._signature = signature

    @property
    def index(self):
        """
        Returns the param index of the current cursor position.
        Returns None if the index cannot be found in the curent call.

        :rtype: int
        """
        return self._call_details.calculate_index(
            self._signature.get_param_names(resolve_stars=True)
        )

    @property
    def bracket_start(self):
        """
        Returns a line/column tuple of the bracket that is responsible for the
        last function call. The first line is 1 and the first column 0.

        :rtype: int, int
        """
        return self._call_details.bracket_leaf.start_pos

    def __repr__(self):
        return '<%s: index=%r %s>' % (
            type(self).__name__,
            self.index,
            self._signature.to_string(),
        )


class ParamName(Name):
    def infer_default(self):
        """
        Returns default values like the ``1`` of ``def foo(x=1):``.

        :rtype: list of :class:`.Name`
        """
        return _values_to_definitions(self._name.infer_default())

    def infer_annotation(self, **kwargs):
        """
        :param execute_annotation: Default True; If False, values are not
            executed and classes are returned instead of instances.
        :rtype: list of :class:`.Name`
        """
        return _values_to_definitions(self._name.infer_annotation(ignore_stars=True, **kwargs))

    def to_string(self):
        """
        Returns a simple representation of a param, like
        ``f: Callable[..., Any]``.

        :rtype: str
        """
        return self._name.to_string()

    @property
    def kind(self):
        """
        Returns an enum instance of :mod:`inspect`'s ``Parameter`` enum.

        :rtype: :py:attr:`inspect.Parameter.kind`
        """
        return self._name.get_kind()

# === NexusCore/openenv\Lib\site-packages\openai\lib\streaming\chat\__init__.py ===
from ._types import (
    ParsedChoiceSnapshot as ParsedChoiceSnapshot,
    ParsedChatCompletionSnapshot as ParsedChatCompletionSnapshot,
    ParsedChatCompletionMessageSnapshot as ParsedChatCompletionMessageSnapshot,
)
from ._events import (
    ChunkEvent as ChunkEvent,
    ContentDoneEvent as ContentDoneEvent,
    RefusalDoneEvent as RefusalDoneEvent,
    ContentDeltaEvent as ContentDeltaEvent,
    RefusalDeltaEvent as RefusalDeltaEvent,
    LogprobsContentDoneEvent as LogprobsContentDoneEvent,
    LogprobsRefusalDoneEvent as LogprobsRefusalDoneEvent,
    ChatCompletionStreamEvent as ChatCompletionStreamEvent,
    LogprobsContentDeltaEvent as LogprobsContentDeltaEvent,
    LogprobsRefusalDeltaEvent as LogprobsRefusalDeltaEvent,
    ParsedChatCompletionSnapshot as ParsedChatCompletionSnapshot,
    FunctionToolCallArgumentsDoneEvent as FunctionToolCallArgumentsDoneEvent,
    FunctionToolCallArgumentsDeltaEvent as FunctionToolCallArgumentsDeltaEvent,
)
from ._completions import (
    ChatCompletionStream as ChatCompletionStream,
    AsyncChatCompletionStream as AsyncChatCompletionStream,
    ChatCompletionStreamState as ChatCompletionStreamState,
    ChatCompletionStreamManager as ChatCompletionStreamManager,
    AsyncChatCompletionStreamManager as AsyncChatCompletionStreamManager,
)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\ncl.py ===
"""
    pygments.lexers.ncl
    ~~~~~~~~~~~~~~~~~~~

    Lexers for NCAR Command Language.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, include, words
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation

__all__ = ['NCLLexer']


class NCLLexer(RegexLexer):
    """
    Lexer for NCL code.
    """
    name = 'NCL'
    aliases = ['ncl']
    filenames = ['*.ncl']
    mimetypes = ['text/ncl']
    url = 'https://www.ncl.ucar.edu'
    version_added = '2.2'

    flags = re.MULTILINE

    tokens = {
        'root': [
            (r';.*\n', Comment),
            include('strings'),
            include('core'),
            (r'[a-zA-Z_]\w*', Name),
            include('nums'),
            (r'[\s]+', Text),
        ],
        'core': [
            # Statements
            (words((
                'begin', 'break', 'continue', 'create', 'defaultapp', 'do',
                'else', 'end', 'external', 'exit', 'True', 'False', 'file', 'function',
                'getvalues', 'graphic', 'group', 'if', 'list', 'load', 'local',
                'new', '_Missing', 'Missing', 'noparent', 'procedure',
                'quit', 'QUIT', 'Quit', 'record', 'return', 'setvalues', 'stop',
                'then', 'while'), prefix=r'\b', suffix=r'\s*\b'),
             Keyword),

            # Data Types
            (words((
                'ubyte', 'uint', 'uint64', 'ulong', 'string', 'byte',
                'character', 'double', 'float', 'integer', 'int64', 'logical',
                'long', 'short', 'ushort', 'enumeric', 'numeric', 'snumeric'),
                prefix=r'\b', suffix=r'\s*\b'),
             Keyword.Type),

            # Operators
            (r'[\%^*+\-/<>]', Operator),

            # punctuation:
            (r'[\[\]():@$!&|.,\\{}]', Punctuation),
            (r'[=:]', Punctuation),

            # Intrinsics
            (words((
                'abs', 'acos', 'addfile', 'addfiles', 'all', 'angmom_atm', 'any',
                'area_conserve_remap', 'area_hi2lores', 'area_poly_sphere',
                'asciiread', 'asciiwrite', 'asin', 'atan', 'atan2', 'attsetvalues',
                'avg', 'betainc', 'bin_avg', 'bin_sum', 'bw_bandpass_filter',
                'cancor', 'cbinread', 'cbinwrite', 'cd_calendar', 'cd_inv_calendar',
                'cdfbin_p', 'cdfbin_pr', 'cdfbin_s', 'cdfbin_xn', 'cdfchi_p',
                'cdfchi_x', 'cdfgam_p', 'cdfgam_x', 'cdfnor_p', 'cdfnor_x',
                'cdft_p', 'cdft_t', 'ceil', 'center_finite_diff',
                'center_finite_diff_n', 'cfftb', 'cfftf', 'cfftf_frq_reorder',
                'charactertodouble', 'charactertofloat', 'charactertointeger',
                'charactertolong', 'charactertoshort', 'charactertostring',
                'chartodouble', 'chartofloat', 'chartoint', 'chartointeger',
                'chartolong', 'chartoshort', 'chartostring', 'chiinv', 'clear',
                'color_index_to_rgba', 'conform', 'conform_dims', 'cos', 'cosh',
                'count_unique_values', 'covcorm', 'covcorm_xy', 'craybinnumrec',
                'craybinrecread', 'create_graphic', 'csa1', 'csa1d', 'csa1s',
                'csa1x', 'csa1xd', 'csa1xs', 'csa2', 'csa2d', 'csa2l', 'csa2ld',
                'csa2ls', 'csa2lx', 'csa2lxd', 'csa2lxs', 'csa2s', 'csa2x',
                'csa2xd', 'csa2xs', 'csa3', 'csa3d', 'csa3l', 'csa3ld', 'csa3ls',
                'csa3lx', 'csa3lxd', 'csa3lxs', 'csa3s', 'csa3x', 'csa3xd',
                'csa3xs', 'csc2s', 'csgetp', 'css2c', 'cssetp', 'cssgrid', 'csstri',
                'csvoro', 'cumsum', 'cz2ccm', 'datatondc', 'day_of_week',
                'day_of_year', 'days_in_month', 'default_fillvalue', 'delete',
                'depth_to_pres', 'destroy', 'determinant', 'dewtemp_trh',
                'dgeevx_lapack', 'dim_acumrun_n', 'dim_avg', 'dim_avg_n',
                'dim_avg_wgt', 'dim_avg_wgt_n', 'dim_cumsum', 'dim_cumsum_n',
                'dim_gamfit_n', 'dim_gbits', 'dim_max', 'dim_max_n', 'dim_median',
                'dim_median_n', 'dim_min', 'dim_min_n', 'dim_num', 'dim_num_n',
                'dim_numrun_n', 'dim_pqsort', 'dim_pqsort_n', 'dim_product',
                'dim_product_n', 'dim_rmsd', 'dim_rmsd_n', 'dim_rmvmean',
                'dim_rmvmean_n', 'dim_rmvmed', 'dim_rmvmed_n', 'dim_spi_n',
                'dim_standardize', 'dim_standardize_n', 'dim_stat4', 'dim_stat4_n',
                'dim_stddev', 'dim_stddev_n', 'dim_sum', 'dim_sum_n', 'dim_sum_wgt',
                'dim_sum_wgt_n', 'dim_variance', 'dim_variance_n', 'dimsizes',
                'doubletobyte', 'doubletochar', 'doubletocharacter',
                'doubletofloat', 'doubletoint', 'doubletointeger', 'doubletolong',
                'doubletoshort', 'dpres_hybrid_ccm', 'dpres_plevel', 'draw',
                'draw_color_palette', 'dsgetp', 'dsgrid2', 'dsgrid2d', 'dsgrid2s',
                'dsgrid3', 'dsgrid3d', 'dsgrid3s', 'dspnt2', 'dspnt2d', 'dspnt2s',
                'dspnt3', 'dspnt3d', 'dspnt3s', 'dssetp', 'dtrend', 'dtrend_msg',
                'dtrend_msg_n', 'dtrend_n', 'dtrend_quadratic',
                'dtrend_quadratic_msg_n', 'dv2uvf', 'dv2uvg', 'dz_height',
                'echo_off', 'echo_on', 'eof2data', 'eof_varimax', 'eofcor',
                'eofcor_pcmsg', 'eofcor_ts', 'eofcov', 'eofcov_pcmsg', 'eofcov_ts',
                'eofunc', 'eofunc_ts', 'eofunc_varimax', 'equiv_sample_size', 'erf',
                'erfc', 'esacr', 'esacv', 'esccr', 'esccv', 'escorc', 'escorc_n',
                'escovc', 'exit', 'exp', 'exp_tapersh', 'exp_tapersh_wgts',
                'exp_tapershC', 'ezfftb', 'ezfftb_n', 'ezfftf', 'ezfftf_n',
                'f2fosh', 'f2foshv', 'f2fsh', 'f2fshv', 'f2gsh', 'f2gshv', 'fabs',
                'fbindirread', 'fbindirwrite', 'fbinnumrec', 'fbinread',
                'fbinrecread', 'fbinrecwrite', 'fbinwrite', 'fft2db', 'fft2df',
                'fftshift', 'fileattdef', 'filechunkdimdef', 'filedimdef',
                'fileexists', 'filegrpdef', 'filevarattdef', 'filevarchunkdef',
                'filevarcompressleveldef', 'filevardef', 'filevardimsizes',
                'filwgts_lancos', 'filwgts_lanczos', 'filwgts_normal',
                'floattobyte', 'floattochar', 'floattocharacter', 'floattoint',
                'floattointeger', 'floattolong', 'floattoshort', 'floor',
                'fluxEddy', 'fo2fsh', 'fo2fshv', 'fourier_info', 'frame', 'fspan',
                'ftcurv', 'ftcurvd', 'ftcurvi', 'ftcurvp', 'ftcurvpi', 'ftcurvps',
                'ftcurvs', 'ftest', 'ftgetp', 'ftkurv', 'ftkurvd', 'ftkurvp',
                'ftkurvpd', 'ftsetp', 'ftsurf', 'g2fsh', 'g2fshv', 'g2gsh',
                'g2gshv', 'gamma', 'gammainc', 'gaus', 'gaus_lobat',
                'gaus_lobat_wgt', 'gc_aangle', 'gc_clkwise', 'gc_dangle',
                'gc_inout', 'gc_latlon', 'gc_onarc', 'gc_pnt2gc', 'gc_qarea',
                'gc_tarea', 'generate_2d_array', 'get_color_index',
                'get_color_rgba', 'get_cpu_time', 'get_isolines', 'get_ncl_version',
                'get_script_name', 'get_script_prefix_name', 'get_sphere_radius',
                'get_unique_values', 'getbitsone', 'getenv', 'getfiledimsizes',
                'getfilegrpnames', 'getfilepath', 'getfilevaratts',
                'getfilevarchunkdimsizes', 'getfilevardims', 'getfilevardimsizes',
                'getfilevarnames', 'getfilevartypes', 'getvaratts', 'getvardims',
                'gradsf', 'gradsg', 'greg2jul', 'grid2triple', 'hlsrgb', 'hsvrgb',
                'hydro', 'hyi2hyo', 'idsfft', 'igradsf', 'igradsg', 'ilapsf',
                'ilapsg', 'ilapvf', 'ilapvg', 'ind', 'ind_resolve', 'int2p',
                'int2p_n', 'integertobyte', 'integertochar', 'integertocharacter',
                'integertoshort', 'inttobyte', 'inttochar', 'inttoshort',
                'inverse_matrix', 'isatt', 'isbigendian', 'isbyte', 'ischar',
                'iscoord', 'isdefined', 'isdim', 'isdimnamed', 'isdouble',
                'isenumeric', 'isfile', 'isfilepresent', 'isfilevar',
                'isfilevaratt', 'isfilevarcoord', 'isfilevardim', 'isfloat',
                'isfunc', 'isgraphic', 'isint', 'isint64', 'isinteger',
                'isleapyear', 'islogical', 'islong', 'ismissing', 'isnan_ieee',
                'isnumeric', 'ispan', 'isproc', 'isshort', 'issnumeric', 'isstring',
                'isubyte', 'isuint', 'isuint64', 'isulong', 'isunlimited',
                'isunsigned', 'isushort', 'isvar', 'jul2greg', 'kmeans_as136',
                'kolsm2_n', 'kron_product', 'lapsf', 'lapsg', 'lapvf', 'lapvg',
                'latlon2utm', 'lclvl', 'lderuvf', 'lderuvg', 'linint1', 'linint1_n',
                'linint2', 'linint2_points', 'linmsg', 'linmsg_n', 'linrood_latwgt',
                'linrood_wgt', 'list_files', 'list_filevars', 'list_hlus',
                'list_procfuncs', 'list_vars', 'ListAppend', 'ListCount',
                'ListGetType', 'ListIndex', 'ListIndexFromName', 'ListPop',
                'ListPush', 'ListSetType', 'loadscript', 'local_max', 'local_min',
                'log', 'log10', 'longtobyte', 'longtochar', 'longtocharacter',
                'longtoint', 'longtointeger', 'longtoshort', 'lspoly', 'lspoly_n',
                'mask', 'max', 'maxind', 'min', 'minind', 'mixed_layer_depth',
                'mixhum_ptd', 'mixhum_ptrh', 'mjo_cross_coh2pha',
                'mjo_cross_segment', 'moc_globe_atl', 'monthday', 'natgrid',
                'natgridd', 'natgrids', 'ncargpath', 'ncargversion', 'ndctodata',
                'ndtooned', 'new', 'NewList', 'ngezlogo', 'nggcog', 'nggetp',
                'nglogo', 'ngsetp', 'NhlAddAnnotation', 'NhlAddData',
                'NhlAddOverlay', 'NhlAddPrimitive', 'NhlAppGetDefaultParentId',
                'NhlChangeWorkstation', 'NhlClassName', 'NhlClearWorkstation',
                'NhlDataPolygon', 'NhlDataPolyline', 'NhlDataPolymarker',
                'NhlDataToNDC', 'NhlDestroy', 'NhlDraw', 'NhlFrame', 'NhlFreeColor',
                'NhlGetBB', 'NhlGetClassResources', 'NhlGetErrorObjectId',
                'NhlGetNamedColorIndex', 'NhlGetParentId',
                'NhlGetParentWorkstation', 'NhlGetWorkspaceObjectId',
                'NhlIsAllocatedColor', 'NhlIsApp', 'NhlIsDataComm', 'NhlIsDataItem',
                'NhlIsDataSpec', 'NhlIsTransform', 'NhlIsView', 'NhlIsWorkstation',
                'NhlName', 'NhlNDCPolygon', 'NhlNDCPolyline', 'NhlNDCPolymarker',
                'NhlNDCToData', 'NhlNewColor', 'NhlNewDashPattern', 'NhlNewMarker',
                'NhlPalGetDefined', 'NhlRemoveAnnotation', 'NhlRemoveData',
                'NhlRemoveOverlay', 'NhlRemovePrimitive', 'NhlSetColor',
                'NhlSetDashPattern', 'NhlSetMarker', 'NhlUpdateData',
                'NhlUpdateWorkstation', 'nice_mnmxintvl', 'nngetaspectd',
                'nngetaspects', 'nngetp', 'nngetsloped', 'nngetslopes', 'nngetwts',
                'nngetwtsd', 'nnpnt', 'nnpntd', 'nnpntend', 'nnpntendd',
                'nnpntinit', 'nnpntinitd', 'nnpntinits', 'nnpnts', 'nnsetp', 'num',
                'obj_anal_ic', 'omega_ccm', 'onedtond', 'overlay', 'paleo_outline',
                'pdfxy_bin', 'poisson_grid_fill', 'pop_remap', 'potmp_insitu_ocn',
                'prcwater_dp', 'pres2hybrid', 'pres_hybrid_ccm', 'pres_sigma',
                'print', 'print_table', 'printFileVarSummary', 'printVarSummary',
                'product', 'pslec', 'pslhor', 'pslhyp', 'qsort', 'rand',
                'random_chi', 'random_gamma', 'random_normal', 'random_setallseed',
                'random_uniform', 'rcm2points', 'rcm2rgrid', 'rdsstoi',
                'read_colormap_file', 'reg_multlin', 'regcoef', 'regCoef_n',
                'regline', 'relhum', 'replace_ieeenan', 'reshape', 'reshape_ind',
                'rgba_to_color_index', 'rgbhls', 'rgbhsv', 'rgbyiq', 'rgrid2rcm',
                'rhomb_trunc', 'rip_cape_2d', 'rip_cape_3d', 'round', 'rtest',
                'runave', 'runave_n', 'set_default_fillvalue', 'set_sphere_radius',
                'setfileoption', 'sfvp2uvf', 'sfvp2uvg', 'shaec', 'shagc',
                'shgetnp', 'shgetp', 'shgrid', 'shorttobyte', 'shorttochar',
                'shorttocharacter', 'show_ascii', 'shsec', 'shsetp', 'shsgc',
                'shsgc_R42', 'sigma2hybrid', 'simpeq', 'simpne', 'sin',
                'sindex_yrmo', 'sinh', 'sizeof', 'sleep', 'smth9', 'snindex_yrmo',
                'solve_linsys', 'span_color_indexes', 'span_color_rgba',
                'sparse_matrix_mult', 'spcorr', 'spcorr_n', 'specx_anal',
                'specxy_anal', 'spei', 'sprintf', 'sprinti', 'sqrt', 'sqsort',
                'srand', 'stat2', 'stat4', 'stat_medrng', 'stat_trim',
                'status_exit', 'stdatmus_p2tdz', 'stdatmus_z2tdp', 'stddev',
                'str_capital', 'str_concat', 'str_fields_count', 'str_get_cols',
                'str_get_dq', 'str_get_field', 'str_get_nl', 'str_get_sq',
                'str_get_tab', 'str_index_of_substr', 'str_insert', 'str_is_blank',
                'str_join', 'str_left_strip', 'str_lower', 'str_match',
                'str_match_ic', 'str_match_ic_regex', 'str_match_ind',
                'str_match_ind_ic', 'str_match_ind_ic_regex', 'str_match_ind_regex',
                'str_match_regex', 'str_right_strip', 'str_split',
                'str_split_by_length', 'str_split_csv', 'str_squeeze', 'str_strip',
                'str_sub_str', 'str_switch', 'str_upper', 'stringtochar',
                'stringtocharacter', 'stringtodouble', 'stringtofloat',
                'stringtoint', 'stringtointeger', 'stringtolong', 'stringtoshort',
                'strlen', 'student_t', 'sum', 'svd_lapack', 'svdcov', 'svdcov_sv',
                'svdstd', 'svdstd_sv', 'system', 'systemfunc', 'tan', 'tanh',
                'taper', 'taper_n', 'tdclrs', 'tdctri', 'tdcudp', 'tdcurv',
                'tddtri', 'tdez2d', 'tdez3d', 'tdgetp', 'tdgrds', 'tdgrid',
                'tdgtrs', 'tdinit', 'tditri', 'tdlbla', 'tdlblp', 'tdlbls',
                'tdline', 'tdlndp', 'tdlnpa', 'tdlpdp', 'tdmtri', 'tdotri',
                'tdpara', 'tdplch', 'tdprpa', 'tdprpi', 'tdprpt', 'tdsetp',
                'tdsort', 'tdstri', 'tdstrs', 'tdttri', 'thornthwaite', 'tobyte',
                'tochar', 'todouble', 'tofloat', 'toint', 'toint64', 'tointeger',
                'tolong', 'toshort', 'tosigned', 'tostring', 'tostring_with_format',
                'totype', 'toubyte', 'touint', 'touint64', 'toulong', 'tounsigned',
                'toushort', 'trend_manken', 'tri_trunc', 'triple2grid',
                'triple2grid2d', 'trop_wmo', 'ttest', 'typeof', 'undef',
                'unique_string', 'update', 'ushorttoint', 'ut_calendar',
                'ut_inv_calendar', 'utm2latlon', 'uv2dv_cfd', 'uv2dvf', 'uv2dvg',
                'uv2sfvpf', 'uv2sfvpg', 'uv2vr_cfd', 'uv2vrdvf', 'uv2vrdvg',
                'uv2vrf', 'uv2vrg', 'v5d_close', 'v5d_create', 'v5d_setLowLev',
                'v5d_setUnits', 'v5d_write', 'v5d_write_var', 'variance', 'vhaec',
                'vhagc', 'vhsec', 'vhsgc', 'vibeta', 'vinth2p', 'vinth2p_ecmwf',
                'vinth2p_ecmwf_nodes', 'vinth2p_nodes', 'vintp2p_ecmwf', 'vr2uvf',
                'vr2uvg', 'vrdv2uvf', 'vrdv2uvg', 'wavelet', 'wavelet_default',
                'weibull', 'wgt_area_smooth', 'wgt_areaave', 'wgt_areaave2',
                'wgt_arearmse', 'wgt_arearmse2', 'wgt_areasum2', 'wgt_runave',
                'wgt_runave_n', 'wgt_vert_avg_beta', 'wgt_volave', 'wgt_volave_ccm',
                'wgt_volrmse', 'wgt_volrmse_ccm', 'where', 'wk_smooth121', 'wmbarb',
                'wmbarbmap', 'wmdrft', 'wmgetp', 'wmlabs', 'wmsetp', 'wmstnm',
                'wmvect', 'wmvectmap', 'wmvlbl', 'wrf_avo', 'wrf_cape_2d',
                'wrf_cape_3d', 'wrf_dbz', 'wrf_eth', 'wrf_helicity', 'wrf_ij_to_ll',
                'wrf_interp_1d', 'wrf_interp_2d_xy', 'wrf_interp_3d_z',
                'wrf_latlon_to_ij', 'wrf_ll_to_ij', 'wrf_omega', 'wrf_pvo',
                'wrf_rh', 'wrf_slp', 'wrf_smooth_2d', 'wrf_td', 'wrf_tk',
                'wrf_updraft_helicity', 'wrf_uvmet', 'wrf_virtual_temp',
                'wrf_wetbulb', 'wrf_wps_close_int', 'wrf_wps_open_int',
                'wrf_wps_rddata_int', 'wrf_wps_rdhead_int', 'wrf_wps_read_int',
                'wrf_wps_write_int', 'write_matrix', 'write_table', 'yiqrgb',
                'z2geouv', 'zonal_mpsi', 'addfiles_GetVar', 'advect_variable',
                'area_conserve_remap_Wrap', 'area_hi2lores_Wrap',
                'array_append_record', 'assignFillValue', 'byte2flt',
                'byte2flt_hdf', 'calcDayAnomTLL', 'calcMonAnomLLLT',
                'calcMonAnomLLT', 'calcMonAnomTLL', 'calcMonAnomTLLL',
                'calculate_monthly_values', 'cd_convert', 'changeCase',
                'changeCaseChar', 'clmDayTLL', 'clmDayTLLL', 'clmMon2clmDay',
                'clmMonLLLT', 'clmMonLLT', 'clmMonTLL', 'clmMonTLLL', 'closest_val',
                'copy_VarAtts', 'copy_VarCoords', 'copy_VarCoords_1',
                'copy_VarCoords_2', 'copy_VarMeta', 'copyatt', 'crossp3',
                'cshstringtolist', 'cssgrid_Wrap', 'dble2flt', 'decimalPlaces',
                'delete_VarAtts', 'dim_avg_n_Wrap', 'dim_avg_wgt_n_Wrap',
                'dim_avg_wgt_Wrap', 'dim_avg_Wrap', 'dim_cumsum_n_Wrap',
                'dim_cumsum_Wrap', 'dim_max_n_Wrap', 'dim_min_n_Wrap',
                'dim_rmsd_n_Wrap', 'dim_rmsd_Wrap', 'dim_rmvmean_n_Wrap',
                'dim_rmvmean_Wrap', 'dim_rmvmed_n_Wrap', 'dim_rmvmed_Wrap',
                'dim_standardize_n_Wrap', 'dim_standardize_Wrap',
                'dim_stddev_n_Wrap', 'dim_stddev_Wrap', 'dim_sum_n_Wrap',
                'dim_sum_wgt_n_Wrap', 'dim_sum_wgt_Wrap', 'dim_sum_Wrap',
                'dim_variance_n_Wrap', 'dim_variance_Wrap', 'dpres_plevel_Wrap',
                'dtrend_leftdim', 'dv2uvF_Wrap', 'dv2uvG_Wrap', 'eof_north',
                'eofcor_Wrap', 'eofcov_Wrap', 'eofunc_north', 'eofunc_ts_Wrap',
                'eofunc_varimax_reorder', 'eofunc_varimax_Wrap', 'eofunc_Wrap',
                'epsZero', 'f2fosh_Wrap', 'f2foshv_Wrap', 'f2fsh_Wrap',
                'f2fshv_Wrap', 'f2gsh_Wrap', 'f2gshv_Wrap', 'fbindirSwap',
                'fbinseqSwap1', 'fbinseqSwap2', 'flt2dble', 'flt2string',
                'fo2fsh_Wrap', 'fo2fshv_Wrap', 'g2fsh_Wrap', 'g2fshv_Wrap',
                'g2gsh_Wrap', 'g2gshv_Wrap', 'generate_resample_indices',
                'generate_sample_indices', 'generate_unique_indices',
                'genNormalDist', 'get1Dindex', 'get1Dindex_Collapse',
                'get1Dindex_Exclude', 'get_file_suffix', 'GetFillColor',
                'GetFillColorIndex', 'getFillValue', 'getind_latlon2d',
                'getVarDimNames', 'getVarFillValue', 'grib_stime2itime',
                'hyi2hyo_Wrap', 'ilapsF_Wrap', 'ilapsG_Wrap', 'ind_nearest_coord',
                'indStrSubset', 'int2dble', 'int2flt', 'int2p_n_Wrap', 'int2p_Wrap',
                'isMonotonic', 'isStrSubset', 'latGau', 'latGauWgt', 'latGlobeF',
                'latGlobeFo', 'latRegWgt', 'linint1_n_Wrap', 'linint1_Wrap',
                'linint2_points_Wrap', 'linint2_Wrap', 'local_max_1d',
                'local_min_1d', 'lonFlip', 'lonGlobeF', 'lonGlobeFo', 'lonPivot',
                'merge_levels_sfc', 'mod', 'month_to_annual',
                'month_to_annual_weighted', 'month_to_season', 'month_to_season12',
                'month_to_seasonN', 'monthly_total_to_daily_mean', 'nameDim',
                'natgrid_Wrap', 'NewCosWeight', 'niceLatLon2D', 'NormCosWgtGlobe',
                'numAsciiCol', 'numAsciiRow', 'numeric2int',
                'obj_anal_ic_deprecated', 'obj_anal_ic_Wrap', 'omega_ccm_driver',
                'omega_to_w', 'oneDtostring', 'pack_values', 'pattern_cor', 'pdfx',
                'pdfxy', 'pdfxy_conform', 'pot_temp', 'pot_vort_hybrid',
                'pot_vort_isobaric', 'pres2hybrid_Wrap', 'print_clock',
                'printMinMax', 'quadroots', 'rcm2points_Wrap', 'rcm2rgrid_Wrap',
                'readAsciiHead', 'readAsciiTable', 'reg_multlin_stats',
                'region_ind', 'regline_stats', 'relhum_ttd', 'replaceSingleChar',
                'RGBtoCmap', 'rgrid2rcm_Wrap', 'rho_mwjf', 'rm_single_dims',
                'rmAnnCycle1D', 'rmInsufData', 'rmMonAnnCycLLLT', 'rmMonAnnCycLLT',
                'rmMonAnnCycTLL', 'runave_n_Wrap', 'runave_Wrap', 'short2flt',
                'short2flt_hdf', 'shsgc_R42_Wrap', 'sign_f90', 'sign_matlab',
                'smth9_Wrap', 'smthClmDayTLL', 'smthClmDayTLLL', 'SqrtCosWeight',
                'stat_dispersion', 'static_stability', 'stdMonLLLT', 'stdMonLLT',
                'stdMonTLL', 'stdMonTLLL', 'symMinMaxPlt', 'table_attach_columns',
                'table_attach_rows', 'time_to_newtime', 'transpose',
                'triple2grid_Wrap', 'ut_convert', 'uv2dvF_Wrap', 'uv2dvG_Wrap',
                'uv2vrF_Wrap', 'uv2vrG_Wrap', 'vr2uvF_Wrap', 'vr2uvG_Wrap',
                'w_to_omega', 'wallClockElapseTime', 'wave_number_spc',
                'wgt_areaave_Wrap', 'wgt_runave_leftdim', 'wgt_runave_n_Wrap',
                'wgt_runave_Wrap', 'wgt_vertical_n', 'wind_component',
                'wind_direction', 'yyyyddd_to_yyyymmdd', 'yyyymm_time',
                'yyyymm_to_yyyyfrac', 'yyyymmdd_time', 'yyyymmdd_to_yyyyddd',
                'yyyymmdd_to_yyyyfrac', 'yyyymmddhh_time', 'yyyymmddhh_to_yyyyfrac',
                'zonal_mpsi_Wrap', 'zonalAve', 'calendar_decode2', 'cd_string',
                'kf_filter', 'run_cor', 'time_axis_labels', 'ut_string',
                'wrf_contour', 'wrf_map', 'wrf_map_overlay', 'wrf_map_overlays',
                'wrf_map_resources', 'wrf_map_zoom', 'wrf_overlay', 'wrf_overlays',
                'wrf_user_getvar', 'wrf_user_ij_to_ll', 'wrf_user_intrp2d',
                'wrf_user_intrp3d', 'wrf_user_latlon_to_ij', 'wrf_user_list_times',
                'wrf_user_ll_to_ij', 'wrf_user_unstagger', 'wrf_user_vert_interp',
                'wrf_vector', 'gsn_add_annotation', 'gsn_add_polygon',
                'gsn_add_polyline', 'gsn_add_polymarker',
                'gsn_add_shapefile_polygons', 'gsn_add_shapefile_polylines',
                'gsn_add_shapefile_polymarkers', 'gsn_add_text', 'gsn_attach_plots',
                'gsn_blank_plot', 'gsn_contour', 'gsn_contour_map',
                'gsn_contour_shade', 'gsn_coordinates', 'gsn_create_labelbar',
                'gsn_create_legend', 'gsn_create_text',
                'gsn_csm_attach_zonal_means', 'gsn_csm_blank_plot',
                'gsn_csm_contour', 'gsn_csm_contour_map', 'gsn_csm_contour_map_ce',
                'gsn_csm_contour_map_overlay', 'gsn_csm_contour_map_polar',
                'gsn_csm_hov', 'gsn_csm_lat_time', 'gsn_csm_map', 'gsn_csm_map_ce',
                'gsn_csm_map_polar', 'gsn_csm_pres_hgt',
                'gsn_csm_pres_hgt_streamline', 'gsn_csm_pres_hgt_vector',
                'gsn_csm_streamline', 'gsn_csm_streamline_contour_map',
                'gsn_csm_streamline_contour_map_ce',
                'gsn_csm_streamline_contour_map_polar', 'gsn_csm_streamline_map',
                'gsn_csm_streamline_map_ce', 'gsn_csm_streamline_map_polar',
                'gsn_csm_streamline_scalar', 'gsn_csm_streamline_scalar_map',
                'gsn_csm_streamline_scalar_map_ce',
                'gsn_csm_streamline_scalar_map_polar', 'gsn_csm_time_lat',
                'gsn_csm_vector', 'gsn_csm_vector_map', 'gsn_csm_vector_map_ce',
                'gsn_csm_vector_map_polar', 'gsn_csm_vector_scalar',
                'gsn_csm_vector_scalar_map', 'gsn_csm_vector_scalar_map_ce',
                'gsn_csm_vector_scalar_map_polar', 'gsn_csm_x2y', 'gsn_csm_x2y2',
                'gsn_csm_xy', 'gsn_csm_xy2', 'gsn_csm_xy3', 'gsn_csm_y',
                'gsn_define_colormap', 'gsn_draw_colormap', 'gsn_draw_named_colors',
                'gsn_histogram', 'gsn_labelbar_ndc', 'gsn_legend_ndc', 'gsn_map',
                'gsn_merge_colormaps', 'gsn_open_wks', 'gsn_panel', 'gsn_polygon',
                'gsn_polygon_ndc', 'gsn_polyline', 'gsn_polyline_ndc',
                'gsn_polymarker', 'gsn_polymarker_ndc', 'gsn_retrieve_colormap',
                'gsn_reverse_colormap', 'gsn_streamline', 'gsn_streamline_map',
                'gsn_streamline_scalar', 'gsn_streamline_scalar_map', 'gsn_table',
                'gsn_text', 'gsn_text_ndc', 'gsn_vector', 'gsn_vector_map',
                'gsn_vector_scalar', 'gsn_vector_scalar_map', 'gsn_xy', 'gsn_y',
                'hsv2rgb', 'maximize_output', 'namedcolor2rgb', 'namedcolor2rgba',
                'reset_device_coordinates', 'span_named_colors'), prefix=r'\b'),
             Name.Builtin),

            # Resources
            (words((
                'amDataXF', 'amDataYF', 'amJust', 'amOn', 'amOrthogonalPosF',
                'amParallelPosF', 'amResizeNotify', 'amSide', 'amTrackData',
                'amViewId', 'amZone', 'appDefaultParent', 'appFileSuffix',
                'appResources', 'appSysDir', 'appUsrDir', 'caCopyArrays',
                'caXArray', 'caXCast', 'caXMaxV', 'caXMinV', 'caXMissingV',
                'caYArray', 'caYCast', 'caYMaxV', 'caYMinV', 'caYMissingV',
                'cnCellFillEdgeColor', 'cnCellFillMissingValEdgeColor',
                'cnConpackParams', 'cnConstFEnableFill', 'cnConstFLabelAngleF',
                'cnConstFLabelBackgroundColor', 'cnConstFLabelConstantSpacingF',
                'cnConstFLabelFont', 'cnConstFLabelFontAspectF',
                'cnConstFLabelFontColor', 'cnConstFLabelFontHeightF',
                'cnConstFLabelFontQuality', 'cnConstFLabelFontThicknessF',
                'cnConstFLabelFormat', 'cnConstFLabelFuncCode', 'cnConstFLabelJust',
                'cnConstFLabelOn', 'cnConstFLabelOrthogonalPosF',
                'cnConstFLabelParallelPosF', 'cnConstFLabelPerimColor',
                'cnConstFLabelPerimOn', 'cnConstFLabelPerimSpaceF',
                'cnConstFLabelPerimThicknessF', 'cnConstFLabelSide',
                'cnConstFLabelString', 'cnConstFLabelTextDirection',
                'cnConstFLabelZone', 'cnConstFUseInfoLabelRes',
                'cnExplicitLabelBarLabelsOn', 'cnExplicitLegendLabelsOn',
                'cnExplicitLineLabelsOn', 'cnFillBackgroundColor', 'cnFillColor',
                'cnFillColors', 'cnFillDotSizeF', 'cnFillDrawOrder', 'cnFillMode',
                'cnFillOn', 'cnFillOpacityF', 'cnFillPalette', 'cnFillPattern',
                'cnFillPatterns', 'cnFillScaleF', 'cnFillScales', 'cnFixFillBleed',
                'cnGridBoundFillColor', 'cnGridBoundFillPattern',
                'cnGridBoundFillScaleF', 'cnGridBoundPerimColor',
                'cnGridBoundPerimDashPattern', 'cnGridBoundPerimOn',
                'cnGridBoundPerimThicknessF', 'cnHighLabelAngleF',
                'cnHighLabelBackgroundColor', 'cnHighLabelConstantSpacingF',
                'cnHighLabelCount', 'cnHighLabelFont', 'cnHighLabelFontAspectF',
                'cnHighLabelFontColor', 'cnHighLabelFontHeightF',
                'cnHighLabelFontQuality', 'cnHighLabelFontThicknessF',
                'cnHighLabelFormat', 'cnHighLabelFuncCode', 'cnHighLabelPerimColor',
                'cnHighLabelPerimOn', 'cnHighLabelPerimSpaceF',
                'cnHighLabelPerimThicknessF', 'cnHighLabelString', 'cnHighLabelsOn',
                'cnHighLowLabelOverlapMode', 'cnHighUseLineLabelRes',
                'cnInfoLabelAngleF', 'cnInfoLabelBackgroundColor',
                'cnInfoLabelConstantSpacingF', 'cnInfoLabelFont',
                'cnInfoLabelFontAspectF', 'cnInfoLabelFontColor',
                'cnInfoLabelFontHeightF', 'cnInfoLabelFontQuality',
                'cnInfoLabelFontThicknessF', 'cnInfoLabelFormat',
                'cnInfoLabelFuncCode', 'cnInfoLabelJust', 'cnInfoLabelOn',
                'cnInfoLabelOrthogonalPosF', 'cnInfoLabelParallelPosF',
                'cnInfoLabelPerimColor', 'cnInfoLabelPerimOn',
                'cnInfoLabelPerimSpaceF', 'cnInfoLabelPerimThicknessF',
                'cnInfoLabelSide', 'cnInfoLabelString', 'cnInfoLabelTextDirection',
                'cnInfoLabelZone', 'cnLabelBarEndLabelsOn', 'cnLabelBarEndStyle',
                'cnLabelDrawOrder', 'cnLabelMasking', 'cnLabelScaleFactorF',
                'cnLabelScaleValueF', 'cnLabelScalingMode', 'cnLegendLevelFlags',
                'cnLevelCount', 'cnLevelFlag', 'cnLevelFlags', 'cnLevelSelectionMode',
                'cnLevelSpacingF', 'cnLevels', 'cnLineColor', 'cnLineColors',
                'cnLineDashPattern', 'cnLineDashPatterns', 'cnLineDashSegLenF',
                'cnLineDrawOrder', 'cnLineLabelAngleF', 'cnLineLabelBackgroundColor',
                'cnLineLabelConstantSpacingF', 'cnLineLabelCount',
                'cnLineLabelDensityF', 'cnLineLabelFont', 'cnLineLabelFontAspectF',
                'cnLineLabelFontColor', 'cnLineLabelFontColors',
                'cnLineLabelFontHeightF', 'cnLineLabelFontQuality',
                'cnLineLabelFontThicknessF', 'cnLineLabelFormat',
                'cnLineLabelFuncCode', 'cnLineLabelInterval', 'cnLineLabelPerimColor',
                'cnLineLabelPerimOn', 'cnLineLabelPerimSpaceF',
                'cnLineLabelPerimThicknessF', 'cnLineLabelPlacementMode',
                'cnLineLabelStrings', 'cnLineLabelsOn', 'cnLinePalette',
                'cnLineThicknessF', 'cnLineThicknesses', 'cnLinesOn',
                'cnLowLabelAngleF', 'cnLowLabelBackgroundColor',
                'cnLowLabelConstantSpacingF', 'cnLowLabelCount', 'cnLowLabelFont',
                'cnLowLabelFontAspectF', 'cnLowLabelFontColor',
                'cnLowLabelFontHeightF', 'cnLowLabelFontQuality',
                'cnLowLabelFontThicknessF', 'cnLowLabelFormat', 'cnLowLabelFuncCode',
                'cnLowLabelPerimColor', 'cnLowLabelPerimOn', 'cnLowLabelPerimSpaceF',
                'cnLowLabelPerimThicknessF', 'cnLowLabelString', 'cnLowLabelsOn',
                'cnLowUseHighLabelRes', 'cnMaxDataValueFormat', 'cnMaxLevelCount',
                'cnMaxLevelValF', 'cnMaxPointDistanceF', 'cnMinLevelValF',
                'cnMissingValFillColor', 'cnMissingValFillPattern',
                'cnMissingValFillScaleF', 'cnMissingValPerimColor',
                'cnMissingValPerimDashPattern', 'cnMissingValPerimGridBoundOn',
                'cnMissingValPerimOn', 'cnMissingValPerimThicknessF',
                'cnMonoFillColor', 'cnMonoFillPattern', 'cnMonoFillScale',
                'cnMonoLevelFlag', 'cnMonoLineColor', 'cnMonoLineDashPattern',
                'cnMonoLineLabelFontColor', 'cnMonoLineThickness', 'cnNoDataLabelOn',
                'cnNoDataLabelString', 'cnOutOfRangeFillColor',
                'cnOutOfRangeFillPattern', 'cnOutOfRangeFillScaleF',
                'cnOutOfRangePerimColor', 'cnOutOfRangePerimDashPattern',
                'cnOutOfRangePerimOn', 'cnOutOfRangePerimThicknessF',
                'cnRasterCellSizeF', 'cnRasterMinCellSizeF', 'cnRasterModeOn',
                'cnRasterSampleFactorF', 'cnRasterSmoothingOn', 'cnScalarFieldData',
                'cnSmoothingDistanceF', 'cnSmoothingOn', 'cnSmoothingTensionF',
                'cnSpanFillPalette', 'cnSpanLinePalette', 'ctCopyTables',
                'ctXElementSize', 'ctXMaxV', 'ctXMinV', 'ctXMissingV', 'ctXTable',
                'ctXTableLengths', 'ctXTableType', 'ctYElementSize', 'ctYMaxV',
                'ctYMinV', 'ctYMissingV', 'ctYTable', 'ctYTableLengths',
                'ctYTableType', 'dcDelayCompute', 'errBuffer',
                'errFileName', 'errFilePtr', 'errLevel', 'errPrint', 'errUnitNumber',
                'gsClipOn', 'gsColors', 'gsEdgeColor', 'gsEdgeDashPattern',
                'gsEdgeDashSegLenF', 'gsEdgeThicknessF', 'gsEdgesOn',
                'gsFillBackgroundColor', 'gsFillColor', 'gsFillDotSizeF',
                'gsFillIndex', 'gsFillLineThicknessF', 'gsFillOpacityF',
                'gsFillScaleF', 'gsFont', 'gsFontAspectF', 'gsFontColor',
                'gsFontHeightF', 'gsFontOpacityF', 'gsFontQuality',
                'gsFontThicknessF', 'gsLineColor', 'gsLineDashPattern',
                'gsLineDashSegLenF', 'gsLineLabelConstantSpacingF', 'gsLineLabelFont',
                'gsLineLabelFontAspectF', 'gsLineLabelFontColor',
                'gsLineLabelFontHeightF', 'gsLineLabelFontQuality',
                'gsLineLabelFontThicknessF', 'gsLineLabelFuncCode',
                'gsLineLabelString', 'gsLineOpacityF', 'gsLineThicknessF',
                'gsMarkerColor', 'gsMarkerIndex', 'gsMarkerOpacityF', 'gsMarkerSizeF',
                'gsMarkerThicknessF', 'gsSegments', 'gsTextAngleF',
                'gsTextConstantSpacingF', 'gsTextDirection', 'gsTextFuncCode',
                'gsTextJustification', 'gsnAboveYRefLineBarColors',
                'gsnAboveYRefLineBarFillScales', 'gsnAboveYRefLineBarPatterns',
                'gsnAboveYRefLineColor', 'gsnAddCyclic', 'gsnAttachBorderOn',
                'gsnAttachPlotsXAxis', 'gsnBelowYRefLineBarColors',
                'gsnBelowYRefLineBarFillScales', 'gsnBelowYRefLineBarPatterns',
                'gsnBelowYRefLineColor', 'gsnBoxMargin', 'gsnCenterString',
                'gsnCenterStringFontColor', 'gsnCenterStringFontHeightF',
                'gsnCenterStringFuncCode', 'gsnCenterStringOrthogonalPosF',
                'gsnCenterStringParallelPosF', 'gsnContourLineThicknessesScale',
                'gsnContourNegLineDashPattern', 'gsnContourPosLineDashPattern',
                'gsnContourZeroLineThicknessF', 'gsnDebugWriteFileName', 'gsnDraw',
                'gsnFrame', 'gsnHistogramBarWidthPercent', 'gsnHistogramBinIntervals',
                'gsnHistogramBinMissing', 'gsnHistogramBinWidth',
                'gsnHistogramClassIntervals', 'gsnHistogramCompare',
                'gsnHistogramComputePercentages',
                'gsnHistogramComputePercentagesNoMissing',
                'gsnHistogramDiscreteBinValues', 'gsnHistogramDiscreteClassValues',
                'gsnHistogramHorizontal', 'gsnHistogramMinMaxBinsOn',
                'gsnHistogramNumberOfBins', 'gsnHistogramPercentSign',
                'gsnHistogramSelectNiceIntervals', 'gsnLeftString',
                'gsnLeftStringFontColor', 'gsnLeftStringFontHeightF',
                'gsnLeftStringFuncCode', 'gsnLeftStringOrthogonalPosF',
                'gsnLeftStringParallelPosF', 'gsnMajorLatSpacing',
                'gsnMajorLonSpacing', 'gsnMaskLambertConformal',
                'gsnMaskLambertConformalOutlineOn', 'gsnMaximize',
                'gsnMinorLatSpacing', 'gsnMinorLonSpacing', 'gsnPanelBottom',
                'gsnPanelCenter', 'gsnPanelDebug', 'gsnPanelFigureStrings',
                'gsnPanelFigureStringsBackgroundFillColor',
                'gsnPanelFigureStringsFontHeightF', 'gsnPanelFigureStringsJust',
                'gsnPanelFigureStringsPerimOn', 'gsnPanelLabelBar', 'gsnPanelLeft',
                'gsnPanelMainFont', 'gsnPanelMainFontColor',
                'gsnPanelMainFontHeightF', 'gsnPanelMainString', 'gsnPanelRight',
                'gsnPanelRowSpec', 'gsnPanelScalePlotIndex', 'gsnPanelTop',
                'gsnPanelXF', 'gsnPanelXWhiteSpacePercent', 'gsnPanelYF',
                'gsnPanelYWhiteSpacePercent', 'gsnPaperHeight', 'gsnPaperMargin',
                'gsnPaperOrientation', 'gsnPaperWidth', 'gsnPolar',
                'gsnPolarLabelDistance', 'gsnPolarLabelFont',
                'gsnPolarLabelFontHeightF', 'gsnPolarLabelSpacing', 'gsnPolarTime',
                'gsnPolarUT', 'gsnRightString', 'gsnRightStringFontColor',
                'gsnRightStringFontHeightF', 'gsnRightStringFuncCode',
                'gsnRightStringOrthogonalPosF', 'gsnRightStringParallelPosF',
                'gsnScalarContour', 'gsnScale', 'gsnShape', 'gsnSpreadColorEnd',
                'gsnSpreadColorStart', 'gsnSpreadColors', 'gsnStringFont',
                'gsnStringFontColor', 'gsnStringFontHeightF', 'gsnStringFuncCode',
                'gsnTickMarksOn', 'gsnXAxisIrregular2Linear', 'gsnXAxisIrregular2Log',
                'gsnXRefLine', 'gsnXRefLineColor', 'gsnXRefLineDashPattern',
                'gsnXRefLineThicknessF', 'gsnXYAboveFillColors', 'gsnXYBarChart',
                'gsnXYBarChartBarWidth', 'gsnXYBarChartColors',
                'gsnXYBarChartColors2', 'gsnXYBarChartFillDotSizeF',
                'gsnXYBarChartFillLineThicknessF', 'gsnXYBarChartFillOpacityF',
                'gsnXYBarChartFillScaleF', 'gsnXYBarChartOutlineOnly',
                'gsnXYBarChartOutlineThicknessF', 'gsnXYBarChartPatterns',
                'gsnXYBarChartPatterns2', 'gsnXYBelowFillColors', 'gsnXYFillColors',
                'gsnXYFillOpacities', 'gsnXYLeftFillColors', 'gsnXYRightFillColors',
                'gsnYAxisIrregular2Linear', 'gsnYAxisIrregular2Log', 'gsnYRefLine',
                'gsnYRefLineColor', 'gsnYRefLineColors', 'gsnYRefLineDashPattern',
                'gsnYRefLineDashPatterns', 'gsnYRefLineThicknessF',
                'gsnYRefLineThicknesses', 'gsnZonalMean', 'gsnZonalMeanXMaxF',
                'gsnZonalMeanXMinF', 'gsnZonalMeanYRefLine', 'lbAutoManage',
                'lbBottomMarginF', 'lbBoxCount', 'lbBoxEndCapStyle', 'lbBoxFractions',
                'lbBoxLineColor', 'lbBoxLineDashPattern', 'lbBoxLineDashSegLenF',
                'lbBoxLineThicknessF', 'lbBoxLinesOn', 'lbBoxMajorExtentF',
                'lbBoxMinorExtentF', 'lbBoxSeparatorLinesOn', 'lbBoxSizing',
                'lbFillBackground', 'lbFillColor', 'lbFillColors', 'lbFillDotSizeF',
                'lbFillLineThicknessF', 'lbFillPattern', 'lbFillPatterns',
                'lbFillScaleF', 'lbFillScales', 'lbJustification', 'lbLabelAlignment',
                'lbLabelAngleF', 'lbLabelAutoStride', 'lbLabelBarOn',
                'lbLabelConstantSpacingF', 'lbLabelDirection', 'lbLabelFont',
                'lbLabelFontAspectF', 'lbLabelFontColor', 'lbLabelFontHeightF',
                'lbLabelFontQuality', 'lbLabelFontThicknessF', 'lbLabelFuncCode',
                'lbLabelJust', 'lbLabelOffsetF', 'lbLabelPosition', 'lbLabelStride',
                'lbLabelStrings', 'lbLabelsOn', 'lbLeftMarginF', 'lbMaxLabelLenF',
                'lbMinLabelSpacingF', 'lbMonoFillColor', 'lbMonoFillPattern',
                'lbMonoFillScale', 'lbOrientation', 'lbPerimColor',
                'lbPerimDashPattern', 'lbPerimDashSegLenF', 'lbPerimFill',
                'lbPerimFillColor', 'lbPerimOn', 'lbPerimThicknessF',
                'lbRasterFillOn', 'lbRightMarginF', 'lbTitleAngleF',
                'lbTitleConstantSpacingF', 'lbTitleDirection', 'lbTitleExtentF',
                'lbTitleFont', 'lbTitleFontAspectF', 'lbTitleFontColor',
                'lbTitleFontHeightF', 'lbTitleFontQuality', 'lbTitleFontThicknessF',
                'lbTitleFuncCode', 'lbTitleJust', 'lbTitleOffsetF', 'lbTitleOn',
                'lbTitlePosition', 'lbTitleString', 'lbTopMarginF', 'lgAutoManage',
                'lgBottomMarginF', 'lgBoxBackground', 'lgBoxLineColor',
                'lgBoxLineDashPattern', 'lgBoxLineDashSegLenF', 'lgBoxLineThicknessF',
                'lgBoxLinesOn', 'lgBoxMajorExtentF', 'lgBoxMinorExtentF',
                'lgDashIndex', 'lgDashIndexes', 'lgItemCount', 'lgItemOrder',
                'lgItemPlacement', 'lgItemPositions', 'lgItemType', 'lgItemTypes',
                'lgJustification', 'lgLabelAlignment', 'lgLabelAngleF',
                'lgLabelAutoStride', 'lgLabelConstantSpacingF', 'lgLabelDirection',
                'lgLabelFont', 'lgLabelFontAspectF', 'lgLabelFontColor',
                'lgLabelFontHeightF', 'lgLabelFontQuality', 'lgLabelFontThicknessF',
                'lgLabelFuncCode', 'lgLabelJust', 'lgLabelOffsetF', 'lgLabelPosition',
                'lgLabelStride', 'lgLabelStrings', 'lgLabelsOn', 'lgLeftMarginF',
                'lgLegendOn', 'lgLineColor', 'lgLineColors', 'lgLineDashSegLenF',
                'lgLineDashSegLens', 'lgLineLabelConstantSpacingF', 'lgLineLabelFont',
                'lgLineLabelFontAspectF', 'lgLineLabelFontColor',
                'lgLineLabelFontColors', 'lgLineLabelFontHeightF',
                'lgLineLabelFontHeights', 'lgLineLabelFontQuality',
                'lgLineLabelFontThicknessF', 'lgLineLabelFuncCode',
                'lgLineLabelStrings', 'lgLineLabelsOn', 'lgLineThicknessF',
                'lgLineThicknesses', 'lgMarkerColor', 'lgMarkerColors',
                'lgMarkerIndex', 'lgMarkerIndexes', 'lgMarkerSizeF', 'lgMarkerSizes',
                'lgMarkerThicknessF', 'lgMarkerThicknesses', 'lgMonoDashIndex',
                'lgMonoItemType', 'lgMonoLineColor', 'lgMonoLineDashSegLen',
                'lgMonoLineLabelFontColor', 'lgMonoLineLabelFontHeight',
                'lgMonoLineThickness', 'lgMonoMarkerColor', 'lgMonoMarkerIndex',
                'lgMonoMarkerSize', 'lgMonoMarkerThickness', 'lgOrientation',
                'lgPerimColor', 'lgPerimDashPattern', 'lgPerimDashSegLenF',
                'lgPerimFill', 'lgPerimFillColor', 'lgPerimOn', 'lgPerimThicknessF',
                'lgRightMarginF', 'lgTitleAngleF', 'lgTitleConstantSpacingF',
                'lgTitleDirection', 'lgTitleExtentF', 'lgTitleFont',
                'lgTitleFontAspectF', 'lgTitleFontColor', 'lgTitleFontHeightF',
                'lgTitleFontQuality', 'lgTitleFontThicknessF', 'lgTitleFuncCode',
                'lgTitleJust', 'lgTitleOffsetF', 'lgTitleOn', 'lgTitlePosition',
                'lgTitleString', 'lgTopMarginF', 'mpAreaGroupCount',
                'mpAreaMaskingOn', 'mpAreaNames', 'mpAreaTypes', 'mpBottomAngleF',
                'mpBottomMapPosF', 'mpBottomNDCF', 'mpBottomNPCF',
                'mpBottomPointLatF', 'mpBottomPointLonF', 'mpBottomWindowF',
                'mpCenterLatF', 'mpCenterLonF', 'mpCenterRotF', 'mpCountyLineColor',
                'mpCountyLineDashPattern', 'mpCountyLineDashSegLenF',
                'mpCountyLineThicknessF', 'mpDataBaseVersion', 'mpDataResolution',
                'mpDataSetName', 'mpDefaultFillColor', 'mpDefaultFillPattern',
                'mpDefaultFillScaleF', 'mpDynamicAreaGroups', 'mpEllipticalBoundary',
                'mpFillAreaSpecifiers', 'mpFillBoundarySets', 'mpFillColor',
                'mpFillColors', 'mpFillColors-default', 'mpFillDotSizeF',
                'mpFillDrawOrder', 'mpFillOn', 'mpFillPatternBackground',
                'mpFillPattern', 'mpFillPatterns', 'mpFillPatterns-default',
                'mpFillScaleF', 'mpFillScales', 'mpFillScales-default',
                'mpFixedAreaGroups', 'mpGeophysicalLineColor',
                'mpGeophysicalLineDashPattern', 'mpGeophysicalLineDashSegLenF',
                'mpGeophysicalLineThicknessF', 'mpGreatCircleLinesOn',
                'mpGridAndLimbDrawOrder', 'mpGridAndLimbOn', 'mpGridLatSpacingF',
                'mpGridLineColor', 'mpGridLineDashPattern', 'mpGridLineDashSegLenF',
                'mpGridLineThicknessF', 'mpGridLonSpacingF', 'mpGridMaskMode',
                'mpGridMaxLatF', 'mpGridPolarLonSpacingF', 'mpGridSpacingF',
                'mpInlandWaterFillColor', 'mpInlandWaterFillPattern',
                'mpInlandWaterFillScaleF', 'mpLabelDrawOrder', 'mpLabelFontColor',
                'mpLabelFontHeightF', 'mpLabelsOn', 'mpLambertMeridianF',
                'mpLambertParallel1F', 'mpLambertParallel2F', 'mpLandFillColor',
                'mpLandFillPattern', 'mpLandFillScaleF', 'mpLeftAngleF',
                'mpLeftCornerLatF', 'mpLeftCornerLonF', 'mpLeftMapPosF',
                'mpLeftNDCF', 'mpLeftNPCF', 'mpLeftPointLatF',
                'mpLeftPointLonF', 'mpLeftWindowF', 'mpLimbLineColor',
                'mpLimbLineDashPattern', 'mpLimbLineDashSegLenF',
                'mpLimbLineThicknessF', 'mpLimitMode', 'mpMaskAreaSpecifiers',
                'mpMaskOutlineSpecifiers', 'mpMaxLatF', 'mpMaxLonF',
                'mpMinLatF', 'mpMinLonF', 'mpMonoFillColor', 'mpMonoFillPattern',
                'mpMonoFillScale', 'mpNationalLineColor', 'mpNationalLineDashPattern',
                'mpNationalLineThicknessF', 'mpOceanFillColor', 'mpOceanFillPattern',
                'mpOceanFillScaleF', 'mpOutlineBoundarySets', 'mpOutlineDrawOrder',
                'mpOutlineMaskingOn', 'mpOutlineOn', 'mpOutlineSpecifiers',
                'mpPerimDrawOrder', 'mpPerimLineColor', 'mpPerimLineDashPattern',
                'mpPerimLineDashSegLenF', 'mpPerimLineThicknessF', 'mpPerimOn',
                'mpPolyMode', 'mpProjection', 'mpProvincialLineColor',
                'mpProvincialLineDashPattern', 'mpProvincialLineDashSegLenF',
                'mpProvincialLineThicknessF', 'mpRelativeCenterLat',
                'mpRelativeCenterLon', 'mpRightAngleF', 'mpRightCornerLatF',
                'mpRightCornerLonF', 'mpRightMapPosF', 'mpRightNDCF',
                'mpRightNPCF', 'mpRightPointLatF', 'mpRightPointLonF',
                'mpRightWindowF', 'mpSatelliteAngle1F', 'mpSatelliteAngle2F',
                'mpSatelliteDistF', 'mpShapeMode', 'mpSpecifiedFillColors',
                'mpSpecifiedFillDirectIndexing', 'mpSpecifiedFillPatterns',
                'mpSpecifiedFillPriority', 'mpSpecifiedFillScales',
                'mpTopAngleF', 'mpTopMapPosF', 'mpTopNDCF', 'mpTopNPCF',
                'mpTopPointLatF', 'mpTopPointLonF', 'mpTopWindowF',
                'mpUSStateLineColor', 'mpUSStateLineDashPattern',
                'mpUSStateLineDashSegLenF', 'mpUSStateLineThicknessF',
                'pmAnnoManagers', 'pmAnnoViews', 'pmLabelBarDisplayMode',
                'pmLabelBarHeightF', 'pmLabelBarKeepAspect', 'pmLabelBarOrthogonalPosF',
                'pmLabelBarParallelPosF', 'pmLabelBarSide', 'pmLabelBarWidthF',
                'pmLabelBarZone', 'pmLegendDisplayMode', 'pmLegendHeightF',
                'pmLegendKeepAspect', 'pmLegendOrthogonalPosF',
                'pmLegendParallelPosF', 'pmLegendSide', 'pmLegendWidthF',
                'pmLegendZone', 'pmOverlaySequenceIds', 'pmTickMarkDisplayMode',
                'pmTickMarkZone', 'pmTitleDisplayMode', 'pmTitleZone',
                'prGraphicStyle', 'prPolyType', 'prXArray', 'prYArray',
                'sfCopyData', 'sfDataArray', 'sfDataMaxV', 'sfDataMinV',
                'sfElementNodes', 'sfExchangeDimensions', 'sfFirstNodeIndex',
                'sfMissingValueV', 'sfXArray', 'sfXCActualEndF', 'sfXCActualStartF',
                'sfXCEndIndex', 'sfXCEndSubsetV', 'sfXCEndV', 'sfXCStartIndex',
                'sfXCStartSubsetV', 'sfXCStartV', 'sfXCStride', 'sfXCellBounds',
                'sfYArray', 'sfYCActualEndF', 'sfYCActualStartF', 'sfYCEndIndex',
                'sfYCEndSubsetV', 'sfYCEndV', 'sfYCStartIndex', 'sfYCStartSubsetV',
                'sfYCStartV', 'sfYCStride', 'sfYCellBounds', 'stArrowLengthF',
                'stArrowStride', 'stCrossoverCheckCount',
                'stExplicitLabelBarLabelsOn', 'stLabelBarEndLabelsOn',
                'stLabelFormat', 'stLengthCheckCount', 'stLevelColors',
                'stLevelCount', 'stLevelPalette', 'stLevelSelectionMode',
                'stLevelSpacingF', 'stLevels', 'stLineColor', 'stLineOpacityF',
                'stLineStartStride', 'stLineThicknessF', 'stMapDirection',
                'stMaxLevelCount', 'stMaxLevelValF', 'stMinArrowSpacingF',
                'stMinDistanceF', 'stMinLevelValF', 'stMinLineSpacingF',
                'stMinStepFactorF', 'stMonoLineColor', 'stNoDataLabelOn',
                'stNoDataLabelString', 'stScalarFieldData', 'stScalarMissingValColor',
                'stSpanLevelPalette', 'stStepSizeF', 'stStreamlineDrawOrder',
                'stUseScalarArray', 'stVectorFieldData', 'stZeroFLabelAngleF',
                'stZeroFLabelBackgroundColor', 'stZeroFLabelConstantSpacingF',
                'stZeroFLabelFont', 'stZeroFLabelFontAspectF',
                'stZeroFLabelFontColor', 'stZeroFLabelFontHeightF',
                'stZeroFLabelFontQuality', 'stZeroFLabelFontThicknessF',
                'stZeroFLabelFuncCode', 'stZeroFLabelJust', 'stZeroFLabelOn',
                'stZeroFLabelOrthogonalPosF', 'stZeroFLabelParallelPosF',
                'stZeroFLabelPerimColor', 'stZeroFLabelPerimOn',
                'stZeroFLabelPerimSpaceF', 'stZeroFLabelPerimThicknessF',
                'stZeroFLabelSide', 'stZeroFLabelString', 'stZeroFLabelTextDirection',
                'stZeroFLabelZone', 'tfDoNDCOverlay', 'tfPlotManagerOn',
                'tfPolyDrawList', 'tfPolyDrawOrder', 'tiDeltaF', 'tiMainAngleF',
                'tiMainConstantSpacingF', 'tiMainDirection', 'tiMainFont',
                'tiMainFontAspectF', 'tiMainFontColor', 'tiMainFontHeightF',
                'tiMainFontQuality', 'tiMainFontThicknessF', 'tiMainFuncCode',
                'tiMainJust', 'tiMainOffsetXF', 'tiMainOffsetYF', 'tiMainOn',
                'tiMainPosition', 'tiMainSide', 'tiMainString', 'tiUseMainAttributes',
                'tiXAxisAngleF', 'tiXAxisConstantSpacingF', 'tiXAxisDirection',
                'tiXAxisFont', 'tiXAxisFontAspectF', 'tiXAxisFontColor',
                'tiXAxisFontHeightF', 'tiXAxisFontQuality', 'tiXAxisFontThicknessF',
                'tiXAxisFuncCode', 'tiXAxisJust', 'tiXAxisOffsetXF',
                'tiXAxisOffsetYF', 'tiXAxisOn', 'tiXAxisPosition', 'tiXAxisSide',
                'tiXAxisString', 'tiYAxisAngleF', 'tiYAxisConstantSpacingF',
                'tiYAxisDirection', 'tiYAxisFont', 'tiYAxisFontAspectF',
                'tiYAxisFontColor', 'tiYAxisFontHeightF', 'tiYAxisFontQuality',
                'tiYAxisFontThicknessF', 'tiYAxisFuncCode', 'tiYAxisJust',
                'tiYAxisOffsetXF', 'tiYAxisOffsetYF', 'tiYAxisOn', 'tiYAxisPosition',
                'tiYAxisSide', 'tiYAxisString', 'tmBorderLineColor',
                'tmBorderThicknessF', 'tmEqualizeXYSizes', 'tmLabelAutoStride',
                'tmSciNoteCutoff', 'tmXBAutoPrecision', 'tmXBBorderOn',
                'tmXBDataLeftF', 'tmXBDataRightF', 'tmXBFormat', 'tmXBIrrTensionF',
                'tmXBIrregularPoints', 'tmXBLabelAngleF', 'tmXBLabelConstantSpacingF',
                'tmXBLabelDeltaF', 'tmXBLabelDirection', 'tmXBLabelFont',
                'tmXBLabelFontAspectF', 'tmXBLabelFontColor', 'tmXBLabelFontHeightF',
                'tmXBLabelFontQuality', 'tmXBLabelFontThicknessF',
                'tmXBLabelFuncCode', 'tmXBLabelJust', 'tmXBLabelStride', 'tmXBLabels',
                'tmXBLabelsOn', 'tmXBMajorLengthF', 'tmXBMajorLineColor',
                'tmXBMajorOutwardLengthF', 'tmXBMajorThicknessF', 'tmXBMaxLabelLenF',
                'tmXBMaxTicks', 'tmXBMinLabelSpacingF', 'tmXBMinorLengthF',
                'tmXBMinorLineColor', 'tmXBMinorOn', 'tmXBMinorOutwardLengthF',
                'tmXBMinorPerMajor', 'tmXBMinorThicknessF', 'tmXBMinorValues',
                'tmXBMode', 'tmXBOn', 'tmXBPrecision', 'tmXBStyle', 'tmXBTickEndF',
                'tmXBTickSpacingF', 'tmXBTickStartF', 'tmXBValues', 'tmXMajorGrid',
                'tmXMajorGridLineColor', 'tmXMajorGridLineDashPattern',
                'tmXMajorGridThicknessF', 'tmXMinorGrid', 'tmXMinorGridLineColor',
                'tmXMinorGridLineDashPattern', 'tmXMinorGridThicknessF',
                'tmXTAutoPrecision', 'tmXTBorderOn', 'tmXTDataLeftF',
                'tmXTDataRightF', 'tmXTFormat', 'tmXTIrrTensionF',
                'tmXTIrregularPoints', 'tmXTLabelAngleF', 'tmXTLabelConstantSpacingF',
                'tmXTLabelDeltaF', 'tmXTLabelDirection', 'tmXTLabelFont',
                'tmXTLabelFontAspectF', 'tmXTLabelFontColor', 'tmXTLabelFontHeightF',
                'tmXTLabelFontQuality', 'tmXTLabelFontThicknessF',
                'tmXTLabelFuncCode', 'tmXTLabelJust', 'tmXTLabelStride', 'tmXTLabels',
                'tmXTLabelsOn', 'tmXTMajorLengthF', 'tmXTMajorLineColor',
                'tmXTMajorOutwardLengthF', 'tmXTMajorThicknessF', 'tmXTMaxLabelLenF',
                'tmXTMaxTicks', 'tmXTMinLabelSpacingF', 'tmXTMinorLengthF',
                'tmXTMinorLineColor', 'tmXTMinorOn', 'tmXTMinorOutwardLengthF',
                'tmXTMinorPerMajor', 'tmXTMinorThicknessF', 'tmXTMinorValues',
                'tmXTMode', 'tmXTOn', 'tmXTPrecision', 'tmXTStyle', 'tmXTTickEndF',
                'tmXTTickSpacingF', 'tmXTTickStartF', 'tmXTValues', 'tmXUseBottom',
                'tmYLAutoPrecision', 'tmYLBorderOn', 'tmYLDataBottomF',
                'tmYLDataTopF', 'tmYLFormat', 'tmYLIrrTensionF',
                'tmYLIrregularPoints', 'tmYLLabelAngleF', 'tmYLLabelConstantSpacingF',
                'tmYLLabelDeltaF', 'tmYLLabelDirection', 'tmYLLabelFont',
                'tmYLLabelFontAspectF', 'tmYLLabelFontColor', 'tmYLLabelFontHeightF',
                'tmYLLabelFontQuality', 'tmYLLabelFontThicknessF',
                'tmYLLabelFuncCode', 'tmYLLabelJust', 'tmYLLabelStride', 'tmYLLabels',
                'tmYLLabelsOn', 'tmYLMajorLengthF', 'tmYLMajorLineColor',
                'tmYLMajorOutwardLengthF', 'tmYLMajorThicknessF', 'tmYLMaxLabelLenF',
                'tmYLMaxTicks', 'tmYLMinLabelSpacingF', 'tmYLMinorLengthF',
                'tmYLMinorLineColor', 'tmYLMinorOn', 'tmYLMinorOutwardLengthF',
                'tmYLMinorPerMajor', 'tmYLMinorThicknessF', 'tmYLMinorValues',
                'tmYLMode', 'tmYLOn', 'tmYLPrecision', 'tmYLStyle', 'tmYLTickEndF',
                'tmYLTickSpacingF', 'tmYLTickStartF', 'tmYLValues', 'tmYMajorGrid',
                'tmYMajorGridLineColor', 'tmYMajorGridLineDashPattern',
                'tmYMajorGridThicknessF', 'tmYMinorGrid', 'tmYMinorGridLineColor',
                'tmYMinorGridLineDashPattern', 'tmYMinorGridThicknessF',
                'tmYRAutoPrecision', 'tmYRBorderOn', 'tmYRDataBottomF',
                'tmYRDataTopF', 'tmYRFormat', 'tmYRIrrTensionF',
                'tmYRIrregularPoints', 'tmYRLabelAngleF', 'tmYRLabelConstantSpacingF',
                'tmYRLabelDeltaF', 'tmYRLabelDirection', 'tmYRLabelFont',
                'tmYRLabelFontAspectF', 'tmYRLabelFontColor', 'tmYRLabelFontHeightF',
                'tmYRLabelFontQuality', 'tmYRLabelFontThicknessF',
                'tmYRLabelFuncCode', 'tmYRLabelJust', 'tmYRLabelStride', 'tmYRLabels',
                'tmYRLabelsOn', 'tmYRMajorLengthF', 'tmYRMajorLineColor',
                'tmYRMajorOutwardLengthF', 'tmYRMajorThicknessF', 'tmYRMaxLabelLenF',
                'tmYRMaxTicks', 'tmYRMinLabelSpacingF', 'tmYRMinorLengthF',
                'tmYRMinorLineColor', 'tmYRMinorOn', 'tmYRMinorOutwardLengthF',
                'tmYRMinorPerMajor', 'tmYRMinorThicknessF', 'tmYRMinorValues',
                'tmYRMode', 'tmYROn', 'tmYRPrecision', 'tmYRStyle', 'tmYRTickEndF',
                'tmYRTickSpacingF', 'tmYRTickStartF', 'tmYRValues', 'tmYUseLeft',
                'trGridType', 'trLineInterpolationOn',
                'trXAxisType', 'trXCoordPoints', 'trXInterPoints', 'trXLog',
                'trXMaxF', 'trXMinF', 'trXReverse', 'trXSamples', 'trXTensionF',
                'trYAxisType', 'trYCoordPoints', 'trYInterPoints', 'trYLog',
                'trYMaxF', 'trYMinF', 'trYReverse', 'trYSamples', 'trYTensionF',
                'txAngleF', 'txBackgroundFillColor', 'txConstantSpacingF', 'txDirection',
                'txFont', 'HLU-Fonts', 'txFontAspectF', 'txFontColor',
                'txFontHeightF', 'txFontOpacityF', 'txFontQuality',
                'txFontThicknessF', 'txFuncCode', 'txJust', 'txPerimColor',
                'txPerimDashLengthF', 'txPerimDashPattern', 'txPerimOn',
                'txPerimSpaceF', 'txPerimThicknessF', 'txPosXF', 'txPosYF',
                'txString', 'vcExplicitLabelBarLabelsOn', 'vcFillArrowEdgeColor',
                'vcFillArrowEdgeThicknessF', 'vcFillArrowFillColor',
                'vcFillArrowHeadInteriorXF', 'vcFillArrowHeadMinFracXF',
                'vcFillArrowHeadMinFracYF', 'vcFillArrowHeadXF', 'vcFillArrowHeadYF',
                'vcFillArrowMinFracWidthF', 'vcFillArrowWidthF', 'vcFillArrowsOn',
                'vcFillOverEdge', 'vcGlyphOpacityF', 'vcGlyphStyle',
                'vcLabelBarEndLabelsOn', 'vcLabelFontColor', 'vcLabelFontHeightF',
                'vcLabelsOn', 'vcLabelsUseVectorColor', 'vcLevelColors',
                'vcLevelCount', 'vcLevelPalette', 'vcLevelSelectionMode',
                'vcLevelSpacingF', 'vcLevels', 'vcLineArrowColor',
                'vcLineArrowHeadMaxSizeF', 'vcLineArrowHeadMinSizeF',
                'vcLineArrowThicknessF', 'vcMagnitudeFormat',
                'vcMagnitudeScaleFactorF', 'vcMagnitudeScaleValueF',
                'vcMagnitudeScalingMode', 'vcMapDirection', 'vcMaxLevelCount',
                'vcMaxLevelValF', 'vcMaxMagnitudeF', 'vcMinAnnoAngleF',
                'vcMinAnnoArrowAngleF', 'vcMinAnnoArrowEdgeColor',
                'vcMinAnnoArrowFillColor', 'vcMinAnnoArrowLineColor',
                'vcMinAnnoArrowMinOffsetF', 'vcMinAnnoArrowSpaceF',
                'vcMinAnnoArrowUseVecColor', 'vcMinAnnoBackgroundColor',
                'vcMinAnnoConstantSpacingF', 'vcMinAnnoExplicitMagnitudeF',
                'vcMinAnnoFont', 'vcMinAnnoFontAspectF', 'vcMinAnnoFontColor',
                'vcMinAnnoFontHeightF', 'vcMinAnnoFontQuality',
                'vcMinAnnoFontThicknessF', 'vcMinAnnoFuncCode', 'vcMinAnnoJust',
                'vcMinAnnoOn', 'vcMinAnnoOrientation', 'vcMinAnnoOrthogonalPosF',
                'vcMinAnnoParallelPosF', 'vcMinAnnoPerimColor', 'vcMinAnnoPerimOn',
                'vcMinAnnoPerimSpaceF', 'vcMinAnnoPerimThicknessF', 'vcMinAnnoSide',
                'vcMinAnnoString1', 'vcMinAnnoString1On', 'vcMinAnnoString2',
                'vcMinAnnoString2On', 'vcMinAnnoTextDirection', 'vcMinAnnoZone',
                'vcMinDistanceF', 'vcMinFracLengthF', 'vcMinLevelValF',
                'vcMinMagnitudeF', 'vcMonoFillArrowEdgeColor',
                'vcMonoFillArrowFillColor', 'vcMonoLineArrowColor',
                'vcMonoWindBarbColor', 'vcNoDataLabelOn', 'vcNoDataLabelString',
                'vcPositionMode', 'vcRefAnnoAngleF', 'vcRefAnnoArrowAngleF',
                'vcRefAnnoArrowEdgeColor', 'vcRefAnnoArrowFillColor',
                'vcRefAnnoArrowLineColor', 'vcRefAnnoArrowMinOffsetF',
                'vcRefAnnoArrowSpaceF', 'vcRefAnnoArrowUseVecColor',
                'vcRefAnnoBackgroundColor', 'vcRefAnnoConstantSpacingF',
                'vcRefAnnoExplicitMagnitudeF', 'vcRefAnnoFont',
                'vcRefAnnoFontAspectF', 'vcRefAnnoFontColor', 'vcRefAnnoFontHeightF',
                'vcRefAnnoFontQuality', 'vcRefAnnoFontThicknessF',
                'vcRefAnnoFuncCode', 'vcRefAnnoJust', 'vcRefAnnoOn',
                'vcRefAnnoOrientation', 'vcRefAnnoOrthogonalPosF',
                'vcRefAnnoParallelPosF', 'vcRefAnnoPerimColor', 'vcRefAnnoPerimOn',
                'vcRefAnnoPerimSpaceF', 'vcRefAnnoPerimThicknessF', 'vcRefAnnoSide',
                'vcRefAnnoString1', 'vcRefAnnoString1On', 'vcRefAnnoString2',
                'vcRefAnnoString2On', 'vcRefAnnoTextDirection', 'vcRefAnnoZone',
                'vcRefLengthF', 'vcRefMagnitudeF', 'vcScalarFieldData',
                'vcScalarMissingValColor', 'vcScalarValueFormat',
                'vcScalarValueScaleFactorF', 'vcScalarValueScaleValueF',
                'vcScalarValueScalingMode', 'vcSpanLevelPalette', 'vcUseRefAnnoRes',
                'vcUseScalarArray', 'vcVectorDrawOrder', 'vcVectorFieldData',
                'vcWindBarbCalmCircleSizeF', 'vcWindBarbColor',
                'vcWindBarbLineThicknessF', 'vcWindBarbScaleFactorF',
                'vcWindBarbTickAngleF', 'vcWindBarbTickLengthF',
                'vcWindBarbTickSpacingF', 'vcZeroFLabelAngleF',
                'vcZeroFLabelBackgroundColor', 'vcZeroFLabelConstantSpacingF',
                'vcZeroFLabelFont', 'vcZeroFLabelFontAspectF',
                'vcZeroFLabelFontColor', 'vcZeroFLabelFontHeightF',
                'vcZeroFLabelFontQuality', 'vcZeroFLabelFontThicknessF',
                'vcZeroFLabelFuncCode', 'vcZeroFLabelJust', 'vcZeroFLabelOn',
                'vcZeroFLabelOrthogonalPosF', 'vcZeroFLabelParallelPosF',
                'vcZeroFLabelPerimColor', 'vcZeroFLabelPerimOn',
                'vcZeroFLabelPerimSpaceF', 'vcZeroFLabelPerimThicknessF',
                'vcZeroFLabelSide', 'vcZeroFLabelString', 'vcZeroFLabelTextDirection',
                'vcZeroFLabelZone', 'vfCopyData', 'vfDataArray',
                'vfExchangeDimensions', 'vfExchangeUVData', 'vfMagMaxV', 'vfMagMinV',
                'vfMissingUValueV', 'vfMissingVValueV', 'vfPolarData',
                'vfSingleMissingValue', 'vfUDataArray', 'vfUMaxV', 'vfUMinV',
                'vfVDataArray', 'vfVMaxV', 'vfVMinV', 'vfXArray', 'vfXCActualEndF',
                'vfXCActualStartF', 'vfXCEndIndex', 'vfXCEndSubsetV', 'vfXCEndV',
                'vfXCStartIndex', 'vfXCStartSubsetV', 'vfXCStartV', 'vfXCStride',
                'vfYArray', 'vfYCActualEndF', 'vfYCActualStartF', 'vfYCEndIndex',
                'vfYCEndSubsetV', 'vfYCEndV', 'vfYCStartIndex', 'vfYCStartSubsetV',
                'vfYCStartV', 'vfYCStride', 'vpAnnoManagerId', 'vpClipOn',
                'vpHeightF', 'vpKeepAspect', 'vpOn', 'vpUseSegments', 'vpWidthF',
                'vpXF', 'vpYF', 'wkAntiAlias', 'wkBackgroundColor', 'wkBackgroundOpacityF',
                'wkColorMapLen', 'wkColorMap', 'wkColorModel', 'wkDashTableLength',
                'wkDefGraphicStyleId', 'wkDeviceLowerX', 'wkDeviceLowerY',
                'wkDeviceUpperX', 'wkDeviceUpperY', 'wkFileName', 'wkFillTableLength',
                'wkForegroundColor', 'wkFormat', 'wkFullBackground', 'wkGksWorkId',
                'wkHeight', 'wkMarkerTableLength', 'wkMetaName', 'wkOrientation',
                'wkPDFFileName', 'wkPDFFormat', 'wkPDFResolution', 'wkPSFileName',
                'wkPSFormat', 'wkPSResolution', 'wkPaperHeightF', 'wkPaperSize',
                'wkPaperWidthF', 'wkPause', 'wkTopLevelViews', 'wkViews',
                'wkVisualType', 'wkWidth', 'wkWindowId', 'wkXColorMode', 'wsCurrentSize',
                'wsMaximumSize', 'wsThresholdSize', 'xyComputeXMax',
                'xyComputeXMin', 'xyComputeYMax', 'xyComputeYMin', 'xyCoordData',
                'xyCoordDataSpec', 'xyCurveDrawOrder', 'xyDashPattern',
                'xyDashPatterns', 'xyExplicitLabels', 'xyExplicitLegendLabels',
                'xyLabelMode', 'xyLineColor', 'xyLineColors', 'xyLineDashSegLenF',
                'xyLineLabelConstantSpacingF', 'xyLineLabelFont',
                'xyLineLabelFontAspectF', 'xyLineLabelFontColor',
                'xyLineLabelFontColors', 'xyLineLabelFontHeightF',
                'xyLineLabelFontQuality', 'xyLineLabelFontThicknessF',
                'xyLineLabelFuncCode', 'xyLineThicknessF', 'xyLineThicknesses',
                'xyMarkLineMode', 'xyMarkLineModes', 'xyMarker', 'xyMarkerColor',
                'xyMarkerColors', 'xyMarkerSizeF', 'xyMarkerSizes',
                'xyMarkerThicknessF', 'xyMarkerThicknesses', 'xyMarkers',
                'xyMonoDashPattern', 'xyMonoLineColor', 'xyMonoLineLabelFontColor',
                'xyMonoLineThickness', 'xyMonoMarkLineMode', 'xyMonoMarker',
                'xyMonoMarkerColor', 'xyMonoMarkerSize', 'xyMonoMarkerThickness',
                'xyXIrrTensionF', 'xyXIrregularPoints', 'xyXStyle', 'xyYIrrTensionF',
                'xyYIrregularPoints', 'xyYStyle'), prefix=r'\b'),
             Name.Builtin),

            # Booleans
            (r'\.(True|False)\.', Name.Builtin),
            # Comparing Operators
            (r'\.(eq|ne|lt|le|gt|ge|not|and|or|xor)\.', Operator.Word),
        ],

        'strings': [
            (r'(?s)"(\\\\|\\[0-7]+|\\.|[^"\\])*"', String.Double),
        ],

        'nums': [
            (r'\d+(?![.e])(_[a-z]\w+)?', Number.Integer),
            (r'[+-]?\d*\.\d+(e[-+]?\d+)?(_[a-z]\w+)?', Number.Float),
            (r'[+-]?\d+\.\d*(e[-+]?\d+)?(_[a-z]\w+)?', Number.Float),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\freefem.py ===
"""
    pygments.lexers.freefem
    ~~~~~~~~~~~~~~~~~~~~~~~

    Lexer for FreeFem++ language.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.token import Comment, Operator, Keyword, Name

from pygments.lexers.c_cpp import CppLexer

__all__ = ['FreeFemLexer']


class FreeFemLexer(CppLexer):
    """
    For FreeFem++ source.

    This is an extension of the CppLexer, as the FreeFem Language is a superset
    of C++.
    """

    name = 'Freefem'
    url = 'https://freefem.org/'
    aliases = ['freefem']
    filenames = ['*.edp']
    mimetypes = ['text/x-freefem']
    version_added = '2.4'

    # Language operators
    operators = {'+', '-', '*', '.*', '/', './', '%', '^', '^-1', ':', '\''}

    # types
    types = {'bool', 'border', 'complex', 'dmatrix', 'fespace', 'func', 'gslspline',
             'ifstream', 'int', 'macro', 'matrix', 'mesh', 'mesh3', 'mpiComm',
             'mpiGroup', 'mpiRequest', 'NewMacro', 'EndMacro', 'ofstream', 'Pmmap',
             'problem', 'Psemaphore', 'real', 'solve', 'string', 'varf'}

    # finite element spaces
    fespaces = {'BDM1', 'BDM1Ortho', 'Edge03d', 'Edge13d', 'Edge23d', 'FEQF', 'HCT',
                'P0', 'P03d', 'P0Edge', 'P1', 'P13d', 'P1b', 'P1b3d', 'P1bl', 'P1bl3d',
                'P1dc', 'P1Edge', 'P1nc', 'P2', 'P23d', 'P2b', 'P2BR', 'P2dc', 'P2Edge',
                'P2h', 'P2Morley', 'P2pnc', 'P3', 'P3dc', 'P3Edge', 'P4', 'P4dc',
                'P4Edge', 'P5Edge', 'RT0', 'RT03d', 'RT0Ortho', 'RT1', 'RT1Ortho',
                'RT2', 'RT2Ortho'}

    # preprocessor
    preprocessor = {'ENDIFMACRO', 'include', 'IFMACRO', 'load'}

    # Language keywords
    keywords = {
                'adj',
                'append',
                'area',
                'ARGV',
                'be',
                'binary',
                'BoundaryEdge',
                'bordermeasure',
                'CG',
                'Cholesky',
                'cin',
                'cout',
                'Crout',
                'default',
                'diag',
                'edgeOrientation',
                'endl',
                'false',
                'ffind',
                'FILE',
                'find',
                'fixed',
                'flush',
                'GMRES',
                'good',
                'hTriangle',
                'im',
                'imax',
                'imin',
                'InternalEdge',
                'l1',
                'l2',
                'label',
                'lenEdge',
                'length',
                'LINE',
                'linfty',
                'LU',
                'm',
                'max',
                'measure',
                'min',
                'mpiAnySource',
                'mpiBAND',
                'mpiBXOR',
                'mpiCommWorld',
                'mpiLAND',
                'mpiLOR',
                'mpiLXOR',
                'mpiMAX',
                'mpiMIN',
                'mpiPROD',
                'mpirank',
                'mpisize',
                'mpiSUM',
                'mpiUndefined',
                'n',
                'N',
                'nbe',
                'ndof',
                'ndofK',
                'noshowbase',
                'noshowpos',
                'notaregion',
                'nt',
                'nTonEdge',
                'nuEdge',
                'nuTriangle',
                'nv',
                'P',
                'pi',
                'precision',
                'qf1pE',
                'qf1pElump',
                'qf1pT',
                'qf1pTlump',
                'qfV1',
                'qfV1lump',
                'qf2pE',
                'qf2pT',
                'qf2pT4P1',
                'qfV2',
                'qf3pE',
                'qf4pE',
                'qf5pE',
                'qf5pT',
                'qfV5',
                'qf7pT',
                'qf9pT',
                'qfnbpE',
                'quantile',
                're',
                'region',
                'rfind',
                'scientific',
                'searchMethod',
                'setw',
                'showbase',
                'showpos',
                'sparsesolver',
                'sum',
                'tellp',
                'true',
                'UMFPACK',
                'unused',
                'whoinElement',
                'verbosity',
                'version',
                'volume',
                'x',
                'y',
                'z'
    }

    # Language shipped functions and class ( )
    functions = {
                'abs',
                'acos',
                'acosh',
                'adaptmesh',
                'adj',
                'AffineCG',
                'AffineGMRES',
                'arg',
                'asin',
                'asinh',
                'assert',
                'atan',
                'atan2',
                'atanh',
                'atof',
                'atoi',
                'BFGS',
                'broadcast',
                'buildlayers',
                'buildmesh',
                'ceil',
                'chi',
                'complexEigenValue',
                'copysign',
                'change',
                'checkmovemesh',
                'clock',
                'cmaes',
                'conj',
                'convect',
                'cos',
                'cosh',
                'cube',
                'd',
                'dd',
                'dfft',
                'diffnp',
                'diffpos',
                'dimKrylov',
                'dist',
                'dumptable',
                'dx',
                'dxx',
                'dxy',
                'dxz',
                'dy',
                'dyx',
                'dyy',
                'dyz',
                'dz',
                'dzx',
                'dzy',
                'dzz',
                'EigenValue',
                'emptymesh',
                'erf',
                'erfc',
                'exec',
                'exit',
                'exp',
                'fdim',
                'floor',
                'fmax',
                'fmin',
                'fmod',
                'freeyams',
                'getARGV',
                'getline',
                'gmshload',
                'gmshload3',
                'gslcdfugaussianP',
                'gslcdfugaussianQ',
                'gslcdfugaussianPinv',
                'gslcdfugaussianQinv',
                'gslcdfgaussianP',
                'gslcdfgaussianQ',
                'gslcdfgaussianPinv',
                'gslcdfgaussianQinv',
                'gslcdfgammaP',
                'gslcdfgammaQ',
                'gslcdfgammaPinv',
                'gslcdfgammaQinv',
                'gslcdfcauchyP',
                'gslcdfcauchyQ',
                'gslcdfcauchyPinv',
                'gslcdfcauchyQinv',
                'gslcdflaplaceP',
                'gslcdflaplaceQ',
                'gslcdflaplacePinv',
                'gslcdflaplaceQinv',
                'gslcdfrayleighP',
                'gslcdfrayleighQ',
                'gslcdfrayleighPinv',
                'gslcdfrayleighQinv',
                'gslcdfchisqP',
                'gslcdfchisqQ',
                'gslcdfchisqPinv',
                'gslcdfchisqQinv',
                'gslcdfexponentialP',
                'gslcdfexponentialQ',
                'gslcdfexponentialPinv',
                'gslcdfexponentialQinv',
                'gslcdfexppowP',
                'gslcdfexppowQ',
                'gslcdftdistP',
                'gslcdftdistQ',
                'gslcdftdistPinv',
                'gslcdftdistQinv',
                'gslcdffdistP',
                'gslcdffdistQ',
                'gslcdffdistPinv',
                'gslcdffdistQinv',
                'gslcdfbetaP',
                'gslcdfbetaQ',
                'gslcdfbetaPinv',
                'gslcdfbetaQinv',
                'gslcdfflatP',
                'gslcdfflatQ',
                'gslcdfflatPinv',
                'gslcdfflatQinv',
                'gslcdflognormalP',
                'gslcdflognormalQ',
                'gslcdflognormalPinv',
                'gslcdflognormalQinv',
                'gslcdfgumbel1P',
                'gslcdfgumbel1Q',
                'gslcdfgumbel1Pinv',
                'gslcdfgumbel1Qinv',
                'gslcdfgumbel2P',
                'gslcdfgumbel2Q',
                'gslcdfgumbel2Pinv',
                'gslcdfgumbel2Qinv',
                'gslcdfweibullP',
                'gslcdfweibullQ',
                'gslcdfweibullPinv',
                'gslcdfweibullQinv',
                'gslcdfparetoP',
                'gslcdfparetoQ',
                'gslcdfparetoPinv',
                'gslcdfparetoQinv',
                'gslcdflogisticP',
                'gslcdflogisticQ',
                'gslcdflogisticPinv',
                'gslcdflogisticQinv',
                'gslcdfbinomialP',
                'gslcdfbinomialQ',
                'gslcdfpoissonP',
                'gslcdfpoissonQ',
                'gslcdfgeometricP',
                'gslcdfgeometricQ',
                'gslcdfnegativebinomialP',
                'gslcdfnegativebinomialQ',
                'gslcdfpascalP',
                'gslcdfpascalQ',
                'gslinterpakima',
                'gslinterpakimaperiodic',
                'gslinterpcsplineperiodic',
                'gslinterpcspline',
                'gslinterpsteffen',
                'gslinterplinear',
                'gslinterppolynomial',
                'gslranbernoullipdf',
                'gslranbeta',
                'gslranbetapdf',
                'gslranbinomialpdf',
                'gslranexponential',
                'gslranexponentialpdf',
                'gslranexppow',
                'gslranexppowpdf',
                'gslrancauchy',
                'gslrancauchypdf',
                'gslranchisq',
                'gslranchisqpdf',
                'gslranerlang',
                'gslranerlangpdf',
                'gslranfdist',
                'gslranfdistpdf',
                'gslranflat',
                'gslranflatpdf',
                'gslrangamma',
                'gslrangammaint',
                'gslrangammapdf',
                'gslrangammamt',
                'gslrangammaknuth',
                'gslrangaussian',
                'gslrangaussianratiomethod',
                'gslrangaussianziggurat',
                'gslrangaussianpdf',
                'gslranugaussian',
                'gslranugaussianratiomethod',
                'gslranugaussianpdf',
                'gslrangaussiantail',
                'gslrangaussiantailpdf',
                'gslranugaussiantail',
                'gslranugaussiantailpdf',
                'gslranlandau',
                'gslranlandaupdf',
                'gslrangeometricpdf',
                'gslrangumbel1',
                'gslrangumbel1pdf',
                'gslrangumbel2',
                'gslrangumbel2pdf',
                'gslranlogistic',
                'gslranlogisticpdf',
                'gslranlognormal',
                'gslranlognormalpdf',
                'gslranlogarithmicpdf',
                'gslrannegativebinomialpdf',
                'gslranpascalpdf',
                'gslranpareto',
                'gslranparetopdf',
                'gslranpoissonpdf',
                'gslranrayleigh',
                'gslranrayleighpdf',
                'gslranrayleightail',
                'gslranrayleightailpdf',
                'gslrantdist',
                'gslrantdistpdf',
                'gslranlaplace',
                'gslranlaplacepdf',
                'gslranlevy',
                'gslranweibull',
                'gslranweibullpdf',
                'gslsfairyAi',
                'gslsfairyBi',
                'gslsfairyAiscaled',
                'gslsfairyBiscaled',
                'gslsfairyAideriv',
                'gslsfairyBideriv',
                'gslsfairyAiderivscaled',
                'gslsfairyBiderivscaled',
                'gslsfairyzeroAi',
                'gslsfairyzeroBi',
                'gslsfairyzeroAideriv',
                'gslsfairyzeroBideriv',
                'gslsfbesselJ0',
                'gslsfbesselJ1',
                'gslsfbesselJn',
                'gslsfbesselY0',
                'gslsfbesselY1',
                'gslsfbesselYn',
                'gslsfbesselI0',
                'gslsfbesselI1',
                'gslsfbesselIn',
                'gslsfbesselI0scaled',
                'gslsfbesselI1scaled',
                'gslsfbesselInscaled',
                'gslsfbesselK0',
                'gslsfbesselK1',
                'gslsfbesselKn',
                'gslsfbesselK0scaled',
                'gslsfbesselK1scaled',
                'gslsfbesselKnscaled',
                'gslsfbesselj0',
                'gslsfbesselj1',
                'gslsfbesselj2',
                'gslsfbesseljl',
                'gslsfbessely0',
                'gslsfbessely1',
                'gslsfbessely2',
                'gslsfbesselyl',
                'gslsfbesseli0scaled',
                'gslsfbesseli1scaled',
                'gslsfbesseli2scaled',
                'gslsfbesselilscaled',
                'gslsfbesselk0scaled',
                'gslsfbesselk1scaled',
                'gslsfbesselk2scaled',
                'gslsfbesselklscaled',
                'gslsfbesselJnu',
                'gslsfbesselYnu',
                'gslsfbesselInuscaled',
                'gslsfbesselInu',
                'gslsfbesselKnuscaled',
                'gslsfbesselKnu',
                'gslsfbessellnKnu',
                'gslsfbesselzeroJ0',
                'gslsfbesselzeroJ1',
                'gslsfbesselzeroJnu',
                'gslsfclausen',
                'gslsfhydrogenicR1',
                'gslsfdawson',
                'gslsfdebye1',
                'gslsfdebye2',
                'gslsfdebye3',
                'gslsfdebye4',
                'gslsfdebye5',
                'gslsfdebye6',
                'gslsfdilog',
                'gslsfmultiply',
                'gslsfellintKcomp',
                'gslsfellintEcomp',
                'gslsfellintPcomp',
                'gslsfellintDcomp',
                'gslsfellintF',
                'gslsfellintE',
                'gslsfellintRC',
                'gslsferfc',
                'gslsflogerfc',
                'gslsferf',
                'gslsferfZ',
                'gslsferfQ',
                'gslsfhazard',
                'gslsfexp',
                'gslsfexpmult',
                'gslsfexpm1',
                'gslsfexprel',
                'gslsfexprel2',
                'gslsfexpreln',
                'gslsfexpintE1',
                'gslsfexpintE2',
                'gslsfexpintEn',
                'gslsfexpintE1scaled',
                'gslsfexpintE2scaled',
                'gslsfexpintEnscaled',
                'gslsfexpintEi',
                'gslsfexpintEiscaled',
                'gslsfShi',
                'gslsfChi',
                'gslsfexpint3',
                'gslsfSi',
                'gslsfCi',
                'gslsfatanint',
                'gslsffermidiracm1',
                'gslsffermidirac0',
                'gslsffermidirac1',
                'gslsffermidirac2',
                'gslsffermidiracint',
                'gslsffermidiracmhalf',
                'gslsffermidirachalf',
                'gslsffermidirac3half',
                'gslsffermidiracinc0',
                'gslsflngamma',
                'gslsfgamma',
                'gslsfgammastar',
                'gslsfgammainv',
                'gslsftaylorcoeff',
                'gslsffact',
                'gslsfdoublefact',
                'gslsflnfact',
                'gslsflndoublefact',
                'gslsflnchoose',
                'gslsfchoose',
                'gslsflnpoch',
                'gslsfpoch',
                'gslsfpochrel',
                'gslsfgammaincQ',
                'gslsfgammaincP',
                'gslsfgammainc',
                'gslsflnbeta',
                'gslsfbeta',
                'gslsfbetainc',
                'gslsfgegenpoly1',
                'gslsfgegenpoly2',
                'gslsfgegenpoly3',
                'gslsfgegenpolyn',
                'gslsfhyperg0F1',
                'gslsfhyperg1F1int',
                'gslsfhyperg1F1',
                'gslsfhypergUint',
                'gslsfhypergU',
                'gslsfhyperg2F0',
                'gslsflaguerre1',
                'gslsflaguerre2',
                'gslsflaguerre3',
                'gslsflaguerren',
                'gslsflambertW0',
                'gslsflambertWm1',
                'gslsflegendrePl',
                'gslsflegendreP1',
                'gslsflegendreP2',
                'gslsflegendreP3',
                'gslsflegendreQ0',
                'gslsflegendreQ1',
                'gslsflegendreQl',
                'gslsflegendrePlm',
                'gslsflegendresphPlm',
                'gslsflegendrearraysize',
                'gslsfconicalPhalf',
                'gslsfconicalPmhalf',
                'gslsfconicalP0',
                'gslsfconicalP1',
                'gslsfconicalPsphreg',
                'gslsfconicalPcylreg',
                'gslsflegendreH3d0',
                'gslsflegendreH3d1',
                'gslsflegendreH3d',
                'gslsflog',
                'gslsflogabs',
                'gslsflog1plusx',
                'gslsflog1plusxmx',
                'gslsfpowint',
                'gslsfpsiint',
                'gslsfpsi',
                'gslsfpsi1piy',
                'gslsfpsi1int',
                'gslsfpsi1',
                'gslsfpsin',
                'gslsfsynchrotron1',
                'gslsfsynchrotron2',
                'gslsftransport2',
                'gslsftransport3',
                'gslsftransport4',
                'gslsftransport5',
                'gslsfsin',
                'gslsfcos',
                'gslsfhypot',
                'gslsfsinc',
                'gslsflnsinh',
                'gslsflncosh',
                'gslsfanglerestrictsymm',
                'gslsfanglerestrictpos',
                'gslsfzetaint',
                'gslsfzeta',
                'gslsfzetam1',
                'gslsfzetam1int',
                'gslsfhzeta',
                'gslsfetaint',
                'gslsfeta',
                'imag',
                'int1d',
                'int2d',
                'int3d',
                'intalledges',
                'intallfaces',
                'interpolate',
                'invdiff',
                'invdiffnp',
                'invdiffpos',
                'Isend',
                'isInf',
                'isNaN',
                'isoline',
                'Irecv',
                'j0',
                'j1',
                'jn',
                'jump',
                'lgamma',
                'LinearCG',
                'LinearGMRES',
                'log',
                'log10',
                'lrint',
                'lround',
                'max',
                'mean',
                'medit',
                'min',
                'mmg3d',
                'movemesh',
                'movemesh23',
                'mpiAlltoall',
                'mpiAlltoallv',
                'mpiAllgather',
                'mpiAllgatherv',
                'mpiAllReduce',
                'mpiBarrier',
                'mpiGather',
                'mpiGatherv',
                'mpiRank',
                'mpiReduce',
                'mpiScatter',
                'mpiScatterv',
                'mpiSize',
                'mpiWait',
                'mpiWaitAny',
                'mpiWtick',
                'mpiWtime',
                'mshmet',
                'NaN',
                'NLCG',
                'on',
                'plot',
                'polar',
                'Post',
                'pow',
                'processor',
                'processorblock',
                'projection',
                'randinit',
                'randint31',
                'randint32',
                'random',
                'randreal1',
                'randreal2',
                'randreal3',
                'randres53',
                'Read',
                'readmesh',
                'readmesh3',
                'Recv',
                'rint',
                'round',
                'savemesh',
                'savesol',
                'savevtk',
                'seekg',
                'Sent',
                'set',
                'sign',
                'signbit',
                'sin',
                'sinh',
                'sort',
                'splitComm',
                'splitmesh',
                'sqrt',
                'square',
                'srandom',
                'srandomdev',
                'Stringification',
                'swap',
                'system',
                'tan',
                'tanh',
                'tellg',
                'tetg',
                'tetgconvexhull',
                'tetgreconstruction',
                'tetgtransfo',
                'tgamma',
                'triangulate',
                'trunc',
                'Wait',
                'Write',
                'y0',
                'y1',
                'yn'
    }

    # function parameters
    parameters = {
                'A',
                'A1',
                'abserror',
                'absolute',
                'aniso',
                'aspectratio',
                'B',
                'B1',
                'bb',
                'beginend',
                'bin',
                'boundary',
                'bw',
                'close',
                'cmm',
                'coef',
                'composante',
                'cutoff',
                'datafilename',
                'dataname',
                'dim',
                'distmax',
                'displacement',
                'doptions',
                'dparams',
                'eps',
                'err',
                'errg',
                'facemerge',
                'facetcl',
                'factorize',
                'file',
                'fill',
                'fixedborder',
                'flabel',
                'flags',
                'floatmesh',
                'floatsol',
                'fregion',
                'gradation',
                'grey',
                'hmax',
                'hmin',
                'holelist',
                'hsv',
                'init',
                'inquire',
                'inside',
                'IsMetric',
                'iso',
                'ivalue',
                'keepbackvertices',
                'label',
                'labeldown',
                'labelmid',
                'labelup',
                'levelset',
                'loptions',
                'lparams',
                'maxit',
                'maxsubdiv',
                'meditff',
                'mem',
                'memory',
                'metric',
                'mode',
                'nbarrow',
                'nbiso',
                'nbiter',
                'nbjacoby',
                'nboffacetcl',
                'nbofholes',
                'nbofregions',
                'nbregul',
                'nbsmooth',
                'nbvx',
                'ncv',
                'nev',
                'nomeshgeneration',
                'normalization',
                'omega',
                'op',
                'optimize',
                'option',
                'options',
                'order',
                'orientation',
                'periodic',
                'power',
                'precon',
                'prev',
                'ps',
                'ptmerge',
                'qfe',
                'qforder',
                'qft',
                'qfV',
                'ratio',
                'rawvector',
                'reffacelow',
                'reffacemid',
                'reffaceup',
                'refnum',
                'reftet',
                'reftri',
                'region',
                'regionlist',
                'renumv',
                'rescaling',
                'ridgeangle',
                'save',
                'sigma',
                'sizeofvolume',
                'smoothing',
                'solver',
                'sparams',
                'split',
                'splitin2',
                'splitpbedge',
                'stop',
                'strategy',
                'swap',
                'switch',
                'sym',
                't',
                'tgv',
                'thetamax',
                'tol',
                'tolpivot',
                'tolpivotsym',
                'transfo',
                'U2Vc',
                'value',
                'varrow',
                'vector',
                'veps',
                'viso',
                'wait',
                'width',
                'withsurfacemesh',
                'WindowIndex',
                'which',
                'zbound'
    }

    # deprecated
    deprecated = {'fixeborder'}

    # do not highlight
    suppress_highlight = {
                'alignof',
                'asm',
                'constexpr',
                'decltype',
                'div',
                'double',
                'grad',
                'mutable',
                'namespace',
                'noexcept',
                'restrict',
                'static_assert',
                'template',
                'this',
                'thread_local',
                'typeid',
                'typename',
                'using'
    }

    def get_tokens_unprocessed(self, text, stack=('root',)):
        for index, token, value in CppLexer.get_tokens_unprocessed(self, text, stack):
            if value in self.operators:
                yield index, Operator, value
            elif value in self.types:
                yield index, Keyword.Type, value
            elif value in self.fespaces:
                yield index, Name.Class, value
            elif value in self.preprocessor:
                yield index, Comment.Preproc, value
            elif value in self.keywords:
                yield index, Keyword.Reserved, value
            elif value in self.functions:
                yield index, Name.Function, value
            elif value in self.parameters:
                yield index, Keyword.Pseudo, value
            elif value in self.suppress_highlight:
                yield index, Name, value
            else:
                yield index, token, value

# === NexusCore/openenv\Lib\site-packages\tornado\gen.py ===
"""``tornado.gen`` implements generator-based coroutines.

.. note::

   The "decorator and generator" approach in this module is a
   precursor to native coroutines (using ``async def`` and ``await``)
   which were introduced in Python 3.5. Applications that do not
   require compatibility with older versions of Python should use
   native coroutines instead. Some parts of this module are still
   useful with native coroutines, notably `multi`, `sleep`,
   `WaitIterator`, and `with_timeout`. Some of these functions have
   counterparts in the `asyncio` module which may be used as well,
   although the two may not necessarily be 100% compatible.

Coroutines provide an easier way to work in an asynchronous
environment than chaining callbacks. Code using coroutines is
technically asynchronous, but it is written as a single generator
instead of a collection of separate functions.

For example, here's a coroutine-based handler:

.. testcode::

    class GenAsyncHandler(RequestHandler):
        @gen.coroutine
        def get(self):
            http_client = AsyncHTTPClient()
            response = yield http_client.fetch("http://example.com")
            do_something_with_response(response)
            self.render("template.html")

Asynchronous functions in Tornado return an ``Awaitable`` or `.Future`;
yielding this object returns its result.

You can also yield a list or dict of other yieldable objects, which
will be started at the same time and run in parallel; a list or dict
of results will be returned when they are all finished:

.. testcode::

    @gen.coroutine
    def get(self):
        http_client = AsyncHTTPClient()
        response1, response2 = yield [http_client.fetch(url1),
                                      http_client.fetch(url2)]
        response_dict = yield dict(response3=http_client.fetch(url3),
                                   response4=http_client.fetch(url4))
        response3 = response_dict['response3']
        response4 = response_dict['response4']

If ``tornado.platform.twisted`` is imported, it is also possible to
yield Twisted's ``Deferred`` objects. See the `convert_yielded`
function to extend this mechanism.

.. versionchanged:: 3.2
   Dict support added.

.. versionchanged:: 4.1
   Support added for yielding ``asyncio`` Futures and Twisted Deferreds
   via ``singledispatch``.

"""

import asyncio
import builtins
import collections
from collections.abc import Generator
import concurrent.futures
import datetime
import functools
from functools import singledispatch
from inspect import isawaitable
import sys
import types

from tornado.concurrent import (
    Future,
    is_future,
    chain_future,
    future_set_exc_info,
    future_add_done_callback,
    future_set_result_unless_cancelled,
)
from tornado.ioloop import IOLoop
from tornado.log import app_log
from tornado.util import TimeoutError

try:
    import contextvars
except ImportError:
    contextvars = None  # type: ignore

import typing
from typing import (
    Mapping,
    Union,
    Any,
    Callable,
    List,
    Type,
    Tuple,
    Awaitable,
    Dict,
    Sequence,
    overload,
)

if typing.TYPE_CHECKING:
    from typing import Deque, Optional, Set, Iterable  # noqa: F401

_T = typing.TypeVar("_T")

_Yieldable = Union[
    None, Awaitable, List[Awaitable], Dict[Any, Awaitable], concurrent.futures.Future
]


class KeyReuseError(Exception):
    pass


class UnknownKeyError(Exception):
    pass


class LeakedCallbackError(Exception):
    pass


class BadYieldError(Exception):
    pass


class ReturnValueIgnoredError(Exception):
    pass


def _value_from_stopiteration(e: Union[StopIteration, "Return"]) -> Any:
    try:
        # StopIteration has a value attribute beginning in py33.
        # So does our Return class.
        return e.value
    except AttributeError:
        pass
    try:
        # Cython backports coroutine functionality by putting the value in
        # e.args[0].
        return e.args[0]
    except (AttributeError, IndexError):
        return None


def _create_future() -> Future:
    future = Future()  # type: Future
    # Fixup asyncio debug info by removing extraneous stack entries
    source_traceback = getattr(future, "_source_traceback", ())
    while source_traceback:
        # Each traceback entry is equivalent to a
        # (filename, self.lineno, self.name, self.line) tuple
        filename = source_traceback[-1][0]
        if filename == __file__:
            del source_traceback[-1]
        else:
            break
    return future


def _fake_ctx_run(f: Callable[..., _T], *args: Any, **kw: Any) -> _T:
    return f(*args, **kw)


@overload
def coroutine(
    func: Callable[..., "Generator[Any, Any, _T]"]
) -> Callable[..., "Future[_T]"]: ...


@overload
def coroutine(func: Callable[..., _T]) -> Callable[..., "Future[_T]"]: ...


def coroutine(
    func: Union[Callable[..., "Generator[Any, Any, _T]"], Callable[..., _T]]
) -> Callable[..., "Future[_T]"]:
    """Decorator for asynchronous generators.

    For compatibility with older versions of Python, coroutines may
    also "return" by raising the special exception `Return(value)
    <Return>`.

    Functions with this decorator return a `.Future`.

    .. warning::

       When exceptions occur inside a coroutine, the exception
       information will be stored in the `.Future` object. You must
       examine the result of the `.Future` object, or the exception
       may go unnoticed by your code. This means yielding the function
       if called from another coroutine, using something like
       `.IOLoop.run_sync` for top-level calls, or passing the `.Future`
       to `.IOLoop.add_future`.

    .. versionchanged:: 6.0

       The ``callback`` argument was removed. Use the returned
       awaitable object instead.

    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # type: (*Any, **Any) -> Future[_T]
        # This function is type-annotated with a comment to work around
        # https://bitbucket.org/pypy/pypy/issues/2868/segfault-with-args-type-annotation-in
        future = _create_future()
        if contextvars is not None:
            ctx_run = contextvars.copy_context().run  # type: Callable
        else:
            ctx_run = _fake_ctx_run
        try:
            result = ctx_run(func, *args, **kwargs)
        except (Return, StopIteration) as e:
            result = _value_from_stopiteration(e)
        except Exception:
            future_set_exc_info(future, sys.exc_info())
            try:
                return future
            finally:
                # Avoid circular references
                future = None  # type: ignore
        else:
            if isinstance(result, Generator):
                # Inline the first iteration of Runner.run.  This lets us
                # avoid the cost of creating a Runner when the coroutine
                # never actually yields, which in turn allows us to
                # use "optional" coroutines in critical path code without
                # performance penalty for the synchronous case.
                try:
                    yielded = ctx_run(next, result)
                except (StopIteration, Return) as e:
                    future_set_result_unless_cancelled(
                        future, _value_from_stopiteration(e)
                    )
                except Exception:
                    future_set_exc_info(future, sys.exc_info())
                else:
                    # Provide strong references to Runner objects as long
                    # as their result future objects also have strong
                    # references (typically from the parent coroutine's
                    # Runner). This keeps the coroutine's Runner alive.
                    # We do this by exploiting the public API
                    # add_done_callback() instead of putting a private
                    # attribute on the Future.
                    # (GitHub issues #1769, #2229).
                    runner = Runner(ctx_run, result, future, yielded)
                    future.add_done_callback(lambda _: runner)
                yielded = None
                try:
                    return future
                finally:
                    # Subtle memory optimization: if next() raised an exception,
                    # the future's exc_info contains a traceback which
                    # includes this stack frame.  This creates a cycle,
                    # which will be collected at the next full GC but has
                    # been shown to greatly increase memory usage of
                    # benchmarks (relative to the refcount-based scheme
                    # used in the absence of cycles).  We can avoid the
                    # cycle by clearing the local variable after we return it.
                    future = None  # type: ignore
        future_set_result_unless_cancelled(future, result)
        return future

    wrapper.__wrapped__ = func  # type: ignore
    wrapper.__tornado_coroutine__ = True  # type: ignore
    return wrapper


def is_coroutine_function(func: Any) -> bool:
    """Return whether *func* is a coroutine function, i.e. a function
    wrapped with `~.gen.coroutine`.

    .. versionadded:: 4.5
    """
    return getattr(func, "__tornado_coroutine__", False)


class Return(Exception):
    """Special exception to return a value from a `coroutine`.

    This exception exists for compatibility with older versions of
    Python (before 3.3). In newer code use the ``return`` statement
    instead.

    If this exception is raised, its value argument is used as the
    result of the coroutine::

        @gen.coroutine
        def fetch_json(url):
            response = yield AsyncHTTPClient().fetch(url)
            raise gen.Return(json_decode(response.body))

    By analogy with the return statement, the value argument is optional.
    """

    def __init__(self, value: Any = None) -> None:
        super().__init__()
        self.value = value
        # Cython recognizes subclasses of StopIteration with a .args tuple.
        self.args = (value,)


class WaitIterator:
    """Provides an iterator to yield the results of awaitables as they finish.

    Yielding a set of awaitables like this:

    ``results = yield [awaitable1, awaitable2]``

    pauses the coroutine until both ``awaitable1`` and ``awaitable2``
    return, and then restarts the coroutine with the results of both
    awaitables. If either awaitable raises an exception, the
    expression will raise that exception and all the results will be
    lost.

    If you need to get the result of each awaitable as soon as possible,
    or if you need the result of some awaitables even if others produce
    errors, you can use ``WaitIterator``::

      wait_iterator = gen.WaitIterator(awaitable1, awaitable2)
      while not wait_iterator.done():
          try:
              result = yield wait_iterator.next()
          except Exception as e:
              print("Error {} from {}".format(e, wait_iterator.current_future))
          else:
              print("Result {} received from {} at {}".format(
                  result, wait_iterator.current_future,
                  wait_iterator.current_index))

    Because results are returned as soon as they are available the
    output from the iterator *will not be in the same order as the
    input arguments*. If you need to know which future produced the
    current result, you can use the attributes
    ``WaitIterator.current_future``, or ``WaitIterator.current_index``
    to get the index of the awaitable from the input list. (if keyword
    arguments were used in the construction of the `WaitIterator`,
    ``current_index`` will use the corresponding keyword).

    `WaitIterator` implements the async iterator
    protocol, so it can be used with the ``async for`` statement (note
    that in this version the entire iteration is aborted if any value
    raises an exception, while the previous example can continue past
    individual errors)::

      async for result in gen.WaitIterator(future1, future2):
          print("Result {} received from {} at {}".format(
              result, wait_iterator.current_future,
              wait_iterator.current_index))

    .. versionadded:: 4.1

    .. versionchanged:: 4.3
       Added ``async for`` support in Python 3.5.

    """

    _unfinished = {}  # type: Dict[Future, Union[int, str]]

    def __init__(self, *args: Future, **kwargs: Future) -> None:
        if args and kwargs:
            raise ValueError("You must provide args or kwargs, not both")

        if kwargs:
            self._unfinished = {f: k for (k, f) in kwargs.items()}
            futures = list(kwargs.values())  # type: Sequence[Future]
        else:
            self._unfinished = {f: i for (i, f) in enumerate(args)}
            futures = args

        self._finished = collections.deque()  # type: Deque[Future]
        self.current_index = None  # type: Optional[Union[str, int]]
        self.current_future = None  # type: Optional[Future]
        self._running_future = None  # type: Optional[Future]

        for future in futures:
            future_add_done_callback(future, self._done_callback)

    def done(self) -> bool:
        """Returns True if this iterator has no more results."""
        if self._finished or self._unfinished:
            return False
        # Clear the 'current' values when iteration is done.
        self.current_index = self.current_future = None
        return True

    def next(self) -> Future:
        """Returns a `.Future` that will yield the next available result.

        Note that this `.Future` will not be the same object as any of
        the inputs.
        """
        self._running_future = Future()

        if self._finished:
            return self._return_result(self._finished.popleft())

        return self._running_future

    def _done_callback(self, done: Future) -> None:
        if self._running_future and not self._running_future.done():
            self._return_result(done)
        else:
            self._finished.append(done)

    def _return_result(self, done: Future) -> Future:
        """Called set the returned future's state that of the future
        we yielded, and set the current future for the iterator.
        """
        if self._running_future is None:
            raise Exception("no future is running")
        chain_future(done, self._running_future)

        res = self._running_future
        self._running_future = None
        self.current_future = done
        self.current_index = self._unfinished.pop(done)

        return res

    def __aiter__(self) -> typing.AsyncIterator:
        return self

    def __anext__(self) -> Future:
        if self.done():
            # Lookup by name to silence pyflakes on older versions.
            raise getattr(builtins, "StopAsyncIteration")()
        return self.next()


def multi(
    children: Union[Sequence[_Yieldable], Mapping[Any, _Yieldable]],
    quiet_exceptions: "Union[Type[Exception], Tuple[Type[Exception], ...]]" = (),
) -> "Union[Future[List], Future[Dict]]":
    """Runs multiple asynchronous operations in parallel.

    ``children`` may either be a list or a dict whose values are
    yieldable objects. ``multi()`` returns a new yieldable
    object that resolves to a parallel structure containing their
    results. If ``children`` is a list, the result is a list of
    results in the same order; if it is a dict, the result is a dict
    with the same keys.

    That is, ``results = yield multi(list_of_futures)`` is equivalent
    to::

        results = []
        for future in list_of_futures:
            results.append(yield future)

    If any children raise exceptions, ``multi()`` will raise the first
    one. All others will be logged, unless they are of types
    contained in the ``quiet_exceptions`` argument.

    In a ``yield``-based coroutine, it is not normally necessary to
    call this function directly, since the coroutine runner will
    do it automatically when a list or dict is yielded. However,
    it is necessary in ``await``-based coroutines, or to pass
    the ``quiet_exceptions`` argument.

    This function is available under the names ``multi()`` and ``Multi()``
    for historical reasons.

    Cancelling a `.Future` returned by ``multi()`` does not cancel its
    children. `asyncio.gather` is similar to ``multi()``, but it does
    cancel its children.

    .. versionchanged:: 4.2
       If multiple yieldables fail, any exceptions after the first
       (which is raised) will be logged. Added the ``quiet_exceptions``
       argument to suppress this logging for selected exception types.

    .. versionchanged:: 4.3
       Replaced the class ``Multi`` and the function ``multi_future``
       with a unified function ``multi``. Added support for yieldables
       other than ``YieldPoint`` and `.Future`.

    """
    return multi_future(children, quiet_exceptions=quiet_exceptions)


Multi = multi


def multi_future(
    children: Union[Sequence[_Yieldable], Mapping[Any, _Yieldable]],
    quiet_exceptions: "Union[Type[Exception], Tuple[Type[Exception], ...]]" = (),
) -> "Union[Future[List], Future[Dict]]":
    """Wait for multiple asynchronous futures in parallel.

    Since Tornado 6.0, this function is exactly the same as `multi`.

    .. versionadded:: 4.0

    .. versionchanged:: 4.2
       If multiple ``Futures`` fail, any exceptions after the first (which is
       raised) will be logged. Added the ``quiet_exceptions``
       argument to suppress this logging for selected exception types.

    .. deprecated:: 4.3
       Use `multi` instead.
    """
    if isinstance(children, dict):
        keys = list(children.keys())  # type: Optional[List]
        children_seq = children.values()  # type: Iterable
    else:
        keys = None
        children_seq = children
    children_futs = list(map(convert_yielded, children_seq))
    assert all(is_future(i) or isinstance(i, _NullFuture) for i in children_futs)
    unfinished_children = set(children_futs)

    future = _create_future()
    if not children_futs:
        future_set_result_unless_cancelled(future, {} if keys is not None else [])

    def callback(fut: Future) -> None:
        unfinished_children.remove(fut)
        if not unfinished_children:
            result_list = []
            for f in children_futs:
                try:
                    result_list.append(f.result())
                except Exception as e:
                    if future.done():
                        if not isinstance(e, quiet_exceptions):
                            app_log.error(
                                "Multiple exceptions in yield list", exc_info=True
                            )
                    else:
                        future_set_exc_info(future, sys.exc_info())
            if not future.done():
                if keys is not None:
                    future_set_result_unless_cancelled(
                        future, dict(zip(keys, result_list))
                    )
                else:
                    future_set_result_unless_cancelled(future, result_list)

    listening = set()  # type: Set[Future]
    for f in children_futs:
        if f not in listening:
            listening.add(f)
            future_add_done_callback(f, callback)
    return future


def maybe_future(x: Any) -> Future:
    """Converts ``x`` into a `.Future`.

    If ``x`` is already a `.Future`, it is simply returned; otherwise
    it is wrapped in a new `.Future`.  This is suitable for use as
    ``result = yield gen.maybe_future(f())`` when you don't know whether
    ``f()`` returns a `.Future` or not.

    .. deprecated:: 4.3
       This function only handles ``Futures``, not other yieldable objects.
       Instead of `maybe_future`, check for the non-future result types
       you expect (often just ``None``), and ``yield`` anything unknown.
    """
    if is_future(x):
        return x
    else:
        fut = _create_future()
        fut.set_result(x)
        return fut


def with_timeout(
    timeout: Union[float, datetime.timedelta],
    future: _Yieldable,
    quiet_exceptions: "Union[Type[Exception], Tuple[Type[Exception], ...]]" = (),
) -> Future:
    """Wraps a `.Future` (or other yieldable object) in a timeout.

    Raises `tornado.util.TimeoutError` if the input future does not
    complete before ``timeout``, which may be specified in any form
    allowed by `.IOLoop.add_timeout` (i.e. a `datetime.timedelta` or
    an absolute time relative to `.IOLoop.time`)

    If the wrapped `.Future` fails after it has timed out, the exception
    will be logged unless it is either of a type contained in
    ``quiet_exceptions`` (which may be an exception type or a sequence of
    types), or an ``asyncio.CancelledError``.

    The wrapped `.Future` is not canceled when the timeout expires,
    permitting it to be reused. `asyncio.wait_for` is similar to this
    function but it does cancel the wrapped `.Future` on timeout.

    .. versionadded:: 4.0

    .. versionchanged:: 4.1
       Added the ``quiet_exceptions`` argument and the logging of unhandled
       exceptions.

    .. versionchanged:: 4.4
       Added support for yieldable objects other than `.Future`.

    .. versionchanged:: 6.0.3
       ``asyncio.CancelledError`` is now always considered "quiet".

    .. versionchanged:: 6.2
       ``tornado.util.TimeoutError`` is now an alias to ``asyncio.TimeoutError``.

    """
    # It's tempting to optimize this by cancelling the input future on timeout
    # instead of creating a new one, but A) we can't know if we are the only
    # one waiting on the input future, so cancelling it might disrupt other
    # callers and B) concurrent futures can only be cancelled while they are
    # in the queue, so cancellation cannot reliably bound our waiting time.
    future_converted = convert_yielded(future)
    result = _create_future()
    chain_future(future_converted, result)
    io_loop = IOLoop.current()

    def error_callback(future: Future) -> None:
        try:
            future.result()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            if not isinstance(e, quiet_exceptions):
                app_log.error(
                    "Exception in Future %r after timeout", future, exc_info=True
                )

    def timeout_callback() -> None:
        if not result.done():
            result.set_exception(TimeoutError("Timeout"))
        # In case the wrapped future goes on to fail, log it.
        future_add_done_callback(future_converted, error_callback)

    timeout_handle = io_loop.add_timeout(timeout, timeout_callback)
    if isinstance(future_converted, Future):
        # We know this future will resolve on the IOLoop, so we don't
        # need the extra thread-safety of IOLoop.add_future (and we also
        # don't care about StackContext here.
        future_add_done_callback(
            future_converted, lambda future: io_loop.remove_timeout(timeout_handle)
        )
    else:
        # concurrent.futures.Futures may resolve on any thread, so we
        # need to route them back to the IOLoop.
        io_loop.add_future(
            future_converted, lambda future: io_loop.remove_timeout(timeout_handle)
        )
    return result


def sleep(duration: float) -> "Future[None]":
    """Return a `.Future` that resolves after the given number of seconds.

    When used with ``yield`` in a coroutine, this is a non-blocking
    analogue to `time.sleep` (which should not be used in coroutines
    because it is blocking)::

        yield gen.sleep(0.5)

    Note that calling this function on its own does nothing; you must
    wait on the `.Future` it returns (usually by yielding it).

    .. versionadded:: 4.1
    """
    f = _create_future()
    IOLoop.current().call_later(
        duration, lambda: future_set_result_unless_cancelled(f, None)
    )
    return f


class _NullFuture:
    """_NullFuture resembles a Future that finished with a result of None.

    It's not actually a `Future` to avoid depending on a particular event loop.
    Handled as a special case in the coroutine runner.

    We lie and tell the type checker that a _NullFuture is a Future so
    we don't have to leak _NullFuture into lots of public APIs. But
    this means that the type checker can't warn us when we're passing
    a _NullFuture into a code path that doesn't understand what to do
    with it.
    """

    def result(self) -> None:
        return None

    def done(self) -> bool:
        return True


# _null_future is used as a dummy value in the coroutine runner. It differs
# from moment in that moment always adds a delay of one IOLoop iteration
# while _null_future is processed as soon as possible.
_null_future = typing.cast(Future, _NullFuture())

moment = typing.cast(Future, _NullFuture())
moment.__doc__ = """A special object which may be yielded to allow the IOLoop to run for
one iteration.

This is not needed in normal use but it can be helpful in long-running
coroutines that are likely to yield Futures that are ready instantly.

Usage: ``yield gen.moment``

In native coroutines, the equivalent of ``yield gen.moment`` is
``await asyncio.sleep(0)``.

.. versionadded:: 4.0

.. deprecated:: 4.5
   ``yield None`` (or ``yield`` with no argument) is now equivalent to
    ``yield gen.moment``.
"""


class Runner:
    """Internal implementation of `tornado.gen.coroutine`.

    Maintains information about pending callbacks and their results.

    The results of the generator are stored in ``result_future`` (a
    `.Future`)
    """

    def __init__(
        self,
        ctx_run: Callable,
        gen: "Generator[_Yieldable, Any, _T]",
        result_future: "Future[_T]",
        first_yielded: _Yieldable,
    ) -> None:
        self.ctx_run = ctx_run
        self.gen = gen
        self.result_future = result_future
        self.future = _null_future  # type: Union[None, Future]
        self.running = False
        self.finished = False
        self.io_loop = IOLoop.current()
        if self.ctx_run(self.handle_yield, first_yielded):
            gen = result_future = first_yielded = None  # type: ignore
            self.ctx_run(self.run)

    def run(self) -> None:
        """Starts or resumes the generator, running until it reaches a
        yield point that is not ready.
        """
        if self.running or self.finished:
            return
        try:
            self.running = True
            while True:
                future = self.future
                if future is None:
                    raise Exception("No pending future")
                if not future.done():
                    return
                self.future = None
                try:
                    try:
                        value = future.result()
                    except Exception as e:
                        # Save the exception for later. It's important that
                        # gen.throw() not be called inside this try/except block
                        # because that makes sys.exc_info behave unexpectedly.
                        exc: Optional[Exception] = e
                    else:
                        exc = None
                    finally:
                        future = None

                    if exc is not None:
                        try:
                            yielded = self.gen.throw(exc)
                        finally:
                            # Break up a circular reference for faster GC on
                            # CPython.
                            del exc
                    else:
                        yielded = self.gen.send(value)

                except (StopIteration, Return) as e:
                    self.finished = True
                    self.future = _null_future
                    future_set_result_unless_cancelled(
                        self.result_future, _value_from_stopiteration(e)
                    )
                    self.result_future = None  # type: ignore
                    return
                except Exception:
                    self.finished = True
                    self.future = _null_future
                    future_set_exc_info(self.result_future, sys.exc_info())
                    self.result_future = None  # type: ignore
                    return
                if not self.handle_yield(yielded):
                    return
                yielded = None
        finally:
            self.running = False

    def handle_yield(self, yielded: _Yieldable) -> bool:
        try:
            self.future = convert_yielded(yielded)
        except BadYieldError:
            self.future = Future()
            future_set_exc_info(self.future, sys.exc_info())

        if self.future is moment:
            self.io_loop.add_callback(self.ctx_run, self.run)
            return False
        elif self.future is None:
            raise Exception("no pending future")
        elif not self.future.done():

            def inner(f: Any) -> None:
                # Break a reference cycle to speed GC.
                f = None  # noqa: F841
                self.ctx_run(self.run)

            self.io_loop.add_future(self.future, inner)
            return False
        return True

    def handle_exception(
        self, typ: Type[Exception], value: Exception, tb: types.TracebackType
    ) -> bool:
        if not self.running and not self.finished:
            self.future = Future()
            future_set_exc_info(self.future, (typ, value, tb))
            self.ctx_run(self.run)
            return True
        else:
            return False


def _wrap_awaitable(awaitable: Awaitable) -> Future:
    # Convert Awaitables into Futures.
    # Note that we use ensure_future, which handles both awaitables
    # and coroutines, rather than create_task, which only accepts
    # coroutines. (ensure_future calls create_task if given a coroutine)
    fut = asyncio.ensure_future(awaitable)
    # See comments on IOLoop._pending_tasks.
    loop = IOLoop.current()
    loop._register_task(fut)
    fut.add_done_callback(lambda f: loop._unregister_task(f))
    return fut


def convert_yielded(yielded: _Yieldable) -> Future:
    """Convert a yielded object into a `.Future`.

    The default implementation accepts lists, dictionaries, and
    Futures. This has the side effect of starting any coroutines that
    did not start themselves, similar to `asyncio.ensure_future`.

    If the `~functools.singledispatch` library is available, this function
    may be extended to support additional types. For example::

        @convert_yielded.register(asyncio.Future)
        def _(asyncio_future):
            return tornado.platform.asyncio.to_tornado_future(asyncio_future)

    .. versionadded:: 4.1

    """
    if yielded is None or yielded is moment:
        return moment
    elif yielded is _null_future:
        return _null_future
    elif isinstance(yielded, (list, dict)):
        return multi(yielded)  # type: ignore
    elif is_future(yielded):
        return typing.cast(Future, yielded)
    elif isawaitable(yielded):
        return _wrap_awaitable(yielded)  # type: ignore
    else:
        raise BadYieldError(f"yielded unknown object {yielded!r}")


convert_yielded = singledispatch(convert_yielded)

# === NexusCore/openenv\Lib\site-packages\nltk\sentiment\util.py ===
#
# Natural Language Toolkit: Sentiment Analyzer
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Pierpaolo Pantone <24alsecondo@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Utility methods for Sentiment Analysis.
"""

import codecs
import csv
import json
import random
import re
import sys
import time
from copy import deepcopy

import nltk
from nltk.corpus import CategorizedPlaintextCorpusReader
from nltk.data import load
from nltk.tokenize import PunktTokenizer
from nltk.tokenize.casual import EMOTICON_RE

# ////////////////////////////////////////////////////////////
# { Regular expressions
# ////////////////////////////////////////////////////////////

# Regular expression for negation by Christopher Potts
NEGATION = r"""
    (?:
        ^(?:never|no|nothing|nowhere|noone|none|not|
            havent|hasnt|hadnt|cant|couldnt|shouldnt|
            wont|wouldnt|dont|doesnt|didnt|isnt|arent|aint
        )$
    )
    |
    n't"""

NEGATION_RE = re.compile(NEGATION, re.VERBOSE)

CLAUSE_PUNCT = r"^[.:;!?]$"
CLAUSE_PUNCT_RE = re.compile(CLAUSE_PUNCT)

# Happy and sad emoticons

HAPPY = {
    ":-)",
    ":)",
    ";)",
    ":o)",
    ":]",
    ":3",
    ":c)",
    ":>",
    "=]",
    "8)",
    "=)",
    ":}",
    ":^)",
    ":-D",
    ":D",
    "8-D",
    "8D",
    "x-D",
    "xD",
    "X-D",
    "XD",
    "=-D",
    "=D",
    "=-3",
    "=3",
    ":-))",
    ":'-)",
    ":')",
    ":*",
    ":^*",
    ">:P",
    ":-P",
    ":P",
    "X-P",
    "x-p",
    "xp",
    "XP",
    ":-p",
    ":p",
    "=p",
    ":-b",
    ":b",
    ">:)",
    ">;)",
    ">:-)",
    "<3",
}

SAD = {
    ":L",
    ":-/",
    ">:/",
    ":S",
    ">:[",
    ":@",
    ":-(",
    ":[",
    ":-||",
    "=L",
    ":<",
    ":-[",
    ":-<",
    "=\\",
    "=/",
    ">:(",
    ":(",
    ">.<",
    ":'-(",
    ":'(",
    ":\\",
    ":-c",
    ":c",
    ":{",
    ">:\\",
    ";(",
}


def timer(method):
    """
    A timer decorator to measure execution performance of methods.
    """

    def timed(*args, **kw):
        start = time.time()
        result = method(*args, **kw)
        end = time.time()
        tot_time = end - start
        hours = tot_time // 3600
        mins = tot_time // 60 % 60
        # in Python 2.x round() will return a float, so we convert it to int
        secs = int(round(tot_time % 60))
        if hours == 0 and mins == 0 and secs < 10:
            print(f"[TIMER] {method.__name__}(): {method.__name__:.3f} seconds")
        else:
            print(f"[TIMER] {method.__name__}(): {hours}h {mins}m {secs}s")
        return result

    return timed


# ////////////////////////////////////////////////////////////
# { Feature extractor functions
# ////////////////////////////////////////////////////////////
"""
Feature extractor functions are declared outside the SentimentAnalyzer class.
Users should have the possibility to create their own feature extractors
without modifying SentimentAnalyzer.
"""


def extract_unigram_feats(document, unigrams, handle_negation=False):
    """
    Populate a dictionary of unigram features, reflecting the presence/absence in
    the document of each of the tokens in `unigrams`.

    :param document: a list of words/tokens.
    :param unigrams: a list of words/tokens whose presence/absence has to be
        checked in `document`.
    :param handle_negation: if `handle_negation == True` apply `mark_negation`
        method to `document` before checking for unigram presence/absence.
    :return: a dictionary of unigram features {unigram : boolean}.

    >>> words = ['ice', 'police', 'riot']
    >>> document = 'ice is melting due to global warming'.split()
    >>> sorted(extract_unigram_feats(document, words).items())
    [('contains(ice)', True), ('contains(police)', False), ('contains(riot)', False)]
    """
    features = {}
    if handle_negation:
        document = mark_negation(document)
    for word in unigrams:
        features[f"contains({word})"] = word in set(document)
    return features


def extract_bigram_feats(document, bigrams):
    """
    Populate a dictionary of bigram features, reflecting the presence/absence in
    the document of each of the tokens in `bigrams`. This extractor function only
    considers contiguous bigrams obtained by `nltk.bigrams`.

    :param document: a list of words/tokens.
    :param unigrams: a list of bigrams whose presence/absence has to be
        checked in `document`.
    :return: a dictionary of bigram features {bigram : boolean}.

    >>> bigrams = [('global', 'warming'), ('police', 'prevented'), ('love', 'you')]
    >>> document = 'ice is melting due to global warming'.split()
    >>> sorted(extract_bigram_feats(document, bigrams).items()) # doctest: +NORMALIZE_WHITESPACE
    [('contains(global - warming)', True), ('contains(love - you)', False),
    ('contains(police - prevented)', False)]
    """
    features = {}
    for bigr in bigrams:
        features[f"contains({bigr[0]} - {bigr[1]})"] = bigr in nltk.bigrams(document)
    return features


# ////////////////////////////////////////////////////////////
# { Helper Functions
# ////////////////////////////////////////////////////////////


def mark_negation(document, double_neg_flip=False, shallow=False):
    """
    Append _NEG suffix to words that appear in the scope between a negation
    and a punctuation mark.

    :param document: a list of words/tokens, or a tuple (words, label).
    :param shallow: if True, the method will modify the original document in place.
    :param double_neg_flip: if True, double negation is considered affirmation
        (we activate/deactivate negation scope every time we find a negation).
    :return: if `shallow == True` the method will modify the original document
        and return it. If `shallow == False` the method will return a modified
        document, leaving the original unmodified.

    >>> sent = "I didn't like this movie . It was bad .".split()
    >>> mark_negation(sent)
    ['I', "didn't", 'like_NEG', 'this_NEG', 'movie_NEG', '.', 'It', 'was', 'bad', '.']
    """
    if not shallow:
        document = deepcopy(document)
    # check if the document is labeled. If so, do not consider the label.
    labeled = document and isinstance(document[0], (tuple, list))
    if labeled:
        doc = document[0]
    else:
        doc = document
    neg_scope = False
    for i, word in enumerate(doc):
        if NEGATION_RE.search(word):
            if not neg_scope or (neg_scope and double_neg_flip):
                neg_scope = not neg_scope
                continue
            else:
                doc[i] += "_NEG"
        elif neg_scope and CLAUSE_PUNCT_RE.search(word):
            neg_scope = not neg_scope
        elif neg_scope and not CLAUSE_PUNCT_RE.search(word):
            doc[i] += "_NEG"

    return document


def output_markdown(filename, **kwargs):
    """
    Write the output of an analysis to a file.
    """
    with codecs.open(filename, "at") as outfile:
        text = "\n*** \n\n"
        text += "{} \n\n".format(time.strftime("%d/%m/%Y, %H:%M"))
        for k in sorted(kwargs):
            if isinstance(kwargs[k], dict):
                dictionary = kwargs[k]
                text += f"  - **{k}:**\n"
                for entry in sorted(dictionary):
                    text += f"    - {entry}: {dictionary[entry]} \n"
            elif isinstance(kwargs[k], list):
                text += f"  - **{k}:**\n"
                for entry in kwargs[k]:
                    text += f"    - {entry}\n"
            else:
                text += f"  - **{k}:** {kwargs[k]} \n"
        outfile.write(text)


def split_train_test(all_instances, n=None):
    """
    Randomly split `n` instances of the dataset into train and test sets.

    :param all_instances: a list of instances (e.g. documents) that will be split.
    :param n: the number of instances to consider (in case we want to use only a
        subset).
    :return: two lists of instances. Train set is 8/10 of the total and test set
        is 2/10 of the total.
    """
    random.seed(12345)
    random.shuffle(all_instances)
    if not n or n > len(all_instances):
        n = len(all_instances)
    train_set = all_instances[: int(0.8 * n)]
    test_set = all_instances[int(0.8 * n) : n]

    return train_set, test_set


def _show_plot(x_values, y_values, x_labels=None, y_labels=None):
    try:
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise ImportError(
            "The plot function requires matplotlib to be installed."
            "See https://matplotlib.org/"
        ) from e

    plt.locator_params(axis="y", nbins=3)
    axes = plt.axes()
    axes.yaxis.grid()
    plt.plot(x_values, y_values, "ro", color="red")
    plt.ylim(ymin=-1.2, ymax=1.2)
    plt.tight_layout(pad=5)
    if x_labels:
        plt.xticks(x_values, x_labels, rotation="vertical")
    if y_labels:
        plt.yticks([-1, 0, 1], y_labels, rotation="horizontal")
    # Pad margins so that markers are not clipped by the axes
    plt.margins(0.2)
    plt.show()


# ////////////////////////////////////////////////////////////
# { Parsing and conversion functions
# ////////////////////////////////////////////////////////////


def json2csv_preprocess(
    json_file,
    outfile,
    fields,
    encoding="utf8",
    errors="replace",
    gzip_compress=False,
    skip_retweets=True,
    skip_tongue_tweets=True,
    skip_ambiguous_tweets=True,
    strip_off_emoticons=True,
    remove_duplicates=True,
    limit=None,
):
    """
    Convert json file to csv file, preprocessing each row to obtain a suitable
    dataset for tweets Semantic Analysis.

    :param json_file: the original json file containing tweets.
    :param outfile: the output csv filename.
    :param fields: a list of fields that will be extracted from the json file and
        kept in the output csv file.
    :param encoding: the encoding of the files.
    :param errors: the error handling strategy for the output writer.
    :param gzip_compress: if True, create a compressed GZIP file.

    :param skip_retweets: if True, remove retweets.
    :param skip_tongue_tweets: if True, remove tweets containing ":P" and ":-P"
        emoticons.
    :param skip_ambiguous_tweets: if True, remove tweets containing both happy
        and sad emoticons.
    :param strip_off_emoticons: if True, strip off emoticons from all tweets.
    :param remove_duplicates: if True, remove tweets appearing more than once.
    :param limit: an integer to set the number of tweets to convert. After the
        limit is reached the conversion will stop. It can be useful to create
        subsets of the original tweets json data.
    """
    with codecs.open(json_file, encoding=encoding) as fp:
        (writer, outf) = _outf_writer(outfile, encoding, errors, gzip_compress)
        # write the list of fields as header
        writer.writerow(fields)

        if remove_duplicates == True:
            tweets_cache = []
        i = 0
        for line in fp:
            tweet = json.loads(line)
            row = extract_fields(tweet, fields)
            try:
                text = row[fields.index("text")]
                # Remove retweets
                if skip_retweets == True:
                    if re.search(r"\bRT\b", text):
                        continue
                # Remove tweets containing ":P" and ":-P" emoticons
                if skip_tongue_tweets == True:
                    if re.search(r"\:\-?P\b", text):
                        continue
                # Remove tweets containing both happy and sad emoticons
                if skip_ambiguous_tweets == True:
                    all_emoticons = EMOTICON_RE.findall(text)
                    if all_emoticons:
                        if (set(all_emoticons) & HAPPY) and (set(all_emoticons) & SAD):
                            continue
                # Strip off emoticons from all tweets
                if strip_off_emoticons == True:
                    row[fields.index("text")] = re.sub(
                        r"(?!\n)\s+", " ", EMOTICON_RE.sub("", text)
                    )
                # Remove duplicate tweets
                if remove_duplicates == True:
                    if row[fields.index("text")] in tweets_cache:
                        continue
                    else:
                        tweets_cache.append(row[fields.index("text")])
            except ValueError:
                pass
            writer.writerow(row)
            i += 1
            if limit and i >= limit:
                break
        outf.close()


def parse_tweets_set(
    filename, label, word_tokenizer=None, sent_tokenizer=None, skip_header=True
):
    """
    Parse csv file containing tweets and output data a list of (text, label) tuples.

    :param filename: the input csv filename.
    :param label: the label to be appended to each tweet contained in the csv file.
    :param word_tokenizer: the tokenizer instance that will be used to tokenize
        each sentence into tokens (e.g. WordPunctTokenizer() or BlanklineTokenizer()).
        If no word_tokenizer is specified, tweets will not be tokenized.
    :param sent_tokenizer: the tokenizer that will be used to split each tweet into
        sentences.
    :param skip_header: if True, skip the first line of the csv file (which usually
        contains headers).

    :return: a list of (text, label) tuples.
    """
    tweets = []
    if not sent_tokenizer:
        sent_tokenizer = PunktTokenizer()

    with codecs.open(filename, "rt") as csvfile:
        reader = csv.reader(csvfile)
        if skip_header == True:
            next(reader, None)  # skip the header
        i = 0
        for tweet_id, text in reader:
            # text = text[1]
            i += 1
            sys.stdout.write(f"Loaded {i} tweets\r")
            # Apply sentence and word tokenizer to text
            if word_tokenizer:
                tweet = [
                    w
                    for sent in sent_tokenizer.tokenize(text)
                    for w in word_tokenizer.tokenize(sent)
                ]
            else:
                tweet = text
            tweets.append((tweet, label))

    print(f"Loaded {i} tweets")
    return tweets


# ////////////////////////////////////////////////////////////
# { Demos
# ////////////////////////////////////////////////////////////


def demo_tweets(trainer, n_instances=None, output=None):
    """
    Train and test Naive Bayes classifier on 10000 tweets, tokenized using
    TweetTokenizer.
    Features are composed of:

    - 1000 most frequent unigrams
    - 100 top bigrams (using BigramAssocMeasures.pmi)

    :param trainer: `train` method of a classifier.
    :param n_instances: the number of total tweets that have to be used for
        training and testing. Tweets will be equally split between positive and
        negative.
    :param output: the output file where results have to be reported.
    """
    from nltk.corpus import stopwords, twitter_samples
    from nltk.sentiment import SentimentAnalyzer
    from nltk.tokenize import TweetTokenizer

    # Different customizations for the TweetTokenizer
    tokenizer = TweetTokenizer(preserve_case=False)
    # tokenizer = TweetTokenizer(preserve_case=True, strip_handles=True)
    # tokenizer = TweetTokenizer(reduce_len=True, strip_handles=True)

    if n_instances is not None:
        n_instances = int(n_instances / 2)

    fields = ["id", "text"]
    positive_json = twitter_samples.abspath("positive_tweets.json")
    positive_csv = "positive_tweets.csv"
    json2csv_preprocess(positive_json, positive_csv, fields, limit=n_instances)

    negative_json = twitter_samples.abspath("negative_tweets.json")
    negative_csv = "negative_tweets.csv"
    json2csv_preprocess(negative_json, negative_csv, fields, limit=n_instances)

    neg_docs = parse_tweets_set(negative_csv, label="neg", word_tokenizer=tokenizer)
    pos_docs = parse_tweets_set(positive_csv, label="pos", word_tokenizer=tokenizer)

    # We separately split subjective and objective instances to keep a balanced
    # uniform class distribution in both train and test sets.
    train_pos_docs, test_pos_docs = split_train_test(pos_docs)
    train_neg_docs, test_neg_docs = split_train_test(neg_docs)

    training_tweets = train_pos_docs + train_neg_docs
    testing_tweets = test_pos_docs + test_neg_docs

    sentim_analyzer = SentimentAnalyzer()
    # stopwords = stopwords.words('english')
    # all_words = [word for word in sentim_analyzer.all_words(training_tweets) if word.lower() not in stopwords]
    all_words = [word for word in sentim_analyzer.all_words(training_tweets)]

    # Add simple unigram word features
    unigram_feats = sentim_analyzer.unigram_word_feats(all_words, top_n=1000)
    sentim_analyzer.add_feat_extractor(extract_unigram_feats, unigrams=unigram_feats)

    # Add bigram collocation features
    bigram_collocs_feats = sentim_analyzer.bigram_collocation_feats(
        [tweet[0] for tweet in training_tweets], top_n=100, min_freq=12
    )
    sentim_analyzer.add_feat_extractor(
        extract_bigram_feats, bigrams=bigram_collocs_feats
    )

    training_set = sentim_analyzer.apply_features(training_tweets)
    test_set = sentim_analyzer.apply_features(testing_tweets)

    classifier = sentim_analyzer.train(trainer, training_set)
    # classifier = sentim_analyzer.train(trainer, training_set, max_iter=4)
    try:
        classifier.show_most_informative_features()
    except AttributeError:
        print(
            "Your classifier does not provide a show_most_informative_features() method."
        )
    results = sentim_analyzer.evaluate(test_set)

    if output:
        extr = [f.__name__ for f in sentim_analyzer.feat_extractors]
        output_markdown(
            output,
            Dataset="labeled_tweets",
            Classifier=type(classifier).__name__,
            Tokenizer=tokenizer.__class__.__name__,
            Feats=extr,
            Results=results,
            Instances=n_instances,
        )


def demo_movie_reviews(trainer, n_instances=None, output=None):
    """
    Train classifier on all instances of the Movie Reviews dataset.
    The corpus has been preprocessed using the default sentence tokenizer and
    WordPunctTokenizer.
    Features are composed of:

    - most frequent unigrams

    :param trainer: `train` method of a classifier.
    :param n_instances: the number of total reviews that have to be used for
        training and testing. Reviews will be equally split between positive and
        negative.
    :param output: the output file where results have to be reported.
    """
    from nltk.corpus import movie_reviews
    from nltk.sentiment import SentimentAnalyzer

    if n_instances is not None:
        n_instances = int(n_instances / 2)

    pos_docs = [
        (list(movie_reviews.words(pos_id)), "pos")
        for pos_id in movie_reviews.fileids("pos")[:n_instances]
    ]
    neg_docs = [
        (list(movie_reviews.words(neg_id)), "neg")
        for neg_id in movie_reviews.fileids("neg")[:n_instances]
    ]
    # We separately split positive and negative instances to keep a balanced
    # uniform class distribution in both train and test sets.
    train_pos_docs, test_pos_docs = split_train_test(pos_docs)
    train_neg_docs, test_neg_docs = split_train_test(neg_docs)

    training_docs = train_pos_docs + train_neg_docs
    testing_docs = test_pos_docs + test_neg_docs

    sentim_analyzer = SentimentAnalyzer()
    all_words = sentim_analyzer.all_words(training_docs)

    # Add simple unigram word features
    unigram_feats = sentim_analyzer.unigram_word_feats(all_words, min_freq=4)
    sentim_analyzer.add_feat_extractor(extract_unigram_feats, unigrams=unigram_feats)
    # Apply features to obtain a feature-value representation of our datasets
    training_set = sentim_analyzer.apply_features(training_docs)
    test_set = sentim_analyzer.apply_features(testing_docs)

    classifier = sentim_analyzer.train(trainer, training_set)
    try:
        classifier.show_most_informative_features()
    except AttributeError:
        print(
            "Your classifier does not provide a show_most_informative_features() method."
        )
    results = sentim_analyzer.evaluate(test_set)

    if output:
        extr = [f.__name__ for f in sentim_analyzer.feat_extractors]
        output_markdown(
            output,
            Dataset="Movie_reviews",
            Classifier=type(classifier).__name__,
            Tokenizer="WordPunctTokenizer",
            Feats=extr,
            Results=results,
            Instances=n_instances,
        )


def demo_subjectivity(trainer, save_analyzer=False, n_instances=None, output=None):
    """
    Train and test a classifier on instances of the Subjective Dataset by Pang and
    Lee. The dataset is made of 5000 subjective and 5000 objective sentences.
    All tokens (words and punctuation marks) are separated by a whitespace, so
    we use the basic WhitespaceTokenizer to parse the data.

    :param trainer: `train` method of a classifier.
    :param save_analyzer: if `True`, store the SentimentAnalyzer in a pickle file.
    :param n_instances: the number of total sentences that have to be used for
        training and testing. Sentences will be equally split between positive
        and negative.
    :param output: the output file where results have to be reported.
    """
    from nltk.corpus import subjectivity
    from nltk.sentiment import SentimentAnalyzer

    if n_instances is not None:
        n_instances = int(n_instances / 2)

    subj_docs = [
        (sent, "subj") for sent in subjectivity.sents(categories="subj")[:n_instances]
    ]
    obj_docs = [
        (sent, "obj") for sent in subjectivity.sents(categories="obj")[:n_instances]
    ]

    # We separately split subjective and objective instances to keep a balanced
    # uniform class distribution in both train and test sets.
    train_subj_docs, test_subj_docs = split_train_test(subj_docs)
    train_obj_docs, test_obj_docs = split_train_test(obj_docs)

    training_docs = train_subj_docs + train_obj_docs
    testing_docs = test_subj_docs + test_obj_docs

    sentim_analyzer = SentimentAnalyzer()
    all_words_neg = sentim_analyzer.all_words(
        [mark_negation(doc) for doc in training_docs]
    )

    # Add simple unigram word features handling negation
    unigram_feats = sentim_analyzer.unigram_word_feats(all_words_neg, min_freq=4)
    sentim_analyzer.add_feat_extractor(extract_unigram_feats, unigrams=unigram_feats)

    # Apply features to obtain a feature-value representation of our datasets
    training_set = sentim_analyzer.apply_features(training_docs)
    test_set = sentim_analyzer.apply_features(testing_docs)

    classifier = sentim_analyzer.train(trainer, training_set)
    try:
        classifier.show_most_informative_features()
    except AttributeError:
        print(
            "Your classifier does not provide a show_most_informative_features() method."
        )
    results = sentim_analyzer.evaluate(test_set)

    if save_analyzer == True:
        sentim_analyzer.save_file(sentim_analyzer, "sa_subjectivity.pickle")

    if output:
        extr = [f.__name__ for f in sentim_analyzer.feat_extractors]
        output_markdown(
            output,
            Dataset="subjectivity",
            Classifier=type(classifier).__name__,
            Tokenizer="WhitespaceTokenizer",
            Feats=extr,
            Instances=n_instances,
            Results=results,
        )

    return sentim_analyzer


def demo_sent_subjectivity(text):
    """
    Classify a single sentence as subjective or objective using a stored
    SentimentAnalyzer.

    :param text: a sentence whose subjectivity has to be classified.
    """
    from nltk.classify import NaiveBayesClassifier
    from nltk.tokenize import regexp

    word_tokenizer = regexp.WhitespaceTokenizer()
    try:
        sentim_analyzer = load("sa_subjectivity.pickle")
    except LookupError:
        print("Cannot find the sentiment analyzer you want to load.")
        print("Training a new one using NaiveBayesClassifier.")
        sentim_analyzer = demo_subjectivity(NaiveBayesClassifier.train, True)

    # Tokenize and convert to lower case
    tokenized_text = [word.lower() for word in word_tokenizer.tokenize(text)]
    print(sentim_analyzer.classify(tokenized_text))


def demo_liu_hu_lexicon(sentence, plot=False):
    """
    Basic example of sentiment classification using Liu and Hu opinion lexicon.
    This function simply counts the number of positive, negative and neutral words
    in the sentence and classifies it depending on which polarity is more represented.
    Words that do not appear in the lexicon are considered as neutral.

    :param sentence: a sentence whose polarity has to be classified.
    :param plot: if True, plot a visual representation of the sentence polarity.
    """
    from nltk.corpus import opinion_lexicon
    from nltk.tokenize import treebank

    tokenizer = treebank.TreebankWordTokenizer()
    pos_words = 0
    neg_words = 0
    tokenized_sent = [word.lower() for word in tokenizer.tokenize(sentence)]

    x = list(range(len(tokenized_sent)))  # x axis for the plot
    y = []

    for word in tokenized_sent:
        if word in opinion_lexicon.positive():
            pos_words += 1
            y.append(1)  # positive
        elif word in opinion_lexicon.negative():
            neg_words += 1
            y.append(-1)  # negative
        else:
            y.append(0)  # neutral

    if pos_words > neg_words:
        print("Positive")
    elif pos_words < neg_words:
        print("Negative")
    elif pos_words == neg_words:
        print("Neutral")

    if plot == True:
        _show_plot(
            x, y, x_labels=tokenized_sent, y_labels=["Negative", "Neutral", "Positive"]
        )


def demo_vader_instance(text):
    """
    Output polarity scores for a text using Vader approach.

    :param text: a text whose polarity has to be evaluated.
    """
    from nltk.sentiment import SentimentIntensityAnalyzer

    vader_analyzer = SentimentIntensityAnalyzer()
    print(vader_analyzer.polarity_scores(text))


def demo_vader_tweets(n_instances=None, output=None):
    """
    Classify 10000 positive and negative tweets using Vader approach.

    :param n_instances: the number of total tweets that have to be classified.
    :param output: the output file where results have to be reported.
    """
    from collections import defaultdict

    from nltk.corpus import twitter_samples
    from nltk.metrics import accuracy as eval_accuracy
    from nltk.metrics import f_measure as eval_f_measure
    from nltk.metrics import precision as eval_precision
    from nltk.metrics import recall as eval_recall
    from nltk.sentiment import SentimentIntensityAnalyzer

    if n_instances is not None:
        n_instances = int(n_instances / 2)

    fields = ["id", "text"]
    positive_json = twitter_samples.abspath("positive_tweets.json")
    positive_csv = "positive_tweets.csv"
    json2csv_preprocess(
        positive_json,
        positive_csv,
        fields,
        strip_off_emoticons=False,
        limit=n_instances,
    )

    negative_json = twitter_samples.abspath("negative_tweets.json")
    negative_csv = "negative_tweets.csv"
    json2csv_preprocess(
        negative_json,
        negative_csv,
        fields,
        strip_off_emoticons=False,
        limit=n_instances,
    )

    pos_docs = parse_tweets_set(positive_csv, label="pos")
    neg_docs = parse_tweets_set(negative_csv, label="neg")

    # We separately split subjective and objective instances to keep a balanced
    # uniform class distribution in both train and test sets.
    train_pos_docs, test_pos_docs = split_train_test(pos_docs)
    train_neg_docs, test_neg_docs = split_train_test(neg_docs)

    training_tweets = train_pos_docs + train_neg_docs
    testing_tweets = test_pos_docs + test_neg_docs

    vader_analyzer = SentimentIntensityAnalyzer()

    gold_results = defaultdict(set)
    test_results = defaultdict(set)
    acc_gold_results = []
    acc_test_results = []
    labels = set()
    num = 0
    for i, (text, label) in enumerate(testing_tweets):
        labels.add(label)
        gold_results[label].add(i)
        acc_gold_results.append(label)
        score = vader_analyzer.polarity_scores(text)["compound"]
        if score > 0:
            observed = "pos"
        else:
            observed = "neg"
        num += 1
        acc_test_results.append(observed)
        test_results[observed].add(i)
    metrics_results = {}
    for label in labels:
        accuracy_score = eval_accuracy(acc_gold_results, acc_test_results)
        metrics_results["Accuracy"] = accuracy_score
        precision_score = eval_precision(gold_results[label], test_results[label])
        metrics_results[f"Precision [{label}]"] = precision_score
        recall_score = eval_recall(gold_results[label], test_results[label])
        metrics_results[f"Recall [{label}]"] = recall_score
        f_measure_score = eval_f_measure(gold_results[label], test_results[label])
        metrics_results[f"F-measure [{label}]"] = f_measure_score

    for result in sorted(metrics_results):
        print(f"{result}: {metrics_results[result]}")

    if output:
        output_markdown(
            output,
            Approach="Vader",
            Dataset="labeled_tweets",
            Instances=n_instances,
            Results=metrics_results,
        )


if __name__ == "__main__":
    from sklearn.svm import LinearSVC

    from nltk.classify import MaxentClassifier, NaiveBayesClassifier
    from nltk.classify.scikitlearn import SklearnClassifier
    from nltk.twitter.common import _outf_writer, extract_fields

    naive_bayes = NaiveBayesClassifier.train
    svm = SklearnClassifier(LinearSVC()).train
    maxent = MaxentClassifier.train

    demo_tweets(naive_bayes)
    # demo_movie_reviews(svm)
    # demo_subjectivity(svm)
    # demo_sent_subjectivity("she's an artist , but hasn't picked up a brush in a year . ")
    # demo_liu_hu_lexicon("This movie was actually neither that funny, nor super witty.", plot=True)
    # demo_vader_instance("This movie was actually neither that funny, nor super witty.")
    # demo_vader_tweets()

# === NexusCore/openenv\Lib\site-packages\tornado\http1connection.py ===
#
# Copyright 2014 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Client and server implementations of HTTP/1.x.

.. versionadded:: 4.0
"""

import asyncio
import logging
import re
import types

from tornado.concurrent import (
    Future,
    future_add_done_callback,
    future_set_result_unless_cancelled,
)
from tornado.escape import native_str, utf8
from tornado import gen
from tornado import httputil
from tornado import iostream
from tornado.log import gen_log, app_log
from tornado.util import GzipDecompressor


from typing import cast, Optional, Type, Awaitable, Callable, Union, Tuple

CR_OR_LF_RE = re.compile(b"\r|\n")


class _QuietException(Exception):
    def __init__(self) -> None:
        pass


class _ExceptionLoggingContext:
    """Used with the ``with`` statement when calling delegate methods to
    log any exceptions with the given logger.  Any exceptions caught are
    converted to _QuietException
    """

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def __enter__(self) -> None:
        pass

    def __exit__(
        self,
        typ: "Optional[Type[BaseException]]",
        value: Optional[BaseException],
        tb: types.TracebackType,
    ) -> None:
        if value is not None:
            assert typ is not None
            self.logger.error("Uncaught exception", exc_info=(typ, value, tb))
            raise _QuietException


class HTTP1ConnectionParameters:
    """Parameters for `.HTTP1Connection` and `.HTTP1ServerConnection`."""

    def __init__(
        self,
        no_keep_alive: bool = False,
        chunk_size: Optional[int] = None,
        max_header_size: Optional[int] = None,
        header_timeout: Optional[float] = None,
        max_body_size: Optional[int] = None,
        body_timeout: Optional[float] = None,
        decompress: bool = False,
    ) -> None:
        """
        :arg bool no_keep_alive: If true, always close the connection after
            one request.
        :arg int chunk_size: how much data to read into memory at once
        :arg int max_header_size:  maximum amount of data for HTTP headers
        :arg float header_timeout: how long to wait for all headers (seconds)
        :arg int max_body_size: maximum amount of data for body
        :arg float body_timeout: how long to wait while reading body (seconds)
        :arg bool decompress: if true, decode incoming
            ``Content-Encoding: gzip``
        """
        self.no_keep_alive = no_keep_alive
        self.chunk_size = chunk_size or 65536
        self.max_header_size = max_header_size or 65536
        self.header_timeout = header_timeout
        self.max_body_size = max_body_size
        self.body_timeout = body_timeout
        self.decompress = decompress


class HTTP1Connection(httputil.HTTPConnection):
    """Implements the HTTP/1.x protocol.

    This class can be on its own for clients, or via `HTTP1ServerConnection`
    for servers.
    """

    def __init__(
        self,
        stream: iostream.IOStream,
        is_client: bool,
        params: Optional[HTTP1ConnectionParameters] = None,
        context: Optional[object] = None,
    ) -> None:
        """
        :arg stream: an `.IOStream`
        :arg bool is_client: client or server
        :arg params: a `.HTTP1ConnectionParameters` instance or ``None``
        :arg context: an opaque application-defined object that can be accessed
            as ``connection.context``.
        """
        self.is_client = is_client
        self.stream = stream
        if params is None:
            params = HTTP1ConnectionParameters()
        self.params = params
        self.context = context
        self.no_keep_alive = params.no_keep_alive
        # The body limits can be altered by the delegate, so save them
        # here instead of just referencing self.params later.
        self._max_body_size = (
            self.params.max_body_size
            if self.params.max_body_size is not None
            else self.stream.max_buffer_size
        )
        self._body_timeout = self.params.body_timeout
        # _write_finished is set to True when finish() has been called,
        # i.e. there will be no more data sent.  Data may still be in the
        # stream's write buffer.
        self._write_finished = False
        # True when we have read the entire incoming body.
        self._read_finished = False
        # _finish_future resolves when all data has been written and flushed
        # to the IOStream.
        self._finish_future = Future()  # type: Future[None]
        # If true, the connection should be closed after this request
        # (after the response has been written in the server side,
        # and after it has been read in the client)
        self._disconnect_on_finish = False
        self._clear_callbacks()
        # Save the start lines after we read or write them; they
        # affect later processing (e.g. 304 responses and HEAD methods
        # have content-length but no bodies)
        self._request_start_line = None  # type: Optional[httputil.RequestStartLine]
        self._response_start_line = None  # type: Optional[httputil.ResponseStartLine]
        self._request_headers = None  # type: Optional[httputil.HTTPHeaders]
        # True if we are writing output with chunked encoding.
        self._chunking_output = False
        # While reading a body with a content-length, this is the
        # amount left to read.
        self._expected_content_remaining = None  # type: Optional[int]
        # A Future for our outgoing writes, returned by IOStream.write.
        self._pending_write = None  # type: Optional[Future[None]]

    def read_response(self, delegate: httputil.HTTPMessageDelegate) -> Awaitable[bool]:
        """Read a single HTTP response.

        Typical client-mode usage is to write a request using `write_headers`,
        `write`, and `finish`, and then call ``read_response``.

        :arg delegate: a `.HTTPMessageDelegate`

        Returns a `.Future` that resolves to a bool after the full response has
        been read. The result is true if the stream is still open.
        """
        if self.params.decompress:
            delegate = _GzipMessageDelegate(delegate, self.params.chunk_size)
        return self._read_message(delegate)

    async def _read_message(self, delegate: httputil.HTTPMessageDelegate) -> bool:
        need_delegate_close = False
        try:
            header_future = self.stream.read_until_regex(
                b"\r?\n\r?\n", max_bytes=self.params.max_header_size
            )
            if self.params.header_timeout is None:
                header_data = await header_future
            else:
                try:
                    header_data = await gen.with_timeout(
                        self.stream.io_loop.time() + self.params.header_timeout,
                        header_future,
                        quiet_exceptions=iostream.StreamClosedError,
                    )
                except gen.TimeoutError:
                    self.close()
                    return False
            start_line_str, headers = self._parse_headers(header_data)
            if self.is_client:
                resp_start_line = httputil.parse_response_start_line(start_line_str)
                self._response_start_line = resp_start_line
                start_line = (
                    resp_start_line
                )  # type: Union[httputil.RequestStartLine, httputil.ResponseStartLine]
                # TODO: this will need to change to support client-side keepalive
                self._disconnect_on_finish = False
            else:
                req_start_line = httputil.parse_request_start_line(start_line_str)
                self._request_start_line = req_start_line
                self._request_headers = headers
                start_line = req_start_line
                self._disconnect_on_finish = not self._can_keep_alive(
                    req_start_line, headers
                )
            need_delegate_close = True
            with _ExceptionLoggingContext(app_log):
                header_recv_future = delegate.headers_received(start_line, headers)
                if header_recv_future is not None:
                    await header_recv_future
            if self.stream is None:
                # We've been detached.
                need_delegate_close = False
                return False
            skip_body = False
            if self.is_client:
                assert isinstance(start_line, httputil.ResponseStartLine)
                if (
                    self._request_start_line is not None
                    and self._request_start_line.method == "HEAD"
                ):
                    skip_body = True
                code = start_line.code
                if code == 304:
                    # 304 responses may include the content-length header
                    # but do not actually have a body.
                    # http://tools.ietf.org/html/rfc7230#section-3.3
                    skip_body = True
                if 100 <= code < 200:
                    # 1xx responses should never indicate the presence of
                    # a body.
                    if "Content-Length" in headers or "Transfer-Encoding" in headers:
                        raise httputil.HTTPInputError(
                            "Response code %d cannot have body" % code
                        )
                    # TODO: client delegates will get headers_received twice
                    # in the case of a 100-continue.  Document or change?
                    await self._read_message(delegate)
            else:
                if headers.get("Expect") == "100-continue" and not self._write_finished:
                    self.stream.write(b"HTTP/1.1 100 (Continue)\r\n\r\n")
            if not skip_body:
                body_future = self._read_body(
                    resp_start_line.code if self.is_client else 0, headers, delegate
                )
                if body_future is not None:
                    if self._body_timeout is None:
                        await body_future
                    else:
                        try:
                            await gen.with_timeout(
                                self.stream.io_loop.time() + self._body_timeout,
                                body_future,
                                quiet_exceptions=iostream.StreamClosedError,
                            )
                        except gen.TimeoutError:
                            gen_log.info("Timeout reading body from %s", self.context)
                            self.stream.close()
                            return False
            self._read_finished = True
            if not self._write_finished or self.is_client:
                need_delegate_close = False
                with _ExceptionLoggingContext(app_log):
                    delegate.finish()
            # If we're waiting for the application to produce an asynchronous
            # response, and we're not detached, register a close callback
            # on the stream (we didn't need one while we were reading)
            if (
                not self._finish_future.done()
                and self.stream is not None
                and not self.stream.closed()
            ):
                self.stream.set_close_callback(self._on_connection_close)
                await self._finish_future
            if self.is_client and self._disconnect_on_finish:
                self.close()
            if self.stream is None:
                return False
        except httputil.HTTPInputError as e:
            gen_log.info("Malformed HTTP message from %s: %s", self.context, e)
            if not self.is_client:
                await self.stream.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
            self.close()
            return False
        finally:
            if need_delegate_close:
                with _ExceptionLoggingContext(app_log):
                    delegate.on_connection_close()
            header_future = None  # type: ignore
            self._clear_callbacks()
        return True

    def _clear_callbacks(self) -> None:
        """Clears the callback attributes.

        This allows the request handler to be garbage collected more
        quickly in CPython by breaking up reference cycles.
        """
        self._write_callback = None
        self._write_future = None  # type: Optional[Future[None]]
        self._close_callback = None  # type: Optional[Callable[[], None]]
        if self.stream is not None:
            self.stream.set_close_callback(None)

    def set_close_callback(self, callback: Optional[Callable[[], None]]) -> None:
        """Sets a callback that will be run when the connection is closed.

        Note that this callback is slightly different from
        `.HTTPMessageDelegate.on_connection_close`: The
        `.HTTPMessageDelegate` method is called when the connection is
        closed while receiving a message. This callback is used when
        there is not an active delegate (for example, on the server
        side this callback is used if the client closes the connection
        after sending its request but before receiving all the
        response.
        """
        self._close_callback = callback

    def _on_connection_close(self) -> None:
        # Note that this callback is only registered on the IOStream
        # when we have finished reading the request and are waiting for
        # the application to produce its response.
        if self._close_callback is not None:
            callback = self._close_callback
            self._close_callback = None
            callback()
        if not self._finish_future.done():
            future_set_result_unless_cancelled(self._finish_future, None)
        self._clear_callbacks()

    def close(self) -> None:
        if self.stream is not None:
            self.stream.close()
        self._clear_callbacks()
        if not self._finish_future.done():
            future_set_result_unless_cancelled(self._finish_future, None)

    def detach(self) -> iostream.IOStream:
        """Take control of the underlying stream.

        Returns the underlying `.IOStream` object and stops all further
        HTTP processing.  May only be called during
        `.HTTPMessageDelegate.headers_received`.  Intended for implementing
        protocols like websockets that tunnel over an HTTP handshake.
        """
        self._clear_callbacks()
        stream = self.stream
        self.stream = None  # type: ignore
        if not self._finish_future.done():
            future_set_result_unless_cancelled(self._finish_future, None)
        return stream

    def set_body_timeout(self, timeout: float) -> None:
        """Sets the body timeout for a single request.

        Overrides the value from `.HTTP1ConnectionParameters`.
        """
        self._body_timeout = timeout

    def set_max_body_size(self, max_body_size: int) -> None:
        """Sets the body size limit for a single request.

        Overrides the value from `.HTTP1ConnectionParameters`.
        """
        self._max_body_size = max_body_size

    def write_headers(
        self,
        start_line: Union[httputil.RequestStartLine, httputil.ResponseStartLine],
        headers: httputil.HTTPHeaders,
        chunk: Optional[bytes] = None,
    ) -> "Future[None]":
        """Implements `.HTTPConnection.write_headers`."""
        lines = []
        if self.is_client:
            assert isinstance(start_line, httputil.RequestStartLine)
            self._request_start_line = start_line
            lines.append(utf8(f"{start_line[0]} {start_line[1]} HTTP/1.1"))
            # Client requests with a non-empty body must have either a
            # Content-Length or a Transfer-Encoding. If Content-Length is not
            # present we'll add our Transfer-Encoding below.
            self._chunking_output = (
                start_line.method in ("POST", "PUT", "PATCH")
                and "Content-Length" not in headers
            )
        else:
            assert isinstance(start_line, httputil.ResponseStartLine)
            assert self._request_start_line is not None
            assert self._request_headers is not None
            self._response_start_line = start_line
            lines.append(utf8("HTTP/1.1 %d %s" % (start_line[1], start_line[2])))
            self._chunking_output = (
                # TODO: should this use
                # self._request_start_line.version or
                # start_line.version?
                self._request_start_line.version == "HTTP/1.1"
                # Omit payload header field for HEAD request.
                and self._request_start_line.method != "HEAD"
                # 1xx, 204 and 304 responses have no body (not even a zero-length
                # body), and so should not have either Content-Length or
                # Transfer-Encoding headers.
                and start_line.code not in (204, 304)
                and (start_line.code < 100 or start_line.code >= 200)
                # No need to chunk the output if a Content-Length is specified.
                and "Content-Length" not in headers
            )
            # If connection to a 1.1 client will be closed, inform client
            if (
                self._request_start_line.version == "HTTP/1.1"
                and self._disconnect_on_finish
            ):
                headers["Connection"] = "close"
            # If a 1.0 client asked for keep-alive, add the header.
            if (
                self._request_start_line.version == "HTTP/1.0"
                and self._request_headers.get("Connection", "").lower() == "keep-alive"
            ):
                headers["Connection"] = "Keep-Alive"
        if self._chunking_output:
            headers["Transfer-Encoding"] = "chunked"
        if not self.is_client and (
            self._request_start_line.method == "HEAD"
            or cast(httputil.ResponseStartLine, start_line).code == 304
        ):
            self._expected_content_remaining = 0
        elif "Content-Length" in headers:
            self._expected_content_remaining = parse_int(headers["Content-Length"])
        else:
            self._expected_content_remaining = None
        # TODO: headers are supposed to be of type str, but we still have some
        # cases that let bytes slip through. Remove these native_str calls when those
        # are fixed.
        header_lines = (
            native_str(n) + ": " + native_str(v) for n, v in headers.get_all()
        )
        lines.extend(line.encode("latin1") for line in header_lines)
        for line in lines:
            if CR_OR_LF_RE.search(line):
                raise ValueError("Illegal characters (CR or LF) in header: %r" % line)
        future = None
        if self.stream.closed():
            future = self._write_future = Future()
            future.set_exception(iostream.StreamClosedError())
            future.exception()
        else:
            future = self._write_future = Future()
            data = b"\r\n".join(lines) + b"\r\n\r\n"
            if chunk:
                data += self._format_chunk(chunk)
            self._pending_write = self.stream.write(data)
            future_add_done_callback(self._pending_write, self._on_write_complete)
        return future

    def _format_chunk(self, chunk: bytes) -> bytes:
        if self._expected_content_remaining is not None:
            self._expected_content_remaining -= len(chunk)
            if self._expected_content_remaining < 0:
                # Close the stream now to stop further framing errors.
                self.stream.close()
                raise httputil.HTTPOutputError(
                    "Tried to write more data than Content-Length"
                )
        if self._chunking_output and chunk:
            # Don't write out empty chunks because that means END-OF-STREAM
            # with chunked encoding
            return utf8("%x" % len(chunk)) + b"\r\n" + chunk + b"\r\n"
        else:
            return chunk

    def write(self, chunk: bytes) -> "Future[None]":
        """Implements `.HTTPConnection.write`.

        For backwards compatibility it is allowed but deprecated to
        skip `write_headers` and instead call `write()` with a
        pre-encoded header block.
        """
        future = None
        if self.stream.closed():
            future = self._write_future = Future()
            self._write_future.set_exception(iostream.StreamClosedError())
            self._write_future.exception()
        else:
            future = self._write_future = Future()
            self._pending_write = self.stream.write(self._format_chunk(chunk))
            future_add_done_callback(self._pending_write, self._on_write_complete)
        return future

    def finish(self) -> None:
        """Implements `.HTTPConnection.finish`."""
        if (
            self._expected_content_remaining is not None
            and self._expected_content_remaining != 0
            and not self.stream.closed()
        ):
            self.stream.close()
            raise httputil.HTTPOutputError(
                "Tried to write %d bytes less than Content-Length"
                % self._expected_content_remaining
            )
        if self._chunking_output:
            if not self.stream.closed():
                self._pending_write = self.stream.write(b"0\r\n\r\n")
                self._pending_write.add_done_callback(self._on_write_complete)
        self._write_finished = True
        # If the app finished the request while we're still reading,
        # divert any remaining data away from the delegate and
        # close the connection when we're done sending our response.
        # Closing the connection is the only way to avoid reading the
        # whole input body.
        if not self._read_finished:
            self._disconnect_on_finish = True
        # No more data is coming, so instruct TCP to send any remaining
        # data immediately instead of waiting for a full packet or ack.
        self.stream.set_nodelay(True)
        if self._pending_write is None:
            self._finish_request(None)
        else:
            future_add_done_callback(self._pending_write, self._finish_request)

    def _on_write_complete(self, future: "Future[None]") -> None:
        exc = future.exception()
        if exc is not None and not isinstance(exc, iostream.StreamClosedError):
            future.result()
        if self._write_callback is not None:
            callback = self._write_callback
            self._write_callback = None
            self.stream.io_loop.add_callback(callback)
        if self._write_future is not None:
            future = self._write_future
            self._write_future = None
            future_set_result_unless_cancelled(future, None)

    def _can_keep_alive(
        self, start_line: httputil.RequestStartLine, headers: httputil.HTTPHeaders
    ) -> bool:
        if self.params.no_keep_alive:
            return False
        connection_header = headers.get("Connection")
        if connection_header is not None:
            connection_header = connection_header.lower()
        if start_line.version == "HTTP/1.1":
            return connection_header != "close"
        elif (
            "Content-Length" in headers
            or is_transfer_encoding_chunked(headers)
            or getattr(start_line, "method", None) in ("HEAD", "GET")
        ):
            # start_line may be a request or response start line; only
            # the former has a method attribute.
            return connection_header == "keep-alive"
        return False

    def _finish_request(self, future: "Optional[Future[None]]") -> None:
        self._clear_callbacks()
        if not self.is_client and self._disconnect_on_finish:
            self.close()
            return
        # Turn Nagle's algorithm back on, leaving the stream in its
        # default state for the next request.
        self.stream.set_nodelay(False)
        if not self._finish_future.done():
            future_set_result_unless_cancelled(self._finish_future, None)

    def _parse_headers(self, data: bytes) -> Tuple[str, httputil.HTTPHeaders]:
        # The lstrip removes newlines that some implementations sometimes
        # insert between messages of a reused connection.  Per RFC 7230,
        # we SHOULD ignore at least one empty line before the request.
        # http://tools.ietf.org/html/rfc7230#section-3.5
        data_str = native_str(data.decode("latin1")).lstrip("\r\n")
        # RFC 7230 section allows for both CRLF and bare LF.
        eol = data_str.find("\n")
        start_line = data_str[:eol].rstrip("\r")
        headers = httputil.HTTPHeaders.parse(data_str[eol:])
        return start_line, headers

    def _read_body(
        self,
        code: int,
        headers: httputil.HTTPHeaders,
        delegate: httputil.HTTPMessageDelegate,
    ) -> Optional[Awaitable[None]]:
        if "Content-Length" in headers:
            if "," in headers["Content-Length"]:
                # Proxies sometimes cause Content-Length headers to get
                # duplicated.  If all the values are identical then we can
                # use them but if they differ it's an error.
                pieces = re.split(r",\s*", headers["Content-Length"])
                if any(i != pieces[0] for i in pieces):
                    raise httputil.HTTPInputError(
                        "Multiple unequal Content-Lengths: %r"
                        % headers["Content-Length"]
                    )
                headers["Content-Length"] = pieces[0]

            try:
                content_length: Optional[int] = parse_int(headers["Content-Length"])
            except ValueError:
                # Handles non-integer Content-Length value.
                raise httputil.HTTPInputError(
                    "Only integer Content-Length is allowed: %s"
                    % headers["Content-Length"]
                )

            if cast(int, content_length) > self._max_body_size:
                raise httputil.HTTPInputError("Content-Length too long")
        else:
            content_length = None

        is_chunked = is_transfer_encoding_chunked(headers)

        if code == 204:
            # This response code is not allowed to have a non-empty body,
            # and has an implicit length of zero instead of read-until-close.
            # http://www.w3.org/Protocols/rfc2616/rfc2616-sec4.html#sec4.3
            if is_chunked or content_length not in (None, 0):
                raise httputil.HTTPInputError(
                    "Response with code %d should not have body" % code
                )
            content_length = 0

        if is_chunked:
            return self._read_chunked_body(delegate)
        if content_length is not None:
            return self._read_fixed_body(content_length, delegate)
        if self.is_client:
            return self._read_body_until_close(delegate)
        return None

    async def _read_fixed_body(
        self, content_length: int, delegate: httputil.HTTPMessageDelegate
    ) -> None:
        while content_length > 0:
            body = await self.stream.read_bytes(
                min(self.params.chunk_size, content_length), partial=True
            )
            content_length -= len(body)
            if not self._write_finished or self.is_client:
                with _ExceptionLoggingContext(app_log):
                    ret = delegate.data_received(body)
                    if ret is not None:
                        await ret

    async def _read_chunked_body(self, delegate: httputil.HTTPMessageDelegate) -> None:
        # TODO: "chunk extensions" http://tools.ietf.org/html/rfc2616#section-3.6.1
        total_size = 0
        while True:
            chunk_len_str = await self.stream.read_until(b"\r\n", max_bytes=64)
            try:
                chunk_len = parse_hex_int(native_str(chunk_len_str[:-2]))
            except ValueError:
                raise httputil.HTTPInputError("invalid chunk size")
            if chunk_len == 0:
                crlf = await self.stream.read_bytes(2)
                if crlf != b"\r\n":
                    raise httputil.HTTPInputError(
                        "improperly terminated chunked request"
                    )
                return
            total_size += chunk_len
            if total_size > self._max_body_size:
                raise httputil.HTTPInputError("chunked body too large")
            bytes_to_read = chunk_len
            while bytes_to_read:
                chunk = await self.stream.read_bytes(
                    min(bytes_to_read, self.params.chunk_size), partial=True
                )
                bytes_to_read -= len(chunk)
                if not self._write_finished or self.is_client:
                    with _ExceptionLoggingContext(app_log):
                        ret = delegate.data_received(chunk)
                        if ret is not None:
                            await ret
            # chunk ends with \r\n
            crlf = await self.stream.read_bytes(2)
            assert crlf == b"\r\n"

    async def _read_body_until_close(
        self, delegate: httputil.HTTPMessageDelegate
    ) -> None:
        body = await self.stream.read_until_close()
        if not self._write_finished or self.is_client:
            with _ExceptionLoggingContext(app_log):
                ret = delegate.data_received(body)
                if ret is not None:
                    await ret


class _GzipMessageDelegate(httputil.HTTPMessageDelegate):
    """Wraps an `HTTPMessageDelegate` to decode ``Content-Encoding: gzip``."""

    def __init__(self, delegate: httputil.HTTPMessageDelegate, chunk_size: int) -> None:
        self._delegate = delegate
        self._chunk_size = chunk_size
        self._decompressor = None  # type: Optional[GzipDecompressor]

    def headers_received(
        self,
        start_line: Union[httputil.RequestStartLine, httputil.ResponseStartLine],
        headers: httputil.HTTPHeaders,
    ) -> Optional[Awaitable[None]]:
        if headers.get("Content-Encoding", "").lower() == "gzip":
            self._decompressor = GzipDecompressor()
            # Downstream delegates will only see uncompressed data,
            # so rename the content-encoding header.
            # (but note that curl_httpclient doesn't do this).
            headers.add("X-Consumed-Content-Encoding", headers["Content-Encoding"])
            del headers["Content-Encoding"]
        return self._delegate.headers_received(start_line, headers)

    async def data_received(self, chunk: bytes) -> None:
        if self._decompressor:
            compressed_data = chunk
            while compressed_data:
                decompressed = self._decompressor.decompress(
                    compressed_data, self._chunk_size
                )
                if decompressed:
                    ret = self._delegate.data_received(decompressed)
                    if ret is not None:
                        await ret
                compressed_data = self._decompressor.unconsumed_tail
                if compressed_data and not decompressed:
                    raise httputil.HTTPInputError(
                        "encountered unconsumed gzip data without making progress"
                    )
        else:
            ret = self._delegate.data_received(chunk)
            if ret is not None:
                await ret

    def finish(self) -> None:
        if self._decompressor is not None:
            tail = self._decompressor.flush()
            if tail:
                # The tail should always be empty: decompress returned
                # all that it can in data_received and the only
                # purpose of the flush call is to detect errors such
                # as truncated input. If we did legitimately get a new
                # chunk at this point we'd need to change the
                # interface to make finish() a coroutine.
                raise ValueError(
                    "decompressor.flush returned data; possible truncated input"
                )
        return self._delegate.finish()

    def on_connection_close(self) -> None:
        return self._delegate.on_connection_close()


class HTTP1ServerConnection:
    """An HTTP/1.x server."""

    def __init__(
        self,
        stream: iostream.IOStream,
        params: Optional[HTTP1ConnectionParameters] = None,
        context: Optional[object] = None,
    ) -> None:
        """
        :arg stream: an `.IOStream`
        :arg params: a `.HTTP1ConnectionParameters` or None
        :arg context: an opaque application-defined object that is accessible
            as ``connection.context``
        """
        self.stream = stream
        if params is None:
            params = HTTP1ConnectionParameters()
        self.params = params
        self.context = context
        self._serving_future = None  # type: Optional[Future[None]]

    async def close(self) -> None:
        """Closes the connection.

        Returns a `.Future` that resolves after the serving loop has exited.
        """
        self.stream.close()
        # Block until the serving loop is done, but ignore any exceptions
        # (start_serving is already responsible for logging them).
        assert self._serving_future is not None
        try:
            await self._serving_future
        except Exception:
            pass

    def start_serving(self, delegate: httputil.HTTPServerConnectionDelegate) -> None:
        """Starts serving requests on this connection.

        :arg delegate: a `.HTTPServerConnectionDelegate`
        """
        assert isinstance(delegate, httputil.HTTPServerConnectionDelegate)
        fut = gen.convert_yielded(self._server_request_loop(delegate))
        self._serving_future = fut
        # Register the future on the IOLoop so its errors get logged.
        self.stream.io_loop.add_future(fut, lambda f: f.result())

    async def _server_request_loop(
        self, delegate: httputil.HTTPServerConnectionDelegate
    ) -> None:
        try:
            while True:
                conn = HTTP1Connection(self.stream, False, self.params, self.context)
                request_delegate = delegate.start_request(self, conn)
                try:
                    ret = await conn.read_response(request_delegate)
                except (
                    iostream.StreamClosedError,
                    iostream.UnsatisfiableReadError,
                    asyncio.CancelledError,
                ):
                    return
                except _QuietException:
                    # This exception was already logged.
                    conn.close()
                    return
                except Exception:
                    gen_log.error("Uncaught exception", exc_info=True)
                    conn.close()
                    return
                if not ret:
                    return
                await asyncio.sleep(0)
        finally:
            delegate.on_close(self)


DIGITS = re.compile(r"[0-9]+")
HEXDIGITS = re.compile(r"[0-9a-fA-F]+")


def parse_int(s: str) -> int:
    """Parse a non-negative integer from a string."""
    if DIGITS.fullmatch(s) is None:
        raise ValueError("not an integer: %r" % s)
    return int(s)


def parse_hex_int(s: str) -> int:
    """Parse a non-negative hexadecimal integer from a string."""
    if HEXDIGITS.fullmatch(s) is None:
        raise ValueError("not a hexadecimal integer: %r" % s)
    return int(s, 16)


def is_transfer_encoding_chunked(headers: httputil.HTTPHeaders) -> bool:
    """Returns true if the headers specify Transfer-Encoding: chunked.

    Raise httputil.HTTPInputError if any other transfer encoding is used.
    """
    # Note that transfer-encoding is an area in which postel's law can lead
    # us astray. If a proxy and a backend server are liberal in what they accept,
    # but accept slightly different things, this can lead to mismatched framing
    # and request smuggling issues. Therefore we are as strict as possible here
    # (even technically going beyond the requirements of the RFCs: a value of
    # ",chunked" is legal but doesn't appear in practice for legitimate traffic)
    if "Transfer-Encoding" not in headers:
        return False
    if "Content-Length" in headers:
        # Message cannot contain both Content-Length and
        # Transfer-Encoding headers.
        # http://tools.ietf.org/html/rfc7230#section-3.3.3
        raise httputil.HTTPInputError(
            "Message with both Transfer-Encoding and Content-Length"
        )
    if headers["Transfer-Encoding"].lower() == "chunked":
        return True
    # We do not support any transfer-encodings other than chunked, and we do not
    # expect to add any support because the concept of transfer-encoding has
    # been removed in HTTP/2.
    raise httputil.HTTPInputError(
        "Unsupported Transfer-Encoding %s" % headers["Transfer-Encoding"]
    )

# === NexusCore/openenv\Lib\site-packages\parso\python\diff.py ===
"""
The diff parser is trying to be a faster version of the normal parser by trying
to reuse the nodes of a previous pass over the same file. This is also called
incremental parsing in parser literature. The difference is mostly that with
incremental parsing you get a range that needs to be reparsed. Here we
calculate that range ourselves by using difflib. After that it's essentially
incremental parsing.

The biggest issue of this approach is that we reuse nodes in a mutable way. The
intial design and idea is quite problematic for this parser, but it is also
pretty fast. Measurements showed that just copying nodes in Python is simply
quite a bit slower (especially for big files >3 kLOC). Therefore we did not
want to get rid of the mutable nodes, since this is usually not an issue.

This is by far the hardest software I ever wrote, exactly because the initial
design is crappy. When you have to account for a lot of mutable state, it
creates a ton of issues that you would otherwise not have. This file took
probably 3-6 months to write, which is insane for a parser.

There is a fuzzer in that helps test this whole thing. Please use it if you
make changes here. If you run the fuzzer like::

    test/fuzz_diff_parser.py random -n 100000

you can be pretty sure that everything is still fine. I sometimes run the
fuzzer up to 24h to make sure everything is still ok.
"""
import re
import difflib
from collections import namedtuple
import logging

from parso.utils import split_lines
from parso.python.parser import Parser
from parso.python.tree import EndMarker
from parso.python.tokenize import PythonToken, BOM_UTF8_STRING
from parso.python.token import PythonTokenTypes

LOG = logging.getLogger(__name__)
DEBUG_DIFF_PARSER = False

_INDENTATION_TOKENS = 'INDENT', 'ERROR_DEDENT', 'DEDENT'

NEWLINE = PythonTokenTypes.NEWLINE
DEDENT = PythonTokenTypes.DEDENT
NAME = PythonTokenTypes.NAME
ERROR_DEDENT = PythonTokenTypes.ERROR_DEDENT
ENDMARKER = PythonTokenTypes.ENDMARKER


def _is_indentation_error_leaf(node):
    return node.type == 'error_leaf' and node.token_type in _INDENTATION_TOKENS


def _get_previous_leaf_if_indentation(leaf):
    while leaf and _is_indentation_error_leaf(leaf):
        leaf = leaf.get_previous_leaf()
    return leaf


def _get_next_leaf_if_indentation(leaf):
    while leaf and _is_indentation_error_leaf(leaf):
        leaf = leaf.get_next_leaf()
    return leaf


def _get_suite_indentation(tree_node):
    return _get_indentation(tree_node.children[1])


def _get_indentation(tree_node):
    return tree_node.start_pos[1]


def _assert_valid_graph(node):
    """
    Checks if the parent/children relationship is correct.

    This is a check that only runs during debugging/testing.
    """
    try:
        children = node.children
    except AttributeError:
        # Ignore INDENT is necessary, because indent/dedent tokens don't
        # contain value/prefix and are just around, because of the tokenizer.
        if node.type == 'error_leaf' and node.token_type in _INDENTATION_TOKENS:
            assert not node.value
            assert not node.prefix
            return

        # Calculate the content between two start positions.
        previous_leaf = _get_previous_leaf_if_indentation(node.get_previous_leaf())
        if previous_leaf is None:
            content = node.prefix
            previous_start_pos = 1, 0
        else:
            assert previous_leaf.end_pos <= node.start_pos, \
                (previous_leaf, node)

            content = previous_leaf.value + node.prefix
            previous_start_pos = previous_leaf.start_pos

        if '\n' in content or '\r' in content:
            splitted = split_lines(content)
            line = previous_start_pos[0] + len(splitted) - 1
            actual = line, len(splitted[-1])
        else:
            actual = previous_start_pos[0], previous_start_pos[1] + len(content)
            if content.startswith(BOM_UTF8_STRING) \
                    and node.get_start_pos_of_prefix() == (1, 0):
                # Remove the byte order mark
                actual = actual[0], actual[1] - 1

        assert node.start_pos == actual, (node.start_pos, actual)
    else:
        for child in children:
            assert child.parent == node, (node, child)
            _assert_valid_graph(child)


def _assert_nodes_are_equal(node1, node2):
    try:
        children1 = node1.children
    except AttributeError:
        assert not hasattr(node2, 'children'), (node1, node2)
        assert node1.value == node2.value, (node1, node2)
        assert node1.type == node2.type, (node1, node2)
        assert node1.prefix == node2.prefix, (node1, node2)
        assert node1.start_pos == node2.start_pos, (node1, node2)
        return
    else:
        try:
            children2 = node2.children
        except AttributeError:
            assert False, (node1, node2)
    for n1, n2 in zip(children1, children2):
        _assert_nodes_are_equal(n1, n2)
    assert len(children1) == len(children2), '\n' + repr(children1) + '\n' + repr(children2)


def _get_debug_error_message(module, old_lines, new_lines):
    current_lines = split_lines(module.get_code(), keepends=True)
    current_diff = difflib.unified_diff(new_lines, current_lines)
    old_new_diff = difflib.unified_diff(old_lines, new_lines)
    import parso
    return (
        "There's an issue with the diff parser. Please "
        "report (parso v%s) - Old/New:\n%s\nActual Diff (May be empty):\n%s"
        % (parso.__version__, ''.join(old_new_diff), ''.join(current_diff))
    )


def _get_last_line(node_or_leaf):
    last_leaf = node_or_leaf.get_last_leaf()
    if _ends_with_newline(last_leaf):
        return last_leaf.start_pos[0]
    else:
        n = last_leaf.get_next_leaf()
        if n.type == 'endmarker' and '\n' in n.prefix:
            # This is a very special case and has to do with error recovery in
            # Parso. The problem is basically that there's no newline leaf at
            # the end sometimes (it's required in the grammar, but not needed
            # actually before endmarker, CPython just adds a newline to make
            # source code pass the parser, to account for that Parso error
            # recovery allows small_stmt instead of simple_stmt).
            return last_leaf.end_pos[0] + 1
        return last_leaf.end_pos[0]


def _skip_dedent_error_leaves(leaf):
    while leaf is not None and leaf.type == 'error_leaf' and leaf.token_type == 'DEDENT':
        leaf = leaf.get_previous_leaf()
    return leaf


def _ends_with_newline(leaf, suffix=''):
    leaf = _skip_dedent_error_leaves(leaf)

    if leaf.type == 'error_leaf':
        typ = leaf.token_type.lower()
    else:
        typ = leaf.type

    return typ == 'newline' or suffix.endswith('\n') or suffix.endswith('\r')


def _flows_finished(pgen_grammar, stack):
    """
    if, while, for and try might not be finished, because another part might
    still be parsed.
    """
    for stack_node in stack:
        if stack_node.nonterminal in ('if_stmt', 'while_stmt', 'for_stmt', 'try_stmt'):
            return False
    return True


def _func_or_class_has_suite(node):
    if node.type == 'decorated':
        node = node.children[-1]
    if node.type in ('async_funcdef', 'async_stmt'):
        node = node.children[-1]
    return node.type in ('classdef', 'funcdef') and node.children[-1].type == 'suite'


def _suite_or_file_input_is_valid(pgen_grammar, stack):
    if not _flows_finished(pgen_grammar, stack):
        return False

    for stack_node in reversed(stack):
        if stack_node.nonterminal == 'decorator':
            # A decorator is only valid with the upcoming function.
            return False

        if stack_node.nonterminal == 'suite':
            # If only newline is in the suite, the suite is not valid, yet.
            return len(stack_node.nodes) > 1
    # Not reaching a suite means that we're dealing with file_input levels
    # where there's no need for a valid statement in it. It can also be empty.
    return True


def _is_flow_node(node):
    if node.type == 'async_stmt':
        node = node.children[1]
    try:
        value = node.children[0].value
    except AttributeError:
        return False
    return value in ('if', 'for', 'while', 'try', 'with')


class _PositionUpdatingFinished(Exception):
    pass


def _update_positions(nodes, line_offset, last_leaf):
    for node in nodes:
        try:
            children = node.children
        except AttributeError:
            # Is a leaf
            node.line += line_offset
            if node is last_leaf:
                raise _PositionUpdatingFinished
        else:
            _update_positions(children, line_offset, last_leaf)


class DiffParser:
    """
    An advanced form of parsing a file faster. Unfortunately comes with huge
    side effects. It changes the given module.
    """
    def __init__(self, pgen_grammar, tokenizer, module):
        self._pgen_grammar = pgen_grammar
        self._tokenizer = tokenizer
        self._module = module

    def _reset(self):
        self._copy_count = 0
        self._parser_count = 0

        self._nodes_tree = _NodesTree(self._module)

    def update(self, old_lines, new_lines):
        '''
        The algorithm works as follows:

        Equal:
            - Assure that the start is a newline, otherwise parse until we get
              one.
            - Copy from parsed_until_line + 1 to max(i2 + 1)
            - Make sure that the indentation is correct (e.g. add DEDENT)
            - Add old and change positions
        Insert:
            - Parse from parsed_until_line + 1 to min(j2 + 1), hopefully not
              much more.

        Returns the new module node.
        '''
        LOG.debug('diff parser start')
        # Reset the used names cache so they get regenerated.
        self._module._used_names = None

        self._parser_lines_new = new_lines

        self._reset()

        line_length = len(new_lines)
        sm = difflib.SequenceMatcher(None, old_lines, self._parser_lines_new)
        opcodes = sm.get_opcodes()
        LOG.debug('line_lengths old: %s; new: %s' % (len(old_lines), line_length))

        for operation, i1, i2, j1, j2 in opcodes:
            LOG.debug('-> code[%s] old[%s:%s] new[%s:%s]',
                      operation, i1 + 1, i2, j1 + 1, j2)

            if j2 == line_length and new_lines[-1] == '':
                # The empty part after the last newline is not relevant.
                j2 -= 1

            if operation == 'equal':
                line_offset = j1 - i1
                self._copy_from_old_parser(line_offset, i1 + 1, i2, j2)
            elif operation == 'replace':
                self._parse(until_line=j2)
            elif operation == 'insert':
                self._parse(until_line=j2)
            else:
                assert operation == 'delete'

        # With this action all change will finally be applied and we have a
        # changed module.
        self._nodes_tree.close()

        if DEBUG_DIFF_PARSER:
            # If there is reasonable suspicion that the diff parser is not
            # behaving well, this should be enabled.
            try:
                code = ''.join(new_lines)
                assert self._module.get_code() == code
                _assert_valid_graph(self._module)
                without_diff_parser_module = Parser(
                    self._pgen_grammar,
                    error_recovery=True
                ).parse(self._tokenizer(new_lines))
                _assert_nodes_are_equal(self._module, without_diff_parser_module)
            except AssertionError:
                print(_get_debug_error_message(self._module, old_lines, new_lines))
                raise

        last_pos = self._module.end_pos[0]
        if last_pos != line_length:
            raise Exception(
                ('(%s != %s) ' % (last_pos, line_length))
                + _get_debug_error_message(self._module, old_lines, new_lines)
            )
        LOG.debug('diff parser end')
        return self._module

    def _enabled_debugging(self, old_lines, lines_new):
        if self._module.get_code() != ''.join(lines_new):
            LOG.warning('parser issue:\n%s\n%s', ''.join(old_lines), ''.join(lines_new))

    def _copy_from_old_parser(self, line_offset, start_line_old, until_line_old, until_line_new):
        last_until_line = -1
        while until_line_new > self._nodes_tree.parsed_until_line:
            parsed_until_line_old = self._nodes_tree.parsed_until_line - line_offset
            line_stmt = self._get_old_line_stmt(parsed_until_line_old + 1)
            if line_stmt is None:
                # Parse 1 line at least. We don't need more, because we just
                # want to get into a state where the old parser has statements
                # again that can be copied (e.g. not lines within parentheses).
                self._parse(self._nodes_tree.parsed_until_line + 1)
            else:
                p_children = line_stmt.parent.children
                index = p_children.index(line_stmt)

                if start_line_old == 1 \
                        and p_children[0].get_first_leaf().prefix.startswith(BOM_UTF8_STRING):
                    # If there's a BOM in the beginning, just reparse. It's too
                    # complicated to account for it otherwise.
                    copied_nodes = []
                else:
                    from_ = self._nodes_tree.parsed_until_line + 1
                    copied_nodes = self._nodes_tree.copy_nodes(
                        p_children[index:],
                        until_line_old,
                        line_offset
                    )
                # Match all the nodes that are in the wanted range.
                if copied_nodes:
                    self._copy_count += 1

                    to = self._nodes_tree.parsed_until_line

                    LOG.debug('copy old[%s:%s] new[%s:%s]',
                              copied_nodes[0].start_pos[0],
                              copied_nodes[-1].end_pos[0] - 1, from_, to)
                else:
                    # We have copied as much as possible (but definitely not too
                    # much). Therefore we just parse a bit more.
                    self._parse(self._nodes_tree.parsed_until_line + 1)
            # Since there are potential bugs that might loop here endlessly, we
            # just stop here.
            assert last_until_line != self._nodes_tree.parsed_until_line, last_until_line
            last_until_line = self._nodes_tree.parsed_until_line

    def _get_old_line_stmt(self, old_line):
        leaf = self._module.get_leaf_for_position((old_line, 0), include_prefixes=True)

        if _ends_with_newline(leaf):
            leaf = leaf.get_next_leaf()
        if leaf.get_start_pos_of_prefix()[0] == old_line:
            node = leaf
            while node.parent.type not in ('file_input', 'suite'):
                node = node.parent

            # Make sure that if only the `else:` line of an if statement is
            # copied that not the whole thing is going to be copied.
            if node.start_pos[0] >= old_line:
                return node
        # Must be on the same line. Otherwise we need to parse that bit.
        return None

    def _parse(self, until_line):
        """
        Parses at least until the given line, but might just parse more until a
        valid state is reached.
        """
        last_until_line = 0
        while until_line > self._nodes_tree.parsed_until_line:
            node = self._try_parse_part(until_line)
            nodes = node.children

            self._nodes_tree.add_parsed_nodes(nodes, self._keyword_token_indents)
            if self._replace_tos_indent is not None:
                self._nodes_tree.indents[-1] = self._replace_tos_indent

            LOG.debug(
                'parse_part from %s to %s (to %s in part parser)',
                nodes[0].get_start_pos_of_prefix()[0],
                self._nodes_tree.parsed_until_line,
                node.end_pos[0] - 1
            )
            # Since the tokenizer sometimes has bugs, we cannot be sure that
            # this loop terminates. Therefore assert that there's always a
            # change.
            assert last_until_line != self._nodes_tree.parsed_until_line, last_until_line
            last_until_line = self._nodes_tree.parsed_until_line

    def _try_parse_part(self, until_line):
        """
        Sets up a normal parser that uses a spezialized tokenizer to only parse
        until a certain position (or a bit longer if the statement hasn't
        ended.
        """
        self._parser_count += 1
        # TODO speed up, shouldn't copy the whole list all the time.
        # memoryview?
        parsed_until_line = self._nodes_tree.parsed_until_line
        lines_after = self._parser_lines_new[parsed_until_line:]
        tokens = self._diff_tokenize(
            lines_after,
            until_line,
            line_offset=parsed_until_line
        )
        self._active_parser = Parser(
            self._pgen_grammar,
            error_recovery=True
        )
        return self._active_parser.parse(tokens=tokens)

    def _diff_tokenize(self, lines, until_line, line_offset=0):
        was_newline = False
        indents = self._nodes_tree.indents
        initial_indentation_count = len(indents)

        tokens = self._tokenizer(
            lines,
            start_pos=(line_offset + 1, 0),
            indents=indents,
            is_first_token=line_offset == 0,
        )
        stack = self._active_parser.stack
        self._replace_tos_indent = None
        self._keyword_token_indents = {}
        # print('start', line_offset + 1, indents)
        for token in tokens:
            # print(token, indents)
            typ = token.type
            if typ == DEDENT:
                if len(indents) < initial_indentation_count:
                    # We are done here, only thing that can come now is an
                    # endmarker or another dedented code block.
                    while True:
                        typ, string, start_pos, prefix = token = next(tokens)
                        if typ in (DEDENT, ERROR_DEDENT):
                            if typ == ERROR_DEDENT:
                                # We want to force an error dedent in the next
                                # parser/pass. To make this possible we just
                                # increase the location by one.
                                self._replace_tos_indent = start_pos[1] + 1
                                pass
                        else:
                            break

                    if '\n' in prefix or '\r' in prefix:
                        prefix = re.sub(r'[^\n\r]+\Z', '', prefix)
                    else:
                        assert start_pos[1] >= len(prefix), repr(prefix)
                        if start_pos[1] - len(prefix) == 0:
                            prefix = ''
                    yield PythonToken(
                        ENDMARKER, '',
                        start_pos,
                        prefix
                    )
                    break
            elif typ == NEWLINE and token.start_pos[0] >= until_line:
                was_newline = True
            elif was_newline:
                was_newline = False
                if len(indents) == initial_indentation_count:
                    # Check if the parser is actually in a valid suite state.
                    if _suite_or_file_input_is_valid(self._pgen_grammar, stack):
                        yield PythonToken(ENDMARKER, '', token.start_pos, '')
                        break

            if typ == NAME and token.string in ('class', 'def'):
                self._keyword_token_indents[token.start_pos] = list(indents)

            yield token


class _NodesTreeNode:
    _ChildrenGroup = namedtuple(
        '_ChildrenGroup',
        'prefix children line_offset last_line_offset_leaf')

    def __init__(self, tree_node, parent=None, indentation=0):
        self.tree_node = tree_node
        self._children_groups = []
        self.parent = parent
        self._node_children = []
        self.indentation = indentation

    def finish(self):
        children = []
        for prefix, children_part, line_offset, last_line_offset_leaf in self._children_groups:
            first_leaf = _get_next_leaf_if_indentation(
                children_part[0].get_first_leaf()
            )

            first_leaf.prefix = prefix + first_leaf.prefix
            if line_offset != 0:
                try:
                    _update_positions(
                        children_part, line_offset, last_line_offset_leaf)
                except _PositionUpdatingFinished:
                    pass
            children += children_part
        self.tree_node.children = children
        # Reset the parents
        for node in children:
            node.parent = self.tree_node

        for node_child in self._node_children:
            node_child.finish()

    def add_child_node(self, child_node):
        self._node_children.append(child_node)

    def add_tree_nodes(self, prefix, children, line_offset=0,
                       last_line_offset_leaf=None):
        if last_line_offset_leaf is None:
            last_line_offset_leaf = children[-1].get_last_leaf()
        group = self._ChildrenGroup(
            prefix, children, line_offset, last_line_offset_leaf
        )
        self._children_groups.append(group)

    def get_last_line(self, suffix):
        line = 0
        if self._children_groups:
            children_group = self._children_groups[-1]
            last_leaf = _get_previous_leaf_if_indentation(
                children_group.last_line_offset_leaf
            )

            line = last_leaf.end_pos[0] + children_group.line_offset

            # Newlines end on the next line, which means that they would cover
            # the next line. That line is not fully parsed at this point.
            if _ends_with_newline(last_leaf, suffix):
                line -= 1
        line += len(split_lines(suffix)) - 1

        if suffix and not suffix.endswith('\n') and not suffix.endswith('\r'):
            # This is the end of a file (that doesn't end with a newline).
            line += 1

        if self._node_children:
            return max(line, self._node_children[-1].get_last_line(suffix))
        return line

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.tree_node)


class _NodesTree:
    def __init__(self, module):
        self._base_node = _NodesTreeNode(module)
        self._working_stack = [self._base_node]
        self._module = module
        self._prefix_remainder = ''
        self.prefix = ''
        self.indents = [0]

    @property
    def parsed_until_line(self):
        return self._working_stack[-1].get_last_line(self.prefix)

    def _update_insertion_node(self, indentation):
        for node in reversed(list(self._working_stack)):
            if node.indentation < indentation or node is self._working_stack[0]:
                return node
            self._working_stack.pop()

    def add_parsed_nodes(self, tree_nodes, keyword_token_indents):
        old_prefix = self.prefix
        tree_nodes = self._remove_endmarker(tree_nodes)
        if not tree_nodes:
            self.prefix = old_prefix + self.prefix
            return

        assert tree_nodes[0].type != 'newline'

        node = self._update_insertion_node(tree_nodes[0].start_pos[1])
        assert node.tree_node.type in ('suite', 'file_input')
        node.add_tree_nodes(old_prefix, tree_nodes)
        # tos = Top of stack
        self._update_parsed_node_tos(tree_nodes[-1], keyword_token_indents)

    def _update_parsed_node_tos(self, tree_node, keyword_token_indents):
        if tree_node.type == 'suite':
            def_leaf = tree_node.parent.children[0]
            new_tos = _NodesTreeNode(
                tree_node,
                indentation=keyword_token_indents[def_leaf.start_pos][-1],
            )
            new_tos.add_tree_nodes('', list(tree_node.children))

            self._working_stack[-1].add_child_node(new_tos)
            self._working_stack.append(new_tos)

            self._update_parsed_node_tos(tree_node.children[-1], keyword_token_indents)
        elif _func_or_class_has_suite(tree_node):
            self._update_parsed_node_tos(tree_node.children[-1], keyword_token_indents)

    def _remove_endmarker(self, tree_nodes):
        """
        Helps cleaning up the tree nodes that get inserted.
        """
        last_leaf = tree_nodes[-1].get_last_leaf()
        is_endmarker = last_leaf.type == 'endmarker'
        self._prefix_remainder = ''
        if is_endmarker:
            prefix = last_leaf.prefix
            separation = max(prefix.rfind('\n'), prefix.rfind('\r'))
            if separation > -1:
                # Remove the whitespace part of the prefix after a newline.
                # That is not relevant if parentheses were opened. Always parse
                # until the end of a line.
                last_leaf.prefix, self._prefix_remainder = \
                    last_leaf.prefix[:separation + 1], last_leaf.prefix[separation + 1:]

        self.prefix = ''

        if is_endmarker:
            self.prefix = last_leaf.prefix

            tree_nodes = tree_nodes[:-1]
        return tree_nodes

    def _get_matching_indent_nodes(self, tree_nodes, is_new_suite):
        # There might be a random dedent where we have to stop copying.
        # Invalid indents are ok, because the parser handled that
        # properly before. An invalid dedent can happen, because a few
        # lines above there was an invalid indent.
        node_iterator = iter(tree_nodes)
        if is_new_suite:
            yield next(node_iterator)

        first_node = next(node_iterator)
        indent = _get_indentation(first_node)
        if not is_new_suite and indent not in self.indents:
            return
        yield first_node

        for n in node_iterator:
            if _get_indentation(n) != indent:
                return
            yield n

    def copy_nodes(self, tree_nodes, until_line, line_offset):
        """
        Copies tree nodes from the old parser tree.

        Returns the number of tree nodes that were copied.
        """
        if tree_nodes[0].type in ('error_leaf', 'error_node'):
            # Avoid copying errors in the beginning. Can lead to a lot of
            # issues.
            return []

        indentation = _get_indentation(tree_nodes[0])
        old_working_stack = list(self._working_stack)
        old_prefix = self.prefix
        old_indents = self.indents
        self.indents = [i for i in self.indents if i <= indentation]

        self._update_insertion_node(indentation)

        new_nodes, self._working_stack, self.prefix, added_indents = self._copy_nodes(
            list(self._working_stack),
            tree_nodes,
            until_line,
            line_offset,
            self.prefix,
        )
        if new_nodes:
            self.indents += added_indents
        else:
            self._working_stack = old_working_stack
            self.prefix = old_prefix
            self.indents = old_indents
        return new_nodes

    def _copy_nodes(self, working_stack, nodes, until_line, line_offset,
                    prefix='', is_nested=False):
        new_nodes = []
        added_indents = []

        nodes = list(self._get_matching_indent_nodes(
            nodes,
            is_new_suite=is_nested,
        ))

        new_prefix = ''
        for node in nodes:
            if node.start_pos[0] > until_line:
                break

            if node.type == 'endmarker':
                break

            if node.type == 'error_leaf' and node.token_type in ('DEDENT', 'ERROR_DEDENT'):
                break
            # TODO this check might take a bit of time for large files. We
            # might want to change this to do more intelligent guessing or
            # binary search.
            if _get_last_line(node) > until_line:
                # We can split up functions and classes later.
                if _func_or_class_has_suite(node):
                    new_nodes.append(node)
                break
            try:
                c = node.children
            except AttributeError:
                pass
            else:
                # This case basically appears with error recovery of one line
                # suites like `def foo(): bar.-`. In this case we might not
                # include a newline in the statement and we need to take care
                # of that.
                n = node
                if n.type == 'decorated':
                    n = n.children[-1]
                if n.type in ('async_funcdef', 'async_stmt'):
                    n = n.children[-1]
                if n.type in ('classdef', 'funcdef'):
                    suite_node = n.children[-1]
                else:
                    suite_node = c[-1]

                if suite_node.type in ('error_leaf', 'error_node'):
                    break

            new_nodes.append(node)

        # Pop error nodes at the end from the list
        if new_nodes:
            while new_nodes:
                last_node = new_nodes[-1]
                if (last_node.type in ('error_leaf', 'error_node')
                        or _is_flow_node(new_nodes[-1])):
                    # Error leafs/nodes don't have a defined start/end. Error
                    # nodes might not end with a newline (e.g. if there's an
                    # open `(`). Therefore ignore all of them unless they are
                    # succeeded with valid parser state.
                    # If we copy flows at the end, they might be continued
                    # after the copy limit (in the new parser).
                    # In this while loop we try to remove until we find a newline.
                    new_prefix = ''
                    new_nodes.pop()
                    while new_nodes:
                        last_node = new_nodes[-1]
                        if last_node.get_last_leaf().type == 'newline':
                            break
                        new_nodes.pop()
                    continue
                if len(new_nodes) > 1 and new_nodes[-2].type == 'error_node':
                    # The problem here is that Parso error recovery sometimes
                    # influences nodes before this node.
                    # Since the new last node is an error node this will get
                    # cleaned up in the next while iteration.
                    new_nodes.pop()
                    continue
                break

        if not new_nodes:
            return [], working_stack, prefix, added_indents

        tos = working_stack[-1]
        last_node = new_nodes[-1]
        had_valid_suite_last = False
        # Pop incomplete suites from the list
        if _func_or_class_has_suite(last_node):
            suite = last_node
            while suite.type != 'suite':
                suite = suite.children[-1]

            indent = _get_suite_indentation(suite)
            added_indents.append(indent)

            suite_tos = _NodesTreeNode(suite, indentation=_get_indentation(last_node))
            # Don't need to pass line_offset here, it's already done by the
            # parent.
            suite_nodes, new_working_stack, new_prefix, ai = self._copy_nodes(
                working_stack + [suite_tos], suite.children, until_line, line_offset,
                is_nested=True,
            )
            added_indents += ai
            if len(suite_nodes) < 2:
                # A suite only with newline is not valid.
                new_nodes.pop()
                new_prefix = ''
            else:
                assert new_nodes
                tos.add_child_node(suite_tos)
                working_stack = new_working_stack
                had_valid_suite_last = True

        if new_nodes:
            if not _ends_with_newline(new_nodes[-1].get_last_leaf()) and not had_valid_suite_last:
                p = new_nodes[-1].get_next_leaf().prefix
                # We are not allowed to remove the newline at the end of the
                # line, otherwise it's going to be missing. This happens e.g.
                # if a bracket is around before that moves newlines to
                # prefixes.
                new_prefix = split_lines(p, keepends=True)[0]

            if had_valid_suite_last:
                last = new_nodes[-1]
                if last.type == 'decorated':
                    last = last.children[-1]
                if last.type in ('async_funcdef', 'async_stmt'):
                    last = last.children[-1]
                last_line_offset_leaf = last.children[-2].get_last_leaf()
                assert last_line_offset_leaf == ':'
            else:
                last_line_offset_leaf = new_nodes[-1].get_last_leaf()
            tos.add_tree_nodes(
                prefix, new_nodes, line_offset, last_line_offset_leaf,
            )
            prefix = new_prefix
            self._prefix_remainder = ''

        return new_nodes, working_stack, prefix, added_indents

    def close(self):
        self._base_node.finish()

        # Add an endmarker.
        try:
            last_leaf = self._module.get_last_leaf()
        except IndexError:
            end_pos = [1, 0]
        else:
            last_leaf = _skip_dedent_error_leaves(last_leaf)
            end_pos = list(last_leaf.end_pos)
        lines = split_lines(self.prefix)
        assert len(lines) > 0
        if len(lines) == 1:
            if lines[0].startswith(BOM_UTF8_STRING) and end_pos == [1, 0]:
                end_pos[1] -= 1
            end_pos[1] += len(lines[0])
        else:
            end_pos[0] += len(lines) - 1
            end_pos[1] = len(lines[-1])

        endmarker = EndMarker('', tuple(end_pos), self.prefix + self._prefix_remainder)
        endmarker.parent = self._module
        self._module.children.append(endmarker)

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\input\win32.py ===
from __future__ import annotations

import os
import sys
from abc import abstractmethod
from asyncio import get_running_loop
from contextlib import contextmanager

from ..utils import SPHINX_AUTODOC_RUNNING

assert sys.platform == "win32"

# Do not import win32-specific stuff when generating documentation.
# Otherwise RTD would be unable to generate docs for this module.
if not SPHINX_AUTODOC_RUNNING:
    import msvcrt
    from ctypes import windll

from ctypes import Array, byref, pointer
from ctypes.wintypes import DWORD, HANDLE
from typing import Callable, ContextManager, Iterable, Iterator, TextIO

from prompt_toolkit.eventloop import run_in_executor_with_context
from prompt_toolkit.eventloop.win32 import create_win32_event, wait_for_handles
from prompt_toolkit.key_binding.key_processor import KeyPress
from prompt_toolkit.keys import Keys
from prompt_toolkit.mouse_events import MouseButton, MouseEventType
from prompt_toolkit.win32_types import (
    INPUT_RECORD,
    KEY_EVENT_RECORD,
    MOUSE_EVENT_RECORD,
    STD_INPUT_HANDLE,
    EventTypes,
)

from .ansi_escape_sequences import REVERSE_ANSI_SEQUENCES
from .base import Input
from .vt100_parser import Vt100Parser

__all__ = [
    "Win32Input",
    "ConsoleInputReader",
    "raw_mode",
    "cooked_mode",
    "attach_win32_input",
    "detach_win32_input",
]

# Win32 Constants for MOUSE_EVENT_RECORD.
# See: https://docs.microsoft.com/en-us/windows/console/mouse-event-record-str
FROM_LEFT_1ST_BUTTON_PRESSED = 0x1
RIGHTMOST_BUTTON_PRESSED = 0x2
MOUSE_MOVED = 0x0001
MOUSE_WHEELED = 0x0004

# See: https://msdn.microsoft.com/pl-pl/library/windows/desktop/ms686033(v=vs.85).aspx
ENABLE_VIRTUAL_TERMINAL_INPUT = 0x0200


class _Win32InputBase(Input):
    """
    Base class for `Win32Input` and `Win32PipeInput`.
    """

    def __init__(self) -> None:
        self.win32_handles = _Win32Handles()

    @property
    @abstractmethod
    def handle(self) -> HANDLE:
        pass


class Win32Input(_Win32InputBase):
    """
    `Input` class that reads from the Windows console.
    """

    def __init__(self, stdin: TextIO | None = None) -> None:
        super().__init__()
        self._use_virtual_terminal_input = _is_win_vt100_input_enabled()

        self.console_input_reader: Vt100ConsoleInputReader | ConsoleInputReader

        if self._use_virtual_terminal_input:
            self.console_input_reader = Vt100ConsoleInputReader()
        else:
            self.console_input_reader = ConsoleInputReader()

    def attach(self, input_ready_callback: Callable[[], None]) -> ContextManager[None]:
        """
        Return a context manager that makes this input active in the current
        event loop.
        """
        return attach_win32_input(self, input_ready_callback)

    def detach(self) -> ContextManager[None]:
        """
        Return a context manager that makes sure that this input is not active
        in the current event loop.
        """
        return detach_win32_input(self)

    def read_keys(self) -> list[KeyPress]:
        return list(self.console_input_reader.read())

    def flush(self) -> None:
        pass

    @property
    def closed(self) -> bool:
        return False

    def raw_mode(self) -> ContextManager[None]:
        return raw_mode(
            use_win10_virtual_terminal_input=self._use_virtual_terminal_input
        )

    def cooked_mode(self) -> ContextManager[None]:
        return cooked_mode()

    def fileno(self) -> int:
        # The windows console doesn't depend on the file handle, so
        # this is not used for the event loop (which uses the
        # handle instead). But it's used in `Application.run_system_command`
        # which opens a subprocess with a given stdin/stdout.
        return sys.stdin.fileno()

    def typeahead_hash(self) -> str:
        return "win32-input"

    def close(self) -> None:
        self.console_input_reader.close()

    @property
    def handle(self) -> HANDLE:
        return self.console_input_reader.handle


class ConsoleInputReader:
    """
    :param recognize_paste: When True, try to discover paste actions and turn
        the event into a BracketedPaste.
    """

    # Keys with character data.
    mappings = {
        b"\x1b": Keys.Escape,
        b"\x00": Keys.ControlSpace,  # Control-Space (Also for Ctrl-@)
        b"\x01": Keys.ControlA,  # Control-A (home)
        b"\x02": Keys.ControlB,  # Control-B (emacs cursor left)
        b"\x03": Keys.ControlC,  # Control-C (interrupt)
        b"\x04": Keys.ControlD,  # Control-D (exit)
        b"\x05": Keys.ControlE,  # Control-E (end)
        b"\x06": Keys.ControlF,  # Control-F (cursor forward)
        b"\x07": Keys.ControlG,  # Control-G
        b"\x08": Keys.ControlH,  # Control-H (8) (Identical to '\b')
        b"\x09": Keys.ControlI,  # Control-I (9) (Identical to '\t')
        b"\x0a": Keys.ControlJ,  # Control-J (10) (Identical to '\n')
        b"\x0b": Keys.ControlK,  # Control-K (delete until end of line; vertical tab)
        b"\x0c": Keys.ControlL,  # Control-L (clear; form feed)
        b"\x0d": Keys.ControlM,  # Control-M (enter)
        b"\x0e": Keys.ControlN,  # Control-N (14) (history forward)
        b"\x0f": Keys.ControlO,  # Control-O (15)
        b"\x10": Keys.ControlP,  # Control-P (16) (history back)
        b"\x11": Keys.ControlQ,  # Control-Q
        b"\x12": Keys.ControlR,  # Control-R (18) (reverse search)
        b"\x13": Keys.ControlS,  # Control-S (19) (forward search)
        b"\x14": Keys.ControlT,  # Control-T
        b"\x15": Keys.ControlU,  # Control-U
        b"\x16": Keys.ControlV,  # Control-V
        b"\x17": Keys.ControlW,  # Control-W
        b"\x18": Keys.ControlX,  # Control-X
        b"\x19": Keys.ControlY,  # Control-Y (25)
        b"\x1a": Keys.ControlZ,  # Control-Z
        b"\x1c": Keys.ControlBackslash,  # Both Control-\ and Ctrl-|
        b"\x1d": Keys.ControlSquareClose,  # Control-]
        b"\x1e": Keys.ControlCircumflex,  # Control-^
        b"\x1f": Keys.ControlUnderscore,  # Control-underscore (Also for Ctrl-hyphen.)
        b"\x7f": Keys.Backspace,  # (127) Backspace   (ASCII Delete.)
    }

    # Keys that don't carry character data.
    keycodes = {
        # Home/End
        33: Keys.PageUp,
        34: Keys.PageDown,
        35: Keys.End,
        36: Keys.Home,
        # Arrows
        37: Keys.Left,
        38: Keys.Up,
        39: Keys.Right,
        40: Keys.Down,
        45: Keys.Insert,
        46: Keys.Delete,
        # F-keys.
        112: Keys.F1,
        113: Keys.F2,
        114: Keys.F3,
        115: Keys.F4,
        116: Keys.F5,
        117: Keys.F6,
        118: Keys.F7,
        119: Keys.F8,
        120: Keys.F9,
        121: Keys.F10,
        122: Keys.F11,
        123: Keys.F12,
    }

    LEFT_ALT_PRESSED = 0x0002
    RIGHT_ALT_PRESSED = 0x0001
    SHIFT_PRESSED = 0x0010
    LEFT_CTRL_PRESSED = 0x0008
    RIGHT_CTRL_PRESSED = 0x0004

    def __init__(self, recognize_paste: bool = True) -> None:
        self._fdcon = None
        self.recognize_paste = recognize_paste

        # When stdin is a tty, use that handle, otherwise, create a handle from
        # CONIN$.
        self.handle: HANDLE
        if sys.stdin.isatty():
            self.handle = HANDLE(windll.kernel32.GetStdHandle(STD_INPUT_HANDLE))
        else:
            self._fdcon = os.open("CONIN$", os.O_RDWR | os.O_BINARY)
            self.handle = HANDLE(msvcrt.get_osfhandle(self._fdcon))

    def close(self) -> None:
        "Close fdcon."
        if self._fdcon is not None:
            os.close(self._fdcon)

    def read(self) -> Iterable[KeyPress]:
        """
        Return a list of `KeyPress` instances. It won't return anything when
        there was nothing to read.  (This function doesn't block.)

        http://msdn.microsoft.com/en-us/library/windows/desktop/ms684961(v=vs.85).aspx
        """
        max_count = 2048  # Max events to read at the same time.

        read = DWORD(0)
        arrtype = INPUT_RECORD * max_count
        input_records = arrtype()

        # Check whether there is some input to read. `ReadConsoleInputW` would
        # block otherwise.
        # (Actually, the event loop is responsible to make sure that this
        # function is only called when there is something to read, but for some
        # reason this happened in the asyncio_win32 loop, and it's better to be
        # safe anyway.)
        if not wait_for_handles([self.handle], timeout=0):
            return

        # Get next batch of input event.
        windll.kernel32.ReadConsoleInputW(
            self.handle, pointer(input_records), max_count, pointer(read)
        )

        # First, get all the keys from the input buffer, in order to determine
        # whether we should consider this a paste event or not.
        all_keys = list(self._get_keys(read, input_records))

        # Fill in 'data' for key presses.
        all_keys = [self._insert_key_data(key) for key in all_keys]

        # Correct non-bmp characters that are passed as separate surrogate codes
        all_keys = list(self._merge_paired_surrogates(all_keys))

        if self.recognize_paste and self._is_paste(all_keys):
            gen = iter(all_keys)
            k: KeyPress | None

            for k in gen:
                # Pasting: if the current key consists of text or \n, turn it
                # into a BracketedPaste.
                data = []
                while k and (
                    not isinstance(k.key, Keys)
                    or k.key in {Keys.ControlJ, Keys.ControlM}
                ):
                    data.append(k.data)
                    try:
                        k = next(gen)
                    except StopIteration:
                        k = None

                if data:
                    yield KeyPress(Keys.BracketedPaste, "".join(data))
                if k is not None:
                    yield k
        else:
            yield from all_keys

    def _insert_key_data(self, key_press: KeyPress) -> KeyPress:
        """
        Insert KeyPress data, for vt100 compatibility.
        """
        if key_press.data:
            return key_press

        if isinstance(key_press.key, Keys):
            data = REVERSE_ANSI_SEQUENCES.get(key_press.key, "")
        else:
            data = ""

        return KeyPress(key_press.key, data)

    def _get_keys(
        self, read: DWORD, input_records: Array[INPUT_RECORD]
    ) -> Iterator[KeyPress]:
        """
        Generator that yields `KeyPress` objects from the input records.
        """
        for i in range(read.value):
            ir = input_records[i]

            # Get the right EventType from the EVENT_RECORD.
            # (For some reason the Windows console application 'cmder'
            # [http://gooseberrycreative.com/cmder/] can return '0' for
            # ir.EventType. -- Just ignore that.)
            if ir.EventType in EventTypes:
                ev = getattr(ir.Event, EventTypes[ir.EventType])

                # Process if this is a key event. (We also have mouse, menu and
                # focus events.)
                if isinstance(ev, KEY_EVENT_RECORD) and ev.KeyDown:
                    yield from self._event_to_key_presses(ev)

                elif isinstance(ev, MOUSE_EVENT_RECORD):
                    yield from self._handle_mouse(ev)

    @staticmethod
    def _merge_paired_surrogates(key_presses: list[KeyPress]) -> Iterator[KeyPress]:
        """
        Combines consecutive KeyPresses with high and low surrogates into
        single characters
        """
        buffered_high_surrogate = None
        for key in key_presses:
            is_text = not isinstance(key.key, Keys)
            is_high_surrogate = is_text and "\ud800" <= key.key <= "\udbff"
            is_low_surrogate = is_text and "\udc00" <= key.key <= "\udfff"

            if buffered_high_surrogate:
                if is_low_surrogate:
                    # convert high surrogate + low surrogate to single character
                    fullchar = (
                        (buffered_high_surrogate.key + key.key)
                        .encode("utf-16-le", "surrogatepass")
                        .decode("utf-16-le")
                    )
                    key = KeyPress(fullchar, fullchar)
                else:
                    yield buffered_high_surrogate
                buffered_high_surrogate = None

            if is_high_surrogate:
                buffered_high_surrogate = key
            else:
                yield key

        if buffered_high_surrogate:
            yield buffered_high_surrogate

    @staticmethod
    def _is_paste(keys: list[KeyPress]) -> bool:
        """
        Return `True` when we should consider this list of keys as a paste
        event. Pasted text on windows will be turned into a
        `Keys.BracketedPaste` event. (It's not 100% correct, but it is probably
        the best possible way to detect pasting of text and handle that
        correctly.)
        """
        # Consider paste when it contains at least one newline and at least one
        # other character.
        text_count = 0
        newline_count = 0

        for k in keys:
            if not isinstance(k.key, Keys):
                text_count += 1
            if k.key == Keys.ControlM:
                newline_count += 1

        return newline_count >= 1 and text_count >= 1

    def _event_to_key_presses(self, ev: KEY_EVENT_RECORD) -> list[KeyPress]:
        """
        For this `KEY_EVENT_RECORD`, return a list of `KeyPress` instances.
        """
        assert isinstance(ev, KEY_EVENT_RECORD) and ev.KeyDown

        result: KeyPress | None = None

        control_key_state = ev.ControlKeyState
        u_char = ev.uChar.UnicodeChar
        # Use surrogatepass because u_char may be an unmatched surrogate
        ascii_char = u_char.encode("utf-8", "surrogatepass")

        # NOTE: We don't use `ev.uChar.AsciiChar`. That appears to be the
        # unicode code point truncated to 1 byte. See also:
        # https://github.com/ipython/ipython/issues/10004
        # https://github.com/jonathanslenders/python-prompt-toolkit/issues/389

        if u_char == "\x00":
            if ev.VirtualKeyCode in self.keycodes:
                result = KeyPress(self.keycodes[ev.VirtualKeyCode], "")
        else:
            if ascii_char in self.mappings:
                if self.mappings[ascii_char] == Keys.ControlJ:
                    u_char = (
                        "\n"  # Windows sends \n, turn into \r for unix compatibility.
                    )
                result = KeyPress(self.mappings[ascii_char], u_char)
            else:
                result = KeyPress(u_char, u_char)

        # First we handle Shift-Control-Arrow/Home/End (need to do this first)
        if (
            (
                control_key_state & self.LEFT_CTRL_PRESSED
                or control_key_state & self.RIGHT_CTRL_PRESSED
            )
            and control_key_state & self.SHIFT_PRESSED
            and result
        ):
            mapping: dict[str, str] = {
                Keys.Left: Keys.ControlShiftLeft,
                Keys.Right: Keys.ControlShiftRight,
                Keys.Up: Keys.ControlShiftUp,
                Keys.Down: Keys.ControlShiftDown,
                Keys.Home: Keys.ControlShiftHome,
                Keys.End: Keys.ControlShiftEnd,
                Keys.Insert: Keys.ControlShiftInsert,
                Keys.PageUp: Keys.ControlShiftPageUp,
                Keys.PageDown: Keys.ControlShiftPageDown,
            }
            result.key = mapping.get(result.key, result.key)

        # Correctly handle Control-Arrow/Home/End and Control-Insert/Delete keys.
        if (
            control_key_state & self.LEFT_CTRL_PRESSED
            or control_key_state & self.RIGHT_CTRL_PRESSED
        ) and result:
            mapping = {
                Keys.Left: Keys.ControlLeft,
                Keys.Right: Keys.ControlRight,
                Keys.Up: Keys.ControlUp,
                Keys.Down: Keys.ControlDown,
                Keys.Home: Keys.ControlHome,
                Keys.End: Keys.ControlEnd,
                Keys.Insert: Keys.ControlInsert,
                Keys.Delete: Keys.ControlDelete,
                Keys.PageUp: Keys.ControlPageUp,
                Keys.PageDown: Keys.ControlPageDown,
            }
            result.key = mapping.get(result.key, result.key)

        # Turn 'Tab' into 'BackTab' when shift was pressed.
        # Also handle other shift-key combination
        if control_key_state & self.SHIFT_PRESSED and result:
            mapping = {
                Keys.Tab: Keys.BackTab,
                Keys.Left: Keys.ShiftLeft,
                Keys.Right: Keys.ShiftRight,
                Keys.Up: Keys.ShiftUp,
                Keys.Down: Keys.ShiftDown,
                Keys.Home: Keys.ShiftHome,
                Keys.End: Keys.ShiftEnd,
                Keys.Insert: Keys.ShiftInsert,
                Keys.Delete: Keys.ShiftDelete,
                Keys.PageUp: Keys.ShiftPageUp,
                Keys.PageDown: Keys.ShiftPageDown,
            }
            result.key = mapping.get(result.key, result.key)

        # Turn 'Space' into 'ControlSpace' when control was pressed.
        if (
            (
                control_key_state & self.LEFT_CTRL_PRESSED
                or control_key_state & self.RIGHT_CTRL_PRESSED
            )
            and result
            and result.data == " "
        ):
            result = KeyPress(Keys.ControlSpace, " ")

        # Turn Control-Enter into META-Enter. (On a vt100 terminal, we cannot
        # detect this combination. But it's really practical on Windows.)
        if (
            (
                control_key_state & self.LEFT_CTRL_PRESSED
                or control_key_state & self.RIGHT_CTRL_PRESSED
            )
            and result
            and result.key == Keys.ControlJ
        ):
            return [KeyPress(Keys.Escape, ""), result]

        # Return result. If alt was pressed, prefix the result with an
        # 'Escape' key, just like unix VT100 terminals do.

        # NOTE: Only replace the left alt with escape. The right alt key often
        #       acts as altgr and is used in many non US keyboard layouts for
        #       typing some special characters, like a backslash. We don't want
        #       all backslashes to be prefixed with escape. (Esc-\ has a
        #       meaning in E-macs, for instance.)
        if result:
            meta_pressed = control_key_state & self.LEFT_ALT_PRESSED

            if meta_pressed:
                return [KeyPress(Keys.Escape, ""), result]
            else:
                return [result]

        else:
            return []

    def _handle_mouse(self, ev: MOUSE_EVENT_RECORD) -> list[KeyPress]:
        """
        Handle mouse events. Return a list of KeyPress instances.
        """
        event_flags = ev.EventFlags
        button_state = ev.ButtonState

        event_type: MouseEventType | None = None
        button: MouseButton = MouseButton.NONE

        # Scroll events.
        if event_flags & MOUSE_WHEELED:
            if button_state > 0:
                event_type = MouseEventType.SCROLL_UP
            else:
                event_type = MouseEventType.SCROLL_DOWN
        else:
            # Handle button state for non-scroll events.
            if button_state == FROM_LEFT_1ST_BUTTON_PRESSED:
                button = MouseButton.LEFT

            elif button_state == RIGHTMOST_BUTTON_PRESSED:
                button = MouseButton.RIGHT

        # Move events.
        if event_flags & MOUSE_MOVED:
            event_type = MouseEventType.MOUSE_MOVE

        # No key pressed anymore: mouse up.
        if event_type is None:
            if button_state > 0:
                # Some button pressed.
                event_type = MouseEventType.MOUSE_DOWN
            else:
                # No button pressed.
                event_type = MouseEventType.MOUSE_UP

        data = ";".join(
            [
                button.value,
                event_type.value,
                str(ev.MousePosition.X),
                str(ev.MousePosition.Y),
            ]
        )
        return [KeyPress(Keys.WindowsMouseEvent, data)]


class Vt100ConsoleInputReader:
    """
    Similar to `ConsoleInputReader`, but for usage when
    `ENABLE_VIRTUAL_TERMINAL_INPUT` is enabled. This assumes that Windows sends
    us the right vt100 escape sequences and we parse those with our vt100
    parser.

    (Using this instead of `ConsoleInputReader` results in the "data" attribute
    from the `KeyPress` instances to be more correct in edge cases, because
    this responds to for instance the terminal being in application cursor keys
    mode.)
    """

    def __init__(self) -> None:
        self._fdcon = None

        self._buffer: list[KeyPress] = []  # Buffer to collect the Key objects.
        self._vt100_parser = Vt100Parser(
            lambda key_press: self._buffer.append(key_press)
        )

        # When stdin is a tty, use that handle, otherwise, create a handle from
        # CONIN$.
        self.handle: HANDLE
        if sys.stdin.isatty():
            self.handle = HANDLE(windll.kernel32.GetStdHandle(STD_INPUT_HANDLE))
        else:
            self._fdcon = os.open("CONIN$", os.O_RDWR | os.O_BINARY)
            self.handle = HANDLE(msvcrt.get_osfhandle(self._fdcon))

    def close(self) -> None:
        "Close fdcon."
        if self._fdcon is not None:
            os.close(self._fdcon)

    def read(self) -> Iterable[KeyPress]:
        """
        Return a list of `KeyPress` instances. It won't return anything when
        there was nothing to read.  (This function doesn't block.)

        http://msdn.microsoft.com/en-us/library/windows/desktop/ms684961(v=vs.85).aspx
        """
        max_count = 2048  # Max events to read at the same time.

        read = DWORD(0)
        arrtype = INPUT_RECORD * max_count
        input_records = arrtype()

        # Check whether there is some input to read. `ReadConsoleInputW` would
        # block otherwise.
        # (Actually, the event loop is responsible to make sure that this
        # function is only called when there is something to read, but for some
        # reason this happened in the asyncio_win32 loop, and it's better to be
        # safe anyway.)
        if not wait_for_handles([self.handle], timeout=0):
            return []

        # Get next batch of input event.
        windll.kernel32.ReadConsoleInputW(
            self.handle, pointer(input_records), max_count, pointer(read)
        )

        # First, get all the keys from the input buffer, in order to determine
        # whether we should consider this a paste event or not.
        for key_data in self._get_keys(read, input_records):
            self._vt100_parser.feed(key_data)

        # Return result.
        result = self._buffer
        self._buffer = []
        return result

    def _get_keys(
        self, read: DWORD, input_records: Array[INPUT_RECORD]
    ) -> Iterator[str]:
        """
        Generator that yields `KeyPress` objects from the input records.
        """
        for i in range(read.value):
            ir = input_records[i]

            # Get the right EventType from the EVENT_RECORD.
            # (For some reason the Windows console application 'cmder'
            # [http://gooseberrycreative.com/cmder/] can return '0' for
            # ir.EventType. -- Just ignore that.)
            if ir.EventType in EventTypes:
                ev = getattr(ir.Event, EventTypes[ir.EventType])

                # Process if this is a key event. (We also have mouse, menu and
                # focus events.)
                if isinstance(ev, KEY_EVENT_RECORD) and ev.KeyDown:
                    u_char = ev.uChar.UnicodeChar
                    if u_char != "\x00":
                        yield u_char


class _Win32Handles:
    """
    Utility to keep track of which handles are connectod to which callbacks.

    `add_win32_handle` starts a tiny event loop in another thread which waits
    for the Win32 handle to become ready. When this happens, the callback will
    be called in the current asyncio event loop using `call_soon_threadsafe`.

    `remove_win32_handle` will stop this tiny event loop.

    NOTE: We use this technique, so that we don't have to use the
          `ProactorEventLoop` on Windows and we can wait for things like stdin
          in a `SelectorEventLoop`. This is important, because our inputhook
          mechanism (used by IPython), only works with the `SelectorEventLoop`.
    """

    def __init__(self) -> None:
        self._handle_callbacks: dict[int, Callable[[], None]] = {}

        # Windows Events that are triggered when we have to stop watching this
        # handle.
        self._remove_events: dict[int, HANDLE] = {}

    def add_win32_handle(self, handle: HANDLE, callback: Callable[[], None]) -> None:
        """
        Add a Win32 handle to the event loop.
        """
        handle_value = handle.value

        if handle_value is None:
            raise ValueError("Invalid handle.")

        # Make sure to remove a previous registered handler first.
        self.remove_win32_handle(handle)

        loop = get_running_loop()
        self._handle_callbacks[handle_value] = callback

        # Create remove event.
        remove_event = create_win32_event()
        self._remove_events[handle_value] = remove_event

        # Add reader.
        def ready() -> None:
            # Tell the callback that input's ready.
            try:
                callback()
            finally:
                run_in_executor_with_context(wait, loop=loop)

        # Wait for the input to become ready.
        # (Use an executor for this, the Windows asyncio event loop doesn't
        # allow us to wait for handles like stdin.)
        def wait() -> None:
            # Wait until either the handle becomes ready, or the remove event
            # has been set.
            result = wait_for_handles([remove_event, handle])

            if result is remove_event:
                windll.kernel32.CloseHandle(remove_event)
                return
            else:
                loop.call_soon_threadsafe(ready)

        run_in_executor_with_context(wait, loop=loop)

    def remove_win32_handle(self, handle: HANDLE) -> Callable[[], None] | None:
        """
        Remove a Win32 handle from the event loop.
        Return either the registered handler or `None`.
        """
        if handle.value is None:
            return None  # Ignore.

        # Trigger remove events, so that the reader knows to stop.
        try:
            event = self._remove_events.pop(handle.value)
        except KeyError:
            pass
        else:
            windll.kernel32.SetEvent(event)

        try:
            return self._handle_callbacks.pop(handle.value)
        except KeyError:
            return None


@contextmanager
def attach_win32_input(
    input: _Win32InputBase, callback: Callable[[], None]
) -> Iterator[None]:
    """
    Context manager that makes this input active in the current event loop.

    :param input: :class:`~prompt_toolkit.input.Input` object.
    :param input_ready_callback: Called when the input is ready to read.
    """
    win32_handles = input.win32_handles
    handle = input.handle

    if handle.value is None:
        raise ValueError("Invalid handle.")

    # Add reader.
    previous_callback = win32_handles.remove_win32_handle(handle)
    win32_handles.add_win32_handle(handle, callback)

    try:
        yield
    finally:
        win32_handles.remove_win32_handle(handle)

        if previous_callback:
            win32_handles.add_win32_handle(handle, previous_callback)


@contextmanager
def detach_win32_input(input: _Win32InputBase) -> Iterator[None]:
    win32_handles = input.win32_handles
    handle = input.handle

    if handle.value is None:
        raise ValueError("Invalid handle.")

    previous_callback = win32_handles.remove_win32_handle(handle)

    try:
        yield
    finally:
        if previous_callback:
            win32_handles.add_win32_handle(handle, previous_callback)


class raw_mode:
    """
    ::

        with raw_mode(stdin):
            ''' the windows terminal is now in 'raw' mode. '''

    The ``fileno`` attribute is ignored. This is to be compatible with the
    `raw_input` method of `.vt100_input`.
    """

    def __init__(
        self, fileno: int | None = None, use_win10_virtual_terminal_input: bool = False
    ) -> None:
        self.handle = HANDLE(windll.kernel32.GetStdHandle(STD_INPUT_HANDLE))
        self.use_win10_virtual_terminal_input = use_win10_virtual_terminal_input

    def __enter__(self) -> None:
        # Remember original mode.
        original_mode = DWORD()
        windll.kernel32.GetConsoleMode(self.handle, pointer(original_mode))
        self.original_mode = original_mode

        self._patch()

    def _patch(self) -> None:
        # Set raw
        ENABLE_ECHO_INPUT = 0x0004
        ENABLE_LINE_INPUT = 0x0002
        ENABLE_PROCESSED_INPUT = 0x0001

        new_mode = self.original_mode.value & ~(
            ENABLE_ECHO_INPUT | ENABLE_LINE_INPUT | ENABLE_PROCESSED_INPUT
        )

        if self.use_win10_virtual_terminal_input:
            new_mode |= ENABLE_VIRTUAL_TERMINAL_INPUT

        windll.kernel32.SetConsoleMode(self.handle, new_mode)

    def __exit__(self, *a: object) -> None:
        # Restore original mode
        windll.kernel32.SetConsoleMode(self.handle, self.original_mode)


class cooked_mode(raw_mode):
    """
    ::

        with cooked_mode(stdin):
            ''' The pseudo-terminal stdin is now used in cooked mode. '''
    """

    def _patch(self) -> None:
        # Set cooked.
        ENABLE_ECHO_INPUT = 0x0004
        ENABLE_LINE_INPUT = 0x0002
        ENABLE_PROCESSED_INPUT = 0x0001

        windll.kernel32.SetConsoleMode(
            self.handle,
            self.original_mode.value
            | (ENABLE_ECHO_INPUT | ENABLE_LINE_INPUT | ENABLE_PROCESSED_INPUT),
        )


def _is_win_vt100_input_enabled() -> bool:
    """
    Returns True when we're running Windows and VT100 escape sequences are
    supported.
    """
    hconsole = HANDLE(windll.kernel32.GetStdHandle(STD_INPUT_HANDLE))

    # Get original console mode.
    original_mode = DWORD(0)
    windll.kernel32.GetConsoleMode(hconsole, byref(original_mode))

    try:
        # Try to enable VT100 sequences.
        result: int = windll.kernel32.SetConsoleMode(
            hconsole, DWORD(ENABLE_VIRTUAL_TERMINAL_INPUT)
        )

        return result == 1
    finally:
        windll.kernel32.SetConsoleMode(hconsole, original_mode)

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydev_runfiles\pydev_runfiles.py ===
from __future__ import nested_scopes

import fnmatch
import os.path
from _pydev_runfiles.pydev_runfiles_coverage import start_coverage_support
from _pydevd_bundle.pydevd_constants import *  # @UnusedWildImport
import re
import time
import json


# =======================================================================================================================
# Configuration
# =======================================================================================================================
class Configuration:
    def __init__(
        self,
        files_or_dirs="",
        verbosity=2,
        include_tests=None,
        tests=None,
        port=None,
        files_to_tests=None,
        jobs=1,
        split_jobs="tests",
        coverage_output_dir=None,
        coverage_include=None,
        coverage_output_file=None,
        exclude_files=None,
        exclude_tests=None,
        include_files=None,
        django=False,
    ):
        self.files_or_dirs = files_or_dirs
        self.verbosity = verbosity
        self.include_tests = include_tests
        self.tests = tests
        self.port = port
        self.files_to_tests = files_to_tests
        self.jobs = jobs
        self.split_jobs = split_jobs
        self.django = django

        if include_tests:
            assert isinstance(include_tests, (list, tuple))

        if exclude_files:
            assert isinstance(exclude_files, (list, tuple))

        if exclude_tests:
            assert isinstance(exclude_tests, (list, tuple))

        self.exclude_files = exclude_files
        self.include_files = include_files
        self.exclude_tests = exclude_tests

        self.coverage_output_dir = coverage_output_dir
        self.coverage_include = coverage_include
        self.coverage_output_file = coverage_output_file

    def __str__(self):
        return """Configuration
 - files_or_dirs: %s
 - verbosity: %s
 - tests: %s
 - port: %s
 - files_to_tests: %s
 - jobs: %s
 - split_jobs: %s

 - include_files: %s
 - include_tests: %s

 - exclude_files: %s
 - exclude_tests: %s

 - coverage_output_dir: %s
 - coverage_include_dir: %s
 - coverage_output_file: %s

 - django: %s
""" % (
            self.files_or_dirs,
            self.verbosity,
            self.tests,
            self.port,
            self.files_to_tests,
            self.jobs,
            self.split_jobs,
            self.include_files,
            self.include_tests,
            self.exclude_files,
            self.exclude_tests,
            self.coverage_output_dir,
            self.coverage_include,
            self.coverage_output_file,
            self.django,
        )


# =======================================================================================================================
# parse_cmdline
# =======================================================================================================================
def parse_cmdline(argv=None):
    """
    Parses command line and returns test directories, verbosity, test filter and test suites

    usage:
        runfiles.py  -v|--verbosity <level>  -t|--tests <Test.test1,Test2>  dirs|files

    Multiprocessing options:
    jobs=number (with the number of jobs to be used to run the tests)
    split_jobs='module'|'tests'
        if == module, a given job will always receive all the tests from a module
        if == tests, the tests will be split independently of their originating module (default)

    --exclude_files  = comma-separated list of patterns with files to exclude (fnmatch style)
    --include_files = comma-separated list of patterns with files to include (fnmatch style)
    --exclude_tests = comma-separated list of patterns with test names to exclude (fnmatch style)

    Note: if --tests is given, --exclude_files, --include_files and --exclude_tests are ignored!
    """
    if argv is None:
        argv = sys.argv

    verbosity = 2
    include_tests = None
    tests = None
    port = None
    jobs = 1
    split_jobs = "tests"
    files_to_tests = {}
    coverage_output_dir = None
    coverage_include = None
    exclude_files = None
    exclude_tests = None
    include_files = None
    django = False

    from _pydev_bundle._pydev_getopt import gnu_getopt

    optlist, dirs = gnu_getopt(
        argv[1:],
        "",
        [
            "verbosity=",
            "tests=",
            "port=",
            "config_file=",
            "jobs=",
            "split_jobs=",
            "include_tests=",
            "include_files=",
            "exclude_files=",
            "exclude_tests=",
            "coverage_output_dir=",
            "coverage_include=",
            "django=",
        ],
    )

    for opt, value in optlist:
        if opt in ("-v", "--verbosity"):
            verbosity = value

        elif opt in ("-p", "--port"):
            port = int(value)

        elif opt in ("-j", "--jobs"):
            jobs = int(value)

        elif opt in ("-s", "--split_jobs"):
            split_jobs = value
            if split_jobs not in ("module", "tests"):
                raise AssertionError('Expected split to be either "module" or "tests". Was :%s' % (split_jobs,))

        elif opt in (
            "-d",
            "--coverage_output_dir",
        ):
            coverage_output_dir = value.strip()

        elif opt in (
            "-i",
            "--coverage_include",
        ):
            coverage_include = value.strip()

        elif opt in ("-I", "--include_tests"):
            include_tests = value.split(",")

        elif opt in ("-E", "--exclude_files"):
            exclude_files = value.split(",")

        elif opt in ("-F", "--include_files"):
            include_files = value.split(",")

        elif opt in ("-e", "--exclude_tests"):
            exclude_tests = value.split(",")

        elif opt in ("-t", "--tests"):
            tests = value.split(",")

        elif opt in ("--django",):
            django = value.strip() in ["true", "True", "1"]

        elif opt in ("-c", "--config_file"):
            config_file = value.strip()
            if os.path.exists(config_file):
                f = open(config_file, "r")
                try:
                    config_file_contents = f.read()
                finally:
                    f.close()

                if config_file_contents:
                    config_file_contents = config_file_contents.strip()

                if config_file_contents:
                    for line in config_file_contents.splitlines():
                        file_and_test = line.split("|")
                        if len(file_and_test) == 2:
                            file, test = file_and_test
                            if file in files_to_tests:
                                files_to_tests[file].append(test)
                            else:
                                files_to_tests[file] = [test]

            else:
                sys.stderr.write("Could not find config file: %s\n" % (config_file,))

    filter_tests_env_var = os.environ.get("PYDEV_RUNFILES_FILTER_TESTS", None)
    if filter_tests_env_var:
        loaded = json.loads(filter_tests_env_var)
        include = loaded["include"]
        for path, name in include:
            existing = files_to_tests.get(path)
            if not existing:
                existing = files_to_tests[path] = []
            existing.append(name)
        # Note: at this point exclude or `*` is not handled.
        # Clients need to do all the filtering on their side (could
        # change to have `exclude` and support `*` entries).

    if type([]) != type(dirs):
        dirs = [dirs]

    ret_dirs = []
    for d in dirs:
        if "|" in d:
            # paths may come from the ide separated by |
            ret_dirs.extend(d.split("|"))
        else:
            ret_dirs.append(d)

    verbosity = int(verbosity)

    if tests:
        if verbosity > 4:
            sys.stdout.write("--tests provided. Ignoring --exclude_files, --exclude_tests and --include_files\n")
        exclude_files = exclude_tests = include_files = None

    config = Configuration(
        ret_dirs,
        verbosity,
        include_tests,
        tests,
        port,
        files_to_tests,
        jobs,
        split_jobs,
        coverage_output_dir,
        coverage_include,
        exclude_files=exclude_files,
        exclude_tests=exclude_tests,
        include_files=include_files,
        django=django,
    )

    if verbosity > 5:
        sys.stdout.write(str(config) + "\n")
    return config


# =======================================================================================================================
# PydevTestRunner
# =======================================================================================================================
class PydevTestRunner(object):
    """finds and runs a file or directory of files as a unit test"""

    __py_extensions = ["*.py", "*.pyw"]
    __exclude_files = ["__init__.*"]

    # Just to check that only this attributes will be written to this file
    __slots__ = [
        "verbosity",  # Always used
        "files_to_tests",  # If this one is given, the ones below are not used
        "files_or_dirs",  # Files or directories received in the command line
        "include_tests",  # The filter used to collect the tests
        "tests",  # Strings with the tests to be run
        "jobs",  # Integer with the number of jobs that should be used to run the test cases
        "split_jobs",  # String with 'tests' or 'module' (how should the jobs be split)
        "configuration",
        "coverage",
    ]

    def __init__(self, configuration):
        self.verbosity = configuration.verbosity

        self.jobs = configuration.jobs
        self.split_jobs = configuration.split_jobs

        files_to_tests = configuration.files_to_tests
        if files_to_tests:
            self.files_to_tests = files_to_tests
            self.files_or_dirs = list(files_to_tests.keys())
            self.tests = None
        else:
            self.files_to_tests = {}
            self.files_or_dirs = configuration.files_or_dirs
            self.tests = configuration.tests

        self.configuration = configuration
        self.__adjust_path()

    def __adjust_path(self):
        """add the current file or directory to the python path"""
        path_to_append = None
        for n in range(len(self.files_or_dirs)):
            dir_name = self.__unixify(self.files_or_dirs[n])
            if os.path.isdir(dir_name):
                if not dir_name.endswith("/"):
                    self.files_or_dirs[n] = dir_name + "/"
                path_to_append = os.path.normpath(dir_name)
            elif os.path.isfile(dir_name):
                path_to_append = os.path.dirname(dir_name)
            else:
                if not os.path.exists(dir_name):
                    block_line = "*" * 120
                    sys.stderr.write("\n%s\n* PyDev test runner error: %s does not exist.\n%s\n" % (block_line, dir_name, block_line))
                    return
                msg = "unknown type. \n%s\nshould be file or a directory.\n" % (dir_name)
                raise RuntimeError(msg)
        if path_to_append is not None:
            # Add it as the last one (so, first things are resolved against the default dirs and
            # if none resolves, then we try a relative import).
            sys.path.append(path_to_append)

    def __is_valid_py_file(self, fname):
        """tests that a particular file contains the proper file extension
        and is not in the list of files to exclude"""
        is_valid_fname = 0
        for invalid_fname in self.__class__.__exclude_files:
            is_valid_fname += int(not fnmatch.fnmatch(fname, invalid_fname))
        if_valid_ext = 0
        for ext in self.__class__.__py_extensions:
            if_valid_ext += int(fnmatch.fnmatch(fname, ext))
        return is_valid_fname > 0 and if_valid_ext > 0

    def __unixify(self, s):
        """stupid windows. converts the backslash to forwardslash for consistency"""
        return os.path.normpath(s).replace(os.sep, "/")

    def __importify(self, s, dir=False):
        """turns directory separators into dots and removes the ".py*" extension
        so the string can be used as import statement"""
        if not dir:
            dirname, fname = os.path.split(s)

            if fname.count(".") > 1:
                # if there's a file named xxx.xx.py, it is not a valid module, so, let's not load it...
                return

            imp_stmt_pieces = [dirname.replace("\\", "/").replace("/", "."), os.path.splitext(fname)[0]]

            if len(imp_stmt_pieces[0]) == 0:
                imp_stmt_pieces = imp_stmt_pieces[1:]

            return ".".join(imp_stmt_pieces)

        else:  # handle dir
            return s.replace("\\", "/").replace("/", ".")

    def __add_files(self, pyfiles, root, files):
        """if files match, appends them to pyfiles. used by os.path.walk fcn"""
        for fname in files:
            if self.__is_valid_py_file(fname):
                name_without_base_dir = self.__unixify(os.path.join(root, fname))
                pyfiles.append(name_without_base_dir)

    def find_import_files(self):
        """return a list of files to import"""
        if self.files_to_tests:
            pyfiles = self.files_to_tests.keys()
        else:
            pyfiles = []

            for base_dir in self.files_or_dirs:
                if os.path.isdir(base_dir):
                    for root, dirs, files in os.walk(base_dir):
                        # Note: handling directories that should be excluded from the search because
                        # they don't have __init__.py
                        exclude = {}
                        for d in dirs:
                            for init in ["__init__.py", "__init__.pyo", "__init__.pyc", "__init__.pyw", "__init__$py.class"]:
                                if os.path.exists(os.path.join(root, d, init).replace("\\", "/")):
                                    break
                            else:
                                exclude[d] = 1

                        if exclude:
                            new = []
                            for d in dirs:
                                if d not in exclude:
                                    new.append(d)

                            dirs[:] = new

                        self.__add_files(pyfiles, root, files)

                elif os.path.isfile(base_dir):
                    pyfiles.append(base_dir)

        if self.configuration.exclude_files or self.configuration.include_files:
            ret = []
            for f in pyfiles:
                add = True
                basename = os.path.basename(f)
                if self.configuration.include_files:
                    add = False

                    for pat in self.configuration.include_files:
                        if fnmatch.fnmatchcase(basename, pat):
                            add = True
                            break

                if not add:
                    if self.verbosity > 3:
                        sys.stdout.write(
                            "Skipped file: %s (did not match any include_files pattern: %s)\n" % (f, self.configuration.include_files)
                        )

                elif self.configuration.exclude_files:
                    for pat in self.configuration.exclude_files:
                        if fnmatch.fnmatchcase(basename, pat):
                            if self.verbosity > 3:
                                sys.stdout.write("Skipped file: %s (matched exclude_files pattern: %s)\n" % (f, pat))

                            elif self.verbosity > 2:
                                sys.stdout.write("Skipped file: %s\n" % (f,))

                            add = False
                            break

                if add:
                    if self.verbosity > 3:
                        sys.stdout.write("Adding file: %s for test discovery.\n" % (f,))
                    ret.append(f)

            pyfiles = ret

        return pyfiles

    def __get_module_from_str(self, modname, print_exception, pyfile):
        """Import the module in the given import path.
        * Returns the "final" module, so importing "coilib40.subject.visu"
        returns the "visu" module, not the "coilib40" as returned by __import__"""
        try:
            mod = __import__(modname)
            for part in modname.split(".")[1:]:
                mod = getattr(mod, part)
            return mod
        except:
            if print_exception:
                from _pydev_runfiles import pydev_runfiles_xml_rpc
                from _pydevd_bundle import pydevd_io

                buf_err = pydevd_io.start_redirect(keep_original_redirection=True, std="stderr")
                buf_out = pydevd_io.start_redirect(keep_original_redirection=True, std="stdout")
                try:
                    import traceback

                    traceback.print_exc()
                    sys.stderr.write("ERROR: Module: %s could not be imported (file: %s).\n" % (modname, pyfile))
                finally:
                    pydevd_io.end_redirect("stderr")
                    pydevd_io.end_redirect("stdout")

                pydev_runfiles_xml_rpc.notifyTest("error", buf_out.getvalue(), buf_err.getvalue(), pyfile, modname, 0)

            return None

    def remove_duplicates_keeping_order(self, seq):
        seen = set()
        seen_add = seen.add
        return [x for x in seq if not (x in seen or seen_add(x))]

    def find_modules_from_files(self, pyfiles):
        """returns a list of modules given a list of files"""
        # let's make sure that the paths we want are in the pythonpath...
        imports = [(s, self.__importify(s)) for s in pyfiles]

        sys_path = [os.path.normpath(path) for path in sys.path]
        sys_path = self.remove_duplicates_keeping_order(sys_path)

        system_paths = []
        for s in sys_path:
            system_paths.append(self.__importify(s, True))

        ret = []
        for pyfile, imp in imports:
            if imp is None:
                continue  # can happen if a file is not a valid module
            choices = []
            for s in system_paths:
                if imp.startswith(s):
                    add = imp[len(s) + 1 :]
                    if add:
                        choices.append(add)
                    # sys.stdout.write(' ' + add + ' ')

            if not choices:
                sys.stdout.write("PYTHONPATH not found for file: %s\n" % imp)
            else:
                for i, import_str in enumerate(choices):
                    print_exception = i == len(choices) - 1
                    mod = self.__get_module_from_str(import_str, print_exception, pyfile)
                    if mod is not None:
                        ret.append((pyfile, mod, import_str))
                        break

        return ret

    # ===================================================================================================================
    # GetTestCaseNames
    # ===================================================================================================================
    class GetTestCaseNames:
        """Yes, we need a class for that (cannot use outer context on jython 2.1)"""

        def __init__(self, accepted_classes, accepted_methods):
            self.accepted_classes = accepted_classes
            self.accepted_methods = accepted_methods

        def __call__(self, testCaseClass):
            """Return a sorted sequence of method names found within testCaseClass"""
            testFnNames = []
            className = testCaseClass.__name__

            if className in self.accepted_classes:
                for attrname in dir(testCaseClass):
                    # If a class is chosen, we select all the 'test' methods'
                    if attrname.startswith("test") and hasattr(getattr(testCaseClass, attrname), "__call__"):
                        testFnNames.append(attrname)

            else:
                for attrname in dir(testCaseClass):
                    # If we have the class+method name, we must do a full check and have an exact match.
                    if className + "." + attrname in self.accepted_methods:
                        if hasattr(getattr(testCaseClass, attrname), "__call__"):
                            testFnNames.append(attrname)

            # sorted() is not available in jython 2.1
            testFnNames.sort()
            return testFnNames

    def _decorate_test_suite(self, suite, pyfile, module_name):
        import unittest

        if isinstance(suite, unittest.TestSuite):
            add = False
            suite.__pydev_pyfile__ = pyfile
            suite.__pydev_module_name__ = module_name

            for t in suite._tests:
                t.__pydev_pyfile__ = pyfile
                t.__pydev_module_name__ = module_name
                if self._decorate_test_suite(t, pyfile, module_name):
                    add = True

            return add

        elif isinstance(suite, unittest.TestCase):
            return True

        else:
            return False

    def find_tests_from_modules(self, file_and_modules_and_module_name):
        """returns the unittests given a list of modules"""
        # Use our own suite!
        from _pydev_runfiles import pydev_runfiles_unittest
        import unittest

        unittest.TestLoader.suiteClass = pydev_runfiles_unittest.PydevTestSuite
        loader = unittest.TestLoader()

        ret = []
        if self.files_to_tests:
            for pyfile, m, module_name in file_and_modules_and_module_name:
                accepted_classes = {}
                accepted_methods = {}
                tests = self.files_to_tests[pyfile]
                for t in tests:
                    accepted_methods[t] = t

                loader.getTestCaseNames = self.GetTestCaseNames(accepted_classes, accepted_methods)

                suite = loader.loadTestsFromModule(m)
                if self._decorate_test_suite(suite, pyfile, module_name):
                    ret.append(suite)
            return ret

        if self.tests:
            accepted_classes = {}
            accepted_methods = {}

            for t in self.tests:
                splitted = t.split(".")
                if len(splitted) == 1:
                    accepted_classes[t] = t

                elif len(splitted) == 2:
                    accepted_methods[t] = t

            loader.getTestCaseNames = self.GetTestCaseNames(accepted_classes, accepted_methods)

        for pyfile, m, module_name in file_and_modules_and_module_name:
            suite = loader.loadTestsFromModule(m)
            if self._decorate_test_suite(suite, pyfile, module_name):
                ret.append(suite)

        return ret

    def filter_tests(self, test_objs, internal_call=False):
        """based on a filter name, only return those tests that have
        the test case names that match"""
        import unittest

        if not internal_call:
            if not self.configuration.include_tests and not self.tests and not self.configuration.exclude_tests:
                # No need to filter if we have nothing to filter!
                return test_objs

            if self.verbosity > 1:
                if self.configuration.include_tests:
                    sys.stdout.write("Tests to include: %s\n" % (self.configuration.include_tests,))

                if self.tests:
                    sys.stdout.write("Tests to run: %s\n" % (self.tests,))

                if self.configuration.exclude_tests:
                    sys.stdout.write("Tests to exclude: %s\n" % (self.configuration.exclude_tests,))

        test_suite = []
        for test_obj in test_objs:
            if isinstance(test_obj, unittest.TestSuite):
                # Note: keep the suites as they are and just 'fix' the tests (so, don't use the iter_tests).
                if test_obj._tests:
                    test_obj._tests = self.filter_tests(test_obj._tests, True)
                    if test_obj._tests:  # Only add the suite if we still have tests there.
                        test_suite.append(test_obj)

            elif isinstance(test_obj, unittest.TestCase):
                try:
                    testMethodName = test_obj._TestCase__testMethodName
                except AttributeError:
                    # changed in python 2.5
                    testMethodName = test_obj._testMethodName

                add = True
                if self.configuration.exclude_tests:
                    for pat in self.configuration.exclude_tests:
                        if fnmatch.fnmatchcase(testMethodName, pat):
                            if self.verbosity > 3:
                                sys.stdout.write("Skipped test: %s (matched exclude_tests pattern: %s)\n" % (testMethodName, pat))

                            elif self.verbosity > 2:
                                sys.stdout.write("Skipped test: %s\n" % (testMethodName,))

                            add = False
                            break

                if add:
                    if self.__match_tests(self.tests, test_obj, testMethodName):
                        include = True
                        if self.configuration.include_tests:
                            include = False
                            for pat in self.configuration.include_tests:
                                if fnmatch.fnmatchcase(testMethodName, pat):
                                    include = True
                                    break
                        if include:
                            test_suite.append(test_obj)
                        else:
                            if self.verbosity > 3:
                                sys.stdout.write(
                                    "Skipped test: %s (did not match any include_tests pattern %s)\n"
                                    % (
                                        testMethodName,
                                        self.configuration.include_tests,
                                    )
                                )
        return test_suite

    def iter_tests(self, test_objs):
        # Note: not using yield because of Jython 2.1.
        import unittest

        tests = []
        for test_obj in test_objs:
            if isinstance(test_obj, unittest.TestSuite):
                tests.extend(self.iter_tests(test_obj._tests))

            elif isinstance(test_obj, unittest.TestCase):
                tests.append(test_obj)
        return tests

    def list_test_names(self, test_objs):
        names = []
        for tc in self.iter_tests(test_objs):
            try:
                testMethodName = tc._TestCase__testMethodName
            except AttributeError:
                # changed in python 2.5
                testMethodName = tc._testMethodName
            names.append(testMethodName)
        return names

    def __match_tests(self, tests, test_case, test_method_name):
        if not tests:
            return 1

        for t in tests:
            class_and_method = t.split(".")
            if len(class_and_method) == 1:
                # only class name
                if class_and_method[0] == test_case.__class__.__name__:
                    return 1

            elif len(class_and_method) == 2:
                if class_and_method[0] == test_case.__class__.__name__ and class_and_method[1] == test_method_name:
                    return 1

        return 0

    def __match(self, filter_list, name):
        """returns whether a test name matches the test filter"""
        if filter_list is None:
            return 1
        for f in filter_list:
            if re.match(f, name):
                return 1
        return 0

    def run_tests(self, handle_coverage=True):
        """runs all tests"""
        sys.stdout.write("Finding files... ")
        files = self.find_import_files()
        if self.verbosity > 3:
            sys.stdout.write("%s ... done.\n" % (self.files_or_dirs))
        else:
            sys.stdout.write("done.\n")
        sys.stdout.write("Importing test modules ... ")

        if self.configuration.django:
            import django

            if hasattr(django, "setup"):
                django.setup()

        if handle_coverage:
            coverage_files, coverage = start_coverage_support(self.configuration)

        file_and_modules_and_module_name = self.find_modules_from_files(files)
        sys.stdout.write("done.\n")

        all_tests = self.find_tests_from_modules(file_and_modules_and_module_name)
        all_tests = self.filter_tests(all_tests)

        from _pydev_runfiles import pydev_runfiles_unittest

        test_suite = pydev_runfiles_unittest.PydevTestSuite(all_tests)
        from _pydev_runfiles import pydev_runfiles_xml_rpc

        pydev_runfiles_xml_rpc.notifyTestsCollected(test_suite.countTestCases())

        start_time = time.time()

        def run_tests():
            executed_in_parallel = False
            if self.jobs > 1:
                from _pydev_runfiles import pydev_runfiles_parallel

                # What may happen is that the number of jobs needed is lower than the number of jobs requested
                # (e.g.: 2 jobs were requested for running 1 test) -- in which case execute_tests_in_parallel will
                # return False and won't run any tests.
                executed_in_parallel = pydev_runfiles_parallel.execute_tests_in_parallel(
                    all_tests, self.jobs, self.split_jobs, self.verbosity, coverage_files, self.configuration.coverage_include
                )

            if not executed_in_parallel:
                # If in coverage, we don't need to pass anything here (coverage is already enabled for this execution).
                runner = pydev_runfiles_unittest.PydevTextTestRunner(stream=sys.stdout, descriptions=1, verbosity=self.verbosity)
                sys.stdout.write("\n")
                runner.run(test_suite)

        if self.configuration.django:
            get_django_test_suite_runner()(run_tests).run_tests([])
        else:
            run_tests()

        if handle_coverage:
            coverage.stop()
            coverage.save()

        total_time = "Finished in: %.2f secs." % (time.time() - start_time,)
        pydev_runfiles_xml_rpc.notifyTestRunFinished(total_time)


DJANGO_TEST_SUITE_RUNNER = None


def get_django_test_suite_runner():
    global DJANGO_TEST_SUITE_RUNNER
    if DJANGO_TEST_SUITE_RUNNER:
        return DJANGO_TEST_SUITE_RUNNER
    try:
        # django >= 1.8
        import django
        from django.test.runner import DiscoverRunner

        class MyDjangoTestSuiteRunner(DiscoverRunner):
            def __init__(self, on_run_suite):
                django.setup()
                DiscoverRunner.__init__(self)
                self.on_run_suite = on_run_suite

            def build_suite(self, *args, **kwargs):
                pass

            def suite_result(self, *args, **kwargs):
                pass

            def run_suite(self, *args, **kwargs):
                self.on_run_suite()

    except:
        # django < 1.8
        try:
            from django.test.simple import DjangoTestSuiteRunner
        except:

            class DjangoTestSuiteRunner:
                def __init__(self):
                    pass

                def run_tests(self, *args, **kwargs):
                    raise AssertionError(
                        "Unable to run suite with django.test.runner.DiscoverRunner nor django.test.simple.DjangoTestSuiteRunner because it couldn't be imported."
                    )

        class MyDjangoTestSuiteRunner(DjangoTestSuiteRunner):
            def __init__(self, on_run_suite):
                DjangoTestSuiteRunner.__init__(self)
                self.on_run_suite = on_run_suite

            def build_suite(self, *args, **kwargs):
                pass

            def suite_result(self, *args, **kwargs):
                pass

            def run_suite(self, *args, **kwargs):
                self.on_run_suite()

    DJANGO_TEST_SUITE_RUNNER = MyDjangoTestSuiteRunner
    return DJANGO_TEST_SUITE_RUNNER


# =======================================================================================================================
# main
# =======================================================================================================================
def main(configuration):
    PydevTestRunner(configuration).run_tests()

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\TupleVariation.py ===
from fontTools.misc.fixedTools import (
    fixedToFloat as fi2fl,
    floatToFixed as fl2fi,
    floatToFixedToStr as fl2str,
    strToFixedToFloat as str2fl,
    otRound,
)
from fontTools.misc.textTools import safeEval
import array
from collections import Counter, defaultdict
import io
import logging
import struct
import sys


# https://www.microsoft.com/typography/otspec/otvarcommonformats.htm

EMBEDDED_PEAK_TUPLE = 0x8000
INTERMEDIATE_REGION = 0x4000
PRIVATE_POINT_NUMBERS = 0x2000

DELTAS_ARE_ZERO = 0x80
DELTAS_ARE_WORDS = 0x40
DELTAS_ARE_LONGS = 0xC0
DELTAS_SIZE_MASK = 0xC0
DELTA_RUN_COUNT_MASK = 0x3F

POINTS_ARE_WORDS = 0x80
POINT_RUN_COUNT_MASK = 0x7F

TUPLES_SHARE_POINT_NUMBERS = 0x8000
TUPLE_COUNT_MASK = 0x0FFF
TUPLE_INDEX_MASK = 0x0FFF

log = logging.getLogger(__name__)


class TupleVariation(object):
    def __init__(self, axes, coordinates):
        self.axes = axes.copy()
        self.coordinates = list(coordinates)

    def __repr__(self):
        axes = ",".join(
            sorted(["%s=%s" % (name, value) for (name, value) in self.axes.items()])
        )
        return "<TupleVariation %s %s>" % (axes, self.coordinates)

    def __eq__(self, other):
        return self.coordinates == other.coordinates and self.axes == other.axes

    def getUsedPoints(self):
        # Empty set means "all points used".
        if None not in self.coordinates:
            return frozenset()
        used = frozenset([i for i, p in enumerate(self.coordinates) if p is not None])
        # Return None if no points used.
        return used if used else None

    def hasImpact(self):
        """Returns True if this TupleVariation has any visible impact.

        If the result is False, the TupleVariation can be omitted from the font
        without making any visible difference.
        """
        return any(c is not None for c in self.coordinates)

    def toXML(self, writer, axisTags):
        writer.begintag("tuple")
        writer.newline()
        for axis in axisTags:
            value = self.axes.get(axis)
            if value is not None:
                minValue, value, maxValue = value
                defaultMinValue = min(value, 0.0)  # -0.3 --> -0.3; 0.7 --> 0.0
                defaultMaxValue = max(value, 0.0)  # -0.3 -->  0.0; 0.7 --> 0.7
                if minValue == defaultMinValue and maxValue == defaultMaxValue:
                    writer.simpletag("coord", axis=axis, value=fl2str(value, 14))
                else:
                    attrs = [
                        ("axis", axis),
                        ("min", fl2str(minValue, 14)),
                        ("value", fl2str(value, 14)),
                        ("max", fl2str(maxValue, 14)),
                    ]
                    writer.simpletag("coord", attrs)
                writer.newline()
        wrote_any_deltas = False
        for i, delta in enumerate(self.coordinates):
            if type(delta) == tuple and len(delta) == 2:
                writer.simpletag("delta", pt=i, x=delta[0], y=delta[1])
                writer.newline()
                wrote_any_deltas = True
            elif type(delta) == int:
                writer.simpletag("delta", cvt=i, value=delta)
                writer.newline()
                wrote_any_deltas = True
            elif delta is not None:
                log.error("bad delta format")
                writer.comment("bad delta #%d" % i)
                writer.newline()
                wrote_any_deltas = True
        if not wrote_any_deltas:
            writer.comment("no deltas")
            writer.newline()
        writer.endtag("tuple")
        writer.newline()

    def fromXML(self, name, attrs, _content):
        if name == "coord":
            axis = attrs["axis"]
            value = str2fl(attrs["value"], 14)
            defaultMinValue = min(value, 0.0)  # -0.3 --> -0.3; 0.7 --> 0.0
            defaultMaxValue = max(value, 0.0)  # -0.3 -->  0.0; 0.7 --> 0.7
            minValue = str2fl(attrs.get("min", defaultMinValue), 14)
            maxValue = str2fl(attrs.get("max", defaultMaxValue), 14)
            self.axes[axis] = (minValue, value, maxValue)
        elif name == "delta":
            if "pt" in attrs:
                point = safeEval(attrs["pt"])
                x = safeEval(attrs["x"])
                y = safeEval(attrs["y"])
                self.coordinates[point] = (x, y)
            elif "cvt" in attrs:
                cvt = safeEval(attrs["cvt"])
                value = safeEval(attrs["value"])
                self.coordinates[cvt] = value
            else:
                log.warning("bad delta format: %s" % ", ".join(sorted(attrs.keys())))

    def compile(
        self, axisTags, sharedCoordIndices={}, pointData=None, *, optimizeSize=True
    ):
        assert set(self.axes.keys()) <= set(axisTags), (
            "Unknown axis tag found.",
            self.axes.keys(),
            axisTags,
        )

        tupleData = []
        auxData = []

        if pointData is None:
            usedPoints = self.getUsedPoints()
            if usedPoints is None:  # Nothing to encode
                return b"", b""
            pointData = self.compilePoints(usedPoints)

        coord = self.compileCoord(axisTags)
        flags = sharedCoordIndices.get(coord)
        if flags is None:
            flags = EMBEDDED_PEAK_TUPLE
            tupleData.append(coord)

        intermediateCoord = self.compileIntermediateCoord(axisTags)
        if intermediateCoord is not None:
            flags |= INTERMEDIATE_REGION
            tupleData.append(intermediateCoord)

        # pointData of b'' implies "use shared points".
        if pointData:
            flags |= PRIVATE_POINT_NUMBERS
            auxData.append(pointData)

        auxData.append(self.compileDeltas(optimizeSize=optimizeSize))
        auxData = b"".join(auxData)

        tupleData.insert(0, struct.pack(">HH", len(auxData), flags))
        return b"".join(tupleData), auxData

    def compileCoord(self, axisTags):
        result = []
        axes = self.axes
        for axis in axisTags:
            triple = axes.get(axis)
            if triple is None:
                result.append(b"\0\0")
            else:
                result.append(struct.pack(">h", fl2fi(triple[1], 14)))
        return b"".join(result)

    def compileIntermediateCoord(self, axisTags):
        needed = False
        for axis in axisTags:
            minValue, value, maxValue = self.axes.get(axis, (0.0, 0.0, 0.0))
            defaultMinValue = min(value, 0.0)  # -0.3 --> -0.3; 0.7 --> 0.0
            defaultMaxValue = max(value, 0.0)  # -0.3 -->  0.0; 0.7 --> 0.7
            if (minValue != defaultMinValue) or (maxValue != defaultMaxValue):
                needed = True
                break
        if not needed:
            return None
        minCoords = []
        maxCoords = []
        for axis in axisTags:
            minValue, value, maxValue = self.axes.get(axis, (0.0, 0.0, 0.0))
            minCoords.append(struct.pack(">h", fl2fi(minValue, 14)))
            maxCoords.append(struct.pack(">h", fl2fi(maxValue, 14)))
        return b"".join(minCoords + maxCoords)

    @staticmethod
    def decompileCoord_(axisTags, data, offset):
        coord = {}
        pos = offset
        for axis in axisTags:
            coord[axis] = fi2fl(struct.unpack(">h", data[pos : pos + 2])[0], 14)
            pos += 2
        return coord, pos

    @staticmethod
    def compilePoints(points):
        # If the set consists of all points in the glyph, it gets encoded with
        # a special encoding: a single zero byte.
        #
        # To use this optimization, points passed in must be empty set.
        # The following two lines are not strictly necessary as the main code
        # below would emit the same. But this is most common and faster.
        if not points:
            return b"\0"

        # In the 'gvar' table, the packing of point numbers is a little surprising.
        # It consists of multiple runs, each being a delta-encoded list of integers.
        # For example, the point set {17, 18, 19, 20, 21, 22, 23} gets encoded as
        # [6, 17, 1, 1, 1, 1, 1, 1]. The first value (6) is the run length minus 1.
        # There are two types of runs, with values being either 8 or 16 bit unsigned
        # integers.
        points = list(points)
        points.sort()
        numPoints = len(points)

        result = bytearray()
        # The binary representation starts with the total number of points in the set,
        # encoded into one or two bytes depending on the value.
        if numPoints < 0x80:
            result.append(numPoints)
        else:
            result.append((numPoints >> 8) | 0x80)
            result.append(numPoints & 0xFF)

        MAX_RUN_LENGTH = 127
        pos = 0
        lastValue = 0
        while pos < numPoints:
            runLength = 0

            headerPos = len(result)
            result.append(0)

            useByteEncoding = None
            while pos < numPoints and runLength <= MAX_RUN_LENGTH:
                curValue = points[pos]
                delta = curValue - lastValue
                if useByteEncoding is None:
                    useByteEncoding = 0 <= delta <= 0xFF
                if useByteEncoding and (delta > 0xFF or delta < 0):
                    # we need to start a new run (which will not use byte encoding)
                    break
                # TODO This never switches back to a byte-encoding from a short-encoding.
                # That's suboptimal.
                if useByteEncoding:
                    result.append(delta)
                else:
                    result.append(delta >> 8)
                    result.append(delta & 0xFF)
                lastValue = curValue
                pos += 1
                runLength += 1
            if useByteEncoding:
                result[headerPos] = runLength - 1
            else:
                result[headerPos] = (runLength - 1) | POINTS_ARE_WORDS

        return result

    @staticmethod
    def decompilePoints_(numPoints, data, offset, tableTag):
        """(numPoints, data, offset, tableTag) --> ([point1, point2, ...], newOffset)"""
        assert tableTag in ("cvar", "gvar")
        pos = offset
        numPointsInData = data[pos]
        pos += 1
        if (numPointsInData & POINTS_ARE_WORDS) != 0:
            numPointsInData = (numPointsInData & POINT_RUN_COUNT_MASK) << 8 | data[pos]
            pos += 1
        if numPointsInData == 0:
            return (range(numPoints), pos)

        result = []
        while len(result) < numPointsInData:
            runHeader = data[pos]
            pos += 1
            numPointsInRun = (runHeader & POINT_RUN_COUNT_MASK) + 1
            point = 0
            if (runHeader & POINTS_ARE_WORDS) != 0:
                points = array.array("H")
                pointsSize = numPointsInRun * 2
            else:
                points = array.array("B")
                pointsSize = numPointsInRun
            points.frombytes(data[pos : pos + pointsSize])
            if sys.byteorder != "big":
                points.byteswap()

            assert len(points) == numPointsInRun
            pos += pointsSize

            result.extend(points)

        # Convert relative to absolute
        absolute = []
        current = 0
        for delta in result:
            current += delta
            absolute.append(current)
        result = absolute
        del absolute

        badPoints = {str(p) for p in result if p < 0 or p >= numPoints}
        if badPoints:
            log.warning(
                "point %s out of range in '%s' table"
                % (",".join(sorted(badPoints)), tableTag)
            )
        return (result, pos)

    def compileDeltas(self, optimizeSize=True):
        deltaX = []
        deltaY = []
        if self.getCoordWidth() == 2:
            for c in self.coordinates:
                if c is None:
                    continue
                deltaX.append(c[0])
                deltaY.append(c[1])
        else:
            for c in self.coordinates:
                if c is None:
                    continue
                deltaX.append(c)
        bytearr = bytearray()
        self.compileDeltaValues_(deltaX, bytearr, optimizeSize=optimizeSize)
        self.compileDeltaValues_(deltaY, bytearr, optimizeSize=optimizeSize)
        return bytearr

    @staticmethod
    def compileDeltaValues_(deltas, bytearr=None, *, optimizeSize=True):
        """[value1, value2, value3, ...] --> bytearray

        Emits a sequence of runs. Each run starts with a
        byte-sized header whose 6 least significant bits
        (header & 0x3F) indicate how many values are encoded
        in this run. The stored length is the actual length
        minus one; run lengths are thus in the range [1..64].
        If the header byte has its most significant bit (0x80)
        set, all values in this run are zero, and no data
        follows. Otherwise, the header byte is followed by
        ((header & 0x3F) + 1) signed values.  If (header &
        0x40) is clear, the delta values are stored as signed
        bytes; if (header & 0x40) is set, the delta values are
        signed 16-bit integers.
        """  # Explaining the format because the 'gvar' spec is hard to understand.
        if bytearr is None:
            bytearr = bytearray()

        pos = 0
        numDeltas = len(deltas)

        if optimizeSize:
            while pos < numDeltas:
                value = deltas[pos]
                if value == 0:
                    pos = TupleVariation.encodeDeltaRunAsZeroes_(deltas, pos, bytearr)
                elif -128 <= value <= 127:
                    pos = TupleVariation.encodeDeltaRunAsBytes_(deltas, pos, bytearr)
                elif -32768 <= value <= 32767:
                    pos = TupleVariation.encodeDeltaRunAsWords_(deltas, pos, bytearr)
                else:
                    pos = TupleVariation.encodeDeltaRunAsLongs_(deltas, pos, bytearr)
        else:
            minVal, maxVal = min(deltas), max(deltas)
            if minVal == 0 == maxVal:
                pos = TupleVariation.encodeDeltaRunAsZeroes_(deltas, pos, bytearr)
            elif -128 <= minVal <= maxVal <= 127:
                pos = TupleVariation.encodeDeltaRunAsBytes_(
                    deltas, pos, bytearr, optimizeSize=False
                )
            elif -32768 <= minVal <= maxVal <= 32767:
                pos = TupleVariation.encodeDeltaRunAsWords_(
                    deltas, pos, bytearr, optimizeSize=False
                )
            else:
                pos = TupleVariation.encodeDeltaRunAsLongs_(
                    deltas, pos, bytearr, optimizeSize=False
                )

        assert pos == numDeltas, (pos, numDeltas)

        return bytearr

    @staticmethod
    def encodeDeltaRunAsZeroes_(deltas, offset, bytearr):
        pos = offset
        numDeltas = len(deltas)
        while pos < numDeltas and deltas[pos] == 0:
            pos += 1
        runLength = pos - offset
        while runLength >= 64:
            bytearr.append(DELTAS_ARE_ZERO | 63)
            runLength -= 64
        if runLength:
            bytearr.append(DELTAS_ARE_ZERO | (runLength - 1))
        return pos

    @staticmethod
    def encodeDeltaRunAsBytes_(deltas, offset, bytearr, optimizeSize=True):
        pos = offset
        numDeltas = len(deltas)
        while pos < numDeltas:
            value = deltas[pos]
            if not (-128 <= value <= 127):
                break
            # Within a byte-encoded run of deltas, a single zero
            # is best stored literally as 0x00 value. However,
            # if are two or more zeroes in a sequence, it is
            # better to start a new run. For example, the sequence
            # of deltas [15, 15, 0, 15, 15] becomes 6 bytes
            # (04 0F 0F 00 0F 0F) when storing the zero value
            # literally, but 7 bytes (01 0F 0F 80 01 0F 0F)
            # when starting a new run.
            if (
                optimizeSize
                and value == 0
                and pos + 1 < numDeltas
                and deltas[pos + 1] == 0
            ):
                break
            pos += 1
        runLength = pos - offset
        while runLength >= 64:
            bytearr.append(63)
            bytearr.extend(array.array("b", deltas[offset : offset + 64]))
            offset += 64
            runLength -= 64
        if runLength:
            bytearr.append(runLength - 1)
            bytearr.extend(array.array("b", deltas[offset:pos]))
        return pos

    @staticmethod
    def encodeDeltaRunAsWords_(deltas, offset, bytearr, optimizeSize=True):
        pos = offset
        numDeltas = len(deltas)
        while pos < numDeltas:
            value = deltas[pos]

            # Within a word-encoded run of deltas, it is easiest
            # to start a new run (with a different encoding)
            # whenever we encounter a zero value. For example,
            # the sequence [0x6666, 0, 0x7777] needs 7 bytes when
            # storing the zero literally (42 66 66 00 00 77 77),
            # and equally 7 bytes when starting a new run
            # (40 66 66 80 40 77 77).
            if optimizeSize and value == 0:
                break

            # Within a word-encoded run of deltas, a single value
            # in the range (-128..127) should be encoded literally
            # because it is more compact. For example, the sequence
            # [0x6666, 2, 0x7777] becomes 7 bytes when storing
            # the value literally (42 66 66 00 02 77 77), but 8 bytes
            # when starting a new run (40 66 66 00 02 40 77 77).
            if (
                optimizeSize
                and (-128 <= value <= 127)
                and pos + 1 < numDeltas
                and (-128 <= deltas[pos + 1] <= 127)
            ):
                break

            if not (-32768 <= value <= 32767):
                break

            pos += 1
        runLength = pos - offset
        while runLength >= 64:
            bytearr.append(DELTAS_ARE_WORDS | 63)
            a = array.array("h", deltas[offset : offset + 64])
            if sys.byteorder != "big":
                a.byteswap()
            bytearr.extend(a)
            offset += 64
            runLength -= 64
        if runLength:
            bytearr.append(DELTAS_ARE_WORDS | (runLength - 1))
            a = array.array("h", deltas[offset:pos])
            if sys.byteorder != "big":
                a.byteswap()
            bytearr.extend(a)
        return pos

    @staticmethod
    def encodeDeltaRunAsLongs_(deltas, offset, bytearr, optimizeSize=True):
        pos = offset
        numDeltas = len(deltas)
        while pos < numDeltas:
            value = deltas[pos]
            if optimizeSize and -32768 <= value <= 32767:
                break
            pos += 1
        runLength = pos - offset
        while runLength >= 64:
            bytearr.append(DELTAS_ARE_LONGS | 63)
            a = array.array("i", deltas[offset : offset + 64])
            if sys.byteorder != "big":
                a.byteswap()
            bytearr.extend(a)
            offset += 64
            runLength -= 64
        if runLength:
            bytearr.append(DELTAS_ARE_LONGS | (runLength - 1))
            a = array.array("i", deltas[offset:pos])
            if sys.byteorder != "big":
                a.byteswap()
            bytearr.extend(a)
        return pos

    @staticmethod
    def decompileDeltas_(numDeltas, data, offset=0):
        """(numDeltas, data, offset) --> ([delta, delta, ...], newOffset)"""
        result = []
        pos = offset
        while len(result) < numDeltas if numDeltas is not None else pos < len(data):
            runHeader = data[pos]
            pos += 1
            numDeltasInRun = (runHeader & DELTA_RUN_COUNT_MASK) + 1
            if (runHeader & DELTAS_SIZE_MASK) == DELTAS_ARE_ZERO:
                result.extend([0] * numDeltasInRun)
            else:
                if (runHeader & DELTAS_SIZE_MASK) == DELTAS_ARE_LONGS:
                    deltas = array.array("i")
                    deltasSize = numDeltasInRun * 4
                elif (runHeader & DELTAS_SIZE_MASK) == DELTAS_ARE_WORDS:
                    deltas = array.array("h")
                    deltasSize = numDeltasInRun * 2
                else:
                    deltas = array.array("b")
                    deltasSize = numDeltasInRun
                deltas.frombytes(data[pos : pos + deltasSize])
                if sys.byteorder != "big":
                    deltas.byteswap()
                assert len(deltas) == numDeltasInRun, (len(deltas), numDeltasInRun)
                pos += deltasSize
                result.extend(deltas)
        assert numDeltas is None or len(result) == numDeltas
        return (result, pos)

    @staticmethod
    def getTupleSize_(flags, axisCount):
        size = 4
        if (flags & EMBEDDED_PEAK_TUPLE) != 0:
            size += axisCount * 2
        if (flags & INTERMEDIATE_REGION) != 0:
            size += axisCount * 4
        return size

    def getCoordWidth(self):
        """Return 2 if coordinates are (x, y) as in gvar, 1 if single values
        as in cvar, or 0 if empty.
        """
        firstDelta = next((c for c in self.coordinates if c is not None), None)
        if firstDelta is None:
            return 0  # empty or has no impact
        if type(firstDelta) in (int, float):
            return 1
        if type(firstDelta) is tuple and len(firstDelta) == 2:
            return 2
        raise TypeError(
            "invalid type of delta; expected (int or float) number, or "
            "Tuple[number, number]: %r" % firstDelta
        )

    def scaleDeltas(self, scalar):
        if scalar == 1.0:
            return  # no change
        coordWidth = self.getCoordWidth()
        self.coordinates = [
            (
                None
                if d is None
                else d * scalar if coordWidth == 1 else (d[0] * scalar, d[1] * scalar)
            )
            for d in self.coordinates
        ]

    def roundDeltas(self):
        coordWidth = self.getCoordWidth()
        self.coordinates = [
            (
                None
                if d is None
                else otRound(d) if coordWidth == 1 else (otRound(d[0]), otRound(d[1]))
            )
            for d in self.coordinates
        ]

    def calcInferredDeltas(self, origCoords, endPts):
        from fontTools.varLib.iup import iup_delta

        if self.getCoordWidth() == 1:
            raise TypeError("Only 'gvar' TupleVariation can have inferred deltas")
        if None in self.coordinates:
            if len(self.coordinates) != len(origCoords):
                raise ValueError(
                    "Expected len(origCoords) == %d; found %d"
                    % (len(self.coordinates), len(origCoords))
                )
            self.coordinates = iup_delta(self.coordinates, origCoords, endPts)

    def optimize(self, origCoords, endPts, tolerance=0.5, isComposite=False):
        from fontTools.varLib.iup import iup_delta_optimize

        if None in self.coordinates:
            return  # already optimized

        deltaOpt = iup_delta_optimize(
            self.coordinates, origCoords, endPts, tolerance=tolerance
        )
        if None in deltaOpt:
            if isComposite and all(d is None for d in deltaOpt):
                # Fix for macOS composites
                # https://github.com/fonttools/fonttools/issues/1381
                deltaOpt = [(0, 0)] + [None] * (len(deltaOpt) - 1)
            # Use "optimized" version only if smaller...
            varOpt = TupleVariation(self.axes, deltaOpt)

            # Shouldn't matter that this is different from fvar...?
            axisTags = sorted(self.axes.keys())
            tupleData, auxData = self.compile(axisTags)
            unoptimizedLength = len(tupleData) + len(auxData)
            tupleData, auxData = varOpt.compile(axisTags)
            optimizedLength = len(tupleData) + len(auxData)

            if optimizedLength < unoptimizedLength:
                self.coordinates = varOpt.coordinates

    def __imul__(self, scalar):
        self.scaleDeltas(scalar)
        return self

    def __iadd__(self, other):
        if not isinstance(other, TupleVariation):
            return NotImplemented
        deltas1 = self.coordinates
        length = len(deltas1)
        deltas2 = other.coordinates
        if len(deltas2) != length:
            raise ValueError("cannot sum TupleVariation deltas with different lengths")
        # 'None' values have different meanings in gvar vs cvar TupleVariations:
        # within the gvar, when deltas are not provided explicitly for some points,
        # they need to be inferred; whereas for the 'cvar' table, if deltas are not
        # provided for some CVT values, then no adjustments are made (i.e. None == 0).
        # Thus, we cannot sum deltas for gvar TupleVariations if they contain
        # inferred inferred deltas (the latter need to be computed first using
        # 'calcInferredDeltas' method), but we can treat 'None' values in cvar
        # deltas as if they are zeros.
        if self.getCoordWidth() == 2:
            for i, d2 in zip(range(length), deltas2):
                d1 = deltas1[i]
                try:
                    deltas1[i] = (d1[0] + d2[0], d1[1] + d2[1])
                except TypeError:
                    raise ValueError("cannot sum gvar deltas with inferred points")
        else:
            for i, d2 in zip(range(length), deltas2):
                d1 = deltas1[i]
                if d1 is not None and d2 is not None:
                    deltas1[i] = d1 + d2
                elif d1 is None and d2 is not None:
                    deltas1[i] = d2
                # elif d2 is None do nothing
        return self


def decompileSharedTuples(axisTags, sharedTupleCount, data, offset):
    result = []
    for _ in range(sharedTupleCount):
        t, offset = TupleVariation.decompileCoord_(axisTags, data, offset)
        result.append(t)
    return result


def compileSharedTuples(
    axisTags, variations, MAX_NUM_SHARED_COORDS=TUPLE_INDEX_MASK + 1
):
    coordCount = Counter()
    for var in variations:
        coord = var.compileCoord(axisTags)
        coordCount[coord] += 1
    # In python < 3.7, most_common() ordering is non-deterministic
    # so apply a sort to make sure the ordering is consistent.
    sharedCoords = sorted(
        coordCount.most_common(MAX_NUM_SHARED_COORDS),
        key=lambda item: (-item[1], item[0]),
    )
    return [c[0] for c in sharedCoords if c[1] > 1]


def compileTupleVariationStore(
    variations,
    pointCount,
    axisTags,
    sharedTupleIndices,
    useSharedPoints=True,
    *,
    optimizeSize=True,
):
    # pointCount is actually unused. Keeping for API compat.
    del pointCount
    newVariations = []
    pointDatas = []
    # Compile all points and figure out sharing if desired
    sharedPoints = None

    # Collect, count, and compile point-sets for all variation sets
    pointSetCount = defaultdict(int)
    for v in variations:
        points = v.getUsedPoints()
        if points is None:  # Empty variations
            continue
        pointSetCount[points] += 1
        newVariations.append(v)
        pointDatas.append(points)
    variations = newVariations
    del newVariations

    if not variations:
        return (0, b"", b"")

    n = len(variations[0].coordinates)
    assert all(
        len(v.coordinates) == n for v in variations
    ), "Variation sets have different sizes"

    compiledPoints = {
        pointSet: TupleVariation.compilePoints(pointSet) for pointSet in pointSetCount
    }

    tupleVariationCount = len(variations)
    tuples = []
    data = []

    if useSharedPoints:
        # Find point-set which saves most bytes.
        def key(pn):
            pointSet = pn[0]
            count = pn[1]
            return len(compiledPoints[pointSet]) * (count - 1)

        sharedPoints = max(pointSetCount.items(), key=key)[0]

        data.append(compiledPoints[sharedPoints])
        tupleVariationCount |= TUPLES_SHARE_POINT_NUMBERS

    # b'' implies "use shared points"
    pointDatas = [
        compiledPoints[points] if points != sharedPoints else b""
        for points in pointDatas
    ]

    for v, p in zip(variations, pointDatas):
        thisTuple, thisData = v.compile(
            axisTags, sharedTupleIndices, pointData=p, optimizeSize=optimizeSize
        )

        tuples.append(thisTuple)
        data.append(thisData)

    tuples = b"".join(tuples)
    data = b"".join(data)
    return tupleVariationCount, tuples, data


def decompileTupleVariationStore(
    tableTag,
    axisTags,
    tupleVariationCount,
    pointCount,
    sharedTuples,
    data,
    pos,
    dataPos,
):
    numAxes = len(axisTags)
    result = []
    if (tupleVariationCount & TUPLES_SHARE_POINT_NUMBERS) != 0:
        sharedPoints, dataPos = TupleVariation.decompilePoints_(
            pointCount, data, dataPos, tableTag
        )
    else:
        sharedPoints = []
    for _ in range(tupleVariationCount & TUPLE_COUNT_MASK):
        dataSize, flags = struct.unpack(">HH", data[pos : pos + 4])
        tupleSize = TupleVariation.getTupleSize_(flags, numAxes)
        tupleData = data[pos : pos + tupleSize]
        pointDeltaData = data[dataPos : dataPos + dataSize]
        result.append(
            decompileTupleVariation_(
                pointCount,
                sharedTuples,
                sharedPoints,
                tableTag,
                axisTags,
                tupleData,
                pointDeltaData,
            )
        )
        pos += tupleSize
        dataPos += dataSize
    return result


def decompileTupleVariation_(
    pointCount, sharedTuples, sharedPoints, tableTag, axisTags, data, tupleData
):
    assert tableTag in ("cvar", "gvar"), tableTag
    flags = struct.unpack(">H", data[2:4])[0]
    pos = 4
    if (flags & EMBEDDED_PEAK_TUPLE) == 0:
        peak = sharedTuples[flags & TUPLE_INDEX_MASK]
    else:
        peak, pos = TupleVariation.decompileCoord_(axisTags, data, pos)
    if (flags & INTERMEDIATE_REGION) != 0:
        start, pos = TupleVariation.decompileCoord_(axisTags, data, pos)
        end, pos = TupleVariation.decompileCoord_(axisTags, data, pos)
    else:
        start, end = inferRegion_(peak)
    axes = {}
    for axis in axisTags:
        region = start[axis], peak[axis], end[axis]
        if region != (0.0, 0.0, 0.0):
            axes[axis] = region
    pos = 0
    if (flags & PRIVATE_POINT_NUMBERS) != 0:
        points, pos = TupleVariation.decompilePoints_(
            pointCount, tupleData, pos, tableTag
        )
    else:
        points = sharedPoints

    deltas = [None] * pointCount

    if tableTag == "cvar":
        deltas_cvt, pos = TupleVariation.decompileDeltas_(len(points), tupleData, pos)
        for p, delta in zip(points, deltas_cvt):
            if 0 <= p < pointCount:
                deltas[p] = delta

    elif tableTag == "gvar":
        deltas_x, pos = TupleVariation.decompileDeltas_(len(points), tupleData, pos)
        deltas_y, pos = TupleVariation.decompileDeltas_(len(points), tupleData, pos)
        for p, x, y in zip(points, deltas_x, deltas_y):
            if 0 <= p < pointCount:
                deltas[p] = (x, y)

    return TupleVariation(axes, deltas)


def inferRegion_(peak):
    """Infer start and end for a (non-intermediate) region

    This helper function computes the applicability region for
    variation tuples whose INTERMEDIATE_REGION flag is not set in the
    TupleVariationHeader structure.  Variation tuples apply only to
    certain regions of the variation space; outside that region, the
    tuple has no effect.  To make the binary encoding more compact,
    TupleVariationHeaders can omit the intermediateStartTuple and
    intermediateEndTuple fields.
    """
    start, end = {}, {}
    for axis, value in peak.items():
        start[axis] = min(value, 0.0)  # -0.3 --> -0.3; 0.7 --> 0.0
        end[axis] = max(value, 0.0)  # -0.3 -->  0.0; 0.7 --> 0.7
    return (start, end)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\anthropic\chat\handler.py ===
"""
Calling + translation logic for anthropic's `/v1/messages` endpoint
"""

import copy
import json
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
    cast,
)

import httpx  # type: ignore

import litellm
import litellm.litellm_core_utils
import litellm.types
import litellm.types.utils
from litellm.litellm_core_utils.core_helpers import map_finish_reason
from litellm.llms.custom_httpx.http_handler import (
    AsyncHTTPHandler,
    HTTPHandler,
    get_async_httpx_client,
)
from litellm.types.llms.anthropic import (
    ContentBlockDelta,
    ContentBlockStart,
    ContentBlockStop,
    MessageBlockDelta,
    MessageStartBlock,
    UsageDelta,
)
from litellm.types.llms.openai import (
    ChatCompletionRedactedThinkingBlock,
    ChatCompletionThinkingBlock,
    ChatCompletionToolCallChunk,
)
from litellm.types.utils import (
    Delta,
    GenericStreamingChunk,
    LlmProviders,
    ModelResponse,
    ModelResponseStream,
    StreamingChoices,
    Usage,
)

from ...base import BaseLLM
from ..common_utils import AnthropicError, process_anthropic_headers
from .transformation import AnthropicConfig

if TYPE_CHECKING:
    from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper
    from litellm.llms.base_llm.chat.transformation import BaseConfig


async def make_call(
    client: Optional[AsyncHTTPHandler],
    api_base: str,
    headers: dict,
    data: str,
    model: str,
    messages: list,
    logging_obj,
    timeout: Optional[Union[float, httpx.Timeout]],
    json_mode: bool,
) -> Tuple[Any, httpx.Headers]:
    if client is None:
        client = litellm.module_level_aclient

    try:
        response = await client.post(
            api_base, headers=headers, data=data, stream=True, timeout=timeout
        )
    except httpx.HTTPStatusError as e:
        error_headers = getattr(e, "headers", None)
        error_response = getattr(e, "response", None)
        if error_headers is None and error_response:
            error_headers = getattr(error_response, "headers", None)
        raise AnthropicError(
            status_code=e.response.status_code,
            message=await e.response.aread(),
            headers=error_headers,
        )
    except Exception as e:
        for exception in litellm.LITELLM_EXCEPTION_TYPES:
            if isinstance(e, exception):
                raise e
        raise AnthropicError(status_code=500, message=str(e))

    completion_stream = ModelResponseIterator(
        streaming_response=response.aiter_lines(),
        sync_stream=False,
        json_mode=json_mode,
    )

    # LOGGING
    logging_obj.post_call(
        input=messages,
        api_key="",
        original_response=completion_stream,  # Pass the completion stream for logging
        additional_args={"complete_input_dict": data},
    )

    return completion_stream, response.headers


def make_sync_call(
    client: Optional[HTTPHandler],
    api_base: str,
    headers: dict,
    data: str,
    model: str,
    messages: list,
    logging_obj,
    timeout: Optional[Union[float, httpx.Timeout]],
    json_mode: bool,
) -> Tuple[Any, httpx.Headers]:
    if client is None:
        client = litellm.module_level_client  # re-use a module level client

    try:
        response = client.post(
            api_base, headers=headers, data=data, stream=True, timeout=timeout
        )
    except httpx.HTTPStatusError as e:
        error_headers = getattr(e, "headers", None)
        error_response = getattr(e, "response", None)
        if error_headers is None and error_response:
            error_headers = getattr(error_response, "headers", None)
        raise AnthropicError(
            status_code=e.response.status_code,
            message=e.response.read(),
            headers=error_headers,
        )
    except Exception as e:
        for exception in litellm.LITELLM_EXCEPTION_TYPES:
            if isinstance(e, exception):
                raise e
        raise AnthropicError(status_code=500, message=str(e))

    if response.status_code != 200:
        response_headers = getattr(response, "headers", None)
        raise AnthropicError(
            status_code=response.status_code,
            message=response.read(),
            headers=response_headers,
        )

    completion_stream = ModelResponseIterator(
        streaming_response=response.iter_lines(), sync_stream=True, json_mode=json_mode
    )

    # LOGGING
    logging_obj.post_call(
        input=messages,
        api_key="",
        original_response="first stream response received",
        additional_args={"complete_input_dict": data},
    )

    return completion_stream, response.headers


class AnthropicChatCompletion(BaseLLM):
    def __init__(self) -> None:
        super().__init__()

    async def acompletion_stream_function(
        self,
        model: str,
        messages: list,
        api_base: str,
        custom_prompt_dict: dict,
        model_response: ModelResponse,
        print_verbose: Callable,
        timeout: Union[float, httpx.Timeout],
        client: Optional[AsyncHTTPHandler],
        encoding,
        api_key,
        logging_obj,
        stream,
        _is_function_call,
        data: dict,
        json_mode: bool,
        optional_params=None,
        litellm_params=None,
        logger_fn=None,
        headers={},
    ):
        from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper

        data["stream"] = True

        completion_stream, headers = await make_call(
            client=client,
            api_base=api_base,
            headers=headers,
            data=json.dumps(data),
            model=model,
            messages=messages,
            logging_obj=logging_obj,
            timeout=timeout,
            json_mode=json_mode,
        )
        streamwrapper = CustomStreamWrapper(
            completion_stream=completion_stream,
            model=model,
            custom_llm_provider="anthropic",
            logging_obj=logging_obj,
            _response_headers=process_anthropic_headers(headers),
        )
        return streamwrapper

    async def acompletion_function(
        self,
        model: str,
        messages: list,
        api_base: str,
        custom_prompt_dict: dict,
        model_response: ModelResponse,
        print_verbose: Callable,
        timeout: Union[float, httpx.Timeout],
        encoding,
        api_key,
        logging_obj,
        stream,
        _is_function_call,
        data: dict,
        optional_params: dict,
        json_mode: bool,
        litellm_params: dict,
        provider_config: "BaseConfig",
        logger_fn=None,
        headers={},
        client: Optional[AsyncHTTPHandler] = None,
    ) -> Union[ModelResponse, "CustomStreamWrapper"]:
        async_handler = client or get_async_httpx_client(
            llm_provider=litellm.LlmProviders.ANTHROPIC
        )

        try:
            response = await async_handler.post(
                api_base, headers=headers, json=data, timeout=timeout
            )
        except Exception as e:
            ## LOGGING
            logging_obj.post_call(
                input=messages,
                api_key=api_key,
                original_response=str(e),
                additional_args={"complete_input_dict": data},
            )
            status_code = getattr(e, "status_code", 500)
            error_headers = getattr(e, "headers", None)
            error_text = getattr(e, "text", str(e))
            error_response = getattr(e, "response", None)
            if error_headers is None and error_response:
                error_headers = getattr(error_response, "headers", None)
            if error_response and hasattr(error_response, "text"):
                error_text = getattr(error_response, "text", error_text)
            raise AnthropicError(
                message=error_text,
                status_code=status_code,
                headers=error_headers,
            )

        return provider_config.transform_response(
            model=model,
            raw_response=response,
            model_response=model_response,
            logging_obj=logging_obj,
            api_key=api_key,
            request_data=data,
            messages=messages,
            optional_params=optional_params,
            litellm_params=litellm_params,
            encoding=encoding,
            json_mode=json_mode,
        )

    def completion(
        self,
        model: str,
        messages: list,
        api_base: str,
        custom_llm_provider: str,
        custom_prompt_dict: dict,
        model_response: ModelResponse,
        print_verbose: Callable,
        encoding,
        api_key,
        logging_obj,
        optional_params: dict,
        timeout: Union[float, httpx.Timeout],
        litellm_params: dict,
        acompletion=None,
        logger_fn=None,
        headers={},
        client=None,
    ):
        from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper
        from litellm.utils import ProviderConfigManager

        optional_params = copy.deepcopy(optional_params)
        stream = optional_params.pop("stream", None)
        json_mode: bool = optional_params.pop("json_mode", False)
        is_vertex_request: bool = optional_params.pop("is_vertex_request", False)
        _is_function_call = False
        messages = copy.deepcopy(messages)
        headers = AnthropicConfig().validate_environment(
            api_key=api_key,
            headers=headers,
            model=model,
            messages=messages,
            optional_params={**optional_params, "is_vertex_request": is_vertex_request},
            litellm_params=litellm_params,
        )

        config = ProviderConfigManager.get_provider_chat_config(
            model=model,
            provider=LlmProviders(custom_llm_provider),
        )
        if config is None:
            raise ValueError(
                f"Provider config not found for model: {model} and provider: {custom_llm_provider}"
            )

        data = config.transform_request(
            model=model,
            messages=messages,
            optional_params=optional_params,
            litellm_params=litellm_params,
            headers=headers,
        )

        ## LOGGING
        logging_obj.pre_call(
            input=messages,
            api_key=api_key,
            additional_args={
                "complete_input_dict": data,
                "api_base": api_base,
                "headers": headers,
            },
        )
        print_verbose(f"_is_function_call: {_is_function_call}")
        if acompletion is True:
            if (
                stream is True
            ):  # if function call - fake the streaming (need complete blocks for output parsing in openai format)
                print_verbose("makes async anthropic streaming POST request")
                data["stream"] = stream
                return self.acompletion_stream_function(
                    model=model,
                    messages=messages,
                    data=data,
                    api_base=api_base,
                    custom_prompt_dict=custom_prompt_dict,
                    model_response=model_response,
                    print_verbose=print_verbose,
                    encoding=encoding,
                    api_key=api_key,
                    logging_obj=logging_obj,
                    optional_params=optional_params,
                    stream=stream,
                    _is_function_call=_is_function_call,
                    json_mode=json_mode,
                    litellm_params=litellm_params,
                    logger_fn=logger_fn,
                    headers=headers,
                    timeout=timeout,
                    client=(
                        client
                        if client is not None and isinstance(client, AsyncHTTPHandler)
                        else None
                    ),
                )
            else:
                return self.acompletion_function(
                    model=model,
                    messages=messages,
                    data=data,
                    api_base=api_base,
                    custom_prompt_dict=custom_prompt_dict,
                    model_response=model_response,
                    print_verbose=print_verbose,
                    encoding=encoding,
                    api_key=api_key,
                    provider_config=config,
                    logging_obj=logging_obj,
                    optional_params=optional_params,
                    stream=stream,
                    _is_function_call=_is_function_call,
                    litellm_params=litellm_params,
                    logger_fn=logger_fn,
                    headers=headers,
                    client=client,
                    json_mode=json_mode,
                    timeout=timeout,
                )
        else:
            ## COMPLETION CALL
            if (
                stream is True
            ):  # if function call - fake the streaming (need complete blocks for output parsing in openai format)
                data["stream"] = stream
                completion_stream, headers = make_sync_call(
                    client=client,
                    api_base=api_base,
                    headers=headers,  # type: ignore
                    data=json.dumps(data),
                    model=model,
                    messages=messages,
                    logging_obj=logging_obj,
                    timeout=timeout,
                    json_mode=json_mode,
                )
                return CustomStreamWrapper(
                    completion_stream=completion_stream,
                    model=model,
                    custom_llm_provider="anthropic",
                    logging_obj=logging_obj,
                    _response_headers=process_anthropic_headers(headers),
                )

            else:
                if client is None or not isinstance(client, HTTPHandler):
                    client = HTTPHandler(timeout=timeout)  # type: ignore
                else:
                    client = client

                try:
                    response = client.post(
                        api_base,
                        headers=headers,
                        data=json.dumps(data),
                        timeout=timeout,
                    )
                except Exception as e:
                    status_code = getattr(e, "status_code", 500)
                    error_headers = getattr(e, "headers", None)
                    error_text = getattr(e, "text", str(e))
                    error_response = getattr(e, "response", None)
                    if error_headers is None and error_response:
                        error_headers = getattr(error_response, "headers", None)
                    if error_response and hasattr(error_response, "text"):
                        error_text = getattr(error_response, "text", error_text)
                    raise AnthropicError(
                        message=error_text,
                        status_code=status_code,
                        headers=error_headers,
                    )

        return config.transform_response(
            model=model,
            raw_response=response,
            model_response=model_response,
            logging_obj=logging_obj,
            api_key=api_key,
            request_data=data,
            messages=messages,
            optional_params=optional_params,
            litellm_params=litellm_params,
            encoding=encoding,
            json_mode=json_mode,
        )

    def embedding(self):
        # logic for parsing in - calling - parsing out model embedding calls
        pass


class ModelResponseIterator:
    def __init__(
        self, streaming_response, sync_stream: bool, json_mode: Optional[bool] = False
    ):
        self.streaming_response = streaming_response
        self.response_iterator = self.streaming_response
        self.content_blocks: List[ContentBlockDelta] = []
        self.tool_index = -1
        self.json_mode = json_mode

    def check_empty_tool_call_args(self) -> bool:
        """
        Check if the tool call block so far has been an empty string
        """
        args = ""
        # if text content block -> skip
        if len(self.content_blocks) == 0:
            return False

        if (
            self.content_blocks[0]["delta"]["type"] == "text_delta"
            or self.content_blocks[0]["delta"]["type"] == "thinking_delta"
        ):
            return False

        for block in self.content_blocks:
            if block["delta"]["type"] == "input_json_delta":
                args += block["delta"].get("partial_json", "")  # type: ignore

        if len(args) == 0:
            return True
        return False

    def _handle_usage(self, anthropic_usage_chunk: Union[dict, UsageDelta]) -> Usage:
        return AnthropicConfig().calculate_usage(
            usage_object=cast(dict, anthropic_usage_chunk), reasoning_content=None
        )

    def _content_block_delta_helper(
        self, chunk: dict
    ) -> Tuple[
        str,
        Optional[ChatCompletionToolCallChunk],
        List[Union[ChatCompletionThinkingBlock, ChatCompletionRedactedThinkingBlock]],
        Dict[str, Any],
    ]:
        """
        Helper function to handle the content block delta
        """
        text = ""
        tool_use: Optional[ChatCompletionToolCallChunk] = None
        provider_specific_fields = {}
        content_block = ContentBlockDelta(**chunk)  # type: ignore
        thinking_blocks: List[
            Union[ChatCompletionThinkingBlock, ChatCompletionRedactedThinkingBlock]
        ] = []

        self.content_blocks.append(content_block)
        if "text" in content_block["delta"]:
            text = content_block["delta"]["text"]
        elif "partial_json" in content_block["delta"]:
            tool_use = {
                "id": None,
                "type": "function",
                "function": {
                    "name": None,
                    "arguments": content_block["delta"]["partial_json"],
                },
                "index": self.tool_index,
            }
        elif "citation" in content_block["delta"]:
            provider_specific_fields["citation"] = content_block["delta"]["citation"]
        elif (
            "thinking" in content_block["delta"]
            or "signature" in content_block["delta"]
        ):
            thinking_blocks = [
                ChatCompletionThinkingBlock(
                    type="thinking",
                    thinking=content_block["delta"].get("thinking") or "",
                    signature=content_block["delta"].get("signature"),
                )
            ]
            provider_specific_fields["thinking_blocks"] = thinking_blocks

        return text, tool_use, thinking_blocks, provider_specific_fields

    def _handle_reasoning_content(
        self,
        thinking_blocks: List[
            Union[ChatCompletionThinkingBlock, ChatCompletionRedactedThinkingBlock]
        ],
    ) -> Optional[str]:
        """
        Handle the reasoning content
        """
        reasoning_content = None
        for block in thinking_blocks:
            thinking_content = cast(Optional[str], block.get("thinking"))
            if reasoning_content is None:
                reasoning_content = ""
            if thinking_content is not None:
                reasoning_content += thinking_content
        return reasoning_content

    def _handle_redacted_thinking_content(
        self,
        content_block_start: ContentBlockStart,
        provider_specific_fields: Dict[str, Any],
    ) -> Tuple[List[ChatCompletionRedactedThinkingBlock], Dict[str, Any]]:
        """
        Handle the redacted thinking content
        """
        thinking_blocks = [
            ChatCompletionRedactedThinkingBlock(
                type="redacted_thinking",
                data=content_block_start["content_block"]["data"],  # type: ignore
            )
        ]
        provider_specific_fields["thinking_blocks"] = thinking_blocks

        return thinking_blocks, provider_specific_fields

    def chunk_parser(self, chunk: dict) -> ModelResponseStream:
        try:
            type_chunk = chunk.get("type", "") or ""

            text = ""
            tool_use: Optional[ChatCompletionToolCallChunk] = None
            finish_reason = ""
            usage: Optional[Usage] = None
            provider_specific_fields: Dict[str, Any] = {}
            reasoning_content: Optional[str] = None
            thinking_blocks: Optional[
                List[
                    Union[
                        ChatCompletionThinkingBlock, ChatCompletionRedactedThinkingBlock
                    ]
                ]
            ] = None

            index = int(chunk.get("index", 0))
            if type_chunk == "content_block_delta":
                """
                Anthropic content chunk
                chunk = {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': 'Hello'}}
                """
                (
                    text,
                    tool_use,
                    thinking_blocks,
                    provider_specific_fields,
                ) = self._content_block_delta_helper(chunk=chunk)
                if thinking_blocks:
                    reasoning_content = self._handle_reasoning_content(
                        thinking_blocks=thinking_blocks
                    )
            elif type_chunk == "content_block_start":
                """
                event: content_block_start
                data: {"type":"content_block_start","index":1,"content_block":{"type":"tool_use","id":"toolu_01T1x1fJ34qAmk2tNTrN7Up6","name":"get_weather","input":{}}}
                """
                content_block_start = ContentBlockStart(**chunk)  # type: ignore
                self.content_blocks = []  # reset content blocks when new block starts
                if content_block_start["content_block"]["type"] == "text":
                    text = content_block_start["content_block"]["text"]
                elif content_block_start["content_block"]["type"] == "tool_use":
                    self.tool_index += 1
                    tool_use = {
                        "id": content_block_start["content_block"]["id"],
                        "type": "function",
                        "function": {
                            "name": content_block_start["content_block"]["name"],
                            "arguments": "",
                        },
                        "index": self.tool_index,
                    }
                elif (
                    content_block_start["content_block"]["type"] == "redacted_thinking"
                ):
                    (
                        thinking_blocks,
                        provider_specific_fields,
                    ) = self._handle_redacted_thinking_content(  # type: ignore
                        content_block_start=content_block_start,
                        provider_specific_fields=provider_specific_fields,
                    )
            elif type_chunk == "content_block_stop":
                ContentBlockStop(**chunk)  # type: ignore
                # check if tool call content block
                is_empty = self.check_empty_tool_call_args()

                if is_empty:
                    tool_use = {
                        "id": None,
                        "type": "function",
                        "function": {
                            "name": None,
                            "arguments": "{}",
                        },
                        "index": self.tool_index,
                    }
            elif type_chunk == "message_delta":
                """
                Anthropic
                chunk = {'type': 'message_delta', 'delta': {'stop_reason': 'max_tokens', 'stop_sequence': None}, 'usage': {'output_tokens': 10}}
                """
                # TODO - get usage from this chunk, set in response
                message_delta = MessageBlockDelta(**chunk)  # type: ignore
                finish_reason = map_finish_reason(
                    finish_reason=message_delta["delta"].get("stop_reason", "stop")
                    or "stop"
                )
                usage = self._handle_usage(anthropic_usage_chunk=message_delta["usage"])
            elif type_chunk == "message_start":
                """
                Anthropic
                chunk = {
                    "type": "message_start",
                    "message": {
                        "id": "msg_vrtx_011PqREFEMzd3REdCoUFAmdG",
                        "type": "message",
                        "role": "assistant",
                        "model": "claude-3-sonnet-20240229",
                        "content": [],
                        "stop_reason": null,
                        "stop_sequence": null,
                        "usage": {
                            "input_tokens": 270,
                            "output_tokens": 1
                        }
                    }
                }
                """
                message_start_block = MessageStartBlock(**chunk)  # type: ignore
                if "usage" in message_start_block["message"]:
                    usage = self._handle_usage(
                        anthropic_usage_chunk=message_start_block["message"]["usage"]
                    )
            elif type_chunk == "error":
                """
                {"type":"error","error":{"details":null,"type":"api_error","message":"Internal server error"}      }
                """
                _error_dict = chunk.get("error", {}) or {}
                message = _error_dict.get("message", None) or str(chunk)
                raise AnthropicError(
                    message=message,
                    status_code=500,  # it looks like Anthropic API does not return a status code in the chunk error - default to 500
                )

            text, tool_use = self._handle_json_mode_chunk(text=text, tool_use=tool_use)

            returned_chunk = ModelResponseStream(
                choices=[
                    StreamingChoices(
                        index=index,
                        delta=Delta(
                            content=text,
                            tool_calls=[tool_use] if tool_use is not None else None,
                            provider_specific_fields=(
                                provider_specific_fields
                                if provider_specific_fields
                                else None
                            ),
                            thinking_blocks=(
                                thinking_blocks if thinking_blocks else None
                            ),
                            reasoning_content=reasoning_content,
                        ),
                        finish_reason=finish_reason,
                    )
                ],
                usage=usage,
            )

            return returned_chunk

        except json.JSONDecodeError:
            raise ValueError(f"Failed to decode JSON from chunk: {chunk}")

    def _handle_json_mode_chunk(
        self, text: str, tool_use: Optional[ChatCompletionToolCallChunk]
    ) -> Tuple[str, Optional[ChatCompletionToolCallChunk]]:
        """
        If JSON mode is enabled, convert the tool call to a message.

        Anthropic returns the JSON schema as part of the tool call
        OpenAI returns the JSON schema as part of the content, this handles placing it in the content

        Args:
            text: str
            tool_use: Optional[ChatCompletionToolCallChunk]
        Returns:
            Tuple[str, Optional[ChatCompletionToolCallChunk]]

            text: The text to use in the content
            tool_use: The ChatCompletionToolCallChunk to use in the chunk response
        """
        if self.json_mode is True and tool_use is not None:
            message = AnthropicConfig._convert_tool_response_to_message(
                tool_calls=[tool_use]
            )
            if message is not None:
                text = message.content or ""
                tool_use = None

        return text, tool_use

    # Sync iterator
    def __iter__(self):
        return self

    def __next__(self):
        try:
            chunk = self.response_iterator.__next__()
        except StopIteration:
            raise StopIteration
        except ValueError as e:
            raise RuntimeError(f"Error receiving chunk from stream: {e}")

        try:
            str_line = chunk
            if isinstance(chunk, bytes):  # Handle binary data
                str_line = chunk.decode("utf-8")  # Convert bytes to string
                index = str_line.find("data:")
                if index != -1:
                    str_line = str_line[index:]

            if str_line.startswith("data:"):
                data_json = json.loads(str_line[5:])
                return self.chunk_parser(chunk=data_json)
            else:
                return GenericStreamingChunk(
                    text="",
                    is_finished=False,
                    finish_reason="",
                    usage=None,
                    index=0,
                    tool_use=None,
                )
        except StopIteration:
            raise StopIteration
        except ValueError as e:
            raise RuntimeError(f"Error parsing chunk: {e},\nReceived chunk: {chunk}")

    # Async iterator
    def __aiter__(self):
        self.async_response_iterator = self.streaming_response.__aiter__()
        return self

    async def __anext__(self):
        try:
            chunk = await self.async_response_iterator.__anext__()
        except StopAsyncIteration:
            raise StopAsyncIteration
        except ValueError as e:
            raise RuntimeError(f"Error receiving chunk from stream: {e}")

        try:
            str_line = chunk
            if isinstance(chunk, bytes):  # Handle binary data
                str_line = chunk.decode("utf-8")  # Convert bytes to string
                index = str_line.find("data:")
                if index != -1:
                    str_line = str_line[index:]

            if str_line.startswith("data:"):
                data_json = json.loads(str_line[5:])
                return self.chunk_parser(chunk=data_json)
            else:
                return GenericStreamingChunk(
                    text="",
                    is_finished=False,
                    finish_reason="",
                    usage=None,
                    index=0,
                    tool_use=None,
                )
        except StopAsyncIteration:
            raise StopAsyncIteration
        except ValueError as e:
            raise RuntimeError(f"Error parsing chunk: {e},\nReceived chunk: {chunk}")

    def convert_str_chunk_to_generic_chunk(self, chunk: str) -> ModelResponseStream:
        """
        Convert a string chunk to a GenericStreamingChunk

        Note: This is used for Anthropic pass through streaming logging

        We can move __anext__, and __next__ to use this function since it's common logic.
        Did not migrate them to minmize changes made in 1 PR.
        """
        str_line = chunk
        if isinstance(chunk, bytes):  # Handle binary data
            str_line = chunk.decode("utf-8")  # Convert bytes to string
            index = str_line.find("data:")
            if index != -1:
                str_line = str_line[index:]

        if str_line.startswith("data:"):
            data_json = json.loads(str_line[5:])
            return self.chunk_parser(chunk=data_json)
        else:
            return ModelResponseStream()

# === NexusCore/openenv\Lib\site-packages\fsspec\implementations\http.py ===
import asyncio
import io
import logging
import re
import weakref
from copy import copy
from urllib.parse import urlparse

import aiohttp
import yarl

from fsspec.asyn import AbstractAsyncStreamedFile, AsyncFileSystem, sync, sync_wrapper
from fsspec.callbacks import DEFAULT_CALLBACK
from fsspec.exceptions import FSTimeoutError
from fsspec.spec import AbstractBufferedFile
from fsspec.utils import (
    DEFAULT_BLOCK_SIZE,
    glob_translate,
    isfilelike,
    nullcontext,
    tokenize,
)

from ..caching import AllBytes

# https://stackoverflow.com/a/15926317/3821154
ex = re.compile(r"""<(a|A)\s+(?:[^>]*?\s+)?(href|HREF)=["'](?P<url>[^"']+)""")
ex2 = re.compile(r"""(?P<url>http[s]?://[-a-zA-Z0-9@:%_+.~#?&/=]+)""")
logger = logging.getLogger("fsspec.http")


async def get_client(**kwargs):
    return aiohttp.ClientSession(**kwargs)


class HTTPFileSystem(AsyncFileSystem):
    """
    Simple File-System for fetching data via HTTP(S)

    ``ls()`` is implemented by loading the parent page and doing a regex
    match on the result. If simple_link=True, anything of the form
    "http(s)://server.com/stuff?thing=other"; otherwise only links within
    HTML href tags will be used.
    """

    sep = "/"

    def __init__(
        self,
        simple_links=True,
        block_size=None,
        same_scheme=True,
        size_policy=None,
        cache_type="bytes",
        cache_options=None,
        asynchronous=False,
        loop=None,
        client_kwargs=None,
        get_client=get_client,
        encoded=False,
        **storage_options,
    ):
        """
        NB: if this is called async, you must await set_client

        Parameters
        ----------
        block_size: int
            Blocks to read bytes; if 0, will default to raw requests file-like
            objects instead of HTTPFile instances
        simple_links: bool
            If True, will consider both HTML <a> tags and anything that looks
            like a URL; if False, will consider only the former.
        same_scheme: True
            When doing ls/glob, if this is True, only consider paths that have
            http/https matching the input URLs.
        size_policy: this argument is deprecated
        client_kwargs: dict
            Passed to aiohttp.ClientSession, see
            https://docs.aiohttp.org/en/stable/client_reference.html
            For example, ``{'auth': aiohttp.BasicAuth('user', 'pass')}``
        get_client: Callable[..., aiohttp.ClientSession]
            A callable which takes keyword arguments and constructs
            an aiohttp.ClientSession. It's state will be managed by
            the HTTPFileSystem class.
        storage_options: key-value
            Any other parameters passed on to requests
        cache_type, cache_options: defaults used in open
        """
        super().__init__(self, asynchronous=asynchronous, loop=loop, **storage_options)
        self.block_size = block_size if block_size is not None else DEFAULT_BLOCK_SIZE
        self.simple_links = simple_links
        self.same_schema = same_scheme
        self.cache_type = cache_type
        self.cache_options = cache_options
        self.client_kwargs = client_kwargs or {}
        self.get_client = get_client
        self.encoded = encoded
        self.kwargs = storage_options
        self._session = None

        # Clean caching-related parameters from `storage_options`
        # before propagating them as `request_options` through `self.kwargs`.
        # TODO: Maybe rename `self.kwargs` to `self.request_options` to make
        #       it clearer.
        request_options = copy(storage_options)
        self.use_listings_cache = request_options.pop("use_listings_cache", False)
        request_options.pop("listings_expiry_time", None)
        request_options.pop("max_paths", None)
        request_options.pop("skip_instance_cache", None)
        self.kwargs = request_options

    @property
    def fsid(self):
        return "http"

    def encode_url(self, url):
        return yarl.URL(url, encoded=self.encoded)

    @staticmethod
    def close_session(loop, session):
        if loop is not None and loop.is_running():
            try:
                sync(loop, session.close, timeout=0.1)
                return
            except (TimeoutError, FSTimeoutError, NotImplementedError):
                pass
        connector = getattr(session, "_connector", None)
        if connector is not None:
            # close after loop is dead
            connector._close()

    async def set_session(self):
        if self._session is None:
            self._session = await self.get_client(loop=self.loop, **self.client_kwargs)
            if not self.asynchronous:
                weakref.finalize(self, self.close_session, self.loop, self._session)
        return self._session

    @classmethod
    def _strip_protocol(cls, path):
        """For HTTP, we always want to keep the full URL"""
        return path

    @classmethod
    def _parent(cls, path):
        # override, since _strip_protocol is different for URLs
        par = super()._parent(path)
        if len(par) > 7:  # "http://..."
            return par
        return ""

    async def _ls_real(self, url, detail=True, **kwargs):
        # ignoring URL-encoded arguments
        kw = self.kwargs.copy()
        kw.update(kwargs)
        logger.debug(url)
        session = await self.set_session()
        async with session.get(self.encode_url(url), **self.kwargs) as r:
            self._raise_not_found_for_status(r, url)
            try:
                text = await r.text()
                if self.simple_links:
                    links = ex2.findall(text) + [u[2] for u in ex.findall(text)]
                else:
                    links = [u[2] for u in ex.findall(text)]
            except UnicodeDecodeError:
                links = []  # binary, not HTML
        out = set()
        parts = urlparse(url)
        for l in links:
            if isinstance(l, tuple):
                l = l[1]
            if l.startswith("/") and len(l) > 1:
                # absolute URL on this server
                l = f"{parts.scheme}://{parts.netloc}{l}"
            if l.startswith("http"):
                if self.same_schema and l.startswith(url.rstrip("/") + "/"):
                    out.add(l)
                elif l.replace("https", "http").startswith(
                    url.replace("https", "http").rstrip("/") + "/"
                ):
                    # allowed to cross http <-> https
                    out.add(l)
            else:
                if l not in ["..", "../"]:
                    # Ignore FTP-like "parent"
                    out.add("/".join([url.rstrip("/"), l.lstrip("/")]))
        if not out and url.endswith("/"):
            out = await self._ls_real(url.rstrip("/"), detail=False)
        if detail:
            return [
                {
                    "name": u,
                    "size": None,
                    "type": "directory" if u.endswith("/") else "file",
                }
                for u in out
            ]
        else:
            return sorted(out)

    async def _ls(self, url, detail=True, **kwargs):
        if self.use_listings_cache and url in self.dircache:
            out = self.dircache[url]
        else:
            out = await self._ls_real(url, detail=detail, **kwargs)
            self.dircache[url] = out
        return out

    ls = sync_wrapper(_ls)

    def _raise_not_found_for_status(self, response, url):
        """
        Raises FileNotFoundError for 404s, otherwise uses raise_for_status.
        """
        if response.status == 404:
            raise FileNotFoundError(url)
        response.raise_for_status()

    async def _cat_file(self, url, start=None, end=None, **kwargs):
        kw = self.kwargs.copy()
        kw.update(kwargs)
        logger.debug(url)

        if start is not None or end is not None:
            if start == end:
                return b""
            headers = kw.pop("headers", {}).copy()

            headers["Range"] = await self._process_limits(url, start, end)
            kw["headers"] = headers
        session = await self.set_session()
        async with session.get(self.encode_url(url), **kw) as r:
            out = await r.read()
            self._raise_not_found_for_status(r, url)
        return out

    async def _get_file(
        self, rpath, lpath, chunk_size=5 * 2**20, callback=DEFAULT_CALLBACK, **kwargs
    ):
        kw = self.kwargs.copy()
        kw.update(kwargs)
        logger.debug(rpath)
        session = await self.set_session()
        async with session.get(self.encode_url(rpath), **kw) as r:
            try:
                size = int(r.headers["content-length"])
            except (ValueError, KeyError):
                size = None

            callback.set_size(size)
            self._raise_not_found_for_status(r, rpath)
            if isfilelike(lpath):
                outfile = lpath
            else:
                outfile = open(lpath, "wb")  # noqa: ASYNC101, ASYNC230

            try:
                chunk = True
                while chunk:
                    chunk = await r.content.read(chunk_size)
                    outfile.write(chunk)
                    callback.relative_update(len(chunk))
            finally:
                if not isfilelike(lpath):
                    outfile.close()

    async def _put_file(
        self,
        lpath,
        rpath,
        chunk_size=5 * 2**20,
        callback=DEFAULT_CALLBACK,
        method="post",
        mode="overwrite",
        **kwargs,
    ):
        if mode != "overwrite":
            raise NotImplementedError("Exclusive write")

        async def gen_chunks():
            # Support passing arbitrary file-like objects
            # and use them instead of streams.
            if isinstance(lpath, io.IOBase):
                context = nullcontext(lpath)
                use_seek = False  # might not support seeking
            else:
                context = open(lpath, "rb")  # noqa: ASYNC101, ASYNC230
                use_seek = True

            with context as f:
                if use_seek:
                    callback.set_size(f.seek(0, 2))
                    f.seek(0)
                else:
                    callback.set_size(getattr(f, "size", None))

                chunk = f.read(chunk_size)
                while chunk:
                    yield chunk
                    callback.relative_update(len(chunk))
                    chunk = f.read(chunk_size)

        kw = self.kwargs.copy()
        kw.update(kwargs)
        session = await self.set_session()

        method = method.lower()
        if method not in ("post", "put"):
            raise ValueError(
                f"method has to be either 'post' or 'put', not: {method!r}"
            )

        meth = getattr(session, method)
        async with meth(self.encode_url(rpath), data=gen_chunks(), **kw) as resp:
            self._raise_not_found_for_status(resp, rpath)

    async def _exists(self, path, **kwargs):
        kw = self.kwargs.copy()
        kw.update(kwargs)
        try:
            logger.debug(path)
            session = await self.set_session()
            r = await session.get(self.encode_url(path), **kw)
            async with r:
                return r.status < 400
        except aiohttp.ClientError:
            return False

    async def _isfile(self, path, **kwargs):
        return await self._exists(path, **kwargs)

    def _open(
        self,
        path,
        mode="rb",
        block_size=None,
        autocommit=None,  # XXX: This differs from the base class.
        cache_type=None,
        cache_options=None,
        size=None,
        **kwargs,
    ):
        """Make a file-like object

        Parameters
        ----------
        path: str
            Full URL with protocol
        mode: string
            must be "rb"
        block_size: int or None
            Bytes to download in one request; use instance value if None. If
            zero, will return a streaming Requests file-like instance.
        kwargs: key-value
            Any other parameters, passed to requests calls
        """
        if mode != "rb":
            raise NotImplementedError
        block_size = block_size if block_size is not None else self.block_size
        kw = self.kwargs.copy()
        kw["asynchronous"] = self.asynchronous
        kw.update(kwargs)
        info = {}
        size = size or info.update(self.info(path, **kwargs)) or info["size"]
        session = sync(self.loop, self.set_session)
        if block_size and size and info.get("partial", True):
            return HTTPFile(
                self,
                path,
                session=session,
                block_size=block_size,
                mode=mode,
                size=size,
                cache_type=cache_type or self.cache_type,
                cache_options=cache_options or self.cache_options,
                loop=self.loop,
                **kw,
            )
        else:
            return HTTPStreamFile(
                self,
                path,
                mode=mode,
                loop=self.loop,
                session=session,
                **kw,
            )

    async def open_async(self, path, mode="rb", size=None, **kwargs):
        session = await self.set_session()
        if size is None:
            try:
                size = (await self._info(path, **kwargs))["size"]
            except FileNotFoundError:
                pass
        return AsyncStreamFile(
            self,
            path,
            loop=self.loop,
            session=session,
            size=size,
            **kwargs,
        )

    def ukey(self, url):
        """Unique identifier; assume HTTP files are static, unchanging"""
        return tokenize(url, self.kwargs, self.protocol)

    async def _info(self, url, **kwargs):
        """Get info of URL

        Tries to access location via HEAD, and then GET methods, but does
        not fetch the data.

        It is possible that the server does not supply any size information, in
        which case size will be given as None (and certain operations on the
        corresponding file will not work).
        """
        info = {}
        session = await self.set_session()

        for policy in ["head", "get"]:
            try:
                info.update(
                    await _file_info(
                        self.encode_url(url),
                        size_policy=policy,
                        session=session,
                        **self.kwargs,
                        **kwargs,
                    )
                )
                if info.get("size") is not None:
                    break
            except Exception as exc:
                if policy == "get":
                    # If get failed, then raise a FileNotFoundError
                    raise FileNotFoundError(url) from exc
                logger.debug("", exc_info=exc)

        return {"name": url, "size": None, **info, "type": "file"}

    async def _glob(self, path, maxdepth=None, **kwargs):
        """
        Find files by glob-matching.

        This implementation is idntical to the one in AbstractFileSystem,
        but "?" is not considered as a character for globbing, because it is
        so common in URLs, often identifying the "query" part.
        """
        if maxdepth is not None and maxdepth < 1:
            raise ValueError("maxdepth must be at least 1")
        import re

        ends_with_slash = path.endswith("/")  # _strip_protocol strips trailing slash
        path = self._strip_protocol(path)
        append_slash_to_dirname = ends_with_slash or path.endswith(("/**", "/*"))
        idx_star = path.find("*") if path.find("*") >= 0 else len(path)
        idx_brace = path.find("[") if path.find("[") >= 0 else len(path)

        min_idx = min(idx_star, idx_brace)

        detail = kwargs.pop("detail", False)

        if not has_magic(path):
            if await self._exists(path, **kwargs):
                if not detail:
                    return [path]
                else:
                    return {path: await self._info(path, **kwargs)}
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

        allpaths = await self._find(
            root, maxdepth=depth, withdirs=True, detail=True, **kwargs
        )

        pattern = glob_translate(path + ("/" if ends_with_slash else ""))
        pattern = re.compile(pattern)

        out = {
            (
                p.rstrip("/")
                if not append_slash_to_dirname
                and info["type"] == "directory"
                and p.endswith("/")
                else p
            ): info
            for p, info in sorted(allpaths.items())
            if pattern.match(p.rstrip("/"))
        }

        if detail:
            return out
        else:
            return list(out)

    async def _isdir(self, path):
        # override, since all URLs are (also) files
        try:
            return bool(await self._ls(path))
        except (FileNotFoundError, ValueError):
            return False

    async def _pipe_file(self, path, value, mode="overwrite", **kwargs):
        """
        Write bytes to a remote file over HTTP.

        Parameters
        ----------
        path : str
            Target URL where the data should be written
        value : bytes
            Data to be written
        mode : str
            How to write to the file - 'overwrite' or 'append'
        **kwargs : dict
            Additional parameters to pass to the HTTP request
        """
        url = self._strip_protocol(path)
        headers = kwargs.pop("headers", {})
        headers["Content-Length"] = str(len(value))

        session = await self.set_session()

        async with session.put(url, data=value, headers=headers, **kwargs) as r:
            r.raise_for_status()


class HTTPFile(AbstractBufferedFile):
    """
    A file-like object pointing to a remote HTTP(S) resource

    Supports only reading, with read-ahead of a predetermined block-size.

    In the case that the server does not supply the filesize, only reading of
    the complete file in one go is supported.

    Parameters
    ----------
    url: str
        Full URL of the remote resource, including the protocol
    session: aiohttp.ClientSession or None
        All calls will be made within this session, to avoid restarting
        connections where the server allows this
    block_size: int or None
        The amount of read-ahead to do, in bytes. Default is 5MB, or the value
        configured for the FileSystem creating this file
    size: None or int
        If given, this is the size of the file in bytes, and we don't attempt
        to call the server to find the value.
    kwargs: all other key-values are passed to requests calls.
    """

    def __init__(
        self,
        fs,
        url,
        session=None,
        block_size=None,
        mode="rb",
        cache_type="bytes",
        cache_options=None,
        size=None,
        loop=None,
        asynchronous=False,
        **kwargs,
    ):
        if mode != "rb":
            raise NotImplementedError("File mode not supported")
        self.asynchronous = asynchronous
        self.loop = loop
        self.url = url
        self.session = session
        self.details = {"name": url, "size": size, "type": "file"}
        super().__init__(
            fs=fs,
            path=url,
            mode=mode,
            block_size=block_size,
            cache_type=cache_type,
            cache_options=cache_options,
            **kwargs,
        )

    def read(self, length=-1):
        """Read bytes from file

        Parameters
        ----------
        length: int
            Read up to this many bytes. If negative, read all content to end of
            file. If the server has not supplied the filesize, attempting to
            read only part of the data will raise a ValueError.
        """
        if (
            (length < 0 and self.loc == 0)  # explicit read all
            # but not when the size is known and fits into a block anyways
            and not (self.size is not None and self.size <= self.blocksize)
        ):
            self._fetch_all()
        if self.size is None:
            if length < 0:
                self._fetch_all()
        else:
            length = min(self.size - self.loc, length)
        return super().read(length)

    async def async_fetch_all(self):
        """Read whole file in one shot, without caching

        This is only called when position is still at zero,
        and read() is called without a byte-count.
        """
        logger.debug(f"Fetch all for {self}")
        if not isinstance(self.cache, AllBytes):
            r = await self.session.get(self.fs.encode_url(self.url), **self.kwargs)
            async with r:
                r.raise_for_status()
                out = await r.read()
                self.cache = AllBytes(
                    size=len(out), fetcher=None, blocksize=None, data=out
                )
                self.size = len(out)

    _fetch_all = sync_wrapper(async_fetch_all)

    def _parse_content_range(self, headers):
        """Parse the Content-Range header"""
        s = headers.get("Content-Range", "")
        m = re.match(r"bytes (\d+-\d+|\*)/(\d+|\*)", s)
        if not m:
            return None, None, None

        if m[1] == "*":
            start = end = None
        else:
            start, end = [int(x) for x in m[1].split("-")]
        total = None if m[2] == "*" else int(m[2])
        return start, end, total

    async def async_fetch_range(self, start, end):
        """Download a block of data

        The expectation is that the server returns only the requested bytes,
        with HTTP code 206. If this is not the case, we first check the headers,
        and then stream the output - if the data size is bigger than we
        requested, an exception is raised.
        """
        logger.debug(f"Fetch range for {self}: {start}-{end}")
        kwargs = self.kwargs.copy()
        headers = kwargs.pop("headers", {}).copy()
        headers["Range"] = f"bytes={start}-{end - 1}"
        logger.debug(f"{self.url} : {headers['Range']}")
        r = await self.session.get(
            self.fs.encode_url(self.url), headers=headers, **kwargs
        )
        async with r:
            if r.status == 416:
                # range request outside file
                return b""
            r.raise_for_status()

            # If the server has handled the range request, it should reply
            # with status 206 (partial content). But we'll guess that a suitable
            # Content-Range header or a Content-Length no more than the
            # requested range also mean we have got the desired range.
            response_is_range = (
                r.status == 206
                or self._parse_content_range(r.headers)[0] == start
                or int(r.headers.get("Content-Length", end + 1)) <= end - start
            )

            if response_is_range:
                # partial content, as expected
                out = await r.read()
            elif start > 0:
                raise ValueError(
                    "The HTTP server doesn't appear to support range requests. "
                    "Only reading this file from the beginning is supported. "
                    "Open with block_size=0 for a streaming file interface."
                )
            else:
                # Response is not a range, but we want the start of the file,
                # so we can read the required amount anyway.
                cl = 0
                out = []
                while True:
                    chunk = await r.content.read(2**20)
                    # data size unknown, let's read until we have enough
                    if chunk:
                        out.append(chunk)
                        cl += len(chunk)
                        if cl > end - start:
                            break
                    else:
                        break
                out = b"".join(out)[: end - start]
            return out

    _fetch_range = sync_wrapper(async_fetch_range)


magic_check = re.compile("([*[])")


def has_magic(s):
    match = magic_check.search(s)
    return match is not None


class HTTPStreamFile(AbstractBufferedFile):
    def __init__(self, fs, url, mode="rb", loop=None, session=None, **kwargs):
        self.asynchronous = kwargs.pop("asynchronous", False)
        self.url = url
        self.loop = loop
        self.session = session
        if mode != "rb":
            raise ValueError
        self.details = {"name": url, "size": None}
        super().__init__(fs=fs, path=url, mode=mode, cache_type="none", **kwargs)

        async def cor():
            r = await self.session.get(self.fs.encode_url(url), **kwargs).__aenter__()
            self.fs._raise_not_found_for_status(r, url)
            return r

        self.r = sync(self.loop, cor)
        self.loop = fs.loop

    def seek(self, loc, whence=0):
        if loc == 0 and whence == 1:
            return
        if loc == self.loc and whence == 0:
            return
        raise ValueError("Cannot seek streaming HTTP file")

    async def _read(self, num=-1):
        out = await self.r.content.read(num)
        self.loc += len(out)
        return out

    read = sync_wrapper(_read)

    async def _close(self):
        self.r.close()

    def close(self):
        asyncio.run_coroutine_threadsafe(self._close(), self.loop)
        super().close()


class AsyncStreamFile(AbstractAsyncStreamedFile):
    def __init__(
        self, fs, url, mode="rb", loop=None, session=None, size=None, **kwargs
    ):
        self.url = url
        self.session = session
        self.r = None
        if mode != "rb":
            raise ValueError
        self.details = {"name": url, "size": None}
        self.kwargs = kwargs
        super().__init__(fs=fs, path=url, mode=mode, cache_type="none")
        self.size = size

    async def read(self, num=-1):
        if self.r is None:
            r = await self.session.get(
                self.fs.encode_url(self.url), **self.kwargs
            ).__aenter__()
            self.fs._raise_not_found_for_status(r, self.url)
            self.r = r
        out = await self.r.content.read(num)
        self.loc += len(out)
        return out

    async def close(self):
        if self.r is not None:
            self.r.close()
            self.r = None
        await super().close()


async def get_range(session, url, start, end, file=None, **kwargs):
    # explicit get a range when we know it must be safe
    kwargs = kwargs.copy()
    headers = kwargs.pop("headers", {}).copy()
    headers["Range"] = f"bytes={start}-{end - 1}"
    r = await session.get(url, headers=headers, **kwargs)
    r.raise_for_status()
    async with r:
        out = await r.read()
    if file:
        with open(file, "r+b") as f:  # noqa: ASYNC101, ASYNC230
            f.seek(start)
            f.write(out)
    else:
        return out


async def _file_info(url, session, size_policy="head", **kwargs):
    """Call HEAD on the server to get details about the file (size/checksum etc.)

    Default operation is to explicitly allow redirects and use encoding
    'identity' (no compression) to get the true size of the target.
    """
    logger.debug("Retrieve file size for %s", url)
    kwargs = kwargs.copy()
    ar = kwargs.pop("allow_redirects", True)
    head = kwargs.get("headers", {}).copy()
    head["Accept-Encoding"] = "identity"
    kwargs["headers"] = head

    info = {}
    if size_policy == "head":
        r = await session.head(url, allow_redirects=ar, **kwargs)
    elif size_policy == "get":
        r = await session.get(url, allow_redirects=ar, **kwargs)
    else:
        raise TypeError(f'size_policy must be "head" or "get", got {size_policy}')
    async with r:
        r.raise_for_status()

        if "Content-Length" in r.headers:
            # Some servers may choose to ignore Accept-Encoding and return
            # compressed content, in which case the returned size is unreliable.
            if "Content-Encoding" not in r.headers or r.headers["Content-Encoding"] in [
                "identity",
                "",
            ]:
                info["size"] = int(r.headers["Content-Length"])
        elif "Content-Range" in r.headers:
            info["size"] = int(r.headers["Content-Range"].split("/")[1])

        if "Content-Type" in r.headers:
            info["mimetype"] = r.headers["Content-Type"].partition(";")[0]

        if r.headers.get("Accept-Ranges") == "none":
            # Some servers may explicitly discourage partial content requests, but
            # the lack of "Accept-Ranges" does not always indicate they would fail
            info["partial"] = False

        info["url"] = str(r.url)

        for checksum_field in ["ETag", "Content-MD5", "Digest"]:
            if r.headers.get(checksum_field):
                info[checksum_field] = r.headers[checksum_field]

    return info


async def _file_size(url, session=None, *args, **kwargs):
    if session is None:
        session = await get_client()
    info = await _file_info(url, session=session, *args, **kwargs)
    return info.get("size")


file_size = sync_wrapper(_file_size)