
# === NexusCore/openenv\Lib\site-packages\jinja2\environment.py ===
"""Classes for managing templates and their runtime and compile time
options.
"""

import os
import typing
import typing as t
import weakref
from collections import ChainMap
from functools import lru_cache
from functools import partial
from functools import reduce
from types import CodeType

from markupsafe import Markup

from . import nodes
from .compiler import CodeGenerator
from .compiler import generate
from .defaults import BLOCK_END_STRING
from .defaults import BLOCK_START_STRING
from .defaults import COMMENT_END_STRING
from .defaults import COMMENT_START_STRING
from .defaults import DEFAULT_FILTERS  # type: ignore[attr-defined]
from .defaults import DEFAULT_NAMESPACE
from .defaults import DEFAULT_POLICIES
from .defaults import DEFAULT_TESTS  # type: ignore[attr-defined]
from .defaults import KEEP_TRAILING_NEWLINE
from .defaults import LINE_COMMENT_PREFIX
from .defaults import LINE_STATEMENT_PREFIX
from .defaults import LSTRIP_BLOCKS
from .defaults import NEWLINE_SEQUENCE
from .defaults import TRIM_BLOCKS
from .defaults import VARIABLE_END_STRING
from .defaults import VARIABLE_START_STRING
from .exceptions import TemplateNotFound
from .exceptions import TemplateRuntimeError
from .exceptions import TemplatesNotFound
from .exceptions import TemplateSyntaxError
from .exceptions import UndefinedError
from .lexer import get_lexer
from .lexer import Lexer
from .lexer import TokenStream
from .nodes import EvalContext
from .parser import Parser
from .runtime import Context
from .runtime import new_context
from .runtime import Undefined
from .utils import _PassArg
from .utils import concat
from .utils import consume
from .utils import import_string
from .utils import internalcode
from .utils import LRUCache
from .utils import missing

if t.TYPE_CHECKING:
    import typing_extensions as te

    from .bccache import BytecodeCache
    from .ext import Extension
    from .loaders import BaseLoader

_env_bound = t.TypeVar("_env_bound", bound="Environment")


# for direct template usage we have up to ten living environments
@lru_cache(maxsize=10)
def get_spontaneous_environment(cls: t.Type[_env_bound], *args: t.Any) -> _env_bound:
    """Return a new spontaneous environment. A spontaneous environment
    is used for templates created directly rather than through an
    existing environment.

    :param cls: Environment class to create.
    :param args: Positional arguments passed to environment.
    """
    env = cls(*args)
    env.shared = True
    return env


def create_cache(
    size: int,
) -> t.Optional[t.MutableMapping[t.Tuple["weakref.ref[t.Any]", str], "Template"]]:
    """Return the cache class for the given size."""
    if size == 0:
        return None

    if size < 0:
        return {}

    return LRUCache(size)  # type: ignore


def copy_cache(
    cache: t.Optional[t.MutableMapping[t.Any, t.Any]],
) -> t.Optional[t.MutableMapping[t.Tuple["weakref.ref[t.Any]", str], "Template"]]:
    """Create an empty copy of the given cache."""
    if cache is None:
        return None

    if type(cache) is dict:  # noqa E721
        return {}

    return LRUCache(cache.capacity)  # type: ignore


def load_extensions(
    environment: "Environment",
    extensions: t.Sequence[t.Union[str, t.Type["Extension"]]],
) -> t.Dict[str, "Extension"]:
    """Load the extensions from the list and bind it to the environment.
    Returns a dict of instantiated extensions.
    """
    result = {}

    for extension in extensions:
        if isinstance(extension, str):
            extension = t.cast(t.Type["Extension"], import_string(extension))

        result[extension.identifier] = extension(environment)

    return result


def _environment_config_check(environment: _env_bound) -> _env_bound:
    """Perform a sanity check on the environment."""
    assert issubclass(
        environment.undefined, Undefined
    ), "'undefined' must be a subclass of 'jinja2.Undefined'."
    assert (
        environment.block_start_string
        != environment.variable_start_string
        != environment.comment_start_string
    ), "block, variable and comment start strings must be different."
    assert environment.newline_sequence in {
        "\r",
        "\r\n",
        "\n",
    }, "'newline_sequence' must be one of '\\n', '\\r\\n', or '\\r'."
    return environment


class Environment:
    r"""The core component of Jinja is the `Environment`.  It contains
    important shared variables like configuration, filters, tests,
    globals and others.  Instances of this class may be modified if
    they are not shared and if no template was loaded so far.
    Modifications on environments after the first template was loaded
    will lead to surprising effects and undefined behavior.

    Here are the possible initialization parameters:

        `block_start_string`
            The string marking the beginning of a block.  Defaults to ``'{%'``.

        `block_end_string`
            The string marking the end of a block.  Defaults to ``'%}'``.

        `variable_start_string`
            The string marking the beginning of a print statement.
            Defaults to ``'{{'``.

        `variable_end_string`
            The string marking the end of a print statement.  Defaults to
            ``'}}'``.

        `comment_start_string`
            The string marking the beginning of a comment.  Defaults to ``'{#'``.

        `comment_end_string`
            The string marking the end of a comment.  Defaults to ``'#}'``.

        `line_statement_prefix`
            If given and a string, this will be used as prefix for line based
            statements.  See also :ref:`line-statements`.

        `line_comment_prefix`
            If given and a string, this will be used as prefix for line based
            comments.  See also :ref:`line-statements`.

            .. versionadded:: 2.2

        `trim_blocks`
            If this is set to ``True`` the first newline after a block is
            removed (block, not variable tag!).  Defaults to `False`.

        `lstrip_blocks`
            If this is set to ``True`` leading spaces and tabs are stripped
            from the start of a line to a block.  Defaults to `False`.

        `newline_sequence`
            The sequence that starts a newline.  Must be one of ``'\r'``,
            ``'\n'`` or ``'\r\n'``.  The default is ``'\n'`` which is a
            useful default for Linux and OS X systems as well as web
            applications.

        `keep_trailing_newline`
            Preserve the trailing newline when rendering templates.
            The default is ``False``, which causes a single newline,
            if present, to be stripped from the end of the template.

            .. versionadded:: 2.7

        `extensions`
            List of Jinja extensions to use.  This can either be import paths
            as strings or extension classes.  For more information have a
            look at :ref:`the extensions documentation <jinja-extensions>`.

        `optimized`
            should the optimizer be enabled?  Default is ``True``.

        `undefined`
            :class:`Undefined` or a subclass of it that is used to represent
            undefined values in the template.

        `finalize`
            A callable that can be used to process the result of a variable
            expression before it is output.  For example one can convert
            ``None`` implicitly into an empty string here.

        `autoescape`
            If set to ``True`` the XML/HTML autoescaping feature is enabled by
            default.  For more details about autoescaping see
            :class:`~markupsafe.Markup`.  As of Jinja 2.4 this can also
            be a callable that is passed the template name and has to
            return ``True`` or ``False`` depending on autoescape should be
            enabled by default.

            .. versionchanged:: 2.4
               `autoescape` can now be a function

        `loader`
            The template loader for this environment.

        `cache_size`
            The size of the cache.  Per default this is ``400`` which means
            that if more than 400 templates are loaded the loader will clean
            out the least recently used template.  If the cache size is set to
            ``0`` templates are recompiled all the time, if the cache size is
            ``-1`` the cache will not be cleaned.

            .. versionchanged:: 2.8
               The cache size was increased to 400 from a low 50.

        `auto_reload`
            Some loaders load templates from locations where the template
            sources may change (ie: file system or database).  If
            ``auto_reload`` is set to ``True`` (default) every time a template is
            requested the loader checks if the source changed and if yes, it
            will reload the template.  For higher performance it's possible to
            disable that.

        `bytecode_cache`
            If set to a bytecode cache object, this object will provide a
            cache for the internal Jinja bytecode so that templates don't
            have to be parsed if they were not changed.

            See :ref:`bytecode-cache` for more information.

        `enable_async`
            If set to true this enables async template execution which
            allows using async functions and generators.
    """

    #: if this environment is sandboxed.  Modifying this variable won't make
    #: the environment sandboxed though.  For a real sandboxed environment
    #: have a look at jinja2.sandbox.  This flag alone controls the code
    #: generation by the compiler.
    sandboxed = False

    #: True if the environment is just an overlay
    overlayed = False

    #: the environment this environment is linked to if it is an overlay
    linked_to: t.Optional["Environment"] = None

    #: shared environments have this set to `True`.  A shared environment
    #: must not be modified
    shared = False

    #: the class that is used for code generation.  See
    #: :class:`~jinja2.compiler.CodeGenerator` for more information.
    code_generator_class: t.Type["CodeGenerator"] = CodeGenerator

    concat = "".join

    #: the context class that is used for templates.  See
    #: :class:`~jinja2.runtime.Context` for more information.
    context_class: t.Type[Context] = Context

    template_class: t.Type["Template"]

    def __init__(
        self,
        block_start_string: str = BLOCK_START_STRING,
        block_end_string: str = BLOCK_END_STRING,
        variable_start_string: str = VARIABLE_START_STRING,
        variable_end_string: str = VARIABLE_END_STRING,
        comment_start_string: str = COMMENT_START_STRING,
        comment_end_string: str = COMMENT_END_STRING,
        line_statement_prefix: t.Optional[str] = LINE_STATEMENT_PREFIX,
        line_comment_prefix: t.Optional[str] = LINE_COMMENT_PREFIX,
        trim_blocks: bool = TRIM_BLOCKS,
        lstrip_blocks: bool = LSTRIP_BLOCKS,
        newline_sequence: "te.Literal['\\n', '\\r\\n', '\\r']" = NEWLINE_SEQUENCE,
        keep_trailing_newline: bool = KEEP_TRAILING_NEWLINE,
        extensions: t.Sequence[t.Union[str, t.Type["Extension"]]] = (),
        optimized: bool = True,
        undefined: t.Type[Undefined] = Undefined,
        finalize: t.Optional[t.Callable[..., t.Any]] = None,
        autoescape: t.Union[bool, t.Callable[[t.Optional[str]], bool]] = False,
        loader: t.Optional["BaseLoader"] = None,
        cache_size: int = 400,
        auto_reload: bool = True,
        bytecode_cache: t.Optional["BytecodeCache"] = None,
        enable_async: bool = False,
    ):
        # !!Important notice!!
        #   The constructor accepts quite a few arguments that should be
        #   passed by keyword rather than position.  However it's important to
        #   not change the order of arguments because it's used at least
        #   internally in those cases:
        #       -   spontaneous environments (i18n extension and Template)
        #       -   unittests
        #   If parameter changes are required only add parameters at the end
        #   and don't change the arguments (or the defaults!) of the arguments
        #   existing already.

        # lexer / parser information
        self.block_start_string = block_start_string
        self.block_end_string = block_end_string
        self.variable_start_string = variable_start_string
        self.variable_end_string = variable_end_string
        self.comment_start_string = comment_start_string
        self.comment_end_string = comment_end_string
        self.line_statement_prefix = line_statement_prefix
        self.line_comment_prefix = line_comment_prefix
        self.trim_blocks = trim_blocks
        self.lstrip_blocks = lstrip_blocks
        self.newline_sequence = newline_sequence
        self.keep_trailing_newline = keep_trailing_newline

        # runtime information
        self.undefined: t.Type[Undefined] = undefined
        self.optimized = optimized
        self.finalize = finalize
        self.autoescape = autoescape

        # defaults
        self.filters = DEFAULT_FILTERS.copy()
        self.tests = DEFAULT_TESTS.copy()
        self.globals = DEFAULT_NAMESPACE.copy()

        # set the loader provided
        self.loader = loader
        self.cache = create_cache(cache_size)
        self.bytecode_cache = bytecode_cache
        self.auto_reload = auto_reload

        # configurable policies
        self.policies = DEFAULT_POLICIES.copy()

        # load extensions
        self.extensions = load_extensions(self, extensions)

        self.is_async = enable_async
        _environment_config_check(self)

    def add_extension(self, extension: t.Union[str, t.Type["Extension"]]) -> None:
        """Adds an extension after the environment was created.

        .. versionadded:: 2.5
        """
        self.extensions.update(load_extensions(self, [extension]))

    def extend(self, **attributes: t.Any) -> None:
        """Add the items to the instance of the environment if they do not exist
        yet.  This is used by :ref:`extensions <writing-extensions>` to register
        callbacks and configuration values without breaking inheritance.
        """
        for key, value in attributes.items():
            if not hasattr(self, key):
                setattr(self, key, value)

    def overlay(
        self,
        block_start_string: str = missing,
        block_end_string: str = missing,
        variable_start_string: str = missing,
        variable_end_string: str = missing,
        comment_start_string: str = missing,
        comment_end_string: str = missing,
        line_statement_prefix: t.Optional[str] = missing,
        line_comment_prefix: t.Optional[str] = missing,
        trim_blocks: bool = missing,
        lstrip_blocks: bool = missing,
        newline_sequence: "te.Literal['\\n', '\\r\\n', '\\r']" = missing,
        keep_trailing_newline: bool = missing,
        extensions: t.Sequence[t.Union[str, t.Type["Extension"]]] = missing,
        optimized: bool = missing,
        undefined: t.Type[Undefined] = missing,
        finalize: t.Optional[t.Callable[..., t.Any]] = missing,
        autoescape: t.Union[bool, t.Callable[[t.Optional[str]], bool]] = missing,
        loader: t.Optional["BaseLoader"] = missing,
        cache_size: int = missing,
        auto_reload: bool = missing,
        bytecode_cache: t.Optional["BytecodeCache"] = missing,
        enable_async: bool = missing,
    ) -> "te.Self":
        """Create a new overlay environment that shares all the data with the
        current environment except for cache and the overridden attributes.
        Extensions cannot be removed for an overlayed environment.  An overlayed
        environment automatically gets all the extensions of the environment it
        is linked to plus optional extra extensions.

        Creating overlays should happen after the initial environment was set
        up completely.  Not all attributes are truly linked, some are just
        copied over so modifications on the original environment may not shine
        through.

        .. versionchanged:: 3.1.5
            ``enable_async`` is applied correctly.

        .. versionchanged:: 3.1.2
            Added the ``newline_sequence``, ``keep_trailing_newline``,
            and ``enable_async`` parameters to match ``__init__``.
        """
        args = dict(locals())
        del args["self"], args["cache_size"], args["extensions"], args["enable_async"]

        rv = object.__new__(self.__class__)
        rv.__dict__.update(self.__dict__)
        rv.overlayed = True
        rv.linked_to = self

        for key, value in args.items():
            if value is not missing:
                setattr(rv, key, value)

        if cache_size is not missing:
            rv.cache = create_cache(cache_size)
        else:
            rv.cache = copy_cache(self.cache)

        rv.extensions = {}
        for key, value in self.extensions.items():
            rv.extensions[key] = value.bind(rv)
        if extensions is not missing:
            rv.extensions.update(load_extensions(rv, extensions))

        if enable_async is not missing:
            rv.is_async = enable_async

        return _environment_config_check(rv)

    @property
    def lexer(self) -> Lexer:
        """The lexer for this environment."""
        return get_lexer(self)

    def iter_extensions(self) -> t.Iterator["Extension"]:
        """Iterates over the extensions by priority."""
        return iter(sorted(self.extensions.values(), key=lambda x: x.priority))

    def getitem(
        self, obj: t.Any, argument: t.Union[str, t.Any]
    ) -> t.Union[t.Any, Undefined]:
        """Get an item or attribute of an object but prefer the item."""
        try:
            return obj[argument]
        except (AttributeError, TypeError, LookupError):
            if isinstance(argument, str):
                try:
                    attr = str(argument)
                except Exception:
                    pass
                else:
                    try:
                        return getattr(obj, attr)
                    except AttributeError:
                        pass
            return self.undefined(obj=obj, name=argument)

    def getattr(self, obj: t.Any, attribute: str) -> t.Any:
        """Get an item or attribute of an object but prefer the attribute.
        Unlike :meth:`getitem` the attribute *must* be a string.
        """
        try:
            return getattr(obj, attribute)
        except AttributeError:
            pass
        try:
            return obj[attribute]
        except (TypeError, LookupError, AttributeError):
            return self.undefined(obj=obj, name=attribute)

    def _filter_test_common(
        self,
        name: t.Union[str, Undefined],
        value: t.Any,
        args: t.Optional[t.Sequence[t.Any]],
        kwargs: t.Optional[t.Mapping[str, t.Any]],
        context: t.Optional[Context],
        eval_ctx: t.Optional[EvalContext],
        is_filter: bool,
    ) -> t.Any:
        if is_filter:
            env_map = self.filters
            type_name = "filter"
        else:
            env_map = self.tests
            type_name = "test"

        func = env_map.get(name)  # type: ignore

        if func is None:
            msg = f"No {type_name} named {name!r}."

            if isinstance(name, Undefined):
                try:
                    name._fail_with_undefined_error()
                except Exception as e:
                    msg = f"{msg} ({e}; did you forget to quote the callable name?)"

            raise TemplateRuntimeError(msg)

        args = [value, *(args if args is not None else ())]
        kwargs = kwargs if kwargs is not None else {}
        pass_arg = _PassArg.from_obj(func)

        if pass_arg is _PassArg.context:
            if context is None:
                raise TemplateRuntimeError(
                    f"Attempted to invoke a context {type_name} without context."
                )

            args.insert(0, context)
        elif pass_arg is _PassArg.eval_context:
            if eval_ctx is None:
                if context is not None:
                    eval_ctx = context.eval_ctx
                else:
                    eval_ctx = EvalContext(self)

            args.insert(0, eval_ctx)
        elif pass_arg is _PassArg.environment:
            args.insert(0, self)

        return func(*args, **kwargs)

    def call_filter(
        self,
        name: str,
        value: t.Any,
        args: t.Optional[t.Sequence[t.Any]] = None,
        kwargs: t.Optional[t.Mapping[str, t.Any]] = None,
        context: t.Optional[Context] = None,
        eval_ctx: t.Optional[EvalContext] = None,
    ) -> t.Any:
        """Invoke a filter on a value the same way the compiler does.

        This might return a coroutine if the filter is running from an
        environment in async mode and the filter supports async
        execution. It's your responsibility to await this if needed.

        .. versionadded:: 2.7
        """
        return self._filter_test_common(
            name, value, args, kwargs, context, eval_ctx, True
        )

    def call_test(
        self,
        name: str,
        value: t.Any,
        args: t.Optional[t.Sequence[t.Any]] = None,
        kwargs: t.Optional[t.Mapping[str, t.Any]] = None,
        context: t.Optional[Context] = None,
        eval_ctx: t.Optional[EvalContext] = None,
    ) -> t.Any:
        """Invoke a test on a value the same way the compiler does.

        This might return a coroutine if the test is running from an
        environment in async mode and the test supports async execution.
        It's your responsibility to await this if needed.

        .. versionchanged:: 3.0
            Tests support ``@pass_context``, etc. decorators. Added
            the ``context`` and ``eval_ctx`` parameters.

        .. versionadded:: 2.7
        """
        return self._filter_test_common(
            name, value, args, kwargs, context, eval_ctx, False
        )

    @internalcode
    def parse(
        self,
        source: str,
        name: t.Optional[str] = None,
        filename: t.Optional[str] = None,
    ) -> nodes.Template:
        """Parse the sourcecode and return the abstract syntax tree.  This
        tree of nodes is used by the compiler to convert the template into
        executable source- or bytecode.  This is useful for debugging or to
        extract information from templates.

        If you are :ref:`developing Jinja extensions <writing-extensions>`
        this gives you a good overview of the node tree generated.
        """
        try:
            return self._parse(source, name, filename)
        except TemplateSyntaxError:
            self.handle_exception(source=source)

    def _parse(
        self, source: str, name: t.Optional[str], filename: t.Optional[str]
    ) -> nodes.Template:
        """Internal parsing function used by `parse` and `compile`."""
        return Parser(self, source, name, filename).parse()

    def lex(
        self,
        source: str,
        name: t.Optional[str] = None,
        filename: t.Optional[str] = None,
    ) -> t.Iterator[t.Tuple[int, str, str]]:
        """Lex the given sourcecode and return a generator that yields
        tokens as tuples in the form ``(lineno, token_type, value)``.
        This can be useful for :ref:`extension development <writing-extensions>`
        and debugging templates.

        This does not perform preprocessing.  If you want the preprocessing
        of the extensions to be applied you have to filter source through
        the :meth:`preprocess` method.
        """
        source = str(source)
        try:
            return self.lexer.tokeniter(source, name, filename)
        except TemplateSyntaxError:
            self.handle_exception(source=source)

    def preprocess(
        self,
        source: str,
        name: t.Optional[str] = None,
        filename: t.Optional[str] = None,
    ) -> str:
        """Preprocesses the source with all extensions.  This is automatically
        called for all parsing and compiling methods but *not* for :meth:`lex`
        because there you usually only want the actual source tokenized.
        """
        return reduce(
            lambda s, e: e.preprocess(s, name, filename),
            self.iter_extensions(),
            str(source),
        )

    def _tokenize(
        self,
        source: str,
        name: t.Optional[str],
        filename: t.Optional[str] = None,
        state: t.Optional[str] = None,
    ) -> TokenStream:
        """Called by the parser to do the preprocessing and filtering
        for all the extensions.  Returns a :class:`~jinja2.lexer.TokenStream`.
        """
        source = self.preprocess(source, name, filename)
        stream = self.lexer.tokenize(source, name, filename, state)

        for ext in self.iter_extensions():
            stream = ext.filter_stream(stream)  # type: ignore

            if not isinstance(stream, TokenStream):
                stream = TokenStream(stream, name, filename)

        return stream

    def _generate(
        self,
        source: nodes.Template,
        name: t.Optional[str],
        filename: t.Optional[str],
        defer_init: bool = False,
    ) -> str:
        """Internal hook that can be overridden to hook a different generate
        method in.

        .. versionadded:: 2.5
        """
        return generate(  # type: ignore
            source,
            self,
            name,
            filename,
            defer_init=defer_init,
            optimized=self.optimized,
        )

    def _compile(self, source: str, filename: str) -> CodeType:
        """Internal hook that can be overridden to hook a different compile
        method in.

        .. versionadded:: 2.5
        """
        return compile(source, filename, "exec")

    @typing.overload
    def compile(
        self,
        source: t.Union[str, nodes.Template],
        name: t.Optional[str] = None,
        filename: t.Optional[str] = None,
        raw: "te.Literal[False]" = False,
        defer_init: bool = False,
    ) -> CodeType: ...

    @typing.overload
    def compile(
        self,
        source: t.Union[str, nodes.Template],
        name: t.Optional[str] = None,
        filename: t.Optional[str] = None,
        raw: "te.Literal[True]" = ...,
        defer_init: bool = False,
    ) -> str: ...

    @internalcode
    def compile(
        self,
        source: t.Union[str, nodes.Template],
        name: t.Optional[str] = None,
        filename: t.Optional[str] = None,
        raw: bool = False,
        defer_init: bool = False,
    ) -> t.Union[str, CodeType]:
        """Compile a node or template source code.  The `name` parameter is
        the load name of the template after it was joined using
        :meth:`join_path` if necessary, not the filename on the file system.
        the `filename` parameter is the estimated filename of the template on
        the file system.  If the template came from a database or memory this
        can be omitted.

        The return value of this method is a python code object.  If the `raw`
        parameter is `True` the return value will be a string with python
        code equivalent to the bytecode returned otherwise.  This method is
        mainly used internally.

        `defer_init` is use internally to aid the module code generator.  This
        causes the generated code to be able to import without the global
        environment variable to be set.

        .. versionadded:: 2.4
           `defer_init` parameter added.
        """
        source_hint = None
        try:
            if isinstance(source, str):
                source_hint = source
                source = self._parse(source, name, filename)
            source = self._generate(source, name, filename, defer_init=defer_init)
            if raw:
                return source
            if filename is None:
                filename = "<template>"
            return self._compile(source, filename)
        except TemplateSyntaxError:
            self.handle_exception(source=source_hint)

    def compile_expression(
        self, source: str, undefined_to_none: bool = True
    ) -> "TemplateExpression":
        """A handy helper method that returns a callable that accepts keyword
        arguments that appear as variables in the expression.  If called it
        returns the result of the expression.

        This is useful if applications want to use the same rules as Jinja
        in template "configuration files" or similar situations.

        Example usage:

        >>> env = Environment()
        >>> expr = env.compile_expression('foo == 42')
        >>> expr(foo=23)
        False
        >>> expr(foo=42)
        True

        Per default the return value is converted to `None` if the
        expression returns an undefined value.  This can be changed
        by setting `undefined_to_none` to `False`.

        >>> env.compile_expression('var')() is None
        True
        >>> env.compile_expression('var', undefined_to_none=False)()
        Undefined

        .. versionadded:: 2.1
        """
        parser = Parser(self, source, state="variable")
        try:
            expr = parser.parse_expression()
            if not parser.stream.eos:
                raise TemplateSyntaxError(
                    "chunk after expression", parser.stream.current.lineno, None, None
                )
            expr.set_environment(self)
        except TemplateSyntaxError:
            self.handle_exception(source=source)

        body = [nodes.Assign(nodes.Name("result", "store"), expr, lineno=1)]
        template = self.from_string(nodes.Template(body, lineno=1))
        return TemplateExpression(template, undefined_to_none)

    def compile_templates(
        self,
        target: t.Union[str, "os.PathLike[str]"],
        extensions: t.Optional[t.Collection[str]] = None,
        filter_func: t.Optional[t.Callable[[str], bool]] = None,
        zip: t.Optional[str] = "deflated",
        log_function: t.Optional[t.Callable[[str], None]] = None,
        ignore_errors: bool = True,
    ) -> None:
        """Finds all the templates the loader can find, compiles them
        and stores them in `target`.  If `zip` is `None`, instead of in a
        zipfile, the templates will be stored in a directory.
        By default a deflate zip algorithm is used. To switch to
        the stored algorithm, `zip` can be set to ``'stored'``.

        `extensions` and `filter_func` are passed to :meth:`list_templates`.
        Each template returned will be compiled to the target folder or
        zipfile.

        By default template compilation errors are ignored.  In case a
        log function is provided, errors are logged.  If you want template
        syntax errors to abort the compilation you can set `ignore_errors`
        to `False` and you will get an exception on syntax errors.

        .. versionadded:: 2.4
        """
        from .loaders import ModuleLoader

        if log_function is None:

            def log_function(x: str) -> None:
                pass

        assert log_function is not None
        assert self.loader is not None, "No loader configured."

        def write_file(filename: str, data: str) -> None:
            if zip:
                info = ZipInfo(filename)
                info.external_attr = 0o755 << 16
                zip_file.writestr(info, data)
            else:
                with open(os.path.join(target, filename), "wb") as f:
                    f.write(data.encode("utf8"))

        if zip is not None:
            from zipfile import ZIP_DEFLATED
            from zipfile import ZIP_STORED
            from zipfile import ZipFile
            from zipfile import ZipInfo

            zip_file = ZipFile(
                target, "w", dict(deflated=ZIP_DEFLATED, stored=ZIP_STORED)[zip]
            )
            log_function(f"Compiling into Zip archive {target!r}")
        else:
            if not os.path.isdir(target):
                os.makedirs(target)
            log_function(f"Compiling into folder {target!r}")

        try:
            for name in self.list_templates(extensions, filter_func):
                source, filename, _ = self.loader.get_source(self, name)
                try:
                    code = self.compile(source, name, filename, True, True)
                except TemplateSyntaxError as e:
                    if not ignore_errors:
                        raise
                    log_function(f'Could not compile "{name}": {e}')
                    continue

                filename = ModuleLoader.get_module_filename(name)

                write_file(filename, code)
                log_function(f'Compiled "{name}" as {filename}')
        finally:
            if zip:
                zip_file.close()

        log_function("Finished compiling templates")

    def list_templates(
        self,
        extensions: t.Optional[t.Collection[str]] = None,
        filter_func: t.Optional[t.Callable[[str], bool]] = None,
    ) -> t.List[str]:
        """Returns a list of templates for this environment.  This requires
        that the loader supports the loader's
        :meth:`~BaseLoader.list_templates` method.

        If there are other files in the template folder besides the
        actual templates, the returned list can be filtered.  There are two
        ways: either `extensions` is set to a list of file extensions for
        templates, or a `filter_func` can be provided which is a callable that
        is passed a template name and should return `True` if it should end up
        in the result list.

        If the loader does not support that, a :exc:`TypeError` is raised.

        .. versionadded:: 2.4
        """
        assert self.loader is not None, "No loader configured."
        names = self.loader.list_templates()

        if extensions is not None:
            if filter_func is not None:
                raise TypeError(
                    "either extensions or filter_func can be passed, but not both"
                )

            def filter_func(x: str) -> bool:
                return "." in x and x.rsplit(".", 1)[1] in extensions

        if filter_func is not None:
            names = [name for name in names if filter_func(name)]

        return names

    def handle_exception(self, source: t.Optional[str] = None) -> "te.NoReturn":
        """Exception handling helper.  This is used internally to either raise
        rewritten exceptions or return a rendered traceback for the template.
        """
        from .debug import rewrite_traceback_stack

        raise rewrite_traceback_stack(source=source)

    def join_path(self, template: str, parent: str) -> str:
        """Join a template with the parent.  By default all the lookups are
        relative to the loader root so this method returns the `template`
        parameter unchanged, but if the paths should be relative to the
        parent template, this function can be used to calculate the real
        template name.

        Subclasses may override this method and implement template path
        joining here.
        """
        return template

    @internalcode
    def _load_template(
        self, name: str, globals: t.Optional[t.MutableMapping[str, t.Any]]
    ) -> "Template":
        if self.loader is None:
            raise TypeError("no loader for this environment specified")
        cache_key = (weakref.ref(self.loader), name)
        if self.cache is not None:
            template = self.cache.get(cache_key)
            if template is not None and (
                not self.auto_reload or template.is_up_to_date
            ):
                # template.globals is a ChainMap, modifying it will only
                # affect the template, not the environment globals.
                if globals:
                    template.globals.update(globals)

                return template

        template = self.loader.load(self, name, self.make_globals(globals))

        if self.cache is not None:
            self.cache[cache_key] = template
        return template

    @internalcode
    def get_template(
        self,
        name: t.Union[str, "Template"],
        parent: t.Optional[str] = None,
        globals: t.Optional[t.MutableMapping[str, t.Any]] = None,
    ) -> "Template":
        """Load a template by name with :attr:`loader` and return a
        :class:`Template`. If the template does not exist a
        :exc:`TemplateNotFound` exception is raised.

        :param name: Name of the template to load. When loading
            templates from the filesystem, "/" is used as the path
            separator, even on Windows.
        :param parent: The name of the parent template importing this
            template. :meth:`join_path` can be used to implement name
            transformations with this.
        :param globals: Extend the environment :attr:`globals` with
            these extra variables available for all renders of this
            template. If the template has already been loaded and
            cached, its globals are updated with any new items.

        .. versionchanged:: 3.0
            If a template is loaded from cache, ``globals`` will update
            the template's globals instead of ignoring the new values.

        .. versionchanged:: 2.4
            If ``name`` is a :class:`Template` object it is returned
            unchanged.
        """
        if isinstance(name, Template):
            return name
        if parent is not None:
            name = self.join_path(name, parent)

        return self._load_template(name, globals)

    @internalcode
    def select_template(
        self,
        names: t.Iterable[t.Union[str, "Template"]],
        parent: t.Optional[str] = None,
        globals: t.Optional[t.MutableMapping[str, t.Any]] = None,
    ) -> "Template":
        """Like :meth:`get_template`, but tries loading multiple names.
        If none of the names can be loaded a :exc:`TemplatesNotFound`
        exception is raised.

        :param names: List of template names to try loading in order.
        :param parent: The name of the parent template importing this
            template. :meth:`join_path` can be used to implement name
            transformations with this.
        :param globals: Extend the environment :attr:`globals` with
            these extra variables available for all renders of this
            template. If the template has already been loaded and
            cached, its globals are updated with any new items.

        .. versionchanged:: 3.0
            If a template is loaded from cache, ``globals`` will update
            the template's globals instead of ignoring the new values.

        .. versionchanged:: 2.11
            If ``names`` is :class:`Undefined`, an :exc:`UndefinedError`
            is raised instead. If no templates were found and ``names``
            contains :class:`Undefined`, the message is more helpful.

        .. versionchanged:: 2.4
            If ``names`` contains a :class:`Template` object it is
            returned unchanged.

        .. versionadded:: 2.3
        """
        if isinstance(names, Undefined):
            names._fail_with_undefined_error()

        if not names:
            raise TemplatesNotFound(
                message="Tried to select from an empty list of templates."
            )

        for name in names:
            if isinstance(name, Template):
                return name
            if parent is not None:
                name = self.join_path(name, parent)
            try:
                return self._load_template(name, globals)
            except (TemplateNotFound, UndefinedError):
                pass
        raise TemplatesNotFound(names)  # type: ignore

    @internalcode
    def get_or_select_template(
        self,
        template_name_or_list: t.Union[
            str, "Template", t.List[t.Union[str, "Template"]]
        ],
        parent: t.Optional[str] = None,
        globals: t.Optional[t.MutableMapping[str, t.Any]] = None,
    ) -> "Template":
        """Use :meth:`select_template` if an iterable of template names
        is given, or :meth:`get_template` if one name is given.

        .. versionadded:: 2.3
        """
        if isinstance(template_name_or_list, (str, Undefined)):
            return self.get_template(template_name_or_list, parent, globals)
        elif isinstance(template_name_or_list, Template):
            return template_name_or_list
        return self.select_template(template_name_or_list, parent, globals)

    def from_string(
        self,
        source: t.Union[str, nodes.Template],
        globals: t.Optional[t.MutableMapping[str, t.Any]] = None,
        template_class: t.Optional[t.Type["Template"]] = None,
    ) -> "Template":
        """Load a template from a source string without using
        :attr:`loader`.

        :param source: Jinja source to compile into a template.
        :param globals: Extend the environment :attr:`globals` with
            these extra variables available for all renders of this
            template. If the template has already been loaded and
            cached, its globals are updated with any new items.
        :param template_class: Return an instance of this
            :class:`Template` class.
        """
        gs = self.make_globals(globals)
        cls = template_class or self.template_class
        return cls.from_code(self, self.compile(source), gs, None)

    def make_globals(
        self, d: t.Optional[t.MutableMapping[str, t.Any]]
    ) -> t.MutableMapping[str, t.Any]:
        """Make the globals map for a template. Any given template
        globals overlay the environment :attr:`globals`.

        Returns a :class:`collections.ChainMap`. This allows any changes
        to a template's globals to only affect that template, while
        changes to the environment's globals are still reflected.
        However, avoid modifying any globals after a template is loaded.

        :param d: Dict of template-specific globals.

        .. versionchanged:: 3.0
            Use :class:`collections.ChainMap` to always prevent mutating
            environment globals.
        """
        if d is None:
            d = {}

        return ChainMap(d, self.globals)


class Template:
    """A compiled template that can be rendered.

    Use the methods on :class:`Environment` to create or load templates.
    The environment is used to configure how templates are compiled and
    behave.

    It is also possible to create a template object directly. This is
    not usually recommended. The constructor takes most of the same
    arguments as :class:`Environment`. All templates created with the
    same environment arguments share the same ephemeral ``Environment``
    instance behind the scenes.

    A template object should be considered immutable. Modifications on
    the object are not supported.
    """

    #: Type of environment to create when creating a template directly
    #: rather than through an existing environment.
    environment_class: t.Type[Environment] = Environment

    environment: Environment
    globals: t.MutableMapping[str, t.Any]
    name: t.Optional[str]
    filename: t.Optional[str]
    blocks: t.Dict[str, t.Callable[[Context], t.Iterator[str]]]
    root_render_func: t.Callable[[Context], t.Iterator[str]]
    _module: t.Optional["TemplateModule"]
    _debug_info: str
    _uptodate: t.Optional[t.Callable[[], bool]]

    def __new__(
        cls,
        source: t.Union[str, nodes.Template],
        block_start_string: str = BLOCK_START_STRING,
        block_end_string: str = BLOCK_END_STRING,
        variable_start_string: str = VARIABLE_START_STRING,
        variable_end_string: str = VARIABLE_END_STRING,
        comment_start_string: str = COMMENT_START_STRING,
        comment_end_string: str = COMMENT_END_STRING,
        line_statement_prefix: t.Optional[str] = LINE_STATEMENT_PREFIX,
        line_comment_prefix: t.Optional[str] = LINE_COMMENT_PREFIX,
        trim_blocks: bool = TRIM_BLOCKS,
        lstrip_blocks: bool = LSTRIP_BLOCKS,
        newline_sequence: "te.Literal['\\n', '\\r\\n', '\\r']" = NEWLINE_SEQUENCE,
        keep_trailing_newline: bool = KEEP_TRAILING_NEWLINE,
        extensions: t.Sequence[t.Union[str, t.Type["Extension"]]] = (),
        optimized: bool = True,
        undefined: t.Type[Undefined] = Undefined,
        finalize: t.Optional[t.Callable[..., t.Any]] = None,
        autoescape: t.Union[bool, t.Callable[[t.Optional[str]], bool]] = False,
        enable_async: bool = False,
    ) -> t.Any:  # it returns a `Template`, but this breaks the sphinx build...
        env = get_spontaneous_environment(
            cls.environment_class,  # type: ignore
            block_start_string,
            block_end_string,
            variable_start_string,
            variable_end_string,
            comment_start_string,
            comment_end_string,
            line_statement_prefix,
            line_comment_prefix,
            trim_blocks,
            lstrip_blocks,
            newline_sequence,
            keep_trailing_newline,
            frozenset(extensions),
            optimized,
            undefined,  # type: ignore
            finalize,
            autoescape,
            None,
            0,
            False,
            None,
            enable_async,
        )
        return env.from_string(source, template_class=cls)

    @classmethod
    def from_code(
        cls,
        environment: Environment,
        code: CodeType,
        globals: t.MutableMapping[str, t.Any],
        uptodate: t.Optional[t.Callable[[], bool]] = None,
    ) -> "Template":
        """Creates a template object from compiled code and the globals.  This
        is used by the loaders and environment to create a template object.
        """
        namespace = {"environment": environment, "__file__": code.co_filename}
        exec(code, namespace)
        rv = cls._from_namespace(environment, namespace, globals)
        rv._uptodate = uptodate
        return rv

    @classmethod
    def from_module_dict(
        cls,
        environment: Environment,
        module_dict: t.MutableMapping[str, t.Any],
        globals: t.MutableMapping[str, t.Any],
    ) -> "Template":
        """Creates a template object from a module.  This is used by the
        module loader to create a template object.

        .. versionadded:: 2.4
        """
        return cls._from_namespace(environment, module_dict, globals)

    @classmethod
    def _from_namespace(
        cls,
        environment: Environment,
        namespace: t.MutableMapping[str, t.Any],
        globals: t.MutableMapping[str, t.Any],
    ) -> "Template":
        t: Template = object.__new__(cls)
        t.environment = environment
        t.globals = globals
        t.name = namespace["name"]
        t.filename = namespace["__file__"]
        t.blocks = namespace["blocks"]

        # render function and module
        t.root_render_func = namespace["root"]
        t._module = None

        # debug and loader helpers
        t._debug_info = namespace["debug_info"]
        t._uptodate = None

        # store the reference
        namespace["environment"] = environment
        namespace["__jinja_template__"] = t

        return t

    def render(self, *args: t.Any, **kwargs: t.Any) -> str:
        """This method accepts the same arguments as the `dict` constructor:
        A dict, a dict subclass or some keyword arguments.  If no arguments
        are given the context will be empty.  These two calls do the same::

            template.render(knights='that say nih')
            template.render({'knights': 'that say nih'})

        This will return the rendered template as a string.
        """
        if self.environment.is_async:
            import asyncio

            return asyncio.run(self.render_async(*args, **kwargs))

        ctx = self.new_context(dict(*args, **kwargs))

        try:
            return self.environment.concat(self.root_render_func(ctx))  # type: ignore
        except Exception:
            self.environment.handle_exception()

    async def render_async(self, *args: t.Any, **kwargs: t.Any) -> str:
        """This works similar to :meth:`render` but returns a coroutine
        that when awaited returns the entire rendered template string.  This
        requires the async feature to be enabled.

        Example usage::

            await template.render_async(knights='that say nih; asynchronously')
        """
        if not self.environment.is_async:
            raise RuntimeError(
                "The environment was not created with async mode enabled."
            )

        ctx = self.new_context(dict(*args, **kwargs))

        try:
            return self.environment.concat(  # type: ignore
                [n async for n in self.root_render_func(ctx)]  # type: ignore
            )
        except Exception:
            return self.environment.handle_exception()

    def stream(self, *args: t.Any, **kwargs: t.Any) -> "TemplateStream":
        """Works exactly like :meth:`generate` but returns a
        :class:`TemplateStream`.
        """
        return TemplateStream(self.generate(*args, **kwargs))

    def generate(self, *args: t.Any, **kwargs: t.Any) -> t.Iterator[str]:
        """For very large templates it can be useful to not render the whole
        template at once but evaluate each statement after another and yield
        piece for piece.  This method basically does exactly that and returns
        a generator that yields one item after another as strings.

        It accepts the same arguments as :meth:`render`.
        """
        if self.environment.is_async:
            import asyncio

            async def to_list() -> t.List[str]:
                return [x async for x in self.generate_async(*args, **kwargs)]

            yield from asyncio.run(to_list())
            return

        ctx = self.new_context(dict(*args, **kwargs))

        try:
            yield from self.root_render_func(ctx)
        except Exception:
            yield self.environment.handle_exception()

    async def generate_async(
        self, *args: t.Any, **kwargs: t.Any
    ) -> t.AsyncGenerator[str, object]:
        """An async version of :meth:`generate`.  Works very similarly but
        returns an async iterator instead.
        """
        if not self.environment.is_async:
            raise RuntimeError(
                "The environment was not created with async mode enabled."
            )

        ctx = self.new_context(dict(*args, **kwargs))

        try:
            agen = self.root_render_func(ctx)
            try:
                async for event in agen:  # type: ignore
                    yield event
            finally:
                # we can't use async with aclosing(...) because that's only
                # in 3.10+
                await agen.aclose()  # type: ignore
        except Exception:
            yield self.environment.handle_exception()

    def new_context(
        self,
        vars: t.Optional[t.Dict[str, t.Any]] = None,
        shared: bool = False,
        locals: t.Optional[t.Mapping[str, t.Any]] = None,
    ) -> Context:
        """Create a new :class:`Context` for this template.  The vars
        provided will be passed to the template.  Per default the globals
        are added to the context.  If shared is set to `True` the data
        is passed as is to the context without adding the globals.

        `locals` can be a dict of local variables for internal usage.
        """
        return new_context(
            self.environment, self.name, self.blocks, vars, shared, self.globals, locals
        )

    def make_module(
        self,
        vars: t.Optional[t.Dict[str, t.Any]] = None,
        shared: bool = False,
        locals: t.Optional[t.Mapping[str, t.Any]] = None,
    ) -> "TemplateModule":
        """This method works like the :attr:`module` attribute when called
        without arguments but it will evaluate the template on every call
        rather than caching it.  It's also possible to provide
        a dict which is then used as context.  The arguments are the same
        as for the :meth:`new_context` method.
        """
        ctx = self.new_context(vars, shared, locals)
        return TemplateModule(self, ctx)

    async def make_module_async(
        self,
        vars: t.Optional[t.Dict[str, t.Any]] = None,
        shared: bool = False,
        locals: t.Optional[t.Mapping[str, t.Any]] = None,
    ) -> "TemplateModule":
        """As template module creation can invoke template code for
        asynchronous executions this method must be used instead of the
        normal :meth:`make_module` one.  Likewise the module attribute
        becomes unavailable in async mode.
        """
        ctx = self.new_context(vars, shared, locals)
        return TemplateModule(
            self,
            ctx,
            [x async for x in self.root_render_func(ctx)],  # type: ignore
        )

    @internalcode
    def _get_default_module(self, ctx: t.Optional[Context] = None) -> "TemplateModule":
        """If a context is passed in, this means that the template was
        imported. Imported templates have access to the current
        template's globals by default, but they can only be accessed via
        the context during runtime.

        If there are new globals, we need to create a new module because
        the cached module is already rendered and will not have access
        to globals from the current context. This new module is not
        cached because the template can be imported elsewhere, and it
        should have access to only the current template's globals.
        """
        if self.environment.is_async:
            raise RuntimeError("Module is not available in async mode.")

        if ctx is not None:
            keys = ctx.globals_keys - self.globals.keys()

            if keys:
                return self.make_module({k: ctx.parent[k] for k in keys})

        if self._module is None:
            self._module = self.make_module()

        return self._module

    async def _get_default_module_async(
        self, ctx: t.Optional[Context] = None
    ) -> "TemplateModule":
        if ctx is not None:
            keys = ctx.globals_keys - self.globals.keys()

            if keys:
                return await self.make_module_async({k: ctx.parent[k] for k in keys})

        if self._module is None:
            self._module = await self.make_module_async()

        return self._module

    @property
    def module(self) -> "TemplateModule":
        """The template as module.  This is used for imports in the
        template runtime but is also useful if one wants to access
        exported template variables from the Python layer:

        >>> t = Template('{% macro foo() %}42{% endmacro %}23')
        >>> str(t.module)
        '23'
        >>> t.module.foo() == u'42'
        True

        This attribute is not available if async mode is enabled.
        """
        return self._get_default_module()

    def get_corresponding_lineno(self, lineno: int) -> int:
        """Return the source line number of a line number in the
        generated bytecode as they are not in sync.
        """
        for template_line, code_line in reversed(self.debug_info):
            if code_line <= lineno:
                return template_line
        return 1

    @property
    def is_up_to_date(self) -> bool:
        """If this variable is `False` there is a newer version available."""
        if self._uptodate is None:
            return True
        return self._uptodate()

    @property
    def debug_info(self) -> t.List[t.Tuple[int, int]]:
        """The debug info mapping."""
        if self._debug_info:
            return [
                tuple(map(int, x.split("=")))  # type: ignore
                for x in self._debug_info.split("&")
            ]

        return []

    def __repr__(self) -> str:
        if self.name is None:
            name = f"memory:{id(self):x}"
        else:
            name = repr(self.name)
        return f"<{type(self).__name__} {name}>"


class TemplateModule:
    """Represents an imported template.  All the exported names of the
    template are available as attributes on this object.  Additionally
    converting it into a string renders the contents.
    """

    def __init__(
        self,
        template: Template,
        context: Context,
        body_stream: t.Optional[t.Iterable[str]] = None,
    ) -> None:
        if body_stream is None:
            if context.environment.is_async:
                raise RuntimeError(
                    "Async mode requires a body stream to be passed to"
                    " a template module. Use the async methods of the"
                    " API you are using."
                )

            body_stream = list(template.root_render_func(context))

        self._body_stream = body_stream
        self.__dict__.update(context.get_exported())
        self.__name__ = template.name

    def __html__(self) -> Markup:
        return Markup(concat(self._body_stream))

    def __str__(self) -> str:
        return concat(self._body_stream)

    def __repr__(self) -> str:
        if self.__name__ is None:
            name = f"memory:{id(self):x}"
        else:
            name = repr(self.__name__)
        return f"<{type(self).__name__} {name}>"


class TemplateExpression:
    """The :meth:`jinja2.Environment.compile_expression` method returns an
    instance of this object.  It encapsulates the expression-like access
    to the template with an expression it wraps.
    """

    def __init__(self, template: Template, undefined_to_none: bool) -> None:
        self._template = template
        self._undefined_to_none = undefined_to_none

    def __call__(self, *args: t.Any, **kwargs: t.Any) -> t.Optional[t.Any]:
        context = self._template.new_context(dict(*args, **kwargs))
        consume(self._template.root_render_func(context))
        rv = context.vars["result"]
        if self._undefined_to_none and isinstance(rv, Undefined):
            rv = None
        return rv


class TemplateStream:
    """A template stream works pretty much like an ordinary python generator
    but it can buffer multiple items to reduce the number of total iterations.
    Per default the output is unbuffered which means that for every unbuffered
    instruction in the template one string is yielded.

    If buffering is enabled with a buffer size of 5, five items are combined
    into a new string.  This is mainly useful if you are streaming
    big templates to a client via WSGI which flushes after each iteration.
    """

    def __init__(self, gen: t.Iterator[str]) -> None:
        self._gen = gen
        self.disable_buffering()

    def dump(
        self,
        fp: t.Union[str, t.IO[bytes]],
        encoding: t.Optional[str] = None,
        errors: t.Optional[str] = "strict",
    ) -> None:
        """Dump the complete stream into a file or file-like object.
        Per default strings are written, if you want to encode
        before writing specify an `encoding`.

        Example usage::

            Template('Hello {{ name }}!').stream(name='foo').dump('hello.html')
        """
        close = False

        if isinstance(fp, str):
            if encoding is None:
                encoding = "utf-8"

            real_fp: t.IO[bytes] = open(fp, "wb")
            close = True
        else:
            real_fp = fp

        try:
            if encoding is not None:
                iterable = (x.encode(encoding, errors) for x in self)  # type: ignore
            else:
                iterable = self  # type: ignore

            if hasattr(real_fp, "writelines"):
                real_fp.writelines(iterable)
            else:
                for item in iterable:
                    real_fp.write(item)
        finally:
            if close:
                real_fp.close()

    def disable_buffering(self) -> None:
        """Disable the output buffering."""
        self._next = partial(next, self._gen)
        self.buffered = False

    def _buffered_generator(self, size: int) -> t.Iterator[str]:
        buf: t.List[str] = []
        c_size = 0
        push = buf.append

        while True:
            try:
                while c_size < size:
                    c = next(self._gen)
                    push(c)
                    if c:
                        c_size += 1
            except StopIteration:
                if not c_size:
                    return
            yield concat(buf)
            del buf[:]
            c_size = 0

    def enable_buffering(self, size: int = 5) -> None:
        """Enable buffering.  Buffer `size` items before yielding them."""
        if size <= 1:
            raise ValueError("buffer size too small")

        self.buffered = True
        self._next = partial(next, self._buffered_generator(size))

    def __iter__(self) -> "TemplateStream":
        return self

    def __next__(self) -> str:
        return self._next()  # type: ignore


# hook in default template class.  if anyone reads this comment: ignore that
# it's possible to use custom templates ;-)
Environment.template_class = Template

# === NexusCore/openenv\Lib\site-packages\litellm\types\llms\openai.py ===
from enum import Enum
from os import PathLike
from typing import IO, Any, Iterable, List, Literal, Mapping, Optional, Tuple, Union

import httpx
from openai._legacy_response import (
    HttpxBinaryResponseContent as _HttpxBinaryResponseContent,
)
from openai.lib.streaming._assistants import (
    AssistantEventHandler,
    AssistantStreamManager,
    AsyncAssistantEventHandler,
    AsyncAssistantStreamManager,
)
from openai.pagination import AsyncCursorPage, SyncCursorPage
from openai.types import Batch, EmbeddingCreateParams, FileObject
from openai.types.beta.assistant import Assistant
from openai.types.beta.assistant_tool_param import AssistantToolParam
from openai.types.beta.thread_create_params import (
    Message as OpenAICreateThreadParamsMessage,
)
from openai.types.beta.threads.message import Message as OpenAIMessage
from openai.types.beta.threads.message_content import MessageContent
from openai.types.beta.threads.run import Run
from openai.types.chat import ChatCompletionChunk
from openai.types.chat.chat_completion_audio_param import ChatCompletionAudioParam
from openai.types.chat.chat_completion_content_part_input_audio_param import (
    ChatCompletionContentPartInputAudioParam,
)
from openai.types.chat.chat_completion_modality import ChatCompletionModality
from openai.types.chat.chat_completion_prediction_content_param import (
    ChatCompletionPredictionContentParam,
)
from openai.types.embedding import Embedding as OpenAIEmbedding
from openai.types.fine_tuning.fine_tuning_job import FineTuningJob
from openai.types.responses.response import (
    IncompleteDetails,
    Response,
    ResponseOutputItem,
    ResponseTextConfig,
    Tool,
    ToolChoice,
)
from openai.types.responses.response_create_params import (
    Reasoning,
    ResponseIncludable,
    ResponseInputParam,
    ResponseTextConfigParam,
    ToolChoice,
    ToolParam,
)
from openai.types.responses.response_function_tool_call import ResponseFunctionToolCall
from pydantic import BaseModel, ConfigDict, Discriminator, Field, PrivateAttr
from typing_extensions import Annotated, Dict, Required, TypedDict, override

from litellm.types.llms.base import BaseLiteLLMOpenAIResponseObject
from litellm.types.responses.main import (
    GenericResponseOutputItem,
    OutputFunctionToolCall,
)

FileContent = Union[IO[bytes], bytes, PathLike]

FileTypes = Union[
    # file (or bytes)
    FileContent,
    # (filename, file (or bytes))
    Tuple[Optional[str], FileContent],
    # (filename, file (or bytes), content_type)
    Tuple[Optional[str], FileContent, Optional[str]],
    # (filename, file (or bytes), content_type, headers)
    Tuple[Optional[str], FileContent, Optional[str], Mapping[str, str]],
]


EmbeddingInput = Union[str, List[str]]


class HttpxBinaryResponseContent(_HttpxBinaryResponseContent):
    _hidden_params: dict = {}
    pass


class NotGiven:
    """
    A sentinel singleton class used to distinguish omitted keyword arguments
    from those passed in with the value None (which may have different behavior).

    For example:

    ```py
    def get(timeout: Union[int, NotGiven, None] = NotGiven()) -> Response:
        ...


    get(timeout=1)  # 1s timeout
    get(timeout=None)  # No timeout
    get()  # Default timeout behavior, which may not be statically known at the method definition.
    ```
    """

    def __bool__(self) -> Literal[False]:
        return False

    @override
    def __repr__(self) -> str:
        return "NOT_GIVEN"


NOT_GIVEN = NotGiven()


class ToolResourcesCodeInterpreter(TypedDict, total=False):
    file_ids: List[str]
    """
    A list of [file](https://platform.openai.com/docs/api-reference/files) IDs made
    available to the `code_interpreter` tool. There can be a maximum of 20 files
    associated with the tool.
    """


class ToolResourcesFileSearchVectorStore(TypedDict, total=False):
    file_ids: List[str]
    """
    A list of [file](https://platform.openai.com/docs/api-reference/files) IDs to
    add to the vector store. There can be a maximum of 10000 files in a vector
    store.
    """

    metadata: object
    """Set of 16 key-value pairs that can be attached to a vector store.

    This can be useful for storing additional information about the vector store in
    a structured format. Keys can be a maximum of 64 characters long and values can
    be a maxium of 512 characters long.
    """


class ToolResourcesFileSearch(TypedDict, total=False):
    vector_store_ids: List[str]
    """
    The
    [vector store](https://platform.openai.com/docs/api-reference/vector-stores/object)
    attached to this thread. There can be a maximum of 1 vector store attached to
    the thread.
    """

    vector_stores: Iterable[ToolResourcesFileSearchVectorStore]
    """
    A helper to create a
    [vector store](https://platform.openai.com/docs/api-reference/vector-stores/object)
    with file_ids and attach it to this thread. There can be a maximum of 1 vector
    store attached to the thread.
    """


class OpenAICreateThreadParamsToolResources(TypedDict, total=False):
    code_interpreter: ToolResourcesCodeInterpreter

    file_search: ToolResourcesFileSearch


class FileSearchToolParam(TypedDict, total=False):
    type: Required[Literal["file_search"]]
    """The type of tool being defined: `file_search`"""


class CodeInterpreterToolParam(TypedDict, total=False):
    type: Required[Literal["code_interpreter"]]
    """The type of tool being defined: `code_interpreter`"""


AttachmentTool = Union[CodeInterpreterToolParam, FileSearchToolParam]


class Attachment(TypedDict, total=False):
    file_id: str
    """The ID of the file to attach to the message."""

    tools: Iterable[AttachmentTool]
    """The tools to add this file to."""


class ImageFileObject(TypedDict):
    file_id: Required[str]
    detail: Optional[str]


class ImageURLObject(TypedDict):
    url: Required[str]
    detail: Optional[str]


class MessageContentTextObject(TypedDict):
    type: Required[Literal["text"]]
    text: str


class MessageContentImageFileObject(TypedDict):
    type: Literal["image_file"]
    image_file: ImageFileObject


class MessageContentImageURLObject(TypedDict):
    type: Required[str]
    image_url: ImageURLObject


class MessageData(TypedDict):
    role: Literal["user", "assistant"]
    content: Union[
        str,
        List[
            Union[
                MessageContentTextObject,
                MessageContentImageFileObject,
                MessageContentImageURLObject,
            ]
        ],
    ]
    attachments: Optional[List[Attachment]]
    metadata: Optional[dict]


class Thread(BaseModel):
    id: str
    """The identifier, which can be referenced in API endpoints."""

    created_at: int
    """The Unix timestamp (in seconds) for when the thread was created."""

    metadata: Optional[object] = None
    """Set of 16 key-value pairs that can be attached to an object.

    This can be useful for storing additional information about the object in a
    structured format. Keys can be a maximum of 64 characters long and values can be
    a maxium of 512 characters long.
    """

    object: Literal["thread"]
    """The object type, which is always `thread`."""


OpenAICreateFileRequestOptionalParams = Literal["purpose"]

OpenAIFilesPurpose = Literal[
    "assistants",
    "assistants_output",
    "batch",
    "batch_output",
    "fine-tune",
    "fine-tune-results",
    "vision",
    "user_data",
]


class OpenAIFileObject(BaseModel):
    id: str
    """The file identifier, which can be referenced in the API endpoints."""

    bytes: int
    """The size of the file, in bytes."""

    created_at: int
    """The Unix timestamp (in seconds) for when the file was created."""

    filename: str
    """The name of the file."""

    object: Literal["file"]
    """The object type, which is always `file`."""

    purpose: OpenAIFilesPurpose
    """The intended purpose of the file.

    Supported values are `assistants`, `assistants_output`, `batch`, `batch_output`,
    `fine-tune`, `fine-tune-results`, `vision`, and `user_data`.
    """

    status: Literal["uploaded", "processed", "error"]
    """Deprecated.

    The current status of the file, which can be either `uploaded`, `processed`, or
    `error`.
    """

    expires_at: Optional[int] = None
    """The Unix timestamp (in seconds) for when the file will expire."""

    status_details: Optional[str] = None
    """Deprecated.

    For details on why a fine-tuning training file failed validation, see the
    `error` field on `fine_tuning.job`.
    """

    _hidden_params: dict = {"response_cost": 0.0}  # no cost for writing a file

    def __contains__(self, key):
        # Define custom behavior for the 'in' operator
        return hasattr(self, key)

    def get(self, key, default=None):
        # Custom .get() method to access attributes with a default value if the attribute doesn't exist
        return getattr(self, key, default)

    def __getitem__(self, key):
        # Allow dictionary-style access to attributes
        return getattr(self, key)

    def json(self, **kwargs):  # type: ignore
        try:
            return self.model_dump()  # noqa
        except Exception:
            # if using pydantic v1
            return self.dict()


CREATE_FILE_REQUESTS_PURPOSE = Literal["assistants", "batch", "fine-tune"]


# OpenAI Files Types
class CreateFileRequest(TypedDict, total=False):
    """
    CreateFileRequest
    Used by Assistants API, Batches API, and Fine-Tunes API

    Required Params:
        file: FileTypes
        purpose: Literal['assistants', 'batch', 'fine-tune']

    Optional Params:
        extra_headers: Optional[Dict[str, str]]
        extra_body: Optional[Dict[str, str]] = None
        timeout: Optional[float] = None
    """

    file: Required[FileTypes]
    purpose: Required[CREATE_FILE_REQUESTS_PURPOSE]
    extra_headers: Optional[Dict[str, str]]
    extra_body: Optional[Dict[str, str]]
    timeout: Optional[float]


class FileContentRequest(TypedDict, total=False):
    """
    FileContentRequest
    Used by Assistants API, Batches API, and Fine-Tunes API

    Required Params:
        file_id: str

    Optional Params:
        extra_headers: Optional[Dict[str, str]]
        extra_body: Optional[Dict[str, str]] = None
        timeout: Optional[float] = None
    """

    file_id: str
    extra_headers: Optional[Dict[str, str]]
    extra_body: Optional[Dict[str, str]]
    timeout: Optional[float]


# OpenAI Batches Types
class CreateBatchRequest(TypedDict, total=False):
    """
    CreateBatchRequest
    """

    completion_window: Literal["24h"]
    endpoint: Literal["/v1/chat/completions", "/v1/embeddings", "/v1/completions"]
    input_file_id: str
    metadata: Optional[Dict[str, str]]
    extra_headers: Optional[Dict[str, str]]
    extra_body: Optional[Dict[str, str]]
    timeout: Optional[float]


class LiteLLMBatchCreateRequest(CreateBatchRequest, total=False):
    model: str


class RetrieveBatchRequest(TypedDict, total=False):
    """
    RetrieveBatchRequest
    """

    batch_id: str
    extra_headers: Optional[Dict[str, str]]
    extra_body: Optional[Dict[str, str]]
    timeout: Optional[float]


class CancelBatchRequest(TypedDict, total=False):
    """
    CancelBatchRequest
    """

    batch_id: str
    extra_headers: Optional[Dict[str, str]]
    extra_body: Optional[Dict[str, str]]
    timeout: Optional[float]


class ListBatchRequest(TypedDict, total=False):
    """
    ListBatchRequest - List your organization's batches
    Calls https://api.openai.com/v1/batches
    """

    after: Union[str, NotGiven]
    limit: Union[int, NotGiven]
    extra_headers: Optional[Dict[str, str]]
    extra_body: Optional[Dict[str, str]]
    timeout: Optional[float]


BatchJobStatus = Literal[
    "validating",
    "failed",
    "in_progress",
    "finalizing",
    "completed",
    "expired",
    "cancelling",
    "cancelled",
]


class ChatCompletionAudioDelta(TypedDict, total=False):
    data: str
    transcript: str
    expires_at: int
    id: str


class ChatCompletionToolCallFunctionChunk(TypedDict, total=False):
    name: Optional[str]
    arguments: str


class ChatCompletionAssistantToolCall(TypedDict):
    id: Optional[str]
    type: Literal["function"]
    function: ChatCompletionToolCallFunctionChunk


class ChatCompletionToolCallChunk(TypedDict):  # result of /chat/completions call
    id: Optional[str]
    type: Literal["function"]
    function: ChatCompletionToolCallFunctionChunk
    index: int


class ChatCompletionDeltaToolCallChunk(TypedDict, total=False):
    id: str
    type: Literal["function"]
    function: ChatCompletionToolCallFunctionChunk
    index: int


class ChatCompletionCachedContent(TypedDict):
    type: Literal["ephemeral"]


class ChatCompletionThinkingBlock(TypedDict, total=False):
    type: Required[Literal["thinking"]]
    thinking: str
    signature: str
    cache_control: Optional[Union[dict, ChatCompletionCachedContent]]


class ChatCompletionRedactedThinkingBlock(TypedDict, total=False):
    type: Required[Literal["redacted_thinking"]]
    data: str
    cache_control: Optional[Union[dict, ChatCompletionCachedContent]]


class WebSearchOptionsUserLocationApproximate(TypedDict, total=False):
    city: str
    """Free text input for the city of the user, e.g. `San Francisco`."""

    country: str
    """
    The two-letter [ISO country code](https://en.wikipedia.org/wiki/ISO_3166-1) of
    the user, e.g. `US`.
    """

    region: str
    """Free text input for the region of the user, e.g. `California`."""

    timezone: str
    """
    The [IANA timezone](https://timeapi.io/documentation/iana-timezones) of the
    user, e.g. `America/Los_Angeles`.
    """


class WebSearchOptionsUserLocation(TypedDict, total=False):
    approximate: Required[WebSearchOptionsUserLocationApproximate]
    """Approximate location parameters for the search."""

    type: Required[Literal["approximate"]]
    """The type of location approximation. Always `approximate`."""


class WebSearchOptions(TypedDict, total=False):
    search_context_size: Literal["low", "medium", "high"]
    """
    High level guidance for the amount of context window space to use for the
    search. One of `low`, `medium`, or `high`. `medium` is the default.
    """

    user_location: Optional[WebSearchOptionsUserLocation]
    """Approximate location parameters for the search."""


class FileSearchTool(TypedDict, total=False):
    type: Literal["file_search"]
    """The type of tool being defined: `file_search`"""

    vector_store_ids: Optional[List[str]]
    """The IDs of the vector stores to search."""


class ChatCompletionAnnotationURLCitation(TypedDict, total=False):
    end_index: int
    """The index of the last character of the URL citation in the message."""

    start_index: int
    """The index of the first character of the URL citation in the message."""

    title: str
    """The title of the web resource."""

    url: str
    """The URL of the web resource."""


class ChatCompletionAnnotation(TypedDict, total=False):
    type: Literal["url_citation"]
    """The type of the URL citation. Always `url_citation`."""

    url_citation: ChatCompletionAnnotationURLCitation
    """A URL citation when using web search."""


class OpenAIChatCompletionTextObject(TypedDict):
    type: Literal["text"]
    text: str


class ChatCompletionTextObject(
    OpenAIChatCompletionTextObject, total=False
):  # litellm wrapper on top of openai object for handling cached content
    cache_control: ChatCompletionCachedContent


class ChatCompletionImageUrlObject(TypedDict, total=False):
    url: Required[str]
    detail: str
    format: str


class ChatCompletionImageObject(TypedDict):
    type: Literal["image_url"]
    image_url: Union[str, ChatCompletionImageUrlObject]


class ChatCompletionVideoUrlObject(TypedDict, total=False):
    url: Required[str]
    detail: str


class ChatCompletionVideoObject(TypedDict):
    type: Literal["video_url"]
    video_url: Union[str, ChatCompletionVideoUrlObject]


class ChatCompletionAudioObject(ChatCompletionContentPartInputAudioParam):
    pass


class DocumentObject(TypedDict):
    type: Literal["text"]
    media_type: str
    data: str


class CitationsObject(TypedDict):
    enabled: bool


class ChatCompletionDocumentObject(TypedDict):
    type: Literal["document"]
    source: DocumentObject
    title: str
    context: str
    citations: Optional[CitationsObject]


class ChatCompletionFileObjectFile(TypedDict, total=False):
    file_data: str
    file_id: str
    filename: str
    format: str


class ChatCompletionFileObject(TypedDict):
    type: Literal["file"]
    file: ChatCompletionFileObjectFile


OpenAIMessageContentListBlock = Union[
    ChatCompletionTextObject,
    ChatCompletionImageObject,
    ChatCompletionAudioObject,
    ChatCompletionDocumentObject,
    ChatCompletionVideoObject,
    ChatCompletionFileObject,
]

OpenAIMessageContent = Union[
    str,
    Iterable[OpenAIMessageContentListBlock],
]

# The prompt(s) to generate completions for, encoded as a string, array of strings, array of tokens, or array of token arrays.
AllPromptValues = Union[str, List[str], Iterable[int], Iterable[Iterable[int]], None]


class OpenAIChatCompletionUserMessage(TypedDict):
    role: Literal["user"]
    content: OpenAIMessageContent


class OpenAITextCompletionUserMessage(TypedDict):
    role: Literal["user"]
    content: AllPromptValues


class ChatCompletionUserMessage(OpenAIChatCompletionUserMessage, total=False):
    cache_control: ChatCompletionCachedContent


class OpenAIChatCompletionAssistantMessage(TypedDict, total=False):
    role: Required[Literal["assistant"]]
    content: Optional[
        Union[
            str, Iterable[Union[ChatCompletionTextObject, ChatCompletionThinkingBlock]]
        ]
    ]
    name: Optional[str]
    tool_calls: Optional[List[ChatCompletionAssistantToolCall]]
    function_call: Optional[ChatCompletionToolCallFunctionChunk]
    reasoning_content: Optional[str]


class ChatCompletionAssistantMessage(OpenAIChatCompletionAssistantMessage, total=False):
    cache_control: ChatCompletionCachedContent
    thinking_blocks: Optional[List[ChatCompletionThinkingBlock]]


class ChatCompletionToolMessage(TypedDict):
    role: Literal["tool"]
    content: Union[str, Iterable[ChatCompletionTextObject]]
    tool_call_id: str


class ChatCompletionFunctionMessage(TypedDict):
    role: Literal["function"]
    content: Optional[Union[str, Iterable[ChatCompletionTextObject]]]
    name: str
    tool_call_id: Optional[str]


class OpenAIChatCompletionSystemMessage(TypedDict, total=False):
    role: Required[Literal["system"]]
    content: Required[Union[str, List]]
    name: str


class OpenAIChatCompletionDeveloperMessage(TypedDict, total=False):
    role: Required[Literal["developer"]]
    content: Required[Union[str, List]]
    name: str


class ChatCompletionSystemMessage(OpenAIChatCompletionSystemMessage, total=False):
    cache_control: ChatCompletionCachedContent


class ChatCompletionDeveloperMessage(OpenAIChatCompletionDeveloperMessage, total=False):
    cache_control: ChatCompletionCachedContent


class GenericChatCompletionMessage(TypedDict, total=False):
    role: Required[str]
    content: Required[Union[str, List]]


ValidUserMessageContentTypes = [
    "text",
    "image_url",
    "input_audio",
    "document",
    "video_url",
    "file",
]  # used for validating user messages. Prevent users from accidentally sending anthropic messages.

AllMessageValues = Union[
    ChatCompletionUserMessage,
    ChatCompletionAssistantMessage,
    ChatCompletionToolMessage,
    ChatCompletionSystemMessage,
    ChatCompletionFunctionMessage,
    ChatCompletionDeveloperMessage,
]


class ChatCompletionToolChoiceFunctionParam(TypedDict):
    name: str


class ChatCompletionToolChoiceObjectParam(TypedDict):
    type: Literal["function"]
    function: ChatCompletionToolChoiceFunctionParam


ChatCompletionToolChoiceStringValues = Literal["none", "auto", "required"]

ChatCompletionToolChoiceValues = Union[
    ChatCompletionToolChoiceStringValues, ChatCompletionToolChoiceObjectParam
]


class ChatCompletionToolParamFunctionChunk(TypedDict, total=False):
    name: Required[str]
    description: str
    parameters: dict
    strict: bool


class OpenAIChatCompletionToolParam(TypedDict):
    type: Union[Literal["function"], str]
    function: ChatCompletionToolParamFunctionChunk


class ChatCompletionToolParam(OpenAIChatCompletionToolParam, total=False):
    cache_control: ChatCompletionCachedContent


class Function(TypedDict, total=False):
    name: Required[str]
    """The name of the function to call."""


class ChatCompletionNamedToolChoiceParam(TypedDict, total=False):
    function: Required[Function]

    type: Required[Literal["function"]]
    """The type of the tool. Currently, only `function` is supported."""


class ChatCompletionRequest(TypedDict, total=False):
    model: Required[str]
    messages: Required[List[AllMessageValues]]
    frequency_penalty: float
    logit_bias: dict
    logprobs: bool
    top_logprobs: int
    max_tokens: int
    n: int
    presence_penalty: float
    response_format: dict
    seed: int
    service_tier: str
    stop: Union[str, List[str]]
    stream_options: dict
    temperature: float
    top_p: float
    tools: List[ChatCompletionToolParam]
    tool_choice: ChatCompletionToolChoiceValues
    parallel_tool_calls: bool
    function_call: Union[str, dict]
    functions: List
    user: str
    metadata: dict  # litellm specific param


class ChatCompletionDeltaChunk(TypedDict, total=False):
    content: Optional[str]
    tool_calls: List[ChatCompletionDeltaToolCallChunk]
    role: str


ChatCompletionAssistantContentValue = (
    str  # keep as var, used in stream_chunk_builder as well
)


class ChatCompletionResponseMessage(TypedDict, total=False):
    content: Optional[ChatCompletionAssistantContentValue]
    tool_calls: Optional[List[ChatCompletionToolCallChunk]]
    role: Literal["assistant"]
    function_call: Optional[ChatCompletionToolCallFunctionChunk]
    provider_specific_fields: Optional[dict]
    reasoning_content: Optional[str]
    thinking_blocks: Optional[
        List[Union[ChatCompletionThinkingBlock, ChatCompletionRedactedThinkingBlock]]
    ]


class ChatCompletionUsageBlock(TypedDict, total=False):
    prompt_tokens: Required[int]
    completion_tokens: Required[int]
    total_tokens: Required[int]
    prompt_tokens_details: Optional[dict]
    completion_tokens_details: Optional[dict]


class OpenAIChatCompletionChunk(ChatCompletionChunk):
    def __init__(self, **kwargs):
        # Set the 'object' kwarg to 'chat.completion.chunk'
        kwargs["object"] = "chat.completion.chunk"
        super().__init__(**kwargs)


class Hyperparameters(BaseModel):
    batch_size: Optional[Union[str, int]] = None  # "Number of examples in each batch."
    learning_rate_multiplier: Optional[Union[str, float]] = (
        None  # Scaling factor for the learning rate
    )
    n_epochs: Optional[Union[str, int]] = (
        None  # "The number of epochs to train the model for"
    )


class FineTuningJobCreate(BaseModel):
    """
    FineTuningJobCreate - Create a fine-tuning job

    Example Request
    ```
    {
        "model": "gpt-3.5-turbo",
        "training_file": "file-abc123",
        "hyperparameters": {
            "batch_size": "auto",
            "learning_rate_multiplier": 0.1,
            "n_epochs": 3
        },
        "suffix": "custom-model-name",
        "validation_file": "file-xyz789",
        "integrations": ["slack"],
        "seed": 42
    }
    ```
    """

    model: str  # "The name of the model to fine-tune."
    training_file: str  # "The ID of an uploaded file that contains training data."
    hyperparameters: Optional[Hyperparameters] = (
        None  # "The hyperparameters used for the fine-tuning job."
    )
    suffix: Optional[str] = (
        None  # "A string of up to 18 characters that will be added to your fine-tuned model name."
    )
    validation_file: Optional[str] = (
        None  # "The ID of an uploaded file that contains validation data."
    )
    integrations: Optional[List[str]] = (
        None  # "A list of integrations to enable for your fine-tuning job."
    )
    seed: Optional[int] = None  # "The seed controls the reproducibility of the job."


class LiteLLMFineTuningJobCreate(FineTuningJobCreate):
    custom_llm_provider: Optional[Literal["openai", "azure", "vertex_ai"]] = None

    model_config = {
        "extra": "allow"
    }  # This allows the model to accept additional fields


AllEmbeddingInputValues = Union[str, List[str], List[int], List[List[int]]]

OpenAIAudioTranscriptionOptionalParams = Literal[
    "language",
    "prompt",
    "temperature",
    "response_format",
    "timestamp_granularities",
    "include",
]


OpenAIImageVariationOptionalParams = Literal["n", "size", "response_format", "user"]


OpenAIImageGenerationOptionalParams = Literal[
    "background",
    "moderation",
    "n",
    "output_compression",
    "output_format",
    "quality",
    "response_format",
    "size",
    "style",
    "user",
]


class ComputerToolParam(TypedDict, total=False):
    display_height: Required[float]
    """The height of the computer display."""

    display_width: Required[float]
    """The width of the computer display."""

    environment: Required[Union[Literal["mac", "windows", "ubuntu", "browser"], str]]
    """The type of computer environment to control."""

    type: Required[Union[Literal["computer_use_preview"], str]]


ALL_RESPONSES_API_TOOL_PARAMS = Union[ToolParam, ComputerToolParam]


class PromptObject(TypedDict, total=False):
    """Reference to a stored prompt template."""

    id: Required[str]
    """The unique identifier of the prompt template to use."""

    variables: Optional[Dict]
    """Variables to substitute into the prompt template."""

    version: Optional[str]
    """Optional version of the prompt template."""


class ResponsesAPIOptionalRequestParams(TypedDict, total=False):
    """TypedDict for Optional parameters supported by the responses API."""

    include: Optional[List[ResponseIncludable]]
    instructions: Optional[str]
    max_output_tokens: Optional[int]
    metadata: Optional[Dict[str, Any]]
    parallel_tool_calls: Optional[bool]
    previous_response_id: Optional[str]
    reasoning: Optional[Reasoning]
    store: Optional[bool]
    background: Optional[bool]
    stream: Optional[bool]
    temperature: Optional[float]
    text: Optional[ResponseTextConfigParam]
    tool_choice: Optional[ToolChoice]
    tools: Optional[List[ALL_RESPONSES_API_TOOL_PARAMS]]
    top_p: Optional[float]
    truncation: Optional[Literal["auto", "disabled"]]
    user: Optional[str]
    prompt: Optional[PromptObject]


class ResponsesAPIRequestParams(ResponsesAPIOptionalRequestParams, total=False):
    """TypedDict for request parameters supported by the responses API."""

    input: Union[str, ResponseInputParam]
    model: str


class OutputTokensDetails(BaseLiteLLMOpenAIResponseObject):
    reasoning_tokens: Optional[int] = None

    text_tokens: Optional[int] = None

    model_config = {"extra": "allow"}


class InputTokensDetails(BaseLiteLLMOpenAIResponseObject):
    audio_tokens: Optional[int] = None
    cached_tokens: Optional[int] = None
    text_tokens: Optional[int] = None

    model_config = {"extra": "allow"}


class ResponseAPIUsage(BaseLiteLLMOpenAIResponseObject):
    input_tokens: int
    """The number of input tokens."""

    input_tokens_details: Optional[InputTokensDetails] = None
    """A detailed breakdown of the input tokens."""

    output_tokens: int
    """The number of output tokens."""

    output_tokens_details: Optional[OutputTokensDetails] = None
    """A detailed breakdown of the output tokens."""

    total_tokens: int
    """The total number of tokens used."""

    model_config = {"extra": "allow"}


class ResponsesAPIResponse(BaseLiteLLMOpenAIResponseObject):
    id: str
    created_at: float
    error: Optional[dict]
    incomplete_details: Optional[IncompleteDetails]
    instructions: Optional[str]
    metadata: Optional[Dict]
    model: Optional[str]
    object: Optional[str]
    output: Union[
        List[Union[ResponseOutputItem, Dict]],
        List[Union[GenericResponseOutputItem, OutputFunctionToolCall]],
    ]
    parallel_tool_calls: bool
    temperature: Optional[float]
    tool_choice: ToolChoice
    tools: Union[List[Tool], List[ResponseFunctionToolCall]]
    top_p: Optional[float]
    max_output_tokens: Optional[int]
    previous_response_id: Optional[str]
    reasoning: Optional[Reasoning]
    status: Optional[str]
    text: Optional[ResponseTextConfig]
    truncation: Optional[Literal["auto", "disabled"]]
    usage: Optional[ResponseAPIUsage]
    user: Optional[str]
    # Define private attributes using PrivateAttr
    _hidden_params: dict = PrivateAttr(default_factory=dict)


class ResponsesAPIStreamEvents(str, Enum):
    """
    Enum representing all supported OpenAI stream event types for the Responses API.

    Inherits from str to allow direct string comparison and usage as dictionary keys.
    """

    # Response lifecycle events
    RESPONSE_CREATED = "response.created"
    RESPONSE_IN_PROGRESS = "response.in_progress"
    RESPONSE_COMPLETED = "response.completed"
    RESPONSE_FAILED = "response.failed"
    RESPONSE_INCOMPLETE = "response.incomplete"

    # Part added
    RESPONSE_PART_ADDED = "response.reasoning_summary_part.added"

    # Output item events
    OUTPUT_ITEM_ADDED = "response.output_item.added"
    OUTPUT_ITEM_DONE = "response.output_item.done"

    # Content part events
    CONTENT_PART_ADDED = "response.content_part.added"
    CONTENT_PART_DONE = "response.content_part.done"

    # Output text events
    OUTPUT_TEXT_DELTA = "response.output_text.delta"
    OUTPUT_TEXT_ANNOTATION_ADDED = "response.output_text.annotation.added"
    OUTPUT_TEXT_DONE = "response.output_text.done"

    # Refusal events
    REFUSAL_DELTA = "response.refusal.delta"
    REFUSAL_DONE = "response.refusal.done"

    # Function call events
    FUNCTION_CALL_ARGUMENTS_DELTA = "response.function_call_arguments.delta"
    FUNCTION_CALL_ARGUMENTS_DONE = "response.function_call_arguments.done"

    # File search events
    FILE_SEARCH_CALL_IN_PROGRESS = "response.file_search_call.in_progress"
    FILE_SEARCH_CALL_SEARCHING = "response.file_search_call.searching"
    FILE_SEARCH_CALL_COMPLETED = "response.file_search_call.completed"

    # Web search events
    WEB_SEARCH_CALL_IN_PROGRESS = "response.web_search_call.in_progress"
    WEB_SEARCH_CALL_SEARCHING = "response.web_search_call.searching"
    WEB_SEARCH_CALL_COMPLETED = "response.web_search_call.completed"

    # Error event
    ERROR = "error"


class ResponseCreatedEvent(BaseLiteLLMOpenAIResponseObject):
    type: Literal[ResponsesAPIStreamEvents.RESPONSE_CREATED]
    response: ResponsesAPIResponse


class ResponseInProgressEvent(BaseLiteLLMOpenAIResponseObject):
    type: Literal[ResponsesAPIStreamEvents.RESPONSE_IN_PROGRESS]
    response: ResponsesAPIResponse


class ResponseCompletedEvent(BaseLiteLLMOpenAIResponseObject):
    type: Literal[ResponsesAPIStreamEvents.RESPONSE_COMPLETED]
    response: ResponsesAPIResponse
    _hidden_params: dict = PrivateAttr(default_factory=dict)


class ResponseFailedEvent(BaseLiteLLMOpenAIResponseObject):
    type: Literal[ResponsesAPIStreamEvents.RESPONSE_FAILED]
    response: ResponsesAPIResponse


class ResponseIncompleteEvent(BaseLiteLLMOpenAIResponseObject):
    type: Literal[ResponsesAPIStreamEvents.RESPONSE_INCOMPLETE]
    response: ResponsesAPIResponse


class OutputItemAddedEvent(BaseLiteLLMOpenAIResponseObject):
    type: Literal[ResponsesAPIStreamEvents.OUTPUT_ITEM_ADDED]
    output_index: int
    item: dict


class OutputItemDoneEvent(BaseLiteLLMOpenAIResponseObject):
    type: Literal[ResponsesAPIStreamEvents.OUTPUT_ITEM_DONE]
    output_index: int
    item: dict


class ContentPartAddedEvent(BaseLiteLLMOpenAIResponseObject):
    type: Literal[ResponsesAPIStreamEvents.CONTENT_PART_ADDED]
    item_id: str
    output_index: int
    content_index: int
    part: dict


class ContentPartDoneEvent(BaseLiteLLMOpenAIResponseObject):
    type: Literal[ResponsesAPIStreamEvents.CONTENT_PART_DONE]
    item_id: str
    output_index: int
    content_index: int
    part: dict


class OutputTextDeltaEvent(BaseLiteLLMOpenAIResponseObject):
    type: Literal[ResponsesAPIStreamEvents.OUTPUT_TEXT_DELTA]
    item_id: str
    output_index: int
    content_index: int
    delta: str


class OutputTextAnnotationAddedEvent(BaseLiteLLMOpenAIResponseObject):
    type: Literal[ResponsesAPIStreamEvents.OUTPUT_TEXT_ANNOTATION_ADDED]
    item_id: str
    output_index: int
    content_index: int
    annotation_index: int
    annotation: dict


class OutputTextDoneEvent(BaseLiteLLMOpenAIResponseObject):
    type: Literal[ResponsesAPIStreamEvents.OUTPUT_TEXT_DONE]
    item_id: str
    output_index: int
    content_index: int
    text: str


class RefusalDeltaEvent(BaseLiteLLMOpenAIResponseObject):
    type: Literal[ResponsesAPIStreamEvents.REFUSAL_DELTA]
    item_id: str
    output_index: int
    content_index: int
    delta: str


class RefusalDoneEvent(BaseLiteLLMOpenAIResponseObject):
    type: Literal[ResponsesAPIStreamEvents.REFUSAL_DONE]
    item_id: str
    output_index: int
    content_index: int
    refusal: str


class FunctionCallArgumentsDeltaEvent(BaseLiteLLMOpenAIResponseObject):
    type: Literal[ResponsesAPIStreamEvents.FUNCTION_CALL_ARGUMENTS_DELTA]
    item_id: str
    output_index: int
    delta: str


class FunctionCallArgumentsDoneEvent(BaseLiteLLMOpenAIResponseObject):
    type: Literal[ResponsesAPIStreamEvents.FUNCTION_CALL_ARGUMENTS_DONE]
    item_id: str
    output_index: int
    arguments: str


class FileSearchCallInProgressEvent(BaseLiteLLMOpenAIResponseObject):
    type: Literal[ResponsesAPIStreamEvents.FILE_SEARCH_CALL_IN_PROGRESS]
    output_index: int
    item_id: str


class FileSearchCallSearchingEvent(BaseLiteLLMOpenAIResponseObject):
    type: Literal[ResponsesAPIStreamEvents.FILE_SEARCH_CALL_SEARCHING]
    output_index: int
    item_id: str


class FileSearchCallCompletedEvent(BaseLiteLLMOpenAIResponseObject):
    type: Literal[ResponsesAPIStreamEvents.FILE_SEARCH_CALL_COMPLETED]
    output_index: int
    item_id: str


class WebSearchCallInProgressEvent(BaseLiteLLMOpenAIResponseObject):
    type: Literal[ResponsesAPIStreamEvents.WEB_SEARCH_CALL_IN_PROGRESS]
    output_index: int
    item_id: str


class WebSearchCallSearchingEvent(BaseLiteLLMOpenAIResponseObject):
    type: Literal[ResponsesAPIStreamEvents.WEB_SEARCH_CALL_SEARCHING]
    output_index: int
    item_id: str


class WebSearchCallCompletedEvent(BaseLiteLLMOpenAIResponseObject):
    type: Literal[ResponsesAPIStreamEvents.WEB_SEARCH_CALL_COMPLETED]
    output_index: int
    item_id: str


class ErrorEvent(BaseLiteLLMOpenAIResponseObject):
    type: Literal[ResponsesAPIStreamEvents.ERROR]
    code: Optional[str]
    message: str
    param: Optional[str]


class GenericEvent(BaseLiteLLMOpenAIResponseObject):
    type: str

    model_config = ConfigDict(extra="allow", protected_namespaces=())


# Union type for all possible streaming responses
ResponsesAPIStreamingResponse = Annotated[
    Union[
        ResponseCreatedEvent,
        ResponseInProgressEvent,
        ResponseCompletedEvent,
        ResponseFailedEvent,
        ResponseIncompleteEvent,
        OutputItemAddedEvent,
        OutputItemDoneEvent,
        ContentPartAddedEvent,
        ContentPartDoneEvent,
        OutputTextDeltaEvent,
        OutputTextAnnotationAddedEvent,
        OutputTextDoneEvent,
        RefusalDeltaEvent,
        RefusalDoneEvent,
        FunctionCallArgumentsDeltaEvent,
        FunctionCallArgumentsDoneEvent,
        FileSearchCallInProgressEvent,
        FileSearchCallSearchingEvent,
        FileSearchCallCompletedEvent,
        WebSearchCallInProgressEvent,
        WebSearchCallSearchingEvent,
        WebSearchCallCompletedEvent,
        ErrorEvent,
        GenericEvent,
    ],
    Discriminator("type"),
]


REASONING_EFFORT = Literal["low", "medium", "high"]


class OpenAIRealtimeStreamSession(TypedDict, total=False):
    id: Required[str]
    """
    Unique identifier for the session that looks like sess_1234567890abcdef.
    """

    input_audio_format: str
    """
    The format of input audio. Options are pcm16, g711_ulaw, or g711_alaw. For pcm16, input audio must be 16-bit PCM at a 24kHz sample rate, single channel (mono), and little-endian byte order.
    """

    input_audio_noise_reduction: object
    """
    Configuration for input audio noise reduction. This can be set to null to turn off. Noise reduction filters audio added to the input audio buffer before it is sent to VAD and the model. Filtering the audio can improve VAD and turn detection accuracy (reducing false positives) and model performance by improving perception of the input audio.
    """

    input_audio_transcription: object
    """
    Configuration for input audio transcription, defaults to off and can be set to null to turn off once on. Input audio transcription is not native to the model, since the model consumes audio directly. Transcription runs asynchronously through the /audio/transcriptions endpoint and should be treated as guidance of input audio content rather than precisely what the model heard. The client can optionally set the language and prompt for transcription, these offer additional guidance to the transcription service.
    """

    instructions: str
    """
    The default system instructions (i.e. system message) prepended to model calls. This field allows the client to guide the model on desired responses. The model can be instructed on response content and format, (e.g. "be extremely succinct", "act friendly", "here are examples of good responses") and on audio behavior (e.g. "talk quickly", "inject emotion into your voice", "laugh frequently"). The instructions are not guaranteed to be followed by the model, but they provide guidance to the model on the desired behavior.
    """

    max_response_output_tokens: Union[int, Literal["inf"]]
    """
    Maximum number of output tokens for a single assistant response, inclusive of tool calls. Provide an integer between 1 and 4096 to limit output tokens, or inf for the maximum available tokens for a given model. Defaults to inf.
    """

    modalities: List[str]
    """
    The set of modalities the model can respond with. To disable audio, set this to ["text"].
    """

    model: str
    """
    The Realtime model used for this session.
    """

    output_audio_format: str
    """
    The format of output audio. Options are pcm16, g711_ulaw, or g711_alaw. For pcm16, output audio is sampled at a rate of 24kHz.
    """

    temperature: float
    """
    Sampling temperature for the model, limited to [0.6, 1.2]. For audio models a temperature of 0.8 is highly recommended for best performance.
    """

    tool_choice: str
    """
    How the model chooses tools. Options are auto, none, required, or specify a function.
    """

    tools: list
    """
    Tools (functions) available to the model.
    """

    turn_detection: object
    """

    Configuration for turn detection, ether Server VAD or Semantic VAD. This can be set to null to turn off, in which case the client must manually trigger model response. Server VAD means that the model will detect the start and end of speech based on audio volume and respond at the end of user speech. Semantic VAD is more advanced and uses a turn detection model (in conjuction with VAD) to semantically estimate whether the user has finished speaking, then dynamically sets a timeout based on this probability. For example, if user audio trails off with "uhhm", the model will score a low probability of turn end and wait longer for the user to continue speaking. This can be useful for more natural conversations, but may have a higher latency.
    """

    voice: str
    """
    The voice the model uses to respond.
    """


class OpenAIRealtimeStreamSessionEvents(TypedDict):
    event_id: str
    session: OpenAIRealtimeStreamSession
    type: Union[Literal["session.created"], Literal["session.updated"]]


class OpenAIRealtimeStreamResponseOutputItemContent(TypedDict, total=False):
    audio: str
    """Base64-encoded audio bytes, used for 'input_audio' content types"""
    id: str
    """The ID of the previous conversation item for reference"""
    text: str
    """The text content, used for 'input_text' and 'text' content types"""
    transcript: str
    """The transcript content, used for 'input_audio' content types"""
    type: Literal["input_audio", "input_text", "text", "item_reference", "audio"]
    """The type of content"""


class OpenAIRealtimeStreamResponseOutputItem(TypedDict, total=False):
    arguments: str
    """For function call items"""

    call_id: str
    """The ID of the function call"""

    id: str
    """The ID of the previous conversation item for reference"""

    content: List[OpenAIRealtimeStreamResponseOutputItemContent]

    name: str
    """The name of the function call"""

    object: Literal["realtime.item"]
    """The object type"""

    role: Literal["assistant", "user", "system"]
    """The role of the item, only used for 'message' items"""

    status: Literal["completed", "incomplete", "in_progress"]
    """The status of the item"""

    output: str
    """The output of the function call"""

    type: Literal["function_call", "message", "function_call_output"]
    """The type of item"""


class OpenAIRealtimeStreamResponseOutputItemAdded(TypedDict):
    type: Literal["response.output_item.added"]
    response_id: str
    output_index: int
    item: OpenAIRealtimeStreamResponseOutputItem


class OpenAIRealtimeStreamResponseBaseObject(TypedDict):
    event_id: str
    response: dict
    type: str


class OpenAIRealtimeConversationObject(TypedDict, total=False):
    id: str
    object: Required[Literal["realtime.conversation"]]


class OpenAIRealtimeConversationCreated(TypedDict, total=False):
    type: Required[Literal["conversation.created"]]
    conversation: OpenAIRealtimeConversationObject
    event_id: str


class OpenAIRealtimeConversationItemCreated(TypedDict, total=False):
    type: Required[Literal["conversation.item.created"]]
    item: OpenAIRealtimeStreamResponseOutputItem
    event_id: str
    previous_item_id: str


class OpenAIRealtimeResponseContentPart(TypedDict, total=False):
    audio: str
    """Base64-encoded audio bytes, if type is 'audio'"""

    text: str
    """The text content, if type is 'text'"""

    transcript: str
    """The transcript content, if type is 'audio'"""

    type: Literal["audio", "text"]
    """The type of content"""


class OpenAIRealtimeResponseContentPartAdded(TypedDict):
    type: Literal["response.content_part.added"]
    content_index: int
    event_id: str
    item_id: str
    output_index: int
    part: OpenAIRealtimeResponseContentPart
    response_id: str


class OpenAIRealtimeResponseDelta(TypedDict):
    content_index: int
    delta: str
    event_id: str
    item_id: str
    output_index: int
    response_id: str
    type: Union[Literal["response.text.delta"], Literal["response.audio.delta"]]


class OpenAIRealtimeResponseTextDone(TypedDict):
    content_index: int
    event_id: str
    item_id: str
    output_index: int
    response_id: str
    text: str
    type: Literal["response.text.done"]


class OpenAIRealtimeResponseAudioDone(TypedDict):
    content_index: int
    event_id: str
    item_id: str
    output_index: int
    response_id: str
    type: Literal["response.audio.done"]


class OpenAIRealtimeContentPartDone(TypedDict):
    content_index: int
    event_id: str
    item_id: str
    output_index: int
    response_id: str
    part: OpenAIRealtimeResponseContentPart
    type: Literal["response.content_part.done"]


class OpenAIRealtimeOutputItemDone(TypedDict):
    event_id: str
    item: OpenAIRealtimeStreamResponseOutputItem
    output_index: int
    response_id: str
    type: Literal["response.output_item.done"]


class OpenAIRealtimeResponseDoneObject(TypedDict, total=False):
    conversation_id: str
    id: str
    max_output_tokens: int
    metadata: dict
    modalities: list
    object: Literal["realtime.response"]
    output: List[OpenAIRealtimeStreamResponseOutputItem]
    output_audio_format: str
    status: Literal["completed", "cancelled", "failed", "incomplete"]
    status_details: dict
    temperature: float
    usage: dict  # ResponseAPIUsage
    voice: str


class OpenAIRealtimeDoneEvent(TypedDict):
    event_id: str
    response: OpenAIRealtimeResponseDoneObject
    type: Literal["response.done"]


class OpenAIRealtimeEventTypes(Enum):
    SESSION_CREATED = "session.created"
    RESPONSE_TEXT_DELTA = "response.text.delta"
    RESPONSE_AUDIO_DELTA = "response.audio.delta"
    RESPONSE_TEXT_DONE = "response.text.done"
    RESPONSE_AUDIO_DONE = "response.audio.done"
    RESPONSE_DONE = "response.done"
    RESPONSE_OUTPUT_ITEM_ADDED = "response.output_item.added"
    RESPONSE_CONTENT_PART_ADDED = "response.content_part.added"


OpenAIRealtimeEvents = Union[
    OpenAIRealtimeStreamResponseBaseObject,
    OpenAIRealtimeStreamSessionEvents,
    OpenAIRealtimeStreamResponseOutputItemAdded,
    OpenAIRealtimeResponseContentPartAdded,
    OpenAIRealtimeConversationItemCreated,
    OpenAIRealtimeConversationCreated,
    OpenAIRealtimeResponseDelta,
    OpenAIRealtimeResponseTextDone,
    OpenAIRealtimeResponseAudioDone,
    OpenAIRealtimeContentPartDone,
    OpenAIRealtimeOutputItemDone,
    OpenAIRealtimeDoneEvent,
]

OpenAIRealtimeStreamList = List[OpenAIRealtimeEvents]


class ImageGenerationRequestQuality(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    AUTO = "auto"
    STANDARD = "standard"
    HD = "hd"


class OpenAIModerationResult(BaseLiteLLMOpenAIResponseObject):
    categories: Optional[Dict]
    category_applied_input_types: Optional[Dict]
    category_scores: Optional[Dict]
    flagged: Optional[bool]


class OpenAIModerationResponse(BaseLiteLLMOpenAIResponseObject):
    """
    Response from the OpenAI Moderation API.
    """

    id: str
    """The unique identifier for the moderation request."""

    model: str
    """The model used to generate the moderation results."""

    results: List[OpenAIModerationResult]
    """A list of moderation objects."""

    # Define private attributes using PrivateAttr
    _hidden_params: dict = PrivateAttr(default_factory=dict)


class OpenAIChatCompletionLogprobsContentTopLogprobs(TypedDict, total=False):
    bytes: List
    logprob: Required[float]
    token: Required[str]


class OpenAIChatCompletionLogprobsContent(TypedDict, total=False):
    bytes: List
    logprob: Required[float]
    token: Required[str]
    top_logprobs: List[OpenAIChatCompletionLogprobsContentTopLogprobs]


class OpenAIChatCompletionLogprobs(TypedDict, total=False):
    content: List[OpenAIChatCompletionLogprobsContent]
    refusal: List[OpenAIChatCompletionLogprobsContent]


class OpenAIChatCompletionChoices(TypedDict, total=False):
    finish_reason: Required[str]
    index: Required[int]
    logprobs: Optional[OpenAIChatCompletionLogprobs]
    message: Required[ChatCompletionResponseMessage]


class OpenAIChatCompletionResponse(TypedDict, total=False):
    id: Required[str]
    object: Required[str]
    created: Required[int]
    model: Required[str]
    choices: Required[List[OpenAIChatCompletionChoices]]
    usage: Required[ChatCompletionUsageBlock]
    system_fingerprint: str
    service_tier: str


OpenAIChatCompletionFinishReason = Literal[
    "stop", "content_filter", "function_call", "tool_calls", "length"
]


class OpenAIWebSearchUserLocationApproximate(TypedDict):
    city: str
    country: str
    region: str
    timezone: str


class OpenAIWebSearchUserLocation(TypedDict):
    approximate: OpenAIWebSearchUserLocationApproximate
    type: Literal["approximate"]


class OpenAIWebSearchOptions(TypedDict, total=False):
    search_context_size: Optional[Literal["low", "medium", "high"]]
    user_location: Optional[OpenAIWebSearchUserLocation]


class OpenAIRealtimeTurnDetection(TypedDict, total=False):
    create_response: bool
    eagerness: str
    interrupt_response: bool
    prefix_padding_ms: int
    silence_duration_ms: int
    threshold: int
    type: str


class OpenAIMcpServerTool(TypedDict, total=False):
    type: Required[Literal["mcp"]]
    server_label: Required[str]
    server_url: Required[str]
    require_approval: str
    allowed_tools: Optional[List[str]]
    headers: Optional[Dict[str, str]]

# === NexusCore/openenv\Lib\site-packages\googleapiclient\discovery.py ===
# Copyright 2014 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Client for discovery based APIs.

A client library for Google's discovery based APIs.
"""
from __future__ import absolute_import

__author__ = "jcgregorio@google.com (Joe Gregorio)"
__all__ = ["build", "build_from_document", "fix_method_name", "key2param"]

from collections import OrderedDict
import collections.abc

# Standard library imports
import copy
from email.generator import BytesGenerator
from email.mime.multipart import MIMEMultipart
from email.mime.nonmultipart import MIMENonMultipart
import http.client as http_client
import io
import json
import keyword
import logging
import mimetypes
import os
import re
import urllib

import google.api_core.client_options
from google.auth.exceptions import MutualTLSChannelError
from google.auth.transport import mtls
from google.oauth2 import service_account

# Third-party imports
import httplib2
import uritemplate

try:
    import google_auth_httplib2
except ImportError:  # pragma: NO COVER
    google_auth_httplib2 = None

try:
    from google.api_core import universe

    HAS_UNIVERSE = True
except ImportError:
    HAS_UNIVERSE = False

# Local imports
from googleapiclient import _auth, mimeparse
from googleapiclient._helpers import _add_query_parameter, positional
from googleapiclient.errors import (
    HttpError,
    InvalidJsonError,
    MediaUploadSizeError,
    UnacceptableMimeTypeError,
    UnknownApiNameOrVersion,
    UnknownFileType,
)
from googleapiclient.http import (
    BatchHttpRequest,
    HttpMock,
    HttpMockSequence,
    HttpRequest,
    MediaFileUpload,
    MediaUpload,
    build_http,
)
from googleapiclient.model import JsonModel, MediaModel, RawModel
from googleapiclient.schema import Schemas

# The client library requires a version of httplib2 that supports RETRIES.
httplib2.RETRIES = 1

logger = logging.getLogger(__name__)

URITEMPLATE = re.compile("{[^}]*}")
VARNAME = re.compile("[a-zA-Z0-9_-]+")
DISCOVERY_URI = (
    "https://www.googleapis.com/discovery/v1/apis/" "{api}/{apiVersion}/rest"
)
V1_DISCOVERY_URI = DISCOVERY_URI
V2_DISCOVERY_URI = (
    "https://{api}.googleapis.com/$discovery/rest?" "version={apiVersion}"
)
DEFAULT_METHOD_DOC = "A description of how to use this function"
HTTP_PAYLOAD_METHODS = frozenset(["PUT", "POST", "PATCH"])

_MEDIA_SIZE_BIT_SHIFTS = {"KB": 10, "MB": 20, "GB": 30, "TB": 40}
BODY_PARAMETER_DEFAULT_VALUE = {"description": "The request body.", "type": "object"}
MEDIA_BODY_PARAMETER_DEFAULT_VALUE = {
    "description": (
        "The filename of the media request body, or an instance "
        "of a MediaUpload object."
    ),
    "type": "string",
    "required": False,
}
MEDIA_MIME_TYPE_PARAMETER_DEFAULT_VALUE = {
    "description": (
        "The MIME type of the media request body, or an instance "
        "of a MediaUpload object."
    ),
    "type": "string",
    "required": False,
}
_PAGE_TOKEN_NAMES = ("pageToken", "nextPageToken")

# Parameters controlling mTLS behavior. See https://google.aip.dev/auth/4114.
GOOGLE_API_USE_CLIENT_CERTIFICATE = "GOOGLE_API_USE_CLIENT_CERTIFICATE"
GOOGLE_API_USE_MTLS_ENDPOINT = "GOOGLE_API_USE_MTLS_ENDPOINT"
GOOGLE_CLOUD_UNIVERSE_DOMAIN = "GOOGLE_CLOUD_UNIVERSE_DOMAIN"
DEFAULT_UNIVERSE = "googleapis.com"
# Parameters accepted by the stack, but not visible via discovery.
# TODO(dhermes): Remove 'userip' in 'v2'.
STACK_QUERY_PARAMETERS = frozenset(["trace", "pp", "userip", "strict"])
STACK_QUERY_PARAMETER_DEFAULT_VALUE = {"type": "string", "location": "query"}


class APICoreVersionError(ValueError):
    def __init__(self):
        message = (
            "google-api-core >= 2.18.0 is required to use the universe domain feature."
        )
        super().__init__(message)


# Library-specific reserved words beyond Python keywords.
RESERVED_WORDS = frozenset(["body"])

# patch _write_lines to avoid munging '\r' into '\n'
# ( https://bugs.python.org/issue18886 https://bugs.python.org/issue19003 )
class _BytesGenerator(BytesGenerator):
    _write_lines = BytesGenerator.write


def fix_method_name(name):
    """Fix method names to avoid '$' characters and reserved word conflicts.

    Args:
      name: string, method name.

    Returns:
      The name with '_' appended if the name is a reserved word and '$' and '-'
      replaced with '_'.
    """
    name = name.replace("$", "_").replace("-", "_")
    if keyword.iskeyword(name) or name in RESERVED_WORDS:
        return name + "_"
    else:
        return name


def key2param(key):
    """Converts key names into parameter names.

    For example, converting "max-results" -> "max_results"

    Args:
      key: string, the method key name.

    Returns:
      A safe method name based on the key name.
    """
    result = []
    key = list(key)
    if not key[0].isalpha():
        result.append("x")
    for c in key:
        if c.isalnum():
            result.append(c)
        else:
            result.append("_")

    return "".join(result)


@positional(2)
def build(
    serviceName,
    version,
    http=None,
    discoveryServiceUrl=None,
    developerKey=None,
    model=None,
    requestBuilder=HttpRequest,
    credentials=None,
    cache_discovery=True,
    cache=None,
    client_options=None,
    adc_cert_path=None,
    adc_key_path=None,
    num_retries=1,
    static_discovery=None,
    always_use_jwt_access=False,
):
    """Construct a Resource for interacting with an API.

    Construct a Resource object for interacting with an API. The serviceName and
    version are the names from the Discovery service.

    Args:
      serviceName: string, name of the service.
      version: string, the version of the service.
      http: httplib2.Http, An instance of httplib2.Http or something that acts
        like it that HTTP requests will be made through.
      discoveryServiceUrl: string, a URI Template that points to the location of
        the discovery service. It should have two parameters {api} and
        {apiVersion} that when filled in produce an absolute URI to the discovery
        document for that service.
      developerKey: string, key obtained from
        https://code.google.com/apis/console.
      model: googleapiclient.Model, converts to and from the wire format.
      requestBuilder: googleapiclient.http.HttpRequest, encapsulator for an HTTP
        request.
      credentials: oauth2client.Credentials or
        google.auth.credentials.Credentials, credentials to be used for
        authentication.
      cache_discovery: Boolean, whether or not to cache the discovery doc.
      cache: googleapiclient.discovery_cache.base.CacheBase, an optional
        cache object for the discovery documents.
      client_options: Mapping object or google.api_core.client_options, client
        options to set user options on the client.
        (1) The API endpoint should be set through client_options. If API endpoint
        is not set, `GOOGLE_API_USE_MTLS_ENDPOINT` environment variable can be used
        to control which endpoint to use.
        (2) client_cert_source is not supported, client cert should be provided using
        client_encrypted_cert_source instead. In order to use the provided client
        cert, `GOOGLE_API_USE_CLIENT_CERTIFICATE` environment variable must be
        set to `true`.
        More details on the environment variables are here:
        https://google.aip.dev/auth/4114
      adc_cert_path: str, client certificate file path to save the application
        default client certificate for mTLS. This field is required if you want to
        use the default client certificate. `GOOGLE_API_USE_CLIENT_CERTIFICATE`
        environment variable must be set to `true` in order to use this field,
        otherwise this field doesn't nothing.
        More details on the environment variables are here:
        https://google.aip.dev/auth/4114
      adc_key_path: str, client encrypted private key file path to save the
        application default client encrypted private key for mTLS. This field is
        required if you want to use the default client certificate.
        `GOOGLE_API_USE_CLIENT_CERTIFICATE` environment variable must be set to
        `true` in order to use this field, otherwise this field doesn't nothing.
        More details on the environment variables are here:
        https://google.aip.dev/auth/4114
      num_retries: Integer, number of times to retry discovery with
        randomized exponential backoff in case of intermittent/connection issues.
      static_discovery: Boolean, whether or not to use the static discovery docs
        included in the library. The default value for `static_discovery` depends
        on the value of `discoveryServiceUrl`. `static_discovery` will default to
        `True` when `discoveryServiceUrl` is also not provided, otherwise it will
        default to `False`.
      always_use_jwt_access: Boolean, whether always use self signed JWT for service
        account credentials. This only applies to
        google.oauth2.service_account.Credentials.

    Returns:
      A Resource object with methods for interacting with the service.

    Raises:
      google.auth.exceptions.MutualTLSChannelError: if there are any problems
        setting up mutual TLS channel.
    """
    params = {"api": serviceName, "apiVersion": version}

    # The default value for `static_discovery` depends on the value of
    # `discoveryServiceUrl`. `static_discovery` will default to `True` when
    # `discoveryServiceUrl` is also not provided, otherwise it will default to
    # `False`. This is added for backwards compatability with
    # google-api-python-client 1.x which does not support the `static_discovery`
    # parameter.
    if static_discovery is None:
        if discoveryServiceUrl is None:
            static_discovery = True
        else:
            static_discovery = False

    if http is None:
        discovery_http = build_http()
    else:
        discovery_http = http

    service = None

    for discovery_url in _discovery_service_uri_options(discoveryServiceUrl, version):
        requested_url = uritemplate.expand(discovery_url, params)

        try:
            content = _retrieve_discovery_doc(
                requested_url,
                discovery_http,
                cache_discovery,
                serviceName,
                version,
                cache,
                developerKey,
                num_retries=num_retries,
                static_discovery=static_discovery,
            )
            service = build_from_document(
                content,
                base=discovery_url,
                http=http,
                developerKey=developerKey,
                model=model,
                requestBuilder=requestBuilder,
                credentials=credentials,
                client_options=client_options,
                adc_cert_path=adc_cert_path,
                adc_key_path=adc_key_path,
                always_use_jwt_access=always_use_jwt_access,
            )
            break  # exit if a service was created
        except HttpError as e:
            if e.resp.status == http_client.NOT_FOUND:
                continue
            else:
                raise e

    # If discovery_http was created by this function, we are done with it
    # and can safely close it
    if http is None:
        discovery_http.close()

    if service is None:
        raise UnknownApiNameOrVersion("name: %s  version: %s" % (serviceName, version))
    else:
        return service


def _discovery_service_uri_options(discoveryServiceUrl, version):
    """
      Returns Discovery URIs to be used for attempting to build the API Resource.

    Args:
      discoveryServiceUrl:
          string, the Original Discovery Service URL preferred by the customer.
      version:
          string, API Version requested

    Returns:
        A list of URIs to be tried for the Service Discovery, in order.
    """

    if discoveryServiceUrl is not None:
        return [discoveryServiceUrl]
    if version is None:
        # V1 Discovery won't work if the requested version is None
        logger.warning(
            "Discovery V1 does not support empty versions. Defaulting to V2..."
        )
        return [V2_DISCOVERY_URI]
    else:
        return [DISCOVERY_URI, V2_DISCOVERY_URI]


def _retrieve_discovery_doc(
    url,
    http,
    cache_discovery,
    serviceName,
    version,
    cache=None,
    developerKey=None,
    num_retries=1,
    static_discovery=True,
):
    """Retrieves the discovery_doc from cache or the internet.

    Args:
      url: string, the URL of the discovery document.
      http: httplib2.Http, An instance of httplib2.Http or something that acts
        like it through which HTTP requests will be made.
      cache_discovery: Boolean, whether or not to cache the discovery doc.
      serviceName: string, name of the service.
      version: string, the version of the service.
      cache: googleapiclient.discovery_cache.base.Cache, an optional cache
        object for the discovery documents.
      developerKey: string, Key for controlling API usage, generated
        from the API Console.
      num_retries: Integer, number of times to retry discovery with
        randomized exponential backoff in case of intermittent/connection issues.
      static_discovery: Boolean, whether or not to use the static discovery docs
        included in the library.

    Returns:
      A unicode string representation of the discovery document.
    """
    from . import discovery_cache

    if cache_discovery:
        if cache is None:
            cache = discovery_cache.autodetect()
        if cache:
            content = cache.get(url)
            if content:
                return content

    # When `static_discovery=True`, use static discovery artifacts included
    # with the library
    if static_discovery:
        content = discovery_cache.get_static_doc(serviceName, version)
        if content:
            return content
        else:
            raise UnknownApiNameOrVersion(
                "name: %s  version: %s" % (serviceName, version)
            )

    actual_url = url
    # REMOTE_ADDR is defined by the CGI spec [RFC3875] as the environment
    # variable that contains the network address of the client sending the
    # request. If it exists then add that to the request for the discovery
    # document to avoid exceeding the quota on discovery requests.
    if "REMOTE_ADDR" in os.environ:
        actual_url = _add_query_parameter(url, "userIp", os.environ["REMOTE_ADDR"])
    if developerKey:
        actual_url = _add_query_parameter(url, "key", developerKey)
    logger.debug("URL being requested: GET %s", actual_url)

    # Execute this request with retries build into HttpRequest
    # Note that it will already raise an error if we don't get a 2xx response
    req = HttpRequest(http, HttpRequest.null_postproc, actual_url)
    resp, content = req.execute(num_retries=num_retries)

    try:
        content = content.decode("utf-8")
    except AttributeError:
        pass

    try:
        service = json.loads(content)
    except ValueError as e:
        logger.error("Failed to parse as JSON: " + content)
        raise InvalidJsonError()
    if cache_discovery and cache:
        cache.set(url, content)
    return content


def _check_api_core_compatible_with_credentials_universe(credentials):
    if not HAS_UNIVERSE:
        credentials_universe = getattr(credentials, "universe_domain", None)
        if credentials_universe and credentials_universe != DEFAULT_UNIVERSE:
            raise APICoreVersionError


@positional(1)
def build_from_document(
    service,
    base=None,
    future=None,
    http=None,
    developerKey=None,
    model=None,
    requestBuilder=HttpRequest,
    credentials=None,
    client_options=None,
    adc_cert_path=None,
    adc_key_path=None,
    always_use_jwt_access=False,
):
    """Create a Resource for interacting with an API.

    Same as `build()`, but constructs the Resource object from a discovery
    document that is it given, as opposed to retrieving one over HTTP.

    Args:
      service: string or object, the JSON discovery document describing the API.
        The value passed in may either be the JSON string or the deserialized
        JSON.
      base: string, base URI for all HTTP requests, usually the discovery URI.
        This parameter is no longer used as rootUrl and servicePath are included
        within the discovery document. (deprecated)
      future: string, discovery document with future capabilities (deprecated).
      http: httplib2.Http, An instance of httplib2.Http or something that acts
        like it that HTTP requests will be made through.
      developerKey: string, Key for controlling API usage, generated
        from the API Console.
      model: Model class instance that serializes and de-serializes requests and
        responses.
      requestBuilder: Takes an http request and packages it up to be executed.
      credentials: oauth2client.Credentials or
        google.auth.credentials.Credentials, credentials to be used for
        authentication.
      client_options: Mapping object or google.api_core.client_options, client
        options to set user options on the client.
        (1) The API endpoint should be set through client_options. If API endpoint
        is not set, `GOOGLE_API_USE_MTLS_ENDPOINT` environment variable can be used
        to control which endpoint to use.
        (2) client_cert_source is not supported, client cert should be provided using
        client_encrypted_cert_source instead. In order to use the provided client
        cert, `GOOGLE_API_USE_CLIENT_CERTIFICATE` environment variable must be
        set to `true`.
        More details on the environment variables are here:
        https://google.aip.dev/auth/4114
      adc_cert_path: str, client certificate file path to save the application
        default client certificate for mTLS. This field is required if you want to
        use the default client certificate. `GOOGLE_API_USE_CLIENT_CERTIFICATE`
        environment variable must be set to `true` in order to use this field,
        otherwise this field doesn't nothing.
        More details on the environment variables are here:
        https://google.aip.dev/auth/4114
      adc_key_path: str, client encrypted private key file path to save the
        application default client encrypted private key for mTLS. This field is
        required if you want to use the default client certificate.
        `GOOGLE_API_USE_CLIENT_CERTIFICATE` environment variable must be set to
        `true` in order to use this field, otherwise this field doesn't nothing.
        More details on the environment variables are here:
        https://google.aip.dev/auth/4114
      always_use_jwt_access: Boolean, whether always use self signed JWT for service
        account credentials. This only applies to
        google.oauth2.service_account.Credentials.

    Returns:
      A Resource object with methods for interacting with the service.

    Raises:
      google.auth.exceptions.MutualTLSChannelError: if there are any problems
        setting up mutual TLS channel.
    """

    if client_options is None:
        client_options = google.api_core.client_options.ClientOptions()
    if isinstance(client_options, collections.abc.Mapping):
        client_options = google.api_core.client_options.from_dict(client_options)

    if http is not None:
        # if http is passed, the user cannot provide credentials
        banned_options = [
            (credentials, "credentials"),
            (client_options.credentials_file, "client_options.credentials_file"),
        ]
        for option, name in banned_options:
            if option is not None:
                raise ValueError(
                    "Arguments http and {} are mutually exclusive".format(name)
                )

    if isinstance(service, str):
        service = json.loads(service)
    elif isinstance(service, bytes):
        service = json.loads(service.decode("utf-8"))

    if "rootUrl" not in service and isinstance(http, (HttpMock, HttpMockSequence)):
        logger.error(
            "You are using HttpMock or HttpMockSequence without"
            + "having the service discovery doc in cache. Try calling "
            + "build() without mocking once first to populate the "
            + "cache."
        )
        raise InvalidJsonError()

    # If an API Endpoint is provided on client options, use that as the base URL
    base = urllib.parse.urljoin(service["rootUrl"], service["servicePath"])
    universe_domain = None
    if HAS_UNIVERSE:
        universe_domain_env = os.getenv(GOOGLE_CLOUD_UNIVERSE_DOMAIN, None)
        universe_domain = universe.determine_domain(
            client_options.universe_domain, universe_domain_env
        )
        base = base.replace(universe.DEFAULT_UNIVERSE, universe_domain)
    else:
        client_universe = getattr(client_options, "universe_domain", None)
        if client_universe:
            raise APICoreVersionError

    audience_for_self_signed_jwt = base
    if client_options.api_endpoint:
        base = client_options.api_endpoint

    schema = Schemas(service)

    # If the http client is not specified, then we must construct an http client
    # to make requests. If the service has scopes, then we also need to setup
    # authentication.
    if http is None:
        # Does the service require scopes?
        scopes = list(
            service.get("auth", {}).get("oauth2", {}).get("scopes", {}).keys()
        )

        # If so, then the we need to setup authentication if no developerKey is
        # specified.
        if scopes and not developerKey:
            # Make sure the user didn't pass multiple credentials
            if client_options.credentials_file and credentials:
                raise google.api_core.exceptions.DuplicateCredentialArgs(
                    "client_options.credentials_file and credentials are mutually exclusive."
                )
            # Check for credentials file via client options
            if client_options.credentials_file:
                credentials = _auth.credentials_from_file(
                    client_options.credentials_file,
                    scopes=client_options.scopes,
                    quota_project_id=client_options.quota_project_id,
                )
            # If the user didn't pass in credentials, attempt to acquire application
            # default credentials.
            if credentials is None:
                credentials = _auth.default_credentials(
                    scopes=client_options.scopes,
                    quota_project_id=client_options.quota_project_id,
                )

            # Check google-api-core >= 2.18.0 if credentials' universe != "googleapis.com".
            _check_api_core_compatible_with_credentials_universe(credentials)

            # The credentials need to be scoped.
            # If the user provided scopes via client_options don't override them
            if not client_options.scopes:
                credentials = _auth.with_scopes(credentials, scopes)

        # For google-auth service account credentials, enable self signed JWT if
        # always_use_jwt_access is true.
        if (
            credentials
            and isinstance(credentials, service_account.Credentials)
            and always_use_jwt_access
            and hasattr(service_account.Credentials, "with_always_use_jwt_access")
        ):
            credentials = credentials.with_always_use_jwt_access(always_use_jwt_access)
            credentials._create_self_signed_jwt(audience_for_self_signed_jwt)

        # If credentials are provided, create an authorized http instance;
        # otherwise, skip authentication.
        if credentials:
            http = _auth.authorized_http(credentials)

        # If the service doesn't require scopes then there is no need for
        # authentication.
        else:
            http = build_http()

        # Obtain client cert and create mTLS http channel if cert exists.
        client_cert_to_use = None
        use_client_cert = os.getenv(GOOGLE_API_USE_CLIENT_CERTIFICATE, "false")
        if not use_client_cert in ("true", "false"):
            raise MutualTLSChannelError(
                "Unsupported GOOGLE_API_USE_CLIENT_CERTIFICATE value. Accepted values: true, false"
            )
        if client_options and client_options.client_cert_source:
            raise MutualTLSChannelError(
                "ClientOptions.client_cert_source is not supported, please use ClientOptions.client_encrypted_cert_source."
            )
        if use_client_cert == "true":
            if (
                client_options
                and hasattr(client_options, "client_encrypted_cert_source")
                and client_options.client_encrypted_cert_source
            ):
                client_cert_to_use = client_options.client_encrypted_cert_source
            elif (
                adc_cert_path and adc_key_path and mtls.has_default_client_cert_source()
            ):
                client_cert_to_use = mtls.default_client_encrypted_cert_source(
                    adc_cert_path, adc_key_path
                )
        if client_cert_to_use:
            cert_path, key_path, passphrase = client_cert_to_use()

            # The http object we built could be google_auth_httplib2.AuthorizedHttp
            # or httplib2.Http. In the first case we need to extract the wrapped
            # httplib2.Http object from google_auth_httplib2.AuthorizedHttp.
            http_channel = (
                http.http
                if google_auth_httplib2
                and isinstance(http, google_auth_httplib2.AuthorizedHttp)
                else http
            )
            http_channel.add_certificate(key_path, cert_path, "", passphrase)

        # If user doesn't provide api endpoint via client options, decide which
        # api endpoint to use.
        if "mtlsRootUrl" in service and (
            not client_options or not client_options.api_endpoint
        ):
            mtls_endpoint = urllib.parse.urljoin(
                service["mtlsRootUrl"], service["servicePath"]
            )
            use_mtls_endpoint = os.getenv(GOOGLE_API_USE_MTLS_ENDPOINT, "auto")

            if not use_mtls_endpoint in ("never", "auto", "always"):
                raise MutualTLSChannelError(
                    "Unsupported GOOGLE_API_USE_MTLS_ENDPOINT value. Accepted values: never, auto, always"
                )

            # Switch to mTLS endpoint, if environment variable is "always", or
            # environment varibable is "auto" and client cert exists.
            if use_mtls_endpoint == "always" or (
                use_mtls_endpoint == "auto" and client_cert_to_use
            ):
                if HAS_UNIVERSE and universe_domain != universe.DEFAULT_UNIVERSE:
                    raise MutualTLSChannelError(
                        f"mTLS is not supported in any universe other than {universe.DEFAULT_UNIVERSE}."
                    )
                base = mtls_endpoint
    else:
        # Check google-api-core >= 2.18.0 if credentials' universe != "googleapis.com".
        http_credentials = getattr(http, "credentials", None)
        _check_api_core_compatible_with_credentials_universe(http_credentials)

    if model is None:
        features = service.get("features", [])
        model = JsonModel("dataWrapper" in features)

    return Resource(
        http=http,
        baseUrl=base,
        model=model,
        developerKey=developerKey,
        requestBuilder=requestBuilder,
        resourceDesc=service,
        rootDesc=service,
        schema=schema,
        universe_domain=universe_domain,
    )


def _cast(value, schema_type):
    """Convert value to a string based on JSON Schema type.

    See http://tools.ietf.org/html/draft-zyp-json-schema-03 for more details on
    JSON Schema.

    Args:
      value: any, the value to convert
      schema_type: string, the type that value should be interpreted as

    Returns:
      A string representation of 'value' based on the schema_type.
    """
    if schema_type == "string":
        if type(value) == type("") or type(value) == type(""):
            return value
        else:
            return str(value)
    elif schema_type == "integer":
        return str(int(value))
    elif schema_type == "number":
        return str(float(value))
    elif schema_type == "boolean":
        return str(bool(value)).lower()
    else:
        if type(value) == type("") or type(value) == type(""):
            return value
        else:
            return str(value)


def _media_size_to_long(maxSize):
    """Convert a string media size, such as 10GB or 3TB into an integer.

    Args:
      maxSize: string, size as a string, such as 2MB or 7GB.

    Returns:
      The size as an integer value.
    """
    if len(maxSize) < 2:
        return 0
    units = maxSize[-2:].upper()
    bit_shift = _MEDIA_SIZE_BIT_SHIFTS.get(units)
    if bit_shift is not None:
        return int(maxSize[:-2]) << bit_shift
    else:
        return int(maxSize)


def _media_path_url_from_info(root_desc, path_url):
    """Creates an absolute media path URL.

    Constructed using the API root URI and service path from the discovery
    document and the relative path for the API method.

    Args:
      root_desc: Dictionary; the entire original deserialized discovery document.
      path_url: String; the relative URL for the API method. Relative to the API
          root, which is specified in the discovery document.

    Returns:
      String; the absolute URI for media upload for the API method.
    """
    return "%(root)supload/%(service_path)s%(path)s" % {
        "root": root_desc["rootUrl"],
        "service_path": root_desc["servicePath"],
        "path": path_url,
    }


def _fix_up_parameters(method_desc, root_desc, http_method, schema):
    """Updates parameters of an API method with values specific to this library.

    Specifically, adds whatever global parameters are specified by the API to the
    parameters for the individual method. Also adds parameters which don't
    appear in the discovery document, but are available to all discovery based
    APIs (these are listed in STACK_QUERY_PARAMETERS).

    SIDE EFFECTS: This updates the parameters dictionary object in the method
    description.

    Args:
      method_desc: Dictionary with metadata describing an API method. Value comes
          from the dictionary of methods stored in the 'methods' key in the
          deserialized discovery document.
      root_desc: Dictionary; the entire original deserialized discovery document.
      http_method: String; the HTTP method used to call the API method described
          in method_desc.
      schema: Object, mapping of schema names to schema descriptions.

    Returns:
      The updated Dictionary stored in the 'parameters' key of the method
          description dictionary.
    """
    parameters = method_desc.setdefault("parameters", {})

    # Add in the parameters common to all methods.
    for name, description in root_desc.get("parameters", {}).items():
        parameters[name] = description

    # Add in undocumented query parameters.
    for name in STACK_QUERY_PARAMETERS:
        parameters[name] = STACK_QUERY_PARAMETER_DEFAULT_VALUE.copy()

    # Add 'body' (our own reserved word) to parameters if the method supports
    # a request payload.
    if http_method in HTTP_PAYLOAD_METHODS and "request" in method_desc:
        body = BODY_PARAMETER_DEFAULT_VALUE.copy()
        body.update(method_desc["request"])
        parameters["body"] = body

    return parameters


def _fix_up_media_upload(method_desc, root_desc, path_url, parameters):
    """Adds 'media_body' and 'media_mime_type' parameters if supported by method.

    SIDE EFFECTS: If there is a 'mediaUpload' in the method description, adds
    'media_upload' key to parameters.

    Args:
      method_desc: Dictionary with metadata describing an API method. Value comes
          from the dictionary of methods stored in the 'methods' key in the
          deserialized discovery document.
      root_desc: Dictionary; the entire original deserialized discovery document.
      path_url: String; the relative URL for the API method. Relative to the API
          root, which is specified in the discovery document.
      parameters: A dictionary describing method parameters for method described
          in method_desc.

    Returns:
      Triple (accept, max_size, media_path_url) where:
        - accept is a list of strings representing what content types are
          accepted for media upload. Defaults to empty list if not in the
          discovery document.
        - max_size is a long representing the max size in bytes allowed for a
          media upload. Defaults to 0L if not in the discovery document.
        - media_path_url is a String; the absolute URI for media upload for the
          API method. Constructed using the API root URI and service path from
          the discovery document and the relative path for the API method. If
          media upload is not supported, this is None.
    """
    media_upload = method_desc.get("mediaUpload", {})
    accept = media_upload.get("accept", [])
    max_size = _media_size_to_long(media_upload.get("maxSize", ""))
    media_path_url = None

    if media_upload:
        media_path_url = _media_path_url_from_info(root_desc, path_url)
        parameters["media_body"] = MEDIA_BODY_PARAMETER_DEFAULT_VALUE.copy()
        parameters["media_mime_type"] = MEDIA_MIME_TYPE_PARAMETER_DEFAULT_VALUE.copy()

    return accept, max_size, media_path_url


def _fix_up_method_description(method_desc, root_desc, schema):
    """Updates a method description in a discovery document.

    SIDE EFFECTS: Changes the parameters dictionary in the method description with
    extra parameters which are used locally.

    Args:
      method_desc: Dictionary with metadata describing an API method. Value comes
          from the dictionary of methods stored in the 'methods' key in the
          deserialized discovery document.
      root_desc: Dictionary; the entire original deserialized discovery document.
      schema: Object, mapping of schema names to schema descriptions.

    Returns:
      Tuple (path_url, http_method, method_id, accept, max_size, media_path_url)
      where:
        - path_url is a String; the relative URL for the API method. Relative to
          the API root, which is specified in the discovery document.
        - http_method is a String; the HTTP method used to call the API method
          described in the method description.
        - method_id is a String; the name of the RPC method associated with the
          API method, and is in the method description in the 'id' key.
        - accept is a list of strings representing what content types are
          accepted for media upload. Defaults to empty list if not in the
          discovery document.
        - max_size is a long representing the max size in bytes allowed for a
          media upload. Defaults to 0L if not in the discovery document.
        - media_path_url is a String; the absolute URI for media upload for the
          API method. Constructed using the API root URI and service path from
          the discovery document and the relative path for the API method. If
          media upload is not supported, this is None.
    """
    path_url = method_desc["path"]
    http_method = method_desc["httpMethod"]
    method_id = method_desc["id"]

    parameters = _fix_up_parameters(method_desc, root_desc, http_method, schema)
    # Order is important. `_fix_up_media_upload` needs `method_desc` to have a
    # 'parameters' key and needs to know if there is a 'body' parameter because it
    # also sets a 'media_body' parameter.
    accept, max_size, media_path_url = _fix_up_media_upload(
        method_desc, root_desc, path_url, parameters
    )

    return path_url, http_method, method_id, accept, max_size, media_path_url


def _fix_up_media_path_base_url(media_path_url, base_url):
    """
    Update the media upload base url if its netloc doesn't match base url netloc.

    This can happen in case the base url was overridden by
    client_options.api_endpoint.

    Args:
      media_path_url: String; the absolute URI for media upload.
      base_url: string, base URL for the API. All requests are relative to this URI.

    Returns:
      String; the absolute URI for media upload.
    """
    parsed_media_url = urllib.parse.urlparse(media_path_url)
    parsed_base_url = urllib.parse.urlparse(base_url)
    if parsed_media_url.netloc == parsed_base_url.netloc:
        return media_path_url
    return urllib.parse.urlunparse(
        parsed_media_url._replace(netloc=parsed_base_url.netloc)
    )


def _urljoin(base, url):
    """Custom urljoin replacement supporting : before / in url."""
    # In general, it's unsafe to simply join base and url. However, for
    # the case of discovery documents, we know:
    #  * base will never contain params, query, or fragment
    #  * url will never contain a scheme or net_loc.
    # In general, this means we can safely join on /; we just need to
    # ensure we end up with precisely one / joining base and url. The
    # exception here is the case of media uploads, where url will be an
    # absolute url.
    if url.startswith("http://") or url.startswith("https://"):
        return urllib.parse.urljoin(base, url)
    new_base = base if base.endswith("/") else base + "/"
    new_url = url[1:] if url.startswith("/") else url
    return new_base + new_url


# TODO(dhermes): Convert this class to ResourceMethod and make it callable
class ResourceMethodParameters(object):
    """Represents the parameters associated with a method.

    Attributes:
      argmap: Map from method parameter name (string) to query parameter name
          (string).
      required_params: List of required parameters (represented by parameter
          name as string).
      repeated_params: List of repeated parameters (represented by parameter
          name as string).
      pattern_params: Map from method parameter name (string) to regular
          expression (as a string). If the pattern is set for a parameter, the
          value for that parameter must match the regular expression.
      query_params: List of parameters (represented by parameter name as string)
          that will be used in the query string.
      path_params: Set of parameters (represented by parameter name as string)
          that will be used in the base URL path.
      param_types: Map from method parameter name (string) to parameter type. Type
          can be any valid JSON schema type; valid values are 'any', 'array',
          'boolean', 'integer', 'number', 'object', or 'string'. Reference:
          http://tools.ietf.org/html/draft-zyp-json-schema-03#section-5.1
      enum_params: Map from method parameter name (string) to list of strings,
         where each list of strings is the list of acceptable enum values.
    """

    def __init__(self, method_desc):
        """Constructor for ResourceMethodParameters.

        Sets default values and defers to set_parameters to populate.

        Args:
          method_desc: Dictionary with metadata describing an API method. Value
              comes from the dictionary of methods stored in the 'methods' key in
              the deserialized discovery document.
        """
        self.argmap = {}
        self.required_params = []
        self.repeated_params = []
        self.pattern_params = {}
        self.query_params = []
        # TODO(dhermes): Change path_params to a list if the extra URITEMPLATE
        #                parsing is gotten rid of.
        self.path_params = set()
        self.param_types = {}
        self.enum_params = {}

        self.set_parameters(method_desc)

    def set_parameters(self, method_desc):
        """Populates maps and lists based on method description.

        Iterates through each parameter for the method and parses the values from
        the parameter dictionary.

        Args:
          method_desc: Dictionary with metadata describing an API method. Value
              comes from the dictionary of methods stored in the 'methods' key in
              the deserialized discovery document.
        """
        parameters = method_desc.get("parameters", {})
        sorted_parameters = OrderedDict(sorted(parameters.items()))
        for arg, desc in sorted_parameters.items():
            param = key2param(arg)
            self.argmap[param] = arg

            if desc.get("pattern"):
                self.pattern_params[param] = desc["pattern"]
            if desc.get("enum"):
                self.enum_params[param] = desc["enum"]
            if desc.get("required"):
                self.required_params.append(param)
            if desc.get("repeated"):
                self.repeated_params.append(param)
            if desc.get("location") == "query":
                self.query_params.append(param)
            if desc.get("location") == "path":
                self.path_params.add(param)
            self.param_types[param] = desc.get("type", "string")

        # TODO(dhermes): Determine if this is still necessary. Discovery based APIs
        #                should have all path parameters already marked with
        #                'location: path'.
        for match in URITEMPLATE.finditer(method_desc["path"]):
            for namematch in VARNAME.finditer(match.group(0)):
                name = key2param(namematch.group(0))
                self.path_params.add(name)
                if name in self.query_params:
                    self.query_params.remove(name)


def createMethod(methodName, methodDesc, rootDesc, schema):
    """Creates a method for attaching to a Resource.

    Args:
      methodName: string, name of the method to use.
      methodDesc: object, fragment of deserialized discovery document that
        describes the method.
      rootDesc: object, the entire deserialized discovery document.
      schema: object, mapping of schema names to schema descriptions.
    """
    methodName = fix_method_name(methodName)
    (
        pathUrl,
        httpMethod,
        methodId,
        accept,
        maxSize,
        mediaPathUrl,
    ) = _fix_up_method_description(methodDesc, rootDesc, schema)

    parameters = ResourceMethodParameters(methodDesc)

    def method(self, **kwargs):
        # Don't bother with doc string, it will be over-written by createMethod.

        # Validate credentials for the configured universe.
        self._validate_credentials()

        for name in kwargs:
            if name not in parameters.argmap:
                raise TypeError("Got an unexpected keyword argument {}".format(name))

        # Remove args that have a value of None.
        keys = list(kwargs.keys())
        for name in keys:
            if kwargs[name] is None:
                del kwargs[name]

        for name in parameters.required_params:
            if name not in kwargs:
                # temporary workaround for non-paging methods incorrectly requiring
                # page token parameter (cf. drive.changes.watch vs. drive.changes.list)
                if name not in _PAGE_TOKEN_NAMES or _findPageTokenName(
                    _methodProperties(methodDesc, schema, "response")
                ):
                    raise TypeError('Missing required parameter "%s"' % name)

        for name, regex in parameters.pattern_params.items():
            if name in kwargs:
                if isinstance(kwargs[name], str):
                    pvalues = [kwargs[name]]
                else:
                    pvalues = kwargs[name]
                for pvalue in pvalues:
                    if re.match(regex, pvalue) is None:
                        raise TypeError(
                            'Parameter "%s" value "%s" does not match the pattern "%s"'
                            % (name, pvalue, regex)
                        )

        for name, enums in parameters.enum_params.items():
            if name in kwargs:
                # We need to handle the case of a repeated enum
                # name differently, since we want to handle both
                # arg='value' and arg=['value1', 'value2']
                if name in parameters.repeated_params and not isinstance(
                    kwargs[name], str
                ):
                    values = kwargs[name]
                else:
                    values = [kwargs[name]]
                for value in values:
                    if value not in enums:
                        raise TypeError(
                            'Parameter "%s" value "%s" is not an allowed value in "%s"'
                            % (name, value, str(enums))
                        )

        actual_query_params = {}
        actual_path_params = {}
        for key, value in kwargs.items():
            to_type = parameters.param_types.get(key, "string")
            # For repeated parameters we cast each member of the list.
            if key in parameters.repeated_params and type(value) == type([]):
                cast_value = [_cast(x, to_type) for x in value]
            else:
                cast_value = _cast(value, to_type)
            if key in parameters.query_params:
                actual_query_params[parameters.argmap[key]] = cast_value
            if key in parameters.path_params:
                actual_path_params[parameters.argmap[key]] = cast_value
        body_value = kwargs.get("body", None)
        media_filename = kwargs.get("media_body", None)
        media_mime_type = kwargs.get("media_mime_type", None)

        if self._developerKey:
            actual_query_params["key"] = self._developerKey

        model = self._model
        if methodName.endswith("_media"):
            model = MediaModel()
        elif "response" not in methodDesc:
            model = RawModel()

        api_version = methodDesc.get("apiVersion", None)

        headers = {}
        headers, params, query, body = model.request(
            headers, actual_path_params, actual_query_params, body_value, api_version
        )

        expanded_url = uritemplate.expand(pathUrl, params)
        url = _urljoin(self._baseUrl, expanded_url + query)

        resumable = None
        multipart_boundary = ""

        if media_filename:
            # Ensure we end up with a valid MediaUpload object.
            if isinstance(media_filename, str):
                if media_mime_type is None:
                    logger.warning(
                        "media_mime_type argument not specified: trying to auto-detect for %s",
                        media_filename,
                    )
                    media_mime_type, _ = mimetypes.guess_type(media_filename)
                if media_mime_type is None:
                    raise UnknownFileType(media_filename)
                if not mimeparse.best_match([media_mime_type], ",".join(accept)):
                    raise UnacceptableMimeTypeError(media_mime_type)
                media_upload = MediaFileUpload(media_filename, mimetype=media_mime_type)
            elif isinstance(media_filename, MediaUpload):
                media_upload = media_filename
            else:
                raise TypeError("media_filename must be str or MediaUpload.")

            # Check the maxSize
            if media_upload.size() is not None and media_upload.size() > maxSize > 0:
                raise MediaUploadSizeError("Media larger than: %s" % maxSize)

            # Use the media path uri for media uploads
            expanded_url = uritemplate.expand(mediaPathUrl, params)
            url = _urljoin(self._baseUrl, expanded_url + query)
            url = _fix_up_media_path_base_url(url, self._baseUrl)
            if media_upload.resumable():
                url = _add_query_parameter(url, "uploadType", "resumable")

            if media_upload.resumable():
                # This is all we need to do for resumable, if the body exists it gets
                # sent in the first request, otherwise an empty body is sent.
                resumable = media_upload
            else:
                # A non-resumable upload
                if body is None:
                    # This is a simple media upload
                    headers["content-type"] = media_upload.mimetype()
                    body = media_upload.getbytes(0, media_upload.size())
                    url = _add_query_parameter(url, "uploadType", "media")
                else:
                    # This is a multipart/related upload.
                    msgRoot = MIMEMultipart("related")
                    # msgRoot should not write out it's own headers
                    setattr(msgRoot, "_write_headers", lambda self: None)

                    # attach the body as one part
                    msg = MIMENonMultipart(*headers["content-type"].split("/"))
                    msg.set_payload(body)
                    msgRoot.attach(msg)

                    # attach the media as the second part
                    msg = MIMENonMultipart(*media_upload.mimetype().split("/"))
                    msg["Content-Transfer-Encoding"] = "binary"

                    payload = media_upload.getbytes(0, media_upload.size())
                    msg.set_payload(payload)
                    msgRoot.attach(msg)
                    # encode the body: note that we can't use `as_string`, because
                    # it plays games with `From ` lines.
                    fp = io.BytesIO()
                    g = _BytesGenerator(fp, mangle_from_=False)
                    g.flatten(msgRoot, unixfrom=False)
                    body = fp.getvalue()

                    multipart_boundary = msgRoot.get_boundary()
                    headers["content-type"] = (
                        "multipart/related; " 'boundary="%s"'
                    ) % multipart_boundary
                    url = _add_query_parameter(url, "uploadType", "multipart")

        logger.debug("URL being requested: %s %s" % (httpMethod, url))
        return self._requestBuilder(
            self._http,
            model.response,
            url,
            method=httpMethod,
            body=body,
            headers=headers,
            methodId=methodId,
            resumable=resumable,
        )

    docs = [methodDesc.get("description", DEFAULT_METHOD_DOC), "\n\n"]
    if len(parameters.argmap) > 0:
        docs.append("Args:\n")

    # Skip undocumented params and params common to all methods.
    skip_parameters = list(rootDesc.get("parameters", {}).keys())
    skip_parameters.extend(STACK_QUERY_PARAMETERS)

    all_args = list(parameters.argmap.keys())
    args_ordered = [key2param(s) for s in methodDesc.get("parameterOrder", [])]

    # Move body to the front of the line.
    if "body" in all_args:
        args_ordered.append("body")

    for name in sorted(all_args):
        if name not in args_ordered:
            args_ordered.append(name)

    for arg in args_ordered:
        if arg in skip_parameters:
            continue

        repeated = ""
        if arg in parameters.repeated_params:
            repeated = " (repeated)"
        required = ""
        if arg in parameters.required_params:
            required = " (required)"
        paramdesc = methodDesc["parameters"][parameters.argmap[arg]]
        paramdoc = paramdesc.get("description", "A parameter")
        if "$ref" in paramdesc:
            docs.append(
                ("  %s: object, %s%s%s\n    The object takes the form of:\n\n%s\n\n")
                % (
                    arg,
                    paramdoc,
                    required,
                    repeated,
                    schema.prettyPrintByName(paramdesc["$ref"]),
                )
            )
        else:
            paramtype = paramdesc.get("type", "string")
            docs.append(
                "  %s: %s, %s%s%s\n" % (arg, paramtype, paramdoc, required, repeated)
            )
        enum = paramdesc.get("enum", [])
        enumDesc = paramdesc.get("enumDescriptions", [])
        if enum and enumDesc:
            docs.append("    Allowed values\n")
            for (name, desc) in zip(enum, enumDesc):
                docs.append("      %s - %s\n" % (name, desc))
    if "response" in methodDesc:
        if methodName.endswith("_media"):
            docs.append("\nReturns:\n  The media object as a string.\n\n    ")
        else:
            docs.append("\nReturns:\n  An object of the form:\n\n    ")
            docs.append(schema.prettyPrintSchema(methodDesc["response"]))

    setattr(method, "__doc__", "".join(docs))
    return (methodName, method)


def createNextMethod(
    methodName,
    pageTokenName="pageToken",
    nextPageTokenName="nextPageToken",
    isPageTokenParameter=True,
):
    """Creates any _next methods for attaching to a Resource.

    The _next methods allow for easy iteration through list() responses.

    Args:
      methodName: string, name of the method to use.
      pageTokenName: string, name of request page token field.
      nextPageTokenName: string, name of response page token field.
      isPageTokenParameter: Boolean, True if request page token is a query
          parameter, False if request page token is a field of the request body.
    """
    methodName = fix_method_name(methodName)

    def methodNext(self, previous_request, previous_response):
        """Retrieves the next page of results.

        Args:
          previous_request: The request for the previous page. (required)
          previous_response: The response from the request for the previous page. (required)

        Returns:
          A request object that you can call 'execute()' on to request the next
          page. Returns None if there are no more items in the collection.
        """
        # Retrieve nextPageToken from previous_response
        # Use as pageToken in previous_request to create new request.

        nextPageToken = previous_response.get(nextPageTokenName, None)
        if not nextPageToken:
            return None

        request = copy.copy(previous_request)

        if isPageTokenParameter:
            # Replace pageToken value in URI
            request.uri = _add_query_parameter(
                request.uri, pageTokenName, nextPageToken
            )
            logger.debug("Next page request URL: %s %s" % (methodName, request.uri))
        else:
            # Replace pageToken value in request body
            model = self._model
            body = model.deserialize(request.body)
            body[pageTokenName] = nextPageToken
            request.body = model.serialize(body)
            request.body_size = len(request.body)
            if "content-length" in request.headers:
                del request.headers["content-length"]
            logger.debug("Next page request body: %s %s" % (methodName, body))

        return request

    return (methodName, methodNext)


class Resource(object):
    """A class for interacting with a resource."""

    def __init__(
        self,
        http,
        baseUrl,
        model,
        requestBuilder,
        developerKey,
        resourceDesc,
        rootDesc,
        schema,
        universe_domain=universe.DEFAULT_UNIVERSE if HAS_UNIVERSE else "",
    ):
        """Build a Resource from the API description.

        Args:
          http: httplib2.Http, Object to make http requests with.
          baseUrl: string, base URL for the API. All requests are relative to this
              URI.
          model: googleapiclient.Model, converts to and from the wire format.
          requestBuilder: class or callable that instantiates an
              googleapiclient.HttpRequest object.
          developerKey: string, key obtained from
              https://code.google.com/apis/console
          resourceDesc: object, section of deserialized discovery document that
              describes a resource. Note that the top level discovery document
              is considered a resource.
          rootDesc: object, the entire deserialized discovery document.
          schema: object, mapping of schema names to schema descriptions.
          universe_domain: string, the universe for the API. The default universe
          is "googleapis.com".
        """
        self._dynamic_attrs = []

        self._http = http
        self._baseUrl = baseUrl
        self._model = model
        self._developerKey = developerKey
        self._requestBuilder = requestBuilder
        self._resourceDesc = resourceDesc
        self._rootDesc = rootDesc
        self._schema = schema
        self._universe_domain = universe_domain
        self._credentials_validated = False

        self._set_service_methods()

    def _set_dynamic_attr(self, attr_name, value):
        """Sets an instance attribute and tracks it in a list of dynamic attributes.

        Args:
          attr_name: string; The name of the attribute to be set
          value: The value being set on the object and tracked in the dynamic cache.
        """
        self._dynamic_attrs.append(attr_name)
        self.__dict__[attr_name] = value

    def __getstate__(self):
        """Trim the state down to something that can be pickled.

        Uses the fact that the instance variable _dynamic_attrs holds attrs that
        will be wiped and restored on pickle serialization.
        """
        state_dict = copy.copy(self.__dict__)
        for dynamic_attr in self._dynamic_attrs:
            del state_dict[dynamic_attr]
        del state_dict["_dynamic_attrs"]
        return state_dict

    def __setstate__(self, state):
        """Reconstitute the state of the object from being pickled.

        Uses the fact that the instance variable _dynamic_attrs holds attrs that
        will be wiped and restored on pickle serialization.
        """
        self.__dict__.update(state)
        self._dynamic_attrs = []
        self._set_service_methods()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, exc_tb):
        self.close()

    def close(self):
        """Close httplib2 connections."""
        # httplib2 leaves sockets open by default.
        # Cleanup using the `close` method.
        # https://github.com/httplib2/httplib2/issues/148
        self._http.close()

    def _set_service_methods(self):
        self._add_basic_methods(self._resourceDesc, self._rootDesc, self._schema)
        self._add_nested_resources(self._resourceDesc, self._rootDesc, self._schema)
        self._add_next_methods(self._resourceDesc, self._schema)

    def _add_basic_methods(self, resourceDesc, rootDesc, schema):
        # If this is the root Resource, add a new_batch_http_request() method.
        if resourceDesc == rootDesc:
            batch_uri = "%s%s" % (
                rootDesc["rootUrl"],
                rootDesc.get("batchPath", "batch"),
            )

            def new_batch_http_request(callback=None):
                """Create a BatchHttpRequest object based on the discovery document.

                Args:
                  callback: callable, A callback to be called for each response, of the
                    form callback(id, response, exception). The first parameter is the
                    request id, and the second is the deserialized response object. The
                    third is an apiclient.errors.HttpError exception object if an HTTP
                    error occurred while processing the request, or None if no error
                    occurred.

                Returns:
                  A BatchHttpRequest object based on the discovery document.
                """
                return BatchHttpRequest(callback=callback, batch_uri=batch_uri)

            self._set_dynamic_attr("new_batch_http_request", new_batch_http_request)

        # Add basic methods to Resource
        if "methods" in resourceDesc:
            for methodName, methodDesc in resourceDesc["methods"].items():
                fixedMethodName, method = createMethod(
                    methodName, methodDesc, rootDesc, schema
                )
                self._set_dynamic_attr(
                    fixedMethodName, method.__get__(self, self.__class__)
                )
                # Add in _media methods. The functionality of the attached method will
                # change when it sees that the method name ends in _media.
                if methodDesc.get("supportsMediaDownload", False):
                    fixedMethodName, method = createMethod(
                        methodName + "_media", methodDesc, rootDesc, schema
                    )
                    self._set_dynamic_attr(
                        fixedMethodName, method.__get__(self, self.__class__)
                    )

    def _add_nested_resources(self, resourceDesc, rootDesc, schema):
        # Add in nested resources
        if "resources" in resourceDesc:

            def createResourceMethod(methodName, methodDesc):
                """Create a method on the Resource to access a nested Resource.

                Args:
                  methodName: string, name of the method to use.
                  methodDesc: object, fragment of deserialized discovery document that
                    describes the method.
                """
                methodName = fix_method_name(methodName)

                def methodResource(self):
                    return Resource(
                        http=self._http,
                        baseUrl=self._baseUrl,
                        model=self._model,
                        developerKey=self._developerKey,
                        requestBuilder=self._requestBuilder,
                        resourceDesc=methodDesc,
                        rootDesc=rootDesc,
                        schema=schema,
                        universe_domain=self._universe_domain,
                    )

                setattr(methodResource, "__doc__", "A collection resource.")
                setattr(methodResource, "__is_resource__", True)

                return (methodName, methodResource)

            for methodName, methodDesc in resourceDesc["resources"].items():
                fixedMethodName, method = createResourceMethod(methodName, methodDesc)
                self._set_dynamic_attr(
                    fixedMethodName, method.__get__(self, self.__class__)
                )

    def _add_next_methods(self, resourceDesc, schema):
        # Add _next() methods if and only if one of the names 'pageToken' or
        # 'nextPageToken' occurs among the fields of both the method's response
        # type either the method's request (query parameters) or request body.
        if "methods" not in resourceDesc:
            return
        for methodName, methodDesc in resourceDesc["methods"].items():
            nextPageTokenName = _findPageTokenName(
                _methodProperties(methodDesc, schema, "response")
            )
            if not nextPageTokenName:
                continue
            isPageTokenParameter = True
            pageTokenName = _findPageTokenName(methodDesc.get("parameters", {}))
            if not pageTokenName:
                isPageTokenParameter = False
                pageTokenName = _findPageTokenName(
                    _methodProperties(methodDesc, schema, "request")
                )
            if not pageTokenName:
                continue
            fixedMethodName, method = createNextMethod(
                methodName + "_next",
                pageTokenName,
                nextPageTokenName,
                isPageTokenParameter,
            )
            self._set_dynamic_attr(
                fixedMethodName, method.__get__(self, self.__class__)
            )

    def _validate_credentials(self):
        """Validates client's and credentials' universe domains are consistent.

        Returns:
            bool: True iff the configured universe domain is valid.

        Raises:
            UniverseMismatchError: If the configured universe domain is not valid.
        """
        credentials = getattr(self._http, "credentials", None)

        self._credentials_validated = (
            (
                self._credentials_validated
                or universe.compare_domains(self._universe_domain, credentials)
            )
            if HAS_UNIVERSE
            else True
        )
        return self._credentials_validated


def _findPageTokenName(fields):
    """Search field names for one like a page token.

    Args:
      fields: container of string, names of fields.

    Returns:
      First name that is either 'pageToken' or 'nextPageToken' if one exists,
      otherwise None.
    """
    return next(
        (tokenName for tokenName in _PAGE_TOKEN_NAMES if tokenName in fields), None
    )


def _methodProperties(methodDesc, schema, name):
    """Get properties of a field in a method description.

    Args:
      methodDesc: object, fragment of deserialized discovery document that
        describes the method.
      schema: object, mapping of schema names to schema descriptions.
      name: string, name of top-level field in method description.

    Returns:
      Object representing fragment of deserialized discovery document
      corresponding to 'properties' field of object corresponding to named field
      in method description, if it exists, otherwise empty dict.
    """
    desc = methodDesc.get(name, {})
    if "$ref" in desc:
        desc = schema.get(desc["$ref"], {})
    return desc.get("properties", {})

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc5280.py ===
# coding: utf-8
#
# This file is part of pyasn1-modules software.
#
# Created by Stanisław Pitucha with asn1ate tool.
# Updated by Russ Housley for ORAddress Extension Attribute opentype support.
# Updated by Russ Housley for AlgorithmIdentifier opentype support.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pyasn1/license.html
#
# Internet X.509 Public Key Infrastructure Certificate and Certificate
# Revocation List (CRL) Profile
#
# ASN.1 source from:
# https://www.rfc-editor.org/rfc/rfc5280.txt
#
from pyasn1.type import char
from pyasn1.type import constraint
from pyasn1.type import namedtype
from pyasn1.type import namedval
from pyasn1.type import opentype
from pyasn1.type import tag
from pyasn1.type import univ
from pyasn1.type import useful

MAX = float('inf')


def _buildOid(*components):
    output = []
    for x in tuple(components):
        if isinstance(x, univ.ObjectIdentifier):
            output.extend(list(x))
        else:
            output.append(int(x))

    return univ.ObjectIdentifier(output)


ub_e163_4_sub_address_length = univ.Integer(40)

ub_e163_4_number_length = univ.Integer(15)

unformatted_postal_address = univ.Integer(16)


class TerminalType(univ.Integer):
    pass


TerminalType.namedValues = namedval.NamedValues(
    ('telex', 3),
    ('teletex', 4),
    ('g3-facsimile', 5),
    ('g4-facsimile', 6),
    ('ia5-terminal', 7),
    ('videotex', 8)
)


class Extension(univ.Sequence):
    pass


Extension.componentType = namedtype.NamedTypes(
    namedtype.NamedType('extnID', univ.ObjectIdentifier()),
    namedtype.DefaultedNamedType('critical', univ.Boolean().subtype(value=0)),
    namedtype.NamedType('extnValue', univ.OctetString())
)


class Extensions(univ.SequenceOf):
    pass


Extensions.componentType = Extension()
Extensions.sizeSpec = constraint.ValueSizeConstraint(1, MAX)

physical_delivery_personal_name = univ.Integer(13)

ub_unformatted_address_length = univ.Integer(180)

ub_pds_parameter_length = univ.Integer(30)

ub_pds_physical_address_lines = univ.Integer(6)


class UnformattedPostalAddress(univ.Set):
    pass


UnformattedPostalAddress.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('printable-address', univ.SequenceOf(componentType=char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_pds_parameter_length)))),
    namedtype.OptionalNamedType('teletex-string', char.TeletexString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_unformatted_address_length)))
)

ub_organization_name = univ.Integer(64)


class X520OrganizationName(univ.Choice):
    pass


X520OrganizationName.componentType = namedtype.NamedTypes(
    namedtype.NamedType('teletexString', char.TeletexString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_organization_name))),
    namedtype.NamedType('printableString', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_organization_name))),
    namedtype.NamedType('universalString', char.UniversalString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_organization_name))),
    namedtype.NamedType('utf8String',
                        char.UTF8String().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_organization_name))),
    namedtype.NamedType('bmpString',
                        char.BMPString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_organization_name)))
)

ub_x121_address_length = univ.Integer(16)

pds_name = univ.Integer(7)

id_pkix = _buildOid(1, 3, 6, 1, 5, 5, 7)

id_kp = _buildOid(id_pkix, 3)

ub_postal_code_length = univ.Integer(16)


class PostalCode(univ.Choice):
    pass


PostalCode.componentType = namedtype.NamedTypes(
    namedtype.NamedType('numeric-code', char.NumericString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_postal_code_length))),
    namedtype.NamedType('printable-code', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_postal_code_length)))
)

ub_generation_qualifier_length = univ.Integer(3)

unique_postal_name = univ.Integer(20)


class DomainComponent(char.IA5String):
    pass


ub_domain_defined_attribute_value_length = univ.Integer(128)

ub_match = univ.Integer(128)

id_at = _buildOid(2, 5, 4)


class AttributeType(univ.ObjectIdentifier):
    pass


id_at_organizationalUnitName = _buildOid(id_at, 11)

terminal_type = univ.Integer(23)


class PDSParameter(univ.Set):
    pass


PDSParameter.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('printable-string', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_pds_parameter_length))),
    namedtype.OptionalNamedType('teletex-string', char.TeletexString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_pds_parameter_length)))
)


class PhysicalDeliveryPersonalName(PDSParameter):
    pass


ub_surname_length = univ.Integer(40)

id_ad = _buildOid(id_pkix, 48)

ub_domain_defined_attribute_type_length = univ.Integer(8)


class TeletexDomainDefinedAttribute(univ.Sequence):
    pass


TeletexDomainDefinedAttribute.componentType = namedtype.NamedTypes(
    namedtype.NamedType('type', char.TeletexString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_domain_defined_attribute_type_length))),
    namedtype.NamedType('value', char.TeletexString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_domain_defined_attribute_value_length)))
)

ub_domain_defined_attributes = univ.Integer(4)


class TeletexDomainDefinedAttributes(univ.SequenceOf):
    pass


TeletexDomainDefinedAttributes.componentType = TeletexDomainDefinedAttribute()
TeletexDomainDefinedAttributes.sizeSpec = constraint.ValueSizeConstraint(1, ub_domain_defined_attributes)

extended_network_address = univ.Integer(22)

ub_locality_name = univ.Integer(128)


class X520LocalityName(univ.Choice):
    pass


X520LocalityName.componentType = namedtype.NamedTypes(
    namedtype.NamedType('teletexString',
                        char.TeletexString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_locality_name))),
    namedtype.NamedType('printableString', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_locality_name))),
    namedtype.NamedType('universalString', char.UniversalString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_locality_name))),
    namedtype.NamedType('utf8String',
                        char.UTF8String().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_locality_name))),
    namedtype.NamedType('bmpString',
                        char.BMPString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_locality_name)))
)

teletex_organization_name = univ.Integer(3)

ub_given_name_length = univ.Integer(16)

ub_initials_length = univ.Integer(5)


class PersonalName(univ.Set):
    pass


PersonalName.componentType = namedtype.NamedTypes(
    namedtype.NamedType('surname', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_surname_length)).subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.OptionalNamedType('given-name', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_given_name_length)).subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.OptionalNamedType('initials', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_initials_length)).subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
    namedtype.OptionalNamedType('generation-qualifier', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_generation_qualifier_length)).subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3)))
)

ub_organizational_unit_name_length = univ.Integer(32)


class OrganizationalUnitName(char.PrintableString):
    pass


OrganizationalUnitName.subtypeSpec = constraint.ValueSizeConstraint(1, ub_organizational_unit_name_length)

id_at_generationQualifier = _buildOid(id_at, 44)


class Version(univ.Integer):
    pass


Version.namedValues = namedval.NamedValues(
    ('v1', 0),
    ('v2', 1),
    ('v3', 2)
)


class CertificateSerialNumber(univ.Integer):
    pass


algorithmIdentifierMap = {}


class AlgorithmIdentifier(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('algorithm', univ.ObjectIdentifier()),
        namedtype.OptionalNamedType('parameters', univ.Any(),
            openType=opentype.OpenType('algorithm', algorithmIdentifierMap)
        )
    )


class Time(univ.Choice):
    pass


Time.componentType = namedtype.NamedTypes(
    namedtype.NamedType('utcTime', useful.UTCTime()),
    namedtype.NamedType('generalTime', useful.GeneralizedTime())
)


class AttributeValue(univ.Any):
    pass


certificateAttributesMap = {}


class AttributeTypeAndValue(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('type', AttributeType()),
        namedtype.NamedType(
            'value', AttributeValue(),
            openType=opentype.OpenType('type', certificateAttributesMap)
        )
    )


class RelativeDistinguishedName(univ.SetOf):
    pass


RelativeDistinguishedName.componentType = AttributeTypeAndValue()
RelativeDistinguishedName.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class RDNSequence(univ.SequenceOf):
    pass


RDNSequence.componentType = RelativeDistinguishedName()


class Name(univ.Choice):
    pass


Name.componentType = namedtype.NamedTypes(
    namedtype.NamedType('rdnSequence', RDNSequence())
)


class TBSCertList(univ.Sequence):
    pass


TBSCertList.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('version', Version()),
    namedtype.NamedType('signature', AlgorithmIdentifier()),
    namedtype.NamedType('issuer', Name()),
    namedtype.NamedType('thisUpdate', Time()),
    namedtype.OptionalNamedType('nextUpdate', Time()),
    namedtype.OptionalNamedType(
        'revokedCertificates', univ.SequenceOf(
            componentType=univ.Sequence(
                componentType=namedtype.NamedTypes(
                    namedtype.NamedType('userCertificate', CertificateSerialNumber()),
                    namedtype.NamedType('revocationDate', Time()),
                    namedtype.OptionalNamedType('crlEntryExtensions', Extensions())
                )
            )
        )
    ),
    namedtype.OptionalNamedType(
        'crlExtensions', Extensions().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)))
)


class CertificateList(univ.Sequence):
    pass


CertificateList.componentType = namedtype.NamedTypes(
    namedtype.NamedType('tbsCertList', TBSCertList()),
    namedtype.NamedType('signatureAlgorithm', AlgorithmIdentifier()),
    namedtype.NamedType('signature', univ.BitString())
)


class PhysicalDeliveryOfficeName(PDSParameter):
    pass


ub_extension_attributes = univ.Integer(256)

certificateExtensionsMap = {
}

oraddressExtensionAttributeMap = {
}


class ExtensionAttribute(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType(
            'extension-attribute-type',
            univ.Integer().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, ub_extension_attributes)).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.NamedType(
            'extension-attribute-value',
            univ.Any().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)),
            openType=opentype.OpenType('extension-attribute-type', oraddressExtensionAttributeMap))
    )

id_qt = _buildOid(id_pkix, 2)

id_qt_cps = _buildOid(id_qt, 1)

id_at_stateOrProvinceName = _buildOid(id_at, 8)

id_at_title = _buildOid(id_at, 12)

id_at_serialNumber = _buildOid(id_at, 5)


class X520dnQualifier(char.PrintableString):
    pass


class PosteRestanteAddress(PDSParameter):
    pass


poste_restante_address = univ.Integer(19)


class UniqueIdentifier(univ.BitString):
    pass


class Validity(univ.Sequence):
    pass


Validity.componentType = namedtype.NamedTypes(
    namedtype.NamedType('notBefore', Time()),
    namedtype.NamedType('notAfter', Time())
)


class SubjectPublicKeyInfo(univ.Sequence):
    pass


SubjectPublicKeyInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('algorithm', AlgorithmIdentifier()),
    namedtype.NamedType('subjectPublicKey', univ.BitString())
)


class TBSCertificate(univ.Sequence):
    pass


TBSCertificate.componentType = namedtype.NamedTypes(
    namedtype.DefaultedNamedType('version',
                                 Version().subtype(explicitTag=tag.Tag(tag.tagClassContext,
                                                                       tag.tagFormatSimple, 0)).subtype(value="v1")),
    namedtype.NamedType('serialNumber', CertificateSerialNumber()),
    namedtype.NamedType('signature', AlgorithmIdentifier()),
    namedtype.NamedType('issuer', Name()),
    namedtype.NamedType('validity', Validity()),
    namedtype.NamedType('subject', Name()),
    namedtype.NamedType('subjectPublicKeyInfo', SubjectPublicKeyInfo()),
    namedtype.OptionalNamedType('issuerUniqueID', UniqueIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.OptionalNamedType('subjectUniqueID', UniqueIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
    namedtype.OptionalNamedType('extensions',
                                Extensions().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3)))
)

physical_delivery_office_name = univ.Integer(10)

ub_name = univ.Integer(32768)


class X520name(univ.Choice):
    pass


X520name.componentType = namedtype.NamedTypes(
    namedtype.NamedType('teletexString',
                        char.TeletexString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_name))),
    namedtype.NamedType('printableString',
                        char.PrintableString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_name))),
    namedtype.NamedType('universalString',
                        char.UniversalString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_name))),
    namedtype.NamedType('utf8String',
                        char.UTF8String().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_name))),
    namedtype.NamedType('bmpString', char.BMPString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_name)))
)

id_at_dnQualifier = _buildOid(id_at, 46)

ub_serial_number = univ.Integer(64)

ub_pseudonym = univ.Integer(128)

pkcs_9 = _buildOid(1, 2, 840, 113549, 1, 9)


class X121Address(char.NumericString):
    pass


X121Address.subtypeSpec = constraint.ValueSizeConstraint(1, ub_x121_address_length)


class NetworkAddress(X121Address):
    pass


ub_integer_options = univ.Integer(256)

id_at_commonName = _buildOid(id_at, 3)

ub_organization_name_length = univ.Integer(64)

id_ad_ocsp = _buildOid(id_ad, 1)

ub_country_name_numeric_length = univ.Integer(3)

ub_country_name_alpha_length = univ.Integer(2)


class PhysicalDeliveryCountryName(univ.Choice):
    pass


PhysicalDeliveryCountryName.componentType = namedtype.NamedTypes(
    namedtype.NamedType('x121-dcc-code', char.NumericString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(ub_country_name_numeric_length, ub_country_name_numeric_length))),
    namedtype.NamedType('iso-3166-alpha2-code', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(ub_country_name_alpha_length, ub_country_name_alpha_length)))
)

id_emailAddress = _buildOid(pkcs_9, 1)

common_name = univ.Integer(1)


class X520Pseudonym(univ.Choice):
    pass


X520Pseudonym.componentType = namedtype.NamedTypes(
    namedtype.NamedType('teletexString',
                        char.TeletexString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_pseudonym))),
    namedtype.NamedType('printableString',
                        char.PrintableString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_pseudonym))),
    namedtype.NamedType('universalString',
                        char.UniversalString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_pseudonym))),
    namedtype.NamedType('utf8String',
                        char.UTF8String().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_pseudonym))),
    namedtype.NamedType('bmpString',
                        char.BMPString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_pseudonym)))
)

ub_domain_name_length = univ.Integer(16)


class AdministrationDomainName(univ.Choice):
    pass


AdministrationDomainName.tagSet = univ.Choice.tagSet.tagExplicitly(
    tag.Tag(tag.tagClassApplication, tag.tagFormatConstructed, 2))
AdministrationDomainName.componentType = namedtype.NamedTypes(
    namedtype.NamedType('numeric', char.NumericString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(0, ub_domain_name_length))),
    namedtype.NamedType('printable', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(0, ub_domain_name_length)))
)


class PresentationAddress(univ.Sequence):
    pass


PresentationAddress.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('pSelector', univ.OctetString().subtype(
        explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.OptionalNamedType('sSelector', univ.OctetString().subtype(
        explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.OptionalNamedType('tSelector', univ.OctetString().subtype(
        explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
    namedtype.NamedType('nAddresses', univ.SetOf(componentType=univ.OctetString()).subtype(
        explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3)))
)


class ExtendedNetworkAddress(univ.Choice):
    pass


ExtendedNetworkAddress.componentType = namedtype.NamedTypes(
    namedtype.NamedType(
        'e163-4-address', univ.Sequence(
            componentType=namedtype.NamedTypes(
                namedtype.NamedType('number', char.NumericString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_e163_4_number_length)).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
                namedtype.OptionalNamedType('sub-address', char.NumericString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_e163_4_sub_address_length)).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
            )
        )
    ),
    namedtype.NamedType('psap-address', PresentationAddress().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0)))
)


class TeletexOrganizationName(char.TeletexString):
    pass


TeletexOrganizationName.subtypeSpec = constraint.ValueSizeConstraint(1, ub_organization_name_length)

ub_terminal_id_length = univ.Integer(24)


class TerminalIdentifier(char.PrintableString):
    pass


TerminalIdentifier.subtypeSpec = constraint.ValueSizeConstraint(1, ub_terminal_id_length)

id_ad_caIssuers = _buildOid(id_ad, 2)

id_at_countryName = _buildOid(id_at, 6)


class StreetAddress(PDSParameter):
    pass


postal_code = univ.Integer(9)

id_at_givenName = _buildOid(id_at, 42)

ub_title = univ.Integer(64)


class ExtensionAttributes(univ.SetOf):
    pass


ExtensionAttributes.componentType = ExtensionAttribute()
ExtensionAttributes.sizeSpec = constraint.ValueSizeConstraint(1, ub_extension_attributes)

ub_emailaddress_length = univ.Integer(255)

id_ad_caRepository = _buildOid(id_ad, 5)


class ExtensionORAddressComponents(PDSParameter):
    pass


ub_organizational_unit_name = univ.Integer(64)


class X520OrganizationalUnitName(univ.Choice):
    pass


X520OrganizationalUnitName.componentType = namedtype.NamedTypes(
    namedtype.NamedType('teletexString', char.TeletexString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_organizational_unit_name))),
    namedtype.NamedType('printableString', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_organizational_unit_name))),
    namedtype.NamedType('universalString', char.UniversalString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_organizational_unit_name))),
    namedtype.NamedType('utf8String', char.UTF8String().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_organizational_unit_name))),
    namedtype.NamedType('bmpString', char.BMPString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_organizational_unit_name)))
)


class LocalPostalAttributes(PDSParameter):
    pass


teletex_organizational_unit_names = univ.Integer(5)


class X520Title(univ.Choice):
    pass


X520Title.componentType = namedtype.NamedTypes(
    namedtype.NamedType('teletexString',
                        char.TeletexString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_title))),
    namedtype.NamedType('printableString',
                        char.PrintableString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_title))),
    namedtype.NamedType('universalString',
                        char.UniversalString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_title))),
    namedtype.NamedType('utf8String',
                        char.UTF8String().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_title))),
    namedtype.NamedType('bmpString', char.BMPString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_title)))
)

id_at_localityName = _buildOid(id_at, 7)

id_at_initials = _buildOid(id_at, 43)

ub_state_name = univ.Integer(128)


class X520StateOrProvinceName(univ.Choice):
    pass


X520StateOrProvinceName.componentType = namedtype.NamedTypes(
    namedtype.NamedType('teletexString',
                        char.TeletexString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_state_name))),
    namedtype.NamedType('printableString',
                        char.PrintableString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_state_name))),
    namedtype.NamedType('universalString',
                        char.UniversalString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_state_name))),
    namedtype.NamedType('utf8String',
                        char.UTF8String().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_state_name))),
    namedtype.NamedType('bmpString',
                        char.BMPString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_state_name)))
)

physical_delivery_organization_name = univ.Integer(14)

id_at_surname = _buildOid(id_at, 4)


class X520countryName(char.PrintableString):
    pass


X520countryName.subtypeSpec = constraint.ValueSizeConstraint(2, 2)

physical_delivery_office_number = univ.Integer(11)

id_qt_unotice = _buildOid(id_qt, 2)


class X520SerialNumber(char.PrintableString):
    pass


X520SerialNumber.subtypeSpec = constraint.ValueSizeConstraint(1, ub_serial_number)


class Attribute(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('type', AttributeType()),
        namedtype.NamedType('values',
                            univ.SetOf(componentType=AttributeValue()),
                            openType=opentype.OpenType('type', certificateAttributesMap))
    )

ub_common_name = univ.Integer(64)

id_pe = _buildOid(id_pkix, 1)


class ExtensionPhysicalDeliveryAddressComponents(PDSParameter):
    pass


class EmailAddress(char.IA5String):
    pass


EmailAddress.subtypeSpec = constraint.ValueSizeConstraint(1, ub_emailaddress_length)

id_at_organizationName = _buildOid(id_at, 10)

post_office_box_address = univ.Integer(18)


class BuiltInDomainDefinedAttribute(univ.Sequence):
    pass


BuiltInDomainDefinedAttribute.componentType = namedtype.NamedTypes(
    namedtype.NamedType('type', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_domain_defined_attribute_type_length))),
    namedtype.NamedType('value', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_domain_defined_attribute_value_length)))
)


class BuiltInDomainDefinedAttributes(univ.SequenceOf):
    pass


BuiltInDomainDefinedAttributes.componentType = BuiltInDomainDefinedAttribute()
BuiltInDomainDefinedAttributes.sizeSpec = constraint.ValueSizeConstraint(1, ub_domain_defined_attributes)

id_at_pseudonym = _buildOid(id_at, 65)

id_domainComponent = _buildOid(0, 9, 2342, 19200300, 100, 1, 25)


class X520CommonName(univ.Choice):
    pass


X520CommonName.componentType = namedtype.NamedTypes(
    namedtype.NamedType('teletexString',
                        char.TeletexString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_common_name))),
    namedtype.NamedType('printableString',
                        char.PrintableString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_common_name))),
    namedtype.NamedType('universalString',
                        char.UniversalString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_common_name))),
    namedtype.NamedType('utf8String',
                        char.UTF8String().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_common_name))),
    namedtype.NamedType('bmpString',
                        char.BMPString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_common_name)))
)

extension_OR_address_components = univ.Integer(12)

ub_organizational_units = univ.Integer(4)

teletex_personal_name = univ.Integer(4)

ub_numeric_user_id_length = univ.Integer(32)

ub_common_name_length = univ.Integer(64)


class TeletexCommonName(char.TeletexString):
    pass


TeletexCommonName.subtypeSpec = constraint.ValueSizeConstraint(1, ub_common_name_length)


class PhysicalDeliveryOrganizationName(PDSParameter):
    pass


extension_physical_delivery_address_components = univ.Integer(15)


class NumericUserIdentifier(char.NumericString):
    pass


NumericUserIdentifier.subtypeSpec = constraint.ValueSizeConstraint(1, ub_numeric_user_id_length)


class CountryName(univ.Choice):
    pass


CountryName.tagSet = univ.Choice.tagSet.tagExplicitly(tag.Tag(tag.tagClassApplication, tag.tagFormatConstructed, 1))
CountryName.componentType = namedtype.NamedTypes(
    namedtype.NamedType('x121-dcc-code', char.NumericString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(ub_country_name_numeric_length, ub_country_name_numeric_length))),
    namedtype.NamedType('iso-3166-alpha2-code', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(ub_country_name_alpha_length, ub_country_name_alpha_length)))
)


class OrganizationName(char.PrintableString):
    pass


OrganizationName.subtypeSpec = constraint.ValueSizeConstraint(1, ub_organization_name_length)


class OrganizationalUnitNames(univ.SequenceOf):
    pass


OrganizationalUnitNames.componentType = OrganizationalUnitName()
OrganizationalUnitNames.sizeSpec = constraint.ValueSizeConstraint(1, ub_organizational_units)


class PrivateDomainName(univ.Choice):
    pass


PrivateDomainName.componentType = namedtype.NamedTypes(
    namedtype.NamedType('numeric', char.NumericString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_domain_name_length))),
    namedtype.NamedType('printable', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_domain_name_length)))
)


class BuiltInStandardAttributes(univ.Sequence):
    pass


BuiltInStandardAttributes.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('country-name', CountryName()),
    namedtype.OptionalNamedType('administration-domain-name', AdministrationDomainName()),
    namedtype.OptionalNamedType('network-address', NetworkAddress().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.OptionalNamedType('terminal-identifier', TerminalIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.OptionalNamedType('private-domain-name', PrivateDomainName().subtype(
        explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 2))),
    namedtype.OptionalNamedType('organization-name', OrganizationName().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3))),
    namedtype.OptionalNamedType('numeric-user-identifier', NumericUserIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 4))),
    namedtype.OptionalNamedType('personal-name', PersonalName().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 5))),
    namedtype.OptionalNamedType('organizational-unit-names', OrganizationalUnitNames().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 6)))
)


class ORAddress(univ.Sequence):
    pass


ORAddress.componentType = namedtype.NamedTypes(
    namedtype.NamedType('built-in-standard-attributes', BuiltInStandardAttributes()),
    namedtype.OptionalNamedType('built-in-domain-defined-attributes', BuiltInDomainDefinedAttributes()),
    namedtype.OptionalNamedType('extension-attributes', ExtensionAttributes())
)


class DistinguishedName(RDNSequence):
    pass


id_ad_timeStamping = _buildOid(id_ad, 3)


class PhysicalDeliveryOfficeNumber(PDSParameter):
    pass


teletex_domain_defined_attributes = univ.Integer(6)


class UniquePostalName(PDSParameter):
    pass


physical_delivery_country_name = univ.Integer(8)

ub_pds_name_length = univ.Integer(16)


class PDSName(char.PrintableString):
    pass


PDSName.subtypeSpec = constraint.ValueSizeConstraint(1, ub_pds_name_length)


class TeletexPersonalName(univ.Set):
    pass


TeletexPersonalName.componentType = namedtype.NamedTypes(
    namedtype.NamedType('surname', char.TeletexString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_surname_length)).subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.OptionalNamedType('given-name', char.TeletexString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_given_name_length)).subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.OptionalNamedType('initials', char.TeletexString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_initials_length)).subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
    namedtype.OptionalNamedType('generation-qualifier', char.TeletexString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_generation_qualifier_length)).subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3)))
)

street_address = univ.Integer(17)


class PostOfficeBoxAddress(PDSParameter):
    pass


local_postal_attributes = univ.Integer(21)


class DirectoryString(univ.Choice):
    pass


DirectoryString.componentType = namedtype.NamedTypes(
    namedtype.NamedType('teletexString',
                        char.TeletexString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, MAX))),
    namedtype.NamedType('printableString',
                        char.PrintableString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, MAX))),
    namedtype.NamedType('universalString',
                        char.UniversalString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, MAX))),
    namedtype.NamedType('utf8String', char.UTF8String().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, MAX))),
    namedtype.NamedType('bmpString', char.BMPString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, MAX)))
)

teletex_common_name = univ.Integer(2)


class CommonName(char.PrintableString):
    pass


CommonName.subtypeSpec = constraint.ValueSizeConstraint(1, ub_common_name_length)


class Certificate(univ.Sequence):
    pass


Certificate.componentType = namedtype.NamedTypes(
    namedtype.NamedType('tbsCertificate', TBSCertificate()),
    namedtype.NamedType('signatureAlgorithm', AlgorithmIdentifier()),
    namedtype.NamedType('signature', univ.BitString())
)


class TeletexOrganizationalUnitName(char.TeletexString):
    pass


TeletexOrganizationalUnitName.subtypeSpec = constraint.ValueSizeConstraint(1, ub_organizational_unit_name_length)

id_at_name = _buildOid(id_at, 41)


class TeletexOrganizationalUnitNames(univ.SequenceOf):
    pass


TeletexOrganizationalUnitNames.componentType = TeletexOrganizationalUnitName()
TeletexOrganizationalUnitNames.sizeSpec = constraint.ValueSizeConstraint(1, ub_organizational_units)

id_ce = _buildOid(2, 5, 29)

id_ce_issuerAltName = _buildOid(id_ce, 18)


class SkipCerts(univ.Integer):
    pass


SkipCerts.subtypeSpec = constraint.ValueRangeConstraint(0, MAX)


class CRLReason(univ.Enumerated):
    pass


CRLReason.namedValues = namedval.NamedValues(
    ('unspecified', 0),
    ('keyCompromise', 1),
    ('cACompromise', 2),
    ('affiliationChanged', 3),
    ('superseded', 4),
    ('cessationOfOperation', 5),
    ('certificateHold', 6),
    ('removeFromCRL', 8),
    ('privilegeWithdrawn', 9),
    ('aACompromise', 10)
)


class PrivateKeyUsagePeriod(univ.Sequence):
    pass


PrivateKeyUsagePeriod.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('notBefore', useful.GeneralizedTime().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.OptionalNamedType('notAfter', useful.GeneralizedTime().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


anotherNameMap = {

}


class AnotherName(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('type-id', univ.ObjectIdentifier()),
        namedtype.NamedType(
            'value',
            univ.Any().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)),
            openType=opentype.OpenType('type-id', anotherNameMap)
        )
    )


class EDIPartyName(univ.Sequence):
    pass


EDIPartyName.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('nameAssigner', DirectoryString().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.NamedType('partyName', DirectoryString().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1)))
)


class GeneralName(univ.Choice):
    pass


GeneralName.componentType = namedtype.NamedTypes(
    namedtype.NamedType('otherName',
                        AnotherName().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.NamedType('rfc822Name',
                        char.IA5String().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.NamedType('dNSName',
                        char.IA5String().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
    namedtype.NamedType('x400Address',
                        ORAddress().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3))),
    namedtype.NamedType('directoryName',
                        Name().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 4))),
    namedtype.NamedType('ediPartyName',
                        EDIPartyName().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 5))),
    namedtype.NamedType('uniformResourceIdentifier',
                        char.IA5String().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 6))),
    namedtype.NamedType('iPAddress',
                        univ.OctetString().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 7))),
    namedtype.NamedType('registeredID', univ.ObjectIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 8)))
)


class BaseDistance(univ.Integer):
    pass


BaseDistance.subtypeSpec = constraint.ValueRangeConstraint(0, MAX)


class GeneralSubtree(univ.Sequence):
    pass


GeneralSubtree.componentType = namedtype.NamedTypes(
    namedtype.NamedType('base', GeneralName()),
    namedtype.DefaultedNamedType('minimum', BaseDistance().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)).subtype(value=0)),
    namedtype.OptionalNamedType('maximum', BaseDistance().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


class GeneralNames(univ.SequenceOf):
    pass


GeneralNames.componentType = GeneralName()
GeneralNames.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class DistributionPointName(univ.Choice):
    pass


DistributionPointName.componentType = namedtype.NamedTypes(
    namedtype.NamedType('fullName',
                        GeneralNames().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('nameRelativeToCRLIssuer', RelativeDistinguishedName().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


class ReasonFlags(univ.BitString):
    pass


ReasonFlags.namedValues = namedval.NamedValues(
    ('unused', 0),
    ('keyCompromise', 1),
    ('cACompromise', 2),
    ('affiliationChanged', 3),
    ('superseded', 4),
    ('cessationOfOperation', 5),
    ('certificateHold', 6),
    ('privilegeWithdrawn', 7),
    ('aACompromise', 8)
)


class IssuingDistributionPoint(univ.Sequence):
    pass


IssuingDistributionPoint.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('distributionPoint', DistributionPointName().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.DefaultedNamedType('onlyContainsUserCerts', univ.Boolean().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)).subtype(value=0)),
    namedtype.DefaultedNamedType('onlyContainsCACerts', univ.Boolean().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2)).subtype(value=0)),
    namedtype.OptionalNamedType('onlySomeReasons', ReasonFlags().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3))),
    namedtype.DefaultedNamedType('indirectCRL', univ.Boolean().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 4)).subtype(value=0)),
    namedtype.DefaultedNamedType('onlyContainsAttributeCerts', univ.Boolean().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 5)).subtype(value=0))
)

id_ce_certificatePolicies = _buildOid(id_ce, 32)

id_kp_emailProtection = _buildOid(id_kp, 4)


class AccessDescription(univ.Sequence):
    pass


AccessDescription.componentType = namedtype.NamedTypes(
    namedtype.NamedType('accessMethod', univ.ObjectIdentifier()),
    namedtype.NamedType('accessLocation', GeneralName())
)


class IssuerAltName(GeneralNames):
    pass


id_ce_cRLDistributionPoints = _buildOid(id_ce, 31)

holdInstruction = _buildOid(2, 2, 840, 10040, 2)

id_holdinstruction_callissuer = _buildOid(holdInstruction, 2)

id_ce_subjectDirectoryAttributes = _buildOid(id_ce, 9)

id_ce_issuingDistributionPoint = _buildOid(id_ce, 28)


class DistributionPoint(univ.Sequence):
    pass


DistributionPoint.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('distributionPoint', DistributionPointName().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.OptionalNamedType('reasons', ReasonFlags().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.OptionalNamedType('cRLIssuer', GeneralNames().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2)))
)


class CRLDistributionPoints(univ.SequenceOf):
    pass


CRLDistributionPoints.componentType = DistributionPoint()
CRLDistributionPoints.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class GeneralSubtrees(univ.SequenceOf):
    pass


GeneralSubtrees.componentType = GeneralSubtree()
GeneralSubtrees.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class NameConstraints(univ.Sequence):
    pass


NameConstraints.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('permittedSubtrees', GeneralSubtrees().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.OptionalNamedType('excludedSubtrees', GeneralSubtrees().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


class SubjectDirectoryAttributes(univ.SequenceOf):
    pass


SubjectDirectoryAttributes.componentType = Attribute()
SubjectDirectoryAttributes.sizeSpec = constraint.ValueSizeConstraint(1, MAX)

id_kp_OCSPSigning = _buildOid(id_kp, 9)

id_kp_timeStamping = _buildOid(id_kp, 8)


class DisplayText(univ.Choice):
    pass


DisplayText.componentType = namedtype.NamedTypes(
    namedtype.NamedType('ia5String', char.IA5String().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, 200))),
    namedtype.NamedType('visibleString',
                        char.VisibleString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, 200))),
    namedtype.NamedType('bmpString', char.BMPString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, 200))),
    namedtype.NamedType('utf8String', char.UTF8String().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, 200)))
)


class NoticeReference(univ.Sequence):
    pass


NoticeReference.componentType = namedtype.NamedTypes(
    namedtype.NamedType('organization', DisplayText()),
    namedtype.NamedType('noticeNumbers', univ.SequenceOf(componentType=univ.Integer()))
)


class UserNotice(univ.Sequence):
    pass


UserNotice.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('noticeRef', NoticeReference()),
    namedtype.OptionalNamedType('explicitText', DisplayText())
)


class PolicyQualifierId(univ.ObjectIdentifier):
    pass


policyQualifierInfoMap = {

}


class PolicyQualifierInfo(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('policyQualifierId', PolicyQualifierId()),
        namedtype.NamedType(
            'qualifier', univ.Any(),
            openType=opentype.OpenType('policyQualifierId', policyQualifierInfoMap)
        )
    )


class CertPolicyId(univ.ObjectIdentifier):
    pass


class PolicyInformation(univ.Sequence):
    pass


PolicyInformation.componentType = namedtype.NamedTypes(
    namedtype.NamedType('policyIdentifier', CertPolicyId()),
    namedtype.OptionalNamedType('policyQualifiers', univ.SequenceOf(componentType=PolicyQualifierInfo()))
)


class CertificatePolicies(univ.SequenceOf):
    pass


CertificatePolicies.componentType = PolicyInformation()
CertificatePolicies.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class SubjectAltName(GeneralNames):
    pass


id_ce_basicConstraints = _buildOid(id_ce, 19)

id_ce_authorityKeyIdentifier = _buildOid(id_ce, 35)

id_kp_codeSigning = _buildOid(id_kp, 3)


class BasicConstraints(univ.Sequence):
    pass


BasicConstraints.componentType = namedtype.NamedTypes(
    namedtype.DefaultedNamedType('cA', univ.Boolean().subtype(value=0)),
    namedtype.OptionalNamedType('pathLenConstraint',
                                univ.Integer().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, MAX)))
)

id_ce_certificateIssuer = _buildOid(id_ce, 29)


class PolicyMappings(univ.SequenceOf):
    pass


PolicyMappings.componentType = univ.Sequence(
    componentType=namedtype.NamedTypes(
        namedtype.NamedType('issuerDomainPolicy', CertPolicyId()),
        namedtype.NamedType('subjectDomainPolicy', CertPolicyId())
    )
)

PolicyMappings.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class InhibitAnyPolicy(SkipCerts):
    pass


anyPolicy = _buildOid(id_ce_certificatePolicies, 0)


class CRLNumber(univ.Integer):
    pass


CRLNumber.subtypeSpec = constraint.ValueRangeConstraint(0, MAX)


class BaseCRLNumber(CRLNumber):
    pass


id_ce_nameConstraints = _buildOid(id_ce, 30)

id_kp_serverAuth = _buildOid(id_kp, 1)

id_ce_freshestCRL = _buildOid(id_ce, 46)

id_ce_cRLReasons = _buildOid(id_ce, 21)

id_ce_extKeyUsage = _buildOid(id_ce, 37)


class KeyIdentifier(univ.OctetString):
    pass


class AuthorityKeyIdentifier(univ.Sequence):
    pass


AuthorityKeyIdentifier.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('keyIdentifier', KeyIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.OptionalNamedType('authorityCertIssuer', GeneralNames().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.OptionalNamedType('authorityCertSerialNumber', CertificateSerialNumber().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2)))
)


class FreshestCRL(CRLDistributionPoints):
    pass


id_ce_policyConstraints = _buildOid(id_ce, 36)

id_pe_authorityInfoAccess = _buildOid(id_pe, 1)


class AuthorityInfoAccessSyntax(univ.SequenceOf):
    pass


AuthorityInfoAccessSyntax.componentType = AccessDescription()
AuthorityInfoAccessSyntax.sizeSpec = constraint.ValueSizeConstraint(1, MAX)

id_holdinstruction_none = _buildOid(holdInstruction, 1)


class CPSuri(char.IA5String):
    pass


id_pe_subjectInfoAccess = _buildOid(id_pe, 11)


class SubjectKeyIdentifier(KeyIdentifier):
    pass


id_ce_subjectAltName = _buildOid(id_ce, 17)


class KeyPurposeId(univ.ObjectIdentifier):
    pass


class ExtKeyUsageSyntax(univ.SequenceOf):
    pass


ExtKeyUsageSyntax.componentType = KeyPurposeId()
ExtKeyUsageSyntax.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class HoldInstructionCode(univ.ObjectIdentifier):
    pass


id_ce_deltaCRLIndicator = _buildOid(id_ce, 27)

id_ce_keyUsage = _buildOid(id_ce, 15)

id_ce_holdInstructionCode = _buildOid(id_ce, 23)


class SubjectInfoAccessSyntax(univ.SequenceOf):
    pass


SubjectInfoAccessSyntax.componentType = AccessDescription()
SubjectInfoAccessSyntax.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class InvalidityDate(useful.GeneralizedTime):
    pass


class KeyUsage(univ.BitString):
    pass


KeyUsage.namedValues = namedval.NamedValues(
    ('digitalSignature', 0),
    ('nonRepudiation', 1),
    ('keyEncipherment', 2),
    ('dataEncipherment', 3),
    ('keyAgreement', 4),
    ('keyCertSign', 5),
    ('cRLSign', 6),
    ('encipherOnly', 7),
    ('decipherOnly', 8)
)

id_ce_invalidityDate = _buildOid(id_ce, 24)

id_ce_policyMappings = _buildOid(id_ce, 33)

anyExtendedKeyUsage = _buildOid(id_ce_extKeyUsage, 0)

id_ce_privateKeyUsagePeriod = _buildOid(id_ce, 16)

id_ce_cRLNumber = _buildOid(id_ce, 20)


class CertificateIssuer(GeneralNames):
    pass


id_holdinstruction_reject = _buildOid(holdInstruction, 3)


class PolicyConstraints(univ.Sequence):
    pass


PolicyConstraints.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('requireExplicitPolicy',
                                SkipCerts().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.OptionalNamedType('inhibitPolicyMapping',
                                SkipCerts().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)

id_kp_clientAuth = _buildOid(id_kp, 2)

id_ce_subjectKeyIdentifier = _buildOid(id_ce, 14)

id_ce_inhibitAnyPolicy = _buildOid(id_ce, 54)

# map of ORAddress ExtensionAttribute type to ExtensionAttribute value

_oraddressExtensionAttributeMapUpdate = {
    common_name: CommonName(),
    teletex_common_name: TeletexCommonName(),
    teletex_organization_name: TeletexOrganizationName(),
    teletex_personal_name: TeletexPersonalName(),
    teletex_organizational_unit_names: TeletexOrganizationalUnitNames(),
    pds_name: PDSName(),
    physical_delivery_country_name: PhysicalDeliveryCountryName(),
    postal_code: PostalCode(),
    physical_delivery_office_name: PhysicalDeliveryOfficeName(),
    physical_delivery_office_number: PhysicalDeliveryOfficeNumber(),
    extension_OR_address_components: ExtensionORAddressComponents(),
    physical_delivery_personal_name: PhysicalDeliveryPersonalName(),
    physical_delivery_organization_name: PhysicalDeliveryOrganizationName(),
    extension_physical_delivery_address_components: ExtensionPhysicalDeliveryAddressComponents(),
    unformatted_postal_address: UnformattedPostalAddress(),
    street_address: StreetAddress(),
    post_office_box_address: PostOfficeBoxAddress(),
    poste_restante_address: PosteRestanteAddress(),
    unique_postal_name: UniquePostalName(),
    local_postal_attributes: LocalPostalAttributes(),
    extended_network_address: ExtendedNetworkAddress(),
    terminal_type: TerminalType(),
    teletex_domain_defined_attributes: TeletexDomainDefinedAttributes(),
}

oraddressExtensionAttributeMap.update(_oraddressExtensionAttributeMapUpdate)


# map of AttributeType -> AttributeValue

_certificateAttributesMapUpdate = {
    id_at_name: X520name(),
    id_at_surname: X520name(),
    id_at_givenName: X520name(),
    id_at_initials: X520name(),
    id_at_generationQualifier: X520name(),
    id_at_commonName: X520CommonName(),
    id_at_localityName: X520LocalityName(),
    id_at_stateOrProvinceName: X520StateOrProvinceName(),
    id_at_organizationName: X520OrganizationName(),
    id_at_organizationalUnitName: X520OrganizationalUnitName(),
    id_at_title: X520Title(),
    id_at_dnQualifier: X520dnQualifier(),
    id_at_countryName: X520countryName(),
    id_at_serialNumber: X520SerialNumber(),
    id_at_pseudonym: X520Pseudonym(),
    id_domainComponent: DomainComponent(),
    id_emailAddress: EmailAddress(),
}

certificateAttributesMap.update(_certificateAttributesMapUpdate)


# map of Certificate Extension OIDs to Extensions

_certificateExtensionsMap = {
    id_ce_authorityKeyIdentifier: AuthorityKeyIdentifier(),
    id_ce_subjectKeyIdentifier: SubjectKeyIdentifier(),
    id_ce_keyUsage: KeyUsage(),
    id_ce_privateKeyUsagePeriod: PrivateKeyUsagePeriod(),
    id_ce_certificatePolicies: CertificatePolicies(),
    id_ce_policyMappings: PolicyMappings(),
    id_ce_subjectAltName: SubjectAltName(),
    id_ce_issuerAltName: IssuerAltName(),
    id_ce_subjectDirectoryAttributes: SubjectDirectoryAttributes(),
    id_ce_basicConstraints: BasicConstraints(),
    id_ce_nameConstraints: NameConstraints(),
    id_ce_policyConstraints: PolicyConstraints(),
    id_ce_extKeyUsage: ExtKeyUsageSyntax(),
    id_ce_cRLDistributionPoints: CRLDistributionPoints(),
    id_pe_authorityInfoAccess: AuthorityInfoAccessSyntax(),
    id_ce_cRLNumber: univ.Integer(),
    id_ce_deltaCRLIndicator: BaseCRLNumber(),
    id_ce_issuingDistributionPoint: IssuingDistributionPoint(),
    id_ce_cRLReasons: CRLReason(),
    id_ce_holdInstructionCode: univ.ObjectIdentifier(),
    id_ce_invalidityDate: useful.GeneralizedTime(),
    id_ce_certificateIssuer: GeneralNames(),
}

certificateExtensionsMap.update(_certificateExtensionsMap)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\markup.py ===
"""
    pygments.lexers.markup
    ~~~~~~~~~~~~~~~~~~~~~~

    Lexers for non-HTML markup languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexers.html import XmlLexer
from pygments.lexers.javascript import JavascriptLexer
from pygments.lexers.css import CssLexer
from pygments.lexers.lilypond import LilyPondLexer
from pygments.lexers.data import JsonLexer

from pygments.lexer import RegexLexer, DelegatingLexer, include, bygroups, \
    using, this, do_insertions, default, words
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Generic, Other, Whitespace, Literal
from pygments.util import get_bool_opt, ClassNotFound

__all__ = ['BBCodeLexer', 'MoinWikiLexer', 'RstLexer', 'TexLexer', 'GroffLexer',
           'MozPreprocHashLexer', 'MozPreprocPercentLexer',
           'MozPreprocXulLexer', 'MozPreprocJavascriptLexer',
           'MozPreprocCssLexer', 'MarkdownLexer', 'OrgLexer', 'TiddlyWiki5Lexer',
           'WikitextLexer']


class BBCodeLexer(RegexLexer):
    """
    A lexer that highlights BBCode(-like) syntax.
    """

    name = 'BBCode'
    aliases = ['bbcode']
    mimetypes = ['text/x-bbcode']
    url = 'https://www.bbcode.org/'
    version_added = '0.6'

    tokens = {
        'root': [
            (r'[^[]+', Text),
            # tag/end tag begin
            (r'\[/?\w+', Keyword, 'tag'),
            # stray bracket
            (r'\[', Text),
        ],
        'tag': [
            (r'\s+', Text),
            # attribute with value
            (r'(\w+)(=)("?[^\s"\]]+"?)',
             bygroups(Name.Attribute, Operator, String)),
            # tag argument (a la [color=green])
            (r'(=)("?[^\s"\]]+"?)',
             bygroups(Operator, String)),
            # tag end
            (r'\]', Keyword, '#pop'),
        ],
    }


class MoinWikiLexer(RegexLexer):
    """
    For MoinMoin (and Trac) Wiki markup.
    """

    name = 'MoinMoin/Trac Wiki markup'
    aliases = ['trac-wiki', 'moin']
    filenames = []
    mimetypes = ['text/x-trac-wiki']
    url = 'https://moinmo.in'
    version_added = '0.7'

    flags = re.MULTILINE | re.IGNORECASE

    tokens = {
        'root': [
            (r'^#.*$', Comment),
            (r'(!)(\S+)', bygroups(Keyword, Text)),  # Ignore-next
            # Titles
            (r'^(=+)([^=]+)(=+)(\s*#.+)?$',
             bygroups(Generic.Heading, using(this), Generic.Heading, String)),
            # Literal code blocks, with optional shebang
            (r'(\{\{\{)(\n#!.+)?', bygroups(Name.Builtin, Name.Namespace), 'codeblock'),
            (r'(\'\'\'?|\|\||`|__|~~|\^|,,|::)', Comment),  # Formatting
            # Lists
            (r'^( +)([.*-])( )', bygroups(Text, Name.Builtin, Text)),
            (r'^( +)([a-z]{1,5}\.)( )', bygroups(Text, Name.Builtin, Text)),
            # Other Formatting
            (r'\[\[\w+.*?\]\]', Keyword),  # Macro
            (r'(\[[^\s\]]+)(\s+[^\]]+?)?(\])',
             bygroups(Keyword, String, Keyword)),  # Link
            (r'^----+$', Keyword),  # Horizontal rules
            (r'[^\n\'\[{!_~^,|]+', Text),
            (r'\n', Text),
            (r'.', Text),
        ],
        'codeblock': [
            (r'\}\}\}', Name.Builtin, '#pop'),
            # these blocks are allowed to be nested in Trac, but not MoinMoin
            (r'\{\{\{', Text, '#push'),
            (r'[^{}]+', Comment.Preproc),  # slurp boring text
            (r'.', Comment.Preproc),  # allow loose { or }
        ],
    }


class RstLexer(RegexLexer):
    """
    For reStructuredText markup.

    Additional options accepted:

    `handlecodeblocks`
        Highlight the contents of ``.. sourcecode:: language``,
        ``.. code:: language`` and ``.. code-block:: language``
        directives with a lexer for the given language (default:
        ``True``).

        .. versionadded:: 0.8
    """
    name = 'reStructuredText'
    url = 'https://docutils.sourceforge.io/rst.html'
    aliases = ['restructuredtext', 'rst', 'rest']
    filenames = ['*.rst', '*.rest']
    mimetypes = ["text/x-rst", "text/prs.fallenstein.rst"]
    version_added = '0.7'
    flags = re.MULTILINE

    def _handle_sourcecode(self, match):
        from pygments.lexers import get_lexer_by_name

        # section header
        yield match.start(1), Punctuation, match.group(1)
        yield match.start(2), Text, match.group(2)
        yield match.start(3), Operator.Word, match.group(3)
        yield match.start(4), Punctuation, match.group(4)
        yield match.start(5), Text, match.group(5)
        yield match.start(6), Keyword, match.group(6)
        yield match.start(7), Text, match.group(7)

        # lookup lexer if wanted and existing
        lexer = None
        if self.handlecodeblocks:
            try:
                lexer = get_lexer_by_name(match.group(6).strip())
            except ClassNotFound:
                pass
        indention = match.group(8)
        indention_size = len(indention)
        code = (indention + match.group(9) + match.group(10) + match.group(11))

        # no lexer for this language. handle it like it was a code block
        if lexer is None:
            yield match.start(8), String, code
            return

        # highlight the lines with the lexer.
        ins = []
        codelines = code.splitlines(True)
        code = ''
        for line in codelines:
            if len(line) > indention_size:
                ins.append((len(code), [(0, Text, line[:indention_size])]))
                code += line[indention_size:]
            else:
                code += line
        yield from do_insertions(ins, lexer.get_tokens_unprocessed(code))

    # from docutils.parsers.rst.states
    closers = '\'")]}>\u2019\u201d\xbb!?'
    unicode_delimiters = '\u2010\u2011\u2012\u2013\u2014\u00a0'
    end_string_suffix = (rf'((?=$)|(?=[-/:.,; \n\x00{re.escape(unicode_delimiters)}{re.escape(closers)}]))')

    tokens = {
        'root': [
            # Heading with overline
            (r'^(=+|-+|`+|:+|\.+|\'+|"+|~+|\^+|_+|\*+|\++|#+)([ \t]*\n)'
             r'(.+)(\n)(\1)(\n)',
             bygroups(Generic.Heading, Text, Generic.Heading,
                      Text, Generic.Heading, Text)),
            # Plain heading
            (r'^(\S.*)(\n)(={3,}|-{3,}|`{3,}|:{3,}|\.{3,}|\'{3,}|"{3,}|'
             r'~{3,}|\^{3,}|_{3,}|\*{3,}|\+{3,}|#{3,})(\n)',
             bygroups(Generic.Heading, Text, Generic.Heading, Text)),
            # Bulleted lists
            (r'^(\s*)([-*+])( .+\n(?:\1  .+\n)*)',
             bygroups(Text, Number, using(this, state='inline'))),
            # Numbered lists
            (r'^(\s*)([0-9#ivxlcmIVXLCM]+\.)( .+\n(?:\1  .+\n)*)',
             bygroups(Text, Number, using(this, state='inline'))),
            (r'^(\s*)(\(?[0-9#ivxlcmIVXLCM]+\))( .+\n(?:\1  .+\n)*)',
             bygroups(Text, Number, using(this, state='inline'))),
            # Numbered, but keep words at BOL from becoming lists
            (r'^(\s*)([A-Z]+\.)( .+\n(?:\1  .+\n)+)',
             bygroups(Text, Number, using(this, state='inline'))),
            (r'^(\s*)(\(?[A-Za-z]+\))( .+\n(?:\1  .+\n)+)',
             bygroups(Text, Number, using(this, state='inline'))),
            # Line blocks
            (r'^(\s*)(\|)( .+\n(?:\|  .+\n)*)',
             bygroups(Text, Operator, using(this, state='inline'))),
            # Sourcecode directives
            (r'^( *\.\.)(\s*)((?:source)?code(?:-block)?)(::)([ \t]*)([^\n]+)'
             r'(\n[ \t]*\n)([ \t]+)(.*)(\n)((?:(?:\8.*)?\n)+)',
             _handle_sourcecode),
            # A directive
            (r'^( *\.\.)(\s*)([\w:-]+?)(::)(?:([ \t]*)(.*))',
             bygroups(Punctuation, Text, Operator.Word, Punctuation, Text,
                      using(this, state='inline'))),
            # A reference target
            (r'^( *\.\.)(\s*)(_(?:[^:\\]|\\.)+:)(.*?)$',
             bygroups(Punctuation, Text, Name.Tag, using(this, state='inline'))),
            # A footnote/citation target
            (r'^( *\.\.)(\s*)(\[.+\])(.*?)$',
             bygroups(Punctuation, Text, Name.Tag, using(this, state='inline'))),
            # A substitution def
            (r'^( *\.\.)(\s*)(\|.+\|)(\s*)([\w:-]+?)(::)(?:([ \t]*)(.*))',
             bygroups(Punctuation, Text, Name.Tag, Text, Operator.Word,
                      Punctuation, Text, using(this, state='inline'))),
            # Comments
            (r'^ *\.\..*(\n( +.*\n|\n)+)?', Comment),
            # Field list marker
            (r'^( *)(:(?:\\\\|\\:|[^:\n])+:(?=\s))([ \t]*)',
             bygroups(Text, Name.Class, Text)),
            # Definition list
            (r'^(\S.*(?<!::)\n)((?:(?: +.*)\n)+)',
             bygroups(using(this, state='inline'), using(this, state='inline'))),
            # Code blocks
            (r'(::)(\n[ \t]*\n)([ \t]+)(.*)(\n)((?:(?:\3.*)?\n)+)',
             bygroups(String.Escape, Text, String, String, Text, String)),
            include('inline'),
        ],
        'inline': [
            (r'\\.', Text),  # escape
            (r'``', String, 'literal'),  # code
            (r'(`.+?)(<.+?>)(`__?)',  # reference with inline target
             bygroups(String, String.Interpol, String)),
            (r'`.+?`__?', String),  # reference
            (r'(`.+?`)(:[a-zA-Z0-9:-]+?:)?',
             bygroups(Name.Variable, Name.Attribute)),  # role
            (r'(:[a-zA-Z0-9:-]+?:)(`.+?`)',
             bygroups(Name.Attribute, Name.Variable)),  # role (content first)
            (r'\*\*.+?\*\*', Generic.Strong),  # Strong emphasis
            (r'\*.+?\*', Generic.Emph),  # Emphasis
            (r'\[.*?\]_', String),  # Footnote or citation
            (r'<.+?>', Name.Tag),   # Hyperlink
            (r'[^\\\n\[*`:]+', Text),
            (r'.', Text),
        ],
        'literal': [
            (r'[^`]+', String),
            (r'``' + end_string_suffix, String, '#pop'),
            (r'`', String),
        ]
    }

    def __init__(self, **options):
        self.handlecodeblocks = get_bool_opt(options, 'handlecodeblocks', True)
        RegexLexer.__init__(self, **options)

    def analyse_text(text):
        if text[:2] == '..' and text[2:3] != '.':
            return 0.3
        p1 = text.find("\n")
        p2 = text.find("\n", p1 + 1)
        if (p2 > -1 and              # has two lines
                p1 * 2 + 1 == p2 and     # they are the same length
                text[p1+1] in '-=' and   # the next line both starts and ends with
                text[p1+1] == text[p2-1]):  # ...a sufficiently high header
            return 0.5


class TexLexer(RegexLexer):
    """
    Lexer for the TeX and LaTeX typesetting languages.
    """

    name = 'TeX'
    aliases = ['tex', 'latex']
    filenames = ['*.tex', '*.aux', '*.toc']
    mimetypes = ['text/x-tex', 'text/x-latex']
    url = 'https://tug.org'
    version_added = ''

    tokens = {
        'general': [
            (r'%.*?\n', Comment),
            (r'[{}]', Name.Builtin),
            (r'[&_^]', Name.Builtin),
        ],
        'root': [
            (r'\\\[', String.Backtick, 'displaymath'),
            (r'\\\(', String, 'inlinemath'),
            (r'\$\$', String.Backtick, 'displaymath'),
            (r'\$', String, 'inlinemath'),
            (r'\\([a-zA-Z@_:]+|\S?)', Keyword, 'command'),
            (r'\\$', Keyword),
            include('general'),
            (r'[^\\$%&_^{}]+', Text),
        ],
        'math': [
            (r'\\([a-zA-Z]+|\S?)', Name.Variable),
            include('general'),
            (r'[0-9]+', Number),
            (r'[-=!+*/()\[\]]', Operator),
            (r'[^=!+*/()\[\]\\$%&_^{}0-9-]+', Name.Builtin),
        ],
        'inlinemath': [
            (r'\\\)', String, '#pop'),
            (r'\$', String, '#pop'),
            include('math'),
        ],
        'displaymath': [
            (r'\\\]', String, '#pop'),
            (r'\$\$', String, '#pop'),
            (r'\$', Name.Builtin),
            include('math'),
        ],
        'command': [
            (r'\[.*?\]', Name.Attribute),
            (r'\*', Keyword),
            default('#pop'),
        ],
    }

    def analyse_text(text):
        for start in ("\\documentclass", "\\input", "\\documentstyle",
                      "\\relax"):
            if text[:len(start)] == start:
                return True


class GroffLexer(RegexLexer):
    """
    Lexer for the (g)roff typesetting language, supporting groff
    extensions. Mainly useful for highlighting manpage sources.
    """

    name = 'Groff'
    aliases = ['groff', 'nroff', 'man']
    filenames = ['*.[1-9]', '*.man', '*.1p', '*.3pm']
    mimetypes = ['application/x-troff', 'text/troff']
    url = 'https://www.gnu.org/software/groff'
    version_added = '0.6'

    tokens = {
        'root': [
            (r'(\.)(\w+)', bygroups(Text, Keyword), 'request'),
            (r'\.', Punctuation, 'request'),
            # Regular characters, slurp till we find a backslash or newline
            (r'[^\\\n]+', Text, 'textline'),
            default('textline'),
        ],
        'textline': [
            include('escapes'),
            (r'[^\\\n]+', Text),
            (r'\n', Text, '#pop'),
        ],
        'escapes': [
            # groff has many ways to write escapes.
            (r'\\"[^\n]*', Comment),
            (r'\\[fn]\w', String.Escape),
            (r'\\\(.{2}', String.Escape),
            (r'\\.\[.*\]', String.Escape),
            (r'\\.', String.Escape),
            (r'\\\n', Text, 'request'),
        ],
        'request': [
            (r'\n', Text, '#pop'),
            include('escapes'),
            (r'"[^\n"]+"', String.Double),
            (r'\d+', Number),
            (r'\S+', String),
            (r'\s+', Text),
        ],
    }

    def analyse_text(text):
        if text[:1] != '.':
            return False
        if text[:3] == '.\\"':
            return True
        if text[:4] == '.TH ':
            return True
        if text[1:3].isalnum() and text[3].isspace():
            return 0.9


class MozPreprocHashLexer(RegexLexer):
    """
    Lexer for Mozilla Preprocessor files (with '#' as the marker).

    Other data is left untouched.
    """
    name = 'mozhashpreproc'
    aliases = [name]
    filenames = []
    mimetypes = []
    url = 'https://firefox-source-docs.mozilla.org/build/buildsystem/preprocessor.html'
    version_added = '2.0'

    tokens = {
        'root': [
            (r'^#', Comment.Preproc, ('expr', 'exprstart')),
            (r'.+', Other),
        ],
        'exprstart': [
            (r'(literal)(.*)', bygroups(Comment.Preproc, Text), '#pop:2'),
            (words((
                'define', 'undef', 'if', 'ifdef', 'ifndef', 'else', 'elif',
                'elifdef', 'elifndef', 'endif', 'expand', 'filter', 'unfilter',
                'include', 'includesubst', 'error')),
             Comment.Preproc, '#pop'),
        ],
        'expr': [
            (words(('!', '!=', '==', '&&', '||')), Operator),
            (r'(defined)(\()', bygroups(Keyword, Punctuation)),
            (r'\)', Punctuation),
            (r'[0-9]+', Number.Decimal),
            (r'__\w+?__', Name.Variable),
            (r'@\w+?@', Name.Class),
            (r'\w+', Name),
            (r'\n', Text, '#pop'),
            (r'\s+', Text),
            (r'\S', Punctuation),
        ],
    }


class MozPreprocPercentLexer(MozPreprocHashLexer):
    """
    Lexer for Mozilla Preprocessor files (with '%' as the marker).

    Other data is left untouched.
    """
    name = 'mozpercentpreproc'
    aliases = [name]
    filenames = []
    mimetypes = []
    url = 'https://firefox-source-docs.mozilla.org/build/buildsystem/preprocessor.html'
    version_added = '2.0'

    tokens = {
        'root': [
            (r'^%', Comment.Preproc, ('expr', 'exprstart')),
            (r'.+', Other),
        ],
    }


class MozPreprocXulLexer(DelegatingLexer):
    """
    Subclass of the `MozPreprocHashLexer` that highlights unlexed data with the
    `XmlLexer`.
    """
    name = "XUL+mozpreproc"
    aliases = ['xul+mozpreproc']
    filenames = ['*.xul.in']
    mimetypes = []
    url = 'https://firefox-source-docs.mozilla.org/build/buildsystem/preprocessor.html'
    version_added = '2.0'

    def __init__(self, **options):
        super().__init__(XmlLexer, MozPreprocHashLexer, **options)


class MozPreprocJavascriptLexer(DelegatingLexer):
    """
    Subclass of the `MozPreprocHashLexer` that highlights unlexed data with the
    `JavascriptLexer`.
    """
    name = "Javascript+mozpreproc"
    aliases = ['javascript+mozpreproc']
    filenames = ['*.js.in']
    mimetypes = []
    url = 'https://firefox-source-docs.mozilla.org/build/buildsystem/preprocessor.html'
    version_added = '2.0'

    def __init__(self, **options):
        super().__init__(JavascriptLexer, MozPreprocHashLexer, **options)


class MozPreprocCssLexer(DelegatingLexer):
    """
    Subclass of the `MozPreprocHashLexer` that highlights unlexed data with the
    `CssLexer`.
    """
    name = "CSS+mozpreproc"
    aliases = ['css+mozpreproc']
    filenames = ['*.css.in']
    mimetypes = []
    url = 'https://firefox-source-docs.mozilla.org/build/buildsystem/preprocessor.html'
    version_added = '2.0'

    def __init__(self, **options):
        super().__init__(CssLexer, MozPreprocPercentLexer, **options)


class MarkdownLexer(RegexLexer):
    """
    For Markdown markup.
    """
    name = 'Markdown'
    url = 'https://daringfireball.net/projects/markdown/'
    aliases = ['markdown', 'md']
    filenames = ['*.md', '*.markdown']
    mimetypes = ["text/x-markdown"]
    version_added = '2.2'
    flags = re.MULTILINE

    def _handle_codeblock(self, match):
        from pygments.lexers import get_lexer_by_name

        yield match.start('initial'), String.Backtick, match.group('initial')
        yield match.start('lang'), String.Backtick, match.group('lang')
        if match.group('afterlang') is not None:
            yield match.start('whitespace'), Whitespace, match.group('whitespace')
            yield match.start('extra'), Text, match.group('extra')
        yield match.start('newline'), Whitespace, match.group('newline')

        # lookup lexer if wanted and existing
        lexer = None
        if self.handlecodeblocks:
            try:
                lexer = get_lexer_by_name(match.group('lang').strip())
            except ClassNotFound:
                pass
        code = match.group('code')
        # no lexer for this language. handle it like it was a code block
        if lexer is None:
            yield match.start('code'), String, code
        else:
            # FIXME: aren't the offsets wrong?
            yield from do_insertions([], lexer.get_tokens_unprocessed(code))

        yield match.start('terminator'), String.Backtick, match.group('terminator')

    tokens = {
        'root': [
            # heading with '#' prefix (atx-style)
            (r'(^#[^#].+)(\n)', bygroups(Generic.Heading, Text)),
            # subheading with '#' prefix (atx-style)
            (r'(^#{2,6}[^#].+)(\n)', bygroups(Generic.Subheading, Text)),
            # heading with '=' underlines (Setext-style)
            (r'^(.+)(\n)(=+)(\n)', bygroups(Generic.Heading, Text, Generic.Heading, Text)),
            # subheading with '-' underlines (Setext-style)
            (r'^(.+)(\n)(-+)(\n)', bygroups(Generic.Subheading, Text, Generic.Subheading, Text)),
            # task list
            (r'^(\s*)([*-] )(\[[ xX]\])( .+\n)',
            bygroups(Whitespace, Keyword, Keyword, using(this, state='inline'))),
            # bulleted list
            (r'^(\s*)([*-])(\s)(.+\n)',
            bygroups(Whitespace, Keyword, Whitespace, using(this, state='inline'))),
            # numbered list
            (r'^(\s*)([0-9]+\.)( .+\n)',
            bygroups(Whitespace, Keyword, using(this, state='inline'))),
            # quote
            (r'^(\s*>\s)(.+\n)', bygroups(Keyword, Generic.Emph)),
            # code block fenced by 3 backticks
            (r'^(\s*```\n[\w\W]*?^\s*```$\n)', String.Backtick),
            # code block with language
            # Some tools include extra stuff after the language name, just
            # highlight that as text. For example: https://docs.enola.dev/use/execmd
            (r'''(?x)
              ^(?P<initial>\s*```)
              (?P<lang>[\w\-]+)
              (?P<afterlang>
                 (?P<whitespace>[^\S\n]+)
                 (?P<extra>.*))?
              (?P<newline>\n)
              (?P<code>(.|\n)*?)
              (?P<terminator>^\s*```$\n)
              ''',
             _handle_codeblock),

            include('inline'),
        ],
        'inline': [
            # escape
            (r'\\.', Text),
            # inline code
            (r'([^`]?)(`[^`\n]+`)', bygroups(Text, String.Backtick)),
            # warning: the following rules eat outer tags.
            # eg. **foo _bar_ baz** => foo and baz are not recognized as bold
            # bold fenced by '**'
            (r'([^\*]?)(\*\*[^* \n][^*\n]*\*\*)', bygroups(Text, Generic.Strong)),
            # bold fenced by '__'
            (r'([^_]?)(__[^_ \n][^_\n]*__)', bygroups(Text, Generic.Strong)),
            # italics fenced by '*'
            (r'([^\*]?)(\*[^* \n][^*\n]*\*)', bygroups(Text, Generic.Emph)),
            # italics fenced by '_'
            (r'([^_]?)(_[^_ \n][^_\n]*_)', bygroups(Text, Generic.Emph)),
            # strikethrough
            (r'([^~]?)(~~[^~ \n][^~\n]*~~)', bygroups(Text, Generic.Deleted)),
            # mentions and topics (twitter and github stuff)
            (r'[@#][\w/:]+', Name.Entity),
            # (image?) links eg: ![Image of Yaktocat](https://octodex.github.com/images/yaktocat.png)
            (r'(!?\[)([^]]+)(\])(\()([^)]+)(\))',
             bygroups(Text, Name.Tag, Text, Text, Name.Attribute, Text)),
            # reference-style links, e.g.:
            #   [an example][id]
            #   [id]: http://example.com/
            (r'(\[)([^]]+)(\])(\[)([^]]*)(\])',
             bygroups(Text, Name.Tag, Text, Text, Name.Label, Text)),
            (r'^(\s*\[)([^]]*)(\]:\s*)(.+)',
             bygroups(Text, Name.Label, Text, Name.Attribute)),

            # general text, must come last!
            (r'[^\\\s]+', Text),
            (r'.', Text),
        ],
    }

    def __init__(self, **options):
        self.handlecodeblocks = get_bool_opt(options, 'handlecodeblocks', True)
        RegexLexer.__init__(self, **options)

class OrgLexer(RegexLexer):
    """
    For Org Mode markup.
    """
    name = 'Org Mode'
    url = 'https://orgmode.org'
    aliases = ['org', 'orgmode', 'org-mode']
    filenames = ['*.org']
    mimetypes = ["text/org"]
    version_added = '2.18'

    def _inline(start, end):
        return rf'(?<!\w){start}(.|\n(?!\n))+?{end}(?!\w)'

    tokens = {
        'root': [
            (r'^# .*', Comment.Single),

            # Headings
            (r'^(\* )(COMMENT)( .*)',
             bygroups(Generic.Heading, Comment.Preproc, Generic.Heading)),
            (r'^(\*\*+ )(COMMENT)( .*)',
             bygroups(Generic.Subheading, Comment.Preproc, Generic.Subheading)),
            (r'^(\* )(DONE)( .*)',
             bygroups(Generic.Heading, Generic.Deleted, Generic.Heading)),
            (r'^(\*\*+ )(DONE)( .*)',
             bygroups(Generic.Subheading, Generic.Deleted, Generic.Subheading)),
            (r'^(\* )(TODO)( .*)',
             bygroups(Generic.Heading, Generic.Error, Generic.Heading)),
            (r'^(\*\*+ )(TODO)( .*)',
             bygroups(Generic.Subheading, Generic.Error, Generic.Subheading)),

            (r'^(\* .+?)( :[a-zA-Z0-9_@:]+:)?$', bygroups(Generic.Heading, Generic.Emph)),
            (r'^(\*\*+ .+?)( :[a-zA-Z0-9_@:]+:)?$', bygroups(Generic.Subheading, Generic.Emph)),

            # Unordered lists items, including TODO items and description items
            (r'^(?:( *)([+-] )|( +)(\* ))(\[[ X-]\])?(.+ ::)?',
             bygroups(Whitespace, Keyword, Whitespace, Keyword, Generic.Prompt, Name.Label)),

            # Ordered list items
            (r'^( *)([0-9]+[.)])( \[@[0-9]+\])?', bygroups(Whitespace, Keyword, Generic.Emph)),

            # Dynamic blocks
            (r'(?i)^( *#\+begin: *)((?:.|\n)*?)(^ *#\+end: *$)',
             bygroups(Operator.Word, using(this), Operator.Word)),

            # Comment blocks
            (r'(?i)^( *#\+begin_comment *\n)((?:.|\n)*?)(^ *#\+end_comment *$)',
             bygroups(Operator.Word, Comment.Multiline, Operator.Word)),

            # Source code blocks
            # TODO: language-dependent syntax highlighting (see Markdown lexer)
            (r'(?i)^( *#\+begin_src .*)((?:.|\n)*?)(^ *#\+end_src *$)',
             bygroups(Operator.Word, Text, Operator.Word)),

            # Other blocks
            (r'(?i)^( *#\+begin_\w+)( *\n)((?:.|\n)*?)(^ *#\+end_\w+)( *$)',
             bygroups(Operator.Word, Whitespace, Text, Operator.Word, Whitespace)),

            # Keywords
            (r'^(#\+\w+:)(.*)$', bygroups(Name.Namespace, Text)),

            # Properties and drawers
            (r'(?i)^( *:\w+: *\n)((?:.|\n)*?)(^ *:end: *$)',
             bygroups(Name.Decorator, Comment.Special, Name.Decorator)),

            # Line break operator
            (r'\\\\$', Operator),

            # Deadline, Scheduled, CLOSED
            (r'(?i)^( *(?:DEADLINE|SCHEDULED): )(<.+?> *)$',
             bygroups(Generic.Error, Literal.Date)),
            (r'(?i)^( *CLOSED: )(\[.+?\] *)$',
             bygroups(Generic.Deleted, Literal.Date)),

            # Bold
            (_inline(r'\*', r'\*+'), Generic.Strong),
            # Italic
            (_inline(r'/', r'/'), Generic.Emph),
            # Verbatim
            (_inline(r'=', r'='), String), # TODO token
            # Code
            (_inline(r'~', r'~'), String),
            # Strikethrough
            (_inline(r'\+', r'\+'), Generic.Deleted),
            # Underline
            (_inline(r'_', r'_+'), Generic.EmphStrong),

            # Dates
            (r'<.+?>', Literal.Date),
            # Macros
            (r'\{\{\{.+?\}\}\}', Comment.Preproc),
            # Footnotes
            (r'(?<!\[)\[fn:.+?\]', Name.Tag),
            # Links
            (r'(?s)(\[\[)(.*?)(\]\[)(.*?)(\]\])',
             bygroups(Punctuation, Name.Attribute, Punctuation, Name.Tag, Punctuation)),
            (r'(?s)(\[\[)(.+?)(\]\])', bygroups(Punctuation, Name.Attribute, Punctuation)),
            (r'(<<)(.+?)(>>)', bygroups(Punctuation, Name.Attribute, Punctuation)),

            # Tables
            (r'^( *)(\|[ -].*?[ -]\|)$', bygroups(Whitespace, String)),

            # Any other text
            (r'[^#*+\-0-9:\\/=~_<{\[|\n]+', Text),
            (r'[#*+\-0-9:\\/=~_<{\[|\n]', Text),
        ],
    }

class TiddlyWiki5Lexer(RegexLexer):
    """
    For TiddlyWiki5 markup.
    """
    name = 'tiddler'
    url = 'https://tiddlywiki.com/#TiddlerFiles'
    aliases = ['tid']
    filenames = ['*.tid']
    mimetypes = ["text/vnd.tiddlywiki"]
    version_added = '2.7'
    flags = re.MULTILINE

    def _handle_codeblock(self, match):
        """
        match args: 1:backticks, 2:lang_name, 3:newline, 4:code, 5:backticks
        """
        from pygments.lexers import get_lexer_by_name

        # section header
        yield match.start(1), String, match.group(1)
        yield match.start(2), String, match.group(2)
        yield match.start(3), Text,   match.group(3)

        # lookup lexer if wanted and existing
        lexer = None
        if self.handlecodeblocks:
            try:
                lexer = get_lexer_by_name(match.group(2).strip())
            except ClassNotFound:
                pass
        code = match.group(4)

        # no lexer for this language. handle it like it was a code block
        if lexer is None:
            yield match.start(4), String, code
            return

        yield from do_insertions([], lexer.get_tokens_unprocessed(code))

        yield match.start(5), String, match.group(5)

    def _handle_cssblock(self, match):
        """
        match args: 1:style tag 2:newline, 3:code, 4:closing style tag
        """
        from pygments.lexers import get_lexer_by_name

        # section header
        yield match.start(1), String, match.group(1)
        yield match.start(2), String, match.group(2)

        lexer = None
        if self.handlecodeblocks:
            try:
                lexer = get_lexer_by_name('css')
            except ClassNotFound:
                pass
        code = match.group(3)

        # no lexer for this language. handle it like it was a code block
        if lexer is None:
            yield match.start(3), String, code
            return

        yield from do_insertions([], lexer.get_tokens_unprocessed(code))

        yield match.start(4), String, match.group(4)

    tokens = {
        'root': [
            # title in metadata section
            (r'^(title)(:\s)(.+\n)', bygroups(Keyword, Text, Generic.Heading)),
            # headings
            (r'^(!)([^!].+\n)', bygroups(Generic.Heading, Text)),
            (r'^(!{2,6})(.+\n)', bygroups(Generic.Subheading, Text)),
            # bulleted or numbered lists or single-line block quotes
            # (can be mixed)
            (r'^(\s*)([*#>]+)(\s*)(.+\n)',
             bygroups(Text, Keyword, Text, using(this, state='inline'))),
            # multi-line block quotes
            (r'^(<<<.*\n)([\w\W]*?)(^<<<.*$)', bygroups(String, Text, String)),
            # table header
            (r'^(\|.*?\|h)$', bygroups(Generic.Strong)),
            # table footer or caption
            (r'^(\|.*?\|[cf])$', bygroups(Generic.Emph)),
            # table class
            (r'^(\|.*?\|k)$', bygroups(Name.Tag)),
            # definitions
            (r'^(;.*)$', bygroups(Generic.Strong)),
            # text block
            (r'^(```\n)([\w\W]*?)(^```$)', bygroups(String, Text, String)),
            # code block with language
            (r'^(```)(\w+)(\n)([\w\W]*?)(^```$)', _handle_codeblock),
            # CSS style block
            (r'^(<style>)(\n)([\w\W]*?)(^</style>$)', _handle_cssblock),

            include('keywords'),
            include('inline'),
        ],
        'keywords': [
            (words((
                '\\define', '\\end', 'caption', 'created', 'modified', 'tags',
                'title', 'type'), prefix=r'^', suffix=r'\b'),
             Keyword),
        ],
        'inline': [
            # escape
            (r'\\.', Text),
            # created or modified date
            (r'\d{17}', Number.Integer),
            # italics
            (r'(\s)(//[^/]+//)((?=\W|\n))',
             bygroups(Text, Generic.Emph, Text)),
            # superscript
            (r'(\s)(\^\^[^\^]+\^\^)', bygroups(Text, Generic.Emph)),
            # subscript
            (r'(\s)(,,[^,]+,,)', bygroups(Text, Generic.Emph)),
            # underscore
            (r'(\s)(__[^_]+__)', bygroups(Text, Generic.Strong)),
            # bold
            (r"(\s)(''[^']+'')((?=\W|\n))",
             bygroups(Text, Generic.Strong, Text)),
            # strikethrough
            (r'(\s)(~~[^~]+~~)((?=\W|\n))',
             bygroups(Text, Generic.Deleted, Text)),
            # TiddlyWiki variables
            (r'<<[^>]+>>', Name.Tag),
            (r'\$\$[^$]+\$\$', Name.Tag),
            (r'\$\([^)]+\)\$', Name.Tag),
            # TiddlyWiki style or class
            (r'^@@.*$', Name.Tag),
            # HTML tags
            (r'</?[^>]+>', Name.Tag),
            # inline code
            (r'`[^`]+`', String.Backtick),
            # HTML escaped symbols
            (r'&\S*?;', String.Regex),
            # Wiki links
            (r'(\[{2})([^]\|]+)(\]{2})', bygroups(Text, Name.Tag, Text)),
            # External links
            (r'(\[{2})([^]\|]+)(\|)([^]\|]+)(\]{2})',
            bygroups(Text, Name.Tag, Text, Name.Attribute, Text)),
            # Transclusion
            (r'(\{{2})([^}]+)(\}{2})', bygroups(Text, Name.Tag, Text)),
            # URLs
            (r'(\b.?.?tps?://[^\s"]+)', bygroups(Name.Attribute)),

            # general text, must come last!
            (r'[\w]+', Text),
            (r'.', Text)
        ],
    }

    def __init__(self, **options):
        self.handlecodeblocks = get_bool_opt(options, 'handlecodeblocks', True)
        RegexLexer.__init__(self, **options)


class WikitextLexer(RegexLexer):
    """
    For MediaWiki Wikitext.

    Parsing Wikitext is tricky, and results vary between different MediaWiki
    installations, so we only highlight common syntaxes (built-in or from
    popular extensions), and also assume templates produce no unbalanced
    syntaxes.
    """
    name = 'Wikitext'
    url = 'https://www.mediawiki.org/wiki/Wikitext'
    aliases = ['wikitext', 'mediawiki']
    filenames = []
    mimetypes = ['text/x-wiki']
    version_added = '2.15'
    flags = re.MULTILINE

    def nowiki_tag_rules(tag_name):
        return [
            (rf'(?i)(</)({tag_name})(\s*)(>)', bygroups(Punctuation,
             Name.Tag, Whitespace, Punctuation), '#pop'),
            include('entity'),
            include('text'),
        ]

    def plaintext_tag_rules(tag_name):
        return [
            (rf'(?si)(.*?)(</)({tag_name})(\s*)(>)', bygroups(Text,
             Punctuation, Name.Tag, Whitespace, Punctuation), '#pop'),
        ]

    def delegate_tag_rules(tag_name, lexer, **lexer_kwargs):
        return [
            (rf'(?i)(</)({tag_name})(\s*)(>)', bygroups(Punctuation,
             Name.Tag, Whitespace, Punctuation), '#pop'),
            (rf'(?si).+?(?=</{tag_name}\s*>)', using(lexer, **lexer_kwargs)),
        ]

    def text_rules(token):
        return [
            (r'\w+', token),
            (r'[^\S\n]+', token),
            (r'(?s).', token),
        ]

    def handle_syntaxhighlight(self, match, ctx):
        from pygments.lexers import get_lexer_by_name

        attr_content = match.group()
        start = 0
        index = 0
        while True:
            index = attr_content.find('>', start)
            # Exclude comment end (-->)
            if attr_content[index-2:index] != '--':
                break
            start = index + 1

        if index == -1:
            # No tag end
            yield from self.get_tokens_unprocessed(attr_content, stack=['root', 'attr'])
            return
        attr = attr_content[:index]
        yield from self.get_tokens_unprocessed(attr, stack=['root', 'attr'])
        yield match.start(3) + index, Punctuation, '>'

        lexer = None
        content = attr_content[index+1:]
        lang_match = re.findall(r'\blang=("|\'|)(\w+)(\1)', attr)

        if len(lang_match) >= 1:
            # Pick the last match in case of multiple matches
            lang = lang_match[-1][1]
            try:
                lexer = get_lexer_by_name(lang)
            except ClassNotFound:
                pass

        if lexer is None:
            yield match.start() + index + 1, Text, content
        else:
            yield from lexer.get_tokens_unprocessed(content)

    def handle_score(self, match, ctx):
        attr_content = match.group()
        start = 0
        index = 0
        while True:
            index = attr_content.find('>', start)
            # Exclude comment end (-->)
            if attr_content[index-2:index] != '--':
                break
            start = index + 1

        if index == -1:
            # No tag end
            yield from self.get_tokens_unprocessed(attr_content, stack=['root', 'attr'])
            return
        attr = attr_content[:index]
        content = attr_content[index+1:]
        yield from self.get_tokens_unprocessed(attr, stack=['root', 'attr'])
        yield match.start(3) + index, Punctuation, '>'

        lang_match = re.findall(r'\blang=("|\'|)(\w+)(\1)', attr)
        # Pick the last match in case of multiple matches
        lang = lang_match[-1][1] if len(lang_match) >= 1 else 'lilypond'

        if lang == 'lilypond':  # Case sensitive
            yield from LilyPondLexer().get_tokens_unprocessed(content)
        else:  # ABC
            # FIXME: Use ABC lexer in the future
            yield match.start() + index + 1, Text, content

    # a-z removed to prevent linter from complaining, REMEMBER to use (?i)
    title_char = r' %!"$&\'()*,\-./0-9:;=?@A-Z\\\^_`~+\u0080-\uFFFF'
    nbsp_char = r'(?:\t|&nbsp;|&\#0*160;|&\#[Xx]0*[Aa]0;|[ \xA0\u1680\u2000-\u200A\u202F\u205F\u3000])'
    link_address = r'(?:[0-9.]+|\[[0-9a-f:.]+\]|[^\x00-\x20"<>\[\]\x7F\xA0\u1680\u2000-\u200A\u202F\u205F\u3000\uFFFD])'
    link_char_class = r'[^\x00-\x20"<>\[\]\x7F\xA0\u1680\u2000-\u200A\u202F\u205F\u3000\uFFFD]'
    double_slashes_i = {
        '__FORCETOC__', '__NOCONTENTCONVERT__', '__NOCC__', '__NOEDITSECTION__', '__NOGALLERY__',
        '__NOTITLECONVERT__', '__NOTC__', '__NOTOC__', '__TOC__',
    }
    double_slashes = {
        '__EXPECTUNUSEDCATEGORY__',  '__HIDDENCAT__', '__INDEX__',  '__NEWSECTIONLINK__',
        '__NOINDEX__',  '__NONEWSECTIONLINK__',  '__STATICREDIRECT__', '__NOGLOBAL__',
        '__DISAMBIG__', '__EXPECTED_UNCONNECTED_PAGE__',
    }
    protocols = {
        'bitcoin:', 'ftp://', 'ftps://', 'geo:', 'git://', 'gopher://', 'http://', 'https://',
        'irc://', 'ircs://', 'magnet:', 'mailto:', 'mms://', 'news:', 'nntp://', 'redis://',
        'sftp://', 'sip:', 'sips:', 'sms:', 'ssh://', 'svn://', 'tel:', 'telnet://', 'urn:',
        'worldwind://', 'xmpp:', '//',
    }
    non_relative_protocols = protocols - {'//'}
    html_tags = {
        'abbr', 'b', 'bdi', 'bdo', 'big', 'blockquote', 'br', 'caption', 'center', 'cite', 'code',
        'data', 'dd', 'del', 'dfn', 'div', 'dl', 'dt', 'em', 'font', 'h1', 'h2', 'h3', 'h4', 'h5',
        'h6', 'hr', 'i', 'ins', 'kbd', 'li', 'link', 'mark', 'meta', 'ol', 'p', 'q', 'rb', 'rp',
        'rt', 'rtc', 'ruby', 's', 'samp', 'small', 'span', 'strike', 'strong', 'sub', 'sup',
        'table', 'td', 'th', 'time', 'tr', 'tt', 'u', 'ul', 'var', 'wbr',
    }
    parser_tags = {
        'graph', 'charinsert', 'rss', 'chem', 'categorytree', 'nowiki', 'inputbox', 'math',
        'hiero', 'score', 'pre', 'ref', 'translate', 'imagemap', 'templatestyles', 'languages',
        'noinclude', 'mapframe', 'section', 'poem', 'syntaxhighlight', 'includeonly', 'tvar',
        'onlyinclude', 'templatedata', 'langconvert', 'timeline', 'dynamicpagelist', 'gallery',
        'maplink', 'ce', 'references',
    }
    variant_langs = {
        # ZhConverter.php
        'zh', 'zh-hans', 'zh-hant', 'zh-cn', 'zh-hk', 'zh-mo', 'zh-my', 'zh-sg', 'zh-tw',
        # WuuConverter.php
        'wuu', 'wuu-hans', 'wuu-hant',
        # UzConverter.php
        'uz', 'uz-latn', 'uz-cyrl',
        # TlyConverter.php
        'tly', 'tly-cyrl',
        # TgConverter.php
        'tg', 'tg-latn',
        # SrConverter.php
        'sr', 'sr-ec', 'sr-el',
        # ShiConverter.php
        'shi', 'shi-tfng', 'shi-latn',
        # ShConverter.php
        'sh-latn', 'sh-cyrl',
        # KuConverter.php
        'ku', 'ku-arab', 'ku-latn',
        # IuConverter.php
        'iu', 'ike-cans', 'ike-latn',
        # GanConverter.php
        'gan', 'gan-hans', 'gan-hant',
        # EnConverter.php
        'en', 'en-x-piglatin',
        # CrhConverter.php
        'crh', 'crh-cyrl', 'crh-latn',
        # BanConverter.php
        'ban', 'ban-bali', 'ban-x-dharma', 'ban-x-palmleaf', 'ban-x-pku',
    }
    magic_vars_i = {
        'ARTICLEPATH', 'INT', 'PAGEID', 'SCRIPTPATH', 'SERVER', 'SERVERNAME', 'STYLEPATH',
    }
    magic_vars = {
        '!', '=', 'BASEPAGENAME', 'BASEPAGENAMEE', 'CASCADINGSOURCES', 'CONTENTLANGUAGE',
        'CONTENTLANG', 'CURRENTDAY', 'CURRENTDAY2', 'CURRENTDAYNAME', 'CURRENTDOW', 'CURRENTHOUR',
        'CURRENTMONTH', 'CURRENTMONTH2', 'CURRENTMONTH1', 'CURRENTMONTHABBREV', 'CURRENTMONTHNAME',
        'CURRENTMONTHNAMEGEN', 'CURRENTTIME', 'CURRENTTIMESTAMP', 'CURRENTVERSION', 'CURRENTWEEK',
        'CURRENTYEAR', 'DIRECTIONMARK', 'DIRMARK', 'FULLPAGENAME', 'FULLPAGENAMEE', 'LOCALDAY',
        'LOCALDAY2', 'LOCALDAYNAME', 'LOCALDOW', 'LOCALHOUR', 'LOCALMONTH', 'LOCALMONTH2',
        'LOCALMONTH1', 'LOCALMONTHABBREV', 'LOCALMONTHNAME', 'LOCALMONTHNAMEGEN', 'LOCALTIME',
        'LOCALTIMESTAMP', 'LOCALWEEK', 'LOCALYEAR', 'NAMESPACE', 'NAMESPACEE', 'NAMESPACENUMBER',
        'NUMBEROFACTIVEUSERS', 'NUMBEROFADMINS', 'NUMBEROFARTICLES', 'NUMBEROFEDITS',
        'NUMBEROFFILES', 'NUMBEROFPAGES', 'NUMBEROFUSERS', 'PAGELANGUAGE', 'PAGENAME', 'PAGENAMEE',
        'REVISIONDAY', 'REVISIONDAY2', 'REVISIONID', 'REVISIONMONTH', 'REVISIONMONTH1',
        'REVISIONSIZE', 'REVISIONTIMESTAMP', 'REVISIONUSER', 'REVISIONYEAR', 'ROOTPAGENAME',
        'ROOTPAGENAMEE', 'SITENAME', 'SUBJECTPAGENAME', 'ARTICLEPAGENAME', 'SUBJECTPAGENAMEE',
        'ARTICLEPAGENAMEE', 'SUBJECTSPACE', 'ARTICLESPACE', 'SUBJECTSPACEE', 'ARTICLESPACEE',
        'SUBPAGENAME', 'SUBPAGENAMEE', 'TALKPAGENAME', 'TALKPAGENAMEE', 'TALKSPACE', 'TALKSPACEE',
    }
    parser_functions_i = {
        'ANCHORENCODE', 'BIDI', 'CANONICALURL', 'CANONICALURLE', 'FILEPATH', 'FORMATNUM',
        'FULLURL', 'FULLURLE', 'GENDER', 'GRAMMAR', 'INT', r'\#LANGUAGE', 'LC', 'LCFIRST', 'LOCALURL',
        'LOCALURLE', 'NS', 'NSE', 'PADLEFT', 'PADRIGHT', 'PAGEID', 'PLURAL', 'UC', 'UCFIRST',
        'URLENCODE',
    }
    parser_functions = {
        'BASEPAGENAME', 'BASEPAGENAMEE', 'CASCADINGSOURCES', 'DEFAULTSORT', 'DEFAULTSORTKEY',
        'DEFAULTCATEGORYSORT', 'FULLPAGENAME', 'FULLPAGENAMEE', 'NAMESPACE', 'NAMESPACEE',
        'NAMESPACENUMBER', 'NUMBERINGROUP', 'NUMINGROUP', 'NUMBEROFACTIVEUSERS', 'NUMBEROFADMINS',
        'NUMBEROFARTICLES', 'NUMBEROFEDITS', 'NUMBEROFFILES', 'NUMBEROFPAGES', 'NUMBEROFUSERS',
        'PAGENAME', 'PAGENAMEE', 'PAGESINCATEGORY', 'PAGESINCAT', 'PAGESIZE', 'PROTECTIONEXPIRY',
        'PROTECTIONLEVEL', 'REVISIONDAY', 'REVISIONDAY2', 'REVISIONID', 'REVISIONMONTH',
        'REVISIONMONTH1', 'REVISIONTIMESTAMP', 'REVISIONUSER', 'REVISIONYEAR', 'ROOTPAGENAME',
        'ROOTPAGENAMEE', 'SUBJECTPAGENAME', 'ARTICLEPAGENAME', 'SUBJECTPAGENAMEE',
        'ARTICLEPAGENAMEE', 'SUBJECTSPACE', 'ARTICLESPACE', 'SUBJECTSPACEE', 'ARTICLESPACEE',
        'SUBPAGENAME', 'SUBPAGENAMEE', 'TALKPAGENAME', 'TALKPAGENAMEE', 'TALKSPACE', 'TALKSPACEE',
        'INT', 'DISPLAYTITLE', 'PAGESINNAMESPACE', 'PAGESINNS',
    }

    tokens = {
        'root': [
            # Redirects
            (r"""(?xi)
                (\A\s*?)(\#REDIRECT:?) # may contain a colon
                (\s+)(\[\[) (?=[^\]\n]* \]\]$)
            """,
             bygroups(Whitespace, Keyword, Whitespace, Punctuation), 'redirect-inner'),
            # Subheadings
            (r'^(={2,6})(.+?)(\1)(\s*$\n)',
             bygroups(Generic.Subheading, Generic.Subheading, Generic.Subheading, Whitespace)),
            # Headings
            (r'^(=.+?=)(\s*$\n)',
             bygroups(Generic.Heading, Whitespace)),
            # Double-slashed magic words
            (words(double_slashes_i, prefix=r'(?i)'), Name.Function.Magic),
            (words(double_slashes), Name.Function.Magic),
            # Raw URLs
            (r'(?i)\b(?:{}){}{}*'.format('|'.join(protocols),
             link_address, link_char_class), Name.Label),
            # Magic links
            (rf'\b(?:RFC|PMID){nbsp_char}+[0-9]+\b',
             Name.Function.Magic),
            (r"""(?x)
                \bISBN {nbsp_char}
                (?: 97[89] {nbsp_dash}? )?
                (?: [0-9] {nbsp_dash}? ){{9}} # escape format()
                [0-9Xx]\b
            """.format(nbsp_char=nbsp_char, nbsp_dash=f'(?:-|{nbsp_char})'), Name.Function.Magic),
            include('list'),
            include('inline'),
            include('text'),
        ],
        'redirect-inner': [
            (r'(\]\])(\s*?\n)', bygroups(Punctuation, Whitespace), '#pop'),
            (r'(\#)([^#]*?)', bygroups(Punctuation, Name.Label)),
            (rf'(?i)[{title_char}]+', Name.Tag),
        ],
        'list': [
            # Description lists
            (r'^;', Keyword, 'dt'),
            # Ordered lists, unordered lists and indents
            (r'^[#:*]+', Keyword),
            # Horizontal rules
            (r'^-{4,}', Keyword),
        ],
        'inline': [
            # Signatures
            (r'~{3,5}', Keyword),
            # Entities
            include('entity'),
            # Bold & italic
            (r"('')(''')(?!')", bygroups(Generic.Emph,
             Generic.EmphStrong), 'inline-italic-bold'),
            (r"'''(?!')", Generic.Strong, 'inline-bold'),
            (r"''(?!')", Generic.Emph, 'inline-italic'),
            # Comments & parameters & templates
            include('replaceable'),
            # Media links
            (
                r"""(?xi)
                (\[\[)
                    (File|Image) (:)
                    ((?: [{}] | \{{{{2,3}}[^{{}}]*?\}}{{2,3}} | <!--[\s\S]*?--> )*)
                    (?: (\#) ([{}]*?) )?
                """.format(title_char, f'{title_char}#'),
                bygroups(Punctuation, Name.Namespace,  Punctuation,
                         using(this, state=['wikilink-name']), Punctuation, Name.Label),
                'medialink-inner'
            ),
            # Wikilinks
            (
                r"""(?xi)
                (\[\[)(?!{}) # Should not contain URLs
                    (?: ([{}]*) (:))?
                    ((?: [{}] | \{{{{2,3}}[^{{}}]*?\}}{{2,3}} | <!--[\s\S]*?--> )*?)
                    (?: (\#) ([{}]*?) )?
                (\]\])
                """.format('|'.join(protocols), title_char.replace('/', ''),
                       title_char, f'{title_char}#'),
                bygroups(Punctuation, Name.Namespace,  Punctuation,
                         using(this, state=['wikilink-name']), Punctuation, Name.Label, Punctuation)
            ),
            (
                r"""(?xi)
                (\[\[)(?!{})
                    (?: ([{}]*) (:))?
                    ((?: [{}] | \{{{{2,3}}[^{{}}]*?\}}{{2,3}} | <!--[\s\S]*?--> )*?)
                    (?: (\#) ([{}]*?) )?
                    (\|)
                """.format('|'.join(protocols), title_char.replace('/', ''),
                       title_char, f'{title_char}#'),
                bygroups(Punctuation, Name.Namespace,  Punctuation,
                         using(this, state=['wikilink-name']), Punctuation, Name.Label, Punctuation),
                'wikilink-inner'
            ),
            # External links
            (
                r"""(?xi)
                (\[)
                    ((?:{}) {} {}*)
                    (\s*)
                """.format('|'.join(protocols), link_address, link_char_class),
                bygroups(Punctuation, Name.Label, Whitespace),
                'extlink-inner'
            ),
            # Tables
            (r'^(:*)(\s*?)(\{\|)([^\n]*)$', bygroups(Keyword,
             Whitespace, Punctuation, using(this, state=['root', 'attr'])), 'table'),
            # HTML tags
            (r'(?i)(<)({})\b'.format('|'.join(html_tags)),
             bygroups(Punctuation, Name.Tag), 'tag-inner-ordinary'),
            (r'(?i)(</)({})\b(\s*)(>)'.format('|'.join(html_tags)),
             bygroups(Punctuation, Name.Tag, Whitespace, Punctuation)),
            # <nowiki>
            (r'(?i)(<)(nowiki)\b', bygroups(Punctuation,
             Name.Tag), ('tag-nowiki', 'tag-inner')),
            # <pre>
            (r'(?i)(<)(pre)\b', bygroups(Punctuation,
             Name.Tag), ('tag-pre', 'tag-inner')),
            # <categorytree>
            (r'(?i)(<)(categorytree)\b', bygroups(
                Punctuation, Name.Tag), ('tag-categorytree', 'tag-inner')),
            # <hiero>
            (r'(?i)(<)(hiero)\b', bygroups(Punctuation,
             Name.Tag), ('tag-hiero', 'tag-inner')),
            # <math>
            (r'(?i)(<)(math)\b', bygroups(Punctuation,
             Name.Tag), ('tag-math', 'tag-inner')),
            # <chem>
            (r'(?i)(<)(chem)\b', bygroups(Punctuation,
             Name.Tag), ('tag-chem', 'tag-inner')),
            # <ce>
            (r'(?i)(<)(ce)\b', bygroups(Punctuation,
             Name.Tag), ('tag-ce', 'tag-inner')),
            # <charinsert>
            (r'(?i)(<)(charinsert)\b', bygroups(
                Punctuation, Name.Tag), ('tag-charinsert', 'tag-inner')),
            # <templatedata>
            (r'(?i)(<)(templatedata)\b', bygroups(
                Punctuation, Name.Tag), ('tag-templatedata', 'tag-inner')),
            # <gallery>
            (r'(?i)(<)(gallery)\b', bygroups(
                Punctuation, Name.Tag), ('tag-gallery', 'tag-inner')),
            # <graph>
            (r'(?i)(<)(gallery)\b', bygroups(
                Punctuation, Name.Tag), ('tag-graph', 'tag-inner')),
            # <dynamicpagelist>
            (r'(?i)(<)(dynamicpagelist)\b', bygroups(
                Punctuation, Name.Tag), ('tag-dynamicpagelist', 'tag-inner')),
            # <inputbox>
            (r'(?i)(<)(inputbox)\b', bygroups(
                Punctuation, Name.Tag), ('tag-inputbox', 'tag-inner')),
            # <rss>
            (r'(?i)(<)(rss)\b', bygroups(
                Punctuation, Name.Tag), ('tag-rss', 'tag-inner')),
            # <imagemap>
            (r'(?i)(<)(imagemap)\b', bygroups(
                Punctuation, Name.Tag), ('tag-imagemap', 'tag-inner')),
            # <syntaxhighlight>
            (r'(?i)(</)(syntaxhighlight)\b(\s*)(>)',
             bygroups(Punctuation, Name.Tag, Whitespace, Punctuation)),
            (r'(?si)(<)(syntaxhighlight)\b([^>]*?(?<!/)>.*?)(?=</\2\s*>)',
             bygroups(Punctuation, Name.Tag, handle_syntaxhighlight)),
            # <syntaxhighlight>: Fallback case for self-closing tags
            (r'(?i)(<)(syntaxhighlight)\b(\s*?)((?:[^>]|-->)*?)(/\s*?(?<!--)>)', bygroups(
                Punctuation, Name.Tag, Whitespace, using(this, state=['root', 'attr']), Punctuation)),
            # <source>
            (r'(?i)(</)(source)\b(\s*)(>)',
             bygroups(Punctuation, Name.Tag, Whitespace, Punctuation)),
            (r'(?si)(<)(source)\b([^>]*?(?<!/)>.*?)(?=</\2\s*>)',
             bygroups(Punctuation, Name.Tag, handle_syntaxhighlight)),
            # <source>: Fallback case for self-closing tags
            (r'(?i)(<)(source)\b(\s*?)((?:[^>]|-->)*?)(/\s*?(?<!--)>)', bygroups(
                Punctuation, Name.Tag, Whitespace, using(this, state=['root', 'attr']), Punctuation)),
            # <score>
            (r'(?i)(</)(score)\b(\s*)(>)',
             bygroups(Punctuation, Name.Tag, Whitespace, Punctuation)),
            (r'(?si)(<)(score)\b([^>]*?(?<!/)>.*?)(?=</\2\s*>)',
             bygroups(Punctuation, Name.Tag, handle_score)),
            # <score>: Fallback case for self-closing tags
            (r'(?i)(<)(score)\b(\s*?)((?:[^>]|-->)*?)(/\s*?(?<!--)>)', bygroups(
                Punctuation, Name.Tag, Whitespace, using(this, state=['root', 'attr']), Punctuation)),
            # Other parser tags
            (r'(?i)(<)({})\b'.format('|'.join(parser_tags)),
             bygroups(Punctuation, Name.Tag), 'tag-inner-ordinary'),
            (r'(?i)(</)({})\b(\s*)(>)'.format('|'.join(parser_tags)),
             bygroups(Punctuation, Name.Tag, Whitespace, Punctuation)),
            # LanguageConverter markups
            (
                r"""(?xi)
                (-\{{) # Use {{ to escape format()
                    ([^|]) (\|)
                    (?:
                        (?: ([^;]*?) (=>))?
                        (\s* (?:{variants}) \s*) (:)
                    )?
                """.format(variants='|'.join(variant_langs)),
                bygroups(Punctuation, Keyword, Punctuation,
                         using(this, state=['root', 'lc-raw']),
                         Operator, Name.Label, Punctuation),
                'lc-inner'
            ),
            # LanguageConverter markups: composite conversion grammar
            (
                r"""(?xi)
                (-\{)
                    ([a-z\s;-]*?) (\|)
                """,
                bygroups(Punctuation,
                         using(this, state=['root', 'lc-flag']),
                         Punctuation),
                'lc-raw'
            ),
            # LanguageConverter markups: fallbacks
            (
                r"""(?xi)
                (-\{{) (?!\{{) # Use {{ to escape format()
                    (?: (\s* (?:{variants}) \s*) (:))?
                """.format(variants='|'.join(variant_langs)),
                bygroups(Punctuation, Name.Label, Punctuation),
                'lc-inner'
            ),
        ],
        'wikilink-name': [
            include('replaceable'),
            (r'[^{<]+', Name.Tag),
            (r'(?s).', Name.Tag),
        ],
        'wikilink-inner': [
            # Quit in case of another wikilink
            (r'(?=\[\[)', Punctuation, '#pop'),
            (r'\]\]', Punctuation, '#pop'),
            include('inline'),
            include('text'),
        ],
        'medialink-inner': [
            (r'\]\]', Punctuation, '#pop'),
            (r'(\|)([^\n=|]*)(=)',
             bygroups(Punctuation, Name.Attribute, Operator)),
            (r'\|', Punctuation),
            include('inline'),
            include('text'),
        ],
        'quote-common': [
            # Quit in case of link/template endings
            (r'(?=\]\]|\{\{|\}\})', Punctuation, '#pop'),
            (r'\n', Text, '#pop'),
        ],
        'inline-italic': [
            include('quote-common'),
            (r"('')(''')(?!')", bygroups(Generic.Emph,
             Generic.Strong), ('#pop', 'inline-bold')),
            (r"'''(?!')", Generic.EmphStrong, ('#pop', 'inline-italic-bold')),
            (r"''(?!')", Generic.Emph, '#pop'),
            include('inline'),
            include('text-italic'),
        ],
        'inline-bold': [
            include('quote-common'),
            (r"(''')('')(?!')", bygroups(
                Generic.Strong, Generic.Emph), ('#pop', 'inline-italic')),
            (r"'''(?!')", Generic.Strong, '#pop'),
            (r"''(?!')", Generic.EmphStrong, ('#pop', 'inline-bold-italic')),
            include('inline'),
            include('text-bold'),
        ],
        'inline-bold-italic': [
            include('quote-common'),
            (r"('')(''')(?!')", bygroups(Generic.EmphStrong,
             Generic.Strong), '#pop'),
            (r"'''(?!')", Generic.EmphStrong, ('#pop', 'inline-italic')),
            (r"''(?!')", Generic.EmphStrong, ('#pop', 'inline-bold')),
            include('inline'),
            include('text-bold-italic'),
        ],
        'inline-italic-bold': [
            include('quote-common'),
            (r"(''')('')(?!')", bygroups(
                Generic.EmphStrong, Generic.Emph), '#pop'),
            (r"'''(?!')", Generic.EmphStrong, ('#pop', 'inline-italic')),
            (r"''(?!')", Generic.EmphStrong, ('#pop', 'inline-bold')),
            include('inline'),
            include('text-bold-italic'),
        ],
        'lc-flag': [
            (r'\s+', Whitespace),
            (r';', Punctuation),
            *text_rules(Keyword),
        ],
        'lc-inner': [
            (
                r"""(?xi)
                (;)
                (?: ([^;]*?) (=>))?
                (\s* (?:{variants}) \s*) (:)
                """.format(variants='|'.join(variant_langs)),
                bygroups(Punctuation, using(this, state=['root', 'lc-raw']),
                         Operator, Name.Label, Punctuation)
            ),
            (r';?\s*?\}-', Punctuation, '#pop'),
            include('inline'),
            include('text'),
        ],
        'lc-raw': [
            (r'\}-', Punctuation, '#pop'),
            include('inline'),
            include('text'),
        ],
        'replaceable': [
            # Comments
            (r'<!--[\s\S]*?(?:-->|\Z)', Comment.Multiline),
            # Parameters
            (
                r"""(?x)
                (\{{3})
                    ([^|]*?)
                    (?=\}{3}|\|)
                """,
                bygroups(Punctuation, Name.Variable),
                'parameter-inner',
            ),
            # Magic variables
            (r'(?i)(\{{\{{)(\s*)({})(\s*)(\}}\}})'.format('|'.join(magic_vars_i)),
             bygroups(Punctuation, Whitespace, Name.Function, Whitespace, Punctuation)),
            (r'(\{{\{{)(\s*)({})(\s*)(\}}\}})'.format('|'.join(magic_vars)),
                bygroups(Punctuation, Whitespace, Name.Function, Whitespace, Punctuation)),
            # Parser functions & templates
            (r'\{\{', Punctuation, 'template-begin-space'),
            # <tvar> legacy syntax
            (r'(?i)(<)(tvar)\b(\|)([^>]*?)(>)', bygroups(Punctuation,
             Name.Tag, Punctuation, String, Punctuation)),
            (r'</>', Punctuation, '#pop'),
            # <tvar>
            (r'(?i)(<)(tvar)\b', bygroups(Punctuation, Name.Tag), 'tag-inner-ordinary'),
            (r'(?i)(</)(tvar)\b(\s*)(>)',
             bygroups(Punctuation, Name.Tag, Whitespace, Punctuation)),
        ],
        'parameter-inner': [
            (r'\}{3}', Punctuation, '#pop'),
            (r'\|', Punctuation),
            include('inline'),
            include('text'),
        ],
        'template-begin-space': [
            # Templates allow line breaks at the beginning, and due to how MediaWiki handles
            # comments, an extra state is required to handle things like {{\n<!---->\n name}}
            (r'<!--[\s\S]*?(?:-->|\Z)', Comment.Multiline),
            (r'\s+', Whitespace),
            # Parser functions
            (
                r'(?i)(\#[{}]*?|{})(:)'.format(title_char,
                                           '|'.join(parser_functions_i)),
                bygroups(Name.Function, Punctuation), ('#pop', 'template-inner')
            ),
            (
                r'({})(:)'.format('|'.join(parser_functions)),
                bygroups(Name.Function, Punctuation), ('#pop', 'template-inner')
            ),
            # Templates
            (
                rf'(?i)([{title_char}]*?)(:)',
                bygroups(Name.Namespace, Punctuation), ('#pop', 'template-name')
            ),
            default(('#pop', 'template-name'),),
        ],
        'template-name': [
            (r'(\s*?)(\|)', bygroups(Text, Punctuation), ('#pop', 'template-inner')),
            (r'\}\}', Punctuation, '#pop'),
            (r'\n', Text, '#pop'),
            include('replaceable'),
            *text_rules(Name.Tag),
        ],
        'template-inner': [
            (r'\}\}', Punctuation, '#pop'),
            (r'\|', Punctuation),
            (
                r"""(?x)
                    (?<=\|)
                    ( (?: (?! \{\{ | \}\} )[^=\|<])*? ) # Exclude templates and tags
                    (=)
                """,
                bygroups(Name.Label, Operator)
            ),
            include('inline'),
            include('text'),
        ],
        'table': [
            # Use [ \t\n\r\0\x0B] instead of \s to follow PHP trim() behavior
            # Endings
            (r'^([ \t\n\r\0\x0B]*?)(\|\})',
             bygroups(Whitespace, Punctuation), '#pop'),
            # Table rows
            (r'^([ \t\n\r\0\x0B]*?)(\|-+)(.*)$', bygroups(Whitespace, Punctuation,
             using(this, state=['root', 'attr']))),
            # Captions
            (
                r"""(?x)
                ^([ \t\n\r\0\x0B]*?)(\|\+)
                # Exclude links, template and tags
                (?: ( (?: (?! \[\[ | \{\{ )[^|\n<] )*? )(\|) )?
                (.*?)$
                """,
                bygroups(Whitespace, Punctuation, using(this, state=[
                         'root', 'attr']), Punctuation, Generic.Heading),
            ),
            # Table data
            (
                r"""(?x)
                ( ^(?:[ \t\n\r\0\x0B]*?)\| | \|\| )
                (?: ( (?: (?! \[\[ | \{\{ )[^|\n<] )*? )(\|)(?!\|) )?
                """,
                bygroups(Punctuation, using(this, state=[
                         'root', 'attr']), Punctuation),
            ),
            # Table headers
            (
                r"""(?x)
                ( ^(?:[ \t\n\r\0\x0B]*?)!  )
                (?: ( (?: (?! \[\[ | \{\{ )[^|\n<] )*? )(\|)(?!\|) )?
                """,
                bygroups(Punctuation, using(this, state=[
                         'root', 'attr']), Punctuation),
                'table-header',
            ),
            include('list'),
            include('inline'),
            include('text'),
        ],
        'table-header': [
            # Requires another state for || handling inside headers
            (r'\n', Text, '#pop'),
            (
                r"""(?x)
                (!!|\|\|)
                (?:
                    ( (?: (?! \[\[ | \{\{ )[^|\n<] )*? )
                    (\|)(?!\|)
                )?
                """,
                bygroups(Punctuation, using(this, state=[
                         'root', 'attr']), Punctuation)
            ),
            *text_rules(Generic.Subheading),
        ],
        'entity': [
            (r'&\S*?;', Name.Entity),
        ],
        'dt': [
            (r'\n', Text, '#pop'),
            include('inline'),
            (r':', Keyword, '#pop'),
            include('text'),
        ],
        'extlink-inner': [
            (r'\]', Punctuation, '#pop'),
            include('inline'),
            include('text'),
        ],
        'nowiki-ish': [
            include('entity'),
            include('text'),
        ],
        'attr': [
            include('replaceable'),
            (r'\s+', Whitespace),
            (r'(=)(\s*)(")', bygroups(Operator, Whitespace, String.Double), 'attr-val-2'),
            (r"(=)(\s*)(')", bygroups(Operator, Whitespace, String.Single), 'attr-val-1'),
            (r'(=)(\s*)', bygroups(Operator, Whitespace), 'attr-val-0'),
            (r'[\w:-]+', Name.Attribute),

        ],
        'attr-val-0': [
            (r'\s', Whitespace, '#pop'),
            include('replaceable'),
            *text_rules(String),
        ],
        'attr-val-1': [
            (r"'", String.Single, '#pop'),
            include('replaceable'),
            *text_rules(String.Single),
        ],
        'attr-val-2': [
            (r'"', String.Double, '#pop'),
            include('replaceable'),
            *text_rules(String.Double),
        ],
        'tag-inner-ordinary': [
            (r'/?\s*>', Punctuation, '#pop'),
            include('tag-attr'),
        ],
        'tag-inner': [
            # Return to root state for self-closing tags
            (r'/\s*>', Punctuation, '#pop:2'),
            (r'\s*>', Punctuation, '#pop'),
            include('tag-attr'),
        ],
        # There states below are just like their non-tag variants, the key difference is
        # they forcibly quit when encountering tag closing markup
        'tag-attr': [
            include('replaceable'),
            (r'\s+', Whitespace),
            (r'(=)(\s*)(")', bygroups(Operator,
             Whitespace, String.Double), 'tag-attr-val-2'),
            (r"(=)(\s*)(')", bygroups(Operator,
             Whitespace, String.Single), 'tag-attr-val-1'),
            (r'(=)(\s*)', bygroups(Operator, Whitespace), 'tag-attr-val-0'),
            (r'[\w:-]+', Name.Attribute),

        ],
        'tag-attr-val-0': [
            (r'\s', Whitespace, '#pop'),
            (r'/?>', Punctuation, '#pop:2'),
            include('replaceable'),
            *text_rules(String),
        ],
        'tag-attr-val-1': [
            (r"'", String.Single, '#pop'),
            (r'/?>', Punctuation, '#pop:2'),
            include('replaceable'),
            *text_rules(String.Single),
        ],
        'tag-attr-val-2': [
            (r'"', String.Double, '#pop'),
            (r'/?>', Punctuation, '#pop:2'),
            include('replaceable'),
            *text_rules(String.Double),
        ],
        'tag-nowiki': nowiki_tag_rules('nowiki'),
        'tag-pre': nowiki_tag_rules('pre'),
        'tag-categorytree': plaintext_tag_rules('categorytree'),
        'tag-dynamicpagelist': plaintext_tag_rules('dynamicpagelist'),
        'tag-hiero': plaintext_tag_rules('hiero'),
        'tag-inputbox': plaintext_tag_rules('inputbox'),
        'tag-imagemap': plaintext_tag_rules('imagemap'),
        'tag-charinsert': plaintext_tag_rules('charinsert'),
        'tag-timeline': plaintext_tag_rules('timeline'),
        'tag-gallery': plaintext_tag_rules('gallery'),
        'tag-graph': plaintext_tag_rules('graph'),
        'tag-rss': plaintext_tag_rules('rss'),
        'tag-math': delegate_tag_rules('math', TexLexer, state='math'),
        'tag-chem': delegate_tag_rules('chem', TexLexer, state='math'),
        'tag-ce': delegate_tag_rules('ce', TexLexer, state='math'),
        'tag-templatedata': delegate_tag_rules('templatedata', JsonLexer),
        'text-italic': text_rules(Generic.Emph),
        'text-bold': text_rules(Generic.Strong),
        'text-bold-italic': text_rules(Generic.EmphStrong),
        'text': text_rules(Text),
    }

# === NexusCore/openenv\Lib\site-packages\matplotlib\font_manager.py ===
"""
A module for finding, managing, and using fonts across platforms.

This module provides a single `FontManager` instance, ``fontManager``, that can
be shared across backends and platforms.  The `findfont`
function returns the best TrueType (TTF) font file in the local or
system font path that matches the specified `FontProperties`
instance.  The `FontManager` also handles Adobe Font Metrics
(AFM) font files for use by the PostScript backend.
The `FontManager.addfont` function adds a custom font from a file without
installing it into your operating system.

The design is based on the `W3C Cascading Style Sheet, Level 1 (CSS1)
font specification <http://www.w3.org/TR/1998/REC-CSS2-19980512/>`_.
Future versions may implement the Level 2 or 2.1 specifications.
"""

# KNOWN ISSUES
#
#   - documentation
#   - font variant is untested
#   - font stretch is incomplete
#   - font size is incomplete
#   - default font algorithm needs improvement and testing
#   - setWeights function needs improvement
#   - 'light' is an invalid weight value, remove it.

from __future__ import annotations

from base64 import b64encode
import copy
import dataclasses
from functools import lru_cache
import functools
from io import BytesIO
import json
import logging
from numbers import Number
import os
from pathlib import Path
import plistlib
import re
import subprocess
import sys
import threading

import matplotlib as mpl
from matplotlib import _api, _afm, cbook, ft2font
from matplotlib._fontconfig_pattern import (
    parse_fontconfig_pattern, generate_fontconfig_pattern)
from matplotlib.rcsetup import _validators

_log = logging.getLogger(__name__)

font_scalings = {
    'xx-small': 0.579,
    'x-small':  0.694,
    'small':    0.833,
    'medium':   1.0,
    'large':    1.200,
    'x-large':  1.440,
    'xx-large': 1.728,
    'larger':   1.2,
    'smaller':  0.833,
    None:       1.0,
}
stretch_dict = {
    'ultra-condensed': 100,
    'extra-condensed': 200,
    'condensed':       300,
    'semi-condensed':  400,
    'normal':          500,
    'semi-expanded':   600,
    'semi-extended':   600,
    'expanded':        700,
    'extended':        700,
    'extra-expanded':  800,
    'extra-extended':  800,
    'ultra-expanded':  900,
    'ultra-extended':  900,
}
weight_dict = {
    'ultralight': 100,
    'light':      200,
    'normal':     400,
    'regular':    400,
    'book':       400,
    'medium':     500,
    'roman':      500,
    'semibold':   600,
    'demibold':   600,
    'demi':       600,
    'bold':       700,
    'heavy':      800,
    'extra bold': 800,
    'black':      900,
}
_weight_regexes = [
    # From fontconfig's FcFreeTypeQueryFaceInternal; not the same as
    # weight_dict!
    ("thin", 100),
    ("extralight", 200),
    ("ultralight", 200),
    ("demilight", 350),
    ("semilight", 350),
    ("light", 300),  # Needs to come *after* demi/semilight!
    ("book", 380),
    ("regular", 400),
    ("normal", 400),
    ("medium", 500),
    ("demibold", 600),
    ("demi", 600),
    ("semibold", 600),
    ("extrabold", 800),
    ("superbold", 800),
    ("ultrabold", 800),
    ("bold", 700),  # Needs to come *after* extra/super/ultrabold!
    ("ultrablack", 1000),
    ("superblack", 1000),
    ("extrablack", 1000),
    (r"\bultra", 1000),
    ("black", 900),  # Needs to come *after* ultra/super/extrablack!
    ("heavy", 900),
]
font_family_aliases = {
    'serif',
    'sans-serif',
    'sans serif',
    'cursive',
    'fantasy',
    'monospace',
    'sans',
}

# OS Font paths
try:
    _HOME = Path.home()
except Exception:  # Exceptions thrown by home() are not specified...
    _HOME = Path(os.devnull)  # Just an arbitrary path with no children.
MSFolders = \
    r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
MSFontDirectories = [
    r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts',
    r'SOFTWARE\Microsoft\Windows\CurrentVersion\Fonts']
MSUserFontDirectories = [
    str(_HOME / 'AppData/Local/Microsoft/Windows/Fonts'),
    str(_HOME / 'AppData/Roaming/Microsoft/Windows/Fonts'),
]
X11FontDirectories = [
    # an old standard installation point
    "/usr/X11R6/lib/X11/fonts/TTF/",
    "/usr/X11/lib/X11/fonts",
    # here is the new standard location for fonts
    "/usr/share/fonts/",
    # documented as a good place to install new fonts
    "/usr/local/share/fonts/",
    # common application, not really useful
    "/usr/lib/openoffice/share/fonts/truetype/",
    # user fonts
    str((Path(os.environ.get('XDG_DATA_HOME') or _HOME / ".local/share"))
        / "fonts"),
    str(_HOME / ".fonts"),
]
OSXFontDirectories = [
    "/Library/Fonts/",
    "/Network/Library/Fonts/",
    "/System/Library/Fonts/",
    # fonts installed via MacPorts
    "/opt/local/share/fonts",
    # user fonts
    str(_HOME / "Library/Fonts"),
]


def get_fontext_synonyms(fontext):
    """
    Return a list of file extensions that are synonyms for
    the given file extension *fileext*.
    """
    return {
        'afm': ['afm'],
        'otf': ['otf', 'ttc', 'ttf'],
        'ttc': ['otf', 'ttc', 'ttf'],
        'ttf': ['otf', 'ttc', 'ttf'],
    }[fontext]


def list_fonts(directory, extensions):
    """
    Return a list of all fonts matching any of the extensions, found
    recursively under the directory.
    """
    extensions = ["." + ext for ext in extensions]
    return [os.path.join(dirpath, filename)
            # os.walk ignores access errors, unlike Path.glob.
            for dirpath, _, filenames in os.walk(directory)
            for filename in filenames
            if Path(filename).suffix.lower() in extensions]


def win32FontDirectory():
    r"""
    Return the user-specified font directory for Win32.  This is
    looked up from the registry key ::

      \\HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders\Fonts

    If the key is not found, ``%WINDIR%\Fonts`` will be returned.
    """  # noqa: E501
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, MSFolders) as user:
            return winreg.QueryValueEx(user, 'Fonts')[0]
    except OSError:
        return os.path.join(os.environ['WINDIR'], 'Fonts')


def _get_win32_installed_fonts():
    """List the font paths known to the Windows registry."""
    import winreg
    items = set()
    # Search and resolve fonts listed in the registry.
    for domain, base_dirs in [
            (winreg.HKEY_LOCAL_MACHINE, [win32FontDirectory()]),  # System.
            (winreg.HKEY_CURRENT_USER, MSUserFontDirectories),  # User.
    ]:
        for base_dir in base_dirs:
            for reg_path in MSFontDirectories:
                try:
                    with winreg.OpenKey(domain, reg_path) as local:
                        for j in range(winreg.QueryInfoKey(local)[1]):
                            # value may contain the filename of the font or its
                            # absolute path.
                            key, value, tp = winreg.EnumValue(local, j)
                            if not isinstance(value, str):
                                continue
                            try:
                                # If value contains already an absolute path,
                                # then it is not changed further.
                                path = Path(base_dir, value).resolve()
                            except RuntimeError:
                                # Don't fail with invalid entries.
                                continue
                            items.add(path)
                except (OSError, MemoryError):
                    continue
    return items


@lru_cache
def _get_fontconfig_fonts():
    """Cache and list the font paths known to ``fc-list``."""
    try:
        if b'--format' not in subprocess.check_output(['fc-list', '--help']):
            _log.warning(  # fontconfig 2.7 implemented --format.
                'Matplotlib needs fontconfig>=2.7 to query system fonts.')
            return []
        out = subprocess.check_output(['fc-list', '--format=%{file}\\n'])
    except (OSError, subprocess.CalledProcessError):
        return []
    return [Path(os.fsdecode(fname)) for fname in out.split(b'\n')]


@lru_cache
def _get_macos_fonts():
    """Cache and list the font paths known to ``system_profiler SPFontsDataType``."""
    try:
        d, = plistlib.loads(
            subprocess.check_output(["system_profiler", "-xml", "SPFontsDataType"]))
    except (OSError, subprocess.CalledProcessError, plistlib.InvalidFileException):
        return []
    return [Path(entry["path"]) for entry in d["_items"]]


def findSystemFonts(fontpaths=None, fontext='ttf'):
    """
    Search for fonts in the specified font paths.  If no paths are
    given, will use a standard set of system paths, as well as the
    list of fonts tracked by fontconfig if fontconfig is installed and
    available.  A list of TrueType fonts are returned by default with
    AFM fonts as an option.
    """
    fontfiles = set()
    fontexts = get_fontext_synonyms(fontext)

    if fontpaths is None:
        if sys.platform == 'win32':
            installed_fonts = _get_win32_installed_fonts()
            fontpaths = []
        else:
            installed_fonts = _get_fontconfig_fonts()
            if sys.platform == 'darwin':
                installed_fonts += _get_macos_fonts()
                fontpaths = [*X11FontDirectories, *OSXFontDirectories]
            else:
                fontpaths = X11FontDirectories
        fontfiles.update(str(path) for path in installed_fonts
                         if path.suffix.lower()[1:] in fontexts)

    elif isinstance(fontpaths, str):
        fontpaths = [fontpaths]

    for path in fontpaths:
        fontfiles.update(map(os.path.abspath, list_fonts(path, fontexts)))

    return [fname for fname in fontfiles if os.path.exists(fname)]


@dataclasses.dataclass(frozen=True)
class FontEntry:
    """
    A class for storing Font properties.

    It is used when populating the font lookup dictionary.
    """

    fname: str = ''
    name: str = ''
    style: str = 'normal'
    variant: str = 'normal'
    weight: str | int = 'normal'
    stretch: str = 'normal'
    size: str = 'medium'

    def _repr_html_(self) -> str:
        png_stream = self._repr_png_()
        png_b64 = b64encode(png_stream).decode()
        return f"<img src=\"data:image/png;base64, {png_b64}\" />"

    def _repr_png_(self) -> bytes:
        from matplotlib.figure import Figure  # Circular import.
        fig = Figure()
        font_path = Path(self.fname) if self.fname != '' else None
        fig.text(0, 0, self.name, font=font_path)
        with BytesIO() as buf:
            fig.savefig(buf, bbox_inches='tight', transparent=True)
            return buf.getvalue()


def ttfFontProperty(font):
    """
    Extract information from a TrueType font file.

    Parameters
    ----------
    font : `.FT2Font`
        The TrueType font file from which information will be extracted.

    Returns
    -------
    `FontEntry`
        The extracted font properties.

    """
    name = font.family_name

    #  Styles are: italic, oblique, and normal (default)

    sfnt = font.get_sfnt()
    mac_key = (1,  # platform: macintosh
               0,  # id: roman
               0)  # langid: english
    ms_key = (3,  # platform: microsoft
              1,  # id: unicode_cs
              0x0409)  # langid: english_united_states

    # These tables are actually mac_roman-encoded, but mac_roman support may be
    # missing in some alternative Python implementations and we are only going
    # to look for ASCII substrings, where any ASCII-compatible encoding works
    # - or big-endian UTF-16, since important Microsoft fonts use that.
    sfnt2 = (sfnt.get((*mac_key, 2), b'').decode('latin-1').lower() or
             sfnt.get((*ms_key, 2), b'').decode('utf_16_be').lower())
    sfnt4 = (sfnt.get((*mac_key, 4), b'').decode('latin-1').lower() or
             sfnt.get((*ms_key, 4), b'').decode('utf_16_be').lower())

    if sfnt4.find('oblique') >= 0:
        style = 'oblique'
    elif sfnt4.find('italic') >= 0:
        style = 'italic'
    elif sfnt2.find('regular') >= 0:
        style = 'normal'
    elif ft2font.StyleFlags.ITALIC in font.style_flags:
        style = 'italic'
    else:
        style = 'normal'

    #  Variants are: small-caps and normal (default)

    #  !!!!  Untested
    if name.lower() in ['capitals', 'small-caps']:
        variant = 'small-caps'
    else:
        variant = 'normal'

    # The weight-guessing algorithm is directly translated from fontconfig
    # 2.13.1's FcFreeTypeQueryFaceInternal (fcfreetype.c).
    wws_subfamily = 22
    typographic_subfamily = 16
    font_subfamily = 2
    styles = [
        sfnt.get((*mac_key, wws_subfamily), b'').decode('latin-1'),
        sfnt.get((*mac_key, typographic_subfamily), b'').decode('latin-1'),
        sfnt.get((*mac_key, font_subfamily), b'').decode('latin-1'),
        sfnt.get((*ms_key, wws_subfamily), b'').decode('utf-16-be'),
        sfnt.get((*ms_key, typographic_subfamily), b'').decode('utf-16-be'),
        sfnt.get((*ms_key, font_subfamily), b'').decode('utf-16-be'),
    ]
    styles = [*filter(None, styles)] or [font.style_name]

    def get_weight():  # From fontconfig's FcFreeTypeQueryFaceInternal.
        # OS/2 table weight.
        os2 = font.get_sfnt_table("OS/2")
        if os2 and os2["version"] != 0xffff:
            return os2["usWeightClass"]
        # PostScript font info weight.
        try:
            ps_font_info_weight = (
                font.get_ps_font_info()["weight"].replace(" ", "") or "")
        except ValueError:
            pass
        else:
            for regex, weight in _weight_regexes:
                if re.fullmatch(regex, ps_font_info_weight, re.I):
                    return weight
        # Style name weight.
        for style in styles:
            style = style.replace(" ", "")
            for regex, weight in _weight_regexes:
                if re.search(regex, style, re.I):
                    return weight
        if ft2font.StyleFlags.BOLD in font.style_flags:
            return 700  # "bold"
        return 500  # "medium", not "regular"!

    weight = int(get_weight())

    #  Stretch can be absolute and relative
    #  Absolute stretches are: ultra-condensed, extra-condensed, condensed,
    #    semi-condensed, normal, semi-expanded, expanded, extra-expanded,
    #    and ultra-expanded.
    #  Relative stretches are: wider, narrower
    #  Child value is: inherit

    if any(word in sfnt4 for word in ['narrow', 'condensed', 'cond']):
        stretch = 'condensed'
    elif 'demi cond' in sfnt4:
        stretch = 'semi-condensed'
    elif any(word in sfnt4 for word in ['wide', 'expanded', 'extended']):
        stretch = 'expanded'
    else:
        stretch = 'normal'

    #  Sizes can be absolute and relative.
    #  Absolute sizes are: xx-small, x-small, small, medium, large, x-large,
    #    and xx-large.
    #  Relative sizes are: larger, smaller
    #  Length value is an absolute font size, e.g., 12pt
    #  Percentage values are in 'em's.  Most robust specification.

    if not font.scalable:
        raise NotImplementedError("Non-scalable fonts are not supported")
    size = 'scalable'

    return FontEntry(font.fname, name, style, variant, weight, stretch, size)


def afmFontProperty(fontpath, font):
    """
    Extract information from an AFM font file.

    Parameters
    ----------
    fontpath : str
        The filename corresponding to *font*.
    font : AFM
        The AFM font file from which information will be extracted.

    Returns
    -------
    `FontEntry`
        The extracted font properties.
    """

    name = font.get_familyname()
    fontname = font.get_fontname().lower()

    #  Styles are: italic, oblique, and normal (default)

    if font.get_angle() != 0 or 'italic' in name.lower():
        style = 'italic'
    elif 'oblique' in name.lower():
        style = 'oblique'
    else:
        style = 'normal'

    #  Variants are: small-caps and normal (default)

    # !!!!  Untested
    if name.lower() in ['capitals', 'small-caps']:
        variant = 'small-caps'
    else:
        variant = 'normal'

    weight = font.get_weight().lower()
    if weight not in weight_dict:
        weight = 'normal'

    #  Stretch can be absolute and relative
    #  Absolute stretches are: ultra-condensed, extra-condensed, condensed,
    #    semi-condensed, normal, semi-expanded, expanded, extra-expanded,
    #    and ultra-expanded.
    #  Relative stretches are: wider, narrower
    #  Child value is: inherit
    if 'demi cond' in fontname:
        stretch = 'semi-condensed'
    elif any(word in fontname for word in ['narrow', 'cond']):
        stretch = 'condensed'
    elif any(word in fontname for word in ['wide', 'expanded', 'extended']):
        stretch = 'expanded'
    else:
        stretch = 'normal'

    #  Sizes can be absolute and relative.
    #  Absolute sizes are: xx-small, x-small, small, medium, large, x-large,
    #    and xx-large.
    #  Relative sizes are: larger, smaller
    #  Length value is an absolute font size, e.g., 12pt
    #  Percentage values are in 'em's.  Most robust specification.

    #  All AFM fonts are apparently scalable.

    size = 'scalable'

    return FontEntry(fontpath, name, style, variant, weight, stretch, size)


def _cleanup_fontproperties_init(init_method):
    """
    A decorator to limit the call signature to single a positional argument
    or alternatively only keyword arguments.

    We still accept but deprecate all other call signatures.

    When the deprecation expires we can switch the signature to::

        __init__(self, pattern=None, /, *, family=None, style=None, ...)

    plus a runtime check that pattern is not used alongside with the
    keyword arguments. This results eventually in the two possible
    call signatures::

        FontProperties(pattern)
        FontProperties(family=..., size=..., ...)

    """
    @functools.wraps(init_method)
    def wrapper(self, *args, **kwargs):
        # multiple args with at least some positional ones
        if len(args) > 1 or len(args) == 1 and kwargs:
            # Note: Both cases were previously handled as individual properties.
            # Therefore, we do not mention the case of font properties here.
            _api.warn_deprecated(
                "3.10",
                message="Passing individual properties to FontProperties() "
                        "positionally was deprecated in Matplotlib %(since)s and "
                        "will be removed in %(removal)s. Please pass all properties "
                        "via keyword arguments."
            )
        # single non-string arg -> clearly a family not a pattern
        if len(args) == 1 and not kwargs and not cbook.is_scalar_or_string(args[0]):
            # Case font-family list passed as single argument
            _api.warn_deprecated(
                "3.10",
                message="Passing family as positional argument to FontProperties() "
                        "was deprecated in Matplotlib %(since)s and will be removed "
                        "in %(removal)s. Please pass family names as keyword"
                        "argument."
            )
        # Note on single string arg:
        # This has been interpreted as pattern so far. We are already raising if a
        # non-pattern compatible family string was given. Therefore, we do not need
        # to warn for this case.
        return init_method(self, *args, **kwargs)

    return wrapper


class FontProperties:
    """
    A class for storing and manipulating font properties.

    The font properties are the six properties described in the
    `W3C Cascading Style Sheet, Level 1
    <http://www.w3.org/TR/1998/REC-CSS2-19980512/>`_ font
    specification and *math_fontfamily* for math fonts:

    - family: A list of font names in decreasing order of priority.
      The items may include a generic font family name, either 'sans-serif',
      'serif', 'cursive', 'fantasy', or 'monospace'.  In that case, the actual
      font to be used will be looked up from the associated rcParam during the
      search process in `.findfont`. Default: :rc:`font.family`

    - style: Either 'normal', 'italic' or 'oblique'.
      Default: :rc:`font.style`

    - variant: Either 'normal' or 'small-caps'.
      Default: :rc:`font.variant`

    - stretch: A numeric value in the range 0-1000 or one of
      'ultra-condensed', 'extra-condensed', 'condensed',
      'semi-condensed', 'normal', 'semi-expanded', 'expanded',
      'extra-expanded' or 'ultra-expanded'. Default: :rc:`font.stretch`

    - weight: A numeric value in the range 0-1000 or one of
      'ultralight', 'light', 'normal', 'regular', 'book', 'medium',
      'roman', 'semibold', 'demibold', 'demi', 'bold', 'heavy',
      'extra bold', 'black'. Default: :rc:`font.weight`

    - size: Either a relative value of 'xx-small', 'x-small',
      'small', 'medium', 'large', 'x-large', 'xx-large' or an
      absolute font size, e.g., 10. Default: :rc:`font.size`

    - math_fontfamily: The family of fonts used to render math text.
      Supported values are: 'dejavusans', 'dejavuserif', 'cm',
      'stix', 'stixsans' and 'custom'. Default: :rc:`mathtext.fontset`

    Alternatively, a font may be specified using the absolute path to a font
    file, by using the *fname* kwarg.  However, in this case, it is typically
    simpler to just pass the path (as a `pathlib.Path`, not a `str`) to the
    *font* kwarg of the `.Text` object.

    The preferred usage of font sizes is to use the relative values,
    e.g.,  'large', instead of absolute font sizes, e.g., 12.  This
    approach allows all text sizes to be made larger or smaller based
    on the font manager's default font size.

    This class accepts a single positional string as fontconfig_ pattern_,
    or alternatively individual properties as keyword arguments::

        FontProperties(pattern)
        FontProperties(*, family=None, style=None, variant=None, ...)

    This support does not depend on fontconfig; we are merely borrowing its
    pattern syntax for use here.

    .. _fontconfig: https://www.freedesktop.org/wiki/Software/fontconfig/
    .. _pattern:
       https://www.freedesktop.org/software/fontconfig/fontconfig-user.html

    Note that Matplotlib's internal font manager and fontconfig use a
    different algorithm to lookup fonts, so the results of the same pattern
    may be different in Matplotlib than in other applications that use
    fontconfig.
    """

    @_cleanup_fontproperties_init
    def __init__(self, family=None, style=None, variant=None, weight=None,
                 stretch=None, size=None,
                 fname=None,  # if set, it's a hardcoded filename to use
                 math_fontfamily=None):
        self.set_family(family)
        self.set_style(style)
        self.set_variant(variant)
        self.set_weight(weight)
        self.set_stretch(stretch)
        self.set_file(fname)
        self.set_size(size)
        self.set_math_fontfamily(math_fontfamily)
        # Treat family as a fontconfig pattern if it is the only parameter
        # provided.  Even in that case, call the other setters first to set
        # attributes not specified by the pattern to the rcParams defaults.
        if (isinstance(family, str)
                and style is None and variant is None and weight is None
                and stretch is None and size is None and fname is None):
            self.set_fontconfig_pattern(family)

    @classmethod
    def _from_any(cls, arg):
        """
        Generic constructor which can build a `.FontProperties` from any of the
        following:

        - a `.FontProperties`: it is passed through as is;
        - `None`: a `.FontProperties` using rc values is used;
        - an `os.PathLike`: it is used as path to the font file;
        - a `str`: it is parsed as a fontconfig pattern;
        - a `dict`: it is passed as ``**kwargs`` to `.FontProperties`.
        """
        if arg is None:
            return cls()
        elif isinstance(arg, cls):
            return arg
        elif isinstance(arg, os.PathLike):
            return cls(fname=arg)
        elif isinstance(arg, str):
            return cls(arg)
        else:
            return cls(**arg)

    def __hash__(self):
        l = (tuple(self.get_family()),
             self.get_slant(),
             self.get_variant(),
             self.get_weight(),
             self.get_stretch(),
             self.get_size(),
             self.get_file(),
             self.get_math_fontfamily())
        return hash(l)

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __str__(self):
        return self.get_fontconfig_pattern()

    def get_family(self):
        """
        Return a list of individual font family names or generic family names.

        The font families or generic font families (which will be resolved
        from their respective rcParams when searching for a matching font) in
        the order of preference.
        """
        return self._family

    def get_name(self):
        """
        Return the name of the font that best matches the font properties.
        """
        return get_font(findfont(self)).family_name

    def get_style(self):
        """
        Return the font style.  Values are: 'normal', 'italic' or 'oblique'.
        """
        return self._slant

    def get_variant(self):
        """
        Return the font variant.  Values are: 'normal' or 'small-caps'.
        """
        return self._variant

    def get_weight(self):
        """
        Set the font weight.  Options are: A numeric value in the
        range 0-1000 or one of 'light', 'normal', 'regular', 'book',
        'medium', 'roman', 'semibold', 'demibold', 'demi', 'bold',
        'heavy', 'extra bold', 'black'
        """
        return self._weight

    def get_stretch(self):
        """
        Return the font stretch or width.  Options are: 'ultra-condensed',
        'extra-condensed', 'condensed', 'semi-condensed', 'normal',
        'semi-expanded', 'expanded', 'extra-expanded', 'ultra-expanded'.
        """
        return self._stretch

    def get_size(self):
        """
        Return the font size.
        """
        return self._size

    def get_file(self):
        """
        Return the filename of the associated font.
        """
        return self._file

    def get_fontconfig_pattern(self):
        """
        Get a fontconfig_ pattern_ suitable for looking up the font as
        specified with fontconfig's ``fc-match`` utility.

        This support does not depend on fontconfig; we are merely borrowing its
        pattern syntax for use here.
        """
        return generate_fontconfig_pattern(self)

    def set_family(self, family):
        """
        Change the font family.  Can be either an alias (generic name
        is CSS parlance), such as: 'serif', 'sans-serif', 'cursive',
        'fantasy', or 'monospace', a real font name or a list of real
        font names.  Real font names are not supported when
        :rc:`text.usetex` is `True`. Default: :rc:`font.family`
        """
        if family is None:
            family = mpl.rcParams['font.family']
        if isinstance(family, str):
            family = [family]
        self._family = family

    def set_style(self, style):
        """
        Set the font style.

        Parameters
        ----------
        style : {'normal', 'italic', 'oblique'}, default: :rc:`font.style`
        """
        if style is None:
            style = mpl.rcParams['font.style']
        _api.check_in_list(['normal', 'italic', 'oblique'], style=style)
        self._slant = style

    def set_variant(self, variant):
        """
        Set the font variant.

        Parameters
        ----------
        variant : {'normal', 'small-caps'}, default: :rc:`font.variant`
        """
        if variant is None:
            variant = mpl.rcParams['font.variant']
        _api.check_in_list(['normal', 'small-caps'], variant=variant)
        self._variant = variant

    def set_weight(self, weight):
        """
        Set the font weight.

        Parameters
        ----------
        weight : int or {'ultralight', 'light', 'normal', 'regular', 'book', \
'medium', 'roman', 'semibold', 'demibold', 'demi', 'bold', 'heavy', \
'extra bold', 'black'}, default: :rc:`font.weight`
            If int, must be in the range  0-1000.
        """
        if weight is None:
            weight = mpl.rcParams['font.weight']
        if weight in weight_dict:
            self._weight = weight
            return
        try:
            weight = int(weight)
        except ValueError:
            pass
        else:
            if 0 <= weight <= 1000:
                self._weight = weight
                return
        raise ValueError(f"{weight=} is invalid")

    def set_stretch(self, stretch):
        """
        Set the font stretch or width.

        Parameters
        ----------
        stretch : int or {'ultra-condensed', 'extra-condensed', 'condensed', \
'semi-condensed', 'normal', 'semi-expanded', 'expanded', 'extra-expanded', \
'ultra-expanded'}, default: :rc:`font.stretch`
            If int, must be in the range  0-1000.
        """
        if stretch is None:
            stretch = mpl.rcParams['font.stretch']
        if stretch in stretch_dict:
            self._stretch = stretch
            return
        try:
            stretch = int(stretch)
        except ValueError:
            pass
        else:
            if 0 <= stretch <= 1000:
                self._stretch = stretch
                return
        raise ValueError(f"{stretch=} is invalid")

    def set_size(self, size):
        """
        Set the font size.

        Parameters
        ----------
        size : float or {'xx-small', 'x-small', 'small', 'medium', \
'large', 'x-large', 'xx-large'}, default: :rc:`font.size`
            If a float, the font size in points. The string values denote
            sizes relative to the default font size.
        """
        if size is None:
            size = mpl.rcParams['font.size']
        try:
            size = float(size)
        except ValueError:
            try:
                scale = font_scalings[size]
            except KeyError as err:
                raise ValueError(
                    "Size is invalid. Valid font size are "
                    + ", ".join(map(str, font_scalings))) from err
            else:
                size = scale * FontManager.get_default_size()
        if size < 1.0:
            _log.info('Fontsize %1.2f < 1.0 pt not allowed by FreeType. '
                      'Setting fontsize = 1 pt', size)
            size = 1.0
        self._size = size

    def set_file(self, file):
        """
        Set the filename of the fontfile to use.  In this case, all
        other properties will be ignored.
        """
        self._file = os.fspath(file) if file is not None else None

    def set_fontconfig_pattern(self, pattern):
        """
        Set the properties by parsing a fontconfig_ *pattern*.

        This support does not depend on fontconfig; we are merely borrowing its
        pattern syntax for use here.
        """
        for key, val in parse_fontconfig_pattern(pattern).items():
            if type(val) is list:
                getattr(self, "set_" + key)(val[0])
            else:
                getattr(self, "set_" + key)(val)

    def get_math_fontfamily(self):
        """
        Return the name of the font family used for math text.

        The default font is :rc:`mathtext.fontset`.
        """
        return self._math_fontfamily

    def set_math_fontfamily(self, fontfamily):
        """
        Set the font family for text in math mode.

        If not set explicitly, :rc:`mathtext.fontset` will be used.

        Parameters
        ----------
        fontfamily : str
            The name of the font family.

            Available font families are defined in the
            :ref:`default matplotlibrc file <customizing-with-matplotlibrc-files>`.

        See Also
        --------
        .text.Text.get_math_fontfamily
        """
        if fontfamily is None:
            fontfamily = mpl.rcParams['mathtext.fontset']
        else:
            valid_fonts = _validators['mathtext.fontset'].valid.values()
            # _check_in_list() Validates the parameter math_fontfamily as
            # if it were passed to rcParams['mathtext.fontset']
            _api.check_in_list(valid_fonts, math_fontfamily=fontfamily)
        self._math_fontfamily = fontfamily

    def copy(self):
        """Return a copy of self."""
        return copy.copy(self)

    # Aliases
    set_name = set_family
    get_slant = get_style
    set_slant = set_style
    get_size_in_points = get_size


class _JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, FontManager):
            return dict(o.__dict__, __class__='FontManager')
        elif isinstance(o, FontEntry):
            d = dict(o.__dict__, __class__='FontEntry')
            try:
                # Cache paths of fonts shipped with Matplotlib relative to the
                # Matplotlib data path, which helps in the presence of venvs.
                d["fname"] = str(Path(d["fname"]).relative_to(mpl.get_data_path()))
            except ValueError:
                pass
            return d
        else:
            return super().default(o)


def _json_decode(o):
    cls = o.pop('__class__', None)
    if cls is None:
        return o
    elif cls == 'FontManager':
        r = FontManager.__new__(FontManager)
        r.__dict__.update(o)
        return r
    elif cls == 'FontEntry':
        if not os.path.isabs(o['fname']):
            o['fname'] = os.path.join(mpl.get_data_path(), o['fname'])
        r = FontEntry(**o)
        return r
    else:
        raise ValueError("Don't know how to deserialize __class__=%s" % cls)


def json_dump(data, filename):
    """
    Dump `FontManager` *data* as JSON to the file named *filename*.

    See Also
    --------
    json_load

    Notes
    -----
    File paths that are children of the Matplotlib data path (typically, fonts
    shipped with Matplotlib) are stored relative to that data path (to remain
    valid across virtualenvs).

    This function temporarily locks the output file to prevent multiple
    processes from overwriting one another's output.
    """
    try:
        with cbook._lock_path(filename), open(filename, 'w') as fh:
            json.dump(data, fh, cls=_JSONEncoder, indent=2)
    except OSError as e:
        _log.warning('Could not save font_manager cache %s', e)


def json_load(filename):
    """
    Load a `FontManager` from the JSON file named *filename*.

    See Also
    --------
    json_dump
    """
    with open(filename) as fh:
        return json.load(fh, object_hook=_json_decode)


class FontManager:
    """
    On import, the `FontManager` singleton instance creates a list of ttf and
    afm fonts and caches their `FontProperties`.  The `FontManager.findfont`
    method does a nearest neighbor search to find the font that most closely
    matches the specification.  If no good enough match is found, the default
    font is returned.

    Fonts added with the `FontManager.addfont` method will not persist in the
    cache; therefore, `addfont` will need to be called every time Matplotlib is
    imported. This method should only be used if and when a font cannot be
    installed on your operating system by other means.

    Notes
    -----
    The `FontManager.addfont` method must be called on the global `FontManager`
    instance.

    Example usage::

        import matplotlib.pyplot as plt
        from matplotlib import font_manager

        font_dirs = ["/resources/fonts"]  # The path to the custom font file.
        font_files = font_manager.findSystemFonts(fontpaths=font_dirs)

        for font_file in font_files:
            font_manager.fontManager.addfont(font_file)
    """
    # Increment this version number whenever the font cache data
    # format or behavior has changed and requires an existing font
    # cache files to be rebuilt.
    __version__ = 390

    def __init__(self, size=None, weight='normal'):
        self._version = self.__version__

        self.__default_weight = weight
        self.default_size = size

        # Create list of font paths.
        paths = [cbook._get_data_path('fonts', subdir)
                 for subdir in ['ttf', 'afm', 'pdfcorefonts']]
        _log.debug('font search path %s', paths)

        self.defaultFamily = {
            'ttf': 'DejaVu Sans',
            'afm': 'Helvetica'}

        self.afmlist = []
        self.ttflist = []

        # Delay the warning by 5s.
        timer = threading.Timer(5, lambda: _log.warning(
            'Matplotlib is building the font cache; this may take a moment.'))
        timer.start()
        try:
            for fontext in ["afm", "ttf"]:
                for path in [*findSystemFonts(paths, fontext=fontext),
                             *findSystemFonts(fontext=fontext)]:
                    try:
                        self.addfont(path)
                    except OSError as exc:
                        _log.info("Failed to open font file %s: %s", path, exc)
                    except Exception as exc:
                        _log.info("Failed to extract font properties from %s: "
                                  "%s", path, exc)
        finally:
            timer.cancel()

    def addfont(self, path):
        """
        Cache the properties of the font at *path* to make it available to the
        `FontManager`.  The type of font is inferred from the path suffix.

        Parameters
        ----------
        path : str or path-like

        Notes
        -----
        This method is useful for adding a custom font without installing it in
        your operating system. See the `FontManager` singleton instance for
        usage and caveats about this function.
        """
        # Convert to string in case of a path as
        # afmFontProperty and FT2Font expect this
        path = os.fsdecode(path)
        if Path(path).suffix.lower() == ".afm":
            with open(path, "rb") as fh:
                font = _afm.AFM(fh)
            prop = afmFontProperty(path, font)
            self.afmlist.append(prop)
        else:
            font = ft2font.FT2Font(path)
            prop = ttfFontProperty(font)
            self.ttflist.append(prop)
        self._findfont_cached.cache_clear()

    @property
    def defaultFont(self):
        # Lazily evaluated (findfont then caches the result) to avoid including
        # the venv path in the json serialization.
        return {ext: self.findfont(family, fontext=ext)
                for ext, family in self.defaultFamily.items()}

    def get_default_weight(self):
        """
        Return the default font weight.
        """
        return self.__default_weight

    @staticmethod
    def get_default_size():
        """
        Return the default font size.
        """
        return mpl.rcParams['font.size']

    def set_default_weight(self, weight):
        """
        Set the default font weight.  The initial value is 'normal'.
        """
        self.__default_weight = weight

    @staticmethod
    def _expand_aliases(family):
        if family in ('sans', 'sans serif'):
            family = 'sans-serif'
        return mpl.rcParams['font.' + family]

    # Each of the scoring functions below should return a value between
    # 0.0 (perfect match) and 1.0 (terrible match)
    def score_family(self, families, family2):
        """
        Return a match score between the list of font families in
        *families* and the font family name *family2*.

        An exact match at the head of the list returns 0.0.

        A match further down the list will return between 0 and 1.

        No match will return 1.0.
        """
        if not isinstance(families, (list, tuple)):
            families = [families]
        elif len(families) == 0:
            return 1.0
        family2 = family2.lower()
        step = 1 / len(families)
        for i, family1 in enumerate(families):
            family1 = family1.lower()
            if family1 in font_family_aliases:
                options = [*map(str.lower, self._expand_aliases(family1))]
                if family2 in options:
                    idx = options.index(family2)
                    return (i + (idx / len(options))) * step
            elif family1 == family2:
                # The score should be weighted by where in the
                # list the font was found.
                return i * step
        return 1.0

    def score_style(self, style1, style2):
        """
        Return a match score between *style1* and *style2*.

        An exact match returns 0.0.

        A match between 'italic' and 'oblique' returns 0.1.

        No match returns 1.0.
        """
        if style1 == style2:
            return 0.0
        elif (style1 in ('italic', 'oblique')
              and style2 in ('italic', 'oblique')):
            return 0.1
        return 1.0

    def score_variant(self, variant1, variant2):
        """
        Return a match score between *variant1* and *variant2*.

        An exact match returns 0.0, otherwise 1.0.
        """
        if variant1 == variant2:
            return 0.0
        else:
            return 1.0

    def score_stretch(self, stretch1, stretch2):
        """
        Return a match score between *stretch1* and *stretch2*.

        The result is the absolute value of the difference between the
        CSS numeric values of *stretch1* and *stretch2*, normalized
        between 0.0 and 1.0.
        """
        try:
            stretchval1 = int(stretch1)
        except ValueError:
            stretchval1 = stretch_dict.get(stretch1, 500)
        try:
            stretchval2 = int(stretch2)
        except ValueError:
            stretchval2 = stretch_dict.get(stretch2, 500)
        return abs(stretchval1 - stretchval2) / 1000.0

    def score_weight(self, weight1, weight2):
        """
        Return a match score between *weight1* and *weight2*.

        The result is 0.0 if both weight1 and weight 2 are given as strings
        and have the same value.

        Otherwise, the result is the absolute value of the difference between
        the CSS numeric values of *weight1* and *weight2*, normalized between
        0.05 and 1.0.
        """
        # exact match of the weight names, e.g. weight1 == weight2 == "regular"
        if cbook._str_equal(weight1, weight2):
            return 0.0
        w1 = weight1 if isinstance(weight1, Number) else weight_dict[weight1]
        w2 = weight2 if isinstance(weight2, Number) else weight_dict[weight2]
        return 0.95 * (abs(w1 - w2) / 1000) + 0.05

    def score_size(self, size1, size2):
        """
        Return a match score between *size1* and *size2*.

        If *size2* (the size specified in the font file) is 'scalable', this
        function always returns 0.0, since any font size can be generated.

        Otherwise, the result is the absolute distance between *size1* and
        *size2*, normalized so that the usual range of font sizes (6pt -
        72pt) will lie between 0.0 and 1.0.
        """
        if size2 == 'scalable':
            return 0.0
        # Size value should have already been
        try:
            sizeval1 = float(size1)
        except ValueError:
            sizeval1 = self.default_size * font_scalings[size1]
        try:
            sizeval2 = float(size2)
        except ValueError:
            return 1.0
        return abs(sizeval1 - sizeval2) / 72

    def findfont(self, prop, fontext='ttf', directory=None,
                 fallback_to_default=True, rebuild_if_missing=True):
        """
        Find the path to the font file most closely matching the given font properties.

        Parameters
        ----------
        prop : str or `~matplotlib.font_manager.FontProperties`
            The font properties to search for. This can be either a
            `.FontProperties` object or a string defining a
            `fontconfig patterns`_.

        fontext : {'ttf', 'afm'}, default: 'ttf'
            The extension of the font file:

            - 'ttf': TrueType and OpenType fonts (.ttf, .ttc, .otf)
            - 'afm': Adobe Font Metrics (.afm)

        directory : str, optional
            If given, only search this directory and its subdirectories.

        fallback_to_default : bool
            If True, will fall back to the default font family (usually
            "DejaVu Sans" or "Helvetica") if the first lookup hard-fails.

        rebuild_if_missing : bool
            Whether to rebuild the font cache and search again if the first
            match appears to point to a nonexisting font (i.e., the font cache
            contains outdated entries).

        Returns
        -------
        str
            The filename of the best matching font.

        Notes
        -----
        This performs a nearest neighbor search.  Each font is given a
        similarity score to the target font properties.  The first font with
        the highest score is returned.  If no matches below a certain
        threshold are found, the default font (usually DejaVu Sans) is
        returned.

        The result is cached, so subsequent lookups don't have to
        perform the O(n) nearest neighbor search.

        See the `W3C Cascading Style Sheet, Level 1
        <http://www.w3.org/TR/1998/REC-CSS2-19980512/>`_ documentation
        for a description of the font finding algorithm.

        .. _fontconfig patterns:
           https://www.freedesktop.org/software/fontconfig/fontconfig-user.html
        """
        # Pass the relevant rcParams (and the font manager, as `self`) to
        # _findfont_cached so to prevent using a stale cache entry after an
        # rcParam was changed.
        rc_params = tuple(tuple(mpl.rcParams[key]) for key in [
            "font.serif", "font.sans-serif", "font.cursive", "font.fantasy",
            "font.monospace"])
        ret = self._findfont_cached(
            prop, fontext, directory, fallback_to_default, rebuild_if_missing,
            rc_params)
        if isinstance(ret, cbook._ExceptionInfo):
            raise ret.to_exception()
        return ret

    def get_font_names(self):
        """Return the list of available fonts."""
        return list({font.name for font in self.ttflist})

    def _find_fonts_by_props(self, prop, fontext='ttf', directory=None,
                             fallback_to_default=True, rebuild_if_missing=True):
        """
        Find the paths to the font files most closely matching the given properties.

        Parameters
        ----------
        prop : str or `~matplotlib.font_manager.FontProperties`
            The font properties to search for. This can be either a
            `.FontProperties` object or a string defining a
            `fontconfig patterns`_.

        fontext : {'ttf', 'afm'}, default: 'ttf'
            The extension of the font file:

            - 'ttf': TrueType and OpenType fonts (.ttf, .ttc, .otf)
            - 'afm': Adobe Font Metrics (.afm)

        directory : str, optional
            If given, only search this directory and its subdirectories.

        fallback_to_default : bool
            If True, will fall back to the default font family (usually
            "DejaVu Sans" or "Helvetica") if none of the families were found.

        rebuild_if_missing : bool
            Whether to rebuild the font cache and search again if the first
            match appears to point to a nonexisting font (i.e., the font cache
            contains outdated entries).

        Returns
        -------
        list[str]
            The paths of the fonts found.

        Notes
        -----
        This is an extension/wrapper of the original findfont API, which only
        returns a single font for given font properties. Instead, this API
        returns a list of filepaths of multiple fonts which closely match the
        given font properties.  Since this internally uses the original API,
        there's no change to the logic of performing the nearest neighbor
        search.  See `findfont` for more details.
        """

        prop = FontProperties._from_any(prop)

        fpaths = []
        for family in prop.get_family():
            cprop = prop.copy()
            cprop.set_family(family)  # set current prop's family

            try:
                fpaths.append(
                    self.findfont(
                        cprop, fontext, directory,
                        fallback_to_default=False,  # don't fallback to default
                        rebuild_if_missing=rebuild_if_missing,
                    )
                )
            except ValueError:
                if family in font_family_aliases:
                    _log.warning(
                        "findfont: Generic family %r not found because "
                        "none of the following families were found: %s",
                        family, ", ".join(self._expand_aliases(family))
                    )
                else:
                    _log.warning("findfont: Font family %r not found.", family)

        # only add default family if no other font was found and
        # fallback_to_default is enabled
        if not fpaths:
            if fallback_to_default:
                dfamily = self.defaultFamily[fontext]
                cprop = prop.copy()
                cprop.set_family(dfamily)
                fpaths.append(
                    self.findfont(
                        cprop, fontext, directory,
                        fallback_to_default=True,
                        rebuild_if_missing=rebuild_if_missing,
                    )
                )
            else:
                raise ValueError("Failed to find any font, and fallback "
                                 "to the default font was disabled")

        return fpaths

    @lru_cache(1024)
    def _findfont_cached(self, prop, fontext, directory, fallback_to_default,
                         rebuild_if_missing, rc_params):

        prop = FontProperties._from_any(prop)

        fname = prop.get_file()
        if fname is not None:
            return fname

        if fontext == 'afm':
            fontlist = self.afmlist
        else:
            fontlist = self.ttflist

        best_score = 1e64
        best_font = None

        _log.debug('findfont: Matching %s.', prop)
        for font in fontlist:
            if (directory is not None and
                    Path(directory) not in Path(font.fname).parents):
                continue
            # Matching family should have top priority, so multiply it by 10.
            score = (self.score_family(prop.get_family(), font.name) * 10
                     + self.score_style(prop.get_style(), font.style)
                     + self.score_variant(prop.get_variant(), font.variant)
                     + self.score_weight(prop.get_weight(), font.weight)
                     + self.score_stretch(prop.get_stretch(), font.stretch)
                     + self.score_size(prop.get_size(), font.size))
            _log.debug('findfont: score(%s) = %s', font, score)
            if score < best_score:
                best_score = score
                best_font = font
            if score == 0:
                break

        if best_font is None or best_score >= 10.0:
            if fallback_to_default:
                _log.warning(
                    'findfont: Font family %s not found. Falling back to %s.',
                    prop.get_family(), self.defaultFamily[fontext])
                for family in map(str.lower, prop.get_family()):
                    if family in font_family_aliases:
                        _log.warning(
                            "findfont: Generic family %r not found because "
                            "none of the following families were found: %s",
                            family, ", ".join(self._expand_aliases(family)))
                default_prop = prop.copy()
                default_prop.set_family(self.defaultFamily[fontext])
                return self.findfont(default_prop, fontext, directory,
                                     fallback_to_default=False)
            else:
                # This return instead of raise is intentional, as we wish to
                # cache that it was not found, which will not occur if it was
                # actually raised.
                return cbook._ExceptionInfo(
                    ValueError,
                    f"Failed to find font {prop}, and fallback to the default font was "
                    f"disabled"
                )
        else:
            _log.debug('findfont: Matching %s to %s (%r) with score of %f.',
                       prop, best_font.name, best_font.fname, best_score)
            result = best_font.fname

        if not os.path.isfile(result):
            if rebuild_if_missing:
                _log.info(
                    'findfont: Found a missing font file.  Rebuilding cache.')
                new_fm = _load_fontmanager(try_read_cache=False)
                # Replace self by the new fontmanager, because users may have
                # a reference to this specific instance.
                # TODO: _load_fontmanager should really be (used by) a method
                # modifying the instance in place.
                vars(self).update(vars(new_fm))
                return self.findfont(
                    prop, fontext, directory, rebuild_if_missing=False)
            else:
                # This return instead of raise is intentional, as we wish to
                # cache that it was not found, which will not occur if it was
                # actually raised.
                return cbook._ExceptionInfo(ValueError, "No valid font could be found")

        return _cached_realpath(result)


@lru_cache
def is_opentype_cff_font(filename):
    """
    Return whether the given font is a Postscript Compact Font Format Font
    embedded in an OpenType wrapper.  Used by the PostScript and PDF backends
    that cannot subset these fonts.
    """
    if os.path.splitext(filename)[1].lower() == '.otf':
        with open(filename, 'rb') as fd:
            return fd.read(4) == b"OTTO"
    else:
        return False


@lru_cache(64)
def _get_font(font_filepaths, hinting_factor, *, _kerning_factor, thread_id):
    first_fontpath, *rest = font_filepaths
    return ft2font.FT2Font(
        first_fontpath, hinting_factor,
        _fallback_list=[
            ft2font.FT2Font(
                fpath, hinting_factor,
                _kerning_factor=_kerning_factor
            )
            for fpath in rest
        ],
        _kerning_factor=_kerning_factor
    )


# FT2Font objects cannot be used across fork()s because they reference the same
# FT_Library object.  While invalidating *all* existing FT2Fonts after a fork
# would be too complicated to be worth it, the main way FT2Fonts get reused is
# via the cache of _get_font, which we can empty upon forking (not on Windows,
# which has no fork() or register_at_fork()).
if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=_get_font.cache_clear)


@lru_cache(64)
def _cached_realpath(path):
    # Resolving the path avoids embedding the font twice in pdf/ps output if a
    # single font is selected using two different relative paths.
    return os.path.realpath(path)


def get_font(font_filepaths, hinting_factor=None):
    """
    Get an `.ft2font.FT2Font` object given a list of file paths.

    Parameters
    ----------
    font_filepaths : Iterable[str, Path, bytes], str, Path, bytes
        Relative or absolute paths to the font files to be used.

        If a single string, bytes, or `pathlib.Path`, then it will be treated
        as a list with that entry only.

        If more than one filepath is passed, then the returned FT2Font object
        will fall back through the fonts, in the order given, to find a needed
        glyph.

    Returns
    -------
    `.ft2font.FT2Font`

    """
    if isinstance(font_filepaths, (str, Path, bytes)):
        paths = (_cached_realpath(font_filepaths),)
    else:
        paths = tuple(_cached_realpath(fname) for fname in font_filepaths)

    if hinting_factor is None:
        hinting_factor = mpl.rcParams['text.hinting_factor']

    return _get_font(
        # must be a tuple to be cached
        paths,
        hinting_factor,
        _kerning_factor=mpl.rcParams['text.kerning_factor'],
        # also key on the thread ID to prevent segfaults with multi-threading
        thread_id=threading.get_ident()
    )


def _load_fontmanager(*, try_read_cache=True):
    fm_path = Path(
        mpl.get_cachedir(), f"fontlist-v{FontManager.__version__}.json")
    if try_read_cache:
        try:
            fm = json_load(fm_path)
        except Exception:
            pass
        else:
            if getattr(fm, "_version", object()) == FontManager.__version__:
                _log.debug("Using fontManager instance from %s", fm_path)
                return fm
    fm = FontManager()
    json_dump(fm, fm_path)
    _log.info("generated new fontManager")
    return fm


fontManager = _load_fontmanager()
findfont = fontManager.findfont
get_font_names = fontManager.get_font_names

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\_asy_builtins.py ===
"""
    pygments.lexers._asy_builtins
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This file contains the asy-function names and asy-variable names of
    Asymptote.

    Do not edit the ASYFUNCNAME and ASYVARNAME sets by hand.
    TODO: perl/python script in Asymptote SVN similar to asy-list.pl but only
    for function and variable names.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

ASYFUNCNAME = {
    'AND',
    'Arc',
    'ArcArrow',
    'ArcArrows',
    'Arrow',
    'Arrows',
    'Automatic',
    'AvantGarde',
    'BBox',
    'BWRainbow',
    'BWRainbow2',
    'Bar',
    'Bars',
    'BeginArcArrow',
    'BeginArrow',
    'BeginBar',
    'BeginDotMargin',
    'BeginMargin',
    'BeginPenMargin',
    'Blank',
    'Bookman',
    'Bottom',
    'BottomTop',
    'Bounds',
    'Break',
    'Broken',
    'BrokenLog',
    'Ceil',
    'Circle',
    'CircleBarIntervalMarker',
    'Cos',
    'Courier',
    'CrossIntervalMarker',
    'DefaultFormat',
    'DefaultLogFormat',
    'Degrees',
    'Dir',
    'DotMargin',
    'DotMargins',
    'Dotted',
    'Draw',
    'Drawline',
    'Embed',
    'EndArcArrow',
    'EndArrow',
    'EndBar',
    'EndDotMargin',
    'EndMargin',
    'EndPenMargin',
    'Fill',
    'FillDraw',
    'Floor',
    'Format',
    'Full',
    'Gaussian',
    'Gaussrand',
    'Gaussrandpair',
    'Gradient',
    'Grayscale',
    'Helvetica',
    'Hermite',
    'HookHead',
    'InOutTicks',
    'InTicks',
    'J',
    'Label',
    'Landscape',
    'Left',
    'LeftRight',
    'LeftTicks',
    'Legend',
    'Linear',
    'Link',
    'Log',
    'LogFormat',
    'Margin',
    'Margins',
    'Mark',
    'MidArcArrow',
    'MidArrow',
    'NOT',
    'NewCenturySchoolBook',
    'NoBox',
    'NoMargin',
    'NoModifier',
    'NoTicks',
    'NoTicks3',
    'NoZero',
    'NoZeroFormat',
    'None',
    'OR',
    'OmitFormat',
    'OmitTick',
    'OutTicks',
    'Ox',
    'Oy',
    'Palatino',
    'PaletteTicks',
    'Pen',
    'PenMargin',
    'PenMargins',
    'Pentype',
    'Portrait',
    'RadialShade',
    'Rainbow',
    'Range',
    'Relative',
    'Right',
    'RightTicks',
    'Rotate',
    'Round',
    'SQR',
    'Scale',
    'ScaleX',
    'ScaleY',
    'ScaleZ',
    'Seascape',
    'Shift',
    'Sin',
    'Slant',
    'Spline',
    'StickIntervalMarker',
    'Straight',
    'Symbol',
    'Tan',
    'TeXify',
    'Ticks',
    'Ticks3',
    'TildeIntervalMarker',
    'TimesRoman',
    'Top',
    'TrueMargin',
    'UnFill',
    'UpsideDown',
    'Wheel',
    'X',
    'XEquals',
    'XOR',
    'XY',
    'XYEquals',
    'XYZero',
    'XYgrid',
    'XZEquals',
    'XZZero',
    'XZero',
    'XZgrid',
    'Y',
    'YEquals',
    'YXgrid',
    'YZ',
    'YZEquals',
    'YZZero',
    'YZero',
    'YZgrid',
    'Z',
    'ZX',
    'ZXgrid',
    'ZYgrid',
    'ZapfChancery',
    'ZapfDingbats',
    '_cputime',
    '_draw',
    '_eval',
    '_image',
    '_labelpath',
    '_projection',
    '_strokepath',
    '_texpath',
    'aCos',
    'aSin',
    'aTan',
    'abort',
    'abs',
    'accel',
    'acos',
    'acosh',
    'acot',
    'acsc',
    'add',
    'addArrow',
    'addMargins',
    'addSaveFunction',
    'addnode',
    'addnodes',
    'addpenarc',
    'addpenline',
    'addseg',
    'adjust',
    'alias',
    'align',
    'all',
    'altitude',
    'angabscissa',
    'angle',
    'angpoint',
    'animate',
    'annotate',
    'anticomplementary',
    'antipedal',
    'apply',
    'approximate',
    'arc',
    'arcarrowsize',
    'arccircle',
    'arcdir',
    'arcfromcenter',
    'arcfromfocus',
    'arclength',
    'arcnodesnumber',
    'arcpoint',
    'arcsubtended',
    'arcsubtendedcenter',
    'arctime',
    'arctopath',
    'array',
    'arrow',
    'arrow2',
    'arrowbase',
    'arrowbasepoints',
    'arrowsize',
    'asec',
    'asin',
    'asinh',
    'ask',
    'assert',
    'asy',
    'asycode',
    'asydir',
    'asyfigure',
    'asyfilecode',
    'asyinclude',
    'asywrite',
    'atan',
    'atan2',
    'atanh',
    'atbreakpoint',
    'atexit',
    'atime',
    'attach',
    'attract',
    'atupdate',
    'autoformat',
    'autoscale',
    'autoscale3',
    'axes',
    'axes3',
    'axialshade',
    'axis',
    'axiscoverage',
    'azimuth',
    'babel',
    'background',
    'bangles',
    'bar',
    'barmarksize',
    'barsize',
    'basealign',
    'baseline',
    'bbox',
    'beep',
    'begin',
    'beginclip',
    'begingroup',
    'beginpoint',
    'between',
    'bevel',
    'bezier',
    'bezierP',
    'bezierPP',
    'bezierPPP',
    'bezulate',
    'bibliography',
    'bibliographystyle',
    'binarytree',
    'binarytreeNode',
    'binomial',
    'binput',
    'bins',
    'bisector',
    'bisectorpoint',
    'blend',
    'boutput',
    'box',
    'bqe',
    'breakpoint',
    'breakpoints',
    'brick',
    'buildRestoreDefaults',
    'buildRestoreThunk',
    'buildcycle',
    'bulletcolor',
    'canonical',
    'canonicalcartesiansystem',
    'cartesiansystem',
    'case1',
    'case2',
    'case3',
    'cbrt',
    'cd',
    'ceil',
    'center',
    'centerToFocus',
    'centroid',
    'cevian',
    'change2',
    'changecoordsys',
    'checkSegment',
    'checkconditionlength',
    'checker',
    'checklengths',
    'checkposition',
    'checktriangle',
    'choose',
    'circle',
    'circlebarframe',
    'circlemarkradius',
    'circlenodesnumber',
    'circumcenter',
    'circumcircle',
    'clamped',
    'clear',
    'clip',
    'clipdraw',
    'close',
    'cmyk',
    'code',
    'colatitude',
    'collect',
    'collinear',
    'color',
    'colorless',
    'colors',
    'colorspace',
    'comma',
    'compassmark',
    'complement',
    'complementary',
    'concat',
    'concurrent',
    'cone',
    'conic',
    'conicnodesnumber',
    'conictype',
    'conj',
    'connect',
    'containmentTree',
    'contains',
    'contour',
    'contour3',
    'controlSpecifier',
    'convert',
    'coordinates',
    'coordsys',
    'copy',
    'cos',
    'cosh',
    'cot',
    'countIntersections',
    'cputime',
    'crop',
    'cropcode',
    'cross',
    'crossframe',
    'crosshatch',
    'crossmarksize',
    'csc',
    'cubicroots',
    'curabscissa',
    'curlSpecifier',
    'curpoint',
    'currentarrow',
    'currentexitfunction',
    'currentmomarrow',
    'currentpolarconicroutine',
    'curve',
    'cut',
    'cutafter',
    'cutbefore',
    'cyclic',
    'cylinder',
    'debugger',
    'deconstruct',
    'defaultdir',
    'defaultformat',
    'defaultpen',
    'defined',
    'degenerate',
    'degrees',
    'delete',
    'deletepreamble',
    'determinant',
    'diagonal',
    'diamond',
    'diffdiv',
    'dir',
    'dirSpecifier',
    'dirtime',
    'display',
    'distance',
    'divisors',
    'do_overpaint',
    'dot',
    'dotframe',
    'dotsize',
    'downcase',
    'draw',
    'drawAll',
    'drawDoubleLine',
    'drawFermion',
    'drawGhost',
    'drawGluon',
    'drawMomArrow',
    'drawPhoton',
    'drawScalar',
    'drawVertex',
    'drawVertexBox',
    'drawVertexBoxO',
    'drawVertexBoxX',
    'drawVertexO',
    'drawVertexOX',
    'drawVertexTriangle',
    'drawVertexTriangleO',
    'drawVertexX',
    'drawarrow',
    'drawarrow2',
    'drawline',
    'drawtick',
    'duplicate',
    'elle',
    'ellipse',
    'ellipsenodesnumber',
    'embed',
    'embed3',
    'empty',
    'enclose',
    'end',
    'endScript',
    'endclip',
    'endgroup',
    'endl',
    'endpoint',
    'endpoints',
    'eof',
    'eol',
    'equation',
    'equations',
    'erase',
    'erasestep',
    'erf',
    'erfc',
    'error',
    'errorbar',
    'errorbars',
    'eval',
    'excenter',
    'excircle',
    'exit',
    'exitXasyMode',
    'exitfunction',
    'exp',
    'expfactors',
    'expi',
    'expm1',
    'exradius',
    'extend',
    'extension',
    'extouch',
    'fabs',
    'factorial',
    'fermat',
    'fft',
    'fhorner',
    'figure',
    'file',
    'filecode',
    'fill',
    'filldraw',
    'filloutside',
    'fillrule',
    'filltype',
    'find',
    'finite',
    'finiteDifferenceJacobian',
    'firstcut',
    'firstframe',
    'fit',
    'fit2',
    'fixedscaling',
    'floor',
    'flush',
    'fmdefaults',
    'fmod',
    'focusToCenter',
    'font',
    'fontcommand',
    'fontsize',
    'foot',
    'format',
    'frac',
    'frequency',
    'fromCenter',
    'fromFocus',
    'fspline',
    'functionshade',
    'gamma',
    'generate_random_backtrace',
    'generateticks',
    'gergonne',
    'getc',
    'getint',
    'getpair',
    'getreal',
    'getstring',
    'gettriple',
    'gluon',
    'gouraudshade',
    'graph',
    'graphic',
    'gray',
    'grestore',
    'grid',
    'grid3',
    'gsave',
    'halfbox',
    'hatch',
    'hdiffdiv',
    'hermite',
    'hex',
    'histogram',
    'history',
    'hline',
    'hprojection',
    'hsv',
    'hyperbola',
    'hyperbolanodesnumber',
    'hyperlink',
    'hypot',
    'identity',
    'image',
    'incenter',
    'incentral',
    'incircle',
    'increasing',
    'incrementposition',
    'indexedTransform',
    'indexedfigure',
    'initXasyMode',
    'initdefaults',
    'input',
    'inradius',
    'insert',
    'inside',
    'integrate',
    'interactive',
    'interior',
    'interp',
    'interpolate',
    'intersect',
    'intersection',
    'intersectionpoint',
    'intersectionpoints',
    'intersections',
    'intouch',
    'inverse',
    'inversion',
    'invisible',
    'is3D',
    'isDuplicate',
    'isogonal',
    'isogonalconjugate',
    'isotomic',
    'isotomicconjugate',
    'isparabola',
    'italic',
    'item',
    'key',
    'kurtosis',
    'kurtosisexcess',
    'label',
    'labelaxis',
    'labelmargin',
    'labelpath',
    'labels',
    'labeltick',
    'labelx',
    'labelx3',
    'labely',
    'labely3',
    'labelz',
    'labelz3',
    'lastcut',
    'latex',
    'latitude',
    'latticeshade',
    'layer',
    'layout',
    'ldexp',
    'leastsquares',
    'legend',
    'legenditem',
    'length',
    'lift',
    'light',
    'limits',
    'line',
    'linear',
    'linecap',
    'lineinversion',
    'linejoin',
    'linemargin',
    'lineskip',
    'linetype',
    'linewidth',
    'link',
    'list',
    'lm_enorm',
    'lm_evaluate_default',
    'lm_lmdif',
    'lm_lmpar',
    'lm_minimize',
    'lm_print_default',
    'lm_print_quiet',
    'lm_qrfac',
    'lm_qrsolv',
    'locale',
    'locate',
    'locatefile',
    'location',
    'log',
    'log10',
    'log1p',
    'logaxiscoverage',
    'longitude',
    'lookup',
    'magnetize',
    'makeNode',
    'makedraw',
    'makepen',
    'map',
    'margin',
    'markangle',
    'markangleradius',
    'markanglespace',
    'markarc',
    'marker',
    'markinterval',
    'marknodes',
    'markrightangle',
    'markuniform',
    'mass',
    'masscenter',
    'massformat',
    'math',
    'max',
    'max3',
    'maxbezier',
    'maxbound',
    'maxcoords',
    'maxlength',
    'maxratio',
    'maxtimes',
    'mean',
    'medial',
    'median',
    'midpoint',
    'min',
    'min3',
    'minbezier',
    'minbound',
    'minipage',
    'minratio',
    'mintimes',
    'miterlimit',
    'momArrowPath',
    'momarrowsize',
    'monotonic',
    'multifigure',
    'nativeformat',
    'natural',
    'needshipout',
    'newl',
    'newpage',
    'newslide',
    'newton',
    'newtree',
    'nextframe',
    'nextnormal',
    'nextpage',
    'nib',
    'nodabscissa',
    'none',
    'norm',
    'normalvideo',
    'notaknot',
    'nowarn',
    'numberpage',
    'nurb',
    'object',
    'offset',
    'onpath',
    'opacity',
    'opposite',
    'orientation',
    'orig_circlenodesnumber',
    'orig_circlenodesnumber1',
    'orig_draw',
    'orig_ellipsenodesnumber',
    'orig_ellipsenodesnumber1',
    'orig_hyperbolanodesnumber',
    'orig_parabolanodesnumber',
    'origin',
    'orthic',
    'orthocentercenter',
    'outformat',
    'outline',
    'outprefix',
    'output',
    'overloadedMessage',
    'overwrite',
    'pack',
    'pad',
    'pairs',
    'palette',
    'parabola',
    'parabolanodesnumber',
    'parallel',
    'partialsum',
    'path',
    'path3',
    'pattern',
    'pause',
    'pdf',
    'pedal',
    'periodic',
    'perp',
    'perpendicular',
    'perpendicularmark',
    'phantom',
    'phi1',
    'phi2',
    'phi3',
    'photon',
    'piecewisestraight',
    'point',
    'polar',
    'polarconicroutine',
    'polargraph',
    'polygon',
    'postcontrol',
    'postscript',
    'pow10',
    'ppoint',
    'prc',
    'prc0',
    'precision',
    'precontrol',
    'prepend',
    'print_random_addresses',
    'project',
    'projection',
    'purge',
    'pwhermite',
    'quadrant',
    'quadraticroots',
    'quantize',
    'quarticroots',
    'quotient',
    'radialshade',
    'radians',
    'radicalcenter',
    'radicalline',
    'radius',
    'rand',
    'randompath',
    'rd',
    'readline',
    'realmult',
    'realquarticroots',
    'rectangle',
    'rectangular',
    'rectify',
    'reflect',
    'relabscissa',
    'relative',
    'relativedistance',
    'reldir',
    'relpoint',
    'reltime',
    'remainder',
    'remark',
    'removeDuplicates',
    'rename',
    'replace',
    'report',
    'resetdefaultpen',
    'restore',
    'restoredefaults',
    'reverse',
    'reversevideo',
    'rf',
    'rfind',
    'rgb',
    'rgba',
    'rgbint',
    'rms',
    'rotate',
    'rotateO',
    'rotation',
    'round',
    'roundbox',
    'roundedpath',
    'roundrectangle',
    'samecoordsys',
    'sameside',
    'sample',
    'save',
    'savedefaults',
    'saveline',
    'scale',
    'scale3',
    'scaleO',
    'scaleT',
    'scaleless',
    'scientific',
    'search',
    'searchtree',
    'sec',
    'secondaryX',
    'secondaryY',
    'seconds',
    'section',
    'sector',
    'seek',
    'seekeof',
    'segment',
    'sequence',
    'setpens',
    'sgn',
    'sgnd',
    'sharpangle',
    'sharpdegrees',
    'shift',
    'shiftless',
    'shipout',
    'shipout3',
    'show',
    'side',
    'simeq',
    'simpson',
    'sin',
    'single',
    'sinh',
    'size',
    'size3',
    'skewness',
    'skip',
    'slant',
    'sleep',
    'slope',
    'slopefield',
    'solve',
    'solveBVP',
    'sort',
    'sourceline',
    'sphere',
    'split',
    'sqrt',
    'square',
    'srand',
    'standardizecoordsys',
    'startScript',
    'startTrembling',
    'stdev',
    'step',
    'stickframe',
    'stickmarksize',
    'stickmarkspace',
    'stop',
    'straight',
    'straightness',
    'string',
    'stripdirectory',
    'stripextension',
    'stripfile',
    'strokepath',
    'subdivide',
    'subitem',
    'subpath',
    'substr',
    'sum',
    'surface',
    'symmedial',
    'symmedian',
    'system',
    'tab',
    'tableau',
    'tan',
    'tangent',
    'tangential',
    'tangents',
    'tanh',
    'tell',
    'tensionSpecifier',
    'tensorshade',
    'tex',
    'texcolor',
    'texify',
    'texpath',
    'texpreamble',
    'texreset',
    'texshipout',
    'texsize',
    'textpath',
    'thick',
    'thin',
    'tick',
    'tickMax',
    'tickMax3',
    'tickMin',
    'tickMin3',
    'ticklabelshift',
    'ticklocate',
    'tildeframe',
    'tildemarksize',
    'tile',
    'tiling',
    'time',
    'times',
    'title',
    'titlepage',
    'topbox',
    'transform',
    'transformation',
    'transpose',
    'tremble',
    'trembleFuzz',
    'tremble_circlenodesnumber',
    'tremble_circlenodesnumber1',
    'tremble_draw',
    'tremble_ellipsenodesnumber',
    'tremble_ellipsenodesnumber1',
    'tremble_hyperbolanodesnumber',
    'tremble_marknodes',
    'tremble_markuniform',
    'tremble_parabolanodesnumber',
    'triangle',
    'triangleAbc',
    'triangleabc',
    'triangulate',
    'tricoef',
    'tridiagonal',
    'trilinear',
    'trim',
    'trueMagnetize',
    'truepoint',
    'tube',
    'uncycle',
    'unfill',
    'uniform',
    'unit',
    'unitrand',
    'unitsize',
    'unityroot',
    'unstraighten',
    'upcase',
    'updatefunction',
    'uperiodic',
    'upscale',
    'uptodate',
    'usepackage',
    'usersetting',
    'usetypescript',
    'usleep',
    'value',
    'variance',
    'variancebiased',
    'vbox',
    'vector',
    'vectorfield',
    'verbatim',
    'view',
    'vline',
    'vperiodic',
    'vprojection',
    'warn',
    'warning',
    'windingnumber',
    'write',
    'xaxis',
    'xaxis3',
    'xaxis3At',
    'xaxisAt',
    'xequals',
    'xinput',
    'xlimits',
    'xoutput',
    'xpart',
    'xscale',
    'xscaleO',
    'xtick',
    'xtick3',
    'xtrans',
    'yaxis',
    'yaxis3',
    'yaxis3At',
    'yaxisAt',
    'yequals',
    'ylimits',
    'ypart',
    'yscale',
    'yscaleO',
    'ytick',
    'ytick3',
    'ytrans',
    'zaxis3',
    'zaxis3At',
    'zero',
    'zero3',
    'zlimits',
    'zpart',
    'ztick',
    'ztick3',
    'ztrans'
}

ASYVARNAME = {
    'AliceBlue',
    'Align',
    'Allow',
    'AntiqueWhite',
    'Apricot',
    'Aqua',
    'Aquamarine',
    'Aspect',
    'Azure',
    'BeginPoint',
    'Beige',
    'Bisque',
    'Bittersweet',
    'Black',
    'BlanchedAlmond',
    'Blue',
    'BlueGreen',
    'BlueViolet',
    'Both',
    'Break',
    'BrickRed',
    'Brown',
    'BurlyWood',
    'BurntOrange',
    'CCW',
    'CW',
    'CadetBlue',
    'CarnationPink',
    'Center',
    'Centered',
    'Cerulean',
    'Chartreuse',
    'Chocolate',
    'Coeff',
    'Coral',
    'CornflowerBlue',
    'Cornsilk',
    'Crimson',
    'Crop',
    'Cyan',
    'Dandelion',
    'DarkBlue',
    'DarkCyan',
    'DarkGoldenrod',
    'DarkGray',
    'DarkGreen',
    'DarkKhaki',
    'DarkMagenta',
    'DarkOliveGreen',
    'DarkOrange',
    'DarkOrchid',
    'DarkRed',
    'DarkSalmon',
    'DarkSeaGreen',
    'DarkSlateBlue',
    'DarkSlateGray',
    'DarkTurquoise',
    'DarkViolet',
    'DeepPink',
    'DeepSkyBlue',
    'DefaultHead',
    'DimGray',
    'DodgerBlue',
    'Dotted',
    'Draw',
    'E',
    'ENE',
    'EPS',
    'ESE',
    'E_Euler',
    'E_PC',
    'E_RK2',
    'E_RK3BS',
    'Emerald',
    'EndPoint',
    'Euler',
    'Fill',
    'FillDraw',
    'FireBrick',
    'FloralWhite',
    'ForestGreen',
    'Fuchsia',
    'Gainsboro',
    'GhostWhite',
    'Gold',
    'Goldenrod',
    'Gray',
    'Green',
    'GreenYellow',
    'Honeydew',
    'HookHead',
    'Horizontal',
    'HotPink',
    'I',
    'IgnoreAspect',
    'IndianRed',
    'Indigo',
    'Ivory',
    'JOIN_IN',
    'JOIN_OUT',
    'JungleGreen',
    'Khaki',
    'LM_DWARF',
    'LM_MACHEP',
    'LM_SQRT_DWARF',
    'LM_SQRT_GIANT',
    'LM_USERTOL',
    'Label',
    'Lavender',
    'LavenderBlush',
    'LawnGreen',
    'LeftJustified',
    'LeftSide',
    'LemonChiffon',
    'LightBlue',
    'LightCoral',
    'LightCyan',
    'LightGoldenrodYellow',
    'LightGreen',
    'LightGrey',
    'LightPink',
    'LightSalmon',
    'LightSeaGreen',
    'LightSkyBlue',
    'LightSlateGray',
    'LightSteelBlue',
    'LightYellow',
    'Lime',
    'LimeGreen',
    'Linear',
    'Linen',
    'Log',
    'Logarithmic',
    'Magenta',
    'Mahogany',
    'Mark',
    'MarkFill',
    'Maroon',
    'Max',
    'MediumAquamarine',
    'MediumBlue',
    'MediumOrchid',
    'MediumPurple',
    'MediumSeaGreen',
    'MediumSlateBlue',
    'MediumSpringGreen',
    'MediumTurquoise',
    'MediumVioletRed',
    'Melon',
    'MidPoint',
    'MidnightBlue',
    'Min',
    'MintCream',
    'MistyRose',
    'Moccasin',
    'Move',
    'MoveQuiet',
    'Mulberry',
    'N',
    'NE',
    'NNE',
    'NNW',
    'NW',
    'NavajoWhite',
    'Navy',
    'NavyBlue',
    'NoAlign',
    'NoCrop',
    'NoFill',
    'NoSide',
    'OldLace',
    'Olive',
    'OliveDrab',
    'OliveGreen',
    'Orange',
    'OrangeRed',
    'Orchid',
    'Ox',
    'Oy',
    'PC',
    'PaleGoldenrod',
    'PaleGreen',
    'PaleTurquoise',
    'PaleVioletRed',
    'PapayaWhip',
    'Peach',
    'PeachPuff',
    'Periwinkle',
    'Peru',
    'PineGreen',
    'Pink',
    'Plum',
    'PowderBlue',
    'ProcessBlue',
    'Purple',
    'RK2',
    'RK3',
    'RK3BS',
    'RK4',
    'RK5',
    'RK5DP',
    'RK5F',
    'RawSienna',
    'Red',
    'RedOrange',
    'RedViolet',
    'Rhodamine',
    'RightJustified',
    'RightSide',
    'RosyBrown',
    'RoyalBlue',
    'RoyalPurple',
    'RubineRed',
    'S',
    'SE',
    'SSE',
    'SSW',
    'SW',
    'SaddleBrown',
    'Salmon',
    'SandyBrown',
    'SeaGreen',
    'Seashell',
    'Sepia',
    'Sienna',
    'Silver',
    'SimpleHead',
    'SkyBlue',
    'SlateBlue',
    'SlateGray',
    'Snow',
    'SpringGreen',
    'SteelBlue',
    'Suppress',
    'SuppressQuiet',
    'Tan',
    'TeXHead',
    'Teal',
    'TealBlue',
    'Thistle',
    'Ticksize',
    'Tomato',
    'Turquoise',
    'UnFill',
    'VERSION',
    'Value',
    'Vertical',
    'Violet',
    'VioletRed',
    'W',
    'WNW',
    'WSW',
    'Wheat',
    'White',
    'WhiteSmoke',
    'WildStrawberry',
    'XYAlign',
    'YAlign',
    'Yellow',
    'YellowGreen',
    'YellowOrange',
    'addpenarc',
    'addpenline',
    'align',
    'allowstepping',
    'angularsystem',
    'animationdelay',
    'appendsuffix',
    'arcarrowangle',
    'arcarrowfactor',
    'arrow2sizelimit',
    'arrowangle',
    'arrowbarb',
    'arrowdir',
    'arrowfactor',
    'arrowhookfactor',
    'arrowlength',
    'arrowsizelimit',
    'arrowtexfactor',
    'authorpen',
    'axis',
    'axiscoverage',
    'axislabelfactor',
    'background',
    'backgroundcolor',
    'backgroundpen',
    'barfactor',
    'barmarksizefactor',
    'basealign',
    'baselinetemplate',
    'beveljoin',
    'bigvertexpen',
    'bigvertexsize',
    'black',
    'blue',
    'bm',
    'bottom',
    'bp',
    'brown',
    'bullet',
    'byfoci',
    'byvertices',
    'camerafactor',
    'chartreuse',
    'circlemarkradiusfactor',
    'circlenodesnumberfactor',
    'circleprecision',
    'circlescale',
    'cm',
    'codefile',
    'codepen',
    'codeskip',
    'colorPen',
    'coloredNodes',
    'coloredSegments',
    'conditionlength',
    'conicnodesfactor',
    'count',
    'cputimeformat',
    'crossmarksizefactor',
    'currentcoordsys',
    'currentlight',
    'currentpatterns',
    'currentpen',
    'currentpicture',
    'currentposition',
    'currentprojection',
    'curvilinearsystem',
    'cuttings',
    'cyan',
    'darkblue',
    'darkbrown',
    'darkcyan',
    'darkgray',
    'darkgreen',
    'darkgrey',
    'darkmagenta',
    'darkolive',
    'darkred',
    'dashdotted',
    'dashed',
    'datepen',
    'dateskip',
    'debuggerlines',
    'debugging',
    'deepblue',
    'deepcyan',
    'deepgray',
    'deepgreen',
    'deepgrey',
    'deepmagenta',
    'deepred',
    'default',
    'defaultControl',
    'defaultS',
    'defaultbackpen',
    'defaultcoordsys',
    'defaultfilename',
    'defaultformat',
    'defaultmassformat',
    'defaultpen',
    'diagnostics',
    'differentlengths',
    'dot',
    'dotfactor',
    'dotframe',
    'dotted',
    'doublelinepen',
    'doublelinespacing',
    'down',
    'duplicateFuzz',
    'ellipsenodesnumberfactor',
    'eps',
    'epsgeo',
    'epsilon',
    'evenodd',
    'extendcap',
    'fermionpen',
    'figureborder',
    'figuremattpen',
    'firstnode',
    'firststep',
    'foregroundcolor',
    'fuchsia',
    'fuzz',
    'gapfactor',
    'ghostpen',
    'gluonamplitude',
    'gluonpen',
    'gluonratio',
    'gray',
    'green',
    'grey',
    'hatchepsilon',
    'havepagenumber',
    'heavyblue',
    'heavycyan',
    'heavygray',
    'heavygreen',
    'heavygrey',
    'heavymagenta',
    'heavyred',
    'hline',
    'hwratio',
    'hyperbolanodesnumberfactor',
    'identity4',
    'ignore',
    'inXasyMode',
    'inch',
    'inches',
    'includegraphicscommand',
    'inf',
    'infinity',
    'institutionpen',
    'intMax',
    'intMin',
    'invert',
    'invisible',
    'itempen',
    'itemskip',
    'itemstep',
    'labelmargin',
    'landscape',
    'lastnode',
    'left',
    'legendhskip',
    'legendlinelength',
    'legendmargin',
    'legendmarkersize',
    'legendmaxrelativewidth',
    'legendvskip',
    'lightblue',
    'lightcyan',
    'lightgray',
    'lightgreen',
    'lightgrey',
    'lightmagenta',
    'lightolive',
    'lightred',
    'lightyellow',
    'linemargin',
    'lm_infmsg',
    'lm_shortmsg',
    'longdashdotted',
    'longdashed',
    'magenta',
    'magneticPoints',
    'magneticRadius',
    'mantissaBits',
    'markangleradius',
    'markangleradiusfactor',
    'markanglespace',
    'markanglespacefactor',
    'mediumblue',
    'mediumcyan',
    'mediumgray',
    'mediumgreen',
    'mediumgrey',
    'mediummagenta',
    'mediumred',
    'mediumyellow',
    'middle',
    'minDistDefault',
    'minblockheight',
    'minblockwidth',
    'mincirclediameter',
    'minipagemargin',
    'minipagewidth',
    'minvertexangle',
    'miterjoin',
    'mm',
    'momarrowfactor',
    'momarrowlength',
    'momarrowmargin',
    'momarrowoffset',
    'momarrowpen',
    'monoPen',
    'morepoints',
    'nCircle',
    'newbulletcolor',
    'ngraph',
    'nil',
    'nmesh',
    'nobasealign',
    'nodeMarginDefault',
    'nodesystem',
    'nomarker',
    'nopoint',
    'noprimary',
    'nullpath',
    'nullpen',
    'numarray',
    'ocgindex',
    'oldbulletcolor',
    'olive',
    'orange',
    'origin',
    'overpaint',
    'page',
    'pageheight',
    'pagemargin',
    'pagenumberalign',
    'pagenumberpen',
    'pagenumberposition',
    'pagewidth',
    'paleblue',
    'palecyan',
    'palegray',
    'palegreen',
    'palegrey',
    'palemagenta',
    'palered',
    'paleyellow',
    'parabolanodesnumberfactor',
    'perpfactor',
    'phi',
    'photonamplitude',
    'photonpen',
    'photonratio',
    'pi',
    'pink',
    'plain',
    'plus',
    'preamblenodes',
    'pt',
    'purple',
    'r3',
    'r4a',
    'r4b',
    'randMax',
    'realDigits',
    'realEpsilon',
    'realMax',
    'realMin',
    'red',
    'relativesystem',
    'reverse',
    'right',
    'roundcap',
    'roundjoin',
    'royalblue',
    'salmon',
    'saveFunctions',
    'scalarpen',
    'sequencereal',
    'settings',
    'shipped',
    'signedtrailingzero',
    'solid',
    'springgreen',
    'sqrtEpsilon',
    'squarecap',
    'squarepen',
    'startposition',
    'stdin',
    'stdout',
    'stepfactor',
    'stepfraction',
    'steppagenumberpen',
    'stepping',
    'stickframe',
    'stickmarksizefactor',
    'stickmarkspacefactor',
    'textpen',
    'ticksize',
    'tildeframe',
    'tildemarksizefactor',
    'tinv',
    'titlealign',
    'titlepagepen',
    'titlepageposition',
    'titlepen',
    'titleskip',
    'top',
    'trailingzero',
    'treeLevelStep',
    'treeMinNodeWidth',
    'treeNodeStep',
    'trembleAngle',
    'trembleFrequency',
    'trembleRandom',
    'tremblingMode',
    'undefined',
    'unitcircle',
    'unitsquare',
    'up',
    'urlpen',
    'urlskip',
    'version',
    'vertexpen',
    'vertexsize',
    'viewportmargin',
    'viewportsize',
    'vline',
    'white',
    'wye',
    'xformStack',
    'yellow',
    'ylabelwidth',
    'zerotickfuzz',
    'zerowinding'
}